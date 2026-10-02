---
chapter: 36
title: Production 架構與部署
part: 8
---

# 第 36 章　Production 架構與部署

> [!abstract] 本章地圖
> **核心問題**：當一個 agent 從「一個 process 跑一個使用者」變成「數千個租戶共用的線上服務」，要長出哪些元件，才能同時扛住流量、隔離租戶、安全地改版，並在供應商或整個區域故障時活下來？
>
> **你會學到**：
> - 畫出 production agent 平台的參考架構，說清楚 API gateway、agent service、session store 與 event log、job queue、sandbox pool、model gateway、tool gateway、memory／retrieval store、observability pipeline 各自的職責、擴展方式與失效模式
> - 把 harness 設計成 stateless：任何 worker 都能從 event log 喚醒任何 session，並用序號擋住過期的 worker
> - 設計多租戶隔離與 per-tenant token bucket、配額與並行上限，讓一個大租戶的 fan-out 不會拖垮所有人
> - 把 prompt、model snapshot、tool 版本與 policy 綁成一個不可變的 release，並用 canary、A/B、shadow 安全地推出
> - 寫出依線上 eval 指標自動推進或回滾的 canary controller，以及帶 circuit breaker 與合規約束的 model fallback
> - 為每個元件定出 RPO 與 RTO，設計區域故障與模型供應商故障時的降級模式
>
> **前置知識**：第 17 章（sandbox 與 pool）、第 22 章（durable execution、lease 與佇列）、第 25 章（model adapter 與 routing）、第 27 章（eval）、第 29 章（tracing）、第 33 章（identity 與多租戶授權）、第 35 章（設計方法論與容量估算）

## 36.1 故事：上線前一週的三個事故

青鳥科技決定把三個 agent 變成產品：數千家網店可以在後台開啟「AI 客服」，大型客戶還能加購「營運分析助理」。過去一年，客服 agent、內部 coding agent 與營運 research agent 都跑在各自的服務裡，共用部分抽成了 `loom`，但每個服務都是一個團隊自己顧、自己部署、自己接模型 API。阿哲排定雙十一前三週正式開放，要求在開放前先讓兩百家店家進入 beta。

beta 第一週就出了三件事。週二下午，最大的 beta 客戶「萬家購物」讓營運分析助理一次分析三百個商品類別，research agent 依第 20 章的設計平行派出幾十個子 agent，每個都在大量讀報表。整個公司共用同一組模型 API 金鑰，供應商給的每分鐘 token 上限（TPM）在兩分鐘內被吃光。接下來二十分鐘，所有店家的 AI 客服都收到 429（請求太多），畫面只顯示「系統忙碌中」。萬家購物的分析做完了，另外一百九十九家店的客人卻在等。

週四，Iris 修改了客服 agent 的 system prompt，讓回覆語氣更口語，同一天平台組把模型設定從帶日期的 snapshot 改成供應商的「最新版」別名，想順便吃到新模型的改進。兩件事都直接推到全部租戶。週五的抽樣評分發現退款判斷的正確率掉了好幾個百分點，可是沒有人說得清是 prompt 還是模型造成的；trace 裡只記了「客服 agent」，沒有記是哪個 prompt 版本搭配哪個模型版本。要回滾時，大家才發現 prompt 存在資料庫、模型名稱寫在環境變數、tool 描述寫在程式碼裡，三者沒有一起版本化，根本沒有「上一版」可以回去。

週六凌晨的例行部署則讓 agent service 的 pod 全部滾動重啟。客服 agent 的對話狀態放在 pod 的記憶體裡，正在進行中的四百多個對話全部消失，使用者回到聊天視窗時看到的是一個不記得前情的 agent。剛好同一時間，主要模型供應商的一個區域發生故障四十分鐘，平台沒有任何備援路徑，只能整個掛上維護公告。

週一的檢討會上，老陳把三件事寫在白板左邊，右邊畫了一張很大的方塊圖。「這三件事都和模型聰不聰明無關，」老陳說，「第一件是沒有租戶隔離，第二件是沒有版本與發布紀律，第三件是 harness 有狀態、模型沒有備援。一個 agent 變成平台，問題就從『loop 寫得對不對』變成『分散式系統設計得對不對』。」Maya 在旁邊補了一句：「還有 tool 呼叫要有一個集中的地方做授權和稽核，不然兩百個租戶的退款權限，我沒辦法審。」

這一章就是那張方塊圖。我們先看參考架構，再逐一拆開每個元件的職責、擴展方式與失效模式；接著處理多租戶與配額、版本與發布、災難復原三件跨元件的事；最後在「動手做」用 Python 模擬 per-tenant token bucket、model gateway 的 fallback 與熔斷，以及依 eval 指標自動回滾的 canary controller。

## 36.2 參考架構全景：一個請求會經過哪些元件

先建立整體地圖。下面這張圖是一個多租戶 agent 平台的**參考架構**（reference architecture，意思是「大多數系統都會長成這樣的骨架」，不是唯一正解）。圖中每一個方塊都對應前面某一章講過的能力，本章的工作是把它們放進同一個服務拓撲，說清楚邊界與資料流。

```text
                    使用者 / 店家後台 / 外部系統（webhook、排程）
                                     │ HTTPS、SSE、WebSocket
                                     ▼
 ┌──────────────────────── API gateway ────────────────────────┐
 │ 認證（租戶、使用者）  請求級 rate limit  路由  串流連線管理  │
 └───────────┬──────────────────────────────────┬──────────────┘
      同步互動│                          非同步任務│（報表、coding、research）
             ▼                                  ▼
 ┌─ agent service（stateless harness）─┐    ┌─ job queue ─┐    ┌─ workers ─────┐
 │ wake(session) → 重建 context        │    │ 依租戶與     │──► │ 同一套 harness │
 │ loop：model → policy → tool → append│◄───│ 優先序分流   │    │ 長時間執行     │
 └──┬──────────┬─────────────┬─────────┘    └─────────────┘    └──┬────────────┘
    │          │             │                                     │
    │          │             └──────────── 同上（共用下列元件）────┘
    ▼          ▼             ▼
 ┌─ session store ─┐ ┌─ model gateway ──────────┐ ┌─ tool gateway ─────────────┐
 │ session 中繼資料 │ │ 配額 → cache → routing   │ │ 授權 → policy → 憑證注入   │
 │ release 綁定     │ │ → breaker → adapter      │ │ → idempotency → 稽核       │
 ├─ event log ─────┤ │ → 計量                   │ └──┬───────────┬────────────┘
 │ append-only      │ └──┬──────────┬───────────┘    │           │
 │ 每個 session 一條│    ▼          ▼                ▼           ▼
 └─────────────────┘  供應商 A   供應商 B／自架  sandbox pool  業務 API／MCP server
                      （多區域）  小模型          （code 執行） （訂單、金流、ERP）
 ┌─ memory／retrieval store ─┐                         ┌─ release registry ────────┐
 │ 依租戶分區的記憶與知識庫   │                         │ prompt、model、tool、policy│
 └───────────────────────────┘                         │ 綁成不可變的 release       │
                                                        └───────────────────────────┘
 ═══════ observability pipeline：trace、metric、成本、稽核、線上 eval 抽樣（每個元件都送）═══════
```

沿著一個請求走一遍。店家的客人在聊天視窗問「B-1042 到哪了」，請求先到 **API gateway**：它驗證這是哪個租戶、哪個使用者，做請求層級的限流，然後把請求交給 **agent service**。agent service 裡跑的是第 4 章那個 loop 的 production 版，它本身不保存任何對話狀態，而是用 session id 從 **session store** 找到這個對話綁定的 release（哪一版 prompt、模型與 tools），再從 **event log** 讀出歷史、重建 context。

loop 每一次要呼叫模型，都經過 **model gateway**：先檢查這個租戶的 token 配額，再看能不能命中快取，然後依 routing 規則選模型、檢查該供應商的熔斷器，最後透過 adapter 呼叫供應商並記錄用量。模型要求呼叫 tool 時，請求經過 **tool gateway**：確認這個租戶、這個使用者、這個 agent 版本有沒有權限呼叫 `refund`，套用 policy（例如 500 元以下自動），把真正的業務 API 憑證注入請求，用 idempotency key 去重，並寫下稽核紀錄。需要執行程式碼的 tool 則送到 **sandbox pool**。每一個步驟的結果都 append 進 event log，loop 才繼續下一圈。

右邊那條路是非同步任務。營運分析、coding 任務動輒跑幾十分鐘，不能讓 HTTP 連線一直開著等，所以 API gateway 把它們變成 **job queue** 裡的工作，由 **worker** 撿起來執行。worker 跑的是同一套 harness，共用同一組 model gateway、tool gateway 與 event log，差別只在觸發方式與時間尺度。底部的 **observability pipeline** 收集所有元件的 trace、指標、成本與稽核事件，並抽樣一部分 session 交給線上 eval 評分，這些分數就是後面 canary controller 判斷「新版本有沒有變差」的依據。

| 元件 | 主要職責 | 有沒有狀態 | 怎麼擴展 | 典型失效模式 |
|---|---|---|---|---|
| API gateway | 認證、請求級限流、路由、串流連線 | 無（連線狀態除外） | 水平擴展；串流連線要注意 drain | 長連線在部署時被切斷；認證服務故障導致全面拒絕 |
| agent service | 跑 harness loop、組 context、呼叫兩個 gateway | 無（全部在 event log） | 依並行 session 數水平擴展 | 記憶體被大 context 撐爆；過期 worker 寫入造成歷史分岔 |
| session store／event log | session 中繼資料、release 綁定、append-only 事件 | 有，系統的真相來源 | 依 session id 分片；冷資料歸檔 | 熱分片；寫入延遲拖慢每一步；跨區複製落後 |
| job queue＋workers | 非同步任務、優先序、重試、排程 | 佇列本身有狀態 | 依佇列深度與等待時間擴展 worker | 重複投遞造成重複執行；毒訊息卡住佇列；大租戶塞滿佇列 |
| sandbox pool | 執行程式碼、檔案系統、shell | 每個 sandbox 有短暫狀態 | 預熱池＋按需配置；依啟動延遲調整池大小 | 冷啟動延遲；sandbox 洩漏佔滿資源；egress 設定錯誤 |
| model gateway | 配額、快取、routing、熔斷、fallback、計量 | 限流計數與快取（可重建） | 水平擴展，計數放共享儲存 | 重試放大打爆供應商；fallback 到未驗證模型；快取跨租戶命中 |
| tool gateway | 授權、policy、憑證注入、去重、稽核 | 去重表與稽核日誌 | 水平擴展；稽核寫入要可靠 | policy 服務故障時 fail-open；憑證外洩；重複副作用 |
| memory／retrieval store | 長期記憶、知識庫、向量索引 | 有 | 依租戶分區；索引分片 | 跨租戶檢索洩漏；索引版本與 release 不一致 |
| observability pipeline | trace、metric、成本、稽核、eval 抽樣 | 有（分不同保存期限） | 收集器水平擴展；抽樣 | PII 未遮蔽就落地；高峰時丟資料；成本無法歸屬到租戶 |

這張表是全章的索引，後面每一節都在展開其中一列或幾列。有兩個觀察值得先記住。第一，真正「有狀態」的元件很少：event log、佇列、memory store、稽核日誌。其他元件都設計成可以隨時砍掉重啟，這是 production 系統能夠頻繁部署、自動擴縮的前提。第二，失效模式一欄裡反覆出現「重複」與「跨租戶」兩個詞。agent 平台的特殊之處在於，重複執行的不只是請求，還有退款、寄信這類副作用；跨租戶洩漏的不只是資料，還有 token 配額、快取與檢索結果。

## 36.3 Agent service：stateless harness、session store 與 event log

週六凌晨那四百多個消失的對話，根本原因是 harness 把狀態放在記憶體裡。第 4 章的 `loom` v0.1 把 messages 存在 `run()` 的區域變數，這在單機測試沒有問題；但在 production，pod 會因為部署、自動縮容、節點維護、記憶體不足而隨時消失。**stateless harness**（無狀態的 harness）的意思是：harness process 本身不擁有任何 session 的狀態，所有狀態都在外部的 event log，任何一個 worker 都可以在任何時候「喚醒」任何一個 session 接著做。

```text
 使用者        API gateway      agent service（pod-3）      session store / event log     model gateway
   │── 追問 ──────►│                    │                              │                         │
   │               │── wake(s-77) ─────►│                              │                         │
   │               │                    │── 取得 lease、讀 release ───►│                         │
   │               │                    │◄── rel-b1fe、events[0..12] ──│                         │
   │               │                    │ 重建 context（第 10 章：      │                         │
   │               │                    │ context 是 log 的可重建視圖） │                         │
   │               │                    │── append user（seq=13）─────►│                         │
   │               │                    │── complete(context) ─────────────────────────────────►│
   │               │                    │◄──────────────────────────────────── tool_use ────────│
   │               │                    │── append model（seq=14）────►│                         │
   │               │                    ×  pod-3 在這裡被部署砍掉       │                         │
   │               │── 重試 wake(s-77) ─► pod-5                         │                         │
   │               │                    │── 讀 events[0..14] ─────────►│ 從 seq=14 接著做：        │
   │               │                    │   執行 tool、append seq=15    │ 不重打模型，tool 用       │
   │◄── 串流回覆 ──│◄───────────────────│                              │ idempotency key 去重     │
```

