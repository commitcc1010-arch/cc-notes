---
chapter: 33
title: Step Functions 與分散式系統模式
part: 6
---

# 第 33 章　Step Functions 與分散式系統模式

> [!abstract] 本章地圖
> **你會學到**：
> - 解釋為什麼分散式呼叫會有「成功、失敗、不知道」三種結果，並用 timeout、retry、exponential backoff 與 jitter 安全地處理它們
> - 用 idempotency key 讓重試與重複投遞不會造成重複扣款，並說清楚 at-least-once 與「exactly-once」的真正意義
> - 用 Step Functions（Standard 與 Express）實作多步驟流程，包括 Retry／Catch、等待人工核准、Map 與 Distributed Map
> - 用 saga 與補償交易處理 Wanderly 的訂房付款流程，用 transactional outbox 解決「寫資料庫又要發事件」的雙寫問題
> - 用 circuit breaker、bulkhead 與 backpressure 防止一個下游的故障擴散到整個系統
> - 判斷一個 API 該同步還是非同步、一個元件該 stateless 還是 stateful
>
> **前置知識**：第 32 章（SQS、SNS、EventBridge）、第 19 章（Lambda）、第 27 章（DynamoDB conditional write 與 transactions）
> **考試比重**：SAA ★★☆（Domain 2 解耦與高可用）｜SAP ★★★（Domain 2 可靠性、Domain 3 改善既有系統、Domain 4 現代化）

## 33.1 故事：一筆訂房被扣了兩次款

第 32 章把寄信、點數這些「晚點做也可以」的工作搬到了 queue 後面，結帳流程變快也變穩了。但核心的訂房付款流程還是一段很長的程式：先向旅館保留房間、再向金流商扣款、再請旅館正式確認、最後通知使用者。

某天金流商的 API 變慢，一次扣款請求花了 12 秒才回應，但 Wanderly 的程式設定 10 秒逾時。程式判斷「扣款失敗」，於是重試了一次，第二次在 2 秒內成功。結果使用者的信用卡被扣了兩次：第一次請求其實在金流商那邊成功了，只是回應來得太晚。

同一週還發生了另一件事：旅館確認步驟失敗了，但程式已經扣了款，錯誤處理只寫了「記錄日誌」。客服收到使用者投訴才發現，這筆訂單錢收了、房間卻沒有。工程師翻遍日誌，花了半天才拼湊出這筆訂單到底走到哪一步。

這兩個事故暴露了分散式系統最根本的難題：**當流程跨越多個系統時，沒有一個資料庫交易能保護你**。這一章先建立處理失敗的基本工具（timeout、retry、idempotency），再用 Step Functions 把整個訂房流程變成看得見、管得住的狀態機，最後介紹讓系統在部分故障時仍能運作的幾個經典模式。

## 33.2 分散式呼叫的三種結果

在單一程式裡呼叫一個函式，結果只有兩種：成功或拋出例外。透過網路呼叫另一個服務時，結果有**三種**：

1. **成功**：收到成功回應。
2. **失敗**：收到明確的錯誤回應，例如 400 參數錯誤、402 卡片被拒。
3. **不知道**：逾時、連線中斷、收到 502／503。對方可能根本沒收到請求，可能處理到一半，也可能**已經處理完成只是回應遺失了**。

Wanderly 重複扣款的事故，就是把第三種結果當成第二種處理。「不知道」才是分散式系統的常態，所有本章的模式都在回答同一個問題：**結果不明時，怎麼做才安全？**

### Timeout：等待必須有上限

如果不設定逾時，一個沒有回應的下游會讓呼叫端無限期等待，占用執行緒、連線與記憶體，最後呼叫端自己也耗盡資源。所以每一個網路呼叫都必須有 **timeout（逾時）**：

- **Connection timeout**：建立 TCP 連線最多等多久，通常很短（例如 1–3 秒）。
- **Request／read timeout**：送出請求後等回應最多等多久，依下游的正常延遲設定，通常是 P99 延遲再留一些餘裕。

Timeout 還要**由外往內遞減**。API Gateway REST API 的整合逾時預設是 29 秒（第 20 章），API Gateway 後面的 Lambda timeout 就應該小於 29 秒，Lambda 呼叫金流的 timeout 又要更小，並扣掉自己重試所需的時間。否則外層已經放棄、回傳錯誤給使用者，內層還在繼續重試，做的全是白工，甚至在使用者以為失敗後才偷偷成功。

## 33.3 Retry、exponential backoff 與 jitter

很多失敗是暫時的：網路瞬斷、下游正在擴展、被 throttle（限流）。對這類錯誤，最簡單有效的處理就是 **retry（重試）**。但重試做錯了，會把一個小故障放大成大事故。

### 哪些錯誤該重試

| 錯誤類型 | 例子 | 該重試嗎 |
|---|---|---|
| 暫時性、可恢復 | 逾時、連線重置、HTTP 500／502／503、`ThrottlingException`、HTTP 429 | 是，搭配 backoff |
| 確定性的用戶端錯誤 | HTTP 400 參數錯誤、403 權限不足、404 不存在、卡片被拒 | 否，重試一萬次結果都一樣 |
| 結果不明且操作不是冪等 | 扣款逾時 | 只有在加上 idempotency key 後才能重試（33.4 節） |

### Exponential backoff：失敗越多次，等越久

假設金流商因為過載開始回錯誤，而 1,000 個 Wanderly worker 都在失敗後「立刻重試」，下游收到的請求量就變成原本的兩倍、三倍，本來快恢復的服務被重試流量壓垮。這稱為 **retry storm（重試風暴）**。

**Exponential backoff（指數退避）** 讓每次重試前的等待時間成倍增加：第 1 次等 100 ms、第 2 次 200 ms、第 3 次 400 ms……並設定一個上限（cap）與最大重試次數，給下游恢復的時間。

### Jitter：不要大家一起重試

只有 exponential backoff 還不夠。如果 1,000 個 worker 在同一時刻失敗，它們會在「同一時刻 + 100 ms」一起重試，再在「+300 ms」一起重試，形成一波一波的尖峰。**Jitter（抖動）** 在等待時間中加入隨機性，把重試分散開。AWS 推薦的做法之一是 **full jitter**：在 0 到「指數退避值」之間隨機挑一個等待時間。

```python
import random
import time

def call_with_retry(operation, max_attempts=4, base=0.1, cap=5.0):
    """呼叫 operation；只對暫時性錯誤重試，使用 exponential backoff + full jitter。"""
    for attempt in range(max_attempts):
        try:
            return operation()
        except TransientError:            # 逾時、5xx、throttling
            if attempt == max_attempts - 1:
                raise                     # 重試用盡，交給上層處理
            delay = random.uniform(0, min(cap, base * (2 ** attempt)))
            time.sleep(delay)
        # 其他例外（參數錯誤、權限錯誤）不攔截，直接拋出
```

```text
沒有 jitter：                       有 full jitter：
請求數                               請求數
 │█        █        █                │█
 │█        █        █                │█ ▄ ▃▄ ▂▃ ▄▂ ▃ ▂▃▂ ▂
 │█        █        █                │█▄█▃██▄██▃██▄█▃███▄█▂
 └──────────────────────► 時間       └──────────────────────► 時間
   一波波同步重試的尖峰                 重試被攤平，下游壓力平穩
```

### AWS SDK 的內建重試

AWS SDK 已經內建重試，提供三種 retry mode：

- **legacy**：舊版行為，各語言 SDK 不一致。
- **standard**：跨 SDK 一致的重試規則，預設最多 3 次嘗試，使用帶 jitter 的 exponential backoff，並有重試配額（retry quota）避免故障時無止盡重試。
- **adaptive**：在 standard 的基礎上加入用戶端限速，被 throttle 時自動降低送出速率，適合「大量呼叫同一個容易被限流的 API」的情境。

所以呼叫 AWS API 時，通常不需要自己再包一層重試；需要做的是選對 mode、確認 timeout 合理。

### 只在一層重試

如果使用者端重試 3 次、API Gateway 後的 Lambda 重試 3 次、Lambda 裡的 SDK 再重試 3 次，一次失敗最多會變成 3 × 3 × 3 = 27 次下游請求。這稱為 **retry amplification（重試放大）**。原則是**只在一個層級重試**（通常是最靠近失敗的那一層，或最外層的流程協調者），其他層級快速失敗。第 35 章會再介紹 token bucket 與 retry budget 這類限制重試總量的方法。

> [!warning] 常見誤解
> 「重試越多次越可靠。」重試只對暫時性錯誤有用；對已經過載的下游，大量重試會讓它更難恢復。可靠性來自「有上限、有退避、有隨機、只在一層」的重試，加上冪等的操作，而不是重試次數。

## 33.4 Idempotency：讓「再做一次」變得安全

回到重複扣款的事故。扣款逾時，結果不明，重試可能造成重複扣款、不重試可能讓使用者付不了錢。唯一的出路是讓扣款這個操作變成 **idempotent（冪等）**：用同樣的參數執行一次或多次，效果完全相同。

### Idempotency key

有些操作天生冪等，例如「把訂單 B-1001 的狀態設為 CONFIRMED」、「刪除 S3 物件 X」。但「扣款 12,800 元」、「加 100 點」、「建立一筆新訂單」不是。讓它們變成冪等的標準做法是 **idempotency key（冪等鍵）**：

1. 呼叫端為每一個「業務上的單一意圖」產生一個唯一的 key，例如 `charge:B-1001`。**重試時必須沿用同一個 key**，而不是每次重新產生。
2. 被呼叫端收到請求時，先查這個 key 有沒有處理過：
   - 沒處理過 → 記錄「處理中」，執行操作，把結果和 key 一起存下來。
   - 已處理完成 → 不再執行，直接回傳上次存下的結果。
   - 正在處理中 → 回傳「處理中」或衝突錯誤，請呼叫端稍後再試。

多數金流商的 API 都支援在請求中帶 idempotency key。Wanderly 修正後的扣款呼叫一律帶 `Idempotency-Key: charge:B-1001`，就算逾時重試十次，金流商也只會扣款一次。

### 在 AWS 上實作：DynamoDB conditional write

Wanderly 自己的服務（例如點數服務）也要冪等，因為 SQS Standard 會重複投遞、EventBridge replay 會重送。常見做法是用 DynamoDB 存 idempotency 紀錄，利用 **conditional write（條件式寫入）** 保證「同一個 key 只有一個請求能搶到」：

