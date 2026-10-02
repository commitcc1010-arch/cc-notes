---
chapter: 22
title: Durable Execution 與長時間 Agent
part: 4
---

# 第 22 章　Durable Execution 與長時間 Agent

> [!abstract] 本章地圖
> **核心問題**：一個要跑幾十分鐘到幾天、中途會遇到 crash、部署、rate limit 與等人核准的 agent，要怎麼做到「死掉之後從原地接著跑」，而且不重複扣款、不重複寄信、不重複付模型的錢？
>
> **你會學到**：
> - 列出長時間 agent 的失敗來源（crash、部署、rate limit、下游故障、等人），判斷每一種會丟掉什麼
> - 比較三種恢復策略：從頭重跑、state 快照、event history 重播，知道各自的代價
> - 說清楚 durable execution 的三個核心：workflow 與 activity 的切分、event history、replay 與 determinism
> - 用 idempotency key 把「至少執行一次」變成「效果只發生一次」，並找出 key 設計的常見錯誤
> - 設計 background agent 的佇列、lease、heartbeat、租戶並行限制與排程（含錯過觸發與重疊政策）
> - 動手寫一個基於事件日誌的可恢復 runner，模擬中途 crash 三次仍然正確完成
>
> **前置知識**：第 4 章（agent loop 與 `loom` v0.1）、第 5 章（tool 的副作用分級）、第 10 章（durable session log 與 context 的關係）、第 19 章（checkpoint 與 interrupt）、第 21 章（approval gate）

## 22.1 故事：凌晨兩點的部署，讓補償 agent 發了兩次優惠券

青鳥科技的營運 research agent 上線第三個月，負責一件以前要兩位營運同事花一整天的工作：每月初分析上個月的物流延遲，找出受影響最嚴重的店家，發補償優惠券，最後把報告寄給營運主管。這是第 1 章定義的 L5 任務：agent 在預算內自己拆解子目標、自主執行，只有不可逆或超出預算的動作才找人。它平均要呼叫模型一百多次、查二十幾張報表，順利的話跑四十分鐘。

十月一日凌晨兩點，平台組照例做每週部署。滾動更新把跑著 research agent 的 container 換掉了，這個 process 當時正在第 87 步。Iris 寫的 runner 和第 4 章的 `loom` v0.1 一樣，messages 只存在記憶體裡，所以 process 一停，前 86 步全部消失。排程系統看到任務失敗，按照設定自動重試：新的 process 從第 1 步開始，重新查報表、重新呼叫模型、重新做決定。

早上九點，客服收到兩家店家的訊息：「為什麼我收到兩張一樣的補償券？」第一次執行在被砍掉之前已經發出了 31 張券，第二次執行又發了一輪；其中兩家店因為重跑時模型對同一份資料做出稍微不同的判斷，金額還不一樣。帳單上，這個任務的模型費用是平常的兩倍多。更糟的是，同一天另一個任務在等營運主管核准一筆大額補償，那個 process 已經空等了兩天，佔著一個 worker 什麼也沒做，部署時也一起被砍，核准紀錄跟著不見。

老陳看完事故報告，在白板上寫了兩行字：「process 會死」「副作用會重複」。「長時間任務的第一條假設，是執行它的機器一定會在任務結束前死掉，」老陳說，「部署、自動擴縮、記憶體不足、rate limit 導致逾時，都是常態，不是意外。你要的不是不會死的 process，而是死了也沒關係的執行模型。業界叫它 durable execution。」

這一章就是 Iris 把 `loom` 改造成可恢復 runner 的過程。我們先把長時間 agent 的失敗分類，比較三種恢復策略；接著拆解 durable execution 的原理：event history、replay、determinism，以及 activity 的 idempotency；然後處理「等人兩天」這類長時間等待，以及 background agent 的佇列與排程；最後在「動手做」寫出一個每次 model call 與 tool call 都記成事件、crash 三次仍然只發一次優惠券的 runner。

## 22.2 長時間 agent 會怎麼失敗

第 4 章的 loop 默默假設了一件事：從使用者送出問題到 agent 回答，執行它的 process 都活著。同步的客服對話只有幾十秒，這個假設大致成立；但當任務長到幾十分鐘、幾小時，甚至要等人好幾天，「process 活到最後」的機率就快速下降。這裡說的**長時間 agent**（long-running agent），指的是執行時間遠超過一次 HTTP 請求、需要跨越多次部署或多個 worker 才能完成的 agent run，例如月度分析、從 issue 到 PR 的 coding agent、跨天的退款核准流程。

```text
 一個 3 小時的 research agent run，時間軸上會遇到的事

 t=0      t=25m        t=70m          t=95m           t=2h         t=3h
 │────────┼────────────┼──────────────┼───────────────┼────────────│
 啟動     429 風暴     下游報表 API    平台例行部署     等主管核准   完成
          （月初所有    逾時 5 分鐘     container 被換掉  （人下班了）
          任務同時跑）
          │            │              │               │
          ▼            ▼              ▼               ▼
 沒有設計：│ 例外炸穿    │ 整個 run 失敗 │ 記憶體中的     │ process 空等，
          │ 或無限重試  │              │ messages 全丟  │ 部署時一起被砍
 durable：│ activity    │ activity 依   │ 新 worker 重播 │ 存檔後讓出 worker，
          │ 退避重試    │ 政策重試      │ 日誌接著跑     │ 收到 signal 再叫醒
```

這張時間軸把一次長任務會遇到的四種典型事件排在一起。t=25m 的 429 風暴是因為月初所有店家的月報同時啟動，模型供應商的配額被打滿；t=70m 是下游報表系統慢了五分鐘；t=95m 是平台例行部署，這一次和 Iris 的事故一模一樣；t=2h 則是 agent 走到需要人核准的動作，而那個人下班了。每一種事件，在「沒有設計」那一列都會讓任務失敗或卡住；在「durable」那一列，處理方式各不相同，但共同點是：**任務的進度不存在 process 的記憶體裡**。

把失敗來源分類，是設計恢復機制的第一步，因為不同的失敗丟掉的東西不一樣：

| 失敗來源 | 例子 | 丟掉什麼 | 天真的處理 | durable 的處理 |
|---|---|---|---|---|
| process crash | OOM、節點故障、斷電 | 記憶體中的所有進度 | 從頭重跑 | 新 worker 重播 event history，從斷點接著跑 |
| 部署與擴縮 | 滾動更新、縮容 | 同上，而且每週都會發生 | 部署前等所有任務結束 | worker 優雅停止，任務交給新版 worker 續跑 |
| 模型 API 限流 | 429、overloaded | 這一次呼叫 | 立刻重試，加劇風暴 | activity 依 retry-after 退避重試，佇列限制並行數 |
| 下游暫時故障 | 報表 API 逾時 | 這一次 tool 呼叫 | 例外炸穿或回填給模型亂試 | activity 依政策重試，用盡才回報給模型 |
| 下游永久錯誤 | 權限被撤銷、參數非法 | 無（重試沒用） | 無限重試 | 標記為不可重試，立刻失敗或交給模型處理 |
| 等人或等外部事件 | 主管核准、CI 跑完 | worker 被空佔 | process 裡 `sleep` 或輪詢 | 存檔後讓出 worker，事件到達再喚醒 |
| 任務本身太長 | 數千步、歷史過大 | 無，但會越跑越慢 | 一個 run 撐到底 | 分段：以摘要狀態開新 run 接續 |

這張表最重要的一欄是「丟掉什麼」。crash 與部署丟掉的是整個進度，這是本章的主菜；限流與下游故障只丟掉一次呼叫，用 retry 就能補回，但 retry 的位置很關鍵：重試的單位必須是「一次呼叫」，而不是「整個任務」，否則一次逾時就要付整個任務的錢。等人這一列最容易被低估：一個 process 空等兩天，佔用的不只是記憶體，還有部署的彈性，因為你不敢重啟它。

常見的誤解是「把 timeout 和 retry 設好就夠了」。retry 只能修補單一呼叫的失敗，它無法讓一個被砍掉的 process 想起自己做到第幾步；而且如果 retry 的對象是有副作用的動作，例如發優惠券，重試本身就會製造 Iris 遇到的重複副作用。要同時解決「進度不丟」與「副作用不重複」，需要的是一個新的執行模型，而不是更多的 try/except。

## 22.3 三種恢復策略：重跑、快照、事件重播

process 死掉之後，要怎麼讓任務繼續？業界大致有三種做法，代價與保證差很多。

第一種是**從頭重跑**：任務失敗就整個重來，這是 Iris 原本的做法。它最簡單，前提是任務滿足兩個條件：夠短（重跑的成本可以接受），以及沒有不可逆的副作用（或副作用天生冪等）。對 agent 來說，第二個條件特別難成立，因為重跑時模型可能做出不同的決定：第一次發了 200 元的券，第二次判斷要發 150 元，連「冪等」都談不上，因為兩次根本不是同一個請求。

第二種是 **checkpoint**（檢查點、state 快照）：在每一個步驟結束時，把整個狀態（messages、變數、下一步要做什麼）序列化存起來，恢復時載入最近一次的快照接著跑。第 19 章的 graph runtime 就是這種做法，LangGraph 的 checkpointer 也是：每個 super-step（一輪節點執行）存一次。快照的粒度是「步驟」，步驟內做到一半的事情不會被記住。

第三種是 **event history replay**（事件歷史重播）：不存狀態本身，而是把「發生過的每一件有外部效果的事」依序記成事件：呼叫了哪個模型、得到什麼回應；呼叫了哪個 tool、得到什麼結果。恢復時從頭重新執行程式碼，但每遇到一個已經記錄過的呼叫，就直接拿紀錄裡的結果，不真的再呼叫一次。程式碼重新跑一遍，外部世界卻一次都沒有被重複打擾。這是 Temporal、Restate、DBOS 等 durable execution 系統的核心機制。

```text
 三種策略在第 87 步 crash 後的恢復方式

 (1) 從頭重跑     步驟 1 ─ 2 ─ 3 ─ … ─ 86 ─ 87 ✗
                 步驟 1 ─ 2 ─ 3 ─ … ─ 86 ─ 87 ─ … 完成      ← 前 86 步全部重做（含副作用）

 (2) 快照恢復     [S1] ─ [S2] ─ … ─ [S86] ─ 87 ✗             [Sn] = 第 n 步結束時的完整 state
                                     └─► 載入 S86 ─ 87 ─ … 完成   ← 只重做第 87 步

 (3) 事件重播     E1 E2 E3 … E172 ─ 87 ✗                     En = 一次 model／tool 呼叫的結果
                 重跑程式碼：E1…E172 直接讀日誌（不呼叫外部）─ 87 ─ … 完成
                                                             ← 只有沒記錄到的呼叫會真的執行
```

這張圖並排三種恢復方式。(1) 的問題一目了然：前 86 步的模型費用與副作用全部重來。(2) 載入第 86 步結束時的快照，只重做第 87 步；它的代價是每一步都要序列化完整 state，而 agent 的 state 主要是越來越長的 messages，快照會越來越大。(3) 記錄的是每一次外部呼叫的結果（大約每步一次 model call 加一次 tool call，所以 86 步約 172 個事件），恢復時程式碼從頭跑，但前 172 個呼叫都直接從日誌拿結果，幾乎不花時間也不花錢。

(2) 和 (3) 看起來很像，差別在三個地方。一是**粒度**：快照以步驟為單位，事件以單次呼叫為單位；一個步驟裡如果有三個平行的 tool call，快照恢復可能要整步重做，事件重播只重做沒記到的那一個。二是**狀態從哪裡來**：快照恢復信任序列化下來的 state；事件重播則用「程式碼加上事件」重建 state，所以程式碼本身必須是確定性的（下一節的主題）。三是**平台責任**：Temporal 一類的系統除了重播，還負責 worker 排程、計時器、跨服務的重試與逾時；框架內建的 checkpointer 通常只負責存取快照，其他要靠部署平台或你自己。

| 比較 | 從頭重跑 | 快照（checkpoint） | 事件重播（durable execution） |
|---|---|---|---|
| 存什麼 | 只存輸入 | 每步結束時的完整 state | 每次外部呼叫的結果 |
| 恢復時重做什麼 | 全部 | 最後一個未完成的步驟 | 只有沒記錄到的那一次呼叫 |
| 對程式碼的要求 | 無 | state 要可序列化 | workflow 程式碼要確定性 |
| 副作用重複的風險 | 高 | 中（步驟內做到一半的） | 低（仍需 idempotency，見 22.6） |
| 儲存成本 | 最低 | 隨 state 大小成長，每步一份 | 隨呼叫次數成長，只追加 |
| 典型實作 | 一般 job queue 重試 | 第 19 章的 graph runtime、LangGraph checkpointer | Temporal、Restate、DBOS、Inngest |
| 適合 | 短、純讀取的任務 | 以節點為單位的 graph、HITL 中斷 | 長時間、多副作用、要等人的任務 |

