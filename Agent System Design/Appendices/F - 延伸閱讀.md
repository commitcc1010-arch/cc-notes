# 附錄 F　延伸閱讀

> [!abstract] 本附錄地圖
> **用途**：把全書各章「延伸閱讀」節與 2026-10 survey 中查證過的來源合併、去重，依主題整理成一份書單。每一項寫名稱、作者或機構、年份、一句話說明為什麼值得讀，以及它對應本書哪幾章。
>
> **怎麼查**：
> - 不知道從哪裡開始：先看 F.1 的建議閱讀順序（入門 → 實作 → 進階）。
> - 正在讀某一章：用 F.2–F.13 的「對應章節」欄反查，或直接看該章結尾的延伸閱讀。
> - 要確認某份文件的版本或可信度：看 F.14 的收錄原則與查證說明。
>
> **約定**：全附錄不放 URL，請用名稱與機構搜尋。標了「標題待核對」的項目，代表文件確實存在，但本書無法確認確切標題，所以用描述性名稱代替。官方文件與規格會持續改版，年份欄寫「持續更新」者，以截至 2026 年 10 月的版本為準。

## F.1 建議閱讀順序

這份書單有一百多項，沒有人需要全部讀完。下面的路線把它們分成三個階段：入門階段建立「agent 是什麼、什麼時候該用」的判斷力；實作階段對應本書 Part 1–5，讀的是能直接改變程式碼的設計指南與官方文件；進階階段對應 Part 6–10，處理評估、安全、治理與大規模營運。每個階段結束時，都應該能回答一個具體問題，答不出來就回頭補，不要急著往下讀。

```text
 入門（約 1 週）            實作（約 3–4 週）               進階（持續）
 ┌───────────────┐        ┌────────────────────┐         ┌──────────────────────┐
 │ 什麼是 agent   │        │ tools 與 context    │         │ eval 與 benchmarks    │
 │ 何時不該用     │ ─────► │ 長任務與 memory     │ ──────► │ 威脅模型與防禦設計    │
 │ 五種 workflow  │        │ 協定（MCP、A2A）    │         │ 治理、法規、production │
 └───────────────┘        │ orchestration       │         │ 案例與訓練方法        │
   檢查：能判斷一個        └────────────────────┘         └──────────────────────┘
   任務該用 workflow         檢查：能從零寫出有             檢查：能為自己的 agent
   還是 agent               compaction 與核准的 agent       寫出 eval 與 threat model
```

這張圖的讀法是由左到右：入門階段只讀三到五篇長文，目標是建立共同語彙，例如 workflow 與 agent 的差異、augmented LLM、agent-computer interface。實作階段的閱讀量最大，建議和本書對應章節的「動手做」交錯進行，讀一篇就改一次自己的 loop。進階階段沒有終點，因為 benchmark、規格與法規都在改版，重點是養成「看到新東西先問它解決哪個舊問題」的習慣（第 46 章）。

| 階段 | 先讀 | 再讀 | 讀完應能做到 | 對應章節 |
|---|---|---|---|---|
| 入門 | Anthropic〈Building effective agents〉 | OpenAI〈A practical guide to building agents〉；HumanLayer〈12-Factor Agents〉 | 說清楚單次呼叫、workflow、agent 的差別，並用「開放、可驗證、可回復」三問判斷任務 | 第 1、2、18 章 |
| 入門 | Anthropic〈Effective context engineering for AI agents〉 | Yao et al.〈ReAct〉 | 解釋 context 為什麼是稀缺資源，以及 loop 每一步在 context 裡留下什麼 | 第 3、4、9 章 |
| 實作 | Anthropic〈Writing effective tools for agents — with agents〉 | Yang et al.〈SWE-agent〉；MCP 規格 Tools 章節 | 重構一組 tool 的命名、描述、回傳與錯誤訊息 | 第 5、13、14 章 |
| 實作 | Manus〈Context Engineering for AI Agents: Lessons from Building Manus〉 | Anthropic〈Effective harnesses for long-running agents〉；Chroma〈Context Rot〉 | 設計 cache-friendly 的 context 版面與 compaction 策略 | 第 9、10 章 |
| 實作 | Anthropic〈How we built our multi-agent research system〉 | Cognition〈Don't Build Multi-Agents〉 | 用 context 共享需求判斷是否該拆成 multi-agent | 第 20、40 章 |
| 實作 | Anthropic〈Scaling Managed Agents〉 | Temporal、Restate、DBOS 的 AI agent 文件 | 把 session log 與 context window 分開，做出可恢復的 runner | 第 10、22、36 章 |
| 進階 | Anthropic〈Demystifying evals for AI agents〉 | Yao et al.〈τ-bench〉；Evan Miller〈Adding Error Bars to Evals〉 | 建立從真實失敗出發的 eval set，並用 pass^k 與信賴區間比較版本 | 第 27、28 章 |
| 進階 | Simon Willison〈The lethal trifecta for AI agents〉 | Beurer-Kellner et al.〈Design Patterns for Securing LLM Agents against Prompt Injections〉；Anthropic〈How we contain Claude across products〉 | 對自己的 agent 做 threat modeling，並把防線放在環境層 | 第 31、32 章 |
| 進階 | Cemri et al.〈Why Do Multi-Agent LLM Systems Fail?〉 | NIST AI RMF；OWASP Agentic Top 10 | 寫出 failure taxonomy、SLO 與內部治理流程 | 第 34、38 章 |

> [!tip] 先讀原典，再讀二手整理
> 本附錄刻意偏重一手來源：規格、論文、建造者本人寫的 engineering blog。社群上的摘要文常把「某產品在某時間點的做法」寫成通則；讀原典時順手記下文章日期與當時的模型世代，才能判斷其中哪些建議已經被新模型淘汰（第 30 章「harness 隨模型升級而簡化」）。

## F.2 設計指南

