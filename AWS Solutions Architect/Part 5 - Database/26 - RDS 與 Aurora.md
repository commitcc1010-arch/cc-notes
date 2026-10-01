---
chapter: 26
title: RDS 與 Aurora：受管關聯式資料庫
part: 5
---

# 第 26 章　RDS 與 Aurora：受管關聯式資料庫

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚把 MySQL 從 EC2 搬到 RDS 後，哪些工作交給 AWS、哪些仍是你的責任
> - 分辨 Multi-AZ（高可用）與 read replica（讀取擴展）：複寫方式、能不能讀、failover 怎麼發生
> - 依 RPO／RTO 選擇 automated backup、PITR、snapshot、Backtrack、cloning 或跨 Region 方案
> - 解釋 Aurora 為什麼「把儲存層拆出來」，以及 reader endpoint、custom endpoint、Serverless v2、Global Database 的用途
> - 用加密 snapshot copy、RDS Proxy、IAM DB authentication、Blue/Green Deployments 解決常見的安全與營運題
>
> **前置知識**：第 4 章（ACID、同步與非同步複寫、RPO／RTO）、第 5 章（DB subnet group 與 isolated subnet）、第 15 章（KMS）
> **考試比重**：SAA ★★★（Domain 2 高可用、Domain 3 資料庫效能、Domain 4 資料庫成本）｜SAP ★★★（Domain 2 業務持續、Domain 3 改善可靠性、Domain 4 遷移）

## 26.1 故事：訂單資料庫在凌晨三點停了

Wanderly 成立第一年，所有訂單、會員與房價都放在一台 EC2 上自己安裝的 MySQL。工程師小林寫了一支 cron job，每天凌晨兩點用 `mysqldump` 把資料庫匯出到 S3。這個做法撐了很久，直到某個週五凌晨三點，那台 EC2 所在 AZ 的硬體出了問題，instance 卡在無法連線的狀態。

小林在家裡開電腦，花了將近三個小時才在另一個 AZ 開出新機器、裝好 MySQL、把前一天凌晨兩點的 dump 匯回去。服務恢復了，但凌晨兩點到三點之間成立的四百多筆訂單不見了，客服花了一整週人工比對金流紀錄補單。事後檢討列出三個問題：**復原要人工做（RTO 三小時）、會遺失最多一天的資料（RPO 24 小時）、沒有人確定 dump 檔真的能用**。

技術主管提出新的要求：訂單資料庫在一個 AZ 故障時要自動恢復、資料遺失要以秒計算、工程師不要再手動 patch 作業系統與資料庫。同時，旺季的搜尋流量讓資料庫 CPU 長期在 80% 以上，報表查詢一跑就拖慢結帳。

這一章跟著 Wanderly 把資料庫搬上 **Amazon RDS**，再升級到 **Amazon Aurora**。每加一個功能，我們都問兩個問題：它解決的是「可用性」、「讀取效能」還是「資料復原」？它的代價是什麼？這三類問題在考題裡最常被混在一起，分清楚就能解掉大半的資料庫題。

## 26.2 RDS 是什麼：受管的是「維運」，不是「設計」

**Amazon RDS（Relational Database Service）** 是 AWS 的受管關聯式資料庫服務。你選擇資料庫引擎與機器大小，AWS 負責準備硬體、安裝與修補資料庫軟體、執行備份、偵測故障並自動切換。你連到的是一個 **endpoint（連線端點）**，也就是一個 DNS 名稱，例如 `orders-db.abc123.ap-northeast-1.rds.amazonaws.com`，而不是某台機器的 IP。

### 支援的引擎

| 引擎 | 說明 |
|---|---|
| MySQL、MariaDB、PostgreSQL | 開源引擎，功能最完整（read replica 最多；MySQL 與 PostgreSQL 另支援 Multi-AZ DB cluster） |
| Oracle、Microsoft SQL Server、IBM Db2 | 商用引擎，需處理授權：License Included（費用含授權）或 BYOL（自帶授權，依引擎與版本而定） |
| Aurora MySQL／Aurora PostgreSQL | AWS 重新設計儲存層的相容引擎，見 26.9 節 |

### 責任怎麼切

RDS 把「維運工作」受管化，但不會替你做「資料庫設計」。這條界線考試常拿來出題：

| AWS 負責 | 你負責 |
|---|---|
| 硬體、作業系統、資料庫軟體安裝與修補（在你設定的 maintenance window 內） | Schema、index、SQL 效能調校 |
| 自動備份與 transaction log 保存 | 決定 retention 天數、是否跨 Region 複製 |
| 故障偵測與 Multi-AZ failover | 是否啟用 Multi-AZ、應用程式能否重連 |
| 儲存加密的實作 | 建立時決定是否加密、選哪把 KMS key |
| 監控指標的收集 | 設定 CloudWatch alarm 並處理告警 |

因為作業系統由 AWS 管理，**你無法 SSH 登入 RDS 主機，也拿不到資料庫的最高權限帳號**（例如 MySQL 的 `SUPER`）。如果某套第三方軟體要求在資料庫主機上安裝 agent，或需要修改作業系統設定，標準 RDS 做不到，選項是 **RDS Custom**（目前支援 Oracle 與 SQL Server，讓你有作業系統與資料庫的特權存取，同時保留部分自動化），或是自己在 EC2 上安裝資料庫。

### 建立一個 RDS instance 要決定的事

1. **DB instance class**：機器大小，例如 `db.r7g.large`（`r` 是記憶體最佳化，`g` 代表 Graviton 處理器）。可以事後修改，修改時通常會重新啟動，若有 Multi-AZ 會先改 standby 再切換，縮短中斷時間。
2. **Storage**：gp3（一般用途，可分開調整 IOPS 與 throughput）、io1／io2（高 IOPS 需求）。可以開啟 **storage autoscaling**，空間快滿時自動加大。注意：**RDS 的儲存空間只能加大、不能縮小**。
3. **DB subnet group**：指定 RDS 可以放在哪些 subnet，必須涵蓋至少兩個 AZ。第 5 章的 isolated data subnet 就是為這裡準備的。
4. **Public access**：是否給 endpoint 一個 public IP。正式環境應設為 No，並用 security group 只允許 app tier 的 security group 連入 3306／5432。
5. **Multi-AZ、backup retention、加密、parameter group**：本章接下來逐一說明。

> [!note] 停止 RDS instance
> 開發環境下班時可以把 RDS instance **stop**，停止期間只收儲存與備份費用。但停止最多維持 7 天，第 7 天 AWS 會自動把它啟動，以免錯過必要的維護更新。長期不用的環境應該做 snapshot 後刪除。

把資料庫交給 RDS 後，小林的第一個需求是「AZ 故障時自動恢復」，這就是 Multi-AZ。

## 26.3 Multi-AZ：讓資料庫撐過一個 AZ 故障

### 為什麼需要

單一 instance 的資料庫只要所在 AZ 出事，就算資料都在，服務也停了。要讓服務撐過 AZ 故障，就要在另一個 AZ 隨時有一份「最新、可立即接手」的資料庫。關鍵字是「最新」：如果備援比主資料庫落後幾秒，切換時就會掉資料。所以 Multi-AZ 使用**同步複寫（synchronous replication）**：主資料庫的每一筆寫入，都要等備援也寫好，才回覆應用程式「成功」。

RDS 的 Multi-AZ 有兩種部署方式，名稱很像，行為差很多。

### Multi-AZ DB instance deployment：一主一備

這是最傳統、所有引擎都支援的形式：

- 在另一個 AZ 建立一台 **standby（備援 instance）**，以儲存層的同步複寫保持與 primary 一致。
- **Standby 不能讀也不能寫**，它唯一的工作是等待接手。它不分擔任何讀取流量。
- 備份從 standby 取得，避免影響 primary 的 I/O。
- 發生故障時，RDS 自動把 standby 升為新的 primary，並把 endpoint 的 DNS 記錄改指向它。官方描述 failover 通常在 60–120 秒內完成。

### Failover 怎麼發生

```text
           應用程式（連 orders-db.xxx.rds.amazonaws.com）
                           │
                ① DNS 解析 → 10.20.64.15
                           ▼
 AZ-a ┌───────────────────────────┐        AZ-c ┌───────────────────────────┐
      │ Primary 10.20.64.15       │ ─②同步─►    │ Standby 10.20.65.22       │
      │ （接受讀寫）              │   複寫       │ （不可讀寫）              │
      └───────────────────────────┘             └───────────────────────────┘
                ③ AZ-a 故障，RDS 偵測到 primary 失效
                ④ 把 standby 升為 primary
                ⑤ endpoint 的 DNS 改為 → 10.20.65.22
                           ▼
           ⑥ 應用程式的舊連線中斷，重新解析 DNS 後重連成功
```

① 應用程式永遠只知道 endpoint 名稱。② 每筆 commit 都要兩邊寫好才算完成，所以切換時不會遺失已 commit 的交易。③④ 偵測與升格由 RDS 自動完成，不需要人工。⑤ endpoint 名稱不變，背後的 IP 變了。⑥ 這一步是應用程式的責任：**既有連線一定會斷**，未完成的交易會被 rollback；應用程式要能重連，而且不能把 IP 寫死，也不能讓 DNS 快取太久（例如 Java 的 JVM 預設可能長時間快取 DNS 結果，需要把 TTL 調低）。

觸發自動 failover 的情況包括：primary 所在 AZ 故障、primary 主機或儲存故障、修改 instance class、作業系統修補，以及你在 reboot 時選擇「reboot with failover」（常用來演練）。

### Multi-AZ DB cluster deployment：一寫兩讀

較新的形式，目前支援 MySQL 與 PostgreSQL：

- 三台 instance 分布在三個 AZ：一台 **writer**、兩台 **reader**。
- 使用資料庫引擎的複寫，**至少一台 reader 確認收到變更後才算 commit**（官方稱為 semisynchronous，半同步）。
- **兩台 reader 可以讀**，提供 **reader endpoint** 分散讀取。
- Failover 比 instance deployment 快很多（官方描述通常在 35 秒以內），因為 reader 已經在運作中。

