---
chapter: 18
title: Auto Scaling 與高可用 Web Tier
part: 3
---

# 第 18 章　Auto Scaling 與高可用 Web Tier：Launch Template、Scaling Policy 與 ALB + ASG

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 launch template、Auto Scaling group、scaling policy 各自負責什麼，以及 min／max／desired 三個數字如何驅動整個機群
> - 依流量型態選擇 target tracking、step、simple、scheduled 或 predictive scaling，並挑出「加機器後會下降」的正確 metric
> - 用 health check、grace period、warm-up、lifecycle hook 與 warm pool 處理「機器剛開好」與「機器要被關掉」這兩個最容易出事的時刻
> - 用 instance refresh 安全地替換整個機群，並用 termination policy 與 scale-in protection 控制縮容時誰先離開
> - 設計跨多 AZ 的 ALB + ASG web tier：外部化 session、混用 On-Demand 與 Spot，並在一個 AZ 故障時仍維持服務
>
> **前置知識**：第 5 章（subnet 與多 AZ）、第 10 章（ALB、target group、health check）、第 17 章（AMI、user data、購買方式與 Spot）
> **考試比重**：SAA ★★★（Domain 2 高可用、Domain 3 彈性運算、Domain 4 成本）｜SAP ★★☆（Domain 2 可靠性與部署、Domain 3 改善既有系統）

## 18.1 故事：週五晚上的限時特價

第 17 章結束時，Wanderly 已經依 workload 選好了 instance type、做好 golden AMI，但網站本身仍然只跑在一台機器上，前面是一個 ALB，資料庫已經搬到 RDS。工程師小林對這台機器照顧得無微不至：每週手動更新、每個月看一次 CPU 曲線，必要時半夜爬起來重開。

某個週五晚上 8 點，行銷團隊推出「東京飯店一元起」限時特價，事前沒有通知工程團隊。8 點 02 分，流量變成平常的十倍，CPU 衝到 100%，頁面開始 timeout。小林手忙腳亂地從 AMI 開了三台新機器、手動註冊到 ALB 的 target group，等它們開機、安裝套件、通過 health check，已經是 8 點 25 分。特價最熱的二十分鐘，Wanderly 一張單都沒接到。

更糟的是隔天早上。流量回到平常水準，四台機器的 CPU 都只有 10%，但沒有人記得把多開的機器關掉，直到月底看到帳單。再過兩週，`ap-northeast-1a` 發生一次短暫的網路異常，原本那台機器剛好在 1a，雖然另外三台還活著，但其中兩台也在 1a，網站容量瞬間只剩四分之一。

技術主管在事後檢討裡寫下三個要求：第一，容量要自動跟著需求增減，不能靠人；第二，壞掉的機器要自動被換掉；第三，機器要平均分散在多個 AZ，任何一個 AZ 出事都不能讓網站倒下。這一章就是 AWS 對這三個要求的答案：**EC2 Auto Scaling**，以及它和 ALB 組成的標準高可用 web tier。

## 18.2 從照顧一台機器到管理一群機器

小林遇到的問題，本質上是「把伺服器當寵物養」：每台機器都有名字、有手動調整過的設定、壞了就要救。雲端的做法是把伺服器當成牛群：每台都是用同一份藍圖做出來的、可以隨時被替換，系統關心的是「現在有幾台健康的機器在工作」，而不是「web-01 還好嗎」。

**Elasticity（彈性）** 指的是容量能跟著需求自動增加與減少：流量來時加機器，流量走時減機器，只為實際用到的容量付費。**Self-healing（自我修復）** 指的是系統偵測到故障元件後自動替換，不需要人介入。EC2 Auto Scaling 同時提供這兩種能力。

要讓機器能被隨意增減，應用程式必須滿足兩個前提：

1. **Stateless（無狀態）**：任何一台機器被關掉，都不會遺失使用者資料。購物車、登入 session、上傳到一半的檔案，都要放在機器之外（18.12 節）。
2. **可重複建立**：新機器啟動後不需要人登入設定，就能自己進入可服務狀態。這靠的是 AMI 與 user data（第 17 章），以及本章的 launch template。

### 三個名字很像的服務

AWS 有三個名字都帶「Auto Scaling」的東西，考試會混著出現：

| 名稱 | 管什麼 | 例子 |
|---|---|---|
| **Amazon EC2 Auto Scaling** | EC2 instance 組成的 Auto Scaling group | 本章主角 |
| **Application Auto Scaling** | 其他服務的「可調整容量」 | ECS service 的 task 數（第 21 章）、DynamoDB provisioned capacity（第 27 章）、Aurora replica 數（第 26 章）、Lambda provisioned concurrency（第 19 章） |
| **AWS Auto Scaling（scaling plans）** | 一個集中介面，替上面兩者的資源一起建立 scaling plan | 較舊的整合主控台，新設計多半直接在各服務設定 |

本章說「Auto Scaling」時，指的都是 EC2 Auto Scaling。它負責的是**機器數量**，不負責分配流量；把流量分給機器的是第 10 章的 Load Balancer。兩者分工清楚，是理解本章的第一步。

## 18.3 Launch template：新機器的藍圖

Auto Scaling 要能自己開機器，首先得知道「要開什麼樣的機器」。**Launch template（啟動範本）** 就是這份藍圖：它記錄啟動一台 EC2 需要的所有參數，Auto Scaling 每次要加機器時，都照著它啟動。

### Launch template 裡放什麼

| 欄位 | 說明 |
|---|---|
| AMI ID | 開機用的映像檔，決定作業系統與預先安裝的軟體 |
| Instance type | 例如 `m7i.large`；也可以在 ASG 層級用 mixed instances policy 覆寫成多種（18.11 節） |
| Security groups | 新機器套用哪些 security group |
| IAM instance profile | 機器上的程式用哪個 IAM role 呼叫 AWS API（第 12 章） |
| User data | 開機時執行的腳本 |
| Metadata options | 例如強制 IMDSv2（`HttpTokens: required`，第 17 章） |
| Block device mappings | Root volume 大小、volume type、是否加密 |
| Key pair、tags、monitoring | 其他啟動參數 |

注意 launch template 裡**通常不指定 subnet**。要把機器放在哪些 subnet（也就是哪些 AZ），是 Auto Scaling group 的設定；藍圖只描述「機器長什麼樣子」。

### 版本：藍圖可以改，但舊版本不會消失

Launch template 有**版本（version）**。每次修改都會產生一個新版本，舊版本保留不變。Auto Scaling group 引用 launch template 時要指定版本，有三種寫法：

- 指定版本號（例如 `7`）：最明確，正式環境建議用法，搭配 IaC 管理。
- `$Default`：template 的預設版本，由你手動設定哪一版是預設。
- `$Latest`：永遠使用最新版本。方便，但任何人建立新版本，下一台新機器就會照新版啟動。

修改 launch template **不會改變已經在跑的機器**，只會影響之後新啟動的機器。這是很多人第一次踩到的坑：更新了 AMI，結果機群裡新舊版本混在一起好幾天。要讓整個機群換成新版本，需要 18.10 節的 instance refresh。

### Launch configuration：舊做法

在 launch template 出現前，Auto Scaling 使用 **launch configuration**。它不能修改（只能整份重建）、不支援版本、不支援 mixed instances policy 與許多新功能。AWS 已逐步淘汰它：2023 年 1 月 1 日之後推出的新 instance type 不支援 launch configuration；2023 年 6 月 1 日之後建立的帳號不能在 console 建立它；2024 年 10 月 1 日之後建立的帳號則完全無法建立（console、API、CLI、CloudFormation 都不行）。AWS 建議全部遷移到 launch template。題目選項若同時出現兩者，新設計請選 launch template。

### Golden AMI 與 user data 的取捨

新機器從啟動到能接流量要多久，直接決定 Auto Scaling 救火的速度。小林原本的做法是用乾淨的 Amazon Linux AMI，再用 user data 在開機時安裝 Nginx、下載程式碼、編譯相依套件，整個過程要 8 分鐘。

| 做法 | 開機速度 | 彈性 | 適合 |
|---|---|---|---|
| 全部用 user data 安裝 | 慢（幾分鐘以上） | 高，改腳本即可 | 開發、低頻變更 |
| **Golden AMI**（預先把軟體與程式烤進 AMI） | 快（通常一兩分鐘內） | 每次改版要重新產生 AMI | 正式環境、需要快速擴展 |
| Golden AMI + 少量 user data | 快 | 只在開機時拉取設定、環境變數 | 最常見的折衷 |

**Golden AMI** 是指已經安裝好作業系統更新、執行環境與應用程式、經過測試的標準映像檔。用 EC2 Image Builder 可以把產生 golden AMI 的流程自動化（第 17 章）。考試看到「新 instance 需要很久才能開始服務，導致擴展太慢」時，「預先烤好 AMI、縮短 user data」幾乎總是答案的一部分。

## 18.4 Auto Scaling group：min、max、desired 與自我修復

有了藍圖，接著需要一個「機群管理員」。**Auto Scaling group（ASG）** 是一組由 Auto Scaling 統一管理的 EC2 instance，它的核心只有三個數字：

- **Minimum（min）**：機群最少要有幾台。即使沒有任何流量，也不會低於這個數字。
- **Maximum（max）**：機群最多能有幾台。這是成本與失控保護的上限。
- **Desired capacity（desired）**：機群「現在應該有」幾台。它必須介於 min 與 max 之間。

### ASG 是一個不停核對的控制迴圈

理解 ASG 最好的方式，是把它想成一個不斷比對「應該有幾台」與「實際有幾台健康的」的程式：

```text
            ┌──────────────────────────────────────────────┐
            │  ① 輸入：desired capacity                     │
            │     （由你手動設定、scaling policy 或排程改變）  │
            └──────────────────────┬───────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  ② 比對：實際 InService 且健康的 instance 數     │
            └──────┬───────────────────────────────┬───────┘
          實際 < desired                      實際 > desired
                   ▼                               ▼
   ③ 依 launch template 啟動新 instance   ④ 依 termination policy
      選擇 instance 最少的 AZ 優先放置        選 instance 最多的 AZ 先縮
                   │                               │
                   ▼                               ▼
   ⑤ 註冊到 target group，等 health check   ⑥ 從 target group 取消註冊，
      通過後開始接流量                         等連線排空後 terminate
                   │                               │
                   └──────────────┬────────────────┘
                                  ▼
            ⑦ 持續監看 health check：不健康的 instance 會被
               terminate，於是「實際 < desired」，回到 ③ 補一台
```

① desired 是整個機群的「目標」。Scaling policy 做的事情其實只有一件：**修改 desired**。② ASG 隨時比對目前健康、正在服務的 instance 數量。③ 少了就照 launch template 補，並優先放到 instance 最少的 AZ。④ 多了就挑一台關掉，挑法由 termination policy 決定（18.9 節）。⑤⑥ 如果 ASG 綁定了 target group，加入與移除時會自動註冊與取消註冊，不需要像小林那樣手動處理。⑦ 這個迴圈也是自我修復的來源：一台 instance 被判定不健康後會被替換，因為替換只是「實際數量少了一台」的自然結果。

所以，即使完全不設定任何 scaling policy，把 min = desired = max = 2 的 ASG 跨兩個 AZ 部署，也已經得到一個「永遠維持兩台健康機器」的自我修復機群。這是考試裡「讓單台 EC2 在故障時自動恢復，成本最低」的經典答案之一（另一個答案是第 17 章的 EC2 auto recovery，只適用於底層硬體故障且不會換 AZ）。

### 跨多個 AZ：ASG 的 subnet 設定

ASG 設定時要選一組 subnet（設定欄位叫 `VPCZoneIdentifier`），每個 subnet 屬於一個 AZ。ASG 會盡量讓各 AZ 的 instance 數量平均：