這張表不是要你永遠選第三欄。客服對話只有幾十秒、只查不寫，從頭重跑完全合理；第 19 章那種以節點組成的 graph，快照天生就對應到圖上的位置，也很好用。事件重播的價值在任務同時具備「長」「有副作用」「要等」三個特徵時才完全顯現，而青鳥的補償 agent 三個都有。另外要澄清一個誤解：事件重播不是「每次都從頭跑一遍很浪費」。重跑的只是 orchestration 程式碼本身（拼 messages、判斷條件），它在毫秒內完成；昂貴的模型與 tool 呼叫一個都不會重做。

## 22.4 Durable execution 的原理：workflow、activity 與 event history

**durable execution**（持久化執行）是一種執行模型：程式碼寫起來像普通的函式，但它的進度被平台持續記錄，執行它的 process 隨時可以死掉，換一個 process 就能從原處接著跑，對程式碼來說就像什麼都沒發生。要做到這件事，它把程式切成兩種角色。

**workflow**（工作流程）是負責「決定下一步做什麼」的協調程式碼，必須是確定性的：同樣的輸入與同樣的事件，一定走出同樣的路徑。**activity**（活動，Restate 與 DBOS 等系統稱為 step）是負責「和外部世界打交道」的程式碼：呼叫模型、查資料庫、發優惠券、寄信。activity 的結果是不確定的（模型每次回答可能不同、資料庫內容會變），所以每一次 activity 的結果都要寫進 **event history**（事件歷史，也稱 journal）：一份只追加、依序編號的日誌。

對應到 agent，切法非常自然：**agent loop 是 workflow，每次 model call 與 tool call 都是 activity**。loop 本身只是在拼 messages、看 stop_reason、決定要不要繼續，這些都是確定性的邏輯；模型回應與 tool 結果才是外部輸入。Temporal 的 AI Cookbook 與 Restate 的 AI 文件都採用這種切法，Google ADK 的 Temporal 範例更直接寫成「每次 LLM 呼叫與每次 I/O tool 呼叫都以 durable activity 執行」。

```text
 第一次執行（process A）                      恢復（process B）
 workflow 程式碼        event history         workflow 程式碼          event history
 ────────────────       ─────────────         ────────────────         ─────────────
 activity#1 model ────► 記錄 #1 結果           activity#1 model ◄────── 讀 #1（不呼叫模型）
 activity#2 query ────► 記錄 #2 結果           activity#2 query ◄────── 讀 #2（不查報表）
 activity#3 model ────► 記錄 #3 結果           activity#3 model ◄────── 讀 #3
 activity#4 coupon ───► 已發券……               activity#4 coupon ─────► 日誌裡沒有 #4：真的執行
          ✗ crash（#4 還沒記錄）                                        記錄 #4 結果
                                              activity#5 model ──────► 記錄 #5 結果 … 繼續
```

這張時序圖是本章的核心。左半邊是第一次執行：workflow 每做一個 activity，結果就寫進 history，依序得到 #1、#2、#3；做到 #4（發優惠券）時 process 死掉，#4 還沒來得及記錄。右半邊是恢復：新的 process 從頭執行同一份 workflow 程式碼。走到 activity #1 時，runner 發現 history 裡已經有 #1，於是直接回傳紀錄裡的模型回應，不呼叫模型；#2、#3 同理。走到 #4 時 history 裡沒有紀錄，runner 才真的去執行；從這裡開始，行為就和第一次執行完全一樣。

這裡有一個容易漏看的細節：右半邊的 workflow 程式碼「以為」自己呼叫了三次模型，它拿到的回應和當初一模一樣，所以它拼出來的 messages、做出的判斷也和當初一模一樣。這就是 replay 能成立的原因：**程式碼是確定性的，外部輸入被記錄下來，所以重新執行會走到完全相同的狀態**。第 10 章說「context 是 session log 的可重建視圖」，在這裡得到了最字面的實現：messages 根本不需要另外存，它可以從事件日誌重建出來。

下面用 30 行程式把這個機制寫出來。`Context.activity()` 是整個 replay 引擎：第 n 個 activity 如果已經在 history 裡，就回傳紀錄；否則真的執行並記錄。

```python
from __future__ import annotations


class Crash(BaseException):
    """模擬 process 被 kill。"""


class Context:
    """最小的 replay 引擎：第 n 個 activity 若已在 history 裡，就回傳紀錄，不重做。"""

    def __init__(self, history: list[dict]):
        self.history, self.seq = history, 0

    def activity(self, name: str, fn):
        self.seq += 1
        if self.seq <= len(self.history):               # 重播：照抄當時的結果
            return self.history[self.seq - 1]["result"]
        result = fn()                                   # 第一次：真的執行
        self.history.append({"seq": self.seq, "name": name, "result": result})
        return result


executed: list[str] = []

def lookup(name: str, value):
    def fn():
        executed.append(name)
        return value
    return fn

def workflow(ctx: Context, crash_after: int | None = None) -> str:
    order = ctx.activity("get_order", lookup("get_order", {"tracking": "TC-88301"}))
    if crash_after == 1:
        raise Crash()
    ship = ctx.activity("get_shipment", lookup("get_shipment", {"eta": "明天"}))
    return f"物流單號 {order['tracking']}，預計{ship['eta']}送達"


history: list[dict] = []                                # 真實系統裡它存在資料庫
try:
    workflow(Context(history), crash_after=1)
except Crash:
    print("第一次執行在 get_order 之後 crash，history =", [h["name"] for h in history])
print("恢復：", workflow(Context(history)))
print("真正執行過的 activity：", executed)
assert executed == ["get_order", "get_shipment"]       # get_order 沒有因為重播而被執行第二次
```

```text
第一次執行在 get_order 之後 crash，history = ['get_order']
恢復： 物流單號 TC-88301，預計明天送達
真正執行過的 activity： ['get_order', 'get_shipment']
```

第一行是第一次執行：`get_order` 完成並記錄後，程式在呼叫 `get_shipment` 之前 crash，history 裡只有 `get_order`。第二行是恢復：用同一份 history 建立新的 `Context` 重跑 workflow，它順利組出完整的回答「物流單號 TC-88301，預計明天送達」，物流單號來自第一次執行時記下的結果。第三行最關鍵：真正被執行過的 activity 只有兩次，`get_order` 沒有因為重播而被執行第二次。這段程式用「第幾個 activity」當作對照的依據（`seq`），這是所有 replay 系統的共同做法，也直接帶出下一節的問題：如果重跑時程式碼走了不同的路，第 n 個 activity 就對不上了。

## 22.5 Determinism：重播成立的前提

replay 的承諾是「重新執行會走到相同的狀態」，這個承諾只在 workflow 程式碼是**確定性的**（deterministic，同樣的輸入與事件一定產生同樣的指令序列）時才成立。如果 workflow 在重播時走了不同的分支，runner 就會拿第 3 個 activity 的紀錄去回答一個完全不同的呼叫，結果可能是把「查報表」的結果當成「發優惠券」的回應，錯得悄無聲息。

會破壞確定性的東西，比直覺多：

| 不確定來源 | workflow 裡的錯誤寫法 | 為什麼重播會出錯 | durable 的寫法 |
|---|---|---|---|
| 現在時間 | `if datetime.now().hour > 18` | 重播時間不同，走不同分支 | 用平台提供的 workflow 時間，或把時間當 activity 結果記錄 |
| 亂數與 UUID | `uuid4()` 當訂單編號、亂數抽樣 | 每次重播產生不同值 | 由平台提供可重播的亂數，或包成 activity |
| 模型呼叫 | 在 workflow 裡直接呼叫 LLM | 同樣的 prompt 會得到不同回答 | 一律包成 activity |
| 讀外部狀態 | 直接查資料庫、讀設定檔、讀環境變數 | 資料與設定會變 | 包成 activity，或在啟動時記錄下來 |
| 並行完成順序 | 用「誰先回來」決定下一步 | 重播時完成順序可能不同 | 用平台的 select／race 原語，結果順序會被記錄 |
| 程式碼改版 | 部署新版 prompt 或新增一個步驟 | 進行中的 run 用新程式碼重播舊歷史 | 版本標記、run 綁定版本、或讓舊版 worker 跑完 |

表中前四列的共同原則是：**任何可能不同的值，都要先變成事件，再讓 workflow 讀它**。第五列在 agent 中很常見：第 20 章的 orchestrator 同時派出三個 subagent，「誰先回來就先處理誰」若用一般的 thread 寫，重播時順序可能不同；durable 平台會把完成順序也記進歷史。最後一列最容易在 production 出事，下面會專門談。

下面的程式示範確定性被破壞時會發生什麼，以及 runner 怎麼抓到它。這次 `Context` 在重播時多做一件事：比對「這一步程式要做的 activity 名稱」和日誌裡記錄的是否相同，不同就丟出 `NonDeterminismError`。

```python
from __future__ import annotations

import random


class NonDeterminismError(Exception):
    pass


class Context:
    """重播時除了回傳紀錄，還要比對「這一步要做的事」是否和日誌相同。"""

    def __init__(self, history: list[dict]):
        self.history, self.seq = history, 0

    def activity(self, name: str, fn):
        self.seq += 1
        if self.seq <= len(self.history):
            rec = self.history[self.seq - 1]
            if rec["name"] != name:
                raise NonDeterminismError(f"第 {self.seq} 步：日誌是 {rec['name']}，程式這次卻要 {name}")
            return rec["result"]
        result = fn()
        self.history.append({"name": name, "result": result})
        return result


def flaky_workflow(ctx: Context, rng: random.Random) -> str:
    ctx.activity("load_orders", lambda: 120)
    # 錯誤示範：在 workflow 程式裡直接擲骰子決定路徑。重播時骰子可能擲出不同的點數
    if rng.random() < 0.5:
        ctx.activity("summarize_short", lambda: "短摘要")
    else:
        ctx.activity("summarize_long", lambda: "長摘要")
    return "ok"


def fixed_workflow(ctx: Context, rng: random.Random) -> str:
    ctx.activity("load_orders", lambda: 120)
    coin = ctx.activity("coin", lambda: rng.random())    # 正確：隨機值本身也當成 activity 記錄
    name = "summarize_short" if coin < 0.5 else "summarize_long"
    ctx.activity(name, lambda: name)
    return "ok"


for wf in (flaky_workflow, fixed_workflow):
    history: list[dict] = []
    wf(Context(history), random.Random(1))              # 第一次執行
    try:
        wf(Context(history), random.Random(2))          # 換一台機器重播，亂數種子不同
        print(f"{wf.__name__:<15} 重播成功，日誌：{[h['name'] for h in history]}")
        assert wf is fixed_workflow
    except NonDeterminismError as exc:
        print(f"{wf.__name__:<15} 重播失敗：{exc}")
        assert wf is flaky_workflow
```

```text
flaky_workflow  重播失敗：第 2 步：日誌是 summarize_short，程式這次卻要 summarize_long
fixed_workflow  重播成功，日誌：['load_orders', 'coin', 'summarize_short']
```

`flaky_workflow` 在 workflow 程式碼裡直接用亂數決定要做短摘要還是長摘要。第一次執行（種子 1）擲出小於 0.5 的值，走了 `summarize_short`；重播時換了一台機器（種子 2），擲出大於 0.5 的值，程式想做 `summarize_long`，但日誌第 2 步記錄的是 `summarize_short`，runner 立刻丟出錯誤。注意這是好事：沒有這個比對，runner 會把 `summarize_short` 的結果當成 `summarize_long` 的回應交回去，錯誤會一路傳下去而沒人發現。`fixed_workflow` 把擲骰子本身包成名為 `coin` 的 activity，結果被記錄，重播時讀回同一個值，自然走同一條路，日誌多了一筆 `coin`。

真實系統的比對比這更嚴格。Temporal 會比對 workflow 重播時產生的指令序列（排程哪個 activity、啟動哪個計時器）與歷史是否一致，不一致就讓這個 workflow 卡住並回報 non-determinism 錯誤，而不是繼續錯下去。本章的動手做會把 activity 的參數也做成摘要一起比對：model activity 的參數是整串 messages，所以如果新版程式碼改了拼 messages 的方式，重播時立刻會被發現。

對 agent 來說，最常見的不確定來源其實是**程式碼與 prompt 的改版**。月報 agent 跑到一半時部署了新版：新的 system prompt、多一個 tool、或在第 5 步之後插入一個驗證步驟。新版 worker 接手舊的 run，用新程式碼重播舊歷史，第 6 個 activity 就對不上了。常見的處理方式有三種：一是**版本綁定**，run 啟動時記下程式與 prompt 的版本，只讓同版本的 worker 接手，舊版 worker 留到舊 run 跑完再下線；二是**版本標記**（patching），在程式碼中用「這個 run 是否在改版之後才走到這裡」的判斷包住新邏輯，Temporal 的 SDK 提供這類 API；三是**分段**，讓長任務定期以摘要狀態開一個新 run（見 22.7），新 run 自然使用新版本。agent 的 prompt 改得比一般程式碼頻繁得多，所以版本策略要在第一天就決定，而不是等到第一次 non-determinism 錯誤才想。

