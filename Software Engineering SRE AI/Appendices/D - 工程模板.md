---
title: 工程模板
---

# 附錄 D　工程模板

這份附錄收錄全書出現過的十二種工程 artifact 的空白模板。每一份都先說明什麼時候用、誰寫、誰 review，再給一個可以直接複製的空白模板，最後是 Harbor 的填寫範例。章節中已經有完整範例的，這裡直接指出章節位置，不重寫另一個版本，避免同一份文件出現兩種說法；章節中沒有完整範例的，這裡補上一份和章節內容一致的 Harbor 範例。

模板不是表格作業。第 48 章說過，artifact 的價值在於它是下一站的輸入：design doc 裡的 invariant 會變成測試與 policy，SLO 會變成告警規則，postmortem 的 action items 會變成新的 eval 案例與 CI 檢查。所以每一份模板裡都有「連結」欄位，填寫時要真的連到上一站與下一站的文件。

## D.1 總覽

| # | 模板 | 什麼時候用 | 誰寫 | 誰 review | Harbor 範例 |
|---|---|---|---|---|---|
| 1 | ADR | 重要、難以回復或會被反覆爭論的決策 | Decision owner | 受影響的 owner 與諮詢對象 | 第 7 章 ADR-003、第 48 章 ADR-041；本附錄 ADR-047 |
| 2 | Design doc | 跨團隊、新依賴、金流個資、超過兩週、單向門 | 負責實作的工程師或 owner | 領域專家、受影響團隊、SRE、資安 | 第 17 章多幣別、第 48 章 refund-assistant |
| 3 | PR 描述 | 每一個 PR | 送出 PR 的人（不論程式碼是誰打的） | 熟悉程式的 reviewer 加 code owner | 第 16 章退款分攤、第 48 章 PR #2317 |
| 4 | SLO 文件 | 每一個有使用者的服務 | 服務 owner 與產品 | SRE；產品、開發、SRE 共同同意 | 第 32 章 checkout 欄位表、第 48 章 refund-assistant |
| 5 | Error budget policy | 每一份 SLO 文件 | 服務 owner | 產品、開發、SRE 主管共同簽署 | 第 32 章 v3、第 35 章執行細則；本附錄 refund-assistant |
| 6 | Alert 規則說明卡 | 新增或修改任何 page 等級的告警 | 提出告警的人 | 值班輪值成員與 SLO owner | 本附錄 `RefundReasonCodeDrift` |
| 7 | Runbook | 每一條 page 等級的告警 | 服務的值班團隊 | 另一位值班者；在演練中驗證 | 第 43 章、第 48 章；本附錄 `#drift` 節 |
| 8 | Incident 狀態更新 | 宣告事故後，依嚴重度的固定節奏 | Comms lead（AI 可起草） | IC 確認；對外訊息依規定加審 | 第 44 章雙十一；本附錄 INC-0611 |
| 9 | Postmortem | 符合第 45 章觸發條件的事故與 near miss | Postmortem owner（最好不是 IC） | 資深工程師或 SRE；postmortem review 會議 | 本附錄 INC-0611（因素與行動見第 48 章） |
| 10 | Launch checklist | 任何一題風險分級問題答「是」的上線 | 服務團隊 | Launch 協調人（輪值 SRE）；上線決策者簽核 | 第 46 章直播搶購、第 48 章節錄；本附錄 AI 檢查 |
| 11 | Deprecation 公告 | 淘汰任何有使用者的 API、服務、函式庫 | 舊系統的 owner（提供方） | 受影響團隊代表與核准淘汰的主管 | 第 18 章 `/v1/pay` |
| 12 | Agent policy | 任何 agent 的建立、等級或邊界變更 | Agent owner | Owner 以外的人；高風險加平台與資安 | 附錄 C.8（唯一版本） |

幾條適用於所有模板的規則：放在 repository 中、以 Markdown 撰寫、透過 PR 變更（第 17 章的 docs as code）；每份文件開頭寫明 owner、狀態與下次檢討日期；AI 可以依模板起草，但每一條事實陳述都要能追溯到證據，沒有證據的標記為假設（第 7 章 7.12），不讓 AI 補上看似合理的數字。

## D.2 ADR（Architecture Decision Record）

**什麼時候用**：決策影響多個團隊或多年、難以回復（第 7 章的 one-way door），或同一個問題已經被爭論第二次。一份 ADR 只記一個決策。

**誰寫、誰 review**：Decision owner 撰寫並具名；諮詢對象與受影響服務的 owner review；以 PR 放進 `docs/adr/`，合併即 Accepted。被取代時不刪除，標成 Superseded 並互相連結；部分修訂用 `Amended by`。

```text
ADR-NNN：<用動詞描述決策，例如「採用 X，暫不做 Y」>
狀態：<Proposed／Accepted／Rejected／Superseded by ADR-MMM／Deprecated>（<日期>）
Decision owner：<具名的人>
諮詢：<人與團隊>；spike 由 <人> 執行
關聯：<Supersedes／Amends／Amended by ADR-xxx；相關 design doc、事故>

## 背景
- <當時的問題、限制、規模、時間壓力；組織與商業事實，不只技術>

## 考慮過的選項
1. 維持現狀：<…>
2. <選項，用它最強的版本描述>
3. <選項>

## 決策
採用選項 <N>：<主動語氣，一句話>

## 理由
- <每個被否決的選項輸在哪裡>
- 關鍵假設：(a) <…> (b) <…>

## 後果
- 好：<…>
- 壞：<…>
- 我們接受：<明確承擔的代價>

## 重新評估條件（任一成立即重新檢視）
- <可量測的條件>
- 最晚 <日期> 重新檢視

（若有 AI 參與起草）AI 參與：<哪些段落由 AI 起草；事實已由 <人> 對照 <證據> 核對>
```

