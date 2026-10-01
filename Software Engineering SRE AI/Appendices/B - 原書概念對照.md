---
title: 原書概念對照
---

# 附錄 B　原書概念對照

這份附錄把三本原書的每一章，對應到本書的章與節，並用一句話說明本書在原書之外補充了什麼。三本書的代號和各章「本章地圖」裡的寫法相同：

- **SWE**：《Software Engineering at Google: Lessons Learned from Programming Over Time》，Titus Winters、Tom Manshreck、Hyrum Wright 編，O'Reilly，2020。
- **SRE**：《Site Reliability Engineering: How Google Runs Production Systems》，Betsy Beyer、Chris Jones、Jennifer Petoff、Niall Richard Murphy 編，O'Reilly，2016。
- **WB**：《The Site Reliability Workbook: Practical Ways to Implement SRE》，Betsy Beyer、Niall Richard Murphy、David K. Rensin、Kent Kawahara、Stephen Thorne 編，O'Reilly，2018。

三本書都可以在官方網站免費線上閱讀（SWE 在 abseil.io，SRE 與 WB 在 sre.google），連結整理在附錄 G。

## B.1 怎麼讀這張對照表

**對照的方向。** 表格以原書章節為主軸。如果你讀過原書某一章，想知道本書在哪裡處理同一個主題，就查這張表；反過來，本書每章開頭的「對應原書」已經列出它根據的原書章節。

**「主要」與「部分」。** 「本書對應」一欄先列主要處理該主題的章節，再列有相關段落的其他章節。標示「（部分）」的，代表本書只處理了原書該章的一部分概念，通常是因為原書內容和 Google 內部系統綁得很深（例如 SWE 第 19 章的 Critique、SRE 第 2 章的 Borg），或是主題偏向特定組織的經驗分享。這些地方本書會改用業界通用的工具與做法說明同一個原則。

**「本書補充了什麼」。** 這一欄說的是本書相對原書多做了什麼，大致有三類：原書出版後的業界演進（DORA 指標的變化、OpenTelemetry、SLSA、platform engineering、AI 輔助開發）；把 Google 規模的做法換成從 8 人長到 200 人的 Harbor 案例，說清楚「在什麼規模下開始需要」；以及每章「動手寫」的可執行模擬程式。

## B.2 Software Engineering at Google（SWE）

原書分成 Thesis、Culture、Processes、Tools 四部，最後是 Afterword。本書的 Part 1 對應 Thesis，Part 2 對應 Culture，Part 3、4 對應 Processes 與 Tools。

