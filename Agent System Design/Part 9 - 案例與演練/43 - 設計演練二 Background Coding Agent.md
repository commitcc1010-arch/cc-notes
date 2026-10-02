---
chapter: 43
title: 設計演練二：Background Coding Agent 平台
part: 9
---

# 第 43 章　設計演練二：Background Coding Agent 平台

> [!abstract] 本章地圖
> **核心問題**：要讓工程師把 issue 指派給 agent、幾十分鐘後收到一個值得 review 的 PR，整個平台要怎麼設計，才能同時做到排隊不久、PR 可信、憑證不外洩、平行任務不互相踩踏，而且帳單算得出來？
>
> **你會學到**：
> - 用 system design interview 的節奏走完一題：需求釐清 → 估算 → 高階架構 → 時序 → 深入元件 → 擴展與取捨 → 追問
> - 用 Little's law 從每日任務數推出尖峰並行 sandbox 數、vCPU 與模型 TPM，並算出每個合併 PR 的成本
> - 設計 issue intake、task queue、scheduler、sandbox pool、repo cache、agent harness、驗證、PR 服務與人工審查之間的分工與介面
> - 為 sandbox 設計 egress allowlist 與 credential proxy，讓 git token 與模型金鑰從頭到尾不進 sandbox
> - 設計防範 reward hacking 的驗證層：獨立驗證環境、diff 政策、fail-to-pass 檢查與 review agent
> - 用 Python 模擬 warm pool 排程，驗證 Little's law，並實作任務生命週期狀態機與冪等的 PR 建立
>
> **前置知識**：第 17 章（sandbox 隔離層級、egress、credential proxy、warm pool）、第 20 章（平行寫入的 branch／worktree 隔離）、第 21 章（核准與信任 UX）、第 22 章（background agent 的佇列、lease 與 fencing）、第 29 章（tracing 慣例）、第 35 章（設計方法論與估算）、第 39 章（主流 coding agent 的架構拆解）

## 43.1 故事：試辦兩週，五件事故

青鳥科技的內部 coding agent 已經在 CI 裡跑了半年：工程師在 pull request 上留言，agent 在 sandbox 裡修測試、補型別，依第 1 章的 autonomy 分級是「sandbox 內 L4」，所有寫入都關在 sandbox 與分支裡，合併永遠由人決定。工程主管們很滿意，於是提出下一步：「讓我們直接把 issue 指派給 agent，像指派給同事一樣，下午回來看 PR。」阿哲把這個需求排進季度目標，Iris 用三台共用的 VM 和一個簡單的工作佇列，在兩週內做出試辦版。

試辦第二週就出了五件事。週一早上 sprint 規劃會一結束，七十張 issue 同時被指派，每個任務都要從頭 clone 一個 2 GB 的 monorepo、再花五分鐘安裝相依套件，最後一張等了五十分鐘才開始動工。週二，一個 PR 宣稱修好了退款金額的 bug，CI 全綠，reviewer 差點按下 approve，才發現 agent 把測試裡的預期值從 500 改成了 5。週三，兩個任務同時修改 `checkout/pricing.ts`，產生了兩個互相衝突的 PR，後合併的那個悄悄覆蓋了前一個的修正。週四，一個任務卡在「改一行、跑全部測試、再改一行」的迴圈裡三個小時，花掉的 token 是平均任務的四十倍。週五，Maya 在審查時發現，VM 的環境變數裡放著 Iris 的個人 GitHub token，任何一個任務裡的程式都讀得到，而 issue 內容是任何人都能寫的文字。

老陳看完事故報告，沒有直接給答案，而是說：「這週的設計審查，我們用面試的方式來做。我當面試官，你當候選人，題目是『設計一個讓工程師把 issue 指派給 agent、非同步產生 PR 的平台』。五件事故，每一件都應該在某個步驟被問出來。」這一章就是那場審查的完整紀錄。我們依 system design interview 的順序前進：先釐清需求與估算，再畫出高階架構與時序，接著逐一深入 sandbox、secrets、repo 快取、平行衝突、驗證、成本與可觀測性，最後討論擴展、取捨與面試官的追問。動手做會用 Python 模擬 sandbox pool 的排程，並實作任務的生命週期狀態機。

## 43.2 需求釐清：先問清楚，再畫方塊

system design interview 最常見的失誤，是聽完題目就開始畫架構。老陳的第一個問題是：「這個平台的『完成』是什麼意思？」Iris 想了一下：「不是 agent 說完成，也不是 CI 綠燈，而是一個工程師願意合併、而且合併後不會被 revert 的 PR。」這個定義直接決定了後面所有的設計：成功率要從 PR 合併率與 revert 率來量，驗證層的目標是讓 reviewer 的時間花得值得，而不是讓 agent 盡量多開 PR。

接著要把功能需求、非功能需求與不做的事分開。功能需求是：工程師在 issue tracker 上把 issue 指派給 agent（或加上一個標籤），agent 在背景完成修改，開出一個附有說明、測試結果與成本的 PR；reviewer 可以在 PR 上留言要求修改，agent 會接著改；工程師隨時可以查看進度或取消。非功能需求則是延遲、可靠性、安全與成本的目標。不做的事同樣重要：agent 不合併、不部署、不修改 CI 設定，也不碰 production 資料，這幾條把 autonomy 鎖在「sandbox 與分支內 L4，越過分支邊界一律由人決定」。

| 要問的問題 | 試辦後的答案（本章的假設） | 影響的設計 |
|---|---|---|
| 誰能指派？任務來自哪裡？ | 內部工程師；issue 內容可能貼了客戶回報，視為不可信文字 | intake 的權限檢查；prompt injection 防線 |
| 規模多大？ | 400 位工程師、120 個 repo，每日約 300 張任務 | 估算、sandbox pool 容量 |
| 使用者願意等多久？ | 開始動工 p95 小於 2 分鐘；PR p50 在 30 分鐘內 | warm pool、repo 快取 |
| 「完成」怎麼定義？ | PR 被合併且 14 天內沒有 revert | 驗證層、成功指標 |
| agent 能做到哪裡？ | 改程式、跑測試、開 PR；不合併、不部署、不改 CI | autonomy 邊界、權限、diff 政策 |
| 能用哪些網路資源？ | 公司套件鏡像站、git server；不開放任意網際網路 | egress allowlist |
| 單一任務的上限？ | 60 分鐘 sandbox 時間、固定 token 預算，超過就停 | scheduler 的預算控制 |
| 失敗時要怎樣？ | 不靜默失敗：留言說明卡在哪、附上部分成果 | 狀態機、通知 |
| 語言與工具鏈？ | TypeScript 為主，少數 Python 與 Go | 映像與快取策略 |

這張表的左欄是面試時應該主動問出口的問題，中欄是本章採用的假設。真實面試裡，面試官常常只回答其中幾題，其餘要你自己提出合理假設並說出來。最值得注意的是第一列與第五列：issue 內容是不可信輸入，而 agent 的權限邊界停在「開 PR」。這兩條加起來，等於在需求階段就承認了第 31 章的 lethal trifecta：agent 會讀到不可信內容、接觸私有原始碼、還能執行程式。後面的 sandbox 與 secrets 設計，都是在拆掉其中一條腿。

> [!warning] 常見誤解
> 「非同步就代表延遲不重要。」使用者不必盯著畫面，不代表可以等一個小時。background agent 的延遲體驗分成兩段：「開始動工要多久」決定使用者是否相信任務真的被接走了，「PR 多久出現」決定能不能在同一個工作時段內 review。第一段比第二段敏感得多，這正是週一事故讓大家不滿的原因：不是 PR 慢，而是五十分鐘內什麼都沒發生。

## 43.3 估算：任務量、sandbox 分鐘、token 與成本

估算的目的不是算出精確數字，而是找出**哪個資源會先成為瓶頸、哪個成本項目最大**。第 35 章的方法是先列假設、再推導、最後找出「改哪個假設，結論就會翻轉」。下面這段程式把青鳥試辦期的數據寫成假設，一次算完。記號與單價沿用第 35 章：Little's law 算平均並行、Poisson 分位數算 p99，輸入成本以「命中的部分以 cache 讀取價、沒命中的部分以寫入價」計算；單價是為了計算比例而設的假設值，實際價格請查當時的價目表。

```python
import math

# 青鳥 background coding agent 的容量與成本估算：所有輸入都是假設，改這裡就能重算
A = dict(
    engineers=400, tasks_per_engineer=0.75,      # 試辦期：每位工程師每工作日指派約 0.75 張 issue
    attempts=1.3,                                # 驗證失敗重來、reviewer 要求修改，平均每張 1.3 個 session
    peak_share=0.5, peak_minutes=240,            # 一半的任務集中在上午四小時
    agent_min=25, verify_min=6,                  # 每個 session 佔用 agent sandbox 25 分、驗證 sandbox 6 分
    headroom=1.6, vcpu_per_sbx=4,
    calls=60, ctx_tokens=60_000, cache_hit=0.9, out_per_call=600,   # ctx＝第 35 章的 P ＋ d×(k−1)/2
    price_in=3.0, price_out=15.0, cache_read=0.10, cache_write=1.25,  # 和第 35 章相同的示意價格與倍數
    sbx_hour=0.20,                               # 假設每台 4 vCPU sandbox 每小時 0.2 美元
    merge_rate=0.55,
)


def poisson_quantile(mean: float, q: float = 0.99) -> int:
    """每個 session 各佔一台 sandbox、Poisson 到達時，忙碌台數服從 Poisson(mean)；回傳 q 分位數。"""
    k, total = 0, 0.0
    while True:
        total += math.exp(-mean + k * math.log(mean) - math.lgamma(k + 1))
        if total >= q:
            return k
        k += 1


tasks = A["engineers"] * A["tasks_per_engineer"]
sessions = tasks * A["attempts"]
lam = sessions * A["peak_share"] / A["peak_minutes"]                 # 尖峰到達率（每分鐘）
busy_agent, busy_verify = lam * A["agent_min"], lam * A["verify_min"]  # Little's law：L = λW
p99 = poisson_quantile(busy_agent + busy_verify)
capacity = round((busy_agent + busy_verify) * A["headroom"])
sbx_hours = sessions * (A["agent_min"] + A["verify_min"]) / 60

tok_in = A["calls"] * A["ctx_tokens"]
tok_out = A["calls"] * A["out_per_call"]
in_mult = A["cache_hit"] * A["cache_read"] + (1 - A["cache_hit"]) * A["cache_write"]  # 沒命中的部分寫進 cache
usd_tok = (tok_in * in_mult * A["price_in"] + tok_out * A["price_out"]) / 1e6
usd_day_tok, usd_day_sbx = usd_tok * sessions, sbx_hours * A["sbx_hour"]
peak_tpm = busy_agent * A["calls"] / A["agent_min"] * A["ctx_tokens"]  # 忙碌台數 × 每台每分鐘呼叫數 × 每次 input

rows = [
    ("每日任務／session", f"{tasks:.0f} 張／{sessions:.0f} 個"),
    ("尖峰到達率 λ", f"{lam:.2f} 個/分鐘"),
    ("尖峰忙碌 sandbox（agent＋驗證）", f"{busy_agent:.1f}＋{busy_verify:.1f} 台，Poisson p99 {p99} 台"),
    ("sandbox 上限（平均 × 1.6）", f"{capacity} 台、{capacity * A['vcpu_per_sbx']} vCPU"),
    ("每日 sandbox 時數", f"{sbx_hours:.0f} 小時"),
    ("每 session tokens（input／output）", f"{tok_in / 1e6:.1f}M／{tok_out / 1e3:.0f}k"),
    ("每 session 成本（tokens）", f"${usd_tok:.2f}"),
    ("每日成本：tokens／sandbox", f"${usd_day_tok:,.0f}／${usd_day_sbx:,.0f}"),
    ("每個合併 PR 的成本", f"${(usd_day_tok + usd_day_sbx) / (tasks * A['merge_rate']):.2f}"),
    ("尖峰 input TPM", f"{peak_tpm / 1e6:.1f}M tokens/分鐘"),
]
for k, v in rows:
    print(f"{k:<30}{v}")
assert 15 < busy_agent < 25 and usd_day_tok > 10 * usd_day_sbx     # token 成本遠大於運算成本
assert busy_agent + busy_verify < p99 < capacity                    # 上限要高過 Poisson p99，留給長尾工時
```

