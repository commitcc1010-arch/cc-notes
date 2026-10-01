---
title: "Reliability、Performance 與 Cost"
part: 6
as_of: 2026-10-01
---

# Part 6　Reliability、Performance 與 Cost

# 第 61 章　Multi-AZ、Multi-Region 與 Fault Domains

副本只有放在獨立failure domain，才能抵抗對應範圍的故障。

## 從故障發生的那一刻倒推：先從故事開始

故事從一個看似簡單的需求開始：服務要抵抗AZ故障；只有法規與極低RTO服務需要跨Region運作。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：副本只有放在獨立failure domain，才能抵抗對應範圍的故障。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Availability Zones會是本章的主要角色，AWS Regions則幫我們看清邊界。方向是「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：服務要抵抗AZ故障；只有法規與極低RTO服務需要跨Region運作。

正常production路徑
          ▼
[Availability Zones] → 使用者可觀察的結果
          │ 在同一Region內提供可彼此隔離的資料中心級failure domains。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · AWS Regions：隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。
  · Amazon Route 53：提供authoritative DNS、health check與多種流量政策。

失敗時先找：將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Availability Zones有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Availability Zones和AWS Regions並不是兩個任意的產品名稱。前者適合本章，是因為「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」直接回應了眼前的問題；後者描述的「Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「resilience is limited by the largest shared dependency」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 |
| AWS Regions | 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。 | 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |

## 把全圖套進一個具體案例

**場景：** 服務要抵抗AZ故障；只有法規與極低RTO服務需要跨Region運作。

1. 故事的起點：服務要抵抗AZ故障；只有法規與極低RTO服務需要跨Region運作。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Availability Zones負責「在同一Region內提供可彼此隔離的資料中心級failure domains。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Regions、Amazon Route 53各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Availability Zones

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：副本只有放在獨立failure domain，才能抵抗對應範圍的故障。
- **具體例子／邊界：** 在「服務要抵抗AZ故障；只有法規與極低RTO服務需要跨Region運作。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Regions

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：resilience is limited by the largest shared dependency。
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

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

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

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Availability Zones

- **功用：** 在同一Region內提供可彼此隔離的資料中心級failure domains。
- **底層機制：** AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。
- **關鍵設定：** subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
- **選擇時機：** 幾乎所有production regional workload的第一層高可用設計。
- **替換時機：** 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。

### AWS Regions

- **功用：** 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。
- **底層機制：** 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。
- **關鍵設定：** Region選擇、service availability、data residency、cross-Region replication與transfer cost。
- **選擇時機：** 法規、使用者延遲、DR或服務可用性要求必須指定地理位置時。
- **替換時機：** 只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

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

### AWS Regions：逐項設定說明

#### `Region選擇`

- **控制什麼：** 決定workload部署在哪個地理AWS區域；它同時影響使用者延遲、data residency、服務可用性、價格與故障隔離。
- **何時需要：** 建立任何production workload、跨Region DR，或法規指定資料必須位於特定國家／區域時。
- **怎麼設定／驗證：** 建立候選Region矩陣，逐項驗證使用者latency、法規、所需服務／instance types、quota、價格與DR配對，再把Region做成IaC參數。
- **常見錯法：** 只選離使用者最近的Region可能違反資料位置或缺少必要服務；只選最便宜Region也可能增加延遲與跨Region傳輸費。

#### `service availability`

- **控制什麼：** 表示某項AWS服務、功能、instance family或managed integration是否已在目標Region提供；不同Region不保證功能完全相同。
- **何時需要：** 架構使用較新服務、特定accelerator、Local Zone、Global Database或跨服務整合時，必須在設計階段確認。
- **怎麼設定／驗證：** 逐一檢查官方Regional Services清單與產品文件，並在目標account/Region呼叫Describe/List API或以小型IaC stack驗證；同時確認quota。
- **常見錯法：** Console中看得到服務名稱不代表所需feature、engine version或capacity可用；DR Region也不能假設和primary完全對稱。

#### `data residency`

- **控制什麼：** 描述資料必須儲存、處理或備份在哪些地理邊界，以及哪些metadata、logs、keys或support流程也受限制。
- **何時需要：** 受法規、客戶合約、資料主權、安全分類或跨境傳輸規則約束，且必須留下可稽核部署證據時。
- **怎麼設定／驗證：** 先分類data types與允許位置，再檢查每個service的storage、backup、replication、logging與KMS Region；用SCP／Config與IaC guardrails限制部署位置。
- **常見錯法：** 只把主database放在指定Region不夠；backup、log、snapshot copy、analytics export與support evidence也可能把資料帶到其他Region。

#### `cross-Region replication`

- **控制什麼：** 把資料或artifact非同步／同步複製到另一Region，以支援讀取延遲、災難復原或資料分發；不同服務的一致性與failover語意不同。
- **何時需要：** 整個Region中斷仍需達到指定RPO/RTO，或全球讀取需要在地副本時。
- **怎麼設定／驗證：** 選擇authoritative writer、replication destination、KMS keys、網路與conflict規則；持續監控lag，並演練promotion、DNS切換與failback。
- **常見錯法：** 有副本不代表可立即接手，也不等於backup；錯誤刪除可能同步複製，client與dependencies也可能仍指向舊Region。

#### `transfer cost`

- **控制什麼：** 計算資料跨AZ、跨Region、經NAT／Transit Gateway／Internet或回源時的流量費；方向與路徑會影響計價。
- **何時需要：** 高流量架構、集中式inspection、跨Region資料庫、data lake或CDN origin設計時。
- **怎麼設定／驗證：** 畫出每GB的實際data path與方向，使用Pricing Calculator及Cost and Usage Report驗證；監控NAT、cross-AZ與inter-Region bytes並計算每筆交易成本。
- **常見錯法：** 只比較compute單價會漏掉巨額網路費；為了省錢把所有元件塞同一AZ，又可能破壞availability要求。

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

1. Availability Zones的責任：在同一Region內提供可彼此隔離的資料中心級failure domains。
2. 底層機制：AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。
3. 第一個要看的設定：subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
4. 選擇邏輯：先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。
5. 不要混淆：AWS Regions的責任是「隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。」；它不會自動取代Availability Zones。
6. 替換訊號：需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。
7. 最常見錯法：將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。
8. 可移植原則：resilience is limited by the largest shared dependency。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 | 幾乎所有production regional workload的第一層高可用設計。 | 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。 |
| AWS Regions | 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。 | 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。 | 法規、使用者延遲、DR或服務可用性要求必須指定地理位置時。 | 只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。 | 只有當題目條件明確改變時才可能合理。 | 將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。」之間做選擇。
- 認得常考設定：subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜依故障範圍選擇 Multi-AZ 或 Multi-Region

某公司的訂單 API 目前把三台 EC2 都放在 us-east-1a。業務要求單一 Availability Zone 故障時仍可下單，但未要求整個 Region 中斷時繼續服務，也希望先控制成本與操作複雜度。哪個改造最符合需求？

A. 將負載平衡器與 Auto Scaling group 分布到至少兩個 AZ，並確認資料層與必要依賴也具有跨 AZ 的復原能力
B. 在同一個 AZ 再增加三台 EC2，因為六台執行個體代表六個故障網域
C. 在 us-east-1a 建立兩個 subnet，讓每組 EC2 使用不同 subnet
D. 直接建立第二個 Region 的完整 active-active 系統，因為所有 production workload 都必須 Multi-Region

**答案：A**

- **A：** 正確。需求的故障範圍是單一 AZ，計算、入口與狀態依賴都跨 AZ 才能真正抵抗該故障；一個 AZ 可包含一個或多個離散資料中心。
- **B：** 錯誤。同一 AZ 內的更多 instances 只能改善個別主機故障，無法隔離 AZ 級電力、網路或基礎設施事件。
- **C：** 錯誤。Subnet 本身不形成新的 AZ；兩個 subnet 若都在 us-east-1a，仍共享同一 AZ 故障邊界。
- **D：** 錯誤。Multi-Region 可處理 Region 級需求，但題目未要求，且會引入跨 Region 資料、部署與營運複雜度。

