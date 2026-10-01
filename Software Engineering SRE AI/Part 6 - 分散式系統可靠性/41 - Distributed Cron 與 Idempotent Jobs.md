---
chapter: 41
title: Distributed Cron、Leases 與 Idempotent Jobs
part: 6
---

# 第 41 章　Distributed Cron、Leases 與 Idempotent Jobs

> [!abstract] 本章地圖
> **核心問題**：定期執行的工作搬到多台機器上之後，要怎麼做到「該跑的不漏跑、不該重複的不重複」，而且在機器當機、process 停頓、網路分割時依然成立？
>
> **你會學到**：
> - 說出單機 cron 的隱含假設，以及這些假設在分散式環境中如何造成漏跑、重跑與重疊執行
> - 區分 at-most-once、at-least-once 與 exactly-once，並依工作性質選擇「寧可漏跑」或「寧可重跑」
> - 用確定性的 idempotency key、唯一約束與狀態機條件寫入，讓重試變得無害
> - 設計一個用 leader election、lease 與 fencing token 保護的排程與 worker 架構
> - 保存 job 狀態、設定 checkpoint 與補跑策略，並避開午夜的 thundering herd
> - 用「上次成功時間」與對帳，偵測排程系統自己看不到的漏跑與重複
>
> **前置知識**：第 39 章（retry、backoff 與 deadline）、第 40 章（leader election、lease、fencing token）
>
> **對應原書**：SRE 第 24 章〈Distributed Periodic Scheduling with Cron〉

## 41.1 故事：沒撥款的那一天，和撥了兩次的那一天

Harbor 的賣家每天凌晨可以收到前一天的銷售撥款。負責這件事的是一支叫 `seller_payout` 的程式，跑在一台叫 `batch-01` 的虛擬機上，crontab 裡只有一行：每天 02:00 執行。它跑了三年，沒人想過它。

十月中的某個凌晨，雲端供應商排程更新主機，`batch-01` 在 01:55 被重新開機，02:10 才回來。cron 只在「時間到了且自己醒著」時啟動工作；它醒來時已經過了 02:00，那一天的撥款就這樣沒有發生。沒有任何告警響，因為沒有東西「失敗」：程式根本沒被啟動。直到早上九點，客服開始接到賣家的電話，才有人發現。

檢討會上，大家的結論是「單一機器不可靠」。platform 團隊的工程師把同一份 crontab 也裝到 `batch-02`，兩台互為備援。這個改動通過了 code review，因為看起來非常合理。`batch-02` 不屬於第 36 章那批「雙十一前三天預先擴容」的線上服務，上線時程一路被雙十一的準備工作往後擠，11 月 11 日白天才正式上線。

漏撥之後大約一個月，雙十一隔天（11 月 12 日）凌晨 02:00，是兩台機器第一次同時在線迎接排程時間。它們準時各自啟動了一次 `seller_payout`。那天是 Harbor 一年中撥款金額最大的一天，選擇「每日撥款」方案的 1,800 位賣家每人收到兩筆撥款，溢付金額超過新台幣兩千萬元（其他賣家採每週撥款，逃過一劫）。更麻煩的是收回：錢已經進了賣家的銀行帳戶，Harbor 必須一一聯絡、請求退回，部分賣家已經把錢拿去進貨。產品經理 Lisa 在事故頻道裡寫下一句話：「漏撥我們可以隔天補，多撥我們不一定拿得回來。」

SRE 志明後來在 postmortem 裡記下真正的問題：團隊把「讓工作一定會被執行」和「讓工作只被執行一次」當成同一件事，而它們在分散式環境中正好互相拉扯。這一章要講的就是怎麼同時處理兩者：用 lease 與 leader 決定誰來跑，用 idempotency 讓重複無害，用狀態保存與對帳抓出漏掉的那一次。

## 41.2 Cron 的隱含假設

### 單機 cron 怎麼運作

**Cron** 是 Unix 系統上的定期排程工具。背景程式 `crond` 讀取 **crontab**（排程表），每分鐘檢查一次有沒有到時間的工作，有就啟動。crontab 的時間欄位依序是「分、時、日、月、星期」：

| 寫法 | 意思 |
|---|---|
| `0 2 * * *` | 每天 02:00 |
| `*/5 * * * *` | 每 5 分鐘 |
| `30 9 * * 1` | 每週一 09:30 |
| `0 0 1 * *` | 每月 1 日 00:00 |

SRE 書指出單機 cron 在可靠性上的幾個特性：它的故障範圍就是一台機器，機器不在，排程和工作都不會發生；它唯一需要跨重啟保存的狀態是 crontab 本身；它的啟動是「fire-and-forget」（射後不理），不追蹤工作有沒有成功。一個例外是 **anacron**：它記錄每個工作上次啟動的時間，開機後會補跑關機期間錯過的每日（或更低頻率）工作，這對常關機的筆電很實用。

### 五個沒寫出來的假設

`seller_payout` 那一行 crontab 背後，藏著五個沒人寫下來的假設：

1. **機器一直開著。** 機器在排定時間不在，工作就不會跑，而且沒有人知道。
2. **只有一台機器。** 同一個 crontab 放在兩台機器，就有兩個排程器，各自覺得自己該執行。
3. **工作在下一次排程前會結束。** 每小時跑一次的對帳如果某天跑了 70 分鐘，下一次就會和它重疊，兩份 process 同時改同一份資料。
4. **時鐘與時區正確。** 伺服器若設成 UTC，`0 2 * * *` 其實是台灣時間上午 10:00。如果 Harbor 擴展到有日光節約時間（DST）的地區，排在切換時段的工作會出問題：例如在中歐時區，春天切換那天的 02:30 根本不存在，秋天切換那天的 02:30 會出現兩次。
5. **失敗會有人看到。** Cron 不追蹤結果；工作失敗或根本沒啟動，都不會自動通知任何人。

在一台機器上，這些假設大多數時候成立，偶爾不成立的代價也不大。但當工作從「清理暫存檔」變成「撥款給 1,800 位賣家」，每一個假設都需要被明確處理。

### 分散式環境多了什麼問題

把排程搬到多台機器（或像 Kubernetes 這樣的排程平台）上，又會多出幾種失敗：

```text
排程器              datacenter scheduler／平台           worker
   │  ① 決定啟動            │                              │
   │ ─────────────────────► │  ② 分配機器、拉映像、啟動     │
   │                        │ ───────────────────────────► │ ③ 執行副作用
   │                        │                              │   （撥款、寄信）
   │  ⑤ 記錄「已完成」       │ ◄──── ④ 回報結果 ──────────── │
   ▼                        ▼                              ▼
 任何一個箭頭都可能遺失；任何一個方框都可能在兩個步驟之間當機
```

① 到 ② 之間排程器當機，工作沒被啟動（漏跑）。② 成功但回應遺失，排程器以為失敗而再啟動一次（重跑）。③ 做到一半 worker 被殺，副作用只完成一部分（部分完成）。③ 完成但 ④ 或 ⑤ 遺失，系統不知道它已經做過，下一個 worker 又做一次（重複副作用）。SRE 書描述 Google 的 cron 時也特別提到這種**部分失敗**：在資料中心啟動一個工作可能需要多個 RPC，送出 RPC 的 process 可能在中途死掉，結果有些 RPC 成功、有些沒有。

這些問題沒有一個能靠「多加一台機器」解決；多加一台機器只會把「漏跑」換成「重跑」，Harbor 已經用兩千萬元驗證過這件事。

## 41.3 At-most-once、at-least-once 與 exactly-once

### 三種傳遞語意

面對「訊息或動作可能遺失或重複」的世界，系統只能在三種保證中選擇：

- **At-most-once**（最多一次）：每個動作最多執行一次，可能是零次。做法是「送出後不重試」。適合漏掉無妨、重複有害的事，例如行銷推播。
- **At-least-once**（至少一次）：每個動作至少執行一次，可能更多次。做法是「沒收到確認就重試」。適合不能漏掉的事，但要求重複執行是安全的。
- **Exactly-once**（恰好一次）：每個動作恰好執行一次。這是大家都想要的，但在會當機、會遺失訊息的系統裡，**無法單靠傳遞機制達成**。

