# 《Agent System 設計全書：從 0 到 1 打造 Agent 與 Agentic Framework》章節大綱

每一列：章｜檔名｜標題｜類型｜Q&A 數｜必須涵蓋。技術現況以 2026-10 的 survey 為準（`/tmp/agent_survey_frameworks.md`、`/tmp/agent_survey_techniques.md`、`/tmp/agent_survey_production.md`）；凡是版本、價格、benchmark 分數、產品細節，一律放在標明日期的「2026 現況」小節，正文以不易過時的原理為主。

貫穿案例 **青鳥科技（Bluebird）**：一家做電商營運 SaaS 的公司，團隊從零開始：先做一個能查訂單、退款的客服 agent，接著做內部 coding agent 與營運分析 research agent，最後把共用的部分抽成自己的 agentic framework **`loom`**。人物：剛轉職的 AI 工程師 Iris、staff engineer 老陳（mentor）、產品經理阿哲、資安工程師 Maya。

全書程式碼：Python 3.11+、只用標準函式庫。用 `ScriptedModel`（依劇本回應的假模型）讓每段程式都能離線執行並附 assert；接真實 API（Anthropic、OpenAI、Gemini）的 adapter 標為 `# not-runnable`。`loom` 從第 4 章的 100 行 loop 一路長成第 45 章的完整 framework。

## Part 0　全局地圖（`Part 0 - 全局地圖/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 1 | 01 - 什麼是 Agent.md | 什麼是 Agent：從一次 LLM 呼叫到自主系統 | concept | 8 | LLM call → workflow → agent 的光譜；agent 的定義（model 在 loop 中自己決定下一步與何時停止）；autonomy 等級（L0–L5）；什麼時候不該用 agent；agent 適合的任務特徵（開放、可驗證、可回復）；青鳥案例介紹；全書地圖與讀法 |
| 2 | 02 - Agent System 全景.md | Agent System 全景：十個組成元件 | concept | 8 | model、harness／loop、tools、context、memory、orchestration、runtime／sandbox、interfaces（UI、API、協定）、evaluation、guardrails／governance；每個元件回答的問題與彼此關係圖；2026 生態地圖（模型廠商、SDK、協定、託管 agent 服務、觀測與評估工具）；Model／Harness／Environment 三層心智模型 |
| 3 | 03 - 給 Agent 建造者的 LLM 基礎.md | 給 Agent 建造者的 LLM 基礎 | concept | 8 | token、context window、sampling；reasoning models 與 effort 控制（thinking 對 agent 的影響、interleaved thinking）；function calling 在各家 API 的形態（messages／responses／interactions、item 與 step）；structured outputs；prompt caching 原理與計價；延遲（TTFT、tokens/s）與成本模型；模型選擇與 model card 怎麼讀 |

## Part 1　從零打造第一個 Agent（`Part 1 - 第一個 Agent/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 4 | 04 - 最小 Agent Loop.md | 100 行的最小 Agent Loop | build | 8 | message 格式、tool schema、dispatch、tool result 回填、停止條件（end_turn、max steps、budget）；ScriptedModel；錯誤處理與 tool 例外回填；streaming 的概念；`loom` v0.1；逐步追蹤一次完整 trajectory 的視覺化 |
| 5 | 05 - Tool 設計.md | Tool 設計：Agent-Computer Interface | build | 8 | tool 是給模型用的 API；命名、描述、參數 schema、範例；粒度（workflow 級 vs CRUD 級）；回傳格式與截斷；錯誤訊息要可行動；idempotency 與副作用分級（read／write／destructive）；pagination；評估 tool 好壞的方法；青鳥訂單／退款 tools 重構 |
| 6 | 06 - 指令與 System Prompt.md | 指令與 System Prompt 設計 | build | 8 | system prompt 結構（角色、目標、規則、工具使用指引、輸出格式）；正確的抽象高度（不過度具體也不空泛）；few-shot 與 canonical examples；instruction hierarchy；prompt 版本管理；prompt 測試；隨模型升級刪減 prompt |
| 7 | 07 - Structured Output 與可靠解析.md | Structured Output 與可靠解析 | build | 8 | JSON schema、constrained decoding、strict mode；驗證與修復迴圈；Pydantic 式資料模型（以 dataclass 實作）；enum 與 discriminated union；部分輸出與 streaming 解析；何時讓模型輸出程式碼而非 JSON |
| 8 | 08 - 推理與規劃 Patterns.md | 推理與規劃 Patterns | build | 8 | ReAct；plan-and-execute；reflection／self-critique 與其限制；tree search（LATS 概念）；reasoning models 讓哪些 pattern 過時；test-time compute 取捨；「先規劃再執行」對安全的價值；每個 pattern 的 Python 實作與比較表 |