這一類是「建造者寫給建造者」的總論，回答的是方向問題：該不該用 agent、該用多少抽象、哪些地方值得花力氣。它們之間的觀點大致一致（從簡單開始、tool 設計比 prompt 花俏重要、確定性程式碼包住 LLM），但各有側重，交叉閱讀最能看出哪些是共識、哪些是單一廠商的偏好。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Building effective agents〉 | Anthropic Engineering Blog | 2024 | 定義 workflow 與 agent 的差異、五種 workflow pattern 與 ACI 概念，是本書第 1、18 章的起點；附錄〈Prompt engineering your tools〉也是 tool 設計的入門 | 第 1、2、4、5、18、19、23、26、35、37、46 章 |
| 〈A practical guide to building agents〉 | OpenAI | 2025 | 以 model、tools、instructions 三要素拆解 agent，並給出「先用最強模型建 baseline 再換小模型」與分層 guardrails 的實務建議 | 第 1、2、4、5、6、18、20、21、26、35、38、41、42 章 |
| 〈Agents〉whitepaper | Google（Wiesinger et al.） | 2024 | 從 cognitive architecture 角度看 agent，把 tools 分成 extensions、functions、data stores，適合對照不同廠商的心智模型 | 第 1、2 章 |
| 〈Agents Companion〉whitepaper | Google | 2025 | 前一篇的續作，延伸到 AgentOps、trajectory 評估與 multi-agent | 第 2、27 章 |
| 〈12-Factor Agents〉 | HumanLayer（Dex Horthy），GitHub | 2025 | 十二條原則把 production agent 描述成「大部分是確定性軟體，在關鍵點撒上 LLM」，其中 Own your context window、Make your agent a stateless reducer 直接對應本書的 context 與 durable 設計 | 第 1、2、3、4、6、7、18、19、21、22、26、35 章 |
| 〈Effective context engineering for AI agents〉 | Anthropic Engineering Blog | 2025 | 把 prompt engineering 擴大成「管理整個 context 的有限注意力」，提出 just-in-time 載入與 compaction 的原則 | 第 1、2、3、5、6、9、10、11、12、20、40 章 |
| 〈Context Engineering for AI Agents: Lessons from Building Manus〉 | Manus Blog（Yichao "Peak" Ji） | 2025 | 從真實產品歸納六條 context 規則，例如 KV-cache 命中率優先、mask 而不移除 tool、檔案系統當 context、保留錯誤紀錄 | 第 3、6、9、10、13、30、41 章 |
| 〈The Bitter Lesson〉 | Rich Sutton（個人網站） | 2019 | 指出手工加入的領域知識長期會被隨算力擴展的通用方法超越，是「harness 元件隨模型升級而過時」的思想背景 | 第 46 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，上表的 OpenAI 指南已由 survey 讀過前半並核對；Anthropic〈Building effective agents〉與 Google whitepaper 的內容摘要依知識撰寫、未經網路查證（日期已核對）。Google 的 agent whitepaper 之後還有其他系列文章，最新一篇請以 Google 官方公告為準。

## F.3 Agent loop 與推理

這一類是 agent loop 的學術根源與它的變形：ReAct 把「想」和「做」交錯，ReWOO 與 plan-and-execute 把規劃提前，Reflexion 與 Self-Refine 加入自我批評，LATS 把它推成樹搜尋。讀這些論文時要記得，它們大多是在推理模型普及前發表的，有些技巧已經被模型內建的 thinking 吸收（第 8 章「reasoning models 讓哪些 pattern 過時」）。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈ReAct: Synergizing Reasoning and Acting in Language Models〉 | Yao et al.（ICLR） | 2023 | 現代 tool-calling loop 的概念原型：推理、行動、觀察交錯進行 | 第 1、4、8 章 |
| 〈ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models〉 | Xu et al. | 2023 | 先規劃完整步驟再執行，示範如何減少重複讀入觀察結果的 token 成本 | 第 8 章 |
| 〈Reflexion: Language Agents with Verbal Reinforcement Learning〉 | Shinn et al.（NeurIPS） | 2023 | 用文字形式的回饋當作跨嘗試的記憶，是 reflection 類 pattern 的代表 | 第 8 章 |
| 〈Self-Refine: Iterative Refinement with Self-Feedback〉 | Madaan et al.（NeurIPS） | 2023 | evaluator-optimizer 迴圈的早期實證，適合對照第 18 章的實作 | 第 8、18 章 |
| 〈Large Language Models Cannot Self-Correct Reasoning Yet〉 | Huang et al.（ICLR） | 2024 | 指出沒有外部訊號時自我修正常常無效，是「verifier 決定上限」的反面證據 | 第 8、27 章 |
| 〈Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models〉 | Zhou et al.（ICML） | 2024 | LATS 把 Monte Carlo tree search 引入 agent，說明 search 只有在有可靠評分時才划算 | 第 8 章 |
| 〈Self-Consistency Improves Chain of Thought Reasoning in Language Models〉 | Wang et al.（ICLR） | 2023 | 多次取樣再投票的理論基礎，對應 parallelization 中的 voting | 第 18 章 |
| 〈Improving Factuality and Reasoning in Language Models through Multiagent Debate〉 | Du et al. | 2023 | debate 型 multi-agent 的代表研究，可用來評估「多個模型互相辯論」的成本與收益 | 第 20 章 |
| 〈DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning〉 | DeepSeek-AI | 2025 | 公開說明以可驗證 reward 訓練推理能力的方法，幫助理解推理模型為什麼改變 agent 設計 | 第 3、8、30 章 |
| 〈Harness design for long-running application development〉 | Anthropic Engineering Blog | 2026 | 以長時間開發任務為例，說明每個 harness 元件都編碼了某代模型的弱點，換模型時要逐一拿掉重測 | 第 8、10、18、30 章 |

## F.4 Tools 與 context

