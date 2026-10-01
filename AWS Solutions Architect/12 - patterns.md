---
title: "跨雲通用 Architecture Patterns"
part: 11
as_of: 2026-10-01
---

# Part 11　跨雲通用 Architecture Patterns

# 第 105 章　Managed Service 優先與 Escape Hatch

自行營運基礎元件能獲得控制，但會承擔patch、HA、backup、upgrade與on-call。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：團隊考慮自建Kafka/RDS替代品，只因單價看似較低。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：自行營運基礎元件能獲得控制，但會承擔patch、HA、backup、upgrade與on-call。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon RDS，對照角色是Amazon MSK。我們選擇「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：團隊考慮自建Kafka/RDS替代品，只因單價看似較低。

商業需求與不能妥協的限制
          ▼
[Amazon RDS：主要責任]
          │ 代管關聯式database engine的provisioning、patch、backup與failover。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon MSK：提供managed Apache Kafka brokers與control plane。
  · AWS Fargate：讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。
可移植原則：buy undifferentiated operations; retain control over differentiating contracts

失敗時先找：把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon RDS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon RDS和Amazon MSK並不是兩個任意的產品名稱。前者適合本章，是因為「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」直接回應了眼前的問題；後者描述的「自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「buy undifferentiated operations; retain control over differentiating contracts」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 |
| Amazon MSK | 提供managed Apache Kafka brokers與control plane。 | Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 |

## 把全圖套進一個具體案例

**場景：** 團隊考慮自建Kafka/RDS替代品，只因單價看似較低。

1. 故事的起點：團隊考慮自建Kafka/RDS替代品，只因單價看似較低。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon RDS負責「代管關聯式database engine的provisioning、patch、backup與failover。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon MSK、AWS Fargate各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon RDS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：自行營運基礎元件能獲得控制，但會承擔patch、HA、backup、upgrade與on-call。
- **具體例子／邊界：** 在「團隊考慮自建Kafka/RDS替代品，只因單價看似較低。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon MSK

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：buy undifferentiated operations; retain control over differentiating contracts。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### managed service

供應商接手部分基礎設施責任的服務；customer仍負責資料、身份、設定、access pattern與business correctness。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon RDS

- **功用：** 代管關聯式database engine的provisioning、patch、backup與failover。
- **底層機制：** DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
- **關鍵設定：** engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- **選擇時機：** 需要SQL transaction、joins、schema與managed operations。
- **替換時機：** 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。

### Amazon MSK

- **功用：** 提供managed Apache Kafka brokers與control plane。
- **底層機制：** Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。
- **關鍵設定：** provisioned/serverless、broker type/count、storage、partitions/replication、authentication、configuration與connectors。
- **選擇時機：** 既有Kafka clients、portable ecosystem、長retention與複雜stream processing。
- **替換時機：** 不需要Kafka營運/相容性時Kinesis較AWS-native；simple queue選SQS。

### AWS Fargate

- **功用：** 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。
- **底層機制：** AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。
- **關鍵設定：** task CPU/memory組合、awsvpc、subnets/security groups、ephemeral storage與platform version。
- **選擇時機：** bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。
- **替換時機：** 穩定高利用率或需GPU、特殊daemon/host access時改用EC2-backed ECS/EKS。

## 考前與實作時再查：設定操作手冊

### Amazon RDS：逐項設定說明

#### `engine/version`

- **控制什麼：** `engine/version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `instance/storage`

- **控制什麼：** `instance/storage`選擇Amazon RDS的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `Multi-AZ`

- **控制什麼：** `Multi-AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon RDS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `backup retention`

- **控制什麼：** `backup retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon RDS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `maintenance window`

- **控制什麼：** `maintenance window`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon RDS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `parameter/option group`

- **控制什麼：** `parameter/option group`是一組可版本化的engine/runtime參數，會改變Amazon RDS的實際process行為。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `network`

- **控制什麼：** `network`指定Amazon RDS的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

### Amazon MSK：逐項設定說明

#### `provisioned/serverless`

- **控制什麼：** `provisioned/serverless`決定Amazon MSK如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `broker type/count`

- **控制什麼：** `broker type/count`選擇Amazon MSK的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `storage`

- **控制什麼：** `storage`選擇Amazon MSK的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `partitions/replication`

- **控制什麼：** `partitions/replication`設定Amazon MSK的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「既有Kafka clients、portable ecosystem、長retention與複雜stream processing。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `authentication`

- **控制什麼：** `authentication`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `configuration`

- **控制什麼：** `configuration`是一組可版本化的engine/runtime參數，會改變Amazon MSK的實際process行為。
- **何時需要：** 當需求符合「既有Kafka clients、portable ecosystem、長retention與複雜stream processing。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `connectors`

- **控制什麼：** `connectors`把Amazon MSK與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

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

## 讀到這裡，請用自己的話說一次

1. Amazon RDS的責任：代管關聯式database engine的provisioning、patch、backup與failover。
2. 底層機制：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
3. 第一個要看的設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
4. 選擇邏輯：先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。
5. 不要混淆：Amazon MSK的責任是「提供managed Apache Kafka brokers與control plane。」；它不會自動取代Amazon RDS。
6. 替換訊號：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
7. 最常見錯法：把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。
8. 可移植原則：buy undifferentiated operations; retain control over differentiating contracts。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 | 需要SQL transaction、joins、schema與managed operations。 | 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。 |
| Amazon MSK | 提供managed Apache Kafka brokers與control plane。 | Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。 | 既有Kafka clients、portable ecosystem、長retention與複雜stream processing。 | 不需要Kafka營運/相容性時Kinesis較AWS-native；simple queue選SQS。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 | bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。 | 穩定高利用率或需GPU、特殊daemon/host access時改用EC2-backed ECS/EKS。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。 | 只有當題目條件明確改變時才可能合理。 | 把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。」之間做選擇。
- 認得常考設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Managed service 與客戶責任邊界

團隊把自管 PostgreSQL 搬到 Amazon RDS 後，主管認為 AWS 會同時負責 schema 正確性、慢查詢、使用者權限與業務 RPO。哪一項最準確描述上線後的責任邊界？

A. AWS管底層；客戶管資料、權限、效能與RPO
B. RDS 是 managed service，因此 application 的 retry 與 transaction correctness 都由服務保證
C. 只要啟用 Multi-AZ，schema、容量與資料保留需求便由 AWS 決定
D. 客戶仍要修補 RDS 主機作業系統，但 AWS 會自動修正所有 SQL

**答案：A**

- **A：** 正確。Managed service 收斂基礎設施責任，不會接手應用語意、權限設計、效能假設與業務正確性。
- **B：** 錯誤。連線重試、冪等性、transaction 邊界與錯誤處理仍須由 application 與架構明確設計。
- **C：** 錯誤。Multi-AZ 提供特定 HA 拓撲，不會替業務定義 schema、容量、RTO 或 RPO。
- **D：** 錯誤。RDS 接手資料庫主機與引擎維運的一部分，客戶不登入主機修補 OS；但 SQL 與資料模型仍屬客戶責任。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[What is Amazon Relational Database Service?](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 2｜SAA｜依必要 contract 選 managed abstraction

公司已有數十個使用 Kafka protocol、consumer groups 與既有 connector 的應用，目標是減少 broker patch 與 replacement 的營運負擔，但短期不能改 client protocol。哪個方案最直接符合限制？

A. 改用 Amazon RDS，因為任何持久資料都應優先放入 relational database
B. 改用單一 Amazon SQS queue，並假設它與 Kafka replay、partition ordering 與 connector 生態完全等價；遷移前另以connector重寫試點驗證成本，但正式路徑仍先維持自管Kafka protocol
C. Amazon MSK保留Kafka protocol、consumer groups與connectors
D. 改用 AWS Fargate，因為容器執行平台會自動提供 Kafka topic 與 consumer-group semantics

**答案：C**

- **A：** 錯誤。RDS 提供 SQL relational contract，不能直接取代 Kafka 的 log、partition 與 consumer-group 行為。
- **B：** 錯誤。SQS 適合 work queue；其消費、重播與 ordering contract 與 Kafka 不同，不能只因較 managed 就強行替換。
- **C：** 正確。Kafka 相容性是 hard constraint；MSK 減少 broker 基礎維運，同時保留需要的 protocol 與 ecosystem。
- **D：** 錯誤。Fargate 執行 containers，但不自動提供 managed Kafka control/data plane。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[What is Amazon MSK?](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)、[AWS Fargate for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

### 練習題 3｜SAP｜Managed service adoption 前的 escape hatch

企業準備把關鍵訂單資料庫移到 managed engine。董事會要求未來若遇到不支援的功能、區域限制或不可接受的成本，必須有可執行的離開路徑。遷移前最重要的設計產物是什麼？

A. 只保留每日 snapshot；只要有備份，就能證明任意目標 engine 都可直接還原
B. 記錄資料格式、功能相容性、quota、替代目標與退出門檻，並定期演練匯出、切換與對帳
C. 先申請最大的 service quota，因為 quota 增加能消除所有功能與相容性差異
D. 禁止使用任何 AWS-specific 能力，因為 portability 等於只能採最低共同功能；並把跨engine restore與cutover驗證排到真正觸發退出時才執行，以降低目前投資

**答案：B**

- **A：** 錯誤。備份只證明存在 recovery point；沒有目標相容性與 restore test，不能證明可遷移。
- **B：** 正確。可攜性要被具體化成格式、相容性、觸發條件、測試與資料對帳，而不是抽象口號。
- **C：** 錯誤。Quota 處理數量上限，不會補上 engine feature、資料格式或法規差距。
- **D：** 錯誤。完全放棄平台能力會犧牲價值；escape hatch 的重點是了解 lock-in 與可接受的轉換成本。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 4｜SAA｜RDS production contract 的具體設定

一套 RDS PostgreSQL 訂單系統要求同 Region 的資料庫高可用、可回到 20 分鐘前、使用 customer managed KMS key，且只允許 application security group 連線。哪一組設定最完整？

A. 只增加 instance class；較大的 instance 會同時提供跨 AZ failover、PITR 與 network isolation
B. 使用預設 subnet、預設 SG 與預設 KMS 行為，因 resource 建立成功已證明 production readiness
C. 建立 read replica、停用 automated backups，並開放 public access 方便故障時連線
D. Multi-AZ + PITR + CMK + private DB subnets，SG只允許application SG

**答案：D**

- **A：** 錯誤。Scale up 只改變容量，不能替代 HA、backup、KMS 與 SG 設計。
- **B：** 錯誤。預設值是待審查輸入；建立成功不代表符合 RPO、安全或維護需求。
- **C：** 錯誤。Read replica 主要處理 read scaling，停用備份會破壞 PITR；public access 也違反 network 限制。
- **D：** 正確。拓撲、資料保護、key、network、維護與觀測要一起形成可檢查的 production contract。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Configuring and managing a Multi-AZ deployment](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Working with automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)、[Control traffic to your AWS resources using security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

### 練習題 5｜SAP｜異質資料庫 schema conversion、資料複寫與可回復 cutover

公司要把 8 TB 商業資料庫遷移到不同 engine 的 Amazon RDS，停機窗口只有 20 分鐘；stored procedures、資料型別與 SQL 語意可能不相容。哪個 cutover 計畫最可信？

A. 先以 AWS SCT/DMS Schema Conversion 產生目標 schema，但不做持續資料複寫；在 20 分鐘窗口內再搬完 8 TB
B. 先用 DMS full load 搬資料；因 DMS 會自動修正所有 schema 與 application SQL，完成後直接切 DNS
C. Schema Conversion處理schema/code；DMS full load+CDC搬資料並驗證
D. 先建立目標 RDS 並長期 dual-write；不定義衝突、順序與 authoritative writer，切換時只比較兩邊 instance health；切換前僅以schema物件數與instance health抽樣，不執行stored procedure語意測試

**答案：C**

- **A：** 錯誤。Schema conversion 是必要步驟，但沒有預先複寫 8 TB，20 分鐘窗口通常無法完成資料搬移與驗證。
- **B：** 錯誤。DMS 的 data migration 不等於完整 schema/code conversion；異質引擎仍需處理 assessment action items 與 application 相容性。
- **C：** 正確。Schema Conversion 處理 schema/code 差異，DMS full load+CDC 壓低停機；對帳、writer freeze 與 rollback gate 才控制語意與切換風險。
- **D：** 錯誤。Dual-write 在有明確 ownership、ordering 與 reconciliation 時可能可用；缺少這些規則會產生不可判定的資料分歧。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Converting database schemas with DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion.html)、[What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)

### 練習題 6｜SAP｜Managed service 健康但 workload 失敗的診斷

RDS console 顯示資料庫 available，AWS Health 也沒有事件；但尖峰時 application 出現 timeout 與 too many connections。第一個合理的診斷方向是什麼？

A. 比較 client connection pool、DB connections、CPU/I/O、locks、quota、retry 與 downstream latency，找出 service health 之外的 workload bottleneck
B. 只要 status 是 available，就能排除 data-plane 與應用層問題，應忽略監控
C. 立即改成自管 EC2 database；managed service 的任何 timeout 都代表產品不適用；若connection數下降就直接升級instance class，不先分辨lock、pool或retry storm來源
D. 直接把 SG 開放到 0.0.0.0/0；timeout 通常代表 network 必須公開

**答案：A**

- **A：** 正確。Control-plane health 不代表 workload 的 connections、locks、I/O、quota 或 retry contract 健康。
- **B：** 錯誤。Available 只表示服務資源狀態，不是每個 query 或 dependency 的成功證明。
- **C：** 錯誤。應先定位瓶頸；不經證據更換平台可能保留同一資料模型或 client 問題。
- **D：** 錯誤。放寬 network 既不會增加 DB connection budget，也會擴大攻擊面。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Monitoring Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Monitoring.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜Managed 與 self-managed 的同 SLO TCO 比較

自管 Kafka 的 EC2 帳單比 MSK 報價低 18%。CFO 要求判斷是否應維持自管。哪個比較方式最有架構意義？

A. 只比較 broker 每小時單價，因人力與 outage 不屬於 architecture cost；另用過去一個月EC2利用率外推三年成本，不納入版本升級與on-call事件
B. 一律選自管；只要 EC2 單價較低，patch 與故障風險可忽略
C. 一律選 managed；managed service 在任何利用率下都必然較便宜
D. 相同SLO下比較自管與MSK的人力、事故、升級及遷移TCO

**答案：D**

- **A：** 錯誤。人力、值班、升級與事故是維持相同 SLO 所需的真實成本。
- **B：** 錯誤。單價沒有包含完整責任與風險，不能直接推導 TCO；這會把資料模型或相容性責任錯放給managed service，故障後仍缺少可執行的restore/cutover證據。
- **C：** 錯誤。Managed 可降低營運面，但在特定穩定高利用率或 feature gap 下未必總成本最低。
- **D：** 正確。只有在相同能力與 SLO 邊界下納入服務、營運、風險與轉換成本，才能做可辯護比較。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 8｜SAA｜最少營運負擔且滿足容器 contract 的選型

小型團隊已有標準 OCI container image。工作每天只在不規則時段執行，不能管理 worker nodes，也不需要 GPU、host daemon 或 privileged host access。哪個執行方案最符合需求？

A. 建立 Amazon MSK cluster，讓每個 broker 直接執行 application image
B. ECS on Fargate，設定task CPU/memory、IAM與network
C. 使用 Amazon RDS 執行 container，因 RDS 能管理任何長時間 process
D. 在固定 EC2 fleet 上自行管理 ECS capacity，因自管 nodes 一定比按 task 使用量更省

**答案：B**

- **A：** 錯誤。MSK 提供 Kafka brokers，不能取代 container runtime。
- **B：** 正確。Fargate 保留 container contract 並移除 EC2 node 管理；團隊仍須設定 task 與 network/IAM 邊界。
- **C：** 錯誤。RDS 執行資料庫 engine，不是通用 container scheduler。
- **D：** 錯誤。EC2-backed ECS 可在穩定高利用率或需要 host 控制時合理，但題目明確不要 node management 且工作不規則。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Fargate for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

### 練習題 9｜SAP｜跨帳號 managed-service portfolio 治理

企業有 80 個 AWS accounts 使用多種 RDS engines。平台團隊要降低 upgrade 與 quota 事故，同時保留 workload ownership。選擇兩項。

A. 以 Organizations/Config 等 guardrail 與證據集中發現偏差，但把資料模型、測試與 cutover 責任留給明確的 workload owner
B. 讓各 workload team 依產品需求自行選 engine/version，中央平台每季從帳單、support cases 與 incidents 回顧組合；版本例外與 quota 風險則由各團隊在升級前自行處理
C. 建立 approved engine/version 與 exception inventory，指派 workload owner，定期做 quota、backup/restore、upgrade wave 與 exit-path review
D. 讓中央團隊取得所有 account 的永久 AdministratorAccess，並直接修改 production schema
E. 只建立第二 Region 的空 VPC；這會自動處理所有 managed-service deprecation 與 rollback

**答案：A、C**

- **A：** 正確。中央 guardrail 與分散 ownership 可以同時存在；治理應提供邊界與 evidence，而不是無限權限。
- **B：** 錯誤。季度結果回顧保留 autonomy，卻太晚才暴露 unsupported version、集中到期與 quota 競爭；跨 80 個 accounts 仍需要可查詢的版本、例外與 owner inventory。
- **C：** 正確。Portfolio 治理需要版本、例外、quota、復原、升級與退出責任可見。
- **D：** 錯誤。永久廣權限擴大 blast radius，且中央平台不應接管 application schema 正確性。
- **E：** 錯誤。空 Region 不包含資料、capacity、keys、runbook 或 owner，不能處理版本生命週期。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[SEC01-BP01 Separate workloads using accounts](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_multi_accounts.html)、[Aggregating AWS Config data](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)、[What is Amazon Relational Database Service?](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)

### 練習題 10｜SAP｜Managed database 的 exit drill 與 cutover evidence

核心帳務已在 RDS 穩定運行。董事會要求每年證明：若成本或功能限制越過 exit trigger，可在 30 天內遷至核准替代 engine。哪兩項最能提供這項證據？

A. 只提高 RDS service quota；quota 足夠即可證明 engine portability
B. 在隔離環境執行 schema/code conversion action items、資料 export/full load+CDC，並以 row counts、checksums 與業務不變量驗證目標
C. 保留最近一次 snapshot 與架構圖，但不在替代 engine 執行 restore、conversion 或 reconciliation
D. 量測 cutover freeze、replication lag、DNS/client reconnect、rollback deadline 與 owner，並演練新舊 writer fencing
E. 把 production 改為永久雙寫兩個 engine，即使沒有 conflict resolution、成本上限或解除機制

**答案：B、D**

- **A：** 錯誤。Service quota 只處理資源上限，無法證明替代引擎的 schema、protocol 或 cutover 相容性。
- **B：** 正確。這直接驗證異質目標的 schema、資料與業務語意，而不是重複檢查目前 RDS 的 Multi-AZ 設定。
- **C：** 錯誤。Snapshot 與圖能支持現況復原，但不能證明不同 engine 可接受 schema、資料與 application semantics。
- **D：** 正確。可執行退出能力必須量到 writer authority、資料窗口、client 行為與有期限 rollback，而非只有 export 成功。
- **E：** 錯誤。受控 dual-write 可協助遷移，但無期限且無衝突規則會新增另一套 production 風險，不能視為 exit drill。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Converting database schemas with DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion.html)、[What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先選滿足需求的最高managed abstraction，同時確認limits、data portabil…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「自行營運基礎元件能獲得控制，但會承擔patch、HA、backup、upgrade與on-call。」，所以「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」能直接滿足它；若constraint改成「自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」。替代方案「自管適合供應商未支援的protocol、性能或合規需求，但要估完整人力成本。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「自行營運基礎元件能獲得控制，但會承擔patch、HA、backup、upgrade與on-call。」，排除會導致「把managed service當無限制黑盒，直到quota或feature gap才發現沒有替代方案。」的選項，再選「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先選滿足需求的最高managed abstraction，同時確認limits、data portability與離開路徑。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「buy undifferentiated operations; retain control over differentiating contracts」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 106 章　Decouple Independently Scalable Components

若前後端必須同步同時成功、同時擴展，一個慢元件會限制整體。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：圖片上傳後縮圖與內容審核可晚幾秒完成，不能拖慢upload response。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：若前後端必須同步同時成功、同時擴展，一個慢元件會限制整體。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon SQS如何接手工作，再看Amazon EventBridge何時更合適，最後用設定與考題驗證「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：圖片上傳後縮圖與內容審核可晚幾秒完成，不能拖慢upload response。

商業需求與不能妥協的限制
          ▼
[Amazon SQS：主要責任]
          │ 以managed queue解耦producer與consumer的時間和容量。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon EventBridge：以event bus路由AWS、SaaS與custom events到targets。
  · AWS Step Functions：以可視化state machine編排多步驟、retry、branch、parallel與human wo…
可移植原則：decoupling is independent change, scale, and failure

失敗時先找：只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon SQS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon SQS和Amazon EventBridge並不是兩個任意的產品名稱。前者適合本章，是因為「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」直接回應了眼前的問題；後者描述的「同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「decoupling is independent change, scale, and failure」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |

## 把全圖套進一個具體案例

**場景：** 圖片上傳後縮圖與內容審核可晚幾秒完成，不能拖慢upload response。

1. 故事的起點：圖片上傳後縮圖與內容審核可晚幾秒完成，不能拖慢upload response。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon SQS負責「以managed queue解耦producer與consumer的時間和容量。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EventBridge、AWS Step Functions各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon SQS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：若前後端必須同步同時成功、同時擴展，一個慢元件會限制整體。
- **具體例子／邊界：** 在「圖片上傳後縮圖與內容審核可晚幾秒完成，不能拖慢upload response。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EventBridge

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：decoupling is independent change, scale, and failure。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### eventual consistency

更新後不同副本可能暫時看到舊值，但在沒有新更新時最終收斂；application必須容忍stale reads與重複event。

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### Amazon EventBridge

- **功用：** 以event bus路由AWS、SaaS與custom events到targets。
- **底層機制：** Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。
- **關鍵設定：** event buses、rules/patterns、targets、input transformer、archive/replay、DLQ與resource policy。
- **選擇時機：** domain events、cross-account integration、content-based routing與scheduler。
- **替換時機：** 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

## 考前與實作時再查：設定操作手冊

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### Amazon EventBridge：逐項設定說明

#### `event buses`

- **控制什麼：** `event buses`定義event/notification送到哪些consumers，以及是否套用filter、保留payload或跨帳號分享。
- **何時需要：** 一個producer需要fan-out到多個consumer、告警對象或workflow入口時。
- **怎麼設定／驗證：** 建立target/subscription與filter，設定resource policy、retry/DLQ和owner；用匹配與不匹配event各測一次。
- **常見錯法：** 只建立topic/bus卻沒有可用target不會產生business effect；consumer仍需處理duplicate與schema evolution。

#### `rules/patterns`

- **控制什麼：** `rules/patterns`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「domain events、cross-account integration、content-based routing與scheduler。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EventBridge以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `targets`

- **控制什麼：** `targets`指定Amazon EventBridge讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `input transformer`

- **控制什麼：** `input transformer`控制model選擇/grounding、knowledge-base同步、event payload轉換或API consumer的quota/rate plan。
- **何時需要：** AI、event-driven或public API需要可版本化quality、資料新鮮度、payload contract或tenant限額時。
- **怎麼設定／驗證：** 鎖定model/version與eval，設定grounding threshold或sync schedule；event/API則定義transform schema、API key plan、quota與throttle。
- **常見錯法：** Model或sync成功不代表回答正確；input transform漏欄位會破壞consumer，usage plan也不能取代authentication/authorization。

#### `archive/replay`

- **控制什麼：** `archive/replay`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `DLQ`

- **控制什麼：** `DLQ`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「domain events、cross-account integration、content-based routing與scheduler。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EventBridge依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `resource policy`

- **控制什麼：** `resource policy`指定Amazon EventBridge讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

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

## 讀到這裡，請用自己的話說一次

1. Amazon SQS的責任：以managed queue解耦producer與consumer的時間和容量。
2. 底層機制：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
3. 第一個要看的設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
4. 選擇邏輯：以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。
5. 不要混淆：Amazon EventBridge的責任是「以event bus路由AWS、SaaS與custom events到targets。」；它不會自動取代Amazon SQS。
6. 替換訊號：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
7. 最常見錯法：只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。
8. 可移植原則：decoupling is independent change, scale, and failure。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 | domain events、cross-account integration、content-based routing與scheduler。 | 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。 | 只有當題目條件明確改變時才可能合理。 | 只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。」之間做選擇。
- 認得常考設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜同步回應所承諾的 durable boundary

使用者上傳影片後，API 必須在 300 ms 內回應「已接受」，轉碼可在數分鐘後完成，但上傳成功回應後不能遺失工作。API 應在什麼時點回應成功？

A. 每次查詢影片狀態也改成非同步，因 decoupling 表示不能有同步 read
B. 收到第一個 HTTP byte 就回應，即使檔案與工作都尚未持久化
C. 影片已可靠存放且轉碼工作已寫入 durable queue 後回應，另以狀態 API 或事件通知結果
D. 等三種轉碼完成後才回應成功，並以API timeout與較大的worker fleet維持300 ms目標

**答案：C**

- **A：** 錯誤。Decoupling 不禁止同步 read；要依使用者需要的保證選 contract。
- **B：** 錯誤。尚未跨過 durable acceptance boundary 就宣告成功，故障時會造成無法補償的遺失。
- **C：** 正確。同步回應承諾「資料與工作已可靠接受」，後續獨立工作以 status/event 呈現。
- **D：** 錯誤。同步完成可提供強完成語意，但數分鐘工作不可能穩定落在300 ms，且會把最慢consumer綁回上傳路徑。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 2｜SAA｜SQS competing-consumer work distribution

一批獨立縮圖工作要由 40 個 workers 共同處理；每個工作只需由一個 logical consumer 完成，失敗後可重試。哪個設計最符合需求？

A. worker 一收到 message 就先 delete，再開始轉碼，以避免 duplicate
B. SQS競爭消費；side effect commit後delete並做冪等
C. 以 retention period 取代 visibility timeout；retention 到期前 message 不會被其他 worker 看見；把偶發duplicate交由下游人工對帳，未建立穩定idempotency key與commit紀錄
D. 讓所有 workers 訂閱同一 SNS topic，確保每個縮圖被處理 40 次

**答案：B**

- **A：** 錯誤。處理前 delete 會在 worker crash 時永久遺失工作。
- **B：** 正確。SQS 可把工作分配給 competing consumers；visibility、delete-after-commit 與冪等性共同處理失敗。
- **C：** 錯誤。Retention 控制 message 可保存多久；visibility 控制 receive 後暫時不可見的時間。
- **D：** 錯誤。SNS pub/sub 會把副本推給 subscribers，適合 fan-out，不是每件工作只由一個 worker 完成。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

### 練習題 3｜SAA｜EventBridge content routing 與 per-consumer isolation

訂單服務會發布 OrderPlaced 事件。庫存、詐欺與分析三個團隊只想接收符合各自欄位條件的事件，且分析故障不能拖慢庫存。哪個架構最合理？

A. 讓訂單服務同步呼叫三個 API，任一 timeout 就整筆訂單失敗
B. 只建立一個共享 SQS queue，讓三個 consumer 競爭同一 message；各團隊仍可在中央函式內提交規則，但任何一方部署都需要整體一起發布
C. 把所有判斷放進一個大型 Lambda，再依序呼叫所有下游
D. EventBridge按內容fan-out；各團隊使用獨立SQS

**答案：D**

- **A：** 錯誤。同步 fan-out 在所有下游都必須參與訂單交易時可能合理；本題要求分析故障不能拖慢庫存，因此會形成不必要的共同可用性邊界。
- **B：** 錯誤。單一 SQS queue 適合 competing consumers；三個團隊需要各自收到事件副本與獨立 backlog，不能共用一次消費。
- **C：** 錯誤。集中 Lambda 可統一轉換，但依序呼叫仍讓三個團隊共用部署、容量與失敗邊界，沒有達成隔離。
- **D：** 正確。EventBridge rule 負責內容式 fan-out；各 consumer queue 的 visibility、retry 與 DLQ 則處理自己的工作失敗。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[EventBridge retry policy and dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)

### 練習題 4｜SAA｜Step Functions orchestration 選擇

貸款流程包含驗證、人工審核 callback、撥款與失敗時補償；流程可能等待數天，並需要可查詢的 execution history。哪個方案最直接？

A. 以Lambda保存目前步驟，人工審核期間定期延長函式執行與重試，完成後再繼續下一步
B. 只用 EventBridge rule 發布事件，假設 rule 會自動保存完整 business process state
C. 用Step Functions Standard保存callback、retry與補償狀態
D. 依賴 SQS message 的接收順序表示目前業務步驟，不保存 workflow state

**答案：C**

- **A：** 錯誤。Lambda適合短期計算；長達數天的等待與callback state應由持久workflow保存，而不是佔用函式執行。
- **B：** 錯誤。EventBridge 路由事實事件，但不自動協調整個流程的狀態與補償。
- **C：** 正確。Standard Workflow 適合長時間、可稽核、需要 callback 與錯誤處理的 orchestration。
- **D：** 錯誤。Queue order 不是多步驟流程狀態機，無法表達 branch、callback 與 compensation。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Choosing workflow type in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)

### 練習題 5｜SAA｜At-least-once 下的 duplicate 與 partial failure

SQS consumer 已向付款系統扣款，但在 DeleteMessage 前 process crash；visibility 到期後同一工作再次出現。應用如何避免重複扣款？

A. payment key冪等；commit後才delete message
B. 改成 FIFO queue 後移除所有 application idempotency，因 queue 可保證外部付款 side effect 只發生一次
C. 把 maxReceiveCount 設為 1，任何暫時錯誤都直接丟入 DLQ
D. 把 visibility timeout 設為 0，讓其他 consumer 更快重做

**答案：A**

- **A：** 正確。Queue delivery 與外部 commit 不是原子交易；冪等 key 才能讓重試安全。
- **B：** 錯誤。FIFO 的 deduplication/ordering 不會把任意外部付款 API 變成 exactly-once transaction。
- **C：** 錯誤。過早送 DLQ 會把可恢復錯誤變成人工積壓，也不修正扣款冪等性。
- **D：** 錯誤。Visibility 變短會增加並行重複處理，不解決已提交 side effect。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

### 練習題 6｜SAP｜非同步 handoff 的端到端診斷

Producer 的 SendMessage 成功率為 100%，但使用者仍沒有收到報表。哪個排查順序最能找出第一個 broken handoff？

A. 只重啟 producer；下游 metrics 與 DLQ 不需要檢查
B. 只看 producer CPU；SendMessage 成功已證明報表 side effect 完成；當queue depth下降就宣告成功，不比對downstream commit與使用者通知狀態
C. 先增加 queue retention，因保留更久必然能讓 consumer 正常
D. 沿 correlation ID 檢查 queue visible/in-flight/oldest age、receive/delete、consumer errors/throttles、DLQ 與 downstream commit/notification

**答案：D**

- **A：** 錯誤。症狀在後續 handoff，盲目重啟 producer 可能製造更多重複工作。
- **B：** 錯誤。SendMessage 只證明 queue 接受資料，不代表 consumer 與下游完成。
- **C：** 錯誤。Retention 延長保存時間，不增加 processing capacity，也不修正錯誤。
- **D：** 正確。逐跳觀察 acceptance、backlog、consumer 與 business commit，才能定位第一個失敗邊界。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAA｜非同步系統 polling、batch 與 workflow 成本

一個低流量 SQS worker 每秒 short poll，絕大多數請求為空；每筆 message 單獨觸發昂貴 downstream call。如何先降低無效成本而不改變業務語意？

A. 把 retention 設為最大值；message 保存較久會降低 receive API 次數
B. SQS long polling；batch對齊side effect
C. 把所有工作改成 Express Workflow，不管執行時間、at-least-once suitability 與 history 需求
D. 持續提高 poll 頻率，以空回應數量證明 queue 健康

**答案：B**

- **A：** 錯誤。Retention 與 polling 頻率無直接替代關係。
- **B：** 正確。Long polling 減少空 receive；合適 batch 可攤平呼叫成本，但仍須處理局部失敗。
- **C：** 錯誤。Workflow type 必須依 duration、execution semantics 與 observability 選擇，不能只為名稱替換。
- **D：** 錯誤。更頻繁空 poll 增加 API 與 worker 浪費，沒有提高服務率。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)、[Choosing workflow type in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜可獨立擴縮的圖片處理架構

上傳 API 尖峰每秒 2,000 張圖片，三種轉換各自速度不同；使用者只需立即得到 upload ID，之後查狀態。哪個方案最能獨立擴縮並隔離慢轉換？

A. S3經EventBridge/SNS fan-out到三個獨立queues
B. S3 保存原圖，S3 事件送至單一共享 queue；三種 consumer 競爭同一訊息並各自推測是否該處理
C. Upload API 同步啟動三種轉換並等待最慢結果，再以較大的 API timeout 吸收尖峰
D. S3 只發 EventBridge event 到三個直接 Lambda targets，不設任何 queue；即使個別轉換長期低於輸入率也不保留 backlog

**答案：A**

- **A：** 正確。顯式 fan-out 讓每種轉換收到同一上傳事件；獨立 queue、capacity 與狀態又隔離不同服務率和失敗。
- **B：** 錯誤。共享 queue 的 competing consumers 不會自動複製同一事件給三種轉換，可能造成某些轉換永遠收不到工作。
- **C：** 錯誤。同步方案在低流量、短任務時可行，但本題有每秒 2,000 張與不同服務率，會把上傳可用性綁到最慢轉換。
- **D：** 錯誤。直接 target 適合可在 retry window 內吸收的流量；持續 backlog 需要 durable consumer buffer 與完成狀態。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Scale an Auto Scaling group based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)、[Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[Fanout Amazon SNS notifications to Amazon SQS queues](https://docs.aws.amazon.com/sns/latest/dg/sns-sqs-as-subscriber.html)

### 練習題 9｜SAP｜跨帳號 event contract 演進

企業把 monolith 拆成跨帳號 event-driven services。要求 producer 與 consumers 可獨立部署，舊 consumer 在新欄位上線後仍可運作，失敗可重播且 owner 清楚。選擇兩項。

A. 建立向後相容且版本化的 event contract；optional field 可新增，破壞性變更另開版本與遷移窗口
B. 只增加 EventBridge target retry 次數，不保存 correlation、schema version 或 consumer completion evidence
C. 把所有 accounts 的 PutEvents 與管理 target 權限授予同一廣泛 role，再由 event pattern 取代 resource policy
D. 依賴 target DLQ 作為永久事件 archive；需要重跑時直接把 DLQ 視為依時間範圍重播全部成功與失敗事件的來源
E. 用 EventBridge archive 保存原始事件，事件 bus resource policy 限定可 PutEvents 的 accounts/principals；為 target retry/DLQ 與 replay 指定 owner

**答案：A、E**

- **A：** 正確。版本與相容規則讓 producer/consumer 不必同步部署，並避免新欄位直接破壞舊 consumer。
- **B：** 錯誤。Retry 可處理暫時 target failure，但沒有事件保存與完成證據時，無法支援受控 replay 或回答停在哪一站。
- **C：** 錯誤。Event pattern 決定路由內容，不授予 PutEvents；跨帳號仍要以 event-bus resource policy 限定 principal 與範圍。
- **D：** 錯誤。Target DLQ 保存無法投遞的事件，不包含成功事件，也不是 EventBridge archive 的時間範圍 replay 機制。
- **E：** 正確。Archive/replay、event-bus resource policy 與具名 recovery owner分別處理重播、跨帳號授權與營運責任。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[EventBridge retry policy and dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)、[Archiving and replaying Amazon EventBridge events](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html)、[Amazon EventBridge event-bus permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-bus-perms.html)

### 練習題 10｜SAP｜可復原 asynchronous processing 的必要組合

財務匯入 pipeline 使用 SQS 與多個 consumers。要求 worker crash 不遺失資料、duplicate 不重複入帳，並能回答每筆匯入停在哪一站。選擇兩項。

A. 把 retention 延長到 14 天，將原始 message ID 與 S3 匯入 manifest 保存供夜間批次比對；批次依 queue depth 與成功檔案數找缺口，再由值班人員重新送入未完成檔案
B. consumer 使用穩定 idempotency key，visibility/heartbeat 覆蓋工作，成功 commit 後 delete，重複失敗送入可管理的 DLQ
C. 在 producer、message、consumer 與 downstream commit 間傳遞 correlation/status evidence，對 age、error、DLQ 與未完成 business outcome 告警
D. 停用所有 retry，因 retry 是 duplicate 的唯一來源
E. 收到 message 立刻 delete，再執行 database commit

**答案：B、C**

- **A：** 錯誤。離線對帳有助於事後發現缺口，但沒有把 delete 綁在 downstream commit 之後，也沒有讓重送具 idempotency；worker crash 仍可能遺失或重複入帳。
- **B：** 正確。這組合使 at-least-once delivery 下的重試可安全收斂，並保存 poison message。
- **C：** 正確。End-to-end correlation 與 outcome signal 才能回答「接受了但尚未完成」的位置。
- **D：** 錯誤。停用 retry 會把暫時故障變成資料遺失，且其他來源仍可能 duplicate。
- **E：** 錯誤。Crash 發生於 delete 與 commit 之間時，工作會永久遺失。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以queue/event/API contract分離rate、deployment與failure，讓c…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「若前後端必須同步同時成功、同時擴展，一個慢元件會限制整體。」，所以「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」能直接滿足它；若constraint改成「同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」。替代方案「同步仍適合需要即時確認的短路徑，不必為所有呼叫引入eventual consistency。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「若前後端必須同步同時成功、同時擴展，一個慢元件會限制整體。」，排除會導致「只把同步request包進queue卻仍阻塞等待，增加元件但沒有真正解耦。」的選項，再選「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以queue/event/API contract分離rate、deployment與failure，讓consumer依自己capacity處理。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「decoupling is independent change, scale, and failure」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 107 章　Eliminate Single Points of Failure

單點不只是一台server，也可能是AZ、NAT、identity provider、deployment pipeline或人。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

把鏡頭拉到一個真實的production現場：架構圖有三台EC2，但所有流量與資料仍依賴單一AZ元件。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：單點不只是一台server，也可能是AZ、NAT、identity provider、deployment pipeline或人。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Availability Zones是這一章的入口，Elastic Load Balancing用來畫出邊界；主要方向「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：架構圖有三台EC2，但所有流量與資料仍依賴單一AZ元件。

商業需求與不能妥協的限制
          ▼
[Availability Zones：主要責任]
          │ 在同一Region內提供可彼此隔離的資料中心級failure domains。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Elastic Load Balancing：將連線或request分散到健康targets並隔離client與backend生命週期。
  · Amazon RDS：代管關聯式database engine的provisioning、patch、backup與failov…
可移植原則：availability is the product of every required dependency

失敗時先找：前端多AZ但database、NAT或KMS policy只有單一可用路徑。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Availability Zones有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Availability Zones和Elastic Load Balancing並不是兩個任意的產品名稱。前者適合本章，是因為「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」直接回應了眼前的問題；後者描述的「有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：前端多AZ但database、NAT或KMS policy只有單一可用路徑。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「availability is the product of every required dependency」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 |

## 把全圖套進一個具體案例

**場景：** 架構圖有三台EC2，但所有流量與資料仍依賴單一AZ元件。

1. 故事的起點：架構圖有三台EC2，但所有流量與資料仍依賴單一AZ元件。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Availability Zones負責「在同一Region內提供可彼此隔離的資料中心級failure domains。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Elastic Load Balancing、Amazon RDS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「前端多AZ但database、NAT或KMS policy只有單一可用路徑。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Availability Zones

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：單點不只是一台server，也可能是AZ、NAT、identity provider、deployment pipeline或人。
- **具體例子／邊界：** 在「架構圖有三台EC2，但所有流量與資料仍依賴單一AZ元件。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Elastic Load Balancing

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：前端多AZ但database、NAT或KMS policy只有單一可用路徑。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：availability is the product of every required dependency。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### failure domain

會因同一事件一起失效的資源集合，例如單一instance、AZ或Region。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### data plane

實際處理每個packet、request、message、query與資料讀寫的runtime路徑。

### listener

在load balancer指定protocol/port等待client connection的入口。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### Availability Zones

- **功用：** 在同一Region內提供可彼此隔離的資料中心級failure domains。
- **底層機制：** AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。
- **關鍵設定：** subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
- **選擇時機：** 幾乎所有production regional workload的第一層高可用設計。
- **替換時機：** 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。

### Elastic Load Balancing

- **功用：** 將連線或request分散到健康targets並隔離client與backend生命週期。
- **底層機制：** Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
- **關鍵設定：** scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- **選擇時機：** 多instance/task高可用入口與rolling deployment。
- **替換時機：** 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。

### Amazon RDS

- **功用：** 代管關聯式database engine的provisioning、patch、backup與failover。
- **底層機制：** DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
- **關鍵設定：** engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- **選擇時機：** 需要SQL transaction、joins、schema與managed operations。
- **替換時機：** 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。

## 考前與實作時再查：設定操作手冊

### Availability Zones：逐項設定說明

#### `subnet AZ`

- **控制什麼：** `subnet AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Availability Zones前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `Auto Scaling distribution`