這張時序圖有三個關鍵動作。第一是 **wake**：每一輪開始，harness 用 session id 讀出 session 綁定的 release 與完整事件，重建這一輪要送給模型的 context。這和第 10 章「context 是 session log 的可重建視圖」是同一件事：log 是真相，context 只是從 log 算出來的投影，所以 compaction 策略改了、harness 換了一個 pod，都不影響 log 本身。第二是**每一步先寫 log 再繼續**：模型回應、tool 結果都要確認寫入成功，才進行下一步；pod-3 在 seq=14 之後被砍，pod-5 讀到的歷史停在「模型要求呼叫 tool」，於是從執行 tool 開始，不需要重新呼叫模型。第三是 tool 的 idempotency：如果 pod-3 其實已經呼叫了退款 API、只是還沒寫下結果就被砍，pod-5 重新執行時，tool gateway 會用同一把 key 把第二次呼叫擋下來。這三件事合起來，就是第 22 章 durable execution 在同步互動場景的應用。

stateless 還有一個常被忽略的難題：**同一個 session 在同一時間只能有一個 writer**。如果 pod-3 不是被砍掉，而是卡在一次很長的垃圾回收，lease（租約，「這個 session 暫時歸我處理」的有時效鎖）過期後排程器把 session 交給 pod-5；pod-3 醒來後若繼續寫，同一個 session 就會分岔成兩條歷史。第 22 章用 lease 與 heartbeat 處理 worker 的存活，這裡再補上一道保險：寫入 event log 時帶上「我看到的最後序號」，序號不符就拒絕，這叫**樂觀並行控制**（optimistic concurrency control），效果等同分散式鎖文獻裡的 fencing token（隔離令牌，讓過期的持有者無法再生效）。

```python
from __future__ import annotations

from dataclasses import dataclass, field


class ConflictError(Exception):
    """寫入時的 expected_seq 和 log 目前長度不符：代表有別的 worker 已經接手這個 session。"""


@dataclass
class EventLog:
    """append-only 的 session 事件日誌；用「預期序號」做樂觀並行控制。"""
    events: dict[str, list[dict]] = field(default_factory=dict)

    def append(self, session_id: str, expected_seq: int, event: dict) -> int:
        log = self.events.setdefault(session_id, [])
        if len(log) != expected_seq:
            raise ConflictError(f"{session_id}: 預期序號 {expected_seq}，實際已有 {len(log)} 筆")
        log.append(event)
        return len(log)

    def read(self, session_id: str) -> list[dict]:
        return list(self.events.get(session_id, []))


class StatelessHarness:
    """不把 session 狀態放在記憶體：每次 wake 都從 log 重建，寫入時帶著自己看到的序號。"""

    def __init__(self, name: str, log: EventLog):
        self.name, self.log = name, log

    def wake(self, session_id: str) -> int:
        history = self.log.read(session_id)            # context 是 log 的可重建視圖
        return len(history)

    def step(self, session_id: str, seq: int, kind: str, data: str) -> int:
        return self.log.append(session_id, seq, {"by": self.name, "kind": kind, "data": data})


log = EventLog()
log.append("s-77", 0, {"by": "api", "kind": "user", "data": "B-1042 幫我退款"})

w1 = StatelessHarness("worker-1", log)
seq1 = w1.wake("s-77")
seq1 = w1.step("s-77", seq1, "tool_call", "get_order(B-1042)")
# worker-1 卡在 GC 停頓，lease 過期；排程器把 session 交給 worker-2
w2 = StatelessHarness("worker-2", log)
seq2 = w2.wake("s-77")                               # 從 log 重建，看到 2 筆
seq2 = w2.step("s-77", seq2, "tool_result", "shipped")
# worker-1 醒來，想用舊序號繼續寫：必須被拒絕，否則同一個 session 會分岔成兩條歷史
try:
    w1.step("s-77", seq1, "tool_result", "shipped（重複）")
except ConflictError as exc:
    print("拒絕過期 worker：", exc)

for i, e in enumerate(log.read("s-77")):
    print(f"#{i} {e['by']:<9} {e['kind']:<12} {e['data']}")
assert [e["by"] for e in log.read("s-77")] == ["api", "worker-1", "worker-2"]
```

```text
拒絕過期 worker： s-77: 預期序號 2，實際已有 3 筆
#0 api       user         B-1042 幫我退款
#1 worker-1  tool_call    get_order(B-1042)
#2 worker-2  tool_result  shipped
```

輸出的第一行是 worker-1 的下場：它以為下一筆的序號是 2，但 worker-2 已經寫了第 2 筆，log 長度是 3，所以寫入被拒絕。下面三行是最後的 log：使用者訊息、worker-1 在 lease 有效時寫的 tool call、worker-2 接手後寫的 tool result，沒有重複、沒有分岔。這個機制的成本很低，只要儲存層支援「條件寫入」（例如關聯式資料庫的交易加唯一索引，或 key-value store 的 compare-and-set）。被拒絕的 worker 應該直接放棄這個 session，而不是重讀之後再寫，因為它手上的決定是根據舊歷史做的。

session store 和 event log 常被放在一起講，但它們的存取模式不同。**session store** 存的是每個 session 的中繼資料：租戶、使用者、綁定的 release id、目前狀態（進行中、等待核准、已結束）、lease 持有者。它是小筆、頻繁更新、需要索引查詢的資料（「列出這個租戶所有等待核准的 session」）。**event log** 則是大量、只追加、依 session id 循序讀取的資料。很多團隊一開始把兩者都放在同一個關聯式資料庫，這在初期沒問題；規模上來之後，event log 的寫入量通常是第一個瓶頸，常見的做法是依 session id 分片、把已結束 session 的事件歸檔到物件儲存，並用 claim check（提領單）模式把大型 tool 結果存到物件儲存，log 只記指標與摘要。

event log 的寫入延遲直接加在每一步上。一個 12 步的客服任務，每一步寫兩筆事件（模型回應與 tool 結果），如果每次寫入要 20 毫秒，就多了將近半秒；如果為了跨區域複製而要求同步寫兩個區域，延遲可能翻倍。這是 36.12 節災難復原要面對的取捨：同步複製讓 RPO（最多會丟多少資料）接近零，但每一步都變慢；非同步複製比較快，但區域故障時會丟掉最後幾秒的事件。

## 36.4 非同步路徑：job queue、worker 與 sandbox pool

同步互動的 agent 有使用者在等，回覆要在幾秒內開始串流；營運分析、coding 任務卻常常跑幾十分鐘，HTTP 連線不可能一直開著，而且流量很「尖」，月初報表或大客戶一次送出三百個分析，都會瞬間湧入。**job queue**（工作佇列）把「接受請求」和「執行請求」拆開：API gateway 只負責把任務寫進佇列並回傳任務 id，worker 依自己的節奏撿工作來做，使用者透過串流事件、通知或輪詢得到結果。

```text
                 ┌──────────────── 重試（未超過次數，退避後重新可見）─────────────┐
                 ▼                                                                 │
 enqueue ──► queued ──（worker 撿起，取得 lease）──► running ──（成功）──► succeeded
               │  ▲                                    │  │
               │  └──（lease 過期：worker 死了）────────┘  ├──（需要人核准）──► waiting_approval
               │                                          │                       │（核准後重新 enqueue）
               │                                          └──（失敗）────────────┘
               │                                                │ 超過重試次數，或不可重試的錯誤
               └──（取消）──► cancelled                          ▼
                                                           dead_letter（人工檢查）
```

這張狀態機描述一個非同步任務的生命週期。任務進入 `queued` 後，worker 撿起它並取得 lease，狀態變成 `running`。成功就結束；失敗時分兩種：可重試的（下游暫時故障、模型 429）在退避之後重新變成可見，不可重試的或超過重試次數的進入 **dead letter queue**（死信佇列，存放無法處理的任務，等人檢查）。`running` 狀態如果 lease 過期，代表 worker 已經死了，任務回到佇列由別人接手，這就是上一節 wake 機制的非同步版本。`waiting_approval` 是 agent 特有的狀態：任務停下來等人核准時，不應該佔著 worker 空等，而是釋放 worker、把狀態存在 session store，核准事件到達後再重新 enqueue。

佇列有三個在 agent 場景特別容易出事的設計點。第一是**投遞語意**：主流佇列大多提供 at-least-once（至少投遞一次），也就是同一個任務可能被兩個 worker 各做一次，所以任務本身必須能安全地重複執行，這又回到 event log 的序號檢查與 tool 的 idempotency。第二是**公平性**：如果所有租戶共用一條 FIFO 佇列，萬家購物一次送進三百個任務，後面所有小租戶都要排在它們後面；常見的解法是依租戶分成多條邏輯佇列，worker 用加權輪詢從各租戶佇列撿工作，或者限制每個租戶同時在跑的任務數。第三是**擴展訊號**：agent worker 大部分時間在等模型回應，CPU 使用率很低，用 CPU 做自動擴縮會嚴重失準，應該改用佇列深度、最舊任務的等待時間、或每個 worker 的並行 session 數。

**sandbox pool** 是 coding agent 與資料分析 agent 的執行環境來源。第 17 章談過隔離層級與 pool 的生命週期，放到平台上要多考慮兩件事。第一是**何時配置**：如果每個 session 一開始就配一個 sandbox，大部分只需要查資料、不需要執行程式的 session 也要等 sandbox 開機，還白白佔用資源；比較好的做法是等模型第一次要求執行程式時才配置，並且讓 sandbox 失敗時以 tool 錯誤的形式回到 loop，而不是讓整個 session 失敗。第二是**池的大小與預熱**：預熱的 sandbox 越多，冷啟動越少，但閒置成本越高；池的大小應該依「每秒新增的 sandbox 需求 × 開機時間」來估算，再依時段調整。每個 sandbox 都必須綁定單一租戶與單一 session，用完即丟，絕不能為了省開機時間而在租戶之間重用。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 在〈Scaling Managed Agents〉（2026-04-08）中公開描述了 Claude Managed Agents 的設計：把 agent 拆成 brain（模型＋harness）、hands（sandbox 與工具，統一成 `execute(name, input) → string` 介面）與 session（harness 之外的 append-only 持久 log）。harness 是無狀態的，可以用 session id 喚醒並恢復；容器死掉時以 tool 錯誤呈現，再重新配置。文中提到改成「需要 tool 時才配置容器」之後，p50 TTFT 降低約 60%，p95 降低超過 90%。Amazon Bedrock AgentCore 的公開文件則說明，其託管 agent loop（Harness）讓每個 session 在隔離的 microVM 中執行，Runtime 也提供 session 隔離。具體限制與計價請以官方文件為準。

## 36.5 Model gateway：routing、rate limit、cache 與 fallback

beta 第一週的兩個事故（TPM 被吃光、供應商區域故障）都發生在「呼叫模型」這一步，原因是每個服務都直接拿金鑰呼叫供應商 API。**model gateway**（模型閘道）是平台內所有模型呼叫的唯一出口：agent service 與 worker 不知道金鑰、不知道要打哪個區域，只說「這個租戶、這個 release，要用這個模型角色完成這次呼叫」，其餘交給 gateway。第 25 章在 framework 層實作了 adapter 與 router；這一節談的是把它們變成一個共享服務之後，多出來的平台責任。

```text
 agent service：complete(tenant=shop-a, release=rel-b1fe, role=primary, messages)
   │
   ▼
 (1) 身分與配額 ── 租戶 token bucket、月配額、並行上限 ──── 不足 ──► 429 + retry-after／quota_exceeded
   │
   ▼
 (2) 快取 ────── 應用層 response cache（key 含租戶、release、權限）── 命中 ──► 直接回傳
   │            （provider 端的 prompt caching 在 (5) 由前綴穩定性決定）
   ▼
 (3) routing ─── 依 release 的模型清單：主要模型 → 備援 1 → 備援 2
   │            過濾：租戶的資料駐留區域、該 release 是否在此模型上通過 eval
   ▼
 (4) 熔斷器 ──── 每個「供應商 × 區域 × 模型」一個 breaker；open 就跳過
   │
   ▼
 (5) adapter ─── 轉成供應商格式、帶 snapshot 版本、設逾時；同一端點不在這層重試
   │
   ▼
 (6) 計量 ────── 結算 input／output／cache／reasoning tokens，寫入 trace 與帳務，歸屬到租戶
```

依序看這六關。第 (1) 關是 36.9 節的主題：在花錢之前先確認這個租戶還有額度，並區分「暫時太快」（回 429 與等待時間，客戶端可以稍後再試）與「本月用完」（不該重試）。第 (2) 關是應用層快取，例如完全相同的分類請求或 embedding；它和供應商端的 **prompt caching**（第 9 章）是兩回事，後者靠的是 harness 維持穩定前綴，gateway 能做的是不要破壞它，例如不要在前綴插入每次都不同的 request id。應用層快取的 key 一定要包含租戶與權限範圍，否則 A 店的客服回答可能被 B 店的使用者命中。

第 (3) 關的 routing 有兩個平台層級的約束，比第 25 章談的「依難度選模型」更優先。一是**資料駐留**：歐盟的租戶如果合約規定資料不出區域，fallback 鏈裡就只能有該區域的端點，寧可失敗也不能悄悄送到別的區域。二是 **eval 覆蓋**：一個 release 的 prompt 與 tool 描述是針對特定模型調好的，換一個模型，tool 呼叫格式的遵守程度、拒答傾向、成本都可能不同；只有在 release 上線前已經用 eval 驗證過的模型，才能出現在它的 fallback 清單裡。第 (4) 關的熔斷器讓 gateway 在供應商故障時「快速失敗」：已知壞掉的端點直接跳過，不必每個請求都先等一次逾時。

第 (5) 關有一條很重要的規則：**整條呼叫鏈只能有一層做重試**。如果 agent service 重試 3 次、gateway 重試 3 次、SDK 又重試 3 次，供應商過載時每個原始請求會變成 27 次呼叫，把一場小故障放大成大故障，這叫 **retry amplification**（重試放大）。本書依第 24 章的分工，把重試放在 harness 的 `loom.runtime`：它知道整個 run 還剩多少時間、使用者還在不在、有沒有已經串流出去的半段文字，所以由它用指數退避加 jitter（隨機抖動）並遵守 retry-after 決定要不要再試；SDK 的內建重試關掉，gateway 不對同一個端點重試，只做限流、熔斷與「換到下一個端點」的 fallback，並把錯誤分類（可不可重試、建議等多久）原樣回傳給 runtime。串流也有限制：一旦已經把部分文字串流給使用者，就不能無聲地切換到另一個模型重來，因為兩個模型的回答不會接得上，必須明確告訴前端「重新產生」。