| 比較 | Multi-AZ DB instance | Multi-AZ DB cluster |
|---|---|---|
| 拓撲 | 1 primary + 1 standby（2 AZ） | 1 writer + 2 readers（3 AZ） |
| Standby 可讀 | 否 | 是（有 reader endpoint） |
| 複寫 | 同步（儲存層） | 半同步（引擎層，至少一台 reader 確認） |
| Failover 時間 | 通常 60–120 秒 | 通常 35 秒以內 |
| 引擎 | 所有 RDS 引擎 | MySQL、PostgreSQL |

> [!warning] 常見誤解
> 「開了 Multi-AZ，讀取效能就會變好。」對 Multi-AZ DB instance 來說完全不會：standby 不服務任何流量。Multi-AZ 解決的是**可用性**，不是**讀取擴展**。題目同時要求「高可用」與「分擔報表讀取」時，答案通常是「Multi-AZ + read replica」，或改用 Multi-AZ DB cluster／Aurora。

> [!note] Multi-AZ 不防人為錯誤
> 同步複寫會把「錯誤」也同步過去。工程師執行了 `DELETE FROM orders` 沒加 `WHERE`，standby 上的資料也在同一瞬間消失。防範人為錯誤要靠 26.5 節的備份與 PITR。

## 26.4 Read replica：把讀取分出去

解決了可用性，接著處理「搜尋與報表拖慢結帳」的問題。Wanderly 的流量裡，讀取遠多於寫入：每一次訂單寫入，背後可能有上百次房價與庫存查詢。把讀取分到其他資料庫，primary 就能專心處理寫入。

### 運作方式

**Read replica（唯讀副本）** 是另一台獨立的 DB instance，有自己的 endpoint。Primary 把變更以**非同步複寫（asynchronous replication）** 送過去：primary commit 後立刻回覆應用程式，不等 replica。這帶來兩個結果：

1. **Primary 的寫入延遲不受 replica 影響**，replica 再多也不拖慢寫入。
2. **Replica 會落後（replication lag）**。剛寫入的資料，可能要幾百毫秒到數秒後才能在 replica 上讀到；primary 寫入量很大或 replica 規格太小時，lag 會更長。用 CloudWatch 的 `ReplicaLag` 指標監控。

所以 read replica 適合「可以接受資料晚一點」的讀取，例如報表、搜尋列表、推薦；而「使用者剛下單，馬上要看到自己的訂單」這種 **read-after-write（寫後即讀）** 的路徑，應該讀 primary。

### 重要特性

- MySQL、MariaDB、PostgreSQL 每個 source 最多 15 個 read replica。商用引擎的上限與限制各不相同（例如 Oracle 也可建立到 15 個但 AWS 建議 5 個以內；Oracle 與 Db2 還有不接受連線、只用於 DR 的 mounted／standby replica），考試以開源引擎的 15 個為主。
- 建立 read replica 前，source 必須**開啟 automated backups**（retention 大於 0）。
- Replica 可以在同一個 AZ、不同 AZ，或**不同 Region（cross-Region read replica）**。同一 Region 內的複寫流量不收資料傳輸費；跨 Region 會收。
- Replica 本身可以設定為 Multi-AZ，讓它在升格後也具備高可用。
- **應用程式要自己決定把哪些查詢送到 replica**。RDS 不會自動把 SELECT 導到 replica；多個 replica 時，可以用 Route 53 加權記錄或應用程式的連線池分散。

### Promote：把 replica 變成獨立資料庫

Read replica 可以被 **promote（升格）** 成一個獨立、可寫的 DB instance。升格後它和原本的 primary **斷開複寫關係**，再也不會同步。這個功能有三種常見用途：

1. **跨 Region 災難復原**：主 Region 失效時，把另一個 Region 的 replica 升格成新的 primary。因為是非同步複寫，RPO 等於當時的 replication lag；而且升格與修改應用程式連線都需要操作，RTO 通常是分鐘級。
2. **分拆資料庫**：把某個功能的資料移到獨立資料庫。
3. **重大變更前的預演**。

下面兩個指令分別建立跨 Region read replica（在目的 Region 執行），以及在災難時把它升格：

```bash
aws rds create-db-instance-read-replica \
  --region ap-southeast-1 \
  --db-instance-identifier orders-replica-sg \
  --source-db-instance-identifier arn:aws:rds:ap-northeast-1:111122223333:db:orders-db


aws rds promote-read-replica --region ap-southeast-1 \
  --db-instance-identifier orders-replica-sg
```

### Multi-AZ 與 read replica 放在一起比

| 比較 | Multi-AZ（DB instance） | Read replica |
|---|---|---|
| 主要目的 | 高可用、AZ 故障自動切換 | 讀取擴展、跨 Region 讀取或 DR |
| 複寫 | 同步 | 非同步（有 lag） |
| 能否服務讀取 | 否 | 是，使用自己的 endpoint |
| 範圍 | 同一 Region 的另一個 AZ | 同 AZ、跨 AZ、跨 Region |
| 切換方式 | 自動 failover，endpoint 不變 | 手動 promote，endpoint 不同 |
| 資料遺失 | 已 commit 的交易不遺失 | 可能遺失 lag 期間的資料 |

到這裡，Wanderly 的資料庫能撐過 AZ 故障，讀取也分出去了。但三個月後，一個錯誤的 migration script 把一張表的價格全部改成 0。Multi-AZ 與 read replica 都在一秒內忠實地複製了這個錯誤，這時能救命的只有備份。

## 26.5 備份與還原：處理「資料被改壞」

### Automated backups 與 PITR

RDS 的 **automated backups（自動備份）** 由兩部分組成：

1. 每天在 **backup window** 內做一次儲存層的 snapshot（第一次是完整的，之後是增量）。
2. 持續保存資料庫的 **transaction log**（交易紀錄），大約每 5 分鐘上傳一次到 S3。

有了「某天的 snapshot」加上「之後所有交易紀錄」，RDS 就能把資料庫還原到 retention 期間內任意一秒，這叫 **PITR（Point-in-Time Recovery，時間點還原）**。可還原的最新時間點通常在最近 5 分鐘內。

- Retention 可設為 1–35 天；設為 0 等於關閉自動備份（也就無法建立 read replica）。
- **PITR 一定會建立一個新的 DB instance**，有新的 endpoint。它不會覆蓋原本的資料庫。還原後，你要驗證資料，再把應用程式的連線改到新 endpoint（或把新舊 instance 改名對調）。
- 刪除 DB instance 時，automated backups 預設會一起刪除（可選擇保留），所以刪除前通常會要求建立 **final snapshot**。

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier orders-db \
  --target-db-instance-identifier orders-db-0314-1359 \
  --restore-time 2026-03-14T05:59:00Z \
  --db-subnet-group-name wanderly-data \
  --vpc-security-group-ids sg-0db1234567890abcd
```

### Manual snapshot

**Manual snapshot（手動快照）** 是你主動建立的備份，**會一直保留直到你刪除**，不受 retention 限制，也不會因為 DB instance 被刪除而消失。用途：

- 長期保存（例如法規要求保留月結資料七年）。
- **複製到其他 Region**（copy snapshot），作為跨 Region DR。
- **分享給其他 AWS 帳號**，例如給隔離的備份帳號或稽核帳號（加密 snapshot 的分享條件見 26.6 節）。

除了 manual snapshot，RDS 也支援 **cross-Region automated backup replication**：把 automated backups（snapshot 與交易紀錄）持續複製到另一個 Region，在那個 Region 也能做 PITR。若要集中管理多個帳號、多種服務的備份政策，可以用 **AWS Backup**（第 34 章）。

> [!tip] 考試提示：選對還原手段
> - 「還原到 10 分鐘前、retention 內的任意時間點」→ PITR（建立新 instance）。
> - 「保存超過 35 天」→ manual snapshot 或 AWS Backup。
> - 「另一個 Region 也要能還原」→ snapshot copy 或 cross-Region automated backup replication。
> - Aurora MySQL 「原地倒帶幾分鐘、不想建新 cluster」→ Backtrack（26.11 節）。

### 防止誤刪

**Deletion protection** 開啟後，任何人（包括有權限的管理員）都無法刪除該 DB instance，必須先修改設定關閉它。在 CloudFormation 中，另外可以用 `DeletionPolicy: Snapshot`，讓堆疊刪除或資源被取代時先留下 snapshot。這兩層保護在 production 都應開啟。

```yaml
OrdersDb:
  Type: AWS::RDS::DBInstance
  DeletionPolicy: Snapshot
  UpdateReplacePolicy: Snapshot
  Properties:
    Engine: mysql
    DBInstanceClass: db.r7g.large
    AllocatedStorage: 200
    MaxAllocatedStorage: 1000      # 開啟 storage autoscaling 的上限
    StorageType: gp3
    MultiAZ: true
    BackupRetentionPeriod: 14
    StorageEncrypted: true
    KmsKeyId: !Ref DatabaseKey     # customer managed key，第 15 章
    DeletionProtection: true
    PubliclyAccessible: false
    DBSubnetGroupName: !Ref DataSubnetGroup
    VPCSecurityGroups: [!Ref DbSecurityGroup]
    ManageMasterUserPassword: true # 主帳號密碼交給 Secrets Manager 管理
    MasterUsername: admin