```python
import time
import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table("idempotency")

def add_points_once(event_id: str, member_id: str, points: int):
    key = f"points:{event_id}"
    try:
        # 只有 key 不存在時才寫入成功，等於「搶鎖」
        table.put_item(
            Item={"pk": key, "status": "IN_PROGRESS",
                  "expiresAt": int(time.time()) + 7 * 86400},   # 搭配 DynamoDB TTL 自動清除
            ConditionExpression="attribute_not_exists(pk)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = table.get_item(Key={"pk": key})["Item"]
        if existing["status"] == "COMPLETED":
            return existing["result"]          # 已處理過：回傳上次結果，不再加點
        raise InProgressError(key)             # 另一個 worker 處理中：讓訊息稍後重試

    result = do_add_points(member_id, points)  # 真正的副作用
    table.update_item(
        Key={"pk": key},
        UpdateExpression="SET #s = :done, #r = :result",
        ExpressionAttributeNames={"#s": "status", "#r": "result"},
        ExpressionAttributeValues={":done": "COMPLETED", ":result": result},
    )
    return result
```

讀這段程式時注意四個細節：

1. **Key 來自業務事件**（事件 ID 或訂單編號），不是收到訊息時隨機產生，否則每次重送都是新 key。
2. **`attribute_not_exists` 讓兩個同時到達的重複訊息只有一個能寫入成功**，避免「兩個 worker 同時查詢、都以為沒處理過」的競態。
3. **IN_PROGRESS 狀態要能過期**。若 worker 在處理中當機，紀錄永遠卡在 IN_PROGRESS 會讓這筆工作再也做不了；實務上會記錄開始時間，超過合理處理時間後允許重新搶。
4. **TTL 要比「重複可能出現的最長時間」更長**。例如 SQS retention 4 天、EventBridge archive 可能重播 7 天內的事件，idempotency 紀錄就至少保留 7 天。

如果副作用本身也寫在同一個 DynamoDB table，可以用 **TransactWriteItems** 把「寫入 idempotency 紀錄」與「加點數」放在同一個交易裡，一次完成。Lambda 的 Python、TypeScript 等 **Powertools for AWS Lambda** 提供現成的 idempotency 工具，內部就是這個 DynamoDB 模式。

### 其他 AWS 服務的冪等設計

- **Step Functions Standard**：execution name 在同一個 state machine 內 90 天不能重複。用訂單編號當 execution name，重複的 `StartExecution` 不會啟動第二個流程（同名同輸入且仍在執行中時，會回傳原本的結果；其他情況回傳 `ExecutionAlreadyExists`）。
- **EC2 `RunInstances`** 等 API 支援 `ClientToken` 參數，重試時帶相同 token 不會重複建立資源。
- **SQS FIFO** 的 deduplication ID 防止 5 分鐘內 producer 重送（第 32 章），但這只是入口的去重，不等於業務處理冪等。

## 33.5 At-least-once 與 exactly-once 的錯覺

看完前兩節，你可能會問：有沒有一個服務能保證「每則訊息剛好被處理一次」，讓我不用煩惱冪等？答案是：**在跨越網路的系統中，「剛好一次投遞」在一般情況下做不到**。原因就是 33.2 節的「不知道」：consumer 處理完、準備確認時當機了，系統無法分辨它「處理完沒確認」還是「根本沒處理」，只能選擇重送（可能重複）或不重送（可能遺失）。

所以實務上只有兩種投遞保證可選：

- **At-most-once（最多一次）**：不重送，可能遺失。適合可以容忍遺失的資料，例如部分監控指標。
- **At-least-once（至少一次）**：會重送，可能重複。絕大多數 AWS 服務的選擇。

大家說的「exactly-once」，實際上是 **effectively-once（效果上一次）**：**at-least-once 投遞 + 冪等處理 = 效果上只發生一次**。

| 重複可能從哪裡來 | 例子 | 對策 |
|---|---|---|
| Producer 重送 | 送 SQS 時逾時，producer 重試 | SQS FIFO dedup ID（5 分鐘內）、事件帶唯一 ID |
| Queue 重投 | Visibility timeout 到期、Standard queue 的偶發重複 | Consumer 冪等 |
| 批次部分失敗 | Lambda 處理 SQS batch，一則失敗整批重試 | `ReportBatchItemFailures` + 冪等 |
| 流程重試 | Step Functions 的 Retry、Lambda 非同步呼叫的自動重試 | 每個 task 冪等，帶 idempotency key |
| 人為重放 | DLQ redrive、EventBridge replay | 冪等，key 的保存期間涵蓋重放範圍 |

> [!warning] 常見誤解
> 「Step Functions Standard 是 exactly-once，所以裡面的 Lambda 只會被執行一次。」Standard workflow 保證的是**狀態轉換**（從一個 state 走到下一個）只發生一次；如果你為 task 設定了 Retry，或 Lambda 呼叫的結果不明，同一個 task 仍然可能被執行多次。Task 呼叫的外部副作用依然要冪等。

## 33.6 Step Functions：把流程狀態交給狀態機

有了冪等與重試，我們可以安全地呼叫每一個步驟了。但第 33.1 節的第二個事故還沒解決：流程走到一半失敗時，誰記得「現在走到哪一步」？誰負責執行補救動作？如果把這些邏輯都寫在一個 Lambda 裡，它很快就會變成難以維護的巨大函式，而且 Lambda 最長只能執行 15 分鐘，等不了需要人工審核數小時的流程。

**AWS Step Functions** 是 serverless 的流程協調（orchestration）服務。你用 **state machine（狀態機）** 描述流程的每一步、每一步成功或失敗後去哪裡，Step Functions 負責依序執行、保存每一步的輸入輸出、處理重試與錯誤分支，並在 console 上以圖形顯示每一次 **execution（執行）** 走到哪裡、在哪一步失敗。

### Amazon States Language 與 state 類型

State machine 用 **Amazon States Language（ASL）** 定義，是一份 JSON 文件（也可以在 Workflow Studio 用拖拉方式設計）。常用的 state 類型：

| State | 作用 | Wanderly 的例子 |
|---|---|---|
| `Task` | 執行一件工作：呼叫 Lambda、AWS 服務 API、等待外部回呼 | 保留房間、扣款 |
| `Choice` | 依資料內容分支 | 金額超過 50,000 元走人工審核 |
| `Parallel` | 同時執行多個固定分支，全部完成才繼續 | 同時查詢三家旅館的空房 |
| `Map` | 對陣列中的每個項目執行同一組步驟 | 團體訂單的每個房間各自保留 |
| `Wait` | 等待一段時間或到某個時間點 | 等待 15 分鐘後檢查付款狀態 |
| `Pass` | 傳遞或轉換資料，不做外部呼叫 | 補上預設值 |
| `Succeed`／`Fail` | 結束 execution，標示成功或失敗 | 訂房完成／訂房失敗 |

### Standard vs Express

Step Functions 有兩種 workflow type，建立時就要選擇，之後不能更改：

| 比較 | Standard Workflows | Express Workflows |
|---|---|---|
| 最長執行時間 | 1 年 | 5 分鐘 |
| 執行語意 | Exactly-once（每個狀態轉換只執行一次） | 非同步：at-least-once；同步：at-most-once |
| 執行歷史 | 由 Step Functions 保存，可在 console 查詢每一步（結束後保留 90 天） | 送到 CloudWatch Logs（需開啟 logging） |
| 計費 | 依狀態轉換次數 | 依執行次數、執行時間與記憶體 |
| `.sync`、`.waitForTaskToken` | 支援 | 不支援 |
| 適合 | 付款、訂單、人工核准、長時間且需要稽核的流程 | 高頻率、短時間的事件處理、資料轉換、IoT 資料擷取、同步 API 背後的微流程 |

選擇的關鍵問題有三個：流程會不會超過 5 分鐘？需不需要等待外部回呼或人工核准？步驟是不是冪等、能不能接受重複執行？Wanderly 的訂房付款流程需要等待旅館確認、可能需要人工審核、每一步都必須可稽核，所以選 Standard；而點擊流的每筆事件格式轉換每秒數千次、幾百毫秒完成，用 Express 便宜很多。

Express 還分成**同步**（`StartSyncExecution`，呼叫端等待結果，常見於 API Gateway 直接整合）與**非同步**（啟動後立即返回）兩種呼叫方式。

## 33.7 Step Functions 的錯誤處理、等待與整合

### Retry 與 Catch

每個 `Task`（以及 `Parallel`、`Map`）都可以宣告 `Retry` 與 `Catch`：

- **`Retry`**：遇到符合 `ErrorEquals` 的錯誤時重試。欄位包括 `IntervalSeconds`（第一次重試前等待，預設 1 秒）、`MaxAttempts`（預設 3）、`BackoffRate`（每次等待的倍數，預設 2.0）、`MaxDelaySeconds`（等待上限）與 `JitterStrategy`（設為 `FULL` 即 33.3 節的 full jitter）。
- **`Catch`**：重試用盡或遇到不重試的錯誤時，轉到指定的 state，並可用 `ResultPath` 把錯誤資訊附加在原本的輸入上，讓後續步驟知道發生了什麼。

錯誤名稱可以是你的 Lambda 拋出的自訂錯誤（例如 `CardDeclined`），也可以是內建錯誤：`States.Timeout`（逾時）、`States.TaskFailed`、`States.HeartbeatTimeout`，以及代表全部的 `States.ALL`（必須放在最後）。

### Timeout 與 heartbeat

- **`TimeoutSeconds`**：task 最長執行時間，逾時拋出 `States.Timeout`。**沒有設定時，task 可以一直等到整個 execution 的上限**；對等待外部回呼的 task，這代表一個沒人回應的請求可能讓 execution 卡住長達一年，所以一定要設。
- **`HeartbeatSeconds`**：長時間 task 必須在這個間隔內回報一次「我還活著」（`SendTaskHeartbeat`），否則拋出 `States.HeartbeatTimeout`。這讓「worker 默默當機」能被快速發現，而不是等到總逾時。

### 三種 service integration pattern

Step Functions 可以直接呼叫兩百多個 AWS 服務的 API（**AWS SDK integrations**），其中常用服務另有參數更友善的 **optimized integrations**（例如 Lambda、DynamoDB、SQS、SNS、ECS、Glue、EventBridge）。不需要為了「寫一筆 DynamoDB」或「發一則 SNS」特地寫 Lambda。呼叫方式有三種：

| Pattern | Resource 寫法 | 行為 | 例子 |
|---|---|---|---|
| **Request Response** | `arn:aws:states:::sns:publish` | 呼叫 API，拿到回應就繼續 | 發布通知、寫入資料 |
| **Run a Job（.sync）** | `arn:aws:states:::ecs:runTask.sync` | 啟動工作，等它完成才繼續 | 跑一個 ECS 批次 task、Glue job |
| **Wait for Callback（.waitForTaskToken）** | `arn:aws:states:::sqs:sendMessage.waitForTaskToken` | 送出一個 **task token**，暫停直到有人用這個 token 回報結果 | 等待人工核准、等待外部系統 |