- **擴展時**：優先在 instance 最少的 AZ 啟動。
- **某個 AZ 無法啟動時**（容量不足、AZ 故障）：改到其他 AZ 啟動，維持總數。
- **AZ 恢復後**：ASG 的 **AZRebalance** 程序會把數量重新拉平。它會**先在少的 AZ 啟動新機器，再關掉多的 AZ 的機器**，避免重新平衡期間容量下降。因此重新平衡時，實際 instance 數可能暫時超過 desired（最多超過 max 的 10% 或 1 台，取較大者）。

回到小林的故事：如果當時有一個跨 1a、1c 兩個 AZ 的 ASG，1a 出事時，ASG 會在 1c 補足 instance，網站不會只剩四分之一容量。

> [!warning] 常見誤解
> 「ASG 設了 max 10，所以需要時一定開得出 10 台。」max 只是上限，不是保證。啟動仍可能因為 instance type 在某 AZ 容量不足（`InsufficientInstanceCapacity`）、subnet IP 用完、帳號的 vCPU quota 不足、AMI 或 KMS key 權限錯誤而失敗。失敗原因會記錄在 ASG 的 activity history。降低風險的方式是使用多個 AZ、多種 instance type（18.11 節），以及在關鍵情境預留容量（18.16 節）。

### 手動操作 desired 也是合法的

你隨時可以手動修改 desired，例如活動前直接設成 20。手動修改和 scaling policy 修改的是同一個數字；之後 scaling policy 仍會依 metric 繼續調整它。另外，desired 不能被設到 min 以下或 max 以上，scaling policy 的結果也會被限制在這個範圍內。

## 18.5 Health check：誰來判斷一台機器壞了

自我修復的前提是「知道誰壞了」。ASG 用 **health check（健康檢查）** 判斷 instance 是否健康，不健康的 instance 會被 terminate 並替換。問題在於：「健康」的定義不只一種。

### 健康檢查的類型

| 類型 | 檢查什麼 | 預設 |
|---|---|---|
| **EC2 health check** | EC2 status checks：instance 是否在 running 狀態、底層主機與作業系統網路是否正常 | 永遠啟用 |
| **ELB health check** | Target group 的 health check：ALB 定期送 HTTP 請求到指定路徑，回應碼是否符合 | **需要手動啟用** |
| **Custom health check** | 你自己的監控系統呼叫 `SetInstanceHealth` API，把 instance 標成 Unhealthy | 選用 |
| 其他 | 例如 VPC Lattice target group 的健康檢查、EBS volume 狀態 | 選用 |

這張表裡最重要的一格是「ELB health check 需要手動啟用」。EC2 status check 只知道「機器有沒有活著」，不知道「網站能不能用」。如果 Nginx 掛了、程式卡死、磁碟寫滿導致每個請求都回 500，EC2 status check 仍然顯示一切正常。

### 考試最愛的情境：ALB 說壞了，ASG 卻不換

小林把 ASG 綁上 ALB 的 target group 後，某天應用程式因為記憶體洩漏卡死。ALB 的 health check 很快把這台 instance 標成 unhealthy，不再送流量給它；但 ASG 使用的仍是預設的 EC2 health check，覺得這台機器 running 一切正常，**既不 terminate 也不替換**。結果機群裡永遠有一台「活著但沒用」的機器，實際容量少了一台。

修正方式是把 ASG 的 **health check type 設成 ELB**（同時保留 EC2 檢查）。這樣當 target group 判定 instance 不健康時，ASG 也會把它視為不健康並替換。

> [!tip] 考試提示
> 題目描述「ALB 顯示 target unhealthy，但 Auto Scaling 沒有替換它」，答案就是「為 ASG 啟用 ELB health check」。看到「應用程式層面的故障要自動替換」也是同一件事。

### Health check grace period：給新機器一點時間

新 instance 剛啟動時，user data 還在跑、應用程式還沒監聽 port，這時去做 ELB health check 一定失敗。如果 ASG 立刻把它判成不健康並替換，就會陷入「開機 → 還沒好就被判壞 → 關掉 → 再開一台」的無限迴圈。

**Health check grace period（健康檢查寬限期）** 就是用來解決這件事：instance 進入 InService 後的這段時間內，ASG 不會因為 health check 失敗而把它判為不健康並替換（例外：若 instance 已經不在 EC2 的 running 狀態，例如被停止，ASG 會立即替換）。用 console 建立 ASG 時預設是 300 秒，用 CLI 或 SDK 建立時預設是 0（等於關閉寬限期）；設定值應該大於「開機到應用程式可以通過 health check」的實際時間。Grace period 從 instance 進入 InService 才開始計算；若使用 launch lifecycle hook 在開機時做完準備（18.8 節），instance 進入 InService 時已經準備好，grace period 可以設得很短甚至為 0。

### Health check 端點怎麼設計

ALB health check 打的路徑（例如 `/health`）回什麼，決定了「健康」的定義：

- **淺層檢查（shallow）**：只確認程序活著、能回應 HTTP 200。優點是不會被下游拖累。
- **深層檢查（deep）**：同時檢查資料庫、快取等相依服務。優點是更接近「使用者能不能成功」；缺點是**當共用的資料庫短暫變慢時，所有 instance 會同時被判定不健康**，ASG 開始大量替換機器，讓小問題變成全站事故。

實務上的平衡是：health check 檢查「這台機器本身」能否服務（程序、記憶體、本機設定），相依服務的健康交給監控與告警（第 36 章）。另外，ALB 在 target group 裡**所有** target 都不健康時會 fail open，把流量送給所有 target（第 10 章），這是避免 health check 設計錯誤導致零容量的最後一道保險，但不應該依賴它。

## 18.6 Scaling policies：什麼時候加、加幾台

到這裡，ASG 能維持固定數量的健康機器，但還不會「跟著需求變化」。這是 **scaling policy（擴展政策）** 的工作：觀察某個訊號，決定要把 desired 改成多少。EC2 Auto Scaling 提供五種方式，分成兩大類：

- **Dynamic scaling（動態擴展）**：根據即時 metric 反應。包含 target tracking、step、simple。
- **事先規劃**：根據時間或預測提前調整。包含 scheduled、predictive。

### Target tracking：設定目標值，像恆溫器一樣

**Target tracking scaling** 是最推薦、最常用的方式。你只要指定一個 metric 與目標值，例如「平均 CPU 維持在 50%」，Auto Scaling 就會自動建立並管理所需的 CloudWatch alarm，計算要加或減幾台，讓 metric 回到目標值附近，就像冷氣的恆溫器一樣。

內建可直接選的 metric：

| Predefined metric | 意義 | 適合 |
|---|---|---|
| `ASGAverageCPUUtilization` | ASG 所有 instance 的平均 CPU | CPU-bound 的應用 |
| `ALBRequestCountPerTarget` | ALB target group 中每個 target 平均收到的請求數 | Web／API，請求量與負載成正比時 |
| `ASGAverageNetworkIn`／`ASGAverageNetworkOut` | 每台平均網路流量 | 網路傳輸密集的服務 |

你也可以使用 custom metric，例如 18.6 節後段的「每台 instance 分到的 SQS 訊息數」。

Target tracking 的幾個重要行為：

- **擴展積極、縮減保守**：metric 超過目標時會較快加機器；低於目標時會較慢、較小幅度地減機器，避免來回震盪。
- **它自動建立的 CloudWatch alarm 不要手動修改或刪除**，否則 policy 會失效。
- 可以設定 `DisableScaleIn`，讓 policy 只負責擴展、縮減交給其他機制。
- 同一個 ASG 可以有多個 target tracking policy（例如 CPU 與請求數各一個）。這時**只要任何一個 policy 要求擴展就會擴展；所有 policy 都同意縮減時才會縮減**，以容量較大的結果為準。

### 選對 metric：加機器後，它會不會下降？

Target tracking 有一個隱含假設：**增加 instance 後，這個 metric 應該會成比例下降**。平均 CPU 與每台請求數都符合：流量不變時，機器從 4 台變 8 台，每台的 CPU 與請求數大約減半。

不符合這個假設的 metric 會讓 policy 失控：

- **ALB 的總請求數**：加機器不會讓總請求數下降，policy 會一直加到 max。
- **平均延遲（latency）**：瓶頸若在資料庫，加再多 web 機器延遲也不會降。
- **Queue 中的訊息總數**：在加機器後下降得很慢，而且同一個數字在 2 台與 20 台時代表的壓力完全不同。

> [!example] 例子：SQS worker 的正確 metric
> Wanderly 的訂單確認信由一組 worker 從 SQS queue 取出處理（第 32 章）。每台 worker 每秒處理 10 則訊息，業務要求一則訊息最多等 60 秒。所以每台 worker 可以接受的待處理量是 10 × 60 = **600 則**。
>
> 正確的 custom metric 是 **backlog per instance（每台待處理量）** = `ApproximateNumberOfMessagesVisible` ÷ ASG 中 InService 的 instance 數，target 設為 600。當 queue 累積 12,000 則訊息、目前有 10 台時，每台 1,200 則，policy 會把機群擴到約 20 台；加了機器後這個比值自然下降。這個 metric 需要你自己定期計算並發布到 CloudWatch（例如用一個排程的 Lambda），這是 AWS 文件建議的標準做法。

### Step scaling：依超標程度分段加機器

**Step scaling** 需要你自己建立 CloudWatch alarm，再定義「metric 超過多少就加幾台」的階梯：

| Alarm 條件（CPU） | 調整 |
|---|---|
| 60% ≤ CPU < 75% | +1 台 |
| 75% ≤ CPU < 90% | +3 台 |
| CPU ≥ 90% | +30%（百分比調整） |

它的優點是控制精細：超標越多、加越多，適合需要對「劇烈飆升」反應更快的情境。Step scaling 在一次擴展進行中仍會持續評估 alarm，可以疊加後續的調整，並用 instance warm-up（18.7 節）避免把還在開機的機器重複計算。

### Simple scaling：最舊的方式

**Simple scaling** 也是 alarm 觸發、調整固定數量，但每次調整後要等 **cooldown period（冷卻時間，預設 300 秒）** 結束才會回應下一次 alarm。在 cooldown 期間，即使流量持續暴增，它也不會再加機器。這讓它對突發流量反應太慢，AWS 建議改用 target tracking 或 step scaling。題目選項若出現 simple scaling，通常是錯誤選項，除非題目明確要求「每次觸發只調整固定數量並等待一段時間」。

### Scheduled scaling：已知的時間，提前準備

有些流量變化是**事先知道**的：每天晚上 7 點到 11 點是訂房尖峰、每週五晚上 8 點固定有特價、年底有大型促銷。這時與其等 metric 上升再反應，不如提前把容量準備好。

**Scheduled action（排程動作）** 可以在指定時間（一次性或用 cron 表示的週期）修改 min、max、desired，並可以指定時區。例如每週五 19:30（台北時間）把 min 提高到 10：

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name wanderly-web-asg \
  --scheduled-action-name friday-flash-sale \
  --recurrence "30 19 * * 5" \
  --time-zone "Asia/Taipei" \
  --min-size 10 --desired-capacity 12 --max-size 40