> [!warning] 常見誤解
> 「模型回答本來就不確定，所以 agent 不可能做 durable execution。」不確定的是 activity 的結果，不是 workflow。durable execution 從來不要求外部世界確定，它要求的是：不確定的東西只能經由 activity 進入 workflow，並且被記錄下來。模型回答一旦被記錄，重播時就是一個確定的值。

## 22.6 Activity 的 idempotency：至少一次，加上效果只發生一次

event history 解決了「已完成的 activity 不重做」，但還剩一個窄小卻致命的縫隙：activity 已經對外部世界產生效果、結果卻還沒寫進 history 的那一瞬間。Iris 的補償券就死在這條縫裡。

```text
 worker                         優惠券服務                  event history
   │── issue_coupon(S-311) ────────►│                           │
   │                                │ 發出 CP-001（已生效）      │
   │◄──────────── {coupon: CP-001} ─│                           │
   ✗ crash：結果還沒寫進 history                                 │（沒有 #4）
   ·                                                            │
 新 worker 重播：#4 沒有紀錄，只能再執行一次                      │
   │── issue_coupon(S-311) ────────►│                           │
   │                                │ 沒有 key：再發 CP-002 ✗    │
   │                                │ 有 key：「這個 key 處理過」 │
   │◄──────────── {coupon: CP-001} ─│   回傳第一次的結果 ✓       │
   │── 記錄 #4 ─────────────────────────────────────────────────►│
```

這張時序圖說明了為什麼縫隙無法消除。worker 必須先執行、再記錄；兩者之間不管多短，crash 都可能發生在中間。新 worker 重播時看不到 #4 的紀錄，它無從得知「券到底發了沒」，唯一安全的選擇是再執行一次。所以 durable execution 平台對 activity 的保證是 **at-least-once**（至少執行一次），而不是 exactly-once（恰好一次）。要讓「至少執行一次」不變成「發了兩張券」，責任在 activity 與它呼叫的服務：讓重複的請求不產生重複的效果，也就是 **idempotency**（冪等性：同一個操作做一次和做很多次，效果相同）。

最常見的做法是 **idempotency key**（冪等鍵）：呼叫有副作用的 API 時附上一個唯一的鍵，服務端記住「這個鍵已經處理過，結果是什麼」，同一個鍵再來時直接回傳第一次的結果。Stripe 等金流 API 公開支援這種機制（以 HTTP header 傳遞），很多內部服務也會自己做一張去重表。第 4 章與第 5 章提過這個概念，本節要回答的是更細的問題：**key 要怎麼產生**。

```python
from __future__ import annotations

import uuid


class Crash(BaseException):
    """模擬 process 在「退款成功」與「寫入日誌」之間被 kill。"""


class PaymentAPI:
    """金流商：支援 Idempotency-Key 的退款 API。同一個 key 只會真的退一次。"""

    def __init__(self):
        self.refunds: list[str] = []
        self.seen: dict[str, str] = {}

    def refund(self, order_id: str, amount: int, key: str | None = None) -> str:
        if key is not None and key in self.seen:
            return self.seen[key]                        # 重複的請求：回傳第一次的結果
        refund_id = f"RF-{len(self.refunds) + 1}"
        self.refunds.append(f"{refund_id} {order_id} {amount} 元")
        if key is not None:
            self.seen[key] = refund_id
        return refund_id


def attempt(api: PaymentAPI, log: list[str], make_key, crash: bool) -> None:
    """一次 activity 執行：呼叫退款 → （可能 crash）→ 寫日誌。"""
    if log:                                              # 日誌裡已有完成紀錄：重播，不重做
        return
    api.refund("B-1042", 590, key=make_key())
    if crash:
        raise Crash()
    log.append("refund completed")


strategies = {
    "不帶 key": lambda: None,
    "每次 uuid4()": lambda: str(uuid.uuid4()),          # 錯誤：重試時產生新 key，等於沒有 key
    "run_id:seq": lambda: "run-0917:4",                  # 正確：由 workflow 身分與步驟序號決定
}
for label, make_key in strategies.items():
    api, log = PaymentAPI(), []
    try:
        attempt(api, log, make_key, crash=True)          # 第一次：退款成功後 crash
    except Crash:
        pass
    attempt(api, log, make_key, crash=False)             # 恢復後重試同一個 activity
    print(f"{label}：實際退款 {len(api.refunds)} 筆：{api.refunds}")
    assert len(api.refunds) == (1 if label == "run_id:seq" else 2)
```

```text
不帶 key：實際退款 2 筆：['RF-1 B-1042 590 元', 'RF-2 B-1042 590 元']
每次 uuid4()：實際退款 2 筆：['RF-1 B-1042 590 元', 'RF-2 B-1042 590 元']
run_id:seq：實際退款 1 筆：['RF-1 B-1042 590 元']
```

三種策略面對同一個情境：第一次執行退款成功後 crash，恢復後重試同一個 activity。「不帶 key」退了兩次，這是 Iris 的事故。「每次 uuid4()」也退了兩次，這是最常見、也最隱蔽的錯誤：程式碼看起來有 key，但 key 是在 activity 每次執行時才產生的，重試時產生了新的 key，服務端當然把它當成新請求。「run_id:seq」只退了一次，因為 key 由 workflow 的身分（哪一個 run）與步驟序號（第幾個 activity）決定，不論重試幾次、在哪台機器上，算出來的都是同一個值。

所以 key 設計的原則是：**key 要在「意圖」產生時就固定，而不是在「執行」時產生**。在 durable runner 裡，最自然的 key 就是 run id 加上 activity 序號，因為它們由日誌決定、重播時不會變。如果一定要用 UUID，就要把產生 UUID 本身當成 activity 記錄下來（就像上一節的 `coin`）。

第 5 章的 `loom` 用的是同一個原則的另一種寫法：harness 依 run id、tool 名稱與 tool 宣告的 `intent_fields`（定義業務意圖的參數，例如店家與金額）推導 key，模型看不到也填不了。兩種 key 在重播時都不會變，差別在範圍：`run_id:seq` 綁的是「日誌中的位置」，意圖推導的 key 綁的是「要做的事」。如果 crash 之後模型被重問、在後面某一步又提出同一個意圖（同一家店、同一個金額），位置不同，`run_id:seq` 會把它當成新請求，意圖推導的 key 則會認出它是重複。所以全書的規則是：宣告了 `intent_fields` 的副作用 tool 一律用意圖推導的 key，`run_id:seq` 只是沒有意圖欄位時的保底，本節的程式為了聚焦在重播機制而用了後者。key 的範圍也要依業務決定：同一個 run 中對同一家店發兩次券，如果真的是兩個不同的補償事件，就要把事件 id 放進意圖欄位；如果業務上「一家店一個月只能補償一次」，那是另一層的業務規則，要用 `(store, month)` 做唯一約束，不能指望 idempotency key 代勞。

不是每個下游都支援 idempotency key。寄信、發簡訊、呼叫老舊的 ERP，常常沒有這種機制。這時有幾種補救方式：先查再做（重試前先查「這家店本月有沒有收到券」，有就跳過）；在自己的資料庫裡維護去重表，和寄信請求放在同一個交易裡寫入（outbox pattern：先把「要寄的信」寫進自己的資料庫，再由另一個程序可靠地送出）；或者接受極少數重複，但讓重複可以被偵測與補救（例如寄出的信件帶著 run id，客服看到重複可以解釋）。真正不可逆、又沒有去重機制的動作，依全書「不可回復的動作永遠不完全自動」的原則（第 1 章），應該經過第 21 章的 approval gate。

| activity 類型 | 例子 | 重試政策 | 不可重試的錯誤 | idempotency 做法 |
|---|---|---|---|---|
| 模型呼叫 | `complete(messages)` | 429／5xx／逾時依 retry-after 指數退避，設總時限 | context 過長、內容被拒、認證失敗 | 天生沒有外部副作用；重做只多花錢，必要時用 cache |
| 唯讀 tool | 查報表、查訂單 | 積極重試 | 參數錯誤、查無資料 | 天生冪等 |
| 可冪等的寫入 | 發券、退款（API 支援 key） | 重試，帶同一個 key | 業務規則拒絕 | 依 intent_fields 推導 key（保底 run_id:seq） |
| 不可冪等的寫入 | 寄信、呼叫老舊 ERP | 謹慎重試，先查再做 | 大多數錯誤 | 自建去重表或 outbox；高風險的走人工核准 |
| 長時間 activity | sandbox 裡跑 20 分鐘測試 | 依 heartbeat 判斷存活，逾時重試 | 測試本身失敗（那是結果，不是錯誤） | 以 run_id:seq 命名 sandbox 與產出物，重試時可接手 |

這張表把第 4 章的錯誤分類與本章的 idempotency 合在一起。模型呼叫有一個特殊之處：它沒有外部副作用，重做是安全的，只是要多付一次錢，所以 crash 窗口落在模型呼叫上時，代價是一次模型費用；這也是為什麼結果要在拿到後立刻寫進日誌。最後一列的 **heartbeat**（心跳）是長時間 activity 的存活訊號：activity 定期回報「我還活著，做到哪裡了」，平台超過一定時間沒收到心跳，就判定執行它的 worker 死了，可以把這個 activity 交給別人重試，而不必等到整個逾時時間結束。

> [!warning] 常見誤解
> 「我們用的 durable 平台保證 exactly-once，所以 tool 不用做冪等。」主流平台保證的是 workflow 的狀態推進恰好一次（重播不會重複記錄），activity 的執行仍然是至少一次。所謂 exactly-once 的效果，永遠是「at-least-once 執行」加上「冪等的 activity」組合出來的，冪等這一半是你的責任。

## 22.7 長時間等待：timer、signal 與人工核准

Iris 事故的第二部分，是一個 process 空等了兩天的核准。第 21 章設計了 approval gate：超出 L4 邊界的動作，要暫停並等人核准。但「暫停」在實作上是什麼意思？如果是 process 裡的 `while not approved: sleep(60)`，那它在等待期間佔著一個 worker、擋著部署，而且一旦被重啟，等待狀態就消失了。

durable execution 對「等待」的回答是：**等待也是一個事件**。workflow 需要等外部事件時，runner 把「我在等什麼、最晚等到什麼時候」寫進日誌，然後讓這次執行結束，釋放 worker。等待期間，系統裡沒有任何 process 為這個 run 運轉，它只是資料庫裡的幾筆紀錄。當事件到達（主管按下核准）或計時器到期，平台找一個 worker，從頭重播日誌，走到等待點時發現「事件已經在日誌裡了」，於是繼續往下。這裡用到兩個原語：**durable timer**（持久化計時器：把「在某個時間點叫醒我」記錄下來，由平台負責到時喚醒）與 **signal**（訊號：從 workflow 外部送進來、會被寫入日誌的事件，例如核准結果）。

```text
                     submit
                       │
                       ▼
                ┌────────────┐  activity 完成
                │  RUNNING   │◄──────────────────────────┐
                └─────┬──────┘                           │
       ┌──────────────┼───────────────┬─────────────┐    │
       │ 遇到等待點    │ 所有步驟完成   │ 不可重試錯誤 │    │
       ▼              ▼               ▼             │    │
 ┌────────────┐ ┌────────────┐  ┌────────────┐      │    │
 │  WAITING   │ │ COMPLETED  │  │   FAILED   │      │    │
 │ (timer 或  │ └────────────┘  └────────────┘      │    │
 │  signal)   │                                     │    │
 └─────┬──────┘   cancel 訊號（任何非終態皆可）       │    │
       │          ──────────────► CANCELLED ◄────────┘    │
       │ signal 到達或 timer 到期：worker 重播後繼續        │
       └──────────────────────────────────────────────────┘

 worker crash 不是狀態轉換：RUNNING 的 run 只是換一個 worker 重播
```

這張狀態機描述了一個 durable agent run 的生命週期。RUNNING 是有 worker 在執行的狀態；遇到等待點就轉到 WAITING，此時不佔任何運算資源；signal 到達或 timer 到期，再轉回 RUNNING。三個終態分別是 COMPLETED、FAILED（不可重試的錯誤，或重試用盡）與 CANCELLED（使用者或系統送出取消訊號）。圖底下那行很重要：worker crash 在這張圖上根本不是一個轉換，因為對 run 來說，換一個 worker 重播和沒有發生任何事是一樣的。這和第 15 章 A2A 的 task 狀態（含 input-required）以及第 19 章 graph 的 interrupt 是同一個概念的不同層次：協定層描述「對外看到的狀態」，durable 層保證「這個狀態不會因為機器死掉而遺失」。

下面的程式實作「等核准，最多等 48 小時」。`wait_signal()` 第一次執行時把截止時間寫進日誌，然後丟出 `Suspend` 讓出 worker；每次被叫醒都從頭重播，直到 signal 出現或計時器到期。

