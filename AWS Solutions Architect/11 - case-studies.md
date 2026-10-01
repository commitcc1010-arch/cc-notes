---
title: "完整實戰案例"
part: 10
as_of: 2026-10-01
---

# Part 10　完整實戰案例

# 第 97 章　Case Study：全球電商平台

全球電商同時要求低延遲、庫存一致、付款冪等、促銷burst與跨Region DR。

## 走進一次完整架構會議：先從故事開始

故事從一個看似簡單的需求開始：平日一萬RPS，促銷十倍；付款不能重複，推薦可降級。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：全球電商同時要求低延遲、庫存一致、付款冪等、促銷burst與跨Region DR。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon CloudFront會是本章的主要角色，Application Load Balancer則幫我們看清邊界。方向是「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：平日一萬RPS，促銷十倍；付款不能重複，推薦可降級。

全球使用者
      │
CloudFront / WAF / regional entry
      │
      ├─ Catalog / recommendation：可cache、可降級
      ├─ Cart / order：需要durable state
      └─ Payment：idempotency + authoritative transaction
                         │
                         ▼
                Event / Queue fan-out
                 ├─ inventory
                 ├─ notification
                 └─ analytics

促銷burst先由edge、autoscaling與queue吸收；付款正確性不能為吞吐讓步。

失敗時先找：將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon CloudFront有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon CloudFront和Application Load Balancer並不是兩個任意的產品名稱。前者適合本章，是因為「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」直接回應了眼前的問題；後者描述的「全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate browse availability from transaction correctness」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| AWS WAF | 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。 | Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。 |

## 把全圖套進一個具體案例

**場景：** 平日一萬RPS，促銷十倍；付款不能重複，推薦可降級。

1. 故事的起點：平日一萬RPS，促銷十倍；付款不能重複，推薦可降級。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon CloudFront負責「在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Application Load Balancer、Amazon Aurora、Amazon SQS、AWS WAF各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon CloudFront

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：全球電商同時要求低延遲、庫存一致、付款冪等、促銷burst與跨Region DR。
- **具體例子／邊界：** 在「平日一萬RPS，促銷十倍；付款不能重複，推薦可降級。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Application Load Balancer

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate browse availability from transaction correctness。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### stickiness

以cookie讓同一client暫時持續導向同一target；它是相容legacy state的折衷，不是高可用session store。

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### listener

在load balancer指定protocol/port等待client connection的入口。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### Layer 7

理解HTTP等application protocol，可依host/path/header做routing；ALB與CloudFront屬於此類。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

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

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

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

### Application Load Balancer

- **功用：** 提供HTTP/HTTPS Layer 7 routing與web workload入口。
- **底層機制：** 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。
- **關鍵設定：** listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
- **選擇時機：** 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。
- **替換時機：** 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。

### Amazon Aurora

- **功用：** 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。
- **底層機制：** Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。
- **關鍵設定：** cluster/instance endpoints、replica count、I/O-Optimized、backup、failover priority、parameter groups與Global Database。
- **選擇時機：** 需要高availability、較多read replicas、快速failover或AWS-native relational features。
- **替換時機：** 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### AWS WAF

- **功用：** 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。
- **底層機制：** Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。
- **關鍵設定：** scope、associated resource、managed rule groups、rate-based rules、IP sets、labels、logging與oversize handling。
- **選擇時機：** SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。
- **替換時機：** L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。

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

### Amazon Aurora：逐項設定說明

#### `cluster/instance endpoints`

- **控制什麼：** `cluster/instance endpoints`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要高availability、較多read replicas、快速failover或AWS-native relational features。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Aurora的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `replica count`

- **控制什麼：** `replica count`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「需要高availability、較多read replicas、快速failover或AWS-native relational features。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Aurora依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `I/O-Optimized`

- **控制什麼：** `I/O-Optimized`改變Amazon Aurora的performance/cost策略，例如並行度、I/O計價、query scheduling或memory回收。
- **何時需要：** 已有代表性load與瓶頸證據，能說明是latency、throughput、concurrency、I/O cost或memory pressure問題時。
- **怎麼設定／驗證：** 用benchmark比較候選mode，設定queue/class/eviction policy，觀察p95/p99、queue time、hit ratio及unit cost。
- **常見錯法：** 未先找瓶頸便切換模式可能只增加費用；問題也可能來自data model或workload isolation。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「需要高availability、較多read replicas、快速failover或AWS-native relational features。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Aurora依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `failover priority`

- **控制什麼：** `failover priority`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「需要高availability、較多read replicas、快速failover或AWS-native relational features。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Aurora設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `parameter groups`

- **控制什麼：** `parameter groups`是一組可版本化的engine/runtime參數，會改變Amazon Aurora的實際process行為。
- **何時需要：** 當需求符合「需要高availability、較多read replicas、快速failover或AWS-native relational features。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `Global Database`

- **控制什麼：** `Global Database`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

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

### AWS WAF：逐項設定說明

#### `scope`

- **控制什麼：** `scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `associated resource`

- **控制什麼：** `associated resource`指定AWS WAF讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `managed rule groups`

- **控制什麼：** `managed rule groups`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `rate-based rules`

- **控制什麼：** `rate-based rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `IP sets`

- **控制什麼：** `IP sets`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `labels`

- **控制什麼：** `labels`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `oversize handling`

- **控制什麼：** `oversize handling`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

## 讀到這裡，請用自己的話說一次

1. Amazon CloudFront的責任：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
2. 底層機制：DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
3. 第一個要看的設定：origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
4. 選擇邏輯：Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。
5. 不要混淆：Application Load Balancer的責任是「提供HTTP/HTTPS Layer 7 routing與web workload入口。」；它不會自動取代Amazon CloudFront。
6. 替換訊號：需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。
7. 最常見錯法：將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。
8. 可移植原則：separate browse availability from transaction correctness。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 | 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。 | 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。 |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 | 需要高availability、較多read replicas、快速failover或AWS-native relational features。 | 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| AWS WAF | 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。 | Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。 | SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。 | L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。 | 只有當題目條件明確改變時才可能合理。 | 將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。」之間做選擇。
- 認得常考設定：origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜CloudFront cache key 與個人化資料隔離

全球電商把 `/catalog/*`、`/cart/*` 與 `/checkout/*` 都放在同一個 CloudFront behavior，TTL 為 10 分鐘。上線後，少數登入使用者看到別人的購物車摘要。靜態商品圖片仍希望維持高 cache hit ratio。哪個修改最符合安全與效能需求？

A. 保留單一長 TTL，付款成功後再對整個 distribution 執行 invalidation
B. 拆分 behaviors：安全快取靜態 catalog；個人化或交易回應停用快取或只納入真正決定內容的身分輸入
C. 只把 Authorization header 轉送到 origin，但不把任何會改變回應的身分資訊放入 cache key
D. 保留單一 behavior，但把所有 viewer headers、cookies 與 query strings 全部加入 cache key

**答案：B**

- **A：** 錯誤。Invalidation 不是使用者隔離機制，且長 TTL 期間仍可能把已快取的個人化內容交給其他 viewer。
- **B：** 正確。CloudFront 只應共用可安全共享的回應；不同 path 使用不同 cache policy，才能同時保留靜態內容命中率與交易資料隔離。
- **C：** 錯誤。只轉送而未納入 cache key，可能讓 origin 產生不同內容，CloudFront 卻仍以相同 key 共用先前的回應。
- **D：** 不建議。全部納入會降低誤共用風險，卻讓 cache key 幾乎每次都不同；應只加入真正改變回應的值，並分離交易路徑。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understand the CloudFront cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)

### 練習題 2｜SAA｜CloudFront OAC 與私有 S3 origin

商品圖由 S3 提供並經 CloudFront 發送。安全稽核發現，知道 S3 URL 的人可以繞過 WAF 與 CloudFront 直接讀取物件。團隊要封閉這條旁路，同時保留 CloudFront 存取。應採用哪個方案？

A. 維持 public-read，但將物件 key 改成難以猜測的 UUID
B. 改用 S3 website endpoint，然後在 CloudFront 上啟用 Origin Access Control
C. 使用 S3 REST origin 與 CloudFront Origin Access Control，啟用 Block Public Access，並以 bucket policy 僅授權指定 distribution
D. 只在 CloudFront 加入 AWS WAF，S3 bucket policy 不需更動

**答案：C**

- **A：** 錯誤。不可猜測名稱不是授權控制；物件仍為 public-read，取得 URL 的人依然可以繞過 edge controls。
- **B：** 錯誤。OAC 用於受支援的 S3 bucket origin；S3 website endpoint 以自訂 origin 運作，不能用此模式建立相同的私有邊界。
- **C：** 正確。OAC 讓 CloudFront 以簽署的 origin request 取得私有物件；bucket policy 與 Block Public Access 共同阻止直接公開讀取。
- **D：** 錯誤。WAF 只處理經過 CloudFront 的請求；若 S3 仍公開，直接 origin request 不會經過該 Web ACL。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Restrict access to an Amazon S3 origin with CloudFront OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)

### 練習題 3｜SAP｜WAF rate control 與交易授權責任邊界

促銷期間，攻擊者從大量共享 NAT 位址送出 checkout requests。團隊已用 AWS WAF rate-based rule 降低濫用，但有人主張「通過 WAF 的請求可直接扣款」。哪個設計最正確？

A. 以 IAM identity policy 取代所有公開 HTTP bot 與 rate controls
B. 封鎖所有流量較高的來源 IP，無須考慮行動網路或企業 NAT 的共用位址
C. 將 rate limit 設得極低，通過 WAF 即視為已驗證客戶與合法訂單
D. WAF 負責 edge 流量與常見攻擊控制；應用仍須驗證登入者、價格、庫存、訂單狀態與付款授權

**答案：D**

- **A：** 錯誤。IAM 適合 AWS principal 與 API 授權，但不能直接取代面向匿名 Internet viewer 的 WAF bot/rate protection。
- **B：** 錯誤。共用 NAT 可能代表許多正常使用者；rate key 與 scope-down 條件應依實際攻擊模式設計，不能把來源 IP 當交易身分。
- **C：** 錯誤。Rate rule 是流量控制，不知道客戶是否有權購買，也不知道價格與庫存是否仍有效。
- **D：** 正確。WAF 與業務授權位於不同信任層；只有受信任的應用與資料層能決定某筆交易是否可提交。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS WAF rate-based rule statements](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html)

### 練習題 4｜SAP｜付款操作的持久化冪等設計

行動 App 呼叫付款 API 後逾時，使用者立刻重試。第一次請求其實已成功扣款，但 response 在網路中遺失。系統必須避免第二次扣款，且相同重試要得到可重現的結果。哪個方法最好？

A. 將 client timeout 調長到五分鐘，使 client 不會重試
B. 把付款放入 FIFO queue，並把 queue 的短期去重視為永久付款帳本
C. 在 Lambda global variable 暫存最近一分鐘的 request ID
D. 以客戶與付款操作範圍的 idempotency key 原子保存請求摘要、狀態與結果；相同參數重試回傳原結果

**答案：D**

- **A：** 錯誤。較長 timeout 只能降低部分重試，無法消除網路中斷、client crash 或 intermediary retry。
- **B：** 錯誤。Queue 可改善排序與短期重複處理，但付款的最終冪等性仍需由交易狀態與持久化 operation identity 保證。
- **C：** 錯誤。執行環境可被回收或平行擴展，記憶體狀態不是跨 instance、跨時間的可靠去重資料。
- **D：** 正確。持久化且原子的 operation record 能區分同一操作的安全重試，也能拒絕同一 key 被不同參數重用。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)

### 練習題 5｜SAA｜SQS backpressure 與 Lambda concurrency 上限

促銷流量會在三分鐘內由 1 萬 RPS 升到 10 萬 RPS。訂單可先進 SQS，但付款 API 經壓測只能承受約每秒 2,000 筆；每批處理時間、batch size 與 retry 都會改變實際吞吐。哪個修改最能保護下游？

A. 保留無上限 event source，改由付款 API throttle；Lambda retry 會自動形成穩定 backpressure
B. 只設定 function provisioned concurrency 為 2,000，將 concurrent executions 直接視為每秒 2,000 筆
C. 先以 batch size、平均/尾端處理時間與重試率估算安全 concurrency；再用 SQS event-source maximum concurrency 與 function reserved concurrency設上限，並監控 queue age
D. 只把 SQS message retention 增加到 14 天，讓服務自行把每秒呼叫數限制在 2,000

**答案：C**

- **A：** 錯誤。把 throttle 當控制器會產生大量失敗與 retry；應在呼叫下游之前限制消費速率並觀測 backlog。
- **B：** 錯誤。Provisioned concurrency 預先準備執行環境，並不等於 event-source 最大併發；concurrency 與每秒處理量也不是一比一。
- **C：** 正確。Concurrency 不是 RPS；安全上限需由 batch size、服務時間、retry 與下游 latency 推導，再用 event-source maximum concurrency 和 reserved concurrency形成可驗證 ceiling。
- **D：** 錯誤。Retention 只延長訊息可等待的時間，不控制同時執行數，也不會依付款服務容量自動調節 consumer。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS standard queues provide at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)、[Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[Lambda reserved concurrency and provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Configuring maximum concurrency for Amazon SQS event sources](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)

### 練習題 6｜SAA｜可選依賴的 graceful degradation

推薦服務偶爾需要 8 秒回應，但 catalog SLA 是 500 ms，checkout 不依賴推薦結果。產品經理接受推薦區塊暫時顯示熱門商品。應如何設計？

A. 把第一位使用者的推薦結果以不含身分的 cache key 全球快取
B. 為推薦呼叫設定短 timeout/circuit breaker，失敗時回傳確定性的熱門商品 fallback，並分開量測降級率
C. 推薦結果過舊時，讓整個 checkout 回傳 503 以避免不一致
D. 對推薦服務無限重試，直到取得個人化結果才回傳 catalog

**答案：B**

- **A：** 錯誤。個人化資料不能用共享 key 跨使用者重用；這既有資料洩漏風險，也不是可靠的降級策略。
- **B：** 正確。明確的 dependency budget 與 fallback 能保留核心功能，且獨立指標可揭露服務正在降級而非掩蓋問題。
- **C：** 錯誤。題目已說 checkout 不依賴推薦；把可選功能升級成硬依賴會擴大故障半徑。
- **D：** 錯誤。無界重試會消耗 request deadline 與資源，讓非關鍵依賴拖垮主要使用者旅程。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)

### 練習題 7｜SAP｜庫存 single-writer 與受控 promotion

稀缺商品不可 oversell。兩個 Region 都需要低延遲讀取，但業務尚未定義 concurrent write 的衝突解決規則。哪個資料寫入策略最安全？

A. 維持單一 authoritative writer；跨 Region 複寫讀取，故障時先 fence 舊 writer 再受控 promote secondary
B. 兩個 Region 同時接受庫存扣減，衝突一律以最後時間戳為準
C. 交易前讀取離使用者最近的 replica；只要讀取成功就允許扣庫存
D. 由 Route 53 health check 自動保證任何時刻只有一個 database writer

**答案：A**

- **A：** 正確。Single-writer 把庫存順序集中在一個 authority；promotion 必須包含寫入 fencing、lag 驗證與應用交易測試。
- **B：** 錯誤。Last-write-wins 可能遺失已承諾的扣庫存；沒有業務衝突語意時不能假設 active-active 可安全合併。
- **C：** 錯誤。Replica 可能有 replication lag，稀缺庫存決策不能把可能陳舊的讀取當作可提交的權威狀態。
- **D：** 錯誤。DNS health 只影響名稱解析，不會變更資料庫角色，也不會終止既有連線或鎖住舊 writer。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 8｜SAP｜Aurora Global Database planned switchover 與 unplanned failover 的選擇

主要 Region 仍健康，但公司要為預定維護把 Aurora Global Database writer 移到 secondary Region，並希望避免不必要的資料遺失。Runbook 應選哪種操作？

A. 先把 Route 53 TTL 設為零，DNS 會自行將 Aurora secondary 變成 writer 並保證既有連線切換
B. 在兩個 Regions 同時開放寫入，維護後再以 timestamp 合併，便不需要角色切換
C. 使用 managed switchover，先確認 secondary 狀態與 replication lag，讓 Aurora 協調角色切換；應用再重新解析 endpoint、重連並執行交易驗證
D. 宣告 unplanned failover，因 failover 與 switchover 的資料保護與前置條件完全相同

**答案：C**

- **A：** 錯誤。DNS 不會修改 Aurora cluster role，TTL 也不會終止既有資料庫連線；database operation 必須先完成。
- **B：** 錯誤。Aurora Global Database 並非任意雙寫衝突合併系統；未定義交易語意時開放兩個 authority 會造成分叉。
- **C：** 正確。健康環境的預定移轉應使用 switchover，先檢查複寫狀態並讓服務協調角色；應用仍須處理 endpoint/連線更新和業務驗證。
- **D：** 錯誤。Failover 用於非預期中斷，可能接受較高資料損失風險；健康 primary 的計畫維護不應把它當成相同操作。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)、[Using Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)

### 練習題 9｜SAP｜以成功 checkout 為單位的成本最佳化

財務團隊要求降低每筆成功訂單的成本，但不可改變付款正確性與 30 分鐘跨 Region RTO。下列哪些兩項措施最符合要求？（選兩項）

A. 移除 secondary Region 的資料與 capacity，等災難發生再重建
B. 將 checkout response 快取十分鐘，以最大化所有 path 的 cache hit ratio
C. 依實測 arrival/service rate 調整 queue batch、consumer concurrency 與 database capacity，同時保留 RTO 所需的 standby
D. 把可安全共享的 catalog 與圖片放到 CloudFront，並量測 origin offload 與每筆成功訂單的傳輸成本
E. 只追蹤 EC2 CPU 利用率，因 queue、database 與 data transfer 不影響單位經濟

**答案：C、D**