**事實查證：** [AWS Regions and Availability Zones](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions-availability-zones.html)、[AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 2｜SAP｜找出假 Multi-AZ 架構中的共享依賴

一個 checkout 服務的 ALB 與 EC2 已分布在三個 AZ，RDS 也啟用 Multi-AZ。團隊要驗證「失去任一 AZ 仍可完成付款」。哪兩項檢查最可能揭露仍存在的單一 AZ 失敗點？（選兩項）

A. 只確認 Auto Scaling group 的 desired capacity 大於 1
B. 確認每個 AZ 的 private subnet 是否都把對外流量路由到同 AZ 可用的 NAT 路徑，且失去一個 AZ 後剩餘路徑有足夠容量
C. 把所有 instance type 改成同一系列，方便統一採購
D. 確認付款服務使用的 secret、queue、KMS 權限與第三方連線不依賴失敗 AZ 中唯一的 endpoint 或 appliance
E. 只查看 RDS 主控台是否顯示 Multi-AZ

**答案：B、D**

- **A：** 錯誤。Instance 數量沒有說明它們分布在哪裡，也沒有涵蓋 egress、state 與安全依賴。
- **B：** 正確。跨 AZ compute 若共用另一 AZ 的唯一 NAT 或 inspection path，仍會在該路徑故障時一起失效，且 surviving path 也可能容量不足。
- **C：** 錯誤。Instance family 一致性是容量與成本議題，不能證明 end-to-end 的故障隔離。
- **D：** 正確。完整可用性受最大共享依賴限制；唯一 endpoint、key path、queue 或外部連線都可能推翻 Multi-AZ 宣稱。
- **E：** 錯誤。RDS 的 Multi-AZ 標籤只描述資料庫拓撲，不能代表整個交易路徑都跨 AZ。

**事實查證：** [AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)、[NAT gateway connectivity types](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)、[SAP-C02 Domain 1: Design for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)

### 練習題 3｜SAA｜區分 RDS Multi-AZ 與 read replica

一個 RDS MySQL 資料庫需要在 AZ 故障時由 AWS 管理 failover；目前讀取量不高，但業務不能接受把非同步 replica 的舊資料當成同步 HA。應優先選擇哪個設計？

A. 建立一個跨 Region read replica，並把它當作同步 standby
B. 建立多個 read replicas，讓應用程式同時對所有 replicas 寫入
C. 啟用合適的 RDS Multi-AZ deployment，並讓應用程式使用資料庫端點與重連機制
D. 把所有讀取送到一般 Multi-AZ standby，因為每種 Multi-AZ 拓撲都提供 reader endpoint

**答案：C**

- **A：** 錯誤。一般 read replica 使用非同步複寫，主要用於讀取擴展或 DR 元件，不能直接等同同步 AZ HA。
- **B：** 錯誤。RDS read replica 不是多主寫入節點；一般寫入仍應送往 writer。
- **C：** 正確。RDS Multi-AZ 是符合題目之 managed availability/failover 需求的選項；failover 後既有連線仍需由 client 重建。
- **D：** 錯誤。Readable standby 與 reader endpoint 取決於特定 Multi-AZ deployment 類型，不能對所有拓撲一概而論。

**事實查證：** [Amazon RDS Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Working with Amazon RDS read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 練習題 4｜SAA｜AZ evacuation 後的剩餘容量

一個 web tier 平時在三個 AZ 各有 4 台 instances，尖峰需要至少 8 台才能符合 latency SLO。ALB 與 Auto Scaling 都已跨三個 AZ。團隊要證明失去一個 AZ 後仍可承載尖峰，最重要的下一步是什麼？

A. 只開啟 cross-zone load balancing；只要流量能跨區，容量一定足夠
B. 在同一 AZ 放置已停止的 standby instances，等故障時再啟動
C. 把每台 instance 的 EBS volume 加倍，因為儲存量可取代 compute capacity
D. 以失去一個 AZ 的條件做負載測試，驗證剩餘 8 台、Auto Scaling、下游與 quotas 都能維持 SLO

**答案：D**

- **A：** 錯誤。Cross-zone 能分配流量，但不會憑空產生 targets、下游連線或 service quota headroom。
- **B：** 錯誤。同 AZ 的停止 instances 會和該 AZ 一起不可用，且啟動時仍可能遇到容量不足。
- **C：** 錯誤。EBS 容量與 web tier 的可服務運算容量是不同限制。
- **D：** 正確。數學上剩餘 8 台剛好等於需求，不含 headroom；必須用 evacuation load 驗證 readiness、下游容量與擴展時序。

**事實查證：** [AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)、[EC2 Auto Scaling target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)

### 練習題 5｜SAP｜判斷 Multi-Region 的必要性

某內部報表系統可接受 8 小時停機與前一晚資料，使用者都在單一國家；現有 Multi-AZ 設計已通過 AZ game day。架構委員會提議改為雙 Region active-active。哪個評估最合理？

A. 要求先提出 Region loss、資料主權或全球 latency 的明確目標，再比較 Multi-Region 的資料一致性、部署、觀測與成本負擔
B. 立即採用 active-active，因為任何 Multi-AZ 系統都不算 production-ready
C. 只把每日 backup 複製到另一 Region，並宣稱應用已是 active-active
D. 只在第二 Region 建立空 VPC；只要 VPC 存在就可達成 8 小時 RTO

**答案：A**

- **A：** 正確。Multi-Region 應由區域失效、法規或全球服務目標驅動；低 RTO/RPO 需求未必值得承擔 active-active 的長期複雜度。
- **B：** 錯誤。Production 並不一律要求 Multi-Region；設計要和具體 business continuity 目標匹配。
- **C：** 錯誤。跨 Region backup 是 DR 資料元件，不會讓第二地區立即接收流量或擁有完整依賴。
- **D：** 錯誤。空 VPC 沒有 application、data、identity、capacity 與 runbook，不能證明可在 RTO 內恢復。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)

### 練習題 6｜SAP｜雙 Region 架構的隱藏共享依賴

一個 API 在兩個 Regions 都有 compute 與資料庫，但安全審查發現仍可能因單一 Region 故障而兩地同時無法部署或解密。哪兩項改造最直接降低這種風險？（選兩項）

A. 把兩地的 artifact 都只保存在 primary Region 的單一 S3 bucket
B. 讓所有 emergency operator 只能透過 primary Region 的唯一 bastion 登入
C. 確保 recovery Region 能取得受控的 artifacts、secrets 與所需 KMS key，並測試在 primary 不可用時的部署與解密路徑
D. 把 artifacts 複製到 recovery Region，但 secrets、KMS 解密權限與緊急身分驗證仍只依賴 primary Region
E. 盤點 DNS、憑證、identity、quotas 與第三方依賴，為其中的單點建立獨立 recovery path

**答案：C、E**

- **A：** 錯誤。Recovery deployment 仍需跨回失敗 Region 讀 artifact，會製造共享單點。
- **B：** 錯誤。唯一 bastion 讓 operator access 本身成為 primary Region 依賴。
- **C：** 正確。資料平面之外，artifact、secret 與 key 的可用性會直接決定第二 Region 是否真的能啟動。
- **D：** 錯誤。複製 artifact 只消除一段依賴；若 secrets、KMS 或 emergency identity 仍錨定 primary，recovery stack 依舊無法完成部署與解密。
- **E：** 正確。雙 Region 聲明必須包含完整 dependency graph；global 名稱也不能取代故障模式分析與實測。

**事實查證：** [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[SAP-C02 Domain 1: Design for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)

### 練習題 7｜SAA → SAP｜DNS failover 的 TTL、健康與資料限制

團隊為 primary 與 secondary Region 建立 Route 53 failover records，TTL 為 60 秒。有人保證 primary health check 失敗後，所有使用者會在 60 秒內無縫切換且資料一定正確。哪個說法最準確？

A. 正確，Route 53 會代理每條既有 TCP 連線並同步兩地資料庫
B. 不正確；health check 影響後續 DNS 答覆，實際切換仍受 resolver/client cache、既有連線、secondary capacity 與資料 promotion/一致性影響
C. 不正確，但唯一原因是 Route 53 health check 最短只能每 24 小時執行一次
D. 正確，只要 TTL 低於 300 秒，任何 recursive resolver 都必須立即丟棄 cache

**答案：B**

- **A：** 錯誤。Route 53 回答 DNS 查詢，不是連線代理，也不負責資料複寫或資料庫 promotion。
- **B：** 正確。TTL 是 DNS cache 行為的一部分，不是全體 client 的切換 SLA；完整 failover 還需要健康判定、容量與一致資料。
- **C：** 錯誤。Route 53 health checks 能以秒級頻率執行；問題不在每日一次。
- **D：** 錯誤。Resolver 與應用程式可能有額外 cache 或長連線，不能承諾所有 clients 按 TTL 精準切換。

**事實查證：** [Amazon Route 53 health checks and DNS failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 8｜SAP｜使用 ARC routing control 執行受控 Region evacuation

金融服務要求 Region evacuation 必須由兩位值班人員核准，且 incident 期間不能依賴建立新的 DNS/control-plane 資源。哪個方案最符合這個操作要求？

A. 事故發生後才手動建立 secondary stack 與新的 Route 53 records
B. 讓單一應用 health endpoint 自動同時 promotion 資料庫並切換全球流量
C. 每次事故臨時修改 DNS weight，且不保留審核或 safety rule
D. 預先建立 Amazon Application Recovery Controller routing controls，設定 safety rules，並由核准流程呼叫高可用 data-plane API 切換

**答案：D**

- **A：** 錯誤。Incident 中建立資源會把 RTO 暴露於 control-plane、quota、template 與人工作業延遲。
- **B：** 錯誤。單一 health signal 可能誤判，也不能取代資料 promotion 次序與人為授權。
- **C：** 錯誤。臨時 DNS 編輯缺乏預先驗證、guardrail 與可重複的 recovery data path。
- **D：** 正確。ARC routing controls 可預先配置，safety rules 可限制不安全狀態，並以 data-plane endpoint 執行受控切換。

**事實查證：** [Amazon Application Recovery Controller routing control](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)、[ARC routing-control data and control planes](https://docs.aws.amazon.com/r53recovery/latest/dg/data-and-control-planes.html)

### 練習題 9｜SAP｜Failover 前驗證 surviving capacity 與 quotas

一個三 AZ 服務平時每 AZ 使用 35% 容量。團隊認為失去一個 AZ 後其餘兩區會自動 scale out，因此不用預先檢查 quotas。哪個修正最重要？

A. 把平均 CPU alarm 門檻提高，避免 failover 時告警
B. 只確認 Auto Scaling policy 存在，因為 AWS 一定提供所需 instance capacity
C. 以 N-1 負載計算並測試剩餘容量，預查 instance、IP、ENI、連線與下游 service quotas，保留啟動與 warmup headroom
D. 等第一次 AZ 事故後再提交 quota increase，以便使用真實數字

**答案：C**

- **A：** 錯誤。降低告警敏感度不會增加 capacity，反而可能隱藏 evacuation 的使用者影響。
- **B：** 錯誤。Auto Scaling 是請求與控制機制，不保證所需 type、IP 或下游 quota 在事故時必然可得。
- **C：** 正確。Fault tolerance 需要可承載 N-1 流量的完整路徑；quota、IP、連線與 warmup 都應在事故前驗證。
- **D：** 錯誤。Quota increase 可能需處理時間，不能放在已開始計時的 recovery critical path。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)、[EC2 Auto Scaling default instance warmup](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-default-instance-warmup.html)

### 練習題 10｜SAP｜AZ／Region game day 的有效證據

團隊要執行一次 AZ evacuation game day，目標是證明 checkout 在一區失效時仍符合 SLO，並能安全恢復。哪兩項屬於必要做法？（選兩項）

A. 事前定義 hypothesis、stop conditions、允許的 error budget 與安全範圍
B. 只終止一台沒有流量的 instance，看到 Auto Scaling 補回就結束
C. 只保存 CloudFormation deployment success 當作可用性證據
D. 為避免結果難看，測試期間暫停所有 business outcome alarms
E. 量測偵測、流量撤離、交易正確性、RTO、剩餘容量與 failback，保留時間線及後續修正

**答案：A、E**

- **A：** 正確。Fault injection 必須有清楚假設、範圍與 stop condition，才能避免測試本身造成不可控傷害。
- **B：** 錯誤。單機 replacement 不能代表整個 AZ 的 network、egress、state 與容量故障。
- **C：** 錯誤。資源建立成功是 control-plane 訊號，不證明使用者交易或資料在故障中正確。
- **D：** 錯誤。Business alarms 是測試判定的重要證據；應控制通知流程而不是隱藏影響。
- **E：** 正確。有效 game day 要測完整生命週期，包括 failback 與資料驗證，並把結果轉成可追蹤改善。

**事實查證：** [AWS Fault Injection Service concepts and safeguards](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Mu…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「副本只有放在獨立failure domain，才能抵抗對應範圍的故障。」，所以「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」能直接滿足它；若constraint改成「Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」。替代方案「Multi-Region提高resilience與latency選項，但帶來資料一致性、部署、成本與操作複雜度。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「副本只有放在獨立failure domain，才能抵抗對應範圍的故障。」，排除會導致「將所有副本放同一AZ，或宣稱multi-Region卻共享單一identity/DNS/control dependency。」的選項，再選「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先用Multi-AZ處理datacenter級故障，再依business continuity需求評估Multi-Region。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「resilience is limited by the largest shared dependency」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 62 章　Backup、Pilot Light、Warm Standby 與 Active-Active

DR策略由RTO、RPO、成本與操作成熟度決定，不是越昂貴越好。

## 從故障發生的那一刻倒推：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：四套系統分別可接受24小時、4小時、30分鐘與近零停機。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：DR策略由RTO、RPO、成本與操作成熟度決定，不是越昂貴越好。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS Backup負責主要工作，AWS Elastic Disaster Recovery提醒我們答案不是永遠固定。本章會走向「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：四套系統分別可接受24小時、4小時、30分鐘與近零停機。

Business先給RTO / RPO，才選DR成本

Backup & Restore ── 幾乎不常駐 ── 恢復最慢、成本最低
Pilot Light      ── 核心資料常駐 ── 需要啟動其餘服務
Warm Standby     ── 縮小版全系統 ── 可快速擴容接手
Active-Active    ── 多地同時服務 ── 最快但資料與營運最複雜

每一級都必須搬動identity、network、data、dependencies與DNS，並以game day計時。

失敗時先找：建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和AWS Elastic Disaster Recovery並不是兩個任意的產品名稱。前者適合本章，是因為「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」直接回應了眼前的問題；後者描述的「Active-passive通常較易維持單一writer語意，active-active需衝突處理。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「recovery architecture must be continuously executable」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |

## 把全圖套進一個具體案例

**場景：** 四套系統分別可接受24小時、4小時、30分鐘與近零停機。

1. 故事的起點：四套系統分別可接受24小時、4小時、30分鐘與近零停機。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Elastic Disaster Recovery、Amazon Route 53各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：DR策略由RTO、RPO、成本與操作成熟度決定，不是越昂貴越好。
- **具體例子／邊界：** 在「四套系統分別可接受24小時、4小時、30分鐘與近零停機。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Elastic Disaster Recovery

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Active-passive通常較易維持單一writer語意，active-active需衝突處理。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：recovery architecture must be continuously executable。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

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

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

### AWS Elastic Disaster Recovery

- **功用：** 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。
- **底層機制：** Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。
- **關鍵設定：** source servers、staging subnet、replication settings、launch template、point-in-time snapshot與drill。
- **選擇時機：** on-premises/other cloud servers的lift-and-shift DR與低RPO。
- **替換時機：** 雲原生database/object workload優先native replication/backup；它不自動解決app dependency order。

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

### AWS Elastic Disaster Recovery：逐項設定說明

#### `source servers`

- **控制什麼：** `source servers`指定AWS Elastic Disaster Recovery讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `staging subnet`

- **控制什麼：** `staging subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `replication settings`

- **控制什麼：** `replication settings`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義AWS Elastic Disaster Recovery建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `point-in-time snapshot`

- **控制什麼：** `point-in-time snapshot`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `drill`

- **控制什麼：** `drill`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

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
4. 選擇邏輯：Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。
5. 不要混淆：AWS Elastic Disaster Recovery的責任是「把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。
8. 可移植原則：recovery architecture must be continuously executable。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 | on-premises/other cloud servers的lift-and-shift DR與低RPO。 | 雲原生database/object workload優先native replication/backup；它不自動解決app dependency order。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Active-passive通常較易維持單一writer語意，active-active需衝突處理。 | 只有當題目條件明確改變時才可能合理。 | 建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Active-passive通常較易維持單一writer語意，active-active需衝突處理。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-4.2 Design cost-optimized compute solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA → SAP｜由 RTO、RPO、成本與操作能力選 DR strategy

一個員工入口網站的 RTO 是 4 小時、RPO 是 30 分鐘。團隊可在 recovery Region 事先保留資料庫與核心網路，但不願全年支付完整 production compute，也能以 IaC 在 90 分鐘內啟動其餘 tiers。哪個 DR strategy 最貼近限制？

A. Multi-site active-active，因為它永遠是最低成本方案
B. Pilot light：持續維護資料與核心元件，災難時部署或啟動其餘 capacity
C. 只保留本機磁碟 snapshot，災難後再設計 recovery architecture
D. Warm standby，且要求縮小版系統在災難前完全沒有任何 compute

**答案：B**

- **A：** 錯誤。Active-active 常駐多地完整能力，成本與資料操作複雜度最高，題目沒有近零 RTO 要求。
- **B：** 正確。Pilot light 保留 critical core 與資料複寫，其他層可在事故時啟動，符合 4 小時 RTO 與成本限制。
- **C：** 錯誤。單一 snapshot 既未說明跨 Region，也缺少 identity、network、code 與恢復次序。
- **D：** 錯誤。Warm standby 的定義是縮小但可運作的完整 stack；完全沒有 compute 更接近 pilot light。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)

### 練習題 2｜SAA｜完整的 backup-and-restore recovery path

一個低優先級應用選擇 backup-and-restore，RTO 為 12 小時。哪兩項工作最能把「有 backup」變成可執行的整體復原？（選兩項）

A. 只保護 RDS；application binaries、IaC、secrets 與 DNS 可在事故後重新猜測
B. 將可用的 recovery points 複製到所需 account/Region 邊界，並驗證可由 recovery authority 解密
C. 假設 AWS Backup 會自動還原所有非受支援的 SaaS 與 application workflow
D. 保留版本化 IaC、artifacts 與 dependency-order runbook，定期從空環境執行 restore 和 business validation
E. 把所有 restore steps 留在單一工程師的個人筆記中

**答案：B、D**

- **A：** 錯誤。資料庫只是 dependency graph 的一部分；缺 code、configuration、identity 與 ingress 仍無法服務。
- **B：** 正確。Recovery point 若位於同一失敗或受攻擊邊界，或 recovery 人員無法解密，就不是可用的復原材料。
- **C：** 錯誤。AWS Backup 支援特定資源；應用程式與外部依賴仍需架構和 runbook。
- **D：** 正確。IaC 與 dependency-order 執行可重建環境；實際 restore 與交易驗證才能量出 RTO。
- **E：** 錯誤。個人筆記沒有版本、審查、交接與演練證據；只有在它被轉成團隊擁有、可執行且定期驗證的 runbook 後，才可成為復原材料。

**事實查證：** [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 3｜SAA｜辨識真正的 pilot light

下列哪個架構最符合 pilot light，而不是 backup/restore 或 warm standby？

A. 第二 Region 只有離線 backups，災難後才建立 network、database 與 compute
B. 第二 Region 有縮小但正在處理真實流量的完整 application stack
C. 第二 Region 持續接收資料複寫並保留必要 network/identity core，但 web 與 worker capacity 必須在 failover 前啟動或部署
D. 兩個 Regions 都以 production capacity 同時接收寫入

**答案：C**

- **A：** 錯誤。幾乎所有 runtime 都需災後建立，屬於 backup-and-restore。
- **B：** 錯誤。縮小但完整且持續運作的 stack 是 warm standby；若只保留核心資料與基礎、故障時才啟動其餘 compute，才是 pilot light。
- **C：** 正確。Pilot light 的核心資料與基礎持續存在，但非核心 compute 仍需在 recovery 時啟動。
- **D：** 錯誤。兩地同時服務是 active-active，需處理多地寫入與衝突語意。

**事實查證：** [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 4｜SAA｜辨識 warm standby 與 scaling requirement

一個 SaaS 在 recovery Region 長期運行一套縮小的 ALB、application fleet 與 database replica；它每分鐘接受 synthetic transaction，發生災難時需 promotion 並把 fleet 從 20% 擴到 100%。這是哪種策略？

A. Warm standby，因為完整但縮小的系統已可運作，failover 後仍需擴容
B. Pilot light，因為任何需要擴容的系統都叫 pilot light
C. Backup-and-restore，因為 primary Region 仍然存在 backups
D. Active-active，因為 synthetic transaction 等同 production traffic

**答案：A**

- **A：** 正確。Warm standby 保留功能完整的縮小環境，可較快接手但仍須驗證 scale-up 與 surviving capacity。
- **B：** 錯誤。Pilot light 通常缺少部分 serving compute；題目中的完整 stack 已經運行。
- **C：** 錯誤。存在 backup 不會改變 runtime recovery strategy 的分類。
- **D：** 錯誤。Synthetic probes 用於驗證，不表示兩地同時承接真實 production workload。

**事實查證：** [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 5｜SAP｜Active-active 的寫入語意與 corruption recovery

全球購物車服務計畫在兩個 Regions active-active，兩地都可接受更新。哪兩項設計決策不可省略？（選兩項）

A. 定義 write ownership、衝突解決或 business invariant，並驗證同一購物車在並行更新時的結果
B. 假設非同步複寫等同單一全球 serializable transaction，不需要應用層決策
C. 移除 point-in-time backups，因為兩地 replicas 足以處理邏輯刪除與惡意修改
D. 只用低 DNS TTL，就能保證所有寫入順序一致
E. 保留獨立版本或 point-in-time recovery，因為 corruption 可能被複寫到所有 active sites

**答案：A、E**

- **A：** 正確。Active-active 最大難點是多地寫入語意；必須明確決定衝突、所有權與不可破壞的業務規則。
- **B：** 錯誤。非同步 replication 不會自動提供跨 Region 單一交易序列。
- **C：** 錯誤。Replication 能複製好資料，也會複製壞資料；仍需獨立 recovery point。
- **D：** 錯誤。DNS 決定 endpoint 選擇，不定義 database consistency 或 global write ordering。
- **E：** 正確。Backup/PITR 處理的是邏輯 corruption、刪除與勒索情境，和 infrastructure availability 互補。

**事實查證：** [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Backup logically air-gapped vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 6｜SAP｜AWS Elastic Disaster Recovery 的適用邊界

企業要把 300 台 VMware 上的 legacy servers 以持續 block-level replication 保護到 AWS，災難時啟動 recovery EC2，之後還要支援 failback。哪個方案最合適？

A. 在每個 Amazon RDS instance 內安裝 AWS DRS agent
B. 用 Route 53 health check 複寫 server blocks
C. 使用 AWS DRS 保護 server-hosted workloads，並為 RDS、DynamoDB、S3 等 managed state 另採其原生 recovery 機制
D. 用 AWS Backup 取代所有 application dependency、DNS 與 failback 設計

**答案：C**

- **A：** 錯誤。客戶不能登入 managed RDS host 安裝 server replication agent。
- **B：** 錯誤。Route 53 管理 DNS 答覆與 health routing，不複寫磁碟 block。
- **C：** 正確。DRS 適合 server-hosted application 的持續 block replication 與 recovery launch；managed services 仍須使用各自能力。
- **D：** 錯誤。Backup 是 recovery data/control 元件，不會自動完成全部依賴、流量與 failback lifecycle。

**事實查證：** [AWS Elastic Disaster Recovery concepts](https://docs.aws.amazon.com/drs/latest/userguide/concepts.html)、[AWS Elastic Disaster Recovery recovery and failback](https://docs.aws.amazon.com/drs/latest/userguide/failback.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 7｜SAA → SAP｜Replication 與 point-in-time recovery 的互補

資料庫已跨 Region 非同步複寫。某次錯誤 migration 在 primary 刪除資料，幾秒後 deletion 也出現在 replica。哪個改善最能處理此類風險？

A. 保留獨立、可還原的 point-in-time recovery 或版本化 backup，並定期測試 recovery
B. 再新增一個同步 read replica，但允許相同 migration 自動執行
C. 把 replication lag alarm 關閉，避免誤報
D. 只把 DNS TTL 降低，讓 deletion 不會傳播

**答案：A**

- **A：** 正確。Replication 主要改善基礎設施故障下的 RPO/availability；獨立 recovery points 才能回到 corruption 前狀態。
- **B：** 錯誤。若相同錯誤變更仍會傳播，更多 replicas 只會增加受影響副本。
- **C：** 錯誤。關閉 lag 可視性既不能恢復資料，也會削弱 recovery readiness。
- **D：** 錯誤。DNS 不控制 data replication 或 database transaction。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[AWS Backup logically air-gapped vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 8｜SAP｜降低 workload compromise 對 backup 的影響

安全團隊擔心 production administrator 憑證遭竊後，攻擊者會刪除 workloads 與所有 backups。哪兩項控制最能縮小這個 blast radius？（選兩項）

A. 讓 production role 永久擁有所有 backup vault 與 KMS key 的刪除權限
B. 在支援的資源上使用跨帳號 recovery copy 或 logically air-gapped vault，並由獨立 recovery authority 管理
C. 取消 backup encryption，避免 KMS key 不可用
D. 使用 Vault Lock／vault access policy 與 least privilege 限制刪除和修改，並測試 recovery role 可實際還原
E. 只增加 database replicas，因為 replica 永遠不會收到惡意刪除

**答案：B、D**

- **A：** 錯誤。把 workload administration 與 recovery deletion 放在同一權限邊界，正是題目要避免的風險。
- **B：** 正確。獨立帳號或邏輯隔離 vault 可減少 production compromise 同時控制 recovery copies 的機會。
- **C：** 錯誤。取消 encryption 會削弱機密性；正確作法是設計獨立且可用的 key/recovery authority。
- **D：** 正確。不可變或受限 vault 控制必須和 least privilege、實際 restore 測試一起使用。
- **E：** 錯誤。Replicas 通常會複寫合法 API 發出的 delete/corruption，不能取代 protected backup。

**事實查證：** [AWS Backup logically air-gapped vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)、[AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 9｜SAP｜把 failover 與 failback 設計成同一 lifecycle

Primary Region 故障後，recovery Region 已接受新訂單 12 小時。Primary 修復時，團隊打算直接把 DNS 切回並用舊 primary 資料覆寫 recovery database。最重要的修正是什麼？

A. 先把 TTL 設成零，因為零 TTL 會自動合併兩地資料
B. 直接切回；primary 是原本主站，所以一定擁有最新資料
C. 停止記錄 recovery Region 的新寫入，簡化操作
D. 依 runbook 重新同步或 reconcile recovery 期間的 writes，驗證一致性與容量，再以受控方式切回並監控

**答案：D**

- **A：** 錯誤。DNS TTL 不具資料合併語意，且 client/resolver cache 也不能保證零延遲。
- **B：** 錯誤。Primary 在故障後已落後 12 小時，盲目切回會造成資料遺失或 split-brain。
- **C：** 錯誤。刪除 recovery 期間的業務寫入不是可接受的 failback 策略。
- **D：** 正確。Failback 必須把 recovery site 產生的新 authoritative state 安全帶回，並包含 validation 與 traffic control。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[Amazon Application Recovery Controller routing control](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)

### 練習題 10｜SAP｜用 recurring restore test 證明 DR readiness

AWS Backup console 顯示最近 30 天所有 jobs 都是 COMPLETED。稽核人員問：是否已證明 2 小時 RTO 與 15 分鐘 RPO？哪個回答最準確？

A. 是；backup job completed 等同完整 application 在 RTO 內可服務
B. 是；只要 recovery point 已加密，便不需要 restore test
C. 否；需定期執行 restore/failover，驗證 data、dependencies、business transactions、capacity 與實際 RTO/RPO 並保留證據
D. 否；唯一有效測試是永久關閉 primary Region

**答案：C**

- **A：** 錯誤。Completed 只證明特定 backup 工作完成，不代表解密、還原、啟動與業務驗證都能在時限內完成。
- **B：** 錯誤。Encryption 是必要控制之一，不能替代 recovery execution。
- **C：** 正確。DR readiness 是可執行能力；restore testing、business validation 與 measured timing 才能證明目標。
- **D：** 錯誤。可以用隔離 recovery environment、FIS 與受控演練取得證據，不必製造不可逆 production 災難。

**事實查證：** [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[AWS Resilience Hub resiliency policies](https://docs.aws.amazon.com/resilience-hub/latest/userguide/create-policy.html)、[AWS Fault Injection Service concepts and safeguards](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「DR策略由RTO、RPO、成本與操作成熟度決定，不是越昂貴越好。」，所以「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」能直接滿足它；若constraint改成「Active-passive通常較易維持單一writer語意，active-active需衝突處理。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」。替代方案「Active-passive通常較易維持單一writer語意，active-active需衝突處理。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「DR策略由RTO、RPO、成本與操作成熟度決定，不是越昂貴越好。」，排除會導致「建立第二Region資源卻沒有資料、IAM、DNS與runbook同步。」的選項，再選「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-4.2 Design cost-optimized compute solutions；SAA-4.3 Design cost-optimized database solutions；SAP-1.3 Design reliable and resilient architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Backup/restore成本最低；pilot light保留核心；warm standby保留縮小環境；active-active常駐兩地。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「recovery architecture must be continuously executable」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 63 章　RTO/RPO 驅動的 DR 設計

若不將business impact轉成可測量目標，恢復設計會過度或不足。

## 從故障發生的那一刻倒推：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：應用可在一小時恢復，但付款資料最多只能遺失五分鐘。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：若不將business impact轉成可測量目標，恢復設計會過度或不足。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 但請同時記住它的邊界：恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Backup，對照角色是AWS Elastic Disaster Recovery。我們選擇「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：應用可在一小時恢復，但付款資料最多只能遺失五分鐘。

正常production路徑
          ▼
[AWS Backup] → 使用者可觀察的結果
          │ 以policy集中排程、保存與複製多種AWS resource backups。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · AWS Elastic Disaster Recovery：把server block data持續複寫到AWS低成本staging area，故障時快速launch…
  · AWS Resilience Hub：定義application resilience policy並評估components是否滿足RTO/R…

失敗時先找：只看database RPO，忽略event stream、object、DNS與secret的復原點。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和AWS Elastic Disaster Recovery並不是兩個任意的產品名稱。前者適合本章，是因為「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」直接回應了眼前的問題；後者描述的「更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只看database RPO，忽略event stream、object、DNS與secret的復原點。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「RTO is a path; RPO is a data graph」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 |
| AWS Resilience Hub | 定義application resilience policy並評估components是否滿足RTO/RPO。 | 匯入app resources與relationships，套policy分析故障與提出recommendations，可整合FIS/SOP。 |

## 把全圖套進一個具體案例

**場景：** 應用可在一小時恢復，但付款資料最多只能遺失五分鐘。

1. 故事的起點：應用可在一小時恢復，但付款資料最多只能遺失五分鐘。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Elastic Disaster Recovery、AWS Resilience Hub各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只看database RPO，忽略event stream、object、DNS與secret的復原點。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：若不將business impact轉成可測量目標，恢復設計會過度或不足。
- **具體例子／邊界：** 在「應用可在一小時恢復，但付款資料最多只能遺失五分鐘。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Elastic Disaster Recovery

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只看database RPO，忽略event stream、object、DNS與secret的復原點。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：RTO is a path; RPO is a data graph。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

## 回到 AWS：Components、功用與責任邊界

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

### AWS Elastic Disaster Recovery

- **功用：** 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。
- **底層機制：** Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。
- **關鍵設定：** source servers、staging subnet、replication settings、launch template、point-in-time snapshot與drill。
- **選擇時機：** on-premises/other cloud servers的lift-and-shift DR與低RPO。
- **替換時機：** 雲原生database/object workload優先native replication/backup；它不自動解決app dependency order。

### AWS Resilience Hub

- **功用：** 定義application resilience policy並評估components是否滿足RTO/RPO。
- **底層機制：** 匯入app resources與relationships，套policy分析故障與提出recommendations，可整合FIS/SOP。
- **關鍵設定：** application definition、resilience policy、RTO/RPO targets、assessment、alarms/SOP/tests。
- **選擇時機：** portfolio resilience posture、gap analysis與持續驗證。
- **替換時機：** 它不替你執行所有failover；實作仍在服務配置、runbook與game day。

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

### AWS Elastic Disaster Recovery：逐項設定說明

#### `source servers`

- **控制什麼：** `source servers`指定AWS Elastic Disaster Recovery讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `staging subnet`

- **控制什麼：** `staging subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `replication settings`

- **控制什麼：** `replication settings`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義AWS Elastic Disaster Recovery建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `point-in-time snapshot`

- **控制什麼：** `point-in-time snapshot`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `drill`

- **控制什麼：** `drill`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「on-premises/other cloud servers的lift-and-shift DR與低RPO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Disaster Recovery設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

### AWS Resilience Hub：逐項設定說明

#### `application definition`

- **控制什麼：** `application definition`定義AWS Resilience Hub管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `resilience policy`

- **控制什麼：** `resilience policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「portfolio resilience posture、gap analysis與持續驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Resilience Hub明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `RTO/RPO targets`

- **控制什麼：** `RTO/RPO targets`指定AWS Resilience Hub讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `assessment`

- **控制什麼：** `assessment`定義AWS Resilience Hub用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `alarms/SOP/tests`

- **控制什麼：** `alarms/SOP/tests`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「portfolio resilience posture、gap analysis與持續驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Resilience Hub選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

## 讀到這裡，請用自己的話說一次

1. AWS Backup的責任：以policy集中排程、保存與複製多種AWS resource backups。
2. 底層機制：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
3. 第一個要看的設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
4. 選擇邏輯：將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。
5. 不要混淆：AWS Elastic Disaster Recovery的責任是「把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：只看database RPO，忽略event stream、object、DNS與secret的復原點。
8. 可移植原則：RTO is a path; RPO is a data graph。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 | on-premises/other cloud servers的lift-and-shift DR與低RPO。 | 雲原生database/object workload優先native replication/backup；它不自動解決app dependency order。 |
| AWS Resilience Hub | 定義application resilience policy並評估components是否滿足RTO/RPO。 | 匯入app resources與relationships，套policy分析故障與提出recommendations，可整合FIS/SOP。 | portfolio resilience posture、gap analysis與持續驗證。 | 它不替你執行所有failover；實作仍在服務配置、runbook與game day。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。 | 只有當題目條件明確改變時才可能合理。 | 只看database RPO，忽略event stream、object、DNS與secret的復原點。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜正確定義 RTO 與 RPO

風險委員會說：「付款服務中斷後最多 60 分鐘要恢復，而且最多只能回到中斷前 5 分鐘內的資料。」這兩個要求分別代表什麼？

A. RPO 60 分鐘，RTO 5 分鐘
B. Availability 60%，MTTR 5 分鐘
C. RTO 60 分鐘，RPO 5 分鐘
D. RTO 與 RPO 都是全年平均值，因此單次事故可以無限延長

**答案：C**

- **A：** 錯誤。RPO 描述可接受的資料年齡／遺失量，而非恢復服務所需時間。
- **B：** 錯誤。Availability 與 MTTR 是不同指標，不能取代對單次 recovery 的 downtime/data-loss 目標。
- **C：** 正確。60 分鐘是 service restoration deadline（RTO）；5 分鐘是可接受 recovery point 的最大資料落後（RPO）。
- **D：** 錯誤。RTO/RPO 是 workload 的 business recovery targets，不是允許任一事故超標的平均值。

**事實查證：** [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 2｜SAP｜由 business impact 建立分級 recovery objectives

公司有即時付款、每日推薦模型與法規文件庫三套 workload。有人建議全部設定 zero RTO/zero RPO，因為這最安全。架構師應如何回應？

A. 接受，因為任何 managed service 都自動提供 zero RTO/zero RPO
B. 依每個 workflow 的 downtime/data-loss impact、法規、依賴與成本分級，設定可量測且可測試的目標
C. 只複製目前 backup schedule 當作 RPO，不需要詢問業務
D. 使用資料庫 SLA 當作三套 application 的完整 recovery objective

**答案：B**

- **A：** 錯誤。Managed service 的 availability、failover 與 data semantics 不等於應用程式的零目標。
- **B：** 正確。Recovery objectives 源自業務影響與約束；不同 workflow 應有不同投資與可接受風險。
- **C：** 錯誤。現有設定是 implementation，不是 business requirement，且 backup schedule 不一定等於 achieved RPO。
- **D：** 錯誤。Application 還包含 identity、network、queues、objects 與 client path，不能只用 database SLA 代表。

**事實查證：** [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)

### 練習題 3｜SAP｜計算 end-to-end RTO critical path

團隊量到 database restore 需 35 分鐘，便宣稱可符合 45 分鐘 RTO。哪兩項還必須納入 end-to-end critical path 才能判定？（選兩項）

A. 事故偵測、宣告、授權與自動化啟動所需時間
B. 把所有可平行步驟無條件相加，而不建立依賴圖或辨識真正 critical path
C. 只從資料庫恢復完成開始計時，排除事故偵測、宣告與授權時間
D. dependency 啟動、traffic convergence、client reconnection 與 business transaction validation
E. 只量到 ALB health check 轉綠便停止計時，不等待 DNS convergence、client reconnect 與成功交易

**答案：A、D**

- **A：** 正確。RTO 從中斷開始計時，偵測、決策與授權延遲都會消耗 recovery budget。
- **B：** 錯誤。真正 critical path 應辨識依賴與可安全平行的步驟；盲目相加會扭曲結果。
- **C：** 錯誤。RTO 從業務中斷開始計時；排除偵測、宣告與授權會系統性低估真實恢復時間。
- **D：** 正確。資料還原後仍需讓 application、ingress 與 clients 正常運作，並證明業務結果正確。
- **E：** 錯誤。Infrastructure health 不是 business readiness；DNS、既有連線、client retry 與交易驗證仍可能位於 critical path。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 4｜SAP｜建立 transaction-level RPO data graph

訂單交易同時寫入 RDS、把收據放到 S3，並送出 SQS message 觸發出貨。團隊只用 RDS 的 PITR 時間宣稱整個交易 RPO 為 5 分鐘。哪兩項修正最重要？（選兩項）

A. 把 S3 object/version、queue/workflow state 與必要 configuration 納入 recovery point 分析
B. 假設所有 AWS services 的 recovery points 天然具有同一 atomic timestamp
C. 為跨資料來源建立 reconciliation 與 idempotent replay 規則，處理恢復點不一致
D. 刪除 SQS，因為任何 queue 都無法參與 DR
E. 只把 RDS backup 頻率提高，其他 state 就會自動同步

**答案：A、C**

- **A：** 正確。完整訂單的 authoritative/derived state 分布在多個 stores，RPO 必須涵蓋全部必要資料。
- **B：** 錯誤。獨立服務的 backup、replication 與 retention 並不形成自動跨服務交易快照。
- **C：** 正確。若資料來源回到不同時間點，reconciliation 與安全 replay 才能恢復 business invariant。
- **D：** 錯誤。Queue 可被納入 recovery 設計；問題是要定義 retention、replay 與 side-effect 語意。
- **E：** 錯誤。RDS 設定不會改變 S3、SQS 或 application configuration 的 recovery point。

**事實查證：** [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 5｜SAA → SAP｜由 backup policy 推導 achieved RPO

Backup plan 每小時啟動一次，但 start window 可延後 2 小時，某些 jobs 需 50 分鐘，跨帳號 copy 又可能落後 30 分鐘。可以直接宣稱 recovery account 的 RPO 是 1 小時嗎？

A. 可以；只要 schedule 寫 hourly，其他時間都不影響 RPO
B. 不可以；要依最後一個已完成、已複製、可解密且通過 restore 驗證的 recovery point 計算
C. 可以；backup job 進入 RUNNING 就等同可還原
D. 不可以；任何 backup-based DR 都沒有 RPO

**答案：B**

- **A：** 錯誤。Schedule 是觸發意圖；window、執行時間、copy lag 與失敗會改變實際 recovery point。
- **B：** 正確。Achieved RPO 由最後可用且可還原的 recovery point 決定，而不是規則名稱。
- **C：** 錯誤。尚未完成的 job 不一定有一致、可用的 recovery artifact。
- **D：** 錯誤。Backup-based DR 可以有可量測 RPO，只是通常大於即時 replication，且需以執行證據確認。

**事實查證：** [AWS Backup plan scheduling and start windows](https://docs.aws.amazon.com/aws-backup/latest/devguide/plan-options-and-configuration.html)、[Create cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)

### 練習題 6｜SAA → SAP｜把 replication lag 當作訊號而非保證

RDS MySQL 跨 Region read replica 的 `ReplicaLag` 平時低於 2 秒。產品經理因此要求文件寫成「任何災難都保證 zero RPO」。架構師應採取哪個立場？

A. 同意；只要目前 lag 很低，就等於未來每次 failover 都零資料遺失
B. 同意；read replica promotion 會自動等待所有未傳輸 transactions
C. 拒絕；lag 是當下觀測訊號，應告警 stalled replication、測試 promotion/consistency，並保留 PITR 以處理 corruption
D. 拒絕；read replica 永遠不能用於任何 DR

**答案：C**

- **A：** 錯誤。非同步複寫在故障瞬間可能有 lag 或未傳輸資料，歷史低值不是 zero-RPO contract。
- **B：** 錯誤。Promotion 行為與最後已複寫狀態依服務而定，不能保證取得失敗 primary 上尚未傳出的寫入。
- **C：** 正確。Lag 應用於 readiness 與風險監控；promotion、資料驗證和獨立 recovery points 仍不可省略。
- **D：** 錯誤。Read replica 可作為讀取擴展與 DR 元件，只是不能被誤寫成同步零風險保證。

**事實查證：** [Working with Amazon RDS read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 7｜SAP｜依 dependency sequence 恢復 workload

Recovery runbook 第一個步驟是切換 public DNS，之後才建立 KMS permissions、database、queue 與 application。演練時使用者先看到大量 5xx。哪個修正最合理？

A. 先依 dependency graph 恢復 identity/network/keys、authoritative data、messaging 與 compute，通過 readiness 和交易驗證後再切流量
B. 保留順序但把 DNS TTL 設成 1 秒
C. 先讓 ALB health check 只檢查 web process 是否存活，database、queue 與 KMS 尚未就緒也回 healthy
D. 把所有步驟改成人工序列，避免 IaC 平行化

**答案：A**

- **A：** 正確。Ingress 應在可服務依賴就緒後才開放；可平行化獨立工作，但不能破壞真實 dependency order。
- **B：** 錯誤。更短 TTL 只可能加快部分 resolver/client 取得新答案，不能建立缺失的 dependencies；若 recovery stack 已通過 readiness，低 TTL 才可能縮短 DNS convergence。
- **C：** 錯誤。只做 shallow liveness 會讓尚不能完成交易的 targets 提前接流量；只有把 readiness 與必要依賴分開建模並在切流量前驗證，才不會重演 5xx。
- **D：** 錯誤。自動化與安全平行化可縮短 RTO；問題是 dependency modeling，不是自動化本身。

**事實查證：** [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)、[Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 8｜SAP｜正確解讀 AWS Resilience Hub assessment

Resilience Hub assessment 顯示某 workload 的 estimated RTO/RPO 符合 policy。團隊是否可直接把它當成 audit proof，聲稱已完成 recovery test？

A. 可以；assessment 會自動執行所有 business transactions 與 failback
B. 可以；只要 policy 數字填得夠低，workload 就會自動符合
C. 不可以；Resilience Hub 只能顯示成本，與 resiliency 無關
D. 不可以；assessment 是 configuration posture 與估計，仍需執行 restore/failover、資料驗證與實測 RTO/RPO

**答案：D**

- **A：** 錯誤。Assessment 不等於完整 production failover 與 application-level validation。
- **B：** 錯誤。Policy 定義目標，不會因輸入零而自動改造 resources 或 data paths。
- **C：** 錯誤。Resilience Hub 的核心就是 resiliency policy、assessment 與 recommendations，不是單純成本服務。
- **D：** 正確。Assessment 可找出缺口，但真正 compliance 仍要靠可重複 recovery execution 與 evidence。

**事實查證：** [AWS Resilience Hub resiliency policies](https://docs.aws.amazon.com/resilience-hub/latest/userguide/create-policy.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 9｜SAP｜驗證 restored workload 而非只有 resources

Restore automation 已把 RDS、EC2 與 ALB 建立完成。哪兩項證據最能證明 workload 而非單純 resources 已恢復？（選兩項）

A. 執行代表性 login、下單、付款與查詢，確認結果及 side effects 正確
B. 只保存 EC2 instance state 為 running 的截圖
C. 核對資料完整性、reconciliation、security controls、telemetry 與 achieved RTO/RPO，並由 owner sign-off
D. 只確認 CloudFormation stack status 是 CREATE_COMPLETE
E. 刪除 restore job IDs 與時間線，避免產生稽核資料

**答案：A、C**

- **A：** 正確。Business transactions 驗證完整 request/data path 與使用者可見結果。
- **B：** 錯誤。Running 只代表 VM state，不代表 application、data 或 external dependencies 正常。
- **C：** 正確。資料、控制與營運可觀測性都要驗證，時間線才可用來證明目標與找出瓶頸。
- **D：** 錯誤。Stack 建立成功是 control-plane completion，不是 business readiness。
- **E：** 錯誤。保留 job IDs、timestamps 與 outputs 才能提供 audit 與改善依據。

**事實查證：** [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 10｜SAP｜以明確 clock 與 acceptance criteria 執行 DR game day

DR 演練中，團隊在遇到錯誤後暫停 RTO 計時 40 分鐘進行人工除錯，最後宣稱 50 分鐘內達成 1 小時 RTO。哪個結論正確？

A. 宣稱有效，因為人工除錯時間不屬於 recovery
B. 宣稱無效；RTO 從 interruption 到恢復 business service，除錯、授權與等待時間都在 clock 內，且還要驗證 RPO 與 failback
C. 只要 infrastructure 最終建立，任何時間都可算符合
D. 把下一次 RTO 改成平均值即可保留此次結果

**答案：B**

- **A：** 錯誤。使用者在人工除錯期間仍無法完成業務，因此時間必須計入 RTO；只有事前明確定義且不影響服務可用性的觀察階段，才可能位於停止計時之後。
- **B：** 正確。演練要事前定義 clock start/stop、acceptance threshold、資料點與安全條件，不能事後排除不方便的時間。
- **C：** 錯誤。RTO 是 business service restoration 目標，並非 resource creation completion。
- **D：** 錯誤。不能用平均值掩蓋單次 recovery objective breach；應據此改善 runbook 或 architecture。

**事實查證：** [AWS Fault Injection Service concepts and safeguards](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「將每個dependency的restore/failover時間串成critical path，確認資料複…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「若不將business impact轉成可測量目標，恢復設計會過度或不足。」，所以「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」能直接滿足它；若constraint改成「更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」。替代方案「更頻繁backup降低RPO但不必然降低RTO；automation與預置容量主要影響RTO。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只看database RPO，忽略event stream、object、DNS與secret的復原點。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「若不將business impact轉成可測量目標，恢復設計會過度或不足。」，排除會導致「只看database RPO，忽略event stream、object、DNS與secret的復原點。」的選項，再選「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「將每個dependency的restore/failover時間串成critical path，確認資料複寫滿足RPO。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「RTO is a path; RPO is a data graph」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 64 章　Cache、Replica、Queue 與 Horizontal Scaling

效能改善方法分別降低重算、分散讀取、吸收burst與增加平行capacity。

## 從故障發生的那一刻倒推：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：API p99慢；profile顯示80%時間等資料庫相同查詢，寫入很少。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：效能改善方法分別降低重算、分散讀取、吸收burst與增加平行capacity。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，Queue像餐廳的出單夾：前台可以先收下工作，廚房按能力處理，失敗的單則移到另一個夾子調查。 出單夾不會創造處理能力，也不保證每張單只被拿一次，所以consumer仍需冪等與backpressure。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon ElastiCache如何接手工作，再看RDS read replicas何時更合適，最後用設定與考題驗證「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：API p99慢；profile顯示80%時間等資料庫相同查詢，寫入很少。

正常production路徑
          ▼
[Amazon ElastiCache] → 使用者可觀察的結果
          │ 提供managed Valkey/Redis OSS/Memcached記憶體data store。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · RDS read replicas：以非同步replica增加read capacity，並可支援跨Region read/DR。
  · Amazon SQS：以managed queue解耦producer與consumer的時間和容量。
  · Auto Scaling：依健康狀態與需求訊號維持、替換並調整EC2 fleet。

失敗時先找：同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Amazon ElastiCache有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon ElastiCache和RDS read replicas並不是兩個任意的產品名稱。前者適合本章，是因為「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」直接回應了眼前的問題；後者描述的「Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「optimize the constrained stage, not the architecture diagram」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |
| RDS read replicas | 以非同步replica增加read capacity，並可支援跨Region read/DR。 | Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 |

## 把全圖套進一個具體案例

**場景：** API p99慢；profile顯示80%時間等資料庫相同查詢，寫入很少。

1. 故事的起點：API p99慢；profile顯示80%時間等資料庫相同查詢，寫入很少。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon ElastiCache負責「提供managed Valkey/Redis OSS/Memcached記憶體data store。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：RDS read replicas、Amazon SQS、Auto Scaling各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon ElastiCache

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：效能改善方法分別降低重算、分散讀取、吸收burst與增加平行capacity。
- **具體例子／邊界：** 在「API p99慢；profile顯示80%時間等資料庫相同查詢，寫入很少。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### RDS read replicas

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：optimize the constrained stage, not the architecture diagram。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

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

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon ElastiCache

- **功用：** 提供managed Valkey/Redis OSS/Memcached記憶體data store。
- **底層機制：** Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
- **關鍵設定：** engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- **選擇時機：** session、hot reads、leaderboard、rate limiting與降低database load。
- **替換時機：** 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。

### RDS read replicas

- **功用：** 以非同步replica增加read capacity，並可支援跨Region read/DR。
- **底層機制：** Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。
- **關鍵設定：** replica count/class/Region、public accessibility、promotion、backup與replica lag alarms。
- **選擇時機：** read-heavy報表、全球read或可接受非同步RPO的DR。
- **替換時機：** 需要自動同步HA選Multi-AZ；不能把lagging replica當authoritative read。

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### Auto Scaling

- **功用：** 依健康狀態與需求訊號維持、替換並調整EC2 fleet。
- **底層機制：** Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。
- **關鍵設定：** min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
- **選擇時機：** stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。
- **替換時機：** 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。

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

### RDS read replicas：逐項設定說明

#### `replica count/class/Region`

- **控制什麼：** `replica count/class/Region`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署RDS read replicas前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `public accessibility`

- **控制什麼：** `public accessibility`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「read-heavy報表、全球read或可接受非同步RPO的DR。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在RDS read replicas中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `promotion`

- **控制什麼：** `promotion`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「read-heavy報表、全球read或可接受非同步RPO的DR。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在RDS read replicas依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `replica lag alarms`

- **控制什麼：** `replica lag alarms`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

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

### Auto Scaling：逐項設定說明

#### `min/max/desired`

- **控制什麼：** `min/max/desired`設定Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義Auto Scaling建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Auto Scaling的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `health check grace`

- **控制什麼：** `health check grace`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `instance warmup`

- **控制什麼：** `instance warmup`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `target tracking`

- **控制什麼：** `target tracking`指定Auto Scaling讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `mixed instances`

- **控制什麼：** `mixed instances`設定Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `lifecycle hooks`

- **控制什麼：** `lifecycle hooks`把Auto Scaling與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. Amazon ElastiCache的責任：提供managed Valkey/Redis OSS/Memcached記憶體data store。
2. 底層機制：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
3. 第一個要看的設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
4. 選擇邏輯：先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。
5. 不要混淆：RDS read replicas的責任是「以非同步replica增加read capacity，並可支援跨Region read/DR。」；它不會自動取代Amazon ElastiCache。
6. 替換訊號：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
7. 最常見錯法：同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。
8. 可移植原則：optimize the constrained stage, not the architecture diagram。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| RDS read replicas | 以非同步replica增加read capacity，並可支援跨Region read/DR。 | Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。 | read-heavy報表、全球read或可接受非同步RPO的DR。 | 需要自動同步HA選Multi-AZ；不能把lagging replica當authoritative read。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 | stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。 | 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。 | 只有當題目條件明確改變時才可能合理。 | 同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。」之間做選擇。
- 認得常考設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-3.3 Determine high-performing database solutions；SAA-4.2 Design cost-optimized compute solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜依真正瓶頸選 cache、replica、queue 或 horizontal scaling

商品 API 的 profiling 顯示 80% request time 花在重複查詢同一批幾乎不變的商品分類資料；database CPU 已高，寫入很少，使用者可接受 5 分鐘內的資料。第一個最精準的改善是什麼？

A. 在同步 read path 前加 SQS，讓使用者等待 consumer 回傳查詢
B. 採 cache-aside，把分類查詢結果放入 ElastiCache，設定符合 5 分鐘 freshness 的 TTL 並量測 hit rate
C. 只增加 application instances，因為更多 callers 會降低 database CPU
D. 新增 write replicas 並把相同資料同時寫入每個 replica

**答案：B**

- **A：** 錯誤。Queue 適合可延後工作；把互動式查詢排隊會改變契約，且不直接消除重複 database reads。
- **B：** 正確。高重複、低變動且允許短暫 stale 的讀取適合 caching；TTL 與 hit rate 讓正確性和效益可量測。
- **C：** 錯誤。增加 callers 可能讓已受限的 database 更忙；應先優化受限 stage。
- **D：** 錯誤。一般 RDS read replicas 不是 multi-writer，且題目的瓶頸是重複讀取而非寫入。

**事實查證：** [ElastiCache caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[SAA-C03 Domain 3: Design High-Performing Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html)

### 練習題 2｜SAA｜Cache-aside 的 miss、TTL 與 invalidation

團隊要對可修改的商品價格使用 cache-aside。哪個 implementation 最能避免把 cache 誤當成 authoritative store？

A. 所有讀取只查 cache；miss 時直接回傳「商品不存在」，永遠不讀 database
B. 把所有價格設為無限 TTL，因為 ElastiCache 會自動偵測 RDS row 更新
C. 先更新 cache 再略過 database write，讓 cache 成為唯一資料來源
D. Cache miss 時讀 authoritative database 並填 cache；寫入成功後 invalidation 或更新版本，另定義 TTL、staleness 與 stampede protection

**答案：D**

- **A：** 錯誤。Cache miss 不代表 authoritative data 不存在；cache 可以 eviction 或尚未 warm。
- **B：** 錯誤。ElastiCache 不會自動理解任意 RDS row 的 business invalidation；無限 TTL 會造成永久 stale。
- **C：** 錯誤。若 cache 不是以 durability 為主要責任，跳過 database 會在 eviction/failure 時遺失價格。
- **D：** 正確。Cache-aside 的 application 明確管理 miss、populate 與 invalidation，並把資料庫保留為 authoritative source。

**事實查證：** [ElastiCache caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 3｜SAP｜Cache 故障與 cold-cache surge

大型 Redis/Valkey cache cluster failover 後，大量 keys 被 eviction，所有 application instances 同時回源，RDS 連線飽和。哪兩項改造最能降低下一次 cold-cache impact？（選兩項）

A. 讓 application 能把 cache miss 視為正常路徑，並以 request coalescing、抖動 TTL 或受控 warmup 限制同一 key 的同時回源
B. Cache unavailable 時讓所有 requests 無限 retry，直到 RDS 恢復
C. 依 engine 與 workload 選擇合理 memory、eviction、replication/failover 設定，並對回源 database 設 admission limit
D. 假設只要有 replica 就永遠不會發生 miss 或 eviction
E. Failover 後一次把所有 keys 以最大並行度重建

**答案：A、C**

- **A：** 正確。Coalescing 與 jitter 可防止 hot key stampede；受控 warmup 避免 cache recovery 反而擊倒 authoritative store。
- **B：** 錯誤。無限 retries 會形成 retry storm，放大 connection 與 database pressure。
- **C：** 正確。Cache 高可用設定和 application fallback 必須一起設計，且 database 需要明確的保護邊界。
- **D：** 錯誤。Replica 改善特定 node failure，不會消除 TTL expiry、eviction、logic error 或全域冷啟。
- **E：** 錯誤。全量最大並行回填會把 read surge 集中到同一時刻。

**事實查證：** [ElastiCache caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)

### 練習題 4｜SAA｜安全使用 RDS read replica

報表查詢佔 RDS PostgreSQL 讀取量的 70%，可接受數十秒舊資料；checkout 寫入與 read-after-write 查詢必須使用最新資料。哪個 routing 最合理？

A. 把 checkout writes 送到每個 read replica，避免 writer 成為單點
B. 把報表送到 read replica 並監控 lag；checkout writes 與需要 read-after-write 的查詢留在 writer，另處理 promotion/reconnect
C. 把所有查詢送到任何 Multi-AZ standby，因為每種 standby 都是 read endpoint
D. 把 writer 關閉，僅使用 replicas 以降低成本

**答案：B**

- **A：** 錯誤。一般 read replicas 是 read-only 非同步副本，不接受任意 multi-writer。
- **B：** 正確。將 stale-tolerant analytics 分離可擴展讀取；一致性敏感路徑仍由 writer 服務。
- **C：** 錯誤。Readable standby 取決於 RDS deployment 類型，不能把所有 Multi-AZ standby 當通用 reader。
- **D：** 錯誤。Replica 仍依賴 writer 的 replication source，且無法承接正常 writes。

**事實查證：** [Working with Amazon RDS read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)、[Amazon RDS Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)

### 練習題 5｜SAA｜Queue 吸收 burst 但不隱藏 downstream overload

影片轉碼 producer 可在 10 分鐘送入 100 萬個 jobs，consumer fleet 長期每分鐘只能完成 5,000 個；影片超過 6 小時就失去商業價值。哪兩項設計最合理？（選兩項）

A. 只監控 ApproximateNumberOfMessagesVisible；不必監控 message age
B. Consumer 收到 message 後立即刪除，再開始轉碼
C. 把 queue retention 設成最高 14 天，假設只要 backlog 尚未過期就不必增加 processing capacity
D. 讓 consumer processing 冪等，完成 durable output 後才刪除，並從 arrival/processing rate 計算所需 capacity
E. 監控 ApproximateAgeOfOldestMessage，對超過 useful deadline 的工作採明確丟棄／重導策略並擴展 consumers

**答案：D、E**

- **A：** 錯誤。Depth 不含 job 的等待時間與 deadline；同一深度在不同 arrival rate 下風險不同。
- **B：** 錯誤。先刪除會讓 worker failure 造成永久 job loss。
- **C：** 錯誤。SQS retention 最長可設 14 天，但 retention 只延後資料消失，不能提高每分鐘 5,000 個的完成速率，也無法挽回六小時後失去價值的工作。
- **D：** 正確。At-least-once processing 需要 idempotency；capacity planning 必須比較 arrival 與完成速率。
- **E：** 正確。Oldest age 直接反映 SLO/商業期限，超時工作不應永遠排擠仍有價值的工作。

**事實查證：** [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Amazon SQS standard queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 6｜SAA｜讓 application tier 可水平擴展

Web application 使用 Auto Scaling，但使用者在 scale-out 後常被登出，且新 instances 看不到舊 instance 上的 uploads。最根本的修正是什麼？

A. 把 session 與 uploads 移到適合的 shared/durable stores，讓任一 healthy instance 都能服務下一個 request
B. 永久啟用 sticky session，並把每位使用者綁在一台 instance 上
C. 在 scale-out 時複製 process memory 到新 instance
D. 把所有 instances 放回同一 AZ，讓 local filesystem 比較接近

**答案：A**

- **A：** 正確。Authoritative state 外置後 instances 才能被任意替換與水平擴展，並跨 AZ 分布。
- **B：** 錯誤。Stickiness 可作短期相容手段，但會造成不均衡、failover session loss 與擴展限制。
- **C：** 錯誤。Auto Scaling 不提供 application process memory replication，也不應依賴它保存 session。
- **D：** 錯誤。同一 AZ 既不共享各 instance 的 filesystem，也降低 failure isolation。

**事實查證：** [EC2 Auto Scaling target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[REL07-BP03 Obtain resources upon detection that more resources are needed](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_in_demand_dynamically_obtain_resources.html)、[AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)

### 練習題 7｜SAA｜選擇符合 target tracking 假設的 metric

每台 web instance 的吞吐量近似固定；當 fleet 增加時，每台分到的 ALB requests 會下降。哪個 target tracking metric 最符合比例擴展特性？

A. 全公司每日營收總額，因為營收越高就一定需要更多 instances
B. Fleet 的總 CPUCreditBalance，因為更多 instances 會讓總 credit 一直增加
C. ALBRequestCountPerTarget 或具有同類反比例特性的自訂 per-capacity demand metric
D. 每月一次發布的 marketing campaign 數量

**答案：C**

- **A：** 錯誤。營收和每單運算成本不一定呈固定關係，且增加 capacity 不會讓總營收 metric 下降。
- **B：** 錯誤。總 credit 會隨 instance 數改變基準，通常不是 demand/capacity 的因果比例訊號。
- **C：** 正確。Per-target request demand 隨負載增加而升、隨 capacity 增加而下降，適合 target tracking。
- **D：** 錯誤。低頻且非直接 demand 的 metric 無法及時驅動 elasticity。

**事實查證：** [EC2 Auto Scaling target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)

### 練習題 8｜SAA｜Default instance warmup 與 readiness

新 EC2 需要 8 分鐘載入模型後才能正常服務，但 scaling policy 在它啟動 1 分鐘後就把其初期低 CPU 納入平均並觸發 scale-in，造成震盪。應如何修正？

A. 把所有 alarms 關閉，讓 fleet 自由擴縮
B. 只把 health-check grace period 設得更長，並假設它對所有 scaling policy 都等同 instance warmup
C. 把 application 在模型尚未載入時就回報 healthy
D. 設定符合實際初始化時間的 default instance warmup，並讓 readiness/health check 在 dependency 就緒後才成功

**答案：D**

- **A：** 錯誤。停用 alarms 會移除容量 feedback 與異常訊號；只有在改用另一套明確的 scaling controller 與保護機制時才可能合理，不能用來修正 warmup/readiness。
- **B：** 錯誤。Health-check grace 與 scaling warmup 服務不同目的，不能一概互換。
- **C：** 錯誤。過早 healthy 會把 request 送到尚未可服務的 instance。
- **D：** 正確。Warmup 防止新容量尚未貢獻就影響 aggregate metrics，readiness 則保護 request routing。

**事實查證：** [EC2 Auto Scaling default instance warmup](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-default-instance-warmup.html)、[Health checks for instances in an Auto Scaling group](https://docs.aws.amazon.com/autoscaling/ec2/userguide/health-checks-overview.html)、[Health checks for Application Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)

### 練習題 9｜SAP｜平均 CPU 正常時診斷 p99

API 平均 CPU 35%、p50 80 ms，但 p99 偶爾 4 秒。團隊先不假設單一根因，哪兩項調查最能以多訊號找出真正的 constrained stage？（選兩項）

A. 依 operation、版本與 AZ 切分 p99 時段，將慢窗與 downstream latency、retry、throttle、connection 與 queue 指標對齊
B. 只看 fleet 平均 CPU；低於 50% 即可證明沒有 performance problem
C. 立即把每台 instance 加大兩倍，不保留 baseline
D. 只看單一分鐘的快照，未對齊 request volume、版本、AZ 或 downstream 指標
E. 關聯 ElastiCache `CacheHits/CacheMisses`、RDS engine-appropriate replica lag 與 `DatabaseConnections`、SQS oldest-message age、服務 throttles 與 p99

**答案：A、E**

- **A：** 正確。先以同一時間軸與維度找出哪個 stage 的 saturation 與 p99 同步變化，可建立可驗證假設；個別 trace mechanics 留給後續深入定位。
- **B：** 錯誤。I/O wait、lock、retries 或少數慢 dependency 可讓 p99 很差而平均 CPU 仍低。
- **C：** 錯誤。Scale-up 可能暫時掩蓋問題，卻沒有證明 bottleneck，也難比較效果。
- **D：** 錯誤。孤立快照無法分辨因果或共同尖峰；只有在流量、版本與依賴皆穩定時才可能提供有限線索，不能作主要診斷。
- **E：** 正確。這些 AWS 指標把 cache、database connection/replication、queue 與 quota 等候選限制對齊使用者結果；若應用另有 connection-pool saturation，也應以自訂 metric 補上。

**事實查證：** [Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)、[ElastiCache metrics for Valkey and Redis OSS](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheMetrics.Redis.html)、[Amazon CloudWatch metrics for Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-metrics.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 10｜SAP｜以 SLO 與成本驗證 performance change

團隊同時加入 cache、read replica 與更大的 instances，平均 latency 下降 10%，但 p99、errors 與成本來源不明。下一輪最好的方法是什麼？

A. 保留所有變更，因為任何平均改善都證明三個元件都必要
B. 使用相同代表性 traffic 與 failure conditions，逐一或以受控實驗變更主要瓶頸，比較 percentiles、errors、lag/backlog、hit rate 與每次成功交易成本
C. 只比較兩次測試的 instance 數量，不需要 business SLO
D. 將 p99 換成平均值，因為平均較容易達標

**答案：B**

- **A：** 錯誤。同時保留所有變更無法建立因果，也可能長期支付無效元件；只有在事故緊急緩解且後續仍安排拆分驗證時，才適合作暫時措施。
- **B：** 正確。Controlled comparison 能確認哪個機制解決哪個 bottleneck，並把效能、可靠性和成本放在同一決策。
- **C：** 錯誤。Instance 數不能代表使用者結果或 downstream constraints。
- **D：** 錯誤。若 SLO 關注 tail latency，平均值會掩蓋少數嚴重慢請求。

**事實查證：** [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「效能改善方法分別降低重算、分散讀取、吸收burst與增加平行capacity。」，所以「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」能直接滿足它；若constraint改成「Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」。替代方案「Vertical scaling是簡單過渡方案，但有上限、停機或大型instance成本。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「效能改善方法分別降低重算、分散讀取、吸收burst與增加平行capacity。」，排除會導致「同時加入cache、replica與queue，卻無法知道哪個解決哪個metric。」的選項，再選「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-3.3 Determine high-performing database solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先量測瓶頸：讀多用cache/replica，獨立工作水平擴展，短burst用queue。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「optimize the constrained stage, not the architecture diagram」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 65 章　Service Quota、Throttling 與 Graceful Degradation

雲端服務與下游都有quota，尖峰時成功率取決於是否在耗盡前降級。

## 從故障發生的那一刻倒推：先從故事開始

把鏡頭拉到一個真實的production現場：促銷時圖片推薦可關閉，但結帳必須保留capacity且不得無限排隊。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：雲端服務與下游都有quota，尖峰時成功率取決於是否在耗盡前降級。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Service Quotas是這一章的入口，Amazon CloudWatch用來畫出邊界；主要方向「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：促銷時圖片推薦可關閉，但結帳必須保留capacity且不得無限排隊。

正常production路徑
          ▼
[Service Quotas] → 使用者可觀察的結果
          │ 查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。

失敗時先找：只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Service Quotas有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Service Quotas和Amazon CloudWatch並不是兩個任意的產品名稱。前者適合本章，是因為「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」直接回應了眼前的問題；後者描述的「Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「every architecture has a finite admission boundary」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Service Quotas | 查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。 | 每account/Region quota限制resource或API rate；可用CloudWatch與request workflow管理。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 促銷時圖片推薦可關閉，但結帳必須保留capacity且不得無限排隊。

1. 故事的起點：促銷時圖片推薦可關閉，但結帳必須保留capacity且不得無限排隊。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Service Quotas負責「查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：每account/Region quota限制resource或API rate；可用CloudWatch與request workflow管理。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudWatch、AWS Lambda各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「提高quota不會修復下游瓶頸或成本；仍需admission control與graceful degradation。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Service Quotas

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：雲端服務與下游都有quota，尖峰時成功率取決於是否在耗盡前降級。
- **具體例子／邊界：** 在「促銷時圖片推薦可關閉，但結帳必須保留capacity且不得無限排隊。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudWatch

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：every architecture has a finite admission boundary。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Service Quotas

- **功用：** 查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。
- **底層機制：** 每account/Region quota限制resource或API rate；可用CloudWatch與request workflow管理。
- **關鍵設定：** quota code、applied/default value、automatic management、CloudWatch usage與increase request。
- **選擇時機：** launch readiness、multi-account capacity planning與throttling診斷。
- **替換時機：** 提高quota不會修復下游瓶頸或成本；仍需admission control與graceful degradation。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

## 考前與實作時再查：設定操作手冊

### Service Quotas：逐項設定說明

#### `quota code`

- **控制什麼：** `quota code`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。
- **何時需要：** Service Quotas capacity接近account/Region limit，或migration/launch會一次建立大量resources時。
- **怎麼設定／驗證：** 查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。
- **常見錯法：** Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。

#### `applied/default value`

- **控制什麼：** `applied/default value`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。
- **何時需要：** Service Quotas capacity接近account/Region limit，或migration/launch會一次建立大量resources時。
- **怎麼設定／驗證：** 查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。
- **常見錯法：** Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。

#### `automatic management`

- **控制什麼：** `automatic management`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。
- **何時需要：** Service Quotas capacity接近account/Region limit，或migration/launch會一次建立大量resources時。
- **怎麼設定／驗證：** 查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。
- **常見錯法：** Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。

#### `CloudWatch usage`

- **控制什麼：** `CloudWatch usage`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。
- **何時需要：** Service Quotas capacity接近account/Region limit，或migration/launch會一次建立大量resources時。
- **怎麼設定／驗證：** 查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。
- **常見錯法：** Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。

#### `increase request`

- **控制什麼：** `increase request`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。
- **何時需要：** Service Quotas capacity接近account/Region limit，或migration/launch會一次建立大量resources時。
- **怎麼設定／驗證：** 查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。
- **常見錯法：** Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。

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

1. Service Quotas的責任：查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。
2. 底層機制：每account/Region quota限制resource或API rate；可用CloudWatch與request workflow管理。
3. 第一個要看的設定：quota code、applied/default value、automatic management、CloudWatch usage與increase request。
4. 選擇邏輯：盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。
5. 不要混淆：Amazon CloudWatch的責任是「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；它不會自動取代Service Quotas。
6. 替換訊號：提高quota不會修復下游瓶頸或成本；仍需admission control與graceful degradation。
7. 最常見錯法：只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。
8. 可移植原則：every architecture has a finite admission boundary。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Service Quotas | 查看與申請AWS service quotas，避免capacity在流量前先被control limit阻擋。 | 每account/Region quota限制resource或API rate；可用CloudWatch與request workflow管理。 | launch readiness、multi-account capacity planning與throttling診斷。 | 提高quota不會修復下游瓶頸或成本；仍需admission control與graceful degradation。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。 | 只有當題目條件明確改變時才可能合理。 | 只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。」之間做選擇。
- 認得常考設定：quota code、applied/default value、automatic management、CloudWatch usage與increase request。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：提高quota不會修復下游瓶頸或成本；仍需admission control與graceful degradation。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜辨識 quota 的 scope、類型與 adjustability

團隊要把服務部署到新 Region，架構師看到「Lambda concurrent executions、VPCs per Region、某 API requests per second」三種限制。第一步應怎麼做？

A. 假設所有 limits 都是 global，primary Region 的 increase 會自動套用
B. 把三者都當作 EC2 capacity reservation
C. 在 Service Quotas 與服務文件中確認 quota code、account/Region scope、default/applied value、adjustability，以及它是 resource count 或 request-rate limit
D. 等 production 出現 throttle 後再判斷是哪一種

**答案：C**

- **A：** 錯誤。Quotas 有 global、Regional、account-specific 與 service-specific 差異，不能推定自動轉移。
- **B：** 錯誤。Resource quota、API throttle 與 EC2 capacity 是不同邊界。
- **C：** 正確。先分類 scope 與 limit semantics，才能決定 increase、admission、retry 或 architecture change。
- **D：** 錯誤。Launch/DR readiness 必須在流量前驗證，否則 recovery 或促銷時才發現會太晚。

**事實查證：** [AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 2｜SAP｜Service Quotas Automatic Management 的適用邊界

平台團隊想對所有 AWS limits 啟用 automatic management，並把 threshold 設 100%，相信之後永遠不會 throttling。哪個修正最準確？

A. 只對支援且可監控的 quotas 啟用，設定能留下處理 lead time 的 threshold，並保留 owner、budget、downstream 與 hard-limit 控制
B. 做法正確；Automatic Management 能讓每個不可調整 quota 無限增長
C. 把 threshold 保持在 100%，等用量碰到 quota 才開始申請 increase
D. 停用所有 workload alarms，因為 quota service 會取代 observability

**答案：A**

- **A：** 正確。Automatic Management 有支援範圍與條件，只是 quota management 元件，不會創造 downstream capacity 或免除治理。
- **B：** 錯誤。並非所有 quotas 都 adjustable 或受此功能支援，也不存在無限 scaling 保證。
- **C：** 錯誤。100% 才觸發代表 workload 可能已被 throttle，且 quota increase 不保證即時核准；只有完全無流量風險的測試環境才可能容忍這種零 lead-time 設定。
- **D：** 錯誤。Quota usage、throttle 與 business outcome 仍需持續監控。

**事實查證：** [Service Quotas Automatic Management](https://docs.aws.amazon.com/servicequotas/latest/userguide/automatic-management.html)、[AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)

### 練習題 3｜SAA → SAP｜建立 quota headroom 與 growth alarms

活動流量預計四週後成長 3 倍。哪兩項做法最能在 quota exhaustion 前留出行動時間？（選兩項）

A. 只監控 EC2 CPU，因為所有 quota 都會先反映在 CPU
B. 使用 Service Quotas usage metric 或 service-specific usage/throttle metrics，計算 applied quota 的 utilization 與 headroom
C. 只在出現大量 429 後才告警，避免 false positive
D. 用 AWS Budget 當作毫秒級 concurrency limiter
E. 把近期成長率與活動預測納入門檻，提早提交 increase 或降低 admission，並驗證 recovery Region 也有 headroom

**答案：B、E**

- **A：** 錯誤。Concurrency、API rate、IP 或 connection limits 可能先耗盡而 CPU 仍正常。
- **B：** 正確。Usage/quota 比率讓不同 limits 可被一致追蹤，service-specific metrics 則補充 throttle 行為。
- **C：** 錯誤。等使用者已收到 429 才處理通常沒有 lead time。
- **D：** 錯誤。Budget 是成本治理訊號，不是 request data-path 的即時 capacity control。
- **E：** 正確。Quota planning 要結合 growth 與 DR/launch scope，並在事故前完成 increase 或 admission strategy。

**事實查證：** [AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)、[Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)

### 練習題 4｜SAA｜區分 Lambda reserved 與 provisioned concurrency

同一帳號有 checkout 與 image-resize 兩個 Lambda。Image resize burst 會耗盡 account concurrency，checkout 另有 cold-start latency 要求。哪個設計最合理？

A. 只替 image resize 設 provisioned concurrency，這會自動保留 checkout 的 account capacity
B. 替所有 functions 設相同最大 reserved concurrency，無視下游 database limits
C. 只增加 function timeout，因為 timeout 等同 concurrency
D. 用 reserved concurrency 隔離／限制 functions 並保留 checkout capacity；若要降低 checkout startup latency，再評估 provisioned concurrency

**答案：D**

- **A：** 錯誤。Provisioned concurrency 預初始化 environments，並不自動替另一 function 隔離帳號 concurrency。
- **B：** 錯誤。Reserved concurrency 應依 priority 與 downstream capacity 分配，不是平均分滿。
- **C：** 錯誤。Timeout 增加反而可能讓 execution 占用 concurrency 更久。
- **D：** 正確。Reserved concurrency 同時提供 reservation 與 cap；provisioned concurrency 解決 startup latency，是不同責任。

**事實查證：** [Configuring reserved and provisioned concurrency for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

### 練習題 5｜SAA｜有界 exponential backoff、jitter 與 idempotency

某 AWS API 短暫回傳 throttling。500 個 clients 目前都每 10 ms 無限重試，讓服務更難恢復。最適合的修正是什麼？

A. 把 retry interval 固定改成 11 ms，確保 clients 同步
B. 只對 retryable failures 使用有限次數、exponential backoff 與 jitter，遵守 total deadline，非冪等 writes 使用 operation key
C. 把所有 timeouts 改成 24 小時，讓 request 永遠不失敗
D. 對 validation error 也無限 retry，因為所有 4xx 都是暫時性

**答案：B**

- **A：** 錯誤。固定且同步的 retry 仍會產生 thundering herd。
- **B：** 正確。Backoff+jitter 分散重試，有界 deadline 防止資源被永久占用，idempotency 保護重送 side effects。
- **C：** 錯誤。過長 timeout 會累積 threads/connections，掩蓋 sustained overload。
- **D：** 錯誤。不可重試的 client/configuration errors 不會因重送而成功。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)、[REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)

### 練習題 6｜SAP｜以 bulkhead 保留 critical transaction capacity

Checkout 與 personalized recommendations 共用同一 Lambda concurrency 和 RDS connection pool。促銷時 recommendations 讓 checkout 失敗。哪兩項改造最符合 graceful degradation？（選兩項）

A. 為 checkout 與 recommendation 分隔 reserved concurrency、queues 或 connection pools，並依 database 安全 capacity 設上限
B. 把兩者放入同一個更大的無界 work queue
C. 在壓力升高時關閉或回傳 cached/default recommendations，優先保留 checkout
D. 讓 recommendation clients 無限 retry，直到取得 checkout connections
E. 對兩種流量都回傳成功，即使付款尚未授權

**答案：A、C**

- **A：** 正確。Bulkhead 可阻止 optional workload 吃完所有 shared capacity，cap 也保護 database。
- **B：** 錯誤。無界共享 queue 仍允許 optional work 排擠 critical deadlines。
- **C：** 正確。Recommendation 可近似或暫停，checkout 則保留正確性與 capacity。
- **D：** 錯誤。無限 retries 會加劇 saturation，沒有創造真正容量。
- **E：** 錯誤。Graceful degradation 不可捏造不可逆 financial success。

**事實查證：** [REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)、[Configuring reserved and provisioned concurrency for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

### 練習題 7｜SAA｜依 useful age 管理 asynchronous backlog

Recommendation jobs 若等待超過 20 分鐘就沒有價值。SQS retention 是 4 天，consumer 過載後 backlog age 已達 2 小時。最合理的處置是什麼？

A. 把 retention 增加到 14 天，讓無效 jobs 保存更久
B. 只看 visible message count，不需要 oldest age
C. 繼續按 FIFO 處理所有舊 recommendations，即使新的 checkout events 也在等
D. 定義 maximum useful age，監控 oldest age/arrival/completion rate，擴容並將過期工作丟棄或送往明確的處置流程

**答案：D**

- **A：** 錯誤。Retention 是最大保存時間，不是商業 deadline，也不增加 processing throughput。
- **B：** 錯誤。Age 才顯示使用者期限是否已違反；depth 單獨不足。
- **C：** 錯誤。已失去價值的工作會繼續消耗 scarce capacity。
- **D：** 正確。Bounded usefulness 讓 queueing 成為可控 backpressure，而不是無限延後失敗。

**事實查證：** [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)

### 練習題 8｜SAA → SAP｜為可近似與不可近似功能設計誠實降級

下游 inventory service 暫時不可用。產品頁可以顯示稍舊庫存，但下單不能超賣。哪個 degraded-mode contract 最合理？

A. 產品頁顯示帶時間戳的 cached inventory；checkout 無法確認時回 pending/拒絕或排入受控流程，並發布 degraded-mode metrics
B. 所有 checkout 都直接回 SUCCESS，之後再看是否有庫存
C. 因 inventory 不可用，連靜態產品圖片與說明也全部回 500
D. 隱藏 degraded mode，不建立任何 metric，避免客戶知道

**答案：A**

- **A：** 正確。可近似的 read 可降級，但不可捏造需要強 correctness 的 inventory reservation。
- **B：** 錯誤。未確認庫存就回成功會破壞不可超賣的 invariant；只有業務明確接受 backorder、補償與客戶通知時，才可改成另一種經產品批准的契約。
- **C：** 錯誤。Failing optional content 會把局部 dependency failure 擴大成全站 outage。
- **D：** 錯誤。降級狀態必須可觀測，才能控制 error budget、容量與恢復。

**事實查證：** [REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 9｜SAP｜把 quotas 納入 DR readiness

Recovery Region 的 CloudFormation dry run 已成功建立少量 resources。正式簽署「可在 RTO 內承載 10 倍 disaster traffic」之前，哪一項是最完整的下一個驗證動作？

A. 盤點 recovery account/Region 中各 quota 的 Region、AZ 或 resource scope 與 applied value，也確認 IP/ENI、instance 與連線上限，但不部署 production-scale recovery stack 或執行代表性 disaster load
B. 直接部署 production 數量並執行代表性 disaster load，卻沿用 primary Region 的 quota 假設，不先核對 recovery Region 的 quota scope、applied value 與 increase lead time
C. 先核對 recovery account/Region 的 quota scope、applied value 與 increase lead time，再以 production 數量建立 recovery stack；在 RTO 時鐘內測試啟動速率、代表性流量、IP/ENI、connections、instance capacity、下游 headroom 與業務 SLO
D. 完成 quota 與 production-scale steady-state load 驗證，但先人工預熱所有容量再開始 RTO 計時，且不測試真實 failover 的啟動速率與下游故障後 headroom

**答案：C**

- **A：** 錯誤。這個 quota/capacity inventory 補足了 scope 與 applied value，但缺少 production-scale deployment、代表性流量與業務 SLO，仍不能證明 data plane 可承載災難負載。
- **B：** 錯誤。Production-scale load test 很重要，但未先驗證 recovery Region 的 quota scope、applied value 與 increase lead time，可能直到演練或事故才發現無法取得所需容量。
- **C：** 正確。它同時驗證 control-plane quota、production-scale data plane、啟動與擴展時序、下游容量和使用者結果，並把所有步驟放進真實 RTO 時鐘。
- **D：** 錯誤。Steady-state capacity 證據不能取代 recovery execution；先預熱再計時會漏掉啟動速率，且未驗證下游故障後 headroom，無法支持題目的 RTO 宣稱。

**事實查證：** [AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)、[REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 10｜SAP｜有 safety controls 的 overload game day

團隊要測試 recommendation overload 不會拖垮 checkout。哪兩項最能產生可信證據？（選兩項）

A. 測試前移除所有 concurrency caps，讓 database 自行失敗
B. 在定義範圍與 stop conditions 下增加 optional load 或限制 capacity，觀察 throttle、retry volume、queue age 與 rejection/degradation rate
C. 只確認 CloudWatch alarm 曾進入 ALARM，不看交易結果
D. 先把所有 quotas 提到無限大，再宣稱 graceful degradation 通過
E. 量測 checkout success/latency、資料正確性與恢復時間，據結果調整 bulkhead、threshold 與 runbook

**答案：B、E**

- **A：** 錯誤。無 safeguards 的 production overload 不是受控實驗，可能破壞核心資料。
- **B：** 正確。受控注入配合 system signals 可驗證 admission、retry 與 backpressure 行為。
- **C：** 錯誤。Alarm 是偵測元件；題目要證明核心 business transaction 被保護。
- **D：** 錯誤。移除限制會跳過真正要測的 finite boundary 與 degradation mechanism。
- **E：** 正確。Business SLO、correctness 與 recovery 才是 acceptance criteria，結果應回饋架構。

**事實查證：** [AWS Fault Injection Service concepts and safeguards](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)、[REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「雲端服務與下游都有quota，尖峰時成功率取決於是否在耗盡前降級。」，所以「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」能直接滿足它；若constraint改成「Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」。替代方案「Retry可處理短暫throttle，但若arrival rate長期高於capacity只會惡化。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「雲端服務與下游都有quota，尖峰時成功率取決於是否在耗盡前降級。」，排除會導致「只監控CPU，直到Lambda concurrency、NAT ports或API quota先耗盡。」的選項，再選「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「盤點quota、預先申請、監控usage，對非關鍵功能load shed並保留核心transaction。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「every architecture has a finite admission boundary」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 66 章　CloudWatch Metrics、Logs、Alarms 與 Dashboards

沒有可觀測性時，團隊只能從使用者抱怨猜測跨服務問題。

## 從故障發生的那一刻倒推：先從故事開始

如果今天由你值班，收到的需求可能是這樣：訂單失敗率上升但所有EC2 CPU正常，SQS age與下游429正在增加。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：沒有可觀測性時，團隊只能從使用者抱怨猜測跨服務問題。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：關聯式資料庫像一本正式帳簿：交易要讓多個欄位一起成立，讀副本則像提供影本給查詢者使用。 這只是起點，因為副本可能有延遲，failover也涉及client重新連線；不能把影本當成永遠同步的主帳簿。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon CloudWatch承接主要責任，以CloudWatch Logs檢查替代條件，並用「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：訂單失敗率上升但所有EC2 CPU正常，SQS age與下游429正在增加。

正常production路徑
          ▼
[Amazon CloudWatch] → 使用者可觀察的結果
          │ 收集metrics、logs、events與synthetic/real-user signals以監控AWS w…
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · CloudWatch Logs：集中保存與查詢application、service與audit logs。
  · CloudWatch Alarms：將metric或composite condition轉成OK/ALARM/INSUFFICIENT_DA…

失敗時先找：只告警平均CPU，忽略p99 latency、error rate、queue age與business success。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Amazon CloudWatch有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon CloudWatch和CloudWatch Logs並不是兩個任意的產品名稱。前者適合本章，是因為「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」直接回應了眼前的問題；後者描述的「High-cardinality資料不應全部變metric dimensions，可放log或trace。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只告警平均CPU，忽略p99 latency、error rate、queue age與business success。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「observe user outcomes, then supporting resources」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| CloudWatch Logs | 集中保存與查詢application、service與audit logs。 | Log events寫入log stream/group，可用filter、Logs Insights、subscription與retention處理。 |
| CloudWatch Alarms | 將metric或composite condition轉成OK/ALARM/INSUFFICIENT_DATA並觸發action。 | 依period、evaluation periods、datapoints-to-alarm與missing-data policy評估時間序列。 |

## 把全圖套進一個具體案例

**場景：** 訂單失敗率上升但所有EC2 CPU正常，SQS age與下游429正在增加。

1. 故事的起點：訂單失敗率上升但所有EC2 CPU正常，SQS age與下游429正在增加。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon CloudWatch負責「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：CloudWatch Logs、CloudWatch Alarms各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只告警平均CPU，忽略p99 latency、error rate、queue age與business success。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon CloudWatch

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：沒有可觀測性時，團隊只能從使用者抱怨猜測跨服務問題。
- **具體例子／邊界：** 在「訂單失敗率上升但所有EC2 CPU正常，SQS age與下游429正在增加。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### CloudWatch Logs

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：High-cardinality資料不應全部變metric dimensions，可放log或trace。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只告警平均CPU，忽略p99 latency、error rate、queue age與business success。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：observe user outcomes, then supporting resources。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### CloudWatch Logs

- **功用：** 集中保存與查詢application、service與audit logs。
- **底層機制：** Log events寫入log stream/group，可用filter、Logs Insights、subscription與retention處理。
- **關鍵設定：** log groups/streams、retention、KMS、metric/subscription filters、Logs Insights與cross-account observability。
- **選擇時機：** 需要事件context、search、centralization與log-derived metrics。
- **替換時機：** 高cardinality長期archive可delivery至S3；單次request因果需tracing。

### CloudWatch Alarms

- **功用：** 將metric或composite condition轉成OK/ALARM/INSUFFICIENT_DATA並觸發action。
- **底層機制：** 依period、evaluation periods、datapoints-to-alarm與missing-data policy評估時間序列。
- **關鍵設定：** metric/statistic、threshold、comparison、period、evaluation periods、M/N、treat missing data與actions。
- **選擇時機：** SLO symptoms、capacity、queue age、error rate與automated rollback/scaling。
- **替換時機：** 單一瞬時data point不應直接page；複雜business logic可先發custom metric。

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

### CloudWatch Logs：逐項設定說明

#### `log groups/streams`

- **控制什麼：** `log groups/streams`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從CloudWatch Logs持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要事件context、search、centralization與log-derived metrics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定CloudWatch Logs的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「需要事件context、search、centralization與log-derived metrics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Logs指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `metric/subscription filters`

- **控制什麼：** `metric/subscription filters`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `Logs Insights`

- **控制什麼：** `Logs Insights`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要事件context、search、centralization與log-derived metrics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Logs選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `cross-account observability`

- **控制什麼：** `cross-account observability`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「需要事件context、search、centralization與log-derived metrics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Logs建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### CloudWatch Alarms：逐項設定說明

#### `metric/statistic`

- **控制什麼：** `metric/statistic`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「SLO symptoms、capacity、queue age、error rate與automated rollback/scaling。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudWatch Alarms選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `threshold`

- **控制什麼：** `threshold`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `comparison`

- **控制什麼：** `comparison`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `period`

- **控制什麼：** `period`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「SLO symptoms、capacity、queue age、error rate與automated rollback/scaling。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定CloudWatch Alarms的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `evaluation periods`

- **控制什麼：** `evaluation periods`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「SLO symptoms、capacity、queue age、error rate與automated rollback/scaling。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定CloudWatch Alarms的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `M/N`

- **控制什麼：** `M/N`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `treat missing data`

- **控制什麼：** `treat missing data`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `actions`

- **控制什麼：** Alarm actions是在狀態轉為ALARM、OK或INSUFFICIENT_DATA時通知SNS、調整Auto Scaling或執行支援的自動化動作。
- **何時需要：** 告警需要通知owner或觸發安全、可逆且有明確邊界的自動反應時。
- **怎麼設定／驗證：** 為每個state設定action ARN與service role，先用測試metric驗證；高風險remediation加入rate limit、approval與rollback。
- **常見錯法：** Alarm action不是無條件修復；反覆flapping可能重複觸發，錯誤自動化也可能比原故障造成更大blast radius。

## 可以直接對照 AWS 的設定範例

### CloudWatch p99 latency alarm

```yaml
Resources:
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

```

1. 3-of-5避免單點noise，仍能在持續p99惡化時告警。
2. TreatMissingData必須依metric語意設定；沒有request時notBreaching合理，但heartbeat metric可能應breaching。
3. Resource latency alarm要與business success/error-rate alarm並列，否則快速失敗可能看似低延遲。

## 讀到這裡，請用自己的話說一次

1. Amazon CloudWatch的責任：收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
2. 底層機制：AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
3. 第一個要看的設定：namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
4. 選擇邏輯：Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。
5. 不要混淆：CloudWatch Logs的責任是「集中保存與查詢application、service與audit logs。」；它不會自動取代Amazon CloudWatch。
6. 替換訊號：API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。
7. 最常見錯法：只告警平均CPU，忽略p99 latency、error rate、queue age與business success。
8. 可移植原則：observe user outcomes, then supporting resources。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| CloudWatch Logs | 集中保存與查詢application、service與audit logs。 | Log events寫入log stream/group，可用filter、Logs Insights、subscription與retention處理。 | 需要事件context、search、centralization與log-derived metrics。 | 高cardinality長期archive可delivery至S3；單次request因果需tracing。 |
| CloudWatch Alarms | 將metric或composite condition轉成OK/ALARM/INSUFFICIENT_DATA並觸發action。 | 依period、evaluation periods、datapoints-to-alarm與missing-data policy評估時間序列。 | SLO symptoms、capacity、queue age、error rate與automated rollback/scaling。 | 單一瞬時data point不應直接page；複雜business logic可先發custom metric。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | High-cardinality資料不應全部變metric dimensions，可放log或trace。 | 只有當題目條件明確改變時才可能合理。 | 只告警平均CPU，忽略p99 latency、error rate、queue age與business success。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「High-cardinality資料不應全部變metric dimensions，可放log或trace。」之間做選擇。
- 認得常考設定：namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAP｜由使用者結果定義 SLI、SLO 與 error budget

Checkout 團隊過去只看 EC2 CPU，現在要建立能反映使用者是否成功完成交易的 28 天 rolling SLO。下列哪個定義最可操作？

A. 99.9% 的有效 checkout requests 在 800 ms 內成功完成，以 28 天為 interval；不符合部分消耗 error budget 並觸發對應 burn-rate action
B. EC2 CPU 永遠低於 60%，因為 CPU 就是 checkout availability
C. 服務要「一直很快」，不設定 threshold、population 或時間區間
D. 直接採用 RDS SLA 當作整個 checkout path 的 SLO

**答案：A**

- **A：** 正確。它定義 user-visible outcome、門檻、population 與 interval，能計算 compliance/error budget。
- **B：** 錯誤。CPU 是 supporting resource signal，不等同成功 checkout。
- **C：** 錯誤。沒有可量測 threshold、population 與 interval，就無法計算 compliance、告警或比較改善效果。
- **D：** 錯誤。完整 checkout 還包含 ingress、application、payments 與其他 dependencies。

**事實查證：** [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 2｜SAA｜區分 metrics、logs 與 traces 的責任

付款成功率突然下降，但服務跨越 API、queue 與 database，單一畫面看不出失敗在哪裡。哪兩項敘述正確描述 telemetry 的互補角色？（選兩項）

A. 把每個 request ID 都做成 metric dimension，是最低成本且唯一需要的觀測方式
B. Metrics 用來觀察成功率、latency 與趨勢並驅動 alarms；traces 用來連接單次 request 的跨服務 path
C. Dashboard 可以取代原始 logs，因此不需保留事件 context
D. Logs 保存錯誤、參數與事件 context；以穩定 correlation ID 和 trace/deploy 資訊關聯
E. Traces 應作為唯一不可變 audit record，取代 CloudTrail

**答案：B、D**

- **A：** 錯誤。每個 ID 都會建立高 cardinality custom metrics；request-level identity 更適合 log/trace。
- **B：** 正確。Metrics 提供 population-level signal，traces 分解特定 request dependencies。
- **C：** 錯誤。Dashboard 是呈現層，不保留每個事件的詳細診斷 context。
- **D：** 正確。Logs 可說明 implicated component 發生什麼事，correlation fields 讓三種 telemetry 互相定位。
- **E：** 錯誤。Trace sampling 與 retention 不適合取代 API audit trail。

**事實查證：** [Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)、[CloudWatch Logs groups and streams](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)、[AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)

### 練習題 3｜SAA → SAP｜先監控 business outcome 再看 resource

所有 EC2 CPU 都低於 40%，但訂單完成率下降；同時 SQS oldest age 與下游 429 增加。哪個 alarm strategy 最合理？

A. 只告警 EC2 status checks，因為 CPU 正常代表 application 正常
B. 把 accepted HTTP requests 當作 completed orders，不追蹤最終結果
C. 以訂單成功率、end-to-end latency 或 backlog age 為 primary user-impact alarms，再用 CPU、429、connections 與 queue metrics 診斷
D. 移除 business metrics，避免它們和 resource metrics 衝突

**答案：C**

- **A：** 錯誤。Dependency saturation 或 queued work 可在 EC2 CPU 正常時傷害使用者。
- **B：** 錯誤。Accepted 只量到入口接收，付款、持久化或履約仍可能失敗；只有 API 契約本身就是 durable asynchronous admission 時，accepted 才能作另一個獨立 SLI。
- **C：** 正確。User outcome 決定是否真的 outage，resource signals 用來解釋原因。
- **D：** 錯誤。Business 與 resource signals 是互補關係：前者判斷使用者影響，後者協助定位受限元件。

**事實查證：** [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 4｜SAA｜以 percentile 觀察 tail latency

某 API 一小時內 99% requests 為 100 ms，1% requests 為 10 秒。團隊只看 average，認為服務約 199 ms 很健康。哪個修正最合理？

A. 改看每月平均，資料越多越能掩蓋短期異常
B. 把所有 instance 的 p99 直接相加得到 global p99
C. 把 p99 解讀成單一最慢 request
D. 以符合 SLO window 的 p95/p99 搭配 sample count、success rate 與 operation dimensions，保留 average 作輔助

**答案：D**

- **A：** 錯誤。更長平均 window 會讓 tail impact 更難被看到。
- **B：** 錯誤。Percentiles 不能用普通加法合併；應由符合統計條件的 aggregate distribution 計算。
- **C：** 錯誤。P99 是分布中第 99 百分位，並非單一最慢 request；若樣本量極小或統計不適合計算 percentile，才應改用原始樣本或其他統計。
- **D：** 正確。Tail percentile 直接暴露受影響少數使用者，count 與 success rate 提供統計和品質 context。

**事實查證：** [Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)

### 練習題 5｜SAA｜設定 M-of-N 與 missing data

一個 error metric 只在發生錯誤時發布，平時完全沒有 datapoint。Alarm 使用 3 個 periods、2 datapoints to alarm。若目標是「沒有 error 時不要因 missing 而告警」，應怎麼設定？

A. 永遠把 missing data 當 breaching，因為沒有資料一定是 outage
B. 保留 2-of-3 抗單點雜訊，並依 emission contract 將 missing 視為 notBreaching；另用獨立 heartbeat 監控 telemetry silence
C. 把 missing data 當作一個真實值 100%，不需要知道 metric 語意
D. 只要設定 dashboard，alarm 便會自動理解 missing

**答案：B**

- **A：** 錯誤。對稀疏 error-only metric，正常無錯也會沒有資料，breaching 會產生 false alarms。
- **B：** 正確。M-of-N 可容忍瞬間 spike，missing treatment 必須符合發布語意；heartbeat 解決 telemetry loss 的另一風險。
- **C：** 錯誤。Missing 並不是任意數值，應由 metric contract 判斷。
- **D：** 錯誤。Dashboard 不會改變 alarm evaluation。

**事實查證：** [Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)

### 練習題 6｜SAP｜用 composite alarm 降低 page noise

每個 EC2、RDS、queue alarm 都直接 page on-call，造成同一事件 40 次通知。團隊希望只有「使用者 SLO 受影響且至少一個相關 dependency 異常」才 page，同時保留元件 alarms 供診斷。應使用什麼？

A. 建立 CloudWatch composite alarm 組合 user-impact 與 dependency alarms，讓底層 alarms 不直接執行 page action
B. 刪除所有 component alarms，只保留一張 dashboard
C. 把所有 alarms 用 OR 組合，任何單一低風險事件都 page
D. 將 alarm history 當作新的 metric dimension

**答案：A**

- **A：** 正確。Composite alarm 可用 Boolean rule 限制通知條件，底層 alarms 仍保留 state 與診斷價值。
- **B：** 錯誤。刪除 component signals 會降低 root-cause visibility，dashboard 也不主動 page。
- **C：** 錯誤。無差別 OR 會讓任何底層波動都 page，通常放大 noise；只有每個 constituent alarm 都代表獨立且必須立即處理的 user impact 時才適合。
- **D：** 錯誤。Alarm history 不是用來建立 dependency Boolean logic 的 metric。

**事實查證：** [Combining alarms with CloudWatch composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-combining.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 7｜SAP｜控制 custom metric cardinality 與 EMF 成本

開發團隊使用 Embedded Metric Format，準備把 userId、requestId、full URL 與 timestamp 全設為 dimensions。哪個建議最好？

A. 全部保留，因為 EMF 會讓 unlimited cardinality 免費
B. 移除所有 dimensions，讓任何 service/operation 都無法分辨
C. 只保留有界且可行動的 dimensions，例如 service、operation、status class；把 user/request 等高 cardinality 欄位留在 log/trace
D. 每次 request 動態建立新的 dimension name，避免重複

**答案：C**

- **A：** 錯誤。每組 dimension values 可形成獨立 custom metric，會增加數量與成本。
- **B：** 錯誤。完全無 dimensions 會失去必要 breakdown；應選 bounded operational dimensions。
- **C：** 正確。Metrics 適合聚合，log/trace 適合 request-level context。
- **D：** 錯誤。動態 key 會讓 schema 與 cardinality 更不可控。

**事實查證：** [CloudWatch embedded metric format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)

### 練習題 8｜SAA｜區分 Logs retention、Insights、metric filter 與 subscription

團隊要讓 application logs 保存 90 天、偶爾互動查詢，並把符合 security pattern 的新事件持續送到中央處理器。哪兩項配置正確？（選兩項）

A. 使用 CloudWatch metric retention 設定刪除 log events
B. 在 log group 設定 retention/encryption，使用 Logs Insights 做 ad hoc queries
C. 把 Logs Insights query 當成永遠運行的 streaming consumer
D. 為每個 raw log field 建立一個高 cardinality custom metric
E. 使用 subscription filter 將 matching events 持續送往支援的 destination；需要 bounded alarm signal 時另用 metric filter

**答案：B、E**

- **A：** 錯誤。Metric retention 與 log group retention 是不同機制。
- **B：** 正確。Log group 控制保存生命週期；Insights 適合互動式分析。
- **C：** 錯誤。Logs Insights 是 query 能力，不是 continuous delivery pipeline。
- **D：** 錯誤。Raw high-cardinality fields 會產生大量 metrics；應只抽取有界 operational signal。
- **E：** 正確。Subscription filter 是持續事件傳送機制，metric filter 則從 log pattern 產生可告警數值。

**事實查證：** [CloudWatch Logs groups and streams](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)、[Analyze log data with CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)、[Create metrics from log events using filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html)、[Real-time processing of log data with subscription filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html)、[CloudWatch embedded metric format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)

### 練習題 9｜SAP｜CloudWatch cross-account observability 與 ownership

公司有 80 個 workload accounts，希望 central operations 能跨帳號查看 metrics、logs 與 traces，但 workload teams 仍保留自己的 retention 與 incident ownership。哪個設計最合理？

A. 把所有 production resources 搬到單一帳號，因為 observability 不能跨帳號
B. 把每個 workload 的長期 access keys 複製到 central dashboard server
C. 假設 central view 會自動修改所有 source log retention 與 alarms
D. 使用 CloudWatch cross-account observability，把 source accounts 連到 monitoring account，標準化 identifiers/access，並保留 source-account owners 與 response paths

**答案：D**

- **A：** 錯誤。單帳號擴大 blast radius，也不是 cross-account telemetry 的必要條件。
- **B：** 錯誤。複製長期 credentials 增加風險；應使用服務提供的授權與 linking。
- **C：** 錯誤。集中觀察不等於自動接管 source configuration 或 operational ownership。
- **D：** 正確。Monitoring account 提供統一視圖，同時 source accounts 保留資源、政策與責任邊界。

**事實查證：** [CloudWatch cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)

### 練習題 10｜SAP｜區分 runtime、API audit 與 configuration history

部署後 checkout latency 上升。調查同時需要 runtime impact、誰修改了 security group，以及 resource configuration 前後差異。哪兩項描述正確？（選兩項）

A. 用 CloudWatch SLO/metrics/logs 量測使用者影響，再與 deploy/change timestamp 關聯
B. 只看綠色 dashboard 即可證明沒有任何 API change
C. 使用 CloudTrail 當作毫秒級 application latency time series
D. 使用 AWS Config 作為每筆 checkout transaction 的業務 event log
E. 用 CloudTrail 查 API actor/time，用 AWS Config 查 resource configuration/history，兩者和 runtime telemetry 互補

**答案：A、E**

- **A：** 正確。CloudWatch 描述 runtime 與 user outcome，是判斷 rollback impact 的主要證據。
- **B：** 錯誤。Dashboard 只呈現選定 signals，不能否定未顯示的 configuration change。
- **C：** 錯誤。CloudTrail 記錄 AWS API activity，不是 application latency metric 系統。
- **D：** 錯誤。Config 追蹤資源 configuration 與 compliance，不是業務交易日誌。
- **E：** 正確。CloudTrail 回答誰做了什麼 API 操作，Config 回答資源狀態如何改變。

**事實查證：** [CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與re…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「沒有可觀測性時，團隊只能從使用者抱怨猜測跨服務問題。」，所以「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」能直接滿足它；若constraint改成「High-cardinality資料不應全部變metric dimensions，可放log或trace。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」。替代方案「High-cardinality資料不應全部變metric dimensions，可放log或trace。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只告警平均CPU，忽略p99 latency、error rate、queue age與business success。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「沒有可觀測性時，團隊只能從使用者抱怨猜測跨服務問題。」，排除會導致「只告警平均CPU，忽略p99 latency、error rate、queue age與business success。」的選項，再選「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Metrics看趨勢與告警，logs保留事件context，dashboards連接business與resource signals。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「observe user outcomes, then supporting resources」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 67 章　X-Ray、Tracing 與 Bottleneck Analysis

分散式request跨越多服務後，單一log無法還原延遲與因果。

## 從故障發生的那一刻倒推：先從故事開始

故事從一個看似簡單的需求開始：API p99偶發三秒，平均正常，需要知道慢在Lambda、DynamoDB還是外部API。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：分散式request跨越多服務後，單一log無法還原延遲與因果。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS X-Ray會是本章的主要角色，Amazon CloudWatch則幫我們看清邊界。方向是「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：API p99偶發三秒，平均正常，需要知道慢在Lambda、DynamoDB還是外部API。

正常production路徑
          ▼
[AWS X-Ray] → 使用者可觀察的結果
          │ 收集distributed traces並建立service map、latency與error因果。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…
  · AWS Distro for OpenTelemetry：以OpenTelemetry相容SDK與collector收集metrics、traces及相關telem…

失敗時先找：每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問AWS X-Ray有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS X-Ray和Amazon CloudWatch並不是兩個任意的產品名稱。前者適合本章，是因為「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」直接回應了眼前的問題；後者描述的「Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「correlation IDs turn distributed events into one causal path」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS X-Ray | 收集distributed traces並建立service map、latency與error因果。 | Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| AWS Distro for OpenTelemetry | 以OpenTelemetry相容SDK與collector收集metrics、traces及相關telemetry並送往AWS觀測服務。 | Application instrumentation產生OTLP資料，collector接收、處理、取樣並export到X-Ray、CloudWatch或其他相容backend。 |

## 把全圖套進一個具體案例

**場景：** API p99偶發三秒，平均正常，需要知道慢在Lambda、DynamoDB還是外部API。

1. 故事的起點：API p99偶發三秒，平均正常，需要知道慢在Lambda、DynamoDB還是外部API。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS X-Ray負責「收集distributed traces並建立service map、latency與error因果。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudWatch、AWS Distro for OpenTelemetry各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS X-Ray

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：分散式request跨越多服務後，單一log無法還原延遲與因果。
- **具體例子／邊界：** 在「API p99偶發三秒，平均正常，需要知道慢在Lambda、DynamoDB還是外部API。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudWatch

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：correlation IDs turn distributed events into one causal path。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS X-Ray

- **功用：** 收集distributed traces並建立service map、latency與error因果。
- **底層機制：** Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。
- **關鍵設定：** sampling rules、daemon/SDK/ADOT、annotations/metadata、groups與trace map。
- **選擇時機：** 定位跨Lambda/API/DB request的p99 bottleneck與errors。
- **替換時機：** 總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### AWS Distro for OpenTelemetry

- **功用：** 以OpenTelemetry相容SDK與collector收集metrics、traces及相關telemetry並送往AWS觀測服務。
- **底層機制：** Application instrumentation產生OTLP資料，collector接收、處理、取樣並export到X-Ray、CloudWatch或其他相容backend。
- **關鍵設定：** SDK auto/manual instrumentation、collector receivers/processors/exporters、sampling、resource attributes與IAM。
- **選擇時機：** 需要vendor-neutral instrumentation、跨ECS/EKS/EC2/Lambda統一收集pipeline時。
- **替換時機：** 只需要AWS managed trace backend可直接使用X-Ray SDK/daemon；telemetry仍需正確context propagation。

## 考前與實作時再查：設定操作手冊

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

### AWS Distro for OpenTelemetry：逐項設定說明

#### `SDK auto/manual instrumentation`

- **控制什麼：** 決定由agent自動攔截常見framework與AWS SDK，或由程式碼手動建立span、metric與business attributes來補足語意。
- **何時需要：** 需要快速取得HTTP／database基礎traces，同時又要觀測checkout、tenant或job等框架無法自動理解的business operation時。
- **怎麼設定／驗證：** 先啟用支援的auto instrumentation並驗證context propagation，再只對關鍵business boundaries加入manual spans與低基數attributes。
- **常見錯法：** 只靠auto instrumentation通常看不到business outcome；過度manual instrumentation或高基數attributes則會增加成本、噪音與敏感資料風險。

#### `collector receivers/processors/exporters`

- **控制什麼：** `collector receivers/processors/exporters`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「需要vendor-neutral instrumentation、跨ECS/EKS/EC2/Lambda統一收集pipeline時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Distro for OpenTelemetry的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `sampling`

- **控制什麼：** `sampling`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要vendor-neutral instrumentation、跨ECS/EKS/EC2/Lambda統一收集pipeline時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Distro for OpenTelemetry選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `resource attributes`

- **控制什麼：** `resource attributes`指定AWS Distro for OpenTelemetry讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `IAM`

- **控制什麼：** `IAM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「需要vendor-neutral instrumentation、跨ECS/EKS/EC2/Lambda統一收集pipeline時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Distro for OpenTelemetry明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 讀到這裡，請用自己的話說一次

1. AWS X-Ray的責任：收集distributed traces並建立service map、latency與error因果。
2. 底層機制：Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。
3. 第一個要看的設定：sampling rules、daemon/SDK/ADOT、annotations/metadata、groups與trace map。
4. 選擇邏輯：傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。
5. 不要混淆：Amazon CloudWatch的責任是「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；它不會自動取代AWS X-Ray。
6. 替換訊號：總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。
7. 最常見錯法：每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。
8. 可移植原則：correlation IDs turn distributed events into one causal path。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS X-Ray | 收集distributed traces並建立service map、latency與error因果。 | Trace由segments/subsegments組成，context跨服務傳遞；sampling控制成本。 | 定位跨Lambda/API/DB request的p99 bottleneck與errors。 | 總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| AWS Distro for OpenTelemetry | 以OpenTelemetry相容SDK與collector收集metrics、traces及相關telemetry並送往AWS觀測服務。 | Application instrumentation產生OTLP資料，collector接收、處理、取樣並export到X-Ray、CloudWatch或其他相容backend。 | 需要vendor-neutral instrumentation、跨ECS/EKS/EC2/Lambda統一收集pipeline時。 | 只需要AWS managed trace backend可直接使用X-Ray SDK/daemon；telemetry仍需正確context propagation。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。 | 只有當題目條件明確改變時才可能合理。 | 每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。」之間做選擇。
- 認得常考設定：sampling rules、daemon/SDK/ADOT、annotations/metadata、groups與trace map。
- 對應官方tasks：SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：總體趨勢先看metrics、詳細事件看logs；新instrumentation可優先OpenTelemetry。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA → SAP｜Metrics、traces、logs 的診斷順序

API p99 在新版本後惡化，但只有 2% requests 受影響。哪個調查流程最有效率？

A. 先閱讀所有服務的隨機 logs，不先限定 operation、版本或受影響 population
B. 先由 SLO/metrics 確認 operation、時間與版本，再比較快慢 traces 定位 path，最後查 implicated components 的 logs
C. 只看平均 CPU，因為 distributed latency 一定由 CPU 引起
D. 永久 100% tracing，並取消 metrics 和 logs

**答案：B**

- **A：** 錯誤。沒有先縮小範圍，logs 量大且缺少因果路徑，容易浪費時間。
- **B：** 正確。Population signal 找 impact，trace 找 request path，log 解釋該 component 的事件細節。
- **C：** 錯誤。Tail latency 可能來自 downstream、retry、cold start 或 connection wait。
- **D：** 錯誤。100% tracing 可能昂貴，且 trace 不能取代 alarm population 或詳細 event logs。

**事實查證：** [Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)、[AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)

### 練習題 2｜SAA｜跨同步服務傳遞 trace context

ALB 後的 Service A 呼叫 Service B，再呼叫 payment API。Service map 顯示三段互不相關的 root traces，無法還原一筆交易。最可能的修正是什麼？

A. 讓 ingress、application 與 supported SDK/client calls 傳遞 W3C/X-Ray 支援的 trace context，並在下游建立 child spans/subsegments
B. 每個 service 都產生新的 root trace，並只記在 local disk
C. 以 source IP 當作跨服務唯一 request identity
D. 移除 Service B 的 instrumentation，減少 trace nodes

**答案：A**

- **A：** 正確。共同 trace context 才能把同步 child calls 連回同一 causal path。
- **B：** 錯誤。新的 roots 正是 path 被切斷的原因；local log 也無法自動建立 parent-child。
- **C：** 錯誤。NAT、proxy 與連線重用會讓多個 requests 共享 IP，不能作 trace identity。
- **D：** 錯誤。移除 instrumentation 會增加盲點，不會修復 context propagation。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)、[OpenTelemetry in Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OpenTelemetry-Sections.html)

### 練習題 3｜SAA｜理解 segment、subsegment 與 inferred node

X-Ray service map 顯示 Service A 到外部 API 的 inferred node，但外部 API 沒有自己的 trace SDK。哪個解讀最正確？

A. Inferred node 證明外部 API 已完整上傳它的 internal logs 與 spans
B. 每個 segment 都必定代表一台 EC2 instance
C. 只要 map 有 edge，就能直接證明外部 API 是根因
D. Service A 的 downstream call data 可產生 inferred node；它顯示依賴與觀測到的 call，但下游內部仍可能沒有 instrumentation

**答案：D**

- **A：** 錯誤。Inferred node 可由 caller observation 建立，不代表 downstream 有完整 telemetry。
- **B：** 錯誤。Segment 表示 traced service/resource 的工作，不等同固定一台 host。
- **C：** 錯誤。Map edge 是診斷線索，仍需 trace timeline、responses 與 metrics 驗證 causality。
- **D：** 正確。Caller 能記錄 outbound subsegment，X-Ray 據此顯示 inferred dependency，但內部細節仍不可見。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)

### 練習題 4｜SAP｜以 sampling 控制成本且不隱藏 rare failures

支付 API 每秒 50,000 requests，錯誤率約 0.02%，其中 premium transactions 必須有較佳診斷覆蓋。哪兩項 sampling 設計合理？（選兩項）

A. 只 sample success，因為 failed requests 會污染資料
B. 保留有界 baseline sampling，並為高價值 operation/attributes 建立較高優先的 targeted rules
C. 永久 trace 100% traffic，且不設定成本或 retention guardrail
D. 由一個月無 sampled errors 推論 rare error 不存在
E. 以 error-rate metrics/logs 監控完整 population，將 sampling 當診斷取樣而非唯一 availability signal

**答案：B、E**

- **A：** 錯誤。排除 failures 會失去最需要分析的 traces。
- **B：** 正確。Baseline 保留整體可見性，targeted rules 對重要或罕見路徑增加機率。
- **C：** 錯誤。高流量 100% tracing 可能造成不必要的 telemetry 成本與管理壓力。
- **D：** 錯誤。Sampling 沒看到事件不代表 population 沒有事件。
- **E：** 正確。Metrics/logs 可覆蓋完整計數，traces 用來分解被抽中的 path。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 5｜SAP｜Annotations、metadata 與敏感資料邊界

團隊想讓 traces 可依 operation、tenant tier 與 deployment version 搜尋，也想附上大型 debug payload。哪個做法最合理？

A. 把完整 customer email、password 與 payload 都作為 indexed annotations
B. 每個 request 動態建立唯一 annotation key
C. 把有界且可搜尋的 operation/tier/version 放 annotations；較大非索引 context 放 metadata，並移除 secrets 與不必要個資
D. Metadata 不會被儲存，因此可安全放 credentials

**答案：C**

- **A：** 錯誤。敏感資料不應放入 telemetry；高 cardinality 個資也不適合作為 indexed annotation。
- **B：** 錯誤。穩定 schema 才能查詢與治理，動態 key 會失控。
- **C：** 正確。Annotations 用於有界 searchable attributes，metadata 用於非索引細節，兩者都需 data minimization。
- **D：** 錯誤。Metadata 仍是 trace data，不能把 credentials 放進去。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)

### 練習題 6｜SAP｜把 service map 當作 hypothesis 而非因果證明

Service map 顯示 DynamoDB node 的 latency 顏色最深。工程師因此直接宣稱 DynamoDB 是 root cause。哪個下一步最嚴謹？

A. 選取同 operation 的 slow traces，檢查 timeline、retries、client wait、response codes 與 correlated logs/metrics，再判斷責任
B. 先提高 DynamoDB capacity，卻不檢查 caller retries、SDK backoff、response codes 或 client-side waiting
C. 只依 node 顏色判定，因為 visualization 等同 causal proof
D. 忽略 upstream retry；同一 downstream call 永遠只會發生一次

**答案：A**

- **A：** 正確。Map 是聚合線索；trace timeline 與 service metrics 才能區分 downstream 慢、caller retry 或 client-side wait。
- **B：** 錯誤。提高 capacity 只有在確定是 capacity throttling 時才有用；若延遲來自 caller retry、網路等待或應用序列化，它只會增加成本而不消除根因。
- **C：** 錯誤。Service-map correlation 與聚合 latency 只能形成假設，不能單獨證明 downstream 是 root cause。
- **D：** 錯誤。Retries 可能放大 call count 與總等待，是常見 tail-latency 成因。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)、[Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)