為什麼 exactly-once 做不到？看這個時間線：

```text
worker:  讀取「尚未撥款」──► 呼叫金流商撥款 ──► 💥 crash ──╳── 寫入「已撥款」
                                   │
金流商:                            └── 款項已送出 ✓

新 worker 接手：看到「尚未撥款」→ 再撥一次？還是不撥？
```

副作用（撥款）和紀錄（寫入「已撥款」）發生在兩個不同的系統，中間永遠有一個縫隙。worker 在縫隙裡當機，新的 worker 從紀錄上看到的是「沒做」，但現實世界裡已經做了。把順序反過來（先寫「已撥款」再呼叫金流商）只是把縫隙換到另一邊：紀錄說做了，現實中沒做。

實務上所謂的 exactly-once，其實是 **effectively-once**（效果上恰好一次）：**用 at-least-once 確保不漏，再讓副作用 idempotent，使重複執行的效果和執行一次相同**。有些訊息系統能在系統內部提供 exactly-once 的處理語意：例如 Kafka 的官方文件說明，Kafka Streams 或「transactional producer 搭配 read-committed 的 consumer」可以在「從 Kafka topic 讀取、處理、再寫回 Kafka topic」這段做到 exactly-once；但寫到其他目的系統時，通常需要那個系統配合。一旦副作用離開那個系統（寄信、呼叫金流），保證就不再涵蓋，還是要回到 idempotency。

### 寧可漏跑，還是寧可重跑

SRE 書描述 Google 分散式 cron 的設計取向時說得很清楚：在基礎設施允許的範圍內，**他們傾向寧可跳過一次啟動，也不冒重複啟動的風險**，也就是「fail closed」。理由是漏跑比較容易補救：工作的 owner 可以（也應該）監控自己的工作，發現漏跑後依工作性質補跑；但重複啟動，例如寄出兩次電子報，可能很難甚至完全無法撤銷。

這個取向是排程系統的預設值，不是每個工作的答案。SRE 書用兩個維度區分工作，Harbor 照著把自己的工作分類：

| 工作 | 漏跑一次的後果 | 重跑一次的後果 | 選擇 |
|---|---|---|---|
| 每 5 分鐘清理過期 session | 下次再清，無妨 | 無妨（本身 idempotent） | 任意，不需特別保護 |
| 每晚寄出「購物車提醒」信 | 少一次行銷，可接受 | 客人收到兩封，抱怨 | At-most-once：寧可漏 |
| 每晚賣家撥款 | 賣家沒拿到錢，必須補 | 溢付，難以收回 | At-least-once + idempotency + 對帳 |
| 每月開立發票 | 違反法規，必須補 | 重複發票，需作廢 | At-least-once + idempotency + 對帳 |
| 每小時重建搜尋索引 | 索引晚一小時 | 浪費運算資源 | At-least-once，限制同時只有一份 |

表格最後一欄的選擇，必須由**工作的 owner**決定並寫進工作的設定或文件，排程平台無法替所有工作猜對。最危險的是「漏跑和重跑都不能接受」的那一類（撥款、發票、薪資），它們需要本章後面的全套工具。

> [!warning] 常見誤解
> 「我們的佇列（或排程平台）保證 exactly-once，所以程式不用管重複。」請先找出那份保證的範圍：通常它只涵蓋「訊息在系統內被標記為已處理」這一段，不涵蓋你的程式在處理過程中對外部世界做的事。只要你的 worker 會在副作用完成後、確認送出前當機，重複就可能發生。

## 41.4 Idempotency：讓重複變得無害

### 定義與直覺

一個操作是 **idempotent**（冪等）的，如果執行一次和執行很多次的效果相同。數學寫法是 f(f(x)) = f(x)。

有些操作天生 idempotent，有些天生不是：

| 天生 idempotent | 天生不 idempotent |
|---|---|
| 把訂單狀態設為「已出貨」 | 把庫存減 1 |
| 把賣家 7 的 11/12 撥款金額設為 12,000 | 對賣家 7 轉帳 12,000 |
| 刪除某個暫存檔 | 寄一封信 |
| 用固定名稱建立一個資源（已存在就跳過） | 用隨機名稱建立一個資源 |

規律是：**「設定成某個狀態」通常 idempotent；「做一個動作」或「相對地改變」通常不是**。設計 idempotent job 的核心技巧，就是把「做一個動作」改寫成「確保某個狀態成立」，例如把「對賣家 7 轉帳」改寫成「確保賣家 7 的 11/12 撥款存在且只存在一筆」。

### Idempotency key：給每一個「業務上的動作」一個名字

要讓不 idempotent 的動作變得可安全重試，最常用的工具是 **idempotency key**（冪等鍵）：呼叫方為每一個業務上的動作產生一個唯一名稱，隨請求一起送出；接收方記住處理過的名稱，同一個名稱再來時，不重做，直接回傳第一次的結果。許多金流 API 都支援這種設計，例如 Stripe 的 API 在 POST 請求上接受 `Idempotency-Key` header：它會保存同一把 key 第一次請求的狀態碼與回應內容（不論成功或失敗），之後同一把 key 的請求都回傳同樣的結果。

Idempotency key 最容易出錯的地方，是**它怎麼產生**：

```text
✗ 每次嘗試都呼叫 uuid4()                每次嘗試都不同，重試等於新請求
✗ key = f"payout-{now()}"                 重試時時間變了，key 也變了
✗ key = f"payout-{seller}"                  明天的撥款會被當成今天的重複而被擋掉
✓ key = f"payout:{seller}:{business_date}"  同一賣家、同一營業日的撥款，永遠是同一把 key
```

正確的 key 必須**由業務身分決定（deterministic）**：同一件事不管重試幾次、由哪個 worker 執行，都算出同一把 key；不同的事一定得到不同的 key。隨機 UUID 本身不是問題，Stripe 的文件甚至建議用 V4 UUID 當 key；問題在於「每次嘗試都重新產生」。如果要用 UUID，必須在第一次呼叫之前就把它和業務紀錄一起存進資料庫（例如寫進狀態為 PENDING 的撥款列），之後所有重試都讀出同一個值。對定期工作來說，「排定的執行時間」幾乎永遠是 key 的一部分。SRE 書在描述 Google cron 時強調同一件事：光是識別「哪個 cron job」不夠，還要用排定的啟動時間識別「哪一次啟動」，否則每分鐘執行的工作會無法分辨兩次啟動。

實務上還有幾個細節：

- **範圍**：key 要以呼叫方或租戶為範圍，避免不同系統剛好用到相同字串。
- **請求內容比對**：同一把 key 送來不同的內容（例如金額不同），應該回傳錯誤，而不是靜默地回傳舊結果。這通常代表呼叫方有 bug。
- **保存多久**：接收方要把 key 保存得比「最長可能的重試間隔」更久。以 Stripe 為例，文件說明 key 存在至少 24 小時後就可能被清除，之後重用同一把 key 會被當成新請求。若某個工作三天後才補跑，金流商端的保護就已經失效，必須靠自己資料庫裡的紀錄與補跑前的對帳。
- **儲存結果，不只儲存「見過」**：重送時回傳第一次的結果（例如交易編號），呼叫方才能正確地記錄完成。

### 在自己的資料庫裡做到 idempotency

當副作用是寫入自己的資料庫時，有三種常用手法：

**唯一約束**。在撥款表上建立 `(business_date, seller_id)` 的唯一鍵，第二次插入會失敗，程式把「違反唯一約束」視為「已經做過」。這是最簡單也最可靠的方法，因為檢查由資料庫原子地完成。

**狀態機條件寫入**。把工作狀態寫成明確的轉移，並在 UPDATE 的條件中要求「目前狀態」：

```text
UPDATE payouts SET status = 'SENT', provider_tx = :tx
 WHERE id = :id AND status = 'PENDING';
-- 影響 0 列：別人已經處理過，或狀態不對，不要再做
```

**Transactional outbox**（交易性寄件匣）。如果工作需要「更新資料庫」並「通知外部系統」，在同一個資料庫交易中，同時寫入業務資料與一筆「待送出的訊息」到 outbox 表；另一個 publisher 程式持續讀取 outbox、送出訊息、標記已送出。資料庫交易保證兩者同時成功或同時失敗；publisher 可能重送，所以接收端仍需 idempotency，但至少不會出現「資料改了、通知沒發」或反過來的情況。

