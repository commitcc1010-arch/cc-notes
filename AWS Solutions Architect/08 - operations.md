---
title: "Deployment 與 Operations"
part: 7
as_of: 2026-10-01
---

# Part 7　Deployment 與 Operations

# 第 72 章　CloudFormation 與 Infrastructure as Code

手動console操作不可重現、難review，也無法可靠建立多帳號多Region環境。

## 跟著一次變更走到production：先從故事開始

如果今天由你值班，收到的需求可能是這樣：同一三層架構需部署dev、staging、prod與DR Region。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：手動console操作不可重現、難review，也無法可靠建立多帳號多Region環境。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：IaC像建築藍圖：它讓每次施工有一致依據，也能在動工前看出哪些牆會被拆掉重建。 這只是起點，因為藍圖不會自動保護資料；replacement、secret、drift與部署順序仍需明確設計。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS CloudFormation承接主要責任，以AWS CDK檢查替代條件，並用「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：同一三層架構需部署dev、staging、prod與DR Region。

Git中的Infrastructure as Code
      │ review / test
      ▼
Template + parameters
      │ create Change Set
      ▼
預覽：新增、修改、replacement、delete
      │ approval
      ▼
CloudFormation依dependency順序建立resources
      │
      ├─ 成功：保存stack state與outputs
      └─ 失敗：rollback；資料型resource另需retention保護

同一份設計以不同parameters部署dev、prod與DR，而不是手動重做。

失敗時先找：在production手改資源後template不知情，下一次deploy覆蓋或失敗。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS CloudFormation有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS CloudFormation和AWS CDK並不是兩個任意的產品名稱。前者適合本章，是因為「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」直接回應了眼前的問題；後者描述的「CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：在production手改資源後template不知情，下一次deploy覆蓋或失敗。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「infrastructure changes deserve versioned code and review」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 |
| AWS CDK | 以程式語言constructs定義AWS基礎設施，再合成CloudFormation templates部署。 | CDK app建立construct tree；synth產生template與assets metadata，deploy仍由CloudFormation建立change set和管理resource state。 |

## 把全圖套進一個具體案例

**場景：** 同一三層架構需部署dev、staging、prod與DR Region。

1. 故事的起點：同一三層架構需部署dev、staging、prod與DR Region。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS CloudFormation負責「以declarative templates建立、更新與刪除AWS resources。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS CDK各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「在production手改資源後template不知情，下一次deploy覆蓋或失敗。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### CloudFormation Guard 與 Custom Resource：一個在部署前說不，一個把 CloudFormation 做不到的事接進生命週期

Guard 是 policy-as-code evaluator：拿 YAML/JSON 與規則比對，適合 shift-left；CloudFormation Hooks 才能在server side 阻擋 create/update/delete。Custom Resource 則讓 CloudFormation 把 Create/Update/Delete request 送給 Lambda/SNS provider，等待它回 SUCCESS/FAILED。

```text
template ─ cfn-lint ─ Guard rules ─ change set ─ CloudFormation
                                                   │
                                      built-in resource or Custom::Thing
                                                   │ request + ResponseURL
                                                   ▼
                                              Lambda provider
                                                   │ SUCCESS/FAILED
                                                   └──────────────> stack continues/rolls back
```

#### Guard rule與Custom Resource各自最小的樣子

```Guard + YAML
# Guard: policy check, not template syntax validation
rule encrypted_buckets {
  AWS::S3::Bucket Properties.BucketEncryption exists
}

# CloudFormation: lifecycle extension
MyExternalObject:
  Type: Custom::ExternalObject
  Properties:
    ServiceToken: !GetAtt ProviderFunction.Arn
    Name: invoice-schema
```

1. cfn-lint 檢查 template structure；Guard 檢查你定義的政策；Hook 才是 CloudFormation control-plane enforcement。
2. Custom Resource provider 必須對 Create/Update/Delete 冪等，並一定回覆 pre-signed ResponseURL；漏回覆會讓 stack 等到 timeout。
3. PhysicalResourceId 若不穩定，update 可能被視為 replacement；delete path 也必須能清理外部資源。

**選擇邊界：** 只需標準資源時不要用 Custom Resource；能用 Registry extension 時可得到較完整 CRUDL/drift model。Guard 適合 CI policy test，組織級不可繞過控制再加 Hooks、SCP、Config 等。

**考試範圍：** SAA 會辨識 IaC、change set、rollback；custom resource lifecycle、Guard/Hook enforcement、跨帳號 pipeline 與 policy rollout 是 SAP 深度。

- [AWS：CloudFormation custom resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html)
- [AWS：What is CloudFormation Guard?](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)

## 需要時再查：四個閱讀支點

### AWS CloudFormation

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：手動console操作不可重現、難review，也無法可靠建立多帳號多Region環境。
- **具體例子／邊界：** 在「同一三層架構需部署dev、staging、prod與DR Region。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS CDK

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：在production手改資源後template不知情，下一次deploy覆蓋或失敗。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：infrastructure changes deserve versioned code and review。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### dependency graph

以nodes/edges表示application、database、network、identity與外部系統的依賴，幫助避免把強耦合元件拆到不同waves。

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### change set

CloudFormation在執行前計算預計新增、修改、刪除或替換哪些resources，供review但不保證application side effects。

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### stack

CloudFormation以一個生命週期單位管理的一組resources；更新與刪除行為受dependencies及policies影響。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

## 回到 AWS：Components、功用與責任邊界

### AWS CloudFormation

- **功用：** 以declarative templates建立、更新與刪除AWS resources。
- **底層機制：** CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。
- **關鍵設定：** Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
- **選擇時機：** repeatable environment、reviewable IaC與cross-account StackSets。
- **替換時機：** 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。

### AWS CDK

- **功用：** 以程式語言constructs定義AWS基礎設施，再合成CloudFormation templates部署。
- **底層機制：** CDK app建立construct tree；synth產生template與assets metadata，deploy仍由CloudFormation建立change set和管理resource state。
- **關鍵設定：** app/stacks、constructs、context、bootstrap、assets、synth、diff、permissions boundary與deployment role。
- **選擇時機：** 團隊希望用TypeScript/Python等語言封裝重用架構construct，同時保留CloudFormation deployment model。
- **替換時機：** 需要直接審核純宣告template可用CloudFormation；CDK不是取代CloudFormation state engine。

## 考前與實作時再查：設定操作手冊

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

### AWS CDK：逐項設定說明

#### `app/stacks`

- **控制什麼：** CDK app是construct tree與合成入口；stack是會被合成為一份CloudFormation template並在特定environment部署的邊界。
- **何時需要：** 需要把大型基礎設施依ownership、deployment order、Region／account或blast radius切成可獨立變更單位時。
- **怎麼設定／驗證：** 在App中建立具明確env的Stacks，用cross-stack references或外部contract傳遞必要值，保持每個stack責任與rollback範圍清楚。
- **常見錯法：** 把所有資源塞進單一stack會放大更新風險；過度cross-stack reference又會鎖死部署順序並使環境難以獨立演進。

#### `constructs`

- **控制什麼：** Construct是封裝一個或多個AWS resources、defaults與guardrails的可重用元件；L1／L2／L3代表不同抽象層級。
- **何時需要：** 多個團隊反覆建立相同network、service或security baseline，希望以程式介面重用並集中修正時。
- **怎麼設定／驗證：** 設計小而有清楚contract的construct props，暴露必要設定與escape hatch，加入synthesis assertions及integration deployment tests。
- **常見錯法：** 把所有選項硬編碼成高階construct會限制合法use case；直接暴露每個底層property又失去抽象與安全預設的價值。

#### `context`

- **控制什麼：** 提供synthesis階段的環境查詢結果或設定值，可能保存在cdk.context.json，影響之後產生的CloudFormation template。
- **何時需要：** Construct需要查VPC、Availability Zones或其他environment facts，且團隊要讓同一revision能重現相同synth結果時。
- **怎麼設定／驗證：** 把必要context檔納入版本控制，變更前review diff；需要刷新lookup時明確清除指定key並在目標account／Region重新synth。
- **常見錯法：** 把secret放入context會洩漏；未鎖定lookup結果可能讓相同程式碼在不同時間產生不同template，造成無預期替換。

#### `bootstrap`

- **控制什麼：** `bootstrap`是可版本化的啟動或工作規格，定義AWS CDK建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `assets`

- **控制什麼：** 表示部署需要的本地程式碼、container image或檔案；CDK會打包、雜湊並透過bootstrap資源上傳後供CloudFormation引用。
- **何時需要：** Lambda code、ECS image或S3 deployment內容不是既有遠端artifact，需要隨IaC版本一起發佈時。
- **怎麼設定／驗證：** 先bootstrap目標environment，固定build input與exclude規則，讓CI執行asset build／publish並確認deployment role可讀取對應bucket或ECR。
- **常見錯法：** 未固定dependency會讓相同source產生不同asset；把敏感檔案包入context或asset，以及跨帳號缺少bootstrap trust都會造成風險。

#### `synth`

- **控制什麼：** 執行CDK程式並把construct tree轉成CloudFormation templates、asset manifests與metadata，是部署前可審查的輸出。
- **何時需要：** 任何CDK變更要進入CI、security scan、policy check或code review之前，都需要先產生確定的deployment artifact時。
- **怎麼設定／驗證：** 在固定runtime與dependencies下執行cdk synth，保存或檢查輸出，對generated template做lint、policy及snapshot assertions。
- **常見錯法：** Synth成功只代表可產生template，不代表service quota、runtime permissions或data-plane行為正確；context漂移也會改變輸出。

#### `diff`

- **控制什麼：** 比較目前CDK合成結果與已部署stack，標示新增、修改、刪除與可能造成replacement的CloudFormation變更。
- **何時需要：** production部署前需要人工或自動review blast radius，尤其涉及database、network、IAM與有狀態resource時。
- **怎麼設定／驗證：** 在與部署相同的context及credentials下執行cdk diff，將security-sensitive與replacement changes設為approval gate，再建立change set驗證。
- **常見錯法：** Diff不是完整runtime驗證，也可能受context或lookup權限影響；只看行數而不理解replacement／deletion語意仍可能造成資料遺失。

#### `permissions boundary`

- **控制什麼：** `permissions boundary`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「團隊希望用TypeScript/Python等語言封裝重用架構construct，同時保留CloudFormation deployment model。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CDK明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `deployment role`

- **控制什麼：** `deployment role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「團隊希望用TypeScript/Python等語言封裝重用架構construct，同時保留CloudFormation deployment model。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CDK明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 可以直接對照 AWS 的設定範例

### CloudFormation安全更新：保留database並輸出endpoint

```yaml
Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, stage, prod]
Resources:
  Database:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: aurora-postgresql
      StorageEncrypted: true
      DeletionProtection: !Equals [!Ref Environment, prod]
Outputs:
  WriterEndpoint:
    Value: !GetAtt Database.Endpoint.Address
    Export:
      Name: !Sub "${Environment}-orders-db-writer"