### 練習題 7｜SAP｜用 trace timeline 分解 p99 bottleneck

Slow trace 有三個 spans：A 同時呼叫 B（900 ms）與 C（850 ms），之後重試 B（700 ms）；root duration 為 1.7 秒。哪兩項分析方式正確？（選兩項）

A. 把 B 與 C 的 900+850 ms 相加，因為任何 spans 都必然串行
B. 只看每個 service 的月平均，不比較 fast traces
C. 辨識 B/C 的 overlap、retry 與 root exclusive time；平行 spans 的 wall-clock contribution 不能直接相加
D. 把所有 services 同時加大，因為 trace 不能提供局部線索
E. 比較相同 operation 的 fast/slow traces，並以 B latency、retry rate、connections/throttles metrics 驗證假設

**答案：C、E**

- **A：** 錯誤。Parallel spans 重疊，直接相加會高估 critical path。
- **B：** 錯誤。月平均會掩蓋 tail；需要相同 operation/version 的分布比較。
- **C：** 正確。Timeline 結構能指出真正串行等待與 retry cost。
- **D：** 錯誤。無差別 scale 既昂貴，也無法確認問題是否在 capacity。
- **E：** 正確。Trace 建立 path hypothesis，service metrics 則驗證是否為持續 bottleneck。