### 等待人工核准：task token

Wanderly 規定金額超過 50,000 元或風險分數過高的訂單要由風控人員人工審核。這個等待可能是幾分鐘，也可能是隔天早上。如果用 Lambda 迴圈等待，不但會超過 15 分鐘上限，等待期間也一直在計費。Wait for Callback 解決這件事：

```json
"ManualReview": {
  "Type": "Task",
  "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
  "Parameters": {
    "QueueUrl": "https://sqs.ap-northeast-1.amazonaws.com/111122223333/fraud-review",
    "MessageBody": {
      "bookingId.$": "$.bookingId",
      "amount.$": "$.amount",
      "taskToken.$": "$$.Task.Token"
    }
  },
  "TimeoutSeconds": 86400,
  "ResultPath": "$.review",
  "Catch": [
    { "ErrorEquals": ["States.Timeout", "Rejected"], "ResultPath": "$.error", "Next": "VoidPayment" }
  ],
  "Next": "ConfirmWithHotel"
}
```

```text
[Step Functions]                 [SQS fraud-review]          [風控後台]
 ① ManualReview 送出訊息 ──────►  {bookingId, taskToken} ──► ② 審核人員看到待辦
    execution 暫停，不計算 compute                              │
                                                              ③ 按下「核准」
 ④ 收到 SendTaskSuccess ◄──────── 後台程式以 taskToken 呼叫 ──┘
    帶著 output 繼續往 ConfirmWithHotel
    （若 24 小時沒有回應 → States.Timeout → VoidPayment）
```

① `$$.Task.Token` 是 Step Functions 為這次等待產生的唯一 token，隨訊息送出。② 風控後台從 queue 取出待審核訂單。③ 審核人員決定後，後台程式呼叫 API 回報結果。④ Execution 從暫停處繼續；核准走下一步，拒絕（`SendTaskFailure` 帶錯誤名稱 `Rejected`）或逾時則走 Catch 進入補償流程。後台回報時使用的是一般的 AWS API：

```bash
aws stepfunctions send-task-success \
  --task-token "$TASK_TOKEN" \
  --task-output '{"decision":"APPROVE","reviewer":"risk-ops-07"}'
```

回報 token 的程式需要 `states:SendTaskSuccess`／`states:SendTaskFailure` 權限；如果是透過 email 連結讓人點選核准，通常會在中間放一個 API Gateway + Lambda，由 Lambda 驗證審核者身份後才呼叫這個 API，而不是把 token 直接暴露成可以被任何人呼叫的連結。

### Map 與 Distributed Map

**Map state** 對一個陣列的每個元素執行同一組步驟。預設的 **inline 模式**在同一個 execution 內處理，最多 40 個並行 iteration（`MaxConcurrency` 只能再往下限制），所有 iteration 的歷史都算在同一個 execution 裡，適合幾十到幾百個項目，例如團體訂單的每個房間。

**Distributed Map** 是為大規模資料設計的模式：每個 iteration（或每一批項目）以一個 **child workflow execution** 執行，最多可同時執行 10,000 個 child workflow，可以直接從 S3 讀取項目來源（某個 prefix 下的所有物件、一個 CSV 或 JSON 檔、S3 Inventory 報表），結果可以寫回 S3，並可設定容許失敗的比例（`ToleratedFailurePercentage`）。

Wanderly 每晚要重新處理數百萬張旅館照片（產生新尺寸的縮圖），用 Distributed Map 以 S3 prefix 作為輸入、每批 100 張交給一個 Express child workflow，就能在不管理任何 worker 叢集的情況下平行處理。

### 幾個會影響設計的限制

- **State 之間傳遞的資料（input／output）上限 256 KB**。大型資料要放 S3，只在 state 之間傳遞 S3 位置（和第 32 章的 claim check pattern 同一個道理）。
- **Standard execution 的歷史事件上限是 25,000 個**。用 `Choice` + `Wait` 自己寫的迴圈跑幾千次就可能超過，應改用 Map／Distributed Map，或在迴圈中啟動 child execution 分擔歷史。
- 失敗的 Standard execution 可以在結束後 14 天內 **redrive**（Express 不支援）：從失敗的那一步繼續執行，不必從頭再跑；前面已成功的步驟不會重做。
- 如果某些步驟需要由自己管理的 worker（例如地端主機）執行，可以使用 **activity**：worker 主動向 Step Functions 輪詢工作並回報結果。新設計多半改用 callback pattern 搭配 SQS。

## 33.8 Saga：沒有分散式交易時怎麼保持一致

現在可以處理第二個事故了：扣了款、房間卻沒確認。在單一資料庫裡，我們會把多個寫入包在一個交易中，失敗就 rollback。但「旅館的庫存系統」「金流商」「Wanderly 的訂單資料庫」是三個不同組織的系統，不可能有一個跨越它們的 ACID 交易。

**Saga** 是解決這個問題的模式：把一個大流程拆成一連串的**本地交易（local transaction）**，每一步都在自己的系統內獨立提交；如果中途某一步失敗，就依相反順序執行前面各步的 **compensating transaction（補償交易）**，在業務上抵銷已完成的效果。

### 補償不是 rollback

補償是一個新的、業務上有意義的動作，不是讓時間倒流：已經扣的款不能「取消扣款」，只能「退款」；已經寄出的確認信收不回來，只能再寄一封「訂房已取消」。補償完成後，系統裡會留下「扣款、退款」兩筆紀錄，這是正確的，也是稽核需要的。

所以設計 saga 時，要把步驟依「能不能補償」分成三類，並**把難以補償的步驟盡量往後排**：

| 類型 | 意義 | Wanderly 的步驟 |
|---|---|---|
| **可補償（compensatable）** | 之後失敗時可以用補償抵銷 | 保留房間（補償：釋放保留）、信用卡授權（補償：取消授權） |
| **轉折點（pivot）** | 一旦成功，saga 就必須往前走完，不再回頭 | 旅館正式確認（不可退款的房價，確認後無法免費取消） |
| **可重試（retriable）** | 在轉折點之後，保證最終會成功，失敗就重試 | 請款（capture）、發布訂房成立事件、寄確認信 |

Wanderly 原本的流程是「保留 → **直接扣款** → 確認」，扣款後若確認失敗，補償是退款：有手續費、使用者會在帳單上看到一扣一退。改良後的流程使用信用卡的 **authorize／capture（授權／請款）** 兩階段：先授權（凍結額度，但未真正扣款），旅館確認後才請款。確認失敗時的補償變成「取消授權」，使用者幾乎感受不到。這就是「調整步驟順序與粒度，讓補償變便宜」。

### 用 Step Functions 實作 orchestration saga

```text
            ┌──────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌────────────────┐
 Start ───► │HoldRoom  │──►│AuthorizePay  │──►│ConfirmWithHotel│──►│CapturePayment│──►│PublishConfirmed│──► 成功
            └────┬─────┘   └──────┬───────┘   └───────┬───────┘   └──────────────┘   └────────────────┘
                 │失敗            │失敗                │失敗            （轉折點之後：只重試，不補償）
                 │                ▼                   ▼
                 │          ┌───────────┐       ┌─────────────┐
                 │          │ReleaseRoom│◄──────│VoidPayment  │
                 │          └─────┬─────┘       └─────────────┘
                 ▼                ▼
            ┌───────────────────────┐
            │ BookingFailed (Fail)  │
            └───────────────────────┘
```

成功路徑由左到右；每一步失敗時，Catch 把流程導向「補償前面已完成的步驟」：授權失敗只需釋放房間，旅館確認失敗則先取消授權再釋放房間。轉折點之後的請款與發布事件只設定 Retry（次數多、間隔長），不設補償，若仍失敗就通知人工處理，因為房間已經確定賣出，流程不能再回頭。

對應的 ASL 節錄如下（省略部分 state 的重複設定）：

```json
{
  "Comment": "Wanderly booking saga (orchestration)",
  "StartAt": "HoldRoom",
  "States": {
    "HoldRoom": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "hold-room", "Payload.$": "$" },
      "ResultSelector": { "holdId.$": "$.Payload.holdId" },
      "ResultPath": "$.hold",
      "TimeoutSeconds": 10,
      "Retry": [
        {
          "ErrorEquals": ["Lambda.TooManyRequestsException", "Lambda.ServiceException", "States.Timeout"],
          "IntervalSeconds": 1, "MaxAttempts": 3, "BackoffRate": 2.0, "JitterStrategy": "FULL"
        }
      ],
      "Catch": [ { "ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "BookingFailed" } ],
      "Next": "AuthorizePayment"
    },
    "AuthorizePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "authorize-payment", "Payload.$": "$" },
      "ResultSelector": { "authId.$": "$.Payload.authId" },
      "ResultPath": "$.auth",
      "TimeoutSeconds": 15,
      "Retry": [ { "ErrorEquals": ["States.Timeout"], "MaxAttempts": 2, "JitterStrategy": "FULL" } ],
      "Catch": [ { "ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "ReleaseRoom" } ],
      "Next": "ConfirmWithHotel"
    },
    "ConfirmWithHotel": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "confirm-with-hotel", "Payload.$": "$" },
      "ResultPath": null,
      "TimeoutSeconds": 30,
      "Catch": [ { "ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "VoidPayment" } ],
      "Next": "CapturePayment"
    },
    "CapturePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "capture-payment", "Payload.$": "$" },
      "ResultPath": null,
      "Retry": [
        { "ErrorEquals": ["States.ALL"], "IntervalSeconds": 5, "MaxAttempts": 10,
          "BackoffRate": 2.0, "MaxDelaySeconds": 600, "JitterStrategy": "FULL" }
      ],
      "Next": "PublishConfirmed"
    },
    "PublishConfirmed": {
      "Type": "Task",
      "Resource": "arn:aws:states:::events:putEvents",
      "Parameters": {
        "Entries": [ {
          "EventBusName": "booking",
          "Source": "com.wanderly.booking",
          "DetailType": "BookingConfirmed",
          "Detail.$": "$"
        } ]
      },
      "End": true
    },
    "VoidPayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "void-payment", "Payload.$": "$" },
      "ResultPath": null,
      "Retry": [ { "ErrorEquals": ["States.ALL"], "MaxAttempts": 5, "JitterStrategy": "FULL" } ],
      "Next": "ReleaseRoom"
    },
    "ReleaseRoom": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "release-room", "Payload.$": "$" },
      "ResultPath": null,
      "Retry": [ { "ErrorEquals": ["States.ALL"], "MaxAttempts": 5, "JitterStrategy": "FULL" } ],
      "Next": "BookingFailed"
    },
    "BookingFailed": { "Type": "Fail", "Error": "BookingFailed", "Cause": "A step failed and compensations ran" }
  }
}
```

