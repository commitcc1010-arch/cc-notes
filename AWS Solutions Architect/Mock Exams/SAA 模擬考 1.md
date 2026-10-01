---
title: SAA 模擬考 1
exam: SAA-C03
---

# SAA 模擬考 1

> [!abstract] 作答說明
> **題數與時間**：65 題，建議計時 130 分鐘（與 SAA-C03 正式考試相同），平均每題 2 分鐘。題目依 domain 混合排列，和真實考試一樣不會分段。
> **題型**：單選題 4 個選項選 1 個；「選兩項」題 5 個選項選 2 個，兩個都對才算得分。
> **及格參考**：正式考試以 100–1000 的量尺分數計分、720 分及格，且有不計分的試驗題，無法直接換算答對率。練習時以答對 47 題（約 72%）作為及格參考，答對 52 題以上代表準備相對穩定。
> **作答方式**：先遮住答案一口氣作答完畢，把每題答案寫在紙上或筆記中，全部完成後再逐題展開 `答案` 區塊核對。不要邊做邊看答案，否則無法量測真實的時間壓力。
> **錯題記錄**：每答錯一題，記下「題號、選錯的選項、錯在哪個關鍵字或機制」。最後用文末的「答案速查與 Domain 分析」表格，把錯題對回章節複習；同一章錯兩題以上，代表該章需要重讀而不只是看重點整理。
> **情境說明**：本回題目以零售電商、媒體影音、醫療健康與製造業為主；所有公司與情境皆為虛構，題目皆為原創。

## 題目

### 第 1 題｜SAA｜單選｜D1 EC2 存取 S3 的最小權限

一家連鎖診所的影像判讀系統跑在 Amazon EC2 上，需要讀取 S3 bucket `clinic-imaging` 中 `dicom/` 前綴下的醫學影像。目前開發人員把一組 IAM user 的 access key 寫在應用程式設定檔裡，而這個 IAM user 附加了 `AmazonS3FullAccess`。資安稽核要求移除所有長期憑證，並讓應用程式只能讀取 `dicom/` 前綴下的物件。

哪個做法最能滿足稽核要求？

- A. 把 access key 移到 AWS Secrets Manager 並啟用自動輪替，應用程式啟動時從 Secrets Manager 讀取金鑰
- B. 建立一個附加 `AmazonS3ReadOnlyAccess` 的 IAM role，透過 instance profile 掛到 EC2，並刪除原本的 access key
- C. 建立一個 IAM role，identity policy 只允許對 `arn:aws:s3:::clinic-imaging/dicom/*` 執行 `s3:GetObject`，透過 instance profile 掛到 EC2，並刪除原本的 access key
- D. 在 bucket policy 中以 `aws:SourceIp` 條件只允許 EC2 的 private IP 讀取 `dicom/`，並保留原本的 access key 作為驗證

> [!answer]- 答案：C
> **A ✗** Secrets Manager 只是換個地方存放 access key，IAM user 的 key 仍然是長期憑證，而且 `AmazonS3FullAccess` 的過大權限也沒有收斂。這個做法適合「必須使用第三方提供的長期 API key」的情境，不適合 AWS 自己的服務存取。
>
> **B ✗** 改用 instance profile 確實移除了長期憑證（EC2 會從 instance metadata 取得自動輪替的臨時憑證），但 `AmazonS3ReadOnlyAccess` 能讀取帳號內所有 bucket，不符合「只能讀 `dicom/`」的最小權限要求。
>
> **C ✓** IAM role 搭配 instance profile 讓 EC2 取得由 STS 發出、會自動輪替的臨時憑證，沒有任何長期金鑰。identity policy 把 Resource 限定在 `clinic-imaging/dicom/*` 的物件 ARN，就只能讀取該前綴；若應用程式還需要列出物件，可再對 bucket ARN 允許 `s3:ListBucket` 並加上 `s3:prefix` 條件。
>
> **D ✗** EC2 經由 Internet 或 NAT 存取 S3 時，S3 看到的是 public IP，而經由 VPC endpoint 時要用 `aws:VpcSourceIp`，因此用 `aws:SourceIp` 比對 private IP 不會生效。更根本的問題是它保留了長期 access key，沒有滿足稽核要求。
>
> **考點**：SAA-1.1｜EC2 用 instance profile 取得臨時憑證，並以 Resource ARN 收斂權限｜延伸閱讀：第 12 章

### 第 2 題｜SAA｜單選｜D3 長影片轉碼的運算選擇

一家串流影音平台讓創作者把 4K 原始影片上傳到 S3，再轉成多種解析度的 HLS 格式供播放。目前的做法是由 S3 事件觸發 AWS Lambda 呼叫 ffmpeg 轉碼，但長度超過 20 分鐘的影片經常在執行到 15 分鐘時被中止。團隊希望支援任意長度的影片、上傳後自動開始轉碼，並且營運負擔最少。

哪個方案最符合需求？

- A. 把 Lambda 記憶體調到 10,240 MB、ephemeral storage（/tmp）調到 10,240 MB，讓轉碼在時限內完成
- B. 由 S3 事件觸發一個 Lambda，只負責建立 AWS Elemental MediaConvert 轉碼工作，把 HLS 輸出寫回 S3
- C. 建立一個 EC2 Auto Scaling group 執行 ffmpeg，從 Amazon SQS queue 取得轉碼工作，依 queue 長度擴展
- D. 用 AWS Step Functions 的 Map state 把影片切成多段，平行交給多個 Lambda 轉碼，最後再由一個 Lambda 合併輸出

> [!answer]- 答案：B
> **A ✗** 提高記憶體會同時提高 CPU 配額，確實能讓轉碼變快，但 Lambda 單次執行最長 15 分鐘是硬上限，4K 長片仍可能超時，無法保證「任意長度」。
>
> **B ✓** MediaConvert 是受管的檔案型影片轉碼服務，原生支援 HLS 等串流格式，轉碼工作不受 Lambda 那種 15 分鐘執行時限的限制，也不必管理任何轉碼伺服器。Lambda 只負責呼叫 `CreateJob` 這種幾秒內完成的動作，完全不會碰到 15 分鐘限制。
>
> **C ✗** 技術上可行，也是「需要自訂轉碼軟體或特殊編碼器」時的合理選擇，但要自行維護 AMI、ffmpeg 版本、擴展與 Spot 中斷處理，營運負擔明顯高於受管服務。
>
> **D ✗** 自行切段平行轉碼可以避開單次 15 分鐘的限制，但切段點的關鍵影格對齊、合併與失敗重試都要自己處理，複雜度高，屬於重新發明 MediaConvert 已經提供的功能。
>
> **考點**：SAA-3.2｜Lambda 15 分鐘上限與選擇受管的專用運算服務｜延伸閱讀：第 19 章

### 第 3 題｜SAA｜單選｜D2 MES 系統的 AZ 層級高可用

一家汽車零件製造商的製造執行系統（MES）跑在同一個 AZ 的兩台 EC2 上，前面由 Application Load Balancer（ALB）分流，資料庫是 Single-AZ 的 Amazon RDS for PostgreSQL。上一季該 AZ 發生中斷，產線因此停擺 3 小時。管理層要求系統在單一 AZ 故障時能自動恢復服務，並且盡量不修改應用程式程式碼。

哪個方案最能滿足需求？

- A. 每天建立 EC2 AMI 與 RDS snapshot，並準備好 runbook，在 AZ 故障時由值班人員在另一個 AZ 還原
- B. 把 EC2 換成更大的 instance type 並啟用 EC2 auto recovery，再為 RDS 建立一個位於同一 AZ 的 read replica
- C. 建立跨兩個 AZ 的 Auto Scaling group；為 RDS 建立一個位於另一個 AZ 的 read replica，AZ 故障時讓應用程式改連 replica
- D. 建立跨兩個以上 AZ 的 Auto Scaling group 並註冊到 ALB，同時把 RDS 修改為 Multi-AZ 部署

> [!answer]- 答案：D
> **A ✗** 手動還原的 RTO 以小時計，而且每天一次的 snapshot 代表最多遺失一天的資料，不符合「自動恢復」。
>
> **B ✗** EC2 auto recovery 只處理底層硬體故障，instance 仍留在同一個 AZ；同 AZ 的 read replica 在 AZ 故障時會一起失效。兩個元件都沒有離開單一 AZ 這個 single point of failure。
>
> **C ✗** Web tier 的部分正確，但 read replica 是非同步複寫、唯讀的。AZ 故障時必須手動 promote replica，應用程式也要改用新的 endpoint，需要修改設定或程式，且可能遺失尚未複寫的交易。
>
> **D ✓** 跨 AZ 的 Auto Scaling group 會在某個 AZ 失效時於其他 AZ 補足 instance，ALB 只把流量送給健康的 target。RDS Multi-AZ 以同步複寫維持 standby，主節點故障時自動 failover，應用程式使用的 DNS endpoint 不變，因此不必改程式。
>
> **考點**：SAA-2.2｜Multi-AZ Auto Scaling 與 RDS Multi-AZ 自動 failover｜延伸閱讀：第 18 章、第 26 章

### 第 4 題｜SAA｜單選｜D4 影片素材的長期保存成本

一家紀錄片製作公司把拍攝原始素材存在 S3 Standard，每月新增約 80 TB，每個檔案通常數 GB 以上。素材在拍攝後 30 天內會被頻繁剪輯，之後幾乎不再存取；但依授權合約必須保存 7 年，偶爾有客戶要求調閱舊素材，公司承諾在 48 小時內交付。

哪個方案最具成本效益？

- A. 設定 S3 Lifecycle rule，物件建立 30 天後轉換到 S3 Glacier Deep Archive，7 年後自動刪除
- B. 設定 S3 Lifecycle rule，物件建立 30 天後轉換到 S3 Glacier Flexible Retrieval，7 年後自動刪除
- C. 上傳時直接使用 S3 Intelligent-Tiering，只使用預設的自動分層、不啟用選用的 archive 層
- D. 設定 S3 Lifecycle rule，物件建立 30 天後轉換到 S3 One Zone-IA，7 年後自動刪除

> [!answer]- 答案：A
> **A ✓** Glacier Deep Archive 是 S3 儲存單價最低的類別，Standard 取回在 12 小時內完成、Bulk 取回在 48 小時內完成，都符合 48 小時的交付承諾。存取模式（30 天後幾乎不用）已知，用 lifecycle 依物件年齡轉換最直接，也遠超過 Deep Archive 180 天的最短保存期。
>
> **B ✗** Flexible Retrieval 取回較快（分鐘到數小時），但儲存單價高於 Deep Archive。題目的取回時限是 48 小時，不需要為更快的取回多付長期儲存費。如果承諾是「數小時內交付」，它才會是較好的選擇。
>
> **C ✗** Intelligent-Tiering 適合存取模式「無法預測」的資料；它的預設層最低只到 Archive Instant Access，單價仍明顯高於 Deep Archive，還要按物件數支付監控費。存取模式已知時，lifecycle 規則更便宜。
>
> **D ✗** One Zone-IA 的單價高於任何 Glacier 類別，而且資料只存在一個 AZ，用來保存唯一一份、要留 7 年的原始素材，耐受 AZ 損毀的能力不足。
>
> **考點**：SAA-4.1｜依已知存取模式與取回時限選擇最便宜的封存類別｜延伸閱讀：第 23 章

### 第 5 題｜SAA｜單選｜D1 阻擋 SQL injection 與爬蟲

一家線上服飾零售商的網站由 internet-facing ALB 後面的 EC2 提供服務。資安團隊在存取日誌中發現有人在搜尋欄位注入 SQL 語句，另外有少數 IP 每 5 分鐘對商品頁發出上萬次請求爬取價格，而且這些 IP 每天都在變。公司希望以最少營運負擔同時阻擋這兩種行為，並且不修改應用程式。

哪個方案最合適？

- A. 為 ALB 訂閱 AWS Shield Advanced，啟用自動的應用層 DDoS 緩解
- B. 在 ALB 所在 subnet 的 network ACL 加入 deny 規則封鎖爬蟲 IP，並每天依日誌更新清單
- C. 在 ALB 上掛載 AWS WAF web ACL，加入 AWS managed 的 SQL database rule group，並建立 rate-based rule 限制單一 IP 的請求速率
- D. 啟用 Amazon GuardDuty，透過 Amazon EventBridge 觸發 Lambda，把可疑 IP 加入 EC2 security group 的拒絕清單

> [!answer]- 答案：C
> **C ✓** AWS WAF 在第 7 層檢查 HTTP 請求內容：AWS managed 的 SQL database rule group 能辨識常見的 SQL injection 樣式，rate-based rule 會自動封鎖在時間窗內超過門檻的來源 IP，IP 換了也會被重新計數與封鎖，不需要人工維護清單。
>
> **A ✗** Shield Advanced 處理的是 DDoS 攻擊，並提供 Shield Response Team 與費用保護；SQL injection 屬於應用層漏洞利用，仍需要 WAF 規則來檢查請求內容。單純訂閱 Shield Advanced 無法擋下 SQL 注入。
>
> **B ✗** NACL 只看 IP 與 port，看不到 HTTP 內容，無法擋 SQL injection；每個 NACL 的規則數有上限，而且每天手動更新變動的 IP 營運負擔很高。
>
> **D ✗** GuardDuty 是威脅偵測服務，分析 VPC Flow Logs、DNS 與 CloudTrail 等資料，不會檢查 HTTP 請求中的 SQL 語句。security group 也只有 allow 規則，無法建立「拒絕清單」。
>
> **考點**：SAA-1.2｜WAF managed rule group 與 rate-based rule 的用途｜延伸閱讀：第 16 章

### 第 6 題｜SAA｜單選｜D3 Aurora 讀取尖峰的彈性擴展

一家生鮮電商使用 Amazon Aurora MySQL，叢集有一個 writer 與一個 Aurora Replica，商品瀏覽的唯讀查詢透過 reader endpoint 送到 replica。行銷活動期間瀏覽量會在數分鐘內暴增 5 倍，活動時間由業務部門臨時決定、難以預測；尖峰時 replica 的 CPU 達 95%，頁面明顯變慢，平時只有 20%。寫入量則幾乎不變。

哪個方案能以最少營運負擔處理讀取尖峰？

- A. 把 writer 與 replica 都升級到最大的 instance class，確保活動期間有足夠 CPU
- B. 為叢集設定 Aurora Auto Scaling，依 Aurora Replicas 的平均 CPU 使用率自動增減 replica，應用程式繼續使用 reader endpoint
- C. 建立 Aurora Global Database，在另一個 Region 加入 secondary cluster 分擔唯讀查詢
- D. 在叢集前面加入 Amazon RDS Proxy，讓唯讀查詢的連線集中共用

> [!answer]- 答案：B
> **B ✓** Aurora Auto Scaling 以 target tracking 依 replica 的平均 CPU 或連線數增減 Aurora Replica（一個叢集最多 15 個）。新 replica 共用同一個儲存層，不必複製資料，加入後會自動出現在 reader endpoint 的負載分配中，應用程式不需改動，尖峰過後也會自動縮減。
>
> **A ✗** 垂直升級需要修改 instance、可能造成短暫中斷，而且平時 CPU 只有 20%，長期使用最大規格很浪費；writer 也不是瓶頸。
>
> **C ✗** Global Database 的 secondary cluster 在另一個 Region，主要用途是跨 Region 災難復原與當地低延遲讀取。讓同一個 Region 的使用者跨 Region 查詢會增加延遲，也無法隨尖峰自動伸縮。
>
> **D ✗** RDS Proxy 解決的是「連線數過多」或 Lambda 大量建立連線的問題，透過連線池共用連線；它不增加資料庫的運算能力，CPU 95% 的瓶頸仍然存在。
>
> **考點**：SAA-3.3｜Aurora Replica Auto Scaling 與 reader endpoint｜延伸閱讀：第 26 章

### 第 7 題｜SAA｜單選｜D1 理賠文件的加密金鑰控制

一家健康保險公司把會員理賠文件存在 S3。法遵要求：加密金鑰必須由公司自己控制、能隨時停用以讓資料無法被解密、金鑰每年自動輪替，而且每一次使用金鑰都要留下可稽核的紀錄。團隊不想自行保管金鑰材料，也不想在應用程式中撰寫加解密程式。

哪個方案最符合需求？

- A. 啟用 S3 預設的 SSE-S3 加密，並啟用 S3 server access logging 記錄每一次存取
- B. 使用 SSE-C，由應用程式在每次上傳與下載時提供公司自行保管的金鑰
- C. 由應用程式在上傳前以存放於 AWS Secrets Manager 的金鑰進行 client-side encryption
- D. 建立 AWS KMS customer managed key 並啟用自動輪替，把 bucket 預設加密設為 SSE-KMS 使用這把金鑰

> [!answer]- 答案：D
> **D ✓** Customer managed key 由公司透過 key policy 控制誰能使用，可以隨時 disable，啟用自動輪替後預設每年輪替一次金鑰材料，舊資料仍可解密。S3 以 SSE-KMS 加解密時會呼叫 KMS，每次 `GenerateDataKey`、`Decrypt` 都會記錄在 AWS CloudTrail，滿足稽核要求，而且加解密完全由 S3 處理。
>
> **A ✗** SSE-S3 的金鑰由 S3 完全管理，公司無法停用金鑰或控制誰能使用它，也沒有每次金鑰使用的 CloudTrail 紀錄；access log 記錄的是物件存取，不是金鑰使用。
>
> **B ✗** SSE-C 讓公司完全控制金鑰，但金鑰要由公司自行保管、輪替並在每個請求中傳送，違反「不想自行保管金鑰材料」；輪替後舊物件也必須用舊金鑰才能讀取，管理負擔大。
>
> **C ✗** Client-side encryption 需要在應用程式中撰寫加解密程式並自行設計輪替機制，違反題目限制；金鑰使用的稽核也得自己實作。
>
> **考點**：SAA-1.3｜SSE-KMS customer managed key 的控制、輪替與 CloudTrail 稽核｜延伸閱讀：第 15 章

### 第 8 題｜SAA｜選兩項｜D2 訂單事件的扇出解耦

一家家電電商的訂單服務在訂單成立後，需要通知庫存、出貨與會員點數三個系統。目前訂單服務以同步 HTTP 依序呼叫三個系統，任何一個系統變慢或故障都會讓下單失敗。新架構的要求是：三個系統各自獨立處理、任何一個系統停機數小時時訊息也不能遺失，而且之後新增訂閱者時不需要修改訂單服務。