```

設計重點是**提高 min，而不只是 desired**：如果只調高 desired，target tracking 看到 CPU 很低，可能在活動開始前就把機器縮回去。活動結束後，再用另一個 scheduled action 把 min 調回原值。

### Predictive scaling：從歷史學習週期

**Predictive scaling（預測擴展）** 會分析過去的 metric 歷史（至少需要 24 小時資料，越多越準），找出每日、每週的規律，預測未來兩天的負載，並**在預測的尖峰到來前提前啟動 instance**。

它適合：

- 有明顯週期（每天上班時間、每週固定模式）的流量。
- 新 instance 初始化很久，等 dynamic scaling 反應已經太遲的應用。

使用時的建議：

- 先用 **forecast only（只預測）** 模式觀察一段時間，確認預測準確，再切到 **forecast and scale** 實際調整容量。
- 搭配 dynamic scaling 一起使用：predictive 負責準備可預期的基礎量，target tracking 負責處理預測之外的突發。兩者同時存在時，ASG 取兩者中較大的容量。
- 它不適合沒有規律、純突發的流量（例如新聞事件），這時預測沒有幫助。

### 五種方式的比較

| 方式 | 觸發 | 需要自己建 alarm | 優點 | 限制 |
|---|---|---|---|---|
| Target tracking | Metric 偏離目標 | 否 | 最簡單、自動計算 | Metric 必須與容量成比例 |
| Step scaling | Alarm 分段 | 是 | 依超標程度分段反應 | 設定較複雜 |
| Simple scaling | 單一 alarm | 是 | 概念簡單 | Cooldown 期間不再反應，太慢 |
| Scheduled | 時間 | 否 | 已知事件提前準備 | 只適合可預知的時間 |
| Predictive | 歷史預測 | 否 | 週期流量提前擴展 | 需要歷史資料、不處理突發 |

## 18.7 Cooldown 與 warm-up：別被剛開機的機器騙了

Scaling policy 下決定時依賴 metric，但 metric 在「機器剛加進來」的那幾分鐘並不可靠：

- 新 instance 開機時 CPU 很高（安裝套件、載入快取），會把平均 CPU 拉高，讓 policy 以為還需要更多機器。
- 新 instance 還沒開始接流量時，它的 metric 是零，又會讓平均值看起來比實際低。

如果不處理，policy 會在剛擴展完就再擴展一次，造成過度擴展，然後再縮減，來回震盪。Auto Scaling 有兩個機制處理這個問題。

### Cooldown period（用於 simple scaling）

**Cooldown（冷卻時間）** 是 simple scaling 的機制：一次擴展活動完成後，在冷卻時間內不再執行同一 ASG 的 simple scaling 動作。預設 300 秒。它的做法很粗糙，等於「做完一次後先閉上眼睛」。

### Instance warm-up（用於 target tracking 與 step scaling）

**Instance warm-up（暖機時間）** 是比較精細的做法：新 instance 在 warm-up 時間內**仍被計入容量**（所以 policy 知道「已經加了機器」，不會重複加），但**它的 metric 不被納入 ASG 的彙總 metric**（所以不會被開機時的高 CPU 誤導）。

建議在 ASG 層級設定 **default instance warmup**，數值大約等於「instance 從啟動到 metric 穩定」的時間。設定後，target tracking、step scaling 與 instance refresh 都會使用它。

### 三個時間設定，不要混淆

| 設定 | 誰使用 | 解決什麼 |
|---|---|---|
| Health check grace period | Health check | 新 instance 還沒準備好，不要判成不健康 |
| Default instance warmup | Target tracking、step scaling、instance refresh | 新 instance 的 metric 還不穩定，不要納入計算 |
| Cooldown | Simple scaling | 一次調整後暫停一段時間再反應 |

> [!warning] 常見誤解
> 「把 cooldown 設成 0 就能讓 Auto Scaling 反應更快。」如果你用的是 target tracking，cooldown 根本不是主要的控制旋鈕；而把等待時間設得比實際開機時間短，只會讓 policy 被開機中的 metric 誤導而過度擴展。要讓擴展更快，正確方向是縮短開機時間（golden AMI）、使用 warm pool，或用 scheduled／predictive scaling 提前準備。

## 18.8 Instance 的一生：lifecycle hooks、warm pools 與 standby

前面兩節處理的是 metric 的問題，但「機器剛開好」與「機器要被關掉」這兩個時刻，應用程式本身也常常需要做事：開機時要先從設定中心拉設定、預熱快取；關機前要把還沒上傳的 log 送出去、把手上的工作做完。Auto Scaling 用 instance 的生命週期狀態讓你插手這兩個時刻。

### Lifecycle 狀態圖

```text
             擴展（scale out）
                   │
                   ▼
              [Pending]
                   │ ① 有 launch hook 時進入等待
                   ▼
           [Pending:Wait] ──── 你的程式做準備工作
                   │            （拉設定、預熱快取、註冊到其他系統）
                   │ ② 呼叫 complete-lifecycle-action（CONTINUE）
                   ▼
          [Pending:Proceed]
                   ▼
              [InService] ◄────────────┐
              │        │               │ ⑥ exit-standby
   ③ 縮減或    │        │ ⑤ enter-standby │
   不健康      │        └──────► [Standby]（不接流量、不被健康檢查替換）
              ▼
           [Terminating]
              │ ④ 有 termination hook 時進入等待
              ▼
         [Terminating:Wait] ── 你的程式做收尾工作
              │                （停止取新工作、上傳 log、完成手上工作）
              │ 呼叫 complete-lifecycle-action 或 timeout
              ▼
        [Terminating:Proceed] → [Terminated]
```

① 設定了 launch lifecycle hook 時，新 instance 會停在 `Pending:Wait`，這段時間它還沒被註冊到 target group，不會收到流量。② 你的準備程式完成後，呼叫 API 讓它繼續。③ Instance 因為 scale in、不健康或 instance refresh 要被移除時，進入 `Terminating`。④ 若有 termination hook，它會停在 `Terminating:Wait`，此時已經從 target group 取消註冊，可以安心做收尾。⑤⑥ Standby 是另一條支線，後面說明。

### Lifecycle hook 怎麼運作

**Lifecycle hook（生命週期掛鉤）** 讓 instance 在進入或離開服務前暫停，等你的程式完成某件事。設定重點：

- **通知方式**：hook 觸發時會送出事件，可以透過 **EventBridge**、SNS 或 SQS 通知你的處理程式（例如 Lambda 或 SSM Automation，第 38 章）；也可以讓 instance 自己在 user data 或程式裡處理。
- **Heartbeat timeout**：每次等待的時間，預設 1 小時（3,600 秒），最長可設 7,200 秒。工作需要更久時，可以呼叫 `record-lifecycle-action-heartbeat` 重新開始計時，但整體等待最長 48 小時。
- **Default result**：timeout 到了還沒收到回覆時怎麼辦。`CONTINUE` 表示照常繼續；`ABANDON` 在 launch hook 上表示放棄這台並 terminate，在 termination hook 上兩者最後都會 terminate，差別在於是否繼續執行其他 hook。
- **完成**：處理程式完成後呼叫 complete-lifecycle-action：

```bash
aws autoscaling complete-lifecycle-action \
  --auto-scaling-group-name wanderly-worker-asg \
  --lifecycle-hook-name drain-before-terminate \
  --instance-id i-0abc1234def567890 \
  --lifecycle-action-result CONTINUE
```

Wanderly 的使用例子：

- **Launch hook**：新 web instance 啟動後，先從 S3 下載當天的匯率與熱門飯店快取，完成後才讓它加入 target group，避免第一批使用者遇到慢回應。
- **Termination hook**：影像處理 worker 被縮減時，先停止從 queue 取新工作、完成手上那一張照片的處理，並把 `/var/log` 上傳到 S3，才真正關機。

### Warm pools：預先準備好的備用機器

Golden AMI 能把開機時間縮短到一兩分鐘，但有些應用的初始化本質上就很慢：例如要載入幾 GB 的機器學習模型、建立大量本機快取，需要 10 分鐘以上。這時即使用 predictive scaling，也很難應付預測之外的突發。

**Warm pool（暖機池）** 是 ASG 旁邊的一群「已經完成初始化、但還沒進入服務」的 instance。擴展時，ASG 優先從 warm pool 拿機器，省掉初始化時間。Warm pool 中的 instance 可以處於三種狀態：

| 狀態 | 費用 | 恢復速度 |
|---|---|---|
| **Stopped** | 只付 EBS 儲存與 Elastic IP 等費用，不付 instance 運算費 | 需要開機，但不需要重新初始化應用程式 |
| **Hibernated** | 同上，另含保存記憶體內容的 EBS 空間 | 記憶體內容還原，比 stopped 更快恢復到可用狀態 |
| **Running** | 和一般 instance 相同 | 最快，但最貴 |

設定重點與限制：

- 可以設定 warm pool 的大小（例如最小保留幾台、最多準備到幾台）。
- 可以設定 **instance reuse policy**，讓縮減時的 instance 回到 warm pool 而不是被 terminate。
- 搭配 lifecycle hook，讓 instance 在進入 warm pool 前完成初始化。
- **Warm pool 不支援 Spot instance，也不支援使用 instance weighting（權重，18.11 節）的 ASG**。ASG 可以用 mixed instances policy 列出多種 instance type，但必須設定為全部 On-Demand、不使用權重。這是設計時必須注意的取捨：要 warm pool 的快速擴展，就得放棄 Spot 的成本節省。（較舊的文件與考題寫成「warm pool 不能搭配 mixed instances policy」，現況已放寬為上述條件；不變的重點是 Spot 不行。）
- Warm pool 中的 instance 若無法正常進入 InService，或 warm pool 已經用完，擴展時仍會直接啟動新 instance（cold start）。

### Standby：暫時把機器拿出來

**Standby（待命）** 狀態讓你把一台 InService 的 instance 暫時移出服務：它會從 target group 取消註冊、不再接流量，ASG 也不會對它做 health check 替換，但它仍屬於這個 ASG。用途是除錯或更新單台機器。進入 standby 時可以選擇是否同時降低 desired（若不降低，ASG 會補一台新機器來維持容量）。處理完後用 exit-standby 讓它回到服務。

相較之下，**detach（分離）** 是把 instance 永久移出 ASG，之後它就是一台普通的 EC2。

## 18.9 縮減時誰先離開：termination policy 與 scale-in protection

擴展時要決定「開在哪裡」，縮減時則要決定「關掉誰」。這個選擇會影響 AZ 平衡、成本，以及正在處理工作的 instance 會不會被誤殺。

### 預設 termination policy

預設政策依序考慮：

1. **AZ 平衡優先**：先選出 instance 最多的 AZ，從那個 AZ 裡挑。這確保縮減後各 AZ 仍保持平衡。
2. **配合分配策略**：使用 mixed instances policy 時，挑選能讓剩下的 On-Demand／Spot 比例與 instance type 分配最符合設定的那台。
3. **最舊的設定**：優先關掉使用 launch configuration 或較舊 launch template 版本的 instance，讓機群逐步收斂到新版本。
4. **最接近下一個計費小時**：對以小時計費的 instance 有意義（現在多數 Linux instance 以秒計費，這一條影響較小）。
5. **隨機**：前面都無法區分時，隨機選一台。

### 其他可選的 termination policy

| Policy | 行為 | 適合 |
|---|---|---|
| `OldestInstance` | 先關最早啟動的 | 想逐步汰換舊機器 |
| `NewestInstance` | 先關最新啟動的 | 測試新 launch template 時，若有問題先移除新機器 |
| `OldestLaunchTemplate`／`OldestLaunchConfiguration` | 先關使用最舊設定的 | 收斂到新版本 |
| `ClosestToNextInstanceHour` | 先關最接近下一個計費小時的 | 以小時計費的 instance |
| `AllocationStrategy` | 依 mixed instances 分配策略 | Spot／On-Demand 混合機群 |
| Custom（Lambda） | 由你的 Lambda function 回傳要關掉的 instance | 需要依應用程式狀態決定 |

不論選哪一種，**AZ 平衡永遠先被考慮**。

### Scale-in protection：這台正在忙，先不要關

Wanderly 的影片轉檔 worker 每個工作要跑 20 分鐘，中途被關掉就得重來。Termination policy 無法知道哪台正在忙，這時可以使用 **instance scale-in protection（縮減保護）**：

- 被保護的 instance **不會因為 scale in 被選中 terminate**。
- 應用程式可以在開始一個長工作時呼叫 API 為自己開啟保護，完成後關閉保護。這是 queue worker 常見的模式。
- 保護**不影響**健康檢查替換、手動 terminate 與 Spot 中斷；它只針對「縮減」。Instance refresh 則可以在設定中選擇略過、等待或照樣替換受保護的 instance。
- 如果所有 instance 都被保護，縮減就無法進行，desired 會降低但實際數量不變，直到有 instance 解除保護。

Scale-in protection 與 termination lifecycle hook 是互補的：保護讓忙碌的機器不被選中；hook 讓被選中的機器有時間優雅收尾。

### Suspend processes：暫停某些自動行為

ASG 的行為由幾個「程序（process）」組成：`Launch`、`Terminate`、`HealthCheck`、`ReplaceUnhealthy`、`AZRebalance`、`AlarmNotification`、`ScheduledActions`、`AddToLoadBalancer`、`InstanceRefresh`。你可以暫停（suspend）其中幾個，例如：

- 排查問題時暫停 `ReplaceUnhealthy`，避免機器在你登入除錯時被替換。
- 大型維護期間暫停 `AlarmNotification`，避免 scaling policy 干擾。
- 暫停 `AZRebalance`，避免 AZ 恢復後機器被重新搬動。

暫停是臨時手段，用完要記得恢復；若只是要處理單台機器，standby 通常更合適。

## 18.10 更新整個機群：instance refresh

前面提過，修改 launch template 不會改變已在執行的 instance。當 Wanderly 每月更新 golden AMI（作業系統 patch、新版程式），需要一個安全的方式把整個機群換成新版本。

### Instance refresh 怎麼運作

**Instance refresh（instance 汰換）** 是 ASG 內建的滾動替換功能：它依照你設定的比例，分批 terminate 舊 instance 並啟動新 instance，每批新機器通過 health check 並經過 warm-up 後，才進行下一批。

關鍵設定：

- **Minimum healthy percentage**：替換過程中至少維持多少比例的健康容量，未設定 instance maintenance policy 時預設 90%。在 maximum 維持預設 100% 時，設成 90% 代表每批最多先關掉 10% 的容量再補新的。
- **Maximum healthy percentage**：允許替換過程中容量最多增加到 desired 的多少，範圍 100%–200%，預設 100%。設成超過 100% 時，ASG 可以「先啟動新的、再關掉舊的」；把 minimum 設為 100%、maximum 設為 110% 以上，替換期間容量就不會低於 desired，代價是短暫多付一些機器的費用。Minimum 與 maximum 之間的差距決定每批能替換多少台。
- **Instance warmup**：每台新 instance 被視為就緒前要等多久。
- **Checkpoints**：在完成某些百分比（例如 20%、50%）後暫停一段時間，讓你觀察新版本的錯誤率與延遲。
- **Skip matching**：已經符合新設定的 instance 不重新替換。
- **Desired configuration**：直接在 instance refresh 指定要換成的 launch template 版本，不必先修改 ASG。
- **Auto rollback**：替換失敗，或指定的 CloudWatch alarm 進入 ALARM 狀態時，自動把機群換回原本的設定。

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name wanderly-web-asg \
  --desired-configuration '{"LaunchTemplate":{"LaunchTemplateName":"wanderly-web","Version":"8"}}' \
  --preferences '{
    "MinHealthyPercentage": 90,
    "MaxHealthyPercentage": 110,
    "InstanceWarmup": 180,
    "CheckpointPercentages": [20, 50, 100],
    "CheckpointDelay": 600,
    "SkipMatching": true,
    "AutoRollback": true,
    "AlarmSpecification": {"Alarms": ["wanderly-web-5xx-high"]}
  }'
```