```text
                  連續失敗達門檻（例如 3 次）
     ┌────────┐ ─────────────────────────────► ┌────────┐
     │ closed │                                │  open  │ ◄──┐
     │ 正常送 │ ◄─────────┐                    │ 直接跳過│    │
     └────────┘           │                    └───┬────┘    │
          ▲               │ 探測成功              │ cooldown 到期（例如 30 秒）
          │               │                        ▼          │
          │          ┌────┴──────┐                            │
          └──────────│ half_open │ ─── 探測失敗 ───────────────┘
                     │ 只放一個  │
                     │ 探測請求  │
                     └───────────┘
```

這是 **circuit breaker**（熔斷器）的三態狀態機。`closed` 是正常狀態，請求照常送出並計算失敗次數；連續失敗達到門檻就跳到 `open`，這段期間所有請求直接跳過這個端點，改走 fallback。`open` 維持一段 cooldown 之後進入 `half_open`，只放一個探測請求過去：成功就回到 `closed`，失敗就重新 `open` 並重新計時。熔斷器的門檻要依錯誤類型區分：429 代表「你太快了」，應該先降速而不是換供應商（換過去可能一樣被限流，還把問題帶到備援端）；5xx 與逾時才代表端點不健康。36.13 節的動手做會把這張狀態機和 fallback 鏈、資料駐留約束一起寫成程式。

> [!warning] 常見誤解
> 「fallback 越多層越可靠。」每一層 fallback 都是一個沒有經常跑到的程式路徑，品質未經驗證的 fallback 會把「服務中斷」換成「服務靜默地變差」，而後者更難發現。比較穩健的做法是 fallback 鏈短而明確，每一層都在 release 的 eval 中跑過，並在 trace 上標記「這個回答來自備援模型」，讓線上指標可以分開看。最後一層甚至可以不是模型，而是降級的確定性流程，例如客服只回覆訂單狀態並轉真人。

## 36.6 Tool gateway 與 memory／retrieval store

Maya 在檢討會上說的「兩百個租戶的退款權限我沒辦法審」，指的是一個結構問題：如果每個 agent 服務自己拿業務 API 的金鑰、自己判斷能不能退款、自己寫 log，權限邏輯就分散在好幾個程式庫裡，任何一個 prompt 改壞或程式漏判，都可能讓 agent 做出越權的動作。**tool gateway**（工具閘道）把所有 tool 呼叫收斂到一個確定性的關卡：模型可以「提議」呼叫什麼，但能不能做、用誰的身分做、做了之後留下什麼紀錄，全部在 gateway 裡由程式決定。

```text
 harness 送出：tool_call(refund, {order_id: B-1042, amount: 380})
              ＋ context：tenant=shop-a, user=u-19, session=s-77, release=rel-b1fe
   │
   ▼
 授權 ───── 這個 release 宣告過 refund 嗎？租戶開通了嗎？使用者有權代表這張訂單嗎？（第 33 章）
   │
   ▼
 policy ─── 依副作用分級與參數判斷：amount ≤ 500 自動（L4）；否則轉核准（第 21 章）
   │        policy 服務不可用時 fail-closed：寫入類 tool 一律拒絕
   ▼
 憑證注入 ─ 從 vault 取這個租戶的短效憑證，放在請求 header；模型與 sandbox 都看不到（第 17、33 章）
   │
   ▼
 去重 ───── idempotency key 由 harness 依 intent_fields 推導；已執行過就回傳上次結果（第 5、22 章）
   │
   ▼
 執行 ───── 呼叫業務 API 或 MCP server；結果截斷、遮蔽 PII 後回傳
   │
   ▼
 稽核 ───── append-only、hash chain：誰、代表誰、哪個 release、什麼參數、policy 判定、結果
```

這條流水線把前面好幾章的機制串在一起。授權回答「誰能做」，使用第 33 章的 delegation 模型：agent 代表使用者行動，權限是租戶開通的能力、使用者本身的權限與 release 宣告的 tool 清單三者的交集。policy 回答「在什麼條件下能做」，例如第 21 章的 approval policy；這一層最重要的設計決定是 **fail-closed**（故障時關閉）：policy 服務掛掉時，唯讀 tool 可以繼續，寫入與 destructive tool 一律拒絕，因為「暫時不能退款」比「誰都能退款」好太多。憑證注入讓業務 API 的金鑰永遠不進入模型的 context 或 sandbox。去重依照全書的定義，key 由 harness 依業務意圖推導，去重發生在真正執行副作用的那一端。

稽核紀錄和第 29 章的 debug trace 要分開治理。trace 是給工程師除錯的，可以抽樣、保存幾週、有 PII 遮蔽；稽核紀錄是給資安、法務與客戶查證的，必須完整、不可竄改、保存期限依法規與合約。常見的防竄改做法是 **hash chain**：每一筆紀錄都包含前一筆的雜湊值，任何一筆被改，後面的鏈就對不上；更嚴格的場景會寫入 WORM（write once read many，寫入後不可修改）儲存。兩者用 trace id 關聯，讓事故調查時可以從一筆稽核紀錄找回完整的 trajectory。

**memory／retrieval store** 是另一個跨租戶風險集中的地方。第 11 章的檢索與第 12 章的記憶系統，在平台上都必須以租戶為第一層分區：最安全的做法是每個租戶獨立的索引或 namespace，查詢時由 gateway 而不是模型填入租戶條件；如果為了成本共用索引，過濾條件必須在檢索引擎內部執行，而不是先取回 top-k 再過濾（那樣不只會漏結果，還可能在 log 或 rerank 階段接觸到別人的資料）。另一個常被忽略的是**索引版本**：知識庫重新 chunking 或換 embedding 模型後，索引內容就變了，它應該像 prompt 一樣被視為 release 的一部分（36.10 節），否則「同一個 release」在兩天內可能檢索到完全不同的內容。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 AWS 公開文件，Amazon Bedrock AgentCore 把 tool gateway 做成獨立服務：Gateway 可以把 API、Lambda 與既有服務轉成 MCP tools，Policy 在 Gateway 攔截每一次 tool call，規則可以用自然語言或文件稱為 Dogwood 的 Cedar 相容 policy 語言撰寫；Identity 負責 agent 身分與 OAuth 憑證管理。Google 的 Gemini Enterprise Agent Platform（原 Vertex AI Agent Engine 頁面）在 Agent Runtime 中列出 agent identity 與 Agent Gateway 路由。產品名稱與功能變動快，請以官方文件為準。

## 36.7 Observability pipeline：一份資料，四種用途

第 29 章講過怎麼為單一 agent 設計 trace；平台化之後，問題變成「每天幾百萬個 span，誰要看、看什麼、保存多久」。同一份觀測資料至少有四種用途：工程師除錯（trace）、營運監控與告警（metric）、成本歸屬與帳務（metering）、品質評估（線上 eval）。再加上 36.6 節的稽核，每一種的保存期限、存取權限與遮蔽規則都不同，所以 production 的 observability 是一條有分流的 pipeline，而不是「把所有東西丟進一個 log 系統」。

```text
 agent service ┐
 workers       ├─► OTel 收集器 ─► PII 遮蔽 ─► 屬性補齊 ─┬─► trace store（抽樣；保存數週）── 除錯
 model gateway │   （span、event、  （email、電話、  （tenant、release、 │
 tool gateway  ┘    metric）         地址、卡號）     model snapshot）  ├─► metric（全量聚合）── 儀表板、SLO 告警
                                                                       │
                                                                       ├─► 計量（全量、不抽樣）── 租戶帳單、配額結算
                                                                       │
                                                                       ├─► eval 抽樣佇列 ── LLM judge／code grader
                                                                       │        └─► 依 release 分組的品質分數 ── canary controller
                                                                       │
 tool gateway 稽核事件 ──（另一條路，不經抽樣）──────────────────────────┴─► 稽核儲存（hash chain、WORM、依法規保存）
```

圖中的分流有幾個刻意的設計。PII 遮蔽放在最前面，落地之前就處理，因為一旦原文寫進 trace store，就很難保證所有副本都被刪除。屬性補齊把 tenant id、release id、model snapshot 加到每個 span 上，這是 36.1 節第二個事故缺少的東西：有了 release id，「退款正確率下降」才能被切成「哪個 release、哪個模型、哪個租戶」來看。trace 可以抽樣，但計量絕對不能抽樣：帳單要精確到每一個 token，所以 model gateway 在第 (6) 關結算的用量要走一條全量、可對帳的路。eval 抽樣佇列則是線上品質訊號的來源：依 release 分組抽一部分 session，交給第 27 章的 grader 評分，結果餵給 36.11 節的 canary controller。

抽樣策略本身也要設計。純隨機的 head sampling（在 trace 開始時就決定要不要保留）會讓罕見但重要的事件被丟掉，例如 status=loop 或 guardrail 觸發的 session。常見的組合是：一般 session 低比例隨機抽樣；錯誤、逾時、guardrail 觸發、使用者負評、高成本的 session 全部保留（這需要 tail sampling，等 trace 結束後再決定）；新 release 在 canary 期間提高抽樣比例。

## 36.8 多租戶隔離與 noisy neighbor

週二下午的事故有個名字：**noisy neighbor**（吵鬧的鄰居），意思是共用資源的系統裡，一個租戶的大量使用拖慢或拖垮其他租戶。agent 平台特別容易發生，因為 agent 的資源用量變異極大：同樣是一次「請求」，客服查訂單可能用幾千個 token，research agent 的 fan-out 可能用幾百萬個 token，還會同時佔用幾十個 sandbox 和 worker。用請求數來分配資源，在 agent 平台上幾乎沒有意義。

多租戶隔離可以在不同程度上做，SaaS 架構常用三個名詞描述：**pooled**（所有租戶共用同一組資源，用邏輯欄位區分）、**silo**（每個租戶專屬一組資源）、**bridge**（介於兩者之間，部分共用、部分專屬）。這三種不是整個系統選一種，而是每一類資源各自決定。

| 資源 | pooled（共用） | silo（專屬） | 青鳥的選擇 | 理由 |
|---|---|---|---|---|
| agent service／worker | 共用 pod，依租戶限並行 | 每個大租戶專屬 worker 池 | pooled；企業方案可選專屬 worker 池 | stateless 元件共用最省；專屬池給有 SLA 的大客戶 |
| 模型 TPM | 共用供應商金鑰，per-tenant bucket | 大租戶用自己的供應商帳號或專屬容量 | pooled＋per-tenant bucket；大客戶可自帶金鑰 | 供應商上限是全公司共享的硬限制 |
| sandbox | 永遠不共用 | 每個 session 一個 | silo（每 session） | 程式執行是最高風險的隔離邊界 |
| event log／session store | 共用資料庫，tenant 欄位＋列級權限 | 每個租戶獨立資料庫或 schema | pooled；受監管客戶用獨立 schema | 數千個小租戶各一個資料庫不切實際 |
| 檢索索引 | 共用索引，引擎內過濾 | 每個租戶獨立 namespace | 每租戶獨立 namespace | 檢索洩漏的後果嚴重，namespace 成本可接受 |
| 業務 API 憑證 | 不適用 | 每個租戶各自的短效憑證 | silo | 憑證必須代表租戶本身，第 33 章 |
| 快取 | key 必含租戶與權限 | 每租戶獨立快取 | pooled，key 含租戶 | 錯誤命中就是資料外洩 |

這張表的模式是：**運算可以共用，資料與身分要分開，執行程式碼的環境永遠不共用**。stateless 的 agent service 和 worker 共用最划算，只要用並行上限與公平排程防止某個租戶佔滿；資料層依風險與客戶等級選擇共用或分開；sandbox 與憑證則沒有共用的選項。企業方案的「專屬資源」通常也是賣點：大客戶願意多付錢換取不受別人影響的容量與更強的隔離，這是第 37 章談單位經濟時會用到的產品槓桿。

noisy neighbor 不只發生在模型 TPM。實務上要逐一檢查每個共享資源：job queue（大租戶塞滿佇列，小租戶的任務排很久）、sandbox pool（大租戶把預熱池用光，別人都要冷啟動）、event log 的資料庫（大租戶的長任務造成熱分片）、tool gateway 背後的業務 API（agent 的平行呼叫打爆青鳥自己的訂單服務），甚至 observability pipeline（大租戶的大量 span 讓收集器丟資料）。每一個都需要一個「每租戶上限」，而且上限要能依方案等級設定。

隔離做得好，還要能**看得見**：每個租戶的 token 用量、被限流次數、佇列等待時間與 sandbox 冷啟動比例都應該是一級指標，而這需要 36.7 節的每個 span 都帶 tenant id；少了它，noisy neighbor 只會表現成「系統整體變慢」。

## 36.9 Rate limit 與配額：per-tenant token bucket

隔離的核心工具是限流。agent 平台的限流有一個和一般 API 不同的特性：**要限的是 token，不是請求數**。供應商給你的上限通常同時有每分鐘請求數（RPM）、每分鐘 token 數（TPM，有時 input 與 output 分開）與並行數；而 agent 的一次請求可能是幾百或幾十萬個 token。所以平台內部的限流，也要用 token 當單位。

最常用的演算法是 **token bucket**（令牌桶）。想像每個租戶有一個桶子，容量是 C 個令牌，每秒補充 r 個，補到滿為止；每次呼叫模型要從桶子裡拿出「這次預估要用的 token 數」那麼多令牌，不夠就被拒絕或排隊。容量 C 決定允許多大的瞬間爆量（例如使用者一次貼上一份長文件），補充速率 r 決定長期平均速率。和固定時間窗計數相比，token bucket 不會在時間窗交界處允許兩倍的流量，也比較符合「偶爾爆量、長期平均受限」的實際需求。

