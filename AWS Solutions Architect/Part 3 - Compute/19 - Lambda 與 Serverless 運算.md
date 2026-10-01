---
chapter: 19
title: Lambda：Serverless 運算
part: 3
---

# 第 19 章　Lambda：Serverless 運算、Concurrency 與事件驅動

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 Lambda 的執行模型：function、handler、execution environment 的一生，以及 cold start 從哪裡來
> - 分辨同步、非同步與 event source mapping 三種呼叫方式，知道每一種由誰負責重試、失敗的事件去了哪裡
> - 用 concurrency 的公式估算容量，正確使用 reserved concurrency、provisioned concurrency 與 SnapStart
> - 讓 Lambda 安全地存取 VPC 內的資源，並知道什麼時候需要 NAT Gateway、VPC endpoint 或 RDS Proxy
> - 設計 SQS／Kinesis 觸發的批次處理與部分失敗回報，分清 execution role 與 resource-based policy
> - 估算 Lambda 費用，判斷一個 workload 什麼時候不該用 Lambda
>
> **前置知識**：第 4 章（VM、container 與 serverless 的差異）、第 12 章（IAM role 與 policy）、第 18 章（容量與擴展的基本觀念）
> **考試比重**：SAA ★★★（Domain 2 鬆耦合、Domain 3 彈性運算、Domain 4 成本）｜SAP ★★☆（Domain 2 效能與成本、Domain 4 現代化）

## 19.1 故事：一天只忙兩小時的縮圖機群

第 18 章之後，Wanderly 的 web tier 已經能自動擴展。但帳單上還有一筆讓財務皺眉的費用：一個由 4 台 EC2 組成的 ASG，專門負責把旅館上傳的照片縮成三種尺寸。旅館大多在白天集中上傳，這組機器一天真正忙碌的時間大約只有兩小時，其餘時間都在空轉；而且它們還要定期 patch、維護 AMI、處理 Spot 中斷。

同一個月，金流團隊也提出需求：付款服務商會在每筆交易完成後呼叫 Wanderly 的一個 webhook，一天大約幾千次，但月底與連假時會瞬間湧入上萬次。為了這個 webhook 另外養一組 ASG 與 ALB，似乎不太划算。

工程師小林想到 **AWS Lambda**：照片一上傳到 S3 就自動觸發一段程式產生縮圖，沒有照片時完全不收運算費用；webhook 有請求才執行，流量暴增時 AWS 自動同時跑更多份。不需要選 instance type、不需要 AMI、不需要 Auto Scaling group。

但小林很快發現，Lambda 不是「把程式丟上去就好」。為什麼第一次呼叫特別慢？為什麼大量照片同時上傳時有些請求被拒絕？為什麼 function 放進 VPC 後就連不到付款服務商的 API？為什麼一個壞掉的訊息讓整個 queue 卡住？這一章就跟著小林，把這些問題一個一個弄清楚。

## 19.2 Serverless 與 Lambda：你只負責程式碼

**Serverless（無伺服器）** 不是真的沒有伺服器，而是**你不需要管理伺服器**：不選機型、不 patch 作業系統、不規劃容量；服務依實際使用量自動擴展，閒置時不收（或幾乎不收）運算費用。S3、DynamoDB、SQS 都是 serverless 服務，Lambda 則是 serverless 的「運算」。

**AWS Lambda** 是一個事件驅動的運算服務：你上傳一段程式碼（稱為 **function**），設定它在什麼事件發生時執行，Lambda 就會在事件發生時準備執行環境、執行程式、回傳結果。

### 幾個基本名詞

- **Function（函式）**：部署到 Lambda 的一個單位，包含程式碼、設定（記憶體、timeout、環境變數）與權限。
- **Handler（處理函式）**：function 裡被 Lambda 呼叫的進入點，例如 Python 的 `lambda_handler(event, context)`。每次呼叫，Lambda 就呼叫一次 handler。
- **Event（事件）**：觸發 function 的 JSON 資料，例如「S3 上有一個新物件，bucket 是 X、key 是 Y」，或一個 HTTP 請求的內容。
- **Runtime（執行環境語言）**：Lambda 提供的語言環境，例如 Python、Node.js、Java、.NET、Ruby；也可以用 **custom runtime** 或 container image 執行其他語言。
- **Trigger（觸發來源）**：會呼叫 function 的服務，例如 S3、API Gateway、EventBridge、SQS。

一個最簡單的縮圖 function 長這樣：

```python
import boto3
from PIL import Image

s3 = boto3.client("s3")          # 在 handler 外建立，可被後續呼叫重複使用

def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        local = f"/tmp/{key.split('/')[-1]}"
        s3.download_file(bucket, key, local)
        with Image.open(local) as img:
            img.thumbnail((400, 400))
            img.save(local)
        s3.upload_file(local, "wanderly-thumbnails", key)
    return {"processed": len(event["Records"])}
```

### 責任分擔：誰管什麼

使用 EC2 時，作業系統、執行環境、擴展都是你的事；使用 Lambda 時，這些都交給 AWS：

| 項目 | EC2（第 17 章） | Lambda |
|---|---|---|
| 作業系統 patch | 你 | AWS |
| Runtime 更新 | 你 | AWS（受管 runtime 會自動更新小版本；舊版本到期會被棄用，需自行升級） |
| 擴展 | 你設定 ASG | AWS 自動依事件數擴展 |
| 高可用 | 你部署多 AZ | AWS 自動在 Region 內多個 AZ 執行 |
| 程式碼、相依套件、IAM 權限、資料 | 你 | 你 |
| 收費單位 | Instance 執行時間 | 請求次數 + 執行時間 × 記憶體 |

注意最後一列之前的那一行：**程式碼的安全、相依套件的漏洞、IAM 權限是否過大，仍然是你的責任**（第 2 章的 shared responsibility model）。

## 19.3 Execution environment 的一生與 cold start

小林部署縮圖 function 後，發現第一次上傳照片要 2 秒才處理完，之後每張都只要 300 毫秒。要理解這個差異，必須知道 Lambda 在背後做了什麼。

### Execution environment

**Execution environment（執行環境）** 是 Lambda 執行 function 的一個隔離環境，底層是輕量級的虛擬機器（Firecracker microVM）。每個 execution environment **同一時間只處理一個請求**。它的生命週期分成三個階段：

```text
  事件到達，但沒有閒置的 execution environment
        │
        ▼
 ┌──────────────── Init 階段（cold start）────────────────┐
 │ ① 建立隔離環境、下載程式碼或 container image              │
 │ ② 啟動 runtime（例如 Python 直譯器、JVM）                 │
 │ ③ 執行 handler 外的初始化程式碼                            │
 │    （import 套件、建立 SDK client、讀取設定、建立連線）       │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌──────────────── Invoke 階段 ────────────────────────────┐
 │ ④ 呼叫 handler(event, context)，回傳結果                  │
 └───────────────────────────┬────────────────────────────┘
                             ▼
              ⑤ 環境保持閒置（frozen），等待下一個事件
                 ├─ 下一個事件到達 → 直接回到 ④（warm start）
                 └─ 閒置一段時間或 AWS 回收 → Shutdown 階段，環境銷毀
```

① 到 ③ 只在新建 execution environment 時發生，這段額外的延遲就是 **cold start（冷啟動）**。④ 是真正執行你的 handler。⑤ 執行完後環境不會馬上銷毀，而是被「凍結」保留一段時間；下一個事件若剛好分配到這個環境，就跳過 init 直接執行，稱為 **warm start**。AWS 不保證環境會保留多久。

Init 階段對一般 on-demand 的 function 有時間限制（約 10 秒）；Java 這類需要啟動 JVM、載入大量類別的 runtime，cold start 通常比 Python、Node.js 明顯更久。Container image、大型相依套件、在 init 時建立大量連線，也會讓 cold start 變長。

### 利用環境重用，但不要依賴它

環境重用帶來一個重要的寫法：**把昂貴的初始化放在 handler 外**。上面的縮圖範例把 `boto3.client("s3")` 放在 handler 外，它只在 init 時建立一次，之後每次 warm start 都直接使用。資料庫連線、讀取 Secrets Manager 的密碼（可以快取一段時間）、載入設定檔也是同理。

但重用只是效能優化，**不能當成正確性的保證**：

- 同一個 function 可能同時有幾百個 execution environment，每個都有自己的記憶體與 `/tmp`，彼此看不到。
- 環境隨時可能被回收，下一次呼叫可能是全新的環境。
- 因此，全域變數不能當計數器、`/tmp` 不能存使用者資料。需要保存的狀態要放到 S3、DynamoDB、ElastiCache 這類外部服務。

> [!warning] 常見誤解
> 「Lambda 是 stateless 的，所以每次呼叫都會重新初始化，把初始化放在 handler 外沒有意義。」剛好相反：環境經常被重用，放在 handler 外的初始化可以省下大量時間。真正的意思是「不能**依賴**狀態被保留」，而不是「狀態一定不會被保留」。

### 冷啟動的影響有多大？

對縮圖這種非同步的背景工作，偶爾多 1 秒完全無感；對使用者正在等待的 API，尤其是 Java function 或需要穩定低延遲的結帳流程，cold start 就值得處理。19.9 節會介紹 provisioned concurrency 與 SnapStart 這兩個對策。

## 19.4 資源設定：記憶體、CPU、timeout 與 /tmp

Lambda 沒有 instance type 可以選，只有一個主要旋鈕：**記憶體**。

### 記憶體決定 CPU

- 記憶體可設定 **128 MB 到 10,240 MB**，以 1 MB 為單位。
- **CPU 與網路頻寬依記憶體成比例分配**。大約在 1,769 MB 時相當於一個完整的 vCPU，最大設定時可用到 6 個 vCPU。你不能單獨調整 CPU。

這帶來一個反直覺的結果：**增加記憶體有時反而更便宜**。Lambda 依「記憶體 × 執行時間」計費。若一個 CPU 密集的縮圖 function 在 512 MB 時要跑 4 秒，調到 2,048 MB（四倍 CPU）後只要 0.9 秒：

| 記憶體 | 執行時間 | GB-秒（記憶體 GB × 秒） |
|---|---|---|
| 512 MB | 4.0 秒 | 0.5 × 4.0 = 2.0 |
| 2,048 MB | 0.9 秒 | 2.0 × 0.9 = 1.8 |

更快、也更便宜。反過來，若 function 大部分時間在等外部 API 回應（I/O 密集），加記憶體不會變快，只會更貴。開源工具 **AWS Lambda Power Tuning** 可以自動用不同記憶體設定測試，找出最划算的值；AWS Compute Optimizer 也會對 Lambda 提出記憶體建議。

### Timeout：最長 15 分鐘

