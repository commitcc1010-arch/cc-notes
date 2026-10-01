---
chapter: 24
title: Block 與 File Storage：EBS、EFS 與 FSx
part: 4
---

# 第 24 章　Block 與 File Storage：EBS、EFS 與 FSx

> [!abstract] 本章地圖
> **你會學到**：
> - 說明 EBS 是「透過網路掛載、綁定單一 AZ 的硬碟」，並依 IOPS、throughput 與成本選出 gp3、io2、st1、sc1
> - 看懂 snapshot 的增量機制，設計跨 AZ 還原、跨 Region 複製、Fast Snapshot Restore、archive tier 與 Recycle Bin
> - 分辨 EBS、instance store、EBS Multi-Attach 的使用時機與資料遺失風險
> - 為多台 Linux 機器設計共享的 EFS，正確設定 mount target、throughput mode、storage class 與 access point
> - 依通訊協定與既有系統，在 FSx for Windows File Server、Lustre、NetApp ONTAP、OpenZFS 之間做選擇
>
> **前置知識**：第 4 章（block／file／object 儲存）、第 17 章（EC2 與 instance store）、第 15 章（KMS 基礎）
> **考試比重**：SAA ★★★（Domain 3 高效能儲存、Domain 4 成本最佳化儲存、Domain 2 高可用）｜SAP ★★☆（Domain 2 業務持續、Domain 4 遷移）

## 24.1 故事：Wanderly 的三種「硬碟問題」

Wanderly 進入成長期後，工程師小林在同一週接到三張工單，乍看都是「硬碟」問題，實際上卻需要三種完全不同的儲存服務。

第一張來自資料庫。訂單資料庫還沒搬到 RDS（第 26 章），仍是一台 EC2 自己裝的 MySQL，資料放在一顆 1 TiB 的 gp2 volume 上。每到週五晚上訂房尖峰，資料庫延遲就從 2 毫秒暴增到 40 毫秒。CloudWatch 顯示 volume 的 IOPS 卡在 3,000 一條平平的線上，看起來像撞到了天花板。

第二張來自網站團隊。Web tier 已經用 Auto Scaling 分散在兩個 AZ（第 18 章），但後台編輯上傳的旅遊專題頁面樣板與活動素材，只存在其中一台機器的本機硬碟上。其他機器讀不到，只好用 cron 每五分鐘 rsync 一次，經常出現「A 機器看到新版、B 機器還是舊版」的情況。

第三張來自財務與客服部門。他們仍在用辦公室一台老舊的 Windows 檔案伺服器，靠公司 Active Directory 帳號控制誰能開哪個資料夾。機器保固即將到期，主管希望搬到 AWS，但「使用者照舊用 `\\files\finance` 開資料夾、權限一個都不能亂」。

這一章就跟著小林把三張工單逐一處理完。過程中你會看到：block storage 和 file storage 的差異不只是名稱，而是「誰能同時掛載、資料存在幾個 AZ、用什麼協定存取」這些會直接決定架構的特性。

## 24.2 先選介面：block、file、object 三條路

第 4 章介紹過三種儲存介面，這裡用一張表把它們和 AWS 服務對起來，因為本章所有選型都從這一步開始：

| 介面 | 應用程式看到什麼 | 誰負責檔案系統 | AWS 服務 | 典型用途 |
|---|---|---|---|---|
| Block | 一顆空白硬碟（`/dev/nvme1n1`），要自己格式化 | 你的作業系統（ext4、XFS、NTFS） | EBS、instance store | 開機磁碟、自管資料庫、單機高效能 I/O |
| File | 一個可掛載的目錄（`/mnt/shared`、`\\server\share`） | 儲存服務本身 | EFS、FSx 家族 | 多台機器共享檔案、家目錄、HPC |
| Object | 用 HTTP API 存取的 key → 物件 | S3 | S3（第 22、23 章） | 照片、備份、資料湖、靜態網站 |

**Block storage（區塊儲存）** 只提供「第幾個區塊寫入哪些位元組」這種最底層的操作，檔案、目錄、權限都是作業系統在上面建立的。正因為檔案系統的狀態（哪個區塊屬於哪個檔案）存在作業系統的記憶體裡，兩台機器同時寫同一顆 block 裝置，彼此不知道對方改了什麼，檔案系統會毀損。這是「EBS 預設只能掛一台」的根本原因。

**File storage（檔案儲存）** 則把檔案系統放在儲存服務那一端，用 NFS 或 SMB 這類網路檔案協定提供給許多 client。鎖定（locking）、權限、目錄結構都由服務端統一協調，所以上百台機器可以同時讀寫同一個目錄。

所以小林的三張工單，第一步就分好了：資料庫是單機 block I/O 問題（EBS），網站素材是 Linux 多機共享檔案問題（EFS），財務資料夾是 Windows SMB 與 AD 權限問題（FSx for Windows File Server）。接下來先處理最緊急的資料庫。

## 24.3 EBS 是什麼：一顆透過網路掛上的硬碟

**Amazon EBS（Elastic Block Store）** 提供可以掛載到 EC2 的 block 裝置，稱為 **EBS volume**。它摸起來像一顆插在主機上的硬碟，實際上卻是放在 AWS 儲存叢集裡、透過網路連到 EC2 的。這個「網路硬碟」的本質，解釋了 EBS 的大部分特性。

### 四個必須記住的事實

1. **Volume 屬於單一 AZ。** 在 `ap-northeast-1a` 建立的 volume，只能掛到 1a 的 instance。要搬到另一個 AZ，必須先做 snapshot，再從 snapshot 在新 AZ 建立 volume（24.5 節）。
2. **Volume 在 AZ 內自動複寫。** AWS 會在同一個 AZ 的多台儲存伺服器上保存副本，單一硬體故障不會讓你遺失資料。但這個複寫**不跨 AZ**，所以 EBS 本身不能讓你撐過 AZ 故障。
3. **Volume 的生命週期獨立於 instance。** Instance stop 之後 volume 仍在；instance terminate 時，root volume 預設會被刪除，額外掛的 data volume 預設會保留。這由每顆 volume 的 **DeleteOnTermination** 屬性決定，可以逐顆修改。
4. **Volume 一般一次只掛一台 instance**（例外是 24.7 節的 Multi-Attach）。可以在 instance 執行中卸載（detach）再掛到同 AZ 的另一台。

### 效能有兩個天花板：volume 與 instance

既然 EBS 走網路，EC2 和 volume 之間就有一條頻寬有限的通道。每種 instance type 都有自己的 **EBS 頻寬與 IOPS 上限**；現行 Nitro 世代的 instance 預設都是 **EBS-optimized**，也就是 EBS 流量有專用頻寬，不和一般網路流量搶。

這帶來一個常見盲點：你可以為一顆 volume 配置很高的 IOPS，但如果掛在一台小 instance 上，實際效能會被 instance 的上限卡住。效能除錯時一定要兩邊一起看：volume 的配置值，和 instance type 的 EBS 上限。

### 修改不必停機：Elastic Volumes

**Elastic Volumes** 讓你在 volume 掛載使用中直接修改大小、volume type、IOPS 與 throughput，不需要卸載或重開機。要注意三點：

- **只能放大不能縮小。** 想縮小只能建新的小 volume，再把資料複製過去。
- 放大 volume 後，作業系統裡的**分割區與檔案系統要自己擴充**（例如 `growpart` 與 `xfs_growfs`），否則多出來的空間看不到。
- 同一顆 volume 一次只能有一個進行中的修改，要等前一次修改到達 `completed` 才能再改；目前規則是在任意連續 24 小時內最多修改 4 次。（舊資料與舊題目常寫「每次修改後要等 6 小時」，那是較早的限制。）修改依大小可能需要數分鐘到數小時才完成。

到這裡小林知道：資料庫的問題可能出在 volume 本身，也可能出在 instance。要判斷是哪一個，得先懂 EBS 的效能怎麼計算。

## 24.4 EBS volume types：IOPS、throughput 與成本的取捨

### 先懂三個效能名詞

- **IOPS（Input/Output Operations Per Second）**：每秒能完成幾次讀寫操作。資料庫大量讀寫小區塊（例如 16 KiB 的資料頁），最在意 IOPS。
- **Throughput（吞吐量）**：每秒能搬多少資料，單位 MiB/s。掃描大型日誌、做備份、處理影片，一次讀一大段連續資料，最在意 throughput。
- **Latency（延遲）**：一次操作從送出到完成要多久。SSD 是毫秒以下到個位數毫秒，HDD 則慢得多，而且很怕隨機存取。

三者的關係是：**throughput ≈ IOPS × 每次 I/O 的大小**。同一顆 volume，用 16 KiB 小區塊讀寫時先撞到 IOPS 上限，用 1 MiB 大區塊讀寫時先撞到 throughput 上限。這就是為什麼 AWS 把 SSD 類型設計成「以 IOPS 為主」，HDD 類型設計成「以 throughput 為主」。

### 五種主要 volume type

| 類型 | 介質 | 設計目標 | 效能特性（考試常用數字） | 可當開機磁碟 | 適合 |
|---|---|---|---|---|---|
| **gp3** | SSD | 一般用途，預設首選 | 基準 3,000 IOPS、125 MiB/s，與容量無關；可另外付費調高 IOPS 與 throughput（上限見下方說明） | 可以 | 開機磁碟、多數應用與中型資料庫 |
| **gp2** | SSD | 舊一代一般用途 | 每 GiB 3 IOPS（最低 100），小於 1 TiB 的 volume 可 burst 到 3,000；最高 16,000 IOPS | 可以 | 既有環境，建議遷移到 gp3 |
| **io2 Block Express** | SSD | 關鍵、持續高 IOPS、低延遲 | 最高 256,000 IOPS、4,000 MiB/s、64 TiB；耐久度 99.999% | 可以 | 核心交易資料庫、SAP HANA、Oracle |
| **st1** | HDD | Throughput optimized | 以 MiB/s 計，最高 500 MiB/s；隨機小 I/O 很差 | 不行 | 大型循序讀寫：日誌處理、資料倉儲 ETL、Kafka |
| **sc1** | HDD | Cold，最低成本 | 最高 250 MiB/s，每 GB 價格最低 | 不行 | 很少存取的循序冷資料 |

另外還有 **io1**（舊一代 provisioned IOPS SSD，最高 64,000 IOPS）與 **standard（magnetic）**（上一代 HDD），新設計不會選它們。gp2、gp3、st1、sc1 的年故障率設計目標是 0.1%–0.2%（耐久度 99.8%–99.9%），io2 則是 99.999%，這也是題目說「要求最高耐久度的 block storage」時指向 io2 的原因。

