# AWS 題庫獨立審查：Part 09（第 91–96 章）

- 審查日期：2026-10-01
- 題庫：`tools/aws_question_banks/part_09.json`
- 範圍：60 題；Amazon Bedrock、Knowledge Bases、Guardrails、AgentCore Identity、人工核准與 AI observability
- 題庫作者：`P09-A`
- 審查者：獨立審查；未修改題庫
- 依據：AWS 官方 SAP-C02 exam guide、官方 sample question 格式、AWS 服務文件。Jayendra Patil 文章只作主題靈感核對，不作服務事實來源。

## 結論

本 part 的大部分服務概念與正解方向正確，且未發現 dumps、回憶真題、ExamTopics 類來源或把社群文章當成服務事實依據。JSON 結構檢查亦通過：

```text
✅ AWS question banks passed: 60 questions across 6 chapters
```

但目前仍有會影響出版品質的問題，不能標記為 VERIFIED：

1. 全部 60 題的 `level` 使用未獲官方考綱支持的「SAP-C03 transition」標籤。
2. 多組題目在本 part 內，或與 Part 05、Part 10 高度重複。
3. 14 題複選題中有 12 題包含 D，且 11 題答案為 AD 或 BD，存在明顯作答線索。
4. `ch094-q02` 以外的 AgentCore 核心方向多數正確，但若干題缺少真正支撐該機制的精確官方 deep link。
5. Application inference profile 題目沒有完整反映 2026 年的 API 支援邊界與 Amazon Bedrock Projects 建議。
6. 少數題目的 scenario、正解或解析混合了不在該操作路徑中的元件，或 task mapping 不符合題幹真正測量的能力。

## 官方考綱定位

截至 2026-10-01，官方考試名稱與考綱仍是 **AWS Certified Solutions Architect - Professional (SAP-C02)**。官方 guide 已把下列內容列入「Emerging Topics」，並明說它們可能以**不計分的 pretest questions** 出現：

- Amazon Bedrock Guardrails
- Amazon Bedrock AgentCore Identity
- AI agent human oversight controls
- 在 AWS 上的 generative AI 應用

官方並未在目前 guide 中公告 `SAP-C03`。因此：

- `SAP-C03 transition/enrichment` 應改為 `SAP-C02 emerging topic (unscored pretest)`。
- `SAP-C02 / SAP-C03 transition` 應依題目性質改為：
  - `SAP-C02 scored-domain transfer + emerging topic`，或
  - `SAP-C02 emerging topic (unscored pretest)`。
- 題目可以保留現有 `SAP-*` task mapping 作能力映射，但文字必須說明這是把 emerging topic 映射到既有 scored-domain skill，不可暗示 AWS 已公告 SAP-C03。
- 本 part 沒有 `SAA-*` mapping，不應宣稱這 60 題同時是官方 SAA-C03 coverage。

官方基準：

- SAP-C02 exam guide：<https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html>
- Domain 2：<https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html>
- Domain 3：<https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html>
- SAP official sample questions：<https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf>
- SAA official sample questions：<https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf>

## 跨題重複與唯一性

以下不是字面完全相同，但 scenario、錯誤選項與正解機制高度重疊。至少應重寫每組中的一題，使其測不同能力。

| 重複群組 | 問題 |
|---|---|
| `ch091-q07`, `ch093-q01`, `ch093-q08`, Part 10 的 Q104.05 | 都在測「Guardrails 不是 IAM/tool authorization，工具仍須 deterministic validation」。 |
| `ch091-q06`, `ch094-q09` | 都是退款 action Lambda、agent/Lambda permission、customer ownership、金額上限與 idempotency。 |
| `ch091-q08`, `ch092-q04` | 都在測 PrivateLink 只改變網路路徑，不能取代 IAM/tenant authorization。 |
| `ch091-q05`, `ch096-q06` | 都把 retrieve-only evaluation 與 generation 分離。 |
| `ch091-q10`, `ch096-q10` | 都是 400/429/503/529 分類、bounded backoff/jitter 與停止 retry amplification。 |
| `ch092-q03`, `ch096-q02` | 都是 invocation logging opt-in、敏感 payload、IAM/KMS/retention。 |
| `ch094-q03`, Part 10 的 Q104.02 | 都是 AgentCore inbound JWT 必須驗 issuer/audience/client/claims，再做 tenant/tool authorization。 |
| `ch095-q04`, Part 05 的 Q55.06, Part 10 的 Q104.07 | 都是 raw task token 不可放公開 URL、需驗 approver、綁定 request、設 timeout/replay 防護。 |