```text
 每一次 model 呼叫要通過的三層（由外到內，任何一層不過就停）

  ┌─ 月配額（合約）──────────────── 本月已用＋預留＋本次估計 ≤ 配額？ ── 否 ─► quota_exceeded（不重試）
  │
  ├─ 租戶 token bucket ─────────── 桶內令牌 ≥ 本次估計？            ── 否 ─► rate_limited（retry-after）
  │    （容量＝爆量上限，補充速率＝方案的 TPM）
  │
  ├─ 全域 token bucket ─────────── 供應商給全公司的 TPM 還有嗎？     ── 否 ─► 把租戶桶的令牌還回去
  │    （每個供應商 × 區域 × 模型一個）                                       rate_limited
  │
  └─ 通過：預留「估計值」 ──► 呼叫模型 ──► 結算「實際值」，多扣的令牌退回桶子與配額
```

這張圖有三個設計細節。第一是**層次**：全域 bucket 代表供應商給的硬上限，租戶 bucket 代表方案分配的份額，月配額代表合約。三層的檢查順序是由「最便宜、最不該重試」到「最貴」：配額用完的請求不需要碰任何 bucket；租戶 bucket 過了但全域 bucket 沒過時，要把租戶 bucket 扣掉的令牌還回去，否則這個租戶會被重複扣款。第二是**預留與結算**：呼叫模型之前不知道實際會用多少 token，所以先用「input 估計＋output 上限」預留，回應之後用 usage 結算，多扣的退回。不做結算，每個租戶實際可用的額度都會被系統性地低估。第三是**兩種拒絕的語意不同**：rate_limited 代表「稍後再試」，要附上 retry-after，非同步任務應該留在佇列等待而不是失敗；quota_exceeded 代表「這個週期用完了」，重試沒有用，應該通知租戶管理者升級方案或等下個週期。

| 機制 | 限制什麼 | 時間尺度 | 被觸發時的行為 | 典型設定依據 |
|---|---|---|---|---|
| 請求級 rate limit（API gateway） | 每秒請求數 | 秒 | 429，客戶端退避 | 防濫用、防腳本 |
| 租戶 token bucket（model gateway） | 每分鐘 token 數 | 秒到分鐘 | 429＋retry-after；非同步任務延後 | 方案等級的 TPM 份額 |
| 全域 token bucket | 供應商給的 TPM／RPM | 秒到分鐘 | 降速、切到備援容量 | 供應商合約 |
| 並行上限 | 同時進行的 session、sandbox、子 agent 數 | 即時 | 排隊 | worker 與 sandbox 容量 |
| 月配額 | 一個計費週期的總 token 或金額 | 天到月 | 拒絕並通知；可設軟警告 | 合約與定價 |
| 單一任務預算（第 4 章） | 一次 run 的 token 與步數 | 單次任務 | 結束 run，status=budget | 單題可接受成本 |

這張表把限流放回完整的層次裡。第 4 章的 token 預算限制「一次任務」，本節的機制限制「一個租戶在一段時間內」，兩者互補：一個失控的 run 會先撞到自己的預算；很多個正常 run 同時湧入，則由租戶 bucket 攔住。並行上限是 agent 平台特別需要的一欄，因為 fan-out 型的 research agent 可以在一瞬間開出幾十個子 agent，每一個單獨看都很守規矩，加起來卻佔滿 worker 與 sandbox。實作上，bucket 的狀態要放在所有 gateway 實例共享的儲存（例如記憶體資料庫的原子操作），否則十個 gateway 實例各自計數，等於把上限放大十倍。

> [!warning] 常見誤解
> 「429 就讓客戶端重試。」對同步客服這樣做可以，但對 agent 的 fan-out 是災難：幾十個子 agent 同時收到 429、同時退避、又同時重試，形成週期性的尖峰。更好的做法是讓限流發生在佇列入口與 harness 層：子任務在佇列裡等令牌，而不是各自重試；並且讓 orchestrator 知道剩餘額度，主動減少平行度（第 20 章）。

## 36.10 版本管理：prompt、model、tool 與 policy 一起版本化

週四事故的本質是：系統的行為由很多個會變的東西共同決定，但它們沒有被一起記錄。一個 agent 在某一刻的行為，取決於 system prompt、模型（而且是哪一個 snapshot）、每個 tool 的描述與實作、policy 規則、檢索索引、harness 本身的程式碼與設定（例如 compaction 門檻、reasoning effort）。只要其中一項改變，行為就可能改變；只版本化其中幾項，就無法回答「上週的版本是什麼」。

```text
 release rel-b1fe216c（不可變；內容雜湊即版本號）
 ┌──────────────────────────────────────────────────────────────────┐
 │ prompt         customer-service@v12        sha256:3f9a…          │
 │ model          primary:  frontier-2026-06-01（snapshot，不用 alias）│
 │                fallback: frontier-alt-2026-05-15、small-eu-2026-04 │
 │ tools          get_order@5  get_shipment@2  refund@3  create_return@4│
 │ policy         refund-auto-limit=500  approval=refund>500        │
 │ retrieval      kb-index@2026-09-28（embedding 模型、chunking 版本）│
 │ harness        loom@git:9c1e2a7  compaction=0.7  effort=high      │
 │ eval 證據      offline suite cs-v31：pass 91.2%（每個 fallback 模型各一份）│
 └──────────────────────────────────────────────────────────────────┘
        │ 綁定（session 建立時寫入 session store，整個 session 不變）
        ▼
 session s-77 ── release=rel-b1fe216c ── 每個 span 都帶 release id
```

這張圖是一份 **release manifest**（發布清單），概念上類似套件管理的 lockfile：把所有會影響行為的東西鎖定到確切版本，再用整份內容的雜湊當作版本號。有幾個欄位特別值得注意。model 一定要寫帶日期的 snapshot，而不是「最新版」這類 alias；alias 會在供應商更新時悄悄指向新模型，等於有人在你不知情的情況下發布了新版本。fallback 模型也列在 manifest 裡，而且每一個都附上 eval 證據，這正是 36.5 節「只有驗證過的模型才能當 fallback」的落實方式。harness 的設定也要納入：公開的事故分析顯示，像 reasoning effort 預設值、裁掉舊 thinking 的快取最佳化、system prompt 中一行看似無害的字數限制，都可能明顯改變品質。

**session 綁定版本**是另一個關鍵決定。一個對話進行到一半時切換 release，模型會看到前半段是舊 prompt 的風格、後半段是新規則，tool 的 schema 也可能變了，事件歷史裡的舊 tool 呼叫在新版本裡甚至可能不存在。更實際的影響是成本：system prompt 或 tool 定義一改，prompt cache 的前綴就失效，這個 session 接下來每一輪都要付全價。所以平台在 session 建立時就把 release id 寫進 session store，整個 session 用同一個版本，新版本只套用到新 session。長時間的背景任務也一樣，而且更嚴格：第 22 章的事件重播要求 determinism，用新版程式重播舊版產生的事件，就可能走到不同的分支。

版本化還有幾個落地細節。第一，prompt 與 policy 這類「設定」最好和程式碼放在同一個版本控制與審查流程裡，至少要有變更紀錄與審核人；讓營運人員在後台直接改 prompt 而沒有版本，是週四事故的直接成因。第二，release 是不可變的：要改任何東西就產生一個新 release，回滾就是把流量指回舊 release，而不是「把設定改回去」。第三，供應商會下架舊模型，所以要有 **model migration** 流程：在新 snapshot 上跑完整的 offline eval、比較 trajectory 差異、調整 prompt，產生新 release，再走 36.11 節的發布流程。event log 的事件格式也要帶版本欄位，讓新版 harness 讀得懂舊事件。第四，多租戶平台還要在 release 之上疊一層租戶設定：第 42 章會把兩者一起編譯成每個租戶的 **AgentSpec**，同樣以內容 hash 為版本號、每段對話 pin 住；span 上的屬性名稱依第 29 章的 `bluebird.*` 慣例，寫成 `bluebird.tenant.id` 與 `bluebird.spec.version`。

## 36.11 發布策略：canary、A/B 與 shadow

有了不可變的 release，下一個問題是怎麼安全地把新 release 推出去。agent 的改版和一般軟體不同：一般軟體的 regression 多半表現為錯誤或例外，監控很快就會看到；agent 的 regression 常常是「回答看起來正常，但退款判斷錯了」，HTTP 200、延遲正常、沒有任何例外。所以 agent 的發布策略必須以**品質指標**為核心，而品質指標需要評分、需要樣本，也就需要時間。

| 策略 | 怎麼做 | 回答的問題 | 使用者受影響嗎 | 主要成本與限制 |
|---|---|---|---|---|
| offline eval gate | 發布前在固定 eval set 上跑新 release | 新版本在已知案例上有沒有退步？ | 否 | 只覆蓋已知案例；第 27 章 |
| shadow | 新版本處理同一份真實輸入，副作用改為 dry-run，結果不給使用者 | 在真實流量分布下，新版本的決策和舊版差多少？ | 否 | 雙倍模型成本；多步任務在 dry-run 後會和真實狀態分岔 |
| canary | 一小部分 session 用新版本，依指標逐步推進或回滾 | 新版本在真實使用中有沒有讓結果變差？ | 是，小比例 | 小比例需要很長時間才有統計力 |
| A/B test | 兩個版本各分一部分流量，比較業務指標 | 哪個版本比較好（轉換率、解決率、成本）？ | 是 | 需要預先定義主要指標與樣本數；agent 變異大 |
| feature flag／kill switch | 不改 release，即時關閉某個 tool 或能力 | 出事時能不能立刻止血？ | 是（能力被關閉） | 只能關，不能修；要事先埋好開關 |

這五種不是互相替代，而是依序組成一條發布管線。offline eval 是第一道門，擋住已知案例上的退步；shadow 用真實流量檢查「決策有沒有改變」，特別適合 tool 選擇與 policy 改動；canary 用小比例真實 session 檢查「結果有沒有變差」；A/B 則是在確認安全之後回答「是不是更好」。canary 和 A/B 常被混用：canary 的問題是「新版本能不能取代舊版本而不出事」，判斷方向是單邊的（只怕變差）；A/B 的問題是「哪個比較好」，需要預先定義主要指標與足夠的樣本。kill switch 是最後的保險，讓值班工程師不必發布新 release 就能關掉某個出問題的 tool。

shadow 在 agent 上有一個特殊的困難：agent 是多步的，而 shadow 不能產生副作用。第一步的 read tool 可以照常執行，但只要遇到 write 或 destructive tool，shadow 版本就只能拿到模擬結果，之後的步驟和真實世界的狀態就分岔了。因此 shadow 最有價值的比較點是「第一個副作用之前的決策」：新版本想做的第一個寫入動作是什麼、參數是什麼，和舊版本實際做的是否一致。

```python
from __future__ import annotations

from typing import Any, Callable

SIDE_EFFECT = {"refund": "destructive", "create_return": "write", "get_order": "read"}


class ShadowTools:
    """shadow 版本拿到的 tool 層：read 照常執行，write／destructive 一律只記錄意圖、回傳模擬結果。"""

    def __init__(self, real: dict[str, Callable[..., Any]]):
        self.real, self.intents = real, []

    def call(self, name: str, **args: Any) -> Any:
        level = SIDE_EFFECT.get(name, "destructive")          # 未標註的 tool 一律當 destructive
        if level == "read":
            return self.real[name](**args)
        self.intents.append((name, args))
        return {"dry_run": True, "note": f"{name} 未執行（shadow 模式）"}


executed: list[str] = []
real = {"get_order": lambda order_id: {"order_id": order_id, "status": "shipped", "amount": 380},
        "refund": lambda order_id: executed.append(f"refund {order_id}") or "已退款",
        "create_return": lambda order_id: executed.append(f"return {order_id}") or "R-7781"}

# production 版本（v12）真的執行；shadow 版本（v13）重放同一則使用者訊息
prod_actions = [("get_order", {"order_id": "B-1042"}), ("create_return", {"order_id": "B-1042"})]
for name, args in prod_actions:
    real[name](**args)
shadow = ShadowTools(real)
shadow.call("get_order", order_id="B-1042")
shadow.call("refund", order_id="B-1042")                     # v13 想對已出貨訂單直接退款

prod_writes = [a for a in prod_actions if SIDE_EFFECT[a[0]] != "read"]
print("production 實際副作用：", executed)
print("shadow 想做的副作用：  ", shadow.intents)
print("決策分歧：", prod_writes != shadow.intents)
assert executed == ["return B-1042"] and shadow.intents == [("refund", {"order_id": "B-1042"})]
```

```text
production 實際副作用： ['return B-1042']
shadow 想做的副作用：   [('refund', {'order_id': 'B-1042'})]
決策分歧： True
```

這段程式模擬一則真實訊息「B-1042 幫我退款」。production 版本（v12）查了訂單、發現已出貨，於是建立退貨單，這是唯一真的發生的副作用。shadow 版本（v13）拿到同一則訊息，查訂單是 read，照常執行；但它接著想直接退款，被 `ShadowTools` 攔下只記錄意圖。最後一行顯示兩個版本的寫入決策不同，這正是 shadow 要抓的東西：v13 很可能弄丟了「已出貨要走退貨」這條規則。注意未標註的 tool 一律當 destructive，和全書的副作用分級一致；shadow 模式下這個預設尤其重要，因為漏標一個 tool 就會讓 shadow 流量產生真實的副作用。