## Part 2　Context、Retrieval 與 Memory（`Part 2 - Context 與 Memory/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 9 | 09 - Context Engineering.md | Context Engineering：有限注意力的預算 | build | 8 | context 是稀缺資源；context rot；分層（穩定前綴 → 半穩定 → 動態）；cache-friendly 版面配置（不中途改 tool 定義）；token 預算與計數；just-in-time 載入；檔案系統當外部 context；context 視覺化與量測 |
| 10 | 10 - 長任務與 Compaction.md | 長任務的 Context 管理：Compaction 與 Session Log | build | 8 | tool output clearing；分階段 compaction；摘要即交接筆記；durable session log 與「context 是 log 的可重建視圖」；sub-agent 隔離 context；長任務的進度檔（todo、notes）；compaction 的失敗模式與測試 |
| 11 | 11 - Retrieval 與 Agentic RAG.md | Retrieval 與 Agentic RAG | build | 8 | embedding 與向量檢索原理；BM25、hybrid search、rerank；chunking；傳統 RAG vs agent 主導的檢索（search tool、grep、多輪查詢）；citation 與 grounding；檢索品質量測（recall@k、nDCG）；用純 Python 實作小型 hybrid 檢索 |
| 12 | 12 - Memory 系統.md | Memory 系統設計 | build | 8 | 短期 vs 長期；episodic／semantic／procedural；檔案式 memory（MEMORY.md、memory tool）；寫入政策（何時記、記什麼）、衝突與遺忘；使用者層級 vs 組織層級；隱私與刪除權；Letta／mem0／Zep 等做法比較；Agent Skills 作為 procedural memory |
| 13 | 13 - 大量工具與能力擴充.md | 大量工具與能力擴充 | build | 8 | tool 數量上升時的問題；tool search 與 deferred loading；Skills 漸進揭露；code-as-action（CodeAct、programmatic tool calling、code mode）；何時用 code 取代多次 tool call；token 與正確率的取捨；實作 tool registry 與搜尋 |

## Part 3　協定與環境（`Part 3 - 協定與環境/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 14 | 14 - MCP.md | Model Context Protocol 深入 | build | 8 | 為什麼需要 MCP；host／client／server；tools、resources、prompts；transport（stdio、Streamable HTTP）；2026-07-28 stateless 改版（server/discover、multi round-trip、deprecated 項目）；授權（OAuth、resource indicator、禁止 token passthrough）；extensions（MCP Apps、Skills over MCP、Tasks）；用純 Python 寫一個最小 MCP 風格 server 與 client；MCP 的安全注意事項 |
| 15 | 15 - A2A 與 AG-UI.md | Agent 之間與 Agent 到前端：A2A 與 AG-UI | build | 8 | A2A 的 agent card、task 生命週期與狀態（含 input-required、auth-required）、streaming 與 push；A2A vs MCP 的分工；AG-UI 事件模型與前端串流；generative UI；agent payments 協定概覽（AP2、ACP、x402）與信任問題；實作 task 狀態機 |
| 16 | 16 - Computer Use 與 Browser Agent.md | Computer Use 與 Browser Agent | build | 8 | perception–action loop；截圖 vs DOM／accessibility tree；座標與動作空間；等待、驗證與重試；登入與 CAPTCHA 的處理原則；成本與延遲；可靠性設計（checkpoint、人工接手）；適用與不適用的場景；模擬環境中的實作 |
| 17 | 17 - Code Execution 與 Sandbox.md | Code Execution 與 Sandbox | build | 8 | 為什麼 agent 需要執行環境；隔離層級（process、container、gVisor、microVM）；檔案系統、網路 egress 控制、資源限制；secrets 不進 sandbox；sandbox 生命週期與 pool；託管 sandbox 服務概覽；用 subprocess 與資源限制實作安全的執行器（概念版） |

