# 附錄 C　框架與協定速查

> [!abstract] 本附錄地圖
> **用途**：在選型會議、設計審查或讀別人的架構文件時，快速查到一個 SDK、框架、協定、託管服務或 durable execution 引擎「是什麼、核心抽象是什麼、適合與不適合什麼、本書在哪一章講」。本附錄只整理，不取代第 14、15、22、26 章的完整討論；判斷方法（分層、九個選型維度、gate 與加權矩陣）請回到第 26 章。
>
> **怎麼查**：
> - 有明確需求、想知道該看哪幾個候選：先查 C.2 的「需求 → 候選」速選表。
> - 已經有候選、想知道它的設計哲學與限制：查 C.3（SDK 與框架）、C.5（協定）、C.7（託管服務）、C.8（durable execution 引擎）。
> - 想比較同一個機制在各家怎麼做（暫停與恢復、狀態、multi-agent）：查 C.4 與 C.6。
> - 要寫進文件或簡報的版本號：只從 C.9「2026 現況」取用，並保留查證狀態與日期；C.10 列出寫進正式文件前必須再核對的項目。
>
> **前置知識**：第 26 章（選型方法）。各列最後一欄的「本書章節」指出該概念的完整解釋在哪裡。

## C.1 怎麼讀這份速查表

本附錄的表格分成兩種。第一種是**原理表**（C.2 到 C.8）：記錄核心抽象、設計哲學、適用場景與限制，這些內容來自各專案的公開設計文件，變動較慢，一兩年內通常仍然成立。第二種是**現況表**（C.9）：記錄版本號、發布日期、beta 或 GA 狀態，這些內容每週都在變，只代表截至 2026 年 10 月的快照。把兩者分開，是因為選型的判斷應該建立在第一種資訊上，第二種資訊只用來確認「現在能不能用、要付多少升級成本」。

每一筆現況資訊都帶有查證狀態，定義沿用本書撰寫時的技術 survey：

| 查證狀態 | 意義 | 使用方式 |
|---|---|---|
| 已查證 | 於 2026-10-02 讀取官方文件、GitHub releases 或官方網站確認 | 可以直接引用，但仍要寫明「截至 2026 年 10 月」 |
| 部分查證 | 主要事實已確認，細節（API 名稱、日期、整合範圍）來自模型知識 | 主要事實可引用；細節寫進設計文件前要再查 |
| 未查證 | 只依模型知識（約 2026 年中），本書未能從官方來源確認 | 只能以保留語氣使用，或在採用前自己查證 |

另一個常見的閱讀錯誤是把不同類別的東西放在同一張表上二選一。下圖沿用第 26 章的分層，標出每一類項目大致落在 agent 技術堆疊的哪幾層：

```text
 堆疊層（第 26 章）        主要涵蓋的類別                    本附錄小節
 ┌────────────────────────────────────────────────────────────────────────┐
 │ ⑥ 平台服務              託管平台積木（identity、gateway、    C.7
 │                         memory、policy、eval）
 ├────────────────────────────────────────────────────────────────────────┤
 │ ⑤ 執行環境              durable execution 引擎、託管 runtime C.8、C.7
 ├────────────────────────────────────────────────────────────────────────┤
 │ ④ 編排                  graph／workflow 框架、multi-agent    C.3、C.4
 ├────────────────────────────────────────────────────────────────────────┤
 │ ③ harness（agent loop） code-first SDK、完整 harness SDK、   C.3、C.7
 │                         託管 harness
 ├────────────────────────────────────────────────────────────────────────┤
 │ ② 能力（tools、prompts）永遠由你擁有；DSPy 優化其中的模組    C.3
 ├────────────────────────────────────────────────────────────────────────┤
 │ ① 模型與低階 API        各家有狀態的模型 API                C.7
 └────────────────────────────────────────────────────────────────────────┘
   協定（MCP、A2A、AG-UI、payments）不屬於任何一層，而是層與層、
   系統與系統之間的「邊」，見 C.5、C.6
```

由下往上讀這張圖：第 ① 層是模型 API，第 ② 層是你的業務 tools 與 prompts，第 ③ 到 ⑤ 層是可以分開外包的 harness、編排與執行環境，第 ⑥ 層是平台服務。DSPy 雖然常被列在「框架」清單裡，它優化的其實是第 ② 層裡的個別模組，所以不能拿來和 LangGraph 二選一（第 26 章稱為類別錯誤）。協定畫在最下方，因為它們描述的是邊而不是層：MCP 是 agent 到 tools 的邊，A2A 是 agent 到 agent 的邊，AG-UI 是 agent 到前端的邊（第 15 章 15.2 節）。

## C.2 速選表：需求 → 候選

這張表把常見需求對應到值得進入 POC 的候選。它是「提出 POC 假設」的起點，不是結論：候選的排列沒有優先順序，表中的判斷是本書依公開設計文件的歸納，不是官方說法。用法是先找出你的硬性限制（資料駐留、ZDR、語言、指定模型），用第 26 章 26.8 節的流程淘汰做不到的選項，再從下表挑兩到三個候選，用第 26 章 26.3 節「不愉快的路徑」做 POC。