```text
每日任務／session                  300 張／390 個
尖峰到達率 λ                       0.81 個/分鐘
尖峰忙碌 sandbox（agent＋驗證）        20.3＋4.9 台，Poisson p99 38 台
sandbox 上限（平均 × 1.6）          40 台、160 vCPU
每日 sandbox 時數                 202 小時
每 session tokens（input／output）3.6M／36k
每 session 成本（tokens）          $2.86
每日成本：tokens／sandbox           $1,116／$40
每個合併 PR 的成本                   $7.01
尖峰 input TPM                  2.9M tokens/分鐘
```

逐行看這份估算。400 位工程師每天各指派 0.75 張，得到每日 300 張任務；因為驗證失敗會重來、reviewer 會要求修改，每張任務平均 1.3 個 session，所以 sandbox 實際要服務 390 個 session。尖峰集中在上午四小時，到達率約每分鐘 0.81 個。

並行數用 **Little's law**（利特爾法則）推導：在穩定的系統中，系統內的平均個數 L 等於到達率 λ 乘以每個個體的平均停留時間 W，即 L = λW。它不需要知道到達或服務時間的分布，只要系統穩定就成立。例如一家咖啡店每分鐘來 2 位客人、每位平均停留 10 分鐘，店裡平均就有 20 位客人。套到這裡：每分鐘 0.81 個 session、每個佔用 agent sandbox 25 分鐘，尖峰平均有約 20 台 agent sandbox 在忙，再加約 5 台驗證 sandbox。平均值不能當容量。若到達近似 Poisson、每個 session 各佔一台，忙碌台數的 p99 約 38 台（第 35 章 35.12 節的算法）；工時又有長尾，比 Poisson 假設更容易擠在一起，所以乘上 1.6 倍餘裕，上限設 40 台、160 個 vCPU，略高於 p99。43.16 節的模擬會看到，上限只比平均多兩成時，佇列會怎麼失控。

成本的結論最重要：每個 session 讀進約 3.6M input tokens（60 次模型呼叫、平均每次 60k tokens 的 context）。用第 35 章的記號，k ＝ 60，平均每次的 context 等於 P ＋ d×(k−1)/2，例如 P ＝ 10,000、d ≈ 1,700；這時平方項占了八成以上，所以 compaction 直接砍在最大的成本來源上。每日 token 成本約 1,100 美元，sandbox 運算只要 40 美元左右，兩者差了二十多倍。這代表**成本控制的主戰場是 token，不是機器**；省 sandbox 時間的主要價值在延遲與容量，而不是帳單。另一個常被忽略的數字是尖峰 TPM：約 2.9M input tokens／分鐘，模型供應商的 rate limit 很可能比 sandbox 容量更早成為瓶頸，所以 model gateway 的配額要和 sandbox 容量一起規劃。最後一行「每個合併 PR 約 7 美元」是給阿哲的數字：它要和「工程師自己修這張 issue 的時間成本」比較，也要拿來追蹤趨勢，因為合併率每掉 10 個百分點，這個數字就上升約兩成。

| 假設 | 目前值 | 改變後的影響 | 翻轉結論的條件 |
|---|---|---|---|
| 每次呼叫的平均 context | 60k tokens | 線性影響 token 成本 | context 加倍時，token 仍是最大成本，只是更大 |
| cache 命中率 | 90% | 掉到 50% 時 token 成本約變成 2.7 倍 | 中途改寫 system prompt 或 tool 順序就會發生 |
| 每任務 session 數 | 1.3 | 線性影響 sandbox 與 token | 驗證太嚴或太鬆都會推高它 |
| 尖峰集中度 | 50% 在四小時內 | 決定 sandbox 上限與 TPM | 改成全天平均時，容量需求減半 |
| 合併率 | 55% | 決定每個合併 PR 的成本 | 低於 20% 時，平台的效益可能低於 reviewer 的時間成本 |

這張敏感度表是估算的第二半：它告訴你哪些假設值得先驗證。cache 命中率與合併率是最有槓桿的兩個，前者靠 context 版面設計（第 9 章），後者靠 intake 篩選與驗證品質，兩者在後面的深入元件中都會再出現。

## 43.4 高階架構：從 issue 到 PR 的元件

有了需求與數字，才開始畫方塊。核心的架構決定只有一句話：**agent 的大腦（harness 與模型呼叫）在 sandbox 外面，sandbox 只是它的手。** harness 持有任務狀態、預算與模型存取，sandbox 只負責執行檔案操作與 shell 指令；sandbox 掛了，換一台新的就好，任務狀態不會跟著消失。

```text
                       ┌──────────────────────── 控制平面（可信） ─────────────────────────┐
 Issue tracker ─webhook─► (1) Intake ──► (2) Task store ＋ queue ──► (3) Scheduler          │
 （指派／標籤／留言）    │  權限、去重、   （durable：任務、事件、   admission、預算、       │
       ▲                 │  適合度篩選     attempt、成本帳）        租戶與 repo 並行上限    │
       │                 │                                              │ lease             │
       │                 │  (8) PR 服務 ◄── (7) 驗證服務 ◄──────── (4) Agent harness ──────┼──► Model gateway
       │                 │  GitHub App 身分   測試／lint／型別、     loom runtime：loop、   │    （配額、路由、
       │                 │  推送分支、開 PR   diff 政策、review agent  context、compaction  │      cache、計費）
       │                 └───────┬──────────────────▲───────────────────────┬────────────────┘
       │ PR、留言、狀態           │ push（只在這裡）   │ 套用 diff 重跑        │ execute(tool, args)
       │                         ▼                  │                       ▼
 (9) 人工審查 ◄──────── git server     ┌──────── 資料平面（不可信） ───────────────────┐
     approve／要求修改／合併             │ (5) Sandbox pool：warm pool、每任務一台 microVM │
                                        │ (6) Repo cache：base 映像＋每 repo snapshot     │
                                        │ 唯一出口：egress proxy（鏡像站、git fetch）     │
                                        └─────────────────────────────────────────────────┘
```

這張圖分成上下兩個平面。上方的**控制平面**是可信的程式碼，持有狀態與權限；下方的**資料平面**執行模型產生的指令，一律當成不可信。依編號走一遍：(1) **Intake** 接收 issue tracker 的 webhook，檢查指派者有沒有該 repo 的寫入權限、這張 issue 是否已有進行中的任務（去重），並用小型快速模型做**適合度篩選**：描述太模糊、需要產品決策、或明顯超出 agent 能力的 issue，直接留言請人補充，而不是燒一個 session 去猜。(2) **Task store** 是 durable 的任務紀錄與事件日誌，佇列只存任務 id；所有狀態轉移都寫成事件，這是第 22 章「進度在 durable 儲存裡」的原則。(3) **Scheduler** 決定誰先跑：檢查租戶與 repo 的並行上限、每日預算、熱點檔案的衝突，再以 lease 把任務交給 harness。

(4) **Agent harness** 就是 `loom` 的 runtime：跑 agent loop、組 context、做 compaction、記帳。它透過 model gateway 呼叫模型，透過 `execute(tool, args)` 把檔案與 shell 操作送進 sandbox。(5) **Sandbox pool** 管理 microVM 的生命週期與 warm pool，(6) **Repo cache** 提供每個 repo 已安裝好相依套件的 snapshot，這兩個元件決定「開始動工要多久」。(7) **驗證服務**把 agent 的 diff 套到另一台乾淨的 sandbox 上重跑測試、lint 與型別檢查，再執行 diff 政策與 review agent。(8) **PR 服務**是整個系統裡唯一能推送到 git server 的元件，用 GitHub App 身分建立分支與 PR。(9) **人工審查**是最後一道門，也是唯一能合併的角色。

| 元件 | 主要職責 | 持有的狀態 | 失敗時怎麼辦 |
|---|---|---|---|
| Intake | 權限、去重、適合度篩選、建立任務 | 無（寫入 task store） | webhook 重送以 issue id＋事件 id 去重 |
| Task store／queue | 任務、事件、attempt、成本帳 | 全部的權威狀態 | 資料庫的複寫與備份；佇列可從 store 重建 |
| Scheduler | 准入、預算、並行上限、lease | lease 與 fencing token | lease 過期就回到佇列；fencing 擋住舊 worker |
| Agent harness | agent loop、context、compaction | session log（寫入 store） | 無狀態，由 session log 恢復 |
| Sandbox pool | microVM 生命週期、warm pool | 實例清單 | 實例掛掉以 tool error 回報，harness 換一台 |
| Repo cache | 每 repo snapshot、相依套件快取 | snapshot 與版本 | 退回較舊的 snapshot，再 git fetch 補差 |
| 驗證服務 | 重放 diff、測試、diff 政策、review agent | 驗證報告 | 基礎設施失敗與測試失敗分開回報 |
| PR 服務 | 推送分支、開 PR、留言 | idempotency key | 以 key 去重，重試不會開出第二個 PR |

這張表最值得看的是第三欄：只有 task store 持有權威狀態，harness 與 sandbox 都是可丟棄的。這種「cattle, not pets」的設計讓每個元件都能獨立重啟，也讓 43.6 節的狀態機成為整個系統唯一的真相來源。

## 43.5 一張 issue 的旅程：時序圖

架構圖說明「有哪些元件」，時序圖說明「它們怎麼互動」。下面追蹤一張 issue「退款金額沒有換算成分」從指派到合併的完整過程，其中包含一次驗證失敗後的修正。

```text
 工程師   Tracker   Intake   Store/Queue  Scheduler  Harness   Sandbox   驗證服務   PR 服務   Model
   │ 指派給 agent │        │           │          │         │          │          │         │
   │────────►│ webhook │           │          │         │          │          │         │
   │         │────────►│ 權限、去重、適合度    │         │          │          │         │
   │         │◄────────│ 留言「已接手，預計 30 分」  │          │          │         │
   │         │         │──建立任務─►│ QUEUED    │         │          │          │         │
   │         │         │           │◄─lease──│ 檢查預算、並行上限         │          │         │
   │         │         │           │          │─派工───►│ acquire（warm）    │          │         │
   │         │         │           │          │         │─還原 snapshot、fetch、checkout base   │
   │         │         │           │          │         │◄────────►│ loop：讀碼、改檔、跑測試 ◄─►│
   │         │         │           │◄──────── 每步事件、token 帳 ─│          │          │         │
   │         │         │           │          │         │── diff ─────────────►│ 乾淨 sandbox 重放
   │         │         │           │          │         │◄── 失敗：改了既有斷言 ──│          │         │
   │         │         │           │          │         │◄────────►│ 帶回饋繼續改           │◄─►│
   │         │         │           │          │         │── diff ─────────────►│ 通過＋review agent
   │         │         │           │          │         │────────────────────────────────►│ 推送、開 PR
   │◄────────│◄─────── 通知：PR、測試結果、成本、trace 連結 ──────────────────────│         │
   │ review、合併（人）│           │ MERGED    │         │ sandbox 銷毀          │          │         │
```

時序圖有幾個值得停下來的點。第一，intake 在建立任務之前就回覆了一則留言，這是 43.2 節「開始動工要多久」的體驗答案：使用者立刻知道任務被接走，並拿到預估時間。第二，scheduler 拿到 lease 才派工，而 harness 從 warm pool 取得 sandbox 後，先還原 repo snapshot、用 `git fetch` 補上 snapshot 之後的新 commit，再 checkout 到 issue 指定的 base commit；這三步讓「開始動工」從分鐘級降到秒級。第三，loop 的每一步都寫回 store，包括 token 與 sandbox 時間的成本帳，所以 harness 在任何時刻掛掉，都能由新的 harness 從 session log 接手。

第四，驗證不在 agent 自己的 sandbox 裡做。harness 只把 diff 交給驗證服務，驗證服務在另一台乾淨的 sandbox 上套用 diff、重跑完整測試。這樣 agent 在自己 sandbox 裡做的任何事（改了快取、裝了奇怪的套件、在背景留下 process）都不會影響驗證結果。第一次驗證失敗時，回饋送回同一個 harness，agent 在原來的 sandbox 繼續修改。第五，只有 PR 服務會推送，推送前 sandbox 已經不參與了；通知裡除了 PR 連結，還附上測試結果、本次任務的成本與 trace 連結，讓 reviewer 能判斷這個 PR 是怎麼來的。