> [!note] 數字會更新
> AWS 會持續提高 volume 上限。2025 年起 gp3 的上限已提高到容量 64 TiB、80,000 IOPS（每 GiB 最多 500 IOPS）、2,000 MiB/s，但考試題目仍常用「gp3 最高 16 TiB、16,000 IOPS、1,000 MiB/s」這組經典數字。實務上請以當時的 EBS 文件為準；解題時抓住「gp3 是可獨立調整的通用 SSD、io2 是頂規 SSD、HDD 不能開機」這個相對關係就夠了。

### gp2 的陷阱：IOPS 綁著容量

回到小林的資料庫。gp2 的 IOPS 由容量決定：1 TiB（1,024 GiB）× 3 = 約 3,072 IOPS，正好就是 CloudWatch 上那條天花板。小於 1 TiB 的 gp2 還能用 **burst credit（爆發額度）** 短暫衝到 3,000 IOPS，額度用完就掉回基準值；超過 1 TiB 後基準已高於 3,000，就沒有 burst 的概念了。

在 gp2 時代，想要 6,000 IOPS 只能把 volume 放大到 2 TiB，即使根本用不到那麼多空間。這是典型的「為了效能多買容量」。

**gp3** 把三件事拆開：容量、IOPS、throughput 各自設定、各自計價。不論多小的 gp3 都有 3,000 IOPS 與 125 MiB/s 的基準，需要更多時另外加購。而且 gp3 每 GB 的單價本來就比 gp2 低（約便宜 20%）。所以小林的解法很直接：

```bash
aws ec2 modify-volume \
  --volume-id vol-0a1b2c3d4e5f67890 \
  --volume-type gp3 \
  --iops 6000 \
  --throughput 250

aws ec2 describe-volumes-modifications --volume-ids vol-0a1b2c3d4e5f67890
```

第一個指令用 Elastic Volumes 原地把 gp2 改成 gp3，並配置 6,000 IOPS 與 250 MiB/s；第二個指令觀察修改進度：狀態依序是 `modifying` → `optimizing` → `completed`。容量放大在進入 `optimizing` 後就生效；`optimizing` 期間的效能介於舊設定與新設定之間，到 `completed` 才完全達到 6,000 IOPS。修改過程中資料庫不需要停機。改完後，小林順手確認那台 instance type 的 EBS 上限高於 6,000 IOPS，避免換成 instance 卡住。

> [!warning] 常見誤解
> 「IOPS 不夠就換 io2。」io2 很強也很貴，適合需要數萬 IOPS、或要求 99.999% 耐久度與穩定低延遲的關鍵系統。若需求只是幾千到一萬多 IOPS，gp3 加購 IOPS 幾乎總是比較便宜。考題寫「MOST cost-effective」時，先檢查 gp3 是否夠用。

### 什麼時候選 HDD？

st1 與 sc1 的效能以 throughput 計，而且隨容量增加。它們適合「一次讀一大段、從頭讀到尾」的工作，例如每天掃一遍 TB 級的點擊日誌。它們有兩個硬限制：**不能當開機磁碟**，以及**隨機小 I/O 非常慢**。如果題目說「大量循序讀取、要最低成本」選 st1；「很少存取、要每 GB 最便宜的 block storage」選 sc1。但要注意：如果資料很少存取，又不一定需要 block 介面，S3 的冷儲存類別（第 23 章）往往更便宜。

### 超過單一 volume 的效能：RAID 0

如果需要的 IOPS 或 throughput 超過單顆 volume 上限（且 instance 上限還有餘裕），可以把多顆 volume 用作業系統做成 **RAID 0（條帶化）**，效能大致相加。代價是任何一顆故障整組資料都毀損，所以一定要搭配 snapshot。RAID 1（鏡像）在 EBS 上通常不建議，因為 EBS 在 AZ 內本來就有複寫，鏡像只會讓寫入流量加倍。

解決了效能問題，下一個問題接踵而至：這顆資料庫 volume 如果整個 AZ 掛掉怎麼辦？答案從 snapshot 開始。

## 24.5 EBS snapshot：增量備份與跨 AZ、跨 Region 的橋樑

**EBS snapshot（快照）** 是 volume 在某個時間點的備份。它存放在 AWS 管理的 S3 中（你在自己的 bucket 裡看不到），因此是 **Regional** 的：同一 Region 的任何 AZ 都能用它建立新 volume。這讓 snapshot 成為 EBS 跨 AZ 的唯一內建橋樑。

### 增量機制：只存改變的區塊

```text
 Volume（100 GiB，只寫了 10 GiB）

 時間 T1           T2                 T3
 ┌──────────┐     ┌──────────┐       ┌──────────┐
 │ A B C D  │     │ A B' C D │       │ A B' C D'│
 └──────────┘     └──────────┘       └──────────┘
      │ ①              │ ②                 │ ③
      ▼                ▼                   ▼
 snap-1: A B C D   snap-2: B'          snap-3: D'
 （完整的已用區塊） （只存改變的區塊，   （只存 D'，
                     其餘指向 snap-1）    其餘指向前面的）

 ④ 刪除 snap-1：B 被 snap-2 取代可刪；A、C、D 仍被 snap-2 需要而保留
```

① 第一次 snapshot 會複製所有「已寫入」的區塊（沒寫過的空白區塊不算），所以 100 GiB 的 volume 只用了 10 GiB 時，第一份 snapshot 大約 10 GiB。② 之後的 snapshot 只儲存自上次以來改變的區塊，其餘區塊用指標指向舊 snapshot。③ 每一份 snapshot 在還原時都是「完整的」：AWS 會沿著指標組出那個時間點的整顆 volume。④ 刪除中間的 snapshot 很安全：只有不再被任何 snapshot 引用的區塊會真的被刪掉，後面的 snapshot 仍然完整可用。

這也解釋了計費方式：snapshot 按實際儲存的區塊量收費，所以頻繁 snapshot 的成本主要取決於資料變動量，而不是 volume 大小。

### Crash-consistent 與 application-consistent

Snapshot 在你按下的那一刻擷取區塊，但應用程式記憶體裡還沒寫進磁碟的資料不會在裡面。這種 snapshot 稱為 **crash-consistent（當機一致）**：效果等同於突然斷電後的磁碟，資料庫通常能靠 journal 恢復，但不保證。

要得到 **application-consistent（應用程式一致）** 的備份，需要先讓應用程式把資料 flush 到磁碟並暫停寫入（例如 MySQL 的 `FLUSH TABLES WITH READ LOCK`、Windows 的 VSS），再拍 snapshot。如果資料庫跨多顆 volume（例如資料與日誌分開），要用 **multi-volume snapshot**，讓同一台 instance 上的多顆 volume 在同一時間點一起拍，否則還原時資料和日誌會對不上。

### 從 snapshot 建立 volume：為什麼第一次讀很慢？

從 snapshot 建立的新 volume 可以立刻掛載使用，但資料是**延遲載入（lazy loading）**的：區塊在第一次被讀取時才從 S3 拉到 volume 上。所以剛還原的資料庫，第一次掃描每個區塊都會很慢，這稱為 first-touch latency。傳統做法是還原後先用 `fio` 或 `dd` 把所有區塊讀一遍（initialization，預熱）。

**Fast Snapshot Restore（FSR）** 讓你對特定 snapshot、在指定的 AZ 預先啟用「已完全初始化」的狀態：從它建立的 volume 一建立就有完整效能，不需要預熱。FSR 依「每個 snapshot × 每個 AZ × 啟用時數」計費，而且同時能用它快速建立的 volume 數量有額度限制。適合「必須在幾分鐘內還原且立刻承受正式流量」的情境，例如 DR 演練、從 golden snapshot 大量建立 VDI 或測試環境。

```bash
aws ec2 enable-fast-snapshot-restores \
  --availability-zones ap-northeast-1a ap-northeast-1c \
  --source-snapshot-ids snap-0123456789abcdef0
```

### 跨 Region 複製與分享

- **Copy snapshot**：可以把 snapshot 複製到另一個 Region（做 DR）或同一 Region（換加密金鑰）。複製時可以加密原本未加密的 snapshot，或換成另一把 KMS key。跨 Region 複製時，目的地 Region 要有可用的 KMS key，因為 KMS key 是 Regional 的。
- **Share snapshot**：可以把 snapshot 分享給指定 AWS 帳號（或公開，正式資料絕對不要這樣做）。加密 snapshot 的分享要點見 24.6 節。

```bash
aws ec2 copy-snapshot \
  --region ap-southeast-1 \
  --source-region ap-northeast-1 \
  --source-snapshot-id snap-0123456789abcdef0 \
  --encrypted \
  --kms-key-id alias/wanderly-dr-ebs \
  --description "orders-db DR copy"
```

注意 `copy-snapshot` 要在**目的地 Region**（這裡是新加坡）執行，`--source-region` 指向東京，並指定新加坡的 KMS key 加密複本。

### 自動化：Data Lifecycle Manager 與 AWS Backup

手動拍 snapshot 遲早會忘。**Amazon Data Lifecycle Manager（DLM）** 讓你用 tag 選定 volume 或 instance，設定排程（例如每 4 小時）、保留數量、跨 Region 複製、跨帳號分享，甚至自動啟用 FSR 或移到 archive tier。若組織要統一管理 EBS、RDS、EFS、FSx、DynamoDB 等多種資源的備份與保存政策，則用 **AWS Backup**（第 34、43 章）。

### 降成本與防誤刪：archive tier 與 Recycle Bin

- **EBS Snapshots Archive（archive tier）**：把很少需要還原、但要長期保存的 snapshot（例如每月的合規備份）移到封存層，儲存成本約便宜 75%。代價是：封存時會存成**完整 snapshot**（不再是增量）、**最少要存 90 天**（提早刪除仍按 90 天計費）、還原需要 **24–72 小時**先回到標準層。
- **Recycle Bin（資源回收筒）**：建立 retention rule 後，被刪除的 snapshot 與 EBS-backed AMI 不會立即消失，而是在回收筒中保留指定期間（1 天到 1 年），期間可以復原。Rule 可以用 tag 篩選，也可以上鎖（rule lock），防止有人先改規則再刪資源。這是對抗誤刪與勒索軟體刪除備份的重要防線。

> [!tip] 考試提示
> 「snapshot 很少用到但要保存數年、要最低成本」→ archive tier。「防止有人誤刪 snapshot、要能在一段時間內救回」→ Recycle Bin。「還原後立刻要有完整效能」→ Fast Snapshot Restore。這三個常被放在同一題的選項裡互相干擾。

## 24.6 EBS 加密：一個勾選，保護四個地方

