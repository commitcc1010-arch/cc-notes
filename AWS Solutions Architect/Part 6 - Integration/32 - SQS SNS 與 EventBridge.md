---
chapter: 32
title: SQS、SNS、EventBridge 與 Amazon MQ
part: 6
---

# 第 32 章　非同步解耦：SQS、SNS、EventBridge 與 Amazon MQ

> [!abstract] 本章地圖
> **你會學到**：
> - 說明同步呼叫為什麼會讓一個慢服務拖垮整條流程，以及 queue、topic、event bus 各自解決哪一種耦合
> - 正確設定 SQS 的 visibility timeout、long polling、delay、retention 與 DLQ，並解釋一則訊息從送出到刪除的完整生命週期
> - 判斷何時用 Standard queue、何時用 FIFO queue，並用 message group ID 同時取得順序與平行度
> - 用 SNS 搭配多個 SQS queue 做可靠的 fan-out，並用 filter policy 讓每個訂閱者只收到自己要的訊息
> - 用 EventBridge 的 rules、archive／replay、跨帳號 event bus、Pipes 與 Scheduler 建立事件驅動架構
> - 在 SQS、SNS、EventBridge、Kinesis 與 Amazon MQ 之間依題目關鍵字做出選擇
>
> **前置知識**：第 4 章（同步 vs 非同步、loose coupling）、第 19 章（Lambda invocation types）
> **考試比重**：SAA ★★★（Domain 2 解耦與高可用、Domain 3 資料擷取）｜SAP ★★★（Domain 2 可靠性、Domain 4 現代化）

## 32.1 故事：一封確認信讓整個結帳卡住

Wanderly 進入成長期後，訂房流程變得越來越長。使用者按下「確認付款」時，訂單服務會依序做六件事：寫入訂單資料庫、呼叫金流、呼叫旅館的庫存 API、寄確認信、幫會員加點數、送一筆紀錄給分析系統。這六件事全部寫在同一個 HTTP request 裡，一件做完才做下一件。

第一次出事是在一個連假前的晚上。寄信用的第三方服務變慢，每封信要 20 秒才回應。訂單服務的每個 request 因此卡在「寄信」這一步，執行緒一個接一個被占住，很快就沒有執行緒可以接新的結帳請求。使用者看到的不是「信寄得比較慢」，而是「付款頁面轉圈圈然後失敗」。寄信根本不影響訂房是否成立，卻讓整個結帳停擺。

第二次出事是促銷活動。結帳量在十分鐘內暴增 20 倍，分析系統的寫入 API 扛不住，開始回傳錯誤；訂單服務把這些錯誤當成失敗，回滾了已經扣款的訂單。工程師小林在事後檢討寫下一句話：「我們把『必須馬上完成的事』和『晚一點完成也沒關係的事』綁在一起了。」

技術主管給的新方向是：結帳 request 只做真正必須同步完成的步驟（寫訂單、確認付款），其他事情變成「訂單已成立」這個事件發生後，由各自的服務在自己的步調下處理。這一章介紹 AWS 上實現這個想法的四個服務：SQS、SNS、EventBridge 與 Amazon MQ。下一章（第 33 章）再處理更難的部分：付款、扣庫存這種多步驟流程失敗時要怎麼收拾。

## 32.2 為什麼要解耦：同步呼叫的兩種綁定

先把問題講清楚。當服務 A 同步呼叫服務 B，A 和 B 之間其實有兩種綁定：

- **時間耦合（temporal coupling）**：B 必須在 A 呼叫的那一刻活著而且回得夠快。B 停機五分鐘，A 在這五分鐘內的相關功能全部失敗。
- **容量耦合（capacity coupling）**：A 送多快，B 就必須處理多快。A 突然來了 20 倍流量，B 也得瞬間撐住 20 倍，否則就回傳錯誤。

**解耦（decoupling）** 的做法是在中間放一個可靠的中介者：A 把工作或事件交給中介者就算完成，中介者負責保存，B 在自己方便的時候取走處理。B 暫時掛掉，訊息就在中介者那裡等；流量暴增，訊息就先堆起來，B 用固定速度慢慢消化。這種「先存起來、削平尖峰」的效果常被稱為 **load leveling（負載平準）**。

```text
改造前（同步串接）：
使用者 ─► 訂單服務 ─► 金流 ─► 旅館 API ─► 寄信 ─► 點數 ─► 分析
                      任何一站變慢或失敗，使用者都在等

改造後（核心同步，其餘非同步）：
使用者 ─► 訂單服務 ─► 金流（同步，必須知道結果）
              │
              │ ① 發布「BookingConfirmed」事件
              ▼
        [中介者：topic / event bus]
         │          │           │
         ▼ ②        ▼           ▼
     [queue]     [queue]     [queue]      ③ 每個消費者有自己的 queue
         │          │           │
      寄信服務    點數服務     分析管線      ④ 各自依自己的速度拉取
```

① 訂單服務只負責宣告「這筆訂單成立了」，不再知道有誰在乎這件事。② 中介者把同一個事件複製給每個訂閱者。③ 每個訂閱者前面有一個自己的 queue，寄信服務變慢只會讓「寄信 queue」堆積，不影響點數服務。④ 消費者用拉取（pull）的方式自己控制處理速度。

這張圖裡出現了兩種不同的中介者，它們的差別是本章的主軸：

| 模式 | 一則訊息給幾個接收者 | 誰主動 | AWS 服務 |
|---|---|---|---|
| **Queue（佇列，point-to-point）** | 一個（多個 worker 競爭同一則訊息，誰拿到誰處理） | 消費者拉取（pull） | SQS、Amazon MQ |
| **Publish/subscribe（發布訂閱）** | 每個訂閱者都拿到一份 | 服務推送（push） | SNS、EventBridge、Amazon MQ |
| **Stream（串流）** | 多個消費者各自依位置讀取、可重讀 | 消費者拉取 | Kinesis、MSK（第 31 章） |

> [!warning] 常見誤解
> 「非同步就一定比較好。」非同步讓系統更有彈性，但使用者不會馬上知道結果，資料會有短暫不一致，除錯也比較難。付款授權這種「使用者必須立刻知道成功與否」的步驟仍然應該同步。解耦的判斷標準是：這件事晚幾秒、幾分鐘完成，業務能不能接受？

## 32.3 SQS 的運作：一則訊息的一生

**Amazon SQS（Simple Queue Service）** 是全受管的訊息佇列。你不需要管理任何伺服器或叢集，建立一個 queue 就能用，容量自動擴展。SQS 是 Regional 服務，訊息會被冗餘儲存在多個 AZ。

理解 SQS 最好的方式是跟著一則訊息走完它的生命週期：

```text
Producer                    SQS queue                         Consumer
   │ ① SendMessage            │                                  │
   ├─────────────────────────►│ 訊息狀態：visible（可被取走）     │
   │                          │                                  │
   │                          │◄──────── ② ReceiveMessage ────────┤
   │                          │──── 訊息 + receipt handle ───────►│
   │                          │ 訊息狀態：in flight（暫時隱藏）    │
   │                          │ visibility timeout 開始倒數       │ ③ 處理中…
   │                          │                                  │
   │                          │◄──── ④a DeleteMessage(handle) ────┤ 處理成功
   │                          │ 訊息永久刪除                       │
   │                          │                                  │
   │                          │ ④b 若 timeout 到期仍未刪除：        │ 處理失敗或當機
   │                          │    訊息重新變成 visible，            │
   │                          │    另一個 consumer 可以再取走        │
```

① Producer 呼叫 `SendMessage` 把訊息放進 queue，SQS 確認寫入後才回應成功。② Consumer 呼叫 `ReceiveMessage` 主動拉取，一次最多取 10 則。SQS 回傳訊息內容和一個 **receipt handle（收據代碼）**，這是之後刪除或延長這則訊息時要用的憑證。③ 訊息被取走後**不會被刪除**，而是進入 in flight 狀態，在 **visibility timeout（可見性逾時）** 期間對其他 consumer 隱藏。④a Consumer 處理成功後必須明確呼叫 `DeleteMessage`，訊息才真正消失。④b 若 consumer 在處理途中當機，或處理時間超過 visibility timeout，訊息會重新出現，讓其他 consumer 再試一次。

這個設計的核心想法是：**SQS 不相信 consumer 一定會成功**。只有 consumer 明確說「我做完了」，訊息才會被刪除。這保證了工作不會因為某台 worker 當機而遺失，但也帶來一個必然的後果：**同一則訊息可能被處理不只一次**。

### Standard queue 的 at-least-once

SQS 預設的 **Standard queue** 提供 **at-least-once delivery（至少一次投遞）**：每則訊息至少會被投遞一次，偶爾會投遞兩次以上。原因有兩個：一是上面的 visibility timeout 到期重投，二是 SQS 為了高可用把訊息存在多台伺服器上，在少數情況下某台伺服器暫時不可用，刪除沒有同步到它，之後它又把訊息交出去。

Standard queue 也只提供 **best-effort ordering（盡力排序）**：大致按照送入順序，但不保證。換來的是幾乎沒有上限的吞吐量。

所以使用 Standard queue 的 consumer 必須是 **idempotent（冪等）** 的：同一則訊息處理兩次，結果和處理一次相同。例如「把訂單 B-1001 的確認信狀態設為已寄出」是冪等的；「幫會員加 100 點」不是，處理兩次就會加 200 點。冪等的具體實作方法在第 33 章詳細說明。

### Retention：訊息最多等多久

訊息不會永遠留在 queue 裡。**Message retention period（保留期間）** 可以設定為 1 分鐘到 14 天，預設 4 天。超過保留期間還沒被刪除的訊息會被 SQS 自動丟棄。如果你的 consumer 可能因為事故停擺一個週末，4 天通常夠；如果需要保留更久的歷史資料供重讀，SQS 就不是正確的工具，應該考慮第 31 章的 Kinesis 或把資料寫入 S3。

## 32.4 三個時間參數：visibility timeout、long polling 與 delay

SQS 有好幾個以秒為單位的設定，考試很喜歡讓它們互相混淆。我們一個一個看。

### Visibility timeout：給 consumer 的處理時限

