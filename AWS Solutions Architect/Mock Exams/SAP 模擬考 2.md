---
title: SAP 模擬考 2
exam: SAP-C02
---

# SAP 模擬考 2

> [!abstract] 作答說明
> **題數與時間**：75 題，建議一次完成、計時 180 分鐘（與真實 SAP-C02 相同），平均每題約 2 分 20 秒。
> **難度定位**：本回刻意比真實考試略難，作為考前最後一回。題幹較長、同時有多個限制（跨帳號、既有系統、遷移時程、合規、預算），選項多半是「多步驟方案」，常常只差一個步驟就不成立。
> **情境產業**：醫療健康、電信、政府公共部門、能源、航空物流、跨國 SaaS。
> **及格參考**：真實考試以 100–1000 分計、750 分及格，且含不計分題。本回答對 56 題（約 75%）以上可視為準備充分；若低於 49 題（約 65%），請依文末「錯題對應複習章節」回頭補強。
> **作答方式**：先把 75 題全部作答、記下答案，再一次展開 `答案` 對照。每題先找出「最佳化目標」（MOST cost-effective、LEAST operational overhead、highest availability…）與所有硬性限制，再用刪去法逐一排除違反限制的選項。多選題會在題目標明「選兩項」或「選三項」，必須全對才算得分。
> **錯題記錄**：每錯一題，在錯題本寫下三件事：（1）題號與 task ID；（2）你選的選項錯在哪個限制或機制；（3）正確答案的關鍵字。考前一週只重看錯題本與對應章節的「考試這樣考」。

## 題目

### 第 1 題｜SAP｜單選｜D1 兩座資料中心經 AWS 骨幹互通

北辰電信在台北與高雄各有一座核心資料中心，兩地各自透過一條 10 Gbps 的 AWS Direct Connect 連線接到不同的 DX location，並用 transit VIF 經 Direct Connect gateway 連到 Transit Gateway，再連到三個 Region 的 60 個 VPC。兩座資料中心之間目前靠一條租用的電路互通，這條電路每年中斷數次，續約價格又大幅上漲。網路團隊希望在電路中斷時，台北與高雄之間的流量能改走 AWS 骨幹，而且不經過任何 VPC 或 Region 內的轉送設備。團隊希望變更最少、不需要在 AWS 上維運任何 router。

哪個方案最符合需求？

- A. 在兩地之間各建立一條經 Internet 的 Site-to-Site VPN 連到 Transit Gateway，讓 Transit Gateway 在兩條 VPN 之間轉送流量
- B. 在兩條既有 DX 連線所用的 VIF 上啟用 SiteLink，讓兩個 DX location 之間的流量經 AWS 骨幹直接互通，並以 BGP 屬性讓租用電路維持主要路徑
- C. 在一個 transit VPC 中部署兩台第三方 router EC2，兩地資料中心都透過 private VIF 連到該 VPC，由 router 互相轉送路由
- D. 把兩條 DX 改接到同一個 Direct Connect gateway 的兩個 private VIF，並在 Direct Connect gateway 上啟用路由傳遞，讓兩地 prefix 互相學習

> [!answer]- 答案：B
> **A ✗** Transit Gateway 確實可以在 VPN attachment 之間轉送流量，但流量走的是 Internet 上的 IPsec，頻寬與延遲都不穩定，也沒有利用既有的 DX 骨幹。若公司沒有 DX、只想快速建立備援路徑，這個做法才會是合理選項。
>
> **B ✓** **SiteLink** 讓連到同一個 Direct Connect gateway 的不同 DX location 之間，流量可以沿 AWS 全球骨幹走最短路徑互通，不必進入任何 Region 或 VPC。它是在既有 VIF（private 或 transit）上開啟的功能，不需要額外設備，按 VIF 開啟時數與傳輸量計費。搭配 BGP 屬性（例如 AS path prepend 或 local preference）就能讓租用電路維持主要路徑、SiteLink 作為備援。
>
> **C ✗** Transit VPC 加自管 router 是 Transit Gateway 出現前的舊做法，流量要進 Region、經過 EC2，正好違反「不經過 VPC 內轉送設備」與「不維運 router」兩個限制。
>
> **D ✗** 未啟用 SiteLink 時，Direct Connect gateway 不會在兩個 VIF 之間轉送流量，它只負責 VIF 與 VPC／Transit Gateway 之間的路由，所以兩地無法互相學到 prefix。沒有「在 DX gateway 啟用路由傳遞」這種設定可以替代 SiteLink。
>
> **考點**：SAP-1.1｜DX SiteLink 讓地端站點經 AWS 骨幹互通｜延伸閱讀：第 8 章

### 第 2 題｜SAP｜單選｜D2 電子病歷資料庫的跨 Region 復原

康橋醫療集團的電子病歷系統跑在 ap-northeast-1 的 Aurora PostgreSQL，資料量 8 TB，每秒約 3,000 筆寫入。新的法規稽核要求：主要 Region 整區故障時，資料遺失不得超過 1 分鐘，系統要在 30 分鐘內於另一個 Region 恢復寫入。資安部也希望平時就能在備援 Region 執行唯讀的報表查詢，減輕主要資料庫的負擔。維運團隊只有三人，偏好受管機制。

哪個方案能以最少的維運負擔滿足 RPO 與 RTO？

- A. 啟用 AWS Backup 每小時 snapshot，並設定 copy job 把每份 recovery point 複製到 ap-southeast-1，故障時從最新的複本還原新 cluster
- B. 在 ap-southeast-1 建立另一個 Aurora PostgreSQL cluster，用 AWS DMS 做 full load 加 CDC 持續同步，故障時把應用程式連線字串改到新 cluster
- C. 把現有 cluster 加入 Aurora Global Database，在 ap-southeast-1 建立 secondary cluster 並放入 reader instance 供報表使用，故障時執行 global database 的 failover
- D. 在同一 Region 把 Aurora Replicas 增加到 15 個並分散在三個 AZ，讓報表查詢使用 reader endpoint，並開啟 backtrack 防範邏輯錯誤

> [!answer]- 答案：C
> **A ✗** 每小時 snapshot 的 RPO 最差接近 1 小時，而且 8 TB 的 snapshot 還原時間不容易保證在 30 分鐘內。若 RPO 是 24 小時、成本是唯一考量，備份複製才會是合理的 DR 做法。
>
> **B ✗** DMS CDC 可以做跨 Region 同步，但延遲沒有保證，大量寫入時可能落後；還要自己監控 task、處理 schema 變更與 sequence，維運負擔明顯高於受管的 Global Database。若目標是異質資料庫（例如 Oracle → Aurora），DMS 才是主角。
>
> **C ✓** **Aurora Global Database** 在儲存層做跨 Region 複寫，典型延遲低於 1 秒，能滿足 1 分鐘 RPO；secondary Region 的 reader instance 可直接承接唯讀報表。主要 Region 故障時，可對 global database 執行 failover，讓 secondary cluster 升為可寫，通常數分鐘內完成，落在 30 分鐘 RTO 內。
>
> **D ✗** Aurora Replicas 與 backtrack 都只在單一 Region 內，Region 整區故障時全部一起失效。backtrack 也只支援 Aurora MySQL，不支援 PostgreSQL。這個設計只解決了「同 Region 讀取擴展」。
>
> **考點**：SAP-2.2｜Aurora Global Database 的 RPO／RTO 與 secondary 讀取｜延伸閱讀：第 26 章、第 34 章

### 第 3 題｜SAP｜單選｜D3 全組織找出含個資的 bucket

國家社會福利署有 180 個 AWS 帳號，由 AWS Organizations 管理，各縣市分署可以自行建立 S3 bucket 存放申請資料。最近一次稽核發現，有分署把含身分證字號與病歷摘要的 CSV 放進命名為 `temp-share` 的 bucket，稽核單位要求資安中心能持續掌握「哪些 bucket 含有敏感個資、是否公開或跨帳號共享」，並把結果送進現有的 Security Hub 統一追蹤。資安中心只有兩人，不能逐帳號手動設定，也無法撰寫掃描程式。

哪個方案最符合需求？

- A. 在組織中把資安帳號指定為 Amazon Macie 的 delegated administrator，自動為所有成員帳號啟用 Macie，開啟 automated sensitive data discovery，並把 findings 發布到 Security Hub
- B. 在組織層級啟用 GuardDuty 並開啟 S3 Protection，讓它分析 CloudTrail S3 data events，找出存放身分證字號的 bucket 並送進 Security Hub
- C. 用 AWS Config 的 organization conformance pack 部署 `s3-bucket-public-read-prohibited` 等 managed rules，再把 Config 的 aggregator 結果匯入 Security Hub
- D. 為每個帳號啟用 S3 Inventory 輸出到集中 bucket，以 Athena 搭配 Lambda 定期下載物件、用正規表示式比對身分證字號格式，結果寫入 Security Hub

> [!answer]- 答案：A
> **A ✓** **Amazon Macie** 專門掃描 S3 物件內容、辨識個資等敏感資料，同時評估 bucket 是否公開或與外部帳號共享。透過 Organizations 指定 delegated administrator 後，可以集中為所有成員帳號啟用；automated sensitive data discovery 會持續抽樣評估整個 S3 資產，不必自訂掃描工作。Macie findings 可以直接發布到 Security Hub。
>
> **B ✗** GuardDuty S3 Protection 偵測的是「可疑的存取行為」（例如異常 API 呼叫、已知惡意 IP），它不讀物件內容，因此不知道哪個 bucket 有身分證字號。若題目問的是「資料被異常外洩下載」，GuardDuty 才是答案。
>
> **C ✗** Config rules 檢查的是資源「設定」，例如是否公開或有無加密，無法判斷內容是否含個資。它能補足部分需求，但核心的「哪些 bucket 有敏感資料」做不到。
>
> **D ✗** 自建掃描在技術上可行，但需要開發與維運，正規表示式也容易誤判，還違反「無法撰寫掃描程式」的限制。只有在要辨識非常特殊、Macie 自訂 data identifier 也表達不了的格式時，才需要考慮自建。
>
> **考點**：SAP-3.2｜Macie delegated admin 與 automated sensitive data discovery｜延伸閱讀：第 16 章

### 第 4 題｜SAP｜選兩項｜D4 大規模 VMware 遷移的相依分析與低停機切換

遠翔航空貨運要在 14 個月內關閉地端機房，裡面有約 2,000 台 VMware VM，執行艙位訂位、倉儲管理與海關申報等系統，多數系統的文件早已過時，沒人能完整說清楚哪些伺服器彼此相依。公司在 2024 年做初步評估時就已啟用 Application Discovery Service 與 Migration Hub，屬於這兩個服務的既有客戶。管理層決定先以 rehost 為主，之後再逐步現代化。限制是：每個系統的切換停機時間不得超過 1 小時；必須依相依關係分批（wave）遷移，避免把彼此頻繁通訊的伺服器拆到不同批次。

哪兩個步驟最適合？（選兩項）

- A. 在代表性伺服器安裝 AWS Application Discovery Service 的 discovery agent，收集程序與網路連線資料，依實際通訊關係把伺服器分組，規劃 wave
- B. 用 VM Import/Export 把每台 VM 匯出成 OVA 檔上傳到 S3，再匯入成 AMI 後啟動 EC2
- C. 為所有伺服器（包含應用程式伺服器與檔案伺服器）建立 AWS DMS replication task，把磁碟資料持續同步到 AWS
- D. 用 AWS Application Migration Service（MGN）在來源伺服器安裝 replication agent，做持續的 block-level 複寫，先 test launch 驗證，再於維護時段執行 cutover
- E. 用 AWS DataSync 把每台 VM 的虛擬磁碟檔（VMDK）複製到 S3，再轉換為 EBS snapshot 建立 instance

> [!answer]- 答案：A、D
> **A ✓** 文件過時時，必須用實際觀測資料找出相依關係。**Application Discovery Service** 的 agent 會收集伺服器上的程序與 TCP 連線，讓你看出哪些伺服器彼此頻繁通訊，進而把它們放進同一個 wave。若只需要 CPU、記憶體等容量資料做 TCO 估算，agentless collector 就夠了，但它無法提供同等深度的程序層相依資訊。注意：ADS 與 Migration Hub 自 2025-11-07 起不再開放新客戶，題目中的公司是既有客戶所以可以使用；從未用過的組織要改用 AWS Transform 的探索與 wave 規劃功能。
>
> **B ✗** VM Import/Export 是一次性的映像轉換：匯出、上傳、匯入期間來源 VM 仍在變動，最後必須停機重做一次，大型 VM 很難控制在 1 小時內，2,000 台的規模也難以管理。少量、可長時間停機的 VM 才適合。
>
> **C ✗** DMS 只遷移資料庫的資料，不會複製作業系統、應用程式或檔案伺服器磁碟。資料庫要換引擎或需要 CDC 時才用 DMS。
>
> **D ✓** **MGN** 在背景持續做 block-level 複寫，來源伺服器照常運作；切換時只需最後一次同步並啟動目標 instance，停機通常是分鐘級。test launch 讓每個 wave 先演練，是大規模 rehost 的標準做法。
>
> **E ✗** DataSync 處理的是檔案與物件的搬移，不會處理執行中 VM 的一致性快照，也不負責轉換成可開機的 instance。它適合 NAS 或檔案共享的資料搬遷。
>
> **考點**：SAP-4.2、SAP-4.1｜相依探索決定 wave，MGN 持續複寫降低停機｜延伸閱讀：第 44 章、第 45 章

### 第 5 題｜SAP｜單選｜D1 限制單一租戶故障的影響範圍

雲序科技提供跨國人資 SaaS，約 4,000 家企業租戶共用同一套部署：API Gateway、ECS on Fargate 服務與 Aurora 叢集，橫跨三個 AZ。上個月一個大型租戶匯入了格式異常的薪資檔，觸發程式缺陷，導致所有 ECS task 連續崩潰，全部租戶中斷 2 小時。CTO 要求重新設計，讓類似的「毒藥請求」或錯誤部署最多只影響一小部分租戶，同時不想為每個租戶各自維運一套環境。

哪個方案最能達成目標？

- A. 把 ECS 服務的 task 數提高到目前的三倍並啟用 Service Auto Scaling，讓部分 task 崩潰時仍有足夠容量承接流量
- B. 在第二個 Region 部署同樣的環境做 active-active，用 Route 53 latency routing 分流，任一 Region 故障時由另一個 Region 承接
- C. 為每個租戶建立 API Gateway usage plan 與 API key，限制單一租戶每秒的請求數與每日配額
- D. 改成 cell-based 架構：建立多個完整且彼此獨立的 cell（各自有運算與資料庫），以輕量的路由層依租戶 ID 對應到固定的 cell，並讓部署依 cell 逐一推出

> [!answer]- 答案：D
> **A ✗** 毒藥請求會讓每一個處理它的 task 崩潰，task 再多也會被重試的請求逐一打倒。擴容只能處理「容量不足」，處理不了「共用的故障模式」。
>
> **B ✗** 毒藥請求與錯誤部署會被複製到兩個 Region，兩邊一起倒。多 Region 解決的是 Region 級基礎設施故障，不能縮小應用層缺陷的影響範圍。
>
> **C ✗** Usage plan 能限制吵鬧鄰居的請求量，但一筆異常請求就足以觸發崩潰，與請求量無關。若問題是單一租戶耗盡共用容量，這才是對的工具。
>
> **D ✓** **Cell-based 架構**把系統切成多個完全獨立的副本，每個 cell 只服務一部分租戶。毒藥請求只會打倒它所在的 cell；部署也依 cell 逐一推出，有問題時只影響第一個 cell。路由層要盡量簡單，避免它本身變成新的共用故障點。這是「限制 blast radius」的標準答案，又不必一租戶一環境。
>
> **考點**：SAP-1.3｜cell-based architecture 縮小 blast radius｜延伸閱讀：第 35 章、第 49 章

### 第 6 題｜SAP｜單選｜D2 新帳號自動套用基線

海嶼電信用 AWS Organizations 管理 120 個帳號，沒有使用 Control Tower，短期內也不打算導入。資安部要求每個帳號都必須有一組標準資源：一個供資安團隊稽核用的 IAM role、一組 CloudWatch alarm，以及一個把 VPC Flow Logs 送到集中帳號的設定。每個月會新增 5–10 個帳號，過去常有新帳號忘了部署基線而被稽核點名。團隊希望用 CloudFormation 管理基線，而且新帳號一加入指定 OU 就自動套用，不需要人工介入。

哪個方案的維運負擔最低？

- A. 在每個帳號手動建立 `AWSCloudFormationStackSetExecutionRole`，再於管理帳號建立 self-managed permissions 的 StackSet，每次新帳號加入時把帳號 ID 加入 StackSet 的 deployment targets
- B. 啟用 StackSets 與 Organizations 的 trusted access，建立 service-managed permissions 的 StackSet 並以 OU 為 deployment target，開啟 automatic deployment，必要時把資安帳號註冊為 StackSets 的 delegated administrator
- C. 在 Service Catalog 建立包含基線範本的 portfolio 並分享給整個組織，要求各帳號負責人在開帳號後自行從 Service Catalog 啟動產品
- D. 用 EventBridge 規則攔截 Organizations 的 `CreateAccount` 事件，觸發 Lambda 以 assume role 進入新帳號，再呼叫 CloudFormation `CreateStack` 部署基線

> [!answer]- 答案：B
> **A ✗** Self-managed permissions 要求每個目標帳號事先建立 execution role，新帳號也要有人記得加進 deployment targets，正是過去出錯的根源。只有目標帳號不在同一個 Organization 時才需要用它。
>
> **B ✓** **Service-managed permissions** 的 StackSet 由 Organizations 自動建立所需的 role；以 OU 為目標並開啟 **automatic deployment** 後，帳號一移入該 OU 就自動部署，帳號移出時也可以設定自動刪除 stack instance。註冊 delegated administrator 能避免日常操作都在管理帳號進行。
>
> **C ✗** Service Catalog 適合讓團隊「自助」選用標準產品，但仍需人工啟動，無法保證每個新帳號都有基線。
>
> **D ✗** 事件驅動的自建流程做得到，但要自己處理重試、多 Region、更新既有帳號與漂移，維運負擔遠高於 StackSets 內建的功能。另外，`CreateAccount` 是非同步操作，帳號真正可用前就觸發 Lambda 也可能失敗。
>
> **考點**：SAP-2.1｜StackSets service-managed 與 automatic deployment｜延伸閱讀：第 37 章、第 40 章

### 第 7 題｜SAP｜單選｜D1 不用 VPN 存取院內系統

仁和醫院體系有 6,000 名醫護人員，需要從院外存取部署在 AWS 上的三個內部 web 應用（排班、檢驗報告查詢、教學平台），這些應用都在 private subnet 的 ALB 後面。目前使用者必須先連公司的 VPN，但 VPN 一旦連上就能看到整個內部網段，資安部認為風險太高。新的政策要求：每一個 HTTP 請求都要依使用者身份（公司的 IdP）與裝置狀態（端點管理工具回報的合規狀態）逐一判斷是否放行，不再提供網段層級的存取。

哪個方案最符合政策？

- A. 改用 AWS Client VPN 並啟用 SAML 聯合驗證，再以 authorization rules 限制不同群組可以存取的 CIDR
- B. 把三個 ALB 改為 internet-facing，在 listener 規則啟用 Cognito 驗證並把公司 IdP 設為 Cognito 的 SAML identity provider
- C. 建立 AWS Verified Access instance，接上公司 IdP 作為 user trust provider、端點管理工具作為 device trust provider，為每個應用建立 Verified Access endpoint 並撰寫依群組與裝置狀態放行的 policy
- D. 為醫護人員配發 Amazon WorkSpaces 虛擬桌面，在 WorkSpaces 所在的 VPC 開放對三個 ALB 的存取，使用者透過桌面瀏覽器操作

> [!answer]- 答案：C
> **A ✗** Client VPN 加 authorization rules 能縮小可達網段，但本質仍是網路層存取：使用者連上後在允許的 CIDR 內可以嘗試存取任何服務，也沒有逐請求的裝置狀態判斷。若需求只是「取代自建 VPN 伺服器」，Client VPN 才是答案。
>
> **B ✗** ALB 整合 Cognito 可以做到逐請求的身份驗證，但無法納入裝置合規狀態；把內部應用直接暴露在 Internet，也需要額外的 WAF 與防護。
>
> **C ✓** **AWS Verified Access** 是零信任（zero trust）存取服務：每個請求都依 user trust provider（IdP 的身份與群組）與 device trust provider（裝置狀態）評估以 Cedar 語言撰寫的 policy，通過才轉送到後端應用，使用者完全不需要 VPN，也拿不到任何網段層級的連線。
>
> **D ✗** 虛擬桌面能隔離端點，但每人一台 WorkSpaces 成本很高，而且桌面所在的 VPC 仍是網段層級存取，沒有逐請求依身份判斷。若需求是「端點不可留存任何資料」，VDI 才值得考慮。
>
> **考點**：SAP-1.2｜Verified Access 依身份與裝置逐請求授權｜延伸閱讀：第 13 章

### 第 8 題｜SAP｜單選｜D3 早上尖峰的報表查詢排隊

Telvia 電信的營運儀表板查詢 Amazon Redshift provisioned cluster（4 個 ra3.4xlarge 節點）。每天上午 9:00–10:30，全國 300 位門市主管同時開啟儀表板，大量唯讀查詢在 WLM queue 中排隊，平均等待超過 2 分鐘；其他時段 cluster CPU 使用率低於 25%。這些查詢的長度與複雜度相近，資料每晚批次載入一次。財務部要求不得永久增加節點規模。

哪個做法最能以最低成本改善尖峰時段的查詢等待？

- A. 為處理儀表板查詢的 WLM queue 啟用 concurrency scaling，讓 Redshift 在 queue 開始排隊時自動加入暫時的運算容量
- B. 以 Redshift 的排程動作（scheduled action）每天早上把 cluster elastic resize 成 8 個節點，上午 10:30 後再縮回 4 個節點
- C. 為 WLM 啟用 short query acceleration（SQA），讓短查詢優先執行，並把 queue 的 concurrency 調高到 50
- D. 每晚批次載入後，把儀表板需要的彙總結果匯出到 Aurora PostgreSQL，讓儀表板改查 Aurora 的 read replica

> [!answer]- 答案：A
> **A ✓** **Concurrency scaling** 會在 queue 排隊時自動加入暫時的叢集處理查詢（儀表板這類讀取查詢，以及部分常見的寫入），尖峰過後自動釋放，只在 concurrency scaling 叢集實際執行查詢時計費。每個 cluster 每天會累積約一小時的免費額度（最多累積 30 小時），超過才按秒計費；每天 90 分鐘的尖峰大部分可由免費額度抵銷。對「每天固定一段時間的大量併發」這是最直接、成本最低的做法。
>
> **B ✗** 排程 resize 可以做到，但 elastic resize 期間 cluster 會有短暫的不可用，而且尖峰只有 90 分鐘，每天兩次 resize 的成本與風險都比 concurrency scaling 高。若尖峰持續數小時且也包含大量寫入，排程 resize 才較有吸引力。
>
> **C ✗** SQA 只是讓短查詢插隊，題目說查詢長度相近，插隊沒有幫助；把 concurrency 調高只是讓更多查詢分食同一組節點的記憶體與 CPU，每個查詢反而變慢。
>
> **D ✗** 另建一套 Aurora 與匯出流程會增加維運與資料一致性負擔，也改變了儀表板的資料來源。若儀表板只需少量高頻的點查詢，才值得把資料下沉到 OLTP 資料庫。
>
> **考點**：SAP-3.3｜Redshift concurrency scaling 處理併發尖峰｜延伸閱讀：第 30 章

### 第 9 題｜SAP｜選兩項｜D2 金鑰必須留在 AWS 之外

一個國家的稅務機關要把報稅資料系統遷移到 AWS，資料存放在 S3 與 EBS。依當地資料主權法規，加密金鑰的金鑰材料必須保存在機關自有機房、由機關自行管理的 HSM 中，任何時候都不得存放在雲端供應商的設施；機關也必須能在緊急時立即切斷雲端對金鑰的使用。應用程式由外包商開發，合約規定不得修改程式碼，因此必須沿用 S3 與 EBS 原生的伺服器端加密整合。

哪兩個步驟能滿足需求？（選兩項）

- A. 在機關的 HSM 產生金鑰材料，以 KMS 的 import key material（BYOK）功能匯入一把 customer managed key，供 S3 與 EBS 使用
- B. 在機房部署支援 XKS 的外部金鑰管理器與 XKS proxy，建立 AWS KMS external key store，並在其中建立 KMS key 作為 S3 預設加密（SSE-KMS）與 EBS 加密的金鑰
- C. 建立 AWS CloudHSM cluster 並以它建立 KMS custom key store，讓金鑰材料保存在單一租戶的 HSM 中
- D. 要求應用程式上傳時使用 SSE-C，在每個請求中提供由機關 HSM 產生的金鑰
- E. 以 bucket policy 搭配 `StringNotEqualsIfExists` 條件，拒絕在請求中指定其他 KMS key 的 `s3:PutObject`（沒帶加密 header 的上傳會套用 bucket 預設加密的 XKS 金鑰），並把各 Region 的 EBS 預設加密金鑰指定為該金鑰，防止有人改用其他金鑰

