---
chapter: 2
title: 雲端是什麼：Region、AZ、Edge 與責任分擔
part: 0
---

# 第 2 章　雲端是什麼：Region、AZ、Edge 與責任分擔

> [!abstract] 本章地圖
> **你會學到**：
> - 用 CapEx／OpEx 與彈性說明雲端和自建機房的根本差異，並分辨 IaaS、PaaS、SaaS
> - 說清楚 Region、Availability Zone、edge location、Local Zones、Wavelength 與 Outposts 各自解決什麼問題，並依合規、延遲、服務可用性與價格四個因素為 workload 挑選 Region
> - 判斷一個 AWS 資源是 global、regional 還是 zonal，知道它的故障範圍和跨 Region 時要做什麼
> - 用 Shared Responsibility Model 判斷某項安全工作是 AWS 還是你的責任
> - 用 Well-Architected Framework 的六個 pillar 檢視一個架構，並說出它們之間常見的衝突
> - 建立一個安全的新帳號：保護 root user、設定預算告警，並了解 data transfer 的計費方向
>
> **前置知識**：第 1 章
> **考試比重**：SAA ★★☆（Domain 1、2、4 的基礎）｜SAP ★☆☆（多 Region 與治理的前置）

## 2.1 故事：機房報價單與一張信用卡

第 1 章教的是怎麼讀題，但刪去法要能用，前提是你看得懂選項裡的名詞。接下來三章補的就是那些名詞，而且從最底層補起：第 1 章六題裡出現的 Region、AZ、受管服務、按用量付費，全部屬於本章。

Wanderly 創辦的第一週，執行長拿到兩份方案。第一份是傳統機房的報價：買四台伺服器、兩台網路設備、一組儲存設備，再租一個機櫃，前期費用一百多萬元，交貨要六週，合約三年。第二份只有一句話：「用公司信用卡開一個 AWS 帳號，今天下午就能把網站架起來。」

選第二份並不需要太多考慮，但阿哲很快發現，「雲端」不只是「別人的電腦」。他第一次建立 EC2 時，Console 要他先選一個 **Region**，接著選一個 **Availability Zone**；建 S3 bucket 時又要選 Region；設定 IAM 時卻沒有 Region 可選。他不知道這些選擇代表什麼，也不知道選錯會怎樣。

更讓他緊張的是帳號本身。註冊帳號用的 email 和密碼可以做任何事，包括刪除所有資源和關閉帳號。如果這組密碼外洩，誰要負責？AWS 不是說它很安全嗎？

這一章回答阿哲的三個疑問：雲端到底改變了什麼？AWS 的全球基礎設施怎麼組成、怎麼選？哪些安全工作是 AWS 做的，哪些是你要做的？

## 2.2 雲端改變了什麼

### 從「買設備」變成「付用量」

自建機房時，公司要先花一大筆錢購買伺服器、網路設備與機房空間，這叫 **CapEx（Capital Expenditure，資本支出）**：一次性投入、分年攤提，買了就是你的資產，用不用都已經付了錢。雲端則是 **OpEx（Operating Expenditure，營運支出）**：按實際用量付費，像水電費一樣每月結算，不用了就不付。

這個差異帶來的不只是會計上的不同，而是工程決策方式的改變：

- **不用再猜容量。** 自建機房要依「三年後的尖峰流量」採購，買少了撐不住，買多了閒置浪費。雲端可以先用小規模，需要時再擴充。
- **彈性（elasticity）。** 容量可以在幾分鐘內隨需求增減。Wanderly 在連假前一週可以把伺服器從 4 台擴到 40 台，連假結束再縮回來，只付那幾天的錢。
- **速度。** 開一台伺服器從「六週交貨」變成「幾分鐘」，實驗新想法的成本大幅降低，失敗了刪掉就好。
- **規模經濟。** AWS 向硬體廠商大量採購、自己設計資料中心與晶片，單位成本比單一公司低。
- **全球化。** 想在歐洲服務使用者，不必在當地找機房，選一個歐洲的 Region 部署即可。
- **不再管理實體機房。** 電力、冷卻、門禁、硬體故障更換都由 AWS 負責。

> [!warning] 常見誤解
> 「雲端一定比較便宜。」不一定。如果 workload 長年穩定、全天滿載，而你又把所有東西都用最貴的方式（On-Demand、高規格、預設儲存類別）跑著，帳單可能比自建機房更高。雲端省錢的前提是**用對計價模式並關掉不用的資源**，這正是 SAA Domain 4 與第 39 章的主題。

### IaaS、PaaS、SaaS：你要管到哪一層

雲端服務依「AWS 幫你管到哪一層」分成三類。分類的意義在於：**你管的層越少，營運負擔越小，但能控制的細節也越少**。

| 類型 | 定義 | 你負責 | AWS 例子 |
|---|---|---|---|
| **IaaS**（Infrastructure as a Service，基礎設施即服務） | 提供虛擬機、網路、儲存等基礎元件 | 作業系統、修補、中介軟體、應用程式、資料 | EC2、EBS、VPC |
| **PaaS**（Platform as a Service，平台即服務） | 提供可直接部署程式或使用的平台，底層 OS 由供應商管 | 應用程式、資料、設定 | Elastic Beanstalk、RDS、Lambda（常被歸為 serverless） |
| **SaaS**（Software as a Service，軟體即服務） | 直接使用完整的軟體 | 使用者帳號、資料與使用方式 | Amazon WorkMail、Amazon Connect、各種線上辦公軟體 |

用 Wanderly 的資料庫來比較：如果在 EC2 上自己安裝 MySQL（IaaS），作業系統修補、MySQL 升級、備份、複寫都是你的工作；改用 RDS for MySQL（受管服務），AWS 負責作業系統與資料庫引擎的修補、自動備份與 failover 機制，你只要決定規格、備份保留天數與維護時段。考試中看到「最少營運負擔」，答案往往就是往表格下方移動一層。

> [!note] 先認識幾個本章會用到的服務名稱
> 後面的章節會逐一深入，這裡只給一句話的定義，讓你讀本章時不會卡住：
> - **EC2**：AWS 的虛擬機器服務；一台 EC2 **instance** 就是一台租來的虛擬機。**AMI** 是啟動 EC2 用的映像檔（作業系統加預裝軟體的範本）。
> - **EBS**：掛在 EC2 上的虛擬磁碟。
> - **S3**：物件儲存，用來放照片、文件、備份等檔案；檔案放在名為 **bucket** 的容器裡。
> - **RDS**：AWS 代管的關聯式資料庫（MySQL、PostgreSQL 等）；**DynamoDB** 是 AWS 的 NoSQL 資料庫。
> - **Lambda**：上傳一段函式、有事件時才執行的 serverless 運算服務。
> - **VPC**：你在 AWS 裡的私有網路；**subnet** 是從 VPC 切出來、位於某個 AZ 的一段網路；**security group** 是套在機器上的虛擬防火牆（第 3、5、6 章）。
> - **IAM**：管理「誰可以對哪些資源做什麼」的身份與權限服務（第 12 章）。
> - **CloudFront**：AWS 的 CDN；**Route 53**：AWS 的 DNS 服務。
> - **ARN（Amazon Resource Name）**：每個 AWS 資源的唯一識別字串，例如 `arn:aws:s3:::wanderly-photos`。

