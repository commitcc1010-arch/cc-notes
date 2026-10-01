# P04 Audit：第 41–51 章 Storage / Data Architecture

稽核日期：2026-10-01
範圍：第 41–51 章現有章內題庫。本文只定義原創題目的「命題 intent」，不收錄、改寫或推測任何真實考題／exam dump。

## 共通稽核結論

- 第 41 章有 5 題手寫題；第 42–51 章則由同一個五題模板生成。模板固定為選型、設定、機制、最少營運負擔、企業治理，造成題幹與正解反覆重述 `topic.decision` 或 component profile。
- 多數題目不是一個可判分的 scenario，而是把整章摘要直接放進正解；讀者只需辨認最完整、最長的選項，不必理解 access semantics、consistency、failure mode 或 trade-off。
- 通用干擾項如「自動理解 business requirements」「全部服務都部署」「等故障後人工處理」過度荒謬，不能區分真正理解與猜題能力。
- 多個「底層機制」題同時放入兩段正確敘述，只因題幹點名 primary component 才勉強維持單選；第 46、47 章尤其接近多重正解。
- 除第 41 章少數 policy 題外，現況缺少可實際推理的 policy、resource scope、consistency window、replication lag、restore path、capacity unit、failover endpoint 與資料模型。
- 每章應改為以下恰好 10 個互不重疊 intent。實作時每個 intent 只生成一題；每題的三個 distractors 應保留合理前提，但違反題目中的一個明確 constraint。

任務代碼沿用專案中的 SAA-C03 / SAP-C02 task mapping；`Source` 一律指向 AWS 官方文件，而非第三方題庫。

---

## 第 41 章：S3 Object Model、Consistency 與 Security

### 現有題目缺陷

- 現有 5 題中有 3 題集中在 authorization；沒有直接測 strong consistency、versioning、replication、SSE-KMS、Object Lock、multipart upload 或 checksum。
- 第 4 題其實主要考 EFS/POSIX，對 S3 object semantics 的判斷只停在「不是檔案系統」。
- 第 1 題把 cross-account 的雙邊 Allow 說成唯一完整模型，但沒有區分直接 bucket policy 授權、AssumeRole、SCP、VPC endpoint policy 與 KMS key policy。
- 第 3 題只測 CloudFront OAC，不能代表一般 S3 private access、presigned URL 或 VPC endpoint。
- 第 5 題是合理 SAP 題，但仍缺 access point policy 與 bucket policy 的共同評估、KMS encryption context、replication role等深度。

### 10 個原創、非重疊 intents

1. **Object API 與 POSIX 語意**
   - Intent：應用必須 append、rename directory、advisory locking；判斷不能因 S3 容量大就把它當共享磁碟。
   - Correct principle：S3 以 bucket/key 及完整 object 的 HTTP operations 存取；需要共享檔案語意時選 EFS/FSx，單機 block device 才考慮 EBS。
   - Distractors：(1) S3 prefix 等同可原子 rename 的 directory；(2) multipart upload 可提供任意 offset 的 in-place write；(3) S3 strong consistency 等同完整 POSIX semantics。
   - Level / Task / Source：SAA｜SAA-3.1｜[S3 overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)

2. **Strong consistency 的真正邊界**
   - Intent：PUT 後立即 GET/LIST 必須看見新值，但跨兩個 keys 的更新不可暴露半完成狀態。
   - Correct principle：成功的 S3 PUT/DELETE 及後續 GET/LIST 具 strong read-after-write consistency；這不提供跨 object transaction，應以 manifest、versioned pointer 或 application protocol 發布一組資料。
   - Distractors：(1) 新 object strong、overwrite 仍 eventual；(2) LIST 永遠 eventual，需固定等待；(3) strong consistency 可讓多 object 更新自動 atomic。
   - Level / Task / Source：SAA → SAP｜SAA-3.1、SAP-2.4｜[S3 data consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel)

3. **Cross-account authorization 與 resource scope**
   - Intent：Account A role 讀取 Account B 的特定 prefix，並允許列出該 prefix。
   - Correct principle：來源 principal 必須有 `s3:GetObject`/`s3:ListBucket` 權限，目的端必須信任或直接授權該 principal；`ListBucket` 使用 bucket ARN 加 `s3:prefix`，`GetObject` 使用 object ARN。若使用 SSE-KMS，還要通過 KMS authorization。
   - Distractors：(1) 只在 A 帳號附 AdministratorAccess；(2) 只允許來源 CIDR 即完成 identity authorization；(3) 對 `ListBucket` 使用 `bucket/*`、對 `GetObject` 使用 bucket ARN。
   - Level / Task / Source：SAA → SAP｜SAA-1.3、SAP-2.3｜[S3 bucket policy examples](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html)

4. **Object Ownership、ACL 與 Block Public Access**
   - Intent：多帳號上傳物件後，bucket owner 必須一致擁有並集中以 policy 治理。
   - Correct principle：使用 Bucket owner enforced 停用 ACL，並保留 account/bucket 層 Block Public Access；具名 cross-account access 使用 IAM、bucket/access point policy，而不是關閉 BPA。
   - Distractors：(1) 每個 uploader 以 object ACL 授予 bucket owner full control 作為首選；(2) 關閉 BPA 才能做任何 cross-account access；(3) bucket 名稱難猜即可安全公開。
   - Level / Task / Source：SAA｜SAA-1.3｜[Controlling ownership of objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html)

5. **SSE-S3、SSE-KMS 與雙重政策邊界**
   - Intent：敏感 object 必須使用 customer managed KMS key，只有指定 role 能解密，且需控制 KMS request 成本。
   - Correct principle：設定 SSE-KMS/customer managed key；caller 同時需要 S3 與 KMS 權限，key policy/grant 也必須允許；S3 Bucket Key 可降低 KMS request traffic，但不取代 key policy。
   - Distractors：(1) bucket policy 的 `s3:GetObject` 會自動授予 `kms:Decrypt`；(2) SSE-S3 可用 customer managed key policy 限制個別 role；(3) TLS 只保護傳輸，因此啟用 TLS 後無需 at-rest encryption。
   - Level / Task / Source：SAA → SAP｜SAA-1.3、SAP-2.3｜[Using server-side encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/serv-side-encryption.html)

6. **Same-Region / Cross-Region Replication 的先決條件**
   - Intent：將合規資料自動複寫到另一帳號與 Region，包含既有 SSE-KMS objects。
   - Correct principle：source/destination 開啟 versioning，建立 replication IAM role 與 destination permissions；SSE-KMS objects 需明確 opt in 並授權 source/destination KMS keys。Replication 為非同步，既有 objects 要另用 Batch Replication。
   - Distractors：(1) 開啟 CRR 後自動同步所有既有 objects；(2) replication 是同步 commit，可宣稱零 RPO；(3) versioning 關閉仍可建立標準 replication rule。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.3｜[S3 replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)

7. **Versioning、delete marker 與可恢復性**
   - Intent：使用者誤刪或覆寫 object，要求快速恢復，同時控制 noncurrent versions 成本。
   - Correct principle：Versioning 保存版本；一般 DELETE 會建立 delete marker，可移除 marker 或指定 version 恢復。Lifecycle 應分別處理 current、noncurrent versions 與 expired delete markers。
   - Distractors：(1) versioning 是另一 Region 的備份；(2) 啟用 versioning 後舊版本不計費；(3) lifecycle expiration 永遠可逆且不會永久刪除 version。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-4.1｜[Using versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)

8. **Presigned URL 的權限與有效期**
   - Intent：未登入 AWS 的客戶只能在短時間下載單一 object。
   - Correct principle：由具備該 object 權限的 principal 產生 presigned URL；URL 權限不超過簽署者且受簽署 credentials 有效期限制。它不是 object 永久公開設定。
   - Distractors：(1) presigned URL 可繞過所有 explicit deny；(2) 建立 URL 後即使 signing credentials 到期仍依指定期限有效；(3) 必須先對 bucket 設 public-read。
   - Level / Task / Source：SAA｜SAA-1.1、SAA-1.3｜[Sharing objects with presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)

9. **大型 object 上傳、parallelism 與 integrity**
   - Intent：跨洲上傳 200 GB object，需要重試局部失敗並驗證內容完整性。
   - Correct principle：使用 multipart upload 並行上傳 parts、僅重送失敗 part，完成時組合 object；配合 supported checksums 驗證 integrity，並用 lifecycle abort incomplete multipart uploads。
   - Distractors：(1) 單次 PUT 可無限制上傳且失敗只重送壞掉區段；(2) 增加隨機 prefix 才能解除現代 S3 的固定 prefix throughput ceiling；(3) ETag 在所有 encryption/multipart 情境都必然是整個 object 的 MD5。
   - Level / Task / Source：SAA｜SAA-3.1、SAA-4.1｜[S3 performance guidelines](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance-guidelines.html)

