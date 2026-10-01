---
title: "Storage 與 Data Architecture"
part: 4
as_of: 2026-10-01
---

# Part 4　Storage 與 Data Architecture

# 第 41 章　S3 Object Model、Consistency 與 Security

Object storage提供近乎無限namespace，但bucket、object、prefix與HTTP API不同於檔案系統。

## 跟著一筆資料走：先從故事開始

把鏡頭拉到一個真實的production現場：資料平台每天寫入十億個事件物件，僅分析角色可讀，外部客戶以限時連結下載。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：Object storage提供近乎無限namespace，但bucket、object、prefix與HTTP API不同於檔案系統。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：S3比較像大型包裹倉庫：每件物品用完整key存取，而不是在遠端磁碟上任意改其中幾個bytes。 倉庫類比不能取代一致性、multipart upload、versioning與policy細節；它只用來先分清object和file。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon S3是這一章的入口，S3 Block Public Access用來畫出邊界；主要方向「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：資料平台每天寫入十億個事件物件，僅分析角色可讀，外部客戶以限時連結下載。

Application以bucket + key操作object
      │
      ├─ PUT完整object ──> S3持久保存與versioning
      ├─ GET完整object ──> IAM / bucket policy先授權
      └─ LIST prefix ────> bucket-level permission

S3沒有一般POSIX檔案系統的append、directory rename或file locking。

公開下載通常走：
Viewer ── CloudFront / presigned URL ──> private S3 object
而不是直接把整個bucket設為public。

失敗時先找：開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snap…
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon S3有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3和S3 Block Public Access並不是兩個任意的產品名稱。前者適合本章，是因為「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」直接回應了眼前的問題；後者描述的「EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「object storage scales by immutable objects and explicit metadata」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |
| S3 Block Public Access | 在account、bucket或access point層阻止policy/ACL造成public access。 | 四個flags在授權前套用最嚴格組合，可拒絕public ACL/policy或忽略既有public ACL。 |
| S3 bucket policies | 在bucket資源側指定誰可對bucket/objects執行哪些S3 actions及條件。 | Policy statement匹配Principal、Action、Resource與Condition；explicit Deny可強制TLS、KMS或organization boundary。 |

## 把全圖套進一個具體案例

**場景：** 資料平台每天寫入十億個事件物件，僅分析角色可讀，外部客戶以限時連結下載。

1. 故事的起點：資料平台每天寫入十億個事件物件，僅分析角色可讀，外部客戶以限時連結下載。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3負責「以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：S3 Block Public Access、S3 bucket policies各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### S3不是網路磁碟

S3以bucket + key識別object，透過HTTP API整個PUT/GET；prefix只是key字串的共同前綴。它沒有一般POSIX filesystem的append、rename directory與跨object transaction。若應用依賴file locking、in-place update或共享mount，應比較EFS、FSx或EBS，而不是勉強把S3當磁碟。

### IAM policy與bucket policy何時選誰

IAM identity policy附在user/group/role，適合描述「這個role可操作哪些AWS資源」，可跨多個服務集中管理。Bucket policy附在bucket，適合描述「誰可以碰這個bucket」、cross-account、CloudFront/AWS service delivery，以及用explicit Deny強制TLS、organization、VPC endpoint或encryption。同帳號簡單存取可能只需其中一個Allow；cross-account通常來源identity與目標resource兩側都要允許。

### ARN最常寫錯的地方