哪兩個步驟的組合能滿足需求？

- A. 訂單服務在訂單成立後，把訂單事件發布到一個 Amazon SNS standard topic
- B. 訂單服務把訂單事件寫入單一 Amazon SQS queue，讓三個系統共同輪詢同一個 queue
- C. 三個系統各自提供 HTTPS endpoint，直接訂閱 SNS topic 接收事件
- D. 為三個系統各建立一個 SQS queue 並訂閱 SNS topic，每個系統只從自己的 queue 取訊息處理
- E. 改用 AWS Step Functions 的 Parallel state，由 workflow 同步呼叫三個系統的 API

> [!answer]- 答案：A、D
> **A ✓** SNS topic 是發布端與訂閱端之間的扇出點：訂單服務只需要發布一次，不知道有哪些訂閱者，之後新增訂閱者只要加 subscription，不必修改訂單服務。
>
> **B ✗** 多個 consumer 輪詢同一個 queue 是「競爭消費」，每則訊息只會被其中一個系統處理，庫存收到的訂單出貨就收不到，無法讓三個系統各自拿到完整事件。
>
> **C ✗** SNS 對 HTTP/S endpoint 會依 delivery policy 重試，但重試次數與時間有限，系統停機數小時時重試用盡，訊息會被丟棄（除非另外設定 DLQ）。這無法滿足「停機數小時不遺失」。
>
> **D ✓** SNS 搭配 SQS 的 fan-out 讓每個系統擁有自己的 queue，訊息最長可保留 14 天（預設 4 天），系統停機時訊息在 queue 中累積，恢復後再處理，彼此互不影響。
>
> **E ✗** Step Functions 仍是同步協調三個系統，訂單流程仍受任一系統影響；新增訂閱者必須修改 workflow 定義，不符合鬆耦合要求。它適合「步驟之間有順序與補償邏輯」的流程，而不是單純廣播事件。
>
> **考點**：SAA-2.1｜SNS + SQS fan-out 讓訂閱者獨立且可緩衝｜延伸閱讀：第 32 章

### 第 9 題｜SAA｜單選｜D4 架構會變動時的運算承諾

一家工業設備製造商在 us-east-1 執行 24 小時運作的 ERP 與 IoT 後端，每月 EC2 費用穩定約 4 萬美元，主要是 m5 instance。架構團隊計畫在未來一年把部分服務從 m5 改到 Graviton 的 m7g，並把另一部分改成 Amazon ECS on AWS Fargate。財務希望簽 3 年的承諾換取最大折扣，但不能因為架構調整讓承諾的金額浪費。

應該購買哪種方案？

- A. Compute Savings Plans，承諾每小時的運算支出金額
- B. EC2 Instance Savings Plans，承諾 us-east-1 的 m5 family 支出金額
- C. 3 年期全額預付的 Standard Reserved Instances，涵蓋目前所有 m5 instance
- D. 3 年期的 Convertible Reserved Instances，之後再交換成 m7g instance

> [!answer]- 答案：A
> **A ✓** Compute Savings Plans 的折扣適用於任何 instance family、大小、Region、作業系統，也涵蓋 Fargate 與 Lambda。從 m5 改到 m7g 或改成 Fargate，承諾的金額都會自動套用到新的用量，不會浪費。
>
> **B ✗** EC2 Instance Savings Plans 折扣較高，但綁定單一 Region 的單一 instance family。m5 改成 m7g 後承諾就套不上，也不涵蓋 Fargate。若架構確定三年不變，它才是更便宜的選擇。
>
> **C ✗** Standard RI 綁定 instance family，不能套用到 Fargate；架構改變後只能到 RI Marketplace 轉售，增加作業與損失。
>
> **D ✗** Convertible RI 可以交換成其他 family，但只適用於 EC2，改成 Fargate 的那部分無法使用，仍可能浪費承諾。
>
> **考點**：SAA-4.2｜Compute Savings Plans 涵蓋 family 變更與 Fargate｜延伸閱讀：第 39 章

### 第 10 題｜SAA｜單選｜D1 病患下載報告的臨時授權

一家醫學檢驗公司讓病患登入網站後下載自己的檢驗報告 PDF，報告存在一個 private S3 bucket。目前網站後端從 S3 讀出檔案再轉傳給瀏覽器，流量大時後端 instance 的網路頻寬吃緊。公司希望讓瀏覽器直接從 S3 下載，但每份報告只能被該病患在短時間內存取，而且 bucket 不得公開。

哪個做法最合適？

- A. 開放 bucket 的 public read，但把物件 key 改成隨機 UUID，讓外人無法猜到檔名
- B. 後端驗證病患身份與報告擁有權後，以具備 `s3:GetObject` 權限的 IAM role 產生有效期 5 分鐘的 S3 presigned URL 回傳給瀏覽器
- C. 建立 Amazon CloudFront distribution，以 Origin Access Control（OAC）存取 bucket，讓病患透過 CloudFront 網址下載
- D. 在 bucket policy 加上 `aws:Referer` 條件，只允許來自公司網站網域的下載請求

> [!answer]- 答案：B
> **B ✓** Presigned URL 是以簽署者的權限、對單一物件、在指定期限內有效的連結。後端先完成身份與擁有權檢查，再產生短效 URL，瀏覽器直接向 S3 下載，後端不再轉傳流量，bucket 也維持 private。
>
> **A ✗** 這是「藏起來就安全」的做法，網址一旦外流（瀏覽器記錄、轉寄）任何人都能下載；開放 public read 也違反「bucket 不得公開」。
>
> **C ✗** OAC 只保證 bucket 只能經由 CloudFront 存取，但 distribution 本身是公開的，任何知道網址的人都能下載，沒有逐一病患的授權。若再加上 CloudFront signed URL 才能達到類似效果。
>
> **D ✗** Referer 標頭由用戶端送出、可以任意偽造，不能作為安全控制；它也無法區分是哪一位病患。
>
> **考點**：SAA-1.1｜S3 presigned URL 提供單一物件的限時存取｜延伸閱讀：第 22 章

### 第 11 題｜SAA｜單選｜D3 算圖農場的高效能共用儲存

一家動畫工作室在 AWS 上用數百台 EC2 Spot instance 執行算圖（rendering）。數百 TB 的場景素材存放在 S3，每次算圖工作需要讓所有節點以 POSIX 檔案系統同時、高吞吐量地讀取素材，並把算圖結果寫回 S3。工作結束後檔案系統就不再需要。

哪個儲存方案效能最好且最符合需求？

- A. 建立 Amazon EFS 檔案系統掛載到所有節點，每次工作前用 AWS DataSync 把素材從 S3 複製到 EFS
- B. 每個節點掛載一顆 io2 Block Express EBS volume，各自從 S3 複製需要的素材到本機
- C. 在 EC2 上部署 Amazon S3 File Gateway，所有節點以 NFS 掛載 gateway 存取 S3
- D. 建立以 S3 bucket 為 data repository 的 Amazon FSx for Lustre scratch 檔案系統，所有節點掛載後讀取素材，結果匯出回 S3

> [!answer]- 答案：D
> **D ✓** FSx for Lustre 是為 HPC 設計的平行檔案系統，可提供數百 GB/s 等級的總吞吐量給大量節點。連結 S3 data repository 後，檔案在第一次讀取時從 S3 載入，結果可匯出回 S3；scratch 類型不做資料複寫、成本較低，適合工作結束即丟棄的暫存用途。
>
> **A ✗** EFS 提供共享 POSIX 檔案系統，但總吞吐量與延遲不如 Lustre 適合數百節點的密集讀取；每次工作前複製數百 TB 到 EFS 也耗時且昂貴。
>
> **B ✗** EBS volume 一般只掛在一台 instance（Multi-Attach 也限同 AZ 少量 instance），每個節點各自複製一份素材會產生大量重複傳輸與儲存費用，也不是共用檔案系統。
>
> **C ✗** File Gateway 是讓地端應用以 NFS/SMB 存取 S3 的混合儲存服務，單一 gateway 會成為數百節點的吞吐瓶頸，不適合雲端 HPC。
>
> **考點**：SAA-3.1｜FSx for Lustre 連結 S3 供 HPC 平行讀取｜延伸閱讀：第 24 章

### 第 12 題｜SAA｜單選｜D2 訂單資料庫的跨 Region 災難復原

一家跨國運動用品電商的訂單資料庫是 us-east-1 的 Amazon Aurora PostgreSQL。董事會要求發生 Region 層級災難時，RPO 約 1 秒、RTO 在數分鐘內；平時也希望在 eu-west-1 提供低延遲的唯讀查詢給歐洲的客服系統。團隊希望使用受管功能，避免自行維護複寫程式。

哪個方案最符合需求？

- A. 建立 Aurora Global Database，在 eu-west-1 加入 secondary cluster，歐洲客服系統查詢 secondary cluster，災難時執行跨 Region failover
- B. 啟用 Aurora 自動備份的跨 Region 複製到 eu-west-1，災難時在 eu-west-1 從備份還原叢集
- C. 使用 AWS Database Migration Service（AWS DMS）持續把資料複寫到 eu-west-1 的另一個 Aurora 叢集，災難時把應用程式改連該叢集
- D. 在 us-east-1 把 Aurora Replica 增加到 15 個並分散在所有 AZ，歐洲客服系統透過 reader endpoint 查詢

> [!answer]- 答案：A
> **A ✓** Global Database 以儲存層的專用複寫把資料送到 secondary Region，典型延遲低於 1 秒，secondary cluster 平時可承接當地的唯讀查詢。Region 故障時可以把 secondary 提升為主叢集，RTO 通常在數分鐘內，完全是受管功能。
>
> **B ✗** 從跨 Region 備份還原的 RPO 取決於備份時間點，RTO 也要等待整個叢集還原，通常是小時等級；平時也無法提供唯讀查詢。這是成本最低的 backup and restore 策略，適合 RTO／RPO 寬鬆的系統。
>
> **C ✗** DMS 可以做持續複寫，但複寫延遲不保證、需要監控與維護 replication instance，切換也是手動，不是「受管、RPO 約 1 秒」的最佳解。
>
> **D ✗** 所有 replica 都在 us-east-1，Region 故障時一起失效；歐洲客服跨洋查詢的延遲也沒有改善。
>
> **考點**：SAA-2.2｜Aurora Global Database 的跨 Region RPO／RTO 與當地讀取｜延伸閱讀：第 34 章

### 第 13 題｜SAA｜選兩項｜D1 無 Internet 路徑的私有存取

一家半導體廠在 VPC 的 private subnet 執行良率分析用的 EC2，資料存在同一個 Region 的 S3。資安政策要求這些 instance 不得有任何通往 Internet 的路徑（route table 不能有 NAT Gateway 或 Internet Gateway 的 route），但維運人員仍要用 AWS Systems Manager Session Manager 登入，應用程式也要讀寫 S3。instance 已附加含 `AmazonSSMManagedInstanceCore` 的 instance profile。

哪兩個步驟能滿足需求？

- A. 在 public subnet 建立 NAT Gateway，再以 network ACL 限制只允許 TCP 443 出站
- B. 為 S3 建立 gateway VPC endpoint，並關聯到 private subnet 的 route table
- C. 在 public subnet 建立 bastion host，並在 instance 的 security group 允許來自 bastion 的 TCP 22
- D. 在 instance 上設定 HTTP proxy，透過 Site-to-Site VPN 走地端資料中心的 proxy 連到 AWS 服務
- E. 為 `ssm`、`ssmmessages`（以及 `ec2messages`）建立 interface VPC endpoint，並啟用 private DNS

> [!answer]- 答案：B、E
> **A ✗** NAT Gateway 本身就是 Internet 路徑，即使限制 port，仍違反「不得有 NAT Gateway route」的政策。
>
> **B ✓** S3 gateway endpoint 在 route table 中加入指向 S3 prefix list 的 route，流量留在 AWS 網路內，不需要 NAT 或 IGW，而且 gateway endpoint 不收費。
>
> **C ✗** Bastion 需要 public subnet 與 Internet 入口，也要管理 SSH 金鑰；題目要求的是 Session Manager，SSM 根本不需要開放 inbound 22。
>
> **D ✗** 經由地端 proxy 存取 AWS 服務雖然沒有在 VPC 內建立 NAT，但流量繞回地端再從地端出 Internet，實際上仍是 Internet 路徑，而且增加延遲與維運負擔。
>
> **E ✓** SSM Agent 需要連到 Systems Manager 的 API 端點（`ssm`），Session Manager 的工作階段則走 `ssmmessages`。`ec2messages` 只有較舊版本的 SSM Agent（3.3.40.0 之前）才需要，新版 agent 在 `ssmmessages` 可用時改用它，因此選項中以括號標示。在 VPC 內建立這些 interface endpoint 並啟用 private DNS 後，agent 用原本的服務網域就能解析到 endpoint 的私有 IP，完全不需要 Internet；B 的 S3 gateway endpoint 也順便讓 agent 能從 S3 下載更新。
>
> **考點**：SAA-1.2｜Gateway endpoint 與 SSM interface endpoints 建立無 Internet 的 isolated subnet｜延伸閱讀：第 6 章、第 38 章

### 第 14 題｜SAA｜單選｜D3 跨洲直播推流的網路品質

一家直播平台讓全球的直播主以 RTMP（TCP 1935）推流到 us-west-2 與 ap-northeast-1 兩個 Region 的 Network Load Balancer（NLB），後方是 ingest server。直播主抱怨跨洲推流時封包遺失與抖動嚴重；部分企業客戶的防火牆只允許連到固定 IP 位址的允許清單。平台還希望某個 Region 故障時，推流能自動導向另一個 Region。

哪個方案最符合需求？

- A. 在兩個 NLB 前面建立 Amazon CloudFront distribution，讓直播主推流到 CloudFront 網域
- B. 為每個 NLB 配置 Elastic IP，並使用 Amazon Route 53 latency-based routing 搭配 health check
- C. 建立 AWS Global Accelerator，以兩個 Region 的 NLB 作為 endpoint group，讓直播主推流到 accelerator 的固定 anycast IP
- D. 在兩個 Region 的 VPC 之間建立 inter-Region VPC peering，讓直播主連到最近的 Region 後再由 peering 轉送

> [!answer]- 答案：C
> **C ✓** Global Accelerator 提供兩個固定的 anycast IP，直播主的流量在最近的 AWS edge location 進入 AWS 骨幹網路，避開不穩定的公共 Internet 長距離路段，對 TCP／UDP 都適用。endpoint group 以 health check 監測 NLB，某個 Region 故障時秒級改送到健康的 Region，客戶端不受 DNS 快取影響。
>
> **A ✗** CloudFront 只處理 HTTP/HTTPS（以及 WebSocket），不支援 RTMP 推流，也不提供固定 IP 給防火牆允許清單。
>
> **B ✗** NLB 的 Elastic IP 可以給允許清單，但企業客戶要同時允許兩個 Region 的多組 IP；流量仍走公共 Internet，品質沒有改善；DNS failover 也會受用戶端與 resolver 快取 TTL 影響。
>
> **D ✗** VPC peering 連接的是兩個 VPC 的內部流量，直播主從 Internet 進入最近 Region 的路段品質不會改變，也沒有提供固定入口 IP 與自動 failover。
>
> **考點**：SAA-3.4｜Global Accelerator 的 anycast 固定 IP、骨幹網路與跨 Region failover｜延伸閱讀：第 11 章

### 第 15 題｜SAA｜單選｜D2 含人工覆核的檢體處理流程

一家醫院的檢體處理流程包含四個步驟：接收檢驗儀器上傳的結果、呼叫外部檢驗資訊系統驗證、等待醫檢師人工覆核（可能數小時到 2 天）、最後通知主治醫師。目前由一支 cron 腳本串起所有步驟，失敗時很難知道卡在哪一步，也無法從中斷處重跑。團隊希望以 serverless 方式重構，具備每個步驟的自動重試、可視化的執行狀態，並能暫停等待人工覆核。

哪個方案最合適？

- A. 使用 AWS Step Functions Express workflow，以 `.waitForTaskToken` 等待醫檢師覆核
- B. 每個步驟各用一個 Lambda，步驟之間以 SQS queue 串接，覆核狀態存在 Amazon DynamoDB
- C. 使用 AWS Step Functions Standard workflow，每個 Task 設定 Retry，覆核步驟使用 `.waitForTaskToken` 等待醫檢師在系統中按下核准
- D. 每個 Lambda 結束時以非同步方式呼叫下一個 Lambda，覆核步驟由 Lambda 每分鐘輪詢資料庫直到狀態改變

> [!answer]- 答案：C
> **C ✓** Standard workflow 單次執行最長可達 1 年，每個狀態都有可視化的執行歷程，Task 可以宣告式設定 Retry 與 Catch。callback 模式（`.waitForTaskToken`）讓流程暫停並把 task token 交給覆核系統，醫檢師核准後呼叫 `SendTaskSuccess` 讓流程繼續，等待期間不消耗運算資源。
>
> **A ✗** Express workflow 單次最長 5 分鐘，且不支援 `.waitForTaskToken` 這種 callback 整合模式，無法等待 2 天。它適合高頻、短時間的事件處理。
>
> **B ✗** SQS 串接可以解耦，但沒有整體流程的可視化與統一的錯誤處理，等待 2 天的覆核狀態也要自己設計輪詢或觸發邏輯，等於自己實作 workflow 引擎。
>
> **D ✗** Lambda 互相呼叫的鏈式設計難以追蹤失敗位置，也無法從中斷處重跑；每分鐘輪詢兩天會產生大量無意義的呼叫與費用。
>
> **考點**：SAA-2.1｜Step Functions Standard workflow 的重試、可視化與 callback 等待｜延伸閱讀：第 33 章

### 第 16 題｜SAA｜單選｜D4 Private subnet 存取 S3 與 DynamoDB 的費用

一家零售商的推薦引擎跑在 private subnet 的 EC2 上，每天從同一個 Region 的 S3 讀取約 40 TB 的訓練資料，並大量讀寫 Amazon DynamoDB。所有流量目前都經過 NAT Gateway，帳單顯示 NAT Gateway 的資料處理費是最大的網路成本。資安要求 instance 必須留在 private subnet。

哪個方案最具成本效益？

