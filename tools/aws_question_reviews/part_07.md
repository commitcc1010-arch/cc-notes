# Part 07 Independent Review — Chapters 72–78

Review date: 2026-10-01
Scope: `tools/aws_question_banks/part_07.json`（70 題，Chapter 72–78）

## Review boundary

- 本輪逐題檢查正解、每一個干擾項解析、single/multi 題型、task mapping、題目唯一性、現行服務限制、官方來源 deep link、跨題重複與答案位置偏差。
- 服務行為以 AWS 官方文件為準；SAA-C03 與 SAP-C02 exam guides、官方公開 sample questions 只用來校準 blueprint 與題型，不複製或重製題目。
- 截至 2026-10-01，SAP-C03 的 registration 將於 2026-10-27 才開放；AWS 官方頁面要求屆時再查新版 exam guide 與 preparation resources。因此本輪不能把尚未發布的 SAP-C03 guide/sample 當成 authoritative source，也不應把任何題目標示為已完成 SAP-C03 mapping。
- 未使用 exam dumps、recalled live questions、ExamTopics 或宣稱「actual exam questions」的來源。
- 本輪沒有修改題庫。

## Overall result

題庫架構比舊版完整：70 題都有獨立 ID、每章 intents 1–10 齊全，每章 8 題 single 與 2 題 multi；沒有完全相同的 choices、explanations 或 prompts，也沒有發現與其他 part 高度相似的 prompt。所有 factual `source_ids` 都指向 AWS 官方來源；Jayendra Patil 頁面只出現在 `inspiration_ids`。

但目前仍有會影響正確性與測驗品質的阻擋問題：

1. 6 題未通過題庫 validator 的最低解析深度。
2. 5 題的服務機制不精確或答案不完整。
3. 3 題的 SAA task mapping 不符合官方 task boundary。
4. 多個來源 URL 已退化成指南首頁，不能算精確 deep link。
5. 七章答案位置使用可預測模板，會讓讀者在不知道內容時猜中答案。

## Required factual and scoring corrections

### `ch074-q01` — CodeDeploy EC2 deployment control 寫成不存在的獨立 `batch size`

目前 B 說「設定 batch size 與 minimum healthy hosts」。CodeDeploy EC2/on-premises 的 in-place deployment configuration 核心控制是 `minimum healthy hosts`（數量或百分比）；CodeDeploy 依此決定能同時離線更新多少 instances，並沒有另一個獨立的 EC2 `batch size` 設定。

Required fix:

- 保留 B 為正解，但改成「使用 in-place deployment，建立 custom deployment configuration，將 minimum healthy hosts 設為至少 32 台或 80%，並驗證 mixed-version compatibility」。
- 若正文仍使用「rolling」，要明說這是部署策略描述，不是 CodeDeploy EC2 console/API 中另一個名為 rolling 的設定。
- 來源應保留官方 CodeDeploy deployment configurations 文件。

### `ch075-q01` — EC2 managed-node identity 錯把 hybrid activation 當成同等選項

題幹明確是 EC2 instances。現行官方做法是：

- 建議使用 Default Host Management Configuration；或
- 使用附加到 EC2 的 IAM instance profile。

Hybrid activation 是 hybrid/multicloud 的非 EC2 machines 所用，不應在 EC2 題目的正解中寫成「instance profile 或 hybrid activation」。

Required fix:

- B 改為「Default Host Management Configuration 或具最小權限的 EC2 instance profile」。
- 若要保留 hybrid activation，必須放在解析中明確標示它適用於 non-EC2 hybrid/multicloud nodes。
- 將 `ssm-managed-node` 更新為目前 canonical deep link：
  `https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-instance-permissions.html`

### `ch075-q02` — Patch Manager private data path 不完整，現有選項沒有完整正解

只有 Systems Manager interface endpoints，不代表 patch operation 可完成。官方文件另要求：