> [!answer]- 答案：B、E
> **A ✗** 匯入金鑰材料後，材料會保存在 AWS KMS 的 HSM 中，只是由你決定來源與到期時間，仍違反「不得存放在雲端供應商的設施」。若法規只要求「金鑰由自己產生並可設定到期」，BYOK 才足夠。
>
> **B ✓** **KMS external key store（XKS）** 讓 KMS key 的金鑰材料留在你自己的外部金鑰管理器，每次加解密時 KMS 透過 XKS proxy 請外部系統執行運算。S3 與 EBS 照常使用 KMS 整合，應用程式不必修改；機關切斷 proxy 或停用外部金鑰後，新的加解密請求就會失敗（已掛載的 EBS volume 等已在記憶體中的資料金鑰可能繼續使用到卸載為止）。代價是可用性與延遲取決於你的外部系統與網路。
>
> **C ✗** CloudHSM 雖然是單一租戶、由你掌控金鑰，但 HSM 仍位於 AWS 的資料中心，不符合主權法規。若要求是「單一租戶 HSM、FIPS 驗證、由客戶獨占」，CloudHSM custom key store 才是答案。
>
> **D ✗** SSE-C 的確不會讓 AWS 保存金鑰，但每個請求都要由應用程式帶入金鑰，等於修改程式碼，也不適用 EBS。
>
> **E ✓** 有了正確的金鑰還要防止繞過：bucket policy 可依 `s3:x-amz-server-side-encryption-aws-kms-key-id` 條件拒絕指定其他金鑰的上傳。用 `IfExists` 版本的條件很重要：外包商的程式沒有帶加密 header，若改用一般的 `StringNotEquals`，這些依賴預設加密的上傳也會被拒絕。EBS 的帳號層級預設加密（每個 Region 各自設定）可以指定這把金鑰。兩者組合確保新資料都受外部金鑰保護。
>
> **考點**：SAP-2.3｜KMS external key store 與強制使用指定金鑰｜延伸閱讀：第 15 章

### 第 10 題｜SAP｜單選｜D4 挑選第一批遷移的系統

明德醫學中心決定把地端系統遷移到 AWS，雲端團隊剛完成 landing zone：Direct Connect、與院內 Active Directory 的整合、集中監控與備份政策都已建好但尚未經過實際驗證。院方希望第一批（pilot wave）在 8 週內完成，目的是驗證這些共用基礎設施，同時累積團隊經驗，並在不影響病患照護的前提下讓管理層看到成果。以下是四個候選系統。

哪個系統最適合放在第一批？

- A. 核心醫療資訊系統（HIS），Oracle RAC 加上 40 個對外介面，每天 24 小時服務門急診，院方已編列兩年改寫預算
- B. 實驗室儀器資料收集系統，已確定將在 6 個月後由新的 SaaS 產品取代並停止使用
- C. 放射影像 PACS，存放 1.5 PB 影像，與院內的 CT、MRI 設備以 DICOM 低延遲通訊，任何延遲都會影響檢查流程
- D. 員工教育訓練平台：Linux 上的 Java 應用與 MySQL，使用院內 AD 驗證並讀取一個 Windows 檔案分享，相依系統少，系統負責人主動爭取參與

> [!answer]- 答案：D
> **A ✗** HIS 是最關鍵、相依最多的系統，放在第一批風險最高；它正在規劃改寫，更適合在團隊累積經驗後以 refactor 方式處理。
>
> **B ✗** 6 個月後就要停用的系統應該 retain 到期後 retire，遷移它浪費人力，也無法驗證 landing zone 的長期使用情境。這是 7Rs 中「不要搬」的典型案例。
>
> **C ✗** PACS 資料量大，又與院內醫療設備有嚴格的低延遲需求，搬到雲端可能直接影響檢查流程，不適合當作試水溫的第一批，甚至可能適合長期 retain 在院內或改採 hybrid 架構。
>
> **D ✓** 好的 pilot wave 應該是：業務重要性中等、相依少、技術上具代表性、負責人配合度高。這個平台會用到 AD 驗證、檔案分享、DX 連線與資料庫遷移，剛好能驗證 landing zone 的各項共用元件，出問題也不影響病患照護。
>
> **考點**：SAP-4.1｜pilot wave 的選擇標準｜延伸閱讀：第 44 章

### 第 11 題｜SAP｜單選｜D1 以 Terraform 供應新帳號

Fieldnote 是一家跨國專案管理 SaaS 公司，已經用 AWS Control Tower 建立 landing zone，管理 70 個帳號。公司所有基礎設施都以 Terraform 管理，平台團隊希望「開新帳號」也能像其他變更一樣：工程師提交一個描述帳號需求（帳號名稱、OU、預算標籤）的 pull request，審核合併後自動建立帳號，並自動套用公司用 Terraform 寫好的帳號層級客製化（例如預設 IAM role、VPC）。團隊不想維護 CloudFormation 範本，也不想撰寫自己的帳號供應程式。

哪個方案最符合需求？

- A. 使用 Customizations for AWS Control Tower（CfCT），把帳號客製化改寫為 CloudFormation 範本與 SCP，放進 CfCT 的設定 repository
- B. 撰寫 Terraform 程式直接呼叫 Organizations 的 `CreateAccount` API 建立帳號，再於 pipeline 中切換到新帳號套用其他 Terraform module
- C. 部署 Account Factory for Terraform（AFT），以 Git repository 中的帳號請求檔觸發 Control Tower Account Factory 建立帳號，並以 AFT 的 account customizations 套用既有的 Terraform module
- D. 在 Control Tower 主控台使用 Account Factory 逐一建立帳號，建立後由平台團隊在新帳號手動執行 Terraform 套用客製化

> [!answer]- 答案：C
> **A ✗** CfCT 是 Control Tower 官方的客製化方案，但它以 CloudFormation 範本與 SCP 為主，違反「不想維護 CloudFormation」的限制。團隊若以 CloudFormation 為標準，CfCT 才是答案。
>
> **B ✗** 直接呼叫 `CreateAccount` 建立的帳號不會被 Control Tower enroll，也不會自動套用 Control Tower 的 controls，還要自己處理非同步建立的等待與錯誤，等於自己寫了一套帳號供應程式。
>
> **C ✓** **Account Factory for Terraform（AFT）** 是以 GitOps 方式供應 Control Tower 帳號的官方方案：在 repository 中提交帳號請求，AFT pipeline 呼叫 Account Factory 建立並 enroll 帳號，再依 global 與 account customizations 執行團隊的 Terraform。整個流程不需撰寫 CloudFormation。
>
> **D ✗** 主控台手動建立可行，但每個帳號都需要人工操作與手動套用 Terraform，無法達成 pull request 驅動的自動化，也容易漏做客製化。
>
> **考點**：SAP-1.4｜Control Tower 搭配 AFT 的 GitOps 帳號供應｜延伸閱讀：第 40 章

### 第 12 題｜SAP｜單選｜D3 設定變更造成事故

風岬能源經營多座離岸風場，交易部門的電力競價服務部署在 ECS 上，服務中有數十個業務參數（例如報價上下限、風速預測權重），目前寫在 container image 內的設定檔。每次調整參數都要重新 build、走完整部署，耗時 40 分鐘；上一季有兩次參數設定錯誤，在全部 task 生效後才被發現，造成錯誤報價。營運主管希望：參數可以在不重新部署的情況下調整，並分階段生效；若關鍵 CloudWatch alarm 在推出過程中觸發，要自動退回前一版設定。

哪個方案最符合需求，且維運負擔最低？

- A. 把參數移到 Systems Manager Parameter Store，讓服務每分鐘輪詢一次；設定 EventBridge 規則在 alarm 觸發時呼叫 Lambda，把參數改回前一個版本
- B. 把參數移到 AWS AppConfig 的 configuration profile，以帶有 bake time 的漸進式 deployment strategy 推出設定，並把關鍵 CloudWatch alarm 設為 deployment 的 rollback 監控
- C. 保留設定檔在 image 內，改用 CodeDeploy 的 ECS blue/green 部署，搭配 CloudWatch alarm 讓錯誤版本自動回滾
- D. 把設定檔放到啟用 versioning 的 S3 bucket，服務啟動時讀取；需要退回時由值班人員還原前一個 object 版本並重新啟動 task

> [!answer]- 答案：B
> **A ✗** Parameter Store 可以集中參數，但沒有漸進式推出的機制，新值一寫入就被所有 task 輪詢讀到；自動回退要自己寫 Lambda 並追蹤版本，還要處理推出到一半的狀態。若只需要集中存放少量參數，Parameter Store 才是較簡單的選擇。
>
> **B ✓** **AWS AppConfig** 專門處理執行期設定與 feature flag：設定與程式碼分離、可先驗證格式，並用 deployment strategy 控制推出比例與 bake time。推出期間若指定的 CloudWatch alarm 進入 ALARM，AppConfig 會自動 rollback 到前一版設定，正好對應「分階段生效、自動退回」的需求。
>
> **C ✗** Blue/green 能讓錯誤的「程式版本」自動回滾，但每次調參數仍要重新 build 與部署 40 分鐘，沒有解決「不需重新部署」的需求。
>
> **D ✗** S3 versioning 只是保留舊版，退回仍要人工判斷並重啟 task，不是自動化，也沒有分階段生效。
>
> **考點**：SAP-3.1｜AppConfig 漸進式設定部署與 alarm 自動回滾｜延伸閱讀：第 37 章、第 38 章

### 第 13 題｜SAP｜單選｜D2 多個 consumer 搶同一條 stream

Orbis Mobile 把全國基地台產生的通話詳細紀錄（CDR）寫入一條 Kinesis Data Streams（provisioned mode，40 個 shard），寫入量只用到 shard 寫入上限的約 30%。這條 stream 有 6 個獨立的 consumer 應用：詐欺偵測、即時計費、網路品質監控等，都用 KCL 以 polling 方式讀取。最近新增第 6 個 consumer 後，各 consumer 頻繁出現 `ReadProvisionedThroughputExceededException`，詐欺偵測的處理延遲從 1 秒升到 8 秒。詐欺偵測要求端到端延遲低於 2 秒，而且未來還會再增加 consumer。

哪個方案最能以合理成本解決問題？

- A. 把 shard 數從 40 增加到 120，讓每個 consumer 分到的讀取頻寬增加三倍
- B. 把 stream 改為 on-demand capacity mode，讓 Kinesis 依流量自動調整 shard 數
- C. 在 stream 後面加一個 Amazon Data Firehose delivery stream，把資料複製到 6 個 SQS queue，各 consumer 改讀自己的 queue
- D. 把延遲敏感的 consumer 註冊為 enhanced fan-out consumer，改用 `SubscribeToShard` 推送模式讀取，讓每個 consumer 在每個 shard 都有專屬的讀取頻寬

> [!answer]- 答案：D
> **A ✗** 增加 shard 確實提高總讀取量，但寫入只用到 30%，為了讀取把 shard 增加三倍會讓 shard 費用跟著三倍；而且 polling 模式下每個 shard 每秒最多 5 次 `GetRecords`，consumer 越多，每個 consumer 的輪詢間隔仍會拉長。
>
> **B ✗** On-demand mode 解決的是「寫入量難以預測」，shard 數主要依寫入流量調整；共用讀取的模式沒有改變，6 個 consumer 仍在同一個 shard 上搶讀取額度。
>
> **C ✗** Firehose 是把資料送到 S3、Redshift、OpenSearch 等目的地的交付服務，不能把資料直接分送到多個 SQS queue。即使自己串接，也會增加延遲與元件，違反 2 秒延遲的要求。
>
> **D ✓** 標準 consumer 共用每個 shard 每秒 2 MB 的讀取頻寬；**enhanced fan-out** 讓每個註冊的 consumer 在每個 shard 都有專屬的 2 MB/s，資料以 HTTP/2 推送，延遲通常約 70 毫秒。它另外按 consumer-shard 時數與資料量計費，但比為了讀取而大量增加 shard 划算，也能支撐未來更多 consumer。
>
> **考點**：SAP-2.5｜Kinesis enhanced fan-out 解決多 consumer 讀取瓶頸｜延伸閱讀：第 31 章

### 第 14 題｜SAP｜單選｜D1 及早發現異常支出

Quorvia 是一家跨國電子簽章 SaaS 公司，在 Organizations 中有 45 個帳號，各產品團隊擁有自己的帳號。去年發生兩次意外：一次是測試腳本錯誤地持續建立 GPU instance，另一次是 NAT Gateway 的資料處理費在一週內暴增十倍，兩次都到月底看帳單才發現。各帳號的支出隨業務季節波動很大，財務部嘗試為每個帳號設定固定的預算門檻，結果誤報太多被大家忽略。財務長希望在支出出現「與歷史模式不符的異常」時，24 小時內通知該帳號的負責團隊，且不必人工維護門檻。

哪個方案最符合需求？

- A. 在管理帳號啟用 AWS Cost Anomaly Detection，建立依 linked account 劃分的 cost monitor，並為每個 monitor 設定 alert subscription，以每日或即時的方式透過 SNS 通知各團隊
- B. 在每個帳號建立 AWS Budgets，把預算設為上月實際支出的 120%，超過時寄信給帳號負責人
- C. 在每個帳號的 us-east-1 建立 `EstimatedCharges` 的 CloudWatch billing alarm，以 anomaly detection band 判斷是否異常並發送 SNS 通知
- D. 每週由財務分析師在 Cost Explorer 依帳號與服務檢視趨勢，發現異常時開立工單給該團隊

> [!answer]- 答案：A
> **A ✓** **Cost Anomaly Detection** 以機器學習建立每個 monitor 的歷史支出模式，自動考慮季節性，發現異常時依設定的頻率通知，並指出可能的根因（帳號、服務、usage type）。依 linked account 建立 monitor 正好對應「通知該帳號的負責團隊」，不需要維護固定門檻。
>
> **B ✗** 以上月支出的固定比例當門檻，正是誤報太多的原因：季節波動會觸發假警報，而真正的異常若發生在支出較低的月份可能又不會觸發。Budgets 適合「有明確上限」的控管，例如沙盒帳號每月不得超過 500 美元。
>
> **C ✗** Billing metric 只在 us-east-1 提供，而且是累計的預估總費用，每月重置，並不適合直接套用 anomaly detection band 判斷異常；要細分到服務還要大量自建設定，維護負擔高。
>
> **D ✗** 人工每週檢視最晚要一週才發現，不符合 24 小時內通知的要求，也無法擴展到 45 個帳號。
>
> **考點**：SAP-1.5｜Cost Anomaly Detection 依帳號監控異常支出｜延伸閱讀：第 39 章、第 43 章

### 第 15 題｜SAP｜選兩項｜D2 AZ 故障時仍維持訂位服務

天穹航空的線上報到與座位選擇服務部署在單一 Region 的三個 AZ：ALB 後面是 EC2 Auto Scaling group，資料層是 Aurora 與 DynamoDB。過去一次 AZ 部分故障（網路封包遺失率升高，但 instance 健康檢查時好時壞）期間，報到成功率掉到 60%，持續 50 分鐘。事後檢討發現：一是故障 AZ 的 instance 沒有被完全移出流量；二是團隊嘗試在其他 AZ 擴容時，新的 instance 啟動緩慢。航空公司要求下次 AZ 發生類似故障時，能在數分鐘內自動把流量移出該 AZ，且剩下的 AZ 能立刻承接全部流量。

哪兩個做法最能達成目標？（選兩項）

- A. 為 ALB 與 Auto Scaling group 啟用 Route 53 Application Recovery Controller 的 zonal autoshift，並設定定期的 practice run 驗證移轉後服務仍正常
- B. 把 ALB 的健康檢查間隔縮短到 5 秒、unhealthy threshold 設為 2，讓故障 AZ 的 instance 更快被標記為不健康
- C. 依 static stability 原則預先配置容量：讓任意兩個 AZ 的既有 instance 就能承接 100% 尖峰流量，不依賴故障當下再擴容
- D. 在第二個 Region 建立完整的備援環境，以 Route 53 failover routing 在主要 Region 健康檢查失敗時切換
- E. 為 Auto Scaling group 設定 target tracking，CPU 目標值從 60% 降為 40%，讓其他 AZ 在故障時更快擴容

> [!answer]- 答案：A、C
> **A ✓** 灰色故障（gray failure）時健康檢查時好時壞，單靠 instance 健康檢查無法穩定移出流量。**Zonal shift** 會把整個 AZ 從 ALB 的流量中移出（ARC 支援 ALB、NLB、EC2 Auto Scaling group 與 EKS；ALB 不論是否啟用 cross-zone load balancing 都支援；Auto Scaling group 啟用後也會避免在被移出的 AZ 啟動新 instance）；**zonal autoshift** 則在 AWS 偵測到該 AZ 可能受損時自動執行，practice run 定期演練，確保移出一個 AZ 時服務仍正常。
>
> **B ✗** 更敏感的健康檢查在灰色故障中容易讓 instance 在健康與不健康之間來回跳動，還可能誤殺其他 AZ 中短暫變慢的 instance。它無法以 AZ 為單位處理問題。
>
> **C ✓** **Static stability** 意指故障發生時不需要任何控制平面操作（例如啟動新 instance）就能維持服務。三個 AZ 各配置可承接 50% 尖峰的容量，任一 AZ 失效時剩下兩個 AZ 合計即可承接 100%，直接解決「擴容太慢」的問題，代價是平時多付約 50% 的容量。
>
> **D ✗** 多 Region 能處理 Region 級故障，但成本與複雜度高；以 Region 為單位切換對 AZ 故障過於粗略，而且 Route 53 failover 同樣依賴健康檢查，灰色故障時不一定觸發。
>
> **E ✗** 降低 CPU 目標值只是讓平時保有較多空間，故障時仍要依賴新 instance 啟動；而灰色故障下 CPU 未必升高，擴容不一定會被觸發。
>
> **考點**：SAP-2.4｜zonal autoshift 與 static stability｜延伸閱讀：第 34 章、第 35 章

### 第 16 題｜SAP｜單選｜D3 Lambda 連線風暴壓垮資料庫

安心診是一個遠距醫療平台，掛號 API 由 API Gateway 與 Lambda 組成，後端是 Aurora PostgreSQL（一個 writer、兩個 reader）。每天早上 8 點開放掛號時，Lambda 並行數在一分鐘內從 50 升到 1,500，資料庫出現大量 `too many connections` 錯誤，CPU 有一半花在建立與關閉連線上。另外，上次 writer failover 時，應用程式花了將近兩分鐘才重新連上。團隊希望在不大幅修改程式的前提下改善這兩個問題。

哪個方案最合適？

- A. 把 Aurora writer 升級為記憶體加倍的 instance class，並把 `max_connections` 參數調高到 5,000
- B. 為 Lambda 設定 reserved concurrency 為 100，讓同時連線資料庫的函式數量不超過資料庫的連線上限
- C. 在 Aurora 前面建立 Amazon RDS Proxy，Lambda 改連 proxy endpoint，並以 Secrets Manager 或 IAM 驗證連線
- D. 在 Lambda 與資料庫之間加入 ElastiCache，所有查詢先查快取，未命中才連資料庫

> [!answer]- 答案：C
> **A ✗** 調高 `max_connections` 只是讓資料庫能接受更多連線，大量連線本身就會耗用記憶體與 CPU，建立連線的開銷依舊存在；failover 慢的問題也沒有改善。
>
> **B ✗** Reserved concurrency 能限制同時執行數，但掛號尖峰的請求會因 Lambda throttle 而回傳錯誤給使用者，等於把資料庫的問題轉嫁給病患。若請求可以非同步排隊處理，限制並行數才是合理做法。
>
> **C ✓** **RDS Proxy** 維護一個連線池，讓數千個 Lambda 執行環境共用少量的資料庫連線，消除連線建立風暴；failover 時 proxy 保持 client 連線並直接轉到新的 writer，能大幅縮短應用程式感受到的中斷時間。應用程式只需改連線端點。
>
> **D ✗** 快取能減少讀取，但掛號是寫入為主的交易，仍要連資料庫；而且引入快取需要改寫資料存取邏輯，也沒有解決 failover 問題。
>
> **考點**：SAP-3.4｜RDS Proxy 處理連線風暴並縮短 failover｜延伸閱讀：第 19 章、第 26 章

### 第 17 題｜SAP｜單選｜D4 有狀態的報稅網站要能彈性擴展

某市政府稅務局的線上報稅網站是 Java 應用，目前在兩台大型 EC2 上執行，使用者的申報草稿暫存在 application server 的記憶體 session 中，ALB 啟用 sticky session。每年 5 月申報期流量是平時的 20 倍，團隊嘗試導入 Auto Scaling，但只要 scale-in 或 instance 被替換，正在填寫的民眾就會遺失草稿而必須重填，客訴大增。稅務局要求申報期間能依流量自動擴縮，任何 instance 被移除都不能讓民眾遺失資料，且程式修改越少越好。

哪個方案最合適？

- A. 把 sticky session 的 cookie 有效時間延長到 8 小時，並把 ALB 的 deregistration delay 設為最大值，讓 instance 在移除前有足夠時間服務完既有使用者
- B. 修改 session 管理設定，把 session 外部化存放到 Amazon ElastiCache（Valkey 或 Redis OSS）或 DynamoDB，關閉 sticky session，再讓 Auto Scaling group 依請求數擴縮
- C. 改用記憶體為四倍的 instance type 垂直擴展，並在申報期前手動把兩台 instance 都升級
- D. 為 Auto Scaling group 設定 lifecycle hook，scale-in 時讓 instance 停留在 `Terminating:Wait` 狀態兩小時，等使用者離開後再終止

> [!answer]- 答案：B
> **A ✗** 延長 sticky 時間只會讓負載更不平均，新 instance 很難分到流量；deregistration delay 最長 3,600 秒，填寫中的民眾仍可能在 instance 移除時遺失草稿，instance 意外故障時則完全無法保護。
>
> **B ✓** 把 session 狀態移出 application server，讓應用層變成 **stateless**，是可彈性擴展的前提：任何 instance 被移除，下一個請求到其他 instance 仍能讀到草稿。Java 應用通常只需換 session store 的設定或函式庫，程式修改很少；ElastiCache 提供低延遲，DynamoDB 則免維運並可用 TTL 自動清除過期 session。
>
> **C ✗** 垂直擴展無法自動擴縮，仍有兩台單點，instance 故障或維護時資料一樣會遺失。
>
> **D ✗** Lifecycle hook 可以延後終止（最長 48 小時），但這只能處理「計畫性 scale-in」，對健康檢查失敗或 AZ 故障造成的替換沒有幫助；拖延終止也會讓成本與擴縮反應變差。
>
> **考點**：SAP-4.3｜把 session 外部化，讓既有應用可水平擴展｜延伸閱讀：第 18 章、第 28 章

### 第 18 題｜SAP｜選兩項｜D1 讓數百個客戶私有存取 SaaS 服務

Ledgerline 是一家跨國供應鏈 SaaS 公司，要讓 300 家企業客戶從客戶自己的 AWS 帳號與 VPC 私有存取它的資料匯入 API（自訂的 TCP 協定，不是 HTTP）。客戶不在 Ledgerline 的 Organization 中，許多客戶的 VPC 都使用 `10.0.0.0/16`，彼此與 Ledgerline 的網段大量重疊。資安要求：流量不得經過 Internet，客戶只能存取這一個服務、不能看到 Ledgerline 的其他網段，並且只有完成合約的客戶帳號可以連線。

哪兩個步驟最適合？（選兩項）

- A. 與每個客戶建立 VPC peering，並在客戶端以 security group 只允許連到 API 所在 subnet 的 CIDR
- B. 在 Ledgerline 的 VPC 中以 Network Load Balancer 前置 API 服務，建立 VPC endpoint service（PrivateLink），讓客戶在自己的 VPC 建立 interface endpoint 連線
- C. 建立 Transit Gateway 並透過 AWS RAM 分享給每個客戶帳號，讓客戶把 VPC 附加上來，再以獨立的 route table 隔離不同客戶
- D. 在 endpoint service 設定 allowed principals，只列入已簽約客戶的 AWS 帳號，並開啟 acceptance required，由 Ledgerline 審核每個 endpoint 連線請求
- E. 把 NLB 改為 internet-facing 並配置 Elastic IP，在 security group 只允許客戶提供的公有 IP 位址

> [!answer]- 答案：B、D
> **A ✗** VPC peering 不允許 CIDR 重疊，大量客戶使用相同網段時根本無法建立；peering 也會讓雙方網段互相可達，不符合「只能存取這一個服務」。
>
> **B ✓** **PrivateLink** 讓客戶在自己的 VPC 中得到一個 interface endpoint（自己網段的 private IP），流量在 AWS 網路內單向送到 Ledgerline 的 NLB；雙方 CIDR 重疊也不影響，客戶也看不到 provider 的其他網段。NLB 支援任意 TCP 協定，適合非 HTTP 的服務。
>
> **C ✗** Transit Gateway 要求附加的網段不重疊才能正確路由，而且會在雙方之間建立網路層連線，管理 300 個外部客戶的路由與隔離也很複雜。
>
> **D ✓** Endpoint service 的 **allowed principals** 控制哪些帳號可以建立 endpoint，**acceptance required** 讓 provider 逐一核准連線，兩者合起來確保只有簽約客戶能連線。provider 也可以隨時拒絕或移除連線。
>
> **E ✗** Internet-facing 的 NLB 讓流量經過 Internet，違反資安要求；客戶的出口 IP 也可能變動，維護白名單很麻煩。
>
> **考點**：SAP-1.1、SAP-1.2｜PrivateLink 解決 CIDR 重疊並控制可連線帳號｜延伸閱讀：第 7 章

### 第 19 題｜SAP｜單選｜D2 架構轉型期間的承諾折扣

海港電信的計費平台目前在 us-east-1 執行約 400 台 x86 的 m5 instance，每小時 On-Demand 費用穩定約 2,000 美元。未來 18 個月的規劃是：先把一半服務改為 Graviton（m7g），再把部分服務容器化遷移到 ECS on Fargate，另外有一個新服務將部署在 eu-west-1。財務部希望現在就簽三年期承諾以降低成本，但不能因為架構轉型而讓折扣失效或被綁死在特定 instance family。