- 每次呼叫最長可執行 **900 秒（15 分鐘）**，預設只有 3 秒。超過 timeout，Lambda 會中止這次執行並視為失敗。（例外：較新的 **Lambda Managed Instances** 讓 function 跑在你帳號中由 Lambda 管理的 EC2 容量上，其非同步與多數 event source mapping 呼叫可設定到 90 分鐘。考試與一般設計仍以 15 分鐘為準。）
- Timeout 要依實際需求設定，不要一律設成 15 分鐘：設太長時，卡住的呼叫會一直佔用 concurrency 並持續計費。
- 同步呼叫還受到前端的限制。例如經 API Gateway REST API 呼叫時，整合逾時預設 29 秒（第 20 章），function 跑得再久，使用者也早就收到逾時錯誤。

### 暫存空間 /tmp 與其他限制

| 項目 | 限制 | 備註 |
|---|---|---|
| 記憶體 | 128 MB – 10,240 MB | CPU 依比例分配 |
| Timeout | 最長 900 秒 | 預設 3 秒 |
| `/tmp`（ephemeral storage） | 512 MB – 10,240 MB | 預設 512 MB，超過的部分另外計費；只在該 execution environment 內存在 |
| 同步呼叫 payload | 6 MB（請求與回應各自） | 大檔案改傳 S3 位置 |
| 非同步呼叫 event 大小 | 1 MB | 2025 年由 256 KB 提高到 1 MB；舊教材與題目可能仍寫 256 KB。大資料一樣改傳 S3 位置 |
| 環境變數 | 總共 4 KB | 敏感資料改放 Secrets Manager 或 Parameter Store |
| Zip 部署套件 | 直接上傳 50 MB（壓縮後）；解壓後含 layers 共 250 MB | 超過就改用 container image |
| Container image | 最大 10 GB | 存放在 ECR |
| Layers | 每個 function 最多 5 個 | 計入 250 MB 解壓上限 |
| Account concurrency | 每個 Region 預設 1,000 | 預設 quota，可申請提高（19.8 節） |

需要更大、可在多個 execution environment 之間共享、持久保存的檔案空間時，Lambda 可以掛載 **Amazon EFS**（第 24 章），但 function 必須連到 VPC。

## 19.5 三種呼叫方式：誰在等、誰負責重試

縮圖 function 由 S3 觸發，webhook function 由 HTTP 請求觸發，訂單處理 function 由 SQS 觸發。它們看起來都是「事件來了就執行」，但 Lambda 在背後用三種完全不同的方式處理，而**失敗時的行為、重試、throttling 的結果都不一樣**。這是本章最重要、也是考試最常考的觀念。

```text
 ① 同步（synchronous，RequestResponse）
    Caller ── 呼叫並等待 ──► [Lambda function] ── 回傳結果 ──► Caller
    例：API Gateway、ALB、Function URL、SDK 直接呼叫、Cognito triggers
    失敗或 throttle：錯誤直接回給 caller，由 caller 決定是否重試

 ② 非同步（asynchronous，Event）
    Caller ── 丟出事件，立刻收到 202 ──► [Lambda 內部 event queue]
                                            │ Lambda 取出並呼叫
                                            ▼
                                     [Lambda function]
                                            │ 失敗：Lambda 自動重試（預設 2 次）
                                            ▼
                               仍失敗 → on-failure destination 或 DLQ
    例：S3 event notification、SNS、EventBridge、CloudWatch Logs subscription

 ③ Event source mapping（輪詢，poll-based）
    [SQS／Kinesis／DynamoDB Streams／MSK／Amazon MQ]
            ▲  Lambda 的 poller 主動拉取一批記錄
            │
    [Lambda event source mapping] ── 批次呼叫（同步） ──► [Lambda function]
    失敗：依來源而定（SQS 靠 visibility timeout 重現；stream 依 shard 重試）
```

### ① 同步呼叫

Caller 呼叫後**等待結果**。Function 回傳什麼，caller 就收到什麼；function 出錯或被 throttle，caller 會收到錯誤（throttle 時是 HTTP 429 `TooManyRequestsException`）。**Lambda 不會替同步呼叫自動重試**，重試是 caller 的責任，例如 SDK 內建的重試，或前端顯示錯誤讓使用者再按一次。

Wanderly 的 webhook 經由 API Gateway 同步呼叫 function：付款服務商要知道 Wanderly 是否成功收到通知，必須等待回應。

### ② 非同步呼叫

Caller 把事件交給 Lambda 後**立刻收到「已接受」**（HTTP 202），不等待執行結果。Lambda 把事件放進內部的 queue，再由 Lambda 自己取出呼叫 function。

- Function 執行失敗時，Lambda **自動重試，預設 2 次**（可設定 0–2 次），兩次重試之間會等待一段時間。
- 事件在內部 queue 中最多保留的時間（**maximum event age**）可設定 60 秒到 6 小時。
- Function 被 throttle 時，Lambda 會把事件放回 queue，在最長 6 小時內持續重試。
- 重試與 maximum event age 都用完仍未成功的事件，會送到 **on-failure destination** 或 **DLQ**（下一節）；兩者都沒設定就會被丟棄。
- 非同步呼叫**可能重複執行同一事件**，function 必須是 **idempotent（冪等）**：同一事件處理兩次的結果和處理一次相同（第 33 章）。

S3 觸發縮圖就是非同步呼叫：S3 不在乎縮圖何時完成，只要事件被接住就好。

### ③ Event source mapping

**Event source mapping（事件來源對應，ESM）** 用於「資料在 queue 或 stream 裡，需要有人去拉」的來源。SQS、Kinesis Data Streams、DynamoDB Streams、Amazon MSK、自管 Kafka、Amazon MQ 都不會主動推送事件給 Lambda；而是由 Lambda 管理的 **poller** 持續輪詢，把記錄組成一個**批次（batch）**，再同步呼叫 function。

ESM 的重試與失敗處理由來源的性質決定，19.7 節會詳細說明。

### 三種方式對照

| | 同步 | 非同步 | Event source mapping |
|---|---|---|---|
| Caller 是否等待 | 是 | 否 | 由 Lambda poller 呼叫 |
| 典型來源 | API Gateway、ALB、Function URL、SDK | S3、SNS、EventBridge | SQS、Kinesis、DynamoDB Streams、MSK |
| 誰負責重試 | Caller | Lambda（預設 2 次） | 依來源：SQS 訊息重新可見；stream 重試直到成功或過期 |
| Throttle 時 | Caller 收到 429 | Lambda 持續重試最長 6 小時 | Poller 放慢並重試 |
| 失敗事件去處 | 回給 caller | Destination／DLQ | SQS 的 DLQ（redrive policy）；stream 的 on-failure destination |
| Lambda 權限設定 | Resource-based policy 允許 caller | Resource-based policy 允許來源服務 | Execution role 允許讀取來源 |

最後一列預告了 19.12 節的重點：**推送型來源（同步、非同步）需要 resource-based policy 允許它呼叫 function；拉取型來源（ESM）需要 function 的 execution role 有權讀取來源。**

## 19.6 非同步的失敗處理：destinations 與 DLQ

縮圖 function 上線一週後，小林發現有些旅館上傳了損毀的圖片，function 每次都失敗。重試兩次後，這些事件就消失了，沒有人知道哪些照片沒有縮圖。非同步呼叫需要一個地方接住失敗的事件。

### Dead-letter queue（DLQ）

**Dead-letter queue（死信佇列）** 是較早的做法：在 function 的非同步設定指定一個 **SQS queue 或 SNS topic**，重試用完仍失敗的事件會被送到這裡。DLQ 只保存**原始事件**，不包含錯誤訊息等執行結果。

### Destinations

**Destinations（目的地）** 是較新、功能較完整的做法，建議新設計優先使用：

- 可以分別設定 **on-success** 與 **on-failure** 兩種目的地。
- 目的地可以是 **SQS、SNS、另一個 Lambda function 或 EventBridge event bus**。
- 送出的記錄除了原始事件，還包含**執行結果**：成功時的回傳值，或失敗時的錯誤類型、錯誤訊息與重試次數。

| | DLQ | Destinations |
|---|---|---|
| 適用 | 非同步呼叫 | 非同步呼叫；stream 類 ESM 的 on-failure |
| 成功事件 | 不支援 | 支援 on-success |
| 目標 | SQS、SNS | SQS、SNS、Lambda、EventBridge 等 |
| 內容 | 只有原始事件 | 原始事件 + 回應或錯誤詳情 |

小林把縮圖 function 的 on-failure destination 設為一個 SQS queue，每天由維運人員檢查失敗的照片並通知旅館重新上傳；on-success destination 送到 EventBridge，觸發後續的「照片已上架」通知。

> [!tip] 考試提示
> 題目要求「非同步呼叫失敗時保留事件並包含錯誤資訊」或「成功與失敗都要通知不同系統」，答案是 **Lambda destinations**。若題目是 **SQS 觸發的 function**，失敗訊息的去處是 **SQS queue 本身的 DLQ（redrive policy）**，不是 Lambda 的 DLQ 或 destination，因為 SQS 觸發屬於 event source mapping，不是非同步呼叫。

## 19.7 Event source mapping：SQS、Kinesis 與批次的部分失敗

Wanderly 的訂單確認流程把訊息放進 SQS，由 Lambda 處理；點擊流資料則寫進 Kinesis Data Streams（第 31 章），也由 Lambda 即時彙總。兩者都使用 event source mapping，但行為差異很大。

### SQS 觸發

Poller 從 queue 拉取訊息，組成批次呼叫 function：

- **Batch size**：每批最多幾則訊息。Standard queue 最多 10,000 則（超過 10 則時要設定 **batching window**，讓 poller 最多等待一段時間湊批次）；FIFO queue 每批最多 10 則。
- **成功**：整個批次成功時，Lambda 自動從 queue 刪除這些訊息。
- **失敗**：function 拋出錯誤時，整批訊息都不刪除，等 **visibility timeout** 到期後重新出現在 queue 中被重試（第 32 章）。重試次數超過 queue 的 `maxReceiveCount` 後，訊息被移到 **SQS 的 DLQ**。
- **Visibility timeout 要夠長**：AWS 建議 queue 的 visibility timeout 至少是 function timeout 的 6 倍，否則 function 還在處理時訊息就重新出現，被另一個環境重複處理。
- **Maximum concurrency**：可以在 ESM 上設定最多同時呼叫幾個 function（最小 2），用來保護下游資料庫，而且比 reserved concurrency 更不容易造成訊息因 throttle 被退回 queue。
- **FIFO queue**：同一個 message group ID 的訊息依序處理，同時處理的批次數最多等於活躍的 message group 數。

### 部分失敗：一則壞訊息不該拖累整批

假設一批 10 則訊息中只有第 7 則格式錯誤。預設行為下，function 只要拋出錯誤，**10 則全部**都會重新出現並被重新處理，其中 9 則已經成功處理過的訊息會被重複執行。