**EBS encryption** 使用 KMS key（第 15 章）以 AES-256 加密。一顆加密的 volume，下列四者都會被加密：

1. Volume 上靜態存放的資料。
2. Instance 與 volume 之間傳輸中的資料。
3. 從這顆 volume 建立的所有 snapshot。
4. 從這些 snapshot 建立的所有 volume。

加密與解密發生在承載 instance 的主機上，對作業系統與應用程式完全透明，效能影響可以忽略。可以使用 AWS managed key（`aws/ebs`）或自己的 customer managed key。

### 預設加密與既有未加密 volume

**EBS encryption by default** 是一個「帳號 × Region」的設定：開啟後，該 Region 之後新建的所有 volume 與 snapshot copy 都會自動加密。它不會回頭加密既有的 volume。

一顆已存在的未加密 volume **不能原地加密**，標準流程是：

1. 對未加密 volume 建立 snapshot。
2. 從該 snapshot 建立新 volume 時勾選加密（或先 copy snapshot 並加密）。
3. 停止應用程式，卸載舊 volume、掛上新的加密 volume（root volume 則用加密的 AMI 重新啟動 instance）。

這和 RDS「加密只能在建立時決定，既有 instance 要靠加密 snapshot 還原」的邏輯一樣（第 26 章）。

### 加密 snapshot 的跨帳號分享

用 `aws/ebs` 這把 AWS managed key 加密的 snapshot **不能分享給其他帳號**，因為你無法修改 AWS managed key 的 key policy。要跨帳號分享，必須使用 **customer managed key**，並在 key policy 中授權對方帳號使用該 key（`kms:Decrypt`、`kms:CreateGrant`、`kms:DescribeKey` 等），再分享 snapshot。對方通常會再用自己帳號的 key 複製一份，讓之後不再依賴來源帳號的 key。

> [!warning] 常見誤解
> 「從加密的 snapshot 可以建立未加密的 volume。」不行。加密是一路傳下去的：加密 snapshot 建出的 volume 一定是加密的。反過來，未加密 snapshot 可以在建立 volume 或複製時變成加密的。

## 24.7 Multi-Attach 與 instance store：兩種「例外」

EBS 的標準模型是「一顆 volume 掛一台 instance、資料持久保存」。考試很喜歡拿兩個偏離這個模型的選項來測試你：可以掛多台的 Multi-Attach，以及不持久的 instance store。

### EBS Multi-Attach

**Multi-Attach** 允許一顆 **io1 或 io2** volume 同時掛載到**同一個 AZ** 內最多 16 台 Nitro 型 instance。它的用途很窄：叢集軟體需要共享同一顆磁碟的場景，例如 Linux 上的叢集檔案系統（GFS2、OCFS2）或 Windows Server Failover Clustering（io2 支援 NVMe reservation 這類 fencing 機制）。

關鍵限制：

- 只支援 provisioned IOPS SSD（io1／io2），gp3、st1、sc1 都不行。
- 只能在同一個 AZ，**不提供跨 AZ 共享，也不提供高可用**。
- EBS 只負責把同一組區塊給多台機器，**不協調寫入**。用一般的 ext4、XFS 讓多台同時寫，檔案系統一定會損壞，必須使用 cluster-aware 的檔案系統或應用程式自己的鎖定與 fencing。

所以「多台 EC2 要共享一個目錄」的題目，答案幾乎都是 EFS 或 FSx；只有題目明確說「叢集軟體需要共享 block 裝置」時才是 Multi-Attach。

### Instance store

**Instance store（執行個體儲存）** 是實體插在承載 instance 那台主機上的本機磁碟（多為 NVMe SSD），只有特定 instance type 提供（例如型號帶 `d` 的 `m6id`、`c6gd`，或儲存最佳化的 `i4i`）。第 17 章從 EC2 角度介紹過它，這裡從儲存角度比較：

| 比較 | EBS | Instance store |
|---|---|---|
| 位置 | AWS 儲存叢集，經網路連線 | 主機本機磁碟 |
| 持久性 | 獨立於 instance 存在 | 只在 instance 運行期間存在 |
| Reboot | 保留 | 保留 |
| Stop／hibernate／terminate | 保留（root 視 DeleteOnTermination） | **資料遺失** |
| 底層主機故障 | 保留 | **資料遺失** |
| Snapshot | 支援 | 不支援 |
| 大小 | 自選，可放大 | 由 instance type 固定 |
| 效能 | 依 volume type 與 instance 上限 | 極高 IOPS、極低延遲 |
| 費用 | 另外計費 | 包含在 instance 價格內 |

Instance store 適合「丟了可以重建」的資料：快取、暫存檔、緩衝區、排序時的中間結果，或應用程式本身就在多台機器之間複寫資料的系統（例如 Cassandra、Kafka 叢集，靠多副本而不是單機磁碟保證耐久）。唯一一份的資料絕對不能只放在 instance store。

> [!warning] 常見誤解
> 「Stop 再 start 跟 reboot 一樣。」不一樣。Reboot 是同一台主機重新開機，instance store 資料還在；stop／start 通常會讓 instance 換到另一台主機，舊主機上的 instance store 資料就消失了。

EBS 這條線到這裡告一段落。小林的第二張工單是「多台 web server 要看到同一份檔案」，block storage 無論怎麼調都解不了，需要真正的共享檔案系統。

## 24.8 EFS：多 AZ 共享的 Linux 檔案系統

**Amazon EFS（Elastic File System）** 是全受管的 **NFS（Network File System，網路檔案系統）** 服務。Linux instance 用標準 NFS 協定（NFSv4.0 與 4.1）掛載後，看到的就是一個普通的目錄，數千台 client 可以同時讀寫，檔案鎖定與權限由 EFS 協調。容量會隨寫入的資料自動增減，不需要預先配置，按實際使用量計費。

EFS 只支援 NFS，也就是 **Linux／Unix client**。Windows 機器要共享檔案，請看 24.9 節的 FSx for Windows File Server。

### 架構：一個檔案系統、每個 AZ 一個 mount target

```text
                VPC 10.20.0.0/16
  ┌───────────────────────────────────────────────────────────┐
  │   AZ 1a                              AZ 1c                │
  │  ┌─────────────────────┐           ┌─────────────────────┐│
  │  │ app-a subnet        │           │ app-c subnet        ││
  │  │ [web EC2] [web EC2] │           │ [web EC2] [Lambda]  ││
  │  │     │ ① NFS 2049    │           │     │               ││
  │  │     ▼               │           │     ▼               ││
  │  │ [mount target ENI]  │           │ [mount target ENI]  ││
  │  │  sg-efs ②           │           │  sg-efs             ││
  │  └─────────┬───────────┘           └─────────┬───────────┘│
  │            └──────────────┬──────────────────┘            │
  │                           ▼ ③                             │
  │          [ EFS file system fs-0123（Regional）]           │
  │           資料自動跨多個 AZ 保存                           │
  └───────────────────────────────────────────────────────────┘
```

① Client 透過 NFS（TCP 2049）連到**自己所在 AZ 的 mount target**。**Mount target** 是 EFS 在你的 subnet 裡建立的一張 ENI，有一個 private IP。每個 AZ 最多一個 mount target，同一 AZ 的所有 subnet 共用它。② Mount target 有自己的 security group，最佳做法是只允許來自應用程式 security group 的 TCP 2049 入站。③ 所有 mount target 都通往同一個檔案系統，所以 1a 寫入的檔案，1c 立刻讀得到。EFS 提供 close-to-open 一致性：一台 client 寫完並關閉檔案後，其他 client 再開啟就會看到新內容。

Client 使用 EFS 的 DNS 名稱（`fs-0123.efs.ap-northeast-1.amazonaws.com`）掛載時，會自動解析到同 AZ 的 mount target，避免跨 AZ 流量與費用。建議安裝 **amazon-efs-utils** 掛載輔助工具，它讓 TLS 加密與 IAM 授權變成一個參數：

```bash
sudo mount -t efs -o tls,iam,accesspoint=fsap-0abc1234def567890 fs-0123456789abcdef0:/ /mnt/cms
```

除了 EC2，ECS、EKS、Lambda（需連進 VPC，第 19 章）都能掛載 EFS；地端伺服器也能透過 Direct Connect 或 VPN 掛載。

### Regional 與 One Zone

- **Regional（區域型，原稱 Standard）**：資料跨多個 AZ 保存，可以在每個 AZ 建 mount target，能承受一個 AZ 故障。正式環境的預設選擇。
- **One Zone（單 AZ）**：資料只存在一個 AZ，價格明顯較低，但該 AZ 故障時檔案系統無法存取，極端情況可能遺失資料。適合可重建的資料或開發測試環境。其他 AZ 的 client 仍可跨 AZ 掛載，但會產生跨 AZ 傳輸費用，且失去 AZ 隔離。

### Performance mode：建立後不能改

| Performance mode | 特性 | 何時選 |
|---|---|---|
| **General Purpose**（預設） | 每次操作延遲最低 | 幾乎所有情境，包括網站、CMS、家目錄、容器 |
| **Max I/O** | 支援更高的總體並行度，但每次操作延遲較高 | 舊式的超大規模平行工作；One Zone 與 Elastic throughput 不支援 |

AWS 已提高 General Purpose 的上限，現在建議幾乎所有工作負載都用 General Purpose。考題如果強調「延遲敏感」，Max I/O 就是錯的。

### Throughput mode：誰來決定頻寬

- **Elastic（建議預設）**：頻寬隨工作負載自動擴縮，按實際傳輸的資料量計費。適合尖峰難預測、平時低流量的工作負載。
- **Provisioned**：你指定固定的 throughput，與儲存量無關，按配置值計費。適合長時間穩定且需要高 throughput、但資料量不大的情境。
- **Bursting**：throughput 隨儲存量成長（資料越多頻寬越大），小檔案系統靠 burst credit 短暫衝高。資料量小卻需要持續高頻寬時，credit 會耗盡而變慢，這是舊題常見的「EFS 突然變慢」原因。

### Storage classes 與 lifecycle：讓冷檔案自動變便宜

EFS 有三種 storage class：

- **Standard**：頻繁存取，延遲最低（Regional 為 EFS Standard，One Zone 為 EFS One Zone）。
- **Infrequent Access（IA）**：每 GB 儲存費低很多，但每次讀取另收存取費（One Zone 對應 One Zone-IA）。
- **Archive**：比 IA 更便宜（約再省一半），給一年只存取幾次的資料。只支援使用 Elastic throughput 的 Regional 檔案系統，最短存放 90 天。

IA 與 Archive 中小於 128 KiB 的檔案會以 128 KiB 計費，所以 lifecycle 不會把這類小檔案搬過去。

