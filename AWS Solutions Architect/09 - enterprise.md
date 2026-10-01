---
title: "SAP Enterprise Architecture"
part: 8
as_of: 2026-10-01
---

# Part 8　SAP Enterprise Architecture

# 第 79 章　Landing Zone 與 Multi-account Strategy

企業需要以帳號隔離billing、quota、權限與blast radius，同時保留一致治理。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

故事從一個看似簡單的需求開始：企業併購後有數百工作負載，需統一安全基線但讓團隊獨立交付。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：企業需要以帳號隔離billing、quota、權限與blast radius，同時保留一致治理。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

Landing zone像新城市開發前先鋪好道路、門牌、警報與管理規則，之後每個團隊才能安全地蓋自己的房子。 中央治理不能變成所有變更都排隊等同一個團隊；良好設計同時保留guardrail與delegation。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Organizations會是本章的主要角色，AWS Control Tower則幫我們看清邊界。方向是「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：企業併購後有數百工作負載，需統一安全基線但讓團隊獨立交付。

Management account / Organization
      │
      ├─ Security OU：log archive、security tooling
      ├─ Infrastructure OU：network、shared services
      ├─ Workloads OU：prod accounts / non-prod accounts
      └─ Sandbox OU：較小blast radius的實驗

Control Tower / Account Factory提供一致account baseline與guardrails。
中央團隊管理共同道路與安全底線；workload團隊在帳號邊界內獨立交付。
OU是policy繼承樹，不是封包流動的network boundary。

失敗時先找：把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Organizations有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Organizations和AWS Control Tower並不是兩個任意的產品名稱。前者適合本章，是因為「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」直接回應了眼前的問題；後者描述的「單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「accounts are strong operational and security boundaries」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 |
| AWS Account Factory | 以Control Tower核准blueprint自助供應新AWS accounts。 | 透過Service Catalog/AFT pipeline收集account metadata並套landing-zone baseline。 |

## 把全圖套進一個具體案例

**場景：** 企業併購後有數百工作負載，需統一安全基線但讓團隊獨立交付。

1. 故事的起點：企業併購後有數百工作負載，需統一安全基線但讓團隊獨立交付。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Organizations負責「集中建立accounts、OU、政策與consolidated billing。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Control Tower、AWS Account Factory各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「單一account內的日常permission仍用IAM；不要在management account執行workloads。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Organizations

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：企業需要以帳號隔離billing、quota、權限與blast radius，同時保留一致治理。
- **具體例子／邊界：** 在「企業併購後有數百工作負載，需統一安全基線但讓團隊獨立交付。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Control Tower

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：accounts are strong operational and security boundaries。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### AWS account

AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### drift

實際resource設定與IaC宣告狀態不同，常由console手動修改或外部automation造成。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

## 回到 AWS：Components、功用與責任邊界

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

### AWS Control Tower

- **功用：** 建立與治理符合best practices的multi-account landing zone。
- **底層機制：** 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。
- **關鍵設定：** landing zone Regions、OU、controls、Account Factory/AFT、log archive、audit account與drift repair。
- **選擇時機：** 快速建立一致account vending與preventive/detective/proactive controls。
- **替換時機：** 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。

### AWS Account Factory

- **功用：** 以Control Tower核准blueprint自助供應新AWS accounts。
- **底層機制：** 透過Service Catalog/AFT pipeline收集account metadata並套landing-zone baseline。
- **關鍵設定：** account email/name、OU、SSO owner、network blueprint、AFT customizations與lifecycle events。
- **選擇時機：** 大量team/project accounts且需要一致guardrails與審批。
- **替換時機：** 不要用單一共享account加tags取代真正blast-radius與billing boundaries。

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

### AWS Account Factory：逐項設定說明

#### `account email/name`

- **控制什麼：** `account email/name`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「大量team/project accounts且需要一致guardrails與審批。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Account Factory建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `OU`

- **控制什麼：** `OU`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「大量team/project accounts且需要一致guardrails與審批。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Account Factory建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `SSO owner`

- **控制什麼：** `SSO owner`指定誰能使用、管理或接受AWS Account Factory的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `network blueprint`

- **控制什麼：** `network blueprint`是可版本化的啟動或工作規格，定義AWS Account Factory建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `AFT customizations`

- **控制什麼：** `AFT customizations`控制AWS Account Factory的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

#### `lifecycle events`

- **控制什麼：** `lifecycle events`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「大量team/project accounts且需要一致guardrails與審批。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Account Factory依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

## 可以直接對照 AWS 的設定範例

### Landing zone account manifest

```yaml
account:
  name: payments-prod
  email: aws+payments-prod@example.com
  ou: /Workloads/Prod
  owners:
    business: payments
    technical: payments-platform
  baseline:
    identity: IAMIdentityCenter
    organization_trail: required
    config_recorder: required
    guardduty: delegated-admin
    backup_vault_account: security-backup
  network:
    segment: prod
    egress: centralized
  tags:
    cost-center: CC-1042
    data-classification: restricted

```

1. Account是security、quota、billing與blast-radius boundary，不只是資料夾。
2. OU決定繼承的SCP/controls；不要按公司org chart盲目設計，而要按policy與lifecycle相似度。
3. Owner、cost center、data classification與network segment必須在供應時建立，不能事後靠人工補。

## 讀到這裡，請用自己的話說一次

1. AWS Organizations的責任：集中建立accounts、OU、政策與consolidated billing。
2. 底層機制：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
3. 第一個要看的設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
4. 選擇邏輯：依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。
5. 不要混淆：AWS Control Tower的責任是「建立與治理符合best practices的multi-account landing zone。」；它不會自動取代AWS Organizations。
6. 替換訊號：單一account內的日常permission仍用IAM；不要在management account執行workloads。
7. 最常見錯法：把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。
8. 可移植原則：accounts are strong operational and security boundaries。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 | 快速建立一致account vending與preventive/detective/proactive controls。 | 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。 |
| AWS Account Factory | 以Control Tower核准blueprint自助供應新AWS accounts。 | 透過Service Catalog/AFT pipeline收集account metadata並套landing-zone baseline。 | 大量team/project accounts且需要一致guardrails與審批。 | 不要用單一共享account加tags取代真正blast-radius與billing boundaries。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。 | 只有當題目條件明確改變時才可能合理。 | 把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。」之間做選擇。
- 認得常考設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：單一account內的日常permission仍用IAM；不要在management account執行workloads。
- 對應官方tasks：SAP-1.4 Design a multi-account AWS environment；SAP-1.5 Determine cost optimization and visibility strategies；SAP-3.1 Determine a strategy to improve overall operational excellence。

## 本章 10 題考題

### 練習題 1｜SAP｜以帳號建立隔離邊界

一家醫療 SaaS 將 production、development 與受監管資料放在同一 AWS 帳號，只用 VPC 和 tags 區分。最近 development 的大量測試耗盡帳號 quota，production 也無法擴容。公司還要求開發者不能管理 production 的 billing 與 root-level 設定。應優先採取哪個重整方式？

A. 將受監管資料拆到專用帳號；Audit trail 另標示「以帳號建立隔離邊界」的設定版本、生效時間與 exception expiry
B. 保留單一帳號，改用獨立 VPC、ABAC 與 quota increase 管理環境隔離；治理 dashboard 分別顯示各 account 的 service-quota utilization、月成本與 root-contact 狀態，具名 owner 與 approver 依固定 cadence 複核
C. 依產品線拆帳號
D. 把 production、development 與受監管 workload 分到不同帳號；以 OUs 套用共同治理政策

**答案：D**

- **A：** 受監管資料另置帳號能縮小法遵邊界，但 production 與 development 仍共用 account-level quota、billing 與最高權限。若兩個環境可共同承擔容量與管理風險才適用。
- **B：** VPC 與 ABAC 能隔離網路和資源操作，quota、root、billing 與 account administrator 仍屬同一帳號。這適合信任與容量邊界相同的環境，不符合題目的強隔離要求。
- **C：** 依產品線拆帳號可改善部分 quota 隔離，卻仍讓開發者控制 production 的帳號級設定。若同一團隊同時擁有開發與正式環境才可能接受。
- **D：** 符合本題。AWS 帳號可形成權限、quota、billing 與事故 blast radius 的強邊界；OU 用來對帳號分組並套用政策，不承載 workload。

**事實查證：** [Policy inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html)、[What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)

### 練習題 2｜SAP｜設計穩定的 OU hierarchy

一家跨國企業每季都會調整部門與產品線。如果 OU 完全照組織圖建立，帳號會頻繁移動，繼承的 SCP 與 controls 也跟著改變。哪一種 OU 設計最能降低這種治理震盪？

A. 以 production、security、infrastructure、sandbox 等持久治理差異建立上層 OU，易變的產品 ownership 放在 account metadata 或 tags
B. 依目前部門建立 OU，組織改組時同步移動帳號，產品 metadata 仍放在 tags；Release evidence 另關聯「設計穩定的 OU hierarchy」的 pilot wave、result 與 rollback timestamp
C. 維持扁平 OU，將不同治理政策逐帳號附加並用 Config 偵測 policy drift；Release evidence 另關聯「設計穩定的 OU hierarchy」的 pilot wave、result 與 rollback timestamp
D. 依季度組織圖自動移動 accounts，effective SCP 與 controls 由季度 governance review 確認；Audit account 保存 OU move history、policy attachment 版本與 effective SCP snapshots，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。OU 應反映穩定且會造成不同政策的邊界；產品、成本中心與 owner 可用 metadata 表示，不必改變政策繼承路徑。
- **B：** 部門型 OU 在組織穩定時容易理解；此公司每季改組，帳號移動會同步改變 SCP 與 controls 的繼承結果。
- **C：** 扁平 OU 加逐帳號政策可支援少量特殊帳號，但大量例外會失去可預測的 inherited governance，Config 也只能偵測部分結果，不能取代政策結構。
- **D：** 自動化搬移帳號能降低人工成本，仍會在每次改組時改變 effective policies。題目要降低治理震盪，因此自動化錯誤的分類軸並不能解決問題。

**事實查證：** [Policy inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html)、[What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)

### 練習題 3｜SAP｜SCP 與 IAM policy 的交集（選兩項）

某 member account 的 Developer role 有 identity policy 允許 `s3:DeleteBucket`。該帳號所在 OU 的 SCP 明確 Deny 這個 action。安全團隊要向開發者解釋實際授權結果。哪兩項敘述正確？（選兩項）

A. 在 role 加上 AdministratorAccess，並保留 OU 上的 explicit Deny 作為防護
B. Developer role 不能刪除 bucket，因為適用的 SCP explicit Deny 會限制 member account 的有效權限
C. 以允許 s3:DeleteBucket 的 bucket policy 補充 identity policy；保留 SCP Deny
D. 即使 SCP 允許某 action，principal 仍需要 identity-based 或 resource-based policy 提供相應 Allow
E. 把相同 IAM policy 複製到 management account 的操作角色，再由該角色代為刪除

**答案：B、D**

- **A：** AdministratorAccess 是 IAM Allow，不能覆蓋適用 SCP 的 explicit Deny。它只會擴大其他未被 SCP 阻擋的權限。
- **B：** 符合本題。SCP 定義 member account 可用權限的上限；其 explicit Deny 無法由較寬的 identity policy 覆蓋。
- **C：** Bucket policy 可提供 resource-based Allow，但 member account principal 仍受 SCP explicit Deny 限制；resource policy 不能把該 Deny 變成 Allow。
- **D：** 符合本題。有效權限是多層 policy 的交集；SCP Allow 只是沒有在該層阻擋，不等於完成授權。
- **E：** 改由 management account principal 操作可能繞開 member-account SCP 的限制，但那是更換 principal 與信任邊界，不是 Developer role 取得有效權限，也會破壞題目要解釋的治理模型。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 4｜SAP｜保護 management account 與 delegated administration

公司把 CI/CD runners、共享 container registry 和日常 SOC dashboard 都部署在 Organizations management account，因為它能存取整個 organization。稽核要求縮小最高權限帳號的攻擊面。最適合的改造是什麼？

A. 把 SOC dashboard 移到 security account；CI runners 與 registry 留在 management account
B. 把 workload 移到 member accounts，對支援的服務指定 delegated administrator，只保留少數受監控的 management 與 break-glass 操作
C. 指定 delegated administrators，同時保留平台團隊在 management account 的長期 organization-admin role；CloudTrail 集中記錄 management-account 與 delegated-administrator 的 Organizations API activity，相關 alarms 與 rollback timestamp 納入 release evidence
D. 採分批遷移；第一個 wave 同時切換 workload 與撤銷 management-account access，以縮短雙軌操作時間

**答案：B**

- **A：** SOC dashboard 移出後仍有 CI runner 與 registry 暴露在最高權限帳號。若 management account 只承載 Organizations 必要操作，攻擊面才真正收斂。
- **B：** 符合本題。Management account 應保持最少資源與人員存取；服務日常營運應在 delegated administrator 或專用 member account 執行。
- **C：** Delegated administrator 本來就是為了把日常管理移出 management account；保留長期 organization-admin role 會讓同一批操作仍可影響整個 organization。
- **D：** 分批遷移是合理策略，但在替代路徑可用前撤銷既有 access 會造成營運鎖死。安全遷移需要先建立並驗證新路徑，再縮權。

**事實查證：** [Management account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html)、[Delegated administration for IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/delegated-admin.html)

### 練習題 5｜SAP｜Control Tower preventive、detective、proactive controls

平台團隊有三個需求：禁止帳號執行某些 API、找出已存在且不合規的資源，以及在 CloudFormation 建立資源前檢查 template。哪一項對 Control Tower control behavior 的配對最準確？

A. 以 SCP 實作 preventive、Config rule 實作 detective，CloudFormation template 由部署後的 Config evaluation 檢查；Control catalog 保存 control behavior、版本、target OUs、例外期限與 remediation owner，設定版本與生效時間一併寫入 change record
B. 以 CloudFormation hook 做 proactive 檢查；「Control Tower preventive、detective、proactive controls」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. Preventive 透過 Organizations policies 阻止違規；detective 透過 Config rules 找出違規；proactive 以 CloudFormation hooks 在 provisioning 前檢查
D. 在 organization root 啟用三類 controls

**答案：C**

- **A：** SCP preventive 與 Config detective 的配對正確；部署後掃描 template 則不是 proactive control，因為不合規資源已可能被建立。
- **B：** CloudFormation hook 可在 provisioning 前檢查；Config remediation 發生在資源建立後，不能取代 API 層的 preventive deny。
- **C：** 符合本題。三種 behavior 分別處理事前禁止、事後偵測與 IaC provisioning 前驗證，需依需求選擇。
- **D：** 三類 controls 可以附加在不同 scope，但直接由 root 全量啟用會把測試與 exception discovery 放到 production。若 control 已在代表 OU 驗證才適合擴大。