| 原書章 | 原書章名 | 本書對應 | 本書補充了什麼 |
|---|---|---|---|
| 1 | What Is Software Engineering? | 第 3 章（3.2–3.9）；第 4 章（4.2–4.7）；第 5 章（5.2–5.7）；第 6 章（6.2–6.8）；第 7 章（7.2–7.9）；另見 1.6–1.7 | 把原書第 1 章的五個主題（時間、Hyrum's Law、規模、取捨、決策）拆成五章，各自加上成本模擬程式；補上技術債的分類、one-way／two-way door 與完整的 ADR 格式（7.7–7.8） |
| 2 | How to Work Well on Teams | 第 8 章（8.2–8.10）；9.2、9.4 | 把 HRT 與 bus factor 變成可以量測的機制：用 `git log` 估算 bus factor、ownership 地圖，以及用 AI 起草 runbook 來找出「只存在人身上」的知識 |
| 3 | Knowledge Sharing | 第 10 章（10.2–10.9）；16.3（readability 批准） | 補上 onboarding 的設計方法（10.8）、single source of truth 的文件健康檢查程式，以及讓 AI 助理回答內部問題時如何驗證來源 |
| 4 | Engineering for Equity | 第 11 章（11.2–11.8） | 把公平性寫成可測試的需求：色彩對比度檢查、依使用者群體切分的 SLI、風控模型在不同群體的誤擋率，以及一份能帶進設計會議的檢查清單 |
| 5 | How to Lead a Team | 第 12 章（12.2–12.8）；9.7 | 補上 RACI／DACI 的 decision rights 表、SBI 回饋模型、決策瓶頸的排隊模擬，以及為 AI coding agent 指定人類負責人的「授權卡」 |
| 6 | Leading at Scale | 第 13 章（13.2–13.8） | 補上一頁技術策略文件的寫法（診斷、指導方針、一致的行動），以及把「靠某人在 review 時提醒」逐步升級為工具與平台的階梯（13.7） |
| 7 | Measuring Engineering Productivity | 第 14 章（14.2–14.8）；29.9 | 原書的 GSM 與 QUANTS 之外，加入 DORA 指標（含 2024 年起的 rework rate）、SPACE、DevEx，以及評估 AI 工具導入時為什麼不能只看行數或接受率 |
| 8 | Style Guides and Rules | 第 15 章（15.2–15.3、15.7–15.8） | 從「規則」延伸到執行工具：formatter、linter、type checker 的分工、baseline 與 autofix、從 warning 到 blocking 的導入節奏，以及檢查 AI 以 suppression 規避規則 |
| 9 | Code Review | 第 16 章（16.2–16.8） | 加入 review 延遲的成本模型與 merge gate 程式，以及如何 review AI 生成的變更、如何使用 AI reviewer 而不讓它取代 owner 的批准 |
| 10 | Documentation | 第 17 章（17.2–17.7、17.10） | 用 Diátaxis 補充原書的文件分類；新增 API contract（OpenAPI、protobuf）與相容性規則（17.8–17.9）、文件新鮮度 linter，以及 AI 生成文件的驗證 |
| 11 | Testing Overview | 第 22 章（22.2–22.9）；26.7（coverage） | 加入依風險配置測試的方法（22.8）、四種測試組合的模擬比較，以及 AI 生成測試時把 bug 寫成期望值的陷阱 |
| 12 | Unit Testing | 第 23 章（23.2–23.7） | 補上 property-based testing 與 mutation testing（23.8–23.9），並用 `unittest` 實際示範「重構不改測試、改壞行為會被抓到」 |
| 13 | Test Doubles | 第 24 章（24.2–24.9） | 補上 contract test（24.10），讓 fake 和真實依賴遵守同一份契約；用退款重複執行的例子示範 over-mocking 如何隱藏真實錯誤 |
| 14 | Larger Testing | 第 25 章（25.2–25.6）；第 26 章（26.3–26.6） | 加入 consumer-driven contract test（Pact）、load／stress／soak 測試、chaos engineering、在 production 測試，並把 AI agent 的 eval 視為一種新的 larger test |
| 15 | Deprecation | 第 18 章（18.2–18.10）；5.6 | 用 Harbor 淘汰舊付款 API 走完整個流程，補上 brownout、追蹤剩餘使用者與防止新增使用的程式，以及讓 AI 產生遷移 PR 時的語意檢查 |
| 16 | Version Control and Branch Management | 第 19 章（19.2–19.9） | 以 Git 與混合 polyrepo 的情境重述原書的 monorepo 與 One Version 觀點，補上 feature flag、branch by abstraction 與 merge queue（19.10） |
| 17 | Code Search | 第 21 章（21.2–21.3） | 把「找到程式碼」細分成文字搜尋、語意索引、runtime 證據三個層次，說明每一層能回答什麼問題，以及 AI agent 的搜尋摘要需要附哪些證據 |
| 18 | Build Systems and Build Philosophy | 第 27 章（27.2–27.7） | 以 artifact-based build 的原則延伸到 reproducible build、容器映像建置，以及 SLSA 的 provenance（27.8–27.10） |
| 19 | Critique: Google's Code Review Tool | 16.3、16.8（部分） | 本書不介紹 Critique 本身，而是把它體現的原則（LGTM 與 owner 批准分開、靜態分析結果直接出現在 review 中）放進一般 code review 平台的情境說明 |
| 20 | Static Analysis | 21.4；15.4–15.6 | 以 Tricorder 的原則（低誤報、可行動、整合進工作流）指導自訂規則的設計，並說明如何量測一條規則的 effective false positive |
| 21 | Dependency Management | 第 20 章（20.2–20.11） | 原書以依賴管理的理論為主，本書補上供應鏈安全：SBOM、SLSA、簽章、typosquatting、dependency confusion、更新自動化，以及 AI 建議不存在套件的風險 |
| 22 | Large-Scale Changes | 第 21 章（21.5–21.7） | 以一個可執行的 codemod 示範搜尋、分析、改寫、拆分的完整流程，並說明讓 AI agent 執行大規模變更時的分片與驗證方式 |
| 23 | Continuous Integration | 第 28 章（28.2–28.9） | 加入 test selection、culprit finding 與 merge queue 的模擬，「主線壞了先 rollback」的處理原則，以及如何在 CI 中驗證 AI 產生的變更 |
| 24 | Continuous Delivery | 第 29 章（29.2–29.5、29.7） | 補上 canary 的統計比較（29.6）、expand／contract 的 schema migration（29.8），以及用 DORA 指標檢查 delivery 是否真的變好（29.9） |
| 25 | Compute as a Service | 2.5；30.2；36.8–36.9（部分） | 本書不以專章介紹 Google 的 Borg，而是用 Kubernetes 等開源 scheduler 的「期望狀態」概念說明 cluster 與 scheduler，並在容量章節說明 provisioning 與 autoscaling 的限制 |