tool 是模型的 API，context 是模型的工作記憶，兩者決定了 agent 的大部分品質。這一類資料的共同主題是「為模型而不是為人設計介面」：名稱與描述要讓模型選得對，回傳要短且可行動，context 要穩定前綴、按需載入。後半段收錄 code-as-action 的資料，因為它正在改變大量工具的使用方式（第 13 章）。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Writing effective tools for agents — with agents〉 | Anthropic Engineering Blog | 2025 | 用 eval 驅動 tool 設計，示範如何讓 agent 協助分析 transcript 並改寫 tool 描述 | 第 4、5、13、30 章 |
| 〈SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering〉 | Yang et al.（NeurIPS） | 2024 | 提出 ACI 一詞，並用實驗證明介面設計（檔案檢視、編輯指令）對 coding agent 的影響 | 第 5、39 章 |
| 〈Introducing advanced tool use on the Claude Developer Platform〉 | Anthropic Engineering Blog | 2025 | 介紹 tool search、deferred loading 與 programmatic tool calling，是大量工具問題的一手資料 | 第 13 章 |
| 〈Code execution with MCP: Building more efficient agents〉 | Anthropic Engineering Blog | 2025 | 讓 agent 以程式碼呼叫 MCP tools，說明中間結果不進 context 如何同時省 token 與保護資料 | 第 13、14、17 章 |
| 〈Code Mode: the better way to use MCP〉 | Cloudflare Blog | 2025 | 從另一家廠商角度論證「把 tools 暴露成程式 API」比逐次 tool call 更適合模型 | 第 13 章 |
| 〈Executable Code Actions Elicit Better LLM Agents〉 | Wang et al.（ICML，CodeAct） | 2024 | code-as-action 的代表論文，比較以 Python 程式與 JSON 作為動作空間的差異 | 第 7、13 章 |
| 〈Context Rot: How Increasing Input Tokens Impacts LLM Performance〉 | Chroma Research | 2025 | 以系統性實驗說明輸入越長、表現越不穩定，是 context 預算觀念的實證依據 | 第 9、10、34 章 |
| 〈Lost in the Middle: How Language Models Use Long Contexts〉 | Liu et al.（TACL） | 2024 | 證明資訊放在長 context 中段時最容易被忽略，影響檢索結果的排列策略 | 第 9、11 章 |
| 〈How Long Contexts Fail〉 | Drew Breunig（個人部落格） | 2025 | 把長 context 的失敗歸納成幾種可辨識的類型，適合拿來對照自己的 trace | 第 9 章 |
| 〈Improved token efficiency for longer agent runs〉 | Cursor Blog | 2026 | 真實產品的 harness 瘦身紀錄：縮短 system prompt、低用量 tool 改按需載入，品質不變而 token 下降 | 第 6、9、39 章 |
| 〈Effective harnesses for long-running agents〉 | Anthropic Engineering Blog | 2025 | 用 initializer agent、進度檔與 feature list 讓跨 session 的長任務能接續，是第 10 章進度檔設計的原型 | 第 9、10、22 章 |
| 〈The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions〉 | Wallace et al.（arXiv） | 2024 | 說明 system、user、tool 輸出之間的優先順序如何在訓練中建立，以及它的限制 | 第 6、31 章 |
| 〈Model Spec〉 | OpenAI | 2024 起，持續更新 | 公開描述模型應如何處理不同來源指令的衝突，可作為設計 system prompt 規則時的參照 | 第 6 章 |
| Prompt engineering 各章（含 XML 標籤與提示最佳實務） | Anthropic Claude 開發者文件 | 持續更新 | 官方的 prompt 撰寫指引，適合在寫 system prompt 時逐項對照 | 第 6 章 |
| Prompt caching、Context editing、Extended thinking、Effort、Tool use、Errors 各章 | Anthropic Claude 開發者文件 | 持續更新 | prompt caching 計價、thinking 與 effort 控制、tool use 格式的權威說明 | 第 3、9、25 章 |
| Responses API、Function calling、Structured Outputs、Error codes | OpenAI 開發者文件 | 持續更新 | OpenAI 端 tool calling 與 structured outputs 的介面定義，寫 provider adapter 時必讀 | 第 3、7、25 章 |
| Interactions API 與 Function calling | Google Gemini API 文件 | 持續更新 | Gemini 端的 tool 呼叫與互動模型，與前兩家對照可看出 adapter 要處理的差異 | 第 3、25 章 |
| JSON Schema 規格（Draft 2020-12）與〈Understanding JSON Schema〉 | JSON Schema 組織 | 2020 | tool 參數 schema 與 structured output 的共同基礎 | 第 5、7 章 |
| 〈Efficient Guided Generation for Large Language Models〉 | Willard and Louf（arXiv，Outlines 的原理） | 2023 | 解釋 constrained decoding 如何用有限狀態機保證輸出符合語法 | 第 7 章 |
| 〈Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models〉 | Tam et al.（arXiv） | 2024 | 研究格式限制是否會傷害推理品質，是「先自由推理再結構化輸出」的依據之一 | 第 7 章 |
| 〈Parse, don't validate〉 | Alexis King（個人部落格） | 2019 | 用型別系統思維處理不可信輸入：解析一次、得到可信型別，而不是到處檢查 | 第 7 章 |
| 〈Neural Machine Translation of Rare Words with Subword Units〉 | Sennrich, Haddow, Birch（ACL，BPE 原始論文） | 2016 | 理解 token 是什麼、為什麼不同語言的 token 成本不同 | 第 3 章 |
| Stripe API Reference〈Idempotent requests〉 | Stripe | 持續更新 | idempotency key 在真實金流 API 中的設計，對應第 5 章的副作用分級與重試規則 | 第 5 章 |

## F.5 Memory 與 retrieval

retrieval 回答「這一輪需要哪些外部知識」，memory 回答「哪些東西值得跨 session 保留」。前者有數十年的資訊檢索研究可以借用，後者還在快速演變。下表先列檢索的經典論文（BM25、RRF、nDCG、HNSW），再列 agent memory 的代表系統，讀的時候特別注意各系統的寫入政策與遺忘機制，這是第 12 章最在意的地方。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks〉 | Lewis et al.（NeurIPS） | 2020 | RAG 一詞的出處，理解「檢索再生成」的原始動機 | 第 11 章 |
| 〈The Probabilistic Relevance Framework: BM25 and Beyond〉 | Robertson & Zaragoza（Foundations and Trends in Information Retrieval） | 2009 | BM25 的完整推導，理解關鍵字檢索為什麼仍是 hybrid search 的支柱 | 第 11 章 |
| 〈Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods〉 | Cormack, Clarke & Büttcher（SIGIR） | 2009 | RRF 的出處，hybrid search 合併多路結果最常用的方法 | 第 11 章 |
| 〈Cumulated gain-based evaluation of IR techniques〉 | Järvelin & Kekäläinen（ACM TOIS） | 2002 | nDCG 的出處，檢索品質量測的基礎 | 第 11 章 |
| 〈Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs〉 | Malkov & Yashunin（IEEE TPAMI） | 2018 | HNSW 的原理，多數向量資料庫的近似檢索核心 | 第 11 章 |
| 〈Introducing Contextual Retrieval〉 | Anthropic | 2024 | 在每個 chunk 前加上由模型產生的上下文說明，再搭配 BM25、embedding 與 rerank，是實務上改善 chunking 的做法 | 第 11 章 |
| Memory tool 文件 | Anthropic Claude 開發者文件 | 持續更新 | 檔案式 memory 的官方設計：由 client 端存放檔案，模型透過 tool 讀寫 | 第 12 章 |
| 〈Equipping agents for the real world with Agent Skills〉 | Anthropic Engineering Blog | 2025 | 把 Skills 定位成可漸進揭露的 procedural memory，說明 metadata、說明檔與附屬檔案的分層載入 | 第 12、13 章 |
| Agent Skills 開放標準規格文件 | Agent Skills 專案 | 2025 | Skills 格式的跨產品規格，設計自家 skill 載入機制時的參照 | 第 13 章 |
| 〈MemGPT: Towards LLMs as Operating Systems〉 | Packer et al.（arXiv） | 2023 | 用作業系統的分頁比喻管理 context 與長期記憶，是 Letta 的前身 | 第 12 章 |
| 〈Cognitive Architectures for Language Agents〉 | Sumers et al.（arXiv，CoALA） | 2023 | 提出 working、episodic、semantic、procedural memory 的分類框架，本書第 12 章沿用 | 第 12 章 |
| 〈Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory〉 | Chhikara et al.（arXiv） | 2025 | 以萃取、合併、更新的流程管理長期記憶，適合對照寫入政策設計 | 第 12 章 |
| 〈Zep: A Temporal Knowledge Graph Architecture for Agent Memory〉 | Rasmussen et al.（arXiv） | 2025 | 用帶時間的知識圖處理「事實會過期」的問題，是處理記憶衝突的一種做法 | 第 12 章 |
| Letta 官方文件（MemGPT 概念與 memory blocks） | Letta | 持續更新 | 以記憶為核心的 framework，可觀察 memory blocks 與檔案式記憶的演進 | 第 12、26 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證 Mem0、Zep 的 arXiv 頁面與 Letta 文件；MemGPT 論文內容依知識撰寫。各 memory 系統在公開 benchmark 上的比較曾引發業界爭議，引用分數前請先讀雙方的評測設定。

## F.6 協定