**Lifecycle management** 依「多久沒被存取」自動搬移檔案，例如 30 天沒讀過移到 IA、90 天沒讀過移到 Archive，並可設定「被存取一次就移回 Standard」。整個過程對應用程式透明：檔案路徑不變，IA 與 Archive 的檔案仍可直接讀取，不需要像 S3 Glacier 那樣先提出取回請求（第 23 章）。

小林檢查後發現，素材目錄 2 TB 中有九成是一年前的活動頁面，幾乎沒人讀。啟用 lifecycle 後，這部分的儲存費用大幅下降，網站完全不用改程式。

### 安全：網路、身份、加密三層

1. **網路**：mount target 的 security group 控制哪些 client 能連 2049。
2. **身份與授權**：**EFS file system policy** 是附加在檔案系統上的 resource-based policy，可以要求 client 使用 IAM 身份掛載、限制唯讀，或強制 TLS。之後才是檔案本身的 POSIX 權限（UID／GID 與 rwx）。
3. **加密**：靜態加密（KMS）**只能在建立檔案系統時啟用**，之後不能開啟；傳輸中加密透過掛載時的 `tls` 參數。

強制所有 client 使用 TLS 的 file system policy：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedTransport",
      "Effect": "Deny",
      "Principal": { "AWS": "*" },
      "Action": "*",
      "Resource": "arn:aws:elasticfilesystem:ap-northeast-1:111122223333:file-system/fs-0123456789abcdef0",
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

### Access points：替每個應用程式開一扇專屬的門

**EFS access point** 是檔案系統的應用程式專用入口，可以強制兩件事：

- **POSIX 身份**：透過這個 access point 的所有操作，一律以指定的 UID／GID 執行，不管 client 自己宣稱是誰。
- **根目錄**：client 看到的 `/` 其實是檔案系統裡的某個子目錄（例如 `/tenants/hotel-a`），看不到也碰不到其他目錄；目錄不存在時可自動以指定權限建立。

搭配 IAM policy（例如只允許某個 Lambda 的 role 使用某個 access point），就能在同一個檔案系統裡安全地切給多個應用程式或租戶。Lambda 掛載 EFS 時一定要透過 access point。

### 跨 Region：EFS replication

**EFS replication** 可以把檔案系統持續複寫到另一個 Region（或同一 Region），大部分變更會在幾分鐘內同步，AWS 公布對大多數檔案系統維持 15 分鐘的 RPO（檔案數超過 1 億、或有頻繁變動的超大檔案時可能更久）。目的地檔案系統在複寫期間是**唯讀**的；要 failover 時刪除 replication 設定，目的地就變成可寫入的獨立檔案系統。日常的時間點備份則由 AWS Backup 負責。Replication 防的是 Region 故障，不防誤刪：來源刪掉的檔案，幾分鐘後目的地也會刪掉。

到這裡網站素材的問題解決了：所有 web server 掛同一個 EFS，rsync 腳本退休。最後一張工單是 Windows 檔案伺服器，EFS 不支援 SMB，需要換一個家族。

## 24.9 FSx 家族：把熟悉的檔案系統原封不動搬上雲

EFS 是 AWS 自己設計的 NFS 服務。但企業世界裡已經有許多成熟的檔案系統：Windows 的 NTFS 與 SMB、HPC 界的 Lustre、企業儲存的 NetApp ONTAP、Linux 社群的 ZFS。它們各自有使用者依賴的功能與管理流程。**Amazon FSx** 提供這四種檔案系統的全受管版本：AWS 負責硬體、修補、備份與高可用，你繼續使用原本的協定與功能。

### FSx for Windows File Server

**FSx for Windows File Server** 是建立在 Windows Server 上的全受管檔案伺服器，對 client 而言就是一台標準的 Windows 檔案伺服器：

- **SMB 協定**與 **NTFS** 檔案系統，完整支援 Windows ACL（資料夾與檔案權限）。
- **必須加入 Active Directory**：可以是 AWS Managed Microsoft AD，或公司自管的 AD（地端或 EC2 上皆可）。使用者用原本的網域帳號登入，權限照舊。
- 支援 **DFS Namespaces**（把多台檔案伺服器整合成一個 `\\corp\shares` 路徑）、shadow copies（使用者自己還原「舊版」檔案）、資料重複刪除（data deduplication）、使用者配額、存取稽核日誌。
- 儲存可選 SSD 或 HDD；throughput capacity 另外配置，可以之後調整。
- 每天自動備份到 S3，也可以手動備份。
- Linux 與 macOS client 也能透過 SMB 存取。

部署類型決定可用性：

- **Single-AZ**：一台檔案伺服器在一個 AZ，AZ 故障即中斷。
- **Multi-AZ**：在兩個 AZ 各有一台檔案伺服器（preferred 與 standby），資料同步複寫，偵測到故障時**自動 failover**，client 繼續使用同一個 DNS 名稱，不需要改設定。

小林為財務部門建立了一個 Multi-AZ 的 FSx for Windows File Server，加入公司 AD（透過 Direct Connect 連回辦公室，第 8 章），再用第 25 章的 DataSync 把舊伺服器的檔案連同 NTFS 權限一起搬過來。使用者的磁碟機代號與路徑透過 DFS namespace 保持不變。

### FSx for Lustre

**Lustre** 是超級電腦界常用的平行檔案系統：把一個檔案切成許多片段分散到很多台儲存伺服器，讓數千個運算節點同時讀寫，總 throughput 可以達到每秒數百 GB、延遲在毫秒以下。**FSx for Lustre** 是它的受管版本，Linux client 使用 Lustre client 掛載。

它的殺手級功能是與 **S3 的 data repository 整合**：把檔案系統和一個 S3 bucket（或 prefix）建立 **data repository association**，S3 裡的物件會以檔案的形式出現在 Lustre 上，第一次讀取時才從 S3 載入（lazy load）；運算結果可以匯出回 S3，也可以設定雙向的自動匯入匯出。於是 S3 是長期、便宜、耐久的資料湖，Lustre 是運算期間的高速工作區。

部署類型：

| 類型 | 資料保護 | 適合 |
|---|---|---|
| **Scratch** | 不複寫；檔案伺服器故障時資料遺失；不支援備份 | 短期、可重建的運算，例如一次性的模型訓練或模擬，最便宜且 burst 效能高 |
| **Persistent** | 在**同一個 AZ 內**複寫，故障的伺服器會自動替換；支援備份 | 長時間運行、需要保留資料的工作負載 |

不論哪一種，FSx for Lustre 都**只部署在單一 AZ**，因為 HPC 運算節點通常也集中在同一 AZ（甚至 cluster placement group，第 17 章）以取得最低延遲。典型用途：機器學習訓練（SageMaker、EKS）、基因分析、影片算圖、金融風險模擬、EDA。和 AWS Batch、ParallelCluster 的搭配見第 21 章。

Wanderly 的資料科學團隊每週要用三天前的訂房紀錄訓練一次定價模型，資料在 S3、中間檔可重建。他們選擇每次訓練前建立一個 scratch 型 FSx for Lustre 連到 S3，訓練完把模型匯出回 S3，再刪掉檔案系統。

### FSx for NetApp ONTAP

**NetApp ONTAP** 是企業資料中心最常見的儲存作業系統之一。**FSx for NetApp ONTAP** 提供完整的 ONTAP 功能：

- **多協定**：同時支援 NFS、SMB、iSCSI（以及 NVMe/TCP），Linux、Windows、macOS 都能存取，同一份資料可以同時以 NFS 和 SMB 提供。
- **儲存效率**：重複資料刪除、壓縮、thin provisioning；並有 SSD 主儲存層加上可自動分層的低成本 **capacity pool** 儲存層，冷資料自動下沉。
- **Snapshot 與 FlexClone**：瞬間建立、幾乎不占空間的複本，適合給測試環境一份正式資料的副本。
- **SnapMirror**：把資料從地端 NetApp 複寫到 AWS，或在兩個 FSx 之間跨 Region 複寫。這讓遷移與 DR 都能沿用 NetApp 團隊原本的工具與流程。
- **SnapLock**：WORM（一次寫入、多次讀取）保存，滿足法規不可竄改的要求。
- 部署類型有 Single-AZ 與 Multi-AZ。

題目只要出現「地端是 NetApp」「同時需要 NFS 與 SMB（或 iSCSI）」「SnapMirror」，幾乎就是 FSx for ONTAP。

### FSx for OpenZFS

**ZFS** 是以資料完整性與 snapshot／clone 聞名的檔案系統。**FSx for OpenZFS** 透過 NFS（v3、v4.0、v4.1、v4.2）提供給 Linux（以及 macOS、Windows 的 NFS client），特點是：

- 極低延遲（毫秒以下）與高 IOPS，適合對延遲敏感的小檔案工作負載。
- 瞬間 snapshot、可寫入的 clone、資料壓縮。
- 部署類型有 Single-AZ 與 Multi-AZ。

適合把地端的 ZFS 或一般 Linux NFS 伺服器原樣搬上雲，尤其是依賴 ZFS snapshot／clone 流程的開發、分析與資料庫測試環境。它和 EFS 都提供 NFS，差別在於：EFS 是無伺服器、自動擴展的多 AZ 檔案系統；OpenZFS 是需要配置容量與效能、但延遲更低、提供 ZFS 功能的檔案伺服器。

## 24.10 組起來：Wanderly 的區塊與檔案儲存版圖

三張工單處理完，小林把成長期的儲存架構畫成一張圖：

```text
                               ┌──────────────── 東京 Region ────────────────────────┐
  台北辦公室                    │                                                     │
  [財務/客服 PC]──SMB──┐        │  AZ 1a                        AZ 1c                │
  [AD 網域控制站]      │ DX ①  │  ┌─────────────────┐         ┌─────────────────┐   │
                       └────────┼─►│ FSx for Windows │◄═同步═► │ FSx standby     │   │
                                │  │ (preferred)     │  ②     │                 │   │
                                │  └─────────────────┘         └─────────────────┘   │
                                │  [web EC2 ×N]                 [web EC2 ×N]         │
                                │      │ NFS ③                      │ NFS            │
                                │      └────────► [EFS Regional] ◄──┘                │
                                │                  lifecycle → IA/Archive            │
                                │  [MySQL EC2]                                        │
                                │   └─ EBS gp3 6,000 IOPS ④                           │
                                │        └─ DLM 每 4 小時 snapshot ⑤ ─────────────────┼─► 新加坡：copy snapshot
                                │  [訓練節點 ×M] ── Lustre ⑥ ── [FSx Lustre scratch]  │
                                │                                    ⇅ data repository│
                                │                               [S3 訂房資料湖]        │
                                └─────────────────────────────────────────────────────┘
```

