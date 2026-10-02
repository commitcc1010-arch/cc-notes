# 附錄 A　術語表

> [!abstract] 本附錄地圖
> **用途**：全書以粗體定義的主要術語，在這裡各有一句話的定義與章節位置；細分的子概念併入上層術語的定義中（例如 temperature、top_p 併入 sampling，FAIL_TO_PASS 併入 SWE-bench）。讀到某一章出現沒看過的詞、寫設計文件需要精確用詞、或在審查會議上要確認「我們說的是同一件事」時，先查這裡，再回到章節讀完整的因果與例子。定義與正文及全書共用定義（autonomy 等級、副作用分級、核准狀態、RunResult 狀態等）一致；若有出入，以章節正文為準。
>
> **怎麼查**：
> - 依主題分成九節（A.1–A.9），大致對應全書的 Part 順序；每節內依英文字母排序，書中沒有給英文名稱的本書自訂術語（英文欄為「—」）排在該節最後。
> - 「章節」欄的格式是「首次定義章 → 主要深入章」：前一個數字是術語第一次以粗體出現並定義的章，箭頭後是完整展開或大量使用的章；只有一個數字代表兩者相同。
> - 只在本書成立的名稱，例如人物、租戶、`loom` 的模組、事件與狀態名稱，集中在 A.10，因為它們不是業界通用術語，但各章靠它們互相引用。
> - 版本號、價格、benchmark 分數與產品細節不收在這裡；它們只出現在各章標明「截至 2026 年 10 月」的 2026 現況區塊與附錄 C。
>
> **規模**：A.1–A.9 共 337 個術語，A.10 共 62 個專有名詞。

## A.1 基礎與 LLM

agent 的定義、autonomy、任務適合度，以及 token、取樣、推理模型、快取與延遲等 LLM 基礎（第 1–3 章）。共 27 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| agent | agent | 模型在 loop 中根據環境回饋，自己決定下一步（呼叫哪個 tool）與何時停止的系統。 | 1 |
| autonomy | 自主程度 | 系統在沒有人點頭的情況下能做多少事；本書分成 L0–L5，而且依「動作」決定，不是依系統決定。 | 1 |
| constrained decoding | 受限解碼 | 在 sampling 的每一步把會違反 schema 的 token 機率設為零，保證輸出的「形狀」正確，但不保證內容正確。 | 3 → 7 |
| context window | context window | 模型單次呼叫能處理的 token 總量上限，輸入與輸出共用；它就是 agent 在這一步能「知道」的全部。 | 3 |
| effort | 推理強度 | 以等級（例如 low、medium、high）控制模型投入多少思考與 tool call 的參數，常搭配 adaptive thinking（模型自己決定想不想、想多少）；影響的不只是 thinking 長度，而是所有輸出。 | 3 → 8 |
| function calling | 函式呼叫 | 也叫 tool use：模型輸出「呼叫哪個 tool、參數是什麼」的結構化請求，由 harness 真正執行。 | 3 |
| hallucination | 幻覺 | 看起來像真的、但沒有事實依據的輸出；客服情境最危險的形式是承諾了一個沒有執行的動作。 | 1 → 34 |
| harness | 駕馭層 | 包住模型、負責跑 loop 的程式：prompt 組裝、tool 定義與分派、停止條件、context 管理、錯誤處理；在 Model／Harness／Environment 三層心智模型中位於中間，也常叫 agent runtime 或 runner。 | 1 → 4 |
| interleaved thinking | 交錯式思考 | 模型在每次 tool 結果回來後再思考一次才決定下一步；harness 回填歷史時必須原樣保留 thinking 區塊。 | 3 |
| KV cache | 鍵值快取 | 模型為每個輸入 token 算出的注意力中間結果；前綴相同時可以直接重用，是 prompt caching 的基礎。 | 3 |
| max_tokens | 輸出上限 | 單次回應的輸出 token 上限；撞到上限時回應被截斷，stop_reason 為 `max_tokens`，tool call 參數可能只寫了一半。 | 3 → 4 |
| Messages／Items／Steps 形態 | 歷史表示形態 | 各家 API 表示對話歷史的三種形態：Messages 以 role 為單位、一則訊息含多個內容區塊；Items 攤平成型別各異的 item；Steps 拆成 thought、function_call 等 step。 | 3 |
| prompt caching | prompt 快取 | 模型服務把相同前綴的計算結果（KV cache）快取起來重用；計價分為 cache write（首次寫入，常略貴）、cache read（命中，遠比一般輸入便宜）與一般輸入，前綴越穩定命中率越高。 | 2 → 3、9 |
| reasoning model | 推理模型 | 被訓練成先產生一段內部推理（thinking，也稱 reasoning tokens）、再給出答案或動作的模型；thinking 對使用者通常不可見，但照輸出 token 計費並佔用時間。 | 3 → 8 |
| sampling | 取樣 | 從模型輸出的下一個 token 機率分佈中選出實際 token 的規則：greedy decoding 永遠選最高者；temperature 調整分佈尖銳程度；top_p（nucleus sampling）只保留累積機率達 p 的候選；top_k 只保留前 k 個。 | 3 |
| streaming | 串流 | 把中間進度與回覆逐步送給使用者，讓體感延遲接近 TTFT；在 runtime 中以串流事件實作。 | 3 → 24 |
| token | token | 模型讀寫文字的最小單位；價格、context window、輸出速度與 rate limit 都以它計算。 | 3 |
| tool calling | 工具呼叫 | 呼叫時附上可用工具清單，模型判斷需要時不直接回答，而是輸出一段呼叫某個工具的結構化請求。 | 1 → 4 |
| trajectory | 軌跡 | 一次任務從頭到尾所有模型輸出與 tool 結果的完整序列，是除錯與評估 agent 的主要材料。 | 1 → 27 |
| TTFT | 首字延遲 | time to first token：從送出請求到收到第一個輸出 token 的時間，主要由排隊、網路與 prefill（一次平行處理所有輸入）決定；之後的 decode 階段一次產生一個 token，速度以 tokens/s 衡量。 | 3 → 30 |
| workflow | 工作流程 | 由程式碼預先定義執行路徑，LLM 只負責其中某些步驟的系統。 | 1 → 18 |
| — | 單次呼叫 | 一次 prompt、一次回覆，沒有 loop 也沒有 tool 結果回饋。 | 1 |
| — | 副作用 | side effect：會改變外部世界狀態的動作，例如建立退貨單、退款、寄信；查詢沒有副作用。 | 1 → 5 |
| — | 任務適合度三問 | 判斷任務是否適合 agent 的三個特徵：開放（步驟無法事先列舉）、可驗證（結果能被客觀檢查）、可回復（錯誤能便宜地撤銷）。 | 1 → 35 |
| — | 開放 | open-ended：完成任務需要的步驟與路徑事先無法列舉，必須邊做邊看；這是 agent 存在的理由。 | 1 |
| — | 可驗證 | verifiable：存在客觀方法檢查結果是否正確，最好能在執行中檢查，同時決定 agent 能否自我修正與能否被評估。 | 1 |
| — | 可回復 | reversible：做錯了能以低成本撤銷；可回復性決定 autonomy 能給到多高。 | 1 |

## A.2 loop 與 tools

