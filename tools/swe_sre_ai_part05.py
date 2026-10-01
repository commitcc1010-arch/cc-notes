"""Part 5: SRE foundations, SLOs, observability, alerting, and capacity."""
from __future__ import annotations

from swe_sre_ai_model import C


CHAPTERS = [
    C(
        30,
        "Production Environment、Operations 與 SRE",
        "SRE 和傳統維運、DevOps、平台工程有何關係？為什麼只是把工程師加入值班仍不夠？",
        "入門",
        "以使用者可靠性與長期工程改善為中心，分清 service ownership、operations work 和 SRE 方法。",
        ["sre", "service", "production", "ownership"],
        """
Production 需要部署、監控、容量、事故、權限、資料保護和支援。若團隊只靠人手逐項操作，服務成長會帶來線性 toil；若開發者把部署後問題完全交給另一組，設計也不會收到真實 feedback。SRE 的重點是用軟體工程、量測和共同 incentives 改善營運系統，而不只是換職稱。
""",
        """
一個服務每週因記憶體洩漏重啟。Operations 每次快速處理但問題持續；SRE 會先建立可靠偵測與安全重啟，再分析 heap、修復 leak、加入 regression test 和 capacity guard，使未來事件量下降。
""",
        r"""
Product / service team
  ├─ feature & architecture ownership
  └─ production responsibility
            ↕ shared SLO / error budget
SRE / platform
  ├─ reliability engineering
  ├─ automation / observability / capacity
  ├─ incident practices
  └─ reusable platform & standards

manual response → understand pattern → engineer system → fewer future events
""",
        """
Operations 是維持服務運行所需的活動；DevOps 常指開發與營運共同責任的文化與方法；SRE 是一種具體實作：由具軟體工程能力的團隊管理 availability、latency、performance、change、monitoring、emergency 和 capacity，並限制手動 toil 以保留工程時間。平台工程則把常見能力做成自助產品。實際組織可重疊，重點是 contract 而非名稱。

Service team 不應因有 SRE 就放棄 production ownership。SRE 需要有權要求可靠性工作、停止危險發布或退出無法持續的 engagement；產品團隊仍需修 code、理解 domain 和承擔 roadmap。共享 SLO/error budget 能避免一方只追 feature、另一方只追零變更。

SRE 工作應產生槓桿：自動化、簡化、capacity model、reliable release、incident learning 和 platform。手動操作有時必要，尤其在未知事故，但之後要問能否消除、降低頻率或讓一般 on-call 安全處理。若 SRE 永遠充當 ticket queue，就失去工程目的。
""",
        [
            "明確定義 service owner、SRE engagement、on-call 和 escalation 的責任。",
            "用 SLI/SLO/error budget 對齊可靠性與發布，而非抽象爭論。",
            "追蹤 operation work 與 engineering work，保留改善長期系統的 capacity。",
            "將重複事故轉成 code、automation、platform、test 或 design change。",
            "定期檢查 engagement 是否仍有槓桿；沒有共同承諾時調整或退出。",
        ],
        "用分類函式區分純操作與具有長期槓桿的工程工作。真實任務可能同時包含兩者，應按實際時間拆分。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Work:
    repeated: bool
    manual: bool
    scales_with_service: bool
    reduces_future_work: bool

def classify(work: Work) -> str:
    if work.repeated and work.manual and work.scales_with_service:
        return "toil"
    if work.reduces_future_work:
        return "engineering"
    return "operations"

print(classify(Work(True, True, True, False)))
print(classify(Work(False, False, False, True)))
""",
        [
            "重複、手動、隨服務線性成長是 toil 的強 signals。",
            "修 automation 或架構能減少未來工作，屬工程投資。",
            "一次性 incident response 可能是 operations，但其 follow-up 可成為 engineering。",
            "分類目的是調整資源與系統，不是貶低必要的操作工作。",
        ],
        [
            "把所有 manual work 都稱為 toil，會忽略需要判斷與學習的高價值操作。",
            "SRE 成為產品團隊的永久 ticket queue，無時間做根因改善。",
            "只用 uptime 衡量 SRE，可能鼓勵禁止變更而非建立安全 delivery。",
            "平台沒有使用者研究與 SLO，會把下游團隊綁在另一個不可靠服務。",
        ],
        """
AI-SRE 能搜尋 telemetry、整理事件、執行標準 runbook 和產生修復候選，最適合降低資訊整理與重複診斷 toil；它不會自動解決 service ownership 和 incentives。導入順序應從唯讀調查、建議、需批准操作，再到可逆低風險自治。每次 AI 操作仍由具名 service/SRE owner 承擔，且要留下 evidence 和 audit。
""",
        [
            "讓 AI 彙整 logs、metrics、traces、changes 和相似 incidents，建立 investigation brief。",
            "用 agent 執行唯讀 health checks 與 runbook 導航，縮短 context gathering。",
            "請 AI 將重複 tickets 聚類，找值得 automation/platform 投資的 toil。",
            "讓 agent 草擬 code fix、test 和 postmortem action，由 owners review。",
        ],
        [
            "Production agent 預設 read-only，mutation 使用專用 identity、最小 scope 和 approval。",
            "每個結論連回原始 telemetry/change，不接受無 evidence 的 root-cause 宣告。",
            "操作有 step/time/resource budget、idempotency、rollback 和 kill switch。",
            "量人工接管、錯誤建議、policy violation 和 incident impact，不只量省下時間。",
        ],
        """
Domain expert 會區分「讓操作更快」和「讓操作不再需要」。AI 很容易把 ticket 處理自動化，卻讓根本架構問題繼續存在。高槓桿 SRE 仍會投資簡化、可靠 release、capacity 和 service design；Agent 是執行與資訊介面，不是可靠性策略本身。
""",
        [
            "列出團隊一週 operations tasks，依 toil/operations/engineering 分類並估時間。",
            "執行分類範例，為灰色任務補上『是否需要人類 judgment』維度。",
            "為 product/SRE 寫 engagement contract：SLO、ownership、toil、退出條件。",
            "設計 AI-SRE autonomy ladder，為每級列 allowed actions、evidence 和 approval。",
        ],
        [
            ("SRE 最簡潔的定義是什麼？", "用軟體工程方法設計與營運可靠 production 系統，將操作經驗轉成可重複的 automation、platform 和 architecture。"),
            ("DevOps、SRE、platform 是否互斥？", "不互斥。DevOps 偏文化/原則，SRE 是具體可靠性實作，platform 提供自助能力；組織可依情境重疊。"),
            ("為何 service team 不能把 production 全交給 SRE？", "Domain design 和 feature changes 決定大部分風險；沒有共同 ownership，開發得不到 feedback，SRE 也無法單方面修所有根因。"),
            ("手動工作何時不是 toil？", "一次性、需要高判斷、帶來學習或不隨服務線性成長時；但仍可檢查是否能降低風險與負擔。"),
            ("AI-SRE 最安全的起點？", "唯讀 context gathering、資料關聯、runbook 導航和建議，先評估 precision 與人類使用方式，再逐步授權。"),
            ("為什麼只量 AI 節省時間不足？", "錯誤建議、額外 review、風險、接管和事故可能把成本轉移；需同看品質、policy、stability 和使用者結果。"),
            ("SRE engagement 何時應改變？", "當服務成熟度、SLO、toil、owner commitment 或組織優先級改變；若只剩 ticket 處理且無改善空間，應重新談 contract。"),
        ],
        ["sre-intro", "sre-toil", "sre-engagement", "google-agentic-sre"],
    ),
    C(
        31,
        "Toil、Automation 與逐步取得自治",
        "哪些重複工作應自動化？為什麼錯誤流程自動化後，通常只是更快造成事故？",
        "中階",
        "以頻率、風險、穩定性和可驗證性排序 toil，從 runbook 到 deterministic automation 再到 bounded agent。",
        ["toil", "feedback", "agent", "least-privilege"],
        """
Automation 有建置和維護成本，也會把一個人的錯誤放大到所有機器。若流程尚未理解、例外很多或結果難驗證，立即全自動化會把 tacit judgment 隱藏在脆弱 script。另一方面，長期重複手動工作消耗人力、產生不一致並讓服務無法成長。
""",
        """
團隊每天手動擴容：看 queue depth、計算 replicas、修改 config、觀察。先將計算與 dry-run 自動化，再建立 bounds 和 rollback，最後才讓 controller 自動執行；直接讓 agent 讀 dashboard 後自由修改整個 cluster 風險過高。
""",
        r"""
observe manual work
        ↓
document decision / inputs / exceptions
        ↓
assistive tool (read-only / recommendation)
        ↓
deterministic script + dry-run
        ↓
approval + bounded mutation
        ↓
closed-loop automation with SLO / rollback
        ↓
agent only where semantic ambiguity remains
""",
        """
先量 toil：頻率、每次時間、成長率、錯誤率、認知中斷和 on-call 影響。優先處理高頻、高風險且規則穩定的工作。自動化前先寫 inputs、decision、outputs、exceptions 和 verification；若無法說明正確結果，automation 也無法可靠判斷。

成熟度從輔助到閉環。Read-only tool 收集資訊；推薦系統由人核准；deterministic script 有 dry-run、idempotency 和 bounds；controller 根據明確 signal 自動動作並觀察回饋。Agent 適合補足語意解讀、跨工具協調和長尾，但應把危險 action 留在 policy-checked tools。

Automation 需要 ownership、SLO 和 escape hatch。當環境異常或 signal 不可信時，系統要 fail safe、停止並升級，而不是持續重試。每次人工 override 都是 feedback：若頻繁出現，模型或規則需要更新。
""",
        [
            "量 toil 的頻率、時間、風險、成長與中斷成本，建立優先序。",
            "先讓人工流程穩定且可說明，再分離收集、決策、執行和驗證。",
            "從 read-only/dry-run 開始，加入 idempotency、bounds、approval 和 rollback。",
            "閉環 automation 監控 action 結果，signal 不可信時停止並升級。",
            "追蹤 overrides、failures 和 avoided work，持續修正或刪除 automation。",
        ],
        "以下 autoscaler 只計算建議並限制每次變動。Mutation 可由另一個受控元件在核准後執行。",
        r"""
from math import ceil

def desired_replicas(
    queue_depth: int,
    capacity_per_replica: int,
    current: int,
    minimum: int = 2,
    maximum: int = 50,
    max_step: int = 5,
) -> int:
    raw = ceil(queue_depth / capacity_per_replica)
    bounded = min(maximum, max(minimum, raw))
    return min(current + max_step, max(current - max_step, bounded))

print(desired_replicas(4200, 200, current=10))
""",
        [
            "計算與執行分離，容易 dry-run、review 和測試。",
            "Min/max 限制絕對範圍，`max_step` 限制單次 blast radius。",
            "真實 controller 還要 cooldown、health、quota、cost 和 delayed feedback。",
            "若 `capacity_per_replica` 過時，應停止或保守降級，而非盲目縮放。",
        ],
        [
            "自動化不穩定流程會把例外與錯誤以機器速度擴散。",
            "只算節省工時，不計 maintenance、false action 和 incident 成本。",
            "無 idempotency 的重試會重複建立資源或執行副作用。",
            "Automation owner 離開後無人理解，工具本身變成新的 toil 和風險。",
        ],
        """
AI agents 能處理傳統 automation 難以編碼的語意步驟，但機率性也增加變異。最佳 pattern 是 agent 決定『建議呼叫哪個高層 tool 及參數』，tool broker 用 schema、policy、bounds 和 identity 驗證，再執行 deterministic action。自治權由 eval、shadow mode、歷史 precision 和可逆性逐步取得。
""",
        [
            "用 AI 將自然語言 ticket 轉成標準 runbook/automation parameters。",
            "讓 agent 在 read-only mode 收集 evidence 並產生 dry-run change plan。",
            "對長尾 exceptions 使用 AI 分類，穩定 pattern 再轉 deterministic code。",
            "在 shadow mode 比較 agent 建議與人類決策，建立自治 evidence。",
        ],
        [
            "Tool broker 驗證 schema、identity、resource scope、bounds 和 policy。",
            "所有 mutation 有 idempotency key、preview、audit、rollback 和最大 action 數。",
            "Agent 遇到 conflicting/missing telemetry 必須停止升級，不能猜測補值。",
            "高風險或不可逆操作永遠要求人類批准與 separation of duties。",
        ],
        """
Automation maturity 不是從 script 直接跳到全自治。專家會把可確定部分盡量 deterministic，讓 agent 只處理真正需要語意的狹窄區域。最好的 toil elimination 有時是刪除需求、簡化產品或修 upstream design，而不是為錯誤流程建更聰明的機器人。
""",
        [
            "建立 toil backlog，以年工時、風險、規則穩定性和可驗證性排序。",
            "執行 autoscaler，測零容量、負 queue、突然降載等 invalid inputs。",
            "將一個 runbook 拆成 observe/decide/act/verify，標記可 deterministic 的步驟。",
            "設計 agent shadow eval：案例、human baseline、precision、unsafe action 和接管條件。",
        ],
        [
            ("哪些 toil 最適合先自動化？", "高頻、隨規模成長、錯誤代價明確、規則穩定且結果可驗證的工作，通常有最大槓桿。"),
            ("為什麼先做 dry-run？", "分離計算與 mutation，讓人和系統檢查 scope、參數與預期結果，降低首次自動化 blast radius。"),
            ("Closed-loop automation 需要什麼？", "可靠 signal、明確 policy、bounded action、觀察結果、rollback/stop 和 owner；不是只執行一次 script。"),
            ("Agent 與 deterministic automation 如何搭配？", "Agent 處理語意分類和選擇高層 action，deterministic tool 驗證參數、權限與執行，將危險自由度限制在外。"),
            ("頻繁 human override 表示什麼？", "可能 signal 不可信、policy 過時、例外未建模或 automation 使用情境錯誤，是需要調整的 feedback。"),
            ("自動化何時不值得？", "任務低頻低風險、規則快速變、驗證困難，或直接刪除/簡化流程更便宜時。"),
            ("自治權如何逐步取得？", "從 read-only、recommend、dry-run、approve-to-act 到 bounded auto，依 representative eval、shadow 歷史、可逆性和 audit 擴大。"),
        ],
        ["sre-toil", "sre-automation", "google-agentic-sre", "owasp-llm"],
    ),
    C(
        32,
        "SLI、SLO、SLA 與 Error Budget",
        "可靠性如何從『感覺穩定』變成可計算、可告警、能指導發布與投資的產品決策？",
        "中階",
        "從使用者 journey 定義 valid events、good events、窗口與目標，再把允許失敗轉成共同政策。",
        ["sli", "slo", "sla", "error-budget"],
        """
服務團隊若沒有共同可靠性定義，開發者會看 server uptime、使用者看交易成功、管理者看投訴，彼此都可能說自己正確。追求 100% 也不實際：成本極高且會阻止有價值變更。SLO 把使用者結果、允許風險和時間窗口放進同一尺度。
""",
        """
Checkout 有 100 台 server 都在線，但付款 dependency 回 500，使用者仍無法購買。Machine uptime 不是正確 SLI。更好的 event-based SLI 是成功完成的有效 checkout / 所有有效 checkout，並排除明顯 client invalid requests。
""",
        r"""
user journey
   ↓
valid events: 什麼算一次機會？
good events: 什麼結果對使用者夠好？
   ↓
SLI = good / valid
   ↓
SLO = target + window (例如 99.9% / 28d)
   ↓
error budget = valid × (1 - target)
   ↓
burn / policy:
release normally | slow down | reliability work | emergency

SLA = 對外含後果承諾，通常比內部 SLO 寬鬆
""",
        """
SLI 要從使用者入口量測，定義 denominator 尤其重要。Availability 可用成功 events；latency 可定義在 threshold 內的 good events；freshness、correctness 和 durability 也可能是 SLI。不要把所有 server metrics 都稱為 SLI，它們是診斷 signals。

SLO 包含目標與窗口。Rolling window 對近期事件敏感，calendar window 易對帳；可依決策選擇。目標應根據使用者需要、dependency、成本和替代方案，不是競賽九數。比依賴更嚴格卻無 fallback 的 SLO 可能不可達。

Error budget 將允許的不可靠量具體化。政策可依剩餘預算或 burn rate 調整 rollout、可靠性工作與 exception。它不是「故意製造錯誤」或每月一定用完，而是承認變更與完美可靠都有成本。SLA 則是含商業後果的外部承諾，需與 legal/product 合作。
""",
        [
            "從 critical user journeys 列 valid/good events，選接近使用者的 measurement point。",
            "定義窗口、目標、資料延遲、排除規則和 owner，回放歷史資料驗證。",
            "確認 dependency 與 fallback 能支持目標，估算可靠性提升成本。",
            "把 error budget 接到明確 change/reliability policy，而非只做 dashboard。",
            "定期用 incidents、投訴和產品變化重訪 SLI/SLO，避免量錯目標。",
        ],
        "範例計算 event-based SLI、允許 bad events 與已消耗比例。用 Decimal 避免展示時的浮點誤差。",
        r"""
from decimal import Decimal

def error_budget(valid: int, good: int, target: Decimal) -> dict:
    bad = valid - good
    allowed_bad = Decimal(valid) * (Decimal("1") - target)
    consumed = Decimal(bad) / allowed_bad if allowed_bad else Decimal("Infinity")
    return {
        "sli": Decimal(good) / Decimal(valid),
        "bad": bad,
        "allowed_bad": allowed_bad,
        "budget_consumed": consumed,
    }

print(error_budget(1_000_000, 999_200, Decimal("0.999")))
""",
        [
            "99.9% 目標在一百萬 valid events 中允許約一千 bad events。",
            "實際 bad 為八百，消耗 80% budget；剩餘空間可支援風險決策。",
            "若 denominator 包含惡意或 invalid requests，SLI 可能被扭曲，定義需版本化。",
            "低流量服務 event count 少，可能要結合 time-based 或較長窗口。",
        ],
        [
            "選 server uptime 而非 user outcome，得到健康機器卻失敗產品。",
            "目標任意加九，成本大增但使用者未感知差異。",
            "排除規則太寬，把真正服務錯誤標為 client fault。",
            "Error budget policy 只懲罰開發，不提供可靠性投資與跨團隊責任。",
        ],
        """
AI 服務除了 availability/latency，還可能需要 answer quality、groundedness、tool success、policy violation、cost 和 human takeover SLI。品質是機率性且 ground truth 昂貴，可用線上 proxy、抽樣人工 review 和離線 eval 組合。模型更新、prompt、retrieval 和 tools 都是 change，應共用 error budget 與 rollout。
""",
        [
            "讓 AI 協助從使用者旅程草擬 SLI 候選與 denominator edge cases。",
            "對 AI agent 建立 task success、unsafe action、tool error、人工接管和成本 SLI。",
            "用離線 eval、shadow traffic 和線上抽樣校準品質 proxy。",
            "讓 agent 解釋 budget burn 的主要 cohorts/changes，附可追溯 query。",
        ],
        [
            "SLO 定義與風險接受由產品/service owners 決定，模型不能自行調低目標。",
            "LLM-as-judge 需以人類標註校準、版本化並監控 bias/drift。",
            "品質、policy、latency 和 cost 同時觀測，不能只優化回答分數。",
            "AI 指標按 cohort 分析但遵守隱私、樣本量和資料最小化。",
        ],
        """
好 SLO 是決策介面，不是漂亮數字。它應能回答何時 page、何時放慢 rollout、哪個 reliability project 值得做。專家寧願有一個貼近 user journey 且可行動的 SLO，也不要數十個無人使用的九數；AI 系統更要承認品質不確定並設計抽樣與接管。
""",
        [
            "為一個服務寫 valid/good event 定義，列出五個 denominator edge cases。",
            "執行計算器，測 99%、99.9%、99.99% 的 allowed bad 差距。",
            "寫 error-budget policy：正常、快速 burn、耗盡和 exception 四種狀態。",
            "為 AI agent 定義五個 SLI，指出哪個有 ground truth、哪個需 proxy。",
        ],
        [
            ("SLI、SLO、SLA 分別是什麼？", "SLI 是量測事實；SLO 是內部目標與窗口；SLA 是對外含後果/補償的承諾。"),
            ("Denominator 為何關鍵？", "它定義哪些事件是服務機會；排除過多會掩蓋失敗，包含無效流量又會扭曲使用者可靠性。"),
            ("為何 100% 通常不是好目標？", "成本極高、可能阻止有價值變更，且 dependencies/clients 也非完美；應依使用者需求和成本設定。"),
            ("Error budget 如何對齊開發與 SRE？", "將允許風險量化，預算健康時可持續變更，快速燃燒時共同降低風險並投資可靠性。"),
            ("Server CPU 是否是 SLI？", "通常是診斷 metric，不直接代表使用者結果；除非 service contract 本身就是提供 CPU 資源。"),
            ("AI answer quality 如何做 SLI？", "結合可驗證 task result、policy checks、離線 eval、抽樣人工標註與校準 proxy，並版本化 judge。"),
            ("何時應重訪 SLO？", "產品 journey、使用者期待、dependencies、流量、成本或測量方式改變，以及 incidents 顯示 SLO 未代表傷害時。"),
        ],
        ["sre-risk", "sre-slo", "sre-intro", "openai-evals"],
    ),
    C(
        33,
        "Observability：從輸出重建系統內部狀態",
        "Metrics、logs、traces 各回答什麼？如何讓值班者從『系統慢』走到可驗證的故障假設？",
        "中階",
        "建立 signal model、共同 context、structured events 與變更關聯，讓 telemetry 真正支援決策。",
        ["observability", "feedback", "provenance", "agent"],
        """
監控告訴你已知條件是否異常；observability 更關心能否從輸出探索未知內部狀態。若 metrics 無 user context、logs 無 request ID、traces 無 deployment marker，值班者只能在多個工具間猜測。收集更多資料不等於更可觀測，關鍵是問題可回答與因果可串接。
""",
        """
Checkout p99 上升。Metric 顯示何時與哪些 region；trace 找到 80% 時間在 catalog；structured log 顯示只發生於新 schema；change event 對應十分鐘前 rollout。四種 evidence 合起來才形成可反證假設。
""",
        r"""
request / job / action
      ↓ common context: trace_id, service, version, region, tenant-safe cohort
metrics ─→ trend / rate / saturation
logs ───→ discrete event / values / decision
traces ─→ causal path / latency attribution
profiles → resource hot spots
changes ─→ deploy / config / feature / agent action
      ↓
query → hypothesis → experiment/action → observe
""",
        """
Metrics 是聚合時間序列，適合 rate、latency distribution、error、saturation 和 SLO；logs 保存離散事件和決策 context；traces 連接跨服務 spans，顯示關鍵路徑；profiles 找 CPU/memory hot spots；change events 將系統行為和 deploy/config 連接。工具名稱可以不同，問題類型不變。

共同 identifiers 是組合關鍵：trace/request ID、service/version、region、operation、error code 和 safe cohort。Logs 應 structured，避免 parse 自由文字；metrics 控制 label cardinality，避免把 user ID 當 label；traces 使用 sampling，但 errors/high latency 可提高保留。Sensitive fields 需 redaction 和 access control。

Observability 從問題設計，不從「把所有資料收進來」開始。為每個 SLO 與 runbook 列出需要的 diagnosis questions；測試 dashboard 是否能從 symptom 到 owner/action。Telemetry pipeline 也有成本、延遲與 failure，需要 health 和 data quality。
""",
        [
            "從 user journey/SLO 定義需要回答的診斷問題與共同 context。",
            "Metrics 用 distribution/rate；logs 結構化；traces 串因果；changes 明確標記。",
            "控制 cardinality、sampling、retention、redaction 和資料存取。",
            "Dashboard 從 symptom→slice→dependency→change→runbook 設計，而非圖表集合。",
            "以 incident/game day 驗證 telemetry 是否足夠、正確且及時。",
        ],
        "範例建立一致的 structured event，讓 log 與 trace/deployment 可關聯；敏感值不直接記錄。",
        r"""
import json
from datetime import datetime, timezone

def event(trace_id: str, service: str, version: str,
          operation: str, outcome: str, latency_ms: int) -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "service": service,
        "version": version,
        "operation": operation,
        "outcome": outcome,
        "latency_ms": latency_ms,
    }, sort_keys=True)