- **A：** 錯誤。這會破壞既定 RTO；若要降低 DR 成本，必須先重新協商 recovery objective 或證明較小 standby 仍可在時間內擴容。
- **B：** 錯誤。交易回應具有身分與狀態，不能為了命中率而跨請求共用；此措施可能引入資料洩漏與錯誤交易。
- **C：** 正確。從完整資料路徑找成本，並以 bounded concurrency 和 right-sizing 消除浪費，才能在不犧牲正確性與復原目標下優化。
- **D：** 正確。靜態 browse content 適合 edge cache，能減少重複 origin work；以成功 checkout 正規化才不會用錯誤流量掩飾成本。
- **E：** 錯誤。Serverless request、queue operation、database I/O、edge 與跨 Region 傳輸都可能是主要成本，不能只看一種 compute metric。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Understand the CloudFront cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[Lambda reserved concurrency and provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[REL13-BP02 Select a DR strategy from recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 10｜SAP｜促銷上線的必要可靠性控制組合

下一次促銷必須同時承受十倍 burst，並保證 ambiguous retry 不會重複扣款。下列哪些兩個能力是不可互相取代的必要條件？（選兩項）

A. 讓 Lambda 無上限 scale out，使所有請求盡快直接打到下游
B. 使用 durable queue 吸收非同步工作，並以 concurrency ceiling 保護付款與庫存 dependency
C. 建立持久化 payment idempotency ledger，以 operation key 原子記錄並重放既有結果
D. 只使用 CloudFront 與 WAF，因減少 origin 流量即可保證付款不重複
E. 只使用 SQS standard queue，因 managed queue 會把所有 message 精確交付一次

**答案：B、C**

- **A：** 錯誤。無界 autoscaling 會放大對有限下游的並行壓力，可能更快造成 throttling、逾時與 retry storm。
- **B：** 正確。Queue 與 bounded consumers 解耦流量尖峰及安全 service rate，避免過載把整個交易系統拖垮。
- **C：** 正確。只有持久化且原子的付款 operation state 能在第一次成功但回應遺失時安全回傳同一結果。
- **D：** 錯誤。Edge controls 可減少濫用與可快取流量，但不能替付款建立交易 identity，也無法限制合法 burst 對下游的壓力。
- **E：** 錯誤。SQS standard 採 at-least-once delivery，consumer 必須能處理重複；queue 也不能替代付款帳本。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)、[Amazon SQS standard queues provide at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)、[Lambda reserved concurrency and provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Edge cache靜態內容，regional stateless services，queue吸收非同步…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「全球電商同時要求低延遲、庫存一致、付款冪等、促銷burst與跨Region DR。」，所以「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」能直接滿足它；若constraint改成「全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」。替代方案「全active-active可降低部分延遲，但庫存與付款衝突處理會大幅增加。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「全球電商同時要求低延遲、庫存一致、付款冪等、促銷burst與跨Region DR。」，排除會導致「將每個服務同步串接，推薦失敗便阻止checkout，或重試造成重複付款。」的選項，再選「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Edge cache靜態內容，regional stateless services，queue吸收非同步工作，交易資料定義single writer/replication。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate browse availability from transaction correctness」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 98 章　Case Study：Serverless SaaS

多租戶SaaS需要tenant isolation、burst scaling、成本歸屬與安全onboarding。

## 走進一次完整架構會議：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：數千小客戶共享平台，少數enterprise要求獨立key與資料邊界。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：多租戶SaaS需要tenant isolation、burst scaling、成本歸屬與安全onboarding。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon API Gateway負責主要工作，AWS Lambda提醒我們答案不是永遠固定。本章會走向「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：數千小客戶共享平台，少數enterprise要求獨立key與資料邊界。

商業需求與不能妥協的限制
          ▼
[Amazon API Gateway：主要責任]
          │ 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。
  · Amazon DynamoDB：提供managed key-value/document database與單位毫秒scale。
  · AWS KMS：管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
可移植原則：multi-tenancy is an isolation and noisy-neighbor design

失敗時先找：只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon API Gateway有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon API Gateway和AWS Lambda並不是兩個任意的產品名稱。前者適合本章，是因為「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」直接回應了眼前的問題；後者描述的「Pool model成本低；silo model隔離強；bridge model依tenant tier混合。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「multi-tenancy is an isolation and noisy-neighbor design」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 |

## 把全圖套進一個具體案例

**場景：** 數千小客戶共享平台，少數enterprise要求獨立key與資料邊界。

1. 故事的起點：數千小客戶共享平台，少數enterprise要求獨立key與資料邊界。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon API Gateway負責「提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Lambda、Amazon DynamoDB、AWS KMS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon API Gateway

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：多租戶SaaS需要tenant isolation、burst scaling、成本歸屬與安全onboarding。
- **具體例子／邊界：** 在「數千小客戶共享平台，少數enterprise要求獨立key與資料邊界。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Lambda

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Pool model成本低；silo model隔離強；bridge model依tenant tier混合。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：multi-tenancy is an isolation and noisy-neighbor design。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### envelope encryption

先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### data key

實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

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

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

### AWS KMS

- **功用：** 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
- **底層機制：** Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
- **關鍵設定：** key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- **選擇時機：** S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。
- **替換時機：** 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。

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

## 讀到這裡，請用自己的話說一次

1. Amazon API Gateway的責任：提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
2. 底層機制：Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。
3. 第一個要看的設定：REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
4. 選擇邏輯：API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。
5. 不要混淆：AWS Lambda的責任是「按事件執行短生命函式，自動管理capacity與runtime基礎設施。」；它不會自動取代Amazon API Gateway。
6. 替換訊號：一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。
7. 最常見錯法：只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。
8. 可移植原則：multi-tenancy is an isolation and noisy-neighbor design。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 | serverless API、公開/私有API、consumer治理與request transformation。 | 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 | S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。 | 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Pool model成本低；silo model隔離強；bridge model依tenant tier混合。 | 只有當題目條件明確改變時才可能合理。 | 只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Pool model成本低；silo model隔離強；bridge model依tenant tier混合。」之間做選擇。
- 認得常考設定：REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。
- 對應官方tasks：SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜受信任 tenant context 的建立與傳遞

多租戶 SaaS 的 request body 包含 `tenantId`。滲透測試者只改這個欄位，就讀到另一租戶的 invoice。API 使用 JWT，團隊希望保留 pooled Lambda。應如何修正？

A. 把 tenantId 改成 UUID，因較難猜測即可提供授權
B. 用 API key 取代 JWT，並把 API key 當作完整使用者與資料授權
C. 繼續相信 body，但在 CloudWatch Logs 記錄每次 tenantId
D. 在 API 邊界驗證 token issuer/audience，從受驗證 claims/authorizer context 取得 tenant，服務端再以該身分限制資源

**答案：D**

- **A：** 錯誤。不可猜測識別碼只能增加枚舉成本；client 仍可提交其他值，服務端沒有建立可信的 tenant-resource 關係。
- **B：** 錯誤。API key 主要用於識別 consumer 與 usage plan，不是 user authentication，也不自動限制其可讀取的 tenant data。
- **C：** 錯誤。Logging 有助偵測，不能防止跨租戶存取；不可信 body 不能成為授權輸入。
- **D：** 正確。Tenant identity 必須由已驗證的身分衍生，經 trusted context 傳遞，且每個資料操作仍需執行 tenant-aware authorization。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Use API Gateway Lambda authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)

### 練習題 2｜SAA｜Pooled DynamoDB 的 tenant-scoped session、key 與 Scan 邊界

多租戶 Lambda 共用 DynamoDB table 與 execution role。呼叫端 JWT 已可驗證 tenantId，但目前 partition key 只有 invoiceId，role 可對整表 Query/Scan。哪個改造才能形成完整、可驗證的租戶隔離？

A. 讓共用 execution role 的 policy 列出所有租戶前綴，再相信 application 傳入的 tenantId 不會被錯用
B. 只把 tenantId 加入 FilterExpression；資料被 DynamoDB 讀出後再由 Lambda 丟棄其他租戶項目
C. 將可信 tenantId 納入 partition-key 前綴；每次請求建立 tenant-scoped session/principal tag，把 `dynamodb:LeadingKeys` 綁到該值，並禁止或另行隔離 Scan 等無法維持 key scope 的路徑
D. 保留整表權限，但以 DynamoDB server-side encryption 和 CloudTrail 偵測跨租戶讀取

**答案：C**

- **A：** 錯誤。單一靜態 role 若同時獲准所有租戶前綴，IAM 無法判斷本次 request 的租戶；application bug 或注入仍可越界。
- **B：** 錯誤。FilterExpression 在讀取後才過濾，不是授權；已讀取容量與資料接觸面仍跨越租戶邊界。
- **C：** 正確。可信 caller context 必須進入每次請求的授權邊界；session/principal tag、LeadingKeys 與 tenant-first key design共同限縮存取，Scan 則需停用或走獨立受控流程。
- **D：** 錯誤。加密與稽核很重要，但不會把同一張 table 的 items 自動切成 tenant authorization boundaries。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Use IAM policy conditions for fine-grained DynamoDB access](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)、[Passing session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)

### 練習題 3｜SAP｜Pool、silo 與 bridge tenancy model

SaaS 有 4,000 個標準租戶，希望共享成本；另有 20 個金融租戶要求獨立資料資源、獨立 AWS account 與各自的 customer-managed KMS key。哪個模型最符合需求？

A. 只把金融租戶資料移到另一張 table，但繼續讓 pooled runtime role 任意 decrypt 其 keys
B. 使用 bridge model：標準租戶 pooled；金融租戶 siloed，並以 tenant placement metadata 與一致授權層路由
C. 所有租戶都使用同一 table 與同一 KMS key alias，因 alias 名稱可以提供密碼學隔離
D. 為 4,020 個租戶全部人工複製完整 stack，不需要 tier 或生命週期標準

**答案：B**

- **A：** 錯誤。Storage 分開但 decrypt principal 仍共用且過寬，關鍵的 cryptographic/access boundary 尚未成立。
- **B：** 正確。Bridge model 讓不同 tier 採不同部署隔離強度，同時保留共同 control plane、tenant-aware identity 與可稽核 placement。
- **C：** 錯誤。Alias 是 key 的友善名稱，不會讓同一 key 對不同租戶產生隔離；共享 table 也不符合獨立 account/data boundary。
- **D：** 錯誤。全面 silo 可能做到隔離，但違反大多數租戶希望共享成本的條件，且人工 provisioning 難以治理。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)、[AWS KMS key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 4｜SAA｜API Gateway usage plan 的 best-effort 邊界

產品合約規定每個租戶每月消費不得超過固定金額，超過前必須硬性拒絕。團隊已設定 API Gateway usage plan quota，並打算拿 API key 當唯一授權。哪個評估正確？

A. API key 等同已驗證使用者，知道 key 即可讀取該租戶所有資料
B. Usage plan 可做 best-effort traffic shaping；仍需身分授權，以及原子計量/配額狀態來實施硬性商業上限
C. 只要 gateway 有 throttle，下游 Lambda 與 database 就永遠不需要 capacity/concurrency 限制
D. Usage plan 是嚴格財務計量，因此不需要 application metering 或下游 admission control

**答案：B**

- **A：** 錯誤。API key 不應取代 authentication/authorization；它本身不表示使用者能對哪些 tenant resources 執行哪些 actions。
- **B：** 正確。Gateway quota 適合 consumer shaping；硬上限需要可信 tenant identity、持久化計量與 race-safe admission decision。
- **C：** 錯誤。Gateway 與 downstream limits 是不同層；burst、retry 與其他 invocation path 仍可能耗盡 Lambda concurrency 或 database capacity。
- **D：** 錯誤。AWS 明確說明 usage-plan throttle 與 quota 為 best effort；不能把它當作不可超越的帳務控制。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[API Gateway usage plans and best-effort quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)

### 練習題 5｜SAA｜Serverless SaaS noisy-neighbor 隔離

一個 enterprise tenant 匯入大量資料，Lambda concurrency 被其工作吃滿，其他租戶的登入 API 開始 throttle。團隊不想為每個小租戶建立完整 stack。哪個改善最有效？

A. 所有 function 開啟 provisioned concurrency，因它會形成每租戶硬性 request quota
B. 把批次匯入與互動 API 分離成不同 function/queue，設定 reserved 或 maximum concurrency，並做 tenant admission/backpressure
C. 把所有租戶 message 放在同一 FIFO message group，讓整個平台依序處理
D. 移除 concurrency limits，讓 Lambda 自動擴展直到下游也跟著擴展

**答案：B**

- **A：** 錯誤。Provisioned concurrency 主要降低 cold start 並預先配置 execution environments，不是 tenant quota 或全域 starvation 防護。
- **B：** 正確。Workload 分離與 bounded concurrency 保留關鍵 API capacity，也能把 hot tenant 的非同步工作限制在安全速率。
- **C：** 錯誤。同一 message group 會把所有租戶序列化，雖避免併發，卻造成更嚴重的 head-of-line blocking。
- **D：** 錯誤。Lambda 可比 database、KMS 或第三方 API 更快擴展；無界 concurrency 會把 noisy-neighbor 問題轉移到下游。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Lambda reserved concurrency and provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Configuring maximum concurrency for Amazon SQS event sources](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)

### 練習題 6｜SAP｜Tenant-scoped DynamoDB 冪等寫入

建立 invoice API 可能被 gateway 或 client 重試。不同租戶偶爾使用相同的 client request ID，而且同一 request ID 若帶不同金額必須被拒絕。哪個實作最安全？

A. 依賴 API Gateway，假設它不會重送已轉交給 integration 的 request
B. 把 processed IDs 放在目前 Lambda container 的記憶體集合
C. 只以 client request ID 做全平台唯一 key，第一個租戶會阻擋其他租戶
D. 以 tenant、operation 與 request ID 組合成冪等 key，使用 conditional write/transaction 原子保存參數摘要與結果

**答案：D**

- **A：** 錯誤。任何網路/API path 都可能出現 ambiguous outcome；side-effect owner 必須自行提供冪等語意。
- **B：** 錯誤。Lambda execution environments 非持久且可平行，記憶體集合無法建立跨 invocation 的一致性。
- **C：** 錯誤。沒有 tenant scope 會造成合法碰撞；冪等 identity 必須包含可區分的信任與操作範圍。
- **D：** 正確。Conditional write 或 transaction 可在 race 下只建立一次 operation record，並用參數摘要辨識同 key 的不相容重用。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)

### 練習題 7｜SAP｜可恢復且可稽核的 tenant onboarding

Enterprise tenant onboarding 需建立 account、table、KMS grants、quota 與 DNS。同步 Lambda 在第六步逾時後，管理員無法判斷哪些步驟已完成。哪個重構最合適？

A. 將 Lambda timeout 調到 15 分鐘，繼續在單一 request 中完成所有步驟
B. 授予 onboarding function organization administrator，讓權限錯誤不再阻塞
C. 使用 durable workflow/state record，讓每一步可冪等重試或補償；全部驗證完成後才把 tenant 標記 ready
D. 只要 AWS account 建立成功就回報 onboarding 完成，其餘設定由首次 request 自動補齊

**答案：C**

- **A：** 錯誤。較長 timeout 沒有解決 partial state、重試重複建立、人工判斷與跨服務補償問題。
- **B：** 錯誤。擴大權限會增加 blast radius，且服務故障、quota 或 eventual consistency 仍會造成部分完成。
- **C：** 正確。Durable orchestration 將每個 side effect 變成可觀察狀態，並以 readiness gate 防止未完成隔離的 tenant 接受流量。
- **D：** 錯誤。Resource existence 不代表 key policy、quota、routing 與 isolation 已正確；未驗證前接受流量會造成安全與一致性風險。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)、[AWS KMS key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 8｜SAP｜Pooled 與 siloed 成本歸屬

財務要把共享 API/Lambda/DynamoDB 成本分攤到租戶，同時也要精確歸屬 enterprise tenant 的獨立 accounts 與 keys。只使用 resource tags 為何不夠？應怎麼做？

A. 所有 pooled 成本平均分攤，因共享服務無法量測 tenant usage
B. 以 API key request count 代表全部成本，包括儲存、昂貴查詢與背景工作
C. Siloed resources 使用啟用的 cost-allocation tags/account；pooled path 另記 tenant-aware request、storage 與 expensive-operation usage
D. 每次 Lambda invocation 都動態修改同一 function 的 CostCenter tag

**答案：C**

- **A：** 錯誤。平均分攤可能符合某種商業政策，但題目要求依使用量歸屬；應用層可產生 tenant meter。
- **B：** 錯誤。API request 只是成本 driver 之一，無法反映物件大小、database capacity、async job 或高成本模型推論。
- **C：** 正確。獨立資源可用原生 billing dimensions；共享資源則需在 application path 記錄穩定 tenant identity 與可對帳的 usage units。
- **D：** 錯誤。Resource tag 不是 per-invocation label，頻繁改 tag 也無法把同一計費期間內的共享使用量可靠分割。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Activating user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)

### 練習題 9｜SAP｜Pool-to-silo 資料遷移的安全切換

一個大型租戶要從 pooled DynamoDB 移到其專屬 account/table/KMS key，允許短暫唯讀但不可複製其他租戶資料，也必須能 rollback。下列哪些兩項是必要做法？（選兩項）

A. 以可信 tenant key 範圍匯出/複製並驗證筆數、內容、index/access path 與目標 key permissions
B. 先把 placement metadata 指向空的專屬 table，再在背景補資料
C. 複製整張 pooled table，切換後再刪除不屬於該租戶的 rows
D. 只更換 KMS alias，因 alias 更新會自動移動及重新隔離 DynamoDB items
E. 在一致性邊界暫停或協調寫入，原子切換 placement，並保留來源 checkpoint 與反向切換條件

**答案：A、E**