- A. 為 S3 與 DynamoDB 各建立 interface VPC endpoint，並啟用 private DNS
- B. 把 NAT Gateway 換成自行管理的 NAT instance，以較大的 instance type 承接流量
- C. 為 S3 建立 gateway endpoint，DynamoDB 流量繼續經過 NAT Gateway
- D. 為 S3 與 DynamoDB 各建立 gateway VPC endpoint，並關聯到 private subnet 的 route table

> [!answer]- 答案：D
> **D ✓** S3 與 DynamoDB 是唯二支援 gateway endpoint 的服務，gateway endpoint 沒有小時費也沒有資料處理費。流量改走 endpoint 後就不再經過 NAT Gateway，資料處理費直接消失，instance 仍留在 private subnet。
>
> **A ✗** Interface endpoint 也能讓流量不經 NAT，但它按 AZ 收小時費並按 GB 收資料處理費，每天 40 TB 的流量仍會產生可觀費用。它適合需要從地端或其他 VPC 經由私有 IP 存取 S3 的情境。
>
> **B ✗** NAT instance 省下了 NAT Gateway 的資料處理費，但要自行處理高可用、修補與頻寬瓶頸，而且仍然繞了不必要的路，成本與營運負擔都不如 gateway endpoint。
>
> **C ✗** 只處理了 S3，DynamoDB 的大量流量仍在支付 NAT 資料處理費，不是最具成本效益的方案。
>
> **考點**：SAA-4.4｜Gateway endpoint 免費取代 NAT Gateway 的資料處理費｜延伸閱讀：第 6 章、第 39 章

### 第 17 題｜SAA｜單選｜D1 集中稽核程式的跨帳號唯讀存取

一家連鎖百貨集團用 AWS Organizations 管理 30 個 AWS 帳號。資安團隊在 security 帳號的 EC2 上執行一支自行開發的稽核程式，需要每天讀取每個成員帳號的 EC2、S3 與 IAM 設定，但不得修改任何資源。團隊希望不在任何地方保存長期憑證，並以最少營運負擔管理權限。

哪個方案最合適？

- A. 在每個成員帳號建立只有唯讀權限的 IAM role，trust policy 信任 security 帳號中稽核程式的 role；稽核程式透過 instance profile 取得自己的憑證後，以 `sts:AssumeRole` 切換到各帳號的 role
- B. 在每個成員帳號建立具唯讀權限的 IAM user，把 30 組 access key 存在 security 帳號的 Secrets Manager 並每 90 天輪替
- C. 在每個成員帳號的 EC2、S3 與 IAM 服務上設定 resource-based policy，允許 security 帳號的 role 讀取
- D. 使用 AWS Resource Access Manager（AWS RAM）把每個成員帳號的資源分享給 security 帳號

> [!answer]- 答案：A
> **A ✓** 跨帳號存取的標準做法是「目標帳號的 role ＋ 信任來源帳號的 trust policy」。稽核程式以 instance profile 取得臨時憑證，再 assume 各帳號的唯讀 role 取得該帳號的臨時憑證，全程沒有長期金鑰。這些 role 可以用 CloudFormation StackSets 一次部署到所有成員帳號。
>
> **B ✗** 30 組 access key 都是長期憑證，即使存在 Secrets Manager 並輪替，仍違反「不保存長期憑證」，輪替 30 個帳號的 key 也增加營運負擔。
>
> **C ✗** S3 bucket 支援 resource-based policy，但 EC2 的 Describe API 與 IAM 的讀取 API 不支援以 resource-based policy 授權給其他帳號，這個做法無法完成。
>
> **D ✗** RAM 用來共享特定類型的資源（例如 subnet、Transit Gateway、License Manager 設定），讓其他帳號「使用」它們，不是授權讀取另一個帳號的所有設定。
>
> **考點**：SAA-1.1｜跨帳號 role 與 trust policy、以 AssumeRole 取得臨時憑證｜延伸閱讀：第 13 章

### 第 18 題｜SAA｜單選｜D3 感測器資料近即時落地 S3

一家食品工廠有 5,000 個感測器，每秒各送出一筆 JSON 格式的溫度與壓力讀數。品保團隊要求資料在數分鐘內寫入 S3，以 Parquet 格式、依日期與產線分區存放，供 Amazon Athena 查詢。團隊沒有人力管理伺服器或撰寫串流處理程式。

哪個方案最符合需求？

- A. 感測器把資料寫入 Amazon Kinesis Data Streams，在 EC2 上用 Kinesis Client Library 撰寫 consumer 轉成 Parquet 後寫入 S3
- B. 感測器把資料送到 Amazon Data Firehose，啟用 record format conversion（以 AWS Glue Data Catalog 的資料表定義 schema）轉成 Parquet，並以 dynamic partitioning 依日期與產線寫入 S3
- C. 感測器把資料寫入 Amazon SQS queue，每晚由 AWS Glue job 批次讀出並轉成 Parquet 寫入 S3
- D. 感測器直接呼叫 S3 `PutObject`，每筆讀數存成一個 JSON 物件，再由 Athena 直接查詢

> [!answer]- 答案：B
> **B ✓** Data Firehose 是全受管的串流投遞服務，會依緩衝大小或時間批次寫入 S3。內建的 record format conversion 可把 JSON 轉成 Parquet，dynamic partitioning 可依記錄中的欄位決定 S3 前綴，不需要撰寫或管理任何 consumer。
>
> **A ✗** 功能上可行，但要自行開發與維運 KCL consumer、處理檢查點與擴展，違反「沒有人力管理伺服器或撰寫串流程式」。需要多個即時 consumer 或自訂處理邏輯時，Data Streams 才是較好的選擇。
>
> **C ✗** 每晚批次處理不符合「數分鐘內」寫入的需求；SQS 也不是為大量串流資料落地設計的。
>
> **D ✗** 每秒 5,000 個小物件會產生龐大的 PUT 請求費用，大量小 JSON 檔也讓 Athena 查詢變慢、掃描成本變高，沒有 Parquet 與分區的效益。
>
> **考點**：SAA-3.5｜Data Firehose 的格式轉換與動態分區｜延伸閱讀：第 31 章

### 第 19 題｜SAA｜選兩項｜D2 新聞 CMS 的多 AZ 改造

一家新聞媒體的內容管理系統（CMS）目前跑在單一 EC2 instance 上，同一台機器還執行 MySQL，編輯上傳的新聞圖片存在本機的 EBS volume。公司要把 web tier 改成跨兩個 AZ 的 Auto Scaling group，並要求任一 AZ 故障時，編輯仍能發稿、讀者仍能看到所有圖片。

哪兩個步驟能滿足需求？

- A. 把圖片放在一顆 io2 EBS volume 並啟用 Multi-Attach，讓所有 instance 共用
- B. 每台 instance 啟動時從 S3 同步全部圖片到本機，新上傳的圖片先寫在本機再由 cron 每小時上傳到 S3
- C. 把圖片目錄改成掛載 Amazon EFS（Regional）檔案系統，並在兩個 AZ 各建立 mount target
- D. 把 MySQL 留在其中一台 EC2 上，以 cron 每 5 分鐘執行 `mysqldump` 並上傳到 S3
- E. 把資料庫遷移到 Amazon RDS for MySQL Multi-AZ 部署，CMS 改連 RDS endpoint

> [!answer]- 答案：C、E
> **A ✗** EBS Multi-Attach 只能讓同一個 AZ 內的 instance 掛載，另一個 AZ 的 instance 看不到這顆 volume；而且一般檔案系統同時被多台機器寫入會損毀資料，需要叢集檔案系統。
>
> **B ✗** 本機先寫再每小時上傳，代表其他 instance 最多一小時看不到新圖片；寫入的那台 instance 若在上傳前被終止，圖片就遺失。
>
> **C ✓** EFS Regional 檔案系統的資料跨多個 AZ 儲存，每個 AZ 的 mount target 讓該 AZ 的 instance 掛載同一份檔案。上傳後所有 instance 立即可見，任一 AZ 故障時另一個 AZ 仍能讀寫。
>
> **D ✗** 資料庫仍在單一 instance，AZ 故障時無法發稿；每 5 分鐘的 dump 代表可能遺失 5 分鐘的資料，還原也要手動進行。
>
> **E ✓** RDS Multi-AZ 以同步複寫維持另一個 AZ 的 standby，主節點或 AZ 故障時自動 failover，endpoint 不變，CMS 不需要改連線設定以外的程式。
>
> **考點**：SAA-2.2｜共享檔案用 EFS、資料庫用 RDS Multi-AZ，讓 web tier 無狀態｜延伸閱讀：第 24 章、第 26 章

### 第 20 題｜SAA｜單選｜D1 找出含有病患個資的 bucket

一家醫療 SaaS 公司在多個帳號中有數百個 S3 bucket，由不同團隊建立。法遵部門要求找出哪些 bucket 含有未預期的病患個資，例如姓名、身分證號與公司自訂格式的病歷號，並在之後持續監控新增的資料。團隊希望以最少營運負擔完成。

哪個方案最合適？

- A. 啟用 Amazon GuardDuty 的 S3 Protection，分析 bucket 的資料存取事件
- B. 啟用 Amazon Inspector，對所有 bucket 執行定期掃描
- C. 啟用 Amazon Macie 的自動化敏感資料探索，並為病歷號格式建立 custom data identifier
- D. 用 AWS Glue crawler 建立所有 bucket 的資料表，再以 Athena 定期執行正規表示式查詢

> [!answer]- 答案：C
> **C ✓** Macie 使用機器學習與樣式比對找出 S3 中的敏感資料，內建多種個資類型的 managed data identifier；公司自訂的病歷號可用 custom data identifier（正規表示式加關鍵字）定義。自動化敏感資料探索會持續抽樣評估 bucket，並可透過 Organizations 由委派管理帳號統一管理。
>
> **A ✗** GuardDuty S3 Protection 偵測的是可疑的存取行為（例如異常來源大量讀取），不會分析物件內容是否含有個資。
>
> **B ✗** Inspector 掃描的是 EC2、container image 與 Lambda 的軟體漏洞與網路暴露，不掃描 S3 物件內容。
>
> **D ✗** 自行建立 crawler 與查詢可以做到部分偵測，但要處理各種檔案格式、維護規則與排程，營運負擔遠高於 Macie，也不涵蓋非結構化檔案。
>
> **考點**：SAA-1.3｜Macie 探索 S3 中的敏感資料與 custom data identifier｜延伸閱讀：第 16 章

### 第 21 題｜SAA｜單選｜D4 穩定流量的 DynamoDB 計費模式

一家連鎖超市的會員點數系統使用 Amazon DynamoDB on-demand 模式。過去一年的監控顯示，流量非常穩定且可預測：每天白天約 8,000 WCU、夜間約 2,000 WCU，讀取也呈相同曲線，未來兩年預期不變。財務部門希望在不影響效能的前提下降低 DynamoDB 的費用。

哪個方案最具成本效益？

- A. 維持 on-demand 模式，並在前面加入 DynamoDB Accelerator（DAX）減少讀取請求
- B. 改為 provisioned capacity 並設定 auto scaling 跟隨日夜曲線，再針對穩定的基礎用量購買 reserved capacity
- C. 把資料表的 table class 改為 DynamoDB Standard-IA，降低每次讀寫的費用
- D. 把資料表改成 global table，讓另一個 Region 分擔一半的寫入量

> [!answer]- 答案：B
> **B ✓** On-demand 以請求計價，適合難以預測的流量；流量穩定可預測、利用率高時，provisioned capacity 的單位成本通常較低。Auto scaling 讓容量貼近日夜曲線，reserved capacity 再以一年或三年承諾為基礎用量取得額外折扣。
>
> **A ✗** DAX 能減少重複讀取，但它是按節點計費的叢集，對寫入沒有幫助；在流量穩定的情境下，主要的節省來源是計費模式本身。
>
> **C ✗** Standard-IA table class 降低的是「儲存」單價，讀寫單價反而較高，適合儲存費用占大宗、很少存取的資料表，不適合這個以讀寫為主的工作負載。
>
> **D ✗** Global table 會把每筆寫入複寫到每個 Region，總寫入費用增加而不是減少，它解決的是多 Region 可用性與延遲。
>
> **考點**：SAA-4.3｜穩定流量選 provisioned＋auto scaling＋reserved capacity｜延伸閱讀：第 27 章

### 第 22 題｜SAA｜單選｜D3 緊耦合 HPC 模擬的網路效能

一家航太零件製造商在 AWS 上執行計算流體力學（CFD）模擬，每個工作由 64 台 instance 組成，以 MPI 頻繁交換資料，節點間延遲直接決定模擬時間。工作可以重跑，不要求跨 AZ 的高可用。團隊希望讓節點之間的延遲最低、吞吐量最高。

哪個做法最合適？

- A. 把 64 台 instance 放在 spread placement group，分散到不同的底層硬體
- B. 把 64 台 instance 平均分散到三個 AZ，以 Auto Scaling group 管理
- C. 把 instance 放在 partition placement group，每個 partition 放 16 台
- D. 把 instance 放在同一個 AZ 的 cluster placement group，並使用支援 Elastic Fabric Adapter（EFA）的 instance type

> [!answer]- 答案：D
> **D ✓** Cluster placement group 把 instance 放在同一個 AZ 內彼此靠近的硬體上，提供低延遲、高頻寬的網路；EFA 讓 MPI 等 HPC 應用繞過作業系統網路堆疊，進一步降低延遲。題目明確說不要求跨 AZ 高可用，正好可以接受單一 AZ 的取捨。
>
> **A ✗** Spread placement group 刻意把 instance 放在不同機架以降低同時故障的機率，延遲較高，而且每個 AZ 最多只能放 7 台 instance，無法容納 64 台。
>
> **B ✗** 跨 AZ 部署提高可用性，但 AZ 之間的延遲高於 AZ 內，對緊耦合 MPI 工作是效能損失，還會產生跨 AZ 傳輸費。
>
> **C ✗** Partition placement group 用於 HDFS、Cassandra 等需要「分區故障隔離」的大型分散式系統，不是以最低延遲為目標。
>
> **考點**：SAA-3.2｜Cluster placement group 與 EFA 支援緊耦合 HPC｜延伸閱讀：第 17 章

### 第 23 題｜SAA｜單選｜D1 付費影片的 HLS 授權

一家線上教育影音平台以 Amazon CloudFront 搭配 S3（使用 OAC）提供付費課程影片，格式為 HLS：每部影片有一個播放清單檔與數百個數秒長的片段檔。公司要求只有已購買課程的登入會員能播放，而且不能修改播放器去逐一為片段產生網址。

哪個做法最合適？

- A. 會員登入並驗證購買紀錄後，由應用程式發給 CloudFront signed cookies，以 trusted key group 中的金鑰簽署，限定該課程路徑與有效期限
- B. 會員登入後，由應用程式為播放清單檔產生 S3 presigned URL，播放器再直接向 S3 取得片段
- C. 在 CloudFront distribution 啟用 geographic restriction，只允許公司營運國家的使用者觀看
- D. 在 CloudFront 上掛載 AWS WAF，建立規則檢查 `Referer` 標頭必須是公司網站

> [!answer]- 答案：A
> **A ✓** Signed cookies 一次授權多個檔案：cookie 中的自訂政策可以用萬用字元限定路徑（例如整門課程的目錄）與有效期限，瀏覽器之後請求每個片段都會自動帶上 cookie，播放器不需修改。Signed URL 則適合單一檔案的授權。
>
> **B ✗** Presigned URL 只對單一物件有效，播放清單中的片段仍需各自授權；讓播放器直接向 S3 取片段也繞過了 CloudFront 的快取，而且 bucket 只允許 OAC 存取時根本無法直接讀取。
>
> **C ✗** Geo restriction 依國家限制，不能區分誰買了課程。
>
> **D ✗** Referer 標頭可以被偽造，只能擋住簡單的盜連，不能作為付費內容的授權機制。
>
> **考點**：SAA-1.2｜CloudFront signed cookies 授權多檔案的私有內容｜延伸閱讀：第 11 章

### 第 24 題｜SAA｜選兩項｜D2 限量商品開賣的寫入尖峰

一家球鞋電商每月舉辦一次限量商品抽籤，開放登記的前 10 分鐘會湧入平時 50 倍的寫入請求，目前 API 以同步方式直接寫入 Amazon RDS for MySQL，尖峰時資料庫連線耗盡、大量請求失敗。抽籤結果在登記截止後一小時才公布，因此登記資料不需要即時寫進資料庫，但每一筆登記都不能遺失。

哪兩個步驟的組合最能解決問題？

- A. 把 RDS instance 升級到最大的規格，並把 `max_connections` 調到最高
- B. 讓 Amazon API Gateway 直接整合 Amazon SQS，把每筆登記寫入 queue 後立即回應使用者「已收到」
- C. 在 ALB 前面加入 Amazon CloudFront，快取 POST 請求以減少到達後端的寫入量
- D. 以 Lambda 函式消費 SQS queue，並在 event source mapping 設定最大併發數，以穩定的速率寫入資料庫
- E. 把 SQS 換成 Amazon SNS topic，讓 Lambda 訂閱 topic 後寫入資料庫

> [!answer]- 答案：B、D
> **A ✗** 垂直擴展只能提高上限，50 倍的瞬間尖峰仍可能壓垮資料庫；為一個月 10 分鐘的尖峰長期支付最大規格也不划算。
>
> **B ✓** API Gateway 可以不經 Lambda 直接呼叫 SQS `SendMessage`，請求寫進 queue 就算成功。SQS 會自動擴展吸收尖峰，並持久保存訊息，使用者立即得到回應，資料庫不再直接承受尖峰。
>
> **C ✗** CloudFront 不快取 POST 請求，而且每筆登記都是不同的資料，本來就不能被快取。
>
> **D ✓** Lambda 消費 SQS 時可設定 event source mapping 的最大併發數（maximum concurrency），控制同時寫入資料庫的 Lambda 數量，讓 queue 以資料庫承受得住的速率慢慢清空。處理失敗的訊息會回到 queue 重試，搭配 DLQ 就不會遺失。
>
> **E ✗** SNS 是推送模型，收到訊息後會立即推給所有訂閱者，不會替消費端緩衝，Lambda 會跟著尖峰一起擴展，資料庫照樣被壓垮。
>
> **考點**：SAA-2.1｜以 SQS 削峰填谷並控制消費併發｜延伸閱讀：第 32 章、第 35 章

### 第 25 題｜SAA｜單選｜D3 RDS 儲存 IOPS 的瓶頸