| 需求 | 候選 | POC 時先驗證什麼 | 本書章節 |
|---|---|---|---|
| 其實步驟可以事先列舉、不需要模型決定下一步 | 不用 agent：寫函式或 workflow（MAF 官方文件也明說能寫函式就不要用 agent） | 用任務適合度三問（開放、可驗證、可回復）檢查 | 第 1、18 章 |
| 單一 agent、少量 tools、要快速上線（Python） | OpenAI Agents SDK、Pydantic AI、Strands Agents；或模型 API 加自寫 loop | 未標註副作用的 tool 預設是否需要核准；run state 能否序列化 | 第 4、26 章 |
| 流程有顯式狀態、要長時間暫停、從任一步恢復（退款、審批） | LangGraph、MAF workflows、Google ADK 2.x graph workflow；搭配 durable 引擎 | 核准前離開三小時再回來；在有副作用的 tool 前後殺 process | 第 19、21、22 章 |
| 需要檔案系統＋shell 的通用 agent（coding、ops、文件處理） | Claude Agent SDK；託管選項：Claude Managed Agents、OpenAI Agents API、AgentCore Harness | permission 與 hooks 能否接上自家 approval 政策；sandbox 的 egress 與 secrets | 第 17、26 章 |
| 型別安全、結構化輸出密集的業務 agent | Pydantic AI；其他框架加上 strict 模式的 structured output | 輸出驗證失敗時的修復迴圈；依賴注入是否方便測試 | 第 7、26 章 |
| TypeScript 全端團隊、SaaS 內嵌 agent | Mastra、OpenAI Agents SDK（JS）、Google ADK（TS）、Vercel AI SDK（未查證） | 前端串流是否能經由 AG-UI 與後端解耦 | 第 15、26 章 |
| .NET 或 Microsoft 生態的企業 | Microsoft Agent Framework（MAF） | minor 版本的 breaking change 頻率；checkpoint 的儲存位置 | 第 19、26 章 |
| 需要 Go、Java、Kotlin 等多語言 | Google ADK；MAF 有 Go preview 版 | 各語言版本的功能是否對等 | 第 26 章 |
| 角色式多 agent 原型、內容或研究類協作 | CrewAI（Crews 加 Flows） | 自主模式的可預測性；需要確定性時能否改用 Flows | 第 20、26 章 |
| 文件密集、RAG 為主的 agent 或抽取 pipeline | LlamaIndex Workflows／Agents | event 驅動的控制流是否好除錯；Context 序列化與恢復 | 第 11、26 章 |
| 優化 router、抽取器、judge 等個別模組的 prompt | DSPy（與任何 orchestration 框架並用） | metric 是否可靠；優化結果能否版本化 | 第 30 章 |
| 想研究或教學 code-as-action | smolagents（注意維護節奏放緩）；MAF、LlamaIndex 的 CodeAct 類 agent | 執行器不是安全邊界，正式使用要接 sandbox | 第 13、17 章 |
| 想把協定當成框架的核心介面 | AG2 v1（protocol-first） | 舊 AutoGen 程式不能直接升級；長期維護風險 | 第 14、15、26 章 |
| 同一組 tools 要給多個 host 或多個 agent 共用 | 寫成 MCP server；agent 框架當 MCP client | 2026-07-28 版的無狀態語意；tool 數量大時的 context 成本 | 第 13、14 章 |
| tool 數量上百、context 被 tool 定義塞滿 | tool search 與 deferred loading（Anthropic tool search、AG2）；Skills 漸進揭露 | 前綴不變式：載入新 tool 只追加、不重排 | 第 13 章 |
| 委派給另一個組織的 agent，任務會跑很久、中途要補件或授權 | A2A；ADK、MAF、Strands、AG2 有 A2A 支援 | task 狀態以 server 為準；中斷態的處理 | 第 15 章 |
| 前端要即時顯示文字、tool 進度、共享 state、中途讓使用者確認 | AG-UI（多數主流框架有整合） | 斷線重連與重複事件的冪等處理 | 第 15、37 章 |
| agent 要替使用者付款或購買 | AP2（授權證明）、ACP／UCP（商務流程）、x402／MPP（HTTP 402 付款）；AgentCore Payments | agent 只拿受限 token；限額檢查用確定性程式 | 第 15、33 章 |
| 任務跨天等待、要跨部署存活、不重做副作用 | Temporal、Restate、DBOS、Inngest；Pydantic AI 內建 durability 後端 | 殺 process 測試；activity 的 idempotency key | 第 22 章 |
| 已經有 Postgres，不想多營運一個 orchestrator | DBOS、Absurd（Pydantic AI 已整合） | 歷史與 payload 大小對資料庫的壓力 | 第 22 章 |
| serverless 部署、以 HTTP 呼叫函式 | Restate、Inngest | 長時間等待時是否不佔用 compute | 第 22 章 |
| 營運人力少、合規允許資料由廠商保存 | 託管 harness：Claude Managed Agents、OpenAI Agents API、AgentCore Harness | 出事時能拿到什麼紀錄；離開時 session 能否匯出 | 第 26 章 |
| 資料必須留在自家帳號與區域、需要 ZDR 或 HIPAA | 自託管框架；雲端平台只用積木（runtime、identity、gateway） | 逐項確認區域、保留政策、私有網路；排除不支援的託管 harness | 第 26、33、36 章 |
| AWS 上的生產 agent | Strands Agents 搭配 Amazon Bedrock AgentCore；AgentCore Runtime 也支援其他框架 | Policy 在 Gateway 層的攔截規則；Runtime 的 session 限制（未查證） | 第 26、33 章 |
| Google Cloud 上的企業、需要 A2A | Google ADK 搭配 Gemini Enterprise Agent Platform 的 Agent Runtime | 1.x 到 2.x 的遷移成本；Sessions 的存取控管 | 第 15、26 章 |
| Azure 或 Microsoft 企業環境 | MAF 搭配 Microsoft Foundry（hosted agents 細節部分查證） | 與 Entra 等既有身分系統的整合 | 第 26、33 章 |

讀這張表時有三個提醒。第一，同一個需求列了多個候選，代表它們都「可能」滿足，差別要靠 POC 量出來；第 26 章 26.11 節的加權矩陣顯示，即使分數接近，最後也常取決於「將來換不換得掉」這類價值判斷。第二，有些列描述的是硬性限制而不是偏好，例如資料駐留那一列，做不到就直接出局，不要放進加權。第三，不論選哪個候選，tool 定義、approval 政策、prompts、eval 與 session log 格式都要以不依賴框架的形式自己擁有（第 26 章 26.9 節）。

> [!warning] 常見誤解
> 「速選表選出的第一個候選就是答案。」這張表只回答「哪些值得試」，不回答「哪個最好」。真正決定選型的是你自己的 POC 結果，尤其是核准等待、殺 process、trace 匯出這些在 demo 中看不到的路徑。

## C.3 SDK 與框架速查：核心抽象、適用場景與限制

下表依第 26 章 26.6 節的分類整理十三個主流 SDK 與框架。「核心抽象」列出理解它所需的最少概念；「限制」是本書歸納的取捨，不代表官方立場，而且可能在之後的版本被改善。API 名稱以公開文件為準，標示「部分查證」的名稱在 C.9 與 C.10 有說明。