**事實查證：** [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)、[Amazon CloudWatch metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)

### 練習題 8｜SAP｜跨 asynchronous messaging 關聯 producer 與 consumer

Producer 將 jobs 放入 SQS，數分鐘後 consumer 處理。團隊希望既能看 queue wait，也能把一筆 business job 串起來。哪兩項做法正確？（選兩項）

A. 使用 SQS `AWSTraceHeader` system attribute 傳遞 X-Ray-compatible trace context，consumer 取出 context 建立處理 span／segment，並另加穩定 job/business ID
B. 讓整個 queue 的所有 messages 永久共用同一 trace ID
C. 把 queue wait 全算成 consumer Lambda execution duration
D. 將 producer enqueue、queue wait 與 consumer processing 視為不同 timing segments，搭配 SQS age metrics
E. 只依 message body 的自然語言內容人工比對

**答案：A、D**

- **A：** 正確。`AWSTraceHeader` 是 SQS 保留的 system attribute，可延續原 trace；business ID 則支援跨抽樣與長時間 queue wait 的營運查詢，兩者責任不同。
- **B：** 錯誤。共用一個 trace 會混合無關 jobs 並破壞 trace size/semantics。
- **C：** 錯誤。Consumer duration 不含 message 在 queue 中等待的時間。
- **D：** 正確。Async path 有明確 admission、waiting 與 processing 階段，需用 traces 和 queue metrics 共同觀察。
- **E：** 錯誤。自然語言人工比對缺少穩定鍵值、容易誤關聯且無法自動化；只有一次性的小型調查可把它當輔助，不能作正式追蹤設計。