- **A：** 正確。資料選取必須由 tenant-scoped key 驗證，而不只是後過濾；目的端權限與 access patterns 也要在導流前測試。
- **B：** 錯誤。先導向空資料集會造成遺失與不一致；placement change 應在 copy、delta、validation 完成後才提交。
- **C：** 錯誤。這會把其他租戶資料帶入隔離環境，違反最小資料移動與 confidentiality boundary。
- **D：** 錯誤。Alias 只改變 KMS key 的參照，不會把 table items 複製到另一 account，也不等同資料平面遷移。
- **E：** 正確。切換點必須處理最後增量與 concurrent writes；checkpoint 和保留來源讓錯誤時能有界 rollback。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[SaaS Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/saas-tenant-isolation-strategies.pdf)、[Use IAM policy conditions for fine-grained DynamoDB access](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)、[AWS KMS key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 10｜SAP｜跨租戶讀取與容量飢餓的雙重防護

Pooled SaaS 必須同時防止跨 tenant 讀取，且不能讓單一 hot tenant 耗盡全部 Lambda 與下游容量。下列哪些兩項合起來才能滿足兩個要求？（選兩項）

A. 只設定 API Gateway usage plan，因 quota 也會限制使用者能讀哪些 DynamoDB partitions
B. 所有資料只使用同一 customer-managed KMS key，因 encryption 會自動授權每個 row
C. 只為 Lambda 設定 provisioned concurrency，因 warm environments 會阻止跨 tenant access
D. 從驗證過的 caller claims 建立 tenant context，並以 tenant-aware keys/IAM conditions 約束資料操作
E. 分離關鍵工作並使用 reserved/maximum concurrency、queue 與 tenant admission control 建立 backpressure

**答案：D、E**

- **A：** 錯誤。Usage plan 是 best-effort traffic shaping，不是資料授權，也不能保證下游不被其他 invocation path 壓垮。
- **B：** 錯誤。Encryption at rest 不會替 item 建立 tenant authorization；能 decrypt table 的 principal 仍可能讀取錯誤 partition。
- **C：** 錯誤。Provisioned concurrency 處理 cold start 與預先容量，不會驗證 tenant，亦不是 per-tenant hard quota。
- **D：** 正確。可信身分與 key/policy scoping 解決「誰能讀哪些資料」，是 cross-tenant isolation 的核心。
- **E：** 正確。Bounded concurrency 與 per-tenant backpressure 解決「誰能消耗多少共享 capacity」，補足 noisy-neighbor 隔離。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Use API Gateway Lambda authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)、[Use IAM policy conditions for fine-grained DynamoDB access](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)、[Lambda reserved concurrency and provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「API Gateway/Lambda處理request，DynamoDB以tenant-aware key…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「多租戶SaaS需要tenant isolation、burst scaling、成本歸屬與安全onboarding。」，所以「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」能直接滿足它；若constraint改成「Pool model成本低；silo model隔離強；bridge model依tenant tier混合。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」。替代方案「Pool model成本低；silo model隔離強；bridge model依tenant tier混合。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「多租戶SaaS需要tenant isolation、burst scaling、成本歸屬與安全onboarding。」，排除會導致「只在request body相信tenant ID，或單一hot tenant耗盡整個Lambda concurrency。」的選項，再選「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAA-2.1 Design scalable and loosely coupled architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「API Gateway/Lambda處理request，DynamoDB以tenant-aware keys，per-tenant quota與idempotency控制。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「multi-tenancy is an isolation and noisy-neighbor design」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 99 章　Case Study：高流量影音服務

影音平台需要大物件ingest、transcode、全球delivery與成本控制。

## 走進一次完整架構會議：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：每天上傳TB影片，熱門內容全球觀看，冷內容保存多年。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：影音平台需要大物件ingest、transcode、全球delivery與成本控制。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon S3，對照角色是Amazon CloudFront。我們選擇「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：每天上傳TB影片，熱門內容全球觀看，冷內容保存多年。

商業需求與不能妥協的限制
          ▼
[Amazon S3：主要責任]
          │ 以HTTP API保存object，提供高durability、彈性namespace與多種storage cla…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon CloudFront：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
  · AWS Batch：排程大量batch jobs到managed compute environments。
  · AWS Elemental MediaConvert：以broadcast-grade managed file transcoding將S3中的影音sourc…
可移植原則：move bytes once, transform asynchronously, serve from the edge

失敗時先找：Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon S3有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3和Amazon CloudFront並不是兩個任意的產品名稱。前者適合本章，是因為「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」直接回應了眼前的問題；後者描述的「Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「move bytes once, transform asynchronously, serve from the edge」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| AWS Batch | 排程大量batch jobs到managed compute environments。 | Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。 |
| AWS Elemental MediaConvert | 以broadcast-grade managed file transcoding將S3中的影音source轉成多種codec、resolution與封裝格式。 | Application建立job並引用input/output S3 locations、job template與queue；MediaConvert讀取source、執行轉碼後寫回S3，再以EventBridge發出狀態事件。 |

## 把全圖套進一個具體案例

**場景：** 每天上傳TB影片，熱門內容全球觀看，冷內容保存多年。

1. 故事的起點：每天上傳TB影片，熱門內容全球觀看，冷內容保存多年。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3負責「以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudFront、AWS Batch、AWS Elemental MediaConvert各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon S3

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：影音平台需要大物件ingest、transcode、全球delivery與成本控制。
- **具體例子／邊界：** 在「每天上傳TB影片，熱門內容全球觀看，冷內容保存多年。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudFront

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：move bytes once, transform asynchronously, serve from the edge。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### origin

CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ETL

Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

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

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

### Amazon CloudFront

- **功用：** 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
- **底層機制：** DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
- **關鍵設定：** origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- **選擇時機：** 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。
- **替換時機：** 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。

### AWS Batch

- **功用：** 排程大量batch jobs到managed compute environments。
- **底層機制：** Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。
- **關鍵設定：** job definition、queue priority、compute environment、vCPU/memory/GPU、array jobs、retry與timeout。
- **選擇時機：** rendering、scientific、ETL與可排隊的container batch。
- **替換時機：** 持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。

### AWS Elemental MediaConvert

- **功用：** 以broadcast-grade managed file transcoding將S3中的影音source轉成多種codec、resolution與封裝格式。
- **底層機制：** Application建立job並引用input/output S3 locations、job template與queue；MediaConvert讀取source、執行轉碼後寫回S3，再以EventBridge發出狀態事件。
- **關鍵設定：** queue、job/template、input/output groups、codec、IAM service role、acceleration、priority與EventBridge notifications。
- **選擇時機：** 新建video-on-demand workflow，需要managed file-based transcoding、ABR outputs與可觀測job狀態。
- **替換時機：** Live streaming選MediaLive；簡單圖片處理可用Lambda/Batch；特殊codec或GPU控制才自建。Elastic Transcoder已於2025-11-13停止支援，不應用於新架構。

## 考前與實作時再查：設定操作手冊

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

### AWS Elemental MediaConvert：逐項設定說明

#### `queue`

- **控制什麼：** `queue`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「新建video-on-demand workflow，需要managed file-based transcoding、ABR outputs與可觀測job狀態。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elemental MediaConvert依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `job/template`

- **控制什麼：** Job是一次實際轉碼請求；job template則保存可重用的output groups、video/audio處理與編碼設定。輸入、輸出位置等每支影片不同的值仍可在送出job時覆寫。
- **何時需要：** 同一平台反覆產生HLS、DASH或檔案輸出，希望把經測試的轉碼規格版本化，同時讓每支影片指定自己的S3來源與目的地時。
- **怎麼設定／驗證：** 先在隔離queue用代表性素材建立並驗證job settings，再保存具版本名稱的job template；提交job時指定template、input、destination、IAM role與metadata，並以EventBridge追蹤COMPLETE或ERROR。
- **常見錯法：** 直接修改共用template可能讓重跑的影片產生不同輸出；template也不會自動提供job idempotency，producer仍須以asset/version保存job ID並避免重複計費。

#### `input/output groups`

- **控制什麼：** `input/output groups`指定AWS Elemental MediaConvert讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `codec`

- **控制什麼：** Codec決定影像或音訊如何壓縮，例如H.264、H.265/HEVC或AV1；它影響裝置相容性、畫質、位元率、轉碼時間與播放端計算成本。
- **何時需要：** 需要在廣泛裝置相容、較低傳輸成本、較高畫質或特定播放器能力間取捨，並為adaptive-bitrate ladder產生多個renditions時。
- **怎麼設定／驗證：** 先列出目標裝置與container/streaming format支援，再為每個output設定codec、rate-control mode、bitrate/quality、resolution、frame rate與GOP；用真實播放器及VMAF等品質指標驗證。
- **常見錯法：** 只追求最高壓縮率可能讓舊裝置無法播放或增加編碼成本；把codec、container與manifest混為一談，也會產生檔案成功但播放器不相容的結果。

#### `IAM service role`

- **控制什麼：** `IAM service role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「新建video-on-demand workflow，需要managed file-based transcoding、ABR outputs與可觀測job狀態。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elemental MediaConvert明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `acceleration`

- **控制什麼：** `acceleration`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `priority`

- **控制什麼：** `priority`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「新建video-on-demand workflow，需要managed file-based transcoding、ABR outputs與可觀測job狀態。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elemental MediaConvert以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `EventBridge notifications`

- **控制什麼：** `EventBridge notifications`把AWS Elemental MediaConvert與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. Amazon S3的責任：以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
2. 底層機制：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
3. 第一個要看的設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
4. 選擇邏輯：S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。
5. 不要混淆：Amazon CloudFront的責任是「在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。」；它不會自動取代Amazon S3。
6. 替換訊號：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
7. 最常見錯法：Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。
8. 可移植原則：move bytes once, transform asynchronously, serve from the edge。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| AWS Batch | 排程大量batch jobs到managed compute environments。 | Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。 | rendering、scientific、ETL與可排隊的container batch。 | 持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。 |
| AWS Elemental MediaConvert | 以broadcast-grade managed file transcoding將S3中的影音source轉成多種codec、resolution與封裝格式。 | Application建立job並引用input/output S3 locations、job template與queue；MediaConvert讀取source、執行轉碼後寫回S3，再以EventBridge發出狀態事件。 | 新建video-on-demand workflow，需要managed file-based transcoding、ABR outputs與可觀測job狀態。 | Live streaming選MediaLive；簡單圖片處理可用Lambda/Batch；特殊codec或GPU控制才自建。Elastic Transcoder已於2025-11-13停止支援，不應用於新架構。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。 | 只有當題目條件明確改變時才可能合理。 | Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。」之間做選擇。
- 認得常考設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.1 Design cost-optimized storage solutions；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜S3 multipart upload 的可恢復大檔上傳

影音平台需接收 80–300 GiB master files。架構審查發現現行 client 想用 single PutObject，但單次 PUT 不支援這種大小；跨國連線也常在接近完成時中斷。團隊希望只重送失敗片段並清理未完成資料。哪個方案最合適？

A. 把每個 part 永久保存成獨立 object 與 manifest；即使下游要求單一原始 object，也不再執行 CompleteMultipartUpload
B. 使用 multipart upload，但每次中斷都丟棄 upload ID 並重新建立所有 parts，避免保存 client state
C. 使用 S3 multipart upload，保存 upload ID、獨立重試 parts、完成後組合，並以 lifecycle abort 過期的 incomplete multipart uploads
D. 啟用 S3 Transfer Acceleration 後繼續 single PutObject；加速會移除單次 PUT 大小限制並提供斷點續傳

**答案：C**

- **A：** 錯誤。分片 objects 加 manifest 是另一種資料格式，只有下游明確支援時才可採用；它不能滿足題目既有的單一 object contract。
- **B：** 錯誤。Multipart 的價值之一是保留 upload ID 與已成功 parts；每次全部重傳會失去可恢復性並浪費頻寬。
- **C：** 正確。Multipart upload 支援大型物件與獨立 part retry；完成後仍是單一 S3 object，lifecycle 可清除長期未完成且持續計費的 parts。
- **D：** 錯誤。Transfer Acceleration 可改善長距離傳輸路徑，但不改變 PutObject 的單次上傳限制，也不自動提供 multipart 的 part-level recovery。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Uploading objects to Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html)、[Amazon S3 PutObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)、[Amazon S3 multipart upload overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)、[Managing the lifecycle of Amazon S3 objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

### 練習題 2｜SAA｜短效且限定 object 的 direct upload 授權

已登入 creator 應直接上傳至 S3，application server 不轉送影片。安全要求 presigned request 只能寫入該 creator 的一個預定 key，十分鐘後失效，且完成後要先驗證 metadata 才可轉碼。應怎麼做？

A. 簽發一組長期 IAM access keys 給瀏覽器，允許對整個 bucket `s3:PutObject`
B. 建立一次 presigned URL 後永久重用，因簽名已證明 creator 身分
C. 把 ingest bucket 設為 public-write，並用難猜 object key 取代授權
D. 後端依可信 creator identity 產生短效、限定 method/key 的 presigned request，配合 bucket-policy conditions，完成後再驗證 object

**答案：D**

- **A：** 錯誤。把長期 AWS credentials 放進 client 會擴大洩漏範圍；direct upload 不代表必須交付持久 IAM secret。
- **B：** 錯誤。Presigned URL 是 bearer capability，應短效且單一用途；它也不是永久 subscriber/creator session。
- **C：** 錯誤。Public-write 讓未授權人士寫入並可能產生成本或惡意內容；不可猜測 key 不是 access control。
- **D：** 正確。Presigned request 使用簽發 principal 的權限並受有效期與 request 範圍限制；server-side verification 再決定是否進入處理流程。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Download and upload objects with presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)

### 練習題 3｜SAP｜S3 notification 的重複與順序處理

同一個影片 key 被重新上傳兩次，consumer 偶爾收到重複 `ObjectCreated`，也看見較舊事件晚於較新事件抵達。系統不可讓舊版本覆蓋新轉碼狀態。哪個設計最安全？

A. 以 bucket/key/version 或 sequencer-aware identity 保存處理狀態，consumer 冪等，並依同 key 的版本規則拒絕 stale event
B. 假設 S3 event notification 精確交付一次，因此只需修正 consumer timeout
C. 以事件抵達 consumer 的 wall-clock time 判斷 object 的權威版本
D. 維護一個全 bucket 共用的 last-event ID，較小者一律忽略

**答案：A**

- **A：** 正確。把事件 identity 與實際 object version 綁定，原子記錄處理結果，才能同時處理 duplicate 與同 key 的 out-of-order delivery。
- **B：** 錯誤。S3 event notifications 可能重複，可靠 consumer 必須能安全重處理同一邏輯事件。
- **C：** 錯誤。Delivery time 受 retry 與網路延遲影響，不等同 object mutation order，不能拿來覆寫版本狀態。
- **D：** 錯誤。Sequencer 的比較範圍不是跨所有 object 的全域順序；不同 keys 不應共用一個簡單序號。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon S3 event notification ordering and duplicate delivery](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)

### 練習題 4｜SAA｜轉碼工作 queue、visibility 與 DLQ

熱門活動同時上傳上萬支影片，部分損壞檔案每次都讓 worker 失敗。團隊需要平滑吸收 burst，不能讓 poison jobs 無限重試或阻塞正常影片。哪個方案最好？

A. 把已驗證工作放入 durable queue，依處理時間設定 visibility/timeout、限制 workers，超過重試門檻送 DLQ 並修復後選擇性 redrive
B. 每天自動把 DLQ 全部搬回 source queue，不需分類失敗原因
C. 把 visibility timeout 設短於正常轉碼時間，讓多個 workers 同時處理以加速
D. 上傳 HTTP request 內同步完成轉碼，失敗就讓 client 重送整個影片

**答案：A**

- **A：** 正確。Visibility 應涵蓋一般處理時間並和 worker timeout/heartbeat 協調；過短會重複交付，過長會延後失敗重試，DLQ 則隔離 poison jobs。
- **B：** 錯誤。未修正 poison input 或程式錯誤便全面 redrive，會重建相同 failure storm；應保留原因並選擇性重播。
- **C：** 錯誤。Visibility 過短會在第一個 worker 尚未完成時讓 message 再度可見；需要長工作時應使用 heartbeat 或 ChangeMessageVisibility 延長。
- **D：** 錯誤。同步長工作會把 upload availability 與 transcode capacity 綁死，並放大 timeout 與重送成本。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon SQS standard queues provide at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

### 練習題 5｜SAP｜MediaConvert CreateJob 冪等性

Orchestrator 呼叫 AWS Elemental MediaConvert `CreateJob` 後逾時，無法知道 job 是否已建立。直接重試有時產生第二個相同轉碼並重複計費。應如何修正？

A. 每次 retry 都產生新的隨機 ClientRequestToken，以免 MediaConvert 拒絕請求
B. 從 source object version、output profile 與邏輯 operation 產生穩定 ClientRequestToken，保存 job identity/result，重試時重用
C. 把 S3 event ID 當作 MediaConvert 已保證 exactly-once job creation 的證明
D. 允許兩個 jobs 完成後再依 output filename 刪除其中一份

**答案：B**

- **A：** 錯誤。新 token 代表新 request，會失去 CreateJob 的冪等保護，正是重複工作的來源。
- **B：** 正確。MediaConvert 支援 request token 冪等性；穩定 operation identity 與持久化 job state 可處理「成功但 response 遺失」。
- **C：** 錯誤。S3 通知與 MediaConvert API 是兩個 delivery boundary；notification ID 不會自動成為 downstream API 的冪等 token。
- **D：** 錯誤。事後刪檔不能回收已執行的轉碼成本，也可能在 completion race 中破壞正確 output。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Elemental MediaConvert request idempotency](https://docs.aws.amazon.com/mediaconvert/latest/apireference/idempotency.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)

### 練習題 6｜SAP｜MediaConvert queue 與 capacity 分層

平台有兩類工作：付費直播活動結束後 15 分鐘內要產出 VOD；舊片庫則可在 48 小時內批次重轉。單一 queue 的 archival surge 常讓 premium jobs 排隊。哪個設計最好？

A. 為偶發 premium burst 購買最大 reserved queue，但不先確認 reserved queue 支援的功能與一年期容量承諾
B. 將 premium 與 archival jobs 放在不同 on-demand queues，並在各 queue 內設定 job priority；若長期穩定工作量與功能限制合適，再為該類工作評估 reserved queue
C. 保留單一 queue 並只提高 premium job priority；priority 會跨所有 queues 全域排序且自動增加帳號容量
D. 建立兩個 queues，卻把所有 jobs 都提交到 default queue；queue 名稱本身會自動隔離 backlog

**答案：B**

- **A：** 錯誤。Reserved queue 有購買承諾與功能限制；未量測的偶發尖峰通常應先以 on-demand queues、queue hopping 或配額規劃處理。
- **B：** 正確。Queue 分離先隔開 SLA 與 backlog；priority 只在同一 queue 內排序。Reserved queue 適合可預測負載且有功能/承諾邊界，不是自動的 burst capacity。
- **C：** 錯誤。Job priority 只比較同一 queue 中的工作，不會跨 queue 建立全域順序，也不會提高 service quota 或可用容量。
- **D：** 錯誤。隔離取決於 CreateJob 指向的 queue 及其容量；只建立資源但仍提交到同一 queue 不會改變排程。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Working with AWS Elemental MediaConvert queues](https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-queues.html)、[Setting job priority in AWS Elemental MediaConvert](https://docs.aws.amazon.com/mediaconvert/latest/ug/setting-the-priority-of-a-job.html)、[Working with reserved queues in AWS Elemental MediaConvert](https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-reserved-queues.html)

### 練習題 7｜SAA｜CloudFront 私有 origin 與訂閱者授權

轉碼輸出存放於 S3，只有付費訂閱者可播放。安全要求 viewer 不能直接走 S3 URL，訂閱到期後的授權也不能永久有效。哪個組合最合理？

A. 使用 signed URL，但同時保留 public S3 website endpoint 供舊 client 使用
B. 只設定 OAC，並把它當作 end-user subscription database
C. 把 S3 objects 設 public-read，再以隨機長 key 隱藏影片
D. S3 origin 保持私有並使用 OAC；應用驗證訂閱後發短效 CloudFront signed URL 或 signed cookie

**答案：D**

- **A：** 錯誤。Public website endpoint 仍提供旁路，即使 CloudFront URL 已簽名，未授權者也能直接取得物件。
- **B：** 錯誤。OAC 不知道終端使用者的訂閱狀態，它只是限制哪個 CloudFront distribution 可讀取 origin。
- **C：** 錯誤。Obscurity 不會阻止 URL 被分享或從 log 洩漏，且 public origin 可繞過所有 viewer authorization。
- **D：** 正確。OAC 解決 CloudFront 到 origin 的授權；signed URL/cookie 解決 viewer 到 CloudFront 的限時內容授權，兩者責任不同。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Restrict access to an Amazon S3 origin with CloudFront OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)、[Serve private content with CloudFront signed URLs and signed cookies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html)

### 練習題 8｜SAA｜影音 source 與 rendition 的生命週期分層

Master files 依法保存七年且可能重新轉碼；熱門 renditions 必須毫秒存取，過季 renditions 幾乎不再觀看。團隊打算把所有 objects 上傳一天後移到最便宜 archive class。哪個修正最好？

A. Masters、manifests、thumbnails 與 active renditions 共用同一 lifecycle，方便管理
B. 所有輸出直接進 archive，播放請求發生時再等待 restore
C. 依資料角色與 retrieval SLA 分開 lifecycle；保留 master，hot renditions 用即時類別，冷資料依最短保存與 restore 成本後轉層
D. 刪除 master，只保留目前 1080p rendition，因未來可由 manifest 還原原片

**答案：C**

- **A：** 錯誤。不同 artifacts 的存取頻率、重建能力與法定保留不同，單一規則會造成過度成本或不可接受 restore latency。
- **B：** 錯誤。Archive retrieval 需要時間且有費用，不適合題目要求的熱門影片即時播放。
- **C：** 正確。Storage class 選擇應由 access pattern、minimum duration、retrieval time/cost 與可重建性決定，而不是只比較每 GiB 單價。
- **D：** 錯誤。Lossy rendition 與 manifest 無法重建原始 master；這也違反七年保存與未來新 codec 的 reprocessing 需求。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)、[Managing the lifecycle of Amazon S3 objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

### 練習題 9｜SAP｜媒體 pipeline 的端到端可觀測與安全 redrive

Operations 經常收到「上傳成功但不能播放」，目前只看 S3 bucket size。團隊需要定位到失敗 stage，並在修復後安全重跑。下列哪些兩項最重要？（選兩項）

A. 以 object version、queue message、MediaConvert job/profile、output validation 與 playback URL 建立 correlation ID 與狀態軌跡
B. 監控 queue age、job failure、DLQ 與 subscriber probe；修正根因後以同一冪等 operation identity 選擇性 redrive
C. 只監控 CloudFront request count；有 request 就代表 rendition 一定可播放
D. 每天重新提交所有 master files，以 eventual success 取代個別故障分析
E. 把 S3 `ObjectCreated` 視為 end-to-end 成功，因 source 已可靠保存

**答案：A、B**

- **A：** 正確。跨 stage correlation 讓人能回答某個 source 目前在哪一步、用了哪個 profile、產物是否經驗證，而非只看分散服務指標。
- **B：** 正確。Age/failure/DLQ 揭露處理健康，subscriber probe 驗證外部結果；穩定 token 避免 redrive 建立第二個 billable job。
- **C：** 錯誤。Request count 不包含 output correctness 或授權結果；使用者也可能反覆請求一個失敗的 URL。
- **D：** 錯誤。全面 replay 會重複成功工作、增加費用並掩蓋 poison input；應針對失敗 operation 安全 redrive。
- **E：** 錯誤。Source 上傳完成只代表 ingest 成功；queue、transcode、packaging、authorization 或 delivery 仍可能失敗。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon S3 event notification ordering and duplicate delivery](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html)、[Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[AWS Elemental MediaConvert request idempotency](https://docs.aws.amazon.com/mediaconvert/latest/apireference/idempotency.html)

### 練習題 10｜SAP｜新建影音服務的現行服務與私有交付

公司在 2026 年設計全新的 VOD pipeline，要求 managed file transcoding 不因 retry 重複計費，且影片只能由已授權 viewer 經 CDN 取得。下列哪些兩項符合要求？（選兩項）

A. 只使用 CloudFront signed URL，S3 同時允許匿名 direct read 以相容舊 client
B. 使用 AWS Elemental MediaConvert，為同一邏輯 job 重用穩定 ClientRequestToken 並保存 job state
C. 建立新的 Amazon Elastic Transcoder pipeline，output bucket 設 public-read
D. S3 origin 使用 OAC 保持私有，viewer authorization 使用短效 CloudFront signed URL/cookie
E. 使用 MediaConvert，但每次 retry 產生新 token，因新 token 可提高可用性

**答案：B、D**

- **A：** 錯誤。只要 S3 仍匿名可讀，未授權者就能繞過 signed viewer path，CDN 授權形同可選。
- **B：** 正確。MediaConvert 是目前的 managed file-transcoding 選項之一，request token 與持久化 operation state 用來處理 ambiguous retry。
- **C：** 錯誤。Elastic Transcoder 已於 2025-11-13 停止支援，不應用於 2026 新架構；public output 也破壞私有交付。
- **D：** 正確。OAC 封閉 direct-origin path；signed URL/cookie 則把觀看權限與時間/資源範圍綁定到 CloudFront viewer request。
- **E：** 錯誤。新 token 會被視為新 CreateJob request，無法防止相同 source/profile 被重複處理與計費。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Support for Amazon Elastic Transcoder ended November 13, 2025](https://aws.amazon.com/blogs/media/support-for-amazon-elastic-transcoder-ending-soon/)、[AWS Elemental MediaConvert request idempotency](https://docs.aws.amazon.com/mediaconvert/latest/apireference/idempotency.html)、[Restrict access to an Amazon S3 origin with CloudFront OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)、[Serve private content with CloudFront signed URLs and signed cookies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「S3保存source/output，event觸發queue/batch轉檔，CloudFront edg…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「影音平台需要大物件ingest、transcode、全球delivery與成本控制。」，所以「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」能直接滿足它；若constraint改成「Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」。替代方案「Media services可降低自建轉碼複雜度；自建GPU提供特殊codec控制。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「影音平台需要大物件ingest、transcode、全球delivery與成本控制。」，排除會導致「Origin直接服務全球下載，或轉檔job沒有idempotency造成重複成本。」的選項，再選「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「S3保存source/output，event觸發queue/batch轉檔，CloudFront edge delivery並用signed URL。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「move bytes once, transform asynchronously, serve from the edge」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 100 章　Case Study：金融多帳號環境

金融組織需強身份、不可變稽核、網路分段、資料加密與一致guardrails。

## 走進一次完整架構會議：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：五十個產品團隊受監管，必須證明所有帳號CloudTrail、加密與備份符合政策。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：金融組織需強身份、不可變稽核、網路分段、資料加密與一致guardrails。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Control Tower如何接手工作，再看AWS Organizations何時更合適，最後用設定與考題驗證「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：五十個產品團隊受監管，必須證明所有帳號CloudTrail、加密與備份符合政策。

商業需求與不能妥協的限制
          ▼
[AWS Control Tower：主要責任]
          │ 建立與治理符合best practices的multi-account landing zone。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Organizations：集中建立accounts、OU、政策與consolidated billing。
  · AWS Security Hub：集中標準化security findings並執行security standards checks。
  · AWS KMS：管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
可移植原則：governance must preserve both prevention and recovery access

失敗時先找：Security tooling全在management account，或SCP阻止incident response role。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問AWS Control Tower有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Control Tower和AWS Organizations並不是兩個任意的產品名稱。前者適合本章，是因為「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」直接回應了眼前的問題；後者描述的「分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Security tooling全在management account，或SCP阻止incident response role。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「governance must preserve both prevention and recovery access」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 |

## 把全圖套進一個具體案例

**場景：** 五十個產品團隊受監管，必須證明所有帳號CloudTrail、加密與備份符合政策。

1. 故事的起點：五十個產品團隊受監管，必須證明所有帳號CloudTrail、加密與備份符合政策。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Control Tower負責「建立與治理符合best practices的multi-account landing zone。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Organizations、AWS Security Hub、AWS KMS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Security tooling全在management account，或SCP阻止incident response role。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Control Tower

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：金融組織需強身份、不可變稽核、網路分段、資料加密與一致guardrails。
- **具體例子／邊界：** 在「五十個產品團隊受監管，必須證明所有帳號CloudTrail、加密與備份符合政策。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Organizations

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Security tooling全在management account，或SCP阻止incident response role。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：governance must preserve both prevention and recovery access。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### envelope encryption

先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### data key

實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### drift

實際resource設定與IaC宣告狀態不同，常由console手動修改或外部automation造成。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

## 回到 AWS：Components、功用與責任邊界

### AWS Control Tower

- **功用：** 建立與治理符合best practices的multi-account landing zone。
- **底層機制：** 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。
- **關鍵設定：** landing zone Regions、OU、controls、Account Factory/AFT、log archive、audit account與drift repair。
- **選擇時機：** 快速建立一致account vending與preventive/detective/proactive controls。
- **替換時機：** 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

### AWS Security Hub

- **功用：** 集中標準化security findings並執行security standards checks。
- **底層機制：** 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。
- **關鍵設定：** standards/controls、central configuration、aggregator Region、automation rules與EventBridge。
- **選擇時機：** SOC需要跨帳號單一finding queue與compliance view。
- **替換時機：** 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。

### AWS KMS

- **功用：** 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
- **底層機制：** Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
- **關鍵設定：** key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- **選擇時機：** S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。
- **替換時機：** 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。

## 考前與實作時再查：設定操作手冊

### AWS Control Tower：逐項設定說明

#### `landing zone Regions`

- **控制什麼：** `landing zone Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Control Tower前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `OU`

- **控制什麼：** `OU`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `controls`

- **控制什麼：** `controls`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `Account Factory/AFT`

- **控制什麼：** `Account Factory/AFT`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `log archive`

- **控制什麼：** `log archive`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `audit account`

- **控制什麼：** `audit account`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `drift repair`

- **控制什麼：** `drift repair`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

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

### AWS Security Hub：逐項設定說明

#### `standards/controls`

- **控制什麼：** `standards/controls`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「SOC需要跨帳號單一finding queue與compliance view。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Security Hub以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `central configuration`

- **控制什麼：** `central configuration`是一組可版本化的engine/runtime參數，會改變AWS Security Hub的實際process行為。
- **何時需要：** 當需求符合「SOC需要跨帳號單一finding queue與compliance view。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `aggregator Region`

- **控制什麼：** `aggregator Region`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `automation rules`

- **控制什麼：** `automation rules`把AWS Security Hub與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `EventBridge`

- **控制什麼：** `EventBridge`把AWS Security Hub與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

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

## 讀到這裡，請用自己的話說一次

1. AWS Control Tower的責任：建立與治理符合best practices的multi-account landing zone。
2. 底層機制：在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。
3. 第一個要看的設定：landing zone Regions、OU、controls、Account Factory/AFT、log archive、audit account與drift repair。
4. 選擇邏輯：Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。
5. 不要混淆：AWS Organizations的責任是「集中建立accounts、OU、政策與consolidated billing。」；它不會自動取代AWS Control Tower。
6. 替換訊號：高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。
7. 最常見錯法：Security tooling全在management account，或SCP阻止incident response role。
8. 可移植原則：governance must preserve both prevention and recovery access。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 | 快速建立一致account vending與preventive/detective/proactive controls。 | 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 | SOC需要跨帳號單一finding queue與compliance view。 | 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 | S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。 | 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。 | 只有當題目條件明確改變時才可能合理。 | Security tooling全在management account，或SCP阻止incident response role。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。」之間做選擇。
- 認得常考設定：landing zone Regions、OU、controls、Account Factory/AFT、log archive、audit account與drift repair。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAP｜Landing zone 的 account 與 OU 責任分離

受監管金融公司有 50 個產品團隊。現有設計把 Security Hub、稽核 log、shared network 與 production workloads 全放在 Organizations management account，理由是「這樣最中央化」。哪個重構最合理？

A. 將所有 security tools 留在 management account，因 SCP 可完整限制 management account 內的 principals
B. 保留所有資源在單一 account，只用 tags 區分 team 與 environment
C. 每個團隊建立獨立 account，但不定義 OU、account vending、baseline 或 owner
D. 使用 Control Tower/Organizations 建立 workload OUs 與獨立 log archive、security、shared-services accounts，management account 僅做組織管理

**答案：D**

- **A：** 錯誤。SCP 不限制 management account 本身；因此不應把一般 production/security workloads 的安全性建立在此假設上。
- **B：** 錯誤。Tags 有助分類與成本，不提供 account-level blast-radius、quota、billing 與 administrative boundary。
- **C：** 錯誤。只有 account 數量沒有 governance lifecycle，會產生不一致 baseline、孤兒帳號與難以驗證的例外。
- **D：** 正確。Account boundary 可降低 blast radius 並分離 ownership；管理帳號應減少人員與 workload，以免組織控制面成為日常營運依賴。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)、[AWS Organizations service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 2｜SAA｜SCP 是 permission ceiling 而非授權來源

Security OU 套用 SCP，內容允許 incident responder 執行 EC2 與 IAM actions。Responder role 本身沒有任何 IAM permissions，實際操作仍被拒絕。哪個解釋與修正正確？

A. SCP 的 Allow 應直接授權；等待數小時讓 permissions propagate 即可
B. SCP 只界定 member account 可取得的最大權限；仍要由 identity/resource policy 授權 responder，且不能有適用的 explicit deny
C. 移除所有 SCP，因 SCP 與 incident response 永遠無法共存
D. 把 SCP 掛到 management account，便能讓 member-account role 繼承管理權

**答案：B**

- **A：** 錯誤。SCP 不授予 permissions；Allow 只表示該 action 沒被這層 permission ceiling 排除。
- **B：** 正確。Effective permission 是 SCP、IAM、resource policy、permission boundary 等共同結果，實際 access 仍需正向 grant。
- **C：** 錯誤。SCP 可與受控 recovery role 共存；做法是精確設計 deny、測試 effective access 並保留經核准的 emergency path。
- **D：** 錯誤。Management account 不受 SCP 約束，且把 policy 掛在它上面不會替 member role 建立 identity permission。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Organizations service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 3｜SAP｜Preventive、detective 與 proactive controls

公司有三種要求：禁止停用核心 log、持續找出未加密 bucket、在 CloudFormation 建立資源前拒絕違規模板。應如何選擇 Control Tower control 類型？

A. 三者全部使用 detective controls，因發現後再修復等同預防
B. 不可發生的動作用 preventive；持續評估用 detective；provision 前檢查 IaC 用 proactive，並依 scope 驗證效果
C. CloudTrail logging 本身就是 proactive template validation，不需其他 control
D. 所有 controls 一次套用全組織，不需先測試 Region、resource 或既有例外

**答案：B**

- **A：** 錯誤。Detective control 在變更後評估，不會阻止 prohibited action；要求「不可發生」時需 preventive mechanism。
- **B：** 正確。三種類型在不同時間點介入：事前阻止、事後/持續偵測，以及 IaC 建立前驗證，不能互相混稱。
- **C：** 錯誤。Logging 提供 evidence，不等同在 resource provisioning 前驗證 template 是否符合 policy。
- **D：** 錯誤。Control 可能影響既有 workload 與 recovery path；應以 pilot OU、相容性與 exception lifecycle 安全部署。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Control Tower preventive, detective, and proactive controls](https://docs.aws.amazon.com/prescriptive-guidance/latest/designing-control-tower-landing-zone/controls.html)

### 練習題 4｜SAP｜Organization trail、完整性驗證與 WORM 保留

稽核要求所有 member accounts 的活動集中到 log archive account，保留七年且 privileged workload admin 不能刪除。團隊只開啟 CloudTrail log-file validation，便宣稱 logs 已不可變。哪個方案正確？

A. 讓每個 workload account 擁有自己的 trail/bucket 並自行設定 expiration
B. 建立 organization trail 到受限 log-archive bucket；分離管理權，啟用 validation 偵測竄改，並以 S3 Object Lock/retention 實作 WORM
C. 只收集 Control Tower console events，因它們包含所有 member account data events
D. 保留現況，因 log-file validation 會阻止具有 S3 delete 權限的人刪除 object

**答案：B**

- **A：** 錯誤。Workload admin 若控制 trail、bucket 與 lifecycle，就能停用或縮短保留，無法形成獨立 evidence boundary。
- **B：** 正確。Organization trail 解決集中收集；validation 提供完整性偵測；Object Lock 與受保護 ownership 才處理不可刪除的 retention。
- **C：** 錯誤。Management events 與 data events 的範圍不同，是否收集必須依 audit requirement 明確設定。
- **D：** 錯誤。Validation 可揭露 log file 被修改或刪除的跡象，但本身不撤銷 S3 delete capability，也不是 WORM control。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Creating an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[Logging in AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/about-logging.html)、[Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

### 練習題 5｜SAP｜KMS key administration 與 usage 分離

產品管理員需要操作加密資料，但法規禁止他們自行修改 key policy 後授予自己額外 decrypt 權限。目前同一 Admin role 同時擁有 `kms:*` 與資料庫管理權。應如何調整？

A. 分離 key administrators 與 key users，精確設定 key policy/grants/service principals，並測試實際 decrypt 與 restore path
B. 每天改變 KMS alias 名稱，視為底層 cryptographic key 已完成 rotation 與權限重置
C. 只在 IAM policy 加入 Allow；即使 key policy 沒有有效授權路徑也一定能使用 key
D. 保留同一 admin role 的完整 key 與資料權限，因 CloudTrail 已可取代 separation of duties

**答案：A**

- **A：** 正確。Administration 與 cryptographic use 是不同責任；key policy、grants、IAM 與 resource owner 必須共同形成 least-privilege path。
- **B：** 錯誤。Alias 是可變名稱，更新 alias 不等同 key material rotation，也不會自動重設已授權 principals。
- **C：** 錯誤。KMS authorization 必須考慮 key policy；單有 IAM Allow 不保證 principal 有可用的 key access。
- **D：** 錯誤。Audit log 有助偵測，不會阻止同一人修改 policy 後使用 key；預防與事後 evidence 不能互換。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS KMS key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 6｜SAP｜AWS Backup Vault Lock Compliance mode 與 restore evidence

Backup dashboard 顯示所有 jobs 成功，團隊因此向稽核員保證 ransomware 後一定能恢復。稽核員要求 recovery points 在 retention 期間不可刪除，且每季證明應用可恢復。哪個做法最好？

A. 使用 Vault Lock Governance mode，因有足夠 IAM 權限的管理員也永遠無法移除 governance lock
B. 只複寫到另一 Region；replica 一定不會同步 logical corruption 或惡意刪除，所以不需要保留歷史 recovery points
C. 把 completed backup job 當作應用可恢復的證明，不必實際測試 decrypt、dependency 與 business probe
D. 先驗證 KMS、roles、retention 與 restore；再設定 Vault Lock Compliance mode 的 min/max retention 與 grace time，並在 grace time 結束前完成復原演練

**答案：D**

- **A：** 錯誤。Governance mode 能防止非預期操作，但具足夠權限者仍可移除；不符合「特權管理員在 retention 內也不能刪除」的要求。
- **B：** 錯誤。Replication 與版本化 backup 解決不同問題；邏輯錯誤或惡意動作可能複寫，不能取代具歷史保留的 recovery points。
- **C：** 錯誤。Backup success 只證明 recovery point 建立，沒有證明能解密、啟動 dependencies、符合 RTO 並通過應用驗證。
- **D：** 正確。Compliance mode 在 grace time 結束後形成不可移除的 retention 邊界；因此必須先驗證設定與 restore path，再以定期 restore testing證明可恢復。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Backup Vault Lock modes](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html#vault-lock-modes)、[AWS Backup restore testing and validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

### 練習題 7｜SAP｜AWS Security Hub CSPM delegated administrator 與 remediation 權限邊界

中央資安團隊要透過 AWS Security Hub CSPM 聚合整個 Organizations 的 posture findings，但不希望日常登入 management account，也不應自動取得所有 workload 的永久 AdministratorAccess。哪個設計最佳？

A. 假設 delegated administrator 自動取得任意 workload resource 的修改權，不需另建 remediation permissions
B. 在每個 member account 建立相同永久 IAM user 與 access key
C. 為支援的安全服務設定 delegated administrator，搭配 scoped cross-account remediation roles、短期 sessions 與 audit
D. 共用 management-account root credentials 給所有 security analysts

**答案：C**

- **A：** 錯誤。服務 delegated admin 的管理能力有明確 scope，不等同對每個 member resource 的無限制 AdministratorAccess。
- **B：** 錯誤。分散長期 users/keys 增加 rotation、offboarding 與 credential leakage 風險，也難以集中治理。
- **C：** 正確。Delegated administration 把服務管理移出 management account，實際 remediation 再經明確的 role permissions 與可稽核 session。
- **D：** 錯誤。Root credentials 不適合日常使用，更不應共享；這會破壞個人 attribution 與 least privilege。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Integrating AWS Security Hub CSPM with AWS Organizations](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-accounts-orgs.html)、[AWS Organizations service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 8｜SAP｜Transit Gateway stateful inspection 對稱路由

公司透過 Transit Gateway 將多個 workload VPC 的 egress 導向 inspection VPC。Flow log 顯示 request 通過 firewall appliance，但 return traffic 走另一條 attachment，stateful session 被丟棄。哪個修正最合適？

A. 所有 TGW route tables 只放相同 `0.0.0.0/0`，假設 return path 自然會對稱
B. 移除備援 appliance，讓單一路徑簡化為 single point of failure
C. 只在 firewall ENI 加入更寬的 security group，routing 不需變更
D. 設計 workload/inspection TGW route tables 與 appliance mode，驗證 forward/return 都經同一 stateful inspection path

**答案：D**

- **A：** 錯誤。相同 default route 不代表各 attachment 與 AZ 的 forward/return 選擇一致；必須明確設計 route domains。
- **B：** 錯誤。單一路徑可能暫時降低不對稱，但破壞可用性；正確做法是讓備援拓撲也維持 flow symmetry。
- **C：** 錯誤。Security group 只決定允許與否，無法把未經 appliance 的 return packet 改到正確 attachment。
- **D：** 正確。Stateful appliance 需要雙向 flow 經相同處理節點；TGW appliance mode 與 route-table segmentation 是核心機制。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Transit Gateway appliance-mode routing scenario](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-appliance-scenario.html)

### 練習題 9｜SAP｜Break-glass access 與例外生命週期

Identity provider 曾中斷兩小時，incident team 無法登入 AWS。公司要建立 emergency access，但不能變成永久後門。下列哪些兩項最重要？（選兩項）

A. 對 emergency 使用與 policy exception 設即時 alert、事後 review、到期撤銷與週期性 access test
B. 事故發生後再臨時建立 break-glass user，因平時不存在最安全
C. 預先建立並定期演練獨立保護的 emergency roles/credentials，使用強驗證、明確啟用流程與可追蹤個人身分
D. 給 incident team 永久 organization-wide AdministratorAccess，避免審批延誤
E. 讓 emergency role 永久豁免所有 SCP、CloudTrail 與告警，避免任何 control 影響復原

**答案：A、C**

- **A：** 正確。Alert、expiry 與 post-incident review 讓例外有生命週期，防止暫時權限沉澱成日常常駐權限。
- **B：** 錯誤。建立新 principal 通常也需要原本已失效的管理路徑；沒有預先測試就不能當 recovery mechanism。
- **C：** 正確。IdP 故障時才建立 credentials 太晚；必須事前準備、隔離保存並以 drill 驗證真的能登入與執行必要 action。
- **D：** 錯誤。永久廣泛權限擴大 insider 與 credential compromise 風險；emergency access 應最小化、短效且受監督。
- **E：** 錯誤。Recovery role 可能需要精確例外，但不能關閉全部 evidence 與偵測；否則緊急路徑成為不可見的攻擊路徑。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Set up emergency access to the AWS Management Console](https://docs.aws.amazon.com/singlesignon/latest/userguide/emergency-access.html)、[AWS Organizations service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 10｜SAP｜Baseline control 的安全 rollout

新 SCP/control 要禁止 public storage，但組織中有舊帳號與經核准的 recovery workflow。公司必須同時防止違規與避免 control rollout 鎖死復原。下列哪些兩項是必要措施？（選兩項）

A. 建立獨立測試過的 break-glass 與具 owner/理由/期限的 exception path，持續偵測到期與濫用
B. 只保留一個不受監控的 broad administrator exception，不需要 preventive control
C. 第一天直接套用 root OU，production outage 再由各團隊人工修復
D. 先在 pilot OU 與代表性 accounts 部署，驗證 effective permissions、compliance evidence、service 相容性與 rollback
E. 只檢查 policy JSON 可成功儲存；不需實際測試 denied action 與 recovery action

**答案：A、D**

- **A：** 正確。Recovery path 與 exception lifecycle 必須事前存在並被監控，才能兼顧防止與可恢復性。
- **B：** 錯誤。只有廣泛例外會破壞 non-bypassable baseline，且沒有理由、期限與 evidence 便無法治理。
- **C：** 錯誤。Root-wide big-bang 讓錯誤 deny 同時影響所有 accounts，缺少可控 blast radius 與 learning loop。
- **D：** 正確。Pilot rollout 以真實 effective behavior 驗證 control，而不是只驗證 syntax；通過後再逐 OU 擴大。
- **E：** 錯誤。Policy 被接受只表示 control plane 收到設定，不代表 data-plane access、service-linked roles 或 emergency workflow 正確。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Control Tower preventive, detective, and proactive controls](https://docs.aws.amazon.com/prescriptive-guidance/latest/designing-control-tower-landing-zone/controls.html)、[AWS Organizations service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[Set up emergency access to the AWS Management Console](https://docs.aws.amazon.com/singlesignon/latest/userguide/emergency-access.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Control Tower landing zone、Identity Center、central se…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「金融組織需強身份、不可變稽核、網路分段、資料加密與一致guardrails。」，所以「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」能直接滿足它；若constraint改成「分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」。替代方案「分散治理可加快團隊，但底線controls必須不可繞過且有例外流程。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Security tooling全在management account，或SCP阻止incident response role。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「金融組織需強身份、不可變稽核、網路分段、資料加密與一致guardrails。」，排除會導致「Security tooling全在management account，或SCP阻止incident response role。」的選項，再選「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAP-1.2 Prescribe security controls。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Control Tower landing zone、Identity Center、central security/log accounts、SCP與inspection network。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「governance must preserve both prevention and recovery access」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 101 章　Case Study：Hybrid Enterprise Migration

企業migration期間要同時維持on-premises與AWS，dependency、DNS、identity與network會長期共存。

## 走進一次完整架構會議：先從故事開始

把鏡頭拉到一個真實的production現場：兩個資料中心一年內關閉，四百應用分批搬移且部分需主機大型機。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：企業migration期間要同時維持on-premises與AWS，dependency、DNS、identity與network會長期共存。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。AWS Direct Connect是這一章的入口，AWS Migration Hub用來畫出邊界；主要方向「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：兩個資料中心一年內關閉，四百應用分批搬移且部分需主機大型機。

商業需求與不能妥協的限制
          ▼
[AWS Direct Connect：主要責任]
          │ 提供從客戶網路到AWS的專用網路connection。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Migration Hub：集中追蹤migration portfolio、waves與多工具進度。
  · AWS Application Migration Service：把physical、virtual或cloud servers以block replication搬到EC…
  · AWS DMS：在線搬移或持續複寫databases/data stores，降低downtime。
可移植原則：migration architecture is temporary production architecture

失敗時先找：CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問AWS Direct Connect有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Direct Connect和AWS Migration Hub並不是兩個任意的產品名稱。前者適合本章，是因為「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」直接回應了眼前的問題；後者描述的「Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「migration architecture is temporary production architecture」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Direct Connect | 提供從客戶網路到AWS的專用網路connection。 | 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。 |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 |
| AWS DMS | 在線搬移或持續複寫databases/data stores，降低downtime。 | Replication instance/serverless task做full load與CDC，讀source logs並寫target。 |

## 把全圖套進一個具體案例

**場景：** 兩個資料中心一年內關閉，四百應用分批搬移且部分需主機大型機。

1. 故事的起點：兩個資料中心一年內關閉，四百應用分批搬移且部分需主機大型機。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Direct Connect負責「提供從客戶網路到AWS的專用網路connection。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Migration Hub、AWS Application Migration Service、AWS DMS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Direct Connect

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：企業migration期間要同時維持on-premises與AWS，dependency、DNS、identity與network會長期共存。
- **具體例子／邊界：** 在「兩個資料中心一年內關閉，四百應用分批搬移且部分需主機大型機。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Migration Hub

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：migration architecture is temporary production architecture。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### migration

把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### refactor

重構application與data boundaries以使用cloud-native架構；潛在收益高，時間、風險與testing需求也最高。

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### rehost

盡量不改application，把server搬到cloud IaaS；速度快但保留多數技術債與營運模式。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### VLAN

Virtual LAN，在共享實體link上以標記隔離Layer-2 traffic；Direct Connect VIF配置會使用VLAN ID。

### BGP

Border Gateway Protocol，在network peers間交換可達prefix與path資訊；DX/VPN常用它動態學習routes。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### AWS Direct Connect

- **功用：** 提供從客戶網路到AWS的專用網路connection。
- **底層機制：** 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。
- **關鍵設定：** connection/location、hosted/dedicated、VLAN、BGP ASN、private/public/transit VIF、DX Gateway與LAG。
- **選擇時機：** 持續大量資料、穩定latency、private path與混合企業網路。
- **替換時機：** 部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。

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

### AWS DMS

- **功用：** 在線搬移或持續複寫databases/data stores，降低downtime。
- **底層機制：** Replication instance/serverless task做full load與CDC，讀source logs並寫target。
- **關鍵設定：** source/target endpoints、replication instance/serverless、full-load/CDC task、table mappings、LOB與validation。
- **選擇時機：** homogeneous/heterogeneous database migration與ongoing replication。
- **替換時機：** schema/code conversion使用SCT；一般files用DataSync；DMS不自動修正所有data types。

## 考前與實作時再查：設定操作手冊

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

### AWS DMS：逐項設定說明

#### `source/target endpoints`

- **控制什麼：** `source/target endpoints`指定AWS DMS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `replication instance/serverless`

- **控制什麼：** `replication instance/serverless`設定AWS DMS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「homogeneous/heterogeneous database migration與ongoing replication。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `full-load/CDC task`

- **控制什麼：** `full-load/CDC task`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「homogeneous/heterogeneous database migration與ongoing replication。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS DMS的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `table mappings`

- **控制什麼：** `table mappings`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「homogeneous/heterogeneous database migration與ongoing replication。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS DMS的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `LOB`

- **控制什麼：** `LOB`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `validation`

- **控制什麼：** `validation`定義AWS DMS用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

## 讀到這裡，請用自己的話說一次

1. AWS Direct Connect的責任：提供從客戶網路到AWS的專用網路connection。
2. 底層機制：實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。
3. 第一個要看的設定：connection/location、hosted/dedicated、VLAN、BGP ASN、private/public/transit VIF、DX Gateway與LAG。
4. 選擇邏輯：建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。
5. 不要混淆：AWS Migration Hub的責任是「集中追蹤migration portfolio、waves與多工具進度。」；它不會自動取代AWS Direct Connect。
6. 替換訊號：部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。
7. 最常見錯法：CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。
8. 可移植原則：migration architecture is temporary production architecture。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Direct Connect | 提供從客戶網路到AWS的專用網路connection。 | 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。 | 持續大量資料、穩定latency、private path與混合企業網路。 | 部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。 |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 | 大型migration需要single pane追蹤而不是spreadsheet碎片。 | 它不搬資料本身；server用MGN、database用DMS、files用DataSync。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 | rehost大量servers、低downtime cutover與DR-like migration。 | database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。 |
| AWS DMS | 在線搬移或持續複寫databases/data stores，降低downtime。 | Replication instance/serverless task做full load與CDC，讀source logs並寫target。 | homogeneous/heterogeneous database migration與ongoing replication。 | schema/code conversion使用SCT；一般files用DataSync；DMS不自動修正所有data types。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。 | 只有當題目條件明確改變時才可能合理。 | CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。」之間做選擇。
- 認得常考設定：connection/location、hosted/dedicated、VLAN、BGP ASN、private/public/transit VIF、DX Gateway與LAG。
- 對應官方tasks：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-4.1 Select existing workloads and processes for potential migration；SAP-4.2 Determine the optimal migration approach for existing workloads；SAP-4.3 Determine a new architecture for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAP｜依 dependency 規劃 migration waves

企業要在一年內搬遷 400 個應用。團隊原本依伺服器作業系統分 wave，但第一次 cutover 才發現付款系統仍依賴未搬的 LDAP、batch file share 與下游 mainframe API。下一輪最應先改善什麼？

A. 將所有 applications 改成同一個 cutover weekend，消除 hybrid coexistence
B. 依 application 名稱字母排序，避免團隊對優先順序爭論
C. 建立含 business owner、上下游、identity/network/data dependency、strategy、test、rollback 與共用 foundation 的 wave plan
D. 只使用 network flow discovery，視為所有商業與人工 dependency 的完整證明

**答案：C**

- **A：** 錯誤。Big-bang 會集中 400 個應用的未知風險，且難以在單一窗口完成可靠 rollback。
- **B：** 錯誤。字母順序與技術或業務 dependency 無關，可能再次把上游與下游拆到錯誤 wave。
- **C：** 正確。Migration wave 是暫時 production architecture；必須同時安排 shared services、驗收條件與可逆切換，而不是只搬主機。
- **D：** 錯誤。Flow data 很有價值，但看不到低頻工作、人工流程、授權關係與災難時才啟用的 dependency。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS application portfolio wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)、[AWS large-migration strategy selection](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies)