### 外部系統不支援 idempotency 時

如果外部系統既不接受 idempotency key，也無法用自己的資料庫保護，SRE 書給的條件是：**重試前，至少要能滿足其中之一**：

1. 所有可能需要重做的外部操作都是 idempotent 的；或
2. 能夠查詢外部系統的狀態，明確判斷某個操作是否已經完成。

第二種的典型做法是**預先決定名稱**。Google 的 cron 在啟動工作前，先依「工作名稱 + 排定的啟動時間」算好要在 datacenter scheduler 上使用的 job 名稱，並把這些名稱同步給所有 replica。leader 在啟動途中死掉，新的 leader 只要查詢這些預先算好的名稱是否存在，就知道哪些已經啟動、哪些還沒有，只補啟動缺少的部分。SRE 書還特別提到：名稱中一定要包含排定的啟動時間，否則一個執行很快的工作在 failover 期間已經跑完，新 leader 看到「這個工作已完成」，會無法分辨那是「這一次」還是「上一次」，進而重複啟動。

如果兩者都做不到，就只剩下事後對帳（41.8 節）與人工處理。這時要在設計文件中明確寫下這個風險，而不是假裝它不存在。

## 41.5 Lease、leader 與重疊執行

### 誰來決定「現在該跑了」

Idempotency 讓重複無害，但重複仍然浪費資源，而且不是每個副作用都能做成 idempotent。所以我們仍然希望**同一時間只有一個排程器在決定啟動**。這正是第 40 章的 leader election 問題。

SRE 書描述的 Google 分散式 cron 架構大致如下：

```text
        ┌───────────── Paxos 群組（cron 的 replicas）─────────────┐
        │                                                       │
        │  ┌──────────┐      同步複製狀態       ┌──────────┐      │
        │  │  Leader  │ ─────────────────────► │ Follower │ …    │
        │  └────┬─────┘                        └──────────┘      │
        │       │ ① 寫入「即將啟動 job X @ 02:00」並等 quorum 確認  │
        └───────┼───────────────────────────────────────────────┘
                ▼
        ② 依預先算好的名稱，向 datacenter scheduler 啟動 job X@02:00
                │
                ▼
        ③ 寫入「job X @ 02:00 啟動結束」並等 quorum 確認
```

幾個關鍵設計：

- **只有 leader 能修改共享狀態、能啟動工作。** follower 只追蹤狀態，隨時準備接手。
- **啟動前後各有一個同步點。** leader 必須等 quorum 確認「即將啟動」之後才真的啟動，結束後也同步記錄「啟動結束」。如果不同步，leader 可能在 follower 不知情的情況下啟動了工作，接著當機，新 leader 會再啟動一次。
- **新 leader 必須先收尾。** 所有「已開始、未結束」的啟動（open launches）都要先用 41.4 節的查詢或 idempotency 確認結果，才繼續正常排程。
- **失去領導權就立刻停手。** leader 一旦失去 leader 身分，必須立即停止和 datacenter scheduler 互動，否則新舊 leader 可能做出衝突的動作。
- **選舉要比最小排程間隔快。** 最小的排程單位是一分鐘，所以 failover 必須在一分鐘內完成，否則就會漏跑或嚴重延遲。

Harbor 不需要自己實作 Paxos。他們的做法是：排程器跑 3 個 replica，用 etcd 的 lease 選 leader（第 40 章）；每一次「排定的執行」都在資料庫的 `job_runs` 表中有一列，主鍵是 `(job_name, scheduled_time)`，由 leader 在啟動前寫入。即使兩個排程器同時以為自己是 leader，唯一約束也只會讓其中一個成功建立那一列。

### Worker 的 lease 與 fencing

排程器決定了「要跑」之後，實際執行的 worker 也需要保護：worker 可能跑到一半當機，需要別人接手；也可能只是停頓，之後醒來繼續做。這和第 40 章的舊 leader 問題完全相同，解法也相同：

1. Worker 以條件寫入「認領」一個 run，取得一個 **lease**（例如 60 秒）與一個遞增的 **fencing token**。
2. 執行期間定期**續約**（heartbeat），例如每 20 秒一次。續約間隔要遠小於 lease 長度，才能容忍幾次續約失敗。
3. Worker 對外部資源的每個寫入都帶 token；資源（或 `job_runs` 表）拒絕比目前 token 小的請求。
4. Lease 過期而 run 未完成，另一個 worker 可以重新認領，拿到更大的 token。
5. 續約失敗時，worker 要**主動中止**，不要「把這批做完再說」。

Lease 長度是一個取捨：太短，GC 停頓或網路抖動就會讓 lease 失效，造成不必要的接手；太長，worker 真的當機時，要等很久才有人接手。常見的經驗法則是讓 lease 約為續約間隔的 3 倍，並確保它遠大於系統中常見的停頓時間；這不是標準，具體數字要依自己系統觀察到的停頓與網路狀況調整。

### 重疊執行：上一次還沒跑完，下一次又到了

**重疊執行**是另一種重複：不是同一次被執行兩次，而是第 N 次還沒結束，第 N+1 次就開始了。雙十一的訂單量是平常的好幾倍，Harbor 每小時一次的庫存對帳那天跑了 85 分鐘，下一次在第 60 分鐘啟動，兩份程式同時修正同一批差異，有些修正被套用了兩次。

對策是讓每個工作明確宣告它的**並行政策**。Kubernetes 的 CronJob 就提供這個設定（`concurrencyPolicy`），而且預設值是 Allow，也就是不設定就允許重疊：

| 政策 | 行為 | 適合 |
|---|---|---|
| Allow | 允許多份同時執行 | 每次處理的資料互不重疊的工作 |
| Forbid | 上一次還在跑，就跳過這一次 | 對帳、修復這類會互相干擾的工作 |
| Replace | 終止上一次，啟動新的這一次 | 只有最新一次才有意義的工作，例如重建快取 |

這些政策只管同一個 CronJob 建立的 Job；兩個不同的 CronJob 做同一件事，仍然會同時執行。Kubernetes 還有 `startingDeadlineSeconds`：某一次執行因為任何原因錯過排定時間、而且延遲超過這個秒數，那一次就被跳過（並視為失敗的 Job），之後的排程照常進行。這是一個把「漏跑還是遲跑」的選擇寫進設定的例子。

Kubernetes 文件也坦白說明 CronJob 的排程是「大約」每個時間點建立一個 Job：在某些情況下可能建立兩個，也可能一個都沒建立，所以它要求 Job 本身應該是 idempotent 的。換句話說，即使用了成熟的排程平台，本章的 idempotency 與對帳仍然必要。

> [!tip] 長時間的工作
> 一個工作如果經常接近或超過自己的排程間隔，與其調整並行政策，不如重新設計：把它拆成可以平行處理的分片、改成持續運作的 pipeline（第 42 章），或者把排程間隔改長。並行政策只是安全網，不是容量規劃。

## 41.6 Job 狀態保存：run ledger、checkpoint 與補跑

### 每一次執行都要留下紀錄

單機 cron 不追蹤執行結果，分散式排程必須追蹤。Harbor 的 `job_runs` 表（稱為 **run ledger**，執行帳本）為每一次排定的執行保存一列，狀態轉移如下：

```text
           leader 建立                 worker 認領（取得 token）
SCHEDULED ─────────────► PENDING ─────────────────────────► RUNNING
                            ▲                                 │  │  │
                            │      lease 過期、未完成            │  │  │
                            └─────────────────────────────────┘  │  │
                                                                 │  │
                             成功：寫入結果摘要                   ▼  │
                                                         SUCCEEDED │
                             失敗且還有重試次數 → 回到 PENDING（backoff） │
                             超過重試上限                           ▼
                                                              FAILED → 通知 owner
```