- **控制什麼：** `Auto Scaling distribution`設定Availability Zones的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「幾乎所有production regional workload的第一層高可用設計。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `Multi-AZ`

- **控制什麼：** `Multi-AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Availability Zones前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `cross-zone load balancing`

- **控制什麼：** `cross-zone load balancing`控制load balancer/accelerator如何選target、跨AZ分流或把原始client/flow資訊傳給後端。
- **何時需要：** Backend需要來源IP、session affinity、均衡AZ容量，或virtual appliance需要透明flow metadata時。
- **怎麼設定／驗證：** 在Availability Zones listener/target-group/load-balancer attributes中設定，並以多AZ clients及backend logs驗證實際source與distribution。
- **常見錯法：** Cross-zone可能增加跨AZ費用；關閉preserve client IP或未解析Proxy Protocol會讓backend看到錯誤來源，GENEVE也不是一般app protocol。

#### `cross-AZ cost`

- **控制什麼：** `cross-AZ cost`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Availability Zones前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

### Elastic Load Balancing：逐項設定說明

#### `scheme`

- **控制什麼：** `scheme`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `listeners`

- **控制什麼：** `listeners`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「多instance/task高可用入口與rolling deployment。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Elastic Load Balancing的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `target groups`

- **控制什麼：** `target groups`指定Elastic Load Balancing讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `health checks`

- **控制什麼：** `health checks`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「多instance/task高可用入口與rolling deployment。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Elastic Load Balancing設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `cross-zone`

- **控制什麼：** `cross-zone`控制load balancer/accelerator如何選target、跨AZ分流或把原始client/flow資訊傳給後端。
- **何時需要：** Backend需要來源IP、session affinity、均衡AZ容量，或virtual appliance需要透明flow metadata時。
- **怎麼設定／驗證：** 在Elastic Load Balancing listener/target-group/load-balancer attributes中設定，並以多AZ clients及backend logs驗證實際source與distribution。
- **常見錯法：** Cross-zone可能增加跨AZ費用；關閉preserve client IP或未解析Proxy Protocol會讓backend看到錯誤來源，GENEVE也不是一般app protocol。

#### `deregistration delay`

- **控制什麼：** `deregistration delay`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多instance/task高可用入口與rolling deployment。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Elastic Load Balancing的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `idle timeout`

- **控制什麼：** `idle timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多instance/task高可用入口與rolling deployment。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Elastic Load Balancing的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

### Amazon RDS：逐項設定說明

#### `engine/version`

- **控制什麼：** `engine/version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `instance/storage`

- **控制什麼：** `instance/storage`選擇Amazon RDS的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `Multi-AZ`

- **控制什麼：** `Multi-AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon RDS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `backup retention`

- **控制什麼：** `backup retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon RDS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `maintenance window`

- **控制什麼：** `maintenance window`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon RDS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `parameter/option group`

- **控制什麼：** `parameter/option group`是一組可版本化的engine/runtime參數，會改變Amazon RDS的實際process行為。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「需要SQL transaction、joins、schema與managed operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `network`

- **控制什麼：** `network`指定Amazon RDS的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

## 讀到這裡，請用自己的話說一次

1. Availability Zones的責任：在同一Region內提供可彼此隔離的資料中心級failure domains。
2. 底層機制：AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。
3. 第一個要看的設定：subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
4. 選擇邏輯：列出每個critical path dependency，跨適當failure domain部署並測試自動替換。
5. 不要混淆：Elastic Load Balancing的責任是「將連線或request分散到健康targets並隔離client與backend生命週期。」；它不會自動取代Availability Zones。
6. 替換訊號：需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。
7. 最常見錯法：前端多AZ但database、NAT或KMS policy只有單一可用路徑。
8. 可移植原則：availability is the product of every required dependency。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 | 幾乎所有production regional workload的第一層高可用設計。 | 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 | 多instance/task高可用入口與rolling deployment。 | 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。 |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 | 需要SQL transaction、joins、schema與managed operations。 | 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。 | 只有當題目條件明確改變時才可能合理。 | 前端多AZ但database、NAT或KMS policy只有單一可用路徑。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。」之間做選擇。
- 認得常考設定：subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Critical-path dependency inventory

架構圖上有三台 EC2，因此團隊宣稱沒有單點。實際上三台都在同一 AZ，經同一 NAT appliance 呼叫單一 IdP，部署還需要一位員工手動批准。評估 SPOF 的正確方式是什麼？

A. Managed IdP 與人員不算 dependency，因此只需把 EC2 再加一台
B. 枚舉 ingress、compute、state、egress、identity、keys、DNS、deployment 與人工 authority，找出每個 required link 的單一 failure domain
C. 確認三台EC2分散在不同AZ後停止分析，將NAT、IdP與人工核准視為平台外部風險
D. 只檢查 database，因 network 與 control path 不會讓 application 中斷；並以三台instance的平均availability相乘估算整體服務，不另畫required dependency graph

**答案：B**

- **A：** 錯誤。Managed dependency 與人工 approval 都可能成為 critical path，不能因類型不同而忽略。
- **B：** 正確。Availability 受所有必要連結限制；inventory 必須包含 runtime、control 與人員依賴。
- **C：** 錯誤。Compute跨AZ只是其中一層；任何required egress、identity或authority仍可成為端到端單點。
- **D：** 錯誤。資料庫只是其中一站；route、key、identity 或 deploy authority 失效同樣會中斷服務。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)

### 練習題 2｜SAA｜AZ failure 後仍保有 compute capacity

Web tier 正常需要 8 台 instances。公司使用 3 個 AZ，要求任一 AZ 完全失效後，不等待新 capacity 也仍至少有 8 台健康 instances。哪個最低整數配置符合要求？

A. 每個 AZ 3 台，共 9 台；任一 AZ 失效後仍有 8 台
B. 兩個 AZ 各 4 台，第三個 AZ 0 台；cross-zone load balancing 會在空 AZ 建立 capacity
C. 單一 AZ 8 台，另外建立 snapshot；snapshot 等同即時 compute capacity
D. 每AZ 4台，共12；失一AZ仍有8台

**答案：D**

- **A：** 錯誤。失去一個 AZ 後只剩 6 台，不滿足不等待擴容的限制；它改善一個AZ或tier，卻未驗證剩餘容量、client reconnect與完整business transaction。
- **B：** 錯誤。Load balancer 只能分配到現有健康 capacity，不能在空 AZ 自動產生 instances。
- **C：** 錯誤。Snapshot 是恢復 artifact，不是 outage 當下可立即服務的容量。
- **D：** 正確。3×4=12，失去 4 台後剩 8 台；這是題目要求的預佈建 N+1 failure-domain capacity。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Regions and Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)、[Health checks for Application Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)

### 練習題 3｜SAA｜RDS HA 與 read scaling 拓撲辨識

訂單資料庫的主要需求是同 Region 自動 failover；另一個需求是把報表 read traffic 分流。哪個敘述最準確？

A. 只建立跨 Region read replica，就能取代所有同 Region HA 與自動 failover 設計
B. Daily snapshot 同時提供 live failover 與 read scaling，不需其他 topology
C. Multi-AZ保HA；read scaling另用可讀standby或read replica並評估lag
D. Traditional Multi-AZ standby 必然提供任意 read endpoint，read replica 也必然同步零資料損失

**答案：C**

- **A：** 錯誤。跨 Region replica 可參與 DR，但不能未經條件就取代 regional HA。
- **B：** 錯誤。Snapshot 是 point-in-time recovery，不是線上 standby 或 read endpoint。
- **C：** 正確。HA 與 read scale 是不同 contract，必須依實際 RDS deployment type 分開選擇。
- **D：** 錯誤。Traditional Multi-AZ instance standby 的主要用途是 HA，並非一般 read serving；read replicas 可有 replication lag。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Configuring and managing a Multi-AZ deployment](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Working with DB instance read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 練習題 4｜SAA｜避免 zonal egress choke point

Application instances 分散在三個 private subnets/AZ，但所有 0.0.0.0/0 都跨 AZ 指向 AZ-a 的單一 NAT Gateway。公司要求 AZ-a 故障時其他 AZ 仍可對外更新套件，並避免平時不必要 cross-AZ data path。應如何調整？

A. 每AZ一個NAT且subnet指同AZ；S3走gateway endpoint
B. 為 private instances 配 public IP，仍將 default route 指向 NAT Gateway；平時靠cross-zone路由使用該出口，故障時才建立其他AZ的替代NAT與routes
C. 保留單一 NAT Gateway，只增加 security-group outbound rule
D. 把 route table 全移除，因 security group 可以代替 routing

**答案：A**

- **A：** 正確。Per-AZ NAT 與同 AZ routes 降低 zonal 依賴及 cross-AZ path；endpoints 可進一步移除不必要 Internet egress。
- **B：** 錯誤。Public address 與 NAT path 混用不會形成清楚的 private egress contract，也未消除 route 單點。
- **C：** 錯誤。SG 允許封包不會建立健康下一跳；單一 zonal NAT 仍是共同依賴。
- **D：** 錯誤。SG 是 stateful filter，不負責選擇下一跳。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)、[Route tables for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)、[VPC endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)

### 練習題 5｜SAP｜Static stability 與 control-plane impairment

大型促銷期間，既有 application capacity 足以承受尖峰，但每個 request 都必須先呼叫 deployment API 查最新 target，且失敗時會建立新資源。若 control plane 受限，如何保住既有服務？

A. 對 management API 無限 retry，且每次 request 都重新做 control lookup；在management API失敗時回傳暫時錯誤，等待值班人員重新發布目前已知設定
B. 把所有 replacement 與 configuration 都延後到 outage 發生後才建立
C. 把所有 instances 放到同一 AZ，減少 control-plane 呼叫數
D. 預先建立必要 capacity/configuration，讓 data plane 使用已發布的本地/穩定狀態；control update 失敗時保留 last-known-good 並限制變更

**答案：D**

- **A：** 錯誤。無限 retry 可能造成 storm，且每 request lookup 讓健康 data plane 被 control plane 綁住。
- **B：** 錯誤。Outage 中依賴建立資源會把 control impairment 放入 recovery critical path。
- **C：** 錯誤。集中 AZ 會增加 failure scope，不能解決 control/data-plane coupling。
- **D：** 正確。Static stability 讓既有流量依靠預建 capacity 與已發布 state 繼續，而非臨時控制操作。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 6｜SAP｜Multi-AZ 標籤下的共同依賴診斷

服務標示為 multi-AZ，但 AZ-b 網路事故時全站中斷。ALB 在三個 AZ，EC2 targets 也分散。接下來最應檢查什麼？

A. 只降低 public DNS TTL；任何 multi-AZ outage 都只能由 DNS 解決
B. 查剩餘AZ容量、state、identity、egress與client reconnect
C. 只看 ALB health check；target healthy 就足以證明完整交易可成功
D. 先在AZ-b增加預留instances與subnet容量，假設故障期間仍能透過control plane成功啟動並加入targets；若targets都healthy就將事故歸因於client DNS，暫不檢查database與egress placement

**答案：B**

- **A：** 錯誤。DNS 可能是因素之一，但不能修正 zonal database、NAT、key 或 capacity dependency。
- **B：** 正確。Compute 分散不代表 state、identity、egress 或 client behavior 也分散；需檢查真正 critical path。
- **C：** 錯誤。Health endpoint 可能未驗證 database、identity 或 business transaction。
- **D：** 錯誤。預留與擴容可改善容量，但題目已是AZ網路事故；應先驗證剩餘AZ的既有capacity與共同依賴。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Health checks for Application Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)、[Configuring and managing a Multi-AZ deployment](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜Availability topology 的成本與 SLO 取捨

內部報表系統可接受 12 小時 RTO、24 小時 RPO，每月只使用兩次。團隊提議直接建兩個 Region 的 full-scale active-active stack。哪個決策方式較合理？

A. 依RTO/RPO與business impact比較各DR策略的風險調整TCO
B. 比較各策略的每GB backup費用後選最低者，將常駐capacity、演練人力與超過RTO的衝擊列為共同成本；每年再以一次未計時的restore演練確認資料可讀，不量測是否在12小時內恢復
C. Single-AZ 無 backup 已足夠，因系統使用頻率低
D. 只要 active-active 可用性最高，就不需評估 idle capacity 與資料衝突

**答案：A**

- **A：** 正確。可靠性投資應由 failure objective 與 business impact 驅動，選能達標的最低總成本方案。
- **B：** 錯誤。Backup單價只是DR成本的一部分；各策略的idle capacity、automation與failure impact並不相同。
- **C：** 錯誤。低使用頻率不消除資料保護與明確 RTO/RPO；此做法依賴事故期間的control-plane動作，無法證明既有data plane具有static stability。
- **D：** 錯誤。過度建置會增加固定成本、資料一致性與操作複雜度，仍須與目標比較。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜Regional highly available web application

公司要在單一 Region 建立 highly available shopping site。Web sessions 可移出 instances，database 必須自動 failover。哪個架構最符合需求？

A. 一個 AZ 的 ASG behind CloudFront，加上一個 Single-AZ database
B. 多 AZ EC2，但 session 只在 instance local disk，並用永久 stickiness 避免切換
C. 多 AZ ALB 與 stateless ASG，session 放入可用的外部 store，database 使用符合需求的 Multi-AZ deployment，並測 client reconnect
D. 只有 Route 53 health check，所有 compute 與 database 仍在單一 AZ

**答案：C**

- **A：** 錯誤。CloudFront 不會替單 AZ compute/database 建立 regional redundancy。
- **B：** 錯誤。Local session 與 stickiness 會使 target loss 造成使用者狀態遺失。
- **C：** 正確。Ingress、compute、session state 與 database 都有對應 HA boundary，並包含 failover 後 client 行為。
- **D：** 錯誤。DNS 偵測不能創造另一 AZ 的 runtime 或 state capacity。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Health checks for Application Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)、[Configuring and managing a Multi-AZ deployment](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 9｜SAP｜Zonal game day 與 recovery evidence

平台聲稱付款服務能承受任一 AZ failure。哪兩項 evidence 最能支持這個結論？

A. 只確認 resources 在 console 顯示 running
B. 以 Well-Architected review 與架構圖確認每層都橫跨三個 AZ，並保存各服務 SLA、Auto Scaling 最低容量與資料庫 Multi-AZ 設定；年度稽核再檢查資源是否仍符合圖面
C. 記錄 detection、traffic drain、client reconnect、queue/replica lag、capacity、rollback/failback 與具名 owner，並定期重演
D. 只引用每個 AWS service 的 SLA，未測 application transaction
E. 在有 stop condition 的 game day 中移除一個 AZ 的 targets/路徑，證明剩餘 capacity、state、egress 與 business success 仍達 SLO

**答案：C、E**

- **A：** 錯誤。Running 不代表可達、可寫、容量足夠或交易成功；此做法依賴事故期間的control-plane動作，無法證明既有data plane具有static stability。
- **B：** 錯誤。設定與 SLA 能證明設計意圖，不能證明 AZ impairment 時流量排空、剩餘容量、client reconnect、state 與端到端付款結果真的在 SLO 內。
- **C：** 正確。可重演 runbook、時間分解、owner 與 failback evidence 才構成營運能力。
- **D：** 錯誤。個別 SLA 不能合成應用端到端結果，也不反映依賴配置；這只增加局部capacity或偵測，沒有移除state、identity、egress或人工authority上的共同單點。
- **E：** 正確。受控故障與 business outcome 能驗證 critical path，而非只驗證資源存在。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 10｜SAP｜移除兩個獨立 critical-path SPOF

一個 API 已跨三 AZ 部署，但資料庫是 Single-AZ，且所有 KMS decrypt 依賴一個由單一人員手動切換的自建 proxy。選擇兩項最直接移除 critical-path SPOF 的措施。

A. 把 key path 改為具冗餘與最小權限的服務/架構，預先建立授權與自動 recovery，並消除單一人工批准
B. 建立第二 Region 的空 subnet，但不複寫資料或配置
C. 把 authorization decision 與最近一次成功寫入結果快取 24 小時，proxy 故障時由 API instances 繼續讀取舊決策並接受新交易，待人工切換完成後再批次同步 database
D. 改用符合 RTO 的 Multi-AZ data topology，測 failover endpoint、application reconnect 與資料復原
E. 再增加同 AZ API instances，但保留 Single-AZ database

**答案：A、D**

- **A：** 正確。Key/approval path 也是 required link，必須有冗餘、預授權與可自動執行的 recovery。
- **B：** 錯誤。空 network 沒有 state、keys、capacity 或 traffic path。
- **C：** 錯誤。短暫使用經風險評估的 stale read 有時可降級服務，但把授權與新交易都建立在 24 小時舊狀態上會產生越權與多重 writer；它沒有移除 key proxy 或 Single-AZ database 的單點。
- **D：** 正確。HA data topology 與實測 reconnect 直接處理資料庫單點。
- **E：** 錯誤。增加 stateless tier capacity 不會修正 data-tier SPOF。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configuring and managing a Multi-AZ deployment](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「列出每個critical path dependency，跨適當failure domain部署並測試自動…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「單點不只是一台server，也可能是AZ、NAT、identity provider、deployment pipeline或人。」，所以「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」能直接滿足它；若constraint改成「有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」。替代方案「有些control plane可接受較長恢復，data plane則需持續服務，兩者SLO不同。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「前端多AZ但database、NAT或KMS policy只有單一可用路徑。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「單點不只是一台server，也可能是AZ、NAT、identity provider、deployment pipeline或人。」，排除會導致「前端多AZ但database、NAT或KMS policy只有單一可用路徑。」的選項，再選「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「列出每個critical path dependency，跨適當failure domain部署並測試自動替換。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「availability is the product of every required dependency」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 108 章　Blast Radius 與 Cell-based Architecture

全域共享資源提高效率，也讓單一bug或overload影響所有租戶。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

如果今天由你值班，收到的需求可能是這樣：SaaS需讓單一region或enterprise tenant事故最多影響一小部分使用者。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：全域共享資源提高效率，也讓單一bug或overload影響所有租戶。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Organizations承接主要責任，以Amazon Route 53檢查替代條件，並用「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：SaaS需讓單一region或enterprise tenant事故最多影響一小部分使用者。

商業需求與不能妥協的限制
          ▼
[AWS Organizations：主要責任]
          │ 集中建立accounts、OU、政策與consolidated billing。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon Route 53：提供authoritative DNS、health check與多種流量政策。
  · Amazon DynamoDB：提供managed key-value/document database與單位毫秒scale。
可移植原則：partition failure domains before the incident chooses them

失敗時先找：Shared queue/database沒有tenant限額，一個客戶拖垮全平台。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問AWS Organizations有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Organizations和Amazon Route 53並不是兩個任意的產品名稱。前者適合本章，是因為「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」直接回應了眼前的問題；後者描述的「更多cells增加容量浪費、資料搬移與控制面複雜度。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Shared queue/database沒有tenant限額，一個客戶拖垮全平台。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「partition failure domains before the incident chooses them」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |

## 把全圖套進一個具體案例

**場景：** SaaS需讓單一region或enterprise tenant事故最多影響一小部分使用者。

1. 故事的起點：SaaS需讓單一region或enterprise tenant事故最多影響一小部分使用者。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Organizations負責「集中建立accounts、OU、政策與consolidated billing。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Route 53、Amazon DynamoDB各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Shared queue/database沒有tenant限額，一個客戶拖垮全平台。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「單一account內的日常permission仍用IAM；不要在management account執行workloads。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Organizations

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：全域共享資源提高效率，也讓單一bug或overload影響所有租戶。
- **具體例子／邊界：** 在「SaaS需讓單一region或enterprise tenant事故最多影響一小部分使用者。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Route 53

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：更多cells增加容量浪費、資料搬移與控制面複雜度。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Shared queue/database沒有tenant限額，一個客戶拖垮全平台。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：partition failure domains before the incident chooses them。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

## 考前與實作時再查：設定操作手冊

### AWS Organizations：逐項設定說明

#### `roots/OUs/accounts`

- **控制什麼：** `roots/OUs/accounts`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `SCP/RCP/tag/backup policies`

- **控制什麼：** `SCP/RCP/tag/backup policies`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `delegated admins`

- **控制什麼：** `delegated admins`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `trusted access`

- **控制什麼：** `trusted access`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `billing sharing`

- **控制什麼：** `billing sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

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