print(event("tr-7", "checkout", "a1b2c3", "reserve", "timeout", 803))
""",
        [
            "固定 fields 便於 query、aggregation 和 agent tool 使用，不需脆弱 regex。",
            "Version 可將 error 與 rollout 關聯；trace ID 可跨 service 追蹤。",
            "不記 user/payment raw data，必要 cohort 應以 privacy-safe 方式產生。",
            "真實 schema 需版本、required/optional fields 和 ingestion failure monitoring。",
        ],
        [
            "每個 log 都加高基數 label，造成成本與查詢系統過載。",
            "只保留平均 latency，長尾使用者傷害被隱藏。",
            "Telemetry schema 無 owner，服務各自發明欄位，跨系統無法關聯。",
            "把 observability 當事後工具，發布時沒有 version/change marker。",
        ],
        """
AI-SRE 的品質高度依賴 context。Agent observability 除傳統 signals，還需 model/version、prompt/instruction revision、retrieval sources、tool calls、arguments、policy decisions、token/cost、eval 和 human takeover。Agent 回答或動作必須可沿 trace 回到 evidence；若沒有 provenance，流暢 root-cause 敘事反而危險。
""",
        [
            "讓 AI 用結構化 query tools 關聯 metrics、logs、traces、changes 和 topology。",
            "請 agent 產生 hypothesis 時列 supporting、conflicting evidence 和下一個驗證。",
            "對 agent workflow 建 span：model、retrieval、tool、approval、action 和 result。",
            "用 AI 聚類高量 logs/incident traces，找未知 pattern，再由 owner 驗證。",
        ],
        [
            "Agent 只能讀獲批准 telemetry，查詢結果按使用者/tenant ACL 過濾。",
            "保存 tool/evidence links、model/instruction version 和 action audit。",
            "AI 不得以 summary 取代原始 telemetry；關鍵判斷可回看 query/result。",
            "控制 prompt/log 中 secrets、PII、retention 和 cross-tenant data leakage。",
        ],
        """