協定是 agent 生態裡變動最快的部分，所以這一節幾乎都是規格本身，而不是二手介紹。讀規格時建議先讀 changelog 與 deprecated 清單，再讀主體；因為本書第 14、15 章講的是設計原理，具體欄位名稱會隨版本改變。授權相關的 RFC 一起列在這裡，因為 MCP 的授權模型就建立在它們之上。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| Model Context Protocol Specification（2026-07-28 版）與 changelog | Model Context Protocol 專案 | 2026 | 本書所稱的「目前版本」，包含 stateless 改版、server/discover 與 deprecated 項目 | 第 5、14、15 章 |
| MCP 規格〈Authorization〉與〈Security Best Practices〉 | Model Context Protocol 專案 | 2026 | MCP server 作為 OAuth resource server 的要求，以及禁止 token passthrough 的理由 | 第 14、33 章 |
| 〈Introducing the Model Context Protocol〉 | Anthropic | 2024 | MCP 的發表文，說明它要解決的 M×N 整合問題 | 第 14 章 |
| 〈JSON-RPC 2.0 Specification〉 | JSON-RPC Working Group | 2010 | MCP 與 A2A 共同使用的訊息格式基礎 | 第 14 章 |
| IETF RFC 9728〈OAuth 2.0 Protected Resource Metadata〉 | IETF | 2025 | MCP 授權中 resource server 如何公告自己的授權伺服器 | 第 14、33 章 |
| IETF RFC 8707〈Resource Indicators for OAuth 2.0〉 | IETF | 2020 | client 指定 token 的 audience，是防止 token 被轉用的關鍵 | 第 14、33 章 |
| IETF RFC 8693〈OAuth 2.0 Token Exchange〉 | IETF | 2020 | 代表使用者行動（delegation）時換發下游 token 的標準做法 | 第 33 章 |
| IETF RFC 9396〈OAuth 2.0 Rich Authorization Requests〉 | IETF | 2023 | 用結構化的授權細節取代粗粒度 scope，適合高風險的單筆授權 | 第 33 章 |
| 〈Agent2Agent (A2A) Protocol Specification〉v1.0 | A2A Project（Linux Foundation） | 2026 | agent card、task 生命週期與 streaming 的正式定義 | 第 15 章 |
| AG-UI〈Agent User Interaction Protocol〉文件與 1.0 release notes | CopilotKit 與社群 | 2026 | agent 到前端的事件模型，對應第 15 章的串流與 generative UI | 第 15、24、37 章 |
| 〈AP2: Agent Payments Protocol〉規格文件 | Google 發起，現由 FIDO Alliance 維護 | 2025 起 | 以 mandate 證明使用者授權的付款流程，理解 agent 付款的信任問題 | 第 15 章 |
| 〈Agentic Commerce Protocol〉規格 | OpenAI 與 Stripe（GitHub） | 2025 起 | agent 代為結帳的商務流程協定 | 第 15 章 |
| x402 規格與 SDK 文件 | x402 Foundation（GitHub） | 2025 起 | 以 HTTP 402 狀態碼完成機器對機器付款的傳輸層協定 | 第 15 章 |
| IETF RFC 6902〈JavaScript Object Notation (JSON) Patch〉 | IETF | 2013 | AG-UI 等協定傳送狀態差異時使用的格式 | 第 15 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證：MCP 最新版為 2026-07-28；A2A 最新為 v1.0.1（2026-05-26）；AP2 為 v0.2 且已移交 FIDO Alliance；ACP 最新穩定版為 2026-04-17；x402 已移交 x402 Foundation。MCP 移交 Linux Foundation 旗下 Agentic AI Foundation 的確切日期未經網路查證。

## F.7 Orchestration 與 multi-agent

orchestration 的閱讀重點是「誰決定流程」以及「狀態放在哪裡」。下表混合了三種來源：graph 與 workflow framework 的官方文件、multi-agent 的正反兩方論述，以及 durable execution 引擎的 agent 文件。建議把 Anthropic 的 research system 與 Cognition 的〈Don't Build Multi-Agents〉放在同一天讀，兩篇並不矛盾，差別在任務的 context 耦合程度（第 20 章）。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈How we built our multi-agent research system〉 | Anthropic Engineering Blog | 2025 | orchestrator-worker 架構在研究任務上的完整經驗，含 token 成本倍數、prompt 原則與評估方式 | 第 8、18、20、24、29、35、40、44 章 |
| 〈Don't Build Multi-Agents〉 | Cognition Blog（Walden Yan） | 2025 | 從 context 共享與決策一致性論證多數任務該用單一 agent，是 multi-agent 的必讀反方 | 第 10、20、35、39、43、44 章 |
| 〈Towards self-driving codebases〉 | Cursor Blog | 2026 | 長時間、多層 planner 與 worker 的 coding 實驗，展示寫入型平行任務如何隔離 | 第 20、39 章 |
| 〈Devin Fusion〉 | Cognition Blog | 2026 | 主模型加輔助模型的協作與切換時機，選在 compaction 時切換以避免額外的 cache 成本 | 第 20、25、39、43 章 |
| Subagents 與 Agent teams 文件 | Anthropic Claude Code 文件 | 持續更新 | 產品級 subagent 隔離與 teammate 溝通的具體設計，包括隊友不能代替使用者核准 | 第 20、39 章 |
| 〈How Claude Code works〉 | Anthropic Claude Code 文件 | 持續更新 | 單一主 loop 加上 tools、context 與 session 管理的產品級說明 | 第 4、39 章 |
| LangGraph 文件：Persistence、Interrupts、Time travel、human-in-the-loop | LangChain | 持續更新 | checkpoint、interrupt 與倒帶在 graph framework 中的實作方式 | 第 19、21 章 |
| Microsoft Agent Framework 文件：Overview、Workflows、Middleware | Microsoft Learn | 2025 起，持續更新 | 企業級 framework 的 workflow 與 middleware 抽象，可對照 `loom` 的設計 | 第 2、18、19、23、26 章 |
| Agent Development Kit 文件：Runtime、Events、Callbacks、Workflow agents | Google | 2025 起，持續更新 | 以 event 為核心的 runtime 設計，與第 23 章的持久化事件對照 | 第 19、23 章 |
| OpenAI Agents SDK 文件：Agents、Handoffs、Guardrails、Sessions、human-in-the-loop | OpenAI | 2025 起，持續更新 | handoff 與 guardrail 作為一級抽象的代表設計 | 第 21、23 章 |
| 〈AWS Step Functions Developer Guide〉 | AWS | 持續更新 | 成熟的託管狀態機服務，適合理解 graph orchestration 在 LLM 之前就有的設計 | 第 19 章 |
| Temporal 文件〈AI Cookbook〉 | Temporal | 持續更新 | 以 event history 與 replay 實作可恢復 agent 的範例集 | 第 22 章 |
| Restate 文件 AI agents 章節 | Restate | 持續更新 | 以 durable function 與日誌包裝 LLM 與 tool 呼叫的做法 | 第 22 章 |
| DBOS 文件〈Build Durable AI Agents〉 | DBOS | 持續更新 | 以資料庫為基礎的 durable execution，適合比較不同引擎的取捨 | 第 22 章 |
| 〈Introducing ambient agents〉 | LangChain Blog | 2025 | 由事件觸發、在背景運作的 agent 型態，以及它對 UX 與人工審核的要求 | 第 22、37 章 |
| 〈Why Do Multi-Agent LLM Systems Fail?〉（MAST） | Cemri et al.（arXiv） | 2025 | 從多個框架的 trace 歸納出 multi-agent 的失敗分類，指出許多失敗來自系統設計與驗證，而不是模型本身 | 第 20、27、34、46 章 |

