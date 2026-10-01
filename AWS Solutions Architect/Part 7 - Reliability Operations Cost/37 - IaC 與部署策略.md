---
chapter: 37
title: IaC 與部署策略
part: 7
---

# 第 37 章　Infrastructure as Code 與部署策略

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 Infrastructure as Code 解決了什麼問題，看懂一份 CloudFormation template 的每個區段
> - 安全地更新 stack：用 change set 預覽 replacement、用 DeletionPolicy 與 stack policy 保護資料、理解 rollback 與 drift detection
> - 用 nested stacks、cross-stack references、StackSets 與 custom resources 組織大型與多帳號的基礎設施
> - 分辨 CloudFormation、CDK、SAM 的關係，並用 CodePipeline、CodeBuild、CodeDeploy 建立發布流程
> - 比較 all-at-once、rolling、immutable、blue/green、canary、linear 部署，並知道 EC2、Beanstalk、ECS、Lambda 各自怎麼做
> - 用 AppConfig feature flags 把「部署」和「發布」分開，用 Service Catalog 讓團隊自助取得經核准的架構
>
> **前置知識**：第 18 章（Auto Scaling）、第 19 章（Lambda）、第 21 章（ECS 與 Beanstalk）、第 36 章（CloudWatch alarms）
> **考試比重**：SAA ★★☆（Domain 2 高可用與解耦）｜SAP ★★★（Domain 2 部署策略、Domain 3 營運卓越）

## 37.1 故事：一個在 console 上被改掉的設定

Wanderly 的基礎設施到目前為止大多是小林在 console 上點出來的。一開始很快，但問題一個接一個出現。

第一件事發生在週二。staging 環境一切正常的新版訂房服務，部署到 prod 之後立刻大量逾時。查了一整個下午才發現，三個月前有人為了處理事故，在 console 上把 prod 的 SQS visibility timeout 從 30 秒改成 120 秒，staging 卻沒改。兩個環境「應該一樣」，但沒有人說得清楚到底哪裡不一樣。

第二件事發生在週五晚上。團隊用 SSH 登入每一台 EC2，逐台更新程式，更新到一半發現新版有 bug，要退回時才發現沒有人記得舊版的設定檔長什麼樣，網站斷斷續續壞了 40 分鐘。

技術主管在檢討會上提出兩個原則：**所有基礎設施都要用程式碼描述、經過 code review、從版本控制部署**；**所有應用程式更新都要能在幾分鐘內自動退回，而且新版本一開始只讓少數使用者碰到**。前者是 Infrastructure as Code，後者是部署策略，也就是本章的兩大主題。

## 37.2 為什麼需要 Infrastructure as Code

**Infrastructure as Code（IaC，基礎設施即程式碼）** 是用文字檔描述你要的雲端資源（VPC、資料庫、佇列、IAM role……），再由工具依照這份描述建立或修改資源。這份文字檔可以放進 Git，像應用程式碼一樣被 review、測試與追蹤歷史。

它解決的問題正好對應 Wanderly 的兩次事故：

| 問題 | 手動操作 | IaC |
|---|---|---|
| 環境一致性 | 每個環境靠人記得做了什麼 | 同一份 template 帶不同參數建立 dev、staging、prod |
| 變更追蹤 | 誰改的、為什麼改，很難查 | Git 歷史 + code review 紀錄 |
| 重建速度 | 災難後要靠文件與記憶重建 | 重新部署 template 即可（第 34 章 DR 的前提） |
| 變更風險 | 改了才知道會發生什麼 | 部署前先預覽變更內容 |
| 偏移 | 手動修改沒人知道 | Drift detection 找出和 template 不一致的地方 |

### 宣告式與命令式

IaC 工具大致分兩種思路。**命令式（imperative）** 是寫出「步驟」：先建立 VPC，再建立 subnet，再建立 route……，就像一支 shell script 呼叫一連串 CLI 指令。它的問題是：執行到一半失敗怎麼辦？第二次執行會不會重複建立？

**宣告式（declarative）** 是寫出「最終要長成什麼樣子」：要有一個 CIDR 為 `10.20.0.0/16` 的 VPC、兩個 subnet……。工具負責比較「現在的狀態」與「想要的狀態」，算出需要建立、修改或刪除什麼，並處理相依順序。**CloudFormation、Terraform 都是宣告式的**，這也是 IaC 的主流。

## 37.3 CloudFormation：template 與 stack

**AWS CloudFormation** 是 AWS 原生的宣告式 IaC 服務。你寫一份 **template（範本）**，CloudFormation 依照它建立一組資源，這一組資源稱為一個 **stack（堆疊）**。之後修改 template 並「更新 stack」，CloudFormation 會算出差異並修改實際資源；刪除 stack，資源也一起被刪除（除非另有設定）。CloudFormation 本身不收費，你只付它建立的資源的費用。

### Template 的組成

Template 可以用 YAML 或 JSON 撰寫，主要區段如下（只有 `Resources` 是必要的）：

| 區段 | 用途 |
|---|---|
| `AWSTemplateFormatVersion`、`Description` | 版本與說明 |
| `Parameters` | 部署時才輸入的值，例如環境名稱、instance type |
| `Mappings` | 靜態對照表，例如「每個 Region 用哪個 AMI ID」 |
| `Conditions` | 條件判斷，例如「只有 prod 才建立 Multi-AZ」 |
| `Transform` | 使用 macro 展開 template，例如 SAM（37.6 節） |
| `Resources` | **要建立的資源**，每個資源有 logical ID、`Type` 與 `Properties` |
| `Outputs` | 部署後要輸出的值，例如 queue URL；可以 export 給其他 stack 使用 |

### 一份實際的 template

下面是 Wanderly 付款服務的簡化版 template：

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Wanderly payments service (simplified)

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  DbSubnetGroupName:
    Type: String

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  PaymentsDlq:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600        # 14 天

  PaymentsQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub "wanderly-${Environment}-payments"
      VisibilityTimeout: 120
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt PaymentsDlq.Arn
        maxReceiveCount: 5

  OrdersDb:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: mysql
      DBInstanceClass: !If [IsProd, db.r6g.large, db.t4g.medium]
      AllocatedStorage: "100"
      MultiAZ: !If [IsProd, true, false]
      StorageEncrypted: true
      DBSubnetGroupName: !Ref DbSubnetGroupName
      MasterUsername: wanderly_admin
      ManageMasterUserPassword: true         # 密碼由 RDS 存進 Secrets Manager
      DeletionProtection: !If [IsProd, true, false]

Outputs:
  PaymentsQueueUrl:
    Value: !Ref PaymentsQueue
    Export:
      Name: !Sub "${Environment}-payments-queue-url"
```

讀這份 template 時要注意幾件事：

- **Intrinsic functions（內建函式）**：`!Ref` 取得參數值或資源的主要識別（SQS queue 的 `Ref` 是 URL）；`!GetAtt` 取得資源的屬性（例如 queue 的 ARN）；`!Sub` 做字串替換；`!If` 與 `!Equals` 搭配 `Conditions` 做條件判斷。還有 `!Join`、`!FindInMap`、`!ImportValue` 等。
- **Pseudo parameters**：`AWS::Region`、`AWS::AccountId`、`AWS::StackName` 等由 CloudFormation 自動提供的值，讓同一份 template 能在不同帳號與 Region 部署。
- **相依順序**：`PaymentsQueue` 用 `!GetAtt PaymentsDlq.Arn` 引用了 DLQ，CloudFormation 因此知道要先建 DLQ。這種從引用推導出的相依稱為 **implicit dependency**；沒有引用關係但必須有先後時（例如 route 要等 IGW 附加完成，第 5 章的範例），用 `DependsOn` 明確指定。
- **一份 template、多個環境**：同一份檔案用 `Environment=dev` 與 `Environment=prod` 部署，差異只在 conditions 決定的規格，週二那種「staging 與 prod 不一樣」的事故就不會再發生。

### 機密不要寫在 template 裡

Template 會進 Git、會出現在 console 上，**絕對不能寫入明文密碼**。常見做法：

- 讓服務自己管理密碼，例如 RDS 的 `ManageMasterUserPassword`。
- 使用 **dynamic reference（動態參照）**，在部署時才從 Secrets Manager 或 Parameter Store 取值，例如 `'{{resolve:secretsmanager:wanderly/prod/payco:SecretString:apiKey}}'`。Template 只保存「參照」，不保存值。
- 若必須用 parameter 傳入敏感值，設定 `NoEcho: true` 避免在 console 與 API 回應中顯示，且不要放進 `Outputs`。

## 37.4 安全地更新 stack：change set、rollback、drift 與資料保護

建立 stack 不難，真正的風險在「更新」：一個看似無害的屬性修改，可能讓 CloudFormation 刪掉舊資料庫、建一個新的。這一節是本章最常被考的部分。

### 更新時資源會發生什麼事

CloudFormation 修改每個屬性時，會依該屬性的特性採取三種行為之一：

| 更新行為 | 意義 | 例子 |
|---|---|---|
| **No interruption** | 原地修改，不影響運作 | 修改 SQS visibility timeout、加 tag |
| **Some interruption** | 原地修改，但會短暫中斷 | 修改 EBS-backed EC2 的 instance type（需要 stop／start） |
| **Replacement** | **建立新資源、切換引用、刪除舊資源**，physical ID 改變 | 修改 EC2 的 `ImageId`、RDS 的 `DBInstanceIdentifier` |

Replacement 對有狀態的資源（資料庫、EBS volume）是災難：新資源是空的，舊資源預設會被刪除。另外，如果你為資源指定了**自訂名稱**（例如 `QueueName`），需要 replacement 的更新會失敗，因為新舊資源不能同名。

### Change set：先看再做

**Change set（變更集）** 是「更新 stack 前的預覽」：你提交新的 template 或參數，CloudFormation 計算出會新增、修改、刪除哪些資源，以及每個修改是否需要 **replacement**（`True`、`False` 或 `Conditional`），但**不會實際執行**。確認無誤後才 execute change set。

Wanderly 從此規定：prod 的每次 stack 更新都必須先產生 change set，reviewer 特別檢查兩件事：有沒有任何有狀態資源的 `Replacement` 是 `True` 或 `Conditional`；有沒有 IAM 相關的變更。

```bash
aws cloudformation create-change-set \
  --stack-name wanderly-prod-payments \
  --change-set-name add-alarm-2026-10-01 \
  --template-body file://payments.yaml \
  --parameters ParameterKey=Environment,ParameterValue=prod \
               ParameterKey=DbSubnetGroupName,ParameterValue=wanderly-prod-db \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-change-set \
  --stack-name wanderly-prod-payments \
  --change-set-name add-alarm-2026-10-01
