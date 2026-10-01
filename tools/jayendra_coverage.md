# Jayendra Patil 全站交叉稽核（2026-10-01）

## 結論

- `post-sitemap.xml` 的快照共有 **520** 篇文章；其中包含早期 Solr、職涯、折扣、其他雲與全部 12 張 AWS 證照內容。
  「全部搬進 SAA/SAP 書」會同時造成範圍污染、重複與過時資訊，因此不能把 URL 數量當品質指標。
- Architecture Patterns index 自稱 58 篇，但當日七個分類表實際列出 **54 個連結**。本書逐項映射這 54 個主題。
- 54 項中，既有正文已完整承接核心責任者標為 `covered`；交叉稽核後新增完整解釋與具體設定者標為
  `supplemented`；只屬 AI/ML specialty 深度者標為 `adjacent`，不冒充 SAA-C03／SAP-C02 必考。
- 技術事實一律以 AWS 官方文件校準。社群頁面的用途是發現高頻主題、比較角度與讀者易錯處，而不是成為
  service behavior 或 exam-version 的最終真相。

## 這次實際補進正文的缺口

| 缺口 | 補入章節 | 補充內容 |
| --- | --- | --- |
| VPC Lattice | 15 | service network、association、auth policy、與 TGW／PrivateLink 的選擇邊界 |
| ALB mTLS | 18 | verify/passthrough、trust store、client certificate 與 application authorization |
| Cloud WAN | 19 | core network、segments、policy version、與 regional TGW 的邊界 |
| Hybrid DNS + DNSSEC | 20 | inbound/outbound endpoint、forward rule、split-horizon、簽章驗證 |
| Verified Access | 24 | identity/device-aware application access 與 VPN/L3 connectivity 的差別 |
| Verified Permissions | 26 | application authorization、Cedar policy store 與 IAM 的責任分界 |
| ENA/EFA/Jumbo Frames | 32 | NIC 能力、placement、MTU、HPC failure/capacity trade-off |
| Lambda SnapStart/Streaming | 36 | startup latency、first-byte latency、snapshot correctness |
| S3 Express One Zone | 42 | directory bucket、zonal endpoint、session auth、單 AZ 取捨 |
| Aurora DSQL | 46 | active-active strong consistency、與 Aurora Global Database 的差別 |
| CloudFormation Guard/Custom Resource | 72 | lint/policy/enforcement/lifecycle 的分界與 idempotency |
| CI/CD Pipeline | 74 | source/build/artifact/deploy 四責任、跨帳號 roles、gates 與 rollback |
| Security Lake/Incident Response | 81 | OCSF、subscriber、證據保存、contain/recover/learn 流程 |

## 官方覆寫規則

1. 社群頁面若宣稱新的 exam code、切換日期或 domain weight，但 AWS 官方 exam guide 未確認，本書不採納。
2. DynamoDB Global Tables 必須區分 MREC 與 MRSC；舊文章的一句「只能 eventual consistency」已不足以描述現況。
3. 服務停售、maintenance mode、Region availability、quota 與 feature support 都必須回官方文件查證。
4. AI/ML、Advanced Networking、Security Specialty 的完整 syllabus 不被算入本書的 SAA/SAP coverage，
   但若其架構觀念直接改善 Solutions Architect 判斷，會以 enrichment 明確標示。

完整 54 項對照由 `tools/aws_architect_external_coverage.py` 維護，並生成到書內附錄。