## 43.6 任務資料模型與生命週期狀態機

面試官接下來通常會問：「一個任務在系統裡長什麼樣子？」答案是一筆 durable 的任務紀錄加上一串事件。任務紀錄的關鍵欄位包括：任務 id、來源 issue 與 repo、base commit、指派者（代表誰行動）、狀態、attempt 編號、revision 次數、預算（token 與 sandbox 分鐘）與已用量、目前的 lease 與 fencing token、分支名稱與 PR 編號。事件則是 append-only 的：每次狀態轉移、每一步 tool 呼叫、每一次驗證結果都是一筆事件，這延續第 10 章「log 只能追加」的不變式。

```text
                 取消（任何非終態）──────────────────────────────► CANCELLED
                                                                      ▲
 指派 ─► QUEUED ──lease──► RUNNING ──交出 diff──► VERIFYING ──通過──► PR_OPEN ──人合併──► MERGED
           ▲                 │  ▲                   │                 │  │
           │  lease 過期／   │  └──驗證失敗＋回饋───┘                 │  └──人關閉──► CLOSED
           │  sandbox 掛了   │      （revision < 上限）               │
           └─────────────────┘                     │ 連續失敗達上限    │ reviewer 要求修改
           ▲                 │ 預算用完／不可修正   ▼                 │
           │                 └──────────────────► FAILED   ESCALATED  │
           └──────────────────────────── 新的 revision 任務 ◄─────────┘
```

這張狀態機的設計要點有四個。第一，**合法轉移寫成資料**，不在表上的轉移一律拒絕；例如 CANCELLED 之後，一個遲到的 worker 想把任務改回 RUNNING，必須失敗，這和第 22 章的 fencing token 是同一個目的：防止舊的執行者在新狀態上寫入。第二，**RUNNING 回到 QUEUED** 代表 sandbox 掛了或 lease 過期，任務會換一台新的 sandbox、從 base commit 重新開始，attempt 加一；舊 sandbox 不會被沿用，因為無法確認它的狀態，這是第 17 章「用完即銷毀」原則的延伸。第三，**VERIFYING 回到 RUNNING** 有次數上限，超過就進入 ESCALATED：把目前的 diff、驗證報告與卡住的原因留言給工程師，交由人決定。這比無限重試便宜，也比靜默失敗誠實。

第四，PR_OPEN 不是終點。reviewer 在 PR 上留言要求修改時，系統建立一個新的 revision 任務回到 QUEUED，帶著留言內容與目前分支的 head commit。PR 合併或關閉後才是終態，sandbox 與任務專用的 session token 都在進入終態時銷毀。43.16 節會把這張狀態機實作成程式，並用 ScriptedModel 走過正常路徑、改測試被擋、sandbox 當機與連續失敗四種情境。

## 43.7 深入一：sandbox 隔離與 egress

面試進入深入階段，老陳挑的第一個元件是 sandbox：「issue 是任何人都能寫的文字，agent 會在裡面執行任意指令，你怎麼關住它？」依第 17 章的決策表，寫程式的是模型、輸入含不可信文字、受害者是全公司的原始碼，所以隔離層級要用 microVM 或 gVisor，不能停在共用 host kernel 的一般 container。coding agent 還常需要在 sandbox 裡啟動資料庫或跑 Docker 化的整合測試，這讓 microVM 成為比較自然的選擇：它有自己的 guest kernel，可以在裡面跑完整的 Linux 環境。

範圍是「每個任務 attempt 一台」：從取用到銷毀只服務一個任務，跨 revision 時也開新的一台，從 snapshot 與分支 head 還原。資源上限包括 4 vCPU、16 GB 記憶體、磁碟配額、60 分鐘的租期上限與 pids 上限；租期上限就是 43.2 節「單一任務的上限」，到期由 pool 強制回收，不靠 agent 自己停。

```text
 microVM（每任務一台，沒有預設路由，DNS 只能問 proxy）
   │
   ├─► npm／pip／go 套件請求 ──► Egress proxy ──► 公司套件鏡像站（唯讀）           允許
   ├─► git fetch 本 repo ──────► Egress proxy ──► git server（唯讀、只限本 repo）  允許
   ├─► 模型 API ───────────────► （沒有路徑：模型呼叫在 harness，不在 sandbox）    不存在
   ├─► git push ───────────────► （沒有路徑：只有 PR 服務能推送）                   不存在
   ├─► 任意網站、貼文服務 ────► Egress proxy ──► 拒絕，記錄並計數                   拒絕
   └─► 雲端 metadata 端點 ────► 網路層直接丟棄                                      拒絕
```

這張資料流圖把 egress 分成三類。允許的只有兩條：套件鏡像站與本 repo 的唯讀 git fetch，而且都經過 proxy，proxy 比對主機、方法與路徑前綴，並記錄每一次連線。「不存在」的兩條是架構上就沒有的路徑：模型呼叫在 harness 裡，所以 sandbox 裡沒有模型金鑰也沒有模型端點；推送只能由 PR 服務做，所以 sandbox 裡沒有寫入用的 git 憑證。其餘一律拒絕，包括雲端的 instance metadata 端點。

為什麼不乾脆開放網際網路讓 agent 查文件？因為依第 17 章的原則，allowlist 等同授權：一旦允許連到任何人都能上傳內容的網域，就等於允許把原始碼送到那裡。issue 裡的一段文字就可能誘導 agent 這麼做，而模型自己的判斷不是可靠的防線。需要查文件時，比較安全的做法是由 harness 提供一個唯讀的文件搜尋 tool，在 sandbox 外執行、只回傳文字，而不是讓 sandbox 自己連網。

## 43.8 深入二：secrets 與身分

週五的事故（個人 token 放在 VM 環境變數）是這一節的起點。原則來自第 17 章：**secrets 不進 sandbox**。這個平台實際需要的憑證有四種，每一種都有不同的處理方式。模型 API 金鑰只存在 model gateway，harness 用服務身分呼叫 gateway，sandbox 完全接觸不到。git 的讀取憑證由 egress proxy 在轉送時代為加上，sandbox 只拿到一個任務專用、短效、只能在 proxy 上使用的 session token；即使它被讀走，也只能在任務存活期間，透過 proxy，讀取這一個 repo。git 的寫入憑證只在 PR 服務手上。測試需要的第三方服務憑證則一律以假服務或錄製的回應取代，真的需要連線的整合測試留給一般的 CI。

身分方面，依第 33 章的建議，agent 以自己的 **GitHub App** 身分安裝在允許的 repo 上，PR 服務每次推送前取得只對該 repo 有效、短時間內過期的 installation token。PR 上同時標示「由 agent 建立、代表哪位工程師」，形成可稽核的代理鏈。branch protection 規定 agent 只能推送到 `agent/` 開頭的分支，主分支必須經過人工 review 與 CODEOWNERS 核准，這條規則寫在 git server 上，而不是寫在 agent 的 prompt 裡。

> [!tip] 「代表誰」決定權限的上限
> agent 代表指派者行動，所以它能碰的 repo 不應超過指派者本人能寫的 repo。intake 在建立任務時檢查指派者權限，PR 服務在推送時再檢查一次，兩道檢查用同一份權限資料，避免指派後權限被撤銷的情況。

## 43.9 深入三：repo 快取與暖機

週一的事故是延遲問題，答案是把「開始動工」拆成三段，每段分別處理：開一台 sandbox、把 repo 與相依套件準備好、把程式碼對到正確的 commit。第一段由 warm pool 處理，第二段由 repo snapshot 處理，第三段用增量的 `git fetch` 處理。

```text
 第 1 層：base 映像（每週重建）        作業系統、Node／Python／Go 工具鏈、常用 CLI
     │
 第 2 層：repo snapshot（每晚，或 lockfile 變更時）
     │   由受信任的 builder 從 main 建立：clone、安裝相依套件、建置快取、測試資料
     │   版本鍵 = (repo, lockfile hash, 工具鏈版本)
     │
 第 3 層：任務啟動（每任務）
         warm 實例 ─► 掛載對應 snapshot ─► git fetch（只補 snapshot 之後的 commit）
                   ─► checkout base commit ─► 若 lockfile 不同才增量安裝
         任務的修改只存在這台 sandbox，絕不寫回第 2 層
```

這張分層圖的關鍵是**快取只能由可信的一方寫入**。第 2 層的 snapshot 由一個獨立的 builder 從主分支建立，任務 sandbox 只能讀取；如果允許任務把自己安裝好的 node_modules 寫回快取，一個被誘導的任務就能污染之後所有任務的環境，這叫 **cache poisoning**（快取投毒）。版本鍵包含 lockfile hash 與工具鏈版本，任何一個改變都會產生新的 snapshot，舊的保留幾天供回退。

| 啟動策略 | 開始動工的時間（量級） | 成本 | 風險與限制 |
|---|---|---|---|
| 每次完整 clone＋安裝 | 數分鐘 | 鏡像站與 git server 負載高 | 尖峰時排隊，週一事故的原因 |
| 共用的長駐 repo 目錄 | 秒級 | 低 | 跨任務殘留，違反用完即銷毀，不採用 |
| repo snapshot＋增量 fetch | 數十秒（含開機） | snapshot 儲存與重建 | snapshot 過舊時 fetch 變慢 |
| warm pool＋snapshot | 十幾秒 | 待命實例的閒置成本 | pool 大小要依尖峰調整 |
| 每 repo 的 warm pool | 數秒 | 閒置成本乘上 repo 數 | 只值得用在最熱門的幾個 repo |

表中的時間只寫量級，實際數字取決於 repo 大小與 snapshot 還原方式。青鳥的選擇是第四列：warm pool 中的實例只帶 base 映像，取用後再掛載 repo snapshot，這樣一個 pool 就能服務 120 個 repo；只有三個最熱門的 repo 在尖峰時段各自保留一兩台已掛好 snapshot 的實例。warm pool 中的實例都是「尚未使用」的乾淨實例，這是第 17 章的 sandbox 原則：預熱的是空白的機器，不是用過的機器。

## 43.10 深入四：平行任務與衝突

週三的事故是兩個任務改同一個檔案。第 20 章已經說明，branch 與 worktree 能防止互相干擾，但不能保證一致；這個平台的每個任務本來就在自己的 sandbox 與 `agent/` 分支上工作，所以不會有 lost update，真正的問題是兩個 PR 在合併時衝突，或者文字上不衝突、語意上衝突。

處理分成三道。第一道在 **scheduler**：任務開始前，用 issue 內容與程式碼搜尋預測「可能會改哪些檔案」，如果和進行中的任務重疊很高，就讓後來的任務排隊等前一個開出 PR，或者在任務中註明「另一個任務正在修改 pricing.ts，完成後請 rebase」。這只是預測，不是鎖，所以只用來排序，不用來保證正確。第二道在 **PR 服務**：開 PR 之前先 rebase 到最新的主分支、重跑驗證；如果 rebase 有衝突，任務回到 RUNNING，讓 agent 在最新程式碼上重做，而不是由 agent 自動挑一邊。第三道在**合併**：使用 merge queue，讓每個 PR 在「主分支加上排在它前面的所有 PR」的狀態下再跑一次測試，這是抓語意衝突最可靠的一層。

還有一種平行是刻意的：同一張 issue 同時跑多個 attempt，挑最好的那個，常稱為 **best-of-n**。它能提高困難任務的成功率，但成本直接乘以 n，reviewer 也要面對「哪一個比較好」的選擇。青鳥的政策是只在工程師明確要求、或 issue 被標為高優先且第一次嘗試失敗時才開 n=2，而且由驗證層與 review agent 先排序，只把最好的一個開成 PR。

> [!warning] 常見誤解
> 「agent 速度快，衝突就讓它自己解決。」agent 解決衝突時看不到另一個 PR 背後的意圖，常常挑了文字上合理、語意上錯誤的一邊。合理的分工是：agent 只能在自己的分支上 rebase 並重做自己的修改，絕不修改別人的 PR；兩個意圖真正衝突時，交給人裁決。

## 43.11 深入五：驗證與 reward hacking 防範

週二的事故最危險，因為它看起來是成功。**reward hacking**（獎勵投機）是指 agent 去滿足「被量測的那個指標」，而不是指標背後的目的：目的是修好 bug，指標是測試通過，最省力的路就是改測試。agent 不需要有惡意，只要它被訓練或提示成「讓測試通過」，改測試就是一條會被找到的路。常見形式包括改寫或刪除既有斷言、把測試標成 skip、針對測試輸入寫特例、修改 CI 或覆蓋率門檻，以及偽造輸出。第 34 章把它列為可靠性的主要失敗模式之一。

