---
title: SAA 模擬考 3
exam: SAA-C03
---

# SAA 模擬考 3

> [!abstract] 作答說明
> **題數與時間**：65 題，建議作答時間 130 分鐘（與真實 SAA-C03 相同），請一次坐完、全程計時，中途不查資料。
> **難度定位**：這是考前最後一回，整體略難於真實考試，約 40% 題目需要辨認一個細微的機制差異（例如 execution role 與 task role、Lambda 在 VPC 內沒有 public IP、Kinesis partition key 與順序性）。
> **及格參考**：真實考試以 100–1000 的 scaled score 計分、720 分及格，沒有固定的「答對幾題」換算。本回建議以答對 47 題（約 72%）作為及格參考；若答對 52 題以上，代表已具備穩定通過的實力。
> **作答方式**：每題先在紙上寫下答案，全部作答完畢再展開 `答案` 區塊對答案。「選兩項」題必須兩個都對才算得分。
> **錯題記錄**：對完答案後，把錯題的題號、你選的答案、錯誤原因（概念不懂／讀題漏看限制／兩個選項之間猶豫）記在一張表上，再依文末「答案速查與 Domain 分析」回到對應章節複習。猶豫後才答對的題目也要記下來。
> **情境說明**：本回題目以物流運輸、政府與公共服務、IoT 與智慧城市、旅館餐飲、生技研究等產業為背景，所有公司與情境皆為虛構。

## 題目

### 第 1 題｜SAA｜單選｜D2 承接外部 webhook 尖峰

一家貨運代理公司接收 40 家合作物流商透過 HTTPS webhook 回傳的貨件狀態事件。平常每秒約 200 個事件，但颱風或節日前後，合作商常一次補傳積壓資料，流量瞬間增加 20 倍。後端的訂單資料庫無法隨流量擴展，過去尖峰時曾因連線數爆滿而拒絕寫入，導致部分事件遺失；合作商不會重送失敗的 webhook。公司要求事件一筆都不能遺失，並希望營運負擔最低。

哪一種架構最符合需求？

- A. 以 API Gateway 接收 webhook，同步呼叫 Lambda 寫入資料庫，並把 Lambda 的 reserved concurrency 設為資料庫可承受的上限
- B. 以 Application Load Balancer 搭配 EC2 Auto Scaling group 接收 webhook，依 CPU 使用率擴展 instance，每台 instance 直接寫入資料庫
- C. 以 API Gateway 直接整合 SQS 把事件寫入 queue，再由 Lambda 從 queue 批次讀取寫入資料庫，並在 event source mapping 設定 maximum concurrency
- D. 以 API Gateway 接收 webhook，並在 stage 設定 throttling 上限，超過資料庫容量的請求回傳 429，避免資料庫過載

> [!answer]- 答案：C
> **A ✗** 限制 reserved concurrency 確實能保護資料庫，但 API Gateway 是同步呼叫 Lambda，超過上限的請求會被 throttle 並把錯誤回給合作商；合作商不重送，事件就遺失了。限流本身不等於緩衝。
>
> **B ✗** EC2 會隨流量擴展，但每台 instance 都直接寫資料庫，instance 越多連線越多，正好把瓶頸推給無法擴展的資料庫，與過去出事的模式相同；而且維護 EC2 機群的營運負擔較高。
>
> **C ✓** SQS 是持久的緩衝區：API Gateway 透過 AWS service integration 直接呼叫 `SendMessage`，請求一進來就落地在 queue，回應合作商 200。後端 Lambda 以 event source mapping 讀取，`maximum concurrency` 限制同時執行的函式數，讓寫入速度維持在資料庫可承受的範圍，尖峰的積壓留在 queue 中慢慢消化（預設保留 4 天，最長 14 天）。全部是受管服務，營運負擔最低。
>
> **D ✗** Throttling 能保護後端，但被拒絕的請求就是遺失的事件。只有在呼叫端「會依 429 重試」時，throttling 才是合理的保護機制。
>
> **考點**：SAA-2.1｜用 queue 吸收尖峰、以 consumer 並行度保護下游｜延伸閱讀：第 32 章、第 20 章

### 第 2 題｜SAA｜單選｜D1 同帳號 bucket policy 與 KMS key

一家連鎖旅館把住客電子發票存放在 S3 bucket，物件使用一把 customer managed KMS key 做 SSE-KMS 加密。這把 key 的 key policy 只有預設的一條敘述：允許本帳號的 root principal 執行 `kms:*`（也就是讓 IAM policy 可以授權使用這把 key）。財務團隊在同一個帳號建立了 Lambda 函式，其 execution role `FinanceReportRole` 沒有附加任何與 S3 或 KMS 相關的 identity policy；bucket policy 則明確允許這個 role 的 ARN 執行 `s3:GetObject`。函式讀取發票時收到 `AccessDenied`。

以最小權限原則修正，應該怎麼做？

- A. 在 `FinanceReportRole` 加上 identity policy，允許對該 bucket 執行 `s3:GetObject`
- B. 在 `FinanceReportRole` 加上 identity policy，允許對這把 KMS key 的 ARN 執行 `kms:Decrypt`
- C. 在 bucket policy 中再加一條敘述，允許 `FinanceReportRole` 對這把 key 執行 `kms:Decrypt`
- D. 把 bucket 的預設加密改為 SSE-S3，並重新上傳所有既有發票

> [!answer]- 答案：B
> **A ✗** 在同一個帳號內，resource-based policy（bucket policy）只要明確允許某個 principal，就足以授權，不需要 identity policy 再允許一次。S3 這一段已經通了，問題不在這裡。
>
> **B ✓** 讀取 SSE-KMS 物件時，S3 會代替呼叫者向 KMS 請求解密，呼叫者本身必須擁有 `kms:Decrypt`。這把 key 的 key policy 只授權給帳號 root，意思是「交給 IAM policy 決定」，而 role 沒有任何 KMS 權限，所以失敗。只對這把 key 的 ARN 授權 `kms:Decrypt`，是最小權限的修法。
>
> **C ✗** Bucket policy 只能管 S3 的動作，不能授權 KMS 的 API。KMS 的授權只能來自 key policy、grant，或（在 key policy 允許時的）IAM policy。若想改用 key policy 授權，要改的是 key policy 本身。
>
> **D ✗** 改成 SSE-S3 雖然能讓讀取成功，但放棄了 customer managed key 帶來的存取控制與稽核能力，屬於降低安全性來繞過問題，也需要重新處理既有物件。
>
> **考點**：SAA-1.1、SAA-1.3｜同帳號 resource policy 足以授權 S3，但 SSE-KMS 還需要 KMS 權限｜延伸閱讀：第 12 章、第 15 章

### 第 3 題｜SAA｜單選｜D3 感測資料的順序與多個 consumer

一座城市在 8,000 個路口安裝交通流量感測器，每個感測器每秒送出一筆讀數。號誌控制系統必須依「同一路口」的時間順序處理讀數，不同路口之間可以平行處理；另外有一個歸檔服務要讀取完整的資料流存入 data lake。兩個 consumer 都必須讀到每一筆資料，而且彼此不能搶讀取頻寬，避免歸檔服務拖慢號誌控制。

哪一種設計最合適？

- A. 使用 SQS standard queue，兩個 consumer 各自 long polling 同一個 queue，並在訊息中帶入時間戳記由 consumer 排序
- B. 使用 SQS FIFO queue，以路口 ID 作為 message group ID，兩個 consumer 從同一個 queue 讀取
- C. 使用 Kinesis Data Streams，以隨機值作為 partition key 讓資料平均分散到各 shard，兩個 consumer 都使用 enhanced fan-out
- D. 使用 Kinesis Data Streams，以路口 ID 作為 partition key，兩個 consumer 都註冊為 enhanced fan-out consumer

> [!answer]- 答案：D
> **A ✗** SQS 的一則訊息被某個 consumer 處理並刪除後，另一個 consumer 就讀不到，無法做到「兩個 consumer 都讀到每一筆」；standard queue 也不保證順序。
>
> **B ✗** FIFO 加上 message group ID 可以保證同一路口的順序，但 queue 的語意仍是「一則訊息只交給一個 consumer」，兩個服務會互相分走訊息。若要用 SQS，必須先用 SNS FIFO topic 扇出到兩個 FIFO queue。
>
> **C ✗** 隨機 partition key 會把同一路口的讀數散到不同 shard，順序只在單一 shard 內成立，跨 shard 就無法保證同一路口的時間順序。
>
> **D ✓** Kinesis 會把相同 partition key 的資料送到同一個 shard，shard 內依寫入順序保存，因此同一路口有序、不同路口分散到多個 shard 平行處理。資料流可以被多個 consumer 重複讀取；enhanced fan-out 讓每個註冊的 consumer 在每個 shard 各自獲得專屬的讀取頻寬（每 shard 2 MB/s），歸檔服務不會拖慢號誌控制。
>
> **考點**：SAA-3.5、SAA-2.1｜partition key 決定順序範圍，enhanced fan-out 隔離 consumer｜延伸閱讀：第 31 章

### 第 4 題｜SAA｜單選｜D4 SSE-KMS 的請求成本

一家宅配公司每天把約 5,000 萬張簽收照片上傳到 S3，法遵要求必須使用公司自管的 customer managed KMS key 加密，並保留 key 使用紀錄。每張照片都很小，帳單顯示 KMS 請求費用已經超過 S3 儲存費用，尖峰時段也偶爾出現 KMS 節流錯誤。公司希望在不改變加密方式要求的前提下，以最低成本解決。

應該怎麼做？

- A. 在 bucket 的預設加密設定啟用 S3 Bucket Keys
- B. 改用 SSE-S3 加密，並以 CloudTrail 記錄 S3 的資料事件作為使用紀錄
- C. 改用 DSSE-KMS（雙層伺服器端加密），讓每個物件的加密更完整
- D. 向 AWS 申請提高 KMS 每秒請求數的 quota

> [!answer]- 答案：A
> **A ✓** 啟用 S3 Bucket Keys 後，S3 會向 KMS 取得一把 bucket 層級、短期使用的 key，在本地為物件產生 data key，不必每個物件都呼叫 KMS。KMS 請求量可大幅下降，費用與節流同時改善，而且仍然使用同一把 customer managed key，CloudTrail 仍有 key 使用紀錄。
>
> **B ✗** SSE-S3 由 S3 自管金鑰，不符合「必須使用 customer managed KMS key」的要求。
>
> **C ✗** DSSE-KMS 是兩層加密，用於特定法規要求雙層加密的情境，KMS 相關成本只會更高，不會降低。
>
> **D ✗** 提高 quota 可以處理節流，但每個物件仍要呼叫 KMS，請求費用完全沒有下降。若問題只有節流、成本不是考量，提高 quota 才是合理選項。
>
> **考點**：SAA-4.1、SAA-1.3｜S3 Bucket Keys 降低 SSE-KMS 請求成本｜延伸閱讀：第 15 章、第 22 章

### 第 5 題｜SAA｜選兩項｜D1 VPC 內 Lambda 呼叫外部 API

一個智慧城市專案的 Lambda 函式需要讀取位於 private subnet 的 RDS 資料庫，同時呼叫外部的氣象資料 API。工程師把函式連接到 VPC 時，特意選了兩個 public subnet（route table 有指向 Internet Gateway 的 `0.0.0.0/0`），認為這樣就能同時連到資料庫與 Internet。結果函式能查詢資料庫，但呼叫氣象 API 一律逾時。函式的 security group 使用預設的出站規則（允許所有出站）。

哪兩個步驟組合起來可以修正問題，同時不讓資料庫暴露於 Internet？（選兩項）

- A. 把 Lambda 函式改為連接到 private subnet
- B. 為 Lambda 在每個 subnet 建立的 network interface 綁定 Elastic IP
- C. 在函式的 security group 新增允許 TCP 443 出站到 `0.0.0.0/0` 的規則
- D. 在 public subnet 建立 NAT Gateway，並讓函式所在 private subnet 的 `0.0.0.0/0` route 指向它
- E. 建立一個指向氣象 API 網域的 interface VPC endpoint

> [!answer]- 答案：A、D
> **A ✓** 連接到 VPC 的 Lambda 使用 VPC 內的 network interface，這些 interface 不會取得 public IP，即使放在 public subnet，流量也無法直接經 IGW 上網。正確做法是放在 private subnet，對外流量交給 NAT。
>
> **B ✗** Lambda 的 VPC network interface 由 Lambda 服務管理，不是讓使用者自行綁 Elastic IP 的設計；這種手動修補也不是受支援的架構。
>
> **C ✗** 預設 security group 已允許所有出站流量，問題不在 security group，而在路由與 public IP。
>
> **D ✓** NAT Gateway 放在有 IGW route 的 public subnet、綁定 Elastic IP，private subnet 的 default route 指向它，Lambda 就能主動連出，而 Internet 無法主動連入。與 A 組合後，資料庫仍留在 private subnet。若要高可用，每個 AZ 應各有一台 NAT Gateway。
>
> **E ✗** Interface VPC endpoint 是透過 PrivateLink 存取 AWS 服務或有提供 endpoint service 的服務，不能指向任意的外部網域。
>
> **考點**：SAA-1.2、SAA-3.4｜VPC 內 Lambda 沒有 public IP，連外需要 private subnet + NAT｜延伸閱讀：第 19 章、第 5 章

### 第 6 題｜SAA｜單選｜D2 單一資料庫的 AZ 故障

一家生技公司的實驗室資訊管理系統（LIMS）使用單一 RDS for MySQL instance。上個月該 AZ 發生網路事件，系統停擺三小時。公司要求：AZ 故障時資料庫要在幾分鐘內自動恢復服務、已提交的交易不得遺失，而且應用程式不需要修改連線設定。

哪一種做法最合適？

- A. 在另一個 AZ 建立 read replica，事故發生時由值班人員手動 promote，並修改應用程式的連線字串
- B. 把 instance 修改為 Multi-AZ deployment
- C. 每小時建立一次 snapshot 並複製到另一個 AZ，事故發生時從最新的 snapshot 還原
- D. 啟用 automated backups，事故發生時用 point-in-time restore 在另一個 AZ 還原新 instance

> [!answer]- 答案：B
> **A ✗** Read replica 是非同步複寫，promote 時可能遺失最後一批交易；需要人工 promote，promote 後的 endpoint 也不同，應用程式必須改連線設定，三點都不符合。
>
> **B ✓** Multi-AZ deployment 在另一個 AZ 維護同步複寫的 standby。主節點或 AZ 故障時，RDS 自動 failover，並把同一個 DNS endpoint 指向新的主節點，通常在一到兩分鐘內完成。同步複寫確保已提交的交易不會遺失，應用程式只需重新連線。
>
> **C ✗** RDS 的 snapshot 是 Regional 的，本來就不綁 AZ，不需要「複製到另一個 AZ」；更關鍵的是每小時一次代表最多遺失一小時資料，還原也需要人工與較長時間。
>
> **D ✗** Point-in-time restore 可以把資料恢復到約五分鐘前，但會建立一個新的 instance 與新的 endpoint，耗時且需要人工操作，不符合「幾分鐘內自動恢復」與「不改連線設定」。
>
> **考點**：SAA-2.2｜Multi-AZ 同步 standby 與自動 failover｜延伸閱讀：第 26 章、第 34 章

### 第 7 題｜SAA｜單選｜D1 找出 bucket 中的個資

一家國際連鎖旅館有 300 多個 S3 bucket。稽核發現櫃台的匯出腳本曾把含有住客護照號碼與信用卡號的 CSV 與 Excel 報表，誤存到一般用途的 bucket。資安團隊要求持續、自動找出哪些 bucket 含有這類敏感資料，並在發現時通知團隊，希望營運負擔最低。

應該使用哪一項服務？

- A. 啟用 GuardDuty 的 S3 Protection，針對異常的 S3 存取產生 findings
- B. 部署 AWS Config managed rule，檢查每個 bucket 是否禁止公開讀取
- C. 啟用 Amazon Macie 的 automated sensitive data discovery，並把 findings 透過 EventBridge 通知團隊
- D. 每週用 Athena 對所有 bucket 執行含正規表示式的查詢，找出符合護照號碼格式的資料列

> [!answer]- 答案：C
> **A ✗** GuardDuty S3 Protection 分析的是 CloudTrail 的 S3 資料事件，偵測可疑的存取行為（例如異常 IP 大量下載），不會檢查物件內容是否含有個資。
>
> **B ✗** Config rule 檢查的是 bucket 的設定（是否公開、是否加密），無法得知物件內容是什麼。
>
> **C ✓** Macie 使用受管的資料識別器（例如護照號碼、信用卡號）掃描 S3 物件內容；automated sensitive data discovery 會持續抽樣評估帳號內的 bucket，標示哪些 bucket 可能含有敏感資料。Findings 會送到 EventBridge，可以接 SNS 通知，完全不需要自己寫掃描程式。
>
> **D ✗** Athena 需要先為每種檔案格式定義 table，Excel 檔案也不適合直接查詢；300 多個 bucket 的維護與掃描費用都很高，而且仍要自己維護偵測規則。
>
> **考點**：SAA-1.3｜Macie 負責 S3 敏感資料探索與分類｜延伸閱讀：第 16 章

### 第 8 題｜SAA｜單選｜D3 CPU 密集的 Lambda 太慢

一個市政府的申請案系統使用 Lambda 把使用者上傳的表單轉成 PDF。函式的記憶體設定是預設的 128 MB，實際只用到 90 MB，但每次轉檔要 40 秒，民眾抱怨等太久。CloudWatch 顯示沒有 cold start 問題，函式執行期間也沒有等待任何外部服務，時間幾乎都花在計算。團隊希望用最少的修改縮短處理時間。

應該怎麼做？