## 2.3 AWS 全球基礎設施：從 Region 到 edge

理解了「雲端是租用別人的基礎設施」之後，下一個問題是：這些基礎設施在哪裡？它們怎麼組織，才能同時做到靠近使用者、撐過故障、遵守各國法規？

```text
                         AWS 全球網路（AWS 自有骨幹）
   ┌───────────────────────────────────────────────────────────────┐
   │                                                               │
   │  Region：ap-northeast-1（東京）        Region：eu-west-1      │
   │  ┌─────────────────────────────────┐   ┌──────────────┐       │
   │  │ ┌──────┐  ┌──────┐  ┌──────┐    │   │  AZ  AZ  AZ  │       │
   │  │ │ AZ-a │──│ AZ-c │──│ AZ-d │ ①  │   └──────────────┘       │
   │  │ └──────┘  └──────┘  └──────┘    │                          │
   │  │   高頻寬、低延遲的專用網路      │                          │
   │  └───────────────┬─────────────────┘                          │
   │                  │ ②                                          │
   │        ┌─────────▼─────────┐                                  │
   │        │ Regional edge cache│ ③                               │
   │        └─────────┬─────────┘                                  │
   │       ┌──────────┼──────────┐                                 │
   │   [Edge 台北] [Edge 香港] [Edge 首爾] ④                       │
   │                                                               │
   │  Region 的延伸：                                              │
   │   Local Zone（某城市，⑤）  Wavelength Zone（電信 5G 網路，⑥） │
   │   Outposts（你的資料中心，⑦）                                 │
   └───────────────────────────────────────────────────────────────┘
                      ▲
                 使用者／你的機房
```

① 一個 Region 由多個 Availability Zone 組成，AZ 之間以 AWS 專用的高速網路相連。② Region 之間以及 Region 與 edge 之間，都走 AWS 自己的全球骨幹網路。③ Regional edge cache 是 CloudFront 在 edge 與 Region 之間的中層快取。④ Edge location 散布在世界各大城市，是 CloudFront、Route 53 等服務最靠近使用者的入口。⑤⑥⑦ 是把 AWS 基礎設施延伸到更靠近使用者或你自己機房的三種方式。以下逐一說明。

### Region：地理與法規的邊界

**Region（區域）** 是 AWS 在某個地理位置建立的一組資料中心叢集，例如東京（`ap-northeast-1`）、新加坡（`ap-southeast-1`）、愛爾蘭（`eu-west-1`）。每個 Region 都有一個代碼，CLI 與 API 都用這個代碼指定位置。

Region 有兩個重要特性：

1. **Region 彼此獨立。** 一個 Region 的故障原則上不會影響其他 Region，這是多 Region 災難復原（第 34、42 章）的基礎。
2. **資料不會自己離開 Region。** 你把資料存在東京的 S3 bucket，除非你主動設定複寫或搬移，否則它不會出現在其他 Region。這讓 Region 成為**資料落地（data residency）**法規的基本控制單位。

另外，部分 Region 屬於獨立的分區（partition），例如 AWS GovCloud（US）與中國的 Region，它們使用不同的帳號體系，與一般商用 Region 隔離。考試偶爾以「政府機關、受特殊法規約束」的情境出現。

### Availability Zone：Region 內的故障隔離單位

**Availability Zone（AZ，可用區域）** 是 Region 內一個或多個獨立的資料中心，擁有各自的電力、冷卻與網路。同一個 Region 的 AZ 彼此相隔一段有意義的距離，讓火災、淹水、停電這類事件不會同時影響兩個 AZ；但距離又近到 AZ 之間的網路延遲只有個位數毫秒，足以做**同步複寫**。AWS 官方文件寫明每個 Region 至少有三個 AZ；不過少數較舊的 Region 對新帳號只開放其中兩個（例如 US West（N. California）），所以實際能用的 AZ 數量要以你帳號裡列出的為準。

AZ 是 AWS 高可用設計的核心：**把資源分散到至少兩個 AZ，就能撐過單一資料中心等級的故障。** 第 1 章練習 1-3 的 Multi-AZ 架構就是這個原則。

AZ 有一個容易忽略的細節：**AZ 名稱在不同帳號中可能對應到不同的實體 AZ。** 在 AWS 最早期的幾個 Region，2025 年 11 月以前建立的帳號，AZ 名稱是逐帳號獨立對應的：你帳號裡的 `us-east-1a` 和另一個帳號的 `us-east-1a`，不一定是同一個實體 AZ。AWS 當初這樣做，是為了避免所有人都擠在名稱為「a」的 AZ。2025 年 11 月起新建立的帳號改為一致的對應，但一個組織裡通常同時有新舊帳號，所以不能假設名稱相同就是同一個位置。若要跨帳號對齊實體位置（例如共享 subnet 或規劃跨帳號的低延遲連線），要使用 **AZ ID**（例如 `apne1-az1`），它在所有帳號中一定代表同一個實體 AZ。

下面的指令列出目前帳號在東京 Region 的 AZ 名稱與 AZ ID 對應：

```bash
aws ec2 describe-availability-zones --region ap-northeast-1 \
  --query "AvailabilityZones[].[ZoneName,ZoneId]" --output table
```

### Edge location 與 Regional edge cache：靠近使用者的入口

Region 的數量有限，但使用者遍布全球。**Edge location（邊緣節點）** 是 AWS 設在世界各大城市的據點，數量遠多於 Region。它們不跑你的 EC2，而是承載特定的全球服務：

- **Amazon CloudFront**：CDN（內容傳遞網路），把內容快取在 edge，讓使用者從最近的節點取得（第 11 章）。
- **Amazon Route 53**：DNS 服務，在 edge 回應 DNS 查詢（第 9 章）。
- **AWS Global Accelerator**：讓使用者從最近的 edge 進入 AWS 骨幹網路，再送到你的應用程式（第 11 章）。
- 掛在 CloudFront 上的 **AWS WAF** 與 **AWS Shield**：在 edge 擋掉攻擊流量（第 16 章）。

**Regional edge cache（區域邊緣快取）** 位於 edge location 與你的 origin（來源伺服器，例如 S3 或 ALB）之間，容量比 edge location 大。當某個 edge 的快取裡沒有使用者要的檔案時，會先問 regional edge cache；那裡也沒有，才回到 origin。這讓不常被存取的內容也能留在快取中更久，減少回源次數。它由 CloudFront 自動使用，你不需要設定。

### Local Zones、Wavelength 與 Outposts：把 AWS 帶得更近

有些 workload 對延遲的要求，連「最近的 Region」都滿足不了；有些則因為法規或資料量，必須留在自己的機房。AWS 提供三種 Region 的延伸：

**AWS Local Zones** 把一部分運算、儲存與網路服務放在 Region 以外的大城市，作為**某個父 Region（parent Region）的延伸**。你可以在 VPC 裡建立一個位於 Local Zone 的 subnet，在裡面開 EC2，讓當地使用者享有個位數毫秒的延遲。典型用途是影片後製、即時遊戲伺服器、要求低延遲的金融應用。Local Zone 只提供部分服務，而且多數 Local Zone 需要先在帳號中啟用（opt-in）才能使用。