這份定義有幾個值得注意的設計：

1. **`HoldRoom` 會在逾時後重試**，所以 `hold-room` 必須以訂單編號作為 idempotency key，否則一次逾時可能保留兩間房。
2. **`ConfirmWithHotel` 不重試逾時**。這是轉折點，結果不明時盲目重試很危險；比較安全的做法是讓 `confirm-with-hotel` 內部先以訂單編號查詢旅館是否已確認，再決定是否送出（也就是在步驟內實作冪等）。
3. **補償步驟本身也要重試且冪等**：取消授權、釋放房間可能遇到暫時錯誤，而且「釋放一個已經釋放的保留」必須是安全的。
4. **`ResultPath: null`** 表示丟棄 task 的輸出、保留原本的輸入，讓後續步驟仍拿得到 `hold` 與 `auth` 的資訊。
5. **最後一步用 optimized integration 直接 `PutEvents`**，不需要寫一個只負責發事件的 Lambda。

### Orchestration vs choreography

上面的做法稱為 **orchestration（編排）**：由一個中央協調者（state machine）告訴每個服務該做什麼。另一種做法是 **choreography（編舞）**：沒有中央協調者，每個服務聽事件、做自己的事、再發出新事件，例如訂單服務發 `BookingRequested` → 庫存服務保留房間後發 `RoomHeld` → 支付服務授權後發 `PaymentAuthorized`……失敗時各服務發出失敗事件，上游聽到後自己補償。

| 比較 | Orchestration（Step Functions） | Choreography（EventBridge 事件） |
|---|---|---|
| 流程定義在哪 | 一份 state machine | 分散在各服務的事件處理邏輯 |
| 可見性 | 每筆訂單走到哪一步一目了然 | 需要靠分散式追蹤與日誌拼湊 |
| 補償邏輯 | 集中在協調者 | 每個服務各自實作 |
| 耦合 | 協調者知道所有參與者 | 服務之間只透過事件耦合，新增參與者容易 |
| 適合 | 步驟多、有嚴格順序與補償、需要稽核（付款、訂單） | 步驟少、參與者常變動、只需「通知」而非「指揮」 |

兩者常一起使用：訂房付款的核心流程用 Step Functions 編排，流程完成後發布 `BookingConfirmed` 事件，寄信、點數、分析服務以 choreography 方式各自反應（第 32 章的架構）。

## 33.9 Transactional outbox：寫資料庫又要發事件

Saga 解決了「多個服務之間」的一致性。但還有一個更隱蔽的一致性問題，出現在**單一服務內部**。Wanderly 的訂單服務在建立訂單時要做兩件事：寫入訂單資料庫，並發布 `BookingRequested` 事件讓流程開始。

```python
# 有問題的寫法：dual write（雙寫）
db.insert_order(order)                       # ① 成功
events.put_events(booking_requested(order))  # ② 若這裡失敗或程式在此當機？
```

如果 ① 成功、② 失敗，資料庫裡有訂單，但沒有任何服務知道它存在，訂單永遠停在 PENDING。反過來先發事件再寫資料庫，則可能發出一個「不存在的訂單」的事件。把兩者的順序調來調去都沒用，因為**資料庫和事件匯流排是兩個系統，沒有一個交易能同時涵蓋它們**。這稱為 **dual write problem（雙寫問題）**。

### Outbox 的做法

**Transactional outbox（交易式寄件匣）** 的想法是：不要同時寫兩個系統，只寫一個。

1. 在**同一個資料庫交易**裡，同時寫入訂單資料與一筆 **outbox 紀錄**（「待發布的事件」）。兩者一起成功或一起失敗。
2. 另一個 **relay（轉送程序）** 讀取 outbox 中尚未發布的紀錄，發布到 EventBridge／SNS／SQS，成功後標記為已發布。

```python
# 正確的寫法：同一個交易寫入業務資料與 outbox
with db.transaction() as tx:
    tx.insert("orders", order)
    tx.insert("outbox", {
        "event_id": new_uuid(),            # 事件唯一 ID，供下游去重
        "type": "BookingRequested",
        "payload": to_json(order),
        "published": False,
    })

# relay（另一個程序，或由 CDC 觸發）
for record in db.query("SELECT * FROM outbox WHERE published = false ORDER BY id LIMIT 100"):
    events.put_events(to_event(record))    # 可能重複發布：發布成功但標記前當機
    db.execute("UPDATE outbox SET published = true WHERE event_id = %s", record["event_id"])
```

Relay 在「發布成功、標記之前」當機時，重啟後會再發布一次，所以 outbox 提供的是 **at-least-once 發布**，下游消費者仍然要依 `event_id` 冪等。這是 outbox 和冪等總是一起出現的原因。

### 在 AWS 上的實作方式

- **DynamoDB**：用 `TransactWriteItems` 在同一個交易中寫入訂單 item 與 outbox item（或直接把訂單 item 本身的變更當成事件來源），開啟 **DynamoDB Streams**，再用 **EventBridge Pipes**（source：DynamoDB Streams，filter：只要 outbox 的 INSERT，target：event bus）或 Lambda 把事件送出。完全不需要自己寫輪詢程式。
- **Aurora／RDS**：outbox 是一張資料表。Relay 可以是定期輪詢的 Lambda 或 ECS 服務，也可以用 change data capture（CDC，讀取資料庫的變更紀錄）工具把新插入的 outbox 紀錄轉成事件。
- 需要保證「同一筆訂單的事件依序」時，relay 依訂單編號送到 SQS FIFO（group ID = 訂單編號），或在事件中帶版本號讓下游丟棄過期事件。

> [!tip] 考試提示
> 題目描述「資料庫已更新但事件沒發出去」「訊息送出了但資料庫交易 rollback」「需要保證資料變更與事件發布一致」，答案通常是 transactional outbox，或其 AWS 原生版本「DynamoDB Streams／CDC 觸發事件」。選項若寫「用分散式交易（two-phase commit）同時提交資料庫與 SQS」，那是錯的：SQS、EventBridge 不參與這種交易。

## 33.10 Circuit breaker、bulkhead 與 backpressure：不讓故障擴散

到目前為止，我們處理的是「某個步驟失敗」。還有一類更危險的情況：**下游沒有失敗，只是變得很慢**。回想第 32 章開頭寄信服務變慢拖垮結帳的事故，慢比壞更可怕，因為呼叫端會一直等，資源被一點一點吃光。這一節的三個模式都是在回答「怎麼讓一個下游的問題留在原地」。

### Circuit breaker：下游病了就先別打擾它

Wanderly 搜尋頁面會即時呼叫各家旅館的報價 API。某家旅館的 API 開始每次都要 25 秒才逾時，每個搜尋請求都卡在它身上，搜尋服務的執行緒很快被占滿。重試只會讓情況更糟。

**Circuit breaker（斷路器）** 像家裡的電源斷路器：偵測到一個下游持續失敗，就暫時「跳脫」，之後的呼叫直接快速失敗（或回傳替代結果），不再真的送出請求；過一段時間再放少量請求試探，恢復了才重新導通。

```text
            失敗率超過門檻
  ┌────────┐ ───────────────► ┌────────┐
  │ CLOSED │                  │  OPEN  │  所有呼叫立即失敗／走 fallback
  │正常呼叫 │ ◄─────┐          └───┬────┘
  └────────┘       │              │ 冷卻時間到
                   │ 試探成功      ▼
                   │         ┌───────────┐
                   └──────── │ HALF-OPEN │  只放少量請求試探
                             └─────┬─────┘
                                   │ 試探失敗 → 回到 OPEN
```

```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "CLOSED"
        self.opened_at = 0.0

    def call(self, operation, fallback):
        if self.state == "OPEN":
            if time.time() - self.opened_at < self.reset_timeout:
                return fallback()              # 快速失敗，不打擾下游
            self.state = "HALF_OPEN"           # 冷卻結束，放一個請求試探
        try:
            result = operation()
        except Exception:
            self.failures += 1
            if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
                self.state, self.opened_at = "OPEN", time.time()
            return fallback()
        self.failures, self.state = 0, "CLOSED"
        return result

# 每個旅館 API 一個 breaker；fallback 回傳快取中的最後報價並標示「價格可能變動」
```

Circuit breaker 的關鍵設計點：

- **每個下游一個 breaker**，一家旅館 API 出問題不影響其他旅館。
- **Fallback 要有業務意義**：顯示快取的報價、暫時隱藏該旅館、或回傳「稍後再試」。付款這種沒有安全替代方案的操作，fallback 就是明確告訴使用者暫時無法處理，而不是假裝成功。
- 在多個 instance 或 Lambda 之間，breaker 的狀態若存在記憶體中，每個 instance 會各自判斷；需要一致判斷時，可以把狀態存在 DynamoDB 或 ElastiCache。AWS 也有以 Step Functions + DynamoDB 實作 circuit breaker 的參考模式：在呼叫下游前先查 DynamoDB 中該服務的狀態。

### Bulkhead：用隔艙把故障關在一格

**Bulkhead（隔艙）** 的名稱來自船艙：船體被分成多個密閉隔艙，一格進水不會讓整艘船沉沒。在軟體裡，就是**為不同的工作或下游分配獨立的資源池**，一個池耗盡不會影響其他池。

在 AWS 上常見的 bulkhead 做法：

- **Lambda reserved concurrency**：帳號的 Lambda 並行數是共用的（第 19 章）。如果夜間報表函式一下子用光所有並行，付款函式就會被 throttle。為付款函式設定 reserved concurrency，等於保留一個專屬隔艙；為報表函式設定上限，則限制它最多能占用多少。
- **分開的 SQS queue 與 worker**：高優先的付款確認和低優先的報表產生不要共用同一個 queue，否則報表 backlog 會讓付款訊息排在後面。
- **分開的連線池與執行緒池**：搜尋服務呼叫每家旅館 API 時使用各自有上限的連線池，一家旅館變慢最多吃光它自己的池。
- **分開的帳號、ASG 或 cell**：更大範圍的隔離，第 35 章的 cell-based architecture 與 shuffle sharding 是 bulkhead 的規模化版本。

### Backpressure：讓上游知道「慢一點」

**Backpressure（背壓）** 是讓處理不了的下游能夠「推回去」，讓上游減速，而不是硬吃下所有請求然後崩潰。

