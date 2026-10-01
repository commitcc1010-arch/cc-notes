# 《從 Commit 到可靠服務：Software Engineering × SRE × AI》章節大綱

每一列：章｜檔名｜標題｜對應原書｜Q&A 數｜必須涵蓋。原書代號：**SWE** =《Software Engineering at Google》（Winters, Manshreck, Wright）章號；**SRE** =《Site Reliability Engineering》章號；**WB** =《The Site Reliability Workbook》章號。舊稿：`/tmp/sre_old/chapters/chNN.md`（同章號）。

貫穿案例 **Harbor 港灣市集**：一個台灣的線上市集，服務包括 web／app、search、cart、checkout、payments、inventory、notification，以及兩種 AI：工程團隊使用的 AI coding agent，與面向客戶的 AI 客服 agent（能查訂單、退款）。人物：初階工程師阿凱、tech lead 美華、SRE 志明、產品經理 Lisa、工程經理 Kevin。故事從 8 人新創成長到 200 人工程組織。

## Part 0　先建立全局模型（`Part 0 - 全局模型/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 1 | 01 - 從一行程式碼到可靠服務.md | 從一行程式碼到可靠服務 | SWE 1；SRE 1 | 8 | 一個 commit 從 IDE 到 production 的完整旅程（design、code、review、test、build、CI、release、監控、事故、postmortem 回饋）；software engineering 與 SRE 各自回答的問題；為什麼兩者是同一條生命週期；AI 在每一站的角色與責任邊界；Harbor 案例介紹；全書地圖與讀法 |
| 2 | 02 - 共同語言.md | 共同語言：Service、Feedback 與 AI Agent | SWE 1；SRE 2 | 8 | service、API、dependency、state、invariant、contract、owner 等詞；control loop 與 feedback loop；signal vs noise；production 的組成（cluster、scheduler、load balancer、storage）；AI agent 的組成（model、context、tools、memory、policy、eval）；人、機器、agent 的責任分工模型；本書通用判斷框架 |

## Part 1　Software Engineering 的根基（`Part 1 - Software Engineering 根基/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 3 | 03 - Programming 與 Software Engineering.md | Programming 與 Software Engineering 的差別 | SWE 1 | 8 | 「軟體工程是隨時間積分的程式設計」；壽命、規模、協作三個維度；sustainable 的定義；一次性腳本 vs 十年系統的不同決策；工程成本（金錢、時間、認知、機會成本）；何時「先寫出來」是對的 |
| 4 | 04 - Time and Change.md | Time and Change：軟體為什麼會老化 | SWE 1 | 8 | 依賴、OS、語言版本、安全漏洞帶來的被迫變更；upgrade 的成本曲線（越晚越貴）；「能升級」本身是能力；Beyoncé rule 前身；長壽 codebase 的維護策略；技術債的定義與分類；Harbor 的 Python 2→3／框架升級事故 |
| 5 | 05 - Hyrum’s Law.md | Hyrum’s Law：所有可觀察行為都可能成為依賴 | SWE 1 | 8 | Hyrum's Law 原文與意涵；隱性契約例子（hash 順序、錯誤訊息、timing）；API 設計防禦（隨機化、版本化、明確文件）；如何安全改變可觀察行為（研究使用者、flag、遷移）；與 semantic versioning 的關係 |
| 6 | 06 - Scale and Growth.md | Scale and Growth：規模如何改變問題 | SWE 1 | 8 | 隨 codebase、人數、流量增長而變貴的事；「觀察到線性成長的人工工作就是警訊」；Beyoncé rule；shift left；集中化 vs 去中心化；知識、流程、基礎設施的規模化；Harbor 從 8 人到 200 人 |
| 7 | 07 - Trade-offs Costs 與 ADR.md | Trade-offs、Costs 與 Architecture Decision Records | SWE 1 | 8 | 決策的成本模型；「沒有資料時如何做決策」；可逆 vs 不可逆決策（one-way／two-way door）；ADR 格式與範例；記錄被否決的選項；何時重新評估決策；Harbor 選 monolith vs microservices 的 ADR |