agent loop、tool 設計與副作用分級、system prompt、structured output、推理與規劃 patterns，以及大量工具的載入與 code-as-action（第 4–8、13 章）。共 38 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| ablation | 消融實驗 | 一次拿掉一個元件（例如一條 prompt 規則）跑回歸測試：拿掉就失敗的是 load-bearing（承重），全過的是刪除候選。 | 6 → 30 |
| ACI | agent 與電腦之間的介面 | agent-computer interface：把 tool 當成給模型用的介面來設計，比照 HCI 研究模型看得到什麼、會怎麼誤解、犯錯時怎麼引導。 | 5 |
| agent loop | agent 迴圈 | 呼叫模型、執行 tool call、把結果回填 messages、再呼叫模型，直到模型結束或撞到停止條件的迴圈。 | 1 → 4 |
| code-as-action | 以程式碼作為動作 | 讓模型輸出一段程式，在執行環境中呼叫 tools、跑迴圈與彙總，只把印出的結果回給模型；形式包括 CodeAct、programmatic tool calling 與 code mode。 | 13 → 17 |
| code_callable | 可從程式呼叫 | registry 中每個 tool 的欄位；有副作用（write／destructive）的 tool 一律為 False，必須走一般 tool call 與核准流程。 | 13 |
| CodeAct | CodeAct | 讓模型直接輸出可執行的 Python 作為行動、而不是 JSON tool call 的研究方法（2024）。 | 7 → 13 |
| deferred loading | 延遲載入 | tools 登記在 registry 中可以被找到，但在被需要之前，完整定義不出現在送給模型的 tool 清單。 | 13 |
| discriminated union | 帶標籤的聯集 | 一個值是幾種形狀中的恰好一種，並用共同的標籤欄位（discriminator，例如 `type`）標明是哪一種。 | 7 |
| dispatch | 派送 | 把模型提出的 tool call 對應到真正的函式並執行，要處理名稱不存在、參數不合、例外與結果過大四種情況。 | 4 |
| effect level | 副作用分級 | 替每個 tool 標上對外部世界的影響：read（唯讀）、write（可回復的寫入，例如建立退貨單）、destructive（不可逆或對外，例如退款、寄信、刪除）；未標註的 tool 一律當 destructive。 | 1 → 5 |
| few-shot | 少樣本提示 | 在 prompt 中放幾個「輸入 → 期望輸出」的例子；例子要少量、多樣、典型。 | 6 |
| granularity | 粒度 | 一個 tool 做多少事：一端是對應資料表增刪查改的 CRUD 級 tool，另一端是完成使用者心中一件事的 workflow 級 tool（例如 `orders_get_overview`）。 | 5 |
| idempotency | 冪等性 | 同一個操作執行一次和執行多次結果相同；查詢天生冪等，「退款 1,280 元」不是。 | 5 → 22 |
| idempotency key | 冪等鍵 | 同一把 key 重複送出只生效一次；由 harness 依業務意圖（`intent_fields`）推導，不放進模型看得到的 schema，去重發生在真正執行副作用的那一端。 | 4 → 5、22 |
| instruction hierarchy | 指令層級 | 不同來源的指令有不同優先權，衝突時高層級勝出，最低層級（tool 結果、使用者貼上的內容）只被當成資料。 | 6 → 31 |
| intent_fields | 意圖欄位 | `Tool` 上宣告「哪些參數定義同一個業務意圖」的欄位，idempotency key 與核准都綁在由它推導的意圖上。 | 5 |
| LATS | LATS | Language Agent Tree Search：把 MCTS 搬進 agent 環境、用模型當 value function，並結合失敗反思的方法（2023）。 | 8 |
| parallel tool calls | 平行工具呼叫 | 模型在同一回應中提出多個互不依賴的 tool call，讓 harness 同時執行以節省往返。 | 1 → 24 |
| plan-and-execute | 先規劃再執行 | planner 只看需求、一次寫出完整步驟清單，executor 逐步執行，計畫與現實不符時 replan 的 pattern；ReWOO 進一步用變數串接步驟。 | 8 |
| plan-then-execute | 先固定計畫再執行 | 安全文獻對 plan-and-execute 的稱呼：計畫在讀到任何不可信資料之前就寫好，資料只能沿事先挖好的空格流動。 | 8 → 32 |
| prefix invariant | 前綴不變式 | 延遲載入新 tool 時只追加到 tool 清單尾端，不重排、不刪除；前一輪的清單永遠是下一輪的開頭，以免打斷 prompt cache。 | 13 |
| progressive disclosure | 漸進揭露 | 資訊分層，模型先只看到最上層（例如 skill 的名稱與描述），判斷需要時才往下讀。 | 13 |
| ReAct | ReAct | Reasoning + Acting：模型交錯寫出想法（Thought）、提出動作（Action）、讀取觀察（Observation）的 pattern。 | 8 |
| reflection | 反思 | 產生答案或動作後由 critic 檢查、再依回饋修正的 pattern 家族，代表有 Self-Refine、Reflexion、CRITIC；沒有可信的外部訊號時效果有限。 | 8 |
| ScriptedModel | 劇本模型 | 依事先寫好的劇本回應的假模型，讓全書程式可以離線、可重現地執行並用 assert 驗證。 | 1 → 4 |
| Skill | 技能包 | 一個資料夾加一份 `SKILL.md`（frontmatter 寫名稱與描述、正文寫流程），可附參考文件與腳本，按需載入；也稱 Agent Skills。 | 12 → 13 |
| stop_reason | 停止原因 | 模型回應標示的結束原因；本書正規化為 end_turn、tool_use、max_tokens、refusal 四種，未知值由 adapter 直接報錯。 | 1 → 4、25 |
| structured output | 結構化輸出 | 模型輸出符合事先約定結構、要交給程式處理的資料（最常見是 JSON）；strict mode 以 constrained decoding 保證格式，但不保證內容正確。 | 7 |
| system prompt | 系統指令 | 每次呼叫都放在最前面、由開發者撰寫的指示，設定 agent 的身分、任務、規則與輸出方式；每一輪都隨 messages 重送。 | 6 |
| test-time compute | 推論時算力 | 在推論階段多花計算換取品質，有序列式（想更久）與平行式（多試幾條）兩條軸。 | 8 |
| tool call | 工具呼叫請求 | 模型輸出的特殊格式文字，意思是「我想用這些參數呼叫這個工具」；模型本身從不執行任何東西。 | 4 |
| tool registry | 工具註冊表 | 集中記錄所有 tools 的目錄，除了 schema 與實作，還有搜尋、權限、副作用與載入政策需要的 metadata。 | 13 |
| tool schema | 工具說明書 | 寫給模型看的函式說明：名稱、一句話描述，以及用 JSON Schema 寫成的參數規格；模型對 tool 的全部理解都來自它。 | 4 → 5 |
| tool search | 工具搜尋 | 常駐的 tool：模型用自然語言描述需求，harness 在 registry 中搜尋並把命中的 tools 追加到已載入集合。 | 13 |
| tree search | 樹搜尋 | 在決策點取樣多個候選、以 value function 評估前景、優先展開最好的分支、必要時退回的 pattern，代表有 Tree of Thoughts 與 LATS；best-of-N 是它的簡化形態。 | 8 |
| validate-and-repair loop | 驗證與修復迴圈 | 驗證失敗時先做不改變語意的本地修復，再把具體錯誤回饋給模型修正，並設次數上限與後備路徑。 | 7 |
| — | 可行動的錯誤訊息 | 說清楚發生什麼事、為什麼、可以怎麼做的錯誤回填，讓模型能靠改變行為修正。 | 4 → 5 |
| — | 兩段式 tool | 把 destructive 動作拆成 `prepare`（回傳不可竄改的報價與短效確認 token）與 `commit`（只接受該 token）。 | 5 |

## A.3 context 與 memory

context engineering、session log 與 compaction、retrieval 與 agentic RAG、memory 系統（第 9–12 章）。共 31 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| agentic RAG | agent 主導的檢索 | 把檢索變成 agent 可以反覆呼叫的唯讀 tool，由模型決定查不查、怎麼查、夠不夠，包括 query decomposition（拆解複合問題）與 query rewriting（改寫成知識庫用語）。 | 11 |
| BM25 | BM25 | 詞彙檢索的標準計分公式，結合 IDF（越少見的詞越有鑑別力）、詞頻飽和與長度正規化，以倒排索引實作。 | 11 |
| chunk | 片段 | 檢索的最小單位：一段可以被找到、放進 context、被引用的文字；chunking 決定檢索品質的上限。 | 11 |
| citation | 引用 | grounding 的可見證據：每個主張後面標出它來自哪一段，讓人能核對、讓 eval 能自動檢查。 | 11 → 40 |
| compaction | 壓縮 | 把較早的歷史換成交接筆記、只保留最近幾輪原文；切點必須是安全切點，摘要後用量要遠低於門檻（遲滯），並排在 tool output clearing 之後（分階段 compaction）。 | 10 |
| context engineering | 情境工程 | 決定每次呼叫模型時 context window 裡放哪些 token、以什麼順序與形式放的工作；prompt engineering 只關心指令措辭，context engineering 關心整個輸入的組成。 | 9 |
| context rot | context 腐化 | context 越長，模型越容易漏看或誤用其中資訊的現象，是逐漸下滑的斜坡，不是到上限才突然壞掉。 | 2 → 9 |
| embedding | 嵌入向量 | 把文字轉成固定長度的向量，讓意思相近的文字距離也相近；由 embedding model 產生，常以 cosine similarity 比較，查詢與文件必須用同一個模型與版本。 | 11 |
| episodic memory | 情節記憶 | 記錄發生過的具體事件或經驗的記憶，例如「上週承諾回電」。 | 2 → 12 |
| grounding | 有所本 | 讓回覆建立在提供給模型的資料上、可以追溯到來源的性質。 | 1 → 11 |
| handoff note | 交接筆記 | compaction 摘要的心智模型，固定六段：目標、使用者約束、已完成、進行中、下一步、未解問題；使用者約束逐字保留。 | 10 |
| hybrid search | 混合檢索 | 同時跑詞彙檢索與向量檢索再合併結果；分數尺度不同，常用 RRF 依名次融合。 | 11 |
| just-in-time 載入 | 按需載入 | context 裡只放輕量的引用（章節名、訂單編號、路徑），模型需要時再用 tool 把內容讀進來。 | 9 |
| memory poisoning | 記憶投毒 | 誘導 agent 把惡意內容寫進長期記憶，使注入在之後每個 session 都生效的攻擊。 | 12 → 31 |
| memory tool | 記憶工具 | 讓模型以 view、create、str_replace、insert、delete、rename 讀寫虛擬路徑 `/memories` 的工具，實際位置由 harness 決定；路徑要防 path traversal。 | 12 |
| procedural memory | 程序記憶 | 「怎麼做事」的記憶，例如處理退貨爭議的步驟說明；Agent Skills 是它的產品化。 | 2 → 12、13 |
| progress file | 進度檔 | 任務狀態的權威來源（例如 `progress.json`、`todo.md`），副作用由程式記帳在這裡，不靠摘要。 | 10 |
| RAG | 檢索增強生成 | Retrieval-Augmented Generation：先從外部資料找出相關片段放進 context，再讓模型根據片段生成答案。 | 11 |
| recall@k | 前 k 名召回率 | 所有相關 chunk 中出現在前 k 名的比例，回答「答案有沒有被撈到」，對 RAG 最重要；常與 MRR、nDCG@k 一起以 qrels（查詢相關性標註）計算。 | 11 |
| rerank | 重新排序 | 檢索後的第二階段精排：cross-encoder 把問題和候選 chunk 接在一起送進模型打分，準但貴，只用在前幾十個候選。 | 11 |
| RRF | 倒數名次融合 | Reciprocal Rank Fusion：只看名次，每一路的第 r 名貢獻 1/(k + r)，用來合併 hybrid search 的結果。 | 11 |
| semantic memory | 語意記憶 | 事實與偏好的記憶，例如「偏好退回原信用卡」。 | 2 → 12 |
| session log | 工作階段日誌 | 一次 session 所有事件的 append-only 紀錄（含 harness 的 context 管理動作）；不變式是 context 為 log 的純函式，可重建、倒帶、取回原文。 | 10 → 12、22 |
| sub-agent | 子代理 | 擁有自己獨立 context 的 agent，在乾淨視窗中完成大量閱讀，只把濃縮結論回傳主 agent。 | 10 → 20 |
| tombstone | 刪除墓碑 | 記錄「某使用者的資料在某時被刪除」，所有寫入路徑（含背景萃取與備份還原）都要先檢查，拒絕寫回刪除前的資料。 | 12 |
| tool output clearing | 清除 tool 輸出 | 把較舊的 tool 結果內容換成簡短 placeholder，但保留 tool call 本身與訊息位置；原文仍在 log 中。 | 10 |
| write policy | 寫入政策 | 由 harness 確定性執行、決定一筆資訊能不能進長期記憶與以什麼形式進去的規則。 | 12 |
| — | 版面配置 | context 的分層排列：穩定前綴（tool 定義、system prompt）→ 半穩定層（店家設定、memory 摘要）→ 動態層（對話與 tool 結果）。 | 9 |
| — | token 預算 | 替每次呼叫設定的 input 與 output 上限，通常遠小於模型的 context window。 | 9 |
| — | 檔案系統當外部 context | 大型內容寫進檔案，context 只留路徑、大小與預覽；壓縮必須可還原（丟掉內容但保留路徑或 URL）。 | 9 |
| — | 記憶範圍與優先順序 | 三種範圍：使用者、組織（租戶）、專案，agent 對組織記憶預設唯讀；衝突時產品規則 ＞ 組織規則 ＞ 使用者偏好 ＞ 模型推論。 | 12 |