建議的改寫方向：

- 把其中一題改成具體 IAM/resource policy debug，而非再問責任邊界。
- 把其中一題改成 Guardrail trace/metrics 判讀，或 contextual grounding qualifier 的配置錯誤。
- 把其中一題改成 callback race、expired token、redrive、version/alias 與 in-flight execution 的實際故障。
- 把其中一題改成 Projects、Responses API、Chat Completions API 與 application inference profile 的 2026 支援矩陣。

## 答案位置與官方 sample 風格

### 答案分布

- 46 題單選：A=11、B=12、C=16、D=7。尚未達嚴重偏斜，但 C 偏多、D 偏少。
- 14 題複選：
  - AB=1
  - AC=1
  - AD=5
  - BD=6
  - CD=1
- D 出現在 12/14 題複選答案；AD 或 BD 合計 11/14。

這會讓讀者在不知道內容時也能猜出「複選通常含 D」。應在不改變事實正確性的前提下重排選項，使複選組合更平均。

### Distractor 品質

官方 sample 通常讓錯誤選項在某些條件下看似合理，再由 cost、operations、security、availability 或 requirement 細節排除。本 part 有不少過度荒謬的 distractor，例如：

- 把 AdministratorAccess access key 放進 prompt。
- 把 raw prompt 寫入公開 S3。
- Base64 後模型就不能解碼。
- 所有數字都當 profanity。
- 把 workload token 當永久 root credential。

這些可作初學者教學題，但不應佔 SAP 模擬題太高比例。建議把至少一半改成「技術上可行但不符合題目 hard constraint」的相鄰方案，並在解析中明確指出為何不是最佳答案。

## Deep-link 與來源審查

### 通過項目

- 全部官方與社群 URL 均可存取。
- 每題至少有一個 AWS 官方來源。
- 未使用 dumps 或社群題庫作服務事實來源。
- Jayendra Patil 來源只出現在 `inspiration_ids`。

### 應改成 canonical URL

| Source ID | 現在 URL | Canonical URL |
|---|---|---|
| `bedrock-kb-eval-metrics` | `knowledge-base-eval-retrieve.html` | <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-metrics.html> |
| `bedrock-model-evaluation` | `model-evaluation-type-judge.html` | <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-judge-create.html> |
| `stepfunctions-cross-account` | `concepts-cross-acct-sync-pattern.html` | <https://docs.aws.amazon.com/step-functions/latest/dg/concepts-access-cross-acct-resources.html#concepts-cross-acct-sync-pattern> |

### 缺少或不夠精確的官方來源

- `ch093-q06`：應直接加入 contextual grounding checks 文件；目前 generic component/apply 頁不足以精確支撐 qualifier、threshold 範圍及限制。
  <https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html>
- `ch094-q06`：應加入 AgentCore on-behalf-of token exchange 的精確頁面。
  <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html>
- `ch094-q08`：應加入 S3 policy key/object-tag authorization 文件，並說清楚 `department` 是 principal/session tag 還是 existing object tag。
- `ch094-q10`：`bedrock-cloudtrail` 是 Amazon Bedrock 的 CloudTrail 頁，不足以支撐 AgentCore Runtime/Identity 的整條診斷鏈；應加入 AgentCore observability、runtime troubleshooting 或 AgentCore CloudTrail 的官方頁。
- `ch095-q07`：引用只有 Step Functions，卻陳述 SNS email delivery 的語意；應加入 SNS delivery-status logging 文件。
- `ch095-q08`：callback 與 IAM 文件不支撐 idempotency/duplicate side-effect 的完整敘述；應加入 AWS Builders' Library 的 idempotent API/retry 官方文章，或等價的官方服務文件。
- `ch095-q01`：只有 generic exam guide。Guide 支持 human oversight 是 emerging topic，但沒有完整支撐題目中的 risk/reversibility/amount policy；應補官方 responsible-AI、Generative AI Lens 或 agentic security guidance。
- `ch096-q01`：現有來源分別支撐 trace、runtime metrics 與 KB evaluation，但未直接支撐 `cost-per-successful-task SLO`；若保留此特定指標，應加官方 FinOps/Generative AI cost guidance，或把解析明確標成架構推導。

