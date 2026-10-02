---
chapter: 24
title: Runtime 實作：事件、串流、並行與取消
part: 5
---

# 第 24 章　Runtime 實作：事件、串流、並行與取消

> [!abstract] 本章地圖
> **核心問題**：同一份 agent loop 要同時面對「使用者在等」「工具會卡住」「供應商會限流」「使用者會中途離開」，runtime 要怎麼設計，才能讓每一次 run 都看得見、等得起、停得下、測得出來？
>
> **你會學到**：
> - 分清楚兩層事件：寫進 Session 的核心事件，與給 UI 即時消費的串流事件，並設計它們之間的彙總規則
> - 用 asyncio 實作串流輸出與背壓，處理慢速消費者、中途斷線與消費者離開
> - 實作有上限的 parallel tool calls：唯讀平行、副作用依序、結果依 call 順序落地、部分失敗不連坐
> - 設計分層 timeout 與 cancellation，保證取消後 tool call 配對仍完整，進行中的副作用如實記成「完成」或「結果未知」
> - 用指數退避加 jitter 重試模型呼叫，避開同步重試風暴與多層重試相乘
> - 為 runtime 建立確定性測試：虛擬時間、fault injection、不變式檢查與取消時間點掃描
>
> **前置知識**：第 4 章（loom v0.1 的 loop、配對規則、停止條件、streaming 組裝）、第 5 章（副作用分級與 idempotency）、第 22 章（durable execution 與事件日誌）、第 23 章（loom v0.5 的核心抽象、核心事件與 Runner 契約）

## 24.1 故事：雙 11 那一晚，runtime 的帳

雙 11 隔週的事故檢討會，白板上寫著那四十分鐘的時間線。第 25 章會談 model 層那一半：沒有備援、沒有熔斷、帳本算錯。老陳把另一半留給 Iris：「供應商過載不是我們能控制的，但那四十分鐘裡，我們自己的 runtime 至少做錯了四件事，而且每一件都會在下一次故障時重演。」

第一件事是**重試風暴**。供應商九點零七分開始回傳過載錯誤，客服 agent 的每個 session 都照同一套固定的退避時間重試：等 1 秒、2 秒、4 秒，沒有任何隨機性。數千個 session 在同一秒失敗，於是在同一秒醒來、同一秒再打一次，監控圖上的請求量變成一排整齊的尖峰。更糟的是，官方 SDK 自己也會重試，公司的 API gateway 又重試一次，一個使用者的問題在最壞情況下變成幾十個請求。第二件事是**殭屍 run**：使用者盯著轉圈圈等不下去，關掉了聊天視窗，但後端的 run 毫不知情，繼續排隊、繼續重試、繼續花錢，替一個已經離開的人回答問題，也繼續替供應商的過載火上加油。

第三件事發生在隔天早上的 hotfix。Iris 在 WebSocket 斷線時加了一行 `task.cancel()`，殭屍 run 確實不見了，但兩個新問題跟著出現。一是某些 session 的歷史裡留下「有 tool call、沒有 tool_result」的紀錄，使用者回來追問時，API 直接回 400，這正是第 4 章事故三的新形態。二是 Maya 在稽核時找到一筆退款：run 被取消時，退款請求已經送到金流閘道，但 loom 什麼都沒記下來。客服看紀錄以為沒退，金流那邊卻顯示已退。幸好第 5 章的 idempotency key 讓使用者重送時沒有退第二次，但「我們不知道自己做了什麼」這件事本身，就是一個嚴重的缺陷。

第四件事平時就存在：阿哲調出平常日的數據，「B-1042 和 B-1077 到哪了？」這種問題也要讓使用者看著空白畫面等六、七秒，因為四個查詢是一個接一個做的，前端在 run 結束之前什麼都收不到。Iris 想為這些問題寫回歸測試，測試裡全是真的 `asyncio.sleep`：CI 多跑了十二分鐘，其中一個 timeout 測試每二十次隨機失敗一次。

老陳在白板上寫下四個問題：「外面的人怎麼知道 run 現在在做什麼？可以同時做幾件事？什麼時候該放棄？被叫停時怎麼收尾？」然後補了一句：「第 4 章的 loop 只回答『下一步做什麼』。這四個問題的 bug 全都藏在時間裡，所以 runtime 的測試也必須能控制時間。」第 23 章定下了 `loom` v0.5 的核心抽象與 Runner 契約；這一章用 asyncio 實作那份契約，也就是 `loom.runtime`。我們會依序處理事件的兩層設計、串流與背壓、平行 tool call、取消與 timeout、重試與退避、loop guard，最後是 runtime 的測試策略，並在「動手做」用虛擬時間把雙 11 的每一個情境重演一遍。

## 24.2 從 loop 到 runtime：loom.runtime 的職責

**runtime**（執行期環境）在這裡指的是「把 Agent 宣告真正跑起來的那一層」：它決定什麼時候呼叫模型、哪些 tool 可以同時執行、每件事最多等多久、失敗了要不要再試、被取消時怎麼收尾，以及在這一切發生時向外報告。舉例來說，客服 Agent 的宣告只說「我有 get_order、get_shipment、refund 三個 tool，最多 8 步」；至於兩個 get_order 要不要同時查、refund 卡住時怎麼辦、使用者離開時怎麼停，全部是 runtime 的決定。第 23 章把 Runner 定義成「執行引擎，負責所有不變式」，並給了一個同步的參考版本；`loom.runtime` 是同一份契約的 async 實作。

```text
   Agent（宣告：instructions、tools、上限）     Session（核心事件；load／append）
          │                                               ▲
          └──────────────────┬────────────────────────────┤ commit：先落地
                             ▼                            │
   Runner（策略：model、middleware、並行上限、timeout、retry、取消寬限期）
                             │ start(agent, input, session, deps)
                             ▼
   Run（一次執行 = 一個 asyncio task）
   ┌───────────────────────────────────────────────────────────────────┐
   │ _drive：run deadline、取消、StopRun、收尾 _settle                   │
   │   └ _loop：每一步從 Session 投影 messages                           │
   │        ├ wrap_model 鏈 → _call_model：串流＋單次 timeout＋退避重試  │
   │        ├ LoopGuard：滑動視窗重複、沒有新資訊                        │
   │        └ _run_tools：分組 → Semaphore＋TaskGroup → wrap_tool 鏈      │
   │ commit(核心事件) ──► Session ──► on_event（tracer、計費）            │
   │        └──────────────────────► 串流佇列（Committed 通知）          │
   │ _push(串流事件) ───────────────► 串流佇列（model_delta、tool_*…）    │
   └───────────────────────────────────────┬───────────────────────────┘
                                           ▼ run.stream()
                              UI、AG-UI 轉接器、呼叫端（第 15 章）
```

這張架構圖由上往下讀。最上面是兩個輸入：Agent 是不可變的宣告，Session 是一段對話的事件存放處，兩者都沿用第 23 章的定義。中間的 Runner 持有「怎麼跑」的策略：用哪個 model（可以是第 25 章的 fallback chain 或 router）、掛哪些 middleware、平行上限與各種 timeout。Runner 本身沒有狀態，可以同時服務上千個 run；每次 `start()` 都產生一個新的 Run 物件，這一次執行的所有狀態（進行中的 tool、已收到的結果、串流佇列）都在 Run 裡，結束就丟掉。Run 的內部分成三層：`_drive` 管生死（deadline、取消、收尾），`_loop` 管每一步做什麼，`_call_model` 與 `_run_tools` 管和外界的互動。最下面是兩條往外的路：核心事件先寫進 Session、再通知 middleware 的 `on_event`、最後推一則 `Committed` 到串流；串流事件則只進串流佇列。這兩條路的差別是本章第一個重要的設計，24.3 節會詳細說明。

為什麼要把 Runner 和 Run 分開？因為同一個 Runner 會被並行使用，如果 Runner 上有一個 `self.pending_calls`，兩個同時進行的 run 就會互相覆蓋。runtime 沿用第 23 章「宣告不可變、狀態在 Session」的道理，把一次執行的暫存狀態放進 Run；取消的單位因此是一個 Run、一個 asyncio task，不會波及其他對話。

| 能力 | loom v0.1（第 4 章） | 第 23 章參考 Runner | loom.runtime（本章） |
|---|---|---|---|
| 執行模型 | 同步 for-loop | 同步，事件寫進 Session | asyncio，一個 run 一個 task |
| 對外輸出 | 結束時回傳 RunResult | 核心事件＋`on_event` | 核心事件＋即時串流（兩層） |
| tool 執行 | 逐一序列 | 逐一序列，經 `wrap_tool` | 唯讀平行（有上限）、副作用依序 |
| 時間 | 無 | 無 | 單次 timeout、run deadline、取消與收尾 |
| 模型失敗 | 往外丟 | 往外丟 | 依 `ModelError` 分類退避重試 |
| 迴圈偵測 | 整個 run 累計 | 無（交給本章） | 滑動視窗＋沒有新資訊 |
| 測試 | ScriptedModel | ScriptedModel | ＋虛擬時間、fault injection、時間點掃描 |

這張表說明了本章的範圍：左兩欄的保證全部保留（步數上限、max_tokens 不執行半截的 tool call、例外轉成觀察、每個 tool call 都有結果），右欄是新增的能力。第 23 章把這個關係寫成一句可以測試的契約：**同樣的 Agent、輸入與劇本，async runtime 寫進 Session 的核心事件序列，必須和同步參考版相同**。平行、串流、重試都只能改變「多快」與「外面看到什麼」，不能改變「事實是什麼」。

為什麼選 asyncio？agent 的工作幾乎全是**等待**：等模型產生下一個 token、等 ERP 回應、等物流商 API。**asyncio** 是 Python 標準函式庫的協作式並行框架：程式在每個 `await` 讓出執行權，event loop 趁這段時間推進其他工作。一個 process 裡可以同時有成千上萬個在等待的 task，每個 task 只是一個小物件。它的另一個好處是取消點很明確：取消只會在 `await` 的位置生效，所以你知道「被取消時程式停在哪裡」。

| 並行模型 | 適合的工作 | 能不能從外部取消 | 主要風險 |
|---|---|---|---|
| thread | 只有同步 SDK 可用、少量阻塞 I/O | 不能強制中止執行中的 thread | 共享狀態要加鎖；數量受限 |
| asyncio | 大量等待網路的工作（模型、API） | 可以，在下一個 `await` 注入取消 | 任何阻塞呼叫都會卡住整個 event loop |
| process | CPU 密集、需要隔離的工作 | 可以強制 kill | 啟動與通訊成本高；第 17 章的 sandbox 屬於這類 |

這張表最常被忽略的是最後一欄。asyncio 不會讓程式變快，只是讓等待可以重疊；某個 tool 在 async 函式裡呼叫同步的 HTTP 函式庫，整個 event loop 就停住，同一個 process 上的所有 run 一起卡住。只有同步 SDK 可用時，可以用 `asyncio.to_thread()` 執行，但 thread 一旦開始就無法被取消（延伸問答 Q8）。

## 24.3 兩層事件：寫進 Session 的事實，與給畫面看的進度

第 23 章把 **Event** 定為唯一的事實來源：messages、trace、帳單都是事件的投影，而且只有七種**核心事件**會寫進 Session：`run_started`、`user_message`、`model_response`、`tool_result`、`handoff`、`guardrail_tripped`、`run_finished`。這七種事件的粒度是「一件完整發生的事」：一次模型回應、一個 tool 的結果。但 runtime 一旦開始串流與平行，外面的人需要知道的是「正在發生的事」：模型吐出了哪幾個字、哪個 tool 剛開始、哪個剛結束、為什麼在重試。這些資訊如果也寫進 Session，一則回答會變成幾百個事件，重播時還要決定這些片段算不算數。

所以 `loom.runtime` 有第二層：**串流事件**（stream event）。它們只推給正在看的人，不持久化；等一件事完整發生後，runtime 才把它**彙總**（summarize）成一個核心事件寫進 Session。舉例來說，模型回應的過程中會推出好幾個 `model_delta`，可能還夾著一個 `model_retry`；收到 stop 之後，runtime 寫入一個 `model_response`，裡面是完整的文字、tool calls、usage，以及這次呼叫總共嘗試了幾次。兩層不能混用：UI 不應該從 Session 拼湊打字效果，計費與重播也不應該依賴串流事件，因為串流事件可能被合併、被丟棄，或者根本沒有人在收。

| 串流事件（不持久化） | 主要欄位 | 彙總成的核心事件 | 彙總的時機 |
|---|---|---|---|
| `model_delta` × n | step、text | `model_response`（text、tool_calls、usage、attempts） | 模型串流收到 stop 之後 |
| `model_retry` × k | attempt、delay、reason、discard_partial | 併入同一個 `model_response` 的 attempts | 同上；重試用盡則由 `run_finished` 記 error |
| `tool_started`、`tool_finished` | call_id、name、status | `tool_result`（id、name、is_error、content、status） | 一組 tool 全部結束後，依 call 順序寫入 |
| `run_cancelling` | reason | 未完成 call 的 `tool_result`（cancelled／unknown）＋`run_finished` | 收尾完成之後 |
| `committed` | event（一個核心事件） | 本身就是核心事件寫入成功的通知 | 寫入 Session 並通知 `on_event` 之後 |

這張表的最後一列是兩層之間的橋。每個核心事件寫進 Session 之後，runtime 也把它包成一則 `committed` 推到串流裡，所以只訂閱串流的前端，可以在同一條有順序的通道上看到「進度」與「已確定的事實」，不必另外輪詢 Session。表中 `tool_result` 多了一個 `status` 欄位（ok、error、timeout、cancelled、unknown），這是 v0.5 依第 23 章「只增不改」的規則新增的欄位：舊的投影只讀 `is_error`，完全不受影響；新的消費者則能區分「失敗了」與「不知道有沒有成功」。

```text
 時間 ─────────────────────────────────────────────────────────────────────►
 串流  delta delta │ tool_started c1  tool_started c2 │ tool_finished c2  tool_finished c1 │ delta…
                   │                                  │   （完成順序：c2 比較快）           │
 核心  ● model_response(calls=[c1,c2])                 │            ● tool_result c1  ● tool_result c2
       ▲ 彙總：stop 之後寫入一次                      │            ▲ 彙總：整組結束後，依 call 順序
 不變式：每個核心事件寫入後才推出 committed；tool_result 一定在對應的 tool_finished 之後；
        model_response 宣告的每個 call，恰好一個 tool_finished、恰好一個 tool_result，順序同宣告
```

這張時序圖把同一段時間在兩層上的樣子疊在一起看。上排是串流：文字片段、兩個 tool 開始、兩個 tool 依完成時間結束，c2 比較快所以先結束；這個順序反映真實發生的時間，畫面據此即時更新卡片。下排是核心事件：`model_response` 在串流結束時寫入一次；兩個 `tool_result` 等整組結束後才寫入，而且依模型提出的順序，c1 在前。為什麼核心事件要用 call 順序？因為 messages 是從核心事件投影出來的，下一次呼叫模型時，歷史的內容與順序必須可重現：同一個劇本跑兩次要得到一樣的 messages，第 9 章的 prompt cache 前綴才穩定，第 22 章的重播才能逐筆比對，第 23 章的契約測試也才能成立。完成順序是一種會隨網路抖動而改變的資訊，它屬於串流，不屬於事實。

每個串流事件都帶一個信封：`run_id`、串流內序號 `n`、相對時間 `t`，再加上依類型固定的欄位。這就是 **typed event**（具型別的事件）：消費者可以用 `isinstance` 或 `match` 分辨，不必解析字串；序號 `n` 讓前端重連時說「我收到第 57 號為止」，伺服器從第 58 號補送。下面的程式把兩層之間的契約寫成檢查器，並重現 Iris 的 hotfix 與一個看似合理的「完成一個就落地一個」實作。

```python
from __future__ import annotations

# 串流的契約：哪些核心事件（● 已寫進 Session）與串流事件可以接在哪裡。UI、tracer、測試都依賴它。
CORE = {"run_started", "user_message", "model_response", "tool_result", "handoff", "guardrail_tripped",
        "run_finished"}


def check_stream(items: list[tuple]) -> list[str]:
    """items 是 (n, type, call_id 或 call_id 清單)；回傳違反契約的地方，空清單代表合法。"""
    problems, closed, last_n = [], False, 0
    requested: list[str] = []                           # model_response 宣告的 tool call（依序）
    finished: set[str] = set()                          # 收到 tool_finished 的 call
    persisted: list[str] = []                           # 收到 tool_result 的 call（依序）
    for n, kind, ref in items:
        if n != last_n + 1:
            problems.append(f"#{n}：前一個是 #{last_n}，中間掉了或重送了")
        last_n = n
        if closed:
            problems.append(f"#{n}：run_finished 之後不能再有 {kind}")
        if n == 1 and kind != "run_started":
            problems.append("第一個事件必須是 run_started")
        if kind == "model_response":
            requested += ref
        elif kind == "tool_finished":
            if ref in finished:
                problems.append(f"#{n}：{ref} 結束了兩次")
            finished.add(ref)
        elif kind == "tool_result":
            if ref not in finished:                     # 彙總一定在串流事件之後：先 finished，才落地
                problems.append(f"#{n}：{ref} 的 tool_result 比 tool_finished 先到")
            persisted.append(ref)
        elif kind == "run_finished":
            closed = True
    if persisted != requested:
        problems.append(f"tool_result 應依序涵蓋 {requested}，實際 {persisted}（配對不完整或亂序）")
    if not closed:
        problems.append("串流沒有以 run_finished 結尾")
    return problems


ok = [(1, "run_started", None), (2, "user_message", None), (3, "model_delta", None),
      (4, "model_response", ["c1", "c2"]), (5, "tool_started", "c1"), (6, "tool_started", "c2"),
      (7, "tool_finished", "c2"), (8, "tool_finished", "c1"),           # 串流：依完成順序
      (9, "tool_result", "c1"), (10, "tool_result", "c2"),              # 核心事件：依 call 順序
      (11, "model_delta", None), (12, "model_response", []), (13, "run_finished", None)]
# Iris 第一版的取消：直接砍掉 task，c2 永遠沒有結果，也沒有 run_finished
cancelled_badly = ok[:7] + [(8, "tool_finished", "c1"), (9, "tool_result", "c1")]
# 完成一個就落地一個：tool_result 變成完成順序，重播與 prompt cache 都會不穩定
completion_order = ok[:7] + [(8, "tool_result", "c2"), (9, "tool_finished", "c1"), (10, "tool_result", "c1")] \
    + [(n, k, r) for n, k, r in ok[10:]]

for name, stream in [("ok", ok), ("cancelled_badly", cancelled_badly), ("completion_order", completion_order)]:
    print(f"{name:<17}", check_stream(stream) or "符合契約")
assert check_stream(ok) == []
assert len(check_stream(cancelled_badly)) == 2 and len(check_stream(completion_order)) == 1
print("核心事件類型：", sorted(t for t in {k for _, k, _ in ok} if t in CORE))
```