### Amazon DynamoDB：逐項設定說明

#### `PK/SK`

- **控制什麼：** `PK/SK`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon DynamoDB的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `on-demand/provisioned`

- **控制什麼：** `on-demand/provisioned`決定Amazon DynamoDB如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `RCU/WCU`

- **控制什麼：** `RCU/WCU`決定Amazon DynamoDB如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `GSI/LSI`

- **控制什麼：** `GSI/LSI`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon DynamoDB的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `consistency`

- **控制什麼：** `consistency`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Amazon DynamoDB的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

#### `TTL`

- **控制什麼：** `TTL`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon DynamoDB的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `Streams`

- **控制什麼：** `Streams`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon DynamoDB持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `PITR`

- **控制什麼：** `PITR`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `transactions`

- **控制什麼：** `transactions`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Amazon DynamoDB的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

## 讀到這裡，請用自己的話說一次

1. AWS Organizations的責任：集中建立accounts、OU、政策與consolidated billing。
2. 底層機制：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
3. 第一個要看的設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
4. 選擇邏輯：以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。
5. 不要混淆：Amazon Route 53的責任是「提供authoritative DNS、health check與多種流量政策。」；它不會自動取代AWS Organizations。
6. 替換訊號：單一account內的日常permission仍用IAM；不要在management account執行workloads。
7. 最常見錯法：Shared queue/database沒有tenant限額，一個客戶拖垮全平台。
8. 可移植原則：partition failure domains before the incident chooses them。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 更多cells增加容量浪費、資料搬移與控制面複雜度。 | 只有當題目條件明確改變時才可能合理。 | Shared queue/database沒有tenant限額，一個客戶拖垮全平台。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「更多cells增加容量浪費、資料搬移與控制面複雜度。」之間做選擇。
- 認得常考設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：單一account內的日常permission仍用IAM；不要在management account執行workloads。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability；SAP-4.3 Determine a new architecture for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAP｜Cell partition key 與最大影響範圍

SaaS 有 12,000 個 tenants，要求單次 runtime 故障最多影響約 200 個 tenants。設計 cell boundary 時第一個必要決策是什麼？

A. 讓所有 tenants 共用一個 database 與 queue，再把 dashboard 分成多個 cell 名稱
B. 只建立 Organizations OU；OU 會自動成為 application runtime shard
C. 每個 request 隨機選 cell，且同一 tenant 的資料同時寫入全部 cells
D. 定義穩定tenant-to-cell mapping、每cell容量上限與authoritative state ownership

**答案：D**

- **A：** 錯誤。命名不會消除共享 bottleneck；此方案可能提升平均吞吐，但shared pool或global dependency仍能把單一tenant/cell故障擴散到全體。
- **B：** 錯誤。OU 是 governance grouping，不是 runtime routing/data partition。
- **C：** 錯誤。隨機選cell使同一tenant缺乏穩定state locality；把資料同步寫入所有cells又把每個cell故障擴散成全域寫入風險。
- **D：** 正確。Cell 必須有穩定 membership、容量與 state boundary，才能限制影響範圍。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[REL10-BP03 Use bulkhead architectures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_use_bulkhead.html)

### 練習題 2｜SAP｜Thin cell router

全域 router 依 tenant ID 將 request 送到 cell。哪個設計最不容易讓 router 變成新的 mega-cell？

A. Request 到達時由 router 同步建立新 cell 與 database
B. 只部署一個 router instance，以免 mapping cache 不一致
C. 只在tenant所屬cell內選健康endpoint；搬cell須先遷移state
D. Router 執行所有訂單 transaction，並同步查詢每個 cell 才決定結果

**答案：C**

- **A：** 錯誤。把 provisioning control plane 放進 request path 會降低 static stability。
- **B：** 錯誤。單一router instance是SPOF；mapping consistency應靠版本化資料與cache更新策略，而不是取消水平擴展。
- **C：** 正確。Thin router可水平擴展，但只能在已指派cell內做健康轉送；跨cell relocation必須先搬移authoritative state、fence舊writer並原子更新mapping。
- **D：** 錯誤。厚重業務邏輯與跨 cell 查詢擴大 shared failure。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Serverless cell router architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/serverless-cell-router-architecture.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)

### 練習題 3｜SAP｜Cell state isolation

團隊建立四個 compute cells，但所有寫入仍經同一個 global database connection pool 與 shared queue。最準確的評估是什麼？

A. shared DB pool/queue仍跨cell；應切分state與capacity
B. 把 cells 放入同一 account 便能自動切割 database connections
C. 只需為 shared queue 增加 retention，即可形成四個 failure domains
D. 已完全隔離；只要 compute stack 名稱不同，共享 state 不影響 blast radius；再以per-cell compute autoscaling吸收共享database與queue的contention，不設定partition quota

**答案：A**

- **A：** 正確。Cell isolation 要涵蓋 compute、state、queue 與 capacity，不只是部署單位。
- **B：** 錯誤。Account placement 不會自動 partition application state。
- **C：** 錯誤。Retention 不會分割 consumers 或 downstream capacity。
- **D：** 錯誤。共享 pool/queue/database 可讓單一 overload 或故障影響所有 cells。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[REL10-BP03 Use bulkhead architectures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_use_bulkhead.html)

### 練習題 4｜SAP｜Account boundary 與 application cell boundary

安全團隊把每個 business unit 放入不同 AWS account，並套用 SCP，於是宣稱已完成 cell-based architecture。還缺少什麼？

A. 啟用 consolidated billing，billing aggregation 會隔離 database state
B. SCP 中加入 DNS record，SCP 就能分配 runtime traffic
C. 把 accounts 放入同一 OU，OU 即可提供 per-tenant capacity
D. 另外設計 tenant mapping/router、per-cell compute/data/queue/quota、獨立 alarms/deployments 與故障處置

**答案：D**

- **A：** 錯誤。Billing 聚合不改變 failure domain。
- **B：** 錯誤。SCP 限制 API 權限，不是 application router。
- **C：** 錯誤。OU只組織accounts並承載SCP；它不建立tenant routing、per-cell state partition、capacity quota或noisy-neighbor admission control。
- **D：** 正確。Account 是強治理邊界；cell 還需要 application traffic、state 與 capacity isolation。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[SEC01-BP01 Separate workloads using accounts](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_multi_accounts.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)

### 練習題 5｜SAA｜Noisy-neighbor admission 與 attribution

單一 enterprise tenant 的批次工作吃滿共享 standard SQS queue 的 worker concurrency，使 quiet tenants 的 dwell time 暴增。第一個有效改善是什麼？

A. 為每個 tenant 建立獨立 standard queue，但仍讓所有 queues 共用無上限的單一 downstream connection pool
B. standard SQS用tenant MessageGroupId啟用fair queue；hard quota另做
C. 只依 aggregate queue depth 擴充 workers，不保留 tenant attribution，也不設定 database connection budget；把quiet tenant超時視為可接受trade-off，因總體throughput與worker利用率已經提高
D. 改成 FIFO queue 並讓所有 tenants 使用同一 MessageGroupId，以全域順序換取租戶公平與最高平行度

**答案：B**

- **A：** 錯誤。Per-tenant queues 改善入口隔離，但無上限共享 downstream 仍可讓一個 tenant 耗盡所有連線。
- **B：** 正確。Standard queue 的 MessageGroupId 可識別 tenant 並啟用 fair queue；它改善 quiet-group dwell time，但 hard rate cap 仍需 admission/concurrency 控制。
- **C：** 錯誤。Aggregate autoscaling 可增加總吞吐，但看不到 noisy tenant，也可能把壓力直接推向共同 database。
- **D：** 錯誤。FIFO 單一 group 會序列化全部租戶；只有在全域順序比吞吐與租戶隔離更重要時才可能合理。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS fair queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)

### 練習題 6｜SAP｜Cell failure 跨全站的診斷

Cell C 的 deployment 出錯，理論上只應影響 C；實際上全部 customers 都 timeout。哪個調查最有效？

A. 查global router、identity、config、shared DB/queue
B. 把更多 tenants 指派到 C，觀察問題是否平均；若global error rate仍高就同步回滾全部cells，不保留deployment scope與correlation證據
C. 同時回滾所有 cells，且不保留哪個 cell 先失敗的 evidence
D. 先比較Cell C與其他cells的EC2 CPU及error rate，若C最差就把事故限制判定為有效

**答案：A**

- **A：** 正確。全站症狀通常指向 global/shared dependency 或錯誤 rollout scope。
- **B：** 錯誤。把更多tenant送進故障cell會擴大blast radius；應先保留per-cell證據並定位越過cell boundary的shared dependency或rollout。
- **C：** 錯誤。全 fleet 動作破壞隔離且失去因果證據；這改變部署名稱或compute數量，卻沒有切割tenant mapping、authoritative state與capacity ownership。
- **D：** 錯誤。Cell metrics是起點，但全站timeout表示仍需追global router、identity、configuration或fleet-wide rollout。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜Cell 數量與 fixed-headroom 成本

架構師想把 1 個大 cell 拆成 200 個小 cells，理由是 cells 越多成本必然越低。應如何評估？

A. 只計算每個 cell 的 EC2 單價，不計 minimum headroom 與 data movement
B. 直接維持單一 cell，因 incident impact 不屬於成本
C. 模型化每 cell 固定容量、部署/觀測、資料複製、mapping 與搬移成本，再與可接受 blast radius 和 rollout 安全收益比較
D. 直接採最大 cell 數，因 duplication 永遠免費

**答案：C**

- **A：** 錯誤。大量 cells 的固定 headroom 與營運面可能主導成本。
- **B：** 錯誤。大範圍事故與 risky rollout 也有 business cost。
- **C：** 正確。Cell size 是 isolation benefit 與 duplicated overhead 的量化取捨。
- **D：** 錯誤。每增加一個cell都會複製最低容量、監控與部署成本；若沒有tenant skew與evacuation需求，200個cells可能比所需blast radius更昂貴。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜大型 tenant isolation

某 tenant 的流量是其他租戶總和的三倍，且要求維護時不影響一般租戶。哪個方案最合適？

A. 保留共享 hot partition，只提高所有 tenants 的 timeout
B. 維持同一 client routing contract，將 tenant pin 到有獨立 capacity/state quota 的 cell，並以分波部署與獨立 alarms 管理
C. 給 tenant AWS account AdministratorAccess 讓它自行調整共享 production
D. 只為該 tenant 建新 DNS 名稱，但後端仍共用同一 queue/database pool

**答案：B**

- **A：** 錯誤。Timeout 不會移除 capacity contention。
- **B：** 正確。Stable routing 加獨立 capacity/state/deploy boundary 能隔離 tenant。
- **C：** 錯誤。AdministratorAccess只擴大控制權，不能把共享hot partition、queue配額或database connections切成該tenant的獨立capacity boundary。
- **D：** 錯誤。新DNS名稱只改入口；共享queue、database pool與capacity仍讓heavy tenant影響其他tenant。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)

### 練習題 9｜SAP｜Cell-by-cell rollout operating model

平台要部署共用 cell template 的新版本，並把壞版本影響限制在最小範圍。選擇兩項。

A. 建立統一 global dashboard 與跨 cells 的平均 error/latency gate，當整體指標正常就平行更新全部 cells；部署系統保存共同版本與一次全域 rollback artifact
B. 保留 cell-specific owner、alarm、rollback artifact 與前後版本相容期，並避免 global layer 同步做破壞性變更
C. 允許各 cell 無 inventory 地永久 drift
D. 一次更新所有 cells，因版本一致比 blast radius 更重要
E. 以版本化 stack/template 先部署低風險 canary cell，依 business/error/capacity gate 再分 waves 推進

**答案：B、E**

- **A：** 錯誤。共同版本與 rollback artifact 有價值，但平均指標會掩蓋單一 cell 或 tenant 的退化；平行更新也讓 cell 無法作為限制未知版本 blast radius 的 rollout unit。
- **B：** 正確。Per-cell evidence、owner 與相容 rollback 讓分波部署可操作。
- **C：** 錯誤。永久drift使template測試結果、相容窗口與rollback artifact不可重現；例外也應有inventory與到期條件。
- **D：** 錯誤。All-at-once 會消除 cell 的 blast-radius 優勢。
- **E：** 正確。Cell 是天然 rollout unit，可先限制未知風險。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 10｜SAP｜Cell evacuation、tenant relocation 與 global-state exception

Cell C 將停機維護，需把 300 個 tenants 遷到 Cell D；每個 tenant 的 authoritative state 平時只在所屬 cell。哪兩項是安全 evacuation 的必要條件？

A. 預留 D 的 evacuation capacity，先複製並驗證 tenant state，以版本化 mapping 做 writer fencing/cutover，再監看業務結果
B. 只增加 C 的 DNS TTL；DNS cache 會自動把 tenant state 搬到 D
C. 定義 tenant move protocol、rollback window 與 reconciliation；global identity/config 必須證明不是同步單點或具可用的 local fallback
D. 把 tenant records 搬入跨 cells 共用的同步 database writer，router 可在任一 cell 健康檢查失敗時立即改送其他 cell；以 global transaction lock 維持單一 writer，省去逐 tenant 複製與 mapping cutover
E. 先把 router mapping 指向 D，再開始複製 state；寫入失敗時由 clients 自行重試直到資料出現

**答案：A、C**

- **A：** 正確。Evacuation 必須同時有目標 headroom、state readiness、原 writer fencing 與原子化/版本化 routing cutover。
- **B：** 錯誤。DNS 只影響名稱解析與快取時間，不會複製 tenant data、capacity 或更新 authoritative mapping。
- **C：** 正確。可回復搬移需要具名 protocol 與對帳，且 global dependencies 不能在 cell failure 時把全部 cells 一起拖垮。
- **D：** 錯誤。單一 global writer 簡化 authority，卻把所有 cells 的 availability 與 latency 綁在同一資料路徑，重新形成 mega-cell；本題要求的是保留 cell 隔離下的安全 evacuation。
- **E：** 錯誤。先切 routing 會把 requests 送往尚未擁有 state 的 cell；client retry 不能建立 writer authority 或資料完整性。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)、[Serverless cell router architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/serverless-cell-router-architecture.html)、[REL10-BP03 Use bulkhead architectures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_use_bulkhead.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以account、Region、cell、tenant shard分隔容量與deployment，glob…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「全域共享資源提高效率，也讓單一bug或overload影響所有租戶。」，所以「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」能直接滿足它；若constraint改成「更多cells增加容量浪費、資料搬移與控制面複雜度。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」。替代方案「更多cells增加容量浪費、資料搬移與控制面複雜度。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Shared queue/database沒有tenant限額，一個客戶拖垮全平台。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「全域共享資源提高效率，也讓單一bug或overload影響所有租戶。」，排除會導致「Shared queue/database沒有tenant限額，一個客戶拖垮全平台。」的選項，再選「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以account、Region、cell、tenant shard分隔容量與deployment，global layer只做必要routing。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「partition failure domains before the incident chooses them」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 109 章　Queue 吸收 Burst，而非無限 Overload

Queue能把短期arrival spike平滑成可處理速率，但長期超載只會累積過期工作。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

故事從一個看似簡單的需求開始：Producer長期每秒一萬件，consumer只能八千，queue每天持續增長。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：Queue能把短期arrival spike平滑成可處理速率，但長期超載只會累積過期工作。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

Queue像餐廳的出單夾：前台可以先收下工作，廚房按能力處理，失敗的單則移到另一個夾子調查。 出單夾不會創造處理能力，也不保證每張單只被拿一次，所以consumer仍需冪等與backpressure。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon SQS會是本章的主要角色，Amazon Kinesis則幫我們看清邊界。方向是「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Producer長期每秒一萬件，consumer只能八千，queue每天持續增長。

商業需求與不能妥協的限制
          ▼
[Amazon SQS：主要責任]
          │ 以managed queue解耦producer與consumer的時間和容量。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon Kinesis：保存可重播、按partition key排序的即時event log。
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…
可移植原則：buffers buy time; they do not create throughput

失敗時先找：只看queue depth不看age與deadline，系統仍處理已無價值的request。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon SQS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon SQS和Amazon Kinesis並不是兩個任意的產品名稱。前者適合本章，是因為「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」直接回應了眼前的問題；後者描述的「增加retention爭取處理時間，但不會提升consumer capacity。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只看queue depth不看age與deadline，系統仍處理已無價值的request。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「buffers buy time; they do not create throughput」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| Amazon Kinesis | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |

## 把全圖套進一個具體案例

**場景：** Producer長期每秒一萬件，consumer只能八千，queue每天持續增長。

1. 故事的起點：Producer長期每秒一萬件，consumer只能八千，queue每天持續增長。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon SQS負責「以managed queue解耦producer與consumer的時間和容量。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Kinesis、Amazon CloudWatch各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只看queue depth不看age與deadline，系統仍處理已無價值的request。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon SQS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Queue能把短期arrival spike平滑成可處理速率，但長期超載只會累積過期工作。
- **具體例子／邊界：** 在「Producer長期每秒一萬件，consumer只能八千，queue每天持續增長。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Kinesis

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：增加retention爭取處理時間，但不會提升consumer capacity。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只看queue depth不看age與deadline，系統仍處理已無價值的request。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：buffers buy time; they do not create throughput。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### Amazon Kinesis

- **功用：** 保存可重播、按partition key排序的即時event log。
- **底層機制：** Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。
- **關鍵設定：** on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
- **選擇時機：** 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。
- **替換時機：** 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

## 考前與實作時再查：設定操作手冊

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### Amazon Kinesis：逐項設定說明

#### `on-demand/provisioned mode`

- **控制什麼：** `on-demand/provisioned mode`決定Amazon Kinesis如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `shards`

- **控制什麼：** `shards`設定Amazon Kinesis的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon Kinesis的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `partition key`

- **控制什麼：** `partition key`設定Amazon Kinesis的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `enhanced fan-out`

- **控制什麼：** `enhanced fan-out`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon Kinesis持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Kinesis指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `iterator age`

- **控制什麼：** `iterator age`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon Kinesis持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

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

1. Amazon SQS的責任：以managed queue解耦producer與consumer的時間和容量。
2. 底層機制：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
3. 第一個要看的設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
4. 選擇邏輯：使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。
5. 不要混淆：Amazon Kinesis的責任是「保存可重播、按partition key排序的即時event log。」；它不會自動取代Amazon SQS。
6. 替換訊號：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
7. 最常見錯法：只看queue depth不看age與deadline，系統仍處理已無價值的request。
8. 可移植原則：buffers buy time; they do not create throughput。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| Amazon Kinesis | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 | 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。 | 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 增加retention爭取處理時間，但不會提升consumer capacity。 | 只有當題目條件明確改變時才可能合理。 | 只看queue depth不看age與deadline，系統仍處理已無價值的request。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「增加retention爭取處理時間，但不會提升consumer capacity。」之間做選擇。
- 認得常考設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Arrival rate 與 service rate

Producer 長期每秒送 10,000 件，consumer fleet 長期最多完成 8,000 件；queue retention 為 4 天。若不改任何 rate，會發生什麼？

A. SQS 會自動完成超過 consumer capacity 的 business work
B. Queue depth 會固定，因 distributed queue 能永久隱藏 λ 大於 μ
C. backlog每秒淨增2,000，oldest age持續上升
D. 提高 retention 會自動把 consumer capacity 變成每秒 10,000

**答案：C**

- **A：** 錯誤。SQS 儲存與傳遞 message，不執行 application side effect。
- **B：** 錯誤。Queue只能暫存差額；當arrival每秒10,000而service每秒8,000時，backlog每秒增加2,000，最舊訊息最後會逼近四天retention。
- **C：** 正確。持續 arrival 大於 service 時 backlog 必然成長。
- **D：** 錯誤。Retention 改變保存時間，不改變 service rate。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 2｜SAA｜Queue age 與 business deadline

兩個 queues 都有 50,000 messages。Queue A 每件 10 ms 且可等一小時；Queue B 每件 5 秒且訂單須 3 分鐘內完成。最有判斷力的訊號組合是什麼？

A. 以oldest age/deadline為主，搭配depth、完成率與consumer errors
B. 只看 retention；retention 就等於使用者 SLO
C. 只以visible queue depth除以目前worker數；兩個queues數量相同時就設定相同告警門檻
D. 只看 NumberOfMessagesReceived，並把它當成 unique successful commits

**答案：A**

- **A：** 正確。同一 depth 在不同 service time/deadline 下代表不同風險。
- **B：** 錯誤。Retention 是技術保存上限，不等於 business deadline。
- **C：** 錯誤。Depth per worker能支援capacity判斷，但沒有service time、oldest age與deadline就不能比較使用者風險。
- **D：** 錯誤。Received 可含重複與未完成工作；此方案可能提高worker吞吐，但未限制database connection或transaction budget，會把瓶頸往下游推。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 3｜SAA｜Backlog-per-worker target tracking

平均每個 worker 每分鐘可處理 30 件，目標 queue delay 最多 2 分鐘。以 backlog-per-instance target scaling 時，合理起始 target 是多少？

A. Target設為2件/worker，直接把2分鐘latency目標當作backlog數量，不納入worker吞吐
B. Target設為30件/worker，使用一分鐘平均吞吐但不乘上可接受的兩分鐘等待窗口
C. Target採用queue retention換算的秒數，讓autoscaling直到message即將過期才啟動
D. 平均2秒、目標120秒時，單worker約可承擔60件；再以p95與下游容量驗證

**答案：D**

- **A：** 錯誤。Backlog target的單位是件數；必須用acceptable latency乘以每worker service rate。
- **B：** 錯誤。30件只是一分鐘處理量；本題初始target需涵蓋兩分鐘capacity，再用p95與in-flight校正。
- **C：** 錯誤。Retention是保存上限而非latency budget，且與backlog-per-instance的件數單位不相容。
- **D：** 正確。30×2=60 是初始 target，之後需用真實分布與 downstream 限制驗證。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Scale an Auto Scaling group based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)

### 練習題 4｜SAP｜Producer-side admission 與 stale-work shedding

促銷推薦工作的 deadline 是 5 分鐘，但 outage 後 oldest age 已達 40 分鐘，且 database 只能承受目前 consumer 數。最佳動作是什麼？

A. Purge 全 queue，包括尚在 deadline 內的高價值工作
B. 依 message deadline 丟棄/降級已無價值工作，限制 producer admission，並在 downstream capacity 內恢復高價值 backlog
C. 把 retention 延長到 14 天，並繼續處理所有過期推薦
D. 無條件增加 consumers，直到 database 被打滿

**答案：B**