```text
 agent 的 diff
   │
   ├─(1) 在乾淨 sandbox 重放：從 base commit 套用 diff，重新安裝、重新建置
   │
   ├─(2) 確定性檢查：build、lint、型別、完整測試（agent 看不到驗證環境）
   │
   ├─(3) diff 政策：既有斷言不可刪改、不可新增 skip、不可改 CI 與 golden 檔
   │
   ├─(4) fail-to-pass：新增的測試必須在 base 上失敗、在 head 上通過
   │
   ├─(5) review agent：只看 issue＋diff＋驗證報告，依 rubric 給意見
   │
   └─(6) 人工 review：看 diff、驗證報告與 trace 連結，決定是否合併
```

這張驗證管線由便宜到昂貴、由確定性到判斷性排列。(1) 在乾淨的 sandbox 重放，讓 agent 對自己環境做的任何手腳都失效。(2) 是最基本的門檻。(3) 的 **diff 政策**是專門防 reward hacking 的確定性規則：測試可以新增，但既有的斷言不能被改寫或刪除；驗證設定不在 agent 的修改範圍。(4) 借用 SWE-bench 的 **fail-to-pass** 概念：一個「修正 bug」的 PR 應該附上一個在修正前失敗、修正後通過的測試，否則這個測試根本沒有重現 bug。(5) **review agent** 是另一個 context 乾淨的模型，只看 issue、diff 與驗證報告，看不到 agent 的推理過程，避免被它的說法說服；它負責抓「改了不相關的檔案」「只修了症狀」這類規則寫不出來的問題。(6) 人永遠是最後一道。這條管線就是第 39 章 **verification gate**（驗證閘門）在平台上的形態：agent 說「已修正」不算完成，必須有驗證服務在乾淨環境中產生的外部證據；harness 結束時若還沒有這份證據，run 的結果記為 `unverified`（不等於 `succeeded`），任務只能由驗證服務決定能不能進入 PR_OPEN。

```python
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FileChange:
    path: str
    removed: list[str]
    added: list[str]
    new_file: bool = False


SKIP = re.compile(r"\.skip\(|\bxit\(|@pytest\.mark\.skip|\.only\(")
ASSERT = re.compile(r"\b(assert|expect)\b")
PROTECTED = ("ci/", ".github/workflows/", "jest.config", "coverage", "tests/fixtures/golden/")


def review_diff(changes: list[FileChange]) -> list[tuple[str, str]]:
    """確定性的 diff 政策：block＝直接退回，human＝放行但要求人特別看。"""
    out = []
    for c in changes:
        is_test = "/tests/" in f"/{c.path}" or c.path.endswith((".test.ts", "_test.py"))
        if any(c.path.startswith(p) or p in c.path for p in PROTECTED):
            out.append(("block", f"{c.path}：驗證設定與 golden 檔不在 agent 的修改範圍"))
        if is_test and not c.new_file and any(ASSERT.search(line) for line in c.removed):
            out.append(("block", f"{c.path}：刪除或改寫了既有斷言 {c.removed[0].strip()!r}"))
        if any(SKIP.search(line) for line in c.added):
            out.append(("block", f"{c.path}：新增 skip／only，等於關掉測試"))
        if c.path.endswith(("package-lock.json", "pnpm-lock.yaml")):
            out.append(("human", f"{c.path}：相依套件變更，需要人確認來源"))
    return out


def fail_to_pass(new_test, base_impl, head_impl) -> str:
    """新加的測試要在修正前失敗、修正後通過，才證明它真的抓到這個 bug。"""
    def passes(impl) -> bool:
        try:
            new_test(impl)
            return True
        except AssertionError:
            return False
    if passes(base_impl):
        return "無效：測試在修正前就通過，沒有重現 bug"
    return "有效：修正前失敗、修正後通過" if passes(head_impl) else "修正不完整：修正後仍失敗"


diff = [
    FileChange("src/refund.ts", ["return amount"], ["return Math.round(amount * 100)"]),
    FileChange("src/refund.test.ts", ["  expect(toCents(5)).toBe(500)"], ["  expect(toCents(5)).toBe(5)"]),
    FileChange("src/shipping.test.ts", [], ["describe.skip('flaky eta', () => {"]),
    FileChange("ci/pipeline.yml", ["  coverage_min: 80"], ["  coverage_min: 0"]),
    FileChange("package-lock.json", ["..."], ["..."]),
]
for level, msg in review_diff(diff):
    print(f"[{level:>5}] {msg}")

base, head = (lambda a: a), (lambda a: round(a * 100))
def good_test(f): assert f(5) == 500
def weak_test(f): assert f(0) == 0                   # 0 元換算成分還是 0：修正前也會過
print("good_test:", fail_to_pass(good_test, base, head))
print("weak_test:", fail_to_pass(weak_test, base, head))
levels = [lv for lv, _ in review_diff(diff)]
assert levels.count("block") == 3 and levels.count("human") == 1
assert fail_to_pass(weak_test, base, head).startswith("無效")
```

```text
[block] src/refund.test.ts：刪除或改寫了既有斷言 'expect(toCents(5)).toBe(500)'
[block] src/shipping.test.ts：新增 skip／only，等於關掉測試
[block] ci/pipeline.yml：驗證設定與 golden 檔不在 agent 的修改範圍
[human] package-lock.json：相依套件變更，需要人確認來源
good_test: 有效：修正前失敗、修正後通過
weak_test: 無效：測試在修正前就通過，沒有重現 bug
```

這段程式示範 (3) 與 (4)。第一個 FileChange 是正常的修正，沒有任何發現；第二個把預期值從 500 改成 5，正是週二的事故，被標成 block；第三個加了 `describe.skip`，第四個把覆蓋率門檻改成 0，也都被擋下；lockfile 變更不算錯，但標成 human，提醒 reviewer 確認新套件的來源。下半段的 `weak_test` 檢查「0 元換算成分是 0」，修正前後都會通過，所以 fail-to-pass 判定它無效：這種測試讓 CI 變綠，卻什麼也沒證明。

規則有誤判的代價。有些 issue 本來就是「測試寫錯了」，這時改既有斷言是正確的修改。處理方式不是放寬規則，而是讓 intake 在 issue 被標為「修正測試」時，在任務中明確授權可修改哪些測試檔，diff 政策依任務授權判斷；沒有授權卻改了，就退回並說明。退回的訊息要具體，讓 agent 下一輪知道該怎麼改，這和第 4 章「錯誤訊息要可行動」是同一件事。

## 43.12 深入六：成本控制

43.3 節的估算說明 token 是最大的成本項目，週四的事故則說明成本失控的典型樣子：不是平均成本高，而是長尾。控制成本要在三個層級同時做：任務開始前、執行中、以及整個平台。

| 手段 | 作用的位置 | 省下什麼 | 風險 |
|---|---|---|---|
| intake 適合度篩選 | 開始前 | 註定失敗的 session | 篩太嚴會擋掉可以做的任務 |
| 每任務 token 與 sandbox 時間預算 | 執行中 | 長尾失控任務 | 預算太緊，困難任務做不完 |
| 無進展偵測 | 執行中 | 「改一行、跑全部測試」的迴圈 | 合理的反覆測試被誤判 |
| 只跑相關測試，最後才跑全部 | 執行中 | sandbox 時間、tool 輸出 tokens | 漏掉間接影響，由驗證層補 |
| 穩定前綴與 prompt caching | 每次呼叫 | 大部分的 input token 成本 | 中途改 system 或 tool 順序就失效 |
| compaction 與 tool 輸出清除 | 長任務 | context 長度 | 摘要遺漏關鍵約束（第 10 章） |
| 小型快速模型做探索與摘要 | 執行中 | 單價 | 品質下降，要用 eval 驗證 |
| 團隊每日配額與 kill switch | 平台 | 整體上限 | 配額用完時要有清楚的通知 |

這張表由上到下，從「不要開始」到「開始了也要停得住」。最有效的一列常常是第一列：一張描述不清的 issue 交給 agent，它會花完預算去猜，產生一個沒人想合併的 PR；在 intake 用小模型判斷「資訊是否足夠」並請人補充，成本只有一次小呼叫。第三列的**無進展偵測**直接對應週四的事故：連續若干步程式碼沒有變、或測試結果沒有改善，就提示 agent 換方法，再不行就停下並回報。它比第 4 章的重複呼叫偵測多看一個維度：同一個測試指令重跑是合理的，但「程式碼與測試結果都沒變」才是迴圈。

模型路由要特別注意 cache。第 25 章談過，換模型會讓前綴快取全部失效，所以切換點最好選在本來就要重建 context 的時候，例如 compaction 之後或 subagent 的邊界。預算的計算以 task store 的成本帳為準，每一步寫入時就依有版本的價目表計算（第 29 章的慣例），PR 上顯示這個任務的總成本，讓工程師對「什麼樣的 issue 值得交給 agent」形成直覺。

## 43.13 深入七：可觀測性

background agent 沒有人在旁邊看，所以可觀測性是「事後重建發生了什麼」的唯一手段。每個任務是一條 trace：最外層是 `invoke_agent` span，底下是每次模型呼叫的 `chat` span 與每次 tool 執行的 `execute_tool` span，依第 29 章的慣例，span status 只記技術成敗，業務結果記在 `bluebird.*` 屬性，例如 `bluebird.task.status`、`bluebird.verify.findings`、`bluebird.pr.merged`。trace 連結附在 PR 上，reviewer 可以直接看到 agent 讀了哪些檔案、跑了哪些指令、哪一步被驗證退回。

```text
 指派 300 ─► 通過 intake 270 ─► 開出 PR 205 ─► 合併 165 ─► 14 天內未 revert 158
             （30 請人補充）    （65 FAILED／ESCALATED）（40 被關閉）   （7 被 revert）

 每一段的流失原因都要能從 trace 分類：
   intake：資訊不足｜超出範圍｜權限不足
   執行：預算用完｜無進展｜驗證連續失敗｜基礎設施錯誤
   審查：方向錯｜品質不足｜重複｜reviewer 自己改比較快
```

這個漏斗是平台最重要的儀表板，數字是試辦期的形狀示意。最終指標是最右邊的「合併且未被 revert」，它對應 43.2 節對「完成」的定義；中間每一段的流失都要能分類，才知道該改 intake、harness、驗證還是 tool。第一個常見陷阱是只看「開出 PR 的比例」：驗證放太鬆時這個數字會上升，但合併率會下降，reviewer 的時間被浪費。第二個陷阱是把基礎設施錯誤（sandbox 開機失敗、鏡像站逾時）和 agent 失敗混在一起，前者是 SRE 的問題，後者才是模型與 harness 的問題。

營運指標另外包括：開始動工的 p95 延遲、warm pool 命中率、佇列長度、sandbox 利用率、每個合併 PR 的成本、每個任務的 token 分布（看長尾）、egress 被拒絕的次數（可能是 injection 的徵兆），以及 reviewer 處理一個 agent PR 的時間。告警要對準使用者感受得到的症狀，例如「開始動工 p95 超過 2 分鐘」或「egress 拒絕次數突增」，而不是每一台 sandbox 的 CPU。

## 43.14 擴展與取捨

深入完元件，面試官會問：「如果規模變成十倍呢？」十倍之後，每日約 3,000 張任務，依 Little's law 尖峰平均約 250 台 sandbox 同時在忙（agent 約 200 台、驗證約 50 台）、input TPM 約 29M。第一個撞牆的通常不是 sandbox，而是模型配額，所以 model gateway 要有跨供應商或跨區域的容量，並對每個團隊做 token bucket 式的配額；scheduler 的准入控制要同時看 sandbox 容量與模型配額，兩者取較緊的一邊。第二個是 repo cache：snapshot 的建置與分發要做成區域化的，讓 sandbox 從同一區域的儲存還原。第三個是 task store，它要能水平擴展；以 repo 或團隊做分片是自然的切法，因為衝突偵測與並行上限本來就以 repo 為單位。