一家區域醫院的門診系統使用 Amazon RDS for PostgreSQL，儲存為 100 GiB 的 gp2。每天上午門診高峰時，查詢延遲在一段時間後突然惡化；CloudWatch 顯示 `ReadIOPS` 加 `WriteIOPS` 在尖峰初期約 2,500，之後掉到約 300 並持平，`BurstBalance` 降到 0，而 instance 的 CPU 只有 35%。

哪個做法最能解決問題？

- A. 為資料庫建立兩個 read replica，把查詢分散到 replica
- B. 把 DB instance class 升級成兩倍的 vCPU 與記憶體
- C. 把儲存修改為 Provisioned IOPS SSD（io2），設定符合尖峰需求的 IOPS
- D. 啟用 Multi-AZ 部署，讓 standby 分擔一部分的 I/O

> [!answer]- 答案：C
> **C ✓** gp2 的基準 IOPS 是每 GiB 3 IOPS，100 GiB 只有 300 IOPS，短時間可依 burst credit 衝到 3,000。`BurstBalance` 歸零後 IOPS 掉回 300，正好吻合症狀。改用 io2 可以設定固定、不依賴 credit 的 IOPS，在四個選項中是唯一處理儲存瓶頸的做法。實務上改成 gp3 也能取得不依賴 burst credit 的固定基準 IOPS（RDS 的 gp3 至少有 3,000 IOPS），而且通常比 io2 便宜，但它不在本題選項中。
>
> **A ✗** 讀取量可分散到 replica，但寫入仍集中在主資料庫，而且每個 replica 也有自己的儲存 IOPS 限制，治標不治本。
>
> **B ✗** CPU 只有 35%，瓶頸在儲存的 IOPS，不在運算；更大的 instance 不會提高 gp2 volume 的基準 IOPS。
>
> **D ✗** Multi-AZ 的 standby 不接受讀寫流量，只用於 failover，不會分擔 I/O；同步複寫甚至會略為增加寫入延遲。
>
> **考點**：SAA-3.3｜gp2 burst credit 耗盡與改用 Provisioned IOPS｜延伸閱讀：第 24 章、第 26 章

### 第 26 題｜SAA｜單選｜D4 可中斷算圖工作的 Spot 策略

一家廣告製作公司每晚執行數千個影片算圖工作，每個工作 10 到 40 分鐘，會定期把進度 checkpoint 到 S3，被中斷後可以從 checkpoint 繼續。工作在早上 8 點前完成即可，對 instance type 沒有特殊要求，只要有 8 vCPU 以上。公司希望在可靠完成工作的前提下把運算成本降到最低。

哪個方案最合適？

- A. 購買 3 年期 Standard Reserved Instances，數量足以支撐每晚的尖峰
- B. 使用單一 instance type 的 Spot instance，allocation strategy 設為 lowest-price
- C. 使用 Auto Scaling group 的 mixed instances policy，全部使用 Spot，指定多種符合 8 vCPU 以上的 instance type，allocation strategy 設為 price-capacity-optimized
- D. 使用 On-Demand instance 搭配 Dedicated Hosts，確保容量不被其他客戶占用

> [!answer]- 答案：C
> **C ✓** 工作可中斷、可從 checkpoint 繼續、有時間彈性，是 Spot 的典型用途。指定多種 instance type 擴大可用的 Spot 容量池，price-capacity-optimized 會從可用容量較充足、價格較低的池中選擇，降低被中斷的機率，同時取得接近最低的價格。
>
> **A ✗** RI 適合 24 小時穩定運作的工作負載；這些工作只在夜間執行，白天的 RI 承諾會閒置，而且折扣通常低於 Spot。
>
> **B ✗** 只用單一 instance type 的 Spot 容量池較小，lowest-price 策略會集中在最便宜的池，容量一緊縮就大量中斷，影響工作在早上前完成。
>
> **D ✗** Dedicated Hosts 用於授權綁定實體核心或合規要求的情境，價格最高，與降低成本的目標相反。
>
> **考點**：SAA-4.2｜Spot 多 instance type 分散與 price-capacity-optimized｜延伸閱讀：第 17 章、第 39 章

### 第 27 題｜SAA｜單選｜D1 工廠伺服器的無金鑰 AWS 存取

一家紡織廠在自有機房有 20 台 Linux 伺服器，每小時要把產線品檢照片上傳到 S3。目前每台伺服器都設定了同一組 IAM user 的 access key，資安稽核要求移除長期憑證。公司已有自己的 PKI，每台伺服器都有由內部 CA 簽發的 X.509 憑證。

哪個做法最安全且最符合需求？

- A. 為每台伺服器建立各自的 IAM user，並以腳本每 90 天自動輪替 access key
- B. 建立 Amazon Cognito user pool，讓每台伺服器以帳號密碼登入取得 token 後上傳
- C. 在 bucket policy 中允許工廠的固定 public IP 匿名上傳，移除伺服器上的所有金鑰
- D. 使用 IAM Roles Anywhere，以內部 CA 建立 trust anchor，讓伺服器用自己的 X.509 憑證換取 IAM role 的臨時憑證

> [!answer]- 答案：D
> **D ✓** IAM Roles Anywhere 讓 AWS 以外的工作負載使用 X.509 憑證取得 IAM role 的臨時憑證：把內部 CA 註冊為 trust anchor，建立 profile 對應到只允許上傳該 bucket 的 role，伺服器以 credential helper 換取短效憑證，不再需要任何長期 access key。
>
> **A ✗** 每台伺服器一個 IAM user 雖然縮小了單一金鑰外洩的影響，但仍然是長期憑證，不符合稽核要求，還增加 20 組金鑰的管理負擔。
>
> **B ✗** Cognito user pool 是給應用程式的終端使用者登入，帳號密碼也是長期秘密，伺服器還需要 identity pool 才能換到 AWS 憑證，不是機器對機器存取的合適做法。
>
> **C ✗** 匿名上傳代表任何能從該 IP 發出請求的人都能寫入 bucket，完全沒有身份驗證；新建 bucket 預設的 Block Public Access 也會阻擋這種公開政策。
>
> **考點**：SAA-1.1｜IAM Roles Anywhere 讓地端伺服器以 X.509 取得臨時憑證｜延伸閱讀：第 13 章

### 第 28 題｜SAA｜單選｜D3 門市 POS 的 TCP 長連線入口

一家連鎖便利商店的 6,000 家門市 POS 終端機，以自訂的二進位協定透過 TCP 長連線連到 AWS 上的交易閘道服務，尖峰時有數十萬條同時連線，要求極低延遲。門市網路設備的防火牆規則只能設定固定 IP 位址，後端服務部署在兩個 AZ 的 EC2 上。

應該使用哪種負載平衡器？

- A. Network Load Balancer，在每個 AZ 指定一個 Elastic IP，以 TCP listener 轉送到後端 target group
- B. Application Load Balancer，以 HTTPS listener 轉送，並把 ALB 的 DNS 名稱解析出的 IP 提供給門市
- C. Gateway Load Balancer，搭配 GENEVE 封裝把流量送到後端服務
- D. Classic Load Balancer，以 TCP listener 轉送，並啟用 cross-zone load balancing

> [!answer]- 答案：A
> **A ✓** NLB 在第 4 層運作，能處理大量 TCP 連線且延遲極低；每個 AZ 可以綁定一個 Elastic IP，提供固定 IP 給門市防火牆。自訂的二進位協定不需要 HTTP 解析，正是 NLB 的使用情境。
>
> **B ✗** ALB 只處理 HTTP/HTTPS（與 gRPC、WebSocket），無法處理自訂的二進位 TCP 協定；ALB 節點的 IP 會變動，不能提供固定 IP。若需要「ALB 的 L7 路由加固定 IP」，可以在 ALB 前面加 NLB 或 Global Accelerator。
>
> **C ✗** Gateway Load Balancer 用來把流量透明地送到防火牆、IDS 等第三方網路設備進行檢查，不是應用程式的入口負載平衡器。
>
> **D ✗** Classic Load Balancer 是上一代產品，不支援為每個 AZ 綁定 Elastic IP，新架構不應採用。
>
> **考點**：SAA-3.4｜NLB 的 L4 高效能與每個 AZ 固定 IP｜延伸閱讀：第 10 章

### 第 29 題｜SAA｜選兩項｜D2 低成本的跨 Region 災難復原

一家家具製造商的供應商入口網站跑在 us-east-1，架構為 ALB、EC2 Auto Scaling group 與 Amazon RDS for MySQL Multi-AZ。業務評估後同意：Region 層級災難時 RTO 可以是 24 小時、RPO 可以是 4 小時，但平時在第二個 Region 的支出要盡可能低。

哪兩個步驟的組合最能滿足需求？

- A. 建立 AWS Backup plan，每 4 小時備份 EC2 與 RDS，並設定 copy rule 把備份複製到 us-west-2
- B. 在 us-west-2 部署縮小規模但持續運作的完整環境（warm standby），以 RDS cross-Region read replica 同步資料
- C. 以 AWS CloudFormation template 定義 VPC、ALB、Auto Scaling group 等基礎設施，災難時在 us-west-2 部署並從備份還原
- D. 把 RDS 增加為 Multi-AZ DB cluster，提供兩個可讀的 standby
- E. 在兩個 Region 同時運作完整環境，以 Route 53 latency-based routing 分流

> [!answer]- 答案：A、C
> **A ✓** RPO 4 小時代表最多可遺失 4 小時資料，每 4 小時備份一次並跨 Region 複製即可滿足；平時第二個 Region 只有備份的儲存費用。
>
> **B ✗** Warm standby 能達到分鐘到小時級的 RTO，但第二個 Region 有持續運作的 instance 與 read replica，平時支出明顯高於 backup and restore，超出 24 小時 RTO 所需。
>
> **C ✓** 用 IaC 在災難時重建環境，是 backup and restore 策略能在 24 小時內恢復的關鍵：基礎設施可重複、快速地部署，再從複製過來的備份還原資料。平時不需要在 us-west-2 執行任何資源。
>
> **D ✗** Multi-AZ DB cluster 提高的是單一 Region 內的可用性與 failover 速度，Region 故障時一樣失效，也增加成本。
>
> **E ✗** Multi-site active-active 提供接近零的 RTO，但成本是兩倍以上，遠超過需求。
>
> **考點**：SAA-2.2｜依 RTO／RPO 選擇 backup and restore 與 IaC 重建｜延伸閱讀：第 34 章

### 第 30 題｜SAA｜單選｜D1 持續掃描 EC2 與容器映像的漏洞

一家遠距醫療公司的服務跑在 EC2 與 Amazon ECS 上，container image 存放在 Amazon ECR。資安政策要求持續掃描作業系統套件與程式語言套件的已知 CVE，新漏洞公布時自動重新評估既有的 instance 與 image，並依風險排序結果。團隊希望使用受管服務、不自行維護掃描工具。

應該使用哪個服務？

- A. Amazon GuardDuty Runtime Monitoring
- B. Amazon Inspector
- C. AWS Config 搭配 managed rules
- D. Amazon Macie

> [!answer]- 答案：B
> **B ✓** Amazon Inspector 自動且持續地掃描 EC2 instance、ECR 中的 container image 與 Lambda 函式，比對已知 CVE 與網路可達性；新的 CVE 公布時會重新評估既有資源，並給出依情境調整的風險分數。
>
> **A ✗** GuardDuty Runtime Monitoring 偵測執行期間的可疑行為（例如連到惡意網域、提權），屬於威脅偵測，不是軟體漏洞掃描。
>
> **C ✗** AWS Config 評估資源「設定」是否合規（例如 EBS 是否加密），不檢查 instance 內安裝的套件版本是否有漏洞。
>
> **D ✗** Macie 探索 S3 中的敏感資料，與 EC2、container image 漏洞無關。
>
> **考點**：SAA-1.2｜Inspector 持續掃描 EC2、ECR 與 Lambda 的軟體漏洞｜延伸閱讀：第 16 章

### 第 31 題｜SAA｜單選｜D2 長連線微服務的容器平台

一家新聞媒體把推播、留言與直播聊天室拆成十多個 container 化的微服務，目前跑在自行管理的 EC2 Docker 主機上，每次修補作業系統與調整容量都很耗工。聊天室服務需要維持數小時的 WebSocket 連線，各服務的流量尖峰時間不同，需要各自擴展。公司希望以最少營運負擔執行這些服務。

哪個方案最合適？

- A. 遷移到 Amazon EKS，使用 managed node group，以 Cluster Autoscaler 調整節點數
- B. 把每個服務改成 Lambda container image，前面由 API Gateway WebSocket API 觸發
- C. 每個服務建立一個 Elastic Beanstalk 環境，部署在 Docker platform 上
- D. 遷移到 Amazon ECS on AWS Fargate，每個微服務一個 ECS service，以 Service Auto Scaling 依各自的指標擴展

> [!answer]- 答案：D
> **D ✓** Fargate 讓團隊不必管理任何 EC2 主機或作業系統修補，ECS service 會維持指定數量的 task 並與 ALB 整合，ALB 支援長時間的 WebSocket 連線。每個服務各自設定 Service Auto Scaling，就能依自己的尖峰擴展。
>
> **A ✗** EKS 可以執行這些服務，但要管理 Kubernetes 版本升級、add-on 與節點擴展，營運負擔高於 ECS on Fargate。若公司已有 Kubernetes 生態系或需要跨雲一致性，EKS 才較合適。
>
> **B ✗** 改成 Lambda 需要大幅重寫成事件驅動模型，長連線狀態要外部化；對已經 container 化、長時間執行的服務來說改動過大。
>
> **C ✗** Elastic Beanstalk 能簡化部署，但每個環境底層仍是要修補的 EC2，十多個環境的管理也比 ECS 的多個 service 麻煩。
>
> **考點**：SAA-2.1｜ECS on Fargate 以最少負擔執行獨立擴展的微服務｜延伸閱讀：第 21 章

### 第 32 題｜SAA｜單選｜D2 共用檔案系統的 AZ 韌性

一家連鎖藥妝零售商的會員 App 後端跑在兩個 AZ 的 EC2 Auto Scaling group，所有 instance 掛載同一個 Amazon EFS 檔案系統，存放商品圖片與優惠券範本。當初為了省錢建立的是 EFS One Zone 檔案系統，位於 AZ-a。架構審查指出：AZ-a 故障時，AZ-b 的 instance 也會讀不到檔案。公司要求單一 AZ 故障時服務不受影響，並維持所有 instance 共用同一份檔案。

哪個方案最合適？

- A. 在 AZ-b 再建立一個 EFS One Zone 檔案系統，兩個 AZ 各自掛載，並以 cron 每 10 分鐘用 rsync 互相同步
- B. 啟用 EFS replication，把檔案系統複寫到同一個 Region 的另一個 EFS One Zone 檔案系統，故障時再手動改掛載
- C. 改用一顆 EBS gp3 volume 並啟用 Multi-Attach，讓兩個 AZ 的 instance 同時掛載
- D. 建立 EFS Regional（Standard）檔案系統並在兩個 AZ 建立 mount target，用 AWS DataSync 搬移資料後切換掛載

> [!answer]- 答案：D
> **D ✓** EFS Regional 檔案系統把資料冗餘儲存在多個 AZ，每個 AZ 的 mount target 讓當地 instance 掛載；任一 AZ 故障時，其他 AZ 仍能讀寫同一份資料。DataSync 可以在兩個 EFS 檔案系統之間完成一次性搬移並驗證資料。
>
> **A ✗** 兩份檔案系統各自寫入，rsync 會造成資料衝突與最多 10 分鐘的不一致，也增加維護腳本的負擔，不再是「共用同一份檔案」。
>
> **B ✗** EFS replication 的目的地在複寫期間是唯讀的，故障時要手動中止複寫並改掛載，有 RPO 與人工切換時間，不符合「服務不受影響」。它比較適合跨 Region 的災難復原。
>
> **C ✗** EBS volume 綁定單一 AZ，Multi-Attach 也只能給同一個 AZ 的 instance 使用，根本無法跨 AZ 共用。
>
> **考點**：SAA-2.2｜EFS Regional 與 One Zone 的可用性差異｜延伸閱讀：第 24 章

### 第 33 題｜SAA｜單選｜D4 長期保存 EBS snapshot 的成本

一家醫療器材製造商依品質法規，必須把品質管理系統伺服器的每月 EBS snapshot 保存 7 年。這些 snapshot 只有在稽核或調查時才會被還原，過去三年從未用過，一旦需要還原，可以接受等待 3 天。目前所有 snapshot 都留在 EBS snapshot 的 standard tier，費用逐年增加。

哪個方案最具成本效益？

- A. 每月把 snapshot 複製到另一個 Region 保存，並刪除原 Region 的 snapshot
- B. 每月從 snapshot 建立 AMI 保存，並刪除原本的 snapshot
- C. 以 Amazon Data Lifecycle Manager 政策，把每月 snapshot 移到 EBS Snapshots Archive tier，並在 7 年後刪除
- D. 每月把 volume 掛到一台 EC2，以腳本把整顆 volume 打包上傳到 S3 Glacier Deep Archive

> [!answer]- 答案：C
> **C ✓** EBS Snapshots Archive 為很少還原、需長期保存的 snapshot 提供較低的儲存單價（每份封存的 snapshot 以完整快照計算），最短保存 90 天，還原需要最多 72 小時，正好符合「可以等待 3 天」。Data Lifecycle Manager 可以自動依排程封存與刪除，不需要寫腳本。
>
> **A ✗** 跨 Region 複製會產生資料傳輸費，而且目的地仍是 standard tier，儲存單價沒有降低，只改變了保存位置。
>
> **B ✗** AMI 的底層仍是 EBS snapshot，費用相同；刪除 snapshot 也會讓 AMI 失效。
>
> **D ✗** Deep Archive 單價很低，但要自行撰寫與維護打包、上傳、驗證與還原的流程，還要開機器處理；還原時也要重新建立 volume，營運負擔與風險都高於原生功能。
>
> **考點**：SAA-4.1｜EBS Snapshots Archive 降低長期保存 snapshot 的成本｜延伸閱讀：第 24 章

### 第 34 題｜SAA｜選兩項｜D1 結帳網站的端到端傳輸加密

一家線上家飾零售商的結帳網站由 internet-facing ALB 轉送到 private subnet 的 EC2。為了符合支付卡產業的要求，公司規定：使用者到 ALB 必須使用 TLS 1.2 以上，ALB 到 EC2 之間的流量也必須加密，並且 ALB 仍要依 URL 路徑把請求分到不同的 target group。