```text
ok                符合契約
cancelled_badly   ["tool_result 應依序涵蓋 ['c1', 'c2']，實際 ['c1']（配對不完整或亂序）", '串流沒有以 run_finished 結尾']
completion_order  ["tool_result 應依序涵蓋 ['c1', 'c2']，實際 ['c2', 'c1']（配對不完整或亂序）"]
核心事件類型： ['model_response', 'run_finished', 'run_started', 'tool_result', 'user_message']
```

第一行是合法的串流：兩個 tool 依完成順序結束（c2 在前），但 `tool_result` 依 call 順序落地（c1 在前），每個 call 恰好一次。第二行是 Iris 的 hotfix：task 在 c2 還沒結束時被砍掉，c2 永遠沒有結果，串流也沒有以 `run_finished` 收尾，前端只能一直轉圈圈，Session 裡留下第 4 章那種不完整的配對。第三行是一個常見的「優化」：每個 tool 一完成就寫入 `tool_result`。它不會造成 API 錯誤，因為配對仍然完整，但 messages 的順序開始隨網路延遲而變，同一個劇本跑兩次可能得到不同的歷史，檢查器把它當成違反契約。最後一行列出這段串流用到的核心事件類型，其他都是只存在於串流的事件。這個檢查器在 24.9 節會成為 fault injection 測試的一部分。

hook 看得到哪一層也是刻意的選擇：第 23 章的 `on_event` 在核心事件寫入後被呼叫，本章維持不變，所以 tracer、計費 middleware 只看到七種核心事件，要畫打字效果的前端則訂閱 `run.stream()`。讓 tracing 套件訂閱每一個 delta，會把觀察成本放大幾十倍，一個慢的 tracer 還會拖慢整個 run。

> [!warning] 常見誤解
> 「既然事件是唯一的事實來源，那就把串流事件也全部存起來，最完整。」完整不等於正確。delta 是同一個事實的中間狀態，存進 Session 之後，投影、重播與計費都得決定要不要理它；重試前被丟棄的半段文字更是從來沒有成為事實。需要事後分析串流行為（例如 TTFT 分布）時，把統計值寫進 `model_response` 的欄位，或另外送到第 29 章的 tracing 系統，不要讓 Session 承擔這份工作。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各框架公開文件（細節以官方文件為準）：OpenAI Agents SDK 的 `Runner.run_streamed()` 同時提供原始的模型串流事件與較高層的 run item 事件，正好對應本章的兩層；Google ADK 的 Runner 以事件串流作為輸出，session 就是事件日誌，並區分串流中的部分事件與最終事件；LangGraph 提供 `values`、`updates`、`messages`、`custom`、`debug` 等串流模式，讓呼叫端選擇要看狀態快照、增量還是 token；LlamaIndex Workflows 以 typed Event 驅動步驟。對前端的事件協定，AG-UI 已發布 1.0（第 15 章），把文字、tool call、state 的開始、內容、結束統一成標準事件；Claude Managed Agents 的 Events 以 SSE 串流、由伺服器端持久化，並支援中途 steer 或 interrupt。

## 24.4 串流輸出：從模型片段到使用者的畫面

第 4 章 4.8 節示範過在模型那一端組裝串流：文字片段邊收邊顯示，tool 參數要等完整才能執行。第 25 章的 adapter 把各家不同名稱的串流事件翻成 `text_delta`、`tool_start`、`args_delta`、`stop` 等統一事件。runtime 要做的是另一段路：把這些片段轉成串流事件推給消費者，同時讓 run 繼續往下走。這段路上有兩個獨立的速度：模型產生片段的速度，以及消費者（瀏覽器、手機、AG-UI 轉接器）處理片段的速度。兩者不一樣快時，中間一定要有人做決定。

```text
 Model adapter              Run（producer task）             佇列 maxsize=64        消費者（UI）
   │── text_delta ─────────►│ _push(model_delta) ───────────►│ ─────────────────► │ 畫面長出字
   │── text_delta ─────────►│ _push(model_delta) ───────────►│ 滿了：put 在這裡等 │ 重繪中（慢）
   │── stop(resp) ─────────►│ commit(model_response) ─► Session                   │
   │                        │ _push(committed) ─────────────►│ ─────────────────► │ 泡泡定稿
   │                        │ 執行 tools…                    │                    │
   │                        │ _push(tool_started／finished) ►│ ─────────────────► │ 進度卡片
   │                        │ commit(run_finished) ─► Session，_push(committed) ─►│ 完成
   │                        │                                │◄── 消費者離開 ──── │ 關掉視窗
   │                        │◄── cancel()：stream() 的 finally 觸發 ──────────────┘
```

這張資料流圖有三個角色。左邊是模型 adapter，持續吐出片段。中間的 Run 是一個獨立的 asyncio task（producer），它把片段包成串流事件放進一個**有上限的佇列**；核心事件則先寫進 Session，再把 `committed` 放進同一個佇列。右邊的消費者用 `async for item in run.stream()` 一個一個取出。為什麼 run 要是獨立的 task，而不是讓 `stream()` 這個 async generator 直接推動整個 loop？因為那樣 run 只有在消費者「拉」的時候才會前進：消費者慢，模型的連線就被拖著；消費者在別的地方卡住，run 就跟著停；同一個 run 也無法有兩個消費者。拆成 task 加佇列之後，「消費者慢怎麼辦」「消費者走了怎麼辦」就變成可以明確選擇的政策，而不是 generator 語意的副作用。

**背壓**（backpressure）就是這個政策的核心：下游處理不過來時，壓力要往上游傳，否則中間的緩衝區會無限長大。常見的做法有三種。第一種是無上限佇列，producer 永遠不等，代價是記憶體隨消費者的落後程度成長，一個卡住的手機連線就可能讓伺服器累積上萬個事件。第二種是有上限的佇列，佇列滿了 producer 就在 `put` 等待，壓力一路傳回模型連線；記憶體有上限，但模型那一端被拖慢，太慢時可能觸發供應商的閒置逾時，也會吃掉我們自己的單次 model timeout。第三種是**合併**（coalescing）：消費者每次重繪時，把佇列裡已經到達的片段一次全部取走，畫面更新的次數降下來，但每個字都沒有少。下面用虛擬時間比較這三種做法。程式開頭的 `VirtualTimeLoop` 是本章所有 async 程式共用的測試基礎設施，24.9 節會解釋它的原理；現在只要知道它讓 `asyncio.sleep` 不必真的等待，時間卻照樣準確推進。

```python
from __future__ import annotations

import asyncio
import selectors


class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout                   # 沒事可做：直接把時鐘撥到下一個計時器
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    """asyncio.sleep、timeout 全部照常運作，但時間是假的：一秒不用等，結果完全可重現。"""

    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


DELTAS = [f"字{i:02d}" for i in range(40)]              # 模型每 0.02 秒吐一個片段，共 0.8 秒


async def trial(maxsize: int, coalesce: bool) -> dict:
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)   # maxsize=0 代表沒有上限
    stats = {"max_q": 0, "renders": 0}

    async def producer():                               # runtime：從模型收片段，放進事件佇列
        for d in DELTAS:
            await asyncio.sleep(0.02)
            await q.put(d)                              # 佇列滿了就在這裡等：背壓傳回上游
            stats["max_q"] = max(stats["max_q"], q.qsize())
        await q.put(None)
        stats["producer_done"] = round(loop.time() - t0, 2)

    async def consumer():                               # 慢速前端：每次重繪要 0.1 秒
        shown = []
        while True:
            batch = [await q.get()]
            while coalesce and not q.empty():           # 合併：一次把已經到的片段全部拿走
                batch.append(q.get_nowait())
            done = batch[-1] is None
            shown += [d for d in batch if d is not None]
            await asyncio.sleep(0.1)
            stats["renders"] += 1
            if done:
                break
        assert shown == DELTAS                          # 不論哪種策略，內容都不能掉、不能亂序
        stats["ui_done"] = round(loop.time() - t0, 2)

    await asyncio.gather(producer(), consumer())
    return stats


async def main():
    pad = lambda s, w: s + " " * (w - sum(2 if ord(c) > 0x2E80 else 1 for c in s))   # 中文字佔兩格
    print(pad("策略", 18) + "佇列最長  模型端收完  畫面顯示完  重繪次數")
    rows = {}
    for name, maxsize, coalesce in [("無上限、逐片重繪", 0, False), ("上限 4、逐片重繪", 4, False),
                                    ("上限 4、合併重繪", 4, True)]:
        s = rows[name] = await trial(maxsize, coalesce)
        print(pad(name, 18) + f"{s['max_q']:>8}{s['producer_done']:>11}s{s['ui_done']:>11}s{s['renders']:>10}")
    assert rows["無上限、逐片重繪"]["max_q"] > 30 and rows["上限 4、逐片重繪"]["producer_done"] > 3
    assert rows["上限 4、合併重繪"]["ui_done"] < 1.2 and rows["上限 4、合併重繪"]["renders"] < 15


with asyncio.Runner(loop_factory=VirtualTimeLoop) as runner:
    runner.run(main())
```

```text
策略              佇列最長  模型端收完  畫面顯示完  重繪次數
無上限、逐片重繪        32        0.8s       4.12s        41
上限 4、逐片重繪         4       3.62s       4.12s        41
上限 4、合併重繪         4       0.96s       1.12s        11
```

三列輸出對應三種政策。模型每 0.02 秒吐一個片段，0.8 秒吐完 40 個；前端每次重繪要 0.1 秒。第一列無上限、逐片重繪：模型端 0.8 秒就收完了，但佇列最長累積到 32 個片段，畫面要到 4.12 秒才顯示完，因為 41 次重繪（40 個片段加結束訊號）一個都省不掉；記憶體在這段時間裡隨落後程度成長。第二列有上限、逐片重繪：佇列最多 4 個，記憶體有保障，代價是背壓讓模型端拖到 3.62 秒才收完，等於讓一個慢的手機連線佔住模型連線三秒多。第三列有上限加合併：每次重繪取走所有已到達的片段，只重繪 11 次，畫面 1.12 秒就顯示完，模型端也幾乎沒被拖慢。三種政策都通過了 `shown == DELTAS` 的檢查：不論怎麼合併，內容不能少、不能亂序。

青鳥的做法是「有上限的佇列＋前端合併」：`model_delta` 可以合併，`committed` 與 `tool_finished` 這類狀態事件不能丟。真正的事實在 Session 裡，串流就算被合併，前端重連時仍能拿到完整結果。

串流還有三個要事先決定的政策。第一是**中途斷線**：串流在 stop 之前斷掉，這次回應整個作廢重來（第 4 章 4.8 節），已推出的半段文字要讓前端清掉，所以重試時的 `model_retry` 帶著 `discard_partial=True`。第二是**閒置逾時**（idle timeout）：除了單次呼叫的總時間上限，還要設定「多久沒收到片段就視為斷線」。第三是**消費者離開怎麼辦**：同步聊天的使用者關掉視窗，`loom.runtime` 的 `stream()` 在 `finally` 裡取消 run；背景任務（第 22 章）則應該繼續，前端之後用 Session 加串流序號重新接上。這要由產品決定，不能交給 generator 被垃圾回收的時機。

> [!warning] 常見誤解
> 「串流就是把模型的 SSE 原封不動轉給前端。」模型的串流只有文字與 tool 參數；前端真正需要的 tool 進度、重試、取消、已確定的結果，全都是 runtime 才知道的資訊（第 15 章的 AG-UI 也是同樣的分層）。另外，模型串流裡的 thinking 內容、各家不同的事件名稱，都應該在第 25 章的 adapter 裡被處理掉，不能漏到前端。

## 24.5 Parallel tool calls：同時做，但結果要排好隊

第 3 章拆解過客服回合的延遲：每次模型呼叫加上每個 tool 的延遲，依序串起來。當模型在同一則回應裡要求好幾個互不相依的 tool 時，依序執行就是白白等待。主流 API 都允許模型一次提出多個 tool call，這就是第 4 章提過的 **parallel tool calls**。「B-1042 和 B-1077 到哪了？」需要兩次 get_order、兩次 get_shipment；序列執行的 tool 時間是四者相加，平行執行則是每一步取最慢的那一個。

```text
 序列（v0.1）：tool 時間 0.8 + 0.5 + 0.6 + 2.0 = 3.9 秒
 0.0          0.8      1.3        1.9                         3.9
 ├─ c1 B-1042 ─┤├─ c2 ─┤├─ c3 TC-88301 ┤├─ c4 TC-90512（2.0 秒逾時）─┤

 平行（loom.runtime，上限 4）：每一步取最慢者 0.8 + 2.0 = 2.8 秒
 0.0          0.8 │ 0.8            1.4                         2.8
 ├─ c1 B-1042 ─┤  │ ├─ c3 TC-88301 ┤
 ├─ c2 ────┤      │ ├─ c4 TC-90512（逾時）─────────────────────┤
              barrier：同一步的結果全部到齊，才落地 tool_result 並呼叫模型

 有副作用時的分組：[get_order, get_shipment] → [refund] → [send_email]
                     唯讀，平行                依序      依序（各自一組）
```

這張甘特圖的上半是序列執行，四個 tool 首尾相接，總共 3.9 秒；下半是平行執行，每一步兩個 tool 同時開始，第一步等最慢的 c1（0.8 秒），第二步等逾時的 c4（2.0 秒），總共 2.8 秒。中間那條 barrier 很重要：模型 API 要求「assistant 提出的每個 tool call，都要在下一則訊息之前收到結果」，所以一步之內可以平行，步與步之間仍然是序列的，下一次模型呼叫一定等這一步的所有結果。圖的最下面是有副作用時的分組規則，接下來說明。

平行執行要先回答「誰可以平行」。第 5 章的副作用分級在這裡派上用場：**read** 的 tool 彼此不會互相影響，可以自由平行；**write** 與 **destructive** 的 tool 可能有隱含的先後關係，例如「先退款、再寄通知信」，也可能互相衝突，例如同一張訂單的退款與取消。`loom.runtime` 的規則很保守：連續的唯讀 tool 併成一組平行執行，任何有副作用的 tool 自成一組，依模型給的順序逐一執行，前一組全部結束才開始下一組。更細的做法是依資源加鎖，例如「同一張訂單的寫入互斥、不同訂單可以平行」，這需要 tool 宣告它會碰哪些資源，複雜度高很多，只有在副作用 tool 的延遲真的成為瓶頸時才值得。

第二個問題是「同時最多幾個」。模型可能一次要求十幾個查詢，research agent 的 fan-out 更可能一口氣打出幾十個請求。`loom.runtime` 在每個 run 上放一個 **semaphore**（號誌，限制同時進入某段程式的數量）當平行上限，保護下游不被單一 run 打爆。但要注意，per-run 的上限保護不了共享的下游：一千個 run 各自平行四個，ERP 一樣會收到四千個並行請求。共享資源的上限要放在 process 或整個系統的層級，例如每個下游一個全域 semaphore、每個租戶一個 token bucket，第 36 章的 production 架構會處理。

第三個問題是**部分失敗**：一批 tool 裡有一個失敗、一個卡住，其他的結果怎麼辦？正確答案是「每個 call 的失敗只是它自己的結果」，成功的照常回填，失敗的回填錯誤，卡住的在逾時後回填 timeout，三者都交給模型決定下一步。這聽起來理所當然，但 asyncio 的兩個常用工具預設都不是這個語意。下面的程式讓營運 research agent 一次查六家店的月報，其中一家報錯、一家卡住，比較四種寫法。