- A. 提高函式的記憶體設定，例如調到 2,048 MB 後再觀察執行時間
- B. 為函式設定 provisioned concurrency
- C. 把函式的 timeout 從 60 秒提高到 15 分鐘
- D. 把函式的 ephemeral storage（`/tmp`）從 512 MB 提高到 10,240 MB

> [!answer]- 答案：A
> **A ✓** Lambda 沒有獨立的 CPU 設定，CPU 能力會與記憶體設定成比例分配；記憶體越大，分到的 vCPU 越多（最高 10,240 MB 時約 6 個 vCPU）。CPU 密集的工作提高記憶體後通常會明顯變快，因為按「記憶體 × 執行時間」計費，執行時間縮短後總費用不一定增加。
>
> **B ✗** Provisioned concurrency 讓執行環境預先初始化，只能消除 cold start；題目已說明沒有 cold start 問題。
>
> **C ✗** 提高 timeout 只是允許函式跑更久，不會讓它跑得更快。
>
> **D ✗** `/tmp` 空間影響的是能暫存多大的檔案，與運算速度無關；題目的瓶頸是 CPU。
>
> **考點**：SAA-3.2｜Lambda 的 CPU 隨記憶體設定等比例分配｜延伸閱讀：第 19 章

### 第 9 題｜SAA｜單選｜D2 長短步驟混合的檢體流程

一家基因定序公司的檢體處理流程有四個步驟：驗證檢體資料（Lambda，數秒）、序列比對（AWS Batch job，約 3 小時）、品質檢查（Lambda，數十秒）、通知研究人員。目前由一台 EC2 上的 cron 腳本串接，腳本出錯時常常沒人發現。公司希望每一筆檢體都能看到目前執行到哪一步、暫時性錯誤自動以 backoff 重試、任何步驟失敗都要通知研究人員，並且營運負擔最低。

哪一種做法最合適？

- A. 使用 Step Functions Express workflow 串接四個步驟，並以 Retry 與 Catch 處理錯誤
- B. 每個步驟之間各放一個 SQS queue，每個步驟完成後把訊息送往下一個 queue，失敗的訊息進入 DLQ
- C. 寫一個協調用的 Lambda 函式，依序呼叫各步驟，並輪詢 Batch job 狀態直到完成
- D. 使用 Step Functions Standard workflow，以 `.sync` 整合模式提交 Batch job 並等待完成，各步驟設定 Retry 與 Catch，Catch 分支發送 SNS 通知

> [!answer]- 答案：D
> **A ✗** Express workflow 單次執行最長 5 分鐘，適合高頻、短時間的事件處理，無法等待 3 小時的 Batch job。
>
> **B ✗** 以多個 queue 串接可以解耦，但沒有「每一筆檢體走到哪一步」的集中視圖，重試、錯誤分支與通知都要自己在每個步驟實作，營運負擔較高。
>
> **C ✗** Lambda 單次最長執行 15 分鐘，無法在一次呼叫中等待 3 小時的 Batch job；把協調邏輯寫在程式中，也要自己處理狀態保存與重試。
>
> **D ✓** Standard workflow 單次執行最長一年，每次執行都有可視化的執行歷程。`.sync` 整合讓 Step Functions 提交 Batch job 後等到 job 完成才進入下一步，不必自己輪詢；Retry 可設定間隔與 backoff rate，Catch 把失敗導向通知步驟。這是最少自訂程式的做法。
>
> **考點**：SAA-2.1｜Standard vs Express workflow 與 `.sync` 服務整合｜延伸閱讀：第 33 章

### 第 10 題｜SAA｜單選｜D1 IoT 裝置上傳大型影像

一座城市部署了 3,000 台路邊停車攝影機，每台攝影機都已在 AWS IoT Core 註冊並使用各自的 X.509 憑證連線。攝影機需要把 2–5 MB 的違停照片上傳到 S3，照片超過 MQTT 訊息大小上限，無法直接經 MQTT 傳送。目前韌體內寫死一組所有攝影機共用的 IAM user access key。資安團隊要求移除長期憑證，並讓每台攝影機只能寫入自己的 S3 prefix。

最安全的做法是什麼？

- A. 為每台攝影機建立一個 IAM user 與各自的 access key，並以 IAM policy 限制只能寫入對應的 prefix
- B. 使用 AWS IoT Core credential provider：建立 role alias 指向一個 IAM role，攝影機以既有的 X.509 憑證換取臨時憑證，並在 role 的 policy 中以 thing name 變數限制 prefix
- C. 建立 Cognito identity pool 並啟用未驗證身份（unauthenticated identities），讓攝影機取得臨時憑證後上傳
- D. 把照片切成多個小於 MQTT 上限的片段，透過 IoT Core rule 寫入 S3，再由 Lambda 組合成完整照片

> [!answer]- 答案：B
> **A ✗** 每台裝置一組 IAM user access key 仍然是長期憑證，3,000 組金鑰的輪替與外洩風險很高，違反「移除長期憑證」的要求。
>
> **B ✓** IoT Core credential provider 讓已用 X.509 憑證驗證的裝置，透過 role alias 換取指定 IAM role 的臨時憑證，憑證會自動過期。Role 的 policy 可以使用 `credentials-iot:ThingName` 這類 policy 變數，讓每台攝影機只能寫入以自己 thing name 命名的 prefix（裝置向 credential provider 請求憑證時要在 `x-amzn-iot-thingname` header 帶入 thing name，且該 thing 必須與憑證關聯，否則請求會被拒絕）。裝置不保存任何長期 AWS 金鑰。
>
> **C ✗** 未驗證身份代表任何拿到 identity pool ID 的人都能取得臨時憑證，無法確認是哪台攝影機，也無法依裝置限制 prefix，安全性更差。
>
> **D ✗** 切片再組合可以繞過訊息大小限制，但大幅增加韌體與後端的複雜度、MQTT 訊息費用與失敗處理難度，而且沒有回答「如何安全取得 S3 存取權」這個核心問題。
>
> **考點**：SAA-1.1｜IoT 裝置以 X.509 憑證換取臨時 IAM 憑證｜延伸閱讀：第 13 章、第 31 章

### 第 11 題｜SAA｜單選｜D4 只在上班時間使用的環境

一個政府機關有 40 台開發與測試用 EC2 instance，全部以 On-Demand 方式全天候運行。這些環境只在週一到週五 8:00–18:00 使用，每週約 50 小時；開發人員會在 instance 的 EBS volume 上保留工作狀態，上班時間內不能被中斷。財務單位要求以最低成本運行這批環境。

哪一種做法最划算？

- A. 為這 40 台 instance 購買 1 年期、全額預付的 Standard Reserved Instances
- B. 依目前 24 小時的用量購買 1 年期 Compute Savings Plans
- C. 使用 Instance Scheduler on AWS（或 EventBridge Scheduler 搭配 Systems Manager Automation），在下班時間與週末自動停止 instance、上班前自動啟動
- D. 把這些環境改為 Spot Instances，並在 instance 被中斷時自動重新啟動

> [!answer]- 答案：C
> **A ✗** Reserved Instances 是為「全天候持續運行」設計的折扣：無論 instance 是否開機都要付費。這批環境一週只用 50 小時（約 30% 的時間），停機就能省下約 70% 的運算費用，比 RI 的折扣更多。
>
> **B ✗** Savings Plans 也是承諾每小時的固定花費，按 24 小時用量承諾，等於在不使用的時段也付錢，問題與 A 相同。
>
> **C ✓** 停止的 EC2 instance 不收 instance 費用，只收 EBS 儲存費用，工作狀態保留在 EBS 上。排程停止與啟動讓費用只發生在實際使用的約 50 小時，且不需要長期承諾，是這種使用模式下最划算的做法。
>
> **D ✗** Spot 雖然便宜，但可能在上班時間被中斷，違反「上班時間內不能被中斷」的限制。若是可中斷、無狀態的批次工作，Spot 才是首選。
>
> **考點**：SAA-4.2｜低使用率環境優先關機排程，而不是長期承諾｜延伸閱讀：第 39 章、第 17 章

### 第 12 題｜SAA｜單選｜D1 持續的弱點掃描

一個主管機關要求某政府資訊單位對所有 EC2 instance 與存放在 Amazon ECR 的 container image 進行持續的軟體弱點（CVE）掃描；當新的 CVE 公布時，既有的 instance 與 image 必須自動重新評估，結果要依嚴重程度集中呈現。單位希望不必自行維護掃描伺服器。

應該使用哪一項服務？

- A. Amazon Inspector
- B. Amazon GuardDuty 的 Runtime Monitoring
- C. AWS Config 搭配 managed rules
- D. AWS Systems Manager Patch Manager

> [!answer]- 答案：A
> **A ✓** Amazon Inspector 會持續掃描 EC2 instance（透過 Systems Manager agent 或 agentless 掃描）、ECR image 與 Lambda 函式的軟體套件弱點；新 CVE 加入資料庫時會自動重新評估，findings 依嚴重程度排序，並可整合 Security Hub。
>
> **B ✗** GuardDuty Runtime Monitoring 偵測執行期間的威脅行為（例如可疑的程序或網路連線），不是盤點套件 CVE 的工具。
>
> **C ✗** AWS Config 評估資源設定是否合規（例如 EBS 是否加密），無法掃描作業系統或 image 內的套件弱點。
>
> **D ✗** Patch Manager 負責對 managed node 套用作業系統修補並回報修補合規狀態，但不掃描 ECR image，也不提供 CVE 層級的弱點 findings。弱點由 Inspector 找出，修補可以再交給 Patch Manager。
>
> **考點**：SAA-1.2｜Inspector 負責 EC2、ECR、Lambda 的弱點掃描｜延伸閱讀：第 16 章

### 第 13 題｜SAA｜選兩項｜D2 Health check 造成全站停擺

一家旅館訂房網站以 ALB 搭配 EC2 Auto Scaling group 運行，ASG 使用 ELB health check。應用程式的 `/health` 端點會同時查詢 Aurora 資料庫與第三方付款服務，任何一個逾時就回傳 500。某天付款服務變慢，所有 instance 的 health check 都失敗，ASG 不斷終止並替換 instance，整個網站停擺，連不需要付款的瀏覽與搜尋功能也無法使用。

哪兩項變更最能提升韌性？（選兩項）

- A. 把 health check 的 interval 與 unhealthy threshold 調大，讓 instance 要連續失敗 10 分鐘才被判定不健康
- B. 把 ALB 與 ASG 使用的 health check 改為只檢查應用程式本身是否能處理請求的輕量端點，依賴服務的狀態另以 CloudWatch alarm 監控
- C. 把 ALB 換成 Network Load Balancer，讓 health check 只檢查 TCP 連線
- D. 為 ASG 內所有 instance 啟用 instance scale-in protection
- E. 在應用程式中為付款服務的呼叫設定逾時與 circuit breaker，付款服務異常時只停用付款功能，其他功能照常運作

> [!answer]- 答案：B、E
> **A ✗** 拉長判定時間只會延後連鎖反應發生的時間，付款服務若慢超過 10 分鐘，結果完全一樣；同時也讓真正壞掉的 instance 更久才被替換。
>
> **B ✓** 給 load balancer 與 ASG 的 health check 應該回答「這台 instance 能不能處理請求」，而不是「所有下游都正常嗎」。把共用依賴放進 health check，依賴一出問題，所有 instance 會同時被判定不健康並被替換，造成全面停擺。依賴的健康狀態應另外監控與告警。
>
> **C ✗** 改用 NLB 會失去 ALB 的 L7 路由與 HTTP 功能，屬於過度的架構變更；而且應用程式對付款服務的依賴問題仍在。
>
> **D ✗** Scale-in protection 只防止 ASG 在縮減容量時終止這些 instance，不會阻止因 health check 失敗而進行的替換。
>
> **E ✓** 對非核心依賴設定逾時與 circuit breaker，讓付款服務變慢時快速失敗並降級，瀏覽與搜尋等核心功能不受影響，也避免執行緒被慢速呼叫占滿而拖垮整台伺服器。
>
> **考點**：SAA-2.2｜淺層 health check 與依賴故障時的優雅降級｜延伸閱讀：第 18 章、第 35 章

### 第 14 題｜SAA｜單選｜D3 極高 IOPS 的自管資料庫

一家物流公司因授權限制，必須在 EC2 上自行運行一套商用關聯式資料庫。尖峰時資料庫需要持續 150,000 IOPS、次毫秒等級的延遲，單一 volume 容量約 20 TiB；資料必須在 instance 停止或更換後仍然保留，並要求最高等級的 volume 耐久性。

應該選擇哪一種儲存？

- A. 一個 gp3 volume，並把 IOPS 設定調到該類型的上限
- B. 多個 st1 volume 以 RAID 0 組合，提高總 IOPS
- C. 使用 instance store 的 NVMe SSD，並以應用程式層複寫備份資料
- D. 一個 io2 Block Express volume，掛載在支援 io2 Block Express 的 Nitro instance 上

> [!answer]- 答案：D
> **A ✗** gp3 是性價比最高的通用 SSD，但單一 volume 的 IOPS 上限是 80,000，達不到 150,000，耐久性也只有 99.8%–99.9%，低於 io2。
>
> **B ✗** st1 是 HDD，為大量循序讀寫的 throughput 設計（例如日誌、資料倉儲），隨機 IOPS 很低，RAID 0 也無法把 HDD 變成次毫秒延遲。
>
> **C ✗** Instance store 的 IOPS 很高，但它是暫存儲存：instance 停止、終止或底層硬體故障時資料就會消失，不符合資料必須保留的要求。
>
> **D ✓** io2 Block Express 單一 volume 最高可達 256,000 IOPS、64 TiB，提供次毫秒延遲與 99.999% 的 volume 耐久性，是 EBS 中為關鍵資料庫設計的最高效能類型。需要搭配支援 Block Express 的 Nitro instance 才能發揮完整效能。
>
> **考點**：SAA-3.1｜io2 Block Express 用於極高 IOPS 與高耐久性｜延伸閱讀：第 24 章

### 第 15 題｜SAA｜選兩項｜D1 臨床試驗紀錄的 WORM 保存

一家生技公司要把臨床試驗紀錄存放在一個新建立的 S3 bucket。法規要求每一份紀錄自寫入起保存 7 年，期間不得被刪除或覆寫；任何人，包括帳號的 root user，都不能刪除物件或縮短保存期限。

哪兩個步驟可以滿足需求？（選兩項）

- A. 建立 bucket 時啟用 S3 Object Lock
- B. 設定 Object Lock 的 default retention 為 governance mode、保存 7 年
- C. 設定 Object Lock 的 default retention 為 compliance mode、保存 7 年
- D. 啟用 MFA Delete，要求刪除物件版本時必須提供 MFA
- E. 建立 lifecycle rule，在物件建立 7 年後才轉移到 S3 Glacier Deep Archive

> [!answer]- 答案：A、C
> **A ✓** Object Lock 提供 WORM（write once, read many）保護，啟用時會自動啟用 versioning，鎖定的是特定物件版本。
>
> **B ✗** Governance mode 允許擁有 `s3:BypassGovernanceRetention` 權限的使用者縮短保存期或刪除版本，root user 也能這麼做，不符合「任何人都不能」的要求。若只是防止一般使用者誤刪、但保留管理者例外，governance mode 才適合。
>
> **C ✓** Compliance mode 下，保存期限內任何人（包括 root user）都不能刪除該物件版本或縮短保存期限；default retention 讓每個新寫入的物件自動套用 7 年保存。
>
> **D ✗** MFA Delete 只增加刪除版本時的驗證步驟，持有 MFA 的 root user 仍可刪除，無法達到法規要求的不可刪除。
>
> **E ✗** Lifecycle 只決定物件何時轉移或過期，不會阻止任何人刪除物件。
>
> **考點**：SAA-1.3｜Object Lock compliance mode 與 default retention｜延伸閱讀：第 23 章

### 第 16 題｜SAA｜單選｜D2 一筆壞訊息造成整批重做

一家物流公司用 Lambda 處理 SQS queue 中的發票訊息，event source mapping 的 batch size 為 10。偶爾會有一筆格式錯誤的發票讓函式拋出例外，整批 10 則訊息都回到 queue 重新處理；另外 9 筆正常的發票因此被重複寫入 ERP 系統。公司希望用最少的修改，讓正常的訊息不再被重複處理，壞訊息最終要被隔離以便人工檢查。

應該怎麼做？

- A. 把 batch size 改為 1，讓每次只處理一則訊息
- B. 把 queue 的 visibility timeout 提高為函式 timeout 的 6 倍
- C. 在 event source mapping 啟用 `ReportBatchItemFailures`，函式只回傳處理失敗的訊息 ID，並為 queue 設定 DLQ 與 `maxReceiveCount`
- D. 把 queue 改為 FIFO queue，並啟用 content-based deduplication

> [!answer]- 答案：C
> **A ✗** Batch size 1 確實能避免連坐，但呼叫次數增加 10 倍、吞吐量下降、成本上升。若流量很低，這是可以接受的簡單做法；但在本題不是最佳解。
>
> **B ✗** Visibility timeout 太短會造成訊息在處理中被重複投遞，但本題的重複來自「整批失敗後全部重回 queue」，調整 visibility timeout 不會改變這個行為。AWS 建議的 6 倍設定是另一個問題的答案。
>
> **C ✓** 啟用 partial batch response 後，函式在回應中列出 `batchItemFailures`，Lambda 只會讓這些失敗的訊息重新可見，成功的訊息會被刪除。壞訊息超過 `maxReceiveCount` 後移入 DLQ，供人工檢查。修改量小、吞吐量不變。
>
> **D ✗** FIFO 的去重只在 5 分鐘的去重區間內，防止「生產者重複送出」相同訊息；同一則訊息因處理失敗被重新投遞，不屬於去重的範圍，問題依舊。
>
> **考點**：SAA-2.1｜SQS 與 Lambda 的 partial batch response｜延伸閱讀：第 32 章、第 19 章