哪個購買方式最合適？

- A. 購買三年期 Compute Savings Plans，承諾金額設在轉型後預期最低的每小時運算用量
- B. 購買三年期 EC2 Instance Savings Plans，指定 us-east-1 的 m5 family，承諾金額設為目前每小時用量
- C. 購買三年期 Standard Reserved Instances，涵蓋 400 台 m5 instance，轉型後再到 RI Marketplace 出售不需要的部分
- D. 購買三年期 Convertible Reserved Instances，轉型時把 m5 換成 m7g，並在 eu-west-1 另外購買新的 Convertible RI

> [!answer]- 答案：A
> **A ✓** **Compute Savings Plans** 自動套用到任何 Region、instance family、作業系統的 EC2，也涵蓋 Fargate 與 Lambda，最適合架構轉型期。把承諾設在轉型後的最低基準用量，可避免承諾用不完；超出部分仍以 On-Demand 計費，日後可再加購。
>
> **B ✗** EC2 Instance Savings Plans 折扣較高，但綁定 Region 與 instance family；改為 m7g、遷到 Fargate 或 eu-west-1 時都不適用。若工作負載確定長期留在同一個 family 與 Region，它才是較好的選擇。
>
> **C ✗** Standard RI 綁定 instance 屬性，Marketplace 出售不保證能賣掉、也可能折價，而且 RI 不涵蓋 Fargate。這是把轉型風險留給自己的做法。
>
> **D ✗** Convertible RI 可以換 family，但只適用於 EC2、不能涵蓋 Fargate，也不能跨 Region 轉換，每次轉換都要人工操作。Compute Savings Plans 在彈性與管理負擔上都更好。
>
> **考點**：SAP-2.6｜Compute Savings Plans 涵蓋跨 family、Region 與 Fargate｜延伸閱讀：第 39 章

### 第 20 題｜SAP｜單選｜D3 存取模式不可預測的醫療影像

一家區域醫學影像中心在 S3 Standard 存放 2 PB 的影像，每年新增 300 TB，物件大小多在 5–50 MB。影像在拍攝後一個月內常被讀取；之後大多沒人看，但只要病患回診或轉院，任何年份的影像都可能突然被調閱，而且放射科醫師要求調閱時必須在毫秒等級內開始顯示。資料管理團隊無法事先預測哪些影像會被調閱，也不希望因為調閱而產生難以預估的取回費用。

哪個方案最能在符合需求的前提下降低儲存成本？

- A. 設定 lifecycle rule，物件建立 90 天後轉到 S3 Glacier Flexible Retrieval，調閱時以 Expedited retrieval 在數分鐘內取回
- B. 設定 lifecycle rule，物件建立 30 天後轉到 S3 Standard-IA，一年後轉到 S3 Glacier Instant Retrieval
- C. 把物件轉到 S3 Intelligent-Tiering，只使用自動的 Frequent、Infrequent 與 Archive Instant Access 層，不啟用需要非同步取回的 Archive Access 與 Deep Archive Access 層
- D. 把物件轉到 S3 Intelligent-Tiering，並啟用 Deep Archive Access 層，讓 180 天未存取的影像自動移到最便宜的層級

> [!answer]- 答案：C
> **A ✗** Glacier Flexible Retrieval 的取回是非同步的，即使 Expedited 也要數分鐘，且需要提出 restore 請求，不符合毫秒等級開始顯示的需求，取回費用也難以預估。
>
> **B ✗** Standard-IA 與 Glacier Instant Retrieval 都能毫秒讀取，但每次讀取都有每 GB 的取回費用；對「無法預測、偶爾大量調閱」的影像，取回費用正是團隊想避免的。若存取模式穩定可預測，固定的 lifecycle 轉換通常比 Intelligent-Tiering 更省。
>
> **C ✓** **S3 Intelligent-Tiering** 依每個物件的實際存取自動在層級間移動：30 天未存取移到 Infrequent Access、90 天未存取移到 Archive Instant Access，三層都是毫秒讀取，被存取時自動移回 Frequent 層，而且沒有取回費用，只收少量的監控費。這些影像都大於 128 KB，可以被自動分層（小於 128 KB 的物件不會被自動分層）。
>
> **D ✗** Deep Archive Access 層需要非同步 restore，取回可能長達數小時，違反毫秒等級的需求。只有能接受數小時取回的資料才應啟用這兩個選用的封存層。
>
> **考點**：SAP-3.5｜Intelligent-Tiering 的自動層與選用封存層｜延伸閱讀：第 23 章

### 第 21 題｜SAP｜單選｜D1 偏遠站點斷線時不遺失資料

一家能源公司在 120 座偏遠的變電站與太陽能場安裝了工業閘道器，每秒蒐集上千個感測值，要送到 AWS 的 Kinesis Data Streams 做即時監控與長期分析。這些站點多數透過衛星或 4G 連線，每週會有數次斷線，最長可達 12 小時；閘道器有 256 GB 的本地磁碟。營運部要求斷線期間的資料不得遺失，連線恢復後要自動補送，且希望以受管方式在數百台閘道器上統一部署與更新軟體。

哪個方案最合適？

- A. 讓閘道器以 MQTT QoS 1 直接發布到 AWS IoT Core，再以 IoT rule 寫入 Kinesis Data Streams，依靠 QoS 1 的重送機制處理斷線
- B. 在閘道器安裝 AWS IoT Greengrass，使用 stream manager 元件把資料先寫入本地磁碟的 stream，設定匯出目的地為 Kinesis Data Streams，連線恢復後自動補送；並透過 Greengrass deployment 統一管理元件版本
- C. 從每個站點建立 Site-to-Site VPN 到 AWS，在閘道器安裝 Kinesis Agent 直接寫入 Kinesis Data Streams
- D. 在每個站點部署一台 AWS Outposts server，把資料先寫入 Outposts 上的本地 EBS，再由 Lambda 定期上傳到 Kinesis Data Streams

> [!answer]- 答案：B
> **A ✗** MQTT QoS 1 只保證「已送出的訊息」至少送達一次；長時間斷線時，訊息必須暫存在裝置端的 client 佇列，一般 SDK 的離線佇列容量有限，也不保證跨重新開機保存，12 小時的大量資料很可能遺失。
>
> **B ✓** **IoT Greengrass** 是在邊緣裝置執行的受管 runtime。**Stream manager** 把資料寫入本地持久化的 stream，可設定容量與保留策略，連線恢復後自動匯出到 Kinesis Data Streams、S3 等目的地；Greengrass deployment 可對整個裝置群組推送元件版本，正好符合統一管理的需求。
>
> **C ✗** VPN 只解決傳輸加密，斷線時 VPN 本身也斷了；Kinesis Agent 主要用於讀取日誌檔並送出，並非為長時間離線緩衝設計，也沒有統一部署機制。
>
> **D ✗** Outposts server 是要放在有穩定網路與機房環境的站點、由 AWS 管理的硬體，成本高，而且需要可靠的連線回到 Region；偏遠站點的感測資料緩衝不需要這麼重的方案。
>
> **考點**：SAP-1.3｜邊緣斷線緩衝：Greengrass stream manager｜延伸閱讀：第 31 章

### 第 22 題｜SAP｜單選｜D2 地端醫療系統的低成本 DR

一家地區醫院在院內機房以 VMware 執行 35 台 Windows 與 Linux 伺服器，包含藥局系統與病房護理系統。醫院沒有第二座機房，主管機關要求建立異地災難復原：RPO 不超過 1 分鐘，RTO 不超過 1 小時，並且每季要能在不影響正式系統的情況下演練一次。預算有限，平時不能讓一整套伺服器在雲端持續執行。

哪個方案最合適？

- A. 以 AWS Backup 透過 Backup gateway 保護 VMware VM，每 4 小時備份一次並複製到 AWS，災難時把備份還原為 EC2
- B. 用 AWS Application Migration Service 持續複寫所有伺服器，並讓 AWS 上的目標 instance 長期保持執行，以便隨時切換
- C. 每晚把 VM 以 VM Import/Export 匯入為 AMI，災難時從最新的 AMI 啟動 EC2，資料庫另外以每日備份還原
- D. 使用 AWS Elastic Disaster Recovery，在來源伺服器安裝 replication agent，把資料持續複寫到 AWS 上低成本的 staging area；以 drill 功能定期演練，災難時再啟動 recovery instance

> [!answer]- 答案：D
> **A ✗** 每 4 小時一次的備份 RPO 最差接近 4 小時，遠高於 1 分鐘。若 RPO 是一天、預算極低，備份型 DR 才是合適選擇。
>
> **B ✗** MGN 的設計目的是一次性遷移，而不是長期 DR；讓目標 instance 一直執行等於維持一整套雲端環境，違反「平時不能持續執行」的預算限制。
>
> **C ✗** 每晚匯入 AMI 的 RPO 是一天，VM Import 本身也需要長時間處理，無法滿足 1 分鐘 RPO。
>
> **D ✓** **AWS Elastic Disaster Recovery（DRS）** 持續做 block-level 複寫，RPO 通常是秒級；平時只在 staging subnet 保留低成本的複寫伺服器與 EBS，災難時才啟動 recovery instance，RTO 通常是分鐘級。Drill 會啟動隔離的 recovery instance 而不中斷複寫，符合每季演練的要求。
>
> **考點**：SAP-2.2｜Elastic Disaster Recovery 的秒級 RPO 與低成本 staging｜延伸閱讀：第 34 章

### 第 23 題｜SAP｜選兩項｜D3 淘汰 IMDSv1

一家電信公司的資安團隊在滲透測試中，利用某個 web 應用的 SSRF 弱點讀取了 EC2 instance metadata，取得 instance role 的暫時憑證。公司在 Organizations 下有 60 個帳號、約 6,000 台 EC2，其中許多 instance 仍允許 IMDSv1，也有部分舊版 SDK 與第三方代理程式可能仍以 IMDSv1 讀取 metadata。資安長要求全面改用 IMDSv2，但不能因為強制切換讓正式服務中斷。

哪兩個做法組合最合適？（選兩項）

- A. 先以 CloudWatch 的 `MetadataNoToken` metric 找出仍在使用 IMDSv1 的 instance，更新其 SDK 與代理程式，確認該 metric 歸零後再把既有 instance 的 `HttpTokens` 改為 `required`
- B. 立即在所有既有 instance 上把 metadata service 關閉（`HttpEndpoint` 設為 `disabled`），再逐一確認哪些應用需要 metadata 後重新開啟
- C. 在所有 security group 加入規則，拒絕對 `169.254.169.254` 的連線，阻止應用程式讀取 metadata
- D. 在 web 應用前面加上 AWS WAF，以 managed rule 封鎖 SSRF 攻擊，認定這樣就不需要調整 IMDS 設定
- E. 以 SCP 拒絕不帶 `ec2:MetadataHttpTokens` 為 `required` 條件的 `ec2:RunInstances`，並在各帳號設定 EC2 的帳號層級 instance metadata 預設值為要求 IMDSv2，確保新的 instance 一開始就只接受 IMDSv2

> [!answer]- 答案：A、E
> **A ✓** IMDSv2 要求先以 PUT 取得 session token，大多數 SSRF 只能發出 GET，因而無法取得憑證。**`MetadataNoToken`** metric 記錄不帶 token 的 metadata 請求次數，是找出仍依賴 IMDSv1 程式的標準方法；先修正再強制，可以避免中斷。
>
> **B ✗** 直接關閉 metadata service 會讓所有依賴 instance role 憑證的應用立即失效，正是「不能造成中斷」所禁止的。
>
> **C ✗** Security group 只能寫 allow 規則，不能拒絕特定目的地；而且 metadata 流量不經過 security group 的過濾，這個方法根本做不到。
>
> **D ✗** WAF 能降低部分 SSRF 攻擊，但只是縱深防禦的一層，無法涵蓋所有應用與所有攻擊形式；根本解法仍是讓 metadata 需要 token。
>
> **E ✓** SCP 以 `ec2:MetadataHttpTokens` 條件阻止任何人啟動允許 IMDSv1 的 instance，帳號層級的 metadata 預設值則讓沒有特別指定的新 instance 自動採用 IMDSv2，兩者確保「新增的部分」不再出問題，搭配 A 逐步處理既有 instance。帳號層級設定只影響新 instance、不會改動既有 instance；要跨帳號與 Region 統一套用，也可以改用 Organizations 的 declarative policy，或在帳號層級啟用 IMDSv2 enforcement。
>
> **考點**：SAP-3.2｜IMDSv2 的漸進式強制與組織護欄｜延伸閱讀：第 14 章、第 17 章

### 第 24 題｜SAP｜單選｜D4 現代化排程批次

一家航空物流公司的關務申報批次目前在一台 EC2 上以 cron 執行：每天凌晨 1 點依序執行 6 個步驟（下載海關代碼、轉檔、驗證、上傳、對帳、寄送報告），其中轉檔步驟需要 40 分鐘與 8 GB 記憶體，程式已經打包成 container image。這台 EC2 白天閒置，任何一步失敗都要值班人員登入查看日誌並手動從失敗步驟重跑。團隊希望去掉這台常駐伺服器，每一步失敗時能自動重試、清楚看到每次執行在哪一步失敗，並能從失敗步驟重新開始。

哪個方案最符合需求，且維運負擔最低？

- A. 以 EventBridge Scheduler 每天凌晨觸發 Step Functions state machine，各步驟以 ECS RunTask（`.sync` 整合）在 Fargate 上執行 container，並在 state machine 中為每一步設定 Retry 與 Catch
- B. 以 EventBridge Scheduler 每天觸發一個 Lambda 函式，由它依序呼叫 6 個步驟的程式邏輯，失敗時寫入 CloudWatch Logs 並發出 SNS 通知
- C. 保留 cron 但改由 Auto Scaling group 每天凌晨啟動 instance、執行完自動終止，並把日誌送到 CloudWatch Logs
- D. 建立 Amazon MWAA 環境，把 6 個步驟寫成 Airflow DAG，以 KubernetesPodOperator 執行 container

> [!answer]- 答案：A
> **A ✓** **Step Functions** 提供每一步的狀態、輸入輸出與失敗位置的視覺化紀錄，Retry／Catch 處理自動重試與錯誤分支，也能從失敗步驟以 redrive 重新執行；ECS RunTask 的 `.sync` 整合會等待 Fargate task 完成再進入下一步，不需常駐伺服器，也沒有 15 分鐘的限制。
>
> **B ✗** Lambda 最長只能執行 15 分鐘，40 分鐘的轉檔步驟無法完成；單一函式串起所有步驟也看不到每一步的狀態，失敗時要從頭重跑。
>
> **C ✗** 排程啟動 instance 可以省下白天費用，但仍要維運 AMI 與作業系統，失敗時同樣要人工登入排查，沒有步驟層級的重試與續跑。
>
> **D ✗** MWAA 功能完整，但環境本身持續計費，KubernetesPodOperator 還需要 Kubernetes 叢集；只有 6 個步驟的每日批次，用 Airflow 維運負擔過高。若公司已有大量 Airflow DAG 要遷移，MWAA 才是合理選擇。
>
> **考點**：SAP-4.4｜cron 批次改為 Step Functions 加 Fargate｜延伸閱讀：第 33 章、第 21 章

### 第 25 題｜SAP｜單選｜D1 分析廠商存取客戶資料

一家電信公司委託外部的數據分析廠商分析用戶流失，廠商要從電信公司帳號中的一個 S3 bucket 讀取去識別化的通話統計資料。這家廠商同時服務數十家客戶，在自己的 AWS 帳號中以同一套分析平台、同一個 IAM role 去存取所有客戶的資料，客戶在廠商的入口網站填入自己的 role ARN 即可完成設定。電信公司的資安部擔心：若其他客戶在入口網站填入電信公司的 role ARN，廠商平台會不會被誘導去讀取電信公司的資料。

哪個做法最能防範這個風險？

- A. 在電信公司帳號建立 IAM user 並產生 access key，交給廠商存放在其平台中，每 90 天輪替一次
- B. 在 bucket policy 中直接授權廠商帳號的 root principal 讀取資料，不另外建立 role
- C. 每天以 Lambda 為需要的物件產生有效期 24 小時的 presigned URL，寄給廠商下載
- D. 在電信公司帳號建立給廠商 assume 的 IAM role，trust policy 只信任廠商的帳號，並要求 `sts:ExternalId` 條件等於廠商為電信公司產生的唯一 external ID

> [!answer]- 答案：D
> **A ✗** 長期 access key 一旦外洩就會持續有效，也無法利用廠商的 IAM 控制，是跨帳號存取最不建議的做法。
>
> **B ✗** 授權給廠商帳號本身，等於讓廠商帳號中任何被授權的 principal 都能讀取；廠商的同一套平台為所有客戶服務，仍可能被其他客戶誘導存取電信公司的資料，沒有解決問題。
>
> **C ✗** Presigned URL 可行但需要每天產生與傳遞，維運繁瑣；URL 外流時任何人都能下載，也不適合大量物件的分析。
>
> **D ✓** 這是典型的 **confused deputy** 情境：廠商（代理人）被其他客戶誘導以自己的權限去存取別人的資源。**External ID** 由廠商為每個客戶產生並記錄，廠商 assume role 時必須帶入該客戶專屬的值；其他客戶即使填入電信公司的 role ARN，廠商也只會帶入該客戶的 external ID，trust policy 的條件不符，assume 就會失敗。
>
> **考點**：SAP-1.2｜external ID 防範 confused deputy｜延伸閱讀：第 13 章

### 第 26 題｜SAP｜單選｜D2 Lambda 的漸進式發布與自動回滾

一家醫療器材公司的處方核對服務以 API Gateway 加 Lambda 實作，每次發布新版本都直接更新 `$LATEST`，上個月一個錯誤版本讓 30% 的請求失敗了 25 分鐘。品質部門要求新的部署流程：新版本先接收 10% 流量觀察 10 分鐘，若期間錯誤率或延遲的 CloudWatch alarm 觸發就自動退回舊版；正式接流量前，還要先以一組合成交易驗證新版本能正確呼叫下游的藥品資料庫。團隊已經用 AWS SAM 管理這個服務。

哪個方案最符合需求？

- A. 在 API Gateway 啟用 stage 的 canary release，把 10% 流量導到新的 deployment，10 分鐘後若沒有問題由工程師手動 promote
- B. 為函式發布版本並使用 alias，在 SAM 範本設定 `DeploymentPreference` 為 `Canary10Percent10Minutes`，指定 CloudWatch alarms，並設定 `PreTraffic` hook 函式執行合成交易驗證
- C. 每次發布時建立新函式，以 Route 53 weighted record 把 10% 流量導到新函式的 API endpoint，觀察後調整權重
- D. 發布新版本後把 alias 的 routing config 手動設定為新版本 10% 權重，並建立 CloudWatch dashboard 讓值班人員觀察

> [!answer]- 答案：B
> **A ✗** API Gateway canary release 可以分流，但需要手動 promote 或回滾，沒有依 alarm 自動回滾，也沒有「接流量前先驗證」的 hook。
>
> **B ✓** SAM 的 `DeploymentPreference` 會建立 **CodeDeploy** 部署，以 alias 的加權路由逐步把流量從舊版本移到新版本；`Canary10Percent10Minutes` 先移 10%、10 分鐘後移完其餘流量。指定的 alarm 觸發時 CodeDeploy 自動把 alias 指回舊版本；`PreTraffic` hook 在流量移轉前執行驗證函式，失敗就中止部署。
>
> **C ✗** 以 DNS 權重分流受 TTL 與 client 快取影響，比例不精確，回滾也慢；每次建立新函式還會讓設定與權限管理變得混亂。
>
> **D ✗** Alias 的加權路由是正確的底層機制，但全部手動操作，沒有自動回滾與部署前驗證，等於少了 CodeDeploy 提供的安全網。
>
> **考點**：SAP-2.1｜CodeDeploy 對 Lambda alias 的 canary 與 hooks｜延伸閱讀：第 37 章、第 19 章

### 第 27 題｜SAP｜單選｜D3 全球使用者的即時語音媒體流

Voxbridge 是一家跨國視訊會議 SaaS，媒體伺服器部署在 us-east-1、eu-west-1 與 ap-southeast-1 的 EC2 上，音訊與視訊使用自訂的 UDP 協定傳輸。亞太與南美的使用者經常抱怨聲音斷續，調查發現封包在公共 Internet 的長距離路由上遺失與抖動嚴重。公司希望改善這些使用者的連線品質，並在任一 Region 的媒體伺服器故障時，讓新的連線在 1 分鐘內自動導向其他健康的 Region，而且不希望依賴客戶端的 DNS 快取行為。

哪個方案最合適？

- A. 在三個 Region 的媒體伺服器前面建立 CloudFront distribution，利用 edge location 縮短使用者到 AWS 的距離
- B. 為三個 Region 建立 Route 53 latency-based records，搭配健康檢查，並把 TTL 設為 10 秒
- C. 建立 AWS Global Accelerator，以三個 Region 的 Network Load Balancer 作為 endpoint group，讓使用者連到 anycast 靜態 IP，從最近的 edge location 進入 AWS 骨幹網路
- D. 在每個 Region 部署 Site-to-Site VPN，讓主要企業客戶從自己的網路以 VPN 連到最近的 Region

> [!answer]- 答案：C
> **A ✗** CloudFront 處理 HTTP／HTTPS（包含 WebSocket）流量，不支援任意 UDP 協定，無法承接媒體流。若是影片點播或 HTTP 型 API，CloudFront 才是首選。
>
> **B ✗** Latency routing 只決定使用者連到哪個 Region，封包仍走公共 Internet，遺失與抖動的問題沒有改善；容錯切換也依賴 DNS，client 與 resolver 不一定遵守短 TTL。
>
> **C ✓** **Global Accelerator** 支援 TCP 與 UDP，提供兩個 anycast 靜態 IP，使用者從最近的 edge location 進入 AWS 骨幹網路，減少公共 Internet 上的遺失與抖動；它持續檢查 endpoint 健康，不健康時在數十秒內把新連線導向其他健康的 endpoint group，而且不依賴 DNS。
>
> **D ✗** VPN 只能服務少數企業客戶，一般使用者無法使用，也沒有跨 Region 的自動容錯。
>
> **考點**：SAP-3.3｜Global Accelerator 改善 UDP 長距離品質並快速容錯｜延伸閱讀：第 11 章

### 第 28 題｜SAP｜單選｜D1 管理帳號上的資安工具

一個政府數位發展部門的 AWS Organization 有 90 個帳號。過去為了方便，GuardDuty、Security Hub、AWS Config aggregator 與一個漏洞掃描用的 EC2 都直接放在 management account，資安團隊有 12 位成員都擁有 management account 的管理權限。新的內控規範要求：management account 的存取人數降到最低，資安團隊日常工作不得在 management account 進行，但仍要能集中檢視與管理所有帳號的安全發現。

哪個做法最符合規範？

- A. 建立專屬的 security tooling 帳號，把它註冊為 GuardDuty、Security Hub 等服務的 delegated administrator，並把 Config aggregator 與掃描工具移到該帳號；資安團隊改在該帳號工作，management account 只保留少數人的緊急存取
- B. 保留所有工具在 management account，但為資安團隊建立權限只限於安全服務的 IAM role，並以 SCP 限制他們不得操作 Organizations API
- C. 在每個成員帳號各自啟用 GuardDuty 與 Security Hub，讓各帳號負責人管理自己的發現，資安團隊每月彙整一次報告
- D. 建立第二個 Organization 專門放資安工具，並以跨 Organization 的 IAM role 讀取原 Organization 中各帳號的安全發現

> [!answer]- 答案：A
> **A ✓** **Delegated administrator** 讓組織中的指定成員帳號代表整個 Organization 管理特定服務，例如啟用成員帳號、檢視所有發現。把資安工作移到專屬帳號後，management account 只需處理帳務與組織結構，存取人數可以降到最少，符合多帳號最佳實務。
>
> **B ✗** SCP 對 management account 完全不生效，用 SCP 限制 management account 內的 role 根本無效；工作仍在 management account 進行，也違反規範。
>
> **C ✗** 分散管理會失去集中可視性，延遲一個月才彙整也無法及時處置威脅。
>
> **D ✗** 第二個 Organization 無法成為原組織服務的 delegated administrator，跨組織讀取要自建大量 role 與整合，管理更複雜。
>
> **考點**：SAP-1.4｜以 delegated administrator 讓 management account 最小化｜延伸閱讀：第 14 章、第 40 章

### 第 29 題｜SAP｜單選｜D2 資料庫密碼的零停機輪替

一家天然氣配送公司的調度系統由 30 個 ECS 服務組成，都以同一組寫在環境變數中的 MySQL 帳號密碼連線到 RDS for MySQL，另外還有一套只支援帳號密碼登入的第三方報表工具也使用這組帳密。新的資安政策要求應用程式帳號的密碼每 30 天自動輪替，且輪替過程中不得出現任何連線失敗；同時禁止密碼以明文出現在任務定義或程式碼中。調度系統尖峰時每秒會建立上千個新連線。

哪個方案最符合需求？

- A. 把帳密存入 Secrets Manager，設定 30 天的自動輪替並採用 alternating users 策略，讓兩組資料庫使用者交替更新；ECS 任務定義以 `secrets` 欄位引用 secret，應用程式與報表工具在連線失敗時重新取得最新值（ECS 服務重新啟動 task、報表工具由管理員更新設定）
- B. 把帳密存入 Systems Manager Parameter Store 的 SecureString，以 Parameter Store 內建的自動輪替功能每 30 天更新密碼
- C. 把帳密存入 Secrets Manager，使用 single user 輪替策略，在每次輪替後重新部署所有 ECS 服務以讀取新密碼
- D. 改用 RDS 的 IAM database authentication，讓所有 ECS 服務與報表工具以 IAM 產生的 authentication token 連線，不再使用密碼