## 逐題審查

### 第 91 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch091-q01` | PASS | Bedrock 與 SageMaker AI 的責任邊界、正解與各解析正確；`SAP-4.4` 可接受。需套用全域 level 修正。 |
| `ch091-q02` | PASS | 2026 model-access 流程、Region/IAM/Marketplace/供應商前提與 PrivateLink 邊界正確。需套用全域 level 修正。 |
| `ch091-q03` | PASS | Converse/ConverseStream 提供較一致 messages 介面，但不抹平模型能力差異；正解與解析正確。 |
| `ch091-q04` | REVISE | `Retrieve` 與 `RetrieveAndGenerate`、citations 敘述正確；但 `SAP-2.5` 是 performance objective，題幹沒有 performance requirement。較合理是 `SAP-4.4`，或重寫成有 latency/throughput 目標。`bedrock-kb-permissions` 對 citation flow 也不是精確來源。 |
| `ch091-q05` | REVISE | 技術方向正確，但與 `ch096-q06` 高度重複。保留一題測 ingestion/filter/reranking，另一題應改測 evaluation metric 判讀或 release gate。 |
| `ch091-q06` | REVISE | 正解方向正確，但與 `ch094-q09` 幾乎是同一退款授權鏈。需改寫其中一題。 |
| `ch091-q07` | REVISE | Guardrails 不取代 IAM/tool authorization 正確；但與 `ch093-q01`、`ch093-q08`、Part 10 的 Q104.05 重複。 |
| `ch091-q08` | REVISE | Interface endpoint、private DNS、SG/endpoint policy 與 IAM 分離正確；但與 `ch092-q04` 重複。 |
| `ch091-q09` | REVISE | Cross-Region inference 與 cost attribution 方向正確，但 2026 文件要求說清楚 application inference profile 是以 base model 或 system-defined cross-Region profile 為 source，再呼叫 application profile ARN。另 application profiles 不支援 Responses API/Chat Completions API，Projects 是新工作負載較彈性的建議；題幹未限定 API，因而有歧義。 |
| `ch091-q10` | REVISE | 400、429、503/529 的分類與 bounded backoff 正確；但與 `ch096-q10` 重複。 |

### 第 92 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch092-q01` | PASS | 資料 inventory、classification、owner、retention 與最小化方向正確；解析沒有把 embedding 誤稱為安全 hash。 |
| `ch092-q02` | PASS | 模型供應商邊界不等於客戶應用、logs、tools 或 evaluation 無需治理；正解正確。解析沒有否認 AWS 對少數特定模型可能有受限 retention。 |
| `ch092-q03` | REVISE | Invocation logging 是 opt-in、CloudTrail 不等於完整 payload、目的地需 IAM/KMS/retention 均正確；但與 `ch096-q02` 高度重複。 |
| `ch092-q04` | REVISE | Endpoint policy、SG、IAM 與 document-level authorization 分層正確；但與 `ch091-q08` 重複。 |
| `ch092-q05` | REVISE | 最小 KMS 權限原則正確，但題幹說「建立同步工作時 AccessDenied」，此執行路徑不會因尚未使用的 evaluation-output key 而失敗。應限定為整條 pipeline 的分階段診斷，或只保留 sync 實際觸及的 S3、embedding/vector store、secret/KMS 資源。 |
| `ch092-q06` | PASS | Tenant scope 必須由可信 server-side identity 推導，不能信任 prompt/前端 filter；正解與解析正確。 |
| `ch092-q07` | PASS | Knowledge Bases service role 的 resource/action/trust 最小化正確。 |
| `ch092-q08` | PASS | 從 S3 刪檔不等於索引立即消失；direct ingestion delete 或成功 sync 後驗證有效 corpus 的方向正確。 |
| `ch092-q09` | PASS | PII entity/custom regex 的 BLOCK/ANONYMIZE 與資料治理互補關係正確。 |
| `ch092-q10` | PASS | Evaluation dataset/report 可能包含敏感資料，需 IAM/KMS/retention；正解與解析正確。 |