```

`--capabilities` 是另一道防線：template 中若有建立 IAM 資源，必須明確承認（`CAPABILITY_IAM`，或自訂名稱的 IAM 資源用 `CAPABILITY_NAMED_IAM`）；含有 macro 或需要展開的 transform 時要加 `CAPABILITY_AUTO_EXPAND`。

> [!warning] 常見誤解
> 「Change set 成功建立，代表執行一定會成功。」不對。Change set 只是預覽 CloudFormation「打算做什麼」，執行時仍可能因權限不足、配額不夠、名稱衝突或服務端錯誤而失敗並 rollback。它也不會驗證應用程式行為。

### 保護資料：DeletionPolicy 與 UpdateReplacePolicy

**DeletionPolicy** 決定「資源從 template 移除或 stack 被刪除時」怎麼處理實際資源：

- `Delete`：刪除（大多數資源的預設）。
- `Retain`：保留資源，只是不再由這個 stack 管理。
- `Snapshot`：刪除前先建立 snapshot，只適用於支援 snapshot 的資源，例如 EBS volume、RDS DB instance／cluster、ElastiCache、Redshift、Neptune、DocumentDB。
- `RetainExceptOnCreate`：建立失敗而 rollback 時照常刪除，其他情況保留。適合避免「第一次建立失敗」留下一堆孤兒資源。

**UpdateReplacePolicy** 則處理「更新時發生 replacement」被換掉的舊資源，選項相同。兩者應該一起設定：只設 DeletionPolicy 不能防止「改錯一個屬性導致 replacement、舊資料庫被刪」。

有一個例外要記住：`AWS::RDS::DBCluster`，以及沒有指定 `DBClusterIdentifier`（也就是不屬於 Aurora cluster）的 `AWS::RDS::DBInstance`，若未指定 DeletionPolicy，CloudFormation 的預設是 `Snapshot`；其他資源的預設都是 `Delete`。注意這個預設只處理「刪除」，不處理 replacement，所以最佳實務仍是明確寫出 DeletionPolicy 與 UpdateReplacePolicy，並在 prod 同時開啟資源本身的 `DeletionProtection`。

### Stack policy 與 termination protection

**Stack policy** 是一份附加在 stack 上的 JSON，限制「stack 更新」時哪些資源可以被修改、替換或刪除。一旦設定，**所有資源預設都受保護**，必須明確 Allow 才能更新：

```json
{
  "Statement": [
    { "Effect": "Allow", "Action": "Update:*", "Principal": "*", "Resource": "*" },
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/OrdersDb"
    }
  ]
}
```

這份 policy 允許更新所有資源，但禁止替換或刪除 `OrdersDb`。若真的需要，可以在單次更新時提供臨時的 override policy。

**Termination protection** 則是防止整個 stack 被刪除：啟用後，刪除 stack 的請求會直接失敗。兩者分工：stack policy 管「更新」，termination protection 管「刪除整個 stack」，DeletionPolicy 管「刪除時資源本身的命運」。

### Rollback：失敗時回到上一個穩定狀態

- **建立失敗**：預設會 rollback，刪除已建立的資源，stack 狀態變成 `ROLLBACK_COMPLETE`（這種 stack 只能刪除後重建）。開發時可以選擇保留已成功建立的資源以便除錯。
- **更新失敗**：自動 rollback 回上一個成功的設定，狀態為 `UPDATE_ROLLBACK_COMPLETE`。
- **Rollback triggers**：你可以指定 CloudWatch alarm，CloudFormation 在更新期間以及更新完成後的一段監控期間（最長 180 分鐘）若看到 alarm 進入 ALARM，就自動 rollback。這讓「部署後錯誤率上升」也能觸發基礎設施層的回退。
- **`UPDATE_ROLLBACK_FAILED`**：rollback 本身也失敗了，常見原因是有人在 CloudFormation 之外手動刪除或修改了資源，導致 CloudFormation 無法把它改回舊設定。處理方式是先修正根本原因（例如把資源恢復），再執行 **continue update rollback**；若某些資源確實無法恢復，可以指定跳過這些資源，讓 stack 回到可操作的狀態。

### Drift detection：找出 console 上被改掉的設定

**Drift（偏移）** 是指實際資源的設定和 template 描述的不一致，通常來自有人在 console 或 CLI 直接修改。**Drift detection** 會比對 stack 中資源的實際屬性與預期值，列出哪些資源 `MODIFIED`、`DELETED` 或 `IN_SYNC`，以及差異的屬性。

週二事故的 visibility timeout，若當時有定期執行 drift detection，就會被標記為 `MODIFIED`。不過 drift detection 只比較 template 中明確定義、且該資源類型支援偵測的屬性；它也只負責「發現」，不會自動修正。修正方式有二：把正確值寫回 template 並更新 stack（接受現況），或重新部署 template 覆蓋手動修改（恢復設計）。CloudFormation 也提供 **drift-aware change set**，在預覽時把 drift 納入考量。

## 37.5 組織大型基礎設施：拆 stack、跨帳號與擴充

當 Wanderly 的 template 長到幾千行、團隊增加到十幾個時，「一個 stack 放所有東西」就不再可行：任何小修改都要動整個 stack，一個資源失敗會 rollback 全部，權限也無法依團隊分開。

### 依生命週期拆 stack

最常見的拆法是依「變動頻率與擁有者」分層：網路（VPC、subnet，幾乎不變，網路團隊管理）→ 共用資料層（資料庫、快取，少變動）→ 應用程式（每天部署）。分層後，stack 之間如何傳遞值？有兩種機制：

| | Nested stacks | Cross-stack references |
|---|---|---|
| 做法 | 父 stack 用 `AWS::CloudFormation::Stack` 資源引用存在 S3 的子 template | 一個 stack 在 `Outputs` 用 `Export`，另一個 stack 用 `Fn::ImportValue` 取得 |
| 關係 | 子 stack 是父 stack 的一部分，一起建立、更新、刪除 | 兩個獨立 stack，各自部署 |
| 適合 | **重複使用的元件**（例如標準 ALB + ASG 組合），在同一次部署中組裝 | **不同團隊、不同生命週期**的資源共享值（例如網路 stack 匯出 VPC ID） |
| 限制 | 應從父 stack 更新 | 只能在同帳號同 Region；被 import 的 export 不能刪除或修改 |

> [!tip] 考試提示
> 題目說「網路團隊管理 VPC，多個應用團隊的 stack 需要引用 subnet ID，且各自獨立部署」→ cross-stack references（Export／ImportValue）。題目說「一個標準的安全元件要在很多 template 中重複使用」→ nested stacks（或 CloudFormation modules）。

### StackSets：一次部署到多個帳號與 Region

Wanderly 進入多帳號階段後，每個帳號都需要相同的基線：CloudTrail 設定、Config rules、監控用 IAM role、日誌的 subscription filter（第 36 章）。**CloudFormation StackSets** 讓你用一份 template，在**多個帳號 × 多個 Region** 建立 **stack instances**，並集中更新。

StackSets 有兩種權限模型：

- **Self-managed permissions**：你自己在管理帳號建立 `AWSCloudFormationStackSetAdministrationRole`，在每個目標帳號建立 `AWSCloudFormationStackSetExecutionRole`，並建立信任關係。適合不在 Organizations 中的帳號。
- **Service-managed permissions**：與 **AWS Organizations** 整合，以 OU 為目標，由 StackSets 自動建立所需角色；可啟用 **automatic deployment**，新帳號加入 OU 時自動部署、帳號移出時自動移除（或保留）stack instance。可以把管理權委派給 delegated administrator 帳號。

部署時可以設定 **operation preferences** 控制風險：同時部署的帳號數上限（maximum concurrent accounts）、允許失敗的帳號數（failure tolerance）、Region 的部署順序與是否平行。例如先在一個 Region 的少數帳號部署，確認沒問題再擴大，相當於基礎設施版的 canary。

### Custom resources：CloudFormation 做不到的事

有些事 CloudFormation 沒有原生資源類型，例如：呼叫第三方 API 註冊 webhook、在資料庫建立初始 schema、查詢某個值再回填給其他資源。**Custom resource** 讓 CloudFormation 在建立、更新、刪除時呼叫你的 Lambda function（或 SNS topic）：

```yaml
PaycoWebhook:
  Type: Custom::PaycoWebhook
  Properties:
    ServiceToken: !GetAtt WebhookProviderFunction.Arn
    CallbackUrl: !Sub "https://${ApiDomain}/payments/callback"
```

CloudFormation 送出包含 `RequestType`（Create、Update、Delete）與一個預先簽署的 **response URL** 的請求，Lambda 完成工作後必須把 `SUCCESS` 或 `FAILED` 回傳到這個 URL。實作時要注意三點：一定要回應（包括程式出錯時），否則 stack 會一直等到逾時；Create／Update／Delete 都要能安全地重複執行（idempotent）；Delete 時要清理外部資源，否則會留下孤兒。

### 其他常用機制

- **`cfn-init`、`cfn-signal` 與 CreationPolicy**：EC2 開機時用 `cfn-init` 依 template 中的 metadata 安裝套件與設定，再用 `cfn-signal` 告訴 CloudFormation「設定成功」；搭配 `CreationPolicy`，CloudFormation 會等到收到指定數量的成功訊號才把資源標為完成，否則視為失敗並 rollback。
- **ASG 的 UpdatePolicy**：決定 launch template 改變時 CloudFormation 如何替換 instance。`AutoScalingRollingUpdate` 分批替換（可設定 `MaxBatchSize`、`MinInstancesInService`、是否等待 signal）；`AutoScalingReplacingUpdate` 搭配 `WillReplace: true` 會建立一個全新的 ASG，成功後才刪除舊的，相當於 immutable 部署（37.8 節）。
- **Service role**：讓 CloudFormation 以指定的 IAM role 執行操作，使用者本身只需要 CloudFormation 權限與 `iam:PassRole`，不需要直接擁有建立資源的權限。這是限制「誰能建立什麼」的重要手段。
- **Resource import 與 IaC generator**：把既有、手動建立的資源納入 stack 管理；IaC generator 可以掃描帳號中的既有資源產生 template 草稿。
- **部署前檢查**：`cfn-lint` 檢查 template 語法與屬性；**CloudFormation Guard** 以規則檢查 template 是否符合政策（例如「所有 S3 bucket 必須加密」），適合放在 CI；**CloudFormation Hooks** 則在 CloudFormation 服務端於建立、更新、刪除資源前執行檢查，可以阻擋不合規的操作，無法被繞過。

## 37.6 更高階的寫法：CDK 與 SAM

CloudFormation template 很精確，但也很冗長：一個標準的 ECS 服務加上 ALB、IAM role、log group，YAML 動輒數百行。AWS 提供兩個建立在 CloudFormation 之上的工具。

### AWS CDK：用程式語言描述基礎設施

**AWS Cloud Development Kit（CDK）** 讓你用 TypeScript、Python、Java、C#、Go 等語言撰寫基礎設施。執行 `cdk synth` 時，CDK 把程式「合成」為 CloudFormation template，再由 `cdk deploy` 交給 CloudFormation 部署。也就是說，**CDK 是撰寫層，CloudFormation 仍是實際執行與管理狀態的引擎**，change set、rollback、drift 等觀念完全適用。

```typescript
import * as cdk from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';