## Part 4　Workflow 與 Multi-Agent Orchestration（`Part 4 - Orchestration/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 18 | 18 - Workflow Patterns.md | 五種 Workflow Patterns | build | 8 | prompt chaining、routing、parallelization（sectioning、voting）、orchestrator-workers、evaluator-optimizer；每種的適用條件、成本、失敗模式與 Python 實作；workflow 與 agent 的混合 |
| 19 | 19 - Graph 與 State Machine.md | Graph 與 State Machine Orchestration | build | 8 | 把 agent 建模成狀態機與 graph；節點、邊、條件分支、共享 state；checkpoint 與 time travel；interrupt 與恢復；何時 graph 有幫助、何時是過度設計；實作小型 graph runtime |
| 20 | 20 - Multi-Agent 架構.md | Multi-Agent 架構與取捨 | build | 8 | orchestrator–subagent、supervisor、handoff、swarm、debate；context 共享是核心問題；何時 multi-agent 值得（廣度搜尋、可平行、需要隔離）與何時不值得（緊耦合的寫入）；成本倍數；並行寫入的隔離（branch、worktree）；Anthropic research system 與 Cognition 觀點；實作 orchestrator-subagent |
| 21 | 21 - Human-in-the-Loop.md | Human-in-the-Loop 設計 | build | 8 | approval gate 與風險分級；interrupt／resume；escalation 給真人；信任 UX（顯示計畫、diff、可撤銷）；approval fatigue；自動核准 classifier 的角色與限制；稽核；實作 approval policy engine |
| 22 | 22 - Durable Execution 與長時間 Agent.md | Durable Execution 與長時間 Agent | build | 8 | 長時間任務的失敗（crash、deploy、rate limit）；durable execution 原理（event history、replay、determinism）；activity 的 idempotency；background agent、排程與佇列；Temporal／Restate 等概念對照；實作基於事件日誌的可恢復 runner |

## Part 5　打造自己的 Agentic Framework（`Part 5 - 打造 Framework/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 23 | 23 - Framework 設計原則.md | Framework 設計原則與核心抽象 | build | 8 | 為什麼要（或不要）自己做 framework；核心抽象：Agent、Tool、Runner、Session、Event、Handoff、Guardrail；最少抽象原則；hooks 與 middleware；擴充點；API 設計與向後相容；`loom` 的架構圖 |
| 24 | 24 - Runtime 實作.md | Runtime 實作：事件、串流、並行與取消 | build | 8 | event stream 設計；streaming 回傳；parallel tool calls；cancellation 與 timeout；retry 與 backoff；loop guard（重複動作偵測、預算）；asyncio 實作；runtime 的測試策略 |
| 25 | 25 - Model 抽象與 Routing.md | Model 抽象、Provider Adapter 與 Routing | build | 8 | provider 差異（訊息格式、tool 格式、thinking、cache）；adapter 介面設計；fallback 與熔斷；model routing（依難度、成本、延遲）；主模型＋輔助模型；成本計量；實作 router |
| 26 | 26 - 主流框架比較與選型.md | 主流框架與託管服務：比較與選型 | concept | 8 | OpenAI Agents SDK、Claude Agent SDK、Google ADK、LangGraph、Microsoft Agent Framework、CrewAI、AG2、Pydantic AI、DSPy、Strands、Mastra、LlamaIndex；託管 agent 服務（Managed Agents、Agents API、AgentCore、Agent Engine）；比較維度表；build vs buy 決策；遷移與避免 lock-in；2026 現況小節 |

