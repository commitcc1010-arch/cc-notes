# AWS Solutions Architect 雙證全攻略

版本基線：2026-10-01。SAA-C03 + SAP-C02；另追蹤已公告但尚未開放註冊的SAP-C03 transition。

## 這本書解決什麼問題？

AWS 認證最容易走偏的地方，是把準備過程變成數百個產品名稱與功能口訣。本書採取相反
路線：每一題先還原成 requirement、state、request/data flow、failure boundary、
operating model 與 evidence，再把它映射到 AWS managed service。這樣不只可以應付
SAA 的單一 workload 選型，也能處理 SAP 的跨帳號、跨 Region、migration、治理與
長期營運取捨。讀者只需要一般程式設計背景；前十章會補上 cloud、network、storage、
database、availability、durability、RTO、RPO 與 shared responsibility 等先備知識。

## 版本與考試範圍

- SAA 以 SAA-C03 exam guide 的 4 domains、14 tasks 為 coverage contract。
- SAP 以目前已發布的 SAP-C02 4 domains、20 tasks 為唯一 task mapping contract；
  SAP-C03 只保留官方公告與未來 guide 更新入口。
- 官方 service list 明確是 non-exhaustive 且可能變動，因此本書將穩定的架構原理與
  易變動的 exam mapping 分開。
- Emerging topics 納入 Bedrock Guardrails、AgentCore Identity 與 Step Functions
  human oversight，但不假裝預測未公開題目。
- 全部 160 道模擬題皆為依據公開 exam domains 原創；不包含、改寫或散布 exam dumps。

## 全書 Blueprint

```text
business requirement
  ↓ classify constraints
identity → network → compute → storage / database
  ↓                       ↓
security controls        integration / event flow
  ↓                       ↓
reliability / performance / cost
  ↓
deployment / operations / observability
  ↓
multi-account enterprise architecture / migration
  ↓
AI governance → end-to-end cases → portable patterns
  ↓
20 diagnostic + 65 SAA + 75 SAP original mock questions
```

每一章先用一個真實場景開場，再給一張能從頭走到尾的架構圖；正文沿著使用者請求、
資料變更或故障發生的順序解釋角色，而不是先展示服務清單。第一次讀完故事後，再打開
名詞與設定工具箱，把理解映射到AWS欄位、真實Config、故障演練與考題。這樣既保留完整
考試深度，也讓只具備一般程式設計背景的讀者能先建立一張連貫的心智地圖。

## COSTAR 解題演算法

1. **Constraints**：圈出 security、RTO/RPO、latency、cost、migration window 與
   operational burden。先辨識 hard constraint，不能讓其他高分抵銷它。
2. **Owner**：問誰擁有 identity、state、encryption key、route、capacity 與 recovery。
3. **Semantics**：確認需要 message、stream、file、object、transaction、cache，
   以及 strong 或 eventual consistency。
4. **Trade-off**：明確說出哪個條件改變時，主要方案會輸給相鄰替代方案。
5. **Availability boundary**：尋找共同依賴、correlated failure 與最大 blast radius。
6. **Recovery and evidence**：說明 retry、rollback、restore、failover、game day 與
   觀測證據，不能把「部署成功」當成「需求已滿足」。

## 建議閱讀路線

### 30 天 SAA

先讀 Part 0–7，接著完成案例 97–103，再做 Diagnostic 與 SAA Mock。錯題不要只記答案
字母，而要記錄漏看的 constraint、誤判的 state owner、沒有辨識的 failure boundary，
以及哪個關鍵詞讓替代方案看似合理。

### SAA 後 45 天 SAP

讀 Part 8–11，將每一個 SAA 單服務答案擴寫成可營運的組合：account/OU 邊界、network
topology、delegated administration、rollout、rollback、evidence、cost allocation 與
migration sequence。完成 75 題 SAP Mock 後，依官方 task coverage matrix 回補弱點。

### 零背景 12 週

每週讀一個 Part；每章先沿著真實設定走一次正常流，再闔上答案畫出故障流。若無法解釋
control plane 與 data plane、availability 與 durability、RTO 與 RPO、queue 與 stream、
authentication 與 authorization 的差異，就回到前置章節，而不是繼續背服務。

## 研究與資料使用原則

技術行為、考試 domains 與 in-scope services 以 AWS 官方文件為準。社群筆記、通過
心得與 re:Post 討論只用於發現高頻卡點、易混淆服務、讀題節奏與學習策略；它們不取代
官方文件，也不被當成出題保證。書中每章保留來源入口，附錄則提供完整 research ledger、
service atlas、task coverage、公式卡與術語表，使讀者可以查證而不必在閱讀正文時反覆
跳離上下文。