### 第 17 題｜SAA｜單選｜D4 大量冷資料的 DynamoDB table

一個城市停車管理處把 5 年來的違規停車紀錄存放在一張 DynamoDB table，資料量約 40 TB，每天只有少量民眾申訴時才會查詢舊紀錄。帳單分析顯示這張 table 的費用中，儲存費用占了八成以上，讀寫費用很少。法規要求紀錄保留 5 年，而且既有的申訴系統必須能以相同的 API 與延遲查詢。

最划算的做法是什麼？

- A. 把資料匯出到 S3 後刪除 table，申訴時改用 Athena 查詢
- B. 把 table class 改為 DynamoDB Standard-Infrequent Access
- C. 把 capacity mode 從 provisioned 改為 on-demand
- D. 啟用 TTL，讓超過 1 年的紀錄自動刪除

> [!answer]- 答案：B
> **A ✗** S3 加 Athena 的儲存成本很低，但申訴系統必須改寫成 SQL 查詢，延遲也從毫秒級變成秒級，違反「相同 API 與延遲」的限制。
>
> **B ✓** Standard-IA table class 的儲存單價明顯低於 Standard，讀寫單價較高，適合「儲存費用為主、存取很少」的 table。切換 table class 不需要改程式，API、效能與耐久性都相同。
>
> **C ✗** Capacity mode 影響的是讀寫費用，本題的成本來源是儲存，切換 capacity mode 幾乎沒有幫助。
>
> **D ✗** TTL 刪除資料可以降低儲存量，但違反保留 5 年的法規要求。
>
> **考點**：SAA-4.3｜儲存為主的 table 改用 Standard-IA table class｜延伸閱讀：第 27 章

### 第 18 題｜SAA｜選兩項｜D1 跨帳號傳送事件到 event bus

一家物流集團的營運帳號（帳號 A）在 default event bus 上產生 `ShipmentDelayed` 事件。集團另一個帳號（帳號 B）負責客戶通知，已建立一個名為 `customer-notify` 的 custom event bus，並在上面設定了 rule 觸發通知流程。集團要求只有 `ShipmentDelayed` 事件會從帳號 A 送到帳號 B，且不想額外開發轉送程式。

哪兩個設定是必要的？（選兩項）

- A. 在兩個帳號的 VPC 之間建立 VPC peering，讓 EventBridge 能跨帳號傳送事件
- B. 在帳號 B 的 `customer-notify` 上建立 rule，定期從帳號 A 的 default event bus 拉取事件
- C. 在帳號 B 為 `customer-notify` 設定 resource-based policy，允許帳號 A 對它執行 `events:PutEvents`
- D. 在帳號 A 建立 SNS topic，讓帳號 B 的 event bus 以 HTTPS 端點訂閱這個 topic
- E. 在帳號 A 的 default event bus 建立只比對 `ShipmentDelayed` 的 rule，target 設為 `customer-notify` 的 ARN，並指定一個具有對該 bus 執行 `events:PutEvents` 權限的 IAM role

> [!answer]- 答案：C、E
> **A ✗** EventBridge 是 Regional 的受管服務，跨帳號傳送事件走的是 AWS 服務端點，與 VPC 網路無關。
>
> **B ✗** EventBridge 是推送模型，rule 只能比對「進入本 bus」的事件，不能主動去另一個帳號拉取。
>
> **C ✓** 接收端的 event bus 必須以 resource-based policy 明確允許來源帳號（或整個 organization）寫入，這是跨帳號授權中「資源擁有者同意」的一半。
>
> **D ✗** Event bus 不能直接訂閱 SNS topic；要繞道就得額外寫轉送程式，違反需求。
>
> **E ✓** 來源端以 rule 過濾出 `ShipmentDelayed`，把另一個帳號的 event bus 設為 target，並由一個 IAM role 代表 EventBridge 呼叫 `PutEvents`，這是「呼叫者具備權限」的另一半。EventBridge 自 2023 年 3 月起要求新建立的跨帳號 event bus target 都必須附上 IAM role（用主控台建立時會自動產生）。只有符合 pattern 的事件會被送出。
>
> **考點**：SAA-1.1、SAA-2.1｜跨帳號 event bus 需要雙方授權｜延伸閱讀：第 32 章、第 13 章

### 第 19 題｜SAA｜單選｜D3 全球門市的 TCP 裝置連線

一家連鎖旅館在全球有 900 家分館，每家分館的房卡製卡機透過自訂的 TCP 協定，連到東京 Region 一個 Network Load Balancer 後方的金鑰管理服務。各分館的企業防火牆只允許連往允許清單（allowlist）內的固定 IP，歐洲分館經 Internet 連線時延遲與抖動很高，常導致製卡逾時。公司明年還會在法蘭克福增設第二個 Region 作為備援，屆時不希望各分館修改防火牆設定。

哪一種做法最合適？

- A. 建立 AWS Global Accelerator，把東京的 NLB 設為 endpoint，日後再把法蘭克福 Region 的 NLB 加入另一個 endpoint group
- B. 建立 CloudFront distribution，以 NLB 作為 origin，讓分館連到最近的 edge location
- C. 為 NLB 配置 Elastic IP，並以 Route 53 latency-based routing 在兩個 Region 之間分流
- D. 從每家分館建立 Site-to-Site VPN 到東京 Region 的 Transit Gateway

> [!answer]- 答案：A
> **A ✓** Global Accelerator 提供兩個固定的 anycast IP，分館從最近的 edge location 進入 AWS 骨幹網路，降低延遲與抖動；它支援任意 TCP／UDP 協定。新增 Region 時只要加入 endpoint group，入口 IP 不變，分館防火牆不需修改；它也會依 health check 自動切換到健康的 Region。
>
> **B ✗** CloudFront 處理的是 HTTP／HTTPS（含 WebSocket）流量，無法代理自訂的 TCP 協定。
>
> **C ✗** Route 53 是 DNS 層的分流：分館連到哪個 Region，就是哪個 Region 的 IP，新增法蘭克福後防火牆要多加 IP；流量也仍走 Internet，延遲與抖動問題沒有改善。
>
> **D ✗** 900 條 VPN 的建置與維運負擔極大，VPN 本身也跑在 Internet 上，抖動問題依舊。
>
> **考點**：SAA-3.4、SAA-2.2｜Global Accelerator 提供固定 IP 與非 HTTP 協定的加速｜延伸閱讀：第 11 章

### 第 20 題｜SAA｜單選｜D2 依類型分送的檢體事件

一家生技研究中心的 LIMS 在檢體入庫時，會依序同步呼叫三個系統的 REST API：計費系統（所有檢體都要處理）、定序排程系統（只處理類型為 DNA 或 RNA 的檢體）、生物資料庫（只處理組織檢體）。任何一個系統維護時，LIMS 的入庫操作就會失敗。研究中心希望 LIMS 只發布一次事件，三個系統各自依自己的速度處理、維護期間的事件不遺失，並且營運負擔最低。

哪一種設計最合適？

- A. LIMS 把事件送到一個 SQS queue，三個系統輪流從同一個 queue 讀取
- B. LIMS 發布到 SNS topic，三個系統各以一個 Lambda 函式訂閱，函式再呼叫各系統的 REST API
- C. LIMS 發布到 SNS topic，扇出到三個 SQS queue，三個系統各自讀取全部事件，在程式中丟棄不需要的類型
- D. LIMS 發布到 SNS topic 並在 message attribute 中帶入檢體類型，扇出到三個 SQS queue，並在各 subscription 設定 filter policy

> [!answer]- 答案：D
> **A ✗** 同一個 queue 的一則訊息只會被一個 consumer 處理，三個系統會互相搶訊息，每個系統都只拿到部分事件。
>
> **B ✗** SNS 以非同步方式呼叫 Lambda，但 Lambda 仍要同步呼叫各系統的 API；系統維護時間一長，重試耗盡後事件就可能遺失，沒有一個可以長期保存事件的緩衝區。
>
> **C ✗** 這個設計能運作，也不會遺失事件，但定序系統與生物資料庫要接收並丟棄大量不需要的訊息，增加處理成本與程式邏輯。若各系統其實需要所有事件，這就是正確答案。
>
> **D ✓** SNS 扇出到 SQS 讓每個系統有自己的持久 queue，維護期間事件留在 queue 中等候；subscription filter policy 依 message attribute（例如 `sampleType`）只把符合條件的訊息送到對應 queue，過濾在 SNS 端完成，不需要寫程式。
>
> **考點**：SAA-2.1｜SNS 扇出到 SQS 與 subscription filter policy｜延伸閱讀：第 32 章

### 第 21 題｜SAA｜選兩項｜D1 ECS task 取得機密

一家旅館集團的會員點數服務在 ECS on Fargate 上運行。目前資料庫密碼與合作夥伴 API key 以明文寫在 task definition 的環境變數中，任何有權查看 task definition 的人都能在主控台看到。資安團隊要求機密以加密方式集中保存並支援輪替，在 container 啟動時注入為環境變數，而且應用程式程式碼不能修改。

哪兩個步驟組合起來可以滿足需求？（選兩項）

- A. 把機密存入 Secrets Manager，並在 task role 的 policy 中允許 `secretsmanager:GetSecretValue`
- B. 把機密存入 Secrets Manager，並在 container definition 的 `secrets` 欄位以 `valueFrom` 引用 secret 的 ARN
- C. 把機密寫入 S3 上的 `.env` 檔案，並在 container definition 的 `environmentFiles` 欄位引用它
- D. 在 task execution role 的 policy 中允許對這些 secret 執行 `secretsmanager:GetSecretValue`；若 secret 使用 customer managed key，也允許 `kms:Decrypt`
- E. 在 CI pipeline 建置 image 時，從 Secrets Manager 讀出機密並寫入 image 的設定檔

> [!answer]- 答案：B、D
> **A ✗** Task role 是應用程式在執行期間呼叫 AWS API 所用的身份。啟動 container 時把 secret 注入環境變數，是由 ECS agent 以 task execution role 完成的，權限放在 task role 不會生效。若應用程式改為自己在程式中呼叫 Secrets Manager，才需要 task role 的權限，但本題不能改程式。
>
> **B ✓** Container definition 的 `secrets` 欄位會在啟動時從 Secrets Manager（或 Parameter Store）取值並注入為環境變數，task definition 中只看得到 ARN，看不到明文；Secrets Manager 提供 KMS 加密與輪替。
>
> **C ✗** `environmentFiles` 讀取的是 S3 上的一般設定檔，不提供機密輪替，檔案內容就是明文，管理方式與目前差不多。
>
> **D ✓** 注入 secret 的動作由 task execution role 執行，必須有讀取 secret 的權限；secret 若以 customer managed key 加密，還需要對該 key 的 `kms:Decrypt`。
>
> **E ✗** 把機密寫進 image，任何能拉取 image 的人都能取得機密，輪替時也必須重建並重新部署 image，比現況更不安全。
>
> **考點**：SAA-1.2、SAA-1.1｜ECS 以 execution role 注入 Secrets Manager 機密｜延伸閱讀：第 21 章、第 15 章

### 第 22 題｜SAA｜單選｜D4 長期保存但幾乎不還原的 snapshot

一個政府機關的案件管理伺服器每月建立一次 EBS snapshot，稽核規定每份月度 snapshot 要保存 7 年。過去十年只還原過一次舊 snapshot，若真有需要，72 小時內取回即可接受。這些 snapshot 目前都放在標準層，費用逐年增加。

哪一種做法最划算？

- A. 把每份月度 snapshot 匯出到 S3 bucket，再以 lifecycle rule 轉移到 S3 Glacier Deep Archive
- B. 把建立超過 90 天的月度 snapshot 移到 EBS Snapshots Archive 層
- C. 只保留最新一份 snapshot，因為 snapshot 是增量的，最新一份已包含所有資料
- D. 以 Data Lifecycle Manager 把 snapshot 複製到另一個 Region 的標準層

> [!answer]- 答案：B
> **A ✗** EBS snapshot 存放在 AWS 管理的儲存中，無法直接以物件形式匯出到自己的 S3 bucket 再套 lifecycle，這不是可行的原生做法。
>
> **B ✓** EBS Snapshots Archive 是為「長期保存、很少還原」設計的低成本層：snapshot 封存時會轉成完整（非增量）的 snapshot 存放，儲存單價比標準層低很多；最短保存 90 天，還原回標準層需要最多 72 小時，正好符合需求。AWS 建議封存月度、季度或年度 snapshot；每日 snapshot 轉成完整 snapshot 後反而可能更貴。另外，每個 volume 預設最多 25 份封存 snapshot，7 年 84 份需要先申請提高 quota。
>
> **C ✗** Snapshot 是增量的，但刪除舊 snapshot 後只會保留還原最新狀態所需的資料，無法再還原到過去某個月份，違反 7 年保存規定。
>
> **D ✗** 跨 Region 複製提升的是災難復原能力，等於多一份標準層的費用，成本只會增加。
>
> **考點**：SAA-4.1｜EBS Snapshots Archive 用於長期很少還原的 snapshot｜延伸閱讀：第 24 章、第 39 章

### 第 23 題｜SAA｜單選｜D2 跨 Region 的訂單資料庫

一家跨國物流公司的訂單系統使用 us-east-1 的 Aurora PostgreSQL。公司新增兩項要求：如果整個 Region 故障，必須能在另一個 Region 於數分鐘內恢復寫入，資料遺失控制在秒級；歐洲的調度中心需要低延遲讀取訂單資料。團隊希望以受管功能完成，不自行維護複寫程式。

哪一種做法最合適？

- A. 建立 Aurora Global Database，在 eu-west-1 加入 secondary cluster 供歐洲讀取，Region 故障時把 secondary 提升為 primary
- B. 啟用 automated backups 並設定每小時把 snapshot 複製到 eu-west-1，事故時從最新 snapshot 還原
- C. 在 us-east-1 的 cluster 加入 3 個分布在不同 AZ 的 Aurora Replicas
- D. 使用 AWS DMS 建立持續複寫任務，把資料同步到 eu-west-1 的 RDS for PostgreSQL

> [!answer]- 答案：A
> **A ✓** Aurora Global Database 在儲存層進行跨 Region 複寫，典型延遲在 1 秒以內，secondary Region 的 cluster 可直接提供低延遲讀取。Region 故障時可以把 secondary 提升為可寫入的 primary，通常在數分鐘內完成，RPO 為秒級。
>
> **B ✗** 每小時複製 snapshot 代表最多遺失一小時資料，從 snapshot 還原大型資料庫也需要較長時間，不符合秒級 RPO 與分鐘級 RTO；也無法提供歐洲即時讀取。
>
> **C ✗** Aurora Replicas 提供同 Region 內的讀取擴展與 AZ 故障的快速 failover，但全部在 us-east-1，Region 故障時一起失效。
>
> **D ✗** DMS 能做跨 Region 持續複寫，但複寫任務與目標資料庫都要自行監控與維護，延遲通常比 Global Database 高，切換流程也較複雜。若來源與目標是不同引擎，DMS 才是合理的選擇。
>
> **考點**：SAA-2.2、SAA-3.3｜Aurora Global Database 提供秒級 RPO 的跨 Region DR｜延伸閱讀：第 26 章、第 34 章

### 第 24 題｜SAA｜單選｜D1 金鑰管理與資料存取的職責分離

一個稅務機關以一把 customer managed KMS key 加密民眾的報稅資料。內控規定：資安團隊負責管理這把 key（啟用輪替、修改 key policy、排程刪除），但不得能夠解密任何報稅資料；申報系統使用的 IAM role 可以加解密，但不得修改 key 的設定。

哪一種做法最能滿足職責分離？

- A. 改用 AWS managed key，讓 AWS 負責金鑰管理，資安團隊只需要稽核 CloudTrail
- B. 授予資安團隊包含 `kms:*` 的 IAM policy，並以 CloudTrail 監控與告警任何 `Decrypt` 呼叫
- C. 在 key policy 中，只授予資安團隊的 role 管理類動作（例如 `kms:Put*`、`kms:Enable*`、`kms:ScheduleKeyDeletion`），不含 `kms:Decrypt`；只授予申報系統的 role `kms:Encrypt`、`kms:Decrypt`、`kms:GenerateDataKey*`
- D. 改用匯入金鑰材料（imported key material）的 KMS key，由資安團隊在地端保管金鑰材料備份

> [!answer]- 答案：C
> **A ✗** AWS managed key 的 key policy 由 AWS 管理且無法修改，資安團隊無法啟用自訂的管理流程，也無法精細控制哪些 role 能解密。
>
> **B ✗** 這是「事後偵測」而非「事前防止」：資安團隊仍然擁有解密能力，違反「不得能夠解密」的規定。
>
> **C ✓** KMS 把管理類 API 與密碼學操作（Encrypt、Decrypt、GenerateDataKey）分成不同動作，key policy 可以分別授予不同的 principal，這正是 key administrator 與 key user 的職責分離設計。實務上還要確認 key policy 中若保留「允許 IAM policy 授權」的敘述，沒有任何 IAM policy 另外授予資安團隊 `kms:Decrypt`。
>
> **D ✗** 匯入金鑰材料讓組織能控制金鑰材料的來源與到期，但與「誰能呼叫 Decrypt」的權限分離無關。
>
> **考點**：SAA-1.3｜Key policy 分離 key administrator 與 key user｜延伸閱讀：第 15 章

### 第 25 題｜SAA｜單選｜D3 地端 NAS 的大量資料搬遷

一個基因研究所在地端 NFS NAS 上有 500 TB 的定序資料，已經有一條 10 Gbps 的 Direct Connect 連到 AWS。研究所要在 3 週內把所有資料遷移到 S3，之後每晚把新產生的定序結果增量同步到 S3。研究所要求傳輸後自動驗證資料完整性，並希望自行撰寫的腳本越少越好。