- node 能取得 Patch Manager 產生的 patch baseline snapshot；此路徑使用 AWS-managed S3 patch-operation buckets；
- OS package manager 能到達已設定的 yum/apt/Windows Update/WSUS 等 repositories，或受控 internal mirror。

目前 C 只提 OS repositories/mirror，漏掉 patch-operation S3 bucket reachability。依題幹「只有 Systems Manager interface endpoints」來看，兩段 data path 都可能缺少，因此 C 不是完整答案。

Required fix:

- 將 C 補成「提供通往 Patch Manager operation S3 buckets 的 S3 endpoint/policy，以及通往核准 OS repositories 或 internal mirror 的路徑」。
- 解析要清楚分成 management/control channel、patch snapshot path、package-content path。
- 新增官方來源：
  `https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-operations-s3-buckets.html`

### `ch075-q06` — 正解把兩種 patch orchestration 寫成任意組合

C 同時寫「baseline/policy」和「schedule/Maintenance Window」，讀起來像四個元件任意混用。實際上應選一條清楚流程：

- custom patch baselines + Sunday Maintenance Window 執行 `AWS-RunPatchBaseline`；或
- Quick Setup patch policy，由 policy 定義各 OS baseline、scan/install schedules 與 reboot behavior。

Required fix:

- 依題幹選定其中一條，避免 single-answer 題的正解只是產品清單。
- 若採第一條，寫清 baseline 決定 eligible patches，Maintenance Window 決定 Sunday execution。
- 若採第二條，不要再暗示必須另外建立 Maintenance Window。

### `ch076-q08` — EventBridge DLQ 限制未交代

正解 D 的方向正確，但會讓初學者以為任意 SQS queue 都能作 EventBridge DLQ。Classic/default EventBridge rule target DLQ 的重要限制是：

- 只支援 SQS standard queue，不支援 FIFO queue；
- queue 必須與 rule/event bus 位於同一 Region；
- queue policy 必須允許 EventBridge 傳送訊息。

Required fix:

- D 與解析加入「same-Region SQS standard DLQ」和必要 queue policy。
- 將來源改為 canonical deep link：
  `https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-dlq.html`

### `ch077-q04` — Vault Lock 的「測試期」答案過度模糊

題幹要求最後要達到連高權限管理員都不能解除的 WORM，同時先保留測試期。精確機制是 compliance mode 的 grace time，而不是模糊地「測試 governance/compliance 設定」：

- 設定 `ChangeableForDays` 即建立 compliance mode；
- grace time 必須為 3–36,500 天；
- grace time 內仍可移除或調整 lock；
- lock date 後 vault lock immutable；
- governance mode 仍可由具適當 IAM 權限者移除，不符合最終硬需求。

Required fix:

- C 明確改寫為「建立 compliance-mode Vault Lock，設定並利用 grace time 驗證 min/max retention 與流程；grace time 到期後進入不可變狀態」。
- 解析分清 governance mode 與 compliance mode，不要讓讀者以為兩者可互換地滿足題幹。

### `ch077-q02` — Cross-account recovery 的 provenance 不完整

答案 D 本身可成立，但只引用 encryption 與 restore 概覽，不足以支持跨帳號 copy/restore prerequisites。

Required fix:

- 加入既有來源 `backup-cross-account`。
- 解析保留「服務/backup type 的 encryption model 不同」的限定，不要暗示所有資源都能用同一個 KMS/copy 流程。

## Task mapping corrections

### `ch076-q03`

Security group、network boundary 與 workload segmentation 屬於 SAA-C03 `SAA-1.2 Design secure workloads and applications`，不是 `SAA-1.3 Determine appropriate data security controls`。

Required fix: 將 `SAA-1.3` 改為 `SAA-1.2`。

### `ch076-q06`

自動修復 security-group ingress 仍是 workload/network security，主要 SAA mapping 應為 `SAA-1.2`；資料加密、key management、data classification 才是 `SAA-1.3` 的核心。