**AWS Wavelength** 把 AWS 的運算與儲存放進**電信業者的 5G 網路內部**（Wavelength Zone）。手機或 IoT 裝置的流量不必離開電信網路到 Internet，就能到達你的應用程式，適合行動裝置上的 AR／VR、車聯網、即時影像分析。題目出現「5G」「行動裝置」「電信業者網路」通常就是 Wavelength。

**AWS Outposts** 把 AWS 管理的硬體（整個機櫃或單台伺服器）放進**你自己的資料中心**，在上面執行 EC2、EBS、部分 RDS 等服務，使用和 AWS Region 相同的 API、Console 與工具。Outposts 必須連回它的父 Region，由 AWS 遠端管理與維護硬體。適合「資料必須留在自己機房」「需要和機房內的其他系統極低延遲互動」，但又想用 AWS 一致營運方式的情境。

| 選項 | 在哪裡 | 誰的設施 | 解決什麼 | 典型關鍵字 |
|---|---|---|---|---|
| Region | AWS 選定的地理位置 | AWS | 完整服務、多 AZ 高可用 | 一般部署 |
| Local Zone | Region 以外的大城市 | AWS | 當地使用者的個位數毫秒延遲 | 某城市、影片後製、即時遊戲 |
| Wavelength Zone | 電信業者 5G 網路內 | 電信業者機房 | 行動裝置超低延遲 | 5G、行動、車聯網 |
| Outposts | 你的資料中心 | 你的機房、AWS 的硬體 | 資料留在地端、與地端系統低延遲 | on-premises、資料不能離開機房、一致的 AWS API |
| Edge location | 全球大城市 | AWS | 快取、DNS、入口加速 | 全球使用者、靜態內容 |

> [!tip] 考試提示
> Outposts 不是「離線的 AWS」。它需要和父 Region 保持連線，控制面（建立、管理資源的 API）仍在 Region。題目若要求「完全斷網環境」或「臨時的野外現場運算」，要往 Snow 系列裝置的方向想（第 25 章，注意其新客戶可用性已有變化）。

## 2.4 怎麼選 Region

了解 Region 是什麼之後，第一個實際決策就是：Wanderly 的系統要放在哪個 Region？依重要性排序，通常考慮四個因素。

1. **合規與資料落地。** 如果法規或合約要求個資必須存放在某個國家或地區，這是一票否決的條件，其他因素都要讓步。例如歐盟使用者的資料可能需要留在歐盟境內的 Region。
2. **延遲。** 使用者在哪裡，Region 就盡量靠近哪裡。Wanderly 早期的使用者在台灣與日本，選東京 Region 能讓大多數使用者的往返延遲維持在數十毫秒內。
3. **服務與功能可用性。** 新服務和新的 instance type 通常不會在所有 Region 同時推出。如果架構依賴某個服務（例如特定的 AI 服務或 GPU instance），要先確認目標 Region 有提供。
4. **價格。** 同一個服務在不同 Region 的單價不同，差距可能明顯。在前三個條件都滿足的前提下，才拿價格做最後比較。

> [!example] 例子：Wanderly 的選擇
> Wanderly 的使用者以台灣和日本為主，沒有特定的資料落地要求。AWS 在台灣也有 Region（台北，`ap-east-2`），延遲上對台灣使用者最有利；但新開的 Region 通常還沒有提供所有服務與 instance type，團隊比對後發現自己要用的服務在東京都已齊全、團隊也熟悉，且東京對日本使用者更近。最後選擇東京 Region 作為主要 Region，並記下「等台北 Region 的服務齊全後重新評估」；靜態內容用 CloudFront 從 edge 提供，讓其他地區的使用者也能快速載入。第 34 章會為 Wanderly 建立第二個 Region 作為災難復原，第 42 章再談擴展到歐洲等多個 Region 時的延遲、資料主權與寫入路由考量。

> [!warning] 常見誤解
> 「選最便宜的 Region 就好。」如果最便宜的 Region 離使用者很遠，延遲會影響使用體驗；如果違反資料落地規定，更是不能選。價格是最後的比較因素，不是第一個。

## 2.5 服務的範圍：global、regional 與 zonal

選好 Region 之後，阿哲遇到的下一個困惑是：為什麼有些服務要選 Region、有些要選 AZ、有些什麼都不用選？這反映了每個資源的**範圍（scope）**，也決定了它的故障影響範圍，以及擴展到其他 Region 時要做什麼。

| 範圍 | 意義 | 例子 |
|---|---|---|
| **Global** | 不屬於任何 Region，整個帳號（或全球）共用 | IAM（user、role、policy）、Route 53 hosted zone、CloudFront distribution、AWS Organizations |
| **Regional** | 存在於一個 Region，AWS 自動在該 Region 的多個 AZ 間處理可用性 | S3 bucket、DynamoDB table、Lambda 函式、SQS queue、VPC、AMI、KMS key、Load Balancer（跨你選的 AZ） |
| **Zonal** | 存在於單一 AZ，該 AZ 故障就受影響 | EC2 instance、EBS volume、subnet、NAT Gateway |

這張表有幾個直接的設計後果：

- **Zonal 資源要自己做跨 AZ。** 一台 EC2 只在一個 AZ，所以要跨 AZ 高可用，就得在多個 AZ 各放一份（第 18 章）。EBS volume 只能掛給同一個 AZ 的 EC2；要移到其他 AZ，必須先建立 snapshot 再還原。
- **Regional 資源通常已經跨 AZ。** S3 與 DynamoDB 會自動把資料存放在 Region 內的多個 AZ，你不需要為 AZ 故障額外設計。
- **擴展到新 Region 時，regional 與 zonal 資源都要重建或複製**，global 資源則不必。例如 Wanderly 要在新加坡也部署一份系統：AMI 要複製到新加坡、VPC 和 security group 要重新建立、S3 資料要設定複寫，但 IAM role 可以直接沿用。

> [!note] S3 bucket 名稱是全球唯一的
> S3 bucket 是 regional 資源（資料存放在你選的 Region），但 bucket **名稱**在所有 AWS 帳號中必須唯一。這是因為 bucket 名稱會成為網址的一部分。因此 S3 在 Console 上看起來像 global 服務，但資料確實只在一個 Region。

### Control plane 與 data plane

AWS 服務內部通常分成兩部分：

- **Control plane（控制面）**：負責建立、修改、刪除資源的 API，例如 `RunInstances`（啟動 EC2）、`CreateBucket`、修改 security group。
- **Data plane（資料面）**：負責資源實際運作，例如已經在跑的 EC2 處理請求、S3 回應 `GetObject`、DNS 回應查詢。

這個區分之所以重要，是因為**data plane 的可用性設計通常高於 control plane**，而且 data plane 被刻意設計成不依賴 control plane。換句話說，在某些故障期間，你可能「無法啟動新的 EC2」，但「已經在跑的 EC2 繼續正常服務」。

由此衍生出一個重要的設計原則：**static stability（靜態穩定）**。系統在故障時不應該需要呼叫 control plane 才能恢復。例如 Wanderly 在兩個 AZ 各跑 4 台 EC2、每個 AZ 都足以單獨承擔全部流量；當一個 AZ 故障時，另一個 AZ 不需要「緊急啟動新機器」就能撐住。相反地，如果每個 AZ 只放 2 台、打算故障時再靠 Auto Scaling 補上，就依賴了故障期間可能受影響的 control plane。第 34 章會再深入這個主題。