## F.8 評估與 benchmarks

評估是 agent 工程裡最容易被跳過、也最決定上限的部分。下表前半是方法論（怎麼建 eval set、怎麼用 LLM-as-judge、怎麼加信賴區間），後半是主要 benchmark 的原始論文。讀 benchmark 論文的目的不是記分數，而是理解它測什麼、不測什麼，以及它的環境與評分方式能不能借來建自家 benchmark（第 28 章）。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Demystifying evals for AI agents〉 | Anthropic Engineering Blog | 2026 | outcome 與 trajectory 評估、pass@k 與 pass^k、grader 類型的完整整理，是第 27 章的骨架 | 第 27、28、35、37、38、40、41、46 章 |
| 〈Your AI Product Needs Evals〉 | Hamel Husain（個人部落格） | 2024 | 從 error analysis 出發建 eval 的實務流程，適合產品團隊一起讀 | 第 29、37、38 章 |
| 〈Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena〉 | Zheng et al.（NeurIPS Datasets and Benchmarks） | 2023 | 系統性分析 LLM-as-judge 的位置偏誤、冗長偏誤與自我偏好 | 第 27 章 |
| 〈Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences〉 | Shankar et al.（UIST） | 2024 | 說明評分標準本身會在看過資料後改變，以及如何讓 judge 與人工判斷對齊 | 第 27 章 |
| 〈Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations〉 | Evan Miller（arXiv） | 2024 | 把統計顯著性帶進 eval：樣本數、信賴區間與成對比較 | 第 27、28 章 |
| 〈Evaluating Large Language Models Trained on Code〉 | Chen et al.（arXiv） | 2021 | pass@k 指標與無偏估計式的出處 | 第 27 章 |
| Inspect 文件 | UK AI Security Institute | 持續更新 | 開源 eval framework，以 dataset、solver、scorer 組成任務，並支援 sandbox | 第 27 章 |
| 〈Cheating On AI Agent Evaluations〉 | NIST CAISI | 2025 | 整理 agent 在評測中修改測試、讀取答案等作弊行為，對 grader 隔離設計很有用 | 第 30、34、43 章 |
| 〈SWE-bench: Can Language Models Resolve Real-World GitHub Issues?〉 | Jimenez et al.（ICLR） | 2024 | 以真實 GitHub issue 與測試評估 coding agent 的經典 benchmark | 第 28、39、43 章 |
| 〈SWE-Bench Pro〉論文與排行榜 | Scale AI | 2025 | 在 SWE-bench Verified 飽和後，以更難且有保留切分的題目比較前沿系統 | 第 28 章 |
| Terminal-Bench 官方網站與排行榜 | Stanford 與 Laude Institute | 2025 起，持續更新 | 終端機環境中的真實任務，排行榜同時列出成本與 token，可借鏡如何回報成本 | 第 28、39 章 |
| 〈τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains〉 | Yao et al.（Sierra，arXiv） | 2024 | 模擬使用者與政策文件的客服評估，並提出 pass^k，是青鳥客服 agent 評估的原型 | 第 1、27、28、38、41、42 章 |
| 〈τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment〉 | Barres et al.（Sierra Research） | 2025 | 使用者也能操作環境的雙控制設定，更接近真實的技術支援情境 | 第 28、41 章 |
| 〈OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments〉 | Xie et al.（NeurIPS） | 2024 | 在真實作業系統中評估 computer use agent，並以程式檢查最終狀態 | 第 16、28 章 |
| 〈WebArena: A Realistic Web Environment for Building Autonomous Agents〉 | Zhou et al.（ICLR） | 2024 | 可自架的網站環境，適合學習如何建立可重現的 browser agent 評估 | 第 16、28 章 |
| 〈Mind2Web: Towards a Generalist Agent for the Web〉 | Deng et al.（NeurIPS） | 2023 | 跨大量真實網站的網頁任務資料集，聚焦動作預測 | 第 16 章 |
| 〈GAIA: A Benchmark for General AI Assistants〉 | Mialon et al. | 2023 | 對人簡單、對 agent 困難的多步驟助理題目，答案短且好驗證 | 第 28、40 章 |
| 〈BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents〉 | Wei et al.（OpenAI） | 2025 | 難找但好驗證的網路資訊題，用來評估 research agent 的搜尋堅持度 | 第 28、40 章 |
| 〈MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering〉 | Chan et al.（OpenAI） | 2024 | 以 Kaggle 競賽評估 agent 的機器學習工程能力，適合理解長任務 benchmark 的成本問題 | 第 28 章 |
| 〈AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents〉 | Debenedetti et al.（NeurIPS Datasets and Benchmarks） | 2024 | 同時量測效用與安全的 agent 環境，評估防禦設計時的共同基準 | 第 31、32 章 |
| 〈Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs〉（BIRD） | Li et al.（NeurIPS） | 2023 | 以大型、真實的資料庫評估 text-to-SQL，並以執行結果比對評分 | 第 44 章 |
| 〈Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows〉 | Lei et al.（ICLR） | 2025 | 企業級的大型 schema 與多步驟資料工作流程，適合理解 analytics agent 與一般 text-to-SQL 的落差 | 第 44 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證：SWE-bench Verified 已接近飽和，前沿比較改看 SWE-Bench Pro；Terminal-Bench 改為持續更新的 benchmark，排行榜版本為 4.0.0；τ-bench 系列已演進到 τ³；OSWorld 2.0 於 2026-06-26 釋出。引用任何分數都要同時寫出 benchmark 版本與查詢日期。MLE-bench 的題數與細節依知識撰寫，未經網路查證。

## F.9 可觀測性

agent 的 trace 比一般服務更長、更深、更依賴內容，但底層概念仍來自分散式追蹤。這一節把 OpenTelemetry 的 GenAI 慣例與分散式系統的經典放在一起讀，前者告訴你屬性該叫什麼名字，後者告訴你為什麼 trace 要這樣切、取樣與傳播要怎麼做。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Semantic Conventions for Generative AI Systems〉（semantic-conventions-genai repository，含 agent spans 與 MCP conventions） | OpenTelemetry | 持續更新 | `invoke_agent`、`chat`、`execute_tool` 等 span 名稱與屬性的權威定義，本書 tracing 慣例以它為準 | 第 25、29、36 章 |
| 〈Trace Context〉Recommendation | W3C | 2020 | 跨服務傳遞 trace id 的標準，agent 呼叫 MCP server 或其他 agent 時同樣需要 | 第 29 章 |
| 〈Dapper, a Large-Scale Distributed Systems Tracing Infrastructure〉 | Sigelman et al.（Google Technical Report） | 2010 | 現代 tracing 的原型，說明 span 樹、取樣與低開銷的設計 | 第 29 章 |
| 《Observability Engineering》 | Charity Majors、Liz Fong-Jones、George Miranda（O'Reilly） | 2022 | 以高基數事件與探索式除錯為核心的觀測思維，很適合 agent 這種行為多變的系統 | 第 29 章 |
| 《Site Reliability Engineering》〈Monitoring Distributed Systems〉 | Google（O'Reilly） | 2016 | 四個黃金訊號與告警設計，對應 agent 的線上監控指標 | 第 29 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證 OTel GenAI semantic conventions 已搬到獨立 repository，並新增 workflow、plan 與 memory 相關 operation；幾乎所有項目仍是 Development 穩定度，屬性名稱可能再變動。