**Harbor 範例**：第 7 章 7.8 的 ADR-003（模組化單體）與第 48 章 48.3 的 ADR-041（退款由 refund-gateway 執行）是完整範例。第 48 章 48.13 提到 INC-0611 之後新增了 ADR-047 並修訂 ADR-041，但沒有列出全文；以下依第 48 章的事故與 action items 補上：

```text
ADR-047：知識庫是 agent bundle 的一部分，以不可變快照引用
狀態：Accepted（第 5 年 6 月）
Decision owner：阿凱（客服平台）
諮詢：美華（payments owner）、志明（SRE）、知識平台團隊
關聯：Amends ADR-041；來源 INC-0611 postmortem action items 1、2

## 背景
- refund-assistant 的 agent bundle 以索引名稱 policy-kb 引用知識庫。06-11 18:00 同步 job
  重建索引（v58）並收錄一份草稿政策，agent 的行為在沒有新 artifact、沒有 eval、
  沒有 canary 的情況下改變，約 550 筆退貨被誤判為商品瑕疵（INC-0611）。
- ADR-041 已寫下「規則引擎與知識庫可能不一致」的風險，但沒有對應的機制。
- 另有三個團隊的 AI 功能同樣以索引名稱引用知識庫。

## 考慮過的選項
1. 維持現狀，只修同步 job：只收錄「已核准」狀態的文件。
2. Bundle 以快照版本引用知識庫（例如 policy-kb@v57）；知識庫變更產生新的 bundle 版本，
   走與 prompt 相同的 eval 與 5% canary。
3. 把政策內容全部寫進規則引擎，agent 不再檢索政策文件。

## 決策
採用選項 2，並同時執行選項 1（action item 1，由知識平台負責）。

## 理由
- 選項 1 堵住了這一次的入口，但正式發布卻寫錯的政策、或文件格式改變，
  仍會繞過 eval 與 canary 直接改變 agent 的行為。
- 選項 3 最可預測，但政策文件中大量是要向買家解釋的說明文字，無法全部變成規則；
  規則引擎目前只負責金額與資格（ADR-041）。
- 選項 2 讓「決定 agent 行為的東西」與「要經過變更流程的東西」一致（第 47 章：
  agent 的版本由模型、prompt、工具、retrieval 與 policy 共同決定）。
- 關鍵假設：知識庫更新的頻率讓每次約 40 分鐘的完整 eval 加上 canary 是可接受的成本。

## 後果
- 好：每一次知識庫變更都對應一個 bundle 版本，可以追溯、可以回退；
  INC-0611 中手動把 policy-kb 回退到 v57 的動作，成為標準的 bundle rollback。
- 壞：政策從核准到生效的時間變長；緊急的政策修正需要快速通道。
- 我們接受：政策更新不再「即時生效」。

## 重新評估條件（任一成立即重新檢視）
- 知識庫變更因 eval 或 canary 而延誤，造成對買家的錯誤說明持續超過 1 個工作天
- 最晚第 5 年 12 月 1 日（與 ADR-041 一起檢視）
```

## D.3 Design doc

**什麼時候用**：符合第 17 章任一條件就寫：影響其他團隊或改變對外 API 與資料格式；引入新的儲存系統、資料模型或關鍵依賴；涉及安全、隱私、金流或法規；預計超過兩週；難以回復的決策。中等變更可以只寫一到兩頁的 mini design doc。

**誰寫、誰 review**：負責實作的工程師或服務 owner 撰寫。先給一兩位領域專家看草稿，再發給所有受影響的團隊非同步留言，留言解決不了的爭議才開會。涉及金錢與個資時，資安與 payments owner 必須是 reviewer；需要 SRE 營運的服務，SRE 在設計階段參與（第 46、47 章）。最後由文件開頭列出的 approver 簽核，狀態改為 Approved。

```text
Design Doc：<標題>（v<N>，狀態：Draft／In review／Approved／Implemented／Superseded）
Owner：<人（團隊）>　Reviewers：<人（團隊）>　Approver：<人>
連結：<相關 ADR、PRD、事故、上一版文件>

Context 與 scope
  <現況、為什麼要改、範圍；引用實際資料而不是猜測>

Goals
  - <可驗證的成功標準>
Non-goals
  - <明確不處理的事>

CUJ（若面向使用者）
  <使用者從哪裡開始、到哪裡結束>

Invariants（由程式強制，不寫在 prompt 或文件裡）
  I1 <無論如何都必須成立的條件>

設計概觀
  <一張圖加幾段文字，五分鐘內看懂>

詳細設計
  <API、資料模型、資料流、狀態轉換>

Alternatives considered
  A. <選項> → <否決或暫不採用的理由>

Cross-cutting concerns
  安全與威脅模型：<誰可能怎麼攻擊或誤用；AI 功能須含 prompt injection>
  隱私：<哪些資料、保存多久、誰能看>
  可靠性：<SLO 草案、依賴失效時的行為>
  可觀測性：<metrics、logs、traces>
  容量與成本：<尖峰估算；AI 功能含 token 與配額>
  公平性：<哪些族群可能被系統性地服務得較差，怎麼量>

降級模式
  <由寬到窄的模式、切換方式與生效時間>

Rollout、migration 與 rollback
  <漸進上線的階段與晉升條件；資料怎麼轉；出事怎麼退>

Open questions
  - <需要 reviewer 幫忙判斷的問題>

實作時的差異（Implemented 後補）
```

**Harbor 範例**：第 17 章 17.7 的多幣別 design doc 示範了 context、non-goals、alternatives 與 rollout 的寫法；第 48 章 48.3 的 refund-assistant design doc 摘要示範了 invariants、威脅模型、降級模式與公平性。兩份合起來涵蓋了這份模板的所有段落，這裡不另寫範例。