> [!answer]- 答案：A
> **A ✓** **Secrets Manager** 提供受管的自動輪替。**Alternating users** 策略維護兩個資料庫使用者，每次輪替更新「目前沒在用的那一個」再切換，舊的帳密在下一次輪替前（30 天內）仍然有效，因此仍持有舊值的 task 與報表工具不會立刻連線失敗，有一整個輪替週期可以換成新值。ECS 以 `secrets` 欄位在 task 啟動時注入值，密碼不會以明文出現在任務定義中；因為值只在啟動時注入，長時間執行的 task 要在下一次輪替前重新啟動（例如定期重新部署），或改由程式以 SDK 讀取 secret。
>
> **B ✗** Parameter Store 沒有內建的密碼輪替功能，要自己用 Lambda 與排程實作，還要處理資料庫密碼的變更與同步。
>
> **C ✗** Single user 策略直接修改同一個使用者的密碼，從變更到應用程式讀取新值之間，持有舊密碼的連線會失敗；每次輪替還要重新部署 30 個服務，違反零連線失敗的要求。
>
> **D ✗** IAM database authentication 可以免去密碼，但報表工具只支援帳號密碼；而且 IAM 驗證每秒新連線數有建議上限，尖峰每秒上千個新連線可能造成驗證瓶頸。
>
> **考點**：SAP-2.3｜Secrets Manager alternating users 輪替｜延伸閱讀：第 15 章

### 第 30 題｜SAP｜單選｜D3 選舉期間凍結變更

中央選舉委員會的開票系統部署在 AWS，維運團隊以 Systems Manager Automation runbook 執行修補、擴容與設定變更，也有部分 Automation 由 EventBridge 規則自動觸發。依內控規範，投票日前 3 天到開票結束後 1 天，除非經由緊急變更流程核准，否則不得執行任何計畫性變更；稽核也要求能證明這段期間內的自動化確實被阻擋。所有 Automation 都從團隊維護的 6 個共用 runbook 啟動，團隊可以在這些 runbook 中加入步驟，但不希望為了凍結而調整 IAM 權限。

哪個方案最符合需求？

- A. 在凍結期間以 SCP 搭配 `aws:CurrentTime` 條件拒絕所有 `ssm:StartAutomationExecution`，期間結束後再移除 SCP
- B. 建立 Systems Manager maintenance window，把所有 Automation 排到凍結期間以外的時段執行
- C. 以 AWS Config rule 偵測凍結期間發生的資源變更，觸發 SNS 通知值班人員回復變更
- D. 在 Systems Manager Change Calendar 建立 `DEFAULT_OPEN` 類型的行事曆，把凍結期間設為 closed event；在共用 runbook 的第一步以 `aws:assertAwsResourceProperty` 呼叫 `GetCalendarState`，行事曆不是 OPEN 就停止執行；緊急變更改用含 `aws:approve` 核准步驟的緊急 runbook，核准後才執行

> [!answer]- 答案：D
> **A ✗** SCP 可以依時間拒絕，但會一併阻擋緊急變更，除非再做例外處理；把 SCP 當成排程工具也違反「不影響 IAM 權限的日常管理」，且容易忘記移除。
>
> **B ✗** Maintenance window 決定「什麼時候執行」，但無法阻擋在其他時段手動啟動或由 EventBridge 觸發的 Automation。
>
> **C ✗** Config rule 只能在變更發生後偵測，無法事先阻擋，也不符合「證明自動化被阻擋」的要求。
>
> **D ✓** **Change Calendar** 定義允許與禁止變更的時段。AWS 建議的做法是在 runbook 中加入 `aws:assertAwsResourceProperty` 步驟呼叫 `GetCalendarState`：行事曆是 OPEN 才繼續，否則執行在第一步就停止；不論是手動啟動還是 EventBridge 觸發，都會走到這個檢查，Automation 的執行紀錄也能向稽核證明凍結期間的執行被擋下。緊急變更則走另一個含 `aws:approve` 的 runbook，必須由指定的核准者同意才會繼續。全程不需修改 IAM 權限。舊題常以 Change Manager 處理變更核准，但它自 2025-11-07 起不再開放新客戶，新設計改用 `aws:approve` 或 pipeline 的人工核准階段。
>
> **考點**：SAP-3.1｜Change Calendar 搭配 runbook 檢查步驟的變更凍結｜延伸閱讀：第 38 章

### 第 31 題｜SAP｜單選｜D2 飛行模擬運算的共享檔案系統

一家航空器維修與工程公司要在 AWS 上執行氣動力模擬（CFD），每次作業同時啟動 600 台 EC2 運算節點，執行 6–10 小時。輸入的網格檔與歷史結果存放在 S3（約 400 TB），每次作業要讀取其中 30–50 TB，所有節點需要以 POSIX 檔案系統共享讀寫中間檔，總吞吐量要達到數百 GB/s、延遲低於 1 毫秒。作業結束後，結果要寫回 S3，檔案系統即可刪除。

哪個儲存方案最合適？

- A. 為每次作業建立 Amazon EFS 檔案系統，使用 Max I/O 與 Elastic throughput 模式，以 DataSync 從 S3 複製輸入資料
- B. 在每個運算節點以 Mountpoint for Amazon S3 直接掛載 bucket，讓所有節點直接讀寫 S3 上的檔案
- C. 為每次作業建立 Amazon FSx for Lustre（scratch 部署類型）檔案系統，建立與 S3 bucket 的 data repository association 延遲載入輸入資料，作業結束後把結果匯出回 S3 再刪除檔案系統
- D. 建立 Amazon FSx for NetApp ONTAP 檔案系統，以 FlexCache 從 S3 快取資料，所有節點透過 NFS 掛載

> [!answer]- 答案：C
> **A ✗** EFS 適合一般的共享檔案需求，但對數百 GB/s、次毫秒延遲的 HPC 工作負載不是最佳選擇；從 S3 預先複製數十 TB 也會耗時與增加成本。
>
> **B ✗** Mountpoint for Amazon S3 適合大量循序讀取，但不支援完整的 POSIX 語意（例如修改既有檔案、檔案鎖定），無法作為節點間共享讀寫中間檔的檔案系統。
>
> **C ✓** **FSx for Lustre** 是為 HPC 設計的平行檔案系統，吞吐量可隨容量擴展到數百 GB/s，延遲次毫秒。**Data repository association** 把 S3 bucket 連結為資料來源：檔案在第一次存取時才從 S3 載入，結果可以匯出回 S3。Scratch 類型不做資料複寫、成本較低，適合可以重跑、用完即刪的短期作業。
>
> **D ✗** FSx for NetApp ONTAP 適合企業 NAS 遷移與多協定存取，FlexCache 是快取其他 ONTAP volume 的功能，不是用來快取 S3；吞吐量也不是為這種規模的 HPC 設計。
>
> **考點**：SAP-2.5｜FSx for Lustre 與 S3 data repository｜延伸閱讀：第 24 章



### 第 32 題｜SAP｜單選｜D4 Oracle 遷移到 Aurora PostgreSQL

一家連鎖檢驗所的檢驗報告系統使用地端 Oracle Database（12 TB，含大量 PL/SQL stored procedure），Oracle 授權將在 5 個月後到期，管理層決定改用 Aurora PostgreSQL 以擺脫授權費用。地端與 AWS 之間已有 10 Gbps 的 Direct Connect。檢驗報告系統每天 24 小時運作，切換時的停機時間不得超過 30 分鐘；開發團隊需要知道哪些 PL/SQL 無法自動轉換，以便估算改寫工時。

哪個方案最合適？

- A. 以 Oracle Data Pump 匯出整個資料庫，透過 DX 上傳到 S3，再用 `aws_s3` extension 匯入 Aurora PostgreSQL，週末停機一次完成切換
- B. 以 AWS DMS Schema Conversion 評估並轉換 schema 與程式碼，依評估報告由開發團隊改寫無法自動轉換的 PL/SQL；再以 DMS 執行 full load 加上持續 CDC，在資料同步追上後於短暫的維護時段切換應用程式
- C. 以 AWS Application Migration Service 把 Oracle 伺服器 rehost 到 EC2，切換完成後再於 EC2 上把資料庫引擎改為 PostgreSQL
- D. 啟用 Aurora PostgreSQL 的 Babelfish 功能，讓應用程式不需修改 PL/SQL 就能直接連線 Aurora，再以 DMS 一次性載入資料

> [!answer]- 答案：B
> **A ✗** Data Pump 的匯出檔是 Oracle 專用格式，PostgreSQL 無法直接匯入；即使轉成 CSV，12 TB 一次性搬遷加匯入也很難在 30 分鐘內完成，而且沒有處理 schema 與 PL/SQL 的轉換。
>
> **B ✓** 異質遷移的標準兩步驟：先以 **DMS Schema Conversion**（或 AWS SCT）轉換 schema 與程式碼，評估報告會列出需要人工處理的項目，正好用來估算工時；再以 **DMS full load + CDC** 在正式系統持續運作時同步資料，切換時只需停止寫入、等待最後的變更套用完畢，停機可控制在分鐘級。
>
> **C ✗** MGN 只能把伺服器原樣搬到 EC2，不會轉換資料庫引擎；「在 EC2 上改引擎」仍要做完整的異質遷移，等於多繞一圈，Oracle 授權問題也沒解決。
>
> **D ✗** Babelfish 讓 Aurora PostgreSQL 理解 SQL Server 的 T-SQL 與 TDS 協定，不支援 Oracle 的 PL/SQL。若來源是 SQL Server，Babelfish 才是減少應用程式修改的選項。
>
> **考點**：SAP-4.2｜異質資料庫遷移：Schema Conversion 加 DMS CDC｜延伸閱讀：第 45 章

### 第 33 題｜SAP｜單選｜D1 阻擋惡意網域的 DNS 查詢

一個政府資訊中心管理 150 個 AWS 帳號、每個帳號有 2–5 個 VPC。資安情資顯示，部分被入侵的 EC2 透過 DNS 查詢與命令控制伺服器通訊，甚至利用 DNS 查詢夾帶資料外洩。資訊中心已經部署以 AWS Network Firewall 為核心的集中 egress inspection VPC，但事後分析發現這些 DNS 查詢完全沒有經過防火牆。資安長要求在所有帳號、所有 VPC 一致地阻擋已知惡意網域與資訊中心自訂黑名單網域的查詢，新 VPC 建立時也要自動套用。

哪個方案最合適？

- A. 建立 Route 53 Resolver DNS Firewall rule group，包含 AWS managed domain list 與自訂網域清單，透過 AWS Firewall Manager 的 DNS Firewall policy 在整個 Organization 的 VPC 自動關聯
- B. 在 Network Firewall 增加 domain list 規則，攔截所有包含惡意網域的 DNS 封包，並把每個 VPC 的 DNS 查詢路由導向 inspection VPC
- C. 在組織層級啟用 GuardDuty，開啟 DNS logs 分析，偵測到可疑網域查詢時自動以 Lambda 隔離 instance
- D. 在每個 VPC 的 NACL 中拒絕對外的 UDP 與 TCP 53 連線，強迫所有 instance 只能使用 VPC 內建的 Resolver

> [!answer]- 答案：A
> **A ✓** EC2 預設把 DNS 查詢送到 VPC 內建的 Route 53 Resolver（VPC CIDR +2 位址），這段流量不會經過 route table 指向的防火牆，所以 Network Firewall 看不到。**Route 53 Resolver DNS Firewall** 直接在 Resolver 上依網域清單阻擋或警示查詢；**Firewall Manager** 能把 rule group 自動關聯到組織內所有現有與新建的 VPC。
>
> **B ✗** 這正是題目描述的盲點：送往內建 Resolver 的 DNS 查詢不經過 VPC route table，無法「路由」到 inspection VPC，Network Firewall 根本收不到。Network Firewall 的 domain list 適合過濾 HTTP Host 與 TLS SNI。
>
> **C ✗** GuardDuty 能偵測可疑的 DNS 查詢，但它是偵測服務、不會阻擋查詢；自動隔離是事後處置，資料可能已經外洩。
>
> **D ✗** NACL 不會過濾送往 VPC 內建 Resolver 的流量，而題目中的惡意查詢本來就是透過內建 Resolver 解析的，阻擋對外 53 port 沒有效果。
>
> **考點**：SAP-1.1、SAP-1.2｜DNS Firewall 與 Firewall Manager 的組織級部署｜延伸閱讀：第 6 章、第 41 章

### 第 34 題｜SAP｜選兩項｜D3 一筆壞訊息卡住整批處理

一家電信公司的簡訊發送平台以 SQS standard queue 搭配 Lambda 處理發送請求，event source mapping 的 batch size 為 10。最近發現：只要一批中有一筆格式錯誤的訊息，函式就丟出例外，整批 10 筆都回到 queue 重新處理，其中 9 筆正常訊息被重複發送給用戶，那筆錯誤訊息則無限重試，持續消耗並行數。團隊希望正常訊息只成功處理一次，錯誤訊息在重試數次後被隔離以便人工檢查，同時維持目前的處理吞吐量。

哪兩個做法組合最合適？（選兩項）

- A. 把 queue 的 visibility timeout 從 30 秒調高到 12 小時，讓失敗的訊息不會太快被重新處理
- B. 在 event source mapping 啟用 `ReportBatchItemFailures`，函式只回報處理失敗的訊息 ID，讓成功的訊息從 queue 刪除
- C. 為 source queue 設定 redrive policy，指定 dead-letter queue 並把 `maxReceiveCount` 設為 5，讓重複失敗的訊息被移到 DLQ
- D. 把 batch size 改為 1，讓每次呼叫只處理一筆訊息，避免一筆失敗影響其他訊息
- E. 為 Lambda 函式設定非同步呼叫的 on-failure destination，把失敗的事件送到 SNS topic 通知維運人員

> [!answer]- 答案：B、C
> **A ✗** 延長 visibility timeout 只會讓錯誤訊息更晚重試，最後仍無限重試；而且如果函式中途崩潰，正常訊息也要等 12 小時才會被重新處理。
>
> **B ✓** 預設情況下，函式丟出例外代表整批失敗，所有訊息都回到 queue。**Partial batch response**（`ReportBatchItemFailures`）讓函式回傳失敗訊息的 ID，Lambda 只把這些訊息留在 queue，其餘成功的訊息會被刪除，解決正常訊息被重複發送的問題。
>
> **C ✓** SQS 的 **redrive policy** 在訊息被接收超過 `maxReceiveCount` 次後，把它移到 dead-letter queue，停止無限重試並保留訊息供人工檢查；修正後可以用 redrive 把訊息送回 source queue。
>
> **D ✗** Batch size 1 確實能隔離失敗，但呼叫次數變成 10 倍，吞吐量與成本都變差，違反維持吞吐量的要求；錯誤訊息仍會無限重試。
>
> **E ✗** SQS event source mapping 是由 Lambda 輪詢後以同步方式呼叫函式，非同步呼叫的 on-failure destination 不適用；SQS 情境要在 queue 上設定 DLQ。
>
> **考點**：SAP-3.4｜SQS 加 Lambda 的 partial batch response 與 DLQ｜延伸閱讀：第 32 章、第 19 章

### 第 35 題｜SAP｜單選｜D2 健康檢查讓整個機群同時下線

一家電力公司的用戶服務入口網站在 ALB 後面有 12 台 EC2，由一個跨三個 AZ 的 Auto Scaling group 管理，並使用 ELB 健康檢查判斷 instance 是否健康。為了「及早發現問題」，團隊把 ALB 健康檢查路徑設為 `/health/deep`：它會依序檢查 Aurora 連線、Redis 連線與一個第三方繳費 API，任何一項逾時就回傳 503。上週第三方繳費 API 回應變慢約 5 分鐘，結果 12 台 instance 全部被標記為不健康，Auto Scaling 開始陸續終止並替換它們，新的 instance 一樣檢查失敗，網站在 20 分鐘內幾乎沒有可用容量，連不需要繳費功能的查詢電費頁面也無法使用。團隊希望避免同類事件再次發生。

哪個做法最合適？

- A. 把 `/health/deep` 的逾時時間從 2 秒延長到 10 秒，並把 unhealthy threshold 調高到 10，降低誤判
- B. 把 Auto Scaling group 的 health check grace period 從 300 秒延長到 1,800 秒，讓新啟動的 instance 有更多時間通過健康檢查
- C. 為第三方繳費 API 建立 Route 53 health check，失敗時把整個網站切換到維護頁面
- D. 把 ALB 健康檢查改為只確認 instance 本身能處理請求的淺層檢查；外部依賴的狀態改以獨立的監控與 alarm 追蹤，並在應用程式中以逾時與 circuit breaker 讓繳費功能單獨降級

> [!answer]- 答案：D
> **A ✗** 延長逾時與門檻只是延後所有 instance 一起下線的時間；外部依賴故障超過幾分鐘，結果仍然一樣。問題在於健康檢查把「共用依賴的狀態」當成「instance 的狀態」。
>
> **B ✗** Grace period 只在 instance 剛啟動的一段時間內忽略健康檢查結果，既有的 instance 仍會因外部 API 變慢而被判定不健康並替換；新 instance 過了寬限期一樣失敗。它適合處理「應用程式啟動很慢」的問題。
>
> **C ✗** 繳費 API 故障就把整個網站切到維護頁，等於讓一個非核心依賴決定整個服務的可用性，與需求相反。
>
> **D ✓** ALB 健康檢查應該回答「這台 instance 能不能處理請求」。檢查共用依賴時，依賴一出問題，所有 instance 會同時被判定不健康並被 Auto Scaling 替換，一個非核心依賴就拖垮整個機群。淺層檢查讓 instance 保持在服務中，依賴問題交給監控與 **circuit breaker**，讓繳費功能單獨降級，查詢電費等其他功能照常運作。
>
> **考點**：SAP-2.4｜淺層健康檢查與依賴故障的優雅降級｜延伸閱讀：第 10 章、第 35 章

### 第 36 題｜SAP｜單選｜D1 跨部會的成本分攤

一個地方政府的數位服務中心以一個 Organization 管理 60 個帳號，提供給社會局、交通局、衛生局等 12 個局處使用。部分帳號由單一局處專用，另有 8 個共用帳號（共用的資料平台、身份驗證服務、網路帳號）由多個局處一起使用，共用帳號中的資源都已標上 `agency` 標籤，網路帳號的費用則要依各局處的流量比例分攤。主計單位要求每月產出各局處的費用報表，包含分攤後的共用費用，並能在 Cost Explorer 中直接依局處篩選。

哪個方案最符合需求，且維運負擔最低？

- A. 為每個局處建立獨立的 Organization，把專用帳號移入對應的 Organization，共用帳號的費用每月由人工計算後以內部公文分攤
- B. 在 management account 啟用 `agency` 為 cost allocation tag，建立名為「局處」的 AWS Cost Category，以帳號與 `agency` 標籤為規則把費用對應到各局處，並以 split charge rule 依比例分攤網路帳號的費用
- C. 以 tag policy 強制所有資源都必須有 `agency` 標籤，主計單位每月在 Cost Explorer 中依標籤群組檢視即可
- D. 為每個局處建立 AWS Budgets，預算範圍以帳號與標籤篩選，每月把各 budget 的實際支出匯出成報表

> [!answer]- 答案：B
> **A ✗** 拆成多個 Organization 會失去集中治理與合併帳單的折扣共享，共用帳號的費用也仍要人工分攤。
>
> **B ✓** **Cost allocation tag** 必須在 management account 啟用後才會出現在帳單資料中。**Cost Categories** 能以帳號、標籤等規則把費用歸類為自訂維度（例如「局處」），在 Cost Explorer、Budgets 與 CUR 中都能使用；**split charge rule** 可以把共用類別的費用依比例、平均或固定比例分攤到其他類別，正好處理網路帳號的分攤。
>
> **C ✗** Tag policy 只規範標籤的格式與允許值，無法處理「整個帳號歸屬某個局處」或依比例分攤共用費用，也不會讓標籤自動成為 cost allocation tag。
>
> **D ✗** Budgets 用來追蹤與警示，不是成本歸屬與分攤工具；要把共用費用依比例分攤仍得人工計算。
>
> **考點**：SAP-1.5｜Cost Categories 與 split charge 處理 chargeback｜延伸閱讀：第 39 章、第 43 章

### 第 37 題｜SAP｜選兩項｜D4 自管訊息中介的現代化

一家行動通訊業者的開通（provisioning）系統由 25 個 Java 應用組成，彼此透過地端自建的 Apache ActiveMQ 叢集以 JMS 交換訊息，使用 queue 與 topic。叢集每季都因磁碟或版本升級問題中斷，維運團隊希望移到 AWS 受管服務，但 25 個應用都由不同外包商維護，短期內不可能改寫訊息處理程式碼。另外，公司正在開發新的事件驅動功能（例如把開通完成事件分送給計費、客服與行銷等多個新服務），希望新功能採用能依事件內容篩選路由、免維運的服務。

哪兩個做法最合適？（選兩項）

- A. 把既有叢集遷移到 Amazon MQ for ActiveMQ，使用 active/standby 部署跨兩個 AZ，應用程式只需修改連線端點即可繼續使用 JMS
- B. 把既有的 25 個應用改為使用 Amazon SQS 與 SNS，以 SQS 取代 queue、SNS 取代 topic
- C. 把既有叢集遷移到 Amazon MSK，讓應用程式透過 Kafka 協定交換訊息
- D. 在 EC2 上部署 ActiveMQ，並以 Auto Scaling group 與 EFS 存放訊息資料，提升叢集的可用性
- E. 新的事件驅動功能使用 Amazon EventBridge，由開通系統發布事件到 custom event bus，以規則依事件內容把事件路由到計費、客服與行銷服務

> [!answer]- 答案：A、E
> **A ✓** **Amazon MQ** 是受管的 ActiveMQ 與 RabbitMQ 服務，支援 JMS、AMQP、STOMP、MQTT 等標準協定，現有應用只需更換連線端點，不必改寫訊息程式碼。Active/standby 部署跨 AZ 提供高可用，AWS 負責修補與維護。
>
> **B ✗** SQS／SNS 是 AWS 原生 API，不支援 JMS 協定，25 個應用都要改寫，違反「短期內不能改程式碼」的限制。若應用程式可以改寫，SQS／SNS 的擴展性與成本會比 Amazon MQ 更好。
>
> **C ✗** Kafka 協定與 JMS 不相容，同樣需要改寫應用程式；MSK 適合高吞吐的 streaming 與事件重播情境。
>
> **D ✗** 自建在 EC2 上仍要自己處理版本升級與故障，沒有解決維運負擔，只是把機房換成雲端。
>
> **E ✓** **EventBridge** 是免維運的事件匯流排，規則可以依事件內容（例如方案類型、地區）篩選並路由到多個目標，新增消費者只需增加規則，適合新開發的事件驅動功能。
>
> **考點**：SAP-4.3、SAP-4.4｜既有 JMS 用 Amazon MQ、新功能用 EventBridge｜延伸閱讀：第 32 章

### 第 38 題｜SAP｜單選｜D2 每月批次分析的運算成本

一個國家統計機關每月初執行一次人口與經濟資料的 Spark 批次分析，目前在 Amazon EMR 上長期維持一個 40 台 On-Demand instance 的叢集，但每月實際只有 3 天在跑作業。作業可以中斷後重跑個別 stage，但若存放 HDFS 中間資料的節點被中斷，整個作業就要從頭開始；輸入與輸出資料都存放在 S3。統計機關希望在不延長作業完成時間的前提下大幅降低成本。

哪個方案最合適？

- A. 保留常駐叢集，改為購買一年期 EC2 Instance Savings Plans 涵蓋 40 台 instance
- B. 改為每月建立 transient 叢集，所有節點（包含 primary、core 與 task）都使用 Spot Instances，以降低最多成本
- C. 改為每月作業開始時建立 transient 叢集、作業完成後自動終止；primary 與 core 節點使用 On-Demand，task 節點使用 instance fleet 搭配多種 instance type 的 Spot Instances
- D. 改用 AWS Glue 的 Spark job，並把 worker 數量固定為 40，以免重新撰寫程式

> [!answer]- 答案：C
> **A ✗** 每月只用 3 天，為常駐叢集購買承諾折扣仍是在為閒置時間付費；Savings Plans 也不能讓用不到的容量變便宜。
>
> **B ✗** 全部使用 Spot 最便宜，但 primary 節點被中斷會讓叢集失效，core 節點存放 HDFS 資料，被中斷就要從頭重跑，違反「不延長完成時間」的要求。若作業完全不依賴 HDFS、且能接受重跑，才值得冒這個風險。
>
> **C ✓** **Transient 叢集**只在需要時存在，消除閒置成本。Primary 與 core 節點使用 On-Demand 確保叢集與 HDFS 穩定；只負責運算、不存資料的 task 節點使用 Spot，中斷只影響個別 stage 重跑。**Instance fleet** 能同時指定多種 instance type 與購買選項，提高取得 Spot 容量的機會。
>
> **D ✗** Glue 是 serverless 的 Spark 環境，可行但要調整程式與作業設定；而且固定 40 個 worker 不一定比 EMR 加 Spot 便宜，Glue 也沒有 Spot 定價（Flex 執行類別較便宜，但啟動時間不保證）。若團隊想完全免維運且作業規模較小，Glue 或 EMR Serverless 才更有吸引力。
>
> **考點**：SAP-2.6｜EMR transient cluster 與 Spot task 節點｜延伸閱讀：第 30 章、第 17 章