```text
            offline eval 通過
 draft ─────────────────────────► shadow ──（決策分歧率低於門檻）──► canary 1%
   ▲                                │                                 │
   │                                │ 分歧率過高                       │ 每個階段：收集 ≥ N 個評分樣本
   │                                ▼                                 ▼
   └────────── 修正後產生新 release ◄── rejected                  ┌─ guardrail 觸發率上升 ──► 立即回滾
                                    ▲                             ├─ 品質差的區間上界 < −容忍度 ──► 回滾
                                    │                             ├─ 成本上升超過門檻 ──► 回滾
                                    └──────── rolled_back ◄───────┤
                                                                  ├─ 品質差的區間下界 > −容忍度 ──► 下一階段
                                                                  │   1% → 5% → 25% → 50% → 全量（promoted）
                                                                  └─ 都不成立 ──► 證據不夠，繼續收集
```

這張狀態機是 36.13 節 canary controller 的設計圖。每個階段的判斷有三種結果：證據顯示變差就回滾，證據顯示沒有變差（在容忍度之內）就推進，證據不夠就繼續收集。品質指標用「成功率差異的信賴區間」判斷，而不是直接比較兩個比例，因為小樣本下 88% 和 90% 的差異可能只是隨機波動。guardrail 指標則用硬門檻、而且不等統計顯著：安全相關的訊號寧可誤判回滾，也不要多等一萬個 session。回滾的動作是把新 session 的流量指回舊 release；已經綁定新 release、正在進行中的 session 怎麼辦，要事先決定：多數客服 session 很短，可以讓它們自然結束；長時間任務則可能需要暫停並通知人工檢查。

分流要用 session（或租戶）的雜湊，而不是每個請求隨機決定，理由和 36.10 節的版本綁定相同。依租戶分流還能滿足 B2B 合約常見的「我的店晚一點升級」，代價是租戶之間的差異會混進比較，樣本要更大或改用分層比較。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 在 2026-04-23 公開的 Claude Code 事故分析中提到，降低預設 reasoning effort、一個裁掉舊 thinking 的快取最佳化 bug，以及 system prompt 中限制 tool call 之間文字長度的一行指示，都對品質造成可察覺的影響；文中的教訓是可能影響智力的改動都要經過 soak period、廣泛的 per-model eval 與漸進式 rollout。依 AWS 公開文件，AgentCore 的 Optimization 功能提供版本化的 config bundle，並透過 Gateway 做 A/B 流量切分。具體功能與限制請以官方文件為準。

## 36.12 災難復原：RPO、RTO 與降級模式

最後一個事故是主要供應商的區域故障。**災難復原**（disaster recovery，DR）要回答兩個問題：故障時最多會丟掉多少資料（**RPO**，recovery point objective，例如「最多丟最後 5 秒的事件」），以及多久能恢復服務（**RTO**，recovery time objective，例如「15 分鐘內在另一個區域恢復」）。這兩個數字要依元件分別訂，因為每個元件的資料價值與重建成本差很多。

| 元件 | 丟失的後果 | 建議 RPO | 建議 RTO | 做法 |
|---|---|---|---|---|
| event log／session store | 進行中的對話與任務消失；可能重複副作用 | 秒級（接近零） | 分鐘級 | 跨區複製；寫入確認後才繼續 loop |
| 稽核日誌 | 違反法規與合約；無法調查事故 | 零 | 小時級（可延後查詢） | 同步寫入兩處或 WORM 儲存 |
| idempotency 去重表 | 故障切換後重複退款 | 零（或與副作用同交易） | 分鐘級 | 和業務資料同一個交易，或放在副作用端 |
| memory／retrieval 索引 | 回答品質下降，但可重建 | 小時到天 | 小時級 | 定期快照；保留原始文件可重建索引 |
| release registry | 無法啟動任何 agent | 零（變更少） | 分鐘級 | 多區複本；本地快取最後已知的 release |
| job queue | 任務遺失或重複 | 秒級 | 分鐘級 | 持久化佇列；任務可重播 |
| trace／metric | 除錯與監控出現空窗 | 可容忍丟失 | 不影響服務 | 盡力而為 |
| sandbox | 正在執行的程式中斷 | 不需要 | 秒級（重新配置） | 用完即丟；以 tool 錯誤回到 loop |
| 模型供應商 | 無法推理 | 不適用 | 秒級（切換） | 多區域端點、備援供應商、降級模式 |

這張表最重要的一點是：**不是每個元件都需要一樣強的 DR**。event log、稽核與去重表是「丟了就會造成錯誤或違規」的資料，值得付出同步複製的延遲與成本；trace 與索引則可以接受丟失或重建。sandbox 刻意設計成可丟棄，所以它的 DR 就是重新配置。模型供應商是 agent 平台特有的依賴：它不是你的資料，卻是你的關鍵路徑，所以它的 DR 方案是 36.5 節的多端點 fallback，加上下面的降級模式。

```text
 t=0    主要區域的模型端點 5xx 飆升
 t+10s  model gateway 熔斷器 open → 同供應商另一區域（若租戶資料駐留允許）
 t+30s  備援區域也被大量流量擠到限流 → 依 release 的 fallback 清單切到備援供應商
 t+1m   值班告警：品質指標改看「備援模型」那一組；成本儀表板標記異常
 t+2m   降級模式：L4 自動退款暫停 → 回到 L3（全部轉人工確認）；research agent 新任務暫停入列
 t+40m  主要區域恢復 → breaker half_open 探測成功 → 逐步導回流量（不一次全切）
 事後   postmortem：fallback 期間的品質、成本、被拒絕的租戶；更新 DR runbook
```

這條時間線展示了降級的層次。前兩步是自動的：熔斷器偵測故障，gateway 先切到同供應商的另一個區域（行為最接近原本的模型），再切到備援供應商。第三步提醒值班人員：此時線上品質指標要分開看，因為回答來自不同的模型。第四步是 agent 平台特有的降級：**在備援模型上主動降低 autonomy 等級**。備援模型雖然通過了 eval，但它的錯誤模式和主要模型不同，所以把 L4 的自動退款暫時改回 L3（每筆都要人確認），把高成本、可延後的 research 任務暫停入列，讓有限的備援容量留給同步客服。恢復時也要逐步導回，避免所有流量同時湧回剛恢復的端點，又把它打掛。

DR 方案沒有演練過就等於沒有。常見做法是定期在離峰時段手動打開某個端點的熔斷器，或在 staging 模擬整個區域不可用，量測實際的 RTO。演練最常發現的往往不是切換本身，而是周邊假設：備援金鑰過期、備援區域的 TPM 配額不足、降級模式的 feature flag 在某次重構中被刪掉。

## 36.13 動手做：限流、fallback 與 canary 的模擬

這一節用三段程式模擬平台最關鍵的三個機制。三段都只用標準函式庫、用模擬時鐘與固定 seed，可以離線、可重現地執行。它們是本章架構圖中 model gateway 與發布管線的核心邏輯，可以看成 `loom.models`（gateway 層的限流與 fallback）與 `loom.evals`（用線上評分驅動發布）往平台層延伸的部分：真實系統要把計數放在共享儲存、把狀態寫進資料庫，但判斷邏輯就是這些。

### 第一段：per-tenant token bucket 與月配額

這段程式重現週二的 noisy neighbor 事故。全域 bucket 代表供應商給全公司的上限（每秒 2,000 tokens，換算成 TPM 是 12 萬），三個租戶：萬家購物（`megamart`）每秒 fan-out 8 個子任務，而且總是先到；`shop-a` 與 `shop-b` 每秒各一個客服請求。我們跑兩次模擬：第一次只有全域上限，第二次加上 per-tenant bucket 與月配額，並且使用 36.9 節的「預留估計值、結算實際值」。

```python
from __future__ import annotations

from dataclasses import dataclass, field


class Clock:
    """模擬時鐘：讓 refill 可重現，不需要真的 sleep。"""
    def __init__(self) -> None:
        self.now = 0.0


@dataclass
class TokenBucket:
    capacity: float                 # 允許的瞬間爆量（桶子大小）
    rate: float                     # 每秒補充多少 token（長期平均速率）
    clock: Clock
    level: float = -1.0
    last: float = 0.0

    def __post_init__(self) -> None:
        self.level = self.capacity if self.level < 0 else self.level
        self.last = self.clock.now

    def _refill(self) -> None:
        elapsed = self.clock.now - self.last
        self.level = min(self.capacity, self.level + elapsed * self.rate)
        self.last = self.clock.now

    def try_take(self, n: float) -> bool:
        self._refill()
        if self.level >= n:
            self.level -= n
            return True
        return False

    def give_back(self, n: float) -> None:
        self.level = min(self.capacity, self.level + n)

    def retry_after(self, n: float) -> float:
        self._refill()
        return max(0.0, (n - self.level) / self.rate)


@dataclass
class Tenant:
    name: str
    bucket: TokenBucket | None      # None：沒有 per-tenant 限制（只靠全域）
    monthly_quota: int              # 合約內的月配額（tokens）
    used: int = 0
    reserved: int = 0
    stats: dict[str, int] = field(default_factory=lambda: {"ok": 0, "rate_limited": 0, "quota": 0})


class Limiter:
    """兩層 token bucket（全域 provider 上限 → 租戶）＋月配額；先預留估計值，回應後結算實際用量。"""

    def __init__(self, global_bucket: TokenBucket):
        self.global_bucket = global_bucket

    def admit(self, t: Tenant, estimate: int) -> tuple[str, float]:
        if t.used + t.reserved + estimate > t.monthly_quota:
            t.stats["quota"] += 1
            return "quota_exceeded", 0.0               # 不該重試：要升級方案或等下個週期
        if t.bucket and not t.bucket.try_take(estimate):
            t.stats["rate_limited"] += 1
            return "rate_limited", t.bucket.retry_after(estimate)
        if not self.global_bucket.try_take(estimate):
            if t.bucket:
                t.bucket.give_back(estimate)           # 全域沒過，要把租戶桶的 token 還回去
            t.stats["rate_limited"] += 1
            return "rate_limited", self.global_bucket.retry_after(estimate)
        t.reserved += estimate
        return "ok", 0.0

    def settle(self, t: Tenant, estimate: int, actual: int) -> None:
        t.reserved -= estimate
        t.used += actual
        refund = max(0, estimate - actual)             # 估計多扣的部分退回桶子
        self.global_bucket.give_back(refund)
        if t.bucket:
            t.bucket.give_back(refund)
        t.stats["ok"] += 1


def simulate(per_tenant: bool, seconds: int = 60) -> dict[str, Tenant]:
    clock = Clock()
    limiter = Limiter(TokenBucket(capacity=4_000, rate=2_000, clock=clock))   # provider 給的 TPM 換算成每秒
    def bucket(rate: float) -> TokenBucket | None:
        return TokenBucket(capacity=rate * 2, rate=rate, clock=clock) if per_tenant else None
    tenants = {
        "megamart": Tenant("megamart", bucket(1_000), monthly_quota=10_000_000),
        "shop-a": Tenant("shop-a", bucket(500), monthly_quota=10_000_000),
        "shop-b": Tenant("shop-b", bucket(500), monthly_quota=12_000),
    }
    # 每秒的請求：megamart 的 research agent 一次 fan-out 8 個子任務，而且總是先到
    demand = [("megamart", 900, 850)] * 8 + [("shop-a", 400, 300), ("shop-b", 500, 400)]
    for sec in range(seconds):
        clock.now = float(sec)
        for name, estimate, actual in demand:
            t = tenants[name]
            verdict, _ = limiter.admit(t, estimate)
            if verdict == "ok":
                limiter.settle(t, estimate, actual)
    return tenants


for mode in (False, True):
    print("── 只有全域上限" if not mode else "── 全域上限＋per-tenant token bucket＋月配額")
    print("   租戶        成功  被限流  超配額   用量 tokens")
    result = simulate(per_tenant=mode)
    for t in result.values():
        s = t.stats
        print(f"   {t.name:<10}{s['ok']:>6}{s['rate_limited']:>8}{s['quota']:>8}{t.used:>14,}")

only_global, fair = simulate(False), simulate(True)
assert only_global["shop-b"].stats["ok"] == 0               # 排在後面的小租戶被餓死
assert fair["shop-a"].stats["ok"] == 60                     # 每秒一個請求全部成功
assert fair["shop-b"].stats["quota"] > 0 and fair["shop-b"].used <= 12_000
assert fair["megamart"].used < only_global["megamart"].used
```

```text
── 只有全域上限
   租戶        成功  被限流  超配額   用量 tokens
   megamart     122     358       0       103,700
   shop-a        60       0       0        18,000
   shop-b         0      60       0             0
── 全域上限＋per-tenant token bucket＋月配額
   租戶        成功  被限流  超配額   用量 tokens
   megamart      71     409       0        60,350
   shop-a        60       0       0        18,000
   shop-b        29       0      31        11,600
```

先看第一組「只有全域上限」。萬家購物的請求每秒最先到，桶子補充的 2,000 tokens 先被它拿走兩個子任務的份量（兩次預留 1,800，結算後各退 50），剩下的額度只夠 `shop-a` 的一個請求；`shop-b` 排在最後，60 秒內一次都沒有成功。這正是 noisy neighbor 的典型樣貌：誰受害取決於到達順序，而不是誰比較重要。也要注意萬家購物本身被拒絕了 358 次，在真實系統裡這些子 agent 會各自重試，讓情況更糟。

第二組加上 per-tenant bucket 之後，萬家購物的速率被限制在每秒 1,000 tokens，成功次數從 122 降到 71，用量從約 10.4 萬降到約 6 萬 tokens；`shop-a` 照樣每秒成功一次。`shop-b` 這次一開始都能成功，但它的月配額只有 12,000 tokens：成功 29 次、用掉 11,600 之後，第 30 次的「已用＋估計」（11,600＋500）超過配額，從此每次都回傳 `quota_exceeded`，而不是 `rate_limited`。這兩種拒絕在程式裡是不同的回傳值，呼叫端要採取不同的動作：限流時等 retry-after 再試，配額用完時通知租戶管理者。