Visibility timeout 預設 30 秒，可設定 0 秒到 12 小時。它應該**大於 consumer 正常處理一則訊息所需的時間**。

- 設太短：consumer 還在處理，訊息就重新出現並被另一個 consumer 取走，同一份工作被兩台機器同時執行。這是「重複處理」最常見的原因。
- 設太長：consumer 當機時，訊息要等很久才會重新出現，失敗恢復變慢。

如果處理時間差異很大（大部分 30 秒，少數 10 分鐘），不要把 timeout 一律設成最長情況。比較好的做法是用一般情況的 timeout，處理長工作時由 consumer 定期呼叫 **`ChangeMessageVisibility`** 延長時限，這種做法常被稱為 heartbeat（心跳）。注意整體上限：從訊息第一次被取走起算，最多只能隱藏 12 小時。超過這個長度的工作不適合直接由 SQS 管理，應該交給第 33 章的 Step Functions。

### Long polling：減少空手而回

Consumer 呼叫 `ReceiveMessage` 時，如果 queue 是空的，**short polling（短輪詢）** 會立刻回傳空結果；consumer 只好不斷重試，產生大量「空的」API 呼叫。SQS 按 API request 次數收費，空呼叫也要錢。

**Long polling（長輪詢）** 讓 `ReceiveMessage` 在 queue 沒有訊息時最多等待 20 秒，有訊息一到就立刻回傳。設定方式是把 queue 的 `ReceiveMessageWaitTimeSeconds` 設為 1–20 秒，或在每次呼叫時帶 `WaitTimeSeconds`。效果是空回應大幅減少、成本下降、訊息到達後也能更快被取走。

Short polling 還有一個不太直覺的特性：它只查詢部分 SQS 伺服器，所以 queue 裡訊息很少時，可能一次查不到訊息；long polling 會查詢所有伺服器。實務上幾乎所有情境都應該使用 long polling。

### Delay：讓訊息晚一點才能被看見

**Delay queue（延遲佇列）** 讓新送入的訊息在一段時間內（0–15 分鐘）對 consumer 不可見。可以設在整個 queue 上（`DelaySeconds`），Standard queue 也能對單則訊息設定 **message timer**；FIFO queue 只支援整個 queue 層級的延遲。

用途例如：Wanderly 在使用者取消訂單後，希望 10 分鐘後再檢查退款是否完成。要等更久（例如入住前 3 天提醒），就超過 SQS 的能力，應該改用 32.10 節的 EventBridge Scheduler。

### 四個時間參數對照

| 參數 | 作用對象 | 範圍（預設） | 解決什麼問題 |
|---|---|---|---|
| Visibility timeout | 已被取走的訊息 | 0 秒–12 小時（30 秒） | 處理中不要被別人重複取走 |
| Receive wait time（long polling） | `ReceiveMessage` 呼叫 | 0–20 秒（0，即 short polling） | 減少空回應與成本 |
| Delay | 剛送入的訊息 | 0–15 分鐘（0） | 延後訊息第一次可見的時間 |
| Retention | 所有訊息 | 1 分鐘–14 天（4 天） | 訊息最多保存多久 |

> [!tip] 考試提示
> 「同一份工作偶爾被兩個 worker 同時處理」→ visibility timeout 太短。「queue 空的時候 API 呼叫很多、成本高」→ long polling。「訊息要延後幾分鐘才處理」→ delay queue。「訊息莫名消失」→ 檢查 retention 或是否在處理前就刪除。四個參數各管一件事，不能互相替代。

## 32.5 Standard vs FIFO：順序、去重與吞吐的取捨

Wanderly 的庫存同步服務遇到一個問題：同一筆訂房先送出「建立」再送出「取消」，但 consumer 有時先收到「取消」，因為找不到訂單而失敗，接著才收到「建立」，結果一筆已取消的訂房被當成有效訂房。這種情況需要的是 **FIFO queue**。

### FIFO queue 提供什麼

**SQS FIFO（First-In-First-Out）queue** 的名稱必須以 `.fifo` 結尾，它提供兩個 Standard 沒有的保證：

1. **順序**：同一個 **message group ID（訊息群組 ID）** 內的訊息，嚴格按照送入順序被處理。
2. **去重（deduplication）**：在 **5 分鐘的去重區間** 內，帶有相同 **deduplication ID** 的訊息只會被接受一次。Deduplication ID 可以由 producer 明確提供，也可以開啟 **content-based deduplication**，由 SQS 用訊息內容的 SHA-256 雜湊自動產生。

AWS 把這兩個保證合稱為 **exactly-once processing**。但請注意它的範圍：去重只防止「producer 重送」在 5 分鐘內造成重複訊息；consumer 處理到一半當機、visibility timeout 到期，訊息仍然會被重新投遞。所以 FIFO queue 的 consumer 一樣需要冪等（第 33 章會詳細拆解「exactly-once 的錯覺」）。

### Message group ID：順序與平行度的旋鈕

FIFO 的順序是「每個 message group 內」的順序，而不是整個 queue 的順序。這是理解 FIFO 的關鍵：

```text
FIFO queue: booking-sync.fifo

group = B-1001 : [建立] → [修改] → [取消]      依序，一次只處理一則
group = B-1002 : [建立] → [取消]               依序
group = B-1003 : [建立]

worker-1 處理 B-1001 的「建立」時，B-1001 的「修改」會等它完成；
worker-2 可以同時處理 B-1002，worker-3 處理 B-1003。
```

同一個 group 內，前一則訊息還在 in flight 時，後面的訊息不會被交給任何 consumer，這保證了順序，但也表示**單一 group 只能被序列化處理**。如果把所有訊息都放在同一個 group（例如 group ID 固定是 `all`），整個 queue 就退化成一次只處理一則，吞吐量極低。

正確的做法是：**用「需要保持順序的業務單位」當 group ID**。Wanderly 只要求同一筆訂房的事件有序，所以 group ID 用訂房編號；不同訂房之間不需要順序，就能平行處理。

### 吞吐量

- Standard queue：吞吐量幾乎沒有上限。
- FIFO queue：預設每個 API 動作（send、receive、delete）每秒 300 次呼叫；使用 batch（一次最多 10 則）時相當於每秒 3,000 則訊息。開啟 **high throughput mode** 可再大幅提高（上限依 Region 而定，例如東京為每秒 9,000 次非 batch 呼叫，維吉尼亞北部為 70,000 次），但吞吐量是分散到各個 message group 的，group 數量太少仍然會受限。

### 其他 FIFO 限制

- 不能把 Standard queue 直接轉成 FIFO queue，必須建立新的 queue 再切換 producer 與 consumer。
- FIFO queue 的 DLQ 也必須是 FIFO queue；Standard 的 DLQ 必須是 Standard。
- 不支援單則訊息的 delay（只有 queue 層級）。

| 比較 | Standard queue | FIFO queue |
|---|---|---|
| 投遞保證 | At-least-once | Exactly-once processing（5 分鐘去重區間內） |
| 順序 | 盡力而為 | Message group 內嚴格有序 |
| 吞吐量 | 幾乎無上限 | 300 TPS／API（batch 3,000 msg/s），high throughput mode 更高 |
| 名稱 | 任意 | 必須以 `.fifo` 結尾 |
| 適合 | 互相獨立的工作：縮圖、寄信、報表 | 同一實體的事件必須有序：訂單狀態、帳戶異動 |

## 32.6 失敗處理：DLQ 與 redrive

回到 visibility timeout 的重投機制，它有一個副作用：如果某則訊息**永遠**處理不了（例如格式錯誤、引用了已刪除的資料），它會無限次地被取走、失敗、重新出現。這種訊息稱為 **poison message（毒訊息）**。它會持續消耗 worker，在 FIFO queue 裡更糟糕，因為它會卡住整個 message group 後面的所有訊息。

### Dead-letter queue

**Dead-letter queue（DLQ，死信佇列）** 是另一個普通的 SQS queue，用來收容處理失敗太多次的訊息。在來源 queue 上設定 **redrive policy**：

- `deadLetterTargetArn`：DLQ 的 ARN。
- `maxReceiveCount`：一則訊息被取走幾次仍未刪除，就移到 DLQ。

```yaml
Resources:
  BookingEmailDlq:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600        # 14 天，比來源 queue 長
  BookingEmailQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 120                 # 大於寄信 worker 的正常處理時間
      ReceiveMessageWaitTimeSeconds: 20      # long polling
      MessageRetentionPeriod: 345600         # 4 天
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt BookingEmailDlq.Arn
        maxReceiveCount: 5
  BookingEmailDlqAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      Namespace: AWS/SQS
      MetricName: ApproximateNumberOfMessagesVisible
      Dimensions:
        - Name: QueueName
          Value: !GetAtt BookingEmailDlq.QueueName
      Statistic: Maximum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
```

讀這段 template 時注意三件事：

1. **`maxReceiveCount` 不要設成 1。** 很多失敗是暫時的（下游短暫逾時），給它幾次重試機會；但也不要設得太大，讓 poison message 長時間占用資源。
2. **DLQ 的 retention 要比來源 queue 長。** 對 Standard queue 而言，訊息移入 DLQ 時保留的是**原始的送入時間**。如果來源與 DLQ 都是 4 天，一則在來源 queue 待了 3 天才進 DLQ 的訊息，只剩 1 天就會過期。
3. **DLQ 一定要有告警與負責人。** 沒有人看的 DLQ 只是把資料遺失延後幾天發生。

### Redrive：修好之後重送

找到根因並修正 consumer 後，可以使用 **DLQ redrive**（console 或 `StartMessageMoveTask` API）把 DLQ 裡的訊息搬回來源 queue（或其他 queue）重新處理，並可以控制搬移速度，避免一次湧入壓垮剛修好的服務。重送的訊息會被再處理一次，所以 consumer 的冪等性在這裡又一次變得重要。

### Lambda 消費 SQS 時的部分失敗

