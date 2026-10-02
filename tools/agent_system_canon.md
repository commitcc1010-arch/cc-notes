# 全書共用定義（canon）

撰寫任何章節時，以下定義必須和這裡一致。若你的章節需要新的全書共用定義，寫在完成回報裡，由主編加進本檔。

## Autonomy 等級（第 1 章 1.6 節定義，第 21、32、35、38 章沿用）

本書自訂的分級（借用 SAE J3016 的精神，不是業界標準）。**autonomy 是依「動作」決定的，不是依系統決定的。**

| 等級 | 名稱 | 誰決定下一步 | 誰核准副作用 | 例子 |
|---|---|---|---|---|
| L0 | 無 LLM 決策 | 規則或人 | 人 | 客服按 FAQ 範本回覆 |
| L1 | 建議 | 人 | 人 | 模型擬回覆草稿 |
| L2 | 流程內的 LLM 步驟 | 程式碼 | 程式碼（只開放事先寫好的動作） | 物流查詢固定 workflow |
| L3 | 監督式 agent | 模型 | 每個寫入動作都要人核准 | 客服 agent v1：退貨單要客服確認 |
| L4 | 有邊界的自主 | 模型 | 邊界內自動，超出邊界才找人 | 500 元以下退款自動 |
| L5 | 目標導向的長時間自主 | 模型（含拆解子目標） | 預算內自主；不可逆或超出預算的動作找人 | research agent 自行完成月度分析 |

兩個獨立的軸：「路徑由誰決定」（程式碼 vs 模型）與「副作用由誰核准」。不可回復的動作永遠不完全自動。

## 單次呼叫、workflow、agent（第 1 章）

- **單次呼叫**：一次 prompt → 一次回覆。
- **workflow**：程式碼決定步驟與順序，LLM 只是其中的步驟。
- **agent**：模型在 loop 中自己決定下一步（呼叫哪個 tool）與何時停止。

## 任務適合度三問（第 1 章）

開放（步驟無法事先列舉）、可驗證（結果能被客觀檢查）、可回復（錯誤能便宜地撤銷）。

## 青鳥科技時間線

客服 agent v1 以 L3 上線（查詢自主、寫入要客服確認），之後小額退款移到 L4。內部 coding agent 在 sandbox 內 L4；營運 research agent 為 L5（預算內自主）。共用部分抽成 framework `loom`。

## loom 的版本與模組命名

- 只有三個版本號：第 4 章 `loom` v0.1（最小 loop）、第 23–25 章重構後的 `loom` v0.5（framework 核心抽象＋runtime＋model adapter）、第 45 章 `loom` v1.0（完整組裝）。
- 其他章節不要給新版本號，寫成「給 loom 加上 X 模組」，模組名稱用小寫，例如 `loom.tools`、`loom.schema`、`loom.context`、`loom.compaction`、`loom.retrieval`、`loom.memory`、`loom.registry`、`loom.mcp`、`loom.a2a`、`loom.sandbox`、`loom.browser`、`loom.workflows`、`loom.graph`、`loom.agents`（multi-agent）、`loom.approval`、`loom.durable`、`loom.runtime`、`loom.models`、`loom.evals`、`loom.tracing`、`loom.guardrails`、`loom.auth`。

## Tool 載入與程式呼叫（第 13 章定義，第 17、29、45 章沿用）

- **前綴不變式**：deferred loading 載入新 tool 時只「追加」到 tool 清單尾端，不重排、不刪除；前一輪的 tool 清單永遠是下一輪的開頭，以免打斷 prompt cache。
- **`code_callable`**：registry 中每個 tool 有 `code_callable` 欄位；有副作用（write／destructive）的 tool 一律 `code_callable=False`，不開放從 code-as-action 的程式中呼叫，必須走一般 tool call 與核准流程。

## Tool 副作用分級與 idempotency（第 5 章定義，全書沿用）