## F.10 安全

agent 安全的閱讀順序建議是：先理解成因（indirect prompt injection、lethal trifecta），再讀架構層的防禦模式（dual-LLM、plan-then-execute、CaMeL），最後讀真實產品如何在環境層做 containment。下表只收錄討論成因、偵測與防禦設計的資料；這也是本書第 31、32 章的立場：模型層的分類器只能降低機率，安全邊界要靠確定性的架構。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈The lethal trifecta for AI agents: private data, untrusted content, and external communication〉 | Simon Willison（個人部落格） | 2025 | 用三個條件說明資料外洩風險何時成立，是第 31 章 lethal trifecta 檢查的出處 | 第 2、17、31、32、42、44、46 章 |
| 〈The Dual LLM pattern for building AI assistants that can resist prompt injection〉 | Simon Willison（個人部落格） | 2023 | 讓接觸不可信內容的模型拿不到權限，是隔離式防禦的早期提案 | 第 32 章 |
| 〈Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection〉 | Greshake et al.（AISec） | 2023 | 首批系統化描述 indirect prompt injection 成因與影響的論文 | 第 31 章 |
| 〈Design Patterns for Securing LLM Agents against Prompt Injections〉 | Beurer-Kellner, Tramèr, Debenedetti et al.（arXiv） | 2025 | 整理數種可證明限制 injection 影響的架構模式，並分析各自的效用代價 | 第 8、31、32 章 |
| 〈Defeating Prompt Injections by Design〉（CaMeL） | Debenedetti et al.（arXiv） | 2025 | 以控制流與資料流分離、capability 標記來阻斷 injection，是第 32 章 `loom.guardrails` 的概念來源 | 第 32 章 |
| 〈Defending Against Indirect Prompt Injection Attacks With Spotlighting〉 | Hines et al.（Microsoft） | 2024 | 以標示與編碼不可信內容降低 injection 成功率，代表模型層防線的能力與限制 | 第 32 章 |
| 〈How we contain Claude across products〉 | Anthropic Engineering Blog | 2026 | 從 gVisor、OS sandbox 到本地 VM 的 containment 實務，並記錄「allowlist 等同授權」等事故教訓 | 第 17、21、31、32、39、43、46 章 |
| Claude Code auto mode 的設計說明文章（標題待核對） | Anthropic Engineering Blog | 2026 | 說明自動核准 classifier 的兩層架構與誤判率，以及為何它只能當第二道防線 | 第 21、32、39 章 |
| 〈OWASP Top 10 for LLM Applications 2025〉 | OWASP GenAI Security Project | 2024 | LLM 應用風險清單，其中 LLM06 Excessive Agency 與 agent 最相關 | 第 31、32 章 |
| 〈OWASP Top 10 for Agentic Applications for 2026〉 | OWASP GenAI Security Project | 2025 | agent 專屬的 ASI01–ASI10 風險清單，2025 年 12 月發布 | 第 12、14、21、31、32、33、42 章 |
| 《Threat Modeling: Designing for Security》 | Adam Shostack（Wiley） | 2014 | threat modeling 的經典方法論，第 31 章為青鳥做威脅建模時的流程基礎 | 第 31 章 |
| 〈Firecracker: Lightweight Virtualization for Serverless Applications〉 | Agache et al.（NSDI） | 2020 | microVM 的設計與取捨，理解託管 sandbox 服務的隔離基礎 | 第 17 章 |
| gVisor 官方文件〈Security Model〉 | gVisor 專案 | 持續更新 | 使用者空間核心如何縮小攻擊面，是 container 與 microVM 之間的選項 | 第 17 章 |
| Linux Kernel 文件〈Control Group v2〉 | Linux Kernel 社群 | 持續更新 | CPU、記憶體與行程數限制的底層機制 | 第 17 章 |
| Python 官方文件〈resource〉與〈subprocess〉 | Python Software Foundation | 持續更新 | 第 17 章概念版執行器所使用的標準函式庫介面 | 第 17 章 |
| 〈Efficient Data Structures for Tamper-Evident Logging〉 | Crosby & Wallach（USENIX Security） | 2009 | 防竄改日誌的資料結構，對應稽核日誌的 hash chain 設計 | 第 33 章 |
| PostgreSQL 官方文件〈Row Security Policies〉 | PostgreSQL Global Development Group | 持續更新 | 資料庫原生的列級權限：以政策把租戶或使用者範圍綁在引擎層，是 analytics agent 權限感知查詢的底線 | 第 44 章 |
| 〈Accelerating the Adoption of Software and AI Agent Identity and Authorization〉concept paper | NIST NCCoE | 2026 | 美國標準機構對 agent 身分與授權問題的整理，是 agent identity 的參考框架 | 第 33 章 |

## F.11 治理與法規

這一類資料的讀法和技術文件不同：它們規定的是組織要「能證明」什麼，而不是程式要怎麼寫。本書只在概念層級引用，實際適用範圍與義務請以法律專業意見為準。建議先讀 NIST AI RMF 建立風險管理的語彙，再看 ISO/IEC 42001 的管理系統要求，最後依業務所在地區閱讀法規。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈AI Risk Management Framework（AI RMF 1.0）〉 | NIST | 2023 | Govern、Map、Measure、Manage 四個功能的風險管理框架 | 第 34 章 |
| 〈NIST AI 600-1：Generative AI Profile〉 | NIST | 2024 | 把 AI RMF 套用到生成式 AI 的特有風險與對應行動 | 第 34 章 |
| ISO/IEC 42001:2023〈Information technology — Artificial intelligence — Management system〉 | ISO/IEC | 2023 | AI 管理系統的國際標準，適合規劃內部治理流程與稽核 | 第 34 章 |
| 歐盟《人工智慧法》（Regulation (EU) 2024/1689）及 2026 年 AI Omnibus 修正 | 歐盟 | 2024；2026 修正 | 依風險分級規定義務，透明義務與高風險系統要求都可能影響 agent 產品 | 第 34 章 |
| 〈Moral Crumple Zones: Cautionary Tales in Human-Robot Interaction〉 | Madeleine Clare Elish（Engaging Science, Technology, and Society） | 2019 | 說明人工審核者可能成為「替系統吸收責任」的角色，是設計 human-in-the-loop 時必須面對的問題 | 第 21 章 |
| SAE〈J3016：Taxonomy and Definitions for Terms Related to Driving Automation Systems〉 | SAE International | 持續更新 | 自駕分級的原始文件，本書 L0–L5 autonomy 等級借用其精神 | 第 1 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證：EU AI Act 的 AI Omnibus 修正於 2026-07-27 生效，Annex III 高風險義務延到 2027-12-02，Annex I 延到 2028-08-02；NIST 於 2026 年 2 月啟動 AI Agent Standards Initiative，AI RMF 1.0 正在修訂。ISO/IEC 42001 的細節依知識撰寫，未經網路查證。