## Part 6　評估、可觀測性與優化（`Part 6 - 評估與優化/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 27 | 27 - Agent Evaluation.md | Agent Evaluation：怎麼知道它真的變好了 | build | 8 | outcome vs trajectory 評估；code grader、LLM-as-judge（偏誤與校準）、human eval；pass@k vs pass^k；eval set 怎麼建（從真實失敗開始、error analysis）；環境與 state 檢查；回歸測試；統計顯著性；實作 eval harness |
| 28 | 28 - Benchmarks.md | Benchmarks 全覽與如何解讀 | concept | 8 | SWE-bench 系列、Terminal-Bench、τ-bench 系列、OSWorld、WebArena、GAIA、BrowseComp、MLE-bench 等測什麼；飽和、污染、版本差異；benchmark 與自家任務的落差；建立內部 benchmark；2026 現況小節（分數一律標版本與日期） |
| 29 | 29 - Observability.md | Observability：Tracing、成本與除錯 | build | 8 | trace、span、session；OpenTelemetry GenAI semantic conventions（agent、tool、model span）；記錄什麼、遮蔽什麼（PII）；成本與 token 儀表板；從 trace 找失敗原因；線上監控指標；實作 tracer |
| 30 | 30 - 優化.md | 優化：Prompt、Model、成本與延遲 | build | 8 | prompt optimization（DSPy、GEPA 概念）；fine-tuning for tool use；agent 的 RL（可驗證 reward、環境、reward hacking）；harness 隨模型升級而簡化；cache 命中率優化；延遲優化（平行、串流、小模型）；成本優化 |

## Part 7　安全、可靠性與治理（`Part 7 - 安全與治理/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 31 | 31 - Agent 威脅模型.md | Agent 威脅模型 | concept | 8 | 攻擊面總覽；direct／indirect prompt injection（只談成因與防禦）；lethal trifecta；tool poisoning 與 MCP 供應鏈風險；data exfiltration 管道；過度代理（excessive agency）；OWASP LLM Top 10 與 Agentic Top 10 對照；為青鳥客服 agent 做 threat modeling |
| 32 | 32 - 防禦設計.md | 防禦設計：架構層的安全 | build | 8 | least privilege 與能力切分；dual-LLM、plan-then-execute、CaMeL 等設計模式；輸入／輸出 guardrails；分類器的定位；sandbox 與 egress；高風險動作的確認；縱深防禦；實作 capability-based tool 權限 |
| 33 | 33 - Identity 與授權.md | Identity、授權與稽核 | build | 8 | agent identity；代表使用者行動（delegation）與 OAuth；scope 與 step-up；MCP 授權模型；secrets 管理；多租戶隔離；稽核日誌與不可否認性；實作授權與稽核 middleware |
| 34 | 34 - 可靠性失敗模式與治理.md | 可靠性、失敗模式與治理 | concept | 8 | failure taxonomy（MAST 等研究）；無限迴圈、hallucinated tool call、過早宣告完成、context rot、reward hacking；error recovery 設計；agent 的 SLO 與 error budget；事故處理與 postmortem；EU AI Act、NIST AI RMF、ISO 42001 的概念層級要求；內部治理流程 |

## Part 8　Agent System Design：從 0 到 1（`Part 8 - System Design/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 35 | 35 - 設計方法論.md | Agent System Design 方法論 | design | 8 | 七步驟設計框架（任務與成功標準 → autonomy 與風險 → 架構選型 → context 與 tools → 評估 → 安全 → 營運）；需求釐清清單；容量與成本估算（token、QPS、並行 session）；design doc 範本；設計審查 checklist |
| 36 | 36 - Production 架構.md | Production 架構與部署 | design | 8 | 參考架構圖（gateway、session store、event log、sandbox pool、queue、model gateway、tool gateway、observability）；scaling 與多租戶；版本管理（prompt、model、tool）；canary、A/B 與 shadow；rate limit 與配額；災難復原 |
| 37 | 37 - 產品化與使用者體驗.md | 產品化：UX、信任與回饋迴圈 | design | 8 | 同步 vs 非同步互動；串流與進度呈現；可解釋性與可撤銷；錯誤時的使用者體驗；回饋收集與資料飛輪；定價與單位經濟；導入組織的變革管理 |
| 38 | 38 - 從 Prototype 到 Production.md | 從 Prototype 到 Production 的路線圖 | design | 8 | 五個階段（探索、prototype、內部試用、有限上線、規模化）每階段的目標、產出與退出條件；常見陷阱；團隊組成與角色；上線前檢查清單；青鳥客服 agent 的完整歷程 |