哪一種做法最合適？

- A. 在地端伺服器以 cron 執行 `aws s3 sync`，並撰寫腳本比對檔案的 checksum
- B. 部署 S3 File Gateway，把 NAS 上的資料複製到 File Gateway 提供的 NFS 共享
- C. 建立 AWS Transfer Family SFTP 伺服器，讓研究人員以 SFTP 上傳資料到 S3
- D. 在地端部署 AWS DataSync agent，建立從 NFS 到 S3 的 task，啟用資料驗證並設定每晚排程執行

> [!answer]- 答案：D
> **A ✗** `aws s3 sync` 可以運作，但大量檔案的平行傳輸、重試、完整性驗證與排程都要自己寫腳本與監控，不符合「腳本越少越好」。
>
> **B ✗** S3 File Gateway 的用途是讓地端應用程式持續以 NFS／SMB 存取 S3 中的資料（混合存取），它有本地快取與上傳佇列，並非為一次性大量搬遷與排程增量同步設計的工具。
>
> **C ✗** Transfer Family 適合讓外部合作夥伴以 SFTP／FTPS 交換檔案，用來搬遷 500 TB 需要人工上傳，沒有排程與驗證機制。
>
> **D ✓** DataSync 是為大量線上資料搬遷設計的受管服務：agent 直接讀取 NFS，以平行化傳輸充分利用 Direct Connect 頻寬，內建傳輸後的完整性驗證，task 可設定排程，後續執行只傳輸有變更的檔案。以 10 Gbps 計算，500 TB 在 3 週內傳完是可行的。
>
> **考點**：SAA-3.5｜DataSync 負責線上大量搬遷與排程增量同步｜延伸閱讀：第 25 章

### 第 26 題｜SAA｜單選｜D1 民眾以國家數位身份登入

一個市政府要推出線上服務入口網站，網站以 ECS 運行，前端是 ALB。市民希望使用中央政府提供的國家數位身份服務登入，該服務是符合 OpenID Connect 標準的 identity provider；沒有國家數位身份的外籍居民，則需要以 email 註冊本地帳號。網站後端只想驗證 JWT，不想自行開發帳號、密碼與登入流程。

哪一種做法最合適？

- A. 建立 Cognito user pool，設定國家數位身份服務為 OIDC identity provider，同時允許 user pool 的本地帳號註冊，後端驗證 user pool 簽發的 JWT
- B. 啟用 IAM Identity Center，把國家數位身份服務設為外部 identity provider，並為市民建立 permission set
- C. 建立 Cognito identity pool，把國家數位身份服務設為 OIDC provider，讓市民取得 AWS 臨時憑證後呼叫後端
- D. 以 Lambda 與 DynamoDB 自行實作註冊與登入，密碼以 bcrypt 雜湊保存，並自行簽發 JWT

> [!answer]- 答案：A
> **A ✓** Cognito user pool 是面向終端使用者的使用者目錄，可以同時支援本地帳號與外部 OIDC／SAML／社群登入的聯合身份，並提供受管的登入頁面。無論使用者從哪種方式登入，後端都只需驗證 user pool 簽發的 JWT。
>
> **B ✗** IAM Identity Center 是給員工（workforce）登入 AWS 帳號與企業應用程式用的，不適合也不是為大量市民登入網站設計。
>
> **C ✗** Identity pool 的用途是把已驗證的身份換成 AWS 臨時憑證，讓用戶端直接存取 AWS 資源；它本身不是使用者目錄，無法讓外籍居民註冊本地帳號。
>
> **D ✗** 自建身份系統要處理密碼保存、重設、MFA、權杖簽發與輪替，營運負擔與安全風險都很高。
>
> **考點**：SAA-1.1｜Cognito user pool 聯合外部 OIDC 並提供本地帳號｜延伸閱讀：第 13 章

### 第 27 題｜SAA｜選兩項｜D2 超過 15 分鐘的報表工作

一個稅務機關讓民眾線上申請年度所得明細報表，每份報表需要 20–40 分鐘的 CPU 密集運算。目前 API 直接呼叫 Lambda 產生報表，經常因 15 分鐘上限而失敗。申請量平時很低，但在申報截止前幾天會暴增數十倍。機關希望架構解耦、能隨申請量擴展、成本合理，而且營運負擔低。

哪兩個步驟組合起來最合適？（選兩項）

- A. API 收到申請後，把工作訊息寫入 SQS queue，立即回應民眾「處理中」
- B. 把 Lambda 的 timeout 提高到 60 分鐘
- C. 改用 Step Functions Express workflow 呼叫同一個 Lambda 函式，延長可執行時間
- D. 依截止日前的尖峰需求，建立固定數量的 EC2 instance 全天候輪詢 queue
- E. 以 ECS on Fargate service 作為 worker 從 queue 讀取工作，並以「每個 task 平均待處理訊息數」為指標做 target tracking 擴展

> [!answer]- 答案：A、E
> **A ✓** 把申請寫入 SQS，讓接收請求與執行工作解耦：尖峰時工作在 queue 中排隊，不會因 worker 不足而失敗，API 也能立即回應。
>
> **B ✗** Lambda 單次執行最長 15 分鐘，這是硬上限，無法提高到 60 分鐘。
>
> **C ✗** Express workflow 單次執行最長 5 分鐘，而且被呼叫的 Lambda 仍受 15 分鐘限制，問題沒有解決。
>
> **D ✗** 依尖峰固定配置 instance，平時絕大部分容量閒置，成本最高；instance 的修補與維運也增加負擔。
>
> **E ✓** Fargate 沒有 15 分鐘的執行限制，也不需要管理伺服器。以「backlog per task」（queue 中可見訊息數除以執行中的 task 數）作為擴展指標，能讓 worker 數量隨積壓量增減，平時縮到很少的 task，尖峰自動擴展。
>
> **考點**：SAA-2.1、SAA-3.2｜SQS 解耦長時間工作，worker 依 backlog 擴展｜延伸閱讀：第 32 章、第 21 章

### 第 28 題｜SAA｜單選｜D4 大量傳回地端的傳輸費用

一個生技研究機構每月從 AWS 的 S3 把約 80 TB 的分析結果下載回地端的運算叢集，目前透過 Internet 傳輸，帳單上的 data transfer out 費用很高，傳輸速度也時快時慢。研究機構預期這個傳輸量會持續數年。

哪一種做法最能降低成本並提供穩定的傳輸？

- A. 建立 Site-to-Site VPN，讓下載流量走加密通道
- B. 啟用 S3 Transfer Acceleration，加快下載速度
- C. 建立 AWS Direct Connect 連線，讓下載流量經由 Direct Connect 傳回地端
- D. 在 bucket 啟用 Requester Pays，讓下載的一方負擔傳輸費用

> [!answer]- 答案：C
> **A ✗** Site-to-Site VPN 跑在 Internet 上，傳出流量仍以 Internet data transfer out 的費率計費，並額外產生 VPN 連線的小時費，速度也仍受 Internet 品質影響。
>
> **B ✗** Transfer Acceleration 是在一般傳輸費之外再加收加速費，成本只會更高。
>
> **C ✓** 經由 Direct Connect 傳出的資料，其 data transfer out 費率明顯低於 Internet 傳出費率；在每月數十 TB 且長期持續的傳輸量下，節省的傳輸費用通常遠超過 port 小時費，專線也提供穩定的頻寬與延遲。
>
> **D ✗** Requester Pays 是把費用轉給「請求下載的那個 AWS 帳號」。下載方就是研究機構自己，費用只是換個帳號付，總額不變。
>
> **考點**：SAA-4.4｜大量長期傳出流量走 Direct Connect 以降低傳輸費率｜延伸閱讀：第 8 章、第 39 章

### 第 29 題｜SAA｜單選｜D1 公開 API 遭受注入攻擊

一家貨運平台以 API Gateway REST API（Regional endpoint）提供訂艙服務給客戶。日誌顯示有大量含 SQL injection 字串的請求，以及來自已知惡意 IP 的掃描流量。後端由另一個團隊維護，短期內無法修改程式碼。公司希望以受管、低維護的方式阻擋這些請求。

哪一種做法最合適？

- A. 訂閱 AWS Shield Advanced，由 AWS 自動阻擋 SQL injection
- B. 建立 AWS WAF web ACL，加入 AWS Managed Rules 的核心規則集、SQL database 規則群組與 IP reputation 清單，並與 API 的 stage 關聯
- C. 在 API Gateway 所在 subnet 的 network ACL 中加入惡意 IP 的 deny 規則
- D. 為 API 啟用 API key 與 usage plan，限制每個客戶的請求速率

> [!answer]- 答案：B
> **A ✗** Shield Advanced 專注在 DDoS 防護與相關支援；阻擋 SQL injection 仍要靠 WAF 規則。
>
> **B ✓** AWS WAF 可以直接與 API Gateway REST API 的 stage 關聯。AWS Managed Rules 由 AWS 維護，SQL database 規則群組檢查注入特徵，Amazon IP reputation list 阻擋已知惡意來源，不必修改後端，也不必自己維護規則。
>
> **C ✗** API Gateway 是 AWS 管理的服務，不在你的 VPC subnet 中，network ACL 管不到它；NACL 也無法檢查 HTTP 內容。
>
> **D ✗** Usage plan 可以限制特定客戶的請求速率，但攻擊者不一定使用合法的 API key；API key 也不是安全驗證機制，而且完全無法辨識 SQL injection 內容。
>
> **考點**：SAA-1.2｜WAF managed rules 掛載於 API Gateway｜延伸閱讀：第 16 章、第 20 章

### 第 30 題｜SAA｜單選｜D3 需要 GPU 的 container 工作負載

一個城市交通局在路口攝影機的影像串流上執行車流辨識，模型以 PyTorch 撰寫並打包成 container image，推論時需要 NVIDIA GPU。團隊希望使用 ECS 管理 container 的部署與擴展，有成員提議全部改用 Fargate 以降低營運負擔。

哪一種做法能滿足需求？

- A. 使用 ECS on Fargate，在 task definition 中宣告 GPU 資源需求
- B. 改以 Lambda container image 部署模型，並把記憶體調到 10,240 MB
- C. 使用 EKS，並為推論工作建立 Fargate profile
- D. 使用 ECS 搭配 GPU EC2 instance 的運算容量（例如以 capacity provider 連接使用 GPU instance 與 ECS GPU-optimized AMI 的 Auto Scaling group），在 task definition 中宣告 GPU 需求

> [!answer]- 答案：D
> **A ✗** Fargate 不提供 GPU，即使在 task definition 中宣告 GPU 也無法在 Fargate 上執行。這題的陷阱就是「Fargate 營運負擔最低」這個直覺。
>
> **B ✗** Lambda 不提供 GPU，最大記憶體 10,240 MB 只會分配更多 CPU。
>
> **C ✗** EKS 的 Fargate profile 同樣跑在 Fargate 上，沒有 GPU。
>
> **D ✓** ECS 在 EC2 運算容量上支援 GPU：使用含 NVIDIA 驅動的 GPU-optimized AMI，task definition 中宣告需要的 GPU 數量，ECS 會把 task 排程到有可用 GPU 的 instance。以 capacity provider 連接 Auto Scaling group，ECS 可以依 task 需求自動擴展 instance。若想減少管理 instance 的負擔，也可以改用 ECS Managed Instances（由 AWS 代管 EC2 的修補與擴縮，可選 GPU instance type），它同樣屬於「EC2 運算容量」，不是 Fargate。
>
> **考點**：SAA-3.2｜Fargate 與 Lambda 不支援 GPU，GPU 工作負載使用 EC2 容量｜延伸閱讀：第 21 章、第 17 章

### 第 31 題｜SAA｜單選｜D2 三節點叢集避免同時故障

一個消防局的緊急派遣系統使用三個節點組成的 quorum 叢集，至少要有兩個節點存活才能運作。軟體供應商的認證規定三個節點必須在同一個 subnet 內。系統負責人擔心底層同一台實體主機或同一個機櫃故障時，會同時帶走兩個節點。

哪一種做法最能降低這個風險？

- A. 把三個 instance 啟動在同一個 spread placement group 中
- B. 把三個 instance 啟動在同一個 cluster placement group 中
- C. 建立只有一個 partition 的 partition placement group，把三個 instance 都放進去
- D. 為三個 instance 配置一台 Dedicated Host，確保硬體不與其他客戶共用

> [!answer]- 答案：A
> **A ✓** Spread placement group 會把每個 instance 放在不同的機櫃上，各自有獨立的網路與電源，單一硬體或機櫃故障最多影響一個節點。每個 AZ 每個 group 最多 7 個執行中的 instance，三個節點綽綽有餘。
>
> **B ✗** Cluster placement group 把 instance 緊密放在一起以取得低延遲與高頻寬，反而提高同時故障的機率。
>
> **C ✗** 只有一個 partition 等於所有 instance 共用同一組機櫃，沒有任何隔離效果。Partition placement group 適合 HDFS、Cassandra 這類大型分散式系統，用多個 partition 隔離故障。
>
> **D ✗** 三個 instance 放在同一台 Dedicated Host，主機故障時三個節點全部失效，風險最高。Dedicated Host 解決的是授權與合規問題，不是可用性。
>
> **考點**：SAA-2.2｜Spread placement group 隔離硬體故障｜延伸閱讀：第 17 章

### 第 32 題｜SAA｜單選｜D1 讓所有新的 EBS volume 自動加密

一家物流公司的資安政策要求：所有新建立的 EBS volume 都必須加密，包括團隊從未加密的公開 AMI 啟動的 instance，以及 Auto Scaling group 自動建立的 volume。公司希望以最少的人工作業達成，並且不想讓開發人員因啟動失敗而頻繁求助。

哪一種做法最合適？

- A. 部署 AWS Config managed rule `encrypted-volumes`，發現未加密的 volume 時自動通知負責人重建
- B. 以 SCP 拒絕所有 `ec2:Encrypted` 條件為 false 的 `ec2:CreateVolume` 與 `ec2:RunInstances` 請求
- C. 在每個使用中的 Region 啟用 EBS encryption by default，並指定要使用的 KMS key
- D. 規定所有團隊只能使用由平台團隊預先複製並加密過的 AMI

> [!answer]- 答案：C
> **A ✗** Config rule 是事後偵測，未加密的 volume 已經被建立並可能寫入資料，事後重建也需要人工處理。
>
> **B ✗** SCP 可以預防未加密的 volume，但它只會「拒絕」請求，從未加密 AMI 啟動或未指定加密的範本都會直接失敗，開發人員需要逐一修改，與「不想頻繁求助」相違。
>
> **C ✓** EBS encryption by default 是帳號在每個 Region 的設定，啟用後該 Region 新建立的 EBS volume 與從 snapshot 建立的 volume 都會自動加密，即使來源 AMI 未加密也一樣，不需要修改任何啟動範本。要注意這是 per-Region 設定，每個使用的 Region 都要啟用。
>
> **D ✗** 預先加密的 AMI 只能涵蓋平台團隊準備的映像，人工流程容易被繞過，維護負擔也較大。
>
> **考點**：SAA-1.3｜EBS encryption by default 是每個 Region 的帳號設定｜延伸閱讀：第 24 章、第 15 章

### 第 33 題｜SAA｜選兩項｜D4 夜間大量模擬工作

一個城市交通局每晚要執行 2,000 個彼此獨立的交通模擬工作，每個工作 10–30 分鐘，程式會定期寫 checkpoint 到 S3，被中斷後可以從 checkpoint 繼續。所有工作只要在隔天早上 6 點前完成即可。交通局希望以最低成本運行，同時盡量避免大量工作因容量不足而延誤。

哪兩個做法最合適？（選兩項）

- A. 使用 On-Demand instance 並購買 1 年期 Compute Savings Plans
- B. 使用 AWS Batch managed compute environment，並設定以 Spot instance 為主、allocation strategy 為 `SPOT_PRICE_CAPACITY_OPTIMIZED`
- C. 在 compute environment 中允許多種 instance family 與大小，並為 job 設定重試次數以處理 Spot 中斷
- D. 只使用單一、目前 Spot 價格最低的 instance type，以取得最低單價
- E. 把每個模擬工作改寫為 Lambda 函式，由 Step Functions 平行呼叫

> [!answer]- 答案：B、C
> **A ✗** Savings Plans 適合全天候穩定的用量。這批工作只在夜間執行、可容忍中斷，Spot 的折扣更大，也不需要承諾。
>
> **B ✓** AWS Batch 負責佇列、排程與運算資源的擴縮，工作完成後 instance 自動縮減。`SPOT_PRICE_CAPACITY_OPTIMIZED` 會從容量充足、中斷機率較低的 Spot 池中選擇價格較低者，兼顧成本與穩定。
>
> **C ✓** 允許多種 instance type 能讓 Batch 從更多 Spot 容量池取得資源，降低單一池容量不足或被集中回收的風險；搭配 job retry 與 checkpoint，被中斷的工作能自動重新排程並從中斷點繼續。
>
> **D ✗** 只用單一 instance type 會把所有工作集中在同一個 Spot 容量池，該池一旦容量緊張或被回收，大量工作會同時中斷或無法啟動。
>
> **E ✗** Lambda 單次最長 15 分鐘，無法執行 30 分鐘的工作。
>
> **考點**：SAA-4.2、SAA-3.2｜Batch + Spot 多元化與重試｜延伸閱讀：第 21 章、第 39 章

### 第 34 題｜SAA｜單選｜D2 主資料與搜尋索引不同步

一家訂房平台把各旅館的房型與空房資料存放在 DynamoDB，搜尋頁面則使用 Amazon OpenSearch Service 提供全文與地理位置搜尋。目前應用程式在更新 DynamoDB 後，再自己寫入 OpenSearch；只要第二步失敗，兩邊的資料就不一致，旅客常看到早已售完的房型。平台希望搜尋索引在數秒內反映變更、更新流程與索引流程解耦，並且盡量少寫程式。