Lambda 透過 **event source mapping**（第 19 章）從 SQS 批次取訊息。預設行為是：一個 batch 裡只要有一則失敗，整個 batch 都視為失敗，全部重新出現在 queue 裡，已經成功的那些也會被重做。開啟 **`ReportBatchItemFailures`** 後，函式可以回傳失敗訊息的 ID 清單，只有這些訊息會被重試。此外，AWS 建議 queue 的 visibility timeout 至少是 Lambda 函式 timeout 的 6 倍，讓 Lambda 在遇到 throttling 時有重試的空間。

## 32.7 大訊息、加密與存取控制

### 訊息大小與 claim check pattern

SQS 單則訊息的上限長期以來是 **256 KB**，這也是 SAA／SAP 題目最常用的數字；AWS 在 2025 年把上限提高到 **1 MiB**（1,048,576 bytes），題目若寫 256 KB，就照題目的數字作答。不論是哪個上限，Wanderly 的行程 PDF、旅館照片都放不進去。標準做法是 **claim check pattern（提單模式）**：把大型資料寫入 S3，訊息裡只放 S3 的 bucket 與 key，consumer 收到後再去 S3 讀取。

AWS 提供 **Amazon SQS Extended Client Library**（Java、Python 等）自動完成這件事：訊息超過門檻時自動上傳 S3、送出指標；consumer 端自動下載；刪除訊息時可一併刪除 S3 物件。它支援的 payload 遠大於 SQS 本身的上限（官方文件列出最大 2 GB）。SNS 也有相同概念的 extended client。

> [!warning] 常見誤解
> 「訊息太大就壓縮或拆成多則。」壓縮只是延後問題，拆訊息則要自己處理重組、遺失與順序。考題出現「訊息超過 256 KB」（或超過 SQS 上限）時，答案幾乎都是「放 S3、訊息只帶指標（Extended Client Library）」。

### 加密

- **傳輸中**：SQS API 端點使用 HTTPS（TLS）。可以用 queue policy 的 `aws:SecureTransport` 條件拒絕非 TLS 的請求。
- **靜態加密**：新建 queue 預設啟用 **SSE-SQS**（SQS 管理的金鑰）。若需要自己控制金鑰權限、輪替與 CloudTrail 稽核，可以改用 **SSE-KMS**（第 15 章）。

使用 SSE-KMS 有一個考試和實務都常踩的坑：當 **SNS、EventBridge 或 S3 event notification 要把訊息送進加密的 queue** 時，這些服務需要使用該 KMS key 的權限（`kms:GenerateDataKey` 與 `kms:Decrypt`）。AWS managed key（`aws/sqs`）的 key policy 不能修改，無法授權給這些服務，所以必須改用 **customer managed key**，並在 key policy 中允許對應的服務 principal。症狀通常是「SNS 顯示發布成功，queue 卻一直收不到訊息」。

### Queue policy：誰可以送、誰可以收

SQS 的 **queue policy** 是 resource-based policy（第 12 章），決定其他帳號或 AWS 服務能不能對這個 queue 操作。同帳號內的應用程式通常用 IAM role 授權就夠；跨帳號，或讓 SNS、S3、EventBridge 這類服務寫入時，就需要 queue policy。32.9 節會看到一個完整的例子。

## 32.8 依 queue 深度擴展 consumer

Queue 把尖峰流量存起來了，但如果 consumer 數量固定，促銷時 backlog 會越堆越高，訊息延遲越來越長。我們希望 consumer 的數量跟著 backlog 自動調整。

### 該看哪個 metric

SQS 會免費把以下 metric 送到 CloudWatch：

| Metric | 意義 | 用途 |
|---|---|---|
| `ApproximateNumberOfMessagesVisible` | 等待被取走的訊息數 | 衡量 backlog |
| `ApproximateNumberOfMessagesNotVisible` | In flight 的訊息數 | 正在處理中的量 |
| `ApproximateAgeOfOldestMessage` | 最老訊息已等待多久 | 衡量延遲、告警 SLA |
| `NumberOfMessagesSent／Received／Deleted` | 流量 | 觀察趨勢 |

### EC2 Auto Scaling：backlog per instance

直接用「訊息數」當 scaling 指標有個問題：1,000 則訊息對 2 台 worker 是很大的壓力，對 50 台卻幾乎沒事。AWS 建議的做法是計算 **backlog per instance（每台 instance 的待處理量）**：

```text
backlog per instance = ApproximateNumberOfMessagesVisible ÷ 正在執行的 instance 數

可接受的 backlog per instance = 可接受的最長延遲 ÷ 每則訊息的平均處理時間
例：每則訊息處理 0.5 秒，可接受延遲 60 秒 → 每台最多 120 則
```

做法是用一個排程（例如 Lambda 每分鐘一次）計算這個值並發布成 custom metric，再對 ASG 設定 **target tracking scaling policy**（第 18 章），目標值為 120。Backlog 變大時 ASG 自動加機器，消化完後縮回去。

### Lambda：event source mapping 自動擴展

如果 consumer 是 Lambda，就不需要自己做這件事。Lambda 的 SQS event source mapping 會依 backlog 自動增加 poller 與並行的函式數量。這時要擔心的反而是「擴展太快」：Lambda 可能一下子開到數百個並行，把下游的 RDS 連線數打爆。可以在 event source mapping 設定 **maximum concurrency** 限制這個 queue 最多觸發幾個並行執行，或用 reserved concurrency 限制整個函式（第 19 章）。這就是第 33 章會談的 backpressure（背壓）。

## 32.9 SNS：一則訊息送給很多人

SQS 解決了「一份工作交給一群 worker 其中之一」。但 Wanderly 的「訂單成立」事件需要讓寄信、點數、分析三個服務**各自**都收到一份。如果讓訂單服務分別送三個 queue，它就又知道了所有下游的存在，每新增一個下游都要改訂單服務。我們需要的是發布訂閱。

### SNS 的基本模型

**Amazon SNS（Simple Notification Service）** 是受管的 pub/sub 服務：

- **Topic（主題）**：一個發布點。Publisher 只對 topic 呼叫 `Publish`。
- **Subscription（訂閱）**：把一個端點接到 topic 上。每則訊息會被**推送（push）**給所有訂閱者。
- 支援的訂閱協定：SQS、Lambda、HTTP/HTTPS、Email、SMS、行動推播（mobile push）、Amazon Data Firehose。

SNS 本身**不保存訊息讓人之後來拉**。它收到訊息就立刻推送；推送失敗時會依 delivery policy 重試（對 SQS、Lambda 這類 AWS 端點會長時間重試很多次；HTTP/HTTPS 端點的重試策略可自訂）。重試仍然失敗的訊息，可以送到這個 **subscription 的 DLQ**（一個 SQS queue）。注意 DLQ 是設在 subscription 上，而不是 topic 上，因為每個訂閱者的失敗情況不同。

### Fan-out：SNS + 多個 SQS

SNS 直接推送給 Lambda 或 HTTP 端點時，若訂閱者暫時處理不了（例如被 throttle），就只能依賴 SNS 的重試。更穩健的標準架構是 **fan-out（扇出）**：每個訂閱者前面放一個自己的 SQS queue。

```text
                      [SNS topic: booking-events]
                     ① Publish 一次
                          │
          ┌───────────────┼────────────────┐
          │ ② 複製推送    │                │
          ▼               ▼                ▼
   [SQS email-q]    [SQS points-q]   [SQS analytics-q]
   filter: 無        filter:          filter: 無
                     eventType=Confirmed
          │               │                │
          ▼ ③ 各自拉取     ▼                ▼
     寄信 worker      點數 Lambda      分析 Firehose 管線
```

① 訂單服務只發布一次。② SNS 把訊息複製到每個 queue；有設定 filter policy 的訂閱只收到符合條件的訊息。③ 每個 queue 獨立緩衝與重試：寄信服務停機一小時，它的訊息在 `email-q` 裡安全地等待，其他服務完全不受影響。新增一個下游，只要新增一個 queue 和一個 subscription，訂單服務一行程式都不用改。