## D.4 PR 描述（含 AI 生成變更的揭露欄位）

**什麼時候用**：每一個 PR。第一行摘要要能在列表中單獨讀懂。

**誰寫、誰 review**：送出 PR 的人就是作者，不論程式碼由誰或由哪個 agent 產生，作者都要能回答 reviewer 的每一個問題（第 16 章）。一位熟悉這段程式的 reviewer，加上 CODEOWNERS 規定的 owner；agent 不能核准自己或同一個 agent 其他實例開的 PR（第 47 章）。

```text
<一行摘要：做了什麼，而不是「fix bug」>

## 為什麼
<問題、連結的 issue／事故／ADR>

## 做了什麼
- <變更 1>
- <變更 2>

## 沒有做什麼
- <刻意不在這次範圍內的事，以及在哪裡處理>

## 風險與驗證
- 影響範圍：<哪些路徑、哪些使用者>
- 測試：<新增或修改了哪些測試；測試檔案的修改理由>
- 以真實資料驗證：<重放、比對的結果與不一致的方向>
- Rollback：<怎麼退；有無 schema 或資料變更>

## AI 參與（AI 協助範圍）
- 由 AI 產生的部分：<檔案或函式；用了哪個 agent 或工具>
- 作者重寫或修正的部分：<哪些、為什麼>
- 作者如何驗證：<測試、手動檢查、與誰確認語意>
- 被拒絕的 AI 建議：<例如不存在的套件、範圍外的修改>
- 測試與檢查設定是否被 AI 修改：<是／否；若是，逐項說明>
（沒有 AI 參與時寫「無」，不要刪除這一段）

## 請特別看
- <作者自己最不確定的地方，附檔名與行號>
```

「AI 參與」一段的最後兩項來自第 16 章列出的 AI 生成程式碼特有錯誤：削弱測試（修改預期值、刪掉失敗的測試、放寬 assertion）與繞過檢查（新增 suppression、修改 linter 或 CI 設定）。要求作者明確寫「是／否」，比期待 reviewer 自己從 diff 裡找出來可靠。

**Harbor 範例**：第 16 章 16.5 的退款分攤 PR 是不含 AI 參與的完整範例；第 48 章 48.4 的 PR #2317（refund-gateway）是含「AI 參與」一段的完整範例，其中 coding agent 建議的套件 `idem-keys` 被 CI 的依賴 allowlist 擋下，正好對應「被拒絕的 AI 建議」一欄。

## D.5 SLO 文件

**什麼時候用**：每一個有使用者（包括內部使用者）的服務。導入初期先挑一個重要、團隊願意合作的服務跑完一整輪，再推廣（第 32 章）。

**誰寫、誰 review**：服務 owner 與產品經理一起撰寫，SRE review 量測方式與目標；目標代表風險接受程度，由產品與服務 owner 決定，AI 可以草擬候選 SLI，但不能決定目標。每季由產品、開發、SRE 一起檢討。

```text
SLO 文件：<服務>（v<N>，<日期>；下次檢討 <日期>）
Owner：<人（團隊）>　依賴：<上游服務與外部供應商>
CUJ：<使用者從哪裡開始、到哪裡結束>

SLI-1 <名稱>  good：<精確到可以寫成查詢的定義>
              valid：<分母，以及排除的請求>
              量測來源：<量測點與它的盲區>
              SLO：<目標>，<窗口：30 天 rolling／calendar>
SLI-2 <名稱>  <…>

追蹤但不設目標  <會被 Goodhart's law 扭曲的指標>
零容忍（不是 SLO，違反即 page）
               <invariant 與一次都不能發生的事>
理由            <為什麼是這個數字：歷史表現、依賴的可用性、降級路徑>
Error budget policy：<連結>
告警規則：<連結>　Dashboard：<連結>
變更紀錄        v1：<日期與內容>；v2：<日期與改了什麼定義>
```

**Harbor 範例**：第 48 章 48.7 的 refund-assistant SLO 文件是完整範例，示範了 AI 服務的正確性 SLI、「追蹤但不設目標」、零容忍事項與「理由」的寫法；第 32 章 32.8 的 checkout 欄位表示範了量測來源、變更紀錄與下次檢討日期。注意 refund-assistant 的範例中 SLI-3 的量測延遲是 24 小時，這正是 INC-0611 的 contributing factor 之一：填寫時要問「最主要的風險，訊號有多快」。

## D.6 Error budget policy

**什麼時候用**：每一份 SLO 文件都要有對應的 policy，事先寫好預算在不同狀態下要做什麼，事故發生時就不需要臨時爭論。

**誰寫、誰 review**：服務 owner 起草；產品、開發、SRE 主管共同簽署；例外由 policy 中指定的人（Harbor 是工程副總）書面核准。Policy 狀態由 SLO 系統自動判定並發布，部署系統讀取後放行或阻擋（第 35 章）。

```text
<服務> Error Budget Policy（v<N>，<日期>）
適用：<服務>，SLO = <目標與窗口>
簽署：<產品>、<開發 owner>、<SRE>　例外核准：<職稱與人>

狀態（由 SLO 系統判定，不由人宣布）
  HEALTHY    <條件>  → <正常發布、可進行有風險的實驗與遷移>
  BURNING    <例如某週 burn rate > 2，或單一事故用掉 > 20% 預算>
             → <該事故須完成 postmortem；下一次發布須通過 canary 分析>
  EXHAUSTED  <窗口內預算用完>
             → <依下方分類表凍結>

凍結分類（EXHAUSTED 時）
  一律允許        <rollback、關閉 flag、降低流量>
  允許但走 canary  <安全修補、可靠性修復（須連到 postmortem action item）>
  允許需 owner 核准 <資料修正>
  停在安全階段     <進行中的遷移：不進入下一個不可逆階段>
  暫停            <新功能、打開新的 flag>
  暫停或走例外     <純重構、依賴例行升級>

解凍條件（全部滿足）
  - 最近 7 天 SLI ≥ SLO
  - postmortem 的 P0 action items 已完成
  - 服務 owner 與 SRE 共同確認
  解凍後到 30 天預算回正前，視為 BURNING。

例外
  申請須寫明：為什麼不能等、風險評估、降低風險的做法、回復方式。
  寫不出「降低風險的做法」的申請不核准。例外記錄於本 policy 附錄，季度檢討時回顧。

外部因素
  預算主要因依賴耗盡時，仍適用凍結；action items 改為提升對該依賴的容錯能力。

消耗帳本
  每次明顯的消耗記錄日期、事件、類別（程式碼變更／設定變更／依賴／基礎設施／
  流量異常／原因不明）與比例。
```