**事實查證：** [Tracing Amazon SQS messages with AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-sqs.html)、[OpenTelemetry in Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OpenTelemetry-Sections.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 9｜SAP｜新 instrumentation 遷移到 OpenTelemetry

公司在 2026 年 10 月開始一個預計運行五年的新 tracing 平台。Legacy X-Ray SDKs/daemon 已進 maintenance mode，AWS 公告其 support timeline。最合理的方向是什麼？

A. 完全取消 tracing，直到 2027 年後再決定
B. 以 OpenTelemetry／ADOT instrument 新服務，依需求 export 到 X-Ray/CloudWatch，並規劃 legacy SDK/daemon migration 與 context compatibility 測試
C. 新服務全部依賴 legacy daemon，且不建立 migration plan
D. 只替換 exporter binary，就假設 missing application spans 與 context propagation 都會自動修復

**答案：B**

- **A：** 錯誤。Support transition 是遷移理由，不是失去可觀測性的理由。
- **B：** 正確。Legacy X-Ray SDKs 與 daemon 已在 2026-02-25 進入 maintenance mode，官方目前把 end of support 列為 N/A；長期新平台應採 OpenTelemetry，並驗證 instrumentation、propagation、resource attributes、sampling 與 backend 相容性。
- **C：** 錯誤。對長期新系統忽略已公告的 maintenance/EOS timeline 會累積技術風險。
- **D：** 錯誤。Exporter 只處理傳送／轉換，不能替代應用程式 spans 與 header propagation。

**事實查證：** [X-Ray SDK and daemon support timeline](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-daemon-timeline.html)、[Migrate from X-Ray instrumentation to OpenTelemetry instrumentation](https://docs.aws.amazon.com/xray/latest/devguide/migrate-to-opentelemetry.html)、[OpenTelemetry in Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OpenTelemetry-Sections.html)

### 練習題 10｜SAP｜關聯 deployment、trace distribution 與 telemetry cost

Canary release 後只出現一條 8 秒 trace，團隊立刻要 rollback；同時 sampling 成本在一週內增加 8 倍。哪個決策方法較完整？

A. 只依一條 anecdotal trace rollback，無須確認它屬於哪個版本
B. 把 sampling 永久提升至 100%，成本不列入 architecture decision
C. 在 spans/logs 加入 service、operation 與 deployment identity，比較 canary/control 的 SLO 與 trace distribution，設定 sampling/cardinality budget，再依預定 gate rollback
D. 移除版本 attributes，讓兩個 cohorts 混在一起比較

**答案：C**

- **A：** 錯誤。一條 trace 可觸發調查，但需用 population-level metrics 與 cohort identity 判定 release impact。
- **B：** 錯誤。Telemetry volume 本身需要成本與資料治理。
- **C：** 正確。版本關聯、SLO distribution 和預定 rollback gate 提供可辯護決策，sampling budget 控制長期成本。
- **D：** 錯誤。沒有版本 identity 就無法把 regression 歸因到 canary。

**事實查證：** [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)、[CloudWatch embedded metric format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「傳遞trace context，建立segments/subsegments，使用sampling與ser…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「分散式request跨越多服務後，單一log無法還原延遲與因果。」，所以「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」能直接滿足它；若constraint改成「Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」。替代方案「Metrics先發現影響，trace定位單次path，logs提供細節，三者互補。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「分散式request跨越多服務後，單一log無法還原延遲與因果。」，排除會導致「每個服務產生不同request ID，或100% tracing造成成本與儲存壓力。」的選項，再選「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」。本章對應的代表task包括：SAA-3.2 Design high-performing and elastic compute solutions；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.3 Determine a strategy to improve performance。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「傳遞trace context，建立segments/subsegments，使用sampling與service map定位慢dependency。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「correlation IDs turn distributed events into one causal path」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 68 章　Reserved Instances、Savings Plans 與 Spot

Compute discount取決於使用承諾、instance彈性、中斷容忍與license。

## 從故障發生的那一刻倒推：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：服務有40%穩定基線、20%日常波動與大量可重跑夜間batch。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：Compute discount取決於使用承諾、instance彈性、中斷容忍與license。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Savings Plans負責主要工作，Reserved Instances提醒我們答案不是永遠固定。本章會走向「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：服務有40%穩定基線、20%日常波動與大量可重跑夜間batch。

正常production路徑
          ▼
[Savings Plans] → 使用者可觀察的結果
          │ 用一或三年每小時compute spend承諾換取折扣。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Reserved Instances：為特定EC2/RDS等使用承諾提供billing discount，某些EC2 zonal RI兼具cap…
  · EC2 Spot Instances：使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。

失敗時先找：將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Savings Plans有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Savings Plans和Reserved Instances並不是兩個任意的產品名稱。前者適合本章，是因為「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」直接回應了眼前的問題；後者描述的「Capacity Reservation解決容量保證，不自動等於billing discount。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「match pricing commitment to demand certainty」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Savings Plans | 用一或三年每小時compute spend承諾換取折扣。 | 帳單把eligible usage套用承諾；Compute SP較彈性，EC2 Instance SP較限定。 |
| Reserved Instances | 為特定EC2/RDS等使用承諾提供billing discount，某些EC2 zonal RI兼具capacity reservation。 | Billing依instance attributes匹配discount；Standard與Convertible交換彈性不同。 |
| EC2 Spot Instances | 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。 | Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。 |

## 把全圖套進一個具體案例

**場景：** 服務有40%穩定基線、20%日常波動與大量可重跑夜間batch。

1. 故事的起點：服務有40%穩定基線、20%日常波動與大量可重跑夜間batch。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Savings Plans負責「用一或三年每小時compute spend承諾換取折扣。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：帳單把eligible usage套用承諾；Compute SP較彈性，EC2 Instance SP較限定。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Reserved Instances、EC2 Spot Instances各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「特定EC2屬性與容量保留需求比較RI/Capacity Reservation；可中斷工作用Spot。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Savings Plans

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Compute discount取決於使用承諾、instance彈性、中斷容忍與license。
- **具體例子／邊界：** 在「服務有40%穩定基線、20%日常波動與大量可重跑夜間batch。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Reserved Instances

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Capacity Reservation解決容量保證，不自動等於billing discount。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：match pricing commitment to demand certainty。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Reserved Instance

對特定EC2/RDS等使用條件提供計價折扣或容量選項；它不是新的instance，也不會自動改善架構。

### EC2 instance

AWS虛擬機執行個體，由AMI、instance type、network、storage與IAM instance profile共同定義。

### Savings Plan

以每小時固定用量承諾換取符合範圍compute usage折扣；要追蹤coverage與utilization。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

## 回到 AWS：Components、功用與責任邊界

### Savings Plans

- **功用：** 用一或三年每小時compute spend承諾換取折扣。
- **底層機制：** 帳單把eligible usage套用承諾；Compute SP較彈性，EC2 Instance SP較限定。
- **關鍵設定：** Compute/EC2/SageMaker type、term、payment option、hourly commitment、sharing與coverage/utilization。
- **選擇時機：** 可預測baseline compute且希望跨family/Region較彈性。
- **替換時機：** 特定EC2屬性與容量保留需求比較RI/Capacity Reservation；可中斷工作用Spot。

### Reserved Instances

- **功用：** 為特定EC2/RDS等使用承諾提供billing discount，某些EC2 zonal RI兼具capacity reservation。
- **底層機制：** Billing依instance attributes匹配discount；Standard與Convertible交換彈性不同。
- **關鍵設定：** scope、instance family/type、platform、tenancy、term、payment與offering class。
- **選擇時機：** 穩定、明確的instance footprint或需要zonal capacity benefit。
- **替換時機：** 跨family/Region彈性通常Compute Savings Plans較佳；RI不會自動讓instance啟動。

### EC2 Spot Instances

- **功用：** 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。
- **底層機制：** Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。
- **關鍵設定：** allocation strategy、instance diversification、capacity-optimized、max price、interruption handling與mixed instances policy。
- **選擇時機：** batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。
- **替換時機：** 不可中斷single point、stateful primary或無重試設計不能只用Spot。

## 考前與實作時再查：設定操作手冊

### Savings Plans：逐項設定說明

#### `Compute/EC2/SageMaker type`

- **控制什麼：** `Compute/EC2/SageMaker type`選擇Savings Plans的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `term`

- **控制什麼：** `term`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「可預測baseline compute且希望跨family/Region較彈性。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Savings Plans設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `payment option`

- **控制什麼：** `payment option`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「可預測baseline compute且希望跨family/Region較彈性。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Savings Plans設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `hourly commitment`

- **控制什麼：** `hourly commitment`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「可預測baseline compute且希望跨family/Region較彈性。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Savings Plans設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `sharing`

- **控制什麼：** `sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「可預測baseline compute且希望跨family/Region較彈性。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Savings Plans建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `coverage/utilization`

- **控制什麼：** `coverage/utilization`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「可預測baseline compute且希望跨family/Region較彈性。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Savings Plans設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

### Reserved Instances：逐項設定說明

#### `scope`

- **控制什麼：** `scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「穩定、明確的instance footprint或需要zonal capacity benefit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Reserved Instances建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `instance family/type`

- **控制什麼：** `instance family/type`選擇Reserved Instances的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `platform`

- **控制什麼：** `platform`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「穩定、明確的instance footprint或需要zonal capacity benefit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Reserved Instances鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `tenancy`

- **控制什麼：** `tenancy`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `term`

- **控制什麼：** `term`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「穩定、明確的instance footprint或需要zonal capacity benefit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Reserved Instances設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `payment`

- **控制什麼：** `payment`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「穩定、明確的instance footprint或需要zonal capacity benefit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Reserved Instances設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `offering class`

- **控制什麼：** `offering class`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

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

1. Savings Plans的責任：用一或三年每小時compute spend承諾換取折扣。
2. 底層機制：帳單把eligible usage套用承諾；Compute SP較彈性，EC2 Instance SP較限定。
3. 第一個要看的設定：Compute/EC2/SageMaker type、term、payment option、hourly commitment、sharing與coverage/utilization。
4. 選擇邏輯：穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。
5. 不要混淆：Reserved Instances的責任是「為特定EC2/RDS等使用承諾提供billing discount，某些EC2 zonal RI兼具capacity reservation。」；它不會自動取代Savings Plans。
6. 替換訊號：特定EC2屬性與容量保留需求比較RI/Capacity Reservation；可中斷工作用Spot。
7. 最常見錯法：將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。
8. 可移植原則：match pricing commitment to demand certainty。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Savings Plans | 用一或三年每小時compute spend承諾換取折扣。 | 帳單把eligible usage套用承諾；Compute SP較彈性，EC2 Instance SP較限定。 | 可預測baseline compute且希望跨family/Region較彈性。 | 特定EC2屬性與容量保留需求比較RI/Capacity Reservation；可中斷工作用Spot。 |
| Reserved Instances | 為特定EC2/RDS等使用承諾提供billing discount，某些EC2 zonal RI兼具capacity reservation。 | Billing依instance attributes匹配discount；Standard與Convertible交換彈性不同。 | 穩定、明確的instance footprint或需要zonal capacity benefit。 | 跨family/Region彈性通常Compute Savings Plans較佳；RI不會自動讓instance啟動。 |
| EC2 Spot Instances | 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。 | Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。 | batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。 | 不可中斷single point、stateful primary或無重試設計不能只用Spot。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Capacity Reservation解決容量保證，不自動等於billing discount。 | 只有當題目條件明確改變時才可能合理。 | 將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Capacity Reservation解決容量保證，不自動等於billing discount。」之間做選擇。
- 認得常考設定：Compute/EC2/SageMaker type、term、payment option、hourly commitment、sharing與coverage/utilization。
- 對應官方tasks：SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：特定EC2屬性與容量保留需求比較RI/Capacity Reservation；可中斷工作用Spot。
- 對應官方tasks：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAA｜依需求確定性分層使用 commitments、On-Demand 與 Spot

一個 analytics 平台有 40% 全年穩定 compute baseline、20% 無法預測的互動流量，以及 40% 可 checkpoint 且可延後的夜間 batch。哪兩項採購策略最合理？（選兩項）

A. 以保守的穩定 baseline 評估合適 Savings Plan／RI，保留不確定互動 burst 為 On-Demand
B. 依年度最高峰購買三年 commitment，確保每個小時都付相同峰值
C. 把 singleton metadata database 完全放在 Spot，且不做 replica 或 backup
D. 讓可重跑 batch 使用 diversified Spot capacity，實作 checkpoint/idempotency，必要時以 On-Demand 補位
E. 所有 workload 都用 On-Demand，因為穩定多年需求也不值得評估 discount

**答案：A、D**

- **A：** 正確。Commitment 應覆蓋有高度把握的每小時基線；不可預測 demand 保留彈性可降低浪費。
- **B：** 錯誤。依短期峰值承諾會在非峰值小時產生大量未使用 commitment。
- **C：** 錯誤。不可中斷的單點 state 不適合完全依賴可回收 Spot capacity。
- **D：** 正確。Batch 能 checkpoint、retry 與分散 pool，最能承受 Spot interruption。
- **E：** 錯誤。On-Demand 有彈性，但對穩定長期 baseline 不評估 commitments 可能錯失顯著節省。

**事實查證：** [What are Savings Plans?](https://docs.aws.amazon.com/savingsplans/latest/userguide/)、[Prepare for Spot Instance interruptions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/prepare-for-interruptions.html)、[EC2 Spot rebalance recommendations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/rebalance-recommendations.html)

### 練習題 2｜SAA｜Compute Savings Plans 的 flexibility 與非容量性質

公司預期未來一年會在 EC2 instance families、Regions、Fargate 與 Lambda 之間調整 compute，但能承諾固定每小時的合格 compute spend。哪個選項最符合？

A. 購買 On-Demand Capacity Reservation，因為它會自動折扣 Lambda 與 Fargate
B. 購買 EC2 Instance Savings Plan，因為它可跨所有 Regions 與 compute services
C. 評估 Compute Savings Plans；它提供較廣的合格 compute flexibility，但不保證 EC2 capacity，未使用的 hourly commitment 也不會累積到下一小時
D. 購買 Standard RI，因為 RI discount 可套用所有 AWS 服務

**答案：C**

- **A：** 錯誤。Capacity Reservation 解決特定 EC2 capacity 可用性，不是 Lambda/Fargate discount。
- **B：** 錯誤。EC2 Instance Savings Plans 的 family/Region commitment 較窄。
- **C：** 正確。Compute Savings Plans 適合跨多種合格 compute usage 的彈性需求；它是 billing commitment，不是 runtime capacity。
- **D：** 錯誤。EC2 RI billing benefit 有明確 matching scope，不涵蓋所有 AWS services。

**事實查證：** [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)、[How Savings Plans apply to usage](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-applying.html)、[What are Savings Plans?](https://docs.aws.amazon.com/savingsplans/latest/userguide/)

### 練習題 3｜SAA｜EC2 Instance Savings Plans 的 family／Region commitment

某 EC2 fleet 未來三年確定留在 us-east-1 的 m7i family，但 size、OS 與 tenancy 可能調整；團隊希望以較窄彈性換取較佳折扣潛力。應優先評估什麼？

A. Compute Savings Plans，因為越廣彈性一定永遠有最高折扣
B. EC2 Instance Savings Plans，並以穩定 family/Region 的合格用量評估 hourly commitment
C. Spot only，因為 family 穩定就代表 workload 可中斷
D. On-Demand Capacity Reservation，因為 reservation 本身就是長期 billing discount

**答案：B**

- **A：** 錯誤。Compute Savings Plans 更靈活，但題目明確接受較窄 family/Region boundary 以換取 discount。
- **B：** 正確。EC2 Instance Savings Plans 適合穩定 instance family 與 Region，仍需避免過度承諾。
- **C：** 錯誤。採購穩定性不等於應用程式具 interruption tolerance。
- **D：** 錯誤。Capacity Reservation 提供容量 assurance，本身不自動提供 billing discount。

**事實查證：** [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)、[Savings Plans purchase analysis](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-purchase-analysis.html)

### 練習題 4｜SAA → SAP｜區分 EC2 RI discount 與 Capacity Reservation

交易系統要求在 us-east-1a 一定能啟動 50 台指定 EC2 type，同時希望穩定用量取得折扣。哪個敘述最準確？

A. 任何 Regional RI 都會在所有 AZ 預留 50 台 capacity
B. Capacity Reservation 自動等同三年最高折扣，不需要 Savings Plan 或 RI
C. 購買 Regional RI 就能得到指定 AZ 容量；不需要 Zonal RI 或 On-Demand Capacity Reservation
D. 以 On-Demand Capacity Reservation 或符合條件的 Zonal RI 解決特定 AZ capacity；billing discount 另依 Savings Plan／RI matching 規則評估

**答案：D**

- **A：** 錯誤。Regional RI 主要提供 billing benefit，不建立特定 AZ capacity reservation。
- **B：** 錯誤。Capacity Reservation 與 discount 是可組合但不同的責任。
- **C：** 錯誤。Regional RI 提供區域層級折扣與 size flexibility（須符合規則），但不保留指定 AZ 容量；Zonal RI 或 ODCR 才承擔該 capacity 責任。
- **D：** 正確。先分開 capacity assurance 與 billing discount，才能避免把採購工具誤當 runtime guarantee。

**事實查證：** [How EC2 Reserved Instance discounts apply](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/apply_ri.html)、[Types of Amazon EC2 Reserved Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html)、[EC2 On-Demand Capacity Reservations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-reservations.html)

### 練習題 5｜SAP｜Standard 與 Convertible EC2 RIs 的 trade-off

公司有一批非常穩定、三年內不會換 family 的 legacy EC2；另一批可能在一年後因 license 改變而換 family。哪個決策原則正確？

A. 穩定 fleet 可評估 Standard RI；變動風險較高者評估 Convertible RI 的 exchange flexibility，並接受通常較低 discount
B. 所有 Standard RIs 都可隨時無條件換到任何 AWS service
C. Convertible RI 會自動把 running instances 重新部署到新 family
D. 兩種 RIs 都是 Spot capacity，因此可能隨時被中斷

**答案：A**

- **A：** 正確。Standard 偏向穩定 matching 與折扣，Convertible 以較低折扣換取符合 offering rules 的 exchange flexibility。
- **B：** 錯誤。Standard RI 不是任意交換產品；現行可修改項目只包括 Availability Zone、scope，以及同一 instance family 與 generation 內的 size，且受 platform、tenancy 與 instance size flexibility 限制，更不能跨到任何 AWS service。
- **C：** 錯誤。RI 是 billing instrument，不會修改或重新部署 runtime instances。
- **D：** 錯誤。RI 與 Spot 是不同 purchasing model；RI 不代表可回收 capacity。

**事實查證：** [How EC2 Reserved Instance discounts apply](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/apply_ri.html)、[Types of Amazon EC2 Reserved Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html)、[Modify Amazon EC2 Reserved Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-modifying.html)、[Exchange Convertible Reserved Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-convertible-exchange.html)

### 練習題 6｜SAP｜區分 commitment coverage 與 utilization

一個 organization 的 Savings Plans utilization 為 99%，但 coverage 只有 45%。這最可能表示什麼？

A. 99% eligible usage 已獲 discount，但買來的 commitment 大多未使用
B. Coverage 與 utilization 完全相同，數字不可能不同
C. 既有 commitment 幾乎都被消耗，但仍有大量 eligible usage 以非 Savings Plans 費率計費；是否加購仍要看穩定性與未來變更
D. Savings Plans 已預留 99% EC2 capacity

**答案：C**

- **A：** 錯誤。這把兩個定義顛倒；99% utilization 代表 purchased commitment 幾乎使用完。
- **B：** 錯誤。Coverage 看 usage 被 discount 覆蓋的比例，utilization 看 commitment 被消耗的比例。
- **C：** 正確。低 coverage/high utilization 可代表還有未覆蓋用量，但不能在不了解 durable baseline 時直接加購。
- **D：** 錯誤。Savings Plans 不提供 EC2 capacity reservation。

**事實查證：** [Savings Plans purchase analysis](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-purchase-analysis.html)、[How Savings Plans apply to usage](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-applying.html)

### 練習題 7｜SAP｜以 durable baseline 而非短期 peak 購買 commitment

公司剛完成一週大型活動，compute spend 是平時 5 倍；三個月後會把部分 EC2 遷移到 containers。財務希望立刻依這一週 peak 購買三年 commitment。架構師應怎麼做？

A. 依 peak 全買，因為未使用 commitment 可自動轉到下一年度
B. 使用代表性歷史、seasonality、rightsizing 與 migration forecast 推估保守 hourly baseline，再做 sensitivity analysis
C. 完全忽略所有穩定需求，只用 Spot
D. 先買 commitment，再決定 target architecture，因為 billing 不受服務遷移影響

**答案：B**

- **A：** 錯誤。Hourly commitment 未使用部分仍付費，不會累積成未來 credit。
- **B：** 正確。長期承諾必須扣除暫時 peak 與預期 architecture changes，並保留不確定性。
- **C：** 錯誤。穩定且不可中斷的基線仍適合評估 commitments；Spot 取決於 interruption tolerance。
- **D：** 錯誤。Eligible usage 與 flexibility 會隨 EC2、containers、serverless 遷移而改變。

**事實查證：** [Savings Plans purchase analysis](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-purchase-analysis.html)、[What are Savings Plans?](https://docs.aws.amazon.com/savingsplans/latest/userguide/)

### 練習題 8｜SAA｜建立可承受 Spot interruption 的 workload

基因分析 batch 要使用 Spot 降低成本，每個 job 需 6 小時。哪兩項設計能讓 interruption 不致丟失整個工作？（選兩項）

A. 所有 checkpoint 只存 instance store，instance 終止後再讀回
B. 只選當下最便宜的一個 instance type 和單一 AZ
C. 將進度定期寫到 durable store，讓重新領取 job 的 worker 可冪等續跑
D. 假設每次一定會收到且有足夠時間處理 interruption notice，否則不做 recovery
E. 使用多個相容 instance types/AZ capacity pools，處理 interruption/rebalance signals，並保留必要的非 Spot capacity

**答案：C、E**

- **A：** 錯誤。Instance store 隨 instance 終止而失去，不能作唯一 checkpoint。
- **B：** 錯誤。單一 pool 增加 capacity 與 interruption correlation 風險。
- **C：** 正確。Durable checkpoint 和 idempotency 讓 job 可在另一 worker 恢復。
- **D：** 錯誤。Notice/rebalance 是有用訊號，不是可用來承諾完整 recovery window 的保證。
- **E：** 正確。Diversification 和 fallback capacity 可提高取得 replacement capacity 的機率。

**事實查證：** [Prepare for Spot Instance interruptions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/prepare-for-interruptions.html)、[EC2 Spot rebalance recommendations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/rebalance-recommendations.html)

### 練習題 9｜SAP｜依 capacity resilience 選 Spot allocation

一個可水平分割的 Spot worker fleet 可使用 12 種 instance types 與 3 個 AZ。業務更重視工作穩定完成而非每秒追逐最低牌價。最適合的方向是什麼？

A. 把 max price 設很高，便可保證 Spot 永不中斷
B. 固定使用單一最大 instance type，減少 capacity pools
C. 永遠選 lowest-price 單一 pool，即使該 pool capacity 很少
D. 明確採用 `capacity-optimized` Spot allocation strategy，並讓多種相容 instance types 與三個 AZ 的 pools 都成為 eligible

**答案：D**

- **A：** 錯誤。價格設定不會消除 AWS 回收 capacity 的可能。
- **B：** 錯誤。單一 type/AZ 會集中 interruption 與 capacity shortage 風險。
- **C：** 錯誤。最低瞬時價格不代表最低 interruption 或 replacement risk。
- **D：** 正確。`capacity-optimized` 會從可用 Spot capacity 較深的 pools 配置；instance types 與 AZ 的多樣性負責擴大候選 pools，兩者不能混成不存在的策略名稱。

**事實查證：** [EC2 Spot rebalance recommendations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/rebalance-recommendations.html)、[Prepare for Spot Instance interruptions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/prepare-for-interruptions.html)、[EC2 Fleet allocation strategies](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-allocation-strategy.html)

### 練習題 10｜SAP｜跨帳號 commitment governance 與 exam-version boundary

大型 organization 準備集中購買 Savings Plans，同時市場上出現較新的 Savings Plans 產品類型。哪兩項治理做法最合理？（選兩項）

A. 指定 purchase owner、sharing/chargeback 原則，定期檢查 utilization、coverage、planned migrations 與 realized savings
B. 讓每個帳號獨立購買三年 peak commitment，不建立 inventory
C. 把 billing discount 當成可跨帳號搬移的 runtime capacity
D. 看到新產品名稱就假設它一定是 SAP-C02 scored topic，不核對 exam guide 或版本日期
E. 在書與題庫中分開標示 current service catalog 與 target exam blueprint；例如 Database Savings Plans 可列 current extension，但不冒充已確認的舊版考點

**答案：A、E**

- **A：** 正確。Long-lived commitments 需要組織級 ownership、allocation 與持續驗證，否則容易重複或過度購買。
- **B：** 錯誤。分散採購可能忽略 consolidated eligible usage，並缺少整體 utilization 視圖。
- **C：** 錯誤。Billing benefit 不是 EC2 capacity，也不能用 sharing 取代 runtime availability design。
- **D：** 錯誤。服務目錄會更新，認證內容必須依公布 exam guide 與考試版本校準。
- **E：** 正確。截至 2026-10-01，SAP-C03 尚無公開 exam guide/sample questions；註冊自 2026-10-27 開始，SAP-C02 可考到 2026-11-17。因此 Database Savings Plans 可作 current extension，但不能冒充已確認的 C02/C03 scored content。

**事實查證：** [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)、[Savings Plans purchase analysis](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-purchase-analysis.html)、[SAP-C02 Domain 1: Design for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)、[AWS Certified Solutions Architect – Professional exam transition](https://aws.amazon.com/certification/certified-solutions-architect-professional/)

## Follow-up Questions

### Q1. 為什麼本章不能只背「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留O…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Compute discount取決於使用承諾、instance彈性、中斷容忍與license。」，所以「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」能直接滿足它；若constraint改成「Capacity Reservation解決容量保證，不自動等於billing discount。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」。替代方案「Capacity Reservation解決容量保證，不自動等於billing discount。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Compute discount取決於使用承諾、instance彈性、中斷容忍與license。」，排除會導致「將不可中斷single worker全放Spot，或依短期峰值購買三年承諾。」的選項，再選「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」。本章對應的代表task包括：SAA-4.2 Design cost-optimized compute solutions；SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「穩定基線用Savings Plans/RI；可中斷且可checkpoint工作用Spot；burst保留On-Demand。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「match pricing commitment to demand certainty」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 69 章　Rightsizing 與 Compute Optimizer

過度配置浪費成本，過小配置則造成throttling與tail latency。

## 從故障發生的那一刻倒推：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：數百台instance平均CPU低，但月末有固定高峰且部分服務受memory限制。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：過度配置浪費成本，過小配置則造成throttling與tail latency。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Compute Optimizer，對照角色是Amazon CloudWatch。我們選擇「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：數百台instance平均CPU低，但月末有固定高峰且部分服務受memory限制。

正常production路徑
          ▼
[AWS Compute Optimizer] → 使用者可觀察的結果
          │ 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…
  · Amazon EC2：提供可控制OS、runtime、network與storage的虛擬機compute。

失敗時先找：只看平均CPU便縮小memory-bound instance，或忽略burstable credit。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問AWS Compute Optimizer有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Compute Optimizer和Amazon CloudWatch並不是兩個任意的產品名稱。前者適合本章，是因為「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」直接回應了眼前的問題；後者描述的「Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只看平均CPU便縮小memory-bound instance，或忽略burstable credit。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「rightsizing is a continuous measurement loop」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 |

## 把全圖套進一個具體案例

**場景：** 數百台instance平均CPU低，但月末有固定高峰且部分服務受memory限制。

1. 故事的起點：數百台instance平均CPU低，但月末有固定高峰且部分服務受memory限制。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Compute Optimizer負責「根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudWatch、Amazon EC2各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只看平均CPU便縮小memory-bound instance，或忽略burstable credit。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「建議不是自動安全變更；需load test、seasonality、license與SLO驗證。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Compute Optimizer

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：過度配置浪費成本，過小配置則造成throttling與tail latency。
- **具體例子／邊界：** 在「數百台instance平均CPU低，但月末有固定高峰且部分服務受memory限制。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudWatch

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只看平均CPU便縮小memory-bound instance，或忽略burstable credit。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：rightsizing is a continuous measurement loop。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### temporary credentials

具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Compute Optimizer

- **功用：** 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
- **底層機制：** 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。
- **關鍵設定：** opt-in、lookback、enhanced infrastructure metrics、external metrics ingestion與recommendation preferences。
- **選擇時機：** 找over/under-provisioned resources並建立rightsizing候選。
- **替換時機：** 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### Amazon EC2

- **功用：** 提供可控制OS、runtime、network與storage的虛擬機compute。
- **底層機制：** Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
- **關鍵設定：** instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- **選擇時機：** 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。
- **替換時機：** 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。

## 考前與實作時再查：設定操作手冊

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

## 讀到這裡，請用自己的話說一次

1. AWS Compute Optimizer的責任：根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
2. 底層機制：分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。
3. 第一個要看的設定：opt-in、lookback、enhanced infrastructure metrics、external metrics ingestion與recommendation preferences。
4. 選擇邏輯：以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。
5. 不要混淆：Amazon CloudWatch的責任是「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；它不會自動取代AWS Compute Optimizer。
6. 替換訊號：建議不是自動安全變更；需load test、seasonality、license與SLO驗證。
7. 最常見錯法：只看平均CPU便縮小memory-bound instance，或忽略burstable credit。
8. 可移植原則：rightsizing is a continuous measurement loop。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 | 找over/under-provisioned resources並建立rightsizing候選。 | 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 | 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。 | 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。 | 只有當題目條件明確改變時才可能合理。 | 只看平均CPU便縮小memory-bound instance，或忽略burstable credit。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。」之間做選擇。
- 認得常考設定：opt-in、lookback、enhanced infrastructure metrics、external metrics ingestion與recommendation preferences。
- 對應官方tasks：SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：建議不是自動安全變更；需load test、seasonality、license與SLO驗證。
- 對應官方tasks：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAA｜Rightsizing 是 price-performance optimization

一台 memory-intensive EC2 平均 CPU 只有 12%，但 memory 常達 92%，p99 latency 在月末接近 SLO。哪個 rightsizing 原則正確？

A. 立刻縮小兩個 sizes，因為 CPU 低於 20% 就一定 overprovisioned
B. 同時評估 CPU、memory、network、EBS、tail latency、availability 與 growth，選擇仍符合 SLO 的最低總成本配置
C. 永遠保留最大 size，因為任何 headroom 都不能被量化
D. 只比較每小時 list price，不考慮 fleet count 或 license

**答案：B**

- **A：** 錯誤。CPU 不是唯一 constraint；縮小可能先造成 memory pressure 或 I/O bottleneck。
- **B：** 正確。Rightsizing 的目標是符合 workload contract 的 price-performance，而非把某一 metric 壓到最高。
- **C：** 錯誤。Headroom 可由 peaks、seasonality、scale-out time 與 SLO 量化；無限預留會浪費。
- **D：** 錯誤。總成本還受數量、license、storage/network 與 scaling behavior 影響。

**事實查證：** [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

### 練習題 2｜SAA → SAP｜把 Compute Optimizer recommendation 當作候選而非保證

Compute Optimizer 建議把 production instance 從 r7i.4xlarge 改成較小規格，estimated savings 很高但 performance risk 不是 very low。團隊應如何處理？

A. 自動套用所有 recommendations，因為 AWS 已保證 application SLO
B. 忽略 under-provisioned 或不同 family 建議，因為 cost 可能增加
C. 只看 estimated monthly savings，不需檢查 software/license compatibility
D. 把建議視為候選，檢查 metrics/assumptions、business headroom、architecture compatibility，經 canary/load test 後再變更

**答案：D**

- **A：** 錯誤。Recommendation 是分析結果，不是 application-specific production guarantee。
- **B：** 錯誤。Optimization 也包含修正 underprovisioning；有時增加資源才能恢復 performance。
- **C：** 錯誤。License、architecture、storage/network limits 與 SLO 都會改變實際結果。
- **D：** 正確。Compute Optimizer 縮小候選空間，最終 acceptance 仍需 workload owners 與測試證據。

**事實查證：** [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)

### 練習題 3｜SAP｜為 EC2 rightsizing 提供 memory metrics

Compute Optimizer 對一批 EC2 沒有可靠 memory evidence，但服務已知可能 memory-bound。哪個補強最合理？

A. 透過 CloudWatch agent 發布支援的 guest memory metrics，或設定 Compute Optimizer 支援的 external metrics ingestion，並驗證 permissions/dimensions/history
B. 用 EC2 CPUUtilization 精準推算 RAM，因為兩者永遠成固定比例
C. 只安裝 agent，不授予 PutMetricData 或相關讀取權限
D. 假設 EC2 hypervisor 預設發布所有 guest OS memory 指標

**答案：A**

- **A：** 正確。Guest memory 不像 CPU 一樣由 EC2 預設完整提供；必須建立可信 telemetry path。
- **B：** 錯誤。CPU 與 memory demand 可獨立變化，不能互相精準推算。
- **C：** 錯誤。沒有 permissions 與正確 dimensions，資料不會被有效收集或關聯。
- **D：** 錯誤。EC2 default metrics 不含一般 guest memory utilization。

**事實查證：** [EC2 metrics analyzed by Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/ec2-metrics-analyzed.html)、[Compute Optimizer external metrics ingestion](https://docs.aws.amazon.com/compute-optimizer/latest/ug/external-metrics-ingestion.html)

### 練習題 4｜SAP｜為 seasonal workload 選 lookback 與 enhanced metrics

月末結算服務每 30 天有兩天 load 增加 8 倍。Compute Optimizer 的預設 14 天 lookback 剛好只涵蓋安靜期並建議大幅縮小。應怎麼做？

A. 直接縮小，因為預設 14 天永遠代表下一個月
B. 假設更長 lookback 能預知尚未發生的新產品 launch，因此不需 business forecast
C. 選擇涵蓋月末 peak 的觀測期間，必要時評估 enhanced infrastructure metrics，並把 future events 納入 owner review
D. 為 organization 每個 resource 無條件啟用所有付費功能，不做優先級

**答案：C**

- **A：** 錯誤。Quiet window 會漏掉已知週期 peak，造成 underprovisioning。
- **B：** 錯誤。Historical lookback 不能預測沒有歷史的新 event。
- **C：** 正確。預設 lookback 是 14 天；Enhanced Infrastructure Metrics 可延長到最多 93 天，足以涵蓋 30 天週期，但尚未發生的 launch 仍須加入 business forecast。
- **D：** 錯誤。付費分析應優先用在高價值或季節性 workload，並衡量效益。

**事實查證：** [Compute Optimizer enhanced infrastructure metrics](https://docs.aws.amazon.com/compute-optimizer/latest/ug/enhanced-infrastructure-metrics.html)、[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)

### 練習題 5｜SAA｜Bursty instance 的 CPU credits 與 rightsizing

T3 Unlimited instance 平均 CPU 25%，但每天尖峰後 CPUSurplusCreditsCharged 增加、p99 變差。哪個判斷最好？

A. 平均 CPU 低，所以應再縮小一半並忽略 credits
B. 檢查 CPUCreditBalance／surplus usage、尖峰 duration 與成本；若需求長期超過 baseline，評估較大 burstable 或非 burstable family
C. 把所有 requests 延後到 credit 恢復，但仍承諾相同 real-time SLO
D. CPU credits 只影響 EBS，不影響 processor

**答案：B**

- **A：** 錯誤。低日平均可掩蓋連續 peak 與 credit depletion，縮小會更快耗盡。
- **B：** 正確。Bursty economics 需同時看 credit、surplus charge 與 SLO，持續負載可能更適合固定 baseline。
- **C：** 錯誤。延後即時流量會改變使用者契約，除非 workload 本來可排程。
- **D：** 錯誤。Credits 控制 burstable CPU performance。

**事實查證：** [Monitor CPU credits for burstable instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-monitoring-cpu-credits.html)

### 練習題 6｜SAA｜Fleet rightsizing 與 Auto Scaling 的耦合

團隊把 Auto Scaling fleet 的 instance size 減半，但保留相同 min/max count、request-per-target target 與 warmup。結果 scale-out 更頻繁、queue age 上升，總 instance-hours 反而增加。哪個修正最合理？

A. 只比較單台 hourly price，fleet behavior 不屬於 rightsizing
B. 永久關閉 Auto Scaling，改用固定最小 fleet
C. 把 warmup 設成零，讓 scale-in 更快
D. 重新以單台 capacity 校準 min/max/desired、target metric、warmup 與 instance mix，並比較 fleet-level cost 和 SLO

**答案：D**

- **A：** 錯誤。較便宜單台可能需要更多台與更多 churn，總成本必須在 fleet 層比較。
- **B：** 錯誤。固定 fleet 可能失去 elasticity；問題是 policy 與新 capacity unit 未重新校準。
- **C：** 錯誤。零 warmup 會讓尚未真正貢獻吞吐量的新容量立即進入 aggregate metric，可能加劇 scale-in/scale-out 震盪；只有初始化確實近乎即時時才合理。
- **D：** 正確。Instance size 改變了每個 capacity unit 的能力，scaling contract 也必須同步重算。

**事實查證：** [EC2 Auto Scaling target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[EC2 Auto Scaling default instance warmup](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-default-instance-warmup.html)

### 練習題 7｜SAA｜Rightsizing 前檢查 EC2 network 與 EBS ceilings

某 instance CPU/memory 很低，但 NetworkOut 與 EBS throughput 在尖峰都接近該 instance type 上限。團隊想縮小 instance。哪兩項應先驗證？（選兩項）

A. 核對候選 instance 的 network bandwidth、packet rate、EBS bandwidth/IOPS 與 attached-volume limits
B. 假設同 family 所有 sizes 都有相同 network/EBS performance
C. 只確認 EBS volume provisioned IOPS；instance-side limit 永遠不會限制
D. 只在 idle 環境啟動一次，不需 representative load
E. 以代表性流量 benchmark 候選規格，觀察 throughput、queueing、latency 與 throttling

**答案：A、E**

- **A：** 正確。EC2 size 常有不同 I/O envelope；CPU fit 不代表 network/storage fit。
- **B：** 錯誤。Bandwidth 與 burst/baseline 可能隨 size 變化。
- **C：** 錯誤。End-to-end throughput 受 volume 與 instance 兩側共同限制。
- **D：** 錯誤。Idle startup 不會暴露尖峰 I/O bottleneck。
- **E：** 正確。Benchmark 可驗證文件 limits 在實際 block size、concurrency 與 traffic 下是否符合 SLO。

**事實查證：** [Amazon EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)、[Amazon EC2 instance network bandwidth](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html)、[EBS-optimized instance performance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)、[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)

### 練習題 8｜SAA｜用 scheduled scaling 應對可預測 peak

每月最後一天 09:00，報表服務會在 5 分鐘內從 20% 升到 95% CPU，動態 scaling 要 12 分鐘才能讓新 instances ready。最合理的 cost/performance 改善是什麼？

A. 全年維持月末 peak capacity，避免設定 scaling
B. 等 CPU 已到 95% 才 scale out，因為已知 peak 也不應預先動作
C. 用 scheduled scaling 在 peak 前預先增加 capacity，保留 target tracking 處理變動，完成後再安全 scale in
D. 在 09:01 先 scale in，降低活動期間成本

**答案：C**

- **A：** 錯誤。全年維持月末 peak 能降低啟動風險，卻會長期支付閒置容量；只有 peak 幾乎持續存在或預擴展不可靠時才可能合理。
- **B：** 錯誤。已知 load 到達後才啟動會因 12 分鐘 warmup 違反 SLO。
- **C：** 正確。Scheduled action 處理可預測基線變化，dynamic policy 處理實際偏差。
- **D：** 錯誤。已知 peak 開始後先 scale in 會提高 saturation 與排隊；只有實測證明工作量已提前結束並保留安全 headroom 時，縮容才合理。

**事實查證：** [Scheduled scaling for Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/schedule_time.html)、[EC2 Auto Scaling target tracking scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)

### 練習題 9｜SAP｜以 canary、SLO 與 rollback 驗證 rightsizing

團隊要把 400 台 production instances 換成較小新 family。哪兩項 rollout control 最重要？（選兩項）

A. 一次替換全部 instances，避免新舊配置重疊
B. 先對代表性 canary slice 使用新 launch template，測 steady/peak traffic 與故障情境
C. 只要 hourly price 下降，即使 p99 與 error rate 上升也接受
D. 比較 canary/control 的 latency percentiles、errors、saturation、queue/replica lag 與 cost，超過 gate 時回復前一 launch template
E. 變更開始前刪除舊 launch template，避免 rollback

**答案：B、D**

- **A：** 錯誤。Big-bang 擴大 blast radius，也失去同時對照 cohort。
- **B：** 正確。Canary 讓真實 compatibility/performance 先在有限範圍暴露。
- **C：** 錯誤。Rightsizing 不能以破壞 SLO 換 headline savings。
- **D：** 正確。預定 acceptance/rollback evidence 讓 cost 與使用者結果一起決策。
- **E：** 錯誤。保留已知良好 template 是快速 rollback 的核心。

**事實查證：** [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)

### 練習題 10｜SAP｜跨 organization 排序並驗證 optimization opportunities

Cost Optimization Hub 顯示 2,000 個機會，部分與 Compute Optimizer 重疊。哪兩項治理方式最好？（選兩項）

A. 依 owner、estimated savings、effort、risk、recommendation age 與 workload criticality 排序，去除重疊建議
B. 只按最大 headline savings 自動執行，忽略 owner 與 business context
C. 把 recommendation accepted 當作 realized savings，不追蹤實際 bill
D. 先處理所有 untagged resources，不確認它們屬於誰
E. 變更後以成本、SLO 與資源使用量驗證 realized outcome，未實現節省時找出 commitment、usage 或遷移偏差

**答案：A、E**

- **A：** 正確。排序必須同時考慮價值、風險與可執行 ownership，避免兩個服務重複計算同一機會。
- **B：** 錯誤。Headline savings 是估計，沒有 owner/context 可能破壞 production。
- **C：** 錯誤。接受動作不是財務結果；需查看實際 usage 和 bill。
- **D：** 錯誤。先辨識 owner 與 workload contract，才能安全調整。
- **E：** 正確。Optimization 是 closed loop；只有 after-state 證據才能確認 savings 與 SLO。

**事實查證：** [AWS Cost Optimization Hub](https://docs.aws.amazon.com/cost-management/latest/userguide/cost-optimization-hub.html)、[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合auto…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「過度配置浪費成本，過小配置則造成throttling與tail latency。」，所以「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」能直接滿足它；若constraint改成「Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」。替代方案「Compute Optimizer提供建議，但仍需理解seasonality、license與business headroom。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只看平均CPU便縮小memory-bound instance，或忽略burstable credit。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「過度配置浪費成本，過小配置則造成throttling與tail latency。」，排除會導致「只看平均CPU便縮小memory-bound instance，或忽略burstable credit。」的選項，再選「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」。本章對應的代表task包括：SAA-4.2 Design cost-optimized compute solutions；SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以長期CPU、memory、network、EBS與p95/p99資料rightsizing，配合autoscaling與load test。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「rightsizing is a continuous measurement loop」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 70 章　Storage 與 Database Cost Optimization

儲存成本包含容量、request、IOPS、retrieval、replica與資料搬移。

## 從故障發生的那一刻倒推：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：資料湖容量便宜但每次query掃全量；DynamoDB長期穩定且on-demand帳單快速增加。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：儲存成本包含容量、request、IOPS、retrieval、replica與資料搬移。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon S3 Lifecycle如何接手工作，再看Amazon DynamoDB何時更合適，最後用設定與考題驗證「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：資料湖容量便宜但每次query掃全量；DynamoDB長期穩定且on-demand帳單快速增加。

正常production路徑
          ▼
[Amazon S3 Lifecycle] → 使用者可觀察的結果
          │ 依object age、prefix/tag與version狀態自動transition或expire資料。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon DynamoDB：提供managed key-value/document database與單位毫秒scale。
  · Amazon RDS：代管關聯式database engine的provisioning、patch、backup與failov…
  · AWS Cost Explorer：互動分析歷史與預測成本、usage與RI/SP coverage。

失敗時先找：只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問Amazon S3 Lifecycle有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3 Lifecycle和Amazon DynamoDB並不是兩個任意的產品名稱。前者適合本章，是因為「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」直接回應了眼前的問題；後者描述的「Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「optimize total cost per business operation」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 Lifecycle | 依object age、prefix/tag與version狀態自動transition或expire資料。 | S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 |

## 把全圖套進一個具體案例

**場景：** 資料湖容量便宜但每次query掃全量；DynamoDB長期穩定且on-demand帳單快速增加。

1. 故事的起點：資料湖容量便宜但每次query掃全量；DynamoDB長期穩定且on-demand帳單快速增加。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3 Lifecycle負責「依object age、prefix/tag與version狀態自動transition或expire資料。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon DynamoDB、Amazon RDS、AWS Cost Explorer各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon S3 Lifecycle

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：儲存成本包含容量、request、IOPS、retrieval、replica與資料搬移。
- **具體例子／邊界：** 在「資料湖容量便宜但每次query掃全量；DynamoDB長期穩定且on-demand帳單快速增加。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon DynamoDB

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：optimize total cost per business operation。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### IOPS

每秒可完成的I/O operations數，偏向小型random reads/writes能力。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon S3 Lifecycle

- **功用：** 依object age、prefix/tag與version狀態自動transition或expire資料。
- **底層機制：** S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。
- **關鍵設定：** Filter、Transitions、Expiration、NoncurrentVersionTransitions、AbortIncompleteMultipartUpload與status。
- **選擇時機：** 存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。
- **替換時機：** 存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

### Amazon RDS

- **功用：** 代管關聯式database engine的provisioning、patch、backup與failover。
- **底層機制：** DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
- **關鍵設定：** engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- **選擇時機：** 需要SQL transaction、joins、schema與managed operations。
- **替換時機：** 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。

### AWS Cost Explorer

- **功用：** 互動分析歷史與預測成本、usage與RI/SP coverage。
- **底層機制：** Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。
- **關鍵設定：** date/granularity、filters/group by、cost metric、forecast、RI/SP reports與cost allocation tags。
- **選擇時機：** 回答成本趨勢、來源、forecast與commitment coverage。
- **替換時機：** 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。

## 考前與實作時再查：設定操作手冊

### Amazon S3 Lifecycle：逐項設定說明

#### `Filter`

- **控制什麼：** `Filter`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3 Lifecycle以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `Transitions`

- **控制什麼：** `Transitions`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `Expiration`

- **控制什麼：** `Expiration`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `NoncurrentVersionTransitions`

- **控制什麼：** `NoncurrentVersionTransitions`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `AbortIncompleteMultipartUpload`

- **控制什麼：** `AbortIncompleteMultipartUpload`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `status`

- **控制什麼：** `status`指定Amazon S3 Lifecycle的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

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

## 讀到這裡，請用自己的話說一次

1. Amazon S3 Lifecycle的責任：依object age、prefix/tag與version狀態自動transition或expire資料。
2. 底層機制：S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。
3. 第一個要看的設定：Filter、Transitions、Expiration、NoncurrentVersionTransitions、AbortIncompleteMultipartUpload與status。
4. 選擇邏輯：利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。
5. 不要混淆：Amazon DynamoDB的責任是「提供managed key-value/document database與單位毫秒scale。」；它不會自動取代Amazon S3 Lifecycle。
6. 替換訊號：存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。
7. 最常見錯法：只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。
8. 可移植原則：optimize total cost per business operation。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 Lifecycle | 依object age、prefix/tag與version狀態自動transition或expire資料。 | S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。 | 存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。 | 存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 | 需要SQL transaction、joins、schema與managed operations。 | 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。 |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 | 回答成本趨勢、來源、forecast與commitment coverage。 | 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。 | 只有當題目條件明確改變時才可能合理。 | 只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。」之間做選擇。
- 認得常考設定：Filter、Transitions、Expiration、NoncurrentVersionTransitions、AbortIncompleteMultipartUpload與status。
- 對應官方tasks：SAA-4.1 Design cost-optimized storage solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。
- 對應官方tasks：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAP｜計算每次成功 business operation 的 total cost

團隊比較兩個文件查詢架構，只看 S3 每 GB 月費，忽略 requests、Athena scan、retrieval、replicas、backup 與營運成本。哪個評估方法正確？

A. 只選每 GB 最便宜 storage class，因為其他費用都固定
B. 刪除 backups 後再比較，避免 recovery cost 干擾
C. 以每次成功查詢／交易為單位計入 storage、requests、I/O、compute scan、retrieval、transfer、copies 與操作成本，同時保留 latency/durability/RTO/RPO
D. 只比較服務首頁的起始價格，不用 workload access pattern

**答案：C**

- **A：** 錯誤。低 storage 單價可能搭配高 retrieval、request 或 scan cost。
- **B：** 錯誤。Backup 是 workload recovery contract 的一部分，不能為了算便宜而移除。
- **C：** 正確。Unit economics 必須綁定成功 business outcome 與必要非功能需求。
- **D：** 錯誤。實際成本由 object size、frequency、query layout、IO 與 retention 決定。

**事實查證：** [AWS Cost Optimization Hub](https://docs.aws.amazon.com/cost-management/latest/userguide/cost-optimization-hub.html)、[SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)

### 練習題 2｜SAA｜依 access evidence 設計 S3 Lifecycle

合規文件建立後 30 天內常被存取，31–365 天每月可能讀一次，之後需保留七年且可接受小時級 restore。哪個做法最好？

A. 依 object age/size、retrieval latency、minimum duration/charges 與 resilience 要求建立 Lifecycle transitions，並分開處理 current 與 noncurrent versions
B. 建立後立即全部移到 Deep Archive，並承諾毫秒級讀取
C. 只 expire current versions，假設 versioned bucket 的 noncurrent versions 也自動消失
D. 全部永遠放 Standard，因為 Lifecycle 不能套用 prefix 或 tags

**答案：A**

- **A：** 正確。Lifecycle 應反映真實 age/access 與 restore requirement，versioned objects 需明確管理兩種版本。
- **B：** 錯誤。Deep archival tiers 有 restore latency 與 minimum-duration/retrieval economics，不適合前 30 天高頻讀。
- **C：** 錯誤。Current 與 noncurrent lifecycle actions 分開設定，不能假設一起刪除。
- **D：** 錯誤。Lifecycle rules 可用 filters 限定 objects，且能執行 transition/expiration。

**事實查證：** [S3 Lifecycle transition considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)、[SAA-C03 Domain 4: Design Cost-Optimized Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain4.html)

### 練習題 3｜SAP｜S3 小物件 Lifecycle 的現行預設與 economics

Bucket 每天產生一億個 20 KB objects。團隊假設 current S3 Lifecycle 預設會把所有小物件自動 transition 到任意 colder class，且一定省錢。哪個修正最準確？

A. 正確；object size 不影響 request、monitoring 或 minimum billable economics
B. 只要把 objects 切得更小，所有 storage classes 都更便宜
C. 直接強制 transition，不需要估算 request 次數或保存時間
D. 2024 年 9 月起新建或修改的 Lifecycle configuration 預設不 transition 小於 128 KB 的 objects；舊 configuration 在規則被修改前保留舊行為，且可用 size filter／API header 覆寫，但仍須先算完整成本

**答案：D**

- **A：** 錯誤。大量 tiny objects 的 request/monitoring 與 minimum object-size economics 可能主導成本。
- **B：** 錯誤。更多小 objects 通常增加 object count 與 requests，不保證更省。
- **C：** 錯誤。Override 技術可行不代表經濟合理，且不同 target class 有不同條件。
- **D：** 正確。小物件預設有 2024 年 9 月的相容性邊界；修改舊規則可能改變行為，明確 size filter 或 `x-amz-transition-default-minimum-object-size` 可控制預設，但技術可行仍不代表經濟合理。

**事實查證：** [S3 Lifecycle transition considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)

### 練習題 4｜SAA｜S3 Intelligent-Tiering 的適用情境與 archive opt-in

一批 5 MB research objects 將保存多年，但團隊無法預測哪些會反覆被讀，且 active tiers 要毫秒存取；若多年未讀可接受手動 restore。哪個選擇合理？

A. 全部使用 One Zone class，即使 durability/resilience requirement 不允許單 AZ
B. 評估 S3 Intelligent-Tiering，計入 monitoring/automation；若可接受 restore latency，再選擇性啟用 archive access tiers
C. 把 Intelligent-Tiering 當成 backup，刪除其他 recovery controls
D. 使用短期 tiny-object workload，並忽略 per-object monitoring economics

**答案：B**

- **A：** 錯誤。Storage class 也要符合 resilience requirement，不應只因便宜選單 AZ。
- **B：** 正確。Access pattern 未知且長期保存是適合情境，optional archive tiers 需由 restore latency 決定。
- **C：** 錯誤。Tiering 是 storage cost/access automation，不是獨立 backup lifecycle。
- **D：** 錯誤。短命小物件可能由 monitoring/object economics 主導，應另行分析。

**事實查證：** [S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)

### 練習題 5｜SAA｜用 partition、compression 與 columnar format 降低 Athena scan

Athena 每次只查某一天、某 Region 的兩個欄位，但資料以未壓縮 JSON 混在少數年度大檔中。哪個改造最直接降低 bytes scanned？

A. 只把舊 objects 用 S3 Lifecycle 移到較冷 storage class
B. 把每一 row 拆成 1 KB 獨立 JSON object，增加 object count
C. 依常用 selective dimensions（如 date/region）partition，壓縮並轉成 Parquet/ORC，只讀需要 columns/partitions
D. 為 S3 objects 建立 DynamoDB GSI，Athena 便不會掃資料

**答案：C**

- **A：** 錯誤。Lifecycle 改變 storage class，不會自動改變 query 要讀的資料格式與範圍。
- **B：** 錯誤。Tiny files 增加 metadata/request overhead，也沒有 column pruning。
- **C：** 正確。Partition pruning、compression 與 columnar layout 共同降低實際 scanned data。
- **D：** 錯誤。DynamoDB index 不會替 Athena 自動索引 S3 object contents。

**事實查證：** [Use columnar storage formats with Athena](https://docs.aws.amazon.com/athena/latest/ug/columnar-storage.html)

### 練習題 6｜SAA｜依 EBS IOPS／throughput／durability 選 gp3 或 io2

一般 web database 需要 6,000 IOPS、250 MiB/s 且希望容量與 performance 可獨立調整，實測不需最高等級 provisioned-IOPS durability。應先評估哪個 volume？

A. Gp3，依需求獨立配置 size、IOPS 與 throughput，並確認 EC2 instance-side EBS limit
B. St1，因為 throughput HDD 最適合 latency-sensitive random OLTP
C. 只增加 gp2 size，因為 gp3 performance 不能獨立設定
D. Provision 100,000 IOPS 的 volume，即使 instance 最多只能交付遠低於此數值

**答案：A**

- **A：** 正確。Gp3 將容量與 IOPS/throughput 解耦，常適合一般 SSD workload；end-to-end 仍受 instance limit。
- **B：** 錯誤。St1 適合大型 sequential throughput，不適合高頻 random latency-sensitive OLTP。
- **C：** 錯誤。Gp3 正是允許獨立配置 performance 的 SSD 類型。
- **D：** 錯誤。Volume 與 instance 中較低的上限會成為 bottleneck，超配只增加成本。

**事實查證：** [Amazon EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)

### 練習題 7｜SAA｜DynamoDB on-demand 與 provisioned capacity 選擇

新產品 traffic 未知且可能突然成長 20 倍，團隊暫時無可靠 forecast，希望先降低 capacity management。哪個 DynamoDB mode 最合理？

A. Provisioned capacity 固定成預估平均值，任何 spike 都靠 retry
B. 選擇 on-demand，因為它保證任何 hot partition 與任意瞬間 jump 都不會 throttle
C. 只增加 GSI，capacity mode 便不重要
D. 先使用 on-demand，但在已知 20 倍 launch 前逐步 ramp／預熱以提高 previous peak；取得穩定歷史後再比較 provisioned auto scaling 或 reserved capacity 的成本

**答案：D**

- **A：** 錯誤。未知 20 倍 burst 用平均 provisioned capacity 可能很快 throttle。
- **B：** 錯誤。On-demand 簡化 capacity，但仍有 partition/key design 與 scaling behavior，不能保證任意模式無 throttle。
- **C：** 錯誤。GSI 會增加另一組容量與 storage 成本，不能取代 mode 選擇。
- **D：** 正確。On-demand 適合不可預測 demand；其即時擴展準則是可承接前次峰值兩倍，若在約 30 分鐘內突然跳到更高（本題 20 倍），仍可能 throttling。已知 launch 應逐步 ramp 或預先把 previous peak 提高。

**事實查證：** [Evaluate a DynamoDB table capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CostOptimization_TableCapacityMode.html)、[DynamoDB on-demand capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html)

### 練習題 8｜SAA｜以 access pattern 與 partition key 降低 DynamoDB 成本

DynamoDB table 使用固定 partition key `GLOBAL`，大量 Scan 且有三個從未查詢的 GSIs。哪兩項改造最可能同時改善 performance 與成本？（選兩項）

A. 再加更多 GSIs，為每個欄位建立索引
B. 依 access patterns 設計高 cardinality、能分散流量的 partition keys，必要時使用 write sharding
C. 只切換 on-demand，hot key 與 Scan 便自動消失
D. 保留所有 unused GSIs，因為 index 不會產生 storage/write cost
E. 以 Query 和適當 key/index 取代 broad Scan，刪除未使用 GSIs 並控制 projection/item size/consistency

**答案：B、E**

- **A：** 錯誤。每個 GSI 都有 storage 與 write capacity implications，無需求的 index 只增加成本。
- **B：** 正確。分散 key 可避免單 partition 熱點並讓容量被有效利用。
- **C：** 錯誤。Capacity mode 不會修正單一 hot key 或不必要 Scan。
- **D：** 錯誤。Unused GSI 仍保存 projected data 並處理 writes。
- **E：** 正確。Access-pattern driven Query 與精簡 indexes 可降低讀寫與儲存浪費。

**事實查證：** [DynamoDB partition key design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)、[Global secondary indexes in DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)、[Evaluate a DynamoDB table capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CostOptimization_TableCapacityMode.html)

### 練習題 9｜SAP｜把 backup、replicas 與 idle storage 納入 database TCO

RDS instance 本身 rightsized，但 database 帳單仍高。哪兩項調查最可能找到被忽略的 TCO？（選兩項）

A. 盤點 retention 以外的 retained automated backups、manual snapshots、cross-Region copies 與未使用 read replicas
B. 刪除所有超過一天的 backups，不檢查 compliance 或 RPO
C. 假設 read replica 和 cross-Region transfer 都免費
D. 檢查 overprovisioned storage/IOPS、idle dev instances 與 snapshots，並在刪除前驗證 owner、restore 與 retention requirement
E. 只看 primary instance hourly rate，不需標籤或 cost allocation

**答案：A、D**

- **A：** 正確。Detached recovery artifacts、replicas 與 copies 可能長期累積成本。
- **B：** 錯誤。任意縮短 retention 可能破壞 compliance 與 RPO/PITR。
- **C：** 錯誤。Replicas 消耗 compute/storage，cross-Region paths 也需依 pricing 計入。
- **D：** 正確。Rightsizing 必須涵蓋 storage/performance 與生命週期，並保留 recovery contract。
- **E：** 錯誤。沒有 owner/cost dimensions 難以安全處理與驗證 realized savings。

**事實查證：** [RDS backup retention and storage cost](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.Retaining.html)、[Amazon RDS pricing](https://aws.amazon.com/rds/pricing/)、[Working with Amazon RDS read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)、[Amazon RDS DB instance storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html)、[REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)

### 練習題 10｜SAP｜驗證 storage/database optimization 的真實效果

團隊把 S3 objects transition、Athena 資料轉 Parquet，並調整 DynamoDB capacity。哪兩項 after-state evidence 最重要？（選兩項）

A. 只用工具估計的 forecast savings，無需等待實際 usage
B. 忽略 transition、retrieval 與重寫資料的一次性費用
C. 比較 tagged owner 的實際 cost、request/scan/retrieval/consumed-capacity 與每次成功 operation 成本
D. 只確認 IaC deployment 成功，因為性能與 recovery 會自動正確
E. 驗證 latency、throttles、data correctness、retention 與 restore path，並把 one-time charges 和 seasonality 納入期間比較

**答案：C、E**

- **A：** 錯誤。Forecast 是候選價值，不能替代 realized bill。
- **B：** 錯誤。第一個 billing period 可能被 transition/retrieval/rewrite 費用扭曲。
- **C：** 正確。這些 usage drivers 能說明 savings 來自何處且是否符合 workload economics。
- **D：** 錯誤。Control-plane success 不證明 query、database 或 restore 行為。
- **E：** 正確。Cost change 不能破壞 SLO、correctness 或 recovery；期間也需足以涵蓋代表性 traffic。

**事實查證：** [AWS Cost Optimization Hub](https://docs.aws.amazon.com/cost-management/latest/userguide/cost-optimization-hub.html)、[CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「利用lifecycle、compression、right storage class、gp3與datab…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「儲存成本包含容量、request、IOPS、retrieval、replica與資料搬移。」，所以「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」能直接滿足它；若constraint改成「Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」。替代方案「Serverless/on-demand降低閒置，但高且穩定負載可能provisioned更省。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「儲存成本包含容量、request、IOPS、retrieval、replica與資料搬移。」，排除會導致「只比較每GB單價，忽略Athena掃描、Glacier取回、DynamoDB hot access與backup。」的選項，再選「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」。本章對應的代表task包括：SAA-4.1 Design cost-optimized storage solutions；SAA-4.3 Design cost-optimized database solutions；SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「利用lifecycle、compression、right storage class、gp3與database consolidation/read pattern改善。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「optimize total cost per business operation」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 71 章　Data Transfer、NAT 與跨 AZ 成本

網路費用常由架構流向而非instance價格主導。

## 從故障發生的那一刻倒推：先從故事開始

把鏡頭拉到一個真實的production現場：每月PB級S3流量經NAT，微服務也大量跨AZ聊天。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：網路費用常由架構流向而非instance價格主導。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。NAT Gateway是這一章的入口，AWS Transit Gateway用來畫出邊界；主要方向「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：每月PB級S3流量經NAT，微服務也大量跨AZ聊天。

正常production路徑
          ▼
[NAT Gateway] → 使用者可觀察的結果
          │ 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · AWS Transit Gateway：以regional hub連接大量VPC、VPN與Direct Connect。
  · Amazon CloudFront：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
  · VPC endpoints：讓VPC私下存取AWS服務，不經IGW或NAT。

失敗時先找：Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「從故障發生的那一刻倒推」。先不要急著問NAT Gateway有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，NAT Gateway和AWS Transit Gateway並不是兩個任意的產品名稱。前者適合本章，是因為「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」直接回應了眼前的問題；後者描述的「集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「cost follows bytes through every hop」。更白話地說：用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| NAT Gateway | 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。 | 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| VPC endpoints | 讓VPC私下存取AWS服務，不經IGW或NAT。 | Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。 |

## 把全圖套進一個具體案例

**場景：** 每月PB級S3流量經NAT，微服務也大量跨AZ聊天。

1. 故事的起點：每月PB級S3流量經NAT，微服務也大量跨AZ聊天。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：NAT Gateway負責「讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Transit Gateway、Amazon CloudFront、VPC endpoints各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### NAT Gateway

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：網路費用常由架構流向而非instance價格主導。
- **具體例子／邊界：** 在「每月PB級S3流量經NAT，微服務也大量跨AZ聊天。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Transit Gateway

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：cost follows bytes through every hop。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transitive routing

A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### origin

CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

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

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### NAT Gateway

- **功用：** 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
- **底層機制：** 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。
- **關鍵設定：** public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
- **選擇時機：** private workload必須下載更新或呼叫無private endpoint的public API時。
- **替換時機：** S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。

### AWS Transit Gateway

- **功用：** 以regional hub連接大量VPC、VPN與Direct Connect。
- **底層機制：** Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。
- **關鍵設定：** attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
- **選擇時機：** 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。
- **替換時機：** 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。

### Amazon CloudFront

- **功用：** 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
- **底層機制：** DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
- **關鍵設定：** origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- **選擇時機：** 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。
- **替換時機：** 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。

### VPC endpoints

- **功用：** 讓VPC私下存取AWS服務，不經IGW或NAT。
- **底層機制：** Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。
- **關鍵設定：** service name、endpoint type、subnets、security groups、private DNS、route tables與endpoint policy。
- **選擇時機：** 要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。
- **替換時機：** VPC間完整雙向routing選Peering/TGW；只發布特定服務選PrivateLink。

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

## 讀到這裡，請用自己的話說一次

1. NAT Gateway的責任：讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
2. 底層機制：在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。
3. 第一個要看的設定：public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
4. 選擇邏輯：畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。
5. 不要混淆：AWS Transit Gateway的責任是「以regional hub連接大量VPC、VPN與Direct Connect。」；它不會自動取代NAT Gateway。
6. 替換訊號：S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。
7. 最常見錯法：Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。
8. 可移植原則：cost follows bytes through every hop。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| NAT Gateway | 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。 | 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 | private workload必須下載更新或呼叫無private endpoint的public API時。 | S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 | 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。 | 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| VPC endpoints | 讓VPC私下存取AWS服務，不經IGW或NAT。 | Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。 | 要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。 | VPC間完整雙向routing選Peering/TGW；只發布特定服務選PrivateLink。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。 | 只有當題目條件明確改變時才可能合理。 | Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。」之間做選擇。
- 認得常考設定：public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
- 對應官方tasks：SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAP｜逐 hop 建立 network cost model

一筆 1 GB payload 從 private EC2 經跨 AZ Transit Gateway、集中式 firewall、NAT Gateway 到 Internet，response 又沿 stateful path 返回。團隊只計一次 NAT data processing。第一個正確動作是什麼？

A. 只比較 EC2 instance price，因為 VPC 內所有流量免費
B. 畫出正反向 source/destination AZ、TGW、inspection、NAT、Internet/Region 邊界與每段 bytes，再套用現行各服務 pricing
C. 假設一個 logical request 永遠只產生一項 network charge
D. 只看 NAT hourly charge，不需看 data volume

**答案：B**

- **A：** 錯誤。跨 AZ、TGW、inspection、NAT 與 data transfer 可能各有處理／傳輸費。
- **B：** 正確。Network cost 跟隨 bytes 經過的實體/邏輯 hops；雙向與 retries 都要納入。
- **C：** 錯誤。同一 payload 可先後產生 TGW、Network Firewall、NAT、跨 AZ 與 data-transfer 費用；只有路徑完全不經任何計費 hop 時，logical request 才可能接近單一項目。
- **D：** 錯誤。高流量架構常由 per-GB processing/transfer 而非固定小時費主導。

**事實查證：** [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)、[AWS Transit Gateway pricing](https://aws.amazon.com/transit-gateway/pricing/)、[AWS Network Firewall pricing](https://aws.amazon.com/network-firewall/pricing/)、[NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)

### 練習題 2｜SAA｜用 S3 gateway endpoint 避免 private S3 traffic 經 NAT

同 Region private subnets 每月透過 NAT Gateway 讀取 PB 級 S3 data。團隊要降低 NAT data processing 且不讓 instances 取得 public IP。哪個設計最合適？

A. 保留 `0.0.0.0/0 -> NAT` 作為唯一 S3 path，只把 NAT instance size 加大
B. 建立 interface endpoint 但只放在另一 Region，假設所有 S3 traffic 會自動使用
C. 在 gateway endpoint 上設定 security group，因為 gateway endpoints 必須綁 ENI
D. 建立 S3 gateway endpoint，關聯需要的 private route tables 與 endpoint policy，並保留 IAM/bucket policy 的資料存取授權

**答案：D**

- **A：** 錯誤。這仍讓 PB 級 S3 bytes 經 NAT processing path。
- **B：** 錯誤。Endpoint scope、DNS 與 Region 必須符合 service path；另一 Region 不會自動接管。
- **C：** 錯誤。Gateway endpoint 透過 route-table prefix list path，不建立具有 security group 的 endpoint ENIs。
- **D：** 正確。S3 gateway endpoint 可讓 in-Region VPC traffic 走 endpoint route；network path 與 object authorization 仍是兩層責任。

**事實查證：** [Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)、[NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)

### 練習題 3｜SAP｜Interface endpoint 與 NAT 的功能／成本比較

50 個 VPC 每月只呼叫少量 AWS service APIs。團隊提議每個 VPC、每個 AZ 都建立 interface endpoints，聲稱一定比 NAT 便宜。哪兩項評估正確？（選兩項）

A. 比較 endpoint ENI hourly/data processing、AZ 數與 traffic volume，對照 NAT hourly/data processing 及可能的 cross-AZ path
B. Interface endpoint 對任何 traffic volume 都一定最便宜，因此不用計算
C. S3 gateway endpoint 可取代所有 AWS services 的 interface endpoints
D. 只建立單一 AZ endpoint，並忽略其他 AZ 到該 ENI 的 availability/cost path
E. 確認該 service/Region 支援、private DNS、endpoint policy、security groups 與 application DNS 行為

**答案：A、E**

- **A：** 正確。低流量、多 VPC/AZ 時固定 endpoint cost 可能主導；高流量 NAT processing 則可能主導，需算 break-even。
- **B：** 錯誤。Interface endpoint 有每 AZ endpoint-hour 與 data processing，NAT 也有 gateway-hour 與 processing；低流量、多 VPC/AZ 時固定 endpoint 成本可能更高，必須計算 break-even。
- **C：** 錯誤。Gateway endpoint 只支援特定 services，不能泛化到所有 API。
- **D：** 錯誤。單 AZ endpoint 可能形成 cross-AZ path 與故障邊界，必須明確接受或改善。
- **E：** 正確。功能適配和 DNS/policy/security 是選型前提，不能只看價格。

**事實查證：** [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)、[NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)、[Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)、[Configure an interface VPC endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)

### 練習題 4｜SAA｜設計 zonal NAT 的 local-AZ route

應用分布在三個 AZ，但所有 private subnets 都把 Internet egress 路由到 us-east-1a 的一個 zonal public NAT Gateway。團隊要求失去任一 AZ 時 egress 仍可用並減少不必要跨 AZ bytes。哪個傳統 zonal 設計最符合？

A. 把 NAT Gateway 放到 private subnet，且不給它到 IGW 的 route
B. 保持單一 NAT；cross-zone load balancing 會自動修改 subnet route tables
C. 在每個所需 AZ 建立 public NAT Gateway，讓各 private subnet route 到同 AZ NAT，並分別監控與測試 failover
D. 只在 route table 加上 `0.0.0.0/0 -> IGW`，但不讓 instances 取得 public IPv4／Elastic IP

**答案：C**

- **A：** 錯誤。Public NAT 需要位於有 IGW route 的 public subnet，才能提供 Internet egress。
- **B：** 錯誤。Load balancer cross-zone 不控制 route table 的 NAT next hop。
- **C：** 正確。Local-AZ NAT path 可避免單一 AZ dependency 與一般不必要跨 AZ hop，代價是多個 hourly gateways。
- **D：** 錯誤。IGW route 是必要但不足條件；instance 還需要 public IPv4／Elastic IP，且 security controls 必須允許。這也沒有解決 private-subnet 同 AZ NAT 的 resilience 需求。

**事實查證：** [NAT gateway connectivity types](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)、[NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)

### 練習題 5｜SAA｜區分 public 與 private NAT Gateways

團隊同時設計 Internet egress 與跨私有網路 address translation，卻把兩種 NAT Gateway 混為一談。哪個敘述正確描述 public 與 private NAT Gateway？

A. Private NAT 只要綁 EIP 就能透過 IGW 上 Internet
B. Public NAT 使用 Elastic IP 並透過 IGW 提供 outbound Internet path；private NAT 用 private IP 連接 private networks，不能經 IGW 提供 Internet egress
C. Public NAT 接受 Internet 主動建立到 private instances 的任意 inbound connections
D. 兩者都是具 application-layer allow/deny rules 的 managed firewall

**答案：B**

- **A：** 錯誤。Private NAT 不使用 EIP 作 Internet egress；到 IGW 的 traffic 也不會被當成 public NAT path。
- **B：** 正確。兩者的 connectivity type 與 address/path 不同，private NAT 常用於 TGW/VGW 等 private connectivity。
- **C：** 錯誤。NAT 支援 private resources 發起連線的 return traffic，不提供 unsolicited inbound Internet mapping。
- **D：** 錯誤。NAT 做 address translation；security policy 仍由 SG、NACL、Network Firewall 等元件承擔。

**事實查證：** [NAT gateway connectivity types](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)

### 練習題 6｜SAP｜把 Regional NAT Gateway 當作版本化 current-service extension

2026 年架構更新會評估 Regional NAT Gateway。團隊也在準備以 SAP-C02 為目標的題庫。哪個處理最嚴謹？

A. 把 Regional NAT Gateway 當成現行獨立架構選項，核對 Region availability、route、quota、failure model 與 pricing；題庫則標示為 current extension，除非 exam blueprint 已確認
B. 假設它只是多個 zonal NAT EIPs 的新名稱，不需看文件
C. 假設所有舊 SAA-C03/SAP-C02 題目一定會以它為唯一正解
D. 用它接受 unsolicited inbound Internet connections 到 private instances

**答案：A**

- **A：** 正確。2026-10-01 時 SAP-C03 尚未開放註冊，註冊自 2026-10-27 開始，SAP-C02 可考到 2026-11-17，C03 準備資源也要到 10-27 起發布；因此 current architecture 與已公布 scored blueprint 必須分開標示。
- **B：** 錯誤。Regional NAT Gateway 有自己的 deployment/routing model，不應視為文字別名。
- **C：** 錯誤。較新的服務不能自動倒灌到舊版考試假設，必須依目標考試公布的 guide 與日期校準。
- **D：** 錯誤。NAT 仍主要支援 resources 主動建立的連線，不是 public inbound gateway。

**事實查證：** [Regional NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)、[SAP-C02 Domain 1: Design for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)、[AWS Certified Solutions Architect – Professional exam transition](https://aws.amazon.com/certification/certified-solutions-architect-professional/)

### 練習題 7｜SAA｜依 HTTP cache contract 正確使用 CloudFront

全球使用者下載版本化的公開軟體套件；objects 很少更新，origin egress 與 latency 高。哪個 CloudFront 設計最合理？

A. 把每位使用者的 authorization token 加入 cache key，即使內容完全相同，以最大化 cache fragmentation
B. 用 CloudFront 複寫 relational database transactions
C. 設定長 TTL 但沿用固定 object name 覆寫內容，且永不 invalidation/versioning
D. 使用版本化 object URLs、精簡 cache key、合適 TTL 與 origin request policy，量測 cache hit rate 並保護 origin

**答案：D**

- **A：** 錯誤。不必要的高 cardinality key 會降低 hit rate；只有影響 response 的值才應納入。
- **B：** 錯誤。CloudFront 是 HTTP content delivery/cache，不是 database replication。
- **C：** 錯誤。長 TTL 配覆寫名稱會讓 stale content 難以控制；versioned names 較可預測。
- **D：** 正確。穩定版本化內容適合 edge cache，cache/origin policies 共同決定 hit rate 與送往 origin 的資訊。

**事實查證：** [CloudFront caching behavior](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html)

### 練習題 8｜SAP｜降低 cross-AZ chat 且維持 fault tolerance

三 AZ EKS microservices 使用 Istio service mesh，每個 request 產生 40 次跨 AZ calls，network cost 與 latency 很高。哪兩項改善不會把系統退化成單 AZ？（選兩項）

A. 把所有 services 永久固定在一個 AZ，並移除其他 AZ capacity
B. 用 Istio locality load balancing 依 zone 優先選 local endpoints，保留健康檢查與跨 zone failover，並確保每區有足夠 replicas/capacity
C. 無條件停用 cross-zone behavior，不驗證 target imbalance
D. 忽略 retry amplification，因為 retries 不產生 bytes
E. 批次／壓縮高聊天量 payload，減少不必要 calls，並在 AZ failure game day 驗證 routing 與 SLO

**答案：B、E**

- **A：** 錯誤。這會失去 AZ fault tolerance，可能用較低帳單換更大 outage risk。
- **B：** 正確。Istio locality load balancing 可根據 zone 優先本地 endpoints，並在本區無健康容量時 fail over；若每區 placement/capacity 不足，偏好本地反而會造成 overload。
- **C：** 錯誤。Target/capacity 不均時可能造成 overload，必須和 placement 一起設計。
- **D：** 錯誤。Retries 會增加 call count、bytes 與 downstream load。
- **E：** 正確。減少 payload/call amplification 是可移植優化，game day 則確認 resilience 未被破壞。

**事實查證：** [Optimize EKS data-transfer costs](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)、[AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)、[Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)

### 練習題 9｜SAP｜計算 centralized egress/inspection 的完整 cost 與 blast radius

公司以 TGW 把 100 個 VPC 的 egress 集中到 inspection VPC，再經 Network Firewall 與 NAT。哪個 architecture review 最完整？

A. 只計算一個 NAT 的 hourly charge；集中式一定較便宜
B. 假設 return path 可走任意路徑，stateful inspection 不需要 symmetry
C. 計入 TGW、inspection、NAT、endpoint/cross-AZ/data transfer 的雙向 processing，並評估 route symmetry、scale、latency、governance 與集中 blast radius
D. 只比較 firewall rule 數量，不看 bytes 或 failure boundary

**答案：C**

- **A：** 錯誤。集中式路徑可能串接多種 per-GB charges，固定 gateway 數少不代表總價低。
- **B：** 錯誤。Stateful inspection 通常需要對稱或受支援的 routing 才能正確關聯 flows。
- **C：** 正確。Centralization 的治理收益必須和每 hop 成本、capacity、latency 與單點風險一起比較。
- **D：** 錯誤。Rules 只是安全 configuration，無法代表 traffic economics 或 resilience。

**事實查證：** [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)、[AWS Transit Gateway pricing](https://aws.amazon.com/transit-gateway/pricing/)、[AWS Network Firewall pricing](https://aws.amazon.com/network-firewall/pricing/)、[NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)、[AWS Network Firewall deployment models](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)

### 練習題 10｜SAP｜用 metrics、flow logs、routes 與 cost data 證明 network savings

團隊把大量 S3 traffic 從 NAT 改走 gateway endpoint。哪兩項 before/after evidence 最能證明節省且沒有破壞 connectivity？（選兩項）

A. 關聯 NAT bytes/connection/error metrics、VPC Flow Logs、route/endpoint configuration 與 Cost and Usage data，確認 S3 bytes 的實際路徑改變
B. 只看 request count，假設每個 request bytes 都相同
C. 看到 NAT bill 下降就結束，即使費用可能轉移到另一未標記服務
D. 執行 application data access、policy/permission、AZ failure 與 rollback tests，並比較 total network cost 而非單一 line item
E. 變更前先刪除舊 route，避免保留 rollback path

**答案：A、D**

- **A：** 正確。多種 evidence 能把 byte path、configuration 與 bill 對齊，避免只看單一代理 metric。
- **B：** 錯誤。Object size 與 response volume 差異很大，request count 不能可靠推算 bytes。
- **C：** 錯誤。費用可能移到 endpoint、cross-AZ 或其他 processing；要看 end-to-end total。
- **D：** 正確。Cost optimization 仍需驗證 access、security、resilience 與 reversible rollout。
- **E：** 錯誤。先移除 rollback 會增加 change risk，也不利於 controlled comparison。

**事實查證：** [Monitor NAT gateways with CloudWatch](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway-cloudwatch.html)、[VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)、[Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)、[What are AWS Cost and Usage Reports?](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「網路費用常由架構流向而非instance價格主導。」，所以「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」能直接滿足它；若constraint改成「集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」。替代方案「集中式networking便於治理，但需把TGW、NAT、inspection與跨AZ每跳成本加總。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「網路費用常由架構流向而非instance價格主導。」，排除會導致「Private EC2跨AZ經NAT讀S3，資料多次付費且增加failure path。」的選項，再選「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」。本章對應的代表task包括：SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies；SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「畫出每GB路徑，使用endpoint、local AZ、CloudFront與合適Region減少不必要處理與傳輸。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「cost follows bytes through every hop」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