### 練習題 2｜SAP｜依 workload 條件選擇 migration strategy

Portfolio 內有：即將下線的報表、廠商 SaaS 可替代的 HR 系統、可原樣搬移的 VMware 應用，以及與 mainframe transaction 緊密耦合的核心程式。Architecture board 要求全部 rehost。哪個做法較合理？

A. 所有 mainframe-dependent applications 在期限前全部 refactor，不需先確認介面與 business owner
B. 依 business value、dependency、license、downtime、data gravity 與 target capability，分別評估 retire/retain/repurchase/relocate/rehost/replatform/refactor
C. 所有系統先 rehost，因最少 code change 代表總成本與風險一定最低
D. 把 retain 標記為已完成 migration，無需記錄它對其他已遷移 workloads 的長期 dependency

**答案：B**

- **A：** 錯誤。全面 refactor 時程與風險最高；「依賴 mainframe」本身不足以決定如何切分、保留或替換。
- **B：** 正確。Migration strategy 是每個 workload 的決策，且會隨 discovery 與目標能力更新；沒有單一 R 適用整個 portfolio。
- **C：** 錯誤。Rehost 可能快速，但會保留 license、operating model 與 architecture debt，也不適用即將 retired 或可 repurchase 的系統。
- **D：** 錯誤。Retain 是明確策略，不表示 dependency 消失；共存、connectivity、security 與 eventual exit 仍需 owner 與期限。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS large-migration strategy selection](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies)