Observability 的終點不是 data lake，而是縮短從 symptom 到安全行動的時間。專家會刪除無人使用、高成本 signals，並投資 context consistency。AI 能自然語言查詢與摘要，但若底層 telemetry 不一致、缺失或無權限模型，agent 只會更快產生錯誤故事。
""",
        [
            "選一個 SLO，寫五個 incident 問題，檢查現有 telemetry 能否回答。",
            "執行 structured event，加入 region/error_code 並設計 cardinality policy。",
            "畫出 symptom→metric→trace→log→change→runbook 的調查路徑。",
            "為 agent tool trace 定義 schema，加入 approval、policy、cost 和 result。",
        ],
        [
            ("Metrics、logs、traces 的主要差異？", "Metrics 看聚合趨勢/分布；logs 看離散事件與 context；traces 看跨元件因果和 latency path，三者互補。"),
            ("為何平均 latency 不足？", "少數極慢請求可能對使用者嚴重，但平均被大量快速請求稀釋；需 percentile/distribution 和 cohorts。"),
            ("High-cardinality label 有何問題？", "時間序列數量爆炸，增加成本與查詢負擔；個別 ID 應留 logs/traces，而非 metrics labels。"),
            ("Change event 為何重要？", "許多事故和 deploy/config 有關；版本與時間關聯能快速縮小假設並支援 rollback。"),
            ("Agent observability 為何要記 tool calls？", "答案之外，外部行動決定安全與結果；需知道模型看了什麼、呼叫何工具、參數、policy 和結果。"),
            ("更多 telemetry 是否總是更好？", "不是。成本、隱私、噪音和資料品質會下降；應從可行動問題、SLO 和 retention 設計。"),
            ("如何驗證 observability 真有用？", "在 incident/game day 從 symptom 出發，能否在合理時間找到 owner、相關 change、故障範圍與安全 action。"),
        ],
        ["sre-monitoring", "sre-troubleshooting", "google-agent-observability", "google-agentic-sre"],
    ),
    C(
        34,
        "Actionable Alerting 與 Multi-window Burn Rate",
        "什麼情況值得半夜叫醒人？如何同時抓到快速大事故與持續慢性傷害？",
        "進階",
        "以 SLO burn 和可行動性設計 page/ticket/dashboard，建立多窗口、去重與 runbook contract。",
        ["alert", "burn-rate", "slo", "oncall"],
        """