```

1. Parameters與AllowedValues建立有限輸入，不要讓production template接受任意字串。
2. DeletionPolicy/UpdateReplacePolicy處理刪除與replacement；仍需backup/restore test。
3. 部署前建立change set，特別檢查Replacement=True與IAM capability。

## 讀到這裡，請用自己的話說一次

1. AWS CloudFormation的責任：以declarative templates建立、更新與刪除AWS resources。
2. 底層機制：CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。
3. 第一個要看的設定：Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
4. 選擇邏輯：以template宣告desired state，參數化環境，透過stack events與rollback管理變更。
5. 不要混淆：AWS CDK的責任是「以程式語言constructs定義AWS基礎設施，再合成CloudFormation templates部署。」；它不會自動取代AWS CloudFormation。
6. 替換訊號：需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。
7. 最常見錯法：在production手改資源後template不知情，下一次deploy覆蓋或失敗。
8. 可移植原則：infrastructure changes deserve versioned code and review。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 | repeatable environment、reviewable IaC與cross-account StackSets。 | 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。 |
| AWS CDK | 以程式語言constructs定義AWS基礎設施，再合成CloudFormation templates部署。 | CDK app建立construct tree；synth產生template與assets metadata，deploy仍由CloudFormation建立change set和管理resource state。 | 團隊希望用TypeScript/Python等語言封裝重用架構construct，同時保留CloudFormation deployment model。 | 需要直接審核純宣告template可用CloudFormation；CDK不是取代CloudFormation state engine。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。 | 只有當題目條件明確改變時才可能合理。 | 在production手改資源後template不知情，下一次deploy覆蓋或失敗。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。」之間做選擇。
- 認得常考設定：Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜CDK authoring layer 與 CloudFormation state engine

一個平台團隊想用 TypeScript constructs 封裝公司標準 VPC，同時要求 production 變更可先審查、失敗時可由同一套引擎管理 rollback，並保留 authoritative stack state。哪個流程最符合需求？

A. 只把 CDK 程式碼存進 Git；production 仍由工程師在 console 手動重建相同資源
B. 用 CDK 建立 constructs 並 synthesize；審查產生的 template/change set，再由 CloudFormation 管理資源生命週期
C. 先由 CloudFormation 建立資源，再讓 CDK 自動接管所有 console drift，無須明確匯入或更新 template
D. 讓 CDK 直接呼叫各服務 API 並自行維護 rollback，不產生 CloudFormation template

**答案：B**

- **A：** 錯誤。手動 production 操作會破壞可重現性與審查鏈，也使 Git 中的定義不再是可靠的 desired state。
- **B：** 正確。CDK 解決程式語言抽象與重用，CloudFormation 仍負責比較 desired state、呼叫服務 API、記錄 events，以及 create/update/delete/rollback。
- **C：** 錯誤。既有或手動變更不會因為 CDK 程式存在就自動被接管；仍需更新定義、匯入資源或明確調和 drift。
- **D：** 錯誤。標準 CDK 部署模型會合成 CloudFormation artifacts；CDK 並不是另一個獨立的 stack state 與 rollback 引擎。

**事實查證：** [SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)、[SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)、[What is the AWS CDK?](https://docs.aws.amazon.com/cdk/v2/guide/home.html)、[What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)

### 練習題 2｜SAA｜環境參數化與 secret 邊界

同一份 CloudFormation template 要部署到 dev、staging 與 prod。Instance size 與 subnet ID 可因環境不同，但資料庫密碼會定期輪替，且不得出現在 template、Git history 或一般 parameter value 中。應如何設計？

A. 不使用任何參數，部署後再由工程師逐一在 console 修改
B. 把所有差異放進 Mappings，包含會獨立輪替的明文密碼
C. 保留一份受版本控制的 template；用受約束的 parameters/mappings/conditions 表達非敏感差異，密碼以 Secrets Manager 或 SSM secure value 的 dynamic reference 取得
D. 複製三份 template，將每個環境的密碼寫成 Parameter 的 Default

**答案：C**

- **A：** 錯誤。部署後手改會讓 template 無法完整表達環境，下一次更新也可能覆寫或衝突。
- **B：** 錯誤。Mappings 適合相對靜態、可審查的查表值，不是會獨立輪替的 secret store，而且明文仍會暴露。
- **C：** 正確。非敏感環境差異可參數化並加 AllowedValues 等約束；dynamic reference 讓 CloudFormation 在部署時向專用 secret store 解析值。
- **D：** 錯誤。複製 template 會造成環境漂移；把密碼放在 Default 也會把敏感值寫入定義與版本紀錄。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[CloudFormation template sections](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-anatomy.html)、[CloudFormation Parameters section](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html)、[CloudFormation dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html)

### 練習題 3｜SAA｜implicit dependency 與 DependsOn

一份 template 內，EC2 security group 的 VpcId 以 Ref 指向同 stack 的 VPC；另一個自訂路由資源雖未引用 Internet Gateway attachment 的屬性，卻必須等 attachment 完成才能建立。哪個 dependency 設計最正確？

A. 用 Outputs 取代 Ref，因 Outputs 會強制同一 stack 的建立順序
B. 保留 Ref 讓 CloudFormation 推導 security group 對 VPC 的依賴；只在路由上對 gateway attachment 加 DependsOn
C. 在每個資源之間都加入 DependsOn，確保完全序列化
D. 依照 YAML 中的出現順序排列資源，CloudFormation 會嚴格由上到下建立

**答案：B**

- **A：** 錯誤。Outputs 用於暴露結果，不是同 stack 內建立 dependency 的替代語法。
- **B：** 正確。Ref/GetAtt/Sub 等引用會形成 implicit dependency；只有無法由 properties 看出的額外排序限制才需要 DependsOn。
- **C：** 錯誤。過度使用 DependsOn 會不必要地降低平行度，且不能修正錯誤的資源契約。
- **D：** 錯誤。Template 的文字順序不是資源建立順序；CloudFormation 依 dependency graph 平行處理可獨立的資源。

**事實查證：** [What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)、[CloudFormation DependsOn attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-dependson.html)

### 練習題 4｜SAP｜stack boundary、nested stack 與 failure scope

公司有共享網路、長生命週期資料庫，以及每天部署多次的應用服務。網路由中央團隊管理，資料庫更新需額外審批；應用部署失敗不應把三層一起 rollback。哪個 stack 邊界最合理？

A. 把整個組織所有資源放進單一 stack，讓任何變更都具備同一個原子 rollback
B. 依 ownership、change cadence 與 blast radius 拆分 stacks；以穩定的單向介面共享必要輸出，只有需要同 root lifecycle 的模組才使用 nested stacks
C. 只要 template 超過 500 行，就一律改成由同一 root 管理的 nested stack，不考慮 owner
D. 讓網路與應用互相 export/import 對方的值，形成雙向依賴以保持同步

**答案：B**

- **A：** 錯誤。單一巨大 stack 會把不同 owner 與生命週期綁在一起，擴大部署失敗與權限的影響範圍。
- **B：** 正確。Stack 應是 ownership 與 failure boundary；穩定、單向、非敏感的 interface 可降低跨 stack coupling。
- **C：** 錯誤。Nested stack 的價值是組合與共同 lifecycle，不是單純依檔案長度決定；它仍受 root operation 影響。
- **D：** 錯誤。雙向 cross-stack dependency 容易形成不可部署的循環，也會妨礙獨立替換與刪除。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Work with nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

### 練習題 5｜SAP｜StackSets permission model 與 rollout control

安全團隊要把相同的 Config recorder 與 IAM baseline 部署到 AWS Organizations 內指定 OUs 的 180 個帳號、三個 Regions；新帳號加入 OU 後也要自動取得 baseline，且 rollout 需限制並行與可容忍失敗數。應選哪個方案？

A. 使用 service-managed StackSets、啟用 Organizations trusted access 與 OU auto-deployment，並設定 concurrency 與 failure tolerance
B. 在 management account 建立一個普通 stack，讓它自動跨帳號擁有所有 member resources
C. 使用 self-managed StackSets，但不建立 administration/execution roles，因 Organizations 會自動補上
D. 把 maximum concurrency 設為 100%、failure tolerance 設為 0，這會提供最小 blast radius

**答案：A**

- **A：** 正確。Service-managed permissions 能以 Organizations 的 OU 為 targets 並支援 auto-deployment；operation preferences 可限制同時受影響的帳號與停止條件。
- **B：** 錯誤。普通 stack 的資源位於其部署帳號/Region；它不會自動成為跨組織部署引擎。
- **C：** 錯誤。Self-managed 模式需要明確建立並信任 administration 與 execution roles，不會因為屬於同一 Organization 就省略。
- **D：** 錯誤。高並行加零容忍可能在第一個失敗前同時影響大量帳號，不是最小 blast radius。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[CloudFormation StackSets concepts](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html)、[SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)

### 練習題 6｜SAP｜CDK bootstrap、assets 與跨帳號部署

Tooling account 的 pipeline 要將含 Lambda zip 與 container asset 的 CDK app 部署到兩個 production accounts、各兩個 Regions。公司禁止開發者持有 production access key。哪個準備動作是必要的？

A. 以合適的 trust 與 qualifier bootstrap 每個 target environment，讓 pipeline 發布 assets 並 assume 限權 deployment roles
B. 只執行 cdk synth；synthesized template 會內嵌所有 binary assets，因此不需要發布
C. 讓每位開發者在本機建立 production IAM user，再由 cdk deploy 上傳 assets
D. 建立一個允許匿名讀取的全域 S3 bucket，所有環境共用

**答案：A**

- **A：** 正確。Bootstrap stack 提供 asset bucket/repository 與 deployment-related roles；每個帳號與 Region 都是需要準備的 environment boundary。
- **B：** 錯誤。Synth 會產生 template 與 asset manifests；本地檔案或 image 仍須先發布到 target deployment 可存取的位置。
- **C：** 錯誤。長期 production access key 違反需求，也不利於集中稽核與撤銷。
- **D：** 錯誤。公開 asset bucket 會暴露部署內容；跨帳號存取應由 IAM、bucket policy 與加密權限明確控制。

**事實查證：** [What is the AWS CDK?](https://docs.aws.amazon.com/cdk/v2/guide/home.html)、[Bootstrap AWS CDK environments](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html)、[Create a cross-account CodePipeline pipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-create-cross-account.html)

### 練習題 7｜SAP｜IaC pipeline 各驗證層責任

Production pipeline 必須在部署前擋下 malformed templates 與「S3 bucket 必須加密」的公司規則，並讓 reviewer 看見可能的 replacement。架構師也必須避免宣稱這些檢查能證明 runtime 一定成功。哪個 pipeline 最完整？

A. 只要 ValidateTemplate 成功就直接部署，因它同時驗證 IAM、quota 與應用程式行為
B. 只建立 change set；change set 已等同公司 policy-as-code 與 end-to-end test
C. 先部署 production，再執行 Guard；因只有實體資源存在時 Guard 才能解析 template
D. 依序執行 template/lint 驗證、CloudFormation Guard policy checks、測試與 change-set review；部署後仍做 health/integration validation

**答案：D**

- **A：** 錯誤。Template 驗證不會證明執行角色權限、帳號 quota、服務狀態或應用依賴一定可用。
- **B：** 錯誤。Change set 顯示 CloudFormation 預計採取的資源動作，但不會自動套用組織自訂規則或驗證業務流程。
- **C：** 錯誤。Guard 是可在部署前對結構化資料執行的 policy-as-code 工具；延後到 production 失去 shift-left 的目的。
- **D：** 正確。語法/schema、組織政策、proposed resource transition 與 runtime health 是不同證據，應分層驗證。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)、[Update stacks using change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

### 練習題 8｜SAP｜immutable IaC artifact promotion

稽核要求證明 production 部署的是 staging 已驗證的同一份 synthesized template 與 Lambda artifact；環境間只允許受控參數不同。哪種做法最能建立證據鏈？

A. 每個環境都從當下 main branch 重新 synthesize，因 source repository 相同即可視為相同 artifact
B. 每個環境重新 build Lambda zip，並沿用同一個可覆寫的 S3 key
C. build/synthesize 一次，將 template、asset digest 與測試結果版本化且不可變地保存，再逐環境提升同一 revision 並注入核准參數
D. 在 production approval 後手動修改 template，以免重新走 pipeline

**答案：C**

- **A：** 錯誤。Moving branch、依賴版本與 build environment 都可能使重新 synthesize 的結果不同。
- **B：** 錯誤。可覆寫 key 與重建都破壞 artifact identity；無法證明 production binary 等於 staging binary。
- **C：** 正確。Build once、promote same artifact 把 code/template identity 與環境設定分開，能建立可追溯且可重現的供應鏈。
- **D：** 錯誤。Approval 後手改會使被部署內容不再是 reviewer 與測試所看見的 revision。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)、[CloudFormation deploy action reference](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CloudFormation.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

### 練習題 9｜SAA｜Outputs、cross-stack export 與敏感資料

網路 stack 要把 VPC ID 提供給同 Region、由另一團隊獨立部署的 application stack；資料庫密碼也要供 runtime 取得。哪些 TWO 做法最符合低耦合與 secret 安全？

A. 把資料庫密碼放進 Output 並 Export，因 Outputs 只對 stack owner 可見
B. 建立雙向 exports，讓 network stack 同時 Import application stack 的 deployment ID
C. 將穩定且非敏感的 VPC ID 作為 Output；若使用 Export/ImportValue，明確管理單向 ownership 與替換限制
D. 將密碼存入 Secrets Manager，讓 runtime role 以最小權限讀取，而不是從 stack Outputs 傳遞
E. Export 每個 subnet、security group rule 與暫時資源 ARN，讓 consumer 不需任何自己的設定

**答案：C、D**

- **A：** 錯誤。Stack Outputs 不是 secret store，可能透過 console/API 被讀取；不應輸出明文密碼。
- **B：** 錯誤。雙向 imports 會造成 circular dependency，破壞兩個 stack 的獨立生命週期。
- **C：** 正確。Output 適合提供非敏感 identifiers；cross-stack export 適合穩定同 Region 介面，但 consumer 存在時會限制 exporting value 的修改或刪除。
- **D：** 正確。專用 secret store 支援獨立輪替與 IAM-controlled runtime access，不必把敏感值固化在 deployment interface。
- **E：** 錯誤。把頻繁變動的 implementation details 全部 export 會形成高度 coupling，使替換與刪除困難。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[CloudFormation template sections](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-anatomy.html)、[CloudFormation dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

### 練習題 10｜SAP｜CloudFormation failure diagnosis

一個 stack update 先出現自訂資源 CREATE_FAILED，接著十多個相依資源顯示 UPDATE_FAILED 或 UPDATE_ROLLBACK_IN_PROGRESS。值班工程師必須找出根因並安全重試。應先採取哪些 TWO 動作？

A. 把每一個後續 UPDATE_FAILED 都視為獨立根因，同時修改所有資源
B. 反覆重新建立 stack，直到 eventual consistency 自動解決所有問題
C. 關閉 production rollback，讓失敗資源保持可用狀態
D. 按時間檢查 stack/resource events，沿 dependency chain 找到最早的服務 API 或 custom-resource error
E. 保留 custom-resource logs 與請求證據，確認 IAM、quota、parameters 和外部 dependency 後再部署修正版

**答案：D、E**

- **A：** 錯誤。許多後續失敗只是上游 dependency failure 的結果；同時修改會增加噪音與風險。
- **B：** 錯誤。未修正權限、quota 或 custom logic 前重試只會重複失敗，並可能產生外部副作用。
- **C：** 錯誤。停用 rollback 不會讓建立失敗的資源突然健康，也會留下更難管理的 partial state。
- **D：** 正確。Events 是 CloudFormation state transition 的 authoritative sequence；最早的具體 API error 通常比最後的 rollback 訊息更接近根因。
- **E：** 正確。自訂資源與外部系統可能有 CloudFormation 無法自動撤銷的副作用；先保存 evidence 並驗證前置條件才可安全重試。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以template宣告desired state，參數化環境，透過stack events與rollbac…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「手動console操作不可重現、難review，也無法可靠建立多帳號多Region環境。」，所以「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」能直接滿足它；若constraint改成「CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」。替代方案「CDK用程式產生CloudFormation，提升抽象但仍需理解生成template與deployment lifecycle。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「在production手改資源後template不知情，下一次deploy覆蓋或失敗。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「手動console操作不可重現、難review，也無法可靠建立多帳號多Region環境。」，排除會導致「在production手改資源後template不知情，下一次deploy覆蓋或失敗。」的選項，再選「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以template宣告desired state，參數化環境，透過stack events與rollback管理變更。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「infrastructure changes deserve versioned code and review」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 73 章　Change Sets、Drift 與 Rollback

IaC變更可能replacement、刪除資料或跨stack傳播，部署前需要可見差異。

## 跟著一次變更走到production：先從故事開始

故事從一個看似簡單的需求開始：安全基線要推全組織，但database與KMS key不得因template更新被刪除。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：IaC變更可能replacement、刪除資料或跨stack傳播，部署前需要可見差異。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS CloudFormation會是本章的主要角色，CloudFormation change sets則幫我們看清邊界。方向是「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：安全基線要推全組織，但database與KMS key不得因template更新被刪除。

正常production路徑
          ▼
[AWS CloudFormation] → 使用者可觀察的結果
          │ 以declarative templates建立、更新與刪除AWS resources。
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · CloudFormation change sets：在執行stack update前預覽將新增、修改、替換或刪除的resources。
  · AWS CloudFormation StackSets：把相同CloudFormation stack部署到多帳號、多Regions。

失敗時先找：忽略replacement提示而重建database，或rollback時自訂resource無法復原。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS CloudFormation有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS CloudFormation和CloudFormation change sets並不是兩個任意的產品名稱。前者適合本章，是因為「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」直接回應了眼前的問題；後者描述的「Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：忽略replacement提示而重建database，或rollback時自訂resource無法復原。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「preview destructive transitions before execution」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 |
| CloudFormation change sets | 在執行stack update前預覽將新增、修改、替換或刪除的resources。 | CloudFormation比較template/parameters與現有stack，產生proposed changes但不保證外部副作用。 |
| AWS CloudFormation StackSets | 把相同CloudFormation stack部署到多帳號、多Regions。 | Service-managed模式整合Organizations並自動部署到OU accounts；operations控制並行與failure tolerance。 |

## 把全圖套進一個具體案例

**場景：** 安全基線要推全組織，但database與KMS key不得因template更新被刪除。

1. 故事的起點：安全基線要推全組織，但database與KMS key不得因template更新被刪除。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS CloudFormation負責「以declarative templates建立、更新與刪除AWS resources。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：CloudFormation change sets、AWS CloudFormation StackSets各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「忽略replacement提示而重建database，或rollback時自訂resource無法復原。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS CloudFormation

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：IaC變更可能replacement、刪除資料或跨stack傳播，部署前需要可見差異。
- **具體例子／邊界：** 在「安全基線要推全組織，但database與KMS key不得因template更新被刪除。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### CloudFormation change sets

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：忽略replacement提示而重建database，或rollback時自訂resource無法復原。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：preview destructive transitions before execution。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### dependency graph

以nodes/edges表示application、database、network、identity與外部系統的依賴，幫助避免把強耦合元件拆到不同waves。

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### change set

CloudFormation在執行前計算預計新增、修改、刪除或替換哪些resources，供review但不保證application side effects。

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

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

### stack

CloudFormation以一個生命週期單位管理的一組resources；更新與刪除行為受dependencies及policies影響。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS CloudFormation

- **功用：** 以declarative templates建立、更新與刪除AWS resources。
- **底層機制：** CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。
- **關鍵設定：** Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
- **選擇時機：** repeatable environment、reviewable IaC與cross-account StackSets。
- **替換時機：** 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。

### CloudFormation change sets

- **功用：** 在執行stack update前預覽將新增、修改、替換或刪除的resources。
- **底層機制：** CloudFormation比較template/parameters與現有stack，產生proposed changes但不保證外部副作用。
- **關鍵設定：** change set type、include nested stacks、replacement、capabilities與execution。
- **選擇時機：** production IaC review、辨識replacement與降低誤刪風險。
- **替換時機：** 仍需policy-as-code、tests與rollback；change set不能偵測所有service runtime impact。

### AWS CloudFormation StackSets

- **功用：** 把相同CloudFormation stack部署到多帳號、多Regions。
- **底層機制：** Service-managed模式整合Organizations並自動部署到OU accounts；operations控制並行與failure tolerance。
- **關鍵設定：** permission model、targets OU/accounts、Regions、auto-deployment、concurrency與failure tolerance。
- **選擇時機：** organization-wide baseline、roles、Config rules、logging resources。
- **替換時機：** 帳號供應完整landing zone使用Control Tower/Account Factory；app單帳號stack不需StackSets。

## 考前與實作時再查：設定操作手冊

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

### CloudFormation change sets：逐項設定說明

#### `change set type`

- **控制什麼：** `change set type`選擇CloudFormation change sets的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `include nested stacks`

- **控制什麼：** `include nested stacks`控制CloudFormation change sets的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

#### `replacement`

- **控制什麼：** `replacement`控制CloudFormation change sets的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

#### `capabilities`

- **控制什麼：** `capabilities`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。
- **何時需要：** 當需求符合「production IaC review、辨識replacement與降低誤刪風險。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在CloudFormation change sets template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。
- **常見錯法：** Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。

#### `execution`

- **控制什麼：** `execution`控制CloudFormation change sets的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

### AWS CloudFormation StackSets：逐項設定說明

#### `permission model`

- **控制什麼：** `permission model`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「organization-wide baseline、roles、Config rules、logging resources。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation StackSets明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `targets OU/accounts`

- **控制什麼：** `targets OU/accounts`指定AWS CloudFormation StackSets讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Regions`