每一列至少記錄：`job_name`、`scheduled_time`（兩者合起來是 run 的唯一識別）、狀態、目前的 owner 與 fencing token、lease 到期時間、嘗試次數、開始與結束時間、結果摘要（例如「撥款 1,800 筆、合計 NT$ X」）。這份紀錄同時是排程系統的狀態、值班者的除錯起點，也是對帳的依據。

SRE 書提到 Google cron 的狀態其實很小，所以他們把它存在 cron 服務自己的 Paxos 群組裡（log 放在 replica 所在機器的本機磁碟），而不是依賴一個外部的大型分散式檔案系統。理由有兩個：分散式檔案系統是為大檔案設計的，小量寫入既昂貴又慢；而且 cron 這種基礎服務的依賴越少越好，才能在資料中心部分故障時照常運作。Paxos 的 log 會持續增長，所以要定期做**快照**（snapshot），把「加 1、加 1、加 1」壓縮成「目前是 1,000」。快照是最關鍵的狀態：遺失 log 只會讓系統回到上一次快照的時間點，遺失快照則等於從零開始，所以他們把快照另外備份到分散式檔案系統。

### Checkpoint：長工作不要從頭重來

`seller_payout` 處理 1,800 位賣家，如果在第 1,200 位時當機，重試時從頭開始雖然安全（有 idempotency key 保護），但會浪費時間，而且對外部系統造成不必要的重複請求。**Checkpoint**（檢查點）是在工作過程中定期記錄「已經安全完成到哪裡」，例如「已處理 seller_id ≤ 4821」。重試時從 checkpoint 之後繼續。

Checkpoint 必須在副作用**確實完成之後**才寫入，而且 checkpoint 之後的那一小段仍然可能重做，所以它不能取代 idempotency，只是減少重做的量。

### 重試、上限與 poison job

失敗的 run 應該重試，但要遵守第 39 章的規則：**exponential backoff 加 jitter、設定重試上限、尊重 deadline**。一個每次都會失敗的 run（例如某位賣家的銀行帳號格式錯誤，每次都讓程式拋出例外），叫做 **poison job**（毒藥工作）。如果無限重試，它會一直佔用 worker；如果它讓整批工作失敗，其他 1,799 位賣家也拿不到錢。

比較好的設計是把工作拆到「單一賣家」的粒度：每位賣家的撥款各自成功或失敗，失敗的進入 **dead-letter**（死信，無法處理的項目另外存放的區域）等人處理，其他人照常完成。

### 補跑策略：錯過了要怎麼辦

排程系統停擺一段時間（例如 leader 失效、平台升級）後恢復，面對錯過的執行有三種選擇：

| 策略 | 行為 | 適合 |
|---|---|---|
| 全部補跑 | 每一個錯過的時間點都執行一次 | 每次處理不同時間區間的資料，例如每小時的帳務彙總 |
| 只跑一次 | 錯過幾次都只補一次最新的 | 只在乎「最新狀態」的工作，例如重建索引 |
| 跳過 | 錯過就算了，等下一次 | 高頻、漏一次無妨的工作，例如每 5 分鐘清理 |

「全部補跑」要注意 thundering herd：停擺 6 小時後恢復，所有每小時工作會一次補 6 次。補跑也要受同時執行數量的限制。

要先弄清楚你用的平台預設是哪一種。以 Kubernetes CronJob 為例，它不會把每一個錯過的時間點都補跑；而且控制器計算錯過的次數時，如果超過 100 次（例如每分鐘一次的工作、控制器停了兩個小時，又沒有設定 `startingDeadlineSeconds`），就不啟動 Job，只記錄一筆「too many missed start times」錯誤。設定 `startingDeadlineSeconds` 後，控制器只計算這段時間內錯過的次數，才能在恢復後正常啟動。

**Backfill**（回補）是更大範圍的補跑，例如修正 bug 後重新計算過去 30 天的資料。因為每一次 run 都用 `(job_name, scheduled_time)` 識別，且副作用是 idempotent 的，backfill 只是「對一段時間範圍的 run 重新執行」，不需要寫一次性的特殊腳本。這是 idempotent 設計帶來的一個額外好處。

## 41.7 排程的 thundering herd

**Thundering herd**（驚群效應）是指大量的請求或工作在同一個瞬間湧向同一個資源。在排程系統中，它最常見的來源是人類的習慣：說到「每天跑一次」，幾乎每個人都會寫 `0 0 * * *`，也就是午夜整點。

SRE 書描述的情況是：如果一個每日工作會啟動一個有數千個 worker 的 MapReduce，而同一個資料中心有 30 個團隊都把每日工作排在午夜，資料中心在午夜那一刻就會出現巨大的尖峰。Harbor 也遇過類似的事：十幾個團隊的每日報表、資料匯出與清理工作都在 00:00 啟動，同時打向同一個資料倉儲與同一個金流商的查詢 API，金流商的 rate limit 被觸發，連帶讓 00:00 剛好在付款的使用者失敗。

Google 的解法是擴充 crontab 語法，加入「?」：表示「這個欄位任何值都可以，讓系統選」。系統把工作的設定做 hash，在允許的範圍內（例如 0..23 小時）選一個值。因為 hash 是確定性的，同一個工作每天都在同一個時間執行，但不同工作會分散開來。Jenkins 的 `H` 語法（例如 `H H * * *`）也是同樣的概念：`H` 代表 hash，Jenkins 文件說明它取的是 job 名稱的 hash 而不是隨機值，所以每個工作的時間固定，不同工作則分散開來。

```text
啟動數                                    啟動數
 30 │ █                                     30 │
    │ █                                        │
    │ █                                        │
    │ █                                        │
  3 │ █                                      3 │ ▃  ▃ ▃▃ ▃  ▃ ▃ ▃▃ ▃ ▃  ▃ ▃▃ ▃ ▃▃ ▃ ▃
    └─┴──────────────────── 時間                └─┴──┴─┴┴─┴──┴─┴─┴┴─┴─┴──┴─┴┴─┴─┴┴─┴─┴─ 時間
     00:00                                      00:00                          00:59
     全部寫 0 0 * * *                          依工作名稱 hash 分散到一小時內
```

左圖是所有工作擠在同一分鐘；右圖是依名稱 hash 分散到一小時內，每分鐘只有零到幾個。分散不需要隨機：用 hash 而非 random，工作的執行時間才可以預期、才能寫進文件與告警。

分散啟動時間之外，還有幾個配套：

- **在工作內部加 jitter**：分片執行的工作，每個分片啟動時再加幾秒到幾分鐘的隨機延遲。
- **限制同時啟動數**：排程器對同一個下游（資料倉儲、金流商 API）設定最大並行數，超過就排隊。
- **把下游的容量當成輸入**：每日工作的總量要能被下游的離峰容量吸收，這是容量規劃的一部分（第 36 章）。

SRE 書也誠實地指出：即使有了「?」，Google 的 cron 啟動數仍然很尖，因為很多工作有必須在特定時間執行的理由（例如依賴外部事件）。分散化只能處理「其實沒有理由在整點」的那一部分，剩下的要靠容量與限流。

## 41.8 監控與對帳：抓出排程系統自己看不到的錯

### 「上次成功」比「這次失敗」更重要

Harbor 十月的漏撥沒有觸發任何告警，因為大部分監控都在等「失敗事件」，而漏跑根本不會產生事件。對定期工作，最重要的指標是**距離上次成功完成過了多久**：

```text
告警條件：now − last_success_time > 排程間隔 + 預期執行時間 + 寬限
例：每日 02:00 執行、通常 40 分鐘完成，上次成功是昨天 02:40
    間隔 24 小時 ＋ 預期執行 40 分鐘 ＋ 寬限 40 分鐘
    → 今天 04:00 仍未見新的成功，就告警
```

這種「沒有收到預期的訊號就告警」的設計叫 **dead man's switch**（死人開關）：工作每次成功就回報一次心跳，監控系統在心跳停止時告警。它能抓到所有導致「沒有成功」的原因：工作失敗、沒被啟動、排程器掛了、甚至整台機器不見了。

其他值得監控的指標：