每個異常都 page 會造成 alert fatigue；只設高 error threshold 又可能漏掉長時間小幅傷害。Alert 的目的是在需要人類即時決策、且等待會擴大使用者影響時通知。Machine metric 應先連到 SLO 或明確故障機制，再決定 page。
""",
        """
99.9% SLO 的服務突然 20% 錯誤，需數分鐘內 page；另一個版本每天 0.2% 額外錯誤，單分鐘不明顯但會耗盡月預算。短/長窗口 burn-rate 組合能同時處理。
""",
        r"""
SLI events → error ratio → budget burn rate
                         ↓
         fast window + confirmation window
         slow window + confirmation window
                         ↓
dedupe / inhibit / route by owner
                         ↓
page: urgent + actionable
ticket: important, not immediate
dashboard/log: diagnostic only
                         ↓
runbook → action → observe → resolve
""",
        """
Burn rate 是目前 bad-event rate 相對於剛好用完整個 SLO budget 的速度。對 99.9% 目標，允許 error rate 0.1%；目前 1.4% 就是 14 倍 burn。高倍短窗口偵測劇烈事故，較低倍長窗口偵測慢性問題；搭配第二窗口能降低瞬時尖峰噪音。

Page 條件通常是使用者影響/迫近 SLO 風險、需要即時人類 action、且有 owner/runbook。容量快滿但還有數天可處理，適合 ticket；CPU 短暫高但沒有 user impact，可做 diagnostic。每個 alert 要包含 what/where/when、SLO、scope、recent changes 和 first safe actions。

