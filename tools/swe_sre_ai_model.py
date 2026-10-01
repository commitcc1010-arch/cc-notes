"""Shared model, glossary, and source registry for the SWE × SRE × AI book."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Term:
    title: str
    meaning: str
    example: str
    relevance: str


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    question: str
    level: str
    promise: str
    terms: tuple[str, ...]
    why: str
    use_case: str
    blueprint: str
    mental_model: str
    mechanics: tuple[str, ...]
    example_intro: str
    code: str
    code_lang: str
    walkthrough: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    ai_shift: str
    ai_practices: tuple[str, ...]
    ai_guardrails: tuple[str, ...]
    expert_view: str
    lab: tuple[str, ...]
    qa: tuple[tuple[str, str], ...]
    sources: tuple[str, ...]


def C(
    number: int,
    title: str,
    question: str,
    level: str,
    promise: str,
    terms: Iterable[str],
    why: str,
    use_case: str,
    blueprint: str,
    mental_model: str,
    mechanics: Iterable[str],
    example_intro: str,
    code: str,
    walkthrough: Iterable[str],
    tradeoffs: Iterable[str],
    ai_shift: str,
    ai_practices: Iterable[str],
    ai_guardrails: Iterable[str],
    expert_view: str,
    lab: Iterable[str],
    qa: Iterable[tuple[str, str]],
    sources: Iterable[str],
    code_lang: str = "python",
) -> Chapter:
    chapter = Chapter(
        number=number,
        title=title,
        question=question,
        level=level,
        promise=promise,
        terms=tuple(terms),
        why=why.strip(),
        use_case=use_case.strip(),
        blueprint=blueprint.strip(),
        mental_model=mental_model.strip(),
        mechanics=tuple(mechanics),
        example_intro=example_intro.strip(),
        code=code.strip(),
        code_lang=code_lang,
        walkthrough=tuple(walkthrough),
        tradeoffs=tuple(tradeoffs),
        ai_shift=ai_shift.strip(),
        ai_practices=tuple(ai_practices),
        ai_guardrails=tuple(ai_guardrails),
        expert_view=expert_view.strip(),
        lab=tuple(lab),
        qa=tuple(qa),
        sources=tuple(sources),
    )
    validate_chapter(chapter)
    return chapter


def validate_chapter(chapter: Chapter) -> None:
    assert len(chapter.terms) >= 4, f"chapter {chapter.number}: need 4 terms"
    assert len(chapter.mechanics) >= 4, f"chapter {chapter.number}: need 4 mechanics"
    assert len(chapter.walkthrough) >= 4, f"chapter {chapter.number}: need 4 walkthrough steps"
    assert len(chapter.tradeoffs) >= 3, f"chapter {chapter.number}: need 3 tradeoffs"
    assert len(chapter.ai_practices) >= 4, f"chapter {chapter.number}: need 4 AI practices"
    assert len(chapter.ai_guardrails) >= 4, f"chapter {chapter.number}: need 4 guardrails"
    assert len(chapter.lab) >= 4, f"chapter {chapter.number}: need 4 lab steps"
    assert len(chapter.qa) >= 7, f"chapter {chapter.number}: need 7 Q&A"
    assert len(chapter.sources) >= 2, f"chapter {chapter.number}: need 2 sources"
    assert len(chapter.mental_model) >= 240, f"chapter {chapter.number}: mental model too short"
    assert len(chapter.ai_shift) >= 120, f"chapter {chapter.number}: AI discussion too short"
    assert len(chapter.expert_view) >= 100, f"chapter {chapter.number}: expert view too short"


PARTS = [
    {
        "part": 0,
        "slug": "Start Here",
        "title": "先建立全局模型",
        "range": (1, 2),
        "intro": "先看完整生命週期與共同語言。後面不是 46 個孤立主題，而是逐步放大同一條從需求到事故學習的 feedback loop。",
    },
    {
        "part": 1,
        "slug": "Engineering Over Time",
        "title": "Software Engineering 的根基",
        "range": (3, 7),
        "intro": "把程式放進時間、規模與成本中思考，理解為何今天能跑不等於多年後仍可安全改動。",
    },
    {
        "part": 2,
        "slug": "Culture and Leadership",
        "title": "團隊、文化與領導",
        "range": (8, 14),
        "intro": "軟體是社會技術系統。知識流動、決策權、心理安全與衡量方式，會直接改變 codebase 和 production 的品質。",
    },
    {
        "part": 3,
        "slug": "Sustainable Change",
        "title": "讓變更可以長期維持",
        "range": (15, 21),
        "intro": "把 style、review、documentation、version control、dependencies 與大型遷移組成可重複的變更系統。",
    },
    {
        "part": 4,
        "slug": "Testing Build Delivery",
        "title": "Testing、Build 與 Delivery",
        "range": (22, 29),
        "intro": "將需求轉成可執行證據，從單元測試一路走到可重現 build、CI、canary 與 rollback。",
    },
    {
        "part": 5,
        "slug": "Reliability Foundations",
        "title": "SRE 與可靠性模型",
        "range": (30, 36),
        "intro": "把可靠性從感覺改成可量測的產品決策，以 SLO、error budget、observability、alerting 與 capacity 管理 production。",
    },
    {
        "part": 6,
        "slug": "Distributed Reliability",
        "title": "Distributed Systems Reliability",
        "range": (37, 42),
        "intro": "流量、等待、失敗與資料跨越多台機器後，局部合理行為可能組合成全域災難。本 Part 專門建立故障模型。",
    },
    {
        "part": 7,
        "slug": "Incident Operations",
        "title": "Incident、On-call 與學習",
        "range": (43, 46),
        "intro": "當模型失效時，如何降低傷害、恢復服務、保護人員，並把事故轉成新的工程資產。",
    },
    {
        "part": 8,
        "slug": "Operating Model",
        "title": "組織落地與 Capstone",
        "range": (47, 48),
        "intro": "將前面所有概念組成能在 startup、中型公司與大型組織逐步採用的 engineering operating system。",
    },
]


SOURCES = {
    "swe-preface": (
        "Software Engineering at Google — Preface",
        "https://abseil.io/resources/swe-book/html/pr01.html",
    ),
    "swe-teams": (
        "Software Engineering at Google — How to Work Well on Teams",
        "https://abseil.io/resources/swe-book/html/ch02.html",
    ),
    "swe-knowledge": (
        "Software Engineering at Google — Knowledge Sharing",
        "https://abseil.io/resources/swe-book/html/ch03.html",
    ),
    "swe-equity": (
        "Software Engineering at Google — Engineering for Equity",
        "https://abseil.io/resources/swe-book/html/ch04.html",
    ),
    "swe-lead": (
        "Software Engineering at Google — How to Lead a Team",
        "https://abseil.io/resources/swe-book/html/ch05.html",
    ),
    "swe-scale-lead": (
        "Software Engineering at Google — Leading at Scale",
        "https://abseil.io/resources/swe-book/html/ch06.html",
    ),
    "swe-productivity": (
        "Software Engineering at Google — Measuring Engineering Productivity",
        "https://abseil.io/resources/swe-book/html/ch07.html",
    ),
    "swe-style": (
        "Software Engineering at Google — Style Guides and Rules",
        "https://abseil.io/resources/swe-book/html/ch08.html",
    ),
    "swe-review": (
        "Software Engineering at Google — Code Review",
        "https://abseil.io/resources/swe-book/html/ch09.html",
    ),
    "swe-docs": (
        "Software Engineering at Google — Documentation",
        "https://abseil.io/resources/swe-book/html/ch10.html",
    ),
    "swe-testing": (
        "Software Engineering at Google — Testing Overview",
        "https://abseil.io/resources/swe-book/html/ch11.html",
    ),
    "swe-unit": (
        "Software Engineering at Google — Unit Testing",
        "https://abseil.io/resources/swe-book/html/ch12.html",
    ),
    "swe-doubles": (
        "Software Engineering at Google — Test Doubles",
        "https://abseil.io/resources/swe-book/html/ch13.html",
    ),
    "swe-larger-tests": (
        "Software Engineering at Google — Larger Testing",
        "https://abseil.io/resources/swe-book/html/ch14.html",
    ),
    "swe-deprecation": (
        "Software Engineering at Google — Deprecation",
        "https://abseil.io/resources/swe-book/html/ch15.html",
    ),
    "swe-vcs": (
        "Software Engineering at Google — Version Control and Branch Management",
        "https://abseil.io/resources/swe-book/html/ch16.html",
    ),
    "swe-search": (
        "Software Engineering at Google — Code Search",
        "https://abseil.io/resources/swe-book/html/ch17.html",
    ),
    "swe-build": (
        "Software Engineering at Google — Build Systems and Build Philosophy",
        "https://abseil.io/resources/swe-book/html/ch18.html",
    ),
    "swe-static": (
        "Software Engineering at Google — Static Analysis",
        "https://abseil.io/resources/swe-book/html/ch20.html",
    ),
    "swe-deps": (
        "Software Engineering at Google — Dependency Management",
        "https://abseil.io/resources/swe-book/html/ch21.html",
    ),
    "swe-large-change": (
        "Software Engineering at Google — Large-Scale Changes",
        "https://abseil.io/resources/swe-book/html/ch22.html",
    ),
    "swe-ci": (
        "Software Engineering at Google — Continuous Integration",
        "https://abseil.io/resources/swe-book/html/ch23.html",
    ),
    "swe-cd": (
        "Software Engineering at Google — Continuous Delivery",
        "https://abseil.io/resources/swe-book/html/ch24.html",
    ),
    "swe-compute": (
        "Software Engineering at Google — Compute as a Service",
        "https://abseil.io/resources/swe-book/html/ch25.html",
    ),
    "sre-intro": (
        "Site Reliability Engineering — Introduction",
        "https://sre.google/sre-book/introduction/",
    ),
    "sre-risk": (
        "Site Reliability Engineering — Embracing Risk",
        "https://sre.google/sre-book/embracing-risk/",
    ),
    "sre-slo": (
        "Site Reliability Engineering — Service Level Objectives",
        "https://sre.google/sre-book/service-level-objectives/",
    ),
    "sre-toil": (
        "Site Reliability Engineering — Eliminating Toil",
        "https://sre.google/sre-book/eliminating-toil/",
    ),
    "sre-monitoring": (
        "Site Reliability Engineering — Monitoring Distributed Systems",
        "https://sre.google/sre-book/monitoring-distributed-systems/",
    ),
    "sre-automation": (
        "Site Reliability Engineering — The Evolution of Automation at Google",
        "https://sre.google/sre-book/automation-at-google/",
    ),
    "sre-release": (
        "Site Reliability Engineering — Release Engineering",
        "https://sre.google/sre-book/release-engineering/",
    ),
    "sre-simplicity": (
        "Site Reliability Engineering — Simplicity",
        "https://sre.google/sre-book/simplicity/",
    ),
    "sre-alerting": (
        "Site Reliability Engineering — Practical Alerting",
        "https://sre.google/sre-book/practical-alerting/",
    ),
    "sre-oncall": (
        "Site Reliability Engineering — Being On-Call",
        "https://sre.google/sre-book/being-on-call/",
    ),
    "sre-troubleshooting": (
        "Site Reliability Engineering — Effective Troubleshooting",
        "https://sre.google/sre-book/effective-troubleshooting/",
    ),
    "sre-emergency": (
        "Site Reliability Engineering — Emergency Response",
        "https://sre.google/sre-book/emergency-response/",
    ),
    "sre-incident": (
        "Site Reliability Engineering — Managing Incidents",
        "https://sre.google/sre-book/managing-incidents/",
    ),
    "sre-postmortem": (
        "Site Reliability Engineering — Postmortem Culture",
        "https://sre.google/sre-book/postmortem-culture/",
    ),
    "sre-outages": (
        "Site Reliability Engineering — Tracking Outages",
        "https://sre.google/sre-book/tracking-outages/",
    ),
    "sre-reliability-testing": (
        "Site Reliability Engineering — Testing for Reliability",
        "https://sre.google/sre-book/testing-reliability/",
    ),
    "sre-load-balancing": (
        "Site Reliability Engineering — Load Balancing",
        "https://sre.google/sre-book/load-balancing-frontend/",
    ),
    "sre-overload": (
        "Site Reliability Engineering — Handling Overload",
        "https://sre.google/sre-book/handling-overload/",
    ),
    "sre-cascading": (
        "Site Reliability Engineering — Addressing Cascading Failures",
        "https://sre.google/sre-book/addressing-cascading-failures/",
    ),
    "sre-consensus": (
        "Site Reliability Engineering — Distributed Consensus",
        "https://sre.google/sre-book/managing-critical-state/",
    ),
    "sre-cron": (
        "Site Reliability Engineering — Distributed Periodic Scheduling",
        "https://sre.google/sre-book/distributed-periodic-scheduling/",
    ),
    "sre-data": (
        "Site Reliability Engineering — Data Processing Pipelines",
        "https://sre.google/sre-book/data-processing-pipelines/",
    ),
    "sre-integrity": (
        "Site Reliability Engineering — Data Integrity",
        "https://sre.google/sre-book/data-integrity/",
    ),
    "sre-launch": (
        "Site Reliability Engineering — Reliable Product Launches",
        "https://sre.google/sre-book/reliable-product-launches/",
    ),
    "sre-engagement": (
        "Site Reliability Engineering — Evolving the SRE Engagement Model",
        "https://sre.google/sre-book/evolving-sre-engagement-model/",
    ),
    "sre-onboarding": (
        "Site Reliability Engineering — Accelerating SREs to On-Call and Beyond",
        "https://sre.google/sre-book/accelerating-sre-on-call/",
    ),
    "sre-interrupts": (
        "Site Reliability Engineering — Dealing with Interrupts",
        "https://sre.google/sre-book/dealing-with-interrupts/",
    ),
    "sre-operational-overload": (
        "Site Reliability Engineering — Recovering from Operational Overload",
        "https://sre.google/sre-book/operational-overload/",
    ),
    "sre-collaboration": (
        "Site Reliability Engineering — Communication and Collaboration",
        "https://sre.google/sre-book/communication-and-collaboration/",
    ),
    "dora-ai": (
        "DORA 2025 — AI Capabilities Model",
        "https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model",
    ),
    "openai-codex": (
        "OpenAI — Codex Best Practices",
        "https://developers.openai.com/codex/learn/best-practices/",
    ),
    "openai-evals": (
        "OpenAI — Agent Evals",
        "https://developers.openai.com/api/docs/guides/agent-evals",
    ),
    "anthropic-code": (
        "Anthropic — Claude Code Best Practices",
        "https://docs.anthropic.com/en/docs/claude-code/best-practices",
    ),
    "github-review": (
        "GitHub — Review AI-generated code",
        "https://docs.github.com/copilot/tutorials/review-ai-generated-code",
    ),
    "google-agentic-sre": (
        "Google Cloud — How Google SRE is using agentic AI",
        "https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/",
    ),
    "google-agent-observability": (
        "Google Cloud — Agent observability",
        "https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability",
    ),
    "owasp-llm": (
        "OWASP — Top 10 for LLM Applications 2025",
        "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
    ),
    "nist-genai": (
        "NIST — Generative AI Profile",
        "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
    ),
    "microsoft-ai-incident": (
        "Microsoft — Incident response for AI systems",
        "https://learn.microsoft.com/en-us/security/zero-trust/sfi/incident-response-ai-systems",
    ),
}


TERMS = {
    "software": Term(
        "Software（軟體）",
        "可被電腦執行的指令、資料與設定；真正的產品還包括部署方式、依賴、監控和操作流程。",
        "一個 Python 檔可以運算價格，但沒有資料庫 migration、部署與告警時，還不是可長期營運的服務。",
        "本書把 code 放回完整生命週期，避免把『寫完函式』誤認為『工程完成』。",
    ),
    "service": Term(
        "Service（服務）",
        "長時間運行、透過網路或訊息介面替其他人或系統提供能力的軟體。",
        "付款 API 接收 request，驗證、寫入資料庫，再回傳成功或失敗。",
        "SRE 的可靠性目標通常以服務向使用者提供的行為為單位。",
    ),
    "production": Term(
        "Production",
        "真實使用者、真實資料與真實商業影響所在的執行環境。",
        "測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。",
        "Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。",
    ),
    "lifecycle": Term(
        "Lifecycle（生命週期）",
        "一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。",
        "新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。",
        "SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。",
    ),
    "feedback": Term(
        "Feedback loop（回饋迴路）",
        "採取行動後取得結果，依結果修正下一次行動的閉環。",
        "CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。",
        "優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。",
    ),
    "agent": Term(
        "AI Agent",
        "能接收目標、規劃步驟、呼叫工具、觀察結果並迭代的模型系統。",
        "Coding agent 搜尋 repository、修改檔案、跑測試，再依失敗訊息修正。",
        "Agent 增加速度與自治，也帶來 excessive agency、秘密外洩與不可預測操作等新風險。",
    ),
    "context": Term(
        "Context engineering",
        "設計模型在做決策時能看見哪些規格、程式碼、文件、工具結果與限制。",
        "只說『修 bug』通常不足；提供重現步驟、相關 module、測試命令和完成條件更可靠。",
        "AI 時代的文件、repository 結構與工具輸出同時服務人類與 agent。",
    ),
    "eval": Term(
        "Eval（評估）",
        "以可重複資料和評分規則，量測 AI 系統是否完成目標、遵守限制並安全失敗。",
        "除了答案正確率，也檢查 agent 是否用了禁止的工具、是否引用正確來源。",
        "Eval 是 AI 版本的 executable specification；沒有 eval 就無法知道模型或 prompt 更新是否退步。",
    ),
    "constraint": Term(
        "Constraint（限制條件）",
        "解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。",
        "登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。",
        "工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。",
    ),
    "invariant": Term(
        "Invariant（不變條件）",
        "系統任何合法狀態都必須成立的規則。",
        "銀行轉帳前後，所有帳戶餘額總和不應憑空增加。",
        "測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。",
    ),
    "api": Term(
        "API Contract",
        "元件對外承諾的輸入、輸出、錯誤、狀態與相容性規則。",
        "`get_user(id)` 找不到資料時回 `None` 還是拋 exception，都是 contract。",
        "清楚 contract 讓團隊與 agent 能在不理解所有內部細節時安全組合元件。",
    ),
    "compatibility": Term(
        "Backward compatibility",
        "新版本仍能服務舊呼叫者、舊資料或舊協定的能力。",
        "新增 optional JSON field 通常相容；把字串改為物件可能使舊 client 崩潰。",
        "大型系統無法原子更新所有使用者，因而需要 migration window。",
    ),
    "scale": Term(
        "Scale（規模）",
        "程式碼量、資料量、請求量、團隊數或系統存活時間增加後出現的新約束。",
        "十人可口頭協調；一千人需要可搜尋文件、標準化 review 與自動 policy。",
        "Scale 不是單純把數字放大，常會改變最適合的架構與流程。",
    ),
    "coupling": Term(
        "Coupling（耦合）",
        "一個元件改變時，另一個元件也必須跟著改變的程度。",
        "前端直接依賴資料庫欄位名稱，使 schema rename 同時破壞 UI。",
        "Sustainable design 會讓必要耦合顯式化，並降低偶然耦合。",
    ),
    "tradeoff": Term(
        "Trade-off（取捨）",
        "改善某個目標通常會增加另一種成本，工程決策需比較整體結果。",
        "更多測試提高信心，但也增加執行時間和維護成本。",
        "本書不提供永遠正確的工具選擇，而是提供判斷何時值得的模型。",
    ),
    "adr": Term(
        "ADR（Architecture Decision Record）",
        "短篇記錄決策背景、選項、選擇、代價與未來重訪條件的文件。",
        "記錄為何選 queue 而非同步 RPC，以及流量降到何種程度時可簡化。",
        "ADR 保存『為什麼』，避免人或 AI 只看現況後重複已否決的方案。",
    ),
    "ownership": Term(
        "Ownership",
        "對元件品質、決策、值班與改善負最終責任的明確主體。",
        "平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。",
        "AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。",
    ),
    "psychological-safety": Term(
        "Psychological safety",
        "成員能提出疑問、承認錯誤和挑戰決策，而不必害怕羞辱或不合理懲罰。",
        "新人可以說『我不懂這個 deploy』，團隊因此在事故前發現 runbook 缺口。",
        "安全文化能更早暴露弱信號，是可靠性控制的一部分。",
    ),
    "bus-factor": Term(
        "Bus factor",
        "需要多少關鍵成員同時離開，知識缺口才會讓專案無法維持。",
        "只有一人知道憑證輪替流程，休假時到期便造成 outage。",
        "文件、輪調、pairing 與自動化可以提高 bus factor。",
    ),
    "equity": Term(
        "Equity（公平可及）",
        "依不同使用者與成員的處境提供必要支持，而非假設所有人有相同能力與資源。",
        "CLI 只靠顏色表示錯誤會排除色覺差異使用者；公平設計會同時提供文字和符號。",
        "AI 資料與模型可能延續偏差，需在需求、測試和監控中顯式處理。",
    ),
    "goal-signal-metric": Term(
        "Goal–Signal–Metric",
        "先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。",
        "Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。",
        "這個順序可降低為了容易量測而優化錯誤目標的風險。",
    ),
    "goodhart": Term(
        "Goodhart’s Law",
        "當代理量成為硬目標，人會優化數字而不是原始目的，使指標失去資訊。",
        "以 commit 數評績效，工程師便拆出大量沒有價值的小 commit。",
        "AI 採用率、接受行數與 token 數同樣不適合作為個人績效目標。",
    ),
    "style": Term(
        "Style rule",
        "為一致性、可讀性或避免缺陷而制定的程式碼規則。",
        "Python formatter 統一引號與縮排，review 不必反覆爭論格式。",
        "可機械判斷的規則應由工具執行，人類 review 專注語意。",
    ),
    "review": Term(
        "Code review",
        "變更進入主線前，由另一個視角檢查正確性、設計、測試、可理解性與風險。",
        "Reviewer 發現 retry 沒有 deadline，避免 production thread 永久耗盡。",
        "Review 同時是品質閘門、知識分享與 ownership 轉移。",
    ),
    "design-doc": Term(
        "Design document",
        "在昂貴實作前對齊問題、需求、架構、資料流、失敗模式與 rollout 的文件。",
        "支付服務改資料模型前，先描述雙寫、回填、驗證與 rollback。",
        "AI 可以協助檢查缺項，但設計責任與風險接受仍由人承擔。",
    ),
    "deprecation": Term(
        "Deprecation",
        "宣布某介面將停止支援，提供替代方案、遷移期與最終移除程序。",
        "舊 API 先發 warning、量測剩餘流量、提供 adapter，最後才刪除。",
        "Deprecation 是協調問題，不只是搜尋後直接 rename。",
    ),
    "version-control": Term(
        "Version control",
        "保存變更歷史、身份、分支與可還原狀態的系統。",
        "Git commit 讓團隊看見誰在何時為何改動，並可 revert 壞版本。",
        "Coding agent 必須在可審查 branch/worktree 中工作，不能偷偷修改未知狀態。",
    ),
    "dependency": Term(
        "Dependency",
        "程式運作所依賴的 library、service、tool、資料格式或團隊。",
        "Web service 依賴資料庫 driver 和外部付款 API。",
        "Dependency 帶來升級、供應鏈、安全與可用性成本；AI 可能捏造不存在的套件。",
    ),
    "static-analysis": Term(
        "Static analysis",
        "不實際執行完整程式，就分析程式結構、型別、資料流或規則。",
        "Type checker 在 CI 發現函式可能回傳 `None` 卻被當整數使用。",
        "它為人與 agent 提供快速、確定性、可自動化的 feedback。",
    ),
    "codemod": Term(
        "Codemod",
        "依語法結構批次修改程式碼的自動轉換。",
        "將所有 `old_api(x)` 轉為 `new_api(value=x)`，並保留格式與註解。",
        "大型遷移可由 AI 找策略，再由 AST codemod 可靠執行。",
    ),
    "test-oracle": Term(
        "Test oracle",
        "判斷某次執行結果是否正確的規則或已知答案。",
        "排序後必須單調且包含相同元素，比只比對一個範例更完整。",
        "Agent 只有在 oracle 明確時才能自主迭代，否則可能把錯誤輸出合理化。",
    ),
    "test-size": Term(
        "Test size 與 scope",
        "Size 描述測試能使用的資源與速度；scope 描述跨越多少元件，兩者不是同一件事。",
        "單一函式測試通常 small scope；但若連真資料庫，資源上可能是 medium。",
        "分開思考可建立更平衡、可預測的測試組合。",
    ),
    "unit-test": Term(
        "Unit test",
        "針對小範圍行為、快速且隔離的測試。",
        "輸入購物車項目，驗證折扣規則和邊界值。",
        "好 unit test 保護公開行為，不綁死私有方法的實作順序。",
    ),
    "test-double": Term(
        "Test double",
        "測試中替代真實依賴的物件，包括 fake、stub、mock 等不同角色。",
        "Fake clock 讓測試控制時間，不必真的等待一小時。",
        "錯誤使用 mock 會只驗證自己設定的劇本，與真實依賴 contract 脫節。",
    ),
    "hermetic": Term(
        "Hermetic test/build",
        "結果只由明確宣告的輸入決定，不受網路、目前時間、機器或外部狀態影響。",
        "測試使用固定 timezone、fake clock 和本地 fixture。",
        "Hermeticity 讓 CI 與 agent 能重現失敗，也是可靠 cache 的前提。",
    ),
    "flaky": Term(
        "Flaky test",
        "程式未改變，但測試有時通過、有時失敗。",
        "依賴真實時間的測試剛好跨過午夜便失敗。",
        "Flakiness 會消耗信任；AI 若以重跑掩蓋它，只會讓問題更晚爆發。",
    ),
    "build": Term(
        "Build",
        "把 source、dependencies 與設定轉成可部署 artifact 的可重複流程。",
        "將 Python application 和鎖定套件打成帶 digest 的 container image。",
        "Build graph 和 provenance 讓團隊知道 production 到底執行哪組輸入。",
    ),
    "ci": Term(
        "Continuous Integration",
        "頻繁整合小變更，並以自動 build、test 和 analysis 快速回饋。",
        "Pull request 在 merge 前執行 lint、unit、contract 和 security checks。",
        "CI 是變更進入共享主線前的早期告警系統。",
    ),
    "cd": Term(
        "Continuous Delivery",
        "讓每個通過驗證的版本都處於可安全發布狀態；是否自動進 production 可另行決定。",
        "Artifact 通過 staging 後，以同一 digest 做 canary，再逐步擴大。",
        "CD 重點是可靠、可重複和可回退，不是單純部署更頻繁。",
    ),
    "canary": Term(
        "Canary release",
        "先把新版本暴露給少量流量，觀察結果後才擴大。",
        "先讓 1% request 使用新 checkout，再比較錯誤率和 latency。",
        "Canary 限制 blast radius；前提是有代表流量、健康指標與快速 rollback。",
    ),
    "sre": Term(
        "Site Reliability Engineering",
        "以軟體工程方法設計與營運可靠 production 系統的職能與實務。",
        "SRE 不只手動重啟服務，而會修 automation、capacity model、alert 和架構。",
        "核心是讓操作經驗轉成可重複的工程機制。",
    ),
    "toil": Term(
        "Toil",
        "手動、重複、可自動化、戰術性且隨服務成長線性增加的營運工作。",
        "每天複製 log、手算容量，再逐台修改設定。",
        "消除 toil 不是刪除所有操作，而是保留時間做能長期降低操作量的工程。",
    ),
    "sli": Term(
        "SLI（Service Level Indicator）",
        "以使用者視角量測服務品質的指標。",
        "成功 checkout 數除以所有有效 checkout 數。",
        "SLI 是觀測事實；選錯 measurement point 會得到漂亮卻無用的數字。",
    ),
    "slo": Term(
        "SLO（Service Level Objective）",
        "某段時間內希望 SLI 達到的明確目標。",
        "28 天內 99.9% 有效 API request 成功。",
        "SLO 讓可靠性、告警和發布決策共享同一尺度。",
    ),
    "sla": Term(
        "SLA（Service Level Agreement）",
        "服務提供者與客戶之間含後果或補償的正式承諾。",
        "月可用性低於 99.9% 時提供 service credit。",
        "內部 SLO 通常應比外部 SLA 更嚴格，留下反應空間。",
    ),
    "error-budget": Term(
        "Error budget",
        "SLO 允許的不可靠量；100% 減去目標就是可消耗比例。",
        "99.9% 月 SLO 約允許 0.1% valid events 失敗。",
        "它把『穩定或快速』的爭論轉成可觀察的共同政策。",
    ),
    "observability": Term(
        "Observability",
        "能否從系統輸出推斷內部狀態、因果與失敗位置的能力。",
        "Trace 顯示 request 在付款 dependency 耗掉 1.8 秒，而非只知道整體慢。",
        "Logs、metrics、traces、profiles 與變更事件需以共同 identifiers 串接。",
    ),
    "alert": Term(
        "Actionable alert",
        "代表使用者影響或迫近風險，而且值班者能採取具體行動的通知。",
        "快速消耗 error budget 且 runbook 有 rollback 步驟時 page on-call。",
        "每個異常都 page 會造成 alert fatigue，使真正事故被忽略。",
    ),
    "burn-rate": Term(
        "Burn rate",
        "error budget 被消耗的速度相對於剛好用完整個觀察窗口的速度。",
        "Burn rate 14 表示目前失敗率若持續，預算會比計畫快 14 倍耗盡。",
        "多窗口 burn-rate alert 同時兼顧快速事故與持續慢性問題。",
    ),
    "capacity": Term(
        "Capacity",
        "系統在指定品質下能承受的工作量與資源上限。",
        "服務在 p99 低於 300ms 時，每台最多穩定處理 800 RPS。",
        "Capacity planning 必須考慮成長、尖峰、故障冗餘和補資源所需 lead time。",
    ),
    "load-balancing": Term(
        "Load balancing",
        "依健康、容量和策略把工作分配到多個處理者。",
        "Least-loaded 將新 request 送給目前並發較少的 backend。",
        "平均分配不等於公平；慢 request、cache locality 和異質容量都會影響結果。",
    ),
    "backpressure": Term(
        "Backpressure",
        "下游無法再安全接收工作時，向上游傳回減速或拒絕信號。",
        "Queue 滿時 API 回 429，而不是無限接受並耗盡記憶體。",
        "沒有 backpressure，局部過載會透過等待與 retry 擴散。",
    ),
    "load-shedding": Term(
        "Load shedding",
        "過載時主動拒絕低優先或超過容量的工作，以保護仍可完成的請求。",
        "先拒絕報表刷新，保留付款流量。",
        "拒絕必須早、便宜且可觀測；在昂貴工作做完後才拒絕沒有保護效果。",
    ),
    "deadline": Term(
        "Deadline 與 timeout",
        "Deadline 是整個操作最晚完成時間；timeout 常是單一步驟最多等待多久。",
        "使用者剩 800ms，下一層不能各自重設 2 秒 timeout。",
        "跨服務傳遞剩餘 deadline 可避免每層等待疊加。",
    ),
    "retry": Term(
        "Retry",
        "操作失敗後再次嘗試，適合暫時性且可安全重做的錯誤。",
        "遇到短暫 connection reset，以 exponential backoff 加 jitter 重試兩次。",
        "無上限 retry 會放大負載；非 idempotent 操作可能造成重複副作用。",
    ),
    "circuit-breaker": Term(
        "Circuit breaker",
        "偵測 dependency 持續失敗後暫停呼叫，給下游恢復時間並快速回退。",
        "付款供應商大量 timeout 時，暫停新呼叫並顯示稍後重試。",
        "它是保護機制，不是修復根因；threshold 和恢復探測需要仔細設計。",
    ),
    "consensus": Term(
        "Distributed consensus",
        "多個節點即使發生延遲或故障，仍對單一值或操作順序達成一致。",
        "多台 controller 同意目前 leader 和 configuration generation。",
        "Consensus 解決 critical state 協調；LLM 的多數意見不是 consensus protocol。",
    ),
    "quorum": Term(
        "Quorum",
        "足以代表整體並與其他合法集合重疊的節點數。",
        "五個 replica 中三個形成 majority，任意兩個 majority 至少重疊一台。",
        "重疊讓新決策能遇到知道舊決策的節點。",
    ),
    "idempotency": Term(
        "Idempotency",
        "同一操作執行一次或多次，外部結果相同。",
        "以 payment id 作唯一鍵，重送請求不會重複扣款。",
        "Cron、queue、retry 和 agent tool call 都需要 idempotency 才能安全恢復。",
    ),
    "data-integrity": Term(
        "Data integrity",
        "資料在儲存、傳輸、處理和恢復後仍正確、完整且符合 invariant。",
        "Backup 存在不代表可恢復；需定期 restore 並驗證 checksum 與業務規則。",
        "可靠性最終要保護使用者資料，而不只是 process uptime。",
    ),
    "oncall": Term(
        "On-call",
        "在指定時段負責接收 production 事件並協調恢復的輪值制度。",
        "Pager 在夜間通知 checkout SLO 快速燃燒，值班者依 runbook rollback。",
        "健康 on-call 需要可控事件量、訓練、支援和事故後改善時間。",
    ),
    "troubleshooting": Term(
        "Troubleshooting",
        "以證據縮小假設空間，找出能解釋症狀並可被反證的原因。",
        "先比較最近變更與健康區域差異，再驗證 database latency 是否共同上升。",
        "它不是隨機重啟；AI 產生的假設也必須連回證據。",
    ),
    "incident-command": Term(
        "Incident command",
        "事故中明確分離決策、操作、溝通與記錄角色的協作模型。",
        "Incident Commander 排優先順序；Operations Lead 執行；Comms 更新利害關係人。",
        "角色分工降低認知負荷，也避免所有人同時修改 production。",
    ),
    "postmortem": Term(
        "Blameless postmortem",
        "在不簡化成人員責備的前提下，重建事故條件、決策與系統性改善。",
        "問『為何合理操作能造成災難』，而不是只寫『工程師按錯按鈕』。",
        "產物必須包含 owner、期限和驗證方式，否則只是事故故事。",
    ),
    "game-day": Term(
        "Game day",
        "在受控環境主動注入故障，驗證偵測、操作、架構與人員準備。",
        "關閉一個 dependency，確認 timeout、fallback、alert 和 runbook 是否工作。",
        "Game day 把未知問題提前變成可修復問題。",
    ),
    "least-privilege": Term(
        "Least privilege",
        "身份只取得完成當前任務所需的最小權限、範圍和時間。",
        "調查 agent 可讀 logs，但預設不能 restart production。",
        "它限制 prompt injection、誤判或帳號外洩造成的 blast radius。",
    ),
    "provenance": Term(
        "Provenance（來源鏈）",
        "記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。",
        "Container image 可追到 commit、lockfile、builder identity 和簽章。",
        "AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。",
    ),
}