這段程式有幾個簡化值得指出。第一，真實系統的 bucket 狀態要放在所有 gateway 實例共用的儲存，並用原子操作扣減，否則多個實例各自計數會放大上限。第二，被限流的萬家購物子任務在這裡直接丟棄，真實系統應該讓它們在佇列裡等待令牌，或讓 orchestrator 主動降低平行度。第三，`admit` 裡「全域沒過就把租戶桶的令牌還回去」這一行很容易漏掉，漏掉的後果是租戶在全域壅塞時被重複扣款，比沒有限流還不公平。

### 第二段：model gateway 的 fallback 與熔斷

第二段把 36.5 節的 fallback 鏈、熔斷器與兩個平台約束（資料駐留、eval 覆蓋）寫成程式。三個假的供應商端點都包著全書統一的 `ScriptedModel`：`frontier-us` 是主要模型，在 t=10 到 t=70 秒之間回 503；`frontier-alt` 是同區域的備援；`small-eu` 是歐盟區域的小模型。

```python
from __future__ import annotations

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


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


# ───────── model gateway：fallback 鏈＋per-provider circuit breaker ─────────
class ProviderError(Exception):
    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retryable = status in (429, 500, 503, 529)   # 400 這類請求本身有錯，換誰都一樣


class Clock:
    def __init__(self) -> None:
        self.now = 0.0


class FakeProvider:
    """包住 ScriptedModel 的假供應商；outage(t) 為真時回傳錯誤，模擬區域性故障。"""

    def __init__(self, name: str, region: str, clock: Clock, outage: Callable[[float], int] = lambda t: 0):
        self.name, self.region, self.clock, self.outage = name, region, clock, outage
        self.model = ScriptedModel([say(f"{name} 的回答 #{i}") for i in range(50)])
        self.hits = 0

    def complete(self, messages: list[dict]) -> ModelResponse:
        self.hits += 1
        if status := self.outage(self.clock.now):
            raise ProviderError(status)
        return self.model.complete(messages)


class Breaker:
    """closed →（連續失敗 threshold 次）→ open →（cooldown 後）→ half_open →（探測成功）→ closed"""

    def __init__(self, clock: Clock, threshold: int = 3, cooldown: float = 30.0):
        self.clock, self.threshold, self.cooldown = clock, threshold, cooldown
        self.state, self.failures, self.opened_at = "closed", 0, 0.0

    def allow(self) -> bool:
        if self.state == "open" and self.clock.now - self.opened_at >= self.cooldown:
            self.state = "half_open"                      # 只放一個探測請求進去
        return self.state != "open"

    def record(self, ok: bool) -> None:
        if ok:
            self.state, self.failures = "closed", 0
            return
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.threshold:
            self.state, self.opened_at = "open", self.clock.now


@dataclass
class Route:
    provider: FakeProvider
    eval_covered: bool                                    # 這個 agent 版本在這個模型上跑過 eval 才能當 fallback


class ModelGateway:
    def __init__(self, routes: list[Route], clock: Clock):
        self.routes, self.clock = routes, clock
        self.breakers = {r.provider.name: Breaker(clock) for r in routes}

    def complete(self, messages: list[dict], tenant_regions: set[str]) -> tuple[ModelResponse, list[str]]:
        tried: list[str] = []
        for r in self.routes:
            p, br = r.provider, self.breakers[r.provider.name]
            if p.region not in tenant_regions or not r.eval_covered:
                tried.append(f"{p.name}:不允許")           # 資料駐留或品質未驗證：寧可失敗也不送
                continue
            if not br.allow():
                tried.append(f"{p.name}:熔斷中")           # 不浪費一次逾時去碰已知壞掉的供應商
                continue
            try:
                resp = p.complete(messages)
            except ProviderError as exc:
                br.record(False)
                tried.append(f"{p.name}:{exc}")
                if not exc.retryable:
                    raise
                continue
            br.record(True)
            tried.append(f"{p.name}:OK")
            return resp, tried
        raise ProviderError(503)


clock = Clock()
primary = FakeProvider("frontier-us", "us", clock, outage=lambda t: 503 if 10 <= t < 70 else 0)
backup = FakeProvider("frontier-alt", "us", clock)
small = FakeProvider("small-eu", "eu", clock)
gw = ModelGateway([Route(primary, True), Route(backup, True), Route(small, True)], clock)
msgs = [{"role": "user", "content": "B-1042 到哪了？"}]

for t in (0, 10, 15, 20, 25, 50, 75, 85, 90):
    clock.now = float(t)
    resp, tried = gw.complete(msgs, tenant_regions={"us", "eu"})
    print(f"t={t:>3}s  熔斷器={gw.breakers['frontier-us'].state:<10}{' → '.join(tried)}")

# 歐盟租戶只允許 eu 區域；備援模型也必須在 eval 覆蓋清單裡
clock.now = 30.0
resp, tried = gw.complete(msgs, tenant_regions={"eu"})
print("EU 租戶：", " → ".join(tried), "｜", resp.text)
assert tried[-1] == "small-eu:OK" and primary.hits == 7

strict = ModelGateway([Route(primary, True), Route(backup, False)], clock)
clock.now = 20.0
try:
    strict.complete(msgs, tenant_regions={"us"})
except ProviderError as exc:
    print("備援未經 eval：不切換，回報", exc)
```

```text
t=  0s  熔斷器=closed    frontier-us:OK
t= 10s  熔斷器=closed    frontier-us:HTTP 503 → frontier-alt:OK
t= 15s  熔斷器=closed    frontier-us:HTTP 503 → frontier-alt:OK
t= 20s  熔斷器=open      frontier-us:HTTP 503 → frontier-alt:OK
t= 25s  熔斷器=open      frontier-us:熔斷中 → frontier-alt:OK
t= 50s  熔斷器=open      frontier-us:HTTP 503 → frontier-alt:OK
t= 75s  熔斷器=open      frontier-us:熔斷中 → frontier-alt:OK
t= 85s  熔斷器=closed    frontier-us:OK
t= 90s  熔斷器=closed    frontier-us:OK
EU 租戶： frontier-us:不允許 → frontier-alt:不允許 → small-eu:OK ｜ small-eu 的回答 #0
備援未經 eval：不切換，回報 HTTP 503
```

逐行看這條時間線。t=0 主要模型正常。t=10 與 t=15，主要模型回 503，gateway 立刻改走 `frontier-alt`，使用者拿到的是備援模型的回答，熔斷器仍是 closed，但失敗次數在累積。t=20 是第三次連續失敗，熔斷器跳到 open。t=25 的差別很重要：gateway 不再嘗試主要模型，直接標記「熔斷中」並走備援，省下了一次等待逾時的時間；在真實系統裡，這一次逾時可能是好幾秒。t=50 已經超過 30 秒的 cooldown，熔斷器進入 half_open 放一個探測請求過去，但主要模型還沒恢復，於是重新 open 並重新計時。t=75 仍在新的 cooldown 中，直接跳過。t=85 再次探測，此時故障已經結束，熔斷器回到 closed，t=90 正常。

最後兩行展示兩個平台約束。歐盟租戶只允許 eu 區域，所以即使 `frontier-us` 和 `frontier-alt` 都是更強的模型，gateway 也直接跳過，送到 `small-eu`；這是一個合規決定，不是品質決定。最後一個 gateway 的備援模型沒有通過這個 release 的 eval（`eval_covered=False`），所以主要模型故障時，gateway 寧可回報 503，也不切到一個沒有驗證過的模型。assert 也驗證主要模型總共只被呼叫 7 次：熔斷期間的請求完全沒有碰它，這就是熔斷器保護供應商、也保護自己延遲的方式。

### 第三段：依 eval 指標自動回滾的 canary controller

第三段實作 36.11 節的 canary 狀態機。`AgentRelease` 把 prompt、model snapshot、tool 版本與 policy 綁在一起，用內容雜湊當版本號；`bucket_of` 依 session id 雜湊分流，保證同一個 session 永遠落在同一個版本；`CanaryController` 在每個階段收集線上 grader 的評分，依三條規則推進或回滾。模擬中 baseline 的真實成功率是 90%、guardrail 觸發率 0.4%；三個候選 release 的真實表現由參數決定，controller 當然看不到這些參數，只能看到評分結果。

```python
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentRelease:
    """一次發布 = prompt、model snapshot、tool 版本、policy 一起鎖定；任何一項改變都是新版本。"""
    prompt: str
    model: str                      # 帶日期的 snapshot，不用會漂移的 alias
    tools: tuple[tuple[str, str], ...]
    policy: str

    @property
    def id(self) -> str:
        blob = json.dumps([self.prompt, self.model, self.tools, self.policy], ensure_ascii=False)
        return "rel-" + hashlib.sha256(blob.encode()).hexdigest()[:8]


def bucket_of(session_id: str) -> int:
    """依 session id 雜湊分桶（0–99）：同一個 session 永遠落在同一個版本，不會中途換腦。"""
    return int(hashlib.sha256(session_id.encode()).hexdigest(), 16) % 100


@dataclass
class Arm:
    n: int = 0
    passed: int = 0
    guardrail: int = 0
    cost: float = 0.0

    def rate(self) -> float:
        return self.passed / self.n if self.n else 0.0


@dataclass
class CanaryController:
    """依線上 eval 指標推進或回滾：品質用比例差的信賴下界，guardrail 與成本用硬門檻。"""
    steps: tuple[int, ...] = (1, 5, 25, 50)        # 通過 50% 階段後全量
    min_samples: int = 400                   # 每一階段 canary 至少要有這麼多筆評分
    max_quality_drop: float = 0.03           # 可接受的成功率下降
    max_guardrail_rise: float = 0.01
    max_cost_rise: float = 0.15
    stage: int = 0
    sessions: int = 0                        # 從開始到現在經過多少個 session（含 baseline）
    state: str = "running"                   # running｜promoted｜rolled_back
    base: Arm = field(default_factory=Arm)
    canary: Arm = field(default_factory=Arm)
    log: list[str] = field(default_factory=list)

    @property
    def percent(self) -> int:
        return 0 if self.state == "rolled_back" else self.steps[self.stage]

    def observe(self, arm: str, passed: bool, guardrail: bool, cost: float) -> None:
        a = self.canary if arm == "canary" else self.base
        self.sessions += 1
        a.n, a.passed, a.guardrail, a.cost = a.n + 1, a.passed + passed, a.guardrail + guardrail, a.cost + cost

    def decide(self) -> None:
        b, c = self.base, self.canary
        if c.n < 50:
            return
        # guardrail 是安全指標：樣本少也要立刻反應，不等統計顯著
        c_gr, b_gr = c.guardrail / c.n, b.guardrail / max(b.n, 1)
        if c.guardrail >= 5 and c_gr - b_gr > self.max_guardrail_rise:
            return self._finish("rolled_back", f"guardrail 觸發率 {c_gr:.1%} vs {b_gr:.1%}（n={c.n}）")
        if c.n < self.min_samples:
            return
        diff = c.rate() - b.rate()
        se = math.sqrt(c.rate() * (1 - c.rate()) / c.n + b.rate() * (1 - b.rate()) / b.n)
        lower, upper = diff - 1.64 * se, diff + 1.64 * se          # 單尾 95% 的粗略區間
        cost_rise = (c.cost / c.n) / (b.cost / b.n) - 1
        detail = f"成功率 {c.rate():.1%} vs {b.rate():.1%}，差的 90% 區間 [{lower:+.2%}, {upper:+.2%}]，成本 {cost_rise:+.0%}"
        if upper < -self.max_quality_drop or cost_rise > self.max_cost_rise:
            return self._finish("rolled_back", detail)
        if lower > -self.max_quality_drop:
            self.log.append(f"  {self.percent:>2}% 通過（累計 {self.sessions:,} 個 session）：{detail}")
            if self.stage == len(self.steps) - 1:
                return self._finish("promoted", "推到 100%")
            self.stage += 1
            self.base, self.canary = Arm(), Arm()           # 每一階段重新累積，避免舊資料稀釋新問題
        # 兩個條件都不成立：證據不夠，繼續收集

    def _finish(self, state: str, why: str) -> None:
        self.state = state
        verb = "回滾" if state == "rolled_back" else "完成"
        self.log.append(f"  {verb}（{self.steps[self.stage]}% 階段，累計 {self.sessions:,} 個 session）：{why}")


def rollout(true_rate: float, guardrail_rate: float, cost: float, seed: int) -> CanaryController:
    """模擬線上流量：每個 session 依桶號分到 baseline 或 canary，跑完後由線上 grader 評分。"""
    rng = random.Random(seed)
    ctl = CanaryController()
    for i in range(300_000):
        if ctl.state != "running":
            break
        arm = "canary" if bucket_of(f"sess-{seed}-{i}") < ctl.percent else "base"
        if arm == "canary":
            ok, gr, c = rng.random() < true_rate, rng.random() < guardrail_rate, cost
        else:
            ok, gr, c = rng.random() < 0.90, rng.random() < 0.004, 1.00
        ctl.observe(arm, ok, gr, c * rng.uniform(0.8, 1.2))
        ctl.decide()
    return ctl


v1 = AgentRelease("客服 prompt v12", "frontier-2026-06-01", (("refund", "3"), ("get_order", "5")), "refund<=500")
v2 = AgentRelease("客服 prompt v13", "frontier-2026-06-01", (("refund", "3"), ("get_order", "5")), "refund<=500")
print("baseline", v1.id, "｜ candidate", v2.id, "（只改了 prompt，版本號就不同）")

for title, rate, gr, cost, seed in [("R1 改寫語氣（品質持平、成本略降）", 0.90, 0.004, 0.95, 7),
                                     ("R2 刪掉一行退款規則（品質下降）", 0.84, 0.004, 0.90, 8),
                                     ("R3 換新工具描述（guardrail 變多）", 0.90, 0.040, 1.00, 9)]:
    ctl = rollout(rate, gr, cost, seed)
    print(f"── {title} → {ctl.state}")
    print("\n".join(ctl.log))

assert v1.id != v2.id
assert rollout(0.90, 0.004, 0.95, 7).state == "promoted"
assert rollout(0.84, 0.004, 0.90, 8).state == "rolled_back"
assert rollout(0.90, 0.040, 1.00, 9).log[-1].startswith("  回滾（1% 階段")
```

