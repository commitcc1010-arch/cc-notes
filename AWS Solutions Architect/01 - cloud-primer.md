---
title: "零背景 Cloud Primer"
part: 0
as_of: 2026-10-01
---

# Part 0　零背景 Cloud Primer

# 第 1 章　如何使用本書與雙證地圖

服務名稱很多，但考試真正要求把需求轉成可辯護的架構決策。

## 先建立共同語言：先從故事開始

故事從一個看似簡單的需求開始：同一個網站題目分別要求最低營運成本與最低延遲時，正確答案可能完全不同。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：服務名稱很多，但考試真正要求把需求轉成可辯護的架構決策。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

像第一次看城市地圖：先分清道路、地址、建築與規則，再談哪個地標最好。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Well-Architected Tool會是本章的主要角色，AWS Certification則幫我們看清邊界。方向是「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：同一個網站題目分別要求最低營運成本與最低延遲時，正確答案可能完全不同。

商業需求與不能妥協的限制
          ▼
[AWS Well-Architected Tool：主要責任]
          │ 在AWS中記錄Well-Architected reviews、milestones與improvement pl…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Certification：以公開exam guide驗證特定job role所需的AWS架構能力。
可移植原則：requirements first、service second

失敗時先找：忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問AWS Well-Architected Tool有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Well-Architected Tool和AWS Certification並不是兩個任意的產品名稱。前者適合本章，是因為「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」直接回應了眼前的問題；後者描述的「從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「requirements first、service second」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 |
| AWS Certification | 以公開exam guide驗證特定job role所需的AWS架構能力。 | Exam domains/tasks定義coverage，題目以scenario測服務選型與trade-off，而非要求背CLI語法。 |

## 把全圖套進一個具體案例

**場景：** 同一個網站題目分別要求最低營運成本與最低延遲時，正確答案可能完全不同。

1. 故事的起點：同一個網站題目分別要求最低營運成本與最低延遲時，正確答案可能完全不同。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Well-Architected Tool負責「在AWS中記錄Well-Architected reviews、milestones與improvement plans。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Certification各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Well-Architected Tool

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：服務名稱很多，但考試真正要求把需求轉成可辯護的架構決策。
- **具體例子／邊界：** 在「同一個網站題目分別要求最低營運成本與最低延遲時，正確答案可能完全不同。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Certification

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：requirements first、service second。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

## 回到 AWS：Components、功用與責任邊界

### AWS Well-Architected Tool

- **功用：** 在AWS中記錄Well-Architected reviews、milestones與improvement plans。
- **底層機制：** Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
- **關鍵設定：** workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- **選擇時機：** 需要重複、可稽核的architecture review process。
- **替換時機：** 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。

### AWS Certification

- **功用：** 以公開exam guide驗證特定job role所需的AWS架構能力。
- **底層機制：** Exam domains/tasks定義coverage，題目以scenario測服務選型與trade-off，而非要求背CLI語法。
- **關鍵設定：** exam version、domain weights、task statements、in-scope services與官方sample questions。
- **選擇時機：** 建立讀書範圍、弱點矩陣與mock review loop。
- **替換時機：** 服務實際行為仍以產品文件為準，不能把study guide當產品規格。

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

### AWS Certification：逐項設定說明

#### `exam version`

- **控制什麼：** 指定你準備的是哪一份公開考試藍圖，例如SAA-C03或SAP-C02。不同版本可能調整domain、task、服務範圍與題目深度。
- **何時需要：** 開始讀書、考試改版，或使用任何筆記與題庫以前，都要先確認版本與有效日期。
- **怎麼設定／驗證：** 從AWS Certification官方exam guide記錄exam code、發布／更新日期、domains與附錄；把本書章節及mock題映射到同一版本。
- **常見錯法：** 只寫「SAA」或「SAP」而不記exam code，容易把舊版權重、已改名服務或非本版本考點混入讀書計畫。

#### `domain weights`

- **控制什麼：** Domain是考試藍圖中的能力領域；weight是該領域約占計分內容的比例，用來分配複習時間，不是DNS網域或每次考試固定題數。
- **何時需要：** 需要排兩到三週讀書計畫，或模擬考顯示多個能力領域同時薄弱、必須決定補強順序時。
- **怎麼設定／驗證：** 把官方domain名稱與百分比抄入coverage matrix，再以「權重 × 自己的錯題率」排優先序；每週重新計算而不是平均分配時間。
- **常見錯法：** 高權重不代表只讀服務名稱；低權重也不能完全跳過。實際scenario常同時跨安全、可靠、效能與成本領域。

#### `task statements`

- **控制什麼：** Task statement把domain拆成可被情境題驗證的工作能力，例如設計安全存取、選擇migration策略或改善可靠性。
- **何時需要：** 要判斷某章或某道題到底在訓練哪種架構決策，而不是只記住答案中的服務名稱時。
- **怎麼設定／驗證：** 為每道錯題標記一個主要task與一個次要task，寫下hard constraint、正解機制與答案翻轉條件；以task覆蓋率找盲區。
- **常見錯法：** 把task statement當成固定題庫會過度擬合；同一task可由完全不同服務與產業情境出題。

#### `in-scope services`

- **控制什麼：** 表示考試可能用來描述架構情境的AWS服務集合；in scope不代表每項同深度，也不表示附錄外服務絕不出現在干擾選項。
- **何時需要：** 建立服務學習清單，決定哪些要會選型、哪些要認得整合關係與主要設定時。
- **怎麼設定／驗證：** 依官方附錄把服務映射到identity、network、compute、data、integration與operations；每項至少寫purpose、mechanism、choose、replace與一個常考設定。
- **常見錯法：** 逐項背產品型錄效率很低；服務的實際限制與設定仍應回到產品文件，不能把exam guide當完整產品規格。

#### `官方sample questions`

- **控制什麼：** 官方sample questions展示題幹長度、限制詞、複選格式與逐選項推理深度，用來校準讀題方式，不是完整題庫。
- **何時需要：** 開始準備、考試版本更新，或想檢查自己是在背答案還是真的能從constraint推出方案時。
- **怎麼設定／驗證：** 先限時作答，再為每個選項寫「滿足了什麼、漏了什麼、何時會變正解」；將錯因回填到domain/task coverage matrix。
- **常見錯法：** 只背少量sample答案會嚴重過度擬合，也不能由sample出現次數推論正式考試的服務分布。

## 讀到這裡，請用自己的話說一次

1. AWS Well-Architected Tool的責任：在AWS中記錄Well-Architected reviews、milestones與improvement plans。
2. 底層機制：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
3. 第一個要看的設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
4. 選擇邏輯：先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。
5. 不要混淆：AWS Certification的責任是「以公開exam guide驗證特定job role所需的AWS架構能力。」；它不會自動取代AWS Well-Architected Tool。
6. 替換訊號：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
7. 最常見錯法：忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。
8. 可移植原則：requirements first、service second。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 | 需要重複、可稽核的architecture review process。 | 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。 |
| AWS Certification | 以公開exam guide驗證特定job role所需的AWS架構能力。 | Exam domains/tasks定義coverage，題目以scenario測服務選型與trade-off，而非要求背CLI語法。 | 建立讀書範圍、弱點矩陣與mock review loop。 | 服務實際行為仍以產品文件為準，不能把study guide當產品規格。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。 | 只有當題目條件明確改變時才可能合理。 | 忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。」之間做選擇。
- 認得常考設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜Orientation（不計入 SAA/SAP 模擬分數）｜Purpose：先辨識 hard constraints 與優化目標

某架構題同時要求客戶資料只能留在核准地理區域、互動延遲低於 100 ms，並在符合前兩項後選擇成本最低的方案。考生開始比較 AWS 服務前，第一步應做什麼？

A. 列出所有可能出現在題目的 AWS 服務，再依功能數量排序。
B. 把資料駐留與延遲標為不可違反的限制，把成本標為通過限制後的優化目標，並圈出題目的 MOST、LEAST 等限定詞。
C. 先選自己最熟悉的服務，再調整題目解讀使其符合該服務。
D. 只比較月費最低的選項，因為成本是可量化的需求。

**答案：B**

- **A：** A 不符合情境。服務清單有助於後續比較，但未先區分硬限制與優化目標，功能較多的方案仍可能違反資料駐留；只有需求尚未明確時才適合先做廣泛探索。
- **B：** B 正確。資料位置和延遲先作為淘汰條件，成本只在合格方案間比較，能避免以某項優勢抵銷不可違反的限制，也符合情境題依限定詞做取捨的方式。
- **C：** C 不符合情境。熟悉度不是架構約束，先選服務會造成確認偏誤；它只有在多個方案同樣滿足全部需求、團隊能力被明列為營運條件時才可作次要因素。
- **D：** D 不符合情境。最低帳單若換來跨境資料或超過延遲上限便不是可接受答案；只有題目明確表示其他條件都已滿足時，才能單獨以成本決勝。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)

### 練習題 2｜Orientation（不計入 SAA/SAP 模擬分數）｜Mechanism：exam domain、task 與產品文件的分工

一名 SAP-C02 學員發現 exam guide 的 task statement 只寫「設計符合可靠性需求的策略」，卻沒有列出某資料庫的所有複寫限制。應如何正確使用這兩類資料？

A. 把 task statement 當成固定題庫，產品只會以其中的原句出現。
B. 把 in-scope service 清單視為完整產品規格，未列出的功能一律不存在。
C. 用 domain 與 task statement 定義應練習的能力和考試範圍；服務行為、設定與限制仍回到該服務的官方文件驗證。
D. 以社群筆記取代官方文件，因為社群內容通常更短。

**答案：C**

- **A：** A 錯誤。Task statement 描述能力，不是可背誦的題庫；相同能力可用不同服務與產業情境評量，只有做 coverage mapping 時才應把它當分類標籤。
- **B：** B 錯誤。官方 in-scope 清單明示為非完整清單，也不承諾產品規格；它可協助排讀書優先級，但不能判定某功能的實際支援方式。
- **C：** C 正確。Exam guide 回答「測什麼能力」，產品文件回答「服務實際怎麼運作」，兩者結合才能建立不依賴背題的可驗證推理。
- **D：** D 錯誤。社群指南可提示常見比較點，但可能過時或省略例外；它只有作為導航和靈感時合適，不能取代 AWS 官方產品行為。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)

### 練習題 3｜Orientation（不計入 SAA/SAP 模擬分數）｜Concrete setting：coverage matrix 欄位

團隊要建立一份兩週 SAA-C03 複習 coverage matrix，用來找出「服務題答對但情境題失分」的原因。哪組欄位最能支援後續診斷？

A. Exam code/version、domain/task、題目 hard constraint、錯因、正解機制、各干擾項缺口、答案翻轉條件、官方來源與重測結果。
B. 每章頁數、閱讀分鐘數與醒目標記顏色。
C. 只記服務名稱及其縮寫，避免矩陣過大。
D. 只記每次模考總分與考試日期。

**答案：A**

- **A：** A 正確。這些欄位把考試版本、能力覆蓋、約束推理和可追溯事實連在一起，能分辨知識缺口、讀題錯誤與方案比較錯誤。
- **B：** B 不足。投入時間可供排程，但不能顯示哪個 task 或 constraint 造成失分；只有用於個人時間管理時才有價值。
- **C：** C 不足。服務名稱無法說明何時選、為何不選或需求如何翻轉答案；它適合做索引，不適合作為完整診斷矩陣。
- **D：** D 不足。總分會掩蓋不同 domain、題型與錯因，只有在已另有逐題資料時才適合做趨勢摘要。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)

### 練習題 4｜Orientation（不計入 SAA/SAP 模擬分數）｜Data/request flow：Well-Architected review 工作流

一家公司要用 AWS Well-Architected Tool 對付款 workload 做可追蹤的季度審查。哪個順序最合理？

A. 由工具掃描所有資源並自動修復，之後才指定 workload owner。
B. 先建立 milestone，再決定要審查哪個 workload，最後把 milestone 當成即時監控。
C. 先匯出報告證明 data plane 正常，再略過 lens questions。
D. 定義 workload 與 owner，套用適合的 lens 並回答問題，辨識風險與 improvement items，儲存初始 milestone 作為 baseline，指派並執行改善，之後在季度審查或重大變更後再儲存 milestone 比較進展。

**答案：D**

- **A：** A 錯誤。Well-Architected Tool 是審查與追蹤工具，不會自動理解業務背景或直接修復所有資源；自動 remediation 必須由另行設計的控制實作。
- **B：** B 錯誤。Milestone 是 workload 在特定時間點的狀態快照，必須在 workload 與回答內容存在後才有意義，也不能取代 runtime metrics。
- **C：** C 錯誤。報告反映輸入的 review answers，不是 data-plane 測試證據；只有搭配實際監控、測試與營運證據才能驗證系統。
- **D：** D 正確。初次 review 完成後先保存 milestone，才能留下不可變的 baseline；改善後的後續 milestone 才能顯示風險與回答如何改變。Milestone 是時間點快照，不是即時監控，也不會代替客戶修改資源。

**事實查證：** [What is AWS Well-Architected Tool? - AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)、[Milestones - AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)

### 練習題 5｜Orientation（不計入 SAA/SAP 模擬分數）｜Failure diagnosis：情境題持續失分

一名學員對 EC2、S3、RDS 的定義題答對率達 90%，但只要題目同時出現 MOST cost-effective、RTO 和 operational overhead 就經常答錯。最有效的修正是什麼？

A. 再背一份更長的服務縮寫表。
B. 把錯題依 exam task 與 hard constraint 分類，逐項寫出每個選項違反的條件，以及哪項需求改變時答案會翻轉。
C. 只重做同一批題目直到記住正確字母。
D. 先把每題作答時間減半，不分析錯因。

**答案：B**

- **A：** A 不對症。症狀顯示學員已認得服務，但不會處理多重限制；縮寫表只有在名詞辨識本身不足時才是主要修正。
- **B：** B 正確。按 task 與 constraint 分類可把服務知識轉成方案推理，逐項解釋和答案翻轉條件則能檢查是否真的理解取捨。
- **C：** C 不理想。記住同一題字母只提高重複題表現，無法證明可遷移到新情境；重做應搭配重新推理與間隔重測。
- **D：** D 不理想。速度可能是次要問題，但在推理錯誤未修正前只會更快重複錯誤；應先提升判斷品質再做時間訓練。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)

### 練習題 6｜Orientation（不計入 SAA/SAP 模擬分數）｜Comparison：合法學習素材的不同用途

某讀書小組要建立不使用 dumps 的準備流程。以下哪項素材分工最恰當？

A. 官方 sample questions 用來校準題型與推理深度，原創 mock 用來測試遷移能力，產品官方文件用來查證行為；不得使用聲稱是真實回憶題的 dumps。
B. 官方 sample questions 可用來預測正式考試每個服務的固定出題比例。
C. 原創 mock 的解析可永久取代產品文件，即使服務行為已更新。
D. 只要來源免費，回憶的 live questions 也可當作最高品質教材。

**答案：A**

- **A：** A 正確。不同素材分別解決題型校準、陌生情境遷移與事實查證，且避免使用不合規或破壞考試完整性的 recalled questions。
- **B：** B 錯誤。少量 sample 只能展示格式和思考方式，不能推論完整題庫分布；它適合校準，不適合做頻率統計。
- **C：** C 錯誤。Mock 解析可能簡化或過時，產品限制仍須以官方文件為準；只有不涉及可變產品事實的純推理部分可獨立使用。
- **D：** D 錯誤。免費不代表合法或可靠；宣稱 actual、recalled、live 的題目不應使用，應改以原創場景和公開文件學習。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)

### 練習題 7｜Orientation（不計入 SAA/SAP 模擬分數）｜Cost/operations：有限時間的複習排序

距離 SAA-C03 考試剩十天。學員在高權重 domain 錯題率高，且這些弱點也是其他章節的先備知識。哪個時間分配方式最合理？

A. 平均分配給每一章，不考慮權重或錯題率。
B. 只讀權重最高的 domain，完全略過其他 domain。
C. 以官方 domain 權重、個人錯題率和先備依賴共同排序，同時保留跨 domain 模考、解析回讀與重測時間。
D. 十天全部做新題，不回讀任何官方來源。

**答案：C**

- **A：** A 效率較差。平均分配忽略風險差異，只有各 domain 熟練度與權重接近時才可能合理。
- **B：** B 過度集中。高權重值得優先，但情境題常跨 domain，完全跳過其他能力會留下明顯缺口。
- **C：** C 正確。這種排序把考試藍圖、個人缺口與知識依賴轉成有限時間下的投資優先級，並以回讀和重測形成閉環。
- **D：** D 不足。只做題會累積未查證的錯誤模型；新題適合檢驗遷移，但必須搭配官方文件修正事實與推理。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)

### 練習題 8｜Orientation（不計入 SAA/SAP 模擬分數）｜SAA scenario：成本與營運負擔的決勝順序

兩個候選架構都能處理目前流量。方案一月費較低，但需要團隊自行修補作業系統且單一 AZ 故障會中斷；方案二費用略高但跨 AZ 且由受管服務處理主機維護。題目要求可承受 AZ 故障，並在合格方案中選擇 least operational overhead。應如何判斷？

A. 改選 serverless 執行層，並因為沒有 guest OS patching 就假設整個 workload 已自動符合 AZ 容錯要求。
B. 只要方案標示為 managed service，就把拓撲、資料層和復原責任視為已滿足，不再檢查 failure mode。
C. 選月費最低的方案，將可用性風險留給營運團隊。
D. 先淘汰不滿足 AZ 容錯硬條件的方案，再比較剩餘方案的持續成本、管理責任與失效模式。

**答案：D**

- **A：** A 錯誤。Serverless 可移除 guest OS 工作，但不會自動修正 state、資料層或其他依賴的單 AZ 設計；只有完整 workload 都符合故障條件時才可選。
- **B：** B 錯誤。Managed 會移轉部分營運責任，但 topology、data protection 和 recovery 仍需驗證；只有服務部署模式確實滿足硬條件時才可列入比較。
- **C：** C 錯誤。單一 AZ 方案已違反明示的故障條件，較低月費不能補償硬限制；只有業務可接受 AZ 中斷時才可重新考慮。
- **D：** D 正確。架構選擇先檢查必須成立的可靠性條件，再在可行集合中比較成本和營運責任，才能回答題目的優先順序。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

### 練習題 9｜Orientation（不計入 SAA/SAP 模擬分數）｜SAP expansion：多帳號 migration 的 operating model

一個單帳號可行的應用方案要擴大成 80 個帳號的 production migration。要求可稽核、可分波回復，且不能把所有權限集中在 management account。哪兩項新增設計最重要？（選兩項）

A. 建立 delegated ownership 與 guardrails，定義各團隊責任、允許的變更邊界及稽核證據。
B. 只在第二個 Region 建立空 VPC，便可視為完成災難復原。
C. 升級 support plan，讓 AWS 代替客戶決定 rollout 和 rollback。
D. 把所有帳號的 rollout、例外核准與 rollback 權限長期集中到單一 migration team，以減少跨團隊協調。
E. 以小批次 rollout、明確成功指標和可執行 rollback runbook 遷移，保存每波結果與例外核准。

**答案：A、E**

- **A：** A 正確。多帳號規模需要清楚的決策權、不可繞過的上限和證據 owner，才能降低單一團隊或帳號的 blast radius。
- **B：** B 錯誤。空 VPC 沒有資料、容量、identity、依賴與切換驗證，不能證明任何 RTO/RPO；它只有作為已完整自動化方案的一小部分才有用。
- **C：** C 錯誤。Support 可協助事件與技術問題，但 rollout ownership、風險接受與 rollback 決策仍屬客戶 operating model。
- **D：** D 錯誤。長期集中高權限會形成瓶頸並擴大 migration 失誤的 blast radius；中央團隊可制定 guardrails，但執行權仍應委派並限制資源、時間、動作與審批。
- **E：** E 正確。分波、成功指標與 rollback evidence 讓 migration 可觀測、可停止並可復原，符合 production 變更的治理需求。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

### 練習題 10｜Orientation（不計入 SAA/SAP 模擬分數）｜Multi-response：證明理解架構取捨

讀書小組要驗收成員是否真的理解一道原創架構題，而不是記住答案。哪兩項產出最有力？（選兩項）

A. 背下正確選項的字母位置。
B. 逐一說明每個干擾項滿足了什麼、仍違反哪個情境限制。
C. 統計某個服務在練習題中出現的次數並以頻率猜答案。
D. 指出一項具體需求如何改變，會使目前的干擾項成為更好的答案。
E. 依服務月費高低建立固定答案順序。

**答案：B、D**

- **A：** A 無法證明理解。字母位置與架構機制無關，選項重排後便失效；它沒有任何合理的學習用途。
- **B：** B 正確。逐項分析能顯示成員知道服務邊界與題目 hard constraints，而不是只會為正解找理由。
- **C：** C 無法證明理解。原創題的服務頻率不是正式考試分布，也不能取代需求推理；統計只可用於檢查教材覆蓋是否失衡。
- **D：** D 正確。答案翻轉條件迫使學員說明相鄰方案何時合理，是辨識真正 trade-off 的強證據。
- **E：** E 錯誤。價格必須結合使用量、營運責任和硬限制，不能形成跨題通用排序；只有題目已固定其他因素時才可直接比較。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「服務名稱很多，但考試真正要求把需求轉成可辯護的架構決策。」，所以「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」能直接滿足它；若constraint改成「從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」。替代方案「從熟悉的服務名稱出發猜答案，只適合需求尚未出現時做初步探索。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「服務名稱很多，但考試真正要求把需求轉成可辯護的架構決策。」，排除會導致「忽略 MOST、LEAST、MINIMUM 等限制詞，會選到技術可行卻不符合題目的方案。」的選項，再選「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先圈出安全、可靠、效能、成本與營運限制，再比較符合限制的最小方案。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「requirements first、service second」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 2 章　Cloud、Region、AZ 與 Edge

工作負載需要在延遲、故障隔離、法規與資料位置之間取得平衡。

## 先建立共同語言：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：台灣使用者存取美國服務，要求低延遲且資料必須留在指定Region。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：工作負載需要在延遲、故障隔離、法規與資料位置之間取得平衡。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：CloudFront像把常用商品先放到各地分店，Global Accelerator則像把客戶快速帶上AWS的高速公路，再送往健康的區域入口。 前者理解HTTP與cache，後者主要處理network flow；兩者不是單純的快與更快。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS Regions負責主要工作，Availability Zones提醒我們答案不是永遠固定。本章會走向「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：台灣使用者存取美國服務，要求低延遲且資料必須留在指定Region。

商業需求與不能妥協的限制
          ▼
[AWS Regions：主要責任]
          │ 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Availability Zones：在同一Region內提供可彼此隔離的資料中心級failure domains。
  · Amazon CloudFront：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
  · AWS Global Accelerator：以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。
可移植原則：place state across independent failure domains

失敗時先找：把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問AWS Regions有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Regions和Availability Zones並不是兩個任意的產品名稱。前者適合本章，是因為「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」直接回應了眼前的問題；後者描述的「單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「place state across independent failure domains」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Regions | 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。 | 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。 |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 |

## 把全圖套進一個具體案例

**場景：** 台灣使用者存取美國服務，要求低延遲且資料必須留在指定Region。

1. 故事的起點：台灣使用者存取美國服務，要求低延遲且資料必須留在指定Region。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Regions負責「隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Availability Zones、Amazon CloudFront、AWS Global Accelerator各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Regions

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：工作負載需要在延遲、故障隔離、法規與資料位置之間取得平衡。
- **具體例子／邊界：** 在「台灣使用者存取美國服務，要求低延遲且資料必須留在指定Region。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Availability Zones

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：place state across independent failure domains。
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

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### listener

在load balancer指定protocol/port等待client connection的入口。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

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

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

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

### AWS Regions

- **功用：** 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。
- **底層機制：** 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。
- **關鍵設定：** Region選擇、service availability、data residency、cross-Region replication與transfer cost。
- **選擇時機：** 法規、使用者延遲、DR或服務可用性要求必須指定地理位置時。
- **替換時機：** 只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。

### Availability Zones

- **功用：** 在同一Region內提供可彼此隔離的資料中心級failure domains。
- **底層機制：** AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。
- **關鍵設定：** subnet AZ、Auto Scaling distribution、Multi-AZ、cross-zone load balancing與cross-AZ cost。
- **選擇時機：** 幾乎所有production regional workload的第一層高可用設計。
- **替換時機：** 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。

### Amazon CloudFront

- **功用：** 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
- **底層機制：** DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
- **關鍵設定：** origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- **選擇時機：** 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。
- **替換時機：** 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。

### AWS Global Accelerator