| 項目 | 設計哲學 | 核心抽象 | 適用場景 | 限制 | 本書章節 |
|---|---|---|---|---|---|
| OpenAI Agents SDK（Python、JS） | 少量 primitive，用程式碼編排 | `Agent`、`Runner`、function tools、agents-as-tools、handoff、guardrails（與主 agent 並行）、sessions、`RunState`、tracing、MCP、sandbox agents | 以 OpenAI 模型為主的產品型 agent；客服分流（triage 加 handoff）；需要 sandbox 的 coding 或 data agent | 仍是 0.x，minor 版本有 breaking change；沒有顯式 graph 抽象；最順的路徑在 OpenAI 生態 | 第 20、21、26 章 |
| Claude Agent SDK（Python、TS） | harness-first：把 Claude Code 當成 library | `query()`、`ClaudeSDKClient`、選項物件（allowed tools、permission mode、`can_use_tool`、MCP servers、hooks、subagents）、內建檔案與 shell tools、hooks、subagents、skills、`CLAUDE.md`、in-process MCP server、session resume／fork | coding、ops、研究、文件處理等需要檔案系統與 shell 的通用 agent | 底層驅動 CLI binary，多一個 process 邊界並需要 Node 環境；主要綁定 Claude 模型；純對話型 agent 顯得厚重；第三方產品不得提供 claude.ai 登入 | 第 10、13、17、26 章 |
| Google ADK | event 串流是唯一真相（session 即 event log） | `LlmAgent`、workflow agents（循序、平行、迴圈）、2.x 的 graph `Workflow`、`Runner`、Session／Memory／Artifact service、callbacks、plugins、`McpToolset`、`OpenAPIToolset`、`AgentTool` | Google Cloud 企業；多語言團隊；需要 A2A 的多 agent 系統；語音 agent | 概念多；最順的路徑在 Gemini 與 Google Cloud；1.x 到 2.x 有遷移成本 | 第 15、19、26 章 |
| LangGraph／LangChain | state machine 加持久化 checkpoint | `StateGraph`、reducer、node 與條件邊、`Command`、`Send`、subgraph、checkpointer（以 thread 隔離、time travel）、`interrupt()`、Store；LangChain 的 `create_agent` 與 middleware 建在其上 | 需要精確流程控制、長時間運行、HITL 與 time travel 的生產 agent | reducer、super-step 等概念有學習曲線；LangChain 歷史包袱；部署與觀測平台多與 LangSmith 綁定 | 第 19、21、22、26 章 |
| Microsoft Agent Framework（MAF） | AutoGen 與 Semantic Kernel 的後繼；agent 與 typed workflow 分層 | Agent（多 provider）、agent session、context providers、middleware、functional 與 graph workflows（executors、edges、checkpoint、request／response 式人工介入）、內建 orchestration（循序、並行、handoff、group chat、Magentic）、Harness Agent | .NET 或 Microsoft 生態的企業；需要 typed workflow 與 checkpoint 的多 agent 系統 | API 仍頻繁變動；偏向 Azure；Python 社群動能不如 LangGraph | 第 19、20、26 章 |
| CrewAI | 角色扮演加確定性 Flows | `Agent`（role、goal、backstory）、`Task`、`Crew`（循序或階層）、Flows（`@start`、`@listen`、`@router`、`@persist`）、memory、guardrails | 原型；內容與研究類多角色協作；商務自動化 PoC | 自主模式的可控性與可預測性較差；高階抽象難以精細調校 | 第 20、26 章 |
| AG2（v1） | protocol-first：以標準協定作為 agent 的對外介面 | 以協定為核心的 agent；支援 MCP、A2A、AG-UI、Agent Client Protocol、NLIP；tool search 與 deferred loading | 想以協定互通為核心設計的團隊；參考「協定優先」的框架設計 | v1 是重寫的新框架，舊 AutoGen 式程式不能直接升級；品牌與 API 多次分裂 | 第 14、15、26 章 |
| Pydantic AI | agent 是有型別的函式 | `Agent[Deps, Output]`、`RunContext`（依賴注入）、`@agent.tool`、toolsets（含 MCP）、`run()`／`run_stream()`／`iter()`、pydantic-graph、可插拔 durability 後端、Logfire 觀測、pydantic-evals | 重視型別與可測試性的 Python 後端；結構化輸出密集的業務 agent | 發版極快；高階多 agent pattern 較少，需要自己組 | 第 7、22、26 章 |
| DSPy | prompt 是可編譯、可優化的參數 | Signature、Module（`Predict`、`ChainOfThought`、`ReAct`）、Optimizer（MIPROv2、GEPA 等）、metric、Adapter、`dspy.RLM` | 在 agent 系統中優化個別模組（router、抽取器、judge） | 不是 orchestration 框架；拿來與 graph 框架二選一是類別錯誤 | 第 13、30 章 |
| Strands Agents（Python、TS） | 相信模型：盡量不寫 orchestration | model-driven `Agent(model, tools, system_prompt)`、`@tool`、MCP tools、hooks、conversation managers、session managers、多 agent（agents-as-tools、Swarm、Graph、Workflow）、A2A、OTel | AWS 上的生產 agent；「強模型加好 tools 就夠」的任務 | 預設偏向 Bedrock 與 AWS；需要從頭到尾的確定性流程時要改用 Graph 或 Workflow | 第 20、26 章 |
| Mastra（TS） | batteries-included 的 TS agent server | `Agent`、`createTool`（Zod）、workflows（`.then`、`.parallel`、`.branch`、`suspend()`／`resume()`）、memory（thread、working memory、語意召回）、processors、scorers、Studio、MCP client 與 server | Next.js 或 Node 全端團隊；SaaS 內嵌 agent | API 表面積大、變動快；Python 團隊用不到 | 第 15、26 章 |
| LlamaIndex Workflows／Agents | 以 event 與 step 描述流程 | Workflow、`@step`、typed Event（`StartEvent`、`StopEvent`）、`Context`（可序列化、`wait_for_event`）、`FunctionAgent`、`ReActAgent`、`CodeActAgent`、`AgentWorkflow` | document agent；RAG 密集的 workflow；資料抽取 pipeline | core 仍是 0.x；agent 層影響力不如 LangGraph；生態偏向 RAG | 第 11、26 章 |
| smolagents | code as action，核心極簡 | `CodeAgent`（以 Python 程式作為動作）、`ToolCallingAgent`、`Tool`／`@tool`、本地執行器（AST 檢查）、遠端執行器、`MCPClient` | 教學；理解 CodeAct 範式 | 持久化、HITL、觀測等生產功能較弱；本地執行器不是安全邊界；維護節奏放緩 | 第 13、17 章 |

表中有兩欄最值得在 POC 前先看。「限制」欄是可以提前排除候選的訊號，例如需要從頭到尾確定性流程的退款 agent，就不該把「相信模型」的框架當成唯一候選。「本書章節」欄則告訴你要驗證的機制在哪裡被完整解釋：例如評估 LangGraph 的 HITL，應該先讀第 21 章的 approval 狀態機，才知道要檢查「核准是否綁定參數 hash」這類細節，而不只是「有沒有 interrupt」。

除了上表，下列項目也常出現在選型清單中。本書撰寫時未逐一查證它們的現況，表中只寫公開資料中較穩定的定位；採用前請自行查證。

| 項目 | 定位（保留語氣） | 查證狀態 | 本書章節 |
|---|---|---|---|
| Vercel AI SDK（TS） | TS 的模型呼叫與 agent 工具組，常被其他 TS 框架當成底層；有 durable 相關的 workflow 工具 | 未查證（Temporal 與 Restate 有它的整合範例，已查證） | 第 22、26 章 |
| Cloudflare Agents SDK | 以 Durable Objects 為每個 agent 實例提供狀態、排程與連線 | 未查證 | 第 22 章 |
| Letta（前 MemGPT） | 以記憶管理為核心的 agent 平台 | 未查證（概念見第 12 章） | 第 12 章 |
| Semantic Kernel、AutoGen | MAF 的前身；官方提供遷移到 MAF 的指南 | 部分查證（是否正式標示為維護模式未查證） | 第 26 章 |
| Agno、Haystack、Spring AI、Firebase Genkit、goose | 其他語言或生態的 agent 框架與工具；Spring AI 有 AG-UI 整合 | 多數未查證（Spring AI 的 AG-UI 整合已查證） | 第 26 章 |

## C.4 框架機制對照：狀態、HITL、multi-agent 與可觀測性

同一個機制在各框架有不同的名字。下表把第 26 章九個維度中最常在 POC 被檢查的四個（狀態管理、HITL、multi-agent、可觀測性），對應到各框架的具體機制。名稱依公開文件整理，部分細節未查證（見最後一欄）。

| 框架 | 狀態與恢復 | 暫停等人（HITL） | multi-agent 原語 | 可觀測性 | 細節查證 |
|---|---|---|---|---|---|
| OpenAI Agents SDK | sessions（SQLite、SQLAlchemy、Redis、MongoDB、Dapr、加密 session 等）；`RunState` 序列化後 resume | tool 的 `needs_approval` 使 run 帶著 interruptions 結束，核准或拒絕後 resume | handoffs、agents-as-tools | 內建 tracing，可接自訂 trace processors | 部分查證 |
| Claude Agent SDK | session resume 與 fork；檔案系統與 `CLAUDE.md` | permission modes、`can_use_tool` callback、hooks | subagents（含背景執行） | hooks；OTel 經由 CLI | 部分查證；OTel 未查證 |
| Google ADK | SessionService（event log 加 state）、MemoryService、ArtifactService；2.x workflow 失敗節點在 resume 時重跑 | tool confirmation、workflow 中的 `RequestInput` | sub-agents、workflow agents、graph、A2A | OTel、Cloud Trace、eval 工具 | 部分查證 |
| LangGraph | checkpointer 每個 super-step 存一份快照，以 `thread_id` 隔離，可 time travel；Store 存跨 thread 記憶 | `interrupt()` 加 `Command(resume=...)`；靜態的 interrupt before／after | subgraph、supervisor、swarm、`Send` fan-out | LangSmith | API 細節未查證 |
| MAF | agent session、context providers、workflow checkpoint、session store（例如 Blob） | workflow 的 request／response、tool approval | 循序、並行、handoff、group chat、Magentic | OTel、DevUI | 部分查證；workflow API 名稱未查證 |
| CrewAI | Flow state 加 `@persist`（SQLite）、memory | human input、Flow 中的 HITL 與 pause 事件 | Crew（循序、階層） | AMP tracing、OTel | 部分查證 |
| AG2 v1 | 公開資料未說明（未查證） | 雙向 input requests、AG-UI 的 mid-run human input | 多 agent 對話、經由協定互連 | Prometheus、OTel | 部分查證 |
| Pydantic AI | message history、workspaces、可插拔 durability 後端（Temporal、Absurd 等） | deferred tools 與 approval（未查證） | agent delegation、graph | Logfire（OTel） | 部分查證 |
| Strands Agents | session managers（file、S3）、conversation managers；Graph／Swarm 的 snapshot | hooks、interrupt（未查證） | agents-as-tools、Swarm、Graph、Workflow、A2A | OTel | 部分查證 |
| Mastra | memory（thread、working、semantic、observational）加 workflow snapshot | workflow `suspend()`／`resume()`、tool approval | agent networks、workflows | 內建 tracing、Studio、scorers | 部分查證 |
| LlamaIndex | `Context` store，可序列化後恢復 | `wait_for_event`、HITL events | `AgentWorkflow`（handoff） | OTel 類整合（未查證） | 部分查證 |
| smolagents | 記憶體內的 memory steps | 弱 | managed agents | OTel、MLflow | 部分查證 |