- **read**：唯讀；**write**：可回復的寫入；**destructive**：不可逆或對外的動作（退款、寄信、刪除）。未標註的 tool 一律當 destructive。
- 與 autonomy 的對應：read 通常 auto；write／destructive 依第 1、21 章的 approval policy。
- **idempotency key** 由 harness 依業務意圖（`intent_fields`）推導，不放進模型看得到的 schema；去重在真正執行副作用的那一端（例如金流閘道）。核准綁在意圖上，重試不會產生第二張核准卡片。「結果未知」（例如逾時）是獨立的錯誤類別，不可直接重試 destructive 動作。

## Memory 範圍與優先順序（第 12 章定義）

- 三種範圍：使用者、組織（租戶）、專案。agent 對組織記憶預設唯讀。
- 讀取衝突時的優先順序：產品規則 > 組織規則 > 使用者偏好 > 模型推論。
- 來源權威：使用者明說 > 客服註記 > 模型推論。

## 標準與清單的正式稱呼

- **OWASP Top 10 for LLM Applications 2025**（LLM01–LLM10；agent 最相關的是 LLM06 Excessive Agency）。
- **OWASP Top 10 for Agentic Applications 2026**（ASI01–ASI10，2025-12 發布）。引用時寫「OWASP Agentic Top 10（2026 版，2025 年 12 月發布）」。
- **MCP** 版本以日期稱呼，本書以 2026-07-28 版為「目前版本」。

## 核准（第 21 章定義，第 22、32、33、36、42 章沿用）

- 核准單狀態：PENDING → APPROVED／REJECTED／EXPIRED／CANCELLED；APPROVED 執行後 → EXECUTED／FAILED。
- 政策規則以 **deny-overrides** 合併；未登記的動作預設拒絕。
- 核准引擎使用第 1 章決策表的**風險類別**（讀取／寫入／金錢／破壞性），比第 5 章的副作用等級多分出「金錢」：退款在副作用上屬於 destructive，但在核准政策上屬於「金錢」類，可依金額門檻在 L4 自動（例如 500 元以下）並抽查。**硬底線**只套用在「破壞性」風險類別（不可逆、無法以金錢補償，例如刪除帳號）：結果至少是 approve，寫在引擎程式碼中，不是可改的規則。
- 逾時預設選「做錯時代價較低」的一邊；不可逆的 destructive 動作不得因逾時自動執行。
- 核准綁定參數 hash；執行時參數不符即拒絕。
- 稽核日誌為 append-only 並以 hash chain 防竄改（第 21、33 章）。

## Sandbox 原則（第 17 章定義，第 32、36、43 章沿用）

- sandbox 用完即銷毀，不跨任務、不跨租戶重用（warm pool 中的是「尚未使用」的乾淨實例）。
- secrets 不進 sandbox：需要憑證的呼叫經由 sandbox 外的 credential proxy 代為加上。
- egress 預設拒絕，只開放 allowlist。
- 第 17 章的 `run_untrusted()` 是概念版，不是安全邊界；production 依風險選 container＋seccomp、gVisor 或 microVM。

## Session log 與 compaction（第 10 章定義，第 12、20、22、45 章沿用）

- **不變式**：context 是 session log 的純函式；log 只能追加，清除與摘要也記成事件，可重建、倒帶、取回原文。
- 交接筆記（compaction 摘要）的六個固定段落：目標、使用者約束、已完成、進行中、下一步、未解問題。使用者約束逐字保留，副作用由程式記帳（進度檔），不靠摘要。

## Tracing 慣例（第 29 章定義，第 33、34、45 章沿用）

- span 名稱依 OTel GenAI 慣例：`invoke_agent`、`chat`、`execute_tool`；屬性名稱以官方為準。
- span status 只記技術成敗；業務結果（例如是否真的退款成功、回覆中的宣稱）另外記在 `bluebird.*` 命名空間的屬性（例如 `bluebird.run.status`、`bluebird.claims`）。
- 內容擷取預設關閉；PII 在匯出前遮蔽，使用者 id 以 HMAC 假名化；成本在寫入時依有版本的價目表計算。