## B.3 Site Reliability Engineering（SRE）

原書分成 Introduction、Principles、Practices、Management、Conclusions 五部。本書的 Part 5 對應 Principles，Part 6 對應 Practices 中的分散式系統章節，Part 7 對應 Practices 中的事故與上線章節，Part 8 對應 Management。

| 原書章 | 原書章名 | 本書對應 | 本書補充了什麼 |
|---|---|---|---|
| 1 | Introduction | 第 30 章（30.3–30.5）；1.6；35.4；36.3 | 把 SRE 放進整條軟體生命週期（第 1 章），並比較 SRE、DevOps 與 platform engineering（30.6）；用模擬程式示範維運量如何隨服務成長吞掉團隊 |
| 2 | The Production Environment at Google, from the Viewpoint of an SRE | 2.5；30.2 | 把 Google 內部的 Borg、儲存與鎖服務換成 Kubernetes 與雲端的對應物，並補上資料平面與控制平面的區分 |
| 3 | Embracing Risk | 30.7–30.8；32.6 | 加入「多一個 9 值多少錢」的估算方法，並把 reliability 寫進產品需求的格式（30.7） |
| 4 | Service Level Objectives | 32.2–32.5、32.8 | 補上分母的定義與排除規則、measurement point 的選擇、依賴可用性相乘、低流量與批次服務（32.7），以及 AI 服務的 SLI |
| 5 | Eliminating Toil | 31.2–31.4 | 把 toil 的六個特徵變成可以每週記錄的 toil 帳本程式，並說明如何依風險與頻率排出自動化的優先順序 |
| 6 | Monitoring Distributed Systems | 33.2–33.4；34.2–34.3 | 從 monitoring 延伸到 observability：OpenTelemetry、context propagation、cardinality、exemplars、sampling，以及 LLM 應用的 token、成本與 prompt trace（33.10） |
| 7 | The Evolution of Automation at Google | 31.5–31.8 | 加入自動化的風險（錯誤以機器的速度擴散）與「何時不該自動化」，並把 AI agent 處理 toil 的授權設計成逐級取得的階梯（31.9） |
| 8 | Release Engineering | 35.5；29.3；第 27 章 | 補上 progressive delivery、artifact provenance 與 SLSA，以及設定、flag、模型等非程式碼變更的管理 |
| 9 | Simplicity | 35.2–35.3 | 加入系統複雜度的代理指標、feature flag 的組合爆炸，以及每季「刪除日」等讓系統保持簡單的具體做法 |
| 10 | Practical Alerting | 34.4–34.8 | 原書以 Borgmon 示範規則語言，本書改用 Prometheus 風格的規則，並把重點放在 SLO-based burn rate 告警與告警的路由、去重與內容 |
| 11 | Being On-Call | 43.2–43.5；30.5 | 從單一事件的處理時間推導合理負荷，補上從 shadow 到 primary 的培訓階段、交接模板，以及補償與值班者健康 |
| 12 | Effective Troubleshooting | 43.6–43.9 | 加入壓力下常見的認知偏誤（錨定、確認偏誤、相關非因果），並用模擬程式示範依維度切分資料來推翻錯誤假設 |
| 13 | Emergency Response | 44.4；46.2–46.5 | 用 Harbor 雙十一事故示範「先止血再修復」，並把原書的事故案例延伸成可證偽的 game day 與 DR 演練設計 |
| 14 | Managing Incidents | 44.2–44.7 | 補上可以從監控直接判斷的嚴重度表、status page 的溝通節奏，以及用 AI 擔任 scribe 與摘要時的限制；用程式重播一個沒有指揮結構的事故頻道 |
| 15 | Postmortem Culture: Learning from Failure | 45.2–45.7；9.6、9.9 | 補上 blameless 與 accountability 如何同時成立、為什麼沒有單一 root cause、5 whys 的限制，以及 action item 的品質檢查程式 |
| 16 | Tracking Outages | 45.8–45.9 | 加入事故標籤詞彙表的設計，以及用程式做跨事故趨勢分析、找出「知道卻沒做到」的 action items |
| 17 | Testing for Reliability | 25.7–25.9；46.3–46.5 | 加入 chaos engineering 的原則與實驗設計、shadow traffic 與 synthetic probe，以及以實測驗證 RTO 與 RPO 的方法 |
| 18 | Software Engineering in SRE | 36.3（部分）；31.6 | 以原書的 Auxon 為例說明 intent-based capacity planning，並把「SRE 寫軟體」放進自動化層次與平台工程的脈絡 |
| 19 | Load Balancing at the Frontend | 37.3–37.4；37.11 | 補上 anycast、L4 與 L7 的差異，以及跨區域流量切換的 runbook 設計 |
| 20 | Load Balancing in the Datacenter | 37.5–37.10 | 用模擬比較 round robin、least connections、power of two choices 與 subsetting，並補上 health check、lame duck、connection draining 的實作細節 |
| 21 | Handling Overload | 38.2–38.8；36.4；39.4 | 區分 offered load、throughput 與 goodput，加入 queue 策略與 adaptive throttling 的模擬，以及 graceful degradation 的分層設計 |
| 22 | Addressing Cascading Failures | 第 39 章（39.2–39.10）；38.3 | 補上多層 retry 的乘積放大、retry budget、circuit breaker、bulkhead，以及原書出版後才被系統化描述的 metastable failure（39.9） |
| 23 | Managing Critical State: Distributed Consensus for Reliability | 第 40 章（40.2–40.9） | 加入 PACELC、Raft 的直覺說明、fencing token，以及何時直接使用 etcd／ZooKeeper、何時根本不需要 consensus |
| 24 | Distributed Periodic Scheduling with Cron | 第 41 章（41.2–41.8） | 以賣家撥款為例說明 idempotency key 的設計、run ledger 與補跑，並補上排程的 thundering herd 與對帳工作 |
| 25 | Data Processing Pipelines | 42.2–42.4 | 加入 data freshness 與 correctness 的 SLO，並示範每個 job 都是綠燈、輸出卻錯誤的情境 |
| 26 | Data Integrity: What You Read Is What You Wrote | 42.5–42.7 | 補上 3-2-1 備份、RPO／RTO 與還原演練，以及 lineage 與 AI 訓練資料、RAG 知識庫的 provenance（42.8） |
| 27 | Reliable Product Launches at Scale | 46.6–46.8；48.10 | 加入 production readiness review 的證據要求，以及 AI 功能上線的額外檢查：eval、guardrails、kill switch 與 fallback |
| 28 | Accelerating SREs to On-Call and Beyond | 43.4（從 shadow 到 primary）；10.8（部分） | 本書沒有專章，將新人值班的培訓放在輪值設計中說明，並以 Wheel of Misfortune 作為 runbook 的驗證方式 |
| 29 | Dealing with Interrupts | 43.3；31.4；13.5（部分） | 本書沒有專章，從值班負荷的上限、toil 量測與「保護團隊注意力」三個角度處理中斷問題 |
| 30 | Embedding an SRE to Recover from Operational Overload | 47.3–47.4；30.9（部分） | 本書把 embedded 視為 SRE engagement 模式之一，並補上有條件的 hand-off 與 hand-back |
| 31 | Communication and Collaboration in SRE | 47.3；44.5；30.9（部分） | 本書沒有專章，把 SRE 與產品團隊的協作寫成 engagement charter，並在事故溝通中說明對不同受眾的更新節奏 |
| 32 | The Evolving SRE Engagement Model | 47.3–47.5；30.9 | 從 PRR 模式延伸到早期參與與平台化，補上 platform engineering 與 golden path |
| 33 | Lessons Learned from Other Industries | 47.9；9.6（just culture）、9.7（部分） | 把高風險產業「自動化越多，人的責任越要刻意設計」的經驗，套用到導入 AI agent 的組織 |
| 34 | Conclusion | 48.13–48.14 | 用 Harbor 的 AI 退款助理走完全書所有環節，最後整理成 12 條核心原則 |