### 第 39 題｜SAP｜單選｜D3 NAT Gateway 費用暴增

一家電信公司的資料平台帳號每月 NAT Gateway 費用超過 6 萬美元。分析 VPC Flow Logs 後發現，約 85% 經過 NAT Gateway 的流量是 private subnet 中的 EMR 與 EKS 節點存取同 Region 的 S3 與 DynamoDB，另外約 10% 是 EKS 節點從 Amazon ECR 拉取 container image。資安規範要求這些節點不得有 public IP，也不得移到 public subnet；公司希望以最少的變更大幅降低這筆費用。

哪個方案最合適？

- A. 把 NAT Gateway 換成在每個 AZ 自行維運的 NAT instance，以較便宜的 instance type 承接流量
- B. 把三個 AZ 的 NAT Gateway 合併成一台，讓所有 private subnet 都指向它，減少 NAT Gateway 的小時費用
- C. 把 EMR 與 EKS 節點移到 public subnet 並配置 public IP，讓流量直接經 Internet Gateway 存取 S3 與 DynamoDB
- D. 建立 S3 與 DynamoDB 的 gateway VPC endpoint 並加入 private subnet 的 route table，再建立 ECR 的 `ecr.api` 與 `ecr.dkr` interface endpoint；image layer 存放在 S3，會經由 S3 gateway endpoint 取得

> [!answer]- 答案：D
> **A ✗** NAT instance 能省部分資料處理費，但要自己處理高可用、修補與頻寬上限，維運負擔增加，也沒有消除不必要的 NAT 流量。
>
> **B ✗** NAT Gateway 的主要費用是每 GB 的資料處理費，合併成一台不會降低流量費，反而增加跨 AZ 傳輸費並產生單點故障。
>
> **C ✗** 違反「不得有 public IP、不得移到 public subnet」的資安規範。
>
> **D ✓** S3 與 DynamoDB 的 **gateway endpoint** 不收費，流量直接從 route table 導到服務，不經 NAT Gateway，消除 85% 的資料處理費。ECR 拉 image 需要 `ecr.api` 與 `ecr.dkr` 兩個 interface endpoint（interface endpoint 按小時與流量計費，但比 NAT 便宜），而 image layer 實際從 S3 下載，所以 S3 gateway endpoint 同時服務這部分流量。
>
> **考點**：SAP-3.5｜以 VPC endpoint 消除 NAT 資料處理費｜延伸閱讀：第 6 章、第 39 章

### 第 40 題｜SAP｜選兩項｜D1 雙 Region active-active 的病患入口

一家跨國醫療集團的病患入口網站要同時服務北美與歐洲的病患，在 us-east-1 與 eu-central-1 各部署一套 ECS 服務。需求是：兩個 Region 都要能處理讀寫（預約、留言給醫師），使用者連到延遲最低的 Region；任一 Region 故障時，另一個 Region 能繼續處理全部讀寫，不需要人工執行資料庫升級。資料模型以「病患 ID」為鍵，同一位病患同時在兩個 Region 寫入的機會極低，業務單位可以接受秒級的跨 Region 複寫延遲與「最後寫入者勝出」的衝突處理。

哪兩個做法最合適？（選兩項）

- A. 使用 Aurora Global Database，在 secondary Region 啟用 write forwarding，讓兩個 Region 都能接受寫入
- B. 使用 ElastiCache Global Datastore 作為主要資料庫，在兩個 Region 都能寫入
- C. 使用 DynamoDB global tables，在兩個 Region 都建立 replica，應用程式寫入所在 Region 的 replica
- D. 每個 Region 各自使用一個 Aurora cluster，以 DMS 進行雙向複寫
- E. 使用 Route 53 latency-based routing 為兩個 Region 的 ALB 建立記錄，並為每筆記錄關聯 health check，讓故障 Region 的記錄自動被排除

> [!answer]- 答案：C、E
> **A ✗** Write forwarding 只是把 secondary Region 收到的寫入轉送到 primary cluster 執行，所有寫入仍依賴 primary Region；primary 故障時仍要執行 failover 才能恢復寫入，不符合「不需要人工升級」。
>
> **B ✗** Global Datastore 只有一個 primary cluster 可以寫入，其他 Region 是唯讀的 secondary；它也不適合作為病患資料的持久化主要資料庫。
>
> **C ✓** **DynamoDB global tables** 是多 Region、多主（multi-active）的資料表，每個 replica 都能讀寫，變更通常在一秒左右複寫到其他 Region，衝突以最後寫入者勝出處理，完全符合題目接受的條件；任一 Region 故障，另一個 Region 的 replica 繼續讀寫，不需升級。
>
> **D ✗** DMS 雙向複寫需要自己處理迴圈、衝突與延遲，維運複雜，並不是為 active-active 設計的受管機制。
>
> **E ✓** **Latency-based routing** 把使用者導到延遲最低的 Region；記錄關聯 health check 後，故障 Region 的記錄會被排除，流量自動導到另一個 Region。
>
> **考點**：SAP-1.3｜DynamoDB global tables 加 Route 53 latency routing 的 active-active｜延伸閱讀：第 27 章、第 42 章

### 第 41 題｜SAP｜單選｜D2 勒索軟體下的備份復原能力

一家航空貨運公司在一次資安演練中假設：攻擊者取得了正式環境帳號的管理員權限，可以刪除該帳號中的所有資源與備份。目前公司以 AWS Backup 在同一個帳號中備份 EC2、EBS 與 Aurora（所有 Aurora cluster 都已啟用加密），並做跨 Region 複製。資安長要求：即使正式帳號被完全接管，也必須保有無法被刪除或縮短保留期的備份副本，並能在另一個乾淨的帳號中快速還原，而不用先把備份複製回來。

哪個方案最符合需求？

- A. 在獨立的資料保護帳號建立 AWS Backup logically air-gapped vault，把備份副本複製進去；需要復原時，透過 AWS RAM 把該 vault 分享給乾淨的復原帳號，直接在復原帳號中還原
- B. 在正式帳號的 backup vault 啟用 AWS Backup Vault Lock 的 governance mode，防止備份被刪除
- C. 把備份的跨 Region 複製目的地改為同一帳號中的第三個 Region，讓攻擊者更難找到所有副本
- D. 以 S3 Cross-Region Replication 把 EBS snapshot 與 Aurora snapshot 複製到另一個帳號的 bucket，並在該 bucket 啟用 Object Lock

> [!answer]- 答案：A
> **A ✓** **Logically air-gapped vault** 是一種特殊的 backup vault：預設以 compliance mode 鎖定，保留期間內任何人（包括 root）都無法刪除或縮短保留期，並可透過 AWS RAM 分享給其他帳號直接還原，不必先把備份複製回來。放在獨立帳號中，正式帳號被接管也不會影響它。它支援 EC2、EBS 與 Aurora 等資源，但未加密的 Aurora cluster 無法存入，這也是題幹特別說明 cluster 已加密的原因。
>
> **B ✗** Governance mode 允許擁有特定權限的使用者移除鎖定，取得管理員權限的攻擊者可以解除後刪除；而且 vault 仍在被接管的帳號中。若要真正不可刪除，必須使用 compliance mode。
>
> **C ✗** 同一個帳號的管理員可以存取所有 Region，換 Region 只是隱藏而非保護。
>
> **D ✗** EBS 與 Aurora snapshot 由各服務管理，並不是你可以存取的 S3 物件，無法用 S3 replication 複製。
>
> **考點**：SAP-2.2｜logically air-gapped vault 與跨帳號復原｜延伸閱讀：第 34 章、第 43 章

### 第 42 題｜SAP｜單選｜D3 Lambda 環境變數中的明文憑證

一家能源公司的資安稽核發現，60 個 Lambda 函式把第三方氣象資料 API 的 API key 與一組資料庫密碼直接寫在環境變數中，凡是有 `lambda:GetFunctionConfiguration` 權限的工程師都能在主控台看到明文；這些值也從未輪替。部分函式每秒被呼叫數百次，延遲敏感。資安部要求：憑證不得以明文出現在函式設定中，資料庫密碼要能自動輪替，且不能因為讀取憑證而明顯增加延遲或 API 呼叫成本。

哪個方案最合適？

- A. 改用 customer managed KMS key 加密環境變數，並限制只有函式的 execution role 能使用該金鑰解密
- B. 把憑證存入 Secrets Manager 並為資料庫密碼設定自動輪替，函式加入 AWS Parameters and Secrets Lambda Extension，透過本地快取讀取 secret，並只授權各函式的 execution role 讀取自己需要的 secret
- C. 把憑證存入 Systems Manager Parameter Store 的 String 參數，函式每次呼叫時以 SDK 讀取最新值
- D. 把憑證存放在加密的 S3 物件中，函式在每次呼叫時從 S3 下載並解析

> [!answer]- 答案：B
> **A ✗** 改用 CMK 並限制解密者，可以讓沒有 KMS 權限的工程師看不到明文，但憑證仍然是函式設定的一部分，部署範本與 pipeline 中也常保留原值；更關鍵的是沒有自動輪替，密碼一改就要更新並重新部署 60 個函式。若只有「靜態加密」的要求且值不需輪替，這個做法才足夠。
>
> **B ✓** **Secrets Manager** 集中保存憑證並提供資料庫密碼的自動輪替；**Parameters and Secrets Lambda Extension** 在執行環境中快取 secret，函式透過 localhost 讀取，不必每次呼叫都打 Secrets Manager API，兼顧延遲與成本。以 IAM 讓每個函式只能讀取自己的 secret，符合最小權限。
>
> **C ✗** String 參數不加密，與環境變數一樣是明文；每次呼叫都讀取也增加延遲與 API 呼叫量，而且 Parameter Store 沒有內建輪替。
>
> **D ✗** 每次呼叫都下載 S3 物件會增加延遲與請求成本，也沒有輪替機制，是自己重造 secret 管理。
>
> **考點**：SAP-3.2｜Secrets Manager 與 Lambda extension 快取｜延伸閱讀：第 15 章、第 19 章

### 第 43 題｜SAP｜單選｜D4 自管 FHIR 伺服器的現代化

一家醫療集團為了與其他醫院交換資料，在 EC2 上自行維運開源的 FHIR 伺服器與 PostgreSQL，存放約 2,000 萬筆 FHIR R4 格式的病患、就診與檢驗資源。團隊每月要花大量時間處理版本升級、效能調校與備份，而研究部門還希望從臨床筆記等非結構化文字中萃取診斷與用藥資訊，再以 SQL 做群體分析。集團希望改用受管服務、維持標準 FHIR API 讓既有的介接醫院不用修改，並盡量減少自行開發。

哪個方案最合適？

- A. 把 PostgreSQL 遷移到 Aurora PostgreSQL，FHIR 伺服器容器化部署到 ECS on Fargate，臨床筆記另外以自建的 NLP 模型處理
- B. 把 FHIR 資源改存到 DynamoDB，以 API Gateway 與 Lambda 自行實作 FHIR REST API，臨床筆記送 Amazon Comprehend Medical 分析
- C. 建立 AWS HealthLake FHIR R4 data store，從 S3 匯入既有資源，讓介接醫院改連 HealthLake 的 FHIR API；以 HealthLake 整合的醫療自然語言處理萃取臨床筆記中的資訊，並以 Athena 查詢資料做群體分析
- D. 以 Amazon Comprehend Medical 取代 FHIR 伺服器，直接把所有病患資料送入 Comprehend Medical 儲存與查詢

> [!answer]- 答案：C
> **A ✗** 這是 replatform：資料庫交給 Aurora、伺服器交給 Fargate 確實減少部分維運，但 FHIR 伺服器的升級與調校仍由自己負責，NLP 也要自建，未達「盡量減少自行開發」。
>
> **B ✗** 自己實作完整的 FHIR REST API（搜尋參數、版本、資源關聯）工作量龐大，也容易與標準產生差異，影響介接醫院。
>
> **C ✓** **AWS HealthLake** 是受管的 FHIR 資料儲存服務，提供標準 FHIR R4 API，可從 S3 大量匯入資源；它的 integrated NLP 會呼叫 Comprehend Medical，從 `DocumentReference` 中的臨床筆記萃取診斷、用藥等醫療實體（這個功能預設關閉，要向 AWS Support 申請開啟），並可與 Athena 整合以 SQL 分析資料與 NLP 結果。既有介接醫院只需改連端點，滿足維持標準 API 與減少開發的需求。
>
> **D ✗** Comprehend Medical 是文字分析 API，只負責從文字中萃取醫療實體，不是資料儲存，也不提供 FHIR API。
>
> **考點**：SAP-4.4｜以 HealthLake 現代化自管 FHIR 平台｜延伸閱讀：第 46 章、第 47 章

### 第 44 題｜SAP｜單選｜D1 報到系統的進階 DDoS 防護

一家國籍航空公司的線上報到與登機證系統放在 CloudFront 與 ALB 後面，過去一年遭受過兩次大規模的 L7 HTTP flood，每次都是工程師半夜被叫起來手動調整 WAF 規則，處理了將近兩小時。此外，攻擊期間 CloudFront 與 ALB 的用量暴增，產生了大筆額外費用。航空公司已訂閱 Business Support。管理層要求：攻擊發生時有 AWS 的專家團隊主動聯繫並協助處理、偵測要能參考應用程式的健康狀態以減少誤判，並在攻擊造成的費用激增時能申請補償。

哪個方案最符合需求？

- A. 在 CloudFront 上啟用 AWS WAF 的 rate-based rule 與 AWS Managed Rules 的 Core rule set，並以 Firewall Manager 集中管理
- B. 依靠預設包含的 AWS Shield Standard，並在 CloudWatch 設定 DDoS 指標的 alarm 通知值班人員
- C. 在 ALB 前面部署 Network Firewall，以 stateful rule 阻擋短時間內大量連線的來源 IP
- D. 訂閱 AWS Shield Advanced 並保護 CloudFront distribution 與 ALB，為受保護資源關聯 Route 53 health check 啟用 health-based detection，設定 proactive engagement 與緊急聯絡人，並啟用 Shield Advanced 的自動 L7 緩解

> [!answer]- 答案：D
> **A ✗** WAF 規則能自動處理部分 HTTP flood，是必要的一層，但無法提供 AWS 專家主動聯繫，也沒有費用補償。
>
> **B ✗** Shield Standard 自動防護常見的 L3／L4 攻擊，但不包含 L7 自動緩解、Shield Response Team 支援或費用補償。
>
> **C ✗** Network Firewall 是 VPC 層的流量檢查服務，放在 ALB 前面也處理不了已經被 CloudFront 吸收的 L7 攻擊，而且同樣沒有專家支援與費用補償。
>
> **D ✓** **Shield Advanced** 提供 Shield Response Team（SRT）支援（需要 Business 或 Enterprise Support）、**proactive engagement**（偵測到攻擊影響應用健康時由 SRT 主動聯繫）、**health-based detection**（以 Route 53 health check 判斷應用是否受影響，降低誤判），以及 DDoS 造成用量激增的 **cost protection**；自動 L7 緩解會在攻擊時自動建立並套用 WAF 規則。
>
> **考點**：SAP-1.2｜Shield Advanced 的 SRT、health-based detection 與 cost protection｜延伸閱讀：第 16 章

### 第 45 題｜SAP｜選三項｜D2 防止 IaC 變更意外取代資料庫

一家天然氣公司以 CloudFormation 透過 CodePipeline 部署客服系統，stack 中包含一個 RDS for PostgreSQL instance。上個月一位工程師在範本中修改了資料庫的一個屬性，該屬性變更需要取代（replacement）資源，CloudFormation 因此建立新的 instance 並刪除舊的，造成 3 小時的資料遺失與服務中斷。團隊要求：類似的變更不得在沒有人工確認的情況下執行；即使被誤執行，也一定要保留舊資料庫的資料；而且不影響其他資源的日常自動部署。

哪三個做法組合最合適？（選三項）

- A. 對 stack 啟用 drift detection，每天檢查一次資源設定是否與範本不同
- B. 在範本中為資料庫資源設定 `DeletionPolicy: Snapshot` 與 `UpdateReplacePolicy: Snapshot`，讓資源被刪除或取代時先建立最終 snapshot
- C. 為 stack 設定 stack policy，拒絕對資料庫資源執行 `Update:Replace` 與 `Update:Delete`，其他資源維持允許更新
- D. 把資料庫拆到 nested stack，讓主 stack 的變更不會影響到資料庫
- E. 為 stack 設定 rollback trigger，在資料庫連線錯誤的 CloudWatch alarm 觸發時自動回滾
- F. 在 pipeline 中改為先建立 change set，若 change set 中有任何資源的 `Replacement` 為 `True`，就送到人工核准步驟後才執行

> [!answer]- 答案：B、C、F
> **A ✗** Drift detection 檢查的是「實際資源被手動改過、與範本不一致」，與範本本身的變更導致取代無關，也無法事先阻止。
>
> **B ✓** **`UpdateReplacePolicy`** 控制資源因更新被取代時舊資源如何處理，**`DeletionPolicy`** 控制資源被刪除時的處理；設為 `Snapshot` 時，CloudFormation 會在移除舊資料庫前建立 snapshot，確保最壞情況下仍能還原資料。
>
> **C ✓** **Stack policy** 可以針對特定邏輯資源拒絕某些類型的更新，讓會取代或刪除資料庫的變更直接失敗，而其他資源照常更新。真正需要變更時，可以在更新時暫時提供覆寫的 stack policy。
>
> **D ✗** Nested stack 只是組織範本的方式，nested stack 中的資源更新同樣會被取代，並不提供保護。
>
> **E ✗** Rollback trigger 在部署後依 alarm 回滾，但資料庫取代時舊 instance 已被刪除，回滾無法找回資料。
>
> **F ✓** **Change set** 會列出每個資源的動作與是否 `Replacement`；在 pipeline 中先檢查 change set，只有包含取代時才進入人工核准，既達到「需要人工確認」，又不影響一般變更的自動部署。
>
> **考點**：SAP-2.1｜UpdateReplacePolicy、stack policy 與 change set 審核｜延伸閱讀：第 37 章

### 第 46 題｜SAP｜單選｜D4 把分析查詢從交易資料庫卸載

一家航空物流公司的貨運追蹤系統使用 Aurora MySQL，營運分析團隊每小時對同一個 cluster 執行大量彙總查詢（各航線貨量、延誤統計），即使已經把查詢導向 Aurora Replica，複雜的 join 仍需數十分鐘，而且分析團隊想把資料與 Redshift 中既有的財務資料一起分析。目前的做法是每晚以自建的 ETL 程式把資料匯出到 Redshift，但資料延遲一天，ETL 程式也經常失敗。公司希望分析資料延遲降到數秒到數分鐘，並盡量減少要維護的資料管線。

哪個方案最合適？

- A. 建立 Aurora MySQL 到 Amazon Redshift 的 zero-ETL integration，讓交易資料近即時地複寫到 Redshift，分析團隊在 Redshift 中把貨運資料與財務資料一起查詢
- B. 在 Aurora 增加 5 個 Aurora Replica 並建立 custom endpoint 專門處理分析查詢
- C. 以 AWS DMS 從 Aurora 做 CDC 寫入 S3，再以 Glue crawler 建立資料表，讓 Redshift Spectrum 查詢
- D. 以 Aurora 的 `SELECT INTO OUTFILE S3` 每 15 分鐘匯出資料到 S3，再以 Redshift `COPY` 命令載入

> [!answer]- 答案：A
> **A ✓** **Zero-ETL integration** 由 AWS 管理從 Aurora 到 Redshift 的近即時複寫，通常在數秒內可在 Redshift 查到新資料，不需要撰寫或維運 ETL 管線；Redshift 是為大型彙總與 join 設計的分析資料倉儲，也能與既有財務資料一起查詢。
>
> **B ✗** 增加 replica 只是分散負載；Aurora 是以 row 為單位儲存的交易引擎，大範圍彙總與複雜 join 本來就不是它的強項，查詢仍然很慢，也無法與 Redshift 中的財務資料一起分析。
>
> **C ✗** DMS 加 Glue 加 Spectrum 做得到，但要維運三個元件與檔案格式，資料管線比 zero-ETL 多很多；若目標是 S3 data lake 而不是 Redshift，這條路徑才較合理。
>
> **D ✗** 自建的定期匯出與載入仍是要維運的 ETL，失敗與延遲的問題依然存在，延遲至少 15 分鐘。
>
> **考點**：SAP-4.3｜Aurora 到 Redshift 的 zero-ETL integration｜延伸閱讀：第 30 章

### 第 47 題｜SAP｜單選｜D1 部署前就阻擋不合規資源

一家遠距照護平台公司以 AWS Control Tower 管理 80 個帳號，所有基礎設施都透過 CloudFormation 部署。資安政策要求：RDS instance 必須啟用加密與自動備份（保留至少 7 天）、S3 bucket 必須啟用 versioning。目前已啟用的 detective controls 能在資源建立後發現問題，但修正往往要花數週，期間仍有風險。資安長要求在 CloudFormation 部署階段就拒絕不合規的資源，而 SCP 無法檢查「備份保留天數」或「bucket 是否啟用 versioning」這類資源屬性。

哪個方案最符合需求，且維運負擔最低？

- A. 在每個帳號撰寫 AWS Config custom rule，搭配 Systems Manager Automation 在偵測到不合規資源時自動修正
- B. 在 Control Tower 啟用更多 preventive controls，以 SCP 拒絕 `rds:CreateDBInstance` 與 `s3:CreateBucket`，只允許平台團隊建立這些資源
- C. 要求所有 pull request 都由資安團隊人工審查 CloudFormation 範本後才能合併
- D. 在相關 OU 啟用 Control Tower 的 proactive controls，讓 CloudFormation hooks 在資源佈建前檢查屬性，不合規的資源會讓 stack 操作失敗

> [!answer]- 答案：D
> **A ✗** Config rule 加自動修正屬於事後偵測與修補，資源仍會先以不合規狀態存在一段時間；在 80 個帳號撰寫與維運 custom rule 的負擔也很高。
>
> **B ✗** 完全禁止建立資源會讓各團隊無法自行部署，形成瓶頸，也沒有檢查屬性。SCP 的條件只能使用 API 請求中提供的 condition key，表達不了這類資源屬性的完整檢查。
>
> **C ✗** 人工審查容易遺漏且無法擴展，也擋不住繞過 pipeline 的部署。
>
> **D ✓** Control Tower 的控制分為三類：preventive（SCP 或 RCP）、detective（Config rules）與 **proactive**。Proactive controls 透過 **CloudFormation hooks** 在資源建立或更新前檢查屬性，不合規時讓操作失敗；它們由 AWS 管理，只需在 OU 啟用即可，正好填補 SCP 無法檢查資源屬性的空缺。
>
> **考點**：SAP-1.4、SAP-1.2｜Control Tower proactive controls 與 CloudFormation hooks｜延伸閱讀：第 14 章、第 40 章

### 第 48 題｜SAP｜單選｜D2 Java 函式的冷啟動延遲

Kestrel 是一家跨國物流 SaaS，報價 API 以 Java 21 搭配 Spring Boot 在 Lambda 上執行，平均延遲 120 毫秒，但冷啟動時 p99 延遲高達 6 秒，大客戶常抱怨。流量有明顯但難以預測的突發，有時 5 分鐘內從每秒 10 個請求跳到 800 個。財務部不希望為大部分時間閒置的預熱容量長期付費。團隊希望以最少的程式修改，顯著降低冷啟動造成的延遲。

哪個方案最合適？

- A. 為函式設定 provisioned concurrency 為 800，確保突發時所有請求都有預熱的執行環境
- B. 為函式啟用 Lambda SnapStart，發布版本並讓 API 呼叫該版本的 alias；檢查初始化程式碼中的唯一值與網路連線在 snapshot 還原後是否需要重新產生
- C. 把函式記憶體從 1,024 MB 提高到 10,240 MB，以取得更多 CPU 縮短初始化時間
- D. 以 EventBridge Scheduler 每分鐘呼叫函式一次保持熱機，避免執行環境被回收

> [!answer]- 答案：B
> **A ✗** Provisioned concurrency 能消除冷啟動，但 800 個預熱環境大部分時間閒置，長期付費正是財務部反對的；若流量可預測，可以搭配排程調整 provisioned concurrency，才比較划算。
>
> **B ✓** **Lambda SnapStart** 在發布版本時先執行初始化，並為初始化後的執行環境建立 snapshot；冷啟動時直接從 snapshot 還原，Java 應用的冷啟動延遲可降到原來的一小部分。對 Java runtime 不另外收費，只需在函式設定啟用並呼叫已發布的版本。要注意初始化時產生的亂數種子、唯一 ID 或連線，在還原後可能需要重新建立。
>
> **C ✗** 更多記憶體會帶來更多 CPU，能縮短部分初始化時間，但 Spring Boot 的類別載入與 framework 初始化仍需數秒，而且每個請求的成本都大幅增加。
>
> **D ✗** 定時呼叫只能保持少數環境熱機，突發的數百個並行請求仍然需要新的執行環境，冷啟動依舊發生。
>
> **考點**：SAP-2.5｜Lambda SnapStart 降低 Java 冷啟動｜延伸閱讀：第 19 章

### 第 49 題｜SAP｜單選｜D3 綁定 instance 的舊授權軟體

一家電力公司的變電站資產管理系統是一套商用軟體，只能安裝在單一伺服器上，授權檔綁定伺服器的 hostname 與 private IP，廠商不提供叢集版本。系統目前在一台使用 EBS 的 EC2（支援的現行世代 instance type）上執行，資料也存放在 EBS。上個月底層硬體故障，instance 停擺 3 小時，工程師最後以 snapshot 重建新 instance，又花了半天向廠商重新申請授權。公司希望在不修改軟體、不額外購買授權的前提下，盡量縮短底層硬體故障造成的中斷。