## A.4 協定與環境

MCP、A2A、AG-UI 與付款協定，computer use 與 browser agent，code execution 與 sandbox（第 14–17 章）。共 32 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| A2A | Agent2Agent 協定 | 讓 agent 與 agent 互通的協定，核心抽象是 agent card 與有狀態機的 task。 | 2 → 15 |
| accessibility tree | 無障礙樹 | 瀏覽器從 DOM 算出、給輔助科技用的樹，每個有意義的節點有 role、accessible name 與 state，適合 browser agent 用元素而非座標下指令。 | 16 |
| AG-UI | AG-UI | agent 到前端的事件協定，定義文字串流、tool call、中斷與 state 同步；STATE_SNAPSHOT 送完整狀態，STATE_DELTA 以 JSON Patch 只送變化。 | 2 → 15 |
| agent card | agent 名片 | A2A 中宣告 agent 名稱、版本、連線方式、能力旗標、身分驗證需求與 skill 清單的 JSON 文件，通常發布在 well-known URI。 | 15 |
| audience | 受眾 | token 指定給哪個服務使用；下游只接受 audience 為自己的 token。 | 14 → 33 |
| browser agent | 瀏覽器 agent | 只操作網頁瀏覽器的 computer use 版本，除了截圖還能讀取頁面結構、用元素下指令。 | 16 |
| computer use | 電腦操作 | 讓模型透過看螢幕、動滑鼠鍵盤來使用給人設計的介面。 | 16 |
| container | 容器 | 以 Linux namespace（獨立的檔案系統、process 與網路視圖）、cgroup（資源上限）與 seccomp（過濾 system call）圍住程式的隔離層級，但仍直接使用 host kernel。 | 17 |
| credential proxy | 憑證代理 | sandbox 只拿到短效的 session token，proxy 在比對 allowlist 後於邊界外注入真憑證；secrets 不進 sandbox。 | 17 → 42 |
| egress | 出站流量 | 從 sandbox 往外發出的網路連線；預設拒絕、只開放 allowlist，因為資料外洩的最後一步幾乎都是把資料送出去。 | 17 → 31、32 |
| extensions | 擴充 | MCP 把選用能力定義成帶命名空間的擴充，協商後才啟用、預設停用，例如 MCP Apps（內嵌互動 UI）、Tasks（長時間工作）、Skills over MCP。 | 14 |
| frontend tool | 前端 tool | 由前端宣告、前端執行的 tool（例如請使用者上傳照片）；結果來自瀏覽器，視為不可信輸入。 | 15 |
| gVisor | gVisor | 在 container 與 host kernel 之間插入 user-space kernel，攔截 system call，大幅縮小 host kernel 攻擊面。 | 17 |
| host | 宿主 | MCP 中使用者實際面對的應用程式，擁有模型、對話紀錄與安全政策，是唯一看得到全貌的角色；host 內每個 client 只對應一個 server。 | 14 |
| JSON-RPC 2.0 | JSON-RPC 2.0 | MCP 訊息的基礎規格，只有 request、response、notification 三種訊息，與傳輸方式無關。 | 14 |
| mandate | 授權書 | agent 付款協定中以可驗證數位憑證組成的授權鏈；需區分 human-present（當下確認）與 human-not-present（事先授權、之後自行執行）。 | 15 |
| MCP | Model Context Protocol | 讓 agent 連接工具與資料的協定，角色為 host、client、server，primitives 為 tools、resources、prompts；版本以日期稱呼，本書以 2026-07-28 版為目前版本（截至 2026 年 10 月）。 | 2 → 14 |
| MCP gateway | MCP 閘道 | 所有 host 只能連的集中點，負責 server allowlist、定義 pin、授權、稽核與資料外洩防護。 | 14 |
| microVM | 微型虛擬機 | 每個 sandbox 是一台有自己 guest kernel 的精簡虛擬機，邊界是 hypervisor 與極少的虛擬裝置。 | 17 |
| Multi Round-Trip Requests | 多次往返請求 | MRTR：server 不反向發問，而是直接回傳「需要輸入」的結果，client 取得答案後附在原 request 上重送。 | 14 |
| OAuth 2.1 | OAuth 2.1 | MCP 遠端 server 採用的授權框架：server 以 Protected Resource Metadata 指出授權伺服器，client 走授權碼流程並使用 PKCE 與 resource indicator。 | 14 → 33 |
| perception–action loop | 感知—行動迴圈 | 觀察畫面、決定動作、執行、再觀察結果的節奏；tool 的回傳值是環境當下的狀態。 | 16 |
| primitives | 基本能力 | MCP server 提供的 tools、resources、prompts 三種能力，差別在由誰決定使用（模型、應用程式、使用者）。 | 14 |
| sandbox | 沙箱 | 限制程式能讀的檔案、能連的網路與能用資源的隔離執行環境；原則是用完即銷毀、不跨任務或租戶重用；secrets 不進 sandbox；egress 預設拒絕只開 allowlist；隔離強度依「誰寫的程式、誰會受害」選擇。 | 2 → 17 |
| scope | 權限範圍 | token 允許做的事；一開始只要最少的 scope，需要時再 step-up。 | 14 → 33 |
| `server/discover` | `server/discover` | MCP 2026-07-28 版新增的必要方法，client 任何時候都能問 server 支援的版本、能力與身分，不需先建立連線狀態。 | 14 |
| side-effect ledger | 副作用帳本 | checkpoint 中記錄每個不可逆動作是否已執行、結果是什麼（含「結果不明」）的帳本。 | 16 |
| stale observation | 過期觀察 | 模型依據的畫面在動作發生時已經改變；對策是晚綁定、動作前檢查與動作後驗證，並依語意特徵重新定位以避免 stale ref。 | 16 |
| stdio | 標準輸入輸出傳輸 | host 把 server 當 subprocess 啟動、以標準輸入輸出逐行傳訊息的 MCP transport；跑在使用者權限下。 | 14 |
| Streamable HTTP | Streamable HTTP | MCP 的遠端 transport：單一 HTTP endpoint，client 以 POST 送訊息，server 可直接回 JSON 或改用 SSE 串流進度；另一種標準 transport 是 stdio。 | 14 |
| task（A2A） | 任務 | A2A 的核心抽象：由 server 產生 id、有明確狀態機的遠端工作；可透過串流或 push notification 取得更新，但狀態以 server 為準（狀態名稱見 A.10）。 | 15 |
| warm pool | 預熱池 | 事先開好幾台尚未使用的乾淨 sandbox 待命，用閒置成本換使用者等待；大小可用 Little's law 估算。 | 17 |

## A.5 orchestration