哪一種做法最合適？

- A. 每晚把 DynamoDB table 匯出到 S3，再以批次工作重建 OpenSearch 索引
- B. 啟用 DynamoDB Streams，以 Lambda 讀取變更事件並寫入 OpenSearch，應用程式只寫 DynamoDB
- C. 在 DynamoDB 前加上 DAX，讓搜尋頁面直接從 DAX 讀取，不再使用 OpenSearch
- D. 讓搜尋頁面改用 DynamoDB `Scan` 搭配 `FilterExpression` 查詢，移除 OpenSearch

> [!answer]- 答案：B
> **A ✗** 每晚重建索引只能做到一天一次的同步，無法在數秒內反映空房變化。
>
> **B ✓** DynamoDB Streams 會依序記錄每個 item 的新增、修改與刪除，Lambda 以 event source mapping 讀取後更新 OpenSearch，失敗時會重試。應用程式只負責寫入主資料，索引更新變成非同步的獨立流程，延遲通常在秒級。另一個更少程式的選擇是 DynamoDB 與 OpenSearch Service 的 zero-ETL 整合（透過 OpenSearch Ingestion），原理同樣是讀取變更串流。
>
> **C ✗** DAX 是 DynamoDB 的記憶體快取，只能加速相同的 key-value 查詢，不提供全文或地理位置搜尋。
>
> **D ✗** `Scan` 會讀取整張 table 再過濾，費用與延遲都隨資料量線性增加，也無法提供全文搜尋的相關性排序。
>
> **考點**：SAA-2.1｜以 DynamoDB Streams 非同步同步衍生資料｜延伸閱讀：第 27 章、第 29 章

### 第 35 題｜SAA｜單選｜D1 讓民眾下載私有檔案

一個戶政機關的線上服務讓民眾登入後下載自己的證明文件 PDF。文件存放在一個未公開的 S3 bucket，機關要求 bucket 維持 Block Public Access，每次產生的下載連結 10 分鐘後失效，並希望以最少的開發與維運完成。後端應用程式已在登入時驗證民眾身份。

哪一種做法最合適？

- A. 把文件設為公開讀取，但使用隨機且難以猜測的檔名
- B. 建立 CloudFront distribution 與 OAC，為每位民眾產生 signed cookies，並維護 CloudFront 的 key group
- C. 在 bucket policy 中加入 `aws:Referer` 條件，只允許來自機關網站的請求下載
- D. 後端驗證民眾身份後，以具有讀取權限的 role 產生有效期 10 分鐘的 S3 presigned URL 回傳給民眾

> [!answer]- 答案：D
> **A ✗** 公開物件違反 Block Public Access 的要求；「難以猜測的檔名」不是存取控制，連結外流就無法撤回。
>
> **B ✗** CloudFront signed cookies 可以運作，適合需要邊緣快取、自訂網域或一次授權多個檔案的情境；但本題只需單檔、短時間的下載，額外建立 distribution 與管理簽章金鑰是多餘的負擔。
>
> **C ✗** `Referer` 標頭由用戶端送出，可以輕易偽造，AWS 也不建議用它來保護敏感資料。
>
> **D ✓** Presigned URL 以產生者的權限簽章，在指定的有效期內允許持有者執行該操作，bucket 本身不需公開。要注意 URL 的實際有效期也受簽章憑證的影響：以臨時憑證簽章時，憑證過期後 URL 也會失效，10 分鐘的需求通常不受影響。
>
> **考點**：SAA-1.1｜S3 presigned URL 提供短期的私有物件存取｜延伸閱讀：第 22 章

### 第 36 題｜SAA｜選兩項｜D3 Wi-Fi 日誌進入 data lake

一家飯店集團的 600 家分館每秒共產生約 20 MB 的 JSON 格式 Wi-Fi 連線日誌。分析師使用 Athena 依日期與分館查詢這些資料，目前每次查詢都要掃描大量原始 JSON，費用很高。集團可以接受資料在 5 分鐘內進入 data lake，並希望以最低的營運負擔降低 Athena 的查詢成本。

哪兩個做法組合起來最合適？（選兩項）

- A. 以 Kinesis Data Streams 接收日誌，在 EC2 上執行自訂 consumer 把資料轉成 CSV 寫入 S3
- B. 讓每家分館把每一行日誌各自以一個 S3 物件上傳
- C. 把日誌寫入 RDS for MySQL，分析師改用 SQL 直接查詢資料庫
- D. 以 Amazon Data Firehose 接收日誌，啟用 record format conversion，依 Glue Data Catalog 的 table schema 轉成 Parquet 寫入 S3
- E. 讓資料依日期（與分館）分區寫入 S3 prefix，並在 Athena table 上定義分區（例如使用 partition projection），查詢時以分區條件過濾

> [!answer]- 答案：D、E
> **A ✗** 自建 consumer 需要維運 EC2；CSV 仍是以「列」（row）為單位儲存的文字格式，Athena 依舊要讀取整個檔案。
>
> **B ✗** 每行一個物件會產生數量龐大的小檔案，PUT 請求費用高，Athena 處理大量小檔的效率也很差。
>
> **C ✗** 每秒 20 MB 的持續寫入與大量分析查詢，會讓單一關聯式資料庫成為瓶頸，擴展與成本都不理想。
>
> **D ✓** Firehose 是全受管的傳送服務，會依 buffer 設定把資料批次寫入 S3，延遲在分鐘級以內。Record format conversion 把 JSON 轉為欄式的 Parquet，Athena 只讀取查詢用到的欄位並受益於壓縮，掃描量大幅下降。
>
> **E ✓** Athena 依掃描的資料量計費。資料依日期與分館分區後，查詢條件中帶入分區欄位，Athena 只會讀取符合條件的 prefix。Firehose 可以用預設的時間 prefix 或 dynamic partitioning 寫出這種結構；partition projection 讓 Athena 不必逐一登錄每個分區。
>
> **考點**：SAA-3.5、SAA-4.1｜Firehose 轉 Parquet 加上分區降低 Athena 掃描量｜延伸閱讀：第 31 章、第 30 章

### 第 37 題｜SAA｜單選｜D1 掃描合作夥伴上傳的檔案

一家生技公司讓合作實驗室透過 presigned URL 把實驗資料檔上傳到 S3，下游的分析流程會自動開啟這些檔案。資安團隊要求每個新上傳的物件都必須自動掃描惡意軟體，掃描結果要能用於阻擋下游讀取可疑檔案，而且不想自行維護掃描伺服器或病毒碼更新。

哪一種做法最合適？

- A. 在 bucket 上啟用 Amazon Macie，偵測含有惡意內容的物件
- B. 啟用 Amazon Inspector，對 S3 中新上傳的物件執行弱點掃描
- C. 為該 bucket 啟用 GuardDuty Malware Protection for S3 並啟用掃描結果 tagging，依物件 tag 限制下游讀取，並以 EventBridge 把可疑檔案移到隔離 bucket
- D. 以 S3 event notification 觸發 Auto Scaling group 中執行開源防毒軟體的 EC2 instance 掃描檔案

> [!answer]- 答案：C
> **A ✗** Macie 偵測的是敏感資料（個資、金融資料），不是惡意軟體。
>
> **B ✗** Inspector 掃描的是 EC2、ECR image 與 Lambda 的軟體弱點，不掃描 S3 物件內容。
>
> **C ✓** GuardDuty Malware Protection for S3 會在物件上傳後自動掃描，掃描結果預設發送到 EventBridge；啟用選用的 tagging 後，還會把結果寫成物件 tag `GuardDutyMalwareScanStatus`（例如 `NO_THREATS_FOUND`、`THREATS_FOUND`）。Bucket policy 可依 tag 拒絕下游讀取尚未掃描或有威脅的物件，EventBridge 可觸發自動隔離。掃描引擎由 AWS 維護。
>
> **D ✗** 這種做法能運作，但需要自行維護 EC2、防毒軟體與病毒碼更新，違反「不想自行維護掃描伺服器」的要求。
>
> **考點**：SAA-1.2｜GuardDuty Malware Protection for S3 掃描上傳物件｜延伸閱讀：第 16 章

### 第 38 題｜SAA｜單選｜D2 綁定單一 instance 的舊系統

一家倉儲公司的舊版倉儲管理系統（WMS）因授權綁定，只能在一台特定的 EC2 instance 上執行，不能同時執行多個副本；外部的掃描設備以固定的 Elastic IP 連線。公司希望在底層硬體故障時自動恢復服務，並保留相同的 instance ID、private IP、Elastic IP 與 EBS 資料。這台 instance 只使用 EBS volume。

哪一種做法最合適？

- A. 確認 instance type 支援自動復原，並建立偵測 `StatusCheckFailed_System` 的 CloudWatch alarm，動作設為 recover
- B. 把 instance 放進 min、max、desired 都為 1 的 Auto Scaling group，故障時自動替換
- C. 每天建立 AMI，故障時由值班人員以最新 AMI 啟動新 instance 並重新綁定 Elastic IP
- D. 把 instance 移到 spread placement group，降低硬體故障的機率

> [!answer]- 答案：A
> **A ✓** EC2 的 recover 動作會在系統狀態檢查失敗（底層硬體或網路問題）時，把 instance 移到新的硬體上，保留 instance ID、private IP、Elastic IP、instance metadata 與 EBS volume，對授權綁定的單機系統最友善。許多 instance type 也預設啟用 simplified automatic recovery；以 alarm 設定可以明確掌握並接通知。
>
> **B ✗** ASG 替換時會建立一台全新的 instance，instance ID 與 private IP 都會改變，綁定授權可能失效，Elastic IP 也需要額外腳本重新綁定。若應用程式是無狀態且不綁定 instance，ASG min=max=1 是常見的自我修復模式。
>
> **C ✗** 人工還原需要時間，而且新 instance 的 ID 與 IP 不同，不符合自動恢復與保留識別資訊的要求。
>
> **D ✗** Spread placement group 對多台 instance 才有隔離效果，單一 instance 放進去不會降低它本身的硬體故障率，也不會自動恢復。
>
> **考點**：SAA-2.2｜EC2 auto recovery 保留 instance 身份｜延伸閱讀：第 17 章、第 36 章

### 第 39 題｜SAA｜單選｜D4 存取模式無法預測的影像庫

一個城市的交通管理中心把路口攝影機的截圖存放在 S3，總量約 2 PB，大部分物件不會再被讀取；但警方調查事故時，可能在數個月後密集讀取某段時間的大量截圖，而且必須毫秒級立即取得。多數物件大於 128 KB。管理中心希望降低儲存成本，又不想自己分析存取模式或維護 lifecycle 規則。

哪一種儲存方式最合適？

- A. 以 lifecycle rule 在 30 天後把物件轉移到 S3 Standard-IA
- B. 使用 S3 Intelligent-Tiering
- C. 以 lifecycle rule 在 30 天後把物件轉移到 S3 Glacier Flexible Retrieval
- D. 以 lifecycle rule 在 30 天後把物件轉移到 S3 One Zone-IA

> [!answer]- 答案：B
> **A ✗** Standard-IA 每次讀取都要付 retrieval 費用，警方密集讀取時費用可能很高；物件也不會因為再次被頻繁存取而自動回到 Standard。
>
> **B ✓** Intelligent-Tiering 依每個物件的實際存取情況自動在 Frequent、Infrequent、Archive Instant Access 各層之間移動，這三層都提供毫秒級存取，沒有 retrieval 費用；物件被讀取後自動回到 Frequent 層。只需支付少量的每物件監控費，小於 128 KB 的物件不收監控費但也不會被移到較低層，因此本題「多數物件大於 128 KB」很關鍵。
>
> **C ✗** Glacier Flexible Retrieval 取回需要數分鐘到數小時，不符合毫秒級取得的要求。
>
> **D ✗** One Zone-IA 只存放在單一 AZ，AZ 損毀時資料可能遺失，不適合作為調查證據；同樣有 retrieval 費用。
>
> **考點**：SAA-4.1｜存取模式不可預測時使用 Intelligent-Tiering｜延伸閱讀：第 23 章

### 第 40 題｜SAA｜單選｜D3 讀取為主的查詢頁面

一家物流公司的公開貨件查詢頁面使用 RDS for PostgreSQL。尖峰時資料庫 CPU 使用率長時間超過 90%，Performance Insights 顯示 95% 的負載來自查詢貨件狀態的讀取；貨件狀態延遲幾秒鐘再顯示是可以接受的。公司希望擴展讀取能力，並保留未來繼續擴展的空間。

哪一種做法最合適？

- A. 把 instance 修改為 Multi-AZ deployment，讓 standby 分擔讀取
- B. 把 instance 升級到最大的 instance size
- C. 把貨件資料遷移到 DynamoDB，改寫查詢程式
- D. 建立多個 read replica，讓查詢頁面的讀取流量改連 read replica

> [!answer]- 答案：D
> **A ✗** RDS Multi-AZ instance deployment 的 standby 只用於 failover，不接受讀取流量。（Multi-AZ DB cluster 的 reader instance 可讀，但那是另一種部署選項，題目的選項描述的是讓 standby 分擔讀取。）
>
> **B ✗** 垂直擴展可以暫時舒緩，但有上限，成本隨 instance size 快速增加，無法滿足「保留未來繼續擴展的空間」。
>
> **C ✗** DynamoDB 可以水平擴展，但要重新設計資料模型與改寫程式，對「讀取量大」這個問題是過度的改造。
>
> **D ✓** Read replica 以非同步方式複寫主資料庫，可以承接讀取流量；題目允許數秒延遲，正好能接受複寫延遲。RDS for PostgreSQL 可以建立多個 read replica，隨流量增加再加開，主資料庫只處理寫入。應用程式只需把讀取查詢改連 replica 的 endpoint。
>
> **考點**：SAA-3.3｜Read replica 擴展可容忍延遲的讀取｜延伸閱讀：第 26 章

### 第 41 題｜SAA｜單選｜D1 強制資料庫連線加密

一家連鎖餐飲集團的會員資料庫使用 RDS for PostgreSQL。新的資安規範要求所有資料庫連線都必須使用 TLS 加密，但稽核發現部分舊的報表工具仍以未加密的方式連線。集團希望由資料庫端直接拒絕任何未加密的連線。

應該怎麼做？

- A. 在 DB instance 使用的 custom DB parameter group 中把 `rds.force_ssl` 設為 1，並把 RDS 的 CA 憑證提供給各用戶端
- B. 為資料庫啟用以 KMS 加密的 storage encryption
- C. 修改資料庫的 security group，只允許來自應用程式 security group 的 5432 port
- D. 為資料庫啟用 IAM database authentication，讓用戶端改用 IAM 產生的驗證 token

> [!answer]- 答案：A
> **A ✓** `rds.force_ssl` 設為 1 後，RDS for PostgreSQL 會拒絕所有非 TLS 的連線。用戶端應安裝 RDS 的 CA 憑證並驗證伺服器憑證，才能防止中間人攻擊。較新的 PostgreSQL 主要版本預設值已是 1，但既有 instance 與舊版本仍需要確認設定。
>
> **B ✗** Storage encryption 保護的是靜態資料（磁碟、snapshot、備份），與傳輸中的連線是否加密無關。
>
> **C ✗** Security group 控制「誰能連」，不控制連線是否加密；舊工具若在允許的來源中，仍可明文連線。
>
> **D ✗** IAM database authentication 的連線本身要求使用 TLS，但它不會禁止其他仍使用密碼登入的帳號以明文連線，無法「拒絕任何未加密的連線」。
>
> **考點**：SAA-1.3｜以 parameter group 強制 RDS 傳輸加密｜延伸閱讀：第 26 章、第 15 章

### 第 42 題｜SAA｜單選｜D2 空氣品質感測資料分流

一座城市有 50,000 個空氣品質感測器以 MQTT 把讀數送到 AWS IoT Core。城市需要同時完成三件事：把每一筆讀數存入 S3 data lake、把 PM2.5 超過門檻的讀數即時送到告警用的 Lambda 函式、把每個感測器的最新數值更新到一張 DynamoDB table 供地圖查詢。城市希望各個處理路徑彼此鬆耦合，並且不管理任何伺服器。

哪一種設計最合適？

- A. 在 EC2 上自建 MQTT broker 叢集，由自訂程式訂閱主題後寫入三個目的地
- B. 修改感測器韌體，讓每個感測器各自用 SDK 寫入 S3、DynamoDB 並呼叫 Lambda
- C. 使用 IoT Core rules engine 建立三條 rule：一條把所有讀數送到 Data Firehose 寫入 S3，一條以 `WHERE` 條件篩選 PM2.5 超標的讀數觸發 Lambda，一條以 DynamoDB action 更新最新數值
- D. 建立一條 IoT Core rule 把所有讀數送到單一 Lambda 函式，由函式依序寫入 S3、判斷門檻並更新 DynamoDB

> [!answer]- 答案：C
> **A ✗** 自建 broker 叢集要處理擴展、高可用、憑證與修補，違反「不管理任何伺服器」的要求，而 IoT Core 本身就是受管的 MQTT broker。
>
> **B ✗** 讓每個裝置直接寫多個目的地，裝置需要更多憑證與邏輯，韌體變複雜；任何目的地調整都要更新 50,000 台裝置的韌體，耦合度最高。
>
> **C ✓** IoT Core rules engine 以類 SQL 的語法對主題訊息做篩選與轉換，並直接把結果送到 Firehose、Lambda、DynamoDB 等受管目的地。三條 rule 互相獨立，修改或新增一條路徑不影響其他路徑，也不需要伺服器。
>
> **D ✗** 單一 Lambda 函式把三件事綁在一起：任何一步失敗都會影響其他步驟，50,000 個感測器的持續流量也會帶來大量 Lambda 呼叫成本。若處理邏輯真的需要跨目的地的交易性，才考慮集中在程式中。
>
> **考點**：SAA-2.1｜IoT Core rules engine 鬆耦合地路由裝置資料｜延伸閱讀：第 31 章