- **控制什麼：** `Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS CloudFormation StackSets前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `auto-deployment`

- **控制什麼：** `auto-deployment`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「organization-wide baseline、roles、Config rules、logging resources。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudFormation StackSets設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `concurrency`

- **控制什麼：** `concurrency`設定AWS CloudFormation StackSets的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「organization-wide baseline、roles、Config rules、logging resources。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `failure tolerance`

- **控制什麼：** `failure tolerance`控制AWS CloudFormation StackSets的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

## 讀到這裡，請用自己的話說一次

1. AWS CloudFormation的責任：以declarative templates建立、更新與刪除AWS resources。
2. 底層機制：CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。
3. 第一個要看的設定：Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
4. 選擇邏輯：使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。
5. 不要混淆：CloudFormation change sets的責任是「在執行stack update前預覽將新增、修改、替換或刪除的resources。」；它不會自動取代AWS CloudFormation。
6. 替換訊號：需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。
7. 最常見錯法：忽略replacement提示而重建database，或rollback時自訂resource無法復原。
8. 可移植原則：preview destructive transitions before execution。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS CloudFormation | 以declarative templates建立、更新與刪除AWS resources。 | CloudFormation建立dependency graph並呼叫service APIs；stack state與events支援rollback。 | repeatable environment、reviewable IaC與cross-account StackSets。 | 需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。 |
| CloudFormation change sets | 在執行stack update前預覽將新增、修改、替換或刪除的resources。 | CloudFormation比較template/parameters與現有stack，產生proposed changes但不保證外部副作用。 | production IaC review、辨識replacement與降低誤刪風險。 | 仍需policy-as-code、tests與rollback；change set不能偵測所有service runtime impact。 |
| AWS CloudFormation StackSets | 把相同CloudFormation stack部署到多帳號、多Regions。 | Service-managed模式整合Organizations並自動部署到OU accounts；operations控制並行與failure tolerance。 | organization-wide baseline、roles、Config rules、logging resources。 | 帳號供應完整landing zone使用Control Tower/Account Factory；app單帳號stack不需StackSets。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。 | 只有當題目條件明確改變時才可能合理。 | 忽略replacement提示而重建database，或rollback時自訂resource無法復原。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。」之間做選擇。
- 認得常考設定：Parameters、Mappings、Resources、Outputs、Conditions、DependsOn、DeletionPolicy、UpdateReplacePolicy與stack policy。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要一般程式語言抽象可用CDK產生templates；runtime config用AppConfig/Parameter Store。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜change set 的能力邊界

Production template 更新可能替換一個有資料的資源。Change set 已成功建立並顯示 Replace，reviewer 想知道是否可據此保證執行一定成功且資料可回復。哪個判斷最準確？

A. 只要 change set 顯示 Modify，就絕不可能重建 physical resource
B. Change set 應用來審查新增、修改、刪除與 replacement；但執行前仍須驗證資料保護、權限、quota 與 runtime/外部副作用
C. Drift detection 才是預測新 template 將採取哪些 update action 的主要工具
D. Change set 成功代表所有 IAM、quota、service health 與應用副作用都已驗證

**答案：B**

- **A：** 錯誤。Reviewer 應查看 resource change details 與 replacement semantics，不能只憑高階 action 推論資料一定保留。
- **B：** 正確。它能提高 destructive transition 的可見性，但 rollback 與 data recovery 仍需另行設計與測試。
- **C：** 錯誤。Drift detection 比較既有 expected 與 actual configuration；預覽新 template update 應用 change set。
- **D：** 錯誤。Change set 是 proposed change preview，不是所有執行期前置條件與業務資料的模擬器。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Update stacks using change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)

### 練習題 2｜SAP｜nested stack change-set review

Root stack 只把 child template URL 從 v17 改成 v18，但 child 內的 RDS resource 可能 replacement。審核規則要求在執行前看見 child-resource 層級的影響。應如何處理？

A. 直接更新 child stack，繞過 root stack 的生命週期
B. 只審 root resource 的 template URL，因 nested stack 失敗不會影響 root operation
C. 建立支援 include nested stacks 的 change set，展開並審查 child changes、replacement 與 dependency order
D. 假設 URL 變更只會下載新檔案，不會觸發 child resources 更新

**答案：C**

- **A：** 錯誤。由 parent 管理的 nested stack 應透過 parent 更新，以免 parent 與 child state 不一致。
- **B：** 錯誤。Root 摘要可能不足以揭露 child 中的 stateful replacement，而且 child failure 可使整個 root operation rollback。
- **C：** 正確。Nested change-set analysis 讓 reviewer 查看實際執行層級的 child resource transitions。
- **D：** 錯誤。Nested template 內容改變正是 child resources 可能新增、修改、替換或刪除的原因。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Update stacks using change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)、[Work with nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html)

### 練習題 3｜SAA｜drift detection 的 scope

稽核員看到 stack drift status 為 IN_SYNC，便宣稱沒有任何人改過資源、所有 service defaults 與 application data 也都符合設計。架構師應如何回應？

A. IN_SYNC 只代表受支援資源中被 CloudFormation 建模並檢查的 properties 符合 expected state；它不證明未建模 defaults、runtime data 或外部系統一致
B. 只要刻意不在 template 宣告 property，drift detection 就會把當前 service default 當成永久 desired state
C. 稽核員正確；drift detection 會比較所有 AWS resource types、每個隱含 default 與資料內容
D. IN_SYNC 只證明 CloudTrail 沒有任何 API event

**答案：A**

- **A：** 正確。Drift evidence 受 resource support 與 template 中明確建模的 properties 限制，不能取代 application/runtime validation。
- **B：** 錯誤。未宣告的重要 property 會降低 expected-state 的明確性，而不是自動鎖定現值。
- **C：** 錯誤。並非所有資源與 property 都具備完整 drift support，且 Config data/application data 不在此比較模型內。
- **D：** 錯誤。CloudTrail event history 與 CloudFormation drift 是不同證據來源。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Detect unmanaged configuration changes with drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)

### 練習題 4｜SAP｜drift reconciliation 與 authority

事故期間，值班人員在 console 放寬 connection pool 並恢復服務；Git 中 template 仍是舊值。立即覆寫 live state 可能再度故障，永久接受手改也未經審查。下一步最佳做法是什麼？

A. 把所有 console changes 自動寫回 main branch，不需 review
B. 無條件立即以 Git 覆寫 production，因 IaC 永遠不可能有錯
C. 只在 ticket 寫下例外，讓 template 與 live state 永久不同
D. 確認事故變更的效果與風險，明確決定 template 或 live state 誰是 authority；測試後更新定義/採納現值或受控 revert，並保存 rationale

**答案：D**

- **A：** 錯誤。Live change 可能只是暫時 workaround 或過度授權，不能跳過 review 直接成為標準。
- **B：** 錯誤。Source control 應是有治理的 desired state，但事故已提供證據顯示舊值可能有害，仍需先判斷。
- **C：** 錯誤。永久未調和的 drift 會使下一次 deployment 不可預測，也無法清楚陳述 desired state。
- **D：** 正確。Reconciliation 是 ownership decision：選定 authority、驗證、更新其中一方，並讓事件原因與例外期限可追溯。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Detect unmanaged configuration changes with drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)、[Use drift-aware change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/drift-aware-change-sets.html)、[Update stacks using change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)

### 練習題 5｜SAA｜stack policy 與 update protection

一個 stack 內，application resources 可正常更新，但 production database 只有在核准維護期間才能被 CloudFormation update 或 replace。Stack 本身仍可能在正式除役流程中刪除。應使用哪個控制？

A. 設定 stack policy 拒絕 database 的 update actions，核准時使用範圍最小的 temporary override
B. 只設定 DeletionPolicy: Retain；它會同時阻擋所有 property updates
C. 只啟用 termination protection；它會成為 per-resource update allowlist
D. 設定 UpdateReplacePolicy；它會阻止 replacement 發生

**答案：A**

- **A：** 正確。Stack policy 能限制特定 logical resources 的 update actions；temporary override 應只開放核准變更所需範圍。
- **B：** 錯誤。DeletionPolicy 管理 stack deletion 或 template removal 時的 disposition，不是 update deny policy。
- **C：** 錯誤。Termination protection 阻擋 DeleteStack，不限制一般 stack update。
- **D：** 錯誤。UpdateReplacePolicy 決定 replacement 後舊 physical resource 如何處理，不會阻止 CloudFormation 建立 replacement。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Prevent updates to stack resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html)

### 練習題 6｜SAA｜DeletionPolicy 與 UpdateReplacePolicy

一個 RDS database 必須在兩種情況都保留資料：(a) logical resource 從 template 移除或 stack 被刪除；(b) 某次 property update 需要 replacement。哪個設定最符合？

A. 設定 stack policy Deny Delete，因 stack policy 會在 stack deletion 後繼續管理 database
B. 只設定 DeletionPolicy: Retain，因它也會套用到 replacement 的舊 physical resource
C. 只設定 UpdateReplacePolicy: Retain，因它也涵蓋從 template 移除
D. 同時依需求設定 DeletionPolicy 與 UpdateReplacePolicy 為 Retain，並建立 retained resource 的後續 ownership 流程

**答案：D**

- **A：** 錯誤。Stack policy 是 update restriction，而且 stack 刪除後不會繼續管理 retained physical resource。
- **B：** 錯誤。DeletionPolicy 不等同 replacement 時舊資源的 disposition control。
- **C：** 錯誤。UpdateReplacePolicy 針對 replacement；資源被移除或 stack deletion 仍由 DeletionPolicy 決定。
- **D：** 正確。兩個 attributes 對應不同 lifecycle path；若兩條路都要保留，必須分別設定並承接 retained resource 管理責任。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[DeletionPolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)、[UpdateReplacePolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-updatereplacepolicy.html)

### 練習題 7｜SAP｜retained resource lifecycle ownership

舊 stack 已依 DeletionPolicy: Retain 保留資料庫，stack record 則被刪除。六個月後沒有人知道誰支付、patch、備份或何時可清理。原設計缺少哪個關鍵控制？

A. 依賴 Retain 自動把資料跨帳號複製並輪替 encryption key
B. 對所有 resource types 一律使用 Snapshot，因 CloudFormation 保證都支援
C. 把 retention 視為 ownership transfer，登記 physical ID、KMS key、access owner、backup/cleanup 期限與 import/migration plan
D. 假設 retained resource 仍由已刪除的 stack 自動更新與刪除

**答案：C**

- **A：** 錯誤。Retention 不會自動完成 cross-account copy 或 key rotation。
- **B：** 錯誤。Snapshot 行為只支援特定 resource types，且 snapshot 本身也需要 lifecycle owner。
- **C：** 正確。Retain 只改變 CloudFormation 的刪除行為；組織必須接手成本、安全、備份、更新與最終 disposition。
- **D：** 錯誤。Stack 被刪除後，retained physical resource 不再受該 stack 的 lifecycle 管理。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[DeletionPolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)、[UpdateReplacePolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-updatereplacepolicy.html)、[Import AWS resources into a CloudFormation stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-existing-stack.html)

### 練習題 8｜SAA｜termination protection 的責任邊界

團隊要防止操作員誤刪 production root stack，但仍要允許經審批的 stack updates，並確保特定 database 在真正除役時保留。哪個組合敘述正確？

A. 只要開啟 termination protection，即使之後關閉並刪 stack，database 也必然保留
B. Stack policy 能直接阻擋 DeleteStack，因此不需要 termination protection
C. 用 termination protection 阻擋 stack deletion；另以 stack policy 管 update，以 DeletionPolicy/UpdateReplacePolicy 管 physical resource disposition
D. Termination protection 會阻止所有 update 與 replacement

**答案：C**

- **A：** 錯誤。保留資料需 resource lifecycle policy；termination protection 一旦停用，不能取代 DeletionPolicy。
- **B：** 錯誤。Stack policy 主要限制 update actions，不是 DeleteStack 的保護開關。
- **C：** 正確。三種控制保護的事件不同：刪 stack、更新資源、以及刪除/替換 physical resource。
- **D：** 錯誤。Termination protection 不會阻擋一般 update。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Protect a stack from deletion](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-protect-stacks.html)、[Prevent updates to stack resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html)、[DeletionPolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)

### 練習題 9｜SAP｜rollback trigger 與 application side effects

CloudFormation update 可能在 control plane 顯示完成後 8 分鐘才讓 checkout error rate 上升。團隊希望在 15 分鐘觀察窗內自動 rollback，但不誇大 rollback 能力。哪些 TWO 設計正確？

A. 依賴帳號中任何 CloudWatch alarm，因所有 alarm 都會自動成為 rollback trigger
B. 明確設定 alarm dimensions、threshold、period 與 missing-data behavior，並為不可逆副作用設計補償或 forward recovery
C. 將能反映 checkout 失敗的 CloudWatch alarm 設為 rollback trigger，並選擇涵蓋延遲故障的 monitoring time
D. 宣稱 rollback 可撤銷已提交的付款、資料庫寫入與第三方 API side effects
E. 把 monitoring window 設為零，因 stack UPDATE_COMPLETE 已證明 customer journey 正常

**答案：B、C**

- **A：** 錯誤。不是帳號內任意 alarm 都會自動參與該次 stack operation。
- **B：** 正確。Alarm 必須代表正確 workload 與 failure mode；不可逆資料變更需要另行補償。
- **C：** 正確。Rollback trigger 必須明確關聯，monitoring window 也要足以看見題述的 delayed failure。
- **D：** 錯誤。CloudFormation 能回復受管資源狀態，但無法通用撤銷外部或已提交的業務 side effects。
- **E：** 錯誤。Control-plane complete 不是 application success，零觀察窗也無法捕捉八分鐘後才出現的故障。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Roll back a stack on CloudWatch alarm breaches](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-rollback-triggers.html)、[Use Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)

### 練習題 10｜SAP｜UPDATE_ROLLBACK_FAILED recovery

Production stack 卡在 UPDATE_ROLLBACK_FAILED，原因是某 IAM permission 被移除，另一個 resource 已由人工刪除。團隊要恢復 stack 可更新狀態且不把不一致隱藏起來。應採取哪些 TWO 動作？

A. 在 ContinueUpdateRollback 時跳過所有失敗 resources，之後將它們視為自動 IN_SYNC
B. 只有無法立即修復時才最小化 resource skip；完成後以 drift、template 更新或 import 調和其真實狀態
C. 直接 DeleteStack，因 UPDATE_ROLLBACK_FAILED 沒有其他恢復方式
D. 先修復可修復的 permission/dependency 或重建必要 resource，再執行 ContinueUpdateRollback
E. 停用 drift detection，避免看見被跳過 resource 的差異

**答案：B、D**

- **A：** 錯誤。Skipped resources 可能與 template 不一致；狀態名稱恢復不代表 physical configuration 已調和。
- **B：** 正確。Skip 是最後手段，且必須把被跳過 resource 當成待修復 drift，而不是已完成修復。
- **C：** 錯誤。CloudFormation 提供 continue rollback；立即刪除可能擴大 stateful resource 風險。
- **D：** 正確。先移除 rollback blocker 能讓 CloudFormation 儘量完成原本的恢復流程。
- **E：** 錯誤。隱藏 evidence 不會修正 desired/actual state discrepancy。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Continue rolling back an update](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-continueupdaterollback.html)、[Detect unmanaged configuration changes with drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)、[Import AWS resources into a CloudFormation stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-existing-stack.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「使用change set預覽、drift detection找手改、stack policy/deleti…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「IaC變更可能replacement、刪除資料或跨stack傳播，部署前需要可見差異。」，所以「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」能直接滿足它；若constraint改成「Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」。替代方案「Nested stacks與StackSets改善重用/多帳號部署，但增加版本與failure scope。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「忽略replacement提示而重建database，或rollback時自訂resource無法復原。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「IaC變更可能replacement、刪除資料或跨stack傳播，部署前需要可見差異。」，排除會導致「忽略replacement提示而重建database，或rollback時自訂resource無法復原。」的選項，再選「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「使用change set預覽、drift detection找手改、stack policy/deletion policy保護stateful資源。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「preview destructive transitions before execution」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 74 章　Blue/Green、Canary 與 Rolling Deployment

新版本有未知風險，release strategy決定blast radius、成本與rollback速度。

## 跟著一次變更走到production：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：付款API需零停機、五分鐘內rollback，schema變更必須相容兩版本。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：新版本有未知風險，release strategy決定blast radius、成本與rollback速度。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS CodeDeploy負責主要工作，Elastic Load Balancing提醒我們答案不是永遠固定。本章會走向「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：付款API需零停機、五分鐘內rollback，schema變更必須相容兩版本。

舊版本仍服務100%流量
      │
      ├─ 部署新版本到隔離環境
      ├─ 執行health與business checks
      └─ 逐步切 1% → 5% → 25% → 100%
                         │
            metric超標？ ├─ yes ──> 立即rollback
                         └─ no  ──> 繼續bake

Blue/Green換整套環境；Canary逐步放量；Rolling逐批替換instance。
Database schema必須同時相容新舊application，否則程式rollback也救不回來。

失敗時先找：只看deployment成功而未用business metric判斷canary，或立即銷毀blue。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS CodeDeploy有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS CodeDeploy和Elastic Load Balancing並不是兩個任意的產品名稱。前者適合本章，是因為「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」直接回應了眼前的問題；後者描述的「Database schema需expand/contract，否則compute rollback仍可能不相容。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只看deployment成功而未用business metric判斷canary，或立即銷毀blue。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「deployment safety comes from bounded exposure and reversible state」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS CodeDeploy | 協調EC2/on-premises、Lambda與ECS application deployments。 | Deployment group依strategy轉移traffic並執行lifecycle hooks；health/alarm可觸發rollback。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 |
| AWS Lambda aliases | 以穩定名稱指向特定Lambda version，並可在兩個versions之間分配呼叫權重。 | Alias保存primary version與可選additional version weight；CodeDeploy可逐步調整權重並由CloudWatch alarms觸發rollback。 |

## 把全圖套進一個具體案例

**場景：** 付款API需零停機、五分鐘內rollback，schema變更必須相容兩版本。

1. 故事的起點：付款API需零停機、五分鐘內rollback，schema變更必須相容兩版本。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS CodeDeploy負責「協調EC2/on-premises、Lambda與ECS application deployments。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Deployment group依strategy轉移traffic並執行lifecycle hooks；health/alarm可觸發rollback。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Elastic Load Balancing、AWS Lambda aliases各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只看deployment成功而未用business metric判斷canary，或立即銷毀blue。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「完整CI/CD orchestration需CodePipeline或外部pipeline；IaC資源由CloudFormation。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### CI/CD 的全圖：Source、Build、Artifact、Deploy 是四個責任，不是一個『Pipeline 服務』

最容易背錯的地方，是把 CodePipeline 當成會編譯、測試或部署所有東西。它主要負責 orchestrate stages；CodeBuild 執行 build/test，artifact 放 S3/ECR，CodeDeploy／CloudFormation／ECS deployment controller 負責實際 rollout。每一段都要有自己的 role、evidence 與 rollback contract。

```text
source commit
   ▼
pipeline orchestration
   ├─ build/test role ─ CodeBuild ─ artifact digest/SBOM
   ├─ approval / policy checks
   └─ deploy role ─ CodeDeploy/CloudFormation/ECS
                         ├─ canary/blue-green
                         └─ alarms → rollback
```

#### 一個 production gate 要檢查的是結果，不只是 stage 顯示綠色

```YAML
deployment_gate:
  immutable_artifact: sha256:...
  pre_deploy:
    - unit_and_integration_tests
    - cfn_guard_security_rules
  rollout:
    strategy: canary
    first_exposure: 10_percent
  rollback_on:
    - alarm: checkout_error_rate
    - alarm: checkout_p99_latency
  evidence:
    - deployment_id
    - artifact_digest
    - approver
    - alarm_history
