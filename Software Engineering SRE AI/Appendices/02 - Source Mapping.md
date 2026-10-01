# 兩本原書概念覆蓋表

# 兩本原書概念覆蓋表

本書不是逐章翻譯，而是依完整生命週期重組。以下對照可檢查核心概念沒有因重新編排而遺漏。

## Software Engineering at Google

| 原書章節 | 本書主要章節 |
|---|---|
| 1. What Is Software Engineering? | 1、3–7 |
| 2. How to Work Well on Teams | 8–9 |
| 3. Knowledge Sharing | 9–10 |
| 4. Engineering for Equity | 11 |
| 5. How to Lead a Team | 12 |
| 6. Leading at Scale | 13、47 |
| 7. Measuring Engineering Productivity | 14 |
| 8. Style Guides and Rules | 15 |
| 9. Code Review | 16 |
| 10. Documentation | 10、17 |
| 11. Testing Overview | 22、26 |
| 12. Unit Testing | 23 |
| 13. Test Doubles | 24 |
| 14. Larger Testing | 25 |
| 15. Deprecation | 4、18 |
| 16. Version Control and Branch Management | 19 |
| 17. Code Search | 21 |
| 18. Build Systems and Build Philosophy | 27 |
| 19. Critique: Google’s Code Review Tool | 16、28 |
| 20. Static Analysis | 15、21 |
| 21. Dependency Management | 20 |
| 22. Large-Scale Changes | 18、21 |
| 23. Continuous Integration | 28 |
| 24. Continuous Delivery | 29 |
| 25. Compute as a Service | 13、27、47 |

## Site Reliability Engineering

| 原書章節 | 本書主要章節 |
|---|---|
| 1–2. Introduction / Production Environment | 1–2、30 |
| 3. Embracing Risk | 32、35 |
| 4. Service Level Objectives | 32 |
| 5. Eliminating Toil | 30–31 |
| 6. Monitoring Distributed Systems | 33–34 |
| 7. Evolution of Automation | 31、47 |
| 8. Release Engineering | 27–29 |
| 9. Simplicity | 35 |
| 10. Practical Alerting | 34 |
| 11. Being On-Call | 43 |
| 12. Effective Troubleshooting | 43 |
| 13. Emergency Response | 44 |
| 14. Managing Incidents | 44 |
| 15. Postmortem Culture | 45 |
| 16. Tracking Outages | 45 |
| 17. Testing for Reliability | 25、46 |
| 18. Software Engineering in SRE | 30–31、48 |
| 19–20. Frontend / Datacenter Load Balancing | 37 |
| 21. Handling Overload | 36、38 |
| 22. Cascading Failures | 38–39 |
| 23. Distributed Consensus | 40 |
| 24. Distributed Periodic Scheduling | 41 |
| 25. Data Processing Pipelines | 42 |
| 26. Data Integrity | 42、46 |
| 27. Reliable Product Launches | 29、46 |
| 28. Accelerating SREs to On-Call | 43、47 |
| 29. Dealing with Interrupts | 30–31、47 |
| 30. Recovering from Operational Overload | 30–31、47 |
| 31. Communication and Collaboration | 8–13、44 |
| 32. Evolving SRE Engagement Model | 30、47 |
| 33. Lessons from Other Industries | 31、44、46 |
| 34. Conclusion | 47–48 |

## 主動補足的知識

原書假設讀者已有部分背景。本書另外補上：

- Service/request/state/dependency/deployment 的零背景模型。
- API compatibility、migration、idempotency、deadline、backpressure。
- Test oracle、hermetic build、artifact provenance、supply-chain controls。
- SLI/SLO/error-budget 計算與 multi-window burn-rate 直覺。
- Agent context、tools、eval、least privilege、observability 與 incident response。
- Startup、中型公司與大型組織的漸進採用方式。