哪個做法最合適？

- A. 確認 instance 的 automatic recovery 已啟用（支援的 instance type 預設採用 simplified automatic recovery），並建立 `StatusCheckFailed_System` 的 CloudWatch alarm 搭配 recover action 與通知；recover 後的 instance 會保留 instance ID、private IP、Elastic IP 與 EBS volume
- B. 建立 min、max 與 desired 都是 1 的 Auto Scaling group，讓故障的 instance 自動被替換，並以 user data 在開機時從最新 snapshot 還原資料
- C. 以 EBS Multi-Attach 把同一個 io2 volume 掛到另一個 AZ 的待命 instance，故障時由待命 instance 接手
- D. 以 Amazon Data Lifecycle Manager 每小時建立 snapshot，故障時由值班人員從最新 snapshot 建立新 instance

> [!answer]- 答案：A
> **A ✓** **EC2 automatic recovery** 在底層硬體或網路問題造成系統狀態檢查失敗時，把 instance 移到新的硬體上啟動。復原後的 instance 與原本完全相同：instance ID、private IP、Elastic IP、instance metadata 與 EBS volume 都保留，因此綁定 hostname 與 IP 的授權不受影響。它不適用於使用 instance store 的 instance。
>
> **B ✗** Auto Scaling 替換時會建立「新」的 instance，instance ID 與 private IP 都會改變，授權檔失效；從 snapshot 還原也會遺失最後一次 snapshot 後的資料。對 stateless 的服務這是好做法，但不適合綁定身份的單機軟體。
>
> **C ✗** EBS Multi-Attach 只能在同一個 AZ 內掛載，而且需要能處理共享區塊裝置的叢集軟體，一般應用同時掛載會損毀資料；待命 instance 的 IP 不同，授權也無法使用。
>
> **D ✗** 定期 snapshot 能保護資料，但復原仍要人工建立新 instance，IP 與 hostname 改變，與上次事件的問題一樣。
>
> **考點**：SAP-3.4｜EC2 automatic recovery 保留 instance 身份｜延伸閱讀：第 17 章

### 第 50 題｜SAP｜單選｜D4 快速建立遷移的商業論證

一家電信集團的董事會要求雲端團隊在 6 週內提出「是否把三座機房的 3,500 台伺服器遷移到 AWS」的商業論證，內容要包括：依實際使用率調整規格（right-sizing）後的 AWS 預估成本、Windows Server 與 SQL Server 授權的最佳方案比較，以及與現況的 TCO 對照。三座機房以 VMware 與少量實體機為主，資安部不允許在每台伺服器上安裝代理程式，團隊也沒有足夠人力手動整理所有伺服器的規格。

哪個做法最合適？

- A. 在每台伺服器安裝 AWS Application Discovery Service agent，收集 6 週的程序與網路連線資料後，以 AWS Pricing Calculator 逐台估算成本
- B. 使用 Migration Evaluator，在機房部署 agentless collector 收集伺服器的規格與使用率資料，由 Migration Evaluator 產出含 right-sizing 與授權選項比較的 TCO 評估報告
- C. 匯出 VMware vCenter 的伺服器清單，依每台 VM 目前配置的 vCPU 與記憶體，在 AWS Pricing Calculator 中選擇規格相同的 EC2 instance 估算成本
- D. 先把 100 台代表性伺服器以 MGN 遷移到 AWS 執行一個月，以 AWS Compute Optimizer 的建議推估全部 3,500 台的成本

> [!answer]- 答案：B
> **A ✗** 違反「不允許安裝代理程式」的限制；Application Discovery Service 自 2025-11-07 起也不再開放新客戶；而且 Application Discovery Service 的重點是遷移規劃（相依關係、wave），授權比較與 TCO 報告要自己整理，6 週內處理 3,500 台很吃力。
>
> **B ✓** **Migration Evaluator** 專門用來建立遷移的商業論證：agentless collector 從 vCenter 等來源收集規格與實際使用率，依使用率做 right-sizing，並比較 BYOL 與含授權等不同方案，產出 TCO 報告，正好符合董事會要求的內容與時程。
>
> **C ✗** 依「目前配置」而非「實際使用率」對應規格，通常會高估成本；也沒有授權比較，人工整理 3,500 台也不實際。
>
> **D ✗** 先遷移再估算本末倒置，耗時又花錢；Compute Optimizer 只分析已經在 AWS 上的資源，也無法在 6 週內提供完整的 TCO 比較。
>
> **考點**：SAP-4.1｜Migration Evaluator 建立 TCO 商業論證｜延伸閱讀：第 44 章

### 第 51 題｜SAP｜單選｜D1 跨十幾個 Region 的全球網路分段

一家全球航空物流公司在 14 個 Region 共有 300 多個 VPC，另有 60 個分公司以 SD-WAN 設備透過 Site-to-Site VPN 接入。目前每個 Region 有一個 Transit Gateway，彼此以 Transit Gateway peering 全網狀互連，每次新增 Region 或網段，網路團隊都要在多個 Region 手動調整 peering 與 static route，錯誤頻傳。公司要把網路分成 production、development 與 partner 三個區段，區段之間預設不可互通，只有 partner 區段可以存取 production 中特定的共享服務。網路團隊希望用一份集中的政策描述全球網路，自動在各 Region 套用。

哪個方案最符合需求？

- A. 保留各 Region 的 Transit Gateway 與 peering，撰寫 Lambda 函式讀取集中的設定檔，自動建立 peering 並更新各 route table 的 static route
- B. 把所有 VPC 改為透過 VPC peering 與共享服務 VPC 直接互連，以 security group 控制區段之間的存取
- C. 建立 AWS Cloud WAN core network，以 core network policy 定義各 Region 的 edge location 與 production、development、partner 三個 segment，以 attachment policy 依 VPC 標籤自動把 VPC 與 VPN 附加到對應 segment，並設定 segment 之間的 share 規則
- D. 在單一 Region 建立一個集中的 Transit Gateway，讓 14 個 Region 的 VPC 都透過跨 Region 的 VPN 連到它

> [!answer]- 答案：C
> **A ✗** 自建自動化可以減少手動錯誤，但 Transit Gateway peering 只支援 static route，跨 Region 的路由與分段仍要靠自己的程式維護，等於自己寫了一套全球網路控制平面。
>
> **B ✗** VPC peering 不具遞移性，300 多個 VPC 的全網狀 peering 不可行，也不能讓 VPN 分公司透過 peering 轉送。
>
> **C ✓** **AWS Cloud WAN** 以一份 **core network policy** 描述全球網路：要在哪些 Region 部署 core network edge、有哪些 segment、segment 之間如何 share 路由，以及依標籤自動把 attachment 歸入 segment 的規則。Cloud WAN 會在各 Region 自動建立並維護路由，跨 Region 的路由是動態傳遞的，正好解決手動維護 peering 與 static route 的問題。
>
> **D ✗** 所有流量繞到單一 Region 會大幅增加延遲與跨 Region 傳輸費，該 Region 也成為全球網路的單點故障。
>
> **考點**：SAP-1.1｜Cloud WAN 以政策管理全球網路分段｜延伸閱讀：第 41 章

### 第 52 題｜SAP｜單選｜D2 行動 App 直接存取租戶資料

Carelink 是一家跨國居家照護 SaaS，照護員以行動 App 上傳照護紀錄照片到 S3、讀寫 DynamoDB 中的排班資料。服務採共用資源的 pooled 模式：所有租戶共用同一個 bucket（以 `tenant-id/` 作為 prefix）與同一張資料表（partition key 以 tenant ID 開頭）。使用者在 Cognito user pool 登入，ID token 中帶有 `custom:tenant_id` 屬性。為了降低延遲與成本，App 要以 AWS 臨時憑證直接存取 S3 與 DynamoDB，但必須保證任何使用者都只能存取自己租戶的資料，且新增租戶時不必新增任何 IAM role 或 policy。

哪個方案最合適？

- A. 為每個租戶建立一個 IAM role，policy 只允許存取該租戶的 prefix 與 partition key，App 登入後依租戶選擇對應的 role
- B. App 登入後呼叫一個 API Gateway 端點，由後端 Lambda 以權限較大的 role 存取 S3 與 DynamoDB，並在程式中檢查租戶 ID
- C. 在 S3 bucket policy 中為每個租戶加入一條 statement，以 `aws:userid` 條件限制只能存取對應的 prefix
- D. 以 Cognito identity pool 交換臨時憑證，啟用 attributes for access control，把 `custom:tenant_id` 對應為 principal tag；authenticated role 的 policy 以 `${aws:PrincipalTag/tenant_id}` 限制 S3 的 prefix，並以 `dynamodb:LeadingKeys` 條件限制 partition key

> [!answer]- 答案：D
> **A ✗** 一租戶一 role 在數千個租戶時會碰到 IAM role 數量的配額上限，每新增租戶都要建立 role，也違反「不新增 IAM 資源」的需求。
>
> **B ✗** 由後端統一存取是常見做法，但租戶隔離完全依賴程式碼檢查，一個 bug 就可能跨租戶存取；也不符合「App 直接存取以降低延遲與成本」的設計目標。
>
> **C ✗** 每個租戶都要修改 bucket policy，而 bucket policy 有大小上限（20 KB），租戶一多就放不下；也沒有處理 DynamoDB。
>
> **D ✓** **Cognito identity pool** 的 **attributes for access control** 把使用者屬性對應成 session 的 **principal tag**。單一 role 的 policy 用 `${aws:PrincipalTag/tenant_id}` 動態組出允許的 S3 prefix，以 `dynamodb:LeadingKeys` 限制只能存取以該租戶 ID 開頭的 partition key。這是 ABAC：一份 policy 適用所有租戶，新增租戶不必新增 IAM 資源。
>
> **考點**：SAP-2.3｜Cognito identity pool 的 principal tag 與 ABAC 租戶隔離｜延伸閱讀：第 13 章、第 49 章

### 第 53 題｜SAP｜單選｜D3 找出微服務的延遲源頭

一家電信公司的線上門市由 EKS 上的 40 個微服務組成，主要以 Java 與 Python 撰寫。每當結帳延遲升高，各團隊都只能各自看自己服務的 CPU 與日誌，往往要花數小時才找出是哪個服務或哪個下游呼叫造成的。維運主管希望：自動取得各服務的請求量、延遲與錯誤率，看到服務之間的呼叫關係圖，並能為「結帳 API 的 p99 延遲」設定服務層級目標（SLO），在目標快要違反時告警。各團隊希望盡量不修改程式碼。

哪個方案最符合需求？

- A. 要求每個團隊在程式中以 `PutMetricData` 送出自訂的延遲與錯誤 metric，再以 CloudWatch dashboard 彙整
- B. 啟用 VPC Flow Logs 並以 CloudWatch Logs Insights 分析服務之間的連線數與流量
- C. 在 EKS cluster 安裝 Amazon CloudWatch Observability add-on，啟用 CloudWatch Application Signals，以自動 instrumentation 收集各服務的 metric 與 trace，在 service map 檢視呼叫關係，並為結帳 API 建立 SLO
- D. 在每個服務的 container 中加入 X-Ray SDK 並修改程式碼為每個下游呼叫建立 subsegment，再以 X-Ray 主控台分析

> [!answer]- 答案：C
> **A ✗** 自訂 metric 需要每個團隊改程式，只有各服務各自的數字，看不到呼叫關係與跨服務的延遲來源，SLO 也要自己計算。
>
> **B ✗** Flow Logs 只記錄 IP 與 port 層級的連線資訊，沒有請求延遲與錯誤率，也無法對應到 API。
>
> **C ✓** **CloudWatch Application Signals** 以 OpenTelemetry 為基礎，透過 add-on 對 Java、Python 等應用做自動 instrumentation，不需修改程式碼即可收集請求量、延遲、錯誤率與分散式 trace；service map 呈現服務之間的呼叫關係，並內建 SLO 與 burn rate 告警。
>
> **D ✗** X-Ray 能提供 trace 與 service map，但手動加入 SDK 與 subsegment 需要大量程式修改，也不包含 SLO 管理。若團隊已全面使用 X-Ray SDK，X-Ray 仍是可行的 tracing 後端。
>
> **考點**：SAP-3.1｜Application Signals 的自動 instrumentation 與 SLO｜延伸閱讀：第 36 章

### 第 54 題｜SAP｜單選｜D2 補助申請截止日的瞬間尖峰

一個政府機關的線上補助申請系統由 API Gateway、Lambda 與 RDS for PostgreSQL 組成，平時每秒 20 件申請。每次申請截止前 2 小時，流量會在幾分鐘內暴增到每秒 3,000 件，Lambda 瞬間大量並行寫入，資料庫連線與 CPU 耗盡，民眾看到逾時錯誤。法規規定截止前送出的申請都必須受理，不得拒絕；但申請不需要立即完成審核，只要在送出時取得「已收件」的編號，並能在 30 分鐘內寫入資料庫即可。

哪個方案最符合需求？

- A. 在 API Gateway 設定每秒 300 個請求的 throttling，超過的請求回傳 429，並在網頁提示民眾稍後重試
- B. 把 RDS 升級到最大的 instance class，並把 Lambda 的 reserved concurrency 設為 3,000，確保所有請求都能被處理
- C. 讓 API Gateway 直接把申請寫入 SQS queue 並回傳收件編號；以 Lambda 的 SQS event source mapping 消化 queue，設定 maximum concurrency 讓同時寫入資料庫的函式數量維持在資料庫可承受的範圍
- D. 對 Lambda 設定 reserved concurrency 為 100，讓同時連線資料庫的數量受到限制

> [!answer]- 答案：C
> **A ✗** 回傳 429 等於拒絕申請，民眾若在截止前重試失敗就無法送件，違反「不得拒絕」的法規要求。
>
> **B ✗** 把資料庫升到最大規格仍不一定撐得住每秒 3,000 筆的同步寫入與連線，而且只為每年數次的尖峰付出高額成本；reserved concurrency 設為 3,000 反而讓更多函式同時衝擊資料庫。
>
> **C ✓** 這是 **queue-based load leveling**：API Gateway 直接整合 SQS，申請一進 queue 就能回覆收件編號，前端不再受資料庫速度限制；SQS 可承受突發流量。Event source mapping 的 **maximum concurrency** 控制同時處理 queue 的函式數量，讓資料庫以穩定的速率消化積壓，在 30 分鐘內完成寫入。
>
> **D ✗** API Gateway 同步呼叫 Lambda 時，超過 reserved concurrency 的請求會被 throttle 並回傳錯誤，同樣等於拒絕申請。限制並行數的做法必須搭配 queue 才不會丟失請求。
>
> **考點**：SAP-2.4｜SQS 削峰與 event source mapping maximum concurrency｜延伸閱讀：第 20 章、第 32 章

### 第 55 題｜SAP｜單選｜D1 依電表保序並可重播的事件流

一家電力公司部署了 400 萬具智慧電表，每 15 分鐘回報一次讀數，尖峰時每秒約 8 萬筆事件。下游有三個獨立的系統要處理同一份資料：即時停電偵測、計費與用電預測模型訓練。每具電表的事件必須依產生順序處理，否則停電偵測會誤判；計費系統若發現程式錯誤，要能重新處理過去 7 天的事件。架構團隊希望使用受管服務並能水平擴展。

哪個方案最合適？

- A. 使用 Kinesis Data Streams，以電表 ID 作為 partition key，把 retention period 設為 7 天，三個下游系統各自作為獨立的 consumer 讀取，需要時從指定時間點重新讀取
- B. 使用 SQS FIFO queue，以電表 ID 作為 message group ID，三個下游系統共用同一個 queue 輪流讀取
- C. 使用 SNS standard topic 扇出到三個 SQS standard queue，每個下游系統讀取自己的 queue，並把 queue 的 retention 設為 7 天
- D. 使用 EventBridge custom event bus 搭配三條規則分送到三個下游系統，並啟用 event archive 以便日後 replay

> [!answer]- 答案：A
> **A ✓** **Kinesis Data Streams** 保證同一個 partition key 的資料落在同一個 shard 並依序保存；以電表 ID 為 key 即可保證每具電表的順序。資料在 retention period 內持續保留，多個 consumer 各自維護讀取位置，可以從指定的時間點或序號重新讀取，滿足計費系統重播 7 天的需求。
>
> **B ✗** FIFO queue 能依 message group 保序，但訊息被一個 consumer 處理並刪除後就消失，三個系統無法各自讀取同一份資料，也無法重播已處理的訊息。
>
> **C ✗** SNS standard 與 SQS standard 都不保證順序；訊息處理後被刪除，也無法重播。
>
> **D ✗** EventBridge 不保證事件的傳遞順序；archive 與 replay 可以重送事件，但重播時的順序同樣不保證，停電偵測會誤判。
>
> **考點**：SAP-1.3｜Kinesis 以 partition key 保序並支援多 consumer 重播｜延伸閱讀：第 31 章

### 第 56 題｜SAP｜單選｜D4 大型 NFS 共享的搬遷與切換

一個政府地政單位要把地端 NAS 上 120 TB、約 3 億個檔案的 NFS 共享（地籍圖檔與掃描文件）遷移到 Amazon EFS，應用程式伺服器同時也會遷移到 AWS。地端與 AWS 之間有一條 10 Gbps 的 Direct Connect，但上班時間這條線還要承載其他系統流量，搬遷流量在上班時間不得超過 2 Gbps。搬遷期間民眾申辦仍會持續新增與修改檔案，最終切換的停機時間不得超過 2 小時，並要能驗證搬遷後檔案的完整性。

哪個方案最合適？

- A. 在 AWS 上啟動一台 EC2 掛載 EFS，以 rsync 透過 DX 從地端 NAS 複製檔案，切換前再執行一次 rsync 同步差異
- B. 部署 Storage Gateway 的 S3 File Gateway，讓地端應用改寫入 gateway，再把 S3 中的資料複製到 EFS
- C. 以 AWS Transfer Family 建立 SFTP 端點，從地端 NAS 以 SFTP 上傳檔案到 EFS
- D. 在地端部署 AWS DataSync agent，建立從 NFS 到 EFS 的 DataSync task 並透過 DX 傳輸，以 task 排程安排傳輸，上班時間執行時把 task 的 bandwidth limit 設在 2 Gbps（執行中也可調整），下班時間再放寬；先完成初次全量傳輸，之後定期執行增量傳輸，切換時停止寫入再執行最後一次增量並驗證資料

> [!answer]- 答案：D
> **A ✗** rsync 可行，但 3 億個檔案在比對差異時非常耗時，最後一次同步不一定能在 2 小時內完成；平行化、重試、頻寬控制與驗證都要自己處理。
>
> **B ✗** File Gateway 是給地端應用持續以 NFS／SMB 存取 S3 的 hybrid 服務，目的地是 S3 而不是 EFS；再從 S3 轉存到 EFS 等於多一段搬遷。
>
> **C ✗** Transfer Family 是給外部夥伴以 SFTP 等協定交換檔案的服務，不適合大量檔案的一次性搬遷，也沒有增量同步與完整性驗證。
>
> **D ✓** **DataSync** 專門處理大量檔案的線上搬遷：agent 以平行方式讀取 NFS，透過 DX 傳到 EFS，可設定 bandwidth limit（執行中也能調整）與 task 排程。後續執行只傳輸有變更的檔案，最終增量傳輸量小，能在停機時段內完成；task 也支援傳輸後的資料完整性驗證。
>
> **考點**：SAP-4.2｜DataSync 的頻寬控制、增量傳輸與驗證｜延伸閱讀：第 25 章、第 45 章

### 第 57 題｜SAP｜單選｜D2 數十億個小檔案的長期封存

一家能源公司的風機感測資料以每 10 秒一個 JSON 檔（平均 8 KB）的方式寫入 S3 Standard，目前累積了約 30 億個物件，每天再新增 2,500 萬個。法規要求原始資料保存 10 年；資料寫入 30 天後幾乎不會被存取，偶爾稽核需要調閱時可以接受 48 小時內取得。財務部要求大幅降低這筆儲存成本。

哪個方案最符合成本效益？

- A. 設定 lifecycle rule，物件建立 30 天後直接轉到 S3 Glacier Deep Archive
- B. 每天以排程作業把前一天的小檔案依風機與日期合併、壓縮成較大的物件（例如數百 MB 的檔案），把合併後的物件轉存到 S3 Glacier Deep Archive，確認無誤後刪除原始的小物件
- C. 把所有物件轉到 S3 Intelligent-Tiering，並啟用 Archive Access 與 Deep Archive Access 層，讓物件依存取情況自動封存
- D. 設定 lifecycle rule，物件建立 30 天後轉到 S3 Glacier Instant Retrieval

> [!answer]- 答案：B
> **A ✗** Lifecycle 轉換按每個物件收取請求費用，30 億個物件的轉換費很可觀；封存到 Glacier 類別的每個物件還會額外產生約 40 KB 的計費額外負擔（metadata），對 8 KB 的物件等於大幅增加計費容量。此外，目前 lifecycle 預設不會轉換小於 128 KB 的物件。
>
> **B ✓** 小物件的封存要先**合併**：把每天數千萬個小檔案合併壓縮成少量大物件，轉換請求數與每個物件的額外負擔都大幅減少，壓縮後計費容量也更小；Deep Archive 是最便宜的儲存類別，取回時間在 48 小時內，符合稽核需求。
>
> **C ✗** 小於 128 KB 的物件不會被 Intelligent-Tiering 自動分層，會一直留在 Frequent Access 層，等於沒有省到錢。
>
> **D ✗** Glacier Instant Retrieval 適合需要毫秒存取的冷資料，單價高於 Deep Archive；題目接受 48 小時取回，不需要支付即時存取的費用，小物件的問題也沒有解決。
>
> **考點**：SAP-2.6｜小物件先合併再封存到 Deep Archive｜延伸閱讀：第 23 章

### 第 58 題｜SAP｜單選｜D3 集中化安全日誌供 SIEM 分析

一家醫院集團有 50 個 AWS 帳號，安全相關的日誌分散在各帳號：CloudTrail、VPC Flow Logs、Route 53 Resolver query logs、Security Hub findings 與 EKS audit logs，格式各不相同。資安中心使用第三方 SIEM，目前每種日誌都要寫一套轉換程式，經常因格式變更而中斷。新的要求是：所有帳號與 Region 的這些日誌集中存放在資安帳號、使用一致的標準化格式、可自訂保留期限，並讓 SIEM 與內部的 Athena 查詢都能使用，同時盡量減少自建的日誌管線。

哪個方案最合適？

- A. 啟用 Amazon Security Lake，指定資安帳號為 delegated administrator，在所有帳號與 Region 啟用上述 AWS 日誌來源，資料會以 OCSF 格式存放在資安帳號的 S3；為 SIEM 建立 subscriber，並以 Athena 查詢
- B. 在每個帳號建立 CloudWatch Logs subscription filter，把所有日誌經 Data Firehose 送到集中帳號的 S3，再以 Lambda 把每種格式轉換為 SIEM 的格式
- C. 建立 organization trail 收集 CloudTrail，其他日誌維持在各帳號，由 SIEM 以跨帳號 role 直接讀取各帳號的日誌
- D. 在資安帳號建立 Amazon OpenSearch Service domain，以各帳號的 Lambda 把所有日誌推送到 OpenSearch，SIEM 再從 OpenSearch 匯出資料

> [!answer]- 答案：A
> **A ✓** **Amazon Security Lake** 自動從組織內的帳號與 Region 收集 CloudTrail、VPC Flow Logs、Route 53 Resolver logs、Security Hub findings、EKS audit logs 等來源，轉換為開放標準 **OCSF** 格式，以 Parquet 存放在你自己帳號的 S3，可設定保留期限。**Subscriber** 機制讓 SIEM 取得資料或查詢權限，Athena 也能直接查詢，不需要自建轉換程式。
>
> **B ✗** 這是自建日誌管線，每種格式都要自己轉換與維護，正是目前一直中斷的問題；而且並非所有來源都送到 CloudWatch Logs。
>
> **C ✗** 只集中了 CloudTrail，其他日誌仍分散且格式不一，SIEM 跨帳號讀取的整合與權限管理更複雜。
>
> **D ✗** OpenSearch 適合即時搜尋與儀表板，但推送程式與格式轉換仍要自建，還要維運 domain 的容量；以它作為 SIEM 的中轉站也增加成本。
>
> **考點**：SAP-3.2｜Security Lake 以 OCSF 集中安全日誌｜延伸閱讀：第 16 章、第 36 章

### 第 59 題｜SAP｜單選｜D1 以月為週期的資源規格建議

Northwind Ledger 是一家跨國會計 SaaS，在 Organization 中有 55 個帳號，執行約 4,000 台 EC2、數百個 Auto Scaling group、大量 EBS volume 與 Lambda 函式。工作負載有明顯的月結週期：每月最後 5 天使用率很高，其他時間偏低。財務長懷疑大量資源規格過大，要求平台團隊在全組織產出可執行的 right-sizing 建議，但上一次依「過去兩週的資料」做出的建議，讓幾個服務在月底被調得太小而出事。

哪個做法最合適？

- A. 以 Trusted Advisor 的 Low Utilization Amazon EC2 Instances 檢查找出使用率偏低的 instance，逐一調小規格
- B. 以 Cost Explorer 的 rightsizing recommendations 取得建議，並設定為依過去 14 天的使用資料計算
- C. 在 management account 啟用 AWS Compute Optimizer 的組織層級選擇加入，指定 delegated administrator，並啟用 enhanced infrastructure metrics 讓建議依約三個月的使用資料計算，涵蓋多個完整的月結週期
- D. 自行撰寫腳本匯出所有 instance 的 CloudWatch CPU metric，以月平均使用率低於 40% 為標準調小規格