Bucket-level action如s3:ListBucket使用arn:aws:s3:::my-bucket；object-level action如s3:GetObject使用arn:aws:s3:::my-bucket/prefix/*。把ListBucket綁到/*，或GetObject只綁bucket ARN，都不會match。Condition的s3:prefix限制LIST看到的key範圍，不能取代object ARN的實際讀取限制。

### 四層public防線

Modern S3先保持Object Ownership為Bucket owner enforced以停用ACL，再在account與bucket開啟四個Block Public Access flags，bucket policy只允許具名principal，最後用IAM Access Analyzer/Config持續找外部或public access。公開靜態網站通常用private bucket + CloudFront OAC，而非讓bucket public。

## 需要時再查：四個閱讀支點

### Amazon S3

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Object storage提供近乎無限namespace，但bucket、object、prefix與HTTP API不同於檔案系統。
- **具體例子／邊界：** 在「資料平台每天寫入十億個事件物件，僅分析角色可讀，外部客戶以限時連結下載。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### S3 Block Public Access

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：object storage scales by immutable objects and explicit metadata。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

### S3 Block Public Access

- **功用：** 在account、bucket或access point層阻止policy/ACL造成public access。
- **底層機制：** 四個flags在授權前套用最嚴格組合，可拒絕public ACL/policy或忽略既有public ACL。
- **關鍵設定：** BlockPublicAcls、IgnorePublicAcls、BlockPublicPolicy、RestrictPublicBuckets。
- **選擇時機：** 除非有明確public S3 use case，應在account與bucket層保持全部開啟。
- **替換時機：** 公開網站通常改用private S3 + CloudFront OAC，而不是關閉整體保護。

### S3 bucket policies

- **功用：** 在bucket資源側指定誰可對bucket/objects執行哪些S3 actions及條件。
- **底層機制：** Policy statement匹配Principal、Action、Resource與Condition；explicit Deny可強制TLS、KMS或organization boundary。
- **關鍵設定：** Principal、s3:ListBucket bucket ARN、object actions的/* ARN、aws:SecureTransport、aws:PrincipalOrgID與aws:SourceVpce。
- **選擇時機：** cross-account、CloudFront/service delivery、集中強制安全條件或整個bucket規則。
- **替換時機：** 只管理一個role在多項AWS服務的權限時用IAM identity policy；大量team入口可用Access Points。

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

### S3 Block Public Access：逐項設定說明

#### `BlockPublicAcls`

- **控制什麼：** `BlockPublicAcls`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「除非有明確public S3 use case，應在account與bucket層保持全部開啟。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Block Public Access中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `IgnorePublicAcls`

- **控制什麼：** `IgnorePublicAcls`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「除非有明確public S3 use case，應在account與bucket層保持全部開啟。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Block Public Access中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `BlockPublicPolicy`

- **控制什麼：** `BlockPublicPolicy`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「除非有明確public S3 use case，應在account與bucket層保持全部開啟。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Block Public Access中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `RestrictPublicBuckets`

- **控制什麼：** `RestrictPublicBuckets`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「除非有明確public S3 use case，應在account與bucket層保持全部開啟。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Block Public Access中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

### S3 bucket policies：逐項設定說明

#### `Principal`

- **控制什麼：** `Principal`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、CloudFront/service delivery、集中強制安全條件或整個bucket規則。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 bucket policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `s3:ListBucket bucket ARN`

- **控制什麼：** `s3:ListBucket bucket ARN`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

#### `object actions的/* ARN`

- **控制什麼：** `object actions的/* ARN`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

#### `aws:SecureTransport`

- **控制什麼：** `aws:SecureTransport`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「cross-account、CloudFront/service delivery、集中強制安全條件或整個bucket規則。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 bucket policies的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `aws:PrincipalOrgID`

- **控制什麼：** `aws:PrincipalOrgID`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、CloudFront/service delivery、集中強制安全條件或整個bucket規則。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 bucket policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `aws:SourceVpce`

- **控制什麼：** `aws:SourceVpce`指定S3 bucket policies讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

## 可以直接對照 AWS 的設定範例

### Bucket policy：TLS、prefix 與 cross-account role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::acme-data",
        "arn:aws:s3:::acme-data/*"
      ],
      "Condition": {"Bool": {"aws:SecureTransport": "false"}}
    },
    {
      "Sid": "AllowAnalyticsRoleToListRawPrefix",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::444455556666:role/AnalyticsReader"
      },
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-data",
      "Condition": {"StringLike": {"s3:prefix": ["raw/*"]}}
    },
    {
      "Sid": "AllowAnalyticsRoleToReadRawObjects",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::444455556666:role/AnalyticsReader"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::acme-data/raw/*"
    }
  ]
}
```

1. 第一段是explicit Deny，因此即使其他identity policy允許，也不能用HTTP明文存取。
2. ListBucket操作bucket本身，Resource沒有/*；s3:prefix只限制LIST結果。
3. GetObject操作objects，Resource必須是raw/*；cross-account role在來源帳號通常也要有identity Allow。
4. Principal只出現在resource policy；若這段改成附在AnalyticsReader的IAM policy，就移除Principal。

### Bucket安全基線：停用ACL、封鎖public、SSE-KMS

```yaml
Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: acme-data
      OwnershipControls:
        Rules:
          - ObjectOwnership: BucketOwnerEnforced
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        IgnorePublicAcls: true
        BlockPublicPolicy: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - BucketKeyEnabled: true
            ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !GetAtt DataKey.Arn
      VersioningConfiguration:
        Status: Enabled

```

1. BucketOwnerEnforced停用ACL並讓bucket owner擁有所有objects，是modern default。
2. 四個public access flags處理的風險不同，考試常用「Block all public access」概括。
3. BucketKeyEnabled可減少SSE-KMS對KMS requests與成本；KMS key policy仍要允許S3與讀寫roles。
4. Versioning保留舊version但不是完整backup；刪除、replication與retention仍需額外設計。

### 同一需求若改用 IAM identity policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-data",
      "Condition": {"StringLike": {"s3:prefix": ["raw/*"]}}
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::acme-data/raw/*"
    }
  ]
}
```

1. 這份policy附到role，因此沒有Principal欄位。
2. 若role與bucket同帳號且bucket沒有explicit Deny，這個identity Allow通常可完成授權。
3. 若bucket在另一帳號，target bucket policy仍需允許該role；這就是cross-account兩側授權。

## 讀到這裡，請用自己的話說一次

1. Amazon S3的責任：以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
2. 底層機制：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
3. 第一個要看的設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
4. 選擇邏輯：以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。
5. 不要混淆：S3 Block Public Access的責任是「在account、bucket或access point層阻止policy/ACL造成public access。」；它不會自動取代Amazon S3。
6. 替換訊號：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
7. 最常見錯法：開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。
8. 可移植原則：object storage scales by immutable objects and explicit metadata。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| S3 Block Public Access | 在account、bucket或access point層阻止policy/ACL造成public access。 | 四個flags在授權前套用最嚴格組合，可拒絕public ACL/policy或忽略既有public ACL。 | 除非有明確public S3 use case，應在account與bucket層保持全部開啟。 | 公開網站通常改用private S3 + CloudFront OAC，而不是關閉整體保護。 |
| S3 bucket policies | 在bucket資源側指定誰可對bucket/objects執行哪些S3 actions及條件。 | Policy statement匹配Principal、Action、Resource與Condition；explicit Deny可強制TLS、KMS或organization boundary。 | cross-account、CloudFront/service delivery、集中強制安全條件或整個bucket規則。 | 只管理一個role在多項AWS服務的權限時用IAM identity policy；大量team入口可用Access Points。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。 | 只有當題目條件明確改變時才可能合理。 | 開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。」之間做選擇。
- 認得常考設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
- 對應官方tasks：SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜Object API 與 POSIX 語意

一套建置系統讓多台 Linux worker 共同開啟同一個 SQLite catalog。Worker 會以 memory mapping 讀取檔案，並對既有資料頁做 random in-place writes。團隊想把 catalog file 直接放進 S3，以免管理共享儲存。哪個評估最正確？

A. 不能直接等價替換；S3 的存取單位是完整 object，不提供共享檔案的 mmap 與任意 offset 原地寫入語意，應改用 EFS、合適的 FSx，或重新設計資料層
B. 可以直接替換；S3 strong consistency 代表 object 能被作業系統當成可共享 memory-mapped file
C. 可以直接替換；multipart upload 的 part number 等同檔案 byte offset，可在不建立新 object version 的情況下修改任意資料頁
D. 可以直接替換；啟用 S3 Versioning 後，SQLite 的 page cache、journaling 與 file descriptor 語意會由 S3 自動模擬

**答案：A**

- **A：** 正確。這個 workload 依賴可尋址的檔案位元組、共享 page cache 與檔案系統 I/O contract；S3 適合以 key 取得或取代完整 object，不能直接滿足 mmap 或 random in-place update。
- **B：** 不正確。Strong consistency描述成功寫入後 GET、LIST 等 S3 API 所看到的版本，不會把 object 變成具有 file descriptor 與 virtual-memory mapping 的 POSIX file。
- **C：** 不正確。Multipart upload 是分段組成一個新 object 的上傳機制；完成前各 part 不是既有 object 可被資料庫原地修改的資料頁。
- **D：** 不正確。Versioning保留 object 的多個版本，並不實作 SQLite 所需的 page locking、journal/WAL、mmap 或作業系統快取一致性。

**事實查證：** [What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)

### 練習題 2｜SAA → SAP｜Strong consistency 的邊界

資料管線先寫入 `part-001` 與 `part-002`，最後讓讀者看到一個代表整批完成的資料集。需求是每個成功 PUT 後立即 GET/LIST 都看得到新值，而且讀者不能只看到其中一個 part。應採用哪個設計？

A. 在每次 PUT 後固定等待 30 秒，因為 S3 overwrite 與 LIST 仍是 eventual consistency
B. 利用 S3 單一 object 的 strong consistency，完成所有 parts 後再原子更新一個 manifest/versioned pointer，讀者只依該 pointer 取批次
C. 直接同時 PUT 兩個 keys；S3 會自動把它們包成一個跨 object ACID transaction
D. 關閉 versioning，因為 versioning 會讓 LIST 永遠看見舊資料

**答案：B**

- **A：** 不正確。現行 S3 對成功 PUT/DELETE 後的 GET 與 LIST 提供 strong consistency，不需要任意等待。
- **B：** 正確。Strong consistency解決單一 object 的可見性；manifest 或版本指標另外建立批次發布協定，避免跨 keys 半完成。
- **C：** 不正確。兩個 object 的寫入不是一個共同原子提交；其中一個成功、另一個失敗仍可能發生。
- **D：** 不正確。Versioning 保存版本但不把 LIST 改回 eventual；是否開啟應由恢復與治理需求決定。

**事實查證：** [What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel)

### 練習題 3｜SAA → SAP｜Cross-account S3 resource scope

Account B 的供應商應用要讀取 Account A 中以 customer managed KMS key 加密的 S3 objects。架構師正在比較「直接授權 B 的既有 role」與「讓 B assume Account A 的專用 role」兩種模式。哪個敘述正確？

A. 直接授權只需要 Account B 的 identity policy；Account A 的 bucket policy與KMS key policy都不參與跨帳號判定
B. AssumeRole 模式只要供應商知道 Account A role ARN 即可；role trust policy與呼叫端的 `sts:AssumeRole` 權限都不是必要條件
C. 兩種模式都可行：直接授權需讓 S3 resource policy與跨帳號 KMS authorization共同允許 B 的 role；AssumeRole模式則由 A 的 trust policy建立信任，並把最小 S3/KMS權限授予被assume的A帳號role
D. S3 bucket policy中的 `kms:Decrypt` Allow會自動修改KMS key policy，因此不必另外建立KMS授權

**答案：C**

- **A：** 不正確。跨帳號直接存取需要來源帳號的identity permission與資源擁有者一側的resource permission都成立；SSE-KMS還要另外通過KMS的跨帳號授權。
- **B：** 不正確。AssumeRole要求A帳號role的trust policy信任B的principal，B端principal也必須獲准呼叫`sts:AssumeRole`；知道ARN不構成授權。
- **C：** 正確。直接授權與AssumeRole是兩種不同信任邊界。前者保留B role身份，需同時完成S3與KMS跨帳號授權；後者取得A role的temporary credentials，再由該role的最小權限存取S3與KMS。
- **D：** 不正確。S3 bucket policy只能管S3 resource；customer managed KMS key的使用權必須由KMS key policy、grant，以及適用的identity policy建立，不能由bucket policy代寫。

**事實查證：** [Examples of Amazon S3 bucket policies - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html)、[IAM tutorial: Delegate access across AWS accounts using IAM roles - AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)、[Allowing users in other accounts to use a KMS key - AWS Key Management Service](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)

### 練習題 4｜SAA｜Object Ownership 與 Block Public Access

中央資料帳號接收 30 個 workload 帳號上傳 objects。平台要求 bucket owner一致擁有所有新 objects、禁止 ACL 漂移，且 cross-account 上傳仍需可行。最符合需求的是？

A. 保留 ACL，要求每個 uploader 永久設定 `public-read`
B. 關閉四項 Block Public Access，否則任何 cross-account principal 都無法存取
C. 依賴難猜的 bucket 名稱，不再配置 policy
D. 啟用 Bucket owner enforced 停用 ACL，維持 Block Public Access，並以 IAM 與 bucket/access point policy授權具名 principals

**答案：D**

- **A：** 不正確。Public ACL擴大暴露面，也無法達成集中 policy治理；legacy整合才可能暫時保留 ACL。
- **B：** 不正確。Block Public Access針對 public access，不會阻止寫給具名 cross-account principal 的非公開政策。
- **C：** 不正確。名稱不是安全控制；未授權 request仍須由 IAM/resource policy明確拒絕。
- **D：** 正確。Bucket owner enforced統一 ownership並停用 ACL；具名跨帳號存取與防公開控制可以同時存在。

**事實查證：** [Controlling ownership of objects and disabling ACLs for your bucket - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html)、[Blocking public access to your Amazon S3 storage - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)

### 練習題 5｜SAA → SAP｜SSE-KMS 雙重授權與 Bucket Key

合規 bucket 必須使用 customer managed KMS key。Bucket policy已允許某 role讀取 objects，但該 role仍收到 KMS AccessDenied；同時每月 KMS request費用很高。哪個方案同時處理兩個問題？

A. 在 IAM/key policy中授予所需 `kms:Decrypt`，並評估啟用 S3 Bucket Key降低對 KMS 的 request 次數
B. 把 SSE-KMS改名為 SSE-S3，但繼續使用原 customer managed key policy
C. 只要求 TLS；傳輸加密會自動讓 KMS授權成功
D. 增加 `s3:GetObject` 到 bucket ARN，不需 object ARN與 KMS permission

**答案：A**

- **A：** 正確。Caller必須同時通過 S3與 KMS authorization；S3 Bucket Key可降低部分 SSE-KMS request traffic，但不取代 key policy。
- **B：** 不正確。SSE-S3使用 S3 managed keys，無法套用原 customer managed KMS key policy；只有不需 key-level控制時才可能選它。
- **C：** 不正確。TLS保護傳輸，不授予 KMS Decrypt，也不能取代 at-rest encryption。
- **D：** 不正確。GetObject需 object ARN；即使 S3允許，SSE-KMS object仍可能被 KMS explicit deny阻擋。

**事實查證：** [Using server-side encryption with AWS KMS keys (SSE-KMS) - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html)

### 練習題 6｜SAP｜S3 Replication 先決條件

既有 bucket中有兩年 SSE-KMS合規 objects。公司現在要把它們複寫到另一帳號與 Region。架構師建立 CRR rule後發現舊 objects沒有出現在目的地。最完整的修正是？

A. 等待即可；CRR是同步 commit且會自動回填所有歷史 objects
B. 兩端開啟 versioning、設定 replication role與目的權限、明確包含 SSE-KMS並授權兩端 keys，再用 S3 Batch Replication處理既有 objects
C. 關閉 source versioning，讓 replication rule能覆寫目的 objects
D. 只把目的 KMS key ARN寫入 lifecycle rule；lifecycle會代替 replication

**答案：B**

- **A：** 不正確。一般 replication rule主要處理規則生效後符合條件的 objects，且複寫是非同步，不是零 RPO同步提交。
- **B：** 正確。Versioning、IAM/resource permissions與 KMS授權都是必要邊界；歷史資料需 Batch Replication等回填流程。
- **C：** 不正確。標準 S3 replication要求 source與 destination versioning；關閉會破壞先決條件。
- **D：** 不正確。Lifecycle控制轉層/到期，不會建立跨帳號跨 Region replica。

**事實查證：** [Replicating objects within and across Regions - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)

### 練習題 7｜SAA｜Versioning、delete marker 與 lifecycle

某使用者對 versioned bucket中的 `report.csv`執行一般 DELETE。應用隨後 GET得到 404，但稽核要求立刻恢復上一版，並在一年後清理舊版本。應怎麼做？

A. 從另一 Region自動找 replica；versioning本身必定跨 Region備份
B. 等待 lifecycle expiration反向建立被刪 object
C. 找出並移除目前 delete marker或複製指定舊 version為新版本，另以 noncurrent version lifecycle控制一年後成本
D. 刪除整個 bucket再從 versioning journal原地復原

**答案：C**

- **A：** 不正確。Versioning在同 bucket保存版本；跨 Region copy需另設 replication或 backup。
- **B：** 不正確。Lifecycle expiration是刪除/轉層機制，不會自動復原內容。
- **C：** 正確。一般 DELETE建立 delete marker；移除 marker或發布舊版本即可恢復目前可見值，noncurrent版本需獨立 lifecycle規則。
- **D：** 不正確。刪除 bucket不是恢復步驟，且 bucket必須先清空所有 versions與 markers才可刪除。

**事實查證：** [Retaining multiple versions of objects with S3 Versioning - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)

### 練習題 8｜SAA｜Presigned URL 權限與有效期

客服系統要讓沒有 AWS 身份的客戶下載單一私有 object 15 分鐘。選擇兩項正確敘述。

A. 由具備該 object讀取權限的 principal產生 presigned URL，URL能做的事不超過簽署者
B. 先把整個 bucket設成 public-read，presigned URL才會生效
C. Presigned URL可繞過 bucket policy或 SCP中的 explicit Deny
D. 簽署 credentials被撤銷或提早到期後，URL仍保證使用完整15分鐘
E. URL的實際可用期同時受指定 expiration與簽署 credentials有效期限制

**答案：A、E**

- **A：** 正確。Presigned URL代表簽署者對特定 operation的暫時授權，不能擴大簽署者本來沒有的權限。
- **B：** 不正確。典型用途正是分享 private object；無需讓 bucket公開。
- **C：** 不正確。Explicit Deny仍優先；presigning不是繞過組織或資源政策的後門。
- **D：** 不正確。Temporary credentials到期或被撤銷時，URL可能早於 query-string expiration失效。
- **E：** 正確。有效期由 URL設定與簽署 credentials剩餘期限共同限制。

**事實查證：** [Sharing objects with presigned URLs - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)

### 練習題 9｜SAA｜大型 object 上傳與 integrity

海外站點要透過不穩定網路上傳 200 GB檔案。要求能平行傳輸、只重送失敗區段並驗證內容，且不可讓放棄的 uploads永久計費。應選哪兩項？

A. 以單一 PUT傳輸；S3會在失敗後只重送壞掉的 byte ranges
B. 使用 multipart upload並行上傳 parts，完成前可單獨重試失敗 part
C. 為 upload設定 supported checksum並在完成流程驗證內容完整性
D. 把 ETag一律視為完整 object MD5，不論 multipart或 encryption方式
E. 建立 lifecycle只刪除已完成 objects，不處理 incomplete multipart uploads

**答案：B、C**

- **A：** 不正確。大型單次 PUT失敗通常需重傳整個 request，也不提供 audit所需的 part管理。
- **B：** 正確。Multipart upload支援並行與 per-part retry，正好隔離不穩定網路造成的局部失敗。
- **C：** 正確。S3支援多種 checksum演算法，應明確使用而不是依賴不一定等於 MD5的 ETag。
- **D：** 不正確。Multipart與部分 encryption情境的 ETag不等於完整 object MD5。
- **E：** 不正確。應使用 AbortIncompleteMultipartUpload lifecycle action清理未完成 parts；已完成 object是另一種 lifecycle範圍。

**事實查證：** [Uploading and copying objects using multipart upload in Amazon S3 - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)

### 練習題 10｜SAP｜Object Lock 與跨 Region recovery

證券公司要求 records在七年 retention內連一般 bucket管理者都不能刪除，且 primary Region失效時仍可在另一 Region恢復。哪兩項設計缺一不可？

A. 只啟用 MFA Delete；它與不可縮短的合規 retention完全相同
B. 建立 lifecycle expiration，讓管理者在稽核時手動延後刪除
C. 在versioned bucket對records套用七年的S3 Object Lock Compliance-mode retention，設定不可縮短的retain-until date
D. 依賴 Object Lock自動把每個 version同步到另一 Region
E. 另建受保護的 replication/backup與恢復演練，因不可變性不等於跨 Region副本

**答案：C、E**

- **A：** 不正確。MFA Delete提高 version刪除門檻，但不是 Object Lock Compliance retention contract。
- **B：** 不正確。普通 lifecycle不能凌駕有效的 Compliance retention，且人工延後不構成不可變控制。
- **C：** 正確。Compliance mode在retain-until date前，即使root user也不能刪除受保護version或縮短retention。Governance mode可由具特殊bypass權限者略過；legal hold沒有固定到期日，且可由具`PutObjectLegalHold`權限者移除，所以不能取代本題的固定七年Compliance retention。
- **D：** 不正確。Object Lock保護版本不被改刪，本身不會建立跨 Region replica。
- **E：** 正確。Region recovery是另一個故障域，需透過 replication/backup及實際 restore測試證明 RPO/RTO。

**事實查證：** [Locking objects with Object Lock - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)、[Replicating objects within and across Regions - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以bucket policy、IAM、Block Public Access與encryption建立邊界…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Object storage提供近乎無限namespace，但bucket、object、prefix與HTTP API不同於檔案系統。」，所以「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」能直接滿足它；若constraint改成「EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」。替代方案「EFS提供共享POSIX語意；若應用依賴append、locking或directory rename，不應只因容量選S3。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Object storage提供近乎無限namespace，但bucket、object、prefix與HTTP API不同於檔案系統。」，排除會導致「開放public bucket、忽略cross-account ownership，或把一次LIST結果當transaction snapshot。」的選項，再選「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以bucket policy、IAM、Block Public Access與encryption建立邊界，依key設計平行存取。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「object storage scales by immutable objects and explicit metadata」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 42 章　S3 Storage Classes、Lifecycle 與 Archival

同一份資料的存取頻率會隨時間改變，儲存單價之外還有retrieval、minimum duration與request成本。

## 跟著一筆資料走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：合規log前30天常查，之後六年幾乎不讀，但法律要求數小時內可取回。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：同一份資料的存取頻率會隨時間改變，儲存單價之外還有retrieval、minimum duration與request成本。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：S3比較像大型包裹倉庫：每件物品用完整key存取，而不是在遠端磁碟上任意改其中幾個bytes。 這只是起點，因為倉庫類比不能取代一致性、multipart upload、versioning與policy細節；它只用來先分清object和file。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon S3承接主要責任，以S3 Lifecycle檢查替代條件，並用「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：合規log前30天常查，之後六年幾乎不讀，但法律要求數小時內可取回。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon S3：authoritative或主要資料路徑]
          │ 以HTTP API保存object，提供高durability、彈性namespace與多種storage cla…
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · S3 Lifecycle：依object age、prefix/tag與version狀態自動transition或expire資料。
  · S3 Glacier：提供S3內低成本archive storage classes，以較高取回延遲換成本。

失敗時先找：把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon S3有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3和S3 Lifecycle並不是兩個任意的產品名稱。前者適合本章，是因為「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」直接回應了眼前的問題；後者描述的「Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「optimize lifecycle using total access cost, not storage price」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |
| S3 Lifecycle | 依object age、prefix/tag與version狀態自動transition或expire資料。 | S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。 |
| S3 Glacier | 提供S3內低成本archive storage classes，以較高取回延遲換成本。 | Objects仍由S3 API管理；Flexible Retrieval/Deep Archive需先restore臨時副本。 |

## 把全圖套進一個具體案例

**場景：** 合規log前30天常查，之後六年幾乎不讀，但法律要求數小時內可取回。

1. 故事的起點：合規log前30天常查，之後六年幾乎不讀，但法律要求數小時內可取回。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3負責「以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：S3 Lifecycle、S3 Glacier各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### S3 Express One Zone：它仍是 object storage，但把 latency 與 failure domain 換到同一個 AZ

S3 Standard 的一般用途 bucket 跨多個 AZ 保存資料；S3 Express One Zone 使用 directory bucket，讓 application 可把 compute 與 object storage 放在同一 AZ，換取一致的 single-digit millisecond access。它不是 EBS，也不會突然具備 POSIX rename/locking。

```text
compute in AZ-a ─ zonal endpoint ─ directory bucket (AZ-a)
        │                     ├─ S3 Express One Zone only
        │                     ├─ session-based object access
        │                     └─ single-AZ failure boundary
        └─ durable source / replica may still live in general-purpose S3
```

#### 選它之前要寫下的資料生命週期

```YAML
dataset:
  authoritative_copy: s3-standard://durable-source
  hot_working_set: s3express://directory-bucket--azid--x-s3
  compute_az: apne1-az4
  rebuild_strategy: repopulate-from-authoritative-copy
  encryption: SSE-KMS
  access: CreateSession through supported SDK
```

1. Directory bucket 的 object operations 走 zonal endpoint；client/SDK 會使用 CreateSession 的短期 session credentials。
2. 單 AZ 是刻意的性能取捨。若資料不可重建，還要另外設計 durable copy／replication，而不是只看服務名稱有 S3。
3. Directory bucket 的 feature/authorization 與 general-purpose bucket 不完全相同；部署前要逐項驗證所需 API。

**選擇邊界：** 低延遲、高 request rate、可與 compute co-locate 且可接受／補足單 AZ 風險時使用；一般 data lake、網站物件、跨 AZ durability 或完整 S3 feature set 仍以 general-purpose bucket 為主。

**考試範圍：** SAA 主要仍考 storage class 與 durability/cost；S3 Express 是進階／新服務邊界，重點是不要把高性能誤解成共享磁碟。

- [AWS：Directory buckets and S3 Express One Zone](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html)

## 需要時再查：四個閱讀支點

### Amazon S3

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：同一份資料的存取頻率會隨時間改變，儲存單價之外還有retrieval、minimum duration與request成本。
- **具體例子／邊界：** 在「合規log前30天常查，之後六年幾乎不讀，但法律要求數小時內可取回。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### S3 Lifecycle

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：optimize lifecycle using total access cost, not storage price。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

## 回到 AWS：Components、功用與責任邊界

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

### S3 Lifecycle

- **功用：** 依object age、prefix/tag與version狀態自動transition或expire資料。
- **底層機制：** S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。
- **關鍵設定：** Filter、Transitions、Expiration、NoncurrentVersionTransitions、AbortIncompleteMultipartUpload與status。
- **選擇時機：** 存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。
- **替換時機：** 存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。

### S3 Glacier

- **功用：** 提供S3內低成本archive storage classes，以較高取回延遲換成本。
- **底層機制：** Objects仍由S3 API管理；Flexible Retrieval/Deep Archive需先restore臨時副本。
- **關鍵設定：** Instant/Flexible/Deep Archive class、retrieval tier、restore days、minimum duration與lifecycle transition。
- **選擇時機：** 長期備份、合規archive與極少存取資料。
- **替換時機：** 需要即時頻繁讀取用Standard/IA；RTO小於restore時間時不能選Deep Archive。

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

### S3 Lifecycle：逐項設定說明

#### `Filter`

- **控制什麼：** `Filter`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Lifecycle以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `Transitions`

- **控制什麼：** `Transitions`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `Expiration`

- **控制什麼：** `Expiration`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `NoncurrentVersionTransitions`

- **控制什麼：** `NoncurrentVersionTransitions`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `AbortIncompleteMultipartUpload`

- **控制什麼：** `AbortIncompleteMultipartUpload`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在S3 Lifecycle設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `status`

- **控制什麼：** `status`指定S3 Lifecycle的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

### S3 Glacier：逐項設定說明

#### `Instant/Flexible/Deep Archive class`

- **控制什麼：** `Instant/Flexible/Deep Archive class`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「長期備份、合規archive與極少存取資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Glacier依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `retrieval tier`

- **控制什麼：** `retrieval tier`選擇S3 Glacier的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `restore days`

- **控制什麼：** `restore days`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「長期備份、合規archive與極少存取資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在S3 Glacier設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `minimum duration`

- **控制什麼：** `minimum duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「長期備份、合規archive與極少存取資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定S3 Glacier的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `lifecycle transition`

- **控制什麼：** `lifecycle transition`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在S3 Glacier設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

## 可以直接對照 AWS 的設定範例

### S3 Lifecycle：30天轉IA、180天轉Deep Archive、清理舊version

```json
{
  "Rules": [{
    "ID": "archive-audit-logs",
    "Status": "Enabled",
    "Filter": {"Prefix": "audit/"},
    "Transitions": [
      {"Days": 30, "StorageClass": "STANDARD_IA"},
      {"Days": 180, "StorageClass": "DEEP_ARCHIVE"}
    ],
    "NoncurrentVersionTransitions": [
      {"NoncurrentDays": 30, "StorageClass": "GLACIER_IR"}
    ],
    "NoncurrentVersionExpiration": {"NoncurrentDays": 2555},
    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
  }]
}
```

1. Transitions只應在存取頻率與取回時間符合時使用；還要計入minimum duration與retrieval費。
2. Noncurrent rules與current object rules不同，versioning bucket若不清理會持續累積成本。
3. AbortIncompleteMultipartUpload避免失敗parts永久計費。

## 讀到這裡，請用自己的話說一次

1. Amazon S3的責任：以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
2. 底層機制：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
3. 第一個要看的設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
4. 選擇邏輯：用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。
5. 不要混淆：S3 Lifecycle的責任是「依object age、prefix/tag與version狀態自動transition或expire資料。」；它不會自動取代Amazon S3。
6. 替換訊號：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
7. 最常見錯法：把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。
8. 可移植原則：optimize lifecycle using total access cost, not storage price。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| S3 Lifecycle | 依object age、prefix/tag與version狀態自動transition或expire資料。 | S3非同步套用rules；storage class有minimum duration、minimum billable size與retrieval特性。 | 存取頻率可預測、需要archive、清理舊versions或未完成multipart uploads。 | 存取模式未知時可用Intelligent-Tiering，但仍要處理archive retrieval與monitoring費。 |
| S3 Glacier | 提供S3內低成本archive storage classes，以較高取回延遲換成本。 | Objects仍由S3 API管理；Flexible Retrieval/Deep Archive需先restore臨時副本。 | 長期備份、合規archive與極少存取資料。 | 需要即時頻繁讀取用Standard/IA；RTO小於restore時間時不能選Deep Archive。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。 | 只有當題目條件明確改變時才可能合理。 | 把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。」之間做選擇。
- 認得常考設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- 對應官方tasks：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAA｜Standard-IA total cost

一批 5 TB備份會保存兩年、平均每月讀取一次，要求毫秒存取與跨 AZ resilience。另一批暫存輸出只存14天且每天讀取。哪個判斷最合理？

A. 兩批都應寫入 Standard-IA；它只有較低儲存費，沒有 retrieval或 minimum-duration成本
B. 暫存輸出應用 One Zone-IA，因為所有 IA class都跨 AZ
C. 長期且少讀的備份可評估 Standard-IA；14天且頻繁讀取的輸出通常留 Standard更合理
D. 所有 objects寫入後立即轉 Standard-IA必然是最低總成本

**答案：C**

- **A：** 不正確。Standard-IA有 retrieval與 minimum storage duration等成本，不能只看每 GB storage price。
- **B：** 不正確。One Zone-IA把資料存於單一 AZ；只有可重建且能接受該故障域時才適用。
- **C：** 正確。長生命週期、低讀取頻率與毫秒 SLA符合 Standard-IA；短命且常讀資料可能被 retrieval與最低期限費用抵銷。
- **D：** 不正確。Object大小、存活期、request、retrieval與 early deletion都影響 TCO。

**事實查證：** [Understanding and managing Amazon S3 storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

### 練習題 2｜SAA｜One Zone-IA 適用資料

媒體公司把原始影片保存在 S3 Standard，另產生可由原始檔重建的縮圖。縮圖很少讀但需毫秒取得，且公司接受單一 AZ永久損失後重新產生。應選哪個 class？

A. S3 Glacier Deep Archive，因為任何 archive class都能直接毫秒 GET
B. S3 Standard-IA，因為 One Zone-IA其實也跨三個 AZ
C. S3 One Zone-IA，因資料可重建且明確接受單 AZ故障域
D. S3 Express One Zone，因唯一目的就是長期合規封存

**答案：C**

- **A：** 不正確。Deep Archive需要 restore且 RTO較長，不符合直接毫秒取得。
- **B：** 不正確。Standard-IA確實是 multi-AZ，但題目接受單 AZ以換成本；One Zone-IA不是 multi-AZ。
- **C：** 正確。One Zone-IA提供毫秒存取並把資料存於單一 AZ，適合已有耐久原始檔、可重建且明確接受 AZ損失的 secondary copy。
- **D：** 不正確。Express One Zone針對高頻、低延遲 request，不是極少讀縮圖的成本首選。

**事實查證：** [Understanding and managing Amazon S3 storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

### 練習題 3｜SAA｜Intelligent-Tiering 監控與 archive tiers

研究機構會保存 8 年的 1 MB分析結果，但無法預測哪些 objects下週會突然熱門。任何 object一旦被要求，都必須在毫秒內開始讀取。團隊可以接受 per-object監控費，但不能因自動分層而等待 restore。哪個設計最符合需求？

A. 啟用 Intelligent-Tiering並同時強制所有 objects進入 optional Deep Archive Access tier；所有 tier都可直接毫秒讀取
B. 使用 S3 Intelligent-Tiering的自動低延遲 access tiers，但不要為這批資料啟用需要非同步 restore的 optional Archive Access與 Deep Archive Access tiers
C. 全部放 Standard-IA；該 class會依每個 object的實際讀取自動切換 tier，而且沒有 retrieval charge
D. 建立固定90天後轉 Deep Archive的 Lifecycle rule；後續讀取會自動取消 transition並立即回傳內容

**答案：B**

- **A：** 不正確。Optional archive tiers可進一步降成本，但 archived object不是所有情況都能直接毫秒讀取；只有 RTO允許非同步取回時才應啟用。
- **B：** 正確。Intelligent-Tiering適合不可預測的 access pattern；Frequent、Infrequent與Archive Instant Access等自動 tiers維持低延遲，而監控與自動化有 per-object費用。
- **C：** 不正確。Standard-IA是固定 storage class，不會觀察存取後自動升降 tier，且讀取有 retrieval charge；可預測低頻資料才較適合直接選它。
- **D：** 不正確。Lifecycle transition依時間與 filter執行，不會因未來讀取預測而自動撤銷；Deep Archive資料需先 restore。

**事實查證：** [Managing storage costs with Amazon S3 Intelligent-Tiering - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)

### 練習題 4｜SAA｜Glacier Instant Retrieval

醫院要保存不可重建的診斷影像七年。每張影像約 20 MB，預計一年只讀一到兩次，但臨床人員提出 request後必須像線上 S3 object一樣在毫秒內取得。哪個 storage class最合適？

A. S3 Glacier Instant Retrieval，因它針對極少存取的長期資料提供毫秒級 retrieval，並以跨多個 AZ的設計保存資料
B. S3 Glacier Flexible Retrieval並使用 Standard restore，因 standard tier會讓第一次 GET在毫秒內完成
C. S3 Glacier Deep Archive，因最低 storage price同時代表最快 retrieval
D. S3 One Zone-IA，因唯一且不可重建的醫療副本最適合放在單一 AZ

**答案：A**

- **A：** 正確。Glacier Instant Retrieval適合每季或更少讀取、仍要求立即毫秒 access的長期資料；仍應把 minimum duration、retrieval與 request費用納入成本。
- **B：** 不正確。Flexible Retrieval的 archive object通常要先發出 restore並等待所選 tier完成；若可等待數分鐘到數小時才適合。
- **C：** 不正確。Deep Archive以較長的 restore window換取較低 storage cost，不能滿足臨床即時讀取。
- **D：** 不正確。One Zone-IA雖提供毫秒讀取，但單 AZ故障域不符合題目對唯一、不可重建副本的耐久性要求。

**事實查證：** [Understanding and managing Amazon S3 storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)、[Understanding S3 Glacier storage classes for long-term data storage - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/glacier-storage-classes.html)

### 練習題 5｜SAA｜Glacier Flexible Retrieval restore tier

法務部把案件附件放在 S3 Glacier Flexible Retrieval。平時幾乎不讀；重大事件時會指定一批 objects，允許等待數小時，並希望在 retrieval速度與費用間選擇。完成取回後只需讓副本可讀 10 天。哪個流程正確？

A. 直接重複 GET archived objects；client timeout會讓 S3在同一 request內完成 archive restore
B. 用 Lifecycle把整個 prefix轉回 Standard；轉層會同步、免費且自動在10天後回到原 class
C. 複寫到另一 bucket；replication會把 archived objects立即轉成可讀的 Standard copies
D. 對指定 objects發出 restore，依 RTO選 Flexible Retrieval的 expedited、standard或bulk tier，並把 temporary restored copy可用期設為10天

**答案：D**

- **A：** 不正確。Archived object要先完成 restore；一般 GET不會在一個長連線中自動等待數小時並回傳內容。
- **B：** 不正確。Lifecycle主要做較冷 storage class的 transition與 expiration，不是大量 archive retrieval的同步逆向操作。
- **C：** 不正確。Replication是另一種非同步複寫功能，不能取代明確的 archive restore workflow或保證事件時的完成時間。
- **D：** 正確。Flexible Retrieval可按事件的速度與成本選 retrieval tier；restore建立有期限的可存取副本，原 object仍保留原 storage class。

**事實查證：** [Restoring an archived object - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html)

### 練習題 6｜SAA｜Glacier Deep Archive 與 RTO

保險公司每天產生一次監管匯出檔，每份約 5 GB，法規要求保存七年且不得只有單 AZ副本。資料預計低於每年一次取用，災難演練證明 24 小時內可開始讀取即可。哪個選擇最符合最低長期 storage cost與 RTO？

A. S3 Express One Zone，因單 AZ低延遲 request最適合七年最低成本封存
B. S3 Glacier Deep Archive，並把非同步 restore時間與費用寫入 runbook
C. S3 One Zone-IA，因單 AZ storage同時滿足不得只有單 AZ副本的要求
D. S3 Glacier Instant Retrieval，因任何低頻資料即使可等待一天也必須支付毫秒 access能力

**答案：B**

- **A：** 不正確。Express One Zone優化單 AZ高效能 object access，成本與故障域都不符合此長期 archive案例。
- **B：** 正確。Deep Archive適合極少讀取且可接受較長 restore window的多年資料；實作仍需規劃 restore tier、演練與 retention控制。
- **C：** 不正確。One Zone-IA明確把資料放在單一 AZ，違反題目故障域限制；它適合可重建且需毫秒存取的資料。
- **D：** 不正確。Instant Retrieval能滿足更嚴格的毫秒 SLA，但題目允許24小時，支付該能力通常不是最低 storage cost方案。

**事實查證：** [Understanding S3 Glacier storage classes for long-term data storage - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/glacier-storage-classes.html)、[Restoring an archived object - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html)

### 練習題 7｜SAA｜Lifecycle filter 與 versioned objects

Versioning已啟用的 logging bucket同時保存 dev與prod資料。平台只要對 prefix `logs/prod/`且 tag `retention=standard`的 objects執行三件事：current version在30天後轉 Standard-IA、noncurrent versions在90天後永久刪除、未完成 multipart uploads在7天後中止。應如何配置？

A. 只設定 current version Expiration為90天；S3會自動用相同日期 transition current version並刪除所有 noncurrent versions
B. 在 Lifecycle filter使用上傳者的 IAM Principal；Lifecycle可依 principal而不依 prefix或 tag篩選
C. 設定 AbortIncompleteMultipartUpload；此 action也會刪除已成功完成但超過7天的 objects
D. 以 prefix與 tag組合 filter限定 scope，分別設定 current Transition、NoncurrentVersionExpiration及 AbortIncompleteMultipartUpload actions

**答案：D**

- **A：** 不正確。Current與noncurrent versions有不同 actions；Expiration也不等同 transition，不能靠一個 current rule推導三種行為。
- **B：** 不正確。Lifecycle filter可依 key prefix、object tags及相關條件限定，不是以提出 request的 IAM principal作歷史 object篩選。
- **C：** 不正確。Abort action只清除未完成 upload的 parts，不會刪除已完成 object；已完成 objects需獨立 transition或expiration規則。
- **D：** 正確。精確 filter避免碰到 dev資料，且三種 lifecycle目標分屬 current、noncurrent與incomplete multipart upload的獨立 actions。

**事實查證：** [Managing the lifecycle of objects - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

### 練習題 8｜SAA → SAP｜Minimum duration 與 billable object size

IoT平台每天產生數百萬個10 KB objects，固定14天後刪除，且只在寫入後第一天讀取。團隊在2026年新增Lifecycle rule，打算第二天轉到IA或Glacier class，但沒有設定`ObjectSizeGreaterThan`或`ObjectSizeLessThan` filter。選擇兩項正確判斷。

A. 依現行預設，這些小於128 KB的objects不會被Lifecycle transition；若要改變此行為，必須明確加入object-size filter
B. Lifecycle transition request在所有 storage class都免費，因此 object數量不影響成本
C. 只要14天後刪除，S3就不會收取尚未滿足的 minimum-duration相關費用
D. 轉層後每個 10 KB object在所有 IA與Glacier class都只按實際10 KB計費，沒有任何 metadata或minimum-size考量
E. 即使另加filter允許小objects轉層，也要把minimum billable size、minimum duration、transition requests、metadata與retrieval納入TCO；維持Standard可能更便宜

**答案：A、E**

- **A：** 正確。對2024年9月之後建立或修改的Lifecycle configuration，S3預設不transition小於128 KB的objects；題目未提供自訂size filter，所以規則不會如團隊預期執行。
- **B：** 不正確。Lifecycle transition會產生 request；數百萬 objects即使總 bytes不大，也可能讓request成本成為主要項目。
- **C：** 不正確。提早刪除或轉出仍可能被收取剩餘 minimum storage duration，故14天到期不代表成本也只算14天。
- **D：** 不正確。多種IA與archive class有minimum billable size或額外metadata計費規則，不能假設所有class都只按10 KB。
- **E：** 正確。自訂filter只改變「能否transition」，不會消除目標class的最低計費大小、最短儲存期間、request、metadata或retrieval費用；大量短命小object必須以完整TCO比較。

**事實查證：** [Understanding and managing Amazon S3 storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)、[Managing the lifecycle of objects - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)、[Constraints for transitioning objects between storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)

### 練習題 9｜SAP｜S3 Express One Zone 性能與故障域

資料科學平台在單一 AZ內執行 GPU叢集，每小時反覆讀寫數千萬個 64 KB中間 objects，要求一致低延遲。所有中間結果都可由 S3 Standard中的原始資料重建。選擇兩項合適的設計判斷。

A. 把 S3 Express One Zone directory bucket當成跨 AZ POSIX shared filesystem，依賴它提供 file locking與atomic directory rename
B. 在運算所在 AZ建立 S3 Express One Zone directory bucket，讓這批可重建中間資料利用單 AZ高 request效能
C. 把唯一的災難復原副本移到同一 directory bucket，因 Express One Zone自動跨 Region複寫
D. 驗證應用使用directory bucket支援的API與endpoint模型，並保留從耐久原始資料重建的故障處理流程
E. 選 Express One Zone是因它屬於需數小時 restore的最低成本archive class

**答案：B、D**

- **A：** 不正確。Express One Zone仍是object storage，不提供完整POSIX locking或directory rename contract；需要該介面時應評估EFS或FSx。
- **B：** 正確。工作負載與bucket位於同一AZ且資料可重建，符合其低延遲、高request rate與單AZ故障域的取捨。
- **C：** 不正確。單AZ class不能作為唯一跨Region DR副本；需要保護的資料必須另放在適當的multi-AZ或replicated storage。
- **D：** 正確。Directory buckets與general purpose buckets的endpoint、命名及部分feature/API行為不同，應先驗證相容性與重建runbook。
- **E：** 不正確。Express One Zone是高效能線上storage class，可直接存取；它不是Glacier archive或restore workflow。

**事實查證：** [Optimizing S3 Express One Zone performance - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-performance.html)、[Working with directory buckets - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-overview.html)

### 練習題 10｜SAP｜Archive restore operational workflow

稽核團隊要求在30天後檢查 600萬個 S3 Glacier Flexible Retrieval objects。平台必須批次提出restore、追蹤每個項目結果，讓temporary copies可讀14天，並在演練中證明RTO與request成本。選擇兩項必要做法。

A. 以 S3 Inventory等manifest建立 S3 Batch Operations restore job，保存completion report並追蹤失敗項目
B. 對bucket送出一次restore request；S3會同步恢復其中所有archived objects且沒有per-object狀態
C. 建立Lifecycle transition到Standard；它會立即、免費地把所有archive objects逆向轉層
D. 改建replication rule；replication與restore語意相同且能保證所有objects同時完成
E. 在restore request設定temporary copy天數，監控restore狀態與到期，並用實際演練量測完成時間與費用

**答案：A、E**

- **A：** 正確。Batch Operations可依manifest對大量objects執行restore；completion report讓團隊重試與證明每個object的結果。
- **B：** 不正確。Archive restore是per-object operation，即使透過batch協調也不是一個同步bucket-wide call。
- **C：** 不正確。Lifecycle transition用於按規則移往較冷class，不是archive restore的免費逆向機制。
- **D：** 不正確。Replication建立額外copy但不取代原archive object的restore流程，也不提供相同完成時間保證。
- **E：** 正確。Restored copy有指定可用期間且原object仍在archive class；監控與演練才能驗證RTO、錯誤率及request/retrieval成本。

**事實查證：** [Restoring an archived object - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html)、[Performing object operations in bulk with Batch Operations - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「用access pattern與復原時間選Standard、IA、One Zone-IA、Intellig…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「同一份資料的存取頻率會隨時間改變，儲存單價之外還有retrieval、minimum duration與request成本。」，所以「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」能直接滿足它；若constraint改成「Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」。替代方案「Intelligent-Tiering降低未知pattern的決策成本，但仍需理解archive tier取回延遲。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「同一份資料的存取頻率會隨時間改變，儲存單價之外還有retrieval、minimum duration與request成本。」，排除會導致「把每天讀取的資料轉Glacier，或忽略minimum storage duration與小物件轉換費。」的選項，再選「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」。本章對應的代表task包括：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「用access pattern與復原時間選Standard、IA、One Zone-IA、Intelligent-Tiering與Glacier classes。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「optimize lifecycle using total access cost, not storage price」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 43 章　EBS、EFS 與 FSx 選型

共享方式、protocol、latency與workload相容性決定block/file服務。

## 跟著一筆資料走：先從故事開始

故事從一個看似簡單的需求開始：Windows home directory、HPC scratch與Linux web uploads需要不同共享檔案服務。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：共享方式、protocol、latency與workload相容性決定block/file服務。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon EBS會是本章的主要角色，Amazon EFS則幫我們看清邊界。方向是「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Windows home directory、HPC scratch與Linux web uploads需要不同共享檔案服務。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon EBS：authoritative或主要資料路徑]
          │ 為EC2提供單AZ持久block volumes。
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Amazon EFS：提供regional或One Zone、彈性容量的managed NFS file system。
  · Amazon FSx：提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file sy…

失敗時先找：跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon EBS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EBS和Amazon EFS並不是兩個任意的產品名稱。前者適合本章，是因為「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」直接回應了眼前的問題；後者描述的「EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「filesystem semantics are part of the application contract」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 |
| Amazon EFS | 提供regional或One Zone、彈性容量的managed NFS file system。 | 各AZ mount target接收NFSv4.1；多clients共享目錄與POSIX metadata。 |
| Amazon FSx | 提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file systems。 | 每種engine保留原生protocol與features，由AWS管理server、storage與backup。 |

## 把全圖套進一個具體案例

**場景：** Windows home directory、HPC scratch與Linux web uploads需要不同共享檔案服務。

1. 故事的起點：Windows home directory、HPC scratch與Linux web uploads需要不同共享檔案服務。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EBS負責「為EC2提供單AZ持久block volumes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EFS、Amazon FSx各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon EBS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：共享方式、protocol、latency與workload相容性決定block/file服務。
- **具體例子／邊界：** 在「Windows home directory、HPC scratch與Linux web uploads需要不同共享檔案服務。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EFS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：filesystem semantics are part of the application contract。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### IOPS

每秒可完成的I/O operations數，偏向小型random reads/writes能力。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### Amazon EBS

- **功用：** 為EC2提供單AZ持久block volumes。
- **底層機制：** Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。
- **關鍵設定：** gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
- **選擇時機：** boot disk、database、低延遲random I/O與需要in-place update的單instance state。
- **替換時機：** 多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。

### Amazon EFS

- **功用：** 提供regional或One Zone、彈性容量的managed NFS file system。
- **底層機制：** 各AZ mount target接收NFSv4.1；多clients共享目錄與POSIX metadata。
- **關鍵設定：** Standard/One Zone、performance mode、throughput mode、mount targets、access points、lifecycle與TLS mount。
- **選擇時機：** Linux shared content、home directories、ECS/EKS/Lambda共享files。
- **替換時機：** Windows SMB選FSx Windows；HPC parallel I/O選FSx Lustre；block database選EBS。

### Amazon FSx

- **功用：** 提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file systems。
- **底層機制：** 每種engine保留原生protocol與features，由AWS管理server、storage與backup。
- **關鍵設定：** file-system type、deployment type、throughput capacity、storage type、AD、subnets與backup。
- **選擇時機：** 既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。
- **替換時機：** 一般Linux NFS共享用EFS較簡單；object workload用S3。

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

### Amazon EFS：逐項設定說明

#### `Standard/One Zone`

- **控制什麼：** `Standard/One Zone`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。
- **何時需要：** 需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。
- **怎麼設定／驗證：** 明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。
- **常見錯法：** One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。

#### `performance mode`

- **控制什麼：** `performance mode`選擇Amazon EFS的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `throughput mode`

- **控制什麼：** `throughput mode`選擇Amazon EFS的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `mount targets`

- **控制什麼：** `mount targets`指定Amazon EFS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `access points`

- **控制什麼：** `access points`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「Linux shared content、home directories、ECS/EKS/Lambda共享files。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EFS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `lifecycle`

- **控制什麼：** `lifecycle`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「Linux shared content、home directories、ECS/EKS/Lambda共享files。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EFS依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `TLS mount`

- **控制什麼：** `TLS mount`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「Linux shared content、home directories、ECS/EKS/Lambda共享files。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EFS的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

### Amazon FSx：逐項設定說明

#### `file-system type`

- **控制什麼：** `file-system type`選擇Amazon FSx的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `deployment type`

- **控制什麼：** `deployment type`選擇Amazon FSx的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `throughput capacity`

- **控制什麼：** `throughput capacity`設定Amazon FSx的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `storage type`

- **控制什麼：** `storage type`選擇Amazon FSx的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `AD`

- **控制什麼：** `AD`指定Amazon FSx的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon FSx的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon FSx依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

## 讀到這裡，請用自己的話說一次

1. Amazon EBS的責任：為EC2提供單AZ持久block volumes。
2. 底層機制：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。
3. 第一個要看的設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
4. 選擇邏輯：單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。
5. 不要混淆：Amazon EFS的責任是「提供regional或One Zone、彈性容量的managed NFS file system。」；它不會自動取代Amazon EBS。
6. 替換訊號：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
7. 最常見錯法：跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。
8. 可移植原則：filesystem semantics are part of the application contract。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 | boot disk、database、低延遲random I/O與需要in-place update的單instance state。 | 多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。 |
| Amazon EFS | 提供regional或One Zone、彈性容量的managed NFS file system。 | 各AZ mount target接收NFSv4.1；多clients共享目錄與POSIX metadata。 | Linux shared content、home directories、ECS/EKS/Lambda共享files。 | Windows SMB選FSx Windows；HPC parallel I/O選FSx Lustre；block database選EBS。 |
| Amazon FSx | 提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file systems。 | 每種engine保留原生protocol與features，由AWS管理server、storage與backup。 | 既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。 | 一般Linux NFS共享用EFS較簡單；object workload用S3。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。 | 只有當題目條件明確改變時才可能合理。 | 跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。」之間做選擇。
- 認得常考設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
- 對應官方tasks：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜Block、shared file 與 object 介面契約

公司要把三套workloads搬到AWS：單台EC2上的PostgreSQL需要低延遲block device；跨三個AZ的Linux web fleet需要共享NFS namespace與file locking；不可變build artifacts只依key做PUT/GET並長期保存。哪個對應正確？

A. PostgreSQL用S3、web fleet用EBS、artifacts用EFS
B. PostgreSQL用EBS、web fleet用EFS、artifacts用S3
C. 三者都用S3，因object capacity足以取代block與file semantics
D. PostgreSQL與web fleet共用一個跨AZ EBS volume，artifacts放FSx for Windows

**答案：B**

- **A：** 不正確。S3不是EC2資料庫所需的raw block device；單一EBS volume也不是跨AZ web fleet的共享NFS namespace。
- **B：** 正確。EBS提供EC2 block storage，EFS提供可跨多個clients掛載的NFS file service，S3適合bucket/key object access。
- **C：** 不正確。容量彈性不會改變介面契約；S3不提供一般block device、POSIX locking或任意in-place writes。
- **D：** 不正確。EBS volume位於單一AZ且不能作為一般跨AZ共享file service；FSx for Windows也不是key-based artifact archive的必要選擇。

**事實查證：** [AWS Storage category iconStorage - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)、[What is Amazon Elastic Block Store? - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/what-is-ebs.html)、[What is Amazon Elastic File System? - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)

### 練習題 2｜SAA｜EBS gp3、io2、st1 與 sc1

架構師要為四台EC2選EBS：一般應用boot volume需SSD且要獨立調IOPS；核心交易資料庫要求一致高IOPS與較高durability；日誌分析器做大型sequential scans；冷資料批次只需最低成本sequential access且不是boot volume。哪個順序正確？

A. gp3、st1、io2、sc1
B. io2、gp3、sc1、st1
C. st1、io2、gp3、sc1
D. gp3、io2、st1、sc1

**答案：D**

- **A：** 不正確。st1是throughput-optimized HDD，適合大型sequential I/O，不適合核心高IOPS transactional database。
- **B：** 不正確。一般boot volume通常不需io2成本；sc1的低吞吐冷HDD也不適合較活躍的日誌大型scan。
- **C：** 不正確。st1與sc1 HDD不能作為boot volume；gp3也不是此組中critical sustained high-IOPS資料庫的最佳對應。
- **D：** 正確。gp3適合一般SSD並可分別設定IOPS/throughput，io2服務關鍵高IOPS，st1偏大型sequential throughput，sc1偏低頻冷sequential資料。

**事實查證：** [Amazon EBS volume types - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)

### 練習題 3｜SAA → SAP｜EBS AZ scope 與 snapshot restore

訂單服務的EC2與EBS volume位於us-east-1a。團隊每15分鐘建立一次已協調application flush的EBS snapshot。若1a不可用，必須在us-east-1b恢復到最近restore point。哪個runbook正確？

A. 在1b從最近snapshot建立新EBS volume，附加到1b的instance，完成filesystem/application recovery後切流量
B. 把1a的既有volume直接跨AZ附加到1b；EBS會自動延伸同一block device
C. 等待snapshot從1a恢復，因EBS snapshot只存在建立它的AZ
D. 只啟用跨AZ Auto Scaling；它會同步複寫每台instance的EBS filesystem state

**答案：A**

- **A：** 正確。EBS volume是AZ scoped；snapshot可在同Region另一AZ建立新volume。協調flush與restore演練用來提高application consistency並量測RTO。
- **B：** 不正確。既有volume不能跨AZ直接attach；必須透過snapshot、application replication或其他DR機制重建。
- **C：** 不正確。EBS snapshot是Region範圍的durable backup表示，可用於該Region內不同AZ的新volume。
- **D：** 不正確。Auto Scaling替換compute capacity，但不會推斷並同步每個stateful EBS filesystem內容。

**事實查證：** [Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)、[Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)

### 練習題 4｜SAP｜EBS Multi-Attach 限制與 coordination

三台同一AZ的Linux instances需要同時讀寫一個共享block device。團隊準備把一般ext4 volume掛到三台主機，並假設EBS會協調metadata與writer fencing。哪個評估最正確？

A. 所有EBS types都可跨AZ Multi-Attach，ext4會自動切換為cluster filesystem
B. 只要啟用Multi-Attach，EBS會提供跨Region synchronous replication與distributed locking
C. 只有受支援的io1/io2 volume與instance組合可使用同AZ Multi-Attach；應用仍需cluster-aware filesystem、locking與fencing，否則改評估EFS/FSx
D. 把volume類型改成st1即可，因HDD volumes原生提供多writer檔案協調

**答案：C**

- **A：** 不正確。Multi-Attach有volume type、instance及同AZ限制；一般ext4也不是多節點協調filesystem。
- **B：** 不正確。Multi-Attach分享同一AZ block device，不建立跨Region replica，也不替應用提供distributed lock manager。
- **C：** 正確。EBS只暴露共享blocks；資料一致性、fencing與cluster membership仍由上層軟體負責。一般共享file需求通常EFS或FSx更合適。
- **D：** 不正確。st1著重sequential throughput且不支援此Multi-Attach設計；HDD介質不會產生writer coordination。

**事實查證：** [Attach an EBS volume to multiple EC2 instances using Multi-Attach - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes-multi.html)

### 練習題 5｜SAA｜EFS mount target、routing 與 security group

Linux應用分散在兩個AZ的private subnets，必須以NFS掛載同一個EFS並在任一AZ故障後繼續服務。安全要求是不經公網，且只有application security group可連NFS。應如何部署？

A. 只建立public mount target並經Internet Gateway連線；EFS private DNS無法在VPC內使用
B. 在每個使用中的AZ建立mount target，讓其security group允許來自application security group的TCP 2049，client使用EFS DNS並可加TLS/IAM mount
C. 在同一AZ的每個subnet各建多個mount targets來形成throughput shards，另一AZ不需mount target
D. 用S3 bucket policy授予`elasticfilesystem:ClientMount`；NFS network與POSIX permissions不再需要

**答案：B**

- **A：** 不正確。EFS mount targets使用VPC網路介面，clients可從private subnets路由存取，不必暴露到Internet。
- **B：** 正確。每個使用AZ的mount target提供本地AZ網路路徑與容錯；security groups控制NFS，TLS/IAM、access points及file permissions可補充身份與資料保護。
- **C：** 不正確。每個AZ只能有一個mount target；mount target數量也不是資料吞吐sharding機制。
- **D：** 不正確。S3 bucket policy不控制EFS。EFS存取同時涉及VPC routing/security groups、IAM client actions及filesystem permissions。

**事實查證：** [Managing mount targets - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/accessing-fs.html)、[Using VPC security groups - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/network-access.html)

### 練習題 6｜SAA → SAP｜EFS performance 與 throughput mode

內容平台的EFS大部分時間低流量，但每週發布時有數千個clients在20分鐘內平行讀取，且互動request重視低per-operation latency。檔案系統容量不大，團隊不想手動預估每次burst。哪個起始配置最合理？

A. Max I/O performance mode加Bursting throughput，因Max I/O一定比General Purpose有更低latency
B. General Purpose加Provisioned throughput，且Provisioned數值必須永遠與stored bytes固定成比例
C. 在每個AZ增加多個mount targets；每個target會建立獨立throughput partition
D. General Purpose performance mode加Elastic throughput，並監控client I/O、throughput與latency後再調整

**答案：D**

- **A：** 不正確。Max I/O支援更高parallelism但有較高per-operation latency；重視一般低延遲時通常先從General Purpose評估。
- **B：** 不正確。Provisioned throughput可與storage量分開設定，並非必須固定綁定；題目也希望自動因應無法預估的spikes。
- **C：** 不正確。Mount targets提供AZ網路入口，不是可任意增加的throughput shards，且每個AZ只能有一個。
- **D：** 正確。General Purpose符合低latency需求，Elastic throughput可依工作負載自動調整；監控仍用來驗證是否有client或模式瓶頸。

**事實查證：** [Amazon EFS performance specifications - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/performance.html)

### 練習題 7｜SAA → SAP｜EFS Standard、One Zone、Lifecycle 與 replication

設計檔案服務要保存唯一的使用者文件，primary Region內須承受單一AZ損失；30天未讀的files要自動降成本；另一Region也要有可演練的DR copy。哪個設計符合全部要求？

A. 使用Regional EFS storage classes，設定Lifecycle將冷files移到IA，並另設定EFS replication或backup/restore流程處理跨Region DR
B. 使用EFS One Zone-IA；名稱中的IA代表它會把資料複寫到多個AZ並在另一Region備份
C. 只啟用EFS Lifecycle；任何file轉到IA後都會自動建立跨Region copy
D. 使用Regional EFS IA，但讀取前必須提交數小時restore，所以不能由應用直接存取

**答案：A**

- **A：** 正確。Regional classes保存跨AZ availability；Lifecycle解決access-based成本，replication或backup則分別處理Region故障與restore演練。
- **B：** 不正確。One Zone classes將資料存於單一AZ，不符合唯一文件承受AZ損失的要求；IA也不等於backup。
- **C：** 不正確。Lifecycle只在同filesystem內改變storage class，不會建立另一Region的災難復原副本。
- **D：** 不正確。EFS IA仍由EFS透明提供file access，不使用Glacier式先restore數小時的workflow。

**事實查證：** [Features of Amazon EFS - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/features.html)、[Managing storage lifecycle - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/lifecycle-management-efs.html)、[Replicating EFS file systems - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/efs-replication.html)

### 練習題 8｜SAA｜FSx for Windows File Server

企業要遷移Windows home drives。Clients必須使用SMB、保留NTFS ACL、透過既有Microsoft Active Directory驗證，並在單一AZ故障時自動fail over。選擇兩項合適設計。

A. 使用EFS，因EFS原生提供SMB、NTFS ACL與Windows DFS namespaces
B. 使用FSx for Lustre scratch deployment，因Lustre是Windows home directory的managed SMB service
C. 部署FSx for Windows File Server Multi-AZ並整合self-managed或AWS Managed Microsoft AD
D. 把每個file改成S3 object ACL；object ACL可完整呈現NTFS share與DFS行為
E. 依峰值負載規劃throughput capacity與storage，配置backups，並以建議的DNS名稱或DFS namespace提供clients存取

**答案：C、E**

- **A：** 不正確。EFS主要提供NFS給Linux/Unix workloads，不是原生NTFS/SMB managed Windows file server。
- **B：** 不正確。Lustre是高效能parallel filesystem，不提供題目所需的Windows SMB與NTFS ACL語意。
- **C：** 正確。FSx for Windows提供SMB、Windows ACL與AD整合；Multi-AZ deployment符合AZ故障自動failover需求。
- **D：** 不正確。S3 object authorization與NTFS file/share ACL模型不同，也不會直接成為SMB或DFS namespace。
- **E：** 正確。Multi-AZ不取代容量、效能、backup與client名稱設計；這些設定共同決定可用性與使用者體驗。

**事實查證：** [What is FSx for Windows File Server? - Amazon FSx for Windows File Server](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)

### 練習題 9｜SAA → SAP｜FSx for Lustre 與 S3-linked HPC

基因分析會在數千個Linux compute cores上執行，input datasets位於S3，job需要共享POSIX namespace與極高parallel throughput。運算中間資料可重建，完成結果要寫回S3。選擇兩項正確設計。

A. 讓所有nodes跨AZ掛載同一gp3 volume；一般EBS會自動提供parallel filesystem namespace
B. 為可重建的短期運算評估FSx for Lustre scratch deployment；若需較長期durability再評估persistent deployment
C. 使用FSx for Windows，因SMB server會把I/O自動轉成Lustre protocol
D. 設定FSx for Lustre與S3 data repository整合，在S3與filesystem namespace間載入inputs並匯出results
E. 只使用S3 Select；它能為任何未修改的HPC binary提供完整POSIX shared filesystem

**答案：B、D**

- **A：** 不正確。一般EBS volume是block device，不為數千nodes提供跨AZ共享namespace或cluster filesystem coordination。
- **B：** 正確。Scratch deployment適合temporary、可重建且追求高throughput的workloads；persistent deployment用於需要更高durability或較長生命週期的資料。
- **C：** 不正確。FSx for Windows提供SMB/Windows semantics，不會轉成Lustre parallel filesystem。
- **D：** 正確。Data repository integration讓S3作為durable data lake，而Lustre在compute期間提供高效能file access與結果export路徑。
- **E：** 不正確。S3 Select只對受支援object格式執行部分內容查詢，不會提供POSIX paths、locking或任意filesystem calls。

**事實查證：** [What is Amazon FSx for Lustre? - FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)、[Using data repositories with Amazon FSx for Lustre - FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fsx-data-repositories.html)

### 練習題 10｜SAP｜FSx for ONTAP 與 OpenZFS

公司同時遷移兩套系統：系統A依賴NetApp管理流程、NFS/SMB/iSCSI及space-efficient snapshots/clones；系統B是Linux NFS應用，操作手冊依賴ZFS snapshots與clones。選擇兩項正確判斷。

A. 系統A優先評估FSx for NetApp ONTAP，並驗證所需protocol、storage efficiency、deployment type與migration工具
B. 兩套系統都應只因資料含JSON副檔名而選FSx for OpenZFS
C. ONTAP與OpenZFS都是S3-compatible object stores，不提供NFS、SMB或iSCSI
D. 選任一FSx service後即可忽略client protocol、DNS、backup、encryption與throughput相容性
E. 系統B優先評估FSx for OpenZFS，並依HA、throughput、backup及ZFS資料功能選擇適當deployment

**答案：A、E**

- **A：** 正確。ONTAP符合NetApp-compatible多protocol與資料管理需求；仍要確認實際protocol、容量、HA及遷移限制。
- **B：** 不正確。檔案內容或副檔名不決定filesystem產品；應以client protocol與既有data-management semantics選型。
- **C：** 不正確。這些是managed file systems；ONTAP支援多種file/block protocols，OpenZFS提供NFS與ZFS資料功能。
- **D：** 不正確。Managed service減少基礎設施操作，但不會消除application protocol、network、backup或performance設計。
- **E：** 正確。OpenZFS適合需要NFS與熟悉ZFS snapshots/clones的Linux workload，deployment與保護設定仍要依RTO/RPO選擇。

**事實查證：** [What is Amazon FSx for NetApp ONTAP? - FSx for ONTAP](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/what-is-fsx-ontap.html)、[What is Amazon FSx for OpenZFS? - FSx for OpenZFS](https://docs.aws.amazon.com/fsx/latest/OpenZFSGuide/what-is-fsx.html)、[AWS Storage category iconStorage - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「共享方式、protocol、latency與workload相容性決定block/file服務。」，所以「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」能直接滿足它；若constraint改成「EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」。替代方案「EFS elastic吞吐降低容量規劃，FSx可提供特定檔案系統功能與高效能。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「共享方式、protocol、latency與workload相容性決定block/file服務。」，排除會導致「跨AZ application使用單AZ EBS當共享盤，或忽略EFS throughput mode。」的選項，再選「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」。本章對應的代表task包括：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「單EC2低延遲block用EBS；Linux共享NFS用EFS；Windows/Lustre/NetApp/OpenZFS需求用對應FSx。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「filesystem semantics are part of the application contract」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 44 章　Storage Gateway、DataSync、Transfer 與 Snow

資料搬移受網路頻寬、停機窗口、protocol、持續同步與實體運送限制。

## 跟著一筆資料走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：資料中心有3PB影像、每日新增20TB，合作夥伴仍用SFTP。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：資料搬移受網路頻寬、停機窗口、protocol、持續同步與實體運送限制。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS DataSync負責主要工作，AWS Storage Gateway提醒我們答案不是永遠固定。本章會走向「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：資料中心有3PB影像、每日新增20TB，合作夥伴仍用SFTP。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[AWS DataSync：authoritative或主要資料路徑]
          │ 以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨stor…
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · AWS Storage Gateway：在on-premises提供file/volume/tape介面，後端整合AWS storage。
  · AWS Transfer Family：以managed SFTP/FTPS/FTP/AS2 endpoints把partner files存入S…
  · AWS Snow Family：以實體devices進行離線large-scale data transfer或edge compute。

失敗時先找：只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問AWS DataSync有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS DataSync和AWS Storage Gateway並不是兩個任意的產品名稱。前者適合本章，是因為「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」直接回應了眼前的問題；後者描述的「DMS適合資料庫持續複寫，不應代替一般檔案搬移。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「migration throughput is bytes plus change rate plus verification」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS DataSync | 以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨storage。 | Agent平行讀寫、加密傳輸、驗證完整性並依task schedule執行。 |
| AWS Storage Gateway | 在on-premises提供file/volume/tape介面，後端整合AWS storage。 | Virtual/hardware appliance維持local cache並把資料非同步寫入S3/EBS snapshots/virtual tape。 |
| AWS Transfer Family | 以managed SFTP/FTPS/FTP/AS2 endpoints把partner files存入S3/EFS。 | Service終止protocol與authentication，將user映射到IAM role和logical directory。 |
| AWS Snow Family | 以實體devices進行離線large-scale data transfer或edge compute。 | AWS寄送加密device；客戶copy後寄回，AWS匯入指定storage。 |

## 把全圖套進一個具體案例

**場景：** 資料中心有3PB影像、每日新增20TB，合作夥伴仍用SFTP。

1. 故事的起點：資料中心有3PB影像、每日新增20TB，合作夥伴仍用SFTP。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS DataSync負責「以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨storage。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Agent平行讀寫、加密傳輸、驗證完整性並依task schedule執行。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Storage Gateway、AWS Transfer Family、AWS Snow Family各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「離線大規模且bandwidth不足用Snow；提供持續hybrid storage介面用Storage Gateway。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS DataSync

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：資料搬移受網路頻寬、停機窗口、protocol、持續同步與實體運送限制。
- **具體例子／邊界：** 在「資料中心有3PB影像、每日新增20TB，合作夥伴仍用SFTP。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Storage Gateway

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：DMS適合資料庫持續複寫，不應代替一般檔案搬移。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：migration throughput is bytes plus change rate plus verification。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### modernization

為可維護性、可靠性、交付速度或成本改善application/platform；應由可量測outcome驅動，而非因服務較新。

### migration

把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### AWS DataSync

- **功用：** 以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨storage。
- **底層機制：** Agent平行讀寫、加密傳輸、驗證完整性並依task schedule執行。
- **關鍵設定：** source/destination location、agent、include/exclude filters、bandwidth、verification、schedule與task report。
- **選擇時機：** 持續或一次性online file/object migration、metadata保留與驗證。
- **替換時機：** 離線大規模且bandwidth不足用Snow；提供持續hybrid storage介面用Storage Gateway。

### AWS Storage Gateway

- **功用：** 在on-premises提供file/volume/tape介面，後端整合AWS storage。
- **底層機制：** Virtual/hardware appliance維持local cache並把資料非同步寫入S3/EBS snapshots/virtual tape。
- **關鍵設定：** File/Volume/Tape gateway、cache/storage disks、SMB/NFS/iSCSI、bandwidth與CloudWatch。
- **選擇時機：** legacy apps需維持local protocol、hybrid cache、backup/tape modernization。
- **替換時機：** 只要快速搬完資料用DataSync；它不是一般跨Region filesystem。

### AWS Transfer Family

- **功用：** 以managed SFTP/FTPS/FTP/AS2 endpoints把partner files存入S3/EFS。
- **底層機制：** Service終止protocol與authentication，將user映射到IAM role和logical directory。
- **關鍵設定：** protocol/endpoint type、identity provider、user role/home directory、logging、workflow與custom hostname。
- **選擇時機：** 合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。
- **替換時機：** 內部bulk migration用DataSync；不要為SFTP自行長期維護EC2 servers。

### AWS Snow Family

- **功用：** 以實體devices進行離線large-scale data transfer或edge compute。
- **底層機制：** AWS寄送加密device；客戶copy後寄回，AWS匯入指定storage。
- **關鍵設定：** job/device type、capacity、KMS、shipping、import target、cluster/edge compute與chain of custody。
- **選擇時機：** 網路頻寬無法在migration window內搬完PB級資料。
- **替換時機：** 持續同步或可用足夠線路時DataSync/DX更合適；必須先確認所在Region與服務供應狀態。

## 考前與實作時再查：設定操作手冊

### AWS DataSync：逐項設定說明

#### `source/destination location`

- **控制什麼：** `source/destination location`指定AWS DataSync讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `agent`

- **控制什麼：** `agent`指定AWS DataSync依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。
- **何時需要：** Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。
- **怎麼設定／驗證：** 鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。
- **常見錯法：** Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。

#### `include/exclude filters`

- **控制什麼：** `include/exclude filters`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「持續或一次性online file/object migration、metadata保留與驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS DataSync以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `bandwidth`

- **控制什麼：** `bandwidth`設定AWS DataSync的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「持續或一次性online file/object migration、metadata保留與驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `verification`

- **控制什麼：** `verification`定義AWS DataSync用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「持續或一次性online file/object migration、metadata保留與驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS DataSync的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `task report`

- **控制什麼：** `task report`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「持續或一次性online file/object migration、metadata保留與驗證。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS DataSync的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

### AWS Storage Gateway：逐項設定說明

#### `File/Volume/Tape gateway`

- **控制什麼：** `File/Volume/Tape gateway`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「legacy apps需維持local protocol、hybrid cache、backup/tape modernization。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Storage Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `cache/storage disks`

- **控制什麼：** `cache/storage disks`選擇AWS Storage Gateway的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `SMB/NFS/iSCSI`

- **控制什麼：** `SMB/NFS/iSCSI`選擇AWS Storage Gateway的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `bandwidth`

- **控制什麼：** `bandwidth`設定AWS Storage Gateway的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「legacy apps需維持local protocol、hybrid cache、backup/tape modernization。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `CloudWatch`

- **控制什麼：** `CloudWatch`決定AWS Storage Gateway蒐集哪些control/data-plane audit events，以及如何集中查詢或監控。
- **何時需要：** 需要回答誰在何時修改resource、誰讀寫敏感資料，或集中多帳號事件調查時。
- **怎麼設定／驗證：** 選擇management/data event selectors、accounts/Regions、retention與S3/Lake/CloudWatch destination；用已知API call驗證事件可查。
- **常見錯法：** Data events量大且可能昂貴；只開management events看不到S3 object/Lambda invoke等data-plane行為。

### AWS Transfer Family：逐項設定說明

#### `protocol/endpoint type`

- **控制什麼：** `protocol/endpoint type`選擇AWS Transfer Family的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `identity provider`

- **控制什麼：** `identity provider`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Transfer Family明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `user role/home directory`

- **控制什麼：** `user role/home directory`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Transfer Family明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Transfer Family選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `workflow`

- **控制什麼：** `workflow`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** AWS Transfer Family需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `custom hostname`

- **控制什麼：** `custom hostname`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Transfer Family的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

### AWS Snow Family：逐項設定說明

#### `job/device type`

- **控制什麼：** `job/device type`選擇AWS Snow Family的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `capacity`

- **控制什麼：** `capacity`設定AWS Snow Family的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「網路頻寬無法在migration window內搬完PB級資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「網路頻寬無法在migration window內搬完PB級資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Snow Family指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `shipping`

- **控制什麼：** `shipping`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。
- **何時需要：** Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。
- **怎麼設定／驗證：** 維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。
- **常見錯法：** 過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。

#### `import target`

- **控制什麼：** `import target`指定AWS Snow Family讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `cluster/edge compute`

- **控制什麼：** `cluster/edge compute`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。
- **何時需要：** Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。
- **怎麼設定／驗證：** 維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。
- **常見錯法：** 過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。

#### `chain of custody`

- **控制什麼：** `chain of custody`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。
- **何時需要：** Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。
- **怎麼設定／驗證：** 維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。
- **常見錯法：** 過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。

## 讀到這裡，請用自己的話說一次

1. AWS DataSync的責任：以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨storage。
2. 底層機制：Agent平行讀寫、加密傳輸、驗證完整性並依task schedule執行。
3. 第一個要看的設定：source/destination location、agent、include/exclude filters、bandwidth、verification、schedule與task report。
4. 選擇邏輯：DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。
5. 不要混淆：AWS Storage Gateway的責任是「在on-premises提供file/volume/tape介面，後端整合AWS storage。」；它不會自動取代AWS DataSync。
6. 替換訊號：離線大規模且bandwidth不足用Snow；提供持續hybrid storage介面用Storage Gateway。
7. 最常見錯法：只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。
8. 可移植原則：migration throughput is bytes plus change rate plus verification。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS DataSync | 以managed agent高效在線搬移NFS/SMB/object data到AWS storage或跨storage。 | Agent平行讀寫、加密傳輸、驗證完整性並依task schedule執行。 | 持續或一次性online file/object migration、metadata保留與驗證。 | 離線大規模且bandwidth不足用Snow；提供持續hybrid storage介面用Storage Gateway。 |
| AWS Storage Gateway | 在on-premises提供file/volume/tape介面，後端整合AWS storage。 | Virtual/hardware appliance維持local cache並把資料非同步寫入S3/EBS snapshots/virtual tape。 | legacy apps需維持local protocol、hybrid cache、backup/tape modernization。 | 只要快速搬完資料用DataSync；它不是一般跨Region filesystem。 |
| AWS Transfer Family | 以managed SFTP/FTPS/FTP/AS2 endpoints把partner files存入S3/EFS。 | Service終止protocol與authentication，將user映射到IAM role和logical directory。 | 合作夥伴必須保留傳統file-transfer protocol而後端想用AWS storage。 | 內部bulk migration用DataSync；不要為SFTP自行長期維護EC2 servers。 |
| AWS Snow Family | 以實體devices進行離線large-scale data transfer或edge compute。 | AWS寄送加密device；客戶copy後寄回，AWS匯入指定storage。 | 網路頻寬無法在migration window內搬完PB級資料。 | 持續同步或可用足夠線路時DataSync/DX更合適；必須先確認所在Region與服務供應狀態。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | DMS適合資料庫持續複寫，不應代替一般檔案搬移。 | 只有當題目條件明確改變時才可能合理。 | 只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「DMS適合資料庫持續複寫，不應代替一般檔案搬移。」之間做選擇。
- 認得常考設定：source/destination location、agent、include/exclude filters、bandwidth、verification、schedule與task report。
- 對應官方tasks：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.1 Design cost-optimized storage solutions；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：離線大規模且bandwidth不足用Snow；提供持續hybrid storage介面用Storage Gateway。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.2 Determine the optimal migration approach for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAA｜DataSync 工作負載與 task controls

公司要把on-premises NFS上的120 TB工程資料遷到EFS。遷移期間來源每天仍會變更，要求每晚增量傳輸、保留支援的timestamps與ownership、排除scratch目錄、限制白天頻寬並產出verification report。哪個服務最合適？

A. S3 File Gateway，因它是針對任何NFS來源的一次性bulk migration與逐檔verification engine
B. AWS DataSync；在on-prem部署agent，建立NFS與EFS locations及scheduled task，設定filters、bandwidth、metadata、verification與reports
C. AWS DMS，因database change data capture可原生保留任意NFS ACL與extended attributes
D. S3 Transfer Acceleration，因它會自動crawl NFS filesystem並把files掛載成EFS

**答案：B**

- **A：** 不正確。File Gateway持續提供hybrid NFS/SMB介面並把files映射到S3，不是此NFS到EFS migration task的主要增量搬移工具。
- **B：** 正確。DataSync針對file/object transfer，task可重複執行並提供filter、排程、bandwidth、metadata與verification控制。
- **C：** 不正確。DMS服務database schema/data與CDC，不是一般filesystem crawler或NFS metadata migration工具。
- **D：** 不正確。Transfer Acceleration加速S3 object transfer endpoint，不會發現NFS樹、保留file metadata或直接寫EFS。

**事實查證：** [What is AWS DataSync? - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)、[Configuring how to handle files, objects, and metadata - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/configure-metadata.html)、[Monitoring your data transfers with task reports - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/task-reports.html)

### 練習題 2｜SAP｜DataSync security 與 agent requirement

安全團隊要用DataSync把Account A中SSE-KMS加密的S3 objects搬到Account B的EFS，兩端都在AWS。資料路徑需留在核准網路範圍，且只授予指定prefix與filesystem寫入權。哪個設計最完整？

A. 只建立DataSync task；service-linked role會自動繞過兩個accounts的bucket、KMS與EFS policies
B. 一定要在on-premises安裝agent；所有AWS-to-AWS transfers即使來源與目的都是managed storage也不能由DataSync service執行
C. 只給source S3 read permission；DataSync會從來源權限推導destination EFS write與KMS decrypt權限
D. 依locations確認此AWS-to-AWS path是否可由service直接執行，分別配置S3 role/bucket與KMS key policies、EFS access/network permissions及所需VPC endpoint或ENI路徑

**答案：D**

- **A：** 不正確。DataSync不會繞過IAM、resource policy或KMS key policy；每個account與encryption boundary都要顯式授權。
- **B：** 不正確。Agent需求取決於location類型；多種AWS storage間transfer可不部署self-managed agent，跨account本身不等於必須on-prem agent。
- **C：** 不正確。Source read、destination write與KMS decrypt/encrypt是獨立permissions，不能由一側自動推導另一側。
- **D：** 正確。先依location判定agent，再以least privilege處理兩個accounts、KMS與EFS；private connectivity還需符合DataSync control/data plane與VPC networking要求。

**事實查證：** [Do I need an AWS DataSync agent? - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/do-i-need-datasync-agent.html)、[Security in AWS DataSync - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/security.html)、[AWS DataSync network requirements - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)

### 練習題 3｜SAP｜Bandwidth、change rate 與 cutover

資料中心有500 TB NAS、每日新增與修改8 TB，對AWS是10 Gbps連線。業務要求判斷能否在週末4小時freeze window完成cutover。哪個計畫能產生可信答案並降低停機？

A. 先以代表性目錄試跑取得effective throughput與small-file/metadata/retry成本，完成initial bulk copy後做多輪incremental sync；freeze writes後跑final delta並驗證再切換
B. 直接用500 TB除以10 Gbps；line rate就是端到端保證，不必考慮每日change rate
C. 只執行一次initial copy；完成後到cutover期間的8 TB/day變更由DNS切換自動補齊
D. 關閉所有verification與task reports；資料正確性不影響稽核或rollback，因此完成日期必然可信

**答案：A**

- **A：** 正確。Pilot量到protocol與資料形態下的實際速度；bulk加多輪delta把freeze期間剩餘量降到可估算範圍，最後驗證支持cutover與rollback。
- **B：** 不正確。10 Gbps只是理論line rate；small files、metadata、加密、retries、端點能力與change rate都會降低有效進度。
- **C：** 不正確。Initial copy後來源仍持續變更；沒有incremental與final delta會造成遺漏或版本不一致。
- **D：** 不正確。Verification有時間與成本取捨，但完全不驗證會失去資料完整性證據，也讓錯誤直到切換後才被發現。

**事實查證：** [Starting a task to transfer your data - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/run-task.html)、[Choosing a task mode for your data transfer - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/choosing-task-mode.html)、[Configuring how AWS DataSync verifies data integrity - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/configure-data-verification-options.html)

### 練習題 4｜SAA → SAP｜S3 File Gateway hybrid cache semantics

工廠內的legacy應用未來兩年仍只能使用NFS。公司希望files以S3 objects長期保存，現場保留熱門資料cache並能離線容忍短暫WAN波動。另一個AWS workload偶爾也會直接修改同一bucket。哪個設計與注意事項正確？

A. 使用File Gateway即可取得跨站點完整POSIX distributed locking；直接改S3 objects會立即與所有open file handles強一致
B. 使用Volume Gateway，因它提供NFS/SMB namespace並把每個file存成EBS snapshot
C. 使用S3 File Gateway提供NFS share與local cache，files映射成S3 objects；對直接S3修改需規劃cache refresh與coherency，避免雙邊未協調寫入
D. 使用Tape Gateway，因VTL可直接掛載成一般NFS目錄供互動式file editing

**答案：C**

- **A：** 不正確。File Gateway不是全球cluster filesystem；direct S3與file-share access混用時有refresh與coherency考量。
- **B：** 不正確。Volume Gateway呈現iSCSI block volumes，不提供NFS/SMB file namespace；snapshots是volume backup機制。
- **C：** 正確。File Gateway維持legacy file protocol與local cache，durable資料成為S3 objects；直接object updates需依文件設計refresh與writer ownership。
- **D：** 不正確。Tape Gateway呈現給backup software的iSCSI virtual tape library，不是互動式NFS file service。

**事實查證：** [What is Amazon S3 File Gateway - AWS Storage Gateway](https://docs.aws.amazon.com/filegateway/latest/files3/what-is-file-s3.html)、[Refreshing Amazon S3 bucket object cache - AWS Storage Gateway](https://docs.aws.amazon.com/filegateway/latest/files3/refresh-cache.html)

### 練習題 5｜SAP｜Volume Gateway cached 與 stored volumes

兩套legacy applications都只能連iSCSI。Site A只有2 TB local cache，但dataset有80 TB，接受primary data在AWS；Site B有足夠local storage且低延遲運作不能依賴WAN，僅希望把point-in-time backups送到AWS。哪個mapping正確？

A. A用stored volumes、B用cached volumes；stored會把80 TB primary只放AWS，cached會保留完整B dataset在local
B. A用cached volumes、B用stored volumes，並為兩者設計application-consistent snapshot/backup程序
C. 兩者都用File Gateway，因NFS share與iSCSI block volume完全相同
D. 兩者都用Tape Gateway，因virtual tapes可作為低延遲database primary block devices

**答案：B**

- **A：** 不正確。語意相反：cached volumes把primary放AWS並只cache熱門blocks；stored volumes保留完整primary dataset在local。
- **B：** 正確。A的容量限制符合cached model，B的本地完整primary需求符合stored model；crash/application consistency仍需由應用與snapshot流程協調。
- **C：** 不正確。File Gateway提供NFS/SMB file interface，不滿足只能使用iSCSI block的legacy applications。
- **D：** 不正確。Tape Gateway服務sequential backup VTL workflow，不適合作為transactional application的primary online disk。

**事實查證：** [What is Volume Gateway? - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/vgw/WhatIsStorageGateway.html)、[How Volume Gateway works - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/vgw/StorageGatewayConcepts.html)、[How Volume Gateway works - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/vgw/StorageGatewayConcepts.html)

### 練習題 6｜SAA → SAP｜Tape Gateway 與 virtual tape lifecycle

企業backup software目前寫入實體VTL並維護media catalog。公司要保留既有backup jobs與tape語意，但把長期媒體移到AWS archive，還要求KMS加密與年度restore test。哪個方案正確？

A. 使用Tape Gateway作為interactive database iSCSI disk；virtual tape可由EC2直接attach成EBS volume
B. 啟用Tape Gateway後刪除backup software catalog；AWS會從任意archive自動重建所有retention與media relationships
C. 使用File Gateway並把每個backup file標成public-read；這等同VTL eject與archive
D. 部署Tape Gateway提供iSCSI VTL，讓backup application建立與eject virtual tapes到archive，並保留catalog、KMS、retention及restore runbook

**答案：D**

- **A：** 不正確。Tape Gateway模擬tape devices給backup software，archived tapes不能當一般低延遲EBS block volume使用。
- **B：** 不正確。Backup catalog仍負責可恢復集合、retention與media追蹤；gateway不會替應用重建所有邏輯。
- **C：** 不正確。File Gateway是NFS/SMB到S3 object interface，沒有VTL drive、media changer與eject lifecycle，公開資料也違反安全要求。
- **D：** 正確。Tape Gateway保留既有VTL workflow；eject後的virtual tapes進入archive，組織仍需管理catalog、encryption、retention、retrieval時間與restore測試。

**事實查證：** [What is Tape Gateway? - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/tgw/WhatIsStorageGateway.html)、[Retrieving Archived Tapes - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/tgw/retrieving-archived-tapes-vtl.html)

### 練習題 7｜SAA → SAP｜Transfer Family protocol、identity 與 backend

200家外部partners必須繼續使用SFTP上傳檔案。Backend是私有S3 bucket；每個partner只能看到`partners/<id>/`，部分objects用customer managed KMS key。公司不想維護SFTP servers。哪個設計最合適？

A. 部署AWS Transfer Family managed SFTP endpoint，使用service-managed或custom identity provider，設定logical home directory與per-user role，並授予對應S3 prefix及KMS權限
B. 把S3 bucket設public；HTTPS object access會自動向partners呈現完整SFTP protocol與chroot
C. 建立DataSync task；DataSync agent會提供partners可互動登入的長期SFTP server與password管理
D. 只建立Transfer Family users，不配置backend IAM role；protocol authentication成功會自動授予整個AWS account權限

**答案：A**

- **A：** 正確。Transfer Family管理protocol endpoint，但identity、logical directory、S3 role/policy與KMS authorization仍需明確限制到每個partner。
- **B：** 不正確。Public S3不提供SFTP wire protocol、使用者home mapping或least-privilege partner identity，且擴大資料暴露。
- **C：** 不正確。DataSync執行受控transfer tasks，不是供外部partners持續登入的managed SFTP service。
- **D：** 不正確。Frontend authentication不取代backend authorization；Transfer role與S3/KMS policies決定實際可讀寫範圍。

**事實查證：** [What is AWS Transfer Family? - AWS Transfer Family](https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer-family.html)、[Using logical directories to simplify your Transfer Family directory structures - AWS Transfer Family](https://docs.aws.amazon.com/transfer/latest/userguide/logical-dir-mappings.html)、[Create an IAM role and policy - AWS Transfer Family](https://docs.aws.amazon.com/transfer/latest/userguide/requirements-roles.html)

### 練習題 8｜SAP｜Snow Family offline migration

一家AWS帳戶仍具Snowball Edge使用eligibility、且可成功建立device order的既有客戶，要搬移3 PB不可變影像。現有網路估計需數月，兩端都有受控收送區與chain-of-custody程序；寄出後來源仍會每天新增資料。選擇兩項必要做法。

A. 把Snowball Edge當永久NAS留在資料中心；job完成後不需依期限歸還device
B. device顯示copy完成後立即刪除source；不必等待AWS import、inventory或checksum結果
C. 規劃多個Snowball Edge import jobs，使用各job的encryption、manifest與unlock code，並記錄device交接與shipping狀態
D. 假設device寄出後新增的資料會透過Snow job自動同步，不需任何online delta plan
E. AWS import完成後比對inventory/checksums並保留source直到驗證；另用DataSync或網路transfer處理seed後的增量

**答案：C、E**

- **A：** 不正確。Snowball Edge import是有job與歸還期限的離線transfer流程，不是無限期代管的primary NAS。Snowball Edge已不再提供給新客戶；本題明確假設既有客戶的帳戶仍具eligibility，而且能成功建立device order。
- **B：** 不正確。Local copy成功只證明資料寫到device；仍要確認運送、AWS import與目的端完整性後才能依治理程序刪source。
- **C：** 正確。PB級資料通常需多個jobs；manifest/unlock code、加密與實體交接記錄共同保護device與chain of custody。這個方案只在題目所述的帳戶eligibility成立、且實際device order可成功建立時適用；新客戶應評估AWS列出的替代方案。
- **D：** 不正確。離線device是某一時間點的seed，不會取得寄出後的source changes；缺少delta plan會造成cutover資料缺口。
- **E：** 正確。Inventory/checksum驗證提供可稽核完成證據，而online增量同步把長途物流期間的changes帶到目的地。

**事實查證：** [What is Snowball Edge? - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/whatisedge.html)、[AWS Snowball Edge availability change - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/snowball-edge-availability-change.html)、[Creating a job to order a Snowball Edge device - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/create-job-common.html)、[Security for AWS Snowball Edge - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/security.html)

### 練習題 9｜SAP｜Hybrid migration service combination

媒體公司有3 PB歷史影像、每天新增20 TB，預定六週後切到S3。切換後外部製作partners仍要使用SFTP且只能看到各自目錄。該公司是帳戶仍具Snowball Edge使用eligibility、且可成功建立device order的既有客戶；網路足以傳每日delta，但不足以在六週搬完歷史資料。選擇兩項正確架構步驟。

A. 只用Transfer Family搬完整3 PB；SFTP endpoint會忽略網路吞吐限制並保證六週完成
B. 用Snowball Edge jobs做initial seed，同時規劃DataSync或受控online copies反覆傳delta，最後freeze、final sync並核對inventory/checksums
C. 只用Snowball Edge；device寄出後會永久追蹤每天20 TB changes並在AWS自動套用
D. 切換後用Transfer Family managed SFTP，以identity mapping、per-user roles與logical directories限制每個partner的S3 prefix
E. 只部署File Gateway；它會自動匯入全部歷史資料並向Internet partners提供managed SFTP identity service

**答案：B、D**

- **A：** 不正確。Transfer Family提供protocol endpoint，不消除3 PB經現有network傳輸所需時間；題目已說明頻寬不足。若是新客戶，也不能假設能新訂Snowball Edge，必須重新估算DataSync、Direct Connect、網路傳輸或AWS認可partner等可用路徑。
- **B：** 正確。Offline seed解決歷史bulk，online repeated deltas與final freeze處理物流期間變更；inventory/checksum讓cutover可驗證。Snowball Edge已不再提供給新客戶；這個答案只適用於題目明確指定帳戶eligibility成立、且device order可成功建立的既有客戶。
- **C：** 不正確。Snow device只包含copy時的資料，不是持續CDC或永久同步channel。
- **D：** 正確。Transfer Family承接partner-facing SFTP，而backend IAM/KMS與logical directory mapping維持每個partner的隔離。
- **E：** 不正確。File Gateway提供hybrid NFS/SMB access，不是外部managed SFTP service，也不會在沒有migration plan下保證3 PB期限。

**事實查證：** [What is Snowball Edge? - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/whatisedge.html)、[AWS Snowball Edge availability change - AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/snowball-edge-availability-change.html)、[What is AWS DataSync? - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)、[What is AWS Transfer Family? - AWS Transfer Family](https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer-family.html)

### 練習題 10｜SAA → SAP｜DataSync、DMS、Direct Connect 與 Storage Gateway 邊界

架構委員會同時審查四項需求：一次性遷移NFS files並保留支援metadata；讓Oracle資料庫在cutover前持續CDC到AWS；建立固定private network circuit；以及讓legacy sites長期保留NFS/iSCSI/VTL介面而資料延伸到AWS。選擇兩項正確的服務邊界說明。

A. DataSync適合file/object movement；Direct Connect提供network connectivity與穩定路徑，但不會自行發現或複寫NAS files
B. Direct Connect會自動把所有通過circuit的storage blocks複寫到S3，不需migration service
C. DMS是通用POSIX file copier，可保留任意ACL、xattrs與directory locks
D. Storage Gateway只是一條dedicated network circuit，不提供file、volume或tape storage interfaces
E. DMS適合database migration/ongoing replication；Storage Gateway適合持續hybrid file、block或virtual tape protocol需求

**答案：A、E**

- **A：** 正確。DataSync理解受支援storage locations與metadata；Direct Connect只提供連線，仍需DataSync、應用或其他工具搬資料。
- **B：** 不正確。Direct Connect是network service，不解析filesystem或建立S3 objects，也沒有自動storage replication語意。
- **C：** 不正確。DMS操作database engines、tables與change records，不是NFS/SMB filesystem metadata migration工具。
- **D：** 不正確。Storage Gateway提供File、Volume與Tape等hybrid storage interfaces；dedicated circuit是Direct Connect的角色。
- **E：** 正確。先以state與protocol分類：DMS處理database與CDC，Storage Gateway則讓既有storage clients持續使用熟悉介面並連到AWS。

**事實查證：** [What is AWS DataSync? - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)、[What is AWS Database Migration Service? - AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[What is Direct Connect? - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html)、[What is AWS Storage Gateway? - AWS Storage Gateway](https://docs.aws.amazon.com/storagegateway/latest/userguide/WhatIsStorageGateway.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「DataSync做高效online transfer；Storage Gateway提供hybrid介面；…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「資料搬移受網路頻寬、停機窗口、protocol、持續同步與實體運送限制。」，所以「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」能直接滿足它；若constraint改成「DMS適合資料庫持續複寫，不應代替一般檔案搬移。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」。替代方案「DMS適合資料庫持續複寫，不應代替一般檔案搬移。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「資料搬移受網路頻寬、停機窗口、protocol、持續同步與實體運送限制。」，排除會導致「只用理論頻寬估算PB傳輸，忽略小檔metadata、變更率、驗證與cutover。」的選項，再選「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」。本章對應的代表task包括：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.1 Design cost-optimized storage solutions；SAA-4.4 Design cost-optimized network architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「DataSync做高效online transfer；Storage Gateway提供hybrid介面；Transfer Family接SFTP；Snow處理離線大量資料。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「migration throughput is bytes plus change rate plus verification」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 45 章　RDS Multi-AZ、Read Replica 與 RDS Proxy

關聯式資料庫的HA、read scaling與connection management是三個不同問題。

## 跟著一筆資料走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：交易主庫需自動failover，報表流量不能影響寫入，Lambda尖峰達數千併發。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：關聯式資料庫的HA、read scaling與connection management是三個不同問題。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：關聯式資料庫像一本正式帳簿：交易要讓多個欄位一起成立，讀副本則像提供影本給查詢者使用。 但請同時記住它的邊界：副本可能有延遲，failover也涉及client重新連線；不能把影本當成永遠同步的主帳簿。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon RDS，對照角色是RDS Multi-AZ。我們選擇「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：交易主庫需自動failover，報表流量不能影響寫入，Lambda尖峰達數千併發。

Application write
      └─ RDS writer ── synchronous standby in another AZ
                         └─ 故障時自動failover；不拿來分擔一般讀取

Reporting reads
      └─ Read replica（可能有replication lag）

大量短生命Lambda connections
      └─ RDS Proxy ── connection pool ──> writer / database

Multi-AZ、read replica與proxy分別解決可用性、讀取擴展與連線管理。

失敗時先找：把read replica當零RPO HA，或Lambda直接建立大量DB connections。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon RDS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon RDS和RDS Multi-AZ並不是兩個任意的產品名稱。前者適合本章，是因為「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」直接回應了眼前的問題；後者描述的「Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把read replica當零RPO HA，或Lambda直接建立大量DB connections。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate availability replicas from read-scaling replicas」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 |
| RDS Multi-AZ | 讓RDS在AZ故障時自動failover以提高availability。 | 傳統deployment同步複寫到standby；同一DNS endpoint在failover後指向新primary。 |
| RDS read replicas | 以非同步replica增加read capacity，並可支援跨Region read/DR。 | Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。 |
| Amazon RDS Proxy | 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。 | Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。 |

## 把全圖套進一個具體案例

**場景：** 交易主庫需自動failover，報表流量不能影響寫入，Lambda尖峰達數千併發。

1. 故事的起點：交易主庫需自動failover，報表流量不能影響寫入，Lambda尖峰達數千併發。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon RDS負責「代管關聯式database engine的provisioning、patch、backup與failover。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：RDS Multi-AZ、RDS read replicas、Amazon RDS Proxy各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把read replica當零RPO HA，或Lambda直接建立大量DB connections。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon RDS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：關聯式資料庫的HA、read scaling與connection management是三個不同問題。
- **具體例子／邊界：** 在「交易主庫需自動failover，報表流量不能影響寫入，Lambda尖峰達數千併發。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### RDS Multi-AZ

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把read replica當零RPO HA，或Lambda直接建立大量DB connections。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate availability replicas from read-scaling replicas。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon RDS

- **功用：** 代管關聯式database engine的provisioning、patch、backup與failover。
- **底層機制：** DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
- **關鍵設定：** engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- **選擇時機：** 需要SQL transaction、joins、schema與managed operations。
- **替換時機：** 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。

### RDS Multi-AZ

- **功用：** 讓RDS在AZ故障時自動failover以提高availability。
- **底層機制：** 傳統deployment同步複寫到standby；同一DNS endpoint在failover後指向新primary。
- **關鍵設定：** Multi-AZ deployment/cluster、failover testing、maintenance、DNS TTL與application reconnect。
- **選擇時機：** production database需要HA、patch期間較小中斷與AZ resilience。
- **替換時機：** 它不是read scaling；讀取容量用read replica/Aurora replicas。

### RDS read replicas

- **功用：** 以非同步replica增加read capacity，並可支援跨Region read/DR。
- **底層機制：** Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。
- **關鍵設定：** replica count/class/Region、public accessibility、promotion、backup與replica lag alarms。
- **選擇時機：** read-heavy報表、全球read或可接受非同步RPO的DR。
- **替換時機：** 需要自動同步HA選Multi-AZ；不能把lagging replica當authoritative read。

### Amazon RDS Proxy

- **功用：** 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。
- **底層機制：** Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。
- **關鍵設定：** target group、Secrets Manager auth、IAM auth、max connections、idle timeout、subnets與SG。
- **選擇時機：** Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。
- **替換時機：** 它不cache query也不增加DB compute；讀壓力需replica/cache或schema/index改善。

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

### RDS Multi-AZ：逐項設定說明

#### `Multi-AZ deployment/cluster`

- **控制什麼：** `Multi-AZ deployment/cluster`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署RDS Multi-AZ前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `failover testing`

- **控制什麼：** `failover testing`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「production database需要HA、patch期間較小中斷與AZ resilience。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在RDS Multi-AZ設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `maintenance`

- **控制什麼：** `maintenance`定義哪些patch被核准、哪些fleet套用、何時只掃描或實際安裝，以及如何回報compliance。
- **何時需要：** EC2/on-prem managed nodes需要可分波、可稽核的OS patch流程時。
- **怎麼設定／驗證：** 建立baseline與approval delay，將instances標記到patch group，透過maintenance window先Scan再小批Install，監控reboot與rollback。
- **常見錯法：** 直接全fleet Install可能造成同時reboot；compliant只表示符合baseline，不代表application已通過功能與容量測試。

#### `DNS TTL`

- **控制什麼：** `DNS TTL`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「production database需要HA、patch期間較小中斷與AZ resilience。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在RDS Multi-AZ的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

#### `application reconnect`

- **控制什麼：** `application reconnect`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

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

## 可以直接對照 AWS 的設定範例

### RDS PostgreSQL：Multi-AZ、backup 與保護刪除

```yaml
Resources:
  OrdersDb:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: postgres
      DBInstanceClass: db.r7g.large
      AllocatedStorage: 100
      StorageType: gp3
      MultiAZ: true
      BackupRetentionPeriod: 14
      StorageEncrypted: true
      KmsKeyId: !Ref DatabaseKey
      DeletionProtection: true
      PubliclyAccessible: false
      DBSubnetGroupName: !Ref DbSubnetGroup
      VPCSecurityGroups: [!Ref DbSecurityGroup]

```

1. MultiAZ解決availability，不提供application read scaling。
2. DeletionPolicy與UpdateReplacePolicy保護IaC刪除/替換；DeletionProtection防API誤刪。
3. Backup retention支援point-in-time recovery，但仍須實際restore並量測RTO。

## 讀到這裡，請用自己的話說一次

1. Amazon RDS的責任：代管關聯式database engine的provisioning、patch、backup與failover。
2. 底層機制：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
3. 第一個要看的設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
4. 選擇邏輯：Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。
5. 不要混淆：RDS Multi-AZ的責任是「讓RDS在AZ故障時自動failover以提高availability。」；它不會自動取代Amazon RDS。
6. 替換訊號：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
7. 最常見錯法：把read replica當零RPO HA，或Lambda直接建立大量DB connections。
8. 可移植原則：separate availability replicas from read-scaling replicas。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 | 需要SQL transaction、joins、schema與managed operations。 | 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。 |
| RDS Multi-AZ | 讓RDS在AZ故障時自動failover以提高availability。 | 傳統deployment同步複寫到standby；同一DNS endpoint在failover後指向新primary。 | production database需要HA、patch期間較小中斷與AZ resilience。 | 它不是read scaling；讀取容量用read replica/Aurora replicas。 |
| RDS read replicas | 以非同步replica增加read capacity，並可支援跨Region read/DR。 | Primary log changes非同步傳到replica；application必須使用獨立read endpoint並接受lag。 | read-heavy報表、全球read或可接受非同步RPO的DR。 | 需要自動同步HA選Multi-AZ；不能把lagging replica當authoritative read。 |
| Amazon RDS Proxy | 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。 | Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。 | Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。 | 它不cache query也不增加DB compute；讀壓力需replica/cache或schema/index改善。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。 | 只有當題目條件明確改變時才可能合理。 | 把read replica當零RPO HA，或Lambda直接建立大量DB connections。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。」之間做選擇。
- 認得常考設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Multi-AZ DB instance 與 read scaling

訂單系統使用一個傳統 RDS PostgreSQL Multi-AZ DB instance deployment。主要需求是 writer 所在 AZ 故障時自動切換；月底 reporting query 會吃滿 CPU，但可以接受數秒資料延遲。哪個調整最符合需求？

A. 保留 Multi-AZ deployment提供同步 standby與自動 failover，另建 read replica承接 reporting reads
B. 把 reporting連到 Multi-AZ standby的 read endpoint，因 standby本來就供唯讀查詢
C. 改成 Single-AZ並提高 instance class；較大的 instance會自動提供另一AZ的 failover
D. 把 standby的 private IP寫入 reporting config，failover時由應用直接提升該IP

**答案：A**

- **A：** 正確。傳統 Multi-AZ DB instance的同步 standby用於高可用且不可服務應用讀取；可容忍短暫延遲的報表應由另建的read replica隔離。
- **B：** 不正確。此deployment類型沒有供應用查詢standby的read endpoint；若需要可讀standbys，必須選不同拓撲或另建read replica。
- **C：** 不正確。提高單一instance容量可能緩解CPU，但不建立跨AZ standby，也無法滿足AZ failure自動恢復。
- **D：** 不正確。RDS以DNS endpoint完成角色切換；standby不是客戶可直接管理或以固定IP提升的instance。

**事實查證：** [Configuring and managing a Multi-AZ deployment for Amazon RDS - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)、[Working with DB instance read replicas - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 練習題 2｜SAA → SAP｜Multi-AZ DB cluster 可讀 instances

一個已確認受支援engine與Region的RDS workload需要一個writer，以及分布在三個AZ中的兩個可讀instances。讀流量必須分散，writer故障時也要由其中一個reader快速接手。應選哪個deployment？

A. 傳統Multi-AZ DB instance，因其單一standby可提供兩個read endpoints
B. RDS Multi-AZ DB cluster，使用一個writer與兩個readable DB instances
C. 跨Region read replica，因它在三個本地AZ內進行同步commit
D. Single-AZ DB instance加兩個manual snapshots，因snapshot可直接接收SQL reads

**答案：B**

- **A：** 不正確。傳統Multi-AZ DB instance通常是一個primary加一個不可讀standby，不符合兩個本地readable instances的要求。
- **B：** 正確。對受支援的engine、version與Region，Multi-AZ DB cluster提供一個writer與兩個可讀instances，兼顧read capacity與跨AZ failover。
- **C：** 不正確。Cross-Region replica處理另一Region的讀取或DR，通常非同步，並不等同題目的三AZ本地cluster。
- **D：** 不正確。Snapshot是恢復點，不是可連線的running database，也不能提供自動writer failover。

**事實查證：** [Multi-AZ DB cluster deployments for Amazon RDS - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)

### 練習題 3｜SAA｜Read replica lag 與讀一致性

電商把RDS primary的讀流量移到read replica後，商品報表正常，但checkout剛寫入shipping address便立刻從replica讀取，偶爾看到舊值。哪個修正最合理？

A. 宣告read replica與primary同步commit，因此問題只可能是DNS cache
B. 繼續把所有reads送replica；提高replica instance class即可保證零lag
C. 讓需要read-after-write的checkout流程讀primary，報表繼續讀replica，並監控replication lag
D. 刪除primary並直接寫入read replica；read replica會自動維持唯讀與可寫雙角色

**答案：C**

- **A：** 不正確。一般RDS read replica使用非同步複寫，primary成功commit後replica仍可能短暫落後。
- **B：** 不正確。較大容量可降低資源造成的lag，但非同步拓撲本身不承諾每次讀都立即看到最新commit。
- **C：** 正確。需要強read-after-write語意的路徑應讀writer；可容忍stale的報表適合replica，且lag必須納入監控與路由決策。
- **D：** 不正確。Replica promotion會使其成為獨立DB並中止原複寫關係，不是同時維持自動雙角色的讀寫端點。

**事實查證：** [Working with DB instance read replicas - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 練習題 4｜SAP｜Cross-Region replica promotion 與 DR

公司在另一Region建立RDS cross-Region read replica。演練假設primary Region完全不可用，業務接受最多30秒資料損失與20分鐘恢復時間。哪個runbook最完整？

A. 只建立replica即可；RDS會在Region failure時同步、零資料損失地自動改寫所有application endpoints
B. 提升replica後，原primary恢復時會自動成為新primary的同步replica，不需failback設計
C. 在兩個Regions使用同一固定private IP；promotion不會改變writer ownership或connection資訊
D. 監控lag並在事件中評估RPO，promote replica成獨立DB，切換DNS/secrets與write ownership、驗證資料，再以明確流程重建replication與failback

**答案：D**

- **A：** 不正確。Cross-Region read replication是非同步且promotion通常需要操作；僅建立replica不會完成應用切換或保證零RPO。
- **B：** 不正確。Promotion會中斷原read-replica關係；舊primary恢復後的資料對帳與反向複寫必須由runbook處理。
- **C：** 不正確。跨Region資料庫不共享固定private IP；clients需改用新writer的可解析endpoint或受控DNS抽象。
- **D：** 正確。此流程把replication lag、promotion、client設定、單一writer與failback都納入，才能用演練證明30秒RPO與20分鐘RTO。

**事實查證：** [Creating a read replica in a different AWS Region - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.XRgn.html)

### 練習題 5｜SAA｜RDS Proxy 與 Lambda connection storm

API Gateway後方的Lambda平時每秒100個requests，促銷時突增到5,000。每次invocation都新建RDS連線，database CPU仍有餘裕，但`max_connections`先耗盡。哪個變更最直接？

A. 在Lambda與RDS間加入RDS Proxy以pool/reuse database connections，並設定Secrets Manager或IAM authentication與合適timeouts
B. 提高Lambda reserved concurrency到更高值；更多同時invocations會降低database connection數
C. 建立read replica；它會自動pool所有送往writer的transaction connections
D. 使用RDS Proxy取代transaction與index設計；Proxy會重寫慢SQL並增加database CPU

**答案：A**

- **A：** 正確。RDS Proxy把大量短命client connections多工到較少的database connections，可降低burst對`max_connections`與連線建立成本的壓力。
- **B：** 不正確。提高concurrency通常會增加同時連線需求；只有先按database可承受量做backpressure才可能保護後端。
- **C：** 不正確。Read replica提供讀取容量，但不會替writer transactions做connection pooling。
- **D：** 不正確。Proxy管理連線與故障期間的連線行為，不會修復慢SQL、索引缺失或CPU容量不足。

**事實查證：** [Amazon RDS Proxy - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html)

### 練習題 6｜SAP｜RDS Proxy pinning 與 multiplexing

導入RDS Proxy後，client connections增加十倍，但database connections幾乎一對一增加。監控顯示大量session pinning；程式常送session-level `SET`，也會產生超過16 KB的SQL statements。最合理的處理是？

A. 假設Proxy會自動重寫SQL並消除session state，因此只需忽略pinning metric
B. 檢查pinning logs/metrics，移除不必要的session state或過大statements，並讓transactions盡快結束以恢復可multiplex連線
C. 把Proxy idle timeout設成最大值；連線保持越久即可保證永不pin
D. 把read replica升級；replica lag降低後writer上的session pinning會自動消失

**答案：B**

- **A：** 不正確。Proxy不會任意改寫application SQL；會改變session狀態或過大的statement可能使client固定使用同一database connection。
- **B：** 正確。Pinning限制connection reuse；找出觸發行為、減少跨transaction session依賴並縮短transaction範圍，才能恢復pooling收益。
- **C：** 不正確。Idle timeout控制閒置連線生命週期，不會移除造成pinning的session語意。
- **D：** 不正確。Read-replica容量與writer Proxy的session multiplexing是不同問題；replication lag不是pinning原因。

**事實查證：** [Avoiding pinning an RDS Proxy - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-pinning.html)、[RDS Proxy connection considerations - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-connections.html)

### 練習題 7｜SAA → SAP｜Automated backup、PITR 與 manual snapshot

財務人員在10:45誤刪資料，團隊要恢復到10:30；此外每月結帳點必須保存七年，遠長於automated backup retention。哪個方案正確？

A. 查詢Multi-AZ standby的10:30歷史狀態；standby會保存任意時間點
B. 執行PITR原地覆寫目前production DB，既有clients與transactions會無縫續用
C. 在retention window內以automated backups與transaction logs還原到新DB，再驗證並切換；月末另保留manual snapshots直到治理流程刪除
D. 只依賴automated backups；retention到期後AWS仍會永久保留所有月末restore points

**答案：C**

- **A：** 不正確。Multi-AZ standby是目前狀態的HA副本，不是可查詢任意歷史時間的時間旅行資料庫。
- **B：** 不正確。RDS PITR會建立新的DB instance；application驗證、資料差異處理與connection cutover仍需規劃。
- **C：** 正確。Automated backups支援保留期間內PITR，而manual snapshot可保留到明確刪除，分別滿足誤刪恢復與七年保留。
- **D：** 不正確。Automated retention到期後舊restore points會依服務規則移除，不能代替長期manual snapshot或集中backup政策。

**事實查證：** [Introduction to backups - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)、[Creating a DB snapshot for a Single-AZ DB instance for Amazon RDS - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateSnapshot.html)

### 練習題 8｜SAP｜RDS encryption 與 snapshot copy

一個未加密RDS DB instance必須遷移成encrypted replacement，之後把encrypted snapshot提供給另一帳號並複製到另一Region。選擇兩項必要做法。

A. 修改DB parameter group開啟storage encryption；既有blocks會在原instance原地加密
B. 以AWS managed KMS key加密snapshot後直接分享給任意帳號，不需key policy
C. 只強制TLS；傳輸加密會回溯加密既有storage、snapshots與backups
D. 建立snapshot並在copy時選customer managed KMS key，再從encrypted copy還原新的DB instance
E. 跨帳號與Region流程使用可分享的manual snapshot及customer managed key授權，讓目標帳號按支援流程copy並以其KMS key管理副本

**答案：D、E**

- **A：** 不正確。既有未加密RDS instance不能靠parameter原地切成encrypted；需要snapshot copy與restore等replacement流程。
- **B：** 不正確。以AWS managed key加密的RDS snapshot不能像customer managed key那樣任意跨帳號分享，且KMS authorization不能省略。
- **C：** 不正確。TLS只保護傳輸，不會改變既有storage或snapshot的at-rest encryption狀態。
- **D：** 正確。將未加密snapshot複製為使用customer managed key的encrypted snapshot，再restore新DB，是建立encrypted replacement的標準路徑。
- **E：** 正確。跨帳號encrypted snapshot需要manual snapshot與KMS key policy/grant等授權；目標帳號copy後可用自己的key與Region副本完成隔離。

**事實查證：** [Encrypting Amazon RDS resources - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)、[Sharing a DB snapshot for Amazon RDS - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)

### 練習題 9｜SAP｜Failover endpoint、DNS 與 client recovery

Multi-AZ failover在五分鐘內完成，但Java clients持續20分鐘連到舊位址；部分長transaction也沒有自動續跑。選擇兩項應納入修正的措施。

A. 讓clients使用RDS DNS endpoint而非固定IP，並調整JVM/OS DNS cache使其能在合理時間重新解析
B. 把目前primary IP永久寫入configuration；DNS查詢越少，failover恢復越快
C. 假設既有TCP sessions與未完成transactions會跨instance無縫延續，因此關閉retry
D. 把read replica endpoint當成永遠相同的writer endpoint，所有writes不需辨識角色
E. 設定connection timeout、重連與bounded retry/backoff，並讓可重試交易具備idempotency，因failover會中斷既有connections

**答案：A、E**

- **A：** 正確。RDS在failover時讓DNS名稱指向新primary；client若固定IP或過度快取舊解析，會延長實際恢復時間。
- **B：** 不正確。Primary IP可能在failover改變，硬編碼正是client長時間失敗的原因之一。
- **C：** 不正確。Instance切換會中斷既有connections，未完成transaction不能假設自動在新primary繼續。
- **D：** 不正確。Replica與writer endpoints角色不同；把唯讀端點當writer可能造成寫入失敗或錯誤路由。
- **E：** 正確。Timeout、reconnect與受控retry讓client在DNS切換後恢復；idempotency降低重試造成重複寫入的風險。

**事實查證：** [Failing over a Multi-AZ DB instance for Amazon RDS - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.Failover.html)

### 練習題 10｜SAP｜RDS、Aurora 與 self-managed database 選型

架構委員會比較三個workloads：A需要managed Microsoft SQL Server而不需OS root；B依賴必須安裝到host OS的自訂database extension；C是可相容Aurora PostgreSQL的SaaS，重視多reader與跨Region read/DR架構。選擇兩項正確判斷。

A. A應選Aurora，因Aurora原生支援所有SQL Server engine features
B. A可評估RDS for SQL Server，以managed backups、patching與HA換取較少OS控制
C. B應選RDS，因RDS允許root登入並任意修改database host storage layout
D. C可在完成extension/SQL相容性與TCO驗證後評估Aurora PostgreSQL及其reader/global能力
E. C一定應選Aurora，因managed程度較高代表所有workload與Region都必然更便宜

**答案：B、D**

- **A：** 不正確。Aurora相容MySQL與PostgreSQL家族，不是SQL Server engine；A應比較RDS for SQL Server等實際相容服務。
- **B：** 正確。A不需要host控制，RDS for SQL Server可承接多項日常維運，但仍需核對edition、feature與license需求。
- **C：** 不正確。RDS不提供root OS access或任意storage layout；B若extension要求host控制，應評估EC2 self-managed database。
- **D：** 正確。Aurora的shared storage、reader與Global Database能力可能符合C，但SQL/extension相容性、Region供應與完整成本必須先驗證。
- **E：** 不正確。Managed服務可降低操作負擔，但instance、I/O、replica、跨Region與license成本會依workload改變，不能保證永遠最便宜。

**事實查證：** [AWS Database category iconDatabases - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[What is Amazon Aurora? - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS …」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「關聯式資料庫的HA、read scaling與connection management是三個不同問題。」，所以「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」能直接滿足它；若constraint改成「Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」。替代方案「Aurora有不同storage與replica架構，不能把所有RDS行為直接套用。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把read replica當零RPO HA，或Lambda直接建立大量DB connections。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「關聯式資料庫的HA、read scaling與connection management是三個不同問題。」，排除會導致「把read replica當零RPO HA，或Lambda直接建立大量DB connections。」的選項，再選「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Multi-AZ提供同步standby/failover；read replica服務讀取與DR；RDS Proxy吸收短生命connection。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate availability replicas from read-scaling replicas」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 46 章　Aurora、Global Database 與 Serverless

雲端關聯式workload需要更快failover、跨Region讀取或依需求調整容量。

## 跟著一筆資料走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：全球SaaS主寫在美國，歐洲低延遲讀取，Region事故需在幾分鐘內恢復。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：雲端關聯式workload需要更快failover、跨Region讀取或依需求調整容量。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，關聯式資料庫像一本正式帳簿：交易要讓多個欄位一起成立，讀副本則像提供影本給查詢者使用。 副本可能有延遲，failover也涉及client重新連線；不能把影本當成永遠同步的主帳簿。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon Aurora如何接手工作，再看Aurora Global Database何時更合適，最後用設定與考題驗證「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：全球SaaS主寫在美國，歐洲低延遲讀取，Region事故需在幾分鐘內恢復。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon Aurora：authoritative或主要資料路徑]
          │ 提供MySQL/PostgreSQL-compatible relational database與分散式shar…
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Aurora Global Database：將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
  · Aurora Serverless：讓Aurora compute capacity依負載在設定範圍內細粒度調整。

失敗時先找：將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon Aurora有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Aurora和Aurora Global Database並不是兩個任意的產品名稱。前者適合本章，是因為「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」直接回應了眼前的問題；後者描述的「標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「shared storage changes replica economics but not application recovery」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 |
| Aurora Serverless | 讓Aurora compute capacity依負載在設定範圍內細粒度調整。 | Serverless v2以ACU擴縮cluster instances，storage仍是Aurora distributed storage。 |

## 把全圖套進一個具體案例

**場景：** 全球SaaS主寫在美國，歐洲低延遲讀取，Region事故需在幾分鐘內恢復。

1. 故事的起點：全球SaaS主寫在美國，歐洲低延遲讀取，Region事故需在幾分鐘內恢復。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Aurora負責「提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Aurora Global Database、Aurora Serverless各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Aurora DSQL：不要因為名字有 Aurora，就把它當成 Aurora Global Database 的新 instance class

Aurora Global Database 以單一 primary Region 寫入、secondary Regions 讀取與災難復原；Aurora DSQL 是另一個serverless distributed relational service，多 Region peered cluster 的兩個 Regional endpoints 可同時讀寫並提供強一致性。這會改變 application write path、latency、SQL compatibility 與 migration 假設。

```text
Aurora Global Database:
writer Region ─ async storage replication ─> secondary read Region

Aurora DSQL multi-Region:
app Region A ─ write/read endpoint A ─┐
                                     ├─ one logical strongly consistent DB
app Region B ─ write/read endpoint B ─┘
```

#### 服務選型前先問的四個問題

```Decision record
data_model: relational + ACID
write_topology: single-writer-region | multi-region-active-active
consistency: local/replica-lag-aware | cross-region-strong
compatibility:
  required_postgresql_features: [...]
  migration_tooling_and_driver_tests: [...]
latency_budget:
  local_read_ms: ...
  cross-region_commit_ms: ...
```

1. PostgreSQL-compatible 不等於支援所有 PostgreSQL extensions/features；必須以實際 schema、query 與 driver 做 compatibility test。
2. 強一致 multi-Region 仍受物理距離影響；架構師要測 transaction latency，而不是把 active-active 當成零代價。
3. Aurora DSQL 自動管理 infrastructure，卻不會替你決定 shard-independent transaction、hot key、schema 或 business invariant。

**選擇邊界：** 既有 Aurora／RDS workload、完整 engine feature 與單 writer 模型仍有成熟優勢；需要 serverless distributed SQL、多 Region active-active writes 與強一致性時才評估 DSQL，並先確認 Region set 與 feature compatibility。

**考試範圍：** Aurora/RDS/DynamoDB 是 SAA/SAP-C02 核心；Aurora DSQL 應清楚標成已公告轉版期間的現代架構補充，不可拿新服務知識覆蓋目前官方 exam guide。

- [AWS：What is Amazon Aurora DSQL?](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)

## 需要時再查：四個閱讀支點

### Amazon Aurora

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：雲端關聯式workload需要更快failover、跨Region讀取或依需求調整容量。
- **具體例子／邊界：** 在「全球SaaS主寫在美國，歐洲低延遲讀取，Region事故需在幾分鐘內恢復。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Aurora Global Database

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：shared storage changes replica economics but not application recovery。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon Aurora

- **功用：** 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。
- **底層機制：** Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。
- **關鍵設定：** cluster/instance endpoints、replica count、I/O-Optimized、backup、failover priority、parameter groups與Global Database。
- **選擇時機：** 需要高availability、較多read replicas、快速failover或AWS-native relational features。
- **替換時機：** 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。

### Aurora Global Database

- **功用：** 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
- **底層機制：** Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。
- **關鍵設定：** primary/secondary Regions、write forwarding、global write、switchover/failover、RPO monitoring與headless secondary。
- **選擇時機：** 全球relational reads與分鐘級Region recovery。
- **替換時機：** 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。

### Aurora Serverless

- **功用：** 讓Aurora compute capacity依負載在設定範圍內細粒度調整。
- **底層機制：** Serverless v2以ACU擴縮cluster instances，storage仍是Aurora distributed storage。
- **關鍵設定：** min/max ACU、auto-pause能力依版本、promotion tier、scaling configuration與RDS Proxy相容性。
- **選擇時機：** 不可預測、間歇或多tenant database且仍需要relational semantics。
- **替換時機：** 穩定高負載provisioned Aurora可能更可預測/便宜；不是零connection管理。

## 考前與實作時再查：設定操作手冊

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

### Aurora Serverless：逐項設定說明

#### `min/max ACU`

- **控制什麼：** `min/max ACU`設定Aurora Serverless的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「不可預測、間歇或多tenant database且仍需要relational semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `auto-pause能力依版本`

- **控制什麼：** `auto-pause能力依版本`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。
- **何時需要：** 需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。
- **怎麼設定／驗證：** 明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。
- **常見錯法：** One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。

#### `promotion tier`

- **控制什麼：** `promotion tier`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

#### `scaling configuration`

- **控制什麼：** `scaling configuration`是一組可版本化的engine/runtime參數，會改變Aurora Serverless的實際process行為。
- **何時需要：** 當需求符合「不可預測、間歇或多tenant database且仍需要relational semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `RDS Proxy相容性`

- **控制什麼：** `RDS Proxy相容性`指定Aurora Serverless依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。
- **何時需要：** Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。
- **怎麼設定／驗證：** 鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。
- **常見錯法：** Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。

## 讀到這裡，請用自己的話說一次

1. Amazon Aurora的責任：提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。
2. 底層機制：Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。
3. 第一個要看的設定：cluster/instance endpoints、replica count、I/O-Optimized、backup、failover priority、parameter groups與Global Database。
4. 選擇邏輯：Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。
5. 不要混淆：Aurora Global Database的責任是「將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。」；它不會自動取代Amazon Aurora。
6. 替換訊號：標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。
7. 最常見錯法：將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。
8. 可移植原則：shared storage changes replica economics but not application recovery。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 | 需要高availability、較多read replicas、快速failover或AWS-native relational features。 | 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 | 全球relational reads與分鐘級Region recovery。 | 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。 |
| Aurora Serverless | 讓Aurora compute capacity依負載在設定範圍內細粒度調整。 | Serverless v2以ACU擴縮cluster instances，storage仍是Aurora distributed storage。 | 不可預測、間歇或多tenant database且仍需要relational semantics。 | 穩定高負載provisioned Aurora可能更可預測/便宜；不是零connection管理。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。 | 只有當題目條件明確改變時才可能合理。 | 將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。」之間做選擇。
- 認得常考設定：cluster/instance endpoints、replica count、I/O-Optimized、backup、failover priority、parameter groups與Global Database。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Aurora distributed storage 與 compute separation

Aurora PostgreSQL writer的compute instance突然故障，但cluster volume健康，另一AZ已有reader。團隊擔心必須先把數TB資料完整複製到reader才能恢復。哪個說明最正確？

A. Aurora instances共享跨多AZ的distributed cluster storage；健康reader可被提升或建立新compute，但clients仍需重新連線
B. 每個Aurora reader都維護完全獨立的async EBS copy，必須先完成整庫重建才能promotion
C. 共享storage代表所有Aurora Regions同步commit，因此任何Region故障都保證零RPO
D. Aurora cluster volume就是可由一般EC2直接mount的EFS filesystem

**答案：A**

- **A：** 正確。Aurora把compute與cluster volume分離，writer與readers使用同一distributed storage；compute故障不要求先複製完整資料，但既有connections會中斷。
- **B：** 不正確。這描述較像每個replica持有獨立storage的架構；Aurora本Region readers共享cluster volume。
- **C：** 不正確。單一Aurora cluster的跨AZstorage不等於跨Region同步；Global Database另有非同步複寫與RPO。
- **D：** 不正確。Cluster volume由Aurora服務管理，只供cluster instances使用，不是客戶可mount的通用NFS filesystem。

**事實查證：** [High availability for Amazon Aurora - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)

### 練習題 2｜SAA｜Aurora cluster、reader 與 custom endpoints

一個Aurora cluster有writer、兩個一般readers與兩個大規格analytics readers。OLTP writes只能送目前writer，一般reads要分散，BI connections只能使用analytics subset。哪個routing配置正確？

A. 把所有traffic送cluster endpoint；它會把每個SQL statement平均分配到writer與readers
B. Writes用cluster/writer endpoint，一般reads用reader endpoint，BI用只含analytics instances的custom endpoint
C. Writes用reader endpoint；reader endpoint提供strong read-after-write並自動提升每個connection
D. BI固定使用某reader的instance endpoint；該名稱在任何failover後都會自動改指新writer

**答案：B**

- **A：** 不正確。Cluster endpoint指向目前writer，不會將writes或每個statement分散到所有instances。
- **B：** 正確。Writer endpoint追蹤primary，reader endpoint在可用readers間做connection-level balance，custom endpoint可限定analytics subset。
- **C：** 不正確。Reader endpoint用於read capacity，不能作為一般write入口，也不保證跨所有reads的強read-after-write。
- **D：** 不正確。Instance endpoint固定識別特定DB instance，不會因promotion自動改成另一instance；適合明確instance routing而非writer抽象。

**事實查證：** [Amazon Aurora endpoint connections - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html)

### 練習題 3｜SAA → SAP｜Aurora failover tier 與 promotion priority

Aurora production cluster有一台與writer同規格的reader、一台較小但可短暫承載的reader，以及一台只供BI且promotion後會超載的reader。公司要求writer故障時優先提升同規格instance。應如何設定？

A. 依建立時間排序；最早建立的reader永遠優先，無需任何failover設定
B. 依reader endpoint回傳的DNS順序推論promotion順序
C. 把同規格reader設為最高promotion tier，較小reader次之，BI reader最低，並驗證候選容量與AZ分散
D. 建立Global Database secondary；它會自動比本Region所有readers更早promotion

**答案：C**

- **A：** 不正確。建立時間不是可依賴的唯一promotion contract；應使用Aurora failover priority tiers表達意圖。
- **B：** 不正確。Reader endpoint的DNS與connection balancing不代表failover priority。
- **C：** 正確。Promotion tiers控制優先群組，容量與AZ位置則確保被選中的reader真的能承接writer負載；同tier仍由服務規則選擇。
- **D：** 不正確。Global secondary處理Region級DR，不會自然取代本Regionreader的cluster failover順序。

**事實查證：** [High availability for Amazon Aurora - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)

### 練習題 4｜SAP｜Aurora Global Database replication lag 與 RPO

Aurora primary位於東京，法蘭克福與維吉尼亞secondary提供本地低延遲reads。業務把Region災難時「資料損失不超過5秒」列為架構目標，但不是不可違反的同步寫入保證。哪個敘述最準確？

A. 每筆commit會等待所有secondary Regions確認，所以不必監控任何global lag
B. Secondary clusters預設都是multi-writer，可在網路分割時各自commit後自動無衝突merge
C. Global Database只建立跨Region DNS；資料仍需應用自行batch copy
D. 把跨Region複寫視為非同步，監控replication lag、設定告警並演練failover；這些措施可驗證與改善5秒目標，但不能把一次演練結果宣稱成每次災難的硬性上限

**答案：D**

- **A：** 不正確。Aurora Global Database不要求primary commit等待所有Regions，因此不能宣稱同步零RPO。
- **B：** 不正確。一般拓撲維持單一primary writer；secondary不是可在partition期間任意獨立寫入再merge的active-active peers。
- **C：** 不正確。Global Database會使用專用基礎設施複寫storage changes，不只是DNS routing。
- **D：** 正確。Aurora Global Database的跨Region複寫是非同步；replication lag可用來管理RPO目標，但未複寫完成的writes在unplanned failover時仍可能遺失。Planned switchover會先等待clusters同步，目標是零資料損失；unplanned failover沒有相同前提。若5秒是不可違反的hard guarantee，就不能只靠此非同步secondary宣稱滿足。

**事實查證：** [Using Amazon Aurora Global Database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[Monitoring an Amazon Aurora global database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-monitoring.html)、[Using switchover or failover in Amazon Aurora Global Database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 5｜SAP｜Aurora Global Database switchover 與 failover

公司下週要做primary Region計畫性維護；另有runbook處理primary Region突然完全失聯。資料團隊希望避免雙writer與不必要資料損失。哪個流程最正確？

A. 健康時以managed switchover先同步並交換primary角色；非計畫故障時執行failover並評估lag，兩者都要切換正確endpoint、確認單一writer並規劃failback
B. 兩種情況都只改Route 53 record；DNS health check會自動完成database role promotion
C. 突然故障時保證零RPO，因此不需檢查secondary落後或資料差異
D. 提升secondary後讓恢復的舊primary繼續接受writes；Global Database會自動合併衝突

**答案：A**

- **A：** 正確。Planned switchover可在兩端健康時受控同步角色；unplanned failover可能有lag，且client routing、writer fencing與failback都不可省略。
- **B：** 不正確。Route 53只影響名稱解析，無法自行改變Aurora Global Database cluster角色。
- **C：** 不正確。非計畫Region故障可能在非同步複寫尚未追上時發生，必須量測並處理RPO。
- **D：** 不正確。恢復舊Region後必須先重新加入或重建拓撲；允許兩邊同時寫會造成split-brain風險。

**事實查證：** [Using switchover or failover in Amazon Aurora Global Database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 6｜SAP｜Aurora Global Database write forwarding

歐洲應用連到Aurora Global Database secondary以取得低延遲reads，但少量writes仍必須由美國primary處理。團隊不想把架構改成multi-primary。哪個評估正確？

A. 在secondary本地commit後雙向merge；write forwarding會自動解決所有同row conflicts
B. 在支援條件下啟用write forwarding，把secondary收到的writes送到primary處理，並測量跨Region latency與所選consistency設定
C. Write forwarding消除物理距離；歐洲write latency會與本地commit完全相同
D. 啟用後secondary可在與primary斷線時無限期安全寫入，恢復後保證沒有衝突

**答案：B**

- **A：** 不正確。Forwarded write仍由primary執行，不是secondary本地multi-primary commit或雙向conflict merge。
- **B：** 正確。Write forwarding保留單一writer ownership，但加入跨Region round trip與一致性選項，必須以實際transaction測試。
- **C：** 不正確。Request需要到primary處理，網路距離與primary負載仍會影響write latency。
- **D：** 不正確。Secondary無法把forwarded writes送達primary時不能假設離線本地commit；network partition仍需failure handling。

**事實查證：** [Using write forwarding in an Amazon Aurora global database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html)

### 練習題 7｜SAA → SAP｜Aurora Serverless v2 ACU scaling range

Aurora Serverless v2 production cluster平時需要約4 ACUs，月底壓測需要48 ACUs。現有max設為8，尖峰時`ACUUtilization`接近100%、latency與connection errors上升。服務必須24x7立即可用。哪個調整最合理？

A. 保留max 8；Serverless v2會忽略max並在需要時無上限擴展
B. 把min設為0即可解決尖峰；auto-pause後cache與connections一定完全保留且沒有resume影響
C. 依壓測設定能承載baseline的min與至少涵蓋48 ACUs的max，監控capacity、connections與latency；只有支援且可接受pause/resume的workload才考慮min 0
D. 移除connection pooling並延長所有transactions；每個request會啟動獨立database instance

**答案：C**

- **A：** 不正確。Max ACU是實際capacity上限，設得過低會限制尖峰擴展並影響可用memory與功能。
- **B：** 不正確。Min 0只在支援版本提供auto-pause，resume期間會影響connections與latency，不適合題目的24x7立即服務要求。
- **C：** 正確。Capacity range必須涵蓋實測baseline與peak；CloudWatch capacity、utilization、connection與latency共同證明設定是否足夠。
- **D：** 不正確。Serverless v2是長時間運行並細粒度擴縮的DB capacity，不是每request建立一個database；長transaction還可能妨礙scale與pooling。

**事實查證：** [Using Aurora serverless - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)、[Performance and scaling for Aurora serverless - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)、[Scaling to Zero ACUs with automatic pause and resume for Aurora serverless - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)

### 練習題 8｜SAP｜Provisioned、Serverless v2 與 mixed cluster

Aurora PostgreSQL writer負載全年穩定，兩個月末reporting readers會從低使用量突然升到高負載。Engine、version與Region已確認支援Serverless v2。選擇兩項合理設計。

A. Serverless v2只能有單一instance且不能跨AZ，因此cluster無法保留HA reader
B. Provisioned Aurora不能增加reader；所有讀流量必須在writer執行
C. 改用Serverless v2會把PostgreSQL SQL engine轉成NoSQL，application必須重寫資料模型
D. 穩定writer可保留合適的provisioned instance，bursty reporting readers可評估Serverless v2並設定可承載尖峰的ACU range
E. 支援的cluster可混合provisioned與Serverless v2 instances，但要設定promotion tiers並確認每個failover candidate能承擔writer負載

**答案：D、E**

- **A：** 不正確。Serverless v2可作為Aurora cluster中的DB instances並參與多instance HA；不是只能單instance。
- **B：** 不正確。Provisioned Aurora可加入Aurora Replicas；是否用Serverless取決於負載彈性與成本。
- **C：** 不正確。Serverless v2改變capacity供應方式，不會把Aurora PostgreSQL轉成NoSQL服務。
- **D：** 正確。Steady與bursty角色可採不同instance model；reporting readers的min/max ACU仍要由壓測與成本資料決定。
- **E：** 正確。Mixed configuration可提供彈性，但promotion後的容量、tier、AZ分散與feature相容性必須預先驗證。

**事實查證：** [How Aurora serverless works - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.how-it-works.html)

### 練習題 9｜SAP｜Aurora backup、PITR、clone 與 Backtrack

團隊有三個需求：在保留窗口內恢復災難前時間點、十分鐘內建立完整大小的測試cluster而不先複製全部storage，以及快速撤銷Aurora MySQL production的一次錯誤操作。選擇兩項正確說明。

A. Automated backups/PITR可還原新的cluster；Aurora clone以copy-on-write快速建立獨立測試cluster
B. PITR會直接覆寫目前production cluster，因此不需驗證或切換application
C. Clone一建立就是與source完全無關的完整物理backup，source生命週期與共享storage成本都無需考慮
D. Backtrack支援所有Aurora PostgreSQL與Aurora MySQL clusters，且等同跨Region backup
E. Backtrack只適用特定Aurora MySQL條件並會把既有cluster移回過去狀態；仍需保留backup/PITR作獨立恢復

**答案：A、E**

- **A：** 正確。PITR建立可驗證的新cluster供災難恢復；clone利用copy-on-write快速供應測試環境，兩者目的不同。
- **B：** 不正確。Aurora PITR是restore-to-new-cluster流程，application cutover與資料驗證不可省略。
- **C：** 不正確。Clone起初共享底層storage並在變更時增加配置；它不是可取代長期backup的獨立完整copy。
- **D：** 不正確。Backtrack不是所有engine的通用功能，也不建立跨Region recovery copy。
- **E：** 正確。Backtrack是特定Aurora MySQL配置的原cluster回退能力；它與能建立獨立restore target的backup/PITR不能互相取代。

**事實查證：** [Overview of backing up and restoring an Aurora DB cluster - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.html)、[Cloning a volume for an Amazon Aurora DB cluster - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Clone.html)、[Backtracking an Aurora DB cluster - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Backtrack.html)

### 練習題 10｜SAP + 2026 enrichment｜RDS for Oracle、Aurora Global Database 與 Aurora DSQL 邊界

公司同時評估三種資料庫需求：A是必須保留特定Oracle edition功能的既有ERP；B是單一primary writer、全球read locality與跨Region DR；C是全新服務，要求兩個應用Region都能local commit，跨Region strong consistency，且可接受先驗證PostgreSQL相容範圍與功能限制。選擇兩項正確判斷。

A. B應使用Aurora Global Database的write forwarding，因secondary會在本Region獨立commit，再與primary自動合併衝突
B. A應先核對RDS for Oracle的edition與feature支援；只有managed service限制或OS-level控制無法接受時，才評估EC2 self-managed Oracle
C. Aurora DSQL與Aurora Global Database具有相同writer模型；兩者都只有一個可commit的primary Region
D. C可評估Aurora DSQL：它是serverless、active-active multi-Region且提供strong consistency；兩Region配置需要witness Region，並須先驗證Region set、PostgreSQL相容性與feature limits
E. B只要需要跨Region reads就必須選Aurora DSQL；Aurora Global Database不提供secondary reads或DR

**答案：B、D**

- **A：** 不正確。Aurora Global Database維持單一primary writer；write forwarding把secondary收到的DML送回primary執行與commit，不是各Region獨立commit後做conflict merge。
- **B：** 正確。RDS for Oracle保留managed Oracle engine與支援的edition能力；若需求進一步包含未受支援的host access、agent或特定控制，才需要承擔self-managed責任。
- **C：** 不正確。Aurora Global Database是單一primary writer加非同步跨Regionsecondary；Aurora DSQL則為active-active endpoints與strong consistency，兩者的state ownership不同。
- **D：** 正確。Aurora DSQL符合C的active-active與strong-consistency方向；兩Regioncluster以第三個witness Region協助達成可用性與一致性。它仍有支援Region、SQL/extension與服務功能限制。本選項是2026架構enrichment，Aurora DSQL不屬於SAP-C02既定必考服務清單。
- **E：** 不正確。B的單一writer、全球readers與DR正是Aurora Global Database的典型邊界；DSQL應由active-active write與strong-consistency需求驅動，而不是看到multi-Region就一律替換。

**事實查證：** [What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[Using Amazon Aurora Global Database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[Using write forwarding in an Amazon Aurora global database - Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html)、[What is Amazon Aurora DSQL? - Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)、[Working with Amazon Aurora DSQL clusters - Amazon Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Aurora replicas共享distributed storage；Global Database提…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「雲端關聯式workload需要更快failover、跨Region讀取或依需求調整容量。」，所以「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」能直接滿足它；若constraint改成「標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」。替代方案「標準RDS可能更便宜且引擎相容性更直接，應依feature與成本選擇。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「雲端關聯式workload需要更快failover、跨Region讀取或依需求調整容量。」，排除會導致「將跨Region replica當同步零資料遺失，或忽略promotion、DNS與write endpoint切換。」的選項，再選「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-1.3 Design reliable and resilient architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Aurora replicas共享distributed storage；Global Database提供跨Region複寫；Serverless依版本與需求彈性配置。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「shared storage changes replica economics but not application recovery」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 47 章　DynamoDB Partition、Capacity、GSI 與 DAX

DynamoDB依partition key分散資料，schema設計必須由access patterns與流量分布開始。

## 跟著一筆資料走：先從故事開始

把鏡頭拉到一個真實的production現場：遊戲排行榜每秒數十萬寫入，需依玩家與時間查詢並避免單一熱門partition。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：DynamoDB依partition key分散資料，schema設計必須由access patterns與流量分布開始。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：DynamoDB像把大量卡片依partition key分到不同抽屜；key選得好就能直接找到，選得差就會讓所有人擠在同一個抽屜。 實際partition由服務管理，類比不代表能手動指定實體節點；仍要用access pattern與capacity metric驗證。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon DynamoDB是這一章的入口，DynamoDB global secondary indexes用來畫出邊界；主要方向「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：遊戲排行榜每秒數十萬寫入，需依玩家與時間查詢並避免單一熱門partition。

先從每次request知道的key開始
      │
      ▼
Partition key決定資料如何分散
      │
      ├─ 同一key流量過熱 ──> hot partition / throttling
      └─ 分布均勻 ────────> 水平擴展

Sort key讓同一partition內做range/query。
GSI建立另一種查詢入口，但會增加write與storage成本。
DAX/cache只加速可接受cached semantics的讀取，不修正錯誤data model。

失敗時先找：使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon DynamoDB有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon DynamoDB和DynamoDB global secondary indexes並不是兩個任意的產品名稱。前者適合本章，是因為「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」直接回應了眼前的問題；後者描述的「DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「distributed databases expose partition design through performance」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |
| DynamoDB global secondary indexes | 為base table提供另一組partition/sort key的查詢入口。 | GSI維護獨立partition與capacity，base table更新非同步投影到index。 |
| DAX | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 |
| DynamoDB Global Tables | 把DynamoDB table複寫成multi-Region active-active。 | MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。 |

## 把全圖套進一個具體案例

**場景：** 遊戲排行榜每秒數十萬寫入，需依玩家與時間查詢並避免單一熱門partition。

1. 故事的起點：遊戲排行榜每秒數十萬寫入，需依玩家與時間查詢並避免單一熱門partition。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon DynamoDB負責「提供managed key-value/document database與單位毫秒scale。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：DynamoDB global secondary indexes、DAX、DynamoDB Global Tables各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon DynamoDB

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：DynamoDB依partition key分散資料，schema設計必須由access patterns與流量分布開始。
- **具體例子／邊界：** 在「遊戲排行榜每秒數十萬寫入，需依玩家與時間查詢並避免單一熱門partition。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### DynamoDB global secondary indexes

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：distributed databases expose partition design through performance。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

### DynamoDB global secondary indexes

- **功用：** 為base table提供另一組partition/sort key的查詢入口。
- **底層機制：** GSI維護獨立partition與capacity，base table更新非同步投影到index。
- **關鍵設定：** index PK/SK、projection、capacity mode、sparse index與backfill monitoring。
- **選擇時機：** 需要依非primary key attributes高效Query，且可接受eventual propagation。
- **替換時機：** 強一致GSI read不支援；需要同partition另一排序可評估LSI但須建表時定義。

### DAX

- **功用：** 為DynamoDB提供API-compatible、in-memory read-through cache。
- **底層機制：** Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。
- **關鍵設定：** cluster nodes/subnets/SG、IAM、TTL、parameter group、encryption與client endpoint。
- **選擇時機：** microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。
- **替換時機：** 強一致read、複雜Redis structures或非DynamoDB資料使用ElastiCache/application cache。

### DynamoDB Global Tables

- **功用：** 把DynamoDB table複寫成multi-Region active-active。
- **底層機制：** MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。
- **關鍵設定：** consistency mode（MREC/MRSC）、replica Regions、capacity、PITR、KMS、Streams、MRSC Region-set availability與application conflict assumptions。
- **選擇時機：** 需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。
- **替換時機：** 跨item／跨Region複雜transaction、需要完整關聯SQL，或MRSC限制不合時，改用單writer、Aurora/DSQL或重新設計business invariant。

## 考前與實作時再查：設定操作手冊

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

### DynamoDB global secondary indexes：逐項設定說明

#### `index PK/SK`

- **控制什麼：** `index PK/SK`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「需要依非primary key attributes高效Query，且可接受eventual propagation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出DynamoDB global secondary indexes的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `projection`

- **控制什麼：** `projection`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「需要依非primary key attributes高效Query，且可接受eventual propagation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出DynamoDB global secondary indexes的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `capacity mode`

- **控制什麼：** `capacity mode`選擇DynamoDB global secondary indexes的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `sparse index`

- **控制什麼：** `sparse index`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「需要依非primary key attributes高效Query，且可接受eventual propagation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出DynamoDB global secondary indexes的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `backfill monitoring`

- **控制什麼：** `backfill monitoring`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

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

### DynamoDB Global Tables：逐項設定說明

#### `consistency mode（MREC/MRSC）`

- **控制什麼：** `consistency mode（MREC/MRSC）`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄DynamoDB Global Tables的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

#### `replica Regions`

- **控制什麼：** `replica Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署DynamoDB Global Tables前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `capacity`

- **控制什麼：** `capacity`設定DynamoDB Global Tables的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `PITR`

- **控制什麼：** `PITR`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DynamoDB Global Tables依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在DynamoDB Global Tables指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `Streams`

- **控制什麼：** `Streams`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從DynamoDB Global Tables持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `MRSC Region-set availability`

- **控制什麼：** `MRSC Region-set availability`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署DynamoDB Global Tables前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `application conflict assumptions`

- **控制什麼：** `application conflict assumptions`定義DynamoDB Global Tables管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

## 可以直接對照 AWS 的設定範例

### DynamoDB table：均勻partition key、GSI、PITR與TTL

```yaml
Resources:
  EventsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - {AttributeName: tenant_id, AttributeType: S}
        - {AttributeName: event_time, AttributeType: S}
        - {AttributeName: status, AttributeType: S}
      KeySchema:
        - {AttributeName: tenant_id, KeyType: HASH}
        - {AttributeName: event_time, KeyType: RANGE}
      GlobalSecondaryIndexes:
        - IndexName: by_status
          KeySchema:
            - {AttributeName: status, KeyType: HASH}
            - {AttributeName: event_time, KeyType: RANGE}
          Projection: {ProjectionType: ALL}
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true

```

1. tenant_id若有單一超大型tenant仍可能hot；partition key設計要看實際traffic distribution。
2. GSI是非同步維護的另一個access path；不要假設可做strongly consistent read。
3. TTL刪除是非同步且不消耗table write capacity，不應用於精準到秒的排程。

## 讀到這裡，請用自己的話說一次

1. Amazon DynamoDB的責任：提供managed key-value/document database與單位毫秒scale。
2. 底層機制：Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
3. 第一個要看的設定：PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
4. 選擇邏輯：選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。
5. 不要混淆：DynamoDB global secondary indexes的責任是「為base table提供另一組partition/sort key的查詢入口。」；它不會自動取代Amazon DynamoDB。
6. 替換訊號：ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。
7. 最常見錯法：使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。
8. 可移植原則：distributed databases expose partition design through performance。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| DynamoDB global secondary indexes | 為base table提供另一組partition/sort key的查詢入口。 | GSI維護獨立partition與capacity，base table更新非同步投影到index。 | 需要依非primary key attributes高效Query，且可接受eventual propagation。 | 強一致GSI read不支援；需要同partition另一排序可評估LSI但須建表時定義。 |
| DAX | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 | microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。 | 強一致read、複雜Redis structures或非DynamoDB資料使用ElastiCache/application cache。 |
| DynamoDB Global Tables | 把DynamoDB table複寫成multi-Region active-active。 | MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。 | 需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。 | 跨item／跨Region複雜transaction、需要完整關聯SQL，或MRSC限制不合時，改用單writer、Aurora/DSQL或重新設計business invariant。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。 | 只有當題目條件明確改變時才可能合理。 | 使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。」之間做選擇。
- 認得常考設定：PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA → SAP｜Partition key distribution 與 hot key

社群平台把reaction events存入DynamoDB，partition key是`CELEBRITY#<id>`、sort key是timestamp。全表provisioned WCU仍有餘裕，但單一celebrity在直播時承受80% writes並持續throttle。哪個重設計最直接？

A. 在logical celebrity key後加入受控write shard suffix分散writes，並在讀取時平行Query各shards後聚合
B. 只增加sort key的timestamp精度；同一partition key下更多sort key值會自動分到不同physical partitions
C. 改用Scan讀取全表；Scan會重新平均分配該celebrity的write traffic
D. 加入DAX；DAX會cache並吸收所有writes，因此hot partition不再throttle

**答案：A**

- **A：** 正確。單一logical key的集中write rate需要更多partition-key值才能分散；write sharding以額外query aggregation換取較均勻的physical distribution。
- **B：** 不正確。相同partition key的items形成同一item collection；增加sort-key多樣性不能保證把單一hot key的writes拆到不同partitions。
- **C：** 不正確。Scan是讀取操作且成本高，不會改變write routing或partition-key分布。
- **D：** 不正確。DAX主要加速cacheable reads並write-through到DynamoDB，不能消除底層單一key的write capacity限制。

**事實查證：** [Partitions and data distribution in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.Partitions.html)、[Best practices for designing and using partition keys effectively in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)

### 練習題 2｜SAA｜Composite key 與 Query/Scan

訂單API最常執行「取得某customer最近50筆orders」與「取得該customer在日期區間內的orders」，不得掃描全表。哪個primary key與request模式最合適？

A. Partition key用隨機`orderId`，每次以Scan加FilterExpression找customer與日期
B. Partition key用`customerId`，sort key用可排序的`orderTimestamp#orderId`，以Query與sort-key range條件讀取
C. Partition key只用`orderDate`；sort key會自動在所有customers間提供全域唯一排序
D. 任意key設計都可以；FilterExpression會在DynamoDB讀取前排除items，因此與KeyConditionExpression消耗相同RCU

**答案：B**

- **A：** 不正確。隨機orderId適合單筆lookup，但customer時間範圍需要全表Scan，會隨table成長而浪費讀取容量。
- **B：** 正確。Customer把相關items放入可Query的partition-key範圍，排序時間值讓KeyConditionExpression直接取得最新或指定區間。
- **C：** 不正確。Sort key只在同一partition-key值內排序；以日期作partition key也無法直接取得單一customer跨日期紀錄。
- **D：** 不正確。FilterExpression在items被讀取後才過濾，不會像key condition那樣縮小DynamoDB先讀取的key range或已消耗容量。

**事實查證：** [Querying tables in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)、[Scanning tables in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html)

### 練習題 3｜SAA｜GSI alternate key 與 eventual consistency

Orders table以`orderId`為partition key。客服還要查詢某`customerId`下特定`status`的最近orders，可接受更新後數秒內index尚未反映。哪個設計正確？

A. 建立GSI並要求每次讀取`ConsistentRead=true`；GSI會與base table同步commit
B. GSI必須沿用base table的`orderId` partition key，因此無法服務customer查詢
C. 建立以`customerId`為partition key、`status#timestamp`為sort key的GSI並投影所需attributes，將讀取視為eventually consistent
D. 建立不投影任何非key attributes的GSI；任何欄位仍可由index免費直接返回而不查base table

**答案：C**

- **A：** 不正確。DynamoDB GSI updates非同步傳播，GSI reads不支援strongly consistent選項。
- **B：** 不正確。GSI的用途就是提供不同於base table的partition/sort key，可支援alternate access pattern。
- **C：** 正確。此GSI直接表達customer加status/time查詢；projection決定index可返回內容，application需容忍短暫propagation lag。
- **D：** 不正確。未投影的non-key attributes不能由GSI query直接取得；需要調整projection或另行GetItem讀base table。

**事實查證：** [Using Global Secondary Indexes in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)

### 練習題 4｜SAA → SAP｜LSI 固定 partition key與建立限制

團隊正在建立新table，base key是`customerId`加`orderId`。同一customer內還需依`orderTotal`排序查詢，且某流程要求strongly consistent index reads。哪個index選擇符合？

A. Table上線後隨時新增LSI，並使用完全不同的`regionId` partition key
B. 建立GSI並開啟`ConsistentRead=true`；所有GSI都支援strong reads
C. 建立LSI並為它配置獨立RCU/WCU與跨Region replicas
D. 建table時建立LSI，沿用`customerId` partition key並以`orderTotal`作alternate sort key，同時評估item collection size限制

**答案：D**

- **A：** 不正確。LSI必須與table一起建立，且partition key必須與base table相同。
- **B：** 不正確。GSI可有不同partition key，但只支援eventually consistent reads，不符合題目的strong read。
- **C：** 不正確。LSI與base table共享throughput與partition-key item collection，不是有獨立capacity與Global Tables replicas的table。
- **D：** 正確。LSI以相同partition key加alternate sort key服務同一customer內的另一排序，並可使用strongly consistent reads；設計時要注意item collection上限。

**事實查證：** [Local secondary indexes - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/LSI.html)

### 練習題 5｜SAA｜On-demand 與 provisioned capacity

新遊戲上線前沒有可靠traffic history，活動可能不規則暴增；另一個payroll table長期穩定在約800 writes/s且可提前預測。公司希望兼顧操作負擔與成本。哪個方案合理？

A. 遊戲table先用on-demand降低capacity planning，payroll依量測使用provisioned capacity搭配auto scaling或適用的reserved capacity評估成本
B. 兩者都用on-demand，因on-demand代表任何瞬間流量都絕不會throttle或受partition分布影響
C. 兩者都用固定provisioned且不設auto scaling；provisioned mode無法調整capacity
D. 依一致性需求切換capacity mode；on-demand只支援eventual reads，provisioned才支援strong reads

**答案：A**

- **A：** 正確。未知且不規則流量適合先按request付費，穩定工作負載則能以provisioned、scaling與承諾型折扣做較可預測的成本控制。
- **B：** 不正確。On-demand減少容量規劃但不是無限吞吐；突然成長、table limits與hot keys仍可能造成throttling。
- **C：** 不正確。Provisioned capacity可手動調整並使用Application Auto Scaling；完全固定會增加過度配置或尖峰不足風險。
- **D：** 不正確。Capacity mode決定計費與throughput管理，不會改變DynamoDB read consistency功能。

**事實查證：** [DynamoDB throughput capacity - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html)

### 練習題 6｜SAA｜Capacity units、item size 與 consistency

Provisioned DynamoDB table中的每個item固定為6 KB。穩定負載每秒對一個完整item做一次strongly consistent read，並每秒做一次6 KB transactional write。忽略index額外成本時，至少需要多少capacity？

A. 1 RCU與6 WCU；capacity只按item數量，不按大小或transaction類型
B. 2 RCUs與12 WCUs；read按4 KB邊界進位，write按1 KB邊界進位，transactional write消耗一般write的兩倍
C. 1 RCU與1 WCU；只計算response中實際選取的attributes bytes
D. 0 RCU與6 WCU；strong read由cache免費提供，FilterExpression也會在計費前移除item

**答案：B**

- **A：** 不正確。6 KB strong read需要兩個4 KB read units；6 KB write也先需要六個1 KB units，transaction還會加倍。
- **B：** 正確。6 KB向上取到兩個4 KB strong-read units，所以是2 RCUs；6 KB一般write為6 WCUs，transactional write為12 WCUs。
- **C：** 不正確。Read capacity依讀取item大小計算，不會因ProjectionExpression只返回部分attributes就按response bytes降低。
- **D：** 不正確。Strongly consistent read仍消耗table capacity；FilterExpression是在read之後處理，也不能讓已讀item免費。

**事實查證：** [DynamoDB read and write operations - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/read-write-operations.html)、[DynamoDB provisioned capacity mode - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/provisioned-capacity-mode.html)

### 練習題 7｜SAA → SAP｜Conditional writes、transactions 與 idempotency

最後一件商品的inventory item為1。兩個buyers同時下單；成功訂單必須把inventory減到0並新增另一個ledger item，timeout後相同request可能重試。哪個設計能避免oversell與半完成？

A. 先eventually consistent GetItem，若讀到1就分別Put inventory與ledger；兩個clients會自動排隊
B. 使用BatchWriteItem寫兩個items；BatchWriteItem會對conditions與所有items提供ACID isolation
C. 使用TransactWriteItems，以condition確認inventory仍足夠、原子更新inventory與ledger，並用client request token或業務idempotency key處理重試
D. 只把SQS message ID存log；DynamoDB會據此讓所有未加condition的writes自動exactly once

**答案：C**

- **A：** 不正確。Read-then-write存在race，兩個buyers都可能先讀到1；分開writes也可能只完成inventory或ledger其中一項。
- **B：** 不正確。BatchWriteItem提供批次效率但不是帶condition的多item ACID transaction，未處理項目還需重試。
- **C：** 正確。Condition阻止第二個競爭者在前置狀態改變後扣庫存，transaction確保兩個items共同成功或失敗，idempotency控制timeout retry。
- **D：** 不正確。Queue message ID不會自動變成DynamoDB write condition；consumer仍需明確設計conditional write或transaction idempotency。

**事實查證：** [DynamoDB condition expression CLI example - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[Managing complex workflows with DynamoDB transactions - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)

### 練習題 8｜SAA → SAP｜TTL、Streams 與 PITR 責任邊界

Session table要在`expiresAt`後清理資料，fraud consumer要收到item changes，且營運人員誤刪table時要能恢復。選擇兩項正確設計敘述。

A. TTL時間一到，DynamoDB會在同一秒同步刪除item並保證之後任何read都不返回
B. DynamoDB Streams是永久backup；consumer可在多年後重播所有歷史changes
C. PITR會原地回滾目前table，保留同一table ARN並自動暫停所有writers
D. 啟用TTL做非同步best-effort刪除；若authorization必須在到期秒立即拒絕，application仍要檢查`expiresAt`
E. 用Streams在有限retention內驅動change consumer，另啟用PITR在recovery window內還原新table；兩者不能互相替代

**答案：D、E**

- **A：** 不正確。TTL deletion是非同步，過期item在實際刪除前仍可能由reads看到；不能作為秒級authorization控制。
- **B：** 不正確。Streams只保留有限時間的item-level change records，不是多年永久backup。
- **C：** 不正確。DynamoDB PITR會restore到新的table，不是原地改寫現有table；cutover與資料驗證仍需runbook。
- **D：** 正確。TTL適合生命週期清理但沒有精確刪除SLA，安全敏感流程要以item中的expiration自行判斷。
- **E：** 正確。Streams服務事件處理，PITR服務table recovery；各自有retention、consumer與restore語意，不能拿其中一個取代另一個。

**事實查證：** [Using time to live (TTL) in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)、[Change data capture for DynamoDB Streams - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)、[Point-in-time backups for DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html)

### 練習題 9｜SAP｜Global Tables MREC 與 MRSC

全球購物車需要各Region低延遲active-active writes；另一張支付狀態表要求跨Region strong consistency與RPO 0，候選Regions都在MRSC支援範圍，而且該表不使用DynamoDB transactions、TTL或LSI。選擇兩項正確評估。

A. 購物車可評估MREC，接受非同步replication並設計同item concurrent writes的conflict與failover行為
B. 所有Global Tables一律跨Region同步strong，MREC與MRSC沒有可觀察差異
C. 只建立Route 53 latency records即可；DNS會自動複寫DynamoDB items與resolve write conflicts
D. MREC在network partition期間允許各Region任意更新同item，恢復後保證保存所有欄位且永不發生last-writer conflict
E. 支付表可評估MRSC，但必須採固定三Region拓撲、接受quorum協調的write latency，並確認未依賴transactions、TTL或LSI；建立後也不能任意增減Region

**答案：A、E**

- **A：** 正確。MREC提供多Region本地讀寫與非同步複寫。不同Regions若同時更新同一item，DynamoDB以last-writer-wins處理衝突；application不能假設兩次欄位變更會自動無損merge。
- **B：** 不正確。Global Tables有multi-Region eventual與multi-Region strong consistency選項，行為、限制與latency trade-off不同。
- **C：** 不正確。Route 53只路由clients，不複寫table data，也不提供DynamoDB conflict resolution。
- **D：** 不正確。MREC並不保證並行欄位更新自動無損merge；對同item的競爭writes需要application理解衝突結果。
- **E：** 正確。MRSC提供strongly consistent multi-Region reads/writes與RPO 0。拓撲固定為三個Regions：可使用三個replica Regions，或兩個replica Regions加一個witness Region；quorum/coordinator距離會增加write latency。MRSC不支援DynamoDB transactions、TTL或LSI，而且建立後不能任意加入或移除Region。

**事實查證：** [Global tables - multi-active, multi-Region replication - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)、[How DynamoDB global tables work - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html)

### 練習題 10｜SAA｜DAX cache scope 與 strong reads

遊戲profile服務對相同DynamoDB items有大量eventually consistent GetItem/Query，要求microsecond級cache hits；付款流程則必須strongly consistent read。選擇兩項正確敘述。

A. DAX會把GSI reads轉成strongly consistent，消除GSI propagation lag
B. Profile reads可使用DAX的DynamoDB-compatible in-memory cache，writes由DAX以write-through方式送往DynamoDB
C. DAX是durable system of record；啟用後可關閉DynamoDB PITR並刪除table
D. Strongly consistent reads會由DAX傳到DynamoDB且結果不cache，因此付款流程不能假設取得cache-hit latency
E. 同一DAX cluster可直接cache RDS SQL與OpenSearch queries，只要partition key名稱相同

**答案：B、D**

- **A：** 不正確。DAX不改變GSI只支援eventually consistent reads的資料模型，也不能消除index propagation時間。
- **B：** 正確。DAX適合重複eventually consistent point/query reads，並以write-through更新DynamoDB與cache狀態。
- **C：** 不正確。DynamoDB table仍是durable source of truth；DAX是cache，不能取代PITR、backup或table本身。
- **D：** 正確。DAX對strongly consistent read採pass-through且不cache該結果，所以latency與capacity仍由DynamoDB路徑決定。
- **E：** 不正確。DAX是DynamoDB專用accelerator，不是任意RDS或OpenSearch query cache。

**事實查證：** [In-memory acceleration with DynamoDB Accelerator (DAX) - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)、[DAX and DynamoDB consistency models - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provi…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「DynamoDB依partition key分散資料，schema設計必須由access patterns與流量分布開始。」，所以「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」能直接滿足它；若constraint改成「DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」。替代方案「DAX加速eventually consistent reads；Global Tables處理multi-Region active-active。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「DynamoDB依partition key分散資料，schema設計必須由access patterns與流量分布開始。」，排除會導致「使用Scan代替query、建立hot key，或誤以為GSI與base table同步transaction更新。」的選項，再選「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「選高基數均勻key，透過composite key/GSI支援查詢，依流量選on-demand或provisioned。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「distributed databases expose partition design through performance」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 48 章　ElastiCache 與 Caching Patterns

Cache可降低origin負載與延遲，但引入staleness、eviction與stampede。

## 跟著一筆資料走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：產品頁讀多寫少，但促銷更新後必須快速失效，熱門key會同時到期。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：Cache可降低origin負載與延遲，但引入staleness、eviction與stampede。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon ElastiCache承接主要責任，以Amazon CloudFront檢查替代條件，並用「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：產品頁讀多寫少，但促銷更新後必須快速失效，熱門key會同時到期。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon ElastiCache：authoritative或主要資料路徑]
          │ 提供managed Valkey/Redis OSS/Memcached記憶體data store。
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Amazon CloudFront：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
  · Amazon DynamoDB Accelerator：為DynamoDB提供API-compatible、in-memory read-through cach…

失敗時先找：TTL同時到期造成thundering herd，或把cache當唯一資料來源。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon ElastiCache有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon ElastiCache和Amazon CloudFront並不是兩個任意的產品名稱。前者適合本章，是因為「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」直接回應了眼前的問題；後者描述的「CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：TTL同時到期造成thundering herd，或把cache當唯一資料來源。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「cache is a disposable projection of authoritative state」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| Amazon DynamoDB Accelerator | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 |

## 把全圖套進一個具體案例

**場景：** 產品頁讀多寫少，但促銷更新後必須快速失效，熱門key會同時到期。

1. 故事的起點：產品頁讀多寫少，但促銷更新後必須快速失效，熱門key會同時到期。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon ElastiCache負責「提供managed Valkey/Redis OSS/Memcached記憶體data store。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudFront、Amazon DynamoDB Accelerator各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「TTL同時到期造成thundering herd，或把cache當唯一資料來源。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon ElastiCache

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Cache可降低origin負載與延遲，但引入staleness、eviction與stampede。
- **具體例子／邊界：** 在「產品頁讀多寫少，但促銷更新後必須快速失效，熱門key會同時到期。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudFront

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：TTL同時到期造成thundering herd，或把cache當唯一資料來源。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：cache is a disposable projection of authoritative state。
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

### Amazon DynamoDB Accelerator

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

### Amazon DynamoDB Accelerator：逐項設定說明

#### `cluster nodes/subnets/SG`

- **控制什麼：** `cluster nodes/subnets/SG`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB Accelerator的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `IAM`

- **控制什麼：** `IAM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB Accelerator明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `TTL`

- **控制什麼：** `TTL`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon DynamoDB Accelerator的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `parameter group`

- **控制什麼：** `parameter group`是一組可版本化的engine/runtime參數，會改變Amazon DynamoDB Accelerator的實際process行為。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB Accelerator指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `client endpoint`

- **控制什麼：** `client endpoint`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB Accelerator的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

## 讀到這裡，請用自己的話說一次

1. Amazon ElastiCache的責任：提供managed Valkey/Redis OSS/Memcached記憶體data store。
2. 底層機制：Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
3. 第一個要看的設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
4. 選擇邏輯：Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。
5. 不要混淆：Amazon CloudFront的責任是「在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。」；它不會自動取代Amazon ElastiCache。
6. 替換訊號：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
7. 最常見錯法：TTL同時到期造成thundering herd，或把cache當唯一資料來源。
8. 可移植原則：cache is a disposable projection of authoritative state。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| Amazon DynamoDB Accelerator | 為DynamoDB提供API-compatible、in-memory read-through cache。 | Client先查DAX cluster；miss由DAX讀DynamoDB並cache，主要加速eventually consistent reads。 | microsecond級重複DynamoDB讀、read-heavy且可接受cache semantics。 | 強一致read、複雜Redis structures或非DynamoDB資料使用ElastiCache/application cache。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。 | 只有當題目條件明確改變時才可能合理。 | TTL同時到期造成thundering herd，或把cache當唯一資料來源。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。」之間做選擇。
- 認得常考設定：engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Cache-aside miss path 與 authoritative store

商品API以Aurora保存商品真相，並以ElastiCache快取熱門商品。一次維護清空cache後，服務必須自動重建資料，且cache故障不得造成商品永久遺失。哪個read path最符合cache-aside？

A. Application先查cache；miss時查Aurora，成功後把結果含合理TTL寫回cache再回應，並讓Aurora持續作authoritative store
B. Application只查cache；miss一律回404，等待下一次商品更新自行建立cache entry
C. Application先寫cache且不寫Aurora；只要關閉eviction，cache便成為永久system of record
D. Application同時查cache與Aurora，永遠採用較快回應；此作法會自動對兩個結果提供transactional consistency

**答案：A**

- **A：** 正確。Cache-aside由application處理miss：回源讀取authoritative database，再填入可丟棄的cache；TTL、negative caching與回源失敗仍需明確設計。
- **B：** 不正確。Cache miss不代表商品不存在；若不查authoritative store，冷啟動或eviction會把有效商品誤判成404。
- **C：** 不正確。關閉eviction不會賦予cache durable transaction、backup或永久保存契約；資料不可只存在可失效的cache。
- **D：** 不正確。競速兩個來源可能回傳stale cache，而且跨Aurora與ElastiCache不會因此自動形成ACID transaction。

**事實查證：** [Cache-aside pattern - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/cache-aside.html)、[ElastiCache best practices and caching strategies - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)

### 練習題 2｜SAA → SAP｜Write path、invalidation 與部分失敗

票價服務把價格保存在RDS，cache TTL為30分鐘。營運人員降價後，下一個read必須很快看到新值；RDS成功但cache操作失敗時也不能讓舊價格維持30分鐘。哪個設計最合理？

A. 把TTL延長到24小時，讓cache hit ratio提高；較高hit ratio會自動使資料更新得更快
B. 先提交RDS更新，再刪除或更新對應cache key；對cache失敗使用可重試事件或outbox，並讓read miss從RDS重建
C. 只更新cache，等entry自然evict後再由背景工作把最後值寫入RDS
D. 同一request依序寫RDS與cache即可；兩個managed services會自動成為單一跨服務ACID transaction

**答案：B**

- **A：** 不正確。延長TTL會擴大stale window；hit ratio與資料新鮮度是不同指標。
- **B：** 正確。RDS仍擁有真相，寫入後invalidate或更新cache可縮短舊值時間；outbox或可靠重試處理RDS已成功但cache步驟失敗的dual-write窗口。
- **C：** 不正確。只寫cache會讓durable source落後，cache故障或eviction時可能永久遺失已接受的價格變更。
- **D：** 不正確。RDS與ElastiCache之間沒有自動分散式transaction；第二步失敗必須由application補償或重試。

**事實查證：** [Caching challenges and strategies - Database Caching Strategies Using Redis](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-challenges-and-strategies.html)、[ElastiCache best practices and caching strategies - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)

### 練習題 3｜SAP｜Cache stampede、TTL jitter 與 request coalescing

活動頁面有20,000個熱門cache keys，全部在整點以相同TTL到期。午夜後數萬requests同時miss，Aurora CPU在幾秒內耗盡；單一cache node仍有大量記憶體。哪個修正最直接處理根因？

A. 讓clients在miss後無上限立即重試，直到其中一次在cache命中
B. 關閉所有eviction policy；只要entry不能被evict，任何到期時間也不會生效
C. 對TTL加入jitter，對同一key採single-flight/request coalescing，必要時預熱並限制同時回源數量
D. 只把cache node記憶體加倍；更多記憶體會把所有相同的expiration timestamps自動打散

**答案：C**

- **A：** 不正確。同步重試會放大miss storm與origin負載，還可能造成正回饋式故障。
- **B：** 不正確。Eviction與TTL expiration是不同機制；禁止memory eviction不會取消已設定的到期時間。
- **C：** 正確。Jitter避免大量keys同時失效，single-flight讓同key只有一個回源工作，其餘等待或使用受控stale值，直接限制database fan-out。
- **D：** 不正確。容量擴充可減少memory pressure，卻不會改變所有keys在同一秒到期的同步行為。

**事實查證：** [Caching challenges and strategies - Database Caching Strategies Using Redis](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-challenges-and-strategies.html)、[ElastiCache best practices and caching strategies - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)

### 練習題 4｜SAA → SAP｜Disposable cache 與 durable business state

架構師同時設計兩種state：登入session遺失後使用者可重新登入；購物車已接受的商品與折扣則不得因cache failover、flush或eviction而消失。哪個state ownership設計正確？

A. 兩者都只放單節點Memcached，並把TTL設為零；沒有TTL就等同永久backup
B. 兩者都只放有replica的ElastiCache；Multi-AZ會保存所有歷史版本並提供任意時間點恢復
C. 購物車只寫cache snapshot；snapshot會同步包含每筆已確認write，因此可承諾零RPO
D. 把可重建session視為cacheable state；把購物車寫入durable database並可選擇cache其projection，另行設計backup與recovery

**答案：D**

- **A：** 不正確。TTL為零不會把Memcached變成durable store；node replacement、flush與故障仍可失去資料。
- **B：** 不正確。Multi-AZ與replica改善availability，但不等同永久backup、歷史版本保存或任意PITR。
- **C：** 不正確。週期性snapshot不是每筆write同步commit的零RPO機制，且cache仍有eviction與恢復語意限制。
- **D：** 正確。先區分可重建projection與不可遺失business state；後者由具明確durability/backup契約的database擁有，cache只負責加速。

**事實查證：** [ElastiCache best practices and caching strategies - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)、[AWS Database category iconDatabases - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)

### 練習題 5｜SAA｜Valkey/Redis OSS 與 Memcached engine 選型

Workload A需要sorted sets維護即時排行榜、pub/sub通知、replicas與automatic failover。Workload B只快取獨立HTML fragments，應用已支援一致性hash，並重視簡單multi-threaded cache。哪個mapping最合理？

A. A使用ElastiCache for Valkey或Redis OSS；B可評估ElastiCache for Memcached
B. A使用Memcached，因它原生提供sorted sets、streams與replication groups；B使用Neptune
C. A與B必須使用完全相同engine，因ElastiCache所有engines具有相同data structures與persistence contract
D. A使用CloudFront的Redis protocol endpoint；B使用DAX快取任意HTML key

**答案：A**

- **A：** 正確。Valkey/Redis OSS提供較豐富data structures與replication/cluster能力；Memcached適合較單純、multi-threaded且可丟棄的key-value caching。
- **B：** 不正確。Memcached不提供Redis-family的sorted sets、streams或相同replication-group failover模型。
- **C：** 不正確。Engines的資料結構、threading、replication與persistence能力不同，必須按功能與failure model選擇。
- **D：** 不正確。CloudFront快取HTTP內容而不暴露Redis protocol；DAX則是DynamoDB專用cache。

**事實查證：** [Comparing node-based Valkey, Memcached, and Redis OSS clusters - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html)

### 練習題 6｜SAA → SAP｜Cluster mode sharding 與 hot key

Valkey cluster mode已把keyspace分成12個shards，aggregate CPU只有35%，但`TENANT#mega:dashboard`承受45%的writes，使所在shard持續throttle。其他shards與replicas都很閒。哪個變更最直接？

A. 只增加該shard的read replicas；replicas會平均接收primary的writes並消除write hot key
B. 把單一logical key依可聚合維度分片或重新設計access pattern，讓writes落到多個hash slots，並讓client保持cluster-aware
C. 把12個shards合併成1個；所有writes集中後會自動取得12倍單key吞吐
D. 增加Multi-AZ數量；每新增一個AZ，單一key都會自動複製成可同時寫入的primary

**答案：B**

- **A：** 不正確。Read replicas承接reads與HA，不會把同一primary key的writes分散到多個shards。
- **B：** 正確。Cluster mode依hash slot分配keys；單一hot key仍集中一個shard，必須拆分logical key或改變access pattern才能分散write load。
- **C：** 不正確。減少shards會降低平行容量，且不會讓單一key跨多個primary自動分割。
- **D：** 不正確。AZ placement改善failure isolation；它不改變hash slot ownership或建立multi-primary寫入。

**事實查證：** [Scaling ElastiCache - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling.html)

### 練習題 7｜SAA → SAP｜Replication、Multi-AZ failover 與 reconnect

Node-based Valkey replication group的primary位於AZ-a，replicas分布於AZ-b與AZ-c，並已啟用Multi-AZ automatic failover。Chaos test終止primary後，DNS已指向新primary，但部分clients仍卡在舊TCP connection。哪個修正最完整？

A. 改連單一node IP並永久cache DNS；固定IP可確保promotion後原connection自動搬移
B. 停用replicas並只保留每日snapshot；snapshot可在primary故障時立即接管live traffic
C. 使用適當的primary/configuration endpoint，設定有限timeout、重試與重新解析/reconnect，並在測試中驗證failover窗口
D. 要求ElastiCache在failover時保留每條既有TCP session；managed service會把socket無縫移到另一個AZ

**答案：C**

- **A：** 不正確。Node IP可能隨replacement或promotion改變，長期cache DNS會延長連到失效節點的時間。
- **B：** 不正確。Snapshot是恢復工具而非同步standby，不能取代跨AZ replica與automatic failover。
- **C：** 正確。Endpoint負責指向新角色，但既有socket不會自動遷移；client仍需合理DNS、timeout、backoff與reconnect行為。
- **D：** 不正確。Failover會中斷部分connections；應用必須把斷線與重連視為正常failure path。

**事實查證：** [Minimizing downtime in ElastiCache by using Multi-AZ with Valkey and Redis OSS - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/AutoFailover.html)

### 練習題 8｜SAP｜ElastiCache Serverless 與 node-based trade-off

團隊比較兩個cache。A是流量難預測的新服務，希望避免選node type、shard數與replica topology；B有穩定高流量、特定parameter需求，並希望精確控制shards與maintenance。選擇兩項正確評估。

A. Serverless沒有任何service quota、最大使用量或成本風險，因此不必設定監控與預算
B. Node-based cluster部署後不能online scaling，唯一擴容方法是建立新AWS帳號
C. Serverless會分析application business rules並自動修復cache invalidation與hot-key設計錯誤
D. A可評估Serverless，讓服務管理capacity與scaling，但仍需核對支援功能、限制、latency與用量成本
E. B可評估node-based，以取得node、shard、replica與parameter控制，並以量測結果規劃steady-state成本

**答案：D、E**

- **A：** 不正確。Serverless減少capacity planning，但仍有配額、用量計費與監控需求，不能視為無限資源。
- **B：** 不正確。Node-based支援多種scale操作；是否online及限制要依engine、cluster mode與操作類型判斷。
- **C：** 不正確。Managed scaling不會理解應用的cache key、TTL、invalidation或stampede correctness。
- **D：** 正確。不可預測workload是Serverless的合理候選，但架構師仍須驗證feature coverage、quota、性能與成本模型。
- **E：** 正確。固定且需要細緻topology/parameter控制的workload可選node-based，再以metrics與load test決定容量。

**事實查證：** [Choosing between deployment options - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.deployment.html)、[Scaling ElastiCache - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling.html)

### 練習題 9｜SAP｜ElastiCache network、TLS 與 command authorization

Private ECS tasks要連ElastiCache for Valkey。只有checkout與support兩種application identities可連線；checkout可讀寫`cart:*`，support只能讀，security要求in-transit與at-rest encryption。選擇兩項必要設計。

A. 把cache放在合適VPC subnets，以security groups只允許application SG到cache port，並啟用所需TLS與at-rest encryption
B. 只要cache沒有public IP，就不需要任何authentication、command ACL或credential rotation
C. 使用Valkey/Redis OSS users與RBAC user groups限制commands/key patterns，並安全管理與輪替credentials；不能把SG當成command authorization
D. 在EC2 security group中列出允許的Redis commands；security group會解析RESP並阻擋`SET`
E. 建立public endpoint並使用很長的共用password；public reachability比private network更符合least privilege

**答案：A、C**

- **A：** 正確。VPC/subnet與SG限制network reachability，TLS及at-rest encryption處理傳輸與儲存保護，是不同層的控制。
- **B：** 不正確。Private reachability不等於application authorization；若多角色有不同command權限，仍需authentication/RBAC與credential lifecycle。
- **C：** 正確。RBAC可把users映射到允許的commands與key patterns；network policy與cache-layer authorization應共同使用。
- **D：** 不正確。Security groups依protocol/port與來源判斷，不解析Valkey command或key namespace。
- **E：** 不正確。擴大網路暴露面違反題目的private與least-privilege要求，共用credential也無法區分角色。

**事實查證：** [Security in Amazon ElastiCache - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/security.html)

### 練習題 10｜SAA → SAP｜CloudFront、ElastiCache 與 MemoryDB 邊界

零售平台同時有三個需求：全球快取HTTP商品頁、讓應用以Valkey資料結構保存可重建的session與rate-limit counters，以及建立可作primary database的durable Valkey-compatible inventory store。選擇兩項正確敘述。

A. CloudFront會忽略headers、cookies與query strings，所有request永遠使用相同cache key，因此不必設計cache policy
B. 商品頁可用CloudFront，並依內容差異設計cache key、TTL、invalidation與origin行為；它快取的是HTTP responses，不是應用內的Valkey資料結構
C. 把DAX endpoint設為CloudFront origin即可在edge執行Valkey sorted-set與pub/sub commands
D. ElastiCache只要開啟snapshot，就自動成為不可遺失任何acknowledged write的system of record，無須定義cache miss或重建流程
E. 可重建的session與rate-limit state可評估ElastiCache；若inventory state本身是durable primary database，則應另評估MemoryDB並驗證其一致性、備份與故障契約

**答案：B、E**

- **A：** 不正確。CloudFront cache policy決定哪些headers、cookies與query strings進入cache key；把會改變response的輸入漏掉，可能把錯誤內容分享給其他使用者，全部納入又可能降低hit ratio。
- **B：** 正確。CloudFront位於HTTP delivery path，設計重點是cache key、TTL、失效與origin contract；它不提供Valkey/Redis command protocol。
- **C：** 不正確。DAX是DynamoDB API-compatible accelerator，CloudFront origin則必須是可用的HTTP來源；兩者都不會因此變成Valkey command server。
- **D：** 不正確。Snapshot與replica改善cache恢復，不會自動改寫application對state ownership的假設；若資料不可重建，就不能只因開啟snapshot而把cache當成唯一真相來源。
- **E：** 正確。ElastiCache適合application-managed cache與可重建state；MemoryDB定位為durable、Valkey-compatible primary database。選擇時仍要驗證資料持久性、讀寫一致性、備份與failover是否符合inventory契約。

**事實查證：** [What is Amazon CloudFront? - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)、[ElastiCache best practices and caching strategies - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)、[What is MemoryDB - Amazon MemoryDB](https://docs.aws.amazon.com/memorydb/latest/devguide/what-is-memorydb.html)、[In-memory acceleration with DynamoDB Accelerator (DAX) - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Mem…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Cache可降低origin負載與延遲，但引入staleness、eviction與stampede。」，所以「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」能直接滿足它；若constraint改成「CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」。替代方案「CloudFront處理edge HTTP cache，DAX處理DynamoDB API，不是所有cache都可互換。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「TTL同時到期造成thundering herd，或把cache當唯一資料來源。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Cache可降低origin負載與延遲，但引入staleness、eviction與stampede。」，排除會導致「TTL同時到期造成thundering herd，或把cache當唯一資料來源。」的選項，再選「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Cache-aside適合一般讀取；write-through保持較新資料；Redis支援複雜結構，Memcached偏簡單分散cache。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「cache is a disposable projection of authoritative state」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 49 章　Redshift、Athena、Glue 與 Lake Formation

分析平台要區分warehouse、query-on-object、catalog/ETL與data governance。

## 跟著一筆資料走：先從故事開始

故事從一個看似簡單的需求開始：公司資料都在S3，分析師偶爾查詢，BI dashboard每天高頻聚合。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：分析平台要區分warehouse、query-on-object、catalog/ETL與data governance。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon Redshift會是本章的主要角色，Amazon Athena則幫我們看清邊界。方向是「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：公司資料都在S3，分析師偶爾查詢，BI dashboard每天高頻聚合。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon Redshift：authoritative或主要資料路徑]
          │ 提供columnar MPP data warehouse供大型分析與BI。
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Amazon Athena：以serverless SQL直接查詢S3資料。
  · AWS Glue：提供Data Catalog、crawler與serverless ETL/integration job…
  · AWS Lake Formation：在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。

失敗時先找：讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon Redshift有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Redshift和Amazon Athena並不是兩個任意的產品名稱。前者適合本章，是因為「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」直接回應了眼前的問題；後者描述的「EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate storage, catalog, compute, and governance planes」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 |
| Amazon Athena | 以serverless SQL直接查詢S3資料。 | Query engine依Glue Catalog schema讀取objects；按掃描bytes計費，partition/columnar format決定成本。 |
| AWS Glue | 提供Data Catalog、crawler與serverless ETL/integration jobs。 | Crawler推斷S3/JDBC schema寫入Catalog；Spark/Ray/Python jobs讀取、轉換與寫出資料。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 |

## 把全圖套進一個具體案例

**場景：** 公司資料都在S3，分析師偶爾查詢，BI dashboard每天高頻聚合。

1. 故事的起點：公司資料都在S3，分析師偶爾查詢，BI dashboard每天高頻聚合。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Redshift負責「提供columnar MPP data warehouse供大型分析與BI。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Athena、AWS Glue、AWS Lake Formation各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Redshift

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：分析平台要區分warehouse、query-on-object、catalog/ETL與data governance。
- **具體例子／邊界：** 在「公司資料都在S3，分析師偶爾查詢，BI dashboard每天高頻聚合。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Athena

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate storage, catalog, compute, and governance planes。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### data warehouse

為重複分析、聚合與joins最佳化的columnar analytical database，不是一般低延遲OLTP transaction store。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### ETL

Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon Redshift

- **功用：** 提供columnar MPP data warehouse供大型分析與BI。
- **底層機制：** Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。
- **關鍵設定：** provisioned/serverless、node/RPU、distribution style/key、sort key、WLM、Spectrum與materialized views。
- **選擇時機：** 重複BI、複雜joins、結構化warehouse與高併發dashboard。
- **替換時機：** 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。

### Amazon Athena

- **功用：** 以serverless SQL直接查詢S3資料。
- **底層機制：** Query engine依Glue Catalog schema讀取objects；按掃描bytes計費，partition/columnar format決定成本。
- **關鍵設定：** workgroup、output location、Glue table、partition projection、Parquet/ORC、compression與result reuse。
- **選擇時機：** ad hoc data lake查詢、log investigation與低營運分析。
- **替換時機：** 持續高頻warehouse workload用Redshift；ETL transformation由Glue/EMR。

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

## 考前與實作時再查：設定操作手冊

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

### Amazon Athena：逐項設定說明

#### `workgroup`

- **控制什麼：** `workgroup`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `output location`

- **控制什麼：** `output location`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `Glue table`

- **控制什麼：** `Glue table`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「ad hoc data lake查詢、log investigation與低營運分析。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Athena的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `partition projection`

- **控制什麼：** `partition projection`設定Amazon Athena的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「ad hoc data lake查詢、log investigation與低營運分析。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `Parquet/ORC`

- **控制什麼：** `Parquet/ORC`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「ad hoc data lake查詢、log investigation與低營運分析。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Athena依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

#### `compression`

- **控制什麼：** `compression`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「ad hoc data lake查詢、log investigation與低營運分析。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Athena依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

#### `result reuse`

- **控制什麼：** `result reuse`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「ad hoc data lake查詢、log investigation與低營運分析。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Athena依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

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

## 讀到這裡，請用自己的話說一次

1. Amazon Redshift的責任：提供columnar MPP data warehouse供大型分析與BI。
2. 底層機制：Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。
3. 第一個要看的設定：provisioned/serverless、node/RPU、distribution style/key、sort key、WLM、Spectrum與materialized views。
4. 選擇邏輯：穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。
5. 不要混淆：Amazon Athena的責任是「以serverless SQL直接查詢S3資料。」；它不會自動取代Amazon Redshift。
6. 替換訊號：偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。
7. 最常見錯法：讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。
8. 可移植原則：separate storage, catalog, compute, and governance planes。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 | 重複BI、複雜joins、結構化warehouse與高併發dashboard。 | 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。 |
| Amazon Athena | 以serverless SQL直接查詢S3資料。 | Query engine依Glue Catalog schema讀取objects；按掃描bytes計費，partition/columnar format決定成本。 | ad hoc data lake查詢、log investigation與低營運分析。 | 持續高頻warehouse workload用Redshift；ETL transformation由Glue/EMR。 |
| AWS Glue | 提供Data Catalog、crawler與serverless ETL/integration jobs。 | Crawler推斷S3/JDBC schema寫入Catalog；Spark/Ray/Python jobs讀取、轉換與寫出資料。 | 建立共享catalog、batch ETL、schema discovery與資料品質。 | 只是SQL查詢用Athena；需要完整Spark cluster tuning可選EMR。 |
| AWS Lake Formation | 在S3 data lake上集中管理資料註冊、table/column/row權限與跨帳號分享。 | 以Glue Catalog metadata和LF permissions攔截整合服務存取，可使用LF-tags做ABAC。 | 多團隊analytics需要細粒度資料治理而非大量S3 policy。 | 一般object-level app access仍用IAM/S3 policies/Access Points。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。 | 只有當題目條件明確改變時才可能合理。 | 讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。」之間做選擇。
- 認得常考設定：provisioned/serverless、node/RPU、distribution style/key、sort key、WLM、Spectrum與materialized views。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls；SAA-3.3 Determine high-performing database solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。
- 對應官方tasks：SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Athena 與 Redshift workload selection

資料平台有兩種查詢：稽核人員每月臨時查一次S3中的歷史Parquet；營運dashboard每天數千次執行固定joins與aggregations，要求穩定低延遲與workload isolation。哪個設計最合理？

A. 兩者都使用RDS writer執行大型analytics；OLTP與多年scan共用同一connection pool可得到最佳隔離
B. 臨時S3查詢使用Athena；持續且高併發的BI workload使用Redshift，必要時讓兩者共享catalog/lake資料
C. Athena必須先部署常駐EC2 query cluster，因此只適合固定dashboard；Redshift只能查S3且不能存warehouse tables
D. 兩者都使用DynamoDB Scan；FilterExpression會在計費前排除不需要的columns與rows

**答案：B**

- **A：** 不正確。把大型scan與OLTP writer混用會競爭CPU、I/O與connections，且不符合分析服務的執行模型。
- **B：** 正確。Athena適合serverless query-on-S3與偶發查詢；Redshift適合持續、高性能analytics及可調workload management，兩者可互補。
- **C：** 不正確。Athena不要求使用者管理常駐cluster；Redshift既能存warehouse tables，也能透過外部資料能力查詢S3。
- **D：** 不正確。DynamoDB Scan不是columnar SQL analytics engine，FilterExpression也不會把已讀取容量變成免費。

**事實查證：** [AWS Analytics category iconAnalytics - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/analytics.html)

### 練習題 2｜SAA｜Athena partition pruning 與 scanned bytes cost

Athena每天查詢20 TB gzip JSON logs，幾乎所有SQL都只取5個欄位並以`event_date`與`region`過濾。查詢仍掃描大量bytes，S3中還有數百萬個極小檔案。哪個改善最有效？

A. 移除所有partitions並合併成單一未壓縮CSV；Athena會因只有一個object而只掃需要的rows
B. 只把每個SQL加上`LIMIT 10`；LIMIT保證底層最多讀10 rows，因此scan charge接近零
C. 將資料轉為壓縮Parquet/ORC，依常用date/region predicates合理partition，compact tiny files並確認partition pruning
D. 提高Glue crawler執行頻率；crawler會自動把既有JSON objects原地重寫為Parquet

**答案：C**

- **A：** 不正確。未壓縮row format會增加讀取bytes，單一巨大檔案也可能降低平行度，且無法利用partition pruning。
- **B：** 不正確。LIMIT限制返回rows，不必然限制scan範圍；若格式與partition不能prune，仍可能掃描大量資料。
- **C：** 正確。Columnar format與compression減少需要讀取的columns/bytes，partition pruning縮小資料範圍，合併tiny files降低metadata與open成本。
- **D：** 不正確。Crawler發現schema與partitions，不會替ETL job轉換或重寫source objects。

**事實查證：** [Optimize data - Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/performance-tuning-data-optimization-techniques.html)、[Data discovery and cataloging in AWS Glue - AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)

### 練習題 3｜SAA → SAP｜Athena workgroup cost 與 result governance

Finance與Data Science共用Athena。Finance query results必須寫入自己的加密S3 prefix；Data Science的單一query掃描量要有硬性上限，且兩隊需分開查看usage metrics。應如何配置？

A. 建立兩個Glue databases；Data Catalog會自動強制query result位置、KMS encryption與bytes-scanned cutoff
B. 只建立AWS Budget；Budget會在每個Athena query開始前同步拒絕超過bytes門檻的SQL
C. 使用同一workgroup並讓每位使用者自行輸入result location；client settings天然不可被修改
D. 為兩隊建立Athena workgroups，強制各自result location與encryption，設定data-usage controls並以IAM限制使用

**答案：D**

- **A：** 不正確。Data Catalog保存metadata，不是workgroup級query result與cost-control邊界。
- **B：** 不正確。Budget適合成本通知與治理，但不是Athena單一query執行前的bytes-scanned enforcement機制。
- **C：** 不正確。依賴client自行設定無法保證隔離；workgroup可override client-side settings並集中政策。
- **D：** 正確。Workgroups可分離queries與metrics，強制result S3位置/encryption，並使用per-query或workgroup usage controls管理掃描量。

**事實查證：** [Use workgroups to control query access and costs - Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/workgroups-manage-queries-control-costs.html)

### 練習題 4｜SAA｜Glue Catalog、Crawler 與 ETL job 分工

S3 `raw/`每天收到schema略有演進的JSON。Athena需要可發現的table metadata，而`curated/`必須產生partitioned Parquet並標準化欄位型別。哪個Glue流程正確？

A. Crawler發現或更新raw schema與partitions到Data Catalog；Glue ETL job讀raw、轉換後把Parquet寫到curated並更新其catalog metadata
B. 只建立Data Catalog table；Catalog會保存完整JSON bytes並自動輸出Parquet objects
C. Crawler同時執行所有資料清洗與格式轉換，所以不需要任何ETL job或其他transform process
D. Glue ETL job只管理IAM policies，不能讀寫S3 datasets或改變資料格式

**答案：A**

- **A：** 正確。Crawler與Catalog處理schema/partition metadata；ETL job負責實際讀取、清洗、型別處理與columnar輸出。
- **B：** 不正確。Data Catalog保存metadata而非dataset bytes，也不會自行產生新的S3 data files。
- **C：** 不正確。Crawler的主要工作是分類與填入metadata，資料轉換要由ETL job或其他processing service執行。
- **D：** 不正確。Glue ETL jobs可執行資料抽取、轉換與載入，不只處理access policy。

**事實查證：** [Data discovery and cataloging in AWS Glue - AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)

### 練習題 5｜SAP｜Lake Formation、IAM、S3 與 KMS permission layers

Analyst role只能透過Athena查詢customer table中的三個非敏感columns。安全測試發現該role仍可用S3 API直接下載`raw/customers/`中的完整Parquet，繞過column grants。哪個修正最完整？

A. 只新增更多Lake Formation column grants；任何既有`S3:GetObject *`會被Lake Formation自動覆寫
B. 把raw bucket改成public-read，再依Athena view隱藏敏感columns
C. 保留Lake Formation細粒度grants，同時移除analyst的broad direct S3 access，正確註冊data location並配置IAM、bucket policy與KMS/service role
D. 只修改Glue table owner；table owner可自動撤銷其他帳號所有S3與KMS permissions

**答案：C**

- **A：** 不正確。Lake Formation grants不會神奇撤銷獨立的broad S3 object permission；direct path必須一併治理。
- **B：** 不正確。Public-read會擴大資料暴露面，Athena view也不能阻止直接S3下載。
- **C：** 正確。Catalog/data permissions與底層IAM、S3、KMS及registered-location roles共同形成授權鏈，需關閉可繞過治理的直接存取。
- **D：** 不正確。Glue metadata ownership不會自動修改bucket policy、identity policy或KMS key policy。

**事實查證：** [Overview of Lake Formation permissions - AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-overview.html)

### 練習題 6｜SAP｜Lake Formation cross-account sharing

Producer account集中管理data lake。Consumer account只能查詢`sales_curated`中兩張tables，producer必須能中央撤銷；資料以producer的customer managed KMS key加密。哪個方案最合適？

A. 把S3 bucket設public-read並只分享Glue database名稱；public object不再需要KMS authorization
B. 以Lake Formation cross-account grants分享指定resources，consumer建立resource links或依支援模式存取，並配置IAM、RAM/Organizations及S3/KMS權限
C. 只把Glue table JSON複製到consumer；catalog metadata會自動傳送underlying objects與`kms:Decrypt`
D. 讓consumer取得producer account AdministratorAccess；之後靠命名慣例要求只查兩張tables

**答案：B**

- **A：** 不正確。Public-read破壞中央least privilege，且SSE-KMS objects仍有KMS授權邊界。
- **B：** 正確。Cross-account sharing需要catalog grants/resource links等治理構件，並同時滿足data location、IAM、S3與KMS authorization。
- **C：** 不正確。Metadata sharing不等於資料或KMS key access，underlying S3 permissions仍必須明確授予。
- **D：** 不正確。帳號級管理權遠超需求，也無法用命名慣例實作可稽核的table-level限制。

**事實查證：** [Cross-account data sharing in Lake Formation - AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html)、[Overview of Lake Formation permissions - AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-overview.html)

### 練習題 7｜SAA → SAP｜Redshift distribution、redistribution 與 skew

Redshift有8 TB `sales_fact`與40 GB `customer_dim`，最昂貴query持續以高基數`customer_id` join；目前兩表都以低基數`country_code`作DISTKEY，少數nodes儲存大部分rows且query plan大量redistribute。哪個調整最合理？

A. 把8 TB fact改成ALL distribution；每個node複製完整fact可消除所有storage與load成本
B. 維持country_code並只增加sort key；sort key會自動重新平衡distribution skew
C. 把每張table都設EVEN且忽略join plan；EVEN保證所有joins永遠不需network movement
D. 根據join與資料分布評估AUTO或以customer_id co-locate相關rows，避免low-cardinality skew，並用system views/query plan驗證

**答案：D**

- **A：** 不正確。ALL適合較小、較少更新的dimension候選；複製大型fact會大幅增加storage、load與maintenance成本。
- **B：** 不正確。Sort key影響block ordering與scan skipping，不會改變rows在nodes間的distribution。
- **C：** 不正確。EVEN可減少某些skew，但常用join仍可能需要redistribution，不能跳過query-plan驗證。
- **D：** 正確。Distribution選擇要兼顧join co-location與key cardinality；AUTO或合理KEY需用實際skew與data-movement metrics驗證。

**事實查證：** [Distribution styles - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_choosing_dist_sort.html)

### 練習題 8｜SAA → SAP｜Redshift sort key、zone maps 與 table health

`events`保存五年資料，dashboard主要查單一tenant最近7天，偶爾按時間順序輸出。現在每次都掃描大量blocks。選擇兩項有助於降低不必要block scan的設計判斷。

A. 依實際predicates評估以event time及可能的tenant相關strategy排序，使zone maps能跳過不相關blocks
B. 把sort key當成PRIMARY KEY constraint；Redshift會以它拒絕所有duplicate events並提供OLTP locking
C. 對table每個column都建立獨立sort key；sort columns越多必然越快且沒有load成本
D. 只增加read replicas；replica會重新排列primary table blocks而不需要任何table maintenance或statistics
E. 維持statistics與table physical health，並用query plan與scan metrics驗證sort strategy是否符合常用filter

**答案：A、E**

- **A：** 正確。與常用range/equality predicates相符的sort order可讓zone maps排除不相關blocks，實際欄位順序需按workload驗證。
- **B：** 不正確。Sort key是physical data layout工具，不等同由engine強制唯一性的OLTP primary key。
- **C：** 不正確。Sort設計有排序、load與maintenance trade-off，不能假設增加所有columns沒有代價。
- **D：** 不正確。額外compute不會自動修正不合適的physical sort order或過期statistics。
- **E：** 正確。Sort效果依資料分布與table health而變，應以statistics、maintenance狀態與query metrics閉環驗證。

**事實查證：** [Sort keys - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/t_Sorting_data.html)

### 練習題 9｜SAP｜Redshift WLM、concurrency scaling 與 Serverless cost

每小時ETL query會佔用warehouse 25分鐘，期間短dashboard queries在queue等待；月底又有不可預測的查詢尖峰。選擇兩項合理的改善方向。

A. 把所有users與queries放入同一最高priority queue；同一priority會保證short query先完成
B. 以WLM、query priorities或適當queues隔離ETL與interactive workloads，先量測queue time、CPU、I/O與skew
C. 視尖峰模式評估concurrency scaling或Redshift Serverless，並設定usage/cost controls而非假設容量與費用無上限
D. 只增加sort columns即可完全取代workload queues與concurrency management
E. 停用所有query monitoring；沒有監控overhead後，warehouse會自動辨識business priority

**答案：B、C**

- **A：** 不正確。同一queue/priority可能讓長查詢繼續阻塞短查詢，不能提供題目要求的workload isolation。
- **B：** 正確。WLM與priority可按workload class管理queue與resource allocation，並應由實際瓶頸metrics驅動。
- **C：** 正確。Concurrency scaling或Serverless可處理特定burst，但仍需了解適用條件、RPU/capacity與usage cost。
- **D：** 不正確。Physical sort可改善部分scan，卻不能取代queue、priority與併發資源管理。
- **E：** 不正確。缺少監控會失去queue與resource evidence，服務不會自行理解組織優先級。

**事實查證：** [Workload management - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_workload_mngmt_classification.html)、[Amazon Redshift Serverless feature overview - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-considerations.html)

### 練習題 10｜SAP｜Redshift snapshots、encryption 與 cross-Region recovery

一個KMS-encrypted provisioned Redshift cluster要求保留每日restore points 35天，Region災難時從另一Region恢復，並每季演練RTO。選擇兩項必要做法。

A. 設定適當automated/manual snapshot retention與cross-Region snapshot copy，並確保目的Region可使用所需KMS key/material
B. 只建立materialized view；它會包含cluster users、permissions與所有tables，可直接作完整DR backup
C. 建立Spectrum external table後，所有外部S3資料會自動複製進cluster snapshot且不需另外保護S3
D. 只增加compute nodes；node數量會自動建立另一Region可promotion的同步cluster
E. 定期在目的Regionrestore並驗證schema、permissions、dependencies與client cutover，將觀察結果與RPO/RTO比較

**答案：A、E**

- **A：** 正確。Retention與cross-Region copy建立可用restore artifacts；encrypted recovery還必須規劃目的端KMS access。
- **B：** 不正確。Materialized view是查詢加速物件，不是包含完整cluster metadata與所有資料的災難備份。
- **C：** 不正確。External table指向S3資料，cluster snapshot不會替代S3本身的protection與replication策略。
- **D：** 不正確。Scale compute不會自動建立跨Region同步DR副本或可用snapshot。
- **E：** 正確。只有實際restore與cutover演練才能量測RTO並發現IAM、KMS、network及downstream dependency缺口。

**事實查證：** [Amazon Redshift snapshots and backups - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ET…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「分析平台要區分warehouse、query-on-object、catalog/ETL與data governance。」，所以「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」能直接滿足它；若constraint改成「EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」。替代方案「EMR適合需要Spark/Hadoop控制的處理，QuickSight提供BI visualization。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「分析平台要區分warehouse、query-on-object、catalog/ETL與data governance。」，排除會導致「讓Athena掃描未分區raw JSON導致慢與貴，或同時維護多個不一致catalog。」的選項，再選「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAA-3.3 Determine high-performing database solutions；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.3 Design cost-optimized database solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「穩定高效BI用Redshift；ad hoc S3 SQL用Athena；Glue管理catalog/ETL；Lake Formation治理lake權限。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate storage, catalog, compute, and governance planes」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 50 章　Kinesis、MSK 與 Streaming Pipeline

Streaming需要定義ordering、retention、partition、consumer、replay與backpressure。

## 跟著一筆資料走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：IoT事件需多個獨立consumer即時處理並可回放24小時，既有團隊熟悉Kafka。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：Streaming需要定義ordering、retention、partition、consumer、replay與backpressure。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon Kinesis Data Streams負責主要工作，Amazon MSK提醒我們答案不是永遠固定。本章會走向「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：IoT事件需多個獨立consumer即時處理並可回放24小時，既有團隊熟悉Kafka。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon Kinesis Data Streams：authoritative或主要資料路徑]
          │ 保存可重播、按partition key排序的即時event log。
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Amazon MSK：提供managed Apache Kafka brokers與control plane。
  · Amazon Data Firehose：把streaming records以managed buffering、可選transform後送到S3…

失敗時先找：以單一partition key形成hot shard，或consumer lag增加時只擴producer。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon Kinesis Data Streams有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Kinesis Data Streams和Amazon MSK並不是兩個任意的產品名稱。前者適合本章，是因為「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」直接回應了眼前的問題；後者描述的「SQS適合work queue而非保留可供多consumer replay的ordered log。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：以單一partition key形成hot shard，或consumer lag增加時只擴producer。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「a stream is a replayable ordered log partitioned by key」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Kinesis Data Streams | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 |
| Amazon MSK | 提供managed Apache Kafka brokers與control plane。 | Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。 |
| Amazon Data Firehose | 把streaming records以managed buffering、可選transform後送到S3/Redshift/OpenSearch等destination。 | Service依buffer size/time成批，呼叫Lambda轉換並管理retry與backup。 |

## 把全圖套進一個具體案例

**場景：** IoT事件需多個獨立consumer即時處理並可回放24小時，既有團隊熟悉Kafka。

1. 故事的起點：IoT事件需多個獨立consumer即時處理並可回放24小時，既有團隊熟悉Kafka。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Kinesis Data Streams負責「保存可重播、按partition key排序的即時event log。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon MSK、Amazon Data Firehose各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「以單一partition key形成hot shard，或consumer lag增加時只擴producer。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Kinesis Data Streams

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Streaming需要定義ordering、retention、partition、consumer、replay與backpressure。
- **具體例子／邊界：** 在「IoT事件需多個獨立consumer即時處理並可回放24小時，既有團隊熟悉Kafka。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon MSK

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：SQS適合work queue而非保留可供多consumer replay的ordered log。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：以單一partition key形成hot shard，或consumer lag增加時只擴producer。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：a stream is a replayable ordered log partitioned by key。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon Kinesis Data Streams

- **功用：** 保存可重播、按partition key排序的即時event log。
- **底層機制：** Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。
- **關鍵設定：** on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
- **選擇時機：** 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。
- **替換時機：** 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。

### Amazon MSK

- **功用：** 提供managed Apache Kafka brokers與control plane。
- **底層機制：** Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。
- **關鍵設定：** provisioned/serverless、broker type/count、storage、partitions/replication、authentication、configuration與connectors。
- **選擇時機：** 既有Kafka clients、portable ecosystem、長retention與複雜stream processing。
- **替換時機：** 不需要Kafka營運/相容性時Kinesis較AWS-native；simple queue選SQS。

### Amazon Data Firehose

- **功用：** 把streaming records以managed buffering、可選transform後送到S3/Redshift/OpenSearch等destination。
- **底層機制：** Service依buffer size/time成批，呼叫Lambda轉換並管理retry與backup。
- **關鍵設定：** source/destination、buffer hints、compression/format conversion、Lambda transform、retry與backup bucket。
- **選擇時機：** 目標是可靠delivery而非自訂consumer與replay。
- **替換時機：** 需要多consumer、長期replay或per-key處理時用Kinesis Data Streams/MSK。

## 考前與實作時再查：設定操作手冊

### Amazon Kinesis Data Streams：逐項設定說明

#### `on-demand/provisioned mode`

- **控制什麼：** `on-demand/provisioned mode`決定Amazon Kinesis Data Streams如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `shards`

- **控制什麼：** `shards`設定Amazon Kinesis Data Streams的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon Kinesis Data Streams的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `partition key`

- **控制什麼：** `partition key`設定Amazon Kinesis Data Streams的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `enhanced fan-out`

- **控制什麼：** `enhanced fan-out`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon Kinesis Data Streams持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Kinesis Data Streams指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `iterator age`

- **控制什麼：** `iterator age`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon Kinesis Data Streams持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

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

### Amazon Data Firehose：逐項設定說明

#### `source/destination`

- **控制什麼：** `source/destination`指定Amazon Data Firehose讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `buffer hints`

- **控制什麼：** `buffer hints`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「目標是可靠delivery而非自訂consumer與replay。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Data Firehose依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

#### `compression/format conversion`

- **控制什麼：** `compression/format conversion`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「目標是可靠delivery而非自訂consumer與replay。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Data Firehose依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

#### `Lambda transform`

- **控制什麼：** `Lambda transform`把Amazon Data Firehose與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `retry`

- **控制什麼：** `retry`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「目標是可靠delivery而非自訂consumer與replay。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Data Firehose依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `backup bucket`

- **控制什麼：** `backup bucket`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「目標是可靠delivery而非自訂consumer與replay。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Data Firehose依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

## 讀到這裡，請用自己的話說一次

1. Amazon Kinesis Data Streams的責任：保存可重播、按partition key排序的即時event log。
2. 底層機制：Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。
3. 第一個要看的設定：on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
4. 選擇邏輯：AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。
5. 不要混淆：Amazon MSK的責任是「提供managed Apache Kafka brokers與control plane。」；它不會自動取代Amazon Kinesis Data Streams。
6. 替換訊號：單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。
7. 最常見錯法：以單一partition key形成hot shard，或consumer lag增加時只擴producer。
8. 可移植原則：a stream is a replayable ordered log partitioned by key。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Kinesis Data Streams | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 | 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。 | 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。 |
| Amazon MSK | 提供managed Apache Kafka brokers與control plane。 | Topics分partitions並複寫到brokers；consumer groups分攤partitions，保留Kafka protocol/ecosystem。 | 既有Kafka clients、portable ecosystem、長retention與複雜stream processing。 | 不需要Kafka營運/相容性時Kinesis較AWS-native；simple queue選SQS。 |
| Amazon Data Firehose | 把streaming records以managed buffering、可選transform後送到S3/Redshift/OpenSearch等destination。 | Service依buffer size/time成批，呼叫Lambda轉換並管理retry與backup。 | 目標是可靠delivery而非自訂consumer與replay。 | 需要多consumer、長期replay或per-key處理時用Kinesis Data Streams/MSK。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | SQS適合work queue而非保留可供多consumer replay的ordered log。 | 只有當題目條件明確改變時才可能合理。 | 以單一partition key形成hot shard，或consumer lag增加時只擴producer。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「SQS適合work queue而非保留可供多consumer replay的ordered log。」之間做選擇。
- 認得常考設定：on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Replayable stream 與 competing-consumer queue

每筆card transaction event都要由fraud、analytics與archive三個applications各自處理；任一consumer可停機8小時後從自己的位置重播，且不能因另一consumer讀取而刪除event。哪個基礎服務模型最符合？

A. 單一SQS Standard queue；三個consumer競爭同一message即可保證每個application都各收到一次
B. 單一SNS topic且不建立durable subscriptions；SNS本身提供任意offset與多年replay
C. 使用Kinesis Data Streams或MSK等replayable log，讓每個consumer application保存自己的progress
D. 只使用Amazon Data Firehose；每個application都可對delivery stream維護獨立shard checkpoint並任意seek

**答案：C**

- **A：** 不正確。單一queue的consumer通常競爭處理messages，不會讓三個獨立applications各自保留一份replay position。
- **B：** 不正確。SNS可fan out到durable endpoints，但topic本身不是具任意offset與長期replay的stream log。
- **C：** 正確。Replayable stream保留records於retention window，各consumer independently checkpoint，因此彼此不會消耗或刪除對方的資料。
- **D：** 不正確。Firehose定位是managed delivery到destinations，不提供Kinesis/MSK式多application任意offset consumer contract。

**事實查證：** [Amazon Kinesis Data Streams Terminology and concepts - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[Welcome to the Amazon MSK Developer Guide - Amazon Managed Streaming for Apache Kafka](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)

### 練習題 2｜SAA｜Kinesis partition key ordering 與 hot shard

Order events必須對同一`customerId`保持產生順序，不同customers可平行處理。先前所有producers使用固定partition key `orders`，造成單一shard throttle。哪個修正最合適？

A. 以分布足夠的`customerId`作partition key，保留同customer在shard內的順序，並監控少數超大customers是否形成hot shard
B. 為每筆event產生完全隨機partition key；之後Kinesis會跨所有shards提供同customer的全域排序
C. 繼續使用固定`orders` key並增加consumers；consumer數量會把producer writes重新hash到其他shards
D. 由producer自行指定跨shard sequence number；相同sequence number會建立全stream total order

**答案：A**

- **A：** 正確。Partition key經hash決定shard；以customer作key可保存該key內順序並在customers間平行，但仍要注意極端key skew。
- **B：** 不正確。隨機key能改善分布，卻會把同customer events放到不同shards，Kinesis不提供跨shard全域順序。
- **C：** 不正確。增加consumers只影響read path，不會改變producer partition-key routing或hot write shard。
- **D：** 不正確。Sequence numbers由Kinesis分配並在shard範圍內使用，producer不能藉此建立跨shard total order。

**事實查證：** [Amazon Kinesis Data Streams Terminology and concepts - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

### 練習題 3｜SAA → SAP｜Kinesis provisioned 與 on-demand capacity mode

Stream A長期穩定且能準確預測throughput，團隊願意管理shards以控制成本。Stream B是新產品，沒有歷史資料且可能快速成長，希望減少capacity planning。哪個capacity策略合理？

A. 兩者都固定為一個provisioned shard；Kinesis會忽略shard limits並自動吸收所有burst
B. A使用on-demand只因需要ordering；B使用provisioned只因on-demand不支援partition keys
C. 兩者都使用on-demand並停止監控；on-demand保證任何瞬間、任何hot key都不會throttle
D. A可使用provisioned並按records/bytes與consumer需求管理shards；B可使用on-demand，但仍監控scaling behavior、quotas與key distribution

**答案：D**

- **A：** 不正確。Provisioned shard有明確read/write capacity；超過limits或key skew仍會throttle。
- **B：** 不正確。Ordering與partition keys並非兩種capacity mode的區分，兩者都使用stream partitioning語意。
- **C：** 不正確。On-demand減少shard planning但不是無限容量，突然變化、配額與hot keys仍需監控。
- **D：** 正確。可預測workload適合明確shard規劃；未知workload可用on-demand降低操作負擔，但不免除distribution與quota治理。

**事實查證：** [Choose the right mode to stream in - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)、[Amazon Kinesis Data Streams Terminology and concepts - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

### 練習題 4｜SAA → SAP｜Shared throughput 與 enhanced fan-out

同一Kinesis stream有五個低延遲consumers。使用shared-throughput polling後，新增第五個consumer使其他applications的read throughput下降且latency上升；producer與shard write capacity正常。哪個變更最直接？

A. 延長retention；保留更多歷史records會同步提高每個consumer的即時read bandwidth
B. 為需要低延遲與隔離throughput的applications註冊enhanced fan-out consumers，並評估額外consumer成本
C. 增加producer batch size；較大PutRecords batch會為每個consumer建立獨立read pipe
D. 把所有consumers改成同一application name與checkpoint；共享checkpoint可讓每個application仍收到全部records

**答案：B**

- **A：** 不正確。Retention增加可回放時間，不會提高每個shard的consumer read-throughput allocation。
- **B：** 正確。Enhanced fan-out為registered consumers提供dedicated throughput與push delivery，可避免多個低延遲consumers爭用shared read capacity。
- **C：** 不正確。Producer batching優化write API效率，不會建立dedicated consumer throughput。
- **D：** 不正確。同一consumer application內的workers會分攤shards；共用checkpoint反而破壞三方各自完整處理的需求。

**事實查證：** [Develop enhanced fan-out consumers with dedicated throughput - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)

### 練習題 5｜SAA → SAP｜Retention、checkpoint、replay 與 idempotency

KCL consumer因下游故障停止6小時，恢復後要從最後成功位置繼續。每個record可能觸發退款API，重試時不得重複退款。哪個設計最完整？

A. 把retention設為1小時；過期後Kinesis仍會從checkpoint重新產生已刪除records
B. 每讀到record就先把checkpoint移到stream末端，再非同步呼叫退款API；失敗records會由Kinesis自動補回
C. 讓retention覆蓋最長outage/replay window，checkpoint只在受控進度後更新，並以event ID在退款端實作idempotency/deduplication
D. 依賴Kinesis exactly-once side effects；只要使用KCL，外部HTTP API不可能被重複呼叫

**答案：C**

- **A：** 不正確。超過retention的records不可再讀，checkpoint不能復原已從stream移除的資料。
- **B：** 不正確。過早checkpoint可能在side effect失敗時永久跳過record；Kinesis不會自動重建該外部transaction。
- **C：** 正確。Retention保留replay資料，checkpoint管理consumer位置，而idempotency key處理at-least-once processing可能造成的重複side effects。
- **D：** 不正確。KCL協助shard lease與checkpoint，但不對外部付款/退款API提供端到端exactly-once保證。

**事實查證：** [Develop KCL 1.x consumers - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/developing-consumers-with-kcl.html)、[Amazon Kinesis Data Streams Terminology and concepts - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

### 練習題 6｜SAP｜IteratorAge、consumer bottleneck 與 backpressure

Kinesis producers沒有`WriteProvisionedThroughputExceeded`，但consumer的`IteratorAgeMilliseconds`從1秒穩定增加到25分鐘。下游database latency同時升高，部分shards的workers反覆重啟。哪個處置最合理？

A. 先檢查consumer errors、worker/shard parallelism、hot shards與下游latency，增加安全的processing capacity並確保retention覆蓋catch-up時間
B. 只把retention由24小時改為7天；更長retention會自動把consumer恢復到real-time而不增加處理速率
C. 增加producer速率；更多records可讓IteratorAge分母變大，因此lag會下降
D. 停用checkpoint與error handling；consumer略過所有失敗records後即可宣稱資料完整

**答案：A**

- **A：** 正確。Iterator age持續增加表示consumer落後；應定位worker、shard或downstream瓶頸，再擴充可用處理能力並保護replay window。
- **B：** 不正確。延長retention只避免records過早過期，不會提高consumer throughput或修復下游latency。
- **C：** 不正確。增加producer負載會讓落後更嚴重，不能修正read/processing bottleneck。
- **D：** 不正確。停用checkpoint與錯誤處理可能重複或遺失處理，不能以犧牲correctness換取表面低lag。

**事實查證：** [Monitor the Amazon Kinesis Data Streams service with Amazon CloudWatch - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)、[Develop KCL 1.x consumers - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/developing-consumers-with-kcl.html)

### 練習題 7｜SAP｜Kinesis IAM、KMS 與 network boundaries

Producer role只能寫入一個Kinesis stream，consumer role只能讀該stream；stream使用customer managed KMS key，traffic需走核准private path。哪個authorization設計最完整？

A. 只在KMS key policy允許兩個roles；KMS Allow會自動授予所有Kinesis data-plane actions
B. 只建立interface VPC endpoint；任何能到endpoint的principal都會自動取得stream讀寫權
C. 給兩個roles `kinesis:*`與`Resource:*`；之後以application code避免越權
D. 分別授予最小Put與read actions到指定stream ARN，配置KMS key使用權及TLS/VPC endpoint policies，並保留Kinesis IAM authorization

**答案：D**

- **A：** 不正確。KMS authorization只控制key usage，不取代Kinesis service action與resource permissions。
- **B：** 不正確。Private endpoint限制network path但不授予data-plane access，endpoint policy與IAM都需評估。
- **C：** 不正確。Broad wildcard違反least privilege，也不能靠application convention形成可稽核的service-side control。
- **D：** 正確。Stream IAM、KMS key policy/grants與network controls是獨立層；producer與consumer actions應按角色及stream ARN分離。

**事實查證：** [Security in Amazon Kinesis Data Streams - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/security.html)

### 練習題 8｜SAA → SAP｜MSK partitions、replication 與 consumer groups

既有Kafka application遷移到MSK。Topic有24 partitions、replication factor 3並跨三個AZ；一個consumer group啟動36個members。選擇兩項正確敘述。

A. 同一consumer group中的36個members都會收到24個partitions的每一筆record，因此每筆自動處理36次
B. Partition決定ordering與consumer parallelism；在同一group內，同一時間一個partition通常只分配給一個member，部分members可能idle
C. Replication factor只增加application parallelism，不影響broker/AZ failure resilience或storage
D. MSK會自動選最佳message key並修復所有hot partitions與schema incompatibility，application不需設計
E. 跨broker/AZ replicas改善availability，但仍需規劃partition keys、retention、lag、client retry與topic configuration

**答案：B、E**

- **A：** 不正確。同一group的members分攤partitions，不是每個member都收到全部records；不同groups才可各自消費完整log。
- **B：** 正確。Partition是ordering與parallelism單位；members超過partitions時，額外members沒有partition可處理。
- **C：** 不正確。Replication factor主要影響durability/availability與storage/network overhead，不直接增加partition processing units。
- **D：** 不正確。Managed brokers不會替application選business key、保證schema compatibility或消除skew。
- **E：** 正確。MSK管理Kafka infrastructure，但topic/partition、consumer lag與client failure behavior仍是架構責任。

**事實查證：** [Welcome to the Amazon MSK Developer Guide - Amazon Managed Streaming for Apache Kafka](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)

### 練習題 9｜SAP｜MSK Provisioned、Serverless 與 Kinesis選型

Workload A已有大量Kafka clients與connectors，要求Kafka protocol compatibility但不想管理brokers。Workload B是新AWS-native telemetry pipeline，團隊不需要Kafka API並希望最少概念負擔。選擇兩項合理評估。

A. A應比較MSK；流量難預測且功能符合時可評估MSK Serverless，需要細緻broker/storage/config控制時比較Provisioned
B. Kinesis暴露原生Kafka broker endpoint，所有Kafka clients與admin tools都可無修改連線
C. B可評估Kinesis Data Streams，依ordering、retention、consumer與capacity需求決定，不必為不存在的Kafka相容需求導入MSK
D. MSK Serverless沒有partition、throughput、feature或quota限制，因此不需要capacity與cost監控
E. 選擇MSK後AWS會管理topics、schema evolution、consumer groups與application lag，團隊不再負責任何stream design

**答案：A、C**

- **A：** 正確。Kafka compatibility是MSK的核心選型因素；Serverless與Provisioned再依控制需求、支援範圍、quota與成本比較。
- **B：** 不正確。Kinesis有自己的API與consumer model，不是可供任意Kafka clients直接連線的Kafka broker。
- **C：** 正確。若不需要Kafka ecosystem，Kinesis可提供較AWS-native的managed stream，但仍要設計partitioning、retention與consumers。
- **D：** 不正確。Serverless降低broker capacity管理，不代表沒有partition/throughput限制、feature邊界或用量成本。
- **E：** 不正確。MSK管理基礎設施，但topic、schema、key、lag與consumer correctness仍由使用者負責。

**事實查證：** [Welcome to the Amazon MSK Developer Guide - Amazon Managed Streaming for Apache Kafka](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)、[What is MSK Serverless? - Amazon Managed Streaming for Apache Kafka](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)、[Amazon Kinesis Data Streams Terminology and concepts - Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

### 練習題 10｜SAA → SAP｜Amazon Data Firehose buffering、transformation 與 error path

Telemetry records以Direct PUT進入Firehose，經Lambda轉換後送到S3 primary destination，允許數十秒delivery latency。團隊要保留原始source records、調查Lambda轉換失敗，並理解S3 destination暫時不可用時會發生什麼事。選擇兩項正確設計。

A. Firehose提供任意application consumer offsets與shard checkpoint API，可完全取代Kinesis Data Streams的replay model
B. 把buffer interval設為零即可保證每筆record同步commit到S3，且沒有batch或retry行為
C. 只要Firehose回報delivery成功，所有下游business side effects就具有跨服務exactly-once transaction
D. 設定符合latency/cost需求的size/time buffering與Lambda transformation，理解batching會影響object size與交付延遲
E. 啟用source-record backup保存原始輸入，並為Lambda processing failures設定S3 error prefix；S3 destination不可用時則依Direct PUT的retention/retry規則持續重試，不能把所有delivery failures都說成會落入同一processing-failed prefix

**答案：D、E**

- **A：** 不正確。Firehose是managed delivery service，不提供一般stream consumers任意seek/checkpoint的contract。
- **B：** 不正確。Firehose依buffer與destination行為批次交付；不能藉由零interval取得同步逐筆transaction保證。
- **C：** 不正確。Delivery成功只描述Firehose到destination路徑，不保證後續business processing exactly once。
- **D：** 正確。Buffer size/time是latency、request數與object size的重要成本/效能參數，Lambda可在delivery前轉換records。
- **E：** 正確。Source-record backup、Lambda processing-failed output與destination retry是三個不同contract。Lambda轉換失敗records可進processing-failed prefix；S3 destination delivery failure對Direct PUT source會持續重試，最長受Firehose的24小時資料保留限制。Firehose也不是可任意seek offset的replay log；若要從任意位置重新消費原始stream，應保留Kinesis Data Streams、MSK或另一個durable source。

**事實查證：** [What is Amazon Data Firehose? - Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)、[Transform source data in Amazon Data Firehose - Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html)、[Handle data transformation failure - Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation-failure-handling.html)、[Configure backup settings - Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/create-configure-backup.html)、[Data delivery failures handling - Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/retry.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「AWS-native shard stream用Kinesis；Kafka ecosystem/porta…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Streaming需要定義ordering、retention、partition、consumer、replay與backpressure。」，所以「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」能直接滿足它；若constraint改成「SQS適合work queue而非保留可供多consumer replay的ordered log。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」。替代方案「SQS適合work queue而非保留可供多consumer replay的ordered log。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「以單一partition key形成hot shard，或consumer lag增加時只擴producer。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Streaming需要定義ordering、retention、partition、consumer、replay與backpressure。」，排除會導致「以單一partition key形成hot shard，或consumer lag增加時只擴producer。」的選項，再選「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「AWS-native shard stream用Kinesis；Kafka ecosystem/portability用MSK；delivery到S3等用Data Firehose。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「a stream is a replayable ordered log partitioned by key」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 51 章　OpenSearch、DocumentDB、Neptune 與 Purpose-built DB

搜尋、文件、圖與時序查詢若硬塞關聯資料庫，會產生複雜索引與不穩定效能。

## 跟著一筆資料走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：詐欺系統需遍歷帳戶關係、搜尋文字紀錄並保存原始交易。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：搜尋、文件、圖與時序查詢若硬塞關聯資料庫，會產生複雜索引與不穩定效能。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 但請同時記住它的邊界：恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon OpenSearch Service，對照角色是Amazon DocumentDB。我們選擇「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：詐欺系統需遍歷帳戶關係、搜尋文字紀錄並保存原始交易。

application先提出一個具體access pattern
          │ ① key／query／file／object語意
          ▼
[Amazon OpenSearch Service：authoritative或主要資料路徑]
          │ 提供managed search、log analytics與vector/search indexes。
          │ ② replica／cache／index服務不同讀取需求
          │ ③ backup／archive保護另一種失敗
          ▼
[recovery copy]
唯一真相、複寫、一致性與restore必須分開說明
本章其他角色：
  · Amazon DocumentDB：提供MongoDB-compatible managed document database。
  · Amazon Neptune：提供managed graph database支援property graph與RDF。
  · Amazon Timestream：提供serverless time-series ingestion、storage tiering與SQ…

失敗時先找：只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一筆資料走」。先不要急著問Amazon OpenSearch Service有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon OpenSearch Service和Amazon DocumentDB並不是兩個任意的產品名稱。前者適合本章，是因為「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」直接回應了眼前的問題；後者描述的「Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「specialized read models should not silently become authoritative stores」。更白話地說：先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon OpenSearch Service | 提供managed search、log analytics與vector/search indexes。 | Documents被分析並寫入shards；replicas提供read/availability，cluster manager維護metadata。 |
| Amazon DocumentDB | 提供MongoDB-compatible managed document database。 | Compute instances共享distributed cluster storage；支援MongoDB API的特定子集。 |
| Amazon Neptune | 提供managed graph database支援property graph與RDF。 | 以vertices/edges或triples保存關係，針對多跳traversal執行Gremlin/openCypher/SPARQL。 |
| Amazon Timestream | 提供serverless time-series ingestion、storage tiering與SQL analytics。 | Records依dimensions/time寫入memory store，再依retention移到magnetic store。 |

## 把全圖套進一個具體案例

**場景：** 詐欺系統需遍歷帳戶關係、搜尋文字紀錄並保存原始交易。

1. 故事的起點：詐欺系統需遍歷帳戶關係、搜尋文字紀錄並保存原始交易。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon OpenSearch Service負責「提供managed search、log analytics與vector/search indexes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Documents被分析並寫入shards；replicas提供read/availability，cluster manager維護metadata。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon DocumentDB、Amazon Neptune、Amazon Timestream各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「不能當所有交易的唯一system of record；primary data仍放RDS/DynamoDB/S3等。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon OpenSearch Service

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：搜尋、文件、圖與時序查詢若硬塞關聯資料庫，會產生複雜索引與不穩定效能。
- **具體例子／邊界：** 在「詐欺系統需遍歷帳戶關係、搜尋文字紀錄並保存原始交易。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon DocumentDB

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：specialized read models should not silently become authoritative stores。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### Amazon OpenSearch Service

- **功用：** 提供managed search、log analytics與vector/search indexes。
- **底層機制：** Documents被分析並寫入shards；replicas提供read/availability，cluster manager維護metadata。
- **關鍵設定：** domain/serverless collection、instance/shards/replicas、EBS、VPC access、fine-grained access、snapshots與index lifecycle。
- **選擇時機：** 全文搜尋、可觀測性logs、near-real-time aggregations與部分vector search。
- **替換時機：** 不能當所有交易的唯一system of record；primary data仍放RDS/DynamoDB/S3等。

### Amazon DocumentDB

- **功用：** 提供MongoDB-compatible managed document database。
- **底層機制：** Compute instances共享distributed cluster storage；支援MongoDB API的特定子集。
- **關鍵設定：** instance/cluster、replicas、parameter group、indexes、backup、TLS、VPC與compatibility version。
- **選擇時機：** 既有MongoDB-compatible document workload且想降低database operations。
- **替換時機：** 先驗證driver/operator/feature相容性；不是只因JSON就應選document database。

### Amazon Neptune

- **功用：** 提供managed graph database支援property graph與RDF。
- **底層機制：** 以vertices/edges或triples保存關係，針對多跳traversal執行Gremlin/openCypher/SPARQL。
- **關鍵設定：** engine/version、instance/serverless、replicas、parameter groups、streams、backup與query language。
- **選擇時機：** fraud network、knowledge graph、identity relationships與推薦關係遍歷。
- **替換時機：** 一般key lookup用DynamoDB，transactional tabular data用RDS/Aurora。

### Amazon Timestream

- **功用：** 提供serverless time-series ingestion、storage tiering與SQL analytics。
- **底層機制：** Records依dimensions/time寫入memory store，再依retention移到magnetic store。
- **關鍵設定：** database/table、memory/magnetic retention、dimensions/measures、scheduled query與KMS。
- **選擇時機：** IoT telemetry、metrics、industrial events與時間窗口聚合。
- **替換時機：** 全文搜尋用OpenSearch；一般OLTP用RDS/DynamoDB。

## 考前與實作時再查：設定操作手冊

### Amazon OpenSearch Service：逐項設定說明

#### `domain／serverless collection`

- **控制什麼：** Domain是provisioned OpenSearch cluster；serverless collection由AWS管理底層capacity，依search、time-series或vector workload提供不同抽象。
- **何時需要：** 需要全文搜尋、log analytics或vector index，並在控制cluster拓樸與降低營運負擔之間選擇時。
- **怎麼設定／驗證：** 先定義資料量、ingestion、query latency與相容plugin需求；provisioned設定engine/nodes/shards，Serverless建立collection、encryption、network與data access policies。
- **常見錯法：** 這裡的domain不是DNS名稱。Serverless也不是無上限或零設定；network policy與data access policy缺一仍會拒絕請求。

#### `instances／shards／replicas`

- **控制什麼：** Instance提供CPU、memory與storage；primary shard切分index資料；replica shard增加read capacity並在節點故障時提供副本。
- **何時需要：** 資料量、ingestion或查詢增加，或production搜尋服務需要跨AZ容錯與可預測恢復時間時。
- **怎麼設定／驗證：** 依單一shard大小、heap、query concurrency與AZ規劃node count、primary shards與replicas；用代表性資料量壓測並監控JVM pressure、CPU、storage與shard skew。
- **常見錯法：** 過多小shards浪費heap，過大shard拖慢recovery；replica提高可用性與讀取量，但也增加儲存與寫入成本。

#### `EBS`

- **控制什麼：** 為provisioned data nodes提供持久block storage；volume type、size與IOPS／throughput會限制index與merge效能。
- **何時需要：** 使用provisioned domain且資料量超出instance local storage，或需要可調整的持久容量時。
- **怎麼設定／驗證：** 選擇支援的gp3/io類型與容量，保留watermark headroom；監控FreeStorageSpace、IOPS與throughput，擴容前估算rebalance時間。
- **常見錯法：** 磁碟變大不會修正hot shard或JVM瓶頸；等到空間接近零才擴容可能已觸發read-only block。

#### `VPC access`

- **控制什麼：** 把OpenSearch endpoint放入指定VPC subnets並建立ENIs，使data plane只由具備network path的clients存取。
- **何時需要：** 搜尋資料或logs不應暴露於Internet，且clients位於VPC、peered/TGW network或hybrid環境時。
- **怎麼設定／驗證：** 選擇跨AZ subnets與security groups，建立DNS、route與return path；再搭配fine-grained access或IAM簽章驗證application身份。
- **常見錯法：** VPC access只限制網路可達性，不等於application authorization；建立後切換public/VPC access通常需要replacement或遷移規劃。

#### `fine-grained access`

- **控制什麼：** 在cluster內以users、backend roles、index、document與field permissions控制誰能搜尋或修改哪些資料。
- **何時需要：** 多租戶、security analytics或不同團隊共用cluster，但不能互讀index時。
- **怎麼設定／驗證：** 啟用fine-grained access，將IAM role／IdP group映射到最小OpenSearch roles；分別測試cluster、index與Dashboards權限。
- **常見錯法：** 只靠domain access policy通常粒度太粗；同時混用IAM、basic auth與role mapping若沒有明確模型，容易出現403或過度授權。

#### `snapshots`

- **控制什麼：** 保存index與cluster metadata的可恢復副本；自動snapshot與手動snapshot有不同保留與repository責任。
- **何時需要：** 誤刪index、資料毀損、重大升級或跨domain migration需要恢復點時。
- **怎麼設定／驗證：** 確認自動snapshot時段與保留；長期／遷移需求建立S3 snapshot repository、IAM role與bucket/KMS policy，並定期演練restore到隔離domain。
- **常見錯法：** Replica不是snapshot；snapshot成功也不代表能在目標版本、Region與KMS權限下恢復。

#### `index lifecycle`

- **控制什麼：** 以hot/warm/cold/delete階段管理index rollover、遷移與刪除，讓資料保留和查詢效能對應成本。
- **何時需要：** Logs或time-series資料持續成長，但新資料查詢頻繁、舊資料只偶爾查詢且有明確retention時。
- **怎麼設定／驗證：** 依時間／size設定rollover與ISM policy，定義各階段、minimum age、snapshot及delete；以alias寫入並監控policy execution。
- **常見錯法：** 直接按日期大量建立極小index會產生shard爆炸；delete policy若無legal retention與snapshot檢查，可能永久刪除稽核資料。

### Amazon DocumentDB：逐項設定說明

#### `instance/cluster`

- **控制什麼：** `instance/cluster`設定Amazon DocumentDB的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `replicas`

- **控制什麼：** `replicas`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DocumentDB依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `parameter group`

- **控制什麼：** `parameter group`是一組可版本化的engine/runtime參數，會改變Amazon DocumentDB的實際process行為。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `indexes`

- **控制什麼：** `indexes`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon DocumentDB的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DocumentDB依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `TLS`

- **控制什麼：** `TLS`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DocumentDB的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DocumentDB的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `compatibility version`

- **控制什麼：** `compatibility version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「既有MongoDB-compatible document workload且想降低database operations。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DocumentDB鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

### Amazon Neptune：逐項設定說明

#### `engine/version`

- **控制什麼：** `engine/version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Neptune鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `instance/serverless`

- **控制什麼：** `instance/serverless`設定Amazon Neptune的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `replicas`

- **控制什麼：** `replicas`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Neptune依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `parameter groups`

- **控制什麼：** `parameter groups`是一組可版本化的engine/runtime參數，會改變Amazon Neptune的實際process行為。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `streams`

- **控制什麼：** `streams`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon Neptune持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Neptune依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `query language`

- **控制什麼：** `query language`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「fraud network、knowledge graph、identity relationships與推薦關係遍歷。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Neptune的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

### Amazon Timestream：逐項設定說明

#### `database/table`

- **控制什麼：** `database/table`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「IoT telemetry、metrics、industrial events與時間窗口聚合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Timestream的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `memory/magnetic retention`

- **控制什麼：** `memory/magnetic retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「IoT telemetry、metrics、industrial events與時間窗口聚合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon Timestream的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `dimensions/measures`

- **控制什麼：** `dimensions/measures`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「IoT telemetry、metrics、industrial events與時間窗口聚合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon Timestream的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `scheduled query`

- **控制什麼：** `scheduled query`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「IoT telemetry、metrics、industrial events與時間窗口聚合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon Timestream的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「IoT telemetry、metrics、industrial events與時間窗口聚合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Timestream指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

## 讀到這裡，請用自己的話說一次

1. Amazon OpenSearch Service的責任：提供managed search、log analytics與vector/search indexes。
2. 底層機制：Documents被分析並寫入shards；replicas提供read/availability，cluster manager維護metadata。
3. 第一個要看的設定：domain/serverless collection、instance/shards/replicas、EBS、VPC access、fine-grained access、snapshots與index lifecycle。
4. 選擇邏輯：全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。
5. 不要混淆：Amazon DocumentDB的責任是「提供MongoDB-compatible managed document database。」；它不會自動取代Amazon OpenSearch Service。
6. 替換訊號：不能當所有交易的唯一system of record；primary data仍放RDS/DynamoDB/S3等。
7. 最常見錯法：只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。
8. 可移植原則：specialized read models should not silently become authoritative stores。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon OpenSearch Service | 提供managed search、log analytics與vector/search indexes。 | Documents被分析並寫入shards；replicas提供read/availability，cluster manager維護metadata。 | 全文搜尋、可觀測性logs、near-real-time aggregations與部分vector search。 | 不能當所有交易的唯一system of record；primary data仍放RDS/DynamoDB/S3等。 |
| Amazon DocumentDB | 提供MongoDB-compatible managed document database。 | Compute instances共享distributed cluster storage；支援MongoDB API的特定子集。 | 既有MongoDB-compatible document workload且想降低database operations。 | 先驗證driver/operator/feature相容性；不是只因JSON就應選document database。 |
| Amazon Neptune | 提供managed graph database支援property graph與RDF。 | 以vertices/edges或triples保存關係，針對多跳traversal執行Gremlin/openCypher/SPARQL。 | fraud network、knowledge graph、identity relationships與推薦關係遍歷。 | 一般key lookup用DynamoDB，transactional tabular data用RDS/Aurora。 |
| Amazon Timestream | 提供serverless time-series ingestion、storage tiering與SQL analytics。 | Records依dimensions/time寫入memory store，再依retention移到magnetic store。 | IoT telemetry、metrics、industrial events與時間窗口聚合。 | 全文搜尋用OpenSearch；一般OLTP用RDS/DynamoDB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。 | 只有當題目條件明確改變時才可能合理。 | 只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。」之間做選擇。
- 認得常考設定：domain/serverless collection、instance/shards/replicas、EBS、VPC access、fine-grained access、snapshots與index lifecycle。
- 對應官方tasks：SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：不能當所有交易的唯一system of record；primary data仍放RDS/DynamoDB/S3等。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA → SAP｜OpenSearch derived index 與 source of truth

Order交易在Aurora提交後，客服需要全文搜尋地址與商品名稱。OpenSearch index可接受數秒延遲，而且mapping錯誤時必須能重建。哪個資料流最安全？

A. 只把orders寫入OpenSearch並刪除Aurora backups；search replicas可恢復任何已刪交易
B. 先寫OpenSearch、成功後才盡力寫Aurora；若第二步失敗，以search document作財務真相
C. 讓clients同步dual-write Aurora與OpenSearch，並假設兩個services會自動形成單一ACID transaction
D. Aurora作authoritative store，以transactional outbox/CDC或可靠events投影到OpenSearch，使用idempotency並保留reindex流程

**答案：D**

- **A：** 不正確。OpenSearch replicas改善search availability，不是交易PITR或永久source-of-truth backup。
- **B：** 不正確。以search index擁有交易會把mapping、refresh與index lifecycle語意帶進財務correctness，且第二步失敗難以補償。
- **C：** 不正確。跨Aurora與OpenSearch沒有自動distributed transaction；未設補償會產生部分成功與不一致。
- **D：** 正確。Durable database先擁有交易，outbox/CDC建立可重試projection；index可stale且可由source重建。

**事實查證：** [What is Amazon OpenSearch Service? - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)

### 練習題 2｜SAA → SAP｜OpenSearch shard sizing、replicas 與 recovery

Logging domain有4 TB資料卻建立20,000個tiny primary shards，cluster-manager heap壓力高；另一index只有一個2 TB primary shard，node replacement時恢復很慢。哪個處置最合理？

A. 把每個index都改成數十萬shards；shard完全沒有heap或cluster-state overhead
B. 依index size、ingest/query rate、node storage/heap與recovery目標重新規劃primary shards與replicas，透過load test及metrics驗證
C. 只增加replicas且不增加storage；replicas不會消耗disk或indexing resources，並能分割原primary
D. 關閉所有snapshots；沒有snapshot metadata後，單一2 TB shard會自動跨nodes切成多個primary

**答案：B**

- **A：** 不正確。每個shard都有heap、file handles與cluster-state成本，過多tiny shards會降低穩定性。
- **B：** 正確。Shard計畫需平衡大小、parallelism、heap/storage與failure recovery；replica數也要納入read availability及寫入成本。
- **C：** 不正確。Replicas保存完整shard copies並消耗storage/indexing resources，也不會把一個primary shard拆成多個primaries。
- **D：** 不正確。Snapshot與live shard layout是不同機制；停用backup不會自動reshard，反而降低recoverability。

**事實查證：** [Sizing Amazon OpenSearch Service domains - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html)

### 練習題 3｜SAP｜OpenSearch network、IAM 與 fine-grained access

OpenSearch domain部署在VPC。Tenant A與Tenant B的analysts從同一corporate network連線，但每組只能查自己的indices，且寫入requests需使用AWS身份或受控user。哪個控制組合正確？

A. 以VPC/SG限制reachability，以domain access policy/IAM控制呼叫者，再用fine-grained access control把users/roles映射到index、document或field permissions
B. 只用security group列出`tenant-a-*` index pattern；SG會解析HTTP path並做document-level authorization
C. 只要domain在private subnet，VPC中任何principal都自動具有OpenSearch admin permissions
D. 只建立FGAC role；它會自動修改KMS key policy、VPC routes與security groups

**答案：A**

- **A：** 正確。Network reachability、service/IAM access與OpenSearch細粒度permissions分屬不同層，需共同配置並搭配TLS/encryption。
- **B：** 不正確。Security groups控制來源、protocol與port，不理解index、document或field。
- **C：** 不正確。Private network不等於authorization；可達domain的principal仍需通過access policy與認證。
- **D：** 不正確。FGAC不會自動配置KMS或VPC邊界，這些控制仍須獨立建立。

**事實查證：** [Identity and Access Management in Amazon OpenSearch Service - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html)

### 練習題 4｜SAP｜OpenSearch availability、snapshots 與 index lifecycle

Security logs要承受node/AZ failure，誤刪index後可restore，並在每天50 GB時自動rollover且365天後刪除。哪個設計同時分清三種責任？

A. 只建立一個replica；replica會保存365個歷史版本並可恢復任何誤刪index
B. 只設定Index State Management delete action；ISM會建立跨Region backup並自動接管AZ failover
C. 配置適當Multi-AZ/standby與replicas處理availability，使用snapshots處理restore，並以ISM管理rollover與retention
D. 只使用snapshot；snapshot是同步standby，可保留所有現有TCP sessions並提供zero-RPO failover

**答案：C**

- **A：** 不正確。Replica同步目前index state，誤刪會傳播，不能提供任意歷史restore。
- **B：** 不正確。ISM負責index state transitions與retention，不是AZ failover或backup機制。
- **C：** 正確。Live redundancy、point-in-time recovery artifact與lifecycle automation是三個不同控制，需各自配置並演練。
- **D：** 不正確。Snapshot是restore artifact，不是接管live traffic的同步standby，也不保存client connections。

**事實查證：** [Creating index snapshots in Amazon OpenSearch Service - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html)、[What is Amazon OpenSearch Service? - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)、[Index State Management in Amazon OpenSearch Service - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html)

### 練習題 5｜SAP｜DocumentDB MongoDB API compatibility boundary

公司考慮把MongoDB application移到Amazon DocumentDB。程式使用特定aggregation operators、index types、transactions、change streams與admin commands，並載入既有driver。哪個遷移評估正確？

A. 只要documents是JSON，所有MongoDB server features、extensions與operational commands都必然一對一相容
B. API-compatible代表query behavior、consistency、performance與index semantics必然完全相同，不需測試
C. DocumentDB執行MongoDB原始server binaries，所以任何version-specific feature都可直接啟用
D. 依目標DocumentDB版本逐項核對compatibility文件，並以真實queries、indexes、transactions、drivers及operational tooling進行測試

**答案：D**

- **A：** 不正確。JSON-like document model不等於完整feature compatibility，特定operators與admin功能可能不同。
- **B：** 不正確。API compatibility有明確支援範圍，行為與性能仍需以實際workload驗證。
- **C：** 不正確。DocumentDB是具MongoDB-compatible API的AWS服務，不是宣稱運行所有MongoDB server binaries與extensions。
- **D：** 正確。遷移必須按版本與feature matrix驗證應用真正使用的operators、indexes、transactions、drivers及管理流程。

**事實查證：** [Amazon DocumentDB compatibility with MongoDB - Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/compatibility.html)

### 練習題 6｜SAA → SAP｜DocumentDB replicas、failover 與 PITR

Document workload需要writer、跨AZ reader scaling與自動failover；營運人員誤刪collection時還要恢復到昨天。哪個架構最符合？

A. 只建立三個read replicas；replicas會保存每天歷史版本，因此不需要backup retention或PITR
B. 部署跨AZ cluster instances與replicas，使用cluster/reader endpoints及client retry，另設定automated backups/PITR與KMS
C. 讓每個replica使用完全獨立、手動rsync的filesystem；DocumentDB不共享cluster storage
D. 所有reads都走reader endpoint即可保證全域strong read-after-write，無需理解read preference或replica lag

**答案：B**

- **A：** 不正確。Live replicas會套用刪除，不能取代歷史backup或PITR。
- **B：** 正確。跨AZ replicas提供read scale與promotion候選，endpoints/retry處理failover；backup/PITR則處理誤刪等logical recovery。
- **C：** 不正確。DocumentDB cluster instances使用分散式cluster storage，不需要使用者手動rsync每個replica filesystem。
- **D：** 不正確。Reader path的consistency與lag需按服務語意處理，不能無條件承諾全域read-after-write。

**事實查證：** [Scaling Amazon DocumentDB clusters - Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/db-cluster-manage-performance.html)、[Backing up and restoring in Amazon DocumentDB - Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/backup_restore.html)

### 練習題 7｜SAA → SAP｜Neptune graph model 與 multi-hop traversal

Fraud system要即時查詢「帳號→裝置→IP→其他帳號→地址」多跳關係，並找出短時間形成的可疑環路。現有relational self-joins隨hop數增加快速變慢。哪個資料模型最適合評估？

A. 以Neptune建立vertices/edges，依property graph或RDF需求選Gremlin/openCypher/SPARQL，並按實際traversal設計模型
B. 以OpenSearch全文inverted index代替所有graph edges；任何multi-hop traversal都會自動變成單字搜尋
C. 把所有entities放入單一2 GB JSON document；document越大，任意hop查詢必然越快
D. 把SQL foreign keys原封不動送到SPARQL endpoint；不同query languages與graph model不需轉換

**答案：A**

- **A：** 正確。Neptune針對graph relationships與traversals，需先依query shape選property graph/RDF及vertex/edge建模。
- **B：** 不正確。OpenSearch擅長text search與aggregations，不會自動提供任意關係圖的多跳traversal semantics。
- **C：** 不正確。巨大document增加更新與讀取成本，也沒有把relationship navigation轉成graph execution。
- **D：** 不正確。Relational schema、RDF triples與property graph語言不同，必須明確轉換與重新建模。

**事實查證：** [What Is Amazon Neptune? - Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)

### 練習題 8｜SAP｜Neptune HA、read scaling、backup 與 Global Database

Neptune workload需要primary Region內跨AZ failover與read scaling，另需secondary Region提供DR reads；誤刪graph時要能回復。選擇兩項正確敘述。

A. Reader replica本身是任意歷史point-in-time backup，誤刪後可直接把replica查詢到昨天狀態
B. Global Database預設讓每個Region同步multi-writer，任何network partition都可保證zero-conflict writes
C. 在primary cluster部署跨AZ replicas並使用適當endpoints/client reconnect，讓replica可承接reads與promotion
D. Cluster endpoint會在failover時搬移所有既有TCP sessions，因此application不需要timeout或retry
E. 使用automated backups/PITR處理logical recovery，並以Neptune Global Database規劃跨Region reads/DR、replication lag與promotion runbook

**答案：C、E**

- **A：** 不正確。Replica反映live changes，不能任意查詢歷史狀態；誤刪需要backup/PITR。
- **B：** 不正確。Global Database不是預設同步multi-writer conflict-free架構，需理解單一writer與cross-Region replication/failover語意。
- **C：** 正確。跨AZ replicas改善read scale與promotion能力，但application仍需使用endpoint並處理連線中斷。
- **D：** 不正確。Endpoint可重新指向新writer，但既有socket不會無縫搬移，client resilience仍必要。
- **E：** 正確。PITR與Global Database分別處理logical recovery及Region-level read/DR，並需演練lag、promotion與cutover。

**事實查證：** [Amazon Neptune storage, reliability and availability - Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage.html)、[Backing up and restoring an Amazon Neptune DB cluster - Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/backup-restore.html)、[Using Amazon Neptune with a global database - Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-global-database.html)

### 練習題 9｜SAA → SAP｜Timestream for LiveAnalytics 資料模型、retention 與 late-arriving data

既有客戶以Timestream for LiveAnalytics保存車隊telemetry。Dashboard常查最近24小時，稽核查詢要保留13個月；裝置離線時，帶原始event timestamp的records最晚可能48小時後才到達。選擇兩項正確設計。

A. 把event timestamp存成普通dimension並一律使用ingestion time，因time欄位不能代表裝置實際產生事件的時間
B. 以device、site等dimensions描述series，以time記錄事件時間並以measures保存數值；依24小時熱查詢與13個月歷史需求設定memory與magnetic retention
C. 把memory retention設為24小時後，48小時前的late record仍會自動進memory store，無須任何額外設定
D. 若late record可能落在memory retention之外但仍在magnetic retention內，應啟用magnetic store writes，並接受這類資料不是立即可查、最長可能需要數小時才可見
E. Memory retention到期就代表資料永久刪除；magnetic retention只影響query速度，不影響資料保存期限

**答案：B、D**

- **A：** 不正確。Timestream的time欄位就是資料點的時間軸；改用ingestion time會扭曲離線裝置事件的先後與時間範圍查詢。
- **B：** 正確。Dimensions識別series與篩選維度，time表示事件時間，measures保存觀測值；memory store服務近期快速查詢，magnetic store承接較長期歷史與分析。
- **C：** 不正確。超出memory retention的timestamp預設可能被拒絕；是否接收必須看magnetic store writes設定與magnetic retention，而不是假設自動進memory。
- **D：** 正確。啟用`EnableMagneticStoreWrites`後，timestamp在magnetic retention內的late-arriving data可直接寫入magnetic store，但不會立即可查，官方文件指出最長可能約6小時才可見。時效補充：LiveAnalytics自2025-06-20起不接受新客戶，因此此題只描述既有workload；availability不是SAA/SAP正解判定條件。
- **E：** 不正確。Memory資料到期後可由magnetic store依其retention繼續保存；magnetic retention到期才會永久刪除對應歷史資料。

**事實查證：** [What is Amazon Timestream for LiveAnalytics? - Amazon Timestream](https://docs.aws.amazon.com/timestream/latest/developerguide/what-is-timestream.html)、[Amazon Timestream for LiveAnalytics availability change - Amazon Timestream](https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html)、[Storage - Amazon Timestream for LiveAnalytics](https://docs.aws.amazon.com/timestream/latest/developerguide/storage.html)、[Data ingestion - Amazon Timestream for LiveAnalytics](https://docs.aws.amazon.com/timestream/latest/developerguide/data-ingest.html)

### 練習題 10｜SAP｜Purpose-built database ownership 與 synchronization cost

新平台同時需要payment transactions、全文商品搜尋、fraud graph traversal與MongoDB-compatible document API。團隊提議把每筆資料同步寫入所有databases且不指定owner。選擇兩項正確架構原則。

A. 為每類business state指定authoritative store，再以outbox/CDC/events建立需要的search或graph projections，並設計retry、idempotency與reconciliation
B. 只因OpenSearch支援JSON就讓它成為唯一payment ledger；inverted index等同跨documents ACID transaction
C. Purpose-built代表所有AWS databases會自動跨服務exactly-once同步，因此不需要schema ownership或failure runbook
D. 把所有stores都當writer且採用last response wins；這可在network partition時保證不遺失任何accepted transaction
E. 依access pattern、consistency、compatibility、scale與成本選擇RDS/Aurora、OpenSearch、Neptune或DocumentDB，並把每個額外projection的operational cost納入決策

**答案：A、E**

- **A：** 正確。明確owner避免互相衝突的truth，可靠change propagation與reconciliation處理跨store部分失敗。
- **B：** 不正確。JSON與search能力不會提供payment ledger所需的transaction、constraint與recovery contract。
- **C：** 不正確。跨服務同步不是天然exactly once；schema evolution、retry、duplicates與ownership都必須由架構處理。
- **D：** 不正確。多個未協調writers會放大conflicts與partial failure，last response wins不能保證保存所有交易。
- **E：** 正確。Purpose-built的價值來自query與operational fit，不是把所有資料無條件複製；同步、backup與on-call負擔都是實際成本。

**事實查證：** [AWS Database category iconDatabases - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)、[What is Amazon OpenSearch Service? - Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)、[Amazon DocumentDB compatibility with MongoDB - Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/devguide/compatibility.html)、[What Is Amazon Neptune? - Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「搜尋、文件、圖與時序查詢若硬塞關聯資料庫，會產生複雜索引與不穩定效能。」，所以「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」能直接滿足它；若constraint改成「Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」。替代方案「Purpose-built store改善特定access pattern，但增加同步、備份與技能負擔。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「搜尋、文件、圖與時序查詢若硬塞關聯資料庫，會產生複雜索引與不穩定效能。」，排除會導致「只因資料是JSON就選DocumentDB，或將OpenSearch當唯一system of record。」的選項，再選「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」。本章對應的代表task包括：SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「全文搜尋用OpenSearch；MongoDB相容文件用DocumentDB；關係遍歷用Neptune；時序用Timestream。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「specialized read models should not silently become authoritative stores」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