- **A：** 錯誤。無差別 purge 會遺失仍有效工作；這只延長message保存或增加重試，沒有改變arrival rate與service rate的長期差額。
- **B：** 正確。Bounded admission 與 explicit expiry 防止 overload 變成永久延遲。
- **C：** 錯誤。延長retention不改變database service rate；5分鐘deadline已過的推薦繼續佔用容量，只會延遲仍有價值的新工作。
- **D：** 錯誤。Database已是hard capacity limit；無條件加consumer只會增加connections與throttling，應先做admission與stale-work shedding。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 5｜SAA｜長任務 visibility heartbeat 與 DLQ

影片 job 通常 8 分鐘，偶爾 25 分鐘；目前 visibility 5 分鐘，導致同一影片同時被多個 workers 處理。如何修正？

A. 設定涵蓋正常處理的 visibility，長任務以 ChangeMessageVisibility heartbeat 延長；side effect 冪等、commit 後 delete，重複失敗進 DLQ
B. 把 visibility 設為 0
C. 把 maxReceiveCount 一律設 1，任何 transient failure 都不重試
D. Worker receive後先delete，再把job ID寫入本地檔案；若worker失敗則由人工重新建立message

**答案：A**

- **A：** 正確。Visibility/heartbeat、冪等與 delete-after-commit 對齊真實 processing lifecycle。
- **B：** 錯誤。Visibility設為0會讓其他worker立即再次看見同一job，25分鐘長任務的重複處理會比目前更嚴重。
- **C：** 錯誤。maxReceiveCount=1會讓一次暫時故障就進DLQ，既沒有修正5分鐘visibility，也犧牲可恢復錯誤的重試機會。
- **D：** 錯誤。先delete會在worker crash時失去durable retry；本地紀錄與人工補單不能取代visibility與commit後delete。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

### 練習題 6｜SAP｜Scale-out 後 queue age 仍升高

Worker 數從 100 增至 400，但 oldest age 仍上升，database throttling 同時惡化。第一個正確結論是什麼？

A. 繼續無限增加 workers，throttling 會自行消失
B. 只要 worker CPU 低，就不可能有 downstream bottleneck
C. Consumer capacity 已把 bottleneck 推到 database；應檢查 service time、in-flight、errors、hot groups 與 DB connection/write budget，再限制 concurrency
D. 延長queue retention以避免message過期，並維持400個workers不變等待database throttling消退；當throttle發生時讓SDK無界重試，使400個workers最終都能取得database connection

**答案：C**

- **A：** 錯誤。無界 concurrency 會加劇 throttling。
- **B：** 錯誤。Worker等待database throttle或connection時CPU可以很低；oldest age上升與DB throttling才是下游service rate不足的直接證據。
- **C：** 正確。更多 workers 不會提高受限 downstream 的 service rate，反而可能放大 contention。
- **D：** 錯誤。Retention能防止過早刪除，但不提高受限database的service rate，也不控制connection contention。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Scale an Auto Scaling group based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAA｜Queue processing unit cost

某 queue 每月大量 short-poll 空回應，poison messages 反覆執行昂貴 API，過期工作仍被處理。哪個優化組合最合理？

A. 提高 short-poll 頻率並永久保留 poison messages
B. long polling與batch降成本；partial response只重試失敗項並限制下游並行
C. 只加大 batch，忽略 partial failure 與 downstream transaction
D. 停用DLQ並增加maxReceiveCount，讓poison message持續重試直到某次成功，以避免維護redrive流程

**答案：B**

- **A：** 錯誤。更頻繁short poll增加空ReceiveMessage成本；永久保留poison message又讓昂貴API反覆失敗，兩者都沒有改善有效完成率。
- **B：** 正確。減少空 poll、無效重試與 stale work，且保護 downstream。
- **C：** 錯誤。Batch 必須符合 side-effect 與局部失敗邊界。
- **D：** 錯誤。更多重試對暫時錯誤有用，但poison work會反覆消耗昂貴API與consumer capacity，需隔離與具名處置。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)、[Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜短期 burst 的 queue 使用

票券系統平時每秒 500 件，開賣 10 分鐘升到 8,000 件；工作可延遲 3 分鐘，但不能遺失。哪個方案最合適？

A. 使用單一 FIFO message group 處理所有訂單，不管 throughput
B. 只把 retention 延長，不建立 scaling 或 admission
C. 讓 API 同步呼叫每個 worker，任何 worker 慢就讓購票 request timeout
D. Durable enqueue，依 backlog-per-worker/oldest age 彈性擴縮，在 downstream 安全上限內排空並對 deadline/DLQ 告警

**答案：D**

- **A：** 錯誤。單一 group 會序列化全部工作；這只延長message保存或增加重試，沒有改變arrival rate與service rate的長期差額。
- **B：** 錯誤。Retention 不增加服務率；此方案可能提高worker吞吐，但未限制database connection或transaction budget，會把瓶頸往下游推。
- **C：** 錯誤。同步呼叫把8,000件/秒burst直接壓到API與workers；任一worker變慢都會消耗request timeout，queue也無法保存尚未處理的工作。
- **D：** 正確。Queue 吸收短 burst，consumer capacity 與 age SLO 確保在 deadline 內排空。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Scale an Auto Scaling group based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 9｜SAP｜Multi-tenant queue fairness

共享 queue 中一個 tenant 產生 70% messages，使 quiet tenants 超過 latency SLO。選擇兩項。

A. 把 queue 改成 FIFO 並讓全部 tenants 共用一個 group，以保證每個租戶都取得相同 throughput
B. 實施 per-tenant admission/concurrency 或獨立 queue/cell，保護 downstream connection budget 與 quiet-tenant SLO
C. 依總 queue depth 與平均 message age 擴充共享 consumer fleet，並把 database connection pool 隨 workers 等比例放大；當 quiet tenants 超過 SLO 時提高全域最大容量，讓所有 messages 依到達順序公平競爭連線
D. 在 standard queue 以 tenant ID 作 MessageGroupId，監看 noisy/quiet group dwell time；這可改善公平，但不提供 hard per-tenant rate limit
E. 把 tenant ID 從 message 與 metrics 移除，避免高 cardinality，改用全域平均 age 判斷公平性

**答案：B、D**

- **A：** 錯誤。FIFO 單一 group 提供全域序列化，不會提供高吞吐公平；多租戶通常需要分組與容量邊界。
- **B：** 正確。Hard isolation 來自 admission、concurrency 與 downstream quota；必要時再把極端 tenant 移至獨立資源。
- **C：** 錯誤。總量擴縮在 downstream 尚有餘裕時可降低平均 backlog，但共享 pool 與先到先服務沒有 tenant admission boundary；noisy tenant 仍可耗盡固定 database 或 partner quota。
- **D：** 正確。SQS fair queue 使用 standard queue 的 MessageGroupId 辨識群組並降低 quiet-group dwell time，但不是硬配額。
- **E：** 錯誤。移除 attribution 雖降低 metrics 維度，卻無法量測 noisy 與 quiet group 的不同等待時間。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon SQS fair queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)

### 練習題 10｜SAP｜Sustained overload recovery

Producer 的 sustained rate 已高於 consumer 能力，且部分工作 15 分鐘後失去價值。哪兩項應一起做？

A. 停用DLQ並只監看visible depth，讓失敗工作留在主queue中與正常工作共同排程
B. 把 retention 從 4 天延長到 14 天，先完整保存尖峰工作；consumer 仍依 FIFO 處理，平台以每日預測的低流量時段暫時增加 workers，等 backlog 下降後再恢復原容量
C. 在 downstream 安全範圍內，以 backlog-per-worker/age 擴充或改善 service capacity
D. 依FIFO順序處理所有過期與有效工作，避免business priority改變造成結果難以重現
E. 在 producer/consumer 檢查 deadline，實施 admission、defer/degrade 或 shedding，避免接受無法及時完成的工作

**答案：C、E**

- **A：** 錯誤。這會讓poison work反覆佔用capacity並隱藏失敗；無法解決arrival rate長期高於service rate。
- **B：** 錯誤。離峰 burst capacity 適合可延遲且仍有價值的批次工作，但 sustained arrival 已高於 service rate，且本題工作 15 分鐘後失效；延長 retention 會讓過期工作繼續競爭資源。
- **C：** 正確。提高有效 μ，但要尊重 downstream budget。
- **D：** 錯誤。順序可有業務價值，但本題工作15分鐘後失效；不shedding會讓無價值工作拖慢仍有效請求。
- **E：** 正確。Bounded acceptance 防止 stale backlog 無限增長。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Scale an Auto Scaling group based on Amazon SQS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「使用bounded backlog、queue age SLO、autoscaling、admission…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Queue能把短期arrival spike平滑成可處理速率，但長期超載只會累積過期工作。」，所以「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」能直接滿足它；若constraint改成「增加retention爭取處理時間，但不會提升consumer capacity。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」。替代方案「增加retention爭取處理時間，但不會提升consumer capacity。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只看queue depth不看age與deadline，系統仍處理已無價值的request。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Queue能把短期arrival spike平滑成可處理速率，但長期超載只會累積過期工作。」，排除會導致「只看queue depth不看age與deadline，系統仍處理已無價值的request。」的選項，再選「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「使用bounded backlog、queue age SLO、autoscaling、admission control與load shedding。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「buffers buy time; they do not create throughput」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 110 章　Cache 不是正確性來源

Cache副本可能過期、evict或部分失效，business correctness不能依賴它永久存在。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：權限cache延遲更新可能讓已撤權使用者繼續存取。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：Cache副本可能過期、evict或部分失效，business correctness不能依賴它永久存在。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon ElastiCache負責主要工作，Amazon CloudFront提醒我們答案不是永遠固定。本章會走向「定義authoritative store、TTL/invalidation、miss path與stampede protection。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：權限cache延遲更新可能讓已撤權使用者繼續存取。

商業需求與不能妥協的限制
          ▼
[Amazon ElastiCache：主要責任]
          │ 提供managed Valkey/Redis OSS/Memcached記憶體data store。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon CloudFront：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
  · DAX：為DynamoDB提供API-compatible、in-memory read-through cach…
可移植原則：a cache may accelerate truth but must not redefine it

失敗時先找：Cache miss被當不存在，造成授權或庫存錯判。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon ElastiCache有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon ElastiCache和Amazon CloudFront並不是兩個任意的產品名稱。前者適合本章，是因為「定義authoritative store、TTL/invalidation、miss path與stampede protection。」直接回應了眼前的問題；後者描述的「Write-through/read-through可簡化應用，但仍需處理partial failure。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Cache miss被當不存在，造成授權或庫存錯判。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「a cache may accelerate truth but must not redefine it」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| DAX | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 |

## 把全圖套進一個具體案例

**場景：** 權限cache延遲更新可能讓已撤權使用者繼續存取。

1. 故事的起點：權限cache延遲更新可能讓已撤權使用者繼續存取。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon ElastiCache負責「提供managed Valkey/Redis OSS/Memcached記憶體data store。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudFront、DAX各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Cache miss被當不存在，造成授權或庫存錯判。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon ElastiCache

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Cache副本可能過期、evict或部分失效，business correctness不能依賴它永久存在。
- **具體例子／邊界：** 在「權限cache延遲更新可能讓已撤權使用者繼續存取。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudFront

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Write-through/read-through可簡化應用，但仍需處理partial failure。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Cache miss被當不存在，造成授權或庫存錯判。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：a cache may accelerate truth but must not redefine it。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### origin

CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

## 回到 AWS：Components、功用與責任邊界

### Amazon ElastiCache

- **功用：** 提供managed Valkey/Redis OSS/Memcached記憶體data store。
- **底層機制：** Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
- **關鍵設定：** engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- **選擇時機：** session、hot reads、leaderboard、rate limiting與降低database load。
- **替換時機：** 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。

### Amazon CloudFront

- **功用：** 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
- **底層機制：** DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
- **關鍵設定：** origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- **選擇時機：** 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。
- **替換時機：** 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。

### DAX

- **功用：** 為DynamoDB提供API-compatible、in-memory read-through cache。
- **底層機制：** Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。
- **關鍵設定：** cluster nodes/subnets/SG、IAM、TTL、parameter group、encryption與client endpoint。
- **選擇時機：** microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。
- **替換時機：** 強一致read、複雜Redis structures或非DynamoDB資料使用ElastiCache/application cache。

## 考前與實作時再查：設定操作手冊

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

### DAX：逐項設定說明

#### `cluster nodes/subnets/SG`

- **控制什麼：** `cluster nodes/subnets/SG`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DAX的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `IAM`

- **控制什麼：** `IAM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DAX明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `TTL`

- **控制什麼：** `TTL`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定DAX的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `parameter group`

- **控制什麼：** `parameter group`是一組可版本化的engine/runtime參數，會改變DAX的實際process行為。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DAX指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `client endpoint`

- **控制什麼：** `client endpoint`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DAX的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

## 讀到這裡，請用自己的話說一次

1. Amazon ElastiCache的責任：提供managed Valkey/Redis OSS/Memcached記憶體data store。
2. 底層機制：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
3. 第一個要看的設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
4. 選擇邏輯：定義authoritative store、TTL/invalidation、miss path與stampede protection。
5. 不要混淆：Amazon CloudFront的責任是「在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。」；它不會自動取代Amazon ElastiCache。
6. 替換訊號：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
7. 最常見錯法：Cache miss被當不存在，造成授權或庫存錯判。
8. 可移植原則：a cache may accelerate truth but must not redefine it。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| DAX | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 | microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。 | 強一致read、複雜Redis structures或非DynamoDB資料使用ElastiCache/application cache。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Write-through/read-through可簡化應用，但仍需處理partial failure。 | 只有當題目條件明確改變時才可能合理。 | Cache miss被當不存在，造成授權或庫存錯判。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Write-through/read-through可簡化應用，但仍需處理partial failure。」之間做選擇。
- 認得常考設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Cache 與 authoritative source

商品庫存目前只存在 ElastiCache；節點 replacement 後部分 keys 消失，系統卻把 cache miss 解讀為庫存為零。根本問題是什麼？

A. 系統沒有定義 durable authoritative store 與合法 miss/degraded path；cache 可加速資料但不能重新定義真相
B. TTL 太短；把 TTL 設為永久即可取代 database backup
C. Cache node 不夠大；只要加大 memory 就會成為永久 source of truth
D. 缺少 CloudFront；edge cache 會自動修復遺失的 inventory write

**答案：A**

- **A：** 正確。Cache loss 應只影響 latency/availability，不能改變 business truth。
- **B：** 錯誤。無限 TTL 增加 stale risk，也不提供 durable recovery。
- **C：** 錯誤。容量不能把易失、可 stale 的副本變成 authoritative state。
- **D：** 錯誤。CloudFront 是 HTTP cache，不是 inventory database。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 2｜SAA｜Cache-aside miss flow

Application 採 cache-aside。某 key 在 ElastiCache miss，但 database 有值。正確流程是什麼？

A. 把 miss 永久視為不存在，不查 database
B. 等待 cache 自己從任何 database 自動載入，application 不需知道 source
C. 刪除 database value，讓 truth 與 cache 一致
D. Cache-aside：miss讀DB回填；cache故障時依策略讀DB

**答案：D**

- **A：** 錯誤。Miss 可能是 expiry、eviction 或 cold node。
- **B：** 錯誤。一般 cache-aside 的載入由 application 控制。
- **C：** 錯誤。不能讓加速副本反向刪除 truth；這只改變cache容量或TTL，沒有處理authoritative source、version與跨系統更新競態。
- **D：** 正確。這是明確的 lazy-loading/cache-aside contract。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 3｜SAP｜Write 與 invalidation ordering

價格更新流程先刪除 cache，再寫 database；database write 失敗時，另一 request 從舊 database 值重新填入 cache。改善重點是什麼？

A. 採 write-through 同步更新 cache 與 database，但不定義其中一邊失敗時的 transaction、補償或版本順序
B. DB先commit；outbox再失效cache，讀取比較version
C. 增加 cache replicas 並啟用 Multi-AZ；replication 可提高 cache availability，因此不再需要處理跨系統 write ordering
D. 先失效 cache，再提交 database；若 database 失敗，依賴下一次 miss 自動判斷哪個值才是 authoritative

**答案：B**

- **A：** 錯誤。Write-through 可以使用，但 cache 與 database 通常不是同一原子 transaction，仍要定義 partial-failure 行為。
- **B：** 正確。先讓 authoritative write 成功，再可靠傳遞 invalidation；version/outbox 能處理失效遺失與舊值回填競態。
- **C：** 錯誤。Cache replication 處理節點故障，不會讓 database commit 與 cache update 變成原子操作。
- **D：** 錯誤。這正是題幹 race：database 失敗後，另一 request 可把舊資料重新載入 cache，且沒有版本判斷。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

### 練習題 4｜SAP｜Authorization cache 的 fail-safe freshness

高風險提款 API 快取 allow decision 24 小時。員工撤權後仍能操作。哪個 redesign 最合理？

A. Cache不確定時重查policy或fail closed
B. 把 allow 永久保存以提高 availability
C. 把來源 IP 當唯一 authorization，移除 identity policy；若policy service不可達就沿用最後allow到服務恢復，不區分提款金額或cache年齡
D. 只把 cache 搬到更大的 node，不改 freshness

**答案：A**

- **A：** 正確。安全 cache 必須有 bounded freshness、revocation signal 與安全故障模式。
- **B：** 錯誤。永久 allow 使撤權無法生效；此方案可提高hit ratio，卻讓authorization或inventory承受未定義的stale window與失效模式。
- **C：** 錯誤。Network location 不能取代 identity/data authorization。
- **D：** 錯誤。容量與 authorization correctness 無關。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 5｜SAA｜Cache stampede mitigation

十萬個 clients 的熱門 key 都在整點到期，database 瞬間被 cache misses 打滿。最有效的組合是什麼？

A. 每個cache miss都直接查database並立即回填；以較大的read replica fleet承受整點同步失效
B. 移除 cache，且不評估 database capacity
C. 合併同key並發載入、加入TTL jitter，並只對可容忍stale的資料使用stale-while-revalidate
D. 所有hot keys使用相同固定TTL，並在整點前預先增加database capacity以承受集中reload

**答案：C**

- **A：** 錯誤。擴充origin可提高上限，但大量相同key的重複read仍會形成herd；coalescing與TTL jitter更直接。
- **B：** 錯誤。可能直接把全部 load 推給 source；它改善cache availability，但不能讓database commit與cache invalidation變成同一原子操作。
- **C：** 正確。錯開 expiry 並合併同 key reload 可保護 origin。
- **D：** 錯誤。預先擴容可降低故障風險，但相同expiry仍製造不必要尖峰；jitter能從來源消除同步失效。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 6｜SAP｜Hit ratio 下降與 origin latency 診斷

部署後 cache hit ratio 驟降、evictions 增加、database p99 同步上升。下一步最合理？

A. 延長authorization allow TTL來提高整體hit ratio，再以每日批次撤權補償較長stale window；若hit ratio仍低就增加read replicas，將key版本與eviction變化留到容量擴充後分析
B. 按deploy時序查hit ratio、eviction與origin p99
C. 直接增加 database replicas，不查看 cache key 或 memory
D. 假設 Multi-AZ cache 不會 cold start，因此忽略 endpoint/failover

**答案：B**

- **A：** 錯誤。這可能改善hit ratio，卻改變撤權安全contract；題目應先診斷key、memory、eviction與deploy變化。
- **B：** 正確。以時序與 cache/origin metrics 找第一個變壞的 contract。
- **C：** 錯誤。可能治標且忽略 deployment 導致的 key explosion。
- **D：** 錯誤。Failover/replacement 仍可能造成 cold cache 或 client 行為問題。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Metrics for Valkey and Redis OSS](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheMetrics.WhichShouldIMonitor.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAA｜Useful hit ratio 與 cache-key 成本

CloudFront distribution 把 user-agent、全部 cookies、全部 query strings 都放入 cache key；內容其實只依 path 與語言不同。最佳優化是什麼？

A. 將每個使用者response納入獨立cache key並使用很長TTL，確保個人化內容不互相污染
B. 把所有request headers、cookies與query strings納入cache key，確保任何輸入差異都不會共用response
C. 只加大 origin instance，不修改 cache fragmentation
D. 移除無用query string/cookie/header的cache-key維度，提高CloudFront hit ratio並降低origin負載

**答案：D**

- **A：** 錯誤。隔離個人化內容可避免洩漏，但會造成高cardinality與低hit ratio，不適合用來降低CloudFront成本。
- **B：** 錯誤。完整變化可保守維持correctness，但會碎片化cache；應只納入真正影響response的維度。
- **C：** 錯誤。保留錯誤 cache policy 只會持續浪費 origin capacity。
- **D：** 正確。縮小無意義 key 維度可提高 useful hit ratio 並減少 origin load。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜ElastiCache、DAX、CloudFront 選型

三個需求分別是：全球 HTTP 靜態內容；DynamoDB eventually consistent hot reads 且少改 client；排行榜 sorted-set。正確對應是什麼？

A. 三種資料都放入DAX，利用DynamoDB相容cache統一處理HTTP content、Redis structures與table reads
B. 三種資料都放入CloudFront，以edge distribution統一取代Redis與DynamoDB read cache
C. HTTP 用 CloudFront、DynamoDB hot reads 用 DAX、排行榜用 ElastiCache Valkey/Redis OSS
D. HTTP 用 ElastiCache、DynamoDB 用 CloudFront、排行榜用 DAX

**答案：C**

- **A：** 錯誤。DAX只適用DynamoDB API與其一致性語意，不能快取一般HTTP response或Redis資料結構。
- **B：** 錯誤。CloudFront適合HTTP content；它不提供Redis資料結構，也不能作DynamoDB API的DAX替代。
- **C：** 正確。分別對應 edge HTTP、DynamoDB-compatible cache 與 general-purpose data structures。
- **D：** 錯誤。三者責任錯置；這個cache適用範圍與題目資料模型不符，會破壞原本的protocol或consistency contract。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[DAX and DynamoDB consistency models](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 9｜SAP｜Cache policy rollout 防止 origin collapse

團隊要改 serialized value format 與 TTL。要求新舊 app 可短期並存，且不能因全量 miss 壓垮 database。選擇兩項。

A. 使用 versioned cache keys/namespace，讓新舊格式並存並可回滾
B. 在 warm-up window 暫時移除 database rate limit，讓新 namespace 由 production reads 自然填滿；若 origin p99 升高，再由 Auto Scaling 增加 application instances 分攤 miss traffic
C. 原地覆寫同一 key schema，假設舊 client 能解析
D. 部署時一次 flush 全部 production cache
E. Canary 新 policy，限制 miss concurrency，按有證據的 hot set 漸進 warm-up，監控 hit ratio/origin p99

**答案：A、E**

- **A：** 正確。Versioned key 避免格式 collision 並保留 rollback。
- **B：** 錯誤。Application 擴容不能增加 database 的安全查詢預算；取消 origin protection 會讓大量同時 miss 形成 stampede。自然填充可用，但必須限制 concurrency 並分波觀察 source p99。
- **C：** 錯誤。舊 client 可能反序列化失敗；這個cache適用範圍與題目資料模型不符，會破壞原本的protocol或consistency contract。
- **D：** 錯誤。同步 cold cache 易造成 stampede；這只改變cache容量或TTL，沒有處理authoritative source、version與跨系統更新競態。
- **E：** 正確。Canary、origin protection 與量測可控制 rollout。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 10｜SAP｜撤權事件遺失時的 permission-cache version reconciliation

授權服務以事件通知各 API 清除 permission cache；某 API 網路分區期間漏掉撤權事件，恢復後仍持有 allow。哪兩項最能限制風險？

A. 改用 private subnet，因 network isolation 可讓舊 allow 自動失效
B. 為撤權事件設可追蹤 sequence/version 與重放/補抓機制，並告警 consumer lag 或 version divergence
C. 將所有 allow 永久快取；分區期間維持 availability 比撤權時限更重要
D. 讓每筆 cached decision 帶 policy version/expiry，恢復連線後與 authoritative version 對帳；版本未知或過期的高風險操作重新查驗
E. 把 invalidation topic retention 設長即可；subscriber 漏掉事件後會自動知道自己缺少哪個 policy version

**答案：B、D**

- **A：** 錯誤。Private network 降低暴露面，但不會改變已快取的 identity/data authorization decision。
- **B：** 正確。具序號的撤權 stream、replay 與 divergence alarm 能把遺失事件轉成可偵測、可修復的狀態。
- **C：** 錯誤。某些低風險讀取可在分區時 fail open，但高風險撤權有明確時限，永久 allow 不符合安全 contract。
- **D：** 正確。Version 與 bounded expiry 讓 API 能辨識自己的 cache 是否落後，並為高風險操作採 fail-safe recheck。
- **E：** 錯誤。較長 retention 可協助重播，但 consumer 仍需 checkpoint/version 才知道漏了什麼，不能單靠保存時間。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)、[Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「定義authoritative store、TTL/invalidation、miss path與stam…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Cache副本可能過期、evict或部分失效，business correctness不能依賴它永久存在。」，所以「定義authoritative store、TTL/invalidation、miss path與stampede protection。」能直接滿足它；若constraint改成「Write-through/read-through可簡化應用，但仍需處理partial failure。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「定義authoritative store、TTL/invalidation、miss path與stampede protection。」。替代方案「Write-through/read-through可簡化應用，但仍需處理partial failure。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Cache miss被當不存在，造成授權或庫存錯判。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Cache副本可能過期、evict或部分失效，business correctness不能依賴它永久存在。」，排除會導致「Cache miss被當不存在，造成授權或庫存錯判。」的選項，再選「定義authoritative store、TTL/invalidation、miss path與stampede protection。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「定義authoritative store、TTL/invalidation、miss path與stampede protection。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「a cache may accelerate truth but must not redefine it」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 111 章　Control Plane 與 Data Plane 分離

管理設定與處理每個request的路徑有不同availability、latency與一致性需求。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：Feature flag服務故障時，應用應維持最後已知安全設定。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：管理設定與處理每個request的路徑有不同availability、latency與一致性需求。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon Route 53，對照角色是AWS AppConfig。我們選擇「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Feature flag服務故障時，應用應維持最後已知安全設定。

較慢、需要嚴格驗證的Control Plane
管理者 ──> 建立新設定 ──> validate ──> canary rollout ──> published version
                                                        │
                                                        ▼
較快、每次request都依賴的Data Plane
使用者 ──> application ──> 讀本地cache / last-known-good設定 ──> 回應

Control plane短暫故障時，既有data plane仍以最後已知安全版本服務。
錯誤新設定則靠驗證、分波與rollback阻止擴大。

失敗時先找：控制面短暫不可用導致既有資料面也停止服務。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon Route 53有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Route 53和AWS AppConfig並不是兩個任意的產品名稱。前者適合本章，是因為「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」直接回應了眼前的問題；後者描述的「強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：控制面短暫不可用導致既有資料面也停止服務。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「serve from local published state; manage through slower verified workflows」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| AWS AppConfig | 安全發布runtime configuration與feature flags，不需重新部署程式。 | Hosted/external config經validators與deployment strategy漸進推出；agent/cache讓app本地讀取。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 |

## 把全圖套進一個具體案例

**場景：** Feature flag服務故障時，應用應維持最後已知安全設定。

1. 故事的起點：Feature flag服務故障時，應用應維持最後已知安全設定。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Route 53負責「提供authoritative DNS、health check與多種流量政策。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS AppConfig、AWS Systems Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「控制面短暫不可用導致既有資料面也停止服務。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Route 53

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：管理設定與處理每個request的路徑有不同availability、latency與一致性需求。
- **具體例子／邊界：** 在「Feature flag服務故障時，應用應維持最後已知安全設定。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS AppConfig

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：控制面短暫不可用導致既有資料面也停止服務。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：serve from local published state; manage through slower verified workflows。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### data plane

實際處理每個packet、request、message、query與資料讀寫的runtime路徑。

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

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

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

### AWS AppConfig

- **功用：** 安全發布runtime configuration與feature flags，不需重新部署程式。
- **底層機制：** Hosted/external config經validators與deployment strategy漸進推出；agent/cache讓app本地讀取。
- **關鍵設定：** application/environment/profile、validators、deployment strategy、bake time、alarms與feature flag attributes。
- **選擇時機：** kill switch、dynamic limits、endpoint切換與低風險漸進配置。
- **替換時機：** 基礎設施desired state用CloudFormation；secret用Secrets Manager。

### AWS Systems Manager

- **功用：** 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。
- **底層機制：** SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。
- **關鍵設定：** managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
- **選擇時機：** fleet operations、patch、secure access、runbook與remediation。
- **替換時機：** container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。

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

### AWS AppConfig：逐項設定說明

#### `application/environment/profile`

- **控制什麼：** `application/environment/profile`定義AWS AppConfig管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `validators`

- **控制什麼：** `validators`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「kill switch、dynamic limits、endpoint切換與低風險漸進配置。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS AppConfig以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `deployment strategy`

- **控制什麼：** `deployment strategy`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「kill switch、dynamic limits、endpoint切換與低風險漸進配置。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS AppConfig設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `bake time`

- **控制什麼：** `bake time`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「kill switch、dynamic limits、endpoint切換與低風險漸進配置。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS AppConfig的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `alarms`

- **控制什麼：** `alarms`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「kill switch、dynamic limits、endpoint切換與低風險漸進配置。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS AppConfig選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `feature flag attributes`

- **控制什麼：** `feature flag attributes`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

### AWS Systems Manager：逐項設定說明

#### `managed instance role`

- **控制什麼：** `managed instance role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「fleet operations、patch、secure access、runbook與remediation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Systems Manager明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `VPC endpoints`