Alert lifecycle 包含 dedupe、group、inhibit 和 auto-resolve。Dependency outage 不應讓每個 downstream 各 page 一次；routing 要考慮 owner 和時區。每次 alert 後回顧 precision、action 和是否能改成 automation/更早 signal。
""",
        [
            "從 SLO 或明確 imminent failure 定義 alert，而不是從每個 metric 開始。",
            "使用多窗口 burn rate 抓 fast/slow burn，回放歷史 incidents 校準。",
            "依 urgency/action 分 page、ticket、dashboard，指定 owner 和 runbook。",
            "Dedupe/group/inhibit 下游症狀，alert 內容附 scope、change 和第一步。",
            "回顧 false positive、miss、time-to-action 和 actionability，持續刪除噪音。",
        ],
        "範例計算 burn rate 並依嚴重度分類。真正 multi-window 會對短長窗口各算並要求同時成立。",
        r"""
def burn_rate(error_rate: float, slo_target: float) -> float:
    allowed = 1.0 - slo_target
    return error_rate / allowed if allowed > 0 else float("inf")

def route(rate: float) -> str:
    if rate >= 14:
        return "page"
    if rate >= 2:
        return "ticket"
    return "dashboard"

rate = burn_rate(error_rate=0.014, slo_target=0.999)
print(rate, route(rate))
""",
        [
            "1.4% error 對 99.9% SLO 是約 14 倍 burn，而非『只有 1.4%』。",
            "Routing thresholds 必須結合窗口；單點 rate 容易受低流量與尖峰影響。",
            "低流量服務可用 event count、synthetic 或較長窗口，避免除法噪音。",
            "Ticket 也要 owner/期限，否則慢性 burn 會累積成事故。",
        ],
        [
            "Alert 直接綁 CPU/memory，不驗證是否有 user impact 或可行動。",
            "Threshold 太靈敏導致疲勞，值班者逐步忽略真正 page。",
            "只抓 fast burn，長期小錯誤耗盡預算卻無人處理。",
            "Runbook 第一個步驟是『找 expert』，實際仍有 bus-factor bottleneck。",
        ],
        """