- **功用：** 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。
- **底層機制：** Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。
- **關鍵設定：** listeners、endpoint groups、traffic dial、endpoint weight、health checks與client affinity。
- **選擇時機：** 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。
- **替換時機：** HTTP內容需要cache、header/path routing或edge function時選CloudFront。

## 考前與實作時再查：設定操作手冊

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

## 讀到這裡，請用自己的話說一次

1. AWS Regions的責任：隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。
2. 底層機制：每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。
3. 第一個要看的設定：Region選擇、service availability、data residency、cross-Region replication與transfer cost。
4. 選擇邏輯：Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。
5. 不要混淆：Availability Zones的責任是「在同一Region內提供可彼此隔離的資料中心級failure domains。」；它不會自動取代AWS Regions。
6. 替換訊號：只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。
7. 最常見錯法：把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。
8. 可移植原則：place state across independent failure domains。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Regions | 隔離資料、控制合規位置，並提供跨地理區域的服務部署邊界。 | 每個Region有獨立的服務control plane、quota與多個AZ；資料通常不會自動跨Region複製。 | 法規、使用者延遲、DR或服務可用性要求必須指定地理位置時。 | 只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。 |
| Availability Zones | 在同一Region內提供可彼此隔離的資料中心級failure domains。 | AZ以低延遲私有網路互連；把副本與compute分散到AZ可抵抗單一AZ故障。 | 幾乎所有production regional workload的第一層高可用設計。 | 需要抵抗整個Region中斷或資料主權需求時，升級為Multi-Region。 |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 | 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。 | HTTP內容需要cache、header/path routing或edge function時選CloudFront。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。 | 只有當題目條件明確改變時才可能合理。 | 把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。」之間做選擇。
- 認得常考設定：Region選擇、service availability、data residency、cross-Region replication與transfer cost。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：只需抵抗單一資料中心故障時先用Multi-AZ，避免過早承擔跨Region一致性與成本。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：Region、AZ 與 edge 的責任邊界

一家媒體公司要選擇資料地理位置、抵抗單一資料中心級故障，並加速全球使用者讀取公開影片縮圖。哪個敘述正確區分 Region、Availability Zone（AZ）與 edge location？

A. AZ 是跨國資料駐留邊界；Region 只是同一機房內的網段。
B. Edge location 是關聯式資料庫 primary，負責保存權威交易資料。
C. Region 是地理與服務部署邊界，AZ 是 Region 內的獨立故障域，edge location 則讓快取或入口更靠近使用者。
D. 只要服務部署在一個 Region，所有資源就會自動跨所有 AZ。

**答案：C**

- **A：** A 錯誤。Region 才是主要地理部署邊界，AZ 是 Region 內隔離的位置；只有討論區域內 placement 時才以 AZ 為單位。
- **B：** B 錯誤。Edge 可承載 CDN 快取或全球入口，但不自動成為應用的權威資料庫；權威 state 仍需由所選 Region 內的資料服務設計。
- **C：** C 正確。三者分別處理地理範圍、區域內故障隔離和使用者就近存取，不能互相替代。
- **D：** D 錯誤。跨 AZ 行為取決於服務與部署設定；EC2、EBS 等資源具有明確的 AZ placement，客戶仍須建立多 AZ 架構。

**事實查證：** [Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)、[How CloudFront delivers content - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)

### 練習題 2｜SAA｜Mechanism：CloudFront cache hit/miss

全球使用者透過 CloudFront 讀取同一個公開靜態物件。哪個流程最準確描述正常的 cache hit 與 miss？

A. Viewer 被導向 edge；edge 以 cache key 尋找仍新鮮的物件，hit 時直接回應，miss 時依 behavior 和 origin policy 回源並快取符合規則的回應。
B. 每次請求都直接到 origin，CloudFront 只修改 DNS 名稱而不保存內容。
C. CloudFront 會把 origin 的關聯式資料庫複寫成全球 multi-writer。
D. Global Accelerator 先把 HTTP object 快取後再交給 CloudFront。

**答案：A**

- **A：** A 正確。Cache key 決定可重用的變體，TTL 與回應指示影響新鮮度；只有 miss 或過期時才需要依設定回源。
- **B：** B 錯誤。停用快取或 TTL 為零時可能接近每次回源，但正常 CDN 行為包含 edge cache，不能把它只當 DNS 別名。
- **C：** C 錯誤。CloudFront 快取 HTTP 回應，不提供資料庫交易複寫或衝突處理；全球資料庫必須另選資料服務。
- **D：** D 錯誤。Global Accelerator 不提供 object cache，它加速 TCP/UDP 路徑；只有需要固定 anycast IP 或非快取流量時才可能與 CloudFront 分開選用。