### 練習題 3｜SAA｜Direct Connect 的 location-level resilience

關鍵混合服務不能因單一 router、circuit 或 Direct Connect location 故障中斷。現況是在同一 location 的同一 connection 建兩個 VIF，並宣稱已有完整備援。哪個目標架構較正確？

A. 依 maximum-resiliency model 使用不同 DX locations 與冗餘 customer/AWS paths，保留已驗證且容量足夠的 VPN fallback
B. 在同一設施建立一個更大的 LAG，便可承受整個 location 中斷
C. 只建立 Internet VPN，且不做 bandwidth 或 failover test
D. 在同一 physical connection 建更多 VIF，因每個 VIF 都是獨立線路

**答案：A**

- **A：** 正確。不同 locations 加上 customer 與 AWS 端冗餘能涵蓋更多 failure domains；備援路徑必須定期測試。
- **B：** 錯誤。LAG 可增加容量與 connection redundancy，但同一 location 的共通設施故障仍可能同時影響所有 links。
- **C：** 錯誤。VPN 可作備援，但必須確認 throughput、route preference、BGP convergence 與實際 workload failover。
- **D：** 錯誤。多個 VIF 仍共享底層 connection/location failure domain，不會自動成為 physical diversity。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Direct Connect maximum-resiliency model](https://docs.aws.amazon.com/directconnect/latest/UserGuide/max-resiliency-set-up.html)

### 練習題 4｜SAP｜Direct Connect 與傳輸加密的責任邊界

法遵要求 on-premises 到 AWS 的資料全程加密。Network team 說 Direct Connect 是 private circuit，所以 payload 已自動加密。哪個評估與方案最準確？

A. 在資料進入 DX 前終止 TLS，即使後續 trust boundary 仍要求 encryption 也符合規範
B. 正確；只要不經 public Internet，所有 Ethernet/IP payload 就自動加密
C. 啟用 BGP MD5 即可，因它會加密整個 application payload
D. 錯誤；應依 endpoints 與設備選 MACsec、IPsec VPN over DX 或 application TLS，並驗證實際 encrypted path

**答案：D**

- **A：** 錯誤。若規範要求跨越該段 trust boundary 時仍加密，過早 termination 會留下未保護的傳輸區段。
- **B：** 錯誤。Private connectivity 與 cryptographic confidentiality 是不同屬性；DX 本身不代表所有 payload 已加密。
- **C：** 錯誤。BGP authentication 保護 routing session，不提供業務資料的端到端 payload encryption。
- **D：** 正確。加密方法取決於連線型態、支援設備、吞吐與 compliance；設計後還需以 packet/path evidence 驗證。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Encryption in AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/encryption-in-transit.html)

### 練習題 5｜SAA｜Route 53 Resolver 雙向 hybrid DNS

AWS instances 必須解析 `corp.internal` 的 on-premises records；辦公室 clients 也必須解析 Route 53 private hosted zone `apps.aws.internal`。目前兩邊 resolver 互相把所有 queries 轉送，偶爾形成 recursion loop。哪個方案最好？

A. 在 AWS 與 on-prem 建立同名 private zone，期待 resolver 自動合併 records
B. 建立 Route 53 Resolver outbound endpoint 與指定 `corp.internal` 的 forwarding rule，另用 inbound endpoint 讓 on-prem DNS 轉送 `apps.aws.internal`，兩端跨 AZ 並記錄 queries
C. 把兩個 private namespaces 全部複製到 public hosted zone，讓 Internet DNS 統一回答
D. 讓每個 resolver 把 `.` 根網域無條件轉給另一個 resolver，增加可用性

**答案：B**

- **A：** 錯誤。兩個權威來源不會自動 merge，可能產生 split-brain 與不同 client 得到不一致答案。
- **B：** 正確。Inbound 與 outbound endpoints 解決相反方向，conditional rules 明確界定 authority，避免無界互相轉送。
- **C：** 錯誤。Public zone 會洩漏或暴露內部命名，而且不能替代私有 namespace 的 network-aware resolution。
- **D：** 錯誤。雙向 root forwarding 最容易形成 recursion loop；規則應限定 suffix 並保留清楚的 authoritative owner。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Route 53 Resolver for hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)

### 練習題 6｜SAP｜Overlapping CIDR 的隔離與轉譯策略

兩個待遷移事業部都使用 `10.20.0.0/16`，不能立即 renumber。團隊打算把兩邊 VPC attachments 放入同一 Transit Gateway route table，讓 TGW 自動選對目的地。應改成哪個方案？

A. 加入更廣的 `0.0.0.0/0` route，便能消除相同 CIDR 的歧義
B. 優先規劃 renumber；過渡期用 PrivateLink/proxy 暴露特定服務，或以 private NAT 建立不重疊的 translated address domain
C. 保留重疊 routes，改以 security groups 決定 packet 應走哪個 attachment
D. 讓兩邊都 advertise 相同 prefix，依 BGP 當下選中的路徑決定正確事業部

**答案：B**

- **A：** 錯誤。更廣 prefix 的 specificity 較低，不會修復兩個相同更精確 prefix 的 semantic ambiguity。
- **B：** 正確。Renumber 是長期解；PrivateLink 只暴露服務而非完整互連，NAT 則可建立可路由的非重疊地址空間。
- **C：** 錯誤。Security groups 過濾已被 routing 選中的流量，不能告訴 TGW 兩個相同 destination prefix 分別代表誰。
- **D：** 錯誤。相同 prefix 沒有足夠資訊表達 service identity；route selection 可能將流量送往錯誤組織。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Transit Gateway VPC attachment limitations](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html)、[What is AWS PrivateLink?](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)、[Private NAT Gateway for overlapping networks](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/private-nat-gateway.html)

### 練習題 7｜SAP｜Application Migration Service 測試、cutover 與 revert

MGN 顯示 replication lag 接近零，專案經理要直接標記伺服器 finalized 並關閉來源。應用尚未在 AWS 驗證 DNS、license、service account 與 business transaction。哪個流程正確？

A. EC2 instance 狀態為 running 後立即 finalize，其他 dependency 可在日後補測
B. 第一次 launch 直接設為正式 cutover，因 test launch 會中斷持續 replication
C. Replication lag 為零即證明 application 完整可用，可直接 decommission source
D. 先做 non-disruptive test launch 與驗收，修正 launch settings；cutover 後驗證，失敗則 revert，成功才 finalize/decommission

**答案：D**

- **A：** 錯誤。Instance running 是 infrastructure signal，不等同 application accepted；過早 finalize 會縮小 rollback 選項。
- **B：** 錯誤。Test launch 的目的就是在不中斷來源服務下驗證 target，降低正式窗口才發現問題的風險。
- **C：** 錯誤。Block replication 只代表資料複製進度，不能證明 network、identity、license、application consistency 與 business behavior。
- **D：** 正確。MGN 的 test/cutover/revert/finalize 階段提供明確 decision gates；來源只在 business acceptance 後才安全退役。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Application Migration Service cutover, revert, and finalize](https://docs.aws.amazon.com/mgn/latest/ug/revert-finalize-cutover.html)、[AWS application portfolio wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)

### 練習題 8｜SAP｜DMS full load、CDC 與資料驗證

營運資料庫只能停機 20 分鐘。DMS full load 需要 8 小時，而且 source 在此期間仍持續寫入。團隊打算 full load 完成後立刻切換，只比較兩邊 row count。哪個方案較可靠？

A. 使用 full load + CDC，監控 CDC latency，啟用適當 validation，cutover 時 quiesce/final sync 並保留 rollback gate
B. 只要 DMS task 顯示 running，就代表所有資料與 datatype 已完全一致
C. Full load 完成後忽略 source 的後續 changes，因 target 已有大部分資料
D. 只比較總 row count；即使 transformation 或 unsupported datatype 改變內容也可視為相同

**答案：A**

- **A：** 正確。CDC 縮短 outage，validation 與 final-sync gate 則把「task 完成」轉換成可接受的資料遷移證據。
- **B：** 錯誤。Task state 只說明執行狀態，不是資料內容正確與同步到 cutover point 的證明。
- **C：** 錯誤。Full load 期間的持續寫入若沒有 CDC 捕捉，target 會缺少 transactions，切換後產生資料遺失。
- **D：** 錯誤。相同 row count 可能仍有欄位值、encoding、LOB 或 transformation 差異，需使用更完整 validation。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Creating AWS DMS tasks for ongoing replication](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html)、[AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)

### 練習題 9｜SAP｜Hybrid identity 與 directory coexistence

遷移期間，使用者與 service accounts 必須同時存取 on-premises 與 AWS applications。公司不能突然更換所有帳密，也不能讓兩邊出現無關的同名帳號。下列哪些兩項是必要原則？（選兩項）

A. 在 AWS 建立全新 directory，複製相同 usernames，但不建立 trust、sync 或 migration mapping
B. 在第一個 wave 前立即停用 on-prem directory，迫使所有應用完成轉換
C. 依 trust、latency、outage 與 application protocol 選擇 directory integration/migration pattern，並明確保留 authoritative identity source
D. 把所有 human 與 service identity 改成一組共享長期 IAM user access keys
E. 逐 wave 驗證 authentication、group/authorization、service account、DNS 與失敗模式，通過前保留可回復的舊路徑

**答案：C、E**

- **A：** 錯誤。無映射的同名 accounts 會造成不同 security principal 被誤認為同一人，並讓權限與 offboarding 分叉。
- **B：** 錯誤。Premature cutover 會讓尚未驗證的 dependency 同時失效；identity 應與 application wave 協調。
- **C：** 正確。Directory 選擇不是只看服務名稱；必須先定義誰是 authority，以及 link outage 時哪些 authentication flow 仍可工作。
- **D：** 錯誤。共享長期 key 失去個人與 workload attribution，且 IAM user 不是一般企業 directory coexistence 解法。
- **E：** 正確。Identity 是每個 wave 的 production dependency，需以實際 login、group、service-to-service 與 failure test 作驗收。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Migrating Active Directory workloads to AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-microsoft-workloads-aws/migrating-active-directory-workloads.html)

### 練習題 10｜SAP｜伺服器與資料庫 wave 的可逆 cutover

某 wave 同時包含以 MGN rehost 的應用伺服器與以 DMS 搬遷的交易資料庫，停機窗口 20 分鐘。單純 ping 通 EC2 不算成功。下列哪些兩項必須同時納入 cutover gate？（選兩項）

A. DMS CDC/validation 達標後執行 final sync，再以 application probe 確認 target data；未通過則不 decommission source
B. 只驗證 Direct Connect BGP session 為 up，因 network 可達即代表應用與資料完成
C. 只驗證 MGN block replication，因它也保證資料庫 transaction consistency 與 schema compatibility
D. 只驗證 DMS row count，因資料存在便能證明 application binary、DNS 與權限都正確
E. MGN test/cutover 後驗證 network、identity、license、business transaction，並保留 revert/finalize decision

**答案：A、E**