## Part 2　團隊、文化與領導（`Part 2 - 團隊文化與領導/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 8 | 08 - HRT 與團隊合作.md | HRT、Ownership 與真正的團隊合作 | SWE 2 | 8 | Humility、Respect、Trust；天才迷思；隱藏工作的代價；early feedback；bus factor；如何給與收 code review／設計回饋；ownership 的意義（不是獨佔）|
| 9 | 09 - Psychological Safety.md | Psychological Safety：讓壞消息提早出現 | SWE 2、5；SRE 15 | 8 | Project Aristotle；心理安全的定義與迷思（不是一團和氣）；壞消息延遲的成本；blameless 文化與責任的關係；主管行為如何影響；量測與改善方法；與事故學習的連結 |
| 10 | 10 - Knowledge Sharing.md | Knowledge Sharing、Readability 與 Bus Factor | SWE 3 | 8 | 知識孤島；文件、mentoring、office hours、tech talks、codelab；readability 制度；問問題的文化；知識的 single source of truth；onboarding 設計；AI 作為知識檢索的機會與風險 |
| 11 | 11 - Engineering for Equity.md | Engineering for Equity：為不同使用者設計 | SWE 4 | 8 | 偏誤如何進入產品（資料、預設值、測試對象）；accessibility；多元團隊的價值；把公平性當成需求與測試；AI 模型偏誤與評估；具體檢查清單 |
| 12 | 12 - Tech Lead 與 Manager.md | Tech Lead、Manager 與 Decision Rights | SWE 5 | 8 | TL、EM、TLM 角色；servant leadership；反模式（雇用 pushover、忽略低績效、凡事自己來）；授權與 decision rights（RACI／DACI）；如何說 no；1:1；從 IC 到 lead 的轉變 |
| 13 | 13 - Leading at Scale.md | Leading at Scale：從個人影響力到平台與制度 | SWE 6 | 8 | Always Be Deciding／Leaving／Scaling；把問題拆成可交接的部分；平台化與制度化；影響力而非權力；處理模糊問題；保護團隊的注意力；技術策略文件 |
| 14 | 14 - Measuring Productivity.md | Measuring Engineering Productivity without Gaming | SWE 7 | 8 | 為什麼量測；Goodhart's law；GSM（Goals／Signals／Metrics）；QUANTS；DORA 四大指標（含 2024 後的 rework rate）；SPACE；DevEx；質化與量化結合；AI 工具導入後如何評估生產力（避免只算行數或接受率）|

## Part 3　讓變更可以長期維持（`Part 3 - 可持續的變更/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 15 | 15 - Style Guide 與 Automation.md | Style Guide、Rules 與 Automation | SWE 8 | 8 | 規則的目的（為讀者最佳化、一致性、避免錯誤）；規則要有理由；formatter／linter／type checker；autofix；例外處理；規則的演化與刪除；在 CI 強制；AI 生成程式碼的風格一致性 |
| 16 | 16 - Code Review.md | Code Review：正確性、理解與小型變更 | SWE 9 | 8 | Code review 的目的（正確性、理解、知識傳遞、一致性）；LGTM 與 approval／ownership 分離；小變更；好的 review comment；作者與 reviewer 的責任；review 延遲的成本；自動化先行；review AI 生成的變更（解釋、測試、範圍）；AI reviewer 的用法與限制 |
| 17 | 17 - Documentation 與 API Contract.md | Documentation、Design Doc 與 API Contract | SWE 10 | 8 | 文件類型（reference、design doc、tutorial、conceptual、landing page）；Diátaxis；docs as code；design doc 結構與 review；API contract（OpenAPI、protobuf）、相容性；文件新鮮度與 owner；AI 生成文件的驗證 |
| 18 | 18 - Deprecation.md | Deprecation：如何安全淘汰舊世界 | SWE 15 | 8 | 為什麼淘汰困難；advisory vs compulsory deprecation；遷移工具與自動化；deprecation 時程與溝通；警告的有效性；追蹤剩餘使用者；Harbor 淘汰舊付款 API |
| 19 | 19 - Version Control 與 Small Batches.md | Version Control、Branches 與 Small Batches | SWE 16 | 8 | VCS 基礎（集中式 vs 分散式）；source of truth；monorepo vs polyrepo；trunk-based development；長期分支的代價；feature flags 取代分支；One Version rule；commit 與 PR 的大小；merge queue |
| 20 | 20 - Dependency 與 Supply Chain.md | Dependency Management 與 Supply Chain | SWE 21 | 8 | 依賴管理為何困難；SemVer 及其限制；diamond dependency；lock files；live at head；vendoring；漏洞掃描、SBOM、SLSA、Sigstore／簽章；typosquatting、dependency confusion；更新自動化（Dependabot／Renovate）；AI 建議套件的幻覺風險（slopsquatting）|
| 21 | 21 - Code Search 與 Large-Scale Changes.md | Code Search、Static Analysis 與 Large-Scale Changes | SWE 17、20、22 | 8 | Code search 的價值；static analysis（Tricorder 原則：低誤報、可行動、整合工作流）；LSC 的定義與流程（Rosie：拆分、自動測試、全域 approver）；codemod／AST 改寫；AI agent 執行大規模變更的流程與驗證 |