- **用 queue 吸收，並限制消費速度**：Lambda 消費 SQS 時，用 event source mapping 的 maximum concurrency 限制最多同時有幾個函式在寫 RDS；多出來的訊息留在 queue 裡等待。Queue 就是天然的背壓緩衝。
- **明確拒絕**：同步 API 在過載時回傳 HTTP 429（Too Many Requests）或 503，讓呼叫端帶 backoff 重試。API Gateway 的 throttling 與 usage plans（第 20 章）就是在入口實作這件事。
- **Queue 也需要上限的概念**：Queue 可以吸收短暫尖峰，但如果生產速度長期大於消費速度，backlog 只會無限增長，訊息延遲越來越長，最後超過 retention 被丟棄。要用 `ApproximateAgeOfOldestMessage` 告警，並準備擴展 consumer 或在入口限流、降級（第 35 章的 load shedding）。

| 模式 | 解決的問題 | AWS 上的典型實作 |
|---|---|---|
| Timeout | 無限等待占用資源 | SDK／HTTP client timeout、Lambda timeout、Step Functions `TimeoutSeconds` |
| Retry + backoff + jitter | 暫時性錯誤 | SDK standard／adaptive mode、Step Functions `Retry` |
| Circuit breaker | 持續失敗或變慢的下游拖累呼叫端 | 應用程式內實作、DynamoDB 存狀態、Step Functions 模式 |
| Bulkhead | 一個工作負載耗盡共用資源 | Lambda reserved concurrency、獨立 queue、獨立連線池、cell |
| Backpressure | 上游速度超過下游能力 | SQS 緩衝 + ESM maximum concurrency、API Gateway throttling、429 |

## 33.11 Stateless vs stateful、sync vs async

最後兩組概念是前面所有模式的基礎，考試也常直接出題。

### Stateless：讓任何一台都能處理任何請求

**Stateless（無狀態）** 元件不在自己的記憶體或本機磁碟保存跨請求的資料；每個請求需要的狀態都來自請求本身或外部儲存。**Stateful（有狀態）** 元件則把狀態留在自己身上，例如把使用者的購物車存在 web server 的記憶體裡。

Stateful 的問題在於擴展與故障：Auto Scaling 縮減時被終止的 instance 帶走了它記憶體裡的購物車；instance 故障時使用者被導到另一台，購物車就不見了。用 ALB 的 sticky session 把使用者黏在同一台可以暫時緩解，但會造成負載不均，故障時一樣遺失狀態。

正確的做法是**把狀態外部化**：session 放 ElastiCache 或 DynamoDB（第 27、28 章），上傳檔案放 S3，流程狀態交給 Step Functions。這樣每台 instance、每個 Lambda 都是可以隨時被替換的 stateless 計算單元。狀態並沒有消失，只是被集中到專門設計來可靠保存狀態的受管服務上。

### Sync vs async：使用者要等多久

**同步（synchronous）** API 讓呼叫端等待處理完成才拿到結果；**非同步（asynchronous）** API 先回應「收到了」，處理在背景進行，結果之後再取得。

Wanderly 的「匯出一年訂單報表」需要 3 分鐘，但 API Gateway REST API 的整合逾時預設是 29 秒（Regional／private API 可申請提高，但會降低帳號的節流配額）。把 timeout 調長不是好答案：使用者的瀏覽器、行動網路、負載平衡器都可能在中途斷線，而且長時間的同步請求占用資源。正確的設計是非同步 job API：

```text
① POST /reports            ──► API Gateway ──► Lambda：寫入 job（PENDING），送 SQS 或啟動 Step Functions
   ◄── 202 Accepted { "jobId": "J-77", "statusUrl": "/reports/J-77" }

② 背景 worker 產生報表 ──► 寫入 S3，job 狀態改為 COMPLETED

③ GET /reports/J-77        ──► 回傳 { "status": "COMPLETED", "downloadUrl": "<S3 presigned URL>" }
   （或改用 WebSocket／email／webhook 主動通知完成）
```

① 立即回傳 **202 Accepted** 與 job ID，請求在幾百毫秒內結束。② 背景處理不受 29 秒限制，可以用 SQS + worker、Step Functions，或第 21 章的 AWS Batch。③ 用戶端以 job ID 查詢狀態（polling），或由系統主動通知。若用戶端可能重複送出 `POST`，應讓它帶 idempotency key，避免同一份報表被建立兩次。

選擇同步或非同步的判斷依據：

| 問題 | 偏向同步 | 偏向非同步 |
|---|---|---|
| 使用者是否需要立刻知道結果才能繼續 | 是（付款授權、登入） | 否（寄信、報表、轉檔） |
| 處理時間 | 幾百毫秒到數秒 | 超過數秒、不可預測 |
| 下游是否穩定、容量足夠 | 是 | 否，需要緩衝與重試 |
| 失敗時的處理 | 直接告訴使用者 | 背景重試、DLQ、事後通知 |

## 33.12 比較與選型

### SQS、EventBridge 與 Step Functions 怎麼分工

| 需求 | 選擇 | 原因 |
|---|---|---|
| 把一件獨立的工作交給 worker、吸收尖峰 | SQS | 簡單、便宜、自帶重試與 DLQ |
| 一個事件通知多個服務，各自反應 | EventBridge（或 SNS + SQS） | 發布者不需要知道訂閱者 |
| 多步驟、有順序、分支、補償、需要知道每筆走到哪 | Step Functions Standard | 流程狀態由服務保存，可視化、可稽核 |
| 每秒數千次、幾秒內完成的短流程 | Step Functions Express | 依執行計費，高吞吐 |
| 對數百萬個 S3 物件平行執行同一流程 | Step Functions Distributed Map | 最多 10,000 個並行 child workflow |
| 等待人工或外部系統回覆 | Step Functions `.waitForTaskToken` | 等待期間不占用運算資源 |
| 在未來特定時間觸發 | EventBridge Scheduler | 第 32 章 |

### 失敗處理模式選型流程

```text
呼叫下游時遇到問題……
├─ 一直等不到回應 → 先設 timeout（由外往內遞減）
├─ 偶發的暫時錯誤 → retry + exponential backoff + jitter（只在一層）
│     └─ 操作不冪等、結果不明 → 先加 idempotency key，才可以重試
├─ 下游持續失敗或變慢 → circuit breaker + 有業務意義的 fallback
├─ 某個工作負載吃光共用資源 → bulkhead（reserved concurrency、獨立 queue／池）
├─ 上游速度長期大於下游 → backpressure（queue + 限制消費並行、429、降級）
├─ 跨多個服務的流程中途失敗 → saga + 補償交易（Step Functions 編排）
└─ 寫資料庫與發事件必須一致 → transactional outbox（或 DynamoDB Streams + Pipes）
```

## 33.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 多步驟流程、分支、錯誤處理、可視化、稽核每一步 | Step Functions Standard |
| 高頻率、短時間（< 5 分鐘）、成本敏感的流程 | Step Functions Express |
| 等待人工核准、等待外部系統回覆、不要在 Lambda 中等待 | `.waitForTaskToken` + `SendTaskSuccess`／`SendTaskFailure` |
| 對 S3 中數百萬個物件平行處理 | Distributed Map |
| 流程超過 15 分鐘、Lambda 會逾時 | Step Functions（Standard 最長 1 年）拆步驟 |
| 重試造成下游過載、同時重試的尖峰 | Exponential backoff + jitter、限制重試次數、只在一層重試 |
| 重試造成重複扣款、重複建立 | Idempotency key（DynamoDB conditional write、Powertools） |
| SQS 重複投遞、EventBridge replay 造成重複處理 | Consumer 冪等，key 保存期間涵蓋重放範圍 |
| 跨服務交易、失敗時要撤銷前面的步驟 | Saga + compensating transactions |
| 資料庫更新與事件發布必須一致 | Transactional outbox／DynamoDB Streams 觸發 |
| 某個下游變慢拖垮整個服務 | Circuit breaker + fallback、timeout |
| 一個函式用光帳號 Lambda 並行、影響關鍵函式 | Reserved concurrency（bulkhead） |
| Lambda 消費 SQS 壓垮 RDS | ESM maximum concurrency、RDS Proxy（backpressure） |
| 長時間處理但 API Gateway 29 秒逾時 | 非同步：202 + job ID + 查詢狀態 |
| Scale-in 後使用者 session 遺失 | 外部化狀態到 ElastiCache／DynamoDB |

**常見陷阱**：

1. 選「把 Lambda timeout 調到 15 分鐘並在迴圈中等待人工核准」：會超過上限且浪費成本，正解是 callback pattern。
2. 選「SQS FIFO 保證 exactly-once，不需要冪等」：FIFO 的去重只涵蓋 5 分鐘內的 producer 重送。
3. 選 Express workflow 跑需要人工核准或超過 5 分鐘的流程：Express 不支援 callback，最長 5 分鐘。
4. 選「用分散式交易同時提交資料庫與訊息服務」：SQS、SNS、EventBridge 不參與分散式交易，用 outbox。
5. 選「所有層都加重試以提高可靠性」：重試放大會讓故障惡化。
6. 以為補償等於 rollback：補償是新的業務動作（退款、取消授權），會留下紀錄。
7. 選「用 sticky session 解決 stateful 問題」：只是緩解，instance 故障時狀態仍會遺失。

## 33.14 SAP 加深：大型流程的治理、部署與遷移

### 跨帳號流程

Wanderly 的付款服務在 PCI DSS 範圍內的獨立帳號（第 50 章），訂房流程的 state machine 在訂單帳號。Step Functions 的 task 可以設定 `Credentials` 欄位，在呼叫某個步驟時 **assume 目標帳號的 IAM role**，直接呼叫另一個帳號的 Lambda、DynamoDB 等資源。這讓流程可以跨帳號編排，同時讓付款帳號以 trust policy 精確控制「哪一個 state machine 的 execution role 可以呼叫我」。另一種做法是讓 state machine 只送事件或訊息到付款帳號，由付款帳號自己的流程處理再回呼，邊界更清楚但流程較難追蹤。

### 部署與版本

正在執行中的 Standard execution 可能跑數天，如果直接修改 state machine 定義，新舊 execution 怎麼辦？Step Functions 提供 **versions（版本）與 aliases（別名）**：每次發布產生一個不可變的版本，呼叫端透過 alias 啟動 execution，alias 可以把流量依比例分配給兩個版本，實現 canary 部署（第 37 章）；執行中的 execution 會繼續使用它啟動時的版本。

### 觀測