這張表有一個值得注意的規律：「狀態與恢復」一欄大致分成兩派。一派以**快照**恢復（LangGraph checkpointer、Mastra workflow snapshot、MAF checkpoint），粒度是節點或步驟；另一派以**事件紀錄**恢復（ADK 的 session event log），state 由事件推導。這正是第 22 章 22.3 節的「快照 vs 事件重播」，也和第 10 章「context 是 session log 的純函式」的不變式相通。框架內建的這些機制通常只負責「狀態存得下來」，不負責 worker 排程、持久化計時器與跨服務重試，後者需要 C.8 的 durable 引擎或託管 runtime。

> [!tip] 用這張表設計 POC
> 每一欄都可以轉成一個 POC 測試：「狀態與恢復」對應殺 process 測試，「暫停等人」對應「核准前離開三小時」與「核准後參數被改」測試，「可觀測性」對應「把一次失敗 run 的 trace 匯出到自家系統」測試。測試方法見第 26 章 26.4 節的表格。

## C.5 協定速查：MCP、A2A、AG-UI 與 agent payments

協定的第一個問題永遠是「它連接哪兩方」（第 15 章 15.2 節）。下表先列三個主要協定，再列 agent payments 的五個協定與兩個容易混淆的同縮寫協定。

| 協定 | 連接的兩方 | 核心抽象 | 互動單位與狀態模型 | 適用 | 限制與注意 | 本書章節 |
|---|---|---|---|---|---|---|
| MCP（Model Context Protocol） | host／agent ↔ tools 與資料 | server primitives：tools（模型控制）、resources（應用控制，以 URI 定址）、prompts（使用者控制）；client 端的 elicitation；transport：stdio、Streamable HTTP；extensions（Tasks、MCP Apps、ext-auth、Skills over MCP） | 一次 tool 呼叫；2026-07-28 版起無狀態，跨呼叫狀態由 server 發 handle、以一般參數傳遞；server 需要補輸入時回傳 `input_required`（MRTR），client 補完後重送原 request | 工具與資料整合；讓多個 host 與 agent 共用能力 | 版本演進快；tool 一多就佔滿 context；tool poisoning、confused deputy、token passthrough 等風險要靠實作防範；不適合 agent 對 agent 的長任務協作 | 第 13、14、31、33 章 |
| A2A（Agent2Agent） | agent ↔ 另一個不透明的 agent | AgentCard（身分、能力、skills、介面、安全機制、簽章）、Task（server 產生 id、`contextId`、status、artifacts、history）、Message、Artifact、Part；操作包括送訊息、串流、查詢、列出、取消、訂閱 task 與 push 設定 | 有生命週期的 task：`SUBMITTED` → `WORKING` → 終態（完成、失敗、取消、拒絕）；中斷態 `INPUT_REQUIRED`、`AUTH_REQUIRED` | 跨組織、跨框架的長任務委派；需要中途補件或授權 | v0.3 到 v1.0 有大量 breaking change；真正跨公司的互通案例仍少；和「把 agent 包成 MCP tool」的界線常被混淆 | 第 15 章 |
| AG-UI（Agent–User Interaction） | agent 後端 ↔ 前端畫面 | 事件串流：lifecycle（run 開始、結束、錯誤）、文字訊息片段、tool call 事件（含前端執行的 tools）、state 的 snapshot 與 delta、interrupt；以 middleware 承載 A2UI、MCP Apps | 一次 run 內的一連串事件；state 以 snapshot 加 delta 同步；HITL 以 interrupt 表示 | 前端即時顯示進度、共享 state、中途讓使用者確認；讓前端與後端框架解耦 | 部分事件的確切欄位以官方 schema 為準；生成的介面要限制在元件目錄或隔離 iframe 中 | 第 15、37 章 |
| AP2（Agent Payments Protocol） | 使用者 ↔ agent ↔ 商家 ↔ 支付方 | 以可驗證數位憑證組成的 mandate 授權鏈；支援 human-present 與 human-not-present | 授權證明層；可作為 A2A、MCP、UCP 的 extension | 讓商家與支付方驗證「使用者真的授權了這筆」 | 新舊版本的 mandate 名稱不同，實作以最新 spec 為準 | 第 15 章 |
| ACP（Agentic Commerce Protocol） | agent ↔ 商家 | agentic checkout 與 delegated payment 兩份 OpenAPI 規格；商家仍是交易賣方，agent 不經手金流 | 商務流程層：checkout session | agent 與商家完成結帳並傳遞受限付款 token | 仍是 beta | 第 15 章 |
| UCP（Universal Commerce Protocol） | 平台 ↔ 商家 ↔ 支付方 | capabilities（checkout、identity linking、order、payment token exchange）加 extensions；商家發布 profile 供動態探索 | 商務流程層；與傳輸方式無關（REST、MCP、A2A 皆可） | 商家宣告可被 agent 使用的商務能力 | 只有 draft 與版本化文件 | 第 15 章 |
| x402、MPP（Machine Payments Protocol） | client ↔ 付費資源 | HTTP 402 挑戰與回應：server 告知要付多少、怎麼付，client 附上付款證明重送；MPP 另有按量計費的 session 與 subscription | 付款傳輸層：每次 request 付款或 session 計量 | 機器對機器、按次或按量付費的 API | 付款是不易回復的動作，每一筆都要 idempotency key 與稽核 | 第 15 章 |
| Agent Client Protocol（也簡稱 ACP） | 編輯器或 host ↔ coding agent | JSON-RPC over stdio | — | 讓編輯器驅動不同的 coding agent | 縮寫與商務的 ACP 衝突，閱讀資料時要確認指的是哪一個 | 第 15 章 |
| Agent Communication Protocol（IBM，也簡稱 ACP） | agent ↔ agent | REST | — | 公開報導指出已宣布併入 A2A | 未查證 | 第 15 章 |

付款協定的五列可以用第 15 章 15.8 節的三層來記：授權證明（AP2）、商務流程（ACP、UCP）、付款傳輸（x402、MPP），它們可以疊在一起用，不是互相競爭。對 framework 設計者來說，最重要的結論是 tool 層不需要懂每一種付款協定，只要把「需要付款」抽象成一個中斷，由獨立的付款元件以確定性程式檢查授權範圍。

下圖把三個主要協定與付款協定放在同一張系統圖上，標出每條邊用哪個協定：

```text
  使用者的瀏覽器
        │  AG-UI：run 事件串流（文字、tool 進度、state、interrupt）
        ▼
  ┌───────────────────────┐   A2A：task（有生命週期、    ┌───────────────────────┐
  │  你的 agent           │──── 可中斷、產出 artifact）──►│ 其他組織的 agent       │
  │  loop、context、      │                               │ （不透明）             │
  │  approval、付款元件   │                               └───────────────────────┘
  └───┬──────────────┬────┘
      │ MCP：tool    │ 付款：AP2 mandate（授權證明）→ ACP／UCP checkout（商務流程）
      │ 呼叫（短）   │       → 受限 token 或 x402／MPP 的 HTTP 402（付款傳輸）
      ▼              ▼
  ERP、檔案、     商家與支付服務商
  搜尋等 server
```