要讓 SNS 能寫入 SQS，queue policy 必須允許 SNS 服務，並用 `aws:SourceArn` 限定只有這個 topic 能送，避免其他帳號的 topic 冒用（confused deputy，第 13 章）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBookingTopicOnly",
      "Effect": "Allow",
      "Principal": { "Service": "sns.amazonaws.com" },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:ap-northeast-1:111122223333:points-q",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:sns:ap-northeast-1:111122223333:booking-events"
        }
      }
    }
  ]
}
```

### Message filtering

**Subscription filter policy（訂閱過濾政策）** 讓每個訂閱者只收到自己在意的訊息，過濾在 SNS 端完成，不需要訂閱者收到後自己丟棄（省下處理成本與 queue 費用）。預設比對的是**訊息屬性（message attributes）**；也可以把 filter policy scope 設成 `MessageBody`，直接比對 JSON 格式的訊息內容。

點數服務只在乎已確認、金額至少 3,000 元、來自台灣或日本站的訂單：

```json
{
  "eventType": ["BookingConfirmed"],
  "site": ["TW", "JP"],
  "amount": [{ "numeric": [">=", 3000] }]
}
```

同一個欄位內的多個值是 OR，不同欄位之間是 AND。比起為每種事件建立一個 topic，用一個 topic 加 filter policy 讓架構更簡單，publisher 也不需要知道誰要哪種事件。

另一個實用設定是 **raw message delivery**：預設情況下 SNS 送到 SQS 的訊息會包一層 SNS 的 JSON 信封（含 `Type`、`MessageId`、`Message` 等欄位）；開啟 raw message delivery 後，queue 收到的就是原始訊息內容，consumer 不用再解析一層。

### SNS FIFO topic

如果需要「fan-out 而且每個訂閱者都要保持順序」，可以使用 **SNS FIFO topic**（名稱同樣以 `.fifo` 結尾）。它和 SQS FIFO 一樣有 message group ID 與去重，主要的訂閱者是 SQS FIFO queue。SNS FIFO topic 還支援 **message archiving and replay**：topic 擁有者可以設定保存期間，訂閱者之後可以要求重播某段時間的訊息，例如新加入的訂閱者要補齊歷史資料。FIFO topic 的吞吐量低於 Standard topic，只在真的需要順序時使用。

## 32.10 EventBridge：事件路由中心

SNS 的 filter policy 已經能做基本的過濾。但隨著 Wanderly 的服務越來越多，新的需求出現了：

- 想收到 AWS 服務本身的事件（例如 EC2 instance 狀態改變、GuardDuty 發現威脅）。
- 想接收 SaaS 夥伴（例如客服系統、金流商）的事件，而不必自己架 webhook。
- 事件格式由很多團隊共用，需要有地方記錄「這個事件長什麼樣子」。
- 下游 consumer 有 bug，修好之後想把過去三天的事件重放一次。
- 多個 AWS 帳號的事件要匯集到中央帳號。

這些都是 **Amazon EventBridge** 的強項。它是一個 serverless 的 **event bus（事件匯流排）**：事件送上 bus，由 **rules（規則）** 依事件內容比對，符合的事件被送給 **targets（目標）**。

### 事件長什麼樣子

EventBridge 的事件是有固定外框的 JSON：

```json
{
  "version": "0",
  "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
  "detail-type": "BookingConfirmed",
  "source": "com.wanderly.booking",
  "account": "111122223333",
  "time": "2026-10-01T08:15:30Z",
  "region": "ap-northeast-1",
  "resources": [],
  "detail": {
    "bookingId": "B-1001",
    "hotelId": "H-88",
    "amount": 12800,
    "currency": "TWD",
    "site": "TW"
  }
}
```

`source` 與 `detail-type` 說明「誰發生了什麼事」，`detail` 是業務內容。應用程式用 `PutEvents` API 送出自訂事件，AWS 服務則會自動把事件送到 default bus。

### 三種 event bus

| Event bus | 誰送事件進來 | 用途 |
|---|---|---|
| **Default event bus** | AWS 服務自動送入（每個帳號每個 Region 都有） | 回應 AWS 資源變化，例如自動修復（第 38 章） |
| **Custom event bus** | 你的應用程式 `PutEvents` | 業務事件，例如 `BookingConfirmed` |
| **Partner event bus** | 已整合的 SaaS 夥伴 | 接收第三方服務的事件，不需自建 webhook |

### Rules、event pattern 與 targets

Rule 用 **event pattern（事件樣式）** 比對事件。下面的 rule 只挑出「台灣站、金額超過 10,000 元的已確認訂單」，送給高價值訂單的客服流程：

```json
{
  "source": ["com.wanderly.booking"],
  "detail-type": ["BookingConfirmed"],
  "detail": {
    "site": ["TW"],
    "amount": [{ "numeric": [">", 10000] }]
  }
}
```

Event pattern 支援精確比對、prefix、suffix、`anything-but`、數值範圍、`exists`、wildcard 與 `$or`，比 SNS filter policy 的表達能力更強。每個 rule 最多可以有 5 個 targets，target 種類很多：Lambda、SQS、SNS、Step Functions、Kinesis、ECS task、API Gateway、另一個 event bus、**API destination**（任意 HTTP 端點，EventBridge 幫你處理認證與速率限制）等。

送給 target 前可以用 **input transformer** 改寫事件格式，例如只取出 `bookingId` 和 `amount` 組成下游 API 要的 JSON，免去寫一個 Lambda 專門轉格式。

### 投遞失敗：retry policy 與 DLQ

EventBridge 送 target 失敗時（target 不存在、被 throttle、權限錯誤），會依 **retry policy** 重試，預設最長重試 24 小時、最多 185 次，可以調低。重試用盡後，事件可以送到該 target 設定的 **DLQ**（SQS queue），否則就會被丟棄。和 SNS 一樣，DLQ 是 per target 設定的。

> [!tip] 考試提示
> 「EventBridge rule 有被觸發（`MatchedEvents` 有數字），但 target 沒收到」→ 先查 `FailedInvocations` metric 與 target 權限（Lambda resource policy、SQS queue policy、KMS key policy），再確認 target 有沒有設定 DLQ。

### Archive 與 replay

**Archive（封存）** 可以把 event bus 上的事件（全部或符合某個 pattern 的）保存下來，保存期間可自訂或無限期。**Replay（重播）** 則把封存中某段時間的事件重新送回 event bus，再次經過 rules 投遞；啟動 replay 時可以限定只送往特定幾條 rules，避免所有消費者都重做一次。注意 archive 只保存「建立之後」流經 bus 的事件，所以要在事故發生前就建立。

Wanderly 的點數服務曾因 bug 錯誤處理了三天的訂單事件。修好之後，團隊用 replay 把這三天的 `BookingConfirmed` 重播一次，點數服務重新計算。前提依然是：點數服務必須冪等，否則已正確處理的那部分會被重複加點。

### Schema registry

**Schema registry（結構描述登錄）** 儲存事件的結構定義。AWS 服務事件的 schema 已內建；開啟自訂 bus 的 **schema discovery** 後，EventBridge 會自動從實際流過的事件推斷 schema 並登錄。開發者可以下載對應語言的 code binding（程式碼型別），讓 consumer 用強型別的方式讀取事件，減少「欄位名稱打錯」這類錯誤。

### 跨帳號與跨 Region

一個 rule 的 target 可以是**另一個帳號或另一個 Region 的 event bus**。接收方的 event bus 要有 resource-based policy 允許來源帳號 `events:PutEvents`；在 Organizations 環境下，可以用 `aws:PrincipalOrgID` 條件一次允許整個組織。這是 SAP 常考的「集中事件匯流」架構（見 32.14 節）。

跨帳號轉送有兩個要記住的細節。第一，事件只能「跳一次」帳號：接收帳號的 rule 若想把**從別的帳號收到的事件**再送到第三個帳號的 event bus，EventBridge 不會投遞。第二，自 2025 年起，rule 也可以**直接**把事件送到另一個帳號中支援 resource-based policy 的 target（例如 SQS queue、SNS topic、Lambda function、Kinesis stream、API Gateway），對方只要在該資源的 policy 中授權即可，不必再建一個中繼的 event bus。

### EventBridge Pipes：點對點的整合管線

很多整合長這樣：「從 SQS（或 DynamoDB Streams、Kinesis）讀資料 → 過濾掉不要的 → 補充一些資訊 → 送到某個目標」，以前要寫一個 Lambda 做這些雜事。**EventBridge Pipes** 把這個模式產品化：

```text
Source ──► Filter ──► Enrichment（選用）──► Target
DynamoDB   只保留     呼叫 Lambda／          Step Functions、
Streams、  INSERT     Step Functions Express／ EventBridge bus、
SQS、      事件       API destination 補資料   SQS、Kinesis…
Kinesis、
MSK、MQ
```

Pipes 是**一個 source 對一個 target** 的點對點管線，負責輪詢 source、批次、過濾與重試；而 event bus 是多對多的路由。兩者常搭配使用：用 Pipe 把 DynamoDB Streams 的變更轉成事件送上 bus，再由 bus 的 rules 分送給多個消費者（第 33 章的 transactional outbox 就會用到這個組合）。

### EventBridge Scheduler

**EventBridge Scheduler** 是受管的排程服務，支援三種排程：

- **One-time**：在指定時間執行一次，例如「入住前 3 天 09:00 寄提醒」。
- **Rate**：固定間隔，例如每 5 分鐘。
- **Cron**：cron 表示式，並可指定**時區**（會自動處理日光節約時間）。

每個排程可以直接呼叫大量 AWS 服務 API 當 target，有自己的 retry policy 與 DLQ，也有 **flexible time window**，允許在一個時間窗內分散觸發，避免所有排程同時打在下游上。Scheduler 可以建立大量排程（預設 quota 很高，可申請提高），很適合「每筆訂房各一個提醒」這種一筆資料一個排程的需求。EventBridge 舊有的 scheduled rules 仍可使用，但新設計應優先選 Scheduler。

> [!example] 例子
> Wanderly 有 200 萬筆未來訂房，每筆都要在入住前 3 天寄提醒。用 cron 每分鐘掃資料庫找「該寄的訂單」也可行，但會產生大量查詢且邏輯複雜。改用 Scheduler，在訂房成立時建立一個 one-time 排程（取消訂房時刪除它），時間到了直接把訊息送進寄信 queue，不需要任何輪詢程式。

## 32.11 Amazon MQ：搬來既有的 message broker

Wanderly 併購的旅行社（Part 8 會正式登場）有一套 Java 訂位系統，透過 **JMS（Java Message Service）** API 和 Apache ActiveMQ broker 溝通，程式裡到處是 JMS 的 queue 與 topic。如果要改成 SQS，得改寫所有訊息相關的程式碼。

**Amazon MQ** 是受管的 message broker 服務，提供 **Apache ActiveMQ** 與 **RabbitMQ** 兩種引擎。它的價值不是比 SQS 更強，而是**相容業界標準協定**：JMS、AMQP、MQTT、STOMP、OpenWire、WebSocket。既有應用程式只要把連線位址改到 Amazon MQ 的 broker，幾乎不用改程式碼，AWS 負責 broker 的佈建、patch 與備份。

### 部署模式與高可用

- **ActiveMQ**：single-instance（單一 broker，適合開發測試），或 **active/standby**（兩個 broker 位於不同 AZ，共用持久儲存；主 broker 故障時 standby 接手，用戶端用 failover 連線字串自動重連）。
- **RabbitMQ**：single-instance，或 **cluster deployment**（三個節點分散在多個 AZ）。

Amazon MQ 的 broker 跑在你的 VPC 裡（也可以設定公開存取），你需要選擇 broker 的 instance 大小，容量**不會像 SQS 那樣無限自動擴展**，按 broker 執行時數與儲存量計費。

### 何時選 Amazon MQ

| 情境 | 選擇 |
|---|---|
| 既有應用使用 JMS、AMQP、MQTT 等標準協定，要搬到 AWS 且不想改程式 | Amazon MQ |
| 新開發的雲端應用，需要佇列或 pub/sub | SQS、SNS、EventBridge |
| 需要 RabbitMQ 特有的路由功能（exchange、routing key），團隊已熟悉 | Amazon MQ for RabbitMQ |
| 需要無上限的擴展、不想管 broker 大小 | SQS／SNS |

考試的判斷訊號非常固定：題目提到「JMS」「AMQP」「MQTT」「既有 ActiveMQ／RabbitMQ」「不修改程式碼遷移」，答案就是 Amazon MQ；題目說「新應用」「serverless」「最少營運負擔」「高擴展」，答案就是 SQS／SNS。長期現代化路線則常是先 rehost 到 Amazon MQ，之後再逐步改寫成 SQS／SNS（第 44、46 章）。

## 32.12 比較與選型

### 五個服務並排

| 比較 | SQS | SNS | EventBridge | Kinesis Data Streams | Amazon MQ |
|---|---|---|---|---|---|
| 模型 | Queue（pull） | Pub/sub（push） | Event bus + rules（push） | Stream（pull，可重讀） | Broker（queue + topic） |
| 一則訊息給 | 一個 consumer | 所有訂閱者 | 所有符合 rule 的 target | 每個 consumer 各讀一次 | 依 queue／topic 而定 |
| 訊息保存 | 最多 14 天，處理後刪除 | 不保存（FIFO topic 可封存） | 不保存，可另設 archive | 24 小時起，最長 365 天 | 依 broker 儲存 |
| 順序 | FIFO queue 的 group 內 | FIFO topic 的 group 內 | 不保證 | Shard 內有序 | 依引擎 |
| 過濾 | 無（consumer 自己判斷） | Filter policy | Event pattern（最豐富） | 無（Lambda ESM 可過濾） | 依引擎 |
| 擴展 | 自動、幾乎無上限 | 自動 | 自動（有 PutEvents quota） | Shard 數或 on-demand | 選 broker 大小 |
| 典型用途 | 工作佇列、削峰 | 簡單 fan-out、SMS／email／推播 | 跨服務／跨帳號事件路由、SaaS、AWS 事件 | 點擊流、即時分析、需要重播 | 遷移既有 JMS／AMQP 應用 |

### 選型流程

```text
我要傳遞的是什麼？
├─ 一份「工作」，由一群 worker 中的一個處理 → SQS
│     └─ 同一實體的工作必須有序？→ SQS FIFO（group ID = 實體 ID）
├─ 一個「事件」，要讓多個不同的系統各自知道
│     ├─ 只需要簡單 fan-out、或要送 SMS／email／推播 → SNS（+ 每個訂閱者一個 SQS）
│     └─ 需要內容路由、AWS／SaaS 事件、archive/replay、跨帳號 → EventBridge
├─ 大量連續資料，多個消費者要各自讀、可回頭重讀 → Kinesis（第 31 章）
├─ 既有程式使用 JMS／AMQP／MQTT，不想改 → Amazon MQ
├─ 在未來某個時間點觸發動作 → EventBridge Scheduler
└─ 多步驟、有分支與補償的流程 → Step Functions（第 33 章）
```

SNS 與 EventBridge 的界線最常讓人猶豫。簡單的判斷：SNS 擅長「高吞吐、低延遲地把同一則訊息推給很多訂閱者」，並且能直接送 SMS、email、行動推播；EventBridge 擅長「依內容把各式各樣的事件路由到各式各樣的目標」，並帶有 schema、archive／replay、SaaS 整合、跨帳號匯流等治理功能。

## 32.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 解耦、下游變慢不影響前端、吸收流量尖峰 | SQS queue（前端寫入 queue，worker 非同步處理） |
| 同一工作偶爾被處理兩次、處理時間超過設定 | 加大 visibility timeout 或用 `ChangeMessageVisibility` 延長 |
| 空的 ReceiveMessage 很多、降低 SQS 成本 | Long polling（`ReceiveMessageWaitTimeSeconds` = 20） |
| 訊息必須依序處理、不能重複 | SQS FIFO；group ID 設為需保序的實體 ID |
| FIFO 吞吐量不足 | 增加 message group 數量、batch、high throughput mode |
| 某些訊息一直失敗、卡住 worker | DLQ + `maxReceiveCount`，修正後 redrive |
| 訊息超過 256 KB（題目常用數字；現行上限 1 MiB） | 存 S3、訊息只帶指標（Extended Client Library） |
| 依待處理量擴展 EC2 worker | Backlog per instance custom metric + target tracking |
| 一個事件要讓多個系統都處理，且彼此獨立 | SNS fan-out 到多個 SQS queue |
| 訂閱者只要部分訊息 | SNS subscription filter policy／EventBridge event pattern |
| SaaS 夥伴事件、AWS 服務事件、跨帳號事件匯流 | EventBridge（partner bus、default bus、cross-account bus） |
| 修正 bug 後重新處理過去的事件 | EventBridge archive + replay（或 SNS FIFO archive） |
| 每筆資料在未來特定時間觸發、要時區 | EventBridge Scheduler（one-time schedule） |
| 從 DynamoDB Streams／SQS 過濾後送到目標，不想寫膠水 Lambda | EventBridge Pipes |
| 既有應用使用 JMS／AMQP／MQTT、不改程式碼遷移 | Amazon MQ（ActiveMQ／RabbitMQ） |
| SNS／EventBridge 送不進加密的 SQS | 改用 customer managed KMS key 並授權服務 principal |

**常見陷阱**：

1. 用 SNS 當工作佇列：SNS 不保存訊息讓 worker 稍後拉取，訂閱者不在線時只能靠重試，正解是 SNS → SQS。
2. 以為 FIFO queue 就不需要冪等：去重只涵蓋 5 分鐘內 producer 的重送，consumer 端的重投仍會發生。
3. 把所有 FIFO 訊息放在同一個 message group：順序保住了，平行度歸零。
4. 用 delay queue 或 retention 解決重複處理：重複處理是 visibility timeout 的問題，兩者無關。
5. 以為可以把 Standard queue 改成 FIFO：必須新建 queue。
6. 選項寫「Kinesis」但題目只需要工作佇列、不需要重播或多個獨立消費者：SQS 更簡單便宜。
7. 選項寫「Amazon MQ」但題目是全新開發、要求最少營運：Amazon MQ 要選 broker 大小、規劃高可用，SQS／SNS 才是最低營運負擔。

## 32.14 SAP 加深：多帳號事件架構與遷移

### 集中式 event bus

Wanderly 進入多帳號階段（第 14、40 章）後，每個團隊都有自己的帳號：訂單帳號、會員帳號、資料平台帳號、安全帳號。常見的事件架構有兩種：

```text
模式一：中央 event bus（hub-and-spoke）
[訂單帳號 bus] ─rule─►┐
[會員帳號 bus] ─rule─►├─► [中央帳號 custom bus] ─rules─► 中央帳號內的 target，或直接送到消費者帳號的 SQS／Lambda 等 target
[支付帳號 bus] ─rule─►┘     resource policy: aws:PrincipalOrgID = o-xxxx