## Part 4　Testing、Build 與 Delivery（`Part 4 - Testing Build Delivery/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 22 | 22 - Testing Blueprint.md | Testing Blueprint：Size、Scope 與風險組合 | SWE 11 | 8 | 為什麼寫測試；test size（small／medium／large）vs scope（unit／integration／e2e）；testing pyramid 與反模式（冰淇淋甜筒）；Beyoncé rule；依風險配置測試；測試的成本與信號；AI 生成測試的品質陷阱 |
| 23 | 23 - Unit Testing.md | Unit Testing：保護 Behavior，不綁死 Implementation | SWE 12 | 8 | 可維護的測試；測 behavior 而非 implementation；透過 public API 測試；Given-When-Then；DAMP vs DRY；清晰的失敗訊息；一個測試一個行為；brittle test 的成因；property-based testing；mutation testing |
| 24 | 24 - Test Doubles.md | Test Doubles：Fake、Stub、Mock 的選擇 | SWE 13 | 8 | Fake、stub、mock、spy 的差別；偏好 real → fake → stub/mock 的順序；state vs interaction testing；over-mocking 的問題；fake 的維護與 contract test；dependency injection |
| 25 | 25 - Integration Contract E2E Load Chaos.md | Integration、Contract、E2E、Load 與 Chaos Tests | SWE 14；SRE 17 | 8 | Larger tests 的價值與成本；SUT 的組成；consumer-driven contract test（Pact）；E2E 的 flaky 與維護；load／stress／soak test；chaos engineering 原則；在 production 測試（canary、shadow traffic）；AI agent 的 eval 是新型測試 |
| 26 | 26 - Hermeticity 與 Flakiness.md | Hermeticity、Flakiness 與 Coverage 陷阱 | SWE 11、14 | 8 | Hermetic test；flaky 的成因（時間、順序、共享狀態、網路、並行）與量化；quarantine 與修復流程；coverage 的正確用途與誤用；mutation score；測試資料管理 |
| 27 | 27 - Build Systems 與 Reproducibility.md | Build Systems、Reproducibility 與 Provenance | SWE 18 | 8 | Task-based vs artifact-based build；Bazel 概念（hermetic、remote cache、remote execution）；reproducible build；依賴圖；build cache 的正確性；artifact provenance 與 SLSA level；容器映像建置 |
| 28 | 28 - Continuous Integration.md | Continuous Integration：把錯誤發現在最便宜的位置 | SWE 23 | 8 | CI 的定義（不是只有工具）；presubmit vs postsubmit；fast feedback；test selection；merge queue；broken build 的處理（rollback 優先）；CI 的成本；在 CI 中驗證 AI 產生的變更 |
| 29 | 29 - Continuous Delivery 與 Canary.md | Continuous Delivery、Canary 與 Rollback | SWE 24；SRE 8；WB 16 | 8 | CD vs continuous deployment；release train；feature flags 與 dark launch；canary 分析（統計比較、指標選擇）；blue/green、progressive delivery；rollback vs roll forward；schema migration（expand／contract）；DORA 指標連結 |