```python
from __future__ import annotations

HOUR = 3600


class Suspend(BaseException):
    """workflow 需要等外部事件：存好日誌後讓出 worker，不佔任何運算資源。"""


class Context:
    def __init__(self, history: list[dict], now: float):
        self.history, self.now, self.seq = history, now, 0

    def _recorded(self, kind: str):
        for e in self.history:
            if e["seq"] == self.seq and e["kind"] == kind:
                return e
        return None

    def activity(self, name: str, fn):
        self.seq += 1
        if (e := self._recorded("activity")):
            return e["result"]
        result = fn()
        self.history.append({"seq": self.seq, "kind": "activity", "name": name, "result": result})
        return result

    def wait_signal(self, name: str, timeout: float):
        """等待名為 name 的 signal，最多 timeout 秒。截止時間第一次執行時就寫進日誌，重播時不會變。"""
        self.seq += 1
        timer = self._recorded("timer")
        if timer is None:
            timer = {"seq": self.seq, "kind": "timer", "fire_at": self.now + timeout}
            self.history.append(timer)
        for e in self.history:
            if e["kind"] == "signal" and e["name"] == name and e["at"] <= timer["fire_at"]:
                return e["payload"]
        if self.now >= timer["fire_at"]:
            return None                                  # 逾時：走升級路徑
        raise Suspend(f"等待 {name}，最晚到 {timer['fire_at'] / HOUR:.0f} 小時")


def refund_workflow(ctx: Context) -> str:
    order = ctx.activity("get_order", lambda: {"order_id": "B-2290", "amount": 3200})
    decision = ctx.wait_signal("approval", timeout=48 * HOUR)   # 3,200 元超過 L4 邊界，要人核准
    if decision is None:
        return ctx.activity("escalate", lambda: "48 小時無人核准，已轉主管")
    if decision["approved"]:
        return ctx.activity("refund", lambda: f"已退款 {order['amount']} 元（核准人 {decision['by']}）")
    return ctx.activity("notify", lambda: "退款被拒，已通知顧客")


def wake(history: list[dict], now: float) -> str:
    """worker 被叫醒（signal 到達或計時器到期）時做的事：從頭重播。"""
    try:
        return "完成：" + refund_workflow(Context(history, now))
    except Suspend as exc:
        return f"暫停：{exc}"


# 情境一：客服主管 30 小時後才按下核准
h1: list[dict] = []
print("t=0h  ", wake(h1, 0))
h1.append({"seq": -1, "kind": "signal", "name": "approval", "at": 30 * HOUR,
           "payload": {"approved": True, "by": "值班主管"}})   # 外部 API 只負責把 signal 寫進日誌
print("t=30h ", wake(h1, 30 * HOUR))

# 情境二：一直沒有人處理，48 小時的計時器到期
h2: list[dict] = []
print("t=0h  ", wake(h2, 0))
print("t=20h ", wake(h2, 20 * HOUR))                     # 被其他事件叫醒，但條件都沒滿足：繼續睡
print("t=48h ", wake(h2, 48 * HOUR))
assert [e["name"] for e in h1 if e["kind"] == "activity"] == ["get_order", "refund"]
assert h2[-1]["result"].startswith("48 小時")
```

```text
t=0h   暫停：等待 approval，最晚到 48 小時
t=30h  完成：已退款 3200 元（核准人 值班主管）
t=0h   暫停：等待 approval，最晚到 48 小時
t=20h  暫停：等待 approval，最晚到 48 小時
t=48h  完成：48 小時無人核准，已轉主管
```

情境一：t=0 時 workflow 查完訂單，發現 3,200 元超過 L4 邊界，寫下「最晚等到第 48 小時」後暫停。30 小時後值班主管核准，外部 API 唯一做的事是把 signal 寫進日誌；worker 被叫醒、重播，`get_order` 直接讀紀錄，`wait_signal` 在日誌裡找到核准，於是執行退款。情境二：一直沒人處理。t=20h 時 worker 被某個無關的事件叫醒，重播後兩個條件都沒滿足，於是繼續睡；t=48h 計時器到期，`wait_signal` 回傳 None，workflow 走升級路徑，轉給主管。這裡有一個關鍵細節：截止時間在第一次執行時就寫進日誌，重播時讀回同一個值，所以不管 worker 在第幾小時被叫醒，「48 小時」都是從同一個起點算。如果截止時間是每次重播時用 `now + 48h` 重算，那個 run 會永遠等不到逾時。

長時間等待還帶出兩個實務問題。第一是**歷史會越來越大**：每一次模型呼叫的結果都要寫進日誌，而 agent 的 messages 本身就很大，一個跑了幾千步的 agent，日誌可能大到每次重播都要讀很久。主流平台對單一 run 的事件數與大小都有上限，常見的解法有兩個：大型 payload 外存（claim check pattern：把完整的模型回應存在物件儲存，日誌裡只記參照與雜湊），以及**分段續跑**（Temporal 稱為 continue-as-new：以目前的精簡狀態開一個新的 run 接續，舊 run 的歷史就此封存）。分段續跑對 agent 特別合適，因為「精簡狀態」正好就是第 10 章的 compaction 摘要。

第二是 **streaming 與日誌是兩條路徑**。使用者想看到模型逐字輸出，但日誌只需要記錄完整的最終回應。常見的做法是 activity 在執行時把 token 串流推到另一個通道（例如 pub/sub 或第 15 章的 AG-UI 事件），完成後只把最終結果寫入日誌。重播時不會重新串流，前端要能處理「重新連線後只看到最終結果」的情況。

## 22.8 Background agent：佇列、worker 與排程

到目前為止，我們討論的是「一個 run 如何活下來」。但 Iris 的系統還有更上層的問題：月初一千家店的月報同時啟動，誰來決定先跑哪一個？worker 死了，它手上的任務誰來接？「每月 1 日凌晨跑」這件事，如果排程器那天剛好在停機，要不要補跑？這些是 **background agent**（背景 agent：使用者提交任務後不必等待，agent 在背景執行、完成後通知）的基礎設施問題。

```text
 觸發來源                    任務佇列                       worker pool               durable 儲存
 ─────────                  ─────────                      ───────────               ───────────
 使用者 API ──┐             ┌──────────────────┐            ┌────────┐               ┌──────────┐
 排程器 cron ─┼─ enqueue ──►│ ready  ready  …  │── lease ──►│ W1     │── 讀寫事件 ──►│ event    │
 webhook ────┘   回傳 run_id│ leased(W1, 到 t+10)│◄─ heartbeat│ W2     │               │ history  │
                            │ 租戶並行上限       │            │ W3     │               │ 結果與    │
                            └────────┬─────────┘            └───┬────┘               │ 大型產出 │
                                     │ lease 過期：回到 ready     │                    └────┬─────┘
                                     │ 重試用盡：dead letter       │ 完成                     │
                                     ▼                           ▼                         ▼
                              人工檢查佇列               通知：webhook／email／UI  ◄── 狀態查詢 API
                                                       （A2A push、MCP Tasks）
```

這張架構圖從左到右是一個 background agent 平台的資料流。觸發來源有三種：使用者透過 API 提交（立刻拿到 run id，不必等待）、排程器定時觸發、外部系統的 webhook（例如 CI 跑完通知 coding agent）。任務進入佇列後，worker 用 **lease**（租約：在一段時間內獨佔這個任務的權利）領走任務，並在執行期間定期 heartbeat 續約。worker 死掉就不會再續約，lease 過期後任務回到 ready，被其他 worker 領走；因為進度在 durable 儲存裡，新 worker 從斷點接著跑。重試次數用盡的任務進入 **dead letter queue**（死信佇列），等人檢查，而不是無限重試。右下角是結果的出口：完成時透過 webhook、email 或 UI 通知，第 15 章的 A2A push notification 與 MCP 的 Tasks 擴充，就是把這個出口標準化的協定。

佇列層有三個設計重點。第一是 **lease 與 fencing**：lease 過期不代表舊 worker 真的死了，它可能只是長時間 GC 或網路分區，醒來後還以為任務是自己的。如果它繼續寫入，就會和新 worker 同時推進同一個 run。防止這件事的機制叫 **fencing token**（隔離令牌）：每次發出 lease 時給一個遞增的版本號，儲存層只接受目前版本的寫入，舊 worker 的寫入會被拒絕。第二是**公平性**：如果一家大店一次提交五十個任務，FIFO 佇列會讓其他店家全部排在後面，所以要有租戶層級的並行上限（第 36 章的多租戶設計會再展開）。第三是**背壓**（backpressure）：模型供應商的 rate limit 是整個平台共用的資源，worker 數量與每個租戶的並行數，要依 TPM、RPM 配額反推，而不是越多越好；否則 22.2 節的 429 風暴只是被搬到佇列後面發生。

排程（scheduling）看起來只是 cron，對 agent 而言卻有兩個特別容易出錯的政策。**錯過的觸發**（misfire）：排程器停機三小時，錯過了三次「每小時同步庫存異常」，恢復後要補跑三次、只補最近一次，還是都不補？**重疊**（overlap）：上一次觸發的 agent run 還沒跑完，下一次觸發又到了，要同時跑兩個、跳過這次、還是排隊？agent run 的時長變異很大（同一個月報，資料多的月份可能跑三倍久），所以重疊比傳統批次任務更常見。

| 政策 | 選項 | 適合 | 風險 |
|---|---|---|---|
| 錯過的觸發 | 全部補跑 | 每次觸發處理不同資料（例如每小時的帳務切片） | 恢復時瞬間湧入大量任務，打爆配額 |
| 錯過的觸發 | 只補最近一次 | 每次都處理「最新狀態」（庫存異常、儀表板） | 中間時段沒有被處理，要確認業務上可以接受 |
| 錯過的觸發 | 不補 | 時效性極強、過期就沒意義的通知 | 靜默遺漏，需要監控與告警 |
| 重疊 | 跳過這次 | 處理最新狀態、上一輪結果仍有效 | 長時間卡住的 run 會讓排程一直跳過，需要逾時 |
| 重疊 | 排隊（最多一個） | 不能遺漏、但也不能平行 | 積壓；上一輪失敗時要決定是否仍執行 |
| 重疊 | 允許並行 | 彼此完全獨立的任務 | 兩個 run 寫同一份資料，競爭條件 |
| 重疊 | 取消上一輪 | 只在乎最新結果、舊的跑完也沒用 | 舊 run 的副作用做到一半，需要補償 |

這張表沒有預設的正確答案，要依「每次觸發處理的是什麼」來選。青鳥的月度補償是「全部補跑」型：九月的補償不能因為排程器停機就不做，但它每月只跑一次，補跑不會造成湧入；每小時的庫存異常同步則是「只補最近一次＋重疊時跳過」型，因為舊的庫存狀態沒有意義。Temporal 的 Schedules 功能在公開文件中提供類似的重疊政策選項（例如跳過、緩衝一個、全部緩衝、取消上一輪、允許全部）與補跑時間窗設定，可以當作設計時的檢查表。

> [!tip] 使用者提交了任務，然後呢？
> background agent 的使用者體驗重點不在「跑多快」，而在「我知道它在做什麼」。提交後立刻回傳 run id 與預估時間；提供狀態查詢（目前在第幾步、等什麼）；完成或需要人介入時主動通知；並且提供取消。取消要是協作式的：送出 cancel signal，workflow 在下一個 activity 邊界停下，已經產生的副作用由補償動作處理（例如作廢已發出的優惠券），這種「每個副作用都有對應的撤銷動作」的設計叫 **saga**。第 37 章會從產品角度談非同步互動。

## 22.9 主流系統對照：Temporal、Restate 與框架內建的 durability

durable execution 不是 agent 時代的發明，它來自支付、訂單、資料管線等領域多年的實踐；agent 的出現讓它從「後端進階工具」變成「長時間 agent 的標準配備」。了解主流系統用什麼名詞稱呼同一個概念，能讓你在讀文件、做選型、和其他團隊溝通時少走很多冤枉路。以下只整理公開文件中的概念，不比較效能。

| 概念 | 本章 runner | Temporal | Restate | DBOS | LangGraph |
|---|---|---|---|---|---|
| 協調程式碼 | agent loop | Workflow | 以 handler 撰寫的 service | `@DBOS.workflow` | graph |
| 外部呼叫的單位 | activity | Activity | `ctx.run()` 包住的 step | `@DBOS.step` | node（以快照為單位） |
| 進度的紀錄 | EventLog | Event History | journal | Postgres 中的 workflow 與 step 狀態 | checkpointer（每個 super-step 一份快照） |
| 恢復方式 | 重播事件 | 重播事件 | 重播 journal | 從資料庫的 step 紀錄恢復 | 載入快照 |
| 等外部事件 | `wait_signal` | Signal、Update | awakeable、durable promise 類的原語 | 收發訊息的 API | `interrupt()` 加 `Command(resume=...)` |
| 持久化計時 | timer 事件 | Timer、`workflow.sleep` | 持久化的 sleep | 持久化的 sleep | 需要外部系統 |
| 部署形態 | 函式庫 | 獨立 cluster（或 Temporal Cloud）加上你的 worker | 單一 server，以 HTTP 推送呼叫你的服務 | 函式庫，只需要 Postgres | 函式庫，搭配部署平台 |