## F.12 產品與案例

這一節收錄建造者公開的產品架構文章與事故分析。它們的價值在於「真實限制下的取捨」：成本、延遲、cache 命中率、事故後的修正。閱讀時務必記下文章日期，因為產品細節變化很快，本書第 39–41 章只引用公開資訊並標日期。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 〈Scaling Managed Agents〉 | Anthropic Engineering Blog | 2026 | brain、hands、session 三分的託管架構，以及「context 是 session log 的可重建視圖」的實作 | 第 2、10、22、26、36、43、46 章 |
| 2026 年 4 月 23 日 Claude Code 品質問題 postmortem（標題待核對） | Anthropic Engineering Blog | 2026 | harness 預設值（effort、thinking 保留、prompt 字數限制）如何造成可感知的品質下降，以及漸進 rollout 與 per-model eval 的教訓 | 第 3、34、36、38、39 章 |
| 以多個平行 Claude 實例協作建造 C 編譯器的實驗紀錄（標題待核對） | Anthropic Engineering Blog | 2026 | 以既有編譯器當 oracle、用檔案鎖分派任務，說明 verifier 品質決定長任務的上限 | 第 20、30 章 |
| 〈Reasoning models don't always say what they think〉 | Anthropic Research | 2025 | 推理模型的思考過程不一定忠實反映決策依據，影響「把 thinking 給使用者看」的產品設計 | 第 37 章 |
| SWE-2 發表文（標題待核對） | Cognition Blog | 2026 | 以「成功減去成本懲罰」的 reward 訓練 coding agent，是公開資訊中較具體的 agent RL 配方 | 第 30、39 章 |
| 〈Why We Built Our Own Cloud Agent Infrastructure〉 | Harvey Blog | 2026 | 法律領域 agent 平台為何自建執行基礎設施 | 第 41 章 |
| 〈Rebuilding Playbook Review as a Multi-Agent System〉 | Harvey Blog | 2026 | 把專業審閱流程改寫成 multi-agent 的實際取捨 | 第 41 章 |
| 〈Post-Training RLM Agents for M&A Diligence〉 | Harvey Blog | 2026 | 以 Recursive Language Model harness 讓 agent 用程式遍歷大量文件，並以後訓練提升表現 | 第 40、41 章 |
| 〈The Agency, Control, Reliability (ACR) Tradeoff〉 | Intercom Fin Research | 2025 | 從客服產品角度描述自主程度、控制與可靠性之間的三方取捨 | 第 41 章 |
| Deep research 指南 | OpenAI API 文件 | 持續更新 | 託管 research agent 的資料源、成本控制與 background 模式限制 | 第 40、44 章 |
| Deep Research 文件 | Google Gemini API 文件 | 持續更新 | 透過 Interactions API 以背景模式執行研究任務，並支援先出計畫再執行 | 第 40 章 |
| Codex 文件〈Sandboxing〉與 openai/codex GitHub repository | OpenAI | 持續更新 | 開源 coding agent 的 sandbox、權限模式、apply_patch 與 compaction 實作，可直接讀原始碼對照 | 第 39 章 |
| google-gemini/gemini-cli GitHub repository | Google | 持續更新 | 開源 coding agent 的 context、routing、sandbox 與 policy 模組，適合對照不同產品的 harness 切分 | 第 39 章 |
| GitHub Docs〈About Copilot coding agent〉（文件現稱 Copilot cloud agent） | GitHub | 持續更新 | 從 issue 指派、在臨時環境中工作、每個任務一個分支與 PR 的 background coding agent 產品形態 | 第 39、43 章 |
| Computer use tool 文件 | Anthropic（Claude Developer Platform） | 持續更新 | 截圖、座標與動作空間的官方介面，對應第 16 章的 perception–action loop | 第 16 章 |
| 〈Computer-Using Agent〉介紹文 | OpenAI | 2025 | 另一家廠商的 computer use 設計說明，可對照動作空間與安全確認機制 | 第 16 章 |
| Playwright 文件〈Auto-waiting〉與〈Locators〉 | Playwright（Microsoft） | 持續更新 | browser 自動化中等待與元素定位的成熟做法，可直接借給 browser agent | 第 16 章 |
| W3C〈Accessible Name and Description Computation〉與〈WAI-ARIA〉 | W3C | 持續更新 | accessibility tree 的語意來源，理解為什麼 DOM 與無障礙資訊比截圖更穩定 | 第 16 章 |
| 〈Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V〉 | Yang et al. | 2023 | 在截圖上加標記協助模型定位元素的技巧 | 第 16 章 |
| Amazon Bedrock AgentCore Developer Guide〈What is Amazon Bedrock AgentCore〉 | AWS | 2025 起，持續更新 | 託管 agent 平台的元件拆分（runtime、gateway、identity、memory、observability） | 第 26、36 章 |
| 〈Agent Engine overview〉 | Google Cloud | 持續更新 | 另一家雲端的託管 agent runtime，可與 AgentCore 對照 | 第 26、36 章 |
| 〈Guidelines for Human-AI Interaction〉 | Amershi et al.（Microsoft Research，CHI） | 2019 | 十八條人機互動準則，例如說明系統能做什麼、出錯時如何讓使用者修正 | 第 37 章 |
| 〈People + AI Guidebook〉 | Google PAIR | 2019 起，持續更新 | 以產品設計者視角整理信任、回饋與錯誤處理的設計模式 | 第 37 章 |
| 《Winning at New Products》 | Robert G. Cooper | 1986 起多版 | Stage-Gate 方法的原始著作，第 38 章五階段路線圖的退出條件概念來自這裡 | 第 38 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月，survey 已查證上表 Anthropic、Cognition、Cursor、Harvey 各篇的標題與日期；Intercom 的 ACR 文章只確認標題與日期、未讀內文；OpenAI 主站的部分文章（例如 Codex agent loop 相關文章）無法讀取，因此不收錄。產品的託管服務名稱可能更名，例如 Google 原本的 Agent Engine 頁面現已改用 Gemini Enterprise Agent Platform 與 Agent Runtime 的名稱（頁面未明說是更名），請以官方文件當時的名稱為準。

## F.13 系統設計基礎

agent 系統最後還是分散式系統：要處理重試、冪等、過載、事件日誌、版本相容與漸進發布。這一節的書與文章都早於 LLM，但本書第 22–25、35–38 章的許多設計（fencing token、熔斷、ports and adapters、Hyrum's Law）直接來自這裡。若讀者只有時間讀一本，建議從《Designing Data-Intensive Applications》開始。