解法是 **partial batch response（部分批次回應）**：在 ESM 啟用 `ReportBatchItemFailures`，function 回傳失敗的訊息 ID 清單，Lambda 只讓這些訊息重新可見，其他的直接刪除。

```python
def lambda_handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            process_order(record["body"])          # 必須是 idempotent
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
```

### Kinesis Data Streams 與 DynamoDB Streams

Stream 的特性是**順序很重要**：同一個 shard 裡的記錄必須依序處理（第 31 章）。因此：

- 預設每個 shard 同一時間只有一個 function 呼叫在處理。吞吐量不足時，可以設定 **parallelization factor（1–10）**，讓一個 shard 同時有多個批次在處理，同一個 partition key 的記錄仍保持順序。
- **失敗時預設會不斷重試同一批，直到成功或記錄在 stream 中過期**。在這段期間，這個 shard 後面的記錄全部卡住。這就是所謂的 **poison pill（毒藥訊息）** 問題：一筆壞資料可以讓一個 shard 停擺好幾天。

處理 poison pill 的設定：

| 設定 | 作用 |
|---|---|
| `BisectBatchOnFunctionError` | 批次失敗時拆成兩半分別重試，逐步隔離出壞記錄 |
| `MaximumRetryAttempts` | 限制重試次數 |
| `MaximumRecordAgeInSeconds` | 超過一定年齡的記錄不再重試 |
| On-failure destination | 放棄的批次資訊送到 SQS、SNS 等，事後處理 |
| `ReportBatchItemFailures` | 回報第一筆失敗的記錄，Lambda 從那一筆之後重試，不重做已成功的部分 |

> [!example] 例子：點擊流 function 卡住了
> 某天 Wanderly 的即時熱門飯店排行停止更新。監控顯示 Kinesis 的 `IteratorAge`（最舊未處理記錄的年齡）持續上升，function 的錯誤數穩定地每分鐘幾次。原因是一筆欄位缺失的點擊記錄讓 function 每次都拋出錯誤，Lambda 不斷重試同一批。小林設定了 `MaximumRetryAttempts: 3`、啟用 `BisectBatchOnFunctionError`，並把 on-failure destination 指向一個 SQS queue。之後壞記錄只會被重試幾次就被隔離，shard 繼續前進。

## 19.8 Concurrency：Lambda 的容量單位

EC2 的容量單位是 instance 數量；Lambda 的容量單位是 **concurrency（並行數）**：同一時間正在處理請求的 execution environment 數量。

### 用公式估算

```text
concurrency ≈ 每秒請求數 × 平均執行時間（秒）
```

Wanderly 的 webhook 平時每秒 50 個請求、每個平均執行 0.2 秒，concurrency 約 50 × 0.2 = **10**。月底尖峰每秒 2,000 個請求，若下游變慢使執行時間升到 0.6 秒，concurrency 會跳到 2,000 × 0.6 = **1,200**。注意這個公式的含意：**下游變慢會直接放大 concurrency 需求**，即使請求量沒有增加。

### 帳號層級的上限與擴展速度

- 每個帳號在每個 Region 的 concurrency **預設上限是 1,000**（新帳號可能更低），所有 function 共用。這是預設 quota，可以申請提高。
- 擴展速度也有限制：每個 function 每 10 秒最多可以新增 1,000 個 execution environment。對極度突發的流量，這也是需要考慮的因素。

超過上限時，新的請求會被 **throttle（節流）**：同步呼叫收到 429；非同步呼叫被放回內部 queue 重試；ESM 放慢拉取速度。

上限由所有 function 共用，帶來一個典型問題：月底時批次對帳 function 一口氣用掉 900 個 concurrency，webhook function 就只剩 100 個可用，付款通知開始被拒絕。

### Reserved concurrency：保留，同時也是上限

**Reserved concurrency（保留並行數）** 為某個 function 從帳號總額中切出一塊專屬額度，它有兩個效果：

1. **保證**：這個 function 一定能使用這麼多 concurrency，其他 function 搶不走。
2. **上限**：這個 function **最多**只能使用這麼多，超過就被 throttle。

所以 reserved concurrency 有兩種用途：

- 為重要的 function（webhook）保證容量。
- 為可能失控或會壓垮下游的 function（批次對帳）設上限，例如限制為 50，保護資料庫不被太多連線打爆。
- 設為 **0** 等於暫停這個 function：所有呼叫都會被 throttle，可以作為緊急關閉開關。

Reserved concurrency 不另外收費。帳號必須保留至少 100 個未保留的 concurrency 給其他 function。

### Provisioned concurrency：預先暖好的環境

**Provisioned concurrency（預置並行數）** 是另一回事：Lambda 預先建立並初始化指定數量的 execution environment，讓它們隨時待命，**請求到達時不需要經歷 cold start**。

- 設定在 function 的**版本（version）或 alias** 上，不能設定在 `$LATEST`。
- **會產生費用**：只要設定了，不論是否有請求，都按預置的記憶體與時間計費；實際呼叫的執行時間另計（單價比一般呼叫低）。
- 超過 provisioned 數量的請求會使用一般的 on-demand 環境（可能遇到 cold start），只要還在 concurrency 上限內就不會被 throttle。
- 可以用 **Application Auto Scaling** 管理：例如用 scheduled scaling 在每天 08:00 前調高、深夜調低，或用 target tracking 依使用率調整。

| | Reserved concurrency | Provisioned concurrency |
|---|---|---|
| 解決什麼 | 容量保證與上限 | Cold start 延遲 |
| 是否預先初始化 | 否 | 是 |
| 是否額外收費 | 否 | 是 |
| 是否形成上限 | 是 | 否（超過的部分改用 on-demand） |
| 設定對象 | Function | Version 或 alias |

> [!warning] 常見誤解
> 「設定 reserved concurrency 就沒有 cold start。」Reserved concurrency 只是保留額度，環境仍然是用到時才建立，cold start 照樣會發生。要消除 cold start，用的是 provisioned concurrency（或下一節的 SnapStart）。

### 用 concurrency 保護下游

Lambda 擴展得太快，常常是下游的災難。Wanderly 的訂單 function 每個執行環境會開一條 MySQL 連線，當 concurrency 從 20 飆到 800 時，RDS 的連線數瞬間爆滿，所有服務都連不上資料庫。保護方式：

1. 用 reserved concurrency 或 ESM 的 maximum concurrency 限制 function 最多同時執行幾份。
2. 在 function 與資料庫之間加上 **RDS Proxy**（第 26 章），由它維護連線池，讓大量短暫的 Lambda 連線共用少量的資料庫連線。
3. 在前面放 SQS 緩衝寫入，讓 Lambda 以可控的速度消化（第 32 章）。

## 19.9 對付 cold start：provisioned concurrency 與 SnapStart

Wanderly 的結帳 API 使用 Java 撰寫，cold start 有時超過 4 秒，正好發生在使用者按下「付款」的時候。處理 cold start 有幾層對策，從免費到付費：

1. **讓 init 變輕**：減少相依套件、避免在 init 載入用不到的模組、只在需要時才建立連線。Zip 部署通常比大型 container image 啟動更快。
2. **選擇啟動較快的 runtime**：Python、Node.js 的 cold start 通常比 Java、.NET 短。
3. **SnapStart**：針對特定 runtime，用快照取代初始化。
4. **Provisioned concurrency**：預先準備好環境，最穩定，但要持續付費。

### SnapStart 怎麼運作

**Lambda SnapStart** 在你**發布 function 版本**時，先執行一次 init 階段，把初始化完成後的記憶體與磁碟狀態做成快照（snapshot）並快取。之後需要新的 execution environment 時，Lambda 直接從快照還原，而不是從頭啟動 runtime 與初始化程式，大幅縮短 cold start。

- 支援特定受管 runtime：Java（11 以上）、Python（3.12 以上）、.NET（8 以上），zip 部署與以 Lambda base image 建置的 container image 都可以使用；Node.js、Ruby 與 OS-only runtime 不支援。Java 版本不另外收費；Python 與 .NET 有快照快取與還原的費用。
- 只作用在**已發布的版本**（以及指向版本的 alias），不作用在 `$LATEST`。
- 不能與 provisioned concurrency、EFS 或大於 512 MB 的 `/tmp` 同時使用。

SnapStart 有一個容易被忽略的正確性問題：**同一個快照會被還原成很多個 execution environment**。如果在 init 階段產生了亂數種子、唯一 ID、暫時性憑證或時間戳記，所有從快照還原的環境都會拿到一樣的值；init 時建立的網路連線，在還原後也可能已經失效。正確的做法是把這些「必須唯一或必須新鮮」的東西移到 handler 內，或使用 runtime 提供的還原後 hook 重新產生。

### 怎麼選

| 情境 | 建議 |
|---|---|
| 非同步背景工作，偶爾慢一點無所謂 | 不用處理，讓 init 變輕即可 |
| Java／Python／.NET 的同步 API，cold start 明顯，想低成本改善 | SnapStart |
| 需要穩定、可預測的低延遲，或已知的尖峰時段 | Provisioned concurrency（搭配排程擴展） |
| 函式長時間持續高流量 | 環境本來就常保溫暖；也可評估是否該改用 container（19.15 節） |

## 19.10 Lambda 與 VPC：連到私有資源

Wanderly 的訂單 function 要讀寫 RDS，而 RDS 位於 VPC 的 isolated subnet（第 5 章），從 Internet 完全連不到。預設情況下，Lambda function 執行在 **AWS 管理的 VPC** 中，可以連到 Internet 與 AWS 公開端點，但**連不到你 VPC 內的私有資源**。

### 讓 function 連進 VPC

設定 function 的 VPC、subnet（建議至少兩個 AZ）與 security group 後，Lambda 會在你指定的 subnet 中建立 **Hyperplane ENI**：

```text
   AWS 管理的 Lambda 服務 VPC                     Wanderly VPC 10.20.0.0/16
 ┌──────────────────────────┐            ┌──────────────────────────────────────┐
 │  execution environments   │            │ private subnet app-a                  │
 │  （很多個，同時執行）        │ ── ① ───► │  [Hyperplane ENI]（function 的 SG）   │
 │                           │            │        │ ② local route               │
 └──────────────────────────┘            │        ▼                             │
                                         │  [RDS Proxy] → [RDS]（isolated subnet）│
                                         │        │                             │
                                         │        │ ③ 0.0.0.0/0 → NAT Gateway    │
                                         │        ▼                             │
                                         │  [NAT Gateway]（public subnet）→ IGW  │──► 付款服務商 API
                                         │                                      │
                                         │  [S3 gateway endpoint] ④             │──► S3
                                         └──────────────────────────────────────┘
```