**事實查證：** [Understand the cache key - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[How CloudFront delivers content - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[What is AWS Global Accelerator? - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)

### 練習題 3｜SAA｜Concrete setting：CloudFront cache key

同一個 URL 會依 `language` cookie 回傳英文或中文，但 `tracking_id` query string 只供 origin 記錄，不改變內容。為避免語言內容互相污染又維持高 cache hit ratio，應如何設定？

A. 把所有 headers、cookies 和 query strings 全部加入 cache key。
B. 不把任何 viewer 值加入 cache key，讓所有人共用同一物件。
C. 只調整 Route 53 health-check interval。
D. 在 cache policy 將 `language` cookie 納入 cache key；若 origin 需要 `tracking_id`，可由 origin request policy 轉送而不讓它切分 cache object。

**答案：D**

- **A：** A 可避免部分污染但會讓不影響內容的值建立大量變體，降低 hit ratio；只有所有轉送值都確實改變回應時才合適。
- **B：** B 會讓不同語言共用同一快取物件，直接違反回應語意；只有 origin 對所有 viewer 都回相同內容時才可使用。
- **C：** C 無關。Route 53 健康檢查不決定 CloudFront cache key，也不會分隔 cookie 變體。
- **D：** D 正確。影響內容的語言值必須進 cache key，不影響內容但需回源的 tracking 值可只轉送，兼顧正確性與重用率。

**事實查證：** [Understand the cache key - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)

### 練習題 4｜SAA｜Data/request flow：edge 與資料駐留

醫療入口網站的權威病歷資料必須保留在核准 Region；全球使用者仍希望快速下載公開說明文件。哪個資料流設計最符合兩項要求？

A. 把所有病歷 API 回應設定長 TTL，讓全球 edge 長期保存敏感資料。
B. 讓權威病歷 store 與動態 origin 留在核准 Region，只讓經資料分類核准的公開靜態內容由 CloudFront edge 快取。
C. 因為使用 edge 一定會把整個 database 搬出 Region，所以完全不能使用 CloudFront。
D. 把單一 Region 的 Multi-AZ 部署視為全球 edge network。

**答案：B**

- **A：** A 錯誤。敏感回應是否可被 edge 保存必須由資料分類、cache policy 和法規決定，不能為延遲犧牲駐留要求。
- **B：** B 正確。此設計把權威敏感 state 固定在核准 Region，同時僅將允許複製的公開內容送往 edge。
- **C：** C 過度推論。CloudFront 只快取或代理被請求的 HTTP 內容，不會自動搬移整個資料庫；禁用快取的動態路徑仍可回到核准 origin。
- **D：** D 錯誤。Multi-AZ 解決 Region 內故障隔離，不提供全球 edge cache；只有區域高可用需求時可單獨使用。

**事實查證：** [Understand the cache key - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[How CloudFront delivers content - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

### 練習題 5｜SAA｜Failure diagnosis：instance 數量不等於 failure-domain 數量

一個 Web 服務有三台 EC2 執行個體和一個 Application Load Balancer，但三台執行個體都在同一個 AZ。該 AZ 中斷時服務全部失效。根因與主要修正是什麼？

A. DNS TTL 太高；把 TTL 改成 1 秒即可抵抗 AZ 故障。
B. 執行個體規格太小；把三台換成同 AZ 的一台大型執行個體。
C. 容量副本沒有跨獨立故障域；應把 compute 分散到至少兩個 AZ，並確認 state 與其他依賴也具相符的多 AZ 設計。
D. Subnet 太多；合併成一個更大的單 AZ subnet。

**答案：C**

- **A：** A 錯誤。TTL 影響 DNS cache，不會把執行個體移到其他 AZ，也不能恢復同一 AZ 內失效的所有 targets。
- **B：** B 會進一步集中故障風險。垂直擴展只在單機容量不足時有用，不能修正 failure-domain 集中。
- **C：** C 正確。三個同 AZ 副本共享同一故障域，必須跨 AZ 放置可替換容量，且資料與依賴不能仍是單 AZ 單點。
- **D：** D 錯誤。Subnet 本來就是單 AZ 資源，合併不會增加可用性；應建立不同 AZ 的 subnets 供負載平衡與 Auto Scaling 使用。

**事實查證：** [Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 6｜SAA｜Comparison：CloudFront 與 Global Accelerator

公司有兩種 workload：即時遊戲使用 UDP 且企業客戶要求固定入口 IP；行銷網站需要快取靜態內容並在 edge 套用 Web 防護。哪個配對最恰當？

A. 兩者都只用 Route 53 simple routing，因為 DNS 能快取 HTTP objects 並代理 UDP。
B. 遊戲使用 AWS Global Accelerator；網站使用 Amazon CloudFront。
C. 遊戲使用 CloudFront；網站使用 Global Accelerator object cache。
D. 兩者都使用 S3 Transfer Acceleration，因為它提供任意 TCP/UDP 入口。

**答案：B**

- **A：** A 錯誤。Route 53 回答 DNS 查詢，不代理後續 UDP 連線或快取 HTTP body；它可作名稱與流量政策的一部分。
- **B：** B 正確。Global Accelerator 提供 static anycast IP 與 TCP/UDP 全球路徑；CloudFront 提供 HTTP edge cache 並可整合 WAF。
- **C：** C 顛倒責任。CloudFront 不接受一般遊戲 UDP，Global Accelerator 也不保存 object cache。
- **D：** D 錯誤。S3 Transfer Acceleration 是 S3 object transfer 功能，不是通用遊戲入口或完整網站 CDN。

**事實查證：** [Understand the cache key - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[How CloudFront delivers content - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[What is AWS Global Accelerator? - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)

### 練習題 7｜SAA｜Cost/operations：Multi-AZ 與 Multi-Region

一個區域性內部系統只要求在單一 AZ 故障時繼續服務，資料契約也禁止跨 Region 複寫。哪個理由最支持先採 Multi-AZ 而不是 Multi-Region？

A. Multi-AZ 可保證抵抗任何整個 Region 的中斷。
B. 單 AZ 加每日 backup 與 Multi-AZ 具有相同即時可用性。
C. 跨 Region 複寫不會增加資料傳輸、治理或測試成本。
D. Multi-AZ 直接對應所需故障範圍；Multi-Region 會引入不需要且可能違規的資料複寫、切換、營運與傳輸複雜度。

**答案：D**

- **A：** A 錯誤。Multi-AZ 仍位於同一 Region，不能宣稱抵抗所有 Regional events；需要 Region resilience 時才評估 Multi-Region。
- **B：** B 錯誤。Backup 支援時間點恢復，但通常不能在 AZ 失效時立即承接流量；它仍是必要資料保護層，而非 HA 替代品。
- **C：** C 錯誤。跨 Region 常伴隨複寫、KMS、identity、測試、傳輸與一致性成本，必須納入架構決策。
- **D：** D 正確。設計應匹配明示 failure scope；在只需 AZ resilience 且禁止跨區資料時，Multi-AZ 通常是較小且合規的方案。

**事實查證：** [Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 8｜SAA｜SAA scenario：單一合規 Region 的高可用架構

區域性電商要求單一 AZ 故障時網站不中斷、資料不得跨出指定 Region，且希望最少主機維護。哪個高階方案最符合需求？

A. 在核准 Region 內使用跨至少兩個 AZ 的 load-balanced compute，搭配符合應用語意的 Multi-AZ 資料層。
B. 在一個 AZ 建立較大的 Auto Scaling group，因為 Auto Scaling group 名稱包含 scaling。
C. 在兩個 Region 各放一台執行個體，但不複寫資料或設計切換。
D. 只在網站前加入 CloudFront，不改單 AZ origin 與 database。

**答案：A**

- **A：** A 正確。Compute 與 state 都留在核准 Region，並跨 AZ 消除同一故障域，受管資料層也可降低主機維護。
- **B：** B 錯誤。同 AZ 的 Auto Scaling 只能補容量或替換 instance，AZ 故障仍會同時失去整個 fleet。
- **C：** C 錯誤。它違反單 Region 資料邊界，且沒有資料與流量切換便不是可用的多 Region 設計。
- **D：** D 不足。CloudFront 可緩衝部分可快取內容，但 origin 與資料層仍是單 AZ，動態交易仍會中斷。

**事實查證：** [Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 9｜SAP｜SAP expansion：跨 Region active/passive 驗證

公司設計跨 Region active/passive API。切換前除了確認 secondary stack 已部署，還必須優先驗證哪兩組事項？（選兩項）

A. 只確認 secondary Region 有空 VPC 和 subnet；資料與服務容量可在事故後再想。
B. 持續量測資料複寫 lag，驗證 recovery Region 的 KMS、identity、quota、依賴和足夠服務容量。
C. 只把 DNS TTL 降到 1 秒，便可視為所有 client 都會立即切換。
D. 只複製 AMI；database、secrets、certificates 和外部依賴不屬 DR 範圍。
E. 以 game day 演練 entry-point 切換、fencing、business transaction 驗證、rollback 與 failback runbook。

**答案：B、E**

- **A：** A 不足。空網路不代表可恢復 workload；它只有在資料、identity、容量與部署都由完整 automation 建立時才是基礎元件。
- **B：** B 正確。Secondary 必須能讀到足夠新且可解密的資料，並具備實際啟動和承載 workload 的 dependencies 與配額。
- **C：** C 錯誤。Resolver/client cache、舊 TTL 和既有連線不保證瞬時改向，DNS 也不修正資料或容量問題。
- **D：** D 錯誤。AMI 只涵蓋部分 compute artifact；完整服務還依賴資料、密鑰、憑證、DNS、網路和第三方系統。
- **E：** E 正確。只有經過切換、交易驗證和回復演練，才能證明 runbook、健康訊號與 operating model 可達成目標。

**事實查證：** [Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)、[What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)

### 練習題 10｜SAP｜Multi-response：資料駐留與全球低延遲控制

受規範網站要求個人資料只能在核准 Region 儲存與處理；全球訪客仍要快速取得不含個人資料的公開產品圖片。哪兩項資料流設計可共同滿足需求？（選兩項）

A. 將 PII API 的 DNS hostname 與資料流直接導向核准 Region 的 regional endpoint，不經 CloudFront；權威資料、動態處理、logs 與備份也留在該 Region。
B. 把所有含個人資料的回應設為一年 TTL，降低 origin 負載。
C. 為公開圖片使用獨立 hostname 與 CloudFront distribution，只允許已分類為非敏感的靜態物件進入 edge cache。
D. 以 Global Accelerator 取代 database 複寫與資料分類。
E. 假設 edge cache 不受資料治理要求約束，因此不用記錄快取內容。

**答案：A、C**

- **A：** A 正確。若規範限制的不只是持久副本，還包含 request processing，PII API 就不能先到全球 edge 再回源；regional endpoint、regional logs 與資料服務必須共同留在核准邊界。
- **B：** B 錯誤。長 TTL 會把敏感內容複製並延長暴露，不符合明示資料限制；只有公開且可長期重用的內容才適合。
- **C：** C 正確。把公開資產與 PII API 分成不同 hostname 和 distribution boundary，可讓非敏感圖片在 edge 加速，同時避免個人資料 request 進入 CloudFront POP。
- **D：** D 錯誤。Global Accelerator 處理網路入口與路徑，不保存權威資料、執行資料分類或建立 database replication。
- **E：** E 錯誤。Edge 收到 request、終止連線、記錄欄位或執行 edge function 都可能構成處理；「不快取」只限制 cache copy，不能證明資料從未在 edge 被處理。

**事實查證：** [How CloudFront delivers content - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[Data protection in Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/data-protection-summary.html)、[Regions and Zones - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「工作負載需要在延遲、故障隔離、法規與資料位置之間取得平衡。」，所以「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」能直接滿足它；若constraint改成「單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」。替代方案「單一AZ部署較便宜且簡單，只適合能接受該AZ中斷的非關鍵工作。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「工作負載需要在延遲、故障隔離、法規與資料位置之間取得平衡。」，排除會導致「把多台EC2放在同一AZ誤認為高可用，AZ故障時仍會一起失效。」的選項，再選「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Region決定地理與服務邊界，AZ提供獨立故障域，edge將內容或入口靠近使用者。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「place state across independent failure domains」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 3 章　Server、VM、Container 與 Serverless

不同執行模型把不同程度的OS、runtime與容量責任交給供應商。

## 先建立共同語言：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：團隊要搬移一個長時間執行的Java服務，另有每分鐘少量圖片縮圖事件。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：不同執行模型把不同程度的OS、runtime與容量責任交給供應商。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：像第一次看城市地圖：先分清道路、地址、建築與規則，再談哪個地標最好。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon EC2，對照角色是Amazon ECS。我們選擇「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：團隊要搬移一個長時間執行的Java服務，另有每分鐘少量圖片縮圖事件。

工作抵達
  ├─ 需要完整OS／driver／長時間process ──> VM / EC2
  ├─ 需要封裝與可攜、仍是長時間服務 ────> Container / ECS / EKS
  └─ 短時間、事件驅動、流量高度變動 ────> Serverless / Lambda

共同問題：image從哪來？state放哪裡？如何scale？失敗後誰重啟？
選擇越高階的抽象，主機管理越少；但可控制的OS與runtime細節也越少。

失敗時先找：只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon EC2有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EC2和Amazon ECS並不是兩個任意的產品名稱。前者適合本章，是因為「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」直接回應了眼前的問題；後者描述的「EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「choose the highest abstraction that still exposes required control」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 團隊要搬移一個長時間執行的Java服務，另有每分鐘少量圖片縮圖事件。

1. 故事的起點：團隊要搬移一個長時間執行的Java服務，另有每分鐘少量圖片縮圖事件。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EC2負責「提供可控制OS、runtime、network與storage的虛擬機compute。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon ECS、Amazon EKS、AWS Fargate、AWS Lambda各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon EC2

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：不同執行模型把不同程度的OS、runtime與容量責任交給供應商。
- **具體例子／邊界：** 在「團隊要搬移一個長時間執行的Java服務，另有每分鐘少量圖片縮圖事件。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon ECS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：choose the highest abstraction that still exposes required control。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### temporary credentials

具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### cold start

Serverless/container在沒有可重用execution environment時建立runtime的額外延遲。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon EC2

- **功用：** 提供可控制OS、runtime、network與storage的虛擬機compute。
- **底層機制：** Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
- **關鍵設定：** instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- **選擇時機：** 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。
- **替換時機：** 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。

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

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

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

1. Amazon EC2的責任：提供可控制OS、runtime、network與storage的虛擬機compute。
2. 底層機制：Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
3. 第一個要看的設定：instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
4. 選擇邏輯：依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。
5. 不要混淆：Amazon ECS的責任是「以AWS原生control plane排程與維護containers。」；它不會自動取代Amazon EC2。
6. 替換訊號：只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。
7. 最常見錯法：只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。
8. 可移植原則：choose the highest abstraction that still exposes required control。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 | 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。 | 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。 |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 | 團隊要container但不需要Kubernetes API與生態相容性時。 | 既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 | 需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。 | 不需要Kubernetes複雜度時以ECS降低營運；單一事件handler可用Lambda。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 | bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。 | 穩定高利用率或需GPU、特殊daemon/host access時改用EC2-backed ECS/EKS。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。 | 只有當題目條件明確改變時才可能合理。 | 只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。」之間做選擇。
- 認得常考設定：instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- 對應官方tasks：SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：選擇 compute abstraction 的條件

一個架構師要在 EC2、containers 和 Lambda 之間選擇。Workload 包含需要核心驅動程式的長期 daemon、可攜式封裝需求，以及事件到達後執行 20 秒的無狀態工作。第一組應收集的決策資料是什麼？

A. 只比較團隊使用的程式語言。
B. 只計算每天處理的資料總 GB。
C. 先以 Lambda 作共同執行標準，等部署後真的遇到 host access 或執行時間限制再重構。
D. 確認 OS/driver 控制、封裝與可攜性、工作持續時間、事件模型、啟動與延遲要求，以及團隊可承擔的營運責任。

**答案：D**

- **A：** A 不足。同一語言可執行在 VM、container 或 function，語言只有在 runtime 相容性被明列時才會排除選項。
- **B：** B 不足。資料量可能影響容量，但不能判斷是否需要 host access、長期 process 或事件驅動；它是 sizing 輸入而非首要 abstraction 邊界。
- **C：** C 錯誤。題目已知存在 driver 與長期 daemon 需求，延後處理會造成可預見的重構；只有所有工作都落在 Lambda 的 execution contract 內才適合先統一。
- **D：** D 正確。這些條件直接決定工作需要暴露多少底層控制，以及 VM、orchestrated container 或 function 的執行模型是否相符。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)、[What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)

### 練習題 2｜SAA｜Mechanism：ECS service、task definition 與 Fargate

團隊要在 Amazon ECS 上持續執行六個相同的 container tasks，但不想管理 EC2 nodes。哪個敘述正確描述元件分工？

A. Fargate 取代 container image，因此不再需要 registry 或 task definition。
B. Task definition 描述 image、CPU、memory、ports 和 roles；ECS service scheduler 維持期望 task 數量；Fargate 提供不需客戶管理 nodes 的執行容量。
C. ECS 是 VM hypervisor，task definition 會自動建立應用的關聯式資料庫。
D. Fargate 是獨立於 ECS/EKS 的第三種 container orchestrator。

**答案：B**

- **A：** A 錯誤。Fargate 提供 compute capacity，不保存應用 image 或 workload 規格；container image 和 task definition 仍是部署輸入。
- **B：** B 正確。ECS 負責排程與 desired state，task definition 是 workload 契約，Fargate 則移除客戶維護 worker fleet 的工作。
- **C：** C 錯誤。ECS 是 container orchestration control plane，不是 EC2 hypervisor，也不會根據 task definition 自動推導 durable database。
- **D：** D 錯誤。Fargate 是 ECS tasks 或 EKS pods 的 serverless compute 選項，不是另一套 scheduler。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[AWS Fargate for Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

### 練習題 3｜SAA｜Concrete setting：ECS task role 與 execution role

ECS Fargate task 啟動時要從 Amazon ECR 拉取 image 並把 logs 傳到 CloudWatch Logs；啟動後的應用程式還要讀取特定 DynamoDB table。最小權限角色分工應如何設定？

A. Execution role 允許 ECS/Fargate agent 拉 image 和寫 logs；task role 只允許應用程式對指定 DynamoDB table 執行必要 API。
B. 把所有權限只給 execution role，應用程式會自動取得相同 credentials。
C. Task role 只控制 security group；execution role 提供終端使用者登入權限。
D. 把部署者的長期 access key 放進 image，兩種 role 都不需要。

**答案：A**

- **A：** A 正確。平台啟動動作使用 task execution role，container 內應用呼叫 AWS API 時使用 task role，分離後可各自實作 least privilege。
- **B：** B 錯誤。Execution role 供 ECS agent 執行啟動工作，容器應用不應依賴它取得業務 API 權限；只有平台動作才放在此角色。
- **C：** C 錯誤。Security group 是網路控制，與 IAM role 分工不同；終端使用者也不應透過 task execution role 登入。
- **D：** D 錯誤。Image 中的長期 key 難以輪替、容易外洩且破壞可稽核性；workload role 才能提供臨時 credentials。

**事實查證：** [Best practices for IAM roles in Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-iam-roles.html)

### 練習題 4｜SAA｜Data/request flow：API Gateway、Lambda 與 DynamoDB credentials

Public API 由 API Gateway 呼叫 Lambda，Lambda 再把訂單寫入 DynamoDB。沒有在程式碼中保存 access key。哪個 request 與授權流程正確？

A. Lambda 使用部署工程師當天登入 console 的 credentials 呼叫 DynamoDB。
B. Lambda execution environment 是 durable queue，因此事件一定永久保留在函式記憶體。
C. API Gateway 將 event 交給 Lambda execution environment；函式透過其 execution role 的臨時 credentials 呼叫 DynamoDB，再把結果交回 API 層。
D. Lambda 必須放進 VPC 才能呼叫任何 AWS public service API。

**答案：C**

- **A：** A 錯誤。部署者 identity 不應成為 runtime identity；Lambda execution role 為函式提供可稽核的臨時權限。
- **B：** B 錯誤。Execution environment 可能重用但不是可靠訊息保存層；需要耐久緩衝時應使用 SQS、stream 或其他事件來源。
- **C：** C 正確。API 事件、函式執行身份和 DynamoDB API authorization 是三個清楚交接，回應再沿 API 整合返回 client。
- **D：** D 錯誤。Lambda 不在 VPC 也可呼叫 AWS public endpoints；放入 VPC 是為了存取私有資源或控制網路路徑，並非所有 API 的先決條件。

**事實查證：** [What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)、[Defining Lambda function permissions with an execution role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)、[Set up Lambda proxy integrations in API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)、[Enable internet access for VPC-connected Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc-internet.html)

### 練習題 5｜SAA｜Failure diagnosis：Lambda throttling 與下游飽和

促銷時 Lambda `Throttles` 增加，同時 RDS 連線數達上限。團隊準備直接移除 reserved concurrency 並申請更高帳號 concurrency。哪個診斷與修正方向最好？

A. 只增加 Lambda memory；memory 一定會降低 database connection 數。
B. 取消所有 concurrency 限制，讓 Lambda 比 database 更快擴展。
C. 改成相同數量 EC2，無須測量 arrival rate 或下游 capacity。
D. 量測 arrival rate、duration、函式 concurrency 和 DB 可承受連線，保留能隔離與保護下游的 concurrency 上限，必要時以 queue、connection pooling 或 backpressure 緩衝。

**答案：D**

- **A：** A 不充分。增加 memory 可能縮短 duration，但不保證改變每次 invocation 的連線模式；只有經量測證明 duration 是主要因素時才可採用。
- **B：** B 危險。上游無限制擴展會讓已飽和的 database 更快失效；reserved concurrency 可同時隔離函式和限制下游壓力。
- **C：** C 缺乏證據。換執行模型可能有其他好處，但相同 arrival rate 和連線設計仍可壓垮 database，必須先找出容量契約。
- **D：** D 正確。問題跨越 Lambda concurrency 與 downstream capacity，應以量測建立安全吞吐並加入緩衝或連線管理，而非只抬高上限。

**事實查證：** [Understanding Lambda function scaling - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)、[Using Lambda with Amazon RDS](https://docs.aws.amazon.com/lambda/latest/dg/services-rds.html)、[Configuring scaling behavior for SQS event source mappings](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)

### 練習題 6｜SAA｜Comparison：EKS 與 ECS 的 operating model

團隊 A 已有 Kubernetes operators、portable manifests 和成熟的 cluster 升級流程；團隊 B 只需在 AWS 排程一般 containers，沒有 Kubernetes 經驗並希望降低 control-plane 複雜度。哪個建議最合理？

A. 團隊 A 選 EKS 以保留 Kubernetes API/ecosystem；團隊 B 選 ECS，除非出現必須使用 Kubernetes 的需求。
B. 兩個團隊都選 EKS 以統一平台，並假設工具一致性的收益足以抵銷團隊 B 的學習與 cluster operations 成本。
C. 團隊 A 選 ECS，因為 ECS 可直接執行所有 Kubernetes CRDs。
D. 團隊 B 只選 Fargate；Fargate 本身會取代 scheduler 和 service deployment。

**答案：A**

- **A：** A 正確。平台選擇應匹配既有 API、工具鏈和營運能力；不需要 Kubernetes contract 時，ECS 可減少不必要的複雜度。
- **B：** B 錯誤。統一平台可能有治理價值，但題目未給出足以抵銷 Kubernetes 複雜度的共同需求；若企業已有集中 EKS 平台團隊，這個取捨才可能改變。
- **C：** C 錯誤。ECS 不提供 Kubernetes API 或原生執行 CRDs；只有 workload 不依賴 Kubernetes contract 時才能改寫後遷移。
- **D：** D 錯誤。Fargate 提供 task/pod capacity，仍需 ECS 或 EKS 進行 orchestration。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)

### 練習題 7｜SAA｜Cost/operations：steady 與 bursty compute

Workload X 是 24×7、可預測且長期高 CPU 利用率的 container service；Workload Y 每天只有數次、每次 15 秒的事件工作。哪個成本與營運分析最完整？

A. 兩者都使用按工作量計費的 Fargate，以省去 node operations；不另外比較 X 的長期高利用率與承諾折扣。
B. X 可評估 EC2-backed container fleet 與承諾折扣；Y 可評估 Lambda 或 Fargate，以避免長時間 idle 和 node operations，並以實際用量與營運成本驗證。
C. 兩者都配置可涵蓋峰值的 EC2 fleet 並購買承諾折扣，將 Y 的長時間 idle 視為簡化平台的固定成本。
D. 只比較每 vCPU 秒價格，不計 idle、啟動時間、平台費與 on-call。

**答案：B**

- **A：** A 不完整。Fargate 可減少 node operations，但 X 幾乎沒有 idle，仍應比較 EC2-backed capacity、折扣與平台人力；若團隊無力維護 nodes，Fargate 才可能以營運收益勝出。
- **B：** B 正確。方案把 duty cycle、可預測性、承諾折扣和營運責任一併納入，並允許用量資料決定最終選擇。
- **C：** C 不完整。EC2 可適合 steady workload，但 Y 會產生大量 idle；只有統一平台的營運收益或事件執行限制大於 idle 成本時，這個方案才可能合理。
- **D：** D 不完整。單位 compute 價格忽略 idle、擴縮、patch、control-plane 和人力，容易得到錯誤總成本。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)、[What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)、[What are Savings Plans?](https://docs.aws.amazon.com/savingsplans/latest/userguide/what-is-savings-plans.html)、[AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)

### 練習題 8｜SAA｜SAA scenario：長期 daemon 與短事件工作的組合

公司要搬移兩個工作：第一個是持續執行的 Java daemon，必須安裝特定 OS agent 並開啟長連線；第二個是在圖片上傳後執行 20 秒縮圖，流量高度不規則。哪個組合最符合需求？

A. 兩者都用 Lambda，並忽略 daemon 的持續執行與 OS agent。
B. 兩者都用 Dedicated Hosts，即使縮圖大部分時間沒有工作。
C. Daemon 使用 EC2 或具適當 host control 的 container capacity；縮圖使用事件觸發的 Lambda。
D. 縮圖一定使用 EKS，因為 container 可攜性比所有其他條件更重要。

**答案：C**

- **A：** A 錯誤。Lambda 適合短事件工作，但不滿足持續 daemon、特殊 OS agent 與長期 connection 的控制需求。
- **B：** B 過度配置。Dedicated Host 可處理特定授權或隔離需求，但題目未要求，且對低 duty-cycle 縮圖造成不必要 idle 成本。
- **C：** C 正確。兩個 workload 分別選擇能暴露必要控制和能按事件快速擴縮的執行模型。
- **D：** D 錯誤。EKS 只有在 Kubernetes API/ecosystem 是需求時才有充分理由；單一短事件函式不需要 cluster 複雜度。

**事實查證：** [What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)、[Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)

### 練習題 9｜SAP｜SAP expansion：大型 container 平台 operating model

企業要讓數十個應用團隊跨帳號使用標準 container 平台，同時限制 blast radius 並可分波升級。哪兩項平台設計最重要？（選兩項）

A. 所有 clusters 與 applications 共用一個永久 cluster-admin role。
B. 允許每個團隊任意選 image registry、base image 和掃描流程，不建立共同供應鏈。
C. 分離平台與應用 ownership，為 workload identity、network policy、capacity、quota 和 cluster/service upgrades 定義支援邊界。
D. 只建立第二 Region，便可取代 image provenance、變更治理和 rollback。
E. 建立版本化的 image supply chain 與平台基線，使用 canary/分波升級、相容性測試和可回復的 rollout evidence。

**答案：C、E**

- **A：** A 錯誤。共享永久管理員權限會讓單一 credential 或操作影響全部平台；緊急存取也應短期、可稽核且限 scope。
- **B：** B 錯誤。無共同供應鏈會讓漏洞、來源和 patch 狀態不可追蹤；團隊可保有應用 ownership，但 artifact contract 必須一致。
- **C：** C 正確。清楚責任與平台 contract 能讓團隊自治，同時避免身份、網路、容量和升級問題無 owner。
- **D：** D 錯誤。第二 Region 只處理部分 failure scope，不能取代日常治理、供應鏈和 deployment safety。
- **E：** E 正確。版本化基線與分波 rollout 把大規模變更切成可觀測、可停止並可回復的單位。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)

### 練習題 10｜SAA｜Multi-response：Fargate 的客戶責任

團隊把 ECS workload 從 EC2 launch type 改到 AWS Fargate。哪兩項仍由客戶負責？（選兩項）

A. 修補承載 task 的 AWS 實體主機作業系統。
B. 設定 task CPU/memory、subnets、security groups、task role 與應用所需的網路路徑。
C. 配置底層 hypervisor 與主機 kernel。
D. 維護 application/container image、依賴漏洞、資料保護與應用程式正確性。
E. 管理 Fargate 供應容量的實體 server fleet。

**答案：B、D**

- **A：** A 不由客戶負責。Fargate 將底層 host patching 交給 AWS；只有改回 EC2-backed capacity 時客戶才管理 worker OS。
- **B：** B 正確。Fargate 不會替 workload 決定 sizing、identity 或 network exposure，這些仍是應用架構設定。
- **C：** C 不由客戶負責。Hypervisor 與 host kernel 屬 Fargate 基礎設施，客戶只選擇公開的 platform 與 task 設定。
- **D：** D 正確。Serverless container 不會修正客戶 code、image packages、secret 使用或資料分類，這些責任保持不變。
- **E：** E 不由客戶負責。Fargate 的核心價值正是移除客戶建立與修補 capacity fleet 的工作。

**事實查證：** [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)、[AWS Fargate for Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)、[Best practices for IAM roles in Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-iam-roles.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「不同執行模型把不同程度的OS、runtime與容量責任交給供應商。」，所以「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」能直接滿足它；若constraint改成「EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」。替代方案「EC2提供最大控制；container適合封裝既有服務；serverless適合事件驅動與變動流量。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「不同執行模型把不同程度的OS、runtime與容量責任交給供應商。」，排除會導致「只因為serverless不用管理server就忽略timeout、concurrency、cold start與依賴限制。」的選項，再選「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」。本章對應的代表task包括：SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「依控制需求、啟動時間、工作持續時間、可攜性與營運能力選擇抽象層。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「choose the highest abstraction that still exposes required control」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 4 章　IP、CIDR、Subnet 與 Route 基礎

網路設計必須先回答地址是否重疊、封包往哪裡走，以及回程是否存在。

## 先建立共同語言：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：兩個VPC需要互連，但都使用10.0.0.0/16，且on-premises也有重疊地址。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：網路設計必須先回答地址是否重疊、封包往哪裡走，以及回程是否存在。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，VPC像一座園區，subnet是不同街區，route table是每個路口的指示牌，Internet Gateway則是通往公共道路的出口。 街區叫private不會產生魔法；是否能上網仍由有效route、public address與安全規則共同決定。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon VPC如何接手工作，再看Route tables何時更合適，最後用設定與考題驗證「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：兩個VPC需要互連，但都使用10.0.0.0/16，且on-premises也有重疊地址。

商業需求與不能妥協的限制
          ▼
[Amazon VPC：主要責任]
          │ 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Route tables：決定subnet或gateway流量的下一跳。
  · Subnets：把VPC CIDR切成單一AZ內的IP與路由邊界。
  · CIDR：用prefix長度定義IP位址範圍，決定可用位址與route匹配粒度。
可移植原則：connectivity = name resolution + forward path + return path + policy

失敗時先找：只檢查source到destination的路徑，漏掉return route、DNS或stateful device。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon VPC有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon VPC和Route tables並不是兩個任意的產品名稱。前者適合本章，是因為「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」直接回應了眼前的問題；後者描述的「用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只檢查source到destination的路徑，漏掉return route、DNS或stateful device。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「connectivity = name resolution + forward path + return path + policy」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 |
| Route tables | 決定subnet或gateway流量的下一跳。 | 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。 |
| Subnets | 把VPC CIDR切成單一AZ內的IP與路由邊界。 | Subnet本身不叫public/private；是否有到IGW的route及instance是否有public IP才決定internet path。 |
| CIDR | 用prefix長度定義IP位址範圍，決定可用位址與route匹配粒度。 | 每增加一個prefix bit，位址數減半；route採longest-prefix match。 |

## 把全圖套進一個具體案例

**場景：** 兩個VPC需要互連，但都使用10.0.0.0/16，且on-premises也有重疊地址。

1. 故事的起點：兩個VPC需要互連，但都使用10.0.0.0/16，且on-premises也有重疊地址。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon VPC負責「建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Route tables、Subnets、CIDR各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只檢查source到destination的路徑，漏掉return route、DNS或stateful device。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon VPC

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：網路設計必須先回答地址是否重疊、封包往哪裡走，以及回程是否存在。
- **具體例子／邊界：** 在「兩個VPC需要互連，但都使用10.0.0.0/16，且on-premises也有重疊地址。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Route tables

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只檢查source到destination的路徑，漏掉return route、DNS或stateful device。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：connectivity = name resolution + forward path + return path + policy。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

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

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon VPC

- **功用：** 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
- **底層機制：** ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
- **關鍵設定：** IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- **選擇時機：** 任何需要私有位址、network segmentation或hybrid connectivity的workload。
- **替換時機：** 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。

### Route tables

- **功用：** 決定subnet或gateway流量的下一跳。
- **底層機制：** 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。
- **關鍵設定：** destination CIDR/prefix list、target、association、propagation、blackhole與return route。
- **選擇時機：** 建立public/private/inspection/hybrid data path與故障隔離時。
- **替換時機：** 需要application-aware routing時使用ALB、API Gateway或service mesh，而不是L3 route。

### Subnets

- **功用：** 把VPC CIDR切成單一AZ內的IP與路由邊界。
- **底層機制：** Subnet本身不叫public/private；是否有到IGW的route及instance是否有public IP才決定internet path。
- **關鍵設定：** AZ、CIDR、route-table association、NACL、auto-assign public IP與available IP capacity。
- **選擇時機：** 分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。
- **替換時機：** 只用security group做workload微分段時不必為每個小角色建立過多subnet。

### CIDR

- **功用：** 用prefix長度定義IP位址範圍，決定可用位址與route匹配粒度。
- **底層機制：** 每增加一個prefix bit，位址數減半；route採longest-prefix match。
- **關鍵設定：** primary/secondary VPC CIDR、subnet CIDR、non-overlap planning、IPv6 /56與prefix lists。
- **選擇時機：** 建立VPC、subnet、hybrid route與未來network growth plan時。
- **替換時機：** 大量帳號容易衝突時以VPC IPAM集中配置與稽核。

## 考前與實作時再查：設定操作手冊

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

### Route tables：逐項設定說明

#### `destination CIDR/prefix list`

- **控制什麼：** `destination CIDR/prefix list`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `target`

- **控制什麼：** `target`指定Route tables讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `association`

- **控制什麼：** `association`控制Route tables的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

#### `propagation`

- **控制什麼：** `propagation`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立public/private/inspection/hybrid data path與故障隔離時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route tables的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `blackhole`

- **控制什麼：** `blackhole`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `return route`

- **控制什麼：** `return route`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立public/private/inspection/hybrid data path與故障隔離時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route tables的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

### Subnets：逐項設定說明

#### `AZ`

- **控制什麼：** `AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Subnets前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `CIDR`

- **控制什麼：** `CIDR`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Subnets的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `route-table association`

- **控制什麼：** `route-table association`控制Subnets的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

#### `NACL`

- **控制什麼：** `NACL`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Subnets中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `auto-assign public IP`

- **控制什麼：** `auto-assign public IP`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Subnets中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `available IP capacity`

- **控制什麼：** `available IP capacity`設定Subnets的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### CIDR：逐項設定說明

#### `primary/secondary VPC CIDR`

- **控制什麼：** `primary/secondary VPC CIDR`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立VPC、subnet、hybrid route與未來network growth plan時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CIDR的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `subnet CIDR`

- **控制什麼：** `subnet CIDR`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立VPC、subnet、hybrid route與未來network growth plan時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CIDR的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `non-overlap planning`

- **控制什麼：** `non-overlap planning`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `IPv6 /56`

- **控制什麼：** `IPv6 /56`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `prefix lists`

- **控制什麼：** `prefix lists`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

## 讀到這裡，請用自己的話說一次

1. Amazon VPC的責任：建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
2. 底層機制：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
3. 第一個要看的設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
4. 選擇邏輯：以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。
5. 不要混淆：Route tables的責任是「決定subnet或gateway流量的下一跳。」；它不會自動取代Amazon VPC。
6. 替換訊號：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
7. 最常見錯法：只檢查source到destination的路徑，漏掉return route、DNS或stateful device。
8. 可移植原則：connectivity = name resolution + forward path + return path + policy。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 | 任何需要私有位址、network segmentation或hybrid connectivity的workload。 | 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。 |
| Route tables | 決定subnet或gateway流量的下一跳。 | 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。 | 建立public/private/inspection/hybrid data path與故障隔離時。 | 需要application-aware routing時使用ALB、API Gateway或service mesh，而不是L3 route。 |
| Subnets | 把VPC CIDR切成單一AZ內的IP與路由邊界。 | Subnet本身不叫public/private；是否有到IGW的route及instance是否有public IP才決定internet path。 | 分散AZ、隔離web/app/data tiers或建立inspection/egress路徑時。 | 只用security group做workload微分段時不必為每個小角色建立過多subnet。 |
| CIDR | 用prefix長度定義IP位址範圍，決定可用位址與route匹配粒度。 | 每增加一個prefix bit，位址數減半；route採longest-prefix match。 | 建立VPC、subnet、hybrid route與未來network growth plan時。 | 大量帳號容易衝突時以VPC IPAM集中配置與稽核。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。 | 只有當題目條件明確改變時才可能合理。 | 只檢查source到destination的路徑，漏掉return route、DNS或stateful device。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。」之間做選擇。
- 認得常考設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- 對應官方tasks：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.5 Design a solution to meet performance objectives。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：VPC、subnet 與 route table

新團隊正在設計一個兩 AZ application network。哪個敘述最正確描述 VPC、subnet 和 route table 的責任？

A. VPC 建立 Region 內的位址與 routing domain；每個 subnet 位於單一 AZ 並關聯路由與網路邊界；route table 依目的位址選 next hop。
B. Subnet 可原生跨越 Region 內所有 AZ，因此一個 subnet 足以提供多 AZ placement。
C. Route table 是 stateful firewall，會自動允許已建立連線的回程。
D. AWS 會保證不同帳號建立的 VPC CIDR 全球唯一。

**答案：A**

- **A：** A 正確。三個元件分別界定區域網路、單 AZ 位址/關聯邊界和 L3 下一跳，必須分開設計。
- **B：** B 錯誤。Subnet 綁定一個 AZ；要跨 AZ 放置資源必須建立多個 subnets。
- **C：** C 錯誤。Route table 只決定轉送目標，不追蹤連線狀態；stateful allow-list 是 security group 的責任。
- **D：** D 錯誤。客戶可在不同 VPC 重複使用私有範圍，但要互連時必須自行避免或處理 overlap。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)、[Subnet sizing for IPv4](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)

### 練習題 2｜SAA｜Mechanism：CIDR prefix 計算

網路團隊把 `10.0.0.0/16` 平均切成 `/20` subnets。忽略實際配置策略，關於位址數量的哪個敘述正確？

A. `/20` 比 `/16` 包含更多位址，因此只能建立一個 subnet。
B. Prefix 增加 4 bits 只能切成 4 個 `/20`。
C. 每個 `/20` 的 4096 個位址都可指派給 ENI。
D. 可切成 16 個 `/20`，每個範圍共有 4096 個 IPv4 位址；建立 AWS subnet 時還要扣除 AWS 保留位址。

**答案：D**

- **A：** A 錯誤。Prefix 越長代表 network 範圍越小；`/20` 是 `/16` 的子集合。
- **B：** B 錯誤。多出的 4 個 subnet bits 產生 2^4，也就是 16 個相同大小範圍。
- **C：** C 錯誤。4096 是總位址數，AWS 在每個 IPv4 subnet 保留五個位址；規劃容量時不能全部計入。
- **D：** D 正確。CIDR 算術先得到 16 個各 4096 位址的範圍，再由 AWS subnet 保留規則決定可指派量。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)、[Subnet sizing for IPv4](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)

### 練習題 3｜SAA｜Concrete setting：route longest-prefix match

App subnet 的 route table 包含 `10.0.0.0/16 → local`、`10.20.0.0/16 → tgw-1234`、`0.0.0.0/0 → nat-5678`。目的 IP 是 `10.20.3.4` 時會選哪個 next hop？

A. 選 AWS 自動建立的 `local` route，因為它不受目的 CIDR 是否匹配影響，優先於自訂 route。
B. 選 `10.20.0.0/16 → tgw-1234`，因為它是涵蓋目的位址的最長匹配；default route 只在沒有更精確匹配時使用。
C. 選 NAT gateway，因為 default route 的範圍最大。
D. 三條 route 隨機輪替以分散流量。

**答案：B**

- **A：** A 錯誤。`local` route 仍須匹配 destination，且 `10.0.0.0/16` 不包含 `10.20.3.4`；它不因為由 AWS 建立即取得跨 CIDR 優先權。
- **B：** B 正確。`10.20.0.0/16` 比 `0.0.0.0/0` 更精確並包含目的位址，因此流量送往 Transit Gateway。
- **C：** C 錯誤。Default route 是最不精確的 fallback，不會覆蓋更長 prefix；只有其他 route 都不匹配時才用。
- **D：** D 錯誤。VPC route table 不以等價路由隨機分流這三個不同 prefix，會依 longest-prefix 和服務規則決定。

**事實查證：** [How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)

### 練習題 4｜SAP｜Data/request flow：hybrid 去回程

VPC `10.0.0.0/16` 的 application 要透過 Transit Gateway 和 VPN 存取 on-premises database `172.20.5.10`。DNS 已正確解析，但 TCP timeout。哪個 end-to-end 路徑條件是必要的？

A. 只要 app subnet 有到 `172.20.0.0/16` 的去程 route，回程會由 AWS 自動推導。
B. DNS 成功已證明 route、firewall 和 return path 都正常。
C. Security group 可取代 on-premises 缺少的 `10.0.0.0/16` return route。
D. App subnet、TGW/VPN 與 on-premises 都須有一致的 forward/return routes，沿途 security policy 和 stateful devices 也必須允許並保持可接受的對稱路徑。

**答案：D**

- **A：** A 錯誤。IP 連線需要 response 返回來源，AWS 不會替 on-premises router 自動建立 VPC CIDR route。
- **B：** B 錯誤。DNS 只把名稱翻成位址，不能證明任何封包已通過路由、VPN 或 policy。
- **C：** C 錯誤。Security group 能允許或拒絕到達 ENI 的流量，但不能創造缺失的 L3 return route。
- **D：** D 正確。Hybrid connectivity 必須同時成立去程、回程與沿途 policy；若經 stateful inspection，路徑還要符合設備的對稱性要求。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)、[Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)、[AWS Site-to-Site VPN routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html)、[Example: Appliance in a shared services VPC](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-appliance-scenario.html)

### 練習題 5｜SAA｜Failure diagnosis：更精確 blackhole route

原本可上網的 private subnet 新增 `203.0.113.0/24 → pcx-deleted` 後，只有該網段 timeout；`0.0.0.0/0 → nat-gateway` 仍為 active。最可能原因與檢查順序是什麼？

A. 更精確的 `/24` blackhole route 勝過 default route；檢查 subnet association、有效 routes、target/attachment 狀態及 return path。
B. EC2 必須重啟，route table 只在開機時讀取。
C. 提高 NACL rule number 會讓該 route 恢復 active。
D. 降低 DNS TTL，因為所有 blackhole 都由 DNS cache 造成。

**答案：A**

- **A：** A 正確。目的位址先匹配 `/24`，即使 target 已刪除仍不會改走較不精確 NAT default；應沿有效路由與 target 狀態診斷。
- **B：** B 錯誤。VPC route table 是網路控制面設定，不需重啟 instance 才生效；重啟只在 OS route 或 application 狀態有問題時可能相關。
- **C：** C 錯誤。NACL rule number 控制 stateless policy 優先順序，不會修復 route target。
- **D：** D 錯誤。題目已指出特定 destination route 變更，DNS TTL 不會讓已知 IP 的 next hop 由 blackhole 變 active。

**事實查證：** [How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)

### 練習題 6｜SAA｜Comparison：route table、security group 與 NACL

Web tier 需要把封包送往 NAT，僅允許 ALB 連入 443，並在 subnet 邊界明確拒絕一段惡意 CIDR。哪個責任分工正確？

A. Security group 選 next hop；route table 驗證 IAM；NACL 自動允許回程。
B. Route table 和 NACL 都是 stateful，因此只需寫單向規則。
C. Route table 選 NAT 等 next hop；security group 在 ENI 層提供 stateful allow；NACL 在 subnet 層依序評估 stateless allow/deny。
D. 三者都只影響 DNS，不處理 IP 流量。

**答案：C**

- **A：** A 顛倒責任。Route table 才選 next hop，SG/NACL 處理網路 policy，NACL 回程還需明確規則。
- **B：** B 錯誤。Security group 是 stateful，NACL 是 stateless；route table 則不是 firewall。
- **C：** C 正確。三個元件分別處理轉送、資源級 stateful allow 和 subnet 級 ordered allow/deny。
- **D：** D 錯誤。它們直接控制 VPC IP path；DNS 是另外的名稱解析層。

**事實查證：** [Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)

### 練習題 7｜SAA｜Cost/operations：集中地址規劃

企業每年新增數十個 VPC，未來要透過 Transit Gateway 連回 on-premises。為什麼預先保留可彙總且不重疊的 CIDR，並由 IPAM 集中配置，通常比事後重編址更省成本？

A. 讓每個團隊都使用 `10.0.0.0/16`，可以減少文件工作且不影響互連。
B. 為每個 VPC 配置目前允許的最大 CIDR，以免日後擴容；企業地址空間利用率和 route summarization 可留到互連時再處理。
C. NAT 可以無成本、無限制地消除所有重疊網路的雙向 routing 問題。
D. 分層且不重疊的空間可簡化 TGW、peering、hybrid route 與 route summarization，減少後續 proxy workaround、停機遷移和重編址。

**答案：D**

- **A：** A 錯誤。重複位址在獨立環境可存在，但一旦互連便無法唯一決定目的地，通常需要昂貴 workaround。
- **B：** B 錯誤。過度配置會消耗企業地址空間並降低未來可分配性；應依成長與彙總需求保留合理範圍。
- **C：** C 錯誤。特定 NAT/proxy 可處理部分 use case，但增加營運、可觀測性和 protocol 限制，不能普遍取代乾淨地址規劃。
- **D：** D 正確。地址是長期架構資源，前置治理能降低互連複雜度和未來 migration 成本。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)、[What is IPAM? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)

### 練習題 8｜SAA｜SAA scenario：可互連 VPC 的 CIDR 與 subnet 規劃

公司今天建立兩個 VPC，明年會互連；每個 VPC 都要跨三個 AZ 擴展，且不同 tier 需要明確 route-table association。最佳初始規劃是什麼？

A. 兩個 VPC 先使用相同 CIDR，之後以 security group 區分目的地。
B. 為每個 VPC 選不重疊且預留成長的 CIDR，依 AZ 建立獨立 subnets，並對每個 subnet 明確關聯適合的 route table。
C. 每個 VPC 建立一個跨三 AZ 的 subnet。
D. 只把 subnet 命名為 public 或 private，不檢查有效 route 和 public address。

**答案：B**

- **A：** A 錯誤。SG 不能解決相同目的 IP 代表兩個網路的 routing ambiguity；未互連前就應避免 overlap。
- **B：** B 正確。不重疊空間、單 AZ subnets 和顯式 route association 同時支援未來互連、故障隔離與可預測路徑。
- **C：** C 不可能。VPC subnet 綁定單一 AZ，跨三 AZ 必須建立至少三個 subnets。
- **D：** D 錯誤。Public/private 是由 route、gateway 與資源地址共同形成的可達性，不是名稱本身。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)

### 練習題 9｜SAP｜SAP expansion：重疊 CIDR 的服務級遷移

併購後有大量使用相同 `10.0.0.0/16` 的 VPC。短期內 consumer 只需呼叫中央付款 API，不需要任意 IP 雙向互通；長期仍要消除重疊。哪兩項策略最合理？（選兩項）

A. 以 PrivateLink endpoint service 或受控 application proxy 發布付款 API，避免把整個重疊 route domain 互連。
B. 把所有 VPC attachments 的 routes 全部 propagate 到同一張 TGW route table。
C. 依靠 longest-prefix match 區分兩個完全相同的 `10.0.0.0/16` 目的網路。
D. 為每一對重疊 VPC 建立更多 peering，讓 AWS 自動翻譯位址。
E. 建立分階段 renumber 計畫，包含新 CIDR、依賴盤點、雙路徑驗證、cutover 和 rollback。

**答案：A、E**

- **A：** A 正確。服務級連線只暴露需要的 API，consumer/provider CIDR 即使重疊也不必建立完整 VPC routing。
- **B：** B 錯誤。相同 prefixes 會造成路由歧義並擴大 blast radius；TGW propagation 不會自動做位址轉換。
- **C：** C 錯誤。兩個完全相同的 prefix 長度沒有足夠資訊選擇正確目的地，longest-prefix 不能辨識業務身份。
- **D：** D 錯誤。VPC peering 要求可路由的非重疊空間，且不提供一般 NAT 翻譯。
- **E：** E 正確。PrivateLink 解決短期最小連線，分階段 renumber 才能恢復長期可擴展的網路互通。

**事實查證：** [What is AWS PrivateLink? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)、[What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)

### 練習題 10｜SAP｜Multi-response：private subnet 對外 timeout

Private subnet 的 EC2 無法連到外部套件站，DNS 已回傳正確 public IP。哪兩項網路事實應最先驗證？（選兩項）

A. 確認 private subnet 是否把 `0.0.0.0/0` 直接指向 Internet Gateway；即使 instance 沒有 public IPv4，這條 route 也會替它完成來源 NAT。
B. 確認 NAT gateway 是否放在一個雖稱為 public、但其 route table 沒有 `0.0.0.0/0 → Internet Gateway` 的 subnet；如果是，先只調整 instance security group。
C. Subnet 的有效 route 是否把目的流量送到可用的 NAT/egress target，且 target 所在路徑與 public connectivity 設定正確。
D. Security group、NACL、return path 與沿途 stateful devices 是否允許去回程及必要 ephemeral ports。
E. 只確認 security group 允許 outbound 443；NACL 是 stateful control，會自動允許所有 return traffic，因此不必檢查 ephemeral port。

**答案：C、D**

- **A：** A 錯誤。Internet Gateway 不會替沒有 public IPv4 的 instance 做可用的雙向 internet mapping；private instance 通常要把 default route 指向 NAT gateway 或其他明確 egress path。
- **B：** B 錯誤。Public NAT gateway 自己也需要位於能經 Internet Gateway 出站的 public subnet；若缺少該 route，只改 workload security group 不會補出 NAT 到 internet 的下一跳。
- **C：** C 正確。Private instance 需要有效 egress next hop，NAT/IGW 所在層也必須可用，否則封包無法離開 VPC。
- **D：** D 正確。Route 正確仍可能被 stateful/stateless policy 或缺失回程阻擋，應同時核對去回程。
- **E：** E 錯誤。Security group 是 stateful，但 network ACL 是 stateless；自訂 NACL 必須明確允許 request 與 return traffic，常見疏漏就是只放行目的 port 而漏掉 ephemeral return path。

**事實查證：** [What is Amazon VPC? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)、[Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)、[NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)、[Create a VPC with private subnets and NAT gateways using AWS CLI](https://docs.aws.amazon.com/vpc/latest/userguide/create-a-vpc-with-private-subnets-and-nat-gateways-using-aws-cli.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「網路設計必須先回答地址是否重疊、封包往哪裡走，以及回程是否存在。」，所以「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」能直接滿足它；若constraint改成「用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」。替代方案「用安全規則阻擋封包不能修復錯誤路由；NAT也不會自動建立所有方向的連線。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只檢查source到destination的路徑，漏掉return route、DNS或stateful device。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「網路設計必須先回答地址是否重疊、封包往哪裡走，以及回程是否存在。」，排除會導致「只檢查source到destination的路徑，漏掉return route、DNS或stateful device。」的選項，再選「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」。本章對應的代表task包括：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以不可重疊CIDR規劃地址，將subnet綁定AZ，再用route table做最長前綴匹配。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「connectivity = name resolution + forward path + return path + policy」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 5 章　DNS、TCP、TLS 與 HTTP

應用程式名稱、連線、加密與請求語意位於不同層，故障時不能混為一談。

## 先建立共同語言：先從故事開始

把鏡頭拉到一個真實的production現場：使用者看到502，有些請求DNS正常但TLS握手失敗，另一些已到ALB後端。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：應用程式名稱、連線、加密與請求語意位於不同層，故障時不能混為一談。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：可以把一次網路請求想成打電話：DNS查號碼，TCP接通線路，TLS核對對方身份，HTTP才是接通後真正說的話。 電話類比無法表達cache、重試與多條網路路徑，所以除錯時仍要逐層看實際metric與log。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon Route 53是這一章的入口，Elastic Load Balancing用來畫出邊界；主要方向「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：使用者看到502，有些請求DNS正常但TLS握手失敗，另一些已到ALB後端。

使用者輸入 api.example.com
          │
          ▼
DNS：把名稱查成位址
          │
          ▼
TCP：和該位址的port建立連線
          │
          ▼
TLS：加密並驗證對方certificate
          │
          ▼
HTTP：送出method、path、headers與body
          │
          ▼
Application / ALB回應；502、timeout與certificate error分屬不同層

失敗時先找：看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon Route 53有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Route 53和Elastic Load Balancing並不是兩個任意的產品名稱。前者適合本章，是因為「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」直接回應了眼前的問題；後者描述的「HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「debug from the lowest failed boundary upward」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 |
| AWS Certificate Manager | 申請、保存並自動更新可供整合服務使用的TLS certificates。 | DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。 |

## 把全圖套進一個具體案例

**場景：** 使用者看到502，有些請求DNS正常但TLS握手失敗，另一些已到ALB後端。

1. 故事的起點：使用者看到502，有些請求DNS正常但TLS握手失敗，另一些已到ALB後端。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Route 53負責「提供authoritative DNS、health check與多種流量政策。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Elastic Load Balancing、AWS Certificate Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Route 53

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：應用程式名稱、連線、加密與請求語意位於不同層，故障時不能混為一談。
- **具體例子／邊界：** 在「使用者看到502，有些請求DNS正常但TLS握手失敗，另一些已到ALB後端。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Elastic Load Balancing

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：debug from the lowest failed boundary upward。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### listener

在load balancer指定protocol/port等待client connection的入口。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

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

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

### Elastic Load Balancing

- **功用：** 將連線或request分散到健康targets並隔離client與backend生命週期。
- **底層機制：** Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
- **關鍵設定：** scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- **選擇時機：** 多instance/task高可用入口與rolling deployment。
- **替換時機：** 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。

### AWS Certificate Manager

- **功用：** 申請、保存並自動更新可供整合服務使用的TLS certificates。
- **底層機制：** DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。
- **關鍵設定：** domain/SAN、validation method、key algorithm、exportability、Region與ALB/CloudFront association。
- **選擇時機：** ALB、CloudFront、API Gateway等TLS termination。
- **替換時機：** 需要在EC2自行取private key、特殊CA或device identity時評估Private CA/自管certificate。

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

### AWS Certificate Manager：逐項設定說明

#### `domain/SAN`

- **控制什麼：** `domain/SAN`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「ALB、CloudFront、API Gateway等TLS termination。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Certificate Manager的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

#### `validation method`

- **控制什麼：** `validation method`定義AWS Certificate Manager用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `key algorithm`

- **控制什麼：** `key algorithm`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

#### `exportability`

- **控制什麼：** `exportability`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「ALB、CloudFront、API Gateway等TLS termination。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Certificate Manager的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `Region`

- **控制什麼：** `Region`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Certificate Manager前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `ALB/CloudFront association`

- **控制什麼：** `ALB/CloudFront association`控制AWS Certificate Manager的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

## 讀到這裡，請用自己的話說一次

1. Amazon Route 53的責任：提供authoritative DNS、health check與多種流量政策。
2. 底層機制：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
3. 第一個要看的設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
4. 選擇邏輯：依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。
5. 不要混淆：Elastic Load Balancing的責任是「將連線或request分散到健康targets並隔離client與backend生命週期。」；它不會自動取代Amazon Route 53。
6. 替換訊號：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
7. 最常見錯法：看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。
8. 可移植原則：debug from the lowest failed boundary upward。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 | 多instance/task高可用入口與rolling deployment。 | 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。 |
| AWS Certificate Manager | 申請、保存並自動更新可供整合服務使用的TLS certificates。 | DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。 | ALB、CloudFront、API Gateway等TLS termination。 | 需要在EC2自行取private key、特殊CA或device identity時評估Private CA/自管certificate。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。 | 只有當題目條件明確改變時才可能合理。 | 看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。」之間做選擇。
- 認得常考設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：DNS、TCP、TLS 與 HTTP 分層

使用者輸入 `https://shop.example.com` 後，瀏覽器必須找到 endpoint、建立可靠連線、驗證加密身份，最後送出應用請求。哪個分工正確？

A. DNS 授權 AWS API，TCP 驗證 certificate，TLS 選擇 route，HTTP 保證封包可靠。
B. DNS 將名稱解析成位址，TCP 建立可靠 byte stream，TLS 加密並驗證 endpoint 身份，HTTP 表達 request/response 語意。
C. TLS 在沒有 IP connectivity 時仍可直接完成，DNS 和 TCP 都不是前置條件。
D. HTTP 負責重新傳送遺失的 IP packets，因此不需要 TCP。

**答案：B**

- **A：** A 顛倒各層責任。AWS API authorization 由 identity/policy 處理，route 由網路層決定，不能交給 DNS 或 TLS。
- **B：** B 正確。四層依序處理名稱、連線、加密身份和應用語意，因此故障診斷也應找出最低失敗邊界。
- **C：** C 錯誤。一般 HTTPS 必須先取得可連線位址並建立 transport connection，之後才能進行 TLS handshake。
- **D：** D 錯誤。HTTP 描述應用交換，不替代 TCP 的可靠傳輸；只有改用基於 QUIC 的 HTTP/3 等不同 transport 時模型才改變。

**事實查證：** [What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

### 練習題 2｜SAA｜Mechanism：hosted zone、resolver 與 routing policy

公司在 Route 53 public hosted zone 為同一名稱建立 latency records。Client 查詢名稱後建立 HTTPS connection。哪個敘述最準確？

A. Hosted zone 保存權威 records；resolver 查詢並依 TTL cache；Route 53 routing policy 在 DNS 回答階段選 record，之後的 HTTPS 流量不由 Route 53 逐 request proxy。
B. Route 53 會保存每個使用者的 HTTP session，並逐 request 選後端。
C. TTL 是 Route 53 執行 health check 的探測間隔。
D. Resolver 會把 application request body 傳送到 hosted zone。

**答案：A**

- **A：** A 正確。Route 53 是權威 DNS 與健康/流量政策服務，回答被 resolver 快取後，client 直接連到回傳 endpoint。
- **B：** B 錯誤。DNS 不保存應用 session，也不是 L7 proxy；需要逐 request routing 時應使用 ALB、API Gateway 或 CloudFront 等。
- **C：** C 錯誤。TTL 控制 DNS answer cache，health-check interval 是另一項設定；兩者可能共同影響 failover 觀察時間。
- **D：** D 錯誤。Resolver 只處理 DNS query/answer，不接觸 HTTP body。

**事實查證：** [What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)

### 練習題 3｜SAA｜Concrete setting：zone apex 指向 ALB

Route 53 管理 `example.com`，公司要讓 zone apex `example.com` 指向 internet-facing Application Load Balancer。ALB 位址可能變動。應建立哪種 record？

A. 在 apex 建立一般 CNAME，指向任意一台 target instance。
B. 建立固定 A record，手動抄寫目前解析到的某個 ALB IP。
C. 建立 Route 53 A Alias（需要 IPv6 時另建 AAAA Alias）指向 ALB。
D. 建立 MX record，將網站流量交給 ALB。

**答案：C**

- **A：** A 錯誤。Zone apex 不能使用一般 CNAME，且指向單一 target 會繞過 load balancer；CNAME 適用於非 apex 的其他名稱。
- **B：** B 錯誤。ALB 不提供供客戶長期固定的節點 IP，手抄結果會失效；固定 IP 需求應重新評估入口服務。
- **C：** C 正確。Alias 可在 apex 指向支援的 AWS 資源，讓 Route 53 使用 ALB DNS target 而不維護臨時 IP。
- **D：** D 錯誤。MX 記錄用於郵件交換，不會把 HTTPS 連線導到 ALB。

**事實查證：** [Routing traffic to an ELB load balancer - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html)

### 練習題 4｜SAP｜Data/request flow：browser 到 ALB target

Public HTTPS application 使用 Route 53、ALB HTTPS listener 和 HTTP target group。哪個順序最完整描述一次成功 request？

A. 先由 browser 執行 target health check，再由 Route 53 傳送 HTTP body。
B. 先完成 TLS，再查 DNS 取得要驗證的 hostname。
C. Route 53 把 request 代理到 target，ALB 只回傳 DNS answer。
D. Resolver 取得 DNS answer → client 建立 TCP connection → 與 ALB 完成 TLS/certificate 驗證 → 傳送 HTTP request → listener rule 選 target group → healthy target 處理並回應。

**答案：D**

- **A：** A 錯誤。ALB 自己執行 target health checks，browser 不負責；Route 53 也不承載 HTTP body。
- **B：** B 順序錯誤。Client 通常先解析 hostname 和建立連線，才以該 hostname 驗證 TLS certificate。
- **C：** C 顛倒責任。Route 53 只回答 DNS，ALB 才是接收連線並將 L7 request 導向 targets 的 data plane。
- **D：** D 正確。這個序列把名稱解析、transport、TLS、listener/rule 和 backend health 清楚串接，可用於逐層診斷。

**事實查證：** [What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)、[What is AWS Certificate Manager? - AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)

### 練習題 5｜SAA｜Failure diagnosis：certificate name mismatch

`dig api.example.com` 回傳正確 ALB 名稱，TCP 443 也可建立，但 browser 顯示 certificate name mismatch。最可能故障層與修正是什麼？

A. DNS cache 層；只需把 TTL 改成 0。
B. Target group health path；把 `/health` 改成 `/` 即可修正 certificate。
C. TLS identity 層；讓 HTTPS listener 使用 SAN/CN 涵蓋 `api.example.com` 的 certificate，並確認 certificate 位於與 ALB 相同 Region。
D. NACL 一定阻擋 ephemeral ports；certificate 內容與錯誤無關。

**答案：C**

- **A：** A 不對症。DNS 已解析到預期 endpoint，TTL 不會讓 certificate 新增缺失的 hostname。
- **B：** B 不對症。Health path 影響 target 是否接收流量，但 client 在 ALB TLS handshake 時已因名稱不符失敗。
- **C：** C 正確。Mismatch 表示 client 要求的 hostname 不在 listener 所呈現 certificate 的身份範圍；ALB 使用的 ACM certificate 也需在同一 Region。
- **D：** D 錯誤。TCP 已建立，且明確錯誤是 TLS identity；NACL 問題更常造成 timeout，而非 certificate name mismatch。

**事實查證：** [What is AWS Certificate Manager? - AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

### 練習題 6｜SAA｜Comparison：TCP 與 HTTP health check

Network Load Balancer 的 target group 目前使用 TCP health check。Target process 仍能接受 TCP 連線，但內部 thread pool 已鎖死，`/ready` 會回 503。若要讓 NLB 停止送新流量到該 target，哪個比較正確？

A. TCP health check 可讀取 `/ready` 的 response body，因此一定優於 HTTP。
B. HTTP health check 不需要成功建立 transport connection。
C. 兩種 health check 都能證明完整付款交易成功。
D. 把 NLB target group 的健康檢查改為 HTTP 並檢查 `/ready` 的成功狀態；TCP check 主要證明 port 可接受連線，而 HTTP path 更接近應用 readiness，但仍要避免把非關鍵依賴綁進健康條件。

**答案：D**

- **A：** A 錯誤。TCP check 不理解 HTTP path 或 response body，只驗證能否建立連線。
- **B：** B 錯誤。HTTP 仍依賴 TCP，HTTPS 還依賴 TLS；它是在更高層增加應用語意檢查。
- **C：** C 過度宣稱。Health endpoint 通常只代表選定 readiness 條件，不會自動執行完整 business transaction。
- **D：** D 正確。NLB target group 支援 TCP、HTTP 或 HTTPS 等健康檢查協定；題目故障在應用層，HTTP `/ready` 能看見 503，而 TCP connect 看不見 thread pool 是否仍可服務。

**事實查證：** [Health checks for Network Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/target-group-health-checks.html)

### 練習題 7｜SAA｜Cost/operations：低 DNS TTL 的取捨

團隊預計明天把 API 從舊 endpoint 切到新 endpoint，考慮將 DNS TTL 從一小時降到 60 秒。哪個敘述最準確？

A. 應在切換前至少經過舊 TTL 的時間降低 TTL；較低 TTL 可縮短部分 resolver cache，但增加權威查詢量，且不會終止既有連線。
B. 切換當下才降低 TTL 也會立刻清除所有 resolver 已保存的一小時 cache。
C. TTL 為 0 能保證每名 client 零秒切換並關閉舊 TCP sessions。
D. Alias record 可任意覆寫所有 AWS target 的 TTL，因此不需了解 target 行為。

**答案：A**

- **A：** A 正確。舊 answer 必須先自然過期，低 TTL 只影響後續 DNS cache 行為；長連線和 client 自身 cache 仍需另行處理。
- **B：** B 錯誤。已取得舊 TTL 的 resolver 可繼續使用舊值，新的 TTL 只有重新查詢後才被看見。
- **C：** C 錯誤。Client/resolver 行為與既有 connection 不由 TTL 強制控制，DNS 不能提供精準 request-level cutover。
- **D：** D 錯誤。Alias 的 TTL 由所指 AWS 資源類型處理，不能把它當成可任意設定的一般 record TTL。

**事實查證：** [What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)、[Routing traffic to an ELB load balancer - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html)

### 練習題 8｜SAA｜SAA scenario：ALB HTTPS 與健康分流

Public web application 使用 ALB，要求 TLS certificate 可受管續期，並只把 request 送到真正能處理 `/checkout` 的 targets。哪個設定最符合需求？

A. 把 private key 存進 Route 53 A record，讓 DNS 完成 TLS。
B. 在 ALB 所在 Region 關聯由 ACM 簽發、仍符合 managed-renewal 條件的 public certificate；listener/rules 導向 target group，並設定能代表 `/checkout` readiness 的 HTTP health path。
C. 只做 TCP health check，便能保證每筆 checkout transaction 成功。
D. 把 certificate 安裝在每個 client，ALB 不需要 listener。

**答案：B**

- **A：** A 錯誤。DNS record 不保存 TLS private key，也不終止 HTTPS；certificate 必須關聯支援的 TLS endpoint。
- **B：** B 正確。符合條件的 ACM-issued certificate 可由 ACM 管理續期，ALB listener 負責 TLS termination；target group 的應用健康檢查則控制哪些 targets 接收新流量。Imported certificate 不會由 ACM 自動續期。
- **C：** C 不足。TCP 只證明 port 開啟，無法看見 `/checkout` readiness；若只需 port-level liveness 才適用。
- **D：** D 錯誤。Public server authentication 不要求在每個 client 安裝 server private key，且 ALB 仍需 listener 接收連線。

**事實查證：** [What is AWS Certificate Manager? - AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)、[Managed certificate renewal in AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

### 練習題 9｜SAP｜SAP expansion：DNS cutover 後的舊站流量

多 Region API 完成 DNS failover 後，仍有少量使用者持續到舊 Region。哪兩項設計/診斷最重要？（選兩項）

A. 把新 Region 的 ALB target 數量加倍，便可清除 client 的舊 DNS cache。
B. 檢查舊 TTL、resolver/client cache、既有長連線和健康訊號實際改變時間，將它們納入 cutover 時間線。
C. 把 TTL 改成 1 秒，並宣稱所有 request 從此精準按秒切換。
D. 把 DNS routing policy 當成逐 request proxy，用它保存 session。
E. 在新 Region 準備相容的 session/data state，採分階段切換、舊站 fencing/draining 與可回復 runbook。

**答案：B、E**

- **A：** A 無法解決舊路徑。新站容量可能必要，但不會改變 resolver cache 或已建立 connection。
- **B：** B 正確。DNS failover 的觀察延遲由多層 cache、探測與 connection 行為共同決定，必須以證據定位。
- **C：** C 錯誤。低 TTL 降低部分 cache 上限，但 client 可有額外行為，且不影響既有 sessions。
- **D：** D 錯誤。Route 53 只回答 DNS，不保存應用 session 或代理每個 request。
- **E：** E 正確。完整切換還需處理資料、session、舊 writer 隔離和 rollback，否則 DNS 已改仍可能產生錯寫或失敗。

**事實查證：** [What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)、[Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 10｜SAP｜Multi-response：ALB 502 的高價值證據

Client 能解析 DNS 並完成 ALB TLS handshake，但 ALB 回傳 HTTP 502。哪兩項證據最有助於定位問題？（選兩項）

A. ALB access logs、load balancer/target 狀態碼與對應時間的 target application logs。
B. 只確認 target health check 為 healthy；healthy 證明 production request 一定不會被 target reset，也不可能回傳 malformed HTTP response。
C. 把 ALB idle timeout 調大，因為 idle timeout 過短只會產生 502，不可能產生 504。
D. 驗證 target group 的 port/protocol、listener 轉送設定，以及 target 是否回傳 ALB 可解析的有效 response。
E. 只把 target group 的 healthy threshold 調低；這會修正 backend TLS handshake、target reset 與無效 HTTP header，而不需要查看 target logs。

**答案：A、D**

- **A：** A 正確。502 發生在 ALB 與 target response 路徑，access log 和 backend log 可關聯誰產生錯誤及協定結果。
- **B：** B 錯誤。Health check 只測指定 path 與條件；production response 仍可能在較大 payload、不同 route 或尖峰時被 reset 或形成 ALB 無法解析的 response，因此 healthy 不能排除 502。
- **C：** C 錯誤。較長 idle timeout 只對部分連線生命週期問題有幫助，不能一概修正 502；ALB 也可能因 target connection timeout 回 504，必須先看 access log reason 與 target 行為。
- **D：** D 正確。Port/protocol mismatch、連線重設或無效 HTTP response 都可使 ALB 回 502，應直接驗證 data path。
- **E：** E 錯誤。Healthy threshold 只改變 target 被判定健康所需的連續成功次數，不會修復 backend TLS、連線重設或 malformed response；沒有 logs 也無法區分相鄰故障。

**事實查證：** [Troubleshoot your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「應用程式名稱、連線、加密與請求語意位於不同層，故障時不能混為一談。」，所以「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」能直接滿足它；若constraint改成「HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」。替代方案「HTTP health check可證明應用路徑；TCP health check較便宜但只證明port接受連線。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「應用程式名稱、連線、加密與請求語意位於不同層，故障時不能混為一談。」，排除會導致「看到timeout就重試，可能放大DNS、TLS或後端過載，並造成非冪等操作重複。」的選項，再選「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「依序驗證DNS解析、TCP可達、TLS身份與HTTP回應，每層保存自己的狀態與timeout。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「debug from the lowest failed boundary upward」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 6 章　Block、File 與 Object Storage

資料需要不同的存取介面、一致性、共享方式、延遲與生命週期。

## 先建立共同語言：先從故事開始

如果今天由你值班，收到的需求可能是這樣：影像原檔要保存十年、Linux叢集共享模型檔、資料庫要求低延遲隨機I/O。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：資料需要不同的存取介面、一致性、共享方式、延遲與生命週期。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：S3比較像大型包裹倉庫：每件物品用完整key存取，而不是在遠端磁碟上任意改其中幾個bytes。 這只是起點，因為倉庫類比不能取代一致性、multipart upload、versioning與policy細節；它只用來先分清object和file。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon EBS承接主要責任，以Amazon EFS檢查替代條件，並用「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：影像原檔要保存十年、Linux叢集共享模型檔、資料庫要求低延遲隨機I/O。

資料要怎麼被使用？
  ├─ 像本機磁碟、低延遲隨機I/O ───────> Block / EBS
  ├─ 多台機器共享目錄、需要file semantics ─> File / EFS / FSx
  └─ 以key整個PUT/GET、海量耐久保存 ─────> Object / S3

先選access semantics，再比較容量、throughput、availability與價格。
Backup回答「壞掉後如何找回」；它不是第四種日常存取介面。

失敗時先找：把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon EBS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EBS和Amazon EFS並不是兩個任意的產品名稱。前者適合本章，是因為「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」直接回應了眼前的問題；後者描述的「資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「select storage by access semantics before capacity」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 |
| Amazon EFS | 提供regional或One Zone、彈性容量的managed NFS file system。 | 各AZ mount target接收NFSv4.1；多clients共享目錄與POSIX metadata。 |
| Amazon FSx | 提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file systems。 | 每種engine保留原生protocol與features，由AWS管理server、storage與backup。 |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |

## 把全圖套進一個具體案例

**場景：** 影像原檔要保存十年、Linux叢集共享模型檔、資料庫要求低延遲隨機I/O。

1. 故事的起點：影像原檔要保存十年、Linux叢集共享模型檔、資料庫要求低延遲隨機I/O。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EBS負責「為EC2提供單AZ持久block volumes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EFS、Amazon FSx、Amazon S3各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon EBS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：資料需要不同的存取介面、一致性、共享方式、延遲與生命週期。
- **具體例子／邊界：** 在「影像原檔要保存十年、Linux叢集共享模型檔、資料庫要求低延遲隨機I/O。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EFS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：select storage by access semantics before capacity。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

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

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### IOPS

每秒可完成的I/O operations數，偏向小型random reads/writes能力。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

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

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

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

## 讀到這裡，請用自己的話說一次

1. Amazon EBS的責任：為EC2提供單AZ持久block volumes。
2. 底層機制：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。
3. 第一個要看的設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
4. 選擇邏輯：Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。
5. 不要混淆：Amazon EFS的責任是「提供regional或One Zone、彈性容量的managed NFS file system。」；它不會自動取代Amazon EBS。
6. 替換訊號：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
7. 最常見錯法：把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。
8. 可移植原則：select storage by access semantics before capacity。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 | boot disk、database、低延遲random I/O與需要in-place update的單instance state。 | 多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。 |
| Amazon EFS | 提供regional或One Zone、彈性容量的managed NFS file system。 | 各AZ mount target接收NFSv4.1；多clients共享目錄與POSIX metadata。 | Linux shared content、home directories、ECS/EKS/Lambda共享files。 | Windows SMB選FSx Windows；HPC parallel I/O選FSx Lustre；block database選EBS。 |
| Amazon FSx | 提供Windows、Lustre、NetApp ONTAP與OpenZFS等managed file systems。 | 每種engine保留原生protocol與features，由AWS管理server、storage與backup。 | 既有應用需要SMB/AD、Lustre HPC、ONTAP多protocol或OpenZFS semantics。 | 一般Linux NFS共享用EFS較簡單；object workload用S3。 |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。 | 只有當題目條件明確改變時才可能合理。 | 把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。」之間做選擇。
- 認得常考設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
- 對應官方tasks：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：block、file 與 object semantics

架構師要分別滿足低延遲資料庫磁碟、跨多台 Linux 主機的共享目錄，以及以 API 保存不可變影像。哪個敘述正確區分 storage interfaces？

A. Block、file、object 只差容量大小，application access semantics 相同。
B. S3 是一般 POSIX disk，可原生提供 in-place append、directory rename 和 file locking。
C. Block 提供可格式化的 device/blocks；file 提供共享階層與 NFS/SMB 等語意；object 以 bucket/key 和 API 讀寫獨立物件。
D. EBS 自動為所有 AZ 的主機提供共享目錄，無需 cluster-aware filesystem。

**答案：C**

- **A：** A 錯誤。三者暴露的讀寫 contract、共享方式與更新粒度不同，容量只是其中一項 sizing 條件。
- **B：** B 錯誤。S3 是 object API，不承諾一般 POSIX filesystem 的 append/rename/locking；只有經過語意調整的應用才適合。
- **C：** C 正確。先依 application 需要的 interface 與一致性/共享語意分類，才能選 EBS、EFS/FSx 或 S3。
- **D：** D 錯誤。EBS 主要是單 AZ block device；特定 Multi-Attach 情境仍需支援的 volume/instance 與 cluster-aware 檔案系統，不能視為一般共享目錄。

**事實查證：** [Storage - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)、[Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)

### 練習題 2｜SAA｜Mechanism：EBS volume 與 snapshot

EC2 在 `us-east-1a` 使用一個 EBS volume，團隊要建立 recovery point 並可能在 `us-east-1b` 恢復。哪個敘述正確？

A. EBS snapshot 是可直接由多台主機掛載的 NFS filesystem。
B. Volume 位於單一 AZ；snapshot 是儲存在受管 regional infrastructure 的增量 recovery point，可用它在所選 AZ 建立新 volume。
C. EBS volume 會自動同步複寫到所有 Regions。
D. Snapshot 只保存 filesystem metadata，不保存實際 blocks。

**答案：B**

- **A：** A 錯誤。Snapshot 是建立 volume 的 recovery artifact，不是可直接 mount 的共享檔案服務。
- **B：** B 正確。Running volume 具 AZ affinity，而 snapshot 可作為在同 Region 其他 AZ 建立 volume 的來源。
- **C：** C 錯誤。跨 Region copy 必須明確執行與管理 KMS/成本，volume 本身不自動全球複寫。
- **D：** D 錯誤。EBS snapshot 保存 volume blocks 的增量變更，並非只存 filesystem 目錄資訊。

**事實查證：** [Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

### 練習題 3｜SAA｜Concrete setting：gp3 IOPS 與 throughput

資料庫 volume 需要 12,000 IOPS 和 500 MiB/s，容量需求只有 400 GiB。若評估 EBS gp3，應採取哪個設定思路？

A. 沿用容量驅動效能的做法，只增加 volume size 直到達到目標，不另行設定 gp3 IOPS 或 throughput。
B. 改用 st1，因為 throughput-optimized HDD 最適合低延遲隨機 OLTP。
C. 調整 EFS throughput mode，該設定會直接改變 EBS volume。
D. 把 size、IOPS、throughput 視為獨立需求配置 gp3，並確認 gp3 範圍、EC2 instance 的 EBS bandwidth/IOPS 限制及實際 workload 測試結果。

**答案：D**

- **A：** A 錯誤。Gp3 可獨立配置 IOPS 和 throughput，盲目擴容量會增加不必要成本；只有容量本身需要增加時才調整 size。
- **B：** B 錯誤。St1 適合大型循序 throughput workload，不適合題目要求的低延遲隨機 OLTP。
- **C：** C 無關。EFS throughput mode 控制檔案系統，不會修改 EBS block volume。
- **D：** D 正確。Volume 規格與 instance 通道共同限制可達效能，必須逐層驗證而非只看一個參數。

**事實查證：** [Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[Amazon EBS volume types - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)

### 練習題 4｜SAA｜Data/request flow：多 AZ client 存取 EFS

跨三個 AZ 的 Linux application 要共享 EFS 目錄，並用 access point 強制應用的 POSIX identity。哪個 data path 描述最準確？

A. Client 透過 DNS 找到適合 AZ 的 EFS mount target，以 NFSv4.1 連線；mount target/SG、NFS path、access point 與 POSIX 權限共同決定存取。
B. EFS client 使用 S3 REST API，mount target 是 object backup copy。
C. 所有 clients 直接共用一個跨 AZ EBS attachment，不需要 NFS。
D. Access point 會自動建立 Internet route，讓任何 public client 掛載 filesystem。

**答案：A**

- **A：** A 正確。EFS 由區域檔案系統和各 AZ mount targets 提供 NFS 接入，網路與檔案身份/權限都必須成立。
- **B：** B 錯誤。EFS 暴露 NFS file semantics，不使用 S3 object API；mount target 是 network endpoint，不是備份副本。
- **C：** C 錯誤。一般 EBS attachment 不提供多 AZ 共享 NFS contract；共享 Linux 目錄正是 EFS 的 use case。
- **D：** D 錯誤。Access point 管理應用入口與 POSIX identity，不會建立 public Internet exposure；network path 仍由 VPC 控制。

**事實查證：** [How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)、[Working with access points - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/efs-access-points.html)

### 練習題 5｜SAA｜Failure diagnosis：EBS AZ affinity

原 EC2 位於 `us-west-2a`，替代 instance 啟動在 `us-west-2b` 後無法直接 attach 原 EBS volume。最可能原因與恢復方式是什麼？

A. Security group 一定阻擋 EBS；開放 TCP 2049 即可。
B. EBS volume 與 instance 必須位於相同 AZ；可從合適 snapshot 在 `us-west-2b` 建立新 volume，並檢查應用一致性與恢復流程。
C. 降低 Route 53 TTL 便能把 volume 移到另一 AZ。
D. 手動修改 volume ARN 中的 AZ 字串即可重新定位 blocks。

**答案：B**

- **A：** A 錯誤。EBS attachment 不是透過客戶 SG 的 NFS 2049 流量，題目症狀由 AZ placement 更直接解釋。
- **B：** B 正確。EBS running volume 具 AZ affinity；跨 AZ 恢復需以 snapshot 建新 volume 或使用不同的多 AZ 資料架構。
- **C：** C 無關。DNS cache 不會移動 block storage 或改變 attach placement。
- **D：** D 不可能。ARN/ID 是資源識別，不可藉改字串搬移實際 storage。

**事實查證：** [Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

### 練習題 6｜SAA｜Comparison：EFS、FSx、S3 與 storage protocol

四個需求分別是 Windows SMB 且整合 Active Directory、一般 Linux NFS 分享、HPC Lustre 平行檔案系統，以及長期 object archive。哪個映射最合理？

A. FSx for Windows File Server、EFS、FSx for Lustre、S3 archive storage classes。
B. 四者都用單一 EBS volume，並跨 AZ 同時 attach。
C. 四者都把 S3 當作完全等同原生 filesystem 的 mount。
D. 只依每 GB 月租選同一服務，不考慮 protocol 和 access semantics。

**答案：A**

- **A：** A 正確。每項服務保留題目所需的 SMB/AD、NFS、Lustre 或 object archive contract。
- **B：** B 錯誤。單一 EBS 不提供這四種跨主機、跨協定需求，且具 AZ/attachment 限制。
- **C：** C 錯誤。S3 適合 object，但不能假設完整 SMB、NFS、Lustre 與 POSIX 行為；只有已為 object API 重構的 workload 才合適。
- **D：** D 錯誤。最低 storage 單價若不支援應用 protocol，會轉化成重寫、同步和失敗成本。

**事實查證：** [How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)、[What is FSx for Windows File Server?](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)、[What is Amazon FSx for Lustre?](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)

### 練習題 7｜SAA｜Cost/operations：十年 object archive

數十億個合規 objects 要保存十年，平均每年只讀一次，但稽核要求在指定時間內可取回。選擇 S3 lifecycle 和 archive class 時最完整的成本分析是什麼？

A. 只比較每 GB 月租；request、retrieval、minimum duration 和 restore 時間都不影響。
B. 沿用團隊現有的 EBS sc1 管理流程保存所有 objects，並只用每 GB 儲存單價比較，不計 EC2、AZ 與 volume operations。
C. 啟用跨 Region replication 後刪除來源舊版本，並把 destination replica 當成可還原任意歷史狀態的 backup。
D. 依取回時限選擇合適 storage class，並納入 minimum storage duration、minimum billable size、transition/request、retrieval 費、restore workflow 和舊版本生命週期。

**答案：D**

- **A：** A 不完整。Archive 總成本和可用性取決於取回頻率、物件大小、最短保存期及 restore latency，不只是月租。
- **B：** B 錯誤。Sc1 是 EBS cold HDD block volume，仍需 EC2/AZ 管理且不符合大規模 object archive 的 API/lifecycle 模型。
- **C：** C 危險。Replication 可複製刪除或錯誤，不等同獨立歷史 backup；需要 versioning、retention 或 backup 控制。
- **D：** D 正確。此分析同時滿足保存、取回 SLO 和完整 cost drivers，才能選 Standard-IA、Glacier 類別或其他 lifecycle 組合。

**事實查證：** [Understanding and managing Amazon S3 storage classes - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)

### 練習題 8｜SAA｜SAA scenario：混合 storage 映射

單一 application 同時需要：關聯式資料庫的低延遲隨機 block I/O、三個 AZ 的 Linux workers 共享模型檔，以及影像原檔長期保存並依年份 lifecycle。哪個方案最符合各自語意？

A. 全部放一個 S3 bucket，並假設 database 可原生使用 POSIX block device。
B. 全部放一個 EBS volume，讓三個 AZ 的 workers 同時掛載。
C. 資料庫使用合適的 EBS volume；共享模型檔使用 EFS 或符合協定的 FSx；影像使用 S3 與 lifecycle。
D. 影像使用 EFS，database 和共享檔都使用 Glacier Deep Archive。

**答案：C**

- **A：** A 錯誤。S3 object API 不提供 database 所需的 block device 和一般 POSIX contract。
- **B：** B 錯誤。單一 EBS volume 不能成為跨三 AZ 的一般共享 filesystem，且會集中 failure scope。
- **C：** C 正確。每個資料類型依 access interface、共享方式與 lifecycle 選擇最合適的受管 storage。
- **D：** D 錯誤。EFS 不適合低成本長期 object archive，Deep Archive 也不能提供互動式 database 或共享檔案 I/O。

**事實查證：** [Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)、[Amazon FSx Documentation](https://docs.aws.amazon.com/fsx/)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)

### 練習題 9｜SAP｜SAP expansion：Petabyte NAS 分階段遷移

企業要把 petabyte 級 NAS 搬到 AWS，但應用短期不能改 SMB/NFS protocol，且 cutover 必須可回復。哪兩項做法最合理？（選兩項）

A. 直接把所有資料改成 S3 keys，省略 protocol、ACL、locking 和 metadata 相容性測試。
B. 用 EBS snapshots 直接擷取 on-premises NAS appliance，假設格式可移植。
C. 依現有 SMB/NFS/ONTAP/Lustre 語意選 EFS 或適合的 FSx，盤點 throughput、metadata、ACL、identity 與應用依賴。
D. 只估算總容量，不量測小檔案數、變更率、吞吐和 cutover window。
E. 使用 DataSync 等遷移路徑做初始 copy 與增量同步，驗證 ACL/校驗、freeze/cutover/rollback；之後再把適合內容逐步重構為 object。

**答案：C、E**

- **A：** A 錯誤。Object migration 會改變應用 contract，題目明示短期不能改 protocol；只有後續重構階段才可考慮。
- **B：** B 錯誤。EBS snapshot 是 AWS block volume recovery artifact，不是通用 on-prem NAS 遷移格式。
- **C：** C 正確。先保留應用依賴的 file semantics，才能降低第一階段 migration 風險並選對 managed filesystem。
- **D：** D 不足。相同容量在小檔案、ACL 和變更率不同時，遷移時間與效能會差異巨大。
- **E：** E 正確。可重複的增量同步、驗證和 rollback 支援受控 cutover，也保留日後把合適資料轉成 S3 的路線。

**事實查證：** [What is AWS DataSync? - AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)、[How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)、[Amazon FSx Documentation](https://docs.aws.amazon.com/fsx/)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)

### 練習題 10｜SAA｜Multi-response：S3 與 POSIX filesystem 邊界

Legacy application 會對檔案做任意位置的 in-place mutation、把含有多個檔案的目錄樹做原子 rename，並使用 POSIX locks 協調多個 writers。哪兩項理由說明不能直接把 S3 當成一般 POSIX filesystem？（選兩項）

A. S3 以 bucket/key 和 object API 存取資料，PUT 通常建立或取代完整 object，而不是暴露可隨機更新的 block/file device。
B. 即使 S3 Express One Zone directory bucket 支援受限制的 append 與單一 object 的 metadata-only `RenameObject`，S3 object API 仍不提供此 legacy application 要求的完整 POSIX file-descriptor、任意 in-place mutation、原子目錄樹操作與 locking contract。
C. S3 不具資料耐久性，因此任何 object 都會在單一磁碟故障時遺失。
D. S3 bucket 只能存在於單一 AZ。
E. S3 不支援任何 server-side 或 client-side encryption。

**答案：A、B**

- **A：** A 正確。Object API 的定位與更新粒度不同，legacy file calls 不能假設可一對一映射。
- **B：** B 正確。Directory bucket 的新能力不能推論成一般 POSIX filesystem：append 有 API 與 part 限制，`RenameObject` 只重新命名同一 directory bucket 內的單一 object，且不接受以 `/` 結尾的 directory marker；它不是原子移動整棵目錄樹，也不提供 POSIX lock coordination。
- **C：** C 錯誤。S3 以高 durability 設計，不能用「不耐久」作為排除理由；真正邊界是 interface 與語意。
- **D：** D 錯誤。General purpose S3 bucket 是 Region scope 服務，不是單 AZ block volume。
- **E：** E 錯誤。S3 支援多種 encryption 選項；加密能力與是否具 POSIX semantics 是不同問題。

**事實查證：** [What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)、[Appending data to objects in directory buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-objects-append.html)、[Renaming objects in directory buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-objects-rename.html)、[How Amazon EFS works - Amazon Elastic File System](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「資料需要不同的存取介面、一致性、共享方式、延遲與生命週期。」，所以「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」能直接滿足它；若constraint改成「資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」。替代方案「資料庫磁碟通常用block；共享POSIX工作流用file；大量靜態內容與備份用object。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「資料需要不同的存取介面、一致性、共享方式、延遲與生命週期。」，排除會導致「把S3掛載成一般磁碟並假設rename、locking與低延遲完全等同POSIX檔案系統。」的選項，再選「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」。本章對應的代表task包括：SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Block給單機檔案系統，file提供共享目錄語意，object用key與API管理獨立物件。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「select storage by access semantics before capacity」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 7 章　Relational、NoSQL、Cache 與 Warehouse

資料模型、查詢模式、交易需求與擴展方向共同決定資料服務。

## 先建立共同語言：先從故事開始

故事從一個看似簡單的需求開始：訂單需要ACID交易、session需要毫秒讀取、分析師需要掃描多年事件。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：資料模型、查詢模式、交易需求與擴展方向共同決定資料服務。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

關聯式資料庫像一本正式帳簿：交易要讓多個欄位一起成立，讀副本則像提供影本給查詢者使用。 副本可能有延遲，failover也涉及client重新連線；不能把影本當成永遠同步的主帳簿。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon RDS會是本章的主要角色，Amazon Aurora則幫我們看清邊界。方向是「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：訂單需要ACID交易、session需要毫秒讀取、分析師需要掃描多年事件。

先列出資料access patterns
  ├─ transaction、join、關聯完整性 ─────> RDS / Aurora
  ├─ 已知key、極大scale、低延遲 ────────> DynamoDB
  ├─ 可重建的熱門讀取結果 ─────────────> ElastiCache
  └─ 掃描多年資料做聚合分析 ───────────> Redshift / Athena

同一系統可以同時使用多種store，但每份資料只能有清楚的authoritative owner。

失敗時先找：只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon RDS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon RDS和Amazon Aurora並不是兩個任意的產品名稱。前者適合本章，是因為「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」直接回應了眼前的問題；後者描述的「Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「model access patterns before choosing a database」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 |

## 把全圖套進一個具體案例

**場景：** 訂單需要ACID交易、session需要毫秒讀取、分析師需要掃描多年事件。

1. 故事的起點：訂單需要ACID交易、session需要毫秒讀取、分析師需要掃描多年事件。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon RDS負責「代管關聯式database engine的provisioning、patch、backup與failover。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Aurora、Amazon DynamoDB、Amazon ElastiCache、Amazon Redshift各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon RDS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：資料模型、查詢模式、交易需求與擴展方向共同決定資料服務。
- **具體例子／邊界：** 在「訂單需要ACID交易、session需要毫秒讀取、分析師需要掃描多年事件。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Aurora

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：model access patterns before choosing a database。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### data warehouse

為重複分析、聚合與joins最佳化的columnar analytical database，不是一般低延遲OLTP transaction store。

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon RDS

- **功用：** 代管關聯式database engine的provisioning、patch、backup與failover。
- **底層機制：** DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
- **關鍵設定：** engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- **選擇時機：** 需要SQL transaction、joins、schema與managed operations。
- **替換時機：** 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。

### Amazon Aurora

- **功用：** 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。
- **底層機制：** Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。
- **關鍵設定：** cluster/instance endpoints、replica count、I/O-Optimized、backup、failover priority、parameter groups與Global Database。
- **選擇時機：** 需要高availability、較多read replicas、快速failover或AWS-native relational features。
- **替換時機：** 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

### Amazon ElastiCache

- **功用：** 提供managed Valkey/Redis OSS/Memcached記憶體data store。
- **底層機制：** Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
- **關鍵設定：** engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- **選擇時機：** session、hot reads、leaderboard、rate limiting與降低database load。
- **替換時機：** 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。

### Amazon Redshift

- **功用：** 提供columnar MPP data warehouse供大型分析與BI。
- **底層機制：** Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。
- **關鍵設定：** provisioned/serverless、node/RPU、distribution style/key、sort key、WLM、Spectrum與materialized views。
- **選擇時機：** 重複BI、複雜joins、結構化warehouse與高併發dashboard。
- **替換時機：** 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。

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

1. Amazon RDS的責任：代管關聯式database engine的provisioning、patch、backup與failover。
2. 底層機制：DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。
3. 第一個要看的設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
4. 選擇邏輯：先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。
5. 不要混淆：Amazon Aurora的責任是「提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。」；它不會自動取代Amazon RDS。
6. 替換訊號：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
7. 最常見錯法：只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。
8. 可移植原則：model access patterns before choosing a database。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon RDS | 代管關聯式database engine的provisioning、patch、backup與failover。 | DB instance執行engine；storage與backup由服務管理；Multi-AZ/read replica分別解決HA與read scale。 | 需要SQL transaction、joins、schema與managed operations。 | 極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。 |
| Amazon Aurora | 提供MySQL/PostgreSQL-compatible relational database與分散式shared storage。 | Writer與readers共享跨AZ六份storage copies；compute故障不需重建整份volume。 | 需要高availability、較多read replicas、快速failover或AWS-native relational features。 | 標準RDS有更多engine選擇且可能更便宜；NoSQL access pattern選DynamoDB。 |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| Amazon Redshift | 提供columnar MPP data warehouse供大型分析與BI。 | Leader規劃query，compute slices平行scan columnar blocks；distribution/sort影響shuffle與pruning。 | 重複BI、複雜joins、結構化warehouse與高併發dashboard。 | 偶發直接查S3用Athena；transactional OLTP用RDS/Aurora。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。 | 只有當題目條件明確改變時才可能合理。 | 只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。」之間做選擇。
- 認得常考設定：engine/version、instance/storage、Multi-AZ、backup retention、maintenance window、parameter/option group、encryption與network。
- 對應官方tasks：SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：極高key-value scale選DynamoDB；warehouse analytics選Redshift；OS/engine深度控制用EC2。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.3 Determine a new architecture for existing workloads。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：資料服務選型輸入

公司要為訂單、session 和多年分析資料選擇 database services。架構師在比較 RDS、DynamoDB、ElastiCache 和 Redshift 前，最應先完成什麼？

A. 只計算資料總容量，最大資料集一定使用 NoSQL。
B. 只依目前團隊最熟悉的查詢語言決定所有 store。
C. 選擇功能清單最長的 database，讓所有 workload 共用。
D. 列出每個 workload 的 read/write access patterns、transaction/consistency、latency、scale、retention、query shape 和 authoritative owner。

**答案：D**

- **A：** A 不足。資料量會影響 sizing，但無法判斷 joins、transaction、key access 或分析 scan；只有其他語意相同時才是主要因素。
- **B：** B 不足。團隊技能影響營運成本，但不能使不合適的資料模型滿足一致性或效能要求。
- **C：** C 錯誤。單一功能豐富服務可能同時成為 OLTP、cache 和 analytics 的瓶頸；只有 access patterns 高度一致時才可整併。
- **D：** D 正確。資料存取與一致性 contract 是服務選型的基礎，也能判斷是否需要 polyglot persistence。

**事實查證：** [Databases - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)

### 練習題 2｜SAA｜Mechanism：RDS Multi-AZ DB instance 與 read replica

一個 Amazon RDS DB instance deployment 需要 AZ 故障自動切換，另有報表讀取需要分攤到其他 endpoint。哪個敘述正確區分傳統 Multi-AZ DB instance 與 read replica？

A. Multi-AZ standby 會自動承接所有報表 reads，因此不需要 read endpoint。
B. Read replica 使用同步複寫並保證任何故障下零資料落後。
C. Multi-AZ DB instance 以同步 standby 和受管 failover 為主要目的；read replica 以非同步複寫擴展 reads，application 必須接受 lag 並使用其 endpoint。
D. 兩者都只是手動 snapshot 的不同名稱。

**答案：C**

- **A：** A 錯誤。傳統 Multi-AZ DB instance 的 standby 不服務 application reads；若是 Multi-AZ DB cluster 則有不同可讀架構，題目已限定 deployment 類型。
- **B：** B 錯誤。Read replica 一般使用非同步 replication，可能有 lag；只有 workload 能接受相應一致性時才用於 reads/DR。
- **C：** C 正確。兩者分別優化 availability/failover 與 read scaling，不能把 HA standby 當成通用 read replica。
- **D：** D 錯誤。兩者是持續複寫的部署能力，與離散時間點 snapshot 的目的不同。

**事實查證：** [What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[Multi-AZ DB instance deployments - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)、[Overview of Amazon RDS read replicas - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 練習題 3｜SAA｜Concrete setting：DynamoDB partition/sort key

訂單 API 的主要查詢是「列出某 customer 在起訖時間內的訂單」，customer 數量很多且每名 customer 有多筆訂單。哪個 DynamoDB primary key 起點最合理？

A. 所有 items 使用常數 partition key `ORDERS`，再用 FilterExpression 過濾 customer。
B. 以 customer ID 作 partition key，以時間戳加 order ID 作 sort key；其他不同 access pattern 再明確設計 GSI。
C. 只使用隨機 order ID 作 partition key，然後對全表 Scan 找 customer。
D. 每次 query 都建立一張新的 table。

**答案：B**

- **A：** A 錯誤。單一常數 key 會集中流量並使 filter 在讀取後才丟棄資料；只有極小且低流量集合才可能勉強使用。
- **B：** B 正確。Customer 維度支援等值 Query，時間排序支援 range condition，高基數 customers 也有助於分散 workload。
- **C：** C 不符合主要查詢。隨機 order ID 適合按單號取得，但找 customer 時會依賴昂貴 Scan；可作另一個 GSI access pattern。
- **D：** D 錯誤。Table 是長期資料與容量邊界，不是每次 request 的臨時物件。

**事實查證：** [Best practices for designing and using partition keys effectively in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)、[Best practices for using sort keys to organize data in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-sort-keys.html)

### 練習題 4｜SAA｜Data/request flow：cache-aside read miss

Application 使用 ElastiCache 實作 cache-aside，RDS 是 authoritative source。某 key 第一次讀取時 cache miss。哪個流程正確？

A. Application 先查 cache；miss 時查 RDS，將結果以合適 TTL 寫入 cache，再回應 client；資料更新另需定義 invalidation 或一致性策略。
B. ElastiCache 自動攔截所有 RDS network requests，application 不需 cache logic。
C. Cache miss 時建立永久空值，之後不再查 authoritative database。
D. 把 cache 視為唯一 durable truth，停用 database backup。

**答案：A**

- **A：** A 正確。Cache-aside 由 application 顯式控制 lookup、回源、填充和失效，RDS 保持權威資料。
- **B：** B 錯誤。ElastiCache 不透明代理所有 database request；application 或資料存取層必須使用 cache endpoint 和策略。
- **C：** C 錯誤。Negative caching 可短暫防止重複 miss，但必須有 TTL 並處理資料新建，不能永久遮蔽 authoritative value。
- **D：** D 錯誤。一般 cache 會 eviction、過期或故障，不應取代 durable system of record；只有服務被明確設計為 durable store 時才另論。

**事實查證：** [Caching strategies for Memcached - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)

### 練習題 5｜SAA｜Failure diagnosis：DynamoDB hot partition

DynamoDB table 的整體 consumed capacity 低於上限，但單一大型 tenant 在促銷時持續 throttled，其他 tenants 正常。最可能原因與修正方向是什麼？

A. 只提高 table 的整體 provisioned capacity；既然 aggregate capacity 還有餘裕，單一 tenant 的集中 key 一定會自動平均到所有 partitions。
B. 維持相同的單一 hot key，只依賴 DynamoDB adaptive capacity；它能消除任何單一 item 或 partition 的吞吐上限。
C. 新增一個應用不會查詢、且 partition key 仍等於 tenant ID 的 GSI；GSI 會自動重新分散 base table 的寫入。
D. 該 tenant 的 partition key/access pattern 形成 hot key；應評估 write sharding、重新分散 key、隔離 noisy tenant 或調整請求模式。

**答案：D**

- **A：** A 不足。提高 aggregate capacity 可能改善整體不足，但題目顯示只有單一 tenant 受限；若 requests 仍集中在同一 key，單純提高 table 總量不會保證流量被平均分散。
- **B：** B 錯誤。Adaptive capacity 能協助處理不均衡，但不是取消單一 item、partition 或 access pattern 的物理限制；持續 hot key 仍需要重新分散或隔離。
- **C：** C 錯誤。GSI 只建立額外的索引 access pattern，也會增加寫入工作；若 key 仍集中且應用不查詢該索引，它不會重新分配 base table 的 hot writes。
- **D：** D 正確。Aggregate capacity 可掩蓋單一 partition/key 的集中流量，修正必須改變分布或隔離，而不只是看 table 總量。

**事實查證：** [Best practices for designing and using partition keys effectively in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)

### 練習題 6｜SAA｜Comparison：relational、key-value、cache 與 warehouse

哪個敘述最正確描述 Aurora/RDS、DynamoDB、ElastiCache 和 Redshift 在常見架構中的責任？

A. ElastiCache 可取代所有 durable backups，因為 memory latency 最低。
B. Aurora/RDS 適合 relational transactions；DynamoDB 適合已知 key-based access；ElastiCache 常作非權威加速層；Redshift 適合 columnar analytics/BI。
C. Redshift 是低延遲 OLTP database，應處理每筆 checkout transaction。
D. DynamoDB 最適合任意 ad hoc joins 和全表分析，無需設計 keys。

**答案：B**

- **A：** A 錯誤。Cache node、TTL 和 eviction 不能取代獨立 recovery point；只有權威資料服務才承擔 durable truth。
- **B：** B 正確。四者依 transaction model、access pattern、耐久責任和 query shape 分工，可在同一系統中組合。
- **C：** C 錯誤。Redshift 是分析 warehouse，不是典型高頻 row-level OLTP primary；分析 workloads 才是其選擇條件。
- **D：** D 錯誤。DynamoDB 需要依 access patterns 設計 keys/indexes，不提供一般 relational ad hoc joins。

**事實查證：** [Databases - Overview of Amazon Web Services](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[Best practices for designing and using partition keys effectively in DynamoDB - Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)、[Caching strategies for Memcached - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[What is Amazon Redshift? - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html)

### 練習題 7｜SAA｜Cost/operations：Athena 與 Redshift workload

資料湖歷史檔案每月只做一次臨時 SQL 查詢；另一組資料每天被數百名使用者以複雜 joins 驅動 BI dashboard。哪個分析方案最合理？

A. 偶發 S3 查詢可評估 Athena 的 serverless per-query 模式；穩定高併發 BI 可評估 Redshift，並依資料布局、容量與 workload management 優化。
B. 兩者都配置最大 Redshift cluster，完全不看 idle 和 query pattern。
C. 兩者都在 production RDS primary 執行，以免建立資料管線。
D. 只比較每 GB storage 價格，不考慮 scan、compute、concurrency 和營運。

**答案：A**

- **A：** A 正確。低頻按查詢工作可避免常駐 capacity，高頻複雜 dashboard 則可能受益於專用 columnar warehouse 與並行管理。
- **B：** B 錯誤。最大 cluster 對偶發 workload 產生 idle，只有兩組工作都長期需要該容量時才合理。
- **C：** C 風險高。大型 analytics 會與 OLTP 競爭資源，可能影響交易延遲；只有小型、隔離且已證明安全的報表才可留在 primary。
- **D：** D 不完整。分析成本通常受掃描量、compute 時間、併發與資料布局支配，不能只看 storage。

**事實查證：** [What is Amazon Athena? - Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)、[What is Amazon Redshift? - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html)

### 練習題 8｜SAA｜SAA scenario：OLTP、session 與多年分析

電商訂單需要 ACID transaction，登入 session 需要低延遲且可過期，多年 clickstream 要供分析師掃描。哪個組合最符合各自責任？

A. 所有資料只放 ElastiCache，並停用 durable database。
B. 所有查詢都在單一 production RDS writer 執行，包括多年 full scan。
C. 以 RDS/Aurora 保存訂單 truth，以 ElastiCache 保存 session/cache，以 Redshift 或 Athena 分析歷史資料，並明確設計同步管線。
D. 只用 DynamoDB Scan 取代 warehouse，不設計 partition key 或 export。

**答案：C**

- **A：** A 錯誤。Session cache 可過期，但訂單 truth 不能依賴會 eviction 的非權威 cache。
- **B：** B 錯誤。多年分析會與 OLTP 競爭 I/O/CPU，且單一 writer 成為混合 workload 瓶頸；只有小量報表才可能接受。
- **C：** C 正確。每項服務依 transaction、latency 和 analytics query shape 分工，資料管線則維持 ownership 與新鮮度。
- **D：** D 錯誤。無條件 Scan 不會成為高效 warehouse，且忽略 DynamoDB access-pattern design。

**事實查證：** [What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[Caching strategies for Memcached - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[What is Amazon Redshift? - Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html)、[What is Amazon Athena? - Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)

### 練習題 9｜SAP｜SAP expansion：polyglot migration controls

公司要把單體 relational database 拆成訂單 store、search index、cache 和 analytics store，並逐步切換 production。哪兩項控制最重要？（選兩項）

A. 為每類資料指定 authoritative owner，定義 CDC/dual-write、schema/version、idempotency、reconciliation 與 data-quality evidence。
B. 讓每個 store 永久任意互相寫入，不定義 ownership。
C. 一次 big-bang 切換全部資料與 clients，省略 shadow reads 和 rollback。
D. 保留無監控的 dual-write，若其中一邊失敗就由人工猜測正確資料。
E. 以分階段 backfill、shadow/compare、cutover criteria 和可回復路徑遷移，清楚處理 lag、重試與失敗事件。

**答案：A、E**

- **A：** A 正確。Polyglot 架構若沒有權威 owner 和一致性/reconciliation contract，資料分歧將沒有可判定的修復來源。
- **B：** B 錯誤。任意多 writer 會產生循環更新和衝突，只有服務明確支援且業務定義衝突語意時才可採用。
- **C：** C 風險高。Big-bang 放大 blast radius 並缺乏比較證據；只有極小、可完全離線且可快速還原的系統才可能考慮。
- **D：** D 錯誤。Dual-write 必須監控部分失敗並具備重播/對帳，否則不是可靠 migration mechanism。
- **E：** E 正確。分階段驗證讓資料品質和效能在每波可觀察，且不符合 cutover criteria 時能回退。

**事實查證：** [Creating tasks for ongoing replication using AWS DMS](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html)、[AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)、[AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)

### 練習題 10｜SAP｜Multi-response：cache stampede 緩解

熱門商品的 cache keys 同時過期，數千個 requests 一起回源，RDS CPU 和連線數瞬間飽和。哪兩項做法能有效緩解 cache stampede？（選兩項）

A. 讓所有熱門 keys 在同一秒使用相同 TTL，確保一致過期。
B. 對同一 miss 使用 request coalescing/single-flight，並以受控 early refresh 避免大量 requests 同時回源。
C. 永久取消 TTL，且不提供任何 invalidation，讓資料永不更新。
D. 以 rate limit、queue/backpressure 或 connection protection 限制回源壓力，並監控 hit ratio、evictions 和 database saturation。
E. 把 cache 宣告為唯一 authoritative store，刪除 RDS。

**答案：B、D**

- **A：** A 會放大問題。同步過期讓回源流量同時爆發；只有刻意做 coordinated refresh 且有單一 loader 時才可能安全。
- **B：** B 正確。Request coalescing 讓多個相同 miss 共用一次回源結果，受控 refresh 則避免熱門 key 在到期瞬間形成 thundering herd。
- **C：** C 錯誤。永不過期會造成 stale data 和無界記憶體風險；若資料可由明確事件可靠失效，才可使用較長 TTL。
- **D：** D 正確。即使 cache 失效，系統仍需保護 authoritative database 並以指標看見退化。
- **E：** E 錯誤。一般 cache 不承擔完整 durable transaction contract；只有重新設計資料模型並選擇合適 durable store 才能移除 RDS。

**事實查證：** [Caching strategies for Memcached - Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[Caching challenges and strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCa…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「資料模型、查詢模式、交易需求與擴展方向共同決定資料服務。」，所以「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」能直接滿足它；若constraint改成「Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」。替代方案「Polyglot persistence允許不同子問題使用不同store，但增加資料同步與營運複雜度。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「資料模型、查詢模式、交易需求與擴展方向共同決定資料服務。」，排除會導致「只依資料量選資料庫，忽略join、transaction、hot key、掃描與查詢形狀。」的選項，再選「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」。本章對應的代表task包括：SAA-3.3 Determine high-performing database solutions；SAA-4.3 Design cost-optimized database solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先列出access patterns與一致性，再選RDS/Aurora、DynamoDB、ElastiCache或Redshift。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「model access patterns before choosing a database」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 8 章　Availability、Durability、Scalability 與 Elasticity

這些非功能屬性描述不同風險，不能用一個『高可用』標籤取代。

## 先建立共同語言：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：服務可短暫停機但不能遺失付款資料，且促銷時流量會在五分鐘內增加十倍。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：這些非功能屬性描述不同風險，不能用一個『高可用』標籤取代。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：像第一次看城市地圖：先分清道路、地址、建築與規則，再談哪個地標最好。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon S3負責主要工作，Amazon EC2 Auto Scaling提醒我們答案不是永遠固定。本章會走向「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：服務可短暫停機但不能遺失付款資料，且促銷時流量會在五分鐘內增加十倍。

商業需求與不能妥協的限制
          ▼
[Amazon S3：主要責任]
          │ 以HTTP API保存object，提供高durability、彈性namespace與多種storage cla…
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Amazon EC2 Auto Scaling：依健康狀態與需求訊號維持、替換並調整EC2 fleet。
  · Elastic Load Balancing：將連線或request分散到健康targets並隔離client與backend生命週期。
  · AWS Backup：以policy集中排程、保存與複製多種AWS resource backups。
可移植原則：name the property and its measurement before selecting a mechanism

失敗時先找：以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問Amazon S3有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon S3和Amazon EC2 Auto Scaling並不是兩個任意的產品名稱。前者適合本章，是因為「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」直接回應了眼前的問題；後者描述的「多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「name the property and its measurement before selecting a mechanism」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |

## 把全圖套進一個具體案例

**場景：** 服務可短暫停機但不能遺失付款資料，且促銷時流量會在五分鐘內增加十倍。

1. 故事的起點：服務可短暫停機但不能遺失付款資料，且促銷時流量會在五分鐘內增加十倍。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon S3負責「以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EC2 Auto Scaling、Elastic Load Balancing、AWS Backup各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon S3

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：這些非功能屬性描述不同風險，不能用一個『高可用』標籤取代。
- **具體例子／邊界：** 在「服務可短暫停機但不能遺失付款資料，且促銷時流量會在五分鐘內增加十倍。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EC2 Auto Scaling

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：name the property and its measurement before selecting a mechanism。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### scalability

系統增加資源後可處理更多工作且不破壞正確性的能力；仍受partition、shared dependency與quota限制。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### elasticity

容量能依需求自動增減的速度；受metrics、warm-up、quota與downstream capacity限制。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### listener

在load balancer指定protocol/port等待client connection的入口。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

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

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

## 回到 AWS：Components、功用與責任邊界

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

### Amazon EC2 Auto Scaling

- **功用：** 依健康狀態與需求訊號維持、替換並調整EC2 fleet。
- **底層機制：** Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。
- **關鍵設定：** min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
- **選擇時機：** stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。
- **替換時機：** 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。

### Elastic Load Balancing

- **功用：** 將連線或request分散到健康targets並隔離client與backend生命週期。
- **底層機制：** Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
- **關鍵設定：** scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- **選擇時機：** 多instance/task高可用入口與rolling deployment。
- **替換時機：** 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

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

## 讀到這裡，請用自己的話說一次

1. Amazon S3的責任：以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
2. 底層機制：Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
3. 第一個要看的設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
4. 選擇邏輯：Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。
5. 不要混淆：Amazon EC2 Auto Scaling的責任是「依健康狀態與需求訊號維持、替換並調整EC2 fleet。」；它不會自動取代Amazon S3。
6. 替換訊號：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
7. 最常見錯法：以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。
8. 可移植原則：name the property and its measurement before selecting a mechanism。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 | stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。 | 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 | 多instance/task高可用入口與rolling deployment。 | 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。 |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。 | 只有當題目條件明確改變時才可能合理。 | 以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。」之間做選擇。
- 認得常考設定：bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。
- 對應官方tasks：SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：四種非功能屬性的量測

產品經理提出四句要求：月可服務時間 99.95%、一年不能遺失已確認付款、經壓測可承受每秒 20,000 requests、流量增加時五分鐘內補足容量。它們依序對應什麼？

A. Availability、durability、scalability、elasticity。
B. Durability、latency、availability、backup retention。
C. 四句都只是 high availability 的不同名稱。
D. Scalability、availability、durability、固定最大容量。

**答案：A**

- **A：** A 正確。四句分別量測可服務比例、資料不遺失、可承受上限和容量調整速度。
- **B：** B 錯誤。第一句是服務可用性，不是資料 durability；第二句也不是一般 latency。
- **C：** C 錯誤。把不同風險統稱 HA 會導致機制錯配，例如用 Auto Scaling 回答資料復原。
- **D：** D 錯誤。固定最大容量描述 scalability 上限，不是 elasticity；順序也與 business statements 不符。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 2｜SAA｜Mechanism：ASG 與 ELB 分工

一個 stateless EC2 web tier 使用 Application Load Balancer 和 Auto Scaling group。哪個敘述最準確描述兩者如何共同支援 availability 與 elasticity？

A. ALB 建立新的 EC2 capacity；ASG 逐一代理每個 HTTP request。
B. ASG 維持、替換並依 policy 調整 instances；ALB 將 request 導向通過 health check 的 targets，兩者分別管理容量與流量。
C. 任一服務單獨都能保證 database durability 和 RPO=0。
D. ASG 只修改 DNS，ALB 只建立 backups。

**答案：B**

- **A：** A 顛倒責任。ASG 建立/終止 EC2，ALB 才接收並分配 application traffic。
- **B：** B 正確。Desired capacity 與 health replacement 處理 fleet，target health 與 routing 處理 client-to-backend path。
- **C：** C 錯誤。Compute scaling/load balancing 不保護權威資料，database replication 和 backup 必須另行設計。
- **D：** D 錯誤。兩者都不是 DNS-only 或 backup 服務。

**事實查證：** [Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

### 練習題 3｜SAA｜Concrete setting：target tracking policy

Web fleet 要以 `ALBRequestCountPerTarget` 作 target tracking。哪組設定思路最合理？

A. 只設定 ASG maximum，服務會自動知道理想 metric 和 target。
B. 使用所有 instances 的總 request count，完全不按 capacity 正規化。
C. 選擇能隨單位 capacity 反映需求的 metric 與可達 target，設定 min/max、instance warmup 和必要 headroom，再以 load test 驗證。
D. 把 warmup 設為零一定最佳，因為新 instance 會立即具完整 capacity。

**答案：C**

- **A：** A 不足。Target tracking 仍需 metric、target 和容量邊界，maximum 本身不會建立 scaling policy。
- **B：** B 可能形成錯誤回饋。Metric 應與 fleet capacity 近似成反比或使用 per-target 指標；總量在 scale-out 後不一定下降。
- **C：** C 正確。Metric contract、target、邊界與 warmup 共同決定控制迴路，壓測可驗證是否及時且穩定。
- **D：** D 錯誤。新 instance 尚未 ready 時若過早計入，可能造成連續擴縮；只有 workload 真正瞬時就緒時才能使用極短 warmup。

**事實查證：** [Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)

### 練習題 4｜SAA｜Data/request flow：水平擴展的 state bottleneck

促銷 requests 經 ALB 到可水平擴展的 stateless app fleet，再同步呼叫 database。App instances 增加十倍後 throughput 只提升 20%。哪個分析最合理？

A. ALB 會自動擴展 database schema，因此問題一定不在 downstream。
B. 繼續依 app CPU 增加 instances，並把吞吐未線性成長視為 warmup 誤差，不量測 database 或同步依賴。
C. 開啟 S3 versioning 可提高 database connection limit。
D. Frontend 可 scale-out，但 database connections、hot keys、local/session state 或同步 downstream 仍可能成為瓶頸；應沿 request path 量測每站 saturation。

**答案：D**

- **A：** A 錯誤。ALB 只分配流量，不管理 database schema 或容量。
- **B：** B 錯誤。已有量測顯示 app capacity 不是唯一限制；系統 throughput 受最窄依賴約束，繼續增加上游 capacity 甚至可能放大下游過載。
- **C：** C 無關。S3 object versioning 不改變 database connections 或同步 request path。
- **D：** D 正確。水平可擴展的某一層不代表端到端 scalability，必須找出 state 和 downstream capacity contract。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[How Elastic Load Balancing works - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)

### 練習題 5｜SAP｜Failure diagnosis：ASG 已到 max 仍高延遲

ASG 已擴到 maximum capacity，但 p99 latency 和 5xx 持續上升。哪個診斷順序最有效？

A. 檢查 scaling signal 是否代表需求、instance warmup/health、每層 utilization、downstream saturation、service quota 與先前 load-test ceiling，再決定調整容量或架構。
B. 先把 ASG maximum 加倍；只要能再啟動 instances，就不必檢查 database、quota、warmup 或 scaling metric 是否已失真。
C. 改用 scheduled scaling，在每天固定時刻增加容量；即使尖峰時間不可預測且 downstream 已接近上限，也不需要保留 target tracking。
D. 把 target tracking 目標調得更低以更早擴展，但不檢查 database saturation；更多 app instances 一定會線性降低 p99。

**答案：A**

- **A：** A 正確。達到 max 只是容量控制訊號，根因可能是錯誤 metric、未就緒 instances、quota 或不可擴展 downstream。
- **B：** B 是可能的局部修正，但不是完整診斷。若 maximum 過低，調高可解除控制面上限；若真正瓶頸是 quota、未就緒 instances 或 database，盲目加倍只會放大壓力。
- **C：** C 只適合時間可預測的負載。題目未證明尖峰固定，更沒有排除 downstream saturation；scheduled scaling 不能取代基於實際需求的回饋與端到端容量分析。
- **D：** D 可能改善擴展時機，但不能保證端到端吞吐。若 database 或同步依賴已飽和，更積極的 app scale-out 反而會增加連線與重試，必須先量測最窄瓶頸。

**事實查證：** [Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 6｜SAA｜Comparison：replication、backup、Multi-AZ 與 Auto Scaling

一個線上訂單系統要同時處理單一 AZ 故障、操作人員誤刪資料，以及促銷期間突增的運算需求。哪個機制分工最正確？

A. Replica 天然防止所有邏輯刪除，因此不需要 backup。
B. Backup 會自動接管 production traffic，等同 Multi-AZ failover。
C. Auto Scaling 可以保證資料 RPO=0，無需 data replication。
D. Multi-AZ/replication 支援持續服務與故障切換；backup 支援時間點恢復；Auto Scaling 支援 compute replacement/capacity，三者不能互相取代。

**答案：D**

- **A：** A 錯誤。邏輯刪除或 corruption 可能被 replication 複製，仍需隔離的 recovery points。
- **B：** B 錯誤。Backup 必須先 restore 並接回依賴，通常不是即時 traffic target。
- **C：** C 錯誤。ASG 管理 compute fleet，不控制資料一致性或 recovery point。
- **D：** D 正確。三種機制分別處理 availability、point-in-time recovery 和 capacity，應依失效模式組合。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)

### 練習題 7｜SAP｜Cost/operations：baseline 與 elastic headroom

每日流量尖峰可預測，但 instances 需要 12 分鐘 warmup，SLO 不允許尖峰開始後等待完整擴展。哪個容量策略最平衡成本與可靠性？

A. 離峰時 scale to zero，等尖峰指標觸發 target tracking 後才開始 12 分鐘 warmup。
B. 全天保留歷史最高峰兩倍容量，不再量測 idle。
C. 依可預測尖峰預先調整 baseline，保留能滿足 warmup/SLO 的 headroom，再用 target tracking 處理偏差並保護 downstream。
D. 只看日平均 CPU，忽略尖峰和啟動時間。

**答案：C**

- **A：** A 違反 SLO。Scale-to-zero 適合可等待啟動的低頻 workload，不適合明示的 12 分鐘 warmup。
- **B：** B 可能滿足容量但產生大量 idle；只有峰值隨時不可預測且成本可接受時才可能合理。
- **C：** C 正確。Scheduled/predictable baseline 解決 warmup，elastic policy 處理實際偏差，避免全天維持全部峰值容量。
- **D：** D 錯誤。平均值會掩蓋短時高需求，不能證明尖峰 SLO 或 capacity。

**事實查證：** [Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

### 練習題 8｜SAA｜SAA scenario：資料 durability 與流量 elasticity

付款 API 要求：只有 durable transaction commit 完成後才能向 client 回覆成功；單一 AZ 故障後，已確認成功的付款不得遺失；操作人員誤刪時 RPO 不得超過 5 分鐘。服務可短暫停機，而促銷流量會在五分鐘內增加十倍。哪個方案最完整？

A. 每小時把付款資料匯出到 S3，收到 API request 就先回覆成功；若 primary database 稍後失敗，再從最新匯出檔恢復。
B. 使用具交易語意與同步 Multi-AZ HA 的資料庫，只有 durable commit 成功後才回覆 client；另啟用能達到 5 分鐘 RPO 的隔離 backup/PITR 並測試還原。前端採 stateless multi-AZ compute、load balancing，並預熱或保留足夠 elastic capacity。
C. 只建立 Auto Scaling group，便可同時保證付款資料不遺失。
D. 使用非同步 read replica 作為唯一保護，primary 接受付款後立即回覆；不另做 backup，並假設 replica 永遠沒有 lag。

**答案：B**

- **A：** A 錯誤。先回覆成功再異步匯出，故障時可能遺失已被 client 視為完成的付款；每小時 recovery point 也無法滿足 5 分鐘 RPO。
- **B：** B 正確。同步 HA 與 commit acknowledgement 處理單一 AZ 故障下的已確認交易；隔離 backup/PITR 處理會被 replication 同步的誤刪；stateless multi-AZ compute 與預備容量則處理五分鐘內的流量尖峰。
- **C：** C 錯誤。ASG 只管理 compute，不建立交易資料 durability 或 point-in-time recovery。
- **D：** D 錯誤。非同步 replica 可能有 replication lag，不能單獨保證已確認 transaction 在故障後零資料遺失；它也會複製邏輯刪除，且未處理前端容量。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[Multi-AZ DB instance deployments - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)、[Restoring a DB instance to a specified time for Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)、[What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)

### 練習題 9｜SAP｜SAP expansion：端到端 availability 證據

架構文件引用多個 AWS service SLA，但主管要求證明整體 checkout 系統真的達到可用性目標。哪兩項做法最有力？（選兩項）

A. 只確認所有 resources 顯示 `running`，不執行交易。
B. 定義從使用者角度量測的 success/latency SLI、SLO 與 error budget，並把重要 dependencies 納入告警和責任。
C. 只引用 storage durability 百分比，將它視為 application availability。
D. 把各 service SLA 任意相加或相乘後當作實測結果。
E. 定期執行 failure injection、capacity/load test 和 recovery game day，以 business transaction 與實際恢復時間保存 evidence。

**答案：B、E**

- **A：** A 不足。Resource running 不代表 DNS、TLS、code、data 和 downstream 共同完成使用者交易。
- **B：** B 正確。端到端 SLI 直接量測 business outcome，dependency ownership 和 error budget 則支援持續營運決策。
- **C：** C 錯誤。Durability 衡量資料不遺失，不等於服務可接受 request 的時間比例。
- **D：** D 不足。SLA 組合可作模型輸入，但未驗證共同故障、application 行為和實際 SLO。
- **E：** E 正確。主動故障、容量與復原測試能暴露紙面架構未涵蓋的依賴，並產生可稽核證據。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[Defining Success: SLIs, SLOs, and Performance Budgets](https://docs.aws.amazon.com/solutions/latest/performance-testing/defining-success.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)

### 練習題 10｜SAP｜Multi-response：scalable 但不 elastic

哪兩個系統具備擴展架構，但不具備題目要求的快速 elasticity？（選兩項）

A. 系統可增加數百個 worker nodes，但每次擴展需人工採購、部署和設定，耗時數小時。
B. Auto Scaling 依合適 metric 在五分鐘內加入 ready instances，downstream 也已通過容量測試。
C. 架構支援水平增加 nodes，但 service quota 或 ASG maximum 阻止在尖峰時迅速增加 capacity。
D. Serverless function 隨 request 增加 concurrency，且下游能承受並在 SLO 內完成。
E. Fleet 已依預測尖峰預熱，並能自動調整小幅偏差。

**答案：A、C**

- **A：** A 正確。系統最終可 scale 到大容量，但調整速度依賴數小時人工流程，因此不夠 elastic。
- **B：** B 不符合。它同時展現可增加容量和在需求時快速調整，前提是量測結果成立。
- **C：** C 正確。架構理論上可擴展，但實際控制邊界阻止在所需時間內取得 capacity。
- **D：** D 不符合。若 concurrency 與 downstream 都在 SLO 內自動調整，這正是 elasticity 的例子。
- **E：** E 不符合。預熱 baseline 加自動修正已針對快速調整設計，除非預測誤差超過 headroom。

**事實查證：** [Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「這些非功能屬性描述不同風險，不能用一個『高可用』標籤取代。」，所以「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」能直接滿足它；若constraint改成「多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」。替代方案「多副本可改善某些風險，但同步故障、錯誤刪除與軟體bug仍需要備份與隔離。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「這些非功能屬性描述不同風險，不能用一個『高可用』標籤取代。」，排除會導致「以S3 durability數字推論應用availability，或以Auto Scaling取代容量測試。」的選項，再選「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Availability看服務是否可用，durability看資料是否遺失，scalability看上限，elasticity看調整速度。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「name the property and its measurement before selecting a mechanism」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 9 章　SLA、SLO、RTO、RPO 與 Business Requirement

技術團隊若沒有量化可接受中斷與資料遺失，就無法選擇合理成本的架構。

## 先建立共同語言：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：財務系統RPO為零且RTO十五分鐘；內部報表可接受一天資料與四小時停機。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：技術團隊若沒有量化可接受中斷與資料遺失，就無法選擇合理成本的架構。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 但請同時記住它的邊界：恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Backup，對照角色是AWS Elastic Disaster Recovery。我們選擇「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：財務系統RPO為零且RTO十五分鐘；內部報表可接受一天資料與四小時停機。

商業需求與不能妥協的限制
          ▼
[AWS Backup：主要責任]
          │ 以policy集中排程、保存與複製多種AWS resource backups。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · AWS Elastic Disaster Recovery：把server block data持續複寫到AWS低成本staging area，故障時快速launch…
  · Amazon Route 53：提供authoritative DNS、health check與多種流量政策。
可移植原則：business impact sets recovery architecture

失敗時先找：先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和AWS Elastic Disaster Recovery並不是兩個任意的產品名稱。前者適合本章，是因為「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」直接回應了眼前的問題；後者描述的「更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「business impact sets recovery architecture」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |

## 把全圖套進一個具體案例

**場景：** 財務系統RPO為零且RTO十五分鐘；內部報表可接受一天資料與四小時停機。

1. 故事的起點：財務系統RPO為零且RTO十五分鐘；內部報表可接受一天資料與四小時停機。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Elastic Disaster Recovery、Amazon Route 53各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：技術團隊若沒有量化可接受中斷與資料遺失，就無法選擇合理成本的架構。
- **具體例子／邊界：** 在「財務系統RPO為零且RTO十五分鐘；內部報表可接受一天資料與四小時停機。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Elastic Disaster Recovery

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：business impact sets recovery architecture。
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

### SLA

對外合約承諾，通常包含可用性計算、排除條款與未達成時的補償；不等於內部工程SLO或單一AWS服務SLA。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

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
4. 選擇邏輯：SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。
5. 不要混淆：AWS Elastic Disaster Recovery的責任是「把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。
8. 可移植原則：business impact sets recovery architecture。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| AWS Elastic Disaster Recovery | 把server block data持續複寫到AWS低成本staging area，故障時快速launch recovery instances。 | Agent傳送block changes到replication servers/EBS；launch template在drill/cutover建立target。 | on-premises/other cloud servers的lift-and-shift DR與低RPO。 | 雲原生database/object workload優先native replication/backup；它不自動解決app dependency order。 |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。 | 只有當題目條件明確改變時才可能合理。 | 先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：SLA、SLI、SLO、RTO 與 RPO

公司對外承諾月可用性，內部以成功交易率追蹤更嚴格目標，並為災難定義恢復時間和可接受資料回退。哪個名詞分工正確？

A. SLA 是監控 metric；SLI 是合約罰則；RTO 是可遺失資料量；RPO 是修復時間。
B. SLA 是對外服務承諾，SLI 是實際量測，SLO 是內部目標；RTO 限制服務恢復所需時間，RPO 限制可接受的資料回退點。
C. SLO 只描述 backup retention，與正常服務無關。
D. RTO 和 RPO 都是 DNS TTL 的其他名稱。

**答案：B**

- **A：** A 顛倒定義。SLI 才是量測，SLA 是服務協議；RTO/RPO 也分別處理時間與資料。
- **B：** B 正確。這些名詞把正常營運量測、內外部目標和事故復原限制分開，便於選擇適當 HA/DR 機制。
- **C：** C 錯誤。SLO 可以涵蓋 availability、latency、correctness 等正常服務目標，不等同 backup 設定。
- **D：** D 錯誤。TTL 只影響 DNS cache，不能定義完整恢復時間或資料損失容忍度。

**事實查證：** [Reliability Pillar - AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)、[Defining Success: SLIs, SLOs, and Performance Budgets](https://docs.aws.amazon.com/solutions/latest/performance-testing/defining-success.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)

### 練習題 2｜SAP｜Mechanism：backup interval、RPO 與 RTO

某系統每 15 分鐘建立 application-consistent backup，最近一次完整演練從事故宣告到恢復交易需 2 小時。哪個判讀最準確？

A. 15 分鐘同時保證 RPO=15 分鐘且 RTO=15 分鐘，無需測試。
B. 只要 backup job 顯示 completed，就能保證 application restore 成功。
C. 把 DNS TTL 設成 15 分鐘即可得到 15 分鐘 RPO。
D. Backup 間隔影響理論 recovery point；實際 RPO 還受一致性與失敗時間影響，RTO 則由 restore、依賴、容量、驗證和 cutover 的實測時間決定。

**答案：D**

- **A：** A 錯誤。建立 recovery point 和完成整個 service recovery 是不同流程，不能由同一間隔推導。
- **B：** B 錯誤。Job success 只證明備份流程完成，KMS、IAM、依賴順序或資料一致性仍可能使 restore 失敗。
- **C：** C 錯誤。DNS TTL 影響名稱切換，不建立資料 recovery point。
- **D：** D 正確。RPO 與資料時間點相關，RTO 與端到端恢復時間相關，兩者都必須以可用資料和演練證據驗證。

**事實查證：** [Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)、[What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)

### 練習題 3｜SAA｜Concrete setting：AWS Backup plan

財務資料需要每日 recovery point、七年保留、跨帳號隔離副本，並定期證明可還原。AWS Backup 設計至少應明確設定哪些項目？

A. Backup schedule/window、lifecycle/retention、resource assignment、vault/KMS、cross-account/Region copy 規則及 restore testing/驗證流程。
B. 設定每日 schedule 與七年 retention，但所有 recovery points 只留在 production account 的同一 vault，且不定期執行 restore test。
C. 設定 cross-Region copy 與七年 retention，但副本仍由同一 production account 控制，並以成功建立 recovery point 取代實際還原驗證。
D. 以 tags 指派資源並啟用 cross-account copy，但不驗證 destination vault policy、KMS key 權限、Vault Lock／immutability 要求與 restore role。

**答案：A**

- **A：** A 正確。這些設定共同決定何時保護、保留多久、保護哪些資源、隔離/加密位置及是否能實際恢復。
- **B：** B 不足。Schedule 和 retention 能建立 recovery points，但同帳號同 vault 不能滿足題目的跨帳號隔離，而且沒有 restore test 就沒有可還原證據。
- **C：** C 不足。Cross-Region copy 可處理區域性風險，卻不等於跨帳號隔離；成功備份也只證明寫入 recovery point，不能證明 application 可完整恢復。
- **D：** D 不足。Tag assignment 與 cross-account copy 是必要片段，但 destination vault/KMS policy 若不允許複製或還原，流程仍會失敗；immutability 與 restore role 也要明確驗證。

**事實查證：** [What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[Creating backup copies across AWS accounts](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)、[Restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 4｜SAP｜Data/request flow：Region failure 到 business recovery

Primary Region 故障後，公司要在 recovery Region 恢復可寫的訂單服務。哪個順序最完整？

A. 只修改 DNS，資料與依賴會自動出現在新 Region。
B. 讓兩個 Regions 同時無限制寫入，之後再決定如何處理衝突。
C. 偵測事故並 fencing 舊 writer → 選定可接受 recovery point/replica → 恢復資料及依賴 → 啟動足夠容量 → 切換入口 → 驗證 business transactions 和資料完整性。
D. 只確認 recovery Region 有 VPC，即可宣告完成。

**答案：C**

- **A：** A 不完整。DNS 只改入口，不能建立資料、keys、secrets、capacity 和 application dependencies。
- **B：** B 危險。若沒有明確 multi-writer conflict contract，雙方寫入會產生 split brain；只有服務與業務都支援時才可使用。
- **C：** C 正確。流程先防止舊站繼續衝突寫入，再恢復 state、dependencies、capacity 和入口，最後以交易證據驗收。
- **D：** D 不足。網路骨架不是可運作 workload，也不能證明 RTO/RPO。

**事實查證：** [Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)、[What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)

### 練習題 5｜SAP｜Failure diagnosis：backup 綠燈但超過 RTO

AWS Backup jobs 過去一個月全部成功，但 DR game day 恢復耗時六小時，目標是兩小時。哪個診斷最合理？

A. 先縮短 backup retention，假設 recovery point 數量是 restore 耗時的主要因素，不分解其他復原階段。
B. 量測 restore throughput、資料量、KMS/IAM、quota、dependency order、infrastructure provisioning、DNS/cutover 和人工 runbook 步驟，找出 RTO critical path。
C. S3 durability 不足一定是根因，即使 restore data 已完整。
D. 只提高 Route 53 health-check frequency，restore 會自動縮短四小時。

**答案：B**

- **A：** A 過度推論。Retention 影響保存與成本，但未提供它位於單次 restore critical path 的證據；只有量測顯示 recovery-point 管理確實主導耗時時才應優先調整。
- **B：** B 正確。Backup success 與端到端 recovery time 不同，任何資料、權限、容量、依賴或人工步驟都可能主導 RTO。
- **C：** C 與證據不符。資料已完整時，應調查恢復流程而不是假設 durability failure。
- **D：** D 不足。健康探測可能縮短偵測時間，但無法加速 data restore、provisioning 或 dependency validation。

**事實查證：** [What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)

### 練習題 6｜SAP｜Comparison：Backup、DRS、native replication 與 Route 53

企業同時有 EC2 legacy servers、RDS databases 和跨 Region DNS failover。哪個服務責任比較最準確？

A. Route 53 會複寫 EC2 disks 和 database transactions。
B. AWS Backup 會自動把所有 workloads 建成 active-active production。
C. AWS Backup 管理 recovery points；Elastic Disaster Recovery 持續複寫 supported servers 的 block data 並協助 recovery launch；service-native replication 處理特定資料服務；Route 53 只做 DNS steering。
D. DRS 是 application-level transaction replication，能理解每個業務 invariant。

**答案：C**

- **A：** A 錯誤。Route 53 不保存 workload data，只控制 DNS answer。
- **B：** B 錯誤。Backup 提供 recovery artifacts，不自動建立同時服務流量的多站應用。
- **C：** C 正確。四類能力分別處理時間點資料、server block replication、資料服務複寫與入口切換，需要按 workload 組合。
- **D：** D 錯誤。DRS 在 block/server 層複寫與 launch，不理解應用交易一致性；application quiesce 和驗證仍由客戶設計。

**事實查證：** [What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[What is Elastic Disaster Recovery? - AWS Elastic Disaster Recovery](https://docs.aws.amazon.com/drs/latest/userguide/what-is-drs.html)、[What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)

### 練習題 7｜SAP｜Cost/operations：DR 策略成本曲線

同一 workload 可選 backup/restore、pilot light、warm standby 或 multi-site active/active。哪個成本與營運判斷最合理？

A. 採 active/active 讓兩個 Region 平時都服務流量，並因沒有閒置 standby 就推定其總成本低於其他策略。
B. Backup/restore 可保證秒級 RTO，無需預先準備 capacity。
C. 只建立另一 Region 的空 VPC 就是 warm standby。
D. 通常越低的 RTO/RPO 需要越多常駐容量、複寫、自動化、fencing、監控與演練；應依 business impact 選策略並以 game day 驗證。

**答案：D**

- **A：** A 錯誤。Active/active 需要雙站容量、資料一致性、流量和營運治理，通常成本與複雜度較高。
- **B：** B 錯誤。Backup/restore 必須還原資料與建立 capacity，通常適合較寬鬆 RTO；只有極小且高度自動化 workload 才可能很快。
- **C：** C 錯誤。Warm standby 必須有縮小但可運作的 workload stack、資料和依賴，不能只有網路外殼。
- **D：** D 正確。恢復目標是成本/複雜度驅動因素，策略必須匹配業務損失而非一律追求最高級別。

**事實查證：** [Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)

### 練習題 8｜SAA｜SAA scenario：寬鬆目標的 cost-effective DR

內部報表系統可停機四小時，並可接受最多一天資料遺失。使用者很少，常駐第二套 production 會造成明顯浪費。哪個方案最 cost-effective？

A. 建立符合一天 RPO 的排程 backup，保存可重建 infrastructure/runbook，並實測能在四小時內還原資料、依賴和服務。
B. 跨兩 Region active-active 同步寫入所有報表資料。
C. 建立零資料損失同步 dual-write，即使 application 不支援衝突處理。
D. 只建立 Route 53 failover record，不備份資料或準備 capacity。

**答案：A**

- **A：** A 正確。較寬鬆 RPO/RTO 可由 backup/restore 滿足，前提是完整流程已證明在四小時內完成。
- **B：** B 過度配置。Active-active 可降低部分恢復時間，但題目不需要，會增加常駐成本與資料複雜度。
- **C：** C 過度配置且有風險。近零 RPO 不符合成本優先的業務需求，無衝突設計還可能破壞資料。
- **D：** D 不完整。DNS 只能指向 endpoint，沒有資料與 capacity 的站點無法服務。

**事實查證：** [What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)

### 練習題 9｜SAP｜SAP expansion：近零資料損失與 15 分鐘恢復

財務交易要求近零資料損失、Region 災難後 15 分鐘內恢復。哪兩項設計責任不可省略？（選兩項）

A. 每 15 分鐘建立一次 snapshot，便可宣稱 RPO 接近零。
B. 只把 DNS TTL 設為 30 秒，資料和 writer fencing 會自動完成。
C. 選擇能滿足一致性與 replication lag 目標的 data architecture，持續量測 lag，並定義 promotion/fencing 與 conflict semantics。
D. 讓兩個 Regions 無條件 multi-writer，但不指定衝突處理或權威 owner。
E. 在 recovery Region 準備足夠 capacity、keys/identity 和依賴，以自動化順序切換，並定期 game day 驗證 15 分鐘及 failback。

**答案：C、E**

- **A：** A 不符合近零 RPO。15 分鐘 snapshot 理論上可回退接近 15 分鐘，且還要考慮一致性和失敗時點。
- **B：** B 不足。TTL 只控制部分 DNS cache，不能複寫資料、阻止 split brain 或啟動 capacity。
- **C：** C 正確。近零資料損失的核心是可量測的 replication 與單一/受控寫入語意，而非口頭標記。
- **D：** D 危險。沒有 conflict contract 的 multi-writer 會使財務資料不可判定，不能視為高可用。
- **E：** E 正確。15 分鐘 RTO 是完整 workload 目標，需要可立即使用的依賴、自動化和反覆演練。

**事實查證：** [Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)、[Disaster recovery options in the cloud - Disaster Recovery of Workloads on AWS: Recovery in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)、[What is Amazon Route 53? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)

### 練習題 10｜SAP｜Multi-response：證明 DR 目標達成

哪兩項 evidence 最能證明 workload 已達成承諾的 RTO/RPO，而不只是「有備份」？（選兩項）

A. 定期 restore/failover 演練的時間線，記錄 incident start、資料 recovery point、各階段耗時、實際 RTO/RPO 與偏差。
B. Backup console 顯示最近一個 job 為 `Completed`。
C. Recovery Region 中存在一些 standby resources，但從未接過流量。
D. 在 recovery endpoint 執行代表性 business transactions，驗證資料完整性、讀寫能力、identity、依賴和使用者可用性。
E. 架構圖上標示 `Multi-Region`。

**答案：A、D**

- **A：** A 正確。時間線直接量測資料回退和端到端恢復時間，也能找出超標的 critical path。
- **B：** B 不足。Job completed 只證明建立 recovery artifact，沒有證明可解密、可還原或在時限內上線。
- **C：** C 不足。未經流量與資料驗證的 standby 可能缺少容量、設定或依賴。
- **D：** D 正確。Business transaction 是恢復成功的使用者層證據，可避免只驗證 resource 狀態。
- **E：** E 不足。圖面描述意圖，不是運作證據；必須由實際演練和監控支撐。

**事實查證：** [Disaster Recovery (DR) objectives - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html)、[What is AWS Backup? - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「技術團隊若沒有量化可接受中斷與資料遺失，就無法選擇合理成本的架構。」，所以「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」能直接滿足它；若constraint改成「更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」。替代方案「更低RTO/RPO通常需要更多常駐容量、自動化、同步複寫與演練。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「技術團隊若沒有量化可接受中斷與資料遺失，就無法選擇合理成本的架構。」，排除會導致「先選active-active再問需求，容易付出高成本卻仍沒有經過驗證的恢復流程。」的選項，再選「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「SLO定義正常目標，RTO限制恢復時間，RPO限制可接受資料落後，再映射到HA與DR。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「business impact sets recovery architecture」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 10 章　Shared Responsibility 與六大 Pillars

雲端供應商負責部分基礎設施，但客戶仍擁有資料、身份、設定與工作負載風險。

## 先建立共同語言：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：EC2與Lambda都處理敏感資料，團隊要分清OS patch、runtime、code與IAM責任。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：雲端供應商負責部分基礎設施，但客戶仍擁有資料、身份、設定與工作負載風險。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，像第一次看城市地圖：先分清道路、地址、建築與規則，再談哪個地標最好。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Well-Architected Framework如何接手工作，再看Shared Responsibility Model何時更合適，最後用設定與考題驗證「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：EC2與Lambda都處理敏感資料，團隊要分清OS patch、runtime、code與IAM責任。

商業需求與不能妥協的限制
          ▼
[AWS Well-Architected Framework：主要責任]
          │ 用六個pillars系統化檢視workload架構與營運風險。
          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果
          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore
本章其他角色：
  · Shared Responsibility Model：區分AWS負責cloud infrastructure與customer負責cloud內資料、身份、設定及…
可移植原則：managed does not mean unmanaged responsibility

失敗時先找：將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「先建立共同語言」。先不要急著問AWS Well-Architected Framework有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Well-Architected Framework和Shared Responsibility Model並不是兩個任意的產品名稱。前者適合本章，是因為「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」直接回應了眼前的問題；後者描述的「Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「managed does not mean unmanaged responsibility」。更白話地說：先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Well-Architected Framework | 用六個pillars系統化檢視workload架構與營運風險。 | 以questions、best practices與improvement plan把business context映射到security、reliability等trade-offs。 |
| Shared Responsibility Model | 區分AWS負責cloud infrastructure與customer負責cloud內資料、身份、設定及workload。 | 責任隨IaaS、container與managed/serverless抽象移動，但customer永遠保留資料分類與access決策。 |

## 把全圖套進一個具體案例

**場景：** EC2與Lambda都處理敏感資料，團隊要分清OS patch、runtime、code與IAM責任。

1. 故事的起點：EC2與Lambda都處理敏感資料，團隊要分清OS patch、runtime、code與IAM責任。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Well-Architected Framework負責「用六個pillars系統化檢視workload架構與營運風險。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：以questions、best practices與improvement plan把business context映射到security、reliability等trade-offs。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Shared Responsibility Model各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「它是決策框架，不會自動部署controls或修復resources。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Well-Architected Framework

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：雲端供應商負責部分基礎設施，但客戶仍擁有資料、身份、設定與工作負載風險。
- **具體例子／邊界：** 在「EC2與Lambda都處理敏感資料，團隊要分清OS patch、runtime、code與IAM責任。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Shared Responsibility Model

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：managed does not mean unmanaged responsibility。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### shared responsibility

AWS負責cloud本身的基礎設施；customer負責cloud內的資料、身份、設定與workload。服務越managed，責任會移動但不會消失。

### managed service

供應商接手部分基礎設施責任的服務；customer仍負責資料、身份、設定、access pattern與business correctness。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### pillar

Well-Architected用來檢視架構的一個品質維度：operational excellence、security、reliability、performance efficiency、cost optimization與sustainability。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS Well-Architected Framework

- **功用：** 用六個pillars系統化檢視workload架構與營運風險。
- **底層機制：** 以questions、best practices與improvement plan把business context映射到security、reliability等trade-offs。
- **關鍵設定：** workload definition、milestones、pillar questions、high-risk issues與improvement priorities。
- **選擇時機：** 設計審查、現有系統改善與SAP多constraint scenario。
- **替換時機：** 它是決策框架，不會自動部署controls或修復resources。

### Shared Responsibility Model

- **功用：** 區分AWS負責cloud infrastructure與customer負責cloud內資料、身份、設定及workload。
- **底層機制：** 責任隨IaaS、container與managed/serverless抽象移動，但customer永遠保留資料分類與access決策。
- **關鍵設定：** service abstraction、data owner、IAM、network exposure、encryption、patching與logging responsibility。
- **選擇時機：** 判斷某個安全或營運工作應由誰完成。
- **替換時機：** Managed不等於免責；若需要OS控制，選EC2也同時接回patch/hardening責任。

## 考前與實作時再查：設定操作手冊

### AWS Well-Architected Framework：逐項設定說明

#### `workload definition`

- **控制什麼：** `workload definition`定義AWS Well-Architected Framework管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `milestones`

- **控制什麼：** `milestones`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `pillar questions`

- **控制什麼：** `pillar questions`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `high-risk issues`

- **控制什麼：** `high-risk issues`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「設計審查、現有系統改善與SAP多constraint scenario。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Well-Architected Framework的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `improvement priorities`

- **控制什麼：** `improvement priorities`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

### Shared Responsibility Model：逐項設定說明

#### `service abstraction`

- **控制什麼：** `service abstraction`用來判斷shared-responsibility邊界：誰決定資料、入口、OS/runtime更新，以及managed service接手到哪一層。
- **何時需要：** 比較EC2、container與serverless，或事故後判斷哪個team/vendor應預防、偵測與修復時。
- **怎麼設定／驗證：** 為每層建立RACI：AWS、platform、application、security與data owner；將patch、IAM、encryption、backup與logging責任寫進runbook。
- **常見錯法：** Managed不代表customer免責；AWS patch hypervisor不會替你修application dependency，private subnet也不代表資料已授權。

#### `data owner`

- **控制什麼：** `data owner`用來判斷shared-responsibility邊界：誰決定資料、入口、OS/runtime更新，以及managed service接手到哪一層。
- **何時需要：** 比較EC2、container與serverless，或事故後判斷哪個team/vendor應預防、偵測與修復時。
- **怎麼設定／驗證：** 為每層建立RACI：AWS、platform、application、security與data owner；將patch、IAM、encryption、backup與logging責任寫進runbook。
- **常見錯法：** Managed不代表customer免責；AWS patch hypervisor不會替你修application dependency，private subnet也不代表資料已授權。

#### `IAM`

- **控制什麼：** `IAM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「判斷某個安全或營運工作應由誰完成。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Shared Responsibility Model明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `network exposure`

- **控制什麼：** `network exposure`用來判斷shared-responsibility邊界：誰決定資料、入口、OS/runtime更新，以及managed service接手到哪一層。
- **何時需要：** 比較EC2、container與serverless，或事故後判斷哪個team/vendor應預防、偵測與修復時。
- **怎麼設定／驗證：** 為每層建立RACI：AWS、platform、application、security與data owner；將patch、IAM、encryption、backup與logging責任寫進runbook。
- **常見錯法：** Managed不代表customer免責；AWS patch hypervisor不會替你修application dependency，private subnet也不代表資料已授權。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「判斷某個安全或營運工作應由誰完成。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Shared Responsibility Model指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `patching`

- **控制什麼：** `patching`用來判斷shared-responsibility邊界：誰決定資料、入口、OS/runtime更新，以及managed service接手到哪一層。
- **何時需要：** 比較EC2、container與serverless，或事故後判斷哪個team/vendor應預防、偵測與修復時。
- **怎麼設定／驗證：** 為每層建立RACI：AWS、platform、application、security與data owner；將patch、IAM、encryption、backup與logging責任寫進runbook。
- **常見錯法：** Managed不代表customer免責；AWS patch hypervisor不會替你修application dependency，private subnet也不代表資料已授權。

#### `logging responsibility`

- **控制什麼：** `logging responsibility`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「判斷某個安全或營運工作應由誰完成。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Shared Responsibility Model選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

## 讀到這裡，請用自己的話說一次

1. AWS Well-Architected Framework的責任：用六個pillars系統化檢視workload架構與營運風險。
2. 底層機制：以questions、best practices與improvement plan把business context映射到security、reliability等trade-offs。
3. 第一個要看的設定：workload definition、milestones、pillar questions、high-risk issues與improvement priorities。
4. 選擇邏輯：逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。
5. 不要混淆：Shared Responsibility Model的責任是「區分AWS負責cloud infrastructure與customer負責cloud內資料、身份、設定及workload。」；它不會自動取代AWS Well-Architected Framework。
6. 替換訊號：它是決策框架，不會自動部署controls或修復resources。
7. 最常見錯法：將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。
8. 可移植原則：managed does not mean unmanaged responsibility。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Well-Architected Framework | 用六個pillars系統化檢視workload架構與營運風險。 | 以questions、best practices與improvement plan把business context映射到security、reliability等trade-offs。 | 設計審查、現有系統改善與SAP多constraint scenario。 | 它是決策框架，不會自動部署controls或修復resources。 |
| Shared Responsibility Model | 區分AWS負責cloud infrastructure與customer負責cloud內資料、身份、設定及workload。 | 責任隨IaaS、container與managed/serverless抽象移動，但customer永遠保留資料分類與access決策。 | 判斷某個安全或營運工作應由誰完成。 | Managed不等於免責；若需要OS控制，選EC2也同時接回patch/hardening責任。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。 | 只有當題目條件明確改變時才可能合理。 | 將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。」之間做選擇。
- 認得常考設定：workload definition、milestones、pillar questions、high-risk issues與improvement priorities。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：它是決策框架，不會自動部署controls或修復resources。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜Purpose：Shared Responsibility Model

團隊準備把自管 application 搬到多種 AWS 服務。Shared Responsibility Model 最重要的用途是什麼？

A. 證明 AWS 負責所有 security、availability 和 application correctness。
B. 要求客戶維護 AWS data center、實體網路和 hypervisor。
C. 針對每個服務與層次，界定 AWS 和客戶各自要預防、設定、監控及修復哪些風險；服務抽象只會移動部分責任。
D. 證明使用 managed service 後不再需要資料分類、IAM 或 logging。

**答案：C**

- **A：** A 錯誤。AWS 負責 cloud infrastructure，但客戶仍擁有 workload 設計、資料、identity 和配置責任。
- **B：** B 錯誤。實體設施與 hypervisor 通常屬 AWS 的 security of the cloud，客戶不直接維護。
- **C：** C 正確。模型不是一句口號，而是逐服務辨識 owner，避免風險落在「以為對方負責」的空白區。
- **D：** D 錯誤。Managed 會降低 host operations，但資料治理、access、application logic 和監控仍由客戶決定。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)

### 練習題 2｜SAA｜Mechanism：EC2、RDS、Lambda 的 patching 責任

同一家公司分別在 EC2、Amazon RDS 和 Lambda 執行 workload。隨服務抽象提高，patching 責任如何變化？

A. AWS 一直維護底層設施；客戶在 EC2 管 guest OS，在 RDS/Lambda 減少 host/OS/runtime platform 維護，但仍負責 code、data、IAM、network/config 和應用正確性。
B. 只要啟用 Lambda managed runtime 更新，部署套件內的第三方 dependencies 也會由 AWS 連同函式 code 一起修補。
C. RDS database users、schema 和 query 權限由 AWS 自動依業務需求決定。
D. EC2 hypervisor 和資料中心網路由客戶修補。

**答案：A**

- **A：** A 正確。抽象層越高，AWS 接手更多底層 platform operations，但客戶的 workload 和資料責任不會消失。
- **B：** B 錯誤。AWS 管理 Lambda platform/runtime 基礎，但部署套件、函式 code 和其 dependencies 仍屬客戶供應鏈。
- **C：** C 錯誤。RDS 管理 database infrastructure 的多項操作，客戶仍設計 users、schema、queries 和資料授權。
- **D：** D 錯誤。Hypervisor 和實體設施屬 AWS；客戶在 EC2 負責 guest OS、application 和配置。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)、[What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)

### 練習題 3｜SAP｜Concrete setting：可稽核 Well-Architected review

企業要把 Well-Architected review 轉成可治理的季度流程。哪組紀錄最能支援稽核與改善？

A. 每季重新回答 lens questions，但不在第一次 review 後建立 baseline milestone，因此無法比較風險何時出現或消失。
B. 記錄 HRI/MRI 與 remediation owner，但不設定期限、驗證 evidence 或完成條件；owner 口頭表示完成就關閉 finding。
C. 只匯出季度報告存檔，不把 improvement items 連到 owner、優先級、due date、變更紀錄與後續 milestone。
D. 記錄 workload scope/owner、pillar questions、辨識出的 HRI/MRI、優先級、改善 owner、期限與驗證 evidence；初次 review 完成後先保存 baseline milestone，重大變更或改善完成後再建立後續 milestone。

**答案：D**

- **A：** A 不足。沒有初始 baseline milestone，就缺少可稽核的起點；每季答案仍可閱讀，但無法可靠重建兩個時間點間的改善差異。
- **B：** B 不足。Finding、owner 是必要欄位，但沒有 deadline、acceptance criteria 與 evidence，治理流程無法判斷風險是否真正降低。
- **C：** C 不足。靜態報告保留當期內容，卻沒有 remediation loop；缺少責任、期限與後續 milestone 時，無法證明改善已執行。
- **D：** D 正確。初次 review 完成後先保存 baseline milestone，才能留下可比較的起點；重大變更或改善完成後再建立後續 milestone，便能把問題、責任、期限、驗證 evidence 與風險變化連成可追蹤的 improvement program。

**事實查證：** [What is AWS Well-Architected Tool? - AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)、[Milestones - AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)

### 練習題 4｜SAA｜Data/request flow：敏感資料沿路的責任標註

敏感資料由 public API 進入 Lambda，以 KMS key 保護後寫入 database。哪個責任標註最合理？

A. 只要使用 KMS，AWS 就會依業務需求自動決定哪些 principals 可解密。
B. AWS 維護 API、Lambda、KMS 和 database 的底層服務；客戶仍設計 identity、network exposure、key policy、資料分類、code validation、logging 和 retention。
C. 把 Lambda 放 private subnet 即代表所有 requests 已獲應用授權。
D. 啟用 CloudTrail 後可移除 application authorization，因為所有事件已有記錄。

**答案：B**

- **A：** A 錯誤。KMS 執行客戶設定的 key policy/grants 與服務整合，不知道業務角色應獲得何種權限。
- **B：** B 正確。AWS 接手服務基礎設施，客戶則沿 data path 定義誰可呼叫、可解密、可保存多久及如何證明。
- **C：** C 錯誤。Network locality 不等於身份驗證或業務授權；private workload 仍需要 IAM/application policy。
- **D：** D 錯誤。Audit log 記錄行為但不阻止未授權 request，detective control 不能取代 preventive authorization。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)

### 練習題 5｜SAP｜Failure diagnosis：managed S3 public exposure

敏感 S3 bucket 因 bucket policy 設定錯誤而公開。團隊主張「S3 是 managed service，所以這是 AWS 的責任」。最正確的診斷是什麼？

A. 只啟用 SSE-KMS encryption，保留原 public bucket policy；資料已加密，所以匿名 request 會自動失去讀取權限。
B. 只移除某個 IAM role 的 identity policy，不檢查仍允許 `Principal: *` 的 bucket policy、access point policy 或 ACL。
C. 客戶仍負責資料分類、IAM/bucket policy、Block Public Access、encryption 選擇、logging 和設定審查；應修正 control 與 ownership 並驗證暴露範圍。
D. 先啟用 Block Public Access 阻止 public access，但不移除錯誤 policy、不調查 access logs 與已暴露資料，也不建立防止復發的 configuration control。

**答案：C**

- **A：** A 錯誤。Encryption at rest 與 authorization 是兩個控制面；SSE-KMS 不會自動撤銷一條允許匿名讀取的 resource policy，仍須修正有效存取權限。
- **B：** B 錯誤。S3 authorization 會綜合 identity policy、bucket/access-point policy、ACL 與 Block Public Access；只移除一條 IAM policy 不能排除其他公開路徑。
- **C：** C 正確。Managed storage 不替客戶決定誰可讀資料，事故根因是可配置 control 與責任流程失效。
- **D：** D 是必要的緊急 containment 片段，但不是完整診斷與 remediation。團隊仍須移除錯誤 policy、確認哪些 principals 曾存取資料，並以持續 controls 防止復發。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)、[What is Amazon S3? - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)、[Blocking public access to your Amazon S3 storage - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)

### 練習題 6｜SAP｜Comparison：六大 pillars 與 trade-off

Well-Architected review 發現加強 encryption、增加 Multi-AZ capacity 和延長必要 logs 都會提高成本。團隊要排定 improvement plan、記錄風險接受並在下一次 review 驗證結果。應如何使用六大 pillars 做持續改善決策？

A. 六大 pillars 是六個必須全部部署的 AWS 服務。
B. 以 business context 平衡 operational excellence、security、reliability、performance efficiency、cost optimization 和 sustainability，先滿足風險/合規硬限制，再記錄可接受 trade-off。
C. 只選 security pillar，其他 pillars 與架構無關。
D. Cost optimization 等同選帳單最低的方案，即使違反合規與 RTO。

**答案：B**

- **A：** A 錯誤。Pillars 是審查觀點和 best practices，不是產品清單。
- **B：** B 正確。Framework 用多個觀點揭露取捨，最終仍由業務、風險和約束決定優先級與接受的剩餘風險。
- **C：** C 錯誤。Security 重要但不能單獨代表 availability、operations、performance、cost 或 sustainability。
- **D：** D 錯誤。Cost optimization 是以達成需求的最低浪費取得價值，不是用較低價格違反 hard constraints。

**事實查證：** [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

### 練習題 7｜SAA｜Cost/operations：managed service 的總成本

團隊比較自管 EC2 database 與 Amazon RDS。哪個總成本評估最完整？

A. 比較服務費、idle/capacity、license、patch/backup/on-call 人力、失敗風險、migration effort 和所需技能，再確認兩者是否滿足功能與控制需求。
B. 因 RDS 移轉部分主機維護責任，就直接把它判定為最低 TCO，不再估算規模、license、I/O 或功能限制。
C. 因 EC2 的資源標價可能較低，就把既有 database 團隊的人力視為 sunk cost，不計 patch、backup、on-call 或失敗風險。
D. 只比較每 GB storage 標價，忽略 database operations。

**答案：A**

- **A：** A 正確。受管服務用較高部分服務費換取營運責任轉移，應以完整 TCO 和需求符合度比較。
- **B：** B 錯誤。Managed 通常降低操作面，但在特定規模、license 或控制需求下未必成本最低。
- **C：** C 錯誤。Patch、backup、on-call 和 failure risk 會消耗真實資源，不能從 TCO 移除。
- **D：** D 不完整。Storage 只是 database 成本的一部分，compute、I/O、availability 和人力常同樣重要。

**事實查證：** [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)、[What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)

### 練習題 8｜SAA｜SAA scenario：EC2 與 Lambda 處理 PII

EC2 web application 和 Lambda function 都處理 PII。關於客戶責任，哪個敘述正確？

A. Lambda 是 serverless，因此客戶不再負責 code、IAM、data protection 或 logging。
B. AWS 會為 EC2 application code 自動修補所有第三方 libraries。
C. 服務會自動指定企業內部的資料 owner 和 retention policy。
D. EC2 客戶另需管理 guest OS；兩種服務都仍需由客戶保護 application code、IAM、PII、network/config、secrets 和 logging。

**答案：D**

- **A：** A 錯誤。Serverless 移除 server fleet 管理，不移除 workload security 和資料責任。
- **B：** B 錯誤。AWS 管理 EC2 基礎設施，客戶管理 guest OS 與 application packages。
- **C：** C 錯誤。資料 owner、分類和 retention 是組織/客戶決策，AWS 服務只能執行已設定 policy。
- **D：** D 正確。EC2 暴露更多 OS 責任，但兩種 compute model 共享 code、identity、data 和配置責任。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)、[What is Amazon EC2? - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)、[What is AWS Lambda? - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)

### 練習題 9｜SAP｜SAP expansion：多帳號 improvement program

企業要把數百個帳號的 Well-Architected findings 轉成可持續改善計畫，而不是一次性報告。哪兩項做法最重要？（選兩項）

A. 建立 central standards/guardrails 與 delegated owners，依 risk、business impact 和依賴排優先級，讓每個 finding 有期限與驗證方式。
B. 把所有 remediation 都交給 management account 的單一永久 Administrator role。
C. 只匯出 PDF 存檔，不追蹤 owner、進度或驗證 evidence。
D. 把所有風險視為同一優先級，在同一天 big-bang 修改全部帳號。
E. 版本化 controls，以 canary/分波 rollout 與 rollback 管理變更，收集 evidence，並在 milestones 重新審查剩餘風險。

**答案：A、E**

- **A：** A 正確。中央標準和分散 owner 同時提供一致性與執行責任，風險排序則讓有限資源先處理最大影響。
- **B：** B 錯誤。Management account 集中永久管理權限會擴大 blast radius，且使服務 owner 無法承擔日常改善。
- **C：** C 不足。靜態報告沒有 remediation loop，不能證明風險已降低。
- **D：** D 風險高。不同 findings 的依賴與影響不同，未測試 big-bang 會放大 production 事故。
- **E：** E 正確。版本化、分波、rollback 和 milestone evidence 讓 controls 可安全演進並可稽核。

**事實查證：** [What is AWS Well-Architected Tool? - AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)、[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)、[AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)

### 練習題 10｜SAA → SAP｜Multi-response：RDS 的客戶責任

團隊從自管 EC2 database 遷移到 Amazon RDS。哪兩項工作仍由客戶負責？（選兩項）

A. 修補 RDS database host 的作業系統。
B. 管理 database users、schema、queries、資料品質與 application transaction correctness。
C. 設定並驗證 network access、IAM/database authentication、encryption choices、backup retention 和 restore requirements。
D. 更換 AWS data center 中故障的實體 disks。
E. 維護承載 RDS 的 hypervisor。

**答案：B、C**

- **A：** A 不由客戶負責。RDS 受管服務接手 host OS 維護；客戶仍需安排 engine maintenance window 和應用相容性。
- **B：** B 正確。RDS 不知道企業資料模型與業務 invariant，users、schema、query 和 application correctness 仍是客戶工作。
- **C：** C 正確。這些都是服務暴露給客戶的安全與復原 controls，設定存在不代表已自動符合需求。
- **D：** D 不由客戶負責。AWS 維護實體 storage infrastructure。
- **E：** E 不由客戶負責。Hypervisor 和底層 host platform 屬 AWS 的 cloud infrastructure 責任。

**事實查證：** [Shared responsibility - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)、[What is Amazon Relational Database Service (Amazon RDS)? - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「雲端供應商負責部分基礎設施，但客戶仍擁有資料、身份、設定與工作負載風險。」，所以「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」能直接滿足它；若constraint改成「Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」。替代方案「Managed service能降低操作面，卻不會替客戶決定資料分類、IAM政策與應用正確性。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「雲端供應商負責部分基礎設施，但客戶仍擁有資料、身份、設定與工作負載風險。」，排除會導致「將『AWS負責安全』理解成不需patch guest OS、不需備份或不需限制public access。」的選項，再選「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAP-1.2 Prescribe security controls。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「逐服務判斷AWS管理到哪一層，再用六大pillar平衡安全、可靠、效能、成本、營運與永續。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「managed does not mean unmanaged responsibility」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