逐條看這張圖。上方的 AG-UI 邊只負責「把 agent 的一舉一動變成前端事件」，不承擔業務邏輯，前端按鈕觸發的仍然只是「請後端做某件事」的請求。右側的 A2A 邊把對方當成同儕：你只看得到 task 狀態與產出，看不到對方的 prompt 與 tools。左下的 MCP 邊把對方當成能力：短、可列舉、結果一次到齊。右下的付款路徑最特別，它不是單一協定，而是三層疊在一起；agent 永遠只拿到受限、可撤銷的 token，真正的憑證留在支付服務商或獨立的付款元件。一個 agent 同時是 AG-UI 的後端、A2A 的 client 與多個 MCP server 的 client 是很正常的事。

## C.6 機制對照：暫停與恢復在各協定與框架中的名字

第 26 章與第 22 章都指出，暫停與恢復已經成為各家協定與框架的一等原語。名字各不相同，背後都是同一個抽象：**可恢復的 continuation 加上外部輸入**，也就是「把目前進度存起來，等到某個外部事件（補資料、授權、核准、付款）到達後，從同一點繼續」。下表把它們放在一起，方便在 adapter 層統一（第 23、24 章）。

| 所在 | 暫停的表示方式 | 恢復的方式 | 誰保存暫停期間的狀態 | 本書章節 |
|---|---|---|---|---|
| MCP（2026-07-28） | result 帶 `resultType: "input_required"` 與 `inputRequests` | client 補上 `inputResponses` 後重送原 request；跨輪狀態放 `requestState` | client 與 `requestState`（server 不保留 session） | 第 14 章 |
| MCP Tasks extension | server 回傳 task handle | 以 `tasks/get` 查詢、`tasks/update` 補輸入 | server | 第 14 章 |
| A2A | task 進入 `INPUT_REQUIRED` 或 `AUTH_REQUIRED` | client 在同一個 task 上送出補件或授權訊息 | server（task 狀態以 server 為準） | 第 15 章 |
| AG-UI | interrupt 事件 | client 回應 interrupt；新版可重新連上帶有未完成 interrupt 的 thread（版本見 C.9） | agent 後端 | 第 15 章 |
| LangGraph | 節點中呼叫 `interrupt(value)` | `Command(resume=...)` | checkpointer | 第 19、21 章 |
| OpenAI Agents SDK | `needs_approval` 的 tool 使 run 帶著 interruptions 結束 | 序列化的 `RunState` 核准或拒絕後 resume | 你保存的 `RunState` | 第 21 章 |
| Google ADK 2.x | workflow 節點以 `RequestInput` 暫停；tool confirmation | 補上輸入後 resume | SessionService | 第 19、21 章 |
| Claude Agent SDK | permission mode 與 `can_use_tool` callback 決定是否詢問 | callback 回傳允許或拒絕 | 呼叫端 process（以 callback 即時回答；長時間等待的保存方式公開資料未說明） | 第 21、26 章 |
| Mastra | workflow `suspend()`；tool approval | `resume()`；回應 tool approval 時要帶 tool call id | workflow snapshot | 第 21 章 |
| LlamaIndex | `wait_for_event` | 送入對應的 event | 可序列化的 `Context` | 第 21 章 |
| MAF workflows | request／response 形式的人工介入 | 回覆 request 後繼續 | workflow checkpoint | 第 21 章 |
| Temporal | workflow 等待 Signal（或 Update） | 外部送出 Signal | Temporal 服務端的 event history | 第 22 章 |
| Restate | awakeable、durable promise 類原語 | 外部完成 awakeable | Restate server 的 journal | 第 22 章 |
| Inngest | `waitForEvent()` | 送出對應事件 | Inngest | 第 22 章 |

這張表的「誰保存暫停期間的狀態」一欄決定了兩件事。第一是暫停期間能不能不佔用 process：第 26 章要求驗證「使用者三小時後才回來」，如果暫停只靠呼叫端 process 裡的 callback 即時回答（例如以權限 callback 決定能不能使用某個 tool），而沒有把待核准的狀態持久化，長時間的人工核准就需要另外設計，例如先拒絕並把待核准意圖記進自家的核准單，核准後再以 session resume 繼續。第二是 lock-in：狀態存在誰那裡，換框架時就要從誰那裡搬出來。第 21 章的核准單狀態機（PENDING 到 APPROVED、REJECTED、EXPIRED、CANCELLED）應該由你自己擁有，各框架的暫停原語只是它的執行載體。

```text
  統一抽象：resumable continuation ＋ 外部輸入

   agent 執行中 ──► 遇到需要外部輸入的點（補資料／授權／核准／付款）
                      │
                      ▼
               ┌──────────────────────────────────┐
               │ 1. 保存 continuation（誰保存？）  │  checkpointer／RunState／
               │ 2. 對外發出請求（什麼形式？）     │  task 狀態／event history
               │ 3. 釋放 compute，等待             │
               └──────────────┬───────────────────┘
                              │ 外部事件到達（可能數小時、數天後）
                              ▼
               ┌──────────────────────────────────┐
               │ 4. 驗證事件（綁定參數 hash、     │  第 21、33 章的核准規則
               │    是否過期、是否本人）           │
               │ 5. 從同一點恢復，不重做已完成的   │  第 22 章的 idempotency
               │    副作用                         │
               └──────────────────────────────────┘
```

這張圖把表中十幾種名字收斂成五個步驟。前三步是暫停：保存進度、發出請求、釋放資源；不同協定與框架的差別主要在第 1 步由誰保存、第 2 步用什麼形式表示。後兩步是恢復，而它們恰好是框架最少替你做好的部分：第 4 步要檢查外部事件是否對應原本的請求（第 21 章要求核准綁定參數 hash），第 5 步要保證恢復時不重做已完成的副作用（第 22 章的 idempotency key）。在 `loom` 的 adapter 層，把各家原語翻譯成這五步，業務程式就不必知道底下是哪一家。

## C.7 託管 agent 服務與模型 API 速查

託管服務分成兩種（第 26 章 26.7 節）：**託管 harness** 連 agent loop 都在雲端執行；**託管平台積木**不跑你的 loop，而是提供可以分開使用的 runtime、memory、gateway、identity、policy、eval 等服務。下表整理主要的託管選項。產品細節變動很快，具體狀態見 C.9。