```python
from __future__ import annotations

import asyncio
import selectors


class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


# 營運 research agent 一次要求查 6 家店的月報；S-4 的報表服務會報錯，S-6 會卡住
CALLS = [(f"c{i}", f"S-{i}", lat) for i, lat in enumerate([0.6, 0.9, 0.4, 0.5, 0.7, 30.0], start=1)]


async def store_report(store: str, latency: float) -> str:
    await asyncio.sleep(latency)
    if store == "S-4":
        raise ConnectionError("報表服務 502")
    return f"{store} 月營收 OK"


async def safe_call(call_id, store, latency, sem, timeout=2.0) -> tuple[str, str, str]:
    async with sem:                                     # 上限：同時最多 N 個，保護下游
        try:
            async with asyncio.timeout(timeout):
                return call_id, "ok", await store_report(store, latency)
        except TimeoutError:
            return call_id, "timeout", f"{store} 逾時 {timeout}s"
        except Exception as exc:                        # 部分失敗：變成這一個 call 的結果，不影響其他 call
            return call_id, "error", f"{type(exc).__name__}: {exc}"


async def sequential():
    sem = asyncio.Semaphore(1)
    return [f"{c}={st}" for c, st, _ in [await safe_call(c, s, l, sem) for c, s, l in CALLS]]


async def naive_gather():
    global orphans
    orphans = [asyncio.create_task(store_report(s, l)) for _, s, l in CALLS]
    return await asyncio.gather(*orphans)               # 第一個例外就往外丟，其他 task 不會被取消


async def naive_taskgroup():
    async with asyncio.TaskGroup() as tg:                # 一個失敗，其他全部被取消
        tasks = [tg.create_task(store_report(s, l)) for _, s, l in CALLS]
    return [t.result() for t in tasks]


async def wrapped(limit: int):
    sem = asyncio.Semaphore(limit)
    results = await asyncio.gather(*(safe_call(c, s, l, sem) for c, s, l in CALLS))
    # gather 依「傳入順序」回傳，正好是回填 messages 的順序（依 call 順序，不依完成時間）
    assert [c for c, _, _ in results] == [c for c, _, _ in CALLS]
    return [f"{c}={st}" for c, st, _ in results]


async def main():
    loop = asyncio.get_running_loop()
    timings = {}
    for name, fn in [("序列 for-loop", sequential), ("gather（不收例外）", naive_gather),
                     ("TaskGroup（不收例外）", naive_taskgroup),
                     ("逐一包裝＋上限 6", lambda: wrapped(6)), ("逐一包裝＋上限 3", lambda: wrapped(3))]:
        t0 = loop.time()
        try:
            out = " ".join(await fn())
        except Exception as exc:
            out = f"整批失敗：{type(exc).__name__}"
        timings[name] = round(loop.time() - t0, 2)
        pad = 22 - sum(2 if ord(ch) > 0x2E80 else 1 for ch in name)
        print(f"{name}{' ' * pad}{timings[name]:5.2f}s  {out}")
        if fn is naive_gather:
            print(f"{'':22}        ↑ 還有 {sum(not t.done() for t in orphans)} 個 task 在背景跑，結果沒人收")
    assert timings["序列 for-loop"] == 5.1 and timings["逐一包裝＋上限 6"] == 2.0 and timings["逐一包裝＋上限 3"] == 2.9


with asyncio.Runner(loop_factory=VirtualTimeLoop) as runner:
    runner.run(main())
```

```text
序列 for-loop          5.10s  c1=ok c2=ok c3=ok c4=error c5=ok c6=timeout
gather（不收例外）     0.50s  整批失敗：ConnectionError
                              ↑ 還有 4 個 task 在背景跑，結果沒人收
TaskGroup（不收例外）  0.50s  整批失敗：ExceptionGroup
逐一包裝＋上限 6       2.00s  c1=ok c2=ok c3=ok c4=error c5=ok c6=timeout
逐一包裝＋上限 3       2.90s  c1=ok c2=ok c3=ok c4=error c5=ok c6=timeout
```

逐行看這份輸出。序列執行把六個查詢首尾相接，加上 S-6 的 2 秒逾時，總共 5.10 秒。`asyncio.gather` 在預設設定下，第一個例外（S-4 在 0.5 秒時報錯）就直接往外丟，整批結果都拿不到；更隱蔽的是下一行：其他四個 task 並沒有被取消，仍在背景執行，跑完的結果沒有人收，卡住的 S-6 還會一直佔著連線。`TaskGroup`（Python 3.11 新增的結構化並行工具）的行為相反：一個子 task 失敗，它會取消所有兄弟 task，並把例外包成 `ExceptionGroup` 丟出；沒有孤兒，但同樣整批作廢。這兩種語意對「一組互相依賴的工作」是對的，對 tool calls 卻是錯的，因為 tool calls 彼此獨立。

最後兩行是 `loom.runtime` 的寫法：每個 call 各自包一層，把例外與逾時轉成「這個 call 的結果」，外層再用 TaskGroup 或 gather 收齊，這時外層永遠不會看到例外。上限 6 時，總時間由逾時的 S-6 決定，2.00 秒。上限 3 時反而變成 2.90 秒：卡住的 S-6 排在第六個，要等前面空出位子，0.9 秒才開始，再等 2 秒逾時。這是一個實用的觀察：有上限時，慢的 call 越晚開始，整步就越晚結束，所以單次 timeout 的設定往往比平行上限更影響尾端延遲。另外注意 `wrapped()` 裡的 assert：`gather` 依「傳入順序」回傳結果，不依完成順序，這正好是 24.3 節要求的落地順序。

| 寫法 | 延遲 | 一個失敗時 | 孤兒 task | 適合 |
|---|---|---|---|---|
| 序列 for-loop | 各 call 相加 | 只影響自己 | 無 | 有副作用、彼此相依的 call |
| `gather`（預設） | 取最慢者 | 整批拿不到結果 | 有，其他 task 繼續跑 | 幾乎不適合 tool calls |
| `TaskGroup`（不包裝） | 取最慢者 | 取消兄弟，整批作廢 | 無 | 互相依賴、要一起成功的工作 |
| 逐一包裝＋上限＋單次 timeout | 取最慢者（受上限影響） | 只影響自己，回填錯誤 | 無 | `loom.runtime` 的唯讀 tool 組 |

這張表的結論是：結構化並行（TaskGroup）負責「不留孤兒」，逐一包裝負責「部分失敗不連坐」，兩者要一起用，這正是 `loom.runtime` 的 `_run_tools` 與 `_exec`。

平行的概念也能用在 tool 以外的地方。第 23 章提到，async runtime 可以讓 input guardrail 與模型呼叫同時進行，guardrail 一旦觸發就取消主路徑（fail-fast），以降低延遲。判斷能不能這樣做的原則和 tool 一樣：被取消之前多跑的那一段有沒有副作用。只呼叫模型、還沒執行任何 tool，可以並行；一旦會執行 tool，guardrail 就必須在前面擋住，不能和它賽跑。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各家公開文件：OpenAI 的 API 提供 `parallel_tool_calls` 參數控制模型是否在一則回應中提出多個 function call；Anthropic Messages API 可以在 `tool_choice` 中設定 `disable_parallel_tool_use`。當 tool 之間有模型看不出來的相依性時，關掉模型端的平行比在 runtime 端補救更簡單。開源的 coding agent 中，Codex 的原始碼有獨立的平行 tool 執行模組與相應的測試；Mastra 的近期版本會在單一 tool 的參數完整時就開始執行，不等整則回應結束，這只適合唯讀或可安全取消的 tool。確切參數名稱與行為請以官方文件為準。

## 24.6 Cancellation 與 timeout：停得下來，也收得乾淨

run 需要提早結束的理由很多：使用者關掉視窗、使用者按下停止（Claude Code 這類 coding agent 允許按 Esc 中斷）、使用者在 agent 還在跑時送出新訊息、超過整個 run 的時間上限、服務要部署而需要讓 worker 停下來（第 22 章）。這些情況在 runtime 裡都是同一件事：**cancellation**（取消），也就是要求一個進行中的工作盡快停止。而 **timeout**（逾時）是「時間到了自動觸發的取消」。兩者共用同一套收尾機制，差別只在 run 最後的 status。

asyncio 的取消有幾個必須理解的語意。對一個 task 呼叫 `cancel()`，並不會立刻停止它，而是在它下一次 `await` 的地方丟出 `CancelledError`。這個例外從 Python 3.8 起繼承自 `BaseException`，所以一般的 `except Exception` 攔不到它，這是刻意的設計：取消不應該被當成普通錯誤吞掉。`finally` 區塊會照常執行，適合放關閉連線之類的清理。`asyncio.timeout()`（3.11 新增）在時間到時取消內部的程式碼，並在邊界把取消轉成 `TimeoutError`。`asyncio.shield()` 則保護一段工作不被外層的取消波及：外層照樣收到 `CancelledError`，被保護的工作繼續跑完。下面的程式在同一個時間點取消三種 tool。

```python
from __future__ import annotations

import asyncio
import selectors


class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


log: list[str] = []


def note(msg: str) -> None:
    log.append(f"{asyncio.get_running_loop().time():4.1f}s {msg}")


async def polite_tool():                                # 正確：清理放 finally，CancelledError 照常往外傳
    try:
        note("polite 開始查詢")
        await asyncio.sleep(5)
    finally:
        note("polite 收到取消，關閉連線")


async def greedy_tool():                                # 錯誤：吞掉取消，假裝沒事繼續做
    for i in range(3):
        try:
            await asyncio.sleep(1)
        except BaseException:                           # 裸 except 或 except BaseException 會攔到 CancelledError
            note(f"greedy 吞掉了取消（第 {i + 1} 輪）")
    note("greedy 跑完了：取消完全沒有生效")


async def charge(order: str):                           # 有副作用：扣款不能被砍到一半
    await asyncio.sleep(1.5)
    note(f"charge {order} 完成扣款")
    return "RF-001"


async def main():
    loop = asyncio.get_running_loop()
    polite, greedy = asyncio.create_task(polite_tool()), asyncio.create_task(greedy_tool())
    effect = asyncio.ensure_future(charge("B-2001"))
    shielded = asyncio.create_task(asyncio.wait_for(asyncio.shield(effect), 10))
    await asyncio.sleep(0.5)
    note("使用者取消：對三個 task 呼叫 cancel()")
    for t in (polite, greedy, shielded):
        t.cancel()
    results = await asyncio.gather(polite, greedy, shielded, return_exceptions=True)
    note(f"gather 回來：{[type(r).__name__ if isinstance(r, BaseException) else r for r in results]}")
    note(f"被 shield 保護的扣款：{'完成，結果 ' + effect.result() if effect.done() else '仍在進行'}")
    await effect                                        # 收尾：等副作用真正結束，才能如實回填
    deadline, tool_timeout = loop.time() + 1.2, 5.0     # 截止時間往下傳：子呼叫只能用剩下的時間
    note(f"剩餘時間 {deadline - loop.time():.1f}s → 這次 tool 的 timeout = {min(tool_timeout, deadline - loop.time()):.1f}s")
    print("\n".join(log))
    assert isinstance(results[0], asyncio.CancelledError) and results[1] is None
    assert effect.result() == "RF-001"


with asyncio.Runner(loop_factory=VirtualTimeLoop) as runner:
    runner.run(main())
```

```text
 0.0s polite 開始查詢
 0.5s 使用者取消：對三個 task 呼叫 cancel()
 0.5s polite 收到取消，關閉連線
 0.5s greedy 吞掉了取消（第 1 輪）
 1.5s charge B-2001 完成扣款
 2.5s greedy 跑完了：取消完全沒有生效
 2.5s gather 回來：['CancelledError', None, 'CancelledError']
 2.5s 被 shield 保護的扣款：完成，結果 RF-001
 2.5s 剩餘時間 1.2s → 這次 tool 的 timeout = 1.2s
```

第一行，三個 task 同時開始。0.5 秒時使用者取消，對三個 task 呼叫 `cancel()`。`polite_tool` 在 `await asyncio.sleep(5)` 的位置收到取消，`finally` 立刻執行，關閉連線，然後 `CancelledError` 照常往外傳，這是正確的寫法。`greedy_tool` 用 `except BaseException` 吞掉了取消，繼續跑完剩下的兩輪，一直到 2.5 秒才結束，而且回傳值是 `None`，呼叫端完全不知道它被要求停止過；更糟的是 `gather` 要等它，所以整批取消被拖慢了兩秒。實務上，裸的 `except:`、`except BaseException`，以及「捕捉 `CancelledError` 之後不重新丟出」，都是讓取消失效的常見原因。第三個 task 是被 shield 保護的扣款：外層 task 被取消（gather 的結果是 `CancelledError`），但扣款本身在 1.5 秒完成，結果 RF-001 拿得回來。最後一行示範**截止時間傳遞**（deadline propagation）：子呼叫的 timeout 是「自己的上限」與「整個 run 剩下的時間」取小，這和 gRPC 把 deadline 往下游傳的做法是同一個想法，避免外層只剩 1 秒時，內層還在等一個 5 秒的 timeout。

取消的訊號只是開始，真正的工作是**收尾**（settle）：run 不論怎麼結束，Session 都要停在一個可以續跑的狀態。這就是第 4 章配對不變式在 async 世界的版本。`loom.runtime` 的 `_settle` 對目前這一步的每個 tool call 做一次判斷，結果是下面這個狀態機的某個終態。

```text
                   ┌── loop guard 攔下 ──────────────────────────────► error（不執行，回填提醒）
 requested ────────┤
   │               └── 取得 semaphore ──► running ─┬─ 成功 ──────────► ok
   │                                               ├─ 例外 ──────────► error
   │                                               ├─ 唯讀 tool 逾時 ─► timeout
   │                                               ├─ 副作用 tool 逾時 ► unknown（可能已生效）
   │                                               └─ run 被取消或到期
   │                                                    ├─ 唯讀：立即中止 ───────► cancelled
   │                                                    └─ 副作用：寬限期內完成 ─► ok（如實記錄）
   │                                                               寬限期到了 ──► unknown
   └── run 被取消時還沒開始 ─────────────────────────────────────────► cancelled（尚未執行）

 每個 requested 的 call 恰好落在一個終態，並產生一個 tool_finished 與一個 tool_result
```

這張狀態機從左邊的 requested（模型提出了這個 call）開始。被 loop guard 攔下的 call 直接落到 error，內容是給模型的提醒。其他 call 要先取得 semaphore 才進入 running；還在排隊時 run 就被取消，落到 cancelled，內容註明「尚未開始執行」。running 的 call 有成功、例外、逾時、run 被取消四類出路。逾時要依副作用分級分開處理：唯讀 tool 逾時就是 timeout，模型可以稍後再查；有副作用的 tool 逾時則是 **unknown**（結果未知），因為請求可能已經送到對方，對方可能已經處理完，只是回應還沒回來。

run 被取消時，唯讀 tool 立刻中止，沒有損失；有副作用的 tool 則不能砍。在本機取消一個 coroutine，並不會撤回已經送到金流閘道的請求，對方可能照樣完成退款；如果我們在這時候直接記一筆「已取消」，紀錄就和事實不符，這正是 Maya 在雙 11 之後找到的那筆退款。所以 `loom.runtime` 用 `shield` 包住副作用 tool，取消時給它一段**寬限期**（cancel grace）：在寬限期內完成，就如實記錄成 ok，並註明「run 結束前已完成」；寬限期到了還沒回來，就記成 unknown，內容寫明「不要重試，請轉真人查證」。這和第 5 章的規則一致：結果未知是一個獨立的類別，不能被當成失敗而自動重試，而是要用 idempotency key 向對方查詢或由人處理。

| 層級 | 青鳥客服的例子 | 到期之後 | 數值怎麼定 |
|---|---|---|---|
| 單次 tool call | get_shipment 2 秒 | 唯讀：timeout 回填；副作用：unknown | 依下游 p99 延遲，再留一點餘裕 |
| 單次 model call | 10 秒；串流另設閒置逾時 | 視為可重試的錯誤（24.7 節） | 依 TTFT 分布與預期輸出長度 |
| run deadline | 同步客服 60 秒；CI coding agent 數十分鐘 | 取消並收尾，status=timeout | 依產品的互動模式 |
| 取消寬限期 | 2 秒 | 仍未完成的副作用記為 unknown | 依副作用 API 的 p99 延遲 |
| 部署停機 | worker 停止前等待 | 交給第 22 章的 durable 機制續跑 | 依最長的單步時間 |

這五層各自回答不同的問題，不能互相取代：單次 timeout 防的是「某一個依賴卡住」，run deadline 防的是「整體太久」，寬限期防的是「為了停得快而說謊」。數值要從自己的延遲分布反推，而且內層要服從外層的剩餘時間。

還有一種結束方式不是取消：process 直接 crash，`_settle` 沒有機會執行，Session 裡留下沒有 `run_finished` 的 run。runtime 在同一個 Session 上開始新的 run 之前，要先檢查尾端並套用同一套規則補齊（唯讀記中止、副作用記 unknown 再對帳）；從中斷點重播而不重複呼叫模型，則是第 22 章 `loom.durable` 的工作。

> [!warning] 常見誤解
> 「取消成功，就代表那個動作沒有發生。」本機的取消只代表「我們不再等它」。對外的請求一旦送出，對方的處理就不受我們控制；唯一誠實的做法是等它一段寬限期，或者記成結果未知。另一個誤解是「取消就是 `task.cancel()`」：那一行只是訊號，真正的工作是收尾協定，讓每個 tool call 都有結果、讓 Session 可以續跑。

## 24.7 Retry 與指數退避：重試本身也是負載