workflow patterns、graph 與 state machine、multi-agent、human-in-the-loop、durable execution（第 18–22 章）。共 41 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| activity | 活動 | durable execution 中負責和外部世界打交道的程式碼（呼叫模型、查資料庫、寄信），結果要寫進 event history；部分系統稱為 step。 | 22 |
| approval fatigue | 核准疲勞 | 確認視窗太多，人開始不看就按同意，使核准失去意義。 | 8 → 21 |
| approval policy engine | 核准政策引擎 | 純函式式元件：輸入待執行動作與事實，輸出決定（auto、approve、deny 等）、核准者、期限與依據規則；不執行動作也不呼叫模型。 | 21 |
| approval request | 核准單 | 有 id、狀態、期限並綁定參數 hash 的持久化紀錄；狀態為 PENDING → APPROVED／REJECTED／EXPIRED／CANCELLED，APPROVED 執行後 → EXECUTED／FAILED。 | 21 |
| auto-approval classifier | 自動核准 classifier | 放在灰色地帶的第二位審查者，通常是另一個模型，判斷動作是否符合使用者意圖與政策；只能取代一部分人的注意力。 | 21 |
| background agent | 背景 agent | 使用者提交任務後不必等待，agent 在背景執行、完成後通知的互動模式。 | 22 → 37 |
| brief | 任務說明 | lead 交給 subagent 的說明，要包含目標、邊界、已做的全局決定與回傳格式；subagent 的全部理解都來自它。 | 20 |
| checkpoint | 檢查點 | 任務在某時刻的可恢復狀態；graph runtime 的自然粒度是 super-step，interrupt／resume 以它為唯一真相。 | 16 → 19、21 |
| debate | 辯論 | 多個 agent 對同一問題各自作答、互相反駁修正，再由裁判或共識規則決定的檢驗型架構。 | 20 |
| deny-overrides | 拒絕優先 | 取所有命中規則中最嚴格的結果，與順序無關；相對於 first-match（第一條命中決定），新增規則只可能更嚴、不可能意外放寬。 | 21 → 42 |
| durable execution | 可持久執行 | 讓長時間任務在 crash、重新部署或等待後從斷點繼續的執行模型，核心是 event history 與 replay。 | 2 → 22 |
| escalation | 升級 | 該處理的人沒空時，依 SLA 把核准交給權限更高的角色；也指把整段對話交給真人接手。 | 21 → 41 |
| evaluator-optimizer | 評估者與優化者 | generator 產生草稿、evaluator 依標準評分並回饋、generator 重寫，直到合格、停滯（stagnation stop）或達上限的 workflow pattern。 | 18 |
| event history replay | 事件歷史重播 | 恢復時從頭重跑程式碼，已記錄在 event history（也稱 journal，只追加的日誌）中的呼叫直接取用紀錄結果，外部世界不被重複打擾。 | 22 |
| fencing token | 隔離令牌 | 每次發出 lease 時給的遞增版本號，儲存層只接受目前版本的寫入，讓過期的持有者無法再生效。 | 22 → 36、43 |
| gate | 關卡 | prompt chaining 步驟之間用程式驗證上一步輸出的檢查，不合格就退回或停止。 | 18 |
| generator–evaluator | 產生者與評估者分離 | 一個 agent 負責做，另一個調成懷疑態度的 agent 負責檢查；比讓 generator 自我批判容易做好。 | 20 |
| git worktree | git worktree | 讓同一 repo 同時有多個工作目錄與分支，平行的 coding agent 各自改檔、互不干擾。 | 20 |
| handoff | 交接 | 目前的 agent 把控制權連同對話交給另一個 agent，由對方直接面對使用者的分散式控制。 | 20 → 23 |
| hard floor | 硬底線 | 寫在核准引擎程式碼中、不是可改規則的底線：只套用在「破壞性」風險類別，結果至少是 approve。 | 21 |
| human-in-the-loop | 人在迴圈中 | HITL：在流程中安排真人核准或接手，agent 會因此阻塞；提供事前控制，代價是延遲與人力。 | 2 → 21 |
| human-on-the-loop | 人在迴圈上 | agent 自己執行，人在旁監看、抽查，必要時喊停；不擋路，但只能事後發現問題。 | 21 |
| interrupt／resume | 中斷與恢復 | 需要核准時寫下 checkpoint、結束這次執行並釋放 worker，決定回來後從原處繼續；恢復時重新驗證，副作用只發生一次。 | 19 → 21、22 |
| lease | 租約 | 在一段時間內獨佔某個任務或 session 的權利，執行期間以 heartbeat 續約，過期後交給其他 worker；搭配 fencing token 防止舊持有者寫入。 | 22 → 36、43 |
| lost update | 更新遺失 | 兩個寫入者根據同一舊版本修改，後寫的蓋掉先寫的且沒有人收到錯誤；agent 並行寫入時特別嚴重。 | 20 |
| multi-agent system | 多 agent 系統 | 由多個 agent 分工完成任務的架構；不是更高級的 agent，而是有明確成本倍數的取捨，適合廣度搜尋、可平行、需要隔離的任務。 | 1 → 20 |
| orchestrator-workers | 協調者與工作者 | orchestrator 模型先讀問題、輸出子任務清單，程式派給 worker 平行執行再彙整的 workflow pattern。 | 18 |
| orchestrator–subagent | 協調者與子 agent | 最常見的 multi-agent 架構：lead agent 理解任務、規劃、派工與彙整，透過 tool 呼叫產生有獨立 context 的 subagent，只收回精簡結果。 | 20 → 40 |
| parallelization | 平行化 | 讓多個 LLM 呼叫同時執行再用程式合併：sectioning 切成互不相依的子任務以換速度，voting 同一任務做多次以換可靠性；平行分支不能有副作用。 | 18 |
| prompt chaining | 提示串接 | 把任務拆成固定順序的步驟，每步輸出是下一步輸入，步驟之間可插入 gate。 | 18 |
| reducer | 歸併函式 | 為 state 每個欄位宣告的合併規則（串接、聯集、相加），讓平行寫入的結果可預測。 | 19 |
| routing | 路由 | 先判斷輸入屬於哪一類，再交給為該類專門設計的下游流程；誤分流是靜默的，要有 fallback。 | 18 → 25 |
| saga | saga | 每個副作用都有對應撤銷（補償）動作、失敗時依序補償的長流程設計。 | 22 → 37 |
| super-step | 超級步 | 源自 BSP 的 graph 執行模型：同一步的節點讀同一份 state 快照，寫入在屏障處以 reducer 一次合併。 | 19 |
| supervisor | 監督者 | 集中式路由者，每一輪決定由哪位專家 agent 處理，處理完交回 supervisor。 | 20 |
| swarm | 群體 | 沒有中央指揮、agent 透過共享狀態（例如共享任務板）自我協調的架構。 | 20 |
| time travel | 時間旅行 | 回到歷史上的任一 checkpoint 分岔（fork）出新分支重新執行；不覆寫歷史，也不會回溯外部世界。 | 19 |
| timeout default | 逾時預設 | 等不到人時的處理；選「做錯時代價較低」的一邊，不可逆的 destructive 動作不得因逾時自動執行。 | 21 |
| workflow pattern | 工作流程模式 | 組合多次 LLM 呼叫的常見結構，五種為 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer。 | 18 |
| — | 控制拓撲與 context 拓撲 | multi-agent 架構的兩條獨立軸：誰決定下一個做事的 agent（集中或分散），以及 agent 之間看得到彼此多少東西（完全共享到完全隔離）。 | 20 |
| — | 風險類別 | 核准引擎使用的分類：讀取、寫入、金錢、破壞性；比副作用分級多出「金錢」，讓小額退款可依門檻在 L4 自動。 | 21 |

## A.6 framework 與 runtime

framework 核心抽象與擴充點、runtime 的事件、取消與重試、model 抽象與 routing、選型與 lock-in（第 23–26 章）。共 31 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| adapter | 轉接器 | ports and adapters（六角形架構）中，實作上層定義的埠 `complete(messages, tools, system) -> ModelResponse` 的供應商專屬程式；要避免最小公分母，並原樣保留不透明欄位。 | 25 → 26 |
| Agent | Agent | loom 核心抽象之一：宣告式設定，含名字、指令、可用 tools、可交接對象與 guardrails，屬於不可變宣告。 | 23 |
| build vs buy | 自建或採購 | 從完全自建、低階框架、高階框架、託管平台積木到託管 harness 的光譜選擇，先用硬性限制淘汰，再問差異化。 | 26 |
| cancellation | 取消 | 要求進行中的工作盡快停止；timeout 是時間到自動觸發的取消。副作用 tool 有一段寬限期（cancel grace），逾時未回就記成 unknown、不重試。 | 24 |
| cascade | 串聯升級 | 先用便宜模型做，依訊號判斷結果不可信時才升級到貴的模型重做的 routing 方式。 | 25 → 30 |
| circuit breaker | 熔斷器 | 記錄下游最近的成敗，失敗過多就跳到 `open` 直接跳過，冷卻後進入 `half_open` 放探測請求，成功才回到 `closed`。 | 25 → 36 |
| contract test | 契約測試 | 用同一組劇本在新舊 runtime 上跑，驗證可觀察的行為一致，是降低行為 lock-in 的可靠方法。 | 26 → 45 |
| Event | 事件 | loom 核心抽象之一：run 過程中每件事的不可變紀錄，是唯一的事實來源。 | 23 → 24 |
| exponential backoff | 指數退避 | 每失敗一次等待時間加倍並設上限；必須加上 jitter（例如 full jitter：在 0 到退避值之間均勻取隨機數），否則同時失敗的 client 會同時醒來形成 thundering herd。 | 24 → 36 |
| extension point | 擴充點 | 使用者能在不修改框架原始碼的情況下改變行為的位置；loom 只開放 before_run、wrap_model、wrap_tool、on_event 四個。 | 23 |
| fallback | 後備路線 | 主路徑失敗、低信心或熔斷時改走的去處，要選「錯了代價最低」的一邊。 | 18 → 25 |
| framework | 框架 | 呼叫你的程式的軟體（控制反轉）；library 則是由你的程式去呼叫。framework 能保證一致性，代價是要照它的規矩寫。 | 23 → 26 |
| Guardrail | 護欄（核心抽象） | loom 核心抽象之一：宣告在 Agent 上的檢查，依位置分為 input guardrail（輸入進系統前）、tool guardrail（tool 執行前後）、output guardrail（回答送出前），執行機制由 middleware 提供。 | 23 → 32 |
| Handoff | 交接（核心抽象） | loom 核心抽象之一：把控制權交給另一個 Agent 的宣告。 | 23 |
| lock-in | 供應商鎖定 | 一年後換掉某個選項要付出的代價，可細分為 API、狀態、行為、營運與模型五類。 | 26 |
| loop guard | 迴圈防護 | 以滑動視窗、「沒有新資訊」與狀態感知的 key 偵測原地打轉，觸發時寫 `guardrail_tripped`（`guardrail="loop_guard"`）並以 status=loop 結束。 | 24 → 34 |
| middleware | 中介層 | 把某個呼叫整個包起來、可檢查修改請求與結果並決定是否呼叫下一層的擴充形態，疊起來即洋蔥模型；hook 則只在 lifecycle 某點被呼叫、適合觀察。 | 23 → 24 |
| model routing | 模型路由 | 依任務類別、難度、成本或延遲把請求送到不同模型：規則路由、分類器路由、cascade，以及主模型＋輔助模型（前沿模型做決策、小型快速模型做摘要等輔助工作）。 | 18 → 25 |
| ModelSpec | 模型規格 | 記錄模型能力、可用區域、價格等資訊的版本化資料結構，router 依它過濾候選，而不是散落在 if 判斷中。 | 25 |
| principle of least abstraction | 最少抽象原則 | 一個概念要成為核心抽象，必須保護一個不變式、至少有兩種真實實作或用法、且在主流 SDK 之間穩定。 | 23 |
| retry amplification | 重試放大 | 多層各自重試使一次使用者動作在故障時變成數十個請求；原則是整條呼叫鏈只在一層（`loom.runtime`）重試，並設 retry budget（重試占總請求的比例上限）。 | 24 → 36 |
| Runner | 執行引擎 | loom 核心抽象之一：拿著 Agent 與輸入跑 loop、負責所有不變式（例如每個 tool call 都有對應結果）的引擎。 | 23 → 24 |
| runtime | 執行階段 | 負責事件串流、平行 tool calls、取消與逾時、重試退避與 loop guard 的層；在 loom 中是 `loom.runtime`。 | 24 |
| Session | 工作階段 | loom 核心抽象之一：一段對話的狀態存放處，持久化核心事件，讓下一輪接得上前一輪。 | 23 → 24 |
| stream event | 串流事件 | 只推給正在看的人、不持久化的事件（例如 `model_delta`、`tool_started`）；一件事完整發生後才彙總成核心事件寫進 Session。 | 24 |
| Tool | 工具（核心抽象） | loom 核心抽象之一：模型可以請求執行的能力，帶著 schema、副作用等級與實作函式。 | 23 |
| ZDR | 零資料保留 | zero data retention：廠商不保存請求與回應內容的承諾，常是選型的硬性限制。 | 26 → 41 |
| — | 託管 harness | 連 agent loop 都在雲端執行的託管服務：你定義 agent，loop、壓縮、sandbox、session 持久化由服務處理。 | 26 → 46 |
| — | 託管平台積木 | 不跑你的 loop，而是提供可分開使用的服務：託管 runtime、memory、tool gateway、identity、policy、eval。 | 26 |
| — | 行為 lock-in | 藏在「它剛好這樣做」裡的鎖定，例如未標註 tool 的預設處理、壓縮時機、錯誤回填格式；靠契約測試降低。 | 26 |
| — | 核心事件 | 寫進 Session 的持久化事件，共七種，是唯一事實來源（名稱見 A.10）。 | 23 → 24 |