一些 global 服務的 control plane 集中在單一 Region，例如 AWS 的 fault isolation 白皮書指出，IAM 與 Route 53 的 control plane（建立與修改 user、role、DNS 記錄的 API）位於 `us-east-1`，CloudFront 也是；但它們的 data plane（驗證請求、回應 DNS 查詢、執行 health check）分散在各 Region 與 edge。所以 DR 計畫應該避免在故障時才去「修改 DNS 記錄或建立 IAM 資源」，而是事先建好，故障時靠 data plane 的機制（例如 Route 53 health check 自動 failover）切換。

## 2.6 Shared Responsibility Model：誰負責哪一塊安全

回到阿哲的擔心：AWS 說它很安全，那帳號被盜用時誰負責？答案是 **Shared Responsibility Model（責任分擔模型）**：

- **AWS 負責「雲端本身的安全」（security OF the cloud）**：資料中心的實體安全、硬體、網路基礎設施、虛擬化層，以及受管服務底層的軟體。
- **你負責「你放在雲端上的東西的安全」（security IN the cloud）**：你的資料、帳號與權限、網路設定、加密選擇，以及你自己管理的作業系統與應用程式。

分界線不是固定的，**會隨服務類型移動**。你使用的服務越接近 SaaS，AWS 負責的部分越多：

| 責任 | EC2（IaaS） | RDS（受管資料庫） | Lambda（serverless） | S3（受管儲存） |
|---|---|---|---|---|
| 實體設施、硬體、虛擬化 | AWS | AWS | AWS | AWS |
| 作業系統修補 | **你** | AWS | AWS | AWS |
| 資料庫引擎／執行環境修補 | **你**（自裝軟體） | AWS 執行修補，你決定維護時段與版本升級 | AWS | AWS |
| 應用程式程式碼與相依套件 | **你** | 不適用 | **你** | 不適用 |
| 網路存取控制（security group、公開與否） | **你** | **你** | **你**（是否放進 VPC、誰能呼叫） | **你**（bucket policy、Block Public Access） |
| IAM 權限 | **你** | **你** | **你** | **你** |
| 資料加密的選擇與金鑰管理 | **你** | **你** | **你** | **你** |
| 資料本身與備份策略 | **你** | **你**（AWS 提供自動備份功能，保留設定由你決定） | **你** | **你** |

從表格可以看到一個不變的事實：**無論用什麼服務，資料、IAM 權限與存取設定永遠是你的責任。** AWS 提供工具（加密、Block Public Access、IAM），但要不要用、怎麼設定由你決定。一個 S3 bucket 被設成公開而外洩資料，是客戶的設定問題，不是 AWS 的安全漏洞。

> [!warning] 常見誤解
> 「用了受管服務，安全就全交給 AWS 了。」RDS 會幫你修補作業系統，但如果你把資料庫設為 publicly accessible、security group 開放 `0.0.0.0/0`、密碼設成 `password123`，被入侵仍是你的責任。受管服務減少的是**基礎設施層**的工作，不會減少你在**設定與資料層**的責任。

延伸閱讀：[AWS Well-Architected Security Pillar：Shared responsibility](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/shared-responsibility.html)。

## 2.7 Well-Architected Framework：六個評估面向

知道了誰負責什麼，下一個問題是：怎樣才算一個「好的」架構？AWS 把多年的架構審查經驗整理成 **AWS Well-Architected Framework**，用六個 **pillar（支柱）** 檢視一個 workload：

| Pillar | 關心的問題 | 本書主要章節 |
|---|---|---|
| Operational Excellence（卓越營運） | 能不能有效運作、監控、持續改善？變更是否小而可回復？ | 第 36–38 章 |
| Security（安全） | 身份、權限、資料保護、偵測與事件回應是否到位？ | 第 12–16 章 |
| Reliability（可靠性） | 故障時能否自動恢復？容量是否足夠？DR 是否演練過？ | 第 33–35 章 |
| Performance Efficiency（效能效率） | 是否用對資源類型與規模？能否隨需求調整？ | 第 17–31 章 |
| Cost Optimization（成本最佳化） | 是否只為需要的東西付費？是否知道錢花在哪裡？ | 第 39 章 |
| Sustainability（永續） | 是否以最少的資源與能源達成需求？ | 散見各章 |

這六個面向經常互相拉扯：多一個 AZ 提升可靠性，但成本增加；把資料庫換成更大的 instance 提升效能，但可能浪費。SAA 的題目本質上就是「在某個 pillar 的硬條件下，最佳化另一個 pillar」，這正是第 1 章講的「硬條件 + 最佳化目標」。

**AWS Well-Architected Tool** 是 Console 裡的免費工具，讓團隊針對一個 workload 逐題回答各 pillar 的問題，找出高風險項目（high-risk issues）並記錄改善進度。SAP Domain 3「持續改善既有方案」的題目常把它當成找出改善點的起點（第 38、46 章）。

延伸閱讀：[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)。

## 2.8 AWS 帳號與 root user

前面講的都是概念，現在回到阿哲手上那個剛註冊的帳號。

### 帳號是什麼

**AWS 帳號（AWS account）** 是資源、計費與安全的基本容器：你建立的每個資源都屬於某個帳號，費用也記在那個帳號的帳單上。帳號以一個 12 位數的 account ID 識別。帳號之間預設完全隔離：A 帳號的使用者無法看到 B 帳號的資源，除非明確授權（第 13 章）。這種隔離讓「一個環境一個帳號」成為企業的標準做法（第 14、40 章）。

### Root user：權力最大、最不該使用

註冊帳號用的 email 與密碼，登入後就是 **root user（根使用者）**。它對帳號擁有完全的權限，而且**無法用 IAM policy 限制**（唯一的例外是：帳號加入 AWS Organizations 成為成員帳號後，組織的 **SCP（Service Control Policy，服務控制政策，一種由母公司帳號套在成員帳號上的權限上限）** 可以限制它，第 14 章）。有些事只有 root user 能做，例如關閉帳號、修改帳號的 email 與 root 密碼、變更 AWS Support 方案、為 S3 bucket 啟用 MFA delete，以及當某個 bucket policy 把所有人都擋在外面時修復它。

正因為權力這麼大，保護 root user 是建立帳號後的第一件事：

1. **為 root user 啟用 MFA（多因素驗證）**，最好使用硬體安全金鑰或 passkey。
2. **不要為 root user 建立存取金鑰（access key）**；如果已經有，刪除它。
3. **日常工作不用 root user**。建立具備管理權限的身份給自己使用：單一帳號可用 IAM，多帳號環境則建議使用 IAM Identity Center（第 13 章）。
4. 使用一個由團隊共同管理的 email 信箱註冊帳號，而不是某個員工的個人信箱，並妥善保管 root 密碼與 MFA 裝置。
5. 在帳號設定中填寫正確的聯絡人資訊（帳單、安全、營運），確保 AWS 能通知到你。

> [!tip] 考試提示
> 題目若問「保護 root user 的最佳做法」，答案通常是「啟用 MFA、刪除 root 存取金鑰、日常使用 IAM 或 IAM Identity Center 的身份」。「把 root 密碼分享給所有管理員」「用 root user 的存取金鑰跑自動化腳本」都是錯的。