## 授權（第 33 章定義）

- 有效權限 = 使用者權限 ∩ agent 權限 ∩ 任務範圍。
- step-up 核准 token：綁定單筆交易（參數 hash）、短效、只能用一次。
- 租戶只來自 session（伺服器端身分），tool 參數中不得有租戶欄位，模型不能填寫租戶。
- 禁止 token passthrough：下游只接受 audience 為自己的 token。

## Lethal trifecta 檢查（第 31 章定義，第 32 章沿用）

- egress 四級：none（無對外通訊）／bound（只能回給本人或固定對象）／allowlist（只能到列表中的目的地，注意 allowlist 等同授權）／open。
- 審查單位是 **context**：同一個 context 只要讀過不可信內容，就視為受污染；sub-agent 的 text 回傳會把污染帶回主 context，typed（結構化、受驗證）回傳可以阻斷。

## loom.guardrails（第 32 章定義，第 45 章沿用）

- `Label`：值的來源（source）與可讀者（readers）。
- `ToolSpec` 欄位：`capability`、`integrity_args`（需要完整性保護、不能被不可信資料決定的參數）、`recipient_arg`（收件人參數，用於機密性檢查）、`inherits`（輸出標記如何繼承輸入）。
- 政策結果三種：deny／ask／allow（ask 走第 21 章的核准流程）。檢查順序：能力 → 機密性 → 完整性。

## 正規化的模型回應（第 25 章定義，第 24、29、36、45 章沿用）

- `stop_reason` 四種：end_turn／tool_use／max_tokens／refusal（第 4 章只用前三種）。未知值由 adapter 直接報錯，不默默當成 end_turn。
- usage 四個互不重疊的欄位：`input_tokens`（未命中快取）、`cache_read_tokens`、`cache_write_tokens`、`output_tokens`；`reasoning_tokens` 只做參考，不重複計費。`ModelResponse.raw` 保留原始回應。
- 分工：重試與退避屬於 `loom.runtime`（第 24 章）；錯誤分類、熔斷、fallback、routing、計費屬於 `loom.models`（第 25 章）。

## loom v0.5 核心（第 23 章定義，第 24、25、45 章沿用）

- 核心模組 `loom.core`；八個核心抽象：Agent、Tool、Handoff、Guardrail（不可變宣告）＋ Runner、Session、Event（執行與狀態），外加 Hook／middleware。
- middleware 四個擴充點：`before_run`、`wrap_model`、`wrap_tool`、`on_event`。全域政策掛在 Runner 層 middleware，agent 專屬政策宣告在 Agent 上。
- **持久化的核心事件**（寫進 session，是唯一事實來源）七種：`run_started`、`user_message`、`model_response`、`tool_result`、`handoff`、`guardrail_tripped`、`run_finished`。
- **串流事件**（第 24 章 `loom.runtime` 給 UI／呼叫端即時消費，不持久化）：例如 `model_delta`、`tool_started`、`tool_finished` 等；持久化事件是串流事件完成後的彙總。兩層不要混用。
- 相容層 `loom.compat`，在 v1.0 移除。

## 估算記號（第 3、35 章定義，第 36、38、42–44 章沿用）

- k：每 session 的模型呼叫次數；P：固定前綴 token；d：每步新增 token。每 session 輸入 ≈ k×P ＋ d×k(k−1)/2。
- h：cache 命中率；λ：尖峰到達率；並行數依 Little's law（L = λ×W），p99 用 Poisson 分位數。
- 青鳥基準：試營運每天 2 萬 session；平台化後每天 10 萬 session、約 4,000 家店；L4 自動退款門檻 500 元；核准一張平均 45 秒。
- **動作清冊**（action inventory）：列出 agent 所有動作及其副作用等級、autonomy、`code_callable`、`intent_fields` 的表，是設計審查的必要產出。