| 指標 | 用途 |
|---|---|
| 排程延遲（實際開始 − 排定時間） | 平台資源不足、排程器 failover 過慢 |
| 執行時間與排程間隔的比值 | 接近 1 時，重疊執行即將發生 |
| 嘗試次數、重試比例 | 下游不穩或 poison job |
| 被跳過與被重疊的次數 | 並行政策正在發揮作用，背後可能有容量問題 |
| Lease 被接手的次數 | Worker 不穩或 lease 太短 |
| Dead-letter 數量 | 需要人處理的項目 |

這些指標可以直接變成批次工作的 SLO（第 32 章），例如「99% 的營業日，賣家撥款在 06:00 前完成」。

### 對帳：最後一道防線

排程系統的紀錄只能說明「排程系統以為發生了什麼」。真正的問題是「現實世界發生了什麼」。**Reconciliation**（對帳）是一個獨立的工作，從多個來源比對應有的結果與實際的結果：

```text
應該發生的：昨日有銷售的每日撥款賣家（訂單資料庫）── 1,800 位
系統紀錄的：job_runs 與 payouts 表               ── 1,800 筆 SENT
現實發生的：金流商當日撥款報表                    ── 1,800 筆，金額相符？

差異分類：
  應撥未撥（漏）     → 自動建立補撥 run
  重複撥款（多）     → 立即通知財務與 owner，停止後續相關工作
  金額不符           → 通知 owner
```

對帳必須**不依賴被檢查的系統**：它讀取訂單資料庫與金流商的報表，而不是相信 `seller_payout` 自己寫的紀錄。如果 Harbor 在雙十一前就有這個對帳工作，重複撥款會在當天早上被發現，而不是等賣家打電話來；而十月的漏撥，在 04:00 的 dead man's switch 或早上的對帳中都會被抓到。

對帳本身也是一個定期工作，也需要監控它的「上次成功時間」。監控監控者聽起來像無限迴圈，但實務上只需要兩層：工作本身的 dead man's switch，加上獨立的對帳。

> [!example] Harbor 的修正
> Postmortem 之後，Harbor 把 `seller_payout` 改成：排程器 3 個 replica 透過 etcd 選 leader；每次排定的執行在 `job_runs` 中以 `(job_name, scheduled_time)` 唯一識別；工作拆成每位賣家一個項目，worker 以 lease 與 fencing token 認領；每筆撥款以 `payout:{seller_id}:{business_date}` 作為金流商的 idempotency key；04:00 未完成即 page；08:00 執行對帳，比對訂單、撥款紀錄與金流商報表。兩台機器各裝一份 crontab 的做法被移除。

## 41.9 動手寫：撥款工作的四種情境

下面的程式重現本章的四個情境：兩台機器都裝 crontab 造成的重複撥款；crash 後重試時，隨機 key 與確定性 key 的差別；lease 與 fencing token 擋下停頓後醒來的舊 worker；以及午夜 thundering herd 與 hash 分散。只用標準函式庫，資料庫用 SQLite 的記憶體模式。程式裡的兩位賣家與金額、60 秒的 lease、worker-A 停頓的時間點，以及 30 個每日工作，都是為了示範而假設的參數，不是 Harbor 的實際數據。

```python
import hashlib
import sqlite3
from collections import Counter


# ── 外部金流商：支援 idempotency key（同一把 key 只執行一次，重送回傳上次結果）──
class PaymentProvider:
    def __init__(self):
        self.transfers = []                 # 真正打出去的款項
        self.by_key = {}

    def transfer(self, seller, amount, key=None):
        if key is not None and key in self.by_key:
            return self.by_key[key]         # 重送：不再扣款，回傳第一次的結果
        tx = f"tx-{len(self.transfers) + 1:03d}"
        self.transfers.append((tx, seller, amount))
        if key is not None:
            self.by_key[key] = tx
        return tx


def report(title, provider):
    total = sum(a for _, _, a in provider.transfers)
    print(f"{title}：實際撥款 {len(provider.transfers)} 筆，共 {total:,} 元")


SELLERS = {"seller-7": 12_000, "seller-9": 8_500}
RUN_DATE = "2026-11-12"


# ── Part 1：兩台機器都裝了同一個 crontab ─────────────────
p = PaymentProvider()
for host in ("batch-01", "batch-02"):
    for seller, amount in SELLERS.items():
        p.transfer(seller, amount)
report("情境一 兩台 cron 各跑一次（無保護）", p)


# ── Part 2：撥款後、記錄完成前 crash，然後重試 ──────────────
def payout_run(provider, db, key_fn, crash_after=None):
    for i, (seller, amount) in enumerate(SELLERS.items()):
        done = db.execute("SELECT 1 FROM payout WHERE run_date=? AND seller=?",
                          (RUN_DATE, seller)).fetchone()
        if done:
            continue
        tx = provider.transfer(seller, amount, key=key_fn(seller))
        if crash_after == i:
            raise RuntimeError("worker 在寫入完成紀錄前被 OOM kill")
        db.execute("INSERT INTO payout VALUES (?, ?, ?)", (RUN_DATE, seller, tx))


def fresh_db():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE payout (run_date TEXT, seller TEXT, tx TEXT, "
               "PRIMARY KEY (run_date, seller))")
    return db


for label, key_fn in [
    ("情境二 重試時用隨機 key", lambda s, n=iter(range(100)): f"rand-{next(n)}"),
    ("情境三 重試時用確定性 key", lambda s: f"payout:{s}:{RUN_DATE}"),
]:
    p, db = PaymentProvider(), fresh_db()
    try:
        payout_run(p, db, key_fn, crash_after=0)
    except RuntimeError as e:
        print(f"  ! {e}")
    payout_run(p, db, key_fn)                # 新的 worker 重跑整個 run
    report(label, p)


# ── Part 3：lease + fencing，擋住停頓後醒來的舊 worker ─────
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, state TEXT, owner TEXT, "
           "token INTEGER, lease_until INTEGER)")
db.execute("INSERT INTO runs VALUES ('payout:2026-11-12', 'PENDING', NULL, 0, 0)")
next_token = [0]


def claim(worker, now, ttl=60):
    tok = next_token[0] + 1                  # 真實系統由共識儲存發出遞增的 token
    cur = db.execute("UPDATE runs SET owner=?, token=?, lease_until=?, state='RUNNING' "
                     "WHERE run_id='payout:2026-11-12' AND state!='SUCCEEDED' "
                     "AND lease_until<=?", (worker, tok, now + ttl, now))
    ok = cur.rowcount == 1
    if ok:
        next_token[0] = tok
    print(f"t={now:>3}s {worker} 申請 lease → {'取得，token=' + str(tok) if ok else '失敗（別人持有中）'}")
    return tok if ok else None


def finish(worker, tok, now):
    cur = db.execute("UPDATE runs SET state='SUCCEEDED' WHERE run_id='payout:2026-11-12' "
                     "AND token=?", (tok,))
    ok = cur.rowcount == 1
    print(f"t={now:>3}s {worker} 以 token={tok} 標記完成 → {'成功' if ok else '被拒絕（token 已過期）'}")


print()
t1 = claim("worker-A", now=0)
claim("worker-B", now=30)                    # A 的 lease 還在
print("        worker-A 所在節點被暫停 90 秒……")
t2 = claim("worker-B", now=90)               # lease 已過期，B 接手
finish("worker-B", t2, now=120)
finish("worker-A", t1, now=125)              # A 醒來，想標記完成


# ── Part 4：thundering herd：大家都寫 0 0 * * * ─────────────
jobs = [f"team-{i:02d}-daily-report" for i in range(30)]
naive = Counter(0 for _ in jobs)


def spread_minute(name, window=60):
    h = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    return h % window                        # 同一個 job 每天都落在同一分鐘


spread = Counter(spread_minute(j) for j in jobs)
print(f"\n30 個每日 job：全寫 00:00 → 單一分鐘最多 {max(naive.values())} 個同時啟動")
print(f"依 job 名稱 hash 分散到 00:00–00:59 → 單一分鐘最多 {max(spread.values())} 個，"
      f"用到 {len(spread)} 個不同分鐘")
print(f"team-03 每天固定在 00:{spread_minute(jobs[3]):02d} 執行")
```

執行結果：

