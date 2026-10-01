# 《AWS Solutions Architect 雙證全攻略》寫作規範

所有章節、附錄與模擬考都必須遵守本規範。`tools/check_aws_architect_book.py` 會自動檢查其中可機器驗證的部分。

## 1. 讀者與目標

- **讀者**：會寫程式、但沒有雲端或網路維運背景的初階 engineer。不要假設讀者知道 subnet、TLS、replication、IOPS 是什麼。
- **目標**：讀完後能通過 SAA-C03，並以本書為主教材準備 SAP-C02；同時真的理解「為什麼這樣設計」，能在工作上使用。
- **自給自足（self-contained）**：讀者不需要另外查官方文件就能理解每個知識點。官方連結只是延伸閱讀，不能用「詳見官方文件」取代解釋。
- 引用其他章節一律寫「第 N 章」，不要寫檔名。

## 2. 語言與格式

- 繁體中文（台灣用語：資料庫、伺服器、網路、設定、預設、記憶體、程式）。AWS 服務名稱、功能名稱與專有名詞保留英文（例如 security group、read replica、visibility timeout），第一次出現時附中文解釋。
- 中英文之間加半形空格：「建立一個 VPC 並設定 route table」。中文句子用全形標點。
- 不要為了用英文而用英文：「需求」不必寫 requirement，「成本」不必寫 cost；只有在 AWS 原文術語或考試關鍵字時保留英文。
- 段落短（3–6 句），一段只講一件事。善用條列、表格、圖，但主體仍是有前後因果的敘事文字，不能整章都是條列。
- 新名詞第一次出現時用粗體並立即定義，例如：「**NAT Gateway** 是一個受管的位址轉換服務：它讓 private subnet 裡的機器可以主動連到 Internet，但 Internet 無法主動連進來。」
- 圖一律用 ```` ```text ```` 的 ASCII 圖，圖後要有文字逐步解說圖上的編號或箭頭。
- 程式／設定範例用正確語言標記（```` ```json ````、```` ```yaml ````、```` ```bash ````、```` ```python ````），必須是能在 AWS 上真實使用的語法（IAM policy、CloudFormation、CLI），不要寫偽設定。

## 3. 章節固定結構

```markdown
---
chapter: 5
title: VPC 從零到可上線
part: 1
---

# 第 5 章　VPC 從零到可上線：CIDR、Subnet、Route Table、IGW 與 NAT

> [!abstract] 本章地圖
> **你會學到**：（3–6 點，讀完能「做到」什麼）
> **前置知識**：第 3 章（IP 與 CIDR）
> **考試比重**：SAA ★★★（Domain 1、3）｜SAP ★★☆（Domain 1）

## 5.1 故事：（Wanderly 遇到的問題）
（用 Wanderly 或具體場景開場，說清楚「為什麼需要本章的東西」。2–5 段。）

## 5.2 ～ 5.k（核心概念，由淺入深）
每節大致依序：為什麼需要 → 它怎麼運作（原理）→ 在 AWS 上怎麼做（服務、關鍵設定）→ 例子或圖 → 常見誤解。
節與節之間要有承接句，讓讀者知道「剛解決了什麼、接下來為什麼要談這個」。

## 5.x 比較與選型
（易混淆服務的比較表 + 選型決策流程。）

## 5.x 考試這樣考
（「題目關鍵字 → 想到什麼」表格，至少 8 列；加上 3–6 個常見陷阱。）

## 5.x SAP 加深
（SAP 等級的延伸：跨帳號、規模、治理、遷移。若本章主要就是 SAP 內容，可省略此節。）

## 本章重點整理
（8–15 條，每條一句完整的話，讀者考前只看這節也能複習。）