## Part 9　案例研究與設計演練（`Part 9 - 案例與演練/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 39 | 39 - Coding Agents.md | 案例：Coding Agents | case | 8 | Claude Code、Codex、Cursor、Devin、GitHub Copilot coding agent、Gemini CLI 的架構拆解（loop、tools、context 策略、sandbox、審核、評估）；共同模式與差異；可借鏡的設計；只寫公開資訊並標日期 |
| 40 | 40 - Research Agents.md | 案例：Deep Research 與 Research Agents | case | 8 | 各家 deep research 系統的架構；multi-agent research 的設計與成本；搜尋、閱讀、綜合、引用的流程；評估方法；可借鏡的設計 |
| 41 | 41 - 企業與客服 Agents.md | 案例：客服、企業與垂直領域 Agents | case | 8 | 客服 agent（Sierra、Intercom Fin 等）、法律（Harvey）、通用 agent（Manus、ChatGPT agent）的公開架構重點；政策遵循、知識庫、轉真人；垂直領域的評估與風險 |
| 42 | 42 - 設計演練一 客服 Agent 平台.md | 設計演練一：多租戶客服 Agent 平台 | design | 8 | 以 system design interview 形式完整走一遍：需求、估算、架構、資料流、tools、context、評估、安全、營運、擴展、取捨與追問 |
| 43 | 43 - 設計演練二 Background Coding Agent.md | 設計演練二：Background Coding Agent 平台 | design | 8 | 同上形式：從 issue 到 PR 的非同步 coding agent；sandbox pool、repo 快取、驗證（測試、review agent）、平行任務、成本控制 |
| 44 | 44 - 設計演練三 企業 Research 與 Analytics Agent.md | 設計演練三：企業 Research 與 Analytics Agent | design | 8 | 同上形式：跨內部資料源的研究與數據分析 agent；權限感知檢索、SQL 與 code execution、多 agent 研究、引用與可信度 |

## Part 10　Capstone 與未來（`Part 10 - Capstone/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 45 | 45 - Capstone 組裝 loom.md | Capstone：組裝完整的 loom Framework | build | 8 | 把全書元件組成一個完整 framework：runner、tools、MCP 風格 client、memory、compaction、guardrails、approval、tracing、eval、durable log；端到端跑青鳥三個 agent；目錄結構與擴充指南；下一步可以怎麼長 |
| 46 | 46 - 趨勢與持續學習.md | 趨勢、開放問題與持續學習 | concept | 8 | 正在變化的方向（模型自主時間變長、託管 agent、協定標準化、agent 經濟、評估方法）；尚未解決的問題；如何追蹤新技術而不被炒作帶著走；本書的使用與更新方式 |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - 術語表.md | 全書術語（英文、中文、一句話定義、首次出現章） |
| B - loom 程式碼導覽.md | 全書 Python 範例與 `loom` 各模組的索引、依賴關係與執行方式 |
| C - 框架與協定速查.md | 主要 SDK、協定、託管服務的速查表（核心抽象、適用場景、2026-10 版本狀態），附查證日期 |
| D - 設計與上線 Checklists.md | 設計審查、tool 審查、安全審查、eval、上線、事故處理 checklists |
| E - Agent System Design 面試題.md | 30 題 agent system design 與概念面試題，附答題框架與參考答案要點 |
| F - 延伸閱讀.md | 官方指南、engineering blog、論文與規格文件，依主題整理（只列名稱與出處，不放 URL） |