① 所有 execution environment 的流量都經由 Hyperplane ENI 進入你的 VPC。這個 ENI 在**設定 function 時**就建立，並由使用**相同 subnet 與 security group 組合**的 function 共用，不是每次呼叫都建立一個。因此早期「Lambda 放進 VPC 會讓 cold start 多十幾秒」的問題已經不存在。② 進入 VPC 後，function 可以透過 local route 連到 RDS Proxy 與 RDS，受 security group 控制。③ **連進 VPC 後，function 的對外流量完全依照該 subnet 的 route table**：要連 Internet 上的付款服務商 API，subnet 必須有指向 NAT Gateway 的 route。④ 存取 S3、DynamoDB 等 AWS 服務，可以使用 VPC endpoint（第 6 章），不必經過 NAT。

### 最常見的錯誤：放進 public subnet

小林第一次把 function 連進 VPC 後，付款服務商的 API 就連不上了。他的直覺是「把 function 放到 public subnet」，但這沒有用：**Lambda 的 Hyperplane ENI 不會取得 public IP**，即使 subnet 的 route table 指向 Internet Gateway，流量也出不去。正確做法是：

- Function 放在 **private subnet**，route table 的 `0.0.0.0/0` 指向放在 public subnet 的 **NAT Gateway**。
- 只需要存取 AWS 服務時，用 **VPC endpoint** 取代 NAT（gateway endpoint 給 S3、DynamoDB；interface endpoint 給其他服務）。

### 其他注意事項

- **Execution role 需要建立網路介面的權限**，AWS 提供受管政策 `AWSLambdaVPCAccessExecutionRole`。
- **Hyperplane ENI 會佔用 subnet 的 IP**，規劃 subnet 大小時要納入（第 5 章）。
- **不需要存取 VPC 資源的 function 不要連進 VPC**，否則徒增 NAT 費用與設定複雜度。
- 長時間沒有被呼叫的 VPC function，其 ENI 可能被回收，function 進入 inactive 狀態；下一次呼叫時會短暫失敗或延遲，等待 ENI 重新建立。

## 19.11 打包與部署：zip、layers、container image、版本與 alias

### 兩種打包方式

**Zip 部署套件**：把程式碼與相依套件壓成 zip 上傳（大於 50 MB 時先上傳到 S3），解壓後含 layers 不能超過 250 MB。適合大多數 function，啟動速度通常較快。

**Container image**：把 function 打包成 container image 推送到 **Amazon ECR**，最大 10 GB。適合：

- 相依套件很大（例如機器學習函式庫、模型檔），超過 zip 的 250 MB。
- 團隊已經用 container 工具鏈建置與掃描所有程式。

Container image 必須實作 Lambda 的 Runtime API：最簡單的方式是以 AWS 提供的 Lambda base image 為基礎，或在自己的 image 中加入 Runtime Interface Client。它仍然是 Lambda：一樣有 15 分鐘上限、一樣依請求計費，**不是「在 Lambda 上跑任意的長駐 container」**。

### Layers

**Lambda layer（層）** 是一個可以被多個 function 共用的 zip 檔，裡面放共用的程式庫、自訂 runtime 或設定檔。例如 Wanderly 把影像處理用的 Pillow 套件與公司內部的日誌函式庫做成 layer，五個 function 共用。

- 每個 function 最多 5 個 layer，解壓後與 function 程式碼合計仍受 250 MB 限制。
- Layer 有版本，function 引用特定版本。
- Layer 只適用於 zip 部署；container image 直接把相依套件放進 image。

### 版本與 alias

- **`$LATEST`** 是可修改的最新程式碼。
- **Version（版本）** 是發布時產生的**不可修改**快照，包含程式碼與大部分設定，例如 `:7`。
- **Alias（別名）** 是指向某個版本的名稱，例如 `prod → 7`。呼叫端使用 alias 的 ARN，部署新版本時只要把 alias 指向 8。
- Alias 可以設定**加權路由**：例如 90% 到版本 7、10% 到版本 8，做 canary 部署。搭配 CodeDeploy 可以自動逐步切換並在告警時回滾（第 37 章）。

Provisioned concurrency 與 SnapStart 都綁定版本或 alias，這也是正式環境應該使用 alias 呼叫 function 的原因之一。

## 19.12 權限：execution role 與 resource-based policy

小林把縮圖 function 部署好、在 S3 bucket 設定了 event notification，但 S3 一直顯示無法呼叫 function；修好之後，function 又因為寫不進縮圖 bucket 而失敗。這兩個錯誤分別對應 Lambda 權限的兩個方向。

```text
   誰可以呼叫這個 function？                function 可以做什麼？
   （resource-based policy）                （execution role）

 [S3 bucket] ──┐                                       ┌──► S3 PutObject
 [SNS topic] ──┼─► lambda:InvokeFunction ─► [function] ─┼──► DynamoDB PutItem
 [API Gateway]─┤                                       ├──► CloudWatch Logs
 [其他帳號]  ──┘                                       └──► SQS ReceiveMessage（ESM）
```

### Execution role：function 能做什麼

**Execution role（執行角色）** 是 function 執行時所扮演的 IAM role（第 12 章）。Function 裡的程式呼叫任何 AWS API，用的都是這個 role 的臨時憑證。

- Trust policy 允許 `lambda.amazonaws.com` 扮演它。
- 基本需求是寫入 CloudWatch Logs（受管政策 `AWSLambdaBasicExecutionRole`）。
- 連進 VPC 需要建立 ENI 的權限（`AWSLambdaVPCAccessExecutionRole`）。
- **Event source mapping 讀取 SQS、Kinesis、DynamoDB Streams 也是用 execution role**，所以 SQS 觸發的 function 需要 `sqs:ReceiveMessage`、`sqs:DeleteMessage`、`sqs:GetQueueAttributes`。