哪兩個步驟能滿足需求？

- A. 以 AWS Certificate Manager（ACM）申請公開憑證，掛在 ALB 的 HTTPS listener，並選擇只允許 TLS 1.2 以上的 security policy
- B. 把 ALB 的 listener 改成 TCP 443，讓 TLS 直接穿透到 EC2 再解密
- C. 在 EC2 的 security group 只允許來自 ALB 的 TCP 443，即可確保 ALB 到 EC2 的流量已加密
- D. 啟用 EBS 預設加密，保護 ALB 與 EC2 之間傳輸中的資料
- E. 在 EC2 上安裝憑證（可以是自簽或私有 CA 簽發的憑證），並把 target group 的協定設為 HTTPS

> [!answer]- 答案：A、E
> **A ✓** ACM 公開憑證免費且自動續約，可直接掛在 ALB；ALB 的 security policy 決定可接受的 TLS 版本與加密套件，選擇 TLS 1.2 以上的政策即可拒絕舊版協定。
>
> **B ✗** ALB 不支援 TCP listener；TLS passthrough 需要使用 NLB，但那樣 ALB 就無法讀取 URL 路徑做路由，違反題目要求。
>
> **C ✗** Port 443 只是連接埠號，不代表流量一定經過 TLS；security group 規則不會加密任何資料。
>
> **D ✗** EBS 加密保護的是磁碟上的靜態資料（at rest），與網路上的傳輸中資料（in transit）無關。
>
> **E ✓** Target group 使用 HTTPS 時，ALB 會與後端重新建立 TLS 連線，把流量加密送到 EC2。ALB 不驗證後端憑證，因此後端可以使用自簽或私有 CA 憑證，達成端到端加密並保留 L7 路由。
>
> **考點**：SAA-1.3｜ALB TLS 終止加上 HTTPS target group 達成傳輸加密｜延伸閱讀：第 10 章、第 15 章

### 第 35 題｜SAA｜單選｜D2 微服務之間的服務探索

一家影音平台把推薦、觀看紀錄、計費等功能拆成十多個 Amazon ECS on AWS Fargate 服務。目前服務之間以設定檔寫死對方 task 的 private IP 呼叫，每當 task 被替換或擴展，IP 改變就導致呼叫失敗，需要人工更新設定。團隊希望服務能以穩定的名稱互相呼叫、新 task 自動被發現，並以最少營運負擔取得服務間呼叫的指標與重試能力。

哪個方案最合適？

- A. 在每個服務前面建立 internet-facing ALB，服務之間改用各 ALB 的 public DNS 名稱互相呼叫
- B. 為所有服務啟用 Amazon ECS Service Connect，使用同一個 AWS Cloud Map namespace，服務以短名稱互相呼叫
- C. 為每個 Fargate task 綁定 Elastic IP，讓 IP 在 task 替換後保持不變
- D. 把每個 task 的 IP 存在 AWS Systems Manager Parameter Store，由 Lambda 在 task 啟動時更新，呼叫端每次呼叫前先查詢

> [!answer]- 答案：B
> **B ✓** Service Connect 以 Cloud Map namespace 註冊服務，ECS 會在每個 task 旁注入受管的 proxy，呼叫端用短名稱即可連到健康的 task，task 替換或擴展時自動更新；proxy 也提供連線重試、逾時設定與服務間流量的 CloudWatch 指標，不必自己部署 service mesh。
>
> **A ✗** Internet-facing ALB 讓內部服務暴露在 Internet，流量繞出 VPC 也增加延遲與費用。即使改成 internal ALB，十多個 ALB 的成本與管理負擔也高於 Service Connect。
>
> **C ✗** Fargate task 無法綁定 Elastic IP，而且以 IP 互相呼叫本身就是問題的根源。
>
> **D ✗** 自建註冊表會有更新延遲與一致性問題，每次呼叫前查詢也增加延遲，還要自己處理健康檢查，等於重做服務探索。
>
> **考點**：SAA-2.1｜ECS Service Connect 與 Cloud Map 提供服務探索｜延伸閱讀：第 21 章

### 第 36 題｜SAA｜單選｜D2 非同步 Lambda 的失敗事件保存

一家美妝電商在訂單成立後，由 Amazon EventBridge 以非同步方式呼叫一個 Lambda 函式，函式再呼叫第三方寄信服務發送訂單確認信。第三方服務偶爾會中斷 30 分鐘以上，事後客服發現有部分客戶沒有收到確認信，而且找不到失敗的是哪些訂單。公司希望保存所有處理失敗的事件，以便服務恢復後重新處理，並且盡量不改動既有的觸發方式。

哪個做法最合適？

- A. 把 Lambda 的 timeout 從 30 秒提高到 15 分鐘，讓函式等待第三方服務恢復
- B. 把 Lambda 的 reserved concurrency 設為 0，等第三方服務恢復後再調回來
- C. 在 Lambda 程式中捕捉例外並把錯誤寫入 CloudWatch Logs，事後再從日誌中撈出訂單編號
- D. 為 Lambda 的非同步呼叫設定 on-failure destination 指向一個 Amazon SQS queue，並設定合適的重試次數與最大事件存留時間

> [!answer]- 答案：D
> **D ✓** 非同步呼叫失敗時，Lambda 會依設定重試（最多 2 次）；仍失敗或超過最大事件存留時間的事件，會連同錯誤資訊送到 on-failure destination。把它指向 SQS queue，失敗的訂單事件就完整保存，服務恢復後可由另一個消費者重新處理，觸發方式完全不變。
>
> **A ✗** 第三方中斷可能超過 15 分鐘，延長 timeout 只會讓函式空等、增加費用，而且超時後事件仍然會遺失。
>
> **B ✗** 把 reserved concurrency 設為 0 會讓所有呼叫被節流，需要人工偵測與切換；非同步事件的保留時間有上限，等太久事件仍會被丟棄。
>
> **C ✗** 寫日誌可以事後追查，但重新處理要靠人工撈資料與補送，容易遺漏，不是可靠的失敗事件保存機制。
>
> **考點**：SAA-2.2｜Lambda 非同步呼叫的 on-failure destination 保存失敗事件｜延伸閱讀：第 19 章

### 第 37 題｜SAA｜單選｜D1 合作夥伴跨帳號寫入 SQS

一家音樂串流平台與一家唱片發行商合作，發行商要在新專輯上架時，從他們自己的 AWS 帳號送出通知訊息到平台帳號中的一個 Amazon SQS queue（使用 SSE-SQS 加密）。平台的資安政策禁止為外部單位建立 IAM user，並要求外部單位只能對這個 queue 送出訊息、不能讀取或刪除。

哪個做法最合適？

- A. 在平台帳號建立 IAM user 並把 access key 交給發行商，user 只附加 `sqs:SendMessage` 權限
- B. 在 queue 的 access policy 中允許發行商帳號的特定 IAM role 執行 `sqs:SendMessage`，發行商再在自己的帳號授予該 role 相同權限
- C. 以 AWS RAM 把 queue 分享給發行商的帳號，並只勾選傳送訊息的權限
- D. 把 queue policy 的 Principal 設為 `*`，並以 `aws:SourceIp` 條件只允許發行商辦公室的 IP 送出訊息

> [!answer]- 答案：B
> **B ✓** SQS 支援 resource-based 的 queue policy，可以直接授權另一個帳號的特定 principal 執行指定動作。跨帳號時兩邊都要允許：平台的 queue policy 允許發行商的 role 執行 `sqs:SendMessage`，發行商的 IAM policy 也允許這個 role 對該 queue ARN 送出訊息。若 queue 改用 customer managed KMS key，還要在 key policy 授權發行商使用金鑰。
>
> **A ✗** 為外部單位建立 IAM user 並交出長期金鑰，直接違反資安政策，金鑰外洩時也難以追查。
>
> **C ✗** SQS queue 不是 AWS RAM 支援共享的資源類型，跨帳號授權要透過 queue policy。
>
> **D ✗** Principal 為 `*` 代表任何人只要從該 IP 發出請求都能送訊息，沒有身份驗證；發行商若從 AWS 上的服務送出，來源 IP 也可能變動。
>
> **考點**：SAA-1.1｜SQS queue policy 的跨帳號授權｜延伸閱讀：第 12 章、第 13 章

### 第 38 題｜SAA｜單選｜D3 結帳 API 的冷啟動延遲

一家電商的結帳 API 由 API Gateway 與 Node.js Lambda 函式組成。每天晚上 8 點到 10 點的直播導購時段，請求量會在 1 分鐘內從每秒 20 次升到每秒 800 次，大量新執行環境的冷啟動讓 p99 延遲超過 3 秒，其他時段延遲正常。公司希望在這個已知時段把延遲穩定控制在 500 毫秒以下，並以合理成本達成。

哪個做法最合適？

- A. 為函式的 alias 設定 provisioned concurrency，並以 Application Auto Scaling 的排程在每天 7:50 提高、10:10 降低
- B. 為函式設定 reserved concurrency 為 1,000，確保尖峰時有足夠的執行環境
- C. 把函式記憶體從 512 MB 提高到 10,240 MB，縮短每次冷啟動的初始化時間
- D. 以 EventBridge 排程規則每 5 分鐘呼叫一次函式，讓執行環境保持熱的狀態

> [!answer]- 答案：A
> **A ✓** Provisioned concurrency 會預先初始化指定數量的執行環境，請求進來時不必冷啟動。尖峰時段已知，用排程只在該時段提高、結束後降低，就不必整天為預熱的容量付費。
>
> **B ✗** Reserved concurrency 只是為函式保留（同時也是限制）併發上限，不會預先建立執行環境，冷啟動仍然存在。
>
> **C ✗** 更多記憶體代表更多 CPU，可以縮短部分初始化時間，但每個新的執行環境仍需冷啟動，而且整天都以 10 GB 計價，成本大幅上升卻無法保證 500 毫秒。
>
> **D ✗** 定期呼叫最多只能讓少數執行環境保持熱的狀態，而尖峰需要數百個同時執行的環境，絕大多數請求仍會遇到冷啟動。
>
> **考點**：SAA-3.2｜Provisioned concurrency 搭配排程消除已知尖峰的冷啟動｜延伸閱讀：第 19 章

### 第 39 題｜SAA｜單選｜D4 穩定運作的關聯式資料庫費用

一家醫療預約平台的正式環境資料庫是 Amazon RDS for MySQL Multi-AZ，instance class 為 db.r6g.2xlarge，24 小時全年運作，CPU 使用率穩定在 50% 到 60%。公司預期未來 3 年架構與規模都不會改變，希望在不影響可用性的前提下，降低這個資料庫的費用。

哪個方案最具成本效益？

- A. 購買 Compute Savings Plans，承諾等同於資料庫每小時費用的金額
- B. 把資料庫遷移到 Aurora Serverless v2，讓容量隨負載自動調整
- C. 每天晚上 12 點到早上 6 點停止 DB instance，以 EventBridge Scheduler 自動停止與啟動
- D. 購買 3 年期、符合該 instance class 與 Multi-AZ 部署的 RDS Reserved Instances

> [!answer]- 答案：D
> **D ✓** 工作負載穩定、24 小時運作、規模三年不變，是 Reserved Instances 的最佳情境。RDS RI 必須對應 engine、instance family 與部署選項（Multi-AZ），承諾 3 年可以取得比 1 年更高的折扣，而且不影響任何可用性設定。
>
> **A ✗** Compute Savings Plans 涵蓋的是 EC2、Fargate 與 Lambda，不涵蓋 RDS，買了對這個資料庫的帳單沒有任何折扣。AWS 另有專門的 Database Savings Plans（涵蓋 Aurora、RDS、DynamoDB、ElastiCache 等），但目前只有 1 年期、無預付，最高折扣約 35%，彈性較高但折扣低於 3 年期 RDS RI；架構三年不變時，3 年期 RI 仍是最省的選擇。
>
> **B ✗** Serverless v2 適合負載變化大或難以預測的資料庫；負載穩定時按 ACU 計費通常比預留的 provisioned instance 貴，還要承擔遷移的工作與風險。
>
> **C ✗** 預約平台 24 小時運作，夜間停機會影響使用者，違反「不影響可用性」。這種排程停止適合開發測試環境。
>
> **考點**：SAA-4.3｜穩定 RDS 工作負載使用 Reserved Instances｜延伸閱讀：第 39 章

### 第 40 題｜SAA｜選兩項｜D2 依病患排序且不重複的訊息處理

一家醫學檢驗中心把檢驗儀器產生的結果訊息送進 Amazon SQS，由後端更新病歷。同一位病患的結果必須依產生順序處理，否則較舊的數值可能覆蓋較新的數值；儀器偶爾會因網路重送同一筆結果，系統不能重複寫入。不同病患之間的結果則應盡量平行處理，以維持吞吐量。

哪兩個設定能滿足需求？

- A. 使用 SQS standard queue，由消費端依訊息中的時間戳記重新排序後再處理
- B. 使用 SQS FIFO queue，並以病患 ID 作為 `MessageGroupId`
- C. 以檢驗結果的唯一編號作為 `MessageDeduplicationId`（或啟用 content-based deduplication）
- D. 使用 SQS FIFO queue，並讓所有訊息使用同一個 `MessageGroupId` 以確保全域順序
- E. 把 queue 的 visibility timeout 設為 0，讓訊息處理失敗時可以立即被其他消費者重試

> [!answer]- 答案：B、C
> **A ✗** Standard queue 只提供 best-effort ordering 與 at-least-once 投遞，同一則訊息可能被送達多次；消費端自行排序要先等所有相關訊息到齊，在分散式消費下很難正確實作。
>
> **B ✓** FIFO queue 保證同一個 message group 內的訊息依序處理，而且同一時間只有一則在處理中。以病患 ID 作為 group，同一病患嚴格有序，不同病患屬於不同 group，可以平行處理。
>
> **C ✓** FIFO queue 在 5 分鐘的去重複時間窗內，會忽略 `MessageDeduplicationId` 相同的訊息。以檢驗結果編號作為去重複 ID，儀器重送的同一筆結果就不會被重複處理。
>
> **D ✗** 所有訊息使用同一個 group，雖然保證全域順序，但整個 queue 只能一次處理一則訊息，吞吐量嚴重受限，違反「不同病患應平行處理」。
>
> **E ✗** Visibility timeout 為 0 代表訊息一被取走就立刻對其他消費者可見，會造成同一則訊息被重複處理，與「不能重複寫入」相反。
>
> **考點**：SAA-2.1｜FIFO queue 的 message group 與 deduplication ID｜延伸閱讀：第 32 章

### 第 41 題｜SAA｜單選｜D1 只允許 ALB 存取後端 instance

一家精密機械製造商的客戶服務入口網站由 internet-facing ALB 轉送到 private subnet 的 EC2，ALB 與 EC2 位於同一個 VPC。資安要求 EC2 只接受來自這個 ALB 的流量；同一個 private subnet 中還有其他團隊的 instance，不應能連到這些 EC2。ALB 節點的 IP 會隨擴展而改變。

應如何設定 EC2 的 security group？

- A. Inbound 規則允許 ALB 所在 public subnet 的 CIDR 存取應用程式 port
- B. Inbound 規則允許整個 VPC 的 CIDR 存取應用程式 port，再以 network ACL 拒絕其他團隊 instance 的 IP
- C. Inbound 規則以 ALB 的 security group ID 作為來源，只允許應用程式 port
- D. Inbound 規則允許 `0.0.0.0/0` 存取應用程式 port，因為 EC2 位於 private subnet，Internet 本來就連不進來

> [!answer]- 答案：C
> **C ✓** Security group 規則可以引用另一個 security group 作為來源，意思是「只要網卡掛著該 security group 就允許」。ALB 節點 IP 怎麼變都不影響，其他團隊的 instance 沒有掛 ALB 的 security group，就無法連入。
>
> **A ✗** 允許整個 public subnet 的 CIDR，任何放在該 subnet 的資源（例如 bastion 或其他服務）都能連入，範圍比「只有 ALB」大；subnet 規劃改變時也要跟著修改。
>
> **B ✗** 允許整個 VPC 範圍過大；NACL 是 subnet 層級、stateless，而且其他團隊的 instance 與 EC2 在同一個 subnet，同 subnet 內的流量根本不經過 NACL 評估，無法用它阻擋。
>
> **D ✗** Private subnet 只代表沒有直接通往 Internet 的路徑，但同一個 VPC、peering 或 VPN 連入的任何來源都能連到這些 EC2，違反最小權限原則。
>
> **考點**：SAA-1.2｜Security group 以另一個 security group 作為來源｜延伸閱讀：第 6 章

### 第 42 題｜SAA｜單選｜D3 零件召回的多層關係查詢

一家電動機車製造商要建立零件追溯系統：每個成品由數十個模組組成，每個模組又由多層子零件與供應商批號組成，總共有數億個關係。發生零件召回時，品保人員要在數秒內查出「某個供應商批號往上影響哪些成品、這些成品賣給哪些經銷商」，查詢深度不固定，常超過 8 層。

哪個資料庫最適合這個查詢模式？

- A. Amazon RDS for PostgreSQL，以 recursive CTE 逐層查詢關聯表
- B. Amazon Neptune，以圖形資料庫儲存零件、成品與經銷商之間的關係，用 Gremlin 或 openCypher 進行多層走訪
- C. Amazon DynamoDB，以 adjacency list 設計儲存每個節點的上下層關係
- D. Amazon Redshift，以星狀結構建立零件與成品的事實表與維度表

> [!answer]- 答案：B
> **B ✓** 「深度不固定的多層關係走訪」是圖形資料庫的核心使用情境。Neptune 把關係本身作為一等資料儲存，從一個節點沿著邊走訪的成本與總資料量關係不大，數億個關係下仍能在秒級完成多層查詢。
>
> **A ✗** Recursive CTE 能表達多層查詢，但每一層都是一次 join，深度超過 8 層、資料數億筆時效能會急遽惡化。關係層數固定且淺時，關聯式資料庫仍是好選擇。
>
> **C ✗** DynamoDB 的 adjacency list 可以有效查詢「一個節點的直接鄰居」，但多層走訪要由應用程式反覆查詢、自行合併，延遲與複雜度都隨深度增加。
>
> **D ✗** Redshift 是為大量資料的彙總分析設計的資料倉儲，不擅長逐層的關係走訪，也不是秒級互動查詢的最佳選擇。
>
> **考點**：SAA-3.3｜多層關係查詢選擇圖形資料庫 Neptune｜延伸閱讀：第 29 章