```

1. 同一 immutable artifact 應依序 promoted，不要每個 environment 重新 build 出不同內容。
2. Pipeline service role、build role、deploy role 分開，讓 compromise 與錯誤只影響必要範圍。
3. Rollback 要有 application/data compatibility；把舊 binary 部署回去不一定能回復已做的 schema migration。

**選擇邊界：** 簡單 serverless/CloudFormation deployment 可用原生整合；複雜 application rollout 才加入 CodeDeploy；第三方 CI 也可行，判斷重點是 identity federation、artifact integrity、gates、blast radius 與 evidence。

**考試範圍：** SAA 掌握 deployment strategy；SAP 要能設計跨帳號 roles、artifact promotion、manual approval 邊界、multi-Region waves、rollback 與 audit trail。

- [AWS：CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)
- [AWS：CodeDeploy deployment configurations](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)

## 需要時再查：四個閱讀支點

### AWS CodeDeploy

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：新版本有未知風險，release strategy決定blast radius、成本與rollback速度。
- **具體例子／邊界：** 在「付款API需零停機、五分鐘內rollback，schema變更必須相容兩版本。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Elastic Load Balancing

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Database schema需expand/contract，否則compute rollback仍可能不相容。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只看deployment成功而未用business metric判斷canary，或立即銷毀blue。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：deployment safety comes from bounded exposure and reversible state。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### listener

在load balancer指定protocol/port等待client connection的入口。

### rollback

把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。

### canary

先把小比例流量或少數targets導向新版本，觀察technical與business指標後再擴大，以限制錯誤版本的blast radius。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

## 回到 AWS：Components、功用與責任邊界

### AWS CodeDeploy

- **功用：** 協調EC2/on-premises、Lambda與ECS application deployments。
- **底層機制：** Deployment group依strategy轉移traffic並執行lifecycle hooks；health/alarm可觸發rollback。
- **關鍵設定：** compute platform、deployment group、blue/green/in-place、traffic shifting、AppSpec、hooks與alarms。
- **選擇時機：** 需要managed rolling/blue-green、Lambda aliases或ECS task set切流。
- **替換時機：** 完整CI/CD orchestration需CodePipeline或外部pipeline；IaC資源由CloudFormation。

### Elastic Load Balancing

- **功用：** 將連線或request分散到健康targets並隔離client與backend生命週期。
- **底層機制：** Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
- **關鍵設定：** scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- **選擇時機：** 多instance/task高可用入口與rolling deployment。
- **替換時機：** 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。

### AWS Lambda aliases

- **功用：** 以穩定名稱指向特定Lambda version，並可在兩個versions之間分配呼叫權重。
- **底層機制：** Alias保存primary version與可選additional version weight；CodeDeploy可逐步調整權重並由CloudWatch alarms觸發rollback。
- **關鍵設定：** published versions、alias name、routing config、provisioned concurrency、CodeDeploy deployment config、alarms與hooks。
- **選擇時機：** Lambda canary/linear deployment、穩定invoke ARN與版本rollback。
- **替換時機：** 需要HTTP path/host routing用API Gateway/ALB；alias流量切分不會遷移外部state或schema。

## 考前與實作時再查：設定操作手冊

### AWS CodeDeploy：逐項設定說明

#### `compute platform`

- **控制什麼：** `compute platform`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要managed rolling/blue-green、Lambda aliases或ECS task set切流。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CodeDeploy鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `deployment group`

- **控制什麼：** `deployment group`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「需要managed rolling/blue-green、Lambda aliases或ECS task set切流。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CodeDeploy設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `blue/green/in-place`

- **控制什麼：** `blue/green/in-place`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「需要managed rolling/blue-green、Lambda aliases或ECS task set切流。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CodeDeploy設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `traffic shifting`

- **控制什麼：** `traffic shifting`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「需要managed rolling/blue-green、Lambda aliases或ECS task set切流。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CodeDeploy設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `AppSpec`

- **控制什麼：** `AppSpec`是可版本化的啟動或工作規格，定義AWS CodeDeploy建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `hooks`

- **控制什麼：** `hooks`把AWS CodeDeploy與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `alarms`

- **控制什麼：** `alarms`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要managed rolling/blue-green、Lambda aliases或ECS task set切流。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CodeDeploy選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

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

### AWS Lambda aliases：逐項設定說明

#### `published versions`

- **控制什麼：** `published versions`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「Lambda canary/linear deployment、穩定invoke ARN與版本rollback。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda aliases鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `alias name`

- **控制什麼：** `alias name`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「Lambda canary/linear deployment、穩定invoke ARN與版本rollback。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda aliases指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `routing config`

- **控制什麼：** 讓alias把大部分invocations送到primary published version，並以單一additional-version weight進行Lambda層canary或linear切流。
- **何時需要：** 需要在不改invoke ARN的情況下逐步推出新Lambda version，並能依CloudWatch alarm快速回到舊版本時。
- **怎麼設定／驗證：** 發布immutable version，讓alias先指舊版，再設定additional version weight；搭配CodeDeploy deployment config、hooks與alarms逐步調整。
- **常見錯法：** 權重是機率分配而非每小批request精準比例；alias切回不會回滾database schema、queue side effects或外部state。

#### `provisioned concurrency`

- **控制什麼：** `provisioned concurrency`設定AWS Lambda aliases的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「Lambda canary/linear deployment、穩定invoke ARN與版本rollback。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `CodeDeploy deployment config`

- **控制什麼：** `CodeDeploy deployment config`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「Lambda canary/linear deployment、穩定invoke ARN與版本rollback。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda aliases設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `alarms`

- **控制什麼：** `alarms`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「Lambda canary/linear deployment、穩定invoke ARN與版本rollback。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda aliases選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `hooks`

- **控制什麼：** `hooks`把AWS Lambda aliases與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. AWS CodeDeploy的責任：協調EC2/on-premises、Lambda與ECS application deployments。
2. 底層機制：Deployment group依strategy轉移traffic並執行lifecycle hooks；health/alarm可觸發rollback。
3. 第一個要看的設定：compute platform、deployment group、blue/green/in-place、traffic shifting、AppSpec、hooks與alarms。
4. 選擇邏輯：Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。
5. 不要混淆：Elastic Load Balancing的責任是「將連線或request分散到健康targets並隔離client與backend生命週期。」；它不會自動取代AWS CodeDeploy。
6. 替換訊號：完整CI/CD orchestration需CodePipeline或外部pipeline；IaC資源由CloudFormation。
7. 最常見錯法：只看deployment成功而未用business metric判斷canary，或立即銷毀blue。
8. 可移植原則：deployment safety comes from bounded exposure and reversible state。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS CodeDeploy | 協調EC2/on-premises、Lambda與ECS application deployments。 | Deployment group依strategy轉移traffic並執行lifecycle hooks；health/alarm可觸發rollback。 | 需要managed rolling/blue-green、Lambda aliases或ECS task set切流。 | 完整CI/CD orchestration需CodePipeline或外部pipeline；IaC資源由CloudFormation。 |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 | 多instance/task高可用入口與rolling deployment。 | 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。 |
| AWS Lambda aliases | 以穩定名稱指向特定Lambda version，並可在兩個versions之間分配呼叫權重。 | Alias保存primary version與可選additional version weight；CodeDeploy可逐步調整權重並由CloudWatch alarms觸發rollback。 | Lambda canary/linear deployment、穩定invoke ARN與版本rollback。 | 需要HTTP path/host routing用API Gateway/ALB；alias流量切分不會遷移外部state或schema。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Database schema需expand/contract，否則compute rollback仍可能不相容。 | 只有當題目條件明確改變時才可能合理。 | 只看deployment成功而未用business metric判斷canary，或立即銷毀blue。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Database schema需expand/contract，否則compute rollback仍可能不相容。」之間做選擇。
- 認得常考設定：compute platform、deployment group、blue/green/in-place、traffic shifting、AppSpec、hooks與alarms。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：完整CI/CD orchestration需CodePipeline或外部pipeline；IaC資源由CloudFormation。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜rolling 與 all-at-once 選擇

一組 40 台 EC2 application servers 沒有足夠預算建立完整 duplicate fleet，但可在部署期間同時執行新舊版本；容量規劃顯示至少 32 台必須保持健康。哪個策略最合適？

A. Blue/green，因它不需要任何額外 instances
B. 使用 EC2/on-premises in-place deployment，建立 custom deployment configuration，將 minimum healthy hosts 設為至少 32 台或 80%，並先驗證新舊版本相容
C. 任意使用最大 batch，因縮短部署時間比 minimum healthy capacity 更重要
D. All-at-once，因同時替換全部 instances 會產生最小 customer blast radius

**答案：B**

- **A：** 錯誤。Blue/green 的典型代價正是同時維持 replacement 與 original capacity。
- **B：** 正確。這裡的 rolling 是部署策略描述；CodeDeploy EC2/on-premises 的實際控制欄位是 minimum healthy hosts，而不是另一個獨立 batch-size 設定。設為至少 32 台或 80% 可約束同時離線更新的上限，仍須驗證 mixed-version compatibility。
- **C：** 錯誤。Batch 過大可能把健康容量降到服務需求以下；部署速度不能越過 availability constraint。
- **D：** 錯誤。All-at-once 把整個 fleet 同時暴露於新版本，也可能造成完整中斷。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Work with CodeDeploy deployment configurations](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)、[CodeDeploy deployments on EC2 and on-premises instances](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps.html)

### 練習題 2｜SAA｜blue/green 的成本與 rollback 邊界

付款 API 要求近乎零中斷，application tier 必須能在一分鐘內切回舊版；公司願意在 30 分鐘觀察期支付兩套 stateless capacity。哪個方案最符合？

A. Blue/green 切換後立即刪除 blue，因 DNS 或 load balancer 可從 snapshot 自動恢復它
B. Rolling 且部署完第一台就刪除所有舊 instances
C. 建立並驗證 green environment，切換流量後保留 blue 至觀察期結束；另處理共享資料與不可逆 side effects
D. All-at-once，失敗時再重新 build 舊版本

**答案：C**

- **A：** 錯誤。立即銷毀 blue 就失去快速回切能力，流量層也不會自動還原已刪除的 compute environment。
- **B：** 錯誤。這不保留完整可迅速回切的 original environment。
- **C：** 正確。Blue/green 用 duplicate environment 換取低中斷與快速 application traffic reversal；保留時間與資料契約仍需明確。
- **D：** 錯誤。重新 build 與部署無法滿足一分鐘 reversal，且 production exposure 最大。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[CodeDeploy blue/green deployments for Amazon ECS](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-ecs.html)、[OPS06-BP01 Plan for unsuccessful changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html)

### 練習題 3｜SAA｜canary、bake time 與 stop criteria

新推薦演算法的缺陷只會在真實流量組合下出現。產品允許先讓 5% 使用者接觸新版本，但要求付款成功率或 p99 latency 惡化時不得再擴大流量。應如何部署？

A. 先送 5% 流量，經過足以覆蓋故障模式的 bake time，檢查業務與技術 alarms；健康才繼續，否則停止並 rollback
B. 送 5% 後立即切到 100%，因初始比例已限制全部風險
C. 固定每五分鐘加流量，即使 alarms 已進入 ALARM 仍照表前進
D. 只看 deployment status；只要 CodeDeploy 成功，customer metrics 無需檢查

**答案：A**

- **A：** 正確。Canary 的價值來自 bounded exposure 加 evidence-based promotion；bake time 要與延遲故障相符。
- **B：** 錯誤。沒有觀察期就無法利用小流量驗證真實流量下的延遲故障；若需求改成只驗證部署步驟且可接受立即全面暴露，才可能縮短 bake time。
- **C：** 錯誤。Promotion 必須受 stop criteria 控制，不能在健康訊號失敗時繼續。
- **D：** 錯誤。Control-plane completion 不能證明推薦、付款或 latency 等 customer outcomes。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Work with CodeDeploy deployment configurations](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)、[Monitor CodeDeploy deployments with CloudWatch alarms](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring-create-alarms.html)、[OPS06-BP04 Automate testing and rollback](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html)

### 練習題 4｜SAA｜Lambda version、alias 與 CodeDeploy

Lambda function 的 clients 固定呼叫 `prod` alias。團隊想把 10% 流量送到不可變的新 revision，驗證 hook 與 alarm 正常後再全量；失敗要把 alias traffic 還原。哪個做法正確？

A. 每次改 client URL 指向新的 function name，不使用 alias
B. Publish 新 version，讓 CodeDeploy 調整 `prod` alias 的版本權重，並設定 validation hooks、alarms 與 rollback
C. 修改已 published version 的 environment variables，讓它成為新 revision
D. 在兩份 `$LATEST` 之間直接設定 weighted routing

**答案：B**

- **A：** 錯誤。改 client 會失去穩定 endpoint 與集中式 traffic control，也增加 rollback 時間。
- **B：** 正確。Alias 提供穩定名稱，CodeDeploy 可在兩個 published versions 間執行 canary/linear shift 並由 alarm 觸發回切。
- **C：** 錯誤。Published Lambda version 是 immutable snapshot，需 publish 另一個 version 表達新 revision。
- **D：** 錯誤。Weighted alias routing 是針對 published versions；`$LATEST` 不是不可變 release artifact。

**事實查證：** [CodeDeploy deployments on Lambda](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-lambda.html)、[Roll back and redeploy with CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)

### 練習題 5｜SAA｜ECS CodeDeploy blue/green topology

ECS service 要在 production traffic 切換前，用 test listener 驗證新 task set；切換失敗時舊 task set 必須仍可接回流量。哪個配置符合 CodeDeploy blue/green 模型？

A. 把新舊 tasks 全放在同一 target group，ALB health check 通過即刪除舊 tasks
B. 只依賴 container process running 狀態，因它等同完整業務交易驗證
C. 在 production 切流前先終止 original task set，以釋放容量
D. 使用 original 與 replacement task sets/target groups、production listener 與可選 test listener，搭配 lifecycle hooks、alarms 和 termination wait

**答案：D**

- **A：** 錯誤。單一 target group 無法清楚表達 CodeDeploy 管理的 original/replacement traffic boundary。
- **B：** 錯誤。Process/ALB health 是必要訊號之一，但不證明登入、結帳或資料一致性等 business flow。
- **C：** 錯誤。提前終止 original 會消除快速 rollback 的目標。
- **D：** 正確。兩組 target groups 與 task sets 讓 test traffic、production cutover、alarm rollback 和舊環境保留具備明確狀態。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[CodeDeploy blue/green deployments for Amazon ECS](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-ecs.html)、[Monitor CodeDeploy deployments with CloudWatch alarms](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring-create-alarms.html)

### 練習題 6｜SAP｜EC2 in-place 與 blue/green mechanics

公司有兩套 EC2 workload：A 的資料只存在本機且目前無法重建；B 完全 stateless、位於 ALB 後方並可臨時增加容量。哪個部署決策最合理？

A. A 與 B 都一律 in-place，因 CodeDeploy managed service 可保證零中斷
B. 只要 AppSpec hooks 成功，A 與 B 都不需要 load balancer/application health checks
C. A 與 B 都一律 blue/green，因本機資料會自動複製到 replacement instances
D. A 在確認 backup 與容量影響後採受控 in-place；B 可用 blue/green replacement，以額外容量換 immutable hosts 與快速回切

**答案：D**

- **A：** 錯誤。In-place 會修改現有 hosts 並可能降低 serving capacity，managed orchestration 不等於零中斷。
- **B：** 錯誤。Hook completion 只證明 script 階段成功；仍需 runtime 與 customer-path validation。
- **C：** 錯誤。Blue/green 不會自動遷移 instance-local durable state；若無外部化/同步策略可能遺失資料。
- **D：** 正確。策略應由 state、replacement feasibility、capacity 與 rollback contract 決定，而不是全公司只選一種。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[CodeDeploy deployments on EC2 and on-premises instances](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps.html)、[CodeDeploy blue/green deployments for Amazon ECS](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-ecs.html)

### 練習題 7｜SAP｜build once promote same artifact

Production container image 必須與 staging 通過測試的 image 位元完全相同。現行 pipeline 會在每個 account 重新 docker build，即使使用相同 commit。應如何改善？

A. 繼續每個 account 重建，因相同 Git commit 保證 compiler、base image 與 dependency 完全相同
B. Build 一次，記錄 immutable image digest 與測試 evidence，逐環境 promotion 同一 digest；環境設定由外部注入
C. 所有環境都使用可覆寫的 `latest` tag，以方便快速更新
D. 把 production credentials 烘進 image，避免 target deployment role

**答案：B**

- **A：** 錯誤。Base tag、dependency repository、build toolchain 與時間都可能使相同 source 產生不同 bits。
- **B：** 正確。Digest 固定 artifact identity，能證明 production 所執行的就是已測 revision；設定與 binary 應分離。
- **C：** 錯誤。Mutable tag 會讓核准內容與實際拉取內容分離，破壞 provenance。
- **D：** 錯誤。把 credentials 放進 image 造成長期 secret 暴露，應由 workload/deployment role 在 runtime 取得權限。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)、[OPS06-BP01 Plan for unsuccessful changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html)

### 練習題 8｜SAP｜cross-account pipeline trust 與 artifact encryption

Tooling account 的 CodePipeline 把 encrypted S3 artifact 部署到 production account。Target role 能被 assume，也有 s3:GetObject，但仍收到 KMS AccessDenied。最適當的修正是什麼？

A. 改用 artifact bucket 的 AWS managed key，並假設所有帳號都能解密
B. 把 production IAM user access key 存入 CodeBuild environment variables
C. 把 target role 改成 AdministratorAccess，無須調整 resource policy
D. 在 KMS key policy/grant 與 IAM policy 中允許正確的 cross-account role 解密，並保持 bucket、pipeline role、target role 各自最小權限

**答案：D**

- **A：** 錯誤。跨帳號 artifact encryption 需要選擇可授權 target principal 的 key 與明確 policy。
- **B：** 錯誤。永久 access key 不必要，會降低輪替、撤銷與 attribution 能力；只有無法使用 IAM role 的外部系統才應另評估短期或受控 credentials。
- **C：** 錯誤。Identity policy 過度擴權也不能保證 resource-based KMS key policy 建立跨帳號信任。
- **D：** 正確。S3 object access 與 KMS decrypt 是兩個獨立 authorization checks；pipeline 設計必須同時滿足。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Create a cross-account CodePipeline pipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-create-cross-account.html)、[AWS CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)

### 練習題 9｜SAP｜expand/contract schema migration

Canary 期間舊版與新版會同時讀寫同一資料庫與事件 stream，而且 rollback 後舊版仍需工作。哪些 TWO 步驟符合 expand/contract？

A. 等舊 writers/readers 完全退出且驗證完成後，在後續 release 移除舊結構，並為不可逆 side effects 設補償
B. Canary 開始時立即 rename 或 drop 舊欄位，迫使所有 clients 升級
C. 先新增向後相容的欄位/結構，部署能同時讀寫舊新格式的程式，再安全 backfill
D. Rollback 時重播所有 events，不檢查 idempotency、ordering 或 duplicate effects
E. 假設 compute traffic 回切會自動撤銷 schema、付款與已發出的 events

**答案：A、C**

- **A：** 正確。Contract 階段應在舊版確定退出後進行，且資料/事件副作用需有獨立 recovery 設計。
- **B：** 錯誤。提前破壞舊 contract 會使 canary mixed traffic 與 rollback 都失敗。
- **C：** 正確。Expand 先增加兼容能力，讓 mixed versions 可以安全共存，再逐步移轉資料與讀寫路徑。
- **D：** 錯誤。無條件 replay 可能造成重複扣款、亂序或再次觸發外部副作用。
- **E：** 錯誤。Load balancer 或 alias 只控制 compute traffic，不會通用逆轉 durable state 與外部動作。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[OPS06-BP01 Plan for unsuccessful changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html)、[OPS06-BP04 Automate testing and rollback](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html)

### 練習題 10｜SAP｜deployment rollback signals

新版通過 ALB health check，但付款成功率下降 12%，dependency timeout 與 p99 latency 同時上升。團隊要自動 rollback 且避免單一雜訊 datapoint 造成振盪。哪些 TWO 做法最佳？

A. 任何一筆失敗 request 都立即 rollback，不需要 bake time 或 threshold
B. 把適當 alarms 接到 deployment rollback，並保留 deployment revision、metrics 與 logs 供後續診斷
C. 用付款成功率、error/latency、dependency 與 saturation 等互補 signals，設定合理 period/evaluation windows 與 missing-data behavior
D. 只監控 EC2 CPU，因所有 application regression 最終都會反映在 CPU
E. 只信任 CodeDeploy SUCCEEDED，因 deployment status 等同 customer success

**答案：B、C**

- **A：** 錯誤。單筆失敗通常不具統計意義，容易造成 false positive 與 rollout oscillation。
- **B：** 正確。自動 rollback 需要明確 alarm integration，診斷則需要保存 release context 與執行期 evidence。
- **C：** 正確。多層 signals 能同時捕捉 customer impact 與可能原因；window/threshold 可降低瞬時噪音。
- **D：** 錯誤。CPU 可能正常而下游 dependency、程式邏輯或付款成功率已失敗；只有已證明 CPU 是此回歸的可靠領先指標時，才可把它納入而非單獨使用。
- **E：** 錯誤。Deployment orchestration success 只表示步驟完成，不代表 workload outcome。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Monitor CodeDeploy deployments with CloudWatch alarms](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring-create-alarms.html)、[Roll back and redeploy with CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)、[Use Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)、[OPS06-BP04 Automate testing and rollback](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「新版本有未知風險，release strategy決定blast radius、成本與rollback速度。」，所以「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」能直接滿足它；若constraint改成「Database schema需expand/contract，否則compute rollback仍可能不相容。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」。替代方案「Database schema需expand/contract，否則compute rollback仍可能不相容。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只看deployment成功而未用business metric判斷canary，或立即銷毀blue。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「新版本有未知風險，release strategy決定blast radius、成本與rollback速度。」，排除會導致「只看deployment成功而未用business metric判斷canary，或立即銷毀blue。」的選項，再選「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Canary逐步曝險，blue/green保留完整舊環境快速切回，rolling節省容量但版本混合。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「deployment safety comes from bounded exposure and reversible state」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 75 章　Systems Manager、Patching 與 Fleet Management

大量instance需要安全遠端操作、inventory、patch與參數管理，不能共享SSH key。

## 跟著一次變更走到production：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：一千台private EC2需緊急patch，禁止bastion與inbound SSH。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：大量instance需要安全遠端操作、inventory、patch與參數管理，不能共享SSH key。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Systems Manager，對照角色是Session Manager。我們選擇「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：一千台private EC2需緊急patch，禁止bastion與inbound SSH。

正常production路徑
          ▼
[AWS Systems Manager] → 使用者可觀察的結果
          │ 集中管理EC2與hybrid managed nodes的inventory、run commands、patch…
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Session Manager：透過Systems Manager建立可稽核shell/port-forwarding，不需bastion…
  · Patch Manager：依baseline與maintenance windows掃描/安裝managed nodes patch…

失敗時先找：開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS Systems Manager有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Systems Manager和Session Manager並不是兩個任意的產品名稱。前者適合本章，是因為「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」直接回應了眼前的問題；後者描述的「Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「prefer audited control channels over direct host access」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 |
| Session Manager | 透過Systems Manager建立可稽核shell/port-forwarding，不需bastion或inbound SSH。 | Authenticated user經SSM control channels連到agent；session traffic可加密並記錄。 |
| Patch Manager | 依baseline與maintenance windows掃描/安裝managed nodes patches。 | SSM Agent執行patch document，依OS repository與baseline分類approved/rejected。 |

## 把全圖套進一個具體案例

**場景：** 一千台private EC2需緊急patch，禁止bastion與inbound SSH。

1. 故事的起點：一千台private EC2需緊急patch，禁止bastion與inbound SSH。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Systems Manager負責「集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Session Manager、Patch Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Systems Manager

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：大量instance需要安全遠端操作、inventory、patch與參數管理，不能共享SSH key。
- **具體例子／邊界：** 在「一千台private EC2需緊急patch，禁止bastion與inbound SSH。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Session Manager

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：prefer audited control channels over direct host access。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### drift

實際resource設定與IaC宣告狀態不同，常由console手動修改或外部automation造成。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS Systems Manager

- **功用：** 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。
- **底層機制：** SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。
- **關鍵設定：** managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
- **選擇時機：** fleet operations、patch、secure access、runbook與remediation。
- **替換時機：** container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。

### Session Manager

- **功用：** 透過Systems Manager建立可稽核shell/port-forwarding，不需bastion或inbound SSH。
- **底層機制：** Authenticated user經SSM control channels連到agent；session traffic可加密並記錄。
- **關鍵設定：** instance role、agent/endpoints、session preferences、KMS、S3/Logs logging與IAM conditions。
- **選擇時機：** private instances的administrative access、減少SSH keys與public IP。
- **替換時機：** 若agent或SSM endpoint不可用需break-glass path；它不是application user access。

### Patch Manager

- **功用：** 依baseline與maintenance windows掃描/安裝managed nodes patches。
- **底層機制：** SSM Agent執行patch document，依OS repository與baseline分類approved/rejected。
- **關鍵設定：** patch baseline、approval delay、patch groups、maintenance window、scan/install與compliance reporting。
- **選擇時機：** EC2/hybrid OS fleet規模化patch與audit。
- **替換時機：** immutable image workflow可用Image Builder+rolling replacement，避免in-place drift。

## 考前與實作時再查：設定操作手冊

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

### Session Manager：逐項設定說明

#### `instance role`

- **控制什麼：** `instance role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「private instances的administrative access、減少SSH keys與public IP。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Session Manager明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `agent/endpoints`