```text
情境一 兩台 cron 各跑一次（無保護）：實際撥款 4 筆，共 41,000 元
  ! worker 在寫入完成紀錄前被 OOM kill
情境二 重試時用隨機 key：實際撥款 3 筆，共 32,500 元
  ! worker 在寫入完成紀錄前被 OOM kill
情境三 重試時用確定性 key：實際撥款 2 筆，共 20,500 元

t=  0s worker-A 申請 lease → 取得，token=1
t= 30s worker-B 申請 lease → 失敗（別人持有中）
        worker-A 所在節點被暫停 90 秒……
t= 90s worker-B 申請 lease → 取得，token=2
t=120s worker-B 以 token=2 標記完成 → 成功
t=125s worker-A 以 token=1 標記完成 → 被拒絕（token 已過期）

30 個每日 job：全寫 00:00 → 單一分鐘最多 30 個同時啟動
依 job 名稱 hash 分散到 00:00–00:59 → 單一分鐘最多 3 個，用到 25 個不同分鐘
team-03 每天固定在 00:42 執行
```

逐段解讀：

1. **情境一**：兩位賣家應得 20,500 元，兩台 cron 各跑一次，實際撥出 41,000 元。這就是 Harbor 雙十一隔天的事故，只是規模縮小到兩位賣家。
2. **情境二與情境三**用同一段 `payout_run`：worker 對 seller-7 撥款成功後、寫入 `payout` 表之前被殺掉（`crash_after=0`），接著新的 worker 重跑整個 run。因為 `payout` 表裡沒有 seller-7 的紀錄，重試者一定會再呼叫一次金流商。差別只在 key：隨機 key 讓金流商把重試當成新請求，seller-7 收到兩次錢（32,500 元）；確定性 key `payout:seller-7:2026-11-12` 讓金流商認出這是同一件事，回傳第一次的交易編號，總額正確（20,500 元）。注意 `payout` 表的唯一鍵只保護「自己的紀錄」不重複，保護不了外部的副作用；真正擋下重複撥款的是金流商端的 idempotency key。
3. **Part 3** 用 SQL 條件寫入模擬 lease：`lease_until<=?` 確保只有 lease 過期後才能被別人認領，`token=?` 確保只有目前的持有者能標記完成。worker-A 停頓 90 秒醒來，它的 token 1 已經不是目前的 token，標記完成被拒絕。真實系統中，worker-A 醒來後如果還想繼續撥款，金流商端的 idempotency key 會擋下重複，而 fencing 讓它無法覆蓋 worker-B 寫下的結果。
4. **Part 4** 用 SHA-256 把工作名稱映射到 0–59 分鐘。30 個工作從同一分鐘 30 個，變成每分鐘最多 3 個；而且 hash 是確定性的，`team-03` 每天都在 00:42 執行，可以寫進文件和告警。真實系統還要再加上對下游的並行上限。

在真實系統中，`PaymentProvider.by_key` 對應金流商保存 idempotency key 的資料庫（要保存得比最長重試間隔更久）；`runs` 表對應 run ledger；`next_token` 應由第 40 章的共識系統（例如 etcd 的 revision）發出，而不是由應用程式自己遞增。

## 41.10 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 同一份 crontab 放在多台機器求備援 | 每台都會執行，從漏跑變成重跑 | Harbor 雙十一隔天 1,800 位賣家被重複撥款 | 單一 leader 決定啟動，run 以 `(job, scheduled_time)` 唯一識別 |
| 每次重試產生新的 idempotency key | 重試被當成新請求，保護完全失效 | 用 `uuid4()` 當 key，crash 後重試撥了兩次 | Key 由業務身分與排定時間決定 |
| Idempotency key 保存時間太短 | 晚到的重試或補跑繞過保護 | 金流商端 key 只保存 24 小時，三天後的 backfill 重複撥款 | Key 保存期大於最長重試與補跑區間；補跑前先對帳 |
| Lease 太短 | 一般的 GC 或網路抖動就讓 lease 失效，造成頻繁接手與重做 | Lease 10 秒，worker 在大量寫入時停頓 12 秒 | Lease 約為續約間隔 3 倍，遠大於常見停頓；搭配 fencing |
| Lease 太長 | Worker 真正當機時，要很久才有人接手，工作延誤 | Lease 30 分鐘，撥款延遲到上班時間 | 縮短 lease、提高續約頻率；用 dead man's switch 監控完成時間 |
| 工作越來越慢卻沒有人發現 | 執行時間超過間隔，開始重疊或被跳過 | 雙十一的每小時對帳跑 85 分鐘，修正被套用兩次 | 監控「執行時間／間隔」；設定 Forbid 並行政策；拆分或改成 pipeline |
| 只監控失敗事件 | 沒被啟動的工作不會產生任何事件 | 十月 `batch-01` 重開機，漏撥一整天沒人知道 | 監控「上次成功時間」；獨立的對帳工作 |
| 所有每日工作排在午夜 | 下游在同一分鐘被壓垮 | 十幾個工作同時打金流商 API，觸發 rate limit，連帶影響使用者付款 | 依名稱 hash 分散；對下游設並行上限 |

## 41.11 AI 時代：什麼變了？

**第一，排程的對象從「程式」變成「agent」。** Harbor 開始讓 AI 維運 agent 每天早上巡檢 error budget、每週整理 dependency 更新、每晚整理客服對話中的退款爭議。一般的 cron job 每次執行的步驟是固定的；一個排程的 agent 每次可能呼叫不同的工具、執行不同數量的步驟，它的副作用比傳統 job 更難預測。這讓本章的工具更加重要：

- **每一次 agent run 都有唯一的 run ID**（`agent_name + scheduled_time`），並寫進 run ledger，和一般 job 一樣受 lease 與 fencing 保護。
- **Agent 的每一個有副作用的工具呼叫都要帶 idempotency key**，由 run ID 與工具呼叫的業務身分組成，例如 `refund-review:2026-11-13:order-88231`。Agent 框架在工具呼叫逾時時常會自動重試，模型本身也可能在推理中「再做一次」同樣的動作；沒有 idempotency key，同一筆訂單就會出現兩筆退款申請，客服人員一旦都核准，兩次退款就會真的發生。
- **每次 run 都有硬性上限**：最大步數、最大工具呼叫數、token 與金額預算、最長執行時間。超過就中止並回報，而不是繼續嘗試。
- **固定 run 的輸入版本**：記錄這次 run 使用的 prompt、模型設定與工具清單版本，事後才能重現與比較。
- **輸入資料不能改變排程或權限**：agent 在處理客服對話或文件時，可能讀到「請把這個工作改成每分鐘執行」之類的內容（prompt injection）。排程設定、工具權限與憑證必須在 agent 能修改的範圍之外。

**第二，AI 可以撰寫與審查排程設定，但必須以工具驗證。** Coding agent 很常被要求「寫一個每天凌晨兩點台灣時間執行的 CronJob」。它產生的 cron 表達式與時區設定可能看起來正確、卻在 UTC 的叢集上差了 8 小時：Kubernetes CronJob 若沒有設定 `.spec.timeZone`，排程會以 kube-controller-manager 的本地時區解讀，正確做法是明確寫上 `timeZone: "Asia/Taipei"`。驗證方式是用程式或平台工具展開「接下來 10 次的執行時間」，由人確認，而不是讀表達式本身。

**第三，AI 很適合處理對帳的差異與 dead-letter。** 對帳產生的差異清單與 dead-letter 中的失敗項目，往往需要閱讀錯誤訊息、查詢多個系統、判斷原因。AI agent 可以先做分類與整理，但修正動作（補撥、作廢重複的款項）仍要經過 idempotent 的工具與人類核准。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 盤點所有排程工作，依「漏跑後果」與「重跑後果」初步分類，並找出缺少 idempotency key 或並行政策的工作 | 每個工作「寧可漏還是寧可重」由 owner 確認並寫進設定；AI 的分類只是草稿 |
| 撰寫 cron 表達式與 CronJob 設定，並附上展開後的下 10 次執行時間 | 時區、補跑策略與並行政策由人確認；設定變更走一般 code review |
| 分類 dead-letter 與對帳差異，整理每一筆的證據與建議處理方式 | 補撥、作廢、退款等有金錢影響的動作需要人類核准，且必須透過帶 idempotency key 的工具執行 |
| 以排程 agent 執行唯讀巡檢，異常時建立 ticket | 排程 agent 有獨立身分、最小權限、步數與金額上限；任何 mutating 工具預設關閉，需逐項開放 |
| 分析排程延遲與執行時間的趨勢，提醒哪些工作快要重疊 | 是否拆分工作或改成 pipeline 由 owner 與 SRE 決定 |