```

## 26.6 安全：加密、連線與身份

資料庫的安全分成四層：網路（誰能連到 port）、傳輸加密（連線途中能否被竊聽）、靜態加密（磁碟與備份被拿走能否讀）、身份（用什麼證明自己是誰）。網路層在第 5、6 章已經處理：isolated subnet、不開 public access、security group 只允許 app tier。本節處理其他三層。

### 靜態加密：只能在建立時決定

RDS 用 KMS key（第 15 章）加密儲存。開啟後，**底層儲存、automated backups、snapshot、read replica 與日誌都會被加密**，對應用程式完全透明，效能影響極小。必須記住的規則：

1. **加密只能在建立 DB instance 時啟用**。已經存在的未加密 instance 無法直接改成加密，也無法關閉已啟用的加密。
2. 加密 instance 的 read replica 必須也是加密的；未加密 instance 不能建立加密的 read replica。跨 Region replica 要使用目的 Region 的 KMS key。
3. 既有的未加密資料庫要加密，只能另外建立一個加密的新 instance，流程如下。

三個步驟依序是：① 為未加密 instance 建立 snapshot；② 複製 snapshot 時指定 KMS key，複本就是加密的；③ 從加密 snapshot 還原成新的 instance，再切換應用程式。

```bash
aws rds create-db-snapshot --db-instance-identifier orders-db \
  --db-snapshot-identifier orders-plain-snap

aws rds copy-db-snapshot --source-db-snapshot-identifier orders-plain-snap \
  --target-db-snapshot-identifier orders-encrypted-snap \
  --kms-key-id alias/wanderly-rds

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier orders-db-enc \
  --db-snapshot-identifier orders-encrypted-snap
```

這個流程中，snapshot 之後的寫入不會進入新 instance。若不能接受停機期間的資料差異，就在切換前暫停寫入，或用 AWS DMS（第 45 章）持續同步差異直到切換。

### 加密 snapshot 跨帳號分享

用 **AWS managed key（`aws/rds`）** 加密的 snapshot **不能分享給其他帳號**，因為你無法修改 AWS managed key 的 key policy。要跨帳號分享，snapshot 必須是用 **customer managed key** 加密的，並且：

1. 在 key policy 中允許目標帳號使用這把 key（至少 `kms:Decrypt`、`kms:DescribeKey`、`kms:CreateGrant` 等）。
2. 把 manual snapshot 分享給目標帳號。
3. 目標帳號複製一份到自己帳號（最好再用自己的 key 重新加密），之後即使來源帳號撤銷分享，備份仍然存在。

如果現有 snapshot 是用 `aws/rds` 加密的，先用 copy snapshot 改用 customer managed key 加密，再分享。Automated backups 本身不能直接分享，要先複製成 manual snapshot。

### 傳輸加密

RDS 各引擎都支援 TLS 連線。要**強制**所有連線使用 TLS，在 parameter group 設定，例如 PostgreSQL 與 SQL Server 的 `rds.force_ssl = 1`、MySQL 的 `require_secure_transport = ON`。應用程式端要使用 AWS 提供的 CA 憑證驗證伺服器身份。

### 身份：不要把密碼寫在程式裡

傳統做法是建立資料庫帳號、把密碼放進設定檔。改善方式有兩種：

- **Secrets Manager 管理密碼**：RDS 可以直接讓 Secrets Manager 管理主帳號密碼（`ManageMasterUserPassword`），並自動輪替。應用程式啟動時從 Secrets Manager 取得密碼（第 15 章）。
- **IAM database authentication**：支援 MySQL、MariaDB、PostgreSQL 與對應的 Aurora。應用程式用自己的 IAM role 呼叫 API 產生一個 **authentication token**（有效 15 分鐘），拿它代替密碼登入，連線必須使用 TLS。資料庫裡仍要建立對應的使用者並設定為使用 IAM 驗證，IAM policy 則授予 `rds-db:connect`：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:ap-northeast-1:111122223333:dbuser:db-ABCDEFGHIJKL01234/orders_app"
    }
  ]
}
```

Resource 中的 `db-ABCDEFGHIJKL01234` 是 instance 的 **resource ID**（不是 instance 名稱），`orders_app` 是資料庫使用者名稱。IAM DB auth 的好處是沒有長期密碼、權限集中在 IAM 管理；限制是每秒新建連線數有建議上限，不適合每個請求都新建連線的高頻工作負載，這種情況通常搭配下一節的 RDS Proxy。

## 26.7 RDS Proxy：吸收連線風暴

### 為什麼需要

Wanderly 把訂單 API 改成 Lambda（第 19 章）。促銷開始的那一刻，Lambda 同時啟動了兩千個執行環境，每個都建立自己的 MySQL 連線。資料庫的 `max_connections` 很快用完，新連線被拒絕；就算沒用完，大量建立 TLS 連線與驗證的工作也吃掉了 CPU。問題不在 SQL 慢，而在**連線數太多、連線建立太頻繁**。

### 運作方式

**RDS Proxy** 是位於應用程式與資料庫之間的受管 **connection pool（連線池）**：

- 應用程式連到 Proxy 的 endpoint，Proxy 維持一組數量較少、長期存在的資料庫連線，把大量用戶端連線**多工（multiplex）** 到這些連線上：一個交易結束後，同一條資料庫連線就能給下一個用戶端的交易使用。
- Proxy 連到資料庫時，可以使用存放在 **Secrets Manager** 的帳密，或（支援的引擎上）使用 IAM database authentication；用戶端連到 Proxy 時可以使用帳密或 IAM 驗證，讓應用程式不必直接持有資料庫密碼。
- Failover 時，Proxy 會保持用戶端連線，自動改連到新的 primary，應用程式感受到的中斷比直接重新解析 DNS 短。
- Proxy 必須與資料庫位於同一個 VPC，只能從 VPC 內部存取，不能設為 public。
- 支援 RDS for MySQL、MariaDB、PostgreSQL、SQL Server 與 Aurora。

### Pinning：Proxy 失去效果的情況

如果某個 session 做了「會改變連線狀態」的事，例如設定 session 變數、建立暫存表、使用某些 prepared statement，Proxy 無法安全地把那條資料庫連線交給別人，只好把它**固定（pin）** 給這個用戶端直到連線結束。Pinning 太多，多工效果就消失了。CloudWatch 的 `DatabaseConnectionsCurrentlySessionPinned` 指標與 Proxy log 可以找出原因，解法是減少 session 層級的狀態、讓交易盡快結束。

> [!warning] 常見誤解
> RDS Proxy 不是快取，也不會讓慢查詢變快。它解決的是**連線數量與連線建立成本**。CPU 被慢 SQL 吃滿，要調 index、加 read replica 或 ElastiCache（第 28 章）。

## 26.8 Parameter groups、維護與監控

### Parameter group 與 option group

RDS 不讓你登入主機改設定檔，引擎設定改由 **parameter group（參數群組）** 管理，例如 `max_connections`、`innodb_buffer_pool_size`、`rds.force_ssl`。

- 每個引擎版本有一個 **default parameter group，不能修改**。要改設定，必須建立 **custom parameter group** 再套用到 instance。
- 參數分為 **dynamic（動態，立即生效）** 與 **static（靜態，需要 reboot 才生效）**。套用新的 parameter group 本身也需要 reboot。
- Aurora 有兩層：**DB cluster parameter group**（整個 cluster 共用，例如 binlog 設定）與 **DB parameter group**（個別 instance）。

**Option group（選項群組）** 用來啟用引擎的附加功能，例如 Oracle 的 TDE、SQL Server 的原生備份還原到 S3。

### 維護與升級

- **Maintenance window**：每週一段時間，AWS 在這段時間套用需要停機的修補。Multi-AZ 會先修補 standby、failover、再修補舊 primary，縮短中斷。
- **Minor version upgrade** 可設定自動套用；**major version upgrade**（例如 PostgreSQL 15 → 16）必須手動觸發，可能有相容性問題，建議用 26.12 節的 Blue/Green Deployments。

### 監控

- **CloudWatch metrics**：CPU、可用記憶體、可用儲存空間、`DatabaseConnections`、`ReadIOPS`、`ReplicaLag` 等，由 hypervisor 層收集。
- **Enhanced Monitoring**：由 instance 上的 agent 收集作業系統層級指標（每個 process 的 CPU、記憶體），最細可到 1 秒。
- **Performance Insights／CloudWatch Database Insights**：以「資料庫負載（average active sessions，平均活躍 session 數）」為核心，顯示哪些 SQL、哪些等待事件佔用資源，是找慢查詢最快的工具。AWS 已把這項功能整併到 **CloudWatch Database Insights**（底層 API 仍叫 Performance Insights），舊教材與考題多半沿用 Performance Insights 這個名稱，兩者指的是同一類功能。
- **RDS events** 可以透過 EventBridge 或 SNS 通知 failover、備份失敗等事件。

到這裡，RDS 已能滿足 Wanderly 的大部分需求。但隨著業務成長，團隊開始遇到 RDS 架構本身的限制：read replica 有明顯 lag、failover 要一兩分鐘、儲存要預先配置。這些限制都來自同一個設計：每台 instance 都有自己的一份資料。Aurora 改變的正是這一點。

## 26.9 Aurora 架構：把儲存層拆出來

### 傳統資料庫的瓶頸

在 RDS for MySQL 中，primary、standby、每個 replica 都各自擁有完整的磁碟與資料。複寫就是把變更一份一份送過去，每多一個副本，就多一份要傳送、要套用的工作。Replica 落後、failover 慢、加 replica 要複製整個資料庫，都源自這個「每台機器一份資料」的設計。

### Aurora 怎麼做

**Amazon Aurora** 相容 MySQL 與 PostgreSQL（應用程式和驅動程式大多不用改），但把**運算（DB instance）與儲存（cluster volume）分開**：

```text
                        應用程式
              ┌────────────┴─────────────────┐
     寫入 ① cluster endpoint          讀取 ② reader endpoint
              │                         ┌────┴─────┐
              ▼                         ▼          ▼
       ┌─────────────┐          ┌──────────┐ ┌──────────┐
       │ Writer      │          │ Replica 1│ │ Replica 2│  ③ 最多 15 個
       │ （AZ-a）    │          │ （AZ-c） │ │ （AZ-d） │     Aurora Replicas
       └──────┬──────┘          └────┬─────┘ └────┬─────┘
              │ ④ 只寫 redo log      │ 從同一份儲存讀取
  ════════════▼══════════════════════▼════════════▼═══════════════
   Cluster volume（共享、分散式、自動成長）
     AZ-a: [副本1][副本2]   AZ-c: [副本3][副本4]   AZ-d: [副本5][副本6]
     ⑤ 每 10 GB 一個 segment，6 份副本跨 3 AZ
     寫入需 4/6 確認，讀取需 3/6 確認
  ════════════════════════════════════════════════════════════════
```