## 2.9 計費基本觀念：按用量付費與 data transfer 方向

### 按用量付費的三大成本

AWS 的帳單幾乎都可以歸成三類：

- **運算**：EC2 依 instance 執行時間計費，Lambda 依請求次數與執行時間（以記憶體大小加權）計費。
- **儲存**：依存放的資料量與時間計費（例如每 GB-月），不同儲存類別單價不同；有些還有存取請求與取回費用。
- **資料傳輸（data transfer）**：依資料流動的方向與距離計費。這一項最容易被新手忽略。

### Data transfer 的方向

AWS 的資料傳輸費用有幾個基本規則，考試與實務都很常用：

| 流量方向 | 一般情況 |
|---|---|
| 從 Internet **進入** AWS | 免費 |
| 從 AWS **送出**到 Internet | 收費（依 GB，量越大單價越低） |
| 同一個 AZ 內，用 private IP 傳輸 | 通常免費 |
| **跨 AZ**（同一 Region 內） | 收費（雙向各計） |
| **跨 Region** | 收費 |
| 從 AWS 經 CloudFront 送給使用者 | 由 CloudFront 計費；從 AWS origin 到 CloudFront 的回源流量不收 data transfer out 費用 |

這張表直接影響架構設計：把大量資料傳給使用者時，透過 CloudFront 快取能減少 origin 的負擔與傳輸成本；需要高可用時跨 AZ 是必要的，但「無謂的跨 AZ 往返」會累積費用；跨 Region 複寫要把傳輸費算進去。第 5 章提到的 NAT Gateway 處理費與第 39 章的完整成本分析，都建立在這幾條規則上。

### 從第一天開始控制成本

新帳號最常見的意外是「忘了關掉的資源」或「誤設定造成的大量流量」。建帳號後立即做兩件事：

- 用 **AWS Budgets** 建立一個每月預算，設定在實際或預測花費超過門檻時寄信通知。
- 開啟 **Cost Explorer** 觀察每日費用與各服務的分布（第 39 章）。

AWS 為新帳號提供 **Free Tier（免費方案）**。目前的形式是：新帳號會拿到一筆可在 6 個月內使用的抵用額度（credits），並可選擇「Free plan」（只能用部分服務、額度用完或 6 個月到期前不會產生費用）或「Paid plan」（可用所有服務，超出額度的用量照常計費）；另外有 30 多個服務在每月額度內一直免費。這些規則過去調整過、之後也可能再變，使用前請在 AWS 官方 Free Tier 頁面確認，不要假設某個服務一定免費，Budgets 告警仍然要設。

## 2.10 怎麼操作 AWS：Console、CLI、SDK 與 API

最後一個基礎觀念：你怎麼對 AWS「下指令」？無論用哪一種方式，背後都是同一套 **API**：

- **AWS Management Console**：瀏覽器介面，適合學習、探索與一次性的操作。
- **AWS CLI**：命令列工具，適合腳本與自動化。
- **AWS SDK**：各程式語言的函式庫（Python 的 boto3、JavaScript、Java、Go 等），讓應用程式直接呼叫 AWS 服務。
- **Infrastructure as Code**：CloudFormation、CDK 等工具，以程式碼描述整個架構（第 37 章）。

```text
 Console（瀏覽器）   CLI（終端機）   SDK（應用程式）   CloudFormation
        │                 │                │                │
        └─────────────────┴───────┬────────┴────────────────┘
                                  ▼
                 HTTPS 請求 + 簽章（以憑證計算的 SigV4 簽章）
                                  ▼
                  AWS 服務的 API endpoint（例如 ec2.ap-northeast-1.amazonaws.com）
                                  ▼
                  IAM 驗證身份並評估權限 → 允許才執行
```

圖中每一種工具最後都送出一個帶有簽章的 HTTPS 請求。簽章用你的**憑證（credentials）**計算，AWS 用它確認「你是誰」，再由 IAM 判斷「你能不能做這件事」（第 12 章）。大多數服務的 API endpoint 是 Region 專屬的，這也是為什麼 CLI 指令要指定 `--region`。

這代表兩件事：第一，**在 Console 能做的事，用 CLI 和 SDK 也能做**，所以自動化不受限制。第二，**憑證的保護至關重要**。在自己的電腦上，CLI 會從設定檔或環境變數讀取憑證；在 AWS 上執行的程式（EC2、Lambda、ECS），應該使用 IAM role 提供的臨時憑證，而不是把存取金鑰寫進程式（第 1 章練習 1-4）。

設定好 CLI 後，第一個值得執行的指令是確認「我現在是誰」：

```bash
aws sts get-caller-identity
```

它會回傳目前憑證對應的帳號 ID 與身份 ARN，可用來確認不是不小心用了錯誤的帳號或 root user。若不想在自己的電腦安裝 CLI，Console 內建的 **AWS CloudShell** 提供一個已登入、已安裝 CLI 的瀏覽器終端機。

## 2.11 比較與選型

### 這個 workload 該部署在哪裡？

```text
資料或處理是否必須留在自己的資料中心？
├─ 是 → 能連回 AWS Region 嗎？
│        ├─ 能 → AWS Outposts
│        └─ 不能（斷網／野外現場）→ 邊緣裝置方案（第 25 章）
└─ 否 → 使用者是否在行動 5G 網路上，且需要超低延遲？
         ├─ 是 → AWS Wavelength
         └─ 否 → 是否需要在某個沒有 Region 的城市達到個位數毫秒延遲？
                  ├─ 是 → AWS Local Zone（父 Region 的延伸）
                  └─ 否 → Region（依合規 → 延遲 → 服務 → 價格挑選）
                           └─ 全球使用者的靜態或可快取內容 → 加上 CloudFront（edge）
```

### 容易混淆的概念

| 概念 A | 概念 B | 差別 |
|---|---|---|
| Region | AZ | Region 是地理與法規邊界；AZ 是 Region 內的故障隔離單位 |
| AZ 名稱 | AZ ID | 名稱在不同帳號可能對應不同的實體 AZ；AZ ID 在所有帳號代表同一個實體 AZ |
| Edge location | Regional edge cache | 前者最靠近使用者；後者是 CloudFront 的中層快取，容量更大 |
| Local Zone | Outposts | 前者在 AWS 的設施；後者在你的資料中心 |
| Local Zone | Wavelength | 前者服務某個城市的一般網路使用者；後者在電信 5G 網路內 |
| Control plane | Data plane | 前者建立與修改資源；後者處理實際流量，可用性設計更高 |
| CapEx | OpEx | 前者先買設備；後者按用量付費 |
| Security OF the cloud | Security IN the cloud | 前者是 AWS 的責任；後者是你的責任 |