模型 API 的暫時性錯誤是常態，不是例外：速率限制（429）、服務過載（503，部分供應商另有專用的狀態碼）、連線中斷、串流半途斷線、單次呼叫逾時。第 4 章說過，這類錯誤模型自己看不到，必須由呼叫模型的那一層處理。第 23、25 章把責任切得很清楚：**錯誤分類、熔斷、fallback、routing 屬於 `loom.models`（第 25 章）；同一個 Model 的重試與退避屬於 `loom.runtime`**。runtime 不判斷「這個 503 算不算 provider 壞了」，它只讀第 25 章 `ModelError` 的 `retryable` 屬性，決定要不要再試一次、要等多久。如果 Runner 拿到的 model 是第 25 章的 fallback chain，那麼 chain 內部負責換家，runtime 在 chain 的外面負責「整條 chain 都失敗時，等一下再試」。

| 錯誤（依第 25 章分類） | 例子 | runtime 重試？ | 怎麼等 | 備註 |
|---|---|---|---|---|
| `rate_limit` | 429 速率限制 | 是 | 至少等 `retry-after`，再加 jitter | 長期偏高要檢查自己的 TPM 配額 |
| `overloaded` | 503、過載 | 是 | 指數退避＋jitter | 持續發生交給熔斷與 fallback |
| `server`、`network` | 其他 5xx、斷線、串流中斷、單次逾時 | 是，有限次數 | 指數退避＋jitter | 串流已顯示的文字要清掉 |
| `quota` | 429 額度用盡 | 否 | — | 換家由 fallback 決定；通知帳務 |
| `auth` | 401、403 | 否 | — | 設定錯誤，立即告警 |
| `context_overflow`、`invalid_request` | 400 | 否 | — | 修請求：compaction 或修 bug |
| 不是錯誤：`refusal` | stop_reason 為 refusal | 否 | — | 交給產品政策，不重試、不換家 |

這張表把第 25 章的分類翻成 runtime 的動作。上面三列可以重試，下面四列重試只是浪費：額度用盡、金鑰錯誤、請求格式錯誤，再試一百次結果都一樣。最後一列特別要注意：拒答是一種停止原因（`stop_reason` 的第四種值），不是錯誤；runtime 把它彙總成 `model_response` 後以 status=refusal 結束 run，不執行任何 tool，交給產品層依政策回覆或轉真人。用重試或換家去「試試看會不會答」，等於用工程手段繞過安全機制。

可以重試的錯誤，怎麼等才對？**指數退避**（exponential backoff）是每失敗一次，等待時間加倍：0.5 秒、1 秒、2 秒、4 秒，並設上限。它解決了「立刻重試只會讓過載更嚴重」的問題，卻沒有解決雙 11 那晚的問題：數千個 session 在同一秒失敗，就會在同一個時間點一起醒來，再一起失敗，形成一波一波的同步尖峰，這叫 **thundering herd**（驚群效應）。解法是 **jitter**（隨機抖動）：讓每個 client 的等待時間帶一點隨機性，把同一波重試攤開。AWS 的 Marc Brooker 在〈Exponential Backoff And Jitter〉一文比較了幾種做法，其中 **full jitter** 是在 0 到「指數退避值」之間均勻取一個隨機數。如果伺服器在回應中給了 `retry-after`，就至少等那麼久。下面用離散事件模擬重演開賣瞬間：200 個 run 同時呼叫模型，供應商每 100 毫秒只接 40 個。

```python
from __future__ import annotations

import heapq
import random
from collections import Counter

CAPACITY = 40          # 供應商每 100 毫秒最多接 40 個請求，其餘回 429
CLIENTS = 200          # 雙十一開賣瞬間，200 個 agent run 同時呼叫模型
BASE, CAP, MAX_ATTEMPTS = 0.2, 5.0, 8


def no_jitter(attempt: int, rng: random.Random) -> float:
    return min(CAP, BASE * 2 ** (attempt - 1))


def full_jitter(attempt: int, rng: random.Random) -> float:
    return rng.uniform(0, min(CAP, BASE * 2 ** (attempt - 1)))


def simulate(delay_fn, seed: int = 42) -> dict:
    """離散事件模擬：不用真的等，也不用 asyncio，時間就是 heap 裡的數字。"""
    rng = random.Random(seed)
    heap = [(0.0, cid, 1) for cid in range(CLIENTS)]   # (送出時間, client, 第幾次嘗試)
    heapq.heapify(heap)
    per_bucket, arrivals = Counter(), Counter()        # 被服務的請求數、實際打到供應商的請求數
    requests, rejected, done_at, gave_up = 0, 0, 0.0, 0
    while heap:
        t, cid, attempt = heapq.heappop(heap)
        requests += 1
        bucket = int(t * 10)
        if attempt > 1:
            arrivals[bucket] += 1                       # 只算重試：看重試會不會自己形成新的尖峰
        if per_bucket[bucket] < CAPACITY:
            per_bucket[bucket] += 1
            done_at = max(done_at, t)
            continue
        rejected += 1
        if attempt == MAX_ATTEMPTS:
            gave_up += 1
            continue
        heapq.heappush(heap, (t + delay_fn(attempt, rng), cid, attempt + 1))
    return {"requests": requests, "rejected": rejected, "done_at": round(done_at, 2), "gave_up": gave_up,
            "peak": max(arrivals.values())}


for name, fn in [("固定指數退避（無 jitter）", no_jitter), ("指數退避＋full jitter", full_jitter)]:
    r = simulate(fn)
    pad = 26 - sum(2 if ord(ch) > 0x2E80 else 1 for ch in name)
    print(f"{name}{' ' * pad}請求 {r['requests']:>3}  被拒 {r['rejected']:>3}  重試尖峰（每 100ms） {r['peak']:>3}  "
          f"全部完成 {r['done_at']:>4}s")

r0, r1 = simulate(no_jitter), simulate(full_jitter)
assert r1["requests"] < r0["requests"] and r1["peak"] < r0["peak"] and r1["done_at"] < r0["done_at"]
assert r0["gave_up"] == r1["gave_up"] == 0

# 重試放大：三層各自「最多試 4 次」，最壞情況一個使用者動作打出 4 × 4 × 4 次請求
layers = {"HTTP client": 4, "loom.runtime": 4, "API gateway": 4}
worst = 1
for n in layers.values():
    worst *= n
print(f"三層各自重試 {list(layers.values())} → 最壞 {worst} 次請求；只在一層重試 → 最多 4 次")
assert worst == 64
```

```text
固定指數退避（無 jitter） 請求 600  被拒 400  重試尖峰（每 100ms） 160  全部完成  3.0s
指數退避＋full jitter     請求 515  被拒 315  重試尖峰（每 100ms） 105  全部完成 0.91s
三層各自重試 [4, 4, 4] → 最壞 64 次請求；只在一層重試 → 最多 4 次
```

這段程式沒有用 asyncio，因為它要模擬的是 200 個獨立的 client，用一個以時間排序的 heap 推進就夠了，這本身也是一種確定性測試的技巧。第一列是沒有 jitter 的固定指數退避：第一波 40 個成功，剩下 160 個在 0.2 秒同時重試，再成功 40 個，其餘 120 個在 0.6 秒同時重試……每一波只能消化 40 個，重試的尖峰高達每 100 毫秒 160 個，全部完成要到 3.0 秒，總共送出 600 個請求。第二列加上 full jitter：重試被攤開到每個時間窗裡，供應商的空檔被填滿，重試尖峰降到 105，總請求少了 85 個，全部完成只要 0.91 秒。jitter 不只是對供應商友善，對自己的使用者也更快。

最後一行是第二個教訓：**重試放大**（retry amplification）。HTTP client、`loom.runtime`、API gateway 三層如果各自「最多送 4 次」，最壞情況下一個使用者動作會打出 4 × 4 × 4 ＝ 64 個請求，而且這種放大只在供應商已經出問題的時候發生，等於在最糟的時間加倍施壓。原則是只在一層重試，並選擇資訊最多的那一層。runtime 知道整個 run 還剩多少時間、這次呼叫有沒有已經推給使用者的半段文字、這個使用者還在不在，所以重試放在 runtime，SDK 的內建重試關掉，gateway 只做速率限制不做重試。Google 的《Site Reliability Engineering》在處理過載的章節中還建議**重試預算**（retry budget）：重試請求占總請求的比例要有上限，超過就直接失敗，讓故障時的額外負載可以預期。

`loom.runtime` 的 `_call_model` 還多做了兩個判斷：等待會超過 run deadline 就不等了，直接以 error 結束，讓上層有時間轉真人；重試前已推出過 `model_delta`，`model_retry` 就帶 `discard_partial=True`，讓前端清掉半段文字。嘗試次數彙總進 `model_response` 的 `attempts` 欄位，第 29 章的 tracing 可以據此畫出重試率。

> [!note] 2026 現況
> 截至 2026 年 10 月，依官方 SDK 文件，OpenAI 與 Anthropic 的 Python SDK 預設都會對連線錯誤、429 與 5xx 等錯誤自動重試少數幾次（預設值與可調參數名稱請以官方文件為準），採用 `loom.runtime` 統一重試時，應在 adapter 建立 client 時把它關掉（第 25 章的 adapter 程式已這樣做）。Anthropic API 以 529 表示服務過載，並可能在串流進行中送出錯誤事件，所以串流中途的錯誤同樣要經過分類。OpenAI Agents SDK 在 v0.21 加入了 model call timeout 與 `agents.testing` 確定性測試工具。

## 24.8 Loop guard：在原地打轉之前踩煞車

第 4 章的 `loom` v0.1 用「同一個 (tool, 參數) 在整個 run 裡出現幾次」偵測重複呼叫，採兩段式：先提醒、再停止。這在客服的短對話裡夠用，但在更長的 trajectory 上有三個漏洞。第一是**乒乓**：模型在 A、B 兩個查詢之間來回切換，每個 key 的累計次數都不高，要很久才觸發。第二是**換參數的原地打轉**：模型用 `amy@example.com`、`Amy@example.com`、`amy@exmaple.com` 輪流搜尋，每次參數都不同，累計永遠是 1，但結果永遠是「查無訂單」。第三是**誤判**：coding agent 改完程式再跑一次測試是正確的行為，累計計數卻把它當成重複。

所以 `loom.runtime` 的 **loop guard**（迴圈防護）看兩種不同的訊號。一是**滑動視窗**：只看最近 N 次呼叫裡同一個 key 出現幾次，舊的重複會被遺忘，近期的乒乓會更早被發現。二是**沒有新資訊**：如果連續幾步的 tool 結果全都是之前看過的，代表這幾步沒有帶來任何進展，不論參數有沒有變。第三個技巧是**狀態感知的 key**：把環境的版本（例如工作目錄的檔案雜湊或 commit id）放進 key，狀態改變之後的同一個呼叫就不算重複。下面用四條 trajectory 比較這幾種偵測方式。

```python
from __future__ import annotations

import json
from collections import Counter


def key(name: str, args: dict, state: int | None = None) -> str:
    base = name + json.dumps(args, sort_keys=True, ensure_ascii=False)
    return base if state is None else f"{base}@v{state}"   # 把環境版本放進 key：狀態變了就不算重複


def whole_run(traj, limit=3):                           # loom v0.1 的作法：整個 run 內累計
    seen = Counter()
    for step, (name, args, _result, _state) in enumerate(traj, 1):
        seen[key(name, args)] += 1
        if seen[key(name, args)] > limit:
            return step


def sliding(traj, window=6, limit=2, state_aware=False):   # 只看最近 window 次呼叫
    recent = []
    for step, (name, args, _result, state) in enumerate(traj, 1):
        recent = (recent + [key(name, args, state if state_aware else None)])[-window:]
        if recent.count(recent[-1]) > limit:
            return step


def no_progress(traj, max_stale=3):                     # 結果連續幾步都是看過的：沒有新資訊
    seen, stale = set(), 0
    for step, (_name, _args, result, _state) in enumerate(traj, 1):
        stale = stale + 1 if result in seen else 0
        seen.add(result)
        if stale >= max_stale:
            return step


TRAJ = {
    "原地重查貨態": [("get_shipment", {"tracking": "TC-1"}, "查詢中", 0)] * 5,
    "乒乓查詢": [("get_order", {"id": "B-1"}, "已出貨", 0), ("get_shipment", {"tracking": "TC-1"}, "查詢中", 0)] * 4,
    "換參數沒進展": [("search_orders", {"email": e}, "查無訂單", 0)
                     for e in ["amy@example.com", "Amy@example.com", "amy@example.co", "amy @example.com", "amy@exmaple.com"]],
    "改程式再跑測試": [x for v in range(4) for x in [("edit_file", {"path": "cart.py", "patch": f"#{v}"}, f"已修改 v{v + 1}", v),
                                                ("run_tests", {}, f"{3 - v} failed", v + 1)]],
}

pad = lambda s, w: s + " " * (w - sum(2 if ord(c) > 0x2E80 else 1 for c in s))
print(pad("trajectory", 16) + "整個 run 計數  滑動視窗  視窗＋狀態版本  沒有新資訊")
hits = {}
for name, traj in TRAJ.items():
    hits[name] = [whole_run(traj), sliding(traj), sliding(traj, state_aware=True), no_progress(traj)]
    cells = [f"step {h}" if h else "-" for h in hits[name]]
    print(pad(name, 16) + "".join(pad(c, w) for c, w in zip(cells, (15, 10, 16, 10))))

assert hits["乒乓查詢"][0] == 7 and hits["乒乓查詢"][1] == 5            # 視窗比累計更早抓到乒乓
assert hits["換參數沒進展"][:3] == [None, None, None] and hits["換參數沒進展"][3] == 4
assert hits["改程式再跑測試"][1] is not None and hits["改程式再跑測試"][2] is None   # 狀態版本避免誤判
```

```text
trajectory      整個 run 計數  滑動視窗  視窗＋狀態版本  沒有新資訊
原地重查貨態    step 4         step 3    step 3          step 4    
乒乓查詢        step 7         step 5    step 5          step 5    
換參數沒進展    -              -         -               step 4    
改程式再跑測試  step 8         step 6    -               -         
```

表格的每一列是一條 trajectory，每一欄是一種偵測方式，格子裡是第一次觸發的步數。「原地重查貨態」是最簡單的情況，四種都抓得到，滑動視窗最早（第 3 步）。「乒乓查詢」中，整個 run 計數要到第 7 步才觸發，滑動視窗在第 5 步，沒有新資訊也在第 5 步。「換參數沒進展」是前三種完全抓不到的情況，因為每次參數都不同，只有「沒有新資訊」在第 4 步發現：連續三步都是「查無訂單」。「改程式再跑測試」則是誤判測試：每次修改後測試結果都在改善，這是正常的工作節奏；整個 run 計數在第 8 步、滑動視窗在第 6 步把它當成迴圈，加上狀態版本之後才正確地不觸發，而「沒有新資訊」也不會觸發，因為每次測試結果都不同。

所以 loop guard 要組合使用，而且每種訊號都有代價：滑動視窗太小會漏掉長週期的循環；「沒有新資訊」要求結果可比較，帶時間戳記的回傳要先去掉這類欄位；狀態感知的 key 需要 tool 提供狀態版本，對外部 API 往往做不到。

| 訊號 | 抓得到 | 抓不到 | 可能誤判 | 觸發後 |
|---|---|---|---|---|
| 整個 run 累計（v0.1） | 連續重複 | 乒乓（很晚）、換參數 | 狀態改變後的合理重複 | 先提醒，再 status=loop |
| 滑動視窗 | 連續重複、近期乒乓 | 換參數、長週期循環 | 同上 | 同上 |
| 狀態感知的 key | 同滑動視窗，且不誤判 | 換參數 | 少；需要 tool 提供狀態版本 | 同上 |
| 沒有新資訊 | 換參數的原地打轉、乒乓 | 結果有雜訊（時間戳記） | 慢速輪詢的長任務 | 寫 `guardrail_tripped`，status=loop |
| 預算（步數、token、時間、tool 次數） | 所有形式的失控 | 不區分原因 | 長而合理的任務 | 依預算類型結束 |

在 runtime 裡，loop guard 有兩個位置。執行前的 `inspect()` 檢查即將執行的 call，平行批次要在整批開始之前檢查，否則模型一次提出十個相同的查詢，會在被發現之前全部執行完（第 4 章 Q8）。執行後的 `no_progress()` 看這一步的結果。觸發時，`loom.runtime` 寫入一個 `guardrail_tripped` 核心事件（guardrail 名稱為 loop_guard），再以 status=loop 結束，所以 loop 的發生次數會出現在第 23 章的稽核與營運指標裡。token 預算則沿用第 23 章的 `BudgetMiddleware`，掛在 `wrap_model` 上，用 `StopRun` 結束 run，runtime 只負責保證收尾。最後要記得：loop guard 是保險絲，不是修法。status=loop 的比例上升時，通常要修的是 tool 的回傳訊息，例如讓物流查詢在狀態未更新時明說「建議 2 小時後再查」，第 34 章會把這類失敗納入 failure taxonomy。

## 24.9 Runtime 的測試策略：把時間變成參數

Iris 在雙 11 之後寫的第一批測試，暴露了 runtime 測試的根本困難：結果取決於時間。CI 機器忙的時候，一個 2 秒的 timeout 可能在 1.9 秒的工作上觸發，也可能沒有。runtime 的非確定性有五個來源：時間、排程順序、隨機數、模型輸出、外部系統的失敗。確定性測試的原則就是**把每一個來源都變成可以注入的參數**：ScriptedModel、帶劇本延遲與故障的假後端、固定 seed，以及虛擬時鐘。