> [!answer]- 答案：C
> **A ✗** Trusted Advisor 的低使用率檢查只看過去 14 天且只涵蓋 EC2，同樣會忽略月結尖峰，正是上次出事的原因。
>
> **B ✗** Cost Explorer 的 rightsizing 建議只針對 EC2，回顧期也短，無法完整涵蓋月結週期，也沒有 Auto Scaling group、EBS 與 Lambda 的建議。
>
> **C ✓** **Compute Optimizer** 可以在組織層級為所有成員帳號產生 EC2、Auto Scaling group、EBS、Lambda 等資源的規格建議。預設以過去 14 天的資料分析；啟用 **enhanced infrastructure metrics**（付費功能）後，回顧期延長到約三個月，能看到多次月結尖峰，避免建議調得過小。
>
> **D ✗** 自訂腳本用月平均判斷，會把只有 5 天的尖峰平均掉，正是最危險的錯誤；CloudWatch 預設也不收集記憶體使用率，判斷依據不完整。
>
> **考點**：SAP-1.5｜Compute Optimizer 組織層級與 enhanced infrastructure metrics｜延伸閱讀：第 39 章

### 第 60 題｜SAP｜選三項｜D2 預約掛號系統的 warm standby

一家醫學中心的預約掛號系統部署在 ap-northeast-1：ALB 後面是 ECS on Fargate 服務，資料庫是 Aurora MySQL，病患上傳的轉診文件存放在 S3。新的營運持續計畫要求：Region 整區故障時 RPO 不超過 1 分鐘、RTO 不超過 15 分鐘；切換流程不能依賴故障 Region 的任何服務；預算只允許備援 Region 平時維持少量運算容量，不能採用兩地都以全規模運作的 active-active。

哪三個步驟組合最合適？（選三項）

- A. 把 Aurora 加入 Aurora Global Database，在 ap-southeast-1 建立 secondary cluster；S3 bucket 以 Cross-Region Replication 複寫到 ap-southeast-1 的 bucket
- B. 在 ap-southeast-1 以與主要 Region 相同的規模持續運作 ECS 服務，並以 Route 53 weighted routing 平時各分 50% 流量
- C. 在 ap-southeast-1 預先部署完整的 ALB 與 ECS 服務，平時只執行少量 task，並設定 Service Auto Scaling，切換時把 desired count 調高到正式規模
- D. 備援 Region 平時不部署任何資源，故障時以 CloudFormation 建立整個環境，並從最新的 Aurora snapshot 還原資料庫
- E. 以 AWS Backup 每天把 Aurora snapshot 複製到 ap-southeast-1，作為備援 Region 唯一的資料來源
- F. 以 Route 53 Application Recovery Controller 的 routing control 控制兩個 Region 的 DNS 記錄，切換時透過 ARC 的 data plane 端點變更 routing control 狀態，把流量導到 ap-southeast-1

> [!answer]- 答案：A、C、F
> **A ✓** Aurora Global Database 的跨 Region 複寫延遲通常低於 1 秒，S3 CRR 讓轉診文件也在備援 Region 有副本，兩者共同滿足 1 分鐘 RPO。若需要 S3 複寫時間的保證，可以啟用 Replication Time Control。
>
> **B ✗** 兩地全規模、平時各分 50% 流量就是 active-active，違反預算限制。若 RTO 要求接近零、預算充足，才採用這種 multi-site 設計。
>
> **C ✓** 這是 **warm standby** 的核心：備援 Region 有一套完整但縮小規模的環境持續運作，切換時只需擴容，不必從零建立，可以在 15 分鐘內承接全部流量。與 pilot light 相比，它多了正在運行的應用層，RTO 更短。
>
> **D ✗** 從零建立環境並從 snapshot 還原屬於 backup & restore，RPO 取決於 snapshot 時間點，RTO 也很難在 15 分鐘內完成。
>
> **E ✗** 每天一次的 snapshot 複製 RPO 是 24 小時，無法滿足 1 分鐘的要求。
>
> **F ✓** **ARC routing control** 的狀態變更透過分散在多個 Region 的 data plane 端點進行，不依賴故障 Region 或 Route 53 的 control plane，符合「切換不能依賴故障 Region」的要求。
>
> **考點**：SAP-2.2｜warm standby 的資料複寫、縮小規模環境與 ARC 切換｜延伸閱讀：第 34 章

### 第 61 題｜SAP｜單選｜D3 開放資料入口的快取命中率

一個政府開放資料平台以 CloudFront 前置在 ap-northeast-1 的 ALB 與 EC2 上，提供統計資料的查詢 API 與檔案下載。分析發現 CloudFront 快取命中率只有 12%，ALB 背後的 EC2 經常滿載。原因是 distribution 沿用舊的設定，把所有 header、所有 cookie 與所有 query string 都轉送給 origin 並納入快取鍵，而實際上 API 回應只依 `dataset` 與 `year` 兩個 query string 參數而變，cookie 只用於網站的語系偏好、與 API 無關。全球使用者來自數十個國家，同一份資料會被不同 edge location 重複向 origin 請求。

哪個方案最能提高快取命中率並降低 origin 負載？

- A. 把 cache behavior 的 default TTL 從 1 天提高到 30 天，讓物件在 edge 保存更久
- B. 在 ALB 前面增加一層 ElastiCache，讓 EC2 先查快取再查資料庫
- C. 為 API 建立 Lambda@Edge 函式，在 origin request 事件中改寫請求，把所有 query string 都移除
- D. 為 API 路徑建立 cache policy，快取鍵只包含 `dataset` 與 `year` 兩個 query string，不包含 cookie 與不必要的 header；另以 origin request policy 轉送 origin 確實需要的值，並在靠近 origin 的 Region 啟用 Origin Shield

> [!answer]- 答案：D
> **A ✗** 快取鍵包含所有 header、cookie 與 query string 時，幾乎每個請求都是不同的快取鍵，延長 TTL 也無法讓不同使用者共用快取；問題在快取鍵，不在保存時間。
>
> **B ✗** ElastiCache 能減輕資料庫負擔，但每個請求仍要經過 CloudFront 到 ALB 到 EC2，origin 的請求量沒有降低。
>
> **C ✗** 移除所有 query string 會讓不同的 `dataset` 與 `year` 共用同一份快取，使用者會拿到錯誤的資料。
>
> **D ✓** **Cache policy** 決定快取鍵：只納入真正影響回應的兩個參數，相同查詢的請求就能共用快取。**Origin request policy** 把 origin 需要但不影響快取的值另外轉送，不會降低命中率。**Origin Shield** 在 edge 與 origin 之間增加一層集中快取，讓各地 edge location 的未命中先匯集到同一處，進一步減少 origin 收到的重複請求。
>
> **考點**：SAP-3.3｜cache policy、origin request policy 與 Origin Shield｜延伸閱讀：第 11 章

### 第 62 題｜SAP｜選兩項｜D4 逐步拆解電費帳務單體應用

一家售電業者的帳務系統是一個十多年的 Java 單體應用，部署在 EC2 上，連接一個大型 Oracle 資料庫。業務部門希望先把「電表讀數匯入與驗證」功能拆成獨立服務，以便快速支援新的智慧電表格式，之後再逐步拆出其他功能。管理層不接受一次性重寫（風險與時程都太大），拆分期間系統必須持續對外服務，且任何時候都要能把流量切回舊功能。

哪兩個做法最符合 strangler fig 的現代化方式？（選兩項）

- A. 暫停新功能開發 12 個月，以新技術一次重寫整個帳務系統，完成後一次切換
- B. 在單體應用前面放置 ALB（或 API Gateway），以路徑規則把電表讀數相關的請求導到新的服務，其餘請求仍送到單體應用；需要回退時只要修改路由規則
- C. 讓新的讀數服務直接讀寫單體應用 Oracle 資料庫中的同一組資料表，以免處理資料同步
- D. 讓新服務擁有自己的資料儲存，過渡期以 CDC 或事件把單體應用仍需要的讀數資料同步回去，逐步減少兩邊對同一份資料的依賴
- E. 先把單體應用搬到更大的 EC2 instance 並增加 Oracle 的 read replica，等效能問題解決後再考慮拆分

> [!answer]- 答案：B、D
> **A ✗** 一次性重寫正是管理層拒絕的「big bang」做法，期間業務停滯、切換風險高。
>
> **B ✓** **Strangler fig** 的核心是在既有系統前加一層路由（facade）：新功能完成一塊就把對應的路徑導到新服務，其餘仍由舊系統處理。路由規則可以隨時改回，滿足「隨時切回」的要求。
>
> **C ✗** 共用資料表會讓新舊系統在 schema 上緊密耦合，舊系統的任何 schema 變更都可能破壞新服務，也無法獨立擴展，等於只是換了部署位置的單體。過渡期短暫共用可以接受，但不能作為目標設計。
>
> **D ✓** 微服務應該擁有自己的資料。過渡期以 CDC（例如 DMS）或事件同步，讓單體應用仍能取得需要的資料，再隨著更多功能被拆出而逐步移除同步，是降低資料耦合的常見做法。
>
> **E ✗** 垂直擴展與 read replica 只是延後問題，並沒有開始拆分，也不支援新的電表格式需求。
>
> **考點**：SAP-4.4｜strangler fig 的路由層與資料所有權｜延伸閱讀：第 46 章

### 第 63 題｜SAP｜選兩項｜D1 組織層級的 S3 資料邊界

一個政府衛生主管機關在 Organization 中有 40 個帳號，存放全國疫苗接種資料。稽核提出兩個風險：第一，有帳號曾把 bucket policy 設為允許某個外部研究機構的 AWS 帳號讀取，雖然出於好意卻沒有經過核准；第二，內部 EC2 上的程式若被入侵，可能把資料上傳到攻擊者自己帳號的 bucket。機關要求以組織層級的護欄同時防範這兩種情況，各帳號管理員即使擁有完整權限也無法繞過；AWS 服務代表機關存取資源（例如 CloudTrail 寫入日誌）的功能不能受影響。存放這些資料的 VPC 都沒有 Internet Gateway 或 NAT，EC2 只能透過 S3 gateway endpoint 存取 S3。

哪兩個做法最合適？（選兩項）

- A. 在 Organization root 附加 resource control policy（RCP），拒絕所有 `aws:PrincipalOrgID` 不是本組織、且 `aws:PrincipalIsAWSService` 為 false 的 principal 對 S3 資源的存取
- B. 在 Organization root 附加 SCP，拒絕不屬於本組織的 principal 執行任何 S3 動作
- C. 在 Organization 的每個帳號啟用 S3 Block Public Access，防止 bucket 被分享給外部帳號
- D. 在每個 VPC 的 S3 gateway endpoint 設定 endpoint policy，只允許存取 `aws:ResourceOrgID` 等於本組織的 bucket，並以 SCP 禁止成員帳號修改 endpoint policy、建立 Internet Gateway 或 NAT Gateway
- E. 在所有帳號啟用 Amazon Macie，偵測含有接種資料的 bucket 是否被分享給外部帳號，並寄送通知

> [!answer]- 答案：A、D
> **A ✓** **RCP** 是附加在 Organization、OU 或帳號上、限制「資源」可以被誰存取的政策，對成員帳號中的資源生效，即使帳號管理員在 bucket policy 中授權外部帳號，RCP 的 deny 仍會阻擋。排除 `aws:PrincipalIsAWSService` 為 true 的請求，可以避免影響 AWS 服務以 service principal 代表你存取資源的功能（例如 CloudTrail 寫入日誌）。實務寫法是以 `StringNotEqualsIfExists` 比對 `aws:PrincipalOrgID`、以 `BoolIfExists` 比對 `aws:PrincipalIsAWSService`。RCP 不影響 management account 中的資源。
>
> **B ✗** SCP 只限制本組織內的 principal 能做什麼，外部帳號的 principal 不受你的 SCP 管轄，所以無法阻止外部帳號存取你的 bucket。這正是 RCP 要補的缺口。
>
> **C ✗** Block Public Access 阻擋的是「公開」存取；授權給某個特定外部帳號不算公開，無法被它阻擋。
>
> **D ✓** 防範資料被送到外部 bucket，要在網路路徑上限制「可以存取哪些資源」。攻擊者多半會用「自己帳號」的憑證上傳，SCP 管不到這些外部憑證；但 endpoint policy 會套用到所有經過 endpoint 的請求，不論用的是誰的憑證，所以以 **`aws:ResourceOrgID`** 只允許存取本組織擁有的 bucket，就能擋下上傳到外部 bucket 的請求。這些 VPC 沒有其他通往 Internet 的路徑，請求無法繞過 endpoint；SCP 則禁止成員帳號的管理員放寬 endpoint policy 或新增 Internet 出口，讓這道護欄無法被繞過。這是資料邊界中「只能存取受信任的資源」的部分。
>
> **E ✗** Macie 能偵測 bucket 被分享給外部帳號，但它是偵測而非阻擋，也無法處理資料被上傳到外部 bucket 的情況。
>
> **考點**：SAP-1.2、SAP-1.4｜RCP 與 endpoint policy 組成資料邊界｜延伸閱讀：第 14 章、第 6 章

### 第 64 題｜SAP｜單選｜D2 5G 核心網路的封包處理延遲

一家電信公司要在 AWS 上部署 5G 核心網路的 user plane function（UPF），每個 UPF 叢集由 8 台大型 EC2 組成，節點之間需要極低且穩定的延遲與很高的每秒封包數（PPS）。設計審查決定：可用性透過「在第二個 AZ 部署另一個 UPF 叢集作為備援」來達成，單一叢集內部不要求跨 AZ。網路團隊希望在這個前提下讓叢集內節點間的網路效能達到最佳。

哪個做法最合適？

- A. 把每個 UPF 叢集的 8 台 instance 放進同一個 cluster placement group，選用支援 ENA 增強網路的 instance type；兩個叢集分別位於不同 AZ
- B. 把每個 UPF 叢集的 8 台 instance 放進 spread placement group，讓每台 instance 位於不同的硬體機架
- C. 把每個 UPF 叢集的 8 台 instance 平均分散在三個 AZ，以取得最高的可用性
- D. 把每個 UPF 叢集的 8 台 instance 放進 partition placement group，每個 partition 放 2 台

> [!answer]- 答案：A
> **A ✓** **Cluster placement group** 把 instance 放在同一個 AZ 中網路拓撲相近的位置，提供最低的節點間延遲與最高的 PPS，適合 HPC 與電信封包處理這類緊密耦合的工作負載。題目已決定以另一個 AZ 的叢集處理可用性，因此可以接受單一叢集集中在一個 AZ 的風險。
>
> **B ✗** Spread placement group 讓每台 instance 位於不同機架以降低同時故障的機率（每個 AZ 每個 group 最多 7 台 instance），8 台在同一個 AZ 放不下，也無法提供最低延遲。
>
> **C ✗** 跨 AZ 部署會增加節點間延遲與跨 AZ 傳輸費，違反「叢集內網路效能最佳」的目標。
>
> **D ✗** Partition placement group 用於 HDFS、Cassandra 等需要「感知機架故障域」的大型分散式系統，重點在故障隔離而非最低延遲。
>
> **考點**：SAP-2.5｜cluster placement group 的低延遲與高 PPS｜延伸閱讀：第 17 章

### 第 65 題｜SAP｜單選｜D3 Lambda 帳單的浪費

Meridia 是一家跨國客服工單 SaaS，有 320 個 Lambda 函式，以 Python 與 Node.js 撰寫，沒有使用依賴特定 CPU 架構的原生套件。Lambda 每月費用約 8 萬美元，其中絕大部分是 duration 費用。檢查後發現：當初為了「保險」，所有函式的記憶體都統一設為 3,008 MB，但大多數函式的最大記憶體使用量不到 400 MB；所有函式也都使用 x86_64 架構。財務長要求在不改寫程式邏輯的前提下，最大幅度降低這筆費用。

哪個方案最合適？

- A. 購買三年期 Compute Savings Plans 涵蓋目前的 Lambda 用量，維持現有設定不變
- B. 把所有函式改寫為長時間執行的 container 服務，部署到 ECS on Fargate
- C. 依 Compute Optimizer 的 Lambda 記憶體建議或以 Lambda Power Tuning 實測，為每個函式調整到成本與效能最佳的記憶體；測試通過後把函式架構改為 arm64（Graviton），之後再依調整後的穩定用量考慮 Savings Plans
- D. 為所有函式設定 provisioned concurrency，以較低的 duration 單價計費

> [!answer]- 答案：C
> **A ✗** Compute Savings Plans 對 Lambda 只有有限的折扣，而且是在「浪費的用量」上打折；若先承諾了目前的用量，調整規格後反而可能承諾過多。正確順序是先消除浪費，再承諾。
>
> **B ✗** 改寫為 container 服務違反「不改寫程式邏輯」的限制，對事件驅動的工作負載也不一定比較便宜。
>
> **C ✓** Lambda 依「記憶體大小 × 執行時間」計費。記憶體設得遠大於需求是最常見的浪費，但記憶體也決定 CPU，因此要用 **Compute Optimizer** 或 **Power Tuning** 找出每個函式的最佳點。**arm64（Graviton）** 架構每 GB-秒的單價比 x86_64 低，對沒有原生套件的 Python 與 Node.js 通常只需修改設定並測試。
>
> **D ✗** Provisioned concurrency 會為預熱的執行環境持續收費；只有在使用率長期很高時，整體才可能較便宜，用來處理一般流量反而會增加費用。
>
> **考點**：SAP-3.5｜Lambda 記憶體 right-sizing 與 Graviton｜延伸閱讀：第 19 章、第 39 章

### 第 66 題｜SAP｜單選｜D1 SD-WAN 與 AWS 的動態路由整合

一家能源公司在全國 200 個場站使用第三方 SD-WAN 方案，網路團隊希望把 AWS 納入 SD-WAN 架構：在 AWS 上部署同一廠商的 SD-WAN 虛擬設備，再讓它與 Transit Gateway 交換路由，讓場站能存取 40 個 VPC。需求是：以 BGP 動態交換路由；虛擬設備與 Transit Gateway 之間的頻寬要高於單一 IPsec VPN tunnel 的上限；設備與 Transit Gateway 之間不需要 IPsec 加密（SD-WAN overlay 本身已加密）。

哪個方案最合適？

- A. 在 SD-WAN 虛擬設備與 Transit Gateway 之間建立多條 Site-to-Site VPN，以 ECMP 匯集頻寬
- B. 把 SD-WAN 虛擬設備部署在附加到 Transit Gateway 的 VPC 中，以該 VPC attachment 作為 transport，建立 Transit Gateway Connect attachment，並在設備與 Transit Gateway 之間建立 GRE tunnel 與 BGP session
- C. 在 SD-WAN 虛擬設備所在的 VPC 與 40 個 VPC 之間建立 VPC peering，並在設備上設定 static route
- D. 為每個場站申請 Direct Connect hosted connection，直接連到 Transit Gateway，SD-WAN 只負責場站之間的流量

> [!answer]- 答案：B
> **A ✗** 多條 VPN 加 ECMP 可以提高頻寬，但每條都是 IPsec tunnel，有加密負擔與每 tunnel 的頻寬上限，設定也較多；題目已說明不需要 IPsec。若設備位於地端且必須經 Internet 加密，VPN 才是合適的選擇。
>
> **B ✓** **Transit Gateway Connect** 專為整合 SD-WAN 等第三方虛擬設備設計：以 VPC attachment 或 Direct Connect 作為底層 transport，在其上建立 GRE tunnel，透過 BGP 動態交換路由，每個 Connect peer 的頻寬高於單一 VPN tunnel，也沒有 IPsec 負擔。
>
> **C ✗** VPC peering 不具遞移性，場站流量無法經由設備所在的 VPC 轉送到其他 VPC，40 個 peering 加 static route 也難以維護。
>
> **D ✗** 為 200 個場站各申請 DX 成本高、交期長，也放棄了既有的 SD-WAN 架構。
>
> **考點**：SAP-1.1｜Transit Gateway Connect 整合 SD-WAN｜延伸閱讀：第 41 章、第 8 章

### 第 67 題｜SAP｜單選｜D2 連系統管理員都不能看到的護照資料

一家航空公司要在 EC2 上執行旅客護照影像的辨識與比對程式，護照影像以 KMS 加密後存放在 S3。主管機關要求：解密後的護照資料只能存在於處理程式的隔離環境中，即使擁有該 EC2 instance root 權限的系統管理員，或能登入 instance 的維運人員，也不能讀取解密後的資料或解密金鑰；而且只有經過驗證的特定版本處理程式才能請 KMS 解密。

哪個方案最符合需求？

- A. 以 SSE-KMS 加密 S3 物件，並以 IAM policy 限制只有處理程式的 instance role 能呼叫 `kms:Decrypt`
- B. 把金鑰改存在 AWS CloudHSM，由處理程式透過 CloudHSM client 在 instance 上執行解密
- C. 把處理程式部署在 Dedicated Host 上，確保實體伺服器不與其他 AWS 客戶共用
- D. 在支援的 instance 上啟用 AWS Nitro Enclaves，把處理程式打包為 enclave image 在 enclave 中執行；KMS key policy 以 `kms:RecipientAttestation:ImageSha384` 條件只允許該 enclave image 解密

> [!answer]- 答案：D
> **A ✗** IAM 限制了「誰能解密」，但解密發生在一般的 instance 環境中，擁有 root 權限的管理員可以讀取記憶體或冒用 instance role，無法滿足要求。
>
> **B ✗** CloudHSM 保護的是金鑰，但解密後的資料仍出現在 instance 的記憶體中，管理員一樣可以讀取。
>
> **C ✗** Dedicated Host 隔離的是「其他 AWS 客戶」，不是自己的系統管理員，對這個威脅沒有幫助。
>
> **D ✓** **Nitro Enclaves** 從 EC2 instance 切出隔離的運算環境：沒有持久儲存、沒有互動式登入、沒有對外網路，只能透過 vsock 與 parent instance 溝通，因此即使 parent instance 的 root 也無法讀取 enclave 的記憶體。Enclave 可以產生經簽章的 attestation document，KMS key policy 以 `kms:RecipientAttestation:ImageSha384` 等條件確認只有特定 image 能解密，KMS 回傳的明文也只有 enclave 能讀取。
>
> **考點**：SAP-2.3｜Nitro Enclaves 與 KMS attestation 條件｜延伸閱讀：第 15 章、第 17 章

### 第 68 題｜SAP｜單選｜D3 Aurora 單一 instance 的長時間中斷

一家航空公司的組員排班系統使用 Aurora PostgreSQL，為了省錢只部署了一個 writer instance，沒有任何 Aurora Replica。上週該 instance 所在的硬體故障，Aurora 自動建立新的 instance，排班系統中斷了十幾分鐘，正好碰上颱風造成的大規模航班調度，影響很大。即使資料庫恢復後，部分應用程式仍因為 DNS 快取而連到舊位址，又多花了數分鐘。航空公司要求把資料庫故障造成的中斷縮短到一分鐘以內，並接受適度增加成本。

哪個方案最合適？

- A. 為 cluster 啟用 backtrack，並把自動備份的保留期延長到 35 天
- B. 在不同 AZ 新增一個與 writer 相同 instance class 的 Aurora Replica 並設定最高的 failover 優先順序（tier 0），應用程式使用 cluster endpoint，並改用支援快速 failover 的驅動程式（例如 AWS Advanced JDBC Wrapper 的 failover 功能）以降低 DNS 快取的影響
- C. 在另一個 Region 建立 Aurora cross-Region replica，故障時由值班人員手動升級並修改應用程式設定
- D. 把資料庫遷移到 RDS for PostgreSQL 的 Single-AZ instance 並啟用自動備份

> [!answer]- 答案：B
> **A ✗** Backtrack 用於回復邏輯錯誤（而且只支援 Aurora MySQL），備份保留期也與故障切換時間無關。
>
> **B ✓** 沒有 replica 時，Aurora 必須建立新的 instance 才能恢復，需要數分鐘以上；有 **Aurora Replica** 時，Aurora 直接把 replica 升為 writer，通常在一分鐘內完成。相同的 instance class 確保升級後效能足夠，tier 0 讓它成為優先的 failover 目標；cluster endpoint 會指向新的 writer，搭配感知拓撲的驅動程式可以不等 DNS 更新就連到新 writer。
>
> **C ✗** 跨 Region replica 用於 Region 級災難，手動升級與修改設定需要更長時間，對 AZ 內的硬體故障不是適當的工具，而且 Aurora PostgreSQL 的跨 Region 方案是 Global Database。
>
> **D ✗** Single-AZ RDS 故障時同樣要從備份或新硬體恢復，中斷時間更長。
>
> **考點**：SAP-3.4｜Aurora Replica、failover tier 與快速 failover 驅動程式｜延伸閱讀：第 26 章

### 第 69 題｜SAP｜選兩項｜D4 併購後的應用程式組合合理化

一家跨國人資 SaaS 集團在兩年內併購了三家公司，連同自有系統共有 180 個內部應用程式，分散在四座機房。集團決定 18 個月內關閉被併購公司的三座機房。探索工具與使用紀錄顯示：其中 27 個應用程式過去 90 天沒有任何使用者登入；另有三家被併購公司各自維運的 CRM 系統，功能與集團已經全員授權的商用 SaaS CRM 重疊。遷移團隊人力有限，希望先減少需要遷移的應用程式數量。

哪兩個決策最合適？（選兩項）