AI 可在 page 前後做 enrichment：關聯 recent changes、top errors、affected cohorts、dependencies 和歷史 incidents，並生成候選 runbook；但不應自己創造 page condition。核心觸發維持可重現的 SLO/policy，避免模型語意漂移半夜叫人。AI 可去重和摘要，但必須保留原始 alert 和 evidence。
""",
        [
            "讓 AI 在 alert payload 加入 change、trace、owner、similar incident 和 first checks。",
            "用 agent 聚類 alert storms，提出 root alert 與 downstream symptoms。",
            "請 AI 分析歷史 pages 的 actionability、false positives 和 missing context。",
            "讓 agent 依批准 runbook準備 remediation plan，操作前等待 policy/人類核准。",
        ],
        [
            "Page trigger 由 versioned deterministic SLO policy 控制，模型不能臨時改 threshold。",
            "AI enrichment 有 timeout/fallback；失敗不能延遲原始緊急 page。",
            "Summary 附 queries/evidence，禁止把猜測寫成已確認 root cause。",
            "Auto-remediation 只限可逆、bounded、已 game-day 驗證 actions，完整 audit。",
        ],
        """
好 alert 是人與系統的 API：輸入代表值得中斷的風險，輸出是值班者能採取的安全行動。專家會毫不猶豫刪除無 action alert，並把 diagnostic data 留在 dashboard。AI 應改善 context density，而不是增加更多語言噪音或把 probabilistic 判斷放在 pager critical path。
""",
        [
            "為 99.9% SLO 計算 0.1%、0.5%、1.4% error 的 burn rate。",
            "把十個 alerts 分成 page/ticket/dashboard，為每個寫 action 和 owner。",
            "回放一次 incident，測 multi-window threshold 多早觸發、是否誤報。",
            "設計 AI enrichment schema，限制處理時間並保留原始 evidence links。",
        ],
        [
            ("什麼 alert 值得 page？", "使用者正在受影響或 SLO 快速受威脅、需要即時人類決策、等待會擴大損害，且有可行動 owner/runbook。"),
            ("Burn rate 14 代表什麼？", "以目前速度消耗 error budget，會比恰好用完整窗口快 14 倍；不是單純 14% 錯誤。"),
            ("為何需要多窗口？", "短窗口快速抓劇烈事故，長窗口抓持續傷害；確認窗口降低瞬間噪音和低流量誤報。"),
            ("CPU 高應直接 page 嗎？", "只有它可靠預示迫近 user impact 且需要即時 action 時；否則作診斷或 ticket signal。"),
            ("AI 為何不應決定 page condition？", "Pager 需要穩定可預測和可稽核；模型機率性與版本漂移可能增加誤報/漏報。AI 適合 enrichment。"),
            ("Alert review 應量什麼？", "是否真有 action、false/true positive、miss、time-to-detect/action、重複與是否能 automation。"),
            ("Dependency outage 如何避免 page storm？", "Topology-aware grouping/inhibition、root alert routing、下游症狀降級，並保留影響範圍供 incident 使用。"),
        ],
        ["sre-alerting", "sre-monitoring", "sre-oncall", "google-agentic-sre"],
    ),
    C(
        35,
        "Simplicity、Change Management 與 Error-budget Policy",
        "可靠性是否等於少改？如何讓系統保持簡單，又不停止必要創新？",
        "進階",
        "用必要複雜度、可逆變更、error-budget 狀態和 cleanup discipline 管理 change。",
        ["tradeoff", "coupling", "canary", "error-budget"],
        """
Change 是事故重要來源，但完全不變也會累積漏洞、依賴過時和無法滿足使用者。複雜度會增加狀態、交互和操作路徑，使每次 change 更難預測。可靠策略不是禁止發布，而是減少不必要複雜度、縮小 batch、限制 blast radius，並在預算惡化時調整風險。
""",
        """
服務同時保留三套 cache、六個 feature flags 和兩種 deployment path。每次 incident 都要先判斷組合狀態。刪除舊 cache 和 flags，可能比增加更聰明的自動偵錯更能降低 MTTR。
""",
        r"""
product need / reliability need
           ↓
is new complexity necessary?
  ├─ no → delete / simplify / reuse platform
  └─ yes
       ↓
small reversible change + canary + cleanup owner
       ↓
error budget state
  healthy → normal rollout
  fast burn → reduce risk / investigate
  exhausted → reliability work / exceptions only
       ↓
remove flag / old path / temporary compatibility
""",
        """
Simplicity 不是行數最少，而是狀態、依賴、概念和操作路徑足夠少，使人能預測。抽象可降低重複，也可能增加 indirection；microservice 可隔離 ownership，也可能增加網路 failure。每項 complexity 要對應真 constraint，並有 owner。