| 名稱 | 作者或機構 | 年份 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| 《Designing Data-Intensive Applications》 | Martin Kleppmann（O'Reilly） | 2017 | 一致性、exactly-once、fencing token 與事件日誌的系統性說明，durable execution 的理論底子 | 第 22、36 章 |
| 《Release It! Design and Deploy Production-Ready Software》第 2 版 | Michael T. Nygard（Pragmatic Bookshelf） | 2018 | circuit breaker、bulkhead、timeout 等穩定性模式，對應 model fallback 與熔斷 | 第 25、36 章 |
| 《Site Reliability Engineering: How Google Runs Production Systems》 | Betsy Beyer et al.（O'Reilly） | 2016 | SLO、error budget、處理過載與漸進式發布的經典；第 21 章〈Handling Overload〉與第 22 章〈Addressing Cascading Failures〉是 runtime 重試與退避設計的背景 | 第 24、34、35、36、38 章 |
| 《The Site Reliability Workbook》〈Alerting on SLOs〉 | Betsy Beyer et al.（O'Reilly） | 2018 | 用燃燒率設計 SLO 告警的具體方法 | 第 34 章 |
| 《Software Engineering at Google》 | Titus Winters、Tom Manshreck、Hyrum Wright（O'Reilly） | 2020 | 第 1 章的 Hyrum's Law 說明為什麼 framework 的任何可觀察行為都會被依賴 | 第 23 章 |
| 〈How to Design a Good API and Why it Matters〉 | Joshua Bloch（OOPSLA Companion） | 2006 | API 設計的經典原則，同樣適用於 framework 與 tool 介面 | 第 23 章 |
| 〈Semantic Versioning 2.0.0〉 | Tom Preston-Werner | 2013 | 版本號如何表達相容性承諾，對應 `loom` 的版本與相容層設計 | 第 23 章 |
| 〈Event Sourcing〉 | Martin Fowler | 2005 | 以事件為唯一事實來源、狀態可重建，是 session log 不變式的設計原型 | 第 10、23 章 |
| 〈Hexagonal Architecture（Ports and Adapters）〉 | Alistair Cockburn | 2005 | 用 port 隔離外部依賴，是 provider adapter 與避免 lock-in 的架構基礎 | 第 25、26 章 |
| 〈StranglerFigApplication〉 | Martin Fowler（bliki） | 2004 | 逐步替換舊系統的遷移策略，適用於從某個 framework 遷出 | 第 26 章 |
| 〈Statecharts: A Visual Formalism for Complex Systems〉 | David Harel（Science of Computer Programming） | 1987 | 階層式狀態機的形式化，graph orchestration 與 task 狀態機的源頭 | 第 19 章 |
| 〈Pregel: A System for Large-Scale Graph Processing〉 | Malewicz et al.（SIGMOD） | 2010 | 以 superstep 推進的 graph 計算模型，部分 agent graph runtime 採用類似的執行語意 | 第 19 章 |
| 〈FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance〉 | Chen, Zaharia, Zou（arXiv） | 2023 | 以模型串接與提早停止降低成本，是 model routing 的早期研究 | 第 25 章 |
| 〈RouteLLM: Learning to Route LLMs with Preference Data〉 | Ong et al.（arXiv） | 2024 | 用偏好資料訓練 router，在強弱模型之間依難度分流 | 第 25 章 |
| 〈DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines〉 | Khattab et al.（ICLR） | 2024 | 把 prompt 當成可最佳化的程式參數，是 prompt optimization 的代表框架 | 第 30 章 |
| 〈GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning〉 | Agrawal et al.（arXiv；ICLR 2026） | 2025 | 以反思式演化最佳化 prompt，並與 RL 比較樣本效率 | 第 30 章 |
| 〈A Proof for the Queuing Formula: L = λW〉 | John D. C. Little（Operations Research） | 1961 | Little's law 的原始證明，本書估算並行 session、worker 與 sandbox 數量的基礎 | 第 35、43 章 |
| 〈Exponential Backoff And Jitter〉 | Marc Brooker（AWS Architecture Blog） | 2015 | 用模擬說明加入 jitter 的退避如何避免重試同步造成的流量尖峰 | 第 24 章 |
| 〈Notes on structured concurrency, or: Go statement considered harmful〉 | Nathaniel J. Smith（個人部落格） | 2018 | structured concurrency 的論證：並行任務的生命週期要被包在明確的範圍裡，取消與錯誤才不會遺失 | 第 24 章 |
| Python 官方文件〈Coroutines and Tasks〉 | Python Software Foundation | 持續更新 | asyncio 的 Task 取消、TaskGroup、timeout 與 shield，第 24 章 runtime 實作直接使用的介面 | 第 24 章 |
| FoundationDB 文件〈Simulation and Testing〉 | FoundationDB 專案 | 持續更新 | 以確定性模擬與故障注入測試分散式系統，對應 runtime 在虛擬時間上做 fault injection 的測試策略 | 第 24 章 |
| 《Building Multi-Tenant SaaS Architectures》 | Tod Golding（O'Reilly） | 2024 | silo、pool 與混合部署、租戶隔離與 noisy neighbor 的系統化整理 | 第 42 章 |
| AWS Well-Architected Framework〈SaaS Lens〉 | AWS | 持續更新 | 多租戶 SaaS 的身分、隔離、計量與營運檢查項目，可對照第 42 章的平台設計 | 第 42 章 |
| 《System Design Interview: An Insider's Guide》 | Alex Xu | 2020 | system design interview 的節奏（需求、估算、高階設計、深入、取捨），第 42–44 章的演練沿用這個流程 | 第 42 章 |
| 〈Technology Radar〉 | Thoughtworks | 定期發布 | adopt、trial、assess、hold 四環的出處，示範如何把技術判斷寫成有理由、可定期重審的紀錄 | 第 46 章 |

## F.14 收錄原則與查證說明

這份書單的收錄規則有三條。第一，只收錄本書各章引用過、或 2026-10 survey 實際讀過的文件；沒有把握確實存在的文件一律不收。第二，能確定文件存在、但無法確定確切標題的，改用描述性名稱並標「標題待核對」，避免讀者照著錯誤標題找不到。第三，版本、日期與產品細節依 survey 的查證狀態處理，標為未經網路查證的內容只在「2026 現況」callout 中以保留語氣說明。

| 狀態 | 意義 | 讀者該怎麼做 |
|---|---|---|
| 一般項目 | 名稱、作者與年份已由各章或 survey 核對 | 直接以名稱與機構搜尋 |
| 標題待核對 | 文件存在，但確切標題未核對 | 以機構、年份與描述關鍵字搜尋，找到後以原文標題為準 |
| 年份寫「持續更新」 | 官方文件或規格會不斷改版 | 閱讀時記下當時版本與日期，並先看 changelog |
| 2026 現況 callout 中的版本與日期 | 截至 2026 年 10 月的狀態 | 引用前再查一次官方頁面，benchmark 分數必須附版本與查詢日期 |

學術論文的年份以正式發表的會議或期刊為準；只有 arXiv 版本的，寫首次公開的年份。同一份文件在多章出現時，「對應章節」欄列出主要相關的章節，不是窮舉所有提及處。若讀者發現某項已更名、搬遷或撤下，建議在自己的筆記中記錄發現日期與替代來源，這也是第 46 章「持續學習」所建議的做法。