| 服務 | 類型 | 核心概念 | 適用 | 限制與注意 | 本書章節 |
|---|---|---|---|---|---|
| Claude Managed Agents | 託管 harness | Agent（模型、system prompt、tools、MCP、skills）、Environment（Anthropic 雲端或自架 sandbox）、Session、Events（SSE 串流、server 端持久化、可中途 steer 或 interrupt）；排程部署 | 需要檔案與 shell 能力的長任務、營運人力少的團隊 | beta；不支援 ZDR 與 HIPAA BAA；session 與事件紀錄在廠商端 | 第 17、22、26、33 章 |
| OpenAI Agents API | 託管 harness（managed Codex harness） | 持久化 session 設定、turns 與 items；自動 compaction、multi-agent orchestration、programmatic tool calling、MCP；sandbox 可為 OpenAI 託管、自架或不使用 | 以 OpenAI 模型為主、想把 loop 與 compaction 外包的團隊 | Agents API session、Agents SDK session、Responses conversation 與 sandbox 是四種不同的資源，不要混用；正式 endpoint 與上線日期未查證 | 第 17、26 章 |
| Amazon Bedrock AgentCore | 平台積木（另含託管 harness） | Harness（每個 session 在隔離 microVM 中執行，可自帶容器，支援多家模型）、Runtime（支援多種框架與 MCP、A2A）、Memory、Gateway（API 與 Lambda 轉成 MCP tools）、Identity、Code Interpreter、Browser、Observability、Evaluations、Optimization、Policy（在 Gateway 攔截每次 tool call）、Registry、Payments | AWS 上的生產 agent；想只外包 identity、gateway 或 runtime 中的一塊 | 各服務各自的 lock-in 要分別評估；Runtime 的 session 長度與 payload 限制未查證 | 第 17、26、33 章 |
| Gemini Enterprise Agent Platform 的 Agent Runtime | 平台積木 | Agent Runtime（託管部署、agent identity、Agent Gateway）、Sessions（以 IAM Conditions 控管）、Memory Bank、Code Execution、Example Store、Evaluation | Google Cloud 企業；ADK 為主的團隊 | 文件頁面原為 Vertex AI Agent Engine，是否為正式更名頁面未明說 | 第 26、33 章 |
| Gemini Interactions API 的 agents | 託管 agent（由模型 API 直接呼叫） | 以 Interactions API 呼叫 Deep Research、Antigravity 等 agent；background 模式執行 | 想直接使用廠商做好的 research 或 coding agent | 多為 preview；Deep Research 必須以 background 模式執行 | 第 22 章 |
| Microsoft Foundry（Agent Service、hosted agents） | 平台（MAF 的部署目標） | 託管執行 MAF 等框架寫成的 agent | Azure 企業環境 | 部分查證，細節本書未查證 | 第 26 章 |

託管服務的選擇與框架選擇不是二選一：常見的組合是「平台積木加自家框架」，例如 loop 跑在自己的框架上，只用平台的 identity 服務代管 OAuth token、用 gateway 統一管理 tools。評估託管服務時，第 26 章要求特別測兩件事：出事時能拿到什麼（完整事件紀錄、送給模型的 context），以及要離開時能帶走什麼（session 能不能匯出、格式是什麼）。

模型供應商的低階 API 也在 2026 年同時轉向「server 端狀態、以 item 或 step 表示歷史、支援 background 執行」。這一層是第 25 章 model adapter 要隔離的對象：

| API | 歷史與狀態的表示 | tool 定義的 schema 欄位 | 與 agent 相關的重點 | 本書章節 |
|---|---|---|---|---|
| OpenAI Responses（加 Conversations） | items；可手動傳歷史、以前一個 response id 串接，或用 Conversations 管理 | `parameters`（strict 模式有額外限制） | Assistants API 已停止服務，對應關係為 Threads → Conversations、Runs → Responses；有 remote `mcp` tool | 第 3、7、25 章 |
| Anthropic Messages | messages 與 content blocks（`tool_use`、`tool_result`） | `input_schema`（可設 `strict`） | server tools（web search、code execution、tool search 等）；MCP connector；SDK 的 Tool Runner（beta） | 第 3、13、25 章 |
| Gemini Interactions | steps（thought、function call、function result、model output、user input）；以前一個 interaction id 保存 server 端狀態 | `parameters`；`validated` 模式保證符合 schema | 只有對話歷史會延續，tools 與 system instruction 每次都要重傳；thought signatures 要原樣回傳；遠端 MCP 官方表示即將支援 | 第 3、25 章 |

三家共同的設計教訓是：adapter 要保留 provider 的不透明欄位（推理內容的加密欄位、thought signatures、thinking blocks），否則多輪 tool use 會壞掉（第 25 章）。schema 欄位名稱的差異（`parameters` 與 `input_schema`，MCP 則是 `inputSchema`）在第 26 章 26.11 節的 exporter 中有完整示範。

## C.8 Durable execution 引擎速查

第 22 章說明了為什麼長時間 agent 需要 durable execution：agent loop 是確定性的協調程式，每次模型呼叫與 tool 呼叫是非確定性的外部呼叫，把後者的結果記錄下來，process 掛掉後就能重播恢復而不重打模型、不重做副作用。下表沿用第 22 章 22.9 節的對照，並補上適用場景與限制。

| 引擎 | 協調程式碼 | 外部呼叫的單位 | 進度紀錄與恢復 | 部署形態 | 適用 | 限制與注意 | 本書章節 |
|---|---|---|---|---|---|---|---|
| Temporal | Workflow | Activity | Event History，重播恢復；Signal、Update、Timer | 獨立 cluster（或託管雲端服務）加上你的 worker | 跨語言、跨團隊的大規模編排；需要完整可觀測性的 workflow 歷史 | 要營運 cluster；團隊要理解 determinism 限制；大型 context 要外存（Claim Check） | 第 22 章 |
| Restate | 以 handler 撰寫的 service | `ctx.run()` 包住的 step | journal 重播；以 key 區分的持久 session 內建並發控制；awakeable 類原語 | 單一 server，以 HTTP 推送呼叫你的服務 | serverless 部署；想要低延遲 journal | 部分原語名稱（例如 Virtual Objects）本書未在 AI 文件頁面確認 | 第 22 章 |
| Inngest（含 AgentKit） | event 驅動的 function | `step.run()` | 平台保存 step 結果；`waitForEvent()` 等待外部事件 | serverless-first，以 HTTP 呼叫你的 function | 需要 concurrency、throttle、debounce 等流量控制 | AgentKit 為 TS；`step.ai` 相關 API 未查證 | 第 22 章 |
| DBOS | `@DBOS.workflow` | `@DBOS.step` | Postgres 中的 workflow 與 step 狀態 | 函式庫，只需要 Postgres | 已有 Postgres、不想多一個 orchestrator | 各 agent 框架的整合清單未查證 | 第 22 章 |
| Absurd | 以 Postgres 為基礎的 durable execution | — | Postgres | 函式庫 | Pydantic AI 使用者（已內建整合） | 生態較新，細節本書未展開 | 第 22 章 |
| LangGraph checkpointer | graph | node（以快照為單位） | 每個 super-step 一份快照；載入快照恢復 | 函式庫，搭配部署平台 | 已使用 LangGraph 的 agent | 只負責存取 state；worker 排程、持久化計時器、跨服務重試要靠部署平台或外部系統 | 第 19、22 章 |
| 框架內建的 durability | 依框架 | 依框架 | OpenAI Agents SDK `RunState`、ADK session event log、MAF workflow checkpoint、Mastra workflow snapshot 加 durable streams、CrewAI `@persist`、LlamaIndex `Context` 序列化 | 函式庫 | 任務只有幾分鐘、不需要跨部署等待 | 多數不處理排程與計時器；恢復時是否重做最後一步要實測 | 第 22、26 章 |

```text
  需要 durable execution 嗎？（第 22 章 22.9 節的三個問題）

  (1) 任務多長？要不要等人？
        │ 幾分鐘、不等人 ──► 框架內建的 session 持久化或快照就夠
        │ 跨天、等核准、要跨部署存活
        ▼
  (2) 團隊願意營運多少基礎設施？
        │ 已有 Postgres、不想多一個服務 ──► 函式庫型：DBOS、Absurd
        │ serverless、以 HTTP 呼叫     ──► Restate、Inngest
        │ 跨語言、跨團隊的大規模編排   ──► Temporal（自營或託管）
        ▼
  (3) 現有 agent 框架有官方整合嗎？
        └─► 優先用整合：把每次 model call 與 tool call 自動包成 activity／step，
            agent 程式碼不必改寫；無論選哪個，destructive tool 都要有 idempotency key
```