### 第 93 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch093-q01` | REVISE | 內容防護與工具授權分離正確，但與三題高度重複。 |
| `ch093-q02` | REVISE | 「用資料校準並按官方支援方向/tier 設定」方向正確，但沒有真正回答本題承諾測的精確知識：prompt attack filter、prompt leakage、input/output 與 Standard tier 的現行限制。應把精確限制寫進正解與解析，不能只叫讀者再查文件。 |
| `ch093-q03` | PASS | Denied topic 的語意定義、examples、邊界測試，以及它不等於 IAM 的解析正確。 |
| `ch093-q04` | PASS | Managed sensitive-information entity、custom regex、BLOCK/ANONYMIZE 的選擇正確。 |
| `ch093-q05` | PASS | 精確秘密代號使用 word/phrase filter、仇恨內容使用 semantic content filter，正解合理。 |
| `ch093-q06` | REVISE | Source/query/response 與代表性校準方向正確，但缺精確 contextual-grounding deep link；而 choice C 的 threshold `1.0` 在官方有效範圍 `0–0.99` 之外，解析只說「極端閾值」而沒有指出其無效。 |
| `ch093-q07` | PASS | ApplyGuardrail 不執行模型推論或 ticket side effect；應用需處理 INPUT/OUTPUT、intervention 與 fail policy，正確。 |
| `ch093-q08` | REVISE | 正解正確，但再度重複「Guardrail 不等於 tool authorization」。 |
| `ch093-q09` | PASS | DRAFT 測試、immutable version、明確切換與 rollback 的敘述正確。 |
| `ch093-q10` | PASS | Intervention 數量不能單獨代表安全改善；需 false accept/reject、latency 與 business signal，方向正確。 |

### 第 94 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch094-q01` | PASS | Bedrock Agent service role/Lambda resource permission 與 AgentCore Identity outbound credential 是不同責任，正確。 |
| `ch094-q02` | PASS | 官方文件確認每個 AgentCore runtime version 只能有一種 inbound auth；不同版本可分別使用 IAM/SigV4 或 JWT。正解正確。 |
| `ch094-q03` | REVISE | JWT issuer/audience/client/claims 與後續 tenant authorization 正確，但與 Part 10 的 Q104.02 高度重複。 |
| `ch094-q04` | PASS | Workload token 不是 IAM access key，也不是任意 S3 credential；正解與解析正確。 |
| `ch094-q05` | PASS | User-delegated 與 M2M/client-credentials 的責任配對及最小 scopes 正確。 |
| `ch094-q06` | REVISE | Audience/scopes 限縮的 OBO/token-exchange 正解正確，但現有 source 沒直接指向該機制；應加入官方 on-behalf-of token exchange deep link。 |
| `ch094-q07` | PASS | Credential provider/token vault、短期 audience-scoped credential 與 log redaction 正確。 |
| `ch094-q08` | REVISE | Role 上限、session policy 縮權、session tags/ABAC、source identity 的方向正確；但「相同 department tag 的 S3 objects」需明確定義 principal/session tag 與 `s3:ExistingObjectTag` 的比較方式，並補 S3 condition-key 官方來源，否則 answer B 省略實際 resource-policy 條件。 |
| `ch094-q09` | REVISE | 正解正確，但與 `ch091-q06` 使用相同退款欄位、ownership、amount limit、agent/Lambda permission 與 idempotency。 |
| `ch094-q10` | REVISE | 逐 stage 找第一個 deny 的方法正確；但 `bedrock-cloudtrail` 不足以支撐 AgentCore Runtime/Identity 診斷。需加入 AgentCore 官方 observability/troubleshooting/CloudTrail source，並說明 downstream SaaS 403 不一定出現在 AWS CloudTrail。 |