## 本章練習題
（依大綱題數，格式見第 5 節。）
```

- 節號格式「## 5.3 標題」。最後兩個 H2 必須是「## 本章重點整理」與「## 本章練習題」，順序固定。
- 可用的 callout（Obsidian 語法，builder 會轉成樣式）：
  - `> [!note]` 補充說明
  - `> [!tip] 考試提示` 考試技巧
  - `> [!warning] 常見誤解` 易錯點
  - `> [!sap] SAP 加深` SAP 等級內容
  - `> [!example] 例子` 具體例子
  - `> [!abstract] 本章地圖` 只用在開頭
  - `> [!answer]- 答案：X` 只用在題目
- 字數：核心章正文（不含題目）約 15,000–30,000 字元；Part 0 與案例章 10,000–20,000 字元。深度優先，但不灌水。

## 4. 禁止事項

- **禁止範本化套句**：不得出現同一句型在不同章節重複套用不同名詞的寫法。不得出現以下舊版用語：「證明完成」「四個閱讀支點」「Portable pattern」「故事真的有好結局」「需要時再查」「跟著一個封包走：先從故事開始」「本章其他角色」「第一個交接」「答案翻轉點」。
- 禁止空泛句：「要考慮安全、成本與可用性」這種沒有具體內容的句子不要寫。每句話都要有資訊量。
- 禁止捏造：不確定的數字、限制或功能不要寫。服務限制若為可調整的預設 quota，要寫明「預設值，可申請提高」。已停止或對新客戶關閉的服務（例如 QLDB、Snow 裝置、App Runner）要寫明現況，不要當成推薦方案。
- 禁止虛構 URL：只能使用 `/tmp/aws_old/questions/` 與 `/tmp/aws_old/chapters/` 舊稿中已出現的 AWS 官方連結，或你完全確定存在的 `docs.aws.amazon.com` 頁面。寧可不放連結。
- 禁止收錄或改寫真實考題（exam dumps）。所有題目必須原創。

## 5. 練習題格式（嚴格，checker 會解析）

```markdown
### 練習 5-3｜SAP｜選兩項｜多帳號 IPAM 規劃

一家公司有 50 個 AWS 帳號……（情境 2–6 句，包含明確限制與關鍵字，例如 MOST cost-effective、LEAST operational overhead）

哪兩個步驟能滿足需求？

- A. ……
- B. ……
- C. ……
- D. ……
- E. ……

> [!answer]- 答案：A、C
> **A ✓** 為什麼正確（要點出關鍵字與機制）。
>
> **B ✗** 為什麼錯（具體指出錯在哪個機制或違反哪個限制）。
>
> **C ✓** ……
>
> **D ✗** ……
>
> **E ✗** ……
>
> **考點**：SAP-1.1、SAP-1.4｜IPAM pool 階層與 RAM 共享
```

規則：

1. 標題：`### 練習 <章>-<序>｜<SAA 或 SAP>｜<單選 或 選兩項 或 選三項>｜<考點主題>`。模擬考改為 `### 第 <n> 題｜<SAA 或 SAP>｜<單選…>｜D<domain> <主題>`。
2. 單選 4 個選項（A–D）；選兩項 5 個選項（A–E）；選三項 6 個選項（A–F）。
3. 每個選項都要有 `**X ✓**` 或 `**X ✗**` 解析，且 ✓ 的集合必須等於答案。
4. 最後一行 `**考點**：` 列出官方 task ID（`SAA-1.1`…`SAA-4.4`、`SAP-1.1`…`SAP-4.4`，見下表）與一句考點說明。
5. 品質：
   - 情境要像真實考題：有公司背景、現況、限制與一個最優化目標。SAP 題要有多重限制（跨帳號、既有系統、遷移時程、合規）。
   - 四個選項都必須「看起來可行」：長度相近、使用真實服務、技術上大致合理；錯誤選項要錯在一個關鍵點（違反限制、營運負擔更大、成本更高、功能做不到）。不要放一眼可刪的荒謬選項。
   - 正確答案字母要分散：一章內 A／B／C／D 都要出現，不可集中。
   - 一章約 60% SAA、40% SAP（Part 0 全部 SAA；Part 8 以 SAP 為主），選兩項題約 20%。
   - 解析要教學：說明正確答案的機制，錯誤選項錯在哪、在什麼情況下它反而會是正確答案。
   - 題目必須只靠本書內容就能作答（self-contained）。
6. 可以參考 `/tmp/aws_old/questions/chNNN.md` 的舊題：好題可以改寫修正後收錄，但至少一半要是新題，且不得與其他章重複。

### 官方 task ID