### 第 43 題｜SAA｜單選｜D4 大量資料傳回地端的傳輸費用

一家影視後製公司在 AWS 上完成剪輯與調色，每月要把約 300 TB 的成品從 S3 傳回位於台北的地端母帶歸檔系統，目前透過 Internet 下載，資料傳出（data transfer out）費用很高。這個傳輸量會持續至少 3 年，公司的機房已經位於有 AWS Direct Connect location 的資料中心內。

哪個方案最具成本效益？

- A. 建立 AWS Direct Connect 連線，讓地端經由 Direct Connect 從 S3 下載成品
- B. 為 bucket 啟用 S3 Transfer Acceleration，加快並降低下載的成本
- C. 建立 Site-to-Site VPN 並啟用 accelerated VPN，透過 VPN tunnel 下載成品
- D. 把 bucket 改為 Requester Pays，讓下載端支付資料傳出費用

> [!answer]- 答案：A
> **A ✓** 經由 Direct Connect 傳出的資料，以較低的 DX data transfer out 費率計價，再加上連接埠的小時費。每月 300 TB、持續 3 年的穩定大量傳輸，省下的傳輸費遠超過連接埠費用；機房已在 Direct Connect location，建立 cross-connect 也相對容易。
>
> **B ✗** Transfer Acceleration 透過 edge location 加速長距離傳輸，但是在一般傳輸費之外另外收費，只會更貴。
>
> **C ✗** VPN 仍然跑在 Internet 上，資料傳出仍以一般 Internet 費率計價，還要加上 VPN 連線費與 accelerated VPN 的 Global Accelerator 費用。
>
> **D ✗** Requester Pays 是讓「其他帳號的下載者」支付請求與傳輸費；這裡下載者就是公司自己，費用只是換一個帳號付，總成本不變。
>
> **考點**：SAA-4.4｜大量穩定傳回地端時，Direct Connect 的傳出費率較低｜延伸閱讀：第 8 章、第 39 章

### 第 44 題｜SAA｜單選｜D1 限制 KMS 金鑰只能經由 S3 使用

一家基因檢測公司以 SSE-KMS（customer managed key）加密存放檢測報告的 S3 bucket。分析應用程式使用的 IAM role 需要透過 S3 讀寫這些報告；資安要求這個 role 即使取得了加密的 data key，也不能直接呼叫 KMS `Decrypt` API 在 S3 之外解密資料。目前這把金鑰的使用權限只由 key policy 授予。

哪個做法最能滿足需求？

- A. 在 key policy 授權該 role 使用金鑰的 statement 中，加入 `kms:ViaService` 條件，值為 `s3.<region>.amazonaws.com`
- B. 以 SCP 拒絕所有成員帳號的 `kms:Decrypt` 動作，只保留 `kms:GenerateDataKey`
- C. 在該 role 的 IAM policy 加入對 `kms:*` 的 explicit deny
- D. 為金鑰啟用自動輪替，讓外洩的 data key 在一年後失效

> [!answer]- 答案：A
> **A ✓** `kms:ViaService` 條件限制金鑰只能在「由指定 AWS 服務代表 principal 發出」的請求中使用。加上 `s3.<region>.amazonaws.com` 後，role 透過 S3 讀寫物件時可正常加解密，但自己直接呼叫 KMS API 時條件不成立，請求被拒絕。
>
> **B ✗** S3 讀取 SSE-KMS 物件時，會以呼叫者的身份向 KMS 發出 `Decrypt` 請求；用 SCP 拒絕 `kms:Decrypt` 會讓 S3 也無法解密，應用程式完全讀不到報告。
>
> **C ✗** Explicit deny 優先於任何 allow，對 `kms:*` 的 deny 同樣會阻擋 S3 代表該 role 發出的 KMS 請求，應用程式無法讀寫加密物件。
>
> **D ✗** 自動輪替只產生新的金鑰材料，舊的材料仍會保留以解密既有資料，不會讓任何 data key 失效，也無法限制 API 的使用方式。
>
> **考點**：SAA-1.3｜以 kms:ViaService 條件限制金鑰只能經由特定服務使用｜延伸閱讀：第 15 章

### 第 45 題｜SAA｜選兩項｜D2 觀看紀錄 API 的跨 Region 容錯

一家串流影音平台的「繼續觀看」API 部署在 us-east-1，後端資料存在 Amazon DynamoDB。平台要求 Region 層級故障時，API 必須在數分鐘內自動切換到 us-west-2，資料最多只能遺失數秒；團隊已經用 IaC 在 us-west-2 部署好同樣的無狀態 API（API Gateway 與 Lambda）。

哪兩個步驟的組合能滿足需求？

- A. 在 us-west-2 以每小時一次的 DynamoDB on-demand backup 還原資料表
- B. 在 Amazon Route 53 為 API 網域建立 failover routing records，primary 指向 us-east-1、secondary 指向 us-west-2，並為 primary 設定 health check
- C. 在 API 前面建立 Amazon CloudFront，並啟用 geographic restriction 只服務特定國家
- D. 以 S3 Cross-Region Replication 每 15 分鐘把 DynamoDB 匯出的資料複寫到 us-west-2
- E. 把資料表轉換成 DynamoDB global table，在 us-west-2 加入 replica

> [!answer]- 答案：B、E
> **A ✗** 每小時備份代表最多遺失一小時的資料，還原大型資料表也需要時間，不符合「數秒」的 RPO 與「數分鐘」的 RTO。
>
> **B ✓** Failover routing 在 primary 的 health check 失敗時，自動把 DNS 回應改為 secondary，讓用戶端連到 us-west-2 的 API，不需要人工介入。
>
> **C ✗** Geo restriction 控制「誰能存取」，與 Region 故障的容錯無關。
>
> **D ✗** 每 15 分鐘的匯出與複寫，RPO 至少 15 分鐘，切換後還要匯入資料，不符合需求。
>
> **E ✓** Global table 在多個 Region 之間自動、非同步地複寫資料，跨 Region 複寫延遲通常在一秒左右，每個 replica 都可讀寫。us-east-1 故障時，us-west-2 的 API 直接使用當地 replica 繼續服務。
>
> **考點**：SAA-2.2｜Route 53 failover routing 搭配 DynamoDB global tables｜延伸閱讀：第 9 章、第 27 章

### 第 46 題｜SAA｜單選｜D3 私有存取第三方 AI 判讀服務

一家醫院要使用某家醫療 AI 廠商的影像判讀 API，廠商的服務部署在自己的 AWS 帳號中，以 Network Load Balancer 對外提供。醫院的 VPC 與廠商的 VPC 使用重疊的 CIDR（都是 `10.0.0.0/16`），醫院規定影像流量不得經過 Internet，而且廠商不能存取醫院 VPC 中的其他資源。

哪個方案最合適？

- A. 在兩個 VPC 之間建立 VPC peering，並只在 route table 中加入廠商 NLB 的 IP
- B. 兩個帳號都連到同一個 AWS Transit Gateway，以 TGW route table 只傳遞 NLB 所在 subnet 的路由
- C. 在兩個 VPC 之間建立 Site-to-Site VPN，透過加密的 tunnel 呼叫廠商的 API
- D. 由廠商以 NLB 建立 VPC endpoint service，醫院在自己的 VPC 建立 interface VPC endpoint 連到該服務

> [!answer]- 答案：D
> **D ✓** AWS PrivateLink 讓醫院在自己的 subnet 中取得一張代表廠商服務的網卡（interface endpoint），流量走 AWS 內部網路、不經 Internet。連線只能由醫院單向發起到該服務，廠商無法看到醫院 VPC 的其他資源；而且因為不需要互相路由，重疊的 CIDR 不是問題。
>
> **A ✗** VPC peering 不允許 CIDR 重疊的 VPC 建立連線。即使 CIDR 不重疊，peering 也會讓兩邊的網路可以雙向路由，暴露範圍大於需求。
>
> **B ✗** Transit Gateway 依路由轉送流量，CIDR 重疊時無法正確路由；它也是多 VPC 互連的網路層方案，對單一 API 的存取來說過於複雜。
>
> **C ✗** VPC 之間的 Site-to-Site VPN 同樣依路由運作，重疊 CIDR 無法直接互通，而且需要在 VPC 中自行架設 VPN 設備，營運負擔高。
>
> **考點**：SAA-3.4｜PrivateLink 在 CIDR 重疊時提供單向的私有服務存取｜延伸閱讀：第 7 章

### 第 47 題｜SAA｜單選｜D1 防止 SSRF 竊取 instance 憑證

一家電商的商品頁面有一個「從網址匯入商品圖片」的功能，由 EC2 上的應用程式代為下載使用者提供的 URL。弱點掃描發現，攻擊者可以輸入 `http://169.254.169.254/latest/meta-data/iam/security-credentials/` 讓伺服器把 instance role 的臨時憑證回傳出來。修正程式的輸入驗證需要數週，公司希望先以 AWS 設定立即降低憑證被竊取的風險。

哪個做法最有效？

- A. 把應用程式需要的權限改用 access key 存在環境變數中，並移除 instance role
- B. 在 EC2 的 security group 加入 outbound 規則，阻擋連到 `169.254.169.254`
- C. 修改 instance metadata 選項，要求使用 IMDSv2（HttpTokens 設為 required），並把 PUT 回應的 hop limit 設為 1
- D. 縮短 instance role 臨時憑證的有效時間，讓竊取到的憑證很快失效

> [!answer]- 答案：C
> **C ✓** IMDSv2 要求先以 HTTP PUT 取得 session token，之後的請求都要在標頭帶上 token。一般 SSRF 只能讓伺服器發出單純的 GET 請求、無法帶自訂標頭，因此拿不到憑證；hop limit 設為 1 也避免 token 被轉送到 instance 以外（例如 container 或 proxy）。
>
> **A ✗** 改用長期 access key 讓問題更嚴重：環境變數同樣可能被讀取，外洩後也不會自動失效。
>
> **B ✗** Security group 不會過濾 instance 到 instance metadata service（link-local 位址）的流量，這條規則沒有效果。
>
> **D ✗** EC2 instance role 的臨時憑證由 AWS 自動輪替，使用者無法自行設定縮短；而且即使有效時間較短，攻擊者仍可在有效期內濫用，也可以反覆竊取。
>
> **考點**：SAA-1.2｜強制 IMDSv2 防止 SSRF 竊取 instance 憑證｜延伸閱讀：第 17 章

### 第 48 題｜SAA｜單選｜D3 即時熱門影片排行

一家短影音平台把每次播放事件寫入 Amazon Kinesis Data Streams，每秒約 20 萬筆。產品團隊要在首頁顯示「過去 10 分鐘最熱門的 100 部影片」，每 10 秒更新一次，排行必須涵蓋所有 shard 的資料。團隊希望以最少營運負擔完成串流彙總。

哪個方案最合適？

- A. 以 Amazon Data Firehose 把事件寫入 S3，再每 10 秒以 Amazon Athena 查詢最近 10 分鐘的資料
- B. 以 Lambda 作為 stream 的 consumer，每個 shard 的批次各自計算該 shard 的前 100 名，分別寫入 DynamoDB 供首頁讀取
- C. 以 Amazon Managed Service for Apache Flink 讀取 stream，使用 sliding window 計算熱門排行並把結果寫入快取
- D. 在 Amazon EMR 叢集上執行 Spark Structured Streaming 讀取 stream 並計算排行

> [!answer]- 答案：C
> **C ✓** Managed Service for Apache Flink 是全受管的串流處理服務，原生支援時間窗（tumbling、sliding）與有狀態的彙總，能跨所有 shard 計算全域排行，並以秒級延遲持續輸出結果，不必管理叢集。
>
> **A ✗** Firehose 會先緩衝再寫入，加上每 10 秒以 Athena 掃描大量小檔案，延遲與查詢成本都不符合需求；Athena 適合偶發的互動分析，不適合高頻的即時彙總。
>
> **B ✗** Lambda 對 Kinesis 的處理以 shard 為單位，各 shard 的狀態彼此獨立；把每個 shard 的前 100 名分別寫出，並不等於全域的前 100 名，要正確合併還得自行維護跨 shard 的狀態與時間窗。若只需要逐筆轉換或簡單的單 shard 彙總，Lambda 才是輕量的選擇。
>
> **D ✗** Spark Structured Streaming 能完成這項工作，但要自行管理 EMR 叢集的規模、版本與故障，營運負擔高於受管的 Flink。
>
> **考點**：SAA-3.5｜Managed Service for Apache Flink 進行即時時間窗彙總｜延伸閱讀：第 31 章

### 第 49 題｜SAA｜單選｜D4 低流量內部 API 的運算成本

一家文具連鎖店的內部庫存查詢 API 由兩台 m5.large EC2 全天候運作，前面有 ALB。這個 API 每天只有約 5,000 次請求，集中在門市營業時間，每次處理約 200 毫秒，平均 CPU 使用率不到 3%。公司希望大幅降低這個 API 的運算成本，並維持高可用。

哪個方案最具成本效益？

- A. 為兩台 m5.large 購買 3 年期的 Standard Reserved Instances
- B. 把 API 改寫成 Lambda 函式，透過 Amazon API Gateway HTTP API 提供服務
- C. 把兩台 instance 改成 Spot instance，以降低每小時費用
- D. 把 instance 縮小為兩台 t3.nano，並保留 ALB 與跨 AZ 部署

> [!answer]- 答案：B
> **B ✓** Lambda 以請求數與實際執行時間計費，每天 5,000 次、每次 200 毫秒的用量極小，幾乎落在每月免費額度內；Lambda 與 HTTP API 都是跨 AZ 的受管服務，本身即具備高可用，也省下 ALB 的固定費用。
>
> **A ✗** RI 降低的是單價，但兩台 instance 仍有 97% 的時間閒置，持續為未使用的容量付費。
>
> **C ✗** Spot instance 可能被中斷，兩台同時被回收時 API 就無法服務，不符合高可用；也仍然為閒置時間付費。
>
> **D ✗** 縮小 instance 確實降低成本，但仍需支付兩台 instance 與 ALB 的全天候費用，比 Lambda 加 HTTP API 貴。
>
> **考點**：SAA-4.2｜低使用率工作負載改用按用量計費的 serverless｜延伸閱讀：第 19 章、第 20 章

### 第 50 題｜SAA｜單選｜D1 大型賽事直播的 DDoS 防護

一家運動媒體即將轉播一場國際賽事，網站與 API 透過 Amazon CloudFront、Route 53 與 ALB 對外服務。過去類似賽事曾遭遇大規模 DDoS 攻擊，為了擋攻擊而自動擴展的資源產生了大筆費用。公司希望在賽事期間取得 AWS 專家的 24 小時協助、針對應用層攻擊的進階偵測，以及因 DDoS 造成的擴展費用保護。

哪個方案最合適？

- A. 依賴預設啟用的 AWS Shield Standard，並把 Auto Scaling group 的最大容量調高
- B. 在 CloudFront 掛載 AWS WAF，只設定 rate-based rule 限制每個 IP 的請求數
- C. 啟用 Amazon GuardDuty，在偵測到 DDoS 時以 EventBridge 通知值班人員
- D. 訂閱 AWS Shield Advanced，把 CloudFront distribution、Route 53 hosted zone 與 ALB 加入保護資源，並啟用 Shield Response Team 的協助

> [!answer]- 答案：D
> **D ✓** Shield Advanced 為受保護的資源提供進階的 DDoS 偵測與緩解、24 小時的 Shield Response Team（SRT）支援，以及 DDoS 造成的擴展費用保護（cost protection），正好對應題目的三個需求；它也包含受保護資源上的 AWS WAF 使用費用。
>
> **A ✗** Shield Standard 自動防護常見的第 3／4 層攻擊，但沒有 SRT 協助與費用保護；調高擴展上限只會讓攻擊期間的費用更高。
>
> **B ✗** WAF rate-based rule 能緩解部分應用層洪水攻擊，但不提供專家協助與費用保護，面對分散式、大量來源的攻擊效果有限。
>
> **C ✗** GuardDuty 是帳號與工作負載的威脅偵測服務，不是 DDoS 緩解服務，也沒有 SRT 與費用保護。
>
> **考點**：SAA-1.2｜Shield Advanced 的 SRT 支援與 DDoS 費用保護｜延伸閱讀：第 16 章

### 第 51 題｜SAA｜選兩項｜D2 設備告警事件的路由

一家塑膠射出廠的地端製造執行系統（MES）每天產生數萬筆設備告警事件，要送到 AWS 上的多個系統：嚴重等級為 critical 的事件要立即觸發值班通知的 Lambda、所有事件都要存檔、維修部門的另一個 AWS 帳號只需要收到與模具相關的事件。公司希望之後新增接收者時不必修改 MES，並以最少的自訂程式完成路由。

哪兩個步驟的組合能滿足需求？

- A. 建立一個 Amazon EventBridge custom event bus，讓 MES 以 `PutEvents` API 把告警事件送到這個 bus
- B. 讓 MES 把所有事件寫入一個 Amazon SQS queue，再由各系統輪詢同一個 queue 並自行過濾
- C. 建立只有一個 shard 的 Kinesis data stream，讓所有接收者以同一個 consumer application 讀取
- D. 在 event bus 上建立多條 rule，以 event pattern 依嚴重等級與設備類型過濾，分別以 Lambda、存檔用的 Data Firehose 與維修帳號的 event bus 作為 target
- E. 撰寫一個路由用的 Lambda 函式，以 if-else 判斷事件內容後逐一呼叫每個接收系統的 API

> [!answer]- 答案：A、D
> **A ✓** EventBridge custom event bus 是事件路由的中心點，MES 只需要把事件送到 bus，不需要知道誰會接收；`PutEvents` 可以從地端以 IAM 憑證呼叫。
>
> **B ✗** 多個系統輪詢同一個 queue 會互相搶訊息，每則訊息只會被其中一個系統處理；各自過濾也是自訂程式。
>
> **C ✗** 單一 shard 有吞吐量上限，而且所有接收者共用同一個 consumer application，無法各自獨立處理與過濾，新增接收者也要修改程式。
>
> **D ✓** Rule 以宣告式的 event pattern 過濾事件內容，一個事件可以同時符合多條 rule，送到各自的 target；跨帳號時以另一個帳號的 event bus 作為 target，再由對方的 bus policy 允許接收。新增接收者只要新增 rule，不必改 MES。
>
> **E ✗** 自訂路由函式把所有接收者的邏輯集中在一處，新增接收者就要修改程式並重新部署，也要自己處理重試，與「最少自訂程式」相反。
>
> **考點**：SAA-2.1｜EventBridge custom bus 與 rule 的內容過濾與跨帳號路由｜延伸閱讀：第 32 章