export class PaymentsStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const dlq = new sqs.Queue(this, 'PaymentsDlq', {
      retentionPeriod: cdk.Duration.days(14),
    });
    const queue = new sqs.Queue(this, 'PaymentsQueue', {
      visibilityTimeout: cdk.Duration.minutes(2),
      deadLetterQueue: { queue: dlq, maxReceiveCount: 5 },
    });

    const worker = new lambda.Function(this, 'PaymentWorker', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'app.handler',
      code: lambda.Code.fromAsset('src/worker'),
      timeout: cdk.Duration.seconds(60),
    });
    // 自動建立 event source mapping，並授予 worker 讀取與刪除訊息的 IAM 權限
    worker.addEventSource(new SqsEventSource(queue, { batchSize: 10 }));
  }
}
```

最後一行展示了 CDK 的價值：一行程式就產生了 event source mapping 與最小權限的 IAM policy，在 YAML 裡要自己寫好幾個資源。CDK 的元件稱為 **construct**，分三層：**L1** 與 CloudFormation 資源一對一（類別名稱以 `Cfn` 開頭）；**L2** 是帶有合理預設值與便利方法的高階元件（上例的 `sqs.Queue`）；**L3（patterns）** 是多個資源的組合，例如「ALB 後面接一個 Fargate 服務」。

使用 CDK 部署前，每個目標帳號與 Region 需要先執行一次 **`cdk bootstrap`**，建立一個名為 `CDKToolkit` 的 stack，內含存放 Lambda 程式碼與 container image 等 **asset** 的 S3 bucket、ECR repository，以及部署用的 IAM roles。跨帳號部署時，目標帳號 bootstrap 要信任 pipeline 所在的帳號。`cdk diff` 可以在部署前比較差異，作用類似 change set。

### AWS SAM：serverless 專用的簡寫

**AWS Serverless Application Model（SAM）** 是 CloudFormation 的擴充語法，專門簡化 serverless 應用。Template 開頭加上 `Transform: AWS::Serverless-2016-10-31`，就能使用 `AWS::Serverless::Function`、`AWS::Serverless::Api`、`AWS::Serverless::SimpleTable` 等簡寫資源，部署時由 CloudFormation 展開成完整的 Lambda、API Gateway、IAM role 等資源。

```yaml
Transform: AWS::Serverless-2016-10-31
Resources:
  QuoteFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.12
      Handler: app.handler
      CodeUri: src/quote/
      AutoPublishAlias: live
      DeploymentPreference:
        Type: Canary10Percent5Minutes
        Alarms:
          - !Ref QuoteErrorsAlarm
        Hooks:
          PreTraffic: !Ref QuotePreTrafficCheck
      Events:
        GetQuote:
          Type: HttpApi
          Properties:
            Path: /quotes
            Method: get
```

`AutoPublishAlias` 讓每次程式變更都自動發布新的 Lambda version 並更新 `live` alias；`DeploymentPreference` 會自動建立 CodeDeploy 設定，以 canary 方式把 10% 流量導向新版本 5 分鐘，期間若 `QuoteErrorsAlarm` 觸發就自動退回（37.9 節）。SAM CLI 提供 `sam build`、`sam deploy`、`sam local invoke`（在本機以 container 模擬 Lambda 執行）等指令。

### 第三方工具

**Terraform** 是另一個廣泛使用的宣告式 IaC 工具（HashiCorp），支援多雲。它不使用 CloudFormation，而是自己維護一份 **state file** 記錄資源狀態；在 AWS 上常見的做法是把 state 存在 S3 並啟用鎖定機制避免多人同時修改。考試以 CloudFormation 家族為主，但題目若強調「多雲一致工具」或「既有 Terraform 投資」，Terraform 也是合理的答案（Service Catalog 與 Control Tower 的 Account Factory for Terraform 也支援它）。

## 37.7 CI/CD：從 commit 到 production

有了 IaC，基礎設施可以用程式碼描述；接下來要解決「程式碼怎麼安全地走到 prod」。**CI（Continuous Integration，持續整合）** 是每次 commit 都自動建置與測試；**CD（Continuous Delivery／Deployment，持續交付／部署）** 是把通過測試的成品自動部署到各環境，差別在 prod 前是否需要人工核准。

### AWS 的 CI/CD 服務分工

| 服務 | 負責 | 重點 |
|---|---|---|
| 原始碼來源 | 存放程式碼 | GitHub、GitLab、Bitbucket 透過 **CodeConnections**（舊名 CodeStar Connections）連接；也可用 S3 或 ECR 作為來源 |
| **CodePipeline** | **編排**：定義 stage 與 action 的順序 | Source → Build → Test → Approval → Deploy；artifact 存在 S3 |
| **CodeBuild** | **建置與測試**：在受管 container 中執行指令 | 依 `buildspec.yml` 執行；按建置時間計費；無需管理 build server |
| **CodeDeploy** | **部署**到 EC2／地端、Lambda、ECS | in-place、blue/green、canary、linear；可依 alarm 自動 rollback |
| **CodeArtifact** | 套件庫（npm、PyPI、Maven 等） | 快取公開套件、發布內部套件 |

AWS CodeCommit（AWS 自己的 Git 託管服務）在 2024 年 7 月停止對新客戶開放，AWS 於 2025 年 11 月 24 日宣布它恢復完整的 general availability、重新開放新客戶使用。由於現況曾有變動，舊的考題與文章可能仍寫著「CodeCommit 已不接受新客戶」；本書以 GitHub 等外部 repository 透過 CodeConnections 連接作為主要範例，CodeCommit 也是可用的來源。

最常見的誤解是把 CodePipeline 當成「會編譯、會部署」的服務。它只負責編排：build 是 CodeBuild 做的，部署則交給 CodeDeploy、CloudFormation、ECS、Elastic Beanstalk 等 deploy action provider。

### CodeBuild 的 buildspec

```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      nodejs: 20
  pre_build:
    commands:
      - npm ci
      - npm test
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
  build:
    commands:
      - IMAGE_URI=$ECR_REGISTRY/payments:$CODEBUILD_RESOLVED_SOURCE_VERSION
      - docker build -t $IMAGE_URI .
  post_build:
    commands:
      - docker push $IMAGE_URI
      - printf '[{"name":"payments","imageUri":"%s"}]' $IMAGE_URI > imagedefinitions.json
artifacts:
  files:
    - imagedefinitions.json
```

這份 buildspec 安裝相依套件、跑測試、建立 container image，並以 commit ID 作為 image tag 推到 ECR，最後輸出 `imagedefinitions.json` 給後續的 ECS deploy action 使用。建置 Docker image 的 CodeBuild 專案需要啟用 privileged mode；需要的機密（例如私有套件庫 token）可在 buildspec 的 `env` 區段從 Parameter Store 或 Secrets Manager 取得，不要寫死在檔案裡。

### Wanderly 的發布流程

```text
 開發者 git push（GitHub）
        │ ① CodeConnections 觸發
        ▼
 ┌──────────────── CodePipeline（工具帳號）──────────────────────────────┐
 │ Source ─② Build & Test（CodeBuild）─③ Deploy staging ─④ 整合測試      │
 │                 │ image → ECR                │ CloudFormation    │     │
 │                 │ template → S3（KMS 加密）  │ change set 執行   │     │
 │                                                                  ▼     │
 │                         ⑤ Manual approval（SNS 通知 reviewer）         │
 │                                                                  │     │
 │                         ⑥ Deploy prod：CodeDeploy canary ─────────┘     │
 │                              10% 流量 5 分鐘 → 100%                      │
 └──────────────────────────────────────┬──────────────────────────────────┘
                                        │ ⑦ 部署期間監看 CloudWatch alarms
                                        ▼
                       錯誤率或 p99 超標 → 自動 rollback 到前一版