### 第 43 題｜SAA｜單選｜D4 架構持續演進中的運算折扣

一家旅館集團在兩個 Region 有穩定的運算基線用量。目前主要跑在 m5 與 m6i 系列的 EC2 instance 上，但架構團隊計畫在未來一年內把部分服務改為 Graviton instance，並把另一部分遷移到 Fargate 與 Lambda。集團希望承諾 1 年期，取得折扣的同時保留最大的彈性。

應該購買哪一種方案？

- A. EC2 Instance Savings Plans
- B. 1 年期 Standard Reserved Instances
- C. 1 年期 Convertible Reserved Instances
- D. Compute Savings Plans

> [!answer]- 答案：D
> **A ✗** EC2 Instance Savings Plans 綁定特定 Region 的特定 instance family，折扣較高，但 m6i 換成 Graviton 系列或改用 Fargate／Lambda 後就無法套用。
>
> **B ✗** Standard RI 綁定 instance 屬性，彈性最低，也不涵蓋 Fargate 與 Lambda。
>
> **C ✗** Convertible RI 可以換成其他 instance family，但只適用於 EC2，不涵蓋 Fargate 與 Lambda，交換也需要人工操作。
>
> **D ✓** Compute Savings Plans 承諾的是每小時的運算花費，自動套用於任何 Region、任何 instance family、作業系統與租用方式的 EC2，也涵蓋 Fargate 與 Lambda，最適合架構還在演進的環境。代價是折扣略低於 EC2 Instance Savings Plans。
>
> **考點**：SAA-4.2｜Compute Savings Plans 涵蓋 EC2、Fargate、Lambda｜延伸閱讀：第 39 章

### 第 44 題｜SAA｜單選｜D1 無 Internet 的 subnet 存取 SQS

一家智慧倉儲公司的機器人控制服務部署在 private subnet 的 EC2 instance 上。資安政策禁止這些 subnet 有任何通往 Internet 的路徑，包括 NAT Gateway。現在服務需要把任務訊息送到 Amazon SQS，資安團隊也要求只能存取公司指定的 queue。

應該怎麼做？

- A. 建立 SQS 的 gateway VPC endpoint，並在 private subnet 的 route table 加入對應路由
- B. 建立 SQS 的 interface VPC endpoint 並啟用 private DNS，endpoint 的 security group 允許來自 instance 的 443，並以 endpoint policy 限制只能存取指定的 queue
- C. 建立 NAT Gateway，並以 security group 限制 instance 只能連到 SQS 的 IP 範圍
- D. 為 instance 配置 IPv6 位址，並透過 egress-only Internet Gateway 存取 SQS

> [!answer]- 答案：B
> **A ✗** Gateway endpoint 只支援 S3 與 DynamoDB，SQS 沒有 gateway endpoint。
>
> **B ✓** Interface endpoint 在 subnet 中建立 network interface，透過 PrivateLink 連到 SQS，流量不經過 Internet。啟用 private DNS 後，SDK 使用預設的 SQS 網域名稱就會解析到 endpoint 的私有 IP，程式不必修改。Endpoint policy 可以限制只能對指定 queue 的 ARN 執行動作。
>
> **C ✗** NAT Gateway 就是通往 Internet 的路徑，直接違反資安政策。
>
> **D ✗** Egress-only Internet Gateway 讓 IPv6 流量可以主動連到 Internet，同樣違反政策。
>
> **考點**：SAA-1.2、SAA-3.4｜Interface endpoint 與 endpoint policy｜延伸閱讀：第 6 章

### 第 45 題｜SAA｜單選｜D3 HPC 叢集的高效能共享檔案系統

一家生技公司在 EC2 上執行分子動力學與基因組組裝的 HPC 工作，數百個節點需要同時讀寫一個 POSIX 相容的共享檔案系統，要求數百 GB/s 的總吞吐量與次毫秒延遲。輸入資料存放在 S3 bucket，運算結果也要寫回 S3；檔案系統只在每次運算期間需要。

哪一種儲存最合適？

- A. Amazon FSx for Lustre，並以 data repository association 連結 S3 bucket
- B. Amazon EFS，使用 Max I/O 效能模式
- C. 在每個節點上以 Mountpoint for Amazon S3 掛載 bucket
- D. Amazon FSx for Windows File Server

> [!answer]- 答案：A
> **A ✓** FSx for Lustre 是為 HPC 與機器學習設計的平行檔案系統，總吞吐量可擴展到數百 GB/s、提供次毫秒延遲。Data repository association 讓檔案系統呈現 S3 中的物件，首次存取時載入，並可把結果匯出回 S3。運算期間建立、結束後刪除，只為使用的時間付費。
>
> **B ✗** EFS 是通用的共享檔案系統，適合 web 內容、home directory 等工作，但在這種高度平行的 HPC 情境下，吞吐量與延遲比不上 Lustre，也沒有與 S3 的原生資料儲存庫連結。
>
> **C ✗** Mountpoint for S3 讓應用程式以檔案方式讀取 S3，適合大量循序讀取；但它不是完整的 POSIX 檔案系統（例如不支援修改既有檔案、rename 等操作），不適合多節點同時讀寫的 HPC 工作。
>
> **D ✗** FSx for Windows File Server 提供 SMB 協定的 Windows 檔案共享，不是 Linux HPC 叢集的平行檔案系統。
>
> **考點**：SAA-3.1｜FSx for Lustre 搭配 S3 的 HPC 暫存檔案系統｜延伸閱讀：第 24 章

### 第 46 題｜SAA｜選兩項｜D2 單機系統升級為高可用

一個縣政府的建照申請系統目前運行在單一 AZ 的一台 EC2 instance 上，資料庫是同一個 AZ 的單一 RDS for MySQL instance。上次 AZ 故障時系統停擺半天。縣政府要求系統在單一 AZ 故障時能自動繼續服務，並希望對應用程式的修改越少越好。應用程式本身是無狀態的，上傳的檔案已存放在 S3。

哪兩個變更組合起來能滿足需求？（選兩項）

- A. 建立跨至少兩個 AZ 的 Auto Scaling group，最小容量為 2，前面放 Application Load Balancer
- B. 把 RDS instance 修改為 Multi-AZ deployment
- C. 把 EC2 instance 升級為更大的 instance type
- D. 每天把 EBS snapshot 複製到另一個 Region
- E. 為 instance 配置 Elastic IP，故障時由值班人員重新綁定到新 instance

> [!answer]- 答案：A、B
> **A ✓** 應用程式無狀態，可以直接水平擴展到多個 AZ。ALB 只把流量送到健康的 instance，ASG 會在故障 AZ 之外補足容量，Web 層不再有單點故障。
>
> **B ✓** Multi-AZ 讓資料庫在另一個 AZ 有同步 standby，AZ 故障時自動 failover，endpoint 不變，應用程式不用修改連線設定。
>
> **C ✗** 更大的 instance 仍在單一 AZ，AZ 故障時一樣停擺。
>
> **D ✗** 跨 Region snapshot 是災難復原的備份手段，需要人工還原，不是「自動繼續服務」。
>
> **E ✗** 人工重新綁定 Elastic IP 不是自動恢復，而且新的 instance 仍需要事先準備好。
>
> **考點**：SAA-2.2｜Web 層跨 AZ 加上資料庫 Multi-AZ｜延伸閱讀：第 18 章、第 26 章

### 第 47 題｜SAA｜單選｜D1 分享加密的資料庫 snapshot

一個城市運輸局的 RDS for PostgreSQL 使用 AWS managed key（`aws/rds`）加密。稽核單位位於同一個 organization 的另一個 AWS 帳號，需要每月取得一份資料庫 snapshot，並能在自己的帳號中還原成資料庫進行查核。運輸局嘗試分享 snapshot 時失敗。

應該怎麼做？

- A. 把 snapshot 設為 public，再讓稽核帳號複製後立即改回 private
- B. 修改 `aws/rds` 的 key policy，加入稽核帳號的存取權限
- C. 以一把 customer managed key 複製 snapshot，在 key policy 中授權稽核帳號使用這把 key，再把複製後的 snapshot 分享給稽核帳號
- D. 把 snapshot 匯出成 Parquet 檔案到 S3，再以 bucket policy 允許稽核帳號讀取

> [!answer]- 答案：C
> **A ✗** 加密的 snapshot 不能設為 public；即使是未加密的 snapshot，公開資料庫內容也是嚴重的資安事故。
>
> **B ✗** AWS managed key 的 key policy 由 AWS 管理，無法修改，所以以它加密的 snapshot 無法跨帳號分享。
>
> **C ✓** 跨帳號分享加密 snapshot 的前提是使用 customer managed key，並在 key policy 中允許目標帳號使用（例如 `kms:Decrypt`、`kms:CreateGrant`、`kms:DescribeKey`）。運輸局先以 CMK 複製 snapshot 再分享；稽核帳號通常會再以自己的 key 複製一份後還原。
>
> **D ✗** 匯出到 S3 的 Parquet 檔案可以用 Athena 分析，但無法還原成資料庫，不符合「還原成資料庫查核」的要求。
>
> **考點**：SAA-1.3｜以 AWS managed key 加密的 snapshot 無法跨帳號分享｜延伸閱讀：第 26 章、第 15 章

### 第 48 題｜SAA｜單選｜D4 穩定流量的 DynamoDB 費用

一家物流公司的路線規劃服務使用一張 DynamoDB table，全天候都有穩定流量，約 10,000 RCU 與 3,000 WCU，每日波動在 ±15% 以內，而且這個用量預期會持續數年。這張 table 目前使用 on-demand capacity mode，是帳單中最大的單項。

哪一種做法最划算？

- A. 維持 on-demand，並在 table 前加上 DAX 叢集減少讀取請求
- B. 把 table class 改為 Standard-Infrequent Access
- C. 把 table 轉為 global table，分散讀寫到兩個 Region
- D. 改為 provisioned capacity mode 並啟用 auto scaling，再為穩定的基線購買 reserved capacity

> [!answer]- 答案：D
> **A ✗** DAX 可以減少讀取請求，但 DAX 叢集本身有 node 費用，而且寫入完全不受影響；對穩定流量而言，切換 capacity mode 是更直接的節省方式。若讀取高度集中在少量熱點資料，DAX 才可能划算。
>
> **B ✗** Standard-IA 降低的是儲存費用，讀寫單價反而更高，這張 table 的成本來自讀寫，會更貴。
>
> **C ✗** Global table 會在另一個 Region 複寫所有寫入，成本增加而不是減少。
>
> **D ✓** On-demand 的優勢是應付不可預測的流量；流量穩定且可預測時，provisioned capacity 的單位成本較低，auto scaling 處理 ±15% 的波動。長期穩定的基線再購買 reserved capacity，可以取得更多折扣。
>
> **考點**：SAA-4.3｜穩定可預測流量用 provisioned + reserved capacity｜延伸閱讀：第 27 章、第 39 章

### 第 49 題｜SAA｜單選｜D2 每間客房的狀態依序處理

一家度假村集團有 40,000 間客房，房務、櫃台與維修系統會不斷送出客房狀態更新（打掃中、已入住、維修中）。同一間客房的更新必須依送出順序處理，不同客房可以平行處理；目前使用 SQS standard queue，偶爾出現順序錯亂與重複處理，導致客房狀態顯示錯誤。

哪一種做法最合適？

- A. 改用 SQS FIFO queue，所有訊息使用同一個 message group ID 以確保全域順序
- B. 改用 SQS FIFO queue，以客房 ID 作為 message group ID 並提供 deduplication ID，必要時啟用 high throughput mode
- C. 維持 standard queue，在 consumer 中比對訊息時間戳記，丟棄比資料庫現有狀態更舊的更新
- D. 改用 SNS standard topic，讓每個 consumer 直接訂閱並即時處理

> [!answer]- 答案：B
> **A ✗** 單一 message group 會讓所有客房的更新排成一條隊伍，一次只能處理一則，吞吐量受限，也沒有必要，因為只需要同一間客房內有序。
>
> **B ✓** FIFO queue 在同一個 message group 內保證順序，不同 group 之間可以平行處理；以客房 ID 作為 group，就同時得到「同房有序、跨房平行」。Deduplication ID 在 5 分鐘的去重區間內去除生產者重複送出的訊息。High throughput mode 提高 FIFO 的吞吐上限。
>
> **C ✗** 時間戳記比對可以緩解部分順序問題，但不同系統的時鐘可能不同步，也無法處理重複投遞造成的副作用；把順序邏輯放進每個 consumer 增加複雜度。若下游本來就具備冪等寫入，這可以作為補強，而非主要解法。
>
> **D ✗** SNS standard topic 不保證順序，也沒有讓 consumer 依自己速度處理的緩衝區。
>
> **考點**：SAA-2.1｜FIFO message group ID 決定順序範圍｜延伸閱讀：第 32 章

### 第 50 題｜SAA｜單選｜D3 偏遠地區的大型檔案上傳

一個中央部會的稽查人員在偏遠離島與山區以筆電把 2–5 GB 的稽查影片上傳到 S3。法規規定這些影片只能存放在指定的 Region，而該 Region 距離稽查人員很遠，透過 Internet 上傳常常要數小時，也容易失敗。部會希望以最少的修改改善上傳速度與成功率。

哪一種做法最合適？

- A. 在 bucket 啟用 S3 Transfer Acceleration，上傳工具改用 accelerate endpoint 並使用 multipart upload
- B. 在離稽查人員較近的 Region 建立 bucket 接收上傳，再以 Cross-Region Replication 複寫到指定 Region
- C. 把物件依日期分散到多個 prefix，提高 bucket 的請求效能
- D. 為每台筆電建立 Site-to-Site VPN 連到指定 Region 的 VPC，再經由 gateway endpoint 上傳

> [!answer]- 答案：A
> **A ✓** Transfer Acceleration 讓用戶端連到最近的 edge location，資料再經 AWS 骨幹網路送到 bucket 所在的 Region，長距離傳輸的速度與穩定性通常明顯改善；bucket 仍在指定 Region。Multipart upload 讓大檔案分段平行上傳，單段失敗只需重傳該段。只需啟用功能並改用 accelerate endpoint，修改最少。
>
> **B ✗** 先上傳到其他 Region 的 bucket，等於把影片存放在指定 Region 以外，違反法規。
>
> **C ✗** Prefix 分散解決的是單一 prefix 請求速率過高的問題，本題的瓶頸是長距離網路傳輸。
>
> **D ✗** Site-to-Site VPN 需要有固定公網 IP 的客戶閘道設備，不適合在各地移動的筆電，而且 VPN 仍走 Internet；從地端經 VPN 也無法使用 gateway endpoint 存取 S3。
>
> **考點**：SAA-3.4、SAA-3.1｜Transfer Acceleration 改善長距離上傳｜延伸閱讀：第 22 章

### 第 51 題｜SAA｜單選｜D1 地端儀器伺服器的 AWS 憑證

一個基因研究所的定序儀控制伺服器位於地端機房，每次定序完成後會以腳本把資料上傳到 S3。腳本目前使用存放在設定檔中的 IAM user access key，已經三年沒有輪替。研究所已有內部 PKI，會為每台伺服器簽發 X.509 憑證。資安團隊要求移除所有長期 AWS 憑證，並希望沿用既有的憑證體系。

哪一種做法最合適？

- A. 把 access key 移到 Secrets Manager，並設定每 90 天自動輪替
- B. 為地端伺服器建立 EC2 instance profile，讓伺服器自動取得臨時憑證
- C. 使用 IAM Roles Anywhere：以研究所的 CA 建立 trust anchor，設定 profile 對應到只能寫入指定 bucket 的 IAM role，伺服器以自己的憑證透過 credential helper 換取臨時憑證
- D. 在 IAM Identity Center 中為每台伺服器建立使用者，讓腳本以 SSO 登入取得憑證

> [!answer]- 答案：C
> **A ✗** 輪替可以降低外洩的影響，但伺服器上仍然保存長期 access key，不符合「移除所有長期 AWS 憑證」。
>
> **B ✗** Instance profile 只能附加在 EC2 instance 上，地端伺服器無法使用。
>
> **C ✓** IAM Roles Anywhere 讓 AWS 以外的工作負載使用 X.509 憑證證明身份：trust anchor 信任研究所的 CA，profile 指定可以取得的 role，伺服器以 credential helper 簽章換取臨時憑證，AWS CLI 與 SDK 可透過 `credential_process` 自動使用。伺服器上不再有長期 AWS 金鑰，憑證撤銷也沿用既有 PKI 流程。
>
> **D ✗** IAM Identity Center 是給人員以互動方式登入的，伺服器腳本無法完成瀏覽器式的 SSO 流程，也不適合把機器當成使用者管理。
>
> **考點**：SAA-1.1｜IAM Roles Anywhere 讓地端工作負載取得臨時憑證｜延伸閱讀：第 13 章、第 12 章

### 第 52 題｜SAA｜單選｜D2 資料庫維護期間的資料遺失

一個城市公車動態系統中，每輛公車每 10 秒透過 API Gateway 呼叫 Lambda，Lambda 直接把位置寫入 RDS 資料庫。每次資料庫進行維護或 failover 的一到兩分鐘內，寫入都會失敗，這段時間的位置資料全部遺失；早晚尖峰也偶爾因連線數過多而寫入失敗。城市要求不遺失任何位置資料。

哪一種做法最合適？