### 第 95 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch095-q01` | REVISE | Risk/reversibility/amount 決定 human oversight 的方向合理，且符合 SAP-C02 emerging topic；但只有 generic exam guide，缺少精確官方架構來源。 |
| `ch095-q02` | REVISE | Standard 支援 callback、Express 不支援 `.waitForTaskToken`，正解正確；但 task 應以 `SAP-2.4` reliability 為主，不是只有 `SAP-2.1` deployment strategy。 |
| `ch095-q03` | PASS | Task token 必須由同 AWS account principal 返回、綁定特定等待 task，正確。 |
| `ch095-q04` | REVISE | Server-side token、approver auth、request/evidence/expiration binding 正確；但與 Part 05 的 Q55.06、Part 10 的 Q104.07 高度重複。 |
| `ch095-q05` | PASS | Task timeout、可用時的 heartbeat，以及 timeout/reject/callback error 分流正確。 |
| `ch095-q06` | PASS | 核准頁需足夠且最小化的 action evidence，不能只顯示 confidence 或暴露 credentials；正解合理。 |
| `ch095-q07` | REVISE | SNS delivery 不等於人員核准、workflow 才持有 durable state，結論正確；但缺 SNS delivery-status 官方來源，且與本章其他 approval-state 題目知識增量偏低。 |
| `ch095-q08` | REVISE | Commit 前 revalidation 與穩定 idempotency key 正確；但現有 Step Functions callback/IAM 來源沒有精確支撐 duplicate-side-effect/idempotent API 機制。 |
| `ch095-q09` | PASS | Callback token 的 account restriction與跨帳號 resource action 應分開；中央 broker + scoped target role 是可行設計。 |
| `ch095-q10` | PASS | State machine versions/aliases、受控流量切換、舊 in-flight callbacks 與最小 audit evidence 的方向正確。 |

### 第 96 章

| ID | 狀態 | 審查結果 |
|---|---|---|
| `ch096-q01` | REVISE | Correlation ID 與多維 SLO 正確；但 `cost-per-successful-task` 是合理架構推導，現有來源未直接支撐。應補 cost/FinOps 官方來源或清楚標註推導。 |
| `ch096-q02` | REVISE | 正解與解析正確，但與 `ch092-q03` 重複。 |
| `ch096-q03` | PASS | Runtime metrics 不能直接量 hallucination、tenant authorization 或 business success；正確。 |
| `ch096-q04` | PASS | TTFT 近似不變、output token 增加、OTPS 穩定時，總 latency 主要來自回答變長；正確。 |
| `ch096-q05` | PASS | Agent trace 可定位 orchestration/tool exchange，但 downstream authoritative record 才能證明 commit；正確。 |
| `ch096-q06` | REVISE | Retrieve-only 與 retrieve-and-generate evaluation 分層正確；與 `ch091-q05` 重複，且 source 應換成 canonical metrics URL。 |
| `ch096-q07` | REVISE | 固定資料集、版本化、多維 hard gates、LLM-as-judge calibration 正確；但這是一個 production deployment gate，應至少加入 `SAP-2.1`，並更新 model-evaluation canonical URL。 |
| `ch096-q08` | PASS | Bedrock telemetry/evaluation 與 SageMaker Model Monitor/Clarify drift 的服務責任配對正確。 |
| `ch096-q09` | REVISE | Application inference profile 的 cost attribution 方向正確，但 2026 官方文件已建議新工作負載優先考慮 Projects；application profiles 不支援 Responses API/Chat Completions API。題幹未指定 API，沒有 Projects 選項，故正解不再具唯一性。 |
| `ch096-q10` | REVISE | Admission control、bounded retry、queue 與 canary rollback 正確；但與 `ch091-q10` 重複。 |

## 必須完成的修訂清單

1. 修正全部 60 題的 level，移除未公告的 SAP-C03 字樣，改成官方 SAP-C02 emerging/pretest 定位。
2. 重寫上述八組重複群組，讓每題測不同機制；不可只換產業名詞。
3. 重排複選選項，消除 D 出現在 12/14 題及 AD/BD 佔 11/14 的偏差。
4. 修正 `ch091-q04`, `ch095-q02`, `ch096-q07` 的 task mapping。
5. 修正 `ch091-q09` 與 `ch096-q09` 的 application inference profile / Projects / API 支援邊界。
6. 修正 `ch092-q05`，不要把 evaluation-output KMS key 當成 sync 階段 AccessDenied 的直接原因。
7. 修正 `ch093-q02` 與 `ch093-q06` 的精確 Guardrails 行為及解析。
8. 為 `ch094-q06`, `ch094-q08`, `ch094-q10`, `ch095-q01`, `ch095-q07`, `ch095-q08`, `ch096-q01` 補精確官方來源。
9. 將三個會 redirect 的 source URL 更新為 canonical deep links。
10. 把過度荒謬的 distractors 改為可被 hard constraint 排除的相鄰方案，提高 SAP sample 風格與知識密度。

REVISE

## Verification

