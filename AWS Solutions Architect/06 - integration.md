---
title: "Integration 與 Distributed Systems"
part: 5
as_of: 2026-10-01
---

# Part 5　Integration 與 Distributed Systems

# 第 52 章　SQS Standard、FIFO、Visibility 與 DLQ

Producer與consumer速率不同，工作需要buffer、retry與失敗隔離。

## 跟著一件工作在服務間流動：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：影像工作耗時1到10分鐘，偶爾失敗，促銷尖峰producer增加百倍。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：Producer與consumer速率不同，工作需要buffer、retry與失敗隔離。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，Queue像餐廳的出單夾：前台可以先收下工作，廚房按能力處理，失敗的單則移到另一個夾子調查。 出單夾不會創造處理能力，也不保證每張單只被拿一次，所以consumer仍需冪等與backpressure。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon SQS如何接手工作，再看SQS FIFO queues何時更合適，最後用設定與考題驗證「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：影像工作耗時1到10分鐘，偶爾失敗，促銷尖峰producer增加百倍。

Producer很快地送入工作
      │
      ▼
SQS queue保存message並吸收短期burst
      │ ReceiveMessage
      ▼
Consumer開始處理 ── visibility timeout期間暫時隱藏
      │
      ├─ 成功：DeleteMessage
      └─ 失敗／timeout：message再次可見
                     └─ 超過maxReceiveCount ──> DLQ

Queue讓時間解耦，不會讓consumer憑空多出處理能力；duplicate仍需idempotency。

失敗時先找：處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Amazon SQS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon SQS和SQS FIFO queues並不是兩個任意的產品名稱。前者適合本章，是因為「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」直接回應了眼前的問題；後者描述的「Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「queues decouple time but require idempotent consumers」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| SQS FIFO queues | 在message group內提供嚴格順序與deduplication能力。 | MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。 |
| Dead-letter queues | 隔離多次處理失敗的messages，避免poison message無限重試。 | Source queue以maxReceiveCount判斷移入DLQ；redrive可在修復後重送。 |

## 把全圖套進一個具體案例

**場景：** 影像工作耗時1到10分鐘，偶爾失敗，促銷尖峰producer增加百倍。

1. 故事的起點：影像工作耗時1到10分鐘，偶爾失敗，促銷尖峰producer增加百倍。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon SQS負責「以managed queue解耦producer與consumer的時間和容量。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：SQS FIFO queues、Dead-letter queues各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon SQS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Producer與consumer速率不同，工作需要buffer、retry與失敗隔離。
- **具體例子／邊界：** 在「影像工作耗時1到10分鐘，偶爾失敗，促銷尖峰producer增加百倍。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### SQS FIFO queues

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：queues decouple time but require idempotent consumers。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### SQS FIFO queues

- **功用：** 在message group內提供嚴格順序與deduplication能力。
- **底層機制：** MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。
- **關鍵設定：** MessageGroupId、MessageDeduplicationId/content-based dedup、high-throughput mode與visibility。
- **選擇時機：** 同一business entity必須有序，且可用多groups平行處理。
- **替換時機：** 全域單一group會限制throughput；business side effect仍需idempotency。

### Dead-letter queues

- **功用：** 隔離多次處理失敗的messages，避免poison message無限重試。
- **底層機制：** Source queue以maxReceiveCount判斷移入DLQ；redrive可在修復後重送。
- **關鍵設定：** redrive policy、maxReceiveCount、retention、redrive allow policy、alarm與replay procedure。
- **選擇時機：** 需要保存失敗payload供診斷、修復與重播。
- **替換時機：** DLQ不是終點；沒有owner、alarm與runbook只是在延後遺失。

## 考前與實作時再查：設定操作手冊

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### SQS FIFO queues：逐項設定說明

#### `MessageGroupId`

- **控制什麼：** `MessageGroupId`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在SQS FIFO queues依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `MessageDeduplicationId/content-based dedup`

- **控制什麼：** `MessageDeduplicationId/content-based dedup`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在SQS FIFO queues依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `high-throughput mode`

- **控制什麼：** `high-throughput mode`選擇SQS FIFO queues的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `visibility`

- **控制什麼：** `visibility`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在SQS FIFO queues依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

### Dead-letter queues：逐項設定說明

#### `redrive policy`

- **控制什麼：** `redrive policy`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `maxReceiveCount`

- **控制什麼：** `maxReceiveCount`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「需要保存失敗payload供診斷、修復與重播。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Dead-letter queues的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `redrive allow policy`

- **控制什麼：** `redrive allow policy`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `alarm`

- **控制什麼：** `alarm`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要保存失敗payload供診斷、修復與重播。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Dead-letter queues選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `replay procedure`

- **控制什麼：** `replay procedure`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

## 可以直接對照 AWS 的設定範例

### SQS queue、DLQ 與 redrive policy

```yaml
Resources:
  WorkerDlq:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600
      KmsMasterKeyId: alias/aws/sqs
  WorkerQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 360
      ReceiveMessageWaitTimeSeconds: 20
      MessageRetentionPeriod: 345600
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt WorkerDlq.Arn
        maxReceiveCount: 5
      KmsMasterKeyId: alias/aws/sqs

```

1. VisibilityTimeout應大於一般處理時間並可heartbeat延長；太短會造成同一工作並行重複。
2. Long polling 20秒降低empty receives與成本。
3. DLQ retention通常要比source queue長，且必須有ApproximateNumberOfMessagesVisible alarm與redrive runbook。

## 讀到這裡，請用自己的話說一次

1. Amazon SQS的責任：以managed queue解耦producer與consumer的時間和容量。
2. 底層機制：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
3. 第一個要看的設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
4. 選擇邏輯：Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。
5. 不要混淆：SQS FIFO queues的責任是「在message group內提供嚴格順序與deduplication能力。」；它不會自動取代Amazon SQS。
6. 替換訊號：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
7. 最常見錯法：處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。
8. 可移植原則：queues decouple time but require idempotent consumers。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| SQS FIFO queues | 在message group內提供嚴格順序與deduplication能力。 | MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。 | 同一business entity必須有序，且可用多groups平行處理。 | 全域單一group會限制throughput；business side effect仍需idempotency。 |
| Dead-letter queues | 隔離多次處理失敗的messages，避免poison message無限重試。 | Source queue以maxReceiveCount判斷移入DLQ；redrive可在修復後重送。 | 需要保存失敗payload供診斷、修復與重播。 | DLQ不是終點；沒有owner、alarm與runbook只是在延後遺失。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。 | 只有當題目條件明確改變時才可能合理。 | 處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。」之間做選擇。
- 認得常考設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜SQS Standard 與 FIFO 選型

一家圖片網站在促銷時每秒會送入數萬個縮圖工作。每張圖片彼此獨立，偶爾重複處理可以接受，需求是盡量提高吞吐量並讓 worker 自行擴縮。應選擇哪一項？

A. 使用 SQS Standard queue，並讓 consumer 以圖片工作 ID 實作冪等處理
B. 使用單一 MessageGroupId 的 SQS FIFO queue，藉此取得最高平行度
C. 使用 SNS topic，讓 worker 之後再回頭拉取尚未處理的通知
D. 使用 Kinesis Data Streams，因為所有非同步工作都必須能回播

**答案：A**

- **A：** 正確。工作互不依賴且優先追求吞吐量，Standard queue 是合適的 work buffer；因為可能重複投遞，consumer 仍要冪等。
- **B：** 錯誤。FIFO 的單一 message group 會把工作序列化；只有業務真的要求同一實體有序時才值得使用 FIFO。
- **C：** 錯誤。SNS 是 push fan-out，不是讓一群 worker 競爭拉取並保存 backlog 的工作佇列。
- **D：** 錯誤。Kinesis 適合保留、分割及供多個獨立 consumer 回播的事件流；題目沒有這些需求。