① 所有寫入都送到 **cluster endpoint**（也叫 writer endpoint），它永遠指向目前的 writer。② 讀取送到 **reader endpoint**，它在連線層級把新連線分散到各個 replica。③ 一個 cluster 最多 15 個 **Aurora Replica**，它們和 writer **讀同一份儲存**，不需要各自複製資料，所以 replica lag 通常低於 100 毫秒，新增 replica 也很快。④ Writer 只把 redo log 送到儲存層，由儲存節點自己套用，網路傳輸量比傳統複寫少得多。⑤ **Cluster volume** 把資料切成 10 GB 的 segment，每個 segment 有 **6 份副本分布在 3 個 AZ**；寫入只要 6 份中的 4 份確認、讀取只要 3 份，所以失去一整個 AZ（2 份）仍可正常讀寫，壞掉的副本會自動從其他副本修復。

這個設計帶來幾個直接的結果：

- **儲存自動成長**：不用預先配置大小，按實際使用量計費，上限為 128 TiB（較新的 Aurora MySQL 3.10+ 與 Aurora PostgreSQL 版本提高到 256 TiB）。
- **耐久性不依賴 replica**：就算 cluster 只有一台 writer、沒有任何 replica，資料仍有 6 份跨 3 AZ。但沒有 replica 時，writer 故障後 Aurora 要重新建立一台 instance，恢復時間明顯較長。
- **備份是連續的**：Aurora 持續把資料備份到 S3，不影響效能，retention 1–35 天，可做 PITR。

### Aurora 的 failover

Writer 故障時，Aurora 把其中一個 replica 升為新 writer，cluster endpoint 改指向它。哪一台優先由 **failover priority tier（0–15，數字越小越優先）** 決定；同一個 tier 時選規格最大的。因為 replica 已經在讀同一份儲存，不需要「追上」資料，failover 通常比 RDS Multi-AZ DB instance 快很多。

所以在 Aurora 裡，**「Multi-AZ」的意思就是「在另一個 AZ 至少放一個 Aurora Replica」**。Aurora Replica 同時扮演 RDS 的 standby（failover 目標）與 read replica（分擔讀取）兩種角色，這是 Aurora 與 RDS 最重要的差異。

### 四種 endpoint

| Endpoint | 指向 | 用途 |
|---|---|---|
| Cluster（writer）endpoint | 目前的 writer | 所有寫入與需要 read-after-write 的讀取 |
| Reader endpoint | 所有 replica（連線層級負載分散） | 一般唯讀查詢 |
| Custom endpoint | 你指定的一組 instance | 把報表查詢導到幾台大規格 replica，與線上讀取隔離 |
| Instance endpoint | 單一 instance | 診斷、特殊調校，一般應用不建議依賴 |

> [!example] 例子：用 custom endpoint 隔離報表
> Wanderly 的 Aurora cluster 有 1 台 writer 與 4 台 replica。財務部門的月結報表會跑長時間的大型查詢，曾經拖慢使用者的搜尋。小林把其中 2 台 replica 換成較大的規格，建立一個名為 `analytics` 的 custom endpoint 只包含這 2 台；另一個 `app-read` custom endpoint 包含其他 2 台。報表與線上流量從此互不干擾。

### 儲存設定：Standard 與 I/O-Optimized

Aurora 的費用由 instance、儲存容量與 I/O 組成。**Aurora Standard** 依 I/O 次數另外收費；**Aurora I/O-Optimized** 不收 I/O 費用，但 instance 與儲存單價較高。AWS 的建議是：當 I/O 費用超過 Aurora 總費用約 25% 時，I/O-Optimized 通常比較划算。這是考試中「Aurora 帳單裡 I/O 費用很高」的標準答案。

## 26.10 Aurora Serverless v2：容量跟著負載走

Wanderly 的內部後台、測試環境與一些新功能，流量很難預測：白天偶爾有人用，晚上幾乎沒有，月底又突然很高。為它們配置固定大小的 instance，不是平常浪費就是尖峰不夠。

**Aurora Serverless v2** 讓 instance 的容量自動伸縮。容量單位是 **ACU（Aurora Capacity Unit）**，每個 ACU 約等於 2 GiB 記憶體與對應的 CPU、網路能力。你設定最小與最大 ACU，Aurora 依負載以 0.5 ACU 為單位在幾秒內調整，按每秒使用的 ACU 計費。

- 它是 cluster 裡的一種 **instance class（`db.serverless`）**，可以和一般 provisioned instance 混用。例如 writer 用 provisioned、replica 用 Serverless v2 應付讀取尖峰，或反過來。
- 支援 Multi-AZ、read replica、Global Database 等 Aurora 功能。
- 較新的引擎版本支援把最小容量設為 **0 ACU**，閒置一段時間後**自動暫停（auto-pause）**，暫停期間不收運算費，下次連線時恢復（恢復需要幾秒，第一個連線會等待）。這很適合開發與測試環境，不適合需要穩定低延遲的 production。
- 尖峰時容量放大需要一點時間；如果平時就要接住突然的大流量，最小 ACU 不要設太低，因為容量越小、可用的 buffer pool 越小，冷啟動的查詢會比較慢。

> [!note] Serverless v1 的現況
> 舊版 Aurora Serverless v1 以「暫停後冷啟動」聞名，AWS 已結束對它的支援，並要求升級到 v2。看到舊資料說「Aurora Serverless 不能有 read replica、不能 Multi-AZ」，那是 v1 的限制，不適用於 v2。

## 26.11 Aurora 進階：Global Database、Backtrack 與 Cloning

### Global Database：跨 Region 的秒級複寫

Wanderly 開始服務東南亞與日本的使用者，也被要求「東京 Region 完全失效時，在新加坡 Region 一分鐘內恢復服務、資料遺失以秒計」。Cross-Region read replica 用的是引擎層的非同步複寫，lag 可能更長，升格也是手動流程。Aurora 提供更好的選擇：

**Aurora Global Database** 由一個 **primary Region**（唯一可寫入）與一個或多個 **secondary Region**（唯讀）組成：

- 複寫在**儲存層**進行，由專用的基礎設施把資料送到 secondary Region 的 cluster volume，不消耗 writer 的資源。典型 lag 小於 1 秒，所以 **RPO 通常是秒級**。
- 每個 secondary Region 可以有自己的 Aurora Replicas 服務當地讀取，讓各地使用者讀到低延遲的資料。Secondary Region 可以設計成只有儲存、沒有 instance（headless），平時更省錢，但切換時要先建 instance。
- 一個 Global Database 最多可以有 10 個 secondary Region（早期上限是 5 個，舊教材與舊題目可能仍寫 5）。
- **Write forwarding（寫入轉送）**：secondary Region 的應用程式可以把少量寫入送到本地 cluster，由 Aurora 轉送到 primary 執行。這省去應用程式自己判斷寫入要送哪個 Region，但寫入延遲仍包含跨 Region 往返，不適合大量寫入。

跨 Region 切換分兩種：

| 操作 | 時機 | 資料遺失 | 說明 |
|---|---|---|---|
| **Switchover**（計畫性） | 演練、Region 輪替、維護 | 不遺失（RPO 0） | 等 secondary 完全同步後交換角色，複寫拓撲保留 |
| **Failover**（非計畫性） | Primary Region 真的失效 | 可能遺失尚未複寫的秒級資料 | 把 secondary 升為新 primary，RTO 通常一分鐘級；舊 primary 恢復後可重新加入 |

切換後，應用程式要連到新 primary 的 writer endpoint。Aurora 提供 global 層級的 writer endpoint，或你可以用 Route 53（第 9 章）把應用程式導向正確的 Region。

### Backtrack：原地倒帶

**Backtrack** 只支援 **Aurora MySQL**。開啟後，Aurora 保留一段時間的變更紀錄（target backtrack window 最多 72 小時），讓你把**整個 cluster 原地倒回**過去某個時間點：

- 不建立新 cluster，endpoint 不變，通常幾分鐘內完成。
- 倒帶期間 cluster 會短暫中斷連線。
- 倒帶是整個 cluster 一起，不能只倒一張表。
- 可以多次前後移動，找到正確時間點。
- 需要在建立 cluster（或從 snapshot 還原、clone）時啟用，有額外的變更紀錄儲存費。
- Aurora Global Database 不支援 Backtrack；跨 Region 的 cluster 要回復人為錯誤，改用 PITR。

### Cloning：幾分鐘內複製一個資料庫

測試團隊想用 production 的資料測試一個新版的房價計算。傳統做法是 restore snapshot，要等資料完整複製，而且會多付一整份儲存費。**Aurora cloning** 使用 **copy-on-write（寫入時複製）**：clone 一開始和來源共用同一份儲存頁面，只有任何一邊修改了某一頁，才會為那一頁建立新的副本。

- 建立快，通常幾分鐘，與資料庫大小幾乎無關。
- 初始幾乎不佔額外儲存，只為後來變更的頁面付費。
- Clone 和來源互不影響：在 clone 上做破壞性測試不會改動 production。
- 可以透過 AWS RAM 分享給其他帳號建立 clone。

```bash
aws rds restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier wanderly-prod \
  --db-cluster-identifier wanderly-pricing-test \
  --restore-type copy-on-write \
  --use-latest-restorable-time

aws rds create-db-instance --db-cluster-identifier wanderly-pricing-test \
  --db-instance-identifier wanderly-pricing-test-1 \
  --db-instance-class db.r7g.large --engine aurora-mysql
```