Change management 以 small batch、review、test、immutable artifact、canary 和 rollback 降風險。高風險 change 可加 freeze window、specialist review 或 game day，但永久 freeze 會阻止安全更新。Error-budget policy 將風險狀態化：正常時持續發布，快速 burn 時縮小/暫停，耗盡時優先修可靠性，仍保留 security/emergency exception。

Cleanup 是 change 的一部分。Feature flag、雙寫、adapter 和額外 metrics 都應有 owner/expiry。若 roadmap 只計 launch，不計 cleanup，系統會只增不減。Operational review 應追 temporary mechanisms age 和 cognitive load。
""",
        [
            "每個新 component/flag/path 說明對應 constraint、owner 和移除條件。",
            "以 small reversible changes、canary 和 same-artifact promotion 管理 rollout。",
            "建立 error-budget policy，定義 healthy/burning/exhausted 的 change 行為。",
            "Security/emergency exception 有具名 decision owner 和額外監控。",
            "將 cleanup 排入原始 project，量 flags、old paths 和 temporary code age。",
        ],
        "範例將 budget 狀態轉成 change policy。真實政策會使用多 SLO、burn windows 和變更風險級別。",
        r"""
def change_policy(budget_remaining: float, fast_burn: bool, risk: str) -> str:
    if fast_burn:
        return "pause and investigate"
    if budget_remaining <= 0:
        return "reliability/security changes only"
    if budget_remaining < 0.25 and risk == "high":
        return "require executive exception and narrower canary"
    return "normal progressive delivery"

for remaining in (0.8, 0.2, 0.0):
    print(remaining, change_policy(remaining, False, "high"))
""",
        [
            "Policy 將抽象 reliability 狀態轉成可預期行為，減少臨時爭論。",
            "Fast burn 優先於剩餘比例，因正在發生的事故需要即時 response。",
            "Budget 低不代表禁止所有 change；可靠性和 security fix 仍可能降低風險。",
            "Exception 要縮小 canary、增加 review/monitoring，而非只取得簽名。",
        ],
        [
            "Error budget 被當成懲罰產品團隊，造成隱藏錯誤或修改 SLI。",
            "Freeze 所有 change 讓漏洞和必要修復延遲，風險反而增加。",
            "Feature flags 沒有組合測試和 cleanup，產生無法理解的 runtime states。",
            "為每個問題新增 service/tool，卻不計 on-call、dependency 和知識成本。",
        ],
        """
AI 會讓新增 code、flags、automation 和 services 更便宜，因而增加 accidental complexity 風險。Agent 每次提出新 abstraction 前應先搜尋 canonical solution、列出刪除/簡化選項和 long-term owner。Production AI component 還需要 deterministic fallback 和 kill switch，避免模型不可用時整個 critical path 失效。
""",
        [
            "讓 AI 盤點 flags、duplicate libraries、dead paths 和 temporary compatibility age。",
            "請 agent 在 design alternatives 中固定包含 delete/reuse/do-nothing。",
            "用 AI 依 error-budget、diff 和 ownership 產生 change risk summary。",
            "讓 agent 草擬 cleanup PR，依 telemetry 證明舊路徑無使用。",
        ],
        [
            "Agent 不得自行增加新的 framework/service/dependency 而無 owner review。",
            "AI feature 有 fallback、kill switch、quota 和非 AI 路徑的最低服務。",
            "Error-budget policy 和 exception 由具名 owners 管理，模型不能改 SLI 排除。",
            "Cleanup 自動化先 dry-run、usage evidence、小批次和可逆 commit。",
        ],
        """
專家最大的可靠性貢獻常是刪除：少一個狀態就少一組故障交互。Simplicity 不是反創新，而是讓每項複雜度持續證明價值。AI 時代需把『生成很容易』和『長期 ownership 很昂貴』同時放進決策，否則 code abundance 會變成理解 scarcity。
""",
        [
            "盤點服務所有 flags、deploy paths 和 caches，標 owner、age、usage、cleanup。",
            "執行 policy 範例，加入 low/medium risk 和 security exception。",
            "挑一個新 design，強制提出 delete/reuse/do-nothing 三種 alternative。",
            "讓 AI 找 dead code，再以 production telemetry 和 owners 驗證才移除。",
        ],
        [
            ("Simplicity 是否等於最少 code？", "不是。它關心概念、狀態、依賴和操作是否容易預測；有時多一層清楚 abstraction 反而降低整體複雜度。"),
            ("為何完全停止 change 不可靠？", "漏洞、依賴、使用者和環境仍會變；不更新也累積風險。應降低 change blast radius，而非追求靜止。"),
            ("Error-budget policy 有何價值？", "讓可靠性狀態對發布行為有預先同意的影響，減少事故時的部門爭論。"),
            ("Budget 耗盡時是否不能部署任何東西？", "通常仍允許降低風險的 reliability/security/emergency changes，並加強 review、canary 和監控。"),
            ("Feature flag 為何是暫時 complexity？", "它同時保留多種 behavior；完成 rollout 後若不刪除，狀態組合和測試成本持續存在。"),
            ("AI 為何增加 accidental complexity？", "新增 helper、service 和 abstraction 成本下降，但理解、on-call、migration 和 dependency 成本沒有等比下降。"),
            ("何時新 complexity 是合理的？", "它解決明確重要 constraint，收益超過建置/操作/退出成本，有 owner、evidence、fallback 和 cleanup。"),
        ],
        ["sre-simplicity", "sre-risk", "swe-cd", "dora-ai"],
    ),
    C(
        36,
        "Capacity Planning、Performance 與 Provisioning",
        "服務能撐多少流量？為什麼 CPU 還有空，使用者 latency 卻可能已經爆炸？",
        "進階",
        "用 demand、per-unit capacity、utilization knee、headroom、failure reserve 和 provisioning lead time 建模。",
        ["capacity", "constraint", "load-shedding", "feedback"],
        """
Capacity 不只是機器數。Queueing 讓 utilization 接近上限時等待時間非線性上升；memory、connection、IO、dependency quota 可能先於 CPU 成為瓶頸。資源補充有 lead time，故障又會拿走部分 capacity，因此規劃要在流量到來前完成。
""",
        """
每台 checkout benchmark 可跑 1,000 RPS，但 p99 在 700 RPS 後快速上升。若用理論最大值規劃十台承受 10k RPS，真實 7k 就超過 SLO；再失去一區時會形成 retry storm。
""",
        r"""
