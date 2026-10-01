"""Part 0 and Part 1: the global map and engineering-over-time thesis."""
from __future__ import annotations

from swe_sre_ai_model import C


CHAPTERS = [
    C(
        1,
        "從一行程式碼到可靠服務",
        "一段在筆電上正確執行的程式，距離能被真實使用者長期信任，究竟還差哪些工程能力？",
        "入門",
        "建立全書唯一的黃金路徑：能把需求、程式碼、交付、production、事故與學習放進同一張圖。",
        ["software", "service", "production", "lifecycle", "feedback"],
        """
初學者常把軟體工作想成「理解需求、寫完 code、測試通過」。但真實服務還要面對多人同時修改、依賴升級、部署失敗、流量尖峰、機器故障、資料相容性、值班和多年維護。若沒有共同生命週期，每個團隊只優化自己眼前的一段：開發追求快、維運追求不變、管理只看產出數字，最後由使用者承擔斷裂處。
""",
        """
團隊要為購物網站新增折扣功能。函式算對價格只是起點；還要確認舊手機能解析 response、不同時區不會算錯日期、reviewer 看得懂規則、artifact 可重現、canary 沒傷害使用者、dashboard 看得見錯價，並能在事故後還原與修正。
""",
        r"""
使用者問題
    ↓
需求 / Constraints / SLO
    ↓
Design → Code → Review → Test → Build → CI
                                      ↓
                                 Artifact
                                      ↓
                         Canary → Production
                                      ↓
                     Metrics / Logs / Traces
                                      ↓
                         Alert → Incident
                                      ↓
                  Postmortem → Test / Rule / Doc
                                      └──────────→ 下一次變更
""",
        """
這張圖同時包含兩種流動。上半部是 change flow：一個想法逐漸被約束、實作、驗證，再成為可部署 artifact。下半部是 evidence flow：真實世界把 latency、error、使用者行為和事故送回團隊，迫使模型更新。只畫前半部會得到「交付工廠」，只畫後半部則變成永遠救火的 operations。

Software Engineering at Google 關心的是 change 如何跨越時間與規模仍可安全進行；SRE 關心的是服務進入 production 後，如何用工程方法控制風險。兩者不是開發與維運的兩個島，而是同一個 feedback loop 的前後段。Review、test、CI 是發布前的感測器；SLI、alert 和 incident 是發布後的感測器。

可靠服務不是「從不失敗」。它是知道哪些行為最重要、允許多少失敗、如何限制 blast radius、何時停止發布，以及怎麼把事故留下的知識轉成永久資產。這也解釋為何本書會從文化談到 consensus：它們都在保護同一條價值流。
""",
        [
            "把使用者可見需求轉成 constraints、API contract 與可量測的成功條件。",
            "以 review、test、build 和 CI 建立發布前的快速 feedback。",
            "以 canary、SLI、logs、metrics 和 traces 建立發布後的真實 feedback。",
            "事故發生時先限制傷害、恢復服務，再把教訓編碼成 test、rule、tool 或 document。",
            "定期刪除已無價值的流程與元件，避免 feedback loop 被歷史成本拖慢。",
        ],
        "下面用一個極小的 Python pipeline 表示變更只有通過每個 gate 才能前進。它不是 CI 產品，而是讓你看見『信心來自多個獨立證據』。",
        r"""
from dataclasses import dataclass, field

@dataclass
class Change:
    name: str
    evidence: dict[str, bool] = field(default_factory=dict)

GATES = ("review", "unit_test", "contract_test", "build", "canary")

def releasable(change: Change) -> bool:
    missing = [gate for gate in GATES if not change.evidence.get(gate)]
    if missing:
        print("BLOCKED:", ", ".join(missing))
        return False
    print("READY:", change.name)
    return True

candidate = Change(
    "discount-v2",
    {"review": True, "unit_test": True, "contract_test": True,
     "build": True, "canary": False},
)
releasable(candidate)
""",
        [
            "`Change` 不等同 source code；它攜帶讓人相信這次修改安全的 evidence。",
            "每個 gate 捕捉不同失敗，不能因 unit test 通過就宣稱 production 一定安全。",
            "`canary=False` 表示真實環境仍缺證據，因此 pipeline 正確地阻止全面發布。",
            "Production telemetry 之後應回寫新的 evidence，而不是讓部署成為流程終點。",
        ],
        [
            "Gate 越多不一定越安全；重複、慢或高噪音檢查會鼓勵人繞過整套流程。",
            "所有 gate 都由同一個錯誤假設產生時，數量再多也不是獨立證據。",
            "只量 deployment 成功而不量使用者結果，會把『程式啟動』誤認為『功能正確』。",
            "沒有 owner 的 postmortem action item 會讓 feedback loop 在最後一步斷掉。",
        ],
        """
AI 把變更產生速度提高後，最先出現的瓶頸通常不是打字，而是規格品質、context、驗證、審查與整合。工程師的角色會更多轉向定義 intent、constraints、acceptance criteria 和風險邊界；agent 可探索與實作，但不能替組織承擔產品承諾。若只把 AI 接在 code 方塊，整條生命週期其他部分沒有升級，結果通常是更快產生更多待 review、待修復和待理解的變更。
""",
        [
            "讓 agent 依明確需求建立小型 plan、修改隔離 branch，並列出它取得的證據。",
            "用 AI 摘要 diff、找可能受影響的 call sites，協助 reviewer 建立地圖。",
            "讓 AI 根據失敗 test 或 telemetry 產生候選假設，但要求附上可驗證步驟。",
            "在 postmortem 後讓 AI 草擬新的 tests、runbook 或 static rule，再由 owner 採納。",
        ],
        [
            "Agent 只能取得任務需要的 repository、tool 和環境權限；production 預設唯讀。",
            "完成條件必須包含 deterministic build、test、lint 和安全檢查，不能以模型自評取代。",
            "高風險變更需要獨立 reviewer；產生變更的同一段對話不能自行批准。",
            "保存 model、prompt/instruction、tool trace、commit 與結果，讓問題可重現與稽核。",
        ],
        """
資深工程師不會問「我們用了多少 AI」，而會問 feedback loop 是否變短且仍可信：需求到證據的時間是否下降、rollback 是否更快、review 負荷是否合理、缺陷是否外溢。AI 自治權應依風險與歷史成功證據逐步擴大；低風險文件修正和 production schema migration 不應使用同一套批准政策。
""",
        [
            "選一個最近做過的功能，畫出從需求到 production 的真實路徑，標出每個等待點與 handoff。",
            "在圖上用紅色標記錯誤最晚會在哪裡被發現，再思考能否把 signal 往前移。",
            "執行範例，逐一拿掉 gate，寫出哪類錯誤可能因此進入 production。",
            "為一個 coding agent 任務寫出 intent、constraints、驗證命令與禁止操作四個欄位。",
        ],
        [
            ("為什麼『測試通過』仍不代表服務可靠？", "測試只涵蓋已建模的輸入與環境；production 還有真實流量分布、依賴故障、容量、設定和操作因素。可靠性需要發布前與發布後的多層 evidence，並讓新事故回饋到測試。"),
            ("SWE 與 SRE 在黃金路徑中如何分工？", "SWE 主要降低長期修改 codebase 的成本與風險；SRE 主要控制服務在 production 的可靠性與營運成本。兩者透過 CI/CD、change management、testing 和 telemetry 相接，不能完全分離。"),
            ("為何 postmortem 必須產生工程資產？", "只有故事不會改變下一次系統行為。將教訓變成 test、alert、runbook、API constraint 或自動化，才能讓同類錯誤更早被攔截或更快恢復。"),
            ("更多 gate 何時反而降低可靠性？", "當 gate 太慢、重複、flaky 或無法解釋時，開發者會延後整合、批次變大或尋找繞過方法。好的 gate 必須對應具體風險，並提供快速且可行動的 feedback。"),
            ("AI 在這條路徑中最適合扮演什麼角色？", "它適合加速探索、草擬、搜尋、測試候選、證據整理與低風險操作；人仍需定義產品 intent、接受風險、處理價值衝突並對結果負責。"),
            ("如何判斷 agent 是否可以自動 merge？", "依變更風險、可逆性、測試完整度、blast radius、歷史成功率和 audit 能力決定。先從小型、可回退、deterministic checks 完整的範圍開始，失敗就降低自治。"),
            ("本章最重要的 invariant 是什麼？", "任何變更前進到下一階段時，都應帶著與風險相稱、可被別人檢查的 evidence；不能只因作者或模型表示有信心就前進。"),
        ],
        ["swe-preface", "sre-intro", "dora-ai", "openai-codex"],
    ),
    C(
        2,
        "共同語言：Service、Feedback 與 AI Agent",
        "如果讀者連 service、deployment、context、agent、eval 都不熟，如何建立足以閱讀後續 46 章的共同模型？",
        "入門",
        "用一個最小服務拆清楚 request、state、dependency、deployment、telemetry，以及 AI agent 的 observe–act loop。",
        ["service", "feedback", "agent", "context", "eval"],
        """
工程討論很容易因同一個詞代表不同層級而失焦。例如「服務掛了」可能是 process 已退出、API error rate 上升、dependency timeout，或只是某個使用者流程失敗；「AI 幫我修」也可能只是補全一行，或是具備 shell、Git 和 production 工具的自治 agent。本章先把後文常用物件與邊界定義清楚。
""",
        """
我們建立一個 `/quote` API：client 傳入商品與數量，service 讀取 catalog dependency，計算價格並回覆。接著讓 coding agent 修正折扣 bug。這個小場景同時包含 request、state、dependency、test、deployment、telemetry、context 和 tool permission。
""",
        r"""
Client ──request──> Quote Service ──query──> Catalog
   ▲                     │                    │
   └────response─────────┘                    │
                         ├─ process memory     │
                         ├─ database state <───┘
                         └─ logs / metrics / traces

Human intent
   ↓
[Agent: observe → reason/plan → tool call → observe]
   │       context: code + docs + test output
   └────── tools: search / edit / test / git
""",
        """
Service 是一個責任邊界，不等同單一 process 或機器。它可能有多個 replicas、資料庫、queue 和外部 dependencies，但對 client 提供一組相對穩定的 contract。Request 是一次互動，state 是跨互動保存的事實，deployment 則是把特定 artifact 與 configuration 放入某個 environment 的動作。

Telemetry 是系統主動留下的可觀察輸出；feedback 則要更進一步，讓輸出改變決策。例如 log 存在但沒有人或工具讀取，就不是有效 feedback loop。Metrics 適合趨勢與聚合，logs 適合離散事件，traces 適合跨元件因果路徑；三者不是互相取代。

語言模型只會根據目前 context 產生下一步輸出。Agent harness 把模型放進迴圈，提供 tools、記憶、停止條件和權限。Eval 是在多個固定或代表性案例上量測 agent 是否完成任務、遵守 policy 並安全失敗。這些名詞會在後面逐步深化，此處先建立邊界。
""",
        [
            "Client 依 API contract 送出 request；service 驗證輸入並建立 request-scoped context。",
            "Service 呼叫 dependency 或讀寫 state，任何跨網路互動都可能慢、失敗或重複。",
            "Response 只代表這次互動的結果；可靠性需聚合大量 valid events 才能判斷。",
            "Deployment 改變 production 正在執行的 artifact/config，telemetry 應能標記這個 change event。",
            "Agent 每次工具呼叫都改變外部世界，因此 harness 必須管理 context、permission、budget 和 stop condition。",
        ],
        "這個例子同時展示 request handler 與一個極小的 agent loop。Agent 本身不神奇：它只是根據 observation 選 action，工具執行後再取得新的 observation。",
        r"""
from dataclasses import dataclass

CATALOG = {"book": 300, "pen": 20}

def quote(item: str, quantity: int) -> int:
    if item not in CATALOG:
        raise KeyError("unknown item")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return CATALOG[item] * quantity

@dataclass
class ToolResult:
    ok: bool
    output: str

def tiny_agent(goal: str, tools: dict):
    observation = f"goal={goal}"
    for step in range(3):                 # 明確的 action budget
        action = "run_tests" if step == 0 else "stop"
        if action == "stop":
            return observation
        result: ToolResult = tools[action]()
        observation = result.output
        if result.ok:
            return "verified: " + observation
    return "budget exhausted"
""",
        [
            "`quote` 的 contract 包含正常輸出和兩種明確錯誤，這比『回一個數字』更完整。",
            "`tiny_agent` 只有被注入的 tools，模型或策略不能憑空取得其他權限。",
            "`range(3)` 是最小停止條件，避免錯誤 observation 造成無限 tool loop。",
            "成功條件來自 `ToolResult.ok` 的外部證據，而不是 agent 自己說『應該好了』。",
        ],
        [
            "把 service 等同 process，會忽略 load balancer、replicas、state 和 dependencies。",
            "只收集 telemetry 不建立 owner、threshold 和 action，資料會變成昂貴噪音。",
            "把聊天模型稱為 agent，會低估 tool permission 與 side effect 的安全問題。",
            "Eval 只測快樂路徑，agent 就可能在 timeout、惡意輸入或缺權限時做出危險補救。",
        ],
        """
AI 時代最重要的新共同語言是「模型能力」與「系統能力」的分離。模型可能擅長推理，但 agent 是否可靠取決於 context 是否正確、tools 是否設計良好、環境是否隔離、eval 是否代表真實工作，以及失敗時能否停止。這和 service reliability 相似：單一函式正確不代表整個 production path 可靠。
""",
        [
            "用 agent 搜尋 codebase 與解釋資料流，但要求列出實際檔案與證據。",
            "把測試、type checker、API schema 和 policy check 暴露成結構化 tools。",
            "對重複任務建立 representative eval set，版本更新前後比較結果。",
            "將 tool trace 與 deployment/incident timeline 串接，知道 AI 做過哪些外部操作。",
        ],
        [
            "區分 read、write、deploy、production mutation 四級 tool 權限，預設從 read-only 開始。",
            "限制 steps、wall-clock、token、金額與可觸及資源，超限必須安全停止。",
            "敏感資料進入 context 前先做 ACL、redaction 和 retention 檢查。",
            "Eval 同時包含正確案例、模糊需求、工具失敗、prompt injection 和拒絕案例。",
        ],
        """
Domain expert 會先問 agent 的 control plane：誰定義 tool、誰核准權限、誰看 audit、模型故障時如何 fallback。若團隊只能展示漂亮 demo，卻無法回答這四題，系統仍處於實驗階段。反過來，並非所有工作都需要 agent；固定 schema transformation 用普通程式通常更便宜、可預測且易測。
""",
        [
            "執行 `quote` 的正常、未知商品、零數量三個案例，寫出每個 contract。",
            "替 `tiny_agent` 加入一個永遠失敗的 tool，確認 budget 能停止迴圈。",
            "畫出你熟悉服務的一個 request path，分別標記 process、service、state 與 dependency。",
            "設計五個 eval cases：正常修復、測試失敗、缺檔案權限、惡意文件指令、超過步驟上限。",
        ],
        [
            ("Service 為何不等同一台 server？", "服務是對外責任與 contract 的邊界；實作可以跨多個 process、replica、資料庫和區域。一台 server 只是某個時間點的執行資源。"),
            ("Telemetry 和 feedback 的差別是什麼？", "Telemetry 是輸出資料；feedback 必須讓資料進入決策並改變行為。沒有 owner、threshold、review 或 automation 的 dashboard，可能只是被動資訊。"),
            ("聊天模型何時才成為 agent？", "當系統讓模型在目標下反覆觀察、規劃、呼叫外部工具、接收結果並決定下一步時，才具有 agentic loop；工具 side effects 使權限和停止條件變得重要。"),
            ("為什麼 deterministic 工作不一定適合 LLM？", "固定規則用普通程式可得到相同輸入必有相同輸出、容易測試且成本低。LLM 適合規則難以完整列舉、需要語意判斷的部分，但應把可確定的檢查留給工具。"),
            ("Eval 與一般 unit test 有何異同？", "兩者都提供可重複判斷；但 AI 輸出可能非 deterministic，eval 常需資料集、容忍區間、rubric 或 grader，還要看 tool trajectory 和 policy compliance。"),
            ("Agent 的 step limit 能解決所有失控問題嗎？", "不能。它只限制一次迴圈長度，仍需 resource quota、tool scope、idempotency、approval 和 audit；三步內也可能做出高破壞操作。"),
            ("本章應保留的最小 agent 模型是什麼？", "Agent = model decision + bounded context + explicit tools + observe/act loop + stop conditions + verification + audit。少了任何一項，都要清楚知道風險由哪裡承擔。"),
        ],
        ["sre-intro", "openai-codex", "openai-evals", "owasp-llm"],
    ),
    C(
        3,
        "Programming 與 Software Engineering 的差別",
        "為什麼會寫出正確程式，仍不足以設計一個可由團隊維護十年的系統？",
        "入門",
        "學會把『現在可運行』擴張成『在時間、團隊與環境改變後仍可理解、修改和營運』。",
        ["software", "lifecycle", "constraint", "feedback"],
        """
Programming 通常聚焦把目前問題轉成可執行演算法；software engineering 還必須處理需求會變、呼叫者未知、團隊會換人、依賴會升級、硬體與法規會改變。若只優化當下寫法，未來每次變更都可能增加不可見的協調成本，直到系統再也不敢改。
""",
        """
一位工程師用 80 行 script 每天匯入報表，最初非常成功。半年後它成為營運關鍵流程：五個團隊依賴欄位順序、密碼寫在筆電、失敗無告警、作者休假便沒人敢動。演算法沒有錯，但軟體工程系統不存在。
""",
        r"""
Programming
problem → algorithm → code → output

Software Engineering
problem + changing constraints
   ↓
architecture + ownership + contracts
   ↓
code + tests + docs + build + rollout + telemetry
   ↓
operate / migrate / deprecate / learn
   └───────────────────────────────→ future changes
""",
        """
兩者不是高低之分，而是積分範圍不同。短命、單人、可丟棄的程式可能只需要 programming；一旦輸出被其他人依賴、程式要跨時間維護，工程問題便出現。最常見的錯誤是系統已變成基礎設施，團隊仍以一次性 script 的治理方式對待。

工程化的核心不是加入更多文件或會議，而是讓重要假設顯式、讓風險有 owner、讓修改有快速 evidence。測試保護 behavior，API contract 管理邊界，version control 保存歷史，CI 縮短 feedback，SLO 對齊使用者結果。每項機制都應能回答它降低哪種未來成本。

因此「最佳實務」不能脫離壽命與規模。兩週後刪除的 prototype 不值得建立全球多區部署；處理薪資十年的服務則不應依賴作者記憶。資深判斷在於辨識軟體何時跨過工程化門檻，以及採用足夠而不過度的機制。
""",
        [
            "先估計軟體壽命、使用者、修改者、資料價值和故障影響。",
            "列出最可能改變的 assumptions，為高成本變化建立 contract 或 seam。",
            "建立最小 ownership、version control、test、deployment 和 telemetry。",
            "隨依賴與影響擴大，逐步增加 review、rollout、SLO 和 incident 機制。",
            "定期重新評估：prototype 可能升級為產品，舊產品也可能應該被淘汰。",
        ],
        "以下用同一個資料轉換示範 script 與可維護 component 的差別。後者沒有更聰明的演算法，但把 contract、錯誤和變更點顯式化。",
        r"""
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int
    unit_price: Decimal

def invoice_total(items: list[LineItem]) -> Decimal:
    # Return total; reject invalid business state explicitly.
    total = Decimal("0")
    for item in items:
        if item.quantity <= 0:
            raise ValueError(f"{item.sku}: quantity must be positive")
        if item.unit_price < 0:
            raise ValueError(f"{item.sku}: price cannot be negative")
        total += item.unit_price * item.quantity
    return total
""",
        [
            "`Decimal` 表達金額 constraint，避免 binary float 的隱性誤差。",
            "`LineItem` 把欄位名稱與型別變成 contract，不依賴位置神秘的 list。",
            "Invalid state 立即失敗並帶 context，呼叫者可監控而非得到錯價。",
            "Docstring 和 type hints 同時幫助人、static tool 與 coding agent理解邊界。",
        ],
        [
            "過早工程化會延長探索週期，使尚未確認的需求被錯誤抽象固定。",
            "完全不工程化會讓成功 prototype 在依賴增加後突然成為高風險 legacy。",
            "抽象越多不等於越可維護；錯誤抽象會把不相關變化綁在一起。",
            "只補文件不補 executable checks，文件可能很快與真實行為分離。",
        ],
        """
AI 讓產生可運行 prototype 的成本大幅下降，因此 programming 到 engineering 之間的落差反而更危險。Demo 可能在一天內吸引使用者，卻沒有 owner、security、migration 或 observability。另一方面，AI 也能降低補齊 tests、docs、codemods 和 runbooks 的成本；關鍵是把它用於建立長期 feedback，而非只追求第一版速度。
""",
        [
            "讓 AI 先列出需求中的 assumptions、external consumers 和 failure modes。",
            "請 agent 在實作前提出最小 contract 與驗證計畫，再生成 code。",
            "用 AI 將成功 prototype 盤點成 production-readiness backlog。",
            "定期用 agent 搜尋重複邏輯、孤兒程式、無 owner job 和失效文件候選。",
        ],
        [
            "Prototype 升 production 前必須經 security、data、ownership 和 rollback review。",
            "AI 生成的 abstraction 需以目前至少兩個真實 use cases 驗證，避免 speculative design。",
            "禁止以『模型已解釋』取代 tests、type checks 和實際執行證據。",
            "對快速生成的臨時工具設定 owner、expiry date 和資料處理邊界。",
        ],
        """
成熟團隊會建立「graduation path」而非禁止 prototype：探索期允許低 ceremony，但一旦觸及真實資料、多人依賴或值班責任，就必須升級 contract、tests、deployment 和 ownership。AI 時代最昂貴的不是寫 code，而是讓大量無治理的成功實驗悄悄變成永久系統。
""",
        [
            "挑一個現有 script，列出它的使用者、資料、執行頻率、失敗影響和單點知識。",
            "執行範例並新增一個稅率需求，觀察哪個介面需要改變。",
            "為 prototype 定義三個 graduation triggers，例如真實個資、第二位使用者、每日排程。",
            "請 AI 為同一需求生成 prototype plan 與 production plan，比較多出的工程責任。",
        ],
        [
            ("Programming 與 software engineering 最核心差異是什麼？", "Programming 解決目前計算問題；software engineering 把程式放進時間、多人協作、部署和營運中，管理持續修改的成本與風險。"),
            ("何時一次性 script 開始需要工程化？", "當它被多人或關鍵流程依賴、處理重要資料、需要長期運行、作者不再是唯一操作者，或失敗會有顯著影響時。"),
            ("為什麼更多 abstraction 不必然更好？", "抽象本身增加間接層和學習成本；若變化軸判斷錯誤，反而把不同需求綁死。應以真實重複與穩定 contract 驅動。"),
            ("文件為何不能取代 executable checks？", "文件可能過時且不會阻止錯誤進入主線；test、type 和 schema 能在每次變更自動驗證。兩者互補：文件解釋意圖，checks 保護可機械判斷的規則。"),
            ("AI 為何同時縮短與擴大 engineering gap？", "它讓 prototype 更快，也能協助補 tests/docs；若組織只獎勵 demo 速度，無治理 code 會更快累積。若流程要求 evidence，AI 則能降低建立 evidence 的成本。"),
            ("如何避免 production-readiness 變成沉重官僚？", "依風險分級，使用自動 checks 和預設平台，讓低風險服務走短路徑；只有資料、權限、不可逆 migration 等高風險項目需要深度 review。"),
            ("本章的專家判斷題是什麼？", "不是『是否遵守所有最佳實務』，而是『這個軟體的壽命、依賴與影響是否已要求更多可重複 evidence，而且目前機制是否正好足夠』。"),
        ],
        ["swe-preface", "sre-intro", "dora-ai", "openai-codex"],
    ),
    C(
        4,
        "Time and Change：軟體為什麼會老化",
        "程式碼不會像食物腐敗，為什麼一個多年沒改的系統仍會逐漸變得危險？",
        "初階",
        "看懂軟體老化其實是環境、需求、依賴與知識改變，並學會設計可遷移而非永遠不變的系統。",
        ["lifecycle", "compatibility", "coupling", "invariant"],
        """
軟體 bytes 不會自行磨損，但周圍世界會動：作業系統停止支援、憑證算法淘汰、客戶行為改變、資料量增長、法律更新、原作者離開。當系統假設與現實的距離增加，每次修改都更難預測，這就是實務上的 software aging。
""",
        """
十年前的帳號欄位假設 email 永遠唯一且不可變。公司後來支援企業 SSO、帳號合併和隱私刪除；原本看似合理的 primary key 變成每個 migration 都要繞過的歷史約束。
""",
        r"""
時間 t0                    時間 t1
需求 A                     需求 A + B
依賴 v1      ───────→      依賴 v4
資料 10 GB                 資料 20 TB
作者在團隊                 作者已離開
威脅模型 X                 威脅模型 X + Y

若 assumptions 未顯式化：
現實變化 → hidden mismatch → workaround → coupling → 更難改

健康路徑：
signal → compatibility window → migration → cleanup
""",
        """
時間問題可以拆成四類。External change 是平台、法規與依賴變動；requirement change 是產品需要不同能力；scale change 是原本可接受的演算法或操作超過容量；knowledge change 是團隊失去設計原因。它們都會讓當初正確的決策失去前提。

可維護性不是預先猜中所有未來，而是降低錯誤猜測的代價。清楚 contract 限制耦合，observability 看見舊路徑仍有誰使用，migration 將大改動拆成可共存階段，deprecation 最終清除舊成本。只加 abstraction 卻不安排 cleanup，會讓系統永久同時背負每一代設計。

時間也改變風險計算。暫時 workaround 若有 owner、期限和移除條件，可以是合理取捨；沒有這些資訊，它就會被後人誤認為必要架構。設計文件和 ADR 的價值是保存 constraint 與決策，不是描述每一行 code。
""",
        [
            "辨認設計依賴的 assumptions，區分哪些是 contract、哪些只是目前實作。",
            "為不可原子切換的改動設計 expand、migrate、contract 三階段。",
            "加入 telemetry，量測舊版本、舊欄位和舊 API 的剩餘使用量。",
            "設定 owner、deadline 和 rollback，使暫時相容層不會永久化。",
            "遷移完成後刪除舊 code、flags、metrics 和文件，真正降低複雜度。",
        ],
        "範例示範 schema evolution：先接受新舊輸入，再逐步把內部表示統一，最後才移除舊格式。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class UserName:
    given: str
    family: str

def parse_name(payload: dict) -> UserName:
    # 新格式優先；migration window 仍接受舊 full_name。
    if "given_name" in payload and "family_name" in payload:
        return UserName(payload["given_name"], payload["family_name"])
    if "full_name" in payload:
        parts = payload["full_name"].strip().split(maxsplit=1)
        return UserName(parts[0], parts[1] if len(parts) == 2 else "")
    raise ValueError("name is required")
""",
        [
            "函式把兩種外部格式立即轉成單一 internal model，避免相容性分支污染整個 codebase。",
            "舊格式 parser 是有期限的 migration layer，不應成為永遠支援的第二套 domain model。",
            "Production 應記錄舊格式使用量，但避免把姓名等敏感資料寫入 log。",
            "只有使用量歸零並經過安全窗口後，才能刪除 `full_name` 分支。",
        ],
        [
            "永久同時支援新舊行為會讓測試組合與認知成本持續成長。",
            "Big-bang migration 簡單但要求所有 producer/consumer 同時更新，通常不適合分散式組織。",
            "過度兼容錯誤輸入可能把資料品質問題隱藏到更深層。",
            "只看 repository 搜尋結果會漏掉舊 binary、外部客戶、資料檔與未連線裝置。",
        ],
        """
AI 能快速產生 code，也會讓 codebase 的變更頻率、重複方案與局部 workaround 增加。長期健康更依賴 machine-readable contracts、版本化文件、可搜尋 decision history 和自動 cleanup signal。Agent 可能從 repository 模仿已過期 pattern，因此 context 必須標明 canonical path、deprecated APIs 和 migration 狀態，而不能假設它自然知道最新設計。
""",
        [
            "讓 AI 盤點某 API 的 producers、consumers、schemas、tests 和 documents。",
            "請 agent 草擬 expand–migrate–contract plan，列出每階段的 rollback 與 telemetry。",
            "用 AI 搜尋過期 flags、TODO、deprecated call sites，再由 owner 確認刪除。",
            "讓 AI 比較 ADR 與目前 code，產生可能 drift 的候選清單。",
        ],
        [
            "Migration plan 必須以實際 telemetry 驗證，不能只信 agent 的 repository 搜尋。",
            "Codemod 前先鎖定 AST pattern、建立 dry-run diff 和代表性 tests。",
            "Deprecated path 在 agent instructions 中明確標記禁止新使用。",
            "任何自動 cleanup 必須有 owner、可逆 commit 與資料保留檢查。",
        ],
        """
真正的時間尺度設計通常不是追求『future-proof』，而是投資在 observability、compatibility seam 和 migration discipline。因為未來不可預測，最有價值的能力是讓錯誤假設可以被發現、局部替換並最終清除。AI 會使修改便宜，但不會使協調與資料相容性自動消失。
""",
        [
            "列出一個舊系統的五個原始 assumptions，標記目前是否仍成立。",
            "執行範例，增加第三種 `display_name` 格式，設計不讓分支擴散的方法。",
            "為 `full_name` deprecation 寫三個 metrics：總流量、舊格式比例、最後使用者群。",
            "請 AI 生成 migration plan，再人工找出 repository 之外它可能漏掉的 consumers。",
        ],
        [
            ("軟體為何會老化？", "程式本身不磨損，但需求、依賴、資料規模、威脅和團隊知識會改變。原始 assumptions 與現實的差距使維護風險上升。"),
            ("可維護性是否代表預測所有未來需求？", "不是。它代表建立清楚邊界、feedback、migration 和 cleanup 能力，讓無法預測的變化仍能以可控成本處理。"),
            ("Expand–migrate–contract 各做什麼？", "Expand 先讓系統同時接受新舊世界；migrate 轉移資料和使用者並量測；contract 在證據足夠後移除舊路徑。"),
            ("為什麼 compatibility layer 必須有移除計畫？", "每個額外格式都增加 branch、test matrix 和理解成本。沒有 owner、telemetry、deadline 的暫時層很容易永久化。"),
            ("AI 為何可能強化舊 pattern？", "模型根據可見 repository 和文件模仿；若 deprecated code 仍大量存在且沒有標記，它可能把歷史解法當成推薦解法。"),
            ("Repository 搜尋何時不足以證明舊 API 無人使用？", "外部客戶、離線裝置、舊部署、動態呼叫、資料檔與反射可能不在目前 source tree，需要 runtime telemetry 和溝通。"),
            ("時間與變更章最重要的設計能力是什麼？", "不是避免所有改動，而是安排可共存、可觀測、可回退且可清理的遷移，使每代設計不必永久疊加。"),
        ],
        ["swe-preface", "swe-deprecation", "dora-ai", "openai-codex"],
    ),
    C(
        5,
        "Hyrum’s Law：所有可觀察行為都可能成為依賴",
        "即使沒有修改正式 API，為什麼重排 JSON、改錯誤文字或提升速度也可能破壞使用者？",
        "中階",
        "分清 declared contract、observable behavior 和 accidental dependency，並用 consumer evidence 管理相容性。",
        ["api", "compatibility", "invariant", "test-oracle"],
        """
系統使用者足夠多時，幾乎任何可觀察行為都可能被某人依賴：排序、延遲、錯誤字串、重試次數、未文件化欄位甚至 bug。API 作者心中的 contract 與生態系實際使用的 contract 會逐漸分離，讓『內部重構』意外成為 breaking change。
""",
        """
搜尋 API 宣稱結果順序未定，但多年來剛好按建立時間回傳。某客戶沒有自己排序，直接顯示第一筆。資料庫換 index 後順序改變，服務 schema 完全相同，使用者畫面卻出錯。
""",
        r"""
Provider
  ├─ declared contract ───────────────┐
  ├─ stable implementation behavior ─┼─→ Consumers observe
  ├─ timing / ordering / errors ──────┤       ↓
  └─ bugs / side effects ─────────────┘   some behavior becomes dependency

安全變更：
inventory consumers → classify behavior → add contract/test
                   or warn/migrate/version → observe → remove
""",
        """
Contract 有三層。Declared contract 是文件或 schema 承諾；de facto contract 是大量 consumer 已依賴、無法輕易改變的行為；implementation detail 是理論上可改，但仍可能被觀察的現象。Hyrum’s Law 提醒我們不能只靠作者宣告決定後兩者，規模會把可觀察性轉成耦合。

解法不是凍結所有行為，而是降低不必要的可觀察面，並為重要行為提供明確 contract。Response 應避免暴露內部資料結構；錯誤使用 machine-readable code 而非讓 client parse 文字；需要順序就明確指定，不需要就用測試打亂以防 consumer 偷依賴。

相容性決策需要 consumer evidence。Contract tests、usage telemetry、version negotiation、deprecation notice 和 staged rollout 都能縮小未知。Provider test 只能證明自己符合預期，consumer-driven contract 才能發現真實整合假設。
""",
        [
            "列出 API 的可觀察面：values、ordering、errors、timing、side effects 和 resource limits。",
            "區分哪些行為應升格為正式 contract，哪些應主動隨機化或隱藏。",
            "建立 provider 與 consumer contract tests，對高風險變更先跑 compatibility suite。",
            "透過 version、feature negotiation 或雙軌輸出安排 migration window。",
            "以 telemetry 和 canary 驗證實際 consumer，而非只靠文件推測。",
        ],
        "範例刻意把錯誤文字與穩定 error code 分開。Client 應依 code 決策，message 可以改善而不破壞控制流。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    retryable: bool

def reserve(stock: int, requested: int) -> ApiError | None:
    if requested <= 0:
        return ApiError("INVALID_QUANTITY", "Quantity must be positive", False)
    if requested > stock:
        return ApiError("OUT_OF_STOCK", "Not enough inventory", False)
    return None

def client_action(error: ApiError | None) -> str:
    if error is None:
        return "continue"
    return "retry" if error.retryable else f"show:{error.code}"
""",
        [
            "`code` 是 machine contract，`message` 是可以本地化與改善的人類資訊。",
            "`retryable` 把 policy 顯式化，避免每個 consumer 猜哪些錯誤可重試。",
            "若 client 解析 `message`，哪怕修正文法都可能成為 breaking change。",
            "Contract test 應驗證 code 和 retry semantics，不必鎖死完整英文句子。",
        ],
        [
            "把所有歷史行為永久化會阻止修 bug、提升效能和簡化系統。",
            "只靠 semantic versioning 無法幫助根本不升級或未知的 consumers。",
            "過度寬鬆 parser 可能讓無效資料默默擴散，之後更難收緊。",
            "Latency 改快也可能暴露 race condition，證明 timing 同樣是 observable behavior。",
        ],
        """
Coding agent 會大量搜尋並模仿現有 call sites，因此 accidental behavior 可能以更快速度擴散。另一方面，AI 很適合建立 consumer inventory、比較 schemas、產生 compatibility cases 和找 parse-error-string 等脆弱 pattern。關鍵是讓 contract 成為 machine-readable source of truth，避免模型從數量較多但已過期的範例推斷規則。
""",
        [
            "讓 agent 搜尋所有 consumers 如何處理 response ordering、errors 和 missing fields。",
            "用 AI 產生舊版與新版 schema 的 compatibility matrix，再以 contract tests 固化。",
            "請 AI 找出 parse message、sleep-based timing、依賴 dict order 等 accidental coupling。",
            "在 API 變更 review 中讓 AI 草擬 consumer impact summary，附實際引用位置。",
        ],
        [
            "AI 找到的 call sites 只是候選集合，必須加上 runtime traffic 和外部 consumer 資料。",
            "禁止 agent 因測試失敗就擴大 public contract；先判斷測試是否鎖定實作細節。",
            "Schema、error code 和 compatibility policy 需由 owner 核准並版本化。",
            "大規模修正先 dry-run、分批 canary，保留快速 revert 和舊版服務路徑。",
        ],
        """
Domain expert 的重點不是『任何 observable behavior 都不能改』，而是管理 observable surface。越公開、越長壽、consumer 越多的介面，越應以窄 contract、版本策略和 telemetry 投資；單一 repository 內可原子修改的 internal API，則能用大規模變更降低相容成本。
""",
        [
            "列出你熟悉 API 的十個 observable behaviors，標記 declared、de facto 或可自由修改。",
            "修改範例中的英文 message，寫一個脆弱 client 與一個正確 client 比較結果。",
            "設計 unordered response 的測試策略，讓 consumer 無法依賴偶然順序。",
            "請 AI 搜尋一個 repository 中解析 exception message 的位置，人工驗證 false positives。",
        ],
        [
            ("Hyrum’s Law 想提醒什麼？", "當 API 有足夠多使用者，幾乎所有可觀察行為都可能被某人依賴；作者宣告的 contract 不一定等於生態系實際 contract。"),
            ("是否應把所有 accidental behavior 寫入 contract？", "不應。先評估 consumer 影響、合理性和長期成本；可透過 migration 改掉不健康依賴，並減少未來可觀察面。"),
            ("Machine-readable error code 為何比文字穩定？", "Code 可被明確版本與測試，文字則需要改善、翻譯且格式易變。控制流依 code，message 才能安全服務人類。"),
            ("Consumer-driven contract 提供什麼額外證據？", "它描述真實 consumer 需要的互動，而不只是 provider 自認為提供的行為，能在發布前發現整合假設被破壞。"),
            ("為何效能改善也可能是 breaking change？", "執行順序與 timing 改變可能暴露 race、改變 timeout/retry 或讓依賴舊批次行為的 consumer 出錯。Timing 也是 observable surface。"),
            ("AI 如何同時增加與降低 Hyrum 風險？", "它會快速複製現有 accidental pattern，也能更快盤點 consumers 和產生 compatibility tests。結果取決於是否有 canonical contract 與驗證。"),
            ("Internal API 與 public API 的策略為何不同？", "Internal API 若所有 consumers 可同一變更原子更新，可用大規模修改降低相容負擔；public API 無法控制更新時間，需要版本、deprecation 和長 compatibility window。"),
        ],
        ["swe-preface", "swe-deprecation", "swe-large-change", "github-review"],
    ),
    C(
        6,
        "Scale and Growth：規模如何改變問題",
        "為什麼十人團隊有效的做法，搬到一千人或十年 codebase 後可能完全失效？",
        "中階",
        "從 code、traffic、data、organization、time 五種規模辨認相變，避免只做線性擴容。",
        ["scale", "coupling", "ownership", "feedback"],
        """
規模不只是伺服器數量。當 repository、團隊、資料、請求與時間增加，原本可依賴的人腦同步、全量測試、手動發布和單一 owner 會超過負荷。問題常發生相變：不是慢一點而已，而是協調模型、資料結構或失敗模式根本不同。
""",
        """
五人團隊可在聊天室通知 API 修改；五百個 consumers 時訊息一定漏接。每天十次部署可人工看 dashboard；每小時數千個 agent changes 時，沒有自動 risk classification 和 policy gates 就無法運作。
""",
        r"""
規模維度
  code ─────→ search / ownership / modularity / codemod
  people ───→ docs / review policy / platform / governance
  traffic ──→ load balance / capacity / overload control
  data ─────→ partition / migration / integrity / retention
  time ─────→ compatibility / deprecation / knowledge preservation

局部最佳化 × 高耦合
        ↓
coordination edges 約隨參與者快速增加
        ↓
需要自助平台、標準介面與自動 feedback
""",
        """
第一步是辨認正在成長的維度，因為解法不同。Traffic scale 可能需要 horizontal replication；organizational scale 需要 ownership 和標準介面；code scale 需要 search、build graph 和 automated refactoring；time scale 需要 migration discipline。用 Kubernetes 解知識孤島，不會有效。

成長最昂貴的是 coordination edges。每個團隊若都必須與所有其他團隊同步，關係數會快速增加。平台、API contract、style、review 和 self-service tools 的目的，是把多對多協調壓縮成穩定介面。標準化會犧牲局部自由，但換得整體可組合性。

Scale 也要求分層 feedback。小系統可每次跑全部測試；巨大 codebase 需要 dependency graph、test selection 與 post-submit verification。小流量可人工觀察；大流量需 SLO、aggregation 和 automation。關鍵不是追求最大規模方案，而是在接近轉折點前建立下一層能力。
""",
        [
            "分別量測 code、people、traffic、data 和 time，而非只用『系統很大』描述。",
            "找出目前依賴人腦同步或全域鎖步的 coordination bottleneck。",
            "以 stable interface、ownership 和 self-service platform 減少多對多溝通。",
            "建立分層 feedback：快速局部 checks 加較慢全域 verification。",
            "保留 escape hatch 與例外治理，避免標準平台阻止真正特殊需求。",
        ],
        "小模型計算團隊溝通邊數。它不是組織定律，但能直觀看出全連接協調為何不可持續。",
        r"""
def coordination_edges(teams: int) -> int:
    return teams * (teams - 1) // 2

for n in (5, 20, 100):
    print(f"{n:>3} teams -> {coordination_edges(n):>5} possible edges")

# 以平台介面取代所有 pairwise 協調：
def platform_edges(teams: int, platform_teams: int = 1) -> int:
    return teams * platform_teams
""",
        [
            "五個團隊只有十條可能關係，人際同步仍可工作。",
            "一百個團隊有 4,950 條 pairwise edges，任何全員口頭協議都會漏失。",
            "共同平台把多數協調改成團隊對穩定介面的關係，接近線性。",
            "平台本身成為關鍵 dependency，因此必須有 SLO、版本與使用者研究。",
        ],
        [
            "過早建立通用平台可能抽象尚未穩定的需求，成為另一個瓶頸。",
            "標準化若沒有 escape hatch，特殊工作會建立 shadow system 繞過治理。",
            "只擴機器不降低 coupling，部署和事故 blast radius 仍會成長。",
            "把 headcount 或 code lines 當價值，會鼓勵增加規模而非降低必要複雜度。",
        ],
        """
AI 提高個人產出後，organization scale 的瓶頸更快從撰寫轉到 review、shared context、platform capacity 和 decision coherence。若每個 agent 都生成自己的 library、framework 和操作方式，局部速度會轉成全域碎片化。業界較成熟的方向是提供共用 agent instructions、標準 tools、內部平台和小批次變更，讓速度沿相同 guardrails 流動。
""",
        [
            "用 AI 建立跨 repository dependency 和 ownership 地圖。",
            "將公司標準封裝成 formatter、policy check、scaffold 和 agent tool。",
            "讓 agent 依 dependency graph 選 relevant tests，縮短大型 codebase feedback。",
            "用 AI 摘要跨團隊 change impact，但由 service owners 確認 contract。",
        ],
        [
            "限制 agent 建立新 dependency 或 framework，要求先搜尋 canonical solution。",
            "平台工具必須版本化、有 SLO、fallback，且不能把所有 production 權限集中給模型。",
            "變更維持 small batch；產碼更快不能成為巨大 PR 的理由。",
            "衡量 rework、review queue、duplication 和 incidents，監控 AI 是否放大 coordination cost。",
        ],
        """
真正的 scale 技巧是刪除協調，而不是更努力協調。穩定 API、單一 canonical tool、自助平台和清楚 ownership 都是在減少必須同時知道全部細節的人數。但平台不能只服務治理者；若使用者體驗差，團隊會繞路，組織便同時支付官方和 shadow system 兩套成本。
""",
        [
            "計算你所在組織可能的 team edges，列出最常見的三種跨團隊同步。",
            "為其中一種同步設計 stable interface 或 self-service workflow。",
            "找一個大型 PR，嘗試拆成五個可獨立驗證、可回退的小變更。",
            "請 AI 搜尋 repository 中功能相似的三個 library，分析整併前需要哪些 owner 證據。",
        ],
        [
            ("Scale 為何不是單一數字？", "Code、people、traffic、data 和 time 各自產生不同 constraint；必須先辨認哪個維度成長，才知道需要平台、分片、相容或容量方案。"),
            ("為何 pairwise coordination 不可持續？", "參與者增加時可能關係快速增加，人腦和同步會議無法可靠覆蓋。穩定介面與平台能將多對多改成較少的標準關係。"),
            ("平台如何同時降低與增加成本？", "它降低重複建設和協調，但本身成為 dependency、治理與學習成本。只有當共同需求穩定且使用者體驗好時，收益才會超過成本。"),
            ("大型 codebase 為何需要分層測試？", "每次全量執行可能太慢；依 dependency graph 先跑快速 relevant tests，再由 post-submit 或週期工作補全域 coverage，可以兼顧速度與風險。"),
            ("AI 為何可能讓 codebase 更碎片化？", "產生新 helper 或 library 很便宜，agent 若不知道 canonical path，就會為每個局部問題創造另一套方案，增加 dependency 和認知成本。"),
            ("如何知道團隊接近 scale 轉折點？", "觀察 review queue、等待時間、重複工具、跨團隊 incident、全量測試時間、手動步驟和 owner 不明等 signals，而非等全面失效。"),
            ("本章最重要的 scale 原則是什麼？", "先減少需要協調的 edges，再自動化剩餘流程；不要用更多會議或更多 AI 生成內容掩蓋高耦合設計。"),
        ],
        ["swe-preface", "swe-scale-lead", "swe-compute", "dora-ai"],
    ),
    C(
        7,
        "Trade-offs、Costs 與 Architecture Decision Records",
        "沒有完美解法時，如何讓『我覺得』變成可檢查、可重訪且不假裝精確的工程決策？",
        "中階",
        "用 constraints、alternatives、cost model、signals 和 reversal plan 做取捨，並以 ADR 保存決策原因。",
        ["tradeoff", "constraint", "adr", "goal-signal-metric"],
        """
工程選擇幾乎都同時改變多個目標：cache 降低 latency 卻增加 stale data；更多 replicas 提高 availability 卻增加成本與一致性難度；嚴格 review 降低缺陷卻增加 lead time。若不顯式列出目標與成本，討論會退化為工具偏好或職級較高者的直覺。
""",
        """
團隊要決定 checkout 是否採同步呼叫風控，或先接受訂單再非同步審核。前者結果即時但 dependency outage 直接阻塞付款；後者提高 availability，卻需要補償、狀態機和客戶溝通。答案取決於詐欺成本、延遲目標與可逆性。
""",
        r"""
Problem / decision deadline
        ↓
Hard constraints ──→ 不符合者淘汰
        ↓
Alternatives
        ↓
cost dimensions:
latency · reliability · complexity · people · money · security · lock-in
        ↓
choose + assumptions + reversible steps
        ↓
signals / review date / invalidation conditions
        ↓
ADR 更新或 supersede
""",
        """
先分 hard constraint 與 preference。法規、資料不可遺失、相容承諾可能是硬限制；使用某語言或雲服務通常只是偏好。把偏好假裝成 constraint 會過早消滅選項，把真正 constraint 當偏好則會產生不可接受風險。

Cost model 不必精準到小數點，但要涵蓋全生命週期。購買成本便宜的工具可能需要更多 on-call；開發最快的架構可能讓每次 migration 都昂貴。至少比較建置、運行、失敗、修改和退出成本。也要指出 uncertainty，避免虛假精確。

ADR 是決策快照：背景、選項、選擇、理由、代價、假設、signals 和何時重訪。它不應成為不可挑戰的聖旨；新 evidence 出現時以新 ADR supersede 舊決策，保留歷史即可。可逆決策應快速實驗，不可逆或 blast radius 大的決策才需要深度分析。
""",
        [
            "用一句話定義要做的 decision、owner 和最晚決策時間。",
            "列 hard constraints、goals 和 non-goals，避免每個選項解不同問題。",
            "至少提出三個 alternatives，包括『維持現況』，比較全生命週期成本。",
            "先選可逆、分階段方案，定義 rollout、rollback 與觀測 signals。",
            "寫 ADR 並設定 review trigger，而非讓決策理由留在聊天記錄。",
        ],
        "範例用加權分數幫助揭露假設。它不是自動決策器；權重與分數本身就是需要討論的 judgment。",
        r"""
OPTIONS = {
    "sync":  {"latency": 2, "availability": 1, "simplicity": 4, "fraud": 5},
    "async": {"latency": 4, "availability": 5, "simplicity": 2, "fraud": 3},
    "hybrid":{"latency": 3, "availability": 4, "simplicity": 3, "fraud": 4},
}
WEIGHTS = {"latency": 2, "availability": 5, "simplicity": 2, "fraud": 4}

def score(option: dict[str, int]) -> int:
    return sum(option[key] * WEIGHTS[key] for key in WEIGHTS)

for name, values in OPTIONS.items():
    print(name, score(values))
""",
        [
            "權重顯示此決策特別重視 availability 和 fraud，而非假裝所有面向相等。",
            "分數迫使團隊解釋為何 `sync` availability 只有 1，從而暴露 dependency 假設。",
            "小幅分數差異不應被解讀成科學證明；可用 prototype 或 canary 收集新 evidence。",
            "ADR 應保存原始 matrix、uncertainty 和之後實際指標，方便校準判斷。",
        ],
        [
            "Weighted matrix 容易把主觀數字包裝成客觀答案，忽略不可加總的 hard constraints。",
            "只計算雲端帳單會漏掉 on-call、migration、training 和 opportunity cost。",
            "追求可逆性也有代價；永久雙軌設計可能比果斷選擇更複雜。",
            "ADR 太長、沒有 owner 或從不重訪，會變成另一個失效文件庫。",
        ],
        """
AI 很適合發散 alternatives、找遺漏 cost dimensions、整理過往 ADR 和模擬反方，但它傾向給出流暢而不一定適用的建議。Model 不知道組織真正的風險承受、人才、合約和政治約束，除非 context 明確提供。AI 應幫助 decision quality，而不是成為『是模型選的』責任逃生口。
""",
        [
            "讓 AI 先扮演支持者與反對者，分別 steelman 每個 alternative。",
            "請 agent 搜尋 repository、incidents 和 ADR 中與選項相關的本地 evidence。",
            "用 AI 草擬 ADR 結構、列出未回答問題與可驗證 assumptions。",
            "決策後讓 AI 定期比較 signals 與 ADR 假設，提出需要重訪的候選。",
        ],
        [
            "ADR 的 owner、risk acceptance 和最終選擇必須是具名的人或團隊。",
            "要求 AI 引用本地 evidence；沒有資料時明確標為 assumption，不可虛構數字。",
            "敏感商業、法規與人事 context 只在批准範圍內提供模型。",
            "高不可逆決策需獨立 review、prototype 或 staged commitment，不能只靠一次生成報告。",
        ],
        """
專家通常先問決策是否可逆，再決定分析深度。對可逆選擇，最快取得真實 feedback 的小實驗常勝過長會議；對資料格式、public API、供應商綁定等難逆選擇，退出成本和 migration path 比第一年功能表更重要。好的 ADR 不是證明當時永遠正確，而是讓後人知道當時在什麼 evidence 下合理。
""",
        [
            "挑一個待決問題，寫出 hard constraints、三個 options 和『不做』選項。",
            "執行 scoring 範例，調整 weights，觀察答案如何反映價值判斷。",
            "寫一頁 ADR，必須包含 assumptions、rollback、signals 和 review trigger。",
            "讓 AI 提出反方意見，再標記哪些論點有 evidence、哪些只是通用說法。",
        ],
        [
            ("Hard constraint 與 preference 如何區分？", "Hard constraint 被違反就使方案不可接受；preference 可用其他收益交換。判斷時要問是否存在任何合理情況可以犧牲它。"),
            ("為何一定要包含『維持現況』？", "改變也有 migration 和風險成本；若不比較現況，團隊可能只在新工具間選擇，忽略問題尚未值得解。"),
            ("Weighted score 最大風險是什麼？", "主觀權重和分數看起來像客觀數學，讓人忽略 uncertainty、hard constraints 和指標不可直接相加。它應促進討論，不是自動裁決。"),
            ("ADR 為什麼要記錄 invalidation condition？", "當關鍵 assumption 不再成立，團隊能主動重訪，而不是把舊決策永久化或靠新人猜測。"),
            ("可逆決策為何通常應快速行動？", "可以用小成本 rollback，真實 feedback 比抽象預測更有資訊；過度分析本身是 opportunity cost。"),
            ("AI 在決策中最危險的角色是什麼？", "成為權威或責任替代品。它可生成論點，但不承擔商業、法律和營運後果，也可能缺少本地 context。"),
            ("如何判斷一份 ADR 有價值？", "幾個月後的工程師能用它理解問題、constraints、被否決選項、選擇理由與何時應重訪，而不是只看到最後結論。"),
        ],
        ["swe-preface", "swe-productivity", "dora-ai", "nist-genai"],
    ),
]