第一個指令只建立 clone 的 cluster volume，要再用第二個指令為它加上一台 instance 才能連線。

### 還原方式總整理

| 需求 | 選擇 | 會不會建立新資料庫 | 適用 |
|---|---|---|---|
| 回到 retention 內任一秒 | PITR | 會 | RDS、Aurora |
| 幾分鐘內原地倒回 | Backtrack | 不會 | 只有 Aurora MySQL |
| 長期保存、跨帳號、跨 Region | Manual snapshot（copy／share） | 還原時會 | RDS、Aurora |
| 快速建立測試用副本 | Cloning | 會（共用儲存） | Aurora |
| Region 失效 | Global Database failover／cross-Region replica promote | 升格既有副本 | Aurora／RDS |

## 26.12 Blue/Green Deployments：安全地做大改變

Wanderly 要把 PostgreSQL 從 14 升級到 16。原地 major version upgrade 有兩個風險：升級期間資料庫停機，而且一旦升級後發現相容性問題，很難退回。

**RDS Blue/Green Deployments** 的做法是：

1. 以目前的 production（**blue**）為來源，建立一個完整的 **green** 環境，並用複寫持續同步 blue 的變更。
2. 在 green 上做你要的改變：major version upgrade、修改 parameter group、調整 schema（需與複寫相容）、更換 instance class。Green 預設是唯讀的，避免被誤寫導致不一致。
3. 測試 green。期間 production 流量仍在 blue 上。
4. 執行 **switchover**：RDS 先檢查 guardrails（例如複寫 lag 是否夠小），暫停寫入、等 green 追上，再把 **green 改成 blue 原本的名稱與 endpoint**。應用程式不用修改連線設定，中斷時間通常在一分鐘以內。
5. 舊的 blue 環境保留下來（改名），確認沒問題後再刪除。

它支援 RDS for MySQL、MariaDB、PostgreSQL，以及 Aurora MySQL、Aurora PostgreSQL。考題看到「major version upgrade、最少停機、可在切換前完整測試」，答案就是 Blue/Green Deployments。

## 26.13 比較與選型

### RDS、Aurora、RDS Custom、EC2 自建

| 比較 | RDS（MySQL／PG 等） | Aurora | RDS Custom | EC2 自建 |
|---|---|---|---|---|
| 引擎 | 6 種引擎 | MySQL／PostgreSQL 相容 | Oracle、SQL Server | 任何 |
| OS 存取 | 無 | 無 | 有 | 完全控制 |
| 儲存 | 預先配置，可自動加大 | 共享 cluster volume，自動成長 | 預先配置 | 自己管理 EBS |
| 讀取擴展 | Read replica（非同步，lag 較大） | 最多 15 個 replica，共用儲存，lag 低 | 依引擎 | 自己架設 |
| Failover | Multi-AZ，通常 1–2 分鐘（cluster 部署更快） | Replica 升格，通常更快 | 依設定 | 自己做 |
| 跨 Region | Cross-Region read replica | Global Database（儲存層秒級） | 依引擎 | 自己做 |
| 營運負擔 | 低 | 最低 | 中 | 最高 |
| 典型選擇理由 | 需要特定引擎、成本敏感、標準工作負載 | 高讀取、快速 failover、跨 Region、彈性容量 | 需要 OS 或特權存取的商用引擎 | 不支援的版本或功能、完全掌控 |

### 選型流程

```text
需要關聯式資料庫（交易、JOIN、schema）
├─ 需要作業系統或資料庫特權存取？
│   ├─ 是，引擎是 Oracle／SQL Server → RDS Custom
│   └─ 是，其他需求或 RDS 不支援的版本 → EC2 自建
└─ 否 → 引擎是 MySQL／PostgreSQL？
     ├─ 否（Oracle／SQL Server／Db2／MariaDB）→ RDS（Multi-AZ + read replica）
     └─ 是 → 需要以下任一？
          │   大量讀取擴展、秒級 failover、跨 Region 秒級 RPO、
          │   無法預測的容量、快速 clone
          ├─ 是 → Aurora（容量難預測再加 Serverless v2）
          └─ 否、而且成本優先 → RDS（Multi-AZ；要可讀 standby 用 Multi-AZ DB cluster）
```

不需要關聯式模型、存取模式固定且要求近乎無限擴展的工作負載（例如購物車、session），考慮第 27 章的 DynamoDB；分析型查詢則交給第 30 章的 Redshift。

## 26.14 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| AZ 故障自動切換、同步複寫、不遺失已 commit 資料 | RDS Multi-AZ |
| 報表或讀取拖慢主資料庫、可接受稍舊資料 | Read replica（或 Aurora Replica + reader endpoint） |
| 需要「可讀的 standby」且 failover 更快（MySQL／PG） | Multi-AZ DB cluster |
| Lambda 大量連線、`too many connections` | RDS Proxy |
| 既有未加密資料庫要加密 | Snapshot → copy 時加密 → restore 新 instance |
| 加密 snapshot 分享給另一個帳號失敗 | 改用 customer managed key 並更新 key policy |
| 應用程式不要存資料庫密碼、用 IAM role | IAM database authentication（15 分鐘 token） |
| 誤刪資料，回到某個時間點 | PITR（建立新 instance） |
| Aurora MySQL 誤操作，幾分鐘內原地復原 | Backtrack |
| 快速、低成本複製 production 資料庫做測試 | Aurora cloning |
| 跨 Region DR，RPO 秒級、RTO 約一分鐘 | Aurora Global Database |
| 負載難預測、間歇使用、不想管容量 | Aurora Serverless v2 |
| Aurora 帳單 I/O 費用占比很高 | Aurora I/O-Optimized |
| Major version upgrade、最少停機、可先測試 | Blue/Green Deployments |
| 需要在資料庫主機安裝 agent（SQL Server／Oracle） | RDS Custom |
| 資料要保存超過 35 天 | Manual snapshot 或 AWS Backup |

**常見陷阱**：

1. 以為 Multi-AZ 的 standby 能分擔讀取。傳統 Multi-AZ DB instance 的 standby 完全不服務流量。
2. 以為 read replica 會自動 failover。RDS read replica 要手動 promote，而且有 lag，不是零 RPO 的高可用方案。
3. 以為可以「修改設定」直接加密既有 instance，或修改 parameter group 開啟靜態加密。只能透過 snapshot copy 與 restore。
4. 以為 PITR 會原地還原。RDS 與 Aurora 的 PITR 都建立新的資料庫，應用程式要改連線；只有 Aurora MySQL 的 Backtrack 是原地。
5. 以為 RDS Proxy 能解決慢查詢或 CPU 不足。它只處理連線。
6. 把 Backtrack 用在 Aurora PostgreSQL 或 RDS for MySQL。Backtrack 只屬於 Aurora MySQL。
7. 在 Aurora 題目裡選「另外開啟 Multi-AZ standby」。Aurora 的高可用就是在其他 AZ 放 Aurora Replica。

## 26.15 SAP 加深：跨 Region、跨帳號與遷移

### 依 RPO／RTO 選跨 Region DR 方案

SAP 題目常給一組 RPO／RTO 與成本限制，要你挑「剛好滿足、最便宜」的方案（DR 策略的完整分類見第 34 章）：

| 方案 | 典型 RPO | 典型 RTO | 成本 | 適用 |
|---|---|---|---|---|
| Snapshot 定期 copy 到另一 Region | 數小時（依頻率） | 數小時（restore 時間） | 最低 | Backup & restore 等級 |
| Cross-Region automated backup replication | 分鐘級（交易紀錄持續複製） | 數十分鐘到數小時（restore） | 低 | 需要 PITR 的低成本 DR |
| Cross-Region read replica | 秒到分鐘（lag） | 分鐘級（promote + 切換） | 中（要跑一台 instance） | Pilot light／warm standby |
| Aurora Global Database | 通常秒級 | 通常一分鐘級 | 較高 | 關鍵交易系統 |

注意「剛好滿足」：RPO 4 小時、RTO 8 小時、要求最低成本時，選 Global Database 是過度設計。

### 多帳號備份隔離

為了防範勒索軟體或帳號被入侵，企業常把備份複製到**另一個帳號**（通常在獨立的 OU，由第 14 章的 SCP 禁止刪除）。標準做法是 AWS Backup 跨帳號複製，或手動把用 customer managed key 加密的 snapshot 分享出去，由備份帳號用自己的 key 重新加密保存。重點是：來源帳號整個被刪除或被入侵，備份帳號裡的副本仍然可用。

### 從商用資料庫遷移

- **Oracle → Aurora PostgreSQL**：用 AWS SCT（Schema Conversion Tool）或 DMS Schema Conversion 轉換 schema 與 PL/SQL，再用 DMS 搬資料並持續同步（第 45 章）。常見動機是擺脫授權費用。
- **SQL Server → Aurora PostgreSQL**：**Babelfish for Aurora PostgreSQL** 讓 Aurora PostgreSQL 理解 SQL Server 的 T-SQL 與 TDS 連線協定，應用程式可以先用原本的 SQL Server 驅動程式連線，減少初期改寫量，再逐步現代化。
- **授權**：RDS for Oracle 與 SQL Server 有 License Included 與 BYOL 選擇；若授權條款要求專屬硬體或需要 OS 層控制，則評估 RDS Custom 或 EC2 Dedicated Hosts（第 17 章）。

### 成本與規模

- 穩定運行的 production instance 購買 **RDS Reserved Instances**（1 或 3 年承諾）取得折扣；Aurora 的 provisioned instance 同樣適用。
- 改用 Graviton instance class（`g` 結尾）通常有更好的性價比。
- 讀多寫少的工作負載，與其把 writer 不斷放大，不如加 replica 或在前面加 ElastiCache（第 28 章）。
- 需要即時把交易資料送到 Redshift 分析時，Aurora 與部分 RDS 引擎支援 **zero-ETL integration**，不必自建 ETL 管線（第 30 章）。