- **控制什麼：** `VPC endpoints`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「fleet operations、patch、secure access、runbook與remediation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Systems Manager的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `documents`

- **控制什麼：** `documents`是可版本化的啟動或工作規格，定義AWS Systems Manager建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `associations`

- **控制什麼：** `associations`控制AWS Systems Manager的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

#### `inventory`

- **控制什麼：** `inventory`定義AWS Systems Manager管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `maintenance windows`

- **控制什麼：** `maintenance windows`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「fleet operations、patch、secure access、runbook與remediation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Systems Manager的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `automation`

- **控制什麼：** `automation`把AWS Systems Manager與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. Amazon Route 53的責任：提供authoritative DNS、health check與多種流量政策。
2. 底層機制：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
3. 第一個要看的設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
4. 選擇邏輯：Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。
5. 不要混淆：AWS AppConfig的責任是「安全發布runtime configuration與feature flags，不需重新部署程式。」；它不會自動取代Amazon Route 53。
6. 替換訊號：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
7. 最常見錯法：控制面短暫不可用導致既有資料面也停止服務。
8. 可移植原則：serve from local published state; manage through slower verified workflows。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| AWS AppConfig | 安全發布runtime configuration與feature flags，不需重新部署程式。 | Hosted/external config經validators與deployment strategy漸進推出；agent/cache讓app本地讀取。 | kill switch、dynamic limits、endpoint切換與低風險漸進配置。 | 基礎設施desired state用CloudFormation；secret用Secrets Manager。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 | fleet operations、patch、secure access、runbook與remediation。 | container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。 | 只有當題目條件明確改變時才可能合理。 | 控制面短暫不可用導致既有資料面也停止服務。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。」之間做選擇。
- 認得常考設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.2 Determine a strategy to improve security；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Control plane 與 data plane 分類

團隊用管理 API 發布 feature configuration，ECS tasks 以已發布版本處理使用者 requests。哪個分類正確？

A. 建立/更新 configuration 與每筆 request 都是 control plane
B. 只有 CloudFormation 才算 control plane
C. DNS record 更新與 client 使用 cached answer 是同一操作
D. 控制面建立或變更desired state；資料面以已發布狀態處理每次流量

**答案：D**

- **A：** 錯誤。建立或更新configuration是control plane；ECS task使用已發布版本處理HTTP request是data plane，兩者不能因使用同一設定而合併分類。
- **B：** 錯誤。許多服務都有管理/控制 API；它可以降低retrieval次數，但poll interval、configuration age與高風險flag的fail-safe仍未定義。
- **C：** 錯誤。Record change 與 resolver/client 使用答案分屬不同路徑。
- **D：** 正確。控制面改變 desired state；資料面使用既有 state 處理流量。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)、[What is AWS AppConfig?](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)

### 練習題 2｜SAA｜AppConfig Agent local cache

ECS API 每筆 request 都遠端讀 feature flag；AppConfig endpoint 短暫不可達時全站 timeout。應如何改善？

A. 只在 container memory 保存最後版本，但不定義初次啟動沒有 cache、task replacement 或檔案持久性時的行為
B. AppConfig Agent本地讀；backup/preload或safe default處理cold start
C. 把 feature flag 改成 Route 53 weighted record；DNS cache 同時提供 JSON validation、版本與 deployment rollback
D. 每筆 request 直接呼叫 AppConfig Data API；endpoint timeout 時重試到成功，以確保永遠取得最新版本

**答案：B**

- **A：** 錯誤。In-memory cache 可處理短暫連線問題，卻不能保證新 task 的 cold start；仍需定義 backup/preload/default。
- **B：** 正確。Agent 將遠端 polling 與每次 request 解耦；cold start 是否有可用版本則必須由 backup/preload 或 application default 明確保證。
- **C：** 錯誤。Route 53 適合 DNS 流量路由，沒有 AppConfig configuration profile、validator 與 deployment monitor 的語意。
- **D：** 錯誤。直接遠端讀在 freshness 極端嚴格時可能有吸引力，但會把 AppConfig/network latency 放進每個 request 的可用性路徑。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Using AWS AppConfig Agent](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html)、[Using AWS AppConfig Agent with Amazon ECS and Amazon EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)、[What is AWS AppConfig?](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)

### 練習題 3｜SAA｜AppConfig 安全部署與自動 rollback

一個 pricing flag 語法正確，但使 checkout error rate 升高。哪個 AppConfig 設計可把此風險限制在 rollout 期間？

A. 使用validator、gradual deployment、bake time與CloudWatch alarm rollback控制設定風險
B. 只做 JSON schema validation；語法通過即代表業務安全
C. 直接 all-at-once 修改 production，不設 alarm
D. 把flag烘焙進AMI並以rolling instance replacement發布，使用ASG健康檢查回退失敗instances

**答案：A**

- **A：** 正確。Validation 擋格式，gradual rollout/bake/alarm 處理 runtime regression。
- **B：** 錯誤。Syntax 不能驗證 checkout outcome。
- **C：** 錯誤。All-at-once沒有canary population、bake window或CloudWatch alarm monitor；checkout退化時也缺少AppConfig自動rollback條件。
- **D：** 錯誤。Immutable image可安全發布靜態設定，但題目要用AppConfig限制configuration rollout；此方案增加發布時間且缺少flag-level monitor。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Deploying configurations with AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/deploying-feature-flags.html)、[Monitoring AWS AppConfig deployments for automatic rollback](https://docs.aws.amazon.com/appconfig/latest/userguide/monitoring-deployments.html)、[Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)

### 練習題 4｜SAP｜Configuration staleness boundary

同一套 AppConfig 同時保存 UI 顏色與緊急提款 kill switch。可否使用相同 30 分鐘 local cache policy？

A. 兩者都使用 30 分鐘 poll interval；只要 Agent local endpoint 可回應，就代表提款撤權也符合 freshness SLO
B. 兩者都每 request 遠端讀且不 cache；這消除 stale，但把 control/network 故障加入所有 request 的 critical path
C. UI可用較長cache；kill switch需較短freshness、版本監測與明確fail-safe，並驗證30分鐘SLO
D. 兩者都永久使用 PRELOAD_BACKUP；backup version 一旦存在便不需再 poll 或監看 deployment version

**答案：C**

- **A：** 錯誤。Local availability 與配置新鮮度是兩個指標；低風險 UI 與提款撤權的 business impact 明顯不同。
- **B：** 錯誤。同步遠端讀可縮短 stale window，但降低 runtime resilience；通常應由本地 Agent 加明確 freshness policy 平衡。
- **C：** 正確。高風險控制要把 poll interval、cache age、version divergence 與 outage fail-safe 一起限制在撤權目標內。
- **D：** 錯誤。Preload backup 解決 cold start，不能取代後續 polling、版本比較與受監控的 configuration deployment。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using AWS AppConfig Agent](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html)、[Using AWS AppConfig Agent with Amazon ECS and Amazon EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

### 練習題 5｜SAA｜SSM fleet operations 不進 request path

公司用 Systems Manager Automation 修補 fleet。開發者提議每個 HTTP request 先執行 SSM Run Command 取得設定。哪個評估正確？

A. 用State Manager每五分鐘同步設定，但HTTP handler仍等待最新association成功後才讀本地檔案
B. SSM適合fleet管理/automation；正常request應讀取已部署或本地可用的runtime state
C. 每個request執行Run Command並等待stdout，以控制面回覆保證設定最新
D. 把Run Command放入request path，再以較大timeout與重試吸收控制面節流

**答案：B**

- **A：** 錯誤。State Manager定期落地設定可以合理，但HTTP handler若等待association完成，仍把fleet控制面放回每次request的可用性路徑。
- **B：** 正確。Run Command與Automation適合管理fleet；request serving應讀取已部署或本地cache的狀態，更新失敗則依freshness與fail-safe policy處理。
- **C：** 錯誤。Run Command是非同步管理操作，不是低延遲local read；每次等待command結果會增加節流、延遲與控制面故障耦合。
- **D：** 錯誤。較大timeout與重試不會移除同步依賴，反而可能在SSM受限時造成retry storm並耗盡HTTP worker。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Working with SSM Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 6｜SAP｜Control impairment 導致 traffic stop 的診斷

管理 console/API 受限時，已運行服務也停止。應優先找什麼？

A. 只比較 application CPU 與 memory；若資源未滿，就可排除 configuration、credential 與 endpoint expiry
B. 把 poll interval 降到接近零並停用 local cache；這能讓 control endpoint impairment 對 traffic 的影響更小
C. 在事故中擴大 Auto Scaling desired capacity；即使每個新 task 都因無初始 configuration 失敗，增加數量仍能恢復服務
D. 檢查request path的同步management/config依賴、Agent本地版本，以及新task的backup preload或safe default

**答案：D**

- **A：** 錯誤。CPU 正常不能排除每個 request 被遠端設定 lookup、過期 credentials 或 endpoint timeout 阻塞。
- **B：** 錯誤。更頻繁 polling 有助 freshness，卻增加對故障 endpoint 的依賴；本題要找 control/data plane 耦合。
- **C：** 錯誤。Scale-out 在新 task 可成功啟動時才有用；若 cold start 依賴受損 control plane，反而製造更多失敗。
- **D：** 正確。既有 task 的 cached version 與新 task 的 cold-start path不同；同步控制面依賴、backup/default 和 credential expiry 都可能停止 data plane。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)、[Using AWS AppConfig Agent](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html)、[Using AWS AppConfig Agent with Amazon ECS and Amazon EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜Configuration retrieval cost 與 rollout toil

十萬 containers 每個 request 遠端取 flag，造成大量 retrieval 與 latency。哪個優化最合理？

A. 把所有 tasks 的 poll interval 設為 1 秒；較頻繁 polling 必然同時降低成本與 endpoint request 數
B. 把 configuration 寫入 AMI 並停用版本與 rollback；所有 flag 變更都等下一次完整映像部署
C. 每個 ECS task 使用 AppConfig Agent sidecar/local endpoint，按可接受 freshness 設 poll interval；不要假設不同 tasks 會共享同一 Agent cache
D. 每個 request 直接呼叫 StartConfigurationSession/GetLatestConfiguration，並以 application retries 吸收控制面節流；每個task仍各自poll，但透過較長interval控制總request量與可接受freshness

**答案：C**

- **A：** 錯誤。短 poll 可改善 freshness，但會增加 retrieval 與 endpoint 負擔；應依風險設定而非一律最短。
- **B：** 錯誤。Immutable image 適合靜態設定，但題目需要頻繁 flags 與安全 rollback，完全綁定 binary release 會增加 toil。
- **C：** 正確。Agent 在其部署邊界內提供 local cache/polling；ECS 常見是每 task sidecar，不能虛構跨 container fleet 的透明共享 cache。
- **D：** 錯誤。直接 data API 可用，但每 request 呼叫會放大成本、節流與 latency；Agent 的目的正是集中本地 retrieval。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using AWS AppConfig Agent](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html)、[Deploying configurations with AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/deploying-feature-flags.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜ECS feature flag 完整方案

ECS service 要逐步啟用新 checkout，錯誤率上升時自動回復；短暫網路中斷仍用最後安全版本。哪個方案最完整？

A. AppConfig validators + gradual strategy/bake/alarm，tasks 透過 Agent local endpoint 讀取並定義 last-known-safe
B. 用 DNS weighted record 當所有 feature state
C. 每次 flag 更新重建所有 tasks，無 canary
D. 每次 request 直接讀 Parameter Store 且不 cache

**答案：A**

- **A：** 正確。兼顧安全發布、rollback 與 runtime local serving。
- **B：** 錯誤。DNS traffic routing 不等於 app configuration lifecycle。
- **C：** 錯誤。All fleet replacement 擴大 blast radius。
- **D：** 錯誤。同步 remote read 形成 availability dependency。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Deploying configurations with AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/deploying-feature-flags.html)、[AWS AppConfig Agent for Amazon ECS and Amazon EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)

### 練習題 9｜SAP｜跨帳號 configuration governance

企業要跨帳號/Region 管理 production flags，並防止單人直接全域修改。選擇兩項。

A. 分離 author/approver/deployer roles，版本化配置並保存 audit evidence
B. outage 時才第一次建立 recovery configuration
C. 按低風險 cell/account/Region 分 waves，使用 alarms/rollback，預先準備必要 source/key/endpoint 與 emergency runbook
D. 讓各 Region 的 platform admin 獨立維護 production flags，變更透過當地 change ticket 核准；中央團隊每季匯出版本與 CloudTrail 記錄，比較差異後決定是否統一設定
E. 共用一組 AdministratorAccess credentials

**答案：A、C**

- **A：** 正確。Separation of duties 與版本 evidence 限制未審變更。
- **B：** 錯誤。把 control creation 放入 outage critical path。
- **C：** 正確。分波、預建依賴與 rollback 使跨 Region 變更可操作。
- **D：** 錯誤。區域自治可降低同步 control-plane 依賴，但季度才彙整不足以控制高風險 flag 的即時 drift，也沒有跨 account/Region 的分波 gate、共同版本與快速 rollback 證據。
- **E：** 錯誤。共用AdministratorAccess破壞separation of duties與可歸責性；任一credential外洩或誤操作都可同時修改所有account/Region。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Deploying configurations with AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/deploying-feature-flags.html)、[Monitoring AWS AppConfig deployments for automatic rollback](https://docs.aws.amazon.com/appconfig/latest/userguide/monitoring-deployments.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)

### 練習題 10｜SAP｜AppConfig Agent cold start 與 stale emergency flag 的故障決策

新 ECS task 在 AppConfig endpoint 中斷時啟動；磁碟沒有 backup，而 cached emergency kill switch 已超過允許 freshness。哪兩項設計可避免默默使用不安全狀態？

A. 新 task 啟動時呼叫 StartDeployment，把最近核准版本重新部署到 AppConfig；deployment 完成後再由 Agent 讀取，並以較長 timeout 等待 control plane 在 endpoint 恢復時完成 rollout
B. 只要 local endpoint 回傳任何內容就一律啟動；不檢查版本、年齡或是否為預載的核准版本
C. 把 poll interval 永久設為最大值，讓 emergency flag 不會在執行期間改變
D. 對高風險 flag 定義 stale 時 fail-safe 與 readiness 行為；endpoint 恢復後重新對帳最新版本並告警 divergence
E. 為 task 預先提供經核准的 PRELOAD_BACKUP/BACKUP_DIRECTORY 或 application safe default，並驗證 configuration version 與 age

**答案：D、E**

- **A：** 錯誤。StartDeployment 是 control-plane rollout，不是 task cold-start 的本地讀取機制；把它加入 readiness 會讓 endpoint outage 阻止擴容，且無法處理當下已過 freshness 的 emergency flag。
- **B：** 錯誤。Local response 只證明有資料，不證明其 freshness 或風險可接受；emergency flag 必須有版本與時限。
- **C：** 錯誤。長 poll 可減少 retrieval，但會延後 kill switch；若超過撤權/緊急控制 SLO 就不是可接受取捨。
- **D：** 正確。高風險設定的 availability/freshness trade-off 要事先決定，並在恢復後以 authoritative version reconciliation 收斂。
- **E：** 正確。Backup/preload 或安全 default 明確解決沒有 memory cache 的 cold start，version/age 則避免把任意舊檔案當安全狀態。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using AWS AppConfig Agent](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html)、[Using AWS AppConfig Agent with Amazon ECS and Amazon EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)、[Monitoring AWS AppConfig deployments for automatic rollback](https://docs.aws.amazon.com/appconfig/latest/userguide/monitoring-deployments.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Data plane使用已發布、可cache的configuration；control plane更新需…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「管理設定與處理每個request的路徑有不同availability、latency與一致性需求。」，所以「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」能直接滿足它；若constraint改成「強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」。替代方案「強一致control lookup每request執行較直觀，但會把管理服務變成runtime單點。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「控制面短暫不可用導致既有資料面也停止服務。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「管理設定與處理每個request的路徑有不同availability、latency與一致性需求。」，排除會導致「控制面短暫不可用導致既有資料面也停止服務。」的選項，再選「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Data plane使用已發布、可cache的configuration；control plane更新需版本化、驗證與漸進發布。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「serve from local published state; manage through slower verified workflows」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 112 章　Identity、Network、Data 三層安全

單一防火牆或IAM policy無法同時處理身份、路徑與資料生命週期。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：內部分析服務在private VPC，但仍需tenant authorization與column-level保護。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：單一防火牆或IAM policy無法同時處理身份、路徑與資料生命週期。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看IAM如何接手工作，再看Amazon VPC何時更合適，最後用設定與考題驗證「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：內部分析服務在private VPC，但仍需tenant authorization與column-level保護。

商業需求與不能妥協的限制
          ▼
[IAM：主要責任]
          │ 定義AWS API的principal、authentication與authorization。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon VPC：建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
  · AWS KMS：管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
  · AWS Lake Formation：在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。
可移植原則：security boundaries should fail independently

失敗時先找：Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問IAM有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，IAM和Amazon VPC並不是兩個任意的產品名稱。前者適合本章，是因為「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」直接回應了眼前的問題；後者描述的「Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「security boundaries should fail independently」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| IAM | 定義AWS API的principal、authentication與authorization。 | Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。 |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 |

## 把全圖套進一個具體案例

**場景：** 內部分析服務在private VPC，但仍需tenant authorization與column-level保護。

1. 故事的起點：內部分析服務在private VPC，但仍需tenant authorization與column-level保護。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：IAM負責「定義AWS API的principal、authentication與authorization。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon VPC、AWS KMS、AWS Lake Formation各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### IAM

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：單一防火牆或IAM policy無法同時處理身份、路徑與資料生命週期。
- **具體例子／邊界：** 在「內部分析服務在private VPC，但仍需tenant authorization與column-level保護。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon VPC

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：security boundaries should fail independently。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### envelope encryption

先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### data plane

實際處理每個packet、request、message、query與資料讀寫的runtime路徑。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### data key

實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

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

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### IAM

- **功用：** 定義AWS API的principal、authentication與authorization。
- **底層機制：** Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。
- **關鍵設定：** users/groups/roles、managed/inline policies、MFA、access keys、credential report與Access Analyzer。
- **選擇時機：** 所有AWS control/data plane存取；人員優先federation，workload優先role。
- **替換時機：** 應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。

### Amazon VPC

- **功用：** 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
- **底層機制：** ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
- **關鍵設定：** IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- **選擇時機：** 任何需要私有位址、network segmentation或hybrid connectivity的workload。
- **替換時機：** 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。

### AWS KMS

- **功用：** 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
- **底層機制：** Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
- **關鍵設定：** key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- **選擇時機：** S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。
- **替換時機：** 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。

### AWS Lake Formation

- **功用：** 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。
- **底層機制：** 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。
- **關鍵設定：** data lake locations、administrators、LF-Tags、grants、hybrid access mode與cross-account sharing。
- **選擇時機：** 多團隊analytics需要細粒度資料治理而非大量S3 policy。
- **替換時機：** 一般object-level app access仍用IAM/S3 policies/Access Points。

## 考前與實作時再查：設定操作手冊

### IAM：逐項設定說明

#### `users/groups/roles`

- **控制什麼：** `users/groups/roles`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `managed/inline policies`

- **控制什麼：** `managed/inline policies`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `access keys`

- **控制什麼：** `access keys`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `credential report`

- **控制什麼：** `credential report`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `Access Analyzer`

- **控制什麼：** `Access Analyzer`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

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

### AWS KMS：逐項設定說明

#### `key policy`

- **控制什麼：** `key policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `grants`

- **控制什麼：** `grants`指定誰能使用、管理或接受AWS KMS的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `aliases`

- **控制什麼：** `aliases`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `rotation`

- **控制什麼：** `rotation`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `multi-Region keys`

- **控制什麼：** `multi-Region keys`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS KMS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `encryption context`

- **控制什麼：** `encryption context`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `key spec/usage`

- **控制什麼：** `key spec/usage`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

### AWS Lake Formation：逐項設定說明

#### `data lake locations`

- **控制什麼：** `data lake locations`指定AWS Lake Formation讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `administrators`

- **控制什麼：** `administrators`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊analytics需要細粒度資料治理而非大量S3 policy。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lake Formation建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `LF-Tags`

- **控制什麼：** `LF-Tags`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊analytics需要細粒度資料治理而非大量S3 policy。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lake Formation建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `grants`

- **控制什麼：** `grants`指定誰能使用、管理或接受AWS Lake Formation的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `hybrid access mode`

- **控制什麼：** `hybrid access mode`選擇AWS Lake Formation的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `cross-account sharing`

- **控制什麼：** `cross-account sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊analytics需要細粒度資料治理而非大量S3 policy。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lake Formation建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

## 讀到這裡，請用自己的話說一次

1. IAM的責任：定義AWS API的principal、authentication與authorization。
2. 底層機制：Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。
3. 第一個要看的設定：users/groups/roles、managed/inline policies、MFA、access keys、credential report與Access Analyzer。
4. 選擇邏輯：Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。
5. 不要混淆：Amazon VPC的責任是「建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。」；它不會自動取代IAM。
6. 替換訊號：應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。
7. 最常見錯法：Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。
8. 可移植原則：security boundaries should fail independently。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| IAM | 定義AWS API的principal、authentication與authorization。 | Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。 | 所有AWS control/data plane存取；人員優先federation，workload優先role。 | 應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。 |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 | 任何需要私有位址、network segmentation或hybrid connectivity的workload。 | 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 | S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。 | 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 | 多團隊analytics需要細粒度資料治理而非大量S3 policy。 | 一般object-level app access仍用IAM/S3 policies/Access Points。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。 | 只有當題目條件明確改變時才可能合理。 | Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。」之間做選擇。
- 認得常考設定：users/groups/roles、managed/inline policies、MFA、access keys、credential report與Access Analyzer。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Identity、network、data 三層責任

分析平台位於 private subnets 且使用 KMS encryption。開發者因此認為不需 IAM 或 column authorization。哪項正確？

A. 以private subnet與endpoint policy限制來源網路，再由application自行判斷使用者可讀哪些資料列
B. Identity決定principal/action，network決定可達性，data與key policy決定可讀內容
C. KMS encryption 會決定誰可連 TCP port
D. Security group 可直接授予 Lake Formation SELECT

**答案：B**

- **A：** 錯誤。Network restriction可縮小可達範圍，但仍需identity與data-layer authorization，不能只靠application假設。
- **B：** 正確。Private path只限制可達來源；principal仍需IAM授權，資料範圍與解密則分別由data policy與KMS policy約束。
- **C：** 錯誤。Encryption 不取代 network filtering。
- **D：** 錯誤。SG 不表達 table/column permission。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)、[Lake Formation permissions reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html)

### 練習題 2｜SAA｜IAM effective permission evaluation

Role identity policy Allow s3:GetObject；bucket policy 也 Allow，但 Organizations SCP 對該 action Explicit Deny。結果為何？

A. 拒絕；適用的 explicit deny 優先，SCP 也不會自行授權
B. 以bucket policy授權特定role，並把它視為resource owner的最終決定，即使Organizations SCP拒絕同一action
C. 在SCP加入Allow s3:GetObject，讓member account role不需identity或resource policy也取得存取權
D. 允許，因兩個 Allow 多於一個 Deny

**答案：A**

- **A：** 正確。Explicit deny wins，且仍需實際 grant。
- **B：** 錯誤。Bucket policy可以授權resource access，但不能越過適用的SCP explicit deny。
- **C：** 錯誤。SCP設定permission上限而不授權；仍需identity或resource policy提供實際Allow。
- **D：** 錯誤。Policy evaluation 不是票數；此方案放寬權限可以暫時排查，但會掩蓋真正缺少的action/resource/condition並破壞least privilege。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 3｜SAA｜Security group 與 NACL

Client 對 private API 的 TCP 連線 timeout。SG 已允許 inbound client SG；NACL inbound 允許目的 port，但 outbound 沒有 ephemeral return rule。哪項最準確？

A. 把NACL視為連線追蹤防火牆，只設定inbound service port，讓return traffic沿已建立連線自動通過
B. SG 依 rule number 順序處理，第一條 deny 生效
C. NACL stateless，需允許 return traffic；SG stateful，已允許連線的回應不需另加對應 SG rule
D. Route table 可取代 IAM 與 SG

**答案：C**

- **A：** 錯誤。這描述的是stateful SG；NACL不追蹤連線，所在subnet的雙向規則都要允許相應流量。
- **B：** 錯誤。SG 只有 allow 且不按數字 first-match。
- **C：** 正確。SG是stateful；NACL是subnet邊界的stateless filter。若client連入private API，API subnet的outbound NACL需允許回到client的ephemeral source port，client subnet的inbound NACL也需允許該回程流量。
- **D：** 錯誤。Routing 與 authorization/filter 是不同責任。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Control traffic to your AWS resources using security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[Control subnet traffic with network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 4｜SAA｜Encrypted resource 與 KMS key permission

Cross-account role 已被 S3 bucket policy 允許 GetObject，但讀取 SSE-KMS object 時 AccessDenied。最可能還缺什麼？

A. 在bucket policy加入跨帳號Allow並關閉Block Public Access，讓caller繞過KMS授權讀取encrypted object
B. 同時配置KMS key policy/grant與caller kms:Decrypt；S3/IAM授權本身不足以跨帳號解密
C. 擴大NACL ephemeral return ports，假設目前AccessDenied是回程封包被stateless filter丟棄
D. 維持bucket與KMS設定不變，只停用TLS後重試，以排除傳輸加密與SSE-KMS同時使用造成的衝突

**答案：B**

- **A：** 錯誤。S3 data permission與KMS key permission是獨立檢查；公開bucket也不能繞過kms:Decrypt。
- **B：** 正確。讀 encrypted object 同時需要資料與 key authorization。
- **C：** 錯誤。NACL問題常表現為連線timeout；既然收到服務AccessDenied，應先追S3與KMS授權。
- **D：** 錯誤。TLS保護傳輸、SSE-KMS保護靜態資料，兩者可同時使用；停用TLS不會授予decrypt。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Allowing users in other accounts to use a KMS key](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)、[Sharing SSE-KMS encrypted Amazon S3 objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html)、[Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 5｜SAP｜Lake Formation fine-grained permission

Analyst 只能查 sales table 的 region、amount 欄與自己的 Region rows。哪個控制最直接？

A. 只把 analyst 放入 private subnet
B. 只給 KMS decrypt；查詢服務再用view隱藏其他欄位，但analyst仍保有直接讀取底層table的SELECT
C. 只給 DESCRIBE，DESCRIBE 等同 SELECT
D. 用Lake Formation data filter限制row/column，並另滿足IAM、S3與KMS授權

**答案：D**

- **A：** 錯誤。Network 不表達 row/column scope。
- **B：** 錯誤。Decrypt 不授予資料查詢；它沒有正確區分SCP上限與實際授權，explicit deny或缺少Allow仍然有效。
- **C：** 錯誤。DESCRIBE 不等同讀取資料；此做法忽略SSE-KMS與Lake Formation的獨立授權面，不能由bucket或SG單獨取代。
- **D：** 正確。Lake Formation 負責 fine-grained data authorization，其他層仍須成立。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Lake Formation data filtering and cell-level security](https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html)、[Lake Formation permissions reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)