這個設定的意思是：健康容量不低於 desired 的 90%、也不超過 110%，因此 ASG 每批大約可以替換 20% 的機器（先多開 10%、再關掉舊的）；換完 20% 後停 10 分鐘觀察，再換到 50% 又停 10 分鐘；只要 5xx 錯誤告警響起就自動回滾。

### Instance refresh 與 blue/green 的差別

Instance refresh 是**滾動更新（rolling）**：新舊版本在同一個 ASG、同一個 target group 內短暫共存，回滾也是再滾動一次。如果需求是「新版本完整準備好、測試通過後瞬間切換，出事時瞬間切回」，就需要 **blue/green**：建立第二個 ASG（或第二個 target group），用 ALB 的加權 target group 或 Route 53 切換流量。各種部署策略的完整比較在第 37 章。

## 18.11 省錢又穩定：mixed instances policy 與 Spot

Wanderly 的機群穩定下來後，下一個問題是成本。第 17 章介紹過 **Spot instance**：使用 AWS 閒置容量，價格通常比 On-Demand 便宜很多，但 AWS 需要容量時會以 **2 分鐘通知** 中斷它。Web tier 是 stateless 的、有 ALB 分流、有 ASG 自動補機器，非常適合用一部分 Spot 來降低成本。

### Mixed instances policy 的兩個維度

**Mixed instances policy（混合 instance 政策）** 讓一個 ASG 同時使用多種 instance type，以及 On-Demand 與 Spot 兩種購買方式。

**第一個維度：On-Demand 與 Spot 的比例**

- **On-Demand base capacity**：最先滿足的 On-Demand 台數，例如 4 台。這是「無論如何都要有」的穩定容量。
- **On-Demand percentage above base**：超過 base 的部分，有多少百分比用 On-Demand，例如 20%，其餘 80% 用 Spot。

以 base 4、above base 20% 為例，當 desired 是 14 台：前 4 台 On-Demand；剩下 10 台中 2 台 On-Demand、8 台 Spot。

**第二個維度：instance type 的多樣性**

在 launch template 之外，列出多個可以使用的 instance type（overrides），例如 `m6i.large`、`m7i.large`、`m6a.large`、`m5.large`。每一種 instance type 在每個 AZ 都是一個獨立的 **Spot capacity pool（Spot 容量池）**。可選的 pool 越多，某個 pool 被大量回收時影響越小，也越不容易遇到「開不出機器」。

也可以用 **attribute-based instance type selection（依屬性選擇 instance type）**：不列出具體型號，而是指定「2–4 vCPU、8–16 GiB 記憶體」等條件，由 AWS 自動挑選所有符合的型號，包含之後新推出的世代。

**Instance weighting（權重）** 讓不同大小的 instance 貢獻不同的容量單位，例如 `large` 權重 1、`xlarge` 權重 2。此時 desired capacity 的單位就變成「容量單位」而不是台數。

### Spot 分配策略

| Spot allocation strategy | 行為 | 建議 |
|---|---|---|
| **price-capacity-optimized** | 從容量最充足的 pool 中挑價格較低的 | AWS 建議的預設選擇，兼顧中斷率與價格 |
| capacity-optimized | 只看容量最充足的 pool | 對中斷特別敏感的工作 |
| capacity-optimized-prioritized | 容量優先，同時參考你給的 instance type 順序 | 有偏好型號時 |
| lowest-price | 只看最便宜的 pool | 中斷率可能較高，不建議用於正式服務 |

On-Demand 的部分則有 `lowest-price` 與 `prioritized`（依你列出的順序）兩種策略；後者常用來搭配已購買的 Reserved Instances 或 Savings Plans 涵蓋的型號。

### Capacity Rebalancing：在中斷之前先換

AWS 在 Spot instance 中斷風險升高時，會先發出 **rebalance recommendation（重新平衡建議）**，通常比 2 分鐘中斷通知更早。ASG 啟用 **Capacity Rebalancing** 後，收到建議就會**主動在其他 pool 啟動替代的 Spot instance，等新機器就緒後再關掉高風險的那台**，讓機群在中斷真正發生前完成交接。搭配 termination lifecycle hook 與 ALB 的 deregistration delay，正在處理的請求也能完整結束。

### 什麼時候不要用 Spot

- 需要 warm pool 的 ASG（前一節的限制）。
- 機器上有不能中斷、無法重做的工作，且沒有 checkpoint 機制。
- 最低必要容量：這部分用 On-Demand base（並可以用 Savings Plans 或 RI 降低費用，第 39 章）。

## 18.12 組起來：Wanderly 的 ALB + ASG 高可用 web tier

現在把前面所有元件組成 Wanderly 的正式 web tier：

```text
                              使用者
                                │ HTTPS
                                ▼
                     [CloudFront]（靜態檔案快取，第 11 章）
                       │                     │
              /static/* ▼                     ▼ 其他路徑
                  [S3 bucket]       [ALB]（public subnet，跨 1a、1c）
                                        │ ① 只轉送給健康的 target
               ┌────────────────────────┴────────────────────────┐
               ▼                                                 ▼
   ┌─────────────────────────┐                     ┌─────────────────────────┐
   │ AZ 1a  app subnet        │                     │ AZ 1c  app subnet        │
   │  EC2  EC2  EC2(Spot)     │ ◄── ② 同一個 ASG ──► │  EC2  EC2  EC2(Spot)     │
   └───────────┬─────────────┘                     └───────────┬─────────────┘
               │ ③ session 讀寫                                  │
               ▼                                                 ▼
      [ElastiCache（Multi-AZ）]   ④ 訂單資料    [RDS Multi-AZ primary／standby]

   ⑤ Scaling：target tracking（ALBRequestCountPerTarget）+ 週五 scheduled action
   ⑥ 更新：每月新 golden AMI → launch template 新版本 → instance refresh
```

① ALB 節點分布在兩個 AZ 的 public subnet，只把請求轉送給 target group 中健康的 instance。② 一個 ASG 橫跨兩個 AZ 的 app subnet（private subnet），health check type 設為 ELB，用 mixed instances policy 混合 On-Demand base 與 Spot。③ Session 不存在 instance 上，而是放在 ElastiCache，任何 instance 被關掉都不會讓使用者登出。④ 訂單資料在 RDS Multi-AZ（第 26 章）。⑤ Target tracking 處理日常波動，scheduled action 在已知的活動前提高 min。⑥ 版本更新透過 instance refresh 滾動完成。靜態檔案（圖片、CSS、JavaScript）由 CloudFront 從 S3 提供，web 機器只處理動態請求，需要的容量大幅減少。

### Session 狀態外部化

Session 是 stateless 設計最常卡住的地方。小林的舊系統把登入 session 存在 web 機器的記憶體裡，一旦機器被縮減或替換，上面的使用者就會被登出、購物車清空。有三種解法：

| 做法 | 原理 | 問題 |
|---|---|---|
| **Sticky sessions（黏性 session）** | ALB 用 cookie 讓同一個使用者固定送到同一台 instance（第 10 章） | 機器被關掉時 session 仍會遺失；負載可能不平均；只是延後問題 |
| **外部 session store** | Session 存在 **ElastiCache**（Redis OSS／Valkey）或 **DynamoDB**，所有 instance 共用 | 多一個元件要管理，但任何 instance 都能處理任何請求 |
| **Stateless token** | 使用簽章的 token（例如 JWT），必要資訊放在 token 裡由 client 攜帶 | Token 撤銷較麻煩，大小有限 |

考試題目寫「scale in 時使用者被登出」「需要讓任何 instance 都能處理任何使用者的請求」，答案是**外部 session store**：要求低延遲選 ElastiCache，要求 serverless、免管理、高耐久選 DynamoDB（第 27、28 章）。Sticky sessions 幾乎都是錯誤選項，因為它無法在 instance 消失時保住 session。

### Deregistration delay：讓進行中的請求做完