Required fix: 將 `SAA-1.3` 改為 `SAA-1.2`。

### `ch076-q04`

此題測 CloudTrail、Config 與 runtime telemetry 的事故關聯，主要對應 SAP-C02 `SAP-3.1` 與 `SAP-3.2`。現有 `SAA-1.3` 沒有被題幹中的 data-security decision 支持。

Required fix: 移除 `SAA-1.3`；若要保留 SAA mapping，必須先把題幹改成明確的 secure-workload 或 data-security architecture decision。

## Explanation-depth gate failures

`python3 tools/check_aws_question_banks.py --part 7` 目前回報以下 6 題有至少一個 option explanation 少於最低 32 字：

- `ch074-q03`：B
- `ch074-q08`：A
- `ch074-q10`：A
- `ch076-q09`：D
- `ch078-q02`：A
- `ch078-q05`：C

Required fix:

- 不要只補字數；每個解析應說明它違反哪一個 constraint，以及在什麼條件改變後該選項才可能合理。
- `ch076-q09` 的 B「把 retry 調到無限」是不存在的設定，干擾項過弱。改成可實際設定但仍錯誤的方案，例如只提高 maximum event age/attempts，卻不修正 authoritative IaC 與 oscillation root cause。

## Deep-link provenance defects

以下 source records 雖回傳 HTTP 200，但已 redirect 到整本指南首頁，不能直接支持題目中的具體敘述。

### `wa-plan-unsuccessful-changes`

Affected:

- `ch074-q02`
- `ch074-q07`
- `ch074-q09`
- `ch075-q10`

Replace with:

`https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html`

注意 AWS 現行 slug 使用 `unsucessful` 的拼字。

### `wa-automate-rollback`

Affected:

- `ch074-q03`
- `ch074-q09`
- `ch074-q10`

Replace with:

`https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_auto_testing_and_rollback.html`

### `ssm-patch-policies`

Affected:

- `ch075-q06`
- `ch075-q09`
- `ch075-q10`

Replace with:

`https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-policies.html`

### `eventbridge-direct-events`

Affected:

- `ch076-q05`
- `ch077-q06`

現有 URL redirect 到 EventBridge guide 首頁。依題目用途分別改用：

- AWS service/EventBridge event reference：
  `https://docs.aws.amazon.com/eventbridge/latest/ref/events.html`
- Classic/default event bus 的 CloudTrail-delivered events：
  `https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail.html`
- AWS Backup restore validation 題另保留：
  `https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html`

### `wa-runbook-process`

Affected:

- `ch076-q07`
- `ch078-q07`
- `ch078-q09`

依實際 assertion 拆成精確來源：

- Event/incident/problem process：
  `https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html`
- Runbooks：
  `https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_runbooks.html`
- Playbooks：
  `https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_playbooks.html`

### `wa-post-incident`

Affected:

- `ch076-q09`
- `ch077-q10`
- `ch078-q10`

Replace with:

`https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html`

### Blueprint provenance

題庫含大量 `SAA-1.x` 與 `SAP-3.x` task mappings，但 sources catalog 只有 SAA Domain 2 與 SAP Domain 2。至少新增：

- SAA-C03 Domain 1：
  `https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html`
- SAP-C02 Domain 3：
  `https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html`

官方 sample-question PDFs可用於檢查題幹長度、constraint density 與 multi-answer 指示，但不可重製其文字或答案結構。

## Answer-position bias

單題正解總數看似完美平均：A/B/C/D 各 14 題；但順序不是自然分布，而是明顯模板：

- Chapter 72：`B C A D B C A D AD BE`
- Chapter 73：`B C A D B C A D AD BE`
- Chapter 74：`B C A D B C A D AD BE`
- Chapter 75：`B C A D B C A D AE BE`
- Chapter 76：`B C A D B C A D AE BE`
- Chapter 77：`B D A C B D A C AE BE`
- Chapter 78：`B C A D B C A D AE AE`