- **A：** 正確。DMS 提供持續資料同步與 validation；final sync 必須和應用停止寫入及 business probe 協調。
- **B：** 錯誤。Connectivity 是必要 dependency，但不證明 target application、directory、database consistency 或 business result。
- **C：** 錯誤。MGN 的 block replication 不取代 database-aware CDC、transaction cutover 與資料驗證。
- **D：** 錯誤。Row count 只覆蓋資料的一小部分，不能推論 compute、DNS、identity 與 application semantics。
- **E：** 正確。MGN 階段處理主機與 launch environment 的可逆切換，且必須用真正 business behavior 驗收。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Application Migration Service cutover, revert, and finalize](https://docs.aws.amazon.com/mgn/latest/ug/revert-finalize-cutover.html)、[Creating AWS DMS tasks for ongoing replication](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html)、[AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)、[Route 53 Resolver for hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollba…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「企業migration期間要同時維持on-premises與AWS，dependency、DNS、identity與network會長期共存。」，所以「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」能直接滿足它；若constraint改成「Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」。替代方案「Big-bang可縮短共存期但集中風險；長期hybrid則增加雙環境營運。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「企業migration期間要同時維持on-premises與AWS，dependency、DNS、identity與network會長期共存。」，排除會導致「CIDR重疊、DNS split horizon錯誤與未發現hard-coded IP阻塞cutover。」的選項，再選「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」。本章對應的代表task包括：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies；SAP-4.1 Select existing workloads and processes for potential migration。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「建立DX/VPN冗餘、hybrid DNS、wave plan、MGN/DMS，逐波驗證並保留rollback。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「migration architecture is temporary production architecture」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 102 章　Case Study：Data Lake 與即時分析

同一平台需接batch/stream、保存raw、治理schema與權限，並支援BI/ML。

## 走進一次完整架構會議：先從故事開始

如果今天由你值班，收到的需求可能是這樣：每秒百萬事件、每日批次ERP資料、分析師與ML團隊需不同權限。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：同一平台需接batch/stream、保存raw、治理schema與權限，並支援BI/ML。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon S3承接主要責任，以AWS Glue檢查替代條件，並用「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：每秒百萬事件、每日批次ERP資料、分析師與ML團隊需不同權限。

商業需求與不能妥協的限制
          ▼
[Amazon S3：主要責任]
          │ 以HTTP API保存object，提供高durability、彈性namespace與多種storage cla…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Glue：提供Data Catalog、crawler與serverless ETL/integration job…
  · AWS Lake Formation：在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。
  · Amazon Kinesis：保存可重播、按partition key排序的即時event log。
  · Amazon Redshift：提供columnar MPP data warehouse供大型分析與BI。
可移植原則：a data platform separates immutable facts from derived serving layers

失敗時先找：缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon S3有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3和AWS Glue並不是兩個任意的產品名稱。前者適合本章，是因為「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」直接回應了眼前的問題；後者描述的「單一warehouse簡單但不適合所有raw與低成本長期保存。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「a data platform separates immutable facts from derived serving layers」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |
| AWS Glue | 提供Data Catalog、crawler與serverless ETL/integration jobs。 | Crawler推斷S3/JDBC schema寫入Catalog；Spark/Ray/Python jobs讀取、轉換與寫出資料。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 |
| Amazon Kinesis | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 |

## 把全圖套進一個具體案例

**場景：** 每秒百萬事件、每日批次ERP資料、分析師與ML團隊需不同權限。

1. 故事的起點：每秒百萬事件、每日批次ERP資料、分析師與ML團隊需不同權限。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3負責「以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Glue、AWS Lake Formation、Amazon Kinesis、Amazon Redshift各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon S3

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：同一平台需接batch/stream、保存raw、治理schema與權限，並支援BI/ML。
- **具體例子／邊界：** 在「每秒百萬事件、每日批次ERP資料、分析師與ML團隊需不同權限。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Glue

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：單一warehouse簡單但不適合所有raw與低成本長期保存。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：a data platform separates immutable facts from derived serving layers。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### data warehouse

為重複分析、聚合與joins最佳化的columnar analytical database，不是一般低延遲OLTP transaction store。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### ETL

Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

### AWS Glue

- **功用：** 提供Data Catalog、crawler與serverless ETL/integration jobs。
- **底層機制：** Crawler推斷S3/JDBC schema寫入Catalog；Spark/Ray/Python jobs讀取、轉換與寫出資料。
- **關鍵設定：** crawler targets/classifiers、Catalog database/table、job worker type、bookmark、connection與schedule。
- **選擇時機：** 建立共享catalog、batch ETL、schema discovery與資料品質。
- **替換時機：** 只是SQL查詢用Athena；需要完整Spark cluster tuning可選EMR。

### AWS Lake Formation

- **功用：** 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。
- **底層機制：** 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。
- **關鍵設定：** data lake locations、administrators、LF-Tags、grants、hybrid access mode與cross-account sharing。
- **選擇時機：** 多團隊analytics需要細粒度資料治理而非大量S3 policy。
- **替換時機：** 一般object-level app access仍用IAM/S3 policies/Access Points。

### Amazon Kinesis

- **功用：** 保存可重播、按partition key排序的即時event log。
- **底層機制：** Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。
- **關鍵設定：** on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
- **選擇時機：** 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。
- **替換時機：** 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。

### Amazon Redshift

- **功用：** 提供columnar MPP data warehouse供大型分析與BI。
- **底層機制：** Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。
- **關鍵設定：** provisioned/serverless、node/RPU、distribution style/key、sort key、WLM、Spectrum與materialized views。
- **選擇時機：** 重複BI、複雜joins、結構化warehouse與高併發dashboard。
- **替換時機：** 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。

## 考前與實作時再查：設定操作手冊

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

### AWS Glue：逐項設定說明

#### `crawler targets/classifiers`

- **控制什麼：** `crawler targets/classifiers`指定AWS Glue讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Catalog database/table`

- **控制什麼：** `Catalog database/table`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「建立共享catalog、batch ETL、schema discovery與資料品質。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Glue的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `job worker type`

- **控制什麼：** `job worker type`選擇AWS Glue的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `bookmark`

- **控制什麼：** `bookmark`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `connection`

- **控制什麼：** `connection`指定AWS Glue讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「建立共享catalog、batch ETL、schema discovery與資料品質。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Glue的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

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

### Amazon Redshift：逐項設定說明

#### `provisioned/serverless`

- **控制什麼：** `provisioned/serverless`決定Amazon Redshift如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `node/RPU`

- **控制什麼：** `node/RPU`設定Amazon Redshift的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「重複BI、複雜joins、結構化warehouse與高併發dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `distribution style/key`

- **控制什麼：** `distribution style/key`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「重複BI、複雜joins、結構化warehouse與高併發dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Redshift的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `sort key`

- **控制什麼：** `sort key`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「重複BI、複雜joins、結構化warehouse與高併發dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Redshift的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `WLM`

- **控制什麼：** `WLM`改變Amazon Redshift的performance/cost策略，例如並行度、I/O計價、query scheduling或memory回收。
- **何時需要：** 已有代表性load與瓶頸證據，能說明是latency、throughput、concurrency、I/O cost或memory pressure問題時。
- **怎麼設定／驗證：** 用benchmark比較候選mode，設定queue/class/eviction policy，觀察p95/p99、queue time、hit ratio及unit cost。
- **常見錯法：** 未先找瓶頸便切換模式可能只增加費用；問題也可能來自data model或workload isolation。

#### `Spectrum`

- **控制什麼：** `Spectrum`改變Amazon Redshift的performance/cost策略，例如並行度、I/O計價、query scheduling或memory回收。
- **何時需要：** 已有代表性load與瓶頸證據，能說明是latency、throughput、concurrency、I/O cost或memory pressure問題時。
- **怎麼設定／驗證：** 用benchmark比較候選mode，設定queue/class/eviction policy，觀察p95/p99、queue time、hit ratio及unit cost。
- **常見錯法：** 未先找瓶頸便切換模式可能只增加費用；問題也可能來自data model或workload isolation。

#### `materialized views`

- **控制什麼：** `materialized views`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「重複BI、複雜joins、結構化warehouse與高併發dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Redshift依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

## 讀到這裡，請用自己的話說一次

1. Amazon S3的責任：以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
2. 底層機制：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
3. 第一個要看的設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
4. 選擇邏輯：S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。
5. 不要混淆：AWS Glue的責任是「提供Data Catalog、crawler與serverless ETL/integration jobs。」；它不會自動取代Amazon S3。
6. 替換訊號：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
7. 最常見錯法：缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。
8. 可移植原則：a data platform separates immutable facts from derived serving layers。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| AWS Glue | 提供Data Catalog、crawler與serverless ETL/integration jobs。 | Crawler推斷S3/JDBC schema寫入Catalog；Spark/Ray/Python jobs讀取、轉換與寫出資料。 | 建立共享catalog、batch ETL、schema discovery與資料品質。 | 只是SQL查詢用Athena；需要完整Spark cluster tuning可選EMR。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 | 多團隊analytics需要細粒度資料治理而非大量S3 policy。 | 一般object-level app access仍用IAM/S3 policies/Access Points。 |
| Amazon Kinesis | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 | 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。 | 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。 |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 | 重複BI、複雜joins、結構化warehouse與高併發dashboard。 | 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 單一warehouse簡單但不適合所有raw與低成本長期保存。 | 只有當題目條件明確改變時才可能合理。 | 缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「單一warehouse簡單但不適合所有raw與低成本長期保存。」之間做選擇。
- 認得常考設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls；SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
- 對應官方tasks：SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Kinesis Data Streams 與 MSK 的選擇條件

IoT 平台每秒接收數十萬筆 AWS-native producer events，需要同裝置內順序、數小時 replay 與 managed scaling；既有團隊沒有 Kafka clients、Connect 或 broker 生態需求。哪個選擇最符合現況？

A. 優先使用 Kinesis Data Streams，依 device partition key 與 retention 設計；若 Kafka compatibility 成為硬需求再評估 MSK
B. 同時寫入 Kinesis 與 MSK，但不定義哪個是 source of truth 或如何處理雙寫失敗
C. 選 MSK，只因 throughput 高；是否需要 Kafka compatibility 不影響選擇
D. 使用 Kinesis 並宣稱它保證所有裝置之間的全域 total order

**答案：A**

- **A：** 正確。題目需求直接對應 Kinesis managed stream、partition ordering 與 retention；服務選擇應由必要契約而非名稱決定。
- **B：** 錯誤。沒有 authority 與 failure semantics 的雙寫會增加資料分叉、成本與營運複雜度，並非自動提高可靠性。
- **C：** 錯誤。高 throughput 兩者皆可支援；選 MSK 的主要理由應是 Kafka protocol、clients、ecosystem 或 broker control。
- **D：** 錯誤。Kinesis 的順序範圍與 partition/shard sequence 有關，不提供所有 partition 的單一全域順序。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Kinesis Data Streams PutRecord partition-key mapping](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecord.html)、[Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)、[Changing the Kinesis data retention period](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)、[What is Amazon Managed Streaming for Apache Kafka?](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)

### 練習題 2｜SAA｜高 cardinality partition key 與 ordering 範圍

所有 sensors 目前都使用常數 `factory-1` 作 Kinesis partition key，造成 hot shard；架構只要求同一 sensor 的 events 依序，不要求不同 sensors 間全域排序。應如何修改？

A. 使用穩定且高 cardinality 的 sensorId 作 partition key，監控 hot keys 與 shard/on-demand capacity，保留每 sensor 順序
B. 繼續常數 key，增加更多 consumers 便會提高 stream write capacity
C. 只使用 event timestamp 作 key，因時間值一定平均且不會碰撞
D. 每筆 event 使用完全隨機 partition key，同時宣稱同一 sensor 仍必然依序

**答案：A**

- **A：** 正確。相同 sensorId 經 hash 對應同一 shard sequence，可保留 per-device ordering，又能讓多 sensors 分散到更多 partitions。
- **B：** 錯誤。Consumers 影響讀取，不會改變 producer 使用單一 partition key 造成的 write hot shard。
- **C：** 錯誤。Timestamp 可能大量相同或形成非預期分布，也無法自然表達「同一 sensor」的 ordering boundary。
- **D：** 錯誤。Random key 可分散寫入，但同一 sensor 的 events 會落入不同 shards，失去題目要求的順序。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Kinesis Data Streams PutRecord partition-key mapping](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecord.html)、[Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)

### 練習題 3｜SAP｜Kinesis throughput、record size 與 quota headroom

新平台以平均每秒 event 數估算 Kinesis capacity，沒有考慮每筆 payload 大小與 burst。正式上線後 WriteProvisionedThroughputExceeded 增加，consumer iterator age 也升高。應先怎麼改善？

A. 只增加 consumers，因 reader 數量會自動提高 producer write throughput
B. 計算 records 與 bytes 的 input/output demand、consumer model 與 burst，選 provisioned/on-demand，保留 quota/headroom 並對 throttles/age 告警
C. 依平均 event count 繼續 sizing，因 record bytes 不影響 Kinesis limits
D. 等待 service 在發生 throttle 後自動提高所有 account quotas，不需預先規劃

**答案：B**

- **A：** 錯誤。Read consumers 無法修復 write side capacity；producer 仍會在 shard 或 stream limits 遭 throttling。
- **B：** 正確。把流量轉成服務的實際限制單位，並留出 burst 與 quota headroom，才能選擇適當 capacity mode。
- **C：** 錯誤。Kinesis capacity 同時受 records 與 bytes 影響；只看事件數會低估大型 payload 的需求。
- **D：** 錯誤。某些 capacity 可自動調整，但 account/service quotas 與模式特性仍需事前確認，不能以 production failure 當 sizing 方法。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)、[Requesting a service quota increase](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html)

### 練習題 4｜SAA｜Stream retention、consumer checkpoint 與 replay

Fraud consumer 的程式錯誤在兩天後才被發現，需要重新處理過去 48 小時 events。團隊只保存一個所有 consumers 共用 checkpoint，stream retention 為 24 小時。哪個設計較正確？

A. 依 recovery window 設 retention，各 consumer 維護獨立 checkpoint 並能冪等 replay；過期時從 immutable raw S3 重建
B. 採用 queue delete semantics，最快 consumer 讀完後刪除 record，其他 consumer 不需 replay
C. 所有 consumers 共用 checkpoint，讓最快的 consumer 替其他 consumer 決定已處理位置
D. 錯誤發生後才把 retention 從 24 小時提高，已過期 records 便會重新出現

**答案：A**

- **A：** 正確。Independent checkpoints 讓各用途自行前進與回放，immutable raw layer 則提供超過 stream retention 的重建來源。
- **B：** 錯誤。Kinesis stream records 可被多 consumers 讀取，不以單一 consumer delete 控制生命週期。
- **C：** 錯誤。不同 consumer 的版本、速度與 failure 狀態不同，共享 checkpoint 會讓落後者跳過尚未處理的資料。
- **D：** 錯誤。Retention 延長不會復活已經過期的 data；恢復窗口必須在 incident 前設計。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Changing the Kinesis data retention period](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)

### 練習題 5｜SAP｜Data lake raw/landing zone 與 curated zone 的可重建邊界

ETL job 會直接覆寫 data lake raw prefix；一旦 transformation bug 發生，原始 ERP/stream facts 便無法重建。公司需要可追溯且可重跑的 pipeline。哪個 layout 最合理？

A. 在 raw layer 就地覆寫並把舊值寫入應用 log；log retention 可完全取代受治理的 source data
B. 只保留 curated Parquet；Glue crawler 保存 schema，所以可重建任何已刪除的原始 values 與事件順序
C. 將 landing/raw objects 保持 append-only 或 version-aware，依來源與時間分區；轉換結果寫到獨立 stage/curated layer，並保存輸入版本與 checkpoint metadata
D. Raw、temporary、failed 與 curated 共用同一 prefix 和 lifecycle policy，再靠檔名辨識資料責任

**答案：C**

- **A：** 錯誤。一般應用 log 不具備原始資料的完整性、schema與 retention contract，不能取代受治理的 landing/raw layer。
- **B：** 錯誤。Crawler catalog 描述結構，不保存被刪除的原始 values、抵達順序或轉換前內容，無法成為重建來源。
- **C：** 正確。資料層分離讓 raw facts 保持可重播，stage/curated 可獨立修正；輸入版本與 checkpoint metadata則支援追溯和受控重跑。
- **D：** 錯誤。不同 layers 的 ownership、retention、quality 與 access contract 不同；混用 prefix 和 lifecycle 容易誤刪或越權。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Naming structure for data lake layers](https://docs.aws.amazon.com/prescriptive-guidance/latest/defining-bucket-names-data-lakes/naming-structure-data-layers.html)、[Managing the lifecycle of Amazon S3 objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

### 練習題 6｜SAP｜Glue schema ownership 與 crawler change policy

Production crawler 每小時執行，producer 新增不相容欄位後，crawler 自動改寫 Glue Catalog table，數十個 Athena 與 ETL jobs 隨即失敗。怎麼避免 discovery 直接破壞 production contract？

A. 只用 S3 folder 名稱當 schema，取消 Data Catalog 與任何版本管理
B. 永久凍結所有 schema，任何新欄位都在 ingestion 時無聲丟棄
C. 指定 schema owner/version，設定 crawler update/delete behavior，將不相容變更放入 staging table，驗證 consumers 後再 promote
D. 讓 crawler 永遠覆寫 table，因最新 schema 必然與所有 consumers 相容

**答案：C**

- **A：** 錯誤。Folder 可輔助 partition，不足以描述 types、columns、compatibility 與 owner，也無法支援治理。
- **B：** 錯誤。完全拒絕演進會遺失資料與阻礙產品；重點是有控制地版本化與驗證，而不是永遠不變。
- **C：** 正確。Discovery 與 authoritative schema publication 應分離；change policy、staging 與 consumer test 建立可控 promotion。
- **D：** 錯誤。Crawler 發現的是資料現況，不知道 business compatibility；自動覆寫可能發布 breaking change。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Glue Data Catalog and crawlers](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)、[Configure crawler schema-change handling](https://docs.aws.amazon.com/glue/latest/dg/crawler-schema-changes-prevent.html)

### 練習題 7｜SAP｜Lake Formation 與底層 IAM/S3 權限

資料團隊已在 Lake Formation 對 analyst 隱藏 PII columns，但該 role 仍有 `s3:GetObject` 存取整個 raw bucket，能直接繞過 Catalog 查詢下載檔案。哪個修正最正確？

A. 註冊 governed locations，明確選擇 Lake Formation/hybrid mode，縮小 IAM/bucket access，並對 Catalog/data permissions 做 allow/deny 測試
B. 只更換 S3 encryption key，因加密會自動轉換成 column-level authorization
C. 讓所有 principals 維持 IAM-only access，同時假設 Lake Formation grants 一定優先於任何直接 S3 permission
D. 保留 broad S3 access，但把 Lake Formation dashboard 標成 compliant

**答案：A**

- **A：** 正確。Lake Formation 細粒度權限必須和底層 IAM、S3、registered location 及 access mode 一起設計，避免 alternate path。
- **B：** 錯誤。KMS 控制能否解密 object，不了解 table column/row；它不能取代 data governance policy。
- **C：** 錯誤。Hybrid/opt-in semantics 必須明確管理；保留 IAM-only principals 可能使預期的 LF control 根本未生效。
- **D：** 錯誤。Dashboard 狀態不會撤銷 direct object access；實際 effective permissions 才是資料邊界。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Lake Formation fine-grained access control](https://docs.aws.amazon.com/lake-formation/latest/dg/access-control-fine-grained.html)、[Lake Formation hybrid access mode](https://docs.aws.amazon.com/lake-formation/latest/dg/hybrid-access-mode.html)

### 練習題 8｜SAA｜Athena partition pruning、columnar format 與 small-file compaction

Athena 每次查詢一小時資料，卻掃描數 TB。Curated zone 目前是數百萬個 5 KB gzip CSV，並以唯一 eventId 作 partition。哪個改善最有效？

A. 保留 tiny CSV，只把副檔名改成 `.parquet`
B. 增加更多 Athena users/concurrency，讓每個 query 掃描相同 bytes 但更快
C. 重寫為壓縮 Parquet/ORC，依常用且適度 cardinality 的時間/業務欄位分區，compact files 並驗證 bytes scanned
D. 繼續以 eventId 分區，因 partition 越多越能縮小每次 scan

**答案：C**

- **A：** 錯誤。檔名不會改變實際 encoding；必須真正轉換成 columnar format 才能 column pruning。
- **B：** 錯誤。Concurrency 不會減少單一查詢的 bytes scanned，反而可能提高總成本與 contention。
- **C：** 正確。Columnar compression 減少讀取欄位，適當 partition pruning 減少物件範圍，compaction 降低 open/list overhead。
- **D：** 錯誤。近乎唯一值的 partitions 會增加 Catalog/listing overhead，並形成大量 tiny files。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Athena data optimization, partitioning, and small files](https://docs.aws.amazon.com/athena/latest/ug/performance-tuning-data-optimization-techniques.html)

### 練習題 9｜SAP｜Athena workgroup 與 Redshift WLM 的適用邊界

同一平台有偶發 ad-hoc S3 查詢，也有每分鐘刷新、數百人同時使用的 BI dashboards。公司需要分開成本與避免 ETL 壓垮 dashboards。下列哪些兩項最合理？（選兩項）

A. 所有工作都使用單一 Athena workgroup，因 serverless 代表不需要 workload isolation
B. 高並行且可預測的 warehouse workload 使用 Redshift，透過 WLM/queue 設計隔離 dashboard、ETL 與 data science
C. Ad-hoc 查詢使用 Athena workgroups 控制 result location、query limits、metrics 與 scan-cost governance
D. 以 S3 lifecycle rule 當作 query concurrency 與 cost limit
E. 所有 Redshift users 共用一個無 priority 的 queue，讓 ETL 與 dashboard 自由競爭

**答案：B、C**

- **A：** 錯誤。Serverless 不代表沒有 cost 或 concurrency governance；不同團隊仍需隔離設定與使用。
- **B：** 正確。Redshift/WLM 適合管理可預測、高並行的 warehouse workload，能為不同 query class 建立資源與優先順序。
- **C：** 正確。Workgroup 可把 ad-hoc consumers 的設定、metrics 與 bytes-scanned controls 分開，適合直接查詢 data lake。
- **D：** 錯誤。Lifecycle 管 object storage retention，不會限制 SQL query 的執行資源或掃描上限。
- **E：** 錯誤。單一競爭 queue 可能讓長 ETL 擠壓 latency-sensitive dashboard，與題目的 isolation 需求相反。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Use Athena workgroups to control query access and costs](https://docs.aws.amazon.com/athena/latest/ug/workgroups-manage-queries-control-costs.html)、[Amazon Redshift workload management](https://docs.aws.amazon.com/redshift/latest/dg/cm-c-implementing-workload-management.html)

### 練習題 10｜SAP｜可 replay 且受治理的即時分析路徑

平台必須同時保證同 device events 可有序 replay，並防止 analyst 查到未核准的 PII columns。下列哪些兩項能力缺一不可？（選兩項）

A. 使用高 cardinality device partition key、足夠 stream retention、獨立 checkpoints 與冪等 consumers
B. 只使用 Kinesis，因 per-shard ordering 也會自動限制 analyst 的 SQL 權限
C. 只使用 Lake Formation，因 table grants 也會保存與重播 Kinesis events
D. 在 curated data 上建立 Lake Formation/IAM/S3 一致的存取邊界，驗證 analyst 的 allowed 與 denied columns
E. 只為 S3 啟用 encryption，因加密可同時提供 event ordering 與 column authorization

**答案：A、D**

- **A：** 正確。Partition identity 定義 ordering boundary，retention/checkpoint 定義 replay window，冪等性使重播不重複副作用。
- **B：** 錯誤。Kinesis 處理事件傳輸與保留，不管理 Athena/Glue table 的 column-level authorization。
- **C：** 錯誤。Lake Formation 治理 data access，不是 streaming retention 或 consumer checkpoint 服務。
- **D：** 正確。Fine-grained grants 必須和 alternate S3/IAM paths 一起收斂，才真正限制 analyst 的 PII scope。
- **E：** 錯誤。Encryption at rest 不定義 stream partition/order，也不知道 analyst 可看哪些 schema columns。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Kinesis Data Streams PutRecord partition-key mapping](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecord.html)、[Changing the Kinesis data retention period](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)、[Lake Formation fine-grained access control](https://docs.aws.amazon.com/lake-formation/latest/dg/access-control-fine-grained.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK inge…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「同一平台需接batch/stream、保存raw、治理schema與權限，並支援BI/ML。」，所以「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」能直接滿足它；若constraint改成「單一warehouse簡單但不適合所有raw與低成本長期保存。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」。替代方案「單一warehouse簡單但不適合所有raw與低成本長期保存。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「同一平台需接batch/stream、保存raw、治理schema與權限，並支援BI/ML。」，排除會導致「缺乏partition/schema contract導致small files、昂貴scan與跨團隊資料洩漏。」的選項，再選「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「S3分層保存，Glue catalog，Lake Formation治理，Kinesis/MSK ingest，Athena/Redshift查詢。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「a data platform separates immutable facts from derived serving layers」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 103 章　Case Study：Multi-Region DR

跨Region DR不是複製database就完成，還包括build、identity、network、DNS與operations。

## 走進一次完整架構會議：先從故事開始

故事從一個看似簡單的需求開始：核心服務RTO 30分鐘、RPO 5分鐘，法規要求每半年演練。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：跨Region DR不是複製database就完成，還包括build、identity、network、DNS與operations。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon Route 53會是本章的主要角色，AWS Backup則幫我們看清邊界。方向是「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：核心服務RTO 30分鐘、RPO 5分鐘，法規要求每半年演練。

商業需求與不能妥協的限制
          ▼
[Amazon Route 53：主要責任]
          │ 提供authoritative DNS、health check與多種流量政策。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Backup：以policy集中排程、保存與複製多種AWS resource backups。
  · Aurora Global Database：將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
  · AWS CloudFormation：以declarative templates建立、更新與刪除AWS resources。
可移植原則：failover requires fencing, validation, and failback

失敗時先找：Failover成功但舊Region仍接受write，恢復後資料分叉。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon Route 53有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Route 53和AWS Backup並不是兩個任意的產品名稱。前者適合本章，是因為「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」直接回應了眼前的問題；後者描述的「Backup/restore成本更低，若business可接受較長RTO應優先。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Failover成功但舊Region仍接受write，恢復後資料分叉。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「failover requires fencing, validation, and failback」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 |

## 把全圖套進一個具體案例

**場景：** 核心服務RTO 30分鐘、RPO 5分鐘，法規要求每半年演練。

1. 故事的起點：核心服務RTO 30分鐘、RPO 5分鐘，法規要求每半年演練。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Route 53負責「提供authoritative DNS、health check與多種流量政策。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Backup、Aurora Global Database、AWS CloudFormation各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Failover成功但舊Region仍接受write，恢復後資料分叉。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Route 53

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：跨Region DR不是複製database就完成，還包括build、identity、network、DNS與operations。
- **具體例子／邊界：** 在「核心服務RTO 30分鐘、RPO 5分鐘，法規要求每半年演練。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Backup

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Backup/restore成本更低，若business可接受較長RTO應優先。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Failover成功但舊Region仍接受write，恢復後資料分叉。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：failover requires fencing, validation, and failback。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### dependency graph

以nodes/edges表示application、database、network、identity與外部系統的依賴，幫助避免把強耦合元件拆到不同waves。

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### stack

CloudFormation以一個生命週期單位管理的一組resources；更新與刪除行為受dependencies及policies影響。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

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

### AWS CloudFormation

- **功用：** 以declarative templates建立、更新與刪除AWS resources。
- **底層機制：** CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。
- **關鍵設定：** Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
- **選擇時機：** repeatable environment、reviewable IaC與cross-account StackSets。
- **替換時機：** 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。

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

### AWS CloudFormation：逐項設定說明

#### `Parameters`

- **控制什麼：** `Parameters`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `Mappings`

- **控制什麼：** `Mappings`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `Resources`

- **控制什麼：** `Resources`指定AWS CloudFormation讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Outputs`

- **控制什麼：** `Outputs`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `Conditions`

- **控制什麼：** `Conditions`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `DependsOn`

- **控制什麼：** `DependsOn`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `DeletionPolicy`

- **控制什麼：** `DeletionPolicy`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `UpdateReplacePolicy`

- **控制什麼：** `UpdateReplacePolicy`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `stack policy`

- **控制什麼：** `stack policy`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「repeatable environment、reviewable IaC與cross-account StackSets。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

## 讀到這裡，請用自己的話說一次

1. Amazon Route 53的責任：提供authoritative DNS、health check與多種流量政策。
2. 底層機制：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
3. 第一個要看的設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
4. 選擇邏輯：以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。
5. 不要混淆：AWS Backup的責任是「以policy集中排程、保存與複製多種AWS resource backups。」；它不會自動取代Amazon Route 53。
6. 替換訊號：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
7. 最常見錯法：Failover成功但舊Region仍接受write，恢復後資料分叉。
8. 可移植原則：failover requires fencing, validation, and failback。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 | 全球relational reads與分鐘級Region recovery。 | 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。 |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 | repeatable environment、reviewable IaC與cross-account StackSets。 | 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Backup/restore成本更低，若business可接受較長RTO應優先。 | 只有當題目條件明確改變時才可能合理。 | Failover成功但舊Region仍接受write，恢復後資料分叉。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Backup/restore成本更低，若business可接受較長RTO應優先。」之間做選擇。
- 認得常考設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜以 RTO/RPO 與成本選擇 DR strategy

公司將 workload 分為兩級：Tier A 的 RTO 30 分鐘、RPO 5 分鐘；Tier C 可接受 24 小時恢復與前一晚資料。預算無法讓所有系統 active-active。哪個 DR 規劃最合理？

A. Tier A只保留每日snapshot與pilot-light compute；不量測20 TiB restore時間便假設可在30分鐘內完成
B. Tier A使用backup/restore，Tier C使用multi-site active-active；以最高成本的tier承擔最寬鬆objective
C. Tier A使用continuous replication與warm standby並實測promotion；Tier C使用受保護backup/restore並實測restore，讓兩者分別符合RTO/RPO
D. 兩個tiers都使用warm standby；雖可達Tier A目標，但不評估Tier C較寬鬆目標能否改用更低成本的backup/restore

**答案：C**

- **A：** 錯誤。Daily snapshot最壞RPO接近一天，且大量資料restore未經量測，無法支持Tier A的5分鐘RPO與30分鐘RTO。
- **B：** 錯誤。它把昂貴策略配置給低重要性workload，反而讓Tier A採不符合資料點與恢復時間的策略。
- **C：** 正確。DR strategy要按business impact與RTO/RPO分層，並以promotion/restore實測把replication、capacity、dependencies與runbook納入證據。
- **D：** 錯誤。此方案可能達到可用性，但沒有回應成本限制；Tier C容許一天恢復，應比較backup/restore是否已足夠。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[REL13-BP02 Select a DR strategy from recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 2｜SAP｜Recovery Region 的 IaC、keys、secrets 與 quotas

Game day 時，secondary Region 的 database replica 可 promote，但應用無法啟動：KMS key、secret、certificate 與 EC2 quota 尚未準備。團隊原本只建立空 VPC。哪個改進最完整？

A. 假設 KMS keys、Secrets Manager secrets 與 certificates 會自動成為全球資源
B. 只把 CloudFormation template 存在 source control，不需定期部署或驗證 Region parameters
C. 保留空 VPC，災難發生後再複製所有 Region-specific dependencies 與申請 quotas
D. 以版本化 IaC/StackSets 部署或持續驗證 network、IAM、KMS、secrets、certificates 與 capacity，並預先取得 quota headroom

**答案：D**

- **A：** 錯誤。許多 security/config resources 具有 Region 或 account scope，必須明確複製、重建或以支援機制同步。
- **B：** 錯誤。Template 可重現不等於可部署；Region availability、parameters、service roles 與 drift 都需持續驗證。
- **C：** 錯誤。災難期間才建立 control-plane dependencies 與等待 quota approval，通常無法符合 30 分鐘 RTO。
- **D：** 正確。Recovery environment 是完整 production dependency graph；IaC、Region-specific state、permissions 與 quotas 都要在 RTO 前準備並測試。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS CloudFormation StackSets concepts](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html)、[Requesting a service quota increase](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html)

### 練習題 3｜SAP｜以 replication lag 與 transaction age 證明 RPO

Aurora Global Database secondary 狀態顯示 `available`，團隊便宣稱 RPO 為零。實際演練發現最後三分鐘訂單未出現在 promoted Region。哪個監控與驗證方式較正確？

A. 監控 replication lag 與 durable business checkpoint/transaction age，接近五分鐘前告警，演練時量測實際資料遺失
B. 把 Route 53 TTL 設成五分鐘，並把 TTL 當作資料 RPO
C. 只檢查 destination CPUUtilization，因 CPU 低代表 replication 已追上
D. 只要 secondary endpoint 可連線，便能推論所有 transactions 已 durable

**答案：A**

- **A：** 正確。RPO 是「最後可恢復資料點」的時間距離；必須從 replication 與業務 checkpoint 取得 evidence，並以 game day 驗證。
- **B：** 錯誤。DNS TTL 控制 resolver cache，不描述 source 到 secondary 的資料複寫進度。
- **C：** 錯誤。CPU 只是 resource utilization，無法直接證明 WAL/transaction replication 已符合 RPO。
- **D：** 錯誤。Endpoint availability 代表服務可接受連線，不表示 replication 已包含最新 committed business data。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 4｜SAP｜Route 53 ARC routing control safety rules 與資料層就緒邊界

雙 Region cell 架構已有資料庫 promotion runbook，但操作員曾誤把兩個 ingress 同時切到 active，差點造成 split brain。團隊要讓 traffic switch 有集中、可稽核且能阻擋不安全狀態的控制。哪個改善最合適？

A. 只縮短 DNS TTL；TTL 能驗證 secondary database 已可寫，也能阻止兩個 cells 同時 active
B. 以 ARC readiness check 直接代替 application transaction probe，任何 readiness 結果都保證資料一致性
C. 只建立 CloudWatch dashboard，要求值班人員自行記得正確切換順序，不需要可執行 guardrail
D. 使用 Route 53 ARC routing controls 與 safety rules限制不安全的 control-state 組合；仍把資料層 promotion/fencing 與 business readiness 設為切流前置條件

**答案：D**

- **A：** 錯誤。TTL 影響 cache duration，不知道 writer 狀態，也不會對兩個 routing controls 的組合施加原子 safety constraint。
- **B：** 錯誤。Readiness 能檢查資源與配額準備情況，但不能證明每一筆交易或 application invariant 已正確恢復。
- **C：** 錯誤。Dashboard 是觀測工具，不會阻止誤操作；高風險 failover 需要可執行的 safety rule 和審計軌跡。
- **D：** 正確。ARC routing control提供集中 traffic state，safety rules可禁止危險組合；但它不取代 database fencing、promotion 與端到端業務驗證。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Routing control in Amazon Route 53 ARC](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 5｜SAA｜Route 53 failover 的 health signal 與 DNS 限制

Primary application 的 `/health` 固定回 200，即使 database 不可寫也不會失敗。Route 53 因此沒有 failover。團隊還承諾「TTL 30 秒代表所有 clients 30 秒內切換」。哪個修正最準確？

A. 讓 Route 53 health check 直接充當 database writer fencing 與 promotion lock
B. 將 TTL 設為 0，即可保證 resolver、browser 與既有 TCP sessions 同步切換
C. 使用能反映必要 dependency/business ability 的 health signal；設定合理 TTL，但同時設計 retry/reconnect，因 cache 與既有連線可超過 TTL
D. 保留 shallow 200 endpoint，因 health check 不應依賴任何 workload component

**答案：C**

- **A：** 錯誤。Route 53 選擇 DNS response，不具有 database role coordination 或 writer lock 能力。
- **B：** 錯誤。Resolver 可有最低 cache 行為，既有連線根本不重新解析；TTL 不能保證 universal switch time。
- **C：** 正確。Health signal 應回答 endpoint 是否能服務關鍵需求；DNS 只影響新的解析，client cache 與 existing sessions 仍需應用層處理。
- **D：** 錯誤。完全脫離 dependency 的 shallow endpoint 會在服務實際不可用時仍呈健康，造成 false positive。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Route 53 failover records and health checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-values-failover.html)