### 練習題 6｜SAP｜Private path 下的 AccessDenied 診斷

Private Athena workload 可連線但 query AccessDenied。應採哪個排查順序？

A. 只檢查 source bucket policy；Athena query result location、workgroup、Glue/Lake Formation 與 KMS 不會參與授權；若結果bucket可寫就停止排查，不再確認source data、catalog、KMS與Lake Formation權限
B. 暫時給 AdministratorAccess 與 kms:*；查詢成功後保留廣權限，因這是最快的 production 修復方式
C. 依序驗證 caller session、SCP/identity policy、Athena workgroup、Glue Catalog/Lake Formation、source與query-result S3、KMS；network path 另行驗證
D. 先把 Athena 與 S3 endpoint 移除改走 Internet；若 query 可執行，就表示原本一定只有 security group 問題

**答案：C**

- **A：** 錯誤。Source data 之外，Athena 還需要 query-result S3、workgroup、catalog/table 及加密 key 的相容權限。
- **B：** 錯誤。短期 break-glass 必須受控且回收；永久管理員會掩蓋缺少的 action/resource 並違反 least privilege。
- **C：** 正確。Athena 查詢牽涉多個授權面；先從 AccessDenied 的 action/resource 計算有效權限，再把 reachability 與資料授權分開。
- **D：** 錯誤。改走 Internet 可作受控診斷但擴大暴露，而且 AccessDenied 多半仍需從 IAM、S3、KMS 或 Lake Formation 找根因。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Control traffic to your AWS resources using security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)、[Lake Formation permissions reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html)

### 練習題 7｜SAP｜Security controls 的可營運成本

團隊提議為每個 S3 object 建立獨立 customer managed KMS key，並把全部 VPC Flow Logs 以 debug 級資料永久保留。最佳回應？

A. 依隔離、cross-account、rotation與audit邊界選適量customer managed keys，避免無意義地每物件一把CMK
B. 保留所有 Flow Logs 永不過期，並停用高價值 CloudTrail/audit logs以維持固定總儲存量
C. 每個 object 一把 KMS key可提供最細隔離，因此忽略 key quota、policy、request cost 與 lifecycle toil也合理
D. 全部改用單一 AWS managed key；它在任何 cross-account sharing、key-policy 與合規需求下都與 customer managed key 等價；並以季度人工review追蹤key政策與log成本，不建立自動retention或deletion guardrail

**答案：A**

- **A：** 正確。Envelope encryption 本來就讓物件使用 data key；CMK 應代表可管理的信任/隔離邊界，log retention 也要由調查與法規需求驅動。
- **B：** 錯誤。Flow Logs 與 CloudTrail 提供不同 evidence；應依資料價值與保存要求分層，而非用低價值長期資料取代 audit。
- **C：** 錯誤。極細 key 邊界技術上可設計，但通常帶來 quota、policy、成本與刪除復原風險，未必增加實質安全。
- **D：** 錯誤。AWS managed key 可降低管理負擔，但 cross-account 與自訂 key policy/rotation 控制不同，不能一律替換。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜VPC endpoint policy、IAM、KMS 與 Lake Formation 的 deny 判讀

Contractor role 經 S3 gateway endpoint 查詢資料湖；IAM 與 bucket policy Allow，但 endpoint policy 只允許另一 bucket，KMS key policy 也未授權此 account。哪項最準確？

A. 只授予 Lake Formation SELECT 即可；該 grant會覆寫 endpoint policy與KMS key policy中的拒絕或缺少授權
B. 只調整 security group即可，因 gateway endpoint 使用 SG 來決定 S3 object 與 KMS decrypt permission
C. Private endpoint 會讓所有 service policies失效，因此 role 可直接讀取並解密任何 object
D. 逐層驗證VPC endpoint policy、IAM/S3 policy、KMS decrypt與Lake Formation grant的交集

**答案：D**

- **A：** 錯誤。Lake Formation控制資料範圍，但不能授予通過VPC endpoint或使用KMS key所需的其他權限。
- **B：** 錯誤。S3 gateway endpoint 由 route table與endpoint policy控制；SG 不表達 object action或KMS permission。
- **C：** 錯誤。Endpoint 提供 private path，但不會略過 endpoint、IAM、resource、KMS 或 data-governance policy。
- **D：** 正確。有效存取是多個 policy plane 的交集；endpoint path 與 KMS decrypt 失敗都足以阻擋查詢。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)、[Allowing users in other accounts to use a KMS key](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)、[Lake Formation data filtering and cell-level security](https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html)

### 練習題 9｜SAP｜Multi-account security ownership

企業要讓中央 security team 有 evidence 與 guardrails，但不接管每個 workload。選擇兩項。

A. 一個 flat VPC 作為所有資料 authorization
B. 以 accounts 分離 workloads，Organizations 套 guardrails/delegated services，management account 不承載一般 workload
C. 所有工程師共用 management-account admin
D. 由中央 security team 用 SCP 列出每種 workload 可執行的 actions，member accounts 只透過 Identity Center groups 指派使用者；application runtime 沿用相同許可清單，不再建立個別 IAM roles 或 resource policies
E. 中央化必要 audit/security evidence 與 cross-account read roles；workload owners 管理受限 runtime permissions/runbooks

**答案：B、E**

- **A：** 錯誤。Network 不等於 data/identity authorization。
- **B：** 正確。Accounts 與 delegated governance 建立強邊界。
- **C：** 錯誤。破壞 segregation 與 attribution。
- **D：** 錯誤。SCP 只限制 account 中 identity policy 可授予的最大範圍，本身不授權；Identity Center 也主要處理 workforce access。Runtime 仍需具體 role、resource policy 與 workload owner。
- **E：** 正確。中央 evidence 與 scoped local ownership 可並存。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[SEC01-BP01 Separate workloads using accounts](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_multi_accounts.html)、[AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

### 練習題 10｜SAP｜Cross-account encrypted query

Account B 的 analyst role 要透過 private service path 查 Account A 資料湖的特定 rows/columns；objects 由 Account A customer managed KMS key加密，且需保留查詢 audit。選擇兩項。

A. KMS key policy/grant 允許必要 decrypt，並建立允許的 private network/service path與 audit
B. Bucket policy Allow 即可忽略 KMS
C. 產生限時presigned URL給Account B，讓URL本身同時承擔Lake Formation column filter與KMS cross-account授權
D. 為 role 建立相容的 IAM/resource/Lake Formation grants 與 data filters，限定資料 scope
E. 在security group rule加入analyst role ARN，利用SG同時限制S3 object actions、columns與kms:Decrypt

**答案：A、D**

- **A：** 正確。Key 與 network/evidence 是另外兩個必要 contract。
- **B：** 錯誤。SSE-KMS 還需 key authorization。
- **C：** 錯誤。Presigned URL可委派特定S3請求，但不會自動建立Lake Formation資料範圍或跨帳號KMS key permission。
- **D：** 正確。定義 principal、actions 與 row/column resources。
- **E：** 錯誤。SG以network identity/地址控制封包，不接受IAM role作data authorization，也不表達column或KMS action。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Allowing users in other accounts to use a KMS key](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)、[Sharing SSE-KMS encrypted Amazon S3 objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html)、[Lake Formation data filtering and cell-level security](https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html)、[VPC endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與r…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「單一防火牆或IAM policy無法同時處理身份、路徑與資料生命週期。」，所以「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」能直接滿足它；若constraint改成「Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」。替代方案「Defense in depth不是重複相同規則，而是不同失效模式的獨立控制。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「單一防火牆或IAM policy無法同時處理身份、路徑與資料生命週期。」，排除會導致「Private subnet被當作授權，任何已進VPC的principal都能讀敏感資料。」的選項，再選「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAP-1.2 Prescribe security controls。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Identity限制誰可做什麼，network限制可達路徑，data controls加密、分類、備份與retention。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「security boundaries should fail independently」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 113 章　Observability 跟隨 Business Outcome

資源健康不代表使用者成功，CPU正常時付款仍可能因第三方失敗。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

把鏡頭拉到一個真實的production現場：所有Lambda invocation成功，但事件晚兩小時處理，使用者看到過期資料。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：資源健康不代表使用者成功，CPU正常時付款仍可能因第三方失敗。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon CloudWatch是這一章的入口，AWS X-Ray用來畫出邊界；主要方向「先定義business transaction success/latency，再向下連接service與resource signals。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：所有Lambda invocation成功，但事件晚兩小時處理，使用者看到過期資料。

商業需求與不能妥協的限制
          ▼
[Amazon CloudWatch：主要責任]
          │ 收集metrics、logs、events與synthetic/real-user signals以監控AWS w…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS X-Ray：收集distributed traces並建立service map、latency與error因果。
  · CloudWatch Synthetics：以排程canary從外部視角驗證URL、API與browser journey。
可移植原則：measure what users need, then explain it with internals

失敗時先找：Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問Amazon CloudWatch有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon CloudWatch和AWS X-Ray並不是兩個任意的產品名稱。前者適合本章，是因為「先定義business transaction success/latency，再向下連接service與resource signals。」直接回應了眼前的問題；後者描述的「Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「measure what users need, then explain it with internals」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| AWS X-Ray | 收集distributed traces並建立service map、latency與error因果。 | Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。 |
| CloudWatch Synthetics | 以排程canary從外部視角驗證URL、API與browser journey。 | Lambda-based canary執行script，送metrics/logs/screenshots與trace。 |

## 把全圖套進一個具體案例

**場景：** 所有Lambda invocation成功，但事件晚兩小時處理，使用者看到過期資料。

1. 故事的起點：所有Lambda invocation成功，但事件晚兩小時處理，使用者看到過期資料。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon CloudWatch負責「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS X-Ray、CloudWatch Synthetics各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon CloudWatch

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：資源健康不代表使用者成功，CPU正常時付款仍可能因第三方失敗。
- **具體例子／邊界：** 在「所有Lambda invocation成功，但事件晚兩小時處理，使用者看到過期資料。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS X-Ray

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：measure what users need, then explain it with internals。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### canary

先把小比例流量或少數targets導向新版本，觀察technical與business指標後再擴大，以限制錯誤版本的blast radius。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### AWS X-Ray

- **功用：** 收集distributed traces並建立service map、latency與error因果。
- **底層機制：** Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。
- **關鍵設定：** sampling rules、daemon/SDK/ADOT、annotations/metadata、groups與trace map。
- **選擇時機：** 定位跨Lambda/API/DB request的p99 bottleneck與errors。
- **替換時機：** 總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。

### CloudWatch Synthetics

- **功用：** 以排程canary從外部視角驗證URL、API與browser journey。
- **底層機制：** Lambda-based canary執行script，送metrics/logs/screenshots與trace。
- **關鍵設定：** schedule、runtime、script、environment variables、VPC、artifacts、alarms與X-Ray。
- **選擇時機：** 在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。
- **替換時機：** 它不能取代真實user monitoring或backend metrics；應一起建立evidence chain。

## 考前與實作時再查：設定操作手冊

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

### AWS X-Ray：逐項設定說明

#### `sampling rules`

- **控制什麼：** `sampling rules`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「定位跨Lambda/API/DB request的p99 bottleneck與errors。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS X-Ray選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `daemon/SDK/ADOT`

- **控制什麼：** `daemon/SDK/ADOT`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `annotations/metadata`

- **控制什麼：** `annotations/metadata`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `groups`

- **控制什麼：** Trace groups以filter expression建立動態trace集合，方便把特定service、error、latency或annotation的requests分開觀察。
- **何時需要：** 需要針對一類transaction建立service map、metrics與調查入口，而不是掃描所有traces時。
- **怎麼設定／驗證：** 建立group filter並以代表性trace驗證命中；filter使用可索引annotations與service/error屬性，避免敏感或高基數資料。
- **常見錯法：** Group不會增加未被sample的traces；filter過寬會增加查詢成本，過窄則讓事故看似沒有資料。

#### `trace map`

- **控制什麼：** `trace map`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「定位跨Lambda/API/DB request的p99 bottleneck與errors。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS X-Ray選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

### CloudWatch Synthetics：逐項設定說明

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定CloudWatch Synthetics的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `runtime`

- **控制什麼：** `runtime`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Synthetics鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `script`

- **控制什麼：** `script`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `environment variables`

- **控制什麼：** `environment variables`定義CloudWatch Synthetics管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Synthetics的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `artifacts`

- **控制什麼：** `artifacts`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `alarms`

- **控制什麼：** `alarms`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Synthetics選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `X-Ray`

- **控制什麼：** `X-Ray`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

## 讀到這裡，請用自己的話說一次

1. Amazon CloudWatch的責任：收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
2. 底層機制：AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
3. 第一個要看的設定：namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
4. 選擇邏輯：先定義business transaction success/latency，再向下連接service與resource signals。
5. 不要混淆：AWS X-Ray的責任是「收集distributed traces並建立service map、latency與error因果。」；它不會自動取代Amazon CloudWatch。
6. 替換訊號：API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。
7. 最常見錯法：Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。
8. 可移植原則：measure what users need, then explain it with internals。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| AWS X-Ray | 收集distributed traces並建立service map、latency與error因果。 | Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。 | 定位跨Lambda/API/DB request的p99 bottleneck與errors。 | 總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。 |
| CloudWatch Synthetics | 以排程canary從外部視角驗證URL、API與browser journey。 | Lambda-based canary執行script，送metrics/logs/screenshots與trace。 | 在沒有真實流量時持續驗證availability、DNS/TLS/login與critical path。 | 它不能取代真實user monitoring或backend metrics；應一起建立evidence chain。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。 | 只有當題目條件明確改變時才可能合理。 | Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。」之間做選擇。
- 認得常考設定：namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Business SLI/SLO

付款 API 所有 EC2 CPU 都低於 30%，但 8% transactions 沒有入帳。哪個 SLO 最能反映使用者結果？

A. 在 30 天 window 內，成功完成且正確入帳的付款比例與 p99 completion latency 達目標
B. Instance running 數量
C. AWS service SLA 的數字直接當 application success；入帳錯誤另以客服case統計，且不把duplicate與late completion納入SLO denominator
D. 以EC2 CPU低於50%作為主要SLI，再以付款失敗工單作為月末補充報表

**答案：A**

- **A：** 正確。量測 completed business outcome、correctness 與 latency。
- **B：** 錯誤。Instance running只量到compute resource state；它無法定義付款成功的numerator、正確入帳、duplicate或completion latency。
- **C：** 錯誤。服務 SLA 不等於端到端 SLI；這能增加telemetry數量，卻沒有控制cardinality、sampling、retention與audit evidence的不同需求。
- **D：** 錯誤。CPU可解釋資源壓力，但不能作為正確入帳的numerator/denominator或完成latency。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Service level objectives in CloudWatch Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 2｜SAA｜Metrics、logs、traces 分工

Checkout error rate 上升，需要先看趨勢，再查看單筆錯誤，最後追跨 API/queue/database 路徑。正確工具角色為何？

A. 以traces抽樣估算整體error trend，並從trace events取代所有長期metrics與完整audit logs
B. Host metrics 可直接顯示每個 business invariant
C. Metrics 看 aggregate；logs 看詳細事件；traces 連接單一 request 跨 dependencies
D. 從structured logs聚合error rate並建立SLO，省略獨立metrics與跨dependency trace context

**答案：C**

- **A：** 錯誤。Trace有助因果診斷，但抽樣不保證完整計數或audit；metrics、logs與traces應互補。
- **B：** 錯誤。Infrastructure signal 不等於 business outcome。
- **C：** 正確。Metrics適合計數與趨勢告警，logs保存單筆事件細節，traces以共同context串起API、queue與database的因果路徑。
- **D：** 錯誤。Logs可產生指標與細節，但沒有trace context時較難追跨服務因果；題目要求三個層次。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)

### 練習題 3｜SAP｜Metric cardinality 與 statistic

團隊要監控 checkout p99，提議把 request ID 與 customer ID 都當 CloudWatch metric dimensions。最佳設計？

A. 每月只發布一個p99 latency datapoint，降低CloudWatch費用並在月底判斷是否違反SLO；request ID保留在logs，metrics仍以customer ID分維度以便快速做單客戶p99查詢
B. 低基數metrics量aggregate SLI；customer/request等高基數識別放入logs與traces
C. 只發布平均 latency，但補上 service/Region/result 等 bounded dimensions、五分鐘告警與 deployment annotation；仍以平均值代替 p99，並把 request ID 留在 logs 供事後追查、單筆重建與月度容量檢討使用驗證
D. 每 request 一組 dimensions，cardinality 無成本

**答案：B**

- **A：** 錯誤。低頻資料可做月報，但無法及時偵測退化，也難支援告警與部署關聯。
- **B：** 正確。Metrics 負責可聚合 signal，細粒度 identity 放 logs/traces。
- **C：** 錯誤。更多樣本能改善平均估計，仍不能取代p99等tail statistic；平均可能隱藏少數嚴重延遲。
- **D：** 錯誤。每個request建立metric dimensions會產生無界cardinality與成本；request/customer識別應留在logs或traces供單筆查詢。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 4｜SAA｜Synthetic 與 real-user signals

凌晨沒有真實流量，但公司仍要確認 login→search→checkout 關鍵路徑；白天還要知道真實裝置/Region 體驗。應如何搭配？

A. 只部署CloudWatch RUM收集真實browser sessions，並把凌晨沒有事件解讀為關鍵流程健康
B. 用 CloudTrail 管理事件取代 application transaction
C. 只讓load balancer /health回200，並用該結果代表login、search與checkout dependencies都可用
D. Synthetics定期跑安全關鍵流程；RUM量真實使用者體驗，並與backend telemetry關聯

**答案：D**

- **A：** 錯誤。RUM反映真實使用者，沒有流量時沒有主動證據；仍需Synthetics執行安全測試交易。
- **B：** 錯誤。CloudTrail記錄AWS管理與部分資料事件，不會執行login、search、checkout，也無法取代RUM的真實使用者體驗或Synthetics的主動探測。
- **C：** 錯誤。淺health適合target routing，但不會執行identity、search、payment等完整business path。
- **D：** 正確。Synthetics在無真實流量時仍主動驗證關鍵流程；RUM量測白天真實裝置與Region體驗，backend traces/metrics用來定位依賴。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Using synthetic monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)、[Use CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)、[Service level objectives in CloudWatch Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 5｜SAP｜Async trace/correlation propagation

API 將工作送入 SQS 後 trace 中斷，無法把結果連回原始 order。應怎麼做？

A. 以秒級timestamp作correlation ID，consumer依時間鄰近把SQS message與order trace重新配對
B. 把 credentials 放入 trace annotations
C. 跨SQS傳trace header與business ID
D. 只在事故後嘗試重新 sample 已消失的 requests

**答案：C**

- **A：** 錯誤。Timestamp可能碰撞且在retry/out-of-order時不可靠；應傳遞穩定business ID與trace context。
- **B：** 錯誤。Credentials是secret，不應進trace annotation；它既造成洩漏，也不能代替X-Ray trace header或穩定order correlation ID。
- **C：** 正確。明確 context propagation 才能跨 async boundary 保存因果。
- **D：** 錯誤。事故發生前未傳遞或採樣的trace context無法事後重建；應在enqueue時把trace header與business ID寫入message。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Trace Amazon SQS messages with AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-sqs.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 6｜SAP｜成功 invocation 下的 stale-data 診斷

Lambda Success 99.99%，但 dashboard 資料落後兩小時。最佳排查方式？

A. 沿producer timestamp、queue age與commit watermark找freshness斷點
B. 以Lambda invocation HTTP/Success狀態作為freshness SLI，成功率高時只延長dashboard cache TTL
C. 只提高 Lambda memory
D. 只看function error count與duration；若都正常，就把兩小時延遲歸因於dashboard顯示問題

**答案：A**

- **A：** 正確。沿資料 handoff 找 freshness 首次偏離。
- **B：** 錯誤。Invocation success不代表queue已排空或downstream commit完成；延長cache只會隱藏staleness。
- **C：** 錯誤。提高memory只有在Lambda compute受限時才可能縮短duration；它不會揭示queue backlog、late event或database watermark停滯。
- **D：** 錯誤。每個invocation都成功仍可能有backlog、late data或downstream lag，需沿watermark與queue age追查。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜Telemetry 成本與診斷價值

每個 request 都產生大量 debug logs、unique metric dimension 與 100% traces，成本暴增。最佳調整？

A. 完全停用application tracing與debug logs，只保留服務預設metrics來控制觀測成本
B. 所有debug logs與100% traces永久保存，利用完整資料避免任何事故需要重新重現
C. 把 request ID 轉成更多 metric dimensions；audit events也套用相同ratio sampling，假設抽樣足以支援日後完整合規重建
D. 依用途設定log level/retention、trace sampling與metric cardinality；audit evidence不做任意抽樣

**答案：D**

- **A：** 錯誤。降低volume合理，但完全移除causal evidence會使事故無法定位；應依價值sampling與分層retention。
- **B：** 錯誤。完整保存可能適合短期重大事件或合規audit，但無差別長期保留成本高且未處理敏感資料。
- **C：** 錯誤。Request ID會造成高基數metric成本，audit事件又要求可完整重建，不能套用可能遺漏紀錄的trace ratio sampling。
- **D：** 正確。低基數metrics保留完整聚合訊號，traces依風險取樣，debug logs分層保存；audit與事故證據則依合規和調查需求完整保留。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 8｜SAA｜Payment API observability

新 payment API 要在付款未完成時快速告警並可定位依賴。哪個最完整？

A. 以Route 53 DNS query count與health check作付款成功告警，再由值班人員人工抽查交易
B. 建立business success/error/latency SLI、dependency metrics、安全synthetic交易與可關聯的logs/traces
C. 以 CloudTrail deployment events、Lambda/EC2 service metrics 與 DNS health check 建立告警，再由值班人員用抽樣付款紀錄確認結果；不另建立 business-success SLI 或跨依賴 trace
D. 以EC2 CPU、memory與instance status建立完整告警，將application transaction結果留給客服工單

**答案：B**

- **A：** 錯誤。DNS訊號能反映解析與入口，不能量到付款commit、依賴錯誤或business latency。
- **B：** 正確。Outcome detection、outside-in test 與 causal diagnosis 都具備。
- **C：** 錯誤。CloudTrail與EC2/Lambda metrics可說明部署及資源狀態，但不能計算付款commit成功率，也無法沿payment dependencies定位單筆失敗。
- **D：** 錯誤。Infrastructure health是必要支援訊號，但資源正常時付款仍可能因下游或資料語意失敗。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Service level objectives in CloudWatch Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[Using synthetic monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)

### 練習題 9｜SAP｜Cross-account observability operating model

企業要跨 accounts 建立可營運 observability，選擇兩項。

A. 只保留 global dashboard，不保留原始 context
B. 標準化 telemetry schema/correlation 與 SLO ownership，中央 account 以 least-privilege 匯集可搜尋 evidence
C. 為 alarms 指定 owner/runbook/escalation，並測試 workload/account/Region impairment 時的 evidence access
D. 中央 account 對所有 workloads 取得 unrestricted write/admin
E. 每團隊任意命名 metrics，無共同 dimensions

**答案：B、C**

- **A：** 錯誤。Global dashboard適合概覽，但若不保留原始logs、traces與account/Region context，告警後無法定位是哪個dependency或deployment失敗。
- **B：** 正確。共同語言與 scoped aggregation 支援跨域調查。
- **C：** 正確。Alarm 必須能導向具名行動，且 outage 中仍可存取。
- **D：** 錯誤。中央observability account只需受控的telemetry read/link與必要管理權限；unrestricted write/admin會擴大跨account blast radius。
- **E：** 錯誤。任意metric名稱與dimensions使同一SLI無法跨team聚合，central alarm、search與on-call handoff也無法使用共同查詢。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[CloudWatch cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 10｜SAP｜Stale-data incident detection and explanation

要同時偵測並解釋 stale-data incident，哪兩項缺一不可？

A. 以 freshness/completed-business SLI 與 outside-in check 告警
B. 延長logs retention並建立全文搜尋，將freshness告警與producer/consumer correlation留待事故後人工推斷
C. 以成功deployment event作為pipeline freshness訊號，部署成功後暫停queue age與commit watermark告警
D. 以host CPU與Lambda duration偵測stale data，數值正常時就不追producer timestamp或database watermark
E. 以 correlation 連接 producer、queue age/DLQ、consumer、database commit 的 metrics/logs/traces

**答案：A、E**

- **A：** 正確。Freshness/completed-business SLI負責及時偵測使用者可見的停滯，outside-in check則驗證實際讀取結果，而不是只看producer或host健康。
- **B：** 錯誤。較長retention有助調查，但沒有freshness SLI與共同ID時，不能及時偵測或串起broken handoff。
- **C：** 錯誤。Deployment成功只證明control-plane變更完成，不代表資料持續流動或最新event已commit。
- **D：** 錯誤。資源訊號可解釋瓶頸，但不能直接量測資料新鮮度，正常值也無法排除handoff停滯。
- **E：** 正確。逐跳 evidence 找到 broken handoff。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Service level objectives in CloudWatch Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先定義business transaction success/latency，再向下連接service與…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「資源健康不代表使用者成功，CPU正常時付款仍可能因第三方失敗。」，所以「先定義business transaction success/latency，再向下連接service與resource signals。」能直接滿足它；若constraint改成「Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先定義business transaction success/latency，再向下連接service與resource signals。」。替代方案「Synthetic monitoring驗證外部path，real-user telemetry反映實際分布。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「資源健康不代表使用者成功，CPU正常時付款仍可能因第三方失敗。」，排除會導致「Dashboard充滿host metrics但沒有訂單成功率、lag或資料新鮮度。」的選項，再選「先定義business transaction success/latency，再向下連接service與resource signals。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先定義business transaction success/latency，再向下連接service與resource signals。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「measure what users need, then explain it with internals」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 114 章　RTO/RPO 決定 DR，而非服務名稱

相同AWS服務可組成不同恢復能力，真正contract來自資料流與演練。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

如果今天由你值班，收到的需求可能是這樣：Database可秒級promotion，但DNS、secret與人工核准使整體恢復需兩小時。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：相同AWS服務可組成不同恢復能力，真正contract來自資料流與演練。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 這只是起點，因為恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Backup承接主要責任，以Aurora Global Database檢查替代條件，並用「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Database可秒級promotion，但DNS、secret與人工核准使整體恢復需兩小時。

商業需求與不能妥協的限制
          ▼
[AWS Backup：主要責任]
          │ 以policy集中排程、保存與複製多種AWS resource backups。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Aurora Global Database：將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
  · Amazon Route 53：提供authoritative DNS、health check與多種流量政策。
可移植原則：recovery objectives are end-to-end properties

失敗時先找：購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和Aurora Global Database並不是兩個任意的產品名稱。前者適合本章，是因為「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」直接回應了眼前的問題；後者描述的「Service SLA與DR目標相關但不等價；application還有部署與操作時間。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「recovery objectives are end-to-end properties」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |

## 把全圖套進一個具體案例

**場景：** Database可秒級promotion，但DNS、secret與人工核准使整體恢復需兩小時。

1. 故事的起點：Database可秒級promotion，但DNS、secret與人工核准使整體恢復需兩小時。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Aurora Global Database、Amazon Route 53各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：相同AWS服務可組成不同恢復能力，真正contract來自資料流與演練。
- **具體例子／邊界：** 在「Database可秒級promotion，但DNS、secret與人工核准使整體恢復需兩小時。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Aurora Global Database

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Service SLA與DR目標相關但不等價；application還有部署與操作時間。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：recovery objectives are end-to-end properties。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

### SLA

對外合約承諾，通常包含可用性計算、排除條款與未達成時的補償；不等於內部工程SLO或單一AWS服務SLA。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

### Aurora Global Database

- **功用：** 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
- **底層機制：** Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。
- **關鍵設定：** primary/secondary Regions、write forwarding、global write、switchover/failover、RPO monitoring與headless secondary。
- **選擇時機：** 全球relational reads與分鐘級Region recovery。
- **替換時機：** 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

## 考前與實作時再查：設定操作手冊

### AWS Backup：逐項設定說明

#### `backup plan/rule`

- **控制什麼：** `backup plan/rule`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Backup的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `lifecycle`

- **控制什麼：** `lifecycle`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `vault/KMS`

- **控制什麼：** `vault/KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `resource assignment`

- **控制什麼：** `resource assignment`指定AWS Backup讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `copy action`

- **控制什麼：** `copy action`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `restore testing`

- **控制什麼：** `restore testing`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

### Aurora Global Database：逐項設定說明

#### `primary/secondary Regions`

- **控制什麼：** `primary/secondary Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Aurora Global Database前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `write forwarding`

- **控制什麼：** `write forwarding`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Aurora Global Database的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

#### `global write`

- **控制什麼：** `global write`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `switchover/failover`

- **控制什麼：** `switchover/failover`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「全球relational reads與分鐘級Region recovery。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Aurora Global Database設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `RPO monitoring`

- **控制什麼：** `RPO monitoring`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `headless secondary`

- **控制什麼：** `headless secondary`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Aurora Global Database的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

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

## 讀到這裡，請用自己的話說一次

1. AWS Backup的責任：以policy集中排程、保存與複製多種AWS resource backups。
2. 底層機制：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
3. 第一個要看的設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
4. 選擇邏輯：先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。
5. 不要混淆：Aurora Global Database的責任是「將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。
8. 可移植原則：recovery objectives are end-to-end properties。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 | 全球relational reads與分鐘級Region recovery。 | 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Service SLA與DR目標相關但不等價；application還有部署與操作時間。 | 只有當題目條件明確改變時才可能合理。 | 購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Service SLA與DR目標相關但不等價；application還有部署與操作時間。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜RTO 與 RPO

業務可接受最多遺失 15 分鐘資料，且事故後 2 小時內恢復完整下單。哪項解讀正確？

A. Service SLA 會自動替 workload 決定兩者
B. 將15分鐘設為RTO、2小時設為RPO，並以backup job完成時間代表服務恢復；恢復後只確認API回200，不驗證事故前最後一筆已提交訂單是否存在於recovered state
C. RPO=15 分鐘；RTO=2 小時，且兩者都要以端到端 business service 驗證
D. RPO 是修復時間，RTO 是 backup frequency

**答案：C**

- **A：** 錯誤。業務需自行定義 workload objectives；此方案優化了部分切換步驟，但RTO仍包含detection、declaration、reconnect與validation的serial path。
- **B：** 錯誤。這顛倒兩個目標；RPO限制可接受資料損失，RTO限制從事故到business service恢復。
- **C：** 正確。目標分別約束 data protection 與 recovery workflow。
- **D：** 錯誤。RPO 衡量可接受資料損失時間，RTO 衡量恢復時間；這只證明backup、standby或某個resource存在，沒有證明可解密、可連線並恢復business transaction。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 2｜SAA｜Pilot light 與 warm standby 的 RTO/cost 邊界

訂單平台要求跨 Region DR：RPO 5 分鐘、RTO 45 分鐘。資料可持續複寫；事故後才擴大 application capacity 仍能在 45 分鐘內完成。最低常駐成本的合理起點是什麼？

A. Warm standby：全天維持能立即承接完整 production load的雙 Region等量容量，且不評估較小常駐 stack是否已達 RTO
B. 採pilot light：持續保護核心資料與最小必要服務，預建依賴並演練45分鐘內擴容切換
C. Backup/restore，每日複製一次資料；只要 IaC 完整就能自然符合 5 分鐘 RPO
D. Multi-site active-active，讓兩 Region 同時寫入；即使 application不支援 conflict resolution也可避免所有資料風險

**答案：B**

- **A：** 錯誤。Warm standby 維持縮小但可運作的 stack；若配置成等量完整容量，成本接近 hot/multi-site 且超出本題需要。
- **B：** 正確。Pilot light 保持資料與核心元件可用，事故時擴容；題目明示擴容能在 45 分鐘內完成，因此較低固定成本。
- **C：** 錯誤。Daily backup 可符合較寬鬆 RPO，但無法滿足 5 分鐘資料損失目標，除非增加持續/高頻保護機制。
- **D：** 錯誤。Active-active 可能降低RTO，但需要writer/conflict設計，且在pilot light已達目標時通常不是最低常駐成本。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Creating a backup plan](https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup-plan.html)

### 練習題 3｜SAA｜AWS Backup recovery contract

Daily backup job 都顯示 COMPLETED，但 restore drill 無法解密且超過 RTO。哪個改進最完整？

A. 對所有 resource一律啟用PITR，假設AWS Backup支援清單中的每種資源都提供相同point-in-time recovery語意
B. 保留cross-Region copy但取消restore drill；只要copy job COMPLETED就可把job duration視為application RTO
C. 只延長 recovery point retention；較舊備份能自動修正目前DR account缺少的KMS permission與restore workflow
D. 依resource能力設定backup/PITR、vault/KMS與cross-Region copy，並用restore testing量測與驗證application

**答案：D**

- **A：** 錯誤。PITR並非所有AWS Backup resource都具相同支援；必須依resource type查能力並選對應schedule。
- **B：** 錯誤。Copy success證明recovery point到達，不證明可解密、啟動、連線或在RTO內恢復business service。
- **C：** 錯誤。Retention只改保存時間，不會授權DR key、建立target dependencies或縮短restore critical path。
- **D：** 正確。Backup/PITR能力依resource而異；vault、key、copy、restore testing與業務驗證共同形成可量測的recovery contract。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Creating a backup plan](https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup-plan.html)、[Restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)