這張表的上半部是概念對應，可以發現大家其實在做同一件事：把程式切成確定性的協調與不確定的外部呼叫，記錄後者的結果。差別主要在下半部的部署形態。**Temporal** 最成熟，有獨立的服務端負責保存歷史、排程 worker、管理計時器與重試，Web UI 可以直接看每個 workflow 的事件歷史，代價是要營運一個 cluster（或購買託管服務），以及團隊要理解 determinism 的限制。**Restate** 以單一 server 的形式運作，用 HTTP 把呼叫推送給你的服務，對 serverless 部署友善，並以 key 區分的持久 session 內建了並發控制。**DBOS** 是一個函式庫，狀態直接存在你已經有的 Postgres 裡，不需要另一個 orchestrator。**Inngest** 走 event-driven 與 serverless 路線，用 `step.run()` 定義持久化步驟、`waitForEvent()` 等待外部事件，並內建 concurrency、throttle 等流量控制。**LangGraph** 的 checkpointer 屬於第 19 章的快照路線，它負責存取 state，worker 排程、計時器與跨服務重試則交給部署平台或外部系統。

選型時，問自己三個問題通常就夠了。第一，任務多長、要不要等人？只有幾分鐘、不等人，框架內建的 session 持久化或快照就夠；要跨天等核准、要跨部署存活，需要真正的 durable execution。第二，團隊願意營運多少基礎設施？已經有 Postgres、不想多一個服務，函式庫型的方案比較輕；需要跨語言、跨團隊的大規模編排，獨立服務的方案比較完整。第三，現有的 agent 框架有沒有官方整合？主流框架大多已經和至少一個 durable 平台整合，整合的形式通常是「把框架的每次 model call 與 tool call 自動包成 activity」，讓你不必改寫 agent 程式碼。

下面是用 Temporal Python SDK 寫 agent loop 的骨架，示範 workflow 與 activity 在真實 SDK 中的樣子。依 2026-10 的 SDK 介面撰寫，細節請以官方文件為準；它需要 Temporal 服務與 SDK，所以標為不可執行。

```python
# not-runnable
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@activity.defn
async def call_model(messages: list[dict]) -> dict:
    ...  # 呼叫模型 API；429／5xx 直接丟例外，由 Temporal 依 retry policy 重試


@activity.defn
async def run_tool(name: str, args: dict, idempotency_key: str) -> str:
    ...  # 有副作用的 tool 把 idempotency_key 傳給下游服務


@workflow.defn
class CompensationAgent:
    @workflow.run
    async def run(self, task: str) -> str:
        messages = [{"role": "user", "content": task}]
        for step in range(100):
            resp = await workflow.execute_activity(
                call_model, messages,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            messages.append({"role": "assistant", "content": resp["text"], "tool_calls": resp["tool_calls"]})
            if not resp["tool_calls"]:
                return resp["text"]
            for tc in resp["tool_calls"]:
                key = f"{workflow.info().workflow_id}:{step}:{tc['id']}"   # 重播時算出同一個 key
                out = await workflow.execute_activity(
                    run_tool, args=[tc["name"], tc["args"], key],
                    start_to_close_timeout=timedelta(minutes=5),
                )
                messages.append({"role": "tool", "tool_call_id": tc["id"], "name": tc["name"], "content": out})
        return "步驟用完，轉人工"
```

這段骨架和本章的 runner 結構完全相同：workflow 方法裡只有拼 messages 與判斷的邏輯，模型與 tool 都經由 `execute_activity` 執行，重試政策與逾時是宣告式的設定，不寫在 loop 裡。idempotency key 由 workflow id、步驟與 tool call id 組成，三者在重播時都不會變。注意 messages 會隨著 activity 的參數與結果一起進入事件歷史，長任務要搭配 22.7 節的 payload 外存與分段續跑。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各專案公開文件與 release 紀錄整理（整合狀態變動快，請以官方文件為準）：Temporal 的 AI Cookbook 提供 OpenAI Responses、OpenAI Agents SDK、Anthropic agentic loop、Vercel AI SDK、Google ADK、Strands 等範例，以及以 Signal 實作人工核准、以 Claim Check 外存大型 payload 的 recipe；Temporal 與 OpenAI Agents SDK 的整合（把每次模型呼叫自動變成 activity）於 2025 年推出，目前屬於正式版或預覽版，公開資料未能確認。Restate 的 AI 文件列出 Vercel AI SDK、OpenAI Agents SDK、Google ADK、Pydantic AI、LangChain 的整合，並提供含核准、subagent、排程的參考實作。Pydantic AI 內建可插拔的 durability backend（含 Temporal 與 Postgres-based 的 Absurd）；Mastra 有 Inngest workflow runner 與 durable streams；DBOS 提供 Python、TypeScript、Go、Java 的函式庫與 durable queue、排程功能。框架內建的 session 持久化方面，OpenAI Agents SDK 的 `RunState` 可序列化後 resume，Google ADK 有 session event log，Microsoft Agent Framework 的 workflow 支援 checkpoint。託管服務方面，Claude Managed Agents 的 session 是 harness 之外的持久事件日誌，harness 本身無狀態，可依 session id 喚醒恢復，並支援排程部署；Gemini 的 Deep Research agent 必須以 background 模式執行，可輪詢或以事件 id 續傳串流；OpenAI Codex 的排程任務已於 2026 年正式提供。Cloudflare Agents SDK 以 Durable Objects 為每個 agent 實例提供狀態與排程，細節本書未查證。

## 22.10 動手做：基於事件日誌的可恢復 runner

這一節把前面所有概念組成 `loom.durable`：一個每次 model call 與 tool call 都記成事件、crash 後重播日誌、用 idempotency key 防止重複副作用、對 429 退避重試的 agent runner。接著用一個簡化的佇列與排程器，示範 background agent 的 lease、heartbeat、租戶並行上限、錯過觸發與重疊政策。

```text
 DurableRunner.run(task)
   │
   ├─ 讀 EventLog（run_id）── 已有 finished？ ── 是 ──► 直接回傳結果（重播不花任何錢）
   │
   ├─ seq = 0；messages = [user]                 ← messages 不另外存，從事件重建
   │
   └─ loop：activity("model", messages) ──┐
            activity(tool, args)  ────────┤
                                          ▼
                    ┌─────────── activity(name, args) ───────────┐
                    │ seq += 1；key = run_id:seq                  │
                    │ 日誌有 completed#seq？                       │
                    │   有：比對 name 與參數摘要 → 不同就丟        │
                    │       NonDeterminismError；相同就回傳紀錄   │
                    │   無：寫 scheduled → 執行（429 退避重試）  │
                    │       → ✗ 危險窗口（模擬 crash 的位置）     │
                    │       → 寫 completed（含結果）→ 回傳        │
                    └────────────────────────────────────────────┘
```

這張資料流圖對應下面程式的結構。`run()` 一開始讀日誌：已完成的 run 直接回傳，所以「查詢一個跑完的任務」永遠不會重新呼叫模型。接著從空的 messages 開始跑 loop，但 loop 裡所有外部呼叫都經過 `activity()`。`activity()` 先遞增序號並算出 idempotency key，再查日誌：有紀錄就比對簽章（名稱加參數摘要）後回傳紀錄；沒有紀錄才真的執行，遇到 429 依 retry-after 退避（用模擬時鐘，不真的 sleep），執行完寫入 completed。圖中標示的「危險窗口」就是 22.6 節的縫隙，程式用 `crash_at` 參數在這裡注入 crash。

外部世界用三個物件模擬：`Provider` 是模型供應商（第一次請求回 429）、`CouponService` 是支援 idempotency key 的優惠券服務、`mails` 是以 key 去重的寄信服務。它們都活在 runner 之外，所以「process crash」時不會遺失狀態，就像真實世界一樣。劇本模擬青鳥的補償任務：查延遲 → 給 S-311 發券 → 給 S-502 發券 → 寄報告 → 回答。我們安排三個 process：第一個在 S-311 的券發出後、寫日誌前 crash；第二個在拿到模型回應後、寫日誌前 crash；第三個跑完。

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


class ScriptedModel:
    """依劇本回應的假模型。劇本的每一步是 ModelResponse，或「收到 messages 後回傳 ModelResponse」的函式。"""

    def __init__(self, script: list[ModelResponse | Callable[[list[dict]], ModelResponse]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse:
        self.calls.append(json.loads(json.dumps(messages)))
        if not self.script:
            raise RuntimeError("劇本已用完：agent 呼叫模型的次數比預期多")
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def call(name: str, call_id: str = "c1", **args: Any) -> ModelResponse:
    """劇本小工具：產生一個「呼叫 name 工具」的回應。"""
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


# ───────────────────── loom.durable：可恢復 runner ─────────────────────
class Crash(BaseException):
    """模擬 process 被 kill。繼承 BaseException，一般的 except Exception 攔不到，就像真的斷電。"""


class RateLimited(Exception):
    def __init__(self, retry_after: float):
        super().__init__(f"429，{retry_after} 秒後再試")
        self.retry_after = retry_after


class NonDeterminismError(Exception):
    pass


class EventLog:
    """append-only 的事件日誌。每筆存成 JSON 字串，模擬寫進資料庫：process 死掉，資料還在。"""

    def __init__(self) -> None:
        self.rows: list[str] = []

    def append(self, run_id: str, event: dict) -> None:
        self.rows.append(json.dumps({"run_id": run_id, **event}, ensure_ascii=False))

    def load(self, run_id: str) -> list[dict]:
        return [e for e in map(json.loads, self.rows) if e["run_id"] == run_id]


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


class DurableRunner:
    """agent loop 是 workflow（確定性），每次 model call 與 tool call 是 activity（結果寫進日誌）。"""

    def __init__(self, run_id, log, model, tools, side_effects, crash_at=(), clock=None, max_steps=10):
        self.run_id, self.log, self.model, self.tools = run_id, log, model, tools
        self.side_effects, self.crash_at = side_effects, set(crash_at)
        self.clock = clock if clock is not None else [0.0]
        self.max_steps = max_steps
        self.stats = {"replayed": 0, "executed": 0}

    def activity(self, name: str, args: dict, fn: Callable[[str], Any]) -> Any:
        self.seq += 1
        sig = {"name": name, "args": digest(args)}
        key = f"{self.run_id}:{self.seq}"                 # 重播時一定算出同一個 key
        if self.seq in self.done:                          # 已完成：直接回傳紀錄，不重做
            if self.done[self.seq]["sig"] != sig:
                raise NonDeterminismError(f"seq {self.seq}：日誌是 {self.done[self.seq]['sig']}，程式卻要 {sig}")
            self.stats["replayed"] += 1
            return self.done[self.seq]["result"]
        self.log.append(self.run_id, {"type": "scheduled", "seq": self.seq, "sig": sig})
        for attempt in range(1, 4):
            try:
                result = fn(key)
                break
            except RateLimited as exc:                     # 可重試的錯誤：退避後重試，並留下紀錄
                self.log.append(self.run_id, {"type": "retry", "seq": self.seq, "attempt": attempt})
                self.clock[0] += exc.retry_after * attempt
        else:
            raise RuntimeError(f"{name} 重試用盡")
        if f"{name}#{self.seq}" in self.crash_at:          # 危險窗口：事情做了，但還沒記下來
            raise Crash(f"{name}#{self.seq} 完成後、寫入日誌前")
        self.log.append(self.run_id, {"type": "completed", "seq": self.seq, "sig": sig, "result": result})
        self.stats["executed"] += 1
        return result

    def run(self, user_input: str) -> dict:
        history = self.log.load(self.run_id)
        if not history:
            self.log.append(self.run_id, {"type": "started", "input": user_input})
        for e in history:
            if e["type"] == "finished":                    # 已完成的 run：直接回傳結果
                return {"status": "done", "output": e["output"], **self.stats}
        self.done = {e["seq"]: e for e in history if e["type"] == "completed"}
        self.seq = 0
        messages: list[dict] = [{"role": "user", "content": user_input}]
        for _ in range(self.max_steps):
            resp = self.activity("model", {"messages": messages},
                                 lambda key: to_dict(self.model.complete(messages)))
            messages.append({"role": "assistant", "content": resp["text"], "tool_calls": resp["tool_calls"]})
            if not resp["tool_calls"]:
                self.log.append(self.run_id, {"type": "finished", "output": resp["text"]})
                return {"status": "done", "output": resp["text"], **self.stats}
            for tc in resp["tool_calls"]:
                fn = self.tools[tc["name"]]
                if tc["name"] in self.side_effects:      # 有副作用的 tool：把 idempotency key 傳下去
                    run_tool = lambda key, fn=fn, tc=tc: fn(**tc["args"], idempotency_key=key)
                else:
                    run_tool = lambda key, fn=fn, tc=tc: fn(**tc["args"])
                out = self.activity(tc["name"], tc["args"], run_tool)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "name": tc["name"],
                                 "content": json.dumps(out, ensure_ascii=False)})
        return {"status": "max_steps", "output": "", **self.stats}


def to_dict(r: ModelResponse) -> dict:
    return {"text": r.text, "tool_calls": [vars(tc) for tc in r.tool_calls]}
# ─────────────────────────── 結束 ───────────────────────────


# 外部世界：模型供應商、優惠券服務、寄信服務都活在我們的 process 之外，crash 不會讓它們忘記
class Provider:
    def __init__(self, model: ScriptedModel, fail_first: int = 0):
        self.model, self.fail_first, self.requests = model, fail_first, 0

    def complete(self, messages):
        self.requests += 1
        if self.requests <= self.fail_first:
            raise RateLimited(retry_after=2)
        return self.model.complete(messages)