- 重新審查日期：2026-10-01
- 題庫版本：修訂後 `tools/aws_question_banks/part_09.json`
- 驗證方式：重新閱讀 60 題 prompt、choices、answers、全部 explanations、task keys 與 sources；對照當日 AWS 官方 SAP-C02 guide、Amazon Bedrock、Guardrails、AgentCore、Step Functions、SNS、IAM/S3 與 Generative AI Lens 文件。
- 題庫未修改。

### 已通過的修訂

1. **Level：通過。** 60/60 題已改成：
   - `SAP-C02 emerging topic (unscored pretest)`，或
   - `SAP-C02 scored-domain transfer + emerging topic`。

   題庫已完全移除 `SAP-C03` 字樣，沒有把未來考綱當成既有事實。這與當日官方 SAP-C02 guide 的 Emerging Topics 敘述一致：Guardrails、AgentCore Identity 與 AI human oversight 可能作不計分 pretest content。

2. **複選答案偏差：通過。** 14 題複選的答案組合已改為：
   - AB=3
   - AC=1
   - AE=1
   - BC=2
   - BE=2
   - CD=2
   - CE=2
   - DE=1

   D 只出現在 3/14 題，不再有原本 12/14 題皆含 D、AD/BD 佔 11/14 的猜題線索。

3. **原八組重複：大致通過。** 原本的題目已分化為不同可驗證機制：
   - Guardrail assessment 診斷、Guardrail IAM deny 與 tool authorization responsibility 已拆開。
   - `RETURN_CONTROL` 執行責任與 Lambda resource/business authorization 已拆開。
   - PrivateLink 連線診斷與 tenant authorization 邊界已拆開。
   - Retrieval config 調校與 evaluation-metric 判讀已拆開。
   - API error classification 與 cross-Region/admission-control 架構已拆開。
   - Invocation-logging 設計與 break-glass incident investigation 已拆開。
   - JWT key rotation 與 JWT tenant authorization 已拆開。
   - Callback redrive race 與 raw-token/replay protection 已拆開。

   自動 prompt/tested similarity 掃描已無 `0.68` 以上配對。`ch093-q01` 與 Part 10 的 Q104.05 仍共享「Guardrails 不取代 tool authorization」的核心原則，但 Part 10 已加入 Automated Reasoning 與 AgentCore Policy 的比較，現階段可視為不同深度；若要進一步降低概念重複，可將 `ch093-q01` 改成更具體的 payment authorization policy evaluation。

4. **先前指定 task mappings：通過。**
   - `ch091-q04` 已由 `SAP-2.5` 改為 `SAP-4.4`。
   - `ch095-q02` 已改為 `SAP-2.4`。
   - `ch096-q07` 已加入 `SAP-2.1`。

5. **Application inference profile：部分通過。**
   - `ch091-q09` 已明確限定 InvokeModel/Converse，並正確描述 application profile 可由 base model 或 system-defined cross-Region profile 建立，呼叫時須使用 application profile ARN。
   - 已加入 Projects 與 cost-management 官方來源。

6. **KMS：通過。** `ch092-q05` 已限定 sync 當下真正觸及的 S3/KMS/embedding/vector-store 路徑，並明確排除尚未執行的 evaluation-output key，不再混淆故障階段。

7. **Guardrails：部分通過。**
   - `ch093-q02` 已正確說明 `PROMPT_ATTACK` 的 input 方向、prompt leakage 是 Standard tier 能力，以及 Standard tier 的 cross-Region inference 邊界。
   - `ch093-q06` 已加入 contextual-grounding 精確頁面，並正確指出 threshold 有效範圍為 `0–0.99`、`1.0` 無效。

8. **缺漏來源與 canonical links：通過。**
   - OBO token exchange、AgentCore observability、S3 tag condition、SNS delivery status、idempotent API、Responsible AI、Generative AI Lens 與 GenAI cost sources 均已加入。
   - 原本三個 redirect URL 已換成 canonical URL。
   - 全部 source URL 重新檢查皆回傳 HTTP 200，沒有剩餘 redirect。
   - 社群來源仍只位於 `inspiration_ids`，沒有作 AWS 服務事實來源。

9. **結構與基本唯一性：通過。**

```text
✅ AWS question banks passed: 60 questions across 6 chapters
```

### 仍需修正

#### 1. `ch093-q06` 尚未處理 contextual grounding 的官方 use-case 限制