- Standard workflow 的執行歷史本身就是稽核紀錄；Express 要開啟 CloudWatch Logs。
- 開啟 **X-Ray tracing**，可以看到一次 execution 中每個 Lambda、每個 AWS 服務呼叫的延遲。
- Step Functions 會把 execution 狀態變更事件送到 EventBridge，可以建立 rule：任何訂房 execution `FAILED` 或 `TIMED_OUT` 時通知值班人員。
- Saga 的補償本身也要監控：「補償失敗」是需要人工介入的最高優先事件，因為系統處於不一致狀態。

### 從單體交易遷移到 saga

併購的旅行社系統是一個 Oracle 單體，訂位、付款、出票在同一個資料庫交易裡。拆成微服務時（第 46 章），SAP 題目常考的判斷：

1. **不要一次拆掉交易**。先用 strangler fig 把最獨立的功能（例如通知）拆出去，透過 outbox 發布事件，核心交易仍留在單體。
2. **拆資料庫之前先設計 saga**：列出每一步的補償動作與轉折點；如果找不到合理的補償（例如出票後不可退），就把該步驟排到轉折點之後，或保留在同一個服務內。
3. **接受最終一致性的使用者體驗**：使用者會看到「訂房處理中」狀態，前端以 polling 或推播取得最終結果，客服流程也要能處理「處理中」的訂單。
4. 有些業務確實需要強一致（例如同一個帳戶餘額的扣減），就讓這些資料留在同一個資料庫、同一個服務內，不要為了微服務而拆。

### 延伸閱讀

- AWS Prescriptive Guidance：[Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)、[Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)
- Amazon Builders' Library：[Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- Step Functions：[Choosing workflow type](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)、[Error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)

## 本章重點整理

- 分散式呼叫有成功、失敗、不知道三種結果；逾時代表「不知道」，對非冪等操作盲目重試會造成重複扣款這類事故。
- 每個網路呼叫都要有 timeout，且由外往內遞減，內層的總等待時間必須小於外層（例如小於 API Gateway 的 29 秒）。
- 只重試暫時性錯誤，使用 exponential backoff + jitter、設定上限，並只在一個層級重試以避免重試放大；AWS SDK 的 standard／adaptive mode 已內建這些行為。
- Idempotency key 來自業務意圖並在重試時沿用；在 AWS 上常用 DynamoDB conditional write（`attribute_not_exists`）搶鎖並保存結果，TTL 要涵蓋所有可能的重放範圍。
- 跨網路的「剛好一次投遞」一般做不到；effectively-once = at-least-once 投遞 + 冪等處理。
- Step Functions Standard 最長 1 年、exactly-once 狀態轉換、支援 callback 與 .sync，適合付款與人工核准；Express 最長 5 分鐘、依執行計費，適合高頻短流程。
- Step Functions 的 `Retry`（含 `BackoffRate`、`MaxDelaySeconds`、`JitterStrategy`）處理暫時錯誤，`Catch` 導向補償；等待外部回呼的 task 一定要設 `TimeoutSeconds`。
- `.waitForTaskToken` 讓流程暫停等待人工或外部系統以 `SendTaskSuccess`／`SendTaskFailure` 回報，等待期間不占用運算資源。
- Inline Map 適合少量項目；Distributed Map 以 child workflow 最多 10,000 個並行處理 S3 上的大量資料；state 間資料上限 256 KB，Standard 歷史上限 25,000 個事件。
- Saga 以本地交易 + 補償交易取代分散式交易；把步驟分成可補償、轉折點、可重試，並把難以補償的步驟往後排（例如 authorize／capture）。
- Orchestration（Step Functions）集中流程、可見性高；choreography（EventBridge）耦合低、易擴充；核心交易流程用前者，結果通知用後者。
- Transactional outbox 在同一個資料庫交易寫入業務資料與待發事件，再由 relay（或 DynamoDB Streams + Pipes）發布，下游以事件 ID 冪等。
- Circuit breaker 讓持續失敗的下游快速失敗並走 fallback；bulkhead 以 reserved concurrency、獨立 queue 與連線池隔離資源；backpressure 用 queue 緩衝、限制消費並行與 429 讓上游減速。
- 把 session 與流程狀態外部化到 ElastiCache、DynamoDB、S3 或 Step Functions，讓計算層 stateless；長時間處理改成 202 + job ID 的非同步 API。

## 本章練習題

### 練習 33-1｜SAA｜單選｜選擇 workflow type

Wanderly 要為高額訂單建立審核流程：系統先做自動風險評分，分數過高時要等待風控人員審核，審核可能在數小時到兩天內完成，之後再呼叫旅館確認與請款。每一步的結果都必須保留供稽核查詢，每天約有 2,000 筆此類訂單。

最合適的做法是什麼？

- A. 使用 Step Functions Express workflow，以非同步方式啟動
- B. 使用 Step Functions Standard workflow，人工審核步驟使用 `.waitForTaskToken`
- C. 使用一個 Lambda 函式，在函式中以迴圈輪詢資料庫等待審核結果
- D. 使用 SQS delay queue，延遲兩天後再處理審核結果

> [!answer]- 答案：B
> **A ✗** Express workflow 最長只能執行 5 分鐘，且不支援 `.waitForTaskToken`，無法等待數小時到兩天的人工審核。
>
> **B ✓** Standard workflow 最長可執行 1 年，支援 callback pattern 等待人工回報，並由 Step Functions 保存每一步的執行歷史供稽核。每天 2,000 筆的量對 Standard 的計費也不成問題。
>
> **C ✗** Lambda 最長執行 15 分鐘，無法等待兩天；在函式中輪詢也會在等待期間持續計費。
>
> **D ✗** SQS delay 最長 15 分鐘，而且審核完成時間不固定，用延遲時間等待無法正確反映人工何時完成。
>
> **考點**：SAA-2.1｜Standard workflow 與 callback pattern

### 練習 33-2｜SAA｜單選｜高頻短流程的成本

Wanderly 的點擊流前處理每秒會收到約 3,000 個事件，每個事件需要經過驗證、補上地理資訊、轉換格式三個步驟，全部在 1 秒內完成。步驟都是冪等的，偶爾重複執行沒有影響。團隊想用 Step Functions 管理這三個步驟，並希望成本最低。

應選擇哪種做法？

- A. Step Functions Standard workflow，每個事件啟動一個 execution
- B. Step Functions Standard workflow，每天啟動一個 execution 並以 Map 處理全部事件
- C. Step Functions Express workflow，每個事件或每批事件啟動一個 execution
- D. 每個步驟各自用一個 SQS queue 串接三個 Lambda

> [!answer]- 答案：C
> **A ✗** Standard 依狀態轉換次數計費，每秒 3,000 個 execution、每個數個轉換，成本會非常高；Standard 的 exactly-once 保證在這裡也不需要。
>
> **B ✗** 一個 execution 處理一整天的串流資料不符合事件驅動的即時需求，而且 Standard execution 有 25,000 個歷史事件的上限。
>
> **C ✓** Express workflow 為高頻、短時間（5 分鐘內）的流程設計，依執行次數與時間計費，成本遠低於 Standard；步驟冪等，能接受非同步 Express 的 at-least-once 語意。
>
> **D ✗** 可行，但要自己管理三個 queue、DLQ 與錯誤處理，失去 workflow 的可視化與集中錯誤處理，營運負擔較高。
>
> **考點**：SAA-2.1、SAA-4.2｜Express workflow 的適用情境與計費

### 練習 33-3｜SAA｜單選｜等待外部系統回覆

Wanderly 向某家旅館集團送出訂房確認請求後，對方系統會在 5 分鐘到 6 小時內透過 HTTPS 回呼 Wanderly 的 API 告知結果。目前的做法是一個 Lambda 每分鐘查詢一次資料庫看結果到了沒有，帳單與日誌都很混亂。訂房流程已經用 Step Functions Standard workflow 實作。

最合適的改善是什麼？

- A. 在流程中加入 `Wait` state 固定等待 6 小時，再查詢結果
- B. 把確認步驟改成 Express workflow 的子流程
- C. 把 Lambda 的 timeout 調到 15 分鐘，並在函式內等待回呼
- D. 確認步驟使用 `.waitForTaskToken` 把 task token 與請求一起送出，回呼 API 收到結果後以該 token 呼叫 `SendTaskSuccess` 或 `SendTaskFailure`，並為該步驟設定 `TimeoutSeconds`

> [!answer]- 答案：D
> **A ✗** 固定等待 6 小時，讓 5 分鐘就回覆的訂單也要等 6 小時，使用者體驗很差。
>
> **B ✗** Express workflow 最長 5 分鐘且不支援 callback pattern，無法等待數小時。
>
> **C ✗** 15 分鐘仍不足以等待 6 小時，Lambda 在等待期間也持續計費。
>
> **D ✓** Callback pattern 讓 execution 暫停直到外部以 token 回報，結果一到就立刻繼續；`TimeoutSeconds` 確保對方永遠不回應時流程不會卡住，而是進入逾時處理。
>
> **考點**：SAA-2.1｜Step Functions wait for callback 與 task timeout

### 練習 33-4｜SAA｜單選｜重試造成的尖峰

Wanderly 有 800 個 worker 呼叫旅館庫存 API。當該 API 短暫過載時，所有 worker 在收到錯誤後都固定等待 1 秒再重試，監控顯示 API 每秒都出現整齊的請求尖峰，使它遲遲無法恢復。

哪個調整最能改善這個情況？

- A. 改用 exponential backoff 並加入 full jitter，設定最大等待時間與最大重試次數
- B. 把固定等待時間從 1 秒改為 0.1 秒，讓失敗的請求更快完成
- C. 移除等待時間，失敗後立刻重試，直到成功為止
- D. 讓每個 worker 改用不同的固定等待時間，例如依 worker 編號設為 1 到 8 秒

> [!answer]- 答案：A
> **A ✓** Exponential backoff 讓重試間隔隨失敗次數增加，給下游恢復的時間；full jitter 把重試時間隨機分散，消除同步尖峰；上限避免無止盡重試。
>
> **B ✗** 縮短等待只會讓重試更頻繁、尖峰更密集，加重過載。
>
> **C ✗** 無等待、無上限的重試是典型的 retry storm，會讓下游完全無法恢復。
>
> **D ✗** 固定的不同間隔仍然是週期性的，部分 worker 還是會對齊形成尖峰，而且等待時間不會隨持續失敗而增加。
>
> **考點**：SAA-2.2｜exponential backoff 與 jitter

### 練習 33-5｜SAA｜選兩項｜冪等的點數服務

Wanderly 的點數服務是一個 Lambda，消費 SQS Standard queue 中的「訂單完成」訊息並為會員加點數。最近發現少數會員被加了兩次點數。每則訊息都帶有訂單編號，同一筆訂單只應加一次點數。