class CouponService:
    def __init__(self):
        self.issued: list[dict] = []
        self.by_key: dict[str, dict] = {}
        self.dedup_hits = 0

    def issue(self, store: str, amount: int, idempotency_key: str) -> dict:
        if idempotency_key in self.by_key:              # 同一個 key 第二次送來：回傳第一次的結果
            self.dedup_hits += 1
            return self.by_key[idempotency_key]
        coupon = {"coupon_id": f"CP-{len(self.issued) + 1:03d}", "store": store, "amount": amount}
        self.issued.append(coupon)
        self.by_key[idempotency_key] = coupon
        return coupon


coupons = CouponService()
mails: dict[str, str] = {}

def query_delays(month: str) -> list[dict]:
    return [{"store": "S-311", "late": 42}, {"store": "S-502", "late": 17}]

def send_report(to: str, summary: str, idempotency_key: str) -> str:
    mails.setdefault(idempotency_key, summary)          # 寄信服務同樣以 key 去重
    return f"已寄給 {to}"

TOOLS = {"query_delays": query_delays, "issue_coupon": coupons.issue, "send_report": send_report}
SIDE_EFFECTS = {"issue_coupon", "send_report"}

model = ScriptedModel([
    call("query_delays", "c1", month="2026-09"),
    call("issue_coupon", "c2", store="S-311", amount=200),
    call("issue_coupon", "c3", store="S-502", amount=100),
    call("send_report", "c4", to="ops@bluebird", summary="9 月延遲補償：2 家店"),
    # crash 之後重問同一題，模型的措辭可能不同；因為上一次的回答沒被任何人看到，所以沒關係
    call("send_report", "c4", to="ops@bluebird", summary="9 月物流延遲補償：S-311、S-502"),
    say("9 月延遲補償完成：發出 2 張優惠券，報告已寄出。"),
])
provider = Provider(model, fail_first=1)
log, clock = EventLog(), [0.0]
task = "分析 9 月物流延遲並補償受影響的店家"

plan = [("process 1", {"issue_coupon#4"}), ("process 2", {"model#7"}), ("process 3", set())]
for label, crash_at in plan:
    runner = DurableRunner("run-0917", log, provider, TOOLS, SIDE_EFFECTS, crash_at, clock)
    before = provider.requests
    try:
        result = runner.run(task)
        print(f"{label}: {result['status']}  重播 {runner.stats['replayed']}、執行 {runner.stats['executed']}、"
              f"模型請求 {provider.requests - before}")
    except Crash as exc:
        print(f"{label}: CRASH（{exc}）  重播 {runner.stats['replayed']}、執行 {runner.stats['executed']}、"
              f"模型請求 {provider.requests - before}")

again = DurableRunner("run-0917", log, provider, TOOLS, SIDE_EFFECTS).run(task)
print("再查一次：", again["output"])

events = log.load("run-0917")
print("\n事件日誌（completed）：")
for e in events:
    if e["type"] == "completed":
        r = e["result"]
        if e["sig"]["name"] == "model":                   # 模型的結果只顯示它決定做什麼
            r = (f"→ {r['tool_calls'][0]['name']}({json.dumps(r['tool_calls'][0]['args'], ensure_ascii=False)})"
                 if r["tool_calls"] else f"→ 回答「{r['text']}」")
        print(f"  seq {e['seq']}  {e['sig']['name']:<13} {r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)}"[:78])
kinds = {}
for e in events:
    kinds[e["type"]] = kinds.get(e["type"], 0) + 1
print("事件類型統計：", kinds)
print(f"優惠券實際發出 {len(coupons.issued)} 張（去重 {coupons.dedup_hits} 次）、報告寄出 {len(mails)} 封、"
      f"模型請求共 {provider.requests} 次（含 1 次 429）、模擬時鐘 {clock[0]} 秒")

assert again["status"] == "done" and again["executed"] == 0
assert [c["store"] for c in coupons.issued] == ["S-311", "S-502"] and coupons.dedup_hits == 1
assert len(mails) == 1 and provider.requests == 7 and len(model.calls) == 6
assert kinds["completed"] == 9
```

```text
process 1: CRASH（issue_coupon#4 完成後、寫入日誌前）  重播 0、執行 3、模型請求 3
process 2: CRASH（model#7 完成後、寫入日誌前）  重播 3、執行 3、模型請求 2
process 3: done  重播 6、執行 3、模型請求 2
再查一次： 9 月延遲補償完成：發出 2 張優惠券，報告已寄出。