## 2.12 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 法規要求資料存放在某國／某地區 | 選該地區的 Region，且不設定跨 Region 複寫到境外 |
| 撐過資料中心等級的故障 | 跨至少兩個 AZ 部署 |
| 撐過整個地區的災難 | 多 Region（第 34、42 章） |
| 某城市的使用者需要個位數毫秒延遲，附近沒有 Region | AWS Local Zones |
| 5G、行動裝置、電信業者網路 | AWS Wavelength |
| 資料必須留在自己機房，但想用相同的 AWS API 與工具 | AWS Outposts |
| 全球使用者存取靜態內容很慢 | CloudFront（edge location 快取） |
| 跨帳號對齊同一個實體 AZ | 使用 AZ ID，而不是 AZ 名稱 |
| 誰負責修補 EC2 的作業系統 | 客戶 |
| 誰負責修補 RDS 的作業系統 | AWS（客戶選維護時段） |
| 保護 root user | MFA、不建立 root 存取金鑰、日常使用 IAM／IAM Identity Center |
| 故障時不依賴啟動新資源也能撐住 | Static stability：事先在每個 AZ 預留足夠容量 |
| 流量季節性波動，不想為尖峰購買設備 | 雲端彈性與按用量計價（Auto Scaling，第 18 章） |
| 降低資料傳輸成本 | 避免不必要的跨 AZ／跨 Region 流量；用 CloudFront 提供內容 |

**常見陷阱**：

1. 把「多個 EC2」誤認為「高可用」：如果它們都在同一個 AZ，AZ 故障時會一起失效。
2. 以為使用受管服務後，資料加密、權限與網路暴露就是 AWS 的責任。
3. 以為 IAM role 或 policy 要在每個 Region 重建：IAM 是 global 的。反過來，以為 AMI、security group 可以直接在其他 Region 使用：它們是 regional 的。
4. 以為 Outposts 可以在完全斷網的環境運作：它需要連回父 Region。
5. 以為所有 data transfer 都免費或都收費：進入 AWS 通常免費，送出到 Internet、跨 AZ、跨 Region 才收費。
6. 用 root user 的存取金鑰跑自動化，或讓多人共用 root 登入。

## 2.13 SAP 加深：從一個帳號到一個組織

SAA 的題目大多假設一個帳號、一個 Region；SAP 則把本章的每個概念放大：

- **Region 選擇變成組織政策。** 企業會用 SCP 限制所有成員帳號只能在核准的 Region 建立資源，以落實資料主權（第 14、43 章）。注意 global 服務（例如 IAM、Route 53、CloudFront）沒有 Region，這類 SCP 通常要把它們排除在限制之外，否則會誤擋必要操作。
- **AZ ID 變成跨帳號設計的基礎。** 網路帳號透過 AWS RAM 把 subnet 共享給其他帳號時，或規劃跨帳號的低延遲服務時，要以 AZ ID 溝通，才能確保大家說的是同一個實體位置（第 41 章）。
- **Shared Responsibility 變成內部分工。** 在多帳號組織中，平台團隊負責 landing zone、集中日誌與防護規則，應用團隊負責自己的 workload，等於在公司內部再畫一次責任分界（第 40 章）。
- **Static stability 變成多 Region 設計原則。** 多 Region DR 的設計要避免故障當下才去呼叫集中在單一 Region 的 control plane，例如事先建立好 DNS 記錄與 health check，或使用 Route 53 Application Recovery Controller 這類專為故障切換設計的 data plane 機制（第 34、42 章）。
- **計費變成治理問題。** 多帳號下要用 consolidated billing、cost allocation tags 與 Budgets 讓每個團隊看見自己的花費（第 39、43 章）。

## 本章重點整理

- 雲端把採購設備的 CapEx 轉為按用量付費的 OpEx，核心價值是彈性、速度與不必預先猜測容量，但不保證一定比較便宜。
- IaaS、PaaS、SaaS 的差別在於你要管理到哪一層；越往受管服務移動，營運負擔越小。
- Region 是地理與法規邊界，彼此獨立，資料不會自動離開 Region。
- AZ 是 Region 內獨立電力、冷卻與網路的資料中心群組，彼此距離夠遠以隔離災害、又夠近以支援同步複寫；跨至少兩個 AZ 部署是高可用的基礎。
- AZ 名稱在不同帳號可能對應到不同的實體 AZ（尤其是較早建立的帳號），跨帳號要對齊實體位置時使用 AZ ID。
- Edge location 承載 CloudFront、Route 53、Global Accelerator 等全球服務；regional edge cache 是 CloudFront 的中層快取。
- Local Zones 把 Region 延伸到特定城市，Wavelength 延伸到電信 5G 網路，Outposts 延伸到你的資料中心且必須連回父 Region。
- 選 Region 的順序是合規、延遲、服務可用性，最後才是價格。
- 資源分成 global（IAM、Route 53、CloudFront）、regional（S3、DynamoDB、Lambda、VPC、AMI）與 zonal（EC2、EBS、subnet、NAT Gateway）；zonal 資源要自己做跨 AZ。
- Data plane 的可用性設計高於 control plane；static stability 原則要求故障時不依賴建立新資源就能撐住。
- Shared Responsibility Model 中，AWS 負責雲端本身的安全，你負責放在雲端上的資料、權限與設定；分界會隨服務類型移動。
- Well-Architected Framework 有六個 pillar：卓越營運、安全、可靠性、效能效率、成本最佳化、永續。
- Root user 要啟用 MFA、不建立存取金鑰、日常不使用；日常操作使用 IAM 或 IAM Identity Center 的身份。
- 資料進入 AWS 通常免費，送出到 Internet、跨 AZ、跨 Region 才收費；新帳號應立即設定 AWS Budgets 告警。
- Console、CLI、SDK 與 IaC 最後都呼叫同一套經簽章的 API；在 AWS 上執行的程式應使用 IAM role 的臨時憑證。

## 本章練習題

### 練習 2-1｜SAA｜單選｜依合規選擇 Region

Wanderly 準備在歐洲推出服務。法務部門指出，依當地法規與合約，歐盟使用者的個人資料必須存放在歐盟境內。行銷團隊則發現，美國某個 Region 的 EC2 單價比歐洲的 Region 便宜，而且公司的工程師大多熟悉那個 Region。歐洲使用者希望網站反應迅速。

團隊應該如何選擇部署個人資料的 Region？

- A. 選擇單價最便宜的美國 Region，並用 CloudFront 讓歐洲使用者也能快速存取
- B. 選擇美國 Region 作為主要 Region，並設定把資料每天備份一份到歐洲 Region
- C. 選擇位於歐盟境內、提供所需服務的 Region 存放個人資料，且不設定跨 Region 複寫到歐盟以外
- D. 選擇工程師熟悉的 Region，並對所有個人資料啟用加密，以符合法規

> [!answer]- 答案：C
> **A ✗** CloudFront 能降低延遲，但個人資料的權威存放位置仍在美國，違反資料必須留在歐盟的硬條件。價格是選 Region 時最後才比較的因素。
>
> **B ✗** 主要資料存在美國，備份放在歐洲也無法讓「存放位置」符合要求；方向剛好相反。
>
> **C ✓** 資料落地要求是一票否決條件，必須先滿足。選擇歐盟境內的 Region，同時能就近服務歐洲使用者，再確認所需服務都有提供；也要避免設定把資料複寫到境外的功能。
>
> **D ✗** 加密保護的是資料的機密性，不會改變資料存放的地理位置；只靠加密無法滿足「必須存放在歐盟境內」的規定。
>
> **考點**：SAA-1.3｜Region 選擇的第一優先是合規與資料落地

### 練習 2-2｜SAA｜單選｜同一 AZ 的多台機器

Wanderly 的 API 由 Application Load Balancer 後面的三台 EC2 提供服務，三台都位於 `ap-northeast-1a`。某天這個 AZ 發生電力問題，API 完全中斷。技術主管說：「我們明明有三台機器，為什麼還是全掛？」團隊希望未來單一 AZ 故障時 API 仍能服務。