```

① push 到 main branch 觸發 pipeline。② CodeBuild 建置一次 image 與 template，產出的 artifact 在之後所有環境**重複使用**，不在每個環境重新建置，確保 staging 測過的就是 prod 跑的（build once, deploy many）。③ 以 CloudFormation change set 更新 staging 的基礎設施與服務。④ 自動化整合測試。⑤ prod 前的人工核准，reviewer 可以看到 change set 內容。⑥ prod 以 canary 方式部署。⑦ 部署期間與部署後監看第 36 章設計的 SLI alarm，一旦超標自動 rollback。

CodePipeline 的 V2 類型 pipeline 支援依 Git tag、branch 或 pull request 觸發、pipeline 層級變數，以及 stage 失敗時自動 rollback 到上一次成功的執行。

## 37.8 部署策略：怎麼把新版本換上去

部署策略回答的是：「舊版本正在服務使用者，新版本要怎麼換上去，才能兼顧停機時間、成本、風險與退回速度？」先用一組 10 台機器的服務來理解各策略的原理，37.9 節再看 AWS 各服務怎麼實作。

### 六種策略

**All-at-once（一次全部）**：同時把 10 台都更新。最快、最便宜，但更新期間可能全部停止服務，新版有問題時 100% 使用者受影響，退回要再部署一次舊版。只適合 dev 環境。

**Rolling（滾動）**：每次更新一批（例如 2 台），這批恢復健康後再更新下一批。不需要額外機器，但更新期間可用容量下降（只有 8 台在服務），而且**新舊版本同時在線**。退回要再滾動一次。

**Rolling with additional batch（滾動加額外批次）**：先多開一批新機器，再開始滾動，讓容量全程維持 10 台。多付一點錢換取不降容量，但一樣有新舊版本並存。

**Immutable（不可變）**：不修改任何既有機器，而是建立一組全新的機器跑新版本，新機器都健康後才加入服務並移除舊機器。部署期間機器數量暫時加倍；新版有問題時只要刪除新機器，舊機器完全沒被碰過，退回快又乾淨。

**Blue/green（藍綠）**：維持兩套完整環境，blue 是目前的 prod，green 是新版本。Green 完整部署並測試後，把流量**一次切換**（或依權重切換）到 green；有問題就把流量切回 blue。退回最快（只是切流量），代價是兩套環境的成本與流量切換機制的複雜度。

**Canary（金絲雀）**：先把一小部分流量（例如 10%）導向新版本，觀察一段時間（bake time），指標正常再把剩下的流量一次切過去。名稱來自礦工帶金絲雀下礦坑偵測毒氣。**Linear（線性）**：每隔固定時間增加固定比例，例如每 1 分鐘增加 10%，10 分鐘後達到 100%。兩者通常建立在 blue/green 的雙版本基礎上，以流量權重控制曝險。

### 比較

| 策略 | 部署中容量 | 額外成本 | 新舊並存 | 退回速度 | 受影響範圍 |
|---|---|---|---|---|---|
| All-at-once | 可能中斷 | 無 | 否 | 慢（重新部署） | 100% |
| Rolling | 下降 | 無 | 是 | 慢 | 逐批擴大 |
| Rolling + additional batch | 維持 | 一批 | 是 | 慢 | 逐批擴大 |
| Immutable | 維持 | 暫時加倍 | 短暫 | 快（刪除新機器） | 新機器健康後才服務 |
| Blue/green | 維持 | 兩套環境 | 否（或依權重） | 最快（切回流量） | 切換時全部或依權重 |
| Canary／Linear | 維持 | 兩個版本並存 | 是（受控） | 快 | 一開始只有小比例 |

### 資料庫變更：部署策略的盲點

部署策略處理的是應用程式版本，但資料庫 schema 只有一份。若新版本把欄位 `phone` 改名為 `phone_number`，在 rolling、canary 或 blue/green 期間，舊版本與新版本會同時讀寫同一個資料庫，舊版會立刻壞掉；切回舊版也救不了，因為欄位已經改名了。

解法是 **expand/contract（擴張／收縮）** 模式：

1. **Expand**：先部署只「新增」的 schema 變更（新增 `phone_number` 欄位），新舊程式都能運作。
2. 部署新版程式，同時寫入新舊欄位並以新欄位為主；回填舊資料。
3. 確認不再需要退回舊版後，**contract**：移除舊欄位與相容程式碼。

每一步都向後相容，所以任何時候都能退回應用程式版本。若是資料庫引擎升級或大規模變更，RDS 與 Aurora 另有 **Blue/Green Deployments** 功能，建立同步複寫的 green 資料庫環境再切換（第 26 章）。

## 37.9 AWS 各服務怎麼實作部署策略

### EC2 與 Auto Scaling：CodeDeploy 或 instance refresh

**CodeDeploy** 對 EC2／地端主機的部署需要在主機上安裝 **CodeDeploy agent**，部署內容（revision）存在 S3 或 GitHub，由 `appspec.yml` 定義檔案位置與 **lifecycle hooks**：`ApplicationStop` → `BeforeInstall` → `AfterInstall` → `ApplicationStart` → `ValidateService`，每個 hook 執行你提供的 script。

- **In-place**：在既有主機上停止舊版、安裝新版。可選擇預設設定 `CodeDeployDefault.AllAtOnce`、`HalfAtATime`、`OneAtATime`，或自訂「最少健康主機數」。搭配 load balancer 時，CodeDeploy 會在更新每台主機前把它從 target group 移除、完成後再加回。
- **Blue/green**：CodeDeploy 複製一個新的 Auto Scaling group（或使用另一組主機），在新主機上部署，再透過 load balancer 把流量切到新主機；舊主機可以保留一段時間方便退回，之後自動終止。

CodeDeploy 可以設定**自動 rollback**：部署失敗時，或指定的 CloudWatch alarm 在部署期間進入 ALARM 時，自動重新部署上一個成功的版本。

不用 CodeDeploy 時，若應用程式是烤在 AMI 裡（golden AMI，第 17 章），可以更新 launch template 後使用 ASG 的 **instance refresh** 分批替換 instance（第 18 章），或用 CloudFormation 的 ASG `UpdatePolicy`（37.5 節）。

### Elastic Beanstalk：內建的部署政策

Elastic Beanstalk（第 21 章）把部署策略做成環境的設定選項：

| Beanstalk 政策 | 對應策略 |
|---|---|
| All at once | All-at-once |
| Rolling | Rolling |
| Rolling with additional batch | Rolling + additional batch |
| Immutable | Immutable：在暫時的新 ASG 啟動新 instance，健康後移入原環境 |
| Traffic splitting | Canary：一部分流量導向新 instance，評估期間後決定繼續或退回 |

Beanstalk 的 **blue/green** 不是部署政策，而是做法：**複製（clone）出一個新環境**部署新版本，測試後使用 **swap environment URLs**，交換兩個環境的 CNAME，讓流量切到新環境；有問題再交換回來。因為是 DNS 層的切換，客戶端可能因 DNS 快取而延遲切換。另外，若 RDS 資料庫建立在 Beanstalk 環境「之內」，它會和環境同生共死；正式環境應把資料庫建立在環境之外，blue 與 green 才能共用同一個資料庫。

### ECS：rolling、CodeDeploy blue/green 與內建 blue/green

ECS service 預設使用 **rolling update**，由兩個參數控制：

- `minimumHealthyPercent`：部署中至少要維持多少比例的 task 處於健康狀態。
- `maximumPercent`：部署中最多可以同時存在多少比例的 task（含新舊）。

例如 desired count 為 10、minimum 100%、maximum 200%，ECS 會先啟動新 task、健康後才停止舊 task，容量不下降。**Deployment circuit breaker** 會偵測新 task 一直無法進入穩定狀態的部署，自動判定失敗並可設定自動 rollback；也可以指定 CloudWatch alarm，在部署期間指標異常時 rollback。

需要 blue/green 時，傳統做法是把 service 的 deployment controller 設為 **CodeDeploy**：準備兩個 target group 與 ALB 的 production listener，以及選用的 **test listener**。CodeDeploy 先在 green target group 啟動新 task set，可以透過 test listener 先跑驗證（`AfterAllowTestTraffic` hook），再依部署設定（`ECSAllAtOnce`、`ECSCanary10Percent5Minutes`、`ECSLinear10PercentEvery1Minutes` 等）把 production 流量移到 green，期間監看 alarm 決定是否 rollback。2025 年起 ECS 也提供不需要 CodeDeploy 的內建 blue/green 部署（後續加入 canary 與 linear），概念相同：兩組 target group、驗證 hook、bake time 與自動 rollback。

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:ap-northeast-1:111122223333:task-definition/payments:42"
        LoadBalancerInfo:
          ContainerName: "payments"
          ContainerPort: 8080
Hooks:
  - AfterAllowTestTraffic: "arn:aws:lambda:ap-northeast-1:111122223333:function:payments-smoke-test"
```

這是 CodeDeploy 部署 ECS 用的 appspec：指定新的 task definition 與要接上 load balancer 的 container，並在 test listener 接上流量後呼叫一個 Lambda 跑 smoke test；Lambda 回報失敗時部署會停止並 rollback。

### Lambda：version、alias 與流量權重

Lambda 的部署建立在兩個概念上：

- **Version**：每次 publish 都產生一個不可變的版本（`1`、`2`、`3`……），程式碼與設定都被凍結。`$LATEST` 是唯一可以修改的版本。
- **Alias**：指向某個版本的具名指標，例如 `live → 7`。API Gateway、event source mapping 等呼叫者應該指向 alias 的 ARN，而不是固定版本，這樣切換版本時呼叫端不需要改設定。

Alias 可以設定 **weighted routing**，讓一部分呼叫導向另一個版本：

```bash
aws lambda update-alias \
  --function-name quote \
  --name live \
  --function-version 7 \
  --routing-config '{"AdditionalVersionWeights": {"8": 0.1}}'
```

這會讓 `live` 的 90% 呼叫走版本 7、10% 走版本 8。手動調整權重可行，但正式環境通常交給 **CodeDeploy**：設定 `LambdaCanary10Percent5Minutes`、`LambdaLinear10PercentEvery1Minute`、`LambdaAllAtOnce` 等部署設定，CodeDeploy 會自動調整 alias 權重、執行 `BeforeAllowTraffic`／`AfterAllowTraffic` 驗證 hook，並在 alarm 觸發時把 alias 切回舊版本。37.6 節的 SAM `DeploymentPreference` 就是幫你建立這一整套。

### API Gateway、Route 53、ALB 與 CloudFront

- **API Gateway canary release**：REST API 的 stage 可以設定 canary，把指定比例的請求導到新的 deployment，確認後 promote 成正式版本。
- **Route 53 weighted routing**（第 9 章）：兩筆同名記錄分別指向 blue 與 green 的 load balancer，用權重逐步移轉。優點是可以跨 Region、跨任何端點；缺點是**受 DNS 快取影響**，客戶端可能在 TTL 甚至更久之後才換過去，退回也不是立即生效。
- **ALB weighted target groups**：一個 listener rule 把流量依權重轉到兩個 target group，例如 blue 90%、green 10%。切換在 load balancer 上立即生效，不受 DNS 快取影響，還可以搭配 target group stickiness 讓同一使用者固定在同一版本。
- **CloudFront continuous deployment**：建立 staging distribution，以權重或特定 header 把部分流量導過去測試新的 CDN 設定，再 promote 到 primary distribution。

## 37.10 Feature flags 與 AppConfig：把部署和發布分開

即使有了 canary，「部署新程式」和「讓使用者看到新功能」仍然綁在一起。Wanderly 的行銷團隊想在雙十一凌晨零點準時開放新的優惠券功能，但沒人想在凌晨零點部署程式。

**Feature flag（功能旗標）** 的做法是：新功能的程式碼先部署上線，但被一個設定開關包住；開關關閉時走舊邏輯。到了發布時間只要改設定，不需要重新部署。有問題時把開關關掉，比退回程式版本快得多。這把**部署（deploy，程式碼上線）**和**發布（release，使用者看到）**拆成兩個獨立的動作。

**AWS AppConfig**（Systems Manager 的一部分）是 AWS 受管的設定與 feature flag 服務：