- A. 把 180 個應用程式全部先以 rehost 遷移到 EC2，等機房關閉後再逐一評估哪些需要保留
- B. 在遷移前先把每一個應用程式都重構為 serverless 架構，以一次達到最佳的雲端成本
- C. 與 27 個無人使用的應用程式負責人確認、保存必要資料後，將它們 retire，不納入遷移範圍
- D. 把被併購公司的所有系統以 retain 方式留在原機房至少五年，等合約到期再決定
- E. 把三套自建 CRM 的資料遷移到集團已授權的 SaaS CRM，採用 repurchase，並在完成後停用這三套系統

> [!answer]- 答案：C、E
> **A ✗** 不先篩選就全部 rehost，會把無人使用與重複的系統一起搬上雲，浪費遷移人力，也讓雲端成本一開始就灌水。
>
> **B ✗** 全部 refactor 需要大量時間與人力，18 個月內關閉三座機房幾乎不可能；refactor 應該留給業務價值高、確實需要的系統。
>
> **C ✓** 7Rs 中的 **retire** 是成本最低的遷移：沒有使用者的系統直接淘汰，只保留法規需要的資料。事先與負責人確認可以避免誤刪季節性使用的系統。
>
> **D ✗** Retain 適合「有明確理由暫時不能搬」的系統，例如依賴地端設備或即將淘汰；把所有被併購系統都留下，與關閉機房的決策直接衝突。
>
> **E ✓** **Repurchase** 指改用 SaaS 等現成產品取代自建系統；集團已經有授權，合併到同一套 CRM 還能統一流程與資料，並直接減少三個遷移項目。
>
> **考點**：SAP-4.1｜以 retire 與 repurchase 縮小遷移範圍｜延伸閱讀：第 44 章

### 第 70 題｜SAP｜單選｜D1 併購公司使用不同的 IdP

一家電信公司以 IAM Identity Center 管理 Organization 中 150 個帳號的人員存取，identity source 是集團的 Microsoft Entra ID，透過 SCIM 自動同步使用者與群組。集團剛併購一家使用 Okta 的有線電視業者，對方 800 名員工的帳號已全部在 Okta 中，對方的 25 個 AWS 帳號已經移入集團的 Organization。資安部要求所有人員都透過 Identity Center 以 permission set 存取 AWS 帳號，並以單一入口集中管理與稽核。

哪個方案最合適？

- A. 在集團的 Identity Center 中新增 Okta 作為第二個 identity source，讓兩個 IdP 的使用者都能登入
- B. 在被併購公司的 25 個帳號中各自啟用一個 account instance 的 Identity Center，以 Okta 作為 identity source，並在各 instance 中建立 permission set
- C. 維持 Entra ID 作為 Identity Center 唯一的 identity source，把被併購公司的使用者整合進 Entra ID（例如由 Entra ID 與 Okta 建立聯合或遷移帳號），再透過 SCIM 同步到 Identity Center，以群組指派 permission set
- D. 在被併購公司的 25 個帳號中各自建立信任 Okta 的 IAM SAML identity provider 與 IAM role，維持原本的登入方式

> [!answer]- 答案：C
> **A ✗** 一個 Identity Center instance 同一時間只能有一個 identity source，無法同時接兩個外部 IdP。
>
> **B ✗** Account instance 只能用於支援的 AWS 應用程式，不能用來管理 AWS 帳號的存取與 permission set；只有 organization instance 能指派 permission set 給帳號。
>
> **C ✓** 在 Identity Center 只能有一個 identity source 的前提下，正確做法是在 IdP 層整合：讓所有使用者都出現在集團的 Entra ID 中（由 IdP 之間的聯合或帳號遷移完成），再經 SCIM 同步到 Identity Center，以群組集中指派 permission set，稽核也統一在一處。
>
> **D ✗** 每個帳號各自設定 SAML 與 IAM role 可以運作，但存取分散在 25 個帳號中，無法用 permission set 集中管理，違反單一入口與集中稽核的要求。
>
> **考點**：SAP-1.4｜Identity Center 只能有一個 identity source｜延伸閱讀：第 13 章

### 第 71 題｜SAP｜單選｜D2 全球多 Region 的漸進式部署

Atlasform 是一家跨國表單 SaaS，在 12 個 Region 各有 3 個 cell，每個 cell 是一套完整的 ECS 服務與資料庫。過去的 pipeline 在通過 staging 測試後，就同時部署到所有 Region 的所有 cell；上季一次部署讓全球 36 個 cell 同時出現記憶體洩漏，服務中斷 1 小時。工程副總要求新的部署流程要能在問題擴散前自動停止，同時讓一次完整的全球部署仍能在一個工作天內完成。

哪個方案最合適？

- A. 把 pipeline 分成多個 wave：先部署到流量最小 Region 的單一 cell，再擴大到同 Region 其他 cell、少數 Region，最後是其餘 Region；每個 wave 之間設定 bake time 並監控關鍵 CloudWatch alarm，alarm 觸發時自動停止 pipeline 並回滾該 wave
- B. 維持同時部署到所有 Region，但在每個 Region 都改用 blue/green 部署，讓新版本在全部 Region 同時切換，出問題時再一起切回
- C. 在 staging 增加為期一週的負載測試，通過後由變更顧問委員會人工核准，再同時部署到所有 Region
- D. 每次部署前隨機挑選一個 Region 先部署，觀察一週後再部署到其他 Region

> [!answer]- 答案：A
> **A ✓** **Wave-based deployment** 依「先小後大」的順序推出：第一個 wave 只影響一個 cell，若出問題，影響範圍最小；**bake time** 讓延遲出現的問題（例如記憶體洩漏）有時間浮現；alarm 自動停止與回滾讓問題不需要人工判斷就停在早期的 wave。後面的 wave 可以逐步擴大批次，維持在一個工作天內完成全球部署。
>
> **B ✗** Blue/green 讓每個 Region 可以快速回滾，但全球同時切換，問題一樣同時影響所有 Region，blast radius 沒有縮小。
>
> **C ✗** 更長的 staging 測試有幫助，但正式環境的問題不一定能在 staging 重現；人工核准後仍同時部署到所有 Region，沒有解決擴散問題。
>
> **D ✗** 觀察一週太慢，無法在一個工作天內完成部署；隨機挑選 Region 也可能先打到流量最大的 Region。
>
> **考點**：SAP-2.1｜wave 部署、bake time 與 alarm 自動回滾｜延伸閱讀：第 37 章

### 第 72 題｜SAP｜單選｜D3 把手動建立的資源納入 IaC

一家醫療影像 AI 新創過去三年在主控台手動建立了約 400 個 AWS 資源（VPC、security group、IAM role、S3 bucket、RDS、ECS 服務等），沒有任何範本。最近一次誤刪 security group 規則造成服務中斷，事後無人能說清楚原本的設定。CTO 要求把這些既有資源全部納入 CloudFormation 管理，以便追蹤變更與偵測漂移，但不能重新建立資源（RDS 與 S3 中有正式資料），也希望盡量減少手寫範本的工作量。

哪個方案最合適？

- A. 依照現況手寫全新的 CloudFormation 範本建立一套新環境，再把資料遷移到新資源，最後刪除舊資源
- B. 以 AWS Config advanced query 匯出所有資源的設定 JSON，再用自寫的腳本轉換為 CloudFormation 範本並部署
- C. 使用 CloudFormation 的 IaC generator 掃描帳號中的既有資源，選取要管理的資源產生範本，並以產生的範本透過 resource import 建立 stack，之後再啟用 drift detection
- D. 建立一個空的 CloudFormation stack，對它執行 drift detection，讓 CloudFormation 自動找出帳號中所有未受管的資源並加入 stack

> [!answer]- 答案：C
> **A ✗** 重建環境並遷移資料風險高、停機時間長，也違反「不能重新建立資源」的限制。
>
> **B ✗** 自寫轉換腳本工作量大且容易出錯，產生的範本若直接部署會建立新的資源，而不是接管既有資源。
>
> **C ✓** **IaC generator** 會掃描帳號中的資源，讓你挑選要納入的資源（並建議相關聯的資源）後產生範本；以該範本透過 **resource import** 建立 stack，CloudFormation 會接管既有資源而不重建它們。納入 stack 後即可用 drift detection 追蹤手動變更。
>
> **D ✗** Drift detection 只比較「已在 stack 中的資源」與範本的差異，不會發現或接管帳號中未受管的資源。
>
> **考點**：SAP-3.1｜IaC generator 與 resource import 接管既有資源｜延伸閱讀：第 37 章

### 第 73 題｜SAP｜單選｜D4 包裹即時位置的高寫入量

一家航空快遞公司的包裹追蹤系統以 Oracle 資料表記錄每件包裹的最新位置，掃描器與貨車上的 GPS 裝置每秒送出約 3 萬筆位置更新，每筆都會 `UPDATE` 包裹的最新位置並 `INSERT` 一筆歷史紀錄。尖峰時資料列鎖定競爭嚴重，更新延遲到數分鐘，客戶查詢到的位置過時。查詢模式很單純：客戶以包裹編號查詢最新位置（毫秒等級回應），分析團隊每天對歷史軌跡做彙總分析。公司希望重新設計這部分架構，能隨業務成長水平擴展，且盡量使用受管服務。

哪個方案最合適？

- A. 把 Oracle 遷移到最大規格的 Aurora PostgreSQL，增加 5 個 Aurora Replica 分擔查詢，並把歷史資料表依日期分割
- B. 讓 GPS 裝置把每筆位置更新直接寫入 ElastiCache，客戶查詢與歷史分析都從 ElastiCache 讀取
- C. 讓每筆位置更新都寫成一個 S3 物件，客戶查詢時以 Athena 找出該包裹最新的物件
- D. 以 Kinesis Data Streams 接收位置更新（以包裹編號為 partition key），由 Lambda 以條件寫入（只有時間戳較新時才覆寫）把最新位置寫入以包裹編號為 partition key 的 DynamoDB 資料表；同時以 Data Firehose 把原始事件寫入 S3，供 Athena 分析歷史軌跡

> [!answer]- 答案：D
> **A ✗** 換成 Aurora 與增加 replica 只是擴展讀取，問題是同一列的高頻寫入鎖定競爭，單一 writer 的架構依然受限。
>
> **B ✗** 以 ElastiCache 作為唯一儲存，歷史資料的持久性與大量分析都不適合；記憶體容量也難以存放所有歷史軌跡。
>
> **C ✗** S3 加 Athena 適合批次分析，不適合毫秒等級的單筆查詢，也會產生大量小物件。
>
> **D ✓** 把「最新狀態」與「歷史事件」拆開：**Kinesis** 吸收高頻寫入並以包裹編號維持同一包裹的順序；**DynamoDB** 以 key-value 方式儲存最新位置，寫入可以水平擴展、單筆查詢毫秒回應，條件寫入避免較舊的事件覆蓋新位置；**Firehose** 把原始事件批次寫入 S3，讓 Athena 做低成本的歷史分析。
>
> **考點**：SAP-4.3｜以 Kinesis、DynamoDB 與 S3 重新設計高寫入狀態｜延伸閱讀：第 27 章、第 31 章

### 第 74 題｜SAP｜選兩項｜D4 SQL Server 遷移到 RDS 的低停機切換

一家醫療費用審核公司的核心資料庫是地端 SQL Server Standard Edition（4 TB），應用程式大量使用 T-SQL 與 SQL Server Agent job。公司決定遷移到 Amazon RDS for SQL Server 以減少維運，地端到 AWS 有 Direct Connect。切換的停機時間不得超過 1 小時，而且不得修改應用程式。地端資料庫已採用 full recovery model，DBA 可以依需求啟用 MS-CDC。

哪兩個步驟組合最合適？（選兩項）

- A. 以 AWS Application Migration Service 把 SQL Server 伺服器 rehost 到 EC2，再把 EC2 改為 RDS instance
- B. 對地端資料庫執行 native full backup 並上傳到 S3，在 RDS for SQL Server 設定 S3 整合後，以 `rds_restore_database` 還原到 RDS instance
- C. 改用 Aurora PostgreSQL 並啟用 Babelfish，讓應用程式以 SQL Server 協定連線
- D. 以 AWS DataSync 把資料庫的 `.mdf` 與 `.ldf` 檔案直接複製到 RDS instance 的資料目錄
- E. 還原完成後，建立 AWS DMS 的 CDC-only task，從完整備份對應的 LSN 開始，把之後地端的變更持續套用到 RDS；切換時停止應用程式寫入，等 CDC 追上後把連線改到 RDS

> [!answer]- 答案：B、E
> **A ✗** MGN 把伺服器搬到 EC2，但無法把 EC2 轉換成 RDS；RDS 是受管服務，不能從 instance 映像建立。若公司需要作業系統層級的控制，EC2 上的 SQL Server 才是合理目標。
>
> **B ✓** RDS for SQL Server 支援以 S3 中的 **native backup**（`.bak`）還原資料庫，是搬移數 TB 同質資料庫最快、最完整的方式，schema、T-SQL 物件與資料都一起保留。
>
> **C ✗** Babelfish 能理解大部分 T-SQL，但並非完全相容，SQL Server Agent job 也要另外處理，仍有應用程式修改與相容性風險，違反「不得修改應用程式」。
>
> **D ✗** RDS 不提供檔案系統存取，不能直接複製資料庫檔案；DataSync 也不處理執行中資料庫檔案的一致性。
>
> **E ✓** 4 TB 的備份與還原需要數小時，期間地端仍有新的寫入。**DMS CDC** 可以從 SQL Server 交易日誌中的 native start point（LSN）開始讀取變更：DBA 以 `fn_dump_dblog()` 等函式找出完整備份對應的 LSN，建立 CDC-only task 時設為 `CdcStartPosition`（來源需啟用 MS-CDC 或 MS-Replication；使用 native start point 時，要為參與複寫的資料表建立 publication；這段期間的交易日誌備份也要保留），讓 RDS 持續追上；切換時只需等待最後的變更套用完成，停機可控制在 1 小時內。
>
> **考點**：SAP-4.2｜native backup 還原加 DMS CDC 的同質遷移｜延伸閱讀：第 45 章、第 26 章

### 第 75 題｜SAP｜單選｜D3 合作夥伴上傳檔案的惡意程式掃描

一家航空貨運公司讓全球 300 家貨運代理商透過 web 入口把報關文件（PDF、Office 檔、壓縮檔）上傳到 S3 bucket，下游的 Lambda 會自動解析這些文件並寫入報關系統。資安部擔心代理商的電腦被入侵後上傳含惡意程式的檔案，要求：每個新上傳的物件都要經過惡意程式掃描，只有確認無威脅的物件才能被下游讀取；公司不想自行維運防毒伺服器或更新病毒碼。

哪個方案最合適？

- A. 在帳號中啟用 Amazon Inspector，讓它持續掃描 S3 bucket 中的物件是否含有惡意程式與漏洞
- B. 為該 bucket 啟用 GuardDuty Malware Protection for S3，並在 protection plan 中啟用掃描結果的物件標籤（tagging）；在 bucket policy 中拒絕讀取標籤不是 `NO_THREATS_FOUND` 的物件，並讓下游依掃描結果事件觸發處理
- C. 為該 bucket 啟用 Amazon Macie 的 sensitive data discovery job，把含有惡意內容的物件標記出來
- D. 以 S3 event notification 觸發一組安裝防毒軟體的 EC2 Auto Scaling group，由 instance 下載並掃描每個物件，再把結果寫入 DynamoDB

> [!answer]- 答案：B
> **A ✗** Inspector 掃描的是 EC2、container image 與 Lambda 函式的軟體漏洞與程式碼問題，不掃描 S3 物件內容是否含有惡意程式。
>
> **B ✓** **GuardDuty Malware Protection for S3** 對指定 bucket 中新上傳的物件自動進行惡意程式掃描，由 AWS 維運掃描引擎；啟用 protection plan 的 tagging 選項後，掃描結果會寫成物件標籤 `GuardDutyMalwareScanStatus`（例如 `NO_THREATS_FOUND`、`THREATS_FOUND`），掃描完成也會發送 EventBridge 事件。tagging 是要另外啟用的選項，GuardDuty 使用的 IAM role 也需要 `s3:PutObjectTagging` 權限。剛上傳、尚未掃描完的物件還沒有標籤，以 `StringNotEquals` 拒絕「標籤不是 `NO_THREATS_FOUND`」的寫法也會一併擋住它們。Bucket policy 以標籤條件阻擋未通過掃描的物件被讀取，下游則以掃描完成事件觸發，避免讀到尚未掃描的檔案。
>
> **C ✗** Macie 辨識的是個資等敏感資料，不是惡意程式。
>
> **D ✗** 自建掃描機群可行，但要維運 instance、防毒軟體與病毒碼更新，正是公司不想做的事。若需要使用特定廠商的掃描引擎或掃描 AWS 不支援的格式，才考慮自建或使用第三方方案。
>
> **考點**：SAP-3.2｜GuardDuty Malware Protection for S3 與標籤式存取控制｜延伸閱讀：第 16 章

## 答案速查與 Domain 分析

| 題號 | 答案 | Domain | Task | 相關章節 |
|---|---|---|---|---|
| 1 | B | D1 | SAP-1.1 | 第 8 章 |
| 2 | C | D2 | SAP-2.2 | 第 26 章、第 34 章 |
| 3 | A | D3 | SAP-3.2 | 第 16 章 |
| 4 | A、D | D4 | SAP-4.2、SAP-4.1 | 第 44 章、第 45 章 |
| 5 | D | D1 | SAP-1.3 | 第 35 章、第 49 章 |
| 6 | B | D2 | SAP-2.1 | 第 37 章、第 40 章 |
| 7 | C | D1 | SAP-1.2 | 第 13 章 |
| 8 | A | D3 | SAP-3.3 | 第 30 章 |
| 9 | B、E | D2 | SAP-2.3 | 第 15 章 |
| 10 | D | D4 | SAP-4.1 | 第 44 章 |
| 11 | C | D1 | SAP-1.4 | 第 40 章 |
| 12 | B | D3 | SAP-3.1 | 第 37 章、第 38 章 |
| 13 | D | D2 | SAP-2.5 | 第 31 章 |
| 14 | A | D1 | SAP-1.5 | 第 39 章、第 43 章 |
| 15 | A、C | D2 | SAP-2.4 | 第 34 章、第 35 章 |
| 16 | C | D3 | SAP-3.4 | 第 19 章、第 26 章 |
| 17 | B | D4 | SAP-4.3 | 第 18 章、第 28 章 |
| 18 | B、D | D1 | SAP-1.1、SAP-1.2 | 第 7 章 |
| 19 | A | D2 | SAP-2.6 | 第 39 章 |
| 20 | C | D3 | SAP-3.5 | 第 23 章 |
| 21 | B | D1 | SAP-1.3 | 第 31 章 |
| 22 | D | D2 | SAP-2.2 | 第 34 章 |
| 23 | A、E | D3 | SAP-3.2 | 第 14 章、第 17 章 |
| 24 | A | D4 | SAP-4.4 | 第 33 章、第 21 章 |
| 25 | D | D1 | SAP-1.2 | 第 13 章 |
| 26 | B | D2 | SAP-2.1 | 第 37 章、第 19 章 |
| 27 | C | D3 | SAP-3.3 | 第 11 章 |
| 28 | A | D1 | SAP-1.4 | 第 14 章、第 40 章 |
| 29 | A | D2 | SAP-2.3 | 第 15 章 |
| 30 | D | D3 | SAP-3.1 | 第 38 章 |
| 31 | C | D2 | SAP-2.5 | 第 24 章 |
| 32 | B | D4 | SAP-4.2 | 第 45 章 |
| 33 | A | D1 | SAP-1.1、SAP-1.2 | 第 6 章、第 41 章 |
| 34 | B、C | D3 | SAP-3.4 | 第 32 章、第 19 章 |
| 35 | D | D2 | SAP-2.4 | 第 10 章、第 35 章 |
| 36 | B | D1 | SAP-1.5 | 第 39 章、第 43 章 |
| 37 | A、E | D4 | SAP-4.3、SAP-4.4 | 第 32 章 |
| 38 | C | D2 | SAP-2.6 | 第 30 章、第 17 章 |
| 39 | D | D3 | SAP-3.5 | 第 6 章、第 39 章 |
| 40 | C、E | D1 | SAP-1.3 | 第 27 章、第 42 章 |
| 41 | A | D2 | SAP-2.2 | 第 34 章、第 43 章 |
| 42 | B | D3 | SAP-3.2 | 第 15 章、第 19 章 |
| 43 | C | D4 | SAP-4.4 | 第 46 章、第 47 章 |
| 44 | D | D1 | SAP-1.2 | 第 16 章 |
| 45 | B、C、F | D2 | SAP-2.1 | 第 37 章 |
| 46 | A | D4 | SAP-4.3 | 第 30 章 |
| 47 | D | D1 | SAP-1.4、SAP-1.2 | 第 14 章、第 40 章 |
| 48 | B | D2 | SAP-2.5 | 第 19 章 |
| 49 | A | D3 | SAP-3.4 | 第 17 章 |
| 50 | B | D4 | SAP-4.1 | 第 44 章 |
| 51 | C | D1 | SAP-1.1 | 第 41 章 |
| 52 | D | D2 | SAP-2.3 | 第 13 章、第 49 章 |
| 53 | C | D3 | SAP-3.1 | 第 36 章 |
| 54 | C | D2 | SAP-2.4 | 第 20 章、第 32 章 |
| 55 | A | D1 | SAP-1.3 | 第 31 章 |
| 56 | D | D4 | SAP-4.2 | 第 25 章、第 45 章 |
| 57 | B | D2 | SAP-2.6 | 第 23 章 |
| 58 | A | D3 | SAP-3.2 | 第 16 章、第 36 章 |
| 59 | C | D1 | SAP-1.5 | 第 39 章 |
| 60 | A、C、F | D2 | SAP-2.2 | 第 34 章 |
| 61 | D | D3 | SAP-3.3 | 第 11 章 |
| 62 | B、D | D4 | SAP-4.4 | 第 46 章 |
| 63 | A、D | D1 | SAP-1.2、SAP-1.4 | 第 14 章、第 6 章 |
| 64 | A | D2 | SAP-2.5 | 第 17 章 |
| 65 | C | D3 | SAP-3.5 | 第 19 章、第 39 章 |
| 66 | B | D1 | SAP-1.1 | 第 41 章、第 8 章 |
| 67 | D | D2 | SAP-2.3 | 第 15 章、第 17 章 |
| 68 | B | D3 | SAP-3.4 | 第 26 章 |
| 69 | C、E | D4 | SAP-4.1 | 第 44 章 |
| 70 | C | D1 | SAP-1.4 | 第 13 章 |
| 71 | A | D2 | SAP-2.1 | 第 37 章 |
| 72 | C | D3 | SAP-3.1 | 第 37 章 |
| 73 | D | D4 | SAP-4.3 | 第 27 章、第 31 章 |
| 74 | B、E | D4 | SAP-4.2 | 第 45 章、第 26 章 |
| 75 | B | D3 | SAP-3.2 | 第 16 章 |

### 各 Domain 題數

| Domain | 名稱 | 題數 | 題號 |
|---|---|---|---|
| D1 | Design Solutions for Organizational Complexity | 20 | 1、5、7、11、14、18、21、25、28、33、36、40、44、47、51、55、59、63、66、70 |
| D2 | Design for New Solutions | 22 | 2、6、9、13、15、19、22、26、29、31、35、38、41、45、48、52、54、57、60、64、67、71 |
| D3 | Continuous Improvement for Existing Solutions | 19 | 3、8、12、16、20、23、27、30、34、39、42、49、53、58、61、65、68、72、75 |
| D4 | Accelerate Workload Migration and Modernization | 14 | 4、10、17、24、32、37、43、46、50、56、62、69、73、74 |

題型：單選 61 題、選兩項 12 題（4、9、15、18、23、34、37、40、62、63、69、74）、選三項 2 題（45、60）。

### 錯題對應複習章節

- **D1 錯 4 題以上**：網路題（1、18、33、51、66）回到第 7、8、41 章，重點是 SiteLink、PrivateLink、DNS Firewall、Cloud WAN 與 Transit Gateway Connect 各自解決什麼問題；身份與治理題（11、28、47、63、70）回到第 13、14、40 章，特別是 delegated administrator、proactive controls、RCP 與 SCP 的差異，以及 Identity Center 只能有一個 identity source；成本可視化題（14、36、59）回到第 39、43 章。
- **D2 錯 5 題以上**：DR 題（2、22、41、60）回到第 34 章，把 backup & restore、pilot light、warm standby、multi-site 的 RPO／RTO 與成本差異整理成一張表；部署題（6、26、45、71）回到第 37 章；安全需求題（9、29、52、67）回到第 15 章與第 13 章，分清 XKS、CloudHSM、BYOK 與 Nitro Enclaves 的信任邊界。
- **D3 錯 4 題以上**：營運卓越題（12、30、53、72）回到第 36–38 章；安全改善題（3、23、42、58、75）回到第 16 章，記住 Macie、GuardDuty、Inspector、Security Lake 各看什麼資料；可靠性與效能題（16、34、49、68、8、27、61）回到第 11、26、30、32 章；成本題（20、39、65）回到第 23、39 章。
- **D4 錯 3 題以上**：先回到第 44 章確認 7Rs 與 wave 規劃（10、50、69），再到第 45 章複習 MGN、DMS（含 Schema Conversion 與 CDC）、DataSync 的分工（4、32、56、74），最後以第 46 章複習 strangler fig、stateless 化與事件驅動的現代化模式（17、24、37、43、46、62、73）。
- **選兩項／選三項錯誤偏多**：通常是只看到「技術上可行」就選，沒有逐一核對題目的每個限制。重做時，先把題幹的限制條列出來，再檢查每個選項違反了哪一條。