最根本的修正是什麼？

- A. 在至少兩個 AZ 建立 subnet，讓 EC2 分散在不同 AZ，並讓 Load Balancer 使用這些 AZ
- B. 把三台 EC2 換成同一 AZ 中一台更大的 instance
- C. 在 `ap-northeast-1a` 再增加三台 EC2，總共六台
- D. 把 Route 53 記錄的 TTL 調降到 1 秒，讓使用者更快切換

> [!answer]- 答案：A
> **A ✓** 三台機器共享同一個故障域（同一個 AZ），數量再多也擋不住 AZ 故障。把容量分散到至少兩個 AZ，並讓 Load Balancer 只把流量送到健康 AZ 的機器，才能撐過 AZ 等級的故障。
>
> **B ✗** 垂直擴展只提高單機容量，反而讓所有流量集中在一台機器上，故障風險更集中。
>
> **C ✗** 增加同一 AZ 內的機器數量能提高容量，但故障域沒有變，AZ 故障時六台一樣全部失效。
>
> **D ✗** DNS TTL 只影響快取多久，如果所有後端都在同一個故障的 AZ，切換到哪裡都沒有可用的機器。
>
> **考點**：SAA-2.2｜高可用的單位是 AZ，不是 instance 數量

### 練習 2-3｜SAA｜單選｜受管資料庫的責任分擔

Wanderly 把訂單資料庫從 EC2 上自己安裝的 MySQL 搬到 Amazon RDS for MySQL。安全稽核人員詢問：搬遷之後，哪一項安全工作仍然是 Wanderly 的責任？

哪個敘述正確？

- A. 修補 RDS instance 底層的作業系統
- B. 維護 RDS 所在資料中心的實體門禁與硬體
- C. 更換故障的儲存硬碟並維持虛擬化層的安全
- D. 設定誰能從網路連到資料庫（security group、是否公開存取），以及資料庫使用者與加密選項

> [!answer]- 答案：D
> **A ✗** RDS 是受管服務，底層作業系統的修補由 AWS 負責；Wanderly 只需要選擇維護時段。若是在 EC2 上自己安裝 MySQL，這項才是客戶的責任。
>
> **B ✗** 資料中心的實體安全屬於「雲端本身的安全」，永遠是 AWS 的責任。
>
> **C ✗** 硬體與虛擬化層同樣由 AWS 負責，客戶無法也不需要處理。
>
> **D ✓** 不論服務多受管，網路存取設定、資料庫帳號權限、是否啟用加密與資料本身都是客戶的責任。RDS 被設為公開存取而外洩，是設定問題而不是 AWS 的漏洞。
>
> **考點**：SAA-1.2｜Shared Responsibility Model 隨服務類型移動，但設定與資料永遠是客戶的

### 練習 2-4｜SAA｜單選｜資料必須留在機房

Wanderly 併購的旅行社有一套與機房內票務主機緊密互動的訂位系統，兩者之間要求極低延遲，而且當地法規要求這些訂位資料必須留在旅行社自己的資料中心。IT 團隊希望這套系統能使用和 AWS Region 相同的 EC2 API、Console 與部署工具，由 AWS 負責維護硬體。資料中心與 AWS Region 之間有穩定的網路連線。

哪個方案最符合需求？

- A. 把系統部署到距離最近的 AWS Local Zone
- B. 在旅行社的資料中心部署 AWS Outposts，並在上面執行 EC2
- C. 把系統部署到 AWS Wavelength Zone
- D. 把系統搬到最近的 AWS Region，並用 CloudFront 降低延遲

> [!answer]- 答案：B
> **A ✗** Local Zone 位於 AWS 的設施，不在旅行社的資料中心，無法滿足「資料必須留在自己資料中心」的法規，與機房內主機的延遲也取決於兩地距離。
>
> **B ✓** Outposts 把 AWS 管理的硬體放進客戶自己的資料中心，資料留在機房內，能和機房內系統低延遲互動，同時使用和 Region 一致的 API 與工具。它需要連回父 Region，而題目已說明網路連線穩定。
>
> **C ✗** Wavelength 位於電信業者的 5G 網路內，目的是服務行動裝置，與資料留在自家機房的需求無關。
>
> **D ✗** 搬到 Region 違反資料落地要求；CloudFront 加速的是對使用者的內容傳遞，無法解決系統與機房內主機之間的延遲。
>
> **考點**：SAA-3.2｜Outposts 用於資料或處理必須留在地端的情境

### 練習 2-5｜SAA｜單選｜特定城市的超低延遲

一家與 Wanderly 合作的影音製作公司位於某個大城市，附近沒有 AWS Region，最近的 Region 往返延遲約 30 毫秒。剪輯師要在雲端的高效能工作站上即時編輯影片，要求往返延遲在個位數毫秒內。工作站使用一般的有線網路，不是行動網路。

哪個方案最符合需求？

- A. 在最近的 Region 使用更高規格的 EC2 instance，並啟用 enhanced networking
- B. 在最近的 Region 前面加上 AWS Global Accelerator
- C. 在該城市的 AWS Wavelength Zone 部署工作站
- D. 在該城市的 AWS Local Zone 建立 subnet，於其中執行工作站的 EC2

> [!answer]- 答案：D
> **A ✗** 延遲主要來自地理距離，instance 規格與 enhanced networking 無法把 30 毫秒的網路往返縮短到個位數。
>
> **B ✗** Global Accelerator 透過 AWS 骨幹網路改善路徑與穩定性，但工作站仍在遠端的 Region，無法消除距離造成的延遲。
>
> **C ✗** Wavelength 是為電信 5G 網路上的行動裝置設計的，題目明確說使用一般有線網路。
>
> **D ✓** Local Zone 是父 Region 在特定城市的延伸，可以在 VPC 中建立位於 Local Zone 的 subnet 並執行 EC2，讓當地使用者享有個位數毫秒的延遲。影片後製正是它的典型用途。
>
> **考點**：SAA-3.4｜Local Zones 解決特定城市的低延遲需求

### 練習 2-6｜SAA｜選兩項｜擴展到第二個 Region

Wanderly 目前在東京 Region 運行，使用自建的 AMI 啟動 EC2、以 security group 控制流量，並透過 IAM role 讓 EC2 存取 S3。公司決定在新加坡 Region 部署一套相同的系統作為第二個站點。

在新加坡部署時，哪兩項資源必須在新加坡另外建立或複製？（選兩項）

- A. EC2 使用的 IAM role 與其 policy
- B. 自建的 AMI
- C. 帳號的 root user
- D. Route 53 public hosted zone
- E. EC2 使用的 security group

> [!answer]- 答案：B、E
> **A ✗** IAM 是 global 服務，role 與 policy 在帳號內所有 Region 都可以使用，不需要重建；但 policy 中若寫了特定 Region 的資源 ARN，可能需要更新內容。
>
> **B ✓** AMI 是 regional 資源，只能在建立它的 Region 使用。要在新加坡啟動相同的 EC2，必須先把 AMI 複製到新加坡。
>
> **C ✗** Root user 屬於整個帳號，與 Region 無關。
>
> **D ✗** Route 53 hosted zone 是 global 資源，同一個 zone 可以同時包含指向東京與新加坡的記錄。
>
> **E ✓** Security group 屬於某個 VPC，而 VPC 是 regional 資源。新加坡需要建立自己的 VPC 與 security group。
>
> **考點**：SAA-2.2、SAA-1.1｜global、regional 與 zonal 資源的範圍