哪兩個做法能解決重複加點？（選兩項）

- A. 把 queue 的 retention period 縮短為 1 小時，減少重複訊息存在的時間
- B. 以訂單編號作為 idempotency key，在加點前用 DynamoDB conditional write（`attribute_not_exists`）寫入處理紀錄，寫入失敗代表已處理過
- C. 每次收到訊息時產生一個新的 UUID 作為 idempotency key
- D. 把 idempotency 紀錄與點數異動放在同一個 DynamoDB `TransactWriteItems` 交易中，並為紀錄設定涵蓋重送與重放期間的 TTL
- E. 在 Lambda 中先呼叫 `DeleteMessage` 再加點數，確保訊息只會被處理一次

> [!answer]- 答案：B、D
> **A ✗** Retention 與重複投遞無關；Standard queue 的偶發重複與 visibility timeout 到期重投都會在 retention 內發生。
>
> **B ✓** 以業務上唯一的訂單編號作為 key，conditional write 保證同一筆訂單只有一個請求能寫入成功，即使兩則重複訊息同時被兩個 Lambda 處理也一樣。
>
> **C ✗** 每次產生新 UUID 代表重複的訊息會得到不同的 key，完全無法辨識重複。
>
> **D ✓** 把處理紀錄與點數異動放在同一個交易，避免「紀錄寫了、點數沒加」或「點數加了、紀錄沒寫」的不一致；TTL 讓紀錄在不再需要時自動清除，又能涵蓋 DLQ redrive 等重放期間。
>
> **E ✗** 先刪除訊息再處理，Lambda 若在加點前失敗，訊息就永久遺失，從可能重複變成可能遺失。
>
> **考點**：SAA-2.2｜idempotency key 與 DynamoDB conditional write

### 練習 33-6｜SAA｜單選｜大量 S3 物件的平行處理

Wanderly 要為 S3 bucket 中約 500 萬張旅館照片產生新的 WebP 格式縮圖，每張處理約 2 秒。團隊希望在數小時內完成、能追蹤失敗的項目並重新處理，且不想自己管理 worker 叢集或撰寫分派工作的程式。

最合適的做法是什麼？

- A. 寫一個 Lambda 函式，用迴圈列出所有物件並逐一處理
- B. 用 Step Functions inline Map state，輸入為所有物件 key 組成的陣列
- C. 在 EC2 Auto Scaling group 上執行 worker，由一台 coordinator instance 分派工作
- D. 用 Step Functions Distributed Map，以 S3 prefix 作為項目來源、批次交給 child workflow 處理，並設定容許失敗比例與結果輸出到 S3

> [!answer]- 答案：D
> **A ✗** 單一 Lambda 最長 15 分鐘，500 萬張 × 2 秒遠遠超過；也沒有平行處理。
>
> **B ✗** Inline Map 的並行度有限，500 萬個 key 的陣列也遠超過 state 之間 256 KB 的資料上限，所有 iteration 還會累積在同一個 execution 的歷史中。
>
> **C ✗** 可以完成，但需要自己管理叢集、分派與失敗重試，正是題目不想要的營運負擔。
>
> **D ✓** Distributed Map 可直接從 S3 讀取項目，最多 10,000 個 child workflow 並行，失敗項目可追蹤並寫入結果，不需要任何 worker 叢集。
>
> **考點**：SAA-3.2、SAA-2.1｜Step Functions Distributed Map

### 練習 33-7｜SAA｜單選｜超過 API 逾時的處理

Wanderly 的「匯出年度訂單」功能透過 API Gateway REST API 呼叫 Lambda，產生報表需要 2 到 5 分鐘。使用者經常收到 504 逾時錯誤，有些人以為失敗就重複點擊，造成同一份報表被產生多次。

最合適的設計是什麼？

- A. 申請把 API Gateway 整合逾時提高到 10 分鐘，並把 Lambda timeout 設為 15 分鐘
- B. API 收到請求後寫入 job 紀錄並把工作送到 SQS 或啟動 Step Functions，立即回傳 202 與 job ID；用戶端以 job ID 查詢狀態並帶 idempotency key 送出請求
- C. 改用 ALB 呼叫 Lambda 以避開 API Gateway 的逾時限制
- D. 在前端加入 JavaScript 自動重試，直到請求在 29 秒內完成

> [!answer]- 答案：B
> **A ✗** 讓使用者連線等待數分鐘很脆弱：網路、瀏覽器、負載平衡器都可能中斷，也不解決重複點擊的問題。
>
> **B ✓** 非同步 job API 讓請求在幾百毫秒內回應，處理在背景完成，不受 29 秒限制；idempotency key 讓重複提交不會產生多份報表。
>
> **C ✗** 換入口只是換了一個逾時限制，長時間的同步請求本質問題沒有解決。
>
> **D ✗** 重試不會讓 5 分鐘的工作在 29 秒內完成，反而每次重試都觸發新的報表產生。
>
> **考點**：SAA-2.1｜同步 vs 非同步與 202 Accepted 模式

### 練習 33-8｜SAA｜單選｜Scale-in 後購物車消失

Wanderly 的 web tier 跑在 ALB 後面的 EC2 Auto Scaling group，使用者的「暫存行程」存在每台 instance 的記憶體中，並啟用了 ALB sticky session。每次 ASG 縮減或 instance 被替換時，部分使用者的暫存行程就會消失。

最合適的修正是什麼？

- A. 把 sticky session 的 cookie 有效期間延長為 7 天
- B. 停用 Auto Scaling 的 scale-in，只允許擴展
- C. 把暫存行程存到 ElastiCache 或 DynamoDB，讓 web tier 成為 stateless 並可移除 sticky session
- D. 把每台 instance 的記憶體中資料每小時備份到 EBS snapshot

> [!answer]- 答案：C
> **A ✗** Cookie 期間再長，instance 被終止時記憶體中的資料仍會消失。
>
> **B ✗** 停用 scale-in 會浪費成本，而且 instance 故障或替換時資料一樣會遺失。
>
> **C ✓** 把狀態外部化到 ElastiCache 或 DynamoDB，任何 instance 都能處理任何請求，scale-in 與故障都不會遺失資料，也能移除造成負載不均的 sticky session。
>
> **D ✗** EBS snapshot 是磁碟備份，不會包含記憶體中的資料，還原也無法讓其他 instance 取用。
>
> **考點**：SAA-2.2｜stateless 設計與狀態外部化

### 練習 33-9｜SAA｜單選｜關鍵函式被 throttle

每天凌晨 2 點，Wanderly 的報表 Lambda 會被大量觸發，在短時間內使用掉帳號的大部分 Lambda 並行數。這段時間內，負責處理付款回呼的 Lambda 頻繁出現 throttling，造成付款確認延遲。

以最少變更解決問題的做法是什麼？

- A. 為付款回呼函式設定 reserved concurrency，並為報表函式設定較低的 reserved concurrency 作為上限
- B. 把付款回呼函式的記憶體加倍，讓它執行更快
- C. 把報表函式改成在 EC2 上執行
- D. 為付款回呼函式設定 provisioned concurrency，並移除報表函式的所有限制

> [!answer]- 答案：A
> **A ✓** 這是 bulkhead：reserved concurrency 為付款函式保留一定的並行數，其他函式無法占用；為報表函式設定上限，則限制它最多能用多少。兩者都只是函式設定，變更最少。
>
> **B ✗** 執行更快可以稍微降低並行需求，但報表函式仍可能用光帳號並行，付款函式還是會被 throttle。
>
> **C ✗** 搬到 EC2 可以隔離資源，但需要改寫與管理伺服器，不是最少變更。
>
> **D ✗** Provisioned concurrency 會預先初始化指定數量的執行環境，在這個數量以內付款函式確實不受影響；但它的主要目的是消除 cold start，而且不論有沒有流量都要持續付費。超過配置量的請求仍要和其他函式共用未保留的並行額度，而「移除報表函式的所有限制」會讓報表函式繼續把這部分占滿。要隔離容量，不另收費的 reserved concurrency 才是最直接的 bulkhead 工具。
>
> **考點**：SAA-3.2、SAA-2.2｜Lambda reserved concurrency 作為 bulkhead

### 練習 33-10｜SAA｜單選｜Lambda 消費者壓垮資料庫

促銷期間 Wanderly 的訂單 queue 堆積數十萬則訊息，消費它的 Lambda 自動擴展到數百個並行，每個都開啟資料庫連線寫入 RDS for MySQL，導致 RDS 連線數耗盡，連其他服務也無法連線。業務可以接受訂單在數分鐘內完成處理。

最合適的做法是什麼？

- A. 把 queue 改成 SNS topic，讓訊息直接推送給 Lambda
- B. 把 SQS 的 visibility timeout 調短，讓失敗的訊息更快重試
- C. 把 RDS 的 instance 規格升級到最大
- D. 在 SQS event source mapping 設定 maximum concurrency 限制並行數，讓訊息留在 queue 中排隊，並透過 RDS Proxy 共用連線

> [!answer]- 答案：D
> **A ✗** SNS 推送沒有緩衝能力，Lambda 的並行會更直接地反映流量，對資料庫的壓力更大。
>
> **B ✗** Visibility timeout 縮短只會增加重複處理，不會降低並行數，反而增加資料庫負擔。
>
> **C ✗** 升級規格可以暫時提高連線上限，但只要 Lambda 並行繼續成長，問題仍會再次發生，而且成本高。
>
> **D ✓** 這是 backpressure：maximum concurrency 限制同時處理的數量，多出來的訊息留在 queue 中等待，業務可以接受數分鐘延遲；RDS Proxy 讓多個 Lambda 共用連線池，進一步保護資料庫。
>
> **考點**：SAA-2.1、SAA-3.3｜SQS 緩衝與 ESM maximum concurrency 的背壓

### 練習 33-11｜SAP｜單選｜Saga 步驟順序

Wanderly 的訂房 saga 目前的步驟是：保留房間 → 從信用卡扣款 → 請旅館正式確認（不可退款房價，確認後不能取消）→ 寄確認信。旅館確認失敗率約 2%，每次失敗都要退款，產生手續費與客訴。金流商支援先授權、後請款，授權可以免費取消。

哪個調整最能降低補償成本並維持一致性？

- A. 在扣款步驟加入更多重試次數，讓扣款更穩定
- B. 改為保留房間 → 信用卡授權 → 旅館確認 → 請款 → 寄確認信；授權後若確認失敗則取消授權並釋放房間，確認之後的步驟只重試不補償
- C. 把旅館確認移到第一步，確認成功後再保留房間與扣款
- D. 用分散式交易（two-phase commit）把金流商與旅館系統的操作放在同一個交易