### 練習題 4｜SAP｜Aurora Global switchover 與 failover

健康的 Aurora Global Database 要做 planned Region maintenance，要求零資料損失角色互換。應選什麼？

A. 直接做 unplanned failover 並忽略 replication lag
B. 讓兩個 Regions 同時獨立寫入同一 primary semantics
C. 執行Aurora Global Database managed switchover，先確認健康同步；災難failover另定義fencing與data-loss邊界
D. 只改 Route 53，DNS 會提升 secondary writer；並在切換後才通知clients重新連線，不預先測試writer endpoint與driver failover行為

**答案：C**

- **A：** 錯誤。Unplanned failover 可有未複寫 writes。
- **B：** 錯誤。Aurora Global Database的planned switchover有單一writer角色；讓兩個Region獨立接受同一primary語意的writes會造成split-brain。
- **C：** 正確。Planned switchover 與 disaster failover 的前提/資料風險不同。
- **D：** 錯誤。Route 53只能改名稱解析，不能promote Aurora secondary；必須先由database控制面完成switchover，再驗證writer endpoint、driver reconnect與交易。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Switchover and failover for Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 5｜SAP｜End-to-end dependency recovery

Database 已在 DR Region promote，但 app 無法服務，因 KMS key、secrets、quota 與 container image 不在該 Region。根本改善是什麼？

A. 在DR Region預建network、identity、secrets、artifacts、quota、capacity與可用KMS key並演練
B. 只複寫database；一般Regional KMS key、Secrets Manager secret與container image會在database promote時自動出現在DR Region
C. 只降低Route 53 TTL；DNS變更會建立缺少的key policy、service quota與ECR image，並保留現有database connections
D. 把所有依賴留到事故中建立；這可避免idle cost，且control-plane provisioning時間不需計入RTO

**答案：A**

- **A：** 正確。DR需預建或複寫整條critical path；KMS key是Regional資源，應預建適當key或在適用時使用multi-Region key。
- **B：** 錯誤。資料複寫不會自動複寫所有周邊資源；一般Regional KMS key也不會因database promotion而跨Region出現。
- **C：** 錯誤。TTL只影響部分client cache，不能建立key、quota、artifact或讓既有connections無縫轉移。
- **D：** 錯誤。事故時建立資源可降低固定成本，但所有等待與control-plane失敗都會進入RTO，必須先證明仍達標。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Configuring DNS failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)、[Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)

### 練習題 6｜SAP｜RTO delay decomposition

DB promotion 只需 40 秒，但演練總 RTO 2 小時。如何找主要延遲？

A. 從DNS change開始計時，只比較routing propagation與client cache，不納入事故偵測和宣告；每一段只記平均時間，不標示serial dependency、owner與可平行化的準備工作
B. 把人工approval排除於RTO報告，另列為治理時間；即使使用者仍無法下單也停止計時
C. 繼續把database promotion從40秒降到20秒，假設所有其他步驟都可平行且沒有dependency
D. 分解detection、declaration、approval、data readiness、capacity、DNS/cache、reconnect與business validation時間

**答案：D**

- **A：** 錯誤。DNS只是恢復流程一段；business RTO通常從disruption開始，detection與declaration也在outage內。
- **B：** 錯誤。治理可分項呈現，但只要approval阻擋服務恢復，它仍在端到端RTO critical path。
- **C：** 錯誤。優化非主要瓶頸只能省20秒；需先用時間線辨識兩小時中真正的serial critical path。
- **D：** 正確。把端到端RTO拆成有起訖點的serial/parallel階段，才能看出40秒promotion以外真正主導兩小時恢復時間的步驟。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Switchover and failover for Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)

### 練習題 7｜SAP｜同一RTO/RPO下比較四種DR策略的總成本

兩個候選方案都通過RPO 5分鐘、RTO 45分鐘演練：A為pilot light，每月固定2萬美元、每季演練40人時；B為warm standby，每月固定7萬美元、每季演練12人時。業務估算每次超過RTO的損失為30萬美元。應如何比較？

A. 直接改成active-active；服務層級最高即可視為成本最低，不需重新驗證writer與operating model
B. 在相同已驗證RTO/RPO下，比較固定容量、複寫、license、演練人力、失敗機率與超標損失的TCO
C. 只比較每月compute帳單，因此A必然正確，忽略A較長的scale-out路徑與演練失敗機率
D. 只比較人時，因此B必然正確，忽略每月多出的5萬美元固定容量與資料傳輸

**答案：B**

- **A：** 錯誤。Active-active需更高容量與資料衝突治理；若無法降低足夠風險，會是過度建置而非最低TCO。
- **B：** 正確。兩者都達標時，應比較所有常駐與營運成本，加上DR演練失敗造成的期望業務損失。
- **C：** 錯誤。A可能總成本較低，但仍要把擴容自動化、測試人力與超過45分鐘的剩餘風險納入。
- **D：** 錯誤。B降低部分恢復操作，但固定容量每年多60萬美元；只看人時會忽略主要成本。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 8｜SAA｜Warm standby 是否真能滿足30分鐘RTO

團隊稱已建立warm standby，但DR Region只有資料複本與一台bastion，沒有application stack；RTO要求30分鐘。最準確的評估是什麼？

A. 目前只是pilot light或backup/restore；warm standby需可運作的縮小application stack並演練scale-out
B. 只要降低DNS TTL至30秒，即使DR Region沒有runtime、keys與quota也能符合30分鐘RTO
C. 應直接改成full-scale active-active；warm standby在AWS上無法支援任何RTO小於一小時的workload
D. 這已是warm standby，因任何一台EC2都代表完整application可隨時承接traffic

**答案：A**

- **A：** 正確。Warm standby必須有可運作的縮小副本；只有資料和bastion沒有serving path，名稱不能取代實測scale-out與cutover。
- **B：** 錯誤。DNS只改traffic destination；沒有runtime、identity、keys、artifact與quota時，快切DNS仍無服務可接。
- **C：** 錯誤。Warm standby可支援較短RTO，前提是縮小stack、資料與依賴已運行，且擴容流程經演練。
- **D：** 錯誤。Bastion提供管理入口，不代表application、dependencies與capacity已在DR Region運行。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Creating a backup plan](https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup-plan.html)、[Restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 9｜SAP｜DR declaration 與 failback

跨 Region DR runbook 要避免 split-brain 並可安全 failback。選擇兩項。

A. 當standby與console均顯示healthy就立即failback，之後再比較兩Region寫入差異
B. 允許兩Regions在恢復期間同時接受writes，再以最後寫入時間自動選winner完成reconciliation
C. 定義 data reconciliation、old Region reintegration、business validation、rollback/failback owner 並演練
D. 定義 declaration authority、ordered automation、communication、old-writer fencing 與 degraded-operation limits
E. 由當班工程師自行決定declaration與failback，不預先指定authority以保持事故彈性

**答案：C、D**

- **A：** 錯誤。Health不是writer authority；failback前必須fence、reconcile、重整replication並驗證business state。
- **B：** 錯誤。若application沒有明確multi-writer conflict semantics，會造成split-brain與不可安全合併的資料。
- **C：** 正確。Failback前要先reconcile資料、重建replication、驗證business state並指定owner；它本身是一個需演練且可停止的受控migration。
- **D：** 正確。具名declaration authority避免延誤或重複決策；ordered automation與old-writer fencing確保新Region接管時不產生split-brain。
- **E：** 錯誤。現場判斷仍需要，但沒有具名authority、stop condition與communication會延長RTO並增加雙寫風險。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Switchover and failover for Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 10｜SAP｜以演練時間線量化實際RTO與資料損失窗口

一次DR演練記錄：事故09:00、宣告09:12、最後可用recovery point08:54、服務恢復09:47、第一筆正確訂單09:52。哪兩項是正確證據？

A. 只要standby console顯示available，就能忽略identity、network、KMS與downstream transaction驗證
B. 應以最後已驗證committed write與recovered data比較資料損失窗口；08:54 recovery point最多先提供6分鐘的候選RPO證據
C. 宣告花12分鐘屬人工流程，不應計入RTO；RTO只計database restore API duration
D. Backup job在08:54可見，所以RPO必為0分鐘，無須檢查09:00前最後一次成功寫入
E. 若business recovery定義為正確訂單成功，實測RTO為52分鐘，而不是只看09:47資源健康

**答案：B、E**

- **A：** 錯誤。Resource availability只是中間站；DR完成仍需驗證principal、path、key與完整business transaction。
- **B：** 正確。RPO evidence應比較事件前最後commit與recovered state；08:54相對09:00先顯示6分鐘候選窗口。
- **C：** 錯誤。Detection、declaration與approval都在business outage內，除非業務另有明確且合理的量測起點。
- **D：** 錯誤。Recovery point時間不等於零資料損失；還要知道最後成功寫入與還原後實際存在的資料。
- **E：** 正確。RTO起於disruption並止於預先定義的business service恢復；本題以正確訂單為終點，因此是52分鐘。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先分解資料與dependency的RPO/RTO，再選backup、replication、standby…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「相同AWS服務可組成不同恢復能力，真正contract來自資料流與演練。」，所以「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」能直接滿足它；若constraint改成「Service SLA與DR目標相關但不等價；application還有部署與操作時間。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」。替代方案「Service SLA與DR目標相關但不等價；application還有部署與操作時間。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「相同AWS服務可組成不同恢復能力，真正contract來自資料流與演練。」，排除會導致「購買Global Database便宣稱RTO為零，沒有automation、fencing與runbook。」的選項，再選「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先分解資料與dependency的RPO/RTO，再選backup、replication、standby與routing。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「recovery objectives are end-to-end properties」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 115 章　Cost 是 Architecture Constraint

成本不是設計完成後才清理；data path、availability與營運選擇一開始就決定大部分支出。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

故事從一個看似簡單的需求開始：兩方案月費相近，但其中一個需要兩名工程師全年維護cluster。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：成本不是設計完成後才清理；data path、availability與營運選擇一開始就決定大部分支出。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Cost Explorer會是本章的主要角色，AWS Cost and Usage Report則幫我們看清邊界。方向是「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：兩方案月費相近，但其中一個需要兩名工程師全年維護cluster。

商業需求與不能妥協的限制
          ▼
[AWS Cost Explorer：主要責任]
          │ 互動分析歷史與預測成本、usage與RI/SP coverage。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Cost and Usage Report：輸出最細AWS billing line items到S3供查詢與chargeback。
  · AWS Compute Optimizer：根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
可移植原則：architecture is economics expressed as technical structure

失敗時先找：只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問AWS Cost Explorer有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Cost Explorer和AWS Cost and Usage Report並不是兩個任意的產品名稱。前者適合本章，是因為「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」直接回應了眼前的問題；後者描述的「最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「architecture is economics expressed as technical structure」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 |
| AWS Cost and Usage Report | 輸出最細AWS billing line items到S3供查詢與chargeback。 | 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。 |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 |

## 把全圖套進一個具體案例

**場景：** 兩方案月費相近，但其中一個需要兩名工程師全年維護cluster。

1. 故事的起點：兩方案月費相近，但其中一個需要兩名工程師全年維護cluster。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Cost Explorer負責「互動分析歷史與預測成本、usage與RI/SP coverage。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Cost and Usage Report、AWS Compute Optimizer各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Cost Explorer

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：成本不是設計完成後才清理；data path、availability與營運選擇一開始就決定大部分支出。
- **具體例子／邊界：** 在「兩方案月費相近，但其中一個需要兩名工程師全年維護cluster。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Cost and Usage Report

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：architecture is economics expressed as technical structure。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Cost and Usage Report

AWS提供細粒度billing line items與resource IDs的資料集，可輸出到S3供Athena/BI做自訂分析。

### unit economics

以每成功交易、每tenant、每GB或其他business unit計算成本，比只看單一instance月費更能比較架構。

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### chargeback

把資源與共享平台成本實際分攤到business/team budget，需要穩定accounts、tags與allocation rules。

### showback

把共享與直接成本顯示給使用團隊但不實際轉帳，先建立成本可見性與行為回饋。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### AWS Cost Explorer

- **功用：** 互動分析歷史與預測成本、usage與RI/SP coverage。
- **底層機制：** Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。
- **關鍵設定：** date/granularity、filters/group by、cost metric、forecast、RI/SP reports與cost allocation tags。
- **選擇時機：** 回答成本趨勢、來源、forecast與commitment coverage。
- **替換時機：** 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。

### AWS Cost and Usage Report

- **功用：** 輸出最細AWS billing line items到S3供查詢與chargeback。
- **底層機制：** 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。
- **關鍵設定：** report/data export、S3 bucket、time granularity、resource IDs、split cost allocation與format。
- **選擇時機：** FinOps、showback/chargeback、unit economics與自訂cost allocation。
- **替換時機：** 快速互動圖表用Cost Explorer；通知閾值用Budgets。

### AWS Compute Optimizer

- **功用：** 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
- **底層機制：** 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。
- **關鍵設定：** opt-in、lookback、enhanced infrastructure metrics、external metrics ingestion與recommendation preferences。
- **選擇時機：** 找over/under-provisioned resources並建立rightsizing候選。
- **替換時機：** 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。

## 考前與實作時再查：設定操作手冊

### AWS Cost Explorer：逐項設定說明

#### `date/granularity`

- **控制什麼：** `date/granularity`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `filters/group by`

- **控制什麼：** `filters/group by`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `cost metric`

- **控制什麼：** `cost metric`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `forecast`

- **控制什麼：** `forecast`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `RI/SP reports`

- **控制什麼：** `RI/SP reports`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `cost allocation tags`

- **控制什麼：** `cost allocation tags`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「回答成本趨勢、來源、forecast與commitment coverage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost Explorer建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### AWS Cost and Usage Report：逐項設定說明

#### `report/data export`

- **控制什麼：** `report/data export`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「FinOps、showback/chargeback、unit economics與自訂cost allocation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost and Usage Report的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `S3 bucket`

- **控制什麼：** `S3 bucket`指定AWS Cost and Usage Report讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `time granularity`

- **控制什麼：** `time granularity`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「FinOps、showback/chargeback、unit economics與自訂cost allocation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost and Usage Report設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `resource IDs`

- **控制什麼：** `resource IDs`指定AWS Cost and Usage Report讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `split cost allocation`

- **控制什麼：** `split cost allocation`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「FinOps、showback/chargeback、unit economics與自訂cost allocation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost and Usage Report設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `format`

- **控制什麼：** `format`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「FinOps、showback/chargeback、unit economics與自訂cost allocation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Cost and Usage Report依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

### AWS Compute Optimizer：逐項設定說明

#### `opt-in`

- **控制什麼：** `opt-in`決定AWS Compute Optimizer收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。
- **何時需要：** 要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。
- **怎麼設定／驗證：** 選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。
- **常見錯法：** 樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。

#### `lookback`

- **控制什麼：** `lookback`決定AWS Compute Optimizer收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。
- **何時需要：** 要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。
- **怎麼設定／驗證：** 選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。
- **常見錯法：** 樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。

#### `enhanced infrastructure metrics`

- **控制什麼：** `enhanced infrastructure metrics`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「找over/under-provisioned resources並建立rightsizing候選。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Compute Optimizer選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `external metrics ingestion`

- **控制什麼：** `external metrics ingestion`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「找over/under-provisioned resources並建立rightsizing候選。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Compute Optimizer選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `recommendation preferences`

- **控制什麼：** `recommendation preferences`決定AWS Compute Optimizer收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。
- **何時需要：** 要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。
- **怎麼設定／驗證：** 選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。
- **常見錯法：** 樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。

## 讀到這裡，請用自己的話說一次

1. AWS Cost Explorer的責任：互動分析歷史與預測成本、usage與RI/SP coverage。
2. 底層機制：Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。
3. 第一個要看的設定：date/granularity、filters/group by、cost metric、forecast、RI/SP reports與cost allocation tags。
4. 選擇邏輯：以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。
5. 不要混淆：AWS Cost and Usage Report的責任是「輸出最細AWS billing line items到S3供查詢與chargeback。」；它不會自動取代AWS Cost Explorer。
6. 替換訊號：逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。
7. 最常見錯法：只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。
8. 可移植原則：architecture is economics expressed as technical structure。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 | 回答成本趨勢、來源、forecast與commitment coverage。 | 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。 |
| AWS Cost and Usage Report | 輸出最細AWS billing line items到S3供查詢與chargeback。 | 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。 | FinOps、showback/chargeback、unit economics與自訂cost allocation。 | 快速互動圖表用Cost Explorer；通知閾值用Budgets。 |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 | 找over/under-provisioned resources並建立rightsizing候選。 | 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。 | 只有當題目條件明確改變時才可能合理。 | 只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。」之間做選擇。
- 認得常考設定：date/granularity、filters/group by、cost metric、forecast、RI/SP reports與cost allocation tags。
- 對應官方tasks：SAA-4.1 Design cost-optimized storage solutions；SAA-4.2 Design cost-optimized compute solutions；SAA-4.3 Design cost-optimized database solutions；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。
- 對應官方tasks：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAA｜Unit economics

月帳單從 10 萬增至 12 萬，但成功訂單從 100 萬增至 150 萬。哪個指標最能判斷效率？

A. 以AWS account數量作為成本效率分母；帳號增加較慢就代表每個產品的unit cost改善；failed與cancelled訂單仍算入成功分母，使unit cost看似改善但無法反映有效產出
B. 以每筆成功訂單成本判斷：由0.10降至0.08，並分離fixed、variable與failed-work成本
C. 只看月總帳單由10萬增至12萬，將20%成長直接判定為效率退化
D. 只看 instance 單價

**答案：B**

- **A：** 錯誤。Account是治理邊界，不是business output；不能解釋成功訂單增加後每單成本由0.10降至0.08。
- **B：** 正確。每單成本由100,000/1,000,000=0.10降為120,000/1,500,000=0.08；再分離failed/cancelled work才能判斷效率是否真的改善。
- **C：** 錯誤。總額忽略成功訂單成長50%；需計算每成功訂單成本並分離failed/cancelled work。
- **D：** 錯誤。單價不等於整體單位成本；這只比較單價或總額，沒有以成功業務單位、usage driver與failed work計算真正效率。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Analyzing your costs with AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)

### 練習題 2｜SAP｜Cost allocation

共享account有40% spend無法歸屬產品；部分cost allocation tags今天才啟用。第一個治理動作為何？

A. 只依resource Name tag或命名規則回推所有歷史成本；即使資源當時沒有owner metadata也視為精確chargeback
B. 把更多產品放入同一shared account，再用每月總EC2成本按人數平均分配storage、network與support費
C. 先停用所有未分配資源；只要當月帳單下降，就不需要owner、cost category或歷史backfill
D. 建立account/cost category/tag ownership與unallocated-spend指標；backfill只涵蓋期限內既有tag values

**答案：D**

- **A：** 錯誤。命名可作輔助heuristic，但不是可靠billing dimension；歷史上沒有tag時仍需account/category或明確分攤規則。
- **B：** 錯誤。平均分攤可作暫時共同成本規則，但會扭曲不同服務與資料傳輸驅動，不能取代ownership taxonomy。
- **C：** 錯誤。刪除前要先辨識owner與business value；成本下降也不能解決剩餘spend的歸屬與持續治理。
- **D：** 正確。先建立可持續的allocation contract；backfill可處理已存在tag的歷史啟用狀態，但不能創造當時不存在的tag value。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Backfilling cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)、[What are AWS Cost and Usage Reports?](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)

### 練習題 3｜SAP｜Cost Explorer vs CUR/Data Exports

Finance 要互動看趨勢/forecast；FinOps 另要 resource-level line items 進 Athena 做 custom chargeback。工具如何分工？

A. 使用Cost Explorer篩選趨勢後直接修改或停止高成本resources，省略變更審批與執行工具
B. 用AWS Budgets匯出每筆resource line item到Athena，並以budget threshold取代互動式forecast
C. Cost Explorer 做互動趨勢/forecast；CUR/Data Exports 提供細粒度資料供自訂 SQL/BI
D. CUR/Data Exports 只提供即時 request latency

**答案：C**

- **A：** 錯誤。Cost Explorer提供分析與forecast，不是resource control plane；實際變更仍由服務API、IaC或營運流程執行。
- **B：** 錯誤。Budgets適合門檻、forecast通知與actions，不取代Data Exports的細粒度billing dataset。
- **C：** 正確。Cost Explorer適合互動式趨勢與forecast；CUR 2.0/Data Exports提供可進Athena的resource-level line items，供自訂chargeback與深度分析。
- **D：** 錯誤。Billing dataset 非 request telemetry。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Analyzing your costs with AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)、[Processing AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-processing.html)、[Managing your costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)

### 練習題 4｜SAA｜Rightsizing validation

Compute Optimizer建議縮小一個Amazon RDS DB instance以省35%，但季度結算時memory、network與EBS IOPS/throughput接近上限，且需保留failover headroom。應怎麼做？

A. 驗證memory/network/EBS、seasonal peak與failover headroom後再縮小RDS
B. 依平均 CPU 與過去十四天低利用率直接縮小一級，另以 CUR line item、變更窗口與月度 unit cost 驗證節省；不納入季度 memory、network、EBS 或 AZ failover headroom與結算尖峰
C. 移除Multi-AZ standby來取得立即節省，再以較大的primary instance補回failover headroom
D. 自動套用Compute Optimizer最低成本建議，將季度peak與failover capacity視為推薦模型已完整涵蓋

**答案：A**