**Harbor 範例**：第 32 章 32.6 的 checkout policy v3 是條文的完整範例，第 35 章 35.7 補上了狀態判定、凍結分類表、消耗帳本與改良的解凍條件；上面的空白模板就是兩者合併的結果。第 48 章的 refund-assistant 沒有列出 policy 全文，以下依它的 SLO 文件與 runbook 補上。AI 服務的特別之處在於「變更」的範圍更大：模型、prompt、工具定義、規則與知識庫快照的變更，都和程式碼變更一樣受凍結約束（第 32 章 32.11）。

```text
refund-assistant Error Budget Policy（v1，第 5 年 4 月）
適用：refund-assistant，SLI-1 對話可用性 99.5%、SLI-2 回應延遲，30 天 rolling
簽署：Lisa（產品）、阿凱（客服平台）、志明（SRE）　例外核准：Kevin（工程副總）

狀態
  HEALTHY    → 正常發布；bundle 變更依 rollout 計畫走 eval 與 canary
  BURNING    某週 burn rate > 2，或單一事故用掉 > 20% 預算
             → 該事故須完成 postmortem；下一次 bundle 或程式變更須走 5% canary
  EXHAUSTED  → 依下表凍結

凍結分類（EXHAUSTED 時）
  一律允許         rollback 到上一個 bundle；mode 切到 approval／lookup_only／off
  允許但走 canary   安全修補；連到 postmortem action item 的可靠性修復
  允許需 owner 核准  對帳工具的資料修正（payments owner 美華核准）
  暫停             新的原因碼加入自動清單；放寬自動退款上限；換模型或改 prompt
                   （除非是為了修復本次消耗）
  暫停或走例外      純重構、依賴例行升級

解凍條件：最近 7 天 SLI-1、SLI-2 ≥ SLO；P0 action items 完成；阿凱與志明共同確認

不屬於 error budget 的事（另依 SLO 文件的零容忍處理）
  I1–I4 任一被違反、同一 idempotency key 出現兩筆撥款：
  不論預算剩多少，mode 立即切到 off、撤銷 agent 的 refund scope、宣告事故並寫 postmortem

外部因素
  模型供應商故障造成的消耗同樣適用凍結；action items 指向 circuit breaker、
  lookup_only 降級與配額，而不是「等供應商修好」
```

「暫停」一列把「新的原因碼加入自動清單」和「放寬自動退款上限」放在一起，因為它們和第 35 章的「打開新的 flag」是同一種東西：都是引入新行為。反過來，把 mode 切到 `approval` 和「關閉 flag」一樣是回到更保守的狀態，所以一律允許。

## D.7 Alert 規則說明卡

**什麼時候用**：新增或修改任何 page 等級的告警之前。第 34 章規定新增 page 前要回答四個問題：保護哪個 SLO 或哪種不可逆傷害、誰會被叫醒、收到後能做什麼、預期多久響一次。答不出來的，先做成 dashboard。說明卡就是把這四個答案和規則本身放在一起。

**誰寫、誰 review**：提出告警的人撰寫（服務團隊或 SRE）；值班輪值成員與 SLO owner review；規則本身用 `promtool test rules` 寫單元測試，和程式碼一起 review。每週 on-call 交接時檢視上週的每一個 page，每季檢視所有告警的統計。

```text
告警說明卡：<AlertName>
Owner：<人（團隊）>　接收：<team label 與值班輪值>　等級：<page／ticket>
狀態：<提案／影子期／正式／檢討中／已刪除>　規則檔：<路徑>　測試：<路徑>

保護什麼    <哪個 SLO 或哪種不可逆傷害>
條件        <規則的白話描述；長窗口與短窗口>
為什麼是這個等級 <不立刻處理會怎樣；為什麼不能等到早上>
收到後做什麼 runbook：<連結#節>；安全的第一步：<…>
預期頻率    <影子期量到的觸發次數，與其中需要行動的次數>
四把尺      precision：<…>　recall：<…>　detection time：<…>　reset time：<…>
已知誤報    <情境與處理方式>
驗證        <用哪段歷史資料或演練證明它會在預期時間觸發>
相關告警    <同一個 SLO 的其他規則；inhibition 關係>
檢討紀錄    <日期：保留／調整門檻／降級成 ticket／自動化／刪除，與理由>
```

**Harbor 範例**：第 34 章 34.7 的 `CheckoutErrorBudgetFastBurn` 與第 48 章 48.8 的 refund-assistant 規則組是規則本身的範例，但沒有說明卡。以下是 INC-0611 action item 3 新增的漂移告警。第 48 章 48.8 指出原本的規則組「沒有一條關於判斷正確性的告警」，這條規則就是為了補上這個缺口。