這張流程圖是第 22 章選型三問的濃縮版。第 (1) 步先排除不需要 durable 引擎的情況：很多客服對話只有幾分鐘，框架內建的持久化就夠了，硬上 durable 引擎只會增加營運負擔。第 (2) 步依基礎設施的承受度選擇部署形態，而不是依功能清單，因為主流引擎在核心概念上大致相同。第 (3) 步提醒先找官方整合，整合的形式通常是把框架的每次模型與 tool 呼叫自動變成 activity；但不論哪一種整合，都不會替你推導 idempotency key，這仍然是 harness 依業務意圖負責的事（第 5、22 章）。

## C.9 2026 現況：版本、狀態與查證日期

> [!note] 2026 現況
> 以下整理截至 2026 年 10 月，依本書撰寫時的技術 survey；「已查證」者於 2026-10-02 讀取官方文件、GitHub releases 或官方網站確認。GitHub releases 頁面多半只顯示日與月，年份依上下文推定為 2026。發版頻率很高，版本號在你讀到時多半已經前進；寫進正式文件前請以官方來源重新確認。

**SDK 與框架**

| 項目 | 截至 2026-10 的版本與狀態 | 近期值得注意的變化 | 查證狀態 | 查證日 |
|---|---|---|---|---|
| OpenAI Agents SDK | Python v0.23.0（2026-10），仍是 0.x | 預設模型在 v0.20.0 調整；同時支援 MCP Python SDK v1 與 v2；加入 `agents.testing`、sandbox agents（Docker、Modal 等）、scoped tool approvals | 已查證（版本）；部分查證（class 名稱） | 2026-10-02 |
| Claude Agent SDK | Python v0.2.163（2026-09-30，內含 CLI 2.1.286），幾乎每天發版 | `verbatim_prompts`（防止不可信 prompt 觸發讀檔或指令）；resume 時保持 system prompt 不變以提升 cache 命中 | 已查證（版本與能力）；部分查證（API 名稱） | 2026-10-02 |
| Google ADK | Python v2.11.0（2026-10-01），1.x 仍有安全 backport；TypeScript 2.0 GA 並支援 graph；官方網站已更換網域 | graph workflow（可從 YAML 載入）、`RequestInput`、`FallbackModel`、native A2A task mode、MCP SDK 2.x | 已查證 | 2026-10-02 |
| LangGraph／LangChain | langgraph 1.2.12（2026-09-21）；langchain 1.4.3、langchain-core 1.6.6；langgraph-checkpoint 4.2.0、postgres 3.1.2、sqlite 3.1.1 | `interrupt()` 新增 `response_schema`；`add_node` 新增 `trace_policy` | 已查證（版本）；未查證（API 細節） | 2026-10-02 |
| Microsoft Agent Framework | .NET 1.23.0（2026-10-01）、Python 1.19.0（2026-09-18），約每週發版；Go 為 public preview | Harness Agent（planning、compaction、檔案與記憶、tool approval）；CodeAct；MCP 長任務遷到 Tasks extension；AG-UI 套件 1.0.0 | 已查證（版本）；部分查證（AutoGen 與 Semantic Kernel 是否正式標示維護模式未查證） | 2026-10-02 |
| CrewAI | 1.15.23（2026-09-28） | conversational flows 轉為 stable；`llm_overlay` 依角色路由模型；checkpoint telemetry | 已查證 | 2026-10-02 |
| AG2 | v1.0.0（2026-07-27）為全新的 protocol-driven 框架，官方說明不是 drop-in 升級；舊架構移到 ag2-classic（維護模式）；最新 v1.1.1（2026-09-29） | signed cards、gRPC TLS、AG-UI mid-run input、tool search 與 deferred loading | 已查證 | 2026-10-02 |
| Pydantic AI | v2.53.0（2026-10-01），v1 只做安全 backport | workspaces 與 sandbox；`TemporalDurability`、`AbsurdDurability`；一項 `ConcurrencyLimitedModel` 的安全修正 | 已查證（版本）；部分查證（核心 API 名稱） | 2026-10-02 |
| DSPy | 3.4.0（2026-09-25），定位為 LM 轉換版 | 舊的 `messages=` 呼叫與自訂 `BaseLM.forward()` 預計在 3.5 移除；GEPA、`dspy.RLM` 取代 deprecated 的 CodeAct；`LocalInterpreter` 明說不是 sandbox | 已查證 | 2026-10-02 |
| Strands Agents | Python 1.57.2（2026-10-01）、TypeScript 1.19.0（需 Node 22 以上） | bidirectional streaming API graduated；`a2a_client` vended tool；`mcp` 套件換成 MCP client 2.0（breaking） | 已查證 | 2026-10-02 |
| Mastra | `@mastra/core` 1.72.0（2026-09-29），幾乎每週一個 minor | `@mastra/mcp` 2.0.0 只支援 MCP 2026-07-28 版；tool approval 需帶 tool call id；Inngest runner 新增 `retries` | 已查證 | 2026-10-02 |
| LlamaIndex | core v0.14.25（2026-09-21）；Workflows 拆成獨立套件（需 `llama-index-workflows` 2.14.0 以上） | AgentWorkflow 的 structured output 與 tool 重試修正；AG-UI 整合 | 已查證 | 2026-10-02 |
| smolagents | v1.26.0（2026-05-29），之後約四個月沒有新版 | v1.26 移除遠端 WasmExecutor；文件強調必須 sandbox | 已查證 | 2026-10-02 |

**協定**

| 協定 | 截至 2026-10 的版本與狀態 | 治理 | 查證狀態 | 查證日 |
|---|---|---|---|---|
| MCP | 2026-07-28 為目前版本（本書以此為「目前版本」）：無狀態化、`server/discover`、MRTR、Tasks 移為官方 extension；Roots、Sampling、Logging、HTTP+SSE、Dynamic Client Registration 被 deprecated；官方 MCP Registry 仍標示 preview | Linux Foundation 旗下的 Agentic AI Foundation（AAIF）；SEP 流程；deprecated 功能原則上至少保留 12 個月 | 已查證（規格與 changelog）；部分查證（移交 AAIF 的確切日期與細節） | 2026-10-02 |
| A2A | v1.0.0（2026-03-12）、v1.0.1（2026-05-26，HTTP binding 改用 `application/a2a+json`）；v1.0 拆成 data model、abstract operations、bindings 三層，新增 `ListTasks` | Linux Foundation；spec 頁面標示將加入 AAIF | 已查證（版本與 spec）；未查證（2025-04 由 Google 發起的起源細節） | 2026-10-02 |
| AG-UI | 1.0.0（2026-09-17，同步發布 TS、Python、.NET）、1.0.1（2026-09-29，可重新連上帶有未完成 interrupt 的 thread）；0.x 名稱保留為 deprecated alias | CopilotKit 發起的開源社群 | 已查證（版本）；部分查證（部分事件名稱與欄位） | 2026-10-02 |
| AP2 | v0.2；以 Checkout Mandate 與 Payment Mandate（各分 Open／Closed）描述授權 | 由 Google 發起，已捐給 FIDO Alliance | 已查證（v0.1 時期 Intent／Cart／Payment 的說法未查證） | 2026-10-02 |
| ACP（Agentic Commerce Protocol） | beta；最新穩定版 2026-04-17（cart、feed、orders、authentication、MCP） | OpenAI 與 Stripe 為 Founding Maintainers | 已查證 | 2026-10-02 |
| UCP | 有 draft 與版本化文件，GitHub 上沒有正式 release | UCP org（由 Google 主導發起，未查證） | 已查證（文件內容） | 2026-10-02 |
| x402 | 有多語言 SDK；header 為 `PAYMENT-REQUIRED`、`PAYMENT-SIGNATURE`、`PAYMENT-RESPONSE` | 由 Coinbase 發起，已移交 x402 Foundation | 已查證 | 2026-10-02 |
| MPP | 有 TS、Python、Rust、Go、Ruby SDK；charge、session、subscription；可與 x402 互通 | Tempo 與 Stripe 維護 SDK（發起方頁面未寫明） | 已查證 | 2026-10-02 |