Instance 要被縮減時，ASG 會先把它從 target group 取消註冊。ALB 收到取消註冊後，不再送新請求給它，但會等待 **deregistration delay（取消註冊延遲，也稱 connection draining）** 讓進行中的請求完成，預設 300 秒。之後 ASG 才 terminate 它。

如果 Wanderly 的 API 請求都在 2 秒內完成，把 deregistration delay 降到 30 秒，可以讓縮減與 instance refresh 快很多；如果有長時間的檔案上傳，則要保持較長的值。

### 用 CloudFormation 描述（節錄）

```yaml
Resources:
  WebLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: wanderly-web
      LaunchTemplateData:
        ImageId: !Ref GoldenAmiId           # 每月由 Image Builder 產生
        InstanceType: m7i.large
        IamInstanceProfile:
          Arn: !GetAtt WebInstanceProfile.Arn
        SecurityGroupIds:
          - !Ref WebSecurityGroup           # 只允許來自 ALB security group 的流量
        MetadataOptions:
          HttpTokens: required              # 強制 IMDSv2

  WebAsg:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      MinSize: "4"
      MaxSize: "40"
      DesiredCapacity: "4"
      VPCZoneIdentifier:                    # 兩個 AZ 的 private app subnet
        - !Ref AppSubnetA
        - !Ref AppSubnetC
      TargetGroupARNs:
        - !Ref WebTargetGroup
      HealthCheckType: ELB                  # 應用程式故障也會被替換
      HealthCheckGracePeriod: 180
      DefaultInstanceWarmup: 120
      CapacityRebalance: true
      MixedInstancesPolicy:
        InstancesDistribution:
          OnDemandBaseCapacity: 4
          OnDemandPercentageAboveBaseCapacity: 20
          SpotAllocationStrategy: price-capacity-optimized
        LaunchTemplate:
          LaunchTemplateSpecification:
            LaunchTemplateId: !Ref WebLaunchTemplate
            Version: !GetAtt WebLaunchTemplate.LatestVersionNumber
          Overrides:
            - InstanceType: m7i.large
            - InstanceType: m6i.large
            - InstanceType: m6a.large
            - InstanceType: m5.large

  RequestTracking:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref WebAsg
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ALBRequestCountPerTarget
          ResourceLabel: !Sub "${WebAlb.LoadBalancerFullName}/${WebTargetGroup.TargetGroupFullName}"
        TargetValue: 300                    # 每台每分鐘約 300 個請求
```

讀這段 template 時注意：launch template 沒有 subnet，subnet 在 ASG 的 `VPCZoneIdentifier`；ASG 引用的是明確的版本號，而不是 `$Latest`；`HealthCheckType: ELB` 讓 ALB 的健康判斷也能觸發替換；`MinSize` 4 搭配 On-Demand base 4，代表即使所有 Spot 都被回收，仍有 4 台 On-Demand 在服務。`TargetValue` 的數字要靠壓力測試決定：找出單台在延遲仍可接受時能處理的請求數，再留一些餘裕。

## 18.13 除錯：Auto Scaling 不如預期時

**情境 A：desired 提高了，但 instance 開不出來**

1. 看 ASG 的 **activity history**，裡面會寫失敗原因。
2. `InsufficientInstanceCapacity`：該 AZ 的這個 instance type 暫時沒容量 → 增加 instance type 種類、增加 AZ。
3. Subnet 沒有可用 IP → 擴充 subnet 或新增 subnet（第 5 章）。
4. 超過帳號的 vCPU quota → 申請提高 quota（第 35 章）。
5. AMI 不存在、沒有共享權限，或 EBS 加密用的 KMS key 沒有授權給 Auto Scaling 的 service-linked role → 修正權限（第 15 章）。
6. Launch template 參數錯誤（security group 與 subnet 不在同一個 VPC、instance type 不支援該 AMI 的架構）。

**情境 B：instance 一直被替換（開了又關）**

1. Health check grace period 是否短於實際開機時間？
2. ALB health check 路徑是否正確、security group 是否允許 ALB 連到 health check port？
3. Health check 是否太深，下游一慢就全部失敗？
4. 暫停 `ReplaceUnhealthy` 或把一台放進 standby，登入檢查。

**情境 C：一直擴展到 max，或來回震盪**

1. Target tracking 的 metric 是否會隨 instance 增加而下降？
2. 是否沒有設定 warm-up，開機中的 CPU 被計入？
3. 瓶頸是否其實在資料庫？加 web 機器解決不了資料庫的問題。

**情境 D：ALB 顯示 unhealthy，ASG 卻不處理**

1. ASG 的 health check type 是否只有 EC2？改為 ELB。

## 18.14 比較與選型

### 我該用哪種 scaling 方式？

```text
流量變化可以事先知道嗎？
├─ 知道確切時間（活動、開賣、固定時段）
│     → Scheduled action（提高 min），再加 target tracking 處理超出預期的部分
├─ 有規律的每日／每週週期，且有足夠歷史
│     → Predictive scaling（先 forecast only 驗證）+ target tracking
└─ 不可預測
      ├─ 有一個與容量成比例的 metric（CPU、每台請求數、每台 backlog）
      │     → Target tracking（首選）
      └─ 需要依超標程度分段、對劇烈飆升加大力道
            → Step scaling
開機時間太長，以上都來不及？
      → 先縮短：golden AMI；仍不夠 → warm pool（限 On-Demand，不能用 Spot 與 instance weighting）
```

### 「機器準備好之前／之後」的工具對照

| 需求 | 工具 |
|---|---|
| 新機器還沒準備好，別判它不健康 | Health check grace period |
| 新機器的 metric 還不穩定，別算進去 | Default instance warmup |
| 新機器開機前要做準備工作 | Launch lifecycle hook |
| 機器被關之前要做收尾 | Termination lifecycle hook + deregistration delay |
| 正在做長工作的機器不要被縮掉 | Instance scale-in protection |
| 暫時把一台拿出來除錯 | Standby |
| 擴展要更快 | Golden AMI、warm pool、scheduled／predictive |
| 換新版本 AMI | Launch template 新版本 + instance refresh |
| Spot 被中斷前先換 | Capacity Rebalancing |

### Session 存放選擇

| 選項 | 撐得過 instance 被關？ | 延遲 | 管理負擔 | 考試定位 |
|---|---|---|---|---|
| Instance 記憶體 | 否 | 最低 | 無 | 錯誤答案 |
| Sticky sessions | 否 | 低 | 低 | 通常是錯誤答案 |
| ElastiCache | 是 | 次毫秒級 | 中 | 低延遲 session store |
| DynamoDB | 是 | 個位數毫秒 | 低（serverless） | 免管理 session store |

## 18.15 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| ALB 顯示 unhealthy，但 instance 沒有被替換 | ASG health check type 改為 ELB |
| 單台 EC2 故障要自動恢復、成本最低 | ASG min = max = desired = 1（或跨 AZ 的 2） |
| 每天／每週固定時間的尖峰 | Scheduled action（提高 min） |
| 有規律的週期流量、開機慢、要提前準備 | Predictive scaling |
| 讓平均 CPU／每台請求數維持在某個值 | Target tracking |
| SQS worker 要依 queue 長度擴展 | Custom metric：backlog per instance + target tracking |
| 新 instance 開機要 10 分鐘、擴展太慢 | Golden AMI；再不夠用 warm pool |
| 新 instance 一開機就被判定不健康而反覆替換 | 延長 health check grace period |
| 被縮減前要上傳 log／完成工作 | Termination lifecycle hook |
| 長時間工作不能被 scale in 中斷 | Instance scale-in protection |
| 更新 AMI 並滾動替換整個機群、出錯自動回退 | Instance refresh（checkpoint、auto rollback） |
| Scale in 後使用者被登出 | Session 外部化到 ElastiCache 或 DynamoDB |
| 降低 stateless web tier 成本、仍要有穩定基礎容量 | Mixed instances：On-Demand base + Spot（price-capacity-optimized、多種 instance type） |
| Spot 中斷前先替換 | Capacity Rebalancing |
| 暫時把 instance 移出服務除錯 | Standby |
| 一個 AZ 故障時仍要有足夠容量 | 多 AZ + 每個 AZ 預留足夠容量（static stability，18.16 節） |

**常見陷阱**：

1. 以為修改 launch template 會更新現有 instance：只影響之後新啟動的，現有機群要用 instance refresh。
2. 以為 ASG 會自動使用 ALB 的健康檢查：預設只有 EC2 status check，ELB health check 要手動啟用。
3. 用「ALB 總請求數」或「平均延遲」做 target tracking：這些 metric 不會因為加機器而成比例下降。
4. 選 simple scaling 處理突發流量：cooldown 期間不會再擴展，反應太慢。
5. 用 sticky sessions 解決「scale in 後使用者被登出」：instance 一被關掉，session 仍然遺失。
6. 為使用 Spot（或 instance weighting）的 ASG 加 warm pool：不支援；warm pool 只能搭配 On-Demand。
7. 只用 scheduled action 調高 desired 而不調高 min：dynamic policy 可能在活動前就把容量縮回去。
8. 以為 ASG 的 max 保證容量開得出來：容量不足、IP 不足、quota 不足都會讓啟動失敗。

## 18.16 SAP 加深：static stability、容量保證與大規模機群治理

SAA 題目問「怎麼讓 web tier 自動擴展」；SAP 題目問的是「一個 AZ 故障時，在完全不依賴擴展的情況下，服務還撐得住嗎？幾十個帳號的機群要怎麼一致地更新？」

### Static stability：不要在故障時才擴展

**Static stability（靜態穩定）** 是 AWS 自己設計系統時的重要原則：系統在相依元件故障時，**不需要做任何改變**就能繼續運作。對 web tier 而言，它的意思是：「AZ 故障時，靠剩下 AZ 裡已經在跑的機器撐住，而不是等 ASG 在剩下的 AZ 開新機器。」

原因是：AZ 故障時，所有客戶都會同時在剩下的 AZ 擴展，容量可能一時吃緊；control plane 操作（啟動 instance）在大規模事件中也可能變慢。依賴「故障時擴展」等於把恢復押在最不穩定的時刻。

計算方式：若 Wanderly 尖峰需要 12 台才能撐住流量：

| 部署 | 平時 | 一個 AZ 故障後剩下 | 是否 static stable |
|---|---|---|---|
| 2 個 AZ × 6 台 | 12 台 | 6 台 | 否，需要再擴展 6 台 |
| 2 個 AZ × 12 台 | 24 台 | 12 台 | 是，但平時多付 100% |
| 3 個 AZ × 6 台 | 18 台 | 12 台 | 是，平時只多付 50% |

使用越多 AZ，為了 static stability 需要多準備的比例就越小（N 個 AZ 時，每個 AZ 要能承擔 1/(N−1) 的流量）。這是 SAP 題目選「三個 AZ」而不是「兩個 AZ」的常見理由。

### 容量保證：On-Demand Capacity Reservations

ASG 的 max 不保證容量。對「AZ 故障時一定要開得出機器」或「年度大促一定要有 200 台特定機型」這類需求，可以使用 **On-Demand Capacity Reservations（容量保留）**：在指定 AZ 為指定 instance type 保留容量，不論是否使用都按 On-Demand 價格計費，可以搭配 Savings Plans 或 Regional RI 取得折扣（第 17、39 章）。ASG 可以設定優先使用保留的容量。

### 與 AZ 故障處理的整合

當某個 AZ 出現「沒有全掛，但表現異常」的灰色故障時，AWS 提供 **Route 53 Application Recovery Controller（ARC）的 zonal shift**，可以暫時把 ALB 等資源的流量移出受影響的 AZ（第 34 章）。設計重點仍然是 static stability：把流量移走後，剩下的 AZ 必須已經有足夠容量。

### 多帳號的 AMI 與機群更新

Wanderly 進入企業期後（Part 8），有數十個帳號各自有 ASG。常見的集中化做法：