本章程式開頭的 `VirtualTimeLoop` 只有二十幾行。asyncio 的 event loop 用 `loop.time()` 取得目前時間，所有的 `sleep`、`timeout`、`call_later` 都轉成「在某個時間點喚醒」的計時器；沒有任何工作可做時，event loop 呼叫 selector 的 `select(timeout)`，真的等到下一個計時器到期。`VirtualTimeLoop` 覆寫了這兩個地方：`time()` 回傳一個自己維護的數字，`select()` 在沒有 I/O 時不等待，而是直接把這個數字加上 timeout，等於「把時鐘撥到下一個計時器」。結果是所有 asyncio 的時間語意照常成立，一個要跑 30 秒的情境在幾毫秒內跑完，而且每次的時間都一模一樣。如果所有 task 都在等待、卻沒有任何計時器會喚醒它們，它直接丟出「死結」，不會讓測試永遠掛著。它的限制也要知道：只有經過 event loop 計時器的等待才會被虛擬化，真的 socket、thread 裡的 `time.sleep` 都不受控制，所以測試裡的假後端一律用 `asyncio.sleep` 模擬延遲。

有了可控的時間，測試就可以從「跑幾個範例」升級成系統化的探索。

| 注入點 | 故障 | 期望的行為 | 要檢查的不變式 |
|---|---|---|---|
| 模型 | 429（帶 retry-after）、過載、串流斷線、單次逾時 | 退避重試，成功後彙總成一個 model_response | attempts 正確；半段文字被標記清除 |
| 模型 | 400、額度用盡、持續過載 | 不重試或重試用盡，status=error | run_finished 恰好一次 |
| 模型 | 拒答 | 不執行 tool，status=refusal | 沒有 tool_result |
| tool | 例外、逾時、卡住 | 回填 error 或 timeout，其他 call 不受影響 | 配對完整、依 call 順序 |
| tool（副作用） | 逾時、取消時進行中 | 寬限期內如實記錄，否則 unknown | 副作用不重複；unknown 不重試 |
| 控制 | 在任意時間點取消、run deadline | 收尾後結束，status=cancelled 或 timeout | 每個 call 恰好一個 tool_finished |
| 消費者 | 慢速、中途離開 | 背壓或合併；離開即取消 | 內容不少不亂；佇列有上限 |

這張 **fault injection**（故障注入，刻意在指定位置製造失敗）矩陣的最後一欄最重要：測試斷言的不是「輸出的文字長什麼樣」，而是**不論怎麼失敗都必須成立的性質**。這些不變式包括：核心事件的序號連續、`run_started` 與 `run_finished` 恰好各一個且在頭尾、每個 tool call 恰好一個 `tool_result` 且依 call 順序、每個 tool call 恰好一個 `tool_finished`、串流序號連續。只要不變式寫好，新增一種故障只需要在矩陣加一列。

不變式的另一個威力是可以和**時間點掃描**結合：不是挑幾個時間點取消，而是從 0 秒到 run 結束，每 0.1 秒取消一次，每次都檢查不變式。競態條件（race condition）通常只在很窄的時間窗裡出現，人工挑的測試點很容易剛好錯過。FoundationDB 公開說明過的 deterministic simulation testing 是這個想法的極致：整個分散式系統在單一執行緒的模擬環境裡跑，時間、網路、磁碟故障全部由 seed 決定，失敗可以一字不差地重現。下面用一個縮小版的 runtime 示範時間點掃描能找到什麼。

```python
from __future__ import annotations

import asyncio
import selectors
import time


class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


async def toy_run(cancel_at: float, settle: bool) -> list[dict]:
    """縮小版的 runtime：一次模型呼叫要求兩個 tool，再一次模型呼叫回答。"""
    messages: list[dict] = []

    async def body():
        await asyncio.sleep(0.4)                                    # 模型想了 0.4 秒
        messages.append({"role": "assistant", "tool_calls": [{"id": "c1"}, {"id": "c2"}]})
        results: dict[str, str] = {}

        async def tool(cid: str, latency: float):
            await asyncio.sleep(latency)
            results[cid] = "ok"

        try:
            await asyncio.gather(tool("c1", 0.3), tool("c2", 0.8))
        except asyncio.CancelledError:
            if settle:                                              # 修正版：取消時補齊每個 call 的結果
                messages.extend({"role": "tool", "tool_call_id": c, "content": results.get(c, "已取消")}
                                for c in ("c1", "c2"))
            raise
        messages.extend({"role": "tool", "tool_call_id": c, "content": results[c]} for c in ("c1", "c2"))
        await asyncio.sleep(0.4)
        messages.append({"role": "assistant", "tool_calls": []})

    task = asyncio.create_task(body())
    asyncio.get_running_loop().call_later(cancel_at, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        pass
    return messages


def paired(messages: list[dict]) -> bool:
    asked = [tc["id"] for m in messages if m["role"] == "assistant" for tc in m["tool_calls"]]
    return asked == [m["tool_call_id"] for m in messages if m["role"] == "tool"]


async def sweep(settle: bool) -> list[float]:
    """把取消時間點從 0.0 掃到 2.0 秒，每 0.1 秒一次：找出所有會破壞不變式的時間窗。"""
    bad = []
    for i in range(21):
        if not paired(await toy_run(i / 10, settle)):
            bad.append(i / 10)
    return bad


async def main():
    wall = time.perf_counter()
    naive, fixed = await sweep(settle=False), await sweep(settle=True)
    print(f"天真版：21 個取消時間點中 {len(naive)} 個破壞配對，落在 {naive[0]}s～{naive[-1]}s")
    print(f"修正版：21 個取消時間點中 {len(fixed)} 個破壞配對")
    elapsed = time.perf_counter() - wall
    print(f"42 次 run 共經過虛擬時間 {asyncio.get_running_loop().time():.1f} 秒；真實耗時不到 0.5 秒：{elapsed < 0.5}")
    assert naive == [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2] and fixed == []


with asyncio.Runner(loop_factory=VirtualTimeLoop) as runner:
    runner.run(main())
```

```text
天真版：21 個取消時間點中 8 個破壞配對，落在 0.5s～1.2s
修正版：21 個取消時間點中 0 個破壞配對
42 次 run 共經過虛擬時間 40.0 秒；真實耗時不到 0.5 秒：True
```

天真版在取消時直接讓 `CancelledError` 往外傳，沒有補齊結果；修正版在 `except CancelledError` 裡為每個 call 補上結果（已完成的用真實結果，沒完成的記「已取消」）後再重新丟出。掃描結果顯示，天真版在 21 個時間點中有 8 個破壞配對，全部落在 0.5 到 1.2 秒之間，也就是「模型已經提出 tool call、tool 還沒全部完成」的那段時間窗；在這段時間之外取消，天真版看起來完全正常。這正是 Iris 的 hotfix 沒在手動測試中被發現的原因：當時測的是「剛送出訊息就關掉」與「回答完才關掉」，剛好都在安全的時間窗裡。最後一行說明虛擬時間的效益：42 次 run 共經過 40 秒的 agent 時間，真實耗時不到 0.5 秒，這種測試可以放進每一次 commit 的 CI。

```text
              ┌──────────────────────────────┐
              │ 真實供應商的契約測試           │  少量、每晚：驗證 adapter 與真實的錯誤格式、串流事件（第 25 章）
              ├──────────────────────────────┤
              │ staging 故障演練               │  注入延遲、429、kill worker：看告警、收尾與 durable 續跑
          ┌───┴──────────────────────────────┴───┐
          │ runtime 情境測試（虛擬時間）          │  劇本模型＋假後端＋fault 矩陣＋時間點掃描＋golden 事件序列
      ┌───┴──────────────────────────────────────┴───┐
      │ 純函式單元測試                                │  RetryPolicy、LoopGuard、事件契約檢查器、配對檢查
      └───────────────────────────────────────────────┘
       越往下越快、越多、越確定；越往上越接近真實、越少、越貴
```

這張測試金字塔由下往上讀。最底層是不需要 event loop 的純函式，數量最多。第二層是本章的重點：在虛擬時間上跑完整的 runtime，斷言不變式，並用 **golden 事件序列**（把重要情境的核心事件類型序列存成快照，改動時比對差異）鎖住第 23 章的 Runner 契約；快照只存事件類型與 status，不存模型文字，否則每次調整措辭都要更新。第三層的 staging 故障演練驗證虛擬環境模擬不到的東西：真的網路、真的 worker 被 kill、告警有沒有響。最上層對真實供應商的契約測試確認第 25 章的 adapter 與真實世界一致，它本來就不穩定，所以不放在每次 commit 的關卡裡。

## 24.10 動手做：loom.runtime

這一節把前面所有機制組成 `loom.runtime`，實作第 23 章的 Runner 契約。程式分成五塊：全書統一的 ScriptedModel 與 `VirtualTimeLoop`；第 25 章 adapter 的最小替身 `StreamingScriptedModel`，以 `text_delta` 與 `stop` 串流回應，劇本步驟可以是 `fail(ModelError(...))`（直接失敗）或 `Cut(...)`（吐出一段文字後斷線）；第 23 章 `loom.core` 的最小子集（Handoff、Guardrail 宣告與參數驗證省略，處理方式與參考 Runner 相同）；`loom.runtime` 本體；以及青鳥的假後端與四組情境。

四組情境分別是：A，同時查兩張訂單，其中一個物流商卡住，觀察兩層事件的順序，並和 `max_parallel=1` 比較總時間；B，退款進行中使用者關掉視窗，而且退款 API 卡住，觀察「結果未知」，再等十秒看那筆退款最後怎麼了；C，fault injection 矩陣，十三種情境（含無故障的基準）都檢查同一組不變式；D，取消時間點掃描，從 0 到 4 秒每 0.1 秒取消一次。所有延遲都跑在虛擬時間上，整段程式真實耗時不到一秒。