## A.7 評估與可觀測性

eval 方法與統計、benchmarks、tracing 與成本、prompt 與模型優化（第 27–30 章）。共 41 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| AgentDojo | AgentDojo | 同時量測 agent 在 prompt injection 攻擊下的效用與被攻擊成功率的 benchmark，常用來評估防禦設計。 | 28 → 32 |
| benchmark | 基準測試 | 一組固定任務加固定評分方式，重點是可比較性；分數要標版本與日期，且不等於自家任務表現。 | 28 |
| calibration | 校準 | 用人工標註樣本量 LLM judge 與人的一致程度，達門檻才上線並定期重做；一致率會被基準比例誤導，所以看 Cohen's κ（扣除碰巧一致）。 | 27 |
| capability eval | 能力評估 | 收錄 agent 目前還做不好的題目，是往上爬的目標；穩定通過後畢業進 regression eval。 | 27 → 38 |
| code grader | 程式評分器 | 用確定性程式判分，例如比對狀態、跑測試、檢查 JSON 欄位。 | 27 |
| cost attribution | 成本歸因 | 把每筆成本歸到租戶、功能、agent、prompt 版本、模型、tool 等維度；成本在寫入時依有版本的價目表計算。 | 29 |
| data contamination | 資料污染 | benchmark 題目、解答或相似內容出現在訓練資料中，使高分可能來自背答案；偵測方式包括 canary 字串、補完探測與時間切分。 | 28 |
| error analysis | 錯誤分析 | 讀失敗的 trace，先 open coding（逐條寫下問題、不預設類別）再 axial coding（歸類並定義），得出 failure taxonomy，依頻率與嚴重度排序決定先修什麼。 | 27 → 38 |
| eval | 評估 | 用一組固定任務在可控環境中執行 agent、以明確規則打分；對象是機率性的，結論是比例與它的不確定性。 | 27 |
| failure taxonomy | 失敗分類 | 從自家 trace 歸納出的失敗類型清單；通用分類（如 MAST）只能當參考。 | 27 → 34 |
| fine-tuning | 微調 | 在既有模型上用自己的資料繼續訓練、改變權重，形式包括 SFT（模仿好的 trajectory）與 distillation（用前沿模型當老師）；要注意 catastrophic forgetting。 | 30 |
| GenAI semantic conventions | GenAI 語意慣例 | OpenTelemetry 為生成式 AI 定義的命名規範；agent、模型、tool 的 span 名稱分別為 `invoke_agent`、`chat`、`execute_tool`。 | 29 |
| GEPA | GEPA | Genetic-Pareto：用模型讀失敗紀錄與文字回饋來診斷並改寫 prompt，並保留「在至少一題上表現最好」的所有候選的 prompt optimizer。 | 30 |
| Goodhart 定律 | Goodhart 定律 | 指標一旦成為目標，就不再是好指標；在 optimizer 上表現為過度擬合 train 集。 | 30 |
| held-out 集 | 保留集 | 只用於最終比較、少數人能存取的題目集；調 prompt 時看的題目不能是最後打分數的題目。 | 28 → 30 |
| LLM-as-judge | 以模型當評審 | 讓另一個模型依 rubric 讀 transcript 後給判斷；有位置偏誤、冗長偏誤、自我偏好等偏誤，上線前必須校準。 | 27 |
| observability | 可觀測性 | 只靠系統對外輸出的資料（log、metric、trace）就能回答系統為什麼是現在這樣，包括事先沒想到的問題。 | 29 |
| OpenTelemetry | OpenTelemetry | 簡稱 OTel：CNCF 旗下的開源觀測標準，提供 API、SDK、OTLP 與 semantic conventions。 | 29 |
| OSWorld | OSWorld | 在真實虛擬機中執行桌面任務、以執行式腳本評分的 computer use benchmark。 | 28 |
| outcome grader | 結果評分器 | 不相信 agent 的敘述，直接查環境狀態（退款表、退貨單、工單）判定成功。 | 27 |
| Pareto frontier | 帕雷托前緣 | 沒有被任何其他設定支配（每個目標都不差且至少一項更好）的設定集合。 | 30 |
| pass@k | pass@k | 同一題跑 k 次至少一次成功的機率，隨 k 上升；適合「可以多試再挑」的場景。 | 27 |
| pass^k | pass hat k | 同一題跑 k 次全部成功的機率，隨 k 下降；衡量客服這類任務的一致性。 | 27 → 38 |
| PII | 個人可識別資訊 | 能直接或間接識別某個人的資料；trace 匯出前遮蔽，使用者 id 以 HMAC 假名化。 | 29 |
| prompt optimization | 提示最佳化 | 把 prompt 當參數、eval 分數當目標函數，由程式搜尋候選的做法（例如 DSPy、GEPA）。 | 30 |
| regression eval | 回歸評估 | 收錄已穩定做對的題目，目標接近 100%，任何下降代表改壞了東西。 | 27 → 34、38 |
| reward hacking | 獎勵投機 | 為了拿分而鑽評分規則的空子（例如改測試），而不是真的完成任務；grader 要放在 agent 碰不到的地方。 | 27 → 30、43 |
| RLVR | 可驗證 reward 的強化學習 | reinforcement learning with verifiable rewards：policy（受訓模型）在環境中跑 rollout，reward 由程式驗證（測試、答案比對、狀態檢查）；GRPO 是常見演算法。 | 30 |
| rubric | 評分準則 | 把「好」拆成可獨立判斷的維度與標準，供 LLM judge 或人工評分使用；必過項不能被平均掉。 | 27 → 40 |
| saturation | 飽和 | 前沿系統分數已接近上限，剩下的失敗多半是錯題，benchmark 失去鑑別力。 | 28 |
| scaffold | 鷹架 | 包在模型外面的 agent 程式（loop、tools、prompt、預算），等於 harness；不同 scaffold 的分數不能直接比。 | 28 |
| span | 區段 | trace 中一段有開始與結束時間的工作，以 parent span id 連成樹（樹根為 root span）；attributes 描述工作內容，status 只記技術成敗。 | 29 |
| SWE-bench | SWE-bench | 以真實開源專案 issue 為題、在 Docker 中跑隱藏測試評分的 coding benchmark 系列：FAIL_TO_PASS 確認修好、PASS_TO_PASS 確認沒改壞；有 Verified、Lite、Multilingual、Multimodal 與更難的 SWE-Bench Pro 等版本。 | 28 |
| tail sampling | 尾端取樣 | 整條 trace 結束後才依結果決定保留（錯誤、成本或延遲異常、被負評的全留）；head sampling 則在請求開始時就決定，會丟掉大部分失敗案例。 | 29 |
| τ-bench | τ-bench | 以政策文件、資料庫 tools 與使用者模擬器評估客服 agent 的 benchmark，推廣了 pass^k；後續的 τ²-bench 引入 dual-control（使用者也有自己的工具）。 | 28 → 41 |
| Terminal-Bench | Terminal-Bench | 在終端機中完成各種真實工程任務、以檢查腳本評分的 benchmark。 | 28 |
| time horizon | 時間跨度 | METR 提出的彙總方式：以「agent 有 50% 機率完成的任務，人類專家需要多久」描述能力。 | 28 → 46 |
| trace | 追蹤 | 把一次請求中每個模型呼叫、tool 呼叫的輸入、輸出、耗時、token 記錄成樹狀結構；由 span 組成、共享同一個 trace id。 | 2 → 29 |
| user simulator | 使用者模擬器 | 用另一個模型依劇本扮演顧客、回答 agent 追問的評估元件；本身也有雜訊，要定期抽查。 | 27 → 28、41 |
| — | 保護清單 | 權限檢查、sandbox、loop guard、人工核准等負責環境保證的元件，不參加品質 ablation，也不參與自動移除。 | 30 → 46 |
| — | 每件成功任務的成本 | 分母只算成功的任務、分子含失敗嘗試、升級重跑與轉真人成本；真正要優化的成本指標。 | 30 → 35 |

## A.8 安全與治理