> [!sap] SAP 加深：多 Region 都要寫入
> Aurora Global Database 只有一個 primary Region 可寫；write forwarding 只是轉送，寫入仍在 primary 執行。若需求是「多個 Region 都要低延遲寫入」，關聯式方案可評估 **Aurora DSQL**（AWS 較新的 serverless 分散式 SQL 服務，multi-Region 叢集的各 Region endpoint 都可讀寫並維持強一致，但 PostgreSQL 相容程度與功能需要逐項驗證）；若資料模型可以改成 key-value，則是第 27 章的 DynamoDB global tables。

## 本章重點整理

- RDS 受管的是硬體、OS、引擎修補、備份與 failover；schema、index、SQL 調校與應用程式重連仍是你的責任，而且標準 RDS 沒有 OS 存取（需要時用 RDS Custom 或 EC2）。
- Multi-AZ DB instance 是一主一備、同步複寫，standby 不可讀，failover 透過 DNS 切換 endpoint，通常 60–120 秒，應用程式要能重連且不可快取 DNS 太久。
- Multi-AZ DB cluster（MySQL／PostgreSQL）是一寫兩讀、分布三個 AZ、reader 可讀、failover 通常在 35 秒內。
- Read replica 以非同步複寫擴展讀取，有 lag；可跨 Region，可 promote 成獨立資料庫但會斷開複寫，source 必須開啟 automated backups。
- Multi-AZ 與 read replica 都會忠實複製錯誤；人為錯誤要靠 PITR、snapshot 或 Backtrack。
- Automated backups 保留 1–35 天並支援 PITR；PITR 一定建立新 instance；manual snapshot 保留到你刪除，可跨 Region copy、跨帳號 share。
- 靜態加密只能在建立時啟用；既有未加密資料庫要用「snapshot → 加密 copy → restore」；用 `aws/rds` 加密的 snapshot 不能跨帳號分享。
- RDS Proxy 是受管連線池，解決 Lambda 等大量短連線造成的連線耗盡，並縮短 failover 影響；它不加速 SQL，pinning 會降低效果。
- IAM DB authentication 用 15 分鐘有效的 token 代替密碼；Secrets Manager 可管理並自動輪替主帳號密碼。
- Aurora 把運算與儲存分離：cluster volume 每 10 GB segment 有 6 份副本跨 3 AZ，寫入 4/6、讀取 3/6，自動成長。
- Aurora 最多 15 個 replica，共用儲存、lag 通常低於 100 毫秒，同時是 failover 目標；用 cluster、reader、custom endpoint 分流。
- Aurora Serverless v2 以 ACU 自動伸縮，可與 provisioned instance 混用，新版本可降到 0 ACU 自動暫停；Serverless v1 已結束支援。
- Aurora Global Database 以儲存層複寫到其他 Region，RPO 通常秒級；switchover 不遺失資料，failover 可能遺失秒級資料。
- Backtrack 只支援 Aurora MySQL、原地倒帶最多 72 小時；cloning 用 copy-on-write 快速建立測試副本。
- Blue/Green Deployments 讓 major version upgrade 與重大變更先在同步中的 green 環境測試，switchover 後沿用原 endpoint，中斷通常在一分鐘內。

## 本章練習題

### 練習 26-1｜SAA｜單選｜高可用與讀取分流

Wanderly 的訂單資料庫是 RDS for MySQL，已啟用 Multi-AZ DB instance deployment。財務部門每天下午跑大型報表查詢，期間結帳 API 的延遲明顯上升。報表可以接受幾分鐘前的資料，公司也要求保留 AZ 故障時的自動 failover。

哪個做法最合適？

- A. 把報表查詢改連到 Multi-AZ standby，讓 standby 分擔讀取
- B. 保留 Multi-AZ，另外建立一個 read replica，讓報表查詢連到 replica 的 endpoint
- C. 關閉 Multi-AZ，把省下的費用用來把 primary 升級到更大的 instance class
- D. 建立 RDS Proxy，讓報表查詢透過 Proxy 連線以降低 primary 負載

> [!answer]- 答案：B
> **A ✗** Multi-AZ DB instance 的 standby 不能讀也不能寫，沒有可供查詢的 endpoint，它只等待 failover。
>
> **B ✓** Read replica 以非同步複寫取得資料，有自己的 endpoint，適合可接受稍舊資料的報表；primary 的 Multi-AZ 保持不變，可用性需求也得到滿足。
>
> **C ✗** 加大 instance 可能暫時緩解負載，但關閉 Multi-AZ 就失去 AZ 故障的自動 failover，違反需求。
>
> **D ✗** RDS Proxy 管理連線數量與重用，不會減少查詢本身消耗的 CPU 與 I/O；報表仍在 primary 上執行。若問題是連線耗盡，Proxy 才是答案。
>
> **考點**：SAA-2.2、SAA-3.3｜Multi-AZ 負責可用性，read replica 負責讀取擴展

### 練習 26-2｜SAA｜單選｜加密既有資料庫

稽核發現 Wanderly 一個早期建立的 RDS for PostgreSQL instance 沒有啟用靜態加密。公司規定所有資料庫必須以公司管理的 KMS key 加密，可以安排一段短暫的維護停機。

應如何完成？

- A. 修改 DB instance，勾選啟用加密並指定 KMS key，於下次 maintenance window 套用
- B. 在 parameter group 設定 `rds.force_ssl = 1`，重新啟動 instance
- C. 建立一個加密的 read replica，再把 replica promote 成新的 primary
- D. 為 instance 建立 snapshot，複製 snapshot 時指定 customer managed KMS key，再從加密的 snapshot 還原新 instance 並切換應用程式

> [!answer]- 答案：D
> **A ✗** RDS 的靜態加密只能在建立時啟用，無法修改既有 instance 開啟加密。
>
> **B ✗** `rds.force_ssl` 強制傳輸加密（TLS），與儲存的靜態加密無關。
>
> **C ✗** 未加密的 instance 不能建立加密的 read replica；replica 的加密狀態必須和來源一致。
>
> **D ✓** Snapshot copy 可以指定 KMS key，產生加密的副本，從它還原的新 instance 就是加密的。這是官方的標準流程；切換前需處理 snapshot 之後的寫入（停機或用 DMS 同步）。
>
> **考點**：SAA-1.3｜RDS 加密只能建立時啟用，透過 snapshot copy 轉換

### 練習 26-3｜SAA｜單選｜Lambda 連線耗盡

Wanderly 的優惠券 API 使用 API Gateway 與 Lambda，後端是 Aurora MySQL。限時活動開始時，Lambda 同時執行數千個環境，資料庫出現 `Too many connections` 錯誤，CPU 主要耗在建立連線。SQL 本身都是簡單的主鍵查詢。

哪個做法最能以最少的程式修改解決問題？

- A. 在 Lambda 與 Aurora 之間建立 RDS Proxy，讓 Lambda 連到 Proxy endpoint
- B. 為 Aurora 新增三個 Aurora Replica，並把所有 Lambda 改連 reader endpoint
- C. 提高 Lambda 的 reserved concurrency，讓更多請求能同時完成
- D. 把 Aurora writer 升級到兩倍大的 instance class，以提高 `max_connections`

> [!answer]- 答案：A
> **A ✓** RDS Proxy 維持一組長期的資料庫連線，把大量 Lambda 的短連線多工到這些連線上，減少連線數與建立連線的成本，應用程式只需更換 endpoint。
>
> **B ✗** 優惠券 API 需要寫入，不能全部改連唯讀的 reader endpoint；而且每個 Lambda 仍各自建立連線，問題只是分散到更多 instance。
>
> **C ✗** 提高 concurrency 只會讓同時連線數更多，加劇問題。
>
> **D ✗** 加大 instance 能提高連線上限，但成本高，且連線建立的開銷依然存在；Lambda 擴展速度很快，可能再次觸頂。
>
> **考點**：SAA-3.3、SAA-2.1｜RDS Proxy 解決 serverless 連線風暴

### 練習 26-4｜SAA｜單選｜誤刪資料的還原

一名工程師在 14:07 對 RDS for MySQL 執行了錯誤的 `DELETE`，刪掉了當天的訂單明細。Automated backups 的 retention 是 7 天。團隊希望取回 14:05 時的資料，並盡量減少資料遺失。

應如何處理？

- A. 對 instance 執行 reboot with failover，讓 Multi-AZ standby 接手，standby 上還保有刪除前的資料
- B. 使用 Backtrack 把 instance 原地倒回 14:05
- C. 執行 point-in-time restore 到 14:05，建立一個新的 DB instance，驗證後把需要的資料補回或切換應用程式
- D. 從當天凌晨的 automated snapshot 還原到原本的 instance 上，覆蓋現有資料

> [!answer]- 答案：C
> **A ✗** Multi-AZ 是同步複寫，刪除在 standby 上也同時發生，failover 拿不回資料。
>
> **B ✗** Backtrack 只支援 Aurora MySQL，RDS for MySQL 沒有這個功能。
>
> **C ✓** PITR 結合每日 snapshot 與持續保存的交易紀錄，可以還原到 retention 內的任意一秒。它會建立新的 instance，團隊可以從中取回被刪的資料，或在驗證後切換應用程式。
>
> **D ✗** RDS 的還原一律建立新 instance，不會覆蓋原 instance；而且只用凌晨的 snapshot 會遺失凌晨到 14:05 的所有資料。
>
> **考點**：SAA-2.2｜PITR 建立新 instance，Multi-AZ 不防人為錯誤

### 練習 26-5｜SAA｜單選｜Aurora 讀取擴展

Wanderly 已遷移到 Aurora PostgreSQL，目前只有一台 writer。旅館搜尋功能的讀取量在旺季成長了五倍，寫入量變化不大。團隊希望讀取能水平擴展、replica lag 越低越好，並在 writer 故障時自動切換。