- A. 在 Lambda 的 asynchronous invocation 設定中把重試次數調到最大
- B. 讓 API Gateway 把位置資料寫入 SQS queue，再由另一個 Lambda 函式從 queue 讀取寫入 RDS，處理失敗的訊息留在 queue 中重試，超過次數後進入 DLQ
- C. 把 RDS 改為 Multi-AZ deployment，縮短 failover 的時間
- D. 把 RDS 升級到更大的 instance size，提高可承受的連線數

> [!answer]- 答案：B
> **A ✗** API Gateway 是以同步方式呼叫 Lambda，asynchronous invocation 的重試設定不會生效；同步呼叫失敗後錯誤直接回給呼叫端。
>
> **B ✓** 以 SQS 作為緩衝，資料一進來就持久保存。資料庫無法寫入時，consumer 處理失敗，訊息在 visibility timeout 後重新可見並再次嘗試，維護結束後自動補寫；尖峰時也可以限制 consumer 的並行度，避免連線數爆滿。
>
> **C ✗** Multi-AZ 能讓 failover 自動完成，但 failover 期間仍有一到兩分鐘無法寫入，資料照樣遺失；資料庫維護時也一樣。它提升的是資料庫的可用性，不是寫入端的容錯。
>
> **D ✗** 更大的 instance 可能改善連線數上限，但無法處理維護與 failover 期間的寫入失敗。
>
> **考點**：SAA-2.2、SAA-2.1｜以 queue 讓寫入端容忍下游暫時故障｜延伸閱讀：第 32 章、第 34 章

### 第 53 題｜SAA｜選兩項｜D4 NAT Gateway 處理費過高

一家飯店集團的營收管理分析程式在 private subnet 的 EC2 instance 上執行，每月從同一個 Region 的 S3 讀取約 30 TB 的資料，並大量讀寫同一個 Region 的 DynamoDB table。所有流量都經過 NAT Gateway，帳單顯示 NAT Gateway 的資料處理費用非常高。

哪兩個做法最能降低這筆費用？（選兩項）

- A. 建立 S3 的 interface VPC endpoint，讓 S3 流量經由 PrivateLink 傳送
- B. 把 NAT Gateway 換成一台小型的 NAT instance
- C. 建立 S3 的 gateway VPC endpoint，並與 private subnet 的 route table 關聯
- D. 建立 DynamoDB 的 gateway VPC endpoint，並與 private subnet 的 route table 關聯
- E. 把分析 instance 移到 public subnet 並配置 public IP，直接經由 Internet Gateway 存取 S3 與 DynamoDB

> [!answer]- 答案：C、D
> **A ✗** S3 的 interface endpoint 可以運作，但有每小時與每 GB 的處理費用。它適合需要從地端或其他 VPC 經私有 IP 存取 S3 的情境；同一個 VPC 內的存取，gateway endpoint 更便宜。
>
> **B ✗** NAT instance 沒有資料處理費，但 30 TB 的流量會讓小型 instance 成為效能瓶頸，還要自行處理高可用與修補，以營運負擔換取成本並不划算。
>
> **C ✓** S3 gateway endpoint 沒有小時費也沒有資料處理費。關聯 route table 後，會加入指向 S3 prefix list 的路由，S3 流量不再經過 NAT Gateway。
>
> **D ✓** DynamoDB 是另一個支援 gateway endpoint 的服務，同樣免費，可以把 DynamoDB 流量從 NAT Gateway 移開。
>
> **E ✗** 改放 public subnet 雖然不經 NAT，但讓分析主機直接暴露在 Internet，增加攻擊面，以安全性換取成本不是合適的做法。
>
> **考點**：SAA-4.4｜Gateway endpoint 免費且可繞過 NAT Gateway｜延伸閱讀：第 6 章、第 39 章

### 第 54 題｜SAA｜單選｜D1 三層架構的最小網路權限

一個縣政府的線上繳費系統採用三層架構：public subnet 中的 ALB、private subnet 中由 Auto Scaling group 管理的應用程式 instance（監聽 8080 port），以及 isolated subnet 中的 RDS for PostgreSQL。資安要求應用程式 instance 只接受來自 ALB 的流量，資料庫只接受來自應用程式 instance 的連線。Instance 會隨流量增減，IP 位址經常變動。

哪一種設定最能滿足需求且管理負擔最低？

- A. 在各 subnet 的 network ACL 中以 subnet CIDR 設定允許規則，並開放回程使用的 ephemeral ports
- B. 應用程式的 security group 允許來自 ALB 所在 public subnet CIDR 的 8080，資料庫的 security group 允許來自應用程式 subnet CIDR 的 5432
- C. 應用程式與資料庫的 security group 都允許來自 `0.0.0.0/0` 的流量，依靠 private subnet 沒有 Internet 路由來保護
- D. 應用程式的 security group 允許來自 ALB security group 的 8080，資料庫的 security group 允許來自應用程式 security group 的 5432

> [!answer]- 答案：D
> **A ✗** NACL 是 subnet 層級、stateless 的規則，必須同時管理入站與回程的 ephemeral ports，而且以 CIDR 為單位，subnet 內的任何資源都被允許，粒度粗、管理負擔高。NACL 適合作為額外的粗粒度防線，而不是主要的最小權限機制。
>
> **B ✗** 以 subnet CIDR 授權可以運作，但 public subnet 中的任何其他資源（例如之後在該 subnet 新增的 instance）也會被允許，範圍比「只來自 ALB」寬；以 CIDR 授權資料庫也有同樣的問題。
>
> **C ✗** 沒有 Internet 路由不代表安全，同一個 VPC 或相連網路中的任何資源都能連到這些 instance 與資料庫，完全違反最小權限。
>
> **D ✓** Security group 可以引用另一個 security group 作為來源，意思是「附加了該 security group 的任何網路介面」。Instance 擴縮、IP 改變都不需要修改規則，而且只有 ALB 與應用程式 instance 能符合條件。
>
> **考點**：SAA-1.2｜以 security group 引用建立分層的最小權限｜延伸閱讀：第 6 章

### 第 55 題｜SAA｜單選｜D3 Lambda 大量連線耗盡資料庫

一家生技公司把 LIMS 的 API 改寫成 Lambda 函式，資料庫仍是 RDS for MySQL。每天早上檢體登錄的尖峰時段，數千個並行執行的函式各自開啟資料庫連線，資料庫頻繁回報 `Too many connections`，API 錯誤率升高。公司希望在不大幅改寫程式的情況下解決問題。

哪一種做法最合適？

- A. 在 Lambda 與資料庫之間建立 RDS Proxy，函式改連 proxy 的 endpoint
- B. 把資料庫的 `max_connections` 參數調到非常大的值
- C. 把函式的 reserved concurrency 設為 5，限制同時開啟的連線數
- D. 把函式改為每次呼叫結束前都關閉連線，下次呼叫再重新建立

> [!answer]- 答案：A
> **A ✓** RDS Proxy 維護一個與資料庫之間的連線池，大量 Lambda 的短連線由 proxy 多工使用少量資料庫連線，避免連線數爆滿；proxy 也能縮短 failover 時的中斷，並可整合 Secrets Manager 與 IAM 驗證。函式只需更換連線 endpoint。
>
> **B ✗** 每個連線都會消耗資料庫記憶體，盲目調高 `max_connections` 可能讓資料庫記憶體不足而更不穩定，根本問題（連線數隨並行度成長）沒有解決。
>
> **C ✗** 把並行度限制到 5，尖峰時大量請求會被 throttle，等於用拒絕服務換取資料庫穩定，使用者體驗嚴重下降。
>
> **D ✗** 每次呼叫都重新建立連線會增加延遲與資料庫的連線建立負擔，並行數量多時仍會同時存在大量連線。
>
> **考點**：SAA-3.3｜RDS Proxy 為 Lambda 提供連線池｜延伸閱讀：第 26 章、第 19 章

### 第 56 題｜SAA｜單選｜D2 非同步呼叫的失敗事件

一個智慧城市專案以 S3 event notification 非同步觸發 Lambda，處理噪音感測器上傳的資料檔。當函式因資料格式或下游錯誤失敗時，Lambda 重試後仍失敗的事件就會被丟棄，維運人員事後無從得知是哪些檔案沒有處理。團隊希望以最少的工作保存失敗的事件與錯誤資訊，以便修正後重新處理。

哪一種做法最合適？

- A. 在 S3 bucket 設定 dead-letter queue，讓 S3 在 Lambda 失敗時把事件送到 DLQ
- B. 把函式的非同步重試次數提高到 10 次，降低事件被丟棄的機率
- C. 為函式的非同步呼叫設定 on-failure destination，指向一個 SQS queue
- D. 在函式中以 try/catch 捕捉所有例外並寫入 CloudWatch Logs，再由人工搜尋日誌

> [!answer]- 答案：C
> **A ✗** S3 event notification 本身沒有 DLQ 設定；事件交給 Lambda 之後，失敗處理是 Lambda 非同步呼叫的責任。
>
> **B ✗** Lambda 非同步呼叫的重試次數可設定為 0–2 次，無法提高到 10 次；重試再多，持續性的錯誤仍會失敗。
>
> **C ✓** Lambda 的非同步呼叫可以設定 on-failure destination（SQS、SNS、EventBridge、Lambda 或 S3）。重試耗盡或事件超過最長存活時間後，Lambda 會把原始事件連同錯誤資訊送到 destination，修正程式後可以從 queue 重新處理。舊式的 Lambda DLQ 也能保存事件，但 destination 帶有更多執行結果的資訊。
>
> **D ✗** 日誌可以記錄錯誤，但要從大量日誌中找出失敗事件、再手動重新送出，營運負擔大且容易遺漏；函式本身若在初始化時就失敗，也來不及寫日誌。
>
> **考點**：SAA-2.1｜Lambda 非同步呼叫的 on-failure destination｜延伸閱讀：第 19 章

### 第 57 題｜SAA｜單選｜D1 多個研究團隊共用的 bucket

一家生技公司的基因體資料湖是一個大型 S3 bucket，15 個研究團隊各自使用不同的 prefix。這些團隊的 IAM role 分散在 organization 中不同的 AWS 帳號，有些團隊只能從特定 VPC 存取。目前所有規則都寫在同一份 bucket policy，已接近 bucket policy 的大小上限，每次修改都可能影響其他團隊。

哪一種做法最能簡化權限管理？

- A. 為每個團隊建立獨立的 bucket，並把對應 prefix 的資料複製過去
- B. 為每個團隊建立一個 S3 Access Point，各自設定 access point policy（需要時設定只允許特定 VPC 的 network origin），並把 bucket policy 改為把存取控制委派給 access point
- C. 為每個 prefix 下的物件設定 object ACL，授權對應團隊的帳號
- D. 移除 bucket policy，改為只在各團隊的 IAM role 上設定 identity policy

> [!answer]- 答案：B
> **A ✗** 拆成獨立 bucket 可以隔離權限，但要複製大量資料、維持同步，儲存成本倍增，也破壞了單一資料湖的設計。若資料本來就不需要共用，獨立 bucket 才是合理選擇。
>
> **B ✓** Access point 是 bucket 的具名存取入口，每個 access point 有自己的 policy 與網路來源設定（Internet 或指定 VPC）。每個團隊的規則各自獨立維護，不再擠在一份 bucket policy 中，修改也不會互相影響；bucket policy 只需一條委派敘述。
>
> **C ✗** 新 bucket 預設停用 ACL（Bucket owner enforced），AWS 也建議以 policy 取代 ACL；逐物件設定 ACL 的管理負擔更大，且無法表達 VPC 限制。
>
> **D ✗** 跨帳號存取需要資源擁有者的同意，只有 identity policy 而沒有 bucket policy（或 access point policy）授權，其他帳號的 role 無法存取這個 bucket。
>
> **考點**：SAA-1.1｜S3 Access Points 拆分大型共用 bucket 的權限｜延伸閱讀：第 22 章

### 第 58 題｜SAA｜單選｜D3 多 VPC 與機房的網路整合

一家物流公司在多個 AWS 帳號中共有 14 個 VPC，彼此以 full mesh 的 VPC peering 連接（共 91 條 peering），兩座地端資料中心則分別與每個 VPC 建立 Site-to-Site VPN。網路團隊抱怨路由表難以維護，新增 VPC 時要建立大量連線。公司希望改為 hub-and-spoke 架構、支援遞移路由，並讓開發環境的 VPC 無法連到正式環境的 VPC。

哪一種做法最合適？

- A. 保留 VPC peering，並在每個 VPC 的 route table 中加入經由中間 VPC 轉送的路由，讓流量可以遞移
- B. 建立一個 transit VPC，在其中部署自行管理的 EC2 路由器，所有 VPC 與地端都以 VPN 連到它
- C. 以 AWS PrivateLink 為每個 VPC 建立 endpoint service，讓所有 VPC 互相存取
- D. 建立 Transit Gateway 並以 AWS RAM 分享給各帳號，VPC 與 VPN 都連接到 Transit Gateway，正式與開發環境使用不同的 Transit Gateway route table

> [!answer]- 答案：D
> **A ✗** VPC peering 不支援遞移路由，流量不能經由第三個 VPC 轉送，路由表中加入這種路由也不會生效。
>
> **B ✗** Transit VPC 是 Transit Gateway 出現前的舊模式，需要自行管理 EC2 路由器的高可用、擴展與修補，營運負擔高。
>
> **C ✗** PrivateLink 提供的是單向、以服務為單位的存取（consumer 存取 provider 的特定服務），不是全面的網路互連，也無法取代地端 VPN 的路由。
>
> **D ✓** Transit Gateway 是 Regional 的路由中樞，VPC 與 VPN 都只需連一次，支援遞移路由；透過 RAM 可以讓其他帳號把 VPC 連到同一個 TGW。以不同的 TGW route table 與 association／propagation 設定，正式與開發環境可以各自連到地端，但彼此無法互通。
>
> **考點**：SAA-3.4｜Transit Gateway 的 hub-and-spoke 與 route table 隔離｜延伸閱讀：第 7 章

### 第 59 題｜SAA｜單選｜D4 只在上班時間忙碌的資料庫

一家生技公司的實驗排程系統使用 Aurora MySQL，目前是一台 db.r6g.2xlarge 的 provisioned instance 全天候運行。系統只在平日上班時間使用，夜間與週末幾乎沒有流量；週一早上常出現難以預測的瞬間尖峰。CloudWatch 顯示平均 CPU 使用率不到 15%。公司希望以最低成本運行，且不修改應用程式。

哪一種做法最合適？

- A. 把 instance 改為 Aurora Serverless v2，依負載設定最小與最大 ACU
- B. 為現有的 db.r6g.2xlarge 購買 1 年期 Reserved Instance
- C. 把資料遷移到 DynamoDB on-demand table
- D. 以排程在每天晚上停止 cluster、早上再啟動，其他時間維持現有 instance size

> [!answer]- 答案：A
> **A ✓** Aurora Serverless v2 依實際負載以細粒度調整容量（ACU），閒置時縮到設定的最小值，尖峰時在數秒內擴展，按每秒使用的 ACU 計費。它與 Aurora MySQL 相容，應用程式不用修改。較新的引擎版本還支援把最小容量設為 0 並自動暫停，閒置成本更低。
>
> **B ✗** RI 降低的是全天候運行的單價，但這台 instance 大部分時間閒置，平均使用率不到 15%，等於以折扣價支付大量閒置容量。
>
> **C ✗** 遷移到 DynamoDB 需要重新設計資料模型與改寫應用程式，違反「不修改應用程式」的限制。
>
> **D ✗** 夜間停止可以節省部分費用，但白天仍以過大的 instance 運行，週末也需要另外排程；週一的尖峰若超過這個 size 仍無法自動擴展。若工作時間固定、負載平穩，排程停止才是簡單有效的選擇。
>
> **考點**：SAA-4.3｜Aurora Serverless v2 對間歇且不可預測的負載最划算｜延伸閱讀：第 26 章、第 39 章

### 第 60 題｜SAA｜單選｜D2 有預算限制的跨 Region DR

一個城市的智慧號誌控制平台在單一 Region 運行，架構為 Auto Scaling group 中的 EC2 加上 Aurora MySQL。主管機關要求 Region 故障時，RTO 不超過 15 分鐘、RPO 不超過 1 分鐘。平台預算有限，目前只有每晚一次的備份。

哪一種 DR 策略能滿足要求且成本最低？

- A. Backup and restore：每小時把 Aurora snapshot 與 AMI 複製到 DR Region，事故時以 CloudFormation 重建整個環境
- B. Pilot light：只把 AMI 與 CloudFormation 範本準備在 DR Region，資料庫每小時複製一次 snapshot，事故時再啟動所有資源
- C. Warm standby：使用 Aurora Global Database 在 DR Region 建立 secondary cluster，並在 DR Region 以縮小規模的 ASG 持續運行應用程式，事故時提升資料庫並擴展 ASG，以 Route 53 切換流量
- D. Multi-site active-active：兩個 Region 都以完整容量運行並同時服務流量，資料庫使用雙向複寫

> [!answer]- 答案：C
> **A ✗** 每小時複製 snapshot 代表 RPO 最多一小時；從零重建整個環境與還原資料庫，通常也遠超過 15 分鐘。
>
> **B ✗** 這個選項的資料庫仍只是每小時複製 snapshot，RPO 不符合 1 分鐘。真正的 pilot light 會讓核心資料持續複寫，但應用程式層要事故時才啟動，RTO 常在數十分鐘以上，難以穩定達到 15 分鐘。
>
> **C ✓** Aurora Global Database 的跨 Region 複寫延遲通常在 1 秒內，滿足 RPO；DR Region 已有縮小規模、持續運行並經過驗證的應用程式，事故時只需提升資料庫並擴展容量，能在 15 分鐘內完成切換。成本比完整的 active-active 低得多。
>
> **D ✗** Active-active 可以滿足需求，但兩邊都以完整容量運行，成本最高，不符合「成本最低」。只有在 RTO 接近零或需要全球低延遲時才值得採用。
>
> **考點**：SAA-2.2｜依 RTO／RPO 選擇最低成本的 DR 策略｜延伸閱讀：第 34 章