- **結構**：application → environment（例如 prod）→ configuration profile。Profile 可以是 **feature flag** 類型（定義旗標與屬性，例如優惠券折扣上限），或任意格式的設定（JSON、YAML、文字）。
- **Validators**：部署設定前先以 JSON Schema 或 Lambda 驗證內容，避免一個打錯的設定讓整個服務掛掉。
- **Deployment strategy**：設定也像程式一樣逐步推出，指定部署總時間、成長方式（linear 或 exponential）、每步比例，以及最後的 **bake time**。
- **Monitor 與自動 rollback**：部署期間指定 CloudWatch alarm，alarm 觸發時 AppConfig 自動把設定退回上一版。
- **AppConfig Agent**：以 Lambda extension 或 ECS／EKS sidecar 形式在本地快取設定並定期輪詢，應用程式只要讀取本機端點，不必每次呼叫 API。

| 機制 | 適合放什麼 | 是否需要重新部署 |
|---|---|---|
| 程式碼 | 業務邏輯 | 是 |
| CloudFormation 參數 | 基礎設施規格（instance type、Multi-AZ） | 是（stack 更新） |
| Parameter Store／Secrets Manager | 連線字串、機密 | 視應用程式讀取方式 |
| AppConfig feature flag | 功能開關、漸進開放、執行期參數 | 否，且有驗證、漸進推出與自動 rollback |

## 37.11 Service Catalog：讓團隊自助取得經核准的架構

Wanderly 有十幾個產品團隊，每個團隊都想自己開環境。平台團隊面臨兩難：給大家 AdministratorAccess 太危險，每個請求都由平台團隊手動處理又太慢。

**AWS Service Catalog** 讓平台團隊把經過審核的 CloudFormation template（也支援 Terraform）包裝成 **product（產品）**，放進 **portfolio（產品組合）**，再授權給特定的 IAM 使用者、群組或角色。使用者在 Service Catalog 中選擇產品、填入允許的參數就能自助部署，得到的是符合公司標準的架構。

關鍵的設計元素是 **constraint（限制）**：

- **Launch constraint**：指定一個 IAM role，Service Catalog 以這個 role 的權限去建立資源。使用者本身**不需要**擁有建立 EC2、RDS 等資源的權限，只需要能使用 Service Catalog 的產品，這是最常考的重點。
- **Template constraint**：限制使用者可選的參數值，例如 instance type 只能選 `t4g.medium` 或 `m7g.large`。
- **Notification constraint**：把產品的 stack 事件送到 SNS。
- **StackSet constraint**：讓產品以 StackSets 部署到多個帳號與 Region。
- **TagOptions**：強制或預設套用的 tag，方便成本分攤（第 39 章）。

Portfolio 可以分享給其他帳號，或分享給整個 AWS Organization 或特定 OU，由各帳號匯入使用。產品可以有多個版本，平台團隊推出新版時，使用者可以把已部署的產品更新到新版本。Control Tower 的 Account Factory 就是以 Service Catalog 產品的形式提供「申請新帳號」（第 14、40 章）。

## 37.12 比較與選型

### IaC 工具怎麼選

```text
需要描述 AWS 基礎設施
├─ 主要是 serverless（Lambda、API Gateway、DynamoDB）→ SAM（底層仍是 CloudFormation）
├─ 團隊偏好用程式語言、需要抽象與重用 → CDK（synth 成 CloudFormation）
├─ 需要多雲一致工具或已有 Terraform 投資 → Terraform
└─ 其他 → CloudFormation YAML／JSON
       │
       ├─ 同一份基線要部署到很多帳號與 Region → StackSets（Organizations 用 service-managed）
       ├─ 可重複使用的元件 → nested stacks／modules
       ├─ 不同團隊、獨立生命週期之間傳值 → Export／ImportValue
       ├─ CloudFormation 沒有的資源或動作 → custom resource（Lambda）
       └─ 讓其他團隊自助部署經核准的架構 → Service Catalog（launch constraint）
```

### 部署策略怎麼選

| 情境 | 建議策略 |
|---|---|
| Dev／測試環境，追求最快 | All-at-once |
| 成本敏感、可接受容量暫時下降與新舊並存 | Rolling |
| 不能降容量、可接受新舊並存 | Rolling with additional batch |
| 要求退回快且乾淨、不碰既有機器 | Immutable |
| 要求幾乎即時退回、可負擔兩套環境 | Blue/green |
| 先讓少數流量驗證新版、依指標自動退回 | Canary（Lambda／ECS 用 CodeDeploy；Beanstalk 用 traffic splitting） |
| 想逐步、均勻地增加曝險 | Linear |
| 想在不重新部署的情況下開關功能 | Feature flag（AppConfig） |

### 流量切換機制比較

| 機制 | 粒度 | 生效速度 | 適用 |
|---|---|---|---|
| Lambda alias 權重 | 每次呼叫 | 立即 | Lambda 版本切換 |
| ALB weighted target groups | 每個請求 | 立即 | EC2／ECS 在同一 ALB 後 |
| Route 53 weighted records | DNS 查詢 | 受 TTL 與快取影響 | 跨 Region、跨端點、整個環境 |
| Beanstalk swap URLs | 環境 CNAME | 受 DNS 快取影響 | Beanstalk 環境 |
| API Gateway canary | 每個請求 | 立即 | REST API stage |

## 37.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 環境不一致、可重複建立、版本控制基礎設施 | CloudFormation（或 CDK／SAM）IaC |
| 更新前先看會不會替換資料庫 | Change set（檢查 Replacement） |
| 刪除 stack 或 replacement 時保留資料 | DeletionPolicy／UpdateReplacePolicy：Retain 或 Snapshot |
| 防止某資源在 stack 更新中被替換或刪除 | Stack policy |
| 防止整個 stack 被誤刪 | Termination protection |
| 找出有人在 console 手動改過的設定 | Drift detection |
| 部署後 alarm 觸發就退回基礎設施變更 | CloudFormation rollback triggers |
| `UPDATE_ROLLBACK_FAILED` | 修正原因後 continue update rollback（必要時跳過資源） |
| 同一份 template 部署到 Organization 所有帳號，新帳號自動套用 | StackSets（service-managed、automatic deployment） |
| 網路 stack 的 VPC ID 給多個應用 stack 使用 | Outputs Export + `Fn::ImportValue` |
| CloudFormation 不支援的資源或要呼叫外部 API | Custom resource（Lambda-backed） |
| 用 TypeScript／Python 寫基礎設施 | CDK（需 `cdk bootstrap`） |
| Serverless 應用簡化 template、Lambda canary | SAM（`AutoPublishAlias` + `DeploymentPreference`） |
| Lambda 先導 10% 流量再全部切換、alarm 時自動退回 | CodeDeploy canary + Lambda alias |
| 不降容量、退回最乾淨（Beanstalk） | Immutable deployment |
| Beanstalk 藍綠、退回快 | Clone 環境 + swap environment URLs |
| 藍綠切換不受 DNS 快取影響 | ALB weighted target groups（而非 Route 53 weighted） |
| 不重新部署就開關功能、漸進開放、自動退回 | AppConfig feature flags |
| 讓開發者自助部署標準架構但不給底層權限 | Service Catalog + launch constraint |
| 應用版本與資料庫 schema 同時變更 | Expand/contract（向後相容的 schema 變更） |

**常見陷阱**：

1. 以為 change set 能保證執行成功或驗證應用程式行為。它只預覽 CloudFormation 打算做的變更。
2. 只設 DeletionPolicy 就以為資料庫安全。更新造成的 replacement 要靠 UpdateReplacePolicy，且應同時開啟資源本身的 deletion protection。
3. 以為 CodePipeline 會編譯或部署。它只編排，build 是 CodeBuild，部署是 CodeDeploy、CloudFormation、ECS 等。
4. 以為 drift detection 會自動修正偏移，或能偵測所有屬性。它只回報支援偵測、且 template 中有定義的屬性。
5. 用 Route 53 weighted 做「立即退回」的藍綠。DNS 快取會讓退回延遲，需要立即生效時用 ALB 權重或 Lambda alias。
6. 以為 blue/green 能解決資料庫 schema 不相容。兩個版本共用資料庫時，schema 變更必須向後相容。

## 37.14 SAP 加深：多帳號、多 Region 的發布治理

SAP 題目會把本章所有元件放進一個大型組織：工具帳號中的 pipeline 要部署到數十個 workload 帳號、多個 Region，且要符合安全與稽核要求。

### 跨帳號 pipeline

標準做法是把 CodePipeline 放在專用的**工具帳號（tooling／deployment account）**，部署到 dev、staging、prod 帳號：

1. **Artifact 加密**：pipeline 的 artifact bucket 使用 **customer managed KMS key**，並在 key policy 中允許目標帳號的角色解密。AWS managed key 的 key policy 無法修改，不能用於跨帳號存取。Bucket policy 也要允許目標帳號的角色讀取。
2. **跨帳號角色**：在每個目標帳號建立一個信任工具帳號的角色，讓 pipeline 的 action 能 assume 它；CloudFormation deploy action 再搭配目標帳號中的 CloudFormation service role 實際建立資源。
3. **最小權限分離**：pipeline 角色、build 角色、部署角色各自獨立，任何一個被濫用時影響範圍有限。
4. **Build once, promote many**：同一個 artifact（image digest、template）依序推進各環境，每個環境只差參數。

CDK 的 **CDK Pipelines** 把這套跨帳號流程封裝成 construct，目標帳號用 `cdk bootstrap --trust <工具帳號>` 建立信任；pipeline 也能 self-mutate，在 pipeline 定義改變時先更新自己。

### 多 Region 分波部署

在多 Region 架構（第 42 章）中，一次更新所有 Region 會讓一個壞版本變成全球事故。常見的模式是**分波（waves）**：先部署到一個流量較小的 Region，經過 bake time 並確認 alarm 正常後，再部署到下一批 Region。CodePipeline 支援在 action 中指定目標 Region（cross-Region actions），StackSets 的 operation preferences 可以控制 Region 順序與並行數。每一波都應有自動 rollback 條件，而且 rollback 只影響該波。

### 治理：不可繞過的防線

- **CloudFormation Hooks**：在服務端檢查每一個資源操作，例如拒絕建立未加密的 bucket，不論是誰、從哪個 pipeline 部署。
- **SCP**（第 14 章）：限制 workload 帳號中的人類角色不得直接修改特定資源，只允許 pipeline 角色修改，從根本減少 drift。
- **Service Catalog + StackSets**：由平台團隊提供核准的 product，透過 portfolio 分享給 OU。
- **AWS Config**（第 16 章）：持續偵測不合規資源，作為最後一道偵測防線。