哪個做法最合適？

- A. 在另一個 Region 建立 cross-Region read replica，讓搜尋流量連到它
- B. 為 writer 開啟 RDS Multi-AZ DB instance deployment，並讓搜尋流量連到 standby
- C. 在不同 AZ 新增多個 Aurora Replica，讓搜尋流量使用 reader endpoint，並設定 failover priority tier
- D. 把 writer 改為 Aurora Serverless v2，並把最大 ACU 調到上限

> [!answer]- 答案：C
> **C ✓** Aurora Replica 與 writer 共用同一份 cluster volume，lag 通常低於 100 毫秒，最多 15 個；reader endpoint 在連線層級分散讀取。放在其他 AZ 的 replica 同時是 failover 目標，priority tier 決定升格順序。
>
> **A ✗** 跨 Region 的副本會增加延遲與資料傳輸費用，而且不是同 Region 的 failover 目標，不符合需求。
>
> **B ✗** Aurora 不使用 RDS 傳統的 standby；Aurora 的高可用就是在其他 AZ 放 Aurora Replica。而且傳統 standby 本來就不能讀。
>
> **D ✗** 讓 writer 自動放大可以接住部分流量，但所有讀取仍集中在單一 instance，沒有水平擴展，也沒有 failover 目標。
>
> **考點**：SAA-3.3、SAA-2.2｜Aurora Replica 與 reader endpoint

### 練習 26-6｜SAA｜選兩項｜Failover 後應用程式恢復太慢

Wanderly 演練 RDS Multi-AZ failover 時，RDS 在約 90 秒內完成切換，但部分 Java 應用程式持續報錯超過 20 分鐘，直到重新啟動才恢復。調查發現這些應用程式在設定檔中寫的是資料庫的 IP 位址，另一部分應用程式雖然使用 endpoint 名稱，但 JVM 會長期快取 DNS 解析結果。

哪兩個做法能縮短應用程式的恢復時間？（選兩項）

- A. 把設定檔中的 IP 改成 RDS endpoint 名稱，並調低 JVM 的 DNS 快取 TTL
- B. 把 standby 的 IP 也寫入設定檔，讓應用程式在 primary 失敗時改連 standby
- C. 改用 read replica endpoint 作為寫入端點，因為 replica 不會 failover
- D. 在應用程式與資料庫之間使用 RDS Proxy，讓 Proxy 處理 failover 後的重連
- E. 把 Multi-AZ 改為 Single-AZ，避免 failover 造成 IP 改變

> [!answer]- 答案：A、D
> **A ✓** RDS failover 是把 endpoint 的 DNS 記錄改指向新 primary。應用程式必須使用名稱，並讓 DNS 快取盡快過期，才能連到新的 primary。
>
> **B ✗** Standby 不接受連線，且 failover 後各 instance 的角色與 IP 都可能改變，寫死任何 IP 都會在下一次 failover 出問題。
>
> **C ✗** Read replica 是唯讀的，不能作為寫入端點。
>
> **D ✓** RDS Proxy 維持用戶端連線，failover 時自動連到新的 primary，應用程式不需要依賴 DNS 重新解析，中斷時間更短。
>
> **E ✗** Single-AZ 沒有自動 failover，AZ 故障時要長時間人工恢復，完全違背高可用目標。
>
> **考點**：SAA-2.2｜Multi-AZ failover 以 DNS 切換，應用程式需正確重連

### 練習 26-7｜SAA｜單選｜可讀的 standby

一家公司的 RDS for PostgreSQL 需要在 AZ 故障時更快地 failover（目標低於一分鐘），並且希望備援用的 instance 平時也能服務唯讀查詢，以充分利用付費的資源。公司暫時不打算改用 Aurora。

應選擇哪種部署？

- A. RDS Multi-AZ DB cluster deployment，一台 writer 與兩台可讀的 reader 分布在三個 AZ
- B. RDS Multi-AZ DB instance deployment，並讓唯讀查詢連到 standby
- C. Single-AZ instance 搭配兩個同 AZ 的 read replica
- D. Single-AZ instance 搭配每小時一次的 manual snapshot

> [!answer]- 答案：A
> **A ✓** Multi-AZ DB cluster 支援 MySQL 與 PostgreSQL，兩台 reader 可透過 reader endpoint 服務讀取，並以半同步複寫保護資料；failover 通常在 35 秒內完成。
>
> **B ✗** Multi-AZ DB instance 的 standby 不可讀，failover 通常需要 60–120 秒。
>
> **C ✗** Read replica 不會自動 failover，而且放在同一個 AZ 無法撐過 AZ 故障。
>
> **D ✗** Snapshot 是還原用的備份，不是運作中的資料庫；從 snapshot 還原需要的時間遠超過一分鐘。
>
> **考點**：SAA-2.2、SAA-3.3｜Multi-AZ DB cluster 與 DB instance 的差異

### 練習 26-8｜SAA｜單選｜Aurora MySQL 快速復原

Wanderly 在 Aurora MySQL cluster 上執行一個 schema migration，十分鐘後發現它錯誤地改寫了價格欄位。這個 cluster 建立時已啟用 Backtrack，target window 為 24 小時。團隊希望在最短時間內讓 production 回到 migration 前的狀態，且不想修改應用程式的連線設定。

應如何處理？

- A. 執行 PITR 到 migration 前的時間點，再把應用程式改連到新 cluster 的 endpoint
- B. 從最近的 manual snapshot 還原一個新 cluster，並更新 Route 53 記錄
- C. 建立 production 的 clone，在 clone 上修正價格後再把 clone 改名為 production
- D. 使用 Backtrack 把 cluster 原地倒回 migration 開始前的時間點

> [!answer]- 答案：D
> **A ✗** PITR 可行但會建立新 cluster，需要修改連線並等待還原完成，不是最快、也不符合「不修改連線設定」。
>
> **B ✗** Manual snapshot 可能比 migration 早很多，會遺失更多資料，也需要建立新 cluster 與修改 DNS。
>
> **C ✗** Clone 複製的是目前已被改壞的資料，無法自動回到 migration 之前。
>
> **D ✓** Backtrack 讓 Aurora MySQL cluster 在原地倒回 target window 內的時間點，endpoint 不變，通常幾分鐘內完成，正好符合需求。
>
> **考點**：SAA-2.2｜Aurora MySQL Backtrack 原地倒帶

### 練習 26-9｜SAA｜單選｜測試環境複製 production

Wanderly 的 Aurora PostgreSQL production 資料庫約 3 TB。QA 團隊每週需要一份 production 資料的完整副本，執行會修改資料的破壞性測試，測試結束就丟棄。團隊希望建立副本的速度快，且額外的儲存費用最低。

哪個做法最合適？

- A. 每週從 automated backup 執行 PITR，建立新的 cluster
- B. 每週建立 production 的 Aurora clone，並在測試結束後刪除
- C. 在 production cluster 新增一個 Aurora Replica 給 QA 使用
- D. 用 AWS DMS 每週把 production 完整複製到另一個 Aurora cluster

> [!answer]- 答案：B
> **A ✗** PITR 可以建立副本，但要等待資料完整還原，而且新 cluster 會擁有一整份獨立的儲存費用。
>
> **B ✓** Aurora cloning 使用 copy-on-write，建立快速且一開始與來源共用儲存，只有被修改的頁面才產生額外費用。Clone 上的破壞性測試不會影響 production。
>
> **C ✗** Aurora Replica 是唯讀的，無法執行會修改資料的測試；而且它和 production 共用 cluster volume。
>
> **D ✗** DMS 適合遷移與持續同步，每週完整複製 3 TB 費時、費用高，營運負擔也更大。
>
> **考點**：SAA-4.3、SAA-3.3｜Aurora cloning（copy-on-write）

### 練習 26-10｜SAA｜單選｜移除應用程式中的資料庫密碼

Wanderly 的 EC2 應用程式目前在設定檔中保存 RDS for MySQL 的帳號密碼。安全團隊要求：應用程式不得保存任何長期有效的資料庫密碼，存取權限要能透過 IAM 集中管理與撤銷，連線必須加密。應用程式每個 instance 只維持少量長連線。

最合適的做法是什麼？

- A. 把密碼存成 EC2 user data，啟動時寫入環境變數
- B. 把密碼放進 S3 bucket，並以 bucket policy 限制只有應用程式的 IAM role 能讀取
- C. 啟用 IAM database authentication，讓應用程式以 EC2 instance role 產生 authentication token，透過 TLS 登入
- D. 在 parameter group 中設定 `require_secure_transport = ON`，並保留現有密碼

> [!answer]- 答案：C
> **A ✗** User data 可以被有權限的人讀取，而且密碼仍是長期有效的，只是換了存放位置。
>
> **B ✗** 改善了存放位置，但密碼本身仍然長期有效，不符合「不保存長期密碼」。
>
> **C ✓** IAM DB authentication 讓應用程式用 IAM role 的身份產生 15 分鐘有效的 token 代替密碼，權限由 IAM policy 的 `rds-db:connect` 控制、可隨時撤銷，且要求 TLS 連線。少量長連線的情境也不會碰到新建連線速率的限制。
>
> **D ✗** 只解決了傳輸加密，沒有解決長期密碼的問題。
>
> **考點**：SAA-1.1、SAA-1.3｜IAM database authentication

### 練習 26-11｜SAP｜選兩項｜Aurora 成本最佳化

Wanderly 的帳單分析顯示兩個問題：production Aurora MySQL cluster 的 I/O 費用占了 Aurora 總費用約 40%，工作負載穩定且持續；另外有十幾個開發用 Aurora cluster，每個只在上班時間被零星使用，但一直以 provisioned instance 執行。團隊希望在不影響 production 效能的前提下降低成本。

哪兩個做法最合適？（選兩項）