- **A：** 正確。Rightsizing 必須在完整 resource/SLO 下驗證。
- **B：** 錯誤。CPU 不是唯一瓶頸；此方案能產生recommendation或報表，但沒有owner、change validation與post-change realized savings。
- **C：** 錯誤。Scale-up不提供AZ failover；若需求包含HA，移除standby會違反hard availability constraint。
- **D：** 錯誤。Recommendation是重要evidence，但仍需驗證seasonality、memory/network/EBS與failure headroom。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Viewing RDS DB instance recommendations](https://docs.aws.amazon.com/compute-optimizer/latest/ug/view-rds-recommendations.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 5｜SAA｜Data-path cost drivers

NAT 與 cross-AZ transfer 成為最大成本；private workers 主要讀同 Region S3，卻跨 AZ 走 NAT。最佳先做什麼？

A. 在另一AZ再建一個NAT Gateway，但維持所有private subnet route指向原本跨AZ NAT；以增加resource數量作為成本改善證據
B. 購買更多Compute Savings Plans來涵蓋NAT Gateway與data processing費；commitment會直接降低錯誤network path的每GB成本
C. 改用S3 interface endpoint且不比較費率、AZ placement或route；任何endpoint類型都必然比gateway endpoint低成本
D. 建立S3 gateway endpoint並更新相關route tables與endpoint policy，再比較NAT/cross-AZ bytes

**答案：D**

- **A：** 錯誤。Per-AZ NAT有助韌性，但若route仍跨AZ指向舊NAT，資料路徑與相關費用不會因多一個gateway自動改變。
- **B：** 錯誤。Savings Plans適用特定compute使用承諾，不會修正NAT/data-transfer架構成本或降低每GB NAT processing。
- **C：** 錯誤。Interface endpoint有不同小時與資料處理費；同Region S3大量流量通常應先評估無小時費的gateway endpoint。
- **D：** 正確。Gateway endpoint以route table導向S3且可設endpoint policy；先修正實際path，再用NAT/cross-AZ bytes驗證成本是否消失。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)、[Route tables for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Processing AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-processing.html)

### 練習題 6｜SAP｜以billing dimensions、資料新鮮度與部署事件定位成本尖峰

成本儀表板顯示昨日總成本增加60%，但application metrics沒有同幅流量成長。哪個調查順序最可靠？

A. 把Cost Explorer每小時圖當成秒級meter，與單筆request trace逐秒對齊；任何時間差都視為資料遺失
B. 先依account/service/Region/usage type縮小範圍，再查CUR/Data Exports line items並對齊變更時間
C. 立即終止帳單最高的resource；即使它是production writer，也先用總成本下降證明根因
D. 只比較public list price；忽略實際usage quantity、discount、credits、data transfer與購買模型；若新增費用集中在單一service就直接rightsizing，不再確認usage type與deployment原因

**答案：B**

- **A：** 錯誤。Billing datasets不是request telemetry，更新與彙總有延遲；應用指標用來關聯而不是逐秒一一對齊。
- **B：** 正確。先用billing dimensions定位費用類型，再下鑽line items並與變更時間對齊；billing新鮮度限制必須納入結論。
- **C：** 錯誤。緊急cost guardrail可暫停非關鍵資源，但未定位就刪production可能擴大事故且無法解釋新增usage type。
- **D：** 錯誤。List price是估算輸入，不能解釋實際帳單中的usage、discount、credit或network line item變化。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Analyzing your costs with AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)、[Processing AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-processing.html)、[Managing your costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)

### 練習題 7｜SAA｜Purchase model mix

全年穩定 40 workers，另有 0–200 個可重試尖峰。最佳 purchase mix？

A. 穩定 baseline 用合適 Savings Plans/RI 類承諾，彈性容錯尖峰用 diversified Spot，未知缺口用 On-Demand
B. 為0至200個尖峰workers全部購買長期commitment，以最高coverage避免任何On-Demand單價
C. 全部使用Dedicated Hosts，利用host isolation同時取得最低單價與最好的Spot彈性
D. 全部使用單一instance family與AZ的Spot pool，讓capacity集中以簡化排程與成本預測

**答案：A**

- **A：** 正確。Commitment覆蓋可預測baseline，Spot承擔可重試尖峰，On-Demand處理未承諾缺口；還要持續看coverage、utilization與Spot capacity風險。
- **B：** 錯誤。波動尖峰若未持續使用會降低commitment utilization；應先覆蓋穩定baseline。
- **C：** 錯誤。Dedicated Hosts適合特定license或隔離需求，並非一般可重試worker的預設最低成本方案。
- **D：** 錯誤。Spot適合可中斷尖峰，但單一pool增加容量與中斷相關性；應跨類型/AZ diversification。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[EC2 Spot best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Getting Savings Plans recommendations](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-recommendations.html)、[Using the Savings Plans coverage report](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-usingCR.html)、[Using the Savings Plans utilization report](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-usingPR.html)

### 練習題 8｜SAA｜Cost-optimized valid architecture

選項 A 單 AZ 最便宜；B 多 AZ 且符合 99.95% availability；C active-active 三 Region；需求明確 99.95% 且無全球 latency 需求。應如何選？

A. 選 C，服務最多必然正確
B. 移除monitoring與restore tests來降低B方案營運費，仍以架構圖上的Multi-AZ宣稱達到99.95%
C. 選 B，在先滿足 availability/security/performance 後選總成本最低的有效方案
D. 選單AZ方案A並購買更大的instance，利用垂直擴充降低硬體故障機率以達99.95%

**答案：C**

- **A：** 錯誤。三Region active-active超過99.95%與既定latency需求，增加常駐容量、跨Region資料與多writer營運成本，不能因服務較多就視為最優。
- **B：** 錯誤。缺少監測與測試會失去SLO evidence；成本優化不能靠隱藏availability風險。
- **C：** 正確。B先滿足明示availability且沒有多餘global-latency設計；在security與performance同樣合格後，才以TCO比較有效方案。
- **D：** 錯誤。較大instance不消除AZ或單點故障；A仍未滿足明示availability constraint。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 9｜SAP｜從cost anomaly到owner、變更與realized savings的閉環

FinOps 每月都匯出 cost recommendations，但半年後無法證明哪些建議已落地、由誰負責，或是否真的降低單位成本。哪兩項能建立可持續的改善閉環？

A. 指派 owner/budget，發布 allocation 與 unit-cost metrics，定期 review anomalies/recommendations
B. 每年budget season才review一次recommendations，把短期anomaly交由各服務autoscaling自行吸收
C. Recommendation export 後自動視為 savings
D. 變更先驗證 SLO/seasonality，再 canary，事後量測 realized savings 與 regression
E. 由Finance集中設定節省目標並直接批准rightsizing，engineering只在變更後處理SLO回歸

**答案：A、D**

- **A：** 正確。Owner、budget、allocation與unit-cost指標讓每項建議可被接受、排程或拒絕，並能從anomaly追到具名責任人。
- **B：** 錯誤。年度review適合策略規劃，但無法形成anomaly到owner、change與realized savings的及時閉環。
- **C：** 錯誤。建議不等於實現；這沒有修正實際data path或demand，commitment與帳單工具不能替代架構上的waste removal。
- **D：** 正確。Rightsizing或purchase變更先以seasonality、failure load與SLO驗證，之後再用unit cost和regression量測是否真的實現節省。
- **E：** 錯誤。Finance提供成本治理，但workload owner必須在變更前驗證capacity、seasonality與failure headroom。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)

### 練習題 10｜SAP｜Commitment coverage、waste removal與SLO regression的取捨

團隊目前On-Demand compute每月10萬美元，其中穩定baseline約6萬、閒置/過大資源2萬，其餘為可重試尖峰。哪兩項順序最能降低成本且避免鎖住浪費？

A. 只追蹤帳單總額，不量unit cost、commitment utilization/coverage或change後SLO regression
B. 立即對目前10萬美元全部購買三年commitment；之後再處理閒置，因coverage越高一定越省
C. 先移除/縮小已驗證的idle waste，並以peak與AZ-failure load test確認SLO、capacity與failover headroom
D. 刪除達成RPO所需的recovery points與incident logs，把下降金額算成realized savings而不追蹤風險
E. 對清理後可預測baseline評估Savings Plans/RI commitment；尖峰依可中斷性使用diversified Spot或On-Demand

**答案：C、E**

- **A：** 錯誤。總額可能隨需求變化；需同看unit economics、commitment指標與SLO，才能證明realized savings。
- **B：** 錯誤。Commitment可降低穩定使用單價，但先覆蓋閒置會降低utilization並限制後續rightsizing彈性。
- **C：** 正確。先去除不需要的demand可避免把commitment鎖在浪費上；load/failure測試確保節省沒有破壞SLO。
- **D：** 錯誤。這會把較高資料損失與較弱事故調查能力隱藏成節省，沒有保留原本RPO與營運contract。
- **E：** 正確。Commitment應匹配清理後的穩定baseline；可重試尖峰再依interruption與capacity風險選Spot/On-Demand。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Viewing RDS DB instance recommendations](https://docs.aws.amazon.com/compute-optimizer/latest/ug/view-rds-recommendations.html)、[EC2 Spot best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html)、[Processing AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-processing.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Getting Savings Plans recommendations](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-recommendations.html)、[Using the Savings Plans coverage report](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-usingCR.html)、[Using the Savings Plans utilization report](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-usingPR.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「成本不是設計完成後才清理；data path、availability與營運選擇一開始就決定大部分支出。」，所以「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」能直接滿足它；若constraint改成「最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」。替代方案「最低帳單不一定最佳，還要包含人力、風險、遷移與機會成本。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「成本不是設計完成後才清理；data path、availability與營運選擇一開始就決定大部分支出。」，排除會導致「只靠RI降低費用，沒有修正跨AZ流量、閒置資料與無限retention。」的選項，再選「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」。本章對應的代表task包括：SAA-4.1 Design cost-optimized storage solutions；SAA-4.2 Design cost-optimized compute solutions；SAA-4.3 Design cost-optimized database solutions；SAA-4.4 Design cost-optimized network architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以每transaction、tenant或GB的unit economics比較方案，將固定與變動成本分開。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「architecture is economics expressed as technical structure」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 116 章　Migration 由 Business Value 與 Dependency Graph 驅動

技術上可搬的順序不一定創造價值，也可能切斷高耦合dependency。

## 拿掉AWS名稱，看看設計是否仍然成立：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：公司要退出機房、提高發布速度並降低license，不只是複製VM。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：技術上可搬的順序不一定創造價值，也可能切斷高耦合dependency。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS Migration Hub負責主要工作，AWS Application Migration Service提醒我們答案不是永遠固定。本章會走向「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：公司要退出機房、提高發布速度並降低license，不只是複製VM。

商業需求與不能妥協的限制
          ▼
[AWS Migration Hub：主要責任]
          │ 集中追蹤migration portfolio、waves與多工具進度。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Application Migration Service：把physical、virtual或cloud servers以block replication搬到EC…
  · AWS Well-Architected Tool：在AWS中記錄Well-Architected reviews、milestones與improvemen…
可移植原則：migration completes when the business operating model changes

失敗時先找：Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「拿掉AWS名稱，看看設計是否仍然成立」。先不要急著問AWS Migration Hub有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Migration Hub和AWS Application Migration Service並不是兩個任意的產品名稱。前者適合本章，是因為「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」直接回應了眼前的問題；後者描述的「先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「migration completes when the business operating model changes」。更白話地說：用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 |

## 把全圖套進一個具體案例

**場景：** 公司要退出機房、提高發布速度並降低license，不只是複製VM。

1. 故事的起點：公司要退出機房、提高發布速度並降低license，不只是複製VM。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Migration Hub負責「集中追蹤migration portfolio、waves與多工具進度。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：彙整discovery與migration tools狀態，提供application grouping與journey visibility。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Application Migration Service、AWS Well-Architected Tool各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「它不搬資料本身；server用MGN、database用DMS、files用DataSync。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Migration Hub

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：技術上可搬的順序不一定創造價值，也可能切斷高耦合dependency。
- **具體例子／邊界：** 在「公司要退出機房、提高發布速度並降低license，不只是複製VM。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Application Migration Service

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：migration completes when the business operating model changes。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### dependency graph

以nodes/edges表示application、database、network、identity與外部系統的依賴，幫助避免把強耦合元件拆到不同waves。

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### migration

把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### refactor

重構application與data boundaries以使用cloud-native架構；潛在收益高，時間、風險與testing需求也最高。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### rehost

盡量不改application，把server搬到cloud IaaS；速度快但保留多數技術債與營運模式。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### AWS Migration Hub

- **功用：** 集中追蹤migration portfolio、waves與多工具進度。
- **底層機制：** 彙整discovery與migration tools狀態，提供application grouping與journey visibility。
- **關鍵設定：** home Region、discovery sources、applications、waves、connectors與orchestrator templates。
- **選擇時機：** 大型migration需要single pane追蹤而不是spreadsheet碎片。
- **替換時機：** 它不搬資料本身；server用MGN、database用DMS、files用DataSync。

### AWS Application Migration Service

- **功用：** 把physical、virtual或cloud servers以block replication搬到EC2。
- **底層機制：** Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。
- **關鍵設定：** replication template、staging subnet、launch template、post-launch actions、test/cutover與lag。
- **選擇時機：** rehost大量servers、低downtime cutover與DR-like migration。
- **替換時機：** database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。

### AWS Well-Architected Tool

- **功用：** 在AWS中記錄Well-Architected reviews、milestones與improvement plans。
- **底層機制：** Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
- **關鍵設定：** workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- **選擇時機：** 需要重複、可稽核的architecture review process。
- **替換時機：** 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。

## 考前與實作時再查：設定操作手冊

### AWS Migration Hub：逐項設定說明

#### `home Region`

- **控制什麼：** `home Region`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Migration Hub前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `discovery sources`

- **控制什麼：** `discovery sources`指定AWS Migration Hub讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `applications`

- **控制什麼：** `applications`定義AWS Migration Hub管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `waves`

- **控制什麼：** `waves`定義AWS Migration Hub管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `connectors`

- **控制什麼：** `connectors`把AWS Migration Hub與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `orchestrator templates`

- **控制什麼：** `orchestrator templates`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「大型migration需要single pane追蹤而不是spreadsheet碎片。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Migration Hub依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

### AWS Application Migration Service：逐項設定說明

#### `replication template`

- **控制什麼：** `replication template`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「rehost大量servers、低downtime cutover與DR-like migration。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Application Migration Service依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `staging subnet`

- **控制什麼：** `staging subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「rehost大量servers、低downtime cutover與DR-like migration。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Application Migration Service的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義AWS Application Migration Service建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `post-launch actions`

- **控制什麼：** `post-launch actions`把AWS Application Migration Service與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `test/cutover`

- **控制什麼：** `test/cutover`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

#### `lag`

- **控制什麼：** `lag`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

### AWS Well-Architected Tool：逐項設定說明

#### `workload`

- **控制什麼：** `workload`定義AWS Well-Architected Tool管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `Regions`

- **控制什麼：** `Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Well-Architected Tool前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `lenses`

- **控制什麼：** `lenses`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `milestones`

- **控制什麼：** `milestones`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `profiles`

- **控制什麼：** `profiles`定義AWS Well-Architected Tool管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `sharing`

- **控制什麼：** `sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「需要重複、可稽核的architecture review process。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Well-Architected Tool建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `improvement items`

- **控制什麼：** `improvement items`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

## 讀到這裡，請用自己的話說一次

1. AWS Migration Hub的責任：集中追蹤migration portfolio、waves與多工具進度。
2. 底層機制：彙整discovery與migration tools狀態，提供application grouping與journey visibility。
3. 第一個要看的設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
4. 選擇邏輯：以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。
5. 不要混淆：AWS Application Migration Service的責任是「把physical、virtual或cloud servers以block replication搬到EC2。」；它不會自動取代AWS Migration Hub。
6. 替換訊號：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
7. 最常見錯法：Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。
8. 可移植原則：migration completes when the business operating model changes。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 | 大型migration需要single pane追蹤而不是spreadsheet碎片。 | 它不搬資料本身；server用MGN、database用DMS、files用DataSync。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 | rehost大量servers、低downtime cutover與DR-like migration。 | database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。 |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 | 需要重複、可稽核的architecture review process。 | 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。 | 只有當題目條件明確改變時才可能合理。 | Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。」之間做選擇。
- 認得常考設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
- 對應官方tasks：SAP-4.1 Select existing workloads and processes for potential migration；SAP-4.2 Determine the optimal migration approach for existing workloads；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAP｜Business case 與 7 Rs

公司目標是退出機房、降低商業軟體 license 並提高發布速度。如何選 migration strategy？

A. 先將全部servers以rehost建立快速退出基線，再把retire、repurchase或replatform延後到搬遷後
B. 所有 workload 先 refactor，因必然最快
C. Retain 表示專案失敗
D. 依business driver與限制選7 Rs

**答案：D**

- **A：** 錯誤。兩階段策略有時合理，但若主要driver是license退出或SaaS repurchase，一律rehost會增加不必要雙重遷移。
- **B：** 錯誤。Refactor 通常變更最大；它忽略hard dependency與觀測窗口，wave切分後可能把latency或consistency風險留在混合環境。
- **C：** 錯誤。Retain可以是受法規、技術風險或短期退役計畫驅動的明確策略；它需要owner與重新評估日期，但不代表migration program失敗。
- **D：** 正確。退出機房偏向rehost/relocate或retire，降低license可能偏向repurchase/replatform，提高發布速度才可能支持refactor；不能先固定單一R。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Migration strategy: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)

### 練習題 2｜SAP｜Portfolio discovery 與 dependency graph

CMDB 三年未更新；團隊只有一週 flow logs。哪個 discovery 方案可信？

A. 以現有CMDB建立完整dependency graph，只對沒有owner的servers補一次短期network scan
B. 把觀測到的所有network connections都標為hard dependency，確保wave不會漏掉任何可能關係
C. 結合inventory、長期process/network觀測與owner訪談交叉驗證
D. 一週 flow 可發現所有月結/batch dependency

**答案：C**

- **A：** 錯誤。CMDB已三年未更新，只能作起始假設；需要足夠觀測窗口與owner訪談捕捉周期性dependency。
- **B：** 錯誤。保守收集可避免遺漏，但backup、monitoring與偶發管理流量不一定要求同wave，仍需分類與驗證。
- **C：** 正確。工具 evidence 與人員 knowledge 要互證。
- **D：** 錯誤。短窗口會漏周期工作；此方案推進了technical cutover，卻沒有business acceptance、service ownership與rollback deadline。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[Review groupings and waves in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 3｜SAP｜Dependency-aware waves

App 與 database 有低延遲 hard dependency，另有可延後報表。如何分 wave？

A. 把低延遲app/DB放同一move group；按readiness與風險分wave，報表可另波
B. 第一波放全部 mission-critical systems
C. 依server數量平均切waves，讓每波執行工時相近，再由跨WAN連線維持被拆散的dependencies
D. 把application與database拆成相鄰兩波，期間以VPN/Direct Connect跨WAN維持同步與低延遲

**答案：A**

- **A：** 正確。Move group 保留必要關係並限制 change scope。
- **B：** 錯誤。第一波同時放入全部mission-critical systems會放大未知流程、landing-zone與runbook缺陷；首波應可代表常見模式但具有限blast radius。
- **C：** 錯誤。平衡工時是次要因素；hard latency/data dependency應先形成move group，否則cutover引入長期混合環境風險。
- **D：** 錯誤。Hybrid bridge可短期使用，但hard low-latency dependency通常應同move group，避免將WAN變成新的critical path。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[Review groupings and waves in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 4｜SAP｜AWS Transform 與 Migration Hub 現況

2026 年新客戶要開始 portfolio discovery、application grouping 與 wave planning。應如何選服務？

A. 既有 Migration Hub projects 已被立即刪除
B. 把 AWS Transform 當 block-level replication agent
C. 新客戶仍以Migration Hub建立portfolio與waves，再把availability change視為只影響定價而非新專案存取
D. 新專案使用AWS Transform等current guidance；Migration Hub過渡僅供既有客戶完成進行中專案

**答案：D**

- **A：** 錯誤。Availability change沒有立即刪除既有Migration Hub專案；既有客戶可完成進行中工作，新客戶則應採目前官方規劃流程。
- **B：** 錯誤。Portfolio planning 不等於 server mover。
- **C：** 錯誤。官方availability change限制新客戶使用；新專案應依目前AWS Transform等current guidance規劃。
- **D：** 正確。新專案依 current guidance；舊專案有過渡邊界。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Migration Hub availability change](https://docs.aws.amazon.com/transform/latest/launchguide/migrationhub-availability-change.html)、[Review groupings and waves in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 5｜SAA｜MGN、DMS、DataSync 邊界

需求依序是 VM rehost、database full load+CDC、NFS files 搬 S3。正確工具對應？

A. VM使用DMS、database使用DataSync、NFS使用MGN，依資料量再調整每個工具的throughput
B. VM rehost用MGN、database full load+CDC用DMS、NFS到S3用DataSync
C. DataSync、MGN、DMS
D. 只用AWS Transform完成discovery、wave planning與三種資料搬移，省略MGN、DMS與DataSync

**答案：B**

- **A：** 錯誤。三者處理的state/protocol不同；增加throughput不能讓database mover變成VM block replication工具。
- **B：** 正確。分別對應 block server、database 與 file/object transfer。
- **C：** 錯誤。DataSync搬file/object、MGN做server block replication、DMS做database full load/CDC；此順序把三種資料模型全部配錯。
- **D：** 錯誤。Transform可協助規劃與轉換流程，但不等同三個專用movers的block、database CDC與file transfer能力。

**事實查證：** [AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[What is AWS Application Migration Service?](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)、[What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[What is AWS DataSync?](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)

### 練習題 6｜SAP｜MGN block replication、launch設定與cutover acceptance診斷

MGN cutover instances已啟動，但application無法go-live；本次範圍不含database engine migration或DMS CDC。下一步為何？

A. 檢查MGN replication/lifecycle、launch settings、network/IAM/KMS、外部依賴與business acceptance
B. 立刻decommission來源servers以避免雙跑費；若target失敗再從尚未驗證的backup重建
C. 查看DMS CDC latency作為MGN主要複寫指標；即使專案沒有DMS task也應以CDCLatencySource判定server cutover
D. 只確認EC2 state為running後finalize cutover；MGN的block replication完成即可證明DNS、identity與application transaction正常

**答案：A**

- **A：** 正確。MGN處理block-level server replication；go-live仍需驗證replication readiness、launch template、network/dependencies與業務交易。
- **B：** 錯誤。Decommission應在hypercare與acceptance後；提前刪除來源會失去最直接rollback path。
- **C：** 錯誤。DMS CDC是database migration指標，不是MGN block replication；題幹已明示沒有DMS task。
- **D：** 錯誤。Running只證明instance啟動；cutover finalization前仍應完成acceptance，否則會過早移除可回復來源。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Application Migration Service source-server migration metrics](https://docs.aws.amazon.com/mgn/latest/ug/source-server-migration-metrics.html)、[Launching cutover instances with AWS Application Migration Service](https://docs.aws.amazon.com/mgn/latest/ug/launch-cutover.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)

### 練習題 7｜SAP｜Realized migration benefit

VM 已在 EC2 運行，但機房、license 與雙跑仍未關閉。能否宣稱 business case 完成？

A. 只量migration wave是否準時，不再比較release frequency、SLO或dual-run exit，避免指標過多
B. 當target EC2 running且health check通過就宣告完成，source datacenter與license留待年度預算再處理
C. 不能；需計入migration factory與dual-run成本，驗證SLO、unit cost、release speed及source/license decommission
D. 只比較EC2與舊server的public list price，將migration factory、transfer、retraining與support列為沉沒成本

**答案：C**

- **A：** 錯誤。進度是factory指標，不能證明business case；發布速度、可靠性與decommission才反映遷移價值。
- **B：** 錯誤。技術切換可能完成，但business case仍承擔dual-run、license與機房成本，不能視為價值實現。
- **C：** 正確。Migration 結束於 operating model 與成本真正改變。
- **D：** 錯誤。TCO必須包含轉換與operating-model成本；忽略一次性與持續成本會扭曲realized benefit。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)

### 練習題 8｜SAP｜Rehost與異質資料庫replatform的工具責任

Legacy VM 要在 8 週內低變更退出機房；另一 database 可接受測試過的 engine change以降低 patch。如何選？

A. 兩者都使用DMS；DMS full load+CDC會複寫整台VM的OS、installed software與boot volume
B. VM以MGN做block-level rehost；異質database先做Schema Conversion，再以DMS full load+CDC搬資料
C. 兩者都使用MGN；block replication會把來源database schema自動轉成不同engine並修改application SQL
D. VM使用DataSync搬檔即可視為可開機rehost；database只建立空RDS instance並在cutover窗口首次測schema

**答案：B**

- **A：** 錯誤。DMS處理database資料遷移，不會建立可開機OS image或複寫完整VM runtime。
- **B：** 正確。MGN搬server block state；Schema Conversion/SCT處理異質schema/code，DMS則負責資料full load與CDC。
- **C：** 錯誤。MGN適合server rehost，但不理解不同database engine的schema、stored procedure或application SQL語意。
- **D：** 錯誤。DataSync適合file/object transfer，不是VM block replication；異質schema也應在cutover前完成assessment與驗證。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[What is AWS Application Migration Service?](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)、[Converting database schemas with DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion.html)、[What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[What is Amazon Relational Database Service?](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)

### 練習題 9｜SAP｜Migration factory的wave readiness、hypercare與模板回饋閉環

第一個 migration wave 已完成，但下一波仍重複遇到 landing-zone、cutover 與營運移交問題。哪兩項能讓 migration factory 從前一波學習且維持治理？

A. Migration team 永久擁有 production
B. 為 wave/app 指派 owner，檢查 landing-zone/security/operations readiness，演練 runbook 與 rollback authority
C. 所有 waves 同時進行，不設 resource limits
D. 設 hypercare/acceptance/operational handoff 與 post-wave metrics，把 lessons 更新模板與後續 waves
E. Cutover成功後立即關閉wave並讓migration team離場；service owner可在下一波開始前自行補齊runbook

**答案：B、D**

- **A：** 錯誤。應移交 service owner；此方案推進了technical cutover，卻沒有business acceptance、service ownership與rollback deadline。
- **B：** 正確。Preconditions 與 owner 降低 change risk。
- **C：** 錯誤。所有waves同時進行會爭用migration factory、landing-zone quota與change windows，首波lesson也來不及更新後續模板。
- **D：** 正確。Feedback loop 才形成 migration factory。
- **E：** 錯誤。沒有hypercare、acceptance與operational handoff，問題不會回饋模板，production也會留下ownership gap。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[Review groupings and waves in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 10｜SAP｜Migration完成、營運移交與來源decommission gate

一個migration wave已切流量到AWS。哪兩項共同證明可以結束hypercare並有條件decommission來源？

A. Benefit owner確認dual-run退出、license/contract終止與realized cost/release目標；依保留政策關閉來源並保存必要evidence
B. 永久保留來源與所有licenses但不指定owner；只要AWS端可用，就把雙跑成本排除在business case之外
C. Business transactions、SLO、資料reconciliation與rollback deadline均通過，service owner正式接受runbook、alarms與on-call責任
D. Target instances顯示running且migration team可以登入；不需驗證downstream、成本或使用者結果
E. 為避免額外費用，在business acceptance前立即刪除來源與最後可用rollback artifacts

**答案：A、C**

- **A：** 正確。Migration價值要以dual-run和license真正退出來實現；decommission仍須服從rollback與records-retention gate。
- **B：** 錯誤。有限保留可支援rollback，但永久雙跑且無owner會讓成本與攻擊面持續，表示business case尚未完成。
- **C：** 正確。完成條件包含端到端acceptance與operational handoff；migration team不能在沒有service ownership時直接離場。
- **D：** 錯誤。Resource state與登入能力只是技術中間站，沒有證明資料、dependencies、SLO或營運責任已成立。
- **E：** 錯誤。提前刪除來源會移除可逆性；應先通過acceptance並到達預定rollback deadline。

**事實查證：** [AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[Review groupings and waves in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以business outcome、風險、dependency與學習價值排序waves，完成後量測bene…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「技術上可搬的順序不一定創造價值，也可能切斷高耦合dependency。」，所以「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」能直接滿足它；若constraint改成「先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」。替代方案「先搬簡單系統可建立能力，但若完全不碰代表性dependency就無法驗證factory。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「技術上可搬的順序不一定創造價值，也可能切斷高耦合dependency。」，排除會導致「Migration成功定義成server已啟動，卻沒有關閉data center或改善SLO/成本。」的選項，再選「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」。本章對應的代表task包括：SAP-4.1 Select existing workloads and processes for potential migration；SAP-4.2 Determine the optimal migration approach for existing workloads；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以business outcome、風險、dependency與學習價值排序waves，完成後量測benefit。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「migration completes when the business operating model changes」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