威脅模型、防禦設計、identity 與授權、可靠性與治理框架（第 31–34 章）。共 48 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| agent identity | agent 身分 | 讓系統分辨「哪個 agent、哪個版本、誰負責」的身分，以部署配發的 workload identity 證明，用於歸責、限權與撤銷。 | 33 |
| ambient authority | 環境權限 | 權限瀰漫在執行環境中、不必明確出示；agent 以服務帳號行動時，每個動作都帶著該帳號的全部權限。 | 32 |
| audit log | 稽核日誌 | 回答「是誰、代表誰、憑什麼、做了什麼」的紀錄；append-only、以 hash chain 防竄改、不能取樣，與 trace 分開儲存與授權。 | 33 |
| authorization | 授權 | 回答「你能不能做這件事」；與 authentication（你是誰）、accountability（事後能否證明是誰做的）依序建立。有效權限 = 使用者權限 ∩ agent 權限 ∩ 任務範圍。 | 33 |
| blast radius | 爆炸半徑 | 一個 tool 被濫用時最大的損害範圍；做不到小到可接受或可回復的，就要加人工核准。 | 31 → 32、38 |
| burn rate | 燒率 | 目前錯誤率是 SLO 允許錯誤率的幾倍；燒率 1 代表剛好在視窗結束時用完 error budget。 | 34 |
| CaMeL | CaMeL | 從可信請求抽出控制流與資料流、以 Q-LLM 處理不可信資料、並給每個值附上來源與讀者標籤、在 tool 呼叫時以政策檢查的設計（2025）。 | 32 |
| capability | 能力憑證 | 持有就能做憑證上寫的那件事、且只能做那件事的權限模型；在 CaMeL 中指附在資料上的來源與讀者標籤。 | 32 |
| confidentiality | 機密性 | 「這個值能不能給這個對象看」，保護資料不外流；以收件人是否在允許的讀者中檢查。 | 32 |
| confused deputy | 混淆代理人 | 有權限的中介者被誘導用自己的權限替不該有權限的請求者辦事；防禦是每次依原始請求者身分授權。 | 14 → 33 |
| data exfiltration | 資料外洩 | 資料被未經授權地送出系統邊界；管道不只對外 tool，還包括 tool 參數、輸出渲染、公開寫入與跨 session 記憶。 | 31 |
| defense in depth | 縱深防禦 | 疊上多層獨立防護：機率層少讓攻擊抵達、確定性層抵達了也做不成、偵測與回應做成了也很快發現並撤銷。 | 32 |
| delegation | 委派 | 新 token 同時寫著主體（使用者）與行動者（agent）的代理語意；相對於 impersonation（下游以為是本人），對 agent 系統幾乎總是正確選擇。 | 33 |
| dual-LLM | 雙 LLM 模式 | 把能呼叫 tool、但從不直接讀不可信內容的 privileged LLM（P-LLM），與處理不可信內容、但沒有任何 tool 能力的 quarantined LLM（Q-LLM）拆開，兩者以符號變數溝通。 | 32 |
| error budget | 錯誤預算 | SLO 允許的失敗量，例如 99% 的 SLO 在視窗內允許 1% 失敗；burn rate 以它為基準。 | 34 |
| EU AI Act | 歐盟人工智慧法 | 依用途分級的具法律約束力法規，沒有獨立的 agent 類別；分為禁止、高風險、有透明義務與其他用途。 | 34 → 41 |
| excessive agency | 過度代理 | OWASP LLM06：agent 被賦予超出任務需要的功能、權限或自主性，使任何錯誤都可能造成過大危害。 | 31 → 32 |
| guardrails | 護欄 | 在模型輸入與輸出路徑上檢查與轉換內容的元件，分輸入、輸出、tool 三個位置，三者擋的東西與可靠度不同：注入分類屬於機率型，schema 驗證與參數檢查屬於確定性。 | 32 |
| hallucinated tool call | 幻覺工具呼叫 | 呼叫不存在的 tool，或用捏造的參數呼叫存在的 tool；後者以 provenance（ID 應來自使用者輸入或先前的 tool 結果）檢查偵測。 | 34 |
| hash chain | 雜湊鏈 | 每筆紀錄包含前一筆的 hash 再對自己算 hash，使事後修改、刪除中間一筆或截斷都能被發現。 | 21 → 33 |
| indirect prompt injection | 間接注入 | 注入文字藏在 agent 讀取的內容中（網頁、評論、物流備註、tool 結果），由第三方寫入。 | 6 → 31 |
| injection classifier | 注入分類器 | 輸出「這段文字含注入企圖的機率」的模型；分數適合當偵測訊號，是第二道防線而不是第一道。 | 31 → 32 |
| integrity | 完整性 | 「這個值有沒有被不可信來源左右」，保護做什麼、對誰做（收件人、金額、訂單編號）不被竄改。 | 32 → 40 |
| ISO/IEC 42001:2023 | ISO/IEC 42001 | 第一個可第三方驗證的 AI 管理系統標準；證書證明組織有一套管理 AI 的制度，不證明單一系統安全。 | 34 |
| least privilege | 最小權限 | 每個元件只拿到完成任務所需的最小能力，分 tool、scope、憑證三層落實。 | 32 |
| lethal trifecta | 致命三要素 | 同一個 context 同時能讀私有資料、接觸不可信內容、對外傳送資料時，就有結構性外洩風險，要在架構上切斷一邊。 | 2 → 31 |
| MAST | MAST | Multi-Agent System Failure Taxonomy：分析多個開源 multi-agent 框架執行紀錄歸納出的失敗分類（2025）。 | 34 |
| NIST AI RMF | NIST AI 風險管理框架 | 自願性框架，分 Govern、Map、Measure、Manage 四個 function。 | 34 |
| non-repudiation | 不可否認性 | 讓行動者事後無法否認「這是我做的」；需要核准時的強認證與簽章憑證，hash chain 只能證明沒被改。 | 33 |
| OWASP Top 10 for Agentic Applications 2026 | OWASP Agentic Top 10 | ASI01–ASI10 的 agent 應用風險清單（2026 版，2025 年 12 月發布）。 | 31 |
| OWASP Top 10 for LLM Applications 2025 | OWASP LLM Top 10 | LLM01–LLM10 的 LLM 應用風險清單，與 agent 最相關的是 LLM06 Excessive Agency。 | 31 |
| postmortem | 事後復盤 | blameless（不究責）的事故檢討；agent 版要額外回答失敗屬於哪一類、哪些 trace 變成 regression 題、哪層防線該攔卻沒攔。 | 34 |
| premature completion | 過早宣告完成 | agent 宣稱完成但 outcome 並未達成；完成宣稱必須有證據。 | 34 → 39 |
| prompt injection | 提示注入 | 把惡意指令藏在輸入或 tool 回傳內容中，誘使模型做出開發者不允許的事；分為 direct（使用者本人覆寫指令）與 indirect（藏在 agent 讀取的第三方內容），目前沒有可靠的模型層解法。 | 2 → 31 |
| rug pull | 事後變更 | tool poisoning 的變形：server 在審核時提供正常定義，之後才悄悄改掉；對策是定義 pin。 | 14 → 31 |
| silent failure | 靜默失敗 | 每個呼叫都成功、格式正確、語氣誠懇，但內容和真實世界不一致的失敗，是 agent 最危險的失敗。 | 34 |
| SLO | 服務水準目標 | 對 SLI（可量測的比例，例如宣稱完成的退款中對帳成立的比例）設定的目標與時間視窗，例如 28 天內 ≥ 99%。 | 34 → 38 |
| step-up authorization | 升級授權 | 暫停動作向有權限的人取得額外授權，換一張只對這筆交易有效（綁定參數 hash）、短效、只能用一次的 token。 | 14 → 33 |
| taint tracking | 污點追蹤 | 來自不可信來源的值被標為受污染，由它計算出的值也跟著受污染，直到抵達 sink（會產生副作用的地方）時接受檢查。 | 32 |
| threat modeling | 威脅建模 | 上線前有系統地回答：我們在做什麼、哪裡可能出錯、要怎麼處理、做得夠好嗎；常以資料流圖標出 trust boundary，再用 STRIDE 逐項檢查。 | 31 |
| token exchange | 權杖交換 | RFC 8693：以 subject_token 與 actor_token 換一張受眾為下一跳、範圍不超過原本、期限更短的新 token，並以 `act` claim 記下行動者；也稱 on-behalf-of 流程。 | 33 |
| token passthrough | token 直通 | 把收到的 token 原封不動轉送給下游；MCP 規格明文禁止，下游只接受 audience 為自己的 token。 | 14 → 33 |
| tool poisoning | 工具投毒 | 在 server 撰寫的 tool 描述中夾帶指示；模型完整讀入，但介面通常只顯示名稱。 | 14 → 31 |
| trust boundary | 信任邊界 | 資料從一個信任等級跨到另一個的地方，威脅幾乎都發生在跨越邊界的資料流上。 | 31 |
| — | 機率型防禦與確定性防禦 | 機率型防禦讓模型比較不容易被說服（prompt 規則、標記、分類器）；確定性防禦不管模型怎麼想都成立（沒有寄信能力、egress 鎖死、金額上限）。 | 32 |
| — | 可信完成率 | 青鳥最核心的 SLI：扣除「宣稱完成但對帳不成立、靜默放棄、被偵測器標記」三種壞結局後的比例。 | 34 |
| — | egress 四級 | lethal trifecta 檢查中對外通訊的等級：none、bound（只能回給本人或固定對象）、allowlist（等同授權）、open。 | 31 → 32 |
| — | 受污染的 context | 審查單位是 context：讀過不可信內容就視為受污染；sub-agent 的 text 回傳會把污染帶回主 context，typed 回傳可以阻斷。 | 31 |

## A.9 system design 與營運

設計方法論與估算、production 架構、產品化、上線路線圖、案例與設計演練、新技術評估（第 35–44、46 章）。共 48 個術語。