Chapter 72–74 的完整序列完全相同；Chapter 75–76 也完全相同；Chapter 78 的前八題再次使用相同 `B C A D` 循環。這會讓讀者不讀內容也能預測答案。

Required fix:

- 對每題獨立 shuffle choices，並同步搬移 explanations 與 answer indexes。
- 不要求機械式完全平均；應優先消除重複序列。
- 每章 multi-answer pair 也要分散，不要持續集中在 `AE`、`BE`。
- Shuffle 後重新跑 unique-answer 與 validator，避免正解/解析錯位。

## Distractor and uniqueness observations

- 70 題目前沒有 exact duplicate prompt、choice 或 explanation。
- 與其他 question-bank parts 的 prompt similarity 掃描未發現達 0.70 的近似題。
- 除上述問題外，single/multi 標記和正解數量一致：single 有一個答案，multi 有兩個答案。
- 多數 multi 題有唯一可辯護答案組；修訂時應保留 hard constraints，不要只為打散答案位置而改變知識點。
- 一些干擾項仍過度絕對化，例如「所有、一定、無限、AdministratorAccess」。除 `ch076-q09` 的不存在設定必須修正外，後續可把這些 distractors 改成可部署但違反一個明確 constraint 的方案，使難度更接近官方 sample-question 風格。

## Verification required after revision

1. 只修改題庫與 sources，不修改本 review 原始 findings。
2. 執行 `python3 tools/check_aws_question_banks.py --part 7`，必須通過。
3. 重新核對上述 factual/task/deep-link 項目。
4. 重新計算每章答案序列與跨 part prompt similarity。
5. 由獨立 reviewer 在本檔追加 verification；只有所有 blocking items 清除後，最後一行才能改為 `VERIFIED`。

REVISE

## Verification

Verification date: 2026-10-01

本輪重新讀取全部 70 題，只核對題庫，未修改 `part_07.json`。判定仍以已發布的 SAA-C03、SAP-C02 exam guides、官方 sample questions 與現行服務文件為準。題庫沒有引用或宣稱尚未發布的 SAP-C03 guide/sample；未來 SAP-C03 內容沒有被當成既有事實。

### 已通過

- `python3 tools/check_aws_question_banks.py --part 7` 通過：70 題、7 章。
- 原列 6 個 explanation-depth failures 已全部補足：
  `ch074-q03`、`ch074-q08`、`ch074-q10`、`ch076-q09`、`ch078-q02`、`ch078-q05`。
- `ch074-q01` 已正確改為 EC2/on-premises in-place deployment，以 `minimum healthy hosts` 表達至少 32 台或 80%，不再把 `batch size` 寫成另一個 CodeDeploy EC2 設定。
- `ch075-q02` 已補齊三段 patch data path：Systems Manager control channel、AWS-managed S3 patch-operation buckets，以及 OS repositories/internal mirror。
- `ch075-q06` 已選定明確流程：各 OS custom patch baseline，加上週日 Maintenance Window 執行 `AWS-RunPatchBaseline`。
- `ch076-q08` 已寫明 EventBridge target DLQ 必須是 same-Region SQS standard queue、不能使用 FIFO，並需要 queue policy。
- `ch077-q02` 已加入 `backup-cross-account`。
- `ch077-q04` 已正確使用 compliance-mode Vault Lock 的 `ChangeableForDays` grace time，範圍 3–36,500 天，並區分 governance mode。
- `ch076-q03`、`ch076-q06` 已由 `SAA-1.3` 改為 `SAA-1.2`；`ch076-q04` 已移除不適用的 `SAA-1.3`。
- 已新增並實際套用 SAA-C03 Domain 1 與 SAP-C02 Domain 3 blueprint sources。
- 原列的 Well-Architected、Patch Manager、EventBridge 與 runbook/playbook/post-incident deep links 已換成可直接支持 assertion 的現行頁面。
- 答案位置已重新 shuffle。Chapter 72–78 不再重複舊有的 `B C A D` 模板；56 題 single 的 A/B/C/D 分布為 10/18/14/14，14 題 multi 使用 6 種答案組合。
- Shuffle 後逐題檢查正解、choices 與 explanations 對齊，沒有發現答案 index 搬移錯位。
- Part 07 內沒有 exact duplicate prompt/tested label。對所有可成功解析的其他 parts 做跨題比對，未發現 similarity ≥ 0.82 的 prompt；`part_06.json` 本身有既存 JSON trailing-comma 錯誤，因此無法納入本輪跨-part similarity 掃描，這不是 Part 07 的題庫缺陷。
- 89 個 official source URLs 全部回傳 HTTP 200。

