"""Part 2: teams, knowledge, equity, leadership, and measurement."""
from __future__ import annotations

from swe_sre_ai_model import C


CHAPTERS = [
    C(
        8,
        "HRT、Ownership 與真正的團隊合作",
        "多人一起寫 code 為什麼不等於團隊？什麼條件能讓不同專長在高壓變更中仍然合作？",
        "入門",
        "把 humility、respect、trust 轉成可觀察的 review、ownership、求助和決策行為。",
        ["ownership", "psychological-safety", "bus-factor", "feedback"],
        """
複雜系統不可能由一人理解所有細節；可靠結果來自成員能暴露不確定、交換局部知識並共同承擔結果。若文化獎勵英雄救火、隱藏錯誤和知識壟斷，工具再成熟也只能更快放大單點決策。HRT 不是要求每個人永遠客氣，而是讓技術爭論不必依靠羞辱、地位或個人防衛來取得結論。
""",
        """
付款服務在凌晨失敗。懂資料庫的人、懂 deploy 的人和 product owner 各自掌握一部分事實。若大家爭論誰造成事故，恢復會延後；若角色清楚、能安全說「我不知道」，團隊可以先 rollback，再共同重建因果。
""",
        r"""
共同目標 / 使用者結果
          ↓
   明確 ownership
   ├─ component owner
   ├─ decision owner
   ├─ incident roles
   └─ escalation path
          ↓
Humble: 我的模型可能不完整
Respect: 批評 idea，不貶低人
Trust: 給能力相稱的自治與支援
          ↓
早期暴露風險 → 快速 feedback → 共同修正
""",
        """
Humility 是承認自己看見的是局部，不是降低標準。它表現在設計文件列出 uncertainty、reviewer 願意被反證、incident commander 主動詢問反方 signal。Respect 是把人與產出分開：可以明確說某變更不安全，但要指出 constraint、evidence 和可改善路徑。Trust 則是讓成員在清楚邊界內做決策，同時提供求助與 rollback。

Ownership 不是「出了事找誰怪罪」，而是誰維持 contract、處理 feedback、安排改善並決定風險。單一元件可以有 primary team，但 production path 通常跨多個 owners；因此 escalation 和 handoff 必須顯式。若所有問題都回到最資深英雄，名義 ownership 並沒有真正分散。

健康團隊會把 cooperation 寫進流程：小型 review 讓意見容易交換、design review 先對齊 constraints、on-call pairing 傳遞操作知識、postmortem 將脆弱點轉成共同資產。文化不是牆上的價值觀，而是資訊遇到壞消息時實際如何流動。
""",
        [
            "先對齊共同使用者結果，避免每個職能只優化自己的局部 metric。",
            "為 component、decision、incident 與 escalation 分別指定 owner，避免責任模糊。",
            "在 review 中要求 claim 附 evidence，也允許作者清楚標記 uncertainty。",
            "以 pairing、rotation 和文件降低英雄依賴，使求助不必跨越地位障礙。",
            "事故後檢查系統與 incentives，避免把合理行動簡化成個人失誤。",
        ],
        "以下用簡單 ownership registry 表示 owner 不是名字註解，而是能被工具驗證的 routing contract。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Ownership:
    team: str
    escalation: str
    runbook: str

REGISTRY = {
    "checkout-api": Ownership("payments", "#payments-oncall", "runbooks/checkout.md"),
    "deploy-platform": Ownership("platform", "#platform-oncall", "runbooks/deploy.md"),
}

def route(component: str) -> Ownership:
    try:
        return REGISTRY[component]
    except KeyError:
        raise ValueError(f"unowned component: {component}")
""",
        [
            "Registry 同時提供負責團隊、緊急 escalation 和操作知識入口。",
            "未知 component 立即失敗，讓 ownership 缺口在 CI 或 inventory job 中被看見。",
            "Primary owner 不表示所有修改只能由該團隊完成，而是由它維持 contract 和 review。",
            "真實系統還應加入備援 owner、時區、資料等級與最後驗證日期。",
        ],
        [
            "過度強調 ownership 可能形成領地意識，使其他人不敢改善或 owner 成為 review bottleneck。",
            "只寫團隊名稱卻沒有 on-call、runbook 和 capacity，等同把責任貼標籤。",
            "表面和諧若禁止尖銳技術反對，會讓風險延後到 production。",
            "把 incident 個人化會鼓勵隱藏資訊，降低下一次早期 signal 的品質。",
        ],
        """
AI 讓個人能跨越更多技術領域，但不能因此假設 ownership 不再需要。Agent 可能修改它不理解的下游 contract，也可能讓團隊誤以為「任何人都能維護任何 code」。更成熟的方式是讓 ownership metadata、architecture boundaries 和 escalation path 對 agent 可讀，並要求跨邊界變更自動找到對應 reviewer。
""",
        [
            "讓 AI 依 ownership registry 為 diff 找 reviewers 和可能受影響團隊。",
            "用 agent 將 incident timeline 或 review thread 摘要成共享事實，減少資訊不對稱。",
            "請 AI 指出設計中的 uncertainty、未回答問題和需要其他 domain owner 的位置。",
            "以 AI 協助新成員閱讀 runbook、模擬事故和準備向 expert 提問。",
        ],
        [
            "Agent 不得成為 owner；每個變更、服務和 production action 都要有具名人類團隊。",
            "跨 ownership boundary 的修改需要對方 reviewer 或明確 delegated policy。",
            "AI 摘要不能刪除 dissent、uncertainty 和原始證據連結。",
            "績效制度不能因使用 AI 較少或較常求助而懲罰成員，否則壞消息會被隱藏。",
        ],
        """
資深團隊既不把 ownership 做成封閉領地，也不接受「大家都負責」的空話。好的邊界允許他人貢獻，但清楚誰維持標準、誰能接受風險、誰在事故時回應。AI 可以降低知識入口成本，卻無法替代長期照顧元件、承擔取捨和建立信任的社會責任。
""",
        [
            "列出一條 production request path，為每個 component 補上 owner、on-call 和 runbook。",
            "執行範例，加入一個沒有 owner 的 dependency，設計 CI 如何阻止發布。",
            "找一段最近的 review，將人身或偏好式評論改寫成 constraint、evidence 和建議。",
            "請 AI 摘要一次技術爭論，再人工檢查它是否遺漏少數意見與 uncertainty。",
        ],
        [
            ("HRT 是否等於避免衝突？", "不是。HRT 讓團隊可以直接而有證據地挑戰 idea，同時不羞辱人；真正的技術分歧應更早被提出，而非被禮貌掩蓋。"),
            ("Ownership 與 blame 最大差異是什麼？", "Ownership 指維持 contract、回應 feedback 和安排改善的責任；blame 把系統結果簡化成個人道德問題，通常無法降低再發風險。"),
            ("為什麼『大家都負責』通常不可靠？", "沒有清楚 primary owner 時，維護、值班和跨團隊協調容易被假設成別人會處理；共享參與仍需要明確 accountable party。"),
            ("Trust 如何避免變成無限制授權？", "信任應搭配能力、風險邊界、observability 和 rollback。給予範圍內自治並保留支援與升級，不等於取消 review 或 control。"),
            ("AI 為何不能被列為 service owner？", "模型不承擔法律、商業和倫理責任，也不會自行維持長期 context、值班與風險接受；工具操作必須回到具名人類 ownership。"),
            ("如何知道團隊過度依賴英雄？", "觀察只有一人能 deploy、事故總找同一人、文件和 rotation 缺失、休假時變更停止，以及重要決策只存在私人記憶。"),
            ("本章對可靠性最直接的影響是什麼？", "讓壞消息、未知與跨 domain 風險能早期流動；越早暴露，修復成本和 production blast radius 通常越低。"),
        ],
        ["swe-teams", "swe-knowledge", "sre-incident", "dora-ai"],
    ),
    C(
        9,
        "Psychological Safety：讓壞消息提早出現",
        "心理安全為什麼是工程控制，而不只是讓工作氣氛舒服？",
        "初階",
        "建立能安全提出疑問、承認錯誤和升級風險的機制，同時維持高技術標準。",
        ["psychological-safety", "feedback", "ownership", "incident-command"],
        """
複雜系統的早期危險通常先以弱信號出現：新人看不懂 deploy、值班者覺得 alert 不可信、工程師擔心 migration 無法 rollback。若說出疑慮會被嘲笑或影響績效，這些資訊就會留在個人腦中，直到 production 用更昂貴的方式證明它們。
""",
        """
發布會議中，一位工程師發現 rollback script 從未在新 schema 上測過。若團隊把「別阻礙進度」當文化，他可能沉默；若 pause-and-check 被視為專業行為，十分鐘 game day 可能避免數小時 outage。
""",
        r"""
弱信號
  ├─「我不懂」
  ├─「這裡沒有證據」
  ├─「我操作錯了」
  └─「這個 SLO 可能不代表使用者」
          ↓
安全通道 + 無報復升級 + 明確回應
          ↓
question / review / pause / experiment
          ↓
更早、更便宜的 failure discovery

心理安全 + 高標準 ≠ 降低要求
""",
        """
心理安全的核心是 interpersonal risk：成員是否能在不知道答案、不同意權威或承認失誤時仍被公平對待。它與績效標準是兩條軸；團隊可以同時要求嚴格 evidence，又不因提問者職級、口音或過去錯誤忽略訊息。

安全要有結構支持。Design review 可固定詢問反方和 rollback；incident 開場明確說明先恢復、後分析；leader 公開修正自己的判斷；升級管道不必經過被挑戰者本人。若只說「歡迎提問」，但提出問題後沒有回應，文化不會改變。

另一方面，心理安全不是所有 idea 都同樣正確，也不是免除 accountability。對高風險操作仍要追蹤誰做了什麼、當時有哪些 evidence、policy 是否合理。Blameless 的意思是理解行動所在系統，不是刪除事實或後果。
""",
        [
            "Leader 主動說出自己的 uncertainty，示範模型可以被修正。",
            "Review 和 launch checklist 固定詢問 dissent、rollback 與 missing evidence。",
            "事故中分離恢復與責任調查，保護即時資訊流。",
            "對提出風險的人回報處理結果，讓升級行為被正向強化。",
            "定期以匿名 survey、retrospective 和行為例子檢查安全感，而非只靠口號。",
        ],
        "這個簡單的 preflight 函式把『可以按暫停』做成流程。任何一項未知都回傳阻擋原因，而不是讓職級決定是否忽略。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class LaunchEvidence:
    rollback_tested: bool
    owner_oncall: bool
    slo_dashboard_ready: bool
    dissent_resolved: bool

def launch_decision(e: LaunchEvidence) -> tuple[bool, list[str]]:
    missing = [
        name for name, ready in vars(e).items()
        if not ready
    ]
    return (not missing, missing)

ready, reasons = launch_decision(
    LaunchEvidence(True, True, False, False)
)
print("GO" if ready else f"PAUSE: {reasons}")
""",
        [
            "Checklist 把提出疑慮從個人勇氣轉成正常工作流程。",
            "`dissent_resolved` 不表示所有人同意，而是反對理由已被 owner 回應並記錄。",
            "Missing dashboard 是可修復的 evidence gap，不是某人的能力評價。",
            "高風險 launch 的 decision owner 仍需接受剩餘風險並留下理由。",
        ],
        [
            "匿名管道有助揭露問題，但若所有溝通都匿名，團隊難以共同解決具體細節。",
            "把任何不舒服都稱為不安全，可能阻止必要且尊重的績效或風險討論。",
            "Leader 說歡迎反對，卻獎勵永不延誤發布的人，實際 incentives 仍會壓制信號。",
            "過度 checklist 化可能讓人機械勾選，而不理解真正風險。",
        ],
        """
AI 讓成員能私下詢問「不敢問的問題」，降低學習門檻；但也可能讓人隱藏不理解、直接採用模型答案，或因監控 prompt 而不敢探索。組織需要清楚說明 AI 使用資料如何保留、是否用於績效，以及何時必須向人升級。安全使用 AI 包含能公開說「模型建議但我沒有驗證」。
""",
        [
            "提供私密的 AI 教學助手，幫助新人形成更精確的人類提問。",
            "讓 AI 在 design review 產生 red-team questions，確保少數觀點被討論。",
            "用 AI 匿名聚類 retrospective 主題，但保留原意與可選擇退出。",
            "讓 incident assistant 主動標記 conflicting evidence，而非只生成單一敘事。",
        ],
        [
            "不得用 prompt 數、求助內容或 AI 錯誤作為未告知的個人績效監控。",
            "敏感人事、健康和客戶資料不得進入未批准模型。",
            "AI 回答要明確標示 uncertainty 和來源，允許成員不接受其權威。",
            "任何 safety concern 都要有人類 escalation path，不能被 bot 自動關閉。",
        ],
        """
心理安全最可靠的測試不是 survey 分數，而是壞消息到來時 leader 怎麼做：提出風險的人是否被感謝、發布是否真的能 pause、事故資訊是否被懲罰性使用。AI 可以提供另一個提問入口，但如果組織權力和 incentives 沒有改變，它只會成為更安靜的繞道。
""",
        [
            "回想最近一次有人挑戰發布，記錄 leader、流程和績效信號如何回應。",
            "執行範例，為不同風險等級設計可接受的 missing evidence。",
            "在下一份 design doc 加入『最強反對理由』與『哪些信號會讓我們停下』。",
            "撰寫 AI 使用透明政策：哪些 prompt 被保留、誰能看、不能用於哪些決策。",
        ],
        [
            ("心理安全如何直接改善可靠性？", "它讓未知、錯誤和弱信號在 production 事故前被提出，縮短發現時間；資訊若因人際風險被壓制，技術控制也得不到正確輸入。"),
            ("心理安全是否與高標準衝突？", "不衝突。可以嚴格要求 evidence、測試和改進，同時不羞辱提問或犯錯的人；安全是討論方式，高標準是結果要求。"),
            ("Blameless 是否表示不追蹤誰做了操作？", "不是。必須重建行動、權限和決策脈絡；blameless 是避免用個人缺陷取代系統分析，仍保留 accountability 與必要後果。"),
            ("為什麼只說『歡迎提問』不夠？", "成員會根據過往回應和 incentives 判斷風險。需要固定流程、leader 示範、無報復升級和對問題的實際處理結果。"),
            ("AI 如何降低又可能傷害心理安全？", "它提供低壓學習入口；但 prompt 監控、模型權威和私下採用未驗證答案可能讓真實未知更難被團隊看見。"),
            ("`dissent_resolved` 應如何解讀？", "不是要求一致同意，而是反對內容被準確記錄、由 decision owner 回應，剩餘風險與決策理由可被追蹤。"),
            ("如何辨認表面安全、實際不安全的團隊？", "會議沒有衝突但事故總是意外、發布從不 pause、同一批人發言、壞消息私下流傳，以及提出風險者被標記成不合作。"),
        ],
        ["swe-teams", "swe-knowledge", "sre-postmortem", "nist-genai"],
    ),
    C(
        10,
        "Knowledge Sharing、Readability 與 Bus Factor",
        "如何把『問那位資深工程師』變成任何人與 agent 都能走的可靠知識路徑？",
        "中階",
        "設計知識從發現、驗證、發布、搜尋到淘汰的生命週期，而不是堆積更多文件。",
        ["bus-factor", "design-doc", "context", "provenance"],
        """
知識若只存在個人腦中，團隊的 capacity 和可靠性就被最稀缺的人限制；若全部寫成文件卻無法搜尋、沒有 owner 或過時，讀者仍會回去問人。知識分享真正要管理的是可信來源、發現路徑、更新責任和實作 feedback。
""",
        """
新值班者遇到 queue lag，搜尋得到三份互相衝突的 runbook；最舊一份排名第一，指示已不存在的按鈕。文件很多，但知識系統失敗。正確入口應標記 canonical、owner、最後驗證與 service version。
""",
        r"""
Tacit knowledge / incident / design
            ↓
        capture draft
            ↓
expert review + runnable verification
            ↓
canonical home + owner + version + metadata
            ↓
search / onboarding / agent retrieval
            ↓
usage feedback + freshness check
            ↓
update / supersede / archive
""",
        """
知識有 tacit 和 explicit 兩種。Tacit knowledge 包含判斷、例外和肌肉記憶，不可能一次全部文件化；pairing、rotation、office hours 和 incident shadowing 能傳遞這部分。Explicit knowledge 則應有 canonical home、結構、owner 和更新觸發，例如 API contract、runbook 與 ADR。

Readability 不只是語法漂亮，而是讓 codebase 的慣例能被一致教導與 review。文件解釋 why 和入口，code/test/schema 則保存可執行 truth。最健康的知識路徑通常是薄入口加深層來源：一頁 service map 指到 design、dashboard、runbook 和 source，而不是複製所有內容。

文件也需要 lifecycle。建立時記錄 audience、owner、last verified、scope 和 supersedes；使用時提供 feedback；系統或 API 變更時由 CI 提醒相關文件；無法維護的內容應 archive。搜尋排名必須偏好 canonical 和新鮮來源，否則更多文件會降低答案品質。
""",
        [
            "先畫 service knowledge map，連到 source、owner、API、dashboard、runbook 和 ADR。",
            "對操作文件加入可執行命令或 smoke check，讓內容能被定期驗證。",
            "以 pairing、rotation 和 teaching 補充無法完全文字化的 tacit judgment。",
            "為文件設定 owner、last verified、version 和 superseded-by metadata。",
            "追蹤搜尋失敗、重複提問和 incident confusion，作為知識產品的 feedback。",
        ],
        "用 metadata 驗證文件新鮮度。真實 CI 可以在服務版本改變或期限到期時提醒 owner，而不是靜默相信內容。",
        r"""
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Doc:
    path: str
    owner: str
    verified: date
    canonical: bool

def stale(doc: Doc, today: date, max_age_days: int = 180) -> bool:
    return (today - doc.verified).days > max_age_days

doc = Doc("runbooks/queue-lag.md", "messaging", date(2026, 4, 1), True)
print(stale(doc, date(2026, 9, 30)))
""",
        [
            "Metadata 讓搜尋和 CI 能辨認 canonical 與可能過時內容。",
            "固定 180 天只是預設；高風險 runbook 應依變更或 game day 驗證得更頻繁。",
            "Fresh date 不證明內容正確，verification 應包含實際演練或命令結果。",
            "沒有 owner 的文件即使今天正確，也缺少未來更新責任。",
        ],
        [
            "要求所有知識都寫成長文件，會增加維護成本並壓抑分享。",
            "同一內容複製到多處會產生分叉；入口應連結 canonical source。",
            "只靠搜尋 popularity 會讓舊但常見文件持續排名較高。",
            "將 tacit judgment 假裝完全文件化，可能讓新人過度自信執行高風險操作。",
        ],
        """
在 AI 時代，repository、文件和工具輸出同時成為人類與 agent 的 context substrate。RAG 能快速找到片段，但若來源互相衝突、ACL 錯誤或沒有 freshness，模型只會更流暢地輸出過時答案。最佳實務是先改善 source-of-truth、metadata 和 access control，再增加生成層；短小的 agent instruction 應指向可驗證資料，而不是複製整個知識庫。
""",
        [
            "用 AI 將 incident、review 和 design 討論草擬成可搜尋知識，再由 owner 核准。",
            "建立 ACL-aware retrieval，只取回使用者原本有權閱讀的 canonical sources。",
            "讓 agent 回答時附來源、版本和 last verified，未知時明確升級給 expert。",
            "分析重複問題與無結果搜尋，找出缺少的文件、工具或 training。",
        ],
        [
            "不得因索引或 embedding 讓 agent 繞過原始文件 ACL。",
            "回答必須保留 provenance；無來源的生成文字不能成為 production runbook。",
            "對高風險操作只提供經 game day 驗證的步驟，並要求人類確認當前環境。",
            "文件變更與 agent instruction 一樣進 version control、review 和 freshness checks。",
        ],
        """
知識平台的成功指標不是頁數，而是正確答案的 time-to-find、重複求助是否下降、值班是否能安全執行，以及來源能否隨系統改變。AI 能大幅改善 interface，但不能修復混亂的底層知識；先做 information architecture 和 ownership，模型才是乘數。
""",
        [
            "為一個服務建立一頁 knowledge map，不複製內容，只連到六個 canonical artifacts。",
            "執行範例，將 freshness threshold 改成依文件風險分級。",
            "搜尋三個常見問題，記錄找到答案所需時間、來源衝突與缺口。",
            "讓 AI 回答一個 runbook 問題，要求逐句附來源，再人工驗證權限和版本。",
        ],
        [
            ("為什麼文件數量不是知識分享的好指標？", "頁數不代表可找到、可信或新鮮。大量重複與過時文件反而增加搜尋成本；應看 time-to-correct-answer、使用與維護 feedback。"),
            ("Tacit knowledge 如何傳遞？", "透過 pairing、rotation、teaching、incident shadowing 和實作 review；文件能記錄原則與入口，但無法完全取代情境判斷。"),
            ("Canonical home 有什麼作用？", "讓更新、連結和搜尋指向同一 source of truth，避免多份副本逐漸產生不同答案。"),
            ("Freshness date 為何不足以保證正確？", "日期可能只是形式更新；高風險內容應透過 smoke test、game day 或實際操作證據驗證。"),
            ("RAG 為何不能自動解決知識混亂？", "Retrieval 只會從既有來源取片段；來源衝突、過時或 ACL 錯誤時，生成層可能把問題包裝成更有說服力的錯誤。"),
            ("Agent instruction 應該多長？", "保持短而具導航性：說明邊界、核心命令、禁區和 canonical sources。大量易變細節應留在可版本與驗證的深層文件。"),
            ("Bus factor 改善的證據是什麼？", "關鍵操作可由多位受訓成員完成、休假不阻塞、on-call 不總升級同一人，且知識入口與演練能持續運作。"),
        ],
        ["swe-knowledge", "swe-docs", "openai-codex", "google-agent-observability"],
    ),
    C(
        11,
        "Engineering for Equity：為不同使用者設計",
        "如果平均使用者一切正常，為什麼產品仍可能對某些群體系統性失敗？",
        "中階",
        "把 equity 轉成需求分群、資料檢查、可及性測試、錯誤預算切片和申訴機制。",
        ["equity", "constraint", "eval", "goal-signal-metric"],
        """
平均值會隱藏少數群體的嚴重失敗。裝置較舊、網路較慢、使用不同語言、需要輔助科技或不符合訓練資料主流的人，可能在整體 success rate 看似良好時持續受傷。Equity 要求團隊在需求、設計、測試與監控中看見差異，而不是等投訴證明存在。
""",
        """
語音登入整體成功率 97%，但對特定口音只有 72%。若 dashboard 只看全域 aggregate，團隊會宣稱達標；若按合法且隱私安全的 cohort 分析，就會發現產品可靠性分配不公平。
""",
        r"""
User research / affected groups
          ↓
requirements + accessibility + harm model
          ↓
representative data / test cohorts
          ↓
design + fallback + appeal path
          ↓
slice metrics / SLO / qualitative feedback
          ↓
发现 disparity → prioritize → verify improvement

平均成功率 ─X→ 代表每個群體都成功
""",
        """
Equality 是給所有人相同條件；equity 則考慮不同起點和障礙，使每個人能合理取得結果。工程上先問誰可能被預設排除：網速、裝置、語言、身心能力、地理、付款方式、資料代表性與權力關係。這不是列完清單，而是邀請受影響者參與需求與測試。

Metrics 必須能切片，但切片本身涉及隱私與統計風險。樣本太小會洩露身分或產生不穩定結論；只用敏感屬性又可能違反政策。需要與 privacy、legal 和 domain experts 合作，使用最小資料、聚合門檻和明確 retention。

設計也要提供 fallback 和 appeal。自動判斷若錯誤，使用者是否知道發生什麼、能否改正資料、是否有人類管道？在 AI 系統中，公平不是只在 model benchmark 測一次，而是從資料、介面、工具權限到 production drift 的端到端責任。
""",
        [
            "在需求階段列出可能受影響群體與失敗後果，邀請代表性使用者研究。",
            "建立 accessibility、低頻寬、舊裝置、語言與資料切片的測試矩陣。",
            "以隱私安全方式量測分群 SLI，設定最低樣本與不公開細粒度資料。",
            "為高影響自動決策提供解釋、fallback、人工覆核與申訴。",
            "發布後監控 drift 和 disparity，將改善列入有 owner 的產品 backlog。",
        ],
        "用簡單函式顯示 aggregate success 如何掩蓋 cohort 差異。Production 分析還需 confidence interval 與 privacy threshold。",
        r"""
events = {
    "fast_network": (9700, 10000),
    "slow_network": (720, 1000),
}

def rate(success: int, total: int) -> float:
    return success / total if total else 0.0

all_success = sum(x[0] for x in events.values())
all_total = sum(x[1] for x in events.values())
print("overall", rate(all_success, all_total))

for cohort, counts in events.items():
    print(cohort, rate(*counts))
""",
        [
            "大群體權重高，使 overall 約 94.7%，但慢網路群體只有 72%。",
            "Slice 指標用來找系統差異，不應直接用來評價或歧視個人。",
            "真實資料要有 minimum cohort size、consent、access control 和 retention。",
            "定量 signal 應與使用者訪談和申訴資料交叉，避免只看可量測者。",
        ],
        [
            "切片太細可能暴露個人，且小樣本波動會造成錯誤決策。",
            "只優化已知 cohorts 可能漏掉交叉身份與未被標記的新群體。",
            "公平 metric 之間可能衝突，不能期待單一公式替代價值判斷。",
            "增加 fallback 若流程羞辱、昂貴或等待過久，形式上存在仍不可及。",
        ],
        """
AI 使語言、無障礙和個人化介面更容易建立，也可能繼承訓練資料偏差、對低代表群體 hallucinate，或讓有付費工具的人獲得不成比例優勢。每個 agent workflow 都應檢查資料來源、拒絕與錯誤率切片、可及性、人工申訴和模型更新 drift；不能用單一 overall eval 宣稱公平。
""",
        [
            "用 AI 產生多語與 accessibility 測試候選，再由母語者和實際使用者驗證。",
            "建立分群 eval set，檢查模型、retrieval 與 tool outcomes 而非只看文字風格。",
            "讓 AI 協助分析大量 qualitative feedback，但保留原始聲音和 minority themes。",
            "在設計 review 讓模型提出可能被預設排除的情境，作為人類研究起點。",
        ],
        [
            "敏感屬性與使用者內容必須有合法目的、最小化、ACL 和 retention policy。",
            "不得讓模型自行決定公平定義或高影響申訴結果。",
            "Eval 報告必須同時呈現 overall、重要 slices、樣本量與 uncertainty。",
            "高影響 AI 決策需要人類覆核、使用者可理解通知與可行的 contest path。",
        ],
        """
Domain expert 不會把 equity 當發布前 checklist，而會把它視為可靠性分配問題：誰得到錯誤預算、誰承受 latency、誰有能力恢復。最重要的工作通常不是選一個 fairness formula，而是讓受影響群體進入需求與 feedback loop，並確保不公平 signal 能真的改變 roadmap。
""",
        [
            "執行範例並新增第三個小 cohort，觀察 overall 對它有多不敏感。",
            "為你熟悉的產品列出五種非主流使用環境及各自失敗後果。",
            "設計一份 slice dashboard，加入樣本量、隱私門檻和 qualitative feedback 入口。",
            "為 AI 自動判斷流程畫出通知、fallback、人工覆核和申訴路徑。",
        ],
        [
            ("Equity 與 equality 的差別是什麼？", "Equality 提供相同條件；equity 考慮不同障礙與起點，設計必要支持，使不同群體能取得合理結果。"),
            ("為什麼 overall metric 可能誤導？", "大群體主導加權平均，少數群體的嚴重失敗可能只讓總數小幅變動；需要代表性 slices 和 qualitative evidence。"),
            ("切片越細是否越好？", "不是。小樣本不穩定且可能洩露身分；應依風險選重要 cohorts，設定聚合門檻並遵守資料最小化。"),
            ("公平問題可以由一個數學 metric 解決嗎？", "通常不能。不同公平定義可能衝突，還涉及歷史、權力和後果；metric 提供 evidence，但價值取捨需要跨領域治理。"),
            ("AI 如何幫助 accessibility？", "可協助產生替代文字、多語介面、語音與個人化輔助，但輸出仍需實際使用者與專家驗證，避免流暢卻不準確。"),
            ("為何 appeal path 是系統設計的一部分？", "高影響自動化必然會有錯誤；若使用者無法知道、修正或覆核，模型錯誤就成為不可逆傷害。"),
            ("如何知道 equity 工作不是形式勾選？", "分群 evidence 會影響 priority、SLO、設計和資源；受影響者能參與並看見改善，而不是只在文件列出一段聲明。"),
        ],
        ["swe-equity", "swe-productivity", "nist-genai", "owasp-llm"],
    ),
    C(
        12,
        "Tech Lead、Manager 與 Decision Rights",
        "Leader 應親自做所有重要決定，還是完全放手？如何讓速度、品質與人成長同時成立？",
        "中階",
        "分清方向、決策、執行、諮詢與風險接受，建立能力相稱的 delegation ladder。",
        ["ownership", "adr", "tradeoff", "feedback"],
        """
團隊常因角色含糊而卡住：Tech Lead 以為 manager 決架構，manager 以為 senior engineer 已對齊，工程師等待批准，事故時又沒人知道誰能 rollback。領導的核心不是成為最大吞吐量的個人，而是設計一個團隊能持續做出好決策並成長的系統。
""",
        """
資料 migration 需要選擇 rollout。TL 負責技術 constraints，PM 說明使用者期限，manager 確保人力與 escalation，service owner 接受 production risk，實作者準備計畫。若所有權力集中 TL，速度和接班都受限；若無 decision owner，討論永遠不結束。
""",
        r"""
Mission / priorities
        ↓
Decision map
  ├─ who decides?
  ├─ who must be consulted?
  ├─ who executes?
  ├─ who accepts risk?
  └─ when to escalate?
        ↓
Delegation ladder
tell → propose → decide with review → decide and inform → own
        ↓
feedback / coaching / expanded autonomy
""",
        """
Tech Lead 通常照顧技術方向、quality bar、跨元件取捨與技術 mentoring；manager 照顧團隊健康、人才、資源、績效和組織介面。實際公司可能不同，因此重點不是職稱，而是 decision rights 要寫清楚。Product、security、privacy 和 SRE 也可能對某些風險有否決或簽核責任。

Delegation 不是二元。對陌生高風險任務，leader 可先提供具體方向；能力與 context 增加後，成員先提出方案，再逐步取得直接決定並通知的權限。每次都由 leader 重做會阻止成長；完全放手卻不提供 constraints 和 feedback 則是 abandonment。

好的 leader 管理系統 bottleneck。他們讓工作可見、限制 work in progress、清除跨團隊阻塞、建立 review coverage，並保留深入技術的能力以判斷風險。最重要的是讓成功不依賴自己在線：文件、delegated ownership 和 successor growth 都是領導產出。
""",
        [
            "為常見決策建立 decision map，明確 decide、consult、execute、risk owner。",
            "依任務風險與成員熟悉度選 delegation level，提前說明 escalation triggers。",
            "使用 design/ADR 對齊 constraints，不在實作完成後才重新爭論方向。",
            "以定期 feedback 校準 autonomy，指出 evidence 和影響，而非只給模糊評語。",
            "追蹤 leader 是否成為 review、deploy 或跨團隊資訊的單點瓶頸。",
        ],
        "用政策函式表達 delegation 取決於風險和 readiness，而不是只看職級。數字不是績效分數，而是討論起點。",
        r"""
LEVELS = {
    1: "follow explicit plan",
    2: "propose, leader decides",
    3: "decide with required review",
    4: "decide and inform",
    5: "own outcome and policy",
}

def delegation_level(risk: int, familiarity: int) -> int:
    # risk/familiarity: 1..5
    raw = familiarity - max(0, risk - 3)
    return min(5, max(1, raw))

print(LEVELS[delegation_level(risk=5, familiarity=3)])
""",
        [
            "高風險會降低當前 delegation level，但不代表永久否定成員能力。",
            "Familiarity 包含 domain、production 和組織 context，不只是 coding skill。",
            "Required review 是 guardrail，也可成為刻意教學點。",
            "成熟團隊應記錄何種 evidence 能提升 level，避免權力只靠主觀感受。",
        ],
        [
            "Decision map 太細會讓每個小決定都等待矩陣查詢，應聚焦高頻或高風險邊界。",
            "Leader 以品質為由重寫所有 code，會造成 learned helplessness 和單點瓶頸。",
            "只委派執行、不委派問題理解與決策，成員無法成長為 owner。",
            "過早給 production mutation 權限，可能把 coaching 問題轉成使用者事故。",
        ],
        """
AI 讓 leader 可以更快取得選項、摘要和 draft，也容易製造『看起來什麼都完成』的錯覺。Decision rights 必須延伸到 agent：誰可以要求它改 code、誰核准 merge、哪些 tool 能用、誰接受結果風險。Leader 的新能力包括設計 agent-friendly environment、評估 evidence，而不是親自閱讀每一行生成內容。
""",
        [
            "讓 AI 準備 one-on-one 或 design review 的事實摘要，但由人決定回饋與優先級。",
            "用 agent 對 ADR 做 pre-review，找缺少 constraints、owners 和 rollback。",
            "把 delegation policy 編碼到 repository 和 tool permissions，減少每次臨時判斷。",
            "用 AI 產生 coaching exercises、事故模擬和不同難度的成長任務。",
        ],
        [
            "不得將人事評估、升遷或懲處直接委派給模型決定。",
            "Agent autonomy 必須有具名 sponsor、scope、expires、audit 和 emergency revoke。",
            "AI 摘要可能省略語氣與少數證據，高影響決策必須回看原始資料。",
            "Leader 對模型建議的採用負責，不能用『AI 說的』轉移 accountability。",
        ],
        """
最好的 leader 不是做最多決策，而是提升團隊正確做決策的範圍。他們保留足夠深度辨認危險，卻把 context、權限和 feedback 分散出去。AI 會讓執行更便宜，因此 leader 更要把注意力放在 problem selection、constraints、系統性風險和人的成長。
""",
        [
            "列出團隊五種常見決策，為每種填 decide、consult、execute 和 risk owner。",
            "執行範例，為同一成員比較低風險文件和高風險 schema migration 的 delegation。",
            "找出 leader 每週三個重複 approval，判斷能否改成 policy 或 guardrail。",
            "為 coding agent 寫一份 delegation card：scope、allowed tools、required checks、approval、expiry。",
        ],
        [
            ("Tech Lead 與 manager 的固定分工是什麼？", "沒有跨公司的固定答案；常見上 TL 偏技術方向與品質，manager 偏人員與組織。真正重要的是每類決策的權利與責任被顯式化。"),
            ("Delegation 和 abandonment 有何差別？", "Delegation 提供目標、constraints、權限、支援、feedback 和 escalation；abandonment 只丟出任務，卻不提供成功條件與必要 context。"),
            ("為什麼 familiarity 不等同 coding 年資？", "高風險決策還需要 domain、使用者、production、法規與組織 context；資深工程師進入陌生領域也可能需要較多 review。"),
            ("Leader 如何知道自己成為瓶頸？", "大量工作等待其 review/approval、休假時停止、其他成員不敢決策、資訊只經由他傳遞，或同類問題反覆升級。"),
            ("AI 能否決定工程師績效？", "不應。它可整理可驗證事實，但評估涉及 context、偏差和高影響人事責任，需要透明政策與人類 judgment。"),
            ("Agent 的 delegation 與人的 delegation 最大差異？", "Agent 沒有組織責任、穩定長期記憶和價值判斷，因此權限需更機械化限制、完整 audit，且結果必須由人類 owner 承擔。"),
            ("領導成功最可持續的證據是什麼？", "團隊在 leader 不在線時仍能依共同方向做出好決策、知道何時升級、持續產生新 owners，且品質與健康沒有下降。"),
        ],
        ["swe-lead", "swe-scale-lead", "openai-codex", "nist-genai"],
    ),
    C(
        13,
        "Leading at Scale：從個人影響力到平台與制度",
        "當 leader 無法參與每個 project、review 和 incident 時，如何保持方向一致而不中央集權？",
        "進階",
        "以 mission、principles、interfaces、平台和領導網路放大判斷，並用 local feedback 防止制度失真。",
        ["scale", "ownership", "coupling", "goal-signal-metric"],
        """
小團隊 leader 可以靠直接溝通校正方向；規模增加後，任何需要 leader 親自出席的流程都會排隊。若只增加規則，組織變慢；若完全下放，團隊可能重複平台、採用不相容 contract，或在共同 production 上製造風險。Scale leadership 要把判斷轉成可重用環境，而不是複製個人指令。
""",
        """
二十個服務各自設計 deployment，導致 audit、rollback 和 on-call 工具不同。中央團隊若逐一審核會成為瓶頸；更好的做法是提供 paved road：安全預設、可觀測 rollout、self-service 和清楚的例外流程。
""",
        r"""
Mission / user outcomes
        ↓
few durable principles
        ↓
interfaces + paved road platform + policy-as-code
        ↓
distributed owners / tech leads / communities
        ↓
local decisions + fast feedback
        ↓
portfolio signals / incidents / user research
        └────────────→ improve principles & platform
""",
        """
Scale leadership 的第一層是 direction：少數持久原則和可量測結果，讓 local teams 能自行判斷。若 strategy 只是專案清單，任何新情況都要回中央詢問。第二層是 enablement：提供平台、templates、libraries 和 specialist consultation，把安全做法變成最容易的路。

第三層是 leadership network。Staff engineers、managers、SRE、security champions 和 communities of practice 分散 context 與 judgment。中央團隊維持跨組織 invariants；local owners 保有 use-case 知識和執行自治。例外不是失敗，而是重要 feedback：若大量團隊走 escape hatch，可能代表 paved road 不適合。

制度需要雙向 feedback。Portfolio metrics 看等待、stability 和採用；使用者研究了解平台 friction；incident 和 exception review 找未知需求。若中央只量 compliance，團隊會形式採用或建立 shadow systems。Scale 的目標是提高整體決策品質，不是讓每個服務外觀相同。
""",
        [
            "將 strategy 表達成使用者結果、constraints 和少數 durable principles。",
            "把高頻、安全的共同路徑做成 self-service paved road 和 policy-as-code。",
            "建立 distributed leaders 與 communities，讓 domain context 不必全回中央。",
            "為合法例外提供有期限、可觀測的 escape hatch，而非逼迫地下繞過。",
            "用 platform user research、queue time、incidents 和 exception patterns 更新制度。",
        ],
        "以下把平台採用看成產品 funnel，而非命令。若使用者在 setup 或 deploy 流失，應改善平台，而不只要求 compliance。",
        r"""
funnel = {
    "visited_docs": 1000,
    "created_service": 720,
    "first_deploy": 510,
    "slo_configured": 260,
    "oncall_ready": 180,
}

previous = None
for step, users in funnel.items():
    conversion = 1.0 if previous is None else users / previous
    print(step, f"{conversion:.1%}")
    previous = users
""",
        [
            "每一步 conversion 顯示平台使用者遇到的 friction，不直接責怪團隊。",
            "SLO 和 on-call 準備大幅流失，可能表示流程太晚、文件不足或責任不清。",
            "採用率必須與 reliability 和 developer experience 一起看，避免只追求數字。",
            "Qualitative interviews 能解釋 funnel，但應抽樣不同規模與成熟度團隊。",
        ],
        [
            "Paved road 若變成唯一道路，特殊 latency、法規或資料需求可能被錯誤壓平。",
            "大量中央政策增加 cognitive load，團隊可能只求通過而不理解風險。",
            "平台沒有產品管理和 SLO 時，會把所有下游效率綁在不可靠 dependency 上。",
            "只表揚跨組織 launch，不投資 maintenance，會留下無 owner 的廣泛系統。",
        ],
        """
AI 使個人與團隊能快速建立局部工具，因此 scale organization 更需要共用 agent platform、approved models、tool broker、policy 和 context sources。最佳做法不是中央 team 寫所有 prompts，而是提供身份、sandbox、eval、audit 和 reusable tools，讓 local owners 在 guardrails 內組合。Agent exception 和失敗資料也應回饋平台。
""",
        [
            "建立組織級 agent tool catalog，重用認證、audit 和結構化輸出。",
            "提供 repository scaffold、eval harness 和安全預設，降低每隊自建成本。",
            "用 AI 分析跨服務 incidents、exceptions 和重複元件，找平台機會。",
            "建立 domain-specific agents，由 local owner 維護知識，中央平台維護控制面。",
        ],
        [
            "模型和 tools 必須使用 workload identity，不共享長期個人憑證。",
            "平台提供最小權限、quota、cost attribution、kill switch 和 audit。",
            "Local domain owner 核准資料來源與 action policy，中央不得假設通用 context 足夠。",
            "採用率不是唯一成功指標；同時看 failure、rework、security 和 user experience。",
        ],
        """
Scale leader 的槓桿不是更多 mandate，而是讓好選擇具有最低 friction、壞選擇難以意外發生、真正例外能被看見。AI 平台尤其如此：若 approved path 太慢，團隊會把秘密貼進公共 chatbot；若只禁止不提供替代，治理只會失去 visibility。
""",
        [
            "選一項跨團隊政策，判斷能否改成安全預設、library 或 automated check。",
            "執行 funnel 範例，設計三個 qualitative 問題解釋最大流失。",
            "列出兩種 legitimate escape hatch，為它們設定 owner、expiry 和 review。",
            "畫出公司 AI platform control plane：identity、model、tool、data、eval、audit 和 kill switch。",
        ],
        [
            ("Scale leadership 為何不能只增加規則？", "規則需要理解、審核和更新，數量增加會提高等待與 cognitive load。應把高頻 invariants 轉成平台預設和自動 feedback。"),
            ("Paved road 的核心價值是什麼？", "讓安全、可維護、可觀測的共同做法成為最容易採用的路，同時降低每個團隊重建基礎設施的成本。"),
            ("Escape hatch 為何必要？", "真實 domain 有合法特殊 constraints；沒有透明例外路徑，團隊會建立不可見繞道，使中央更無法管理風險。"),
            ("平台 adoption funnel 能回答什麼？", "它顯示使用者在哪個步驟流失，提供 friction signal；仍需訪談理解原因，不能直接把流失視為團隊不合作。"),
            ("中央 AI 團隊與 local owner 如何分工？", "中央維護 identity、sandbox、models、tool broker、eval/audit 基礎；local owner 維護 domain data、workflow、風險和 action policy。"),
            ("為何 AI 禁令可能降低安全？", "若工作需求仍存在而沒有可用替代，成員會使用未批准工具，組織失去資料流與風險 visibility；治理要提供可行 paved road。"),
            ("成功的 scale system 有何特徵？", "Local decisions 快、共同 invariants 穩定、例外可見、平台有良好體驗與可靠性，且制度會依 feedback 持續更新。"),
        ],
        ["swe-scale-lead", "swe-compute", "dora-ai", "google-agentic-sre"],
    ),
    C(
        14,
        "Measuring Engineering Productivity without Gaming",
        "如何知道工程系統真的改善，而不是只讓 dashboard 數字變漂亮？",
        "進階",
        "從 goal、signal、metric 建立平衡量測，結合速度、品質、認知負荷與使用者結果。",
        ["goal-signal-metric", "goodhart", "feedback", "slo"],
        """
工程工作包含設計、排障、溝通、預防風險和刪除複雜度，不能用 lines of code、commit 或 ticket 數直接代表價值。任何單一 metric 成為績效目標後，都可能被拆分、延後或選擇性記錄。量測的目的應是回答可行動問題，而不是替個人排序製造虛假客觀性。
""",
        """
公司導入 coding assistant 後，accepted suggestions 上升 300%，但 PR 變大、review queue 增長、rollback 增加。若只看 adoption 會宣稱成功；若 goal 是更快且穩定地交付使用者價值，就必須同時看 lead time、rework、change failure 和 developer experience。
""",
        r"""
Question: 我們想改善什麼決策？
        ↓
Goal: 使用者價值 / 工程結果
        ↓
Signals: 哪些現象表示變好？
  ├─ speed / flow
  ├─ quality / stability
  ├─ satisfaction / cognitive load
  ├─ collaboration / learning
  └─ cost / sustainability
        ↓
Metrics + qualitative evidence
        ↓
segment / triangulate / inspect gaming
        ↓
action → observe unintended effects
""",
        """
先寫問題和 actionability。例如「CI 是否阻礙小批次整合，若是要投資哪個 bottleneck？」比「工程師生產力是多少？」更可回答。Goal 描述希望達成的結果；signal 是可觀察現象；metric 才是資料計算。反過來先挑現成欄位，容易把工具可量測的東西誤認為重要。

量測應 triangulate。Repository data 看 flow，incident data 看外溢風險，survey 看 cognitive load，訪談解釋原因。每種資料都有 bias：ticket 不記錄非正式協助，survey 有回應偏差，lead time 可能因 batch definition 不同失真。指標要分群看 distribution，不只平均。

避免用 team-system metrics 排個人。個人 LOC、review comments 或 AI acceptance 會鼓勵競爭與 gaming，傷害共享工作。使用 metrics 應先公開定義、用途、保留和限制，與被量測者共同解讀。每次改善也要看 counter-metrics，防止局部優化。
""",
        [
            "從一個具體決策問題開始，確認量測結果會導致什麼 action。",
            "使用 GSM 定義 goal、至少三個 signals，再選能代表它們的 metrics。",
            "同時量 flow、quality、human experience 和 user outcome，避免單軸優化。",
            "查看 p50/p90、cohort 和 trend，搭配 survey、訪談與抽樣案例。",
            "預先寫出 gaming 和 unintended effects，設定 counter-metrics 與停止條件。",
        ],
        "範例建立平衡 scorecard，但不把不同單位硬加成個人分數。程式只標記需要共同調查的 tension。",
        r"""
team = {
    "lead_time_hours": 8,
    "change_failure_rate": 0.18,
    "review_wait_hours": 11,
    "developer_satisfaction": 3.1,  # 1..5
}

def tensions(m: dict) -> list[str]:
    findings = []
    if m["lead_time_hours"] < 12 and m["change_failure_rate"] > 0.15:
        findings.append("speed improved, stability needs investigation")
    if m["review_wait_hours"] > m["lead_time_hours"] / 2:
        findings.append("review queue dominates lead time")
    if m["developer_satisfaction"] < 3.5:
        findings.append("quantitative gains may hide cognitive load")
    return findings

print(tensions(team))
""",
        [
            "函式尋找 metrics 間的 tension，而不是算出『生產力 78 分』。",
            "Threshold 應依服務與歷史 baseline 設定，範例數字不是跨公司的標準。",
            "Finding 是調查起點，需要看 sample PR、incident 和訪談。",
            "Team-level 系統 metric 用於改善環境，不應直接分配個人績效。",
        ],
        [
            "單一 composite score 隱藏 trade-off，且權重難以公開辯護。",
            "Metric definition 改變或工具遷移會製造假趨勢，需要版本與註記。",
            "只看平均會隱藏少數超長 review、特定時區或新人的困難。",
            "觀測本身改變行為；成員若不信任用途，資料品質和心理安全都會下降。",
        ],
        """
AI 時代最容易被濫用的 metrics 是生成行數、suggestion acceptance、prompt 數和 agent 完成任務數。它們量 adoption 或 activity，不等於使用者價值。DORA 類型的實務更重視 AI 是否縮短 feedback、改善 flow，同時維持 stability、quality 和 developer experience；也要量 review/rework 是否被下游吸收。
""",
        [
            "比較使用 AI 前後的 lead time、review wait、rework、change failure 和 satisfaction。",
            "用 agent 分析 qualitative survey 主題，但保留匿名、樣本量和原文抽查。",
            "量 agent task 的一次通過率、人工接管率、tool failure 和 policy violation。",
            "以 experiment 或 phased rollout 比較相似團隊，避免把同時期變化都歸因 AI。",
        ],
        [
            "禁止以 AI usage 或 acceptance rate 直接評估個人績效。",
            "公開 telemetry 收集範圍、用途、retention 和誰能查看，允許合理 opt-out。",
            "AI 產生的 metric 解釋必須可追到 query、definition 和原始 aggregate。",
            "任何速度改善都配對 stability、security、review load 和使用者 outcome counter-metrics。",
        ],
        """
Domain expert 會把 metrics 當對話和實驗工具，而不是真理。最有價值的結果常是發現原本假設錯了，例如 CI 不是 bottleneck，需求反覆才是。若 dashboard 不能改變資源、流程或產品決策，就不值得長期收集；量測本身也有隱私、維護和信任成本。
""",
        [
            "選一個工程問題，寫 Goal、三個 Signals、每個 Signal 一個 Metric。",
            "執行範例，新增 deploy frequency，觀察它是否提供新資訊或只是 activity。",
            "為 metrics 寫 data contract：definition、source、owner、retention、known bias。",
            "設計 AI pilot scorecard，必須同時包含 flow、quality、human 和 user 四類 evidence。",
        ],
        [
            ("為什麼 LOC 不適合衡量個人生產力？", "價值可能來自刪除 code、設計、review、協助與預防事故；以 LOC 作目標會鼓勵膨脹和避免共享工作，且不同問題不可比較。"),
            ("Goal、Signal、Metric 的順序有何價值？", "先定義結果和可觀察現象，再選數字，能降低因工具容易取得某資料就錯把它當目標的風險。"),
            ("Triangulation 是什麼？", "用多種有不同偏差的證據交叉，例如 repository flow、incidents、survey 和訪談；一致時信心增加，衝突時提供新的調查線索。"),
            ("Counter-metric 有什麼作用？", "監控改善某目標是否傷害另一目標，例如 deployment 變快時同看 change failure、review load 和 burnout。"),
            ("AI suggestion acceptance 能回答什麼？", "主要回答工具功能被採用多少，不能單獨證明工作更快、品質更好或使用者獲益；還需 outcome evidence。"),
            ("為什麼不建議把所有 metrics 合成一分？", "Composite score 隱藏不同單位、取捨與 uncertainty，容易被 gaming；保留多維 tension 更有助於找出系統 bottleneck。"),
            ("何時應停止收集 metric？", "當它沒有可行動 decision、成本或隱私風險超過收益、定義不再可信，或更直接 evidence 已可取得時。"),
        ],
        ["swe-productivity", "swe-preface", "dora-ai", "openai-evals"],
    ),
]