| 英文術語 | 中文 | 定義 | 章節 |
|---|---|---|---|
| action inventory | 動作清冊 | 列出 agent 所有動作及其副作用等級、autonomy、`code_callable`、`intent_fields` 的表，是設計審查的必要產出。 | 35 → 45 |
| AgentSpec | AgentSpec | 租戶設定與 release 一起編譯成的 agent 規格，以內容 hash 為版本號，每段對話 pin 住版本；租戶設定只能收緊、不能放寬平台底線。 | 36 → 42 |
| ambient agent | 環境式 agent | 不等使用者開口，監聽事件（新訂單、新退貨單）自己判斷是否處理，只在需要人時推送卡片的互動模式。 | 37 |
| cache poisoning | 快取投毒 | 一個任務污染共用快取（例如 repo 快取）、進而影響之後所有任務；快取只能由可信的一方寫入。 | 43 |
| canary | 金絲雀發布 | 先讓小比例真實流量使用新版本，觀察成功率、成本、延遲與轉真人比例再擴大。 | 6 → 36 |
| citation precision／recall | 引用精確率與召回率 | precision：有引用的主張中引用真的支持主張的比例；recall：需要引用的主張中確實附上引用的比例；兩者要一起看。 | 40 |
| control plane | 控制平面 | 管「系統應該長什麼樣」：租戶設定、政策、prompt 與 tool 版本、知識庫匯入、eval 與發布。 | 42 → 43 |
| copilot | 副駕駛 | 把 agent 嵌進使用者既有工作流程、擬好草稿由人決定的互動模式，對應 L1。 | 37 → 38 |
| data plane | 資料平面 | 管「每一則訊息怎麼被處理」：接收訊息、跑 agent loop、呼叫模型與 tools、寫 log。 | 42 → 43 |
| deep research | 深度研究 | 給定開放的研究問題，agent 自行規劃、多輪搜尋閱讀、修正方向，最後產出有結構、附引用報告的任務類型。 | 40 |
| demo gap | demo 落差 | demo 證明的是「它做得到」，上線需要證明的是「它幾乎每次都做得對，做錯時損失有限，而且我們會知道」。 | 38 |
| Edge Gateway | 邊緣閘道 | tenant 身分唯一的來源：驗證通路簽章、解析 `tenant_id` 與 `shopper_id` 並往下傳；任何一層都不從模型輸出讀取 tenant。 | 42 → 45 |
| evidence ledger | 證據帳本 | 報告中每個數字都必須追溯到證據：查詢結果以 Q 編號、衍生值以 D 編號，沒有證據編號的數字由核對器擋下。 | 40 → 44 |
| fail-closed | 故障時關閉 | policy 服務故障時，唯讀 tool 可繼續，寫入與 destructive tool 一律拒絕。 | 36 |
| kill switch | 緊急開關 | 一鍵關閉 agent 或某個 tool 的開關，上線前要寫好 runbook 並演練。 | 38 |
| Little's law | Little 定律 | 系統中的平均數量 = 到達率 × 平均停留時間（L = λ×W），用來估算並行 session、sandbox 與 worker 數量。 | 17 → 35 |
| model gateway | 模型閘道 | 每次模型呼叫都經過的元件：檢查租戶配額、快取、routing、熔斷器，透過 adapter 呼叫並記錄用量。 | 36 |
| noisy neighbor | 吵鬧的鄰居 | 共用資源的系統中，一個租戶的大量使用拖慢或拖垮其他租戶。 | 36 → 42 |
| pooled／silo／bridge | 共用／專屬／橋接 | 多租戶資源的三種配置：所有租戶共用、每租戶專屬、部分共用部分專屬；每一類資源各自決定，不是整個系統選一種。 | 36 → 42 |
| reference architecture | 參考架構 | 大多數系統都會長成的骨架：API gateway、無狀態的 agent service 與 worker、session store、event log、model gateway、tool gateway、sandbox pool、job queue、observability pipeline。 | 36 |
| release manifest | 發布清單 | 把 prompt、模型 snapshot、tools、fallback 等影響行為的東西鎖定到確切版本、以內容雜湊為版本號的清單。 | 36 |
| row-level security | 列級安全 | RLS：在資料表上定義政策，讓任何查詢都被自動加上可見列的條件，連寫錯的 SQL 也逃不掉。 | 44 |
| semantic cache | 語意快取 | 依問題的意思重用答案的快取；key 必須包含 tenant 與設定版本。 | 42 |
| shadow | 影子流量 | 讓新版本在背景處理同樣的請求、不回給使用者也不執行副作用，只比較 trajectory 與輸出差異。 | 26 → 36 |
| shadow mode | 影子模式 | agent 對真實流量產生決策但不送出、不執行，只和真人實際處理比對（shadow 一致率）。 | 37 → 38 |
| SOP | 標準作業程序 | 企業寫給真人員工的操作規範；agent 版要編譯成狀態、轉移、guard 與不變式，而不是只貼進 prompt。 | 41 |
| stage gate | 階段關卡 | 每兩個階段之間的閘門，有事先寫下、可量測、由指定的人判定的退出條件，通常同時包含目標指標與護欄指標。 | 38 |
| stateless harness | 無狀態 harness | harness process 不擁有任何 session 狀態，所有狀態在外部 event log，任何 worker 都能喚醒任何 session。 | 36 |
| text-to-SQL | 自然語言轉 SQL | 把自然語言問題翻成 SQL 查詢的技術，只是 analytics agent 的一個零件。 | 44 |
| token bucket | 令牌桶 | 容量 C、每秒補充 r 的限流演算法，允許有限爆量並限制長期平均；用於每租戶 token 配額。 | 24 → 36 |
| tool gateway | 工具閘道 | 每次 tool 呼叫都經過的確定性元件：權限、policy、憑證注入、idempotency 去重與稽核。 | 36 → 42 |
| undo window | 撤回窗口 | 動作提交後延遲一段時間才真正執行，窗口內撤回等於沒發生；其他撤銷機制還有草稿優先與補償動作。 | 37 |
| unit economics | 單位經濟 | 以一次對話、一個成功解決的問題或一個客戶月為單位看收入與成本，核心是毛利率與損益兩平點。 | 37 |
| verification gate | 驗證閘門 | agent 宣告完成前必須有外部證據（測試通過、狀態檢查）；沒有證據的完成記為 `unverified`，不等於 `done`。 | 39 → 43 |
| vertical agent | 垂直領域 agent | 服務某個產業或職能的 agent，比通用 agent 多了必須遵守的業務政策、有權限邊界的資料與動作、可以接手的真人。 | 41 |
| warm handoff | 溫轉接 | 轉給真人時附上對話摘要、已查到的資料與卡住的原因，讓真人不必重問。 | 37 → 41 |
| — | 七步驟框架 | 任務與成功標準 → autonomy 與風險 → 架構選型 → context 與 tools → 評估 → 安全 → 營運；每一步有明確產出物。 | 35 |
| — | 估算記號 | k 為每 session 模型呼叫次數、P 為固定前綴 token、d 為每步新增 token，每 session 輸入 ≈ k×P + d×k(k−1)/2；h 為 cache 命中率、λ 為尖峰到達率。 | 3 → 35 |
| — | 敏感度分析 | 每個假設給樂觀值與悲觀值、一次只動一個（one-at-a-time），依結果擺動排序（tornado 圖），找出真正的成本槓桿。 | 35 |
| — | autonomy 蠕變 | 沒有經過審查，就因為「最近都沒事」把自主邊界放寬（例如把 500 元門檻調到 2,000 元）。 | 38 |
| — | 平台底線 | 多租戶平台的最低規則：租戶設定只能比平台更嚴、不能更鬆。 | 42 |
| — | 多租戶不變式 | tenant 只從 Edge Gateway 驗證過的 session 注入、tool schema 不放 tenant 欄位；所有快取 key 都含 tenant 與設定版本。 | 33 → 42 |
| — | 有效權限 | agent 代表使用者執行時能存取的範圍：使用者權限 ∩ agent 權限 ∩ 任務範圍。 | 33 → 44 |
| — | 證據權限下限 | 報告是衍生資料：分享前檢查讀者權限是否涵蓋報告引用的所有證據。 | 44 |
| — | SQL 守門員 | 確定性程式，依序做語句檢查、權限改寫、成本估計、執行與結果限制，只連唯讀副本。 | 44 |
| — | 證據階梯 | 判斷新技術的五階：⓪ 宣傳或 demo、① 廠商自報、② 可重現實驗、③ 多方採用、④ 自家 eval 驗證；只有 ④ 能決定 adopt。 | 46 |
| — | 技術雷達 | 依證據強度、自家 eval 改善與遷移成本，把新技術放進 adopt／trial／assess／hold 四環（沿用 Thoughtworks 的名稱）。 | 46 |
| — | harness 元件生命週期 | 承重 → 待驗證 → 候選移除 → 已移除；元件要可拆卸，安全與政策元件不參與自動移除。 | 46 |

## A.10 青鳥案例與 loom 專有名詞

這一節收錄只在本書中成立的名稱：貫穿案例的人物、租戶、代表性事故，以及 `loom` 的版本、模組、事件與狀態名稱。它們不是業界通用術語，但全書各章靠它們互相引用，所以名稱必須一字不差。分成六張表，各表內依英文字母或出現順序排列。

### A.10.1 人物與組織

| 名稱 | 身分 | 在書中的角色 | 章節 |
|---|---|---|---|
| Amy | 客服人員 | 第 14、33 章的青鳥客服人員；第 33 章事故中核准欄位被寫成 `amy` 而無法證明真偽 | 14 → 33 |
| 小芸 | 顧客 | 第 8 章一則「一題兩問」客訴的顧客 | 8 |
| Bluebird（青鳥科技） | 貫穿案例的公司 | 做電商營運 SaaS，客戶是數千家中小型網店；依序做出客服 agent、內部 coding agent、營運 research agent，再把共用部分抽成 `loom` | 1 |
| Iris | 剛轉職的 AI 工程師 | 後端背景，第一次負責 agent 專案；全書每一章的主要實作者，第 38 章的角色表中擔任 AI engineer | 1 |
| Maya | 資安工程師 | 負責 threat modeling 與安全審查；第 31 章在 staging 以無害測試證明評論與備註能改變 agent 行為 | 1 → 31 |
| 小林 | 客戶成功經理 | 第 44 章負責 komori 與 harbor 兩家店，問「harbor 九月退貨率為什麼變高」，用來追蹤權限感知的分析流程 | 44 |
| 老陳 | staff engineer | 經歷過多次分散式系統上線，Iris 的 mentor；常以提問代替直接給答案，並在第 45 章寫下 v1.0 的四條規則 | 1 |
| 阿哲 | 產品經理 | 關心使用者體驗、成本與上線時程，推動批次任務、把客服 agent 賣給商家、把 issue 指派給 agent 等需求 | 1 |

人物一律不用性別代名詞，以名字或「對方」稱呼（寫作規範第 6 節）。

### A.10.2 租戶、店家與外部夥伴

| 名稱 | 類型 | 出現情境 | 章節 |
|---|---|---|---|
| harbor | 租戶代號 | 第 33 章 research agent 的 `tenant_id` 由模型依對話中「海港家居」字樣填成 harbor，混進其他店家的訂單；第 44 章「harbor 九月退貨率 12%」是沒有任何查詢產生過的數字 | 33 → 44 |
| komori | 租戶代號 | 小森選物的租戶代號（第 33 章寫作「小森選物（komori）」）；範例顧客 u42 的記憶存在 `tenants/komori/users/u42/` | 12 → 33、42、44 |
| pinecone、sunny | 租戶代號 | 第 44 章權限事故中，只負責 komori 與 harbor 的經理在排名中看到了這兩家 | 44 |
| u42 | 範例顧客 id | 「偏好退回原信用卡」的記憶片段主人；第 42 章追蹤的退款請求也來自 u42 | 2 → 12、42 |
| 小島選物 | 大客戶店家 | 第一個使用批次任務、一次丟進 60 張延誤訂單的店家，引出 compaction 的三個事故 | 10 |
| 小花花藝 | 店家 | 鮮花不接受個人因素退貨，但檢索拿到平台通則，agent 回答「7 天內可以退」 | 11 |
| 小森選物 | 店家（租戶代號 komori） | system prompt 組裝範例的租戶；第 33 章 B-1042 被退 3,200 元卻說不清誰核准；第 42 章被晨光生活的流量拖累，也是語意快取事故中答案被錯用的一方 | 6 → 33、42 |
| 快航物流 | 虛構物流合作商 | 第 10 章的區域性延誤；第 15 章以 A2A 提供查詢貨態與破損理賠的 agent | 10 → 15 |
| 晨光生活 | 大型連鎖店家 | 限時搶購吃光 TPM 造成 noisy neighbor；其顧客從語意快取拿到小森選物的「鑑賞期 7 天」 | 42 |
| 禾田 | 保健食品店 | 退款 SOP 貼進 prompt 後，agent 跳過身分驗證、多退運費，引出把 SOP 編譯成狀態機 | 41 |