```text
告警說明卡：RefundReasonCodeDrift（原因碼占比漂移）
Owner：志明（SRE）　接收：team=cs-platform，refund-assistant primary　等級：page
狀態：影子期（INC-0611 action item 3，期限 06-30）　規則檔：alerts/refund-assistant.yaml

保護什麼    SLI-3 判斷正確性。SLI-3 的每日抽樣延遲約 24 小時，判斷錯誤在這段期間
            不會出現在任何即時訊號上（INC-0611 contributing factor 3）
條件        任一自動原因碼（例如「判為瑕疵」）的占比，2 小時窗口相對過去 7 天基線的
            z 值 > 4
為什麼是 page 判斷錯誤會以穩定速度持續造成金錢損失：INC-0611 約 15 小時誤判約 550 筆，
            平均每小時約 37 筆；等到隔天早上九點的抽樣報告，代價是一整晚
收到後做什麼 runbook：runbooks/refund-assistant.md#drift；安全的第一步：把該原因碼切到
            approval，不需要先知道原因
預期頻率    影子期送到非 page 頻道，記錄觸發次數與需要行動的次數，再決定是否轉正
四把尺      recall：以 06-11 資料重放，18:59 觸發（漂移從 18:05 開始，偵測約 54 分鐘）
            precision 與 reset time：以影子期資料填寫
已知誤報    活動或物流異常時，原因碼分布本來就會改變（例如物流延誤造成「物流遺失」上升）；
            活動前由客服營運在變更時間軸登記，值班者先比對
驗證        以 06-11 資料重放，18:59 觸發（action item 3 的完成證據）
相關告警    RefundAssistantFastBurn／SlowBurn（可用性）、RefundInvariantViolation（零容忍）、
            RefundPolicyDenySpike（可能的注入嘗試，送資安）
```

## D.8 Runbook

**什麼時候用**：每一條 page 等級的告警都必須連結到一份 runbook，沒有 runbook 的告警不能設為 page（第 43 章）。同一個服務的多條告警可以放在同一份 runbook 的不同節。

**誰寫、誰 review**：服務的值班團隊撰寫；另一位值班者 review，並在 Wheel of Misfortune 或 game day 中照著執行一次；值班者發現錯誤時當場修正，或至少寫進交接。Runbook 和程式碼放在一起，用 code review 管理。

```text
# <AlertName 或操作名稱>

意義：<這條告警代表什麼；使用者感受到什麼>

先確認（<N> 分鐘內，全部唯讀）：
  1. 範圍：<依哪些維度切分；在哪個 dashboard>
  2. 起點：<與變更時間軸比對：部署、flag、設定、批次工作、bundle 或知識庫版本>
  3. 依賴：<trace 或依賴 dashboard 看哪裡>

安全的止血動作（依範圍選擇，不需要先知道原因）：
  - <情境> → <動作與指令>；<是否需要核准>
  - <情境> → <動作>

不要做：
  - <會讓情況更糟的動作，與理由（多半來自過去的事故或演練）>

升級：<多少分鐘無法判斷或止血 → 找誰>；<什麼條件 → 宣告 incident>
Owner：<團隊>；最後驗證：<日期與方式（演練名稱）>
```

**Harbor 範例**：第 43 章 43.5 的 `CheckoutLatencyFastBurn` runbook 是完整範例；第 48 章 48.8 的 `runbooks/refund-assistant.md` 節錄示範了 AI 服務的「先判斷是哪一種壞」與「不要做的事」。以下是 D.7 的漂移告警對應的 `#drift` 節，延續同一份 runbook 的寫法：

```text
# RefundReasonCodeDrift（runbooks/refund-assistant.md#drift）

意義：某個自動原因碼的占比在 2 小時內明顯偏離過去 7 天的基線。可能代表 agent 的判斷
      改變了，而 availability 與 latency SLO 仍然是綠的。使用者感受：可能被錯誤地退款
      或錯誤地分配運費，買家多半不會察覺。

先確認（10 分鐘內，全部唯讀）：
  1. 範圍：dashboard「原因碼分布」→ 哪一個原因碼在漂移；集中在特定商品類別、
     活動或買家族群嗎？
  2. 起點：漂移開始的時間，與變更時間軸比對：bundle 版本、知識庫快照版本、
     規則引擎版本、活動上線時間
  3. 抽樣：從漂移開始後的自動退款中抽 20 筆，用 trace 看 agent 檢索到哪些文件 ID

安全的止血動作：
  - 漂移集中在單一原因碼 → 只把該原因碼切到 approval（其他原因碼維持 auto），
    通知客服當班主管調派核准人力（每人每小時約 60 件）
  - 漂移開始時間與 bundle 或知識庫快照變更吻合 → rollback 到上一個 bundle 版本
  - 多個原因碼同時漂移，或無法判斷 → mode 整體切到 approval

不要做：
  - 不要在 production 直接修改 prompt 或知識庫來「修正」判斷（第 3 節的規則同樣適用）
  - 不要因為「沒有 invariant 違反」就判定為誤報：INC-0611 全程沒有 invariant 違反

升級：20 分鐘內無法判斷 → 呼叫 secondary（payments）與 SRE incident commander；
      抽樣中確認有錯誤判斷 → 宣告 incident（第 44 章）
Owner：客服平台；最後驗證：以 06-11 資料重放並由值班者照本節演練一次
```

## D.9 Incident 狀態更新

**什麼時候用**：宣告事故之後，依嚴重度的節奏發布（第 44 章：SEV1 與 SEV2 內部每 30 分鐘一次），以及狀況有重大變化時。每一則都承諾下一次更新的時間。

**誰寫、誰 review**：Comms lead 撰寫；AI scribe 可以依模板起草，但由 comms lead 修改後發布，IC 確認內容和事故文件一致。對外訊息一律由 comms lead 核准發布，涉及金錢或法律責任時加上指定審核者（第 44 章 44.11）。