事件日誌（completed）：
  seq 1  model         → query_delays({"month": "2026-09"})
  seq 2  query_delays  [{"store": "S-311", "late": 42}, {"store": "S-502", "la
  seq 3  model         → issue_coupon({"store": "S-311", "amount": 200})
  seq 4  issue_coupon  {"coupon_id": "CP-001", "store": "S-311", "amount": 200
  seq 5  model         → issue_coupon({"store": "S-502", "amount": 100})
  seq 6  issue_coupon  {"coupon_id": "CP-002", "store": "S-502", "amount": 100
  seq 7  model         → send_report({"to": "ops@bluebird", "summary": "9 月物流延
  seq 8  send_report   已寄給 ops@bluebird
  seq 9  model         → 回答「9 月延遲補償完成：發出 2 張優惠券，報告已寄出。」
事件類型統計： {'started': 1, 'scheduled': 11, 'retry': 1, 'completed': 9, 'finished': 1}
優惠券實際發出 2 張（去重 1 次）、報告寄出 1 封、模型請求共 7 次（含 1 次 429）、模擬時鐘 2.0 秒
```

逐行解說這份輸出。

**process 1** 從零開始。第一次模型請求就被回 429，runner 依 retry-after 退避 2 秒後重試成功（所以「模型請求 3」裡有 1 次是被限流的）；接著執行 `query_delays`、第二次模型呼叫，然後執行 seq 4 的 `issue_coupon`：優惠券服務已經發出 CP-001，但在寫入 completed 之前 crash。所以這個 process 成功記錄了 3 個 activity（seq 1 到 3）。

**process 2** 是新的 runner 物件，代表換了一台機器。它重播 seq 1 到 3（「重播 3」），一次模型都沒呼叫。走到 seq 4，日誌裡沒有 completed，只好再執行一次 `issue_coupon`；但因為 key 是 `run-0917:4`，和第一次相同，優惠券服務認出這是重複請求，回傳原本的 CP-001，沒有發第二張券。接著執行 seq 5（模型決定發券給 S-502）與 seq 6（發出 CP-002），然後 seq 7 的模型呼叫完成、還沒寫入就 crash。這次 crash 的代價是一次模型費用：模型已經回答，但沒有被記錄。

**process 3** 重播 seq 1 到 6，重新執行 seq 7 的模型呼叫。注意劇本裡第 7 步的兩個版本措辭不同：第一次寫「9 月延遲補償：2 家店」，重問時寫「9 月物流延遲補償：S-311、S-502」，這模擬了真實模型被重問時不一定給出相同答案。這完全沒有問題，因為第一次的回答從未被記錄、也沒有任何後續動作依賴它；日誌裡的 seq 7 是第二次的版本，之後所有重播都會讀到它。接著寄出報告（seq 8）、模型給出最終回答（seq 9），status 為 done。

「再查一次」用全新的 runner 讀同一份日誌，因為日誌裡已經有 finished 事件，直接回傳結果，assert 驗證它執行了 0 個 activity。下面的事件日誌列出 9 個 completed 事件，每一個 activity 恰好一筆，從日誌就能完整重建這次 run 的 trajectory。事件類型統計裡，scheduled 有 11 筆而不是 9 筆，多出來的兩筆正是 seq 4 與 seq 7 在 crash 後被重新排程；retry 的 1 筆是那次 429。最後一行是對外部世界的稽核：優惠券實際只發出 2 張（去重 1 次），報告只寄出 1 封；模型請求共 7 次，其中 1 次是 429，1 次是 crash 窗口造成的重做，其餘 5 次是必要的呼叫。和 Iris 的事故相比：三次 crash，零重複副作用，額外成本只有一次模型呼叫。

接下來是 background 的部分。下面的程式模擬三個租戶、兩個 worker、一個排程器，時間以 5 分鐘為一格。每個任務的 `progress` 代表已完成的 activity 數，存在 durable 儲存裡（也就是上面那份事件日誌的簡化），所以接手的 worker 能從斷點繼續。這裡用 worker 自我檢查 lease 歸屬來簡化 fencing；真實系統要由儲存層以 fencing token 拒絕舊 worker 的寫入。

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: str
    tenant: str
    steps: int                       # 這個 agent run 要做幾個 activity
    progress: int = 0                # 已完成的步數：寫在 durable 儲存裡，不在 worker 記憶體
    state: str = "ready"             # ready｜leased｜done｜dead
    worker: str = ""
    lease_until: int = 0
    attempts: int = 0


class TaskQueue:
    """有 lease 的佇列：worker 領走任務後要定期 heartbeat，逾期沒續約就視為死亡，任務回到佇列。"""

    def __init__(self, lease: int = 10, max_attempts: int = 3, per_tenant: int = 1):
        self.tasks: list[Task] = []
        self.lease, self.max_attempts, self.per_tenant = lease, max_attempts, per_tenant
        self.log: list[str] = []

    def reap(self, now: int) -> None:
        for t in self.tasks:
            if t.state == "leased" and t.lease_until < now:
                t.attempts += 1
                t.state = "dead" if t.attempts >= self.max_attempts else "ready"
                self.log.append(f"t={now:>3} {t.id} 的 lease 過期（{t.worker} 沒有 heartbeat），回到佇列")

    def take(self, worker: str, now: int) -> Task | None:
        self.reap(now)
        running = {}
        for t in self.tasks:
            if t.state == "leased":
                running[t.tenant] = running.get(t.tenant, 0) + 1
        for t in self.tasks:          # FIFO，但同一租戶同時最多 per_tenant 個：避免一家店吃光所有 worker
            if t.state == "ready" and running.get(t.tenant, 0) < self.per_tenant:
                t.state, t.worker, t.lease_until = "leased", worker, now + self.lease
                self.log.append(f"t={now:>3} {worker} 領走 {t.id}（從第 {t.progress + 1} 步開始）")
                return t
        return None


class Scheduler:
    """每 every 分鐘觸發一次。錯過的觸發只補最近一次；上一輪還沒跑完就跳過（overlap=skip）。"""

    def __init__(self, name: str, tenant: str, every: int, steps: int):
        self.name, self.tenant, self.every, self.steps = name, tenant, every, steps
        self.next_fire = 0
        self.last: Task | None = None

    def tick(self, now: int, q: TaskQueue) -> None:
        if now < self.next_fire:
            return
        due = (now - self.next_fire) // self.every + 1          # 停機期間累積了幾次該觸發的時間點
        fire_at = self.next_fire + (due - 1) * self.every
        self.next_fire = fire_at + self.every
        if due > 1:
            q.log.append(f"t={now:>3} 排程器恢復：累積 {due} 次觸發，只補最近的 t={fire_at}")
        if self.last and self.last.state in ("ready", "leased"):
            q.log.append(f"t={now:>3} 上一輪 {self.last.id} 還在跑，跳過這次觸發")
            return
        self.last = Task(f"{self.name}@{fire_at}", self.tenant, steps=self.steps)
        q.tasks.append(self.last)


q = TaskQueue(lease=10)
q.tasks += [Task("A-月報", "shopA", steps=6), Task("A-補償", "shopA", steps=2), Task("B-對帳", "shopB", steps=3)]
sched = Scheduler("C-庫存", "shopC", every=30, steps=4)
holding: dict[str, Task | None] = {"W1": None, "W2": None}
paused = {"W1": range(15, 40)}      # W1 在 t=15 卡住（例如長時間 GC 或網路分區），t=40 才醒來
scheduler_down = range(70, 160)     # 排程器停機 90 分鐘

for now in range(0, 201, 5):
    if now not in scheduler_down:
        sched.tick(now, q)
    for w in holding:
        if now in paused.get(w, ()):
            continue
        t = holding[w]
        if t is not None and t.worker != w:              # fencing：lease 已經被別人接手，舊 worker 不得再寫
            q.log.append(f"t={now:>3} {w} 醒來，發現 {t.id} 已由 {t.worker} 接手，放棄而不寫入")
            t = None
        if t is None or t.state != "leased":
            t = holding[w] = q.take(w, now)
        if t is None:
            continue
        t.progress += 1                                  # 做一步 activity，結果先寫進 durable 儲存
        t.lease_until = now + q.lease                    # heartbeat：證明自己還活著
        if t.progress == t.steps:
            t.state, holding[w] = "done", None
            q.log.append(f"t={now:>3} {w} 完成 {t.id}")

print("\n".join(q.log))
done = [t.id for t in q.tasks if t.state == "done"]
print("完成：", done)
assert set(done) == {t.id for t in q.tasks} and all(t.progress == t.steps for t in q.tasks)
assert "C-庫存@30" not in done and "C-庫存@90" not in done and "C-庫存@150" in done
```

```text
t=  0 W1 領走 A-月報（從第 1 步開始）
t=  0 W2 領走 B-對帳（從第 1 步開始）
t= 10 W2 完成 B-對帳
t= 15 W2 領走 C-庫存@0（從第 1 步開始）
t= 30 上一輪 C-庫存@0 還在跑，跳過這次觸發
t= 30 W2 完成 C-庫存@0
t= 35 A-月報 的 lease 過期（W1 沒有 heartbeat），回到佇列
t= 35 W2 領走 A-月報（從第 4 步開始）
t= 40 W1 醒來，發現 A-月報 已由 W2 接手，放棄而不寫入
t= 45 W2 完成 A-月報
t= 50 W1 領走 A-補償（從第 1 步開始）
t= 55 W1 完成 A-補償
t= 60 W1 領走 C-庫存@60（從第 1 步開始）
t= 75 W1 完成 C-庫存@60
t=160 排程器恢復：累積 3 次觸發，只補最近的 t=150
t=160 W1 領走 C-庫存@150（從第 1 步開始）
t=175 W1 完成 C-庫存@150
t=180 W1 領走 C-庫存@180（從第 1 步開始）
t=195 W1 完成 C-庫存@180
完成： ['A-月報', 'A-補償', 'B-對帳', 'C-庫存@0', 'C-庫存@60', 'C-庫存@150', 'C-庫存@180']
```

按時間讀這份日誌。t=0，W1 領走 shopA 的月報、W2 領走 shopB 的對帳；shopA 的另一個任務「A-補償」雖然排在佇列裡，但因為每個租戶同時只能跑一個，它必須等月報結束，這就是租戶並行上限。t=10 對帳完成，t=15 W2 領走排程器在 t=0 觸發的庫存任務。t=30 排程器又到了觸發時間，但 t=0 那一輪還在跑，依「重疊時跳過」政策跳過這次。

t=15 起 W1 卡住了（模擬長時間 GC 或網路分區），停止 heartbeat。它最後一次續約在 t=10，lease 在 t=20 到期；W2 在 t=35 需要新任務時，佇列發現月報的 lease 已過期，把它放回 ready，W2 隨即領走，而且是「從第 4 步開始」：W1 做完的 3 步在 durable 儲存裡，不需要重做。t=40 W1 醒來，發現月報已經由 W2 接手，放棄而不寫入，這就是 fencing 要保護的情況。月報在 t=45 完成後，A-補償才終於被領走。

t=70 到 t=160 排程器停機。恢復時它算出累積了 3 次該觸發的時間點（t=90、120、150），依「只補最近一次」政策只建立 t=150 的任務，之後在 t=180 恢復正常節奏。最後一行列出所有完成的任務，assert 驗證每個任務都完整跑完、t=30 與 t=90 的觸發確實被跳過。這 100 行程式省略了很多真實系統的細節（持久化的佇列、真正的 fencing token、dead letter、優先順序），但每一個決策點都和 22.8 節的架構圖一一對應。

| 版本 | 新增的能力 | 修掉的事故或風險 | 對應小節 |
|---|---|---|---|
| `loom` v0.1（第 4 章） | loop、錯誤回填、停止條件 | 例外炸穿、無限迴圈、成本失控 | 第 4 章 |
| `loom.durable`：事件日誌與重播 | 每次 model／tool 呼叫記成事件，crash 後重播 | 部署或 crash 讓任務從頭重來 | 22.3、22.4 |
| 加上簽章比對 | 重播時比對名稱與參數摘要 | 改版或不確定程式碼造成的靜默錯誤 | 22.5 |
| 加上 idempotency key 與重試 | `run_id:seq` 傳給有副作用的 tool；429 退避 | 重複發券、重複寄信、429 風暴 | 22.6 |
| 加上 timer 與 signal | 等待時讓出 worker，事件到達再重播 | process 空等兩天、核准紀錄遺失 | 22.7 |
| 加上佇列與排程 | lease、heartbeat、租戶上限、misfire 與 overlap 政策 | worker 死掉後任務卡住、大租戶吃光資源、停機後湧入 | 22.8 |

`loom.durable` 刻意沒有做的事也要列清楚：日誌存在記憶體的 list 裡（真實系統要用資料庫，且寫入要確認持久化後才繼續）；沒有 payload 外存與分段續跑；平行 tool call 是序列執行的；沒有版本綁定；佇列沒有持久化。第 36 章的 production 架構會把 event log、queue、sandbox pool 放進完整的參考架構，第 45 章會把 `loom.durable` 組進完整的 framework。

## 22.11 實務應用

durable execution 的技術在不同產品中長得很不一樣，因為「任務有多長、副作用有多危險、要等誰」各不相同。以下四個情境說明本章的機制怎麼落地。

**情境一：青鳥的月度補償 research agent（L5 背景任務）**。這是本章的主線。任務由排程器每月 1 日觸發，錯過的觸發要全部補跑（每個月都要補償），重疊時排隊。每次 model call 與 tool call 都是 activity；`issue_coupon` 帶 `run_id:seq` 當 idempotency key，並在優惠券服務加上 `(store, month)` 的唯一約束作為第二道防線。單筆超過 L4 邊界的補償走 22.7 節的 signal 等待，48 小時沒人處理就升級。所有 run 在月初同時啟動會打爆模型配額，所以佇列層依 TPM 配額限制全域並行數，並對每個租戶設上限。報告寄送是不可冪等的動作，以 outbox 寫入自家資料庫後再由寄信服務送出。

**情境二：從 issue 到 PR 的 background coding agent**。開發者在 issue 上指派 agent，agent 在 sandbox 裡讀程式、改檔案、跑測試，最後開 PR；第 43 章會完整做這個設計演練。這類任務的特殊之處是**長時間 activity**：一次完整測試可能跑二十分鐘，所以要用 heartbeat 判斷 sandbox 是否還活著，並以 `run_id:seq` 命名 sandbox 與產出物，worker 換手時能接回同一個 sandbox，而不是重建環境再跑一次。等 CI 結果是典型的 signal：agent 推完 commit 後進入 WAITING，CI 的 webhook 把結果寫進日誌再喚醒。開 PR 是有副作用的動作，重試前要先查「這個 branch 是否已有 PR」。公開資料中，主流的雲端 coding agent 都採用非同步提交、背景執行、完成後通知的形態，例如 OpenAI Codex 的雲端任務與 GitHub Copilot coding agent 在 GitHub Actions 環境中執行。

**情境三：跨天的退款核准與客服跟催**。客服 agent 遇到 3,200 元的退款，超出 L4 邊界，需要主管核准（第 21 章）；或是承諾顧客「三天後若還沒收到貨，主動幫您追蹤」。這些都是「對話結束了，但任務還沒結束」的情境。用 durable timer 實作三天後的跟催，比在資料庫放一筆「待辦」再寫另一支 cron 掃描可靠得多，因為等待點、截止時間與後續動作都在同一個 workflow 裡，不會出現掃描程式和業務邏輯不同步的問題。核准與跟催的 workflow 可能存活好幾天，橫跨多次部署，所以版本策略特別重要：新版 prompt 上線時，舊的 run 要能用舊版本跑完。

**情境四：企業的深度研究與報表 agent**。使用者問一個需要半小時以上的研究問題，agent 平行派出多個 subagent 搜尋、閱讀、綜合（第 40 章）。這裡 durable execution 的價值在 fan-out：十個 subagent 中有一個所在的 worker 死掉，只需要重做那一個，其餘九個的結果都在日誌裡；完成順序也被記錄，重播時 orchestrator 看到的順序不會改變。公開資料中，Gemini 的 Deep Research agent 規定必須以 background 模式執行，客戶端可以輪詢或用事件 id 續傳串流；這正是「提交、取得 id、斷線後續傳」的 background agent 介面。這類任務的 messages 很大，要搭配 payload 外存，日誌裡只記參照。

| 情境 | 主要失敗來源 | 關鍵機制 | 特別注意 |
|---|---|---|---|
| 月度補償 agent | 部署、429 風暴、等核准 | 事件重播、idempotency key、排程補跑 | 業務唯一約束當第二道防線 |
| background coding agent | sandbox 死掉、長時間測試、等 CI | heartbeat、可接手的 sandbox、signal | 開 PR 前先查是否已存在 |
| 跨天核准與跟催 | 跨多次部署、人遲遲不回應 | durable timer、signal、逾時升級 | 長壽 run 的版本相容 |
| 深度研究 agent | fan-out 中單一 worker 死掉、payload 大 | 逐一 activity 重播、完成順序記錄 | payload 外存、串流與日誌分離 |

這張表的共同點是：agent 的 loop 本身幾乎不用改，改的是「哪些呼叫要變成 activity、哪些 activity 需要 key、等待點放在哪裡」。這也是為什麼主流框架與 durable 平台的整合大多做成「自動把 model call 與 tool call 包成 activity」：agent 開發者照常寫 loop，durability 由執行層提供。

## 22.12 設計檢查清單

設計或審查一個長時間 agent 時，逐項回答下面的問題。

1. 這個任務的執行時間分布是多少？最長的 1% 會不會跨越部署週期？如果會，是否已經放棄「process 活到最後」的假設？
2. 恢復策略選了哪一種：從頭重跑、快照，還是事件重播？選擇的理由是否寫在 design doc 裡？
3. 每一次 model call 與 tool call 是否都經過一個會記錄結果的 activity 層？workflow 程式碼裡是否還有直接的 I/O？
4. workflow 程式碼裡是否還有 `now()`、亂數、UUID、讀設定或環境變數等不確定來源？是否都已改成 activity 或平台提供的原語？
5. 重播時是否會比對 activity 的名稱與參數，不一致時明確失敗，而不是靜默地回傳錯誤的紀錄？
6. prompt、tool 或程式碼改版時，進行中的 run 怎麼處理：版本綁定、版本標記，還是分段續跑？
7. 每一個有副作用的 tool，idempotency key 是否在意圖產生時就固定（依 `intent_fields` 推導，或至少是 `run_id:seq`），而不是在每次執行時產生？
8. 不支援 idempotency key 的下游，是否有先查再做、去重表或 outbox 的替代方案？真正不可逆又無法去重的動作，是否需要人工核准？
9. 每種 activity 的重試政策（可重試錯誤、退避、最大次數、總時限）是否分開設定？不可重試的錯誤是否明確列出？
10. 等人或等外部事件時，是否會釋放 worker？截止時間是否在第一次執行時就寫進日誌？逾時後的升級路徑是什麼？
11. 日誌的大小是否有上限？大型 payload 是否外存？超長任務是否會分段續跑？
12. 佇列是否有 lease、heartbeat 與 fencing？重試用盡的任務是否進入 dead letter 並告警？
13. 是否設定了租戶層級的並行上限，並依模型供應商的配額反推全域並行數？
14. 排程的錯過觸發與重疊政策各是哪一種？是否和「每次觸發處理什麼資料」一致？
15. 使用者能否查詢 run 的狀態、收到完成或需要介入的通知，並且取消？取消時已產生的副作用如何補償？

## 22.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| crash 後重試，副作用發生兩次（重複發券、重複寄信） | 有副作用的 tool 沒有 idempotency key，或 key 在每次執行時才產生 | 比對兩次請求的 key；檢查 key 是否含有 `uuid4()` 或時間戳 | 用 `run_id:seq` 等由日誌決定的值當 key；下游加去重表或業務唯一約束 |
| 部署後大量 run 卡住，回報 non-determinism 錯誤 | 新版程式碼改了 activity 順序或拼 messages 的方式，重播舊歷史對不上 | 看錯誤指出的 seq，比對日誌與新程式在該步要做的 activity | 版本綁定（舊 run 由舊版 worker 跑完），或用版本標記包住新邏輯 |
| 重播後結果和原本不同，但沒有任何錯誤 | workflow 裡有不確定來源（時間、亂數、直接讀 DB），且重播時沒有比對簽章 | 用同一份日誌在兩台機器重播，比較產生的 activity 序列 | 不確定的值一律經由 activity 記錄；重播時比對名稱與參數摘要 |
| 等核准的任務永遠不逾時 | 截止時間在每次重播時用 `now + timeout` 重算 | 檢查日誌裡是否有記錄 timer 的截止時間 | 第一次執行時把截止時間寫進日誌，重播時讀回 |
| 同一個 run 被兩個 worker 同時推進 | lease 過期後舊 worker 醒來繼續寫入，沒有 fencing | 日誌中同一個 seq 出現兩筆 completed，或來自不同 worker | 儲存層以 fencing token 拒絕舊版本的寫入 |
| 月初大量 429，任務延遲數小時 | 所有排程同時觸發，worker 數未依配額限制 | 看 429 的時間分布與並行 run 數 | 依 TPM／RPM 配額限制全域並行；排程加隨機延遲；activity 遵守 retry-after |
| 排程器恢復後瞬間湧入大量任務 | 錯過觸發的政策是「全部補跑」，但任務其實只需要最新狀態 | 看恢復時建立的任務數與觸發時間 | 依資料性質改為只補最近一次；補跑時限制速率 |
| 長任務越跑越慢，重播要很久 | 日誌累積大量大型 payload（完整 messages） | 看單一 run 的事件數與總大小 | payload 外存只記參照；以 compaction 摘要分段續跑 |

## 本章重點整理

- 長時間 agent 的第一條假設是「執行它的 process 一定會在任務結束前死掉」；部署、擴縮、OOM 與 rate limit 都是常態，要的是死了也沒關係的執行模型。
- 恢復策略有三種：從頭重跑適合短而唯讀的任務，快照以步驟為單位恢復，事件重播以單次外部呼叫為單位恢復並且不重做已完成的呼叫。
- durable execution 把程式切成確定性的 workflow 與不確定的 activity；對 agent 而言，loop 是 workflow，每次 model call 與 tool call 都是 activity。
- event history 是只追加的日誌，記錄每個 activity 的結果；恢復時重新執行 workflow 程式碼，已記錄的呼叫直接讀紀錄，messages 可以從日誌完整重建。
- replay 成立的前提是 workflow 的確定性：時間、亂數、外部狀態與模型回答都必須經由 activity 進入 workflow，重播時要比對簽章，不一致就明確失敗。
- prompt 與程式碼改版是 agent 最常見的不確定來源，版本綁定、版本標記或分段續跑的策略要在一開始就決定。
- activity 的執行保證是至少一次，因為「做完」與「記錄」之間的縫隙無法消除；效果只發生一次，必須靠冪等的 activity 與下游服務。
- idempotency key 要在意圖產生時就固定，由執行層依 `intent_fields` 推導（沒有意圖欄位時至少用 `run_id:seq`）；在每次執行時才產生的 UUID 等於沒有 key。
- 不支援 key 的下游要用先查再做、去重表或 outbox 補救，不可逆又無法去重的動作應經過人工核准。
- 等待也是事件：durable timer 與 signal 讓 agent 等人核准時釋放 worker，截止時間要在第一次執行時寫進日誌。
- 長任務的日誌會越來越大，要用 payload 外存與分段續跑控制；分段時的精簡狀態正好就是 compaction 摘要。
- background agent 需要有 lease、heartbeat 與 fencing 的佇列，以及租戶層級的並行上限與依配額反推的背壓。
- 排程要明確選擇錯過觸發的補跑政策與重疊政策，依「每次觸發處理什麼資料」決定，而不是用預設值。
- Temporal、Restate、DBOS、Inngest 與框架內建的 checkpointer 解決的是同一類問題，差別主要在部署形態與恢復粒度；選型看任務長度、是否要等人與團隊願意營運的基礎設施。

## 延伸問答

> [!question]- Q1. 事件重播（durable execution）和 state 快照（checkpoint）都能讓 agent 從斷點恢復，兩者的本質差別是什麼？什麼時候選哪一個？
> 本質差別在「狀態從哪裡來」。快照直接序列化並保存 state 本身，恢復時信任這份 state；事件重播只保存外部呼叫的結果，恢復時用「確定性的程式碼加上事件」重新算出 state。因此快照對程式碼沒有確定性的要求，但每一步都要存一份可能很大的 state；事件重播只追加小事件，代價是 workflow 必須確定性。粒度也不同：快照以步驟或節點為單位，同一步裡做到一半的平行呼叫可能要整步重做；事件重播以單次呼叫為單位。
>
> 選擇上，以節點組成、需要 interrupt 與 time travel 的 graph（第 19 章），快照很自然，因為快照正好對應圖上的位置；任務長、副作用多、要跨天等人、需要計時器與跨服務重試，事件重播加上一個 durable 平台比較完整。兩者也可以並存：用 graph 框架描述流程與快照，再把整個 graph run 放進 durable workflow 中執行。

> [!question]- Q2. 模型的回答本身是不確定的，為什麼 agent 還能做 durable execution？重播時模型給出不同答案怎麼辦？
> durable execution 只要求 workflow 確定，不要求 activity 確定。模型呼叫被包成 activity，它的回答在第一次拿到時就寫進日誌；重播時 runner 根本不會再呼叫模型，而是直接回傳日誌裡的那個回答。所以對 workflow 來說，模型的回答在重播時是一個確定的值，「不同答案」的問題不會發生。
>
> 唯一會重新呼叫模型的情況，是回答拿到了但還沒寫進日誌就 crash（本章動手做的 process 2）。這時重問一次，模型可能給出不同的答案，但這是安全的：第一次的回答從未被記錄，也沒有任何後續動作依賴它，等於從沒發生過。真正危險的是相反的情況：用第一次的回答做了副作用卻沒記錄那個回答，這種設計錯誤會讓重播後的決策和已發生的副作用不一致，所以「結果拿到後立刻寫入、寫入後才做下一步」的順序不能顛倒。

> [!question]- Q3. 你在 production 看到：每週部署後，大約 3% 的長時間 run 進入 non-determinism 錯誤而卡住。你會怎麼排查與修正？
> 先看錯誤指出的 seq，比對日誌在那一步記錄的 activity 與新版程式碼在那一步想做的 activity。對 agent 來說，最常見的原因有三個：新版在 loop 中插入或刪除了一個步驟（例如加了一個驗證 tool）；改了拼 messages 的方式（system 提示、tool 定義或訊息格式改變，導致 model activity 的參數摘要不同）；或是 workflow 裡偷偷用了時間、亂數或讀設定，新版剛好改變了分支。3% 這個比例本身也是線索：通常剛好是「部署當下正在跑、而且已經走過改動點」的 run。
>
> 修正分兩層。短期讓卡住的 run 用舊版 worker 跑完（保留舊版 worker 一段時間，依版本路由），或對它們做明確的處置（例如以目前的摘要狀態開新 run）。長期要建立版本策略：run 啟動時記下程式與 prompt 版本，部署時讓新舊版本 worker 並存直到舊 run 清空；需要立即生效的改動用版本標記包住；並在 CI 中加入重播測試：把 production 的一批歷史日誌拿來用新程式碼重播，部署前就抓出不相容。

> [!question]- Q4. 程式找錯：下面的 tool 實作宣稱「有 idempotency key，所以重試安全」。它錯在哪裡？
> ```python
> def issue_coupon(store: str, amount: int) -> dict:
>     key = f"{store}-{amount}-{time.time()}"
>     return coupon_api.issue(store, amount, idempotency_key=key)
> ```
> key 裡含有 `time.time()`，每次執行都不同，所以 crash 後的重試會帶著一個新的 key，下游把它當成全新的請求，再發一張券。這和完全不帶 key 的效果一樣，只是更難發現，因為 code review 時看起來「有 key」。如果把時間拿掉只用 `store-amount`，又會犯相反的錯：同一個 run 裡兩次合法的發券（例如這個月對同一家店補償兩次不同事件），會被誤判為重複而只發一次。
>
> 正確做法是讓 key 由「意圖的身分」決定，而且由執行層推導、從外部傳進 tool：第 5 章的做法是 run id 加上 tool 名稱與 `intent_fields`（例如店家、金額，必要時加上補償事件 id），沒有宣告意圖欄位時才退回 runner 傳進來的 `run_id:seq`。兩者在重試與重播時都不會變；意圖推導的 key 還能擋住模型在後面的步驟重複提出同一個意圖。tool 本身不應該自己產生 key，模型也不應該看得到或填得了它。「一家店一個月只能補償一次」這種業務規則，則要在資料庫用 `(store, month)` 的唯一約束保證，那是和 idempotency 不同的另一層防線。

> [!question]- Q5. 估算題：月度補償 agent 平均 120 次模型呼叫，每次平均 input 30,000 tokens、output 500 tokens。若第 90 次呼叫時 crash，比較「從頭重跑」與「事件重播」多花的模型費用。
> 從頭重跑時，前 90 次呼叫都要重做，多花 90 ×（30,000 ＋ 500）＝ 2,745,000 tokens，約為整個任務 120 × 30,500 ＝ 3,660,000 tokens 的 75%。實際上 input 是隨步數成長的（第 4 章），後面的呼叫比前面的大，所以用平均值估算會略為高估重跑前段的成本，但量級不變：一次 crash 就多付大半個任務的錢。若每週部署都會砍到一部分任務，這筆費用會成為固定開銷。
>
> 事件重播時，前 89 次呼叫的結果已在日誌中，只有「拿到回應但還沒記錄」的那一次可能要重做，最多多花一次呼叫，約 30,500 tokens，不到整個任務的 1%。重播本身只是重跑 orchestration 程式碼，成本可忽略。要補充的是儲存成本：120 次呼叫的完整 messages 如果都寫進日誌，總量相當可觀，所以實務上會外存 payload、只記參照，或只記每次新增的內容。這個估算也說明了為什麼 crash 窗口要盡量短：結果拿到後立刻寫入，是 durable runner 最基本的紀律。

> [!question]- Q6. 營運 agent 等主管核准時，Iris 想用「每分鐘查一次資料庫的 while 迴圈」實作，老陳反對。請說明 durable timer 與 signal 的做法好在哪裡。
> 輪詢迴圈有三個問題。第一，它在等待期間佔著一個 process 或 worker，等兩天就佔兩天，而且一千個等待中的任務就要一千個 worker。第二，它把等待狀態放在 process 的記憶體與程式計數器裡，部署或 crash 時等待就消失了，重啟後要靠額外的掃描程式找回「哪些任務在等什麼」，這段程式和業務邏輯很容易不同步。第三，逾時的計算常常寫錯：如果每次重啟都重新計時，任務可能永遠不會逾時。
>
> durable timer 與 signal 把等待本身變成日誌中的事件：第一次走到等待點時寫下「等 approval、最晚到第 48 小時」，然後讓出 worker；等待期間沒有任何 process 在跑。主管核准時，外部 API 只是把 signal 寫進日誌並喚醒 run；計時器到期由平台喚醒。worker 重播後從日誌讀到 signal 或逾時，繼續往下。等待狀態、截止時間與後續動作都在同一個 workflow 程式碼中，跨部署也不會遺失。

> [!question]- Q7. 面試追問：設計一個支援一萬個並行 background agent run 的系統，佇列與 worker 層你會怎麼設計？
> 先把「run」與「worker」解耦：run 的狀態全部在 durable 儲存（事件日誌），worker 是無狀態的執行者，任何 worker 都能接手任何 run。一萬個並行 run 中，大多數時間其實在等模型回應或等外部事件，所以真正同時執行的 activity 數遠少於一萬；worker 數量要依「模型供應商的 TPM／RPM 配額」與「每個 activity 的平均時長」反推，而不是依 run 數量。等待中的 run 不佔 worker，這是能撐到一萬的關鍵。
>
> 佇列層要有 lease 與 heartbeat（worker 死掉時任務自動回到佇列）、fencing token（防止舊 worker 繼續寫入）、dead letter queue（重試用盡的任務等人處理）、租戶層級的並行上限與加權公平排程（避免大租戶吃光資源）、以及依配額的全域背壓。觀測面要追蹤佇列深度、等待時間、lease 過期率與 429 比例，並能從任何一個 run id 查到完整的事件歷史（第 29 章）。最後要談取捨：自建這一層的複雜度很高，多數團隊應該評估現成的 durable 平台或託管 agent 服務，把精力放在 agent 本身。

> [!question]- Q8. 排程器停機了 6 小時，恢復後有三種排程：每小時的帳務對帳、每小時的庫存異常同步、每天早上 9 點的「今日待辦」推播。錯過的觸發各該怎麼處理？
> 帳務對帳的每次觸發處理的是不同時段的資料（第 3 小時的交易、第 4 小時的交易……），漏掉任何一次都會讓帳對不起來，所以要全部補跑。但六次同時觸發會瞬間湧入，要限制補跑的速率，並確保每次任務以「觸發時間」而不是「實際執行時間」決定處理哪個時段，否則六個任務會處理同一個小時的資料。
>
> 庫存異常同步處理的是「最新狀態」，舊時段的庫存快照沒有意義，所以只補最近一次就夠，重疊時跳過。「今日待辦」推播有很強的時效：如果恢復時已經是下午三點，早上九點的推播再送出去只會造成困擾，應該不補或改成內容不同的「補發」通知，並觸發告警讓人知道漏發了。這題的重點是：錯過觸發的政策沒有全域的正確答案，必須依「每次觸發處理的資料是什麼、過期後還有沒有價值」逐一決定，並寫進設定，而不是交給排程器的預設值。

## 延伸閱讀

- Temporal 文件〈AI Cookbook〉
- Restate 文件〈AI agents〉章節
- DBOS 文件〈Build Durable AI Agents〉
- Anthropic Engineering Blog〈Effective harnesses for long-running agents〉（2025）
- Anthropic Engineering Blog〈Scaling Managed Agents〉（2026）
- HumanLayer，Dex Horthy〈12-Factor Agents〉（2025，GitHub），尤其是「Launch/Pause/Resume with simple APIs」與「Make your agent a stateless reducer」兩節
- Martin Kleppmann《Designing Data-Intensive Applications》（O'Reilly，2017），第 8、9、11 章關於 fencing token、exactly-once 與事件日誌的討論