> [!sap] SAP 加深
> 題目若同時要求「開發者能自助部署」與「只能部署核准的架構」與「開發者不能直接擁有建立資源的權限」，答案組合通常是 Service Catalog（launch constraint）或「pipeline + CloudFormation service role + SCP 限制直接修改」。若再加上「所有新帳號自動具備基線」，加入 StackSets 的 service-managed automatic deployment 或 Control Tower（第 40 章）。

## 本章重點整理

- IaC 以宣告式文字檔描述資源，讓環境可重現、可 review、可追蹤，並讓災難後的重建只需重新部署。
- CloudFormation template 只有 `Resources` 是必要區段；`Parameters` 與 `Conditions` 讓同一份 template 部署多個環境，`Outputs` 的 `Export` 可供其他 stack 引用。
- 機密不能寫在 template 裡；使用服務自管密碼、dynamic reference（Secrets Manager／Parameter Store）或 `NoEcho` 參數。
- 更新屬性可能造成 replacement；prod 更新前用 change set 檢查 Replacement，且 change set 不保證執行成功。
- DeletionPolicy 處理刪除時的資源命運，UpdateReplacePolicy 處理 replacement 時的舊資源，兩者都應為有狀態資源設定為 Retain 或 Snapshot。
- Stack policy 防止更新時替換或刪除特定資源，termination protection 防止整個 stack 被刪除。
- 更新失敗會自動 rollback；rollback triggers 可依 CloudWatch alarm 退回；`UPDATE_ROLLBACK_FAILED` 要修正原因後 continue update rollback。
- Drift detection 找出手動修改的屬性但不會自動修正；搭配 SCP 限制人工修改能從源頭減少 drift。
- Nested stacks 用於重複使用元件，cross-stack references 用於獨立 stack 之間傳值；StackSets 把同一份 template 部署到多帳號、多 Region，service-managed 模式可對新帳號自動部署。
- CDK 與 SAM 都會轉換成 CloudFormation；CDK 部署前要 bootstrap，SAM 的 `DeploymentPreference` 會自動設定 CodeDeploy 的 Lambda canary。
- CodePipeline 只負責編排，CodeBuild 負責建置測試，CodeDeploy 負責 EC2、Lambda、ECS 的部署與依 alarm 自動 rollback。
- Rolling 省錢但降容量且新舊並存，immutable 退回乾淨，blue/green 退回最快但要兩套環境，canary 與 linear 以流量比例控制曝險。
- 藍綠或 canary 期間新舊版本共用資料庫，schema 變更必須以 expand/contract 保持向後相容。
- AppConfig feature flags 把部署與發布分開，提供驗證、漸進推出與依 alarm 自動 rollback。
- Service Catalog 以 launch constraint 讓使用者在沒有底層資源權限的情況下自助部署經核准的 product，portfolio 可分享給整個 Organization。

## 本章練習題

### 練習 37-1｜SAA｜單選｜預覽 stack 更新

Wanderly 的 prod 訂單資料庫由 CloudFormation stack 管理。一位工程師修改了 template 中 RDS DB instance 的數個屬性，準備更新 stack。主管要求在實際執行之前，必須先確認這次更新是否會造成資料庫被替換（建立新 instance 並刪除舊的）。

最合適的做法是什麼？

- A. 先對 stack 執行 drift detection，確認資料庫是否會被替換
- B. 直接更新 stack，並啟用 termination protection 以防資料庫被刪除
- C. 建立 change set，檢查資料庫資源的 Replacement 欄位是否為 True 或 Conditional，確認後再執行
- D. 在 staging 先刪除再重建 stack，觀察資料庫是否被重建

> [!answer]- 答案：C
> **A ✗** Drift detection 比較的是「目前實際設定」與「目前 template」，用來找手動修改；它不會預測「新 template」執行後會發生什麼。
>
> **B ✗** Termination protection 只防止整個 stack 被刪除，無法防止更新造成的 replacement，也不能讓你在執行前看到影響。
>
> **C ✓** Change set 會在不執行的情況下列出每個資源將被新增、修改或刪除，以及修改是否需要 replacement。檢查有狀態資源的 Replacement 欄位，是 prod 更新前的標準做法。
>
> **D ✗** 刪除重建 staging 無法預測 prod 更新的行為（更新與建立是不同的路徑），而且耗時又有風險。
>
> **考點**：SAA-2.2｜CloudFormation change set 與 replacement

### 練習 37-2｜SAA｜單選｜刪除 stack 時保留資料

Wanderly 要拆除一個舊的行銷活動環境，該環境由一個 CloudFormation stack 建立，包含 EC2、ALB 與一個 RDS for MySQL 資料庫。法務要求資料庫的最終資料必須保留，以備日後查詢，但不需要讓資料庫繼續運作以節省成本。團隊希望未來類似的 stack 都能自動處理這個需求。

最合適的做法是什麼？

- A. 在 template 中為 RDS 資源設定 `DeletionPolicy: Snapshot`，更新 stack 後再刪除 stack
- B. 為 stack 設定 stack policy，Deny 資料庫的 `Update:Delete`
- C. 為 stack 啟用 termination protection
- D. 刪除 stack 前在 RDS 設定 `DeletionProtection: true`

> [!answer]- 答案：A
> **A ✓** DeletionPolicy 為 Snapshot 時，CloudFormation 在刪除 RDS 資源前會先建立最終 snapshot，資料得以保留而資料庫本身不再產生費用。寫在 template 中，未來的 stack 都會自動套用。（單一 RDS DB instance 即使沒寫，預設也是 Snapshot；但明確寫出才不會依賴容易被誤解的預設值，也適用於其他支援 snapshot 的資源。）
>
> **B ✗** Stack policy 只在 stack「更新」時生效，不會影響刪除整個 stack 時資源的處理方式。
>
> **C ✗** Termination protection 會讓刪除 stack 的操作直接失敗，無法達成「拆除環境」的目的。
>
> **D ✗** 資源的 deletion protection 會讓 CloudFormation 刪除資料庫失敗、stack 刪除卡住，資料庫仍持續運作與計費，沒有達成節省成本的目標。
>
> **考點**：SAA-2.2、SAA-4.3｜DeletionPolicy Snapshot

### 練習 37-3｜SAA｜單選｜找出手動修改

Wanderly 的 staging 與 prod 環境由同一份 CloudFormation template 建立，但團隊懷疑過去事故處理時，有人在 console 上直接修改了 prod 的 SQS queue 與 security group 設定。團隊想找出哪些資源的哪些屬性和 template 不一致，再決定要把修改寫回 template 還是覆蓋掉。

應使用哪個功能？

- A. 建立 change set，比較 template 與實際設定
- B. 對 prod stack 執行 drift detection，檢視被標記為 MODIFIED 的資源與差異屬性
- C. 啟用 stack policy，阻止未來的手動修改
- D. 檢視 stack events，找出最近的 UPDATE 事件

> [!answer]- 答案：B
> **A ✗** Change set 預覽的是「提交新 template 後 CloudFormation 打算做的變更」，不是用來報告實際資源與目前 template 的偏移。
>
> **B ✓** Drift detection 比對 stack 中資源的實際設定與 template 定義的預期值，列出 MODIFIED、DELETED 的資源及差異屬性。它只負責發現，後續由團隊決定更新 template 或重新部署覆蓋。
>
> **C ✗** Stack policy 只限制透過 CloudFormation 的 stack 更新，不會阻止有人直接在 console 修改資源，也無法找出既有的偏移。
>
> **D ✗** Stack events 只記錄 CloudFormation 自己執行的操作，console 上的手動修改不會出現在其中。
>
> **考點**：SAA-2.2｜CloudFormation drift detection

### 練習 37-4｜SAP｜單選｜多帳號基線部署

Wanderly 使用 AWS Organizations 管理 60 個帳號，並持續新增。安全團隊有一份 CloudFormation template，會建立稽核用 IAM role 與數條 Config rules，必須部署到 `Workloads` OU 下所有帳號的東京與新加坡 Region。新帳號加入該 OU 時要自動部署，且團隊不想在每個帳號手動建立部署所需的 IAM 角色。

最合適的做法是什麼？

- A. 使用 self-managed permissions 的 StackSets，在每個帳號建立 `AWSCloudFormationStackSetExecutionRole`
- B. 在每個帳號以 CodePipeline 部署該 template，新帳號建立時由人工新增 pipeline
- C. 把 template 包成 Service Catalog product 分享給 OU，請各帳號管理員自行部署
- D. 使用 service-managed permissions 的 StackSets，以 `Workloads` OU 為部署目標、選擇兩個 Region，並啟用 automatic deployment

> [!answer]- 答案：D
> **A ✗** Self-managed 模式需要在每個目標帳號手動建立 execution role 與信任關係，新帳號也不會自動部署，違反題目要求。
>
> **B ✗** 每個帳號一條 pipeline 營運負擔很大，新帳號仍需人工處理。
>
> **C ✗** Service Catalog 是讓使用者自助選擇部署，無法保證每個帳號都部署，也不會自動套用到新帳號。
>
> **D ✓** Service-managed StackSets 與 Organizations 整合，以 OU 為目標並由服務自動建立所需角色；啟用 automatic deployment 後，新帳號加入 OU 時會自動在指定 Region 建立 stack instance。
>
> **考點**：SAP-1.4、SAP-2.1｜StackSets service-managed 與 automatic deployment

### 練習 37-5｜SAA｜單選｜Lambda 漸進部署

Wanderly 的報價 API 由 API Gateway 與一個 Lambda 函式組成，以 SAM 部署。團隊希望新版本先只接收 10% 的請求 5 分鐘，若期間錯誤率 alarm 沒有觸發才把全部流量切過去；若 alarm 觸發就自動回到舊版本，且不想自己寫切換流量的程式。

最合適的做法是什麼？

- A. 在 SAM template 為函式設定 `AutoPublishAlias` 與 `DeploymentPreference`（Type 為 `Canary10Percent5Minutes`，Alarms 指定錯誤率 alarm），讓 API Gateway 呼叫 alias
- B. 建立兩個獨立的 Lambda 函式，並在 Route 53 以 weighted records 各分配 10% 與 90% 流量
- C. 每次部署時直接更新 `$LATEST`，並設定 CloudWatch alarm 在錯誤率升高時通知工程師手動退回
- D. 在 API Gateway 啟用 caching，降低新版本收到的請求比例