### 練習題 6｜SAP｜大量資料 restore throughput 與 recovery critical path

團隊每天成功備份 20 TiB 分析資料，便宣稱可在四小時內完成 Region recovery；但從未完整 restore，也未驗證目標 Region 的配額、KMS、網路與下游重建。哪個做法能真正驗證此 RTO？

A. 定期在隔離環境執行代表性或完整 restore，量測並行度與瓶頸，預先驗證配額、KMS、IAM、網路及下游重建，再用 business probe記錄總恢復時間
B. 只預建空白 compute；只要 instance 已啟動，資料、keys 與 dependencies 可在事件後再處理而不影響 RTO
C. 只檢查 backup job duration；備份在四小時內完成即代表 restore 必然同速
D. 把 DNS TTL 設為 30 秒，因名稱切換速度會決定 20 TiB data restore throughput

**答案：A**

- **A：** 正確。RTO 是整條 recovery critical path 的實測結果；restore throughput、service quota、decrypt、network、rebuild與應用驗證都可能成為瓶頸。
- **B：** 錯誤。Compute readiness 只是其中一段；沒有 data、identity與 dependency，服務仍不可用且四小時目標未被證明。
- **C：** 錯誤。Backup 與 restore 的資料路徑、並行度和 dependency 不相同；建立 recovery point 的時間不能證明恢復時間。
- **D：** 錯誤。DNS 只影響流量入口，無法提高資料還原速度或建立缺失的 keys、roles與 downstream state。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Backup restore testing and validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)、[Requesting a service quota increase](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html)

### 練習題 7｜SAP｜Continuous replication 與 protected backup 的互補

公司有跨 Region replica，架構師因此要刪除 backups。安全團隊指出 ransomware 刪除與 logical corruption 也可能複寫到 secondary。哪個恢復設計最好？

A. 把同一份 corrupted data 再複製到第三個 Region，視為不可變 recovery point
B. 以 replication 滿足低 RPO/RTO，另保留受 retention/lock 保護的 backups，並定期 restore 到隔離環境驗證
C. 只做每日 backup，同時宣稱可達五分鐘 RPO 與數分鐘 failover
D. 只保留 replica，因可用 secondary 不可能包含相同 corruption

**答案：B**

- **A：** 錯誤。更多同步副本不會把 corrupted state 變成歷史不可變版本；需要具 retention 的 recovery points。
- **B：** 正確。Replica 與 backup 對應不同 failure modes；lock/retention 保護歷史點，restore test 則證明資料能實際使用。
- **C：** 錯誤。每日頻率的最壞資料損失遠大於五分鐘，且 restore 所需時間也未必符合數分鐘 RTO。
- **D：** 錯誤。Replication 會快速傳遞許多合法但有害的變更；它解決 availability，不完整解決 point-in-time recovery。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[AWS Backup Vault Lock modes](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html#vault-lock-modes)、[AWS Backup restore testing and validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

### 練習題 8｜SAP｜Game day 與 restore test 的可稽核 evidence

法規要求每半年證明核心服務可在 30 分鐘內恢復，RPO 不超過五分鐘。現有 evidence 只有 runbook PDF 與「backup completed」截圖。哪個測試最符合要求？

A. 只 restore 一個 EBS volume，不測 identity、network、application 或 data point
B. 只做 tabletop discussion，因實際 failover 可能影響 production
C. 受控執行 dependency/data promotion、traffic、business transaction、RTO/RPO 量測與 failback，保存結果並追蹤缺陷
D. 執行測試但不記錄開始、資料 checkpoint、完成時間與失敗 remediation

**答案：C**

- **A：** 錯誤。單一 volume restore 只驗證局部元件；核心服務還依賴 identity、keys、network、database 與 application。
- **B：** 錯誤。Tabletop 有助找流程缺口，但不能單獨證明系統能在目標時間內真正恢復。
- **C：** 正確。端到端 game day 把架構假設轉成可重複測量的 recovery evidence，並包含恢復後的安全 failback。
- **D：** 錯誤。沒有時間與資料點 evidence，就無法證明 RTO/RPO，也不能確認下一次是否修正。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Backup restore testing and validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)、[REL13-BP02 Select a DR strategy from recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)

### 練習題 9｜SAP｜Failback 的資料 reconciliation 與受控切換

公司已在 secondary Region 營運兩天並接受新訂單，原 Region 現在恢復。團隊要 failback，但不能遺失這兩天資料或重建雙 writer。下列哪些兩項正確？（選兩項）

A. 只同步 schema/config，因 business data 在 failover 後會自然對稱
B. 舊 Region endpoint 一可連線就立刻把 Route 53 指回去
C. 以 planned switchover/fencing 執行回切，驗證 business transactions 後才恢復正常 routing 並關閉臨時例外
D. 在舊 Region 從事故前 backup 獨立恢復，兩邊同時接受新 writes
E. 先穩定目前 authoritative Region，重建向目標 Region 的 replication，驗證 lag、keys、capacity 與 exceptional writes

**答案：C、E**

- **A：** 錯誤。Schema 相同不代表 rows/transactions 相同，尤其所有新 writes 都發生在 recovery Region。
- **B：** 錯誤。立刻改 DNS 可能把新訂單送到落後資料庫，且既有 sessions 仍留在 secondary，造成分叉。
- **C：** 正確。Planned switchover 把 writer role、流量與驗證依序協調，並在完成後清理 emergency routes/permissions。
- **D：** 錯誤。舊 backup 不包含這兩天交易；雙寫又會產生新的 conflict，除非另有明確合併語意。
- **E：** 正確。Failback 前必須讓目標重新成為完整、最新且可操作的 secondary；可達不代表資料已追上。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)、[Route 53 failover records and health checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-values-failover.html)

### 練習題 10｜SAP｜Aurora Global Database write forwarding 的能力與 DR 邊界

團隊開啟 Aurora Global Database write forwarding，便宣稱 secondary Region 已成為獨立 active writer，primary 故障時不需 failover。下列哪些兩項敘述正確？（選兩項）

A. Write forwarding 讓每個 secondary 擁有獨立 writer，可在網路分割時各自提交並由 Aurora 自動合併所有衝突
B. Primary 不可用時仍需依 Aurora Global Database 的 managed failover/switchover 程序建立新 writer，並驗證應用連線與資料狀態
C. Write forwarding 會把 Route 53 health checks、ARC routing controls與應用冪等性全部納入單一資料庫設定
D. 只要開啟 forwarding，primary outage 時 secondary 會在零資料風險下自動變成 writer，應用無須重連或執行 failover runbook
E. Secondary 發出的受支援寫入仍會被轉送到 primary writer；應依需求選擇 read consistency，並測試額外 latency 與限制

**答案：B、E**