## 驗證閘門（第 39 章定義，第 43、45 章沿用）

- **verification gate**：agent 宣告完成前必須有外部證據（測試通過、狀態檢查）；沒有證據的完成記為 run status `unverified`，不等於 `done`。

## 多租戶不變式（第 42 章定義，第 36、45 章沿用）

- tenant 只從 Edge Gateway 驗證過的 session 注入，不從模型輸出或對話內容讀取；tool schema 不放 tenant 欄位（同第 33 章）。
- 所有快取（prompt、語意快取、retrieval）的 key 都必須包含 tenant 與設定版本。
- 租戶設定只能收緊、不能放寬平台底線；設定編譯成以內容 hash 為版本號的 AgentSpec，每段對話 pin 住版本。
- 每個 span 帶 `bluebird.tenant.id` 與 `bluebird.spec.version`。

## 證據帳本（第 44 章定義，第 40、45 章沿用）

- 報告中每個數字都必須能追溯到證據：查詢結果以 Q 編號（Q1、Q2…）、由查詢計算出的衍生值以 D 編號（D1…）；沒有證據編號的數字由核對器擋下。
- 報告的證據權限下限：分享報告前檢查讀者權限是否涵蓋報告引用的所有證據。

## 新技術評估（第 46 章定義，第 30 章相容）

- 證據階梯：⓪ 宣傳或 demo、① 廠商自報、② 可重現實驗、③ 多方採用、④ 自家 eval 驗證。
- 技術雷達四環：adopt／trial／assess／hold（沿用 Thoughtworks 的名稱）。
- harness 元件生命週期：承重 → 待驗證 → 候選移除 → 已移除；安全與政策元件不參與自動移除（與第 30 章的保護清單一致）。

## loom.runtime（第 24 章定義，第 45 章沿用）

- Runner 介面：`Runner(model, middleware, ...)`、`start()`／`run(agent, input, session, deps)` 回傳 `RunResult`；middleware 可丟 `StopRun`。
- `tool_result` 事件有 `status`：ok／error／timeout／cancelled／unknown；`model_response` 事件有 `attempts`。
- `RunResult.status`：見下方「RunResult 狀態名稱（全書統一）」；loop guard 觸發寫成 `guardrail_tripped`（`guardrail="loop_guard"`）。
- 串流事件型別：`model_delta`、`model_retry`、`tool_started`、`tool_finished`、`run_cancelling`、`committed`（核心事件寫入後推送）。
- 模型串流介面 `stream()`：先送 `text_delta`，最後送帶完整 `ModelResponse` 的 `stop`。
- 重試只依 `ModelError.retryable` 決定；refusal 不重試。

## RunResult 狀態名稱（全書統一）

- 全書統一使用：done（有外部證據的完成）／unverified（宣告完成但無外部證據，第 39 章）／max_steps／max_tokens／budget／loop／blocked（guardrail 或政策擋下）／cancelled／timeout／error／refusal。
- 不使用 succeeded、budget_exceeded 等別名。
- interrupt／resume 介面（第 21 章）另有兩個非結束狀態：interrupted（暫停等待核准）、ignored（重複的 resume 回呼被忽略）。

## loom v1.0（第 45 章，隨書套件 `Agent System Design/code/`）

- 擴充事件（核心七種之外）：`approval_requested`、`tools_loaded`、`context_cleared`、`context_compacted`；`to_messages` 略過不認識的事件。
- `Agent.version` 是 agent 設定的內容 hash，即 AgentSpec 的版本號。
- 套件未收錄 `loom.sandbox`、`browser`、`a2a`、`workflows`、`graph`、`agents`、`retrieval`；第 45 章 45.12 說明它們的掛接點。