> [!answer]- 答案：A
> **A ✓** `AutoPublishAlias` 每次變更都發布新版本並更新 alias；`DeploymentPreference` 會自動建立 CodeDeploy 部署，以 canary 方式調整 alias 權重，並在指定 alarm 觸發時自動把 alias 切回舊版本，完全不需要自己寫切換程式。
>
> **B ✗** Route 53 weighted 作用於 DNS 層，無法直接指向 Lambda 函式版本，而且受 DNS 快取影響、沒有依 alarm 自動退回的機制。
>
> **C ✗** 直接更新 `$LATEST` 等於 all-at-once，所有請求立刻使用新版本，退回也要人工處理，不符需求。
>
> **D ✗** Caching 會讓部分請求不呼叫 Lambda，但無法控制「哪個版本」處理請求，與漸進部署無關。
>
> **考點**：SAA-2.2、SAA-2.1｜Lambda alias、SAM 與 CodeDeploy canary

### 練習 37-6｜SAA｜單選｜Beanstalk 部署政策

Wanderly 的會員服務跑在 Elastic Beanstalk 上，有 8 台 instance。過去使用 rolling 部署時，曾有新版本在更新一半時才發現 bug，退回又花了 20 分鐘，期間容量也下降。團隊要求：部署期間容量不得下降、新版本有問題時能快速且乾淨地退回、不想維護兩個長期存在的環境。

應選擇哪個部署政策？

- A. Rolling with additional batch
- B. All at once
- C. Immutable
- D. Rolling，並把 batch size 調小為 1 台

> [!answer]- 答案：C
> **A ✗** 能維持容量，但仍然是逐批修改既有 instance，新舊版本並存，退回時要再滾動一次，不夠快也不夠乾淨。
>
> **B ✗** 一次更新全部 instance，部署期間可能中斷服務，新版有問題時全部使用者受影響。
>
> **C ✓** Immutable 在暫時的新 Auto Scaling group 啟動一組新 instance，全部健康後才移入環境並終止舊 instance。既有 instance 沒被修改，容量不會下降；若新 instance 未通過健康檢查，只要終止它們即可退回，也不需要長期維護第二個環境。
>
> **D ✗** 縮小 batch 只會讓部署更慢，仍有容量下降與退回緩慢的問題。
>
> **考點**：SAA-2.2｜Elastic Beanstalk immutable deployment

### 練習 37-7｜SAA｜單選｜藍綠切換不受 DNS 快取影響

Wanderly 的搜尋服務跑在 EC2 Auto Scaling group 上，前面是一個 ALB。團隊準備以 blue/green 方式部署新版本：green 是另一個 Auto Scaling group。團隊希望先把 10% 流量導到 green，觀察後逐步增加；出問題時要能立即把所有流量切回 blue，不能等待客戶端的 DNS 快取過期。

最合適的做法是什麼？

- A. 為 green 建立新的 ALB，在 Route 53 以 weighted records 分配 blue 90%、green 10%
- B. 把 green 註冊到新的 target group，在 ALB listener rule 使用 weighted target groups 分配 blue 90%、green 10%，再逐步調整權重
- C. 把 green instance 直接加入 blue 的 target group，依 instance 數量比例分配流量
- D. 使用 Elastic Beanstalk 的 swap environment URLs 功能切換

> [!answer]- 答案：B
> **A ✗** Route 53 weighted records 可以做藍綠，但切換受 DNS TTL 與客戶端快取影響，退回不會立即生效，違反需求。
>
> **B ✓** ALB 的 weighted target groups 在 load balancer 上依權重分配每個請求，調整權重立即生效，不經過 DNS，最適合需要即時退回的藍綠與 canary。
>
> **C ✗** 混在同一個 target group 中只能靠 instance 數量粗略控制比例，退回要移除 instance，無法精準且立即地切回。
>
> **D ✗** Swap environment URLs 是 Elastic Beanstalk 環境的功能，題目的服務不在 Beanstalk 上；而且它交換 CNAME，同樣受 DNS 快取影響。
>
> **考點**：SAA-2.2、SAA-3.4｜ALB weighted target groups 與 Route 53 weighted 的差異

### 練習 37-8｜SAA｜選兩項｜Template 中的機密

Wanderly 的 CloudFormation template 需要為一個 Lambda 函式設定第三方金流商的 API key，以及建立一個 RDS 資料庫的管理員密碼。安全審查發現目前兩個值都以預設值寫在 template 的 Parameters 中，並出現在 Outputs 裡方便查詢。Template 存放在 Git repository。

哪兩個做法能改善這個問題？（選兩項）

- A. 把 template 改為 JSON 格式並以 base64 編碼機密值
- B. 把 API key 存在 Secrets Manager，讓 Lambda 在執行期間依 secret 名稱讀取，template 只傳入 secret 的 ARN
- C. 把機密值移到 `Mappings` 區段，因為 Mappings 不會顯示在 console
- D. 為 RDS 設定 `ManageMasterUserPassword: true`，由 RDS 在 Secrets Manager 中產生並管理密碼，並從 Outputs 移除所有機密
- E. 為機密參數設定 `NoEcho: true`，並保留其在 Outputs 中以便查詢

> [!answer]- 答案：B、D
> **A ✗** Base64 是編碼不是加密，任何人都能還原，機密仍然存在 Git 中。
>
> **B ✓** 機密留在 Secrets Manager，template 只包含 ARN，Lambda 執行期間以 IAM 權限讀取。Git、console 與 stack 參數中都不會出現 API key，也方便輪替。
>
> **C ✗** Mappings 是 template 的一部分，同樣會進入 Git，也能從 template 內容中讀到。
>
> **D ✓** RDS 自管主密碼會在 Secrets Manager 中產生與輪替，template 中完全不需要密碼值；同時從 Outputs 移除機密，避免任何能讀取 stack 的人看到。
>
> **E ✗** NoEcho 能遮蔽參數顯示，但放進 Outputs 會讓值被輸出；而且預設值仍寫在 template 中。
>
> **考點**：SAA-1.3、SAA-1.2｜IaC 中的機密管理

### 練習 37-9｜SAA｜單選｜CloudFormation 做不到的步驟

Wanderly 用 CloudFormation 建立付款服務。每次建立新環境時，還需要呼叫第三方金流商的 API 註冊一個 callback URL，刪除環境時也要取消註冊。目前這一步由工程師手動執行，常常忘記。團隊希望這一步成為 stack 生命週期的一部分。

最合適的做法是什麼？

- A. 在 Outputs 中輸出 callback URL，由工程師在部署完成後手動註冊
- B. 在 EC2 的 user data 中呼叫金流商 API 註冊
- C. 使用 nested stack 把註冊步驟獨立出來
- D. 建立以 Lambda 實作的 custom resource，在 Create 時註冊、Delete 時取消註冊，並一律把結果回報到 CloudFormation 提供的 response URL

> [!answer]- 答案：D
> **A ✗** 仍然依賴人工，正是目前常常忘記的原因。
>
> **B ✗** User data 在每台 instance 啟動時執行，Auto Scaling 擴展時會重複註冊，刪除 stack 時也不會取消註冊；它不屬於 stack 的生命週期。
>
> **C ✗** Nested stack 只是把資源拆到子 template，本身不會呼叫外部 API；CloudFormation 仍然沒有對應的資源類型。
>
> **D ✓** Custom resource 讓 CloudFormation 在 Create、Update、Delete 時呼叫 Lambda 執行任意邏輯。Lambda 必須回報 SUCCESS 或 FAILED 到 response URL，否則 stack 會一直等到逾時；Delete 時取消註冊可以避免留下外部孤兒設定。
>
> **考點**：SAA-2.1｜CloudFormation custom resource

### 練習 37-10｜SAA｜單選｜不重新部署就開放新功能

Wanderly 的行銷團隊希望新的優惠券功能在週六凌晨零點準時開放，先開放給 10% 使用者，30 分鐘內逐步擴大到全部。若錯誤率 alarm 觸發，要在一分鐘內自動關閉功能。工程團隊不希望在凌晨部署程式碼，也不想自建設定系統。

最合適的做法是什麼？

- A. 預先部署包含新功能的程式，並以 AWS AppConfig feature flag 包住新功能；零點以含 bake time 的漸進 deployment strategy 開啟旗標，並設定錯誤率 alarm 作為 monitor 以自動 rollback
- B. 在零點以 CodeDeploy canary 部署新版本程式，10% 流量 30 分鐘後全部切換
- C. 把功能開關存在 Parameter Store，並以 EventBridge Scheduler 在零點觸發 Lambda 修改參數值
- D. 在零點以 CloudFormation 更新 Lambda 的環境變數開啟功能

> [!answer]- 答案：A
> **A ✓** Feature flag 把「部署程式」與「開放功能」分開，程式可以事先上線；AppConfig 提供漸進推出的 deployment strategy，並可指定 CloudWatch alarm 為 monitor，alarm 觸發時自動退回設定，不需自建系統。
>
> **B ✗** 這仍然是在凌晨部署程式碼，違反需求；canary 控制的是「哪個版本處理請求」，而不是對使用者開放功能。
>
> **C ✗** 可以在零點切換，但沒有內建的漸進開放與依 alarm 自動退回，需要自己寫邏輯，等於自建設定系統。
>
> **D ✗** 更新環境變數會發布新的函式設定，等同一次部署；也沒有漸進開放與自動退回。
>
> **考點**：SAA-2.2｜AppConfig feature flags

### 練習 37-11｜SAA｜單選｜自助部署但不給底層權限

Wanderly 的資料科學團隊經常需要建立標準的分析環境（EC2、S3 bucket、IAM role），平台團隊已寫好符合公司規範的 CloudFormation template。公司規定資料科學家的 IAM 角色不得擁有建立 EC2 或 IAM role 的權限，但他們要能隨時自助建立這個環境，且只能選擇核准的 instance type。

最合適的做法是什麼？

- A. 給資料科學家的角色加上 `AdministratorAccess`，並以 CloudTrail 監控他們的操作
- B. 把 template 建立為 Service Catalog product 放進 portfolio，以 launch constraint 指定一個有建立資源權限的 IAM role，以 template constraint 限制 instance type，再把 portfolio 授權給資料科學家的角色
- C. 把 template 存在 S3，讓資料科學家用 CloudFormation console 自行部署
- D. 讓資料科學家提交工單，由平台團隊手動部署 stack

> [!answer]- 答案：B
> **A ✗** 給予管理員權限直接違反公司規定，事後監控無法防止錯誤或濫用。
>
> **B ✓** Launch constraint 讓 Service Catalog 以指定的 IAM role 建立資源，使用者本身不需要底層服務的權限；template constraint 限制可選參數值。使用者只要能使用該 portfolio 的 product 就能自助部署。
>
> **C ✗** 直接用 CloudFormation 部署時，使用者需要擁有建立 template 中所有資源的權限（除非另外設定 service role），且無法限制參數選項。
>
> **D ✗** 可以符合權限規定，但不是自助，平台團隊會成為瓶頸。
>
> **考點**：SAA-1.1、SAA-2.1｜Service Catalog launch constraint