**事實查證：** [Control behavior and implementation](https://docs.aws.amazon.com/controltower/latest/controlreference/control-behavior.html)、[What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)

### 練習題 6｜SAP｜可重複的 account vending workflow

公司每月建立數十個 AWS 帳號。新帳號常漏掉 owner、logging、network attachment 或 budget，後續靠人工補齊。哪個方案最能建立可重複且可稽核的供應流程？

A. 使用 Account Factory 建帳號；owner、budget 與 network attachment 仍由 ticket 人工補齊；Audit trail 另標示「可重複的 account vending workflow」的設定版本、生效時間與 exception expiry
B. 以 Organizations CreateAccount 與自製 pipeline 建帳號，只記錄 email 與 OU，不發 lifecycle events；Account request record 包含 owner、email、OU、budget、network profile 與 provisioning status，具名 owner 與 approver 依固定 cadence 複核
C. 允許團隊建立 standalone accounts，並以月結流程 enroll 並補套 baseline；「可重複的 account vending workflow」的 change record 另保存 scope、owner、approver 與 rollback trigger
D. 使用 Control Tower Account Factory 或 AFT，收集帳號 metadata，套用版本化 baseline 與 customizations，並發出 lifecycle events

**答案：D**

- **A：** Account Factory 只負責建立帳號時，owner、budget 與 network 仍由 ticket 補齊，供應結果依舊不可重複。少量低頻帳號才可能容忍這種人工尾段。
- **B：** 自製 CreateAccount pipeline 可以成立，但此選項只保存 email/OU 且不產生 lifecycle events，無法驅動完整 baseline 與後續稽核。
- **C：** Standalone account 再於月結納管適合併購或特殊例外，不適合作為每月數十個帳號的標準 vending path，因為治理空窗與 drift 會被制度化。
- **D：** 符合本題。Account Factory/AFT 能把 email、OU、owner、網路、身份、logging 與成本資料納入標準化 workflow，並持續演進 customization。

**事實查證：** [Account Factory](https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html)、[Account Factory for Terraform overview](https://docs.aws.amazon.com/controltower/latest/userguide/aft-overview.html)

### 練習題 7｜SAP｜既有 organization 的 Control Tower enrollment

一個已有 180 個帳號的 organization 要導入 Control Tower。部分帳號已有自訂 CloudTrail、Config recorder、identity federation 與 production pipeline。公司不能接受全組織同時中斷。最佳導入方式是什麼？

A. 盤點 prerequisites 與既有資源，選代表性 OU/帳號 enrollment，驗證 controls、identity 與 drift remediation，再分批擴大
B. 新帳號直接由 Control Tower 供應；既有 180 個帳號保留原治理並以共同 SIEM 彙總 evidence
C. 先以新建 sandbox OU 驗證 landing zone health，通過後直接 enroll organization root 與既有 accounts
D. 移除既有 CloudTrail、Config 與 federation；以單一 maintenance window 全量重建

**答案：A**

- **A：** 符合本題。Brownfield 導入應以 prerequisites、pilot、wave、access 驗證與 drift 修復控制 blast radius。
- **B：** 只治理新帳號可作短期過渡，但 180 個既有帳號會永久保留兩套控制模型，沒有完成題目要求的 brownfield 導入。
- **C：** Sandbox pilot 能驗證 landing zone，本選項接著一次 enroll root 與所有既有帳號，仍把自訂 CloudTrail、Config 和 federation 的衝突集中在同一變更窗口。
- **D：** 全量移除既有基礎服務再重建適合可停機的空白環境；題目明確不能接受 organization-wide interruption，因此需要漸進 enrollment。

**事實查證：** [What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)、[Types of governance drift](https://docs.aws.amazon.com/controltower/latest/userguide/drift.html)

### 練習題 8｜SAP｜辨識與修復 landing-zone drift（選兩項）

Control Tower 顯示某 enrolled account 發生 drift。調查發現帳號管理者在 console 修改了一個由 landing zone 管理的資源。團隊要恢復合規並避免重演。哪兩個動作最恰當？（選兩項）

A. 判斷 drift 類型與 out-of-band change，再依 Control Tower 支援的 repair 或 re-register workflow 恢復
B. 對 drifted account 執行 re-register，讓 Control Tower 重建 landing-zone managed resources 與 baseline
C. 找出允許繞過 IaC/管理流程的權限或程序，調整 guardrail 與變更路徑以防止再次漂移
D. 只修復被修改的資源，保留可直接在 console 變更 landing-zone resources 的權限
E. 先把帳號移到 quarantine OU，依既定稽核週期統一執行 landing-zone repair 與 access review

**答案：A、C**

- **A：** 符合本題。不同 drift 類型有不同 repair 方法；先定位修改，再使用受支援的 recovery path。
- **B：** Re-register 是部分 drift 類型的修復方法，但未先辨識 drift 與衝突資源就執行，可能覆蓋既有設定或選錯 recovery workflow。
- **C：** 符合本題。只修復結果不移除 bypass，drift 會重複發生；需限制 out-of-band administration 並強化 change workflow。
- **D：** 修正資源本身可恢復當下狀態，console bypass 權限仍存在，下一次 out-of-band change 會再次造成 drift。
- **E：** 隔離 OU 能先限制風險，卻不會自動修復 landing-zone resource 或移除 bypass path；它適合 containment，不是完整 remediation。

**事實查證：** [Types of governance drift](https://docs.aws.amazon.com/controltower/latest/userguide/drift.html)、[Control behavior and implementation](https://docs.aws.amazon.com/controltower/latest/controlreference/control-behavior.html)

### 練習題 9｜SAP｜低風險推出 organization guardrail

安全團隊準備用 SCP 禁止未加密 storage API，但擔心既有 backup、incident response 與 deployment roles 被鎖住。哪個 rollout 設計最安全？

A. 在 test OU 驗證一般 deployment role；以 policy simulation 取代實際演練 backup 與 incident-response exception；Denied-call dashboard 分開呈現 deployment、backup 與 incident-response roles 的 API 結果，設定版本與生效時間一併寫入 change record
B. 用 service-access 與 CloudTrail 資料分析影響，在 test OU 放入代表帳號，驗證 emergency path 與 denied calls，再分 waves 附加並保留 rollback
C. 用 IAM Access Analyzer 與 JSON validation 檢查 SCP，略過代表 workload 的 runtime calls
D. 將 Deny 附加到 organization root，使用 NotAction 排除 security 與 incident-response roles；「低風險推出 organization guardrail」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：B**

- **A：** Policy simulation 能檢查部分授權結果，不能證明 backup 與 incident-response workflow 的實際 API、service-linked role 和 KMS 路徑可運作。
- **B：** 符合本題。先收集使用證據、pilot、監控與保留 rollback，才能在不犧牲 incident path 下逐步加強 guardrail。
- **C：** JSON validation 與 Access Analyzer 可找語法或外部存取問題，無法取代代表 workload 的 runtime call evidence；服務實際使用的 action 可能仍被 Deny。
- **D：** Root-level Deny 搭配寬廣 NotAction 適合已成熟且測試完整的 guardrail；此處仍不清楚 backup 與 emergency path，直接全量附加會放大鎖死風險。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[Policy inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html)

### 練習題 10｜SAP｜帳號 ownership 與 lifecycle accountability

財務發現 40 個 member accounts 已三個月無活躍資源，account email 屬於離職員工，也沒有 budget 或 escalation contact。為避免 orphaned accounts 持續存在，account vending 流程應新增什麼？

A. 只記錄 technical owner 與 cost center，不要求 business owner、data class 或 closure trigger；Account registry 追蹤 owner employment status、spend、last activity、data class 與 closure ticket，設定版本與生效時間一併寫入 change record
B. 由中央 cloud team 擔任每個帳號的預設 owner，再以季度 email 尋找實際負責人；Release evidence 另關聯「帳號 ownership 與 lifecycle accountability」的 pilot wave、result 與 rollback timestamp
C. 在 provisioning 時要求 business/technical owner、data class、lifecycle、budget 與 escalation metadata，並定期 quarantine、transfer 或關閉無主帳號
D. 將無主帳號 suspend access，殘留資源交由 payer team 保管，帳號 lifecycle 依年度 inventory review 決定；「帳號 ownership 與 lifecycle accountability」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：C**

- **A：** Technical owner 與 cost center 有助日常維運，卻不能回答誰接受資料、預算與關閉風險。短期 sandbox 才可能只需要這組 metadata。
- **B：** 中央 cloud team 可作 custodian，不應被當成所有帳號的 business owner；責任錯置會讓真正的預算與 lifecycle 決策者持續缺席。
- **C：** 符合本題。Account 是長期營運單位，必須在建立時就有結構化 ownership、成本與關閉流程。
- **D：** Suspend access 是 orphaned account 的 containment 手段，年度 review 對已離職 owner 與持續費用反應太慢，也沒有預先定義 transfer 或 closure authority。

**事實查證：** [Account Factory](https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html)、[Account tags for cost allocation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/account-tags-cost-allocation.html)、[Managing costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「依business unit、environment與data sensitivity設計OU/accou…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「企業需要以帳號隔離billing、quota、權限與blast radius，同時保留一致治理。」，所以「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」能直接滿足它；若constraint改成「單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」。替代方案「單帳號起步簡單，但規模後policy、quota與事故隔離難以管理。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「企業需要以帳號隔離billing、quota、權限與blast radius，同時保留一致治理。」，排除會導致「把OU當網路邊界，或帳號切得太碎卻沒有自動供應與lifecycle。」的選項，再選「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」。本章對應的代表task包括：SAP-1.4 Design a multi-account AWS environment；SAP-1.5 Determine cost optimization and visibility strategies；SAP-3.1 Determine a strategy to improve overall operational excellence。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「依business unit、environment與data sensitivity設計OU/account，Control Tower建立landing zone。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「accounts are strong operational and security boundaries」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 80 章　Centralized Network 與 Inspection VPC

大型組織需要shared connectivity、egress control與流量檢查，但中央化會形成關鍵路徑。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：Prod、dev與partner networks需不同route domain，internet流量必須集中稽核。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：大型組織需要shared connectivity、egress control與流量檢查，但中央化會形成關鍵路徑。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS Transit Gateway負責主要工作，AWS Network Firewall提醒我們答案不是永遠固定。本章會走向「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Prod、dev與partner networks需不同route domain，internet流量必須集中稽核。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Transit Gateway]
          │ 以regional hub連接大量VPC、VPN與Direct Connect。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Network Firewall：在VPC中提供managed stateful/stateless L3–L7 network inspe…
  · Gateway Load Balancer：透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。

失敗時先找：所有流量經單AZappliance，return path不對稱或中央NAT超載。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Transit Gateway有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Transit Gateway和AWS Network Firewall並不是兩個任意的產品名稱。前者適合本章，是因為「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」直接回應了眼前的問題；後者描述的「每VPC自治egress降低中央依賴，但policy、cost與audit較分散。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：所有流量經單AZappliance，return path不對稱或中央NAT超載。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「centralize policy while distributing capacity and failure domains」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 |
| Gateway Load Balancer | 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。 | GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。 |

## 把全圖套進一個具體案例

**場景：** Prod、dev與partner networks需不同route domain，internet流量必須集中稽核。

1. 故事的起點：Prod、dev與partner networks需不同route domain，internet流量必須集中稽核。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Transit Gateway負責「以regional hub連接大量VPC、VPN與Direct Connect。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Network Firewall、Gateway Load Balancer各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「所有流量經單AZappliance，return path不對稱或中央NAT超載。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Transit Gateway

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：大型組織需要shared connectivity、egress control與流量檢查，但中央化會形成關鍵路徑。
- **具體例子／邊界：** 在「Prod、dev與partner networks需不同route domain，internet流量必須集中稽核。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Network Firewall

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：每VPC自治egress降低中央依賴，但policy、cost與audit較分散。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：所有流量經單AZappliance，return path不對稱或中央NAT超載。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：centralize policy while distributing capacity and failure domains。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transitive routing

A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### AWS Transit Gateway

- **功用：** 以regional hub連接大量VPC、VPN與Direct Connect。
- **底層機制：** Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。
- **關鍵設定：** attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
- **選擇時機：** 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。
- **替換時機：** 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。

### AWS Network Firewall

- **功用：** 在VPC中提供managed stateful/stateless L3–L7 network inspection。
- **底層機制：** Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。
- **關鍵設定：** firewall policy、stateless/stateful rule groups、HOME_NET、TLS inspection、logging與route symmetry。
- **選擇時機：** 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。
- **替換時機：** 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。

### Gateway Load Balancer

- **功用：** 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。
- **底層機制：** GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。
- **關鍵設定：** GENEVE 6081、GWLB endpoints、route tables、target health、appliance mode與cross-zone。
- **選擇時機：** 集中deep packet inspection且需水平擴展appliances。
- **替換時機：** AWS-native stateful rules可直接用Network Firewall；一般app traffic用ALB/NLB。

## 考前與實作時再查：設定操作手冊

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

### AWS Network Firewall：逐項設定說明

#### `firewall policy`

- **控制什麼：** `firewall policy`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `stateless/stateful rule groups`

- **控制什麼：** `stateless/stateful rule groups`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `HOME_NET`

- **控制什麼：** `HOME_NET`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `TLS inspection`

- **控制什麼：** `TLS inspection`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `route symmetry`

- **控制什麼：** `route symmetry`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

### Gateway Load Balancer：逐項設定說明

#### `GENEVE 6081`

- **控制什麼：** GWLB以UDP 6081上的GENEVE封裝原始IP flow與metadata，透明送到支援GENEVE的firewall、IDS/IPS或其他virtual appliance。
- **何時需要：** 需要在不改變application endpoint的情況下，水平擴展第三方network appliance並保留雙向flow context時。
- **怎麼設定／驗證：** Appliance必須在UDP 6081監聽並正確decapsulate/recapsulate；SG/NACL允許health與GENEVE traffic，再用packet capture驗證。
- **常見錯法：** GENEVE不是一般application listener；appliance只接受普通Ethernet/IP或錯誤MTU時，會丟包或產生難查的fragmentation。

#### `GWLB endpoints`

- **控制什麼：** GWLBe是consumer VPC中的PrivateLink gateway endpoint，route table可把要檢查的流量導入provider端GWLB appliance service。
- **何時需要：** 多個spoke VPC要共用中央inspection fleet，又不想把所有網路完整route到provider VPC時。
- **怎麼設定／驗證：** 每個需要的AZ建立GWLBe並接受service；在ingress、subnet或TGW路徑加入指向vpce-*的routes，逐方向驗證。
- **常見錯法：** 單AZ endpoint會形成跨AZ或故障問題；endpoint存在但route未指向它時，流量完全不會經過inspection。

#### `route tables`

- **控制什麼：** 決定哪些來源／目的flows被送到GWLBe，以及appliance處理後如何回到原路徑，是service insertion的核心。
- **何時需要：** Internet ingress/egress、east-west或TGW centralized inspection需要強制經過appliance時。
- **怎麼設定／驗證：** 分別畫出forward與return route，對public subnet、application subnet、endpoint subnet與TGW tables設定精確next hop並測試對稱性。
- **常見錯法：** 只改去程不改回程會繞過stateful appliance或造成timeout；過寬default route也可能把管理流量送進錯誤inspection path。

#### `target health`

- **控制什麼：** GWLB以health check判斷appliance能否處理flow；不健康target停止接收新flows，healthy fleet共同分擔流量。
- **何時需要：** Appliance可能process crash、license失效、CPU飽和或無法轉送封包，需要自動隔離時。
- **怎麼設定／驗證：** 設定能代表data-plane readiness的health protocol/port與threshold，搭配ASG capacity及appliance metrics測試replacement。
- **常見錯法：** 管理介面回200不代表轉送面正常；health check過於表面會留下black hole，過深則可能同時摘除整個fleet。

#### `appliance flow stickiness`

- **控制什麼：** 以flow的5-tuple或3-tuple維持同一connection方向持續送往同一appliance，讓stateful inspection保留session狀態。
- **何時需要：** Appliance需要看到完整connection並保存NAT、TLS或firewall session state時。
- **怎麼設定／驗證：** 依traffic特性選擇flow stickiness屬性，確保forward/return path對稱；用長連線、fragment與failover案例驗證。
- **常見錯法：** Stickiness不能在appliance故障時遷移其memory state；不適合的tuple選擇也可能讓大量flows集中到少數targets。

#### `cross-zone`

- **控制什麼：** 決定GWLB node是否可把flow送到其他AZ的healthy appliances，在容量均衡、故障隔離與跨AZ成本之間取捨。
- **何時需要：** 各AZ appliance capacity不均或需要在單AZtarget不足時使用其他AZ容量時。
- **怎麼設定／驗證：** 設定cross-zone attribute，確保所有AZ都有對稱route與足夠MTU；監控每AZflows、appliance utilization及cross-AZ bytes。
- **常見錯法：** 開啟不能修正單一appliance bottleneck，且跨AZpath若未對稱會讓stateful inspection失效並增加data transfer費。

## 讀到這裡，請用自己的話說一次

1. AWS Transit Gateway的責任：以regional hub連接大量VPC、VPN與Direct Connect。
2. 底層機制：Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。
3. 第一個要看的設定：attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
4. 選擇邏輯：TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。
5. 不要混淆：AWS Network Firewall的責任是「在VPC中提供managed stateful/stateless L3–L7 network inspection。」；它不會自動取代AWS Transit Gateway。
6. 替換訊號：只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。
7. 最常見錯法：所有流量經單AZappliance，return path不對稱或中央NAT超載。
8. 可移植原則：centralize policy while distributing capacity and failure domains。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 | 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。 | 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 | 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。 | 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。 |
| Gateway Load Balancer | 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。 | GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。 | 集中deep packet inspection且需水平擴展appliances。 | AWS-native stateful rules可直接用Network Firewall；一般app traffic用ALB/NLB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 每VPC自治egress降低中央依賴，但policy、cost與audit較分散。 | 只有當題目條件明確改變時才可能合理。 | 所有流量經單AZappliance，return path不對稱或中央NAT超載。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「每VPC自治egress降低中央依賴，但policy、cost與audit較分散。」之間做選擇。
- 認得常考設定：attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment。

## 本章 10 題考題

### 練習題 1｜SAP｜TGW、peering、PrivateLink 選型

一家公司有 70 個 VPC，需要 transitive hub routing 與 prod/dev route-domain segmentation；另有一個供合作夥伴使用的私有 API，只希望暴露該服務而不是整個 VPC。哪個設計最符合兩種需求？

A. 內部 VPC 使用 Transit Gateway；合作夥伴的單一服務以 PrivateLink endpoint service 暴露；實作時另記錄 owner、驗收指標與回復條件
B. 用 Transit Gateway 連內部 VPC，也讓合作夥伴取得一個受限 TGW attachment 與專用 route table
C. 內部維持少量 peering，合作夥伴 API 使用 PrivateLink；route exchange 維持原架構 70 個 VPC 的 transitive routing；Network inventory 對每個 VPC 保存 attachment、route domain、CIDR 與 endpoint-service owner，相關 alarms 與 rollback timestamp 納入 release evidence
D. 以 full-mesh peering 連接 70 個 VPC，CIDR 由 IPAM 配置，routes 透過中央 IaC 維護

**答案：A**

- **A：** 符合本題。TGW 適合多附件的 hub 與 route-table segmentation；PrivateLink 適合只發布一個服務給 consumers。
- **B：** TGW attachment 能建立受控 routed connectivity，適合合作夥伴需要多個網段服務時；題目只允許一個 API，TGW 仍暴露較大的路由與信任面。
- **C：** PrivateLink 符合合作夥伴需求，但少量 peering 沒有提供 70 個 VPC 所需的 transitive hub 與 prod/dev route-domain segmentation。
- **D：** Full-mesh peering 可連接少量 VPC，peering 本身不具 transitive routing；70 個 VPC 的連線、route 與分段管理會快速膨脹。

**事實查證：** [Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)、[AWS PrivateLink concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)

### 練習題 2｜SAP｜TGW association 與 propagation 分段

Prod、dev 與 shared-services VPC 都連到同一 TGW。Prod 與 dev 必須彼此不可路由，但兩者都要存取 shared services。哪個 TGW route-table 設計最合理？

A. Prod 與 dev 共用一張 TGW route table；以 NACL 阻擋兩者流量並允許 shared services
B. Prod 與 dev attachments 分別 association 到不同 route tables，只向各自表提供 shared-services routes；shared-services 表再依需求提供回程 routes
C. 分開 association route tables；把 prod 與 dev routes 都 propagation 到兩張表；Release evidence 另關聯「TGW association 與 propagation 分段」的 pilot wave、result 與 rollback timestamp
D. Prod/dev attachments 切到獨立 route tables；shared-services routes 採單向 propagation，回程使用 shared table 的 static routes；Route-table snapshots 完整記錄 attachment associations、propagations、static prefixes 與回程路徑，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** NACL 可在 subnet 邊界過濾封包，卻不能取代 TGW route-domain 隔離；prod/dev routes 仍同時存在於共用 TGW table。
- **B：** 符合本題。Association 決定附件流量查哪張表，propagation/static routes 決定可到達哪些 attachment；分表可控制 prod/dev 隔離。
- **C：** 分開 association 是正確起點，但把 prod 與 dev prefixes 都 propagation 到兩張表會重新建立雙向可達性，抵銷分表目的。
- **D：** 切換 association 可以改變查表邏輯；shared-services 的去程與回程 route 未同時存在時，連線仍會失敗。

**事實查證：** [Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 3｜SAP｜stateful inspection 的對稱路由（選兩項）

公司要讓 VPC A 到 VPC B 的 east-west traffic 強制通過 inspection VPC 中的 stateful appliances。測試發現 forward path 經過 appliance，但 return path 繞過它，連線被重設。哪兩個修正最重要？（選兩項）

A. 建立 spoke→inspection 與 inspection→destination 的明確 TGW/VPC routes，並同樣設計 reverse path
B. 只修正 spoke 到 inspection 的 forward routes，destination 的回程仍直接指向來源 spoke
C. 啟用 appliance mode；讓部分 east-west traffic 使用繞過 inspection 的較特定 static route
D. 將 production traffic 導入 stateful appliances，再以 flow logs 找出非對稱回程
E. 在需要保持 flow symmetry 的 inspection attachment 啟用並驗證 appliance mode

**答案：A、E**

- **A：** 符合本題。Inline inspection 必須完整控制去程與回程，否則 state table 看不到完整 flow。
- **B：** 只改去程可讓第一批封包抵達 appliance，回程直接回 source 仍造成 asymmetric flow，stateful firewall 會看不到完整連線。
- **C：** Appliance mode 有助維持 attachment/AZ affinity，但較特定的 bypass route 仍可讓流量避開檢查；兩者必須與完整 route design 配合。
- **D：** Flow Logs 能協助診斷非對稱路徑，不會強制 production traffic 的回程經過同一 stateful appliance。它適合觀測，不是路由修正。
- **E：** 符合本題。TGW appliance mode 可在適當 topology 中維持流量經過相同 AZ/attachment path，應與明確路由一起驗證。

**事實查證：** [Transit Gateway appliance mode](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#appliance-mode)、[AWS Network Firewall route tables](https://docs.aws.amazon.com/network-firewall/latest/developerguide/route-tables.html)

### 練習題 4｜SAP｜Network Firewall 多 AZ endpoint 路由

Inspection VPC 橫跨三個 AZ，但所有 spoke egress 都被送到 AZ-a 的單一 Network Firewall endpoint。AZ-a 故障時，三個 AZ 的 workload 都失去 egress，平時也產生跨 AZ hairpin。應如何改善？

A. 建立三個 firewall endpoints；所有 AZ route tables 仍固定指向 AZ-a endpoint
B. 每個 AZ 使用 NAT Gateway 分散 egress，inspection 仍集中經過 AZ-a firewall endpoint
C. 在需要的 AZ 建立 firewall endpoints，讓各 AZ route table 導向本 AZ endpoint，並測試 endpoint/AZ 故障路徑；Flow Logs、firewall endpoint health、bytes 與 cross-AZ charges 都依 Availability Zone 分組，相關 alarms 與 rollback timestamp 納入 release evidence
D. 在三個 AZ 建立 firewall endpoints，但所有 spoke default routes 仍經中央 inspection route table 選擇單一 active endpoint

**答案：C**

- **A：** 建立多個 endpoints 只是增加可用資源；所有 route tables 仍指向 AZ-a 時，故障域與 cross-AZ hairpin 都沒有改變。
- **B：** 每 AZ NAT Gateway 可分散 NAT failure，封包仍必須穿越 AZ-a 的單一 firewall endpoint，因此真正的 inspection bottleneck 仍在。
- **C：** 符合本題。AZ-aligned endpoints 與 routes 可分散故障域並避免不必要 hairpin；仍需規劃 endpoint failure 行為。
- **D：** 把 routes 指向新增 endpoints 是必要步驟，但若沒有讓各來源 AZ 對齊本 AZ endpoint，仍可能形成集中故障或不必要的跨 AZ path。

**事實查證：** [AWS Network Firewall deployment models](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)、[AWS Network Firewall route tables](https://docs.aws.amazon.com/network-firewall/latest/developerguide/route-tables.html)

### 練習題 5｜SAP｜Network Firewall 與 GWLB 的責任邊界

企業已有必須保留的第三方 firewall image、vendor rule engine 與授權，並要求 appliance fleet 可水平擴展且透明插入 traffic path。哪個方案最合適？

A. 使用 AWS Network Firewall 重建 vendor 規則，第三方 appliance image 與既有授權依汰換計畫退場
B. 以 NLB 分配 TCP flows 到 firewall instances，自行實作 flow symmetry、健康與 transparent insertion；Appliance dashboard 追蹤 flow count、health、capacity、image version、license 與 rollout wave，具名 owner 與 approver 依固定 cadence 複核
C. 所有流量導入單一 vendor appliance，GWLB 與多 AZ fleet 只在容量擴張時啟用
D. 使用 Gateway Load Balancer 將 flow 分配給相容的第三方 appliances，團隊仍負責 appliance policy、capacity 與版本

**答案：D**

- **A：** AWS Network Firewall 是受管防火牆，不能載入既有第三方 VM image 或原 vendor runtime；若公司願意重建規則並更換產品才適合。
- **B：** NLB 可分配 TCP connections，但不提供 GWLB 的透明 bump-in-the-wire 與 GENEVE appliance insertion contract，flow symmetry 與 service chaining 需自行實作。
- **C：** 單一 vendor appliance 可保留原規則引擎，卻無法滿足水平擴展與 appliance failure isolation；GWLB fleet 必須在正常架構中就生效。
- **D：** 符合本題。GWLB 以透明的 appliance insertion 與 load distribution 支援相容 vendor appliances，但不替團隊撰寫或操作 firewall policy。

**事實查證：** [AWS Network Firewall deployment models](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)、[Gateway Load Balancer overview](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/introduction.html)

### 練習題 6｜SAP｜跨帳號共享 TGW 的 ownership

Network account 透過 AWS RAM 將 TGW 分享給 30 個 workload accounts。某團隊以為接受 share 後，VPC 就會自動與所有 spokes 互通。實際上 attachment 已建立但 packet 不通。最準確的解釋是什麼？

A. RAM 只分享使用 TGW 的能力；owner 仍管理 TGW route tables/政策，participants 需建立或接受 attachments，端到端 VPC routes 與安全規則也必須成立
B. Participant 建立 TGW attachment 與 VPC routes；owner 將 attachment association 到預設 TGW route table
C. Owner 分享 TGW 並啟用 route propagation，spoke security groups 與 return routes 維持原設定；Release evidence 另關聯「跨帳號共享 TGW 的 ownership」的 pilot wave、result 與 rollback timestamp
D. Owner 自動接受 attachment requests 並 association 到共用 default TGW route table，participants 依中央變更流程維護 VPC routes

**答案：A**

- **A：** 符合本題。Share、attachment、TGW association/propagation、VPC subnet route 與 security controls 是不同步驟，需明確 ownership。
- **B：** 建立 attachment、VPC routes 與預設 association 只完成部分 data path；若 TGW table 沒有正確 propagation/static routes，或 SG/NACL/回程不匹配，仍不可達。
- **C：** Route propagation 可填入 TGW table，不能修改 spoke subnet route tables、security rules 或 return path。RAM share 也不會替 participant 完成這些設定。
- **D：** 廣泛接受 attachments 適合單一信任域的簡單 hub；30 個 workload accounts 需要先定義 route-domain ownership，否則可達性與 blast radius 都不可控。

**事實查證：** [Work with shared transit gateways](https://docs.aws.amazon.com/vpc/latest/tgw/working-with-transit-gateways.html)、[Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 7｜SAP｜Direct Connect 的 resilient hybrid path

一個交易平台只有一條 Direct Connect connection 與一個 virtual interface。架構師說 DX 是專線，因此不需要其他連線或 failover test。公司要求任何單一 circuit 或 location 故障都不能中斷交易。應如何設計？

A. 在同一 Direct Connect location 建兩條 connections，兩者接到同一 customer router；Internet VPN 也由該 router 終止；Audit trail 另標示「Direct Connect 的 resilient hybrid path」的設定版本、生效時間與 exception expiry
B. 依 resiliency 需求配置不同 connection/location 的冗餘 DX，必要時加入已測試 VPN backup，並驗證 BGP、routes、MTU 與 application/DNS failover
C. 跨 location 建冗餘 DX；兩條路徑共用同一 customer router 與電信 last mile；「Direct Connect 的 resilient hybrid path」的 change record 另保存 scope、owner、approver 與 rollback trigger
D. 使用兩個 hosted virtual interfaces 經同一條 physical DX connection，BGP 以不同 local preference 建 primary/backup；Hybrid telemetry 保存 BGP route changes、circuit state、packet loss、MTU errors 與 application probes，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** 同一 location 的兩條 DX 可防單一 port/circuit 故障；若 customer router、last mile 或 location 同時是共同依賴，就不能滿足 location failure 要求。
- **B：** 符合本題。冗餘必須跨足實際故障域，並以 routing 與 application 層測試證明備援路徑可用。
- **C：** 跨 location DX 已分散 AWS 端位置，兩條路徑仍共用 customer router 與電信 last mile，企業端單點即可同時中斷。
- **D：** 冗餘連線存在不代表 traffic 會依預期切換；BGP preference、MTU、DNS 與 application session 必須在上線前以 failover test 證明。

**事實查證：** [Resilience in AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/disaster-recovery-resiliency.html)、[Direct Connect gateways and Transit Gateway associations](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-transit-gateways.html)

### 練習題 8｜SAP｜處理併購後 overlapping CIDR（選兩項）

併購公司的 VPC 與母公司都使用 10.0.0.0/16，短期只需讓母公司呼叫對方一個 payment API，長期才需要廣泛雙向互通。哪兩個做法合理？（選兩項）

A. 短期在其中一側做大範圍 NAT 轉址，讓兩個重疊網路先建立 routed connectivity
B. 短期以 PrivateLink 或受控 proxy 暴露單一服務，避免要求兩邊建立完整 routed connectivity
C. 目前服務以 PrivateLink 暴露；新增整合也採一服務一個 endpoint service 的模式
D. 規劃分階段 renumbering/IPAM remediation，讓未來需要廣泛互通的 networks 取得不重疊位址
E. 把兩個重疊 CIDR attachments 接到同一 TGW route domain，再依實際衝突逐條修 route

**答案：B、D**

- **A：** NAT 可在重疊 CIDR 間建立有限連通，適合少量固定 flows；大範圍雙向 NAT 會增加 address mapping、DNS 與除錯成本，不如先縮成單一服務。
- **B：** 符合本題。PrivateLink 把問題縮小為 service consumption，不需向 consumer 公布 provider 的整個 CIDR。
- **C：** 逐服務 PrivateLink 可長期維持 service-oriented integration；題目明示未來需要廣泛雙向 routed access，因此仍需 address remediation。
- **D：** 符合本題。若最終需求是廣泛、雙向 routed access，仍需治理位址並分階段 renumber。
- **E：** TGW route domain 以 destination prefix 選路，兩個相同 10.0.0.0/16 無法在同一 routing context 中可靠區分；逐條 route 也不能消除 prefix ambiguity。

**事實查證：** [AWS PrivateLink concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)、[Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 9｜SAP｜Route 53 Resolver hybrid DNS 方向

On-premises clients 必須解析 AWS private hosted zone；VPC workloads 也必須解析公司內部 `corp.example` DNS。團隊另要封鎖已知惡意 domain。哪個設計正確？

A. 部署 inbound Resolver endpoints 供 on-premises 查 AWS names；AWS 到 on-premises 仍查 public DNS
B. 使用 outbound endpoints 與 forwarding rules，卻把 inbound endpoint 當成 DNS Firewall policy engine；DNS query logs 區分 inbound、outbound、forwarded、recursive 與 firewall-blocked requests，具名 owner 與 approver 依固定 cadence 複核
C. 以多 AZ inbound endpoints 接收 on-premises→AWS 查詢，以 outbound endpoints 與 forwarding rules 處理 AWS→on-premises 查詢；另用 DNS Firewall 套用 domain policy
D. Corporate DNS 將 AWS zones 全量轉送到一個 inbound endpoint IP，第二個 IP 只作 health-check target

**答案：C**

- **A：** Inbound endpoint 只處理 on-premises 對 VPC Resolver 的查詢；AWS workload 查 corp.example 還需要 outbound endpoint 與 forwarding rule。
- **B：** Outbound endpoint/forwarding rule 的方向正確；DNS Firewall 是套用在 VPC Resolver 的獨立 domain-list/rule-group 機制，不是 inbound endpoint 的功能。
- **C：** 符合本題。兩個 endpoint 方向、conditional rules 與 DNS security policy 是三個不同責任，且 endpoints 應跨 AZ。
- **D：** 把 private zone 轉送到 inbound endpoint 可解析 AWS names，但只依賴一個 endpoint IP 會失去跨 AZ 容錯，第二個 IP 不能只當 health target。

**事實查證：** [What is Route 53 VPC Resolver?](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)、[Resolving DNS queries between VPCs and on-premises networks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-DSN-queries-to-vpc.html)、[How Route 53 Resolver DNS Firewall works](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-overview.html)

### 練習題 10｜SAP｜central egress 的 rollout、成本與 blast radius

公司要把 120 個 VPC 的 internet egress 改經中央 TGW、NAT 與 Network Firewall。方案可能增加 cross-AZ/TGW processing cost，也會把中央 path 變成共同依賴。哪個 rollout 最穩健？

A. 集中 egress 但保留單一 AZ NAT/firewall path，以較低固定成本換取較大故障域
B. 每個 VPC 保留分散 egress，使用 Firewall Manager 統一規則並集中 Flow Logs 與 policy review；Egress dashboard 顯示 bytes、cross-AZ/TGW cost、NAT port usage、firewall capacity 與 latency，具名 owner 與 approver 依固定 cadence 複核
C. 一次改完所有 default routes；以次日帳單與 incident tickets 評估容量及 rollback；Release evidence 另關聯「central egress 的 rollout、成本與 blast radius」的 pilot wave、result 與 rollback timestamp
D. 選代表 spokes 分 waves 改 route，量測 bytes、latency、firewall/NAT capacity 與成本，保留已測 fallback route，並指定中央 network on-call owner

**答案：D**

- **A：** 單 AZ 中央 NAT/firewall 能降低初期成本，會把所有 spokes 綁到同一 AZ failure domain，與題目要控制共同依賴的目標相反。
- **B：** 分散 egress 搭配 Firewall Manager 適合自治與故障隔離優先的組織；此題的目標是遷移到中央 TGW/NAT/inspection path，因此它沒有驗證新架構。
- **C：** 一次修改全部 default routes 能快速完成切換，但帳單與 ticket 是落後訊號，無法在容量耗盡或 asymmetric routing 時限制 blast radius。
- **D：** 符合本題。Centralization 同時改變 cost 與 failure domain；wave、evidence、capacity owner 和 rollback 缺一不可。

**事實查證：** [AWS Network Firewall deployment models](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)、[Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「TGW連接spokes，route tables分段，inspection VPC使用Network Fi…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「大型組織需要shared connectivity、egress control與流量檢查，但中央化會形成關鍵路徑。」，所以「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」能直接滿足它；若constraint改成「每VPC自治egress降低中央依賴，但policy、cost與audit較分散。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」。替代方案「每VPC自治egress降低中央依賴，但policy、cost與audit較分散。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「所有流量經單AZappliance，return path不對稱或中央NAT超載。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「大型組織需要shared connectivity、egress control與流量檢查，但中央化會形成關鍵路徑。」，排除會導致「所有流量經單AZappliance，return path不對稱或中央NAT超載。」的選項，再選「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」。本章對應的代表task包括：SAP-1.1 Architect network connectivity strategies；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「TGW連接spokes，route tables分段，inspection VPC使用Network Firewall/GWLB並確保對稱路由。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「centralize policy while distributing capacity and failure domains」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 81 章　Centralized Logging 與 Security Accounts

攻擊者取得workload帳號後不應能刪除稽核證據或停用偵測。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：SOC需查詢全組織API與finding，工作負載管理者不得修改歷史log。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：攻擊者取得workload帳號後不應能刪除稽核證據或停用偵測。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS CloudTrail，對照角色是AWS Config。我們選擇「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：SOC需查詢全組織API與finding，工作負載管理者不得修改歷史log。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS CloudTrail]
          │ 記錄AWS API與account activity供audit與調查。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Config：記錄AWS resource configuration history並評估rules/conforma…
  · Amazon GuardDuty：從AWS telemetry偵測credential compromise、惡意活動與異常行為。
  · AWS Security Hub：集中標準化security findings並執行security standards checks。

失敗時先找：Log bucket policy允許source帳號刪除，或所有security admin都使用management account。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS CloudTrail有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS CloudTrail和AWS Config並不是兩個任意的產品名稱。前者適合本章，是因為「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」直接回應了眼前的問題；後者描述的「各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Log bucket policy允許source帳號刪除，或所有security admin都使用management account。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「security evidence must outlive the compromised account」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS CloudTrail | 記錄AWS API與account activity供audit與調查。 | Management events預設進event history；trail/event data store可保存management/data/insight events。 |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 |
| Amazon GuardDuty | 從AWS telemetry偵測credential compromise、惡意活動與異常行為。 | Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 |

## 把全圖套進一個具體案例

**場景：** SOC需查詢全組織API與finding，工作負載管理者不得修改歷史log。

1. 故事的起點：SOC需查詢全組織API與finding，工作負載管理者不得修改歷史log。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS CloudTrail負責「記錄AWS API與account activity供audit與調查。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Management events預設進event history；trail/event data store可保存management/data/insight events。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Config、Amazon GuardDuty、AWS Security Hub各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Log bucket policy允許source帳號刪除，或所有security admin都使用management account。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「application log與performance metric不是CloudTrail用途。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Security Lake 與 Incident Response：先保存可關聯的證據，再談自動修復

CloudTrail、VPC Flow Logs、Route 53 query logs、WAF logs 與 findings 各自描述不同事件。Security Lake 將多帳號、多 Region 的 security data 集中到你帳號內的 S3，轉成 OCSF 與 Parquet，讓 SIEM／Athena／其他 subscriber 以一致 schema 分析。它不是 GuardDuty 的替代品：前者是資料層，後者是偵測服務。

```text
accounts/Regions
  ├─ CloudTrail / VPC Flow / DNS / WAF
  ├─ Security Hub findings
  └─ custom sources
          ▼ normalize OCSF + Parquet
     Security Lake (S3 owned by customer)
          ├─ query subscriber
          ├─ data-access subscriber / SIEM
          └─ incident evidence retention
                    ▼
detect → triage → contain → preserve → eradicate → recover → learn
```

#### 一個事件不能只留下『已關閉 instance』

```Incident record
incident:
  finding_id: gd-...
  affected_resource: i-...
  timeline_sources:
    - cloudtrail
    - vpc_flow_logs
    - dns_query_logs
  containment:
    action: isolate-with-quarantine-sg
    approved_by: security-oncall
  evidence:
    snapshot_ids: [...]
    log_retention_lock: enabled
  recovery:
    rebuild_from_known_good_image: true
  lessons:
    preventive_control_owner: platform-security
```

1. Containment 要限制 attacker movement，同時避免先銷毀 memory/disk/log evidence；動作順序由 incident severity 與 runbook 決定。
2. Security Lake subscriber 只能取得被授權 sources/Regions；集中不代表所有分析工具自動擁有全資料。
3. Rollup Region、retention、KMS、Lake Formation 與跨帳號 delegated admin 都是 data residency 與 blast-radius 決策。

**選擇邊界：** 只要查單一服務近期 log，CloudWatch Logs/S3/Athena 可能足夠；需要組織級 normalization、長期 security analytics 與多個 subscribers 才評估 Security Lake。偵測、調查、儲存、回應仍是不同責任。

**考試範圍：** 集中 logging、delegated admin、retention 與 incident runbook 是 SAP 高頻；SAA 先分清 CloudTrail、Config、CloudWatch、GuardDuty、Security Hub 與原始 logs。

- [AWS：What is Amazon Security Lake?](https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html)
- [AWS：Security incident response guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html)

## 需要時再查：四個閱讀支點

### AWS CloudTrail

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：攻擊者取得workload帳號後不應能刪除稽核證據或停用偵測。
- **具體例子／邊界：** 在「SOC需查詢全組織API與finding，工作負載管理者不得修改歷史log。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Config

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Log bucket policy允許source帳號刪除，或所有security admin都使用management account。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：security evidence must outlive the compromised account。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS CloudTrail

- **功用：** 記錄AWS API與account activity供audit與調查。
- **底層機制：** Management events預設進event history；trail/event data store可保存management/data/insight events。
- **關鍵設定：** multi-Region/organization trail、management/data events、S3/KMS、log validation、CloudWatch integration與Lake。
- **選擇時機：** 追查who/what/when/source IP、不可否認audit與security detection。
- **替換時機：** application log與performance metric不是CloudTrail用途。

### AWS Config

- **功用：** 記錄AWS resource configuration history並評估rules/conformance packs。
- **底層機制：** Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。
- **關鍵設定：** recorder、delivery channel、managed/custom rules、conformance packs、aggregator與remediation。
- **選擇時機：** 回答「資源何時變成這樣」、組態合規與多帳號inventory。
- **替換時機：** 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。

### Amazon GuardDuty

- **功用：** 從AWS telemetry偵測credential compromise、惡意活動與異常行為。
- **底層機制：** Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。
- **關鍵設定：** detector、protection plans、trusted IP/threat lists、publishing frequency、organization admin與EventBridge response。
- **選擇時機：** 需要managed threat detection與多帳號集中findings。
- **替換時機：** 漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。

### AWS Security Hub

- **功用：** 集中標準化security findings並執行security standards checks。
- **底層機制：** 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。
- **關鍵設定：** standards/controls、central configuration、aggregator Region、automation rules與EventBridge。
- **選擇時機：** SOC需要跨帳號單一finding queue與compliance view。
- **替換時機：** 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。

## 考前與實作時再查：設定操作手冊

### AWS CloudTrail：逐項設定說明

#### `multi-Region/organization trail`

- **控制什麼：** `multi-Region/organization trail`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS CloudTrail前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `management/data events`

- **控制什麼：** `management/data events`決定AWS CloudTrail蒐集哪些control/data-plane audit events，以及如何集中查詢或監控。
- **何時需要：** 需要回答誰在何時修改resource、誰讀寫敏感資料，或集中多帳號事件調查時。
- **怎麼設定／驗證：** 選擇management/data event selectors、accounts/Regions、retention與S3/Lake/CloudWatch destination；用已知API call驗證事件可查。
- **常見錯法：** Data events量大且可能昂貴；只開management events看不到S3 object/Lambda invoke等data-plane行為。

#### `S3/KMS`

- **控制什麼：** `S3/KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「追查who/what/when/source IP、不可否認audit與security detection。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudTrail指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `log validation`

- **控制什麼：** `log validation`定義AWS CloudTrail用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `CloudWatch integration`

- **控制什麼：** `CloudWatch integration`把AWS CloudTrail與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `Lake`

- **控制什麼：** `Lake`決定AWS CloudTrail蒐集哪些control/data-plane audit events，以及如何集中查詢或監控。
- **何時需要：** 需要回答誰在何時修改resource、誰讀寫敏感資料，或集中多帳號事件調查時。
- **怎麼設定／驗證：** 選擇management/data event selectors、accounts/Regions、retention與S3/Lake/CloudWatch destination；用已知API call驗證事件可查。
- **常見錯法：** Data events量大且可能昂貴；只開management events看不到S3 object/Lambda invoke等data-plane行為。

### AWS Config：逐項設定說明

#### `recorder`

- **控制什麼：** `recorder`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `delivery channel`

- **控制什麼：** `delivery channel`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `managed/custom rules`

- **控制什麼：** `managed/custom rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「回答「資源何時變成這樣」、組態合規與多帳號inventory。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Config以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `conformance packs`

- **控制什麼：** `conformance packs`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `aggregator`

- **控制什麼：** `aggregator`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `remediation`

- **控制什麼：** `remediation`把AWS Config與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon GuardDuty：逐項設定說明

#### `detector`

- **控制什麼：** `detector`選擇Amazon GuardDuty分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `protection plans`

- **控制什麼：** `protection plans`選擇Amazon GuardDuty分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `trusted IP/threat lists`

- **控制什麼：** `trusted IP/threat lists`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用Amazon GuardDuty阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `publishing frequency`

- **控制什麼：** `publishing frequency`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要managed threat detection與多帳號集中findings。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon GuardDuty選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `organization admin`

- **控制什麼：** `organization admin`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「需要managed threat detection與多帳號集中findings。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon GuardDuty建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `EventBridge response`

- **控制什麼：** `EventBridge response`把Amazon GuardDuty與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

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

## 讀到這裡，請用自己的話說一次

1. AWS CloudTrail的責任：記錄AWS API與account activity供audit與調查。
2. 底層機制：Management events預設進event history；trail/event data store可保存management/data/insight events。
3. 第一個要看的設定：multi-Region/organization trail、management/data events、S3/KMS、log validation、CloudWatch integration與Lake。
4. 選擇邏輯：建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。
5. 不要混淆：AWS Config的責任是「記錄AWS resource configuration history並評估rules/conformance packs。」；它不會自動取代AWS CloudTrail。
6. 替換訊號：application log與performance metric不是CloudTrail用途。
7. 最常見錯法：Log bucket policy允許source帳號刪除，或所有security admin都使用management account。
8. 可移植原則：security evidence must outlive the compromised account。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS CloudTrail | 記錄AWS API與account activity供audit與調查。 | Management events預設進event history；trail/event data store可保存management/data/insight events。 | 追查who/what/when/source IP、不可否認audit與security detection。 | application log與performance metric不是CloudTrail用途。 |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 | 回答「資源何時變成這樣」、組態合規與多帳號inventory。 | 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。 |
| Amazon GuardDuty | 從AWS telemetry偵測credential compromise、惡意活動與異常行為。 | Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。 | 需要managed threat detection與多帳號集中findings。 | 漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 | SOC需要跨帳號單一finding queue與compliance view。 | 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。 | 只有當題目條件明確改變時才可能合理。 | Log bucket policy允許source帳號刪除，或所有security admin都使用management account。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。」之間做選擇。
- 認得常考設定：multi-Region/organization trail、management/data events、S3/KMS、log validation、CloudWatch integration與Lake。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：application log與performance metric不是CloudTrail用途。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAP｜將安全證據置於 compromised account 之外

攻擊者取得 production account 的 administrator role 後刪除本地 CloudTrail bucket，SOC 因此失去調查證據。哪個多帳號設計最能限制相同事件？

A. 使用 organization trail；logs 仍寫回各 workload account 的 bucket 與 KMS key
B. 使用 organization trail 把 logs 送到獨立 Log Archive account，由 destination 控制 S3/KMS/retention；另以 Security Tooling account 執行 delegated operations
C. 將 organization trail 集中到 security account 的 CloudWatch Logs，log group 保留七年並訂閱中央 SIEM
D. 停用 member-account trails，由 organization trail 集中投遞；destination policy 以部署 pipeline 的成功狀態作驗收

**答案：B**

- **A：** Organization trail 可統一收集事件；destination bucket/KMS 仍由被入侵的 workload account 控制時，攻擊者仍可能破壞唯一證據。
- **B：** 符合本題。Evidence 的 owner 與受調查 account 分離，搭配 destination policies、retention 與 delegated security operations 才能存活於帳號 compromise。
- **C：** 中央 CloudWatch Logs 適合近即時查詢與 SIEM subscription；單靠 log group retention 沒有建立與 workload 管理權分離的長期 S3 evidence custody。
- **D：** 停用重複 member trails 可以節省成本，但必須先證明 organization trail、destination policy、KMS 與所有 Region delivery 已成立，否則會產生日誌空窗。

**事實查證：** [Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)、[Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)

### 練習題 2｜SAP｜organization trail event scope 與成本

公司要稽核所有 accounts/Regions 的 management events，並監控少數含敏感資料的 S3 buckets。安全主管提議對所有 buckets、所有 Lambda functions 開啟全部 data events，不做成本估算。較好的設定是什麼？

A. 建立 multi-Region organization trail，對每個 S3 object 啟用 data events 而不設 selector；CloudTrail usage report 分開計算 management/data event volume、selector 命中率與 ingestion cost，設定版本與生效時間一併寫入 change record
B. 只記錄 management events，將高風險 data events 交由應用 log 取代
C. 建立 multi-Region organization trail 記錄 management events，依 threat model 精選高價值 data events/Insights，估算 volume 並驗證中央 delivery
D. 在 organization trail 啟用全量 data events，保留 90 天高頻事件並按月調整 selectors

**答案：C**

- **A：** 全量 S3 object data events 能提供廣泛可見性，事件量與費用可能遠超 threat model 所需；少量敏感 bucket 應用 selectors 精準涵蓋。
- **B：** Application logs 可補充 business context，不能取代 CloudTrail 對 S3 object API caller、request 與 AWS authorization 的證據。
- **C：** 符合本題。Management coverage、data-event scope、cost 與 delivery validation 都應被明確設計。
- **D：** 全量開啟再用短 retention 控成本仍會產生高 ingestion/query 成本與大量低價值事件；應在啟用前依風險選 scope。

**事實查證：** [Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[CloudTrail Lake event data stores](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-event-data-store.html)

### 練習題 3｜SAP｜CloudTrail integrity 與 immutability（選兩項）

法務要求能發現 CloudTrail log files 是否被修改，並在七年內阻止刪除。哪兩個控制分別直接處理「可驗證完整性」與「retention 期間不可刪除」？（選兩項）

A. 啟用 CloudTrail log validation，logs 寫入 versioned S3 bucket，刪除權限由 MFA Delete 保護
B. 啟用 CloudTrail log file integrity validation，保存並驗證 digest chain
C. 在 archive bucket 使用適當 S3 Object Lock retention，並限制修改 retention 與 delete 的權限
D. 使用 S3 Object Lock Governance retention，保留具 bypass 權限的法遵角色；同時保存 CloudTrail digest files
E. 把既有 logs 搬入受鎖 bucket，再假設搬移前的檔案也取得可驗證來源

**答案：B、C**

- **A：** CloudTrail validation 可檢查 digest chain；S3 versioning 與 MFA Delete 不等同有明確 retention period 的 Object Lock，且自動化刪除路徑仍不同。
- **B：** 符合本題。Integrity validation 使用 digest files 協助偵測 delivered CloudTrail files 是否被修改、刪除或新增。
- **C：** 符合本題。Object Lock 的 retention mode 與 policy 可在指定期間阻止 object deletion/overwrite，需在上線前設計。
- **D：** Object Lock Compliance 可處理不可刪除性；若 digest validation 沒有在 trail delivery 時正確啟用並保管 digest，單純保存檔案不能證明來源完整性。
- **E：** 把舊 logs 搬進 locked bucket能保護搬入後的 object，無法追溯證明搬入前是否曾被修改或遺漏。

**事實查證：** [CloudTrail log file integrity validation](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html)、[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

### 練習題 4｜SAP｜CloudTrail Lake 與 S3 archive analytics

既有 CloudTrail Lake 客戶的 SOC 想用 SQL 查詢受管理的 event data store；另一個新 AWS 客戶要集中 CloudTrail、應用與網路 logs，並保留長期 S3 evidence。依 2026-10-01 的服務可用性，哪個判斷最合理？

A. 既有與新客戶都建立 CloudTrail Lake event data store，再把 application logs 直接寫入同一 store；Audit trail 另標示「CloudTrail Lake 與 S3 archive analytics」的設定版本、生效時間與 exception expiry
B. 新客戶將 organization trail 送到 CloudWatch Logs Insights，log group 設定七年 retention；Query audit 記錄 data owner、retention class、ingestion source、query bytes 與查詢者身分，具名 owner 與 approver 依固定 cadence 複核
C. 為新客戶把 CloudTrail Lake 列為標準查詢層，procurement checklist 依 2026 服務目錄核准；Release evidence 另關聯「CloudTrail Lake 與 S3 archive analytics」的 pilot wave、result 與 rollback timestamp
D. 既有客戶可依保留期限繼續使用 CloudTrail Lake；新客戶採 organization trails 將事件送至 S3，並用 Athena、CloudWatch 或資料湖工具查詢

**答案：D**

- **A：** CloudTrail Lake 對既有客戶可用，也能查詢 event data store；2026-05-31 後的新客戶不能把建立新 Lake store 當成可用方案。
- **B：** CloudWatch Logs Insights 適合互動查詢，長期 retention 仍不是題目要求的 S3 evidence archive，也沒有涵蓋應用與網路 logs 的統一 custody。
- **C：** Procurement 記錄不能改變服務可用性；新客戶無法以 Lake 作承諾中的查詢層，必須選 trails、S3 與現行 analytics path。
- **D：** 符合本題。CloudTrail Lake 自 2026-05-31 起不再接受新客戶。既有客戶仍可使用；新客戶應以 trails、S3 與相應查詢/分析服務建立可保管的 evidence path。

**事實查證：** [CloudTrail Lake availability change](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html)、[Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)

### 練習題 5｜SAP｜Config 與 CloudTrail 的證據差異

稽核員提出兩個問題：目前哪些 security groups 允許 0.0.0.0/0？昨天是誰修改其中一條 ingress rule？應分別使用什麼資料來源？

A. 用 AWS Config configuration/compliance data 回答資源狀態，用 CloudTrail 回答 API caller 與 change event；SIEM schema 保留 Config resource ID/version 與 CloudTrail eventName、principal、request parameters，設定版本與生效時間一併寫入 change record
B. 用 Config aggregator 回答目前狀態與歷史，API caller 只從 application access logs 推論
C. 用 CloudTrail 查 API caller 與變更事件，再以自訂 SQL 取代 Config 的 resource inventory
D. 將 Config snapshots 與 CloudTrail events 正規化成同一 SIEM event schema，以單一 query model 回答狀態與 caller

**答案：A**

- **A：** 符合本題。Config 聚焦 configuration state/history/compliance；CloudTrail 聚焦誰在何時呼叫哪個 AWS API。
- **B：** Config aggregator 能回答跨帳號資源狀態；application access logs 通常不含修改 security group 的 AWS API principal，caller evidence 應來自 CloudTrail。
- **C：** CloudTrail 可找修改 ingress 的 API event，卻不是完整 configuration inventory/compliance database；用事件自行重建目前狀態會增加漏事件與查詢複雜度。
- **D：** SIEM 可以彙總兩種來源；若正規化時把 configuration snapshot 與 API caller 都壓成同一 generic event，就會失去各自回答問題所需的語意。

**事實查證：** [AWS Config aggregators](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)、[Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)

### 練習題 6｜SAP｜GuardDuty delegated administrator 與 Region scope

公司只在 security account 的 us-east-1 啟用 GuardDuty，卻認為 organization 所有 accounts 與 Regions 已受到保護。後來 eu-west-1 的新帳號沒有 findings。應如何改善？

A. 只在 security account 的兩個主要 Regions 設 delegated admin，其他 enabled Regions 靠人工建立 detector
B. 在支援的 security account 設 delegated administrator，依 organization/Region 規劃 member auto-enable 與 protection plans，並建立 finding triage/response workflow
C. 各 member account 自行管理 GuardDuty，中央帳號只接收 EventBridge findings
D. 對 organization 啟用 GuardDuty auto-enable，所有 Regions 沿用 base detector 與各 protection plan 的 account defaults；GuardDuty inventory 逐 account/Region 列出 detector、member、protection-plan 與 finding-export 狀態，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** 只在兩個 Region 建 delegated administration 可保護固定部署範圍；新帳號或其他 enabled Region 的 detector/protection plan 仍可能缺席。
- **B：** 符合本題。Delegated administration、member enrollment、protection plan 與 Region rollout 都需要明確設定與 ownership。
- **C：** 各帳號自行管理 GuardDuty 可保留地方自治，會增加 Region enablement、protection plan 與 finding response 的不一致，中央只收 EventBridge 也不能補齊 detector。
- **D：** Organization auto-enable 能建立基礎 detector；若 protection plans 與 response ownership 仍沿用各帳號預設，新增 Region 或功能不一定得到相同 coverage。

**事實查證：** [Managing GuardDuty accounts](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_accounts.html)

### 練習題 7｜SAP｜Security Hub central configuration 與 finding workflow

Security Hub CSPM delegated administrator 顯示 92% security score。管理層因此主張不必再定義 finding owner、suppression 與 exception review。哪個回應最準確？

A. 使用 Security Hub CSPM central configuration 統一 controls，findings 依 account 分流到各 workload queue 與地方 SLA；Finding record 保存 product ARN、control ID、account owner、workflow status 與 suppression expiry，設定版本與生效時間一併寫入 change record
B. 保留來源服務與 findings，將例外預設改成 control disable 而不記錄風險接受期限
C. Central configuration 可統一 standards/controls 與 aggregation；要依 finding 風險定義 owner、automation、suppression、exception 與 local response context
D. 以 92% Security Hub CSPM security score 作季度門檻，低嚴重度 findings 依 workflow status 自動關閉；「Security Hub central configuration 與 finding workflow」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：C**

- **A：** Central configuration 可統一 standards 與 controls；finding ownership 完全由各帳號自行決定時，跨帳號相同風險可能沒有一致 SLA、escalation 或 aggregation workflow。
- **B：** 停用 control 可處理整體不適用的規則，卻把個別資源例外擴成更大範圍，且缺少有期限的 risk acceptance evidence。
- **C：** 符合本題。中央 policy 與地方處置責任需同時存在，並以可稽核流程管理例外。
- **D：** Security score 適合觀察 posture 趨勢，不代表低嚴重度 finding 可依分數自動結案；asset criticality、exploitability 與 local context 仍會改變優先序。

**事實查證：** [Security Hub central configuration](https://docs.aws.amazon.com/securityhub/latest/userguide/central-configuration-intro.html)、[Managing GuardDuty accounts](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_accounts.html)、[AWS Config aggregators](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)

### 練習題 8｜SAP｜可在帳號 compromise 時使用的 break-glass（選兩項）

Incident responders 必須在 workload account 被完全接管時仍能讀取中央 logs、隔離 resources 並保留證據。哪兩項設計最能支援此需求？（選兩項）

A. 在獨立 security/identity boundary 建立受嚴格監控的 incident roles 與批准流程，預先授權必要的跨帳號 evidence access
B. 在 security account 建 emergency role；批准、MFA 與 secrets 仍依賴同一企業 IdP
C. 為 SOC 建立長期跨帳號 admin sessions，以減少事件期間的 role-assumption 步驟
D. 以 tabletop 驗證 break-glass 流程，實際 cross-account data access 則沿用現有 bucket、KMS 與 SCP policy simulation
E. 定期演練 IAM、SCP、KMS key policy 與 log-bucket policy，確認 emergency session 真的能讀取和執行預定操作

**答案：A、E**

- **A：** 符合本題。Emergency path 應盡量依賴外部 identity/control boundary，並只預授權必要 actions。
- **B：** Emergency role 位於 security account 是良好起點；批准、MFA 與 secrets 仍依賴同一企業 IdP 時，IdP compromise/outage 會同時封鎖應急路徑。
- **C：** 長期跨帳號 admin session 可減少 assume-role 步驟，卻擴大 credential exposure 與難以即時撤銷的權限；break-glass 應短時、具名且按需取得。
- **D：** Tabletop 能檢查人員與流程，不能證明 SCP、KMS key policy、bucket policy 和 role trust 的有效交集；這些隱性 Deny 需實際演練。
- **E：** 符合本題。只有透過演練才能發現 cross-account trust、KMS 與 bucket policy 在事故時形成的隱性 deny。

**事實查證：** [Cross-account access with roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)、[Break-glass access in the AWS Security Reference Architecture](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/break-glass-access.html)

### 練習題 9｜SAP｜診斷中央 evidence 缺口

新加入 organization 的帳號在中央 CloudTrail bucket、Config aggregator 與 GuardDuty console 都看不到資料。下列哪個調查順序最合理？

A. 從中央 S3 destination policy 開始，將 CloudTrail、Config 與 GuardDuty 都視為相同的跨帳號 delivery path 逐層檢查
B. 重建 Config aggregator，並用其 account/Region registration 作為 CloudTrail 與 GuardDuty enrollment 的共同基準
C. 立即重新 enroll member account；保存 delivery errors 與原始設定供 root-cause analysis
D. 檢查帳號 enrollment 時間、Region/service enablement、organization/delegated-admin 關係、trail/recorder/detector 狀態、S3/KMS policies 與 delivery errors

**答案：D**

- **A：** S3 destination policy 是 CloudTrail 的重要檢查點，Config aggregator 與 GuardDuty 不共享同一 delivery contract；把三者都當成 S3 問題會漏掉 recorder、detector 與 delegated-admin 狀態。
- **B：** Config aggregator 只聚合 Config data，不控制 CloudTrail trail 或 GuardDuty detector；重建它不能同時恢復三種 evidence。
- **C：** Re-enroll 可能重建部分組織關係，但會改變現場狀態並掩蓋真正的 Region、policy 或 delivery error；先保存 evidence 才能避免反覆發生。
- **D：** 符合本題。三個服務有不同 enrollment、Region 與 delivery dependencies，應逐層驗證 control plane 與 destination access。

**事實查證：** [Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[AWS Config aggregators](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)、[Managing GuardDuty accounts](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_accounts.html)

### 練習題 10｜SAP｜安全偵測與 retention policy 的漸進 rollout

公司準備開啟新的 Security Hub CSPM controls、CloudTrail data events 與更長 retention。若一次套用全部帳號，預估費用與 false positives 未知。最佳 rollout 是什麼？

A. 估 event volume 與 cost，在代表帳號以 observation/audit 模式或小範圍 pilot 驗證，調整 false positives 與 exceptions，再分 waves 擴大並保留 immutable raw evidence
B. 在代表帳號試行 Security Hub CSPM controls；CloudTrail data-event volume 直接全組織開啟
C. 以 suppression rules 降低 finding noise，raw evidence 保留 30 天，彙總 findings 保留一年；Pilot report 追蹤 event volume、finding precision、retention cost、query latency 與 exception owner，相關 alarms 與 rollback timestamp 納入 release evidence
D. 一次推出 controls、data events 與 retention，再依月底成本和 false positives 回退

**答案：A**

- **A：** 符合本題。Volume、precision、ownership 與 evidence preservation 應在 pilot 中量測，再逐步擴大。
- **B：** 在代表帳號試行 CSPM controls 可量測 finding noise；CloudTrail data events 直接全組織開啟仍保留最大、最昂貴且尚未量化的變更面。
- **C：** Suppression rules 可降低處理噪音，30 天 raw evidence 與一年 summary 是另一種 retention contract；題目要評估更長 retention 與 immutable evidence，不能用彙總 findings 取代。
- **D：** 全量 rollout 適合已知 volume、owner 與 rollback 的成熟設定；此題的費用和 false positives 都未知，月底才看到結果時 blast radius 已覆蓋所有帳號。

**事實查證：** [Security Hub central configuration](https://docs.aws.amazon.com/securityhub/latest/userguide/central-configuration-intro.html)、[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)、[CloudTrail data events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「建立log archive與security tooling帳號，Organizations整合Cloud…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「攻擊者取得workload帳號後不應能刪除稽核證據或停用偵測。」，所以「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」能直接滿足它；若constraint改成「各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」。替代方案「各帳號保留操作view可加速回應，但authoritative copies應跨帳號不可變保存。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Log bucket policy允許source帳號刪除，或所有security admin都使用management account。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「攻擊者取得workload帳號後不應能刪除稽核證據或停用偵測。」，排除會導致「Log bucket policy允許source帳號刪除，或所有security admin都使用management account。」的選項，再選「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」。本章對應的代表task包括：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「建立log archive與security tooling帳號，Organizations整合CloudTrail、Config、GuardDuty與Security Hub。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「security evidence must outlive the compromised account」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 82 章　Enterprise Identity 與 Cross-account Authorization

數千員工、automation與第三方需要不同身份生命週期與權限委派。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：公司目錄有部門與職級屬性，需動態授予數百帳號不同權限。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：數千員工、automation與第三方需要不同身份生命週期與權限委派。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS IAM Identity Center如何接手工作，再看AWS STS何時更合適，最後用設定與考題驗證「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：公司目錄有部門與職級屬性，需動態授予數百帳號不同權限。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS IAM Identity Center]
          │ 集中管理workforce登入多個AWS accounts與business applications。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS STS：簽發有限時效的temporary AWS credentials。
  · IAM ABAC：用JSON描述Effect、Action、Resource與Condition，控制principal可做…

失敗時先找：每帳號local user、shared automation key與永久Administrator role。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS IAM Identity Center有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS IAM Identity Center和AWS STS並不是兩個任意的產品名稱。前者適合本章，是因為「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」直接回應了眼前的問題；後者描述的「ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每帳號local user、shared automation key與永久Administrator role。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「identity lifecycle should be centralized; authorization stays contextual」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 |
| IAM ABAC | 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。 | Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。 |

## 把全圖套進一個具體案例

**場景：** 公司目錄有部門與職級屬性，需動態授予數百帳號不同權限。

1. 故事的起點：公司目錄有部門與職級屬性，需動態授予數百帳號不同權限。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS IAM Identity Center負責「集中管理workforce登入多個AWS accounts與business applications。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS STS、IAM ABAC各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每帳號local user、shared automation key與永久Administrator role。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS IAM Identity Center

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：數千員工、automation與第三方需要不同身份生命週期與權限委派。
- **具體例子／邊界：** 在「公司目錄有部門與職級屬性，需動態授予數百帳號不同權限。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS STS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每帳號local user、shared automation key與永久Administrator role。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：identity lifecycle should be centralized; authorization stays contextual。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### least privilege

只授予完成目前工作需要的actions、resources、conditions與時間，而非先給admin再期待人工回收。

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### AWS account

AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

## 回到 AWS：Components、功用與責任邊界

### AWS IAM Identity Center

- **功用：** 集中管理workforce登入多個AWS accounts與business applications。
- **底層機制：** 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
- **關鍵設定：** identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- **選擇時機：** 企業員工、群組生命週期與多帳號SSO。
- **替換時機：** consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。

### AWS STS

- **功用：** 簽發有限時效的temporary AWS credentials。
- **底層機制：** AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。
- **關鍵設定：** role ARN、session name、duration、external ID、source identity、session tags與session policy。
- **選擇時機：** cross-account、federation、workload identity與避免長期access keys。
- **替換時機：** 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。

### IAM ABAC

- **功用：** 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。
- **底層機制：** Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。
- **關鍵設定：** Version、Statement、Sid、Effect、Action/NotAction、Resource/NotResource、Principal與Condition。
- **選擇時機：** 可用明確ARN與conditions表達least privilege時。
- **替換時機：** 需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。

## 考前與實作時再查：設定操作手冊

### AWS IAM Identity Center：逐項設定說明

#### `identity source`

- **控制什麼：** `identity source`指定AWS IAM Identity Center讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `permission sets`

- **控制什麼：** `permission sets`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `assignments`

- **控制什麼：** `assignments`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session duration`

- **控制什麼：** `session duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS IAM Identity Center的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `SCIM`

- **控制什麼：** `SCIM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `delegated administration`

- **控制什麼：** `delegated administration`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

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

### IAM ABAC：逐項設定說明

#### `Version`

- **控制什麼：** `Version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM ABAC鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `Statement`

- **控制什麼：** `Statement`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Sid`

- **控制什麼：** `Sid`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

#### `Effect`

- **控制什麼：** `Effect`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Action/NotAction`

- **控制什麼：** `Action/NotAction`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Resource/NotResource`

- **控制什麼：** `Resource/NotResource`指定IAM ABAC讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Principal`

- **控制什麼：** `Principal`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM ABAC明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `Condition`

- **控制什麼：** `Condition`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM ABAC以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

## 讀到這裡，請用自己的話說一次

1. AWS IAM Identity Center的責任：集中管理workforce登入多個AWS accounts與business applications。
2. 底層機制：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
3. 第一個要看的設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
4. 選擇邏輯：Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。
5. 不要混淆：AWS STS的責任是「簽發有限時效的temporary AWS credentials。」；它不會自動取代AWS IAM Identity Center。
6. 替換訊號：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
7. 最常見錯法：每帳號local user、shared automation key與永久Administrator role。
8. 可移植原則：identity lifecycle should be centralized; authorization stays contextual。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 | 企業員工、群組生命週期與多帳號SSO。 | consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 | cross-account、federation、workload identity與避免長期access keys。 | 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。 |
| IAM ABAC | 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。 | Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。 | 可用明確ARN與conditions表達least privilege時。 | 需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。 | 只有當題目條件明確改變時才可能合理。 | 每帳號local user、shared automation key與永久Administrator role。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。」之間做選擇。
- 認得常考設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAP｜區分 workforce、workload 與 customer identity

企業要同時支援：員工以公司 IdP 登入 200 個 AWS accounts、CI jobs 取得 AWS API 權限，以及消費者登入 SaaS 應用。哪個 identity 分工最合理？

A. 員工用 Identity Center、CI 用 IAM roles；「區分 workforce、workload 與 customer identity」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 員工與消費者分別用 federation/Cognito，CI jobs 則共用一組輪替的 access key；「區分 workforce、workload 與 customer identity」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 員工使用 IAM Identity Center/federation，CI 使用 workload roles 或 federation，消費者使用 application identity service；日常不依賴長期 IAM users
D. 每個 account 建立 local IAM users，憑證由中央 secrets vault 輪替，CI 與 workforce 使用不同 users；Identity inventory 將 workforce、workload 與 customer principals 分開記錄 owner、issuer 與 credential type，exception expiry 與最後一次驗收時間也被保留

**答案：C**

- **A：** Identity Center 與 IAM roles 分別適合 workforce 和 CI；把 SaaS customers 放入企業 workforce directory 會混合 tenant lifecycle、self-service sign-up 與員工治理。
- **B：** Federation/Cognito 的人員分工合理，共用輪替 access key 仍是長期 workload credential，無法提供每個 CI job 的短期 session 與 attribution。
- **C：** 符合本題。三類 principal 的 lifecycle、authentication 與授權情境不同，應使用 temporary credentials 與對應服務。
- **D：** Local IAM users 可支援少量 legacy principals，200 個 accounts 的 workforce/CI 會產生 credential sprawl；集中輪替仍沒有消除長期金鑰。

**事實查證：** [IAM Identity Center permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)、[Identity providers and federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers.html)、[Amazon Cognito application authentication](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html)

### 練習題 2｜SAP｜Identity Center group、permission set、account assignment

公司希望 Finance-ReadOnly 群組可讀 12 個 production accounts，Platform-Admin 群組可管理 6 個 infrastructure accounts；人員異動由 corporate directory 控制。最可維護的做法是什麼？

A. 使用 groups 與 permission sets；將同一 admin permission set 指派到所有 production accounts
B. 依 account 建 permission sets 並直接指派個人，企業目錄只負責 authentication
C. 刪除 local IAM users，為每個 account 複製一組 Finance 與 Platform permission sets，再建立 group assignments
D. 建立 job-function permission sets，把 IdP groups assignment 到指定 accounts，使用者登入後取得 temporary role sessions

**答案：D**

- **A：** Groups 與 permission sets 是正確元件；把同一 admin set 套到所有 production accounts 無法表達 Finance read-only 與 Platform admin 的不同職能和 account scope。
- **B：** 逐帳號 permission set 加個人 assignment 可以精細授權，卻複製政策並繞過 corporate group lifecycle，人員異動需要多處同步。
- **C：** 移除 IAM users 與測試 assignments 都有價值；若仍為每個帳號複製獨立 permission set，職能政策會漂移，不能形成可維護的 job-function model。
- **D：** 符合本題。Permission set 描述職能權限，group-to-account assignment 描述在哪些帳號可用，適合中央身份生命週期。

**事實查證：** [IAM Identity Center permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)

### 練習題 3｜SAP｜跨帳號 AssumeRole 的必要授權（選兩項）

Account A 的 deployment role 要 assume Account B 的 `ReleaseRole`。B 的 trust policy 已信任 A 的 role，但呼叫仍被拒絕。若沒有其他 explicit Deny，成功 AssumeRole 還需要哪兩個條件？（選兩項）

A. Caller identity policy 允許 sts:AssumeRole；target trust policy 只信任另一個 deployment role
B. Target trust policy 信任 caller；caller 透過 target-account resource policies 取得 S3 管理權限，STS authorization 交由 trust policy 處理
C. Account A 的 caller identity policy 允許對目標 role 執行 `sts:AssumeRole`
D. 兩側授權都正確；OU SCP 對 sts:AssumeRole 有 explicit Deny
E. 目標 role trust policy 的 principal 與 conditions 必須符合實際 caller/request context

**答案：C、E**

- **A：** Caller 具備 sts:AssumeRole Allow 仍不足，target trust policy 信任的是另一個 principal，request 不符合 resource-based trust。
- **B：** Target account 的 S3 resource policy 可授權資料操作，不會替 caller 取得 sts:AssumeRole；STS 呼叫仍需 caller identity permission 與 role trust 同時成立。
- **C：** 符合本題。Caller 必須有呼叫 AssumeRole 的權限；同時不能被 SCP、boundary 或其他 policy 阻擋。
- **D：** Identity policy 與 trust policy 都正確時，Organizations SCP 的 explicit Deny 仍會限制有效權限；題幹已排除其他 Deny，這不是可成功的條件。
- **E：** 符合本題。Trust policy 定義誰能成為該 role session，以及 external ID、MFA、tags 等 request conditions。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[Cross-account access with roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 4｜SAP｜第三方 SaaS external ID 與 confused deputy

監控 SaaS 供應商要求每位客戶建立一個 cross-account role。供應商自己的 AWS account 會代表許多客戶 assume roles。哪個 trust 設計最能降低 confused-deputy 風險？

A. 信任供應商指定的 principal，要求供應商為本客戶提供且在 AssumeRole 時傳入的 customer-specific external ID，並限制 role permissions
B. 信任 vendor account root 並要求共用 external ID，再由 vendor 內部限制實際 principal；Vendor-access log 保存 role ARN、vendor principal、external-ID tenant、session name 與 requested actions，具名 owner 與 approver 依固定 cadence 複核
C. 信任 vendor 指定 role；由每位客戶自行選可重複的 external ID
D. 供應商使用客戶簽發的 IAM access key，存放在 vendor secrets manager 並定期輪替；「第三方 SaaS external ID 與 confused deputy」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：A**

- **A：** 符合本題。Specific principal、customer-specific external ID 與 least privilege 共同綁定供應商代表哪個客戶發起請求。
- **B：** 信任 vendor account root 可讓其帳號內多個 principals 取得路徑，共用 external ID 又不能區分客戶；適合單一專屬 vendor account，不適合 multi-tenant SaaS。
- **C：** 信任指定 vendor role 是合理的；external ID 應由供應商為客戶產生並在代客呼叫時綁定，讓客戶自行選可重複值會削弱 confused-deputy 防護。
- **D：** 長期 access key 可讓供應商呼叫 API，但客戶需承擔金鑰分發、輪替與洩漏風險，也失去 AssumeRole 的 tenant-specific trust conditions。

**事實查證：** [Cross-service and cross-account confused deputy prevention](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)、[AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)

### 練習題 5｜SAP｜ABAC 的可信 attribute 來源

公司用 `department` session tag 控制工程師只能修改同 department 的 resources。現在使用者可自行在 IdP profile 把 department 改成 `security`。應如何修正？

A. 由 IdP 映射 department；Audit trail 另標示「ABAC 的可信 attribute 來源」的設定版本、生效時間與 exception expiry；「ABAC 的可信 attribute 來源」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 由可信 identity source 映射 attributes，限制誰能修改授權 tags 與 `sts:TagSession`，在 policies 限定允許的 tag keys/values，敏感 actions 另保留顯式 guardrails
C. 鎖定 principal tags，resource owners 卻可把敏感資源改標為自己的 department；Attribute audit 追蹤 IdP claim、principal tag、resource tag、mutation actor 與 policy decision，相關 alarms 與 rollback timestamp 納入 release evidence
D. 啟用 ABAC 到 production；「ABAC 的可信 attribute 來源」的 change record 另保存 scope、owner、approver 與 rollback trigger；Audit trail 另標示「ABAC 的可信 attribute 來源」的設定版本、生效時間與 exception expiry

**答案：B**

- **A：** 由 IdP 映射 attribute 是 ABAC 常見做法；使用者可自行修改 department 時，授權輸入不可信，等同允許自我升權。
- **B：** 符合本題。ABAC 的安全性取決於 attribute provenance、tag mutation permission 與 policy conditions。
- **C：** 鎖定 principal tag 只保護一側；resource owner 可重標敏感資源時，policy 的 department equality 仍能被操縱。
- **D：** CloudTrail 能找出 tag mutation 行為，不能阻止第一個惡意或錯誤 session tag 在 production 取得權限；attribute governance 必須先建立。

**事實查證：** [Attribute-based access control in IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)、[Passing session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 6｜SAP｜role chaining 的 requester attribution

員工從 Identity Center session assume PlatformRole，再由 PlatformRole assume ProductionRole。CloudTrail 最後只容易看到中介 role session，SOC 希望保留原始 requester identity 與必要 department attribute。哪個設計較合適？

A. 使用一致 RoleSessionName 保留人員識別；不設定 SourceIdentity 或 transitive tags
B. 傳遞 department session tag，卻允許中介 role 以新值覆寫該 attribute
C. 使用受控的 source identity 與必要 session tags，只有需要跨 role chain 的 attributes 設為 transitive，並驗證 CloudTrail attribution
D. 把大量身份屬性設為 transitive；logs 出現敏感資料後縮小傳遞範圍

**答案：C**

- **A：** RoleSessionName 可出現在 logs，但由 caller 提供且不會像 SourceIdentity 一樣受控地跨 role chain 保留，不能單獨作可信 requester identity。
- **B：** Transitive tag 可以跨鏈傳遞；允許中介 role 改寫 department 會破壞 attribute provenance，SOC 看到的是可被重寫的授權資料。
- **C：** 符合本題。Source identity 與 controlled transitive session tags 可在 temporary sessions 間保留可追溯 context。
- **D：** Transitive tags 適合少量必要 attributes；大量傳遞會擴大敏感資料曝光與 policy surface，且沒有改善原始 requester 的可信識別。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[Passing session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)、[Monitor and control actions taken with assumed roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_monitor.html)、[CloudTrail userIdentity element](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-user-identity.html)

### 練習題 7｜SAP｜session policy 與 role policy 的交集

一個 role 允許讀寫整個 project bucket。自動化在 AssumeRole 時傳入 session policy，只允許讀取 `reports/` prefix。該 session 的有效權限如何決定？

A. Session policy 只允許 reports read
B. 縮短 session duration，保留 role 對整個 project bucket 的原始 read/write 權限；Authorization test matrix 比較 role policy、session policy、resource policy、SCP 與 boundary 的結果，具名 owner 與 approver 依固定 cadence 複核
C. 發出較寬 session，再在工作完成後更新 role policy，希望既有 credentials 同步縮權
D. Session policy 與 role permissions 取交集，因此 session 可縮小到 reports read；不能增加 role 原本採用既有的 action

**答案：D**

- **A：** Session policy 通常限制 role session；若 bucket policy 直接授權特定 role-session principal，resource-based grant 的評估方式可能不受同樣的 implicit deny 限制，因此不能只看 session policy 宣告。
- **B：** 縮短 duration 會減少 credential lifetime，不會把原本的 bucket read/write actions 收斂成 reports read。
- **C：** 先發出較寬 session 會在 credential 到期前保留既有權限；後改 role policy 也不是本次 AssumeRole 所需的即時 session restriction。
- **D：** 符合本題。Session policy 是額外的 permissions boundary，能縮小 session，不能擴張 role permissions。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 8｜SAP｜Identity Center delegated administration（選兩項）

公司要讓 identity operations team 管理日常 Identity Center assignments，但不希望該團隊成為 Organizations management account administrators。哪兩個原則正確？（選兩項）

A. 在 AWS 支援的條件下使用 delegated administration，把日常 Identity Center 管理移到指定 member account
B. 把日常 assignments 委派到 member account；permission-set design 與 privileged review 仍由同一 operator 完成
C. 指定 Identity Center delegated administrator，同時保留 management account role 執行日常 assignment 與 emergency changes
D. 依職責分離 assignment、permission-set design 與 privileged change review，並集中稽核管理事件
E. Identity Center delegated administrator 成為唯一 identity-operations path，management-account operators 停用日常與 emergency assignments

**答案：A、D**

- **A：** 符合本題。Delegated administration 可降低日常操作對 management account 的依賴，但須遵守服務支援與限制。
- **B：** 把 assignment、permission-set design 與 privileged review 都交給同一 operator 可提升速度，卻沒有題目要求的職責分離。
- **C：** 保留 management-account emergency path 是合理的；若同一角色仍用於日常直接修改 assignments，delegation 就沒有縮小最高權限帳號的常態暴露。
- **D：** 符合本題。Delegation 解決帳號位置，仍需要 duties、least privilege、review 與 audit evidence。
- **E：** Delegated administrator 可承接多數日常操作，但部分保留責任與 break-glass 仍在 management account；完全停用該路徑可能使服務限制或 delegated account 故障時無法復原。

**事實查證：** [Delegated administration for IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/delegated-admin.html)、[Management account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html)

### 練習題 9｜SAP｜IdP outage 的 emergency access

企業 IdP 發生全面 outage，IAM Identity Center 使用者都無法登入。Production 仍需緊急修復，但現有 break-glass approval 也依賴同一 IdP。應如何重新設計？

A. 建立依賴獨立 identity/approval path 的少量 emergency roles 或 credentials，嚴格保管、短時使用、完整記錄、定期演練並在事件後 rotate/review
B. 建立 emergency IAM user；Release evidence 另關聯「IdP outage 的 emergency access」的 pilot wave、result 與 rollback timestamp
C. 建立獨立 emergency role，平時讓 production engineers 用它處理一般維運；Release evidence 另關聯「IdP outage 的 emergency access」的 pilot wave、result 與 rollback timestamp
D. 保留一份由 Organizations management account 在事故時建立 emergency credentials 與 trust 的 bootstrap runbook；Emergency-access register 記錄 credential custodian、MFA device、approval path、test date 與 rotation status，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。Emergency path 必須與主要 IdP 故障域解耦，並以監控、演練和事後處理限制風險。
- **B：** Emergency IAM user 本身可繞過 Identity Center；MFA、secret custody 與 approval 仍依賴故障中的 IdP，整條操作鏈沒有獨立。
- **C：** 獨立 emergency role 適合事件使用，拿來處理一般維運會失去低頻、強監控與事後 rotate 的風險邊界。
- **D：** 事件時依 runbook 建立 credentials/trust 可減少平時持有權限，但 IdP 全面 outage 時建立者也可能無法登入；bootstrap path 必須預先存在並演練。

**事實查證：** [Cross-account access with roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)、[Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[Management account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html)

### 練習題 10｜SAP｜least-privilege permission-set rollout

平台要把現有 Administrator permission set 縮小為 job-specific 權限。直接原地修改可能阻擋 production deployments。最佳 rollout 是什麼？

A. 直接原地縮小 production permission set，保留獨立 emergency-admin role 作為營運復原路徑
B. 依實際 access data 建立新版 permission set，在代表 accounts/groups pilot，監控 denied 與 privileged calls，保留舊版 rollback，驗證後再移除舊 assignments
C. 保留 Administrator permission set，僅用定期 access review 鼓勵使用者少用高權限
D. 以 federated login、List APIs 與 policy simulator 驗收新版 permission set，通過後一次替換 production assignments

**答案：B**

- **A：** 原地修改配合 emergency-admin 可快速回復，所有 production users 仍同時承受 policy 缺項；代表 accounts/groups pilot 才能限制 denied-call blast radius。
- **B：** 符合本題。Version、pilot、evidence 與 rollback 能在收斂權限時控制營運風險。
- **C：** Access review 可發現不必要權限，Administrator policy 仍技術上允許所有 actions，不能把鼓勵少用視為 least privilege。
- **D：** Login 與基本 List API smoke test 只能證明 federation/session 建立；deployment 所需 KMS、PassRole、service actions 與 resource conditions 仍可能被新版阻擋。

**事實查證：** [IAM Identity Center permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)、[Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Workforce federation經Identity Center；workload使用roles；…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「數千員工、automation與第三方需要不同身份生命週期與權限委派。」，所以「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」能直接滿足它；若constraint改成「ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」。替代方案「ABAC可依tag擴展授權，但需防止使用者自行修改高信任attribute。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每帳號local user、shared automation key與永久Administrator role。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「數千員工、automation與第三方需要不同身份生命週期與權限委派。」，排除會導致「每帳號local user、shared automation key與永久Administrator role。」的選項，再選「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」。本章對應的代表task包括：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Workforce federation經Identity Center；workload使用roles；第三方使用external ID與最小trust。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「identity lifecycle should be centralized; authorization stays contextual」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 83 章　Global Application 與 Multi-Region Data

全球架構要同時處理route、compute、data consistency、write ownership與failover。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

把鏡頭拉到一個真實的production現場：SaaS需全球低延遲讀取，但帳務寫入不可衝突且Region故障可接管。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：全球架構要同時處理route、compute、data consistency、write ownership與failover。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon Route 53是這一章的入口，AWS Global Accelerator用來畫出邊界；主要方向「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：SaaS需全球低延遲讀取，但帳務寫入不可衝突且Region故障可接管。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[Amazon Route 53]
          │ 提供authoritative DNS、health check與多種流量政策。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Global Accelerator：以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。
  · Aurora Global Database：將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
  · DynamoDB Global Tables：把DynamoDB table複寫成multi-Region active-active。

失敗時先找：DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問Amazon Route 53有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Route 53和AWS Global Accelerator並不是兩個任意的產品名稱。前者適合本章，是因為「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」直接回應了眼前的問題；後者描述的「只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「global compute is easier than global mutable state」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 |
| DynamoDB Global Tables | 把DynamoDB table複寫成multi-Region active-active。 | MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。 |

## 把全圖套進一個具體案例

**場景：** SaaS需全球低延遲讀取，但帳務寫入不可衝突且Region故障可接管。

1. 故事的起點：SaaS需全球低延遲讀取，但帳務寫入不可衝突且Region故障可接管。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Route 53負責「提供authoritative DNS、health check與多種流量政策。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Global Accelerator、Aurora Global Database、DynamoDB Global Tables各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Route 53

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：全球架構要同時處理route、compute、data consistency、write ownership與failover。
- **具體例子／邊界：** 在「SaaS需全球低延遲讀取，但帳務寫入不可衝突且Region故障可接管。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Global Accelerator

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：global compute is easier than global mutable state。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### listener

在load balancer指定protocol/port等待client connection的入口。

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

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

## 回到 AWS：Components、功用與責任邊界

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

### AWS Global Accelerator

- **功用：** 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。
- **底層機制：** Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。
- **關鍵設定：** listeners、endpoint groups、traffic dial、endpoint weight、health checks與client affinity。
- **選擇時機：** 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。
- **替換時機：** HTTP內容需要cache、header/path routing或edge function時選CloudFront。

### Aurora Global Database

- **功用：** 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。
- **底層機制：** Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。
- **關鍵設定：** primary/secondary Regions、write forwarding、global write、switchover/failover、RPO monitoring與headless secondary。
- **選擇時機：** 全球relational reads與分鐘級Region recovery。
- **替換時機：** 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。

### DynamoDB Global Tables

- **功用：** 把DynamoDB table複寫成multi-Region active-active。
- **底層機制：** MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。
- **關鍵設定：** consistency mode（MREC/MRSC）、replica Regions、capacity、PITR、KMS、Streams、MRSC Region-set availability與application conflict assumptions。
- **選擇時機：** 需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。
- **替換時機：** 跨item／跨Region複雜transaction、需要完整關聯SQL，或MRSC限制不合時，改用單writer、Aurora/DSQL或重新設計business invariant。

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

### AWS Global Accelerator：逐項設定說明

#### `listeners`

- **控制什麼：** Listener定義Global Accelerator接受的TCP或UDP port ranges；client連到兩個static anycast IP後，流量才依此入口進入accelerator。
- **何時需要：** 需要固定全球IP、非HTTP protocol，或不可快取的TCP/UDP application經AWS全球骨幹加速時。
- **怎麼設定／驗證：** 建立TCP/UDP listener與最小port ranges，設定client affinity需求；確認regional endpoints及security rules接受相同目的ports。
- **常見錯法：** Listener不是TLS certificate終止點；若後端要TLS，通常仍由NLB/ALB/application處理。Port設太寬也會擴大暴露面。

#### `endpoint groups`

- **控制什麼：** 每個endpoint group對應一個AWS Region，保存該Region的endpoints、health port/protocol與整體traffic dial。
- **何時需要：** 同一accelerator要在多Region間依健康與比例分配流量，或執行regional evacuation時。
- **怎麼設定／驗證：** 為每個Region建立group，加入ALB、NLB、EC2或EIP endpoints，設定health check與traffic dial；從多地client驗證實際Region。
- **常見錯法：** 建立第二group不等於application已多Region就緒；資料、identity、quota與failover dependencies仍要同步設計。

#### `traffic dial`

- **控制什麼：** 以0–100百分比調整某個endpoint group可接收的整體流量比例，常用於Region排空、canary或逐步恢復。
- **何時需要：** 跨Regionmigration、事件期間降低特定Region流量，或先用少量production traffic驗證新Region時。
- **怎麼設定／驗證：** 先確認另一Region有足夠capacity與資料，再逐步調整dial並監控business SLO；預先定義回調與rollback門檻。
- **常見錯法：** Traffic dial不是精準逐request比例，也不修正stateful session與資料一致性；瞬間設為0仍需考慮既有connections。

#### `endpoint weight`

- **控制什麼：** 在同一regional endpoint group內設定各endpoint的相對權重，控制新flows如何分配到多個ALB、NLB、EC2或EIP。
- **何時需要：** 同Region內做blue/green、capacity比例分配，或逐步引入新endpoint時。
- **怎麼設定／驗證：** 為healthy endpoints設定0–255相對weight，以小比例開始並觀察error、latency與capacity；確認health check能正確摘除故障端點。
- **常見錯法：** Weight不是保證百分比，少量flows會有偏差；把不健康endpoint權重設高也不會讓它恢復。

#### `health checks`

- **控制什麼：** Global Accelerator檢查regional endpoints能否服務，並把新flows導向健康端點；對ALB/NLB可沿用其健康狀態。
- **何時需要：** 要求endpoint或整個Region故障時自動停止接收新連線時。
- **怎麼設定／驗證：** 設定代表真實服務的protocol、port、path、interval與threshold，並以故障注入量測偵測及重新導流時間。
- **常見錯法：** 只檢查TCP port可能產生假健康；切走新flows也不會自動終止或遷移已建立的長連線。

#### `client affinity`

- **控制什麼：** 選擇NONE或SOURCE_IP，決定同一來源IP建立的新connections是否傾向被導到同一endpoint。
- **何時需要：** Application仍依賴endpoint-local session，且來源IP能合理代表client時，才作為相容性措施。
- **怎麼設定／驗證：** 在listener設定ClientAffinity；用多client/NAT情境驗證分布，並讓session逐步外部化到shared store。
- **常見錯法：** 大量使用者經同一NAT會被誤認為單一client並造成熱點；affinity也不能在endpoint故障時保存local session。

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

## 讀到這裡，請用自己的話說一次

1. Amazon Route 53的責任：提供authoritative DNS、health check與多種流量政策。
2. 底層機制：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
3. 第一個要看的設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
4. 選擇邏輯：依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。
5. 不要混淆：AWS Global Accelerator的責任是「以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。」；它不會自動取代Amazon Route 53。
6. 替換訊號：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
7. 最常見錯法：DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。
8. 可移植原則：global compute is easier than global mutable state。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 | 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。 | HTTP內容需要cache、header/path routing或edge function時選CloudFront。 |
| Aurora Global Database | 將Aurora cluster非同步複寫到其他Regions，提供低延遲全球讀與regional DR。 | Primary storage changes透過dedicated replication傳到secondary clusters；planned switchover可維持較安全切換。 | 全球relational reads與分鐘級Region recovery。 | 需要真正multi-active writes時需重新設計conflict semantics，或考慮DynamoDB Global Tables。 |
| DynamoDB Global Tables | 把DynamoDB table複寫成multi-Region active-active。 | MREC模式讓每個replica local read/write並非同步複寫，以last-writer-wins收斂；MRSC模式在支援的固定三Region sets中提供multi-Region strongly consistent reads，且仍需遵守其transaction、TTL與Region限制。 | 需要全球低延遲key-value access與regional resilience；若不能接受conflict，先確認workload與Region是否符合MRSC限制。 | 跨item／跨Region複雜transaction、需要完整關聯SQL，或MRSC限制不合時，改用單writer、Aurora/DSQL或重新設計business invariant。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。 | 只有當題目條件明確改變時才可能合理。 | DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。」之間做選擇。
- 認得常考設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAP｜分開設計全球入口與 mutable state

一家 SaaS 已在兩個 Regions 建立 ALB 與 Auto Scaling，架構師因此宣稱系統已是 active-active。實際上第二個 Region 沒有 database write ownership、secrets 與 event-consumer checkpoints。哪個修正觀念最重要？

A. 用 Global Accelerator 建全球入口；secondary Region 的 database、keys 與 quotas 維持 warm-standby 最低配置；Regional readiness matrix 分別列出 ingress、compute、writer、secret、checkpoint、quota 與 third-party dependency，設定版本與生效時間一併寫入 change record
B. 將資料非同步複寫到第二 Region，全球入口固定指向 primary；把 replica healthy 視為 secondary 可接手的 readiness signal；「分開設計全球入口與 mutable state」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 切全球流量到 secondary，再執行 writer promotion 與 dependency validation
D. 入口 routing 與 data architecture 必須分開設計：另外定義 compute readiness、state replication、consistency、write ownership、failover 與 failback

**答案：D**

- **A：** Global Accelerator 能改善全球入口；secondary 只維持最低 capacity 且沒有明確 writer、keys、quota 與 consumer state 時，這是 pilot-light/standby，不是 active-active。
- **B：** 資料複寫加 primary-only ingress 可形成 active-passive DR；它仍沒有定義 secondary 接管寫入、event checkpoints 與依賴的條件，不能因有 replica 就宣稱雙區皆可服務。
- **C：** 先送全球流量再 promotion 會讓 requests 抵達 read-only 或 readiness 尚未達標的 dependency path。Planned transition 應先建立 state authority/readiness，再移動流量。
- **D：** 符合本題。Global compute 相對容易，mutable state、identity 與 dependency readiness 才決定 Region 是否真的能接手。

**事實查證：** [Route 53 routing policies](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)、[What is AWS Global Accelerator?](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)、[Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 2｜SAP｜Route 53 與 Global Accelerator 選型

一個非 HTTP 的低延遲 TCP service 部署在兩個 Regions。客戶端 firewall 只允許少數固定 public IP，並希望 traffic 從最近 AWS edge 進入 backbone 後送到 healthy regional endpoint。應選哪個入口？

A. AWS Global Accelerator，並仍獨立設計 endpoint health 與 regional state
B. 使用 Route 53 latency routing 提供 DNS 選路；入口仍使用 DNS 位址題目要求的固定 anycast IP
C. 使用 CloudFront 加速 HTTP content，將非 HTTP TCP/UDP 流量仍送原本 regional endpoint
D. 建立 Global Accelerator listener 與兩個 endpoint groups，客戶 firewall 只 allowlist 其中一個 anycast IP

**答案：A**

- **A：** 符合本題。Global Accelerator 提供 static anycast IP 與 edge-to-regional TCP/UDP routing；但不會複製 state。
- **B：** Route 53 latency routing 可把 DNS answer 導向低延遲 endpoint，但 client 看到的是可變 endpoint address，不符合只允許少數固定 public IP 的 firewall contract。
- **C：** CloudFront 適合 HTTP(S) content 與支援的 edge workloads，不是任意非 HTTP TCP/UDP proxy；原 regional endpoint 也沒有得到固定 anycast ingress。
- **D：** Global Accelerator listener 是正確服務；若 client allowlist 只納入其中一個 anycast IP，或 endpoint health/traffic dial 沒有預先設計，仍無法達到入口容錯。

**事實查證：** [Route 53 routing policies](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)、[What is AWS Global Accelerator?](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)

### 練習題 3｜SAP｜DNS failover 的 cache 與完整健康驗證（選兩項）

公司用 Route 53 failover records 將 API 從 Region A 切到 Region B。演練時 ALB health check 已失敗，但部分 clients 十分鐘後仍連到 A，且 B 的 database 仍是 read-only。哪兩項改進最重要？（選兩項）

A. 在 planned event 前適度降低 TTL，並把 resolver/client cache 與既有 TCP connections 納入切換時間估算
B. 降低 Route 53 TTL 並建立 health check；secondary 的 write path 與 dependencies 以基礎 health checks 作為驗收
C. 準備可寫 secondary，將 Route 53 record TTL 設為 30 秒，並以 30 秒作為 client traffic 完成切換的目標
D. 健康判斷與 runbook 要驗證完整 regional stack，包括 application、dependencies 與 database write readiness，而不只 ALB
E. Route 53 failover record 使用 30 秒 TTL，load balancer connection draining 也設定 30 秒

**答案：A、D**

- **A：** 符合本題。DNS failover 受 TTL、recursive resolver/client caching 與既有 connections 影響，不能假設瞬間完成。
- **B：** 低 TTL 與 health check 能改善 DNS answer 更新，secondary 的 database/write dependencies 只以入口健康驗收時，仍可能把流量送到不能完成交易的 Region。
- **C：** 可寫 secondary 處理了資料層；把 failover time 等同 DNS TTL 會忽略 recursive resolver/client cache 與既有 TCP connections。
- **D：** 符合本題。入口 healthy 不代表 database、secrets、queues 與 downstream dependencies 已能提供 business outcome。
- **E：** TTL 與 connection draining 都設 30 秒可作調校起點，兩個計時器控制不同層，不能保證所有 resolver cache 和 established sessions 在 30 秒內消失。

**事實查證：** [Route 53 active-passive failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-types.html)、[Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 4｜SAP｜Aurora Global Database writer topology

金融系統使用 Aurora Global Database，需要單一 authoritative writer、其他 Regions local reads，以及災難時受控接管。哪個設計描述最準確？

A. 保留 Aurora Global Database 單一 writer；讓所有 Regions 透過 write forwarding 承接同等寫入權威
B. 明確維持 primary writer Region，secondary Regions 供 reads/DR；依文件使用 switchover 或 failover，讓應用 reconnect，並處理 replication lag、write forwarding 與 reconciliation
C. Secondary cluster 提供 local reads，promotion runbook 以 database cluster health 作為唯一 readiness gate；Database timeline 保存 cluster role、replication lag、switchover event、client reconnect 與 writer endpoint，相關 alarms 與 rollback timestamp 納入 release evidence
D. 更新 DNS 到 secondary cluster，再執行 planned switchover 或 unplanned failover

**答案：B**

- **A：** Write forwarding 可讓 secondary endpoint 將 writes 送往 primary，不會把每個 Region 變成同等 authoritative writer；writer failure 仍需受控 role transition。
- **B：** 符合本題。Aurora global architecture 要把 database role transition 與 application traffic transition 明確排序並驗證。
- **C：** Local reads 與 cluster health 是必要 evidence，database healthy 不代表 application、secrets、queues 和 write invariants 已能在 secondary 完成。
- **D：** 先把 DNS 指向 secondary 會讓 application 在 writer transition 前連到 read-only/舊角色 endpoint；planned switchover 應協調 database role 與 traffic 順序。

**事實查證：** [Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)、[Planned and unplanned Aurora global database failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 5｜SAP｜DynamoDB global tables MREC 與 MRSC

一個全球 catalog 可容忍短暫跨 Region convergence；另一個帳務 invariants 要求支援範圍內的 multi-Region strong consistency。架構師說 DynamoDB global tables 一律只有 eventual consistency。哪個回應正確？

A. 建立 MREC global table 並把 strongly consistent local reads 當成跨 Region 強一致交易
B. Catalog 與帳務 workloads 都採 MRSC global tables，統一使用相同 Region topology 與 write routing；Table inventory 記錄 consistency mode、replica Regions、supported topology、read setting 與 transaction requirements，具名 owner 與 approver 依固定 cadence 複核
C. 應依 application invariants、latency、Region topology 與功能限制選擇 MREC 或 MRSC，不能用單一一致性敘述概括所有 global tables
D. 在既有 global table 的同一次 production change 中切換 consistency mode 與 Region topology，沿用原 application traffic

**答案：C**

- **A：** MREC table 的 strongly consistent read 只適用本地支援語意，不會把跨 Region replication 變成 MRSC transaction contract。
- **B：** MRSC 可服務需要 multi-Region strong consistency 的支援 workload；catalog 已容忍 convergence，強制共用相同 topology 會增加限制與成本，未依 invariant 選型。
- **C：** 符合本題。MREC 與 MRSC 提供不同 consistency/latency/availability contract，必須由 business invariant 選擇。
- **D：** Consistency mode 有各自建立/轉換與 topology 條件，不能把 production error 當作 capability discovery。適合先在支援矩陣與代表 workload 驗證。

**事實查證：** [DynamoDB global tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)、[How DynamoDB global tables and their consistency modes work](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/create-gt-mrsc.html)

### 練習題 6｜SAP｜避免 active-active write conflicts

購物平台讓兩個 Regions 同時更新同一個 customer balance，使用 timestamp 決定最後寫入者。時鐘偏差與重試造成餘額遺失。哪個改造最直接處理核心問題？

A. 允許兩個 Regions 同時更新同一 account balance，再以 last-writer-wins 接受衝突結果；Audit trail 另標示「避免 active-active write conflicts」的設定版本、生效時間與 exception expiry
B. 以 idempotency keys 去除重試，每個 Region 由自己的 reconciliation worker 維護 account balance；Balance audit 保存 operation ID、entity owner Region、version、idempotency key 與 reconciliation result，具名 owner 與 approver 依固定 cadence 複核
C. 啟用 active-active writes；「避免 active-active write conflicts」的 change record 另保存 scope、owner、approver 與 rollback trigger；Audit trail 另標示「避免 active-active write conflicts」的設定版本、生效時間與 exception expiry
D. 依 tenant/entity 分配 write ownership，或選能滿足 invariant 的 datastore mode；所有 operations 使用 idempotency 並定義 conflict/reconciliation

**答案：D**

- **A：** Last-writer-wins 適合可覆寫且衝突可接受的資料，balance update 是不可交換的 business invariant，時鐘排序會遺失合法增減。
- **B：** Idempotency 可消除重試重複，兩個 Region 的 reconciliation workers 仍可能同時更新同一 balance，沒有建立單一 write authority。
- **C：** Reconciliation 與補償可修部分衝突，customer balance 在發現前已可能違反不可透支或總額守恆；核心應先限制 concurrent ownership。
- **D：** 符合本題。需從資料 ownership、consistency 與 idempotency 約束 conflicts，而非依賴 wall-clock overwrite。

**事實查證：** [DynamoDB global tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)、[Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)

### 練習題 7｜SAP｜多 Region dependency readiness

Region failover 測試時 compute 與 database 都正常，但應用無法解密 secrets、拉取 container image，也因 target Region quota 不足無法擴容。最佳預防方式是什麼？

A. 建立並演練 regional dependency checklist：keys/policies、secrets、artifacts、certificates、quotas、configuration、event checkpoints 與 third-party allowlists
B. 複製 application artifacts 與 secrets，secondary Region 採 service default quotas，certificates 於 failover runbook 中簽發
C. 準備 database replica 與 DNS；驗證 queue checkpoints、third-party dependencies 和 KMS grants
D. 預先建立 secondary compute 與 database，quota increase、certificate 與 emergency access 由 regional failover automation 於事件中申請

**答案：A**

- **A：** 符合本題。Failover readiness 必須涵蓋完整 dependency graph，並以 game day 實際驗證。
- **B：** 複製 artifacts/secrets 有助啟動；service default quota 與事件期間簽發 certificate 會讓 capacity 與 TLS readiness 落在 recovery critical path。
- **C：** Database、DNS、queue checkpoint 與 KMS grants 涵蓋主要依賴，仍可能被 image repository、certificate、quota、configuration 或 third-party allowlist 阻擋。
- **D：** 只預建 compute/database 而把 quota 與 operational access request 放進 incident runbook，適合寬鬆 RTO；題目要避免測試時才發現 dependency 不可用。

**事實查證：** [Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Planned and unplanned Aurora global database failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

### 練習題 8｜SAP｜全球架構中的 data residency（選兩項）

歐盟客戶的原始醫療資料不得離開核准 Regions，但全球 support portal 需要顯示去識別化摘要。哪兩個設計原則最合理？（選兩項）

A. 讓 Route 53 geolocation 將 EU users 導到 EU；database replication 仍把原始資料送往其他 Regions
B. 分類 authoritative、restricted 與 derived data，只在核准 Regions 保存原始資料，僅複製允許的去識別化 projections
C. 只複製加密後的原始醫療資料到全球 Regions，將 encryption 視為 residency 例外
D. 在各 Region 以共同 tokenization service 產生 support projection，通過平台級演算法審查後視為可跨區資料
E. 讓 identity、routing、replication policy 與 exception/audit evidence 一起執行 residency 決策，而不是只依使用者延遲

**答案：B、E**

- **A：** Geolocation routing 可把 EU users 送往 EU endpoint，不能限制 database replication；原始資料仍離開核准 Region。
- **B：** 符合本題。Residency 應建立在 data classification 與 permitted projection 上，避免複製原始受限欄位。
- **C：** Encryption 保護 confidentiality，不改變資料所在的法律/政策位置；encrypted raw medical data 仍受 residency 限制。
- **D：** 全球 projection 可以支援 support；若只依通用 tokenization 宣告 de-identification，沒有欄位級分類、核准與重識別風險 evidence，不能證明允許跨區複製。
- **E：** 符合本題。必須讓 access、entry point、state movement 與 evidence 對同一 residency policy 負責。

**事實查證：** [AWS Digital Sovereignty](https://aws.amazon.com/compliance/digital-sovereignty/)、[Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 9｜SAP｜regional switchover 與 failback runbook

團隊計畫 Aurora Global Database 的 Region switchover。哪個 runbook 次序最能避免 split brain 與資料遺失？

A. 完成 database promotion與 DNS 切換，in-flight writes 交由 client retries，failback 以反向 DNS 切換執行；DR timeline 對齊 write fencing、replication checkpoint、database role、DNS change 與 business validation，設定版本與生效時間一併寫入 change record
B. 依需求 quiesce/fence writes，確認 replication state，執行 managed database switchover/failover，更新/驗證 application traffic 與 invariants，再規劃 reconciliation 和 failback
C. 只更新 application traffic，讓原 Region database 繼續作 writer 並跨洲承接所有 writes
D. Failback 以反向切換 DNS 與 application traffic 執行，原 primary 同時恢復 writer role；「regional switchover 與 failback runbook」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：B**

- **A：** Promotion 與 DNS 都是必要步驟；沒有先 quiesce/fence writes、確認 replication state 和驗證 invariants，client retries 可能在角色轉換時造成重複或遺失。
- **B：** 符合本題。Writer ownership、replication readiness 與 traffic movement 要在同一 runbook 中有明確順序和驗收。
- **C：** 讓 application 跨洲繼續寫原 primary 可作暫時流量方案，並沒有完成 database switchover，也保留原 Region 為單一 writer failure domain。
- **D：** Failback 不能只反向 DNS 並同時恢復原 writer；若 replication/reconciliation 尚未完成，兩邊可能再次取得寫入權威。

**事實查證：** [Planned and unplanned Aurora global database failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)、[Route 53 active-passive failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-types.html)

### 練習題 10｜SAP｜以 RTO/RPO 與成本選擇 multi-Region 模式

內部 reporting app 的 RTO 是 8 小時、RPO 是 1 小時，每月只使用兩次。團隊提議建立全天候雙 Region full-capacity active-active。哪個評估方式較合理？

A. 所有 workloads 採 active-active，以供應商 reference architecture 的估算值作為低 RTO 依據；Audit trail 另標示「以 RTO/RPO 與成本選擇 multi-Region 模式」的設定版本、生效時間與 exception expiry；「以 RTO/RPO 與成本選擇 multi-Region 模式」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 只依 infrastructure recovery 選型，不把 business RTO/RPO、write semantics 與 usage 納入；Continuity cost model 分開計算 idle capacity、replication、data transfer、observability、exercise 與 recovery labor，具名 owner 與 approver 依固定 cadence 複核
C. 比較 idle/active capacity、replication、cross-Region transfer、observability 與演練成本對 RTO/RPO/latency 的價值；若需求允許，採 active-passive、pilot light 或 backup/restore
D. 購置完整 secondary capacity；「以 RTO/RPO 與成本選擇 multi-Region 模式」的 dashboard 也保留 quota/cost、alarm state 與 last validation；「以 RTO/RPO 與成本選擇 multi-Region 模式」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：C**

- **A：** Full active-active 適合極低 RTO、全球低延遲且使用頻繁的 workload；每月兩次、RTO 8 小時的 reporting app 未證明這筆常態成本有價值。
- **B：** Infrastructure recovery time 是一項輸入；不納入 business RTO/RPO、write semantics 和 usage，無法在 backup/restore、pilot light 與 warm/full capacity 間選擇。
- **C：** 符合本題。Architecture 應由 business continuity objective 與總成本驅動，而不是把最高可用模式當預設。
- **D：** 先購置完整 secondary 再用演練判斷可以取得真實數據，會在已有寬鬆目標時承擔不必要常態成本；可先用較小可逆驗證估算。

**事實查證：** [Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「依資料語意選single-writer、read-local、active-active或partitio…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「全球架構要同時處理route、compute、data consistency、write ownership與failover。」，所以「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」能直接滿足它；若constraint改成「只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」。替代方案「只將stateless compute active-active可先改善availability，而不必立即讓所有database多主。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「全球架構要同時處理route、compute、data consistency、write ownership與failover。」，排除會導致「DNS切換後新Region沒有最新secret、event offsets或寫入權，造成split brain。」的選項，再選「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」。本章對應的代表task包括：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「依資料語意選single-writer、read-local、active-active或partitioned ownership，再選Route 53/GA與data service。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「global compute is easier than global mutable state」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 84 章　Organization-wide Backup、DR 與 Compliance

各團隊自行備份會產生不一致retention、未加密副本與無人測試的restore。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

如果今天由你值班，收到的需求可能是這樣：勒索風險要求所有production database具跨帳號immutable copy與季度restore證明。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：各團隊自行備份會產生不一致retention、未加密副本與無人測試的restore。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 這只是起點，因為恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Backup承接主要責任，以Backup Vault Lock檢查替代條件，並用「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：勒索風險要求所有production database具跨帳號immutable copy與季度restore證明。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Backup]
          │ 以policy集中排程、保存與複製多種AWS resource backups。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · Backup Vault Lock：以WORM controls防止backup recovery points在保留期內被刪除或縮短。
  · AWS Organizations：集中建立accounts、OU、政策與consolidated billing。

失敗時先找：Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和Backup Vault Lock並不是兩個任意的產品名稱。前者適合本章，是因為「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」直接回應了眼前的問題；後者描述的「Service-native backup提供更細能力，仍可由組織policy建立最低基線。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「recovery assets need independent ownership」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| Backup Vault Lock | 以WORM controls防止backup recovery points在保留期內被刪除或縮短。 | Governance可由特權繞過；Compliance在grace period後連root也不能改。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |

## 把全圖套進一個具體案例

**場景：** 勒索風險要求所有production database具跨帳號immutable copy與季度restore證明。

1. 故事的起點：勒索風險要求所有production database具跨帳號immutable copy與季度restore證明。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Backup Vault Lock、AWS Organizations各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：各團隊自行備份會產生不一致retention、未加密副本與無人測試的restore。
- **具體例子／邊界：** 在「勒索風險要求所有production database具跨帳號immutable copy與季度restore證明。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Backup Vault Lock

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Service-native backup提供更細能力，仍可由組織policy建立最低基線。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：recovery assets need independent ownership。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

## 回到 AWS：Components、功用與責任邊界

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

### Backup Vault Lock

- **功用：** 以WORM controls防止backup recovery points在保留期內被刪除或縮短。
- **底層機制：** Governance可由特權繞過；Compliance在grace period後連root也不能改。
- **關鍵設定：** governance/compliance mode、min/max retention、changeable grace time、KMS與cross-account copy。
- **選擇時機：** 勒索軟體隔離、法規不可變保存與security account vault。
- **替換時機：** 若保留規則尚未驗證先用governance；compliance設定錯誤可能無法逆轉。

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

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

### Backup Vault Lock：逐項設定說明

#### `governance/compliance mode`

- **控制什麼：** `governance/compliance mode`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Backup Vault Lock設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `min/max retention`

- **控制什麼：** `min/max retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「勒索軟體隔離、法規不可變保存與security account vault。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Backup Vault Lock的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `changeable grace time`

- **控制什麼：** `changeable grace time`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「勒索軟體隔離、法規不可變保存與security account vault。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Backup Vault Lock的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「勒索軟體隔離、法規不可變保存與security account vault。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Backup Vault Lock指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `cross-account copy`

- **控制什麼：** `cross-account copy`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「勒索軟體隔離、法規不可變保存與security account vault。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Backup Vault Lock依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

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

## 讀到這裡，請用自己的話說一次

1. AWS Backup的責任：以policy集中排程、保存與複製多種AWS resource backups。
2. 底層機制：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
3. 第一個要看的設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
4. 選擇邏輯：用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。
5. 不要混淆：Backup Vault Lock的責任是「以WORM controls防止backup recovery points在保留期內被刪除或縮短。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。
8. 可移植原則：recovery assets need independent ownership。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| Backup Vault Lock | 以WORM controls防止backup recovery points在保留期內被刪除或縮短。 | Governance可由特權繞過；Compliance在grace period後連root也不能改。 | 勒索軟體隔離、法規不可變保存與security account vault。 | 若保留規則尚未驗證先用governance；compliance設定錯誤可能無法逆轉。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Service-native backup提供更細能力，仍可由組織policy建立最低基線。 | 只有當題目條件明確改變時才可能合理。 | Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Service-native backup提供更細能力，仍可由組織policy建立最低基線。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.3 Design reliable and resilient architectures；SAP-1.4 Design a multi-account AWS environment；SAP-2.2 Design a solution to ensure business continuity；SAP-3.2 Determine a strategy to improve security；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAP｜Organizations backup policy 與 effective policy

企業要確保所有 production accounts 的 tagged databases 每日備份並保留 35 天。有人提議用 SCP 來排程 backup。哪個方案正確？

A. 用 AWS Organizations backup policies 在 root/OU/account 組合完整 policy，指定 resource selection、IAM role、schedule/lifecycle/vault，並檢查 effective policy
B. 使用 Organizations backup policy 定義 schedule；resource selection 仍由各帳號人工維護
C. 以 SCP 要求 teams 呼叫 Backup API，將 SCP 當成實際執行 backup 的 scheduler
D. 附加 backup policy 到 root；缺少 recovery points 後檢查 effective policy 與 opt-in；Effective-policy report 顯示 inherited plan fragments、resource selection、IAM role、vault、schedule 與 lifecycle，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。Backup policy 能跨 organization 定義 baseline，但仍要確保 inherited policy 完整且資源/role 可用。
- **B：** Organization backup policy 可以集中 schedule；resource selection 由各帳號人工維護時，新增 tagged database 仍可能不進入 plan，無法形成 organization-wide baseline。
- **C：** SCP 只限制 principals 可呼叫哪些 API，不會建立 backup plan、排程 job 或選取 resources，因此不能當 scheduler。
- **D：** Root 的 policy fragment 會與子層 effective policy 組合；若 role、selection、vault 或 opt-in 不完整，附加成功也不會產生符合要求的 recovery point。

**事實查證：** [Backup policies in AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup.html)、[Policy inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html)

### 練習題 2｜SAP｜跨帳號 backup copy 的獨立 ownership

勒索情境要求 production account administrators 即使被入侵，也無法刪除唯一可恢復副本。哪個 backup copy 設計最合適？

A. 跨帳號 copy 到 recovery account；workload admins 同時可刪 destination vault 與 KMS key；Audit trail 另標示「跨帳號 backup copy 的獨立 ownership」的設定版本、生效時間與 exception expiry
B. 把 recovery points 複製到 recovery/security account 擁有的 destination vault，使用可支援跨帳號的 KMS/policies，只允許必要 copy/restore 路徑並隔離 delete 權限
C. 在同帳號建立第二 vault 並套 Vault Lock，仍與 compromised account 共用管理邊界
D. 以 copy-job completed 作為 destination 可用證據，立即依 lifecycle 到期 source copy；restore role 與 KMS grant 沿用 source account 設計；Recovery inventory 記錄 source/destination account、vault owner、KMS key、delete principal 與 copy status，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** Cross-account copy 已建立不同資源位置；workload admins 同時能刪 destination vault/key 時，compromised principal 仍可摧毀 recovery copy。
- **B：** 符合本題。Destination account custody、vault/KMS policies 與 restricted source access 才形成獨立 recovery boundary。
- **C：** 同帳號第二 vault 加 Vault Lock 可提高不可變性，仍與 production administrator、root 與 account compromise 共用控制邊界。
- **D：** 刪除 source copy 可降低費用；若 destination restore role、KMS 與完整性只由 copy-job success 推定，故障時可能留下不可還原的唯一副本。

**事實查證：** [Cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)

### 練習題 3｜SAP｜cross-Region recovery point 不等於 DR stack（選兩項）

公司每天把 backups 複製到第二個 Region，主管因此宣稱已達成 30 分鐘 RTO 與 5 分鐘 RPO。哪兩個反駁最關鍵？（選兩項）

A. 建立每日 cross-Region recovery point；準備 network、identity、compute 與 application configuration
B. Cross-Region recovery point 只提供可用資料副本；identity、network、compute、configuration、quotas 與 restore sequence 仍需建立和演練
C. 建立 warm standby stack，資料每日備份到 secondary Region，Route 53 health check 負責入口切換
D. 用 cross-Region copy completion timestamp 加上預估的 infrastructure initialization time，計算並報告 30 分鐘 RTO
E. 每日 backup 的可能資料損失窗口通常無法直接證明 5 分鐘 RPO，應依 schedule/PITR/replication 實測

**答案：B、E**

- **A：** 預先準備 network/identity/compute 可縮短 RTO；每日 recovery point 的資料窗口仍遠大於 5 分鐘，無法證明 RPO。
- **B：** 符合本題。Recovery asset 與 ready-to-serve application 是兩件事，RTO 取決於整個 restore dependency path。
- **C：** Warm standby 能改善 application RTO，資料只靠每日 backup 時仍可能損失近一天 writes；入口 health check 也不能補足 state freshness。
- **D：** 用 backup copy completion 與預估 initialization time 可作 planning estimate，不是實際 restore/replay/dependency test，不能證明 30 分鐘 RTO。
- **E：** 符合本題。RPO 是可接受資料損失；每日 point-in-time copy 與 5 分鐘要求明顯需要更細緻機制與測量。

**事實查證：** [Cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 4｜SAP｜Backup Vault Lock Governance 與 Compliance mode

法遵要求 grace period 結束後，連 root user 都不能縮短七年 retention；另一個非 production vault 則允許少數授權管理者調整 lock。應如何配對 Vault Lock modes？

A. 使用 Governance mode 並嚴格限制 bypass role，將它當成監管要求的不可撤銷 retention
B. 使用 Compliance mode，grace period 內由單一 backup administrator 核准 retention 與 KMS ownership
C. 法遵 vault 用 Compliance mode 並在 grace period 前驗證設定；Vault-lock register 保存 mode、grace-time expiry、minimum/maximum retention、change actor 與 compliance state，相關 alarms 與 rollback timestamp 納入 release evidence
D. 在 production vault 完成 Compliance mode lock，再以真實 recovery points 驗證 retention bounds 與營運修正流程

**答案：C**

- **A：** Governance mode 可由具權限的 principal 移除或修改 lock，適合內部治理，不符合 grace period 後連 root 都不能縮短 retention 的法遵要求。
- **B：** Compliance mode 適合法遵 vault；選項沒有為可調整的 non-production vault 配對 Governance mode，且單一管理者同時核准 retention/key 也弱化職責分離。
- **C：** 符合本題。Compliance mode 在 lock 生效後提供更強不可變性，必須在不可逆前確認 retention bounds；Governance 適合受控管理變更。
- **D：** Vault Lock 生效後才用 production recovery points 測錯誤 retention 可能遇到不可逆設定；應在 grace period 和非正式資料上完成驗證。

**事實查證：** [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)

### 練習題 5｜SAP｜logically air-gapped vault 的角色

公司希望在 ransomware recovery 中有一個與日常 workload 權限更隔離、可受控分享給 recovery account 的 vault。有人說 logically air-gapped vault 會自動複製所有 backups 並完全離線。哪個理解正確？

A. 把 standard-vault recovery points 定期 copy 到同一 workload account 的 logically air-gapped vault，復原沿用 workload emergency role；Vault inventory 記錄 primary/copy source、retention、RAM share、KMS path、restore role 與 last validation，設定版本與生效時間一併寫入 change record
B. 直接建立 primary backups 到 logically air-gapped vault，透過 RAM 分享整個 vault，recovery role 取得廣泛 restore permissions
C. 透過 RAM 將 logically air-gapped vault 分享給 recovery account，restore 時沿用 workload KMS grants 與既有 emergency role
D. 把 logically air-gapped vault 納入 backup plan 的 resource selection，必要時再使用 copy action；另定 retention、RAM sharing、restore role、validation 與 incident runbook

**答案：D**

- **A：** Copy 到 logically air-gapped vault 是受支援架構；vault 與 restore role 都留在 workload account 的同一權限邊界，沒有達成 recovery account 隔離。
- **B：** Primary backup 可直接寫入 logically air-gapped vault，RAM sharing 也是真實能力；給 recovery role 廣泛 restore 權限會擴大 blast radius，仍需最小權限和驗證。
- **C：** 分享 vault 可建立跨帳號 recovery path；KMS、retention 與 restore authorization 若只在 incident 才解析，RTO 會被 control-plane 與 policy troubleshooting 支配。
- **D：** 符合本題。Logically air-gapped vault 可直接接收 primary backups，也可接收 copies；是否使用 copy action取決於架構。Vault 的隔離與共享能力不能取代 restore 驗證和權限設計。

**事實查證：** [Logically air-gapped vaults](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)、[Cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)

### 練習題 6｜SAP｜restore testing 與 application validation

AWS Backup 顯示所有 backup jobs 成功。季度稽核卻要求證明 application 能在隔離 network 中恢復並完成一筆測試交易。最佳方案是什麼？

A. 建立 scheduled restore testing，提供正確 restore metadata/network，完成後執行 data consistency 與 application transaction validation，再記錄時間與結果
B. 啟用 AWS Backup restore testing，只驗證 restore job completed，不執行資料與 application checks；「restore testing 與 application validation」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 由 workload team 每季手動 restore 一個 recovery point，結果記錄在該團隊的 change tickets
D. 將 restore-job completed 狀態視為 recovery-point 驗收，application transaction test 由年度 DR exercise 執行；Restore evidence 保存 recovery-point age、job duration、network metadata、data checks 與 transaction result，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。Restore testing 加 post-restore validation 才能把 recovery point 轉成可驗證的 business recovery evidence。
- **B：** Restore-job completed 證明 AWS Backup 完成資源還原，不證明資料一致、應用可啟動或 business transaction 成功。
- **C：** 人工季度 restore 可產生有效 evidence，適合少量 workload；缺少標準 metadata、isolated network 與自動 application checks 時，跨帳號結果難以一致比較。
- **D：** 年度 transaction test 可以支援較寬鬆稽核週期；題目要求季度證明，單看每次 restore job 狀態無法補足應用驗證。

**事實查證：** [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Restore testing validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

### 練習題 7｜SAP｜AWS Backup Audit Manager controls

法遵團隊要跨帳號檢查 protected resources 是否符合 backup frequency、retention、cross-account copy 與 restore activity 要求。哪個做法最合適？

A. 使用 Backup Audit Manager 評估 policy compliance，將 compliant report 視為應用可恢復證據；「AWS Backup Audit Manager controls」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 使用 AWS Backup Audit Manager 選擇對應 controls 與 scope，了解支援邊界，把 noncompliance 指派給 owner；另用 restore validation 證明 application recoverability
C. 以 scheduled restore testing 作為 backup frequency、retention、encryption 與 cross-account copy 的主要合規檢查；Compliance report 將 framework control、resource scope、evaluation time、owner 與 remediation ticket 關聯，相關 alarms 與 rollback timestamp 納入 release evidence
D. 以 Backup Audit Manager compliant report 作為 RTO/RPO 證據，restore game day 每年執行一次；「AWS Backup Audit Manager controls」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：B**

- **A：** Backup Audit Manager 能評估 controls 與產生報告；compliant 不代表 recovery point 可成功啟動 application 或符合 transaction-level RTO。
- **B：** 符合本題。Framework 評估技術 controls，owner/remediation 與 application restore evidence 仍需另外建立。
- **C：** Restore testing 適合證明 recoverability；它不是用來持續判斷所有 resources 的 backup frequency、retention、encryption 和 cross-account copy policy。
- **D：** Audit Manager report 可作 policy evidence，不會量測完整 application failover 的 RTO/RPO；一年一次 game day 也可能不符合控制要求的 cadence。

**事實查證：** [AWS Backup Audit Manager controls](https://docs.aws.amazon.com/aws-backup/latest/devguide/choosing-controls.html)、[Restore testing validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

### 練習題 8｜SAP｜scheduled recovery point 與 PITR 選擇（選兩項）

訂單資料庫要求能恢復到最近 10 分鐘內的狀態，並另外保留每月 recovery point 七年。哪兩個敘述正確？（選兩項）

A. 對支援的 database 啟用 continuous backup/PITR，以符合 fine-grained recovery window，並定期測試
B. 只保留每月 recovery points 七年，將其作為最近十五分鐘變更的復原來源
C. 另建立 scheduled monthly recovery points 與適當 lifecycle/retention，處理長期保存需求
D. 只啟用 PITR 並假設可保留七年，不建立符合法遵期限的 scheduled backups
E. 所有 resources 套用七年 scheduled-backup lifecycle，PITR 關閉以避免同一份資料產生兩種 retention

**答案：A、C**

- **A：** 符合本題。PITR 適合在 supported window 內選擇較細時間點，但仍需 restore test。
- **B：** 七年 monthly points 滿足長期保存，不提供最近 10 分鐘的細粒度復原點。
- **C：** 符合本題。長期保留應使用排程 recovery points/copies 與 retention policy，和 operational PITR 互補。
- **D：** PITR 適合近期 operational recovery，其支援 window 不是七年法遵 archive；兩種 retention 需求需要不同 recovery-point 類型。
- **E：** 七年 scheduled backups 可滿足 archive；關閉 PITR 會失去 10 分鐘 recovery objective，兩種機制並存並不代表重複錯誤。

**事實查證：** [Continuous backup and point-in-time recovery](https://docs.aws.amazon.com/aws-backup/latest/devguide/point-in-time-recovery.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Backup lifecycle and cold storage](https://docs.aws.amazon.com/aws-backup/latest/devguide/editing-a-backup.html)

### 練習題 9｜SAP｜backup cold storage lifecycle

公司想把所有 recovery points 建立後一天就移到 cold storage，再於第十天刪除，以降低成本。哪個評估方式正確？

A. 所有支援 cold storage 的 recovery points 在建立當日轉入 cold tier，restore SLA 採服務預設
B. 依 cold-storage 單價選擇 lifecycle，法遵 retrieval SLA 沿用 AWS Backup 的預設 restore behavior；Lifecycle report 顯示 warm/cold tier、transition date、minimum duration、retrieval time 與 deletion charge，具名 owner 與 approver 依固定 cadence 複核
C. 確認 resource 支援、transition 規則、minimum cold-storage duration、restore latency、legal retention 與 copy schedule；不符合短期需求者留在 warm tier
D. 將 production recovery points 依最低儲存成本轉入 cold tier，以第一輪實際 restore time 校準 RTO

**答案：C**

- **A：** Cold tier 的 transition 受 resource support 與 minimum storage duration 約束，不是所有 recovery point 都能建立當日轉入；restore latency 也不能只採預設。
- **B：** Cold-storage 單價是重要因素；法遵 retrieval SLA、minimum duration、early deletion charge 與 resource 支援會改變最便宜且可行的 lifecycle。
- **C：** 符合本題。只有在保留時間與 restore objective 相容時，cold tier 才真正節省成本。
- **D：** 先將 production backups 轉 cold 可得到真實 restore time，若 RTO 較短就已把唯一近期副本放進較慢 tier；應先用代表副本驗證。

**事實查證：** [Backup lifecycle and cold storage](https://docs.aws.amazon.com/aws-backup/latest/devguide/editing-a-backup.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 10｜SAP｜ransomware recovery ownership 與 game day

公司有跨帳號 immutable backups，但沒有人確定事故時誰能解鎖 KMS access、建立 network、restore database 或驗證 business data。哪個下一步最能提高實際 recoverability？

A. 保留 immutable cross-account copies；recovery account 的 KMS 與 administrators 由相同中央 security team 管理；Audit trail 另標示「ransomware recovery ownership 與 game day」的設定版本、生效時間與 exception expiry
B. 完成 Vault Lock 與 logically air-gapped vault，為 application、DNS/network 與 incident command 指定不同 owners；Game-day timeline 記錄 credential loss、Region loss、key access、restore sequence、DNS cutover 與 application acceptance，具名 owner 與 approver 依固定 cadence 複核
C. 日常以 backup-job success、recovery-point count 與 Audit Manager reports 驗收 ransomware readiness
D. 明確指定 policy、vault/key、restore、network、application validation 與 incident-command owners，演練 workload account/primary Region/credentials 同時失效並追蹤缺口

**答案：D**

- **A：** Immutable cross-account copies 是核心防線；KMS、vault administration 和 incident command 都由同一小組掌握時，credential compromise 或操作錯誤仍可能成為共同故障域。
- **B：** Vault Lock、air-gapped vault 與指定 application/network owners 已接近完整設計；沒有實際演練同時失去 workload account、Region 和 credentials，仍無法證明整條恢復路徑。
- **C：** Backup-job success 與 storage count 適合日常監控，不能替代 game day；若第一次完整驗證落在真實事故期間，key、network、restore role 和 application sequence 會拉長 RTO。
- **D：** 符合本題。Recoverability 是跨團隊 operating model，必須以有壓力的 game day 驗證 ownership 與 dependencies。

**事實查證：** [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)、[Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「各團隊自行備份會產生不一致retention、未加密副本與無人測試的restore。」，所以「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」能直接滿足它；若constraint改成「Service-native backup提供更細能力，仍可由組織policy建立最低基線。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」。替代方案「Service-native backup提供更細能力，仍可由組織policy建立最低基線。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「各團隊自行備份會產生不一致retention、未加密副本與無人測試的restore。」，排除會導致「Backup role可被workload admin刪除，或KMS key與backup同一故障邊界。」的選項，再選「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」。本章對應的代表task包括：SAP-1.2 Prescribe security controls；SAP-1.3 Design reliable and resilient architectures；SAP-1.4 Design a multi-account AWS environment；SAP-2.2 Design a solution to ensure business continuity。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「用AWS Backup policies跨帳號套用、copy到隔離vault/Region並集中audit。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「recovery assets need independent ownership」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 85 章　Portfolio Cost、Tagging 與 Chargeback

單一帳單無法回答哪個產品、環境或團隊消耗成本，也無法建立責任。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

故事從一個看似簡單的需求開始：CFO需按產品與客戶分攤共享TGW、data lake與support成本。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：單一帳單無法回答哪個產品、環境或團隊消耗成本，也無法建立責任。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Cost and Usage Report會是本章的主要角色，AWS Cost Explorer則幫我們看清邊界。方向是「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：CFO需按產品與客戶分攤共享TGW、data lake與support成本。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Cost and Usage Report]
          │ 輸出最細AWS billing line items到S3供查詢與chargeback。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Cost Explorer：互動分析歷史與預測成本、usage與RI/SP coverage。
  · AWS Budgets：對cost、usage、RI/SP utilization/coverage設定threshold與通知/…

失敗時先找：只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Cost and Usage Report有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Cost and Usage Report和AWS Cost Explorer並不是兩個任意的產品名稱。前者適合本章，是因為「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」直接回應了眼前的問題；後者描述的「Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「cost allocation is an ownership model」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Cost and Usage Report | 輸出最細AWS billing line items到S3供查詢與chargeback。 | 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。 |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 |
| AWS Budgets | 對cost、usage、RI/SP utilization/coverage設定threshold與通知/action。 | Budget依billing data週期評估actual/forecast，越過threshold觸發SNS/email或budget action。 |

## 把全圖套進一個具體案例

**場景：** CFO需按產品與客戶分攤共享TGW、data lake與support成本。

1. 故事的起點：CFO需按產品與客戶分攤共享TGW、data lake與support成本。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Cost and Usage Report負責「輸出最細AWS billing line items到S3供查詢與chargeback。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Cost Explorer、AWS Budgets各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「快速互動圖表用Cost Explorer；通知閾值用Budgets。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Cost and Usage Report

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：單一帳單無法回答哪個產品、環境或團隊消耗成本，也無法建立責任。
- **具體例子／邊界：** 在「CFO需按產品與客戶分攤共享TGW、data lake與support成本。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Cost Explorer

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：cost allocation is an ownership model。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Cost and Usage Report

AWS提供細粒度billing line items與resource IDs的資料集，可輸出到S3供Athena/BI做自訂分析。

### unit economics

以每成功交易、每tenant、每GB或其他business unit計算成本，比只看單一instance月費更能比較架構。

### chargeback

把資源與共享平台成本實際分攤到business/team budget，需要穩定accounts、tags與allocation rules。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### showback

把共享與直接成本顯示給使用團隊但不實際轉帳，先建立成本可見性與行為回饋。

### tagging

為resources加上key/value metadata，以支援ownership、cost allocation、automation與ABAC；taxonomy與enforcement比Name tag更重要。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

## 回到 AWS：Components、功用與責任邊界

### AWS Cost and Usage Report

- **功用：** 輸出最細AWS billing line items到S3供查詢與chargeback。
- **底層機制：** 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。
- **關鍵設定：** report/data export、S3 bucket、time granularity、resource IDs、split cost allocation與format。
- **選擇時機：** FinOps、showback/chargeback、unit economics與自訂cost allocation。
- **替換時機：** 快速互動圖表用Cost Explorer；通知閾值用Budgets。

### AWS Cost Explorer

- **功用：** 互動分析歷史與預測成本、usage與RI/SP coverage。
- **底層機制：** Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。
- **關鍵設定：** date/granularity、filters/group by、cost metric、forecast、RI/SP reports與cost allocation tags。
- **選擇時機：** 回答成本趨勢、來源、forecast與commitment coverage。
- **替換時機：** 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。

### AWS Budgets

- **功用：** 對cost、usage、RI/SP utilization/coverage設定threshold與通知/action。
- **底層機制：** Budget依billing data週期評估actual/forecast，越過threshold觸發SNS/email或budget action。
- **關鍵設定：** budget type/period、filters、actual/forecast thresholds、subscribers與IAM/SCP action。
- **選擇時機：** 防止成本意外、team budget與commitment低利用率告警。
- **替換時機：** 它不是即時hard spending cap；真正阻止資源建立需IAM/SCP/service controls。

## 考前與實作時再查：設定操作手冊

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

### AWS Budgets：逐項設定說明

#### `budget type/period`

- **控制什麼：** `budget type/period`選擇AWS Budgets的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `filters`

- **控制什麼：** `filters`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「防止成本意外、team budget與commitment低利用率告警。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Budgets以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `actual/forecast thresholds`

- **控制什麼：** `actual/forecast thresholds`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `subscribers`

- **控制什麼：** `subscribers`定義event/notification送到哪些consumers，以及是否套用filter、保留payload或跨帳號分享。
- **何時需要：** 一個producer需要fan-out到多個consumer、告警對象或workflow入口時。
- **怎麼設定／驗證：** 建立target/subscription與filter，設定resource policy、retry/DLQ和owner；用匹配與不匹配event各測一次。
- **常見錯法：** 只建立topic/bus卻沒有可用target不會產生business effect；consumer仍需處理duplicate與schema evolution。

#### `IAM/SCP action`

- **控制什麼：** `IAM/SCP action`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「防止成本意外、team budget與commitment低利用率告警。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Budgets明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 讀到這裡，請用自己的話說一次

1. AWS Cost and Usage Report的責任：輸出最細AWS billing line items到S3供查詢與chargeback。
2. 底層機制：定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。
3. 第一個要看的設定：report/data export、S3 bucket、time granularity、resource IDs、split cost allocation與format。
4. 選擇邏輯：Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。
5. 不要混淆：AWS Cost Explorer的責任是「互動分析歷史與預測成本、usage與RI/SP coverage。」；它不會自動取代AWS Cost and Usage Report。
6. 替換訊號：快速互動圖表用Cost Explorer；通知閾值用Budgets。
7. 最常見錯法：只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。
8. 可移植原則：cost allocation is an ownership model。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Cost and Usage Report | 輸出最細AWS billing line items到S3供查詢與chargeback。 | 定期產生含resource IDs、tags、pricing與credits的files，可透過Athena/Glue/Redshift分析。 | FinOps、showback/chargeback、unit economics與自訂cost allocation。 | 快速互動圖表用Cost Explorer；通知閾值用Budgets。 |
| AWS Cost Explorer | 互動分析歷史與預測成本、usage與RI/SP coverage。 | Billing data按service/account/tag/dimension聚合，可建立reports與anomaly investigation。 | 回答成本趨勢、來源、forecast與commitment coverage。 | 逐筆最細分析與自訂BI使用CUR/Data Exports；預算guardrail用Budgets。 |
| AWS Budgets | 對cost、usage、RI/SP utilization/coverage設定threshold與通知/action。 | Budget依billing data週期評估actual/forecast，越過threshold觸發SNS/email或budget action。 | 防止成本意外、team budget與commitment低利用率告警。 | 它不是即時hard spending cap；真正阻止資源建立需IAM/SCP/service controls。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。 | 只有當題目條件明確改變時才可能合理。 | 只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。」之間做選擇。
- 認得常考設定：report/data export、S3 bucket、time granularity、resource IDs、split cost allocation與format。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：快速互動圖表用Cost Explorer；通知閾值用Budgets。
- 對應官方tasks：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAP｜cost-allocation taxonomy 與 ownership

CFO 要按 product、environment、cost center 與 business owner 檢視支出。現況只有不一致的 `Name` tags，shared accounts 也沒有 owner。應先做什麼？

A. 要求每個團隊自由建立 tags，並以月結流程由 Finance 對同義 key/value 做人工合併
B. 定義穩定的 allocation dimensions、允許值、account-level/resource-level 適用範圍、例外與 owner，再將它納入 account/resource provisioning
C. 只用 account name 與 invoice description 分攤成本，不建立 resource-level taxonomy
D. 啟用 CostCenter、cost-center 與 Cost_Center 等既有 tags，月結 pipeline 以字典表正規化 key/value

**答案：B**

- **A：** 自由命名 tags 可讓團隊快速上線；Finance 每月合併同義 key/value 會讓相同資源在不同期間得到不同分類，無法形成穩定 taxonomy。
- **B：** 符合本題。Cost allocation 先是 ownership/taxonomy 問題，之後才是報表工具問題。
- **C：** Account name/invoice 可做粗粒度 showback，shared account 與多產品資源無法得到 resource-level attribution。
- **D：** 字典表可正規化既有多種 spelling，仍把治理留在報表末端；新的 resources 會持續產生不一致 tags，應在 provisioning 時收斂。

**事實查證：** [Account tags for cost allocation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/account-tags-cost-allocation.html)、[Activate user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)

### 練習題 2｜SAP｜啟用 user-defined cost allocation tags

工程團隊已在 EC2、S3 與 RDS 加上 `Product=Atlas`，但本月 Cost Explorer 與 export 沒有完整 Atlas 歷史。最可能還需處理什麼？

A. 在 Billing 啟用 tag 並等待 propagation，申請與本月財務結帳一致的一個月 backfill
B. 使用 Cost Categories 將無 tag 的歷史 usage 歸入 Atlas，並把分類後結果作為 showback allocation basis；Billing audit 保存 resource-tag discovery、activation date、propagation window、backfill request 與 report availability，具名 owner 與 approver 依固定 cadence 複核
C. 在 Billing 啟用支援的 cost allocation tag，等待資料傳播；若符合條件，再申請最多 12 個月的 tag backfill，並記錄不可回填項目與報表生效日
D. 重跑本月報表；財務結帳後確認 tag eligibility、backfill 範圍與 effective date

**答案：C**

- **A：** 啟用 tag、等待 propagation 和申請 backfill 都是正確動作；把範圍固定成一個月會低估現行最多 12 個月的可申請窗口。
- **B：** Cost Categories 可用規則替無 tag 歷史資料做管理分類，適合 approximate showback；它不等同啟用原始 resource tag，也不能重建所有不可回填的 tag history。
- **C：** 符合本題。Resource tag 必須先在 Billing 啟用才成為成本維度。現行功能可依條件申請最多 12 個月 backfill，但仍受 tag eligibility、account 與資料可用性限制。
- **D：** 重新執行報表不會讓未啟用的 tag 自動成為成本維度；eligibility、activation、propagation 與 backfill 必須先完成。

**事實查證：** [Activate user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)、[Cost allocation tag backfill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)

### 練習題 3｜SAP｜account tags 與 resource tags 的互補（選兩項）

每個 product 有獨立 AWS account，但 data platform 與 network accounts 由多個 products 共用。哪兩項成本歸屬設計合理？（選兩項）

A. 在 product accounts 使用 account tags，為帳號內 metered usage 提供穩定的高層 product/cost-center attribution
B. 使用 account tags 表示 business unit；shared account 內的產品成本依帳號總額平均分配
C. 在 shared accounts 使用 resource tags 或 service-specific usage data，並為無法直接標記的共享費用定義透明 allocation rule
D. 只使用 resource tags 分攤 shared account，business unit 與 legal entity 都由 Product tag 對照表推導
E. Shared accounts 依 payer account 的產品收入比例分攤，service-specific usage 僅在重大爭議時作 reconciliation evidence

**答案：A、C**

- **A：** 符合本題。當一個 account 對應一個產品時，account tag 能涵蓋較廣的 metered usage 與治理 metadata。
- **B：** Account tag 適合 product account 的高層歸屬；shared account 依總額平均分配與實際 network/data-platform consumption 無關。
- **C：** 符合本題。共享費用需要 resource/usage evidence 加上 finance-approved rule，並保留 raw 與 allocated views。
- **D：** Resource tags 可分攤可標記資源，business unit/legal entity 是不同治理維度，單靠 Product 對照表會丟失 account-level ownership 與不可標記費用。
- **E：** 平均分攤適合各 consumer 使用量相近且管理成本優先的服務；本題已有 service-specific usage，可用更能反映 consumption 的 driver。

**事實查證：** [Account tags for cost allocation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/account-tags-cost-allocation.html)、[Activate user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)

### 練習題 4｜SAP｜Data Exports CUR 2.0 與 downstream schema

Finance 有一套依賴 legacy CUR columns 的 Athena/BI pipeline，現在要採用 Data Exports CUR 2.0 並保留每日明細分析。最安全的 migration 是什麼？

A. 建立 CUR 2.0 export；直接讓既有 Athena views 指向新 tables，沿用既有 Athena schema；Audit trail 另標示「Data Exports CUR 2.0 與 downstream schema」的設定版本、生效時間與 exception expiry
B. Legacy CUR 維持財務帳務來源，CUR 2.0 獨立供新 BI 使用，兩套報表各由自己的 consumer 簽核；「Data Exports CUR 2.0 與 downstream schema」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 停止 legacy CUR export，讓 CUR 2.0 成為唯一來源；新舊 totals 以第一個完整 billing period 對帳；Export reconciliation 比較 legacy/CUR 2.0 columns、refresh time、row totals、cost totals 與 consumer sign-off，相關 alarms 與 rollback timestamp 納入 release evidence
D. 建立受控 S3 export 與 refresh/query pipeline，對照新舊 schema 與 reconciliation 結果，平行驗證 consumers 後再切換

**答案：D**

- **A：** CUR 2.0 export 與 Athena 是可部署組合；直接讓 legacy views 指向新 tables 假設 columns、refresh 與語意相同，會破壞既有 consumers。
- **B：** 兩套 pipeline 長期並存能隔離風險，卻沒有共同 reconciliation 與 retirement gate，Finance/BI 可能永久產生不同 totals。
- **C：** 停止 legacy 可立刻降低 storage 與雙跑成本；新 schema、cadence 和 payer totals 尚未平行證明時，切換會中斷財務可重現性。
- **D：** 符合本題。版本化 schema、parallel run 與 payer-bill reconciliation 能避免財務報表在切換時失真。

**事實查證：** [Migrate from legacy CUR to Data Exports CUR 2.0](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-migrate.html)、[AWS Billing and Cost Management](https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costmanagement.html)

### 練習題 5｜SAP｜showback 的 cost metric 語意

Finance 用 unblended cost 做月度 cash reconciliation，產品團隊則想看 Savings Plans upfront commitment 在使用期間攤提後的 consumption economics。哪個原則最重要？

A. 在報表上明確標示 unblended、amortized、net 或 effective cost 的用途，採一致 allocation rule 並與 payer bill reconciliation
B. Finance 與產品團隊共用 unblended cost，另用文字註記 upfront commitment 的消費期間
C. 產品報表只看 amortized cost，credits、refunds、fees 與 net discount 另由總帳處理
D. Showback 對各團隊發布單一 total-cost metric，shared-cost allocation rule 由 Finance 統一管理

**答案：A**

- **A：** 符合本題。Metric 必須對應問題並透明揭露，否則不同團隊會用同一數字表達不同概念。
- **B：** Unblended cost 適合 invoice/cash reconciliation；文字註記不能把 upfront commitment 正確攤到實際 consumption period，產品經濟性會失真。
- **C：** Amortized cost 適合看 commitment consumption；忽略 credits、refunds、fees 與 net discounts 時，不能與產品實際負擔或 payer bill 一致對帳。
- **D：** 單一 total-cost metric 容易溝通，Finance 規則無法同時回答 cash、commitment economics 與 net realized cost 等不同問題。

**事實查證：** [Cost Explorer advanced options and cost metrics](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-advanced.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 6｜SAP｜共享平台成本 allocation rule

TGW、central logging 與 data lake 的費用目前全部歸中央平台，consumer teams 看不到邊際成本。哪個 chargeback/showback 設計最健康？

A. Shared platform 依各團隊既有 AWS spend 比例分攤，request、storage 與 active-user drivers 只作 dashboard 參考
B. 依費用性質選直接、固定、比例或 usage-driver allocation，版本化規則、由 finance 批准，並同時保留 raw 與 allocated views
C. 使用單一 request-count driver 分攤 shared platform，allocated view 長期保存，raw CUR 保留 30 天
D. 將共享成本分攤進產品 KPI；季度結帳時驗證 driver 是否與實際消耗相關

**答案：B**

- **A：** 按既有 AWS spend 比例分攤簡單且穩定；TGW bytes、log volume 與 data-lake storage 的 cost drivers 不一定跟總 spend 成比例。
- **B：** 符合本題。Allocation 是 operating model，需要可解釋、可版本化、可核對且與費用 driver 相符。
- **C：** Request count 可合理分攤 request-driven service；central network、logging 與 data lake 同時受 bytes、retention、storage 和 queries 驅動，單一 driver 會交叉補貼。
- **D：** 把 shared cost 放入產品 KPI 有助 accountability；季度才驗證 driver，錯誤 allocation 會連續影響多期，且沒有保留 raw/reproducible rule。

**事實查證：** [Migrate from legacy CUR to Data Exports CUR 2.0](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-migrate.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 7｜SAP｜RI/Savings Plans sharing 與 benefit ownership

Central FinOps 購買 Savings Plans，discount benefits 由多個 accounts 消耗。產品團隊卻只看到 on-demand equivalent cost，不知道誰承擔 commitment risk。應如何治理？

A. 啟用 RI/Savings Plans sharing，將 benefit 全歸購買帳號，使用團隊只看 on-demand baseline；Audit trail 另標示「RI/Savings Plans sharing 與 benefit ownership」的設定版本、生效時間與 exception expiry
B. 關閉 sharing 讓每個帳號自行購買 commitment；採用較低 utilization 換取清楚 ownership
C. 定義哪些 accounts 可分享、commitment purchaser 與 consumption owner，追蹤 utilization/coverage，並一致分配 savings 與未使用 commitment cost
D. 由中央 FinOps 購買 organization-level commitment，benefit 依 on-demand equivalent usage 分配，unused cost 歸中央 reserve；Commitment report 顯示 purchaser、eligible accounts、utilization、coverage、benefit 與 unused-cost allocation，exception expiry 與最後一次驗收時間也被保留

**答案：C**

- **A：** Sharing discount 能提高 organization utilization；把所有 benefit 留給購買帳號，使用團隊只看 on-demand cost，會切斷 consumption 與 savings accountability。
- **B：** 關閉 sharing 可得到清楚的 account ownership，會降低 pooled utilization 並把 workload seasonality 風險分散成多份較小 commitment。
- **C：** 符合本題。Commitment ownership、benefit allocation 與 workload accountability 必須在同一 policy 中明確。
- **D：** Organization-level commitment 可先取得 discount；benefit owner 與 unused-cost allocation 只有利用率下降後才建立，財務激勵在購買時就不清楚。

**事實查證：** [RI and Savings Plans discount sharing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-turn-off.html)、[AWS Billing and Cost Management](https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costmanagement.html)

### 練習題 8｜SAP｜Budgets 的告警與即時控制邊界（選兩項）

Sandbox 每月預算是 5,000 美元。管理者希望 80% 時通知 owner，100% 時立即停止任何可能產生費用的 API。哪兩項說法正確？（選兩項）

A. 使用 Budgets actions 限制部分資源；將 delayed billing data 當成每個 request 的同步判斷
B. AWS Budgets data 與 alerts 有 billing processing latency，不能視為每次 API 前的同步 circuit breaker
C. 使用 service quotas 與 SCP 作即時 guardrails，Budget forecast 與 escalation 由 payer account 季度檢視
D. 可建立 actual/forecast thresholds、subscribers 與支援的 budget actions，並為 sandbox 另用 quotas、SCP/automation 或 service controls 限制即時風險
E. 對 production 設定 100% Budget action 停止支援資源，critical-workload exclusions 依 resource tags 套用

**答案：B、D**

- **A：** Budgets actions 可對支援資源或 IAM/SCP policy 採取動作；billing data 有延遲，不能在每個 API request 前同步判斷是否到達 100%。
- **B：** 符合本題。Cost data 不是 transactional request meter，急迫 control 要用適合的 technical guardrails。
- **C：** Quotas/SCP 可限制技術風險，Budgets forecast 與 escalation 若只季度檢視，無法達成 80% 即通知 owner 的營運需求。
- **D：** 符合本題。Budgets 適合財務 thresholds/actions；即時限制要結合 service quotas、permissions 或由服務流程化並評估安全性。
- **E：** Production stop action 在某些非關鍵資源可行；未先分類不可中止 workload 與測試 action scope，成本事件可能變成可用性事故。

**事實查證：** [Managing costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)

### 練習題 9｜SAP｜Cost Anomaly Detection 與 Budget threshold

一個產品平常每天花費 1,000 美元，週末降到 300 美元。某週末因錯誤 deployment 升到 900 美元，仍低於固定日上限 1,200 美元。哪個工具最能補足固定 threshold 的盲點？

A. 只使用固定 monthly Budget threshold；偵測低於預算但明顯偏離歷史模式的支出
B. 只使用 Cost Anomaly Detection 處理偏離，年度 commitment 與 forecast 留在外部財務試算表
C. 所有 anomaly monitors 發到同一個 organization SNS topic，使用預設 sensitivity 與共同值班 queue
D. 使用 Cost Anomaly Detection 依歷史模式偵測偏離，設定 monitor/subscriber 並由 owner 調查；Budgets 繼續處理計畫性門檻

**答案：D**

- **A：** 固定 Budget 適合監控計畫金額；900 美元低於 1,200 上限，這個機制本身不會辨識週末相對基線的異常。
- **B：** Cost Anomaly Detection 能找偏離模式，不能取代 commitment utilization、年度 forecast 與固定 budget governance；兩者回答不同問題。
- **C：** 共用 SNS queue 可以集中值班；不同 service/account 的基線、影響與 owner 不同，單一預設 sensitivity 容易產生噪音或漏報。
- **D：** 符合本題。它捕捉相對預期模式的偏離，和實際/forecast Budget threshold 互補。

**事實查證：** [Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html)、[Managing costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)

### 練習題 10｜SAP｜驗證 unit economics 而非只看總帳單

團隊把 EC2 batch 改為 Spot 與 queue，月帳單下降 20%，但該月交易量也下降 30%，失敗重試與 on-call time 增加。如何判斷是否真的優化？

A. 以代表期間比較每筆成功交易成本、成功率、latency、重試、data transfer、migration/dual-run 與 operational labor，確認 savings 未轉成風險
B. 比較改造前後總帳單；不以 requests、users 或資料量正規化需求變化
C. Unit economics 只計算基礎設施單價，retries、data transfer、dual-run 與 operational toil 歸中央 overhead；Unit-economics dataset 對齊成功交易數、latency、retry、transfer、labor、dual-run 與總成本，相關 alarms 與 rollback timestamp 納入 release evidence
D. 以新架構的 run-rate 與原月度帳單比較 savings，舊資源成本在 decommission workstream 中獨立追蹤

**答案：A**

- **A：** 符合本題。Normalized unit economics 與 guardrail metrics 才能判斷 architecture 改變是否真的創造價值。
- **B：** 總帳單下降同時受到交易量下降影響；沒有以成功交易、資料量或其他 demand unit 正規化，不能歸因於 Spot/queue 架構。
- **C：** 基礎設施單價是 unit economics 的一部分；retries、transfer、dual-run 和 on-call labor 都是為交付同一成功交易付出的成本。
- **D：** 舊資源仍運行時，run-rate savings 尚未落到 payer bill；先宣告節省會把 decommission 與 demand normalization 排除在 evidence 外。

**事實查證：** [AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Migrate from legacy CUR to Data Exports CUR 2.0](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-migrate.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Organizations consolidated billing配合cost allocation t…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「單一帳單無法回答哪個產品、環境或團隊消耗成本，也無法建立責任。」，所以「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」能直接滿足它；若constraint改成「Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」。替代方案「Showback先提高可見度，chargeback再將成本計入決策；兩者都需穩定taxonomy。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「單一帳單無法回答哪個產品、環境或團隊消耗成本，也無法建立責任。」，排除會導致「只靠資源Name tag，或共享平台成本全部歸中央而讓consumer看不到邊際成本。」的選項，再選「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」。本章對應的代表task包括：SAP-1.5 Determine cost optimization and visibility strategies；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.5 Identify opportunities for cost optimizations。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Organizations consolidated billing配合cost allocation tags、CUR、Budgets與account boundaries。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「cost allocation is an ownership model」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 86 章　Migration Assessment、Portfolio 與 Wave Planning

大型migration不是逐台server搬移；application dependency與business calendar決定風險。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：兩千台server需十八個月搬完，部分系統共享database與批次檔案。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：大型migration不是逐台server搬移；application dependency與business calendar決定風險。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS Migration Hub負責主要工作，AWS Application Discovery Service提醒我們答案不是永遠固定。本章會走向「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：兩千台server需十八個月搬完，部分系統共享database與批次檔案。

兩千台server inventory
      │
      ├─ 依business application重新分組
      ├─ 發現database、file、identity與network dependencies
      └─ 評估7R與business value
                 │
                 ▼
Wave 0：landing zone / network / identity
Wave 1：低風險且依賴少的applications
Wave 2：共享資料與中度相依applications
Wave N：核心、mainframe或需refactor的系統

每一wave都有owner、cutover、validation、rollback與退出機房條件。

失敗時先找：依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Migration Hub有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Migration Hub和AWS Application Discovery Service並不是兩個任意的產品名稱。前者適合本章，是因為「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」直接回應了眼前的問題；後者描述的「Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「migrate dependency groups, not asset lists」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 |
| AWS Application Discovery Service | 收集on-premises server inventory、utilization、process與network dependencies。 | Agentless collector或agent將資料送至Migration Hub，供right-size與wave planning。 |
| Migration Evaluator | 建立現有環境成本與AWS business case/TCO分析。 | Collector或inventory資料分析utilization、licensing與right-sizing，產生migration assessment。 |

## 把全圖套進一個具體案例

**場景：** 兩千台server需十八個月搬完，部分系統共享database與批次檔案。

1. 故事的起點：兩千台server需十八個月搬完，部分系統共享database與批次檔案。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Migration Hub負責「集中追蹤migration portfolio、waves與多工具進度。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：彙整discovery與migration tools狀態，提供application grouping與journey visibility。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Application Discovery Service、Migration Evaluator各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「它不搬資料本身；server用MGN、database用DMS、files用DataSync。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Migration Hub

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：大型migration不是逐台server搬移；application dependency與business calendar決定風險。
- **具體例子／邊界：** 在「兩千台server需十八個月搬完，部分系統共享database與批次檔案。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Application Discovery Service

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：migrate dependency groups, not asset lists。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### migration

把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

## 回到 AWS：Components、功用與責任邊界

### AWS Migration Hub

- **功用：** 集中追蹤migration portfolio、waves與多工具進度。
- **底層機制：** 彙整discovery與migration tools狀態，提供application grouping與journey visibility。
- **關鍵設定：** home Region、discovery sources、applications、waves、connectors與orchestrator templates。
- **選擇時機：** 大型migration需要single pane追蹤而不是spreadsheet碎片。
- **替換時機：** 它不搬資料本身；server用MGN、database用DMS、files用DataSync。

### AWS Application Discovery Service

- **功用：** 收集on-premises server inventory、utilization、process與network dependencies。
- **底層機制：** Agentless collector或agent將資料送至Migration Hub，供right-size與wave planning。
- **關鍵設定：** agent/agentless mode、data collection、export、network connections與application grouping。
- **選擇時機：** migration assessment、dependency mapping與portfolio sizing。
- **替換時機：** 只看CMDB可能過時；但自動發現仍需business owner驗證。

### Migration Evaluator

- **功用：** 建立現有環境成本與AWS business case/TCO分析。
- **底層機制：** Collector或inventory資料分析utilization、licensing與right-sizing，產生migration assessment。
- **關鍵設定：** inventory source、utilization window、license assumptions、target Regions與cost model。
- **選擇時機：** 需要財務批准、TCO與migration prioritization。
- **替換時機：** 它不是技術dependency map或實際migration engine。

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

### AWS Application Discovery Service：逐項設定說明

#### `agent/agentless mode`

- **控制什麼：** `agent/agentless mode`決定AWS Application Discovery Service收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。
- **何時需要：** 要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。
- **怎麼設定／驗證：** 選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。
- **常見錯法：** 樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。

#### `data collection`

- **控制什麼：** `data collection`決定AWS Application Discovery Service收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。
- **何時需要：** 要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。
- **怎麼設定／驗證：** 選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。
- **常見錯法：** 樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。

#### `export`

- **控制什麼：** `export`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「migration assessment、dependency mapping與portfolio sizing。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Application Discovery Service的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `network connections`

- **控制什麼：** `network connections`指定AWS Application Discovery Service讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `application grouping`

- **控制什麼：** `application grouping`定義AWS Application Discovery Service管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

### Migration Evaluator：逐項設定說明

#### `inventory source`

- **控制什麼：** `inventory source`指定Migration Evaluator讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `utilization window`

- **控制什麼：** `utilization window`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要財務批准、TCO與migration prioritization。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Migration Evaluator的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `license assumptions`

- **控制什麼：** `license assumptions`指定Migration Evaluator的工作生命週期、啟用狀態、network/domain整合或成本模型假設。
- **何時需要：** 服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。
- **怎麼設定／驗證：** 記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。
- **常見錯法：** Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。

#### `target Regions`

- **控制什麼：** `target Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Migration Evaluator前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `cost model`

- **控制什麼：** `cost model`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「需要財務批准、TCO與migration prioritization。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Migration Evaluator設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

## 讀到這裡，請用自己的話說一次

1. AWS Migration Hub的責任：集中追蹤migration portfolio、waves與多工具進度。
2. 底層機制：彙整discovery與migration tools狀態，提供application grouping與journey visibility。
3. 第一個要看的設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
4. 選擇邏輯：建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。
5. 不要混淆：AWS Application Discovery Service的責任是「收集on-premises server inventory、utilization、process與network dependencies。」；它不會自動取代AWS Migration Hub。
6. 替換訊號：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
7. 最常見錯法：依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。
8. 可移植原則：migrate dependency groups, not asset lists。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 | 大型migration需要single pane追蹤而不是spreadsheet碎片。 | 它不搬資料本身；server用MGN、database用DMS、files用DataSync。 |
| AWS Application Discovery Service | 收集on-premises server inventory、utilization、process與network dependencies。 | Agentless collector或agent將資料送至Migration Hub，供right-size與wave planning。 | migration assessment、dependency mapping與portfolio sizing。 | 只看CMDB可能過時；但自動發現仍需business owner驗證。 |
| Migration Evaluator | 建立現有環境成本與AWS business case/TCO分析。 | Collector或inventory資料分析utilization、licensing與right-sizing，產生migration assessment。 | 需要財務批准、TCO與migration prioritization。 | 它不是技術dependency map或實際migration engine。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。 | 只有當題目條件明確改變時才可能合理。 | 依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。」之間做選擇。
- 認得常考設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
- 對應官方tasks：SAP-4.1 Select existing workloads and processes for potential migration。

## 本章 10 題考題

### 練習題 1｜SAP｜2026 migration assessment service boundary

一家在 2026 年開始 migration 的新客戶準備盤點 2,000 台 servers。顧問只交付一份 host/IP 清單，並無視 owner、dependencies、licensing 與 Application Discovery Service 對新客戶的可用性變更。哪個方案較完整？

A. 使用 automated discovery inventory 並匯入 CMDB owner tags，application grouping 依主機命名與網路連線推導；「2026 migration assessment service boundary」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 既有 Application Discovery Service agent 與 Migration Hub inventory 作為新客戶的唯一 assessment system of record；「2026 migration assessment service boundary」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 依現行可用性使用 AWS Transform assessment workflows，並整合 CMDB、owner interviews、代表性 utilization、license、criticality、classification、dependencies 與 lifecycle evidence
D. 以 host inventory 與 utilization 產生第一版 waves，dependency mapping 與 target-readiness assessment 併入各 wave execution；Assessment record 關聯 host inventory、CMDB owner、utilization、license、criticality、data class 與 dependencies，exception expiry 與最後一次驗收時間也被保留

**答案：C**

- **A：** Automated inventory、CMDB owner tags 與 network grouping 可建立初版 portfolio；只依 host name/flow 推導 application boundary 會漏掉 license、criticality 與低頻 dependency。
- **B：** 既有客戶可依可用性邊界使用 Application Discovery Service；2026 新客戶把它當唯一入口，沒有符合題幹要求的 current workflow。
- **C：** 符合本題。Decision-grade inventory 必須同時有 current tooling、technical telemetry 與 business ownership。
- **D：** 先產生 wave plan適合已有高可信 inventory 的 program；此處 dependencies/target readiness 尚未形成 decision evidence，第一波會被拿來做 assessment。

**事實查證：** [AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)、[AWS Migration Hub availability for new customers](https://docs.aws.amazon.com/migrationhub/latest/ug/whatishub.html)、[AWS Application Discovery Service availability change](https://docs.aws.amazon.com/application-discovery/latest/userguide/application-discovery-service-availability-change.html)、[AWS services and capabilities moving to maintenance](https://aws.amazon.com/about-aws/whats-new/2025/10/aws-service-availability/)、[Phases of a large migration](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/phases.html)

### 練習題 2｜SAP｜以 dependency move group 排 migration wave

Migration PM 將每波固定為 50 台 servers。結果 payment app 與 shared database、Active Directory、DNS、SFTP partner 和月末 batch 被拆到不同 waves。應如何重新分組？

A. 每 wave 固定 50 台 servers，共用 database、DNS 與 identity 以 cross-wave exception catalog 和暫時 firewall rules 維持
B. 依 application owner 分 wave；共用 middleware 與 tightly coupled services 分散在不同日期
C. 宣布 cutover dates；以 discovery data 調整 move groups 與 shared-service capacity
D. 以能共同運作與切換的 application/dependency move groups 分波，納入 shared data、identity、DNS、files、schedules 與 external partners

**答案：D**

- **A：** 固定 50 台有利於 capacity planning，會切斷 database、DNS、identity 和 batch 等共同 cutover dependency，例外反而成為主流程。
- **B：** Application owner 是重要 ownership boundary；shared middleware 和 tightly coupled services 跨日期時，單一 owner 分組不能保證每波可獨立運作。
- **C：** 先公布日期再用 discovery 微調適合 dependency 已知的 portfolio；本題已出現核心服務被拆開，應先建立 move groups 再承諾 dates。
- **D：** 符合本題。Wave 是可切換的 business/technical dependency unit，不是任意 asset batch。

**事實查證：** [Application Discovery Service Agentless Collector dashboard](https://docs.aws.amazon.com/application-discovery/latest/userguide/agentless-collector-dashboard.html)、[Build a migration plan in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 3｜SAP｜驗證 discovery dependency evidence（選兩項）

Discovery telemetry 顯示 ERP 與 payroll 沒有互連，因此團隊打算分開切換。Owner 說兩者只在每月最後一晚透過 encrypted file exchange 同步。哪兩項作法最合理？（選兩項）

A. 只觀察一個低流量工作日；涵蓋 month-end、batch 與 disaster-recovery traffic
B. 只依 application interviews 建 dependency map，不用 network/process telemetry 交叉驗證
C. 將 discovery window 擴到代表性 business cycles，結合 process/network evidence、owner interviews 與 architecture records
D. 在 cutover rehearsal 中觀察 DNS、identity、files、batch schedules 與 external endpoints，更新 dependency confidence
E. 固定 ERP 與 payroll 為不同 waves，rehearsal 發現的新 file/firewall flows 由 coexistence bridge 跨 wave 承接

**答案：C、D**

- **A：** 低流量工作日能看常態 interactive flow，無法觀察 month-end encrypted file exchange；telemetry window 必須涵蓋實際 business cycle。
- **B：** Owner interview 能揭露加密、離線與商業語意；只靠訪談容易漏掉實際 process/network behavior，需要 records 與 telemetry 交叉驗證。
- **C：** 符合本題。代表性時間與多來源證據可降低週期性、加密或低頻 dependency 被漏掉的風險。
- **D：** 符合本題。Rehearsal 能驗證 discovery/訪談中的假設並暴露實際 cutover path。
- **E：** 固定 scope 可保護計畫穩定；若 rehearsal 發現新 dependency 仍不回饋 wave design，cutover 會保留已知的 firewall/DNS 風險。

**事實查證：** [Application Discovery Service Agentless Collector dashboard](https://docs.aws.amazon.com/application-discovery/latest/userguide/agentless-collector-dashboard.html)、[Build a migration plan in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

### 練習題 4｜SAP｜migration business case assumptions

管理層用 on-prem hardware 折舊與同規格 EC2 list price 做比較，宣稱所有 workload 一年內節省 60%。分析沒有 rightsizing、license、dual-run、transfer、migration labor 或 operational change。應如何改善？

A. 建立多個 target scenarios，納入 representative utilization/right-sizing、license、migration/dual-run/transfer、support model、risk 與 business outcomes，並保留可事後驗證的 assumptions
B. business case 只比較 EC2 與現有 server 單價，不含 licenses、labor、dual-run 與 risk；「migration business case assumptions」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 直接採 vendor 建議的 rightsizing；使用代表性 utilization 與 growth assumptions
D. 依 EC2 rightsizing estimate 取得 migration funding，exit、transfer、dual-run 與 outcome costs 納入 execution budget baseline；Business-case workbook 保存 utilization period、rightsizing、license、transfer、dual-run、labor 與 risk assumptions，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。完整模型比較多個可行 architecture/operating scenarios，而不是簡單 VM price mapping。
- **B：** 同規格 EC2 與 server 單價可作粗略上限；licenses、labor、dual-run、transfer 和 risk 都會改變總成本與現金流。
- **C：** Vendor rightsizing recommendation 可作一個 scenario；沒有 workload utilization、growth、license 與 architecture constraints，不能直接當完整 business case。
- **D：** 先取得 funding 再細化 execution cost 適合探索性 program；題目已用 60% savings 作承諾，exit/transfer/outcome assumptions 必須在決策前可見。

**事實查證：** [AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 5｜SAP｜以 prerequisites 與 learning value 安排 waves

公司尚未完成 landing zone、hybrid DNS、identity、monitoring 與 on-call model，卻打算先搬最關鍵的 revenue application 來『逼平台成熟』。哪個 sequencing 更合理？

A. 第一波選最關鍵 revenue system，以便快速證明 migration value，平台 prerequisites 同步處理；「以 prerequisites 與 learning value 安排 waves」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 建立必要 platform prerequisites，以代表性低風險 workload 驗證 factory，再逐步提高 dependency/criticality 並避開 business blackout
C. 第一波選擇 stateless public web tier，驗證 account vending、deployment 與 monitoring factory；Release evidence 另關聯「以 prerequisites 與 learning value 安排 waves」的 pilot wave、result 與 rollback timestamp
D. 先依 business unit 排定完整 portfolio dates，landing zone、identity、logging 與 network 由中央平台平行交付；Wave-readiness board 分別顯示 landing zone、identity、DNS、network、monitoring、on-call 與 blackout status，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** 關鍵 revenue system 能快速證明價值，也會同時測試未成熟的 identity、DNS、monitoring 與 on-call，第一波失敗具有最大 business impact。
- **B：** 符合本題。Early waves 應建立可重複能力與 evidence，而不是拿最大 business risk 當實驗。
- **C：** Stateless web tier 是良好早期 candidate；若它不使用 hybrid DNS、identity 或資料依賴，可能只驗證部分 factory，不能單獨證明關鍵 workload readiness。
- **D：** 依 business unit 排日期便於 portfolio 溝通；landing zone/network 等 prerequisites 與 migration 平行到最後，wave 可能在 cutover 才被共同平台阻擋。

**事實查證：** [Phases of a large migration](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/phases.html)、[Migration playbook for AWS large migrations](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-migration-playbook/)

### 練習題 6｜SAP｜migration wave entry/exit criteria

Wave dashboard 把『MGN replication 已開始』標成 complete，但 target security review、rollback、support training 與 business validation 都未完成。正確的 completion 定義是什麼？

A. wave exit 若求 instances running，business acceptance、monitoring 與 rollback 依各 workload 的 local runbook 管理
B. MGN/DMS 顯示 completed 即關閉 migration task；DNS、security、backup 與 support readiness 由 post-cutover acceptance checklist 管理
C. Entry/exit criteria 應涵蓋 inventory、target design、security、test/cutover/rollback、capacity、owner/support readiness 與 post-cutover business acceptance
D. 關閉 source 以避免雙重成本，再執行 target business transaction 與 rollback tests

**答案：C**

- **A：** Instances running 可作工具層里程碑；business acceptance、monitoring、rollback 和 support 仍未成為統一 exit gate，program 會把不可營運 workload 算完成。
- **B：** Migration tool completed 能證明複寫/launch 狀態；DNS、security、backup 和 support verification 若不是必須通過的 criteria，dashboard 仍會過早結案。
- **C：** 符合本題。Wave completion 是由可營運與 owner acceptance 定義，不是單一 tool status。
- **D：** 關閉 source 可消除雙寫與成本，應在 target transaction、rollback 和 owner acceptance 已通過後執行，而不是拿 decommission 當驗收起點。

**事實查證：** [Build a migration plan in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)、[Migration playbook for AWS large migrations](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-migration-playbook/)

### 練習題 7｜SAP｜online 與 physical data transfer 決策

新客戶要在三週內搬移 600 TB file archive，現有 link 只能穩定提供 500 Mbps，資料每天仍增加 2 TB。哪個決策流程最正確？

A. 使用 DataSync 建立 20 個 parallel tasks，完成時間依 task concurrency 加總估算，來源 link 維持 500 Mbps
B. 採用 Data Transfer Terminal 搬初始資料；規劃每日 2 TB delta 的最終同步與驗證
C. 預訂 Data Transfer Terminal 或合作夥伴實體轉移窗口，使用標準 encryption 與 chain-of-custody profile，target ingest 採服務額定 throughput
D. 以 volume、daily change、有效頻寬與驗證時間計算是否能收斂；線上路徑可用 DataSync，需實體搬運時評估當前可用的 Data Transfer Terminal 或合作夥伴方案

**答案：D**

- **A：** 增加 DataSync tasks 可提高並行處理，但 aggregate throughput 仍受 500 Mbps link 限制；600 TB 加每日 2 TB 無法用 task 數量線性縮短。
- **B：** Data Transfer Terminal 可處理大型初始 transfer，且 delta sync 思路正確；仍需先計算 ingest、驗證、預約與每日變更能否在三週窗口收斂。
- **C：** 實體轉移適合頻寬不足的 bulk data；來源介面、encryption、chain of custody 與 target ingest 必須是選型前條件，不能只靠交付窗口。
- **D：** 符合本題。500 Mbps 無法僅靠服務名稱保證三週完成 600 TB 加每日增量。應量化傳輸與驗證窗口；新客戶不可把 Snowball Edge 當預設，需評估現行 physical transfer options。

**事實查證：** [AWS DataSync network requirements](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)、[Snowball Edge availability change](https://docs.aws.amazon.com/snowball/latest/developer-guide/snowball-edge-availability-change.html)、[AWS Data Transfer Terminal](https://docs.aws.amazon.com/datatransferterminal/latest/userguide/what-is-dtt.html)

### 練習題 8｜SAP｜migration coexistence 的 hybrid network/DNS（選兩項）

十八個月 migration 期間，一半 applications 在資料中心、一半在 AWS，且雙方互相呼叫。哪兩個架構行動最重要？（選兩項）

A. 建立具故障域冗餘的 DX/VPN、BGP/routes/MTU/capacity 方案，並避免 bulk migration traffic 壓垮 production
B. 建立雙 DX 連線與 BGP failover；hybrid DNS 仍靠手工 hosts files 管理
C. 部署 Resolver endpoints 與 conditional forwarding，network path 只保留單一 circuit
D. 讓 production applications 跨環境互調，再演練 circuit、route、resolver 與 dependency failure
E. 部署跨 AZ Route 53 Resolver inbound/outbound endpoints 與 conditional rules，並演練 circuit、route、DNS 與 resolver failure

**答案：A、E**

- **A：** 符合本題。Hybrid data path 需有容量隔離、routing 與實際 failover evidence。
- **B：** 雙 DX/BGP 可提升 network resiliency；hosts files 無法可靠管理十八個月的雙向 service discovery、TTL 與 endpoint 變更。
- **C：** Resolver endpoints/forwarding 解決 hybrid DNS；單一 network circuit 仍讓所有跨環境 calls 共用一個故障點。
- **D：** Production traffic 能驗證真實 dependency，直接以正式 workload 作第一次 circuit/resolver failure test 會把未知 blast radius 放到客戶路徑。
- **E：** 符合本題。雙向 DNS 與 network failure handling 應一起設計並跨故障域部署。

**事實查證：** [Resilience in AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/disaster-recovery-resiliency.html)、[What is Route 53 VPC Resolver?](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)、[Resolving DNS queries between VPCs and on-premises networks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-DSN-queries-to-vpc.html)、[Verify DataSync agent connections](https://docs.aws.amazon.com/datasync/latest/userguide/test-agent-connections.html)

### 練習題 9｜SAP｜DataSync 與 Storage Gateway 的責任差異

情境 A 是把 on-prem NFS 內容一次搬到 S3，並在 cutover 前每天同步 delta；情境 B 是工廠應用未來兩年仍需使用本地 file/volume/tape interface，但後端資料要整合 AWS storage。應如何選擇？

A. A 使用 DataSync 做受控 transfer/sync；B 使用適合介面的 Storage Gateway，並分別設計 cache、network 與 recovery
B. 使用 DataSync 做一次性 NFS 搬移，卻讓應用長期依賴該 task 作為 on-premises file interface；Storage migration dashboard 區分 initial copy、delta sync、cache hit、local interface、network 與 recovery status，具名 owner 與 approver 依固定 cadence 複核
C. 使用 Storage Gateway 維持 hybrid file access；Release evidence 另關聯「DataSync 與 Storage Gateway 的責任差異」的 pilot wave、result 與 rollback timestamp
D. 先以 read-only consumers 切到 target storage，agent connectivity、permissions 與 delta sync 由同一 cutover window 驗收

**答案：A**

- **A：** 符合本題。DataSync 處理 online file/object movement；Storage Gateway 維持 hybrid storage interface。
- **B：** DataSync 很適合一次搬移與 delta sync，不提供應用長期掛載的 on-prem file/volume/tape interface；B 需要 Storage Gateway 類 contract。
- **C：** Storage Gateway 能維持 hybrid file access；讓應用自行複製 20 TB migration data 會失去 DataSync 的 transfer scheduling、verification 與 throughput controls。
- **D：** 先切 target 再測 agent、permissions 與 delta 適合可快速 rollback 的非關鍵 workload；題目要求受控 migration，這些應在 cutover gate 前完成。

**事實查證：** [AWS DataSync network requirements](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)、[What is AWS Storage Gateway?](https://docs.aws.amazon.com/storagegateway/latest/userguide/WhatIsStorageGateway.html)

### 練習題 10｜SAP｜migration factory throughput 與 ownership

Migration factory 同時開 30 個 waves，所有例外都等 chief architect 批准。WIP 增加但每月完成量下降，重複 defects 不斷出現。哪個 operating model 最能改善？

A. 增加每波 workload 數量提高 utilization；WIP 由各 wave owner 管理 WIP 或分析 queue wait time
B. 建立可重複 playbooks/automation，分派 wave/application/platform owners，限制 WIP，追蹤 blocker、escaped defects 與 cycle time，將 lessons 回饋後續 waves
C. 建立中央 migration team 處理每個 exception，workload owners 不承擔測試與 acceptance
D. 複製更多 playbooks；由重工與等待時間判斷哪些步驟其實需要自動化

**答案：B**

- **A：** 提高每波 workload 數可增加局部人員利用率，30 個同時 waves 已造成 queueing；更多 WIP 會拉長 cycle time 並隱藏 blocker。
- **B：** 符合本題。Factory 的目標是可預測地交付可營運 applications，需以 flow、quality 與 ownership 管理。
- **C：** 中央 team 處理例外可維持標準一致；workload owners 不負責 test/acceptance 時，technical completion 與 business readiness 會脫節。
- **D：** 複製 playbooks 可快速擴編；沒有先限制 WIP、指派 decision owner 和消除重工原因，只會把相同 defect 複製到更多 waves。

**事實查證：** [Migration playbook for AWS large migrations](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-migration-playbook/)、[Build a migration plan in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「建立inventory、dependency map、business case與wave plan，先搬…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「大型migration不是逐台server搬移；application dependency與business calendar決定風險。」，所以「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」能直接滿足它；若constraint改成「Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」。替代方案「Application Discovery Service提供資料，但owner訪談與實際traffic仍需交叉驗證。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「大型migration不是逐台server搬移；application dependency與business calendar決定風險。」，排除會導致「依server數量排wave，拆開強耦合應用，cutover後才發現隱藏dependency。」的選項，再選「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」。本章對應的代表task包括：SAP-4.1 Select existing workloads and processes for potential migration。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「建立inventory、dependency map、business case與wave plan，先搬低風險並建立migration factory。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「migrate dependency groups, not asset lists」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 87 章　Application Migration Service、DMS 與 SCT

Server、database engine與schema/code conversion需要不同migration工具。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：Oracle應用先rehost EC2，database改Aurora PostgreSQL並要求短停機。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：Server、database engine與schema/code conversion需要不同migration工具。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Application Migration Service，對照角色是AWS DMS。我們選擇「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Oracle應用先rehost EC2，database改Aurora PostgreSQL並要求短停機。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Application Migration Service]
          │ 把physical、virtual或cloud servers以block replication搬到EC2。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS DMS：在線搬移或持續複寫databases/data stores，降低downtime。
  · AWS Schema Conversion Tool：評估並轉換異質database schema與部分code objects。

失敗時先找：只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Application Migration Service有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Application Migration Service和AWS DMS並不是兩個任意的產品名稱。前者適合本章，是因為「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」直接回應了眼前的問題；後者描述的「DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate compute replication, data movement, and semantic conversion」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 |
| AWS DMS | 在線搬移或持續複寫databases/data stores，降低downtime。 | Replication instance/serverless task做full load與CDC，讀source logs並寫target。 |
| AWS Schema Conversion Tool | 評估並轉換異質database schema與部分code objects。 | 讀取source metadata，產生assessment report與target DDL；無法自動轉換項目需人工處理。 |

## 把全圖套進一個具體案例

**場景：** Oracle應用先rehost EC2，database改Aurora PostgreSQL並要求短停機。

1. 故事的起點：Oracle應用先rehost EC2，database改Aurora PostgreSQL並要求短停機。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Application Migration Service負責「把physical、virtual或cloud servers以block replication搬到EC2。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS DMS、AWS Schema Conversion Tool各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Application Migration Service

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Server、database engine與schema/code conversion需要不同migration工具。
- **具體例子／邊界：** 在「Oracle應用先rehost EC2，database改Aurora PostgreSQL並要求短停機。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS DMS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate compute replication, data movement, and semantic conversion。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### migration

把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。

### refactor

重構application與data boundaries以使用cloud-native架構；潛在收益高，時間、風險與testing需求也最高。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### rehost

盡量不改application，把server搬到cloud IaaS；速度快但保留多數技術債與營運模式。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

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

### AWS Schema Conversion Tool

- **功用：** 評估並轉換異質database schema與部分code objects。
- **底層機制：** 讀取source metadata，產生assessment report與target DDL；無法自動轉換項目需人工處理。
- **關鍵設定：** source/target engine、assessment report、conversion rules、extension pack與action items。
- **選擇時機：** Oracle/SQL Server等轉PostgreSQL/Aurora或warehouse migration。
- **替換時機：** 實際資料full load/CDC用DMS；同engine migration可能不需SCT。

## 考前與實作時再查：設定操作手冊

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

### AWS Schema Conversion Tool：逐項設定說明

#### `source/target engine`

- **控制什麼：** `source/target engine`指定AWS Schema Conversion Tool讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `assessment report`

- **控制什麼：** `assessment report`定義AWS Schema Conversion Tool用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `conversion rules`

- **控制什麼：** `conversion rules`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「Oracle/SQL Server等轉PostgreSQL/Aurora或warehouse migration。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Schema Conversion Tool鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `extension pack`

- **控制什麼：** `extension pack`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。
- **何時需要：** Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。
- **怎麼設定／驗證：** 設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。
- **常見錯法：** Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。

#### `action items`

- **控制什麼：** `action items`定義AWS Schema Conversion Tool用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

## 讀到這裡，請用自己的話說一次

1. AWS Application Migration Service的責任：把physical、virtual或cloud servers以block replication搬到EC2。
2. 底層機制：Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。
3. 第一個要看的設定：replication template、staging subnet、launch template、post-launch actions、test/cutover與lag。
4. 選擇邏輯：MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。
5. 不要混淆：AWS DMS的責任是「在線搬移或持續複寫databases/data stores，降低downtime。」；它不會自動取代AWS Application Migration Service。
6. 替換訊號：database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。
7. 最常見錯法：只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。
8. 可移植原則：separate compute replication, data movement, and semantic conversion。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 | rehost大量servers、低downtime cutover與DR-like migration。 | database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。 |
| AWS DMS | 在線搬移或持續複寫databases/data stores，降低downtime。 | Replication instance/serverless task做full load與CDC，讀source logs並寫target。 | homogeneous/heterogeneous database migration與ongoing replication。 | schema/code conversion使用SCT；一般files用DataSync；DMS不自動修正所有data types。 |
| AWS Schema Conversion Tool | 評估並轉換異質database schema與部分code objects。 | 讀取source metadata，產生assessment report與target DDL；無法自動轉換項目需人工處理。 | Oracle/SQL Server等轉PostgreSQL/Aurora或warehouse migration。 | 實際資料full load/CDC用DMS；同engine migration可能不需SCT。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。 | 只有當題目條件明確改變時才可能合理。 | 只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。」之間做選擇。
- 認得常考設定：replication template、staging subnet、launch template、post-launch actions、test/cutover與lag。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。
- 對應官方tasks：SAP-4.2 Determine the optimal migration approach for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAP｜MGN、DMS、schema conversion、DataSync 分工

公司要把一台 Oracle application server rehost 到 EC2、把 Oracle database 改成 Aurora PostgreSQL，並把 20 TB NFS reports 搬到 S3。哪個工具分工最合理？

A. MGN rehost application server、DMS 搬資料；Audit trail 另標示「MGN、DMS、schema conversion、DataSync 分工」的設定版本、生效時間與 exception expiry；「MGN、DMS、schema conversion、DataSync 分工」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 使用 MGN 搬 server 與 database host，Oracle 到 PostgreSQL 的 semantic conversion 交給 application startup；Migration asset map 分別標示 server blocks、database data/CDC、schema objects/code 與 NFS file scope，具名 owner 與 approver 依固定 cadence 複核
C. 以 legacy SCT 作新專案唯一 conversion path
D. MGN 以 block replication rehost server；DMS 搬 database data/CDC；新專案優先以 DMS Schema Conversion 處理異質 schema/code，SCT 僅保留既有 workflow；DataSync 搬 NFS files

**答案：D**

- **A：** MGN rehost server、DMS 搬資料的分工正確；Oracle schema、PL/SQL 與 datatype conversion 不能留給 cutover runbook，必須在資料遷移前完成並驗證。
- **B：** MGN 可 block-replicate database host 到 EC2，這是同平台 rehost；application startup 不會把 Oracle semantics 自動轉成 Aurora PostgreSQL。
- **C：** SCT 可支援既有 legacy workflow；2026 新專案應先評估 DMS Schema Conversion 的現行能力，不能把 SCT 當唯一預設路徑。
- **D：** 符合本題。四種工具處理不同資產。2026 新評估應優先使用 DMS Schema Conversion；SCT 可作既有客戶或既有流程的 legacy 選項，而不是新方案的等價預設。

**事實查證：** [AWS Application Migration Service rehost mechanism](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-database-rehost-tools/mgn.html)、[AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_SchemaConversion.html)、[AWS DataSync network requirements](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)

### 練習題 2｜SAP｜MGN staging network 與 replication capacity

MGN agents 已安裝，但 replication backlog 在白天持續增加；staging subnet 很小，egress path 與 production batch 共用，security policy 也封鎖部分必要連線。應先如何處理？

A. 規劃 staging subnet、replication resources、routes/endpoints、permissions 與 bandwidth，監控 lag，並避免 migration traffic 與 production 關鍵流量爭用
B. 只增加 source bandwidth，staging subnet、replication servers、permissions 與 target quotas 維持原狀；Replication dashboard 保存 source change rate、backlog、staging capacity、network throughput 與 blocked connections，具名 owner 與 approver 依固定 cadence 複核
C. 持續放大 replication server instance，容量判斷只採 CloudWatch CPU 與 disk queue metrics；「MGN staging network 與 replication capacity」的 change record 另保存 scope、owner、approver 與 rollback trigger
D. 固定 cutover 日期，staging subnet、replication server size 與 bandwidth 使用 MGN 預設配置；「MGN staging network 與 replication capacity」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：A**

- **A：** 符合本題。MGN replication 仍依賴 network、staging capacity、permissions 與 production-friendly traffic planning。
- **B：** 增加 source bandwidth 只改善一段路徑；staging subnet、replication resources、blocked egress 和 target quota 仍可限制吞吐。
- **C：** 放大 replication server 適合 compute/memory 已證實是 bottleneck 的情境；CPU/disk metrics 不能排除 network、permissions 與 source change rate。
- **D：** MGN defaults 可作小規模起點；固定 cutover date 且不按 backlog/throughput 調整 staging capacity，不能保證白天 lag 收斂。

**事實查證：** [What is AWS Transform MGN?](https://docs.aws.amazon.com/mgn/latest/ug/)

### 練習題 3｜SAP｜MGN test launch 與 application acceptance（選兩項）

一組來源 servers 已穩定 replication。團隊想直接安排 production cutover，因為一次 MGN test instance 成功開機。哪兩個步驟仍應在 cutover 前完成？（選兩項）

A. 在隔離且具代表性的 target network 做 test launch，驗證 OS、application、identity、DNS、dependencies 與 business transactions
B. Test instance 能開機後即視為通過，identity、DNS、external dependencies 由 production readiness gate 管理
C. Application owner 接受 test launch 結果；launch settings 與 post-launch actions 記錄在 change ticket
D. 在 boot test 通過後 finalize testing 以鎖定 lifecycle，owner acceptance 與 dependency findings 併入 production cutover approval
E. 修正 launch settings、post-launch actions 與 discovered dependencies，讓 owner 正式接受測試結果後再 finalize testing

**答案：A、E**

- **A：** 符合本題。Boot success 只驗證 compute 的一部分；test launch 的價值在於暴露完整 target behavior。
- **B：** Test instance 能開機證明 boot 與部分 driver 正常；identity、DNS、dependencies 和 business transaction 才決定 application 可否接管。
- **C：** Owner acceptance 與記錄 launch settings 都是必要治理；若沒有在代表 target network 執行完整 test，簽核只覆蓋有限 evidence。
- **D：** Finalize testing 會推進 migration lifecycle；test findings、launch settings 與 owner acceptance 應先收斂，否則會把已知問題帶入 cutover。
- **E：** 符合本題。Test findings 必須回到 launch/configuration/playbook，並由 application owner 驗收。

**事實查證：** [AWS Application Migration Service test and cutover](https://docs.aws.amazon.com/mgn/latest/ug/server-test-cutover-main.html)、[AWS Application Migration Service rehost mechanism](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-database-rehost-tools/mgn.html)

### 練習題 4｜SAP｜MGN cutover、source fencing 與 finalization

Cutover 後，舊機房 server 與新 EC2 instance 都曾接受訂單寫入，兩側資料已出現 divergence。團隊想立即 finalize MGN 並刪除 source。最佳處理順序是什麼？

A. 選 source 為 authoritative 並重新 cutover，target-only orders 匯出到 S3 供月末財務 reconciliation；Divergence ledger 逐 business key 記錄 source-only、target-only、conflicting writes、authority 與 resolution，設定版本與生效時間一併寫入 change record
B. 停止雙寫並選定 authoritative side，盤點 source/target divergence，依 business keys reconcile 或補償資料；確認單一寫入權威後，再決定完成 cutover 或 rollback，最後才 finalize/decommission
C. 選 target 為 authoritative 並關閉 source，source-only orders 保留在舊資料庫供月末 reconciliation
D. finalize MGN 與刪除 source 降低成本；由 logs 重建兩側 divergence

**答案：B**

- **A：** 選 source 為 authority 可能是正確 business 決策；直接重新 cutover 會以 source block state 建立新 target，target-only orders 必須先逐筆 reconcile，不能只留到月結。
- **B：** 符合本題。MGN 是單向 block replication，不會合併 target-side writes。Split-brain 發生後，首要工作是停止新增 divergence、選定權威並進行應用層 reconciliation；重新 launch cutover instance 可能覆蓋或遺失 target writes。
- **C：** 選 target 為 authority 也可能成立；立即關閉 source 而只保留舊庫待月結，會讓 source-only orders 在 production truth 中遺失。
- **D：** Finalize/decommission 適合單一 writer 已確認且 reconciliation 完成後；logs 通常不足以完整重建兩側 committed business state。

**事實查證：** [AWS Application Migration Service rehost mechanism](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-database-rehost-tools/mgn.html)、[AWS Application Migration Service test and cutover](https://docs.aws.amazon.com/mgn/latest/ug/server-test-cutover-main.html)

### 練習題 5｜SAP｜DMS full load、CDC 與 full load + CDC

一個 8 TB MySQL database 必須在 migration 的兩週內持續接受 writes，cutover downtime 不超過 15 分鐘。Target schema 已準備完成。應選哪種 DMS task strategy？

A. 使用 full-load-only DMS task，cutover window 內停止 source writes 15 分鐘並切換 endpoint；DMS task report 顯示 full-load progress、CDC position、source-log retention、lag、errors 與 cutover threshold，設定版本與生效時間一併寫入 change record
B. 只啟用 CDC，不載入既有歷史 rows，期待 transaction logs 重建完整 database
C. 使用 full load + CDC，確認 source logging/retention、endpoints、mappings 與 task capacity，使 CDC 在 cutover 前追上
D. 使用 full load + CDC；cutover 以 replication task 的 running 狀態和預設 latency threshold 作為 source-fencing trigger

**答案：C**

- **A：** Full-load-only 適合可在整個載入期間停止寫入或可重建增量的資料庫；8 TB 持續寫入且 downtime 15 分鐘時，歷史 load 期間的 changes 會缺失。
- **B：** CDC 可從 log position 持續複寫 changes，不會憑空建立開始位置之前的 8 TB baseline；需要 full load 或既有完整 target。
- **C：** 符合本題。Full load 建 baseline，CDC 持續同步，cutover 只需 fence writes 並等待 lag 收斂。
- **D：** Full load + CDC 是正確策略；lag threshold 與 source fencing 到 production cutover 才決定，無法事先證明 15 分鐘窗口可達成。

**事實查證：** [AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)

### 練習題 6｜SAP｜DMS homogeneous migration 與 conventional task

團隊要從 self-managed PostgreSQL 遷移到支援的 PostgreSQL target，希望評估 DMS homogeneous data migration；另一個 workload 要 Oracle 轉 PostgreSQL。哪個判斷正確？

A. 同 engine migration 也執行完整異質 schema rewrite，增加變更面但不改善相容性；Audit trail 另標示「DMS homogeneous migration 與 conventional task」的設定版本、生效時間與 exception expiry
B. 異質 engine 只建立 conventional DMS task；Release evidence 另關聯「DMS homogeneous migration 與 conventional task」的 pilot wave、result 與 rollback timestamp
C. 先建立 DMS replication task，依 target error 類型選擇 homogeneous data migration 或 conventional heterogeneous workflow；Support assessment 保存 source/target engine、object support、schema responsibility、downtime 與 recovery method，相關 alarms 與 rollback timestamp 納入 release evidence
D. Homogeneous migration 適用支援的 same-engine path；異質 engine 仍需 schema conversion 與適合的 DMS/native workflow，且兩者都要驗證 object support 與 recovery

**答案：D**

- **A：** Same-engine migration 通常可保留更多 schema semantics；強制做異質 rewrite 增加變更與測試面，沒有對應題目的需求。
- **B：** Conventional DMS task 可搬異質資料；schema、stored code 與 datatype conversion 不是 task 自動處理，必須在 target objects 與 validation 計畫中先完成。
- **C：** Replication error 可暴露 support gap，但 homogeneous/heterogeneous 是 source-target engine contract，應在建立 workflow 前判定。
- **D：** 符合本題。Same-engine 與 cross-engine 的 semantic problem 不同，應依 support matrix、secondary objects、downtime 與 validation 選 method。

**事實查證：** [DMS homogeneous data migrations](https://docs.aws.amazon.com/dms/latest/userguide/data-migrations.html)、[AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)

### 練習題 7｜SAP｜異質 schema/code conversion 與 action items

Oracle 到 Aurora PostgreSQL 的 assessment 顯示 tables/indexes 多數可轉換，但大量 PL/SQL packages 與 proprietary functions 需要 action items。最佳執行方式是什麼？

A. 新專案使用 DMS Schema Conversion 轉換受支援 objects，逐項處理 manual action items，再以 application SQL、stored code、資料型別與行為測試驗證；SCT 僅作既有 legacy workflow
B. 使用 DMS Schema Conversion 建立可自動轉換的 target objects，manual action items 統一納入 application UAT backlog
C. 保留既有 SCT workflow；比較 DMS Schema Conversion 對新專案的現行支援與限制
D. 部署轉換後 DDL，再以 production traffic 找出 PL/SQL semantic 與 performance 差異

**答案：A**

- **A：** 符合本題。自動轉換只能處理受支援語意；團隊仍要修正 action items 並以 workload 驗證。AWS 對新工作流優先建議 DMS Schema Conversion，SCT 應清楚標示 legacy。
- **B：** DMS Schema Conversion 建立受支援 objects 是第一步；manual action items 往往涉及 PL/SQL/business semantics，不能全部交給一般 UAT 才發現。
- **C：** 既有 SCT workflow 可以繼續維護；對新專案只做工具比較而沒有執行 conversion、action items 與 workload tests，尚未完成 migration 方法。
- **D：** Production traffic 能找到真實差異，直接用它驗證未處理的 stored code 與 performance 會把 conversion defect 暴露給正式交易。

**事實查證：** [DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_SchemaConversion.html)、[AWS SCT assessment report](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)

### 練習題 8｜SAP｜DMS mappings、LOB 與 replication capacity（選兩項）

DMS full load 經常因大量 LOBs、過寬 wildcard table mappings 與 replication instance memory pressure 失敗。哪兩個調整最合理？（選兩項）

A. 使用 limited LOB mode，limit 依 schema 宣告長度設定，task success 作為 LOB 完整性指標
B. 盤點 LOB 大小與完整性需求，選擇適當 limited/full LOB mode、limits 與 parallel-load settings，並用代表資料測試
C. 將 table selection/transform rules 限定在核准 scope，依 source/target throughput 與 task metrics 調整 capacity，並測 restart/recovery
D. 使用精確 table mappings，依 table count 將 tasks 分散到多個較小 replication instances
E. 把 wildcard 與 unlimited LOB 設定投入 full load；由 OOM/retry 指標調整 task settings

**答案：B、C**

- **A：** Limited LOB mode 可提高效能；schema declared length 不一定代表實際 LOB distribution，task success 也不能證明超過 limit 的內容完整。
- **B：** 符合本題。LOB strategy 應由實際 distribution 與 business requirement 驅動。
- **C：** 符合本題。Explicit scope、metrics-based capacity 與 restart test 能降低 migration surprise。
- **D：** 精確 mappings 與拆 task 都是可行調校；只按 table count 分配到更小 instances，沒有考慮 LOB size、hot tables、source/target throughput 和 memory pressure。
- **E：** Wildcard 與 full/unlimited LOB 可追求完整 scope；在已知 memory pressure 下用 OOM/retry 當調校訊號，會讓 full load 反覆失敗且難以預估。

**事實查證：** [DMS target metadata task settings and LOB modes](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.TargetMetadata.html)、[DMS table mapping selection and transformation rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.html)、[DMS task settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.html)

### 練習題 9｜SAP｜DMS data validation 與 business validation 邊界

DMS task status 顯示 `Load complete, replication ongoing`，團隊就要簽署 migration acceptance。Target row counts 接近 source，但 constraints、stored procedures 與財務 reconciliation 仍不在目前的 acceptance evidence 內。應如何處理？

A. 啟用 DMS row validation，將通過結果視為 stored code、constraints 與 business totals 也正確
B. 啟用/檢視 DMS data validation 與 mismatches，另做 counts、constraints、application regression、stored-code 與 business reconciliation，由 owner 接受
C. 只做 application smoke test，不核對 row counts、checksums、LOBs 與 reconciliation totals；Release evidence 另關聯「DMS data validation 與 business validation 邊界」的 pilot wave、result 與 rollback timestamp
D. 在 rollback window 內切換 target writer，以 production shadow reads 驗證 schema behavior 與 financial balance；Acceptance evidence 對照 DMS validation、row/LOB counts、constraints、stored code、API tests 與 business totals，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** DMS row validation 能比較支援的 source/target rows；它不執行 stored procedures、constraints 或財務 invariants，通過不能外推成完整 acceptance。
- **B：** 符合本題。DMS validation 是 row-level evidence 的一層，仍需 application/domain validation。
- **C：** Application smoke test 可證明核心連線/流程；沒有 row、LOB、checksum 與 balance evidence，靜默資料差異仍可能存在。
- **D：** Rollback window 可保留修正空間；先切 writer 再驗證 schema 與 financial totals，會讓新差異持續累積並使 rollback/reconciliation 更困難。

**事實查證：** [AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)、[AWS SCT assessment report](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)

### 練習題 10｜SAP｜heterogeneous database cutover 與 rollback

Oracle→Aurora PostgreSQL cutover 前 CDC lag 已低，但開發者仍在 source 套用 incompatible DDL。有人建議先改 DNS，讓 source/target 同時接受 writes。最佳 cutover 是什麼？

A. Freeze DDL 並等 CDC lag 收斂；「heterogeneous database cutover 與 rollback」的 dashboard 也保留 quota/cost、alarm state 與 last validation；Release evidence 另關聯「heterogeneous database cutover 與 rollback」的 pilot wave、result 與 rollback timestamp
B. Fence source writes，CDC latency 低於五秒即切換 endpoint，target 驗收採連線測試與核心 API smoke tests；「heterogeneous database cutover 與 rollback」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. Freeze incompatible DDL，讓 CDC 收斂，fence source writes，套用 final changes，驗證 target data/application，切 endpoint，並保留有期限的 rollback/reconciliation plan
D. 在 CDC lag 收斂後 finalize migration 並移除 source replication，pending constraints 與 downstream jobs 由 target stabilization phase 驗收；Cutover timeline 保存 DDL freeze、CDC checkpoint、source fence、target validation、endpoint switch 與 rollback expiry，exception expiry 與最後一次驗收時間也被保留

**答案：C**

- **A：** Freeze DDL 與等待 CDC 收斂是必要步驟；DNS 切換期間讓 source/target 同時接受 writes 會建立 DMS 無法雙向合併的 split brain。
- **B：** Fence source 與低 CDC lag 可縮短 downtime；連線與少量 API smoke test 不足以驗證異質 schema、constraints、stored code 和 business totals。
- **C：** 符合本題。Cutover 需要明確 authority、lag threshold、schema freeze、business validation 與 rollback boundary。
- **D：** 移除 rollback path 能降低雙重營運成本；pending changes、downstream jobs 與 target invariants 尚未驗收時 finalize，失敗後只剩高風險 forward repair。

**事實查證：** [AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)、[AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)、[DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_SchemaConversion.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換sc…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Server、database engine與schema/code conversion需要不同migration工具。」，所以「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」能直接滿足它；若constraint改成「DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」。替代方案「DataSync處理file/object，Snow處理離線資料，不能取代transactional CDC。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Server、database engine與schema/code conversion需要不同migration工具。」，排除會導致「只測initial load，cutover時CDC lag未歸零或unsupported objects未轉換。」的選項，再選「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」。本章對應的代表task包括：SAP-4.2 Determine the optimal migration approach for existing workloads。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「MGN持續block replication搬server；DMS搬資料並持續CDC；SCT評估/轉換schema與code。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate compute replication, data movement, and semantic conversion」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 88 章　7Rs：Rehost 到 Refactor

每個workload的business value、技術債與時間限制不同，不應全部refactor。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：資料中心租約九個月到期，但只有20%核心系統值得立即重構。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：每個workload的business value、技術債與時間限制不同，不應全部refactor。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Migration Hub如何接手工作，再看AWS Application Migration Service何時更合適，最後用設定與考題驗證「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：資料中心租約九個月到期，但只有20%核心系統值得立即重構。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Migration Hub]
          │ 集中追蹤migration portfolio、waves與多工具進度。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Application Migration Service：把physical、virtual或cloud servers以block replication搬到EC…

失敗時先找：把modernization當migration前置條件，導致data center exit期限失敗。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Migration Hub有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Migration Hub和AWS Application Migration Service並不是兩個任意的產品名稱。前者適合本章，是因為「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」直接回應了眼前的問題；後者描述的「Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把modernization當migration前置條件，導致data center exit期限失敗。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「migration strategy is a portfolio optimization problem」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 |

## 把全圖套進一個具體案例

**場景：** 資料中心租約九個月到期，但只有20%核心系統值得立即重構。

1. 故事的起點：資料中心租約九個月到期，但只有20%核心系統值得立即重構。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Migration Hub負責「集中追蹤migration portfolio、waves與多工具進度。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：彙整discovery與migration tools狀態，提供application grouping與journey visibility。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Application Migration Service各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把modernization當migration前置條件，導致data center exit期限失敗。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「它不搬資料本身；server用MGN、database用DMS、files用DataSync。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Migration Hub

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：每個workload的business value、技術債與時間限制不同，不應全部refactor。
- **具體例子／邊界：** 在「資料中心租約九個月到期，但只有20%核心系統值得立即重構。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Application Migration Service

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把modernization當migration前置條件，導致data center exit期限失敗。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：migration strategy is a portfolio optimization problem。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### modernization

為可維護性、可靠性、交付速度或成本改善application/platform；應由可量測outcome驅動，而非因服務較新。

### replatform

搬移時替換部分platform，例如改用managed database/container，但不重寫主要business architecture。

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

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### rehost

盡量不改application，把server搬到cloud IaaS；速度快但保留多數技術債與營運模式。

### retain

因法規、dependency、時程或business理由暫時保留原環境，並記錄重新評估日期。

### retire

確認沒有business value或consumer後安全下線workload，通常是最快的成本與風險消除方式。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

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

## 讀到這裡，請用自己的話說一次

1. AWS Migration Hub的責任：集中追蹤migration portfolio、waves與多工具進度。
2. 底層機制：彙整discovery與migration tools狀態，提供application grouping與journey visibility。
3. 第一個要看的設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
4. 選擇邏輯：用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。
5. 不要混淆：AWS Application Migration Service的責任是「把physical、virtual或cloud servers以block replication搬到EC2。」；它不會自動取代AWS Migration Hub。
6. 替換訊號：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
7. 最常見錯法：把modernization當migration前置條件，導致data center exit期限失敗。
8. 可移植原則：migration strategy is a portfolio optimization problem。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Migration Hub | 集中追蹤migration portfolio、waves與多工具進度。 | 彙整discovery與migration tools狀態，提供application grouping與journey visibility。 | 大型migration需要single pane追蹤而不是spreadsheet碎片。 | 它不搬資料本身；server用MGN、database用DMS、files用DataSync。 |
| AWS Application Migration Service | 把physical、virtual或cloud servers以block replication搬到EC2。 | Agent持續複寫disk到staging area；test/cutover launch settings建立EC2。 | rehost大量servers、低downtime cutover與DR-like migration。 | database engine轉換用DMS/SCT；refactor/serverless需另外重新架構。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。 | 只有當題目條件明確改變時才可能合理。 | 把modernization當migration前置條件，導致data center exit期限失敗。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。」之間做選擇。
- 認得常考設定：home Region、discovery sources、applications、waves、connectors與orchestrator templates。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：它不搬資料本身；server用MGN、database用DMS、files用DataSync。
- 對應官方tasks：SAP-4.1 Select existing workloads and processes for potential migration；SAP-4.2 Determine the optimal migration approach for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAP｜以 business outcome 選擇 migration R

Portfolio committee 規定所有 300 個 applications 都必須 refactor 成 serverless，理由是『cloud-native 最先進』。其中多數 apps 使用量低、即將退役或受 license 限制。較好的決策方式是什麼？

A. 依 business value、lifecycle、dependencies、compliance、deadline、skills、operating model、cost 與 modernization benefit 為每個 workload 選 R，記錄 owner、evidence 與 review date
B. 依技術團隊偏好的 target service 選擇 migration R，商業期限與流程變更由季度 portfolio board 評估
C. 所有 high-value workloads 直接選 Refactor，將 facility-exit deadline 視為次要限制
D. 建立單一 Rehost factory 作為 portfolio baseline，discovery evidence 只用來核准 Retire、Repurchase 或 Refactor exceptions；Portfolio record 對每個 workload 保存 lifecycle、deadline、business value、license、dependency、owner 與 selected R，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。7Rs 是 portfolio optimization，不是技術時尚排行榜；不同 workload 的期限與價值會翻轉答案。
- **B：** Target-service 偏好可反映團隊能力；migration R 還受 lifecycle、deadline、license、business process 與 compliance 影響，不能由技術偏好主導。
- **C：** High-value capability 常值得 Refactor；若 facility exit 或技能/資金是硬期限，先 Rehost/Relocate 再現代化可能有更低 program risk。
- **D：** 單一 R 可建立高吞吐 factory；300 個 workloads 的 retirement、SaaS fit、license 與價值不同，把 evidence 只用來找例外會系統性誤配。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)

### 練習題 2｜SAP｜安全 retire application

CMDB 顯示一個 legacy reporting app 三個月沒有 interactive users，因此團隊要立刻關機。調查發現它仍保存七年法定 records，且月末有下游 batch 讀取。要選 Retire，先做什麼？

A. 以 30 天無 interactive login 作 retire gate，records 留在原 database 並提供受控 read-only endpoint，月末 batch 改走 archived snapshot；Decommission inventory 記錄 consumers、records、integrations、access、contracts、archive location 與 restore window，設定版本與生效時間一併寫入 change record
B. 確認 consumers 與 record obligations，遷移/封存 authoritative data，替代或移除 integrations，撤銷 access/contracts，並在 decommission 後監控 missed use
C. 保留 read-only instance 供歷史查詢，以 cost center 作 owner，access review 依年度稽核週期執行
D. 刪除 application compute 並保留 database snapshot、DNS tombstone 與 support escalation，依 missed-use signals 決定是否 restore；「安全 retire application」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：B**

- **A：** 30 天無 interactive login 可作候選訊號；月末 batch 與七年 records 代表仍有 consumer/data obligation，停 server 不能等同 Retire。
- **B：** 符合本題。Retire 是受控 decommission，包括 data retention、dependency exit、access removal 與觀察期。
- **C：** Read-only instance 能快速保留查詢，仍保留 patching、database、access 和 ownership 成本，也沒有替代 month-end integration。
- **D：** Support tickets 能發現部分 missed users，刪除 production resource 已先破壞 records 與 batch；Retire 需要可逆觀察和資料封存順序。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[Migration playbook for AWS large migrations](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-migration-playbook/)

### 練習題 3｜SAP｜Retain 的責任與 revisit trigger（選兩項）

一個 mainframe workload 因法規與 proprietary hardware 暫時無法 migration，committee 選擇 Retain。哪兩項資訊必須跟著決策保存？（選兩項）

A. 決定 Retain 後停止投資 monitoring、patching 與 security，依既有維運模式持續運作
B. 記錄現有 security/support risk、owner、hybrid integration、lifecycle 與持續投資需求
C. 保留 workload 與 hybrid connectivity，ownership 與 risk acceptance 由 datacenter operations 團隊統一承擔
D. 設定具日期或事件的 revisit trigger，例如 vendor support deadline、法規核准或 dependency modernization
E. 延長 datacenter contract；續約前一個月重新評估 replacement 和 migration options

**答案：B、D**

- **A：** Retain 表示 workload 暫留，不表示停止 security、patching 與 monitoring；它仍是 production system，需要持續風險控制。
- **B：** 符合本題。留在原地仍是 production decision，風險、營運與相依必須被管理。
- **C：** Datacenter operations 可成為 platform custodian；business owner、data risk 與 hybrid dependency 不能全轉給基礎設施團隊。
- **D：** 符合本題。明確且有 owner 的日期或事件 trigger，能防止『暫時 retain』在沒有重新評估風險下變成無期限惰性。
- **E：** 合約續約日前重評估是有效 trigger；只留一個月可能不足以完成 replacement procurement、data migration 和 dependency change。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[Phases of a large migration](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/phases.html)

### 練習題 4｜SAP｜Relocate 與 operating model continuity

公司有大量 VMware workloads、成熟 vCenter/NSX/vSAN 操作流程，必須快速搬離機房，但短期不願改 application 或 operations。哪個 R 的核心最符合？

A. 把 VMware VMs 逐台 rehost 到 EC2；採用 operating model 改變與重新平台驗證
B. 使用 Relocate 搬離機房；同步重寫 application 與 database，擴大 deadline 風險
C. Relocate：在支援的目標平台搬移既有 virtualized environment，並驗證 license、network、operations 與後續 modernization constraints
D. 先搬移 VMware management plane，再將 production clusters 批次 relocation；network、license 與 recovery model沿用現有設定

**答案：C**

- **A：** 逐 VM Rehost 到 EC2 能快速搬離 VMware，會改變 vCenter/NSX/vSAN operating model，與題目短期保持既有操作方式的要求不同。
- **B：** Relocate 本身符合快速搬平台；同步重寫 application/database 把它變成 Refactor/Replatform program，增加六個月 deadline 風險。
- **C：** 符合本題。Relocate 著重平台位置移動而非逐一改造 workload，但仍需評估目標支援與長期成本。
- **D：** 先搬 management plane 可作 staged relocation；network、license 與 recovery model 是 production cutover 的前置條件，不能等流量已切換才確認。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)

### 練習題 5｜SAP｜deadline 驅動的 Rehost

資料中心租約六個月後終止。某穩定的 Windows application 沒有立即 modernization budget，但必須先搬走並保持功能。最適合的策略是什麼？

A. 在六個月內 Refactor 核心 Windows application，以固定 feature scope 與專責轉型團隊執行
B. Repurchase SaaS 並同步重塑 business process；評估 identity、data migration 與 contract lead time
C. Rehost 全部 Windows servers，rightsizing 依 Compute Optimizer 建議執行，modernization 由各產品 roadmap 決定；Exit plan 對照 facility deadline、server inventory、MGN readiness、security baseline、rightsizing 與 backlog owner，相關 alarms 與 rollback timestamp 納入 release evidence
D. Rehost：使用 MGN 等方式以最少 application change 搬到 EC2，同時補上 target security/resilience/rightsizing，並建立 post-migration optimization backlog

**答案：D**

- **A：** 固定 scope 的 Refactor 在有專責團隊時可行；六個月 facility exit 且沒有 modernization budget，使 architecture rewrite 成為 deadline critical path。
- **B：** Repurchase 可減少長期自管負擔；SaaS procurement、process redesign、identity 與 data migration lead time 尚未證明能符合六個月。
- **C：** Rehost 與後續 rightsizing 是合理方向；把 modernization 完全交給無 owner/date 的產品 roadmap，容易讓原有 toil 永久留在 EC2。
- **D：** 符合本題。Rehost 優化 exit speed，但不代表可忽略 landing zone、testing 或後續營運改善。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[What is AWS Transform MGN?](https://docs.aws.amazon.com/mgn/latest/ug/)

### 練習題 6｜SAP｜Replatform 的 bounded change

一個 Java application 可維持原架構與 SQL dialect，但團隊想把 self-managed MySQL 改成 RDS MySQL，減少 backup/patching 工作。這最接近哪個 R？

A. Replatform，因為選擇性改用 managed compatible platform，核心 application architecture 未全面重寫；仍需 compatibility、performance 與 rollback tests
B. 將 self-managed MySQL rehost 到 EC2，使用 Systems Manager automation 執行 patch、backup 與 failover runbook；「Replatform 的 bounded change」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 改寫成 DynamoDB event model 與 serverless API，變更範圍已超過 bounded Replatform
D. 切換到 RDS MySQL，extensions、parameter groups 與 latency 以 production shadow traffic 和 rollback window 驗收；Compatibility report 比較 MySQL version、extensions、parameter groups、SQL behavior、latency 與 rollback path，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。Replatform 是有界的技術優化，介於 as-is rehost 與 architecture refactor 之間。
- **B：** MySQL 搬到 EC2 仍由團隊操作 database，即使以 Systems Manager 自動化 patch/backup，分類上更接近 Rehost。
- **C：** DynamoDB event model 與 serverless API 可能帶來更大效益，已改變資料與 application architecture，屬 Refactor 而非 bounded Replatform。
- **D：** RDS MySQL 是合適 Replatform；extensions、parameter groups、latency 和 operations 若在 cutover 後才驗證，rollback risk 會高於先做 compatibility test。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[DMS homogeneous data migrations](https://docs.aws.amazon.com/dms/latest/userguide/data-migrations.html)

### 練習題 7｜SAP｜Repurchase 與 SaaS exit planning

公司考慮用 SaaS CRM 取代自建 CRM。只比較月租後，SaaS 看似較便宜，但尚未評估歷史資料匯出、SSO、partner integrations、data residency 與 contract exit。正確的 Repurchase 評估是什麼？

A. 購買 SaaS 替代功能；Audit trail 另標示「Repurchase 與 SaaS exit planning」的設定版本、生效時間與 exception expiry；「Repurchase 與 SaaS exit planning」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 比較 functional fit、data migration/export、identity、integration、compliance、operating process、contract 與退出條款，並規劃舊系統 decommission
C. 評估 SaaS process fit 與資料搬移，vendor exit 依賴 CSV export、合約終止條款與人工重建 integrations；SaaS assessment 保存 process fit、SSO、data mapping/export、integrations、residency、API limits 與 exit terms，相關 alarms 與 rollback timestamp 納入 release evidence
D. 簽長期合約取得折扣；「Repurchase 與 SaaS exit planning」的 change record 另保存 scope、owner、approver 與 rollback trigger；Audit trail 另標示「Repurchase 與 SaaS exit planning」的設定版本、生效時間與 exception expiry

**答案：B**

- **A：** SaaS 功能吻合只是起點；沿用原 identity/integration/export assumptions 會把產品 contract 的差異隱藏到導入階段。
- **B：** 符合本題。Repurchase 是產品與流程轉型，需要完整 adoption、data exit 與 decommission plan。
- **C：** CSV export 與人工重建 integrations 可作低複雜度 exit plan；關鍵 CRM 若有大量關聯資料/API，這種 reversibility 可能不滿足 RTO、完整性或合約需求。
- **D：** 長約折扣可降低單價；在簽約後才確認 API limits、data ownership 和 exit，switching cost 已經形成，應先完成 due diligence。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)

### 練習題 8｜SAP｜何時值得 Refactor（選兩項）

一個高營收 checkout capability 因共享部署每季只能發布一次，尖峰擴展與故障隔離都不足。資料中心 exit 只剩九個月。哪兩項做法最合理？（選兩項）

A. 在遷移主路徑一次重寫整個 monolith，讓 facility exit 等待新平台廣泛完成
B. Rehost 高價值 capability 到 EC2，使用 ALB path rules 與 monolith 共存，成功指標採主機可用率
C. 以 business capability、獨立交付價值、scaling/reliability outcome 與 team ownership 證明 checkout 值得 refactor
D. 建立新 microservices，以單次 DNS cutover 接收流量，資料權威仍集中在 monolith database
E. 將 refactor 分成可增量交付的 boundaries/strangler steps，並避免讓整個 facility exit 依賴一次完成的 rewrite

**答案：C、E**

- **A：** 完整 rewrite 可一次清理 monolith debt；它會讓九個月 facility exit 依賴最大、最不可預測的 delivery scope。
- **B：** Rehost checkout 可先離開機房，ALB coexistence 也支持增量；只用主機可用率驗收，沒有處理每季發布、尖峰 scaling 與故障隔離的原 business outcome。
- **C：** 符合本題。Refactor 應保留給有差異化價值且現有 architecture 真正限制 outcome 的 capabilities。
- **D：** Microservices 與 DNS cutover 可建立新 runtime；共享 monolith database 仍保留 schema/release coupling，單次切換也失去 strangler 的漸進回退。
- **E：** 符合本題。Incremental extraction 可同時管理 modernization value 與 deadline risk。

**事實查證：** [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)、[Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)、[Strangler fig pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html)

### 練習題 9｜SAP｜固定 exit date 下的 portfolio mix

九個月後機房關閉：20% workloads 已無用途，15% 適合 SaaS，50% 可快速搬移，15% 核心系統值得長期重構。哪個 portfolio strategy 最合理？

A. 所有 workloads 採同一 Rehost factory，以 throughput 換取不必要的舊系統延續
B. 所有 workloads 都採 Refactor 到共同 serverless platform，使用既定六個月 exit date 與現有 delivery teams；Portfolio burn-up 分類 Retire、Repurchase、Rehost、Relocate、Replatform、Refactor 與 deadline progress，具名 owner 與 approver 依固定 cadence 複核
C. 依證據 retire/repurchase，讓 deadline-critical majority rehost/relocate，僅對高價值 candidates 做不阻塞 exit 的 replatform/refactor
D. 在 portfolio approval 時凍結 disposition，只有年度 steering committee 可以重新分類 workload

**答案：C**

- **A：** Rehost factory 可最大化搬遷 throughput；已無用途或適合 SaaS 的 35% workload 會被不必要地延長成本與技術債。
- **B：** 共同 serverless platform 可標準化長期營運；九個月 exit、現有 teams 與所有 workload 同時 Refactor 的 scope 不相容。
- **C：** 符合本題。Portfolio mix 同時滿足 deadline、risk 與 modernization value。
- **D：** 凍結 disposition 可穩定 portfolio plan；evidence、vendor support 或 dependency 在年度會議前改變時，無法及時重新選 R。

**事實查證：** [Phases of a large migration](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/phases.html)、[AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)

### 練習題 10｜SAP｜migration 後重新檢視 disposition

一年前 rehost 的 application 已穩定運作，但 EC2 成本高、patching toil 沒下降、部署速度也沒有改善。Program office 說 migration 已結案，不應再碰。哪個做法較好？

A. Migration 完成後永久維持原 R，將雲端實際成本與營運 toil 視為 sunk decision；Audit trail 另標示「migration 後重新檢視 disposition」的設定版本、生效時間與 exception expiry；「migration 後重新檢視 disposition」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. 只因新 managed service 上線就立即 Replatform
C. 依新 managed-service capability 啟動 modernization project，將實際 cost、toil 與 delivery metrics納入第一個 design phase；Post-migration review 比較原 business case 與實際 cost、incidents、performance、delivery speed、toil，相關 alarms 與 rollback timestamp 納入 release evidence
D. 比較實際 cost、incidents、performance、delivery speed 與 toil 對原 business case，將合適的 replatform/refactor/rightsizing 納入 owner-backed backlog

**答案：D**

- **A：** 維持原 R 可避免新變更風險；實際成本、patching toil 與 delivery 已證明 business case 未達成，把它視為永久決策會停止應有的優化。
- **B：** 新 managed service 可能讓 Replatform 更有吸引力；服務上線本身不是 workload fit evidence，仍需比較 switching cost、compatibility 與 outcome。
- **C：** Modernization project 可以合理啟動；若先開專案才定義 evidence、success metrics 和 owner，容易再次以技術活動取代 business outcome。
- **D：** 符合本題。Rehost 常是時間策略，migration 後需用實際結果決定是否進一步 modernize。

**事實查證：** [AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)、[Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)、[AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「用retain/retire/relocate/rehost/replatform/repurchase/…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「每個workload的business value、技術債與時間限制不同，不應全部refactor。」，所以「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」能直接滿足它；若constraint改成「Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」。替代方案「Rehost速度快但保留營運問題；refactor收益高但風險與時間最大。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把modernization當migration前置條件，導致data center exit期限失敗。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「每個workload的business value、技術債與時間限制不同，不應全部refactor。」，排除會導致「把modernization當migration前置條件，導致data center exit期限失敗。」的選項，再選「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」。本章對應的代表task包括：SAP-4.1 Select existing workloads and processes for potential migration；SAP-4.2 Determine the optimal migration approach for existing workloads。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「用retain/retire/relocate/rehost/replatform/repurchase/refactor逐一決策並記錄理由。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「migration strategy is a portfolio optimization problem」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 89 章　Monolith 到 Containers／Serverless

Modernization需要找到可獨立演進邊界，而不是把monolith機械切成大量服務。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

把鏡頭拉到一個真實的production現場：大型Java monolith每季發布，團隊想逐步讓付款與通知獨立交付。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：Modernization需要找到可獨立演進邊界，而不是把monolith機械切成大量服務。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon ECS是這一章的入口，Amazon EKS用來畫出邊界；主要方向「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：大型Java monolith每季發布，團隊想逐步讓付款與通知獨立交付。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[Amazon ECS]
          │ 以AWS原生control plane排程與維護containers。
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · Amazon EKS：提供managed Kubernetes control plane與AWS整合。
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。
  · Amazon API Gateway：提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。

失敗時先找：共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問Amazon ECS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon ECS和Amazon EKS並不是兩個任意的產品名稱。前者適合本章，是因為「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」直接回應了眼前的問題；後者描述的「Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「modernize around ownership and change boundaries」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 |

## 把全圖套進一個具體案例

**場景：** 大型Java monolith每季發布，團隊想逐步讓付款與通知獨立交付。

1. 故事的起點：大型Java monolith每季發布，團隊想逐步讓付款與通知獨立交付。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon ECS負責「以AWS原生control plane排程與維護containers。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EKS、AWS Lambda、Amazon API Gateway各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon ECS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Modernization需要找到可獨立演進邊界，而不是把monolith機械切成大量服務。
- **具體例子／邊界：** 在「大型Java monolith每季發布，團隊想逐步讓付款與通知獨立交付。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EKS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：modernize around ownership and change boundaries。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### modernization

為可維護性、可靠性、交付速度或成本改善application/platform；應由可量測outcome驅動，而非因服務較新。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

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

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

### Amazon API Gateway

- **功用：** 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
- **底層機制：** Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。
- **關鍵設定：** REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
- **選擇時機：** serverless API、公開/私有API、consumer治理與request transformation。
- **替換時機：** 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。

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

## 讀到這裡，請用自己的話說一次

1. Amazon ECS的責任：以AWS原生control plane排程與維護containers。
2. 底層機制：Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。
3. 第一個要看的設定：task definition、taskRoleArn、executionRoleArn、networkMode、capacity provider、service deployment與health check。
4. 選擇邏輯：先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。
5. 不要混淆：Amazon EKS的責任是「提供managed Kubernetes control plane與AWS整合。」；它不會自動取代Amazon ECS。
6. 替換訊號：既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。
7. 最常見錯法：共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。
8. 可移植原則：modernize around ownership and change boundaries。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 | 團隊要container但不需要Kubernetes API與生態相容性時。 | 既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 | 需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。 | 不需要Kubernetes複雜度時以ECS降低營運；單一事件handler可用Lambda。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 | serverless API、公開/私有API、consumer治理與request transformation。 | 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。 | 只有當題目條件明確改變時才可能合理。 | 共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。」之間做選擇。
- 認得常考設定：task definition、taskRoleArn、executionRoleArn、networkMode、capacity provider、service deployment與health check。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。
- 對應官方tasks：SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAP｜以 business capability 選 service boundary

團隊準備拆分電商 monolith，提議每張 database table 建一個 microservice。Orders、payments 與 refunds 會跨多張 tables，且由不同團隊負責。較好的第一個 boundary 是什麼？

A. 依現有 code packages 切 services，shared database 與跨團隊 release cadence 維持不變
B. 依 business capability、team/change ownership、data authority、scaling 與 failure needs 找 cohesive boundary，例如先抽出 notifications 或 payments capability
C. 依每張 database table 建 microservice，business capability 與 ownership 分散在多個團隊
D. 先依 code ownership 建立 service repositories，data authority 與 domain boundaries 由 production telemetry 和 incident ownership逐步收斂

**答案：B**

- **A：** Code package boundary 能降低初始搬移成本；shared database 與跨團隊 release cadence 不變時，service 仍不能獨立部署或承擔 capability。
- **B：** 符合本題。Service boundary 應讓一項 capability 能獨立演進並對資料與結果負責。
- **C：** Table-per-service 看似有清楚資料邊界；orders/payments/refunds 的 business transaction 跨 tables，會把一個 capability 拆成大量 chatty services。
- **D：** 多 repositories 可建立組織分工；沒有先定義 data authority 和 business boundary，incident 只會在 production 暴露 ownership 衝突。

**事實查證：** [Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)

### 練習題 2｜SAP｜Strangler pattern 的流量與 rollback

公司要在不停機下逐步把 `/notifications` 從 monolith 移到新服務。哪個實作最符合 strangler pattern？

A. 以 facade/router 將第一版完整流量切到新服務，rollback 使用 DNS 記錄切回 monolith
B. 逐步把流量導向新服務，舊路徑長期保留為 resilience fallback，兩邊共同承擔維護
C. 在 facade/router 建可控規則，導少量 notifications traffic 到新服務，驗證 business behavior 與 rollback，移除依賴後再淘汰舊路徑
D. 依 API Gateway access logs 完成 consumer inventory 後移除 monolith endpoint，partner exceptions 走 support queue

**答案：C**

- **A：** Facade/router 是 strangler 的核心元件；第一版就切全部 traffic 會失去小範圍學習，DNS rollback 也可能受 cache 和 state divergence 影響。
- **B：** 逐步導流符合增量精神；舊路徑永久作 fallback 會形成雙重維護、兩套 behavior 和未完成的 decommission。
- **C：** 符合本題。Strangler 以路由邊界漸進替換 functionality，讓每一步可量測與回退。
- **D：** Access logs 可建立 consumer inventory；立即移除 endpoint 並把 partner 問題交給 support，沒有 parallel route、usage gate 和可驗證 rollback。

**事實查證：** [Strangler fig pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html)、[Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)

### 練習題 3｜SAP｜containerization tooling 的真正邊界（選兩項）

新客戶想用 automated tooling 把 Java monolith 變成 containers，主管認為完成後就自然成為 stateless microservices。哪兩項說法正確？（選兩項）

A. 使用 containerization tooling 打包 monolith，將產生 containers 視為已完成 domain decomposition
B. 建立 ECS/EKS runtime，再把 shared database 與 coordinated deployment 由產品團隊的 local roadmap 管理
C. 對支援的新客戶情境，可評估 AWS Transform source-code containerization；既有 App2Container 客戶需依其現行可用性邊界處理
D. 在同一 release 中完成 container packaging、service boundaries 與 data ownership 拆分，驗收採整合測試
E. Tooling 可改善 packaging/build/deployment 起點；domain boundaries、state、scaling、contracts、team ownership 與 rollback 仍需架構設計

**答案：C、E**

- **A：** Containerization tooling 能產生 image/build artifacts，不會自動改變 domain boundary、shared state 或 coordinated deployment。
- **B：** ECS/EKS runtime 可改善 packaging/operations；shared database 與同步 release 被留在產品 roadmap，architecture coupling 仍存在。
- **C：** 符合本題。服務可用性與名稱會演進，建議必須標示 current customer boundary。
- **D：** 同一 release 同時做 packaging、service/data decomposition 可能適合小型系統；大型 monolith 會把工具遷移與 domain redesign 風險綁成一次不可分割變更。
- **E：** 符合本題。Containerization 是 modernization 的一層，不等於完成 architecture decomposition。

**事實查證：** [AWS Transform source-code containerization](https://docs.aws.amazon.com/transform/latest/userguide/transform-containers.html)、[AWS App2Container availability for new customers](https://docs.aws.amazon.com/app2container/latest/UserGuide/what-is-a2c.html)、[Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)

### 練習題 4｜SAP｜ECS、EKS、Lambda 的 operating contract

三個團隊有不同需求：A 要 AWS-native container orchestration、B 必須使用 Kubernetes operators/CRDs、C 是短時間 event-driven image resize 且流量高度變動。哪個配對最合理？

A. 所有三類 workloads 都選 EKS，以單一平台換取較高 operating burden 與不必要控制面；「ECS、EKS、Lambda 的 operating contract」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. A 與 B 使用 Lambda 搭配 Step Functions，C 以 Lambda container image 執行 Kubernetes controller workload；「ECS、EKS、Lambda 的 operating contract」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 依團隊熟悉度選 ECS、EKS 或 Lambda，workload limits、state 與 observability 以標準 production-readiness review 管理；Runtime scorecard 比較 orchestration API、execution duration、event model、state、skill、cost 與 platform ownership，相關 alarms 與 rollback timestamp 納入 release evidence
D. A 評估 ECS，B 評估 EKS，C 評估 Lambda；再比較 execution limits、team skill、state、observability 與 platform ownership

**答案：D**

- **A：** EKS 可以承載三種 workload，也提供 Kubernetes API；A/C 沒有 operators/CRDs 需求，會承擔額外 control-plane 與 platform operations。
- **B：** Lambda/Step Functions 適合短時 orchestration；Kubernetes controller 需要持續 watch/reconcile 與 CRD contract，C 才是短時 event-driven resize。
- **C：** 團隊熟悉度是選型因素；execution duration、event model、Kubernetes API、state 和 ownership 必須在 runtime 決策前評估，不能只在上線後觀察。
- **D：** 符合本題。選型基於 workload contract 與 operating model，而不是產品偏好。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[AWS Lambda best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

### 練習題 5｜SAP｜共享 database 的解耦

Monolith 已拆成 orders、inventory 與 billing containers，但三個 services 都直接讀寫同一批 tables，任何 schema change 仍需同時部署。下一個最重要的 architecture step 是什麼？

A. 逐步指定 capability 的 authoritative data owner，透過 API/events/transitional views 存取，遷移與 reconcile state，最後移除其他 services 的 shared writes
B. 把 monolith 包成多個 containers；services 仍直接寫同一批 shared tables
C. 指定 data owner 並提供 API，其他 services 仍保留 emergency direct-write credentials
D. 移除 shared writes，再完成資料遷移、reconciliation 與 consumer cutover

**答案：A**

- **A：** 符合本題。Independent deployment 的核心是 contract 與 data authority，而不只是 process/container boundary。
- **B：** 多 containers 可分開 process 和 scaling；共同 direct-write tables 仍讓 schema、transaction 與 deployment lockstep。
- **C：** API 加 data owner 是正確過渡；其他 services 保留常態可用的 direct-write credentials，authority 仍可被繞過，incident 時最容易再次耦合。
- **D：** 移除 shared writes 是最終目標；在 data migration、reconciliation 和 consumer cutover 前先撤銷，會中斷現有流程或遺失 writes。

**事實查證：** [Distributed data management](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/distributed-data-management.html)、[Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)

### 練習題 6｜SAP｜transactional outbox 避免 dual-write gap

Order service 先 commit database，再 publish `OrderCreated` 到 EventBridge。偶爾 process 在兩步之間 crash，database 有訂單但下游沒收到事件。應如何改善？

A. 在 database commit 後直接 publish event，publisher 失敗時由人工比對缺漏訊息
B. 在同一 local transaction 寫入 order 與 outbox record，再由 publisher 重試送出；consumers 以 event/idempotency key 去重
C. 使用 transactional outbox，consumer 以 message timestamp 與五分鐘 deduplication window 處理重送
D. 部署 polling publisher 掃描既有 orders table，以 created_at watermark 推導待發布事件並重送到 EventBridge；Event-delivery audit 關聯 order transaction、outbox row、publish attempt、event ID 與 consumer dedup result，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** DB commit 後直接 publish 保留 dual-write window；人工比對只能事後修復，process crash 時事件仍不會可靠產生。
- **B：** 符合本題。Transactional outbox 讓 business state 與待發布事件共同 commit，delivery 可重試且接受 at-least-once。
- **C：** Transactional outbox 已解決 producer atomicity；用短時間 timestamp window 去重可能把延遲重送當新事件，應以穩定 event/idempotency key。
- **D：** Polling publisher 是 outbox 的常見元件；若 order 與 outbox 不是從一開始就在同一 local transaction，已遺失的事件無法由 polling 重建。

**事實查證：** [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

### 練習題 7｜SAP｜Saga 與 compensation semantics

Checkout 要依序 reserve inventory、charge card、create shipment，三個 services 各自有 database。Charge 成功後 shipment 失敗。哪個設計最符合分散式 transaction reality？

A. 使用 Saga choreography 發布每個 local commit，補償動作以原交易的反向 SQL 或退款 API 實作；Audit trail 另標示「Saga 與 compensation semantics」的設定版本、生效時間與 exception expiry
B. 改用同步 request chain 並延長 timeout，期待跨服務形成單一 ACID transaction
C. 使用 Saga orchestration 或 choreography，讓每一步維持 local transaction，並定義 timeout、idempotency、補償失敗與人工 reconciliation；退款等補償動作不保證外部世界回到完全相同的狀態
D. 使用 Step Functions 對 shipment task 持續 retry，charge transaction 保持 committed 直到物流服務恢復；Workflow trace 保存 step status、task token、retry count、timeout、correlation ID 與 manual case，exception expiry 與最後一次驗收時間也被保留

**答案：C**

- **A：** Saga choreography 可協調 local commits；把補償一律視為反向 SQL/退款 API，沒有處理不可逆外部副作用、補償失敗與人工 reconciliation。
- **B：** 同步 request chain 可簡化控制流程，三個獨立 databases 不會因 timeout 拉長而形成單一 ACID transaction，部分成功仍需處理。
- **C：** 符合本題。Saga 接受跨服務無法形成單一 ACID transaction，改以 local transactions、補償與 reconciliation 管理部分成功；補償本身也可能失敗，且不一定能撤銷已發生的外部副作用。
- **D：** Step Functions retry 適合 transient shipment failure；無界等待會長期保留已扣款但未出貨狀態，仍需 timeout、compensation 與 customer resolution。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Distributed data management](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/distributed-data-management.html)

### 練習題 8｜SAP｜API/event contract 漸進版本化（選兩項）

新 payment service 要把 `customer_id` 改名並新增欄位，但舊 monolith 與三個 partners 尚未同步升級。哪兩項 rollout 原則正確？（選兩項）

A. 優先做 backward-compatible additive change，讓 consumers tolerant 讀取，並量測各版本使用情況
B. 新增欄位並保留舊欄位，舊契約依固定六個月政策退場，consumer usage 不納入期限調整
C. 建立 v2 breaking contract，提供 30 天 partner migration window，期限到期即停止 v1 responses 與 events
D. 若必須 breaking change，建立明確 version、migration/deprecation window，保留 correlation 與 idempotency keys，直到 consumers 完成
E. 改 database row/schema 名稱，再由 API gateway mapping 臨時修補每個舊 consumer

**答案：A、D**

- **A：** 符合本題。Additive evolution 降低 lockstep deployment，usage telemetry 決定何時可安全淘汰。
- **B：** Additive 欄位可維持相容；固定六個月與實際 partner adoption 脫鉤，仍在使用舊契約的 consumer 會被政策日期直接中斷。
- **C：** Versioned v2 與 migration window 是正確機制；30 天不是題幹提供的 business constraint，不能不看 consumer usage、owner 與合約就停止 v1。
- **D：** 符合本題。Breaking change 需要 parallel contracts、owner、期限與追蹤。
- **E：** Gateway mapping 可暫時轉換 API field；直接改 database schema 會同時影響 events、batch 與繞過 gateway 的 consumers，形成多份 per-consumer patch。

**事實查證：** [Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)、[Path-based API versioning with API Gateway](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/implement-path-based-api-versioning-by-using-custom-domains.html)

### 練習題 9｜SAP｜blue/green 與 mutable state rollback

ECS blue/green deployment 的 green tasks 健康，但新版本先執行不可逆 schema migration。切 20% traffic 後 business error rate 上升；團隊只能把 task definition 切回 blue。哪個設計可避免此困境？

A. 使用 blue/green compute deployment；先執行只與 green 相容的不可逆 schema change
B. 採 expand/contract schema，green 版本 dual-write 新舊欄位，blue 版本維持讀取舊欄位
C. 使用 CodeDeploy all-at-once 將流量切到 green，automatic rollback 只依 ALB target health 執行
D. 使用 backward/forward-compatible schema steps、business/technical alarms、漸進 traffic shift 與 bake time，並預先定義 writes/events 在 rollback 時如何處理

**答案：D**

- **A：** Blue/green 能快速切 compute；只與 green 相容的不可逆 schema 使 blue 無法安全接手 rollback。
- **B：** Expand/contract 與 dual-write 是正確方向；blue 只讀舊欄位時，rollback 仍要確認 green 期間的新 writes 已同步回舊 representation。
- **C：** All-at-once 加 ALB health rollback 適合 stateless、schema-compatible release；business error 與 data mutation 可能在 target health 正常時持續發生。
- **D：** 符合本題。Compute rollback 只有在 state/contract 相容時才完整，必須在 deploy design 中共同處理。

**事實查證：** [Amazon ECS blue/green deployments](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-blue-green.html)、[Backward-compatible database changes for continuous delivery](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.ads.5-ensure-backwards-compatibility-for-data-store-and-schema-changes.html)

### 練習題 10｜SAP｜platform team 與 product team ownership

Modernization 後發生 incident，product team 認為 ECS cluster、network 與 observability 都是平台提供，因此平台也應負責所有 application errors、data correctness 與 customer SLO。哪個 ownership model較健康？

A. 平台擁有 paved-road runtime、identity、network、observability 與 deployment capabilities；產品團隊擁有 service behavior、data、SLO、cost 與 on-call，雙方以明確 interfaces 協作
B. 平台團隊同時擁有每個產品的 business behavior、data 與 on-call，產品團隊只提交 code
C. 產品團隊各自建立 runtime、identity 與 observability，避免共享 paved road 的治理限制
D. 平台 golden path 強制統一 runtime、network 與 observability，所有產品共用一組 support SLO 與 exception policy；Ownership catalog 分開列出 platform capabilities 與 product behavior、data、SLO、cost、on-call responsibility，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。Platform/product boundaries 同時提供標準化與 end-to-end ownership。
- **B：** 平台集中擁有 application behavior/data 可減少產品負擔，會讓平台成為所有 domain incident 的 bottleneck，產品團隊也失去 end-to-end accountability。
- **C：** 各產品自建 runtime 可得到最大自治；identity、network、observability 重複實作，安全與營運標準難以一致。
- **D：** Golden path 可以強制最低標準；所有產品共用相同 SLO/exception policy 會忽略不同 customer criticality，標準化也不能轉移 product on-call 責任。

**事實查證：** [AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)、[Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先strangler邊緣功能，建立API/event contract，將state與deployment…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Modernization需要找到可獨立演進邊界，而不是把monolith機械切成大量服務。」，所以「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」能直接滿足它；若constraint改成「Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」。替代方案「Containerize可先改善部署一致性；serverless適合事件與變動流量，但不自動解耦domain。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Modernization需要找到可獨立演進邊界，而不是把monolith機械切成大量服務。」，排除會導致「共享database的微服務仍高度耦合，且distributed transaction讓可靠性下降。」的選項，再選「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」。本章對應的代表task包括：SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先strangler邊緣功能，建立API/event contract，將state與deployment逐步分離。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「modernize around ownership and change boundaries」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 90 章　持續改善既有系統

SAP常不是從空白設計，而是要求在最少風險下改善安全、可靠、效能與成本。

## 把鏡頭從單一服務拉到整家公司：先從故事開始

如果今天由你值班，收到的需求可能是這樣：現有平台穩定但昂貴、部署慢且跨帳號權限過寬，不能長時間停機。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：SAP常不是從空白設計，而是要求在最少風險下改善安全、可靠、效能與成本。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Well-Architected Tool承接主要責任，以AWS Compute Optimizer檢查替代條件，並用「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：現有平台穩定但昂貴、部署慢且跨帳號權限過寬，不能長時間停機。

Organization／business portfolio
          │ ① identity、policy與account vending
          ▼
[AWS Well-Architected Tool]
          │ 在AWS中記錄Well-Architected reviews、milestones與improvement pl…
          │ ② shared network／security／logging平台
          │ ③ workload teams在guardrail內獨立交付
          ▼
[member accounts／workloads]
Operating model：owner + delegation + evidence + rollout/rollback
本章其他角色：
  · AWS Compute Optimizer：根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
  · AWS Config：記錄AWS resource configuration history並評估rules/conforma…

失敗時先找：只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「把鏡頭從單一服務拉到整家公司」。先不要急著問AWS Well-Architected Tool有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Well-Architected Tool和AWS Compute Optimizer並不是兩個任意的產品名稱。前者適合本章，是因為「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」直接回應了眼前的問題；後者描述的「一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「continuous improvement is hypothesis-driven architecture」。更白話地說：除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 |

## 把全圖套進一個具體案例

**場景：** 現有平台穩定但昂貴、部署慢且跨帳號權限過寬，不能長時間停機。

1. 故事的起點：現有平台穩定但昂貴、部署慢且跨帳號權限過寬，不能長時間停機。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Well-Architected Tool負責「在AWS中記錄Well-Architected reviews、milestones與improvement plans。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Compute Optimizer、AWS Config各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Well-Architected Tool

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：SAP常不是從空白設計，而是要求在最少風險下改善安全、可靠、效能與成本。
- **具體例子／邊界：** 在「現有平台穩定但昂貴、部署慢且跨帳號權限過寬，不能長時間停機。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Compute Optimizer

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：continuous improvement is hypothesis-driven architecture。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### AWS Well-Architected Tool

- **功用：** 在AWS中記錄Well-Architected reviews、milestones與improvement plans。
- **底層機制：** Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
- **關鍵設定：** workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- **選擇時機：** 需要重複、可稽核的architecture review process。
- **替換時機：** 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。

### AWS Compute Optimizer

- **功用：** 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。
- **底層機制：** 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。
- **關鍵設定：** opt-in、lookback、enhanced infrastructure metrics、external metrics ingestion與recommendation preferences。
- **選擇時機：** 找over/under-provisioned resources並建立rightsizing候選。
- **替換時機：** 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。

### AWS Config

- **功用：** 記錄AWS resource configuration history並評估rules/conformance packs。
- **底層機制：** Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。
- **關鍵設定：** recorder、delivery channel、managed/custom rules、conformance packs、aggregator與remediation。
- **選擇時機：** 回答「資源何時變成這樣」、組態合規與多帳號inventory。
- **替換時機：** 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。

## 考前與實作時再查：設定操作手冊

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

### AWS Config：逐項設定說明

#### `recorder`

- **控制什麼：** `recorder`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `delivery channel`

- **控制什麼：** `delivery channel`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `managed/custom rules`

- **控制什麼：** `managed/custom rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「回答「資源何時變成這樣」、組態合規與多帳號inventory。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Config以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `conformance packs`

- **控制什麼：** `conformance packs`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `aggregator`

- **控制什麼：** `aggregator`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `remediation`

- **控制什麼：** `remediation`把AWS Config與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. AWS Well-Architected Tool的責任：在AWS中記錄Well-Architected reviews、milestones與improvement plans。
2. 底層機制：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
3. 第一個要看的設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
4. 選擇邏輯：先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。
5. 不要混淆：AWS Compute Optimizer的責任是「根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。」；它不會自動取代AWS Well-Architected Tool。
6. 替換訊號：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
7. 最常見錯法：只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。
8. 可移植原則：continuous improvement is hypothesis-driven architecture。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 | 需要重複、可稽核的architecture review process。 | 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。 |
| AWS Compute Optimizer | 根據歷史metrics與ML提出EC2/EBS/Lambda/ECS等rightsizing建議。 | 分析CPU、memory（需agent）、network與利用率，估計性能風險與節省。 | 找over/under-provisioned resources並建立rightsizing候選。 | 建議不是自動安全變更；需load test、seasonality、license與SLO驗證。 |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 | 回答「資源何時變成這樣」、組態合規與多帳號inventory。 | 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。 | 只有當題目條件明確改變時才可能合理。 | 只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。」之間做選擇。
- 認得常考設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- 對應官方tasks：此章主要是SAP延伸背景。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability；SAP-3.5 Identify opportunities for cost optimizations；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAP｜改善前的 workload baseline

架構師看到某 account CPU 平均 20%，立即建議把整個平台改成 serverless。團隊尚未定義 critical user journeys、SLO、dependencies、incidents、lead time 或 unit cost。第一步應是什麼？

A. 只建立 infrastructure inventory 與月帳單 baseline，不記錄 users、journeys、SLO 與 incidents；Audit trail 另標示「改善前的 workload baseline」的設定版本、生效時間與 exception expiry；「改善前的 workload baseline」的 dashboard 也保留 quota/cost、alarm state 與 last validation
B. Well-Architected review 以整個 AWS account 為 workload scope，中央 cloud team 是 findings 的共同 owner；Workload baseline 保存 owners/users、critical journeys、dependencies、SLO、incidents、lead time 與 unit cost，具名 owner 與 approver 依固定 cadence 複核
C. 建立 workload boundary 與 baseline：owners/users、critical journeys、architecture/dependencies、security obligations、SLO、incidents、delivery metrics 與 unit cost
D. 改造最高成本元件，再以改造後數據推估原始 performance、reliability 與 unit cost；「改善前的 workload baseline」的 dashboard 也保留 quota/cost、alarm state 與 last validation；「改善前的 workload baseline」的 change record 另保存 scope、owner、approver 與 rollback trigger

**答案：C**

- **A：** Infrastructure inventory 與帳單可建立資產/成本起點；沒有 users、journeys、SLO 和 incidents，仍無法判斷 serverless 是否改善真正 workload outcome。
- **B：** 以 account 作 review scope 便於收集 AWS resources；一個 account 可能含多個不同 owner/journey 的 workloads，中央 cloud team 也不應替代 product owner。
- **C：** 符合本題。沒有 baseline 就無法提出可驗證的 improvement hypothesis 或判斷 side effects。
- **D：** 先改最高成本元件可能取得快速 savings；用改造後數據反推 baseline 無法區分 seasonality、需求變化與 change effect。

**事實查證：** [Well-Architected Tool milestones](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 2｜SAP｜從 Well-Architected review 到 owned plan

Well-Architected review 找到 42 個 risks。團隊把 milestone 匯出後就宣布改善完成，沒有 owner、due date 或 evidence。應如何把 review 轉成行動？

A. 保留完整 Well-Architected findings 清單，所有項目依 pillar score 排序並交由中央架構團隊處理
B. 只修分數最低的 pillar；考慮 dependencies、risk concentration 與 reversible learning
C. 把 review milestone 設為 accepted risk，於下一個季度 architecture review 依 score 變化重新排序 improvements
D. 依 business impact、risk 與 dependencies 排序，為選定 improvements 指派 owner/date/evidence，迭代實作並保存 milestones 比較變化

**答案：D**

- **A：** 保留完整 findings 並按分數排序有助可見性；全部交給中央架構團隊會忽略 workload owner、dependency 與實際 implementation authority。
- **B：** 最低分 pillar 可能集中高風險；只看 pillar score 不能比較不同 finding 的 business impact、dependency 與可逆 learning value。
- **C：** Milestone 可保存 review snapshot；把 owner/evidence review 延到下一季，會讓 42 個 risks 在期間沒有執行計畫或 closure criteria。
- **D：** 符合本題。Review 是風險發現與決策輸入；改善需要 owner、change、measurement 與 follow-up。

**事實查證：** [Well-Architected Tool milestones](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)、[Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)

### 練習題 3｜SAP｜有限 capacity 下選第一個 improvement（選兩項）

團隊只有一季容量，可選：全面 rewrite、修復未測試 backups、改漂亮 dashboard、或將高風險 public admin endpoint 私有化。哪兩個 selection principles 最合理？（選兩項）

A. 依 expected risk reduction/business value、effort、uncertainty 與 dependencies 排序，而非只看技術新穎度
B. 優先最大技術專案，因為跨季度 effort 可一次消除較多 architecture debt
C. 只依 incident count 排序，不比較 business impact、uncertainty、dependency 與 reversibility
D. 在價值相近時優先可逆、可產生下一步 evidence 的改變，例如先驗證 restore 或縮小 exposure
E. 同時啟動所有高價值 improvements；由 capacity conflict 判斷實際優先順序

**答案：A、D**

- **A：** 符合本題。Improvement portfolio 應最大化風險降低/價值，而不是均勻消耗容量。
- **B：** 大型 rewrite 可能一次消除多項 debt；只有一季 capacity 時，它的 effort/uncertainty 會排擠可立即降低 backup 或 public-access 風險的工作。
- **C：** Incident count 是重要 signal；低頻高衝擊 exposure 與尚未發生的 restore failure 會被忽略，也沒有比較 effort 和 reversibility。
- **D：** 符合本題。Reversible evidence-producing change 能降低決策不確定性並限制 blast radius。
- **E：** 同時啟動所有高價值項目可增加選擇；capacity conflict 會造成 WIP、延遲與半成品，實際上沒有做出優先序。

**事實查證：** [Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 4｜SAP｜驗證 Compute Optimizer recommendation

Compute Optimizer 建議把 memory-intensive EC2 instance 降兩個 sizes，但 CloudWatch 沒有 memory metric，觀察期也剛好是淡季。應如何處理？

A. 檢查 metric/lookback coverage、memory/external metrics、performance risk、seasonality、architecture constraints 與 price-performance，在 canary workload benchmark 後才採用
B. 將 Compute Optimizer recommendation 套用完整 fleet，依 CPU、network 與 instance-family baseline 評估 memory；「驗證 Compute Optimizer recommendation」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 決策主要依 recommendation，依平均 CPU 固定縮小 instance；涵蓋 peaks 與 seasonality
D. 依 recommendation 對完整 fleet 執行 resize，使用 Auto Scaling replacement 與 rollback alarm 控制 production performance；Rightsizing worksheet 保存 metric coverage、lookback、memory、peak season、benchmark、price-performance 與 rollback，exception expiry 與最後一次驗收時間也被保留

**答案：A**

- **A：** 符合本題。先補觀測、理解假設，再以代表性 load/canary 驗證 performance 與 savings。
- **B：** Compute Optimizer recommendation 可作 rightsizing 輸入；缺少 memory metric 且處於淡季，直接套完整 fleet 會把未知 performance risk 擴大。
- **C：** CPU/network 可以支持部分 recommendation；memory-intensive workload 的關鍵 signal 缺失，平均 CPU 不能代表 peak memory 或 seasonality。
- **D：** Production rollback 能驗證真實行為；先 resize 完整 fleet 才測試，會讓同一錯誤同時影響所有 instances，canary 更適合限制風險。

**事實查證：** [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html)、[Metrics analyzed by Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/metrics.html)

### 練習題 5｜SAP｜Config compliance 與 runtime health 邊界

AWS Config conformance pack 顯示所有 RDS instances 已加密。主管因此認為 database latency、backup restore 與 application availability 也都健康。哪個解釋正確？

A. 用 Config compliance 證明 runtime 可用性，application SLO 與 transaction tests 不再收集；Audit trail 另標示「Config compliance 與 runtime health 邊界」的設定版本、生效時間與 exception expiry
B. Config 記錄支援資源 configuration 並評估 rules；compliance 可作 policy evidence；runtime health、business transaction 與 recoverability 需其他 telemetry/tests
C. 集中收集 runtime metrics，configuration evidence 使用每月匯出的 Config snapshot 與合規摘要；Release evidence 另關聯「Config compliance 與 runtime health 邊界」的 pilot wave、result 與 rollback timestamp
D. AWS Config 對不合規 RDS 執行自動 remediation，成功條件採 rule compliance 與 API completion status；Evidence map 分開標示 Config rule result、runtime telemetry、business transaction 與 restore-test outcome，exception expiry 與最後一次驗收時間也被保留

**答案：B**

- **A：** Config compliance 能證明 encryption configuration；它不執行 application transaction、latency probe 或 restore，因此不能外推 runtime health。
- **B：** 符合本題。Config 解答『資源如何配置/是否符合規則』，不取代 monitoring、load test 或 restore test。
- **C：** Runtime metrics 加定期 Config snapshot 能分開兩種 evidence；每月 snapshot 可能無法滿足持續 configuration compliance 與 drift history。
- **D：** Config remediation 可修不合規設定；API completion 只表示 control-plane change 成功，RDS latency、availability 和 restore outcome 仍需測試。

**事實查證：** [AWS Config conformance packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html)、[AWS Config aggregators](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)

### 練習題 6｜SAP｜可證偽的 improvement hypothesis

團隊的 proposal 只有一句：『把 RDS 搬到 Aurora，因為 managed service 比較好。』哪個版本才是可驗證的 architecture hypothesis？

A. 將 p99 降低 30% 設為成功標準，觀察期採一個 deployment window，abort 由值班主管判斷
B. 以 CPU utilization 與每小時成本作 Aurora migration 的 leading metrics，customer outcome 由既有季度 business review追蹤
C. 說明 change、預期 effect、baseline、leading/guardrail metrics、observation window、cost、abort threshold 與 rollback，例如在不增加 error rate 下把 p99 降 30%
D. 先全量切換 Aurora並收集一個 billing period 的 metrics，再以觀測分布設定 hypothesis、abort threshold 與 rollback標準

**答案：C**

- **A：** p99 降低 30% 是可量測目標；缺少 baseline、error/cost guardrails、明確 observation window 與客觀 abort threshold，仍不能歸因或安全判定。
- **B：** CPU 與成本適合資源效率假設；沒有 business success、error rate 和 customer impact，可能用較低成本換來較差服務而不自知。
- **C：** 符合本題。可證偽 hypothesis 能區分真正 effect 與正常變動，並在 guardrail 破壞時停止。
- **D：** 全量部署後可收集真實資料；事後才定義 hypothesis 與 rollback 會產生 hindsight bias，也無法在 guardrail 破壞時及時停止。

**事實查證：** [AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)、[Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)

### 練習題 7｜SAP｜跨帳號可逆 rollout 與 state rollback

平台要把新 network policy 推到 300 accounts。IaC 可快速更新，但 policy 也會改變 database migration 與 queue consumers 的 access。哪個 rollout 最合理？

A. 使用 StackSets 分 waves 發布 network policy，rollback 恢復 policy stack version；database 與 queue state 由各 service owner 管理；Rollout ledger 保存 account wave、policy version、business alarm、bake time、mutable-state checkpoint 與 rollback，設定版本與生效時間一併寫入 change record
B. 使用 Firewall Manager 對 300 accounts 套用中央 network policy，account exceptions 由 delegated security administrator 核准
C. 在 organization root 套用 policy；以 CloudFormation status 與 support tickets判斷 data-plane 影響
D. 使用版本化 IaC/config，在代表 accounts pilot，設 business/health alarms 與 bake time，分 waves 擴大；rollback 同時考慮 schemas、queues、credentials 等 mutable state

**答案：D**

- **A：** StackSets 分 waves 與 policy-version rollback 都是真實機制；database migration、queue offset 和 credentials 被分散給各 owner，沒有統一 state-aware rollback gate。
- **B：** Firewall Manager 適合跨帳號集中套用支援的 network/security policies；它不替 application 驗證 database/queue access，也沒有 pilot、bake 與 mutable-state rollback。
- **C：** Root scope 可快速取得一致 policy，CloudFormation status 只證明控制面接受設定；support tickets 是落後訊號，無法量測 data-plane/business impact。
- **D：** 符合本題。Reversible rollout 需要 limited exposure、observable outcome 與完整 state-aware rollback。

**事實查證：** [AWS Firewall Manager policy scope and administration](https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html)、[CloudFormation StackSets deployment options](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 8｜SAP｜以 failure hypothesis 改善 reliability（選兩項）

架構圖有第二 Region 與 backups，但從未進行 failover/restore。團隊要證明 60 分鐘 RTO 與 15 分鐘 RPO。哪兩個行動最有價值？（選兩項）

A. 只執行 tabletop review，不在 bounded environment 觀察 detection、decision 與 recovery behavior
B. 選擇最大可信 failure mode，在 bounded scope 注入或模擬，觀察 detection、decision、recovery 與 customer impact
C. 注入 EC2 instance failure並量測 Auto Scaling replacement，RTO 以 instance 與 target-group healthy 時間計算
D. 在 production 執行完整 Region isolation experiment，abort threshold 由既有 customer SLO breach policy觸發
E. 量測實際 RTO/RPO/SLO 與 data reconciliation，更新 architecture、capacity、runbooks 與 owners

**答案：B、E**

- **A：** Tabletop 能驗證角色、決策與文件；不實際執行 bounded failover/restore，就量不到 dependency、capacity、RTO/RPO 和 reconciliation。
- **B：** 符合本題。Failure experiment 應有假設、限制、觀察與 abort conditions。
- **C：** EC2 replacement experiment 可驗證單一 compute failure；題目要證明 Region/backup recovery，instance healthy time 不是完整 application RTO。
- **D：** 完整 production fault 能取得高真實度；scope/abort threshold 應在實驗前定義，不能先造成最大 customer impact 再決定界線。
- **E：** 符合本題。測得 RTO、RPO、SLO 與 reconciliation outcome，才能判斷目標是否成立並以真實缺口驅動下一輪改善。

**事實查證：** [Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

### 練習題 9｜SAP｜realized cost savings evidence

Compute Optimizer 預估改型可省 25%，團隊把這個數字直接列為已實現 savings。Migration 有兩個月 dual-run，且新 instance 的 network transfer 增加。應如何驗證？

A. 在代表期間用 normalized demand 比較 post-change cost/performance，納入 transition 與 operational costs，確認 owner 真正停止舊支出或重新投資 savings
B. 用改造後總成本減改造前總成本；「realized cost savings evidence」的 change record 另保存 scope、owner、approver 與 rollback trigger；「realized cost savings evidence」的 dashboard 也保留 quota/cost、alarm state 與 last validation
C. 以新平台 run-rate 計算 savings，舊資源與 shared licenses 留在中央成本中心的獨立預算；Savings ledger 對齊 normalized demand、pre/post cost、dual-run、transfer、license、labor 與 retired spend，相關 alarms 與 rollback timestamp 納入 release evidence
D. 把預估 savings 記入年度目標；「realized cost savings evidence」的 change record 另保存 scope、owner、approver 與 rollback trigger；Audit trail 另標示「realized cost savings evidence」的設定版本、生效時間與 exception expiry

**答案：A**

- **A：** 符合本題。Normalized unit economics 與 cost closure 才能把 recommendation 轉成財務 evidence。
- **B：** 前後總成本比較可以估計 realized change；若沒有 demand、seasonality 和 service quality normalization，兩個期間的差異不能歸因於改型。
- **C：** 新平台 run-rate 可表示穩態潛力；舊資源、shared licenses 與 dual-run 仍在 payer bill，尚未成為公司實際 savings。
- **D：** 年度 FinOps review 可確認長期 closure；把 forecast 先列為已實現會在數月內高估 savings，也沒有納入 transition/network cost。

**事實查證：** [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html)、[Migrate from legacy CUR to Data Exports CUR 2.0](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-migrate.html)、[AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)

### 練習題 10｜SAP｜continuous architecture improvement cadence

公司每年做一次 architecture review，產出大量 findings，之後無人追蹤；失效 controls、orphaned systems 與重複 incidents 每年再出現。哪個 operating cadence 更有效？

A. 每年做一次 architecture review，期間 incidents、security findings 與 cost drift 不更新 backlog
B. 定期共同回顧 SLO、incidents、security findings、cost、technical debt 與前次 hypotheses，維護有 owner/priority/evidence 的 backlog，並移除不再有價值的 controls/systems
C. 維護 technical-debt 清單，以元件年齡排序，架構委員會每季挑選最舊項目處理
D. 每季加入回應最新 findings 的 controls 與 platforms，以年度 rationalization review 移除重複或低使用機制

**答案：B**

- **A：** 年度 review 適合慢速治理與策略調整；incidents、security findings 和 cost drift 不進入持續 backlog，風險會等到下一年才被整合。
- **B：** 符合本題。Continuous cadence 把 architecture、operations、security 與 cost evidence 連成可執行學習循環。
- **C：** Technical-debt 年齡能找長期未處理項目；最舊不一定是最高 customer/risk impact，也沒有把 SLO、incident 和 cost evidence 納入。
- **D：** 新增 controls/systems 可修正新風險；沒有 retirement criteria 會持續累積複雜度，等問題出現才判斷價值不是學習循環。

**事實查證：** [Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先建立baseline與business priority，再找最大風險、設計reversible cha…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「SAP常不是從空白設計，而是要求在最少風險下改善安全、可靠、效能與成本。」，所以「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」能直接滿足它；若constraint改成「一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」。替代方案「一次全面重寫可能消除部分技術債，但失去漸進驗證與rollback。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「SAP常不是從空白設計，而是要求在最少風險下改善安全、可靠、效能與成本。」，排除會導致「只因服務較新就遷移，沒有證明改善哪個SLO、成本或control gap。」的選項，再選「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」。本章對應的代表task包括：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先建立baseline與business priority，再找最大風險、設計reversible change並量測結果。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「continuous improvement is hypothesis-driven architecture」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
