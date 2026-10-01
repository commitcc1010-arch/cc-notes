# AWS 題庫獨立審查：Part 08（第 79–90 章）

審查日期：2026-10-01
審查範圍：`tools/aws_question_banks/part_08.json`，共 120 題
審查角色：獨立審查；未修改題庫

## 結論

本批題目的架構方向多數正確，章節涵蓋 multi-account、集中網路與安全、multi-Region、備份、FinOps、migration、7Rs、modernization 與持續改善，且未發現直接重製官方 sample、考古題或 exam dump 的跡象。

但目前不能發布，原因不只是少數文字問題：

1. 96 題單選中，94 題的正解是四個選項中「唯一最長」；`ch083-q02` 的正解並列最長。換言之，95/96 題可用長度線索命中，這是全批題庫的阻斷性測量瑕疵。
2. 115/120 題至少有一個錯誤選項使用「永遠、全部、任何、一律、自動、無需」等絕對詞，且常是明顯荒謬敘述。讀者多半只需辨認語氣，不必理解 AWS。
3. 複選題的答案位置也有偏差：24 題中選項 A 為正解 16 次；每章第 3 題有 11/12 題選 A；每章第 8 題有 9/12 題選 E。
4. 有數題未反映 2026-10-01 的服務現況，另有若干 source deep link 與 task mapping 不足。
5. 題幹唯一性檢查通過：本 part 沒有正規化後完全重複的 prompt/tested 欄位；與其餘題庫也未找到高相似度複製題。問題在選項模板與答案線索，而非題幹抄寫。

最終判定：需要修訂後重新逐題驗證。

## 審查基準

主要基準均為 AWS 官方資料：