```text
[SEV<N>] <服務與症狀> — 更新 #<n>（<時間>）
影響：<從何時開始、多少使用者或交易、目前的趨勢；不知道的數字寫「仍在核對」>
已知：<已確認的事實>
未知：<還不知道的事；不給做不到的 ETA>
正在做：<止血與調查的動作>
請大家：<客服、其他團隊、主管各自要做什麼或不要做什麼>
下次更新：<時間>，或狀況有重大變化時。
IC：<人>　Comms：<人>　事故文件：<連結>
```

**Harbor 範例**：第 44 章 44.5 的雙十一 SEV1 更新 #2 是完整範例。以下是第 48 章 INC-0611 宣告後的第一則內部更新，內容只使用 09:30 當下已知的資訊（原因要到 09:41 才查出）：

```text
[SEV2] refund-assistant 退款原因判斷異常 — 更新 #1（06-12 09:30）
影響：06-11 傍晚起，「判為商品瑕疵」的比例明顯上升；今早的抽樣報告 200 筆中 31 筆
      判斷錯誤。受影響筆數與金額仍在核對。沒有任何一筆退款超過訂單金額，
      沒有重複退款（I1–I4 無違反）。
已知：錯誤集中在「瑕疵」原因碼；09:19 起所有退款已改為客服人工核准（approval 模式）。
未知：判斷改變的原因；昨晚以來受影響的確切訂單。
正在做：比對昨晚以來 bundle、知識庫與規則引擎的版本變更；客服主管已調派 6 人
        處理核准佇列。
請大家：客服請依現行流程核准，遇到「描述只是尺寸不合卻判為瑕疵」的案件請駁回並標記；
        客服平台與知識平台暫停一切 bundle 與知識庫變更。
下次更新：10:00，或狀況有重大變化時。
IC：志明　Comms：Lisa　事故文件：（連結）
```

## D.10 Postmortem

**什麼時候用**：符合第 45 章的觸發條件：所有 SEV1、SEV2；單一事故消耗超過 20% 的 30 天預算；任何錯誤扣款、錯誤退款、資料遺失或外洩；由客戶或人工先發現；AI agent 執行了超出預期範圍的動作，即使已被攔下；以及任何人提出的 near miss。SEV3 可以用一頁的輕量版本。

**誰寫、誰 review**：指定一位 postmortem owner，通常是熟悉事故、但不是 IC 的人。Resolved 後 24 小時內發出簡短摘要，5 個工作天內完成初稿，10 個工作天內完成 review 並發布。資深工程師或 SRE review，再在 postmortem review 會議中討論；會議的規則是討論系統，不討論人。

```text
<標題>　<事故編號>　<嚴重度>　狀態：<草稿／review 中／已發布>
作者：<人>　審閱者：<人>

摘要
  <三到五句：發生了什麼、影響多大、最重要的改變是什麼>

影響
  使用者：<…>　金錢：<…>　資料：<…>
  Error budget：<消耗了多少；SLI 有沒有捕捉到這次事故>
  客服與合作夥伴：<…>

關鍵時間點（附來源）
  開始：<時間>　偵測：<時間>　宣告：<時間>　止血：<時間>　解決：<時間>
  開始→偵測：<…>　偵測→止血：<…>

時間線
  <時間>  <事件>（來源：<連結>）；記錄「當時知道什麼」

Contributing factors（列出所有讓事故發生或擴大的條件，不找單一 root cause）
  1. <factor>：<它如何讓事故發生或擴大>

做得好的地方／做得不好的地方／運氣好的地方

AI agent 相關（若有）
  agent 做了什麼：<…>
  依據什麼輸入：<context、檢索到的文件、版本>
  權限邊界在哪：<等級、邊界、gateway 決定>
  哪個 guardrail 有效、哪個缺席：<…>

Action items
  #  類型（預防／緩解／偵測／流程）  控制強度（消除／工程防護／流程／訓練）
     行動  owner  期限  優先順序  驗證方式（怎麼證明完成了）  對應 factor  追蹤連結

其他考慮過但未採用的改進與理由

附錄：dashboard 截圖、查詢、聊天紀錄連結、訪談摘要
```

**Harbor 範例**：第 45 章用雙十一事故示範了時間線、contributing factors 與 action item 品質的寫法。第 48 章 48.11 與 48.12 列出了 INC-0611 的時間線、五個 contributing factors 與七個 action items，但沒有整理成完整的文件。以下把 INC-0611 填進模板；時間線、factors 與 action items 的內容以第 48 章為準，這裡只列出模板中第 48 章沒有直接寫出的部分。