10. **Object Lock、retention 與 backup 的差別**
    - Intent：法規要求 WORM、指定 retention 內任何一般管理者都不能刪除，但仍要有 Region 災難復原。
    - Correct principle：在 versioned bucket 使用 Object Lock retention/legal hold；Compliance mode 與 Governance mode權限不同。Object Lock 解決不可變性，不自動提供跨 Region recovery，仍需規劃 replication/backup。
    - Distractors：(1) MFA Delete 等同 immutable legal retention；(2) lifecycle rule 可覆寫 Compliance mode retention；(3) Object Lock 自動將每個 version 同步到另一 Region。
    - Level / Task / Source：SAP｜SAP-2.2、SAP-2.3｜[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

---

## 第 42 章：S3 Storage Classes、Lifecycle 與 Archival

### 現有題目缺陷

- 第 1 題正解只是整章 storage classes 清單，未給 object size、access frequency、retrieval SLA 或 AZ durability 等可判斷條件。
- 第 2、4 題重複考一組過廣的 S3 設定，且沒有真正測 Lifecycle filter、minimum duration、retrieval fee 或 restore。
- 第 3 題把 S3 object model 當成 lifecycle 的正解；另一個選項才在描述 lifecycle 非同步轉換，題目與測量目標錯位。
- 第 5 題的 governance/rollback 是跨章通用模板，與 storage class 選擇幾乎無關。
- 完全缺少 Intelligent-Tiering archive opt-in、Glacier 三種 class 差異、One Zone-IA 風險、S3 Express One Zone 與 noncurrent versions。

### 10 個原創、非重疊 intents

1. **Standard 與 Standard-IA 的 total cost**
   - Intent：大型備份每月讀一次、必須 multi-AZ，需比較 storage、retrieval、request 與 minimum duration。
   - Correct principle：可預測且不常存取、需要毫秒存取與 multi-AZ resilience 時考慮 Standard-IA；短命或頻繁讀取資料可能因 retrieval/minimum-duration 反而較貴。
   - Distractors：(1) IA 只降低價格，request/retrieval 與 minimum duration 完全相同；(2) Standard-IA 為單 AZ；(3) 所有 object 寫入後立即轉 IA 必然最省。
   - Level / Task / Source：SAA｜SAA-4.1｜[S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

2. **One Zone-IA 的適用資料**
   - Intent：可由原始資料重建的 secondary copy，容許單 AZ 損失且需毫秒讀取。
   - Correct principle：One Zone-IA 適合可重建、非唯一 copy 且可接受單 AZ failure 的 infrequent-access data；不可用於唯一合規副本。
   - Distractors：(1) One Zone-IA 仍跨三個 AZ；(2) 因名稱含 IA，restore 必須數小時；(3) 它比 Standard-IA 更適合唯一不可重建資料。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-4.1｜[S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

3. **Intelligent-Tiering 的監控與 archive tiers**
   - Intent：access pattern 不可預測，object 長期存在，但偶爾需立即讀。
   - Correct principle：Intelligent-Tiering 自動在 frequent/infrequent/instant archive access tiers 間移動；optional archive/deep archive tiers 需按 retrieval SLA 決定是否開啟，且有 per-object monitoring/automation charge。
   - Distractors：(1) 啟用後所有 tiers 都永遠毫秒可讀；(2) 它會依 object content 自動判斷合規 retention；(3) 它沒有任何小 object/monitoring 成本考量。
   - Level / Task / Source：SAA｜SAA-3.1、SAA-4.1｜[S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)

4. **Glacier Instant Retrieval**
   - Intent：醫療影像一年只讀數次，但讀取時必須毫秒級，資料不可丟失。
   - Correct principle：Glacier Instant Retrieval 提供 archive 成本取向與毫秒 retrieval，適合長期且極少存取、仍需即時取回的資料。
   - Distractors：(1) Flexible Retrieval expedited 才是唯一毫秒方案；(2) Deep Archive 可直接 GET 不需 restore；(3) One Zone-IA 比較適合唯一長期合規副本。
   - Level / Task / Source：SAA｜SAA-3.1、SAA-4.1｜[S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

5. **Glacier Flexible Retrieval 的 restore tier**
   - Intent：法務資料通常不讀，事故時可等待數分鐘至數小時，並需在成本與速度間選擇。
   - Correct principle：Flexible Retrieval 需先 restore temporary accessible copy；依需求選 expedited、standard 或 bulk，並規劃 restored copy 的可用期間。
   - Distractors：(1) 所有 retrieval tier 有相同時間與成本；(2) restore 會永久把原 object 改回 Standard；(3) 直接 GET archive object 可由 client timeout 自動等待完成。
   - Level / Task / Source：SAA｜SAA-3.1、SAA-4.1｜[Restoring archived objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html)

6. **Glacier Deep Archive 與 RTO**
   - Intent：七年保留且幾乎不讀，恢復可等待多小時；判斷是否適合最低成本 archive。
   - Correct principle：Deep Archive 適合極少取用且可接受較長 restore window 的資料；不能把低 storage price 誤當低 RTO。
   - Distractors：(1) Deep Archive 適合每小時 analytics query；(2) 它提供 One Zone durability；(3) storage class 越便宜，restore 一定越快。
   - Level / Task / Source：SAA｜SAA-4.1｜[S3 Glacier storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/glacier-storage-classes.html)

7. **Lifecycle filter、current 與 noncurrent versions**
   - Intent：`logs/prod/` tags 符合的 current versions 30 天轉 IA，noncurrent versions 90 天刪除，未完成 multipart 7 天清理。
   - Correct principle：用 prefix/tag filter 精確 scope rule，分開設定 `Transitions`、`NoncurrentVersionTransitions/Expiration` 與 `AbortIncompleteMultipartUpload`。
   - Distractors：(1) current object expiration 會自動套用同樣期限到所有 noncurrent versions；(2) lifecycle filter 可使用 IAM Principal；(3) abort incomplete uploads 會刪除已完成 objects。
   - Level / Task / Source：SAA｜SAA-4.1｜[Managing the lifecycle of objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

8. **Minimum storage duration 與 minimum billable size**
   - Intent：大量 10 KB、兩週後刪除的 objects；評估是否轉 IA/Glacier。
   - Correct principle：必須把 storage class 的 minimum duration、minimum billable object size、transition request 與 retrieval charge 納入 TCO；短命小 object 常不適合立即 transition。
   - Distractors：(1) Lifecycle transition 本身永遠免費；(2) 小 object 僅按實際 bytes 計費，所有 class 都無 minimum；(3) 提前刪除不會產生剩餘 minimum-duration charge。
   - Level / Task / Source：SAA → SAP｜SAA-4.1、SAP-2.6｜[S3 storage class considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)

9. **S3 Express One Zone 的性能與故障域**
   - Intent：同 AZ 的 latency-sensitive application 反覆讀寫大量小 objects，資料可由上游重建。
   - Correct principle：S3 Express One Zone/directory bucket 提供單 AZ 高性能 object access，但 API/feature 與 general purpose bucket 有差異；只在能接受 AZ scope 且符合 access pattern 時選用。
   - Distractors：(1) 它是跨 Region archival class；(2) 可直接當 POSIX shared filesystem；(3) 因價格/性能較高，適合唯一不可重建 DR copy。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6｜[S3 Express One Zone](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html)

10. **Archive restore 的 operational workflow**
    - Intent：數百萬 archived objects 必須在稽核前批次恢復、追蹤完成狀態並於期限後回收 temporary copies。
    - Correct principle：用 S3 Batch Operations/restore requests 規劃批量 restore，監控 inventory/status，設定 restored copy days；原 archive object 保持原 class，需將 RTO 與 request cost 納入演練。
    - Distractors：(1) 對 bucket 執行一次 restore 即同步恢復全部 objects；(2) lifecycle transition 到 Standard 會立即且免費完成大量 restore；(3) replication rule 可取代 archive restore 並保證相同完成時間。
    - Level / Task / Source：SAP｜SAP-2.4、SAP-2.6｜[Restoring archived objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html)

---

## 第 43 章：EBS、EFS 與 FSx 選型

### 現有題目缺陷

- 第 1 題同時塞入 Windows、HPC、Linux 三種 workload，正解只是服務對照表，不需分析單一 use case。
- 第 2、4 題都在背 EBS config 清單；沒有 IOPS/throughput/volume size 的實際數值關係。
- 第 3 題只測 EBS 最基本定義；未測 AZ scope、snapshot restore、Multi-Attach、filesystem/cluster coordination。
- 第 5 題是通用 migration governance，不測 file protocol、mount target、AD integration、FSx deployment type 或 failover。
- 缺少 EFS Standard/One Zone、throughput modes，以及 FSx for Windows/Lustre/ONTAP/OpenZFS 的清楚分界。

### 10 個原創、非重疊 intents

1. **Block、shared file 與 object 的介面契約**
   - Intent：資料庫需要低延遲 block device；web fleet 需要共享 NFS；靜態 archive 以 key 讀寫。
   - Correct principle：依 access semantics 選 EBS、EFS/FSx、S3；容量不是第一判斷，protocol、concurrent writers、locking 與 failure domain 才是。
   - Distractors：(1) 一律以 S3 取代 block/file；(2) EBS volume 可無條件跨 AZ 同時 mount；(3) EFS 因可共享，所以適合所有高 IOPS database log。
   - Level / Task / Source：SAA｜SAA-3.1｜[AWS storage services overview](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)

2. **EBS gp3、io2、st1、sc1 的 access pattern**
   - Intent：分別判斷一般 SSD、critical high-IOPS、large sequential throughput、cold sequential workloads。
   - Correct principle：gp3 適合一般 SSD 且可獨立調 IOPS/throughput；io2 適合一致高 IOPS/durability；st1/sc1 是 HDD、偏 large sequential，不可作 boot volume。
   - Distractors：(1) st1 最適合大量小型 random I/O；(2) gp3 IOPS 永遠只能隨 size 增長；(3) sc1 適合 latency-critical transactional database。
   - Level / Task / Source：SAA｜SAA-3.1、SAA-4.1｜[EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)

3. **EBS AZ scope、snapshot 與跨 AZ 恢復**
   - Intent：EC2 所在 AZ 故障，需從最近 snapshot 在另一 AZ 恢復 volume。
   - Correct principle：EBS volume 屬單 AZ；snapshot 是 Region-scoped incremental backup，可在 Region 內另一 AZ 建立新 volume。應實測 filesystem/application-consistent restore 與 RTO。
   - Distractors：(1) volume 自動同時附加到另一 AZ instance；(2) snapshot 只存在原 AZ；(3) Multi-AZ EC2 Auto Scaling 會自動複寫每個 EBS filesystem state。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.2｜[Amazon EBS snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

4. **EBS Multi-Attach 的限制與 coordination**
   - Intent：多台 instances 需要對同一 block volume 寫入，應用是否可直接使用 ext4。
   - Correct principle：只有支援的 io1/io2 volume/instance 條件能 Multi-Attach；block sharing 不提供檔案協調，需 cluster-aware filesystem/application fencing。一般共享檔案需求優先比較 EFS/FSx。
   - Distractors：(1) Multi-Attach 會自動把 ext4 變成 cluster filesystem；(2) 所有 EBS types 都能跨 AZ Multi-Attach；(3) Multi-Attach 自動提供 cross-Region replication。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-2.5｜[Attach an EBS volume to multiple instances](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes-multi.html)

5. **EFS mount target、routing 與 security group**
   - Intent：兩個 AZ 的 Linux fleet 掛載 EFS，要求 AZ fault tolerance 與 private NFS。
   - Correct principle：在使用中的各 AZ 建 mount target，client 經 DNS/網路到 mount target；security groups允許 NFS 2049，並以 IAM/access point/TLS mount補充 identity 與 encryption。
   - Distractors：(1) EFS 必須經 IGW 公開 mount；(2) 一個 mount target 可同時存在於同 AZ 多個 subnets；(3) bucket policy 控制 NFS file permissions。
   - Level / Task / Source：SAA｜SAA-1.3、SAA-2.2、SAA-3.1｜[EFS mount targets](https://docs.aws.amazon.com/efs/latest/ug/accessing-fs.html)

6. **EFS performance 與 throughput mode**
   - Intent：大量 web content 與 highly parallel workloads；判斷 General Purpose/Max I/O、Elastic/Provisioned/Bursting。
   - Correct principle：先依 latency/parallelism 選 performance mode，再依實際吞吐形態選 throughput mode；監控 throughput、I/O 與 client behavior，不能只增加 storage 猜測性能。
   - Distractors：(1) Provisioned throughput 必須與 stored bytes 固定綁定；(2) Max I/O 永遠比 General Purpose latency 更低；(3) mount targets 數量等同 throughput shards。
   - Level / Task / Source：SAA → SAP｜SAA-3.1、SAP-2.5｜[EFS performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)

7. **EFS Standard、One Zone、Lifecycle 與 replication**
   - Intent：shared files 需跨 AZ availability；冷檔轉 IA，並規劃 Region DR。
   - Correct principle：Standard classes 跨 AZ；One Zone classes 限單 AZ。Lifecycle 依 access transition，replication/backup另處理 DR；不能把 IA 當 backup。
   - Distractors：(1) EFS One Zone 仍可抵抗該 AZ 永久損失；(2) Lifecycle transition 自動建立跨 Region copy；(3) EFS IA 需先 restore 數小時才可讀。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAA-4.1、SAP-2.2｜[EFS storage classes](https://docs.aws.amazon.com/efs/latest/ug/storage-classes.html)

8. **FSx for Windows File Server**
   - Intent：Windows clients 需要 SMB、NTFS ACL、Active Directory、DFS namespaces 與 Multi-AZ failover。
   - Correct principle：選 FSx for Windows；依 HA 需求選 Single-AZ/Multi-AZ，整合 AD，規劃 throughput capacity、storage、backups 與 DNS/DFS access。
   - Distractors：(1) EFS 原生提供 SMB/NTFS ACL；(2) FSx for Lustre 是 Windows home directories 首選；(3) S3 object ACL 可直接呈現成完整 NTFS share。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-3.1｜[What is FSx for Windows File Server](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)

9. **FSx for Lustre 與 S3-linked HPC**
   - Intent：HPC job 需要高吞吐 parallel filesystem，input/output 位於 S3，scratch 可重建。
   - Correct principle：選 FSx for Lustre，依 temporary scratch 或 durable persistent deployment 選型，並使用 S3 data repository integration；它不是 general SMB home-directory service。
   - Distractors：(1) EBS gp3 可天然讓數千 compute nodes共享同一 namespace；(2) FSx for Windows提供 Lustre parallel I/O；(3) S3 Select 可替代任意 POSIX HPC filesystem。
   - Level / Task / Source：SAA → SAP｜SAA-3.1、SAP-2.5｜[What is FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)

10. **FSx for ONTAP / OpenZFS 的遷移與資料功能**
    - Intent：既有 NetApp workload需要 NFS/SMB/iSCSI、snapshots/clones；另一純 Linux workload依賴 ZFS semantics。
    - Correct principle：協議與既有管理/資料功能驅動選型：ONTAP適合 NetApp-compatible multi-protocol/data management；OpenZFS適合 NFS 與 ZFS snapshots/clones。仍須選 deployment type、backup、encryption與 throughput。
    - Distractors：(1) 只因檔案副檔名是 JSON 就選 OpenZFS；(2) ONTAP/OpenZFS 都是 object stores，沒有 file protocol；(3) 選任一 FSx 後即可忽略 application protocol compatibility。
    - Level / Task / Source：SAP｜SAP-4.2、SAP-4.3｜[Choosing an Amazon FSx file system](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/using-fsx-file-systems.html)

---

## 第 44 章：Storage Gateway、DataSync、Transfer 與 Snow

### 現有題目缺陷

- 第 1 題把 DataSync、Storage Gateway、Transfer Family、Snow 的答案全部列出，沒有要求讀者對單一資料流做選擇。
- 第 2、4 題重複 DataSync settings；未測 agent placement、network path、metadata support、verification 或 cutover delta。
- 第 3 題只問一句 DataSync 定義；沒有衡量 bandwidth、change rate、small-file overhead 與 RTO。
- 第 5 題把第 1 題摘要加上通用治理當正解，仍然不測 migration wave 或 rollback。
- 缺少 File/Volume/Tape Gateway 各自介面，以及 Transfer Family identity/backend、Snow chain of custody、DMS 邊界。

### 10 個原創、非重疊 intents

1. **DataSync 的正確工作負載**
   - Intent：on-prem NFS/SMB 資料需重複、增量地傳到 S3/EFS/FSx，保留支援的 metadata 並驗證結果。
   - Correct principle：使用 DataSync locations/tasks；on-prem通常部署 agent，設定 include/exclude、schedule、bandwidth、verification 與 task reports。它是 data movement，不是持續提供 local file interface。
   - Distractors：(1) Storage Gateway File Gateway 是一次性 bulk migration engine；(2) DMS 是一般 NFS metadata migration首選；(3) S3 Transfer Acceleration 能直接 crawl on-prem filesystem。
   - Level / Task / Source：SAA｜SAA-3.5、SAA-4.1｜[What is AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)

2. **DataSync security 與 AWS-to-AWS agent requirement**
   - Intent：跨帳號 S3 到 EFS transfer，需 least privilege、KMS、private path，判斷何時需要 agent。
   - Correct principle：依 location 類型決定 agent；AWS storage 間某些 transfer可由服務直接執行。IAM role、bucket/file permissions、KMS key policy、VPC endpoint/ENI與 network requirements 都需明確配置。
   - Distractors：(1) DataSync service role 自動解密任何 customer KMS key；(2) 所有 AWS-to-AWS transfer 都必須在 EC2 自建 agent；(3) source read permission會自動授予 destination write permission。
   - Level / Task / Source：SAP｜SAP-2.3、SAP-2.5｜[DataSync network requirements](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)

3. **Bandwidth、change rate 與 cutover**
   - Intent：500 TB 初始資料、每日變更 8 TB、10 Gbps link；估算是否能在停機窗口內完成。
   - Correct principle：計算 effective throughput 而非 line rate，納入 small files/metadata、change rate、verification、retries與最後 delta；先 bulk seed，多輪增量後 freeze/cutover/validate。
   - Distractors：(1) 只用 bytes ÷ 10 Gbps 即可保證日期；(2) 初次 copy 完成後不用同步 cutover期間變更；(3) 關閉 verification 必然不影響正確性與稽核。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-4.2｜[DataSync task execution](https://docs.aws.amazon.com/datasync/latest/userguide/run-task.html)

4. **File Gateway 的 hybrid cache 語意**
   - Intent：on-prem apps 必須繼續以 NFS/SMB 寫入，但 durable objects 存在 S3，熱門資料保留 local cache。
   - Correct principle：選 S3 File Gateway；appliance提供 file share/cache並把 files 映射為 S3 objects。需理解 cache refresh、write upload、metadata與直接修改 S3 objects造成的 coherency限制。
   - Distractors：(1) File Gateway 是完整 POSIX distributed lock service across sites；(2) 它把每個 file 存為 EBS snapshot；(3) Volume Gateway 才提供 NFS/SMB namespace。
   - Level / Task / Source：SAA → SAP｜SAA-3.1、SAP-4.2｜[What is Amazon S3 File Gateway](https://docs.aws.amazon.com/filegateway/latest/files3/what-is-file-s3.html)

5. **Volume Gateway：cached 與 stored volumes**
   - Intent：legacy application 只能使用 iSCSI block volumes，分別評估 primary data在 AWS 或 on-prem。
   - Correct principle：cached volumes將 primary data放 AWS、熱門 blocks local cache；stored volumes將完整 primary data留在 local並非同步 snapshot到 AWS。兩者都需 application-consistent backup設計。
   - Distractors：(1) Volume Gateway提供 SMB share；(2) cached mode 保證完整 dataset 永遠在 local；(3) EBS snapshot replication等同同步 zero-RPO block mirror。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-4.2｜[What is Volume Gateway](https://docs.aws.amazon.com/storagegateway/latest/vgw/WhatIsStorageGateway.html)

6. **Tape Gateway 與 virtual tape lifecycle**
   - Intent：既有 backup software 使用 VTL，目標是替代實體 tape並長期 archive。
   - Correct principle：Tape Gateway呈現 iSCSI VTL；virtual tapes由 backup application管理，eject後進 virtual tape shelf/archive。需規劃 retrieval、retention、KMS與restore test。
   - Distractors：(1) Tape Gateway適合 interactive database block I/O；(2) archived virtual tape可直接由 EC2 mount為 EBS；(3) 啟用 gateway後 backup software catalog不再重要。
   - Level / Task / Source：SAA → SAP｜SAA-4.1、SAP-2.2｜[What is Tape Gateway](https://docs.aws.amazon.com/storagegateway/latest/tgw/WhatIsStorageGateway.html)

7. **Transfer Family 的 protocol、identity 與 backend**
   - Intent：外部 partners 必須維持 SFTP，資料落 S3，每個 partner只能看自己的 prefix。
   - Correct principle：使用 Transfer Family managed SFTP endpoint，設定 service-managed或custom identity provider、home directory/logical mapping、per-user role與 S3/KMS permissions；protocol入口不取代 backend authorization。
   - Distractors：(1) 開放 public S3 bucket即可等同 SFTP；(2) Transfer Family user自動取得整個 account權限；(3) DataSync提供 partners可長期登入的 SFTP server。
   - Level / Task / Source：SAA → SAP｜SAA-1.3、SAP-2.3｜[AWS Transfer Family](https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer-family.html)

8. **Snow Family 的 offline migration decision**
   - Intent：多 PB、網路需數月、資料所在地可安全收送設備；規劃離線 seed。
   - Correct principle：比較 online transfer完成時間與 Snow device logistics；使用 Snowball Edge jobs、encryption、manifest/unlock code、chain of custody與 import verification。離線 seed 後仍需處理持續 delta。
   - Distractors：(1) Snowball是長期 NAS，不需歸還；(2) device抵達 AWS即代表所有 objects已驗證並可刪 source；(3) Snow transfer自動同步裝置寄出後的新資料。
   - Level / Task / Source：SAP｜SAP-4.2｜[AWS Snowball Edge Developer Guide](https://docs.aws.amazon.com/snowball/latest/developer-guide/whatisedge.html)

9. **Hybrid migration 組合題**
   - Intent：3 PB歷史影像、每日20 TB新增、partners持續SFTP；要求最短 cutover與介面相容。
   - Correct principle：可用 Snow做 initial seed、DataSync/網路做 delta、Transfer Family承接 SFTP；每個服務只負責一段 path，並以 inventory/checksum與 freeze window驗證。
   - Distractors：(1) 單用 Transfer Family搬完3 PB且不估 bandwidth；(2) 單用 Snow處理 device寄出後永久增量；(3) File Gateway自動遷移所有歷史資料並替外部使用者提供 SFTP。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-4.2｜[AWS storage services overview](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)

10. **DataSync、DMS、Direct Connect 與 Storage Gateway 的邊界**
    - Intent：分別面對 file migration、ongoing database CDC、network connectivity、持續 hybrid storage interface。
    - Correct principle：DataSync搬 file/object；DMS遷移/複寫 database；Direct Connect提供網路，不自動搬資料；Storage Gateway保留 hybrid storage protocol。先辨識 state/protocol，再選工具。
    - Distractors：(1) Direct Connect會自動發現與複寫 NAS files；(2) DMS可保留任意 POSIX ACL/xattrs作通用 file copier；(3) Storage Gateway只是一條 dedicated network circuit。
    - Level / Task / Source：SAA → SAP｜SAA-3.5、SAP-4.2｜[AWS storage services overview](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html)

---

## 第 45 章：RDS Multi-AZ、Read Replica 與 RDS Proxy

### 現有題目缺陷

- 第 1 題同時要求 HA、read scaling、connection pooling，正解照抄三個服務用途，沒有隔離單一 constraint。
- 第 2、4 題重複 broad RDS config；沒有 engine、storage、backup window、replication lag 或 proxy connection limits。
- 第 3 題中「DB instance + Multi-AZ/read replica」與「同步 standby + DNS failover」都正確，只因題幹點名 Amazon RDS 才選前者，鑑別度低。
- 第 5 題仍是通用 rollout/rollback，未處理 schema compatibility、replica promotion、DNS caching 或 connection pinning。
- 缺少 Multi-AZ DB instance與 Multi-AZ DB cluster差異，以及 backup/PITR、KMS、cross-Region replica。

### 10 個原創、非重疊 intents

1. **Multi-AZ DB instance不是 read scaling**
   - Intent：單一 writer需要 AZ failure自動 failover，但 reporting要不要讀 standby。
   - Correct principle：傳統 Multi-AZ DB instance將資料同步複寫到不可讀 standby，主要提供 HA；reporting需另建 read replica或其他 read tier。
   - Distractors：(1) standby提供 read endpoint；(2) Multi-AZ只做 async backup、不能 failover；(3) application必須手動把 endpoint改成 standby IP。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-3.3｜[RDS Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)

2. **Multi-AZ DB cluster 的可讀 standbys**
   - Intent：需要一個 writer、兩個可讀 instances分散三 AZ並可快速 failover。
   - Correct principle：對支援的 engines可選 Multi-AZ DB cluster；writer與兩個 readable DB instances提供 HA/read capacity，與傳統一主一不可讀 standby不同。
   - Distractors：(1) 它是跨 Region同步 cluster；(2) 所有 RDS engines/version都支援；(3) reader instances只保存 backup，不能接 query。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAA-3.3、SAP-2.5｜[Multi-AZ DB clusters](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)

3. **Read replica 的 async consistency 與 read scaling**
   - Intent：報表可接受短暫 stale，不能影響 primary；判斷 replica lag。
   - Correct principle：read replicas通常非同步，適合 read scale與部分 DR；應監控 lag，不能對剛寫入後立即讀的強一致流程無條件導向 replica。
   - Distractors：(1) read replica commit與 primary同步，因此零 lag；(2) replica只能備份不能提供 read traffic；(3) 建 replica會自動分散 application connections，不需 reader endpoint/config。
   - Level / Task / Source：SAA｜SAA-3.3｜[Working with read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

4. **Cross-Region replica promotion 與 DR**
   - Intent：Region failure時 promote cross-Region replica，要求明確 RPO/RTO。
   - Correct principle：cross-Region replica是非同步；promotion會成為獨立 DB，需處理 lag/data loss、DNS/secret/connection、write ownership與 failback。它不是自動零 RPO failover。
   - Distractors：(1) promotion後原 primary自動成為同步 replica；(2) cross-Region replica使用同一 private endpoint且無 DNS變更；(3) 只建立 replica即完成完整 DR runbook。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.4｜[Cross-Region read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.XRgn.html)

5. **RDS Proxy 與 Lambda connection storm**
   - Intent：Lambda burst建立數千短連線，database `max_connections`先耗盡。
   - Correct principle：RDS Proxy在 application與 DB間 pool/reuse connections，搭配 Secrets Manager/IAM auth與合適 timeout；它減少連線壓力，但不加速慢 SQL或增加 DB CPU。
   - Distractors：(1) 增加 Lambda concurrency必然解決 DB connection limit；(2) read replica會自動 pool writer connections；(3) Proxy可取代 transaction correctness與 schema design。
   - Level / Task / Source：SAA｜SAA-2.1、SAA-3.3｜[Using Amazon RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html)

6. **Proxy pinning 與 connection multiplexing 限制**
   - Intent：使用 session state、temporary tables或大型 statements後，Proxy multiplexing收益下降。
   - Correct principle：某些 session/transaction行為會 pin client到同一 DB connection；應監控 pinning metrics、減少不必要 session state，不能假設所有連線都能無限 multiplex。
   - Distractors：(1) Proxy會重寫 SQL消除所有 session state；(2) pinning代表資料已複寫到 read replica；(3) 增大 Proxy idle timeout可保證永不 pin。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-3.3｜[RDS Proxy connection considerations](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-connections.html)

7. **Automated backup、PITR 與 manual snapshot**
   - Intent：誤刪資料需恢復到 15 分鐘前，且月末 snapshot需保留超過 automated retention。
   - Correct principle：automated backups/transaction logs支援 retention window內 PITR；manual snapshots直到刪除前保留。Restore會建立新 DB，仍需驗證 application cutover與 restore time。
   - Distractors：(1) PITR會原地回滾現有 DB且無停機；(2) automated backup retention到期後仍永久保留；(3) Multi-AZ standby可查詢任意歷史時間點。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.2｜[RDS backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)

8. **RDS encryption 與 snapshot copy**
   - Intent：未加密 DB需遷移到 encrypted replacement，並將 encrypted snapshot跨 Region/account。
   - Correct principle：不能直接切換既有 unencrypted instance為 encrypted；可 snapshot/copy with KMS key再 restore。跨 account/Region要處理 customer managed key policy/grant與 snapshot sharing/copy。
   - Distractors：(1) 修改 DB parameter即可原地加密 existing storage；(2) AWS managed key可任意跨 account分享；(3) TLS會自動加密 snapshot at rest並取代 KMS。
   - Level / Task / Source：SAP｜SAP-2.3、SAP-4.3｜[Encrypting Amazon RDS resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)

9. **Failover endpoint、DNS 與 client recovery**
   - Intent：Multi-AZ failover後 application仍使用 cached old IP並長時間失敗。
   - Correct principle：使用 RDS DNS endpoint，不固定 IP；client需合理 DNS caching、connection timeout、retry/backoff與 reconnect。Failover完成不代表既有 TCP sessions繼續。
   - Distractors：(1) 將 primary IP寫入 config可縮短 failover；(2) 所有 drivers會讓既有 transactions無縫續跑；(3) read replica endpoint與 Multi-AZ writer endpoint永遠相同。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-3.4｜[RDS failover process](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.Failover.html)

10. **RDS、Aurora 與 self-managed database比較**
    - Intent：需要特定 engine extension/OS控制、一般 managed relational或 Aurora共享儲存特性。
    - Correct principle：依 engine compatibility、operational control、HA/read model與成本選 self-managed EC2、RDS engine或 Aurora；managed程度越高不等於完全相容或永遠較便宜。
    - Distractors：(1) Aurora支援所有 Oracle/SQL Server features；(2) RDS允許 root OS與任意 storage layout；(3) EC2 self-managed database會自動得到 RDS backups/failover。
    - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6、SAP-4.3｜[AWS database services overview](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)

---

## 第 46 章：Aurora、Global Database 與 Serverless

### 現有題目缺陷

- 第 1 題將 Aurora replicas、Global Database、Serverless 三個不同問題放在同一正解，沒有要求選一個具體 topology。
- 第 2 題的 Aurora config與 Global Database config都可能正確，卻沒有給 workload constraint決定哪組設定。
- 第 3 題的 A（Aurora shared storage）與 B（Global Database replication）均為正確機制，只因題幹寫 Amazon Aurora而把 B當錯，存在明顯多重正解風險。
- 第 4 題只是第 2 題重述；第 5 題是通用 governance。
- 缺 endpoint、failover priority、global lag/RPO、planned switchover、write forwarding、Serverless v2 ACU、backup/clone 等考點。

### 10 個原創、非重疊 intents

1. **Aurora distributed storage 與 compute separation**
   - Intent：DB instance故障時，為何不需像傳統 replica一樣重建完整獨立 storage。
   - Correct principle：Aurora cluster volume跨多 AZ保存多份資料，writer/readers共享 distributed storage；compute instance故障可由其他 instance接手，但 application仍需 reconnect。
   - Distractors：(1) 每個 reader維護完全獨立 async EBS copy；(2) shared storage表示所有 regions同步零 RPO；(3) cluster volume是可由 EC2直接 mount的 EFS。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-3.3｜[Aurora storage reliability](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)

2. **Cluster、reader、instance/custom endpoint**
   - Intent：writes只送 writer、reads分散 readers、特定 analytics replicas需獨立 routing。
   - Correct principle：cluster/writer endpoint連目前 primary；reader endpoint在 replicas間做 connection-level balance；custom endpoint可指定 subset。Endpoint不會重新分配已建立 session中的每次 query。
   - Distractors：(1) reader endpoint提供 strong read-after-write且自動包含 writer以外所有 regions；(2) instance endpoint在 failover後自動指向新 writer；(3) cluster endpoint可將 writes平均分配到所有 replicas。
   - Level / Task / Source：SAA｜SAA-2.2、SAA-3.3｜[Aurora endpoints](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html)

3. **Replica failover tier 與 promotion priority**
   - Intent：指定高規格 replica優先 promotion，analytics replica最後。
   - Correct principle：配置 promotion tiers/failover priority，並確保 candidate capacity與 AZ分散；同 tier時仍依服務規則選擇，不能以 reader endpoint順序推論。
   - Distractors：(1) 建立時間最早永遠先 promotion；(2) reader endpoint DNS順序就是 failover priority；(3) Global Database secondary自動優先於本 Region reader。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.4｜[Aurora fault tolerance](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)

4. **Global Database 非同步 replication 與 RPO**
   - Intent：primary Region寫入、全球低延遲 read，Region loss可容忍數秒資料損失。
   - Correct principle：Aurora Global Database以 dedicated infrastructure非同步複寫到 secondary Regions；監控 replication lag並把實際 RPO寫入設計，不能宣稱同步零資料遺失。
   - Distractors：(1) 每筆 commit等待所有 Regions確認；(2) secondary cluster預設可直接成為 multi-writer；(3) global database只做 DNS routing，不複寫資料。
   - Level / Task / Source：SAP｜SAP-1.3、SAP-2.2｜[Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)

5. **Managed switchover 與 unplanned failover**
   - Intent：planned Region maintenance與 primary Region不可用時，分別如何切換。
   - Correct principle：planned switchover先同步並有較安全的受控角色交換；unplanned failover可能存在 lag/data loss。兩者都需更新/使用正確 endpoint、確認 writer ownership並規劃 failback。
   - Distractors：(1) unplanned failover永遠零 RPO；(2) promote secondary後舊 primary恢復即可同時接受 writes；(3) Route 53 health check本身會完成 database role promotion。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.4｜[Managed planned failovers for Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)

6. **Global write forwarding 的語意**
   - Intent：secondary Region application想送 write但仍維持單一 primary writer。
   - Correct principle：write forwarding可把 secondary收到的 writes轉給 primary Region處理；會增加跨 Region latency並有 consistency/session設定，不能視為真正 multi-primary active-active。
   - Distractors：(1) write在 secondary local commit後再雙向 merge；(2) forwarding消除 Region間 latency與partition風險；(3) 開啟後每個 secondary都能獨立在 network partition期間安全寫入。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-2.5｜[Write forwarding for Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html)

7. **Aurora Serverless v2 ACU 與 scaling range**
   - Intent：流量日夜波動，需要細粒度擴縮，但 production不能 scale到無法承載 connections。
   - Correct principle：設定合適 min/max ACU，理解 capacity range影響可用功能、cache與擴縮；監控 ACU/connection/latency。Serverless v2不是每個 request啟動一個 database。
   - Distractors：(1) max ACU不限制尖峰容量；(2) min ACU越低永遠沒有 cold/cache trade-off；(3) application可忽略 connection pooling與 transaction duration。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAA-4.3、SAP-2.5｜[Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)

8. **Provisioned、Serverless v2 與混合 cluster**
   - Intent：steady writer搭配會突增的 reporting readers，要求選 instance model。
   - Correct principle：依 steady/bursty capacity、engine/version support與成本選 provisioned或 Serverless v2；支援時可在同 cluster配置不同 instance classes，但每個 instance角色與 failover capacity要驗證。
   - Distractors：(1) Serverless v2只能建單 instance、不能 HA；(2) provisioned Aurora不能增加 readers；(3) Serverless v2會改變 SQL engine成 NoSQL。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6｜[Aurora Serverless v2 architecture](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.how-it-works.html)

9. **Backup、PITR、clone 與 Backtrack的差異**
   - Intent：分別處理災難恢復、快速測試環境與 MySQL-compatible誤操作回復。
   - Correct principle：automated backup/PITR建立可恢復點；clone以 copy-on-write快速建立獨立 cluster；Backtrack僅支援特定 Aurora MySQL條件並將 cluster回到過去狀態。三者目的與影響不同。
   - Distractors：(1) clone是獨立完整 backup且 source刪除永不影響任何依賴；(2) Backtrack支援所有 Aurora PostgreSQL clusters；(3) PITR原地修改現有 production cluster。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.6｜[Backing up and restoring Aurora clusters](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.html)

10. **Aurora 與標準 RDS 的選擇**
    - Intent：workload需要特定 engine feature/extension、低成本小型 DB或 Aurora global/read architecture。
    - Correct principle：以 compatibility、HA/read topology、performance profile、Region availability與完整 TCO選擇；Aurora不是標準 MySQL/PostgreSQL的逐位元相容替代，也不必然最便宜。
    - Distractors：(1) 任何 MySQL plugin都可無修改裝進 Aurora host OS；(2) Aurora支援 Oracle與 SQL Server；(3) 因有六份 storage copies，所以不再需要 backup。
    - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6、SAP-4.3｜[What is Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html)

---

## 第 47 章：DynamoDB Partition、Capacity、GSI 與 DAX

### 現有題目缺陷

- 第 1 題正解一次列 key、GSI、capacity mode，沒有實際 access patterns或 item shape可推導 schema。
- 第 2、4 題重複完整 config清單，未測 RCU/WCU計算、hot partition或 throttling metrics。
- 第 3 題 A（GSI async projection）與 D（partition key機制）都是正確敘述，卻只標 D，屬單選正確性缺陷。
- 第 5 題仍是跨帳號 rollout模板，與 DynamoDB migration/data correctness無關。
- 缺 LSI/GSI差異、conditional write/transaction、TTL/Streams、PITR、Global Tables consistency modes、DAX限制。

### 10 個原創、非重疊 intents

1. **Partition key distribution 與 hot key**
   - Intent：單一 celebrity/user key承受大多數 writes，總 table capacity充足仍 throttled。
   - Correct principle：physical distribution受 partition key與流量分布影響；設計高基數 key、必要時 write sharding，再以 query aggregation還原結果。總 capacity不能修復無法分散的單 hot key。
   - Distractors：(1) 增加 sort key種類必然把同 partition key分到不同 physical partitions；(2) Scan可平均 hot writes；(3) DAX會吸收所有 write throttling。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[DynamoDB partitions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.Partitions.html)

2. **Composite key 與 Query/Scan**
   - Intent：依 customer取得最近 orders、依時間範圍排序，不允許全表掃描。
   - Correct principle：以 customer為 partition key、可排序時間/ID為 sort key，使用 Query與 key condition；FilterExpression在讀取後過濾，不能降低已讀 capacity如同 key condition。
   - Distractors：(1) 只用隨機 order ID PK再 Scan所有 items；(2) FilterExpression可避免讀取不符合項目的 RCU；(3) sort key可跨所有 partition keys提供全域排序。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[Querying tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)

3. **GSI 的 alternate key 與 consistency**
   - Intent：base table以 orderId查詢，另需以 customerId/status查；可接受短暫 index lag。
   - Correct principle：GSI有自己的 partition/sort key與 projection，base updates非同步傳到 index；GSI reads只支援 eventually consistent，capacity/storage與 sparse design需評估。
   - Distractors：(1) GSI與 base table在同一 transaction中同步可強一致讀；(2) GSI必須與 base table使用相同 partition key；(3) 未投影 attributes仍可免費由 index直接返回。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[Global secondary indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)

4. **LSI 的固定 partition key與建立限制**
   - Intent：同一 customer items需以不同 sort keys查詢，且有 strong read需求。
   - Correct principle：LSI與 base table共享 partition key、使用 alternate sort key，必須在建 table時建立，支援 strong consistency；同 partition key item collection size等限制需納入。
   - Distractors：(1) LSI可隨時 online加入；(2) LSI可使用完全不同 partition key；(3) LSI有獨立 provisioned capacity與跨 Region replica。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[Local secondary indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/LSI.html)

5. **On-demand 與 provisioned capacity**
   - Intent：新 workload流量未知且尖峰不規則；另一 workload穩定可預測並要求成本控制。
   - Correct principle：on-demand降低 capacity planning並按 request計費，但仍有 scaling/throttling行為；provisioned適合可預測流量，可搭配 auto scaling/reserved capacity。選擇需看 history、峰值與成本。
   - Distractors：(1) on-demand表示任何瞬間流量都無上限；(2) provisioned不能 auto scale；(3) 切換 capacity mode會改變 consistency model。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[DynamoDB capacity modes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html)

6. **Capacity units、item size與 consistency**
   - Intent：計算 6 KB item的 strongly/eventually consistent reads與 transactional write成本方向。
   - Correct principle：capacity按 item size向固定 unit boundary進位；strong read比 eventual消耗更多，transactional operations也有額外 capacity。應以實際 item size/access rate計算而非 item count。
   - Distractors：(1) 只按返回 attributes bytes計費；(2) eventual read永遠免費；(3) FilterExpression先過濾後才計算讀取容量。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[Read/write capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ProvisionedThroughput.html)

7. **Conditional writes、transactions 與 idempotency**
   - Intent：庫存只能由 1減到0一次，重試不能 oversell；跨兩個 items需原子更新。
   - Correct principle：用 conditional expression/optimistic locking阻止不符合前置狀態的 write；需要多 item ACID時用 TransactWriteItems並設計 idempotency/retry。Transaction不能修復 hot partition。
   - Distractors：(1) eventual read後直接 PutItem即可保證不競爭；(2) BatchWriteItem是 ACID transaction；(3) SQS message ID自動讓所有 DynamoDB writes exactly once。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.4｜[DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)

8. **TTL、Streams 與 PITR 各自責任**
   - Intent：sessions到期自動清理、下游收到變更事件、誤刪 table可恢復。
   - Correct principle：TTL是非同步 best-effort過期刪除；Streams記錄有限保留期內 item changes供 consumers處理；PITR提供 recovery window內 table restore。三者不能互相替代。
   - Distractors：(1) TTL到達秒數即同步拒絕所有 reads；(2) Streams是永久 backup；(3) PITR會原地回滾現有 table。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.2｜[DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)

9. **Global Tables 的 multi-Region consistency**
   - Intent：全球 active-active writes，需在低 latency與跨 Region strong consistency需求間選擇。
   - Correct principle：先確認使用 MREC或支援條件下的 MRSC及其 Region/feature限制；MREC跨 Region複寫存在延遲與 conflict resolution，application必須理解 concurrent writes與 failover。
   - Distractors：(1) 所有 Global Tables永遠同步 strong且無 Region限制；(2) Route 53可替代 table replication；(3) 建 replica後 application可安全在 network partition下對同一 item任意寫且永無 conflict。
   - Level / Task / Source：SAP｜SAP-1.3、SAP-2.2、SAP-2.4｜[DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)

10. **DAX 的 cache scope與限制**
    - Intent：read-heavy DynamoDB workload需要 microsecond cache，但某些流程要求 strong reads。
    - Correct principle：DAX是 DynamoDB-compatible in-memory cache，適合 eventually consistent reads與 write-through behavior；strongly consistent reads會 bypass cache。它不解決 hot writes或任意 SQL query。
    - Distractors：(1) DAX讓 GSI變成 strongly consistent；(2) DAX是 durable system of record，可關閉 PITR；(3) DAX可快取 RDS/OpenSearch查詢。
    - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[DynamoDB Accelerator](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)

---

## 第 48 章：ElastiCache 與 Caching Patterns

### 現有題目缺陷

- 第 1 題把 cache-aside、write-through、Redis/Memcached全部放在同一正解，沒有 consistency requirement或 failure behavior。
- 第 2、4 題重複 config清單；未測 cache key、TTL、eviction policy、memory pressure、hit ratio或 connection capacity。
- 第 3 題僅以服務名稱排除 CloudFront，沒有測 cache miss path、stampede、stale data或 failover。
- 第 5 題仍是通用 governance，沒有 cache warm-up、rollback、authoritative store或 invalidation plan。
- 缺 Valkey/Redis OSS/Memcached差異、cluster mode、Multi-AZ、Serverless、AUTH/RBAC/TLS及 DAX/MemoryDB/CloudFront比較。

### 10 個原創、非重疊 intents

1. **Cache-aside 的 miss path**
   - Intent：read-heavy產品資料，cache可丟，database是 authoritative store。
   - Correct principle：application先讀 cache；miss時讀 DB、寫 cache再回傳。需處理 race、TTL、negative caching與 DB失敗；cache flush不得造成資料永久遺失。
   - Distractors：(1) 先寫 cache後永不寫 DB；(2) cache miss直接回 404而不查 source；(3) cache-aside自動保證 cache與 DB同步 transaction。
   - Level / Task / Source：SAA｜SAA-2.1、SAA-3.3｜[Cache-aside pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/cache-aside.html)

2. **Write-through、invalidation 與 stale-read trade-off**
   - Intent：價格更新後必須快速反映，不能接受長 TTL舊值。
   - Correct principle：依 consistency要求選 update/invalidate cache策略；write-through改善後續 reads但增加 write path，invalidate-on-write簡化 source ownership。任何 dual write都需處理部分失敗。
   - Distractors：(1) 把 TTL設一年即可保證最新；(2) 同時寫 DB/cache天然是跨服務 ACID；(3) 只更新 cache、等 eviction後再補 DB。
   - Level / Task / Source：SAA → SAP｜SAA-2.1、SAP-2.4｜[Caching challenges and strategies](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-challenges-and-strategies.html)

3. **Stampede、TTL jitter 與 request coalescing**
   - Intent：熱門 keys同時到期，數萬 requests打向 DB。
   - Correct principle：使用 TTL jitter、single-flight/request coalescing、stale-while-revalidate或預熱，並限制 origin concurrency；擴大 cache node不能消除同步 expiration。
   - Distractors：(1) 讓所有 keys使用相同整點 TTL；(2) client無限立即重試 cache miss；(3) 關閉 eviction即可避免 origin overload。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-2.5｜[Database caching strategies](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/welcome.html)

4. **Cache不是唯一 system of record**
   - Intent：sessions可重建、購物車不可任意遺失；決定 durability與 recovery。
   - Correct principle：先標示 authoritative state；一般 cache視為 disposable projection。若資料不可丟，使用 durable database或明確 persistence/replication產品與 backup策略，不能只靠 eviction-prone cache。
   - Distractors：(1) Multi-AZ cache等同永久 backup；(2) snapshot保證每筆 write零 RPO；(3) 將 TTL關閉即可把 cache變成關聯式 SoR。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.2｜[ElastiCache best practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)

5. **Valkey/Redis OSS 與 Memcached**
   - Intent：需要 sorted sets/pub-sub/replication；另一 workload只需簡單多執行緒 key-value cache。
   - Correct principle：Valkey/Redis OSS提供豐富 data structures、replication與 cluster features；Memcached模型較簡單、multi-threaded、無相同 replication/persistence能力。依功能與 failure model選，不以「哪個較新」決定。
   - Distractors：(1) Memcached原生提供 Redis sorted sets與 streams；(2) Redis OSS完全沒有 sharding；(3) 兩者都提供相同 persistence與 failover contract。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[ElastiCache engine comparison](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html)

6. **Cluster mode、shards 與 hot keys**
   - Intent：dataset與 throughput超過單 node，keys流量分布不均。
   - Correct principle：cluster mode以 shards分散 keyspace並用 replicas提供 read/HA；client需 cluster-aware，hot key仍可能集中單 shard，需 redesign key/access pattern。
   - Distractors：(1) 加 replicas會分散 writes到所有 shards；(2) cluster mode讓單一 key自動拆成多 keys；(3) hash slots與 AZ數量永遠一對一。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[Scaling ElastiCache for Valkey/Redis OSS](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling.html)

7. **Replication、Multi-AZ 與 failover**
   - Intent：primary node失敗時自動 promotion，application需了解 endpoint與資料損失窗口。
   - Correct principle：配置 replicas跨 AZ與 Multi-AZ automatic failover；使用正確 primary/reader/config endpoint並實作 reconnect。非同步 replication仍可能有少量未複寫 writes，不等於零 RPO。
   - Distractors：(1) replica同步確認每筆 write後才回應；(2) failover會保留所有既有 TCP connections；(3) single-node cache啟用 snapshot即具有即時 HA。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.4｜[Minimizing downtime in ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/FaultTolerance.html)

8. **ElastiCache Serverless 與 node-based**
   - Intent：流量不可預測、想降低 shard/node規劃；另一 workload需固定 topology與細緻參數控制。
   - Correct principle：Serverless自動管理 capacity/scaling並按相應用量計費；node-based提供 topology/node/parameter控制。比較 supported features、limits、latency與 steady-state成本。
   - Distractors：(1) Serverless表示沒有任何 service quota或 max usage；(2) node-based不能擴縮；(3) Serverless會自動修復 application cache invalidation bug。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6｜[ElastiCache Serverless](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.Serverless.html)

9. **Network、TLS、AUTH token與 RBAC**
   - Intent：private application限定特定 roles/users存取 cache，傳輸與靜態資料加密。
   - Correct principle：部署於合適 VPC/subnets、以 SG限制 network path，啟用 in-transit/at-rest encryption；依 engine使用 AUTH/RBAC與 Secrets rotation。SG reachability不等於 cache command authorization。
   - Distractors：(1) cache在 private subnet即不需 authentication/TLS；(2) IAM identity policy會自動成為所有 Redis command ACL；(3) public endpoint加難猜 password比 private network更符合 least privilege。
   - Level / Task / Source：SAP｜SAP-2.3｜[ElastiCache security](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Security.html)

10. **ElastiCache、DAX、CloudFront 與 MemoryDB**
    - Intent：分別處理 general application cache、DynamoDB API cache、edge HTTP cache與 durable Redis-compatible primary database。
    - Correct principle：由 protocol、state owner與 consistency決定；ElastiCache供 application-managed cache，DAX專用 DynamoDB，CloudFront在 edge快取 HTTP content，MemoryDB定位 durable in-memory database。
    - Distractors：(1) DAX可快取任意 PostgreSQL SQL；(2) CloudFront可讓 private VPC app直接使用 Redis protocol；(3) ElastiCache snapshot使其自動等同 MemoryDB durability model。
    - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-4.3｜[AWS database services overview](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)

---

## 第 49 章：Redshift、Athena、Glue 與 Lake Formation

### 現有題目缺陷

- 第 1 題把 warehouse、query engine、catalog/ETL、governance完整映射當正解，無法檢驗單一選型。
- 第 2、4 題重複 Redshift config；缺資料量、concurrency、scan bytes、partitioning與 distribution skew等 scenario。
- 第 3 題同時列出正確的 Redshift與 Athena機制，只做服務名稱配對，沒有 query plan推理。
- 第 5 題仍是通用 rollout，未處理 cross-account lake governance、schema evolution或 data quality。
- 缺 Athena workgroup、Parquet/partition projection、Glue Catalog/Crawler/ETL分界、Lake Formation與 IAM/S3 policy交互、Redshift backup/DR。

### 10 個原創、非重疊 intents

1. **Athena 與 Redshift 的 query workload**
   - Intent：偶發 ad hoc S3查詢與高併發、穩定 BI dashboard分別選型。
   - Correct principle：Athena是 serverless query-on-S3，成本/性能與掃描資料相關；Redshift是分析 warehouse，適合持續、高性能與可調 workload management。可混合而非硬選單一服務。
   - Distractors：(1) Athena需先常駐管理 EC2 cluster；(2) Redshift只能讀 S3、不能存 warehouse tables；(3) 任一服務都等同 OLTP database。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[Analytics on AWS](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/analytics.html)

2. **Athena partition、columnar format 與 scan cost**
   - Intent：raw JSON queries慢且昂貴，常以 date/region過濾。
   - Correct principle：轉 Parquet/ORC、壓縮、合理 file size並依常用 predicate partition；讓 partition pruning/column pruning減少 scanned bytes，避免大量 tiny files。
   - Distractors：(1) 將所有資料放單一 uncompressed CSV可最大化 parallelism；(2) 增加 Glue crawler頻率會自動改寫成 Parquet；(3) `LIMIT 10`必然只掃 10 rows並大幅降費。
   - Level / Task / Source：SAA｜SAA-3.3、SAA-4.3｜[Athena performance tuning](https://docs.aws.amazon.com/athena/latest/ug/performance-tuning-data-optimization-techniques.html)

3. **Athena workgroup、result location 與 governance**
   - Intent：不同 teams需限制 scan cost、隔離 query results、強制 encryption。
   - Correct principle：用 workgroups分離 users/queries，設定 result location、encryption與 per-query/data usage controls，搭配 IAM/Lake Formation。Workgroup不是 data catalog。
   - Distractors：(1) workgroup自動授予所有 S3 tables讀取權；(2) query result永遠只存在記憶體不落 S3；(3) 設 budget即可在單一 query掃描前強制中止。
   - Level / Task / Source：SAA → SAP｜SAA-1.3、SAA-4.3、SAP-2.6｜[Athena workgroups](https://docs.aws.amazon.com/athena/latest/ug/workgroups.html)

4. **Glue Data Catalog、Crawler 與 ETL Job**
   - Intent：已有 S3 files需可查 schema；另需將 raw JSON轉 curated Parquet。
   - Correct principle：Data Catalog保存 table/partition metadata，Crawler推斷/更新 metadata，Glue ETL job轉換資料。Crawler不等於 data transformation，Catalog也不是 object storage。
   - Distractors：(1) Crawler會自動重寫所有 source files；(2) Catalog保存完整 dataset bytes；(3) ETL job只更新 IAM policies、不處理資料。
   - Level / Task / Source：SAA｜SAA-3.5｜[AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)

5. **Lake Formation 與 IAM/S3 的 permission layers**
   - Intent：analyst只可查 database/table/column，不能繞過服務直接讀 raw S3。
   - Correct principle：Lake Formation管理 catalog data permissions與 governed access，但底層 IAM、S3 bucket policy、KMS與 registration/service roles仍須正確；需防止 broad direct S3 access繞過細粒度治理。
   - Distractors：(1) Lake Formation grant會自動忽略所有 KMS denies；(2) 只給 `s3:GetObject *`仍能保證 column-level restriction；(3) Glue table owner天然擁有所有帳號的 S3 objects。
   - Level / Task / Source：SAP｜SAP-2.3｜[Lake Formation permissions](https://docs.aws.amazon.com/lake-formation/latest/dg/security-data-access.html)

6. **Cross-account data lake sharing**
   - Intent：producer account集中資料，consumer accounts只讀指定 tables且能被中央撤銷。
   - Correct principle：使用 Lake Formation cross-account grants/resource links或適當 sharing模式，配合 Organizations/RAM、IAM、S3/KMS policies；明確區分 catalog metadata與 data location permissions。
   - Distractors：(1) 將 bucket設 public-read最容易做到跨 account governance；(2) 只分享 Glue table名稱即可自動分享 KMS decrypt；(3) consumer可自行擴大 producer授予的 columns。
   - Level / Task / Source：SAP｜SAP-1.4、SAP-2.3｜[Cross-account data sharing in Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html)

7. **Redshift distribution 與 data movement**
   - Intent：大型 fact與 dimension join產生 network redistribution/skew。
   - Correct principle：依 table size、join keys與 workload選 AUTO/KEY/ALL/EVEN；co-locate常 join資料並避免 skew，使用 query plan/system views驗證，而非只背 distkey。
   - Distractors：(1) 所有 tables使用同一 low-cardinality key；(2) ALL distribution最適合最大且頻繁更新 fact table；(3) distribution style只影響 backup、不影響 joins。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[Redshift data distribution](https://docs.aws.amazon.com/redshift/latest/dg/c_choosing_dist_sort.html)

8. **Sort key、zone map與 data model**
   - Intent：多年 events主要按 date range與 tenant篩選，需降低 block scan。
   - Correct principle：依常見 predicates/order選 sort strategy，讓 zone maps跳過 blocks；維持 statistics/table health。Star schema、sort與 distribution共同影響 analytic queries。
   - Distractors：(1) sort key等同 unique primary-key enforcement；(2) 對每一欄都設 sort key必然最佳；(3) sort key讓 OLTP row updates變成低延遲 point writes。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[Redshift sort keys](https://docs.aws.amazon.com/redshift/latest/dg/t_Sorting_data.html)

9. **WLM、concurrency scaling 與 Serverless**
   - Intent：ETL長查詢阻塞 dashboard短查詢，且 workload有週期性尖峰。
   - Correct principle：用 WLM/query priorities隔離 classes，視需要 concurrency scaling；或評估 Redshift Serverless的 RPU/cost model。先找 queue time、CPU、I/O與 skew，不能只盲目加 nodes。
   - Distractors：(1) 增加 sort key可直接取代 workload queues；(2) Serverless表示 query沒有容量與成本上限；(3) 把所有 queries放同一最高優先 queue最公平。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6、SAP-3.3｜[Redshift workload management](https://docs.aws.amazon.com/redshift/latest/dg/c_workload_mngmt_classification.html)

10. **Redshift backup、encryption 與 DR**
    - Intent：warehouse需要 automated/manual snapshots、cross-Region recovery與 KMS-controlled access。
    - Correct principle：設定 snapshot retention/copy與 restore演練；使用 KMS encryption並規劃 key access。Snapshot/replication策略決定 RPO/RTO，Multi-AZ或 Serverless能力需依 deployment核對，不能假設 query replicas等同 backup。
    - Distractors：(1) materialized view可作完整災難備份；(2) encrypted snapshot跨 account分享時不需處理 KMS key；(3) Spectrum external table會把 S3資料自動備份進 cluster snapshot。
    - Level / Task / Source：SAP｜SAP-2.2、SAP-2.3｜[Redshift snapshots](https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html)

---

## 第 50 章：Kinesis、MSK 與 Streaming Pipeline

### 現有題目缺陷

- 第 1 題一次列 Kinesis、MSK、Firehose，讀者只需選服務字典，不需推理 ordering、retention、consumer model。
- 第 2、4 題重複 Kinesis設定清單，未提供 records/sec、bytes/sec、partition skew或 consumer lag。
- 第 3 題的 Kinesis與 Kafka敘述都正確，只以題幹服務名稱做字面配對。
- 第 5 題仍為通用 rollout/rollback，未測 schema compatibility、replay、dual publishing或 checkpoint migration。
- 缺 shared throughput/enhanced fan-out、retention/replay、idempotency、KMS/IAM、MSK replication與 Firehose buffering/error path。

### 10 個原創、非重疊 intents

1. **Stream 與 queue 的 consumer contract**
   - Intent：同一事件需由 fraud、analytics、archive三個 consumer各自處理並可回放。
   - Correct principle：選 replayable stream（Kinesis/MSK）；每個 consumer保存自己的 progress。SQS work queue通常由 consumers競爭處理，不提供相同 ordered log/replay model。
   - Distractors：(1) 單一 Standard SQS queue讓每個 consumer必定收到每則 message；(2) SNS alone提供 24 小時任意 offset replay；(3) Firehose讓多個 application consumers各自 checkpoint。
   - Level / Task / Source：SAA｜SAA-2.1、SAA-3.5｜[Kinesis Data Streams key concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

2. **Kinesis partition key 與 ordering scope**
   - Intent：同 customer events要有序，不同 customers可平行，且不能形成 hot shard。
   - Correct principle：partition key經 hash映射 shard；同 key records在 shard內具 sequence order。選 business key並確保分布，必要時調整 sharding/explicit hash strategy。
   - Distractors：(1) stream提供所有 shards全域順序；(2) 使用固定 key可提高整體 parallelism；(3) sequence number可由 producer任意指定以跨 shard排序。
   - Level / Task / Source：SAA｜SAA-3.5｜[Kinesis Data Streams key concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)

3. **Provisioned shards 與 on-demand mode**
   - Intent：穩定可預測 throughput與未知快速成長 workload分別選容量模式。
   - Correct principle：provisioned按 shard capacity規劃並 split/merge；on-demand自動管理 capacity但仍有 scaling behavior/quotas。監控 write/read throttling與 distribution，不只看 aggregate bytes。
   - Distractors：(1) on-demand保證任意瞬間無限制吞吐；(2) provisioned shard數只影響 retention、不影響吞吐；(3) 增 producer數會自動消除 hot partition key。
   - Level / Task / Source：SAA → SAP｜SAA-3.5、SAP-2.5｜[Choose Kinesis capacity mode](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)

4. **Shared throughput 與 enhanced fan-out**
   - Intent：五個低延遲 consumers互相爭用 read throughput。
   - Correct principle：一般 consumers共享 shard read throughput/polling；enhanced fan-out為 registered consumers提供 dedicated throughput與 push model，換取額外成本與 consumer management。
   - Distractors：(1) 增加 retention會增加每個 consumer即時 read throughput；(2) enhanced fan-out讓 producer writes分流到更多 shards；(3) 每個 consumer application天然都有無限 dedicated bandwidth。
   - Level / Task / Source：SAA → SAP｜SAA-3.5、SAP-2.5、SAP-2.6｜[Enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)

5. **Retention、checkpoint、replay 與 duplicate processing**
   - Intent：consumer故障六小時後重啟，需從 checkpoint回放且 side effect不能重複。
   - Correct principle：retention必須覆蓋 outage/replay window；consumer保存 checkpoint並從 sequence position恢復。Delivery/processing可重複，consumer需 idempotency/deduplication。
   - Distractors：(1) checkpoint表示 record從 stream永久刪除；(2) retention到期後仍可任意讀全部歷史；(3) Kinesis自動保證外部付款 side effect exactly once。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAP-2.4｜[Developing consumers with KCL](https://docs.aws.amazon.com/streams/latest/dev/developing-consumers-with-kcl.html)

6. **Consumer lag、backpressure 與 resharding**
   - Intent：`IteratorAgeMilliseconds`持續增加，但 producer無 throttling。
   - Correct principle：lag表示 consumer處理速度落後；檢查 consumer errors/concurrency、shard parallelism、downstream latency與 hot shard。擴 producer或延長 retention只延後資料遺失，不會修復 consumer bottleneck。
   - Distractors：(1) 增加 producer batch size必然降低 iterator age；(2) 關閉 checkpoint讓 consumer更快且不重複；(3) 只增加 retention即可恢復 real-time SLA。
   - Level / Task / Source：SAP｜SAP-2.4、SAP-3.3｜[Monitoring Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)

7. **Kinesis encryption 與 least privilege**
   - Intent：producer只能 PutRecord，consumer只能讀指定 stream，使用 customer managed KMS key。
   - Correct principle：IAM分離 write/read actions與 stream ARN；SSE-KMS需 key policy允許服務/callers所需 use，並使用 TLS/VPC endpoint按需求限制 network path。Encryption不會授予 data access。
   - Distractors：(1) KMS key policy Allow即可省略所有 Kinesis IAM permissions；(2) stream ARN無法用於 IAM Resource；(3) private endpoint會自動允許任何 VPC principal讀 stream。
   - Level / Task / Source：SAP｜SAP-2.3｜[Kinesis Data Streams security](https://docs.aws.amazon.com/streams/latest/dev/security.html)

8. **MSK partition、replication 與 consumer groups**
   - Intent：既有 Kafka clients需要 topic partitions、replication factor、consumer group semantics。
   - Correct principle：MSK管理 brokers/control infrastructure；topic partition決定 ordering/parallelism，replication factor與 broker/AZ配置影響 resilience，consumer group內 partitions分配給 members。仍需規劃 keys、retention與 lag。
   - Distractors：(1) consumer group中每個 member都會收到每個 record；(2) replication factor增加 application partitions的平行度但不影響 durability；(3) MSK會自動修正所有 hot keys與 schema incompatibility。
   - Level / Task / Source：SAA → SAP｜SAA-3.5、SAP-2.4、SAP-2.5｜[Amazon MSK concepts](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)

9. **MSK Provisioned、Serverless 與 Kinesis比較**
   - Intent：Kafka API/ecosystem相容性、broker controls與最少營運負擔三者取捨。
   - Correct principle：需要 Kafka protocol/ecosystem或既有 clients時比較 MSK；Serverless減少 capacity management但有支援範圍/配額，Provisioned提供更多 broker/storage/config控制；AWS-native簡化 stream可考慮 Kinesis。
   - Distractors：(1) Kinesis提供原生 Kafka broker endpoint且完全相容；(2) MSK Serverless沒有任何 partition/throughput限制；(3) 選 MSK後不需管理 topic、consumer lag或 schema。
   - Level / Task / Source：SAP｜SAP-2.5、SAP-2.6、SAP-4.4｜[MSK Provisioned and Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/msk-serverless.html)

10. **Amazon Data Firehose 的 delivery contract**
    - Intent：records需 buffer、可選 transformation後持續送 S3/OpenSearch/warehouse，並保存失敗資料。
    - Correct principle：Firehose是 managed delivery stream，依 size/time buffer交付，可調用 Lambda transformation並配置 backup/error prefix；delivery可能有延遲/重試，destination consumer不是任意 offset replay。
    - Distractors：(1) Firehose提供 shard內 multi-consumer checkpoint API；(2) buffer interval為零即可保證同步逐筆 delivery；(3) delivery成功即代表下游 business transaction exactly once。
    - Level / Task / Source：SAA → SAP｜SAA-3.5、SAP-2.4｜[What is Amazon Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)

---

## 第 51 章：OpenSearch、DocumentDB、Neptune 與 Purpose-built DB

### 現有題目缺陷

- 第 1 題一次列出 OpenSearch、DocumentDB、Neptune、Timestream，屬服務字典，不測 query shape、write ownership或 consistency。
- 第 2、4 題重複 OpenSearch config清單；沒有 shard sizing、mapping、index lifecycle、heap/storage與 query latency scenario。
- 第 3 題的 DocumentDB敘述與 OpenSearch敘述都各自正確，只做服務名稱配對；且「共享 distributed cluster storage」太籠統，無法測 compatibility差異。
- 第 5 題仍是通用治理，未測 dual-write、CDC、reindex、backup/restore或 failover。
- Timestream完全沒被實際考；OpenSearch authorization、DocumentDB API compatibility、Neptune graph model與各服務 DR都缺漏。

### 10 個原創、非重疊 intents

1. **OpenSearch作 derived search index，不作唯一 system of record**
   - Intent：交易保存在 durable database，需全文搜尋與聚合；index可重建。
   - Correct principle：以 CDC/events將 authoritative data投影到 OpenSearch，處理 retry/idempotency與 reindex；搜尋 index可 stale且 mapping不同，不應默認為唯一交易真相。
   - Distractors：(1) 寫入 OpenSearch後可刪除所有交易 backup；(2) inverted index提供跨 documents ACID transaction；(3) search replica等同 source database PITR。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.4｜[Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)

2. **OpenSearch shards、replicas 與 capacity**
   - Intent：過多 tiny shards造成 heap/cluster-state壓力；單一 huge shard恢復慢。
   - Correct principle：依 index size、ingest/query rate、node storage/heap與 recovery目標設 primary shards/replicas；replicas增加 read/availability但也耗 storage/indexing resources，需以 metrics與 load test調整。
   - Distractors：(1) shard越多永遠越快且零 overhead；(2) replicas增加 primary write throughput且不增加 storage；(3) 一個 primary shard可跨 nodes切成多段同時恢復。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5｜[Sizing OpenSearch domains](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html)

3. **OpenSearch network、domain policy、IAM 與 fine-grained access**
   - Intent：VPC-only domain中，不同 users只能查各自 indices，requests需簽署或 basic auth。
   - Correct principle：VPC/SG控制 reachability，domain access policy/IAM控制誰可呼叫，fine-grained access control映射 users/roles到 index/document/field permissions；使用 TLS與 encryption。各層不可互相替代。
   - Distractors：(1) 放 private subnet後所有 VPC principals自動有 admin權限；(2) security group可限制到 OpenSearch index名稱；(3) FGAC role會自動修改 KMS key policy。
   - Level / Task / Source：SAP｜SAP-2.3｜[OpenSearch access control](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html)

4. **OpenSearch Multi-AZ、snapshots 與 index lifecycle**
   - Intent：抵抗 node/AZ failure、保留可恢復備份並自動 rollover/delete舊 logs。
   - Correct principle：配置 Multi-AZ/standby與 replicas處理 availability；automated/manual snapshots處理 restore；Index State Management處理 rollover/retention。Replica不是 backup，delete policy也不是 DR。
   - Distractors：(1) 有 replica就能恢復誤刪 index的任意歷史版本；(2) snapshot提供同步 zero-RPO failover；(3) ISM rollover會自動複寫到另一 Region。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.4｜[OpenSearch snapshots](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html)

5. **DocumentDB compatibility不是 MongoDB identity**
   - Intent：既有 MongoDB application使用特定 operators、drivers與 administration features，評估遷移。
   - Correct principle：DocumentDB提供 MongoDB-compatible API的特定版本/功能集合，不是 MongoDB binary；遷移前以 compatibility docs與真實 queries測試 operators、indexes、transactions與 drivers。
   - Distractors：(1) 所有 MongoDB server extensions與 admin commands必然相容；(2) 只要資料是 JSON就必須選 DocumentDB；(3) 相容 API代表性能與 consistency完全相同。
   - Level / Task / Source：SAP｜SAP-4.1、SAP-4.2｜[Amazon DocumentDB compatibility](https://docs.aws.amazon.com/documentdb/latest/developerguide/compatibility.html)

6. **DocumentDB cluster storage、replicas、failover與 backup**
   - Intent：document workload需要 reader scaling、AZ failover與 PITR。
   - Correct principle：cluster instances共享 distributed cluster storage；primary處理 writes、replicas可讀並可 promotion。設定跨 AZ replicas、backup retention/PITR、KMS與 client retry/read preference；replication不取代 backup。
   - Distractors：(1) 每個 replica有獨立需手動同步的 filesystem；(2) reader endpoint提供全域 strong read-after-write保證；(3) 有三個 replicas即可恢復數日前誤刪。
   - Level / Task / Source：SAA → SAP｜SAA-2.2、SAA-3.3、SAP-2.2｜[Amazon DocumentDB clusters](https://docs.aws.amazon.com/documentdb/latest/developerguide/db-cluster-manage-performance.html)

7. **Neptune property graph/RDF 與 traversal**
   - Intent：詐欺分析需多跳遍歷 account-device-address關係，而非大量 relational self-joins。
   - Correct principle：Neptune針對 graph model與 traversals，依 property graph或 RDF選 Gremlin/openCypher/SPARQL；先由 query patterns建 vertices/edges與 indexes，不能只因資料「有關聯」就選 graph。
   - Distractors：(1) Neptune主要是全文 inverted-index engine；(2) graph database會自動發現所有 business relationships而不需 model；(3) SQL foreign keys可直接當 SPARQL query無轉換執行。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-4.3｜[What is Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/intro.html)

8. **Neptune HA、read replicas、backup與 Global Database**
   - Intent：graph workload需跨 AZ failover、read scale與跨 Region DR。
   - Correct principle：cluster volume跨 AZ，read replicas可 promotion/read scale；automated backups/PITR處理恢復，Global Database用於跨 Region read/DR且需理解 replication lag/promotion。Endpoint與 client reconnect仍要設計。
   - Distractors：(1) reader replica是任意歷史 point-in-time backup；(2) Global Database每個 Region預設 multi-writer synchronous；(3) cluster endpoint可保留失敗前所有 TCP sessions。
   - Level / Task / Source：SAP｜SAP-2.2、SAP-2.4｜[Neptune high availability](https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-ha.html)

9. **Timestream 資料模型與 retention tiers**
   - Intent：IoT metrics以 time/device查詢，近期資料高頻、歷史資料低頻，需自動 retention。
   - Correct principle：以 dimensions、time、measure建模，設定 memory store與 magnetic store retention；query、ingest與 scheduled queries依 time-series pattern設計。它不是通用 document/full-text/graph database。
   - Distractors：(1) memory store retention到期後資料必然直接永久刪除、不進 magnetic store；(2) Timestream最適合多跳 social graph traversal；(3) 以單一巨大 JSON document可取代 dimensions/time model並獲得相同性能。
   - Level / Task / Source：SAA → SAP｜SAA-3.3、SAP-2.5、SAP-2.6｜[What is Amazon Timestream](https://docs.aws.amazon.com/timestream/latest/developerguide/what-is-timestream.html)

10. **Purpose-built database selection與同步成本**
    - Intent：交易、全文搜尋、graph traversal、time series與 Mongo-compatible documents同時存在。
    - Correct principle：以 authoritative state、query/access pattern、consistency、scale與 operational cost拆分；RDS/Aurora管 transactions、OpenSearch管 search projection、Neptune管 graph、Timestream管 time series、DocumentDB只在相容 document需求成立時使用。跨 stores需 CDC/outbox、reconciliation、backup與 ownership。
    - Distractors：(1) 將所有資料複製到每個 database且不指定 owner；(2) 只因 schema-less就讓 OpenSearch成唯一 payment store；(3) purpose-built表示服務間天然同步 exactly once且無 reconciliation。
    - Level / Task / Source：SAP｜SAP-2.4、SAP-2.5、SAP-4.3、SAP-4.4｜[AWS purpose-built databases](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html)

---

## 實作驗收條件

- 第 41–51 章各自必須恰好實作上述 10 個 intents，共 110 題；不可再由五題通用模板換字生成。
- 每題只允許一個主要知識判斷。複選題必須在 intent明確要求兩個互補 controls時使用，且不能靠「最長選項」猜答案。
- 每題固定四個選項：一個正確原則、三個在其他情境可能合理但違反本題 constraint的 distractors。不得使用「AWS自動理解所有 business requirements」「全部都部署」「故障後人工處理」等無鑑別度選項。
- 解答必須逐項說明：哪個 requirement、data/access semantic、failure mode或 cost dimension讓答案成立或翻轉。
- 題目不得引用 exam dumps；來源僅用來驗證公開服務行為與官方 exam task coverage。
- 實作後應加入靜態檢查：每章題數為 10、normalized choices無重複、單選題恰好一個 answer、每題三個 distractor explanations、同章 prompt/intent相似度門檻，以及所有 source/task IDs存在。

SUPERSET_WORKER_DONE
{
  "task": "P04-audit",
  "status": "complete",
  "file": "tools/aws_exam_audits/part_04.md",
  "chapters": [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
  "intents_per_chapter": 10,
  "total_intents": 110,
  "exam_dumps_used": false
}