## B.4 The Site Reliability Workbook（WB）

WB 是 SRE 的實作補充，分成 Foundations、Practices、Processes 三部，另有三個附錄。它的範例比 SRE 更貼近非 Google 的組織，本書在 SLO、告警、canary 等主題大量參考了它的做法。

| 原書章 | 原書章名 | 本書對應 | 本書補充了什麼 |
|---|---|---|---|
| 1 | How SRE Relates to DevOps | 30.6 | 把比較延伸到 platform engineering，說明三者分別回答什麼問題，以及 Harbor 在不同規模的選擇 |
| 2 | Implementing SLOs | 32.3–32.8 | 以 Harbor checkout 的 CUJ 為例寫出完整的 SLI 規格與 SLO 文件，並附可執行的 error budget 計算器 |
| 3 | SLO Engineering Case Studies | 32.7–32.8（部分） | 不重述原書的公司案例，改用 Harbor 的 checkout、search、資料管線與 AI 客服示範不同類型服務的 SLO |
| 4 | Monitoring | 第 33 章（33.2–33.9） | 補上 OpenTelemetry、structured logging、cardinality 控制與 dashboard 的四層結構 |
| 5 | Alerting on SLOs | 34.5–34.7 | 從最天真的門檻規則一路推導到 multi-window multi-burn-rate（14.4×、6×、1× 三組門檻），並用模擬比較不同策略的偵測時間與誤報 |
| 6 | Eliminating Toil | 31.4–31.6 | 把 toil 的量測與處理寫成決策流程與帳本程式，並加入 AI agent 處理 toil 的 shadow mode 評估 |
| 7 | Simplicity | 35.2–35.3 | 用 Harbor 一次設定加 feature flag 的事故說明複雜度如何直接變成可靠性問題 |
| 8 | On-Call | 43.3–43.5 | 補上 operational overload 與 underload 的處理、值班制度提案的結構，以及 AI 協助值班的方式與限制 |
| 9 | Incident Response | 44.3–44.7 | 以 Incident Command System 的角色分工重播雙十一事故，並補上 AI 客服 agent 放大傷害時的 kill switch 流程 |
| 10 | Postmortem Culture: Learning from Failure | 45.4–45.7 | 加入時間線從記憶到證據的整理方式、瑞士起司模型，以及預防、緩解、偵測三類 action items 的品質標準 |
| 11 | Managing Load | 36.9；37.6–37.7；38.6 | 補上 autoscaling 的限制、排程擴容，以及依 criticality 的 load shedding |
| 12 | Introducing Non-Abstract Large System Design | 第 36 章（36.2–36.7、36.11）（部分） | 本書沒有專章介紹 NALSD 方法，但以雙十一容量計畫示範同樣的思路：從需求推到具體的機器數、headroom 與 failure domain |
| 13 | Data Processing Pipelines | 42.2–42.4 | 加入 periodic 與 continuous pipeline 的比較、遲到事件與 watermark，以及沒有請求的服務如何定義 SLO |
| 14 | Configuration Design and Best Practices | 35.4、35.6；2.5（部分） | 本書沒有專章，把設定視為一種需要版本控制、review、驗證與漸進推出的變更 |
| 15 | Configuration Specifics | 27.2（部分） | 本書不介紹特定設定語言，只在 build 輸入的分類中把 configuration 列為必須被宣告與追蹤的一類 |
| 16 | Canarying Releases | 29.4、29.6 | 用程式示範一條會依統計比較自動踩煞車的 rollout，並討論 control 組的選擇與暖機造成的誤判 |
| 17 | Identifying and Recovering from Overload | 38.2–38.9；39.9 | 加入 goodput 的量測與 metastable failure，說明為什麼觸發消失後系統仍然回不來 |
| 18 | SRE Engagement Model | 47.3–47.4；46.7 | 補上依失效影響與維運複雜度的服務分級、engagement charter，以及 production readiness review 的證據要求 |
| 19 | SRE: Reaching Beyond Your Walls | 32.5（依賴與 SLA）；25.5（部分） | 本書沒有專章，把「和外部夥伴共享可靠性」的問題放在依賴可用性相乘、SLO 與 SLA 的距離，以及跨團隊的可執行契約中討論 |
| 20 | SRE Team Lifecycles | 47.2–47.3；30.4 | 以 Harbor 從沒有 SRE、成立 4 人團隊，到 200 人組織約 8 人 SRE 的歷程說明 SRE 團隊在不同階段的工作 |
| 21 | Organizational Change Management in SRE | 47.9；13.6–13.7（部分） | 把組織變革的問題聚焦在導入 AI agent：如何逐步授權、保留稽核與責任，而不是一次全面推行 |
| 附錄 A | Example SLO Document | 32.8（SLO 文件）；附錄 D | 提供 Harbor checkout 的 SLO 文件欄位，以及可以直接套用的模板 |
| 附錄 B | Example Error Budget Policy | 32.6；35.7；附錄 D | 補上 policy 在預算真的耗盡時如何執行、哪些變更可以例外，以及凍結的正確用法（35.8） |
| 附錄 C | Results of Postmortem Analysis | 45.9；35.4 | 不重述 Google 的統計結果，而是說明怎麼用自己組織的 postmortem 資料做跨事故分析 |

## B.5 原書沒有、本書新增的主題

有些主題在三本原書中沒有對應的章，或只是一筆帶過，本書則用完整的章節處理。它們大多是原書出版後才成熟的業界做法，或是 AI 帶來的新問題。

| 主題 | 本書位置 |
|---|---|
| 全書生命週期地圖、通用判斷框架與 AI agent 的組成 | 第 1、2 章 |
| ADR 格式與可逆／不可逆決策 | 第 7 章 |
| DORA（含 rework rate）、SPACE、DevEx | 第 14 章 |
| Diátaxis、API contract 與相容性規則 | 第 17 章 |
| 軟體供應鏈安全：SBOM、SLSA、簽章、slopsquatting | 第 20 章、27.10 |
| Consumer-driven contract test、chaos engineering、AI eval | 第 25 章 |
| OpenTelemetry 與 LLM 應用的 observability | 33.7、33.10 |
| Metastable failure | 39.9 |
| Platform engineering 與 golden path | 30.6、47.5 |
| AI agent 的 autonomy 等級、身份、權限、審計與 eval | 31.9、47.6–47.8、附錄 C |
| 每章的「AI 時代：什麼變了？」 | 各章「專家怎麼想」的前一節 |