| 取捨 | 選項 A | 選項 B | 青鳥的選擇與理由 |
|---|---|---|---|
| harness 放哪 | sandbox 內（簡單，一台機器就是一個任務） | sandbox 外（大腦與手分離） | 外面：憑證不進 sandbox，sandbox 可丟棄 |
| sandbox 範圍 | 每任務一台 | 每 repo 長駐 | 每任務一台：不跨任務殘留 |
| 驗證位置 | agent 自己的 sandbox | 獨立乾淨的 sandbox | 獨立：agent 無法影響驗證環境 |
| 驗證深度 | 只跑相關測試，快 | 完整測試＋review agent，慢 | PR 前完整驗證：reviewer 時間比機器時間貴 |
| 平行嘗試 | 單一 attempt | best-of-n | 預設單一，高優先失敗時才 n=2 |
| 自建或購買 | 自建在自家雲 | 採用託管的 cloud coding agent | 先買後建：用託管產品驗證需求，再自建差異化部分 |

這張表的最後一列值得多談。主流 coding agent 產品都已經提供「把 issue 指派給 agent、在雲端環境產生 PR」的形態，對大多數公司而言，第一步應該是買，用真實的合併率與成本驗證需求。自建的理由通常是三種：程式碼與資料不能離開自家環境、需要和內部工具深度整合（自家的 issue tracker、權限系統、部署流程），或者要用 `loom` 跑自己調整過的 harness 與模型路由。即使自建，sandbox 層也常常用託管服務，因為隔離技術是最不該自己發明的部分。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各產品公開文件與 engineering blog 整理（功能與限制變動很快，請以官方文件為準）：GitHub 的 Copilot coding agent（文件已改稱 Copilot cloud agent）可從 issue 指派啟動，在 GitHub Actions 的臨時環境中執行，單次工作有 59 分鐘的硬上限（可在 `copilot-setup-steps.yml` 以 `timeout-minutes` 縮短），每個任務對應一個分支與一個 PR，可在 PR 留言要 agent 繼續修改，branch protection 可能擋住它的推送，預設啟用 GitHub MCP 與 Playwright MCP。Anthropic 的 Claude Managed Agents（beta，2026-04）公開描述 brain／hands／session 分離：harness 無狀態、可由 session 恢復，容器掛掉時以 tool error 呈現再重新配置，並表示改成只在需要 tool 時才配置容器後，p50 TTFT 約降 60%、p95 降超過 90%；其憑證在結構上不可達 sandbox，git token 只在初始化 clone 時使用。Claude Code 可在本機或雲端（Anthropic 的 VM 或自架環境）執行。OpenAI Codex 提供 cloud 執行與可重用的 cloud environments，並有把升權請求交給 reviewer agent 的 auto-review 模式。Cursor 公開了 cloud agents 可在自管機器上執行（2026-09）等更新。Cognition 的 Devin Fusion 以前沿模型為主、便宜模型為輔，並選在 compaction 時切換模型以避免額外的 cache 懲罰。NIST CAISI 在 2025-12 發表了關於 agent 評測作弊的研究〈Cheating On AI Agent Evaluations〉。

## 43.15 面試官追問與回答

前面是候選人主導的部分，最後二十分鐘通常是面試官的追問。以下是老陳在審查中實際問的問題，以及 Iris 整理後的回答。每一題都可以先講結論，再講判斷依據與取捨。

**追問 1：為什麼不把 harness 放進 sandbox，一台機器搞定？** 放進去確實簡單，但 harness 需要模型金鑰、任務狀態與預算控制，這些都會變成 sandbox 裡的程式讀得到的東西。放在外面之後，sandbox 只拿到 `execute(tool, args)`，裡面沒有任何值得偷的憑證；sandbox 掛掉也只是一次 tool error，harness 換一台就能繼續。代價是每次 tool 呼叫多一跳網路延遲，相對於模型呼叫的延遲可以忽略。

**追問 2：warm pool 要開幾台？** 用 Little's law 算平均忙碌數，用到達的波動決定餘裕。warm pool 的大小不是「平均忙碌數」，而是「在補一台新的開機完成之前，可能湧入幾個任務」：大約是尖峰到達率乘以開機時間，再加上幾台應付突發。43.16 節的模擬中，每分鐘 0.8 個任務、開機 45 秒，保留 2 台就有九成以上命中，保留 6 台則幾乎全命中，但閒置成本是將近四倍。上班時段保持幾台、夜間縮到零，用排程而不是固定值。

**追問 3：issue 內容含 prompt injection 怎麼辦？** 不靠模型識破它，而是讓它成功了也做不了什麼。sandbox 沒有對外網路、沒有憑證、不能推送；agent 能造成的最大傷害是一個惡意的 diff，而這個 diff 要經過 diff 政策、review agent 與人工 review 才可能合併。另外在 intake 標記 issue 的來源（內部工程師、客戶回報、外部貢獻者），來源越不可信，任務的權限越小，例如不允許修改相依套件。

**追問 4：測試不穩定（flaky）會怎樣影響這個系統？** flaky 測試會讓驗證隨機失敗，agent 會試圖「修」一個與它無關的失敗，甚至把它 skip 掉。驗證服務要維護一份已知 flaky 測試的清單，失敗時先在 base commit 上重跑同一個測試：base 上也失敗，就標成「與本次修改無關」，不算 agent 的失敗，也不回饋給 agent 要它修。

**追問 5：如果 reviewer 說「方向錯了」，agent 怎麼接手？** reviewer 的留言觸發一個新的 revision 任務，context 包含原 issue、目前的 diff、所有 review 留言與上一輪的交接筆記（第 10 章的六段式摘要）。如果留言是「整個方向錯了」，比較好的做法是從 base 重新開始而不是在錯的 diff 上修補，這可以由 review 留言的分類決定。revision 次數也有上限，超過就請人接手。

**追問 6：怎麼知道平台真的有幫助？** 看漏斗最右端的「合併且未被 revert」與每個合併 PR 的成本，並和人工處理同類 issue 的時間比較。還要量 reviewer 的負擔：如果 reviewer 花在 agent PR 上的時間比自己修還多，平台就是在轉嫁成本。上線新模型或新 prompt 前，用已合併的內部 PR 回推題目做離線 eval（第 28 章），上線後用 A/B 比較合併率。

**追問 7：一個任務跑到一半，scheduler 所在的機器重啟了，會發生什麼？** 任務狀態在 task store，lease 有到期時間。harness 若還活著，會繼續 heartbeat 續約；若 harness 也掛了，lease 到期後任務回到 QUEUED，新的 harness 依 session log 接手或從 base 重做。舊 harness 若晚醒來想寫入，會因 fencing token 過期被拒絕。PR 建立用 idempotency key（任務 id 加上 diff 的 hash），所以重試不會開出第二個 PR。

**追問 8：monorepo 很大，snapshot 不夠快怎麼辦？** 先用 sparse checkout 與 partial clone，只取任務相關的目錄；建置快取用內容定址的遠端快取，讓 sandbox 下載而不是重建。更進一步是讓 snapshot 包含記憶體狀態，例如已經啟動的語言伺服器與已經預熱的測試執行器，還原後馬上可用。這些都要守住同一條線：快取由可信的 builder 寫入，任務只讀。

**追問 9：多個團隊搶資源時，公平性怎麼做？** 單純 FIFO 會讓一個一次指派五十張 issue 的團隊佔滿 pool。scheduler 對每個團隊設並行上限與每日 token 配額，佇列以團隊為單位輪流取任務（類似 weighted fair queuing），高優先任務可以插隊但不能搶走正在跑的 sandbox。配額用完的團隊，任務繼續排隊並收到通知，而不是被靜默丟棄。

**追問 10：agent 需要的套件不在鏡像站裡怎麼辦？** 不能為了它開放公網。任務會以「需要新的相依套件」的狀態停下，或在 PR 中說明需要的套件，由人決定是否加進鏡像站。這看起來慢，但新增相依套件本來就是要人審查的供應鏈決定；agent 自己從公網裝套件，等於讓 issue 的作者決定你的供應鏈。

**追問 11：怎麼避免 agent 把 secrets 寫進 PR？** sandbox 裡本來就沒有 secrets，這是第一道。第二道是 PR 服務在推送前掃描 diff，比對 secret 的特徵與已知憑證的指紋；第三道是 git server 端的 push protection。三道都是確定性的檢查，不依賴模型判斷。

**追問 12：這個設計哪裡最可能出錯？** Iris 的回答是驗證層的品質。整個平台的可信度建立在「驗證通過的 PR 值得 review」，而驗證的上限就是測試的品質：測試涵蓋不到的地方，agent 的修改就沒有被檢查。所以平台的一部分預算要投資在測試本身，例如讓 agent 專門為缺乏測試的模組補測試，經人 review 後成為之後任務的驗證基礎。老陳補了一句：「verifier 決定上限，這句話在 coding agent 上最明顯。」

## 43.16 動手做：模擬 sandbox pool 排程與任務生命週期

動手做分兩個實驗。實驗一用離散事件模擬 sandbox pool，比較冷啟動、repo snapshot、warm pool 與容量上限的效果，並驗證 Little's law；實驗二把 43.6 節的狀態機實作出來，用 ScriptedModel 扮演 agent，走過正常、改測試被擋、sandbox 當機與連續走捷徑四種情境。

### 實驗一：warm pool、排隊與 Little's law

模擬的規則和 43.7 與 43.9 節一致：每個任務獨佔一台 sandbox，用完即銷毀，絕不回到 warm；warm pool 只補「全新」的實例，開機需要 45 秒；準備 repo 的時間在 snapshot 時是 20 秒，完整 clone 加安裝則是 300 秒。到達是每分鐘 0.8 個的 Poisson 過程，工時是中位數 18 分鐘的長尾分布，五種設定使用同一個 seed，看到的是完全相同的任務。