### 第 61 題｜SAA｜單選｜D3 可預測尖峰的 cold start

一家連鎖飯店的行動 App 退房 API 以 Node.js 的 Lambda 函式實作。函式初始化時要載入大型的計價規則檔，cold start 約 4 秒。每天早上 7:00–10:00 是退房尖峰，並行量會在幾分鐘內從個位數增加到數百；飯店要求這段期間 p99 延遲低於 1 秒，其他時段流量很低，不希望全天支付額外費用。

哪一種做法最合適？

- A. 把函式的記憶體設定從 512 MB 提高到 10,240 MB
- B. 為函式的 alias 設定 provisioned concurrency，並以 Application Auto Scaling 的 scheduled scaling 只在尖峰時段提高數量
- C. 為函式設定 reserved concurrency，保留數百個並行額度給這個函式
- D. 以 EventBridge Scheduler 每 5 分鐘呼叫一次函式，保持執行環境溫熱

> [!answer]- 答案：B
> **A ✗** 更多記憶體會分配更多 CPU，可能縮短初始化時間，但無法消除數百個新執行環境同時 cold start 的問題，也會提高全天的單位費用。
>
> **B ✓** Provisioned concurrency 讓指定數量的執行環境預先完成初始化，請求進來時直接處理，沒有 cold start。它必須設定在版本或 alias 上；搭配 Application Auto Scaling 的排程，只在 7:00–10:00 前提高數量、之後降回，費用只發生在尖峰時段。
>
> **C ✗** Reserved concurrency 保留並限制函式的最大並行量，確保不被其他函式搶走額度，但不會預先初始化執行環境，cold start 依舊存在。
>
> **D ✗** 定期呼叫只能讓少數幾個執行環境保持溫熱，尖峰時新增的數百個並行請求仍會遇到 cold start，這種做法也不可靠。
>
> **考點**：SAA-3.2｜Provisioned concurrency 搭配排程消除可預測尖峰的 cold start｜延伸閱讀：第 19 章

### 第 62 題｜SAA｜選兩項｜D4 長期保存的原始定序資料

一家生技公司有約 2 PB 的原始定序檔案（FASTQ）。檔案在產生後的 60 天內會被頻繁分析，之後很少使用，偶爾在研究需要時重新分析整批資料，研究人員可以接受 48 小時內取得。法規要求保存 10 年。公司希望把儲存成本降到最低。

哪兩個做法組合起來最合適？（選兩項）

- A. 以 lifecycle rule 在 60 天後把物件轉移到 S3 Glacier Instant Retrieval
- B. 以 lifecycle rule 在 60 天後把物件轉移到 S3 Glacier Deep Archive
- C. 以 lifecycle rule 在 60 天後把物件轉移到 S3 Standard-IA，並一直保存在該層
- D. 需要重新分析時，以 Expedited retrieval 從 Deep Archive 取回資料
- E. 需要重新分析時，以 S3 Batch Operations 對整批物件發起 Bulk retrieval 的 restore 請求

> [!answer]- 答案：B、E
> **A ✗** Glacier Instant Retrieval 提供毫秒級取回，但儲存單價比 Deep Archive 高得多；本題可以等 48 小時，不需要為立即取回付費。
>
> **B ✓** Deep Archive 是 S3 中儲存單價最低的類別，適合長期保存、很少存取、可以等待數小時以上的資料；10 年保存期也遠超過它 180 天的最短儲存期限。
>
> **C ✗** Standard-IA 的儲存單價遠高於 Deep Archive，對 10 年幾乎不讀取的 2 PB 資料來說成本過高。
>
> **D ✗** Deep Archive 不提供 Expedited retrieval，只有 Standard（通常 12 小時內）與 Bulk（通常 48 小時內）兩種。
>
> **E ✓** Bulk retrieval 是 Deep Archive 取回費用最低的方式，通常在 48 小時內完成，符合研究人員的等待容忍度。S3 Batch Operations 可以一次對數百萬個物件發起 restore，不必自己寫迴圈呼叫 API。
>
> **考點**：SAA-4.1｜Deep Archive 搭配 Bulk retrieval 與 Batch Operations｜延伸閱讀：第 23 章

### 第 63 題｜SAA｜單選｜D4 熱門會議影片的傳出費用

一個市議會把議事錄影以 HLS 格式存放在 S3，目前由 EC2 web server 從 S3 讀取後提供給市民觀看。熱門議題開會時同時觀看人數暴增，EC2 負載與 data transfer out 費用都很高。議會希望降低傳出費用與伺服器負擔，並讓各地市民觀看更順暢。

哪一種做法最合適？

- A. 把 EC2 web server 升級為網路效能更高的 instance type
- B. 在 S3 bucket 啟用 Transfer Acceleration，讓市民透過 accelerate endpoint 觀看
- C. 建立 AWS Global Accelerator，把 EC2 web server 設為 endpoint
- D. 建立 CloudFront distribution，以 S3 為 origin 並使用 OAC，市民改從 CloudFront 觀看

> [!answer]- 答案：D
> **A ✗** 更大的 instance 能承受更多流量，但每一位觀眾仍從 origin 下載完整影片，傳出費用與流量成正比，沒有降低。
>
> **B ✗** Transfer Acceleration 是為長距離傳輸到 S3 設計的，會額外收取加速費，沒有快取效果，觀看人數越多費用越高。
>
> **C ✗** Global Accelerator 改善的是網路路徑，不快取內容，每個請求仍回到 EC2，伺服器負擔與傳出流量都沒有減少，還多了加速器的費用。
>
> **D ✓** CloudFront 在 edge location 快取 HLS 片段，大量市民觀看同一場會議時，絕大部分請求由 edge 回應，S3 只需提供少量回源流量；從 S3 到 CloudFront 的傳輸不收 data transfer out 費用，CloudFront 對外的傳輸費率通常也低於從 Region 直接傳出。EC2 可以從播放路徑中移除，OAC 確保 bucket 不需公開。
>
> **考點**：SAA-4.4、SAA-3.4｜CloudFront 快取降低傳出費用與 origin 負擔｜延伸閱讀：第 11 章、第 39 章

### 第 64 題｜SAA｜單選｜D3 感測資料的 DynamoDB key 設計

一座城市有 200,000 盞智慧路燈，每盞每分鐘寫入一筆狀態到 DynamoDB。主要的查詢有兩種：查詢某盞路燈最近 24 小時的所有讀數，以及查詢某盞路燈的最新狀態。目前的 table 以日期（`YYYY-MM-DD`）作為 partition key、路燈 ID 作為 sort key，寫入經常被 throttle，即使 table 的總容量還很充足。

哪一種 key 設計最合適？

- A. 以路燈 ID 作為 partition key、時間戳記作為 sort key；以 key condition 查詢時間區間，查詢最新狀態時以反向排序並設定 `Limit` 為 1
- B. 以時間戳記（精確到分鐘）作為 partition key、路燈 ID 作為 sort key
- C. 保留現有的 key，另外建立一個以路燈 ID 為 partition key 的 global secondary index
- D. 保留現有的 key，把 table 的 provisioned WCU 提高一倍

> [!answer]- 答案：A
> **A ✓** 以路燈 ID 作為 partition key，200,000 個不同的值讓寫入平均分散到大量 partition，消除熱點。同一盞路燈的資料依時間戳記排序，`Query` 加上 `BETWEEN` 就能取得最近 24 小時；`ScanIndexForward=false` 加上 `Limit=1` 直接取得最新一筆。
>
> **B ✗** 每分鐘的所有寫入共用同一個 partition key，每分鐘都會有一個熱點，throttle 問題依舊。
>
> **C ✗** GSI 能新增查詢方式，但 base table 的寫入仍集中在「今天」這個 partition key，throttle 發生在 base table，GSI 無法解決。
>
> **D ✗** 單一 partition 的吞吐量有上限，所有當日寫入都打在同一個 partition key 上時，提高整張 table 的容量也無法突破這個限制。題目說「總容量還很充足」，就是熱分割的訊號。
>
> **考點**：SAA-3.3｜高基數 partition key 分散寫入並支援時間區間查詢｜延伸閱讀：第 27 章

### 第 65 題｜SAA｜單選｜D3 突發吞吐量的共享檔案系統

一個警察局以多個 AZ 的 ECS task 共用一個 Amazon EFS 檔案系統，處理警用密錄器上傳的影片。平時幾乎閒置，但發生重大事件時會在短時間內湧入大量影片，需要很高的讀寫吞吐量。目前使用 Bursting throughput mode，因為檔案系統資料量不大，burst credit 很快用完，處理速度掉到很低。警察局希望吞吐量能自動隨工作負載擴展，只為實際使用付費，並且不必做容量規劃。

哪一種做法最合適？

- A. 改用 Provisioned throughput mode，並設定為事件尖峰所需的吞吐量
- B. 在檔案系統中寫入大量填充檔案，提高 Bursting mode 的基線吞吐量
- C. 改用 Elastic throughput mode
- D. 改用 io2 volume 搭配 EBS Multi-Attach，讓所有 task 共用同一個 volume

> [!answer]- 答案：C
> **A ✗** Provisioned throughput 能提供穩定的高吞吐量，但無論是否使用都要為設定值付費，大部分時間閒置時並不划算。若工作負載長期穩定且需要高吞吐量，Provisioned 才合適。
>
> **B ✗** Bursting mode 的基線吞吐量與儲存量成正比，填充檔案是過去的權宜做法，要為不需要的儲存付費，也不是自動擴展。
>
> **C ✓** Elastic throughput 會依工作負載自動擴展讀寫吞吐量，按實際傳輸的資料量計費，適合突發、難以預測的工作負載，不需要容量規劃。
>
> **D ✗** EBS Multi-Attach 只能在同一個 AZ 內掛載，需要叢集感知的檔案系統才能安全地多方同時寫入，也不支援跨 AZ 的 ECS task，完全不適合這個情境。
>
> **考點**：SAA-3.1、SAA-4.1｜EFS Elastic throughput 用於突發且不可預測的負載｜延伸閱讀：第 24 章

## 答案速查與 Domain 分析

| 題號 | 答案 | Domain | Task | 相關章節 |
|---|---|---|---|---|
| 1 | C | D2 | SAA-2.1 | 第 32、20 章 |
| 2 | B | D1 | SAA-1.1 | 第 12、15 章 |
| 3 | D | D3 | SAA-3.5 | 第 31 章 |
| 4 | A | D4 | SAA-4.1 | 第 15、22 章 |
| 5 | A、D | D1 | SAA-1.2 | 第 19、5 章 |
| 6 | B | D2 | SAA-2.2 | 第 26、34 章 |
| 7 | C | D1 | SAA-1.3 | 第 16 章 |
| 8 | A | D3 | SAA-3.2 | 第 19 章 |
| 9 | D | D2 | SAA-2.1 | 第 33 章 |
| 10 | B | D1 | SAA-1.1 | 第 13、31 章 |
| 11 | C | D4 | SAA-4.2 | 第 39、17 章 |
| 12 | A | D1 | SAA-1.2 | 第 16 章 |
| 13 | B、E | D2 | SAA-2.2 | 第 18、35 章 |
| 14 | D | D3 | SAA-3.1 | 第 24 章 |
| 15 | A、C | D1 | SAA-1.3 | 第 23 章 |
| 16 | C | D2 | SAA-2.1 | 第 32、19 章 |
| 17 | B | D4 | SAA-4.3 | 第 27 章 |
| 18 | C、E | D1 | SAA-1.1 | 第 32、13 章 |
| 19 | A | D3 | SAA-3.4 | 第 11 章 |
| 20 | D | D2 | SAA-2.1 | 第 32 章 |
| 21 | B、D | D1 | SAA-1.2 | 第 21、15 章 |
| 22 | B | D4 | SAA-4.1 | 第 24、39 章 |
| 23 | A | D2 | SAA-2.2 | 第 26、34 章 |
| 24 | C | D1 | SAA-1.3 | 第 15 章 |
| 25 | D | D3 | SAA-3.5 | 第 25 章 |
| 26 | A | D1 | SAA-1.1 | 第 13 章 |
| 27 | A、E | D2 | SAA-2.1 | 第 32、21 章 |
| 28 | C | D4 | SAA-4.4 | 第 8、39 章 |
| 29 | B | D1 | SAA-1.2 | 第 16、20 章 |
| 30 | D | D3 | SAA-3.2 | 第 21、17 章 |
| 31 | A | D2 | SAA-2.2 | 第 17 章 |
| 32 | C | D1 | SAA-1.3 | 第 24、15 章 |
| 33 | B、C | D4 | SAA-4.2 | 第 21、39 章 |
| 34 | B | D2 | SAA-2.1 | 第 27、29 章 |
| 35 | D | D1 | SAA-1.1 | 第 22 章 |
| 36 | D、E | D3 | SAA-3.5 | 第 31、30 章 |
| 37 | C | D1 | SAA-1.2 | 第 16 章 |
| 38 | A | D2 | SAA-2.2 | 第 17、36 章 |
| 39 | B | D4 | SAA-4.1 | 第 23 章 |
| 40 | D | D3 | SAA-3.3 | 第 26 章 |
| 41 | A | D1 | SAA-1.3 | 第 26、15 章 |
| 42 | C | D2 | SAA-2.1 | 第 31 章 |
| 43 | D | D4 | SAA-4.2 | 第 39 章 |
| 44 | B | D1 | SAA-1.2 | 第 6 章 |
| 45 | A | D3 | SAA-3.1 | 第 24 章 |
| 46 | A、B | D2 | SAA-2.2 | 第 18、26 章 |
| 47 | C | D1 | SAA-1.3 | 第 26、15 章 |
| 48 | D | D4 | SAA-4.3 | 第 27、39 章 |
| 49 | B | D2 | SAA-2.1 | 第 32 章 |
| 50 | A | D3 | SAA-3.4 | 第 22 章 |
| 51 | C | D1 | SAA-1.1 | 第 13、12 章 |
| 52 | B | D2 | SAA-2.2 | 第 32、34 章 |
| 53 | C、D | D4 | SAA-4.4 | 第 6、39 章 |
| 54 | D | D1 | SAA-1.2 | 第 6 章 |
| 55 | A | D3 | SAA-3.3 | 第 26、19 章 |
| 56 | C | D2 | SAA-2.1 | 第 19 章 |
| 57 | B | D1 | SAA-1.1 | 第 22 章 |
| 58 | D | D3 | SAA-3.4 | 第 7 章 |
| 59 | A | D4 | SAA-4.3 | 第 26、39 章 |
| 60 | C | D2 | SAA-2.2 | 第 34 章 |
| 61 | B | D3 | SAA-3.2 | 第 19 章 |
| 62 | B、E | D4 | SAA-4.1 | 第 23 章 |
| 63 | D | D4 | SAA-4.4 | 第 11、39 章 |
| 64 | A | D3 | SAA-3.3 | 第 27 章 |
| 65 | C | D3 | SAA-3.1 | 第 24 章 |

### 各 Domain 題數

| Domain | 題數 | 題號 |
|---|---|---|
| D1 Design Secure Architectures | 20 | 2、5、7、10、12、15、18、21、24、26、29、32、35、37、41、44、47、51、54、57 |
| D2 Design Resilient Architectures | 17 | 1、6、9、13、16、20、23、27、31、34、38、42、46、49、52、56、60 |
| D3 Design High-Performing Architectures | 15 | 3、8、14、19、25、30、36、40、45、50、55、58、61、64、65 |
| D4 Design Cost-Optimized Architectures | 13 | 4、11、17、22、28、33、39、43、48、53、59、62、63 |

本回共 11 題「選兩項」（第 5、13、15、18、21、27、33、36、46、53、62 題），單選題答案 A、B、C、D 各約四分之一。

### 錯題對應複習章節

- **D1 錯 4 題以上**：先重讀第 12 章（policy 評估：同帳號 resource policy、explicit deny）與第 15 章（KMS key policy、SSE-KMS 的雙重授權、snapshot 分享）。若錯在第 10、26、51 題，再看第 13 章的聯合身份與工作負載身份；錯在第 7、12、37 題，看第 16 章的安全服務分工（Macie、Inspector、GuardDuty 各管什麼）；錯在第 5、44、54 題，回到第 5、6 章的路由與 security group。
- **D2 錯 4 題以上**：第 32 章（SQS、SNS、EventBridge 的語意差異，特別是「一則訊息給一個 consumer」與扇出）是本回最常出現的考點；第 33 章的 Standard／Express workflow 限制、第 19 章的 Lambda 非同步呼叫與 destination 也要複習。錯在第 13、52、60 題，重讀第 34、35 章的 DR 策略、health check 設計與優雅降級。
- **D3 錯 3 題以上**：第 24 章（EBS 類型、EFS throughput mode、FSx for Lustre）與第 27 章（partition key 設計、熱分割）各出現多題；第 31 章的 Kinesis 順序性與 Firehose 格式轉換、第 11 章的 Global Accelerator 與 CloudFront 分工也常是失分點。
- **D4 錯 3 題以上**：先讀第 39 章，確認每種購買方式（RI、Savings Plans、Spot、排程關機）各自適合的使用模式；再看第 23 章的儲存類別取回時間與費用、第 27 章的 DynamoDB capacity mode 與 table class。
- **「選兩項」題錯 3 題以上**：多半是只找出一個正確步驟、另一個選了「看起來也對但不是必要」的選項。練習把每個選項都問一次「拿掉它，需求還能滿足嗎？」。
- **猶豫後答對的題目**：與錯題一樣處理。真實考試中，這些題目最容易因讀題時漏看一個限制（例如「不能修改程式」「不得遺失」「任何人包括 root」）而失分。