### 尚未通過

#### 1. `ch075-q01` 仍在錯誤選項解析中保留 EC2 不適用的身分說法

正解 D 已正確改為 Default Host Management Configuration 或 EC2 instance profile，也正確說明 hybrid activation 用於 non-EC2 hybrid/multicloud machines；但選項 A 的解析仍寫：

> node 本身仍需 instance profile 或 hybrid identity

在本題明確限定 EC2 instances 的 context 下，這仍會把 hybrid identity 暗示成 EC2 的替代身分。

Required fix:

- 將 A 的解析改為「EC2 node 本身仍需 Default Host Management Configuration 或具 Systems Manager permissions 的 instance profile」。
- 若提到 hybrid activation，必須再次明示它只適用於 non-EC2 hybrid/multicloud machines。

#### 2. `ch075-q06` 的正解 assertion 缺少直接 provenance

題目現在明確宣稱：

- Maintenance Window 負責週日排程；
- Maintenance Window 執行 `AWS-RunPatchBaseline`。

但 `source_ids` 只有：

- `ssm-patch-baselines`
- `ssm-patch-policies`

這兩個來源不足以直接支持 Maintenance Window task 與 `AWS-RunPatchBaseline` execution assertion。題庫已有正確 source records，尚未掛到本題。

Required fix:

- 在 `ch075-q06.source_ids` 加入 `ssm-maintenance-windows`。
- 加入 `ssm-run-patch-baseline`。
- 保留 `ssm-patch-baselines`；`ssm-patch-policies` 只作為替代 workflow 的解析依據。

#### 3. `cloudwatch-alarms` 仍不是 canonical deep link

所有原 review 指定的退化首頁 links 已修正，但 `cloudwatch-alarms` 仍由：

`https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html`

redirect 到：

`https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html`

它仍能支持題目，並非 factual error；但在本題庫要求「精確 deep links」的條件下，應直接保存 canonical URL。Affected questions：

- `ch073-q09`
- `ch074-q10`
- `ch078-q05`

Required fix: 更新 `cloudwatch-alarms.url` 為 canonical URL，避免依賴 redirect。

上述三項修正後，重新執行 Part 07 validator、URL redirect check 與本 verification 的兩個定點 factual checks，才可標為 `VERIFIED`。

REVISE

## Final Verification

Verification date: 2026-10-01

本輪只讀取 `part_07.json`，重驗上一輪三個剩餘項目；未修改題庫。

- `ch075-q01`：已通過。選項 A 的解析現在明確指出 EC2 node 應使用 Default Host Management Configuration 或具 Systems Manager 最小權限的 EC2 instance profile，並清楚限定 hybrid activation 僅適用於 non-EC2 hybrid/multicloud machines。
- `ch075-q06`：已通過。`source_ids` 已加入 `ssm-maintenance-windows` 與 `ssm-run-patch-baseline`，可直接支持週日 Maintenance Window 與執行 `AWS-RunPatchBaseline` 的敘述。
- `cloudwatch-alarms`：已通過。來源已直接使用 canonical URL `https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html`，HTTP 200 且未 redirect。

上一輪三個 blocking items 均已清除。

VERIFIED