模式二：直接點對點
[訂單帳號 bus] ─rule─► [資料平台帳號 bus]
[訂單帳號 bus] ─rule─► [會員帳號 bus]
```

模式一把路由規則集中管理、易於稽核與監控，新增消費者只改中央帳號的 rules；缺點是中央團隊成為瓶頸與單一治理點。注意中央 bus 收到的是「從別的帳號轉來」的事件，不能再轉送到第三個帳號的 event bus，所以中央 rules 的 target 要是中央帳號內的資源，或消費者帳號中可直接接收的 SQS、Lambda 等 target。模式二讓團隊自治，但帳號一多，互相之間的 rules 與權限就變得難以追蹤。實務上常見的折衷是：業務事件匯流到中央 bus 並由各團隊以 IaC 自助提交 rule；安全事件（GuardDuty、Security Hub、Config）則依第 40 章的方式匯流到安全帳號。

跨帳號投遞的權限有兩層：**來源端的 rule 需要一個 IAM role** 允許對目標 bus `events:PutEvents`（2023 年 3 月之後新建的跨帳號 event bus target 一律要求這個 role）；**目標 bus 的 resource-based policy** 要允許來源帳號或整個組織。若事件最後送進加密的 SQS 或 SNS，還要第三層：KMS key policy。

### 事件契約治理

事件一旦被多個團隊消費，它的格式就成了「公開 API」。SAP 題目會考事件演進的做法：

- 只做**向後相容的變更**（新增欄位，不改名、不刪欄位、不改型別）。
- 需要破壞性變更時，發布新版本的 `detail-type`（例如 `BookingConfirmed.v2`），新舊版本並行一段時間，等所有消費者遷移後再停發舊版。
- 用 schema registry 記錄與發現 schema，消費者使用 code binding。
- 事件中帶有唯一 ID 與發生時間，讓消費者能去重、判斷新舊。

### 可靠性與多 Region

- EventBridge **global endpoints** 讓 producer 對一個 endpoint 發布事件，在主要 Region 的 event bus 不健康時（依 Route 53 health check）自動切到次要 Region，並可搭配跨 Region 事件複寫，降低 Regional 故障對事件發布的影響（多 Region 架構見第 42 章）。
- SQS 本身是 Regional 服務，沒有內建跨 Region 複寫。若需要 Region 故障時仍能接收訊息，要在兩個 Region 各有 queue，由 producer 或上游（例如 SNS 跨 Region 訂閱、EventBridge 跨 Region rule）負責送達。

### 從自管 broker 遷移

併購的旅行社除了 ActiveMQ，還有一套自管 RabbitMQ 叢集。SAP 題目常用「遷移時程緊」與「長期降低營運負擔」兩個限制同時出現：

1. **第一階段（rehost）**：搬到 Amazon MQ，連線字串改掉即可上線，消除自管 broker 的 patch 與硬體負擔。
2. **第二階段（refactor）**：新功能直接使用 SQS／SNS／EventBridge；既有的 queue 按業務重要性逐一改寫，可暫時以橋接程式在 Amazon MQ 與 SQS 之間轉送訊息。
3. 若應用程式重度依賴 JMS 交易語意或特定 broker 功能，改寫成本可能不划算，可以長期留在 Amazon MQ。

## 本章重點整理

- 同步呼叫同時造成時間耦合與容量耦合；把「晚一點完成也可以」的工作改成透過 queue 或事件非同步處理，可以隔離故障並削平流量尖峰。
- SQS 的訊息被取走後只是暫時隱藏，consumer 必須在 visibility timeout 內處理完並呼叫 `DeleteMessage`，否則訊息會重新出現。
- Standard queue 是 at-least-once、盡力排序、吞吐幾乎無上限，因此 consumer 必須冪等。
- Visibility timeout 防止重複處理（預設 30 秒、最長 12 小時），long polling 減少空回應（最長 20 秒），delay queue 延後訊息可見（最長 15 分鐘），retention 決定訊息保存期間（1 分鐘–14 天，預設 4 天）。
- FIFO queue 在 message group 內嚴格有序，並在 5 分鐘去重區間內去除重複送入；group ID 應選需要保序的業務實體，才能兼顧平行度。
- FIFO 預設每個 API 動作 300 TPS（batch 3,000 msg/s），可開 high throughput mode；Standard 不能直接轉成 FIFO。
- DLQ 以 `maxReceiveCount` 隔離 poison message；DLQ retention 要比來源 queue 長、必須有告警，修正後用 redrive 重送。
- 訊息超過上限（考試常用 256 KB，2025 年起為 1 MiB）時用 claim check pattern：資料放 S3，訊息只帶指標（Extended Client Library）。
- SNS、EventBridge、S3 要寫入 SSE-KMS 加密的 queue 時，必須使用 customer managed key 並在 key policy 授權該服務。
- EC2 worker 依 backlog per instance 做 target tracking；Lambda consumer 用 event source mapping 的 maximum concurrency 保護下游。
- SNS 是推送式 pub/sub，不保存訊息；可靠的 fan-out 是 SNS → 每個訂閱者一個 SQS queue，搭配 filter policy 與 subscription DLQ。
- EventBridge 以 event pattern 把事件路由到最多 5 個 targets，提供 default／custom／partner bus、archive／replay、schema registry、跨帳號與跨 Region 投遞。
- EventBridge Pipes 是 source → filter → enrichment → target 的點對點管線；EventBridge Scheduler 處理 one-time、rate 與 cron（含時區）排程。
- Amazon MQ 提供受管 ActiveMQ 與 RabbitMQ，用於不改程式遷移使用 JMS、AMQP、MQTT 的既有應用；新應用優先選 SQS／SNS／EventBridge。

## 本章練習題

### 練習 32-1｜SAA｜單選｜長工作與重複處理

Wanderly 的發票產生 worker 從 SQS Standard queue 取訊息，大多數發票 20 秒內完成，但含有多間旅館的團體訂單需要 8 分鐘。queue 的 visibility timeout 目前為 60 秒。監控顯示團體訂單的發票常被產生兩次，客戶收到重複發票。

哪個做法最能解決問題，同時讓一般訊息在 worker 當機時仍能快速重試？

- A. 把 message retention period 從 4 天調為 14 天
- B. 為 queue 設定 10 分鐘的 delay，讓團體訂單晚一點才被取走
- C. 改用 SQS FIFO queue，讓去重機制阻止重複處理
- D. 維持較短的 visibility timeout，worker 處理長工作時定期呼叫 `ChangeMessageVisibility` 延長時限，完成後才刪除訊息

> [!answer]- 答案：D
> **A ✗** Retention 決定訊息最多保存多久，與「處理中訊息何時重新可見」無關，無法阻止第二個 worker 取走同一則訊息。
>
> **B ✗** Delay 只影響訊息第一次可見的時間，訊息被取走後仍依 visibility timeout 倒數，8 分鐘的處理時間照樣會超過 60 秒。
>
> **C ✗** FIFO 的去重只防止 5 分鐘內 producer 重送相同訊息；consumer 處理超過 visibility timeout 時，訊息一樣會被重新投遞。而且改 FIFO 必須新建 queue，治標不治本。
>
> **D ✓** 重複處理的根因是處理時間超過 visibility timeout。用 heartbeat 方式延長長工作的時限，既避免重複，又讓一般訊息在 worker 當機時只等短時間就能被重試。整體仍受 12 小時上限限制。
>
> **考點**：SAA-2.2｜visibility timeout 與 `ChangeMessageVisibility`

### 練習 32-2｜SAA｜單選｜降低 SQS API 成本

Wanderly 的退款通知 queue 每天只有幾百則訊息，但 consumer 以迴圈不斷呼叫 `ReceiveMessage`，帳單顯示每月有數千萬次 API 呼叫，其中絕大多數回傳空結果。團隊希望在不改變訊息處理語意的情況下降低成本。

最合適的做法是什麼？

- A. 把 queue 的 `ReceiveMessageWaitTimeSeconds` 設為 20 秒，啟用 long polling
- B. 把 visibility timeout 調高到 12 小時，減少訊息被重新取走的次數
- C. 把 queue 換成 SNS topic，讓訊息直接推送給 consumer
- D. 在 consumer 每次呼叫後固定睡眠 5 分鐘再呼叫

> [!answer]- 答案：A
> **A ✓** Long polling 讓 `ReceiveMessage` 在沒有訊息時最多等待 20 秒，訊息一到立即回傳，能大幅減少空回應與 API 次數，而且不影響投遞與刪除的語意。
>
> **B ✗** Visibility timeout 只影響已被取走的訊息；空回應的問題來自 queue 沒有訊息時的輪詢，與 timeout 無關。設成 12 小時還會讓 worker 當機時的訊息延遲極久。
>
> **C ✗** SNS 是推送式 pub/sub，不保存訊息供 consumer 稍後拉取，consumer 停機時只能依賴重試，改變了可靠性語意，也需要改寫架構。
>
> **D ✗** 固定睡眠確實會減少呼叫，但會讓訊息最多延遲 5 分鐘才被處理，改變了服務的延遲特性；long polling 能在省錢的同時保持即時。
>
> **考點**：SAA-2.1、SAA-4.2｜SQS long polling

### 練習 32-3｜SAA｜單選｜FIFO 的順序與平行度

Wanderly 的庫存同步服務會收到每筆訂房的「建立、修改、取消」事件。同一筆訂房的事件必須依序處理，不同訂房之間沒有順序要求。尖峰時每秒約有 1,500 則事件，團隊希望以多個 worker 平行處理。

應如何設計？

- A. 使用 SQS Standard queue，在 consumer 端依事件時間戳記排序後再處理
- B. 使用 SQS FIFO queue，所有訊息使用同一個 message group ID 以確保全域順序
- C. 使用 SQS FIFO queue，以訂房編號作為 message group ID，producer 使用 batch 送出
- D. 使用 SNS Standard topic，讓每個 worker 訂閱並依序處理

> [!answer]- 答案：C
> **A ✗** Standard queue 只盡力排序，訊息也可能被不同 worker 同時取走；consumer 端排序需要額外的狀態與等待邏輯，仍無法保證同一筆訂房不被平行處理。
>
> **B ✗** 單一 message group 會讓整個 queue 一次只處理一則訊息，平行度歸零，遠低於每秒 1,500 則的需求。
>
> **C ✓** FIFO 的順序是 group 內的順序。以訂房編號當 group ID，同一筆訂房有序、不同訂房可以平行；batch 送出讓吞吐量達到每秒 3,000 則的範圍，足以應付尖峰。
>
> **D ✗** SNS Standard topic 會把每則訊息推給所有訂閱者，不是讓 worker 分工；它也不保證順序。
>
> **考點**：SAA-2.1｜FIFO message group ID

### 練習 32-4｜SAA｜選兩項｜Poison message 處理

Wanderly 的點數 queue 偶爾會收到格式錯誤的訊息，worker 每次處理都失敗，訊息不斷重新出現，消耗大量運算資源。團隊希望隔離這些訊息、在問題被注意到時通知值班人員，並在修正 parser 後重新處理。

哪兩個做法最合適？（選兩項）

- A. 為來源 queue 設定 redrive policy 指向 DLQ，`maxReceiveCount` 設為合理的重試次數，並對 DLQ 的 `ApproximateNumberOfMessagesVisible` 建立 CloudWatch alarm
- B. 把 `maxReceiveCount` 設為 1，讓任何失敗都立刻進入 DLQ
- C. 讓 worker 收到訊息後立刻刪除，失敗時把錯誤寫到日誌
- D. 修正 parser 後，使用 DLQ redrive 以受控的速度把訊息送回來源 queue，並確認 consumer 冪等
- E. 把 DLQ 的 retention 設得比來源 queue 短，以免失敗訊息占用空間

> [!answer]- 答案：A、D
> **A ✓** Redrive policy 讓多次失敗的訊息自動移到 DLQ，不再干擾正常處理；DLQ 告警確保有人知道失敗正在累積。
>
> **B ✗** 設為 1 會讓所有暫時性失敗（例如下游短暫逾時）也立刻進 DLQ，失去自動重試的好處，增加人工處理量。
>
> **C ✗** 處理前就刪除訊息，worker 一旦失敗或當機，訊息就永久遺失，只剩日誌，無法重新處理。
>
> **D ✓** 修正根因後用 redrive 送回，並控制速度避免壓垮服務。重送的訊息可能有一部分已處理過，consumer 冪等才不會重複加點。
>
> **E ✗** Standard queue 的訊息移入 DLQ 時保留原始送入時間，DLQ retention 應比來源 queue 長，否則調查期間訊息可能就過期了。
>
> **考點**：SAA-2.2｜DLQ、`maxReceiveCount` 與 redrive

### 練習 32-5｜SAA｜單選｜超過訊息上限的 payload

Wanderly 的行程產生服務要把每筆團體行程的完整資料交給 PDF 產生 worker，資料是約 3 MB 的 JSON。目前架構使用 SQS 傳遞工作，團隊希望保持 SQS 的解耦與重試特性，並以最少的自訂程式完成。

最合適的做法是什麼？

- A. 把 JSON 用 gzip 壓縮後放進 SQS 訊息
- B. 使用 Amazon SQS Extended Client Library，讓大型 payload 自動存入 S3，訊息只帶 S3 指標
- C. 把 JSON 拆成多則 SQS 訊息，consumer 依序號重組
- D. 改用 SNS topic，因為 SNS 的訊息上限比 SQS 大

> [!answer]- 答案：B
> **A ✗** 壓縮率不固定，3 MB 的資料不保證能壓到上限以內，資料量成長後還是會失敗。
>
> **B ✓** Claim check pattern 把大型資料放 S3、訊息只帶指標。Extended Client Library 自動處理上傳、下載與刪除，producer 與 consumer 只需替換 client，保留 SQS 的所有特性。
>
> **C ✗** 拆訊息要自己處理重組、部分遺失與順序（Standard queue 不保序），程式複雜度與錯誤風險都很高。
>
> **D ✗** SNS 的訊息上限並沒有比 SQS 大，同樣遠小於 3 MB；而且 SNS 是推送式，不提供 worker 拉取與重試的佇列語意。
>
> **考點**：SAA-2.1｜SQS 訊息大小與 claim check pattern

### 練習 32-6｜SAA｜單選｜依 backlog 擴展 EC2 worker

Wanderly 的照片轉檔 worker 跑在 EC2 Auto Scaling group，從 SQS queue 取工作。每則訊息平均處理 2 秒，業務要求照片上傳後 5 分鐘內完成轉檔。促銷期間 queue 深度從數百則暴增到數萬則，目前以 CPU 使用率做 scaling，但 CPU 常維持在 50% 左右，ASG 沒有擴展。

最合適的 scaling 設計是什麼？

- A. 對 queue 的 `NumberOfMessagesSent` 設定 step scaling policy
- B. 以 scheduled scaling 在每次促銷前把 desired capacity 調到最大值
- C. 把 visibility timeout 調短，讓訊息更快被處理
- D. 發布「backlog per instance」custom metric（可見訊息數 ÷ 執行中 instance 數），以 150 為目標值設定 target tracking scaling policy

> [!answer]- 答案：D
> **A ✗** `NumberOfMessagesSent` 只代表送入速率，沒有考慮已累積的 backlog 與目前的 worker 數量，無法反映每台機器實際的待處理壓力。
>
> **B ✗** 排程擴展只能處理已知時間的尖峰，無法應付非預期的流量；一律開到最大值也浪費成本。
>
> **C ✗** Visibility timeout 縮短不會讓 worker 處理得更快，反而可能讓處理中的訊息被重複取走。
>
> **D ✓** 可接受延遲 300 秒 ÷ 每則 2 秒 = 每台最多 150 則。以 backlog per instance 做 target tracking，能同時考慮 queue 深度與目前機器數，讓 ASG 依實際待處理量擴縮。
>
> **考點**：SAA-3.2、SAA-2.1｜SQS backlog per instance 與 target tracking

### 練習 32-7｜SAA｜單選｜可靠的 fan-out

訂單成立後，Wanderly 有三個服務需要各自處理同一個事件：寄信、加點數、送分析系統。其中寄信服務每月會有一次維護停機約一小時。團隊要求任何一個服務停機都不能讓其他服務或訂單服務受影響，且停機期間的事件不能遺失。

最合適的架構是什麼？

- A. 訂單服務發布到一個 SNS topic，三個服務各自用一個 SQS queue 訂閱該 topic，並從自己的 queue 拉取
- B. 訂單服務把事件送到一個 SQS queue，三個服務的 worker 都從同一個 queue 拉取
- C. 訂單服務發布到 SNS topic，三個服務以 HTTPS endpoint 直接訂閱
- D. 訂單服務依序同步呼叫三個服務的 API，失敗時寫入日誌由人工補送

> [!answer]- 答案：A
> **A ✓** SNS 把每則事件複製給所有訂閱者，每個 SQS queue 為各自的服務獨立保存與緩衝。寄信服務停機時事件留在它的 queue 裡，恢復後繼續處理，其他服務不受影響。
>
> **B ✗** 單一 queue 中每則訊息只會被一個 consumer 取走並刪除，三個服務會「搶」訊息，而不是各自收到一份。
>
> **C ✗** HTTPS 訂閱只能依賴 SNS 的重試，停機時間若超過重試範圍事件就會遺失（除非另設 DLQ 再人工處理），也無法讓服務依自己的速度拉取。
>
> **D ✗** 同步呼叫正是本章要解決的時間耦合與容量耦合，一個服務停機就會影響訂單流程。
>
> **考點**：SAA-2.1、SAA-2.2｜SNS 與 SQS fan-out

### 練習 32-8｜SAA｜單選｜只收到需要的訊息

Wanderly 的 `booking-events` SNS topic 上有多種事件：建立、確認、取消、退款。新的會員點數服務只需要「已確認、且來自台灣站」的事件。目前點數服務的 SQS queue 收到所有事件，再由 Lambda 丟棄不需要的部分，處理成本很高。團隊希望不修改發布端與其他訂閱者。

最合適的做法是什麼？

- A. 為每一種事件類型建立獨立的 SNS topic，讓發布端依類型發布
- B. 在點數服務的 SQS subscription 設定 filter policy，比對 `eventType` 與 `site` 屬性
- C. 在點數服務的 Lambda 增加 reserved concurrency 以加快丟棄速度
- D. 把點數服務的 queue 改成 FIFO queue，只接收特定 message group

> [!answer]- 答案：B
> **A ✗** 拆 topic 需要修改發布端的程式，也讓其他訂閱者必須改為訂閱多個 topic，違反「不修改發布端與其他訂閱者」的要求。
>
> **B ✓** Subscription filter policy 在 SNS 端過濾，只有符合條件的訊息會送進點數服務的 queue，降低 queue 與 Lambda 的成本，且只影響這一個 subscription。
>
> **C ✗** 增加並行度只是更快地處理不需要的訊息，成本不會下降。
>
> **D ✗** Consumer 無法選擇「只接收某個 message group」；group ID 是用來保序的，不是過濾機制。
>
> **考點**：SAA-2.1、SAA-4.2｜SNS subscription filter policy

### 練習 32-9｜SAA｜單選｜接收 SaaS 夥伴事件

Wanderly 使用一家已與 Amazon EventBridge 整合的 SaaS 客服平台。每當客戶開立「退款申請」工單，Wanderly 希望自動啟動退款審核流程（一個 Step Functions state machine）。團隊不想自己維護對外公開的 webhook endpoint。

最合適的做法是什麼？

- A. 建立 API Gateway 與 Lambda 作為 webhook，接收 SaaS 平台的 HTTP 回呼後啟動 state machine
- B. 用 EventBridge Scheduler 每分鐘呼叫 SaaS API 查詢新的退款工單
- C. 接受 SaaS 夥伴的 partner event source，關聯到 partner event bus，建立 rule 比對退款申請事件，target 設為 Step Functions state machine
- D. 讓 SaaS 平台把事件寫入 Wanderly 的 SNS topic，再由 SNS 直接啟動 state machine

> [!answer]- 答案：C
> **A ✗** 可行，但要自己維護公開端點、驗證來源與處理重試，正是題目不想要的營運負擔。
>
> **B ✗** 輪詢會延遲事件、浪費 API 呼叫，也需要自己追蹤哪些工單已處理過。
>
> **C ✓** 已整合的 SaaS 夥伴可以直接把事件送到 partner event bus，Wanderly 只需建立 rule 並把 state machine 設為 target，不必暴露任何公開端點。
>
> **D ✗** SaaS 平台不會直接寫入客戶的 SNS topic（需要跨帳號授權與客製整合），而且 SNS 不能把 Step Functions 當作訂閱目標。
>
> **考點**：SAA-2.1｜EventBridge partner event bus

### 練習 32-10｜SAA｜單選｜每筆訂房一個提醒

Wanderly 需要在每筆訂房入住日前 3 天、旅館當地時間上午 9 點寄出提醒信。系統中有約 200 萬筆未來訂房，旅館分布在多個時區。訂房取消時提醒也必須取消。團隊希望營運負擔最低。

最合適的做法是什麼？

- A. 訂房成立時以 EventBridge Scheduler 建立一個指定時區的 one-time schedule，target 為寄信 queue；訂房取消時刪除該 schedule
- B. 把提醒訊息送進 SQS，設定 delay 為入住前 3 天
- C. 建立一個 cron 每分鐘執行的 EventBridge rule，觸發 Lambda 掃描整張訂房資料表
- D. 在 EC2 上執行 cron daemon，每個時區設定一個排程掃描資料庫

> [!answer]- 答案：A
> **A ✓** EventBridge Scheduler 支援大量 one-time schedule 並能指定時區，時間到了直接把訊息送到 target，不需要輪詢；取消訂房時刪除對應排程即可。
>
> **B ✗** SQS 的 delay 最長只有 15 分鐘，無法延遲數天或數月。
>
> **C ✗** 每分鐘掃描整張表可行但浪費，還要自己處理時區轉換與避免重複寄送，營運負擔較高。
>
> **D ✗** 自管 EC2 cron 有單點故障與維護負擔，是營運負擔最高的選項。
>
> **考點**：SAA-2.1｜EventBridge Scheduler one-time schedule

### 練習 32-11｜SAA｜選兩項｜遷移 JMS 應用

Wanderly 併購的旅行社有一套 Java 訂位系統，使用 JMS API 與自管的 Apache ActiveMQ broker 溝通。公司要在兩個月內把系統搬到 AWS，不能修改訊息相關的程式碼，並且 broker 必須能承受單一 AZ 故障。

哪兩個做法最合適？（選兩項）

- A. 把 broker 換成 SQS FIFO queue，並用 SQS 的 JMS 相容層改寫程式
- B. 建立 Amazon MQ for ActiveMQ broker
- C. 使用 active/standby 部署模式，讓兩個 broker 位於不同 AZ，用戶端使用 failover 連線字串
- D. 在單一 EC2 instance 上自行安裝 ActiveMQ，並設定每日 AMI 備份
- E. 改用 SNS FIFO topic 取代 ActiveMQ 的 topic

> [!answer]- 答案：B、C
> **A ✗** 改用 SQS 需要修改連線與訊息處理的程式碼，違反「不能修改」的限制，兩個月內也有遷移風險。
>
> **B ✓** Amazon MQ for ActiveMQ 相容 JMS、OpenWire 等協定，應用程式只需改連線位址，broker 的佈建與 patch 由 AWS 負責。
>
> **C ✓** Active/standby 部署讓兩個 broker 位於不同 AZ，主 broker 故障時 standby 接手，用戶端透過 failover 連線字串自動重連，滿足 AZ 故障的要求。
>
> **D ✗** 單一 EC2 是單點故障，AMI 備份無法提供 AZ 故障時的即時接手，且仍需自行維運 broker。
>
> **E ✗** SNS 不支援 JMS 協定，需要改寫程式碼。
>
> **考點**：SAA-2.2、SAA-2.1｜Amazon MQ 與 active/standby broker

### 練習 32-12｜SAP｜單選｜SNS 寫不進加密 queue

Wanderly 的安全規範要求所有 SQS queue 使用 SSE-KMS 加密。團隊把點數服務的 queue 改為使用 AWS managed key（`aws/sqs`）加密後，SNS topic 的發布仍顯示成功，但點數 queue 再也收不到任何訊息。Queue policy 已允許 `sns.amazonaws.com` 以 `aws:SourceArn` 條件 `sqs:SendMessage`。

應如何修正，同時維持加密要求？

- A. 改回 SSE-SQS 加密，因為 SNS 只支援寫入使用 SQS 管理金鑰的 queue
- B. 在 queue policy 加入允許 `sns.amazonaws.com` 執行 `kms:Decrypt` 的陳述
- C. 開啟 SNS subscription 的 raw message delivery，讓 SNS 不需要加密訊息
- D. 改用 customer managed KMS key 加密 queue，並在 key policy 中允許 `sns.amazonaws.com` 使用 `kms:GenerateDataKey` 與 `kms:Decrypt`

> [!answer]- 答案：D
> **A ✗** SNS 可以寫入 SSE-KMS 加密的 queue；改回 SSE-SQS 雖然能動，但違反「使用 SSE-KMS」的規範。
>
> **B ✗** KMS 權限必須在 KMS key policy（或 grant）中授予，queue policy 無法授權 KMS 動作。
>
> **C ✗** Raw message delivery 只是移除 SNS 的 JSON 信封，與加密金鑰權限無關。
>
> **D ✓** AWS managed key 的 key policy 不能修改，無法授權 SNS 使用。改用 customer managed key 並在 key policy 允許 SNS 服務 principal 產生 data key 與解密，SNS 才能把訊息寫入加密的 queue。EventBridge、S3 event notification 也有相同需求。
>
> **考點**：SAP-2.3、SAP-3.2｜SSE-KMS queue 與服務 principal 的 key policy

### 練習 32-13｜SAP｜單選｜組織層的集中事件匯流

Wanderly 有 40 個 AWS 帳號，屬於同一個 AWS Organization。資料平台團隊希望所有業務帳號的 `com.wanderly.*` 事件都匯流到資料平台帳號的 custom event bus，再由資料平台統一分送。新帳號會持續被建立，團隊不希望每新增一個帳號就修改資料平台帳號的權限設定。

最合適的做法是什麼？

- A. 在每個業務帳號建立 SNS topic，由資料平台帳號的 SQS queue 跨帳號訂閱
- B. 在資料平台帳號的 custom event bus 設定 resource-based policy，以 `aws:PrincipalOrgID` 允許組織內所有帳號 `events:PutEvents`；各業務帳號以 IaC 建立 rule，target 為該中央 bus 並附上具 `events:PutEvents` 權限的 IAM role
- C. 在資料平台帳號為每個業務帳號建立一個 IAM user，業務帳號用該 user 的 access key 直接呼叫 `PutEvents`
- D. 讓所有業務帳號把事件寫入同一個 S3 bucket，資料平台帳號用 S3 event notification 觸發處理

> [!answer]- 答案：B
> **A ✗** SNS 跨帳號訂閱可行，但每新增一個帳號都要建立 topic 與訂閱、修改 queue policy，且失去 EventBridge 的內容路由與集中 rules。
>
> **B ✓** 以 `aws:PrincipalOrgID` 授權整個組織，新帳號加入組織後自動具備權限；業務帳號透過 rule 轉送到中央 bus 是 EventBridge 標準的跨帳號模式，搭配帳號 baseline 的 IaC 可自動部署。
>
> **C ✗** 跨帳號使用長期 access key 違反最佳實務，增加金鑰洩漏風險，且每個帳號都要建立與輪替 user。
>
> **D ✗** S3 不是事件匯流排，會增加延遲並失去事件路由能力，資料平台還要自己解析與分送。
>
> **考點**：SAP-1.4、SAP-2.3｜EventBridge 跨帳號 event bus 與 `aws:PrincipalOrgID`

### 練習 32-14｜SAP｜單選｜修正 bug 後重新處理事件

Wanderly 的 `booking` custom event bus 上有 6 條 rules，分別送往點數、寄信、分析等服務。上線時團隊已為這個 bus 建立保留 30 天的 archive。一次部署讓點數服務過去 3 天的計算錯誤，修正後需要重新處理這 3 天的 `BookingConfirmed` 事件，但寄信服務絕對不能再寄一次信，也不想修改訂單服務。

最合適的做法是什麼？

- A. 請訂單服務團隊從資料庫查詢 3 天內的訂單，重新呼叫 `PutEvents` 發布事件
- B. 從 CloudTrail 找出過去 3 天的 `PutEvents` 紀錄，寫程式重新送到 event bus
- C. 把點數服務 SQS queue 的 retention 調到 14 天，從 queue 重新讀取這 3 天的訊息
- D. 從 archive 啟動 replay，時間範圍設為這 3 天，replay 目的地只選點數服務的 rule；點數服務以事件 ID 冪等處理

> [!answer]- 答案：D
> **A ✗** 需要修改並動用訂單服務，而且重新發布的事件會經過所有 rules，寄信服務會再寄一次信。
>
> **B ✗** CloudTrail 不是設計來重建業務事件內容的，即使能取得資料，重送到 bus 一樣會觸發所有 rules。
>
> **C ✗** SQS 訊息處理成功後就已被刪除，事後調長 retention 不能讓已刪除的訊息重新出現。
>
> **D ✓** Archive 保存了流經 bus 的事件，replay 可以指定時間範圍，並限定只送往特定 rules，因此只有點數服務會重新處理，寄信服務不受影響。重播的事件中可能有部分已被正確處理，點數服務依事件 ID 冪等才不會重複加點。
>
> **考點**：SAP-3.4、SAP-2.4｜EventBridge archive 與 replay 範圍

### 練習 32-15｜SAP｜選兩項｜FIFO 吞吐量瓶頸

Wanderly 的帳務系統使用 SQS FIFO queue 傳遞會員錢包的異動事件，要求同一個會員的異動依序處理。目前 producer 每次送一則訊息、所有訊息的 message group ID 都設為 `wallet`。尖峰時 queue 的 backlog 持續成長，增加 consumer 數量也沒有改善。

哪兩個調整最能提高吞吐量，同時維持需求？（選兩項）

- A. 把 message group ID 改為會員 ID，讓不同會員的異動可以平行處理
- B. 把 queue 轉換成 Standard queue 以取得無上限吞吐
- C. 加大 visibility timeout，讓每個 consumer 處理更多訊息
- D. Producer 改用 `SendMessageBatch` 一次送出最多 10 則訊息，並視需要開啟 high throughput mode
- E. 關閉 content-based deduplication 以減少 SQS 的運算

> [!answer]- 答案：A、D
> **A ✓** 所有訊息同一個 group 時，queue 一次只能處理一則，增加 consumer 也沒有用。改用會員 ID，同一會員仍有序，不同會員可以平行處理。
>
> **B ✗** Standard queue 無法直接由 FIFO 轉換，而且失去順序保證，違反「同一會員依序處理」的需求。
>
> **C ✗** Visibility timeout 只影響訊息重新可見的時間，不會提高 group 內的處理速度，還可能讓失敗恢復變慢。
>
> **D ✓** FIFO 預設每個 API 動作每秒 300 次呼叫，batch 讓每次呼叫帶 10 則訊息；high throughput mode 可再提高上限。兩者都提高送入端的吞吐量。
>
> **E ✗** 去重是 FIFO 提供的保證之一，關閉它不會解決 group 序列化的瓶頸，反而可能引入重複訊息。
>
> **考點**：SAP-3.3、SAP-2.5｜FIFO message group 與吞吐量

### 練習 32-16｜SAP｜單選｜自管 RabbitMQ 的現代化

旅行社的另一套行程整合服務使用自管的 RabbitMQ 叢集，用 fanout exchange 把行程異動廣播給 4 個下游服務，每個下游綁定自己的 queue。這套服務正在被改寫成 serverless 架構，開發團隊可以修改程式碼，公司的目標是消除 broker 的容量規劃與 patch 工作，並讓每個下游能獨立重試。

最合適的目標架構是什麼？

- A. 遷移到 Amazon MQ for RabbitMQ cluster deployment，保留現有的 exchange 設計
- B. 使用一個 SQS queue，讓 4 個下游服務共同消費
- C. 使用 SNS topic，4 個下游服務各自以一個 SQS queue 訂閱，並為每個 queue 設定 DLQ
- D. 使用 Kinesis Data Streams，4 個下游服務各自以 enhanced fan-out 讀取

> [!answer]- 答案：C
> **A ✗** Amazon MQ 消除了自管伺服器，但仍需要選擇 broker 大小、規劃容量；題目明確說可以改程式並要消除容量規劃，這是「不能改程式」時的答案。
>
> **B ✗** 單一 queue 的訊息只會被一個 consumer 取走，4 個下游會搶訊息，無法讓每個下游都收到一份。
>
> **C ✓** SNS → 多個 SQS 正是 RabbitMQ fanout exchange 綁定多個 queue 的 serverless 對應：每個下游有自己的緩衝、重試與 DLQ，不需要容量規劃與 patch。
>
> **D ✗** Kinesis 可以讓多個 consumer 各自讀取，但需要規劃 shard 或使用 on-demand、處理 checkpoint；題目沒有重播或順序分析的需求，SNS + SQS 更簡單、營運負擔更低。
>
> **考點**：SAP-4.4、SAP-4.3｜從 RabbitMQ 遷移到 SNS + SQS fan-out