```python
from __future__ import annotations

import asyncio
import json
import random
import selectors
from collections import Counter
from dataclasses import dataclass, field, make_dataclass
from typing import Any, Callable, ClassVar


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens｜refusal
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


def calls(text: str, *specs: tuple[str, str, dict]) -> ModelResponse:
    """劇本小工具：一則回應裡同時要求多個 tool（parallel tool calls）。"""
    return ModelResponse(text=text, tool_calls=[ToolCall(i, n, a) for i, n, a in specs], stop_reason="tool_use")


# ───────────── 測試基礎設施：虛擬時間 event loop（24.9 節）─────────────
class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout                   # 沒事可做：直接把時鐘撥到下一個計時器
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    """asyncio.sleep、timeout 全部照常運作，但時間是假的：一秒不用等，結果完全可重現。"""

    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


# ───────────── 模型端：第 25 章 adapter 的最小替身（可串流、可注入故障）─────────────
@dataclass
class ModelError(Exception):
    kind: str                                          # 分類由 loom.models 負責（第 25 章）
    provider: str = "scripted"
    status: int = 0
    retry_after: float = 0.0

    @property
    def retryable(self) -> bool:
        return self.kind in {"rate_limit", "overloaded", "server", "network"}


@dataclass
class Cut:
    text: str                                          # 劇本步驟：吐出一段文字後斷線


def fail(err: ModelError) -> Callable[[list[dict]], ModelResponse]:
    def step(messages: list[dict]) -> ModelResponse:
        raise err                                      # 劇本步驟：這一次模型呼叫直接失敗
    return step


class StreamingScriptedModel(ScriptedModel):
    def __init__(self, script, ttft: float = 0.4, chunk_delay: float = 0.05, chunk: int = 8):
        super().__init__(script)
        self.ttft, self.chunk_delay, self.chunk = ttft, chunk_delay, chunk

    async def stream(self, messages, tools=None, system=""):
        """統一的串流事件：text_delta 若干個，最後一個 stop 帶著組裝好的 ModelResponse。"""
        await asyncio.sleep(self.ttft)
        resp = self.complete(messages, tools, system)  # 劇本步驟若是 fail(...)，這裡就丟出 ModelError
        if isinstance(resp, Cut):
            yield "text_delta", resp.text
            raise ModelError("network")                # 串流中途斷線
        for i in range(0, len(resp.text), self.chunk):
            await asyncio.sleep(self.chunk_delay)
            yield "text_delta", resp.text[i:i + self.chunk]
        resp.usage = {"input_tokens": len(json.dumps(messages, ensure_ascii=False)) // 2, "output_tokens": 30}
        yield "stop", resp


# ───────────── loom.core 的最小子集（第 23 章）：宣告、核心事件、Session、middleware ─────────────
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]                             # async def fn(deps, **args)
    effect: str = "destructive"                        # 未標註一律當 destructive（第 5 章）
    timeout: float | None = None

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass(frozen=True)
class Agent:
    name: str
    instructions: str
    tools: tuple[Tool, ...] = ()
    max_steps: int = 8                                 # handoffs、guardrails 欄位與第 23 章相同，這裡省略


@dataclass(frozen=True)
class Event:                                           # 核心事件：寫進 Session，是唯一的事實來源
    seq: int
    type: str
    agent: str
    data: dict[str, Any]
    v: int = 1


class InMemorySession:
    def __init__(self, session_id: str):
        self.id, self._events = session_id, []

    def load(self) -> list[Event]:
        return list(self._events)

    def append(self, event: Event) -> None:
        self._events.append(event)


def to_messages(events: list[Event]) -> list[dict]:
    out: list[dict] = []
    for e in events:
        if e.type == "user_message":
            out.append({"role": "user", "content": e.data["text"]})
        elif e.type == "model_response":
            out.append({"role": "assistant", "content": e.data["text"], "tool_calls": e.data["tool_calls"]})
        elif e.type == "tool_result":
            out.append({"role": "tool", "tool_call_id": e.data["id"], "name": e.data["name"],
                        "content": e.data["content"], "is_error": e.data["is_error"]})
    return out


class StopRun(Exception):
    def __init__(self, status: str, output: str):
        super().__init__(status)
        self.status, self.output = status, output


class Middleware:
    """四個擴充點的 async 版：簽名與第 23 章相同，wrap_* 與 nxt 變成 coroutine。"""

    async def before_run(self, ctx, user_input: str) -> None: ...
    def on_event(self, ctx, event: Event) -> None: ...

    async def wrap_model(self, ctx, req: dict, nxt):
        return await nxt(req)

    async def wrap_tool(self, ctx, tc: ToolCall, nxt):
        return await nxt(tc)


@dataclass
class RunResult:
    status: str                                        # done｜max_steps｜max_tokens｜refusal｜budget｜blocked
    output: str                                        # ＋ runtime 新增：loop｜cancelled｜timeout｜error
    last_agent: Agent
    usage: dict[str, int]
    events: list[Event]


# ───────────────────────────── loom.runtime ─────────────────────────────
@dataclass
class StreamEvent:                                     # 串流事件：給 UI／呼叫端即時消費，不持久化
    run_id: str
    n: int                                             # 串流內的序號：重連時用來去重與續傳
    t: float                                           # run 開始後經過的秒數
    type: ClassVar[str] = "stream"


def stream_type(name: str, fields: str) -> type:
    """產生一個 typed 串流事件類別：欄位固定，可以用 isinstance 或 match 分辨。"""
    return make_dataclass(name.title().replace("_", ""), [(f, Any) for f in fields.split()],
                          bases=(StreamEvent,), namespace={"type": name})


ModelDelta = stream_type("model_delta", "step text")
ModelRetry = stream_type("model_retry", "step attempt delay reason discard_partial")   # discard_partial：清掉半段文字
ToolStarted = stream_type("tool_started", "call_id name")
ToolFinished = stream_type("tool_finished", "call_id name status content")   # ok｜error｜timeout｜cancelled｜unknown
RunCancelling = stream_type("run_cancelling", "reason")
Committed = stream_type("committed", "event")         # 一個核心事件已寫進 Session


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base: float = 0.5
    cap: float = 8.0
    seed: int = 7

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)            # 固定 seed：jitter 也能重現

    def delay(self, attempt: int, retry_after: float = 0.0) -> float:
        backoff = self.rng.uniform(0, min(self.cap, self.base * 2 ** (attempt - 1)))   # full jitter
        return round(max(backoff, retry_after), 2)     # 伺服器說要等多久，就至少等那麼久


class LoopGuard:
    """兩種訊號：滑動視窗內的重複呼叫（含 A-B-A-B 乒乓），以及連續幾步都沒有新資訊（24.8 節）。"""

    def __init__(self, window: int = 6, max_repeats: int = 2, max_stale_steps: int = 3):
        self.window, self.max_repeats, self.max_stale_steps = window, max_repeats, max_stale_steps
        self.recent: list[str] = []
        self.seen: set[str] = set()
        self.stale = 0

    def inspect(self, tc: ToolCall) -> str:
        self.recent = (self.recent + [tc.name + json.dumps(tc.args, sort_keys=True)])[-self.window:]
        n = self.recent.count(self.recent[-1])
        return "stop" if n > self.max_repeats + 1 else "warn" if n > self.max_repeats else "ok"

    def no_progress(self, results: list[str]) -> bool:
        self.stale = self.stale + 1 if all(r in self.seen for r in results) else 0
        self.seen.update(results)
        return self.stale >= self.max_stale_steps


class Runner:
    """實作第 23 章的 Runner 契約：同樣的 Agent、輸入與劇本，核心事件序列與同步參考版相同。"""

    def __init__(self, model, middleware: list[Middleware] = (), *, max_parallel: int = 4,
                 tool_timeout: float = 2.0, model_timeout: float = 10.0, run_timeout: float = 60.0,
                 cancel_grace: float = 2.0, retry: RetryPolicy | None = None):
        self.model, self.middleware = model, list(middleware)
        self.max_parallel, self.tool_timeout, self.model_timeout = max_parallel, tool_timeout, model_timeout
        self.run_timeout, self.cancel_grace = run_timeout, cancel_grace
        self.retry = retry or RetryPolicy()

    def start(self, agent: Agent, user_input: str, session: InMemorySession, deps: dict | None = None) -> "Run":
        return Run(self, agent, user_input, session, dict(deps or {}))

    async def run(self, agent, user_input, session, deps=None) -> RunResult:
        run = self.start(agent, user_input, session, deps)
        async for _ in run.stream():
            pass
        return run.result


class Run:
    def __init__(self, runner: Runner, agent: Agent, user_input: str, session: InMemorySession, deps: dict):
        self.runner, self.agent, self.input, self.session, self.deps = runner, agent, user_input, session, deps
        self.start_seq = len(session.load())
        self.id = f"{session.id}#{self.start_seq}"
        # 第 25 章的四個互不重疊的桶：預算與帳單都加總這四個，reasoning_tokens 只供參考
        self.usage = dict.fromkeys(("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens"), 0)
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=64)   # 有上限：慢速消費者會形成背壓（24.4 節）
        self.n, self.detached, self.result = 0, False, None
        self.step_calls: list[ToolCall] = []
        self.results: dict[str, tuple[str, str]] = {}           # call id → (status, content)
        self.persisted: set[str] = set()
        self.started: set[str] = set()
        self.inflight_effects: dict[str, asyncio.Future] = {}
        self.sem = asyncio.Semaphore(runner.max_parallel)
        self.loop = asyncio.get_running_loop()
        self.t0 = self.loop.time()
        self.task = self.loop.create_task(self._drive())

    def cancel(self) -> None:
        self.task.cancel()

    async def stream(self):
        try:
            while True:
                item = await self.queue.get()
                yield item
                if isinstance(item, Committed) and item.event.type == "run_finished":
                    return
        finally:
            if not self.task.done():                     # 消費者離開（關掉視窗）＝取消這次 run
                self.detached = True
                self.cancel()

    async def _push(self, cls, **data) -> None:
        self.n += 1
        item = cls(self.id, self.n, round(self.loop.time() - self.t0, 2), **data)
        if not self.detached:
            await self.queue.put(item)

    async def commit(self, type_: str, **data) -> Event:
        ev = Event(len(self.session.load()), type_, self.agent.name, data)
        self.session.append(ev)                          # 先落地，再通知 middleware，最後才推給串流
        for mw in self.runner.middleware:
            mw.on_event(self, ev)
        await self._push(Committed, event=ev)
        return ev

    async def _drive(self) -> None:
        await self.commit("run_started", agent=self.agent.name)
        deadline = self.loop.time() + self.runner.run_timeout
        try:
            async with asyncio.timeout_at(deadline):
                for mw in self.runner.middleware:
                    await mw.before_run(self, self.input)
                await self.commit("user_message", text=self.input)
                status, output = await self._loop(deadline)
        except TimeoutError:
            status, output = "timeout", "處理時間超過上限，已轉給真人同事。"
            await self._push(RunCancelling, reason=f"超過 run_timeout={self.runner.run_timeout}s")
        except asyncio.CancelledError:
            self.task.uncancel()                           # 取消是預期中的結局：收尾後正常結束
            status, output = "cancelled", ""
            await self._push(RunCancelling, reason="使用者取消")
        except StopRun as stop:                            # middleware 結束 run（預算、攔截），語意同第 23 章
            status, output = stop.status, stop.output
        except Exception as exc:                           # 包含重試用盡的 ModelError；串流不能永遠等下去
            status, output = "error", f"{type(exc).__name__}: {exc}"
        await self._settle(status)
        await self.commit("run_finished", status=status, output=output)
        self.result = RunResult(status, output, self.agent, dict(self.usage),
                                self.session.load()[self.start_seq:])

    async def _loop(self, deadline: float) -> tuple[str, str]:
        guard, tools = LoopGuard(), {t.name: t for t in self.agent.tools}
        call_model = self._chain("wrap_model", lambda req: self._call_model(req, deadline))
        call_tool = self._chain("wrap_tool", self._dispatch)
        for step in range(1, self.agent.max_steps + 1):
            req = {"system": self.agent.instructions, "messages": to_messages(self.session.load()),
                   "tools": [t.schema() for t in tools.values()], "step": step}
            resp, attempts = await call_model(req)
            if resp.stop_reason in ("max_tokens", "refusal"):   # 半截的 tool call 不執行；拒答交給產品政策
                await self.commit("model_response", text=resp.text, tool_calls=[], usage=resp.usage, attempts=attempts)
                return resp.stop_reason, resp.text
            await self.commit("model_response", text=resp.text, tool_calls=[vars(tc) for tc in resp.tool_calls],
                              usage=resp.usage, attempts=attempts)
            if not resp.tool_calls:
                return "done", resp.text
            self.step_calls, self.results, self.persisted = resp.tool_calls, {}, set()
            verdicts = {tc.id: guard.inspect(tc) for tc in resp.tool_calls}
            await self._run_tools(tools, verdicts, call_tool)
            executed = [self.results[tc.id][1] for tc in self.step_calls if verdicts[tc.id] == "ok"]
            if "stop" in verdicts.values() or guard.no_progress(executed):
                kind = "提醒後仍重複相同呼叫" if "stop" in verdicts.values() else f"連續 {guard.stale} 步沒有新資訊"
                await self.commit("guardrail_tripped", guardrail="loop_guard", stage="tool", reason=kind)
                return "loop", "我卡在同一個步驟，已轉給真人同事。"
        return "max_steps", "步驟用完了，我先整理目前進度並轉給真人同事。"

    def _chain(self, method: str, terminal):
        fn = terminal                                      # 由內往外包：清單第一個 middleware 在最外層
        for mw in reversed(self.runner.middleware):
            fn = (lambda m, nxt: lambda x: getattr(m, method)(self, x, nxt))(mw, fn)
        return fn

    async def _call_model(self, req: dict, deadline: float) -> tuple[ModelResponse, int]:
        policy = self.runner.retry
        for attempt in range(1, policy.max_attempts + 1):
            streamed = False
            try:
                async with asyncio.timeout(self.runner.model_timeout):
                    async for kind, data in self.runner.model.stream(req["messages"], req["tools"], req["system"]):
                        if kind == "text_delta":
                            streamed = True
                            await self._push(ModelDelta, step=req["step"], text=data)
                        elif kind == "stop":
                            resp = data
            except (ModelError, TimeoutError) as exc:
                err = exc if isinstance(exc, ModelError) else ModelError("network")   # 單次呼叫逾時視同網路錯誤
                delay = policy.delay(attempt, err.retry_after)
                # 不可重試、次數用完，或等下去會超過整個 run 的 deadline：放棄，交給上層
                if not err.retryable or attempt == policy.max_attempts or self.loop.time() + delay > deadline:
                    raise
                await self._push(ModelRetry, step=req["step"], attempt=attempt, delay=delay,
                                 reason=err.kind, discard_partial=streamed)
                await asyncio.sleep(delay)
                continue
            for k in self.usage:
                self.usage[k] += resp.usage.get(k, 0)
            return resp, attempt
        raise AssertionError("unreachable")

    async def _run_tools(self, tools: dict[str, Tool], verdicts: dict[str, str], call_tool) -> None:
        # 連續的唯讀 tool 併成一組平行執行；有副作用的 tool 自成一組，依模型給的順序逐一執行
        is_read = lambda tc: tc.name not in tools or tools[tc.name].effect == "read"
        groups: list[list[ToolCall]] = []
        for tc in self.step_calls:
            if is_read(tc) and groups and is_read(groups[-1][0]):
                groups[-1].append(tc)
            else:
                groups.append([tc])
        for group in groups:
            try:
                async with asyncio.TaskGroup() as tg:
                    for tc in group:
                        tg.create_task(self._exec(tc, verdicts[tc.id], call_tool))
            except ExceptionGroup as eg:                   # TaskGroup 會把例外包成 ExceptionGroup
                stop = next((e for e in eg.exceptions if isinstance(e, StopRun)), None)
                if stop is None:
                    raise
                raise stop from None                       # wrap_tool 丟的 StopRun 要原樣交給 _drive，語意同第 23 章
            await self._persist(group)                     # 一組做完就落地，依 call 順序，不依完成順序

    async def _exec(self, tc: ToolCall, verdict: str, call_tool) -> None:
        if verdict != "ok":                                # loop guard 攔下：不執行，回填提醒
            status, content = "error", ("已停止：重複呼叫。" if verdict == "stop" else
                                        f"你最近已用相同參數呼叫 {tc.name} 多次，結果不會改變；請換做法或回覆使用者。")
        else:
            async with self.sem:                           # 平行上限：保護下游與 rate limit
                self.started.add(tc.id)
                await self._push(ToolStarted, call_id=tc.id, name=tc.name)
                status, content = await call_tool(tc)
        self.results[tc.id] = (status, content)
        await self._push(ToolFinished, call_id=tc.id, name=tc.name, status=status, content=content)

    async def _dispatch(self, tc: ToolCall) -> tuple[str, str]:
        tool = next((t for t in self.agent.tools if t.name == tc.name), None)
        if tool is None:                                   # 參數驗證與截斷同第 4、23 章，這裡省略
            return "error", f"沒有名為 {tc.name} 的工具。"
        timeout = tool.timeout or self.runner.tool_timeout
        if tool.effect == "read":
            try:
                async with asyncio.timeout(timeout):
                    out = await tool.fn(self.deps, **tc.args)
            except TimeoutError:
                return "timeout", f"{tc.name} 在 {timeout} 秒內沒有回應，可稍後再查或告知使用者。"
            except Exception as exc:
                return "error", f"{type(exc).__name__}: {exc}"
        else:
            # 有副作用的 tool 用 shield 包住：取消 run 不會把扣款砍到一半
            effect = self.inflight_effects[tc.id] = asyncio.ensure_future(tool.fn(self.deps, **tc.args))
            try:
                out = await asyncio.wait_for(asyncio.shield(effect), timeout)
            except TimeoutError:
                return "unknown", f"結果未知：{tc.name} 逾時，可能已生效。不要重試，請轉真人查證。"
            except Exception as exc:
                del self.inflight_effects[tc.id]
                return "error", f"{type(exc).__name__}: {exc}"
            del self.inflight_effects[tc.id]
        return "ok", out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)

    async def _persist(self, group: list[ToolCall]) -> None:
        for tc in group:
            if tc.id not in self.persisted:
                status, content = self.results[tc.id]
                self.persisted.add(tc.id)
                await self.commit("tool_result", id=tc.id, name=tc.name, is_error=status != "ok",
                                  content=content, status=status)   # status 是 v0.5 新增的欄位（只增不改）

    async def _settle(self, status: str) -> None:
        """不論 run 怎麼結束，這一步提出的每個 tool call 都要有 tool_result，Session 才能續跑。"""
        for tc in self.step_calls:
            if tc.id in self.results:
                continue
            effect = self.inflight_effects.pop(tc.id, None)
            if effect is not None:                         # 副作用進行中：給它一段寬限期
                done, _ = await asyncio.wait({effect}, timeout=self.runner.cancel_grace)
                if done and effect.exception() is None:
                    out = effect.result()
                    result = ("ok", (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))
                              + "（run 結束前已完成）")
                else:
                    result = ("unknown", f"結果未知：{tc.name} 在 run 結束時仍未完成。不要重試，請轉真人查證。")
            else:
                verb = "已取消" if status == "cancelled" else "已中止"
                # tool_result 的 status 只有 ok｜error｜timeout｜cancelled｜unknown：run 逾時記 timeout，其餘一律 cancelled
                result = ("timeout" if status == "timeout" else "cancelled", f"{verb}：{tc.name} {'執行到一半被中止' if tc.id in self.started else '尚未開始執行'}。")
            self.results[tc.id] = result
            await self._push(ToolFinished, call_id=tc.id, name=tc.name, status=result[0], content=result[1])
        await self._persist(self.step_calls)
        self.step_calls = []
# ───────────────────────────── loom.runtime 結束 ─────────────────────────────


# 青鳥的假後端：延遲用 asyncio.sleep 模擬，跑在虛擬時間上
LATENCY = {"B-1042": 0.8, "B-1077": 0.5, "B-5555": 30.0, "TC-88301": 0.6, "TC-90512": 30.0}
ORDERS = {"B-1042": "TC-88301", "B-1077": "TC-90512", "B-5555": "TC-00000"}
refunds: list[str] = []


async def get_order(deps, order_id: str) -> dict:
    await asyncio.sleep(LATENCY[order_id])
    return {"order_id": order_id, "status": "shipped", "tracking": ORDERS[order_id]}


async def get_shipment(deps, tracking: str) -> dict:
    await asyncio.sleep(LATENCY[tracking])                # TC-90512 的物流商卡住 30 秒
    return {"tracking": tracking, "eta": "明天"}


def make_refund(latency: float):
    async def refund(deps, order_id: str) -> dict:
        await asyncio.sleep(latency)
        refunds.append(order_id)
        return {"refund_id": f"RF-{len(refunds):03d}", "order_id": order_id}
    return refund


def obj(*names: str) -> dict:
    return {"type": "object", "properties": {n: {"type": "string"} for n in names}, "required": list(names)}


def cs_agent(refund_latency: float = 1.5) -> Agent:
    return Agent("cs", "你是青鳥客服。", tools=(
        Tool("get_order", "查訂單", obj("order_id"), get_order, effect="read"),
        Tool("get_shipment", "查貨態", obj("tracking"), get_shipment, effect="read"),
        Tool("refund", "未出貨訂單退款", obj("order_id"), make_refund(refund_latency), effect="destructive")))


class CountEvents(Middleware):
    def __init__(self):
        self.counts: Counter[str] = Counter()

    def on_event(self, ctx, event):                       # 只看得到核心事件，看不到 model_delta
        self.counts[event.type] += 1


def show(items: list) -> None:
    i = 0
    while i < len(items):
        it, j = items[i], i
        if isinstance(it, ModelDelta):                     # 連續的 delta 合併成一行顯示
            while j + 1 < len(items) and isinstance(items[j + 1], ModelDelta):
                j += 1
            line = f"  model_delta     ×{j - i + 1}「{''.join(x.text for x in items[i:j + 1])}」"
        elif isinstance(it, Committed):                    # ● 標記：已寫進 Session 的核心事件
            d = it.event.data
            detail = {"model_response": lambda: [c["id"] for c in d["tool_calls"]] or d["text"],
                      "tool_result": lambda: f"{d['id']} {d['status']}", "run_finished": lambda: d["status"],
                      "user_message": lambda: d["text"], "guardrail_tripped": lambda: d["reason"],
                      "run_started": lambda: d["agent"]}
            line = f"● {it.event.type:<15} {detail.get(it.event.type, lambda: '')()}"
        elif isinstance(it, ToolFinished):
            line = f"  tool_finished   {it.call_id} {it.name} [{it.status}] {it.content}"
        else:
            line = f"  {it.type:<15} " + " ".join(str(v) for k, v in vars(it).items() if k not in ("run_id", "n", "t", "step"))
        print(f"  {it.t:5.2f}s {line[:66]}")
        i = j + 1


def pad(text: str, width: int) -> str:
    return text + " " * (width - sum(2 if ord(ch) > 0x2E80 else 1 for ch in text))   # 中文字佔兩格


def invariants(events: list[Event], items: list) -> list[str]:
    """不論 run 怎麼結束都必須成立的性質；fault injection 測試就是逐一檢查它們。"""
    bad, types = [], [e.type for e in events]
    if [e.seq for e in events] != list(range(events[0].seq, events[0].seq + len(events))):
        bad.append("核心事件 seq 不連續")
    if types[0] != "run_started" or types[-1] != "run_finished" or types.count("run_finished") != 1:
        bad.append("run_started／run_finished 不是恰好各一個且在頭尾")
    asked = [c["id"] for e in events if e.type == "model_response" for c in e.data["tool_calls"]]
    if asked != [e.data["id"] for e in events if e.type == "tool_result"]:
        bad.append("tool_call 與 tool_result 沒有依序一一配對")
    if sorted(asked) != sorted(x.call_id for x in items if isinstance(x, ToolFinished)):
        bad.append("不是每個 tool_call 都恰好有一個 tool_finished")
    if [x.n for x in items] != list(range(1, len(items) + 1)):
        bad.append("串流序號不連續")
    return bad


async def run_once(agent, runner, text, cancel_at=None, quiet=False):
    run = runner.start(agent, text, InMemorySession("s-1"))
    if cancel_at is not None:
        run.loop.call_later(cancel_at, run.cancel)            # 模擬使用者在某個時間點關掉視窗
    items = [item async for item in run.stream()]
    if not quiet:
        show(items)
    assert invariants(run.result.events, items) == [], invariants(run.result.events, items)
    return run.result, items


async def main() -> None:
    two = lambda: [calls("好的，我同時查兩張訂單。", ("c1", "get_order", {"order_id": "B-1042"}),
                         ("c2", "get_order", {"order_id": "B-1077"})),
                   calls("", ("c3", "get_shipment", {"tracking": "TC-88301"}),
                         ("c4", "get_shipment", {"tracking": "TC-90512"})),
                   say("B-1042 明天到；B-1077 的物流商沒有回應，我晚點再幫您確認。")]
    print("── A 串流＋平行 tool calls＋部分失敗")
    counter = CountEvents()
    a, items = await run_once(cs_agent(), Runner(StreamingScriptedModel(two()), [counter]), "B-1042 和 B-1077 到哪了？")
    _, serial = await run_once(cs_agent(), Runner(StreamingScriptedModel(two()), max_parallel=1), "序列", quiet=True)
    print(f"  串流 {len(items)} 項、核心事件 {len(a.events)} 個；on_event 看到：{dict(counter.counts)}")
    print(f"  總時間：平行 {items[-1].t}s，序列（max_parallel=1）{serial[-1].t}s")
    assert [e.type for e in a.events] == ["run_started", "user_message", "model_response", "tool_result", "tool_result",
                                          "model_response", "tool_result", "tool_result", "model_response", "run_finished"]

    print("── B 退款進行中使用者離開，退款 API 卡住")
    script = [calls("我先退款，再查另一張。", ("c1", "refund", {"order_id": "B-2002"}),
                    ("c2", "get_order", {"order_id": "B-1042"})), say("（不會走到這裡）")]
    b, _ = await run_once(cs_agent(9.0), Runner(StreamingScriptedModel(script)), "退款", cancel_at=1.0)
    assert [e.data["status"] for e in b.events if e.type == "tool_result"] == ["unknown", "cancelled"]
    assert refunds == []
    await asyncio.sleep(10)                               # 再等 10 秒：那筆「結果未知」的退款其實還在跑
    print(f"  10 秒後的退款紀錄：{refunds}（標成「結果未知」的退款最後生效了）")
    assert refunds == ["B-2002"]

    print("── C fault injection 矩陣：每一種故障都檢查同一組不變式")
    base = lambda order="B-1042": [calls("", ("c1", "get_order", {"order_id": order}),
                                         ("c2", "refund", {"order_id": "B-3001"})), say("處理完成。")]
    pingpong = [calls("", (f"p{i}", "get_order", {"order_id": "B-1042"}) if i % 2 else
                      (f"p{i}", "get_shipment", {"tracking": "TC-88301"})) for i in range(1, 9)]
    matrix = [("無故障", base(), {}, None, 1.5),
              ("429 兩次", [fail(ModelError("rate_limit", retry_after=0.5))] * 2 + base(), {}, None, 1.5),
              ("模型持續過載", [fail(ModelError("overloaded", status=503))] * 4, {}, None, 1.5),
              ("請求格式錯誤", [fail(ModelError("invalid_request", status=400))], {}, None, 1.5),
              ("串流斷線", [Cut("處理")] + base(), {}, None, 1.5),
              ("拒答", [ModelResponse(text="這個問題我無法協助。", stop_reason="refusal")], {}, None, 1.5),
              ("tool 例外", base("B-9999"), {}, None, 1.5),
              ("tool 逾時", base("B-5555"), {}, None, 1.5),
              ("取消 @0.7s", base(), {}, 0.7, 1.5),
              ("取消 @1.5s", base(), {}, 1.5, 1.5),
              ("退款卡住＋取消", base(), {}, 1.5, 9.0),
              ("run 逾時 2s", base(), {"run_timeout": 2.0}, None, 1.5),
              ("乒乓查詢", pingpong, {}, None, 1.5)]
    for name, script, opts, cancel_at, refund_latency in matrix:
        r, items = await run_once(cs_agent(refund_latency), Runner(StreamingScriptedModel(script), **opts),
                                  name, cancel_at=cancel_at, quiet=True)
        retries = sum(isinstance(x, ModelRetry) for x in items)
        tool_status = " ".join(f"{e.data['id']}={e.data['status']}" for e in r.events if e.type == "tool_result")
        print(f"  {pad(name, 15)}{r.status:<10}重試 {retries}  {items[-1].t:5.2f}s  {tool_status[:34]:<35}OK")

    print("── D 取消時間點掃描：0.0～4.0 秒每 0.1 秒取消一次")
    outcomes: Counter[str] = Counter()
    for i in range(41):
        r, _ = await run_once(cs_agent(), Runner(StreamingScriptedModel(base())), "掃描", cancel_at=i / 10, quiet=True)
        tool_status = "/".join(e.data["status"] for e in r.events if e.type == "tool_result")
        outcomes[r.status + (f"（{tool_status}）" if tool_status else "")] += 1
    print("  41 次全部滿足不變式；結局分布：", dict(outcomes))


with asyncio.Runner(loop_factory=VirtualTimeLoop) as r:
    r.run(main())
```