**託管服務與模型 API**

| 項目 | 截至 2026-10 的狀態 | 查證狀態 | 查證日 |
|---|---|---|---|
| Claude Managed Agents | beta（需 `managed-agents-2026-04-01` beta header）；不支援 ZDR 與 HIPAA BAA；可在 Claude Platform on AWS 使用；MCP tunnels 等為 research preview | 已查證 | 2026-10-02 |
| OpenAI Agents API | managed Codex harness；四種資源（Agents API session、Agents SDK session、Responses conversation、sandbox）要分清楚 | 已查證（定位與能力）；未查證（正式 endpoint 與上線日期） | 2026-10-02 |
| OpenAI Assistants API | 已於 2026-08-26 停止服務，改用 Responses 與 Conversations | 已查證 | 2026-10-02 |
| OpenAI Agent Builder | 視覺化 canvas 宣布預計 2026-11-30 關閉；ChatKit 保留 | 已查證 | 2026-10-02 |
| Amazon Bedrock AgentCore | Harness、Runtime、Memory、Gateway、Identity、Code Interpreter、Browser、Observability、Payments（x402 與 MPP、支出上限）、Evaluations、Optimization、Policy、Registry | 已查證（服務清單）；未查證（Runtime session 長度上限；Policy 語言名稱與 Cedar 的關係依官方頁面用語） | 2026-10-02 |
| Gemini Enterprise Agent Platform 的 Agent Runtime | 原 Vertex AI Agent Engine 文件頁面改用此名稱；支援 ADK、LangChain、LangGraph、LlamaIndex、AG2、A2A 與自訂框架；合規包括 VPC-SC、CMEK、data residency（Example Store 除外）、HIPAA | 已查證（頁面內容）；更名關係為推論 | 2026-10-02 |
| Gemini Interactions API | 2026-06 GA，官方建議新專案使用，`generateContent` 標為 legacy（仍完整支援）；可呼叫 Deep Research 與 Antigravity 等 preview agents；遠端 MCP 尚未支援 | 已查證 | 2026-10-02 |
| Microsoft Foundry | MAF 的部署目標（Agent Service、hosted agents） | 部分查證 | 2026-10-02 |

**Durable execution**

| 項目 | 截至 2026-10 的狀態 | 查證狀態 | 查證日 |
|---|---|---|---|
| Temporal | AI Cookbook 有 OpenAI Responses、OpenAI Agents SDK、Anthropic agentic loop、Vercel AI SDK、Google ADK、Strands 等範例，以及 Signal 實作人工核准、Claim Check 外存大型 payload | 已查證（cookbook）；未查證（與 OpenAI Agents SDK 的整合目前是正式版或預覽版） | 2026-10-02 |
| Restate | AI 文件列出 Vercel AI SDK、OpenAI Agents SDK、Google ADK、Pydantic AI、LangChain 整合；有含核准、subagent、排程的參考實作 | 已查證 | 2026-10-02 |
| Inngest AgentKit | Agents、Networks、State、Routers、`createTool`；從 v0.9.0 起要另外安裝 `inngest` | 部分查證 | 2026-10-02 |
| DBOS | Python、TS、Go、Java 函式庫；durable queues、排程 | 部分查證（語言與功能已查證；各 agent 框架整合未查證） | 2026-10-02 |
| Absurd | 以 Postgres 為基礎；Pydantic AI 已整合 | 已查證（整合存在） | 2026-10-02 |

**2026 年影響選型的事件**

```text
 2026-03-12  A2A v1.0.0（大量 breaking change）
 2026-05-26  A2A v1.0.1
 2026-05-29  smolagents v1.26.0（之後數月無新版）
 2026-06     Gemini Interactions API GA；generateContent 標為 legacy
 2026-07-27  AG2 v1.0.0（全新框架，舊架構移到 ag2-classic）
 2026-07-28  MCP 新版規格：無狀態化、MRTR、Tasks 移為 extension
 2026-08～09 OpenAI Agents SDK、ADK、Strands、Mastra 等發版支援 MCP SDK 2.x，部分為 breaking
 2026-08-26  OpenAI Assistants API 停止服務
 2026-09-17  AG-UI 1.0.0
 2026-11-30  OpenAI Agent Builder（視覺化 canvas）預計關閉
```

這條時間線揭露的模式比任何一個版本號都有用（第 26 章 26.10 節）。協定改版會連動框架升級：MCP 新版發布後一兩個月內，多數框架都發了支援新版 SDK 的版本，其中部分是 breaking change。平台 API 停止服務是狀態 lock-in 的真實代價：Assistants API 的使用者必須把 threads 與 runs 搬到新的資源模型。重寫與品牌分裂代表遷移風險：AG2 v1 不能直接升級。把這些訊號放進第 26 章「生態」與「lock-in」兩個維度打分，並在決策紀錄裡寫下重新檢視的時間點。

## C.10 使用前必須再核對的項目

下列項目在本書撰寫時未能從官方來源確認，或只確認了一部分。若你的設計文件、選型報告或對外說明依賴其中任何一項，請先查當時的官方文件。

| 類別 | 未查證或部分查證的內容 | 為什麼重要 |
|---|---|---|
| MCP | 移交 AAIF 的確切日期與 AAIF 的成員和專案清單；2025 年以前各版本的細節 | 治理與版本歷史常被寫進合規或採購文件 |
| A2A | 由 Google 於 2025 年 4 月發起、移交 Linux Foundation 的時間 | 只影響背景敘述，不影響實作 |
| AG-UI | step 與 reasoning 事件的確切名稱、終態事件中 `outcome` 的取值 | 前端解析事件時欄位名稱必須正確 |
| AP2 | v0.1 的 Intent／Cart／Payment mandate 與 v0.2 的 Checkout／Payment（Open／Closed）如何對應 | 舊資料與新 spec 的名詞不同，容易實作錯誤 |
| OpenAI | Responses 的 hosted tools 完整清單、custom tools 的參數名稱；Agents API 的正式 endpoint 與上線日期 | 寫 adapter 時不能猜參數名稱 |
| Anthropic | structured outputs、programmatic tool calling 的確切參數與 beta header | 同上 |
| Microsoft | MAF 的 GA 日期；AutoGen 與 Semantic Kernel 是否正式標示為維護模式；workflow API 的類別名稱 | 影響長期維護的判斷 |
| AgentCore | Runtime 的 session 時長與 payload 限制；Policy 語言名稱與 Cedar 的關係 | 長任務與 policy 設計的硬性限制 |
| Durable execution | Temporal 與 OpenAI Agents SDK 的整合是正式版或預覽版；DBOS 支援的 agent 框架清單；Inngest 的 `step.ai` 相關 API | 影響「有沒有官方整合」這個選型問題 |
| 框架 API 細節 | LangGraph、Pydantic AI、Strands、LlamaIndex 等標示「部分查證」的 class 與函式名稱；AG2 v1 的狀態管理方式 | 範例程式與遷移估算要依實際 API |
| 其他框架 | Vercel AI SDK、Cloudflare Agents SDK、Agno、Haystack、Letta、Firebase Genkit、goose 的現況 | 本書只寫了定位，未查證版本與功能 |

核對時有一個實用的順序：先讀該專案的 release notes 中標示 breaking change 的段落，再讀規格或 API reference，最後才看部落格與教學文章。release notes 告訴你「什麼變了」，規格告訴你「現在是什麼」，二手文章常常落後一兩個版本。核對完成後，把結果與日期寫進你自己的決策紀錄，讓下一次重新檢視時有依據；這和第 26 章 26.8 節「把決策寫成可在一季後重新檢視的紀錄」是同一件事。