- A. 把 production cluster 的儲存設定改為 Aurora I/O-Optimized
- B. 把 production cluster 的 Aurora Replica 全部刪除，只保留 writer
- C. 把開發 cluster 改用 Aurora Serverless v2，並在支援的版本上把最小容量設為 0 ACU 以啟用 auto-pause
- D. 把開發 cluster 改為 RDS Multi-AZ DB cluster
- E. 為 production cluster 啟用 Backtrack，以減少 automated backups 的儲存費用

> [!answer]- 答案：A、C
> **A ✓** I/O-Optimized 不收 I/O 費用，instance 與儲存單價較高；當 I/O 費用超過總費用約 25% 時通常更划算。40% 的穩定 I/O 正是適用情境。
>
> **B ✗** 刪除所有 replica 會讓 writer 故障時沒有 failover 目標，恢復時間大幅增加，讀取也會集中到 writer，影響 production。
>
> **C ✓** Serverless v2 依負載自動調整 ACU，零星使用的開發環境平時只付很少的容量；0 ACU 搭配 auto-pause 讓閒置期間不收運算費。
>
> **D ✗** Multi-AZ DB cluster 有三台 instance，對開發環境反而更貴，也不會依使用量縮小。
>
> **E ✗** Backtrack 會增加變更紀錄的儲存費用，而且它不取代 automated backups，不會降低成本。
>
> **考點**：SAP-3.5、SAP-2.6｜Aurora I/O-Optimized 與 Serverless v2

### 練習 26-12｜SAP｜單選｜跨 Region 關鍵交易系統 DR

Wanderly 的訂單系統使用 Aurora PostgreSQL，位於東京 Region。董事會要求：東京 Region 整體失效時，必須在新加坡 Region 恢復寫入，RPO 不超過數秒、RTO 不超過幾分鐘。平時新加坡的使用者也希望能低延遲地讀取訂單狀態。

哪個方案最合適？

- A. 建立 Aurora Global Database，以新加坡為 secondary Region 並在其中部署 Aurora Replica；Region 失效時執行 failover 把新加坡升為 primary
- B. 每小時把 Aurora snapshot 複製到新加坡，Region 失效時從最新 snapshot 還原
- C. 在新加坡建立 Aurora Serverless v2 cluster，用 AWS Lambda 每分鐘把東京的變更寫過去
- D. 在東京 cluster 增加三個 AZ 的 Aurora Replica，並設定 failover priority tier

> [!answer]- 答案：A
> **A ✓** Global Database 在儲存層把資料複寫到 secondary Region，典型 lag 小於 1 秒，failover 通常在一分鐘級完成；secondary Region 的 replica 平時就能服務當地讀取。
>
> **B ✗** 每小時一次的 snapshot 讓 RPO 可能長達一小時，還原大型資料庫的 RTO 也可能是數小時。
>
> **C ✗** 自建同步管線營運負擔高、容易遺失或重複資料，一分鐘的同步週期也無法保證秒級 RPO。
>
> **D ✗** 同一 Region 的 replica 只能撐過 AZ 故障，Region 整體失效時一樣無法服務。
>
> **考點**：SAP-2.2、SAP-1.3｜Aurora Global Database 的 RPO／RTO

### 練習 26-13｜SAP｜單選｜Major version upgrade

Wanderly 要把 RDS for PostgreSQL 13 升級到 16。這個資料庫支撐 24 小時營運的訂房服務，公司要求：升級前要能用接近即時的 production 資料完整測試新版本、正式切換的中斷控制在一分鐘左右、應用程式不修改連線字串，並在出問題時保有舊環境。

最合適的做法是什麼？

- A. 在 maintenance window 執行原地 major version upgrade，事前先做 manual snapshot
- B. 建立 read replica，在 replica 上升級到 16，測試後 promote 並修改應用程式連線到 replica
- C. 用 AWS DMS 把資料搬到新建的 PostgreSQL 16 instance，再修改 Route 53 記錄
- D. 建立 RDS Blue/Green Deployment，在 green 環境升級到 16 並測試，完成後執行 switchover

> [!answer]- 答案：D
> **A ✗** 原地升級期間資料庫無法服務，時間依資料量而定，可能遠超過一分鐘；失敗時只能從 snapshot 還原，回退慢。
>
> **B ✗** 升格後的 replica 有新的 endpoint，應用程式必須修改連線；而且升格前後的資料同步與切換都要自己協調。
>
> **C ✗** DMS 可以做到，但需要自建 instance、設定任務與驗證，營運負擔較高，也需要額外的 DNS 切換設計。
>
> **D ✓** Blue/Green Deployments 讓 green 持續從 blue 同步，可在 green 上升級並測試；switchover 時把 green 改用原本的名稱與 endpoint，中斷通常在一分鐘內，舊的 blue 環境保留供回退判斷。
>
> **考點**：SAP-2.1、SAP-3.4｜RDS Blue/Green Deployments

### 練習 26-14｜SAP｜選兩項｜加密 snapshot 跨帳號保存

Wanderly 的安全規範要求每天把 production RDS for MySQL 的 snapshot 保存到獨立的備份帳號，即使 production 帳號被入侵，備份仍需可用。目前 RDS 使用 AWS managed key（`aws/rds`）加密，工程師嘗試把 snapshot 分享給備份帳號時失敗。

哪兩個步驟是必要的？（選兩項）

- A. 把 snapshot 複製一份並改用 customer managed key 加密，在該 key 的 key policy 中允許備份帳號使用
- B. 修改 `aws/rds` 的 key policy，加入備份帳號的 root principal
- C. 把加密的 manual snapshot 分享給備份帳號，由備份帳號複製到自己帳號，並以自己的 KMS key 重新加密
- D. 直接把 automated backups 分享給備份帳號，省去建立 manual snapshot
- E. 先關閉 production instance 的加密，分享未加密 snapshot 後再重新開啟

> [!answer]- 答案：A、C
> **A ✓** 用 AWS managed key 加密的 snapshot 不能分享，因為無法修改它的 key policy。複製時改用 customer managed key，並在 key policy 授權目標帳號，才能讓對方解密。
>
> **B ✗** AWS managed key 的 key policy 由 AWS 管理，不能修改。
>
> **C ✓** 分享後由備份帳號複製到自己的帳號並用自己的 key 加密，副本完全屬於備份帳號；之後 production 帳號即使被入侵、刪除 snapshot 或撤銷 key 授權，副本仍可使用。
>
> **D ✗** Automated backups 不能直接分享，需要先複製成 manual snapshot。
>
> **E ✗** RDS 的加密建立後無法關閉，而且分享未加密資料違反安全規範。
>
> **考點**：SAP-2.3、SAP-2.2｜跨帳號分享加密 snapshot 的 KMS 條件

### 練習 26-15｜SAP｜單選｜需要 OS 存取的 SQL Server

Wanderly 併購的旅行社使用 Microsoft SQL Server，資料庫主機上必須安裝一套供應商的監控與備份 agent，並需要修改部分 Windows 系統設定。公司希望搬到 AWS 後仍由 AWS 負責大部分自動化（例如備份與部分修補），以降低營運負擔，短期內不改寫應用程式。

最合適的目標是什麼？

- A. Amazon RDS for SQL Server，搭配 option group 安裝 agent
- B. Amazon RDS Custom for SQL Server
- C. Aurora PostgreSQL 搭配 Babelfish
- D. 在 EC2 上自行安裝 SQL Server，並自建備份與修補流程

> [!answer]- 答案：B
> **A ✗** 標準 RDS 不提供作業系統存取，option group 只能啟用 AWS 支援的引擎功能，不能安裝任意第三方 agent。
>
> **B ✓** RDS Custom for SQL Server 允許存取底層作業系統與資料庫特權，可以安裝 agent 與調整系統設定，同時保留自動備份等受管功能，正好介於 RDS 與 EC2 自建之間。
>
> **C ✗** Babelfish 能降低 SQL Server 應用程式遷移到 PostgreSQL 的改寫量，但仍是不同的引擎，也不提供 OS 存取，不符合「短期不改寫」與「安裝 agent」。
>
> **D ✗** EC2 自建可以滿足 OS 需求，但所有備份、修補與高可用都要自己做，營運負擔最高；只有在 RDS Custom 也無法滿足時才選。
>
> **考點**：SAP-4.2、SAP-4.3｜RDS Custom 的使用時機

### 練習 26-16｜SAP｜單選｜低成本跨 Region 備援

Wanderly 的內部會計系統使用 RDS for PostgreSQL，位於東京 Region。法規要求在另一個 Region 保留可還原的備份，DR 目標為 RPO 15 分鐘、RTO 6 小時。這個系統預算很有限，在備援 Region 不希望持續執行任何 DB instance。

哪個方案最符合需求且成本最低？

- A. 建立 Aurora Global Database，並把會計系統遷移到 Aurora PostgreSQL
- B. 在大阪 Region 建立 cross-Region read replica，災難時 promote
- C. 啟用 RDS cross-Region automated backup replication，把 automated backups 與交易紀錄持續複製到大阪 Region，災難時在大阪執行 PITR
- D. 每天把 manual snapshot 複製到大阪 Region，災難時從最新 snapshot 還原

> [!answer]- 答案：C
> **A ✗** Global Database 能提供秒級 RPO，但需要遷移引擎並持續支付 secondary 的費用，對 15 分鐘 RPO、6 小時 RTO 是過度設計。
>
> **B ✗** Read replica 能滿足 RPO 與 RTO，但違反「不持續執行 DB instance」的成本限制。
>
> **C ✓** 跨 Region 複製 automated backups 包含持續的交易紀錄，在目的 Region 可以 PITR 到數分鐘前，符合 15 分鐘 RPO；還原大小適中的資料庫可在 6 小時內完成，且平時只付備份儲存與傳輸費用。
>
> **D ✗** 每天一次的 snapshot 讓 RPO 可能長達 24 小時，不符合 15 分鐘的要求。
>
> **考點**：SAP-2.2、SAP-1.5｜依 RPO／RTO 選擇剛好滿足的跨 Region 備份方案