### 練習 2-7｜SAA｜單選｜Data transfer 計費方向

Wanderly 的財務人員在帳單上看到一筆持續增加的 data transfer 費用，想先了解計費規則再決定怎麼優化。目前的流量包括：使用者上傳照片到 S3、EC2 把照片縮圖後回傳給使用者、兩個 AZ 之間的應用程式伺服器互相呼叫，以及每天把備份複製到另一個 Region。

哪一項流量通常**不會**產生 data transfer 費用？

- A. 使用者從 Internet 上傳照片到 S3
- B. EC2 把縮圖經 Internet 回傳給使用者
- C. 不同 AZ 的應用程式伺服器之間互相呼叫
- D. 把備份每天複製到另一個 Region

> [!answer]- 答案：A
> **A ✓** 從 Internet 進入 AWS 的資料傳輸一般不收費。上傳照片可能有 S3 的請求費用，但沒有 data transfer in 的費用。
>
> **B ✗** 從 AWS 送出到 Internet 的流量會依 GB 收費，這通常是 data transfer 費用的主要來源；用 CloudFront 提供內容可以改善成本結構。
>
> **C ✗** 同一個 Region 內跨 AZ 的流量會收費。高可用需要跨 AZ，但應避免不必要的跨 AZ 往返。
>
> **D ✗** 跨 Region 的資料傳輸會收費，規劃跨 Region 備份或複寫時要把這筆成本算進去。
>
> **考點**：SAA-4.4｜data transfer 的計費方向

### 練習 2-8｜SAA｜單選｜保護 root user

Wanderly 的帳號由創辦人用個人 email 註冊。目前三位工程師共用 root user 的密碼登入 Console，部署腳本也使用 root user 的存取金鑰。新聘的資安顧問要求立即降低風險，同時讓工程師仍能完成日常管理工作。

哪個做法最符合 AWS 的最佳實務？

- A. 保留 root user 的存取金鑰給部署腳本使用，但每 30 天輪替一次
- B. 建立一個 IAM user 給三位工程師共用，並附加 `AdministratorAccess`
- C. 為 root user 啟用 MFA 並刪除其存取金鑰，為每位工程師建立各自具備適當權限的身份，部署腳本改用 IAM role
- D. 用 SCP 限制 root user 的權限，讓它只能查看帳單

> [!answer]- 答案：C
> **A ✗** Root user 的存取金鑰擁有無法限制的完整權限，一旦外洩後果最嚴重。最佳實務是根本不建立 root 存取金鑰，輪替無法消除這個風險。
>
> **B ✗** 共用身份無法追蹤是誰做了什麼操作，也無法在某人離職時單獨撤銷權限；給所有人完整管理權限也違反最小權限原則。
>
> **C ✓** 保護 root user 的基本步驟是啟用 MFA、刪除 root 存取金鑰、日常不使用 root。每人各自的身份讓稽核紀錄可追溯；部署腳本改用 IAM role 取得臨時憑證，避免長期金鑰。帳號 email 也應改成團隊共管的信箱。
>
> **D ✗** SCP 是 AWS Organizations 的功能，對單一獨立帳號不適用；而且 SCP 不會影響 management account。問題的核心是停止使用 root，而不是嘗試限制它。
>
> **考點**：SAA-1.1｜root user 保護與個別身份

### 練習 2-9｜SAA｜單選｜靜態穩定的容量規劃

Wanderly 的網站在尖峰時需要 8 台 EC2 才能承擔全部流量。目前設計是在兩個 AZ 各放 4 台，並計畫在某個 AZ 故障時，由 Auto Scaling 在另一個 AZ 緊急補齊到 8 台。技術主管擔心故障期間啟動新 instance 可能變慢或失敗，要求即使無法啟動任何新 instance，單一 AZ 故障時網站仍能承擔尖峰流量。

哪個設計最符合要求？

- A. 維持每個 AZ 4 台，並把 Auto Scaling 的擴展冷卻時間縮短
- B. 在每個 AZ 預先維持 8 台 instance，讓任一 AZ 單獨就能承擔全部尖峰流量
- C. 把 8 台 instance 全部放在同一個 AZ，故障時再到另一個 AZ 啟動
- D. 維持每個 AZ 4 台，並在故障時手動從 Console 啟動新的 instance

> [!answer]- 答案：B
> **A ✗** 縮短冷卻時間仍然依賴故障當下啟動新 instance，也就是依賴 control plane。題目要求的是「不能啟動任何新 instance 時也撐得住」。
>
> **B ✓** 這是 static stability 的設計：每個 AZ 都預留足以承擔全部流量的容量，AZ 故障時剩下的 AZ 只靠已經在運行的資源（data plane）就能撐住，不需要任何建立資源的操作。代價是平時有較多閒置容量。常見的折衷是改用三個 AZ、每個 AZ 放 4 台（共 12 台）：任一 AZ 故障時仍剩 8 台，平時多出的容量只有 50%，而不是 100%。
>
> **C ✗** 全部放在同一個 AZ 時，該 AZ 故障就會完全中斷，而且恢復仍依賴啟動新 instance。
>
> **D ✗** 手動啟動既慢又依賴 control plane，與 Auto Scaling 有一樣的問題，還多了人工反應時間。
>
> **考點**：SAA-2.2｜control plane vs data plane 與 static stability

### 練習 2-10｜SAA｜單選｜季節性流量與彈性

Wanderly 的訂房流量有明顯的季節性：一年中有四個連假檔期，每次約兩週，流量是平日的 10 倍，其他時間流量穩定且偏低。顧問建議比照傳統做法，依連假尖峰的容量購買並長期運行伺服器。財務長希望在不影響連假服務品質的前提下，讓成本最低。

哪個做法最符合需求？

- A. 依連假尖峰的容量長期運行 EC2，並為全部 instance 購買三年期 Reserved Instances
- B. 依平日容量長期運行 EC2，連假時讓使用者排隊等候
- C. 依連假尖峰的容量長期運行 EC2，平日把多餘的 instance 改為較小的 instance type
- D. 平日只運行承擔基本流量所需的容量，並用 Auto Scaling 在連假期間依需求自動擴充、結束後自動縮回

> [!answer]- 答案：D
> **A ✗** Reserved Instances 降低的是單價，但依尖峰容量長期承諾，一年中大部分時間有九成容量閒置，總成本仍然很高。這就是雲端要解決的「猜測容量」問題。
>
> **B ✗** 讓使用者排隊會直接影響連假的服務品質與營收，違反題目的前提。
>
> **C ✗** 仍然長期運行尖峰數量的 instance，只是換小規格，需要大量人工調整，節省有限。
>
> **D ✓** 雲端的彈性讓容量能隨需求增減，只為實際使用的時間付費。平日的基本容量還可以搭配 Savings Plans 降低單價，尖峰時段的額外容量則由 Auto Scaling 處理（第 18、39 章）。
>
> **考點**：SAA-4.2｜雲端彈性與按用量計價