```text
refund-assistant 將「不想要了」誤判為「商品瑕疵」　INC-0611　SEV2　狀態：已發布
作者：阿凱（ops lead）　審閱者：美華（payments）、志明（SRE，IC）、Lisa（產品）

摘要
  06-11 18:00，知識庫同步 job 把一份待法務確認的年中慶退貨政策草稿收進 policy-kb。
  agent 依草稿把約 550 件「不想要了」的退貨判為商品瑕疵，由 Harbor 多負擔約 5.5 萬元
  退貨運費。所有 invariant 都守住，availability 與 latency SLO 全程綠燈，錯誤直到隔天
  09:00 的每日抽樣報告才被發現。最重要的改變：知識庫以快照版本納入 agent bundle
  （ADR-047），並新增原因碼漂移告警。

影響
  使用者：約 550 筆退貨被判為瑕疵；Lisa 與財務決定不向買家追回
  金錢：約 5.5 萬元退貨運費，計入活動成本
  資料：無遺失或外洩
  Error budget：SLI-1、SLI-2 未受影響；SLI-3 有捕捉到，但延遲約 24 小時
  客服：approval 模式期間調派 6 人處理核准佇列

關鍵時間點
  開始：06-11 18:05（「判為瑕疵」占比開始上升）
  偵測：06-12 09:00（每日抽樣報告 page）
  宣告：06-12 09:15
  止血：06-12 09:19（mode 切到 approval）；12:30 止血完成
  開始→偵測：約 14 小時 55 分　偵測→止血：19 分鐘

時間線：見第 48 章 48.11（由 AI scribe 起草、IC 逐條確認）

Contributing factors：見第 48 章 48.12 的五項

做得好的地方
  - I1–I4 一次都沒有被違反；金額由規則引擎計算，誤判只影響運費由誰負擔
  - approval 模式在 4 分鐘內接手，這是容量估算時就選好的降級路徑
  - idempotency key 讓模式切換期間沒有任何一筆退款重複執行
  - IC、ops、comms 分工讓 ops lead 專心查原因
做得不好的地方
  - 將近 15 小時內所有告警都安靜：唯一能看到判斷錯誤的訊號延遲 24 小時
  - 21:30 夜班客服在群組提出異常，沒有人負責回應
運氣好的地方
  - 草稿影響的只是運費；若草稿寫的是「活動期間全額退款不需退貨」，損失會大一個
    數量級，而 I1–I3 依然不會被違反：invariant 只保證每一筆「不離譜」，不保證「正確」

AI agent 相關
  agent 做了什麼：依檢索到的政策文件把原因碼判為「商品瑕疵」，經 gateway 驗證後自動退款
  依據什麼輸入：policy-kb v58 中的草稿文件（trace 中的檢索文件 ID 可追溯）
  權限邊界在哪：refund-intent-auto × prod = L4；每筆 ≤ 1,000 元；沒有每小時總量上限
  有效的 guardrail：I1–I4、單筆上限、idempotency key、approval 降級模式
  缺席的 guardrail：知識庫變更不經 eval 與 canary；沒有每小時自動退款預算；
                    沒有判斷品質的即時訊號

Action items：見第 48 章 48.12 的七項。依第 45 章補上控制強度：
  #1 同步 job 只收錄已核准文件              預防  工程防護
  #2 bundle 以快照引用知識庫、走 eval 與 canary 預防  工程防護
  #3 原因碼占比漂移告警                      偵測  工程防護
  #4 gateway 每小時自動退款預算              緩解  工程防護
  #5 客服後台「這個案件怪怪的」一鍵回報       偵測  流程
  #6 eval 新增 40 題與政策矛盾案例            預防  工程防護
  #7 「瑕疵」原因碼退回核准後執行兩週         流程  流程
```

## D.11 Launch checklist（含 AI 功能額外檢查）

**什麼時候用**：先用第 46 章的六個風險分級問題判斷。全部答「否」的低風險 launch 只需確認 rollback 與監控就緒；任何一題答「是」，就要填完整的 checklist。

**誰寫、誰 review**：服務團隊填寫，每一題附證據而不只是打勾；launch 協調人（Harbor 由每季輪值的一位 SRE 擔任）review；上線決策者簽核。缺項可以上線，但要寫成正式的例外：具名的承擔人、補償措施與完成期限。每次 postmortem 發現「本來可以在上線前發現」的問題，就回寫一題。

```text
Launch checklist：<功能>（<日期>）
服務團隊：<人>　Launch 協調人：<人>　上線決策者：<人>　簽核：<人>

風險分級（任一答「是」即需完整 checklist）
  [ ] 任何服務流量增加超過 10%？
  [ ] 新增對外部服務或其他團隊服務的依賴？
  [ ] 涉及金流、個資或權限？
  [ ] 修改資料格式或做資料遷移？
  [ ] 綁定對外公告或行銷活動的時間？
  [ ] 包含 AI 模型做出的決策或動作？（是 → 填寫 AI 額外檢查）

核心檢查（每題附證據）
  容量      預估尖峰多少？依據？load test 測到多少？降級路徑本身的容量？
  相依      依賴哪些服務？它們知道嗎？撐得住嗎？每個依賴失效時會怎樣？
  Rollback  怎麼關掉？要多久（實測）？資料怎麼辦？
  監控      SLO、告警、dashboard、runbook 是否就緒並演練過？誰會在幾分鐘內收到通知？
  Client 行為 新版 client 是否會同步發出大量請求？重試是否有 backoff 與 jitter？
  人        值班表、secondary、需要的人工支援是否確認？

AI 功能額外檢查（每題附證據）
  Eval gate   代表性離線 eval、上線門檻、對抗性與分層案例
  Guardrails  哪些規則由確定性的程式強制，而不是交給模型
  Kill switch 怎麼在一分鐘內停掉 agent 的動作能力而不影響其他功能（實測時間）
  Fallback    模型供應商失效或超時時，使用者看到什麼
  品質監控    上線後怎麼知道品質下降；訊號延遲多久
  成本上限    單次互動與每日的上限；超過時怎麼辦
  稽核與追溯  每一個動作能否追溯到對話、模型版本、prompt 版本、知識庫版本與 policy 決定
  漸進授權    動作能力是否分階段開放（附錄 C 的等級與晉升條件）
  變更管線    模型、prompt、工具、知識庫的變更是否走同一條 eval 與 canary 管線

例外與已知風險
  項目：<…>　承擔人：<具名>　補償措施：<…>　完成期限：<…>
```

**Harbor 範例**：第 46 章 46.6 的直播搶購是核心檢查的完整範例，第 48 章 48.10 是 refund-assistant 的 checklist 節錄。以下依第 48 章的 artifact 填寫 refund-assistant 的 AI 額外檢查；最後一列把第 48 章中阿凱向 Kevin 口頭說明的已知弱點，依第 46 章的做法寫成正式例外。