**事實查證：** [Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 2｜SAA｜Visibility timeout 與長工作

SQS worker 通常 4 分鐘完成工作，但少數工作需要 10 分鐘。現在 visibility timeout 為 5 分鐘，監控顯示長工作常被兩個 worker 同時執行。最適合的修正是什麼？

A. 把 message retention 改成 10 分鐘，讓 SQS 延後重新投遞
B. 將初始 visibility 設在正常處理範圍，長工作定期呼叫 ChangeMessageVisibility，且只在結果提交後 DeleteMessage
C. worker 收到 message 後立即 DeleteMessage，再開始執行工作
D. 讓 producer 增加 DelaySeconds，取代 consumer 的 visibility timeout

**答案：B**

- **A：** 錯誤。Retention 控制 message 最久保存多久，不控制已被接收的 message 何時再次可見。
- **B：** 正確。Visibility 必須覆蓋處理時間；無法預知的長工作可使用 receipt handle 延長，完成 durable side effect 後才刪除。
- **C：** 錯誤。先刪除等於在 durable side effect 完成前確認成功；worker 若隨後故障，SQS 已無法重新投遞，工作便會永久遺失。
- **D：** 錯誤。DelaySeconds 隱藏新送入的 message；visibility timeout 才管理已被 consumer 接收的 message。

**事實查證：** [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)

### 練習題 3｜SAA｜DLQ redrive 與營運處置

一個訂單 queue 偶爾收到格式錯誤的 poison message。團隊必須避免它們無限消耗 worker，並在修正 parser 後安全重處理。應採取哪兩項措施？（選兩項）

A. 把 DLQ 當作永久稽核檔案庫，不再設 retention 或處理 owner
B. 對所有錯誤都把 maxReceiveCount 設成 1，避免任何重試
C. 在 source queue 設 RedrivePolicy 與經測試的 maxReceiveCount，並替 DLQ 建立告警
D. 收到 DLQ message 後立刻自動無限 redrive，不必先判斷根因
E. 修正根因後使用受控 redrive，並確保 consumer 對重複處理具冪等性

**答案：C、E**

- **A：** 錯誤。DLQ 是失敗隔離與復原工作區，不是沒有生命週期、owner 與查詢能力的永久 archive。
- **B：** 錯誤。一次暫時性失敗就進 DLQ 通常過於激進；maxReceiveCount 應配合可恢復錯誤與重試時間設計。
- **C：** 正確。RedrivePolicy 控制移入 DLQ 的門檻，告警則確保失敗不會安靜累積。
- **D：** 錯誤。未修根因就持續 redrive 會再次製造 backlog 與失敗風暴。
- **E：** 正確。Redrive 會重新觸發處理，因此要先修正原因、控制速率並保護 side effect 不被重做。

**事實查證：** [Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)

### 練習題 4｜SAP｜Source queue 與 DLQ retention

Standard source queue retention 是 4 天，DLQ retention 也是 4 天。某 message 在 source queue 已停留 3 天後才被移入 DLQ。團隊通常要兩天才能完成調查。最重要的修改是什麼？

A. 把 visibility timeout 設成 2 天，避免 DLQ message 過期
B. 改成 FIFO queue，因為 FIFO message 永遠不會過期
C. 停用 redrive policy，讓 message 留在 source queue
D. 把 DLQ retention 設得比 source queue 更長，以涵蓋原始 enqueue 時間與調查窗口

**答案：D**

- **A：** 錯誤。Visibility 只在 message 被接收後暫時隱藏，不能延長 retention。
- **B：** 錯誤。FIFO message 也受 retention 約束；queue 類型不是永久保存機制。
- **C：** 錯誤。這會讓 poison message 繼續干擾主要處理流程。
- **D：** 正確。Standard message 移入 DLQ 時保留原始 enqueue timestamp，因此 DLQ retention 應長於 source 並涵蓋復原時間。

**事實查證：** [Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 5｜SAA｜Long polling 與 empty receives

一個低流量 queue 的 EC2 consumer 每秒 short poll，多數 ReceiveMessage 都是空回應，造成不必要的 API 成本。需求是不改變 message 處理語意。應如何改善？

A. 設定 ReceiveMessageWaitTimeSeconds，例如 20 秒，並讓 client HTTP timeout 大於等待時間
B. 把 visibility timeout 設成 20 秒
C. 把 MessageRetentionPeriod 設成 20 秒
D. 縮短輪詢間隔到 100 毫秒，增加命中機率

**答案：A**

- **A：** 正確。Long polling 等待 message 出現，可減少空回應與 false-empty；HTTP timeout 必須留足等待時間。
- **B：** 錯誤。Visibility 影響已接收 message 的再投遞，不會減少 queue 為空時的 polling。
- **C：** 錯誤。Retention 只決定未刪除 message 的保存期限。
- **D：** 錯誤。更頻繁 short poll 會增加 API、網路與 CPU 成本。

**事實查證：** [Amazon SQS short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)

### 練習題 6｜SAA｜FIFO message group 與去重邊界

付款工作要求同一 customer 的操作依序處理，但不同 customer 可平行；producer 也可能在 timeout 後重送同一命令。哪兩項設計正確？（選兩項）

A. 所有 message 都使用固定 MessageGroupId，保證全域順序並維持最大平行度
B. 使用 customer_id 作為 MessageGroupId，讓每位 customer 形成自己的 ordering lane
C. 使用 Standard queue，再靠 message attribute 排序即可得到 FIFO 行為
D. 對同一邏輯命令的 producer retry 重用穩定的 MessageDeduplicationId，但 consumer 仍需業務冪等
E. 依賴 content-based dedup 永久阻止任何相同付款內容再次發生

**答案：B、D**

- **A：** 錯誤。單一 group 會把所有 customer 串成一條序列，吞吐量反而受限。
- **B：** 正確。FIFO 僅保證 group 內順序，多個 customer group 可並行。
- **C：** 錯誤。Standard queue 是 best-effort ordering，consumer 排序不能補回已並行執行的 side effect。
- **D：** 正確。穩定 dedup ID 可抑制窗口內的重複 send，但窗口之外與 consumer retry 仍要靠業務冪等。
- **E：** 錯誤。FIFO dedup 有時間與作用範圍，不是永久 business deduplication。

**事實查證：** [Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

### 練習題 7｜SAA｜Lambda SQS partial batch response

Lambda 每次從 SQS 取得 10 筆，其中 1 筆格式錯誤。現在 function 丟出例外，結果另外 9 筆成功資料也會反覆出現。如何減少不必要的重做？

A. 收到 batch 時先刪除全部 10 筆，再逐筆處理
B. 將 queue retention 設為 0，讓失敗資料立刻消失
C. 啟用 partial batch response，回報失敗 item identifiers，並讓逐筆 side effect 冪等
D. 停用 Lambda retry，任何失敗 batch 都直接捨棄

**答案：C**

- **A：** 錯誤。先刪除會讓 function crash 時遺失尚未完成的工作。
- **B：** 錯誤。Retention 不是 batch 成功確認機制，而且 SQS retention 也不能設為 0。
- **C：** 正確。Partial batch response 只讓失敗 records 再次可見；冪等性仍保護已提交但 acknowledgement 不確定的情況。
- **D：** 錯誤。直接丟棄會讓暫時性與永久性錯誤都失去復原機會；應以 partial response、DLQ 與告警隔離失敗，同時保留受控重處理路徑。

**事實查證：** [Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)

### 練習題 8｜SAP｜SQS backlog 診斷

促銷部署後，ApproximateAgeOfOldestMessage 持續上升，但 consumer EC2 CPU 只有 25%。下一個最有效的調查動作是什麼？

A. 依 EC2 CPU 目標值立即把 consumer fleet 加倍，但暫不檢查 worker 等待時間與下游容量
B. 只檢查 NumberOfMessagesNotVisible，看到 in-flight 偏高便延長 visibility timeout
C. 先降低 visibility timeout 以增加 redelivery，期待更多 worker 能加速處理
D. 比較 arrival 與 completion rate，並檢查 visible/in-flight、consumer error/throttle 與 downstream latency

**答案：D**

- **A：** 錯誤。CPU 型擴縮適合 CPU-bound worker；若執行緒正等待資料庫或外部 API，直接加倍 consumer 可能放大下游壓力而未縮短 queue age。
- **B：** 錯誤。In-flight 偏高可提示工作時間或 visibility 設定問題，但只延長 visibility 不能判斷 arrival rate、完成率、錯誤或下游 throttling。
- **C：** 錯誤。縮短 visibility 只在需要更快接手失聯 worker 時可能合理；本題未先確認失聯，提早 redelivery 反而會製造重複工作並壓垮下游。
- **D：** 正確。低 CPU 可能表示 worker 卡在 I/O、被 throttle 或有大量 in-flight；queue age 與端到端速率能定位真正瓶頸。

**事實查證：** [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Cross-account SQS 與 SSE-KMS

Account B 的 application role 必須把 message 寫入 Account A 的 SSE-KMS SQS queue，且不得向 Internet 任意 principal 開放。哪兩項是必要的授權層？（選兩項）

A. 在 queue resource policy 精確允許 Account B role 執行 SendMessage，並可加 TLS、source 或 organization 條件
B. 把 queue policy 設為 Principal:"*"，因為 queue URL 很難猜
C. 只在 Account A 建立一個 IAM user policy；它會自動授權 Account B role
D. 只開啟 SSE-KMS；加密會自動授予跨帳號 SendMessage
E. 讓 producer identity 有 SQS 呼叫權限，並依所選 customer-managed KMS key 配置所需 key permissions

**答案：A、E**

- **A：** 正確。跨帳號 resource 必須明確信任外部 principal，並限制 action、resource 與條件。
- **B：** 錯誤。Queue URL 不是安全邊界；公開 principal 會擴大未授權發送風險。
- **C：** 錯誤。資源擁有帳號不能只靠本帳號 identity policy 替另一帳號 principal 完成雙方授權。
- **D：** 錯誤。Encryption 與 authorization 是不同邊界，SSE 不會自動允許 SQS 或 KMS 操作。
- **E：** 正確。外部 role 的 identity permission 與 queue/key resource trust 必須共同滿足；KMS 權限依 key 類型與 API 行為設定。

**事實查證：** [Least-privilege policies for encrypted Amazon SQS queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-least-privilege-policy.html)、[Configuring server-side encryption for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-sse-existing-queue.html)

### 練習題 10｜SAP｜SQS CloudFormation 設定審查

一個 CloudFormation template 的 source queue 設定 VisibilityTimeout: 30、ReceiveMessageWaitTimeSeconds: 0、MessageRetentionPeriod: 1209600；worker p99 需 4 分鐘，DLQ retention 為 1 天。哪一項審查結論最正確？

A. 只要把 DelaySeconds 設成 240，就能取代 visibility timeout 與 DLQ
B. maxReceiveCount 應設在 DLQ，source queue 不需要 RedrivePolicy
C. 提高 visibility 或由 worker 延長、啟用 long polling，並讓 DLQ retention 長於 source queue 的復原需求
D. 現有設定完整；message retention 14 天會自動避免重複處理

**答案：C**

- **A：** 錯誤。Delay 控制新 message 首次可見時間，不能保護正在處理的工作或隔離 poison message。
- **B：** 錯誤。RedrivePolicy 與 maxReceiveCount 設在 source queue，指向已建立的 DLQ。
- **C：** 正確。30 秒遠短於 4 分鐘處理時間，short poll 增加空請求，而 1 天 DLQ retention 可能不足以保留從 source 移入的失敗資料。
- **D：** 錯誤。Retention 不提供 processing lock，也不會消除 at-least-once delivery。

**事實查證：** [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)、[Amazon SQS short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Producer與consumer速率不同，工作需要buffer、retry與失敗隔離。」，所以「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」能直接滿足它；若constraint改成「Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」。替代方案「Visibility timeout要覆蓋處理時間並可延長；DLQ需設定redrive與告警。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Producer與consumer速率不同，工作需要buffer、retry與失敗隔離。」，排除會導致「處理成功前刪除message、timeout太短造成並行重複，或DLQ無人處理。」的選項，再選「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.1 Determine a strategy to improve overall operational excellence。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Standard queue追求高吞吐並接受至少一次與可能重排；FIFO在message group內提供順序與去重。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「queues decouple time but require idempotent consumers」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 53 章　SNS、EventBridge 與 Publish-Subscribe

一個事件可能需要推送到多個subscriber，並依內容routing到不同targets。

## 跟著一件工作在服務間流動：先從故事開始

把鏡頭拉到一個真實的production現場：訂單成立後庫存、通知、分析與詐欺服務都要獨立處理。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：一個事件可能需要推送到多個subscriber，並依內容routing到不同targets。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：Publish-subscribe像廣播：producer只宣布發生了什麼，各個listener自行決定是否以及如何反應。 廣播不等於持久workflow；delivery、順序、重試與schema仍要依服務分別設計。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon SNS是這一章的入口，Amazon EventBridge用來畫出邊界；主要方向「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：訂單成立後庫存、通知、分析與詐欺服務都要獨立處理。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[Amazon SNS]
          │ 以topic把同一message推送到多個subscribers。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Amazon EventBridge：以event bus路由AWS、SaaS與custom events到targets。
  · Amazon SQS：以managed queue解耦producer與consumer的時間和容量。

失敗時先找：直接同步呼叫所有subscriber，使一個慢服務拖垮producer。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Amazon SNS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon SNS和Amazon EventBridge並不是兩個任意的產品名稱。前者適合本章，是因為「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」直接回應了眼前的問題；後者描述的「SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：直接同步呼叫所有subscriber，使一個慢服務拖垮producer。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「publish facts once, let consumers own their pace」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon SNS | 以topic把同一message推送到多個subscribers。 | Publish後SNS fan-out到SQS、Lambda、HTTP、email/SMS等endpoint，可用filter policy。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |

## 把全圖套進一個具體案例

**場景：** 訂單成立後庫存、通知、分析與詐欺服務都要獨立處理。

1. 故事的起點：訂單成立後庫存、通知、分析與詐欺服務都要獨立處理。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon SNS負責「以topic把同一message推送到多個subscribers。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Publish後SNS fan-out到SQS、Lambda、HTTP、email/SMS等endpoint，可用filter policy。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EventBridge、Amazon SQS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「直接同步呼叫所有subscriber，使一個慢服務拖垮producer。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「複雜event routing/archive/SaaS integration用EventBridge；pull work buffer用SQS。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon SNS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：一個事件可能需要推送到多個subscriber，並依內容routing到不同targets。
- **具體例子／邊界：** 在「訂單成立後庫存、通知、分析與詐欺服務都要獨立處理。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EventBridge

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：直接同步呼叫所有subscriber，使一個慢服務拖垮producer。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：publish facts once, let consumers own their pace。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon SNS

- **功用：** 以topic把同一message推送到多個subscribers。
- **底層機制：** Publish後SNS fan-out到SQS、Lambda、HTTP、email/SMS等endpoint，可用filter policy。
- **關鍵設定：** standard/FIFO topic、subscriptions、filter policy、raw delivery、DLQ、KMS與resource policy。
- **選擇時機：** 簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。
- **替換時機：** 複雜event routing/archive/SaaS integration用EventBridge；pull work buffer用SQS。

### Amazon EventBridge

- **功用：** 以event bus路由AWS、SaaS與custom events到targets。
- **底層機制：** Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。
- **關鍵設定：** event buses、rules/patterns、targets、input transformer、archive/replay、DLQ與resource policy。
- **選擇時機：** domain events、cross-account integration、content-based routing與scheduler。
- **替換時機：** 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

## 考前與實作時再查：設定操作手冊

### Amazon SNS：逐項設定說明

#### `standard/FIFO topic`

- **控制什麼：** `standard/FIFO topic`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SNS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `subscriptions`

- **控制什麼：** `subscriptions`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `filter policy`

- **控制什麼：** `filter policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SNS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `raw delivery`

- **控制什麼：** `raw delivery`定義event/notification送到哪些consumers，以及是否套用filter、保留payload或跨帳號分享。
- **何時需要：** 一個producer需要fan-out到多個consumer、告警對象或workflow入口時。
- **怎麼設定／驗證：** 建立target/subscription與filter，設定resource policy、retry/DLQ和owner；用匹配與不匹配event各測一次。
- **常見錯法：** 只建立topic/bus卻沒有可用target不會產生business effect；consumer仍需處理duplicate與schema evolution。

#### `DLQ`

- **控制什麼：** `DLQ`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SNS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SNS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `resource policy`

- **控制什麼：** `resource policy`指定Amazon SNS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

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

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

## 可以直接對照 AWS 的設定範例

### EventBridge rule：只路由已付款訂單

```json
{
  "Source": ["com.acme.orders"],
  "DetailType": ["OrderStatusChanged"],
  "Detail": {
    "status": ["PAID"],
    "total": [{"numeric": [">", 0]}]
  }
}
```

1. Event pattern是content-based filter；producer只發布fact，不需知道所有consumers。
2. Target若需要buffer與retry isolation，通常把rule送到每個consumer自己的SQS queue。
3. 不要把EventBridge當長期high-throughput ordered log；需要replay/partition ordering時比較Kinesis/MSK。

## 讀到這裡，請用自己的話說一次

1. Amazon SNS的責任：以topic把同一message推送到多個subscribers。
2. 底層機制：Publish後SNS fan-out到SQS、Lambda、HTTP、email/SMS等endpoint，可用filter policy。
3. 第一個要看的設定：standard/FIFO topic、subscriptions、filter policy、raw delivery、DLQ、KMS與resource policy。
4. 選擇邏輯：SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。
5. 不要混淆：Amazon EventBridge的責任是「以event bus路由AWS、SaaS與custom events到targets。」；它不會自動取代Amazon SNS。
6. 替換訊號：複雜event routing/archive/SaaS integration用EventBridge；pull work buffer用SQS。
7. 最常見錯法：直接同步呼叫所有subscriber，使一個慢服務拖垮producer。
8. 可移植原則：publish facts once, let consumers own their pace。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon SNS | 以topic把同一message推送到多個subscribers。 | Publish後SNS fan-out到SQS、Lambda、HTTP、email/SMS等endpoint，可用filter policy。 | 簡單一對多通知、mobile/SMS/email或SNS→SQS fan-out。 | 複雜event routing/archive/SaaS integration用EventBridge；pull work buffer用SQS。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 | domain events、cross-account integration、content-based routing與scheduler。 | 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。 | 只有當題目條件明確改變時才可能合理。 | 直接同步呼叫所有subscriber，使一個慢服務拖垮producer。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。」之間做選擇。
- 認得常考設定：standard/FIFO topic、subscriptions、filter policy、raw delivery、DLQ、KMS與resource policy。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：複雜event routing/archive/SaaS integration用EventBridge；pull work buffer用SQS。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜SNS、EventBridge、SQS 與 Kinesis 選型

訂單事件需要依內容路由到不同 AWS 與 SaaS targets；producer 不應知道 consumers，且日後要能 archive/replay。哪個核心服務最符合？

A. SNS，因為任何 JSON message 都應用 topic 傳送
B. EventBridge event bus 與 rules
C. 單一 SQS queue，讓所有 consumer 都從同一 backlog 取得每個事件副本
D. Kinesis，因為所有多 consumer 系統都必須使用 shard

**答案：B**

- **A：** 錯誤。SNS 適合直接 push fan-out，但複雜 content routing、SaaS integration 與 archive/replay 更符合 EventBridge。
- **B：** 正確。Event pattern 讓 producer 發布 facts，由 rules 決定 targets，archive 可支援日後 replay。
- **C：** 錯誤。一個 SQS message 通常由一個 competing consumer 處理；每個 consumer 都要副本時需不同 queue。
- **D：** 錯誤。Kinesis 適合 retained ordered stream；題目沒有 per-partition ordering 或高吞吐 stream 要求。

**事實查證：** [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[Archiving and replaying Amazon EventBridge events](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html)、[SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)

### 練習題 2｜SAA｜SNS 至 SQS durable fan-out

OrderPlaced 必須同時交給庫存、通知和分析三個團隊；每個團隊處理速度不同，且任一團隊故障不能阻塞其他團隊。應採用哪個架構？

A. producer 依序同步呼叫三個 API
B. 三組 worker 共用一個 SQS queue
C. SNS topic 訂閱三個獨立 SQS queues，各自配置 consumer、retry 與 DLQ
D. SNS 直接寄送 email 給三個服務帳號

**答案：C**

- **A：** 錯誤。同步串接會把最慢或失敗的 subscriber 反向傳給 producer。
- **B：** 錯誤。共用 queue 會分攤工作，而不是讓三個 domain 都取得同一事件。
- **C：** 正確。SNS 複製事件，各 queue 保存自己的 backlog 並形成獨立 failure boundary。
- **D：** 錯誤。Email 適合人類通知，不是可靠的 machine-processing queue。

**事實查證：** [Fanout Amazon SNS notifications to Amazon SQS queues](https://docs.aws.amazon.com/sns/latest/dg/sns-sqs-as-subscriber.html)

### 練習題 3｜SAA｜SNS filter 與 EventBridge pattern

團隊要在傳送前過濾事件，減少不相關 deliveries。哪兩項設定與服務配對正確？（選兩項）

A. SNS subscription filter policy 可依 message attributes，或設定為依 message body 篩選
B. SQS visibility timeout 可依 JSON 欄位拒絕 message
C. EventBridge event pattern 可比對 event envelope 與 detail 中的欄位
D. EventBridge input transformer 是 authorization filter
E. 字串 "300" 與數字 300 在所有 filter 中必然等價

**答案：A、C**

- **A：** 正確。SNS filter policy 的 scope 可針對 attributes 或 body，需按實際 message shape 設計。
- **B：** 錯誤。Visibility 管理接收後的暫時隱藏，不做內容篩選。
- **C：** 正確。EventBridge pattern 依 event JSON 結構匹配 source、detail-type、detail 等。
- **D：** 錯誤。Input transformer 改變送往 target 的內容，不取代 rule matching 或權限。
- **E：** 錯誤。Filter 有型別與結構語意，應用真實事件測試 numeric/string matching。

**事實查證：** [Amazon SNS subscription filter policies](https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html)、[Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)

### 練習題 4｜SAA｜Target retry 與 DLQ

EventBridge rule 已成功匹配事件，但 HTTP target 持續失敗。團隊要限制重試時間並保存最終無法投遞的事件。應怎麼做？

A. 在 target 設 RetryPolicy 與 SQS DLQ，並授予 EventBridge 向 DLQ 發送的權限
B. 把 event bus archive 當作 target DLQ；兩者語意完全相同
C. 設定 SNS delivery policy，因為它會控制 EventBridge target
D. 設定 SQS visibility timeout，但不建立 queue

**答案：A**

- **A：** 正確。Target retry policy 控制最大 event age/attempts，DLQ 保存耗盡重試後的投遞失敗。
- **B：** 錯誤。Archive 用於歷史事件 replay；target DLQ 用於特定投遞失敗，營運流程不同。
- **C：** 錯誤。SNS delivery policy 只影響 SNS endpoint delivery。
- **D：** 錯誤。Visibility 是既有 SQS queue 的屬性，不能控制 EventBridge target retry。

**事實查證：** [Event retry policy and dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)

### 練習題 5｜SAP｜EventBridge archive 與 stream replay 邊界

稽核平台要求每個 customer 的事件保持順序，保存 30 天，五個 consumer 可各自維護 offset 並反覆 replay。最合適的核心資料通道是什麼？

A. SNS FIFO topic 啟用 30 天 archive，讓各 subscription 依時間窗發起 replay
B. EventBridge archive，因為它是 partitioned ordered log
C. Kinesis Data Streams，以 customer_id 分割並設定足夠 retention
D. SQS DLQ，將所有成功事件也存入其中

**答案：C**

- **A：** 錯誤。SNS FIFO 已支援最長 365 天的 archive 與 subscription replay，適合依時間窗重送；但它不提供 Kinesis 式持續維護的 per-consumer offset、shard processing 與任意位置串流消費語意。
- **B：** 錯誤。EventBridge archive 能 replay，但不是提供每-key ordered partitions 與獨立 offsets 的 stream。
- **C：** 正確。Kinesis 提供 retention、partition-key ordering 與多個獨立 consumers。
- **D：** 錯誤。DLQ 適合隔離耗盡重試的失敗投遞；若拿它保存所有成功事件，既沒有正常串流的 offset，也混淆主要資料通道與復原工作區。

**事實查證：** [Archiving and replaying Amazon EventBridge events](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html)、[Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[Amazon SNS FIFO topic message archiving and replay](https://docs.aws.amazon.com/sns/latest/dg/fifo-message-archiving-replay.html)

### 練習題 6｜SAA｜SNS FIFO 端到端順序

交易事件要 fan out 給兩個 queue，且每個 account 內必須按順序處理。哪兩項是端到端 FIFO 設計必要條件？（選兩項）

A. SNS Standard topic 搭配 SQS FIFO queues 即可保證 publisher order
B. 使用 SNS FIFO topic 並訂閱 SQS FIFO queues
C. 所有 account 共用一個 message group，才能提高平行度
D. 使用 account_id 作 MessageGroupId，並設計穩定 deduplication identity
E. 將 Lambda email subscription 加到 FIFO topic，便取得相同 FIFO 語意

**答案：B、D**

- **A：** 錯誤。Standard topic 不提供 FIFO topic 的 ordering/deduplication contract。
- **B：** 正確。SNS FIFO 的支援 fan-out 路徑以相容的 SQS FIFO subscriptions 為核心。
- **C：** 錯誤。單一 MessageGroupId 會把所有 accounts 序列化成同一 ordering lane；只有真的要求全域順序時才值得犧牲跨帳號平行度。
- **D：** 正確。Group 定義順序範圍，dedup identity 處理 producer 重送；consumer 仍需冪等。
- **E：** 錯誤。非 SQS endpoint 並不自動取得相同的 FIFO queue processing contract。

**事實查證：** [Amazon SNS FIFO topics](https://docs.aws.amazon.com/sns/latest/dg/sns-fifo-topics.html)、[Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)

### 練習題 7｜SAP｜Cross-account EventBridge 授權

中央 event bus 位於 shared-services account，應用帳號只能送入特定 source 的事件。哪個授權設計最適合？

A. 讓 rule pattern 充當 authorization；只要不匹配就算安全
B. 只修改 target Lambda execution role
C. 對整個 organization 開放 events:*，事後再查 logs
D. event-bus resource policy 信任指定帳號/organization，加上 sender identity permission 與必要 target invocation permissions

**答案：D**

- **A：** 錯誤。Pattern 決定 routing，不是阻止未授權 PutEvents 的安全邊界。
- **B：** 錯誤。Target role 不授權 sender 寫入 event bus。
- **C：** 錯誤。過寬 action 與無 source 限制違反 least privilege。
- **D：** 正確。Cross-account publication 與 target invocation 是分離的授權邊界，兩者都要明確設定。

**事實查證：** [Sending and receiving Amazon EventBridge events between AWS accounts](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cross-account.html)

### 練習題 8｜SAP｜EventBridge delivery 診斷

Producer 的 PutEvents 回報成功，rule 的 matched-events 指標也增加，但 target Lambda 完全沒有 invocation。第一輪應查什麼？

A. target invocation/failed-invocation 指標、Lambda resource policy、rule target role、throttling 與 DLQ 權限
B. 用 archive replay 重送同一批事件，暫不檢查 target 權限或 FailedInvocations
C. 回頭檢查 producer 的 PutEvents IAM 與 event pattern，忽略已增加的 TriggeredRules 指標
D. 先提高 Lambda reserved concurrency，未確認 Throttles、Invocations 或 resource-based policy

**答案：A**

- **A：** 正確。Event 已進 bus 且 rule 已匹配，故障範圍縮小到 target invocation、permission、throttle、retry/DLQ。
- **B：** 錯誤。Replay 適合根因修復後補送歷史事件；在 target 權限或投遞路徑尚未確認前重播，只會再次產生失敗並擴大待處理量。
- **C：** 錯誤。若 TriggeredRules 沒有增加，才應優先查 pattern 與事件欄位；本題已證明 rule 匹配，故應把範圍縮到 target invocation。
- **D：** 錯誤。Reserved concurrency 適合已觀察到 Lambda throttling 時保留容量；本題 invocation 為零，仍須先查 EventBridge 指標與 Lambda resource policy。

**事實查證：** [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[Event retry policy and dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)、[Monitoring Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-monitoring.html)、[Using resource-based policies for Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Event contract 演進

數十個團隊消費 OrderStatusChanged。Producer 要新增欄位，未來也可能有破壞性語意變更。哪兩項能降低演進風險？（選兩項）

A. 維持穩定 source/detail-type，新增向後相容欄位，要求 consumer 忽略未知欄位
B. 直接重新命名現有欄位，因為 EventBridge 不強制 schema
C. 把每個 consumer 名稱寫入事件，讓 producer 控制執行順序
D. 用 free-form message 讓各 consumer 自行猜測語意
E. 對破壞性變更使用明確的新 event version/type，並在遷移期同時觀測新舊 consumers

**答案：A、E**

- **A：** 正確。Additive contract 與 tolerant readers 讓既有 consumers 不因未知欄位失敗。
- **B：** 錯誤。Schemaless transport 不代表沒有 consumer contract；改名會破壞舊程式。
- **C：** 錯誤。事件應描述已發生的 fact，不應把所有 downstream orchestration 耦合回 producer。
- **D：** 錯誤。缺少明確 schema/version 會讓錯誤延後到 runtime。
- **E：** 正確。Breaking semantics 應有可辨識版本與可觀測的 phased migration。

**事實查證：** [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)、[SAP-C02 Domain 4: Accelerate Workload Migration and Modernization](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)

### 練習題 10｜SAA｜EventBridge rule JSON 審查

實際事件為 {"source":"com.shop.orders","detail-type":"OrderStatusChanged","detail":{"status":"PAID"}}。哪個 pattern 能只選出已付款事件？

A. {"status":["PAID"],"source":["com.shop.orders"]}
B. {"source":["com.shop.orders"],"detail-type":["OrderStatusChanged"],"detail":{"status":["PAID"]}}
C. {"source":"com.shop.orders","detail":{"status":"PAID"}}
D. {"detail":{"status":[{"exists":false}]}}

**答案：B**

- **A：** 錯誤。status 位於 detail，不在 event root。
- **B：** 正確。Pattern 的陣列與巢狀結構對應實際 event envelope。
- **C：** 錯誤。EventBridge pattern 的一般值使用陣列表示可接受值，且此寫法也省略 detail-type 限制。
- **D：** 錯誤。exists:false 會選出沒有 status 的事件，與需求相反。

**事實查證：** [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filter…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「一個事件可能需要推送到多個subscriber，並依內容routing到不同targets。」，所以「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」能直接滿足它；若constraint改成「SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」。替代方案「SQS常放在subscriber前吸收背壓；EventBridge不取代長期stream replay。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「直接同步呼叫所有subscriber，使一個慢服務拖垮producer。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「一個事件可能需要推送到多個subscriber，並依內容routing到不同targets。」，排除會導致「直接同步呼叫所有subscriber，使一個慢服務拖垮producer。」的選項，再選「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「SNS做直接fan-out與mobile/SMS；EventBridge做event bus、filtering、archive與SaaS整合。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「publish facts once, let consumers own their pace」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 54 章　Kinesis Ordering、Partition 與 Consumer Scaling

需要同key順序的高速事件流，容量由shards/partitions與consumer方式決定。

## 跟著一件工作在服務間流動：先從故事開始

如果今天由你值班，收到的需求可能是這樣：每位使用者事件需有序，不同使用者可平行，三個consumer各自讀取。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：需要同key順序的高速事件流，容量由shards/partitions與consumer方式決定。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：DynamoDB像把大量卡片依partition key分到不同抽屜；key選得好就能直接找到，選得差就會讓所有人擠在同一個抽屜。 這只是起點，因為實際partition由服務管理，類比不代表能手動指定實體節點；仍要用access pattern與capacity metric驗證。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon Kinesis Data Streams承接主要責任，以Enhanced fan-out檢查替代條件，並用「以business key分partition，監控iterator age，按吞吐與hot key拆分。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：每位使用者事件需有序，不同使用者可平行，三個consumer各自讀取。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[Amazon Kinesis Data Streams]
          │ 保存可重播、按partition key排序的即時event log。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Enhanced fan-out：讓Kinesis consumer取得每shard專用讀取throughput與較低傳遞延遲。
  · Amazon Data Firehose：把streaming records以managed buffering、可選transform後送到S3…

失敗時先找：把所有事件用tenant常數當partition key，單shard成為瓶頸。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Amazon Kinesis Data Streams有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Kinesis Data Streams和Enhanced fan-out並不是兩個任意的產品名稱。前者適合本章，是因為「以business key分partition，監控iterator age，按吞吐與hot key拆分。」直接回應了眼前的問題；後者描述的「Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把所有事件用tenant常數當partition key，單shard成為瓶頸。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「ordering scope and partition key are the same design decision」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Kinesis Data Streams | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 |
| Enhanced fan-out | 讓Kinesis consumer取得每shard專用讀取throughput與較低傳遞延遲。 | Consumer註冊後由Kinesis以HTTP/2 push records；不同enhanced consumers不再共享傳統GetRecords的per-shard read throughput。 |
| Amazon Data Firehose | 把streaming records以managed buffering、可選transform後送到S3/Redshift/OpenSearch等destination。 | Service依buffer size/time成批，呼叫Lambda轉換並管理retry與backup。 |

## 把全圖套進一個具體案例

**場景：** 每位使用者事件需有序，不同使用者可平行，三個consumer各自讀取。

1. 故事的起點：每位使用者事件需有序，不同使用者可平行，三個consumer各自讀取。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Kinesis Data Streams負責「保存可重播、按partition key排序的即時event log。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Enhanced fan-out、Amazon Data Firehose各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把所有事件用tenant常數當partition key，單shard成為瓶頸。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Kinesis Data Streams

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：需要同key順序的高速事件流，容量由shards/partitions與consumer方式決定。
- **具體例子／邊界：** 在「每位使用者事件需有序，不同使用者可平行，三個consumer各自讀取。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Enhanced fan-out

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把所有事件用tenant常數當partition key，單shard成為瓶頸。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：ordering scope and partition key are the same design decision。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

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

### Enhanced fan-out

- **功用：** 讓Kinesis consumer取得每shard專用讀取throughput與較低傳遞延遲。
- **底層機制：** Consumer註冊後由Kinesis以HTTP/2 push records；不同enhanced consumers不再共享傳統GetRecords的per-shard read throughput。
- **關鍵設定：** registered consumer、SubscribeToShard、consumer ARN、shard count、read throughput、retention與consumer lag。
- **選擇時機：** 多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。
- **替換時機：** 少量可接受polling latency的consumer可用shared throughput；enhanced fan-out不修復hot partition key。

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

### Enhanced fan-out：逐項設定說明

#### `registered consumer`

- **控制什麼：** 在Kinesis Data Streams中建立具名稱與ARN的consumer資源，讓它取得每shard獨立的enhanced fan-out讀取通道。
- **何時需要：** 同一stream有多個低延遲consumer，傳統GetRecords shared throughput造成互相競爭或iterator age上升時。
- **怎麼設定／驗證：** 以RegisterStreamConsumer建立唯一consumer name，等待ACTIVE後讓client使用SubscribeToShard，並監控consumer與shard lag。
- **常見錯法：** 註冊consumer不會增加shard寫入容量，也不能修復hot partition key；閒置registered consumers仍應清理並評估費用。

#### `SubscribeToShard`

- **控制什麼：** `SubscribeToShard`設定Enhanced fan-out的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `consumer ARN`

- **控制什麼：** 唯一識別已註冊的enhanced fan-out consumer，SubscribeToShard與IAM resource scope會用它選定讀取身份。
- **何時需要：** 同一stream有多個獨立應用，需要明確授權、觀測並追蹤每個consumer的低延遲訂閱時。
- **怎麼設定／驗證：** 從DescribeStreamConsumer取得ACTIVE consumer ARN，將它交給SubscribeToShard並在IAM中只允許需要的stream與consumer資源。
- **常見錯法：** 誤用stream ARN或舊consumer ARN會造成授權／訂閱失敗；重新註冊同名consumer後也不能假設ARN永遠不變。

#### `shard count`

- **控制什麼：** `shard count`設定Enhanced fan-out的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `read throughput`

- **控制什麼：** `read throughput`設定Enhanced fan-out的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Enhanced fan-out的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `consumer lag`

- **控制什麼：** `consumer lag`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

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
4. 選擇邏輯：以business key分partition，監控iterator age，按吞吐與hot key拆分。
5. 不要混淆：Enhanced fan-out的責任是「讓Kinesis consumer取得每shard專用讀取throughput與較低傳遞延遲。」；它不會自動取代Amazon Kinesis Data Streams。
6. 替換訊號：單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。
7. 最常見錯法：把所有事件用tenant常數當partition key，單shard成為瓶頸。
8. 可移植原則：ordering scope and partition key are the same design decision。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Kinesis Data Streams | 保存可重播、按partition key排序的即時event log。 | Hash partition key把records分到shards；每個shard內有sequence order，多consumer各自checkpoint。 | 多個獨立consumer、需要replay、per-key ordering與AWS-native streaming。 | 單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。 |
| Enhanced fan-out | 讓Kinesis consumer取得每shard專用讀取throughput與較低傳遞延遲。 | Consumer註冊後由Kinesis以HTTP/2 push records；不同enhanced consumers不再共享傳統GetRecords的per-shard read throughput。 | 多個低延遲consumers同讀stream且傳統shared throughput造成lag或互相競爭時。 | 少量可接受polling latency的consumer可用shared throughput；enhanced fan-out不修復hot partition key。 |
| Amazon Data Firehose | 把streaming records以managed buffering、可選transform後送到S3/Redshift/OpenSearch等destination。 | Service依buffer size/time成批，呼叫Lambda轉換並管理retry與backup。 | 目標是可靠delivery而非自訂consumer與replay。 | 需要多consumer、長期replay或per-key處理時用Kinesis Data Streams/MSK。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。 | 只有當題目條件明確改變時才可能合理。 | 把所有事件用tenant常數當partition key，單shard成為瓶頸。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。」之間做選擇。
- 認得常考設定：on-demand/provisioned mode、shards、retention、partition key、enhanced fan-out、KMS與iterator age。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：單一work queue用SQS；只需delivery到S3/Redshift用Data Firehose；Kafka ecosystem用MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Kinesis Data Streams 適用邊界

遙測資料要保存 7 天，三個 applications 各自從同一資料流讀取、維護進度並可回播；同一 device 的事件要有序。應選哪項？

A. 一個 SQS queue，讓三個 consumer group 都取得每筆 message
B. Amazon Data Firehose，讓三個任意程式維護各自 offset
C. Kinesis Data Streams，以 device_id 作 partition key
D. SNS topic，依 subscription 回讀過去 7 天

**答案：C**

- **A：** 錯誤。一個 queue 是 competing-consumer work distribution，不會自然為三個應用保留獨立 replay 位置。
- **B：** 錯誤。Firehose 是 managed delivery 到目的地，不是一般 consumer offset/replay platform。
- **C：** 正確。Kinesis 提供 retained stream、多 consumer 與 partition-key ordering。
- **D：** 錯誤。SNS 不保存可供 subscriber 任意回讀的 7 天 log。

**事實查證：** [Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[SAA-C03 Domain 3: Design High-Performing Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html)

### 練習題 2｜SAA｜Partition key 與 hot shard

所有 events 目前都以 tenant 作 partition key，但單一大型 tenant 佔 80% 流量，造成一個 shard throttling。每位 user 內仍須有序。最佳修改為何？

A. 每筆 event 產生完全隨機 key，忽略 user ordering
B. 改用 event timestamp，因為時間一定平均
C. 增加 consumer 數量；producer throttling 會自動消失
D. 改用 user_id 作 partition key，讓需排序的最小 business scope 分散到多個 shards

**答案：D**

- **A：** 錯誤。隨機 key 可分散寫入，但破壞同一 user 的順序需求。
- **B：** 錯誤。時間可能讓 burst 集中，且不保留 entity order。
- **C：** 錯誤。Consumer scaling 不增加 shard producer write capacity。
- **D：** 正確。Partition key 同時決定資料分布與 ordering scope，應選最小需要順序的高基數 key。

**事實查證：** [Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

### 練習題 3｜SAA｜Provisioned shard 容量估算

團隊要估算 provisioned stream 的 shard 數。哪兩項資訊不可省略？（選兩項）

A. 預估每秒 records/bytes、record size 與尖峰 headroom
B. 只用每日保存 GB，因為 shard 數只由 storage 決定
C. Enhanced fan-out consumer 數會直接增加 producer write capacity
D. 部署更多 KCL workers 會自動建立 shards
E. Consumer read demand、shared/EFO 模式，以及 partition-key skew/hot keys

**答案：A、E**

- **A：** 正確。Provisioned sizing 必須同時符合每-shard record 與 byte write limits，並保留尖峰空間。
- **B：** 錯誤。Retention storage 與每秒 ingest/read capacity 是不同維度。
- **C：** 錯誤。EFO 隔離 read throughput，不改變 producer write quota。
- **D：** 錯誤。Workers 消費既有 shards，不負責 resharding。
- **E：** 正確。讀取方式、consumer 數及不均勻 key 可能比平均吞吐更早形成瓶頸。

**事實查證：** [Amazon Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)、[Developing consumers with enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)

### 練習題 4｜SAA｜On-demand 與 provisioned mode

新產品流量高度不可預測，團隊沒有可靠 shard forecast，並優先降低容量管理工作。哪個選擇最合理？

A. Provisioned mode 並永遠固定一個 shard
B. On-demand capacity mode，同時仍設計分散的 partition keys 並監控 throttling
C. Enhanced fan-out，因為它是 producer capacity mode
D. Firehose，因為它能讓自訂 consumers 任意 replay

**答案：B**

- **A：** 錯誤。Provisioned mode 固定單 shard 適合穩定且可預測的小流量；本題流量不可預測，固定容量容易在尖峰 throttling，並增加人工調整負擔。
- **B：** 正確。On-demand 減少 shard planning，但不消除 key skew、quota、成本與監控責任。
- **C：** 錯誤。EFO 是 consumer read 選項，不是 stream write capacity mode。
- **D：** 錯誤。Firehose 不是可供任意 consumer replay 的 retained stream。

**事實查證：** [Amazon Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)

### 練習題 5｜SAA｜Enhanced fan-out

四個 Kinesis consumers 使用 shared polling 後互相競爭 read throughput，其中 fraud consumer 要低延遲且不能受 analytics consumer 影響。應採用什麼？

A. 增加 producer retries
B. 將所有 consumers 改成同一 KCL application name
C. 為需要隔離的 consumer 註冊 enhanced fan-out consumer
D. 增加 stream retention

**答案：C**

- **A：** 錯誤。Producer retry 不改善 consumers 共享讀取容量。
- **B：** 錯誤。同一 application name 代表共同分攤 shards，不是每個應用各自取得完整 stream。
- **C：** 正確。EFO 以專屬 per-shard read throughput 與 push delivery 隔離 registered consumers。
- **D：** 錯誤。Retention 延長 replay window，不增加即時 read throughput。

**事實查證：** [Developing consumers with enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)

### 練習題 6｜SAP｜PutRecords partial failure

PutRecords 回傳 HTTP 200，但部分 entries 含 error code；同一 account 的更新必須嚴格有序，且重送不得重複 side effect。哪兩項處理正確？（選兩項）

A. 視 HTTP 200 為整批成功，忽略 entry results
B. 對每個 account 序列化使用 PutRecord；後續寫入帶入前一筆成功回傳的 SequenceNumberForOrdering，失敗時不放行該 account 的後續事件
C. 只重試 PutRecords 的失敗 entries；只要 partition key 相同，就假設原始批次順序一定保留
D. 讓 downstream 依穩定 event identity 實作冪等處理
E. 每次 retry 改用 random partition key，以提高吞吐且仍保序

**答案：B、D**

- **A：** 錯誤。PutRecords 允許 partial success，必須逐 entry 檢查。
- **B：** 正確。PutRecords 沒有 SequenceNumberForOrdering；需要嚴格 producer order 時，可按 ordering key 序列化 PutRecord，並用前一 sequence number 約束下一筆寫入。
- **C：** 錯誤。只重試失敗項目雖減少重複，但批次可能部分成功；若後一筆先成功、前一筆後補，僅保留 partition key 仍無法恢復原始嚴格順序。
- **D：** 正確。Producer timeout/partial retry 仍可能重複，consumer side effect 必須冪等。
- **E：** 錯誤。Random key 會把同一 account 分散到不同 shards，失去 ordering scope；它只適合事件彼此獨立、吞吐優先且不要求 per-account 順序的情境。

**事實查證：** [Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[PutRecords API reference](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecords.html)、[Adding data to a stream with PutRecord](https://docs.aws.amazon.com/streams/latest/dev/developing-producers-with-sdk.html)、[Handling duplicate Kinesis Data Streams records](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 7｜SAP｜Iterator age 診斷

IncomingBytes 穩定，但 IteratorAgeMilliseconds 只在其中一個 shard 快速上升。最佳第一個推論與動作是什麼？

A. 可能是 hot shard 或該 shard consumer/downstream 卡住；按 shard 檢查 throttles、errors、processing latency 與 key distribution
B. 立即 reshard 增加 shards，尚未檢查該 shard 的 consumer error、downstream latency 或 partition-key 分布
C. 先提高 retention，替修復爭取 replay 時間，並把它視為降低 iterator age 的直接方法
D. 把 KCL workers 增加到 active shard 數的數倍，假設同一 shard 可被多個 workers 同時有序處理

**答案：A**

- **A：** 正確。單 shard lag 指向分布或該 shard processing path，需按維度定位後才決定 reshard/consumer 修正。
- **B：** 錯誤。Reshard 適合已證實 write hot shard 或需要更多 shard capacity 的情境；若是單一 consumer 或下游卡住，先擴 shard 會改變拓撲卻未修根因。
- **C：** 錯誤。延長 retention 可保住較長 recovery window，但不會直接降低 iterator age；consumer service rate 仍必須追上該 shard 的資料。
- **D：** 錯誤。增加 workers 適合尚有未分派 shards 時；KCL 同一 application 在同一時間仍由一個 lease owner 處理一個 shard，不能藉此提高該 shard 平行度。

**事實查證：** [Monitoring Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)、[Kinesis Client Library concepts](https://docs.aws.amazon.com/streams/latest/dev/kcl-concepts.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 8｜SAP｜Retention 與 consumer replay

Consumer bug 平均要 18 小時才會被發現，修復與 replay 最多再需 12 小時。Stream 目前只保存 24 小時。最穩健的改進為何？

A. 只增加 checkpoint 頻率；checkpoint 包含所有 payload 備份
B. 維持 24 小時，因為 Kinesis retention 永久有效
C. 把 replay records 改用 random key
D. 將 retention 設到超過偵測加修復窗口，並保留獨立 checkpoints 與 downstream idempotency

**答案：D**

- **A：** 錯誤。Checkpoint 是消費位置，不是 records 的備份。
- **B：** 錯誤。Kinesis 只允許 consumer 讀取 retention window 內的 records；超過保存期限後資料不可再 replay，因此 24 小時無法覆蓋 30 小時復原窗口。
- **C：** 錯誤。改 key 會破壞原 ordering scope，且不能恢復已過期資料。
- **D：** 正確。Recovery window 必須小於 retention；replay 會再執行 side effects，需冪等保護。

**事實查證：** [Changing the Kinesis Data Streams retention period](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)、[Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[Kinesis Client Library concepts](https://docs.aws.amazon.com/streams/latest/dev/kcl-concepts.html)、[Handling duplicate Kinesis Data Streams records](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜KCL leases 與 checkpoints

一個 KCL application 有 8 個 active shards，團隊打算啟動 40 個 workers 並在處理前 checkpoint。哪兩項審查意見正確？（選兩項）

A. 同一 KCL application 的有效 shard-level 平行度受 active shards 限制，額外 workers 可能閒置
B. 40 workers 會讓每個 shard 的 ordered throughput 增加五倍
C. 所有不同 applications 應共用同一 checkpoint，避免重複讀取
D. 處理前 checkpoint 可保證 worker crash 後資料不遺失
E. 應在必要 side effect durable commit 後 checkpoint，並讓處理可安全重放

**答案：A、E**

- **A：** 正確。KCL 透過 leases 將 shards 分派給 workers；一個 shard 不會因更多 workers 而無限並行。
- **B：** 錯誤。Shard capacity 與 order boundary 仍存在。
- **C：** 錯誤。不同 consumer applications 需要獨立進度。
- **D：** 錯誤。先 checkpoint 再 crash 可能跳過尚未完成的 record。
- **E：** 正確。先提交結果再 checkpoint 並接受可能 replay，是較安全的 at-least-once 處理順序。

**事實查證：** [Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)、[Kinesis Client Library concepts](https://docs.aws.amazon.com/streams/latest/dev/kcl-concepts.html)、[Handling duplicate Kinesis Data Streams records](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html)

### 練習題 10｜SAP｜三 consumer stream 架構審查

架構使用 constant partition key，把全部交易寫到單 shard；三個低延遲 consumer 共用 polling，且沒有 iterator-age alarm。哪項改造最完整？

A. 保留 constant key，只增加 Firehose destination
B. 把所有 records 送進一個 SQS queue，讓三個 consumer 都取得完整副本
C. 依交易所需 ordering scope 選高基數 key，重新評估 mode/shards，必要時用 EFO，並監控 write throttles 與 iterator age
D. 只把 retention 從一天提高到七天

**答案：C**

- **A：** 錯誤。Firehose 不會移除原 stream 的 hot shard 或 consumer contention。
- **B：** 錯誤。一個 SQS queue 採 competing-consumer 模型，同一 message 通常只由其中一個應用處理；三個獨立應用都要副本時需 fan-out 到不同 queues。
- **C：** 正確。此方案同時修正 partitioning、capacity、consumer isolation 與可觀測性。
- **D：** 錯誤。Retention 改善 recovery window，但不修復 throughput 與 lag。

**事實查證：** [Amazon Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)、[Developing consumers with enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)、[Monitoring Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以business key分partition，監控iterator age，按吞吐與hot key拆分。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「需要同key順序的高速事件流，容量由shards/partitions與consumer方式決定。」，所以「以business key分partition，監控iterator age，按吞吐與hot key拆分。」能直接滿足它；若constraint改成「Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以business key分partition，監控iterator age，按吞吐與hot key拆分。」。替代方案「Enhanced fan-out隔離consumer throughput；Firehose適合delivery而非任意consumer logic。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把所有事件用tenant常數當partition key，單shard成為瓶頸。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「需要同key順序的高速事件流，容量由shards/partitions與consumer方式決定。」，排除會導致「把所有事件用tenant常數當partition key，單shard成為瓶頸。」的選項，再選「以business key分partition，監控iterator age，按吞吐與hot key拆分。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.5 Determine high-performing data ingestion and transformation solutions；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以business key分partition，監控iterator age，按吞吐與hot key拆分。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「ordering scope and partition key are the same design decision」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 55 章　Step Functions、Workflow 與 Human Approval

多步驟流程需要state、retry、timeout、branch與補償，不能只靠函式互相呼叫。

## 跟著一件工作在服務間流動：先從故事開始

故事從一個看似簡單的需求開始：貸款流程需平行查核、人工核准、72小時等待與失敗補償。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：多步驟流程需要state、retry、timeout、branch與補償，不能只靠函式互相呼叫。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

Workflow像一張可追蹤的辦事流程表：哪些步驟平行、哪裡等待簽核、失敗後要補償，都明白寫在狀態上。 流程引擎只能協調，不能自動讓每個business action具備transaction或冪等性。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Step Functions會是本章的主要角色，Standard Workflows則幫我們看清邊界。方向是「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：貸款流程需平行查核、人工核准、72小時等待與失敗補償。

Start workflow
  ├─ 並行查核 A ─┐
  ├─ 並行查核 B ─┼─> Choice：是否進人工核准？
  └─ 並行查核 C ─┘
                         │ task token / callback
                         ▼
                  等待數小時或數天
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
          核准繼續                 拒絕／逾時
             │                       │
             └──── success      compensate / close

State machine保存流程進度；每個business action本身仍要可安全重試。

失敗時先找：Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問AWS Step Functions有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Step Functions和Standard Workflows並不是兩個任意的產品名稱。前者適合本章，是因為「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」直接回應了眼前的問題；後者描述的「EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「make orchestration state explicit and inspectable」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |
| Standard Workflows | 提供durable、exactly-once workflow execution與最長一年的歷史。 | 每個state transition持久化，可使用callback/task token等待外部或人工事件。 |
| Express Workflows | 提供高吞吐、短時間的Step Functions workflows。 | Optimized runtime不保存完整Standard history；sync/async Express具有不同delivery semantics。 |

## 把全圖套進一個具體案例

**場景：** 貸款流程需平行查核、人工核准、72小時等待與失敗補償。

1. 故事的起點：貸款流程需平行查核、人工核准、72小時等待與失敗補償。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Step Functions負責「以可視化state machine編排多步驟、retry、branch、parallel與human workflow。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Standard Workflows、Express Workflows各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Step Functions

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：多步驟流程需要state、retry、timeout、branch與補償，不能只靠函式互相呼叫。
- **具體例子／邊界：** 在「貸款流程需平行查核、人工核准、72小時等待與失敗補償。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Standard Workflows

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：make orchestration state explicit and inspectable。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### human approval

高風險action執行前由具名人員查看evidence並做有期限、不可重放且可稽核的決策。

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### ETL

Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

### Standard Workflows

- **功用：** 提供durable、exactly-once workflow execution與最長一年的歷史。
- **底層機制：** 每個state transition持久化，可使用callback/task token等待外部或人工事件。
- **關鍵設定：** execution timeout、history/logging、Retry/Catch、callback heartbeat與execution name。
- **選擇時機：** 付款、order、human approval與長時間可稽核流程。
- **替換時機：** 極高量、短時間且可接受at-least-once/asynchronous semantics時選Express。

### Express Workflows

- **功用：** 提供高吞吐、短時間的Step Functions workflows。
- **底層機制：** Optimized runtime不保存完整Standard history；sync/async Express具有不同delivery semantics。
- **關鍵設定：** sync/async type、CloudWatch Logs、timeout、idempotency與service integration。
- **選擇時機：** IoT ingestion、短ETL與高TPS orchestration。
- **替換時機：** 長達數日、human approval或需要durable execution history時選Standard。

## 考前與實作時再查：設定操作手冊

### AWS Step Functions：逐項設定說明

#### `Standard/Express`

- **控制什麼：** `Standard/Express`選擇AWS Step Functions的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `Task/Choice/Map/Parallel/Wait`

- **控制什麼：** `Task/Choice/Map/Parallel/Wait`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Step Functions的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `Retry/Catch`

- **控制什麼：** `Retry/Catch`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `timeouts`

- **控制什麼：** `timeouts`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Step Functions的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `callback token`

- **控制什麼：** `callback token`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** AWS Step Functions需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

### Standard Workflows：逐項設定說明

#### `execution timeout`

- **控制什麼：** `execution timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「付款、order、human approval與長時間可稽核流程。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Standard Workflows的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `history/logging`

- **控制什麼：** `history/logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「付款、order、human approval與長時間可稽核流程。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Standard Workflows選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `Retry/Catch`

- **控制什麼：** `Retry/Catch`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「付款、order、human approval與長時間可稽核流程。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Standard Workflows依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `callback heartbeat`

- **控制什麼：** `callback heartbeat`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** Standard Workflows需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `execution name`

- **控制什麼：** `execution name`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** Standard Workflows需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

### Express Workflows：逐項設定說明

#### `sync/async type`

- **控制什麼：** `sync/async type`控制model選擇/grounding、knowledge-base同步、event payload轉換或API consumer的quota/rate plan。
- **何時需要：** AI、event-driven或public API需要可版本化quality、資料新鮮度、payload contract或tenant限額時。
- **怎麼設定／驗證：** 鎖定model/version與eval，設定grounding threshold或sync schedule；event/API則定義transform schema、API key plan、quota與throttle。
- **常見錯法：** Model或sync成功不代表回答正確；input transform漏欄位會破壞consumer，usage plan也不能取代authentication/authorization。

#### `CloudWatch Logs`

- **控制什麼：** `CloudWatch Logs`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「IoT ingestion、短ETL與高TPS orchestration。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Express Workflows選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「IoT ingestion、短ETL與高TPS orchestration。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Express Workflows的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `idempotency`

- **控制什麼：** `idempotency`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** Express Workflows需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `service integration`

- **控制什麼：** `service integration`把Express Workflows與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 可以直接對照 AWS 的設定範例

### Step Functions：重試、Catch 與人工 callback

```json
{
  "StartAt": "ChargePayment",
  "States": {
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "TimeoutSeconds": 20,
      "Retry": [{
        "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
        "IntervalSeconds": 2,
        "BackoffRate": 2,
        "MaxAttempts": 4
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "CancelOrder"
      }],
      "Next": "WaitForApproval"
    },
    "WaitForApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
      "HeartbeatSeconds": 3600,
      "Next": "CompleteOrder"
    },
    "CancelOrder": {"Type": "Task", "Resource": "COMPENSATION_TASK", "End": true},
    "CompleteOrder": {"Type": "Succeed"}
  }
}
```

1. 只重試可恢復的service/throttle errors；payment Lambda本身仍需idempotency key。
2. Catch把技術錯誤轉入business compensation，不等於rollback分散式transaction。
3. waitForTaskToken可等待外部/人工callback，不需Lambda持續執行或sleep。

## 讀到這裡，請用自己的話說一次

1. AWS Step Functions的責任：以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
2. 底層機制：Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
3. 第一個要看的設定：Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
4. 選擇邏輯：Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。
5. 不要混淆：Standard Workflows的責任是「提供durable、exactly-once workflow execution與最長一年的歷史。」；它不會自動取代AWS Step Functions。
6. 替換訊號：純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。
7. 最常見錯法：Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。
8. 可移植原則：make orchestration state explicit and inspectable。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| Standard Workflows | 提供durable、exactly-once workflow execution與最長一年的歷史。 | 每個state transition持久化，可使用callback/task token等待外部或人工事件。 | 付款、order、human approval與長時間可稽核流程。 | 極高量、短時間且可接受at-least-once/asynchronous semantics時選Express。 |
| Express Workflows | 提供高吞吐、短時間的Step Functions workflows。 | Optimized runtime不保存完整Standard history；sync/async Express具有不同delivery semantics。 | IoT ingestion、短ETL與高TPS orchestration。 | 長達數日、human approval或需要durable execution history時選Standard。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。 | 只有當題目條件明確改變時才可能合理。 | Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。」之間做選擇。
- 認得常考設定：Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.1 Determine a strategy to improve overall operational excellence；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Standard 與 Express workflow

貸款流程會平行查核資料，等待人工核准最長 72 小時，且稽核員需要完整 execution history。應選哪種 Step Functions workflow？

A. Express，因為所有 workflow 都應優先選最高吞吐
B. Lambda 持續執行並 sleep 72 小時
C. EventBridge Scheduler 單獨保存所有 branch state
D. Standard Workflow

**答案：D**

- **A：** 錯誤。Express 適合高量短流程，不適合多日 callback 與所述 durable audit history。
- **B：** 錯誤。Lambda 有執行時間限制，且 sleep 會浪費資源。
- **C：** 錯誤。Scheduler 能觸發時間事件，但不是保存完整多步 state machine。
- **D：** 正確。Standard 支援長執行、durable state、callback 與 execution history。

**事實查證：** [Standard and Express Workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)

### 練習題 2｜SAA｜Service integration patterns

Workflow 要提交 AWS Batch job，等 job 完成後再進下一步；另一個步驟要等外部人工系統回覆。正確配對是什麼？

A. Batch 使用 Run a Job (.sync)，人工系統使用 Wait for Callback with task token
B. 兩者都只使用 Request Response，因為 API 接受就代表工作完成
C. 兩者都用 Wait state 猜測完成時間
D. 在 Lambda 內輪詢兩者直到完成

**答案：A**

- **A：** 正確。.sync 追蹤支援的 job，task token 則讓外部 actor 明確完成 callback。
- **B：** 錯誤。Request Response 只代表 API request 已完成，不代表非同步 job 完成。
- **C：** 錯誤。Wait state 只讓 workflow 暫停指定時間，無法證明 Batch job 或人工系統已成功；它只適合明確的時間延遲，不是 completion signal。
- **D：** 錯誤。長時間 polling 增加程式與執行成本，並隱藏 orchestration state。

**事實查證：** [Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)、[Callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)

### 練習題 3｜SAA｜Payment retry safety

Payment Task 可能收到 throttling 或 validation error。哪兩項設計能避免重複扣款與無效重試？（選兩項）

A. 對 States.ALL 無限 retry
B. 只對暫時性 service/throttle errors 做 bounded backoff retry
C. 每次 retry 產生新的 payment operation ID
D. 讓 payment API 使用穩定 idempotency key
E. 把 validation error 當成網路 timeout

**答案：B、D**

- **A：** 錯誤。States.ALL 無限 retry 會把 validation、permission 或程式錯誤也持續重送，形成 retry storm，並可能重複執行非冪等付款。
- **B：** 正確。Retry 應只涵蓋可恢復的 service、throttle 或暫時網路錯誤，並以 MaxAttempts、backoff 與 workflow deadline 限制總負載。
- **C：** 錯誤。每次 retry 產生新 operation ID 會讓付款系統把同一 logical payment 視為新交易，破壞 idempotency 並造成重複扣款。
- **D：** 正確。Workflow durability 不等於 side effect exactly once，穩定 key 才能安全重放。
- **E：** 錯誤。Validation 通常需改變 request，而不是原樣重試。

**事實查證：** [Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)

### 練習題 4｜SAP｜Retry/Catch 規則順序

State 的 Catchers 先放 States.ALL，後面才放自訂 PaymentDeclined。會發生什麼問題？

A. 沒有問題，Step Functions 會自動挑最精確規則
B. Catch 一定在 Retry 前執行
C. 廣泛 matcher 先攔截錯誤，使後面的特定處理無法到達；States.ALL 應置後
D. States.ALL 只能匹配 timeout

**答案：C**

- **A：** 錯誤。Catchers 依陣列順序掃描並使用第一個匹配項；把 States.ALL 放最前面會吃掉後面的特定錯誤處理，因此廣泛 matcher 應放最後。
- **B：** 錯誤。若錯誤符合 retrier，Step Functions 先依 Retry 處理，耗盡後才進 Catch。
- **C：** 正確。Specific-before-general 才能保留業務錯誤的專用路徑。
- **D：** 錯誤。States.ALL 是廣泛 wildcard，但仍有文件所述例外與放置規則。

**事實查證：** [Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)

### 練習題 5｜SAA｜Parallel 與 Map

流程需對固定的信用、身分、制裁三項查核同時執行；之後另一步要處理 S3 中數十萬筆獨立 records。最佳組合是什麼？

A. 固定三項用 Parallel；大型 collection 評估 Map/Distributed Map 與 failure tolerance
B. 兩者都用 Choice，Choice 會平行執行
C. 一個 Lambda 建立無限制 threads
D. 在每項之間放 Wait state

**答案：A**

- **A：** 正確。Parallel 適合固定 branches，Map 類型處理 collection 並提供受控 concurrency。
- **B：** 錯誤。Choice 選路徑，不代表同時執行所有 branches。
- **C：** 錯誤。自製無界 fan-out 缺少 backpressure、history 與 failure policy。
- **D：** 錯誤。Wait state 只延遲後續 transition，不會建立 branches 或逐筆迭代；它適合節流或等待時間點，不適合固定或大量工作的平行處理。

**事實查證：** [Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)、[Using Map state in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/state-map.html)

### 練習題 6｜SAP｜Secure human approval

高額退款 workflow 會把含 task token 的人工核准連結寄給主管，等待最長 24 小時；核准結果必須可稽核且不能被轉寄者或重播請求濫用。哪兩項控制最重要？（選兩項）

A. 把 task token 完整寫入所有公開 application logs
B. 驗證 approver identity/authorization，並把決策綁定正確 request context
C. 只要 SNS 顯示 email delivered 就視為 approved
D. 設定 timeout/heartbeat 或逾期路徑，並防止 token replay、保存決策證據
E. 所有人共用同一永久 task token

**答案：B、D**

- **A：** 錯誤。Token 能完成等待中的 task，應視為敏感 capability。
- **B：** 正確。系統須驗證目前 approver 身分、角色與案件範圍；單純持有可轉寄連結，不應自動等於有權核准特定退款。
- **C：** 錯誤。Email delivery receipt 只證明郵件傳遞，不代表授權主管已檢視案件並作出不可否認的業務核准。
- **D：** 正確。Timeout 或 heartbeat 建立等待上限，一次性 token 與決策紀錄則避免 replay，並提供事後稽核及逾期復原路徑。
- **E：** 錯誤。Token 應與特定 task execution 綁定。

**事實查證：** [Callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)、[Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)

### 練習題 7｜SAP｜Saga compensation

庫存已保留、付款已完成，但建立物流失敗。Step Functions Catch 是否能自動 rollback 所有已提交服務？

A. 可以，Standard Workflow 等同跨服務 ACID transaction
B. 不可以；需明確呼叫可重試、冪等的 refund/release 等 semantic compensations
C. 可以，只要刪除 execution history
D. 不可以，所以應保持跨服務 database locks 72 小時

**答案：B**

- **A：** 錯誤。Workflow state durability 不會回滾外部已提交資料。
- **B：** 正確。Saga compensation 是新的業務操作，也可能失敗並需監控。
- **C：** 錯誤。刪除 history 不改變外部 side effects。
- **D：** 錯誤。長時間 distributed locks 不適合獨立服務與人工流程。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)

### 練習題 8｜SAP｜Workflow failure diagnosis

Execution 停在 callback Task 數小時，外部系統聲稱已呼叫 API。最有效的第一輪診斷是什麼？

A. 使用外部系統保存的 task token 立即重送 SendTaskSuccess，未先確認 execution 是否仍等待同一 token
B. 先延長 callback Task timeout 並 redrive execution，暫不檢查 token、API 回應與 IAM 拒絕
C. 檢查 execution history/logs、token 對應、SendTaskSuccess/Failure 權限、heartbeat/timeout 與外部回應
D. 啟動一個替代 execution 接管案件，讓原 execution 繼續等待到 timeout

**答案：C**

- **A：** 錯誤。若 token 已過期、屬於別的 execution 或先前 callback 已成功，盲目重送只會再次失敗；僅在確認 execution 仍等待且前次結果未被接受時才適合重試。
- **B：** 錯誤。延長 timeout 可用於已知外部工作確實需要更久的情境，但無法說明 callback 是否送出、token 是否相符或 SendTaskSuccess 是否被拒絕。
- **C：** 正確。這些證據能區分 callback 未送、token 錯誤、權限拒絕與逾時。
- **D：** 錯誤。替代 execution 只適合舊流程已安全終止且 side effects 可去重或補償時；並行保留兩條流程會造成重複核准或重複業務效果。

**事實查證：** [Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)、[Callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Execution role 與敏感資料

State machine 會呼叫限定的 Lambda、DynamoDB table 並記錄 logs。哪兩項安全設計正確？（選兩項）

A. Execution role 只允許實際使用的 actions/resources
B. 所有 state machine 一律 AdministratorAccess
C. 執行開始後完全使用 caller 權限，不需要 execution role
D. 把 database password 直接寫入 ASL Parameters
E. 避免在 state input/output/logs 傳遞 secrets 與巨大 documents，改傳 reference 並限制 log access

**答案：A、E**

- **A：** 正確。Service integrations 由 execution role 執行，應 least privilege。
- **B：** 錯誤。過寬權限擴大 workflow definition 或 input 被濫用的 blast radius。
- **C：** 錯誤。Execution role 是 workflow 呼叫 AWS services 的主要身份。
- **D：** 錯誤。Definition 與 history 可能暴露長期 credential。
- **E：** 正確。Reference pattern 降低 payload limits、敏感資料與 logging 風險。

**事實查證：** [Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)、[Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)

### 練習題 10｜SAP｜ASL 綜合審查

一個多日 Standard workflow 的 payment Task 對 States.ALL 重試 99 次，沒有 TimeoutSeconds；callback Task 沒有 timeout，compensation 也沒有 idempotency key。最正確的審查結論是什麼？

A. Standard 會自動保證每個外部 side effect exactly once
B. 只需改成 Express 即可
C. Succeed state 能證明所有外部資料已提交一次
D. 限制 transient retries、加入 task/callback timeout，並讓 payment 與 compensation 冪等且可觀測

**答案：D**

- **A：** 錯誤。Standard 的 workflow execution 語意不等於第三方付款 exactly once。
- **B：** 錯誤。Express 不適合多日 callback，且不修正 side-effect semantics。
- **C：** 錯誤。Succeed 只代表 state machine 走到該 state。
- **D：** 正確。限制 transient retries 與 task/callback timeout 可約束時間和負載；付款及補償的穩定 idempotency key 與觀測證據則避免重複業務效果。

**事實查證：** [Standard and Express Workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)、[Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)、[Callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Step Functions明確表達state machine；Standard適合durable wor…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「多步驟流程需要state、retry、timeout、branch與補償，不能只靠函式互相呼叫。」，所以「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」能直接滿足它；若constraint改成「EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」。替代方案「EventBridge適合事件routing；SQS適合工作buffer；它們可與workflow組合。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「多步驟流程需要state、retry、timeout、branch與補償，不能只靠函式互相呼叫。」，排除會導致「Lambda內手寫長時間sleep/polling，或retry非冪等步驟造成重複扣款。」的選項，再選「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Step Functions明確表達state machine；Standard適合durable workflow，Express適合高量短流程。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「make orchestration state explicit and inspectable」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 56 章　Retry、Backoff、Jitter 與 Timeout

分散式呼叫會暫時失敗，但無限制重試會把小故障放大成retry storm。

## 跟著一件工作在服務間流動：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：下游偶發429與timeout，client、service mesh與SDK都內建重試。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：分散式呼叫會暫時失敗，但無限制重試會把小故障放大成retry storm。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：重試像沒聽見店員回覆時再次下單；如果店家沒有訂單編號，就可能真的做出兩份餐點。 Idempotency key只是建立辨識基礎，還需要持久記錄、atomic update與合理的有效期限。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。AWS SDK retry behavior負責主要工作，Amazon API Gateway提醒我們答案不是永遠固定。本章會走向「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：下游偶發429與timeout，client、service mesh與SDK都內建重試。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[AWS SDK retry behavior]
          │ 以managed queue解耦producer與consumer的時間和容量。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Amazon API Gateway：提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。

失敗時先找：每一層各重試三次，五層組合成數百次下游request。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問AWS SDK retry behavior有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS SDK retry behavior和Amazon API Gateway並不是兩個任意的產品名稱。前者適合本章，是因為「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」直接回應了眼前的問題；後者描述的「Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每一層各重試三次，五層組合成數百次下游request。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「retries consume a shared failure budget」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS SDK retry behavior | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 下游偶發429與timeout，client、service mesh與SDK都內建重試。

1. 故事的起點：下游偶發429與timeout，client、service mesh與SDK都內建重試。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS SDK retry behavior負責「以managed queue解耦producer與consumer的時間和容量。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon API Gateway、AWS Lambda各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每一層各重試三次，五層組合成數百次下游request。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS SDK retry behavior

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：分散式呼叫會暫時失敗，但無限制重試會把小故障放大成retry storm。
- **具體例子／邊界：** 在「下游偶發429與timeout，client、service mesh與SDK都內建重試。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon API Gateway

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每一層各重試三次，五層組合成數百次下游request。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：retries consume a shared failure budget。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### backoff

每次retry前逐步增加等待，避免所有clients持續打滿失敗服務。

### jitter

在retry delay加入隨機性，避免大量clients在同一時刻同步重試。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS SDK retry behavior

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### Amazon API Gateway

- **功用：** 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
- **底層機制：** Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。
- **關鍵設定：** REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
- **選擇時機：** serverless API、公開/私有API、consumer治理與request transformation。
- **替換時機：** 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

## 考前與實作時再查：設定操作手冊

### AWS SDK retry behavior：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS SDK retry behavior依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS SDK retry behavior的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從AWS SDK retry behavior queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS SDK retry behavior的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS SDK retry behavior指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定AWS SDK retry behavior的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

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

1. AWS SDK retry behavior的責任：以managed queue解耦producer與consumer的時間和容量。
2. 底層機制：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
3. 第一個要看的設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
4. 選擇邏輯：每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。
5. 不要混淆：Amazon API Gateway的責任是「提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。」；它不會自動取代AWS SDK retry behavior。
6. 替換訊號：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
7. 最常見錯法：每一層各重試三次，五層組合成數百次下游request。
8. 可移植原則：retries consume a shared failure budget。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS SDK retry behavior | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 | serverless API、公開/私有API、consumer治理與request transformation。 | 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。 | 只有當題目條件明確改變時才可能合理。 | 每一層各重試三次，五層組合成數百次下游request。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。」之間做選擇。
- 認得常考設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Retryable error classification

Checkout client 會遇到 connection reset、429、偶發 503、400 validation error 與 403 AccessDenied。哪種 retry policy 最合理？

A. 僅對 transient connection、throttling 與合適 5xx 做 bounded retry；non-idempotent call 要有穩定 token
B. 所有 4xx 與 5xx 都原樣重試
C. 429 永遠不可重試
D. 付款 retry 每次都換新的 idempotency token

**答案：A**

- **A：** 正確。Connection reset、throttling 與部分 5xx 通常具暫時性；是否重試仍須同時考量 operation 冪等性、attempt 上限與 caller deadline。
- **B：** 錯誤。Validation/auth failure 通常需修正輸入或權限。
- **C：** 錯誤。429 通常代表目前超過服務速率或容量，不是永久性 payload 錯誤；依服務指引退避、加入 jitter 並降低 offered load 後通常可有限重試。
- **D：** 錯誤。新 token 會把同一 logical payment 變成新操作。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)、[Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)

### 練習題 2｜SAP｜End-to-end deadline budget

API 對使用者的總 deadline 是 3 秒，會呼叫兩個 downstream services。哪個 timeout 設計正確？

A. 每層都設 30 秒，避免過早 timeout
B. 從 3 秒總 budget 分配 connect/request timeout、有限 attempts 與上游收尾時間，並傳遞剩餘 deadline
C. 只設 request timeout，不需 connect/TLS timeout
D. 每次 retry 都重新取得完整 3 秒

**答案：B**

- **A：** 錯誤。下游 timeout 超過 caller deadline 會留下無用在途工作。
- **B：** 正確。Deadline budgeting 防止內層超時與重試超過使用者可等待時間。
- **C：** 錯誤。Request timeout 只涵蓋部分等待；DNS、TCP connect、TLS handshake 與 retry backoff 都會消耗同一端到端 budget，必須一起納入。
- **D：** 錯誤。重啟 deadline 可讓總 latency 無界增長。

**事實查證：** [REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)

### 練習題 3｜SAA｜Backoff 與 jitter

數十萬 clients 在相同時間收到 503。哪兩項最能避免同步 retry storm？（選兩項）

A. 立即連續 retry 三次
B. 使用 capped exponential backoff
C. 所有 clients 使用完全相同 deterministic schedule
D. 固定每秒 retry 且無截止
E. 加入 jitter 並限制 attempts/總 deadline

**答案：B、E**

- **A：** 錯誤。所有 clients 立即連續 retry 會在服務最脆弱時疊加原始流量，造成 synchronized retry storm，並延長服務恢復時間。
- **B：** 正確。Capped exponential backoff 逐次拉長等待並限制最大間隔，能降低 retry rate；仍須搭配 jitter 與總 deadline 避免同步。
- **C：** 錯誤。即使採 exponential backoff，所有 clients 使用相同 deterministic schedule 仍會在相同時間醒來，形成週期性流量波峰。
- **D：** 錯誤。無截止與固定間隔會讓 clients 在服務尚未恢復時持續施壓。
- **E：** 正確。Jitter 分散 clients，bounded budget 限制總 amplification。

**事實查證：** [Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)

### 練習題 4｜SAP｜Retry ownership

Client、API、service mesh、SDK 和 database driver 各自設定 3 次 attempts；一次 user request 最壞會放大成大量 database calls。最佳修正是什麼？

A. 保留所有 retries，因為每層只有三次
B. 只允許 database 永久重試
C. 隱藏 attempt metrics，避免告警
D. 指定有語意知識的一層負責 bounded retry，縮減其他層並計算總 amplification

**答案：D**

- **A：** 錯誤。多層 retries 會相乘，把單一 user request 放大成大量下游 calls。
- **B：** 錯誤。Database layer 不一定知道整體 operation 是否可安全重放。
- **C：** 錯誤。隱藏 attempt metrics 會讓團隊只看到 user request rate，卻看不到多層 retries 的放大倍數；應以 correlation ID 與 per-layer attempts 量測。
- **D：** 正確。集中或嚴格界定 retry ownership 才能管理 failure budget。

**事實查證：** [REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 5｜SAP｜SDK standard 與 adaptive mode

一個 process 以同一 AWS SDK client 存取許多彼此獨立的 DynamoDB tables。團隊想啟用 adaptive retry，又不希望某一張表被 throttling 時拖慢其他表。哪項評估與處置最正確？

A. 保留單一 shared client 即可；adaptive 只延遲 retry attempt，永遠不會延遲第一次請求
B. 改用 standard mode 可避免跨表的 adaptive rate-limit coupling，但也不再取得 adaptive 對初次請求速率的動態調節
C. 若要 adaptive，應按 DynamoDB Region 與 table 等 throttling scope 隔離 clients；否則一張表的 throttle 可能延遲其他表
D. 為每個 API operation 建立新 client；如此一定能避免 coupling，且 connection pooling 成本可忽略

**答案：C**

- **A：** 錯誤。Adaptive mode 的 request-rate token bucket 可能延遲第一次 attempt；共用 client 時，某個 throttled resource 可能影響同 client 的其他請求。
- **B：** 錯誤。Standard mode 確實是不願按資源隔離 clients 時的合理替代，但題目要求啟用 adaptive；它不能滿足動態限制初次請求速率的需求。
- **C：** 正確。Adaptive 假設 client 對應服務實際 throttling 維度；DynamoDB 應至少按 Region 與 table 隔離，避免無關資源共享 request-rate token bucket。
- **D：** 錯誤。按 throttling scope 重用 client 才能兼顧隔離與連線池；每次 operation 新建 client 會增加連線與資源成本，也不是必要條件。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)

### 練習題 6｜SAA｜SDK retry mode 與 server-directed backoff

團隊同時評估 AWS SDK 的 standard/adaptive retry mode，以及 AWS SDK for Python v1 的節流回應；其中一個 response 帶有 x-amz-retry-after。哪兩項敘述正確？（選兩項）

A. Adaptive mode 適合讓所有不同 throttling resources 共用同一 client，並保證第一次 request 永不被延遲
B. 一般 workload 優先使用 standard；若採 adaptive，應按服務的 throttling resource 維度隔離 clients，並接受它可能延遲第一次 attempt
C. AWS SDK for Python v1 把一般 HTTP Retry-After 與 x-amz-retry-after 都解讀為秒數，且任何字串值都有效
D. AWS SDK for Python v1 的 standard strategy 將 x-amz-retry-after 解讀為毫秒整數，無效值會忽略，並把有效提示納入受上限約束的 backoff 計算
E. 提高 read timeout 就等同遵守 server-directed retry timing，因此不必限制 attempts、總 deadline 或 offered load

**答案：B、D**

- **A：** 錯誤。Adaptive 的 request-rate token bucket 可能延遲第一次 attempt；若無關資源共用 client，一個 resource 的 throttling 還可能拖慢其他請求。
- **B：** 正確。Standard 適合多數 workload；adaptive 需要依 Region、table、bucket 等實際 throttling 維度建立 clients，否則會產生非預期的跨資源耦合。
- **C：** 錯誤。該 SDK 明確忽略一般 Retry-After header；x-amz-retry-after 必須是表示毫秒的非負整數，負值或無效字串不參與計算。
- **D：** 正確。有效的 x-amz-retry-after 會與計算出的 backoff 比較後納入延遲，並受文件所述上限控制；這是 server-directed timing，不是 request timeout。
- **E：** 錯誤。Read timeout 控制單次 request 等待，不能取代 retry delay、bounded attempts、caller deadline 或 admission control；忽略這些限制仍會造成 retry amplification。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[AWS SDK retry behavior — choosing a retry mode](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html#choosing-a-retry-mode)、[AWS SDK for Python v1 retries — backoff header](https://docs.aws.amazon.com/sdk-for-python/v1/guide/config-retries.html#backoff-header)

### 練習題 7｜SAA｜Queue-based retry

產生縮圖失敗時不必立即回覆完成，工作可在數分鐘後重試。哪個設計最適合？

A. 讓同步 request 永久等待
B. 用 retention 決定每次 retry 間隔
C. 送入 SQS，配置 visibility/redrive/DLQ、最大工作年齡與冪等 consumer
D. 讓 poison message 無限 redrive

**答案：C**

- **A：** 錯誤。讓同步 request 持續等待會占住 connection、thread 與 caller deadline；只有工作必須立即完成且延遲可控時，才適合維持同步契約。
- **B：** 錯誤。Retention 是保存上限，不是 retry schedule。
- **C：** 正確。Queue 將 immediate retry 轉成受控 eventual completion。
- **D：** 錯誤。Poison message 無限 redrive 會反覆消耗 worker 與下游容量，並阻礙健康工作；應設定最大接收次數、DLQ、告警與修復後受控重送。

**事實查證：** [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

### 練習題 8｜SAP｜Circuit breaker 與 retry

Recommendation dependency 持續故障。哪個組合能避免 retries 成為第二個放大器？

A. Open breaker 時仍進行完整 retries
B. 以 breaker 讓 non-idempotent call 自動安全
C. 每次 process restart 都無條件視為健康
D. 短暫故障用 bounded retries；持續失敗時 breaker open，half-open 少量 probe 並提供安全 fallback

**答案：D**

- **A：** 錯誤。Breaker open 的目的就是在持續故障時快速拒絕大部分呼叫；若仍做完整 retries，會繞過隔離效果並繼續壓迫 dependency。
- **B：** 錯誤。Breaker 不改變 operation semantics。
- **C：** 錯誤。這可能在 fleet restart 時形成 probe storm。
- **D：** 正確。Bounded retries 處理少量暫時錯誤，breaker 則隔離持續故障；half-open 限量探測與安全 fallback 防止恢復時再次形成流量尖峰。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Retry amplification diagnosis

部署後 user request rate 不變，但 downstream TPS 增加四倍。哪兩項證據最能驗證 retry amplification？（選兩項）

A. 把 original requests 與 per-layer attempts 以 correlation ID 對照
B. 只看 successful user responses
C. 直接把 max attempts 再提高
D. 假定所有新增 TPS 都來自新使用者
E. 檢查 timeout/throttle、retry quota、attempt count 與 latency percentiles

**答案：A、E**

- **A：** 正確。Original-to-attempt ratio 直接量化放大倍數與來源層。
- **B：** 錯誤。Successful user responses 只呈現最終結果，無法揭露中間失敗、timeout 與 retry attempts，因此不能計算 original-to-attempt amplification。
- **C：** 錯誤。未定位重試來源前提高 max attempts 會增加 downstream TPS，可能把暫時性問題推成容量故障；應先量測再調整 budget。
- **D：** 錯誤。題目已指出 business request rate 沒有變化，因此新增 TPS 更可能來自內部 attempts；仍須用 correlation 與 attempt metrics 驗證。
- **E：** 正確。這些 signals 能連結錯誤類型、重試行為與 downstream load。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 10｜SAP｜SDK retry configuration review

Checkout 必須在 2 秒內回覆付款授權結果，但 SDK 設為 max_attempts=10、read_timeout=5 秒，且 CreatePayment 每次自動產生新 token。審查結論是什麼？

A. 保留十次 attempts，只把每次 read_timeout 降到 1 秒；其餘 backoff 不需納入總 deadline
B. 改用 adaptive retry 即可自動保證整個付款呼叫在 2 秒內結束
C. 應從 caller deadline 重設 connect/read timeout 與 attempts，並重用同一 logical payment token、記錄 attempts
D. 把付款改送 SQS 並立即回成功；不需把 API contract 改為 pending 或提供查詢狀態

**答案：C**

- **A：** 錯誤。單次 timeout 降低仍未計算最多十次 attempt、connect 時間與 backoff；只有完整 worst-case 小於 caller deadline 時才安全。
- **B：** 錯誤。Adaptive mode 可調節重試與初次請求速率，但不承諾符合應用的 2 秒 deadline；呼叫端仍須配置 timeout 與 attempt budget。
- **C：** 正確。Worst-case duration 必須落在 deadline 內，token 需代表同一 logical operation。
- **D：** 錯誤。SQS 適合業務允許 eventual completion 的工作；題目要求立即付款結果，若改成 queue 必須明確回 pending、提供狀態與 reconciliation，而不能先宣稱成功。

**事實查證：** [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)、[Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「分散式呼叫會暫時失敗，但無限制重試會把小故障放大成retry storm。」，所以「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」能直接滿足它；若constraint改成「Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」。替代方案「Circuit breaker可在持續故障時快速失敗；queue可把立即重試轉成受控重排程。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每一層各重試三次，五層組合成數百次下游request。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「分散式呼叫會暫時失敗，但無限制重試會把小故障放大成retry storm。」，排除會導致「每一層各重試三次，五層組合成數百次下游request。」的選項，再選「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「每次呼叫設timeout，只重試可恢復且冪等操作，使用exponential backoff、jitter與總deadline。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「retries consume a shared failure budget」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 57 章　Idempotency、Deduplication 與 Exactly-once Illusion

Client看不到response時無法判斷server是否已提交，重試可能重複side effect。

## 跟著一件工作在服務間流動：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：付款已完成但response丟失，client在timeout後重送相同request。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：Client看不到response時無法判斷server是否已提交，重試可能重複side effect。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：重試像沒聽見店員回覆時再次下單；如果店家沒有訂單編號，就可能真的做出兩份餐點。 但請同時記住它的邊界：Idempotency key只是建立辨識基礎，還需要持久記錄、atomic update與合理的有效期限。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon DynamoDB，對照角色是Amazon SQS FIFO。我們選擇「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：付款已完成但response丟失，client在timeout後重送相同request。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[Amazon DynamoDB]
          │ 提供managed key-value/document database與單位毫秒scale。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Amazon SQS FIFO：在message group內提供嚴格順序與deduplication能力。
  · AWS Lambda Powertools：按事件執行短生命函式，自動管理capacity與runtime基礎設施。

失敗時先找：用message ID去重卻在重新發布時產生新ID，付款因此重複。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Amazon DynamoDB有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon DynamoDB和Amazon SQS FIFO並不是兩個任意的產品名稱。前者適合本章，是因為「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」直接回應了眼前的問題；後者描述的「FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：用message ID去重卻在重新發布時產生新ID，付款因此重複。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「exactly-once effects are built from at-least-once delivery plus idempotency」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |
| Amazon SQS FIFO | 在message group內提供嚴格順序與deduplication能力。 | MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。 |
| AWS Lambda Powertools | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 付款已完成但response丟失，client在timeout後重送相同request。

1. 故事的起點：付款已完成但response丟失，client在timeout後重送相同request。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon DynamoDB負責「提供managed key-value/document database與單位毫秒scale。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon SQS FIFO、AWS Lambda Powertools各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「用message ID去重卻在重新發布時產生新ID，付款因此重複。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon DynamoDB

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Client看不到response時無法判斷server是否已提交，重試可能重複side effect。
- **具體例子／邊界：** 在「付款已完成但response丟失，client在timeout後重送相同request。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon SQS FIFO

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：用message ID去重卻在重新發布時產生新ID，付款因此重複。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：exactly-once effects are built from at-least-once delivery plus idempotency。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### idempotency

同一operation重複執行，business effect仍只發生一次或得到等價結果。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon DynamoDB

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

### Amazon SQS FIFO

- **功用：** 在message group內提供嚴格順序與deduplication能力。
- **底層機制：** MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。
- **關鍵設定：** MessageGroupId、MessageDeduplicationId/content-based dedup、high-throughput mode與visibility。
- **選擇時機：** 同一business entity必須有序，且可用多groups平行處理。
- **替換時機：** 全域單一group會限制throughput；business side effect仍需idempotency。

### AWS Lambda Powertools

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

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

### Amazon SQS FIFO：逐項設定說明

#### `MessageGroupId`

- **控制什麼：** `MessageGroupId`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS FIFO依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `MessageDeduplicationId/content-based dedup`

- **控制什麼：** `MessageDeduplicationId/content-based dedup`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS FIFO依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `high-throughput mode`

- **控制什麼：** `high-throughput mode`選擇Amazon SQS FIFO的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `visibility`

- **控制什麼：** `visibility`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「同一business entity必須有序，且可用多groups平行處理。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS FIFO依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

### AWS Lambda Powertools：逐項設定說明

#### `memory/CPU`

- **控制什麼：** `memory/CPU`設定AWS Lambda Powertools的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Lambda Powertools的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `reserved/provisioned concurrency`

- **控制什麼：** `reserved/provisioned concurrency`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `event source mapping`

- **控制什麼：** `event source mapping`指定AWS Lambda Powertools讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `DLQ/destination`

- **控制什麼：** `DLQ/destination`指定AWS Lambda Powertools讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda Powertools的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ephemeral storage`

- **控制什麼：** `ephemeral storage`選擇AWS Lambda Powertools的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

## 讀到這裡，請用自己的話說一次

1. Amazon DynamoDB的責任：提供managed key-value/document database與單位毫秒scale。
2. 底層機制：Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
3. 第一個要看的設定：PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
4. 選擇邏輯：以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。
5. 不要混淆：Amazon SQS FIFO的責任是「在message group內提供嚴格順序與deduplication能力。」；它不會自動取代Amazon DynamoDB。
6. 替換訊號：ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。
7. 最常見錯法：用message ID去重卻在重新發布時產生新ID，付款因此重複。
8. 可移植原則：exactly-once effects are built from at-least-once delivery plus idempotency。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon DynamoDB | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| Amazon SQS FIFO | 在message group內提供嚴格順序與deduplication能力。 | MessageGroupId定義ordering lane；deduplication ID在有限窗口內抑制重複enqueue。 | 同一business entity必須有序，且可用多groups平行處理。 | 全域單一group會限制throughput；business side effect仍需idempotency。 |
| AWS Lambda Powertools | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。 | 只有當題目條件明確改變時才可能合理。 | 用message ID去重卻在重新發布時產生新ID，付款因此重複。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。」之間做選擇。
- 認得常考設定：PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Stable idempotency key

Client 在 CreatePayment timeout 後重送。哪個 idempotency key 設計最安全？

A. 每次 attempt 產生新 UUID
B. 使用每個 proxy hop 產生的 request ID
C. 使用目前 timestamp
D. Client 對同一 logical payment 重用 key，server 以 tenant/operation scope 並驗證 payload 一致性

**答案：D**

- **A：** 錯誤。每次 attempt 產生新 UUID 只識別傳輸嘗試，server 無法把 timeout 後的重送連回同一 logical payment，因此可能再次扣款。
- **B：** 錯誤。Hop ID 代表傳輸 attempt，不代表 business operation。
- **C：** 錯誤。Timestamp 會隨 retry 改變，無法穩定代表同一 business operation；在高併發或時鐘精度不足時也可能碰撞不同付款。
- **D：** 正確。穩定且 scoped key 才能辨識同一操作，payload hash 可阻止 key 被誤用。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

### 練習題 2｜SAA｜Atomic operation claim

兩個相同 payment requests 同時到達。如何確保只有一個 caller 執行 charge？

A. 先 eventually-consistent read，再各自 unconditional put
B. charge 完成後才寫 idempotency record
C. 用 DynamoDB conditional put 原子建立 IN_PROGRESS；失敗的 caller 依狀態等待或 replay
D. 以 process memory set 去重所有 instances

**答案：C**

- **A：** 錯誤。Read-then-write 有 race window。
- **B：** 錯誤。先執行 charge、事後才寫 idempotency record 仍有競爭窗口；兩個 callers 都可能在任何一方留下 durable claim 前完成扣款。
- **C：** 正確。Conditional expression 將 claim 變成單一原子決策。
- **D：** 錯誤。Instance-local memory 不共享且重啟會遺失。

**事實查證：** [DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)

### 練習題 3｜SAA｜Result replay

第一次 payment 已成功但 response 遺失。相同 key 再到達時，哪兩項行為正確？（選兩項）

A. 看到 duplicate 一律回 generic error
B. 再次 charge，因為 client 沒看到 response
C. 持久化 COMPLETED 狀態與 payment/result reference
D. 成功後立即刪除 idempotency record
E. 在 key 與 payload 相容時回傳相同 logical outcome，不重做 side effect

**答案：C、E**

- **A：** 錯誤。對 duplicate 一律回 generic error 會讓 caller 無法判斷原付款是否成功，可能觸發人工重試或建立新交易，擴大不確定性。
- **B：** 錯誤。Response loss 不代表 side effect 未提交。
- **C：** 正確。持久化 COMPLETED 與原 payment/result reference，才能讓後續相同 key 重播同一 logical outcome，而不再次執行付款 side effect。
- **D：** 錯誤。成功後立即刪除 idempotency record 會在 response 遺失或延遲 retry 到達時失去既有 outcome，讓 server 再次執行付款。
- **E：** 正確。Idempotency 的目的就是讓多次 attempts 對應同一 business result。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)

### 練習題 4｜SAP｜Stale IN_PROGRESS recovery

Worker charge 後 crash，record 留在 IN_PROGRESS。簡單刪除 record 有何風險，應如何處理？

A. 沒有風險，IN_PROGRESS 證明 charge 未發生
B. 建立 bounded lease/expiry，並向 payment system reconcile 後才決定 replay 或標記完成
C. 永遠等待，不需告警
D. 把所有 IN_PROGRESS 定時改為 COMPLETED

**答案：B**

- **A：** 錯誤。Crash 可能發生在 external commit 後。
- **B：** 正確。不確定 outcome 必須查 authoritative side effect，不能靠本地狀態猜測。
- **C：** 錯誤。永久卡住會讓合法 request 無法完成，也沒有可操作的 recovery deadline。
- **D：** 錯誤。把所有逾期 IN_PROGRESS 直接改成 COMPLETED 會把未真正 charge 的交易偽裝成成功；必須先向 authoritative payment system reconcile outcome。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 5｜SAA｜FIFO dedup 與 business idempotency

團隊宣稱 SQS FIFO 已保證 payment exactly once，因此 consumer 不需 idempotency。最正確的反駁是什麼？

A. FIFO dedup 只抑制其窗口/範圍內的重複 sends；redelivery、晚到重發及其他 channel 仍可能重做 side effect
B. FIFO 完全不提供 ordering
C. Standard queue 才提供永久 dedup
D. 提高 retention 就能取得 exactly-once charge

**答案：A**

- **A：** 正確。Transport dedup 不等於端到端 external effect exactly once。
- **B：** 錯誤。FIFO 提供 message-group ordering。
- **C：** 錯誤。Standard 不提供 FIFO dedup contract。
- **D：** 錯誤。Retention 與 deduplication 是不同功能。

**事實查證：** [Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

### 練習題 6｜SAA｜Idempotent SQS Lambda consumer

Lambda 消費 SQS order events。哪兩項能在 crash/retry 下保護資料？（選兩項）

A. 使用 Lambda invocation ID 作永久 business identity
B. 用 stable order-event identity 做 conditional claim/write
C. 開始處理前把整批標成成功
D. durable side effect 完成後才回報成功，並使用 partial batch failures
E. 假設 visibility timeout 消除 duplicates

**答案：B、D**

- **A：** 錯誤。Lambda invocation ID 隨每次 delivery attempt 改變，不能代表穩定的 order event；用它去重會讓同一 business event 每次都看似全新。
- **B：** 正確。Business identity 跨 delivery attempts 保持穩定。
- **C：** 錯誤。在 durable side effect 完成前把整批回報成功，Lambda 或 worker 隨後 crash 時，SQS 不會再投遞尚未完成的 records，造成資料遺失。
- **D：** 正確。先 commit 再 ack，加上 partial response 可安全縮小 retry 範圍。
- **E：** 錯誤。Visibility 到期正是可能 redelivery 的來源。

**事實查證：** [Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)、[AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)

### 練習題 7｜SAP｜DynamoDB transaction boundary

Idempotency record 與 order ledger 都在 DynamoDB，必須一起成功；付款則在外部 processor。哪個設計正確？

A. DynamoDB transaction 可原子更新兩個 DynamoDB items；外部付款仍需 idempotency/reconciliation
B. Transaction 能一起 commit 第三方 payment
C. 用兩個無關 Lambda 分別寫，效果等同 transaction
D. DynamoDB Streams 可阻止初始 duplicate charge

**答案：A**

- **A：** 正確。TransactWriteItems 的原子範圍是受支援的 DynamoDB items，不包含外部系統。
- **B：** 錯誤。Managed database transaction 無法跨第三方 API。
- **C：** 錯誤。分開 async writes 有 partial failure gap。
- **D：** 錯誤。Streams 發生在 table change 後，且也需處理重複。

**事實查證：** [DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)、[DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)

### 練習題 8｜SAP｜Idempotency TTL

合法 retries 最長可能在 48 小時後到達。團隊把 idempotency TTL 設為 5 分鐘，並期待 DynamoDB 在秒級準時刪除。問題是什麼？

A. 把 TTL 精確設為 48 小時，並假設 expiry 時刻一到 record 就立刻消失
B. 完全移除 TTL、永久保留所有 idempotency records，不評估資料成長與法規需求
C. 只把 dedup key 放在 48 小時 TTL 的 cache；cache miss 時直接重做付款
D. Retention 太短會讓晚 retry 重做；TTL deletion 非即時，application 仍應判斷 expiry

**答案：D**

- **A：** 錯誤。48 小時可作 retention 基線，但 DynamoDB TTL 是背景刪除，通常在過期後數日內完成；應用仍須讀取 expiry 並按規則判斷。
- **B：** 錯誤。永久保存可降低晚 retry 重做風險，卻造成無界儲存、隱私與清理成本；只有法規要求永久稽核且另有生命週期治理時才合理。
- **C：** 錯誤。Cache 可減少熱門 duplicate 的讀取成本，但 eviction、故障或重啟後會遺失去重證據；付款 identity 仍需要 durable authority。
- **D：** 正確。Record retention 應涵蓋 replay horizon，且不能把非同步刪除當精準 scheduler。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[Using time to live in DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Duplicate charge diagnosis

改用 FIFO 後仍出現 duplicate charges。哪兩項最值得追查？（選兩項）

A. Producer 是否對同一 logical operation 重用 dedup/idempotency identity
B. 把 FIFO throughput mode 調高
C. 把 message retention 調高
D. 改回 Standard queue
E. Visibility/redelivery、consumer retries，以及 charge commit 與 idempotency record 的先後邊界

**答案：A、E**

- **A：** 正確。Identity 改變會讓 queue 與 application 都無法認出 duplicate。
- **B：** 錯誤。Throughput mode 不解決 side-effect identity。
- **C：** 錯誤。Message retention 只決定 SQS 保存未刪除訊息的期限，不會辨識 logical payment，也無法阻止 consumer 在 redelivery 時再次 charge。
- **D：** 錯誤。Standard 只會弱化 ordering/dedup guarantees。
- **E：** 正確。Crash window 與 acknowledgment uncertainty 是 duplicate effect 的核心來源。

**事實查證：** [Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)、[AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 10｜SAP｜Idempotency state machine review

一個 payment API 必須承受 concurrent duplicate requests、charge 後 crash、48 小時內的晚到 retry，並對成功重送回傳同一結果。哪個 state machine 最完整？

A. 收到 request 後 charge，成功才記 key
B. 每次 attempt 由 server 產生新 key
C. 只用短期 process cache SET
D. stable scoped key+payload hash；conditional IN_PROGRESS claim；lease/reconcile；COMPLETED result replay；合理 expiry 與 metrics

**答案：D**

- **A：** 錯誤。Crash-before-record 會重複 side effect。
- **B：** 錯誤。每次 attempt 使用新 key，server 就無法辨識它們其實是同一 logical operation。
- **C：** 錯誤。Cache-only 需先證明 durability/atomicity，且重啟可能遺失。
- **D：** 正確。它涵蓋 concurrency、crash uncertainty、response replay、expiry 與 operations。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)、[DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以idempotency key保存operation outcome，consumer以business…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Client看不到response時無法判斷server是否已提交，重試可能重複side effect。」，所以「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」能直接滿足它；若constraint改成「FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」。替代方案「FIFO deduplication有時間與範圍邊界，不能取代業務層idempotency。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「用message ID去重卻在重新發布時產生新ID，付款因此重複。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Client看不到response時無法判斷server是否已提交，重試可能重複side effect。」，排除會導致「用message ID去重卻在重新發布時產生新ID，付款因此重複。」的選項，再選「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以idempotency key保存operation outcome，consumer以business identity去重並讓寫入可重放。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「exactly-once effects are built from at-least-once delivery plus idempotency」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 58 章　Saga、Transactional Outbox 與 Eventual Consistency

跨服務無法用單一ACID transaction同時更新database與message broker。

## 跟著一件工作在服務間流動：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：訂單需扣庫存、付款、建立物流，任何一步可能失敗且各服務有自己的database。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：跨服務無法用單一ACID transaction同時更新database與message broker。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把分散式整合想成餐廳出單：收銀台不必站著等每個廚房完成，但每張單都要能追蹤、重做與防重複。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Step Functions如何接手工作，再看Amazon EventBridge何時更合適，最後用設定與考題驗證「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：訂單需扣庫存、付款、建立物流，任何一步可能失敗且各服務有自己的database。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[AWS Step Functions]
          │ 以可視化state machine編排多步驟、retry、branch、parallel與human workfl…
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Amazon EventBridge：以event bus路由AWS、SaaS與custom events到targets。
  · Amazon DynamoDB Streams：提供managed key-value/document database與單位毫秒scale。

失敗時先找：先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問AWS Step Functions有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Step Functions和Amazon EventBridge並不是兩個任意的產品名稱。前者適合本章，是因為「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」直接回應了眼前的問題；後者描述的「Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「make state transition and event publication one durable decision」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 |
| Amazon DynamoDB Streams | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 |

## 把全圖套進一個具體案例

**場景：** 訂單需扣庫存、付款、建立物流，任何一步可能失敗且各服務有自己的database。

1. 故事的起點：訂單需扣庫存、付款、建立物流，任何一步可能失敗且各服務有自己的database。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Step Functions負責「以可視化state machine編排多步驟、retry、branch、parallel與human workflow。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EventBridge、Amazon DynamoDB Streams各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Step Functions

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：跨服務無法用單一ACID transaction同時更新database與message broker。
- **具體例子／邊界：** 在「訂單需扣庫存、付款、建立物流，任何一步可能失敗且各服務有自己的database。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EventBridge

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：make state transition and event publication one durable decision。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### eventual consistency

更新後不同副本可能暫時看到舊值，但在沒有新更新時最終收斂；application必須容忍stale reads與重複event。

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### transaction

一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### stream

有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

### Amazon EventBridge

- **功用：** 以event bus路由AWS、SaaS與custom events到targets。
- **底層機制：** Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。
- **關鍵設定：** event buses、rules/patterns、targets、input transformer、archive/replay、DLQ與resource policy。
- **選擇時機：** domain events、cross-account integration、content-based routing與scheduler。
- **替換時機：** 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。

### Amazon DynamoDB Streams

- **功用：** 提供managed key-value/document database與單位毫秒scale。
- **底層機制：** Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。
- **關鍵設定：** PK/SK、on-demand/provisioned、RCU/WCU、GSI/LSI、consistency、TTL、Streams、PITR與transactions。
- **選擇時機：** 已知key-based access patterns、極高scale、serverless與低營運需求。
- **替換時機：** ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。

## 考前與實作時再查：設定操作手冊

### AWS Step Functions：逐項設定說明

#### `Standard/Express`

- **控制什麼：** `Standard/Express`選擇AWS Step Functions的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `Task/Choice/Map/Parallel/Wait`

- **控制什麼：** `Task/Choice/Map/Parallel/Wait`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Step Functions的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `Retry/Catch`

- **控制什麼：** `Retry/Catch`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `timeouts`

- **控制什麼：** `timeouts`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Step Functions的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `callback token`

- **控制什麼：** `callback token`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** AWS Step Functions需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

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

### Amazon DynamoDB Streams：逐項設定說明

#### `PK/SK`

- **控制什麼：** `PK/SK`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon DynamoDB Streams的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `on-demand/provisioned`

- **控制什麼：** `on-demand/provisioned`決定Amazon DynamoDB Streams如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `RCU/WCU`

- **控制什麼：** `RCU/WCU`決定Amazon DynamoDB Streams如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。
- **何時需要：** 新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。
- **怎麼設定／驗證：** 設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。
- **常見錯法：** 總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。

#### `GSI/LSI`

- **控制什麼：** `GSI/LSI`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon DynamoDB Streams的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `consistency`

- **控制什麼：** `consistency`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Amazon DynamoDB Streams的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

#### `TTL`

- **控制什麼：** `TTL`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon DynamoDB Streams的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `Streams`

- **控制什麼：** `Streams`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。
- **何時需要：** 需要從Amazon DynamoDB Streams持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。
- **怎麼設定／驗證：** 啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。
- **常見錯法：** Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。

#### `PITR`

- **控制什麼：** `PITR`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「已知key-based access patterns、極高scale、serverless與低營運需求。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon DynamoDB Streams依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `transactions`

- **控制什麼：** `transactions`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。
- **何時需要：** Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。
- **怎麼設定／驗證：** 記錄Amazon DynamoDB Streams的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。
- **常見錯法：** 把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。

## 讀到這裡，請用自己的話說一次

1. AWS Step Functions的責任：以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
2. 底層機制：Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
3. 第一個要看的設定：Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
4. 選擇邏輯：本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。
5. 不要混淆：Amazon EventBridge的責任是「以event bus路由AWS、SaaS與custom events到targets。」；它不會自動取代AWS Step Functions。
6. 替換訊號：純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。
7. 最常見錯法：先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。
8. 可移植原則：make state transition and event publication one durable decision。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| Amazon EventBridge | 以event bus路由AWS、SaaS與custom events到targets。 | Rule用JSON event pattern匹配facts並傳給targets；支援archive/replay、schema與cross-account buses。 | domain events、cross-account integration、content-based routing與scheduler。 | 需要durable work queue/backpressure用SQS；高吞吐replay stream用Kinesis/MSK。 |
| Amazon DynamoDB Streams | 提供managed key-value/document database與單位毫秒scale。 | Partition key hash決定physical partition；sort key維持同partition內排序；capacity與hot key受distribution影響。 | 已知key-based access patterns、極高scale、serverless與低營運需求。 | ad hoc joins/複雜transaction/reporting優先relational；不要用Scan補救錯誤key design。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。 | 只有當題目條件明確改變時才可能合理。 | 先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。」之間做選擇。
- 認得常考設定：Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAP｜Transactional outbox invariant

Outbox publisher 已成功把 OrderConfirmed 交給 EventBridge bus，但在把 outbox row 標記為 sent 前 crash；重啟後同一 row 會再次發布。哪個設計最能防止重複發布造成第二次扣庫存？

A. 為 outbox row 保留穩定 event_id；publisher 可安全重送同一 identity，consumer 以 durable dedup 或 conditional state transition 冪等套用
B. 在呼叫 PutEvents 前先把 row 標成 sent，避免重啟後再次看到它
C. 每次 publisher attempt 產生新的 event_id，讓 EventBridge 能分辨每次傳送
D. 依賴 EventBridge classic rule delivery 自動把所有重複發布轉成 exactly-once side effect

**答案：A**

- **A：** 正確。Bus acceptance 與本地 sent 標記無法原子提交，因此重複發布是可預期的；穩定 identity 與 consumer 冪等把多次 delivery 收斂成一次業務效果。
- **B：** 錯誤。先標 sent 可避免 duplicate，卻在 PutEvents 失敗或 process 隨後 crash 時造成永久漏發；只有 durable handoff 已完成後才能更新進度。
- **C：** 錯誤。每次產生新 identity 會讓 downstream 無法判定這是同一 logical event，反而把 publisher retry 變成兩個合法庫存扣減。
- **D：** 錯誤。Classic EventBridge rule delivery 不替外部 side effect 提供全域 exactly-once；即使 transport 有 dedup 範圍，consumer 仍須保護超窗或跨路徑重複。

**事實查證：** [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)、[PutEvents API reference](https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_PutEvents.html)

### 練習題 2｜SAP｜Outbox record schema

Order service 的 outbox publisher 可能重試，consumer 需要按同一 order 的版本處理，團隊也要追蹤尚未發布的資料。哪個 outbox schema 最能支援 dedup、ordering、schema evolution 與營運追蹤？

A. 只有 free-form payload
B. 只有 publication timestamp
C. 每個 aggregate 只保留一列並覆寫舊事件
D. immutable event_id、aggregate_id/sequence、type/version、payload/reference、created_at 與 publication/checkpoint 狀態

**答案：D**

- **A：** 錯誤。只有 free-form payload 缺少 immutable event identity、schema version、aggregate sequence 與 publication state，publisher 和 consumer 都難以安全重放或診斷。
- **B：** 錯誤。Timestamp 不能可靠代表唯一 identity 或跨 host ordering。
- **C：** 錯誤。每個 aggregate 只保留一列並覆寫舊事件，會遺失中間 transitions 與稽核歷史；它只適合作目前狀態快照，不是完整 outbox log。
- **D：** 正確。這些欄位讓 publisher 與 consumers 能重放、去重及診斷。

**事實查證：** [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

### 練習題 3｜SAP｜DynamoDB Streams outbox publication

團隊以 DynamoDB transaction 寫 order 與 outbox item，再由 Streams Lambda 發布事件。哪兩項仍然必要？（選兩項）

A. Publish 前立即刪除 outbox evidence
B. 以 stable event ID 發布並讓 consumer 冪等
C. 假設 Streams 保證 downstream side effect exactly once
D. 只有 eventually-consistent full scan 才能讀 outbox
E. 檢查 PutEvents 的 FailedEntryCount 與逐 entry 結果，只重試失敗項；成功被 event bus 接受後才把 outbox 標記 handed_off，並另行配置 target retry/DLQ

**答案：B、E**

- **A：** 錯誤。先刪除會在 publish failure 時失去復原依據。
- **B：** 正確。Change stream 與 publish retry 都可能產生 duplicate delivery。
- **C：** 錯誤。Transport delivery 不保證外部 effect exactly once。
- **D：** 錯誤。Streams/CDC 正是避免只靠 full scan 的方式。
- **E：** 正確。HTTP 200 仍可能包含失敗 entries；event ID 只證明 bus ingestion，不代表每個 target 完成。Publisher 在 bus acceptance 後記 durable handoff，target retry/DLQ 與 consumer 冪等則是後續邊界。

**事實查證：** [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)、[DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)、[PutEvents API reference](https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_PutEvents.html)、[Using AWS Lambda with Amazon DynamoDB](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html)

### 練習題 4｜SAP｜Saga orchestration 與 choreography

訂單流程有 12 個 participants、人工例外與複雜 compensation，團隊最重視中央可見性與明確 timeout。較合適的起點是什麼？

A. 純 SNS fan-out，會自動知道補償順序
B. Orchestrated saga，例如 Step Functions 明確保存 sequence、timeout 與 compensation
C. Choreography，因為它完全沒有 coupling
D. 跨所有 database 維持單一 transaction

**答案：B**

- **A：** 錯誤。SNS fan-out 只負責複製訊息，不會自動保存 participant sequence、timeout、補償順序與整體 outcome；簡單獨立通知才適合純 fan-out。
- **B：** 正確。需求偏向集中協調與可觀測流程；仍需避免 orchestrator 承擔 domain logic。
- **C：** 錯誤。Choreography 耦合在 event contracts，participant 增多後追蹤更難。
- **D：** 錯誤。獨立服務通常無法共享長時間 ACID transaction。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)

### 練習題 5｜SAP｜Semantic compensation

商業規則要求缺貨訂單必須取消並退回已收款項；Payment 已 capture，但 inventory reservation 後來失敗。Saga 的首選 compensation 應如何設計？

A. 執行新的、冪等且可觀測的 refund 操作，並為 refund failure 設 retry/escalation
B. 若只是 authorization 尚未 capture，呼叫 void authorization；直接把同一操作套用到本題已 capture 的付款
C. 把訂單改成 backorder 並保留款項，未取得客戶同意也不變更對外承諾
D. 只把案件送人工客服，沒有自動 refund retry、冪等 key 或 escalation deadline

**答案：A**

- **A：** 正確。Compensation 是業務語意上的反向行動，不是時間倒轉。
- **B：** 錯誤。Void authorization 適合款項尚未 capture 的不同狀態；本題已收款，必須依 payment provider 支援的 refund 語意建立新反向交易。
- **C：** 錯誤。Backorder 在客戶接受延期且商業契約允許保留款項時可能合理；本題明定缺貨必須取消退款，不能暗中改寫承諾。
- **D：** 錯誤。人工處理適合自動 refund 重試耗盡或狀態無法判定時的 escalation；若完全沒有自動、冪等且有期限的首選路徑，會擴大延遲與營運風險。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

### 練習題 6｜SAP｜Irreversible action ordering

流程包含 reserve inventory、authorize payment、ship physical goods。哪兩項能降低不可逆失敗？（選兩項）

A. 先 ship，再嘗試 payment
B. 先做可釋放的 reservation/authorization，將 shipment 放在後段
C. 為每次 shipment retry 產生新 identity
D. 為無法自動補償的結果建立人工 reconciliation/escalation
E. 跨服務持鎖直到客戶簽收

**答案：B、D**

- **A：** 錯誤。最難補償的實體出貨不應最先執行，否則前置檢查失敗時只能人工追回。
- **B：** 正確。先完成可釋放或會到期的 inventory reservation 與 payment authorization，能在前置條件失敗時安全撤銷，並把不可逆 shipment 延後。
- **C：** 錯誤。Shipment retry 每次產生新 identity 會讓倉儲系統把同一訂單視為新出貨；應重用穩定 shipment key 並查詢既有 outcome。
- **D：** 正確。物理世界 action 需要明確 exception path。
- **E：** 錯誤。跨服務長時間持鎖既難以實作，也會阻塞其他交易並降低整體可用性。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

### 練習題 7｜SAP｜Aggregate event order

Outbox publisher 可能重複發布，且同一 order 的 v12 有時先於 v11 到達。Consumer 應如何保護狀態？

A. 依牆鐘 timestamp 排序所有 hosts
B. 相信 classic EventBridge rule delivery，或 Custom Event Bus FIFO，能跨所有 publishers 與 event groups 提供 global ordering
C. 用 event_id 去重、aggregate sequence/version 與 conditional state transition 拒絕或暫存 stale/out-of-order event
D. 只依 event type 去重

**答案：C**

- **A：** 錯誤。Clock skew 使 timestamp 不適合作唯一 ordering authority。
- **B：** 錯誤。Classic rule delivery 沒有 global-order contract；Custom Event Bus FIFO 也只在同一 publisher account 的 event group 內排序，不能跨 accounts 或 groups 建立全域順序。
- **C：** 正確。Stable identity 與 aggregate version 明確表達 domain order；即使使用 FIFO transport，consumer 仍能拒絕 stale version 並處理超出 dedup window 的重複。
- **D：** 錯誤。同 type 的不同合法 transitions 會被誤刪。

**事實查證：** [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)、[Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)、[Ordering and deduplication in AWS Custom Event Bus](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-custom-bus-ordering.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 8｜SAP｜Stuck saga diagnosis

Saga 顯示 payment 成功但 shipment 未建立。最佳診斷路徑是什麼？

A. 用 saga/order ID 串聯 execution history、outbox backlog、delivery、participant state、retry 與 compensation，再依 authoritative records reconcile
B. 先把 shipment DLQ 全部 redrive，未確認原 shipment side effect、event identity 或 consumer 冪等狀態
C. 立即執行 payment compensation，未查 shipment 是否其實已建立但 acknowledgement 遺失
D. 啟動新的 saga execution 接管同一 order，讓原 execution 繼續 retry

**答案：A**

- **A：** 正確。跨邊界 correlation 能找出卡在 durable state、publication、delivery 或 participant 的哪一站。
- **B：** 錯誤。若已確認只有可重試 delivery failure 且 consumer 冪等，受控 redrive 才合理；未先定位就整批重送可能重複出貨並掩蓋真正卡點。
- **C：** 錯誤。若 authoritative shipment 狀態證明不可恢復，refund 才可能是正確補償；在 outcome 不確定時先退款，可能形成已出貨又退款的新錯誤。
- **D：** 錯誤。替代 execution 只適合原流程已終止、ownership 已轉移且所有 side effects 可去重的復原程序；雙 execution 會競爭並重做步驟。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)、[Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAA｜Eventual consistency UX

Order workflow 可能數分鐘才收斂。哪兩項使用者與營運設計正確？（選兩項）

A. 對外呈現 pending/confirmed/failed 狀態與 status endpoint/callback
B. 一律立即顯示 confirmed
C. 以一個 global lock 阻止所有 orders
D. 宣稱非同步架構零不一致
E. 定義 convergence SLO、超時告警與 reconciliation job

**答案：A、E**

- **A：** 正確。Pending state 誠實表達尚未完成的 distributed work。
- **B：** 錯誤。在 workflow 尚未收斂時立即顯示 confirmed，會把 provisional state 誤當最終承諾；只有必要 invariants 已 durable commit 時才可宣告完成。
- **C：** 錯誤。全域鎖會把所有獨立 orders 序列化，破壞水平擴展與故障隔離。
- **D：** 錯誤。非同步架構會自然產生暫時不一致與不確定狀態；正確做法是公開 pending、定義收斂 SLO，並提供 timeout 與 reconciliation。
- **E：** 正確。SLO 與 reconciliation 讓 eventual consistency 可營運。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

### 練習題 10｜SAP｜Saga/outbox migration

團隊要把會扣款、保留庫存與出貨的同步 monolith 漸進改為 saga/outbox；遷移期間不得讓舊、新路徑同時擁有同一 side effect。哪個 rollout 最安全？

A. 先讓舊、新 saga 同時對 production payment 與 shipment 寫入，再用月底報表刪除重複結果
B. 先 dual-publish 到新 consumers，讓新路徑可自由執行 side effects；若出錯再依 database timestamp 猜測 ownership
C. 保留舊路徑為 side-effect owner，但 shadow 路徑仍呼叫真實付款，只要求 payment token 每次不同以便比較
D. 先建立 stable identities/versioned contracts；dual-publish 只送 disabled、compare-only 或已證明冪等的 shadow consumers，由舊路徑獨占 side effects；再 canary 轉移 ownership、reconcile 指標並保留 rollback

**答案：D**

- **A：** 錯誤。兩條路徑同時擁有真實 side effects 會重複扣款或出貨；只有完全隔離的測試環境才適合同時執行。
- **B：** 錯誤。Dual-publish 可用於驗證 contract 與讀模型，但在 ownership 未定義前開放寫入會造成競爭；timestamp 也不能取代明確 fencing 或狀態轉移。
- **C：** 錯誤。非變動 shadow 可比較決策，但呼叫真實付款已是 side effect；不同 token 反而會把同一交易視為兩次合法操作。
- **D：** 正確。Shadow 階段不改變 production state，且每一遷移階段只有一條路徑擁有 side effects；canary、reconciliation、lag/duplicate/compensation 指標與 rollback 共同提供可逆證據。

**事實查證：** [SAP-C02 Domain 4: Accelerate Workload Migration and Modernization](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)、[Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「跨服務無法用單一ACID transaction同時更新database與message broker。」，所以「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」能直接滿足它；若constraint改成「Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」。替代方案「Orchestration集中flow可見性；choreography降低中央耦合但事件關係較難追。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「跨服務無法用單一ACID transaction同時更新database與message broker。」，排除會導致「先commit DB再publish時process crash，造成狀態已改但事件永遠遺失。」的選項，再選「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAP-2.4 Design a strategy to meet reliability requirements；SAP-3.4 Determine a strategy to improve reliability。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「本地transaction寫business state與outbox，再發布事件；Saga用補償或協調處理多步流程。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「make state transition and event publication one durable decision」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 59 章　Circuit Breaker、Bulkhead 與 Backpressure

慢依賴會佔滿thread、connection與queue，把局部故障傳到整個系統。

## 跟著一件工作在服務間流動：先從故事開始

把鏡頭拉到一個真實的production現場：推薦服務變慢後，結帳API的thread pool也被占滿，但推薦其實可降級。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：慢依賴會佔滿thread、connection與queue，把局部故障傳到整個系統。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把分散式整合想成餐廳出單：收銀台不必站著等每個廚房完成，但每張單都要能追蹤、重做與防重複。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Elastic Load Balancing是這一章的入口，Amazon SQS用來畫出邊界；主要方向「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：推薦服務變慢後，結帳API的thread pool也被占滿，但推薦其實可降級。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[Elastic Load Balancing]
          │ 將連線或request分散到健康targets並隔離client與backend生命週期。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · Amazon SQS：以managed queue解耦producer與consumer的時間和容量。
  · AWS Lambda reserved concurrency：按事件執行短生命函式，自動管理capacity與runtime基礎設施。

失敗時先找：用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Elastic Load Balancing有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Elastic Load Balancing和Amazon SQS並不是兩個任意的產品名稱。前者適合本章，是因為「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」直接回應了眼前的問題；後者描述的「Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「protect scarce resources before maximizing throughput」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| AWS Lambda reserved concurrency | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 推薦服務變慢後，結帳API的thread pool也被占滿，但推薦其實可降級。

1. 故事的起點：推薦服務變慢後，結帳API的thread pool也被占滿，但推薦其實可降級。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Elastic Load Balancing負責「將連線或request分散到健康targets並隔離client與backend生命週期。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon SQS、AWS Lambda reserved concurrency各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Elastic Load Balancing

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：慢依賴會佔滿thread、connection與queue，把局部故障傳到整個系統。
- **具體例子／邊界：** 在「推薦服務變慢後，結帳API的thread pool也被占滿，但推薦其實可降級。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon SQS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：protect scarce resources before maximizing throughput。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

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

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Elastic Load Balancing

- **功用：** 將連線或request分散到健康targets並隔離client與backend生命週期。
- **底層機制：** Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
- **關鍵設定：** scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- **選擇時機：** 多instance/task高可用入口與rolling deployment。
- **替換時機：** 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### AWS Lambda reserved concurrency

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

## 考前與實作時再查：設定操作手冊

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

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### AWS Lambda reserved concurrency：逐項設定說明

#### `memory/CPU`

- **控制什麼：** `memory/CPU`設定AWS Lambda reserved concurrency的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Lambda reserved concurrency的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `reserved/provisioned concurrency`

- **控制什麼：** `reserved/provisioned concurrency`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `event source mapping`

- **控制什麼：** `event source mapping`指定AWS Lambda reserved concurrency讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `DLQ/destination`

- **控制什麼：** `DLQ/destination`指定AWS Lambda reserved concurrency讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda reserved concurrency的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ephemeral storage`

- **控制什麼：** `ephemeral storage`選擇AWS Lambda reserved concurrency的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

## 讀到這裡，請用自己的話說一次

1. Elastic Load Balancing的責任：將連線或request分散到健康targets並隔離client與backend生命週期。
2. 底層機制：Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。
3. 第一個要看的設定：scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
4. 選擇邏輯：Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。
5. 不要混淆：Amazon SQS的責任是「以managed queue解耦producer與consumer的時間和容量。」；它不會自動取代Elastic Load Balancing。
6. 替換訊號：全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。
7. 最常見錯法：用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。
8. 可移植原則：protect scarce resources before maximizing throughput。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Elastic Load Balancing | 將連線或request分散到健康targets並隔離client與backend生命週期。 | Listener接收流量，rule選target group，health check移除不健康targets；型別決定可見protocol層。 | 多instance/task高可用入口與rolling deployment。 | 全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。 |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| AWS Lambda reserved concurrency | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。 | 只有當題目條件明確改變時才可能合理。 | 用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。」之間做選擇。
- 認得常考設定：scheme、listeners、target groups、health checks、cross-zone、deregistration delay與idle timeout。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：全球跨Region選Route 53/Global Accelerator；API治理選API Gateway。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.3 Determine a strategy to improve performance；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜Failure control selection

推薦服務變慢後占滿 checkout thread pool。哪項描述最正確？

A. Timeout 限等待；bounded retry 處理短暫錯誤；breaker 停止持續失敗呼叫；bulkhead 隔離 pool；backpressure/load shedding 限制進入工作
B. 只靠 ALB health check 可完成所有控制
C. 無限 retry 可提高 availability
D. 擴大 caller fleet 可修復完全失效 downstream

**答案：A**

- **A：** 正確。五種機制處理不同 failure stage，需組合而非混稱。
- **B：** 錯誤。Target health 不管理 caller resource pools 與 optional dependency fallback。
- **C：** 錯誤。無限 retry 會把每次失敗轉成持續新增的下游流量，耗盡 thread、connection 與 capacity；重試必須受 deadline、attempt 和 quota 限制。
- **D：** 錯誤。更多 callers 可能讓 downstream 更快崩潰。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/reducing-scope-of-impact-with-cell-based-architecture.html)、[REL05-BP04 Fail fast and limit queues](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)

### 練習題 2｜SAP｜Circuit breaker states

下游服務偶爾短暫錯誤，也可能持續失效；caller 必須在故障期停止大部分呼叫，並在稍後謹慎驗證恢復。哪個 breaker state transition 設計合理？

A. 單一 error 後永久 open
B. Closed 依窗口 error/slow-call threshold open；等待後 half-open 僅少量 probes；成功 close、失敗 reopen
C. Half-open 立即送全部 production load
D. 每個 request 都清除 failure history

**答案：B**

- **A：** 錯誤。單一瞬時錯誤不足以判定 dependency 長期失效；永久 open 會在服務恢復後仍拒絕流量，應以窗口 threshold 與 half-open probe 判斷。
- **B：** 正確。窗口、冷卻與有限探測共同避免 oscillation 與 recovery stampede。
- **C：** 錯誤。Half-open 階段應只允許少量 probe 驗證服務；未證實恢復便送入全部 production load，可能立刻重現原故障與 recovery stampede。
- **D：** 錯誤。Breaker 需要跨 requests 觀察 failure rate。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 3｜SAA｜Business-safe fallback

Recommendation 與 payment authorization 同時故障。哪兩項 fallback 正確？（選兩項）

A. Payment 未執行仍回 success
B. Recommendations 回 cached/default 並標記降級
C. 長期使用過期 authorization 決策
D. Payment fail closed，或以明確 pending/queue+reconciliation 契約處理
E. 因 recommendations 失敗而讓全部 checkout 必然失敗

**答案：B、D**

- **A：** 錯誤。Payment authorization 尚未執行卻回 success，會對使用者做出不存在的財務承諾；critical payment invariant 應 fail closed 或明確回 pending。
- **B：** 正確。Recommendations 是 optional read path，可回受控 cached/default 結果並標記降級；這能保留 checkout 核心功能而不偽造付款結果。
- **C：** 錯誤。過期 authorization 可能已撤銷或超出風險窗口，不能無限沿用；只有有明確 freshness、風險上限與業務批准時才可短暫快取。
- **D：** 正確。Critical invariant 必須保持真實結果或明確 pending。
- **E：** 錯誤。Optional dependency 不應擴大 blast radius。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)

### 練習題 4｜SAA｜互動驗證與批次匯出的資源隔離

同一服務同時處理需在 200 ms 內完成的使用者 authentication，以及可延後數小時的 nightly audit export。兩者共用 RDS connection pool 與對外 HTTP client pool；export burst 會占滿連線，使 authentication timeout，但主機 CPU 與 RDS CPU 都未飽和。哪項改造最合適？

A. 擴大單一共享 RDS/HTTP pool，並只依主機 CPU 增加 service tasks，不限制 export concurrency
B. 在共享 pool 前加入 export priority queue，但允許 batch requests 取得全部 database 與 HTTP connections
C. 為 authentication 與 export 建立獨立且有上限的 RDS/HTTP client pools，替 authentication 保留容量，並以 queue、rate limit 或 worker concurrency 約束 export
D. 在 authentication 與 export 外圍共用一個 global circuit breaker；任一 workload 變慢時同時停止兩者

**答案：C**

- **A：** 錯誤。更大的共享 pool 或更多 tasks 仍允許 export 吃完連線，還可能超過 RDS 與外部服務的安全容量；只有下游確有餘裕且另有 per-workload cap 時才適合擴容。
- **B：** 錯誤。Priority queue 只能決定等待順序，不能搶回已被 batch 工作占用的 connections；若 export concurrency 已受限，priority 才能進一步改善排程。
- **C：** 正確。獨立 bounded pools 建立 bulkhead，reserved authentication capacity 保護低延遲 SLO；export queue 與 concurrency cap 則把可延後工作留在自己的資源預算內。
- **D：** 錯誤。Global breaker 會把 export 壓力擴散到仍可服務的 authentication；breaker 應按 dependency 或 workload failure boundary 設置，而不是把兩者綁成共同故障域。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/reducing-scope-of-impact-with-cell-based-architecture.html)

### 練習題 5｜SAA｜Lambda reserved concurrency

非關鍵報表 Lambda 的 burst 會耗盡 account concurrency 並壓垮 database，使付款 Lambda 無法執行。應如何隔離？

A. 所有 functions 都設成 account 最大 reserved concurrency
B. 只增加 database timeout
C. 假設 serverless 自動提供無限 concurrency
D. 限制報表 concurrency、為關鍵 function 保留容量，並配置 throttle 後的 queue/retry/DLQ 行為

**答案：D**

- **A：** 錯誤。Reserved concurrency 的總量受 account 配額，不能每個都取最大。
- **B：** 錯誤。Timeout 不限制連線數與 invocation burst。
- **C：** 錯誤。Lambda 有 concurrency quotas，下游容量更有限。
- **D：** 正確。Reserved concurrency 同時可保留與限制，形成 blast-radius control。

**事實查證：** [Configuring reserved concurrency for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

### 練習題 6｜SAA｜Bounded async backlog

促銷 queue 的工作超過 15 分鐘就沒有商業價值。哪兩項設計正確？（選兩項）

A. Retention 設無限
B. 以 ApproximateAgeOfOldestMessage 與 arrival/service rate 擴縮及告警
C. 只監控 queue depth
D. 對過期工作 load shed/expire，保留 DLQ 或 reconciliation evidence
E. 永遠先處理已過 deadline 的舊工作

**答案：B、D**

- **A：** 錯誤。SQS retention 有上限，且無限 backlog 只延後失敗。
- **B：** 正確。Age 比單純 depth 更直接反映 deadline risk。
- **C：** 錯誤。相同 depth 在不同 processing rate 下意義不同。
- **D：** 正確。超過商業 deadline 的工作應 load shed 或 expire，避免占用仍可服務新工作的 capacity；DLQ 或 reconciliation evidence 則保留稽核與補償依據。
- **E：** 錯誤。無條件先處理已失去價值的工作，會消耗 capacity 並讓仍可達成的新工作也逾期。

**事實查證：** [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Amazon SQS message quotas](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html)、[REL05-BP04 Fail fast and limit queues](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)

### 練習題 7｜SAP｜Synchronous admission control

API downstream database 最多安全處理 200 concurrent requests。尖峰突然到 2000。最佳保護是什麼？

A. 入口設 concurrency/rate limit，飽和時回明確 retryable response，clients 使用 backoff/jitter
B. 全部接受到 unbounded memory queue
C. 提高 API timeout
D. 尚未 admission 就先回 200 success

**答案：A**

- **A：** 正確。早期 admission control 保護 database 並使 overload 行為可預期。
- **B：** 錯誤。Memory queue 最終耗盡且 requests 過期。
- **C：** 錯誤。提高 API timeout 不會增加 database 可安全處理的 concurrency，反而讓更多 requests 占住 threads、connections 與 memory，延後 overload 顯現。
- **D：** 錯誤。在 admission 與 durable acceptance 尚未完成前回 200 success，會讓 client 誤認工作已承諾執行；應明確拒絕或先 durable enqueue 再回 accepted。

**事實查證：** [REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)、[REL05-BP04 Fail fast and limit queues](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)

### 練習題 8｜SAP｜Cascading latency diagnosis

API p99 暴增但 CPU 30%。哪組 signals 最能發現 I/O wait 型 cascading failure？

A. 先依 host CPU 與 memory 自動 scale out；若節點資源沒有飽和，仍不檢查 request 等待與下游
B. 只檢查 database CPU、connections 與 slow queries，忽略 caller pools、queue age、retries 與其他 dependencies
C. 統一降低所有 downstream timeout，未依 caller deadline、正常 latency 與 dependency criticality 分配 budget
D. thread/connection pool saturation、in-flight、queue age、downstream latency/errors、retry attempts、breaker/rejection state

**答案：D**

- **A：** 錯誤。Scale out 適合已證實 CPU 或單機容量不足的情境；I/O wait 時 CPU 可偏低，更多 callers 反而可能增加下游連線與重試壓力。
- **B：** 錯誤。資料庫指標適合已懷疑 DB 是瓶頸時深入確認，但只看 DB 會漏掉 caller pool 耗盡、其他依賴或 retry amplification 的完整因果鏈。
- **C：** 錯誤。較短 timeout 能 fail fast，但一體適用可能誤殺正常慢請求；應從端到端 deadline 分配每個 attempt，並搭配 pool、breaker 與 admission signals。
- **D：** 正確。這些 signals 沿著排隊、等待、重試與隔離狀態定位故障。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Noisy tenant isolation

一個大型 tenant 可耗盡所有 workers，讓其他 tenants 超過 SLO。哪兩項治理合理？（選兩項）

A. 建立 per-tenant quota/concurrency/queue 或 cell isolation
B. 只看所有 tenants 的平均 TPS
C. 所有 tenants 共用單一 FIFO MessageGroupId
D. Premium tenant 可無限使用同一 database pool
E. 保留 global safety limit，並以公平排程/tenant metrics 防止共享資源耗盡

**答案：A、E**

- **A：** 正確。Tenant-scoped limits 將 noisy-neighbor impact 限制在明確邊界。
- **B：** 錯誤。所有 tenants 的平均 TPS 會把大型 tenant 的尖峰攤平，無法顯示誰耗盡 workers；應觀察 per-tenant throughput、age、reject 與 concurrency。
- **C：** 錯誤。所有 tenants 共用一個 FIFO MessageGroupId 會把整體工作序列化，降低吞吐且仍無法依 tenant 分配 capacity；需要順序時應按 tenant 分組。
- **D：** 錯誤。Premium entitlement 可配置較高 quota，但不能無上限使用共同 database pool；仍須保留 global safety limit，避免單一租戶擊穿 shared bottleneck。
- **E：** 正確。局部公平之外仍需保護整體 system capacity。

**事實查證：** [SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)、[Configuring reserved concurrency for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/reducing-scope-of-impact-with-cell-based-architecture.html)、[Amazon SQS fair queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html)

### 練習題 10｜SAP｜Resilient call path review

Checkout 的 optional dependency 會 timeout、暫時 throttling 或持續失效，且 caller thread pool 不可被它耗盡。哪條 call path 最完整地控制這個 dependency？

A. Client deadline→bounded retry+jitter→per-dependency pool→breaker→attempt timeout→安全 fallback，並量測 attempts/rejections/saturation/business success
B. 只用 ELB target health
C. Retry 不受 deadline 限制
D. Breaker 前放 unbounded queue

**答案：A**

- **A：** 正確。它限制時間、流量與 failure domain，並留下業務證據。
- **B：** 錯誤。Health check 不控制 client pools/retries/fallback。
- **C：** 錯誤。Retry 超過 caller deadline 後仍執行，只會產生使用者已不再等待的無效工作。
- **D：** 錯誤。Unbounded queue 只是延後 overload。

**事實查證：** [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)、[REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)、[Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)、[Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/reducing-scope-of-impact-with-cell-based-architecture.html)、[REL05-BP04 Fail fast and limit queues](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounde…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「慢依賴會佔滿thread、connection與queue，把局部故障傳到整個系統。」，所以「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」能直接滿足它；若constraint改成「Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」。替代方案「Autoscaling可增加容量但不能修復完全失效依賴或無限arrival rate。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「慢依賴會佔滿thread、connection與queue，把局部故障傳到整個系統。」，排除會導致「用unbounded queue隱藏過載，直到memory耗盡且所有request都過期。」的選項，再選「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Timeout限制等待，circuit breaker阻止無效呼叫，bulkhead隔離資源，bounded queue回傳背壓。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「protect scarce resources before maximizing throughput」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 60 章　Stateless、Stateful、Sync 與 Async

架構需要明確知道state owner與等待關係，才能安全scale與failover。

## 跟著一件工作在服務間流動：先從故事開始

如果今天由你值班，收到的需求可能是這樣：報表產生需十分鐘，使用者不應維持HTTP connection等待。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：架構需要明確知道state owner與等待關係，才能安全scale與failover。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把分散式整合想成餐廳出單：收銀台不必站著等每個廚房完成，但每張單都要能追蹤、重做與防重複。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon SQS承接主要責任，以AWS Step Functions檢查替代條件，並用「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：報表產生需十分鐘，使用者不應維持HTTP connection等待。

producer完成自己的business action
          │ ① 發出message／event／record
          ▼
[Amazon SQS]
          │ 以managed queue解耦producer與consumer的時間和容量。
          │ ② 保存、路由、排序或協調後交給consumer
          │ ③ 成功checkpoint；失敗retry／DLQ／compensate
          ▼
[business state]
交付可能重複，因此side effect必須可安全重做
本章其他角色：
  · AWS Step Functions：以可視化state machine編排多步驟、retry、branch、parallel與human wo…
  · Amazon ElastiCache：提供managed Valkey/Redis OSS/Memcached記憶體data store。

失敗時先找：把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一件工作在服務間流動」。先不要急著問Amazon SQS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon SQS和AWS Step Functions並不是兩個任意的產品名稱。前者適合本章，是因為「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」直接回應了眼前的問題；後者描述的「同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「state placement determines scaling and failure behavior」。更白話地說：先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |

## 把全圖套進一個具體案例

**場景：** 報表產生需十分鐘，使用者不應維持HTTP connection等待。

1. 故事的起點：報表產生需十分鐘，使用者不應維持HTTP connection等待。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon SQS負責「以managed queue解耦producer與consumer的時間和容量。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Step Functions、Amazon ElastiCache各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon SQS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：架構需要明確知道state owner與等待關係，才能安全scale與failover。
- **具體例子／邊界：** 在「報表產生需十分鐘，使用者不應維持HTTP connection等待。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Step Functions

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：state placement determines scaling and failure behavior。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### visibility timeout

SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon SQS

- **功用：** 以managed queue解耦producer與consumer的時間和容量。
- **底層機制：** SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
- **關鍵設定：** Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- **選擇時機：** work queue、burst buffer、retry與獨立擴展consumer。
- **替換時機：** 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

### Amazon ElastiCache

- **功用：** 提供managed Valkey/Redis OSS/Memcached記憶體data store。
- **底層機制：** Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
- **關鍵設定：** engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- **選擇時機：** session、hot reads、leaderboard、rate limiting與降低database load。
- **替換時機：** 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。

## 考前與實作時再查：設定操作手冊

### Amazon SQS：逐項設定說明

#### `Standard/FIFO`

- **控制什麼：** `Standard/FIFO`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `visibility timeout`

- **控制什麼：** `visibility timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `long polling`

- **控制什麼：** Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。
- **何時需要：** Consumer持續從Amazon SQS queue取工作，而且低流量時大量short polls都拿不到message。
- **怎麼設定／驗證：** 設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。
- **常見錯法：** Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon SQS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `DLQ/redrive`

- **控制什麼：** `DLQ/redrive`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。
- **何時需要：** Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。
- **怎麼設定／驗證：** 設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。
- **常見錯法：** 未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon SQS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `batch size`

- **控制什麼：** `batch size`設定Amazon SQS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「work queue、burst buffer、retry與獨立擴展consumer。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### AWS Step Functions：逐項設定說明

#### `Standard/Express`

- **控制什麼：** `Standard/Express`選擇AWS Step Functions的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `Task/Choice/Map/Parallel/Wait`

- **控制什麼：** `Task/Choice/Map/Parallel/Wait`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Step Functions的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `Retry/Catch`

- **控制什麼：** `Retry/Catch`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `timeouts`

- **控制什麼：** `timeouts`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Step Functions的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `callback token`

- **控制什麼：** `callback token`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** AWS Step Functions需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

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

## 讀到這裡，請用自己的話說一次

1. Amazon SQS的責任：以managed queue解耦producer與consumer的時間和容量。
2. 底層機制：SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。
3. 第一個要看的設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
4. 選擇邏輯：可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。
5. 不要混淆：AWS Step Functions的責任是「以可視化state machine編排多步驟、retry、branch、parallel與human workflow。」；它不會自動取代Amazon SQS。
6. 替換訊號：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
7. 最常見錯法：把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。
8. 可移植原則：state placement determines scaling and failure behavior。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon SQS | 以managed queue解耦producer與consumer的時間和容量。 | SendMessage保存副本；ReceiveMessage暫時以visibility timeout隱藏，成功後DeleteMessage。 | work queue、burst buffer、retry與獨立擴展consumer。 | 一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。 | 只有當題目條件明確改變時才可能合理。 | 把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。」之間做選擇。
- 認得常考設定：Standard/FIFO、visibility timeout、long polling、retention、DLQ/redrive、encryption與batch size。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一對多push用SNS/EventBridge；可回播ordered log用Kinesis/MSK。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Hidden instance-local state

Web fleet 以 Auto Scaling 增加 instances，但 session、uploads 與 job status 都只存在 local memory/disk。如何提高可替換性？

A. 把 durable sessions/status/artifacts 移到合適 shared durable stores，只保留可丟棄 cache/temp local
B. 啟用 stickiness 後宣稱 stateless
C. 每次 scale-out 手動複製所有 local disks
D. 所有 authoritative state 留在 process memory

**答案：A**

- **A：** 正確。Stateless compute 的重點是任一 instance 可被替換，而 durable state 有明確 owner。
- **B：** 錯誤。Stickiness 只維持 affinity，不複寫 state。
- **C：** 錯誤。每次 scale-out 手動複製 local disks 需要處理並行寫入、傳輸延遲與失敗重試，仍有一致性 gap；只有不可變 image 才適合複製。
- **D：** 錯誤。Process memory 隨 instance crash、deployment 或 scale-in 消失，不能保存 authoritative state；它只適合可重建 cache 與短暫計算資料。

**事實查證：** [REL05-BP06 Make systems stateless where possible](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html)

### 練習題 2｜SAA｜Sync versus async contract

報表通常需 10 分鐘產生，使用者不需保持連線。最佳 API contract 是什麼？

A. HTTP connection 保持 10 分鐘
B. Durably accept job 後回 202 與 operation ID/status URL，完成時可 callback/notify
C. 所有付款也改成不回結果的 async
D. 在工作尚未入 queue 前回 success

**答案：B**

- **A：** 錯誤。長連線易受 proxy/client timeout 且占用資源。
- **B：** 正確。它明確把 contract 從立即結果改成 eventual completion。
- **C：** 錯誤。需要立即確認的 invariants 不應盲目 async。
- **D：** 錯誤。必須先 durable acceptance，否則 response 後工作可能遺失。

**事實查證：** [SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)、[Managing asynchronous workloads with a REST API](https://aws.amazon.com/blogs/architecture/managing-asynchronous-workflows-with-a-rest-api/)

### 練習題 3｜SAA｜Complete asynchronous job API

設計一個通常需 10 分鐘、client 可能因 timeout 重送且完成後要下載大型檔案的報表 API。哪兩項是完整架構必要部分？（選兩項）

A. POST 以 idempotency key durable 建 job，回 202、job ID 與 status URL
B. 回傳某台 worker hostname 供日後查詢
C. 只把 status 放在 SQS message 內
D. 讓 API process 持續活到報表完成
E. Queue+workers 處理；durable status store 記狀態；結果放 object storage；poll/callback 通知

**答案：A、E**

- **A：** 正確。Stable job identity 使 client retry 不會重複建立工作。
- **B：** 錯誤。Worker hostname 只識別暫時 compute instance，scale-in 或 crash 後便失效；查詢 authority 應是 durable job/status store 與穩定 job ID。
- **C：** 錯誤。Queue 不適合作 queryable status database。
- **D：** 錯誤。讓 API process 活到 worker 完成仍是長同步等待，無法解除 connection 與 instance lifecycle 的耦合。
- **E：** 正確。它分離 work buffer、state owner、result storage 與 completion channel。

**事實查證：** [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)、[Managing asynchronous workloads with a REST API](https://aws.amazon.com/blogs/architecture/managing-asynchronous-workflows-with-a-rest-api/)

### 練習題 4｜SAA｜State ownership

報表平台同時需要保存可查詢的 job status、不可變的大型輸出、短暫 cache、workflow progress 與待處理 messages。哪個 state placement 最合理？

A. SQS 作任意查詢的 job status database
B. ElastiCache 作唯一 payment ledger
C. 大型 report binary 放在 Step Functions input
D. Transactional truth 在 database、large immutable result 在 S3、workflow progress 在 workflow/state store、messages 在 queue

**答案：D**

- **A：** 錯誤。Queue 以 delivery/ack 為主，不提供一般 status query model。
- **B：** 錯誤。Cache eviction/failure 不適合作唯一財務 authority。
- **C：** 錯誤。Workflow payload/history 有大小與敏感資料成本。
- **D：** 正確。每種 store 對應其 durability、access pattern 與 lifecycle。

**事實查證：** [REL05-BP06 Make systems stateless where possible](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html)、[Standard and Express Workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)、[AWS Step Functions service quotas](https://docs.aws.amazon.com/step-functions/latest/dg/service-quotas.html)

### 練習題 5｜SAA｜Sticky sessions boundary

ALB stickiness 是否等同 session high availability？

A. 是，ALB 會複寫 instance memory
B. 否；stickiness 只維持 affinity，外部化 session 才讓其他 healthy instance 接手
C. 是，DNS TTL 會保存 session
D. 是，Auto Scaling 會搬移 process memory

**答案：B**

- **A：** 錯誤。Load balancer 不複寫 application memory。
- **B：** 正確。Instance 故障或 scale-in 時 affinity 無法挽救 local-only session。
- **C：** 錯誤。DNS cache 與 session storage 無關。
- **D：** 錯誤。Auto Scaling 替換 instances，不搬移 runtime state。

**事實查證：** [REL05-BP06 Make systems stateless where possible](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html)

### 練習題 6｜SAA｜SQS versus Step Functions

團隊正在拆分一個 10 分鐘報表流程：入口需要吸收 burst，而某些報表又包含 branching、callback 與 compensation。哪兩項服務選擇正確？（選兩項）

A. SQS 適合獨立 jobs 的 buffering、retry 與 backpressure
B. EventBridge archive 是一般 competing-consumer work queue
C. 一個 Lambda loop 最適合保存數日 workflow state
D. Step Functions 適合 branching、callbacks、timeouts 與 compensation；需要 buffer 時可與 SQS 組合
E. Step Functions 的唯一用途是增加 SQS throughput

**答案：A、D**

- **A：** 正確。Queue 解耦 producer/worker 的時間與容量。
- **B：** 錯誤。Archive 用於 event replay，不是工作 ack queue。
- **C：** 錯誤。Lambda execution environment 可隨時被替換，且不應靠單一 process memory 保存數日 workflow progress；短暫單步計算才適合 function-local state。
- **D：** 正確。Workflow 與 queue 解決不同 contract，可共同使用。
- **E：** 錯誤。Step Functions 管 orchestration state，不是 queue capacity feature。

**事實查證：** [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)

### 練習題 7｜SAP｜Immediate consistency boundary

Checkout 包含 payment authorization、inventory invariant、email 與 analytics。什麼應留在立即確認路徑？

A. 先告知付款成功，再非同步決定是否授權
B. Email 與 analytics 必須完成才可回 checkout
C. Payment/inventory 的必要 invariant；email/analytics 可在 durable acceptance 後 async
D. 全部改 eventual 且不呈現 pending

**答案：C**

- **A：** 錯誤。在 authorization 尚未完成前宣稱付款成功，會做出尚未成立且可能無法兌現的財務承諾。
- **B：** 錯誤。非關鍵工作會拉長 latency 並擴大 failure coupling。
- **C：** 正確。Caller 需要知道的 correctness boundary 保持同步/transactional，獨立 side effects 解耦。
- **D：** 錯誤。Eventual state 必須在 user contract 中明示。

**事實查證：** [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

### 練習題 8｜SAP｜Duplicate async submission

Client 沒收到 202 而重送，worker 也可能在完成結果後、ack 前 crash。如何避免兩份 report 與錯誤狀態？

A. 每次 retry 建新 job ID
B. 依賴 visibility timeout 去重
C. stable creation key、durable job identity/status、idempotent worker，結果與進度 durable 後才 ack
D. 結果寫入前先標 completed

**答案：C**

- **A：** 錯誤。Client 每次 retry 建立新 job ID，server 無法把遺失 202 後的重送連回原工作，會同時產生兩份 report 與競爭狀態。
- **B：** 錯誤。Visibility timeout 只暫時隱藏已接收 message，逾時或 acknowledgement 不確定時仍會 redeliver；它不提供 business-level deduplication。
- **C：** 正確。Submission 與 processing 兩個重複邊界都被保護。
- **D：** 錯誤。在 report object durable 寫入前先標 completed，status reader 可能取得不存在或未完成的 result；應先提交 artifact，再以條件式狀態轉移發布完成。

**事實查證：** [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)、[Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 9｜SAP｜Accepted but never completed diagnosis

API 的 202 rate 正常，但大量 jobs 永遠 pending。哪兩項最有效？（選兩項）

A. 用 job ID 追蹤 acceptance→queue→receive/in-flight→downstream→result write→status transition→notification
B. 先把 worker concurrency 加倍，未確認 database/service quota、throttling、in-flight 與 poison jobs
C. 提高 queue retention，保住較長調查與 redrive 窗口，但不追蹤 job 狀態轉移
D. 只抽樣已完成 jobs 的 successful traces，以降低 observability 成本
E. 對 job age/state-transition latency、queue age、worker errors、DLQ 建立告警

**答案：A、E**

- **A：** 正確。這條 causal path 能定位工作在哪一站消失或卡住。
- **B：** 錯誤。若證據顯示 worker capacity 不足且下游仍有餘裕，增加 concurrency 才合理；未先定位就擴大並行可能加劇 throttling 或失敗重試。
- **C：** 錯誤。延長 retention 能保存 recovery window，適合調查需要更久時使用；但它不會指出 job 卡在哪個 state，也不會修復遺漏的 transition。
- **D：** 錯誤。成功 trace 可驗證正常路徑，卻會系統性漏掉永遠 pending 的工作；應以 job ID 與 age-based sampling 保留失敗和未完成路徑。
- **E：** 正確。跨階段 age/error signals 能在使用者投訴前發現 stuck jobs。

**事實查證：** [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)、[Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)、[SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)

### 練習題 10｜SAP｜Stateful monolith migration

如何把 sticky-session monolith 漸進改為可水平擴展架構？

A. 先停用 stickiness，再處理 state loss
B. 所有同步路徑一次改成 events
C. 把所有 state 放同一 NFS，不評估 locks/throughput
D. 盤點 state owner，逐步外部化 sessions/files/jobs，導入 idempotent APIs 與必要 async boundary，canary stateless instances，failover 測試後移除 stickiness

**答案：D**

- **A：** 錯誤。現有 requests 會立即失去 local sessions。
- **B：** 錯誤。Big-bang 會同時改變 consistency 與 failure semantics。
- **C：** 錯誤。共享 filesystem 不是所有 state 的通用答案。
- **D：** 正確。先理解 state，再以可逆步驟遷移並用 failure test 證明。

**事實查證：** [SAP-C02 Domain 4: Accelerate Workload Migration and Modernization](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)、[REL05-BP06 Make systems stateless where possible](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html)、[REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「可重建compute保持stateless；durable state交給專用store；長工作透過asy…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「架構需要明確知道state owner與等待關係，才能安全scale與failover。」，所以「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」能直接滿足它；若constraint改成「同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」。替代方案「同步適合需要立即結果且延遲可控；非同步適合吸收burst與解耦可用性。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「架構需要明確知道state owner與等待關係，才能安全scale與failover。」，排除會導致「把session鎖在單instance，或將需要立即一致結果的交易全部改成eventual async。」的選項，再選「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「可重建compute保持stateless；durable state交給專用store；長工作透過async queue回傳job ID。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「state placement determines scaling and failure behavior」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