1. **集中產生 golden AMI**：在一個工具帳號用 EC2 Image Builder 產生 AMI，並透過 AMI 共享（或 Image Builder 的分發設定）分發到各帳號與 Region。若 AMI 的 EBS snapshot 使用 customer managed KMS key 加密，必須同時把 KMS key 的使用權授予目標帳號，否則 ASG 啟動會失敗。
2. **用 SSM Parameter Store 發布最新 AMI ID**：launch template 可以直接引用 SSM parameter（`resolve:ssm:` 語法），各帳號不必手動複製 AMI ID。
3. **用 instance refresh 統一滾動更新**：搭配 checkpoint 與 alarm-based auto rollback，先在非正式環境帳號執行，再推進到正式環境（第 37 章的部署管線）。
4. **用 AWS Config rules 或 SCP 治理**：例如要求所有 ASG 使用 launch template、要求 IMDSv2、要求跨至少兩個 AZ（第 14、16 章）。

### 擴展的上游與下游

SAP 題目常把「web tier 擴展」放進更大的系統：web tier 可以在幾分鐘內擴到 10 倍，但後面的 RDS 連線數、第三方 API 的速率限制不一定跟得上。擴展設計要包含：

- 用 RDS Proxy 或連線池保護資料庫（第 26 章）。
- 用 queue 把寫入削峰（第 32 章）。
- 設定 ASG 的 max，作為下游能承受的上限，而不只是成本上限。
- 優雅降級：容量不足時先關閉推薦、評論等非核心功能（第 35 章）。

## 本章重點整理

- EC2 Auto Scaling 管理機器數量，Load Balancer 分配流量；兩者搭配才是完整的高可用 web tier，而應用程式必須是 stateless 的。
- Launch template 是有版本的新機器藍圖，不含 subnet；修改它只影響之後新啟動的 instance，launch configuration 是不建議再使用的舊機制。
- ASG 不斷比對 desired 與實際健康數量：少了就依 launch template 補、多了就依 termination policy 關，scaling policy 唯一做的事是修改 desired。
- ASG 跨多個 AZ 的 subnet 部署並自動維持各 AZ 平衡；AZ 故障時會在其他 AZ 補機器，AZRebalance 會先開新機器再關舊機器。
- ASG 預設只用 EC2 status check；要讓應用程式層的故障也觸發替換，必須啟用 ELB health check，並設定足夠的 health check grace period。
- Target tracking 是首選 scaling policy，但 metric 必須隨 instance 增加而成比例下降，例如平均 CPU、`ALBRequestCountPerTarget` 或每台的 queue backlog。
- 已知時間的尖峰用 scheduled action 提高 min；有規律的週期流量用 predictive scaling 提前擴展；simple scaling 因 cooldown 而反應太慢，不建議使用。
- Default instance warmup 讓新 instance 的 metric 在穩定前不被納入計算，避免過度擴展；cooldown 只用於 simple scaling。
- Lifecycle hook 讓 instance 在進入服務前或終止前暫停做準備或收尾；scale-in protection 讓忙碌的 instance 不被縮減選中；standby 讓你暫時把 instance 移出服務。
- Warm pool 預先初始化 instance 以加速擴展，stopped 狀態只需支付儲存等費用，但不支援 Spot 與 instance weighting，只能搭配 On-Demand。
- 預設 termination policy 先維持 AZ 平衡，再依分配策略、最舊設定、計費時間決定；instance refresh 以 minimum／maximum healthy percentage、checkpoint 與 auto rollback 滾動更新整個機群。
- Mixed instances policy 以 On-Demand base 保住基礎容量、以多種 instance type 的 Spot 承擔彈性部分，搭配 price-capacity-optimized 與 Capacity Rebalancing 降低中斷影響。
- Session 要外部化到 ElastiCache 或 DynamoDB；sticky sessions 無法在 instance 被關掉時保住 session；deregistration delay 讓進行中的請求在縮減前完成。
- SAP 層級的 static stability 要求每個 AZ 預先準備足夠容量，使一個 AZ 故障時不必擴展也能撐住；需要保證特定容量時使用 On-Demand Capacity Reservations。

## 本章練習題

### 練習 18-1｜SAA｜單選｜ELB health check 與自動替換

Wanderly 的 web tier 由一個跨兩個 AZ 的 Auto Scaling group 與一個 Application Load Balancer 組成。某次記憶體洩漏讓兩台 instance 的應用程式停止回應，ALB 的 target group 很快把它們標示為 unhealthy 並停止送流量，但這兩台 instance 持續存在了好幾個小時，ASG 也沒有啟動替代的 instance。EC2 status checks 顯示這兩台都通過檢查。

應如何修改，才能讓這類應用程式故障自動被替換？

- A. 把 ALB health check 的 interval 縮短，並降低 unhealthy threshold
- B. 為 ASG 啟用 ELB health check，讓 target group 的健康狀態也作為替換依據
- C. 啟用 EC2 auto recovery，讓 instance 在故障時自動復原
- D. 啟用 ALB 的 sticky sessions，避免使用者被送到故障的 instance

> [!answer]- 答案：B
> **A ✗** ALB 已經正確判定 target 不健康，問題不在偵測速度，而是 ASG 不使用這個判斷。縮短 interval 只會讓 ALB 更早停止送流量，instance 仍不會被替換。
>
> **B ✓** ASG 預設只使用 EC2 status checks，它只知道機器在 running，不知道應用程式卡死。把 health check type 設為 ELB 後，target group 判定不健康的 instance 也會被 ASG terminate 並替換，機群容量才能自我修復。
>
> **C ✗** EC2 auto recovery 處理的是底層硬體或系統狀態檢查失敗；這兩台的 status checks 都通過，auto recovery 不會被觸發。
>
> **D ✗** Sticky sessions 會把使用者固定送到某台 instance，與故障替換無關；ALB 本來就不會把流量送給 unhealthy target。
>
> **考點**：SAA-2.2｜ASG health check type：EC2 vs ELB

### 練習 18-2｜SAA｜單選｜已知時段的流量尖峰

Wanderly 每週五晚上 20:00（台北時間）都會推出限時特價，流量會在兩分鐘內升到平常的八倍，持續約兩小時。目前 ASG 使用 CPU 的 target tracking policy，但新 instance 需要約 4 分鐘才能通過 health check，每次活動開始的前幾分鐘都有大量 timeout。團隊希望以最少的營運負擔解決。

最合適的做法是什麼？

- A. 改用 simple scaling，並把 cooldown 設為 0 秒
- B. 把 target tracking 的目標 CPU 從 50% 降到 20%，讓它更早擴展
- C. 啟用 predictive scaling，並刪除 target tracking policy
- D. 建立每週五 19:40 的 scheduled action 提高 min 與 desired，活動結束後再用另一個 scheduled action 調回原值，並保留 target tracking 處理超出預期的流量

> [!answer]- 答案：D
> **A ✗** Simple scaling 仍然要等 CPU 升高後才反應，新 instance 4 分鐘的開機時間依舊存在；把 cooldown 設為 0 還可能被開機中的 metric 誤導而過度擴展。
>
> **B ✗** 降低目標值會讓整週都維持大量閒置容量，成本大增；而且流量在兩分鐘內暴增時，仍趕不上 4 分鐘的開機時間。
>
> **C ✗** Predictive scaling 適合有規律的週期流量，每週固定一次的活動理論上可被學到，但它需要足夠歷史、預測可能有誤差；刪除 target tracking 後，超出預測的流量將無人處理。時間已確切知道時，scheduled action 更直接。
>
> **D ✓** 活動時間是確切已知的，scheduled action 能在流量到來前就把容量準備好。提高 min（而不只是 desired）可以避免 target tracking 在活動前因 CPU 低而縮回容量；保留 target tracking 則處理比預期更大的流量。
>
> **考點**：SAA-3.2｜scheduled scaling 與 dynamic scaling 搭配

### 練習 18-3｜SAA｜單選｜Target tracking metric 選擇

Wanderly 的搜尋 API 跑在 ALB 後面的 ASG 上。壓力測試顯示，每台 instance 在延遲可接受的前提下大約能處理每分鐘 400 個請求，瓶頸是應用程式的執行緒數而不是 CPU（CPU 始終低於 40%）。團隊要設定一個 target tracking policy，讓容量隨請求量自動調整。

應使用哪個 metric？

- A. `ALBRequestCountPerTarget`，目標值約 300
- B. ALB 的總請求數 `RequestCount`，目標值 400
- C. `ASGAverageCPUUtilization`，目標值 40%
- D. ALB 的 `TargetResponseTime`，目標值 200 毫秒

> [!answer]- 答案：A
> **A ✓** 每台 target 的請求數會隨 instance 增加而成比例下降，符合 target tracking 的前提；瓶頸本來就是每台能處理的請求量，把目標設在測得上限 400 以下（例如 300）可以保留餘裕。
>
> **B ✗** 總請求數不會因為加機器而下降，policy 會持續擴展直到 max，無法收斂。
>
> **C ✗** 題目說明瓶頸不在 CPU，CPU 始終低於 40%；用 CPU 追蹤會在執行緒耗盡、延遲已經上升時仍然不擴展。
>
> **D ✗** 延遲受很多因素影響（例如下游資料庫），不一定隨 web instance 增加而成比例下降；以它為 target tracking metric 容易造成持續擴展或無效擴展。
>
> **考點**：SAA-3.2｜target tracking metric 必須與容量成比例

### 練習 18-4｜SAP｜單選｜SQS worker 的擴展訊號

Wanderly 的發票產生服務由一個 ASG 的 worker 從 SQS standard queue 取出訊息處理。每台 worker 平均每秒完成 5 則訊息，業務 SLO 要求訊息從進入 queue 到處理完成不超過 2 分鐘。目前用平均 CPU 做 target tracking，但 worker 大部分時間在等外部 API，CPU 只有 20%，月底 queue 累積到數萬則訊息時 ASG 幾乎沒有擴展。

應如何重新設計擴展機制？

- A. 對 queue 的 `ApproximateNumberOfMessagesVisible` 直接做 target tracking，目標值 600
- B. 改用 step scaling，當 CPU 超過 15% 時增加 5 台
- C. 定期計算「可見訊息數 ÷ InService instance 數」並發布為 custom metric，以 target tracking 追蹤目標值 600
- D. 把 queue 的 visibility timeout 延長到 12 小時，讓 worker 有更多時間處理

> [!answer]- 答案：C
> **A ✗** Queue 中的總訊息數不會因為加機器而成比例下降，相同的數字在 2 台和 20 台時代表的壓力完全不同，target tracking 會擴展過頭或不足。
>
> **B ✗** CPU 與這個工作的負載沒有對應關係，worker 在等外部 API 時 CPU 很低；降低門檻只會讓機群在 queue 空的時候也被擴展，問題沒有解決。
>
> **C ✓** 每台 worker 可接受的積壓量 = 每秒 5 則 × 120 秒 = 600 則。Backlog per instance 會隨 instance 增加而下降，符合 target tracking 的前提，是 AWS 建議的 queue worker 擴展方式。這個 metric 需要自行計算並發布到 CloudWatch。
>
> **D ✗** Visibility timeout 控制訊息被取走後多久會重新出現，與處理容量無關；延長它不會讓積壓變少，反而讓失敗的訊息更晚被重試。
>
> **考點**：SAP-2.5、SAP-3.3｜queue backlog per instance custom metric

### 練習 18-5｜SAA｜單選｜初始化很慢的應用程式