| 檢查 | refund-assistant 的證據（依第 48 章） |
|---|---|
| Eval gate | 一般案例 600 題 × 5 次，通過率 ≥ 95% 且比上一版退步 ≤ 1 個百分點；對抗性案例 120 題，每題 5 次全部通過；依書寫流暢度與語言分層，各層差距 ≤ 3 個百分點；eval 報告 v12 |
| Guardrails | I1–I4 由 refund-gateway 強制，gateway 有 property test；agent 只能呼叫 `propose_refund`；單次對話 ≤ 40,000 tokens、≤ 15 次工具呼叫、≤ 10 分鐘 |
| Kill switch | `refund_assistant.mode`：auto → approval → lookup_only → off；game day 實測 4 分鐘（app 端快取 flag），修正後重測 25 秒 |
| Fallback | 每輪對話 8 秒 deadline；模型供應商連續失敗時 circuit breaker 切到 lookup_only；知識庫檢索失敗時只回答「目前無法確認政策，已為您轉人工」 |
| 品質監控 | SLI-3：每日抽樣 200 筆人工判定，次日 09:00 產出；`RefundPolicyDenySpike` 送資安 |
| 成本上限 | 單次對話上限如上；`RefundAssistantTokenOverspend`：預估當日用量 > 1.2 倍預算即開 ticket |
| 稽核與追溯 | Gateway 的 audit log 記錄 intent、決策與規則版本，不含對話全文；trace 帶 bundle 版本與知識庫檢索結果 ID |
| 漸進授權 | Rollout 階段 0（gateway shadow 4 週）→ 2（agent shadow 2 週）→ 3（核准後執行 2 週）→ 4（1% → 5% → 25% → 100%，每階段至少 48 小時並涵蓋一個晚間尖峰） |
| 變更管線 | 模型、prompt、工具定義、規則的變更觸發完整 eval（約 40 分鐘）；知識庫以索引名稱引用，**不在**管線內（INC-0611 後由 ADR-047 修正） |
| 例外與已知風險 | 項目：判斷正確性的唯一訊號延遲約 24 小時。承擔人：阿凱（上線決策者），Kevin 簽核。補償措施：每筆自動退款 ≤ 1,000 元；I1–I4 違反五分鐘內 page。完成期限：7 月 1 日的 SLO 檢討 |

「變更管線」與「例外」兩列是事後回看最有價值的地方。如果上線前就把「知識庫不在管線內」寫成一項需要承擔人的例外，INC-0611 的 contributing factor 2 很可能在 review 時就被提出。這也是 checklist 要求「附證據」而不是打勾的原因：證據寫不出來的地方，就是風險所在。

## D.12 Deprecation 公告

**什麼時候用**：第 18 章淘汰流程的第 ② 步「宣布」。公告要讓每個使用者讀完就知道：發生什麼事、為什麼、對我有什麼影響、我要做什麼、什麼時候之前、遇到問題找誰。公告之前，替代方案必須已經就緒，淘汰決策寫成 ADR。

**誰寫、誰 review**：舊系統的 owner（提供方）撰寫，因為遷移的成本應該盡量由提供方承擔；受影響團隊的代表 review 時程是否可行；核准淘汰的主管簽核，並指定例外的核准人。

```text
主旨：[行動需要] <舊介面> 將於 <日期> 關閉，請遷移至 <新介面>

為什麼：<淘汰的理由；外部的截止日>
誰受影響：<哪些呼叫者>
           查詢方式：<使用量儀表板、client id 查詢>
要做什麼：<遷移指南連結>；<提供方會直接送 PR 的範圍>
時程：
  <日期>  公告；<封住入口：停止接受新的使用者>
  <日期>  回應加上 Sunset／Deprecation header；<第一次 brownout>
  <日期>  <強化強制手段，例如提高 client 最低版本、延長 brownout>
  <日期>  <回傳 410 Gone>
例外：<申請期限>；最長延至 <日期>（早於外部截止日）；需 <具名的人> 核准
支援：<頻道>；<office hours>
回復：關閉後 <期間> 內保留快速回復的能力
```

**Harbor 範例**：第 18 章 18.8 的 `/v1/pay` 淘汰公告是完整範例，示範了逐步加強的里程碑、自助查詢是否受影響的方法，以及早於金流商外部截止日的例外上限。第 48 章的 ADR-041 背景中「舊的 /v1/pay 已依第 18 章的流程淘汰」，就是這份公告走完的結果。

## D.13 Agent policy

**什麼時候用**：建立任何 agent 時；以及任何 workflow 的等級、邊界、工具、降級條件的變更。Agent policy 是 tool gateway 的輸入，沒有 policy 的 agent 在 gateway 的第一道檢查就會被拒絕（第 47 章 47.10 的未登記 agent）。

**誰寫、誰 review**：Agent owner 撰寫並申請；review 必須由 owner 以外的人進行（第 47 章的職責分離）；風險分級為高的 agent（production 寫入、金錢、個資），加上平台團隊與資安審查，並經過 agent readiness review。等級升級由 owner 申請、指定的審查者核准；agent 自己不能修改 policy。

**模板與範例**：空白範本、refund-assistant 的完整範例與 SRE 維運 agent 的節錄都在附錄 C.8。為了避免兩份範本隨時間分歧，本附錄不重複全文。Review 一份 agent policy 的 PR 時，至少問以下問題：

- 每一個 workflow 都同時寫了環境嗎？有沒有任何一格的等級高於它在其他環境的等級，卻沒有理由？
- L4 的每一個邊界都是 gateway 能檢查的數字嗎？還是只是一句描述？
- 單向門的動作，invariant 是否寫在工具層，而不是 prompt 裡？
- `version_bundle` 是否包含知識庫，而且是不可變的快照？
- 降級條件是否包含版本變更、事故、否決比例上升與 owner 缺席四項？
- Kill switch 的生效時間是實測值，還是宣稱值？
- 稽核是否記錄被拒絕的請求？個資是否預設不進 log？
- 這次變更是否讓 agent 碰到 AI 政策中「永遠留給人」的決定？