## Part 5　SRE 與可靠性模型（`Part 5 - SRE 與可靠性模型/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 30 | 30 - Production 與 SRE.md | Production Environment、Operations 與 SRE | SRE 1、2、3 | 8 | SRE 的定義（軟體工程師做維運）；50% 上限；SRE vs DevOps vs platform engineering；production 環境組成；reliability 是產品功能；embracing risk；SRE 團隊的 engagement 模式預告 |
| 31 | 31 - Toil 與 Automation.md | Toil、Automation 與逐步取得自治 | SRE 5、7；WB 6 | 8 | Toil 的六個特徵；量測 toil；toil 預算；automation 的層次（從 runbook 到自主系統）；自動化的風險（大規模放大錯誤）；何時不該自動化；AI agent 做 toil 的漸進授權 |
| 32 | 32 - SLI SLO SLA 與 Error Budget.md | SLI、SLO、SLA 與 Error Budget | SRE 3、4；WB 2 | 8 | SLI 類型（availability、latency、freshness、correctness、throughput、durability）；event-based vs time-based；measurement point；百分位數（p50／p99）與 latency SLO；SLO 窗口（rolling vs calendar）；九的換算表（99.9% ≈ 43.2 分鐘／30 天）；dependency 可用性相乘；SLA 與 SLO 的差距；error budget policy；低流量服務；AI 服務的 SLI |
| 33 | 33 - Observability.md | Observability：從輸出重建系統內部狀態 | SRE 6；WB 4 | 8 | Monitoring vs observability；metrics、logs、traces、profiles、events；four golden signals、RED、USE；cardinality；OpenTelemetry 與 context propagation；structured logging；exemplars；sampling；dashboard 設計；AI／LLM 應用的 observability（token、成本、prompt trace）|
| 34 | 34 - Alerting 與 Burn Rate.md | Actionable Alerting 與 Multi-window Burn Rate | SRE 6、10；WB 5 | 8 | 好 alert 的條件（緊急、可行動、使用者可見）；symptom vs cause alert；page vs ticket；burn rate 數學；multi-window multi-burn-rate（例如 14.4×1h＋5m、6×6h＋30m）的推導；alert fatigue；alert 的生命週期與檢討 |
| 35 | 35 - Simplicity 與 Change Management.md | Simplicity、Change Management 與 Error-budget Policy | SRE 8、9；WB 7 | 8 | 「boring」系統；accidental vs essential complexity；最小 API；release engineering 原則；變更是大部分事故的來源；變更管理（漸進、可觀測、可回復）；error budget policy 的實際條文範例；freeze 的正確用法 |
| 36 | 36 - Capacity Planning.md | Capacity Planning、Performance 與 Provisioning | SRE 18、21；WB 11 | 8 | Demand forecasting；organic vs inorganic growth；load test 找 safe capacity；N+1／N+2；headroom；Little's Law；排隊理論直覺（utilization 與 latency 的非線性）；autoscaling 的限制；成本與容量；Harbor 雙十一 |

## Part 6　Distributed Systems Reliability（`Part 6 - 分散式系統可靠性/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 37 | 37 - Load Balancing.md | Load Balancing：從入口到 Backend 選擇 | SRE 19、20 | 8 | DNS load balancing；anycast；L4 vs L7；round robin、least connections、weighted、power of two choices；subsetting；health check 與 lame duck；connection draining；sticky session 的代價；跨區域流量管理 |
| 38 | 38 - Overload 與 Load Shedding.md | Queue、Backpressure、Overload 與 Load Shedding | SRE 21、22 | 8 | Overload 的徵兆；queue 何時有害；backpressure；load shedding（依 criticality）；client-side throttling（adaptive throttling 公式）；admission control；graceful degradation；過載時的 latency 與 goodput |
| 39 | 39 - Cascading Failure.md | Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker | SRE 22 | 8 | Cascading failure 機制；deadline propagation；retry 放大（多層 retry 的乘積）；exponential backoff＋jitter；retry budget；circuit breaker；bulkhead；timeout 設定方法；metastable failure；testing cascading failure |
| 40 | 40 - Distributed Consensus.md | Distributed Consensus 與 Critical State | SRE 23 | 8 | 為什麼需要 consensus；CAP 與 PACELC；Paxos／Raft 直覺（leader、quorum、log）；leader election；lease；fencing token；quorum 大小與容錯（2f+1）；效能與地理部署；何時用 etcd／ZooKeeper 而不是自己做 |
| 41 | 41 - Distributed Cron 與 Idempotent Jobs.md | Distributed Cron、Leases 與 Idempotent Jobs | SRE 24 | 8 | Cron 在分散式環境的問題（漏跑、重跑）；at-least-once vs at-most-once；idempotency 設計與 idempotency key；lease 與 leader；重疊執行；job 狀態保存；排程的 thundering herd |
| 42 | 42 - Data Pipelines 與 Integrity.md | Data Pipelines、Provenance、Backup 與 Integrity | SRE 25、26 | 8 | Pipeline 的可靠性（periodic vs continuous、Workflow）；data freshness／correctness SLO；backup vs restore（「沒人要 backup，大家要 restore」）；3-2-1；soft delete；資料完整性檢查；provenance 與 lineage；RPO／RTO；AI 訓練與 RAG 資料管線的 provenance |