縮圖 function 的 execution role 需要的權限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::wanderly-hotel-photos/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::wanderly-thumbnails/*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "*"
    }
  ]
}
```

### Resource-based policy：誰能呼叫 function

**Resource-based policy（資源型政策）** 附加在 function 上，決定**哪些服務或帳號可以呼叫它**。S3、SNS、EventBridge、API Gateway 這類「推送」事件的服務，需要被這個 policy 允許才能呼叫 function；其他 AWS 帳號要直接呼叫 function，也是在這裡授權。用 console 設定 trigger 時通常會自動加入；用 CLI 或 IaC 時要自己加：

```bash
aws lambda add-permission \
  --function-name wanderly-thumbnail \
  --statement-id s3-invoke-photos \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::wanderly-hotel-photos \
  --source-account 111122223333
```

`--source-arn` 與 `--source-account` 限制只有這個 bucket 能觸發，避免其他帳號的 bucket 冒用 S3 服務身份呼叫你的 function（confused deputy 問題，第 13 章）。

> [!tip] 考試提示
> 「S3／SNS／EventBridge 無法觸發 function」→ 檢查 function 的 **resource-based policy**。「function 無法讀寫 DynamoDB／S3」或「SQS 觸發器無法讀取 queue」→ 檢查 **execution role**。跨帳號呼叫 function，要在 function 的 resource-based policy 允許對方帳號，對方的 IAM 身份也要有 `lambda:InvokeFunction` 權限。

## 19.13 HTTP 入口：function URL 與其他選擇

Webhook 需要一個 HTTPS 端點。Lambda 有幾種接 HTTP 流量的方式：

- **Function URL**：Lambda 內建的專屬 HTTPS 端點，格式類似 `https://<id>.lambda-url.<region>.on.aws`。設定簡單、不另外收費（只付 Lambda 費用）。認證方式只有兩種：`AWS_IAM`（呼叫端必須用 SigV4 簽章）或 `NONE`（公開，由程式自己驗證，例如檢查 webhook 簽章）。不論哪一種，function 的 resource-based policy 都要允許呼叫者；自 2025 年 10 月起新建立的 function URL 需要同時授予 `lambda:InvokeFunctionUrl` 與 `lambda:InvokeFunction` 兩個權限（console 建立 `NONE` 類型時會自動加上）。跨帳號以 `AWS_IAM` 呼叫時，對方的 identity policy 與你的 resource-based policy 都必須允許。支援 CORS 設定與 response streaming。
- **API Gateway**：完整的 API 管理功能，包括 throttling、usage plan、API key、Cognito 與 Lambda authorizer、請求驗證、快取、WAF 整合、自訂網域（第 20 章）。
- **ALB 的 Lambda target**：已經有 ALB 的環境，可以用 path 規則把部分請求導給 function（第 10 章）。

| 需求 | 選擇 |
|---|---|
| 單一 function、簡單 webhook 或內部工具，設定越少越好 | Function URL |
| 需要 rate limiting、API key、Cognito 驗證、請求驗證、WAF | API Gateway |
| 已有 ALB，部分路徑改由 Lambda 處理 | ALB Lambda target |
| 需要全球邊緣快取或自訂網域，又想用 function URL | 在 function URL 前加 CloudFront |

小林最後選擇 function URL 搭配 `NONE` 認證，在程式中驗證付款服務商的 HMAC 簽章；並為 function 設定 reserved concurrency，確保它在月底不被其他 function 搶走容量，也不會無上限地擴展。

## 19.14 費用模型：什麼時候 Lambda 比較便宜

Lambda 的費用由幾個部分組成：

1. **請求費用**：每次呼叫計一次，每百萬次請求 0.20 美元（以常見公開定價為例）。
2. **執行時間費用**：依 **GB-秒**（配置的記憶體 GB × 執行秒數）計費，以 1 毫秒為單位計算。Arm（Graviton，`arm64`）架構的單價比 x86 低。
3. **其他**：provisioned concurrency 的預置費用、超過 512 MB 的 `/tmp`、SnapStart（Python、.NET）的快取與還原、資料傳輸、CloudWatch Logs 等。

每個帳號每月有免費額度：100 萬次請求與 40 萬 GB-秒。

### 算一次 Wanderly 的縮圖費用

每天 5 萬張照片，每張使用 1,024 MB 執行 1.5 秒：

```text
每月呼叫次數 = 50,000 × 30 = 1,500,000 次
每月 GB-秒   = 1,500,000 × 1 GB × 1.5 秒 = 2,250,000 GB-秒
```

扣掉免費額度後，費用主要來自約 185 萬 GB-秒的執行時間與 50 萬次請求。和 4 台全天執行的 EC2 相比，便宜很多，而且不需要任何維運。

### 交叉點：持續高負載時

反過來，如果一個 function 一天 24 小時都維持數百個 concurrency，等於持續佔用相當多的運算資源。這時以 Lambda 單價計算的費用，可能高於用 ECS on Fargate 或 EC2（搭配 Savings Plans）跑同樣的工作。Lambda 最划算的情境是**流量不規則、有大量閒置時段、或突發性高**的工作。

降低 Lambda 費用的方式：

- 用 Power Tuning 找出最佳記憶體（可能更快也更便宜）。
- 改用 `arm64` 架構（相依套件要支援 Arm）。
- 縮短執行時間：重用連線、避免在 function 裡「等待」（等待也計費，長時間等待改用 Step Functions，第 33 章）。
- **Compute Savings Plans** 也涵蓋 Lambda 的執行時間與 provisioned concurrency，承諾一年或三年用量可以取得折扣（第 39 章）；EC2 Instance Savings Plans 與 Reserved Instances 則不適用於 Lambda。

## 19.15 比較與選型：什麼時候不該用 Lambda

### Lambda 不適合的情境

| 情境 | 原因 | 替代方案 |
|---|---|---|
| 單次工作超過 15 分鐘 | 硬性上限 | ECS／Fargate task、AWS Batch（第 21 章）；或用 Step Functions 拆成多步 |
| 需要長時間保持連線的服務（自建 WebSocket server、遊戲伺服器） | 每次呼叫是短暫的 | ECS、EC2；WebSocket 也可用 API Gateway WebSocket API 搭配 Lambda |
| 需要 GPU | Lambda 不提供 GPU | EC2 GPU instance、SageMaker（第 47 章） |
| 需要控制作業系統、kernel 參數或安裝代理程式 | 無法存取底層 | EC2、ECS on EC2 |
| 24 小時持續高負載、高 concurrency | 單價累積後可能較貴 | ECS／Fargate、EC2 + Savings Plans |
| 需要大量本機狀態或記憶體快取在請求之間共享 | 環境之間不共享，且隨時可能被回收 | ECS service、EC2 + ElastiCache |
| 呼叫的下游無法承受突發的大量連線 | Lambda 擴展極快 | 加 SQS 緩衝、RDS Proxy、限制 concurrency |

### 運算選型決策

```text
工作會超過 15 分鐘，或需要 GPU、作業系統控制、長連線嗎？
├─ 是 → EC2 / ECS / EKS / Batch（第 17、21 章）
└─ 否 → 工作是事件觸發、流量不規則或有大量閒置嗎？
         ├─ 是 → Lambda
         │        ├─ 需要 API 管理功能 → API Gateway + Lambda（第 20 章）
         │        ├─ 多步驟流程、需要等待或人工核准 → Step Functions + Lambda（第 33 章）
         │        └─ 大量訊息處理 → SQS / Kinesis + Lambda（event source mapping）
         └─ 否（持續穩定高負載）→ 比較 Lambda 與 Fargate / EC2 + Savings Plans 的總成本
```

### Lambda 與相關服務

| 服務 | 定位 |
|---|---|
| Lambda | 通用的事件驅動 function，Region 內執行 |
| Lambda@Edge／CloudFront Functions | 在 CloudFront 邊緣修改請求與回應（第 11 章） |
| Step Functions | 編排多個步驟、重試、等待；不是執行運算本身（第 33 章） |
| Fargate | Serverless 的 container 執行環境，沒有 15 分鐘上限（第 21 章） |
| App Runner | 從原始碼或 image 直接部署 web 服務；已不開放新客戶（既有客戶可繼續使用），新專案改評估 ECS Express Mode（第 21 章） |

## 19.16 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 上傳到 S3 後自動處理、流量不規則、最少營運負擔 | S3 event notification → Lambda（非同步） |
| 處理時間超過 15 分鐘 | 不能用 Lambda；ECS／Fargate、Batch，或 Step Functions 拆分 |
| 非同步呼叫失敗要保留事件與錯誤資訊、成功也要通知 | Lambda destinations（on-failure／on-success） |
| SQS 觸發的 function 失敗訊息要保留 | SQS queue 的 DLQ（redrive policy） |
| 一批 SQS 訊息只有幾筆失敗，不想重做整批 | `ReportBatchItemFailures`（partial batch response） |
| Kinesis／DynamoDB Streams 一筆壞資料卡住整個 shard | Bisect batch、maximum retry attempts、record age、on-failure destination |
| 重要 function 不被其他 function 搶走容量 | Reserved concurrency |
| 限制 function 同時執行數以保護資料庫 | Reserved concurrency 或 SQS ESM maximum concurrency；加 RDS Proxy |
| 消除 cold start、需要穩定低延遲 | Provisioned concurrency（設在 version／alias，可排程擴展） |
| Java function cold start 長、想低成本改善 | SnapStart |
| 連進 VPC 後無法存取 Internet | Private subnet + NAT Gateway（放 public subnet 沒用） |
| VPC 中的 function 存取 S3／DynamoDB 不經過 NAT | Gateway VPC endpoint |
| 大量 Lambda 打爆 RDS 連線數 | RDS Proxy |
| 相依套件超過 250 MB | Container image（最大 10 GB）或 EFS |
| 多個 function 共用程式庫 | Lambda layers |
| S3／SNS 無法觸發 function | Function 的 resource-based policy |
| Function 無法寫 DynamoDB、無法讀 SQS | Execution role |
| 單一 function 的簡單 HTTPS 端點、最少設定 | Function URL（`AWS_IAM` 或 `NONE`） |
| CPU 密集的 function 太慢 | 增加記憶體（CPU 依比例增加），可能也更便宜 |
| 持續使用 Lambda 想降低費用 | Compute Savings Plans、`arm64`、調整記憶體 |

**常見陷阱**：

1. 以為 reserved concurrency 能消除 cold start：它只保留額度並形成上限。
2. 以為 Lambda 放到 public subnet 就能上網：Hyperplane ENI 沒有 public IP，要走 NAT Gateway。
3. 對 SQS 觸發的 function 設定 Lambda 的非同步 DLQ 或 destination：SQS 觸發是 event source mapping，失敗訊息由 SQS 自己的 redrive policy 處理。
4. 以為同步呼叫失敗時 Lambda 會自動重試：同步呼叫的重試是 caller 的責任，非同步才由 Lambda 重試。
5. 以為可以單獨調整 Lambda 的 CPU：CPU 只能透過記憶體設定間接調整。
6. 把 `/tmp` 或全域變數當成持久或共享的儲存：每個 execution environment 各自獨立，隨時可能被回收。
7. 以為 EC2 Instance Savings Plans 或 RI 能套用到 Lambda：只有 Compute Savings Plans 涵蓋 Lambda。
8. 把 SQS visibility timeout 設得比 function timeout 短：訊息會在處理中重新出現而被重複處理。

## 19.17 SAP 加深：大規模 serverless 的治理、可靠性與遷移

### Concurrency 是需要分配的共享資源

Wanderly 進入多團隊階段後，一個帳號裡有上百個 function，account concurrency 變成和 VPC CIDR 一樣需要規劃的資源：

- **以帳號隔離**：把不同團隊或不同重要等級的 workload 放在不同帳號，每個帳號有獨立的 concurrency quota，從根本上避免互相搶容量（第 40 章的多帳號策略）。
- **為關鍵路徑保留**：付款、登入等 function 設定 reserved concurrency；批次類 function 設定上限。
- **監控 `ConcurrentExecutions` 與 `Throttles`**，在接近 quota 前申請提高；Service Quotas 可以設定告警（第 35 章）。

### 可靠性：重試會放大故障

Lambda 生態系中，重試發生在很多層：SDK、非同步呼叫、SQS 重新可見、stream 重試。當下游故障時，每一層的重試疊加起來，會讓流量放大好幾倍，並在下游恢復時形成第二波衝擊。SAP 設計重點：

- 每個 function 都要 **idempotent**：使用 idempotency key 並把處理紀錄存在 DynamoDB（開源的 Powertools for AWS Lambda 提供現成的 idempotency 工具）。
- 用 maximum event age、maximum retry attempts 限制重試範圍，搭配 DLQ／destination 保留失敗事件以便 redrive。
- 用 SQS 緩衝與 concurrency 上限實作 **backpressure（背壓）**，而不是讓 Lambda 無限擴展壓垮下游（第 33、35 章）。
- Lambda 預設會偵測並停止部分**遞迴迴圈**：目前涵蓋 function 與 SQS、S3、SNS、EventBridge custom event bus 之間，以及 function 彼此呼叫形成的迴圈。同一個觸發事件連鎖呼叫約 16 次後，Lambda 會擋下下一次呼叫並發出通知。迴圈經過 DynamoDB 等其他服務時偵測不到，所以設計上仍應避免輸出寫回觸發來源，例如讓縮圖寫到另一個 bucket，並為 concurrency 與帳單設定告警。

### 多帳號與跨帳號事件

- 跨帳號事件傳遞時，常見做法是由來源帳號發布到 EventBridge event bus，再用規則轉送到目標帳號的 bus，由目標帳號自己的 function 處理（第 32 章），而不是讓來源帳號直接呼叫其他帳號的 function，以降低耦合並讓權限更清楚。
- SQS 觸發可以跨帳號：queue 的 resource policy 允許目標帳號 function 的 execution role 讀取。
- **Code signing**：用 AWS Signer 簽署部署套件，function 設定只接受受信任簽章的程式碼，防止未經核准的程式被部署（第 37 章的部署治理）。

### 遷移與現代化

SAP 題目常給一個既有系統，問如何以最少的改動現代化：

- **排程的 cron 工作**（例如每天凌晨的報表）：若每次執行少於 15 分鐘，可改成 **EventBridge Scheduler** 觸發 Lambda，移除常駐的 EC2。
- **超過 15 分鐘的批次**：用 Step Functions 的 Distributed Map 把工作切成許多小段平行交給 Lambda（第 33 章），或改用 Fargate／Batch。
- **單體應用程式**：不建議一次全部改寫成 Lambda。先用 ALB path 規則或 API Gateway 把新功能、低流量功能逐步切出去（strangler fig 模式，第 46 章）。
- **觀測性**：啟用 X-Ray active tracing 追蹤跨 function 的請求；使用 CloudWatch Lambda Insights 觀察記憶體與 cold start（第 36 章）。

## 本章重點整理

- Lambda 是事件驅動的 serverless 運算：你負責程式碼、相依套件與 IAM 權限，AWS 負責作業系統、runtime 修補、擴展與多 AZ 高可用。
- 每個 execution environment 同時只處理一個請求；新建環境時的 init 階段就是 cold start，環境會被重用但不保證，狀態必須存在外部服務。
- 把 SDK client、連線等昂貴初始化放在 handler 外可以被後續呼叫重用；`/tmp`（預設 512 MB、最大 10,240 MB）只屬於單一環境。
- 記憶體可設 128 MB 到 10,240 MB，CPU 依記憶體成比例分配；CPU 密集的 function 增加記憶體常常更快也更便宜。最長執行 15 分鐘，同步 payload 6 MB。
- 同步呼叫由 caller 等待並負責重試；非同步呼叫由 Lambda 自動重試（預設 2 次），失敗事件送往 destination 或 DLQ；event source mapping 由 Lambda poller 從 SQS、Kinesis 等來源拉取批次。
- Destinations 支援 on-success 與 on-failure 並包含執行結果，是非同步失敗處理的建議做法；SQS 觸發的失敗訊息由 SQS 自己的 DLQ 處理。
- SQS 觸發要讓 visibility timeout 至少為 function timeout 的 6 倍，並用 `ReportBatchItemFailures` 只重試失敗的訊息；stream 觸發要用 bisect、重試次數、記錄年齡與 on-failure destination 避免 poison pill 卡住 shard。
- Concurrency ≈ 每秒請求數 × 平均執行時間；帳號每 Region 預設 1,000 由所有 function 共用，是可申請提高的 quota。
- Reserved concurrency 同時是保證與上限、不額外收費、設為 0 可暫停 function；provisioned concurrency 預先初始化環境以消除 cold start，設在 version 或 alias 上並持續計費。
- SnapStart 在發布版本時建立初始化後的快照以縮短 cold start，支援 Java、Python、.NET 的特定版本，必須處理快照還原後的唯一性與連線問題。
- 連進 VPC 的 function 透過共用的 Hyperplane ENI 存取私有資源，不會取得 public IP；要上 Internet 必須放在 private subnet 並經 NAT Gateway，存取 AWS 服務可改用 VPC endpoint，連 RDS 應搭配 RDS Proxy。
- Zip 套件解壓後含 layers 上限 250 MB，container image 最大 10 GB；版本不可修改，alias 指向版本並可加權路由做 canary。
- Execution role 決定 function 能做什麼（包含 ESM 讀取 queue 與 stream）；resource-based policy 決定誰能呼叫 function（S3、SNS、API Gateway、其他帳號）。
- Lambda 依請求次數與 GB-秒計費，適合不規則與突發流量；持續高負載、超過 15 分鐘、需要 GPU 或作業系統控制的工作應改用 container 或 EC2。Compute Savings Plans 涵蓋 Lambda。

## 本章練習題

### 練習 19-1｜SAA｜單選｜非同步呼叫的失敗事件

Wanderly 讓 S3 的 event notification 在旅館上傳照片時觸發一個 Lambda function 產生縮圖。部分損毀的圖片會讓 function 每次都失敗，維運團隊發現這些事件在幾次失敗後就消失了，沒有人知道哪些照片沒有縮圖。團隊希望保留所有最終失敗的事件，並同時記錄錯誤訊息，以便事後通知旅館。

最合適的做法是什麼？

- A. 把 function 的 timeout 從 30 秒提高到 15 分鐘，讓它有更多時間處理損毀的圖片
- B. 在 S3 bucket 啟用 versioning，讓失敗的照片可以被重新上傳
- C. 為 function 的非同步呼叫設定 on-failure destination，指向一個 SQS queue
- D. 改用 SQS 觸發 function，並為 function 設定非同步呼叫的 DLQ

> [!answer]- 答案：C
> **A ✗** 損毀的圖片無論給多少時間都會失敗，延長 timeout 只會增加費用；失敗事件仍會在重試用完後被丟棄。
>
> **B ✗** Versioning 保存物件的歷史版本，與 Lambda 呼叫失敗的事件記錄無關，也無法告訴團隊哪些照片處理失敗。
>
> **C ✓** S3 觸發 Lambda 是非同步呼叫，Lambda 會自動重試（預設 2 次），之後仍失敗的事件若沒有設定去處就會被丟棄。On-failure destination 會把原始事件連同錯誤類型與錯誤訊息送到 SQS，正好滿足「保留事件並記錄錯誤」。
>
> **D ✗** 改成 SQS 觸發後屬於 event source mapping，function 的非同步 DLQ 不會作用；失敗訊息應由 SQS queue 自己的 redrive policy 處理。而且 DLQ 只保存原始事件，不含錯誤訊息。
>
> **考點**：SAA-2.1、SAA-2.2｜非同步呼叫的重試與 destinations

### 練習 19-2｜SAA｜單選｜超過 Lambda 執行上限的工作

Wanderly 每天凌晨要把前一天所有訂單彙整成一份給會計系統的報表。目前這個工作在一台全天執行的 EC2 上用 cron 執行，平均需要 35 分鐘，記憶體需求約 8 GB，不需要 GPU。團隊希望移除這台 EC2、改用不需管理伺服器的方式，並盡量減少改寫程式。

最合適的做法是什麼？

- A. 把程式打包成 container image，用 EventBridge Scheduler 每天觸發一個 ECS task 在 Fargate 上執行
- B. 把程式改成 Lambda function，記憶體設為 10,240 MB 讓它在 15 分鐘內完成，並用 EventBridge Scheduler 觸發
- C. 把程式改成 Lambda function，並設定 provisioned concurrency 以延長執行時間上限
- D. 把程式改成 Lambda function，timeout 設為 900 秒，失敗時由非同步重試接續執行

> [!answer]- 答案：A
> **A ✓** 35 分鐘的工作超過 Lambda 15 分鐘的硬性上限。Fargate 執行 container 沒有這個限制，也不需要管理伺服器；把既有程式打包成 container 幾乎不需改寫，EventBridge Scheduler 可以直接依排程啟動 ECS task。
>
> **B ✗** 增加記憶體會增加 CPU，但這個工作是否能從 35 分鐘縮到 15 分鐘以內並無把握；就算勉強達到，資料量一成長就會再次超過上限，設計很脆弱。
>
> **C ✗** Provisioned concurrency 只用來消除 cold start，不會改變 15 分鐘的執行上限。
>
> **D ✗** 超過 timeout 的呼叫會被中止，重試會從頭開始執行，而不是從中斷處接續，因此永遠無法完成。
>
> **考點**：SAA-3.2、SAA-4.2｜Lambda 15 分鐘上限與替代方案

### 練習 19-3｜SAA｜單選｜VPC 內的 Lambda 無法連到外部 API

Wanderly 的付款 function 原本可以正常呼叫外部付款服務商的 HTTPS API。為了存取位於 isolated subnet 的 RDS，工程師把 function 連到 VPC 的兩個 private subnet，之後 RDS 可以連線，但付款服務商的 API 一律 timeout。這兩個 private subnet 的 route table 只有 local route。

應如何修正，同時讓 function 繼續存取 RDS？

- A. 把 function 改放到 public subnet，因為 public subnet 的 route table 有指向 Internet Gateway 的 route
- B. 為 function 的 Hyperplane ENI 配置 Elastic IP
- C. 為 function 建立付款服務商 API 的 gateway VPC endpoint
- D. 在 public subnet 建立 NAT Gateway，並在 function 所在 private subnet 的 route table 加入 `0.0.0.0/0` 指向 NAT Gateway

> [!answer]- 答案：D
> **A ✗** 連到 VPC 的 Lambda 使用的 Hyperplane ENI 不會取得 public IP，即使放在有 IGW route 的 public subnet，流量也無法到達 Internet。
>
> **B ✗** Hyperplane ENI 由 Lambda 管理並由多個執行環境共用，AWS 並不提供以 Elastic IP 讓 function 直接對外的設定方式；VPC 內的 function 對外的標準做法是經由 NAT Gateway。
>
> **C ✗** Gateway VPC endpoint 只支援 S3 與 DynamoDB，無法用來連到第三方的 Internet 服務。
>
> **D ✓** 連進 VPC 後，function 的對外流量完全依照所在 subnet 的 route table。把 private subnet 的 default route 指向位於 public subnet 的 NAT Gateway，function 就能主動連到外部 API，同時仍可經由 local route 存取 RDS。
>
> **考點**：SAA-1.2、SAA-3.4｜VPC 中的 Lambda 與 NAT Gateway

### 練習 19-4｜SAA｜單選｜記憶體與執行時間

Wanderly 的 PDF 行程表產生 function 目前設定 256 MB 記憶體，每次執行約 12 秒，CloudWatch 顯示記憶體實際只用了 180 MB，但 function 全程都在做 CPU 密集的排版運算。使用者抱怨產生行程表太慢，財務也不希望 Lambda 費用增加太多。

最合適的第一步是什麼？

- A. 維持 256 MB，因為記憶體使用率還沒到上限，增加記憶體只會浪費
- B. 用不同的記憶體設定（例如 1,024 MB 到 3,008 MB）測試執行時間與 GB-秒，選擇延遲與成本最佳的設定
- C. 為 function 設定 provisioned concurrency，讓它執行得更快
- D. 把 `/tmp` 從 512 MB 提高到 10,240 MB，讓排版運算有更多空間

> [!answer]- 答案：B
> **A ✗** 記憶體使用率低不代表設定合理；這個 function 的瓶頸是 CPU，而 CPU 只能透過增加記憶體取得。
>
> **B ✓** Lambda 的 CPU 依記憶體成比例分配，CPU 密集的 function 增加記憶體會明顯縮短執行時間。因為費用是「記憶體 × 時間」，執行時間縮短的幅度若大於記憶體增加的幅度，總費用甚至可能下降。用實測（例如 Lambda Power Tuning）找出最佳點是標準做法。
>
> **C ✗** Provisioned concurrency 只消除 cold start，不會讓每次執行的運算變快，還會增加固定費用。
>
> **D ✗** `/tmp` 是暫存磁碟空間，與 CPU 運算速度無關，而且超過 512 MB 的部分會額外計費。
>
> **考點**：SAA-3.2、SAA-4.2｜記憶體決定 CPU 與 GB-秒計費

### 練習 19-5｜SAA｜單選｜Reserved 與 provisioned concurrency

Wanderly 的帳號中有兩個 function：結帳 API function 需要穩定的低延遲，使用者不能遇到 cold start；月底對帳 function 平常不執行，月底會突然產生大量並行呼叫，曾經用光帳號的 concurrency，導致結帳 API 被 throttle。團隊希望一次解決這兩個問題。

哪個設定組合最合適？

- A. 為結帳 function 的 alias 設定 provisioned concurrency；為對帳 function 設定 reserved concurrency 作為它的上限
- B. 為結帳 function 設定 reserved concurrency，即可保證沒有 cold start；對帳 function 不需調整
- C. 為對帳 function 設定 provisioned concurrency，讓它月底不再需要擴展
- D. 把兩個 function 的記憶體都提高到 10,240 MB，以減少需要的 concurrency

> [!answer]- 答案：A
> **A ✓** Provisioned concurrency 預先初始化 execution environment，讓結帳 API 不遇到 cold start（必須設定在 version 或 alias）。Reserved concurrency 同時是保證與上限，為對帳 function 設定上限後，它最多只能用這麼多，帳號其餘的 concurrency 就留給結帳 API。
>
> **B ✗** Reserved concurrency 只保留額度，環境仍在需要時才建立，cold start 照樣發生；而且對帳 function 不加上限，月底仍可能搶光剩下的額度。
>
> **C ✗** 為一個平常不執行的 function 持續支付 provisioned concurrency 非常浪費，而且 provisioned concurrency 不會限制它的最大使用量，仍可能搶光帳號額度。
>
> **D ✗** 記憶體影響單次執行的資源與速度，不能直接控制並行數或消除 cold start；全部調到最大還會大幅增加費用。
>
> **考點**：SAA-3.2、SAA-2.2｜reserved vs provisioned concurrency

### 練習 19-6｜SAA｜單選｜Java function 的 cold start

Wanderly 的會員積分 API 是一個 Java 21 的 Lambda function，使用 Spring 框架，cold start 時間約 5 秒，warm 時只要 80 毫秒。流量不規則，難以預測何時會有新的 execution environment 被建立。團隊希望大幅縮短 cold start，並以最低成本達成，可以接受發布版本並透過 alias 呼叫。

最合適的做法是什麼？

- A. 為 alias 設定足以應付尖峰的 provisioned concurrency
- B. 在 function 的已發布版本啟用 SnapStart，並檢查初始化時產生的唯一值與連線是否在還原後重新建立
- C. 把 function 改為 container image 部署，以加快啟動速度
- D. 設定 reserved concurrency，讓 Lambda 預先保留 execution environment

> [!answer]- 答案：B
> **A ✗** Provisioned concurrency 可以消除 cold start，但要依尖峰數量持續付費；流量不規則時，大部分預置容量會閒置，不是最低成本的選擇。
>
> **B ✓** SnapStart 在發布版本時完成初始化並建立快照，之後新環境直接從快照還原，能大幅縮短 Java 的 cold start，而且 Java 的 SnapStart 不另外收費。需要注意快照會被多個環境共用，初始化時產生的亂數、唯一 ID 與網路連線要在還原後重新處理。
>
> **C ✗** Container image 主要解決套件大小限制，並不會縮短 JVM 與框架的初始化時間，通常還可能讓啟動更慢。
>
> **D ✗** Reserved concurrency 只是保留額度並設定上限，不會預先建立或初始化環境。
>
> **考點**：SAA-3.2、SAA-4.2｜SnapStart 降低 cold start

### 練習 19-7｜SAA｜單選｜SQS 批次中的部分失敗

Wanderly 的訂單確認 function 由 SQS standard queue 觸發，batch size 為 10。偶爾有一則訊息因為資料格式錯誤而處理失敗，這時同一批的其他 9 則訊息也會重新出現在 queue 中被再次處理，導致部分顧客收到重複的確認信。

應如何修改，才能只重試失敗的訊息？

- A. 把 batch size 改為 1，讓每則訊息各自呼叫一次 function
- B. 為 function 設定非同步呼叫的 on-failure destination
- C. 把 queue 的 visibility timeout 縮短到 1 秒，讓失敗的訊息更快重試
- D. 在 event source mapping 啟用 `ReportBatchItemFailures`，讓 function 回傳失敗的訊息 ID

> [!answer]- 答案：D
> **A ✗** Batch size 1 確實能隔離失敗，但會大幅增加呼叫次數與費用、降低吞吐量；有內建的部分批次回應可以達成同樣目的。
>
> **B ✗** SQS 觸發是 event source mapping，不是非同步呼叫，function 的非同步 destination 不會作用。
>
> **C ✗** Visibility timeout 太短會讓還在處理中的訊息重新出現，造成更多重複處理，而且不會改變整批重試的行為。
>
> **D ✓** 啟用 `ReportBatchItemFailures` 後，function 回傳 `batchItemFailures` 清單，Lambda 只讓清單中的訊息重新可見，其餘成功的訊息直接從 queue 刪除。搭配 idempotent 的處理邏輯，可以避免重複寄信。
>
> **考點**：SAA-2.1、SAA-2.2｜SQS partial batch response

### 練習 19-8｜SAA｜選兩項｜S3 觸發與 DynamoDB 寫入的權限

工程師用 CloudFormation 部署了一個 Lambda function，預期在 `wanderly-reviews` bucket 有新物件時被觸發，並把評論摘要寫入 DynamoDB 的 `ReviewSummary` table。部署後發現兩個問題：S3 event notification 設定時出現「無法驗證目的地設定」的錯誤；手動測試 function 時，寫入 DynamoDB 回傳 `AccessDeniedException`。

應該做哪兩項修改？（選兩項）

- A. 在 S3 bucket policy 中允許 `lambda.amazonaws.com` 執行 `s3:PutObject`
- B. 在 function 的 resource-based policy 中允許 `s3.amazonaws.com` 執行 `lambda:InvokeFunction`，並以 source ARN 限定為 `wanderly-reviews` bucket
- C. 為 function 建立 interface VPC endpoint，讓 S3 可以連到 function
- D. 在 DynamoDB table 上建立 resource-based policy，允許 `s3.amazonaws.com` 寫入
- E. 在 function 的 execution role 中加入對 `ReviewSummary` table 的 `dynamodb:PutItem` 權限

> [!answer]- 答案：B、E
> **A ✗** Bucket policy 控制誰能存取 bucket，與 S3 能否呼叫 function 無關；function 也不需要寫入這個 bucket。
>
> **B ✓** S3 是推送事件的服務，要呼叫 function 必須被 function 的 resource-based policy 允許。用 source ARN（與 source account）限定來源 bucket，可以避免其他帳號的 bucket 冒用 S3 服務身份觸發 function。
>
> **C ✗** S3 呼叫 Lambda 是透過 Lambda 的服務 API，不需要也不能用 VPC endpoint 建立這條路徑。
>
> **D ✗** 寫入 DynamoDB 的是 function，不是 S3；權限應授予 function 的 execution role。
>
> **E ✓** Function 程式呼叫 AWS API 時使用 execution role 的憑證，`AccessDeniedException` 表示 role 缺少 `dynamodb:PutItem` 權限，應以最小權限只允許這個 table。
>
> **考點**：SAA-1.1、SAA-1.2｜execution role vs resource-based policy

### 練習 19-9｜SAA｜單選｜最簡單的 HTTPS 入口

Wanderly 的資料團隊在另一個 AWS 帳號中有一個排程工作，每小時需要呼叫 Wanderly 帳號中的一個 Lambda function 一次，觸發匯率快取的更新。呼叫端已經使用 AWS SDK 與 IAM role，可以用 SigV4 簽署請求。團隊希望以最少的元件與設定提供一個 HTTPS 端點，並且只有經過 IAM 驗證的呼叫者能使用。

最合適的做法是什麼？

- A. 建立 API Gateway REST API，設定 usage plan 與 API key，並把 API key 提供給資料團隊
- B. 建立一個 internet-facing ALB，把 function 註冊為 target，並在 security group 只允許資料團隊的 IP
- C. 為 function 建立 auth type 為 `AWS_IAM` 的 function URL，並在 resource-based policy 允許資料團隊帳號的 IAM role 呼叫
- D. 為 function 建立 auth type 為 `NONE` 的 function URL，並把 URL 視為機密只提供給資料團隊

> [!answer]- 答案：C
> **A ✗** API Gateway 可以做到，但多了 API、stage、usage plan 的設定；API key 用於識別客戶與配額管理，本身不是可靠的身份驗證機制。
>
> **B ✗** ALB 需要額外的 subnet、listener、target group 與費用，以 IP 限制也不是 IAM 驗證；元件比題目需求多很多。
>
> **C ✓** Function URL 是 Lambda 內建的 HTTPS 端點，不需其他元件。`AWS_IAM` auth type 要求呼叫者用 SigV4 簽章，再由 function 的 resource-based policy 允許另一個帳號的 role（`lambda:InvokeFunctionUrl` 與 `lambda:InvokeFunction`），對方 role 的 identity policy 也授予相同權限，正好符合「最少元件」與「只有 IAM 驗證的呼叫者」。
>
> **D ✗** `NONE` 代表任何知道 URL 的人都能呼叫，把 URL 當機密不是存取控制，違反只允許 IAM 驗證呼叫者的要求。
>
> **考點**：SAA-1.1、SAA-3.2｜function URL 與 IAM 驗證

### 練習 19-10｜SAA｜單選｜大量暫存空間

Wanderly 要用 Lambda 處理旅館上傳的導覽影片：從 S3 下載一支最大 3 GB 的影片，用 FFmpeg 切成多個片段後上傳回 S3，每次處理約 6 分鐘。測試時 function 在處理較大的影片時出現「No space left on device」錯誤。處理過程中的檔案只需要在單次執行期間存在。

最合適的做法是什麼？

- A. 把 function 的記憶體提高到 10,240 MB，讓影片可以放在記憶體中處理
- B. 把 function 的 ephemeral storage（`/tmp`）提高到足夠容納原始影片與輸出片段的大小，例如 8 GB
- C. 為 function 掛載 Amazon EFS 作為所有影片的暫存空間
- D. 把影片改存到 Lambda layer，讓 function 從 layer 讀取

> [!answer]- 答案：B
> **A ✗** 記憶體與磁碟空間是分開的設定，增加記憶體不會增加 `/tmp` 容量；FFmpeg 也需要寫入檔案，而不是只用記憶體。
>
> **B ✓** `/tmp` 預設只有 512 MB，可以調整到最大 10,240 MB。檔案只需要在單次執行期間存在，正是 ephemeral storage 的用途；6 分鐘也在 15 分鐘上限內。只為超過 512 MB 的部分支付少量費用。
>
> **C ✗** EFS 可以提供大量空間，但 function 必須連進 VPC、還要建立檔案系統與 mount target，適合跨環境共享或持久保存的檔案；單次執行的暫存檔用 `/tmp` 更簡單。
>
> **D ✗** Layer 是部署時包含的唯讀程式庫，解壓後合計上限 250 MB，不能用來放每次上傳的影片。
>
> **考點**：SAA-3.1、SAA-3.2｜Lambda ephemeral storage

### 練習 19-11｜SAP｜單選｜Lambda 擴展壓垮 RDS

Wanderly 的庫存更新 function 由 SQS 觸發，每次執行都會開一條連線到 RDS for MySQL。在連假前的大促中，queue 中的訊息暴增，function 的並行數在幾分鐘內升到 900，RDS 的 `DatabaseConnections` 達到上限，網站、後台與其他服務全部連不上資料庫。團隊要求：庫存更新可以延遲處理，但不能再影響其他服務，並且要盡量減少程式修改。

最合適的做法是什麼？

- A. 把 RDS instance 升級到記憶體最大的規格以提高 `max_connections`，並為 function 設定 provisioned concurrency
- B. 把 function 改成同步呼叫，由 API Gateway 的 throttling 限制每秒請求數
- C. 把 SQS queue 改為 FIFO queue，並讓所有訊息使用同一個 message group ID
- D. 在 SQS event source mapping 設定 maximum concurrency 限制並行數，並讓 function 改經由 RDS Proxy 連線

> [!answer]- 答案：D
> **A ✗** 升級資料庫只是把上限往上推，Lambda 下次擴展得更多時一樣會打滿；provisioned concurrency 只處理 cold start，不限制並行數，還增加成本。
>
> **B ✗** 把 queue 觸發改成同步 API 需要大量改寫，而且失去 SQS 的緩衝與重試特性，與「可以延遲處理」的需求相反。
>
> **C ✗** 單一 message group 確實會讓處理變成一次一批，但吞吐量降到極低，也改變了訊息語意；更換 queue 類型需要重新建立 queue 與修改生產者，不是最小變更。
>
> **D ✓** ESM 的 maximum concurrency 限制同時呼叫 function 的數量，多出的訊息留在 queue 中稍後處理，符合「可以延遲」；RDS Proxy 維護連線池，讓大量短暫的 Lambda 連線共用少量資料庫連線，保護其他服務。兩者都只需設定變更與更換連線端點。
>
> **考點**：SAP-2.5、SAP-3.3｜ESM maximum concurrency 與 RDS Proxy

### 練習 19-12｜SAP｜單選｜Kinesis 的 poison pill

Wanderly 的點擊流分析 function 由 Kinesis Data Streams 觸發（stream retention 為 7 天）。某天即時排行停止更新，監控顯示其中一個 shard 的 `IteratorAge` 持續上升，function 對同一批記錄反覆失敗。調查發現是一筆格式錯誤的記錄造成的。團隊要求：壞記錄不能讓 shard 長時間停擺，必須保留壞記錄以便事後分析，其他正常記錄的處理順序不能被打亂。

最合適的做法是什麼？

- A. 把 stream 的 retention 縮短為 24 小時，讓壞記錄更快過期
- B. 在 event source mapping 啟用 bisect batch on function error、設定 maximum retry attempts，並把 on-failure destination 指向 SQS queue
- C. 把 parallelization factor 提高到 10，讓其他批次可以繞過失敗的批次
- D. 改為 Kinesis 觸發的非同步呼叫，並設定 Lambda 的 DLQ

> [!answer]- 答案：B
> **A ✗** 縮短 retention 只是讓 shard 停擺的時間從 7 天變成 1 天，期間後續的正常記錄仍然全部卡住；而且壞記錄過期後就消失，無法事後分析。
>
> **B ✓** Bisect 會把失敗的批次拆半重試，逐步隔離出壞記錄；maximum retry attempts 限制重試次數，用完後把批次資訊送到 on-failure destination 保存，shard 隨即繼續處理後續記錄，同一 shard 的順序仍維持。
>
> **C ✗** Parallelization factor 讓同一個 shard 同時處理多個批次以提高吞吐量，但同一 partition key 的記錄仍依序處理，壞記錄所在的那條順序依然會卡住；也沒有解決保留壞記錄的需求。
>
> **D ✗** Kinesis 觸發一定是透過 event source mapping，不能改成非同步呼叫；Lambda 的非同步 DLQ 對 stream 觸發不會作用。
>
> **考點**：SAP-3.4、SAP-2.4｜stream event source mapping 的錯誤處理

### 練習 19-13｜SAP｜選兩項｜可預期尖峰的穩定低延遲

Wanderly 的機票比價 API 由 API Gateway 呼叫一個 Node.js Lambda function。每天 09:00 到 11:00 有大量企業客戶同時查詢，這段時間的 concurrency 穩定在 400 左右，客戶合約要求 p99 延遲低於 300 毫秒；其他時段 concurrency 只有 20 以下。目前尖峰剛開始時常因 cold start 違反 SLA。團隊希望滿足 SLA，並避免在離峰時段支付不必要的費用。

哪兩個做法最合適？（選兩項）

- A. 發布版本並建立 alias，讓 API Gateway 呼叫 alias，並在 alias 上設定 provisioned concurrency
- B. 為 function 設定 400 的 reserved concurrency，確保尖峰時有足夠的暖環境
- C. 使用 Application Auto Scaling 的 scheduled action，在每天 08:45 把 provisioned concurrency 調高到約 400，11:00 後調回低值
- D. 為 function 啟用 SnapStart，以取代 provisioned concurrency
- E. 把 provisioned concurrency 設定在 `$LATEST`，讓每次部署都自動套用

> [!answer]- 答案：A、C
> **A ✓** Provisioned concurrency 預先初始化 execution environment，是滿足嚴格延遲 SLA 的直接做法，但它只能設定在已發布的版本或 alias 上；讓 API Gateway 呼叫 alias，部署新版本時只要更新 alias 指向。
>
> **B ✗** Reserved concurrency 只保留額度並設定上限，不會預先建立環境，cold start 仍會發生。
>
> **C ✓** 尖峰時段固定且可預期，用 Application Auto Scaling 的排程在尖峰前調高 provisioned concurrency、結束後調回，避免離峰時段支付大量預置費用。
>
> **D ✗** SnapStart 不支援 Node.js runtime，也不能與 provisioned concurrency 同時使用；對需要穩定 p99 的尖峰，預先初始化的 provisioned concurrency 更可靠。
>
> **E ✗** Provisioned concurrency 不能設定在 `$LATEST`，只能設定在已發布的版本或 alias。
>
> **考點**：SAP-2.5、SAP-2.6｜provisioned concurrency 與排程擴展

### 練習 19-14｜SAP｜單選｜非同步處理結果的路由

Wanderly 的訂房確認流程中，EventBridge 規則會非同步呼叫一個 Lambda function 向飯店系統確認房間。成功時需要通知 CRM 系統（透過 EventBridge 事件），失敗時需要把原始事件連同錯誤原因送到客服團隊的 SQS queue 人工處理。目前 function 程式內自己呼叫 EventBridge 與 SQS 發送結果，常因為程式錯誤或 timeout 而漏送。團隊希望改用受管機制並減少程式碼。

最合適的做法是什麼？

- A. 設定 Lambda destinations：on-success 指向 EventBridge event bus，on-failure 指向客服的 SQS queue，並移除程式中的發送邏輯
- B. 為 function 設定 SQS DLQ 接收失敗事件，成功通知仍由程式碼發送
- C. 把 EventBridge 規則改為呼叫 SQS queue，再由 SQS 觸發 function，並在 function 中判斷成功或失敗
- D. 改用 Step Functions Express workflow 包裝這個 function，並在 workflow 中自行加入 retry 與通知步驟

> [!answer]- 答案：A
> **A ✓** Destinations 由 Lambda 在非同步呼叫完成後自動送出結果：on-success 記錄包含 function 的回傳值，on-failure 記錄包含原始事件、錯誤類型與錯誤訊息，正好滿足兩種路由需求，並把易出錯的發送邏輯從程式碼移除。即使 function timeout，失敗記錄也會由 Lambda 送出。
>
> **B ✗** DLQ 只處理失敗，且只保存原始事件、不含錯誤原因；成功通知仍留在程式中，問題只解決一半。
>
> **C ✗** 改成 SQS 觸發後屬於 event source mapping，非同步 destinations 不再適用，成功與失敗的通知仍要自己寫程式處理，反而增加元件。
>
> **D ✗** Step Functions 可以實作同樣的流程，但需要另外設計 state machine，元件與設定比直接使用 Lambda destinations 多；當需求只是「把結果送到兩個地方」時，destinations 更簡單。
>
> **考點**：SAP-3.1、SAP-2.4｜Lambda destinations vs DLQ

### 練習 19-15｜SAP｜單選｜長期穩定使用 Lambda 的成本

Wanderly 的平台團隊分析發現，公司在三個 Region 的 Lambda 費用過去一年穩定成長，每月執行時間費用波動不大，未來三年預期仍會持續使用，同時也有部分 workload 正逐步從 Lambda 移到 ECS on Fargate。財務要求在不修改任何架構的前提下降低運算費用，並保留在 Lambda 與 Fargate 之間調整的彈性。

最合適的做法是什麼？

- A. 為每個 Region 購買 EC2 Instance Savings Plans，涵蓋 Lambda 與 Fargate 的使用量
- B. 為主要 function 購買 Reserved Instances
- C. 依過去穩定的基礎用量購買 Compute Savings Plans
- D. 為所有 function 提高 reserved concurrency，以取得批量折扣

> [!answer]- 答案：C
> **A ✗** EC2 Instance Savings Plans 綁定特定 Region 的 instance family，只適用於 EC2，不涵蓋 Lambda 與 Fargate。
>
> **B ✗** Reserved Instances 是 EC2（以及 RDS 等資料庫服務）的折扣機制，無法套用到 Lambda。
>
> **C ✓** Compute Savings Plans 以每小時承諾金額取得折扣，涵蓋 EC2、Fargate 與 Lambda，不限 Region 與 instance family。Workload 在 Lambda 與 Fargate 之間移動時，折扣會自動套用到新的用量，完全不需要修改架構。
>
> **D ✗** Reserved concurrency 只是保留並限制並行數，不額外收費也沒有任何折扣效果。
>
> **考點**：SAP-1.5、SAP-2.6｜Compute Savings Plans 涵蓋 Lambda

### 練習 19-16｜SAP｜選兩項｜大型模型的部署方式

Wanderly 要把一個以 Python 撰寫的旅遊評論情緒分析模型部署成 Lambda function，由 SQS 觸發。模型檔約 2.5 GB，相依的機器學習函式庫解壓後約 1.2 GB，每次推論約 3 秒。團隊不希望每次 cold start 都從 S3 下載模型，也不希望另外管理伺服器。

哪兩個做法可行？（選兩項）

- A. 把模型與函式庫拆成五個 Lambda layer，每個 layer 不超過 50 MB
- B. 把程式、函式庫與模型打包成 container image 推送到 ECR，以 container image 部署 function
- C. 把 function 的 `/tmp` 設為 10,240 MB，部署時把模型直接放在 `/tmp`
- D. 把函式庫打包成 container image，模型放在 Amazon EFS，function 連進 VPC 並掛載 EFS 讀取模型
- E. 把模型放在環境變數中，在 init 階段解碼載入

> [!answer]- 答案：B、D
> **A ✗** Zip 部署與所有 layer 解壓後合計不能超過 250 MB，3.7 GB 的模型與函式庫遠超過這個上限，拆成多個 layer 也無法繞過。
>
> **B ✓** Container image 最大 10 GB，可以把函式庫與模型一起打包，部署時就包含在 image 中，不需要在 cold start 時從 S3 下載；它仍然是 serverless 的 Lambda，不需管理伺服器。
>
> **C ✗** `/tmp` 是執行時才存在的暫存空間，每個新環境都是空的，無法在部署時預先放入檔案；要用 `/tmp` 就必須在 cold start 時下載，違反需求。
>
> **D ✓** EFS 可以被多個 execution environment 共享與持久保存，模型放在 EFS 上，function 直接從掛載路徑讀取，不需要每次從 S3 下載；函式庫放在 container image 中避開 250 MB 限制。代價是 function 要連進 VPC，並需規劃 EFS 的吞吐量。
>
> **E ✗** 環境變數總共只有 4 KB，不可能放入模型。
>
> **考點**：SAP-4.4、SAP-2.5｜container image、EFS 與部署套件限制