Wanderly 的推薦服務在啟動時要從 S3 載入 6 GB 的模型並建立記憶體索引，從 instance 啟動到可以服務需要 12 分鐘，已經使用了預先安裝好所有軟體的 golden AMI。流量突發時，target tracking 雖然很快提高了 desired，但新容量總是 12 分鐘後才到位。ASG 只使用單一 instance type 的 On-Demand instance。團隊希望大幅縮短擴展時間，同時讓閒置的備用容量成本盡量低。

最合適的做法是什麼？

- A. 為 ASG 加入 warm pool，讓預先完成初始化的 instance 以 hibernated 狀態待命
- B. 把 min 提高到尖峰需要的數量，讓機器永遠在執行
- C. 改用 mixed instances policy 並加入 Spot instance，以更便宜的價格擴展
- D. 把 health check grace period 縮短到 60 秒，讓新 instance 更早被視為可用

> [!answer]- 答案：A
> **A ✓** Warm pool 中的 instance 已經完成初始化（可以搭配 lifecycle hook 確保模型與記憶體索引都已建立），擴展時直接從 warm pool 取出，不必重新經歷 12 分鐘的準備。Hibernated 狀態會把記憶體內容保存到 EBS，恢復時記憶體索引仍在，而待命期間只需支付儲存費用、不付運算費用，符合低成本待命的要求。這個 ASG 是單一 instance type 的 On-Demand，符合 warm pool 的使用條件。
>
> **B ✗** 永遠維持尖峰容量可以解決速度問題，但大部分時間都在為閒置的運算容量付費，違反成本要求。
>
> **C ✗** Spot 只降低價格，不會縮短初始化時間；而且啟動 Spot instance 的 ASG 無法使用 warm pool。
>
> **D ✗** 縮短 grace period 不會讓應用程式更快準備好，反而可能讓還在載入模型的 instance 被判為不健康而被替換。
>
> **考點**：SAA-3.2、SAA-4.2｜warm pool 加速擴展

### 練習 18-6｜SAA｜單選｜縮減前的收尾工作

Wanderly 的影像處理 worker 會把處理日誌暫存在本機磁碟，每 15 分鐘批次上傳到 S3。最近發現 ASG 縮減時，被 terminate 的 instance 上最後一段日誌全部遺失，稽核要求日誌不能遺失。團隊希望不修改上傳週期。

最合適的做法是什麼？

- A. 為 ASG 啟用 instance scale-in protection，讓所有 instance 都不會被縮減
- B. 把 ALB target group 的 deregistration delay 延長到 3,600 秒
- C. 把 launch template 的 root volume 設定為 terminate 時不刪除，再定期人工收集日誌
- D. 建立 termination lifecycle hook，透過 EventBridge 觸發腳本在 instance 上傳剩餘日誌，完成後呼叫 complete-lifecycle-action

> [!answer]- 答案：D
> **A ✗** 對所有 instance 開啟保護等於讓 ASG 無法縮減，失去彈性並增加成本；scale-in protection 適合「暫時保護正在忙的 instance」，不是用來做收尾。
>
> **B ✗** Deregistration delay 只是讓 ALB 等待進行中的請求完成，instance 不會因此知道要上傳日誌；而且這組 worker 從 queue 取工作，不一定有 ALB。
>
> **C ✗** 保留 EBS volume 可以留下資料，但需要人工收集與清理，營運負擔高，也容易累積大量孤兒 volume 產生費用。
>
> **D ✓** Termination lifecycle hook 讓 instance 停在 `Terminating:Wait`，給收尾程式時間上傳剩餘日誌；完成後呼叫 complete-lifecycle-action 讓 terminate 繼續。Heartbeat timeout 與 default result 能確保程式異常時 instance 最終仍會被關閉。
>
> **考點**：SAA-2.2｜termination lifecycle hook

### 練習 18-7｜SAA｜單選｜縮減後使用者被登出

Wanderly 的會員網站把登入 session 存在每台 web instance 的記憶體中，並在 ALB 啟用了 sticky sessions。每次 ASG 在深夜縮減後，就有部分使用者反映被登出、購物車被清空。團隊希望任何 instance 被移除都不影響使用者，且 session 讀寫延遲要在毫秒以下。

最合適的做法是什麼？

- A. 把 sticky sessions 的 cookie 有效時間延長到 7 天
- B. 把 session 存放到 Amazon ElastiCache，讓所有 web instance 共用
- C. 為所有 web instance 開啟 scale-in protection
- D. 把 session 寫入每台 instance 掛載的 EBS volume，並啟用 EBS snapshot

> [!answer]- 答案：B
> **A ✗** Sticky sessions 只決定使用者被送到哪一台；那台 instance 被 terminate 後，存在它記憶體中的 session 仍會遺失，延長 cookie 時間沒有幫助。
>
> **B ✓** 把 session 外部化到 ElastiCache 後，web tier 變成 stateless，任何 instance 都能處理任何使用者的請求，縮減與替換都不影響登入狀態；ElastiCache 提供次毫秒級的讀寫延遲。
>
> **C ✗** 讓所有 instance 都不被縮減，等於放棄 Auto Scaling 的彈性；而且健康檢查替換與 Spot 中斷仍會移除 instance。
>
> **D ✗** EBS volume 只屬於單一 instance 與單一 AZ，其他 instance 讀不到；snapshot 是備份機制，不能作為即時共用的 session 儲存。
>
> **考點**：SAA-2.1、SAA-2.2｜session 狀態外部化

### 練習 18-8｜SAA｜選兩項｜以 Spot 降低 web tier 成本

Wanderly 的 stateless web tier 平常需要 6 台 instance，尖峰時需要 30 台。財務要求大幅降低運算成本，但營運團隊要求：即使 Spot 容量全部被回收，仍要保有平常需要的 6 台；而且 Spot 中斷造成的容量波動要盡量小。

哪兩個設定組合最合適？（選兩項）

- A. 使用 mixed instances policy，設定 On-Demand base capacity 為 6，超過 base 的部分大多使用 Spot
- B. 只指定一種最便宜的 instance type，Spot allocation strategy 設為 lowest-price
- C. 列出多種相容的 instance type 並跨多個 AZ，Spot allocation strategy 設為 price-capacity-optimized，並啟用 Capacity Rebalancing
- D. 為 ASG 加入 warm pool，讓被中斷的 Spot instance 能快速恢復
- E. 把所有 instance 改為 Spot，並把 min 提高到 30 台

> [!answer]- 答案：A、C
> **A ✓** On-Demand base capacity 是最先滿足、不受 Spot 回收影響的 On-Demand 容量；設為 6 就保住了平常需要的基礎容量，彈性部分用 Spot 大幅降低成本。
>
> **B ✗** 單一 instance type 代表每個 AZ 只有一個 Spot capacity pool，該 pool 一旦被大量回收，容量會同時大幅下降；lowest-price 只看價格，中斷率可能較高。
>
> **C ✓** 多種 instance type 跨多個 AZ 產生很多獨立的 Spot pool，price-capacity-optimized 從容量充足的 pool 中挑價格較低的，降低中斷機率；Capacity Rebalancing 在收到 rebalance recommendation 時先啟動替代 instance，減少中斷造成的容量波動。
>
> **D ✗** Warm pool 不支援 Spot instance，這個以 Spot 為主的機群無法使用 warm pool；而且被中斷的 Spot instance 本來就會被回收，不會「恢復」。
>
> **E ✗** 全部使用 Spot 無法保證「Spot 全被回收時仍有 6 台」；把 min 提高到 30 也讓平常多付大量閒置容量。
>
> **考點**：SAA-4.2、SAA-2.2｜mixed instances policy、Spot 分配策略與 Capacity Rebalancing

### 練習 18-9｜SAA｜單選｜預設 termination policy

一個使用預設 termination policy 的 ASG 跨 AZ-a 與 AZ-b 部署，目前 AZ-a 有 4 台、AZ-b 有 3 台 instance，全部使用同一個 launch template。AZ-a 中有兩台使用 launch template 版本 3，其餘五台使用版本 4。Scaling policy 現在要縮減 1 台，沒有任何 instance 開啟 scale-in protection，也沒有使用 mixed instances policy。

ASG 最可能 terminate 哪一台？

- A. AZ-b 中最早啟動的 instance
- B. 整個 ASG 中 CPU 使用率最低的 instance
- C. AZ-a 中使用 launch template 版本 3 的其中一台
- D. AZ-a 中最新啟動的 instance

> [!answer]- 答案：C
> **A ✗** 預設政策首先維持 AZ 平衡，會從 instance 較多的 AZ-a 挑選；從 AZ-b 縮減會讓兩邊變成 4 比 2，更不平衡。
>
> **B ✗** 預設 termination policy 不看 CPU 使用率；若需要依應用程式狀態選擇，要用 custom termination policy（Lambda）或 scale-in protection。
>
> **C ✓** 預設政策先選出 instance 最多的 AZ（AZ-a），再在該 AZ 中優先選擇使用最舊 launch template 版本的 instance（版本 3），讓機群逐步收斂到新版本。
>
> **D ✗** 「最新啟動的先關」是 `NewestInstance` policy 的行為，不是預設政策。
>
> **考點**：SAA-2.2｜預設 termination policy 的順序

### 練習 18-10｜SAA｜單選｜擴展時無法啟動 instance

Wanderly 的 ASG 只使用 `c7i.2xlarge` 一種 instance type，部署在單一 AZ 的一個 subnet。大型活動期間，scaling policy 把 desired 從 10 提高到 40，但 activity history 顯示多次 `InsufficientInstanceCapacity` 錯誤，實際只開出 18 台。團隊希望提高之後擴展成功的機率，同時改善可用性。

最合適的做法是什麼？

- A. 把 ASG 的 max 從 40 提高到 80
- B. 改用 simple scaling，讓 ASG 分批慢慢啟動 instance
- C. 把 health check grace period 延長，避免啟動失敗被計入
- D. 為 ASG 加入其他 AZ 的 subnet，並以 mixed instances policy 列出多種規格相近的 instance type

> [!answer]- 答案：D
> **A ✗** Max 只是上限，現在連 40 台都開不出來，提高上限不會增加 AWS 在該 AZ 的可用容量。
>
> **B ✗** Scaling policy 的類型只決定 desired 怎麼變，不影響 instance type 在該 AZ 的容量是否足夠。
>
> **C ✗** Grace period 影響的是 health check 判斷，`InsufficientInstanceCapacity` 是啟動階段就失敗，與 grace period 無關。
>
> **D ✓** `InsufficientInstanceCapacity` 表示這個 instance type 在這個 AZ 暫時沒有足夠容量。增加 AZ 與 instance type 的組合，讓 ASG 有更多選擇，能大幅提高啟動成功率；跨多 AZ 也同時消除單一 AZ 的故障風險。
>
> **考點**：SAA-2.2、SAA-3.2｜多 AZ 與多 instance type 提高容量取得率

### 練習 18-11｜SAP｜單選｜安全地更新整個機群

Wanderly 每月由 EC2 Image Builder 產生新的 golden AMI。正式環境的 ASG 有 60 台 instance，過去由工程師手動逐批 terminate 舊機器讓 ASG 補新機器，曾因為新 AMI 的設定錯誤造成 30 分鐘的 5xx 錯誤。團隊要求：更新過程中容量不得低於 desired、能在早期發現問題並自動回到舊版本，且營運負擔最低。

最合適的做法是什麼？

- A. 建立新版 launch template，啟動 instance refresh：minimum healthy percentage 100%、maximum healthy percentage 110%，設定 checkpoint，並以 5xx 錯誤率的 CloudWatch alarm 啟用 auto rollback
- B. 把 launch template 改為 `$Latest`，等待 ASG 在日常縮減與擴展中自然汰換舊 instance
- C. 建立新版 launch template，暫停 ASG 的 `Terminate` 程序，再手動啟動 60 台新 instance 並註冊到 target group
- D. 建立第二個 ASG 使用新 AMI，切換流量後立即刪除舊 ASG，若有問題再從舊 AMI 重建