### 第 52 題｜SAA｜單選｜D3 EFS 吞吐量額度耗盡

一家電商的內容管理系統把商品素材存在 Amazon EFS，檔案系統只有約 200 GiB，使用 Bursting throughput mode。大型促銷前，設計團隊會在短時間內大量上傳與讀取素材，此時吞吐量會先衝高、接著大幅下降，CloudWatch 顯示 `BurstCreditBalance` 降到 0。其餘時間的吞吐量需求很低，而且尖峰時間每次都不同。

哪個做法最能以符合成本的方式解決問題？

- A. 把 throughput mode 改為 Elastic throughput
- B. 把 performance mode 改為 Max I/O
- C. 在檔案系統中寫入大量填充檔，把容量提高到數 TiB 以取得更多的 burst credit
- D. 把 throughput mode 改為 Provisioned throughput，並設定為尖峰所需的吞吐量

> [!answer]- 答案：A
> **A ✓** Bursting mode 的基準吞吐量隨儲存容量增加，小容量檔案系統的 credit 很快會用完。Elastic throughput 會依工作負載自動擴展吞吐量，按實際讀寫的資料量計費，最適合尖峰難以預測、平時用量低的情境。
>
> **B ✗** Max I/O 是為大量平行存取設計的 performance mode，改善的是每秒操作數的上限，代價是較高的延遲；它不提高吞吐量，也解決不了 credit 耗盡。而且 performance mode 在檔案系統建立後就無法修改。
>
> **C ✗** 塞填充檔是 Elastic throughput 推出前的舊做法，要為不需要的儲存空間付費，也很難精準估算所需的容量。
>
> **D ✗** Provisioned throughput 可以保證吞吐量，但無論是否使用都以設定值計費；尖峰短暫且時間不定時，長期為尖峰容量付費並不划算。如果吞吐量需求穩定且高，它才是較好的選擇。
>
> **考點**：SAA-3.1｜EFS Elastic throughput 處理難以預測的吞吐量尖峰｜延伸閱讀：第 24 章

### 第 53 題｜SAA｜單選｜D4 存取模式無法預測的資料湖儲存

一家跨境電商的資料湖 bucket 存放約 2 PB 的訂單、點擊與商品資料，物件平均約 20 MB。不同部門的分析需求經常改變：有些資料集放了半年沒人碰，某天又突然被頻繁查詢好幾週，事前無法判斷哪些資料會被讀取。目前全部存在 S3 Standard，公司希望降低儲存費用，同時不讓被重新使用的資料產生取回費用或延遲。

哪個方案最具成本效益？

- A. 設定 lifecycle rule，所有物件建立 30 天後轉換到 S3 Standard-IA
- B. 設定 lifecycle rule，所有物件建立 90 天後轉換到 S3 Glacier Instant Retrieval
- C. 設定 lifecycle rule，所有物件建立 30 天後轉換到 S3 One Zone-IA
- D. 把物件轉換到 S3 Intelligent-Tiering，由 S3 依每個物件的實際存取情況自動移動層級

> [!answer]- 答案：D
> **D ✓** Intelligent-Tiering 監控每個物件的存取情況，30 天未存取移到 Infrequent Access 層、90 天未存取移到 Archive Instant Access 層，一旦再次被存取就自動移回 Frequent Access 層，沒有取回費用，延遲也維持毫秒級。只需支付每個物件的小額監控費，平均 20 MB 的物件監控費相對很小（小於 128 KB 的物件不會被自動分層）。
>
> **A ✗** Standard-IA 有每 GB 的取回費用與 30 天最短保存期。被重新頻繁查詢好幾週的資料集，取回費用可能超過省下的儲存費。存取模式已知「很少讀取」時，它才划算。
>
> **B ✗** Glacier Instant Retrieval 儲存單價更低，但取回費用更高、最短保存 90 天，對會突然被大量查詢的資料風險最大。
>
> **C ✗** One Zone-IA 同樣有取回費用，而且只存在單一 AZ，資料湖的原始資料若無法重建，不應承擔 AZ 損毀的風險。
>
> **考點**：SAA-4.1｜存取模式無法預測時選擇 S3 Intelligent-Tiering｜延伸閱讀：第 23 章

### 第 54 題｜SAA｜單選｜D1 以既有 AD 帳號登入多個 AWS 帳號

一家醫學中心的 2,000 名員工使用地端的 Microsoft Active Directory 帳號登入院內系統。醫學中心在 AWS Organizations 中有 25 個 AWS 帳號，資訊部門希望員工以既有的 AD 帳號密碼登入 AWS console，依 AD 群組在不同帳號取得不同權限，人員離職停用 AD 帳號後即自動失去 AWS 存取，並以最少營運負擔管理。

哪個方案最合適？

- A. 以腳本每天從 AD 匯出員工清單，在每個 AWS 帳號中建立對應的 IAM user 與 group
- B. 啟用 AWS IAM Identity Center，以 AD Connector 連接地端 AD 作為 identity source，再把 permission set 指派給 AD 群組與對應的帳號
- C. 建立 Amazon Cognito user pool，以 SAML 與 AD FS 聯合，讓員工登入後取得 AWS console 存取
- D. 在 25 個帳號中各自設定 SAML identity provider 與 IAM role，由 AD FS 發出 SAML assertion 對應到各帳號的 role

> [!answer]- 答案：B
> **B ✓** IAM Identity Center 是多帳號員工存取的集中入口。透過 AD Connector（或 AWS Managed Microsoft AD 的信任關係）使用地端 AD 作為身份來源，員工以 AD 帳號登入；permission set 指派給 AD 群組後，Identity Center 會自動在對應帳號建立 role。AD 帳號停用後就無法再登入。
>
> **A ✗** 在 25 個帳號複製 2,000 個 IAM user，會產生大量長期憑證與同步延遲，離職時也可能漏刪，營運負擔最大。
>
> **C ✗** Cognito user pool 是給應用程式的終端使用者使用，不是登入 AWS console 的員工身份方案。
>
> **D ✗** 每個帳號各自設定 SAML 聯合技術上可行，但 25 個帳號的 IdP、role 與 AD FS 規則都要個別維護，新增帳號時也要重做，營運負擔高於 Identity Center 的集中管理。
>
> **考點**：SAA-1.1｜IAM Identity Center 搭配 AD 作為多帳號的員工身份來源｜延伸閱讀：第 13 章

### 第 55 題｜SAA｜單選｜D2 應用程式故障但 instance 未被替換

一家健康管理 App 的 API 跑在 ALB 後方、跨兩個 AZ 的 EC2 Auto Scaling group。某天其中一台 instance 的應用程式行程卡死，對所有請求回應 HTTP 500；ALB 的 target health check 已把它標記為 unhealthy 並停止送流量，但這台 instance 持續存在好幾個小時，Auto Scaling group 沒有替換它，導致整體容量下降。

哪個做法能讓這類故障自動恢復？

- A. 為 instance 建立 CloudWatch alarm，在 `StatusCheckFailed_System` 時執行 EC2 recover 動作
- B. 把 ALB 的 health check 間隔縮短為 5 秒、unhealthy threshold 設為 2
- C. 把 Auto Scaling group 的 health check type 設為 ELB，讓 ASG 同時依據 ALB 的 health check 結果判斷 instance 健康狀態
- D. 啟用 ALB 的 cross-zone load balancing，讓流量平均分散到所有健康的 instance

> [!answer]- 答案：C
> **C ✓** Auto Scaling group 預設只依 EC2 status check 判斷健康，應用程式卡死時 instance 本身仍「健康」，所以不會被替換。把 health check type 設為 ELB 後，ALB 判定 unhealthy 的 instance 也會被 ASG 視為不健康，自動終止並啟動新的 instance。
>
> **A ✗** System status check 檢查的是底層硬體與網路，應用程式行程卡死不會讓它失敗，recover 動作也只是把同一台 instance 搬到新硬體，不會修好應用程式。
>
> **B ✗** 縮短 health check 間隔只會讓 ALB 更快停止送流量，ASG 仍然不知道 instance 不健康，容量下降的問題依舊存在。
>
> **D ✗** Cross-zone load balancing 影響的是流量在 AZ 之間的分配方式，不會替換故障的 instance。
>
> **考點**：SAA-2.2｜ASG health check type 設為 ELB 以替換應用層故障的 instance｜延伸閱讀：第 18 章

### 第 56 題｜SAA｜單選｜D2 AZ 故障時不降級的容量規劃

一家體育直播平台的影像前處理服務在 us-east-1 跑在 Auto Scaling group 上，使用 3 個 AZ。服務在尖峰時段需要 12 台 instance 才能維持效能。過去經驗顯示，某個 AZ 故障時，Auto Scaling 在其他 AZ 補足 instance 需要 10 到 15 分鐘，而直播期間不允許任何效能降級。

在成本最低的前提下，Auto Scaling group 應如何設定容量？

- A. 在 3 個 AZ 平均部署 18 台 instance（每個 AZ 6 台）
- B. 在 3 個 AZ 平均部署 12 台 instance（每個 AZ 4 台），搭配 target tracking scaling policy
- C. 只使用 2 個 AZ，平均部署 24 台 instance（每個 AZ 12 台）
- D. 在 3 個 AZ 平均部署 15 台 instance（每個 AZ 5 台）

> [!answer]- 答案：A
> **A ✓** 要在一個 AZ 故障「當下」仍有 12 台，剩下的 2 個 AZ 必須合計有 12 台，也就是每個 AZ 6 台，總共 18 台。這種「預先保留足夠容量、不依賴故障時的擴展動作」的設計稱為 static stability。
>
> **B ✗** 失去一個 AZ 後只剩 8 台，必須等 10 到 15 分鐘的擴展才能補回，這段時間效能會降級。
>
> **C ✗** 2 個 AZ 各 12 台同樣能承受一個 AZ 故障，但總共要 24 台，比 3 個 AZ 的 18 台貴；AZ 數越多，每個 AZ 需要預留的額外容量越少。
>
> **D ✗** 失去一個 AZ 後只剩 10 台，低於所需的 12 台。
>
> **考點**：SAA-2.2｜Static stability：以 AZ 數計算預留容量｜延伸閱讀：第 18 章、第 34 章

### 第 57 題｜SAA｜選兩項｜D1 防止繞過 CloudFront 直接存取 ALB

一家戶外用品電商的網站以 Amazon CloudFront 作為入口，origin 是一個 internet-facing ALB，AWS WAF 掛在 CloudFront 上。資安團隊發現攻擊者直接對 ALB 的 DNS 名稱發送請求，繞過了 CloudFront 上的 WAF 規則。由於其他系統的整合限制，這個 ALB 暫時必須維持 internet-facing。

哪兩個步驟的組合最能確保只有經過 CloudFront 的請求能到達應用程式？

- A. 在 ALB 的 security group 只允許 CloudFront edge location 的 public IP，並每月手動更新 IP 清單
- B. 為 ALB 另外掛一個 AWS WAF web ACL，以 geo match 規則只允許公司營運的國家
- C. 在 ALB 的 security group inbound 規則中，以 AWS managed prefix list `com.amazonaws.global.cloudfront.origin-facing` 作為來源
- D. 在 ALB 前面加一個 NLB，只把 NLB 的 IP 提供給 CloudFront
- E. 在 CloudFront 的 origin 設定加入一個秘密的自訂標頭，ALB listener rule 只轉送帶有正確標頭值的請求，其他請求回應 403

> [!answer]- 答案：C、E
> **A ✗** CloudFront 的 IP 範圍會變動，手動維護容易出錯；而且 security group 的規則數有限，直接列出所有 IP 很快就會超過上限。
>
> **B ✗** Geo match 只能依國家過濾，攻擊者在允許的國家仍能直接打 ALB，而且這是在補一套 WAF，而不是讓請求一定經過 CloudFront。
>
> **C ✓** AWS 管理的 CloudFront origin-facing prefix list 會自動維護 CloudFront 連到 origin 時使用的 IP 範圍。把它作為 security group 的來源，ALB 只接受從 CloudFront 網路發出的連線，Internet 上的其他來源直接被擋下。
>
> **D ✗** 多加一層 NLB 並不能阻止任何人直接連到 NLB 的 IP，只是把同樣的問題移到另一個入口。
>
> **E ✓** Prefix list 只能確認流量來自 CloudFront，但其他人也可以建立自己的 CloudFront distribution 指向這個 ALB。自訂標頭的秘密值只有自己的 distribution 會加上，ALB 以 listener rule 驗證，兩者結合才能確保請求來自「自己的」distribution。若之後可以改架構，CloudFront VPC origins 能讓 ALB 改放在 private subnet。
>
> **考點**：SAA-1.2｜CloudFront origin-facing prefix list 加自訂標頭保護 ALB origin｜延伸閱讀：第 11 章、第 16 章

### 第 58 題｜SAA｜單選｜D4 熱門讀取的資料庫成本

一家線上書店的 Amazon RDS for MySQL 有 4 個 db.r6g.4xlarge 的 read replica 承接商品頁的查詢。分析顯示 90% 的讀取集中在約 2 萬本熱門書籍的詳細資料，這些資料每天只更新數次，業務可以接受商品頁顯示最多 5 分鐘前的資料。財務希望在維持頁面效能的前提下降低資料庫相關費用。

哪個方案最具成本效益？

- A. 遷移到 Amazon Aurora MySQL，把 read replica 增加到 15 個以分散負載
- B. 把 4 個 read replica 都升級成更大的 instance class，減少查詢延遲
- C. 在應用程式與資料庫之間加入 Amazon RDS Proxy，讓 4 個 replica 共用連線池
- D. 以 Amazon ElastiCache（Redis OSS 相容）實作 cache-aside，熱門書籍資料設定 5 分鐘 TTL，再把 read replica 縮減為 1 個

> [!answer]- 答案：D
> **D ✓** 讀取高度集中在少量熱門資料、可接受數分鐘的舊資料，是快取的典型情境。Cache-aside 讓絕大多數讀取由記憶體中的快取回應，延遲更低；TTL 設為 5 分鐘符合資料新鮮度要求。資料庫負載大幅下降後，只需保留 1 個 replica，快取節點的費用遠低於 3 個大型 replica。
>
> **A ✗** 增加 replica 數量提高的是讀取容量，但費用隨 replica 數量增加，與降低成本的目標相反。
>
> **B ✗** 升級規格同樣增加費用，而且重複讀取同一批資料的問題沒有被解決。
>
> **C ✗** RDS Proxy 管理連線池，解決的是連線數問題，不會減少查詢量，也不會讓 replica 數量可以縮減。
>
> **考點**：SAA-4.3｜以快取吸收熱點讀取並縮減 read replica｜延伸閱讀：第 28 章

### 第 59 題｜SAA｜單選｜D4 以儲存為主的 DynamoDB 費用

一家工具機製造商把設備維修紀錄存在 Amazon DynamoDB，資料表約 30 TB 且持續成長，帳單顯示儲存費用占該資料表費用約 80%。超過一年的紀錄很少被讀取，但維修 App 仍需能以毫秒級延遲查詢任意一筆歷史紀錄，而且紀錄必須永久保存。

哪個方案最具成本效益？

- A. 把超過一年的紀錄匯出到 S3 後從資料表刪除，需要時以 Amazon Athena 查詢
- B. 把資料表的 table class 改為 DynamoDB Standard-Infrequent Access（Standard-IA）
- C. 啟用 TTL，自動刪除超過兩年的紀錄
- D. 把資料表的 capacity mode 從 provisioned 改為 on-demand

> [!answer]- 答案：B
> **B ✓** Standard-IA table class 的儲存單價明顯低於 Standard，讀寫單價則較高，適合「儲存費用占大宗、存取頻率低」的資料表。修改 table class 不影響效能與 API，App 仍以相同方式進行毫秒級查詢。
>
> **A ✗** 匯出到 S3 能降低儲存成本，但 Athena 查詢需要數秒以上，App 也要改寫兩套查詢路徑，不符合「毫秒級查詢任意紀錄」。
>
> **C ✗** TTL 會刪除資料，違反「永久保存」的要求。
>
> **D ✗** Capacity mode 影響的是讀寫的計費方式，與占 80% 的儲存費用無關。
>
> **考點**：SAA-4.3｜DynamoDB Standard-IA table class 降低儲存為主的成本｜延伸閱讀：第 27 章

### 第 60 題｜SAA｜單選｜D1 強制新建 EBS volume 加密

一家動畫公司的 AWS 帳號中，多個團隊會自行建立 EC2 與 EBS volume，只使用 us-east-1 與 ap-northeast-1 兩個 Region。新的資安政策要求：之後建立的所有 EBS volume 都必須以公司指定的 KMS customer managed key 加密，而且不能依賴各團隊記得勾選加密。

哪個做法最能以最少營運負擔滿足需求？

- A. 啟用 AWS Config managed rule `encrypted-volumes`，發現未加密的 volume 時以 SNS 通知擁有者
- B. 把公司提供的 golden AMI 全部改為加密 AMI，並要求各團隊只使用這些 AMI
- C. 在兩個 Region 啟用 EBS encryption by default，並把預設的 KMS key 設為公司指定的 customer managed key
- D. 以 EventBridge 監聽 `CreateVolume` 事件，觸發 Lambda 在 volume 建立後直接把它改為加密

> [!answer]- 答案：C
> **C ✓** EBS encryption by default 是每個 Region 的帳號層級設定，啟用後該 Region 新建的所有 EBS volume（包括從未加密 snapshot 建立的 volume）都會自動加密，並使用指定的預設 KMS key，不需要各團隊做任何設定。
>
> **A ✗** Config rule 是偵測性控制，只能在 volume 建立後發現與通知，不能阻止未加密的 volume 被建立與使用。
>
> **B ✗** 加密 AMI 只保證從這些 AMI 啟動的 root volume 加密，團隊另外建立的空白 data volume 或使用其他 AMI 時仍可能未加密。
>
> **D ✗** 既有的 EBS volume 無法原地改為加密，必須透過 snapshot 複製並加密後再建立新 volume，Lambda 無法「直接」完成，流程也會中斷使用中的 instance。
>
> **考點**：SAA-1.3｜EBS encryption by default 是 Region 層級的預防性設定｜延伸閱讀：第 15 章、第 24 章