```python
from __future__ import annotations

import heapq
import math
import random
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Config:
    name: str
    capacity: int          # 同時存在的 sandbox 上限（含開機中、待命、使用中）
    min_warm: int          # warm pool 至少保留幾台「開好、還沒用過」的乾淨實例
    boot_s: float          # 冷啟動：開一台 microVM 的秒數
    prep_s: float          # 開機後準備 repo：snapshot 還原約 20 秒，完整 clone＋安裝約 300 秒


@dataclass
class Stats:
    waits: list[float] = field(default_factory=list)       # 任務從進入佇列到 agent 開始工作
    sojourn: list[float] = field(default_factory=list)     # 任務在系統內的總時間 W
    warm_hits: int = 0
    area_in_system: float = 0.0                            # ∫ 系統內任務數 dt，用來算時間平均 L
    area_idle: float = 0.0                                 # ∫ 待命 sandbox 數 dt：warm pool 的成本
    area_busy_steady: float = 0.0                          # 只算第 1～6 小時（避開一早從零開始的暖身期）
    service: list[float] = field(default_factory=list)     # 每個任務實際佔用 sandbox 的秒數


def simulate(cfg: Config, lam_per_min: float, hours: float, seed: int = 43) -> tuple[Stats, float, int]:
    rng = random.Random(seed)                              # 同一個 seed：每種設定看到完全相同的到達與工時
    mu, sigma = math.log(18), 0.81                         # 工時：中位數 18 分鐘的 lognormal，長尾截在 60 分鐘
    arrivals, t = [], 0.0
    while True:
        t += rng.expovariate(lam_per_min / 60)
        if t > hours * 3600:
            break
        arrivals.append((t, min(rng.lognormvariate(mu, sigma), 60) * 60))   # 租期上限 60 分鐘

    events: list[tuple[float, int, str, int]] = []         # (時間, 序號, 種類, 任務編號)
    seq = 0
    def push(when: float, kind: str, tid: int = -1) -> None:
        nonlocal seq
        heapq.heappush(events, (when, seq, kind, tid)); seq += 1

    for i, (at, _) in enumerate(arrivals):
        push(at, "arrive", i)
    st = Stats()
    queue: list[int] = []
    warm, booting, busy, in_system = 0, 0, 0, 0
    arrived_at: dict[int, float] = {}
    now = 0.0

    def total() -> int:
        return warm + booting + busy

    def refill(at: float) -> None:                         # 維持 min_warm 台待命（開機中的也算），但不超過上限
        nonlocal booting
        while warm + booting < cfg.min_warm + len(queue) and total() < cfg.capacity:
            booting += 1
            push(at + cfg.boot_s, "booted")

    def start(tid: int, at: float, hit: bool) -> None:     # 取得一台 sandbox：準備 repo 後開始工作
        nonlocal busy
        busy += 1
        st.warm_hits += hit
        st.waits.append(at + cfg.prep_s - arrived_at[tid])
        st.service.append(cfg.prep_s + arrivals[tid][1])
        push(at + cfg.prep_s + arrivals[tid][1], "done", tid)

    warm = cfg.min_warm                                    # 上班前先把 pool 暖好
    while events:
        when, _, kind, tid = heapq.heappop(events)
        dt = when - now
        st.area_in_system += in_system * dt
        st.area_idle += warm * dt
        st.area_busy_steady += busy * max(0.0, min(when, hours * 3600) - max(now, 3600))
        now = when
        if kind == "arrive":
            in_system += 1
            arrived_at[tid] = now
            if warm:                                       # warm 命中：不用等開機
                warm -= 1
                start(tid, now, hit=True)
            else:
                queue.append(tid)
        elif kind == "booted":
            booting -= 1
            if queue:
                start(queue.pop(0), now, hit=False)
            else:
                warm += 1
        elif kind == "done":                               # 用完即銷毀，絕不回到 warm
            busy -= 1
            in_system -= 1
            st.sojourn.append(now - arrived_at[tid])
        refill(now)
        if not queue and not busy and not booting and now > hours * 3600:
            break
    return st, now, len(arrivals)


def pad(s: str, width: int) -> str:                       # 中文字佔兩格，對齊表格用
    return s + " " * (width - sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s))


def p95(xs: list[float]) -> float:
    s = sorted(xs)
    return s[int(0.95 * (len(s) - 1))]


LAM, HOURS = 0.8, 6                                        # 尖峰：每分鐘 0.8 個任務，持續 6 小時
configs = [
    Config("A 冷啟動＋完整 clone", capacity=40, min_warm=0, boot_s=45, prep_s=300),
    Config("B 冷啟動＋snapshot", capacity=40, min_warm=0, boot_s=45, prep_s=20),
    Config("C warm 2＋snapshot", capacity=40, min_warm=2, boot_s=45, prep_s=20),
    Config("D warm 6＋snapshot", capacity=40, min_warm=6, boot_s=45, prep_s=20),
    Config("E 同 D，上限 22", capacity=22, min_warm=6, boot_s=45, prep_s=20),
]
print(f"到達率 λ = {LAM}/分鐘，尖峰 {HOURS} 小時，同一組到達與工時")
print(f"{pad('設定', 22)}任務 warm命中  等待p50  等待p95   L量測    λ×W 穩態忙碌  閒置sbx·h")
res = {}
for cfg in configs:
    st, horizon, n = simulate(cfg, LAM, HOURS)
    W = sum(st.sojourn) / len(st.sojourn)                  # 平均停留時間（秒）
    L = st.area_in_system / horizon                        # 時間平均的系統內任務數
    lam_hat = n / horizon
    busy = st.area_busy_steady / ((HOURS - 1) * 3600)
    waits = sorted(st.waits)
    res[cfg.name[0]] = dict(L=L, lw=lam_hat * W, busy=busy, p95=p95(waits), hit=st.warm_hits / n,
                            S=sum(st.service) / n)
    print(f"{pad(cfg.name, 22)}{n:>4}{st.warm_hits / n:>9.0%}{waits[n // 2]:>8.0f}s{p95(waits):>8.0f}s"
          f"{L:>8.2f}{lam_hat * W:>7.2f}{busy:>9.1f}{st.area_idle / 3600:>10.1f}")

# (1) Little's law：系統開始與結束都是空的，所以 L = λW 是恆等式（面積 = 所有任務停留時間的總和）
for r in res.values():
    assert abs(r["L"] - r["lw"]) / r["lw"] < 1e-6
# (2) 拿來估容量：穩態時忙碌的 sandbox 數 ≈ λ × 每任務平均佔用時間 S
S = res["D"]["S"] / 60
pred = LAM * S
print(f"\n每任務平均佔用 S = {S:.1f} 分；λ×S = {pred:.1f} 台，模擬穩態忙碌 = {res['D']['busy']:.1f} 台")
assert abs(res["D"]["busy"] - pred) / pred < 0.15
# (3) warm pool 把等待壓到只剩 repo 準備時間；上限貼近 λ×S 時，排隊時間暴增
assert res["D"]["hit"] > 0.95 and res["D"]["p95"] < res["B"]["p95"] < res["A"]["p95"]
assert res["E"]["p95"] > 5 * res["D"]["p95"]
print(f"上限 22 台時利用率約 {pred / 22:.0%}，等待 p95 從 {res['D']['p95']:.0f}s 變成 {res['E']['p95']:.0f}s")
```

```text
到達率 λ = 0.8/分鐘，尖峰 6 小時，同一組到達與工時
設定                  任務 warm命中  等待p50  等待p95   L量測    λ×W 穩態忙碌  閒置sbx·h
A 冷啟動＋完整 clone   296       0%     345s     345s   19.96  19.96     22.4       0.0
B 冷啟動＋snapshot     296       0%      65s      65s   16.88  16.88     18.7       0.0
C warm 2＋snapshot     296      93%      20s      31s   16.40  16.40     18.7      10.3
D warm 6＋snapshot     296     100%      20s      20s   16.38  16.38     18.7      38.1
E 同 D，上限 22        296      64%      20s     359s   17.08  17.08     18.6      21.3

每任務平均佔用 S = 23.1 分；λ×S = 18.5 台，模擬穩態忙碌 = 18.7 台
上限 22 台時利用率約 84%，等待 p95 從 20s 變成 359s
```

先看「等待」兩欄，它是任務從進入佇列到 agent 開始工作的時間。設定 A 每個任務都要開機 45 秒加完整 clone 300 秒，所以等待固定是 345 秒；B 改用 snapshot，降到 65 秒；C 保留 2 台 warm，93% 的任務直接拿到開好的機器，只剩 20 秒的 snapshot 掛載，p95 也只有 31 秒；D 保留 6 台則全部命中。代價在最後一欄：D 的閒置 sandbox 時數是 38.1，是 C 的將近四倍，這就是追問 2 說的「warm pool 大小由開機時間內的湧入量決定，再多就是付錢買閒置」。

「L 量測」與「λ×W」兩欄完全相同，這不是巧合：模擬從空系統開始、到空系統結束，所以「系統內任務數對時間的積分」恰好等於「每個任務停留時間的總和」，這正是 Little's law 的證明核心，程式用 assert 鎖住了它。它在設計上的用途是倒過來用：已知到達率與每個任務的佔用時間，就能推出平均需要幾台。最後一行顯示，每任務平均佔用 23.1 分鐘時，λ×S 預測 18.5 台，模擬的穩態忙碌數是 18.7 台，誤差很小。注意 A 的穩態忙碌數是 22.4，比其他設定多了將近 4 台：完整 clone 不只讓使用者多等，那 300 秒也佔著 sandbox，直接吃掉容量。

設定 E 是最有教育意義的一列。它和 D 一樣保留 6 台 warm，只是上限從 40 降到 22，看起來仍比平均忙碌數 18.5 多了兩成。結果 warm 命中率掉到 64%，等待 p95 從 20 秒變成 359 秒，因為利用率約 84% 時，到達的波動與工時的長尾會讓 sandbox 經常全部被佔滿，新任務只能排隊。這就是 43.3 節乘上 1.6 倍餘裕的理由：平均值決定成本，餘裕決定延遲。

### 實驗二：任務生命週期狀態機、驗證閘門與冪等 PR

第二個實驗把 43.6 節的狀態機、43.11 節的 diff 政策與 追問 7 的冪等 PR 組在一起。harness 在 sandbox 的檔案副本上跑 agent loop；驗證把結果拿到另一份乾淨的副本上檢查；PR 服務用任務 id 加上 diff 的 hash 當作 idempotency key。

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
    stop_reason: str = "end_turn"
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


class ScriptedModel:
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
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    return ModelResponse(text=text)


# ── 任務狀態機：合法轉移寫成資料，任何不在表上的轉移一律拒絕 ──
TRANSITIONS = {
    "QUEUED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"VERIFYING", "QUEUED", "FAILED", "CANCELLED"},       # QUEUED：sandbox 掛了，lease 過期重排
    "VERIFYING": {"RUNNING", "PR_OPEN", "ESCALATED"},                # RUNNING：驗證失敗，帶回饋再改
    "PR_OPEN": {"MERGED", "CLOSED", "QUEUED"},                       # QUEUED：reviewer 要求修改
}
TERMINAL = {"MERGED", "CLOSED", "FAILED", "CANCELLED", "ESCALATED"}


@dataclass
class Task:
    id: str
    state: str = "QUEUED"
    attempt: int = 1
    revisions: int = 0
    log: list[str] = field(default_factory=list)

    def to(self, new: str, why: str) -> None:
        if new not in TRANSITIONS.get(self.state, set()):
            raise ValueError(f"{self.id}: 不合法的轉移 {self.state} → {new}")
        self.log.append(f"{self.state:>9} → {new:<9} {why}")
        self.state = new


# ── 假 repo：base 版本有 bug（金額沒有換算成分），測試檔已存在 ──
BASE = {
    "src/refund.py": "def to_cents(amount):\n    return amount\n",
    "tests/test_refund.py": "assert to_cents(5) == 500\n",
}

def run_tests(files: dict[str, str]) -> bool:                       # 模擬在乾淨環境執行測試
    env: dict[str, Any] = {}
    exec(files["src/refund.py"], env)
    try:
        for name, src in files.items():
            if name.startswith("tests/"):
                exec(src, dict(env))
        return True
    except AssertionError:
        return False


def guard(base: dict[str, str], head: dict[str, str]) -> list[str]:
    """驗證閘門的確定性檢查：測試只能新增，不能改寫或刪除既有的 assert。"""
    problems = []
    for path, old in base.items():
        if path.startswith("tests/"):
            kept = [line for line in old.splitlines() if line.startswith("assert")]
            missing = [line for line in kept if line not in head.get(path, "")]
            if missing:
                problems.append(f"{path} 改寫或刪除了既有斷言：{missing[0]}")
    return problems


def harness(task: Task, model: ScriptedModel, files: dict[str, str], feedback: str, max_steps: int = 6):
    """在 sandbox 內跑 agent loop；files 是這台 sandbox 裡的工作副本，sandbox 銷毀就消失。"""
    messages = [{"role": "user", "content": f"修正 {task.id}：退款金額要換算成分。{feedback}"}]
    for _ in range(max_steps):
        resp = model.complete(messages)
        messages.append({"role": "assistant", "content": resp.text,
                         "tool_calls": [tc.__dict__ for tc in resp.tool_calls]})
        if not resp.tool_calls:
            return files
        for tc in resp.tool_calls:
            if tc.name == "crash":                                     # 模擬 sandbox 被回收或 OOM
                raise ConnectionError("sandbox lost")
            if tc.name == "write_file":
                files[tc.args["path"]] = tc.args["content"]
            out = ("PASS" if run_tests(files) else "FAIL") if tc.name == "run_tests" else "ok"
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
    raise TimeoutError("步數預算用完")


PRS: dict[str, str] = {}                                             # PR 服務：以 idempotency key 去重

def open_pr(task: Task, head: dict[str, str]) -> str:
    key = task.id + ":" + hashlib.sha256(json.dumps(head, sort_keys=True).encode()).hexdigest()[:8]
    return PRS.setdefault(key, f"PR-{len(PRS) + 101}")


def drive(task: Task, episodes: list[list], review: ScriptedModel, retry_pr: bool = False) -> str | None:
    files, feedback = dict(BASE), ""
    for script in episodes:
        if task.state == "QUEUED":
            files = dict(BASE)                                         # 新 sandbox：從 base commit 重新開始
            task.to("RUNNING", f"attempt {task.attempt}：取得乾淨 sandbox")
        try:
            files = harness(task, ScriptedModel(script), files, feedback)
        except ConnectionError:
            task.attempt += 1
            task.to("QUEUED", "lease 過期：舊 sandbox 銷毀，重新排隊")
            continue
        task.to("VERIFYING", "把 diff 套到另一台乾淨 sandbox 驗證")
        problems = guard(BASE, files) or ([] if run_tests(files) else ["測試未通過"])
        if not problems:                                               # 確定性檢查都過了，才請 review agent
            verdict = json.loads(review.complete([{"role": "user", "content": json.dumps(files)}]).text)
            problems = [] if verdict["approve"] else [verdict["reason"]]
        if not problems:
            pr = open_pr(task, files)
            if retry_pr:                                               # PR 建好、狀態還沒寫回就當機，重試
                assert open_pr(task, files) == pr
            task.to("PR_OPEN", f"{pr}，通知指派的工程師 review")
            return pr
        task.revisions += 1
        if task.revisions >= 2:
            task.to("ESCALATED", "連續兩次驗證失敗，交給人：" + problems[0])
            return None
        feedback = "驗證回饋：" + problems[0]
        task.to("RUNNING", feedback)
    task.to("FAILED", "重試次數用盡")
    return None