```text
── A 串流＋平行 tool calls＋部分失敗
   0.00s ● run_started     cs
   0.00s ● user_message    B-1042 和 B-1077 到哪了？
   0.45s   model_delta     ×2「好的，我同時查兩張訂單。」
   0.50s ● model_response  ['c1', 'c2']
   0.50s   tool_started    c1 get_order
   0.50s   tool_started    c2 get_order
   1.00s   tool_finished   c2 get_order [ok] {"order_id": "B-1077", "status
   1.30s   tool_finished   c1 get_order [ok] {"order_id": "B-1042", "status
   1.30s ● tool_result     c1 ok
   1.30s ● tool_result     c2 ok
   1.70s ● model_response  ['c3', 'c4']
   1.70s   tool_started    c3 get_shipment
   1.70s   tool_started    c4 get_shipment
   2.30s   tool_finished   c3 get_shipment [ok] {"tracking": "TC-88301", "e
   3.70s   tool_finished   c4 get_shipment [timeout] get_shipment 在 2.0 秒內沒
   3.70s ● tool_result     c3 ok
   3.70s ● tool_result     c4 timeout
   4.15s   model_delta     ×5「B-1042 明天到；B-1077 的物流商沒有回應，我晚點再幫您確認。」
   4.35s ● model_response  B-1042 明天到；B-1077 的物流商沒有回應，我晚點再幫您確認。
   4.35s ● run_finished    done
  串流 25 項、核心事件 10 個；on_event 看到：{'run_started': 1, 'user_message': 1, 'model_response': 3, 'tool_result': 4, 'run_finished': 1}
  總時間：平行 4.35s，序列（max_parallel=1）5.45s
── B 退款進行中使用者離開，退款 API 卡住
   0.00s ● run_started     cs
   0.00s ● user_message    退款
   0.45s   model_delta     ×2「我先退款，再查另一張。」
   0.50s ● model_response  ['c1', 'c2']
   0.50s   tool_started    c1 refund
   1.00s   run_cancelling  使用者取消
   3.00s   tool_finished   c1 refund [unknown] 結果未知：refund 在 run 結束時仍未完成。不要
   3.00s   tool_finished   c2 get_order [cancelled] 已取消：get_order 尚未開始執行。
   3.00s ● tool_result     c1 unknown
   3.00s ● tool_result     c2 cancelled
   3.00s ● run_finished    cancelled
  10 秒後的退款紀錄：['B-2002']（標成「結果未知」的退款最後生效了）
── C fault injection 矩陣：每一種故障都檢查同一組不變式
  無故障         done      重試 0   3.15s  c1=ok c2=ok                        OK
  429 兩次       done      重試 2   4.95s  c1=ok c2=ok                        OK
  模型持續過載   error     重試 3   3.21s                                     OK
  請求格式錯誤   error     重試 0   0.40s                                     OK
  串流斷線       done      重試 1   3.71s  c1=ok c2=ok                        OK
  拒答           refusal   重試 0   0.50s                                     OK
  tool 例外      done      重試 0   2.35s  c1=error c2=ok                     OK
  tool 逾時      done      重試 0   4.35s  c1=timeout c2=ok                   OK
  取消 @0.7s     cancelled 重試 0   0.70s  c1=cancelled c2=cancelled          OK
  取消 @1.5s     cancelled 重試 0   2.70s  c1=ok c2=ok                        OK
  退款卡住＋取消 cancelled 重試 0   3.50s  c1=ok c2=unknown                   OK
  run 逾時 2s    timeout   重試 0   2.70s  c1=ok c2=ok                        OK
  乒乓查詢       loop      重試 0   4.80s  p1=ok p2=ok p3=ok p4=ok p5=error   OK
── D 取消時間點掃描：0.0～4.0 秒每 0.1 秒取消一次
  41 次全部滿足不變式；結局分布： {'cancelled': 5, 'cancelled（cancelled/cancelled）': 8, 'cancelled（ok/ok）': 19, 'done（ok/ok）': 9}
```

逐段解說這份輸出。

**情境 A** 是兩層事件最清楚的示範，● 標記的是寫進 Session 的核心事件。0.45 秒，模型的第一段文字就推到畫面上（`model_delta ×2`），使用者不必等整個 run 結束；0.50 秒串流結束，彙總成一個 `model_response`，宣告 c1、c2 兩個 call。兩個 get_order 同時開始，c2 在 1.00 秒先結束、c1 在 1.30 秒結束，串流依完成順序報告；但兩個 `tool_result` 都在 1.30 秒、依 c1、c2 的順序落地。第二步的 c4 物流商卡住，2.0 秒後以 timeout 回填，c3 的成功結果不受影響，模型據此回答「B-1077 的物流商沒有回應，我晚點再幫您確認」，這就是部分失敗不連坐。下面兩行統計：串流共 25 項，核心事件只有 10 個；`on_event` middleware 看到的正是這 10 個核心事件，看不到任何 delta。總時間平行 4.35 秒、序列 5.45 秒，差的 1.1 秒正好是 24.5 節甘特圖中 3.9 秒與 2.8 秒的差距。程式裡的 assert 把核心事件類型序列寫死，這就是 golden 事件序列，也是第 23 章契約的具體形式：它和同步參考 Runner 跑同一個劇本得到的序列相同。

**情境 B** 重演 Maya 找到的那筆退款。模型先要求 refund、再要求 get_order；refund 有副作用，自成一組先執行。1.00 秒使用者取消，串流推出 `run_cancelling`。get_order 還在排隊，直接記成「已取消：尚未開始執行」；refund 被 shield 保護，runtime 給它 2 秒寬限期，到 3.00 秒仍未完成，於是記成 unknown，內容是「不要重試，請轉真人查證」。兩個 `tool_result` 依 call 順序落地，最後是 `run_finished`，Session 可以續跑。接下來程式再等 10 秒，退款紀錄出現 B-2002：那筆被記成結果未知的退款，其實在 9.5 秒時生效了。如果 runtime 當時把它記成「已取消」或「失敗」，客服就會以為沒退，使用者重新要求時，一個沒有 idempotency key 的系統就會退第二次。

**情境 C** 的矩陣每一列都通過了同一組不變式。模型端：429 兩次後成功，比無故障多 1.8 秒（兩次 0.4 秒的 TTFT 加兩次 0.5 秒的 retry-after）；持續過載重試 3 次後以 error 結束；400 不重試，0.40 秒就結束；拒答不執行任何 tool，status=refusal。tool 端：例外與逾時都只影響 c1，c2 的退款照常完成。控制面：0.7 秒取消時兩個 call 都是 cancelled；1.5 秒取消與 run deadline 到期時退款正在進行，寬限期內完成，如實記成 ok；退款卡住再取消則是 unknown。最後一列的乒乓查詢在第 5 步被 loop guard 以「連續 3 步沒有新資訊」結束，p5 是沒有被執行的提醒。

**情境 D** 把取消時間從 0.0 秒掃到 4.0 秒，41 次全部滿足不變式。結局分布也很有資訊量：5 次在模型回應之前就取消（沒有任何 tool call）；8 次落在 get_order 執行期間，兩個 call 都是 cancelled；19 次在退款進行中或最後一次模型呼叫期間取消，tool 都已如實完成；9 次在取消之前就已經 done。24.9 節的天真版在同樣的掃描下會在第二類時間窗裡破功，而這裡每一個時間點都收得乾淨。

| 能力 | 實作位置 | 修掉的雙 11 問題 | 對應小節 |
|---|---|---|---|
| 兩層事件、`committed` 通知 | `commit()`、`_push()`、`stream()` | 前端在 run 結束前什麼都收不到 | 24.3、24.4 |
| 有上限的佇列、消費者離開即取消 | `Run.queue`、`stream()` 的 finally | 殭屍 run 繼續花錢、繼續施壓 | 24.4 |
| 唯讀平行、副作用依序、依 call 順序落地 | `_run_tools()`、`_exec()`、`_persist()` | 四個查詢一個接一個做 | 24.5 |
| shield＋寬限期、unknown、收尾補齊 | `_dispatch()`、`_settle()` | hotfix 造成的配對缺口與「不知道有沒有退款」 | 24.6 |
| 依 `ModelError.retryable` 的 full jitter 退避、deadline 感知 | `RetryPolicy`、`_call_model()` | 同步重試風暴 | 24.7 |
| 滑動視窗與沒有新資訊 | `LoopGuard` | 原地打轉到步數用完 | 24.8 |
| 虛擬時間、fault 矩陣、時間點掃描 | `VirtualTimeLoop`、`invariants()` | 慢又不穩定的測試 | 24.9 |

這段程式刻意沒有做的事：共享下游的全域並行上限與租戶 token bucket（第 36 章）；串流的閒置逾時、合併與重連續傳；crash 後補齊未完成的 run 與重播（第 22 章 `loom.durable`）；thread 中的同步 tool；重試預算。第 45 章的 `loom` v1.0 會把這些缺口與 durable、tracing、approval 一起組裝起來。

## 24.11 實務應用

runtime 的機制在不同產品裡的權重差異很大：同步聊天最在意串流與 deadline，coding agent 最在意中斷與長時間執行，research agent 最在意 fan-out 與 rate limit，語音 agent 最在意取消的速度。以下四個情境說明同一份 `loom.runtime` 要怎麼調整。

**情境一：電商客服的聊天視窗（青鳥的主線）**。使用者在等，所以最重要的是第一個字出現的時間與整體 deadline。串流事件經過一個轉接器翻成第 15 章的 AG-UI 事件：`model_delta` 對應文字訊息的內容事件，`tool_started`、`tool_finished` 對應 tool call 的開始與結果，前端據此顯示「正在查詢 B-1042」的卡片。訂單與物流查詢都是唯讀的，平行上限設 4；退款依序執行並套用 2 秒寬限期，任何 unknown 的結果自動開一張客服工單，附上 idempotency key 讓客服向金流查證。run deadline 設 60 秒，超過就以 timeout 結束並轉真人，轉交時附上 Session 的摘要。使用者關掉視窗即取消 run，但同一個使用者在 30 秒內回來時，前端用串流序號從 Session 補回已確定的結果，不需要重跑。

**情境二：IDE 與 CLI 中的 coding agent**。開發者隨時可能中斷 agent：Claude Code 這類工具允許使用者按 Esc 停止目前的動作，再輸入新的指示。對 runtime 來說，這就是「取消目前的 run，保留 Session，用新的 user_message 開始下一個 run」，取消必須在幾百毫秒內生效，否則使用者會覺得失控。讀檔、搜尋這類唯讀 tool 很適合平行，寫檔與執行指令則依序執行。執行 shell 指令的 tool 被取消時，要殺掉整個子 process 群組，不能只取消等待它的 coroutine，否則背景的編譯或測試會繼續佔用資源。loop guard 要用狀態感知的 key，讓「改完程式再跑測試」不被誤判；run deadline 放寬到數十分鐘，主要靠 token 預算控制成本。

**情境三：營運 research agent 的 fan-out**。月度分析時，lead agent 會同時派出多個 subagent，每個 subagent 又平行呼叫多個查詢與搜尋 tool（第 20 章）。這時 per-run 的平行上限完全不夠：二十個 subagent 各平行五個，下游就有一百個並行請求，模型的 TPM 也會被瞬間打滿。實務做法是在 process 層為每個下游與每個租戶設全域的上限與 token bucket，讓 subagent 排隊而不是互相踩踏；重試一律帶 jitter，並設重試預算。部分失敗是常態：某家店的報表服務掛了，報告要明確標示「S-4 資料缺漏」，而不是整份重跑。這類任務是背景執行，消費者離開不取消 run，前端之後從 Session 與串流序號接回進度；長時間執行的耐久性交給第 22 章的 `loom.durable`。

**情境四：語音客服 agent**。使用者在 agent 說話時插話（barge-in），系統必須立刻停止語音輸出、取消正在產生的模型回應，並且只把「使用者實際聽到的那一段」彙總進 `model_response`，否則模型會以為自己說完了整段話。較慢的查詢要先回一句「我幫您查一下」，再在背景完成。

| 產品類型 | 最重要的 runtime 機制 | 消費者離開時 | 平行策略 | 特別注意 |
|---|---|---|---|---|
| 客服聊天 | 串流、run deadline、寬限期 | 取消，Session 可續 | 唯讀平行、退款依序 | unknown 自動開工單 |
| coding agent | 快速中斷、長時間 deadline | 取消目前的 run | 讀檔平行、寫入依序 | 取消要殺掉子 process 群組 |
| research fan-out | 全域上限、jitter、重試預算 | 不取消，背景續跑 | 大量平行，受全域上限 | 部分失敗要在報告中標示 |
| 語音 agent | 毫秒級取消、部分輸出的彙總 | 插話即取消生成 | 只允許很快的 tool | 只記錄使用者聽到的部分 |

> [!note] 2026 現況
> 截至 2026 年 10 月，依各專案公開文件與 release 紀錄（細節以官方文件為準）：Anthropic 公開描述其 multi-agent research system 的 lead agent 會同時派出 3–5 個 subagent，每個 subagent 再平行使用多個 tool，複雜查詢的研究時間最多縮短約 90%；Google ADK 2.x 提供 `abort_signal` 讓執行可以被優雅地取消，並有支援語音與電話的 LiveKit runner；Strands Agents 的雙向串流 API 已正式發布，用於語音等即時互動；Mastra 支援跨 process 的取消，以及 durable streams 在暫停時關閉串流的設定；Claude Agent SDK 的 `ClaudeSDKClient` 支援雙向、多輪且可中斷的互動。GitHub Copilot coding agent 在 GitHub Actions 的臨時環境中執行，並有工作時間的硬上限。