## Part 7　Incident、On-call 與學習（`Part 7 - Incident 與學習/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 43 | 43 - On-call 與 Troubleshooting.md | On-call 與 Evidence-driven Troubleshooting | SRE 11、12；WB 8 | 8 | On-call 的合理負荷（每班次事件數、回應時間）；輪值設計；runbook／playbook；補償與健康；troubleshooting 的假設驗證法；常見陷阱（相關非因果、最近變更）；工具；AI 協助值班的方式與限制 |
| 44 | 44 - Incident Command.md | Emergency Response 與 Incident Command | SRE 13、14；WB 9 | 8 | Incident 的宣告與嚴重度；Incident Command System（IC、ops lead、comms lead、scribe）；先止血再修復；溝通節奏與 status page；交接；常見失敗（英雄主義、多頭指揮）；AI 作為 scribe／摘要的用法 |
| 45 | 45 - Blameless Postmortem.md | Blameless Postmortem、Outage Tracking 與 Action Quality | SRE 15、16；WB 10 | 8 | Postmortem 的觸發條件；blameless 與 accountability；timeline 與 contributing factors（避免單一 root cause）；5 whys 的限制；action item 品質（預防、緩解、偵測）；追蹤與關閉；跨事故趨勢分析；分享與學習 |
| 46 | 46 - Game Day 與 Reliable Launch.md | Game Day、Disaster Recovery 與 Reliable Launch | SRE 17、27；WB 18 | 8 | DiRT 與 game day 設計；DR 演練；RTO／RPO 驗證；launch checklist 與 Launch Coordination Engineering；production readiness review；容量、相依、rollback、監控檢查；AI 功能上線的額外檢查（eval、guardrails、kill switch）|

## Part 8　組織落地與 Capstone（`Part 8 - 組織落地與 Capstone/`）

| 章 | 檔名 | 標題 | 對應原書 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 47 | 47 - AI-ready 組織與 SRE Engagement.md | AI-ready Engineering Organization 與 SRE Engagement | SRE 32、33；WB 18、20 | 8 | SRE engagement 模型（embedded、consulting、platform、production readiness）；hand-off 與 hand-back；platform engineering 與 golden path；AI agent 的 autonomy 等級與授權；agent 的身份、權限、審計；eval 與 rollout；組織如何導入 AI 而不失去責任 |
| 48 | 48 - Capstone.md | Capstone：從 Commit 到可靠服務的完整 Operating System | 全書 | 8 | 以 Harbor 的一個新功能（AI 退款助理）走完全書所有環節：design doc／ADR、code review、測試組合、CI／CD、SLO、alert、capacity、overload 防護、on-call、incident、postmortem；每一站的 artifact 範例；全書 12 條核心原則回顧 |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - 讀書路線.md | 21 天核心、28 天完整、依角色（新進工程師、TL、SRE、EM）的路線 |
| B - 原書概念對照.md | SWE、SRE、WB 每章對應到本書哪一章 |
| C - AI Autonomy Maturity Model.md | AI 在開發與維運中的授權等級（L0–L5）、每級的前提、證據、guardrails |
| D - 工程模板.md | ADR、design doc、PR 描述、SLO 文件、error budget policy、runbook、incident 報告、postmortem、launch checklist、agent policy 模板 |
| E - Reliability Math.md | 可用性換算、error budget、burn rate、Little's Law、排隊、retry 放大、quorum、容量公式，每條附算例 |
| F - 術語表.md | 全書術語（英文、中文、一句話定義、首次出現章） |
| G - 延伸閱讀.md | 依主題整理的官方與經典來源 |