### 練習 37-12｜SAP｜單選｜跨團隊共享網路資源

Wanderly 的網路團隊以一個 CloudFormation stack 管理 prod VPC 與 subnet，這個 stack 每年只更新幾次。八個應用團隊各自有自己的 stack，需要引用 VPC ID 與 subnet ID，且各自以不同頻率獨立部署。網路團隊要求應用團隊的部署不能觸發網路 stack 的更新，也要防止網路 stack 意外刪除仍被使用的 subnet。所有 stack 都在同一帳號與 Region。

最合適的做法是什麼？

- A. 把網路資源改成每個應用 stack 的 nested stack，讓每個應用 stack 擁有自己的網路
- B. 讓應用團隊在 template 中寫死 VPC ID 與 subnet ID
- C. 在網路 stack 的 Outputs 以 Export 輸出 VPC 與 subnet ID，應用 stack 以 `Fn::ImportValue` 引用
- D. 把所有應用資源與網路資源合併到同一個 stack，由網路團隊統一部署

> [!answer]- 答案：C
> **A ✗** Nested stack 會讓每個應用 stack 各自建立一份網路資源，變成八套網路，而且網路的更新會綁進應用部署中，違反需求。
>
> **B ✗** 寫死 ID 可以運作，但網路變更時容易不一致，也沒有任何機制防止網路 stack 刪除仍在使用的 subnet。
>
> **C ✓** Cross-stack references 讓獨立生命週期的 stack 共享值：應用 stack 各自部署，不會更新網路 stack；只要某個 export 仍被 import，CloudFormation 就不允許刪除或修改它，保護了正在使用的 subnet。
>
> **D ✗** 合併成單一 stack 會讓所有團隊的部署綁在一起、互相影響，一個資源失敗就 rollback 全部。
>
> **考點**：SAP-2.1、SAP-3.1｜cross-stack references 與 nested stacks 的差異

### 練習 37-13｜SAP｜選兩項｜跨帳號 pipeline

Wanderly 在工具帳號中有一條 CodePipeline，artifact bucket 目前以 AWS managed key（`aws/s3`）加密。團隊要新增一個 stage，以 CloudFormation deploy action 把 artifact 中的 template 部署到 prod 帳號，但測試時 prod 帳號的角色無法解密 artifact。安全團隊要求維持加密，且 pipeline 不得使用長期 access key。

哪兩個步驟是必要的？（選兩項）

- A. 改用 customer managed KMS key 加密 artifact bucket，並在 key policy 中允許 prod 帳號的部署角色使用該 key 解密
- B. 關閉 artifact bucket 的加密，讓 prod 帳號可以直接讀取
- C. 在 prod 帳號建立 IAM user，把 access key 存入 CodePipeline 的環境變數
- D. 在 prod 帳號複製一份 artifact bucket，讓 CodePipeline 同時寫入兩個 bucket
- E. 在 prod 帳號建立信任工具帳號的跨帳號角色供 pipeline action assume，並允許該角色讀取 artifact bucket、把 CloudFormation service role 傳給 CloudFormation 部署

> [!answer]- 答案：A、E
> **A ✓** AWS managed key 的 key policy 無法修改，不能授權給其他帳號；改用 customer managed key 並在 key policy 中授權 prod 帳號的角色，才能跨帳號解密 artifact。
>
> **B ✗** 關閉加密直接違反安全團隊「維持加密」的要求；而且 prod 角色仍需要 bucket policy 授權才能讀取，問題並沒有真正解決。
>
> **C ✗** 長期 access key 有洩漏風險，且明確違反「不得使用長期 access key」。
>
> **D ✗** 複製 bucket 不能解決加密金鑰無法跨帳號使用的問題，還增加同步的複雜度。
>
> **E ✓** 跨帳號部署的標準做法是在目標帳號建立信任工具帳號的角色，讓 pipeline action 以暫時憑證 assume；這個角色要能讀取 artifact bucket（搭配 bucket policy），並把 CloudFormation service role 傳給 CloudFormation，在 prod 帳號中實際建立資源。
>
> **考點**：SAP-2.1、SAP-2.3｜跨帳號 CodePipeline、KMS key policy 與 assume role

### 練習 37-14｜SAP｜單選｜ECS 藍綠部署與驗證

Wanderly 的付款服務跑在 ECS Fargate 上，前面是 ALB。團隊目前使用 rolling update，但某次部署讓新舊版本同時處理請求，造成難以排查的資料不一致。新的要求是：新版本在接收任何正式流量之前，先透過另一個 port 跑自動化 smoke test；通過後以 10% 流量觀察 5 分鐘再全部切換；期間錯誤率 alarm 觸發就自動退回。

最合適的做法是什麼？

- A. 維持 rolling update，把 `minimumHealthyPercent` 設為 100、`maximumPercent` 設為 200，並啟用 deployment circuit breaker
- B. 建立第二個 ECS cluster 部署新版本，再用 Route 53 weighted records 分配 10% 流量
- C. 每次部署時建立新的 ALB 與 ECS service，以 Elastic Beanstalk swap environment URLs 切換
- D. 使用 blue/green 部署（例如以 CodeDeploy 作為 deployment controller）：準備兩個 target group、production listener 與 test listener，在 `AfterAllowTestTraffic` hook 執行 smoke test，使用 `ECSCanary10Percent5Minutes` 部署設定並指定錯誤率 alarm 自動 rollback

> [!answer]- 答案：D
> **A ✗** 這些參數能維持容量、circuit breaker 能偵測無法穩定的 task，但仍是 rolling：新舊版本同時處理正式流量，也沒有在接收正式流量前透過 test listener 驗證的機制。
>
> **B ✗** Route 53 weighted 受 DNS 快取影響，退回不即時；兩套 cluster 也沒有內建的驗證 hook 與自動 rollback。
>
> **C ✗** Swap environment URLs 是 Elastic Beanstalk 的功能，不適用於直接管理的 ECS service。
>
> **D ✓** ECS 的 blue/green 部署先在 green target group 啟動新版本，test listener 讓 smoke test 在正式流量進來前執行；canary 部署設定控制 10% 流量與 5 分鐘觀察期，alarm 觸發時自動把流量切回 blue。
>
> **考點**：SAP-2.1、SAP-3.4｜ECS blue/green 部署、test listener 與自動 rollback

### 練習 37-15｜SAP｜選兩項｜Schema 變更與藍綠部署

Wanderly 的會員服務要把資料表中的 `phone` 欄位改為兩個欄位 `country_code` 與 `phone_number`。服務以 blue/green 方式部署在 ECS 上，切換期間 blue 與 green 會共用同一個 Aurora 資料庫，而且公司要求切換後 24 小時內隨時可以退回 blue。

哪兩個做法能滿足需求？（選兩項）

- A. 在部署 green 的同一個時間點執行 migration，刪除 `phone` 欄位並建立新欄位，讓 schema 與 green 一致
- B. 先執行只新增 `country_code` 與 `phone_number` 欄位的 migration，保留 `phone` 欄位，讓 blue 與 green 都能運作
- C. 讓 green 版本同時寫入新舊欄位並回填既有資料；確認不再需要退回 blue 後，再以另一次部署移除 `phone` 欄位
- D. 為 green 建立一個獨立的新 Aurora cluster，切換後再把 blue 的資料匯入
- E. 在切換前停用 Aurora 自動備份，避免 migration 期間的 snapshot 影響效能

> [!answer]- 答案：B、C
> **A ✗** 一刪除 `phone`，仍在服務的 blue 會立刻壞掉；退回 blue 也不可能成功，因為欄位已經不存在。
>
> **B ✓** 這是 expand 階段：只做新增、向後相容的 schema 變更，舊版程式忽略新欄位仍能運作，新版程式可以開始使用新欄位。
>
> **C ✓** 新版同時寫入新舊欄位，確保退回 blue 時資料仍完整；退回期限過後才執行 contract（移除舊欄位），整個過程任何時候都能退回。
>
> **D ✗** 兩個資料庫在切換期間會分歧，blue 與 green 寫入的資料互不可見，退回時資料遺失或衝突。
>
> **E ✗** 停用備份會降低資料保護，與 schema 相容性問題無關。
>
> **考點**：SAP-2.1、SAP-3.4｜expand/contract schema 變更與藍綠部署

### 練習 37-16｜SAP｜單選｜UPDATE_ROLLBACK_FAILED

Wanderly 的一次 CloudFormation stack 更新失敗並開始 rollback，但 rollback 也失敗，stack 停在 `UPDATE_ROLLBACK_FAILED`。調查發現，事故期間有工程師在 console 上手動刪除了 stack 中的一個 Lambda 函式所使用的 IAM role，CloudFormation 無法把該函式恢復到舊設定。這個 stack 還管理著 prod 的資料庫與佇列，必須盡快恢復可操作狀態，且不能刪除 stack。

最合適的做法是什麼？

- A. 刪除整個 stack，再以舊版 template 重新建立
- B. 等待 CloudFormation 自動重試 rollback，直到成功為止
- C. 先修正根本原因（例如重新建立被刪除的 IAM role），再執行 continue update rollback；若某些資源確實無法恢復，可在 continue update rollback 時指定跳過它們
- D. 立即以新的 template 再次更新 stack，覆蓋失敗的狀態

> [!answer]- 答案：C
> **A ✗** 刪除 stack 可能刪除 prod 的資料庫與佇列（除非都設定 Retain），且題目明確要求不能刪除 stack。
>
> **B ✗** CloudFormation 不會在 `UPDATE_ROLLBACK_FAILED` 狀態下自動重試，問題的根本原因也還在。
>
> **C ✓** 處理 `UPDATE_ROLLBACK_FAILED` 的標準流程是先修正讓 rollback 失敗的原因，再執行 continue update rollback；若某些資源無法恢復，可以指定跳過，讓 stack 回到 `UPDATE_ROLLBACK_COMPLETE` 這個可再次更新的狀態，之後再修正 template 使其與實際一致。
>
> **D ✗** 處於 `UPDATE_ROLLBACK_FAILED` 的 stack 不能直接更新，必須先完成 rollback。
>
> **考點**：SAP-3.4、SAP-2.1｜CloudFormation rollback 失敗的復原