demand forecast (baseline / peak / growth / launch)
        ↓
workload model + SLO
        ↓
load test → utilization/latency curve → safe capacity per unit
        ↓
required units =
 demand / safe capacity
 + headroom
 + N+1 / zone failure reserve
        ↓
provisioning lead time / quota / cost
        ↓
online saturation signals → scale / shed / degrade
""",
        """
先定 workload 和 SLO，再量 capacity。不同 request 成本差異大，單一 RPS 不夠；可用 weighted work units、read/write mix、payload、cache hit 和 concurrency。Load test 找出 latency knee：在 saturation 前設定 safe utilization，而非使用理論最大 throughput。

Forecast 包含平日、尖峰、成長、launch 和季節，並保留 failure reserve。N+1 或失去一區後仍需服務 critical traffic。Provisioning 考慮 VM/database 建立時間、quota、供應不足和 warming；自動擴容不是即時魔法。長 lead-time 資源要提早訂。

Online control 使用 saturation、queue、latency 和 demand。接近上限時先限制低價值工作、降級 expensive feature、load shed，避免所有 request 一起變慢失敗。Capacity review 要和成本連結：過多 headroom 浪費，過少則用事故支付。
""",
        [
            "定義 workload classes、SLO 和 weighted cost，不只看總 RPS。",
            "以 load test 畫 utilization/throughput/latency/error 曲線，找 safe knee。",
            "Forecast baseline/peak/growth/launch，加入 headroom 與 failure reserve。",
            "計入 provisioning lead time、quota、warm-up、regional supply 和 dependency limit。",
            "線上以 queue/saturation 觸發 scale、degrade、priority 和 load shedding。",
        ],
        "範例依 demand、安全單機容量、headroom 和可用區故障計算 replicas。安全容量應來自 SLO load test。",
        r"""
from math import ceil

def required_replicas(
    peak_rps: int,
    safe_rps_per_replica: int,
    headroom: float = 0.30,
    zones: int = 3,
) -> int:
    demand_with_headroom = peak_rps * (1 + headroom)
    # 失去一區後，剩餘 zones-1 仍承擔全部 demand。
    surviving_fraction = (zones - 1) / zones
    normal_needed = demand_with_headroom / safe_rps_per_replica
    return ceil(normal_needed / surviving_fraction)

print(required_replicas(7000, 700))
""",
        [
            "單機 700 是符合 p99 SLO 的 safe capacity，不是壓到 timeout 的最大值。",
            "30% headroom 吸收 forecast error、短峰與 scaling delay。",
            "三區失去一區後只剩三分之二 capacity，因此正常時需更多 replicas。",
            "真實 placement 要確保 replicas 均勻，且 database/dependency 同樣有 reserve。",
        ],
        [
            "使用平均 RPS 規劃，忽略 peak、burst 和昂貴 request mix。",
            "Autoscaler 只看 CPU，漏掉 queue、memory、connections 或 dependency quota。",
            "Scale-up 太慢，尚未生效前 retry 已造成 cascading failure。",
            "Load test 在 warm cache/簡單 payload，過度估計 production capacity。",
        ],
        """
AI workload 增加 token、context、model tier、tool calls 和外部 API 等新成本。Capacity 需量 TTFT、tokens/sec、concurrency、GPU memory、agent step distribution 和 cost/request；長 agent loop 會持續占資源。AI 可做 forecast/anomaly 解釋，但 quota、admission、max steps 和 spend limits 必須 deterministic，防止 denial-of-wallet。
""",
        [
            "讓 AI 分析 workload cohorts、launch plan 和歷史峰值，產生 forecast scenarios。",
            "用 agent 比較 capacity curve，找 latency knee 和主要 resource bottleneck。",
            "對 AI request 建 token/context/tool-step 分布與 model-tier routing 模型。",
            "讓 agent 草擬 scaling/load-shedding plan，附成本、SLO 和 dependency constraints。",
        ],
        [
            "每 request/tenant 設 token、steps、concurrency、time 和 spend quotas。",
            "Autoscaling policy 不由 LLM 即時自由修改，使用 bounds、cooldown 和 audit。",
            "AI forecast 必須顯示資料窗口、uncertainty 和 worst-case scenario。",
            "容量不足時保留 critical deterministic path，能停用 expensive AI features。",
        ],
        """
Capacity 是可靠性、性能與經濟的交界。專家不以「CPU 低」證明充足，而看使用者 SLO 下的 limiting resource 和失敗情境。AI 系統尤其容易被平均 tokens 掩蓋長尾；先限制單請求工作量，再談無限擴容，通常更可靠也更省成本。
""",
        [
            "執行 replicas 計算，改 zones、headroom 和 safe capacity 比較成本。",
            "對一個 service 畫 throughput vs p99 曲線，標出 safe knee。",
            "建立容量表：resource、current、safe max、lead time、owner、shed action。",
            "為 agent 定義 max tokens、steps、tools、concurrency 和降級路徑。",
        ],
        [
            ("為何 capacity 應以 SLO 下的值計算？", "理論最大 throughput 可能伴隨不可接受 latency/error；使用者品質已失敗就不算可用 capacity。"),
            ("Headroom 解決什麼？", "Forecast 誤差、短峰、scale delay、單機差異和小故障；仍需依成本與風險校準。"),
            ("Autoscaling 為何不能取代 planning？", "資源有偵測、啟動、warm-up、quota 和供應 lead time；突然大峰可能在擴容前已過載。"),
            ("CPU 低但 latency 高可能有哪些原因？", "IO、lock、queue、connection pool、dependency、single-thread bottleneck、GC 或 rate limit，需看完整 saturation。"),
            ("Load shedding 與 scaling 如何配合？", "Scaling增加未來 capacity；shedding 立即限制當前工作，防止等待/重試擴散，兩者時間尺度不同。"),
            ("AI capacity 有哪些特有維度？", "Context/token、model tier、TTFT、tokens/sec、GPU memory、tool calls、steps、cost 和 provider quota。"),
            ("Denial-of-wallet 如何防止？", "Per-request/tenant budget、rate/concurrency、max steps、cheaper fallback、anomaly alert 和 hard spend limit。"),
        ],
        ["sre-intro", "sre-overload", "swe-compute", "google-agent-observability"],
    ),
]