### A.10.3 三個 agent 與代表性事故

| 名稱 | 說明 | 章節 |
|---|---|---|
| 客服 agent | 查訂單、查物流、退款；v1 以 L3 上線（查詢自主、寫入要客服確認），之後 500 元以下退款移到 L4 | 1 → 21、42 |
| 內部 coding agent | 在 sandbox 內 L4，所有寫入關在 sandbox 與分支裡，合併永遠由人決定；第 43 章擴充成 issue 到 PR 的背景平台 | 1 → 39、43 |
| 營運 research agent | L5：預算內自主完成月度分析等研究任務 | 1 → 40、44 |
| 週五 demo 的三個事故 | 例外炸掉 process、同參數重查四十幾次、tool call 缺結果；`loom` v0.1 的起點 | 4 |
| 退錯的圍巾 | 小芸一句話問了兩件事，agent 建錯退貨單又漏答物流，用來比較推理與規劃 patterns | 8 |
| 12,800 元退款與消失的核准單 | 摘要合理但金額藏在 JSON 裡、核准率 98%；部署重啟讓待核准單消失並重複退款 | 21 |
| 雙 11 的四十分鐘 | 供應商過載時的重試風暴、殭屍 run 與取消後留下缺結果的 tool call | 24 → 25 |
| 共用 key 與說不清的退款 | 所有 agent 共用一把 ERP 管理者 key、核准欄位可被改寫、模型填寫 `tenant_id` | 33 |
| 週末的「已退款完成」 | prompt 中一行確認指示被刪，金流改成非同步後 agent 對一千九百多位使用者宣稱退款完成，其中三十七筆失敗，而傳統監控全綠 | 34 |
| 試辦第二週的五件事 | 七十張 issue 同時指派、改測試預期值、並行修改同一檔案、無進展迴圈、個人 token 放在 VM 環境變數 | 43 |

### A.10.4 loom 版本與模組

`loom` 只有三個版本號；其他章節一律寫成「給 loom 加上某模組」。模組名稱都用小寫。

| 名稱 | 內容 | 章節 |
|---|---|---|
| `loom` v0.1 | 第 4 章的最小 loop：message 格式、tool schema、dispatch、停止條件與錯誤回填 | 4 |
| `loom` v0.5 | 第 23–25 章重構後的版本：framework 核心抽象、runtime 與 model adapter | 23 → 25 |
| `loom` v1.0 | 第 45 章的完整組裝，隨書套件在 `Agent System Design/code/`；`Agent.version` 是 agent 設定的內容 hash，即 AgentSpec 的版本號 | 45 |
| `loom.a2a`、`loom.agents`、`loom.browser`、`loom.graph`、`loom.retrieval`、`loom.sandbox`、`loom.workflows` | 分別對應 A2A（第 15 章）、multi-agent（第 20 章）、browser agent（第 16 章）、graph runtime（第 19 章）、檢索（第 11 章）、sandbox（第 17 章）、workflow patterns（第 18 章）；v1.0 套件未收錄，第 45 章 45.12 節說明掛接點。第 17 章的 `run_untrusted()` 只是概念版，不是安全邊界 | 16 → 45 |
| `loom.approval` | PolicyEngine、ApprovalDesk、AuditLog、ApprovalMiddleware；只掛在 `wrap_tool`，等待靠 `Interrupt` 與 Session 事件表達 | 21 → 45 |
| `loom.auth` | 授權與稽核 middleware、token exchange；計算有效權限 | 33 → 45 |
| `loom.compaction` | 六段交接筆記、Compactor 與 `check_handoff` | 10 → 45 |
| `loom.compat` | v0.5 時期的相容層（例如狀態別名轉換），在 v1.0 移除 | 23 → 45 |
| `loom.context` | 從 session log 建出 context 視圖（`build_view`）、ContextPolicy 與 ContextMiddleware，寫 `context_cleared`、`context_compacted` 事件 | 9 → 45 |
| `loom.core` | v0.5 起的核心模組：八個核心抽象、事件、Session、RunContext 與參考 Runner | 23 → 45 |
| `loom.durable` | 基於事件日誌的可恢復執行：FileSession（JSONL、compare-and-set、upcaster）與 replay | 22 → 45 |
| `loom.evals` | eval harness：任務、claim、pass@k 與 pass^k、報告；從外面呼叫 Runner，不掛在 Runner 上 | 23 → 27、45 |
| `loom.guardrails` | `Label`（來源 sources 與可讀者 readers）、`ToolSpec`（`capability`、`integrity_args`、`recipient_arg`、`inherits`）；檢查順序為能力 → 機密性 → 完整性，結果為 deny／ask／allow | 23 → 32、45 |
| `loom.mcp` | MCP 風格的 server 與 client、把 MCP tools 橋接進 registry、定義 pin | 14 → 45 |
| `loom.memory` | MemoryStore：`/memories` 虛擬路徑、組織記憶唯讀、TTL 與刪除權 | 12 → 45 |
| `loom.models` | Adapter、錯誤分類、熔斷、FallbackChain、Router 與 CostLedger；重試不在這裡 | 23 → 25 |
| `loom.registry` | ToolRegistry（以 BM25 搜尋）與 RegistryMiddleware，負責延遲載入與 tool search，寫 `tools_loaded` 事件 | 23 → 45 |
| `loom.runtime` | async Runner：串流事件、平行 tool calls、取消與逾時、RetryPolicy、LoopGuard；全書唯一做重試的一層 | 23 → 24 |
| `loom.schema` | structured output 的資料模型、解析與修復迴圈 | 7 |
| `loom.tools` | `@tool`、tool lint 與 IdempotencyStore；tool 帶副作用等級（`effect`）與 `intent_fields` | 5 → 45 |
| `loom.tracing` | 依 OTel GenAI 慣例的 tracer、遮蔽與假名化 | 23 → 29 |

### A.10.5 事件、擴充點與介面名稱

| 名稱 | 類別 | 說明 | 章節 |
|---|---|---|---|
| `before_run`、`wrap_model`、`wrap_tool`、`on_event` | middleware 擴充點 | loom 只有這四個擴充點；`on_event` 只能觀察、不能改變流程；全域政策掛在 Runner 層 middleware，agent 專屬政策宣告在 Agent 上 | 23 → 45 |
| `run_started`、`user_message`、`model_response`、`tool_result`、`handoff`、`guardrail_tripped`、`run_finished` | 核心事件（七種） | 寫進 Session 的持久化事件，是唯一事實來源；`model_response` 帶 `attempts`，`tool_result` 帶 `status` 並依 call 順序寫入，loop guard 觸發時寫 `guardrail_tripped`（`guardrail="loop_guard"`） | 23 → 24、45 |
| `approval_requested`、`tools_loaded`、`context_cleared`、`context_compacted` | 擴充事件（v1.0） | 同樣寫進 Session、有 seq 與版本號；分別記錄核准單 id（等於 intent key）與參數 hash、延遲載入的 tool、被清除的 tool 輸出、compaction 的交接筆記；`to_messages()` 不認得就略過 | 45 |
| `model_delta`、`model_retry`、`tool_started`、`tool_finished`、`run_cancelling`、`committed` | 串流事件 | 不持久化、給 UI 與呼叫端即時消費；`run_cancelling` 表示開始收尾（未完成的 call 記成 cancelled 或 unknown），`committed` 是核心事件寫入 Session 後的通知 | 24 |
| `StopRun`／`Interrupt` | 例外 | middleware 丟 `StopRun` 以結束 run（例如預算用完）；核准等待以 `Interrupt` 表達，不執行、不回填 | 24 → 45 |
| `stream()`：`text_delta`、`stop` | 模型串流介面 | 先送 `text_delta`，最後送帶完整 `ModelResponse` 的 `stop` | 24 → 25 |
| `bluebird.*` 屬性 | span 屬性命名空間 | 業務結果另記於此，不放在 span status：例如 `bluebird.run.status`、`bluebird.claims`、`bluebird.tenant.id`、`bluebird.spec.version` | 29 → 36、42 |
| `Runner(model, middleware, ...)` | runtime 介面 | `start()`／`run(agent, input, session, deps)` 回傳 `RunResult` | 24 → 45 |

核心事件（共七種）寫進 Session，是唯一事實來源；串流事件只給 UI 與呼叫端即時消費、不持久化；擴充事件同樣寫進 Session，但 `to_messages()` 不認得就略過。三者不要混用。

### A.10.6 狀態名稱

| 名稱 | 所屬 | 值與意義 | 章節 |
|---|---|---|---|
| autonomy 等級 | 動作的自主程度 | L0 無 LLM 決策、L1 建議、L2 流程內的 LLM 步驟、L3 監督式 agent（每個寫入都要人核准）、L4 有邊界的自主、L5 目標導向的長時間自主（預算內自主） | 1 → 21、35 |
| RunResult.status | run 的結束狀態 | done（有外部證據的完成）、unverified（宣告完成但無外部證據）、max_steps、max_tokens、budget、loop、blocked（guardrail 或政策擋下）、cancelled、timeout、error、refusal；不使用 succeeded、budget_exceeded 等別名。interrupt／resume 另有兩個非結束狀態：interrupted（暫停等待核准）、ignored（重複的 resume 回呼被忽略） | 4 → 21、24、39 |
| tool_result.status | tool 結果 | ok、error、timeout、cancelled、unknown；「結果未知」是獨立類別，不可直接重試 destructive 動作 | 24 |
| 核准引擎決定 | approval policy engine | auto、approve、deny，以 deny-overrides 合併；未登記的動作預設拒絕 | 21 |
| A2A task 狀態 | A2A | submitted、working、input-required、auth-required、completed、failed、canceled、rejected | 15 |
| coding 任務狀態 | 第 43 章平台 | QUEUED → RUNNING → VERIFYING → PR_OPEN → MERGED 或 CLOSED；另有 FAILED、ESCALATED、CANCELLED；合法轉移寫成資料 | 43 |