題幹明說團隊把「一般對話歷史」當成 source，但兩個正解只修正 source/query/response qualifiers 與 threshold。當日官方文件明確註明 contextual grounding 支援 summarization、paraphrasing、question answering，**不支援 conversational QA/chatbot use cases**。

因此目前題幹提出的其中一個錯誤沒有被正解修正。應：

- 將「一般對話歷史」改成受支援的 reference source；或
- 讓其中一個正解明確指出不可把 conversational history 當成受支援的 chatbot grounding use case。

官方來源：<https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html>

#### 2. `ch093-q09` 產生新的 task-mapping 問題

此題測的是 Guardrail DRAFT、immutable version、受控 promotion 與 rollback，主要是 deployment strategy。修訂前的 `SAP-2.1` 比目前單獨使用的 `SAP-2.4` 更精確。

建議恢復 `SAP-2.1`；若要同時保留 reliability 觀點，可使用 `SAP-2.1` 加 `SAP-2.4`，但不可只留 `SAP-2.4`。

#### 3. `ch095-q04` 的 redrive 前提仍有歧義

Step Functions 只允許 redrive **eligible unsuccessful Standard Workflow executions**。題幹只說 callback task 逾時並「進入補償分支」，未說明 execution 最後失敗、終止或逾時。若補償分支成功並讓 execution 成功完成，就不能 redrive。

正解中的 generation/correlation/no-op 設計方向正確；題幹應補成例如：

> 補償分支稍後失敗，使 execution 成為可 redrive 狀態。

另外，官方文件確認 timeout 後重新執行 callback Task 時會產生新的 random task token，此點與答案方向一致。

官方來源：

- <https://docs.aws.amazon.com/step-functions/latest/dg/redrive-executions.html>
- <https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html>

#### 4. `ch096-q09` 尚未讓 Projects 答案具唯一性

題幹只說新產品使用 Responses API 與 Chat Completions API，沒有指定 endpoint；正解卻直接指定 Projects。

當日官方邊界是：

- Projects 只適用於 `bedrock-mantle`。
- `bedrock-runtime` 是新應用的建議 endpoint。
- Chat Completions 可在兩個 endpoint 使用。
- Responses API 也可能在 `bedrock-runtime` 使用，視模型支援而定。
- Application inference profiles 不支援 Responses/Chat Completions；在這些 APIs 上需要 Projects、IAM principal attribution 或 per-request metadata，取決於 endpoint 與設計。

因此只憑 API 名稱不能唯一推導 Projects。應在題幹明確指定：

- 使用 `bedrock-mantle` 且需要 project-level resource/cost boundary；或
- 要求比較 `bedrock-mantle + Projects` 與 `bedrock-runtime + IAM/per-request metadata`。

官方來源：

- <https://docs.aws.amazon.com/bedrock/latest/userguide/projects.html>
- <https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html>
- <https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html>

#### 5. Weak distractors 尚未完成前次要求

雖然若干 distractor 已改善，但仍有多題使用一眼即可排除、未形成 SAP sample 所需 architecture trade-off 的選項，例如：

- `ch091-q01`：「公司內部資料就一律自行訓練」、「不必定義生命週期責任」。
- `ch091-q02`：「PrivateLink 自動接受供應商條款」。
- `ch092-q07`：直接使用 `AdministratorAccess`。
- `ch093-q08`：替尚未執行的 Lambda 加 `AdministratorAccess`。
- `ch094-q10`：暫時加入 `AdministratorAccess` 與所有 OAuth scopes。
- `ch095-q09`：所有帳號共用 `AdministratorAccess`。

這些選項可作入門教學，但仍未達前次要求的「技術上可能成立，卻因 hard constraint、責任邊界、成本、可用性或營運負擔而不是最佳解」。至少應把上述選項改成相鄰且具迷惑性的方案，並由解析說明具體翻轉條件。

### Verification verdict

其餘題目的服務行為、正解、解析、task mappings、來源與答案位置未發現新的阻擋問題。完成上述五項後可再作最終驗證；目前不能標記 VERIFIED。

REVISE

## Final Verification