> [!ai] AI 提醒
> 要求 AI 寫一個「可以安全重試」的 job 時，檢查它產生的 idempotency key 是怎麼算的。最常見的錯誤是在每次嘗試時才呼叫 `uuid.uuid4()` 或 `datetime.now()`，而沒有把第一次產生的值保存下來重用：程式看起來有 idempotency 的結構，測試也會通過（因為測試通常不模擬 crash 後重試），但在真實的重試中完全沒有保護。寫一個「副作用完成後、紀錄前 crash」的測試，是驗證這件事最直接的方法。

## 41.12 專家怎麼想

- **「漏一次會怎樣？多一次會怎樣？」** 專家看到任何定期工作，第一件事是回答這兩個問題。兩個答案決定了要用 at-most-once、at-least-once 加 idempotency，還是全套保護加對帳；沒有答案就不該上線。
- **Idempotency key 是業務概念，不是技術細節。** 「同一件事」的定義（同一位賣家、同一個營業日）要由懂業務的人確認。key 設計錯，所有重試保護都會失效，或者反過來擋掉不該擋的正常請求。
- **相信對帳，不相信紀錄。** 排程系統的紀錄只能告訴你它以為發生了什麼。資深工程師一定會為重要的工作準備一個獨立、從現實世界讀取資料的對帳。
- **監控「沒發生」比監控「失敗」重要。** 最危險的排程問題是靜默的漏跑。每個重要工作都要有「上次成功時間」的告警。
- **能拆小就拆小。** 一個處理 1,800 位賣家的大工作，不如 1,800 個獨立的小項目：失敗範圍小、可以平行、重試成本低、poison job 不會拖累其他人。
- **排程平台做預設，owner 做決定。** 平台能提供 leader election、run ledger、並行政策與 hash 分散，但每個工作的語意只有 owner 知道。好的平台會強迫 owner 在建立工作時回答這些問題。

## 41.13 動手練習

1. 列出你熟悉的系統（或 Harbor）中的 6 個定期工作，為每一個回答：漏跑一次的後果、重跑一次的後果、選擇的語意（at-most-once 或 at-least-once 加 idempotency）、idempotency key 的組成、並行政策與補跑策略。
2. 修改 41.9 的 Part 2：把 `crash_after` 改成 1（第二位賣家撥款後才 crash），並把 `payout` 表的寫入改成在呼叫金流商之前執行（先記錄、後撥款）。觀察兩種 key 的結果，說明「先記錄」會造成什麼新的問題。
3. 延伸 41.9 的 Part 3：加入續約（`renew`）函式，讓 worker-B 每 20 秒續約一次；再模擬 worker-B 在第 150 秒續約失敗，示範它應該如何主動中止，以及第三個 worker 如何接手。
4. 為 `seller_payout` 設計一個對帳工作：寫出它讀取哪三個資料來源、比對哪些欄位、每一種差異的處理方式，以及它自己的「上次成功時間」告警條件。
5. 盤點你的團隊（或 Harbor）有多少工作排在整點，用 41.9 的 `spread_minute` 為它們重新分配時間，並找出哪些工作確實必須在特定時間執行、原因是什麼。
6. 請 AI coding agent 寫一個每日執行、會呼叫外部 API 的 Kubernetes CronJob 與程式。檢查它的時區、`concurrencyPolicy`、`startingDeadlineSeconds`、idempotency key 的算法與重試邏輯，並補上一個「副作用後 crash」的測試。

## 本章重點整理

- 單機 cron 隱含了機器一直開著、只有一台、工作會準時結束、時鐘正確、失敗有人看到等假設，在分散式環境中這些都不成立。
- 把同一份 crontab 放在多台機器上，只是把「漏跑」換成「重跑」；高可用的排程需要單一 leader 決定啟動。
- 副作用與完成紀錄位於不同系統，中間永遠有縫隙，所以 exactly-once 無法單靠傳遞機制達成；實務上是 at-least-once 加 idempotent 副作用。
- SRE 書描述 Google cron 的預設取向是寧可漏跑也不重複啟動，因為漏跑較容易補救；但每個工作的選擇要由 owner 依「漏一次」與「多一次」的後果決定。
- Idempotency key 必須由業務身分與排定時間確定性地產生；隨機 UUID 或當下時間會讓所有重試保護失效。
- 在自己的資料庫中，用唯一約束、狀態機條件寫入與 transactional outbox 實作 idempotency；外部系統則需要支援 idempotency key，或者能被查詢以判斷操作是否完成。
- Google cron 在啟動前後各用 Paxos 同步記錄一次，新 leader 先收尾未結束的啟動；預先算好、包含排定時間的名稱讓「是否已啟動」可以被查詢。
- Worker 用 lease 認領工作、定期續約、續約失敗就主動中止，並以 fencing token 防止停頓後醒來的舊 worker 覆蓋結果。
- 每個工作要明確宣告並行政策（允許、禁止、取代）與補跑策略（全補、補一次、跳過）。
- Run ledger 以 `(job_name, scheduled_time)` 識別每一次執行，記錄狀態、owner、token、嘗試次數與結果，是排程、除錯與對帳的共同依據。
- 長工作用 checkpoint 減少重做、用細粒度項目與 dead-letter 隔離 poison job，重試遵守 backoff、上限與 deadline。
- 午夜的 thundering herd 可以用依名稱 hash 分散的啟動時間與對下游的並行上限緩解。
- 監控「距離上次成功多久」（dead man's switch）比監控失敗事件更能抓到漏跑；獨立、讀取現實資料的對帳是最後一道防線。
- 排程 agent 需要唯一 run ID、每個工具呼叫的 idempotency key、硬性步數與預算上限，以及不能被輸入資料修改的排程與權限設定。

## 延伸問答

> [!question]- Q1. 為什麼「把同一份 crontab 放到兩台機器上」看起來是在提高可靠性，實際上卻製造了新的事故？
> 這個做法提高的是「工作至少被啟動一次」的機率，但同時讓「工作被啟動兩次」從罕見變成每天必然發生。兩台機器上的 cron 互不知道對方的存在，都會在 02:00 準時啟動；只要工作本身不是 idempotent 的，每天都會重複執行。Harbor 的 `batch-02` 在 11 月 11 日才上線，所以事故發生在它上線後的第一個凌晨，又剛好是一年中撥款金額最大的一天；如果它早一個月上線，重複撥款只會更早、更多次發生。
>
> 正確的高可用設計，是讓多個排程器 replica 透過 leader election 決定只有一個能啟動，並以 `(job_name, scheduled_time)` 作為 run 的唯一識別，讓即使兩個排程器同時以為自己是 leader，也只有一個能成功建立這次 run。同時，撥款這類工作仍然要有 idempotency key 與對帳，因為 leader election 只能減少重複，不能保證副作用不重複。

> [!question]- Q2. 你是 Harbor 的值班者，凌晨 04:00 收到告警：「seller_payout 今日尚未成功完成」。run ledger 顯示今天的 run 狀態是 RUNNING，owner 是 worker-17，lease 已在 03:10 過期。你會怎麼處理？
> 首先確認 worker-17 的實際狀態：它是當機了、被平台移除，還是仍然活著但停頓或卡住？查看該 process 的 log 與平台事件。如果它仍在執行，要先讓它停止，因為它的 lease 已經過期，繼續執行的結果會被 fencing 擋下，卻可能仍對外部系統送出請求。
>
> 接著判斷為什麼 lease 過期後沒有其他 worker 接手：是沒有可用的 worker、認領邏輯有 bug，還是 worker 數量被設為 0。修好後，讓新的 worker 認領這次 run；因為撥款以 `payout:{seller_id}:{business_date}` 作為 idempotency key，且有 checkpoint，重新執行是安全的，會從上次完成的位置附近繼續。完成後檢查對帳結果，確認沒有漏撥或重複。最後在 postmortem 中記錄：lease 過期到告警之間過了 50 分鐘，是否需要對「lease 過期但無人接手」另外設定更早的告警。