```text
baseline rel-b1fe216c ｜ candidate rel-fa6ecb59 （只改了 prompt，版本號就不同）
── R1 改寫語氣（品質持平、成本略降） → promoted
   1% 通過（累計 78,737 個 session）：成功率 88.8% vs 90.0%，差的 90% 區間 [-3.00%, +0.65%]，成本 -5%
   5% 通過（累計 86,349 個 session）：成功率 91.2% vs 90.3%，差的 90% 區間 [-1.44%, +3.33%]，成本 -4%
  25% 通過（累計 88,053 個 session）：成功率 89.6% vs 89.8%，差的 90% 區間 [-2.95%, +2.55%]，成本 -5%
  50% 通過（累計 89,195 個 session）：成功率 90.5% vs 90.6%，差的 90% 區間 [-2.99%, +2.69%]，成本 -5%
  完成（50% 階段，累計 89,195 個 session）：推到 100%
── R2 刪掉一行退款規則（品質下降） → rolled_back
  回滾（1% 階段，累計 77,071 個 session）：成功率 85.0% vs 90.1%，差的 90% 區間 [-7.26%, -3.01%]，成本 -11%
── R3 換新工具描述（guardrail 變多） → rolled_back
  回滾（1% 階段，累計 15,209 個 session）：guardrail 觸發率 3.2% vs 0.4%（n=155）
```

第一行驗證版本化：兩個 release 只差了 prompt 的版本，雜湊就完全不同，所以 trace 上的 release id 能精確指出「是哪一個組合」。

**R1（品質持平、成本略降）**順利推到全量，但請看它花了多少流量：在 1% 階段，canary 要累積到足夠的評分樣本，信賴區間的下界才高於 −3%，這花了將近 7.9 萬個 session；之後 5%、25%、50% 階段因為 canary 比例變大，分別只多花了約 7,600、1,700 與 1,100 個 session。這說明一個實務上很重要的事實：**小比例的 canary 很安全，但要靠它判斷細微的品質差異非常慢**。1% 階段比較適合抓「明顯壞掉」的版本（錯誤率暴增、guardrail 觸發），細微的品質比較應該在比例較大的階段做，或交給 offline eval 與 shadow。另外注意每個「通過」的下界都剛好落在 −3% 附近：controller 每收到一筆資料就檢查一次，條件一成立就推進，所以推進總是發生在邊界上。這種「一直偷看」的做法會讓實際的誤判率高於名目上的 95%，production 應該改用專為連續監控設計的序貫檢定，或固定每個階段的樣本數再判斷。

**R2（刪掉一行退款規則）**真實成功率 84%，在 1% 階段就被回滾：canary 的成功率 85.0% 對 baseline 90.1%，差異的區間上界 −3.01% 已經低於容忍度，代表「有足夠證據顯示它變差了」。即使成本便宜了 11%，controller 也不會因此放行，品質門檻優先。**R3（guardrail 變多）**最快被攔下：只用了 155 個 canary 樣本，guardrail 觸發率 3.2% 對 0.4%，超過硬門檻就立即回滾，沒有等統計顯著。這是刻意的不對稱：安全指標寧可誤殺。為了避免一兩次偶發事件就觸發回滾，程式要求至少累積 5 次觸發，這個數字本身也是可以調整的取捨。

| 模擬 | 機制 | 對應的事故或風險 | 對應小節 |
|---|---|---|---|
| 第一段 | 三層限流（配額 → 租戶 bucket → 全域 bucket）、預留與結算 | 大租戶 fan-out 吃光 TPM；配額被低估或超用 | 36.8、36.9 |
| 第二段 | fallback 鏈、三態熔斷器、資料駐留與 eval 覆蓋約束 | 供應商區域故障；切到未驗證模型；資料出境 | 36.5、36.12 |
| 第三段 | 不可變 release、session 雜湊分流、依 eval 指標推進或回滾 | prompt 與 model 一起改卻無法回滾；品質靜默下降 | 36.10、36.11 |

三段程式都刻意沒有做的事也列在這裡：限流與熔斷的狀態都在單一 process 的記憶體裡；熔斷器只看連續失敗次數，沒有用滑動時間窗的失敗率並區分 429 與 5xx；canary controller 的統計檢定是粗略的常態近似；沒有實作 kill switch 與回滾後對進行中 session 的處理；也沒有把這些判斷寫進 event log 供事後稽核。第 42 章的多租戶客服平台設計演練會把這些機制放回完整的系統，第 45 章則把它們組進 `loom` v1.0。

## 36.14 實務應用

同一張參考架構，在不同產品上的重點完全不同。以下三個情境說明哪些元件是關鍵、哪些可以簡化。

**情境一：多租戶電商客服平台（青鳥的主線）**。數千家店家、同步互動、尖峰明顯（雙十一、整點促銷）。關鍵元件是 model gateway 的 per-tenant bucket 與 fallback，以及 tool gateway 的退款 policy。同步客服的 session 很短，event log 的主要價值是 pod 重啟時不丟對話，以及事後稽核；sandbox 幾乎用不到。版本發布以租戶分組做 canary，大客戶可以選擇「延後升級」。降級模式要事先定義：主要模型不可用時退回 L3、只回答訂單與物流狀態、其他問題轉真人。第 42 章會用 system design interview 的形式完整走一遍這個平台。

**情境二：background coding agent 平台**。開發者在 issue 上指派任務，agent 在 sandbox 裡改程式、跑測試、開 pull request，一個任務可能跑幾十分鐘。這裡的關鍵元件是 job queue 與 sandbox pool：任務要能在 worker 死掉後從 event log 恢復，sandbox 要預熱並快取 repo，每個任務的 token 預算與 wall-clock 上限要嚴格。tool gateway 的重點是 git 與 CI 的憑證：憑證只在 clone 與 push 時由 proxy 注入，sandbox 內沒有長效 token。發布策略偏重 offline eval（在固定的 repo 與 issue 集上跑），因為 coding 任務的結果可以用測試客觀驗證。公開資料中，GitHub Copilot coding agent 在 GitHub Actions 的臨時環境執行，依公開文件，OpenAI Codex 的雲端任務也在隔離的雲端環境中執行；第 43 章會完整設計這類平台。

**情境三：受監管產業的企業內部 agent 平台（例如金融或醫療）**。租戶是企業內部的各部門，最大的需求是稽核、資料駐留與權限。這類平台通常選擇較強的隔離：每個部門獨立的檢索 namespace、敏感部門獨立的資料庫 schema、模型只能使用經過核准的區域端點，fallback 清單裡沒有其他區域。稽核日誌要能回答「這個回答是用哪一版 prompt、哪個模型、引用了哪些文件產生的」，所以 release manifest 和檢索紀錄都要寫進稽核。發布流程通常需要變更審查委員會核准，canary 的速度會比消費性產品慢很多，這是合規成本，而不是工程上的失敗。

| 產品類型 | 最關鍵的元件 | 隔離重點 | 發布重點 | 降級模式 |
|---|---|---|---|---|
| 多租戶客服 | model gateway、tool gateway policy | per-tenant TPM、檢索 namespace | 依租戶分組 canary | 退回 L3、只答狀態查詢、轉真人 |
| background coding | job queue、sandbox pool、event log | 每任務 sandbox、憑證 proxy | offline eval（測試可驗證） | 暫停入列、保留已完成步驟 |
| 受監管企業平台 | tool gateway 稽核、release registry | 部門 namespace、區域鎖定 | 變更審查＋慢速 canary | 停用自動動作，只保留查詢 |

這張表的共同點是：架構圖的方塊幾乎一樣，差別在每個方塊的參數、隔離強度與降級策略。這也是為什麼本章花大部分篇幅在「每個元件的職責與失效模式」，而不是某一種具體部署：同一套元件，換一組設定，就是另一種產品。

> [!note] 2026 現況
> 截至 2026 年 10 月，主要雲端與模型供應商都提供「託管 agent harness」：Claude Managed Agents（beta）、OpenAI 的 Agents API、Amazon Bedrock AgentCore 的 Harness 與 Runtime、Google Gemini Enterprise Agent Platform 的 Agent Runtime。依各家公開文件，它們把 harness loop、session 持久化、sandbox 與部分 gateway 功能做成雲端服務；AgentCore 把 Runtime、Gateway、Identity、Memory、Policy、Observability、Evaluations 等拆成可以單獨使用的服務。Claude Managed Agents 依公開文件不支援 ZDR 與 HIPAA BAA，受監管產業選型時要特別確認。租戶隔離、配額分配、release 版本化與降級模式等責任劃分，公開資料多半沒有完整說明，選型時要逐項向供應商確認；第 26 章有完整比較。

## 36.15 設計檢查清單

設計或審查一個 production agent 平台時，逐項回答下面的問題。

1. harness 是否完全 stateless？任何一個 pod 被砍掉時，進行中的 session 能否由另一個 pod 從 event log 接手，而且不重打已完成的模型呼叫？
2. event log 的寫入是否帶序號或條件寫入，能擋住 lease 過期後仍在寫的舊 worker？
3. 所有模型呼叫是否都經過 model gateway？是否還有任何服務直接持有供應商金鑰？
4. 整條呼叫鏈是否只有一層做重試？重試是否只針對可重試的錯誤，並遵守 retry-after？
5. fallback 清單上的每一個模型，是否都在這個 release 上跑過 eval？是否遵守租戶的資料駐留限制？
6. 所有 tool 呼叫是否都經過 tool gateway 的授權、policy、憑證注入、去重與稽核？policy 服務故障時，寫入類 tool 是 fail-closed 嗎？
7. 每個共享資源（TPM、worker、sandbox、佇列、資料庫、業務 API）是否都有每租戶上限？上限能否依方案等級設定？
8. 限流是以 token 為單位嗎？是否採用預留與結算？rate_limited 與 quota_exceeded 是否回傳不同的結果並觸發不同的處理？
9. prompt、model snapshot、tool 版本、policy、檢索索引、harness 設定是否綁成一個不可變的 release？model 是否使用 snapshot 而非 alias？
10. session 是否在建立時綁定 release，整個 session 不換版本？分流是否用 session 或租戶的雜湊？
11. 發布管線是否依序有 offline eval、shadow（或其替代）、canary？canary 的推進與回滾規則是否寫成程式，而不是靠人看儀表板？
12. 每個 span 是否帶 tenant id、release id 與 model snapshot？計量是否全量、不抽樣？稽核與 debug trace 是否分開治理？
13. 每個有狀態元件是否有明確的 RPO 與 RTO？最近一次 DR 演練是什麼時候、發現了什麼？
14. 主要模型不可用時的降級模式是否事先定義（包括降低 autonomy 等級），並且有可以立即切換的 feature flag？

## 36.16 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 一個大租戶活動時，所有租戶都收到 429 | 共用供應商 TPM，沒有 per-tenant bucket | 依租戶切 token 用量與被限流次數，看尖峰是否集中在一個租戶 | 三層限流；fan-out 任務在佇列等令牌；大客戶專屬容量 |
| 部署後使用者說 agent 忘了前面的對話 | harness 把對話狀態放在 pod 記憶體 | 部署時間點與「對話重頭開始」的 session 比例對照 | stateless harness；每步寫入 event log 後才繼續；wake 時重建 context |
| 同一個 session 的歷史出現兩條分岔、tool 被執行兩次 | lease 過期的舊 worker 繼續寫入 | 在 event log 找同一序號附近不同 writer 的事件 | 條件寫入（預期序號）；被拒絕的 worker 直接放棄 session |
| 品質下降，但說不出是哪個改動造成的 | prompt、model、tool 沒有一起版本化；trace 沒有 release id | 檢查 trace 是否帶 release id 與 model snapshot | release manifest；model 用 snapshot；release 不可變，回滾就是切流量 |
| 供應商小故障演變成全面中斷 | 多層重試造成重試放大；沒有熔斷器 | 比較故障期間對供應商的實際呼叫數與原始請求數 | 只在 runtime 一層重試，SDK 與 gateway 不重試；退避加 jitter；熔斷器與 fallback |
| 故障切換後回答品質明顯變差、使用者投訴 | fallback 到沒有 eval 覆蓋的模型 | 依「是否來自備援模型」切線上品質指標 | fallback 只列 eval 過的模型；備援期間降低 autonomy 等級 |
| 月底租戶抱怨額度被扣太多 | 只預留不結算，或全域不過時沒退回租戶令牌 | 比對計量的實際用量與配額扣減量 | 預留估計值、結算實際值；全域拒絕時歸還租戶令牌 |
| canary 一直不推進，或很快就推到全量卻出事 | 1% 階段樣本不足；每筆資料都檢查造成誤判 | 看每個階段的評分樣本數與信賴區間寬度 | 依樣本數估算每階段時間；用序貫檢定；細微差異交給 offline eval |
| 某店家的客服回答出現別家店的資訊 | 快取或檢索的 key 沒有包含租戶 | 檢查 cache key 與檢索過濾條件；搜尋 trace 中跨租戶命中 | key 一律含租戶與權限；檢索在引擎內過濾或分 namespace |
| policy 服務重啟期間有退款沒經過核准 | tool gateway 在 policy 不可用時 fail-open | 在稽核日誌找 policy 判定為空的寫入動作 | 寫入與 destructive tool 一律 fail-closed；告警 policy 可用性 |

## 本章重點整理