① 辦公室透過 Direct Connect 連到東京，FSx for Windows 加入辦公室的 AD。② Multi-AZ 部署在兩個 AZ 同步複寫，AZ 故障時自動切換。③ 所有 web server 掛載同一個 Regional EFS，素材不再需要 rsync；冷檔案由 lifecycle 自動降級。④ 自管 MySQL 使用 gp3，IOPS 與容量分開調整。⑤ DLM 依 tag 定期拍 snapshot，並複製到新加坡作為跨 Region 備份（真正的 DR 設計見第 34 章）。⑥ 訓練期間建立的 scratch Lustre 從 S3 延遲載入資料，結果寫回 S3。

## 24.11 比較與選型

### 服務總覽

| 服務 | 協定／介面 | Client | 可用範圍 | 共享 | 容量 | 代表特色 |
|---|---|---|---|---|---|---|
| EBS | Block | 單台 EC2（Multi-Attach 例外） | 單一 AZ | 否 | 預先配置 | gp3／io2／st1／sc1、snapshot |
| Instance store | Block | 單台 EC2 | 主機本身 | 否 | 固定 | 最高 I/O、非持久 |
| EFS | NFS v4 | Linux，可數千台 | Regional 或 One Zone | 是 | 自動擴縮 | lifecycle、access point、無伺服器 |
| FSx for Windows | SMB | Windows（也可 Linux／macOS） | Single-AZ 或 Multi-AZ | 是 | 預先配置 | AD、NTFS ACL、DFS |
| FSx for Lustre | Lustre | Linux HPC 節點 | 單一 AZ | 是 | 預先配置 | S3 整合、數百 GB/s |
| FSx for ONTAP | NFS、SMB、iSCSI | Linux、Windows、macOS | Single-AZ 或 Multi-AZ | 是 | 預先配置（含自動分層） | SnapMirror、FlexClone、多協定 |
| FSx for OpenZFS | NFS v3–v4.2 | Linux 為主 | Single-AZ 或 Multi-AZ | 是 | 預先配置 | 超低延遲、ZFS snapshot／clone |
| S3 | HTTP API | 任何程式 | Regional | 是（API） | 無上限 | 物件儲存，第 22、23 章 |

### 選型決策流程

```text
需要 block 裝置（自己格式化、單機資料庫、開機磁碟）？
├─ 是 → 資料可以丟、要最高本機 I/O？
│        ├─ 是 → instance store
│        └─ 否 → EBS：一般用 gp3；關鍵高 IOPS 用 io2；
│                 大型循序用 st1；冷循序最便宜用 sc1
│                 （叢集軟體要共享同一顆磁碟 → io2 Multi-Attach，同 AZ）
└─ 否，需要共享檔案系統 → 用什麼協定？
         ├─ SMB／Windows ACL／AD → FSx for Windows File Server
         ├─ 地端是 NetApp、或要 NFS+SMB+iSCSI 多協定 → FSx for NetApp ONTAP
         ├─ HPC／ML、要極高平行 throughput、資料在 S3 → FSx for Lustre
         ├─ 搬 ZFS／要求毫秒以下延遲的 NFS → FSx for OpenZFS
         └─ 一般 Linux 共享（網站、容器、Lambda）、免容量規劃 → EFS
如果只需要用 key 存取整個檔案、不需要掛載 → S3
```

## 24.12 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 一般 SSD、要獨立調 IOPS／throughput、比 gp2 便宜 | gp3（Elastic Volumes 原地修改） |
| 關鍵資料庫、持續高 IOPS、最高耐久度、毫秒以下延遲 | io2 Block Express |
| 大量循序讀取、日誌、資料倉儲、要便宜 | st1 |
| 很少存取的循序資料、最低成本 block | sc1（不能開機） |
| EBS 搬到另一個 AZ／Region | Snapshot → 新 AZ 建 volume；跨 Region 用 copy snapshot |
| 從 snapshot 還原後效能差 | Lazy loading；Fast Snapshot Restore 或預先讀取初始化 |
| Snapshot 長期保存、極少還原、最低成本 | EBS Snapshots Archive（至少 90 天、還原 24–72 小時） |
| 防止 snapshot／AMI 被誤刪 | Recycle Bin retention rule（可加 rule lock） |
| 既有未加密 volume 要加密 | Snapshot → 加密 copy／建立加密 volume → 替換；並開啟 encryption by default |
| 加密 snapshot 分享給另一帳號 | Customer managed key + key policy 授權對方 |
| 暫存、快取、可重建、最高 I/O | Instance store（stop／terminate 資料消失） |
| 多台 Linux、跨 AZ、共享檔案 | EFS（每 AZ 一個 mount target、SG 開 2049） |
| EFS 冷檔案降成本 | Lifecycle management → IA／Archive |
| 同一 EFS 給多個應用程式且互相隔離 | EFS access point + IAM |
| Windows、SMB、NTFS ACL、Active Directory | FSx for Windows File Server（Multi-AZ 高可用） |
| HPC、ML 訓練、資料在 S3、平行檔案系統 | FSx for Lustre（scratch 或 persistent） |
| NetApp、SnapMirror、NFS 與 SMB 同時 | FSx for NetApp ONTAP |
| ZFS、snapshot／clone、超低延遲 NFS | FSx for OpenZFS |

**常見陷阱**：

1. 以為 EBS 可以跨 AZ 掛載或自動跨 AZ 複寫：volume 綁定單一 AZ，跨 AZ 只能靠 snapshot 或應用層複寫。
2. 把 Multi-Attach 當成「多台共享檔案」的解法：它只限 io1／io2、同 AZ，且需要 cluster-aware 檔案系統；共享檔案請選 EFS／FSx。
3. 以為 EFS 能給 Windows 用：EFS 只支援 NFS，Windows 共享請用 FSx for Windows File Server。
4. 把唯一一份資料放在 instance store，或以為 stop／start 後資料還在。
5. 以為 EFS 的加密可以事後開啟：靜態加密只能在建立時決定，事後要建新檔案系統並搬資料。
6. 選 st1／sc1 當開機磁碟，或拿 HDD 跑隨機小 I/O 的交易資料庫。
7. 以為 FSx for Lustre 是多 AZ 的：它只在單一 AZ；scratch 型更是沒有複寫。

## 24.13 SAP 加深：跨 Region、跨帳號與大規模儲存治理

### EBS 的跨 Region DR 與還原時間

SAA 只要你知道「snapshot 可以跨 Region 複製」；SAP 會追問 RTO。一份在新加坡的 snapshot 要變成可服務的系統，時間花在三個地方：建立 volume 與 instance、從 S3 延遲載入資料（大型資料庫可能要數小時才達到正常效能）、應用程式的復原程序。若 RTO 只有數十分鐘，常見組合是：DLM 跨 Region 複製 snapshot，並對最新的 DR snapshot 啟用 FSR；或改用持續複寫的 **AWS Elastic Disaster Recovery**（第 34 章），把 RPO 降到秒級。加密的 snapshot 跨 Region 時，目的地必須有可用的 KMS key；若使用 multi-Region key 可以簡化金鑰管理（第 15 章）。

### 跨帳號備份隔離

為了防範帳號憑證外洩後攻擊者連備份一起刪除，企業常把 snapshot 複製到獨立的備份帳號：來源帳號用 customer managed key 加密並授權備份帳號，備份帳號複製後改用自己的 key 重新加密，從此不再依賴來源帳號。搭配 AWS Backup 的跨帳號 vault 與 vault lock（第 34、43 章），以及 Recycle Bin 的 rule lock，形成多層防誤刪、防竄改的保護。

### 大規模成本治理

當帳號數量成長到數十個，EBS 的浪費通常來自三個地方：

1. **gp2 遺留**：批次用 Elastic Volumes 把 gp2 改成 gp3，通常能在不影響效能的情況下立即降低儲存費用。
2. **未掛載的 volume 與孤兒 snapshot**：instance 刪了，data volume 因 DeleteOnTermination 為 false 而留下；舊 AMI 的 snapshot 沒人清理。用 AWS Config 規則、Trusted Advisor 或 Cost Explorer 找出來，配合 DLM 的保留政策自動清理。
3. **配置過大**：AWS Compute Optimizer 會根據實際 IOPS 與 throughput 建議更合適的 volume type 與配置。

### 混合與遷移情境的檔案系統選擇

SAP 題目常給一個「地端已經有某種儲存」的背景，要你選最小改動的遷移目標：

- 地端 NetApp：FSx for ONTAP 加 SnapMirror，可以先持續複寫、再在切換窗口一次轉過去，NetApp 團隊的工具與流程不變，也能保留 SnapMirror 作為長期的跨 Region DR。
- 地端 Windows 檔案伺服器：FSx for Windows File Server（Multi-AZ），用 DataSync 搬資料並保留 NTFS ACL，用 DFS namespace 讓使用者路徑不變（第 25 章）。
- 地端 Linux NFS：若需求是彈性、免管理容量，選 EFS；若依賴 ZFS 功能或極低延遲，選 FSx for OpenZFS。
- HPC 叢集的資料在地端：先把資料集搬到 S3（第 25 章），再用 FSx for Lustre 的 data repository association 掛到運算叢集。

> [!sap] SAP 加深
> 檔案系統選型的第一個問題永遠是「client 用什麼協定、依賴哪些既有功能」，而不是「哪個最便宜」。協定不相容的方案（例如把 SMB 使用者導到 EFS）需要改應用程式，在「最小改動遷移」的題目裡一定是錯的。