> [!question]- Q3. 計算題：Harbor 的 worker 每 20 秒續約一次 lease，lease 長度 60 秒。已知 JVM 的 GC 停頓最長約 8 秒，網路偶爾會讓一次續約失敗。這個設定合理嗎？如果把 lease 改成 15 秒呢？
> 60 秒的 lease 加上 20 秒的續約間隔，代表一次續約失敗後還有約 40 秒的餘裕，第二次續約仍有機會補上；要連續兩次失敗，第三次續約才會落在 lease 到期的邊緣。這足以容忍偶發的網路問題；8 秒的 GC 停頓遠小於 60 秒，不會讓 lease 失效。代價是 worker 真的當機時，最多要等 60 秒才有人接手，對每日撥款這種工作完全可以接受。所以這個設定合理。
>
> 改成 15 秒 lease 時，若續約間隔仍是 20 秒，lease 會在每次續約之前就過期，完全不能用；即使續約間隔改成 5 秒，一次 8 秒的 GC 停頓也可能跨過兩次續約，加上網路抖動，就可能讓 lease 失效、觸發不必要的接手與重做。經驗法則是 lease 約為續約間隔的 3 倍，並且遠大於系統中常見的停頓時間。更短的 lease 只有在「快速接手」的價值很高時才值得，而且一定要搭配 fencing token。

> [!question]- Q4. 同事說：「我們在 payouts 表上建了 (business_date, seller_id) 唯一鍵，所以撥款已經是 idempotent 的了。」這句話對嗎？
> 只對了一半。唯一鍵保證的是 Harbor 自己的 `payouts` 表不會有兩筆同樣的紀錄，但撥款的副作用發生在金流商那邊。如果程式的順序是「先呼叫金流商、再寫入 payouts 表」，那麼在兩者之間 crash，重試時 payouts 表裡沒有紀錄，程式會再呼叫一次金流商，唯一鍵完全來不及發揮作用。如果順序反過來，「先寫入、再呼叫」，crash 後紀錄說已撥款，現實中卻沒有，變成漏撥。
>
> 要真正做到 idempotent，需要把保護延伸到副作用發生的地方：呼叫金流商時帶上確定性的 idempotency key（例如 `payout:{seller_id}:{business_date}`），讓金流商自己擋下重複；如果金流商不支援，就要能用某個識別查詢某筆撥款是否已存在，在重試前先查。唯一鍵是必要的，但它保護的是紀錄，不是副作用。

> [!question]- Q5. 「每天寄一次購物車提醒信」和「每天撥款給賣家」都是每日工作，為什麼前者可以用 at-most-once，後者卻不行？
> 兩者的差別在於漏跑與重跑的後果。購物車提醒是行銷用途，漏寄一天，損失的只是一點可能的轉換率，隔天還會再寄；但重複寄送會讓客人收到兩封一樣的信，造成困擾甚至取消訂閱，而且寄出去的信無法收回。所以「寧可漏、不要重」是合理的選擇，at-most-once 的實作也最簡單：不重試，失敗就算了。
>
> 撥款則是兩邊都不能出錯：漏撥會讓賣家拿不到錢、違反和賣家的約定；重撥則會溢付，收回困難。這類工作必須選 at-least-once 確保不漏，再用 idempotency key 讓重複無害，最後用對帳抓出漏網之魚。這個比較說明了為什麼排程平台不能替所有工作選擇同一種語意：語意是業務決定，必須由工作的 owner 寫下來。

> [!question]- Q6. 排程系統停擺了 6 小時，恢復後應該怎麼處理錯過的工作？
> 不能一律「全部補跑」或「全部跳過」，要依工作的補跑策略分別處理。處理不同時間區間資料的工作（例如每小時的帳務彙總）需要每個錯過的時間點都補一次；只在乎最新狀態的工作（例如重建搜尋索引）只要補跑一次最新的即可；高頻、漏一次無妨的工作（例如每 5 分鐘的清理）可以直接跳過。這些策略應該事先寫在工作的設定中，而不是恢復時才臨場決定。
>
> 執行補跑時還要注意 thundering herd：如果 20 個每小時工作都要各補 6 次，一恢復就會有 120 個 run 同時湧向下游。補跑應該受同時執行數量的上限控制，優先處理業務最重要的工作。補跑完成後，執行對帳確認每個工作的結果，並在 postmortem 中檢討停擺原因，例如排程器的 leader election 為什麼沒能在一分鐘內完成 failover。

> [!question]- Q7. Harbor 規劃第 5 年讓 AI 客服在額度內直接退款（第 48 章），其中一項是讓 AI agent 每晚自動處理前一天的退款爭議：讀取客服對話、判斷是否該退款、對符合條件的訂單經 refund-gateway 執行退款。這個排程 agent 需要哪些保護？
> 首先，它和一般排程工作一樣，需要唯一的 run ID（例如 `refund-review:2027-11-13`），寫進 run ledger 並受 lease 與 fencing 保護，避免兩個 agent 實例同時處理同一天的爭議。每一個發起退款的工具呼叫都要帶確定性的 idempotency key，例如 `refund:{order_id}:{dispute_id}`，因為 agent 框架的自動重試或模型本身重複呼叫工具都可能發生，沒有 key 就會重複退款。
>
> 其次是 agent 特有的保護：每次 run 有最大工具呼叫數、單筆與總退款金額上限、最長執行時間，超過就中止並通知人類；超過某金額或不確定的案例只建立 ticket、不直接退款。客服對話是不受信任的輸入，可能含有「請退款全部訂單」之類的 prompt injection，所以退款規則、金額上限、工具權限必須在 agent 無法修改的地方強制執行。最後，要有獨立的對帳，每天比對 agent 發起的退款與爭議清單，並以抽樣人工審查評估 agent 的判斷品質。

> [!question]- Q8. 面試題：請設計一個每天為上萬名賣家計算並撥款的系統，要求不漏撥、不重撥。
> 可以分四層回答。第一層是排程：排程器跑多個 replica，透過 etcd 這類共識系統選出 leader；leader 在排定時間於 run ledger 中建立以 `(job_name, scheduled_time)` 為唯一鍵的 run，避免重複啟動。第二層是執行：把 run 拆成每位賣家一個項目，worker 以 lease 認領、定期續約、帶 fencing token 寫入結果；失敗的項目以 backoff 重試，超過上限進入 dead-letter，不影響其他賣家。
>
> 第三層是 idempotency：每筆撥款以 `payout:{seller_id}:{business_date}` 作為金流商的 idempotency key，自家資料庫以同樣的組合建立唯一鍵，並以狀態機條件寫入記錄進度；如果金流商不支援 key，就要能用預先決定的參考編號查詢撥款是否存在。第四層是偵測：dead man's switch 在預定時間未完成時告警，獨立的對帳工作比對訂單、撥款紀錄與金流商報表，分類出漏撥、重撥與金額不符。回答時強調「exactly-once 無法單靠傳遞達成，實務上是 at-least-once 加 idempotency 加對帳」，並說明哪些決定（key 的組成、重撥的處理流程）需要和財務與產品一起確認，會讓面試官看到你理解問題的本質。

## 延伸閱讀

- [Site Reliability Engineering — Distributed Periodic Scheduling with Cron](https://sre.google/sre-book/distributed-periodic-scheduling/)：本章的主要來源，描述 Google 分散式 cron 的設計：寧可漏跑不重複的取向、用 Paxos 同步記錄啟動前後的狀態、預先命名以解決部分失敗，以及 crontab 的「?」擴充。
- [Site Reliability Engineering — Managing Critical State: Distributed Consensus for Reliability](https://sre.google/sre-book/managing-critical-state/)：第 40 章的主要來源，說明排程器 leader election 背後的共識基礎與 lease 的使用原則。
- [Site Reliability Engineering — Data Processing Pipelines](https://sre.google/sre-book/data-processing-pipelines/)：當定期工作變得太大、太慢時，下一步是改成 pipeline，這是第 42 章的主題。