- production agent 平台的參考架構由 API gateway、stateless agent service、session store 與 event log、job queue 與 worker、sandbox pool、model gateway、tool gateway、memory／retrieval store 與 observability pipeline 組成，真正有狀態的元件只有少數幾個。
- harness 要設計成 stateless：所有狀態都在 append-only 的 event log，任何 worker 都能用 session id 喚醒 session、重建 context 並接著執行。
- 同一個 session 同一時間只能有一個 writer；寫入 event log 時帶預期序號，可以擋住 lease 過期後仍在寫的舊 worker。
- 非同步任務透過佇列與 worker 執行，等待核准時要釋放 worker；worker 的擴展訊號是佇列深度與等待時間，不是 CPU。
- model gateway 是所有模型呼叫的唯一出口，依序做配額、快取、routing、熔斷、adapter 與計量；整條鏈只能有一層重試。
- fallback 只能指向在該 release 上通過 eval、且符合租戶資料駐留限制的模型；未經驗證的 fallback 會把中斷變成靜默的品質下降。
- tool gateway 用確定性程式集中處理授權、policy、憑證注入、idempotency 與稽核，寫入類 tool 在 policy 不可用時必須 fail-closed。
- 多租戶隔離是逐資源決定的：運算可以共用，資料與身分要分開，執行程式碼的 sandbox 永遠不共用。
- agent 平台的限流單位是 token，不是請求數；用月配額、租戶 token bucket 與全域 bucket 三層，並以預留估計值、結算實際值的方式計算。
- rate_limited 與 quota_exceeded 是不同的語意：前者稍後再試，後者重試無用，呼叫端要採取不同的處理。
- prompt、model snapshot、tool 版本、policy、檢索索引與 harness 設定要綁成一個不可變的 release，session 建立時綁定並在整個 session 內不變。
- 發布管線依序是 offline eval、shadow、canary，再視需要做 A/B；canary 依品質信賴區間推進或回滾，安全指標用硬門檻立即回滾。
- 小比例 canary 安全但統計力低，細微的品質差異需要大量樣本；推進規則若每筆資料都檢查，要改用序貫檢定。
- 災難復原要逐元件訂 RPO 與 RTO；event log、稽核與去重表要接近零 RPO，trace 與索引可以接受丟失或重建。
- 主要模型不可用時，除了切換備援，還要主動降低 autonomy 等級並暫停可延後的任務，並定期演練切換與降級。

## 延伸問答

> [!question]- Q1. 為什麼 agent service 一定要 stateless？把對話狀態放在記憶體、用 sticky session 把同一個使用者固定導到同一個 pod，不是更快嗎？
> sticky session 確實能省下每一輪從 event log 重建 context 的時間，但它把 pod 的生命週期和 session 的生命週期綁在一起。pod 會因為部署、自動縮容、節點維護、記憶體不足而消失，每一次消失都會讓上面所有進行中的 session 一起不見，這正是 36.1 節週六凌晨的事故。agent session 又特別長：一個背景任務可能跑幾十分鐘，一個等核准的 session 可能停好幾天，比 pod 的平均壽命長得多。
>
> 比較好的做法是把「快取」和「狀態」分開。pod 可以在記憶體裡快取最近讀過的 session 歷史，用 sticky routing 提高命中率，但真相永遠在 event log：快取遺失時只是變慢，不會變錯。每一步的結果先寫入 log 再繼續，wake 時比對 log 的最新序號，序號一樣就用快取，不一樣就重讀。這樣同時拿到了 sticky session 的效能與 stateless 的可恢復性。
>
> 另一個要補上的是 lease 與序號檢查：如果路由層因為 pod 健康檢查失敗而把 session 轉走，舊 pod 其實還活著，就會出現兩個 writer，這時要靠條件寫入擋下舊 pod。

> [!question]- Q2. 估算題：客服平台尖峰每秒新開 5 個 session，每個 session 平均呼叫模型 6 次、持續 40 秒，每次呼叫平均 6,000 input tokens、300 output tokens。尖峰需要多少 TPM、同時有多少個進行中的 session？
> 模型呼叫率是每秒 5 個 session × 6 次 ＝ 每秒 30 次呼叫。input TPM ＝ 30 × 6,000 × 60 ＝ 每分鐘 1,080 萬 tokens；output TPM ＝ 30 × 300 × 60 ＝ 每分鐘 54 萬 tokens。並行 session 數用 Little's law（系統內平均數量 ＝ 到達率 × 平均停留時間）：5 × 40 ＝ 200 個進行中的 session。
>
> 這些數字直接決定架構參數。input TPM 是供應商配額要申請的量，而且要預留餘裕給重試與 fallback；如果 prompt caching 命中率高，input 的成本會大幅下降，但多數供應商的 TPM 限制是否計入 cache 命中的 tokens 各家規則不同，要查當時的文件。200 個並行 session 決定 agent service 需要多少 pod（每個 pod 能同時處理多少 session 取決於記憶體與連線數，因為大部分時間在等模型），也決定 event log 的寫入率：每個 session 每次呼叫寫兩筆事件，約每秒 60 筆。最後別忘了尖峰係數：雙十一的尖峰可能是平日的數倍，per-tenant bucket 的總和要能在全域上限之內分配完。

> [!question]- Q3. per-tenant token bucket 和月配額都能限制租戶用量，為什麼兩個都要？
> 它們限制的時間尺度與目的不同。token bucket 限制的是「速率」，時間尺度是秒到分鐘，目的是保護共享資源：即使一個租戶有很多月配額，也不能在兩分鐘內吃光全公司的 TPM，讓其他租戶全部 429。月配額限制的是「總量」，時間尺度是一個計費週期，目的是商業上的：租戶買了多少額度、平台承擔多少成本。
>
> 只有月配額，週二的 noisy neighbor 事故照樣會發生，因為萬家購物的額度很大，它可以在短時間內全部用掉。只有 token bucket，平台無法控制單一租戶的月成本，一個以穩定速率持續使用的租戶，月底帳單可能遠超過它付的費用。兩者被觸發時的處理也不同：被限速應該稍後再試，配額用完則重試無用，應該通知租戶管理者或升級方案，所以 36.13 節的程式回傳兩種不同的結果。實務上還會加上「軟警告」，例如配額用到 80% 時通知，讓租戶有時間反應，而不是突然被拒絕。

> [!question]- Q4. 情境題：你在 production 看到主要模型供應商開始大量回 429，model gateway 的熔斷器全部打開，流量都切到備援供應商，結果備援供應商也開始 429。發生了什麼事？應該怎麼設計？
> 這是把「限流」誤當成「故障」處理的典型連鎖反應。429 的意思是「你送太快了」，端點本身是健康的；熔斷器把它當成故障打開，把全部流量推到備援供應商，而備援供應商的配額通常比主要供應商小，很快也被打滿，最後兩邊都在限流，整體可用容量反而變小。如果上層還有多層重試，情況會更糟。
>
> 設計上要把 429 和 5xx／逾時分開處理。429 應該觸發降速：遵守 retry-after，讓請求在 gateway 或佇列裡排隊等待令牌，同時檢查是不是某個租戶的流量暴增（per-tenant bucket 是否設得太寬）。只有 5xx 與逾時才計入熔斷器的失敗次數。必要時可以把一部分「溢出」流量導到備援，但要按比例而不是全部，並且備援端也要有自己的全域 bucket。根本解法則是容量規劃：依 Q2 的方法估算尖峰 TPM，事先向供應商申請足夠的配額，並把非同步、可延後的任務排在離峰時段。

> [!question]- Q5. 為什麼 session 要在建立時綁定 release、整個 session 不換版本？如果新版本修了一個嚴重的 bug，難道進行中的 session 都要繼續用有 bug 的舊版本？
> 綁定版本的理由有三個。第一是行為一致：session 前半段是在舊 prompt 與舊 tool schema 下產生的，中途換版本，模型會看到規則前後不一致的歷史，舊的 tool 呼叫可能在新版本裡已經改名或改參數。第二是成本：system prompt 或 tool 定義一改，prompt cache 的前綴就失效，這個 session 之後每一輪都要付全價。第三是可重現與可稽核：事後要能回答「這個回答是用哪個版本產生的」，一個 session 對應一個 release 最清楚；對長時間任務來說，第 22 章的事件重播也要求同一版程式。
>
> 嚴重 bug 是例外處理，不是常態路徑。如果 bug 會造成錯誤的副作用（例如錯誤退款），第一時間該用的是 kill switch 或 tool gateway 的 policy 關掉那個動作，這不需要換 release 就能立即生效。如果真的必須遷移進行中的 session，要把它當成明確的操作：暫停 session、在 event log 寫入一筆「release 遷移」事件、必要時做一次 compaction 讓新版本從乾淨的摘要接手，並通知使用者。這樣遷移本身也會被記錄與稽核，而不是悄悄發生。

> [!question]- Q6. canary 和 A/B test 都是把一部分流量給新版本，差別在哪裡？什麼時候用哪一個？
> 兩者問的問題不同。canary 問的是「新版本能不能安全地取代舊版本」，是單邊的風險控制：只要沒有證據顯示新版本變差（在容忍度之內），就逐步推進；目標是盡快、安全地完成發布。A/B test 問的是「兩個版本哪個比較好」，是雙邊的比較：要事先定義主要指標（例如問題解決率、轉換率）、最小可偵測差異與樣本數，跑完預定的樣本才下結論；目標是做產品決策。
>
> 實務上，修 bug、模型 migration、例行的 prompt 調整多半走 canary：我們不期待它更好，只要求它不更差。新的互動方式、新的定價相關行為、改變 autonomy 邊界（例如自動退款上限從 500 調到 1,000）則適合 A/B，因為它們的價值本身就是要被證明的。兩者可以串接：先 canary 確認安全，再在 50% 階段停留足夠久，把它當成 A/B 來比較業務指標。不論哪一種，分流都要以 session 或租戶為單位，並且在兩組都抽樣評分，否則比較的是不同的母體。

> [!question]- Q7. 估算題：baseline 成功率 90%，你希望 canary 能偵測出下降到 87%（3 個百分點），單尾 95% 信心、80% 檢定力。每組大概需要多少評分樣本？如果每秒 5 個 session、canary 佔 5%、線上 grader 只抽 20% 的 session 評分，需要多久？
> 兩比例檢定的樣本數近似公式是 n ≈（z_α ＋ z_β）² ×（p₁q₁ ＋ p₂q₂）／ d²。單尾 95% 的 z_α 約 1.645，80% 檢定力的 z_β 約 0.84，和的平方約 6.18；p₁q₁ ＋ p₂q₂ ＝ 0.9 × 0.1 ＋ 0.87 × 0.13 ≈ 0.203；d² ＝ 0.0009。所以 n ≈ 6.18 × 0.203 ／ 0.0009 ≈ 1,400，每組大約需要 1,400 個評分樣本。
>
> canary 每秒得到 5 × 5% ＝ 0.25 個 session，其中 20% 被評分，也就是每秒 0.05 個評分樣本。1,400 ／ 0.05 ＝ 28,000 秒，大約 7.8 小時，而且這還沒有考慮尖峰與離峰的流量差異。這個數字說明了 36.13 節模擬中看到的現象：小比例 canary 要偵測細微品質差異非常慢。可行的調整包括：提高 canary 期間的評分抽樣比例、提早進入較大的比例、把容忍度放寬到只抓「明顯變差」，並把細微差異的偵測交給 offline eval 與 shadow；同時注意若每筆資料都檢查一次，要改用序貫檢定，否則實際誤判率會高於 5%。

> [!question]- Q8. 面試追問：你的平台要支援「主要模型所在區域整個不可用」的情境，請說明你的 DR 設計，以及哪些東西是你刻意不做強保證的。
> 我會先把元件依「丟了會不會造成錯誤或違規」分級。event log、session store、稽核日誌與 idempotency 去重表是第一級：跨區複製，RPO 接近零，因為丟失它們會造成對話遺失、重複退款或違規；為此接受每一步多幾十毫秒的寫入延遲。release registry 變更很少，多區複本加本地快取即可。模型端點的 DR 是 gateway 的 fallback：同供應商的其他區域（在租戶資料駐留允許時）、再到備援供應商，每一個都在 release 上跑過 eval。切換後進入降級模式：L4 自動退款改回 L3、暫停可延後的 research 任務、把備援容量留給同步客服，並在 trace 上標記備援來源。
>
> 刻意不做強保證的有三類。trace 與 metric 只做盡力而為，故障期間丟一段可以接受，因為稽核另走一條可靠的路。檢索索引與 memory 用定期快照，必要時從原始文件重建，RPO 以小時計，代價是故障期間回答品質可能略降。sandbox 完全不做 DR，用完即丟，進行中的程式執行以 tool 錯誤回到 loop 重新來過。最後我會強調演練：定期打開熔斷器、模擬區域不可用，量測真實的 RTO，並檢查備援金鑰、備援區域的 TPM 配額與降級 feature flag 是否都還有效，因為 DR 最常失敗的地方是這些周邊假設。

## 延伸閱讀

- Anthropic Engineering Blog〈Scaling Managed Agents〉（2026）
- Anthropic Engineering Blog，2026-04-23 的 Claude Code 品質事故分析（postmortem）
- Amazon Bedrock AgentCore Developer Guide〈What is Amazon Bedrock AgentCore〉（AWS 文件）
- Google Cloud〈Agent Engine overview〉（Gemini Enterprise Agent Platform 文件）
- OpenTelemetry〈Semantic Conventions for Generative AI〉（semantic-conventions-genai repository）
- Martin Kleppmann《Designing Data-Intensive Applications》（O'Reilly，2017）
- Michael T. Nygard《Release It! Design and Deploy Production-Ready Software》第二版（Pragmatic Bookshelf，2018）
- Betsy Beyer 等《Site Reliability Engineering》（O'Reilly，2016），處理過載與漸進式發布的章節
