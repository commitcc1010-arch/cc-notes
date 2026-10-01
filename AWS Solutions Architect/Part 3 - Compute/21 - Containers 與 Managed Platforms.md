---
chapter: 21
title: Containers 與受管平台：ECS、EKS、Fargate、Beanstalk 與 Batch
part: 3
---

# 第 21 章　Containers 與受管平台：ECS、EKS、Fargate、Beanstalk 與 Batch

> [!abstract] 本章地圖
> **你會學到**：
> - 用自己的話解釋 container、image、registry 是什麼，以及 container 和 VM、Lambda 的差別
> - 說清楚 ECS 的四個核心物件（cluster、task definition、task、service），並正確分配 task role 與 execution role
> - 在 EC2 與 Fargate 之間做選擇，理解 capacity providers 與「兩層擴展」
> - 判斷什麼時候該用 EKS，以及 managed node groups、Fargate profiles、Karpenter 各自解決什麼問題
> - 在 Elastic Beanstalk、ECS Express Mode、App Runner、Lightsail 等高抽象平台之間取捨，並選對 Beanstalk 部署策略
> - 用 AWS Batch 執行大量批次工作，用 ParallelCluster 與 EFA 執行 HPC
>
> **前置知識**：第 4 章（VM／container／serverless 差異）、第 17 章（EC2）、第 18 章（Auto Scaling）、第 19 章（Lambda）
> **考試比重**：SAA ★★★（Domain 2 解耦與高可用、Domain 3 運算效能、Domain 4 運算成本）｜SAP ★★★（Domain 2 部署策略、Domain 4 現代化）

## 21.1 故事：Lambda 裝不下的那些工作

第 20 章的 serverless API 讓 Wanderly 撐過了促銷尖峰，但工程團隊很快發現，不是所有工作都適合放進 Lambda。

第一個是**搜尋服務**。它要維持對 OpenSearch 與快取的長連線池、啟動時載入 2 GB 的同義詞字典，而且全天候都有穩定的每秒數千次請求。放在 Lambda 上，每個新的執行環境都要重新載入字典，冷啟動要好幾秒；穩定高流量下按請求計費也比長期執行的運算貴。

第二個是**夜間房價重算**。每天凌晨要對 200 萬組「旅館 × 日期」重新計算價格，每一組彼此獨立，單組可能要跑 20 分鐘，超過 Lambda 的 15 分鐘上限。

第三個問題比較好笑：搜尋服務在工程師小陳的筆電上跑得好好的，部署到 EC2 卻因為作業系統套件版本不同而崩潰。「在我的機器上明明可以跑」成了團隊的口頭禪。

與此同時，Wanderly 剛併購的一家旅遊行程新創，整個系統都跑在 Kubernetes 上；而公司另一個團隊維護的 PHP 會員後台，則希望「把程式碼丟上去就好，不想管 Load Balancer 和 Auto Scaling 怎麼設」。

這一章會依序解決這些問題：先用 **container** 終結「在我的機器上可以跑」，再用 **ECS** 與 **Fargate** 執行搜尋服務，接著看併購團隊適合的 **EKS**、會員後台適合的 **Elastic Beanstalk**，最後用 **AWS Batch** 跑夜間重算，並延伸到需要超低延遲網路的 HPC 工作。

## 21.2 Container 是什麼：把程式與它的環境一起打包

### 為什麼需要 container

一支程式要能執行，需要的不只是程式碼：還有特定版本的語言 runtime（例如 Python 3.12）、系統函式庫、設定檔、環境變數。在 VM 上部署時，這些東西是「另外裝上去的」，每台機器裝的版本可能略有不同，這就是「在我的機器上可以跑」的根源。

**Container（容器）** 的做法是把程式連同它需要的 runtime、函式庫與設定**打包成一個不可變的單位**，在任何支援 container 的主機上都以完全相同的方式執行。

### Container 怎麼運作

- **Image（映像檔）**：一個唯讀的打包檔，包含檔案系統內容與啟動指令。Image 由多個 **layer（層）** 疊成，每一層記錄一次變更；共用相同底層（例如同一個 Python 基礎 image）的 image 只需要儲存與下載一次那些層。
- **Container**：image 的一個執行中實例。同一個 image 可以同時跑出很多個 container。
- **Registry（儲存庫服務）**：存放與發布 image 的地方，例如 Docker Hub 或 AWS 的 ECR。Image 用 `名稱:tag` 識別（例如 `search-api:1.4.2`），每個 image 也有一個由內容計算出的 **digest**（`sha256:...`），內容一變 digest 就變。
- **Dockerfile**：描述如何建立 image 的文字檔。

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8080
CMD ["python", "-m", "src.server"]
```

這份 Dockerfile 從一個 Python 3.12 基礎 image 開始，安裝相依套件，複製程式碼，宣告服務監聽 8080 port，最後定義啟動指令。建好的 image 在小陳的筆電、測試環境與正式環境上都是同一份位元組。

### Container 與 VM、Lambda 的差別

Container 不是輕量版的 VM。**VM** 有自己完整的作業系統核心（kernel），由 hypervisor 隔離；**container** 則共用主機的 kernel，靠 Linux 的 namespaces（隔離它能看到的程序、網路、檔案系統）與 cgroups（限制它能用的 CPU 與記憶體）彼此隔離。因此 container 啟動只要幾秒甚至更短，一台主機可以跑很多個。

| 比較 | EC2（VM） | Container（ECS／EKS） | Lambda |
|---|---|---|---|
| 打包單位 | AMI | Container image | 程式碼 zip 或 container image |
| 執行時間 | 不限 | 不限 | 最長 15 分鐘 |
| 啟動速度 | 數十秒到分鐘 | 數秒到數十秒 | 毫秒到數秒（冷啟動） |
| 誰管作業系統 | 你 | 你（EC2 launch type）或 AWS（Fargate） | AWS |
| 計費 | 按 instance 時間 | 按 instance 或按 task 的 vCPU／記憶體時間 | 按請求數與執行時間 |
| 適合 | 需要完整 OS 控制、特殊授權軟體 | 長時間執行服務、微服務、可移植工作 | 事件驅動、短時間、流量不規則 |

> [!warning] 常見誤解
> 「Container 是安全邊界，跟 VM 一樣隔離。」因為 container 共用主機 kernel，一個 container 若取得過高權限（例如 privileged 模式），可能影響同主機的其他 container。多租戶或高敏感工作需要更強的隔離時，Fargate（每個 task 跑在獨立的隔離環境）或每個租戶獨立的 instance 是較安全的選擇。

## 21.3 Amazon ECR：存放 image 的地方

Container 打包好之後，需要一個所有執行環境都能取得的地方。**Amazon ECR（Elastic Container Registry）** 是 AWS 的受管 container registry，與 IAM、ECS、EKS、Lambda 原生整合。

### 核心概念

- **Repository**：存放同一個應用程式各版本 image 的地方，例如 `search-api`。ECR 有 private repository 與 public repository（ECR Public，給全世界下載的公開 image）。
- **權限**：IAM policy 控制誰能 push／pull；**repository policy**（resource-based policy）可以允許其他帳號或整個 Organization 拉取 image。
- **Tag immutability（標籤不可變）**：啟用後，同一個 tag（例如 `1.4.2`）不能被覆寫成另一個 image，避免「同樣叫 1.4.2，但內容被偷偷換掉」。正式環境強烈建議啟用，並在部署時使用明確版本或 digest，而不是 `latest`。
- **Lifecycle policy**：自動清理舊 image，例如「未加 tag 的 image 保留 7 天」「只保留最近 50 個版本」，控制儲存費用。
- **Image scanning**：**basic scanning** 在 push 時（或手動）掃描作業系統套件的已知弱點；**enhanced scanning** 整合 Amazon Inspector（第 16 章），持續掃描並涵蓋程式語言套件。
- **加密**：image 預設以 AES-256 加密靜態儲存，也可選擇 KMS key。
- **Replication**：設定 **cross-Region** 與 **cross-account** 複寫，新 push 的 image 自動複製到其他 Region 或帳號，讓各 Region 從本地拉取、加快部署並支援 DR。
- **Pull through cache**：把 Docker Hub、ECR Public 等上游 registry 的 image 快取到你的 private ECR，避免上游的速率限制與可用性問題，也讓 private subnet 只需要連到 ECR。

### 從 private subnet 拉 image

這是考試與實務都非常常見的問題：ECS task 跑在沒有 NAT Gateway 的 private subnet，啟動時失敗並出現 `CannotPullContainerError`。原因是拉 image 需要連到 ECR，而 ECR 的 API 是公開端點。要在不經 Internet 的情況下拉 image，需要建立以下 VPC endpoint（第 6 章）：

| Endpoint | 類型 | 用途 |
|---|---|---|
| `com.amazonaws.{region}.ecr.api` | Interface | ECR API 呼叫（例如取得授權 token） |
| `com.amazonaws.{region}.ecr.dkr` | Interface | Docker registry 協定（拉 image manifest） |
| `com.amazonaws.{region}.s3` | **Gateway** | Image 的 layer 實際存放在 S3 |
| `com.amazonaws.{region}.logs` | Interface | 若使用 `awslogs` 把 log 送到 CloudWatch Logs |

只建了兩個 ECR interface endpoint 卻忘了 S3 gateway endpoint，是最常見的錯誤：授權和 manifest 都拿得到，下載 layer 時卻逾時。若 task 還要從 Secrets Manager 取 secret，也要加上對應的 interface endpoint。

## 21.4 ECS：AWS 原生的 container 編排

有了 image，還需要有人決定「這個 container 要在哪台機器上跑、跑幾份、掛了要重啟、怎麼接到 Load Balancer」。這種工作稱為 **container orchestration（容器編排）**。**Amazon ECS（Elastic Container Service）** 是 AWS 自己的 orchestrator，設計目標是「用 AWS 的方式（IAM、VPC、ELB、CloudWatch）簡單地跑 container」。ECS 本身不收費，你只為底下的運算資源付費。

### 四個核心物件

| 物件 | 是什麼 | 類比 |
|---|---|---|
| **Cluster** | Task 與 service 的邏輯分組，也是運算容量的邊界 | 一間工廠 |
| **Task definition** | 描述一個 task 要跑哪些 container、用多少 CPU／記憶體、網路模式、IAM role、log 設定的 JSON 範本，有版本（`family:revision`） | 產品的設計圖 |
| **Task** | 依 task definition 執行起來的一組 container（一個 task 可以有多個 container，例如主程式加 log sidecar） | 一件產品 |
| **Service** | 讓指定數量（desired count）的 task 持續執行，task 失敗就替換，並負責與 Load Balancer 整合、滾動部署 | 生產線主管 |

不需要長期執行的工作，可以不建 service，直接用 `RunTask` 執行**獨立 task**，或用 EventBridge Scheduler 定時執行（例如每小時一次的資料清理）。

### Task definition 範例

以下是 Wanderly 搜尋服務在 Fargate 上的 task definition：

```json
{
  "family": "search-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "1024",
  "memory": "4096",
  "runtimePlatform": {
    "cpuArchitecture": "ARM64",
    "operatingSystemFamily": "LINUX"
  },
  "taskRoleArn": "arn:aws:iam::111122223333:role/search-api-task-role",
  "executionRoleArn": "arn:aws:iam::111122223333:role/search-api-execution-role",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "111122223333.dkr.ecr.ap-northeast-1.amazonaws.com/search-api:1.4.2",
      "essential": true,
      "portMappings": [{ "containerPort": 8080, "protocol": "tcp" }],
      "environment": [
        { "name": "DICTIONARY_BUCKET", "value": "wanderly-search-assets" }
      ],
      "secrets": [
        {
          "name": "CACHE_AUTH_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:ap-northeast-1:111122223333:secret:prod/search/cache-AbCdEf"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/search-api",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "app"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 90
      }
    }
  ]
}
```

幾個值得注意的欄位：`cpu: 1024` 代表 1 vCPU、`memory: 4096` 代表 4 GB；`runtimePlatform` 指定在 Graviton（ARM64）上執行，通常有更好的性價比（第 17 章），但 image 也必須以 ARM64 建置；`secrets` 讓 ECS 在啟動時從 Secrets Manager 取出值、注入成環境變數，secret 不會寫在 task definition 裡；`healthCheck` 的 `startPeriod: 90` 給搜尋服務 90 秒載入字典，這段時間內的健康檢查失敗不計入。

## 21.5 Task role 與 execution role：誰需要什麼權限

上面的 task definition 有兩個 role，這是 ECS 最重要、也最常考的觀念之一。

- **Task execution role（`executionRoleArn`）**：給 **ECS agent（以及 Fargate 的基礎設施）** 用的身份，負責「把 task 啟動起來」所需的動作：從 ECR 拉 image、把 log 寫到 CloudWatch Logs、從 Secrets Manager 或 Parameter Store 取出 task definition 中 `secrets` 引用的值。AWS 提供 `AmazonECSTaskExecutionRolePolicy` 這個 managed policy 涵蓋前兩項。
- **Task role（`taskRoleArn`）**：給 **container 裡的應用程式** 用的身份。搜尋服務的程式要從 S3 讀字典檔、寫 DynamoDB，這些權限放在 task role。SDK 會自動從 task 的 credential endpoint 取得這個 role 的臨時憑證。

```text
 ┌──────────────────────── ECS Task ────────────────────────┐
 │  啟動階段（ECS agent / Fargate）     執行階段（你的程式）   │
 │  使用 execution role：              使用 task role：        │
 │   ① 從 ECR 拉 image                  ④ s3:GetObject 字典檔  │
 │   ② 從 Secrets Manager 取 secret     ⑤ dynamodb:Query       │
 │   ③ 建立 log stream、寫 log                                  │
 └───────────────────────────────────────────────────────────┘