- **A：** 錯誤。Aurora Global Database 不會把分割期間的多個獨立 writer 交易自動合併；forwarded write 仍依賴 primary。
- **B：** 正確。DR role transition 和 write forwarding 是不同機制；新 writer 建立後仍需檢查 replication、endpoint、session與 business correctness。
- **C：** 錯誤。Traffic control、request idempotency與資料庫 write routing分屬不同責任，不能由單一 forwarding flag 自動完成。
- **D：** 錯誤。Forwarding 不等於故障接管；primary outage 仍需執行服務支援的 failover並讓應用重新建立正確連線。
- **E：** 正確。Forwarding 是 secondary 到 primary writer 的路徑，不是新增獨立 authority；一致性選項、延遲與不支援操作必須納入設計。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Using write forwarding in an Aurora global database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html)、[Aurora Global Database switchovers, failovers, and write fencing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「跨Region DR不是複製database就完成，還包括build、identity、network、DNS與operations。」，所以「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」能直接滿足它；若constraint改成「Backup/restore成本更低，若business可接受較長RTO應優先。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」。替代方案「Backup/restore成本更低，若business可接受較長RTO應優先。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Failover成功但舊Region仍接受write，恢復後資料分叉。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「跨Region DR不是複製database就完成，還包括build、identity、network、DNS與operations。」，排除會導致「Failover成功但舊Region仍接受write，恢復後資料分叉。」的選項，再選「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以RTO/RPO選warm standby，持續複寫state、IaC建立環境、定期game day驗證切換與回切。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「failover requires fencing, validation, and failback」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 104 章　Case Study：AI Agent Application

Agent需存取企業資料與工具，model output不確定但side effect必須受控。

## 走進一次完整架構會議：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：IT agent可查詢與重啟service，高風險production操作需人工批准。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：Agent需存取企業資料與工具，model output不確定但side effect必須受控。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：AI agent像能查資料並操作工具的助理：回答是否合理與它是否被允許執行動作，是兩個完全不同的問題。 類比不能淡化模型的不確定性；production仍要使用評估、policy、approval與完整audit trail。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon Bedrock負責主要工作，Amazon Bedrock Guardrails提醒我們答案不是永遠固定。本章會走向「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：IT agent可查詢與重啟service，高風險production操作需人工批准。

商業需求與不能妥協的限制
          ▼
[Amazon Bedrock：主要責任]
          │ 以managed API使用foundation models並組合RAG、agents、guardrails與e…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon Bedrock Guardrails：在model input/output套用content、denied topics、PII、word與g…
  · AWS Step Functions：以可視化state machine編排多步驟、retry、branch、parallel與human wo…
  · AWS STS：簽發有限時效的temporary AWS credentials。
可移植原則：probabilistic planning must terminate at deterministic authorization

失敗時先找：Model直接持admin credentials，或tool成功但response timeout後重複執行。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「走進一次完整架構會議」。先不要急著問Amazon Bedrock有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Bedrock和Amazon Bedrock Guardrails並不是兩個任意的產品名稱。前者適合本章，是因為「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」直接回應了眼前的問題；後者描述的「純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Model直接持admin credentials，或tool成功但response timeout後重複執行。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「probabilistic planning must terminate at deterministic authorization」。更白話地說：先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Bedrock | 以managed API使用foundation models並組合RAG、agents、guardrails與evaluation。 | Runtime把prompt送到選定model；上層features管理retrieval、tool orchestration與safety policy。 |
| Amazon Bedrock Guardrails | 在model input/output套用content、denied topics、PII、word與grounding policies。 | Guardrail在inference前後分類/過濾內容，可獨立於特定model版本使用。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 |

## 把全圖套進一個具體案例

**場景：** IT agent可查詢與重啟service，高風險production操作需人工批准。

1. 故事的起點：IT agent可查詢與重啟service，高風險production操作需人工批准。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Bedrock負責「以managed API使用foundation models並組合RAG、agents、guardrails與evaluation。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Runtime把prompt送到選定model；上層features管理retrieval、tool orchestration與safety policy。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Bedrock Guardrails、AWS Step Functions、AWS STS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Model直接持admin credentials，或tool成功但response timeout後重複執行。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要完整model training、custom container與深度ML control時用SageMaker。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Bedrock

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Agent需存取企業資料與工具，model output不確定但side effect必須受控。
- **具體例子／邊界：** 在「IT agent可查詢與重啟service，高風險production操作需人工批准。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Bedrock Guardrails

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Model直接持admin credentials，或tool成功但response timeout後重複執行。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：probabilistic planning must terminate at deterministic authorization。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon Bedrock

- **功用：** 以managed API使用foundation models並組合RAG、agents、guardrails與evaluation。
- **底層機制：** Runtime把prompt送到選定model；上層features管理retrieval、tool orchestration與safety policy。
- **關鍵設定：** model access、inference profile、temperature/max tokens、VPC endpoint、KMS、logging與IAM。
- **選擇時機：** 需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。
- **替換時機：** 需要完整model training、custom container與深度ML control時用SageMaker。

### Amazon Bedrock Guardrails

- **功用：** 在model input/output套用content、denied topics、PII、word與grounding policies。
- **底層機制：** Guardrail在inference前後分類/過濾內容，可獨立於特定model版本使用。
- **關鍵設定：** content filters、denied topics、word filters、sensitive information、contextual grounding與version。
- **選擇時機：** 需要一致safety policy、PII遮罩與跨model治理。
- **替換時機：** 它不是IAM、network isolation或事實正確性的完整替代；需多層controls/evals。

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

### AWS STS

- **功用：** 簽發有限時效的temporary AWS credentials。
- **底層機制：** AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。
- **關鍵設定：** role ARN、session name、duration、external ID、source identity、session tags與session policy。
- **選擇時機：** cross-account、federation、workload identity與避免長期access keys。
- **替換時機：** 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。

## 考前與實作時再查：設定操作手冊

### Amazon Bedrock：逐項設定說明

#### `model access`

- **控制什麼：** `model access`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `inference profile`

- **控制什麼：** `inference profile`定義Amazon Bedrock管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `temperature/max tokens`

- **控制什麼：** `temperature/max tokens`控制生成式AI的retrieval、sampling、context或inference routing，直接影響quality、latency與token cost。
- **何時需要：** 使用Amazon Bedrock處理RAG、agent或production inference，而不是單次playground實驗時。
- **怎麼設定／驗證：** 用版本化eval dataset比較設定，記錄model/version、chunk size/overlap、top-k、temperature與max tokens。
- **常見錯法：** 只看一個demo容易過度擬合；低temperature不保證正確，更多context也可能增加雜訊與成本。

#### `VPC endpoint`

- **控制什麼：** `VPC endpoint`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `IAM`

- **控制什麼：** `IAM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### Amazon Bedrock Guardrails：逐項設定說明

#### `content filters`

- **控制什麼：** `content filters`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「需要一致safety policy、PII遮罩與跨model治理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock Guardrails以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `denied topics`

- **控制什麼：** `denied topics`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要一致safety policy、PII遮罩與跨model治理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock Guardrails的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `word filters`

- **控制什麼：** `word filters`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「需要一致safety policy、PII遮罩與跨model治理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock Guardrails以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `sensitive information`

- **控制什麼：** `sensitive information`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「需要一致safety policy、PII遮罩與跨model治理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock Guardrails依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

#### `contextual grounding`

- **控制什麼：** `contextual grounding`控制model選擇/grounding、knowledge-base同步、event payload轉換或API consumer的quota/rate plan。
- **何時需要：** AI、event-driven或public API需要可版本化quality、資料新鮮度、payload contract或tenant限額時。
- **怎麼設定／驗證：** 鎖定model/version與eval，設定grounding threshold或sync schedule；event/API則定義transform schema、API key plan、quota與throttle。
- **常見錯法：** Model或sync成功不代表回答正確；input transform漏欄位會破壞consumer，usage plan也不能取代authentication/authorization。

#### `version`

- **控制什麼：** `version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要一致safety policy、PII遮罩與跨model治理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Bedrock Guardrails鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

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

### AWS STS：逐項設定說明

#### `role ARN`

- **控制什麼：** `role ARN`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session name`

- **控制什麼：** `session name`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `duration`

- **控制什麼：** `duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS STS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `external ID`

- **控制什麼：** `external ID`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `source identity`

- **控制什麼：** `source identity`指定AWS STS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `session tags`

- **控制什麼：** `session tags`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `session policy`

- **控制什麼：** `session policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 讀到這裡，請用自己的話說一次

1. Amazon Bedrock的責任：以managed API使用foundation models並組合RAG、agents、guardrails與evaluation。
2. 底層機制：Runtime把prompt送到選定model；上層features管理retrieval、tool orchestration與safety policy。
3. 第一個要看的設定：model access、inference profile、temperature/max tokens、VPC endpoint、KMS、logging與IAM。
4. 選擇邏輯：Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。
5. 不要混淆：Amazon Bedrock Guardrails的責任是「在model input/output套用content、denied topics、PII、word與grounding policies。」；它不會自動取代Amazon Bedrock。
6. 替換訊號：需要完整model training、custom container與深度ML control時用SageMaker。
7. 最常見錯法：Model直接持admin credentials，或tool成功但response timeout後重複執行。
8. 可移植原則：probabilistic planning must terminate at deterministic authorization。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Bedrock | 以managed API使用foundation models並組合RAG、agents、guardrails與evaluation。 | Runtime把prompt送到選定model；上層features管理retrieval、tool orchestration與safety policy。 | 需要快速使用多家FMs、少管理training infrastructure與AWS-native GenAI building blocks。 | 需要完整model training、custom container與深度ML control時用SageMaker。 |
| Amazon Bedrock Guardrails | 在model input/output套用content、denied topics、PII、word與grounding policies。 | Guardrail在inference前後分類/過濾內容，可獨立於特定model版本使用。 | 需要一致safety policy、PII遮罩與跨model治理。 | 它不是IAM、network isolation或事實正確性的完整替代；需多層controls/evals。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 | cross-account、federation、workload identity與避免長期access keys。 | 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。 | 只有當題目條件明確改變時才可能合理。 | Model直接持admin credentials，或tool成功但response timeout後重複執行。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。」之間做選擇。
- 認得常考設定：model access、inference profile、temperature/max tokens、VPC endpoint、KMS、logging與IAM。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要完整model training、custom container與深度ML control時用SageMaker。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAP enrichment｜AgentCore 新設計與 Bedrock Agents Classic 邊界

公司在 2026 年為新客戶設計可呼叫 IT tools 的 agent。另一個舊系統仍使用 Amazon Bedrock Agents Classic。Architecture proposal 要求所有新舊 workload 都新建 Classic agents。哪個決策正確？

A. 所有新舊 workload 繼續只建立 Classic agents；maintenance mode 表示功能仍會和新平台同步擴充
B. 新 workload 採 AgentCore 或 application-managed orchestration；Classic 僅維持既有系統，先盤點 tools、identity、sessions、traces與行為差異，再以分階段驗證遷移
C. 直接把 Classic agent 的 model ID 改到 AgentCore，原有 action group、identity與trace contract 保證原封不動相容
D. 同時雙寫兩套 agent runtime 的所有 side effects，但不建立 operation identity或結果 reconciliation，以此當零風險遷移

**答案：B**

- **A：** 錯誤。Maintenance mode 不等於新功能持續對等；把新 workload 鎖進 legacy 路徑會增加未來遷移成本。
- **B：** 正確。Maintenance mode 與新設計路徑代表應分開處理：既有系統可維持，新的 workload 採現行平台；遷移必須驗證非模型層 contracts。
- **C：** 錯誤。Runtime 遷移不只是 model replacement；tools、authorization、session、observability與failure semantics都需驗證。
- **D：** 錯誤。Shadow/dual-run 可以比較結果，但有副作用的雙寫若無冪等與 reconciliation 會製造重複操作，不能作為安全預設。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon Bedrock Agents Classic maintenance mode](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html)

### 練習題 2｜SAP enrichment｜Agent runtime 的 inbound authentication 與 authorization

AgentCore Runtime 接收 enterprise JWT。現行程式只檢查 token 尚未過期，就允許 caller 操作任意 tenant 的 tools。哪個修正最完整？

A. 使用支援的 IAM/JWT inbound auth，驗證 issuer、audience/client 與必要 claims，之後再做 tenant/action/resource authorization
B. 只要 endpoint 位於 private subnet，任何 token 都可視為已授權
C. 只檢查 JWT signature，不需驗證 token 是簽給哪個 audience 或可操作哪些 resources
D. 用 outbound OAuth credential provider 取代 inbound caller authentication

**答案：A**

- **A：** 正確。Authentication 證明 caller/token；authorization 仍須依可信 claims 與 server-side resource policy 決定允許的 tool action。
- **B：** 錯誤。Network location 不是 end-user identity，private connectivity 也可能被已入侵 workload 濫用。
- **C：** 錯誤。有效 signature 只證明 issuer 簽過 token；若 audience/claims 不符，仍可能是拿別處的 token 重放。
- **D：** 錯誤。Outbound credentials 用於 agent 呼叫下游，不會驗證誰正在呼叫 agent runtime。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configure an AgentCore Runtime inbound JWT authorizer](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/inbound-jwt-authorizer.html)

### 練習題 3｜SAP enrichment｜Workload identity 與 outbound credentials 分離

IT agent 需呼叫 GitHub 與內部工單 API。有些動作代表目前使用者，有些是 nightly system job。開發者把一組永久 OAuth client secret 放在 system prompt，所有使用者共用。哪個設計較安全？

A. 讓每位使用者把個人 refresh token放進 system prompt，再靠 Guardrails 避免 token 出現在輸出
B. 需要代表使用者時採 user-delegated OAuth；nightly job 採 workload identity/M2M，兩者使用最小 scopes與短期 credentials，秘密由受控 provider取得而不進 prompt
C. 把 AgentCore workload token直接送給所有第三方 API；只要 token 有簽章，audience與第三方授權模型不必相符
D. 所有 GitHub 與工單動作都使用同一 M2M client credential，但在 application log 裡記錄終端使用者名稱

**答案：B**

- **A：** 錯誤。Prompt 與 trace不是秘密儲存區；Guardrails也不保證 refresh token不會被模型、log或tool path暴露。
- **B：** 正確。User delegation與machine-to-machine代表不同 principal和 consent；分開取得短期、最小 scope credentials才能保留權限與稽核邊界。
- **C：** 錯誤。Workload token有特定 audience與用途，不是所有第三方 API 的通用 bearer credential，仍需相應 credential exchange/provider。
- **D：** 錯誤。共同 M2M credential無法保留 delegated-user authority；事後 log不會把 machine privilege轉成使用者授權。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Understand AgentCore workload identities](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/understanding-agent-identities.html)、[Obtain outbound credentials with AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/obtain-credentials.html)

### 練習題 4｜SAP enrichment｜Probabilistic planning 與 deterministic tool authorization

模型產生 `restart-service(prod, payments)` tool call，JSON schema 完全合法，但 requester 只獲准重啟 dev。團隊想用 system prompt「不要碰 production」作唯一防護。哪個做法正確？

A. 只用 JSON schema驗證 `restart-service`參數；schema通過即代表 requester獲准操作 production target
B. 只靠 IAM 允許 runtime呼叫 tool gateway；gateway收到合法 AWS principal後，不再檢查 tool action、resource或business context
C. 只以 Bedrock Guardrails檢查輸入輸出內容；未命中敏感詞就允許所有 side effects
D. 在 AgentCore gateway/tool enforcement point使用 Cedar policy，將可信 principal、action、resource與context做 default-deny決策；IAM仍限制誰能呼叫 AWS/API enforcement layer

**答案：D**

- **A：** 錯誤。Schema只證明資料形狀，不知道 requester是否能重啟 production、resource目前是否允許變更。
- **B：** 錯誤。IAM 可限制誰能到達 AWS資源或gateway，但題目還需要針對每個 tool/resource/context的細粒度決策，不能在入口認證後全面放行。
- **C：** 錯誤。Guardrails處理內容風險，不是 action/resource authorization engine；安全文字也可能提出未授權副作用。
- **D：** 正確。AgentCore Policy/Cedar處理確定性的tool authorization；IAM與runtime authentication仍負責外層 principal和API access，兩層互補。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Understanding Cedar policies in Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-understanding-cedar.html)、[Common AgentCore Policy patterns](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-common-patterns.html)

### 練習題 5｜SAP enrichment｜Bedrock Guardrails 與 tool authorization 的不同責任

Guardrail 已阻擋敏感資訊與禁止主題。產品經理因此主張，只要 prompt/output 沒被 guardrail 擋下，就可以直接執行任何 tool。哪個評估正確？

A. Automated Reasoning checks可以簽發 AWS temporary credentials，因此能同時取代 STS、IAM與tool policy
B. Guardrails處理 denied topics、敏感資訊與內容政策；Automated Reasoning checks驗證可形式化的敘述；tool authorization仍由 IAM/AgentCore Policy與business validation獨立執行
C. Guardrails通過便代表 caller已有對指定 production resource的 IAM permission，gateway可省略授權
D. 只做 AgentCore Policy即可；它會自動攔截 PII、模型幻覺與所有不實敘述，不需內容安全控制

**答案：B**

- **A：** 錯誤。Automated Reasoning checks評估模型內容是否符合規則，不是 credential issuer，也不取代 IAM authorization。
- **B：** 正確。三者責任不同：內容政策、可形式化 claim驗證、以及 principal/action/resource授權不能互相推論或替代。
- **C：** 錯誤。Guardrail結果不包含 caller對具體 AWS或business resource的有效權限，不能批准 side effect。
- **D：** 錯誤。AgentCore Policy可做tool-level確定性授權，但不等於內容過濾或事實驗證；仍需對應 controls。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon Bedrock Guardrails components](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)、[Monitor and enforce Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-enforcements.html)、[Understanding Cedar policies in Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-understanding-cedar.html)

### 練習題 6｜SAP enrichment｜高風險 tool 的 durable human approval

Production restart 必須由當值主管核准；主管可能兩小時後才回覆。現況讓 Lambda sleep 等 email，且核准後模型可修改 target。哪個 workflow 最安全？

A. 先執行 restart 再等待核准，若被拒絕便視為補償完成
B. 把 Lambda timeout 調長到兩小時，收到任何 email response 都視為批准
C. 使用 Standard Step Functions callback，保存不可變 action/evidence digest，驗證 approver，回呼後重驗並只執行已批准內容
D. 只寄送 SNS notification；訊息成功送達就表示主管同意

**答案：C**

- **A：** 錯誤。高風險 action 的核心要求是事前 oversight；並非所有 restart 都可無損補償。
- **B：** 錯誤。Sleep 佔用 execution、難處理重啟與 timeout，且任意 email 不等於經驗證的 approver decision。
- **C：** 正確。Durable callback 可跨越長等待；decision 必須綁定 immutable proposal，避免 approval 後參數被模型更換。
- **D：** 錯誤。Delivery receipt 只證明通知傳送，不代表人類已檢視、理解並批准特定 action。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Step Functions callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)、[Step Functions Task state timeout and heartbeat fields](https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html)、[Common AgentCore Policy patterns](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-common-patterns.html)

### 練習題 7｜SAP enrichment｜Task token 的 capability 保護與 replay 防護

Approval email 直接包含 Step Functions raw task token。連結被轉寄後，未授權人員成功呼叫 callback；逾時 approval 還會自動視為允許。哪個修正最好？

A. 允許任何 AWS account 回呼，因知道 task token 已足以證明身分
B. 保留 raw token 在 URL，只把 token 長度增加
C. 維持 timeout 自動批准，避免審批流程降低 service availability
D. Token 留在 server-side，email 只含短效 decision handle；驗證 approver/action scope，設 timeout/reject branch，完成與執行皆 single-use

**答案：D**

- **A：** 錯誤。Token secrecy 不能替代 caller authorization；callback 仍應限制 account/principal 並保留 audit。
- **B：** 錯誤。Task token 本身是 callback capability，暴露在可轉寄 URL、proxy 或 email log 仍可能被濫用。
- **C：** 錯誤。高風險操作在沒有明確 decision 時應 fail closed 或走人工 escalation，而不是逾時自動批准。
- **D：** 正確。Application handle 可加入 approver、request、expiry 與 one-time state；真正 token 只由受信任 backend 使用。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Step Functions callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)、[Step Functions Task state timeout and heartbeat fields](https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html)

### 練習題 8｜SAP enrichment｜AssumeRole session scope 與 source identity

核准後，executor 需暫時重啟一個特定 service。現在所有 users 共用長期 administrator keys，CloudTrail 只看到相同 role session name。哪個改善最完整？

A. 只使用可由 caller任意填寫的 role session name作唯一終端使用者證據，不需要 source identity或session tags
B. 使用 session policy加入 role本來沒有的 restart與KMS actions，避免修改 role policy
C. 讓所有 users assume同一 broad admin role，再靠 CloudTrail event time推測是哪位使用者發動操作
D. Assume一個最小權限 role，使用 session policy/tags只做進一步縮限，設定受信任 source identity；短期 credentials僅留在 executor，不進模型 context

**答案：D**

- **A：** 錯誤。Role session name可能由 caller控制且可重複；source identity與可信 session attributes更適合保留represented-user context。
- **B：** 錯誤。Session policy與role policy是交集，只能縮小有效 permissions，不能授予 role原本沒有的 action。
- **C：** 錯誤。共同 broad role擴大 blast radius，event time無法取代個人 attribution與resource-scoped authorization。
- **D：** 正確。Role決定權限上限，session policy/tags可再縮限，source identity改善跨role audit；短期 credential不應暴露給模型。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Control permissions for assumed-role sessions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_assumerole.html)、[Monitor assumed roles with source identity](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_monitor.html)

### 練習題 9｜SAP enrichment｜Agent tool side effect 的冪等與部分失敗處理

Executor 已成功 restart，但回應在 network timeout 中遺失，Step Functions retry 又執行第二次。某些 tools 還可能只完成一半。下列哪些兩項應加入？（選兩項）

A. 對 partial failure 定義可驗證 compensation 或人工 recovery，重試時回傳既有結果而非重做已完成副作用
B. 只在單一 Lambda execution environment 的記憶體保存最近 actions
C. 把 requester、approved action、target 與 resource version 綁成 durable idempotency key，原子記錄執行狀態與結果
D. 假設 Step Functions retry 對所有第三方與 AWS side effects 都提供 exactly-once semantics
E. 每次 timeout 產生新 operation ID，確保 retry 不會被舊狀態阻擋

**答案：A、C**

- **A：** 正確。並非所有 side effect 都可單純重試；補償、人工處理與 prior-result replay 必須依 action semantics 設計。
- **B：** 錯誤。Execution environment 會消失或平行擴展，無法成為可靠的全域 operation ledger。
- **C：** 正確。Operation identity 必須涵蓋被批准的精確內容；持久化與原子 state transition 才能跨 process/retry 判斷是否已執行。
- **D：** 錯誤。Workflow retry 只重新呼叫 task，不能把非冪等 downstream API 自動轉成 exactly once。
- **E：** 錯誤。新 ID 會把同一邏輯操作偽裝成新 action，正好繞過冪等保護。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)、[Step Functions callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)

### 練習題 10｜SAP enrichment｜AgentCore、Bedrock inference與成本歸屬的分層 observability

公司要把 agent 上 production，要求未授權 side effect 必須被阻止，也要偵測 runaway token/tool cost 與失敗，但不能無限制保存含敏感資訊的 prompts。下列哪些兩項缺一不可？（選兩項）

A. 只開啟 Bedrock model invocation logging；它會自動包含所有 AgentCore tool traces、第三方 API結果與每個application的完整成本歸屬
B. 在 executor保留 requester-bound policy、human approval（高風險）與durable idempotency，並於執行前重新驗證精確 action/resource
C. 只用resource cost tags；帳單標籤能證明每次tool action已獲授權、成功且符合business invariant
D. 使用 AgentCore Observability收集runtime/session/tool traces與latency/error；另設Bedrock model invocation logs/metrics，並以application inference profile等機制歸屬模型成本，對敏感欄位做redaction與retention
E. 永久保存raw prompts、OAuth tokens與tool credentials，因完整資料比資料最小化更能降低observability風險

**答案：B、D**

- **A：** 錯誤。Model invocation logging聚焦模型請求/回應，不會自動涵蓋AgentCore runtime與tool spans，也不等於application-level成本分攤。
- **B：** 正確。Observability不能取代預防控制；確定性authorization、approval與冪等 ledger直接保護 side-effect boundary。
- **C：** 錯誤。Cost metadata只能協助帳務分析，不能證明authorization、tool outcome或business correctness。
- **D：** 正確。三層訊號需分開建立：AgentCore traces、Bedrock inference telemetry、application inference profile成本歸屬；同時實施redaction、存取與retention。
- **E：** 錯誤。Raw logging會擴大PII與credential exposure；應依除錯/稽核目的最小化資料，而不是永久保存秘密。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Understanding Cedar policies in Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-understanding-cedar.html)、[REL04-BP04 Make mutating operations idempotent](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html)、[Add observability to Amazon Bedrock AgentCore resources](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html)、[Amazon Bedrock model invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)、[Monitor Bedrock runtime inference with CloudWatch metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html)、[Application inference profiles for Bedrock cost attribution](https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardra…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Agent需存取企業資料與工具，model output不確定但side effect必須受控。」，所以「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」能直接滿足它；若constraint改成「純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」。替代方案「純chatbot不執行工具時風險較低；agentic workflow需要更完整audit與idempotency。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Model直接持admin credentials，或tool成功但response timeout後重複執行。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Agent需存取企業資料與工具，model output不確定但side effect必須受控。」，排除會導致「Model直接持admin credentials，或tool成功但response timeout後重複執行。」的選項，再選「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」。本章對應的代表task包括：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Bedrock模型/RAG與tool execution分層，identity綁定user，Guardrails過濾，Step Functions核准高風險action。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「probabilistic planning must terminate at deterministic authorization」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
