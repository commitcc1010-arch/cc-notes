---
title: 延伸閱讀
---

# 附錄 G　延伸閱讀

這份附錄依主題整理值得接著讀的來源，每一項都附一句「讀它能得到什麼」，並標出和本書哪幾章對應。線上資源只列出已查證的官方或原始頁面；書籍只列書名、作者與出版年，請以你取得的版本為準。

讀延伸資料時有一個建議：先讀完本書對應的章、做過動手練習，再去讀原始來源。你會帶著自己的問題去讀，而不是被另一套術語重新淹沒一次。原書的很多段落在你有了 Harbor 的例子之後，會比第一次讀時清楚得多。

## G.1 三本原書

- [Software Engineering at Google](https://abseil.io/resources/swe-book)：Titus Winters、Tom Manshreck、Hyrum Wright 編（2020），官方免費線上版；讀它能看到 Google 如何在數萬名工程師、單一 monorepo 的規模下處理時間、規模與取捨，是本書 Part 1–4 的主要來源。
- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)：原書的前言，說明「programming integrated over time」這個核心觀點與全書的組織方式，適合在第 3 章之後讀。
- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)：Betsy Beyer 等編（2016）的 SRE 書導論，篇幅不長，就能讀到 SRE 的定義、50% 上限、error budget 與「變更是 outage 的主要來源」等核心原則的原始說法（本書第 30 章）。
- [The Site Reliability Workbook — Table of Contents](https://sre.google/workbook/table-of-contents/)：SRE Workbook（2018）的官方目錄；讀它能找到比 SRE 書更貼近非 Google 組織的實作範例，以及範例 SLO 文件、error budget policy 等附錄。

## G.2 工程文化與領導

- [SWE 第 2 章 How to Work Well on Teams](https://abseil.io/resources/swe-book/html/ch02.html)：天才迷思、隱藏工作與 HRT 的原始論述，讀它能看到這些觀念背後的 Google 經驗（本書第 8 章）。
- [SWE 第 3 章 Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)：readability 制度、tech talks、codelab 等做法的細節，讀它能理解 Google 怎麼把 mentoring 規模化（本書第 10 章）。
- [SWE 第 4 章 Engineering for Equity](https://abseil.io/resources/swe-book/html/ch04.html)：原書作者對產品偏誤的反省與案例，讀它能補上本書第 11 章檢查清單背後的動機。
- [SWE 第 5 章 How to Lead a Team](https://abseil.io/resources/swe-book/html/ch05.html)：TL、EM、TLM 的角色與一系列領導反模式，讀它能得到原書對 servant leadership 的完整描述（本書第 12 章）。
- [SWE 第 6 章 Leading at Scale](https://abseil.io/resources/swe-book/html/ch06.html)：Always Be Deciding、Leaving、Scaling 的原始案例，讀它能看到 Google 的 lead 如何處理模糊問題（本書第 13 章）。
- [SWE 第 7 章 Measuring Engineering Productivity](https://abseil.io/resources/swe-book/html/ch07.html)：GSM 與 QUANTS 的原始說明，以及 Google 工程生產力研究團隊如何決定「值不值得量」（本書第 14 章）。
- [DORA](https://dora.dev/)：DORA 研究計畫的官方網站；讀它能取得軟體交付表現指標的最新定義、年度研究報告，以及影響這些指標的能力清單（本書第 14、29 章）。
- 《Accelerate》，Nicole Forsgren、Jez Humble、Gene Kim（2018）：DORA 早期研究的完整說明，讀它能理解四大指標從哪裡來、研究方法是什麼，以及為什麼速度與穩定性可以同時提升。
- 《The Fearless Organization》，Amy C. Edmondson（2018）：心理安全概念的提出者寫給管理者的書，讀它能得到比 Project Aristotle 更完整的研究脈絡與建立心理安全的具體做法（本書第 9 章）。
- 《Team Topologies》，Matthew Skelton、Manuel Pais（2019）：以團隊的認知負荷為核心設計組織與團隊互動模式，讀它能為 platform team 與 golden path 找到組織設計上的理由（本書第 6、47 章）。
- 《The Manager's Path》，Camille Fournier（2017）：從 IC、tech lead 到工程主管每一階段的工作內容，讀它能補充第 12 章「從 IC 到 lead」的職涯面。
- 《An Elegant Puzzle》，Will Larson（2019）：工程組織的規模化、團隊大小與系統性的管理方法，讀它能得到很多可以直接套用的組織設計經驗法則。
- 《Staff Engineer》，Will Larson（2021）：資深 IC 如何在不帶人的情況下發揮影響力，讀它能補充第 13 章「影響力而非權力」與技術策略文件的寫法。
- 《Good Strategy Bad Strategy》，Richard Rumelt（2011）：診斷、指導方針、一致的行動這個策略核心的原始出處，讀它能分辨「真正的策略」與「目標清單」（本書 13.8 節）。

## G.3 Code Health 與可持續的變更

- [SWE 第 8 章 Style Guides and Rules](https://abseil.io/resources/swe-book/html/ch08.html)：Google 的 style guide 如何為讀者最佳化、規則如何被提出與淘汰（本書第 15 章）。
- [SWE 第 9 章 Code Review](https://abseil.io/resources/swe-book/html/ch09.html)：Google 對 code review 目的、LGTM 與 ownership 分離、小變更的原始論述（本書第 16 章）。
- [SWE 第 10 章 Documentation](https://abseil.io/resources/swe-book/html/ch10.html)：把文件當成程式碼對待、依讀者分類文件的原始做法（本書第 17 章）。
- [SWE 第 15 章 Deprecation](https://abseil.io/resources/swe-book/html/ch15.html)：advisory 與 compulsory deprecation 的區分，以及為什麼淘汰比建造更難（本書第 18 章）。
- [SWE 第 16 章 Version Control and Branch Management](https://abseil.io/resources/swe-book/html/ch16.html)：Google monorepo、trunk-based development 與 One Version rule 的原始說明（本書第 19 章）。
- [SWE 第 17 章 Code Search](https://abseil.io/resources/swe-book/html/ch17.html)：Google 內部 code search 的設計取捨與使用情境，讀它能理解為什麼「讀程式碼」值得專門的工具（本書第 21 章）。
- [SWE 第 20 章 Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html)：Tricorder 平台與「低誤報、可行動、整合進工作流」原則的原始出處（本書第 15、21 章）。
- [SWE 第 21 章 Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html)：原書作者認為依賴管理比版本控制更難的理由，以及 SemVer、live at head 的討論（本書第 20 章）。
- [SWE 第 22 章 Large-Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)：Rosie 如何拆分、測試、送審一次改動上萬個檔案的變更（本書第 21 章）。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：審查 AI 生成程式碼時的檢查重點，可以和第 16 章的 review 順序一起使用。
- 《A Philosophy of Software Design》，John Ousterhout（2018）：以「降低複雜度」為核心討論模組與介面設計，讀它能補充第 5、35 章「最小 API」與 accidental complexity 的程式設計面。
- 《Working Effectively with Legacy Code》，Michael Feathers（2004）：在沒有測試的舊程式中安全加入測試與修改的技巧，讀它能把第 24 章的 seam 概念應用到真實的舊系統。
- 《Refactoring》，Martin Fowler（第 2 版，2018）：一套有名字、有步驟的重構手法目錄，讀它能讓小批次變更（第 19 章）在程式碼層級變得可操作。

## G.4 測試

- [SWE 第 11 章 Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)：test size 與 scope、Beyoncé Rule、Google 測試文化的演進史（本書第 22 章）。
- [SWE 第 12 章 Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)：透過 public API 測試、DAMP 而非 DRY 等原則的完整論證與範例（本書第 23 章）。
- [SWE 第 13 章 Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)：fake、stub、mock 的選擇順序與 over-mocking 的原始案例（本書第 24 章）。
- [SWE 第 14 章 Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)：larger test 的組成、SUT 的種類與 Google 的大型測試實務（本書第 25、26 章）。
- [Google Testing Blog — Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)：coverage 參考值與「在 code review 中討論未覆蓋程式碼」的建議，讀它能避免把 coverage 當成 KPI（本書 26.7 節）。
- [State of Mutation Testing at Google](https://research.google/pubs/state-of-mutation-testing-at-google/)：在大規模 codebase 中實際運作 mutation testing 的論文，讀它能看到讓 mutation testing 變得可負擔的工程手法（本書 23.9、26.8 節）。
- [Pact Docs — Can I Deploy](https://docs.pact.io/pact_broker/can_i_deploy)：Pact broker 如何用契約驗證結果判斷一個版本能否部署，讀它能把第 25 章的 contract test 接到 CD pipeline。
- [Principles of Chaos Engineering](https://principlesofchaos.org/)：chaos engineering 的定義與實驗原則，篇幅很短，讀它能檢查自己設計的 chaos 實驗是否有穩態假設與爆炸半徑控制（本書 25.8 節）。
- [SRE 第 17 章 Testing for Reliability](https://sre.google/sre-book/testing-reliability/)：從 SRE 角度看測試，包括設定測試、壓力測試與災難演練（本書第 25、46 章）。
- 《Unit Testing Principles, Practices, and Patterns》，Vladimir Khorikov（2020）：用「對重構的抵抗力」等四個屬性評估 unit test 的好壞，讀它能為第 23 章的 brittle test 診斷提供另一套語言。
- 《Growing Object-Oriented Software, Guided by Tests》，Steve Freeman、Nat Pryce（2009）：以測試驅動設計的完整案例，讀它能理解 mock 原本被設計來解決什麼問題，再對照第 24 章的使用限制。
- 《xUnit Test Patterns》，Gerard Meszaros（2007）：test double 各種名稱的出處與大量測試模式，讀它能查到第 24 章五種 test double 的原始定義。
- 《Chaos Engineering》，Casey Rosenthal、Nora Jones（2020）：多家公司實踐 chaos engineering 的經驗集，讀它能看到從單一實驗走到組織制度的過程。

## G.5 Build、CI 與 CD

- [SWE 第 18 章 Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)：從 task-based 到 artifact-based build 的推導，以及 Bazel 背後的設計哲學（本書第 27 章）。
- [SWE 第 23 章 Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)：Google 的 presubmit／postsubmit、TAP 與處理主線壞掉的方式（本書第 28 章）。
- [SWE 第 24 章 Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)：Google 如何讓發布變得頻繁而無聊，以及 feature flag 與 release train 的角色（本書第 29 章）。
- [SLSA](https://slsa.dev/)：供應鏈安全框架的官方網站，讀它能取得各 build level 的要求與 provenance 格式的規格（本書第 20、27 章）。
- [SRE 第 8 章 Release Engineering](https://sre.google/sre-book/release-engineering/)：SRE 角度的 release engineering 原則，包括 hermetic build 與設定管理（本書第 35 章）。
- [SRE Workbook — Canarying Releases](https://sre.google/workbook/canarying-releases/)：canary 的設計、指標選擇與評估方法的實作細節，讀它能把第 29 章的 canary 分析落實到自己的 pipeline。
- 《Continuous Delivery》，Jez Humble、David Farley（2010）：deployment pipeline 概念的經典來源，讀它能理解「同一個 artifact 一路晉升」等原則的完整推導。
- 《The DevOps Handbook》，Gene Kim、Jez Humble、Patrick Debois、John Willis 等：flow、feedback、持續學習三種實踐的具體案例，讀它能把 CI/CD 放進更大的組織改造脈絡。

## G.6 SLO、Observability 與告警

- [SRE 第 3 章 Embracing Risk](https://sre.google/sre-book/embracing-risk/)：為什麼不追求 100%、如何依服務類型決定風險容忍度，以及 error budget 的原始動機（本書第 30、32 章）。
- [SRE 第 4 章 Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)：SLI、SLO、SLA 的原始定義與選擇指標的方法（本書第 32 章）。
- [SRE Workbook — Implementing SLOs](https://sre.google/workbook/implementing-slos/)：從零開始為服務定義 SLO 的步驟、SLI 規格與 error budget policy 範例，是第 32 章最值得一起讀的原始資料。
- [SRE 第 5 章 Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)：toil 的定義與為什麼要限制它的原始論述（本書第 31 章）。
- [SRE 第 7 章 The Evolution of Automation at Google](https://sre.google/sre-book/automation-at-google/)：自動化的層次與自動化本身造成事故的案例（本書第 31 章）。
- [SRE 第 6 章 Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)：four golden signals、symptom 與 cause 的區分，以及好告警的條件（本書第 33、34 章）。
- [SRE 第 10 章 Practical Alerting](https://sre.google/sre-book/practical-alerting/)：以時間序列資料建立告警規則的實作，讀它能理解規則語言背後的設計考量（本書第 34 章）。
- [SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)：從簡單門檻一路推導到 multi-window multi-burn-rate 的原始說明，讀它能核對第 34 章每一組門檻的來源。
- [SRE 第 9 章 Simplicity](https://sre.google/sre-book/simplicity/)：「boring」系統、最小 API 與刪除程式碼的價值（本書第 35 章）。
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)：traces、metrics、logs 的 API、SDK 與 semantic conventions 官方文件，讀它能把第 33 章的 context propagation 實作到自己的服務。
- 《Implementing Service Level Objectives》，Alex Hidalgo（2020）：整本書專講 SLO 的設計、量測與組織導入，讀它能處理第 32 章篇幅不夠細談的特殊服務與組織阻力。
- 《Observability Engineering》，Charity Majors、Liz Fong-Jones、George Miranda（2022）：以高基數事件資料為核心的 observability 方法，讀它能理解為什麼只靠預先定義的 metrics 回答不了未知的問題（本書第 33 章）。

## G.7 分散式系統可靠性

- [SRE 第 19 章 Load Balancing at the Frontend](https://sre.google/sre-book/load-balancing-frontend/)：DNS 與 virtual IP 層級的流量分配（本書第 37 章）。
- [SRE 第 21 章 Handling Overload](https://sre.google/sre-book/handling-overload/)：依 criticality 的 load shedding 與 client-side adaptive throttling 公式的原始出處（本書第 38 章）。
- [SRE 第 22 章 Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：cascading failure 的觸發機制、retry 與 deadline 的處理方式，以及測試 cascading failure 的建議（本書第 39 章）。
- [SRE 第 23 章 Managing Critical State](https://sre.google/sre-book/managing-critical-state/)：用分散式 consensus 保護 critical state 的動機、效能與部署考量（本書第 40 章）。
- [SRE 第 24 章 Distributed Periodic Scheduling with Cron](https://sre.google/sre-book/distributed-periodic-scheduling/)：Google 如何建立一個可靠的分散式 cron，以及漏跑與重跑的取捨（本書第 41 章）。
- [SRE 第 25 章 Data Processing Pipelines](https://sre.google/sre-book/data-processing-pipelines/)：periodic pipeline 的問題與 Workflow 模型（本書第 42 章）。
- [SRE 第 26 章 Data Integrity](https://sre.google/sre-book/data-integrity/)：資料會用哪些方式遺失、為什麼要以 restore 而非 backup 為目標（本書第 42 章）。
- 《Designing Data-Intensive Applications》，Martin Kleppmann（2017）：複製、分割、交易、一致性與 consensus 的系統性說明，讀它能補足第 40–42 章背後的分散式資料理論。
- 《Release It!》，Michael T. Nygard（第 2 版，2018）：circuit breaker、bulkhead 等穩定性模式的經典來源，讀它能看到這些模式在真實系統故障中的來龍去脈（本書第 38、39 章）。
- 《Database Reliability Engineering》，Laine Campbell、Charity Majors（2017）：把 SRE 原則應用到資料庫維運，讀它能補充第 42 章的備份、還原與 schema 變更實務。

## G.8 事故、On-call 與學習

- [SRE 第 11 章 Being On-Call](https://sre.google/sre-book/being-on-call/)：合理的值班負荷與 operational overload 的處理原則（本書第 43 章）。
- [SRE 第 12 章 Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)：假設驗證式排查的流程與常見陷阱（本書第 43 章）。
- [SRE 第 13 章 Emergency Response](https://sre.google/sre-book/emergency-response/)：幾個真實緊急事件的處理經過與教訓（本書第 44 章）。
- [SRE 第 14 章 Managing Incidents](https://sre.google/sre-book/managing-incidents/)：incident command 的角色分工與一場失控事故的對照案例（本書第 44 章）。
- [SRE 第 15 章 Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)：blameless postmortem 的定義、觸發條件與推廣方式（本書第 9、45 章）。
- [SRE 第 16 章 Tracking Outages](https://sre.google/sre-book/tracking-outages/)：用工具彙整事故資料、找出跨事故趨勢的做法（本書第 45 章）。
- [SRE 第 27 章 Reliable Product Launches at Scale](https://sre.google/sre-book/reliable-product-launches/)：Launch Coordination Engineering 與 launch checklist 的原始內容（本書第 46 章）。
- [SRE 第 32 章 The Evolving SRE Engagement Model](https://sre.google/sre-book/evolving-sre-engagement-model/)：從 PRR 到早期參與與平台化的 engagement 演進（本書第 47 章）。
- 《The Field Guide to Understanding 'Human Error'》，Sidney Dekker（第 3 版，2014）：為什麼「人為疏失」是調查的起點而不是結論，讀它能讓第 45 章的 blameless 寫法有更深的理論基礎。
- 《Seeking SRE》，David N. Blank-Edelman 編（2018）：許多不同公司的 SRE 實踐與觀點，讀它能看到 Google 以外的組織如何調整 SRE 的做法。
- 《Building Secure and Reliable Systems》，Heather Adkins 等（2020）：Google 把安全與可靠性放在同一套設計原則下的做法，讀它能把事故應變與 recovery 延伸到安全事件。

## G.9 AI 工程

- [Introducing DORA's inaugural AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)：DORA 整理哪些組織能力會放大或抵銷 AI 對軟體開發的效益，讀它能把第 14 章的量測方法用在 AI 導入評估。
- [How Google SRE is using agentic AI to improve operations](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)：Google SRE 把 AI agent 應用在維運工作的實務觀點，讀它能對照第 31、43、47 章的授權與邊界設計。
- [OpenAI — Agent evals](https://developers.openai.com/api/docs/guides/agent-evals)：為 agent 設計評估案例與評分方式的官方指南，讀它能把第 25 章「eval 是新型測試」落實成可執行的題組。
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)：使用 coding agent 時如何撰寫 repository 說明、設定任務範圍與驗證方式，可以搭配第 16、19、28 章給 agent 的規則一起讀。
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)：觀測 AI agent 的 prompt、工具呼叫與 token 用量的實務參考（本書 33.10 節）。
- [Microsoft — Incident response for AI systems](https://learn.microsoft.com/en-us/security/zero-trust/sfi/incident-response-ai-systems)：AI 系統本身發生事故時的應變考量，包括證據保存與 containment（本書第 44 章）。
- [OWASP Top 10 for Large Language Model Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)：prompt injection、excessive agency 等 LLM 應用的主要風險清單，讀它能檢查 AI 客服這類 agent 的 guardrails 是否有遺漏（本書第 46、47 章）。
- [NIST — AI Risk Management Framework: Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)：組織層級管理生成式 AI 風險的框架，讀它能把第 47 章的 agent 治理對應到正式的風險管理語言。
- 《AI Engineering》，Chip Huyen（2025）：以基礎模型打造應用的工程方法，涵蓋評估、prompt、RAG、agent 與部署，讀它能補足本書未深入的 AI 產品開發面。
- 《Designing Machine Learning Systems》，Chip Huyen（2022）：機器學習系統從資料到部署與監控的完整生命週期，讀它能理解第 42 章「訓練資料的 provenance」在 ML 系統中的位置。