SAA-C03：
- 1.1 Design secure access to AWS resources
- 1.2 Design secure workloads and applications
- 1.3 Determine appropriate data security controls
- 2.1 Design scalable and loosely coupled architectures
- 2.2 Design highly available and/or fault-tolerant architectures
- 3.1 High-performing and/or scalable storage
- 3.2 High-performing and elastic compute
- 3.3 High-performing database
- 3.4 High-performing and/or scalable network
- 3.5 High-performing data ingestion and transformation
- 4.1 Cost-optimized storage
- 4.2 Cost-optimized compute
- 4.3 Cost-optimized database
- 4.4 Cost-optimized network

SAP-C02：
- 1.1 Network connectivity strategies
- 1.2 Prescribe security controls
- 1.3 Reliable and resilient architectures
- 1.4 Multi-account AWS environment
- 1.5 Cost optimization and visibility strategies
- 2.1 Deployment strategy
- 2.2 Business continuity
- 2.3 Security controls based on requirements
- 2.4 Reliability requirements
- 2.5 Performance objectives
- 2.6 Cost optimization strategy
- 3.1 Improve operational excellence
- 3.2 Improve security
- 3.3 Improve performance
- 3.4 Improve reliability
- 3.5 Identify cost optimizations
- 4.1 Select workloads for migration
- 4.2 Optimal migration approach
- 4.3 New architecture for existing workloads
- 4.4 Modernization and enhancements

## 6. 貫穿案例：Wanderly

Wanderly 是一家台灣起家的線上旅遊訂房平台。依章節進度使用：

- Part 0–3：新創期。一個 web 應用（訂房、搜尋、會員）、一個 MySQL、使用者上傳的旅館照片。從一台 EC2 開始，逐步拆成三層架構、Auto Scaling、serverless API、containers。
- Part 4–6：成長期。照片與行程文件放 S3、訂單資料庫、搜尋快取、即時點擊流分析、訂單非同步處理、付款流程（saga）。
- Part 7：上線營運。監控、IaC、部署、DR、成本壓力。
- Part 8：企業期。併購一家擁有舊資料中心（300 台 VM、Oracle、Windows 檔案伺服器）的旅行社，需要多帳號、hybrid 網路、遷移、法規（個資、支付卡 PCI DSS）。
- Part 9–10：全球化與 AI 旅遊助理。

可以在章內另外使用其他具體情境，但開場故事盡量和 Wanderly 有關，讓全書有連續性。

## 7. 準確性重點（常見錯誤，務必正確）

- S3 自 2020-12 起提供 strong read-after-write consistency（所有 PUT、DELETE、LIST）。
- 新建 S3 bucket 預設啟用 Block Public Access、ACL disabled（Bucket owner enforced）、SSE-S3 預設加密。
- CloudFront 存取 S3 用 Origin Access Control（OAC）；OAI 是舊做法。
- NAT Gateway 是 zonal 資源；高可用需每個 AZ 一個並讓該 AZ 的 private subnet 走自己的 NAT。另有 Regional NAT Gateway 新選項時要保守描述或不提。
- Security group 是 stateful、只有 allow；NACL 是 stateless、有 allow 與 deny、依規則號碼由小到大評估。
- SCP 不授予權限、不影響 management account、會影響成員帳號的 root user；service-linked roles 不受 SCP 影響。
- Aurora 儲存層 6 份副本跨 3 AZ；最多 15 個 Aurora Replicas。
- Lambda 最長 15 分鐘、記憶體 128 MB–10,240 MB、/tmp 最大 10,240 MB、同步 payload 6 MB。
- SQS 訊息最大 256 KB（若有更新的上限公告，保守寫「256 KB（考試常用數字）」）、retention 1 分鐘–14 天（預設 4 天）、visibility timeout 預設 30 秒最長 12 小時。
- DynamoDB item 最大 400 KB。
- API Gateway REST API 整合逾時預設 29 秒（Regional／private API 可申請提高）。
- Kinesis Data Streams retention 預設 24 小時，最長 365 天。
- ACM 憑證給 CloudFront 使用必須在 us-east-1。
- EBS volume 綁定單一 AZ；snapshot 存在 S3（Regional）。
- RDS 加密必須建立時啟用；未加密 instance 要用加密 snapshot copy 再 restore。