- 最終驗證日期：2026-10-01
- 時間邊界：只採用截至 2026-10-01 已發布的 AWS 官方文件；未使用或推定任何之後日期的資料。
- 驗證範圍：上一輪留下的五個阻擋點，以及指定的六題 near-miss distractors。
- 題庫維持唯讀，未修改 `tools/aws_question_banks/part_09.json`。

### 1. Contextual grounding use case：通過

`ch093-q06` 已從不受支援的一般 chatbot 對話，改成以已核准臨床文件片段作 source、摘要要求作 query、候選摘要作 response 的醫療摘要情境。

這符合官方支援的 summarization／question-answering use cases，也正確保留以下限制：

- 必須提供 source、query 與 response。
- qualifiers 必須正確標示。
- grounding/relevance threshold 有效範圍為 `0–0.99`。
- `1.0` 是無效設定。
- 解析已明說一般 chatbot 對話不可假設受支援。

官方來源：<https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html>

### 2. `ch093-q09` task mapping：通過

此題目前映射：

```text
SAP-2.1
SAP-2.4
```

`SAP-2.1` 對應 DRAFT、immutable version、受控 promotion 與 rollback 的 deployment strategy；`SAP-2.4` 補充穩定發布與復原能力。已修正上一輪只保留 reliability mapping 的問題。

### 3. Eligible unsuccessful Standard Workflow redrive：通過

`ch095-q04` 已明確指定：

- 使用 Standard Workflow。
- 人工核准等待逾時。
- 補償分支也失敗。
- execution 以失敗狀態結束。
- execution 符合 redrive eligibility。

這符合官方規則：redrive 適用於在可 redrive 期間內未成功完成的 Standard Workflow executions，包括 failed、aborted 或 timed out executions。題目也正確要求新等待點使用新的 correlation、期限與核准證據，不重用舊 task token。

官方來源：

- <https://docs.aws.amazon.com/step-functions/latest/dg/redrive-executions.html>
- <https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html>

### 4. `bedrock-mantle` Projects 唯一性：通過

`ch096-q09` 已明確加入兩個 hard constraints：

- 新產品使用 `bedrock-mantle` endpoint。
- 必須以 project-level IAM resource boundary 與 cost allocation 隔離產品。

因此 Amazon Bedrock Projects 成為唯一符合要求的選擇。題目亦正確區分：

- `bedrock-mantle` + Responses/Chat Completions + Projects。
- `bedrock-runtime` + InvokeModel/Converse + tagged application inference profiles。

解析沒有把 Project ARN 與 inference profile ARN 當成可互換參數，也沒有把 cross-Region routing 誤當成成本中心。

官方來源：

- <https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html>
- <https://docs.aws.amazon.com/bedrock/latest/userguide/projects.html>
- <https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-projects.html>
- <https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html>

### 5. 六題 near-miss distractors：通過

指定的六題已不再依賴一眼可排除的荒謬選項；錯誤選項現在多為技術上可部署、但不符合題目 hard constraint 或責任邊界的相鄰方案，解析也提供答案翻轉條件。

| 題目 | 驗證結果 |
|---|---|
| `ch091-q01` | Bedrock customization、SageMaker 自管 serving 與 EKS 統一平台都是可行 near-miss；依控制深度與營運責任排除。 |
| `ch091-q02` | FullAccess、只做 Marketplace subscription、改 provisioned throughput 都可能處理部分問題，但不能取代 Region、IAM、subscription 與供應商前提的分層診斷。 |
| `ch092-q07` | 共用 ingestion role、角色分離但權限不足、窄角色但 trust 缺 source conditions 都是具體設計取捨。 |
| `ch093-q08` | Lambda 自行 ApplyGuardrail、DRAFT 診斷與 wildcard Guardrail resource 都有條件可成立，但不符合目前 trace 指出的最小修復。 |
| `ch094-q10` | Bounded canary、重取 OAuth consent/token、IAM Policy Simulator/CloudTrail 都是局部診斷手段；只有端到端 correlation 能保留證據並定位第一個 deny。 |
| `ch095-q09` | 分散 state machine、cross-account nested workflow、Secrets Manager 保存 token 都是可實作方案，但分別違反中央 durable approval ownership 或 callback account boundary。 |

### Final verdict

上一輪五個阻擋點已全部解除；指定題目的正解、解析、task mapping、官方 service boundary、唯一性與 distractor 品質均通過第三輪驗證。題庫結構檢查仍為 60 題、6 章且通過。

VERIFIED