FIX = "def to_cents(amount):\n    return round(amount * 100)\n"
HACK = "assert to_cents(5) == 5\n"
approve = lambda: ScriptedModel([say('{"approve": true, "reason": ""}')])

def fix_after_feedback(messages: list[dict]) -> ModelResponse:      # 讀到驗證回饋才改走正路
    assert "既有斷言" in messages[0]["content"]
    return call("write_file", path="src/refund.py", content=FIX)

runs = {
    "A 正常路徑": (Task("ISSUE-311"), [[call("write_file", path="src/refund.py", content=FIX),
                                     call("run_tests", "c2"), say("已修正")]], approve(), False),
    "B 改測試被擋": (Task("ISSUE-312"), [
        [call("write_file", path="tests/test_refund.py", content=HACK), call("run_tests", "c2"), say("測試全過")],
        [call("write_file", "c3", path="tests/test_refund.py", content=BASE["tests/test_refund.py"]),
         fix_after_feedback, call("run_tests", "c5"), say("已修正並還原測試")]], approve(), False),
    "C sandbox 當機": (Task("ISSUE-313"), [[call("crash")],
                     [call("write_file", path="src/refund.py", content=FIX), say("已修正")]], approve(), True),
    "D 一再走捷徑": (Task("ISSUE-314"), [
        [call("write_file", path="tests/test_refund.py", content=HACK), say("測試全過")],
        [call("write_file", path="tests/test_refund.py", content="pass\n"), say("移除過時的測試")]],
        approve(), False),
}
for name, (task, episodes, review, retry) in runs.items():
    pr = drive(task, episodes, review, retry)
    if name.startswith("A"):
        task.to("MERGED", "工程師 approve 後由人合併")
    print(f"── {name}（{task.id}）")
    print("\n".join("   " + line for line in task.log))

t = {name[0]: v[0] for name, v in runs.items()}
assert t["A"].state == "MERGED" and t["B"].state == "PR_OPEN" and t["B"].revisions == 1
assert t["C"].attempt == 2 and len([k for k in PRS if k.startswith("ISSUE-313")]) == 1
assert t["D"].state == "ESCALATED"

e = Task("ISSUE-315")
e.to("CANCELLED", "工程師在排隊時取消")
try:
    e.to("RUNNING", "遲到的 worker 想接手")
except ValueError as err:
    print("── E 取消後\n   " + str(err))
assert all(x.state in TERMINAL | {"PR_OPEN"} for x in [*t.values(), e])
print(f"PR 服務共建立 {len(PRS)} 個 PR：{sorted(PRS.values())}")
```

```text
── A 正常路徑（ISSUE-311）
      QUEUED → RUNNING   attempt 1：取得乾淨 sandbox
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → PR_OPEN   PR-101，通知指派的工程師 review
     PR_OPEN → MERGED    工程師 approve 後由人合併
── B 改測試被擋（ISSUE-312）
      QUEUED → RUNNING   attempt 1：取得乾淨 sandbox
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → RUNNING   驗證回饋：tests/test_refund.py 改寫或刪除了既有斷言：assert to_cents(5) == 500
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → PR_OPEN   PR-102，通知指派的工程師 review
── C sandbox 當機（ISSUE-313）
      QUEUED → RUNNING   attempt 1：取得乾淨 sandbox
     RUNNING → QUEUED    lease 過期：舊 sandbox 銷毀，重新排隊
      QUEUED → RUNNING   attempt 2：取得乾淨 sandbox
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → PR_OPEN   PR-103，通知指派的工程師 review
── D 一再走捷徑（ISSUE-314）
      QUEUED → RUNNING   attempt 1：取得乾淨 sandbox
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → RUNNING   驗證回饋：tests/test_refund.py 改寫或刪除了既有斷言：assert to_cents(5) == 500
     RUNNING → VERIFYING 把 diff 套到另一台乾淨 sandbox 驗證
   VERIFYING → ESCALATED 連續兩次驗證失敗，交給人：tests/test_refund.py 改寫或刪除了既有斷言：assert to_cents(5) == 500
── E 取消後
   ISSUE-315: 不合法的轉移 CANCELLED → RUNNING