- **控制什麼：** `agent/endpoints`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「private instances的administrative access、減少SSH keys與public IP。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Session Manager的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `session preferences`

- **控制什麼：** `session preferences`控制Session Manager的客製化、變更執行scope、失敗容忍度或operator session行為。
- **何時需要：** 平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。
- **怎麼設定／驗證：** 版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。
- **常見錯法：** 大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「private instances的administrative access、減少SSH keys與public IP。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Session Manager指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `S3/Logs logging`

- **控制什麼：** `S3/Logs logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「private instances的administrative access、減少SSH keys與public IP。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Session Manager選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `IAM conditions`

- **控制什麼：** `IAM conditions`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「private instances的administrative access、減少SSH keys與public IP。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Session Manager明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### Patch Manager：逐項設定說明

#### `patch baseline`

- **控制什麼：** `patch baseline`定義哪些patch被核准、哪些fleet套用、何時只掃描或實際安裝，以及如何回報compliance。
- **何時需要：** EC2/on-prem managed nodes需要可分波、可稽核的OS patch流程時。
- **怎麼設定／驗證：** 建立baseline與approval delay，將instances標記到patch group，透過maintenance window先Scan再小批Install，監控reboot與rollback。
- **常見錯法：** 直接全fleet Install可能造成同時reboot；compliant只表示符合baseline，不代表application已通過功能與容量測試。

#### `approval delay`

- **控制什麼：** `approval delay`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「EC2/hybrid OS fleet規模化patch與audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Patch Manager的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `patch groups`

- **控制什麼：** `patch groups`定義哪些patch被核准、哪些fleet套用、何時只掃描或實際安裝，以及如何回報compliance。
- **何時需要：** EC2/on-prem managed nodes需要可分波、可稽核的OS patch流程時。
- **怎麼設定／驗證：** 建立baseline與approval delay，將instances標記到patch group，透過maintenance window先Scan再小批Install，監控reboot與rollback。
- **常見錯法：** 直接全fleet Install可能造成同時reboot；compliant只表示符合baseline，不代表application已通過功能與容量測試。

#### `maintenance window`

- **控制什麼：** `maintenance window`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「EC2/hybrid OS fleet規模化patch與audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Patch Manager的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `scan/install`

- **控制什麼：** `scan/install`定義哪些patch被核准、哪些fleet套用、何時只掃描或實際安裝，以及如何回報compliance。
- **何時需要：** EC2/on-prem managed nodes需要可分波、可稽核的OS patch流程時。
- **怎麼設定／驗證：** 建立baseline與approval delay，將instances標記到patch group，透過maintenance window先Scan再小批Install，監控reboot與rollback。
- **常見錯法：** 直接全fleet Install可能造成同時reboot；compliant只表示符合baseline，不代表application已通過功能與容量測試。

#### `compliance reporting`

- **控制什麼：** `compliance reporting`定義Patch Manager用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

## 讀到這裡，請用自己的話說一次

1. AWS Systems Manager的責任：集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。
2. 底層機制：SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。
3. 第一個要看的設定：managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
4. 選擇邏輯：使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。
5. 不要混淆：Session Manager的責任是「透過Systems Manager建立可稽核shell/port-forwarding，不需bastion或inbound SSH。」；它不會自動取代AWS Systems Manager。
6. 替換訊號：container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。
7. 最常見錯法：開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。
8. 可移植原則：prefer audited control channels over direct host access。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 | fleet operations、patch、secure access、runbook與remediation。 | container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。 |
| Session Manager | 透過Systems Manager建立可稽核shell/port-forwarding，不需bastion或inbound SSH。 | Authenticated user經SSM control channels連到agent；session traffic可加密並記錄。 | private instances的administrative access、減少SSH keys與public IP。 | 若agent或SSM endpoint不可用需break-glass path；它不是application user access。 |
| Patch Manager | 依baseline與maintenance windows掃描/安裝managed nodes patches。 | SSM Agent執行patch document，依OS repository與baseline分類approved/rejected。 | EC2/hybrid OS fleet規模化patch與audit。 | immutable image workflow可用Image Builder+rolling replacement，避免in-place drift。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。 | 只有當題目條件明確改變時才可能合理。 | 開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。」之間做選擇。
- 認得常考設定：managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Systems Manager managed-node prerequisites

一批 private EC2 instances 已安裝 SSM Agent，但 Fleet Manager 看不到節點。公司禁止 public IP 與 inbound administration ports。哪個檢查清單最完整？

A. 只把 Systems Manager permission 加到工程師的 IAM user；instance 會繼承 user credentials
B. 從管理員電腦對 instances 開放 inbound TCP 443；node 不需要 IAM role
C. 在 security group 開放 inbound SSH，因 SSM Agent 透過 SSH 註冊
D. 確認 agent 版本與運作狀態，使用 Default Host Management Configuration 或具最小權限的 EC2 instance profile，並確認時間、DNS 與到必要 Systems Manager endpoints 的 outbound HTTPS

**答案：D**

- **A：** 錯誤。Human principal 只決定誰可呼叫管理 API；在此 EC2 context，node 本身仍須使用 Default Host Management Configuration，或附加具 Systems Manager 最小權限的 EC2 instance profile。Hybrid activation 僅適用於 non-EC2 hybrid 或 multicloud machines。
- **B：** 錯誤。Agent 是由 node 主動連到 service endpoints；不需要從管理員網路對 instance 開 inbound 443。
- **C：** 錯誤。SSM Agent 不依賴 inbound SSH 註冊；保留 22 反而違反題目安全要求。
- **D：** 正確。EC2 managed node 需要 agent、node identity/permissions 與 control-plane connectivity 三者同時成立。Hybrid activation 是給 non-EC2 hybrid 或 multicloud machines 使用，不是這批 EC2 instances 的同等身分選項。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Configure managed-node permissions for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-instance-permissions.html)、[Create VPC endpoints for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)

### 練習題 2｜SAA｜SSM control channel 與 OS repository connectivity

Private instances 可正常開啟 Session Manager shell，也能執行 Run Command，但 Patch Manager 安裝時顯示無法下載套件。只有 Systems Manager interface endpoints，沒有 NAT 或內部 package mirror。最可能缺少什麼？

A. Systems Manager endpoint 會鏡像所有 Linux/Windows repositories，因此問題一定是 inbound rule
B. 對每台 instance 開放 inbound 80/443，讓 repository 主動推送套件
C. Session Manager 成功已證明所有 patch payload 都能下載，應忽略錯誤
D. 除 Systems Manager interface endpoints 外，還要以 S3 gateway endpoint 與 endpoint/IAM policy 允許 Patch Manager operation buckets，並讓作業系統 package manager 到達核准 repositories 或 internal mirror

**答案：D**

- **A：** 錯誤。SSM service endpoints 不會替各 OS vendor 或自建 repository 提供透明鏡像。
- **B：** 錯誤。Package manager 通常主動對 repository 發起連線，不需要 repository 對 node 開 inbound。
- **C：** 錯誤。Management command path 與 package-content data path 是不同依賴。
- **D：** 正確。Patch Manager 有三段相互獨立的路徑：interface endpoints 承載 management/control channel；AWS-managed S3 patch-operation buckets 提供 command documents 與 baseline snapshots；yum、apt、Windows Update、WSUS 或 internal mirror 提供實際 package content。只打通第一段仍會下載失敗。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Create VPC endpoints for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)、[AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)、[Amazon S3 buckets used by Patch Manager operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-operations-s3-buckets.html)

### 練習題 3｜SAA｜Session Manager logging limitations

公司要淘汰 bastion 與共用 SSH key，改用 IAM 控制的 Session Manager。稽核人員要求準確說明 transcript：哪些敘述正確？

A. 共用一個 IAM role 給所有人最容易稽核，因 transcript 會自動還原每位真實使用者
B. 只要啟用 S3 logging，所有經 port forwarding 傳送的 SQL payload 都會逐字記錄
C. 可為受支援的互動 shell 設定 S3/CloudWatch Logs 記錄；但 SSH 與 port-forwarding 的加密 tunnel 內容不會被 Session Manager command logging 解讀
D. Session Manager 一定需要 instance 對管理員開 inbound 22

**答案：C**

- **A：** 錯誤。稽核需要 per-user IAM identity 與最小權限；共用 principal 會降低 attribution。
- **B：** 錯誤。Port forwarding 內容不會因設定 log destination 就被 Session Manager 解密成 SQL transcript。
- **C：** 正確。Session metadata 與支援的 shell content 可集中記錄，但 encrypted SSH/port-forwarding traffic 有明確 logging limitation。
- **D：** 錯誤。Session Manager 的核心優點之一是無需 inbound SSH 或 bastion。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)、[Session Manager logging limitations](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-logging.html)

### 練習題 4｜SAP｜Run Command rate control

團隊要對 5,000 台 nodes 執行設定修正，但同時處理不得超過 5%，累積失敗超過 1% 就要停止擴散，且需保存每台執行結果。哪個做法最合適？

A. 由工程師逐台開 Session Manager shell，以換取一致性
B. 把 max-errors 設為 100%，確保命令不會提早停止
C. Target 全 fleet 並使用 unlimited concurrency，因 Systems Manager 會自動推斷 application capacity
D. 以 tags/resource groups target，先跑 canary，再設定 max-concurrency=5%、max-errors=1%，收集 invocation status/output

**答案：D**

- **A：** 錯誤。逐台互動不可規模化、難重現，也無法一致執行 rate/error controls。
- **B：** 錯誤。高 error threshold 會容許已知有害命令繼續擴散。
- **C：** 錯誤。Managed orchestration 不知道 workload 的 quorum、capacity 或 business blast-radius 限制。
- **D：** 正確。Target selection、concurrency 與 error threshold 共同界定變更波次，per-target status 則提供證據。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Run commands at scale](https://docs.aws.amazon.com/systems-manager/latest/userguide/send-commands-multiple.html)

### 練習題 5｜SAA｜Systems Manager capabilities responsibility map

團隊分別要：(1) 蒐集 installed applications；(2) 持續確保 NTP 設定；(3) 立刻執行一次診斷命令；(4) 每月在核准時窗重啟服務。哪個對應正確？

A. Inventory 改設定；Run Command 蒐集 durable inventory；Session Manager 排程每月工作；Maintenance Windows 維持 desired state
B. CloudTrail 蒐集 installed packages，Config 直接登入 instance 修正 NTP
C. Inventory 蒐集 facts；State Manager association 維持 desired state；Run Command 執行一次性動作；Maintenance Windows 排程 disruptive tasks
D. Patch Manager 同時取代四項，因所有 fleet operation 都是 patch

**答案：C**

- **A：** 錯誤。Inventory 是 read-oriented metadata collection，不負責修改；其餘責任也被互換。
- **B：** 錯誤。CloudTrail 記錄 AWS API activity，Config 記錄/evaluate AWS resource configuration，兩者不會直接盤點 OS packages 或登入修改 NTP。
- **C：** 正確。四個 capabilities 分別對應 inventory、continuous association、ad hoc command 與 bounded schedule。
- **D：** 錯誤。Patch Manager 專注於 patch classification/scan/install，不是所有 host management 的單一替代品。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS Systems Manager Inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html)、[AWS Systems Manager State Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-state.html)、[AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html)、[Choose between State Manager and Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-vs-maintenance-windows.html)

### 練習題 6｜SAA｜patch baseline 與 schedule 分工

Windows servers 的 security updates 要在 release 後 7 天自動核准，但已知有問題的 KB 必須拒絕；Linux 使用不同規則。實際安裝只可在週日維護窗。應如何設計？

A. 把 patch 核准後立刻安裝所有 nodes，因 baseline 就是 execution schedule
B. 使用一份 Windows baseline 套用所有 Linux package classifications
C. 只設定 Maintenance Window；它會同時決定每個 OS 哪些 patches approved/rejected
D. 為 Windows 與 Linux 分別建立 custom patch baselines，設定 approval delay 與 rejected patches；建立週日 Maintenance Window 執行 AWS-RunPatchBaseline

**答案：D**

- **A：** 錯誤。Baseline 決定 eligible patches；是否及何時執行是另一層 orchestration。
- **B：** 錯誤。不同作業系統的 product/classification 與 repository semantics 不可假設相同。
- **C：** 錯誤。Maintenance Window 控制作業何時與以何種 rate 執行，不定義 patch classification policy。
- **D：** 正確。Custom baseline 決定各 OS 哪些 patches 在七天後成為 eligible，以及哪些 KB/package 必須拒絕；Maintenance Window 則只負責週日何時執行 AWS-RunPatchBaseline。若改採 Quick Setup patch policy，schedule 與 reboot behavior 應由 policy 本身定義，不必再假設另建 Maintenance Window。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Predefined and custom patch baselines](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-predefined-and-custom-patch-baselines.html)、[Patch policy configurations in Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-policies.html)、[AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html)、[AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)

### 練習題 7｜SAA｜Patch scan、install 與 reboot evidence

稽核報告顯示所有 nodes 的 `AWS-RunPatchBaseline` Scan command 成功。團隊因此宣稱 patches 已安裝且 kernel fix 已生效。哪個判斷正確？

A. `NoReboot` 代表所有需要重啟的修補也已立即完全生效
B. Scan 只評估/回報 compliance；要 remediation 必須執行 Install，按需求選 reboot behavior，並在 reboot 後驗證 compliance 與 application health
C. Scan 會安裝所有 approved patches，只是不會留下紀錄
D. Command success 自動證明服務已重新加入 load balancer 且業務交易正常

**答案：B**

- **A：** 錯誤。NoReboot 只控制 document 不主動重啟；某些更新可能待 reboot 才生效。
- **B：** 正確。Scan、Install、Reboot 與 application validation 是不同證據；不可由第一步推論後三步。
- **C：** 錯誤。Scan 用於識別 missing/failed 等 compliance state，不執行安裝。
- **D：** 錯誤。Command exit status 不涵蓋 cluster membership、load balancer health 或 end-to-end transaction。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)、[AWS Systems Manager Compliance](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-compliance.html)

### 練習題 8｜SAP｜availability-aware patch waves

十二台 clustered nodes 分散三個 AZ；任何時刻至少九台健康且每個 AZ 至少兩台，否則 quorum 或容量不足。哪個 patch plan 最安全？

A. 只檢查 patch command exit code，不檢查 node drain、rejoin 或 customer traffic
B. 一次 patch 全 fleet，失敗後再用 max-errors 報告結果
C. 三個 AZ 同時各關閉三台，因 Multi-AZ 名稱保證 quorum
D. 先 patch 小型 canary，逐 wave drain/patch/reboot/rejoin；concurrency 不越過九台與每 AZ 下限，application check 失敗即停止

**答案：D**

- **A：** 錯誤。OS command 成功不代表 node 已回到 serving set 或 cluster state 正常。
- **B：** 錯誤。100% concurrency 直接越過 availability constraint，error reporting 不能追回中斷。
- **C：** 錯誤。這會只剩三台，不符合至少九台的硬限制；Multi-AZ 不會替應用自動維持 quorum。
- **D：** 正確。Patch wave 必須結合 infrastructure rate controls、workload drain/rejoin 與 business health gate。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html)、[AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)

### 練習題 9｜SAP｜organization patch policy governance

企業要由 delegated admin 對多帳號、多 Regions 定義 patch policy，同時保留 member node 的 least-privilege identity 與集中 compliance。哪些 TWO 做法正確？

A. 只在 management account 建一個 Maintenance Window，它會無需角色地直接控制所有 member nodes
B. Organization targeting 會自動取代每個 managed node 的 IAM identity 與 endpoint connectivity
C. 監控 Quick Setup configuration deployment 狀態與各 node compliance，並明確設定 delegated administration 與 execution permissions
D. 用 Systems Manager Quick Setup patch policy 選定 Organization/OUs、Regions、targets、baseline、schedule 與 reboot behavior
E. 自訂 baseline 被 policy 引用時可直接刪除，不會影響後續執行

**答案：C、D**

- **A：** 錯誤。Member accounts 與 nodes 仍需要正確的組織部署、roles、agent 與 connectivity。
- **B：** 錯誤。Central targeting 不會消除 data-plane managed-node prerequisites。
- **C：** 正確。中央 policy 建立成功與 nodes 真正 compliant 是兩種 evidence，必須分別監控。
- **D：** 正確。Quick Setup 提供跨帳號/Region rollout 的 patch-policy 管理平面，但 target scope 與 patch/reboot contract 仍需明確。
- **E：** 錯誤。刪除被引用 baseline 會破壞 policy dependency；應先更新 consumers 與 lifecycle。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Configure organization patching with Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/quick-setup-patch-manager.html)、[Patch policy configurations in Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-policies.html)、[AWS Systems Manager Compliance](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-compliance.html)

### 練習題 10｜SAP｜immutable replacement 與 in-place patching

公司同時有 stateless Auto Scaling web fleet 與無法在本季重建的 legacy stateful nodes。安全修補期限為七天。哪些 TWO 決策最合理？

A. 假設任何 OS patch 都能完整 uninstall，所以不需 backup 或 recovery plan
B. 先終止 legacy stateful nodes，再確認資料是否位於 durable external storage
C. 所有 hosts 一律 in-place patch，因 Patch Manager 必然比 replacement 風險低
D. 對 stateless fleet 建立 patched/tested image，分 wave 替換 instances，以降低長期 drift 並保留舊 image rollback
E. 對暫時無法重建的 legacy nodes 採 canary、backup、in-place patch、reboot 與 application recovery 驗證，並建立未來外部化 state 的計畫

**答案：D、E**

- **A：** 錯誤。Patch rollback 能力依 OS/package 而異，且資料與 application side effects 仍需 recovery design。
- **B：** 錯誤。未確認 durable state 就終止會造成不可逆資料風險。
- **C：** 錯誤。Stateless/replaceable workloads 常能從 immutable image workflow 得到更一致的結果。
- **D：** 正確。Golden image 加 replacement 使新 hosts 從已知狀態建立，也能以 Auto Scaling 控制 exposure。
- **E：** 正確。無法重建的 stateful fleet 可先以受控 in-place 流程滿足期限，同時降低下一輪的結構性限制。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Patch policy configurations in Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-policies.html)、[AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)、[OPS06-BP01 Plan for unsuccessful changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「使用SSM Agent、Session Manager、Patch Manager、Run Command…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「大量instance需要安全遠端操作、inventory、patch與參數管理，不能共享SSH key。」，所以「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」能直接滿足它；若constraint改成「Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」。替代方案「Immutable replacement可降低長期drift，但某些stateful/legacy fleet仍需in-place管理。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「大量instance需要安全遠端操作、inventory、patch與參數管理，不能共享SSH key。」，排除會導致「開放22到internet並把private key傳給所有人，或批次command沒有rate/error control。」的選項，再選「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAP-2.1 Design a deployment strategy to meet business requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「使用SSM Agent、Session Manager、Patch Manager、Run Command與Automation文件。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「prefer audited control channels over direct host access」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 76 章　Event-driven Remediation

設定偏移與安全事件若只靠人工ticket，修復時間長且結果不一致。

## 跟著一次變更走到production：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：有人開放S3 public access，要求數分鐘內封鎖並保留完整證據。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：設定偏移與安全事件若只靠人工ticket，修復時間長且結果不一致。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Config如何接手工作，再看Amazon EventBridge何時更合適，最後用設定與考題驗證「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：有人開放S3 public access，要求數分鐘內封鎖並保留完整證據。

正常production路徑
          ▼
[AWS Config] → 使用者可觀察的結果
          │ 記錄AWS resource configuration history並評估rules/conformance …
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon EventBridge：以event bus路由AWS、SaaS與custom events到targets。
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。
  · AWS Systems Manager：集中管理EC2與hybrid managed nodes的inventory、run commands、p…

失敗時先找：Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS Config有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Config和Amazon EventBridge並不是兩個任意的產品名稱。前者適合本章，是因為「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」直接回應了眼前的問題；後者描述的「高風險動作需approval與dry-run，避免自動化誤刪合法例外。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「automate known-safe responses, escalate ambiguous ones」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 |

## 把全圖套進一個具體案例

**場景：** 有人開放S3 public access，要求數分鐘內封鎖並保留完整證據。

1. 故事的起點：有人開放S3 public access，要求數分鐘內封鎖並保留完整證據。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Config負責「記錄AWS resource configuration history並評估rules/conformance packs。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EventBridge、AWS Lambda、AWS Systems Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Config

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：設定偏移與安全事件若只靠人工ticket，修復時間長且結果不一致。
- **具體例子／邊界：** 在「有人開放S3 public access，要求數分鐘內封鎖並保留完整證據。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EventBridge

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：高風險動作需approval與dry-run，避免自動化誤刪合法例外。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：automate known-safe responses, escalate ambiguous ones。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### IaC

Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### AWS Config

- **功用：** 記錄AWS resource configuration history並評估rules/conformance packs。
- **底層機制：** Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。
- **關鍵設定：** recorder、delivery channel、managed/custom rules、conformance packs、aggregator與remediation。
- **選擇時機：** 回答「資源何時變成這樣」、組態合規與多帳號inventory。
- **替換時機：** 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。

### Amazon EventBridge

- **功用：** 以event bus路由AWS、SaaS與custom events到targets。
- **底層機制：** Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。
- **關鍵設定：** event buses、rules/patterns、targets、input transformer、archive/replay、DLQ與resource policy。
- **選擇時機：** domain events、cross-account integration、content-based routing與scheduler。
- **替換時機：** 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

### AWS Systems Manager

- **功用：** 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。
- **底層機制：** SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。
- **關鍵設定：** managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
- **選擇時機：** fleet operations、patch、secure access、runbook與remediation。
- **替換時機：** container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。

## 考前與實作時再查：設定操作手冊

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

1. AWS Config的責任：記錄AWS resource configuration history並評估rules/conformance packs。
2. 底層機制：Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。
3. 第一個要看的設定：recorder、delivery channel、managed/custom rules、conformance packs、aggregator與remediation。
4. 選擇邏輯：Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。
5. 不要混淆：Amazon EventBridge的責任是「以event bus路由AWS、SaaS與custom events到targets。」；它不會自動取代AWS Config。
6. 替換訊號：回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。
7. 最常見錯法：Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。
8. 可移植原則：automate known-safe responses, escalate ambiguous ones。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Config | 記錄AWS resource configuration history並評估rules/conformance packs。 | Configuration recorder擷取changes，rules在變更或週期時評估COMPLIANT/NON_COMPLIANT。 | 回答「資源何時變成這樣」、組態合規與多帳號inventory。 | 回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 | domain events、cross-account integration、content-based routing與scheduler。 | 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 | fleet operations、patch、secure access、runbook與remediation。 | container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 高風險動作需approval與dry-run，避免自動化誤刪合法例外。 | 只有當題目條件明確改變時才可能合理。 | Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「高風險動作需approval與dry-run，避免自動化誤刪合法例外。」之間做選擇。
- 認得常考設定：recorder、delivery channel、managed/custom rules、conformance packs、aggregator與remediation。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：回答「誰呼叫API」用CloudTrail；runtime health用CloudWatch。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜preventive S3 public-access control

公司政策要求所有一般 workload accounts 的 S3 public access 在 API 層就不可成立；少數網站例外必須位於獨立受治理帳號。哪個主要控制最符合，且仍保留事後證據？

A. 只用 Config rule，因 NON_COMPLIANT evaluation 會同步阻止原始 API request
B. 在適當的 organization/account boundary 啟用 S3 Block Public Access 並搭配 policy guardrails；用 Config 與 CloudTrail 做合規、變更 attribution 與例外監控
C. 只開 CloudTrail，因它會自動拒絕 PutBucketPolicy
D. 依賴每日執行一次的 Config rule，讓 bucket 最多公開 24 小時

**答案：B**

- **A：** 錯誤。Config 是 detective/evaluation service，不是 PutBucketPolicy 的同步 admission controller。
- **B：** 正確。Block Public Access 在最強適用 boundary 阻擋不安全配置；Config/CloudTrail 則補充 state 與 actor evidence。
- **C：** 錯誤。CloudTrail 記錄 API activity，但本身不是 authorization deny control。
- **D：** 錯誤。Detect-and-repair 留有曝露窗口，無法滿足「不可成立」的 preventive requirement。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Block public access to S3 storage](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)、[Evaluate resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)、[CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)

### 練習題 2｜SAA｜AWS Config recorder scope

中央 dashboard 顯示 organization 內資源都 compliant，但後來發現某 Region 的新 resource type 從未有 configuration history。團隊只在主 Region 建立 aggregator 與 rules。哪個修正最重要？

A. 建立更多 CloudWatch dashboards，因 dashboard 會啟動 Config recorder
B. 在每個必要 account/Region 正確啟用 recorder 與 delivery，明確選擇 recording scope，並確認 rules 支援該 resource type；aggregator 只彙總來源資料
C. 只在 management account 啟用一個 rule，它會同步評估所有 regional member resources
D. Aggregator 會回填所有未記錄歷史，只需等待 24 小時

**答案：B**

- **A：** 錯誤。CloudWatch dashboard 與 Config recorder 是不同服務與 data source。
- **B：** 正確。完整性先取決於 source recording scope，再由 aggregator 提供中央查詢視圖。
- **C：** 錯誤。Organization governance 仍需把 recorder/rules 或 conformance packs 部署到正確 accounts/Regions。
- **D：** 錯誤。Aggregator 不會產生 source account/Region 從未記錄的 configuration items。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)、[Evaluate resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)、[Aggregate AWS Config data](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)

### 練習題 3｜SAA｜change-triggered 與 periodic Config evaluation

Security group ingress 變更會產生受支援的 configuration item；另一個控制要每小時查詢外部核准清單，單靠 resource configuration change 不會觸發。應如何配置 rules？

A. 兩者都 change-triggered，外部清單更新會自動變成 AWS resource configuration item
B. Security group rule 用 change-triggered evaluation；外部條件用 periodic evaluation，頻率依偵測目標設定，且兩者都不宣稱同步阻擋 API
C. 兩者都只能 periodic，因 Config 不支援 resource-change trigger
D. 使用 periodic rule 即可在 API request 完成前拒絕不合規變更

**答案：B**

- **A：** 錯誤。外部清單改變不一定會產生目標 AWS resource 的 configuration-item change。
- **B：** 正確。Trigger 應由可觀察事實決定；resource configuration change 與外部時間性條件需要不同評估模型。
- **C：** 錯誤。Config rules 可依 recorded configuration changes 觸發。
- **D：** 錯誤。Periodic evaluation 發生在變更後，不是同步 preventive gate。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Evaluate resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)

### 練習題 4｜SAP｜CloudTrail、Config 與 CloudWatch evidence boundary

事故調查要回答三件事：誰把 RDS instance class 改小、resource 變更前後的 configuration 是什麼、顧客付款成功率是否下降。哪個資料來源組合最正確？

A. 只用 CloudTrail，因 API event 會保存所有 business transactions 與 resource timeline
B. 只用 CloudWatch，因 metrics 會自動包含完整 old/new IAM policy documents
C. CloudTrail 查 actor/request；Config 查 configuration history/compliance；CloudWatch 與 application telemetry 查 runtime/customer impact，再以時間與 resource IDs 關聯
D. 只用 Config，因它同時保存完整 IAM session intent 與 application latency

**答案：C**

- **A：** 錯誤。CloudTrail 提供 API activity，但不等於完整 configuration state 與 customer outcome。
- **B：** 錯誤。Metrics/logs 不會自動取代 API audit 與 resource configuration timeline。
- **C：** 正確。三種服務回答不同問題：who/what API、resource became what、workload performed how。
- **D：** 錯誤。Config 聚焦 resource configuration，不是完整 user intent 或 application health 記錄。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)、[Collect metrics, logs, and traces with the CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

### 練習題 5｜SAA｜EventBridge direct 與 CloudTrail-delivered events

團隊要在某 AWS service 的 job 狀態變成 FAILED 時立即觸發 remediation；另一條規則要在有人呼叫特定 Delete API 時連同 actor 欄位通知。應採哪個 event source 原則？

A. 建立一個匹配所有 API calls 的超寬 pattern，再由 target 猜測是哪種事件
B. 用 Config aggregator，因它會即時路由任何 service state change 與 API event
C. Job state 優先用該服務直接發出的 EventBridge event；API actor/action 用 EventBridge 上 CloudTrail-delivered event，並以實際 schema 測試 pattern
D. 所有 AWS events 都必須等 CloudTrail log files 寫入 S3 後才能進 EventBridge

**答案：C**

- **A：** 錯誤。過寬 pattern 增加誤觸發、成本與 remediation 風險；應在 routing boundary 精確篩選。
- **B：** 錯誤。Aggregator 是 Config compliance/configuration 彙總，不是通用 event router。
- **C：** 正確。選擇原生 state event 或 CloudTrail API event 應由所需語意與欄位決定，不能假設 envelope 相同。
- **D：** 錯誤。許多服務直接向 EventBridge 發送 state-change events，不需經 CloudTrail log-file delivery。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS service events reference for EventBridge](https://docs.aws.amazon.com/eventbridge/latest/ref/events.html)、[CloudTrail-delivered AWS service events in EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail.html)、[CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)

### 練習題 6｜SAP｜Config automatic remediation 與 stale evaluation

Config rule 偵測 security group 開放 SSH 後要自動移除 rule；但在 remediation 排隊期間，owner 可能已合法修改 resource。如何降低 stale evaluation 造成誤改？

A. 使用 least-privilege SSM Automation，執行前重新讀取目前 rule 與 exception state，讓步驟 idempotent，限制 retries 並保存結果
B. 給 Automation role AdministratorAccess，避免 precondition 阻擋修復
C. 對任何失敗無限 retry，直到 resource 被刪除
D. 假設 NON_COMPLIANT snapshot 永遠 strongly consistent，直接重複執行 revoke

**答案：A**

- **A：** 正確。Re-read、precondition、idempotency、bounded retry 與 evidence 共同把 detective state 安全轉成 mutation。
- **B：** 錯誤。擴大權限不能修復 stale-state 問題，反而放大 automation blast radius。
- **C：** 錯誤。無界 destructive retries 會放大錯誤，且可能與 owner/IaC 形成 remediation loop。
- **D：** 錯誤。Config 自動修復可能依先前 evaluation 啟動，current state 必須在 mutation 前重新確認。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Remediate noncompliant resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/remediation.html)、[Set up automatic remediation](https://docs.aws.amazon.com/config/latest/developerguide/setup-autoremediation.html)、[AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)

### 練習題 7｜SAP｜human approval boundary

EventBridge 偵測 production database 的 encryption setting 異常。自動 replacement 可能造成數小時中斷，而 CMDB 顯示某些 databases 有短期核准例外。哪個 response design 最適合？

A. 所有 security finding 都立即刪除並重建 resource，不論可逆性與 business impact
B. 所有低風險 deterministic fixes 也一律等待每月 change board
C. 只看 resource name 決定是否修復，因 dependency 與 owner 不影響 replacement
D. 收集 current state、dependency 與 exception evidence，先 dry-run/precondition；由 accountable approver 在期限內決定，逾時 escalation，保留完整 decision trail

**答案：D**

- **A：** 錯誤。無條件 destructive action 可能造成比原 finding 更大的 outage 或 data risk。
- **B：** 錯誤。Approval boundary 應按 ambiguity 與 impact；已知安全且可逆的 correction 可全自動化。
- **C：** 錯誤。Production remediation 必須理解 dependencies、exception、owner 與 recovery path。
- **D：** 正確。高影響、情境依賴的 remediation 應保留人工 decision point；自動化仍可完成證據蒐集、時限與執行。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)、[Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)、[OPS10-BP01 Use a process for event, incident, and problem management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html)

### 練習題 8｜SAA｜EventBridge retry、DLQ 與 idempotency

同一個 resource-change event 可能被 retry 或重複投遞；偶發 target failure 也不得讓修復靜默消失。哪個 target design 最可靠？

A. 在 Lambda 記憶體放一個 processed flag，跨 cold start 永久去重
B. 依賴 EventBridge exactly-once delivery，target 不需讀 current state
C. Target 每次先讀 authoritative current state 並執行 idempotent transition；設定 bounded retry/maximum age、same-Region SQS standard DLQ、必要 queue policy、alarms 與受控 replay
D. 停用 retries，這樣就不會發生 duplicate mutation

**答案：C**

- **A：** 錯誤。Lambda execution environment 不具 durable uniqueness contract，並行與 cold start 都會失效。
- **B：** 錯誤。事件系統與 target retry 需按 at-least-once/duplicate possibility 設計，而不能假設 exactly once。
- **C：** 正確。Idempotent current-state transition 防止重複副作用。Classic EventBridge rule target 的 DLQ 必須是與 rule/event bus 同 Region 的 SQS standard queue，不能使用 FIFO queue；queue policy 也必須允許 events.amazonaws.com 執行 SendMessage。DLQ、alarm 與 replay 流程共同防止靜默遺失。
- **D：** 錯誤。停用 retry 會把暫時故障轉成 lost remediation。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Retry policies for EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)、[Dead-letter queues for EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-dlq.html)、[AWS Lambda best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

### 練習題 9｜SAP｜remediation loop 與 exception governance

Automation 每五分鐘把 security group 改回安全設定，但 application pipeline 隨後又加回違規 rule，形成持續 loop；另有一個已核准到月底的例外。哪些 TWO 改善最重要？

A. 停止評估整個 security-group resource type，避免 dashboard 變紅
B. 把例外寫成沒有 owner、原因或 expiration 的永久 free-text tag
C. 將例外建模為有 scope、owner、理由與到期日的資料，修復前重新驗證；到期後恢復 enforcement
D. 只把 EventBridge maximum event age 與 retry attempts 調高，讓同一 remediation 更久地重試，但不修改 pipeline 或 authoritative IaC
E. 偵測重複 oscillation，限制 retries/changes，通知 authoritative IaC owner 並修正 pipeline/template 根因

**答案：C、E**

- **A：** 錯誤。關閉整類 control 會隱藏其他真實 violations。
- **B：** 錯誤。無 owner、reason、scope 與 expiration 的永久文字例外無法自動到期、稽核或精確匹配；若建立結構化例外資料與審批生命週期，才可成為有效 policy input。
- **C：** 正確。Exception 也是 policy data，必須具備 owner 與 expiry，才能兼顧合法變更與恢復 default enforcement。
- **D：** 錯誤。提高可設定的 event age 或 retry attempts 只能延長投遞與重試時間，無法消除 pipeline 持續寫回違規設定的根因；反而可能增加 API、成本與 remediation oscillation。
- **E：** 正確。Runtime remediation 不應永遠與 source of truth 對打；需修正上游 IaC/workflow 並限制變更風暴。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Set up automatic remediation](https://docs.aws.amazon.com/config/latest/developerguide/setup-autoremediation.html)、[Retry policies for EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)、[Detect unmanaged configuration changes with drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)、[OPS11-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html)

### 練習題 10｜SAP｜organization conformance pack、aggregator 與 remediation authority

中央 security team 要把共同 Config controls 部署到 80 個 accounts/Regions 並集中查看 compliance；member teams 仍保有範圍受限的 remediation responsibility。哪些 TWO 架構敘述正確？

A. 只在 management account 建立 rules，即可評估所有 member accounts 的 regional resources
B. Config aggregator 會以中央角色自動修復所有 source accounts 的 resources
C. 用 organization conformance packs 在所需 accounts/Regions 部署共同 rules/remediation definitions，並明確設定 delivery/execution roles
D. 用 aggregator 彙總 configuration/compliance view；它是 read-oriented consolidation，不取代 source recorder、rule 或 remediation authority
E. 因 controls 是 organization-wide，中央 remediation role 應無條件取得所有服務 AdministratorAccess

**答案：C、D**

- **A：** 錯誤。Regional source resources 需要相應的 recorder/evaluation deployment，不能只靠 management account 單點 rule。
- **B：** 錯誤。Aggregator 集中資料與查詢，不是跨帳號 enforcement engine。
- **C：** 正確。Conformance pack 可標準化 rule/remediation definitions，但仍需在正確 scope 部署並給執行角色最小權限。
- **D：** 正確。中央 visibility 與 distributed remediation 是可分離的責任；aggregator 只完成前者。
- **E：** 錯誤。Organization scope 不代表 execution role 可忽略 least privilege 與 member ownership。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Deploy organization conformance packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-pack-organization-apis.html)、[Aggregate AWS Config data](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)、[Remediate noncompliant resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/remediation.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「設定偏移與安全事件若只靠人工ticket，修復時間長且結果不一致。」，所以「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」能直接滿足它；若constraint改成「高風險動作需approval與dry-run，避免自動化誤刪合法例外。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」。替代方案「高風險動作需approval與dry-run，避免自動化誤刪合法例外。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「設定偏移與安全事件若只靠人工ticket，修復時間長且結果不一致。」，排除會導致「Remediation形成loop反覆改回資源，卻沒有找出上游IaC或owner。」的選項，再選「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Config/CloudTrail/EventBridge觸發Lambda或SSM Automation，先評估risk再修復並通知。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「automate known-safe responses, escalate ambiguous ones」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 77 章　Backup、Restore Testing 與 Game Day

備份存在不代表應用能在目標時間恢復，依賴、權限與runbook都可能失效。

## 跟著一次變更走到production：先從故事開始

把鏡頭拉到一個真實的production現場：稽核要求證明每季可從跨帳號vault恢復完整付款流程。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：備份存在不代表應用能在目標時間恢復，依賴、權限與runbook都可能失效。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。 恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。AWS Backup是這一章的入口，AWS Fault Injection Service用來畫出邊界；主要方向「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：稽核要求證明每季可從跨帳號vault恢復完整付款流程。

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
  · AWS Fault Injection Service：以受控實驗注入AWS resource failures驗證resilience。
  · AWS Resilience Hub：定義application resilience policy並評估components是否滿足RTO/R…

失敗時先找：只測database restore，忽略application version、KMS key與event replay。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和AWS Fault Injection Service並不是兩個任意的產品名稱。前者適合本章，是因為「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」直接回應了眼前的問題；後者描述的「Game day可測failover與人員流程，但需guardrails和停止條件。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只測database restore，忽略application version、KMS key與event replay。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「reliability claims require exercised evidence」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| AWS Fault Injection Service | 以受控實驗注入AWS resource failures驗證resilience。 | Experiment template選targets/actions/stop conditions，service role執行故障並由CloudWatch alarm中止。 |
| AWS Resilience Hub | 定義application resilience policy並評估components是否滿足RTO/RPO。 | 匯入app resources與relationships，套policy分析故障與提出recommendations，可整合FIS/SOP。 |

## 把全圖套進一個具體案例

**場景：** 稽核要求證明每季可從跨帳號vault恢復完整付款流程。

1. 故事的起點：稽核要求證明每季可從跨帳號vault恢復完整付款流程。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Fault Injection Service、AWS Resilience Hub各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只測database restore，忽略application version、KMS key與event replay。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：備份存在不代表應用能在目標時間恢復，依賴、權限與runbook都可能失效。
- **具體例子／邊界：** 在「稽核要求證明每季可從跨帳號vault恢復完整付款流程。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Fault Injection Service

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Game day可測failover與人員流程，但需guardrails和停止條件。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只測database restore，忽略application version、KMS key與event replay。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：reliability claims require exercised evidence。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### portfolio

待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

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

### AWS Fault Injection Service

- **功用：** 以受控實驗注入AWS resource failures驗證resilience。
- **底層機制：** Experiment template選targets/actions/stop conditions，service role執行故障並由CloudWatch alarm中止。
- **關鍵設定：** targets/tags、actions、duration、stop conditions、IAM role、experiment report與safety limits。
- **選擇時機：** game day、驗證AZ/instance/network failure、alarm與recovery automation。
- **替換時機：** 不能替代load test或backup restore；先縮小blast radius並設stop conditions。

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

### AWS Fault Injection Service：逐項設定說明

#### `targets/tags`

- **控制什麼：** `targets/tags`指定AWS Fault Injection Service讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `actions`

- **控制什麼：** FIS actions是實驗要注入的故障，例如stop instances、增加CPU壓力、network disruption或API throttle。
- **何時需要：** 需要驗證autoscaling、failover、alarm與runbook是否真的能承受特定failure mode時。
- **怎麼設定／驗證：** 選擇具體action ID、targets、parameters與duration，設定stop conditions與最小IAM role，先在小scope執行。
- **常見錯法：** 沒有stop condition或tag-scoped targets可能影響production大範圍；故障實驗不能用來首次發現沒有backup。

#### `duration`

- **控制什麼：** `duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「game day、驗證AZ/instance/network failure、alarm與recovery automation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Fault Injection Service的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `stop conditions`