- [SAP-C02 官方考綱](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)
- [SAP-C02 官方 sample questions](https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf)
- 各題 `source_ids` 對應的 AWS 官方文件
- [AWS services and capabilities moving to maintenance](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/aws-service-availability.html)
- [Cost allocation tag backfill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/backfill-cost-allocation-tags.html)
- [Logically air-gapped vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)
- [AWS DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_SchemaConversion.html)
- [AWS Transform MGN test and cutover actions](https://docs.aws.amazon.com/mgn/latest/ug/test-cutover-action.html)

Jayendra Patil 頁面只檢查是否作為主題靈感，未把其敘述當作正確答案依據。本批 inspiration links 都是主題文章，不是題庫頁或真題來源。

## 必須修正的內容問題

| 題號 | 嚴重度 | 問題 |
|---|---:|---|
| `ch081-q04` | Critical | 題目把 CloudTrail Lake 當成可直接推薦的新方案。AWS 已公告 2026-05-20 後不再接受新客戶使用 CloudTrail Lake；正解必須限定為既有客戶，或對新客戶改用 CloudTrail trails + S3/Athena、CloudWatch 等現行方案。現有 sources 也缺 availability-change 官方頁。 |
| `ch081-q07` | High | 題目中的 security score、standards/controls 與 central configuration 屬於 **AWS Security Hub CSPM**。2025 年後「AWS Security Hub」也指新的整合式服務；在 2026 題庫中只寫 Security Hub 會混淆兩個 service contract。 |
| `ch081-q10` | High | 同上。「Security Hub controls」應明確寫 Security Hub CSPM controls；`CT-LAKE` 又不是本題 rollout/retention 正解所需的精確來源。 |
| `ch084-q05` | High | 正解與解析斷言仍需要明確的「copy policy」。現行 AWS Backup 已支援把 primary backups 直接建立到 logically air-gapped vault；需要的是 backup plan 的 resource selection，或依架構使用 copy action，不能一律說必須 copy。 |
| `ch085-q02` | High | 正解只說啟用前歷史「可能不會追溯補齊」，漏掉現行 Billing 可要求最多 12 個月的 cost-allocation-tag backfill。題幹正是在問歷史不完整，正解應包含 activation、propagation、backfill 的可用範圍與限制。 |
| `ch087-q01` | Medium | 把 DMS Schema Conversion 與 SCT 並列成無差別的現行選項。官方已建議使用 DMS Schema Conversion；SCT 應標示為 legacy/existing workflow，而不是新方案的等價預設。 |
| `ch087-q04` | Critical | 已發生 source 與 target 雙寫後，現有正解先 fence source、再「啟動最新 cutover instances」，可能遺失 target 在 split-brain 期間已接受的訂單。MGN 是單向 block replication，不會把 target-side writes 回寫 source 或合併進新 cutover instance。第一步應停止雙寫、選定 authoritative side、盤點與 reconcile divergence，再決定 rollback 或完成 cutover。 |
| `ch087-q07` | Medium | 同 `ch087-q01`：若保留 SCT，必須標示為 legacy；新評估應優先呈現 DMS Schema Conversion 的現行路徑。 |

## Source deep-link 問題

120 個 source URL 均可連線或正常 redirect，但「HTTP 200」不等於足以證明題目。以下題目的來源應換成直接支持 tested claim 的官方 deep link：

| 題號 | 問題 |
|---|---|
| `ch080-q07` | `TGW-RT` 不支持 Direct Connect resiliency、BGP/MTU 或 VPN backup；保留 `DX-RESILIENCY`，另補 Direct Connect gateway/TGW association 的精確頁面即可。 |
| `ch081-q04` | 缺 CloudTrail Lake 2026 availability-change 頁；現有 `SRA-LOG` 也不能補足新客戶限制。 |
| `ch081-q08` | IAM cross-account 與 log archive 文件不足以直接支持獨立 emergency-access identity、approval 與演練要求；應補 AWS SRA/SEC emergency-access guidance。 |
| `ch082-q01` | 正解包含 customer identity service，但 sources 沒有 Cognito/application identity 官方頁。 |
| `ch082-q06` | `CT-ORGTRAIL` 只支持 organization trail，不能直接支持 SourceIdentity 在 CloudTrail 中的 attribution；應補 SourceIdentity/CloudTrail userIdentity 文件。 |
| `ch083-q08` | Route 53 routing 與一般 DR 文件不能證明 data residency、de-identification 與 permitted projection；需補 AWS data residency/sovereignty 與服務 Region-scope 文件。 |
| `ch085-q05` | `COST-EXPLORER` 指向 Cost Management 總覽，沒有直接定義 unblended、amortized、net/effective cost。 |
| `ch086-q07` | 題目刻意排除 Snowball Edge 新客戶，但正解只說「physical option」，沒有指出並引用當前可用替代途徑，例如 Data Transfer Terminal 或合作夥伴方案。 |
| `ch087-q03` | `MGN-CUTOVER` 的 `/lifecycle.html` 已 redirect 到 migration dashboard，無法精確支持 test launch、finalize testing 與 cutover lifecycle。 |
| `ch087-q04` | 同上，且 FAQ 只能證明 rename，不能支持 split-brain remediation。 |
| `ch087-q08` | DMS Welcome 頁不足以支持 LOB mode、table mappings、parallel load 與 replication-instance memory trade-off。 |
| `ch089-q08` | Outbox 文件不支持 API/event schema evolution、deprecation window 與 tolerant reader。 |
| `ch089-q09` | Outbox 文件不支持 expand/contract database migration 或 ECS blue/green state rollback；應補 schema evolution/deployment 官方 guidance。 |
| `ch090-q07` | ECS blue/green 與 Control Tower drift 都不是 organization-wide network-policy rollout/state rollback 的直接來源。 |

## Task mapping 問題

| 題號 | 問題 |
|---|---|
| `ch081-q04` | 目前只有 `SAP-2.5`、`SAP-2.6`，但核心是集中 audit evidence、security logging 與現有環境改善；應至少映射 `SAP-1.2` 或 `SAP-3.2`，視題幹重寫後再決定是否保留 cost/performance。 |
| `ch085-q04` | CUR 2.0 schema/pipeline migration 不是主要的 performance-objective task；`SAP-2.5` 應改成 operational improvement/modernization 相關 task。 |
| `ch086-q08` | 題目明確是 migration coexistence，卻只有 network/reliability mapping；應加入 `SAP-4.2`。 |
| `ch087-q10` | 整題是 heterogeneous database migration cutover，卻完全沒有 `SAP-4.2`；只標 deployment/business-continuity 不完整。 |
| `ch090-q07` | 題目核心包含 network security policy rollout，只有 deployment/reliability；應依重寫後加入 security-improvement mapping，並移除不相干 source。 |

## 題目設計與答案偏差

### 單選題

- 96 題單選的答案位置總數為 A=20、B=23、C=26、D=27；總體位置分布表面上尚可。
- 但 94 題正解是唯一最長選項；`ch083-q02` 正解並列最長。只有 `ch081-q04` 的正解不是最長。
- 正解常包含 5–9 個正確實務動作，錯誤選項則只有一句明顯錯誤的絕對敘述。這讓測驗測到閱讀線索，而不是 architecture judgment。
- 修訂時不能只把錯誤選項加長；應把 3 個 distractors 改成在某些條件下合理、但因題目 hard constraint 而落敗的鄰近方案。

### 複選題

- 24 題共 48 個正解位置：A=16、B=8、C=9、D=6、E=9。
- 每章第 3 題幾乎固定含 A；每章第 8 題高度偏向 E。
- 多數複選題仍是「兩個完整成熟的做法 + 三個荒謬絕對句」，不具官方 sample 常見的鄰近選項辨識難度。

### 跨題重複

- 沒有完全相同的 prompt 或 tested 欄位。
- 沒有偵測到與其他 parts 的高相似度題幹複製。
- `ch084-q06`、`ch084-q10`、`ch090-q08` 都談 restore/game day，但分別測 restore validation、ownership、RTO/RPO failure experiment，知識角度仍可區分。
- `ch088-q08`、`ch089-q02` 都談 incremental modernization，但前者測 portfolio/deadline，後者測 strangler traffic rollout，也可保留。

## 逐題審查

以下的 `OK` 只代表 architecture claim、正解與 mapping 沒有另發現獨立錯誤；所有題目仍受前述「正解長度與荒謬 distractor」全域 blocker 影響。

### 第 79 章：Landing Zone 與 Multi-account Strategy

| 題號 | 內容審查 |
|---|---|
| `ch079-q01` | OK：帳號作為 quota、billing、root 與 blast-radius 邊界，`SAP-1.4` 合理。 |
| `ch079-q02` | OK：OU 應反映穩定 governance boundary，而非易變組織圖。 |
| `ch079-q03` | OK：SCP 不授權、explicit deny 無法被 AdministratorAccess 覆蓋；management account 例外正確。 |
| `ch079-q04` | OK：management account 最小化 workload，使用 delegated administrator。 |
| `ch079-q05` | OK：preventive/detective/proactive control 的執行方式與時點正確。 |
| `ch079-q06` | OK：Account Factory/AFT 作為可重複 account vending workflow 合理。 |
| `ch079-q07` | OK：brownfield Control Tower 導入採 inventory、pilot、waves 與 drift remediation。 |
| `ch079-q08` | OK：先判斷 drift 類型，再 repair/re-register 並修正 bypass path。 |
| `ch079-q09` | OK：SCP 先以 evidence、test OU、emergency path 與 rollback 漸進推出。 |
| `ch079-q10` | OK：account ownership、budget、escalation 與 lifecycle metadata 合理。 |

### 第 80 章：Centralized Network 與 Inspection VPC

| 題號 | 內容審查 |
|---|---|
| `ch080-q01` | OK：TGW 解決 transitive hub/segmentation，PrivateLink 解決 service-only exposure。 |
| `ch080-q02` | OK：association 與 propagation 的責任區分正確。 |
| `ch080-q03` | OK：stateful inspection 需要雙向路由與 TGW appliance mode。 |
| `ch080-q04` | OK：Network Firewall endpoint 與 route 應 AZ-aligned，避免單 AZ 與 hairpin。 |
| `ch080-q05` | OK：第三方 appliance fleet 使用 GWLB；Network Firewall 不載入任意 VM image。 |
| `ch080-q06` | OK：RAM 分享 TGW 不會自動建立完整 data path。 |
| `ch080-q07` | REVISE-SOURCE：答案方向正確，但 `TGW-RT` 不是本題 Direct Connect resiliency 的直接來源。 |
| `ch080-q08` | OK：overlapping CIDR 的短期 service exposure 與長期 renumbering 分工合理。 |
| `ch080-q09` | OK：inbound/outbound Resolver endpoint 的方向與 DNS Firewall 責任正確。 |
| `ch080-q10` | OK：central egress rollout 同時量測 capacity、cost、blast radius 與 fallback。 |

### 第 81 章：Centralized Logging 與 Security Accounts

| 題號 | 內容審查 |
|---|---|
| `ch081-q01` | OK：organization trail 到獨立 Log Archive account 可讓 evidence 脫離 compromised account。 |
| `ch081-q02` | OK：multi-Region organization trail 加 selective data events，避免無界成本。 |
| `ch081-q03` | OK：digest validation 處理可驗證完整性；Object Lock 處理 retention/deletion。 |
| `ch081-q04` | REVISE-FACT/TASK/SOURCE：CloudTrail Lake 新客戶限制未揭露，task mapping 與 availability source 也錯缺。 |
| `ch081-q05` | OK：Config 回答 configuration state/history，CloudTrail 回答 API caller/change。 |
| `ch081-q06` | OK：GuardDuty 為 Regional detection；delegated admin、auto-enable 與 protection plans 需逐 Region 規劃。 |
| `ch081-q07` | REVISE-TERM：security score/controls/central configuration 應明確稱 Security Hub CSPM。 |
| `ch081-q08` | REVISE-SOURCE：架構原則合理，但 sources 未直接支持 independent emergency-access path。 |
| `ch081-q09` | OK：enrollment、Region、delegated admin、collector 狀態、S3/KMS 與 delivery error 的調查順序合理。 |
| `ch081-q10` | REVISE-TERM/SOURCE：應稱 Security Hub CSPM controls；`CT-LAKE` 與正解不直接相關。 |

### 第 82 章：Enterprise Identity 與 Cross-account Authorization

| 題號 | 內容審查 |
|---|---|
| `ch082-q01` | REVISE-SOURCE：workforce/workload/customer identity 分工正確，但缺 application identity/Cognito 官方來源。 |
| `ch082-q02` | OK：group + permission set + account assignment 模型正確。 |
| `ch082-q03` | OK：跨帳號 AssumeRole 需要 caller permission 與 target trust/conditions，並受其他 deny 限制。 |
| `ch082-q04` | OK：第三方指定 principal、customer-specific external ID 與 least privilege 正確。 |
| `ch082-q05` | OK：ABAC 的安全性依賴可信 attribute provenance 與 tag mutation control。 |
| `ch082-q06` | REVISE-SOURCE：SourceIdentity/transitive session tag 的答案合理，但 organization-trail 文件不是 attribution deep link。 |
| `ch082-q07` | OK：session policy 只能縮小 resulting session，不能增加 role 權限；解析應避免把它稱為正式的 IAM permissions boundary。 |
| `ch082-q08` | OK：Identity Center delegated administration 不會消除 management account 的保留責任。 |
| `ch082-q09` | OK：emergency path 應與主要 IdP/approval 故障域解耦並定期演練。 |
| `ch082-q10` | OK：以 access evidence 建新版 permission set、pilot、監控與 rollback。 |

### 第 83 章：Global Application 與 Multi-Region Data

| 題號 | 內容審查 |
|---|---|
| `ch083-q01` | OK：global entry 與 mutable-state readiness 必須分開設計。 |
| `ch083-q02` | OK：固定 anycast IP、TCP/UDP 與 AWS backbone ingress 對應 Global Accelerator。 |
| `ch083-q03` | OK：DNS TTL/cache/既有連線與完整 regional write readiness 都需納入。 |
| `ch083-q04` | OK：Aurora Global Database 保持單一 primary writer，secondary 提供 local reads/DR；write forwarding 不等於 multi-master。 |
| `ch083-q05` | OK：現行 global tables 應區分 MREC 與 MRSC，不能再一概稱 eventual consistency。 |
| `ch083-q06` | OK：balance 類 invariant 應使用 write ownership/適當 consistency、idempotency 與 reconciliation。 |
| `ch083-q07` | OK：keys、secrets、artifacts、quota、certificate、checkpoint 與 allowlist 都是 regional readiness。 |
| `ch083-q08` | REVISE-SOURCE：data residency 原則可接受，但現有 Route 53/DR sources 不支持法律與資料治理 claim。 |
| `ch083-q09` | OK：database role transition、traffic transition、validation、reconciliation/failback 應置於同一 runbook。 |
| `ch083-q10` | OK：由 RTO/RPO/usage 與總成本選 DR pattern，而非預設 full active-active。 |

### 第 84 章：Organization-wide Backup、DR 與 Compliance

| 題號 | 內容審查 |
|---|---|
| `ch084-q01` | OK：Organizations backup policy 建 schedule/selection/lifecycle；SCP 不會執行 backup。 |
| `ch084-q02` | OK：destination account custody、vault/KMS policy 與 delete isolation 是 ransomware boundary。 |
| `ch084-q03` | OK：recovery point 不等於可服務的 DR stack；daily backup 也不能證明 5 分鐘 RPO。 |
| `ch084-q04` | OK：Compliance mode 在 grace period 後不可移除；Governance mode 保留受權限控制的變更。 |
| `ch084-q05` | REVISE-FACT：現行 logically air-gapped vault 支援 primary backup；不能一律要求 copy policy。 |
| `ch084-q06` | OK：restore testing 加 application/data validation 才能證明 recoverability。 |
| `ch084-q07` | OK：Backup Audit Manager 是 compliance evaluation，不是 preventive control，也不等同 business recovery。 |
| `ch084-q08` | OK：PITR 處理短 recovery window；scheduled monthly recovery points 處理七年 retention。 |
| `ch084-q09` | OK：cold tier 必須考慮 resource support、minimum duration、restore latency 與 retention。 |
| `ch084-q10` | OK：immutable copies 仍需 KMS/network/restore/validation ownership 與 game day。 |

### 第 85 章：Portfolio Cost、Tagging 與 Chargeback

| 題號 | 內容審查 |
|---|---|
| `ch085-q01` | OK：先建立 taxonomy、owners、normalization 與 activation/reconciliation。 |
| `ch085-q02` | REVISE-FACT：漏掉目前可要求最多 12 個月 cost-allocation-tag backfill。 |
| `ch085-q03` | OK：account tags 提供高層歸屬；shared account 仍需 resource/usage driver。 |
| `ch085-q04` | REVISE-TASK：parallel export/schema reconciliation 正確，但 `SAP-2.5` 不是主要 task。 |
| `ch085-q05` | REVISE-SOURCE：成本語意正確，但來源過於泛化，未直接定義各 cost metric。 |
| `ch085-q06` | OK：shared-cost allocation 應依 driver、版本化、可核對並保留 raw view。 |
| `ch085-q07` | OK：Savings Plans sharing 與 commitment/benefit ownership 分開治理。 |
| `ch085-q08` | OK：Budgets 不是 per-request synchronous circuit breaker；需搭配 technical guardrails。 |
| `ch085-q09` | OK：Cost Anomaly Detection 處理相對歷史模式，與固定 Budget threshold 互補。 |
| `ch085-q10` | OK：unit economics 必須 normalization demand，且納入 retries、toil、transfer 與 dual-run。 |

### 第 86 章：Migration Assessment、Portfolio 與 Wave Planning

| 題號 | 內容審查 |
|---|---|
| `ch086-q01` | OK：2026 新客戶應以 AWS Transform 等現行 workflow，結合 CMDB、owner 與 business evidence。 |
| `ch086-q02` | OK：wave 以可共同運作/cutover 的 dependency move group 分組，而非固定 server count。 |
| `ch086-q03` | OK：discovery window 要涵蓋 business cycle，並用訪談、telemetry 與 rehearsal 交叉驗證。 |
| `ch086-q04` | OK：business case 應包含 rightsizing、license、dual-run、transfer、labor、risk 與 outcomes。 |
| `ch086-q05` | OK：先完成平台 prerequisite，以低風險代表 workload 建立 factory evidence。 |
| `ch086-q06` | OK：wave exit 應以 target readiness、rollback、support 與 business acceptance 定義。 |
| `ch086-q07` | REVISE-SOURCE/QUALITY：正解只寫不具名的 physical option，未提供 2026 可選服務與精確官方來源，考生無法做 service-level decision。 |
| `ch086-q08` | REVISE-TASK：DX/VPN 與 hybrid DNS 設計正確，但題目屬 migration coexistence，應加入 `SAP-4.2`。 |
| `ch086-q09` | OK：DataSync 處理 transfer/sync；Storage Gateway 維持長期 hybrid storage interface。 |
| `ch086-q10` | OK：限制 WIP、建立 playbook/automation、delegated ownership 與 flow metrics。 |

### 第 87 章：Application Migration Service、DMS 與 Schema Conversion

| 題號 | 內容審查 |
|---|---|
| `ch087-q01` | REVISE-CURRENCY：MGN/DMS/DataSync 分工正確；Schema Conversion 應優先用 DMS SC，SCT 標示 legacy。 |
| `ch087-q02` | OK：MGN replication lag 取決於 staging resources、network、permissions、bandwidth 與 source change rate。 |
| `ch087-q03` | REVISE-SOURCE：test/acceptance 答案正確，但 lifecycle deep link 已 redirect 到不精確頁面。 |
| `ch087-q04` | REVISE-FACT/SOURCE：split-brain 後的處理順序可能丟失 target writes；MGN 不做雙向 reconcile。 |
| `ch087-q05` | OK：持續寫入、低 downtime 的既有資料庫採 full load + CDC。 |
| `ch087-q06` | OK：homogeneous same-engine 與 heterogeneous conversion 的責任邊界正確。 |
| `ch087-q07` | REVISE-CURRENCY：conversion/action-item/testing 正確，但 SCT 應標示 legacy。 |
| `ch087-q08` | REVISE-SOURCE：LOB/mapping/capacity 判斷合理，但 DMS Welcome 不是可驗證這些細節的 deep link。 |
| `ch087-q09` | OK：DMS validation 只是一層，仍需 schema、application 與 business reconciliation。 |
| `ch087-q10` | REVISE-TASK：cutover/fence/CDC/validation 答案正確，但缺核心 `SAP-4.2` mapping。 |

### 第 88 章：7Rs

| 題號 | 內容審查 |
|---|---|
| `ch088-q01` | OK：7Rs 應由 workload business/technical evidence 決定，不是一律 refactor。 |
| `ch088-q02` | OK：Retire 前要處理 consumers、records、integration、access、contract 與觀察期。 |
| `ch088-q03` | OK：Retain 仍需要 owner、risk、hybrid plan、investment 與 revisit trigger。 |
| `ch088-q04` | OK：保留 VMware operating model、快速搬離機房符合 Relocate。 |
| `ch088-q05` | OK：deadline 且暫無 modernization budget 時，Rehost + post-migration backlog 合理。 |
| `ch088-q06` | OK：self-managed MySQL 到 RDS MySQL 是 bounded Replatform。 |
| `ch088-q07` | OK：Repurchase 必須評估 process、identity、integration、residency、contract 與 exit。 |
| `ch088-q08` | OK：高價值 capability 可 refactor，但應以 incremental strangler step 避免阻塞 facility exit。 |
| `ch088-q09` | OK：portfolio mix 應同時使用 retire、repurchase、rehost/relocate 與少量 refactor。 |
| `ch088-q10` | OK：migration disposition 可在實際 cost/toil/delivery evidence 後重新檢視。 |

### 第 89 章：Monolith 到 Containers／Serverless

| 題號 | 內容審查 |
|---|---|
| `ch089-q01` | OK：service boundary 應依 business capability、data authority、ownership 與 change/failure needs。 |
| `ch089-q02` | OK：facade/router、漸進流量、validation、rollback 與舊路徑淘汰符合 strangler。 |
| `ch089-q03` | OK：AWS Transform/container tooling 改善 packaging，不會自動建立 microservices/data ownership；App2Container qualifier 正確。 |
| `ch089-q04` | OK：ECS/EKS/Lambda 選型依 workload contract 與 operating model。 |
| `ch089-q05` | OK：共享資料庫下的 containers 仍高度耦合，需逐步建立 authoritative data owner。 |
| `ch089-q06` | OK：transactional outbox 消除 local DB/event dual-write gap，consumer 仍需 idempotency。 |
| `ch089-q07` | OK：Saga 以 local transactions、compensation、timeout、idempotency 與 reconciliation 管理失敗。 |
| `ch089-q08` | REVISE-SOURCE：contract-evolution 答案合理，但現有 outbox/decomposition sources 不直接支持 version/deprecation/tolerant-reader claim。 |
| `ch089-q09` | REVISE-SOURCE：expand/contract schema 與 state-aware rollback 正確，但 outbox 不是精確來源。 |
| `ch089-q10` | OK：platform 擁有 paved road；product team 擁有 behavior、data、SLO、cost 與 on-call。 |

### 第 90 章：持續改善既有系統

| 題號 | 內容審查 |
|---|---|
| `ch090-q01` | OK：先定義 workload boundary、journeys、SLO、dependencies、incidents、delivery 與 unit cost baseline。 |
| `ch090-q02` | OK：Well-Architected finding 需轉成有 owner/date/evidence 的 prioritized improvement plan。 |
| `ch090-q03` | OK：以風險降低/價值、effort、uncertainty、dependency 與 reversibility 排優先順序。 |
| `ch090-q04` | OK：Compute Optimizer 缺 memory/peak evidence 時，需補 telemetry 與 canary validation。 |
| `ch090-q05` | OK：Config compliance 不等於 runtime performance、availability 或 recoverability。 |
| `ch090-q06` | OK：可證偽 hypothesis 需 baseline、effect、metrics、window、guardrail、abort 與 rollback。 |
| `ch090-q07` | REVISE-SOURCE/TASK：state-aware wave rollout 原則正確，但 sources 不支持 network-policy claim，security mapping 也缺失。 |
| `ch090-q08` | OK：以 bounded failure experiment 實測 RTO/RPO、reconciliation 與 dependency readiness。 |
| `ch090-q09` | OK：realized savings 必須按 demand normalization，納入 transfer、dual-run、toil 與舊成本關閉。 |
| `ch090-q10` | OK：持續回顧 SLO/incidents/security/cost/debt，維護有 owner 與 evidence 的 backlog。 |

## 重新送審條件

1. 先修正所有 Critical/High factual issues。
2. 為列出的 source 問題替換成直接支持 tested claim 的 AWS 官方 deep link。
3. 修正 task mappings，尤其 migration 題不可漏掉 Domain 4。
4. 重新撰寫全部選項：正解不可系統性最長，錯誤選項不可主要依賴荒謬或絕對語氣。
5. 重新 shuffle 答案位置；複選題不可固定讓第 3 題選 A、第 8 題選 E。
6. 維持目前良好的題幹唯一性，且不得加入 dump、回憶真題或輕度改寫商業題庫。
7. 修訂後重新執行結構檢查、URL 檢查、答案長度/位置統計與逐題官方文件複核。

REVISE

## Maintainer Final Verification

驗證日期：2026-10-01（星期四）。本輪由 maintainer 在停止 subagent 後直接完成，
只接受截至今日已發布的 AWS 官方資料；晚於 2026-10-01 的日期均視為未來。

- Part 08 validator 通過：120 題、12 章。
- 96 題單選的正解位置與長度排名皆各自平均分布為 24／24／24／24；複選位置亦無固定章末模板。
- 已移除前次審查列出的「尚未完整成立」「下一個 wave 再補齊」「人工審批控管暫時風險」
  等自我揭露答案模板。以選項與解析中的 16 字以上 clause 重新掃描，沒有任何相同 clause
  出現在三題以上。
- 每個錯項已改為可部署的相鄰方案，並由題幹中的 custody、deadline、authoritative state、
  Region、cost、recovery 或 migration constraint 排除。
- CloudTrail Lake、cost-allocation-tag backfill、break-glass、MGN test/cutover 與 API
  compatibility 來源已改為 claim-level AWS 官方 deep links；未使用的 stale `MGN-CUTOVER`
  source 已移除。
- CloudTrail Lake existing-customer、Security Hub CSPM、logically air-gapped vault primary
  backup、12 個月 tag backfill、DMS Schema Conversion 與 MGN split-brain reconciliation
  等原列事實問題均已保留在修正版。
- `ch089-q07` compensation 文字已修正；全 part 不含 SAP-C03 task mapping、exam dump
  或把 2026-10-01 之後事件寫成已發生的敘述。

VERIFIED

## Verification

重新驗證日期：2026-10-01
驗證範圍：修訂後 `part_08.json` 的 120 題、原 review 全部 blocker，以及所有 official source records
題庫修改：無

### 已通過

1. 結構檢查通過：120 題、12 章，每章 10 題；96 題單選、24 題複選。
2. 單選答案位置已完全平衡：A/B/C/D 各 24 題。
3. 複選答案位置已大幅改善：A/B/C/D/E 分別出現 11/9/9/9/10 次，沒有原本第 3 題幾乎固定選 A、第 8 題高度固定選 E 的模式。
4. 「選最長答案」不再有效：96 題單選的正解長度排名恰好各有 24 題落在第 1、2、3、4 名；正解唯一最長 24 題、唯一最短 24 題，等同隨機基準。
5. 原 review 點名的 current-service facts 已修正：
   - `ch081-q04` 正確限定 CloudTrail Lake 為既有客戶，並使用 2026-05-31 的新客戶截止日；沒有把 2026-10-01 之後的日期當成既成事實。
   - `ch081-q07`、`ch081-q10` 已明確使用 Security Hub CSPM。
   - `ch084-q05` 已區分 primary backup 與 copy action，不再宣稱 logically air-gapped vault 必須經 copy policy。
   - `ch085-q02` 已加入最多 12 個月 cost-allocation-tag backfill 與適用限制。
   - `ch086-q07` 已加入 Data Transfer Terminal／partner physical-transfer 路徑，並保留 DataSync 做 online/delta transfer。
   - `ch087-q01`、`ch087-q07` 已優先使用 DMS Schema Conversion，將 SCT 標示為既有 legacy workflow。
   - `ch087-q04` 已正確處理 split-brain：先停止雙寫、選 authoritative side、盤點及 reconcile divergence，最後才 finalize/decommission。
6. 原 task-mapping 問題已修正：
   - `ch081-q04` → `SAP-1.2`, `SAP-3.2`
   - `ch085-q04` → `SAP-1.5`, `SAP-3.1`
   - `ch086-q08` 已加入 `SAP-4.2`
   - `ch087-q10` 已加入 `SAP-4.2`
   - `ch090-q07` 已加入 `SAP-3.2`
7. 其餘原 review 判為 OK 的 architecture、migration、reliability 與 distributed-system claims 沒有發現新的 factual reversal。

### 仍未通過：distractors 不是可信 near-miss

修訂雖消除了「正解最長」線索，卻建立了另一套更明顯的答案線索：

- 107 個選項重複「尚未完整成立」與「人工審批控管暫時風險」模板。
- 89 個選項出現「下一個 wave 再補齊」。
- 63 個選項出現「監控可揭露問題，但不能把這個缺口轉換成符合題意的保證」。
- 72/120 題至少有一個選項直接使用同一句「此方案接受……並以人工審批控管暫時風險」。
- 42/96 題單選只有一個選項沒有「未、缺、忽略、先做再驗證、之後再補、尚未」等自我揭露缺陷的語句，而且該選項就是正解。

因此讀者仍可採用下列捷徑，不必真正判斷 AWS：

> 選擇唯一沒有主動承認缺口、沒有「之後再補」、沒有「先上線再驗證」的選項。

具體例子：

- `ch079-q02`：正解簡潔完整；另外三項都直接寫出「組織改組時移動帳號」、「逐帳號附加」、「之後才盤點 effective policy」等已知缺陷。
- `ch081-q04`：錯誤選項直接說新客戶使用已停止開放的 Lake，或「等採購後再確認 availability」，不是可信架構師會提出的相鄰方案。
- `ch086-q07`：三個 distractors 分別主動承認超過 deadline、沒有 delta sync、交付後才確認安全與 ingest；不需要計算 600 TB/500 Mbps 也能排除。
- `ch087-q04`：三個 distractors 全都明說「未盤點另一側 writes」或「先刪 source」，沒有真正測驗 authoritative-side/reconciliation 的取捨。
- `ch090-q04`：錯誤選項直接寫「上線後再觀察」、「忽略 recommendation」、「全 fleet 後才驗證」，正解不需理解 Compute Optimizer 即可找出。

修訂要求不是再調整長度，而是把 distractors 寫成「服務與機制都真實、在另一種 constraint 下可能正確，但因本題的一個關鍵 hard constraint 落敗」。每個錯誤選項應把缺陷藏在 architecture contract 中，不能自行替考生標出「未完成／之後補／先做再驗證」。

### 仍未通過：deep links

118 個 official records 都能取得 HTTP 200，但至少下列**正在被題目引用**的 URL 會 redirect 到 guide root 或過度寬泛的章節，尚未達到 deep-link 要求：

| Source ID | 使用題目 | 驗證問題 | 應改方向 |
|---|---|---|---|
| `CT-LAKE-CHANGE` | `ch081-q04` | 目前 URL redirect 到 CloudTrail User Guide root。 | 使用 `cloudtrail-lake-service-availability-change.html`。 |
| `COST-TAG-BACKFILL` | `ch085-q02` | 目前 URL redirect 到 Billing guide root。 | 使用 `cost-allocation-backfill.html`。 |
| `SRA-INCIDENT` | `ch081-q08` | 目前 URL redirect 到 SRA root。 | 使用現行 Security Incident Response guide 或 Well-Architected incident-response deep link。 |
| `MGN-HOW` | `ch087-q01`, `q03`, `q04` | 目前 URL redirect 到 MGN guide root。 | 使用 current MGN overview 及 migration-action 頁。 |
| `MGN-TEST-CUTOVER` | `ch087-q03`, `q04` | 目前 URL redirect 到 MGN guide root。 | 使用 `source-server-actions-during-migration.html` 或 `server-test-cutover-main.html`。 |
| `API-COMPAT` | `ch089-q08` | 目前 URL redirect 到整個 microservices integration guide，未直接支持 version/deprecation/tolerant-reader claim。 | 改用直接描述 backward compatibility／契約演進的官方頁。 |

此外，source registry 仍保留未被任何題目使用且已失效 redirect 的 `MGN-CUTOVER`；若要求「全部 deep links」乾淨，應刪除或更新未使用的 stale records。

### 其他品質問題

- 大量 explanations 也共用同一段 boilerplate，常只重述「缺少某責任」，沒有說清楚該 AWS service 的實際機制或哪個 hard constraint 使選項落敗。
- `ch089-q07` 的「refund 不一定還原大幅相同世界」疑似文字錯誤，應改為「不一定還原成完全相同的狀態／世界」。
- 未發現題幹抄襲或 dump provenance；此項維持通過。

### 最終判定

Current-service facts、答案長度、複選分布與 task mappings 已通過；但 distractor validity 與 source deep-link precision 尚未通過。這兩項會直接影響題庫是否真的測到 SAP architecture judgment，因此不能標為 VERIFIED。

REVISE

## Consolidated Maintainer Verification

最終驗證日期：2026-10-01（星期四）。本節檢查的是上述 review 完成後的最新
`part_08.json`，因此取代前一輪對舊檔案的 `REVISE` 判定。

- 題庫 gate 通過：120 題、12 章；單選答案位置 A/B/C/D 各 24 題，正解長度排名亦各 24 題。
- 前輪列出的 distractor 模板在最新檔案中均為 0 次；以 16 字以上 clause 檢查，沒有同一
  clause 出現在三題以上，且沒有重複 explanation。
- 24 題複選中，正解恰為最長選項集合者為 8 題，未形成可直接套用的全域長度捷徑。
- CloudTrail Lake availability、cost-allocation-tag backfill、break-glass、MGN
  test/cutover 與 API compatibility 均已換成對應 claim 的 AWS 官方 deep link。
- 題庫未使用 exam dump、回憶真題，也未把 2026-10-01 之後的事件描述為已發生。

VERIFIED