> [!answer]- 答案：B
> **A ✗** 問題不在扣款失敗，而在扣款之後的確認失敗需要退款；增加扣款重試無法降低退款。
>
> **B ✓** 授權是便宜的可補償步驟，旅館確認是轉折點，請款與寄信在轉折點之後只需保證最終完成。確認失敗時的補償從退款變成免費的取消授權，使用者幾乎感受不到。
>
> **C ✗** 先做不可取消的確認，若之後付款失敗就無法補償，Wanderly 必須承擔已確認的房間，順序反而更危險。
>
> **D ✗** 外部的金流商與旅館系統不會參與 Wanderly 的分散式交易，這在跨組織系統中不可行。
>
> **考點**：SAP-2.4、SAP-3.4｜saga 的可補償步驟、轉折點與步驟順序

### 練習 33-12｜SAP｜選兩項｜訂單建立與事件發布不一致

Wanderly 的訂單服務在 Aurora PostgreSQL 交易提交後呼叫 EventBridge `PutEvents` 發布 `BookingRequested`。監控顯示每天有數十筆訂單停在 PENDING 狀態，原因是交易已提交但程式在發布事件前當機或發布失敗。團隊要求每一筆提交的訂單最終都會發布事件，且不新增需要人工對帳的流程。

哪兩個做法組合起來最合適？（選兩項）

- A. 在同一個資料庫交易中寫入訂單與一筆 outbox 紀錄，由獨立的 relay 讀取未發布的 outbox 紀錄並發布到 EventBridge，成功後標記為已發布
- B. 把 `PutEvents` 移到交易提交之前呼叫，確保事件一定先送出
- C. 下游消費者以事件中的唯一事件 ID 實作冪等，因為 relay 可能在發布後、標記前當機而重複發布
- D. 使用 XA 分散式交易同時提交 Aurora 與 EventBridge
- E. 每晚執行批次程式，比對 PENDING 訂單並請客服人員手動處理

> [!answer]- 答案：A、C
> **A ✓** Transactional outbox 把「寫訂單」與「記錄待發事件」放在同一個本地交易，兩者一起成功或失敗；relay 會持續重試未發布的紀錄，保證每筆提交的訂單最終都會發布事件。
>
> **B ✗** 先發事件再提交，交易若 rollback，就發出了一個不存在的訂單的事件，只是把不一致換成另一個方向。
>
> **C ✓** Outbox 提供 at-least-once 發布，relay 重啟後可能重送已發布的事件；消費者依事件 ID 冪等才能讓效果只發生一次。
>
> **D ✗** EventBridge 不參與 XA 或 two-phase commit 交易，這個做法無法實作。
>
> **E ✗** 人工對帳違反「不新增人工流程」的要求，也只能事後補救，無法保證即時一致。
>
> **考點**：SAP-2.4、SAP-4.4｜transactional outbox 與冪等消費者

### 練習 33-13｜SAP｜單選｜慢速的旅館 API 拖垮搜尋

Wanderly 的搜尋服務跑在 ECS 上，每個搜尋請求會平行呼叫 30 家旅館的報價 API，再合併結果。某家旅館的 API 開始每次都要 25 秒才逾時，搜尋服務的執行緒與連線很快被耗盡，所有搜尋都變慢。業務可以接受該旅館暫時以快取報價顯示並標示「價格可能變動」。

最合適的改善組合是什麼？

- A. 為所有旅館 API 呼叫增加重試次數，確保拿到最新報價
- B. 把 ECS service 的 task 數量加倍以提供更多執行緒
- C. 為每家旅館 API 設定較短的 timeout 與獨立的連線池，並為每家旅館使用 circuit breaker，斷路時以快取報價作為 fallback
- D. 把所有旅館 API 呼叫改為透過 SQS 非同步處理，搜尋結果在數分鐘後以 email 寄給使用者

> [!answer]- 答案：C
> **A ✗** 對一個持續逾時的下游增加重試，只會讓每個搜尋請求等得更久、占用更多資源，加重問題。
>
> **B ✗** 加倍 task 只是增加被耗盡的資源量，慢速 API 仍會逐漸占滿新增的執行緒，而且成本上升。
>
> **C ✓** 短 timeout 限制每次等待的成本；獨立連線池（bulkhead）讓一家旅館最多耗盡自己的池；circuit breaker 偵測持續失敗後直接走 fallback，不再呼叫有問題的 API，冷卻後再試探恢復。快取報價是業務可接受的替代結果。
>
> **D ✗** 搜尋是互動式功能，使用者需要即時看到結果，改成數分鐘後寄 email 不符合需求。
>
> **考點**：SAP-3.4、SAP-2.4｜circuit breaker、timeout 與 bulkhead

### 練習 33-14｜SAP｜單選｜長時間迴圈的 workflow 失敗

Wanderly 的每月對帳流程用 Step Functions Standard workflow 實作：以 `Choice` 與 `Task` 組成的迴圈，逐筆處理約 3 萬筆旅館結算資料。流程在處理到約 8,000 筆時失敗，錯誤顯示 execution 的歷史事件數超過上限。每筆處理彼此獨立，結算資料以 CSV 檔存放在 S3。

最合適的修正是什麼？

- A. 改用 Distributed Map，以 S3 中的 CSV 作為項目來源，由 child workflow 平行處理每批資料
- B. 改用 Express workflow，因為 Express 沒有歷史事件上限
- C. 申請提高該 execution 的歷史事件上限
- D. 把迴圈改成在單一 Lambda 函式中處理全部 3 萬筆資料

> [!answer]- 答案：A
> **A ✓** Standard execution 的歷史事件上限是 25,000 個，自己寫的迴圈每筆會產生多個事件，很快就超過。Distributed Map 讓每批資料在各自的 child workflow 中執行，歷史分散在 child execution，並可以直接讀取 S3 的 CSV、平行處理，加快整體完成時間。
>
> **B ✗** Express 確實沒有 25,000 個歷史事件的上限，但它最長只能執行 5 分鐘，處理 3 萬筆對帳資料的時間可能超過；改 workflow type 也必須重建 state machine，且失去 Standard 的稽核歷史。
>
> **C ✗** 歷史事件數是固定上限，無法透過申請提高；正確做法是改變流程結構。
>
> **D ✗** 單一 Lambda 最長 15 分鐘，3 萬筆資料可能無法完成，而且失去逐筆的失敗追蹤與重試。
>
> **考點**：SAP-3.4、SAP-3.1｜Standard 歷史事件上限與 Distributed Map

### 練習 33-15｜SAP｜選兩項｜重複扣款的根因

Wanderly 的付款流程是 Step Functions Standard workflow，其中 `ChargeCard` task 呼叫 Lambda，Lambda 再呼叫金流商 API。該 task 設定了對 `States.Timeout` 的 Retry，Lambda 呼叫金流商的 timeout 為 10 秒。調查發現，重複扣款都發生在金流商回應超過 10 秒的時候。團隊原本以為 Standard workflow 的 exactly-once 會防止重複。

哪兩個敘述或做法是正確的？（選兩項）

- A. Standard workflow 的 exactly-once 保證狀態轉換只發生一次，但 Retry 會讓同一個 task 再次執行，外部副作用仍可能重複
- B. 改用 Express workflow 就能避免重複執行
- C. 以訂單編號產生固定的 idempotency key 並在每次呼叫金流商時帶上，重試時沿用同一個 key
- D. 把 Retry 的 `MaxAttempts` 改為 0，並在逾時後直接標示訂單失敗、讓使用者重新付款
- E. 在 `ChargeCard` 前加入 SQS FIFO queue，利用 5 分鐘去重防止重複扣款

> [!answer]- 答案：A、C
> **A ✓** Exactly-once 指的是 workflow 的狀態轉換，不涵蓋 task 呼叫的外部系統。逾時代表結果不明，第一次請求可能已在金流商成功，Retry 再呼叫一次就重複扣款。
>
> **B ✗** 非同步 Express 是 at-least-once，重複執行的可能性只會更高，不會更低。
>
> **C ✓** 金流商以 idempotency key 判斷是否為同一筆請求，重試時沿用相同 key，就算第一次已成功，第二次也只會回傳原本的結果，不會再扣款。這讓重試變得安全。
>
> **D ✗** 不重試並讓使用者重新付款，第一次請求若其實已成功，使用者重新付款仍然會被扣兩次，問題沒有解決。
>
> **E ✗** FIFO 去重只防止 5 分鐘內相同訊息重複送入 queue，不影響 Step Functions 對同一個 task 的重試，也不知道金流商端的結果。
>
> **考點**：SAP-2.4、SAP-3.4｜exactly-once 的範圍與 idempotency key

### 練習 33-16｜SAP｜單選｜Choreography 流程失去可見性

Wanderly 的訂房流程目前以 choreography 方式實作：庫存、支付、旅館整合、通知四個服務透過 EventBridge 事件彼此觸發，每個服務自己處理失敗與補償。隨著步驟增加，客服經常無法回答「某筆訂單現在卡在哪」，部分補償事件遺失導致授權沒有取消。公司希望提高流程可見性與補償的可靠性，同時讓其他團隊（點數、分析）仍能以事件方式接收訂房結果。

最合適的目標架構是什麼？

- A. 在每個服務加入更詳細的日誌，並把日誌集中到 CloudWatch Logs 供客服查詢
- B. 把四個服務合併成一個大型 Lambda 函式，用 try／except 處理補償
- C. 為每個事件類型建立獨立的 SNS topic，讓服務之間的訊息更可靠
- D. 以 Step Functions Standard workflow 編排訂房 saga（每筆訂單一個 execution，以訂單編號為 execution name），在 Catch 中集中執行補償；流程完成後發布 `BookingConfirmed` 事件到 EventBridge 供其他團隊訂閱

> [!answer]- 答案：D
> **A ✗** 集中日誌有助於除錯，但不會讓流程狀態變得一目了然，也不能修正補償事件遺失的根本問題。
>
> **B ✗** 單一 Lambda 受 15 分鐘限制，無法等待外部回覆，所有服務也被重新耦合在一起，失去獨立部署。
>
> **C ✗** 換成 SNS 只是換了傳遞方式，流程與補償依然分散在各服務中，可見性問題沒有改善。
>
> **D ✓** Orchestration 讓每筆訂單的狀態集中在一個 execution 中，客服可直接查詢走到哪一步；補償由 Catch 集中觸發並可重試。以訂單編號當 execution name 防止重複啟動。完成後發布事件，下游團隊仍以 choreography 方式接收結果，兩種模式各取所長。
>
> **考點**：SAP-4.4、SAP-3.1｜orchestration vs choreography 的選擇