- **控制什麼：** `stop conditions`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「game day、驗證AZ/instance/network failure、alarm與recovery automation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fault Injection Service設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `IAM role`

- **控制什麼：** `IAM role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「game day、驗證AZ/instance/network failure、alarm與recovery automation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fault Injection Service明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `experiment report`

- **控制什麼：** `experiment report`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「game day、驗證AZ/instance/network failure、alarm與recovery automation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fault Injection Service的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `safety limits`

- **控制什麼：** `safety limits`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「game day、驗證AZ/instance/network failure、alarm與recovery automation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fault Injection Service設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
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
4. 選擇邏輯：定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。
5. 不要混淆：AWS Fault Injection Service的責任是「以受控實驗注入AWS resource failures驗證resilience。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：只測database restore，忽略application version、KMS key與event replay。
8. 可移植原則：reliability claims require exercised evidence。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| AWS Fault Injection Service | 以受控實驗注入AWS resource failures驗證resilience。 | Experiment template選targets/actions/stop conditions，service role執行故障並由CloudWatch alarm中止。 | game day、驗證AZ/instance/network failure、alarm與recovery automation。 | 不能替代load test或backup restore；先縮小blast radius並設stop conditions。 |
| AWS Resilience Hub | 定義application resilience policy並評估components是否滿足RTO/RPO。 | 匯入app resources與relationships，套policy分析故障與提出recommendations，可整合FIS/SOP。 | portfolio resilience posture、gap analysis與持續驗證。 | 它不替你執行所有failover；實作仍在服務配置、runbook與game day。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Game day可測failover與人員流程，但需guardrails和停止條件。 | 只有當題目條件明確改變時才可能合理。 | 只測database restore，忽略application version、KMS key與event replay。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Game day可測failover與人員流程，但需guardrails和停止條件。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-2.2 Design a solution to ensure business continuity；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜RPO、backup windows 與 retention

訂單資料的 RPO 是 4 小時，法規 retention 是 7 年。現行 backup rule 每四小時排程，但多次因 start window 過期而未執行；團隊仍宣稱 RPO 已達成。應如何修正判斷與設定？

A. 把 completion window 設為零，讓所有 jobs 立即完成
B. 只要 schedule 寫每四小時，即使 job 未開始也算符合 RPO
C. 依 RPO 設 frequency 與 start/completion windows，依法規設 lifecycle/retention；監控成功 jobs 與 latest usable recovery point age
D. 把 retention 設七年即可同時保證四小時 RPO 與快速 restore

**答案：C**

- **A：** 錯誤。Window 是 job scheduling/operation constraint，不會讓服務瞬間建立 backup。
- **B：** 錯誤。Configured intention 不是 achieved recovery point；missed/failed jobs 會讓實際 data-loss window 變大。
- **C：** 正確。Frequency/window 決定 recovery points 能否形成，retention 決定保存多久；兩者都需以 job evidence 驗證。
- **D：** 錯誤。Retention 不決定 recovery-point frequency，也不等同 RTO。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[AWS Backup plans](https://docs.aws.amazon.com/aws-backup/latest/devguide/about-backup-plans.html)

### 練習題 2｜SAP｜backup vault、KMS 與 restore authority

Recovery account 的團隊能看到 workload account 複製來的 recovery point，也有 vault restore permission，但 restore 仍因 KMS 拒絕。原 workload admin 被視為可能遭入侵。最佳修正是什麼？

A. 使用唯一可能遭入侵的 workload role 作為 recovery principal
B. 依 resource backup 的 encryption model 設計可跨帳號使用的 key/policies、vault policy 與獨立 restore role，並在 recovery account 端實際測試
C. 任何 AWS managed KMS key 都可跨帳號直接解密，應重試即可
D. Vault access policy 已隱含所有 KMS decrypt permissions

**答案：B**

- **A：** 錯誤。Recovery path 不應只依賴可能被撤銷或破壞的原 workload identity。
- **B：** 正確。可恢復性必須把 recovery point、vault、KMS key 與 restore role 當成一條端到端 authorization path 驗證。
- **C：** 錯誤。跨帳號與服務特定 encryption 行為需要支援的 key 類型與明確授權。
- **D：** 錯誤。Vault authorization 與 KMS key authorization 是不同 control planes，兩者都要通過。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Encryption for backups in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/encryption.html)、[Restore a backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-a-backup.html)、[Create backup copies across AWS accounts](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)

### 練習題 3｜SAA｜cross-account cross-Region backup copy

公司希望 backup 同時承受 source-account compromise 與整個 Region disruption。架構師不能假設所有 resource types 支援相同 copy path。應採取哪個做法？

A. 先做 cross-Region copy，再假設它可無限次 transitive copy 到任意帳號
B. 逐 resource/backup type 驗證 cross-account/cross-Region 支援，設定 organization trust、destination vault/KMS、copy retention，並在 destination 實測 restore
C. 把任何 cross-Region replica 視為已具 WORM 的 cross-account backup
D. 只建立 source vault policy；destination KMS 與 restore role 會自動推導

**答案：B**

- **A：** 錯誤。Copy 組合與後續 copy 能力不可假設普遍或 transitive。
- **B：** 正確。Copy support、key requirements 與 restore metadata 都可能依服務而異，必須從 source 到 destination 完整驗證。
- **C：** 錯誤。Replication 與 immutable backup 是不同 resilience/control contract。
- **D：** 錯誤。Destination vault/key 與 principals 仍需明確授權。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Create backup copies across AWS accounts](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[Encryption for backups in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/encryption.html)

### 練習題 4｜SAA｜Backup Vault Lock modes 與能力邊界

法規要求 recovery points 在 retention 期間不可被高權限管理員縮短或刪除。團隊也希望先有測試期，避免錯誤 policy 永久鎖死資料。哪個敘述最準確？

A. Compliance mode 的 lock date 後仍可由 root user 任意縮短 retention
B. 建立 compliance-mode Vault Lock，設定 3 至 36,500 天的 ChangeableForDays grace time 來驗證 min/max retention 與流程；grace time 到期後進入不可變狀態
C. Vault Lock 會自動把每個 recovery point 複製到隔離帳號
D. Vault Lock 會自動還原並驗證 application，因此不需要 restore test

**答案：B**

- **A：** 錯誤。Compliance mode 的目的正是提供不可由一般高權限甚至帳號管理權限任意解除的 WORM 保護。
- **B：** 正確。Compliance mode 的 ChangeableForDays 會建立 3 至 36,500 天的 grace time，期間仍可調整或移除 lock；lock date 後 vault lock 與受保護 recovery points 進入不可變狀態。Governance mode 仍可由具適當 IAM 權限者移除，因此不符合最終 WORM 硬需求。KMS、restore authorization 與 recoverability tests 仍須另行管理。
- **C：** 錯誤。Cross-account copy 必須由 backup/copy plan 與 destination policies 另外設定。
- **D：** 錯誤。Vault Lock 保護 recovery point retention，不證明資料或應用可成功恢復。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)

### 練習題 5｜SAA｜AWS Backup restore testing plan

稽核要求每月從過去 24 小時內的合格 recovery points，自動選取 RDS 與 EBS backup 還原到測試環境，記錄 restore duration；不能每次由操作員手選。應使用什麼？

A. 只建立 backup plan；每個 backup rule 都會自動產生 application restore test
B. 只選最新 recovery point 測一次，便可證明所有七年 retained points 都可用
C. 使用 FIS 停止 production database，視為 backup restore test
D. 建立 restore testing plan 與 resource selections，設定 frequency、recovery-point age、restore role/metadata，並監控 restore jobs

**答案：D**

- **A：** 錯誤。Backup creation plan 與 restore testing plan 是不同資源與工作流程。
- **B：** 錯誤。單一 recovery point 的結果不能證明所有歷史點都可讀，選樣與風險需另行設計。
- **C：** 錯誤。Fault injection 可測 failover/response，但不會證明 backup 可解密、還原與驗證。
- **D：** 正確。Restore testing 能依 schedule 與 selection 自動選 recovery points 並建立 resource-level restore evidence。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Restore testing in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Restore a backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-a-backup.html)

### 練習題 6｜SAP｜restore validation workflow

AWS Backup restore testing job 顯示 COMPLETED，但測試資料庫缺少必要資料，API 也無法完成 checkout。如何讓 restore testing evidence 反映業務可用性？

A. 以 EventBridge 接收 restore-job completion，啟動明確 validation workflow 檢查資料與 application invariants，在時限內回報 validation result 並保存 logs
B. COMPLETED 已等同 business transaction success，不需額外步驟
C. 只要 validator Lambda 執行成功，AWS Backup 會自動推斷 validation outcome
D. 在 restore resource 可用前先執行所有 SQL validation

**答案：A**

- **A：** 正確。Event-driven validation 把 resource restore evidence 提升為 data/application evidence，且讓失敗可追蹤。
- **B：** 錯誤。Resource API restore complete 只證明基礎資源形成，不保證內容與 end-to-end use case。
- **C：** 錯誤。Workflow 必須明確回報 validation status；function execution success 不等同 invariant pass。
- **D：** 錯誤。驗證必須等待 restored resource 到可讀/可連線狀態，並處理 dependencies。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Validate restore testing jobs](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)、[Restore testing in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[AWS service events reference for EventBridge](https://docs.aws.amazon.com/eventbridge/latest/ref/events.html)

### 練習題 7｜SAA｜isolated restore testing 與 cleanup

每月 restore test 含敏感 customer data。測試不得覆寫 production、加入 production DNS、讓一般 developers 取得完整資料，或無限留下昂貴 resources。哪個設計最佳？

A. 直接 restore over production，這最能證明真實性
B. 還原到隔離 account/VPC，以 scoped role 與必要 masking 控制 access；使用唯一命名與測試 dependencies，並驗證 validation 後 cleanup
C. 假設 restore job 一變 COMPLETED，所有 services 都會立刻自動刪除 restored resources
D. 給 validator production AdministratorAccess，避免任何 permission failure

**答案：B**

- **A：** 錯誤。覆寫 production 將測試轉成真實破壞性事件，並違反隔離要求。
- **B：** 正確。Isolation 同時控制 collision、data exposure 與 blast radius；cleanup 也必須被觀察，而非只假設。
- **C：** 錯誤。Restore-testing cleanup 行為與時機依服務/validation window 而異，需明確監控與驗證。
- **D：** 錯誤。應只授權 validation 所需 actions/resources，不能用過度權限掩蓋依賴設計問題。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[Restore testing in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[Validate restore testing jobs](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)

### 練習題 8｜SAP｜application RTO 與 usable recovery

Database restore 在 18 分鐘完成，但 DNS、secrets、application capacity 與 event replay 尚未恢復，直到第 74 分鐘第一筆付款才成功。Business RTO 是 60 分鐘。應如何報告？

A. RTO 是 18 分鐘，因最重要的 database 已完成
B. 實際 end-to-end RTO 是 74 分鐘，未達目標；另記 effective recovery point、依賴順序、validation 與 event reconciliation 的改善項目
C. RTO 在 CloudFormation 建完 compute 時停止，不必等待 traffic
D. 只要 backup job 成功，RTO 不需測量

**答案：B**

- **A：** 錯誤。Resource restore time 只是 application recovery timeline 的一部分。
- **B：** 正確。RTO 應從中斷/宣告到受要求服務恢復；題目證據是第 74 分鐘，因此需如實記錄 gap。
- **C：** 錯誤。Infrastructure ready 不等同 critical business transaction usable。
- **D：** 錯誤。Backup success 是保護 evidence，不是 recovery-duration evidence。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Restore a backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-a-backup.html)、[Validate restore testing jobs](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)、[What is AWS Resilience Hub?](https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html)

### 練習題 9｜SAP｜guarded game day 與 FIS stop conditions

自動 restore test 已通過，但公司還要驗證 on-call 是否能偵測 Regional dependency failure、決定 failover、溝通並完成 failback。哪些 TWO 做法符合安全 game day？

A. 用 FIS 取代所有 backup restores，因 fault injection 能證明 data 可還原
B. 在 production 執行無界 experiment，不設定 CloudWatch stop conditions
C. 先定義 hypothesis、scope、steady-state/customer metrics、owners、runbook、communications、rollback 與 cleanup
D. 只做會議 tabletop 就宣稱技術 failover 與 DNS 已驗證
E. 使用受支援且範圍受限的 FIS actions/targets，設定 CloudWatch stop conditions；量測 failover/failback 並做事後改進

**答案：C、E**

- **A：** 錯誤。FIS 驗證 failure response；backup decrypt/restore/data validation 仍需真正 restore test。
- **B：** 錯誤。沒有 stop condition 與 bounded target 會把學習實驗變成未控制的 outage。
- **C：** 正確。Game day 是有假設與 guardrails 的實驗，不是臨時製造事故。
- **D：** 錯誤。Tabletop 可驗證角色與決策，但不能證明實際 data plane、routing 與 automation。
- **E：** 正確。FIS 的 target/action/stop-condition contract 可控制 blast radius，並產生可重複技術 evidence。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[What is AWS Fault Injection Service?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)、[Stop conditions for AWS Fault Injection Service](https://docs.aws.amazon.com/fis/latest/userguide/stop-conditions.html)、[Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)

### 練習題 10｜SAP｜backup audit evidence 與 corrective action

稽核員要求證明所有應保護 resources 已納入、backup jobs 成功、retention/immutability 正確、restore validation 通過，而且失敗有 owner。哪些 TWO 做法最完整？

A. Audit control 顯示 compliant 就宣稱所有 business transactions 已成功還原
B. Restore test 失敗後只重跑報告；新報告生成即關閉問題
C. 保存 restore/validation logs、exceptions 的 owner/expiry 與 remediation status，追蹤失敗直到修正並重測
D. 只列成功 jobs，未被 backup plan 選中的 resources 不在報告範圍
E. 用 AWS Backup Audit Manager controls/reports，並與 authoritative inventory 對照 coverage、vault 與 job evidence

**答案：C、E**

- **A：** 錯誤。Policy/job compliance 不等同 application-level restore validation。
- **B：** 錯誤。重新產生報告不會修正失敗的 key、role、metadata 或 application dependency。
- **C：** 正確。Durable evidence 必須包含 exceptions 與 failed-test corrective action，而不只是一張當下綠色報表。
- **D：** 錯誤。只看成功集合會產生 survivorship bias，無法發現完全未受保護的 resources。
- **E：** 正確。Audit Manager 提供可重複 controls/reports，但 coverage 仍應與外部 inventory/source of truth 對帳。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[AWS Backup Audit Manager](https://docs.aws.amazon.com/aws-backup/latest/devguide/aws-backup-audit-manager.html)、[Validate restore testing jobs](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)、[OPS11-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「備份存在不代表應用能在目標時間恢復，依賴、權限與runbook都可能失效。」，所以「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」能直接滿足它；若constraint改成「Game day可測failover與人員流程，但需guardrails和停止條件。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」。替代方案「Game day可測failover與人員流程，但需guardrails和停止條件。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只測database restore，忽略application version、KMS key與event replay。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「備份存在不代表應用能在目標時間恢復，依賴、權限與runbook都可能失效。」，排除會導致「只測database restore，忽略application version、KMS key與event replay。」的選項，再選「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.2 Design a solution to ensure business continuity；SAP-3.1 Determine a strategy to improve overall operational excellence。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「定期自動restore到隔離環境，驗證資料、RTO/RPO、DNS、secret與業務交易。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「reliability claims require exercised evidence」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 78 章　Operational Excellence 與 Continuous Improvement

架構不是一次性圖紙；runbook、指標、事件與改進backlog共同決定長期品質。

## 跟著一次變更走到production：先從故事開始

如果今天由你值班，收到的需求可能是這樣：快速成長團隊每週事故增加，alarms數百個但on-call不知道先處理什麼。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：架構不是一次性圖紙；runbook、指標、事件與改進backlog共同決定長期品質。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Well-Architected Tool承接主要責任，以Amazon CloudWatch檢查替代條件，並用「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：快速成長團隊每週事故增加，alarms數百個但on-call不知道先處理什麼。

正常production路徑
          ▼
[AWS Well-Architected Tool] → 使用者可觀察的結果
          │ 在AWS中記錄Well-Architected reviews、milestones與improvement pl…
          │
          ├─ telemetry偵測使用者影響
          ├─ health／alarm決定隔離或停止推出
          └─ recovery path執行replace／failover／rollback
演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證
成本：常駐容量、資料複製與營運工作都要被計入
本章其他角色：
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…
  · AWS Systems Manager：集中管理EC2與hybrid managed nodes的inventory、run commands、p…

失敗時先找：每次事故只增加更多alarm，造成noise而沒有移除根因。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次變更走到production」。先不要急著問AWS Well-Architected Tool有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Well-Architected Tool和Amazon CloudWatch並不是兩個任意的產品名稱。前者適合本章，是因為「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」直接回應了眼前的問題；後者描述的「Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每次事故只增加更多alarm，造成noise而沒有移除根因。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「operations is a feedback system, not a support phase」。更白話地說：每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 |

## 把全圖套進一個具體案例

**場景：** 快速成長團隊每週事故增加，alarms數百個但on-call不知道先處理什麼。

1. 故事的起點：快速成長團隊每週事故增加，alarms數百個但on-call不知道先處理什麼。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Well-Architected Tool負責「在AWS中記錄Well-Architected reviews、milestones與improvement plans。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon CloudWatch、AWS Systems Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每次事故只增加更多alarm，造成noise而沒有移除根因。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Well-Architected Tool

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：架構不是一次性圖紙；runbook、指標、事件與改進backlog共同決定長期品質。
- **具體例子／邊界：** 在「快速成長團隊每週事故增加，alarms數百個但on-call不知道先處理什麼。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon CloudWatch

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每次事故只增加更多alarm，造成noise而沒有移除根因。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：operations is a feedback system, not a support phase。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### managed service

供應商接手部分基礎設施責任的服務；customer仍負責資料、身份、設定、access pattern與business correctness。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

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

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### SLO

Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。

## 回到 AWS：Components、功用與責任邊界

### AWS Well-Architected Tool

- **功用：** 在AWS中記錄Well-Architected reviews、milestones與improvement plans。
- **底層機制：** Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
- **關鍵設定：** workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- **選擇時機：** 需要重複、可稽核的architecture review process。
- **替換時機：** 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

### AWS Systems Manager

- **功用：** 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。
- **底層機制：** SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。
- **關鍵設定：** managed instance role、VPC endpoints、documents、associations、inventory、maintenance windows與automation。
- **選擇時機：** fleet operations、patch、secure access、runbook與remediation。
- **替換時機：** container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。

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

1. AWS Well-Architected Tool的責任：在AWS中記錄Well-Architected reviews、milestones與improvement plans。
2. 底層機制：Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。
3. 第一個要看的設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
4. 選擇邏輯：定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。
5. 不要混淆：Amazon CloudWatch的責任是「收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。」；它不會自動取代AWS Well-Architected Tool。
6. 替換訊號：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
7. 最常見錯法：每次事故只增加更多alarm，造成noise而沒有移除根因。
8. 可移植原則：operations is a feedback system, not a support phase。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Well-Architected Tool | 在AWS中記錄Well-Architected reviews、milestones與improvement plans。 | Workload套用lenses回答questions，工具標示high/medium risk並追蹤改進。 | 需要重複、可稽核的architecture review process。 | 工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| AWS Systems Manager | 集中管理EC2與hybrid managed nodes的inventory、run commands、patch與automation。 | SSM Agent透過IAM與service endpoints輪詢control plane，通常不需開inbound SSH。 | fleet operations、patch、secure access、runbook與remediation。 | container orchestration用ECS/EKS；純configuration storage是Parameter Store子功能。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。 | 只有當題目條件明確改變時才可能合理。 | 每次事故只增加更多alarm，造成noise而沒有移除根因。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。」之間做選擇。
- 認得常考設定：workload、Regions、lenses、milestones、profiles、sharing與improvement items。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：工具輸出依賴輸入品質；仍需metrics、tests與domain experts驗證。
- 對應官方tasks：SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability；SAP-3.5 Identify opportunities for cost optimizations。

## 本章 10 題考題

### 練習題 1｜SAP｜production operational ownership

三個 teams 共同開發 checkout service，但半夜 alarm 只送到沒有 owner 的聊天頻道；依賴廠商、business 溝通與 production rollback 也沒有人有最終決策權。上線前最重要的改善是什麼？

A. 把 alarm 數量加倍，讓任何 team 都可能看到
B. 定義 service owner、24x7 on-call、dependency contacts、escalation、技術/業務 decision authority 與 stakeholder communication responsibilities
C. 把所有 teams 都列為同等 owner，不指定 incident decision maker
D. 購買 AWS Support，讓 AWS Support 成為 application 的主要 on-call owner

**答案：B**

- **A：** 錯誤。增加未擁有的 alerts 只會提高 noise，不會補上 decision authority。
- **B：** 正確。Operational ownership 必須在事件發生前清楚到人/角色、時段、權限與升級路徑。
- **C：** 錯誤。多人共同負責但無 accountable decision owner，事故時仍會產生衝突與延誤。
- **D：** 錯誤。AWS Support 可協助 AWS service 問題，但不承擔 workload business outcome、應用 rollback 或內部溝通責任。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-excellence.html)、[Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)

### 練習題 2｜SAA｜operations as code

不同值班工程師用各自 shell history 執行同一個 cache failover，步驟與驗證結果常不一致，也沒有 approval 或 execution logs。哪個改善最符合 operational excellence？

A. 先把不穩定步驟全部自動化，不定義 preconditions、stop criteria 或 rollback
B. 因不是 application code，所以 operational changes 不需 code review
C. 將 infrastructure/config/automation documents 與 observability 設定版本化、review、測試；以受控 pipeline/SSM Automation 執行並保存 approvals 與結果
D. 讓最資深工程師保留唯一可用的私人指令清單

**答案：C**

- **A：** 錯誤。Automation 會放大既有流程；先明確化安全邊界與驗證，再逐步自動化。
- **B：** 錯誤。Operational code 同樣能改變 production，風險不低於 application code。
- **C：** 正確。Operations as code 使例行變更可重現、可審查、可測與可追蹤。
- **D：** 錯誤。私人知識形成單點故障，無法建立一致執行、peer review 與稽核證據；只有在緊急探索階段可暫時使用，之後仍須沉澱成受控 runbook 或 automation。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-excellence.html)、[AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)、[CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)

### 練習題 3｜SAA｜metrics、logs、traces 與 correlation

Checkout p99 上升，但 CPU 正常。團隊要區分 application regression、database dependency latency 與 thread-pool saturation，且能由一筆 request 追到各服務。哪個 telemetry design 最好？

A. 從 workload questions 出發蒐集 customer/component metrics、structured logs 與 distributed traces，加入 request、service、environment 與 deployment correlation context
B. 只啟用 tracing，但不傳遞 trace context，也不標記 deployment revision
C. 只收集 host CPU，因 managed database 的 latency 最終一定會提高 EC2 CPU
D. 永久記錄所有未遮罩 payload，成本與 privacy 不需控制

**答案：A**

- **A：** 正確。Metrics 顯示趨勢，logs 提供事件細節，traces 顯示跨服務路徑；一致 context 才能把三者關聯。
- **B：** 錯誤。沒有 context propagation 與 release metadata，trace 片段難以組成 causal path。
- **C：** 錯誤。下游 latency、lock 或 network 問題可能在 CPU 正常時造成 customer impact。
- **D：** 錯誤。Observability 仍需 retention、sensitivity、sampling 與成本治理。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)、[Collect metrics, logs, and traces with the CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

### 練習題 4｜SAP｜customer-facing indicators、SLO 與 alert priorities

公司有 420 個 infrastructure alarms，卻無法回答客戶能否成功付款。每次低 CPU、disk burst 或 queue 波動都 page，值班人員逐漸忽略通知。第一個結構性改善是什麼？

A. 以 instance availability 直接代表 payment success SLO
B. 事故後再依當天表現調整 SLO，確保報告達標
C. 定義付款成功率、latency 等 customer/business indicators 與 objectives，再把 component signals 連回這些結果，依可行動性與 objective risk 決定 page
D. 把所有 thresholds 再降低 20%，提早收到更多 alarms

**答案：C**

- **A：** 錯誤。Infrastructure up 不代表 dependency、應用邏輯或付款流程成功。
- **B：** 錯誤。Objective 應事先反映 business expectation，不能在事後為了綠色報表重寫。
- **C：** 正確。先定義使用者結果，才能決定哪些 telemetry 是 indicator、哪些偏差值得立即回應。
- **D：** 錯誤。更多未連結 customer impact 的 alarms 會加劇 alert fatigue。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)、[AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-excellence.html)

### 練習題 5｜SAP｜actionable alarm design

某 alarm 每晚固定進入 ALARM，但從未需要人類在當下採取動作；它沒有 owner、runbook、customer impact 或 escalation。應如何處理？

A. 重新定義有意義的 threshold/window/missing-data behavior，指派 owner 並連結診斷/response；若無即時行動就降級為 ticket/dashboard 或移除
B. 把 alarm 複製到更多 SNS topics，提高收到機率
C. 維持永久 ALARM，讓 dashboard 看起來資訊充足
D. 保留為最高嚴重度 page，因任何異常都應叫醒值班人員

**答案：A**

- **A：** 正確。Actionability、ownership、routing 與 response context 是 page contract；不符合者應改變通知層級。
- **B：** 錯誤。更多 notification destinations 不會建立可行動性、owner 或 response contract；只有原本 alarm 已具明確處置而需提高送達可靠性時，增加路由才有意義。
- **C：** 錯誤。永久噪音降低 dashboard 與 paging system 的信任度。
- **D：** 錯誤。Page 是要求立即行動的中斷，無 response 的 page 會訓練人員忽略真正事件。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Use Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)、[OPS10-BP02 Have a process per alert](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_process_per_alert.html)、[Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)

### 練習題 6｜SAP｜deployment/configuration correlation

Error rate 在 14:07 上升；14:00–14:06 間有 application、CloudFormation 與 runtime configuration 三種 releases。團隊現在只憑「最後一個 commit」猜測根因。哪個改善最有效？

A. 為每次 deploy/config change 保存 revision 與時間並標記 dashboards/events；把 metrics、logs、traces、CloudTrail、Config 前後狀態關聯後再決定 rollback 或 forward fix
B. 永遠 rollback 最新 commit，不看 metrics 或 dependency evidence
C. 成功後立即刪除 deployment markers，避免 dashboard 太複雜
D. 只查 CloudTrail，因 API history 能直接解釋每一筆 customer latency

**答案：A**

- **A：** 正確。統一 change context 與 pre/post evidence 能快速縮小 causal candidates，並支持可辯護的修復決策。
- **B：** 錯誤。時間鄰近不是因果證明，盲目 rollback 也可能撤錯變更。
- **C：** 錯誤。Release marker 是事故與趨勢分析的重要 context，應按 retention policy 保存。
- **D：** 錯誤。CloudTrail 說明 API activity，但 customer latency 原因需要 runtime telemetry。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)、[CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)、[AWS CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)

### 練習題 7｜SAP｜runbook 與 playbook

團隊需要兩份文件：A 用於已知的 failover 操作，步驟固定；B 用於『延遲升高但原因未知』的調查，需要依證據分支。哪個設計正確？

A. 兩者都只寫一條線性 command list，不需 validation
B. B 應保持完全抽象，不寫任何 signals、owner 或 escalation，才能通用
C. A 成功執行 API command 就等同 recovery，因此不用 customer check
D. A 使用 runbook，包含 prerequisites、執行/automation、validation、rollback 與 evidence；B 使用 playbook，包含 hypotheses、branching diagnostics、decision points 與 escalation

**答案：D**

- **A：** 錯誤。未知事件需要分支與假設，已知程序也需要 pre/post validation。
- **B：** 錯誤。沒有 signal 與 decision boundary 的 playbook 無法實際協助值班人員。
- **C：** 錯誤。Control action success 不等同 workload recovery，runbook 必須驗證目標 outcome。
- **D：** 正確。Runbook 適合已知可重複程序；playbook 支援未知原因下的引導式調查。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Operational readiness and change management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-readiness.html)、[OPS07-BP03 Use runbooks to perform procedures](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_runbooks.html)、[OPS07-BP04 Use playbooks to investigate issues](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_playbooks.html)、[AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)

### 練習題 8｜SAP｜operational readiness review

新服務功能測試已通過，但尚未確認 on-call owner、quota、alarms、support access、rollback、restore 或 dependency capacity。產品希望今天直接上線，下週再補文件。架構師應建議什麼？

A. ORR 只需在公司第一次上雲時做一次，後續服務不適用
B. 在 launch 前執行一致的 ORR，對關鍵項目要求 evidence；accepted risks 指派 owner/deadline，且重大變更與新學習後重做 review
C. 填一張沒有 evidence、owner 或 approver 的 checklist 即可
D. Managed services 已通過 deploy，所以可免除所有 readiness checks

**答案：B**

- **A：** 錯誤。Readiness 隨 workload、dependencies、流量與組織能力變化，需要週期性或事件驅動更新。
- **B：** 正確。ORR 是 production responsibility gate；它讓缺口在顧客流量進入前被驗證、接受或修正。
- **C：** 錯誤。Checklist 沒有 evidence 與 accountable decision 只是形式，不能降低 launch risk。
- **D：** 錯誤。Managed service 降低部分基礎設施工作，不承擔 workload quotas、data recovery、alerts 或 ownership。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Operational readiness and change management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-readiness.html)、[OPS07-BP02 Ensure a consistent review of operational readiness](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_const_orr.html)

### 練習題 9｜SAP｜incident command 與 stakeholder communication

Regional outage 同時觸發 35 個 alarms，四個 teams 各自想修改 production；客戶已受影響但根因未知。哪些 TWO 回應方式最符合有效 incident management？

A. 讓每個 team 獨立變更 production，誰先修好就算成功
B. 根因百分之百確定前不對 stakeholder 提供任何狀態
C. 維護 timestamped decision/change log，以單一協調流程核准 rollback/recovery，按 cadence 提供已知事實與下一步
D. 依 business impact 宣告與分級事件，指派 incident lead、technical roles、communication owner 與明確 escalation
E. 以 alarm 數量決定優先級，不需要 customer outcome

**答案：C、D**

- **A：** 錯誤。未協調 concurrent changes 會增加風險、破壞 evidence 並造成互相抵銷。
- **B：** 錯誤。可在不猜測根因的前提下溝通已知 impact、mitigation 與下一次 update 時間。
- **C：** 正確。Decision log 與 change coordination 保留共同事實，也便於 handoff 與 post-incident analysis。
- **D：** 正確。明確 command structure 能避免衝突，並把技術、business 與 dependency response 對齊。
- **E：** 錯誤。多個 alarms 可能源自單一 failure；事件優先級應由 customer/business impact 主導。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)、[OPS10-BP01 Use a process for event, incident, and problem management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html)

### 練習題 10｜SAP｜post-incident continuous improvement

相同 capacity incident 三個月內發生四次。每次 postmortem 都寫「多加一個 alarm」，但 action item 沒有 owner、due date 或驗證；Well-Architected review 仍重複同一 high-risk issue。哪些 TWO 改善最重要？

A. 將事故歸因於最後值班的人，因個人懲處可取代 capacity design
B. 只建立 Well-Architected milestone，就視為 remediation 已部署
C. 新增更多沒有 response process 的 alarms，並關閉原 action items
D. 用 load/game day 或 runtime evidence 驗證修正有效，追蹤到完成；用 Well-Architected milestones 記錄 review 進度而非取代執行
E. 做 blameless、evidence-based analysis，找出 system/process contributing factors，依風險排序 corrective actions 並指派 owner/due date

**答案：D、E**

- **A：** 錯誤。只責怪個人會隱藏 capacity、automation、review 與 alert-design 等系統性條件。
- **B：** 錯誤。Milestone 是 review snapshot，不是 code/config 已變更或效果已證明的 evidence。
- **C：** 錯誤。沒有 actionability 的 alarm 會增加 toil，無法消除重複根因。
- **D：** 正確。Corrective action 要有 verification loop；Well-Architected Tool 可保存 risks/progress，但真正改善由團隊實作與驗證。
- **E：** 正確。Continuous improvement 需要從事件 evidence 形成可執行、可問責且有優先級的工程工作。

**事實查證：** [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[OPS11-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html)、[AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)、[What is AWS Fault Injection Service?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)、[OPS07-BP02 Ensure a consistent review of operational readiness](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_const_orr.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「定義owner、operational readiness review、SLO、alarm、runboo…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「架構不是一次性圖紙；runbook、指標、事件與改進backlog共同決定長期品質。」，所以「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」能直接滿足它；若constraint改成「Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」。替代方案「Managed service降低部分toil，但service quota、cost、security與application failure仍需ownership。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每次事故只增加更多alarm，造成noise而沒有移除根因。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「架構不是一次性圖紙；runbook、指標、事件與改進backlog共同決定長期品質。」，排除會導致「每次事故只增加更多alarm，造成noise而沒有移除根因。」的選項，再選「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.2 Determine a strategy to improve security；SAP-3.3 Determine a strategy to improve performance。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「定義owner、operational readiness review、SLO、alarm、runbook、postmortem與定期Well-Architected review。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「operations is a feedback system, not a support phase」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