PR 服務共建立 3 個 PR：['PR-101', 'PR-102', 'PR-103']
```

逐一看四個情境。**A 正常路徑**走完 QUEUED → RUNNING → VERIFYING → PR_OPEN，最後由人合併；注意 MERGED 這一步是在 harness 之外由「工程師」觸發的，程式裡沒有任何路徑讓 agent 自己合併。**B 改測試被擋**重現週二的事故：第一輪 agent 把斷言改成 `== 5`，自己跑測試得到 PASS，宣稱「測試全過」；驗證閘門比對 base 與 head 的測試檔，發現既有斷言 `assert to_cents(5) == 500` 不見了，於是退回 RUNNING 並附上具體回饋。第二輪的劇本是一個函式，它先 assert 自己收到的指示裡有「既有斷言」這個回饋，才還原測試並修正程式，模擬「agent 讀了回饋後改走正路」。

**C sandbox 當機**中，第一個 attempt 執行到一半 sandbox 消失，任務從 RUNNING 回到 QUEUED、attempt 變成 2，第二次從 base commit 在新的 sandbox 上重做，而不是沿用舊環境。這個情境還開啟了 `retry_pr`：模擬「PR 已經建立、狀態還沒寫回就當機」，重試時用同一個 idempotency key 拿回同一個 PR，所以最後只有 PR-103 一個。**D 一再走捷徑**的 agent 第一次改斷言、第二次乾脆把測試換成 `pass`，兩次都被擋，達到 revision 上限後進入 ESCALATED，交給人處理，而不是無限重試。最後的 E 示範狀態機的防護：任務被取消之後，遲到的 worker 想把它改回 RUNNING，轉移表直接拒絕。

這兩個實驗刻意省略了很多東西：真實的 diff 是行級的，測試會很慢，review agent 會給出有理由的意見，PR 要 rebase。但它們鎖住了這個平台最重要的幾個不變式：驗證在 agent 碰不到的地方做、既有斷言不能被改、sandbox 不重用、PR 不重複、終態不能被改回來。這些不變式寫成 assert 後，之後任何重構都不能悄悄破壞它們。

## 43.17 實務應用

**情境一：青鳥的內部 issue-to-PR 平台（本章主線）**。最後上線的設計是：intake 用小型快速模型篩選，資訊不足的 issue 自動留言請人補充；每任務一台 microVM，egress 只到鏡像站與唯讀 git；harness 在外面跑 `loom`，PR 由 GitHub App 身分建立；驗證在獨立 sandbox 跑完整測試、diff 政策與 review agent。上線前兩個月只開放給三個團隊、只接受標為「good-for-agent」的 issue，類型集中在型別錯誤、測試補強、小型 bug 與相依套件升級，等漏斗數據穩定後才擴大。主流產品的對應做法很類似：公開文件中，GitHub 的 Copilot coding agent 從 issue 指派啟動、在臨時環境中工作、每個任務一個分支與一個 PR，並受 branch protection 約束。

**情境二：大規模遷移與相依套件升級**。例如把上百個模組從舊的 HTTP client 換成新的，或在所有 repo 升級某個有安全漏洞的套件。這類工作的特點是任務數量多、彼此獨立、驗證標準明確，非常適合平行的 background agent。設計重點在 scheduler：每個 repo 的並行上限要低（避免一次開出幾十個互相 rebase 的 PR），按相依順序排程，並用同一份「遷移說明」當作所有任務的共用指示，讓每個 PR 的風格一致。公開資料中，GitHub 也把 coding agent 用在安全修補的批次活動（security campaign）上，入口和一般 issue 指派相同。

**情境三：受監管產業的自託管部署**。金融或醫療機構的程式碼不能離開自家環境，模型也可能必須透過私有端點使用。這時架構不變，但每一層都要放進自家雲：sandbox 用自家叢集上的 microVM，model gateway 指向私有端點，trace 與 session log 的保存期限與存取權限依稽核要求設定，PR 上的代理鏈要能對應到員工身分。主流產品在 2026 年也陸續提供讓 cloud agent 在自管機器或自架環境執行的選項，詳見 43.14 節的 2026 現況。

**情境四：開源專案的維護者助手**。開源專案的 issue 來自任何人，injection 風險最高，所以 agent 的權限要更小：只能讀公開程式碼、只能開 draft PR、不能觸發需要 secrets 的 CI。驗證特別依賴 fail-to-pass：維護者最在意的是「這個 PR 真的重現並修好了回報的問題」。這也是 SWE-bench 系列 benchmark 的任務形態，第 28 章討論過它與真實內部任務之間的落差。

| 情境 | 任務特性 | 設計重點 | 主要風險 |
|---|---|---|---|
| 內部 issue-to-PR | 異質、中小型 | intake 篩選、完整驗證、漏斗指標 | reviewer 負擔、reward hacking |
| 大規模遷移 | 大量、獨立、標準明確 | 每 repo 並行上限、共用指示、依序排程 | PR 洪水、互相 rebase |
| 受監管自託管 | 與內部相同 | 每層自託管、稽核與保存期限 | 自建隔離層的品質 |
| 開源維護者助手 | 不可信輸入 | 最小權限、draft PR、fail-to-pass | prompt injection、供應鏈 |

這張表顯示，四個情境的元件幾乎相同，差別在於旋鈕的位置：輸入越不可信，權限越小；任務越多越獨立，scheduler 越重要；部署環境越受限，自建的比例越高。

## 43.18 設計檢查清單

1. 「完成」是否定義為「PR 被合併且一段時間內未被 revert」，而不是 agent 宣告完成或 CI 通過？
2. agent 的權限邊界是否寫成可檢查的規則：只能推送到 `agent/` 分支、不能合併、不能修改 CI 與驗證設定？
3. 是否用 Little's law 從尖峰到達率與每任務佔用時間推出 sandbox 上限，並保留足夠餘裕（利用率不超過約七成）？
4. 模型配額（TPM、RPM）是否和 sandbox 容量一起規劃，scheduler 的准入是否兩者都看？
5. harness 與模型金鑰是否在 sandbox 之外？sandbox 掛掉時，任務能否由 session log 恢復？
6. sandbox 是否每任務一台、用完即銷毀，warm pool 中只有尚未使用的實例？
7. egress 是否預設拒絕，只開放套件鏡像站與唯讀 git，並封鎖雲端 metadata 端點？
8. git 寫入憑證是否只在 PR 服務手上，並以短效、限定 repo 的 App 身分取得？
9. repo snapshot 是否只由可信的 builder 寫入，任務 sandbox 只能讀取？版本鍵是否包含 lockfile hash 與工具鏈版本？
10. 驗證是否在獨立的乾淨 sandbox 中重放 diff，而不是信任 agent 自己的測試結果？
11. diff 政策是否擋下刪改既有斷言、新增 skip、修改 CI 與覆蓋率設定？是否有 fail-to-pass 檢查？
12. 每任務是否有 token 與 sandbox 時間預算、無進展偵測與 revision 上限，超過時進入 ESCALATED 並留言說明？
13. PR 建立是否以 idempotency key 去重，狀態機是否拒絕不合法的轉移？
14. 漏斗的每一段流失是否都能從 trace 分類，並區分基礎設施錯誤與 agent 失敗？

## 43.19 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 早上開工時段任務排隊數十分鐘 | 冷啟動加完整 clone，或上限貼近平均忙碌數 | 看開始動工延遲的分解：排隊、開機、repo 準備 | repo snapshot、warm pool；依 Little's law 加餘裕 |
| CI 綠燈但 PR 沒修好問題 | agent 改了測試或寫了無效的測試 | 比對 base 與 head 的測試檔；跑 fail-to-pass | diff 政策擋下刪改斷言；要求 fail-to-pass |
| 同一張 issue 出現兩個 PR | 重試時重新建立 PR，沒有去重 | 查 PR 服務的建立紀錄與任務 attempt | 以任務 id 加 diff hash 作為 idempotency key |
| 單一任務成本是平均的數十倍 | 沒有無進展偵測，反覆跑全部測試 | 看 trace 中程式碼與測試結果是否連續不變 | 每任務預算、無進展偵測、只跑相關測試 |
| 兩個 PR 合併後功能壞掉 | 語意衝突：文字不衝突但假設不一致 | 在合併後的主分支重跑測試 | merge queue；開 PR 前 rebase 並重新驗證 |
| egress 拒絕次數突然增加 | issue 或相依套件中的 injection，或新的合法需求 | 依任務與目的地分組查看 proxy 紀錄 | 確認是攻擊就隔離任務；合法需求走審查加入 allowlist |
| 所有任務的 token 成本同時上升 | 改了 system prompt 或 tool 順序，cache 失效 | 比較變更前後的 cache 命中率 | 穩定前綴；變更集中在版本發布時 |
| 驗證隨機失敗、agent 去改無關的測試 | flaky 測試 | 在 base commit 上重跑同一個測試 | 維護 flaky 清單；base 也失敗時不算 agent 失敗 |

## 本章重點整理

- background coding agent 的「完成」應定義為「PR 被合併且未被 revert」，成功指標、驗證與成本都要從這個定義推導。
- 需求釐清要先確定 autonomy 邊界：agent 在 sandbox 與自己的分支內 L4，合併、部署與修改 CI 一律由人決定。
- Little's law（L = λW）讓你從尖峰到達率與每任務佔用時間推出並行 sandbox 數；容量要在平均值之上保留餘裕，否則等待時間會在利用率升高時急遽惡化。
- 估算顯示 token 成本遠大於 sandbox 運算成本，所以成本控制的主戰場是 context、cache 與失控長尾；sandbox 時間的價值主要在延遲與容量。
- 模型配額常常比 sandbox 更早成為瓶頸，scheduler 的准入要同時看兩者。
- 把 harness 放在 sandbox 外，sandbox 只執行 tool；這讓憑證不進 sandbox，sandbox 也成為可丟棄的資源。
- sandbox 每任務一台、用完即銷毀；egress 只開放鏡像站與唯讀 git，git 寫入只由 PR 服務以短效 App 身分執行。
- 開始動工的延遲由 warm pool、repo snapshot 與增量 fetch 分段處理，snapshot 只能由可信的 builder 寫入，以防 cache poisoning。
- 平行任務靠分支隔離避免互相覆蓋，靠 scheduler 的衝突預測、開 PR 前 rebase 與 merge queue 處理衝突；agent 不替別人的 PR 解衝突。
- reward hacking 的防線是確定性的：在獨立 sandbox 重放 diff、禁止刪改既有斷言與 skip、fail-to-pass 檢查，再加上 review agent 與人工 review。
- 任務生命週期是 durable 的狀態機，合法轉移寫成資料；lease、fencing 與 idempotency key 讓當機與重試不會造成重複的 PR 或過期的寫入。
- 可觀測性的核心是從指派到「合併且未 revert」的漏斗，每段流失都要能從 trace 分類，並區分基礎設施錯誤與 agent 失敗。
- 大多數組織應先採用託管產品驗證需求，自建的理由是資料不能離開環境、需要深度整合，或要跑自己的 harness 與模型路由。

## 延伸問答

> [!question]- Q1. 估算題：如果每日任務數不變，但每個 session 的平均佔用時間從 25 分鐘變成 40 分鐘，sandbox 上限與成本各會怎麼變？
> 依 Little's law，平均忙碌數與佔用時間成正比：尖峰到達率仍是每分鐘約 0.81 個，agent sandbox 的平均忙碌數從約 20 台變成約 32 台，加上驗證約 5 台，乘上 1.6 倍餘裕後，上限要從 40 台提高到約 60 台。sandbox 運算成本也大致增加五成，但它本來就只佔總成本的一小部分。
>
> token 成本要看佔用時間為什麼變長。如果是因為模型呼叫次數變多（任務變難、迴圈變長），token 成本會跟著接近線性上升，而且因為每次呼叫的 context 也變長，可能比線性更快；如果是因為測試變慢，token 幾乎不變。所以估算之後的第一個動作是拆解時間：多出來的 15 分鐘花在模型思考、tool 執行還是排隊，三者的對策完全不同。

> [!question]- Q2. 為什麼驗證要在另一台乾淨的 sandbox 重放 diff，而不是直接採用 agent 在自己 sandbox 裡跑出來的測試結果？
> agent 的 sandbox 是它可以任意修改的環境。它可能改了快取、裝了不同版本的套件、在背景留下 process、設定了只在這台機器上存在的環境變數，甚至直接改了測試執行器的設定。在這個環境裡得到的 PASS，只能證明「在被 agent 改過的環境裡會過」，不能證明 diff 本身是對的。
>
> 在乾淨的 sandbox 從 base commit 套用 diff 重跑，等於只承認 diff 這一個產出，其他一切都重新建立。這也讓 verifier 和 agent 在結構上分開：agent 看不到驗證環境，也無法影響它。代價是多一台 sandbox 與幾分鐘的時間，在估算中約佔總 sandbox 時間的兩成，相對於 reviewer 被一個假的綠燈誤導的代價，非常便宜。

> [!question]- Q3. warm pool 裡為什麼不能放「用過但清理乾淨」的 sandbox？清理不是比重新開機快嗎？
> 清理確實可能更快，但「乾淨」很難被證明。一個任務可能在暫存目錄留下檔案、在背景啟動 process、修改 shell 設定或 git 設定、在快取目錄放了被修改過的套件；任何一項沒清到，下一個任務就會在被污染的環境裡執行，而且下一個任務可能屬於另一個團隊、另一個 repo。這正是第 17 章規定 sandbox 不跨任務重用的原因。
>
> 重新開機的延遲問題，應該用「預熱全新的實例」來解決，而不是回收舊的。warm pool 中的實例都是從映像新開的、尚未被任何任務使用過，取用後再掛載 repo snapshot；搭配 snapshot 還原技術，開機時間可以壓到秒級。這樣在延遲上接近回收，在安全上保持「每台只服務一個任務」的簡單保證。

> [!question]- Q4. 你在 production 看到 PR 合併率從 55% 掉到 35%，但開出 PR 的比例反而上升，你會怎麼排查？
> 這個組合通常代表「驗證變鬆了，或任務變難了」。開出 PR 的比例上升，表示更多任務通過了驗證；合併率下降，表示 reviewer 不認同這些 PR。第一步是看時間點：是否剛好換了模型、改了 prompt、調整了 diff 政策或 review agent 的 rubric。換模型後 agent 更積極地「讓測試通過」，是很常見的原因。
>
> 第二步是抽樣被關閉的 PR，依漏斗的分類標記原因：方向錯、品質不足、重複、reviewer 自己改比較快。如果「方向錯」變多，問題可能在 intake，例如新開放的團隊指派了大量描述不清的 issue；如果「品質不足」變多，問題在驗證，例如 fail-to-pass 被關掉或新加了缺乏測試的 repo。第三步是確認不是 reviewer 行為改變，例如新團隊的 reviewer 標準不同。找到原因後，把代表性案例加進離線 eval，避免回歸。

> [!question]- Q5. 面試追問：同一個 repo 一次湧入 30 張 issue，你的 scheduler 會怎麼處理？
> 先不要全部同時跑。scheduler 對每個 repo 有並行上限，例如 5 個，其餘排隊；排隊的順序除了優先級，還要看衝突預測：用 issue 內容與程式碼搜尋估計每個任務可能修改的檔案，和進行中任務重疊高的往後排，彼此獨立的先跑。這樣能減少後續 PR 互相 rebase 的次數。
>
> 這 30 張如果來自同一個團隊，團隊的並行上限與每日 token 配額也會生效，避免它擠掉其他團隊。對使用者要誠實：intake 留言時告訴對方目前排在第幾位、預估何時開始，而不是只說「已接手」。如果這是一次性的大規模遷移，更好的做法是改走遷移模式：先由一個任務產出共用的遷移說明與範例 PR，人確認後再平行展開，讓所有 PR 的風格一致。

> [!question]- Q6. 程式找錯：下面的 PR 服務在重試時會出什麼問題？
> ```python
> def open_pr(task, diff):
>     pr = github.create_pull_request(branch=f"agent/{task.id}-{uuid4()}", body=diff.summary)
>     store.update(task.id, state="PR_OPEN", pr=pr.number)
>     return pr
> ```
> 第一個問題是沒有冪等性。分支名稱裡有 `uuid4()`，每次呼叫都不同；如果 `create_pull_request` 成功後、`store.update` 之前 process 當機，任務仍停在 VERIFYING，重試時會用新的分支名稱再開一個 PR，同一張 issue 就有兩個 PR。正確做法是用任務 id 加上 diff 內容的 hash 推導出固定的分支名稱與 idempotency key，建立前先查詢是否已存在，存在就直接回傳。
>
> 第二個問題是狀態轉移沒有檢查目前狀態與 fencing token。如果這個任務已經被取消，或 lease 已經轉給另一個 worker，這段程式仍會開 PR 並把狀態改成 PR_OPEN。寫入 store 時要帶上預期的目前狀態與 fencing token，不符就拒絕，並關閉剛剛建立的 PR。這和 43.16 節狀態機拒絕 CANCELLED → RUNNING 是同一件事。

> [!question]- Q7. 自建與購買怎麼選？如果青鳥最後選擇購買託管的 cloud coding agent，本章哪些設計仍然要自己做？
> 判斷依據有三個：程式碼與資料能不能離開自家環境、需要和內部系統整合多深、是否需要控制 harness 與模型。對多數公司，第一步買託管產品最划算，因為 sandbox、warm pool、repo 快取與 PR 整合都已經做好，能在幾週內用真實數據回答「合併率與每個合併 PR 的成本是否值得」。
>
> 即使購買，仍有幾件事是平台本身做不到、必須自己負責的：「完成」的定義與漏斗指標（產品只會告訴你開了多少 PR）、哪些 repo 與 issue 類型開放給 agent、branch protection 與 CODEOWNERS 規則、diff 政策中和自家程式碼規範相關的部分、測試品質與 flaky 清單、egress allowlist 與鏡像站的內容，以及預算與配額政策。換句話說，買的是基礎設施，治理與驗證標準仍然是自己的。

> [!question]- Q8. 為什麼 review agent 只看 issue、diff 與驗證報告，而不看 coding agent 的完整 trajectory？看得越多不是判斷得越準嗎？
> review agent 的價值在於它是一個獨立的視角。如果它讀了 coding agent 的推理過程，就會被同一套說法影響：「這個測試本來就過時了，所以我更新了預期值」聽起來很合理，看完推理的 reviewer 容易接受。只看 diff 與 issue，review agent 會直接問：issue 要求的是修正金額換算，為什麼測試的預期值變了？這和人類 code review 只看 PR、不看作者寫程式時的思路是同一個道理。
>
> 第二個理由是 context 成本與 injection 範圍。trajectory 可能長達數十萬 tokens，裡面包含 issue 原文、tool 輸出與相依套件的內容，這些都可能夾帶誘導文字；review agent 的輸入越精簡，被誘導的面越小，成本也越低。需要更多資訊時，可以讓它請求特定檔案的內容，而不是一次全給。最後，review agent 只是輔助，它的意見寫在 PR 上給人看，不是合併的決定者。

## 延伸閱讀

- Little, J. D. C.〈A Proof for the Queuing Formula: L = λW〉（Operations Research，1961）
- Jimenez et al.〈SWE-bench: Can Language Models Resolve Real-World GitHub Issues?〉（ICLR 2024）
- GitHub Docs〈About Copilot coding agent〉（現稱 Copilot cloud agent）
- Anthropic Engineering Blog 關於 Claude Managed Agents 架構（brain、hands 與 session 分離）的文章（2026-04）
- Anthropic〈How we contain Claude across products〉（2026-05）
- NIST CAISI〈Cheating On AI Agent Evaluations〉（2025-12）
- Cognition〈Don't Build Multi-Agents〉（2025）