```

① 到 ③ 發生在你的程式碼開始執行之前或之外，由 ECS 代勞；④ ⑤ 是你的程式碼呼叫 AWS API。把它們分開，才能做到最小權限：搜尋服務的程式碼不需要也不應該擁有拉任何 image 的權限，ECS agent 也不需要讀 DynamoDB。

在 EC2 launch type 上還有第三個身份：**container instance role**（EC2 的 instance profile），讓 EC2 上的 ECS agent 能向 ECS 註冊、回報狀態。過去有人把應用程式權限也放在這裡，結果同一台 EC2 上的所有 task 都共用這些權限，違反最小權限。正確做法是每個 task definition 用自己的 task role。

> [!tip] 考試提示
> 「Task 啟動失敗、無法拉 image、無法取得 secret」→ 檢查 **execution role**（與網路路徑）。「應用程式呼叫 S3／DynamoDB 回 AccessDenied」→ 檢查 **task role**。兩者的用途互換是最常見的錯誤選項。

## 21.6 Launch types：EC2 還是 Fargate？

Task 總要在某台機器上執行。ECS 提供兩種主要的 **launch type**（以及 21.10 節給地端用的 External）：

### EC2 launch type

你建立 EC2 instance（通常透過 Auto Scaling group，使用 ECS-optimized AMI），它們註冊到 cluster 成為 **container instance**，ECS 把 task 放到這些 instance 上。你要負責 instance 的選型、patch、擴展與容量規劃，換來的是完整控制：

- 可以用 GPU instance、特殊 instance type、大量 instance store。
- 可以執行需要 privileged 權限或主機層存取的 container。
- 可以用 Reserved Instances、Savings Plans、Spot 降低成本，並把多個 task 緊密地放在同一台機器上，提高利用率。
- 支援 `DAEMON` 排程策略：每台 instance 各跑一個 task，適合 log 收集或監控 agent。

### Fargate launch type

**AWS Fargate** 是 container 的 serverless 運算引擎：你只在 task definition 宣告 CPU 與記憶體，AWS 負責準備底層運算，你看不到、也不用管任何 EC2 instance。特性：

- **每個 task 在獨立的隔離環境中執行**，不與其他 task 共用 kernel。
- **必須使用 `awsvpc` 網路模式**：每個 task 有自己的 ENI 與 private IP，可以直接套用 security group。
- 按 task 宣告的 vCPU 與記憶體**按秒計費**（有最低計費時間）；Compute Savings Plans 也涵蓋 Fargate。
- 支援 Linux（x86 與 ARM64）與 Windows container；單一 task 最大可到 16 vCPU、120 GB 記憶體；ephemeral storage 預設 20 GB，可設定到 200 GB。
- 限制：**不支援 GPU、不支援 privileged container、不支援 `DAEMON` 排程**、無法存取主機層設定。

### Fargate Spot

**Fargate Spot** 用 AWS 的閒置容量執行 task，價格比 Fargate 便宜很多，但 AWS 需要容量回收時會中斷 task：ECS 會先送出中斷通知，task 收到 `SIGTERM` 後有約 **2 分鐘**時間收尾，然後被停止。適合可中斷、可重試的工作，例如照片處理 worker、測試環境、批次工作；不適合唯一一份的有狀態服務。

### 網路模式

| 模式 | 說明 | 可用於 |
|---|---|---|
| `awsvpc` | 每個 task 一個 ENI 與 VPC IP，可套用 task 層級 security group | Fargate（必須）、EC2 |
| `bridge` | Container 在主機內的虛擬網路，透過 port mapping 對外；可用動態 host port，讓同一台主機跑多個相同 port 的 task | EC2（Linux） |
| `host` | Container 直接使用主機網路，port 不能重複 | EC2 |

`awsvpc` 是 AWS 建議的預設，因為 security group 可以精確到每個服務。在 EC2 上使用時要注意：每個 task 占用一個 ENI，而每種 instance type 能掛的 ENI 數有限；可以啟用 **ENI trunking** 提高每台 instance 可執行的 `awsvpc` task 數。另外，每個 task 都占用一個 subnet IP，subnet 要規劃得夠大（第 5 章）。

### 怎麼選

| 情境 | 選擇 |
|---|---|
| 不想管伺服器、流量會變動、團隊小 | Fargate |
| 需要 GPU、privileged、特殊 instance type | EC2 launch type |
| 穩定高利用率、要把成本壓到最低、已買 RI | EC2 launch type（搭配 Spot、Savings Plans） |
| 每台主機都要跑一份 agent（DAEMON） | EC2 launch type |
| 可中斷的 worker、批次、測試環境 | Fargate Spot（或 EC2 Spot） |
| 多租戶需要較強隔離 | Fargate |

## 21.7 Capacity providers 與兩層擴展

小陳把搜尋服務部署到 EC2 launch type 的 cluster 後，第一次促銷就遇到怪事：流量上升，ECS service 確實把 desired count 從 6 提高到 12，但新的 6 個 task 遲遲無法啟動，service 事件不斷出現「沒有足夠 CPU 的 container instance 可以放置 task」。

原因是 ECS 上的擴展其實有**兩層**：

1. **Service auto scaling（應用層）**：決定要跑幾個 task。ECS 透過 **Application Auto Scaling** 調整 service 的 desired count，支援 target tracking（例如平均 CPU 60%、或 ALB 的 `ALBRequestCountPerTarget`）、step scaling 與 scheduled scaling，概念與第 18 章的 EC2 Auto Scaling 相同。
2. **Cluster capacity（基礎設施層）**：決定有多少台 EC2 可以放 task。Task 變多了，EC2 不夠，task 就無處可放。

在 Fargate 上只有第一層，因為 AWS 負責容量。在 EC2 上，兩層都要處理，而把它們串起來的機制就是 **capacity provider**。

### Capacity provider 是什麼

**Capacity provider** 定義「task 要從哪裡取得運算容量」。有三種：

- `FARGATE` 與 `FARGATE_SPOT`：內建，直接使用。
- **Auto Scaling group capacity provider**：關聯一個 EC2 Auto Scaling group，並啟用 **managed scaling**。ECS 會計算一個 `CapacityProviderReservation` 指標（需要的容量 ÷ 現有容量），以 target tracking 自動調整 ASG 的 desired capacity：task 放不下時加機器，空閒時縮減。這就是 **ECS cluster auto scaling**。啟用 **managed termination protection** 後，ASG 縮減時不會終止還有 task 在跑的 instance。

```text
 流量上升
   │
   ▼
 ① Service auto scaling：CPU 超過目標 → desired count 6 → 12
   │
   ▼
 ② ECS 嘗試放置 6 個新 task → 現有 EC2 容量不足 → task 等待容量（PROVISIONING）
   │
   ▼
 ③ Capacity provider 的 CapacityProviderReservation 指標 > 目標（例如 100%）
   │
   ▼
 ④ Managed scaling 提高 ASG desired capacity → 新 EC2 啟動並註冊到 cluster
   │
   ▼
 ⑤ ECS 把等待中的 task 放到新 instance → 註冊到 ALB target group → 開始接流量
```

① 應用層判斷需要更多 task。② 基礎設施跟不上時，task 會等待而不是直接失敗。③ ④ capacity provider 偵測到容量缺口，自動擴充 ASG。⑤ 新容量就緒後 task 自動放上去。若沒有設定 capacity provider，流程會卡在第 ② 步，只調 desired count 或只加 EC2 都不能完整解決。

### Capacity provider strategy

一個 service 可以同時使用多個 capacity provider，以 **base**（至少有幾個 task 放在這個 provider）與 **weight**（其餘 task 的分配比例）控制。Wanderly 的照片處理 worker 用以下設定：至少 2 個 task 跑在一般 Fargate 上保證基本處理能力，其餘以 1:3 的比例分給 Fargate 與 Fargate Spot。

```bash
aws ecs create-service \
  --cluster wanderly-prod \
  --service-name photo-worker \
  --task-definition photo-worker:7 \
  --desired-count 10 \
  --capacity-provider-strategy \
      capacityProvider=FARGATE,base=2,weight=1 \
      capacityProvider=FARGATE_SPOT,weight=3 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0a1b2c3d,subnet-0e5f6a7b],securityGroups=[sg-0123456789abcdef0],assignPublicIp=DISABLED}"