## 24.12 設計檢查清單

設計或審查一個 agent runtime 時，逐項回答下面的問題。

1. 核心事件與串流事件是否明確分層？只有核心事件寫進 Session，串流事件是否保證不被計費、重播或投影依賴？
2. `tool_result` 是否依模型提出的 call 順序落地，而不是依完成順序？
3. 串流佇列是否有上限？消費者落後時採取背壓、合併還是丟棄 delta？狀態事件是否保證不被丟棄？
4. 消費者離開時，這個產品要取消 run 還是讓它背景續跑？重連時如何用 Session 與串流序號補回？
5. 哪些 tool 可以平行？有副作用的 tool 是否依序執行？平行上限是 per-run 還是全域？共享下游是否另有全域上限？
6. 一個 tool 失敗或逾時時，其他 call 的結果是否照常回填？是否確認沒有用預設的 `gather` 留下孤兒 task？
7. 是否設定了單次 tool、單次 model、串流閒置、run deadline、取消寬限期五層時間上限？內層 timeout 是否服從外層的剩餘時間？
8. 取消時，每個 tool call 是否都有 `tool_result`？副作用 tool 是否用 shield 與寬限期如實記錄，否則記為 unknown？
9. unknown 的結果是否禁止自動重試，並有對帳或轉真人的流程？
10. 重試是否只發生在一層？SDK 的內建重試是否已關閉？是否依 `ModelError.retryable` 決定、使用 jitter、遵守 retry-after、有次數上限與重試預算？
11. refusal 是否被當成停止原因交給產品政策，而不是觸發重試？
12. loop guard 是否同時看滑動視窗與「沒有新資訊」？合理的重複（狀態改變後）是否不會被誤判？
13. runtime 的測試是否跑在虛擬時間上？是否有 fault injection 矩陣、不變式檢查、取消時間點掃描與 golden 事件序列？

## 24.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 使用者回來追問時 API 回 400，提到 tool_use 沒有結果 | 取消或逾時時直接中止 task，沒有補齊 tool_result | 找出 Session 中有 `model_response` 宣告、卻缺 `tool_result` 的 call | 收尾協定：每個未完成的 call 都寫 cancelled 或 unknown |
| 稽核發現「紀錄說已取消，對方卻已執行」 | 取消時把進行中的副作用直接記成取消 | 比對 `tool_result` 與下游系統的 idempotency key 紀錄 | shield＋寬限期；逾期記 unknown 並對帳 |
| 供應商故障時請求量出現整齊的尖峰 | 固定間隔退避，沒有 jitter | 看重試請求的時間分布是否集中 | full jitter；遵守 retry-after |
| 故障時請求量是平常的好幾倍 | SDK、runtime、gateway 多層重試相乘 | 對同一個 request id 計算實際送出次數 | 只在 runtime 重試；關閉 SDK 內建重試；設重試預算 |
| 按下停止後 agent 還繼續跑好幾秒 | tool 吞掉了 `CancelledError`，或在 thread 中執行同步呼叫 | 在 trace 中看 `run_cancelling` 與 `run_finished` 的時間差 | 移除裸 except；同步 tool 標記為不可取消並設寬限期 |
| 一個 tool 失敗，整批查詢都沒有結果 | 用預設的 `gather` 或未包裝的 TaskGroup | 看 tool_result 是否整批缺漏或整批錯誤 | 每個 call 逐一包裝成結果，外層再收齊 |
| 同一劇本跑兩次，messages 順序不同、cache 命中率下降 | 依完成順序寫入 tool_result | 比較兩次 run 的核心事件序列 | 依 call 順序落地；完成順序只放在串流 |
| timeout 測試偶爾失敗、CI 很慢 | 測試用真實時間 | 在忙碌的機器上重跑，失敗率是否改變 | 虛擬時間 event loop；固定 seed；假後端 |

## 本章重點整理

- runtime 是把 Agent 宣告真正跑起來的那一層；`loom.runtime` 用 asyncio 實作第 23 章的 Runner 契約，同樣的劇本必須產生同樣的核心事件序列，Runner 持有策略，每次執行是一個 Run、一個 asyncio task。
- 事件分兩層：七種核心事件寫進 Session，是唯一的事實來源；串流事件只給 UI 與呼叫端即時消費，一件事完整發生後才彙總成核心事件。
- `tool_result` 依模型提出的 call 順序落地，完成順序只出現在串流；這讓 messages 可重現，prompt cache 與重播才穩定。
- 串流的 producer 要是獨立的 task，並用有上限的佇列連接消費者；背壓、合併與丟棄 delta 是要明確選擇的政策，狀態事件不能丟。
- 唯讀 tool 可以平行，有副作用的 tool 依序執行；平行上限要分 per-run 與全域兩層，共享下游必須有全域上限。
- 部分失敗不連坐：每個 call 逐一包裝成結果，外層用 TaskGroup 收齊；預設的 `gather` 會留下孤兒 task，未包裝的 TaskGroup 會整批作廢。
- asyncio 的取消在下一個 `await` 生效，`CancelledError` 不能被吞掉；取消訊號之後的收尾協定才是真正的工作。
- 本機的取消不會撤回已送出的請求；副作用 tool 要用 shield 與寬限期如實記錄，逾期記為「結果未知」，不可自動重試。
- timeout 分成單次 tool、單次 model、串流閒置、run deadline、取消寬限期五層，內層要服從外層剩下的時間。
- 重試與退避屬於 `loom.runtime`，錯誤分類、熔斷與 fallback 屬於第 25 章的 `loom.models`；runtime 只依 `retryable` 決定是否重試，refusal 是停止原因而不是錯誤。
- 指數退避要加 jitter 才能打散同步的重試風暴；重試只在一層發生，並受次數上限、deadline 與重試預算約束。
- loop guard 要組合滑動視窗、沒有新資訊與狀態感知的 key；它是保險絲，status=loop 上升時要修的通常是 tool 的回傳訊息。
- runtime 的測試要把時間、排程、隨機數、模型與外部故障全部變成參數；虛擬時間加 fault 矩陣、不變式與時間點掃描，能在幾毫秒內找出只在窄時間窗出現的競態。

## 延伸問答

> [!question]- Q1. 為什麼串流事件依完成順序送出，`tool_result` 卻要依 call 順序寫進 Session？兩者都用完成順序不是更簡單嗎？
> 兩者服務的對象不同。串流事件是給正在看的人：c2 比 c1 先完成，畫面就應該先顯示 c2 的卡片，這是使用者感受到的真實進度，延後顯示只會讓體驗變差。核心事件則是事實來源，messages 是從它投影出來的；如果 `tool_result` 依完成順序寫入，同一個劇本跑兩次，可能因為網路抖動得到兩種不同順序的歷史。
>
> 不同順序的歷史有三個實際代價。第一，下一次送給模型的 messages 不同，prompt cache 的前綴可能對不上（第 9 章）。第二，第 22 章的重播要逐筆比對事件，順序不確定就無法判斷是不是「同一次執行」。第三，第 23 章的契約測試要求 async runtime 和同步參考版產生相同的核心事件序列，完成順序會讓這個測試變成隨機失敗。等一組結束再依序寫入的成本很低，因為下一次模型呼叫本來就要等整組結果到齊。

> [!question]- Q2. 估算題：營運 research agent 一次派出 20 個 subagent，每個 subagent 每一步平均平行呼叫 5 個 tool，單次 tool 平均 0.8 秒、p99 為 6 秒。ERP 最多只能承受 30 個並行請求。你會怎麼設定上限與 timeout？大概的影響是什麼？
> 不設全域上限時，瞬間並行數是 20 × 5 ＝ 100，遠超過 ERP 的 30，結果通常是 ERP 開始逾時或回錯誤，反而讓所有 subagent 一起變慢。所以要在 process（或整個系統）層級為 ERP 設一個 30 的全域 semaphore，per-run 的上限維持 5 只是防止單一 subagent 霸佔。依 Little's law 粗估，30 個並行、每個平均 0.8 秒，ERP 的吞吐約每秒 37 個請求；一輪 100 個請求大約要 100 ÷ 37 ≈ 2.7 秒才消化完，比無限制時「理論上 0.8 秒」慢，但穩定、不會把 ERP 打掛。
>
> timeout 要看 p99：設在 6 秒附近，代表約 1% 的請求會以 timeout 回填，由模型決定要不要稍後再查；設太短會讓大量正常但稍慢的請求失敗，設太長則一個卡住的請求會佔住全域 semaphore 的名額。另外要注意 24.5 節的觀察：有上限時，排在後面的慢請求開始得晚，整步會被拉長，所以可以讓重要的查詢先送、或為報表類的慢 tool 單獨設一個較小的池，避免它們把快速查詢的名額佔光。

> [!question]- Q3. 程式找錯：下面的 tool 執行程式有三個會在 production 出事的問題，請指出並說明後果。
> ```python
> async def run_tools(calls):
>     results = await asyncio.gather(*(dispatch(c) for c in calls))
>     for c, r in zip(calls, results):
>         session.append(tool_result(c, r))
>
> try:
>     await run_tools(resp.tool_calls)
> except asyncio.CancelledError:
>     return "cancelled"
> ```
> 第一，`gather` 使用預設的 `return_exceptions=False`：只要某個 `dispatch` 丟出例外，整批結果都拿不到，其他 task 還會在背景繼續跑，成為沒人收結果的孤兒。除非 `dispatch` 保證把所有例外轉成結果，否則部分失敗會變成整批失敗。
>
> 第二，取消時直接 `return`，沒有為已提出的 tool call 補上結果，Session 裡留下沒有 `tool_result` 的 call，使用者下一次追問時 API 會拒絕整個請求。已經完成的 call 的結果也一起遺失了。第三，捕捉 `CancelledError` 之後既沒有重新丟出、也沒有呼叫 `uncancel()`，呼叫端不知道這個 task 被取消過，結構化並行的工具（例如外層的 TaskGroup 或 timeout）可能因此判斷錯誤。修法是 `loom.runtime` 的組合：每個 call 包裝成一定會回傳結果的形式，取消時先收尾補齊每個 call 的 `tool_result`（副作用用寬限期），再依設計重新丟出或以 uncancel 明確結束。

> [!question]- Q4. 你在 production 看到：供應商短暫過載之後，即使它已經恢復，你們的錯誤率還高了好幾分鐘，請求量也是平常的三倍。你會怎麼排查？
> 先確認是不是自己造成的二次傷害。第一步看重試請求的時間分布：如果出現整齊的尖峰，代表退避沒有 jitter，大量 client 同步醒來；第二步用 request id 或 trace 計算「一個使用者動作實際送出幾個請求」，如果遠大於 runtime 設定的次數，就是 SDK、runtime、gateway 多層重試相乘。這兩件事都會讓已恢復的供應商再次被打到限流，形成「恢復後仍然高錯誤率」的現象。
>
> 第三步看殭屍 run：統計已經沒有消費者、卻仍在重試的 run 數量，同步聊天的使用者早就離開，這些 run 只是在增加負載。第四步確認熔斷器（第 25 章）有沒有在故障期間打開、恢復後有沒有用半開狀態小量試探，而不是一次放回全部流量。修法依序是：關閉 SDK 內建重試、只在 runtime 重試並加 full jitter、設重試預算、消費者離開即取消、讓熔斷器控制恢復的節奏。修完後把這次的流量形狀做成 24.7 節那樣的離散事件模擬，放進回歸測試。

> [!question]- Q5. 使用者關掉視窗時，退款請求已經送到金流閘道 3 秒但還沒有回應。runtime 應該怎麼處理？如果等不到回應，之後又要怎麼辦？
> 第一個原則是不要說謊：本機取消這個 coroutine，不會讓金流閘道撤回退款，所以不能直接記成「已取消」。`loom.runtime` 的做法是用 shield 保護副作用 tool，取消時給它一段寬限期；寬限期內收到回應，就把真實結果記成 ok 並註明「run 結束前已完成」；寬限期到了還沒有回應，就記成 unknown，內容明確寫「可能已生效，不要重試」。這兩種情況都會產生 `tool_result`，配對不變式與 Session 的可續跑性都維持住。
>
> unknown 之後要有一條確定性的處理路徑，而不是交給模型猜。常見做法是：用 harness 推導的 idempotency key（第 5 章）向金流查詢這筆請求的狀態，查到就補一筆對帳紀錄；查不到或查詢服務也不可用，就開工單轉真人。使用者回來追問「到底退了沒」時，agent 讀到的是 unknown 的 `tool_result`，應該回答「正在確認中」而不是重送退款。就算模型真的重送，idempotency key 也會讓金流端只生效一次，這是最後一道防線。

> [!question]- Q6. 面試追問：如果要讓使用者在網路斷線 20 秒後重新連上，還能看到 agent 的完整進度，你的 runtime 與協定要怎麼設計？
> 第一個決定是「斷線不取消」：這類產品的 run 要和連線解耦，消費者離開時 run 繼續執行（或在背景佇列中執行），而不是在 `stream()` 的 finally 裡取消。第二是兩層資料各自負責：已確定的事實在 Session 的核心事件裡，可以隨時完整讀回；進度在串流裡，每個串流事件帶著遞增的序號。前端重連時帶上「最後收到的序號」，伺服器先送一份由核心事件投影出來的快照（例如目前的訊息與 tool 狀態），再從那個序號之後補送串流事件；這和第 15 章 AG-UI 的 snapshot 加 delta 是同一個想法。
>
> 第三是串流事件的保留：既然要補送，就需要一個短期的串流緩衝（例如每個 run 保留最近幾百個事件或幾十秒），超過範圍就只送快照，讓前端放棄打字效果、直接顯示結果。第四是多個消費者：同一個 run 可能同時有手機與桌機在看，所以串流要用「日誌加每個消費者的游標」而不是單一佇列。最後要談失敗模式：伺服器重啟時串流緩衝會遺失，但 Session 還在，所以重連一定要能退化成「只看快照」，正確性永遠只依賴核心事件。

> [!question]- Q7. timeout、cancellation、deadline 三個詞常被混用，它們的差別是什麼？在 runtime 裡各自由誰觸發、如何互相影響？
> cancellation 是機制：要求一個進行中的工作盡快停止，在 asyncio 裡是對 task 呼叫 `cancel()`，於下一個 `await` 注入 `CancelledError`。timeout 是一種觸發條件：某段工作超過自己的時間上限時，自動對它觸發取消，`asyncio.timeout()` 會在邊界把取消轉成 `TimeoutError`，讓呼叫端分得出「是時間到了」還是「被別人取消」。deadline 是一個絕對時間點：整個 run 必須在幾點幾分之前結束，它往下傳時會轉成每個子呼叫的剩餘時間。
>
> 三者的互動是：使用者取消與 run deadline 都作用在整個 run，觸發 `_drive` 的收尾協定，差別只在最後的 status 是 cancelled 還是 timeout；單次 tool 與 model 的 timeout 只作用在一個呼叫，結果是一個 timeout 的 `tool_result` 或一次可重試的模型錯誤，run 本身繼續。deadline 會壓縮內層：剩 1.2 秒時，tool 的 timeout 取 min(自己的上限, 1.2)，重試的等待若會超過 deadline 就不再等。另外，收尾本身也需要時間（寬限期），所以 deadline 要留給收尾的餘裕，否則 run 永遠會比宣告的上限晚幾秒結束。

> [!question]- Q8. 你們有一個只提供同步 SDK 的 ERP 查詢 tool，而 runtime 是 asyncio。怎麼整合？取消時會發生什麼事？
> 不能直接在 async 函式裡呼叫同步 SDK，否則每次查詢都會卡住整個 event loop，同一個 process 上所有 run 一起停住。常見做法是用 `asyncio.to_thread()`（或一個專用的 thread pool）執行它，event loop 只等待結果。thread pool 的大小本身就是這個下游的並行上限，應該依 ERP 的承受能力設定，而不是用預設值。
>
> 取消時要知道限制：等待 `to_thread` 的 coroutine 會收到 `CancelledError`，但 thread 裡的同步呼叫無法被中止，它會繼續跑到 SDK 自己的 timeout 或完成為止。對唯讀查詢，這只是浪費一個 thread 名額，可以接受，但要設好 SDK 層的連線與讀取 timeout，避免 thread 被永久佔住。如果這個 tool 有副作用，就要把它當成「取消時可能還在進行的副作用」，套用寬限期與 unknown 的規則。長期來看，最好的做法是換成 async 的 HTTP client 直接呼叫 ERP 的 API，或者把它包成一個獨立服務（例如第 14 章的 MCP server），讓阻塞與取消的問題留在那個服務的邊界內。

## 延伸閱讀

- Python 官方文件〈Coroutines and Tasks〉（asyncio 的 Task cancellation、TaskGroup、Timeouts、shield）
- Marc Brooker〈Exponential Backoff And Jitter〉（AWS Architecture Blog，2015）
- Google《Site Reliability Engineering》（O'Reilly，2016）第 21 章〈Handling Overload〉與第 22 章〈Addressing Cascading Failures〉
- Nathaniel J. Smith〈Notes on structured concurrency, or: Go statement considered harmful〉（2018）
- FoundationDB 文件〈Simulation and Testing〉
- AG-UI Protocol 文件〈Events〉
- Anthropic Engineering Blog〈How we built our multi-agent research system〉（2025）