### 第 61 題｜SAA｜單選｜D2 遷移既有的 RabbitMQ 應用

一家連鎖餐飲集團的線上點餐系統在地端使用自行維護的 RabbitMQ，數十個服務以 AMQP 0-9-1 交換訊息，並大量使用 exchange 與 routing key 進行訊息路由。公司要把系統搬到 AWS，希望不修改應用程式中與訊息相關的程式碼，並且不再自行處理 broker 的修補與高可用。

哪個方案最合適？

- A. 部署 Amazon MQ for RabbitMQ 的 cluster deployment，應用程式改連 Amazon MQ 的 broker endpoint
- B. 把訊息機制改寫為 Amazon SNS topic 搭配 SQS queue，以 message filtering 取代 routing key
- C. 在跨兩個 AZ 的 EC2 Auto Scaling group 上自行部署 RabbitMQ 叢集
- D. 遷移到 Amazon MSK，以 Kafka topic 對應原本的 exchange

> [!answer]- 答案：A
> **A ✓** Amazon MQ 提供受管的 RabbitMQ broker，支援原生的 AMQP 0-9-1、exchange 與 routing key，應用程式只需修改連線位址與憑證。Cluster deployment 把節點分散在多個 AZ，修補與故障替換由 AWS 處理。
>
> **B ✗** SNS 加 SQS 是雲端原生、可大規模擴展的選擇，但必須改寫所有訊息相關程式碼，違反「不修改程式碼」。新開發的系統才適合直接採用。
>
> **C ✗** 自建叢集保留了相容性，但修補、升級與高可用都要自己負責，違反第二個需求。
>
> **D ✗** MSK 使用 Kafka 協定，與 AMQP 不相容，資料模型也不同，需要大幅改寫。
>
> **考點**：SAA-2.1｜Amazon MQ 讓既有 AMQP 應用不改程式遷移｜延伸閱讀：第 32 章

### 第 62 題｜SAA｜選兩項｜D3 提高影片快取命中率並降低 origin 負載

一家線上影音平台以 Amazon CloudFront 提供隨選影片，origin 是 us-east-1 的 S3 與一組產生播放清單的 EC2 服務。亞洲與歐洲使用者增加後，origin 的請求量持續上升。分析發現：許多請求因為 URL 帶有每個使用者都不同的 `session_id` query string 與追蹤用 cookie 而無法命中快取，但 origin 產生內容時並不使用這些值；此外，不同 edge location 對同一個影片片段的 cache miss，都各自直接打到 origin。

哪兩個做法最能降低 origin 負載並提升效能？

- A. 在 CloudFront 與 origin 之間加入 AWS Global Accelerator，加速 cache miss 時的回源連線
- B. 啟用 CloudFront Origin Shield，選擇最接近 origin 的 Region
- C. 為 origin 的 S3 bucket 啟用 S3 Transfer Acceleration
- D. 建立 cache policy，讓 cache key 不包含 `session_id` query string 與追蹤 cookie
- E. 把影片片段的 TTL 設為 0，確保每個使用者都取得最新內容

> [!answer]- 答案：B、D
> **A ✗** Global Accelerator 加速的是用戶端到 AWS 應用程式入口的連線，本身不提供快取；CloudFront 回源本來就走 AWS 骨幹網路，多加一層 accelerator 也不會減少回源的請求數。
>
> **B ✓** Origin Shield 是位於 origin 前的額外快取層，所有 regional edge cache 的 cache miss 先集中到 Origin Shield，同一個片段只需向 origin 取一次，大幅降低 origin 負載並提高整體命中率。
>
> **C ✗** Transfer Acceleration 用於從遠端加速「上傳到 S3」或直接存取 S3 的傳輸，CloudFront 回源本來就走 AWS 網路，不會因此減少請求。
>
> **D ✓** Cache key 包含的值越多，同一份內容被切成越多份快取。origin 不使用 `session_id` 與追蹤 cookie，把它們排除在 cache key 之外，所有使用者對同一片段的請求就能共用同一份快取。
>
> **E ✗** TTL 為 0 代表每次都要回 origin 確認，命中率只會更低；影片片段內容固定，應該設定較長的 TTL。
>
> **考點**：SAA-3.4｜Cache key 設計與 Origin Shield 提高命中率｜延伸閱讀：第 11 章

### 第 63 題｜SAA｜單選｜D4 開發測試環境的閒置成本

一家醫療資訊公司在開發與測試帳號中有 60 台 EBS-backed 的 EC2 instance，工程師只在週一到週五的 8:00 到 20:00 使用，其他時間完全閒置。這些 instance 上的資料與設定必須保留，隔天要能直接接續工作。公司希望以最少營運負擔大幅降低這些環境的運算費用。

哪個方案最合適？

- A. 為 60 台 instance 購買 1 年期的 Standard Reserved Instances
- B. 把所有 instance 改成 Spot instance，中斷時由工程師重新建立環境
- C. 使用 AWS Instance Scheduler（或 EventBridge Scheduler）依標籤在工作時段自動啟動、下班後自動停止 instance
- D. 把所有 instance 縮小成 t3.micro，降低每小時費用

> [!answer]- 答案：C
> **C ✓** Instance 停止後不再支付運算費用，只需支付 EBS 儲存，資料與設定都保留。每週實際使用 60 小時、閒置 108 小時，自動排程能省下約六成以上的運算費，而且依標籤排程不需要人工操作。
>
> **A ✗** RI 以 24 小時全年運作計價，每週有 108 小時的閒置時間仍要付費，節省幅度不如直接停機。
>
> **B ✗** Spot 隨時可能被中斷，工程師要重新建立環境，違反「隔天直接接續工作」，也增加人工負擔。
>
> **D ✗** 縮小規格可能讓開發工具與測試無法正常執行，而且仍在閒置時間持續付費。
>
> **考點**：SAA-4.2｜依時段自動停止非正式環境的 instance｜延伸閱讀：第 38 章、第 39 章

### 第 64 題｜SAA｜單選｜D1 限制組織只能使用特定 Region

一家歐洲汽車零件集團以 AWS Organizations 管理 40 個帳號（未使用 AWS Control Tower）。依資料落地要求，所有成員帳號只能在 eu-central-1 與 eu-west-1 建立資源，包括各帳號的管理員在內都不得繞過；但 IAM、Organizations、CloudFront 等全球服務仍必須能正常使用。

哪個方案最能以最少營運負擔強制執行這項規定？

- A. 在 organization root 掛載一個 SCP，以 `aws:RequestedRegion` 條件拒絕兩個 Region 以外的請求，並以 `NotAction` 排除全球服務
- B. 在每個帳號的每個 IAM user 與 role 上附加 IAM policy，拒絕兩個 Region 以外的動作
- C. 啟用 AWS Config，在每個帳號部署規則偵測其他 Region 的資源，並以 Lambda 自動刪除
- D. 在每個帳號為所有 IAM role 設定 permissions boundary，只允許兩個 Region 的動作

> [!answer]- 答案：A
> **A ✓** SCP 設定成員帳號中所有 principal（包括帳號管理員與 root user）可用權限的上限，掛在 root 後自動套用到所有成員帳號與之後新增的帳號，成員帳號內無法移除。`NotAction` 排除 IAM、Organizations、CloudFront 等全球服務，避免它們因為請求被送到 us-east-1 而被誤擋。SCP 不影響 management account，因此它不應用來執行工作負載。
>
> **B ✗** 帳號管理員可以自行修改或移除 IAM policy，無法防止「管理員繞過」，而且 40 個帳號中每個 principal 都要附加，新建的 role 也容易遺漏。
>
> **C ✗** Config 規則是事後偵測，資源已經在不允許的 Region 建立並可能存放了資料；自動刪除也可能造成誤刪。
>
> **D ✗** Permissions boundary 同樣由帳號內的管理員設定，管理員可以移除；每個 role 都要個別設定，營運負擔高。
>
> **考點**：SAA-1.1｜以 SCP 搭配 aws:RequestedRegion 建立組織層級的 Region 護欄｜延伸閱讀：第 14 章

### 第 65 題｜SAA｜單選｜D3 地端 NAS 搬遷到 S3 並持續同步

一家光學元件製造商的地端 NFS NAS 存放約 200 TB 的產品檢測影像，機房到 AWS 有一條 1 Gbps 的 Direct Connect。公司要在兩個月內把資料搬到 S3，搬遷期間產線仍會每天新增檔案，因此需要每天增量同步直到切換；同時要能限制白天使用的頻寬、驗證傳輸後資料的完整性，並以最少營運負擔完成。

哪個方案最合適？

- A. 申請多台 AWS Snowball Edge 裝置完成一次性搬遷，之後的新檔案由工程師手動上傳
- B. 在地端部署 AWS DataSync agent，建立從 NFS 到 S3 的 task，設定每日排程、頻寬限制與資料驗證
- C. 部署 Amazon S3 File Gateway，讓產線改把新檔案寫到 gateway，舊資料以 `cp` 指令複製到 gateway
- D. 在地端伺服器以 cron 每天執行 `aws s3 sync`，並以 shell 腳本比對檔案數量驗證結果

> [!answer]- 答案：B
> **B ✓** DataSync 是為線上資料搬遷設計的受管服務：agent 讀取 NFS 後以平行化的傳輸寫入 S3，task 可以排程執行並只傳送變更的檔案，支援頻寬限制與傳輸後的完整性驗證。200 TB 在 1 Gbps 下滿載約需 19 天，兩個月內足以完成初次搬遷加每日增量同步。
>
> **A ✗** Snowball 適合網路頻寬不足以在時限內搬完的情境，但這裡的頻寬已足夠；裝置的運送與處理也需要時間，之後的增量同步還要靠人工，營運負擔較高。
>
> **C ✗** File Gateway 適合「地端應用持續以檔案協定存取 S3」的長期混合架構，用來搬遷 200 TB 的既有資料不但要改變產線的寫入位置，大量複製也受限於 gateway 的快取與吞吐量。
>
> **D ✗** `aws s3 sync` 可以運作，但頻寬控制、錯誤重試、完整性驗證與監控都要自己撰寫與維護腳本，營運負擔高於 DataSync。
>
> **考點**：SAA-3.5｜DataSync 的排程增量同步、頻寬限制與資料驗證｜延伸閱讀：第 25 章

## 答案速查與 Domain 分析

| 題號 | 答案 | Domain | Task | 相關章節 |
|---|---|---|---|---|
| 1 | C | D1 | SAA-1.1 | 第 12 章 |
| 2 | B | D3 | SAA-3.2 | 第 19 章 |
| 3 | D | D2 | SAA-2.2 | 第 18 章、第 26 章 |
| 4 | A | D4 | SAA-4.1 | 第 23 章 |
| 5 | C | D1 | SAA-1.2 | 第 16 章 |
| 6 | B | D3 | SAA-3.3 | 第 26 章 |
| 7 | D | D1 | SAA-1.3 | 第 15 章 |
| 8 | A、D | D2 | SAA-2.1 | 第 32 章 |
| 9 | A | D4 | SAA-4.2 | 第 39 章 |
| 10 | B | D1 | SAA-1.1 | 第 22 章 |
| 11 | D | D3 | SAA-3.1 | 第 24 章 |
| 12 | A | D2 | SAA-2.2 | 第 34 章 |
| 13 | B、E | D1 | SAA-1.2 | 第 6 章、第 38 章 |
| 14 | C | D3 | SAA-3.4 | 第 11 章 |
| 15 | C | D2 | SAA-2.1 | 第 33 章 |
| 16 | D | D4 | SAA-4.4 | 第 6 章、第 39 章 |
| 17 | A | D1 | SAA-1.1 | 第 13 章 |
| 18 | B | D3 | SAA-3.5 | 第 31 章 |
| 19 | C、E | D2 | SAA-2.2 | 第 24 章、第 26 章 |
| 20 | C | D1 | SAA-1.3 | 第 16 章 |
| 21 | B | D4 | SAA-4.3 | 第 27 章 |
| 22 | D | D3 | SAA-3.2 | 第 17 章 |
| 23 | A | D1 | SAA-1.2 | 第 11 章 |
| 24 | B、D | D2 | SAA-2.1 | 第 32 章、第 35 章 |
| 25 | C | D3 | SAA-3.3 | 第 24 章、第 26 章 |
| 26 | C | D4 | SAA-4.2 | 第 17 章、第 39 章 |
| 27 | D | D1 | SAA-1.1 | 第 13 章 |
| 28 | A | D3 | SAA-3.4 | 第 10 章 |
| 29 | A、C | D2 | SAA-2.2 | 第 34 章 |
| 30 | B | D1 | SAA-1.2 | 第 16 章 |
| 31 | D | D2 | SAA-2.1 | 第 21 章 |
| 32 | D | D2 | SAA-2.2 | 第 24 章 |
| 33 | C | D4 | SAA-4.1 | 第 24 章 |
| 34 | A、E | D1 | SAA-1.3 | 第 10 章、第 15 章 |
| 35 | B | D2 | SAA-2.1 | 第 21 章 |
| 36 | D | D2 | SAA-2.2 | 第 19 章 |
| 37 | B | D1 | SAA-1.1 | 第 12 章、第 13 章 |
| 38 | A | D3 | SAA-3.2 | 第 19 章 |
| 39 | D | D4 | SAA-4.3 | 第 39 章 |
| 40 | B、C | D2 | SAA-2.1 | 第 32 章 |
| 41 | C | D1 | SAA-1.2 | 第 6 章 |
| 42 | B | D3 | SAA-3.3 | 第 29 章 |
| 43 | A | D4 | SAA-4.4 | 第 8 章、第 39 章 |
| 44 | A | D1 | SAA-1.3 | 第 15 章 |
| 45 | B、E | D2 | SAA-2.2 | 第 9 章、第 27 章 |
| 46 | D | D3 | SAA-3.4 | 第 7 章 |
| 47 | C | D1 | SAA-1.2 | 第 17 章 |
| 48 | C | D3 | SAA-3.5 | 第 31 章 |
| 49 | B | D4 | SAA-4.2 | 第 19 章、第 20 章 |
| 50 | D | D1 | SAA-1.2 | 第 16 章 |
| 51 | A、D | D2 | SAA-2.1 | 第 32 章 |
| 52 | A | D3 | SAA-3.1 | 第 24 章 |
| 53 | D | D4 | SAA-4.1 | 第 23 章 |
| 54 | B | D1 | SAA-1.1 | 第 13 章 |
| 55 | C | D2 | SAA-2.2 | 第 18 章 |
| 56 | A | D2 | SAA-2.2 | 第 18 章、第 34 章 |
| 57 | C、E | D1 | SAA-1.2 | 第 11 章、第 16 章 |
| 58 | D | D4 | SAA-4.3 | 第 28 章 |
| 59 | B | D4 | SAA-4.3 | 第 27 章 |
| 60 | C | D1 | SAA-1.3 | 第 15 章、第 24 章 |
| 61 | A | D2 | SAA-2.1 | 第 32 章 |
| 62 | B、D | D3 | SAA-3.4 | 第 11 章 |
| 63 | C | D4 | SAA-4.2 | 第 38 章、第 39 章 |
| 64 | A | D1 | SAA-1.1 | 第 14 章 |
| 65 | B | D3 | SAA-3.5 | 第 25 章 |

### 各 Domain 題數與得分計算

| Domain | 正式考試比重 | 本回題數 | 題號 |
|---|---|---|---|
| D1 Design Secure Architectures | 30% | 20 | 1、5、7、10、13、17、20、23、27、30、34、37、41、44、47、50、54、57、60、64 |
| D2 Design Resilient Architectures | 26% | 17 | 3、8、12、15、19、24、29、31、32、35、36、40、45、51、55、56、61 |
| D3 Design High-Performing Architectures | 24% | 15 | 2、6、11、14、18、22、25、28、38、42、46、48、52、62、65 |
| D4 Design Cost-Optimized Architectures | 20% | 13 | 4、9、16、21、26、33、39、43、49、53、58、59、63 |

對完答案後，分別計算每個 domain 的答對率。正式成績單也會依 domain 顯示表現，任何一個 domain 答對率低於 65%，就代表它是你目前最大的失分來源，應優先處理，而不是平均地重讀全書。

### 錯題對應複習章節

- **D1 錯題集中在 1.1（身份與存取）**：重讀第 12 章的 policy 評估邏輯與第 13 章的跨帳號 role、Identity Center、IAM Roles Anywhere，再看第 14 章 SCP 的作用範圍。常見失分點是分不清「誰授權」（identity policy、resource policy、SCP 各自的角色）。
- **D1 錯題集中在 1.2、1.3（工作負載安全與資料保護）**：第 6 章（security group 引用、VPC endpoint）、第 15 章（KMS key policy、條件鍵、預設加密）、第 16 章（WAF、Shield、Inspector、Macie 的分工）。把每個安全服務「偵測什麼、能不能阻擋」整理成一張表。
- **D2 錯題集中在 2.1（鬆耦合）**：第 32 章的 SNS／SQS／EventBridge 選型與 FIFO 語意、第 33 章 Step Functions 的 workflow 類型，以及第 21 章的 ECS 服務探索。
- **D2 錯題集中在 2.2（高可用與 DR）**：第 34 章的四種 DR 策略與 RTO／RPO 對照、第 18 章的 health check 與 static stability、第 26 章的 Multi-AZ 與 Global Database。
- **D3 錯題**：儲存效能看第 24 章（EBS IOPS、EFS throughput mode、FSx for Lustre）；運算看第 17 章與第 19 章；資料庫看第 26、29 章；網路看第 7、10、11 章；資料擷取看第 25、31 章。
- **D4 錯題**：第 39 章的購買方式（Savings Plans、RI、Spot）是核心，再搭配第 23 章的 S3 儲存類別、第 27 章的 DynamoDB 計費模式與 table class、第 6 章的 endpoint 與 NAT 費用。
- **多選題答錯**：通常是只選對一半。重看該題的解析，確認兩個正確選項分別解決了題目中的哪一個限制；SAA 的多選題常是「一個步驟解決 A 需求、另一個步驟解決 B 需求」。