> [!note] 延伸閱讀
> - [Amazon EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
> - [Amazon EBS snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)
> - [Amazon EFS performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
> - [What is FSx for NetApp ONTAP?](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/what-is-fsx-ontap.html)

## 本章重點整理

- Block storage 由作業系統管理檔案系統，預設只能一台機器寫入；file storage 由服務端協調，讓多台 client 同時讀寫；object storage 用 API 以 key 存取整個物件。
- EBS volume 綁定單一 AZ、在 AZ 內自動複寫，生命週期獨立於 instance；效能同時受 volume 配置與 instance type 的 EBS 上限限制。
- gp3 讓容量、IOPS、throughput 分開設定且比 gp2 便宜，是預設首選；io2 Block Express 給關鍵高 IOPS 與 99.999% 耐久度；st1／sc1 是 HDD，只適合循序 I/O 且不能當開機磁碟。
- Elastic Volumes 可以線上修改 volume type、IOPS、throughput 與放大容量，但不能縮小，放大後要自行擴充檔案系統。
- EBS snapshot 是存在 S3 的增量備份，屬於 Regional，可在同 Region 任何 AZ 還原，也可以跨 Region 複製與跨帳號分享。
- 從 snapshot 還原的 volume 會延遲載入資料；需要立即完整效能時使用 Fast Snapshot Restore。
- 長期很少還原的 snapshot 移到 archive tier（至少 90 天、還原 24–72 小時）可省約 75%；Recycle Bin 讓被刪除的 snapshot 與 AMI 在保留期間內可以救回。
- EBS 加密同時保護靜態資料、傳輸中資料、snapshot 與衍生 volume；既有未加密 volume 要透過 snapshot 建立加密副本替換；跨帳號分享加密 snapshot 需要 customer managed key。
- Multi-Attach 只限 io1／io2、同一 AZ、最多 16 台 Nitro instance，而且需要 cluster-aware 檔案系統。
- Instance store 在 stop、hibernate、terminate 或主機故障時資料遺失，只能放可重建的資料。
- EFS 是 Linux 用的受管 NFS，每個 AZ 一個 mount target（SG 開 TCP 2049），Regional 型可承受 AZ 故障；Elastic throughput 與 General Purpose mode 是多數情境的起點。
- EFS lifecycle 依存取時間把檔案自動移到 IA 與 Archive，對應用程式透明；access point 強制 POSIX 身份與根目錄，適合多應用程式與 Lambda。
- FSx for Windows File Server 提供 SMB、NTFS ACL 與 AD 整合，Multi-AZ 部署會自動 failover。
- FSx for Lustre 是單 AZ 的高效能平行檔案系統，與 S3 整合；scratch 型便宜但不複寫，persistent 型在 AZ 內複寫。
- FSx for NetApp ONTAP 提供 NFS／SMB／iSCSI 多協定與 SnapMirror，FSx for OpenZFS 提供低延遲 NFS 與 ZFS snapshot／clone，兩者都是「原樣搬遷既有儲存」的首選。

## 本章練習題

### 練習 24-1｜SAA｜單選｜gp2 改 gp3 的成本與效能

Wanderly 的自管 MySQL 跑在一台 EC2 上，資料放在一顆 1,000 GiB 的 gp2 volume，實際只用了 600 GiB。監控顯示 volume 的 IOPS 長期卡在約 3,000，團隊評估需要穩定的 6,000 IOPS 與 250 MiB/s throughput。Instance type 的 EBS 上限足夠，而且資料庫不能停機。

哪個做法能以最低成本滿足需求？

- A. 用 Elastic Volumes 把 gp2 volume 放大到 2,000 GiB，讓基準 IOPS 提高到 6,000
- B. 用 Elastic Volumes 把 volume 原地改成 gp3，並配置 6,000 IOPS 與 250 MiB/s
- C. 建立 snapshot，從 snapshot 建立一顆配置 6,000 IOPS 的 io2 volume 並替換
- D. 把 volume 改成 st1，利用 HDD 較高的每 GB throughput 降低成本

> [!answer]- 答案：B
> **A ✗** 放大 gp2 確實能把基準 IOPS 提高到 6,000（每 GiB 3 IOPS），但要為用不到的 1,000 GiB 付費，而且 gp2 每 GB 單價本來就比 gp3 高，不是最低成本。
>
> **B ✓** gp3 的容量、IOPS、throughput 分開設定與計價，基準就有 3,000 IOPS 與 125 MiB/s，只需加購差額。Elastic Volumes 可以在掛載使用中修改，不需停機，而且 gp3 每 GB 單價較低。
>
> **C ✗** io2 能提供 6,000 IOPS，但 provisioned IOPS 單價遠高於 gp3，適合數萬 IOPS 或要求 99.999% 耐久度的系統；替換 volume 也需要停機切換。
>
> **D ✗** st1 是 HDD，處理資料庫的隨機小 I/O 非常差，會讓延遲更嚴重；它的優勢只在大型循序讀寫。
>
> **考點**：SAA-3.1、SAA-4.1｜gp3 獨立配置 IOPS 與 throughput

### 練習 24-2｜SAA｜單選｜循序 throughput 的 volume type

Wanderly 的資料團隊有一組 EC2 每天凌晨把前一天約 3 TB 的點擊日誌從頭到尾讀一次，產生彙總報表。讀取是大型循序 I/O，對單次操作延遲不敏感，資料放在 data volume 上（開機磁碟另外使用 gp3）。團隊希望在滿足每晚批次時間的前提下，把這顆 data volume 的成本降到最低。

應該選擇哪種 EBS volume type？

- A. io2 Block Express，因為它的 throughput 上限最高
- B. gp3，並把 throughput 配置到上限
- C. sc1，因為它是每 GB 最便宜的 EBS volume
- D. st1，因為它是為頻繁存取的大型循序 throughput 設計的 HDD

> [!answer]- 答案：D
> **A ✗** io2 的效能最高，但它是為高 IOPS、低延遲的關鍵資料庫設計，價格最高；循序日誌掃描用不到它的 IOPS 能力。
>
> **B ✗** gp3 可以完成工作，但 3 TB 的 SSD 加上額外購買的 throughput，成本高於專為循序工作設計的 HDD。
>
> **C ✗** sc1 每 GB 最便宜，但它是給「很少存取」的冷資料，baseline throughput 低；每天完整掃描 3 TB 的工作會被拖慢，可能趕不上批次時間。
>
> **D ✓** st1 是 throughput optimized HDD，效能以 MiB/s 計並隨容量增加，正好適合頻繁的大型循序讀取，成本遠低於 SSD。題目把開機磁碟另外處理，也避開了 HDD 不能開機的限制。
>
> **考點**：SAA-3.1、SAA-4.1｜st1 vs sc1 vs SSD 選型

### 練習 24-3｜SAA｜單選｜把 EBS 資料移到另一個 AZ

一台位於 `ap-northeast-1a` 的 EC2 掛著一顆 500 GiB 的 gp3 data volume。因為 1a 的某個 instance type 容量不足，團隊決定在 `ap-northeast-1c` 啟動新的 instance，並使用同一份資料。可以接受短暫停機。

應如何把資料帶到 1c？

- A. 停止應用程式後對 volume 建立 snapshot，從 snapshot 在 1c 建立新 volume，再掛到 1c 的 instance
- B. 把 volume 從 1a 的 instance detach，直接 attach 到 1c 的新 instance
- C. 對 volume 啟用 Multi-Attach，同時掛到 1a 與 1c 的 instance 後再移除舊的
- D. 把 snapshot 複製到 1c，因為 snapshot 和 volume 一樣屬於建立時的 AZ

> [!answer]- 答案：A
> **A ✓** EBS volume 綁定單一 AZ，但 snapshot 存放在 Regional 的 S3 中，可以在同 Region 任何 AZ 建立新 volume。先停止寫入再拍 snapshot，可以得到一致的資料。
>
> **B ✗** Volume 只能掛到同一個 AZ 的 instance，無法跨 AZ attach。
>
> **C ✗** Multi-Attach 只支援 io1／io2，而且所有 instance 必須在同一個 AZ，不能用來跨 AZ。
>
> **D ✗** Snapshot 是 Regional 資源，不屬於某個 AZ，也不需要「複製到 AZ」；跨 Region 才需要 copy snapshot。
>
> **考點**：SAA-2.2、SAA-3.1｜EBS 的 AZ 範圍與 snapshot

### 練習 24-4｜SAA｜單選｜Instance store 的資料遺失

一位工程師把影像轉檔的暫存檔和「轉檔完成清單」都寫在一台 `c6gd` instance 的 instance store 上。週末維運時，他把 instance stop 後再 start，發現暫存檔與清單都不見了，但 instance 的作業系統與程式都正常。

下列哪個說明與改善方式最正確？

- A. Instance store 的資料只會在 reboot 時消失；應改用 stop 來保留資料
- B. Instance store 會自動拍 snapshot 到 S3，應從最近的 snapshot 還原清單
- C. Instance store 在 stop 時資料就會遺失；暫存檔可以留在 instance store，但唯一的完成清單應改存在 EBS、S3 或資料庫等持久儲存
- D. 應把 instance store 改成 Multi-Attach，讓資料同時存在兩台 instance 上

> [!answer]- 答案：C
> **A ✗** 說反了。Reboot 時 instance store 資料會保留；stop、hibernate、terminate 或主機故障時才會遺失。
>
> **B ✗** Instance store 不支援 snapshot，AWS 也不會替它備份。
>
> **C ✓** Stop／start 通常會換到另一台實體主機，原主機上的 instance store 資料就消失了；作業系統還在是因為 root volume 是 EBS。暫存檔可重建，適合放在高效能的 instance store；不可遺失的狀態必須放在持久儲存。
>
> **D ✗** Multi-Attach 是 io1／io2 EBS volume 的功能，instance store 沒有這個選項。
>
> **考點**：SAA-2.2、SAA-3.1｜instance store 的生命週期

### 練習 24-5｜SAA｜選兩項｜EFS 跨 AZ 掛載與安全

Wanderly 的 CMS 跑在兩個 AZ 的 private subnet，Auto Scaling 中的 Linux instance 都要掛載同一個 EFS 檔案系統。要求是：任一 AZ 故障時另一個 AZ 仍能讀寫、流量不經過 Internet、只有 CMS instance 能連到檔案系統。

哪兩個設定是必要的？（選兩項）

- A. 建立 Regional EFS，並在兩個 AZ 各建立一個 mount target
- B. 只在第一個 AZ 建立 mount target，另一個 AZ 的 instance 透過 NAT Gateway 連過去
- C. 在 EFS 前面放一個 Network Load Balancer，把 NFS 流量分散到兩個 AZ
- D. Mount target 的 security group 只允許來自 CMS instance security group 的 TCP 2049 入站
- E. 把 EFS 改成 One Zone，讓兩個 AZ 的 instance 都跨 AZ 掛載以節省費用

> [!answer]- 答案：A、D
> **A ✓** Regional EFS 把資料跨多個 AZ 保存；每個 AZ 一個 mount target，讓該 AZ 的 instance 有本地的連線入口，一個 AZ 故障時另一個 AZ 仍可正常存取。
>
> **B ✗** 單一 mount target 讓所有流量依賴第一個 AZ，該 AZ 故障時另一邊也無法存取；而且 mount target 是 VPC 內的 ENI，不需要也不應該經過 NAT。
>
> **C ✗** EFS 本身就是跨 AZ 的受管服務，client 透過 DNS 連到同 AZ 的 mount target，不需要也不支援在前面放 NLB 做分流。
>
> **D ✓** NFS 使用 TCP 2049。在 mount target 的 security group 只允許 CMS 的 security group 作為來源，就能限制只有 CMS instance 能連線。
>
> **E ✗** One Zone 只把資料存在一個 AZ，該 AZ 故障時整個檔案系統不可用，違反高可用需求。
>
> **考點**：SAA-2.2、SAA-1.2｜EFS mount target 與 security group

### 練習 24-6｜SAA｜單選｜EFS 冷檔案降成本

Wanderly 使用 Elastic throughput 的 Regional EFS 存放 5 TB 歷年旅遊專題的素材檔（多數檔案為數 MB 的圖片與影片）。分析顯示約 85% 的檔案超過 60 天沒有人讀取，但偶爾仍會有編輯打開舊專題，此時要能直接以原路徑開啟，不能要求等待數小時。團隊希望不修改應用程式就降低儲存成本。

最合適的做法是什麼？

- A. 寫一支排程程式，把 60 天沒讀取的檔案搬到 S3 Glacier Deep Archive，並在原處留下捷徑
- B. 啟用 EFS lifecycle management，把一段時間未存取的檔案移到 Infrequent Access 或 Archive storage class，並設定被存取後移回 Standard
- C. 把 throughput mode 從 Elastic 改成 Bursting，以降低每月費用
- D. 把檔案系統改成 Max I/O performance mode，以降低每 GB 的儲存費用

> [!answer]- 答案：B
> **A ✗** Deep Archive 需要先取回、通常要數小時以上，違反「直接開啟、不能等待」的需求，也需要修改應用程式或流程。
>
> **B ✓** EFS lifecycle 依存取時間自動在 storage class 之間搬移檔案，對應用程式完全透明，路徑不變，IA 與 Archive 的檔案可以直接讀取（另收存取費）。大量冷檔案移到低價 storage class 能大幅降低成本。
>
> **C ✗** Throughput mode 影響的是頻寬計費方式，與儲存費用無關；Bursting 在小檔案系統上還可能因 credit 耗盡而變慢。
>
> **D ✗** Performance mode 不影響儲存單價，而且建立後無法修改；Max I/O 還會增加每次操作的延遲。
>
> **考點**：SAA-4.1｜EFS lifecycle 與 storage classes

### 練習 24-7｜SAA｜單選｜Windows 檔案共享

Wanderly 的客服部門有 200 位使用者透過 Windows 檔案總管存取共享資料夾，權限由公司的 Active Directory 群組控制，部分資料夾還使用了 shadow copies 讓使用者自行還原舊版。公司要把這台地端檔案伺服器搬到 AWS，要求維持 SMB 存取與既有 NTFS 權限，並能承受單一 AZ 故障，營運負擔要最低。

應選擇哪個方案？

- A. 建立 Regional EFS，讓 Windows client 安裝 NFS client 掛載
- B. 在兩個 AZ 各建立一台 EC2 Windows Server 檔案伺服器，用 DFS Replication 自行同步
- C. 使用 S3 搭配 S3 File Gateway 提供 SMB share，以 bucket policy 取代 NTFS 權限
- D. 建立 Multi-AZ 的 FSx for Windows File Server，加入公司的 Active Directory

> [!answer]- 答案：D
> **A ✗** EFS 只支援 NFS，Windows 原生不支援以這種方式使用 EFS，也無法提供 NTFS ACL、AD 驗證與 shadow copies。
>
> **B ✗** 自建兩台 Windows 檔案伺服器加 DFS Replication 技術上可行，但需要自己 patch、備份、監控與處理故障切換，營運負擔遠高於受管服務。
>
> **C ✗** S3 File Gateway 是給地端存取 S3 用的混合式閘道，物件權限模型與 NTFS ACL 不同，無法完整保留既有權限，也不是在 AWS 內提供高可用檔案伺服器的方案。
>
> **D ✓** FSx for Windows File Server 提供 SMB、NTFS ACL、AD 整合與 shadow copies；Multi-AZ 部署在兩個 AZ 同步複寫並自動 failover，由 AWS 管理底層 Windows Server。
>
> **考點**：SAA-2.2、SAA-3.1｜FSx for Windows File Server Multi-AZ

### 練習 24-8｜SAA｜單選｜ML 訓練的高效能暫存檔案系統

Wanderly 的資料科學團隊每週一次用 64 台 GPU instance 訓練定價模型。訓練資料約 40 TB，存放在 S3；訓練過程需要所有節點以 POSIX 檔案路徑高並行讀取，訓練中的中間檔可以重建，最終模型要寫回 S3。訓練約持續 10 小時，團隊希望效能最高且成本最低。

最合適的儲存方案是什麼？

- A. 每次訓練前建立 scratch 型 FSx for Lustre，設定連到訓練資料所在 S3 prefix 的 data repository association，訓練完把結果匯出到 S3 後刪除檔案系統
- B. 建立一個 Multi-AZ 的 FSx for Windows File Server，讓 GPU 節點以 SMB 掛載
- C. 建立 Regional EFS 並使用 Provisioned throughput，先把 40 TB 從 S3 複製進去
- D. 每台 GPU instance 掛一顆 io2 volume，各自從 S3 下載完整的 40 TB 資料

> [!answer]- 答案：A
> **A ✓** FSx for Lustre 是為 HPC／ML 設計的平行檔案系統，提供極高的總 throughput；data repository association 讓 S3 物件以檔案形式出現並延遲載入，結果可匯出回 S3。中間檔可重建、使用期短，scratch 型成本最低。
>
> **B ✗** FSx for Windows File Server 提供 SMB 給 Windows 使用者共享，不是為數十台 Linux GPU 節點的高並行讀取設計，也沒有 S3 整合。
>
> **C ✗** EFS 可以共享，但要先把 40 TB 完整複製進去，且長期按儲存量計費；平行 throughput 也不如 Lustre，成本與效能都不是最佳。
>
> **D ✗** 每台都下載 40 TB 會產生 64 份重複資料與大量 io2 費用，也失去共享檔案系統的意義。
>
> **考點**：SAA-3.1、SAA-3.5｜FSx for Lustre scratch 與 S3 整合

### 練習 24-9｜SAA｜單選｜既有未加密 volume 改為加密

一次安全稽核發現，Wanderly 有一顆仍在使用中的未加密 EBS data volume，存放會員上傳的身份文件。安全團隊要求這份資料必須以 KMS 加密，並確保之後這個 Region 新建的 volume 都不會再漏掉加密。可以接受一個短暫的維護窗口。

應該怎麼做？

- A. 在 volume 上直接啟用加密屬性，EBS 會在背景加密既有資料
- B. 開啟 EBS encryption by default，既有 volume 會在下一次 reboot 時自動加密
- C. 對 volume 建立 snapshot，從 snapshot 建立加密的新 volume，在維護窗口把舊 volume 替換掉；另外在該 Region 開啟 EBS encryption by default
- D. 在作業系統內用檔案層級工具加密每個檔案，並保留未加密的 volume

> [!answer]- 答案：C
> **A ✗** EBS 不支援原地加密既有的未加密 volume，加密只能在建立 volume 時決定。
>
> **B ✗** Encryption by default 只影響之後新建的 volume 與 snapshot copy，不會回頭加密既有 volume，reboot 也不會改變。
>
> **C ✓** 標準流程是 snapshot → 建立加密 volume（或先加密複製 snapshot）→ 替換。之後開啟 encryption by default，確保同一 Region 新建的 volume 一律加密。
>
> **D ✗** 作業系統層加密需要自行管理金鑰與工具，也沒有滿足「以 KMS 加密 EBS」的要求；snapshot 與 volume 本身仍未加密。
>
> **考點**：SAA-1.3｜EBS 加密只能在建立時決定

### 練習 24-10｜SAA｜單選｜還原後立即達到完整效能

Wanderly 每天凌晨從 production 資料庫的最新 snapshot 建立 10 顆 volume，供 10 套壓力測試環境使用。測試團隊抱怨每次環境剛建好的前兩小時，資料庫查詢比正式環境慢很多，壓測數字失真。團隊希望環境建立後就有完整效能，且不想手動預先讀取所有區塊。

最合適的做法是什麼？

- A. 把 volume type 改成 io2，因為 io2 從 snapshot 還原時沒有延遲載入
- B. 對每天要使用的 snapshot，在測試環境所在的 AZ 啟用 Fast Snapshot Restore
- C. 改從 EBS Snapshots Archive 還原，因為封存層存放的是完整 snapshot
- D. 把 snapshot 複製到另一個 Region 後再從那裡建立 volume

> [!answer]- 答案：B
> **A ✗** 不論 volume type，從 snapshot 建立的 volume 都會在第一次讀取區塊時從 S3 延遲載入；換成 io2 只增加成本，不解決 first-touch latency。
>
> **B ✓** Fast Snapshot Restore 針對指定 snapshot 與 AZ 啟用後，從它建立的 volume 一開始就是完全初始化的狀態，立刻有完整效能，不需要預先讀取。
>
> **C ✗** Archive tier 的 snapshot 必須先花 24–72 小時還原回標準層才能使用，更不可能解決效能問題。
>
> **D ✗** 跨 Region 複製與延遲載入無關，只會增加時間與傳輸成本。
>
> **考點**：SAA-3.1｜Fast Snapshot Restore

### 練習 24-11｜SAP｜選兩項｜Snapshot 長期保存與防誤刪

Wanderly 已成長到 30 個帳號，法規要求每個月的訂單資料庫 snapshot 要保存 7 年，但這些 snapshot 幾乎不會被還原；若真的要還原，可以接受等待 3 天。過去也發生過工程師執行清理腳本誤刪 snapshot 的事故。財務希望降低 snapshot 成本，安全團隊希望誤刪的 snapshot 能在 14 天內救回，而且規則本身不能被輕易修改。

哪兩個做法最合適？（選兩項）

- A. 把每月 snapshot 轉成 AMI 並分享給所有帳號，讓任何帳號都保留一份
- B. 為每月 snapshot 啟用 Fast Snapshot Restore，確保需要時能立即還原
- C. 用 Data Lifecycle Manager 或 AWS Backup 的政策，把每月 snapshot 自動移到 EBS Snapshots Archive
- D. 每月把 snapshot 複製到另一個 Region 的同一帳號，以降低儲存單價
- E. 建立 Recycle Bin retention rule 保留被刪除的 snapshot 14 天，並啟用 rule lock

> [!answer]- 答案：C、E
> **A ✗** 在多個帳號重複保存同一份資料會增加成本，並擴大可存取正式資料的範圍，也沒有防止誤刪的機制。
>
> **B ✗** FSR 依 snapshot、AZ 與時數計費，是給「立刻要完整效能」的情境；對幾乎不還原、可等 3 天的合規 snapshot 只會大幅增加成本。
>
> **C ✓** Archive tier 適合長期保存、極少還原的 snapshot，儲存成本約便宜 75%；還原需要 24–72 小時，在可接受的 3 天內。7 年的保存期也遠超過 90 天最短期限。
>
> **D ✗** 跨 Region 複製會額外產生傳輸與第二份儲存費用，不會降低單價；同帳號的副本也無法防範同一份清理腳本或憑證誤刪。
>
> **E ✓** Recycle Bin 讓被刪除的 snapshot 在保留期間內可以復原；rule lock 防止有人先修改或刪除規則再刪資源，滿足「規則不能被輕易修改」。
>
> **考點**：SAP-1.5、SAP-2.2｜Snapshot archive 與 Recycle Bin

### 練習 24-12｜SAP｜單選｜加密 snapshot 的跨帳號 DR 複本

Wanderly 的安全規範要求把 production 帳號的 EBS snapshot 複製到獨立的 backup 帳號，以防 production 帳號憑證外洩時備份被一併刪除。目前所有 volume 都以 AWS managed key `aws/ebs` 加密。備份工程師嘗試把 snapshot 分享給 backup 帳號時失敗。

最合適的修正方式是什麼？

- A. 在 `aws/ebs` 的 key policy 中加入 backup 帳號，再分享 snapshot
- B. 把 snapshot 解密後以未加密形式分享，backup 帳號複製時再加密
- C. 把 snapshot 公開分享，backup 帳號複製後立即取消公開
- D. 在 production 帳號建立 customer managed key 並在 key policy 授權 backup 帳號使用；用此 key 重新加密複製 snapshot 後分享，backup 帳號再以自己的 key 複製一份

> [!answer]- 答案：D
> **A ✗** AWS managed key 的 key policy 由 AWS 管理，無法修改，因此以 `aws/ebs` 加密的 snapshot 無法分享給其他帳號。
>
> **B ✗** 加密 snapshot 無法轉成未加密；而且在流程中產生未加密副本也違反安全規範。
>
> **C ✗** 加密 snapshot 不能公開分享；即使是未加密 snapshot，公開分享正式資料也是嚴重的安全風險。
>
> **D ✓** 跨帳號分享加密 snapshot 需要 customer managed key，並在 key policy 授權對方帳號。Backup 帳號再用自己帳號的 key 複製，之後就不再依賴 production 帳號的 key，即使 production 帳號被入侵也無法影響這份備份。
>
> **考點**：SAP-2.2、SAP-2.3｜加密 snapshot 跨帳號分享與 KMS

### 練習 24-13｜SAP｜單選｜叢集軟體需要共享 block 裝置

Wanderly 併購的旅行社有一套舊的訂位系統，運作在兩台 Linux 伺服器組成的 active-passive 叢集上，兩台共享同一顆磁碟並使用 GFS2 叢集檔案系統與 fencing 機制。團隊要以最小改動 rehost 到 AWS，兩台 instance 會放在同一個 AZ，系統需要穩定的高 IOPS。

最合適的儲存設計是什麼？

- A. 使用一顆 io2 volume 並啟用 Multi-Attach，同時掛載到同一 AZ 的兩台 Nitro instance，沿用 GFS2 與 fencing 設定
- B. 使用一顆 gp3 volume 並啟用 Multi-Attach，同時掛到兩台 instance
- C. 改用 EFS 並把兩台 instance 放到不同 AZ，GFS2 會自動轉換成 NFS
- D. 為兩台 instance 各掛一顆 io2 volume，靠 EBS 在兩顆 volume 間自動同步

> [!answer]- 答案：A
> **A ✓** Multi-Attach 讓一顆 io1／io2 volume 同時掛到同一 AZ 最多 16 台 Nitro instance，正好符合「共享磁碟 + cluster-aware 檔案系統」的既有架構。GFS2 與 fencing 負責協調寫入，EBS 只提供共享區塊。
>
> **B ✗** Multi-Attach 不支援 gp3，只支援 provisioned IOPS SSD（io1／io2）。
>
> **C ✗** EFS 是 NFS 檔案服務，不是 block 裝置，GFS2 不會自動轉換；改成 EFS 需要修改叢集設計，不符合最小改動。
>
> **D ✗** EBS 不會在兩顆獨立 volume 之間同步資料；這需要應用層或作業系統層的複寫。
>
> **考點**：SAP-4.2、SAA-3.1｜EBS Multi-Attach 的適用條件

### 練習 24-14｜SAP｜選兩項｜NetApp 儲存遷移

被併購的旅行社資料中心有一套 NetApp ONTAP 儲存，約 120 TB，同一份資料同時以 NFS 提供給 Linux 應用、以 SMB 提供給 Windows 使用者；儲存團隊每天用 SnapMirror 複寫到另一個機房做 DR，並用 FlexClone 建立測試環境。公司要在三個月內把它搬到 AWS，要求切換停機最短、儲存團隊的工具與流程盡量不變，搬遷後還要有跨 Region DR。

哪兩個做法最合適？（選兩項）

- A. 建立 Regional EFS，用 DataSync 把資料搬過去，再讓 Windows 使用者改用 NFS client
- B. 建立 Multi-AZ 的 FSx for NetApp ONTAP，同時提供 NFS 與 SMB，並使用 FlexClone 建立測試環境
- C. 把資料拆成兩份：Linux 部分搬到 EFS、Windows 部分搬到 FSx for Windows File Server
- D. 用 SnapMirror 從地端 NetApp 持續複寫到 FSx for ONTAP，切換窗口只需同步最後的變更；之後再設定 SnapMirror 到另一個 Region 的 FSx for ONTAP 作為 DR
- E. 把資料匯出到 S3，再用 FSx for Lustre 的 data repository association 提供給兩種 client

> [!answer]- 答案：B、D
> **A ✗** EFS 只支援 NFS，Windows 使用者要改用 NFS 不實際，也失去 NetApp 的 FlexClone、SnapMirror 等功能，違反「工具與流程不變」。
>
> **B ✓** FSx for ONTAP 提供完整 ONTAP 功能，同一份資料可同時以 NFS 與 SMB 存取，FlexClone 也能照舊使用；Multi-AZ 部署提供 Region 內的高可用。
>
> **C ✗** 拆成兩個服務會讓原本共用的同一份資料分裂成兩份，需要改應用程式並自行同步，複雜度高。
>
> **D ✓** SnapMirror 是儲存團隊熟悉的工具，可以先持續複寫大部分資料，切換時只同步最後的差異，停機最短；遷移後再用 SnapMirror 跨 Region 複寫，滿足 DR 需求。
>
> **E ✗** FSx for Lustre 是給 Linux HPC 的平行檔案系統，不支援 SMB，也沒有 NetApp 的資料管理功能。
>
> **考點**：SAP-4.2、SAP-2.2｜FSx for ONTAP 與 SnapMirror 遷移

### 練習 24-15｜SAP｜單選｜EFS 的跨 Region DR

Wanderly 的行程文件服務在東京運行，所有 container 共用一個 Regional EFS 存放使用者產生的行程 PDF。DR 要求為：東京整個 Region 故障時，能在新加坡恢復服務，RPO 不超過 1 小時、RTO 不超過 2 小時，且平時營運負擔要低。

最合適的做法是什麼？

- A. 每天用 AWS Backup 備份 EFS，並把 recovery point 複製到新加坡，災難時再還原
- B. 在新加坡建立一個 One Zone EFS，讓東京的 container 同時跨 Region 寫入兩個檔案系統
- C. 設定 EFS replication 把檔案系統複寫到新加坡；災難時刪除 replication 設定，讓新加坡的檔案系統變成可寫入，再在新加坡啟動服務並掛載它
- D. 在東京的 EFS 上啟用 lifecycle management，讓 Archive storage class 的檔案自動複製到新加坡

> [!answer]- 答案：C
> **A ✗** 每日備份的 RPO 最長接近 24 小時，超過 1 小時的要求；從備份還原大量檔案的時間也可能超過 RTO。備份應該保留，但用來防誤刪，不是滿足這組 RPO 的主要手段。
>
> **B ✗** 讓應用程式跨 Region 雙寫需要修改程式並處理寫入失敗與不一致，營運負擔高；One Zone 也降低了新加坡端的可用性。
>
> **C ✓** EFS replication 持續把變更複寫到目的 Region，RPO 設計目標為 15 分鐘。目的地平時是唯讀的，failover 時刪除 replication 設定即可寫入，符合 RPO 與 RTO，且是受管功能、營運負擔低。
>
> **D ✗** Lifecycle 只在同一個檔案系統內搬移 storage class，不會產生任何跨 Region 副本。
>
> **考點**：SAP-2.2、SAP-3.4｜EFS replication 跨 Region DR

### 練習 24-16｜SAP｜單選｜多租戶共用 EFS 的隔離

Wanderly 推出給旅行社使用的 SaaS 報表功能：每個租戶的報表由 Lambda 產生並寫到 EFS，同一個 EFS 檔案系統要服務 300 個租戶。安全要求是：每個租戶的 Lambda 只能看到自己的目錄、即使程式有 bug 也不能以其他 UID 寫檔，而且不能為每個租戶維護一個檔案系統。

最合適的設計是什麼？

- A. 為每個租戶建立一個 mount target，並用不同的 security group 區隔
- B. 在 Lambda 程式中檢查租戶 ID，只在對應目錄下讀寫，並把所有目錄權限設為 777 以避免權限錯誤
- C. 為每個租戶建立 EFS access point，設定其根目錄為該租戶的目錄並強制指定的 POSIX UID／GID；在 file system policy 中限制每個租戶的 Lambda role 只能透過自己的 access point 掛載
- D. 改為每個租戶各用一顆 EBS volume，以 Multi-Attach 掛給該租戶的 Lambda

> [!answer]- 答案：C
> **A ✗** 每個 AZ 只能有一個 mount target，無法為 300 個租戶各建一個；security group 也只能控制網路連線，不能限制目錄。
>
> **B ✗** 只靠程式邏輯檢查，一旦有 bug 就能存取其他租戶的資料；777 權限更是讓所有人都能讀寫，違反安全要求。
>
> **C ✓** Access point 強制根目錄與 POSIX 身份：透過它掛載的 client 看到的 `/` 就是租戶目錄，所有操作都以指定 UID／GID 執行，程式無法越界。File system policy 搭配 IAM 條件，限制每個 Lambda role 只能使用自己的 access point。Lambda 掛載 EFS 本來就必須透過 access point。
>
> **D ✗** Lambda 不能掛載 EBS volume；Multi-Attach 也只適用於同 AZ 的 Nitro EC2 instance。
>
> **考點**：SAP-2.3、SAP-3.2｜EFS access point 與 IAM 的多租戶隔離