```

10 個 task 中，先有 2 個放在 Fargate（base），剩下 8 個依 1:3 分配，約 2 個在 Fargate、6 個在 Fargate Spot。Spot 容量被回收時，service 會自動補 task；即使 Spot 一時無法取得，Fargate 上的 task 仍維持最低處理能力。`subnets` 列出兩個 AZ 的 private subnet，ECS 會把 task 分散到多個 AZ。

## 21.8 ALB 整合、部署與服務探索

### 與 ALB 整合

對外的 ECS service 通常放在 ALB（第 10 章）後面。Service 設定好 target group 後，ECS 會自動把新 task 註冊、把停止的 task 解除註冊。

- **`awsvpc` 模式（含 Fargate）**：target group 的 target type 必須是 **`ip`**，因為每個 task 有自己的 IP。
- **`bridge` 模式的動態 port mapping**：host port 設為 0，ECS 為每個 task 分配一個隨機的主機 port，target type 用 `instance`，ALB 依「instance + port」把流量送到正確的 task。這讓同一台 EC2 能跑多個監聽相同 container port 的 task。
- 一個 ALB 可以用 **path-based routing**（`/search/*`、`/reviews/*`）或 host-based routing 把流量分給多個 service 的 target group，多個微服務共用一個 ALB 可以省下成本。
- **Health check grace period**：給新 task 啟動時間，在這段時間內 ALB 健康檢查失敗不會讓 ECS 把它判定為不健康而替換。搜尋服務要載入字典 90 秒，grace period 就要設得比這更長。
- Task 的 security group 應只允許來自 ALB security group 的流量。

### 部署

ECS service 預設使用 **rolling update**：

- **`minimumHealthyPercent`**：部署過程中至少要維持幾 % 的 desired count 在健康狀態。設 100% 表示先啟動新 task、確認健康後才停舊的。
- **`maximumPercent`**：部署過程中最多可以同時跑幾 % 的 task。設 200% 允許新舊各一整份同時存在，部署較快，但需要有足夠的容量。
- **Deployment circuit breaker**：若新版 task 一直無法進入健康狀態，ECS 判定部署失敗，啟用 rollback 時會自動退回上一個可用的版本，避免卡在一個永遠起不來的部署。

ECS 也支援 **blue/green 部署**：先建立整組新版（green）task，與舊版（blue）同時存在，透過 Load Balancer 的 listener rule 切換流量，切換後還會保留舊版一段 **bake time**，出問題可以快速切回。過去這要搭配 CodeDeploy；現在 ECS 已**內建** blue/green，並提供 **linear**（每隔一段時間切換固定百分比）與 **canary**（先切一小部分、觀察後再全部切換）兩種漸進式流量切換，可以在各個 lifecycle stage 掛 Lambda hook 做自動驗證。CodeDeploy 方式仍可使用。各種部署策略的細節與取捨在第 37 章。

### 服務探索

微服務之間要互相呼叫時，需要知道對方的位址，而 task 的 IP 會一直變動。ECS 提供：

- **Service discovery**：整合 **AWS Cloud Map**，以 Route 53 的私有 DNS 名稱（例如 `reviews.wanderly.local`）解析到健康 task 的 IP。
- **Service Connect**：ECS 在每個 task 旁注入一個代理，讓服務以簡短名稱互相呼叫，並自動提供重試、逾時與連線層級的指標，不需要每個服務自己寫這些邏輯。

除錯時，**ECS Exec** 讓你在不開 SSH、不放 bastion 的情況下，透過 Systems Manager 進入執行中的 container 執行指令（第 38 章）。Container Insights 則收集 cluster、service、task 層級的 CPU、記憶體與網路指標（第 36 章）。

## 21.9 EKS：當你需要 Kubernetes

### 什麼時候選 EKS

**Kubernetes** 是開源的 container orchestrator，已經成為跨雲的業界標準，擁有龐大的生態系：Helm chart（套件化的部署範本）、operator（把資料庫等複雜軟體的維運邏輯寫成程式的擴充元件）、service mesh、各種監控與安全工具。**Amazon EKS（Elastic Kubernetes Service）** 是 AWS 的受管 Kubernetes 服務。

選 EKS 而不是 ECS 的理由通常是：

- 團隊或併購來的系統**已經在用 Kubernetes**，想以最少修改搬上 AWS。
- 需要 Kubernetes 生態系的特定工具（某個供應商軟體只提供 Helm chart 或 operator）。
- **可移植性**：同一套 manifest 要在多個雲或地端執行。

如果沒有這些需求，ECS 通常營運負擔較低：沒有 Kubernetes 版本升級、沒有要學的 Kubernetes 物件模型、與 AWS 服務的整合更直接。考試看到「LEAST operational overhead」且沒有提到 Kubernetes，通常選 ECS。

### EKS 的架構

- **Control plane**：Kubernetes 的 API server、etcd（狀態資料庫）與排程器。EKS 由 AWS 管理，跨多個 AZ 執行，自動處理備援與修補。每個 cluster 按小時收控制平面費用。API server 的 endpoint 可以設為 public、private 或兩者皆有。
- **Data plane（實際跑 Pod 的運算）**：你可以選擇以下方式之一或混用。
- **Pod**：Kubernetes 的最小執行單位，一個 Pod 包含一或多個 container，對應 ECS 的 task。

### Data plane 的選項

| 選項 | 誰管節點 | 特性 |
|---|---|---|
| **Managed node groups** | AWS 管理節點的建立、更新與終止（底層是 EC2 Auto Scaling group），你選 instance type | 最常見的起點；支援 On-Demand 與 Spot；節點升級時會先排空（drain）Pod |
| **Self-managed nodes** | 你自己建立 ASG、選 AMI、處理升級 | 最大彈性，最高營運負擔；需要特殊 AMI 或設定時使用 |
| **Fargate profiles** | AWS，你看不到節點 | 依 namespace 與 label 選擇器決定哪些 Pod 跑在 Fargate；每個 Pod 獨立隔離；不支援 DaemonSet、privileged Pod 與 GPU |
| **EKS Auto Mode** | AWS 管理節點的佈建、擴展、修補與核心附加元件 | 較新的選項，進一步減少 data plane 的維運工作 |

### 節點擴展：Cluster Autoscaler 與 Karpenter

Kubernetes 自己的 **Horizontal Pod Autoscaler（HPA）** 負責調整 Pod 數量（應用層）；節點不夠時，同樣需要第二層的節點擴展，概念與 21.7 節相同。

- **Cluster Autoscaler**：傳統做法，看到有 Pod 因資源不足無法排程時，調高對應 node group（ASG）的大小。每個 node group 通常只包含一種或幾種相近的 instance type，要支援多種規格就要建很多 node group。
- **Karpenter**：AWS 主導的開源節點佈建工具。它不經過 node group，而是直接看等待排程的 Pod 需要多少 CPU、記憶體、架構與可用區，**直接以 EC2 API 啟動最合適的 instance**，可以在數十種 instance type 與 Spot／On-Demand 之間自動挑選。它也會做 **consolidation**：把零散的 Pod 合併到較少或較便宜的節點，關掉多餘的節點來省錢。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: "1000"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

這個 NodePool 允許 Karpenter 使用 Spot 與 On-Demand、x86 與 ARM64 的節點，整個 pool 最多 1,000 vCPU，節點空閒或利用率低一分鐘後就嘗試整併。`EC2NodeClass` 另外定義 AMI、subnet 與 security group（此處省略）。

### EKS 的網路與身份

- **Amazon VPC CNI**：EKS 預設的網路外掛，讓**每個 Pod 拿到一個 VPC 的真實 IP**。好處是 Pod 可以直接被 VPC 內其他資源存取、可以套用 security group；代價是大量 Pod 會快速耗盡 subnet 的 IP。解法包括：啟用 **prefix delegation**（每個 ENI 分配整段 /28 前綴，提高每個節點的 Pod 密度）、使用 **custom networking** 讓 Pod 使用另一段 secondary CIDR（例如 `100.64.0.0/16`）的 subnet，與節點的 subnet 分開（第 5 章），或採用 IPv6。
- **Pod 的 IAM 權限**：不要把應用程式權限放在節點的 instance role 上（同一節點所有 Pod 都會拿到）。正確做法是 **IRSA（IAM Roles for Service Accounts）**：透過 cluster 的 OIDC provider，讓某個 Kubernetes service account 可以 assume 指定的 IAM role；或較新、設定較簡單的 **EKS Pod Identity**：在 EKS API 中直接建立「service account ↔ IAM role」的關聯。兩者都讓每個應用程式只拿到自己需要的權限，概念與 ECS 的 task role 相同。
- **AWS Load Balancer Controller**：在 cluster 中執行的控制器，看到 Kubernetes 的 Ingress 物件就建立 ALB，看到 `type: LoadBalancer` 的 Service 就建立 NLB。
- **存取控制**：誰可以操作 cluster 的 Kubernetes API，透過 EKS **access entries**（較新做法）或 `aws-auth` ConfigMap 把 IAM principal 對應到 Kubernetes 權限。

### 版本升級

Kubernetes 每年推出數個版本，每個 EKS 版本只有固定的標準支援期，之後進入要額外付費的 extended support。升級要依序進行：先升級 control plane，再升級 node groups 與附加元件（VPC CNI、CoreDNS、kube-proxy）。Managed node groups 與 Karpenter 都能協助以排空 Pod 的方式逐步替換節點；搭配 **Pod Disruption Budget**（限制同時被中斷的 Pod 數量）可以避免升級時服務中斷。這是選 EKS 必須接受的持續營運工作。

## 21.10 在自己的機房跑 container：ECS Anywhere 與 EKS Anywhere

Wanderly 收購的旅行社有一間地端機房，因為合約規定部分個資處理必須留在台灣的自有機房內，短期無法搬上雲。團隊希望地端的 container 也用與 AWS 相同的工具管理。

- **ECS Anywhere**：把地端的伺服器或 VM 安裝 SSM agent 與 ECS agent，註冊到 AWS 上的 ECS cluster，成為 **external instance**，使用 `EXTERNAL` launch type。**Control plane 仍在 AWS**，你用同樣的 ECS API、task definition 與 console 管理地端與雲端的工作。地端主機需要能連到 AWS 的網路。功能比在 AWS 內少：external instance 上的 service 不支援 ELB 負載平衡與 service discovery、不支援 `awsvpc` 網路模式（只能用 `bridge`、`host` 或 `none`）、不支援 capacity provider 與 EFS volume。因此它最適合主動連出或處理資料的工作，不適合需要接收大量入站流量的 web 服務。
- **EKS Anywhere**：在你自己的基礎設施（例如 VMware vSphere 或 bare metal）上**建立並執行完整的 Kubernetes cluster**，control plane 也在地端，使用與 EKS 相同的 Kubernetes 發行版（EKS Distro）。Cluster 由你營運，AWS 提供工具與可選的付費支援訂閱。適合需要在完全不依賴雲端連線的環境中執行 Kubernetes 的情境。
- **EKS Hybrid Nodes**：control plane 留在 AWS 的 EKS，把地端的機器加入成為節點。需要地端與 VPC 之間有穩定的私有連線（VPN 或 Direct Connect，第 8 章）。

| 需求 | 選擇 |
|---|---|
| 想用 ECS 的方式管理地端 container，control plane 交給 AWS | ECS Anywhere |
| 地端要有獨立的 Kubernetes cluster，可在無雲端連線時運作 | EKS Anywhere |
| EKS control plane 在 AWS，部分節點在地端 | EKS Hybrid Nodes |
| 要在地端使用 AWS 的硬體與完整服務 | AWS Outposts（第 2 章） |

## 21.11 更高抽象的平台：Beanstalk、ECS Express Mode、App Runner 與 Lightsail

ECS 和 EKS 給你很多控制，也要你做很多決定。有些團隊只想「把程式交出去，平台負責其他一切」。

### Elastic Beanstalk

**AWS Elastic Beanstalk** 是一個應用程式部署與管理平台。你上傳程式碼（Java、.NET、Node.js、Python、PHP、Ruby、Go，或 Docker image），選擇平台，Beanstalk 會**替你建立並管理**底層資源：EC2 instance、Auto Scaling group、Load Balancer、security group、CloudWatch alarm。這些資源在你的帳號裡看得到，必要時也能調整。Beanstalk 本身不收費，只收底層資源的費用。

核心概念：

- **Application**：一個應用程式的容器，底下有多個版本與環境。
- **Application version**：一份已上傳的程式碼套件（存在 S3）。
- **Environment**：一組執行某個版本的 AWS 資源，例如 `members-prod`、`members-staging`。
- **Environment tier**：
  - **Web server tier**：前面有 Load Balancer，處理 HTTP 請求。
  - **Worker tier**：從 **SQS queue** 取訊息處理背景工作。每台 instance 上的 daemon 會從 queue 讀取訊息，以 HTTP POST 送給你的應用程式，處理成功就刪除訊息；也可以用 `cron.yaml` 定義定期工作。
- **設定**：透過 console、`.ebextensions` 設定檔或 saved configuration 管理，例如 instance type、環境變數、Auto Scaling 範圍。
- **Managed platform updates**：可以讓 Beanstalk 在維護時段自動套用平台（作業系統與 runtime）的小版本更新。

> [!warning] 常見誤解
> 在 Beanstalk 環境「內」建立 RDS 很方便，但資料庫的生命週期會與環境綁在一起：刪除環境或用 blue/green 重建環境時，資料庫可能被一起刪除。正式環境應該**在 Beanstalk 外部建立 RDS**，再把連線資訊以環境變數或 Secrets Manager 提供給應用程式。

### Beanstalk 的部署策略

部署新版本時，Beanstalk 提供多種 **deployment policy**，考試很常考：

| 策略 | 做法 | 部署期間容量 | 停機 | 失敗時回復 | 額外成本 |
|---|---|---|---|---|---|
| **All at once** | 所有 instance 同時換新版 | 部署中無法服務 | 有短暫停機 | 要再部署一次舊版 | 無 |
| **Rolling** | 一批一批換，每批先移出服務 | 減少一批的容量 | 無 | 再滾動部署舊版 | 無 |
| **Rolling with additional batch** | 先多開一批新 instance，再一批批換 | 維持完整容量 | 無 | 再滾動部署舊版 | 少量（多一批） |
| **Immutable** | 在臨時的新 ASG 建立全新 instance，健康後才移入原環境並終止舊 instance | 維持完整容量 | 無 | 只要終止新 instance，舊的完全沒被動過 | 最高（暫時雙倍） |
| **Traffic splitting** | 建立新 instance，依設定比例把部分流量導給新版一段評估時間 | 維持完整容量 | 無 | 把流量移回舊 instance | 暫時雙倍 |

另外還有 **blue/green**：它不是 deployment policy，而是建立一個全新的環境部署新版，測試完成後執行 **swap environment URLs**（交換兩個環境的 CNAME），流量就切到新環境；要回退時再交換一次。因為牽涉 DNS，切換受 DNS 快取影響。

選擇方式：開發環境求快選 all at once；正式環境不能降容量選 rolling with additional batch；要最安全、回復最快選 immutable 或 blue/green；要用真實流量驗證新版選 traffic splitting。

### ECS Express Mode 與 App Runner

**AWS App Runner** 曾是 AWS 給「只想丟一個 container image 或原始碼就得到 HTTPS 網址」的團隊的服務。**AWS 已將 App Runner 對新客戶關閉**：既有客戶可以照常使用，包括建立新服務，AWS 仍維護安全性與可用性，但不再推出新功能，並建議遷移到 ECS Express Mode。考試或舊文件中仍可能看到它：重點是它從 source 或 image 自動建置、部署，提供受管的 HTTPS endpoint 與依同時請求數自動擴展，並以 VPC connector 讓服務的**出站**流量進入 VPC 存取私有資源（VPC connector 不是入站入口）。

新專案若要類似的體驗，可以評估 **Amazon ECS Express Mode**：只要提供 container image 與兩個 IAM role（task execution role，以及讓 ECS 代為建立基礎設施的 infrastructure role），一次 API 呼叫，ECS 就會在你的帳號中建立 Fargate 上的 ECS service、Application Load Balancer（含 target group 與健康檢查）、自動擴展政策、security group 與網路設定，並提供一個預設的 HTTPS 網址。Express Mode 本身不另外收費，只付底層資源的費用。這些資源仍是一般的 ECS 與 ELB 資源，需求變複雜時可以直接調整，不必遷移到另一個平台。

### Lightsail

**Amazon Lightsail** 以固定月費的「方案」提供簡化的 VM、受管資料庫、container、Load Balancer 與 CDN，介面單純，適合個人網站、小型 WordPress、原型或學習用途。它不適合需要完整 VPC 設計、細緻 Auto Scaling 或企業治理的系統；需要時可以從 Lightsail 匯出 snapshot 到 EC2。

### 高抽象平台怎麼選

| 平台 | 你提供 | 平台管理 | 適合 |
|---|---|---|---|
| Elastic Beanstalk | 程式碼或 Docker image | EC2、ASG、ELB、部署策略、平台更新 | 傳統 web 應用、想保留看得到的 EC2 資源、需要 worker tier |
| ECS Express Mode | Container image | Fargate service、LB、HTTPS、擴展 | 新的 container web 應用，想要最少設定且日後可完整控制 |
| App Runner（既有客戶） | 原始碼或 image | 建置、部署、HTTPS、擴展 | 既有的 App Runner 服務 |
| Lightsail | 選方案 | 簡化的 VM 與周邊 | 小型網站、原型、可預測的小流量 |

## 21.12 AWS Batch：大量批次工作

回到夜間房價重算：200 萬組獨立的計算，每組 5 到 20 分鐘，必須在早上 6 點前完成，而且希望越便宜越好。自己寫排程器分配工作、管理 Spot instance、處理失敗重試，工作量很大。

**AWS Batch** 是受管的批次運算服務：你只要定義工作與資源需求，Batch 負責排隊、選擇與啟動運算資源、執行、重試，閒置時把資源縮到零。Batch 本身不收費，只收底層 EC2、Fargate 等資源的費用。

### 核心物件

```text
 ① 提交 job（或 array job）
      │
      ▼
 ② Job queue（priority 高者優先；可連到多個 compute environment，依序嘗試）
      │
      ▼
 ③ Batch scheduler 依 job definition 的 vCPU／記憶體／GPU 需求，挑選可用的 compute environment
      │
      ├──► Compute environment A：EC2 Spot（allocation: SPOT_PRICE_CAPACITY_OPTIMIZED）
      └──► Compute environment B：EC2 On-Demand（A 容量不足時使用）
      │
      ▼
 ④ 以 container 執行 job → 成功：SUCCEEDED；失敗：依 retry strategy 重試
      │
      ▼
 ⑤ 佇列清空 → compute environment 縮到 minvCpus（可為 0）
```

- **Job definition**：工作的範本，指定 container image、vCPU、記憶體、GPU、指令、IAM role、timeout 與 **retry strategy**（最多重試次數，以及依結束原因決定是否重試，例如 Spot 被回收就重試、程式錯誤就不重試）。
- **Job queue**：工作排隊的地方，有 **priority**；一個 queue 可以依序對應多個 compute environment。例如高優先 queue 給白天的緊急重算，低優先 queue 給夜間大批工作；也可以設定 fair share scheduling policy，讓多個團隊公平分享容量。
- **Compute environment**：實際執行工作的運算資源。**Managed** 類型由 Batch 依需求啟動與終止 EC2（On-Demand 或 Spot）、Fargate、Fargate Spot，或在 EKS cluster 上執行；你設定 instance type 範圍與 `minvCpus`／`maxvCpus`。Spot 的 allocation strategy 建議用 `SPOT_CAPACITY_OPTIMIZED` 或 `SPOT_PRICE_CAPACITY_OPTIMIZED`，並允許多種 instance type 以降低中斷機率。
- **Array job**：一次提交一個 parent job，展開成最多 10,000 個 child job，每個 child 透過環境變數 `AWS_BATCH_JOB_ARRAY_INDEX` 知道自己處理第幾份資料。200 萬組計算可以切成 200 個 array job、每個 10,000 份。
- **Job dependencies**：一個 job 可以等其他 job 完成才開始，例如「所有重算完成後，再跑彙總 job」。更複雜的流程可以用 Step Functions 編排 Batch job（第 33 章）。
- **Multi-node parallel job**：一個 job 跨多台 instance 同時執行，用於需要節點間通訊的緊耦合工作。

### 常見問題：job 卡在 RUNNABLE

Job 顯示 `RUNNABLE` 卻遲遲不開始，表示它在等運算資源，常見原因：

- Compute environment 的 `maxvCpus` 太小，或已被其他 job 用滿。
- Job 要求的 vCPU 或記憶體大於 compute environment 允許的任何 instance type。
- Instance 啟動後無法向 ECS 註冊：在 private subnet 卻沒有 NAT Gateway 或必要的 VPC endpoint，或 instance role 權限不足。
- Spot 容量不足，且 instance type 選擇太少。

### Batch、Lambda、Step Functions、EMR 怎麼分

| 工作型態 | 選擇 |
|---|---|
| 每個工作 15 分鐘內、事件觸發 | Lambda |
| 大量獨立的長時間容器化工作、需要 Spot 與排隊 | AWS Batch |
| 多步驟流程、需要重試與分支 | Step Functions（可呼叫 Batch、ECS、Lambda） |
| Spark／Hadoop 大數據處理 | EMR（第 30 章） |
| 緊耦合的科學運算（MPI） | ParallelCluster／AWS PCS + EFA（下一節） |

## 21.13 HPC：緊耦合運算、EFA 與 ParallelCluster

房價重算是「易平行（embarrassingly parallel）」的工作：每份計算彼此獨立，散在哪些機器上都沒關係。但有一類工作完全不同：例如流體力學模擬、氣象預測、大型模型的分散式訓練，一個問題被切成很多塊分給上百個節點，**每一步計算都要和其他節點交換資料**。這類**緊耦合（tightly coupled）** 工作的瓶頸往往不是 CPU，而是節點之間的網路延遲。

### EFA：繞過作業系統的網路

**Elastic Fabric Adapter（EFA）** 是可以掛在支援的 EC2 instance 上的網路介面。它除了一般 ENA（第 17 章）的 IP 網路功能外，還提供 **OS-bypass**：HPC 應用透過 libfabric 介面，讓 MPI（Message Passing Interface，HPC 常用的節點間通訊標準）或 NCCL（GPU 之間的集體通訊函式庫）的流量繞過作業系統核心，直接與網路硬體溝通，大幅降低延遲與 CPU 負擔。

使用 EFA 的要點：

- 只有特定 instance type 支援 EFA（通常是運算、HPC、GPU 類型的較大規格）。
- OS-bypass 流量不能跨 subnet 路由，節點要在**同一個 subnet（同一個 AZ）**。
- 通常搭配 **cluster placement group**（第 17 章），把節點放在同一 AZ 內物理位置相近的地方，取得最低延遲與最高頻寬。
- EFA 的 security group 要允許同一個 security group 內所有的出入站流量。

### ParallelCluster 與 AWS PCS

- **AWS ParallelCluster** 是 AWS 提供的開源叢集管理工具。你寫一份 YAML 設定檔（head node、compute queues、instance type、是否啟用 EFA、共享儲存），它透過 CloudFormation 建出一整套 HPC 叢集，並使用 **Slurm** 這個 HPC 界常用的排程器，計算節點依佇列中的工作自動擴縮。
- **AWS Parallel Computing Service（AWS PCS）** 是較新的受管服務，由 AWS 管理 Slurm 控制器，減少自己維護排程器的工作。

HPC 的共享儲存通常使用 **FSx for Lustre**（第 24 章）：一個高吞吐的平行檔案系統，可以連結 S3 bucket，從 S3 載入輸入資料、把結果寫回 S3。

```text
   研究人員 ──► Head node（Slurm）
                    │ 依佇列啟動節點
                    ▼
   ┌──────── Cluster placement group（單一 AZ、同一 subnet）────────┐
   │  [節點 1 + EFA] ◄─► [節點 2 + EFA] ◄─► ... ◄─► [節點 N + EFA]   │
   │        MPI 流量 OS-bypass，低延遲互相交換資料                    │
   └───────────────────────────┬──────────────────────────────────┘
                               ▼
                     FSx for Lustre ◄──► S3（輸入資料與結果）
```

這張圖的關鍵是「全部集中」：HPC 為了延遲，刻意把節點放在同一個 AZ，犧牲了多 AZ 的高可用。這與 web 服務「分散到多 AZ」的原則相反，是因為 HPC 工作通常可以從 checkpoint 重跑，延遲比可用性重要。

## 21.14 比較與選型

### 運算平台決策流程

```text
工作會在 15 分鐘內完成、事件驅動、流量不規則？
├─ 是 → Lambda（第 19 章）
└─ 否 → 是大量獨立的批次工作？
         ├─ 是 → 需要節點間低延遲通訊（MPI）？
         │        ├─ 是 → ParallelCluster／AWS PCS + EFA + cluster placement group
         │        └─ 否 → AWS Batch（搭配 Spot）
         └─ 否 → 是長時間執行的服務，已經或可以 container 化？
                  ├─ 是 → 需要 Kubernetes（既有 K8s、Helm、operator、可移植）？
                  │        ├─ 是 → EKS（managed node groups／Karpenter／Auto Mode／Fargate）
                  │        └─ 否 → 想要最少設定的 web 服務？
                  │                 ├─ 是 → ECS Express Mode（或 Beanstalk Docker 平台）
                  │                 └─ 否 → ECS（Fargate 為預設；GPU／privileged／極致成本用 EC2）
                  └─ 否 → 傳統 web 應用，不想管基礎設施 → Elastic Beanstalk
                           需要完整 OS 控制或特殊軟體 → EC2 + Auto Scaling（第 17、18 章）
                           小型網站、固定月費 → Lightsail
```

### ECS 與 EKS 對照

| 項目 | ECS | EKS |
|---|---|---|
| Orchestrator | AWS 專有 | Kubernetes（開源標準） |
| Control plane 費用 | 免費 | 每個 cluster 按小時收費 |
| 學習與營運負擔 | 較低 | 較高（版本升級、附加元件、Kubernetes 物件） |
| 應用程式身份 | Task role | IRSA 或 EKS Pod Identity |
| Serverless 運算 | Fargate | Fargate profiles、EKS Auto Mode |
| 節點擴展 | Capacity provider + managed scaling | Cluster Autoscaler 或 Karpenter |
| 地端 | ECS Anywhere | EKS Anywhere、EKS Hybrid Nodes |
| 選擇時機 | AWS-native、要最少營運負擔 | 已有 Kubernetes、需要生態系、可移植性 |

### Fargate 與 EC2 對照

| 項目 | Fargate | EC2（ECS／EKS 節點） |
|---|---|---|
| 管理伺服器 | 不需要 | 需要（AMI、patch、擴展） |
| 隔離 | 每個 task／Pod 獨立環境 | 同節點共用 kernel |
| GPU、privileged、DaemonSet | 不支援 | 支援 |
| 計費 | 按 task 的 vCPU／記憶體秒數 | 按 instance；可提高裝箱密度 |
| 折扣 | Fargate Spot、Compute Savings Plans | Spot、RI、Savings Plans |
| 適合 | 預設選擇、變動流量、小團隊 | 穩定高利用率、特殊硬體需求 |

## 21.15 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 跑 container、不想管伺服器、LEAST operational overhead、沒提 Kubernetes | ECS on Fargate |
| 已有 Kubernetes、Helm、operator、跨雲可移植 | EKS |
| Container 中的應用程式呼叫 AWS 服務的權限 | ECS task role／EKS IRSA 或 Pod Identity |
| 無法拉 image、無法取得 secret、無法寫 log | Execution role（與網路路徑） |
| Private subnet 無 NAT、`CannotPullContainerError` | ECR `ecr.api`、`ecr.dkr` interface endpoint + S3 gateway endpoint |
| Service 已擴展但 task 放不下、等待容量 | ASG capacity provider + managed scaling（cluster auto scaling） |
| 可中斷的 worker、降低 container 成本 | Fargate Spot（capacity provider strategy 搭配 base） |
| GPU、privileged container、每台主機一個 agent | EC2 launch type（不是 Fargate） |
| ALB 後面的 Fargate task | Target type `ip`；path-based routing 共用一個 ALB |
| EKS Pod 用盡 subnet IP | VPC CNI prefix delegation、custom networking（secondary CIDR） |
| EKS 節點擴展慢、node group 太多、想自動選 Spot 與多種規格 | Karpenter（consolidation） |
| 地端 container 由 AWS 控制平面管理 | ECS Anywhere |
| 上傳程式碼就部署 web 應用、自動建 ELB 與 ASG | Elastic Beanstalk |
| Beanstalk 部署時維持完整容量、回復最快 | Immutable（或 blue/green swap URL） |
| Beanstalk 背景工作從 queue 處理 | Worker tier（SQS daemon） |
| 大量獨立批次、Spot、自動排隊與重試 | AWS Batch（array job、managed compute environment） |
| 緊耦合 HPC、MPI、節點間低延遲 | EFA + cluster placement group + ParallelCluster |
| Image 不可被覆寫、清理舊 image | ECR tag immutability、lifecycle policy |

**常見陷阱**：

1. 把應用程式權限放在 execution role 或節點的 instance role：應用程式應使用 task role（ECS）或 IRSA／Pod Identity（EKS）。
2. 以為 Fargate 支援 GPU、privileged container 或 DaemonSet：需要這些時要用 EC2。
3. 只調高 ECS service 的 desired count，卻沒有讓 EC2 容量跟著擴展：兩層擴展都要設定。
4. 以為 Fargate 是一個獨立的 orchestrator：它是 ECS 與 EKS 的運算選項，不負責排程與服務管理。
5. 只建 ECR 的兩個 interface endpoint 卻漏了 S3 gateway endpoint：image layer 存在 S3。
6. 沒有任何 Kubernetes 需求卻選 EKS：營運負擔較高，題目要求最少營運時通常選 ECS。
7. 把 HPC 節點分散到多個 AZ 以求高可用：緊耦合工作需要同一 AZ 的 cluster placement group 才能取得低延遲。
8. 把 App Runner 當成新專案的推薦方案：它已不接受新客戶。

## 21.16 SAP 加深：多帳號 container 平台、映像治理與現代化

### 多帳號、多 Region 的 image 供應鏈

企業的 container 平台常見的架構是：一個 **shared services 帳號**擁有 ECR repository 與 CI/CD 管線，所有 workload 帳號從這裡拉 image。

- **跨帳號拉取**：在 repository policy 中以 `aws:PrincipalOrgID` 條件允許整個 Organization 的 principal 拉取，不必逐一列出帳號（第 14 章）；各 workload 帳號的 execution role 仍需要 ECR 拉取權限。
- **跨 Region**：設定 ECR replication，把 image 自動複製到每個使用的 Region，部署時從本地 Region 拉取，降低延遲，也讓 DR Region 在主 Region 故障時仍有 image 可用（第 34 章）。
- **安全**：啟用 enhanced scanning 持續偵測弱點；對 image 做簽章，並在部署前驗證簽章；啟用 tag immutability；用 pull through cache 把外部公開 image 收進受控的 registry，避免直接依賴 Docker Hub。

### 多租戶與隔離

SaaS 平台在 EKS 或 ECS 上服務多個客戶時，隔離層級由弱到強大致是：同 cluster 不同 namespace／service（靠網路政策與 IAM 隔離）、每個租戶獨立節點或 Fargate（不共用 kernel）、每個租戶獨立 cluster、每個租戶獨立帳號。越強的隔離成本越高；SAP 題目通常會從合規要求（例如「客戶資料處理不得與其他客戶共用主機」）推導出最低需要的層級。

### 成本最佳化

- **Compute Savings Plans** 同時涵蓋 EC2、Fargate 與 Lambda，適合 compute 型態仍在變化（例如正從 EC2 遷移到 Fargate）的組織；EC2 Instance Savings Plans 折扣較深但綁定 instance family 與 Region（第 39 章）。
- 可中斷的工作用 Spot（EC2 Spot、Fargate Spot、Batch Spot compute environment、Karpenter 的 Spot NodePool），並允許多種 instance type 以降低中斷。
- 改用 Graviton（ARM64）通常有更好的性價比，但需要以多架構方式建置 image。
- EKS 上用 Karpenter consolidation 回收零散資源；ECS on EC2 用 capacity provider 的 managed scaling 避免閒置 instance。
- 開發與測試環境在夜間把 ECS service 的 desired count 或 EKS 的節點縮到零。

### 從 VM 遷移到 container 的現代化路徑

第 44 至 46 章會完整討論遷移策略。與本章相關的判斷是：

- **Replatform（換平台，不大改程式）**：把既有 Java 或 .NET 應用打包成 container，放到 ECS on Fargate 或 Beanstalk，取得受管擴展與部署，但不重寫架構。
- **Refactor（重構）**：把單體拆成微服務，以 ECS service 或 EKS deployment 分開部署，搭配 Service Connect 或 VPC Lattice（第 7 章）做服務間通訊。
- 有 Kubernetes 經驗與需求的組織選 EKS；想讓應用團隊專注在程式碼的組織選 ECS 或更高抽象的平台。很多企業同時存在兩者，平台團隊的任務是讓 IAM、網路、日誌、image 治理在兩者之間一致。

延伸閱讀：[Amazon ECS task definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)、[Task IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)、[Task execution IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)、[ECS cluster auto scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-auto-scaling.html)、[Amazon ECS Express Mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)、[ECR interface VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)、[AWS Batch compute environments](https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html)、[Elastic Beanstalk deployment policies](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html)。

## 本章重點整理

- Container 把程式與它的 runtime、函式庫、設定打包成不可變的 image，在任何主機上以相同方式執行；它共用主機 kernel，比 VM 輕量但隔離較弱。
- ECR 是受管 container registry，支援 repository policy、tag immutability、lifecycle policy、弱點掃描、跨 Region 與跨帳號複寫；private subnet 無 NAT 時需要 `ecr.api`、`ecr.dkr` interface endpoint 與 S3 gateway endpoint。
- ECS 的四個核心物件是 cluster、task definition（有版本的 JSON 範本）、task（執行中的實例）與 service（維持 desired count、整合 ELB、滾動部署）；ECS 本身不收費。
- Execution role 給 ECS agent 拉 image、寫 log、取 secret；task role 給 container 中的應用程式呼叫 AWS 服務；兩者分開才能做到最小權限。
- Fargate 是 ECS 與 EKS 的 serverless 運算選項，必須使用 `awsvpc`、每個 task 獨立隔離、按 vCPU／記憶體秒數計費，不支援 GPU、privileged container 與 DAEMON；Fargate Spot 便宜但會在約 2 分鐘通知後中斷。
- ECS 的擴展有兩層：service auto scaling 調整 task 數，ASG capacity provider 的 managed scaling 調整 EC2 容量；capacity provider strategy 以 base 與 weight 混用 Fargate 與 Fargate Spot。
- `awsvpc` 模式的 task 在 ALB target group 中使用 `ip` target type；bridge 模式可用動態 host port；deployment circuit breaker 可以自動回復失敗的部署。
- 選 EKS 的理由是既有 Kubernetes、生態系工具或可移植性；沒有這些需求時 ECS 的營運負擔較低。
- EKS 的 data plane 可以是 managed node groups、self-managed nodes、Fargate profiles 或 EKS Auto Mode；Karpenter 依待排程 Pod 直接挑選最合適的 instance 並做 consolidation。
- EKS 的 VPC CNI 讓每個 Pod 拿 VPC IP，IP 不足時用 prefix delegation 或 custom networking；Pod 的 AWS 權限用 IRSA 或 EKS Pod Identity，而不是節點 instance role。
- ECS Anywhere 讓地端主機由 AWS 上的 ECS control plane 管理；EKS Anywhere 在地端執行完整的 Kubernetes cluster。
- Elastic Beanstalk 從程式碼建立並管理 EC2、ASG、ELB；部署策略有 all at once、rolling、rolling with additional batch、immutable、traffic splitting，另可用 swap URL 做 blue/green；正式環境的 RDS 應建在 Beanstalk 外部。
- App Runner 已不接受新客戶；新的「只給 image 就上線」需求可以評估 ECS Express Mode。
- AWS Batch 以 job definition、job queue、compute environment 管理大量批次工作，array job 最多 10,000 個 child，搭配 Spot 與 retry strategy 降低成本。
- 緊耦合 HPC 使用 EFA（OS-bypass，適用 MPI／NCCL）、cluster placement group 與 ParallelCluster（Slurm），共享儲存常用 FSx for Lustre。

## 本章練習題

### 練習 21-1｜SAA｜單選｜最少營運負擔的 container 平台

Wanderly 的搜尋服務已打包成 Linux container image，需要長時間執行、跨兩個 AZ 高可用，並放在 ALB 後面。團隊只有三位工程師，沒有人有 Kubernetes 經驗，也沒有任何需要 Kubernetes 的工具。主管要求以最少的營運負擔上線，並且不想管理任何伺服器的 patch。

最合適的方案是什麼？

- A. 建立 EKS cluster 並使用 managed node groups 執行服務
- B. 在 EC2 Auto Scaling group 上安裝 Docker，以 user data 啟動 container
- C. 使用 ECS service，以 Fargate 執行 task，並與 ALB target group 整合
- D. 把搜尋服務改寫成 Lambda 函式，透過 API Gateway 提供

> [!answer]- 答案：C
> **A ✗** EKS 可以運作，但團隊沒有 Kubernetes 需求與經驗，要承擔版本升級、附加元件與 Kubernetes 物件模型等額外營運工作；managed node groups 的節點仍是 EC2，AMI 更新仍需要處理。
>
> **B ✗** 自己在 EC2 上跑 Docker，需要自行處理 OS patch、container 重啟、部署與 ALB 註冊，營運負擔最高。
>
> **C ✓** ECS 是 AWS 原生的 orchestrator，不需要學 Kubernetes；Fargate 讓 AWS 負責底層運算與 patch，service 維持 desired count、跨 AZ 放置 task，並自動與 ALB target group 整合。
>
> **D ✗** 搜尋服務需要長連線池與啟動時載入大型字典，改寫成 Lambda 會遇到冷啟動與重新載入的問題，而且需要改寫程式，不符合「最少營運負擔上線」。
>
> **考點**：SAA-3.2、SAA-2.2｜ECS on Fargate 的適用情境

### 練習 21-2｜SAA｜單選｜Task role 與 execution role

一個 ECS on Fargate 的 task 可以正常啟動、從 ECR 拉到 image，也能把 log 寫到 CloudWatch Logs。但 container 中的應用程式呼叫 `s3:GetObject` 讀取設定檔時收到 AccessDenied。工程師檢查後發現，`s3:GetObject` 權限被加在 task definition 的 execution role 上，task definition 沒有設定 task role。

應如何修正，並符合最小權限？

- A. 建立一個只允許讀取該設定檔所在 S3 路徑的 IAM role 作為 task role，在 task definition 設定 `taskRoleArn`，並從 execution role 移除 S3 權限
- B. 把 `AmazonS3FullAccess` 也加到 execution role，確保應用程式有足夠權限
- C. 在 S3 bucket policy 中允許 `ecs-tasks.amazonaws.com` 服務主體讀取所有物件
- D. 改用 EC2 launch type，並把 S3 權限加到 container instance 的 instance profile

> [!answer]- 答案：A
> **A ✓** Execution role 給 ECS agent 與 Fargate 基礎設施拉 image、寫 log、取 secret；應用程式程式碼使用的是 task role 的臨時憑證。設定只含所需 S3 路徑的 task role，並移除 execution role 上用不到的權限，才符合最小權限。
>
> **B ✗** 應用程式不會使用 execution role 的憑證，加再多權限也解決不了；`AmazonS3FullAccess` 還大幅擴大權限範圍。
>
> **C ✗** 允許服務主體並不會讓應用程式的請求以該主體身份送出；應用程式需要有身份（task role）才能被授權，而且允許所有物件也違反最小權限。
>
> **D ✗** 把權限放在 instance profile 會讓同一台 instance 上所有 task 都共享這些權限，違反最小權限；改變 launch type 也是不必要的大變更。
>
> **考點**：SAA-1.2、SAA-1.1｜ECS task role 與 execution role

### 練習 21-3｜SAA｜選兩項｜Private subnet 無法拉取 image

Wanderly 把一個 ECS on Fargate service 搬到沒有 NAT Gateway、也沒有 Internet Gateway 路由的 isolated subnet，以符合「workload 不得連到 Internet」的規範。Task 啟動時失敗，錯誤是 `CannotPullContainerError`，訊息顯示連線逾時。Execution role 已有完整的 ECR 拉取權限，log 已透過 CloudWatch Logs interface endpoint 正常傳送。

哪兩個步驟是必要的？（選兩項）

- A. 在 task definition 中把 `assignPublicIp` 設為 `ENABLED`
- B. 建立 `com.amazonaws.{region}.ecr.api` 與 `com.amazonaws.{region}.ecr.dkr` 的 interface VPC endpoint，並允許 task 的 security group 以 443 連入
- C. 把 ECR 的拉取權限也加到 task role
- D. 建立 S3 gateway VPC endpoint，並關聯到這些 subnet 的 route table
- E. 把 task 的記憶體從 2 GB 提高到 8 GB

> [!answer]- 答案：B、D
> **A ✗** Public IP 只有在 subnet 有指向 Internet Gateway 的路由時才有用；而且讓 task 連 Internet 違反規範。
>
> **B ✓** 拉 image 時，取得授權 token 走 ECR API（`ecr.api`），取得 manifest 走 Docker registry 端點（`ecr.dkr`）。沒有 Internet 路徑時，必須透過這兩個 interface endpoint 在 VPC 內存取。
>
> **C ✗** 拉 image 由 execution role 負責，題目也說明它已有權限；錯誤是連線逾時，代表問題在網路路徑而非權限。
>
> **D ✓** ECR 的 image layer 實際存放在 S3。只有 ECR endpoint 時，manifest 拿得到，下載 layer 卻會逾時；必須建立 S3 gateway endpoint 並加入 route table。
>
> **E ✗** 記憶體大小與能否連到 ECR 無關。
>
> **考點**：SAA-1.2、SAA-3.4｜ECR VPC endpoints 與 S3 gateway endpoint

### 練習 21-4｜SAA｜單選｜Task 放不下

Wanderly 的訂單處理服務跑在 ECS 的 EC2 launch type cluster 上，EC2 由一個固定大小為 4 台的 Auto Scaling group 提供。團隊已設定 service auto scaling 以 CPU 70% 為目標調整 desired count。促銷時 desired count 從 8 增加到 20，但其中 12 個 task 一直等待容量無法啟動，回應時間持續惡化。團隊希望 task 與 EC2 容量能自動一起擴展，且縮減時不要終止仍在執行 task 的 instance。

最合適的做法是什麼？

- A. 把 service auto scaling 的目標 CPU 從 70% 調低到 40%
- B. 把 ASG 的 desired capacity 手動改為 12 台並固定不變
- C. 在 ASG 上另外設定以 instance CPU 為目標的 target tracking policy
- D. 為 cluster 建立 ASG capacity provider，啟用 managed scaling 與 managed termination protection，並讓 service 使用這個 capacity provider

> [!answer]- 答案：D
> **A ✗** 調低目標會讓 desired count 更早、更多地增加，但 EC2 容量不變，只會有更多 task 放不下。
>
> **B ✗** 手動固定 12 台可以暫時解決，但無法隨流量自動擴縮，離峰時浪費成本，下一次更大的尖峰仍會不足。
>
> **C ✗** Instance CPU 反映的是「已放上去的 task」的負載；放不下的 task 不會增加任何 instance 的 CPU，所以這個 policy 無法對「容量不足」做出反應，縮減時也可能終止仍有 task 的 instance。
>
> **D ✓** ASG capacity provider 的 managed scaling 依據 task 需要的容量（`CapacityProviderReservation`）自動調整 ASG，讓等待中的 task 有地方可放；managed termination protection 確保縮減時只終止沒有 task 的 instance。這把兩層擴展正確地串起來。
>
> **考點**：SAA-3.2、SAA-2.1｜ECS capacity provider 與 cluster auto scaling

### 練習 21-5｜SAA｜單選｜多個服務共用 ALB

Wanderly 有三個 ECS on Fargate 微服務：`search`、`reviews`、`bookings`，都要透過 `https://www.wanderly.example` 對外提供，分別以 `/search/*`、`/reviews/*`、`/bookings/*` 路徑區分。團隊希望只使用一個 Load Balancer 以降低成本，並讓 task 擴縮時自動更新後端。

應如何設定？

- A. 使用一個 NLB，為每個服務建立一個 listener port，target type 設為 `instance`
- B. 使用一個 ALB，為每個服務建立 target type 為 `ip` 的 target group，在 HTTPS listener 上以 path-based rule 分流，並讓每個 ECS service 關聯自己的 target group
- C. 為每個服務各建一個 ALB，再用 Route 53 weighted routing 依路徑分流
- D. 使用一個 ALB，建立一個共用的 target group，把三個服務的 task 都註冊進去，並由應用程式判斷路徑

> [!answer]- 答案：B
> **A ✗** NLB 是第 4 層的 Load Balancer，看不到 HTTP 路徑，無法依 `/search/*` 分流；Fargate task 也必須使用 `ip` target type，而不是 `instance`。
>
> **B ✓** ALB 的 listener rule 可以依路徑把請求送到不同的 target group；Fargate 使用 `awsvpc`，每個 task 有自己的 IP，target type 必須是 `ip`。ECS service 關聯 target group 後，會自動註冊與解除註冊 task。
>
> **C ✗** 三個 ALB 增加成本；Route 53 是 DNS 服務，只看網域名稱，無法依 URL 路徑分流。
>
> **D ✗** 共用 target group 會把任何路徑的請求隨機送到三種服務的 task，大部分請求會送錯；各服務也無法獨立擴縮與健康檢查。
>
> **考點**：SAA-3.2、SAA-4.2｜ALB path-based routing 與 ECS `ip` target type

### 練習 21-6｜SAA｜單選｜降低 worker 成本

Wanderly 的照片處理 worker 是一個 ECS on Fargate service，從 SQS 讀取工作，每個工作約 30 秒，處理失敗時訊息會在 visibility timeout 後重新出現並被重試。目前平時跑 20 個 task。團隊希望大幅降低成本，但任何時候都至少要有 4 個 task 在處理，避免 queue 完全停滯。

最合適的做法是什麼？

- A. 把 service 改為只使用 `FARGATE_SPOT` capacity provider
- B. 購買 EC2 Reserved Instances，並把 service 改為 EC2 launch type
- C. 設定 capacity provider strategy：`FARGATE` 的 base 為 4、weight 為 1，`FARGATE_SPOT` 的 weight 為 4
- D. 把每個 task 的 vCPU 與記憶體加倍，task 數減半

> [!answer]- 答案：C
> **A ✗** 全部使用 Fargate Spot 最便宜，但 Spot 容量可能同時被回收或暫時無法取得，無法保證「至少 4 個 task」。
>
> **B ✗** 改成 EC2 launch type 需要自行管理 instance 與容量；RI 是一年或三年的承諾，對可中斷的 worker 而言，Spot 的折扣通常更有效，營運負擔也較低。
>
> **C ✓** Base 4 讓前 4 個 task 固定跑在一般 Fargate 上，保證最低處理能力；其餘 task 依 1:4 分配，大部分放在便宜的 Fargate Spot。Worker 可以中斷重試，正適合 Spot。
>
> **D ✗** Fargate 按宣告的 vCPU 與記憶體計費，資源加倍、數量減半，總費用大致不變，並沒有降低成本。
>
> **考點**：SAA-4.2｜Fargate Spot 與 capacity provider strategy

### 練習 21-7｜SAA｜單選｜Beanstalk 部署策略

Wanderly 的會員後台跑在 Elastic Beanstalk 上，有 10 台 instance。過去一次部署中，新版本在部分 instance 上啟動失敗，滾動部署進行到一半卡住，新舊版本混雜，回復花了 40 分鐘。團隊要求：部署期間維持完整容量，新版失敗時能最快回復，而且回復時不能動到原本正在服務的 instance；可以接受部署期間短暫增加成本。

應使用哪種 deployment policy？

- A. Immutable
- B. Rolling
- C. All at once
- D. Rolling with additional batch

> [!answer]- 答案：A
> **A ✓** Immutable 在臨時的新 Auto Scaling group 中建立全新的 instance 部署新版，全部通過健康檢查後才移入環境並終止舊 instance。新版失敗時只要終止新 instance，原本的 instance 完全沒被修改，回復最快；代價是部署期間暫時雙倍容量。
>
> **B ✗** Rolling 會一批一批把舊 instance 改成新版，部署期間容量減少一批；失敗時已更新的 instance 要再滾動部署舊版，正是題目遇到的問題。
>
> **C ✗** All at once 同時更新所有 instance，部署期間會停機，失敗時整個服務中斷。
>
> **D ✗** Rolling with additional batch 先多開一批 instance 維持容量，但之後仍是就地更新既有 instance；失敗時同樣需要再部署一次舊版，回復慢且會動到原本的 instance。
>
> **考點**：SAA-2.2、SAA-3.2｜Elastic Beanstalk deployment policies

### 練習 21-8｜SAA｜選兩項｜ECR 映像治理

稽核發現 Wanderly 的 ECR repository 有兩個問題：一是有人用同一個 `1.4.2` tag 重新 push 了不同內容的 image，導致正式環境的部分 task 跑的是未經測試的程式；二是 repository 累積了數千個再也不會用到的未加 tag 的舊 image，儲存費用持續上升。團隊希望以最少的人工作業解決這兩個問題。

哪兩個做法最合適？（選兩項）

- A. 在 task definition 中一律使用 `latest` tag，確保永遠部署最新的 image
- B. 每月由工程師手動檢查並刪除舊 image
- C. 為 repository 啟用 tag immutability
- D. 在 ECR 底層的 S3 bucket 設定 lifecycle rule
- E. 為 repository 設定 lifecycle policy，自動過期超過指定天數的未加 tag 的 image

> [!answer]- 答案：C、E
> **A ✗** `latest` 每次 push 都會指向不同的 image，讓部署更不可預測，正是第一個問題的根源。
>
> **B ✗** 手動清理容易遺漏，也不符合「最少人工作業」。
>
> **C ✓** Tag immutability 啟用後，已存在的 tag 不能被覆寫成另一個 image，確保 `1.4.2` 永遠代表同一份內容。
>
> **D ✗** ECR 的儲存由 AWS 管理，你看不到也無法設定底層 S3 bucket；要用 ECR 自己的 lifecycle policy。
>
> **E ✓** ECR lifecycle policy 可以依「未加 tag 且超過 N 天」或「只保留最近 N 個 image」等規則自動刪除 image，持續控制儲存費用。
>
> **考點**：SAA-1.2、SAA-4.1｜ECR tag immutability 與 lifecycle policy

### 練習 21-9｜SAA｜單選｜大量獨立批次工作

Wanderly 每天凌晨要重新計算 200 萬組「旅館 × 日期」的房價，每組計算彼此獨立，已打包成 container，單組需要 5 到 20 分鐘、2 vCPU 與 4 GB 記憶體。計算失敗時可以重跑。全部工作需在 4 小時內完成，團隊希望成本最低、且不想自己寫排程與重試邏輯。

最合適的方案是什麼？

- A. 以 EventBridge 觸發 Lambda，每個 Lambda 處理一組計算
- B. 使用 AWS Batch，建立以 Spot 為主、允許多種 instance type 的 managed compute environment，將工作以 array job 提交，並在 job definition 中設定 retry strategy
- C. 建立一個大型 EC2 On-Demand instance，用 cron 依序執行所有計算
- D. 使用 EMR cluster，把每組計算寫成 Spark job

> [!answer]- 答案：B
> **A ✗** 單組計算可能要 20 分鐘，超過 Lambda 的 15 分鐘上限。
>
> **B ✓** AWS Batch 負責排隊、啟動運算資源與重試；array job 讓一次提交展開成大量 child job；可重跑的工作適合 Spot，允許多種 instance type 能降低容量不足與中斷的影響；佇列清空後資源縮到零，不會閒置付費。
>
> **C ✗** 單台 instance 依序執行無法在 4 小時內完成 200 萬組計算，而且 On-Demand 比 Spot 貴，也沒有自動重試。
>
> **D ✗** EMR 適合 Spark 或 Hadoop 的大數據處理；把獨立的 container 計算改寫成 Spark job 需要大幅改程式，增加複雜度。
>
> **考點**：SAA-3.2、SAA-4.2｜AWS Batch array job 與 Spot

### 練習 21-10｜SAA｜單選｜緊耦合 HPC

Wanderly 的資料科學團隊與一所大學合作，要執行一個以 MPI 撰寫的大規模旅遊需求模擬。模擬跨 64 個節點執行，每一步計算後所有節點都要交換資料，測試發現節點間的網路延遲是最大的瓶頸。團隊希望取得最低的節點間延遲，並能依工作佇列自動擴縮節點。

最合適的設計是什麼？

- A. 把 64 個節點平均分散到三個 AZ 的 spread placement group，以提高可用性
- B. 使用 AWS Batch 的 Fargate compute environment，以 array job 執行 64 份模擬
- C. 使用 Lambda 函式平行執行模擬，透過 SQS 交換節點間資料
- D. 以 AWS ParallelCluster 建立 Slurm 叢集，使用支援 EFA 的 instance type 並啟用 EFA，將運算節點放在同一個 subnet 的 cluster placement group 中

> [!answer]- 答案：D
> **A ✗** 把節點分散到多個 AZ 會增加節點間的網路延遲，正好與需求相反；spread placement group 是為了降低同時故障的風險，不是為了效能。
>
> **B ✗** Array job 適合彼此獨立的工作；MPI 模擬需要節點間持續通訊，而 Fargate 也不支援 EFA。
>
> **C ✗** Lambda 不適合長時間、需要節點間低延遲通訊的運算；透過 SQS 交換資料的延遲遠高於直接網路通訊。
>
> **D ✓** EFA 提供 OS-bypass 的節點間通訊，大幅降低 MPI 延遲；cluster placement group 把節點放在物理位置相近處；EFA 的 OS-bypass 流量需要節點在同一 subnet。ParallelCluster 以 Slurm 依佇列自動擴縮節點。
>
> **考點**：SAA-3.2、SAA-3.4｜EFA、cluster placement group 與 ParallelCluster

### 練習 21-11｜SAP｜單選｜遷移既有 Kubernetes 工作

Wanderly 併購的行程新創在自己的機房運行 Kubernetes，使用數十個 Helm chart 與兩個第三方資料庫 operator 管理系統，工程師都熟悉 kubectl 與 Kubernetes 的部署流程。Wanderly 要求在 3 個月內把這些系統搬到 AWS，盡量不修改既有的部署資產，並保留未來在其他環境執行的可能性；同時希望減少 Kubernetes control plane 的維運工作。

最合適的方案是什麼？

- A. 遷移到 Amazon EKS，使用 managed node groups（或 Karpenter）提供節點，沿用既有的 Helm chart 與 operator
- B. 把所有 Helm chart 改寫成 ECS task definition 與 service，部署到 ECS on Fargate
- C. 在 EC2 上自行安裝與維運 Kubernetes control plane，以完全複製地端環境
- D. 把每個服務部署到各自的 Elastic Beanstalk 環境

> [!answer]- 答案：A
> **A ✓** EKS 提供標準的 Kubernetes API，既有的 Helm chart、operator 與 kubectl 流程可以沿用，保留可移植性；control plane 由 AWS 管理與跨 AZ 備援，減少維運工作。Managed node groups 或 Karpenter 進一步減輕節點管理。
>
> **B ✗** ECS 不支援 Helm chart 與 Kubernetes operator，要改寫所有部署資產並替代 operator 的功能，3 個月內風險很高，也失去可移植性。
>
> **C ✗** 自建 control plane 可以完全複製，但要自己負責 etcd 備份、高可用、升級與修補，違反「減少 control plane 維運工作」。
>
> **D ✗** Beanstalk 無法執行 Kubernetes operator 與 Helm chart，同樣需要大幅改寫，而且數十個服務分散在各自環境中難以管理。
>
> **考點**：SAP-4.2、SAP-4.3｜既有 Kubernetes 工作遷移到 EKS

### 練習 21-12｜SAP｜單選｜EKS Pod IP 耗盡

Wanderly 的 EKS cluster 使用 Amazon VPC CNI，節點位於 VPC `10.20.0.0/16` 中兩個 /22 的 private subnet。隨著微服務增加，新 Pod 開始因無法取得 IP 而無法啟動，但節點的 CPU 與記憶體仍有大量空間。VPC 主要 CIDR 已無未分配空間，而 `10.0.0.0/8` 其餘範圍已分配給地端與其他 VPC。團隊希望不重建 cluster、不影響正在執行的服務。

最合適的做法是什麼？

- A. 把節點改用更大的 instance type，以取得更多 ENI 與 IP
- B. 改用 Fargate profiles，讓 Pod 不再使用 VPC IP
- C. 為 VPC 加入 `100.64.0.0/16` 作為 secondary CIDR，在其中建立 Pod 專用 subnet，啟用 VPC CNI custom networking 讓 Pod 使用這些 subnet 的 IP
- D. 把 subnet 的 CIDR 從 /22 修改為 /20

> [!answer]- 答案：C
> **A ✗** 更大的 instance 可以掛更多 ENI，但 IP 仍然來自同兩個已耗盡的 subnet；問題在 subnet 位址空間，而不是每個節點的 ENI 數量。
>
> **B ✗** Fargate 上的每個 Pod 同樣會在 subnet 中取得一個 VPC IP，不能解決位址不足，還會受到 DaemonSet 等限制。
>
> **C ✓** VPC 可以加入 secondary CIDR；`100.64.0.0/10` 範圍常用來避開 RFC 1918 已被分配的空間。VPC CNI custom networking 讓 Pod 的 ENI 使用另一組 subnet，與節點的 subnet 分開，可以在既有 cluster 上逐步套用到新節點，不影響正在執行的服務。
>
> **D ✗** Subnet 建立後 CIDR 不能修改，無法原地放大。
>
> **考點**：SAP-1.1、SAP-3.3｜EKS VPC CNI custom networking 與 secondary CIDR

### 練習 21-13｜SAP｜選兩項｜EKS 運算成本最佳化

Wanderly 的 EKS cluster 有 14 個 managed node group，分別對應不同的 instance type 與 On-Demand／Spot 組合，使用 Cluster Autoscaler。平台團隊發現：節點平均利用率只有 35%，因為很多節點只剩少量 Pod；新的 Pod 規格出現時常要新增 node group；擴展有時要好幾分鐘。整體 compute 用量的基線穩定，但服務正持續從 EC2 遷移到 Fargate 與 Lambda。財務要求在一年內大幅降低 compute 費用，同時降低平台團隊的維運負擔。

哪兩個做法最合適？（選兩項）

- A. 改用 Karpenter，以 NodePool 允許多種 instance type 與 Spot／On-Demand，並啟用 consolidation 回收低利用率節點
- B. 把所有 Pod（包括 DaemonSet 與需要 GPU 的 Pod）都改到 Fargate profiles
- C. 再增加更多 managed node group，讓每種 Pod 規格都有完全對應的 node group
- D. 針對穩定的 compute 基線購買 Compute Savings Plans
- E. 針對目前的 instance family 購買三年期 EC2 Instance Savings Plans，涵蓋全部用量

> [!answer]- 答案：A、D
> **A ✓** Karpenter 依待排程 Pod 的需求直接選擇最合適的 instance，不需要為每種規格建立 node group，擴展也更快；consolidation 把零散的 Pod 合併到較少或較便宜的節點，直接解決 35% 的低利用率。
>
> **B ✗** EKS 的 Fargate 不支援 DaemonSet 與 GPU，這些 Pod 無法遷移；全部改成 Fargate 也不一定比高利用率的 EC2 便宜。
>
> **C ✗** 更多 node group 只會增加管理負擔，也無法解決節點利用率低的問題。
>
> **D ✓** Compute Savings Plans 同時涵蓋 EC2、Fargate 與 Lambda，不綁 instance family 與 Region，在服務正從 EC2 移往 Fargate 與 Lambda 時，仍能持續套用到穩定的基線用量。
>
> **E ✗** EC2 Instance Savings Plans 綁定 instance family 與 Region，只適用於 EC2；服務正在遷往 Fargate 與 Lambda，再加上 Karpenter 會改變 instance 選擇，三年期且涵蓋全部用量很可能造成承諾用不完。
>
> **考點**：SAP-3.5、SAP-1.5｜Karpenter consolidation 與 Compute Savings Plans

### 練習 21-14｜SAP｜單選｜地端 container 由雲端管理

Wanderly 併購的旅行社在台灣有一間自有機房，因合約規定部分客戶個資的處理程式必須在這間機房內執行，至少兩年內無法搬遷。機房已透過 Direct Connect 連到 AWS。Wanderly 的雲端工作全部跑在 ECS 上，團隊希望地端這些 container 也能用相同的 task definition、部署流程與 console 管理，並且不想在地端維運任何 orchestrator 的 control plane。

最合適的做法是什麼？

- A. 在地端建置 EKS Anywhere cluster，並把 ECS task definition 改寫成 Kubernetes manifest
- B. 在地端伺服器安裝 SSM agent 與 ECS agent，以 ECS Anywhere 註冊為 external instance，使用 `EXTERNAL` launch type 執行 task
- C. 在地端每台伺服器安裝 Docker，以 Systems Manager Run Command 啟動 container
- D. 在機房部署 AWS Outposts rack，並在上面執行 ECS

> [!answer]- 答案：B
> **A ✗** EKS Anywhere 的 control plane 在地端，需要自己營運；而且必須把 ECS 的資產改寫成 Kubernetes，違反「相同的 task definition」與「不維運 control plane」。
>
> **B ✓** ECS Anywhere 讓地端主機註冊到 AWS 上的 ECS cluster，control plane 仍由 AWS 提供，可以沿用相同的 task definition、API 與 console；Direct Connect 提供地端與 AWS 之間的連線。
>
> **C ✗** 用 Run Command 啟動 container 沒有 orchestrator 的排程、重啟與部署管理，要自己寫大量腳本，也不是同一套 ECS 流程。
>
> **D ✗** Outposts 可以在地端執行 ECS，但需要訂購並安裝 AWS 的實體硬體，成本與導入時間遠高於直接利用既有伺服器；題目沒有需要 AWS 硬體或其他 AWS 服務在地端的要求。
>
> **考點**：SAP-4.3、SAP-1.1｜ECS Anywhere 的混合雲 container 管理

### 練習 21-15｜SAP｜單選｜多帳號多 Region 的 image 供應

Wanderly 有 40 個 workload 帳號，分布在東京與新加坡兩個 Region，都使用 ECS 執行服務。所有 image 由 shared services 帳號在東京的 CI/CD 管線建置並 push 到 ECR。目前的問題：新增帳號時要手動修改每個 repository policy；新加坡的部署從東京拉 image，啟動較慢；若東京 Region 故障，新加坡也無法拉到 image。團隊希望以最少的營運負擔解決這三個問題。

最合適的做法是什麼？

- A. 在每個 workload 帳號各自建立 ECR repository，由 CI/CD 管線逐一 push 到 40 個帳號
- B. 把 image 匯出成檔案存到 S3，以 S3 Cross-Region Replication 複製到新加坡，再由 task 啟動時下載載入
- C. 在 repository policy 中列出 40 個帳號的 ID，並讓新加坡的 task 改為透過 Transit Gateway 跨 Region 存取東京的 ECR
- D. 在 repository policy 中以 `aws:PrincipalOrgID` 條件允許整個 Organization 拉取，並設定 ECR cross-Region replication 把 image 自動複製到新加坡，新加坡的服務從本地 Region 的 repository 拉取

> [!answer]- 答案：D
> **A ✗** 每次建置都要 push 到 40 個帳號，管線變得複雜，帳號增加時仍要修改流程，營運負擔最高。
>
> **B ✗** ECS 從 container registry 拉 image，不支援直接從 S3 檔案啟動 task；自己實作下載與載入既複雜又脆弱。
>
> **C ✗** 列出帳號 ID 時，每新增帳號都要修改 policy；跨 Region 存取東京 ECR 仍然較慢，東京故障時依然無法拉取。
>
> **D ✓** `aws:PrincipalOrgID` 讓 Organization 內任何帳號都能拉取，新帳號自動適用；ECR replication 在 push 後自動把 image 複製到新加坡，新加坡從本地拉取更快，東京故障時也不受影響。
>
> **考點**：SAP-1.4、SAP-2.2｜ECR 跨帳號存取與 cross-Region replication

### 練習 21-16｜SAP｜單選｜EKS Pod 的最小權限

安全稽核發現，Wanderly 的 EKS cluster 中所有節點的 instance role 都附加了 S3、DynamoDB 與 SQS 的廣泛權限，因為不同的微服務各自需要其中一部分。結果任何一個 Pod 被入侵，攻擊者都能使用所有這些權限。cluster 中有 30 個微服務，各自使用不同的 Kubernetes service account。團隊希望每個微服務只拿到自己需要的權限，並且不修改應用程式的程式碼（應用程式使用 AWS SDK 的預設憑證鏈）。

最合適的做法是什麼？

- A. 為每個微服務建立 IAM user，並把 access key 存在 Kubernetes secret 中供 Pod 讀取
- B. 把每個微服務放到各自的 node group，並為每個 node group 設定只含該服務所需權限的 instance role
- C. 為每個微服務建立只含所需權限的 IAM role，使用 EKS Pod Identity（或 IRSA）把 role 關聯到該微服務的 service account，並從節點 instance role 移除這些應用程式權限
- D. 在 S3 bucket policy、DynamoDB 與 SQS 的 resource policy 中，以來源 IP 限制只有特定 Pod 能存取

> [!answer]- 答案：C
> **A ✗** 長期 access key 有外洩與輪替的風險，不符合最佳實務；存在 Kubernetes secret 中，有讀取 secret 權限的人都能拿到。
>
> **B ✗** 30 個服務各自一個 node group 會造成大量閒置容量與管理負擔，也違背容器共享節點的效益；同一 node group 中若有多個 Pod，仍會共享權限。
>
> **C ✓** EKS Pod Identity 與 IRSA 都讓 Pod 依 service account 取得專屬 IAM role 的臨時憑證，AWS SDK 的預設憑證鏈會自動使用，不需修改程式碼。每個服務只拿到自己的權限，再移除節點 role 上的應用程式權限，完成最小權限。
>
> **D ✗** Pod 的 IP 會隨重新排程而改變，以 IP 為授權依據既不可靠也難以維護；而且節點 role 的廣泛權限仍然存在。
>
> **考點**：SAP-2.3、SAP-3.2｜EKS Pod Identity／IRSA 與 Pod 層級最小權限