> [!answer]- 答案：A
> **A ✓** Instance refresh 是 ASG 內建的滾動替換。Minimum healthy 100% 搭配 maximum healthy 110%，代表先啟動新 instance、通過 health check 與 warm-up 後才關掉舊的，容量不會低於 desired；checkpoint 讓前幾批先接受觀察；alarm-based auto rollback 在 5xx 告警時自動回到原本的 launch template 版本。全部由 ASG 執行，營運負擔最低。
>
> **B ✗** `$Latest` 只影響之後新啟動的 instance，汰換時間不可預期，可能好幾週機群都是新舊混合；而且沒有任何驗證或回滾機制。
>
> **C ✗** 手動啟動並註冊 instance 不在 ASG 的管理流程內，營運負擔高、容易出錯，也沒有自動回滾。
>
> **D ✗** Blue/green 可以快速切換，但「立即刪除舊 ASG」讓回滾必須從頭重建，失去 blue/green 最大的價值；同時需要額外的流量切換設計，營運負擔比內建的 instance refresh 高。
>
> **考點**：SAP-2.1、SAP-3.4｜instance refresh 的 healthy percentage、checkpoint 與 auto rollback

### 練習 18-12｜SAP｜選兩項｜AZ 故障時的 static stability

Wanderly 的訂房 web tier 在尖峰時需要 12 台 `m7i.large` 才能維持 SLO。目前 ASG 跨兩個 AZ、各 6 台，依賴 target tracking 在 AZ 故障時於另一個 AZ 擴展。一次區域性事件中，另一個 AZ 擴展花了 20 多分鐘，SLO 嚴重違反。新的要求是：任何一個 AZ 故障時，不依賴當下擴展就能維持尖峰容量，並在滿足需求的前提下控制成本。

哪兩個做法最合適？（選兩項）

- A. 把 ASG 擴展到三個 AZ，並讓每個 AZ 平時就維持 6 台（共 18 台）
- B. 維持兩個 AZ，但把 target tracking 的目標 CPU 從 50% 降到 30%
- C. 改用 predictive scaling，預測 AZ 故障的發生時間並提前擴展
- D. 在每個 AZ 為所需數量的 `m7i.large` 建立 On-Demand Capacity Reservations，並讓 ASG 優先使用保留容量
- E. 把 health check grace period 從 300 秒縮短到 60 秒，加快替換速度

> [!answer]- 答案：A、D
> **A ✓** Static stability 要求「剩下的 AZ 已有足夠容量」。三個 AZ 各 6 台時，任一 AZ 故障仍有 12 台，平時只多準備 50%；若維持兩個 AZ，則每個 AZ 都要 12 台、平時多準備 100%，成本更高。
>
> **B ✗** 降低 CPU 目標會提高平時的容量，但沒有明確保證任一 AZ 故障後剩下的容量足夠，本質上仍依賴故障時擴展。
>
> **C ✗** Predictive scaling 從流量歷史學習週期，無法預測 AZ 故障。
>
> **D ✓** 在每個 AZ 預先保留所需 instance type 的容量，確保 ASG 需要時一定開得出機器（包括替換故障機器或在大規模事件中補容量），補強了「max 不保證容量」的弱點。保留容量可搭配 Savings Plans 降低費用。
>
> **E ✗** Grace period 影響的是新 instance 的健康判斷，縮短它不會加快啟動，還可能讓尚未準備好的 instance 被誤判為不健康。
>
> **考點**：SAP-2.4、SAP-3.4｜static stability 與 Capacity Reservations

### 練習 18-13｜SAP｜單選｜導入 predictive scaling

Wanderly 的 B2B 旅遊管理後台流量非常規律：每個工作日 08:30 開始快速上升，12:00 與 18:00 後下降，週末幾乎沒有流量，已有三個月的 CloudWatch 歷史。應用程式啟動需要約 7 分鐘，目前的 target tracking 每天早上都要等 10 分鐘以上才追上流量。團隊希望在不增加大量閒置成本的情況下改善早上的體驗，也擔心預測不準造成錯誤擴展。

最合適的導入方式是什麼？

- A. 直接以 forecast and scale 模式啟用 predictive scaling，並刪除 target tracking 以免兩者衝突
- B. 以 forecast only 模式啟用 predictive scaling，確認預測與實際負載吻合後再切換為 forecast and scale，並保留 target tracking 處理預測之外的變化
- C. 建立 scheduled action，在每天 00:00 把 min 設為尖峰容量並維持到 23:59
- D. 改用 step scaling，在 CPU 超過 30% 時一次增加 50% 容量

> [!answer]- 答案：B
> **A ✗** 直接讓未經驗證的預測調整正式容量，風險正是團隊擔心的；刪除 target tracking 後，預測之外的流量變化將無人處理。兩者同時存在時 ASG 會取較大容量，不會衝突。
>
> **B ✓** 規律的工作日週期與數月歷史正適合 predictive scaling，它會在預測的尖峰前提前啟動 instance，解決 7 分鐘的開機延遲。先用 forecast only 觀察預測品質是 AWS 建議的導入方式；保留 target tracking 作為預測之外的安全網。
>
> **C ✗** 全天維持尖峰容量（包括深夜與週末）會產生大量閒置成本，違反需求。
>
> **D ✗** Step scaling 仍是等 metric 上升後才反應，無法消除 7 分鐘的開機延遲；一次加 50% 也容易過度擴展。
>
> **考點**：SAP-3.3、SAP-2.5｜predictive scaling 的 forecast only 導入與 dynamic scaling 搭配

### 練習 18-14｜SAP｜單選｜長時間工作不被縮減中斷

Wanderly 的影片行程簡報產生服務由 ASG 的 worker 從 SQS 取工作，每個工作需要 15 到 40 分鐘，中途被中斷就必須從頭重做，而且沒有 checkpoint 機制。ASG 依 queue backlog 擴展與縮減。最近縮減時，經常有執行到一半的工作被中斷，造成重複運算與延遲。團隊希望保留縮減的彈性，並以最少的程式修改解決。

最合適的做法是什麼？

- A. 改用 `OldestInstance` termination policy，讓最早啟動、最可能已完成工作的 instance 先被縮減
- B. 為 termination lifecycle hook 設定 48 小時的 timeout，讓所有被縮減的 instance 等待工作完成
- C. 讓 worker 在取得一個工作時呼叫 API 為自己開啟 scale-in protection，完成後關閉保護並再取下一個工作
- D. 暫停 ASG 的 `Terminate` 程序，改由工程師每天手動清理閒置的 instance

> [!answer]- 答案：C
> **A ✗** 啟動時間的先後和 instance 是否正在執行工作沒有關係，最舊的 instance 可能剛好接了一個 40 分鐘的工作。
>
> **B ✗** Termination lifecycle hook 可以讓 instance 完成手上工作，但每次縮減都可能選中正在執行長工作的 instance，等待期間它仍佔用費用；而且 heartbeat timeout 單次最長只能設 2 小時，要等更久必須由程式持續送 heartbeat，再怎麼延長整體也只有 48 小時，會讓縮減長時間卡住。它比較適合收尾工作，而不是長達 40 分鐘的不確定任務。
>
> **C ✓** Scale-in protection 讓正在執行工作的 instance 不會被縮減選中，ASG 只會關掉閒置（未保護）的 instance。Worker 在取得與完成工作時切換保護即可，程式修改很少，縮減的彈性也得以保留。
>
> **D ✗** 暫停 `Terminate` 讓 ASG 完全無法縮減，改由人工清理違反「最少營運負擔」，也失去自動化的價值。
>
> **考點**：SAP-3.4、SAP-2.4｜instance scale-in protection 保護進行中的工作

### 練習 18-15｜SAA｜單選｜暫時移出單台 instance 除錯

Wanderly 的 web ASG 中有一台 instance 間歇性回應緩慢，工程師需要登入它收集約 30 分鐘的診斷資料。在這段期間，這台 instance 不能接收使用者流量，也不能被 ASG 因健康檢查而替換，同時其他 instance 要維持完整的服務容量。診斷結束後，這台 instance 要能回到服務中。

最合適的做法是什麼？

- A. 把這台 instance 從 ASG detach，診斷完成後再重新 attach
- B. 把這台 instance 放入 standby，且不降低 desired capacity，讓 ASG 補一台新 instance；診斷完成後執行 exit standby
- C. 暫停整個 ASG 的 `HealthCheck` 與 `Launch` 程序，直到診斷完成
- D. 為這台 instance 開啟 scale-in protection

> [!answer]- 答案：B
> **A ✗** Detach 也能移出 instance，但它的語意是「永久移出 ASG」，重新 attach 需要額外步驟；standby 正是為「暫時移出、之後回來」設計的。
>
> **B ✓** Standby 會把 instance 從 target group 取消註冊，ASG 也不會對它執行健康檢查替換。不降低 desired 時，ASG 會啟動一台新 instance 補足容量，其他使用者不受影響；診斷完成後 exit standby 讓它回到 InService。
>
> **C ✗** 暫停整個 ASG 的健康檢查與啟動，會讓其他 instance 故障時也不會被替換，風險擴散到整個機群；而且這台 instance 仍在 target group 中接收流量。
>
> **D ✗** Scale-in protection 只防止縮減時被選中，不會讓 instance 停止接收流量，也不阻止健康檢查替換。
>
> **考點**：SAA-2.2｜standby 狀態

### 練習 18-16｜SAP｜選兩項｜限時活動的快速擴展

Wanderly 的行銷團隊每週會在事先公告的時間推出 3 到 5 場限時特價，流量在 1 分鐘內升到平常的十倍。Web tier 的 ASG 使用 mixed instances policy（On-Demand base 加 Spot），新 instance 從啟動到通過 health check 需要 6 分鐘，其中 5 分鐘花在 user data 安裝套件與下載程式碼。團隊要求活動開始的第一分鐘就有足夠容量，並維持 Spot 帶來的成本節省。

哪兩個做法最合適？（選兩項）

- A. 為 ASG 加入 stopped 狀態的 warm pool，讓擴展時直接取用已初始化的 instance
- B. 將安裝好的套件與程式碼烤進 golden AMI，讓 user data 只負責拉取少量設定，縮短開機時間
- C. 改用 simple scaling，cooldown 設為 0 秒，讓 ASG 在流量上升時連續擴展
- D. 由行銷系統在活動公告時同步建立 scheduled action，在每場活動前 10 分鐘提高 min 與 desired，活動結束後調回
- E. 把 target tracking 的 metric 改為 ALB 的總請求數，讓它對流量變化更敏感

> [!answer]- 答案：B、D
> **A ✗** Warm pool 不支援 Spot instance；這個 ASG 混用 Spot，若要用 warm pool 就必須把機群改成全部 On-Demand，放棄 Spot 的成本節省，違反要求。
>
> **B ✓** 6 分鐘裡有 5 分鐘是安裝與下載，把它們烤進 golden AMI 可以讓開機時間縮短到一兩分鐘，所有後續擴展（包括超出預期的部分）都受益，而且不影響 mixed instances policy。
>
> **C ✗** Simple scaling 仍要等 metric 上升才反應，無法在第一分鐘就有容量；cooldown 為 0 還會被開機中的 metric 誤導而過度擴展。
>
> **D ✓** 活動時間事先公告，屬於已知時間的尖峰。在活動前用 scheduled action 提高 min 與 desired，可以讓容量在流量到來前就位；結束後調回避免閒置成本。
>
> **E ✗** 總請求數不會因加機器而下降，用它做 target tracking 會一路擴展到 max，而且仍然是等流量來了才反應。
>
> **考點**：SAP-2.5、SAP-3.3｜scheduled scaling、golden AMI 與 warm pool 限制
