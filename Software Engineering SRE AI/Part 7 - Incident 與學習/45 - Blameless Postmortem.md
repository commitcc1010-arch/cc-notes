---
chapter: 45
title: Blameless Postmortem、Outage Tracking 與 Action Quality
part: 7
---

# 第 45 章　Blameless Postmortem、Outage Tracking 與 Action Quality

> [!abstract] 本章地圖
> **核心問題**：事故結束之後，怎麼讓組織真正學到東西，而不是找一個人負責、寫一份沒人讀的報告、列一串永遠不會完成的改進事項？
>
> **你會學到**：
> - 判斷哪些事故需要 postmortem，以及誰負責、多久內完成
> - 分辨 blameless 與「沒有人負責」，用前瞻式的 accountability 取代追究
> - 從證據重建時間線，記錄「當時的人知道什麼」，避開事後諸葛
> - 用 contributing factors 分析事故，理解 5 whys 與單一 root cause 的限制
> - 寫出可驗證、有 owner、真正降低風險的 action items，並追蹤到關閉
> - 跨多個事故找出系統性主題，並把學習分享給整個組織
>
> **前置知識**：第 9 章（psychological safety）、第 32 章（error budget policy）、第 44 章（incident command 與雙十一事故）
>
> **對應原書**：SRE 第 15 章〈Postmortem Culture: Learning from Failure〉、第 16 章〈Tracking Outages〉；SRE Workbook 第 10 章〈Postmortem Culture: Learning from Failure〉

## 45.1 故事：第一版事故報告寫著「根因：人為疏失」

雙十一事故（第 44 章，編號 INC-1111）在 11 月 11 日上午宣告結束。這是同一個晚上的第二個 SEV1：兩小時前，inventory 資料庫的 failover 才讓整個網站倒了半個多小時（第 39 章，INC-1110）。當天下午，執行長要求「明天之前給我一份報告，說清楚是誰的問題」。工程經理 Kevin 熬夜寫了一頁，標題是「1111 結帳事故報告」，核心段落只有三句：

> 根因：payments 團隊於活動前夕部署未經完整壓測的 v2.31，屬人為疏失。事故期間另有工程師未經協調擅自擴容，擴大影響。改善措施：大促期間禁止部署；相關人員再教育；所有變更須經主管核准。

這份報告在事實上沒有錯，但它讓 Harbor 什麼都學不到。小林讀完之後在私訊裡跟美華說：「下次我看到問題，大概不會再主動 rollback 了。」柏翰在週會上沉默了一整個小時。更重要的是，報告裡完全沒有提到：v2.31 的 canary 為什麼沒有發現問題、為什麼重送會造成重複扣款、為什麼 AI 客服送出的兩百多筆退款申請會在十幾分鐘內被整批核准、為什麼從 page 到宣告花了十四分鐘、為什麼同一位值班者在兩小時內接連處理兩個 SEV1 卻沒有人換手、為什麼行銷推播的時間沒有出現在值班行事曆上。

SRE 團隊負責人志明看完報告，去找 Kevin 談了一個小時。志明的論點很簡單：「如果我們把這次的原因寫成『小林不夠小心』，那下次換一個人、換一個服務，一樣會發生。小林當天做的每一個決定，在小林當時知道的資訊下都是合理的。我們要找的是：是什麼讓合理的決定導致了這麼大的傷害？」Kevin 同意了，並且做了一件事後被大家記得很久的事：在全公司頻道收回那份報告，宣布由志明主持正式的 postmortem，並且承諾「這份 postmortem 不會被用來評估任何人的績效」。

兩週後完成的 postmortem 有十一頁，列出十個 contributing factors 和十四個 action items。三個月後回顧時，其中最重要的幾項已經改變了 Harbor 的系統。這一章就用這份 postmortem 當主線，說明一份好的 postmortem 怎麼寫、為什麼 blameless 不等於沒有責任、action item 怎樣才算有品質，以及如何從一年份的事故中看出單一事故看不到的模式。

## 45.2 Postmortem 是什麼、什麼時候要寫

### 定義

**Postmortem**（事後檢討，也常叫 incident review 或 retrospective）是一份書面紀錄，內容包括事故的影響、經過、為什麼會發生、處理過程中什麼有效什麼無效，以及接下來要做什麼來降低再發生的機率或影響。SRE 原書強調它是一份**書面**紀錄：口頭檢討會在幾週內被遺忘，書面紀錄才能被搜尋、被引用、被新人閱讀，並在下一次類似事故時被找出來。

Postmortem 的目標不是「結案」，而是**改變系統與組織的理解**。一份成功的 postmortem 讀完之後，讀者對系統如何運作、如何失敗的認識會更新，而且有具體的改變被排進工作計畫。

### 觸發條件

不是每個問題都需要 postmortem，寫 postmortem 本身也有成本。觸發條件要事先寫好，避免事後才爭論「這次要不要寫」。SRE 原書列出的常見條件包括：使用者可見的停機或品質下降超過某個門檻；任何資料遺失；值班者必須介入（例如 rollback、切換流量）；解決時間超過某個門檻；監控沒有發現、而是由人或客戶發現的問題。另外，任何利害關係人都可以要求為某個事件寫 postmortem。

Harbor 的版本把這些條件和既有的機制連結起來：

| 條件 | Harbor 的門檻 | 連結 |
|---|---|---|
| 嚴重度 | 所有 SEV1、SEV2 | 第 44 章的嚴重度表 |
| Error budget | 單一事故消耗超過 20% 的 30 天預算 | 第 32 章的 error budget policy |
| 金錢與資料 | 任何錯誤扣款、錯誤退款、資料遺失或外洩，不論規模 | 不能用比例衡量的傷害 |
| 偵測失敗 | 由客戶或人工先發現，而不是告警 | 監控本身需要被檢討 |
| AI agent | AI agent 執行了超出預期範圍的動作，即使已被攔下 | 第 47 章的 agent 授權 |
| Near miss | 差一點就造成上述影響的事件，由值班者或任何人提出 | 便宜的學習機會 |

最後一列值得特別說明。**Near miss**（險些發生的事故）是指防線剛好擋住、或者運氣好沒有造成傷害的事件。例如一個錯誤的設定在推到 5% 流量時就被 canary 攔下。它的學習價值常常和真正的事故差不多，代價卻低得多，因為沒有使用者受傷，大家也比較願意坦白討論。

### 誰寫、多久完成

Postmortem 需要一位**負責人**（owner），負責收集資料、召集討論、撰寫初稿、推動 review。負責人通常是熟悉事故經過的人，但最好不是當時的 IC，這樣 IC 可以作為受訪者提供觀點。負責人不是「被追究的人」，而是「組織學習的主持人」。

時間上，Harbor 的規則是：事故 resolved 後 24 小時內發出簡短摘要；5 個工作天內完成初稿；10 個工作天內完成 review 並發布。拖太久，細節會被遺忘，聊天紀錄與監控資料可能已經過了保存期限；太急，又沒有時間做深入的分析。雙十一的 postmortem 因為規模大，Kevin 核准延長到兩週。

## 45.3 Blameless 與 accountability

### 為什麼責怪會讓組織變笨

Kevin 的第一版報告是一種很自然的反應：事情出錯了，找出犯錯的人，要求他們改進。這個做法的問題不在於它不公平（雖然它常常不公平），而在於它**會讓組織失去資訊**。

當人們預期事故後會被追究，他們的理性反應是：少說一點、晚一點說、把自己做過的事說得模糊一點。小林的那句「下次大概不會再主動 rollback 了」就是例子：責怪讓下一次事故的回應變慢。更深的傷害是，事故中最有價值的資訊（「我當時為什麼這樣判斷」「我看到什麼、沒看到什麼」「這個工具在那個時候給了我什麼誤導」）只存在於當事人的腦中。責怪的文化會讓這些資訊永遠不會被說出來。

第 9 章談過心理安全如何讓壞消息提早出現。Postmortem 是心理安全最直接受考驗的地方：如果一份 postmortem 讓某個人在全公司面前難堪，接下來一年的所有 postmortem 都會變得更淺。

### 事後的偏誤

除了文化，責怪還常常建立在錯誤的推理上。事後回顧事故時，有兩種偏誤特別常見：

**後見之明偏誤**（hindsight bias）：知道結果之後，會覺得結果「早就很明顯」。事後看，v2.31 把重送次數從 2 次改成 4 次，顯然會在 gateway 變慢時放大流量；但在部署當下，這個改動的目的是「讓偶發的網路抖動不會造成付款失敗」，而且 code review 與 canary 都通過了。

**結果偏誤**（outcome bias）：用結果的好壞判斷決策的好壞。柏翰的擴容如果剛好讓情況變好，大家會說「反應很快」；因為它讓 gateway 的 429 增加，大家就說「擅自操作」。同一個決策，判斷依據應該是「以當時的資訊，這是不是合理的選擇」，而不是運氣。

Blameless postmortem 的核心問題因此不是「誰做錯了」，而是「**為什麼這些行動在當時看起來是合理的？**」這個觀點有時被稱為 local rationality（局部理性）：人們通常是根據自己當下看到的資訊、目標與壓力，做出合理的判斷。如果合理的判斷導致了壞結果，問題通常在於他們看到的資訊、可用的工具或系統的設計。

### Blameless 不是沒有人負責

最常見的誤解是：blameless 就是「沒有人要負責」。實際上，blameless 改變的是**責任的方向**：

| | 回溯式的責怪 | 前瞻式的 accountability |
|---|---|---|
| 核心問題 | 誰造成了這件事？ | 誰負責讓這件事不再以同樣方式發生？ |
| 結論形式 | 某人要更小心、受到處分 | 具名的 action item owner、期限、驗證方式 |
| 對當事人 | 要求解釋與道歉 | 邀請提供第一手資訊，常常也是最好的 action owner |
| 對組織 | 問題被歸到個人，系統不變 | 系統、流程、工具被改變 |
| 結果 | 資訊變少，下次回應變慢 | 資訊變多，下次防線更多 |

在 Harbor 的 postmortem 裡，小林是 A1（補上 idempotency key）的 owner；柏翰是 A7 的 owner：在各團隊共用的擴容 runbook 加入「先確認下游上限」的步驟，並讓擴容工具顯示下游配額的使用率。他們最了解問題，也最有動力讓它不再發生。這是前瞻式責任最典型的樣子：當事人不是被處罰的對象，而是解決方案的一部分。

Blameless 也有界線。如果有人蓄意破壞、或者明知風險卻刻意繞過安全機制，這屬於另一套人事或安全流程，不在 postmortem 裡處理。業界常引用的 just culture 觀點，會區分無心的失誤、低估風險的冒險行為，以及明知故犯的魯莽行為，對應不同的處理方式。但絕大多數事故中的行動屬於前兩種，而它們的對策幾乎都是改變系統，而不是改變人。

### 語言的改寫

Blameless 最具體的實踐是**用詞**。同一件事可以有完全不同的寫法：

| 帶有責怪的寫法 | Blameless 的寫法 |
|---|---|
| 小林未經壓測就部署 v2.31 | v2.31 通過了 code review 與 30 分鐘 canary；當時的流程不要求針對慢依賴的壓測，canary 也無法模擬 gateway 變慢 |
| 柏翰擅自擴容，擴大影響 | 00:11 payments 的 CPU 偏高，擴容是 runbook 中列出的常見手段；柏翰是當晚的待命支援，平常在 search 團隊，那裡 CPU 偏高時擴容幾乎總是對的；當時沒有任何儀表板顯示 gateway 的流量上限，擴容讓併發連線增加為三倍 |
| 志明延誤宣告 | 從 page 到宣告花了 14 分鐘；志明從 22:03 起已連續處理 inventory 事故，沒有預先安排的換手；當時的 SEV1 定義是「全站無法使用」，兩小時前的全站中斷明確符合，18% 的失敗率則不明顯符合任何等級 |
| 行銷沒有通知值班團隊 | 推播排程存在行銷系統中，沒有任何流程把它同步到值班行事曆 |

右欄並沒有隱藏任何事實，誰在幾點做了什麼都還在。差別是它把焦點從「人的缺點」移到「系統讓這個行動看起來合理的條件」，而後者才是可以修改的東西。

> [!warning] 常見誤解
> 「Blameless 就是不寫名字。」不一定。很多組織在 postmortem 中仍然寫出誰做了什麼，因為事故後要訪談當事人、action item 也要有具名 owner。重點不是匿名，而是描述行動時附上當時的情境與資訊，並且不把個人行為當作結論。有些組織選擇用角色代替名字（「payments 值班者」），兩種做法都可以，前提是文化上確實不追究。

## 45.4 時間線：從記憶到證據

### 為什麼時間線是基礎

Postmortem 的分析品質，取決於時間線的品質。時間線回答的是「發生了什麼、按什麼順序」，它是所有後續分析的事實基礎。如果時間線是憑記憶寫的，就會充滿錯誤：人在壓力下對時間的感知很不可靠，而且每個人只記得自己看到的部分。

好的時間線來自**證據**：第 44 章的事故文件與 scribe 記錄、聊天頻道的時間戳、部署系統的紀錄、告警系統的紀錄、監控指標的變化點、status page 的發布紀錄、AI agent 的工具呼叫紀錄。每一筆都要附來源，讓讀者能自己驗證。

### 雙十一的時間線（節錄）

| 時間 | 事件 | 來源 |
|---|---|---|
| 11/10 18:00 | payments v2.31 開始部署，canary 5% 流量 | 部署紀錄 |
| 18:30 | Canary 分析通過，推到 100% | 部署紀錄、canary 報告 |
| 22:03–22:40 | inventory DB failover 引發重試放大，22:06 起全站不可用（INC-1110，第 39 章）；志明全程處理 | INC-1110 事故文件 |
| 23:59:30 | 行銷推播送出，對象約 210 萬人 | 行銷系統紀錄 |
| 00:01 | Gateway p99 延遲從 0.4 秒升到 3 秒以上 | Gateway client 指標 |
| 00:03 | Checkout 失敗率 18%；快速燒預算告警觸發 | 告警系統 |
| 00:04 | 志明確認 page；將 gateway timeout 從 3 秒調到 15 秒 | Pager、設定變更紀錄 |
| 00:11 | 小林開始 rollback v2.31；柏翰將 payments 從 40 擴到 120 個 pod | 部署紀錄 |
| 00:12 | AI 客服開始依使用者描述大量送出退款申請；客服開始整批核准 | Agent 工具呼叫紀錄、客服後台紀錄 |
| 00:13 | Gateway 429 比例從 2% 升到 31% | Gateway client 指標 |
| 00:16 | 客服主管回報重複扣款，以及 AI 退款申請已被整批核准 | 客服頻道 |
| 00:18 | 志明宣告 SEV1，請美華擔任 IC | 事故頻道 |
| 00:22 | IC 凍結所有非事故變更 | 事故文件決策紀錄 |
| 00:23 | Timeout 調回 3 秒 | 設定變更紀錄 |
| 00:26 | IC 暫停 AI 客服退款申請工具與批次核准（暫停前共 212 筆申請已被核准並退款） | 事故文件、agent 與客服後台紀錄 |
| 00:27 | Pod 縮回 60 個 | 部署紀錄 |
| 00:30 | 第一則 status page 公告 | Status page 紀錄 |
| 00:34 | 啟用結帳排隊，gateway 交易上限 450 TPS | 設定變更紀錄 |
| 00:41 | 確認重複扣款來自 v2.31 的一鍵付款重送路徑 | 事故文件 |
| 00:52 | 失敗率降到 0.5% 以下，宣告 mitigated | 監控、事故文件 |
| 02:00 | IC 交接給俊宇，ops lead 交接給小林 | 事故頻道 |
| 03:40 | Gateway 延遲恢復正常 | Gateway client 指標 |
| 04:30 | 排隊機制逐步放寬後關閉 | 設定變更紀錄 |
| 10:30 | 1,284 筆重複扣款退款核對完成，宣告 resolved | 對帳報告、事故文件 |

### 記錄「當時知道什麼」

時間線不只記錄行動，也要記錄**當時的人看到什麼、相信什麼**。例如在 00:04 那一列，postmortem 補充了志明當時的判斷：「儀表板顯示大量 gateway timeout，推測是 timeout 設定太短，導致原本會成功的交易被提早放棄。」這個推測後來被證明是錯的（調長 timeout 讓 worker 被佔住更久），但它在當時的資訊下是合理的。

這類補充通常要靠**訪談**取得。Postmortem 負責人在初稿完成前，會分別和關鍵參與者談十五到三十分鐘，問的問題是開放式的：「你在那個時間點看到什麼？」「你那時候最擔心什麼？」「有什麼資訊是你希望當時就有的？」「哪個工具或儀表板在那時候幫上忙，哪個讓你誤會？」這些問題不問「為什麼你沒有……」，因為那種問法本身就帶著後見之明。

### 從時間線算出關鍵間隔

時間線也讓我們算出幾個關鍵的時間間隔，這些間隔後面在跨事故分析時會用到：

```text
影響開始 ──▶ 偵測 ──▶ 宣告 ──▶ 止血 ──▶ 解決
  00:01     00:04    00:18    00:52    10:30
     └─ 3 分 ─┘└─ 14 分 ─┘└─ 34 分 ─┘
     └──────────── 51 分（time to mitigate）────┘
```

**Time to detect**（從影響開始到被發現）3 分鐘，代表第 34 章的 burn rate 告警運作良好。**Time to declare**（從發現到宣告）14 分鐘，是這次最明顯的弱點。**Time to mitigate**（從影響開始到止血）51 分鐘，其中三分之一的時間花在宣告之前的混亂裡。把時間拆開看，比只看一個總時長有用得多：它直接指出哪一段需要改善。

### 影響的量化

時間線之後，postmortem 要把影響寫清楚。雙十一事故的影響段落如下：

```text
影響期間：11/11 00:01–00:52（止血），至 10:30 完成補救
結帳：約 54 萬次有效付款嘗試中，約 6.1 萬次失敗（約 11%）
Error budget：11 月 checkout 預計約 8,000 萬次有效嘗試，99.9% SLO 的預算約 8 萬次
             本次消耗約 6.1 萬次，約為整月預算的 76%
             加上同晚 INC-1110 的約 25 萬次（依 4 倍流量粗估），當晚合計約為整月預算的 3.9 倍
金錢：1,284 筆訂單被重複扣款，已於 10:30 前全數退回
      AI 客服送出、經客服整批核准的退款 212 筆，其中 37 筆對應的訂單並未被重複扣款（實為授權圈存）
客服：當日進線量約為平日的 4 倍
```

Error budget 的數字直接觸發了第 32 章 policy：INC-1111 單獨就用掉超過 20% 的預算，觸發第 2 條，必須完成 postmortem；加上 INC-1110，預算已經耗盡，觸發第 3 條：暫停非緊急功能發布，並有開發工程師投入可靠性工作，直到 postmortem 的 P0 action items 完成。37 筆錯誤退款的處理方式（不向使用者追回）則是 Kevin 與財務主管做的業務決定，也記錄在 postmortem 中，因為它是事故成本的一部分。

## 45.5 Contributing factors：為什麼沒有單一 root cause

### 5 whys 的誘惑與限制

**5 whys**（五個為什麼）是一個流行的根因分析方法：從問題出發，連續問「為什麼」，直到找到根本原因。用在雙十一事故上，可能長這樣：

```text
為什麼使用者被重複扣款？      → 因為 payments 在 gateway 逾時後重送了授權請求
為什麼重送會造成重複扣款？    → 因為一鍵付款路徑沒有帶 idempotency key
為什麼沒有帶 idempotency key？→ 因為新路徑沒有沿用舊路徑的 client 封裝
為什麼沒有沿用？              → 因為開發時沒注意到
為什麼沒注意到？              → 因為工程師不夠小心
根因：人為疏失
```

這個鏈條的每一步都沒有錯，結論卻幾乎沒有用。5 whys 有幾個結構性的限制：

1. **它是一條線，事故是一張網**。雙十一事故需要好幾個條件同時成立：gateway 變慢、重送次數增加、沒有 idempotency key、canary 看不到慢依賴、推播比預期集中、宣告延遲、AI 退款申請沒有總量限制。任何一個條件不成立，事故都會小很多。一條「為什麼」的鏈只能抓到其中一條路徑。
2. **它停在哪裡，取決於誰在問**。問到「工程師不夠小心」就停的人，會得到「再教育」的結論；問到「為什麼 code review 沒發現」的人，會得到「review checklist」的結論；問到「為什麼共用的 client library 沒有強制 idempotency」的人，會得到「讓錯誤不可能發生」的結論。5 whys 本身不會告訴你哪一條比較好。
3. **它很容易停在人身上**。人是鏈條上最容易被看到的一環，所以「為什麼」常常在問到某個人的時候就停了。
4. **它只看原因，不看應變**。宣告延遲、擴容造成的放大、溝通真空，都不是「事故的原因」，卻大幅影響了事故的規模。

5 whys 並非完全沒用：作為一個讓人「多問一層」的習慣，它比只看表面好。但它不適合作為大型事故的主要分析架構。

### 瑞士起司模型

另一個常用來理解事故的模型是 **Swiss cheese model**（瑞士起司模型），由心理學家 James Reason 提出：系統有多層防線，每一層都像一片有洞的起司，洞是防線的弱點。單一的洞不會造成事故，因為下一層會擋住；事故發生在多層的洞剛好對齊的時候。

```text
  危害                                                          傷害
 （gateway   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐   （重複扣款、
   變慢）     │ 重試  │  │ 冪等  │  │canary│  │ 偵測  │  │ 應變  │    11% 失敗）
  ─────────▶ │ 上限  ○──▶ 保護  ○──▶ 驗證  ○──▶ 告警  │  │ 指揮  ○──▶
             │      │  │      │  │      │  │  ●   │  │      │
             └──────┘  └──────┘  └──────┘  └──────┘  └──────┘
              4 次重送   新路徑無    看不到     3 分鐘     14 分鐘
              無 budget  key        慢依賴     就發現 ✓   才宣告
```

圖中的 ○ 是對齊的洞，● 是有效的防線。危害（gateway 變慢）本身不是 Harbor 能控制的，但它穿過了重試上限、冪等保護、canary 驗證三層防線，在應變階段又因為宣告延遲而擴大。告警這一層其實有效：3 分鐘就發現了。這張圖帶來的思考方式是：**不要問「哪一個是 root cause」，而要問「每一層防線為什麼沒擋住，哪幾層值得補強」**。

### Harbor 的 contributing factors

雙十一 postmortem 把 contributing factors 分成幾類，每一項都寫清楚「它如何讓事故發生或變大」：

| 類別 | Contributing factor | 它的作用 |
|---|---|---|
| 觸發 | 外部 gateway 在雙十一流量下延遲上升 | 危害的起點；不在 Harbor 控制內，但可預期 |
| 放大 | v2.31 把 payments→gateway 的嘗試次數從 2 次改為 4 次，且不受 checkout 的 8 秒 deadline 限制 | checkout 對 payments 本身最多嘗試 2 次，所以每次點擊最多產生 2×4＝8 次 gateway 呼叫（原本 2×2＝4 次）；checkout 放棄後 payments 仍在重送（第 39 章） |
| 放大 | 一鍵付款路徑沒有 idempotency key | 逾時後的重送造成 1,284 筆重複扣款（第 41 章） |
| 驗證盲點 | Canary 在低流量、gateway 正常時進行；雙十一前的 load test 用固定 200 ms 的 gateway stub | 沒有任何驗證步驟會讓「慢依賴＋更多重送」出現 |
| 需求 | 推播在 23:59:30 一次送給 210 萬人，容量計畫假設流量在 10 分鐘內逐步上升 | 尖峰比計畫更陡 |
| 應變 | 嚴重度定義以「全站無法使用」為 SEV1 門檻 | 18% 失敗不明顯符合，宣告延遲 14 分鐘 |
| 應變 | 同一晚的 INC-1110 結束後沒有重新排班；值班者在疲勞中接下第二個事故 | 志明從 22:03 起沒有休息，兩小時內第二次宣告 SEV1 的心理負擔也拉長了宣告延遲 |
| 應變 | 宣告前任何有部署權限的人都能修改 payments；沒有顯示 gateway 流量上限的儀表板 | 三個變更同時發生；擴容讓 429 從 2% 升到 31% |
| AI agent | 退款申請工具有單筆金額上限，但沒有總量或速率上限；agent 與客服的核准畫面都看不到對帳資料，無法分辨授權圈存與實際扣款；客服在進線暴增時只能整批核准 | 十幾分鐘內 212 筆申請被核准並退款，37 筆錯誤 |
| 流程 | 行銷推播排程沒有同步到值班行事曆 | 值班者不知道 00:00 前會有推播衝擊 |

除了「哪裡出了問題」，postmortem 也記錄了兩個常被省略的部分。**做得好的地方**：burn rate 告警在 3 分鐘內觸發；結帳排隊機制因為第 38 章的演練，啟用後 4 分鐘就見效；AI 客服退款申請工具的 kill switch 在 1 分鐘內生效；每日對帳流程讓重複扣款名單可以精確核對。**運氣好的地方**：gateway 在 03:40 自行恢復，如果持續到早上的第二波尖峰，排隊機制會讓大量使用者等待；知道一鍵付款路徑細節的小林當晚剛好在線上。

「運氣好的地方」特別值得寫下來。運氣是沒有被設計的防線，下一次未必會出現。把它寫出來，等於標出了「目前其實沒有保護」的地方。

> [!note] 關於「root cause」這個詞
> SRE 原書附錄的 postmortem 範例仍然有「root causes」欄位，很多公司的模板也是如此。這個詞本身不是問題，問題在於它暗示「只有一個」。許多組織改用「contributing factors」或在模板中明確寫「列出所有讓事故發生或擴大的條件」，提醒撰寫者不要在找到第一個原因時就停下來。

### 反事實推理要小心

分析時常會出現「如果當時有做 X，事故就不會發生」的句子，這叫**反事實推理**（counterfactual reasoning）。它有用，因為它指出可能的防線；但也危險，因為它很容易變成責怪（「如果小林有做壓測……」），而且它描述的是一個沒有發生的世界，而不是真正發生的事。比較好的寫法是把反事實轉成對系統的問題：不寫「如果小林有做壓測」，而寫「我們的流程在什麼情況下會要求針對慢依賴的壓測？這次為什麼沒有觸發？」

## 45.6 Action items：預防、緩解、偵測

### Action item 的類型

Postmortem 的價值，最終要落在 **action items**（改進事項）上。一份分析很深、但 action items 很弱的 postmortem，對系統的實際改變很有限。Action items 通常依它們作用的位置分類：

- **預防**（prevent）：讓同樣的觸發不再造成事故。例如讓一鍵付款路徑帶 idempotency key，讓重送不可能造成重複扣款。
- **緩解**（mitigate）：事故仍可能發生，但影響變小或恢復變快。例如 retry budget、退款申請的總量熔斷、自動觸發的排隊機制。
- **偵測**（detect）：讓問題更早、更準確地被發現。例如 gateway 延遲與 429 的告警與儀表板。
- **流程**（process）：改變人與團隊的協作方式。例如修訂嚴重度定義、把推播排程同步到值班行事曆。

一組好的 action items 通常會涵蓋多個類別。只有預防，下一個沒想到的觸發會再次造成同樣規模的傷害；只有偵測與流程，則代表系統本身沒有變得更強。

### 控制手段的強度

同樣是「防止重複扣款」，不同的做法效果差很多。職業安全領域有一個 **hierarchy of controls**（控制層級）的概念：最有效的是消除危害本身，其次是用工程手段隔離危害，再其次是行政流程，最弱的是依賴個人的注意力與訓練。套用到軟體：

```text
效果強 ▲
       │ 4 消除（eliminate）  讓錯誤不可能發生
       │                      例：共用 payments client 強制帶 idempotency key，不帶就無法編譯
       │ 3 工程防護（guard）   系統自動擋下或限制影響
       │                      例：retry budget、退款申請總量熔斷、CI 中的慢依賴測試
       │ 2 流程（process）     靠流程與檢查表
       │                      例：大促前的變更 review checklist
       │ 1 訓練（training）    靠人記得
       │                      例：提醒大家部署要小心
效果弱 ▼
```

這張圖的意思不是「流程與訓練沒用」，而是**風險越高，越不能只靠下層的手段**。Kevin 第一版報告中的「相關人員再教育」與「所有變更須經主管核准」，分別在第 1 層和第 2 層；postmortem 最後的 A1 讓共用的 payments client 在沒有 idempotency key 時直接拒絕送出請求，是第 4 層。前者要求每個人每次都記得，後者讓下一個寫新付款路徑的人根本不可能忘記。

### 好的 action item 長什麼樣子

一個有品質的 action item 至少具備以下特徵：

| 特徵 | 意義 | 不好的例子 | 好的例子 |
|---|---|---|---|
| 具體 | 讀完就知道要做什麼 | 加強 payments 的穩定性 | payments 的 gateway 重試改用 retry budget（每秒重試量不超過正常請求的 10%） |
| 可驗證 | 有明確的完成條件與驗證方式 | 改善監控 | 新增 gateway 429 比例告警；在 game day 中驗證值班者 2 分鐘內收到並找到儀表板 |
| 有 owner | 一個具名的人或團隊 | 大家、payments 團隊 | 建宏（platform 團隊，`harbor-common` 的 owner） |
| 有期限 | 依優先順序訂出日期 | 盡快 | 12 月 15 日前，下一次大促之前 |
| 有優先順序 | P0 必須在特定事件前完成 | （沒有標示） | P0：12 月大促前；P1：一季內；P2：排入 backlog 評估 |
| 對應 factor | 說得出它處理哪個 contributing factor | 「順便」重構 checkout | 對應「放大：重送不受 deadline 限制」 |
| 範圍合理 | 能在期限內完成，太大的拆分 | 重寫 payments 服務 | 先完成 retry budget，重構另開 design doc |

最後一點常被忽略。事故後大家的情緒很高，容易列出一長串野心很大的 action items，例如「重寫整個 payments」。這種項目幾乎不會在期限內完成，而且會把真正緊急的小項目擠到後面。Harbor 的經驗法則是：P0 項目要能在兩到四週內完成；更大的工作寫成 design doc（第 17 章），由正常的規劃流程決定。

### 不要列太多

列出所有想得到的改進看起來很負責，但會稀釋注意力。雙十一的討論中一開始列了 31 項，最後保留 14 項，其中 5 項 P0。被刪掉的項目並沒有消失，而是記錄在 postmortem 的「其他考慮過的改進」區塊，說明為什麼沒有列入（例如成本太高、效果不確定、已被其他項目涵蓋）。這和第 7 章 ADR 記錄被否決的選項是同樣的精神。

## 45.7 Postmortem 文件與 review

### 文件結構

Harbor 的 postmortem 模板，參考 SRE 原書附錄的範例並加入了 AI agent 相關欄位：

```text
標題、事故編號、嚴重度、狀態（草稿／review 中／已發布）
作者與審閱者
摘要：三到五句話，讓只讀這一段的人知道發生了什麼、影響多大、最重要的改變是什麼
影響：使用者、金錢、資料、error budget、客服、合作夥伴
時間線：附來源；標出偵測、宣告、止血、解決四個時間點
Contributing factors：分類列出，每項說明它如何讓事故發生或擴大
做得好的地方／做得不好的地方／運氣好的地方
AI agent 相關（若有）：agent 做了什麼、依據什麼輸入、權限邊界在哪、哪個 guardrail 有效或缺席
Action items：類型、控制強度、owner、期限、優先順序、驗證方式、追蹤連結
其他考慮過但未採用的改進與理由
附錄：儀表板截圖、查詢、聊天紀錄連結、訪談摘要
```

### Review：沒有人讀過的 postmortem 等於沒寫

SRE 原書提到一個原則：**沒有經過 review 的 postmortem，就像沒有寫過一樣**。初稿完成後，要經過資深工程師或 SRE 的 review，再在 postmortem review 會議中討論。Reviewer 要檢查的不是文筆，而是幾個實質問題：

- 時間線是否完整，有沒有缺少的段落或沒有來源的事實？
- 影響是否量化，包括 error budget 消耗？
- Contributing factors 是否涵蓋觸發、放大、偵測、應變，而不只是第一個找到的原因？
- 文字是否 blameless：描述行動時是否附上當時的資訊與情境？
- Action items 是否對應 factors、是否有足夠強度的控制手段、是否具體可驗證？
- 是否有「做得好」與「運氣好」的段落？

雙十一的 review 會議邀請了所有參與者、payments 與 checkout 的 tech lead、行銷與客服的代表，以及 Kevin。會議的第一條規則由志明宣布：「我們討論系統，不討論人。如果有人發現自己在解釋『為什麼我當時沒有……』，主持人會把問題改寫成『系統當時給了你什麼資訊』。」

## 45.8 追蹤與關閉：outage tracking

### Action items 的命運

寫出好的 action items 只完成了一半。很多組織的真實情況是：postmortem 發布時大家都很認真，三個月後回頭看，一半的項目還開著，沒有人記得它們。第 1 章提過一個例子：每次事故都寫了「加強測試」，半年後一項都沒做。

Action items 會被遺忘，是因為它們和日常工作競爭同一份時間，而日常工作永遠有更急的事。對策不是要求大家更有紀律，而是把追蹤做成機制：

1. **每個 action item 都是正式的 ticket**，連回 postmortem，放在 owner 團隊平常使用的 backlog 裡，而不是另一個沒人看的清單。
2. **P0 項目與 error budget policy 綁定**。雙十一後，checkout 與 payments 的非緊急發布暫停，直到 P0 項目完成。這讓 action items 和功能開發有了明確的先後順序。
3. **定期檢視**。SRE 團隊每兩週在可靠性週會上檢視所有開著的 P0 與 P1 項目；逾期的項目要由 owner 說明原因，並決定延期、拆分或升級給主管。
4. **關閉要驗證**。「程式碼合併了」不等於「風險降低了」。每個項目都要有驗證方式，例如 A2 的驗證是「在 load test 中讓 gateway 延遲 3 秒，gateway 呼叫數不超過正常的 1.1 倍」，沒有通過驗證就不能關閉。

### Outage tracker

單一事故的 action items 用 ticket 追蹤，但組織還需要一個地方保存**所有事故**的紀錄。SRE 原書第 16 章介紹了 Google 內部的 outage tracker（書中稱為 Outalator）：它把告警與事故彙整在一起，讓值班者可以把相關的告警歸併到同一個事故、加上標籤與註解，之後就能跨時間查詢與分析。原書的重點是：只有當事故被一致地記錄下來，才能回答「我們最常因為什麼出事」「哪類告警最常是雜訊」這種問題。

Harbor 的 outage tracker 比較簡單，是一個有固定欄位的事故資料庫：事故編號、嚴重度、影響服務、四個關鍵時間點、偵測來源（告警／客戶／人工）、contributing factor 標籤、postmortem 連結、action items 數量與完成數。關鍵在於**標籤要用固定的詞彙**：同一類問題，有人寫「retry storm」、有人寫「重試風暴」、有人寫「retry amplification」，就無法統計。Harbor 由 SRE 團隊維護一份約 30 個標籤的詞彙表，每季檢視一次。

## 45.9 跨事故趨勢分析

### 單一事故看不到的東西

一份 postmortem 回答的是「這次發生了什麼」，outage tracker 則能回答「我們一直在發生什麼」。某些問題只有放在一年份的事故中才看得出來：同一個 contributing factor 反覆出現、某一類事故總是由客戶先發現、某個團隊的 action items 總是逾期。

雙十一的 postmortem 在 review 時，志明從 outage tracker 撈出了一個讓所有人都安靜下來的事實：八月的 INC-0815 也是 retry 放大造成的，當時的 postmortem 已經列了「payments 改用 retry budget」這個 action item，但它一直排在功能開發後面，沒有完成。而就在同一個晚上、兩小時之前，INC-1110 的 inventory 只慢了二十幾秒，三層重試就讓整個網站倒了半個多小時（第 39 章）。十月的 INC-1003 是 AI 客服在一次訂單查詢異常時重複建立工單，當時也列了「為 agent 工具加上速率上限」，同樣沒有完成。換句話說，雙十一事故的兩個主要放大因素，Harbor 在事前都已經**知道**了。

這就是跨事故分析的價值：它把「學到了」和「做到了」之間的落差變得看得見。

### 要看哪些指標

| 指標 | 回答什麼問題 | 小心什麼 |
|---|---|---|
| 依嚴重度的事故數 | 整體趨勢是好轉還是惡化 | 事故數下降可能是少報，而不是更可靠 |
| Time to detect 的分佈 | 監控是否有效 | 由客戶先發現的事故要單獨看 |
| Time to declare 的分佈 | 宣告文化是否健康 | 長的宣告延遲往往比長的修復時間更值得改 |
| Time to mitigate 的分佈 | 止血手段是否準備好 | 看中位數與最差的幾次，不只看平均 |
| 重複出現的 factor 標籤 | 哪些是系統性主題 | 標籤詞彙要一致才有意義 |
| Action item 完成率與逾期數 | 學習是否轉成改變 | 只算「關閉」會鼓勵關掉沒驗證的項目 |
| 偵測來源比例 | 監控涵蓋是否足夠 | 客戶先發現的比例上升，是監控有缺口的訊號 |

第 14 章談過 Goodhart's law：當一個指標變成目標，它就不再是好指標。事故指標特別容易被扭曲。如果把「事故數」當成團隊的績效目標，最先發生的事是大家不再宣告事故，或把 SEV2 降成 SEV3。如果把「平均修復時間」當成目標，大家會提早宣告結束。所以這些指標應該用來**找問題**，而不是用來**評比團隊**。Harbor 在每季的可靠性回顧中看這些數字，但從不把它們放進個人或團隊的考核。

### 每季的系統性主題

Harbor 的做法是每季由 SRE 團隊整理一次跨事故分析，挑出二到三個**系統性主題**，交給 engineering 主管會議決定是否投入專案級的資源。雙十一後的那一季，主題是：

1. **Retry 與 deadline 的全面治理**：四次事故都和重試放大有關，其中兩次發生在雙十一同一個晚上。INC-1110 的 postmortem（第 39 章）已經得出同樣的結論，兩份 postmortem 的 retry 相關 action items 因此合併成一個專案：不再由各服務各自修，而是由 platform 團隊在 `harbor-common` 的 client library 中預設 retry budget 與 deadline 傳遞。
2. **Canary 看不到依賴的變化**：三次事故的變更都通過了 canary。投資方向是在 canary 期間注入依賴延遲，並把依賴的 latency 納入 canary 分析指標（第 29 章）。
3. **AI agent 的寫入工具需要總量上限**：兩次事故都和 agent 工具缺少速率限制有關。所有 agent 的寫入工具（包括「只是送出申請」的工具）都必須有總量熔斷，人工核准的畫面也要提供足以判斷的資料，這成為第 47 章 agent 授權模型的一部分。

這三個主題的投資規模，都遠大於任何單一 postmortem 能爭取到的資源。這也是跨事故分析的另一個價值：它讓可靠性投資的理由從「這次出事了」變成「這是我們反覆出事的模式」。

## 45.10 分享與學習

### 讓 postmortem 被讀

一份 postmortem 如果只有參與者讀過，學習就只發生在參與者身上。SRE 原書描述了幾個 Google 用來讓 postmortem 被更多人閱讀的做法：每月挑選一篇寫得好、有啟發性的 postmortem 在組織內分享；舉辦 postmortem 讀書會，讓團隊一起讀、一起討論；用 **Wheel of Misfortune**（不幸之輪）這種角色扮演的方式，讓新的值班者重新經歷過去的事故，練習判斷與應變（第 46 章會談到演練的設計）。

Harbor 把這些做法改成適合自己規模的版本：

- **所有 postmortem 對全體工程師公開**，放在可搜尋的位置，並在 engineering 頻道發布摘要。少數涉及資安細節的部分另外處理，但摘要與 action items 仍然公開。
- **每月一次 30 分鐘的「事故讀書會」**，由一位不是參與者的工程師導讀一篇 postmortem，重點放在「如果是我，我會在哪個時間點注意到」。
- **新人的 on-call 訓練包含三篇必讀 postmortem**，雙十一事故是其中之一。
- **公開表揚寫得好的 postmortem**，而且表揚的是分析品質，例如「這份 postmortem 找出了三個沒有人想到的 factor」，不是「這次事故處理得很快」。

最後一點和文化有關：如果組織只表揚「沒有出事」，大家會學會隱藏事故；如果組織表揚「把事故學得很透」，大家會學會誠實。

### 對外的事故說明

有時事故需要對外說明，例如影響了大量使用者、企業客戶（Harbor 的大型賣家），或有 SLA 責任（第 32 章）。對外的事故說明和內部 postmortem 是不同的文件：讀者不同、目的不同。對外版本要清楚說明影響、Harbor 做了什麼補救、會做哪些改進，用使用者能理解的語言，並經過法務與公關的確認；它不需要內部的訪談細節，也不應該把責任推給特定的合作夥伴或個人。雙十一事故後，Harbor 對受影響的使用者發出了說明與補償券，對大型賣家另外提供了一份較詳細的事故報告。

## 45.11 動手寫：action item 品質檢查與跨事故分析

第一段程式模擬 postmortem 追蹤會議會做的事：檢查每個 action item 的品質（owner、期限、驗證方式、用詞、控制強度），並依今天的日期判斷它們的狀態。

```python
from dataclasses import dataclass
from datetime import date

VAGUE = ("加強", "注意", "小心", "提醒", "確保大家", "再教育", "持續關注", "研究一下", "盡量")
KINDS = {"prevent": "預防", "mitigate": "緩解", "detect": "偵測", "process": "流程"}
STRENGTH = {"eliminate": 4, "guard": 3, "process": 2, "training": 1}   # 控制手段強度


@dataclass
class ActionItem:
    key: str
    title: str
    kind: str              # prevent / mitigate / detect / process
    control: str           # eliminate / guard / process / training
    owner: str
    due: date | None
    verify: str            # 怎麼證明它真的有效
    priority: str          # P0 / P1 / P2
    status: str = "open"   # open / done
    verified: bool = False


def lint(item: ActionItem) -> list[str]:
    problems = []
    if not item.owner or item.owner in ("大家", "團隊", "TBD"):
        problems.append("沒有具名 owner")
    if item.due is None:
        problems.append("沒有期限")
    if not item.verify:
        problems.append("沒有驗證方式")
    if any(word in item.title for word in VAGUE):
        problems.append("用詞模糊，無法判斷何時算完成")
    if item.priority == "P0" and STRENGTH[item.control] <= 1:
        problems.append("P0 風險只靠訓練或提醒")
    return problems


def tracker(items: list[ActionItem], today: date):
    print("項目 | 類型 | 強度 | 狀態 | 品質問題")
    for it in items:
        if it.status == "done" and not it.verified:
            state = "完成未驗證"
        elif it.status == "done":
            state = "已關閉"
        elif it.due and it.due < today:
            state = f"逾期{(today - it.due).days}天"
        else:
            state = "進行中"
        issues = "、".join(lint(it)) or "-"
        print(f"{it.key} | {KINDS[it.kind]} | {STRENGTH[it.control]} | {state} | {issues}")
    closed = sum(it.status == "done" and it.verified for it in items)
    p0_open = [it.key for it in items if it.priority == "P0" and not (it.status == "done" and it.verified)]
    print(f"\n真正關閉 {closed}/{len(items)}；尚未驗證關閉的 P0：{', '.join(p0_open) or '無'}")


items = [
    ActionItem("A1", "一鍵付款路徑補上 idempotency key，gateway 重送不再重複扣款", "prevent",
               "eliminate", "小林", date(2026, 11, 25), "注入 timeout 的整合測試：同一訂單只扣款一次", "P0",
               "done", True),
    ActionItem("A2", "payments 重試改用 retry budget 並受 checkout deadline 限制", "mitigate",
               "guard", "建宏", date(2026, 12, 15), "load test：gateway 延遲 3 秒時，gateway 呼叫數 ≤ 1.1 倍", "P0",
               "done", False),
    ActionItem("A3", "AI 客服退款申請加上總量熔斷：10 分鐘超過 50 筆自動暫停並通知", "mitigate",
               "guard", "美華", date(2026, 12, 1), "staging 演練：第 51 筆被擋下且 page 送達", "P0"),
    ActionItem("A4", "新增 gateway 429 與延遲的 cause dashboard，連結到 checkout alert", "detect",
               "guard", "志明", date(2026, 12, 20), "game day 中值班者 2 分鐘內找到 gateway 訊號", "P1"),
    ActionItem("A5", "提醒大家大促期間部署要更小心", "process", "training", "大家", None, "", "P0"),
    ActionItem("A6", "行銷推播時間表寫入 on-call 行事曆並設定提前 30 分鐘通知", "process",
               "process", "Lisa", date(2026, 11, 30), "12 月大促前抽查：推播排程都出現在行事曆", "P1",
               "done", True),
]
tracker(items, today=date(2027, 1, 15))
```

執行結果：

```text
項目 | 類型 | 強度 | 狀態 | 品質問題
A1 | 預防 | 4 | 已關閉 | -
A2 | 緩解 | 3 | 完成未驗證 | -
A3 | 緩解 | 3 | 逾期45天 | -
A4 | 偵測 | 3 | 逾期26天 | -
A5 | 流程 | 1 | 進行中 | 沒有具名 owner、沒有期限、沒有驗證方式、用詞模糊，無法判斷何時算完成、P0 風險只靠訓練或提醒
A6 | 流程 | 2 | 已關閉 | -

真正關閉 2/6；尚未驗證關閉的 P0：A2, A3, A5
```

第二段程式模擬 outage tracker 的季度分析：從一年份的事故紀錄中，算出關鍵時間的中位數、偵測來源、宣告延遲，以及重複出現的 contributing factor 標籤。

```python
from collections import Counter
from statistics import median

# 一年份的事故紀錄（outage tracker 匯出的精簡版）
# detect：開始影響→被發現；declare：被發現→宣告；mitigate：開始影響→止血（分鐘）
INCIDENTS = [
    ("INC-0213", "SEV2", 6, 3, 41, "alert",    {"retry-amplification", "dependency-latency"}, 5, 5),
    ("INC-0302", "SEV3", 22, 0, 60, "customer", {"config-change", "missing-alert"}, 3, 3),
    ("INC-0418", "SEV2", 4, 12, 35, "alert",   {"deploy", "canary-blind-spot"}, 4, 2),
    ("INC-0507", "SEV3", 9, 2, 25, "alert",    {"capacity", "batch-job"}, 2, 2),
    ("INC-0611", "SEV2", 31, 5, 80, "customer", {"dependency-latency", "missing-alert"}, 4, 1),
    ("INC-0720", "SEV3", 3, 1, 14, "alert",    {"deploy", "canary-blind-spot"}, 3, 3),
    ("INC-0815", "SEV2", 5, 18, 52, "alert",   {"retry-amplification", "deploy"}, 6, 2),
    ("INC-0909", "SEV3", 12, 4, 30, "human",   {"data-migration"}, 2, 2),
    ("INC-1003", "SEV2", 7, 9, 45, "alert",    {"ai-agent-tool", "missing-rate-limit"}, 3, 1),
    ("INC-1024", "SEV3", 15, 2, 33, "customer", {"config-change"}, 2, 1),
    ("INC-1110", "SEV1", 3, 3, 37, "alert",    {"retry-amplification", "dependency-latency", "db-failover"}, 8, 3),
    ("INC-1111", "SEV1", 3, 14, 51, "alert",   {"retry-amplification", "dependency-latency", "deploy",
                                                 "canary-blind-spot", "ai-agent-tool",
                                                 "missing-rate-limit", "declare-delay"}, 14, 2),
    ("INC-1207", "SEV3", 8, 1, 20, "alert",    {"capacity"}, 2, 0),
]

print(f"事故數 {len(INCIDENTS)}：", dict(Counter(i[1] for i in INCIDENTS)))
for name, idx in (("發現", 2), ("宣告", 3), ("止血", 4)):
    print(f"  中位數 time to {name}：{median(i[idx] for i in INCIDENTS):>4} 分鐘")

by_customer = [i[0] for i in INCIDENTS if i[5] == "customer"]
print(f"  由客戶先發現：{len(by_customer)}/{len(INCIDENTS)} {by_customer}")

slow_declare = [i[0] for i in INCIDENTS if i[3] >= 10]
print(f"  發現後 ≥10 分鐘才宣告：{slow_declare}")

print("\n重複出現的 contributing factor（≥3 次 = 系統性主題）：")
tags = Counter(t for i in INCIDENTS for t in i[6])
for tag, n in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0])):
    if n >= 3:
        ids = [i[0] for i in INCIDENTS if tag in i[6]]
        print(f"  {tag:<20} {n} 次  {ids}")

total = sum(i[7] for i in INCIDENTS)
closed = sum(i[8] for i in INCIDENTS)
print(f"\nAction items 關閉率：{closed}/{total} = {closed / total:.0%}")
early = [i for i in INCIDENTS if i[6] & {"retry-amplification"}]
print("retry-amplification 相關事故的 action 關閉情形：",
      [(i[0], f"{i[8]}/{i[7]}") for i in early])
```

執行結果：

```text
事故數 13： {'SEV2': 5, 'SEV3': 6, 'SEV1': 2}
  中位數 time to 發現：   7 分鐘
  中位數 time to 宣告：   3 分鐘
  中位數 time to 止血：  37 分鐘
  由客戶先發現：3/13 ['INC-0302', 'INC-0611', 'INC-1024']
  發現後 ≥10 分鐘才宣告：['INC-0418', 'INC-0815', 'INC-1111']

重複出現的 contributing factor（≥3 次 = 系統性主題）：
  dependency-latency   4 次  ['INC-0213', 'INC-0611', 'INC-1110', 'INC-1111']
  deploy               4 次  ['INC-0418', 'INC-0720', 'INC-0815', 'INC-1111']
  retry-amplification  4 次  ['INC-0213', 'INC-0815', 'INC-1110', 'INC-1111']
  canary-blind-spot    3 次  ['INC-0418', 'INC-0720', 'INC-1111']

Action items 關閉率：27/58 = 47%
retry-amplification 相關事故的 action 關閉情形： [('INC-0213', '5/5'), ('INC-0815', '2/6'), ('INC-1110', '3/8'), ('INC-1111', '2/14')]
```

逐段解讀：

1. `lint` 把 45.6 的品質標準寫成規則：沒有具名 owner、沒有期限、沒有驗證方式、用詞模糊、P0 只靠訓練。A5「提醒大家大促期間部署要更小心」一次觸發五個問題，它幾乎就是 Kevin 第一版報告中「再教育」的翻版。真實系統中，這類檢查可以做成 ticket 模板的必填欄位，或在 postmortem review 前自動檢查。
2. `tracker` 區分「完成」和「真正關閉」。A2 的程式碼已經合併，但 load test 還沒跑，狀態是「完成未驗證」，不算關閉。這個區分很重要：如果只看 ticket 狀態，A2 會被當成已完成，下一次 gateway 變慢時才發現 retry budget 的設定其實沒有生效。
3. 兩個月後，6 個項目中只有 2 個真正關閉，3 個 P0 尚未完成。A3（AI 退款總量熔斷）逾期 45 天，依 45.8 的規則要在可靠性週會上升級處理，而且依 error budget policy，payments 的非緊急發布仍應暫停。
4. 第二段程式的中位數顯示，Harbor 的「宣告」通常很快（中位數 3 分鐘），但有三次事故在發現後 10 分鐘以上才宣告，而且都是 SEV1 或 SEV2。只看中位數會錯過這個問題，所以 45.9 的表格提醒要同時看最差的幾次。同一晚的兩個 SEV1 也形成對比：INC-1110 全站中斷，明確符合舊的 SEV1 定義，3 分鐘就宣告；INC-1111 是 18% 的部分失敗，在舊定義下模稜兩可，加上值班者疲勞，拖了 14 分鐘。
5. 標籤統計找出四個重複主題，其中 retry 放大出現四次。最後一行把它和 action 完成率對照：二月的事故 5 項全完成，八月的事故 6 項只完成 2 項，而沒完成的正是 retry budget；三個月後的雙十一，同一個晚上就發生了兩次重試放大。這就是「知道了卻沒做到」在資料上的樣子。
6. 3/13 的事故由客戶先發現，代表監控有缺口；`missing-alert` 標籤出現在其中兩次，這可以成為下一季的偵測改善主題。

真實的 outage tracker 會從事故管理工具自動匯入時間點，標籤由 postmortem 作者依固定詞彙選擇，分析則用查詢或 notebook 完成。程式的結構不變：**一致地記錄 → 檢查品質 → 跨時間彙總 → 找出反覆出現的模式 → 交給有資源的人決定投資**。

## 45.12 Trade-offs 與 Failure Modes

| 做法或現象 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 找到第一個原因就停 | 事故有多個條件同時成立 | 結論停在「v2.31 有 bug」，canary 盲點、AI 退款申請的總量上限、宣告延遲都沒處理 | 用分類的 contributing factors，要求涵蓋觸發、放大、偵測、應變 |
| Blameless 變成「沒人負責」 | Action items 沒有具名 owner | 「payments 團隊研究重試策略」，半年後沒人記得 | 前瞻式 accountability：每項都有具名 owner、期限與驗證 |
| 名義 blameless，實際追究 | 主管在 postmortem 後私下評價當事人 | 第一版報告的語氣讓小林「下次不敢主動 rollback」 | 主管公開承諾 postmortem 不用於考核，並以行動證明；review 會議由中立者主持 |
| Action items 全在弱控制層 | 高風險只靠流程與訓練 | 「大促期間所有變更需主管核准」，結果主管在半夜成為瓶頸，大家開始找繞過的方法 | 依風險選擇控制強度；P0 至少要有工程防護 |
| 列太多項目 | 注意力被稀釋 | 31 項 action items，三個月後完成 6 項，而且是最簡單的 6 項 | 精簡到真正重要的項目；其餘記錄在「考慮過的改進」 |
| 只追蹤不驗證 | 程式合併但風險沒降低 | Retry budget 合併了，但設定預設值是「關閉」 | 關閉前必須通過驗證；ticket 狀態與驗證狀態分開 |
| 事故指標變成 KPI | 指標被最佳化而不是問題被解決 | 團隊為了降低 SEV2 數量，把事故降級成 SEV3 | 指標用於找問題，不用於考核；同時觀察 near miss 回報數 |
| Postmortem 太重 | 每個小事故都要寫十頁 | 值班者為了避免寫 postmortem，傾向不宣告事故 | 依嚴重度分級：SEV3 用一頁的輕量模板；near miss 可以只寫摘要 |

最後一項值得特別注意，因為它和第 44 章的宣告文化直接相關。如果 postmortem 的成本太高，它會反過來壓抑宣告：大家知道宣告了就要寫十頁的文件，自然傾向「先別宣告」。Postmortem 的深度應該和事故的影響相稱，而且組織要讓「寫 postmortem」被看作有價值的工作，安排時間，而不是在正常工作之外額外加班完成。

## 45.13 AI 時代：什麼變了？

**第一，AI 能大幅降低 postmortem 的整理成本。** 寫 postmortem 最耗時的部分往往不是分析，而是收集與整理：翻聊天紀錄、對照部署與監控時間、整理訪談重點。AI 可以做幾件具體的事：

- 從事故文件、聊天頻道、部署系統、告警系統與 agent 紀錄，產生時間線草稿，每一筆附上原始來源的連結。
- 標出時間線中的缺口，例如「00:13 到 00:16 之間沒有任何紀錄，但 429 比例在這段時間上升」，提示負責人去訪談。
- 檢查草稿中的語言，把「某某未經……」「某某疏忽」這類帶有責怪的句子標出來，並建議改寫成描述情境的版本。
- 依模板檢查 action items 的完整性，像 45.11 的 `lint` 一樣，但能理解比關鍵字更細的模糊表達。
- 在 outage tracker 中搜尋相似的過去事故與未完成的 action items，例如在雙十一 postmortem 的 review 前就提示「INC-0815 有一項 retry budget 尚未完成」。

**第二，AI 的錯誤會直接污染組織的學習。** Postmortem 是組織記憶，錯誤的內容會被引用很多年。AI 在這裡有幾種典型的失敗：在證據不足時補上「看起來合理」的事件或因果；把相關性寫成因果（「部署後 3 分鐘失敗率上升，因此部署是原因」）；從聊天訊息的語氣推論某人「慌張」或「疏忽」；把多個 contributing factors 簡化成一個漂亮的 root cause，因為單一原因的敘事比較好寫。

所以 AI 產生的內容要遵守和人一樣、甚至更嚴格的規則：每個事實附來源；推論與事實明確分開；不對個人的狀態或能力下判斷；最後由 postmortem 負責人與參與者確認。訪談的內容常常包含當事人的坦白，送給哪個模型處理、誰能讀到，要事先說明並取得同意。

**第三，AI agent 的事故需要新的分析問題。** 雙十一的 AI 客服退款申請是一個例子。分析 AI agent 的行為時，「agent 判斷錯了」和「工程師不夠小心」一樣，是起點而不是結論。要問的是系統層的問題：agent 看到的輸入是什麼（使用者描述「被扣兩次」，但沒有對帳資料）？它的工具權限邊界在哪（單筆上限有，總量上限沒有）？人工核准這道防線為什麼在高量時失效（核准畫面沒有對帳資料，客服只能整批核准）？哪個 guardrail 有效（kill switch），哪個缺席（速率熔斷、和帳務系統的交叉確認）？模型、prompt、工具版本是否在事故前有變更？AI agent 的一個好處是，它的「決策情境」比人的記憶更能被重建：只要保存了輸入、prompt 版本與工具呼叫紀錄，就能精確重播。前提是這些紀錄有被保存，這本身就是一個常見的 action item。

**第四，AI 可以幫忙做跨事故分析，但主題的優先順序由人決定。** 讓 AI 對一年份的 postmortem 做分群，常常能找出人沒注意到的模式，例如「五次事故的 contributing factors 都提到某個共用設定檔」。但哪個主題值得投入一季的工程資源，涉及成本、策略與風險偏好，仍是 engineering 主管的決策。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 從多個來源產生時間線草稿，每筆附來源，並標出時間線缺口 | 負責人與參與者確認後才成為正式時間線；沒有來源的事件不得寫入 |
| 標出帶有責怪的語言並建議改寫 | 是否 blameless 由 review 會議判斷；AI 不得對個人的能力、情緒或責任下結論 |
| 依 contributing factor 分類建議可能遺漏的面向（偵測、應變、AI agent） | Contributing factors 的取捨與因果判斷由負責人與參與者決定 |
| 檢查 action items 的完整性與控制強度，提示模糊用詞 | Action items 的優先順序、owner 與資源分配由團隊與主管決定 |
| 搜尋相似事故與未完成的 action items，對 outage tracker 做分群 | 系統性主題與投資決策由 engineering 主管會議決定 |
| 為 AI agent 事故整理輸入、prompt 版本、工具呼叫與 guardrail 觸發紀錄 | Agent 權限與 guardrail 的修改經 owner 審核；事故紀錄的保存與存取權限事先規範 |
| 草擬對外事故說明 | 對外內容由 comms、法務與公關確認，不得推測原因或歸責合作夥伴 |

> [!ai] AI 提醒
> 不要把 AI 的 postmortem 分析用在人事決策上，也不要讓參與者擔心它會被這樣使用。只要大家懷疑「AI 整理的時間線會被拿來評估誰慢了」，訪談與聊天紀錄就會開始變得謹慎，postmortem 失去的資訊會比 AI 節省的時間多得多。

## 45.14 專家怎麼想

- **「為什麼這在當時看起來是合理的？」** 這是資深工程師讀 postmortem 時最常問的問題。如果一份 postmortem 讓某個人的行動看起來很愚蠢，通常代表分析還不夠深，因為真實的人很少在知情的情況下做愚蠢的事。
- **先看 action items，再看分析。** 有經驗的 reviewer 常常先跳到 action items：它們的控制強度如何、是否對應 factors、是否有驗證方式。如果 action items 都在「提醒」「加強」的層次，分析寫得再好也沒有改變系統。
- **「運氣好的地方」是最被低估的段落。** 專家會特別注意這一段，因為它列出的是目前沒有被設計、只是剛好成立的防線。每一條「運氣好」都可以問：如果下次運氣不好，我們有什麼？
- **重複的事故是組織的問題，不是團隊的問題。** 當同一類 factor 出現第三次，專家不會再要求那個團隊「這次一定要修好」，而是問為什麼組織的優先順序機制讓它一直排不上，並把它升級成跨團隊的投資。
- **Postmortem 的成本要和價值相稱。** 資深 SRE 知道，過重的 postmortem 流程會壓抑宣告與坦白。他們會依嚴重度設計不同深度的模板，並為寫 postmortem 的人保留正式的工作時間。
- **主管的第一個反應決定文化。** Kevin 收回第一版報告的那一刻，比任何 blameless 的宣導文件都更有影響力。專家知道，文化是由壓力下的行為建立的，而不是由平時的口號。

## 45.15 動手練習

1. 找一份你寫過或讀過的事故報告，用 45.3 的改寫表把其中帶有責怪的句子改成 blameless 的寫法，並檢查改寫後是否仍然保留了所有事實。
2. 為雙十一事故畫一張你自己的瑞士起司圖：列出至少六層防線，標出哪幾層有洞、哪幾層有效，並為每一個洞提出一個不同控制強度的 action item。
3. 修改 45.11 的第一段程式：為 `ActionItem` 加上 `factor` 欄位，檢查每個 contributing factor 是否至少有一個 action item 對應，並列出沒有被處理的 factors。
4. 延伸第二段程式：加入每個事故的 `actions_due` 與完成日期，算出「上一次相同標籤的事故中，有多少 action items 在下一次事故發生前尚未完成」，找出「知道卻沒做到」的案例。
5. 用 45.7 的模板，為一個你熟悉的小事故（或 Harbor 的 INC-0507：一次夜間批次工作擠壓線上容量的 SEV3）寫一份一頁的輕量 postmortem，包含「做得好」與「運氣好」兩段。
6. 設計一份 Harbor 的事故標籤詞彙表（15–25 個標籤），分成觸發、放大、偵測、應變、流程、AI agent 六類，並寫下每個標籤的定義與一個例子，避免同義詞造成統計失真。

## 本章重點整理

- Postmortem 是一份書面紀錄，目標是更新組織對系統的理解並改變系統，而不是結案或找人負責。
- 觸發條件要事先寫好，通常包括使用者可見的影響、資料或金錢損失、值班者介入、偵測失敗，以及 near miss。
- 責怪會讓組織失去資訊：人們會少說、晚說，事故中最有價值的第一手判斷因此消失。
- 後見之明偏誤與結果偏誤會讓合理的決策在事後看起來愚蠢；blameless 的核心問題是「為什麼這在當時看起來合理」。
- Blameless 不是沒有人負責，而是把責任從回溯式的追究轉為前瞻式的 accountability：具名 owner、期限與驗證。
- 時間線要來自證據並附來源，同時記錄「當時的人知道什麼」；拆開偵測、宣告、止血、解決四個時間點，才能看出哪一段需要改善。
- 大型事故通常沒有單一 root cause；5 whys 只能抓到一條路徑、容易停在人身上，也看不到應變因素。
- 瑞士起司模型提醒我們問「每一層防線為什麼沒擋住」，並記錄做得好與運氣好的地方。
- Action items 依作用分為預防、緩解、偵測與流程；依控制強度分為消除、工程防護、流程與訓練，風險越高越需要強的控制。
- 好的 action item 具體、可驗證、有具名 owner、期限與優先順序，並對應到特定的 contributing factor。
- Action items 要成為正式 ticket，P0 與 error budget policy 綁定，定期檢視逾期項目，並在驗證後才關閉。
- Outage tracker 用一致的欄位與標籤詞彙記錄所有事故，讓跨事故分析成為可能。
- 跨事故分析能找出反覆出現的系統性主題，以及「知道了卻沒做到」的落差；事故指標用於找問題，不用於考核。
- 讓 postmortem 被閱讀：公開、讀書會、新人必讀、表揚分析品質；對外說明是另一份文件。
- AI 適合整理時間線、標出責怪語言、檢查 action items 與搜尋相似事故，但因果判斷、優先順序與人事相關的判斷必須由人做。

## 延伸問答

> [!question]- Q1. Blameless postmortem 和「沒有人要負責」有什麼不同？
> Blameless 改變的是責任的方向，而不是取消責任。回溯式的責怪問「誰造成了這件事」，結論是某人要更小心或受到處分；前瞻式的 accountability 問「誰負責讓這件事不再以同樣方式發生」，結論是有具名 owner、期限與驗證方式的 action items。
>
> 在實務上，blameless 的 postmortem 對「誰做了什麼」仍然寫得很清楚，因為這是事實；差別在於它同時寫出當時的資訊與情境，並且不把個人行為當成結論。當事人通常是最了解問題的人，常常也是最適合的 action item owner。蓄意破壞或明知故犯的行為則屬於另一套流程，不在 postmortem 中處理。

> [!question]- Q2. 為什麼 5 whys 不適合當大型事故的主要分析方法？
> 5 whys 產生的是一條因果鏈，但大型事故通常是多個條件同時成立的結果。以雙十一為例，gateway 變慢、重送次數增加、沒有 idempotency key、canary 看不到慢依賴、宣告延遲、AI 退款申請沒有總量上限，任何一個條件不成立事故都會小很多，一條鏈只能抓到其中一條路徑。
>
> 此外，5 whys 停在哪裡取決於誰在問，而且很容易停在「某人不夠小心」，因為人是最容易被看到的一環；它也只問「為什麼發生」，看不到應變過程中讓事故擴大的因素。比較好的方式是分類列出 contributing factors（觸發、放大、偵測、應變、流程），並為每一層防線問「為什麼沒有擋住」。5 whys 可以作為「多問一層」的習慣，但不應該是唯一的架構。

> [!question]- Q3. 你是 postmortem 的 reviewer，看到 action items 是「加強 code review」「提醒大家注意重試設定」「改善監控」。你會給什麼回饋？
> 這三項都有同樣的問題：不具體、無法驗證、沒有說明誰在什麼時候完成，而且前兩項都在控制強度最弱的訓練與流程層。我會請作者為每一項回答：它對應哪一個 contributing factor？完成時系統會有什麼不同？用什麼方式證明它有效？
>
> 具體的改寫方向例如：「加強 code review」可以變成「共用 payments client 在沒有 idempotency key 時拒絕送出請求，並加上注入 timeout 的整合測試」，這是讓錯誤不可能發生的消除型控制；「提醒注意重試設定」可以變成「client library 預設 retry budget 與 deadline 傳遞，並在 load test 中驗證 gateway 延遲 3 秒時呼叫數不超過 1.1 倍」；「改善監控」可以變成「新增 gateway 429 比例告警，並在 game day 中驗證值班者 2 分鐘內收到」。每一項再補上具名 owner、期限與優先順序。

> [!question]- Q4. 一個 action item 的程式碼已經合併，可以關閉了嗎？
> 不一定。程式碼合併代表「做了改變」，不代表「風險降低了」。設定可能預設關閉、可能只部署到部分環境、可能在真實條件下不如預期有效。所以每個 action item 在建立時就要寫清楚驗證方式，並在驗證通過後才關閉。
>
> 例如 retry budget 的驗證可以是 load test：讓 gateway 延遲 3 秒，觀察 gateway 的呼叫數是否被控制在正常的 1.1 倍以內。在追蹤系統中，最好把「實作完成」與「驗證通過」分成兩個狀態，否則完成率會被高估，而組織會以為自己已經受到保護。

> [!question]- Q5. 計算題：INC-1111 約有 6.1 萬次付款失敗。如果 11 月預計有 8,000 萬次有效付款嘗試，SLO 是 99.9%，這次事故用掉多少 error budget？如果同一晚的 INC-1110 另外造成約 25 萬次失敗，依第 32 章的 policy 會觸發什麼？
> 99.9% 的 SLO 代表允許 0.1% 的失敗，預算是 8,000 萬 × 0.001 ＝ 8 萬次。INC-1111 失敗約 6.1 萬次，是預算的 6.1 ÷ 8 ≈ 76%。單一事故就超過 20%，觸發 policy 第 2 條：必須完成 postmortem，下一次發布也要通過 canary 分析。
>
> 加上 INC-1110 的約 25 萬次，當晚合計約 31.1 萬次，是整月預算的 31.1 ÷ 8 ≈ 3.9 倍，預算耗盡，觸發第 3 條：暫停非緊急功能發布，直到 SLI 回到 SLO 以上，並且至少一位開發工程師加入可靠性工作，直到 postmortem 的 P0 action items 完成。這題也說明為什麼 error budget 要看整個時間窗而不是單一事故：兩個事故分開看，第二個「只」用掉四分之三的預算，合起來看，Harbor 在一個晚上就把好幾個月的預算用完了，這讓 action items 和功能開發有了明確的先後順序。

> [!question]- Q6. 主管要求「事故數量」和「平均修復時間」成為各團隊的季度 KPI。你會怎麼回應？
> 我會說明這兩個指標一旦成為考核目標，很可能會被最佳化而不是問題被解決，這是 Goodhart's law 的典型情境。事故數成為 KPI 後，最先發生的通常是少宣告、把 SEV2 降成 SEV3、不回報 near miss；平均修復時間成為 KPI 後，大家會提早宣告結束，或把一個事故拆成幾個小事故。結果是組織失去了最重要的學習資料。
>
> 比較好的做法是把這些指標用在找問題：看宣告延遲的最差幾次、客戶先發現的比例、重複出現的 factor 標籤、action item 的驗證完成率，並在季度回顧中轉成具體的投資主題。如果主管需要一個可以追蹤的目標，可以選擇「P0 action items 在期限內驗證完成的比例」這類鼓勵學習而不是隱藏事故的指標，同時觀察 near miss 回報數，確認回報文化沒有被壓抑。

> [!question]- Q7. AI 情境：Harbor 讓 AI 從聊天紀錄自動產生 postmortem 初稿，初稿寫著「根因：值班者在 00:04 錯誤地調長 timeout，延誤處理」。這份初稿有哪些問題？流程該怎麼設計？
> 這句話至少有三個問題。第一，它把多個 contributing factors 簡化成單一 root cause，而且選了最容易被看到的人的行動。第二，它用後見之明判斷決策：調長 timeout 在當時的資訊下是一個合理的假設，事後才知道它讓 worker 被佔住更久。第三，「錯誤地」「延誤」是對個人的評價，不是對事實的描述，這會讓參與者不再願意坦白。
>
> 流程上，AI 應該被限制在產生**有來源的時間線草稿**與**候選 factors 清單**，明確區分事實與推論，並被要求不對個人行為下評價；它也可以被設計成主動標出責怪語言。初稿必須由 postmortem 負責人與參與者確認，contributing factors 與結論由人決定。組織也要事先說明 AI 處理的訪談與聊天資料不會用於考核，否則大家會開始在頻道裡說得更少。

> [!question]- Q8. 面試題：如何判斷一個組織的 postmortem 文化是否健康？
> 可以從幾個可觀察的訊號判斷。第一，宣告與回報：near miss 是否會被主動回報、事故是否很早就被宣告，還是總是拖到瞞不住才宣告。第二，postmortem 的內容：是否有「為什麼當時看起來合理」的分析、是否有多個 contributing factors、是否有「做得好」與「運氣好」的段落，還是只有一個 root cause 和「再教育」。第三，action items 的命運：是否有具名 owner 與驗證方式、P0 是否在期限內完成、重複出現的主題是否被升級成跨團隊投資。
>
> 第四是主管的行為：事故後的第一個反應是找人還是找系統，postmortem 是否曾被用於考核。最後是學習的範圍：postmortem 是否公開、是否有人在讀、新人是否從過去的事故中學習。回答時可以補充，健康的文化不代表事故少，而是同一類事故越來越少，而且每次事故都讓系統多一層有效的防線。

## 延伸閱讀

- [Site Reliability Engineering — Postmortem Culture: Learning from Failure](https://sre.google/sre-book/postmortem-culture/)：Postmortem 的觸發條件、blameless 的原則、review 與推廣 postmortem 文化的做法。
- [Site Reliability Engineering — Tracking Outages](https://sre.google/sre-book/tracking-outages/)：Outage tracker 如何彙整告警與事故、加上標籤，並支援跨時間分析。
- [Site Reliability Engineering — Managing Incidents](https://sre.google/sre-book/managing-incidents/)：與第 44 章對照，理解事故中的記錄如何成為 postmortem 的基礎。
- [The Site Reliability Workbook — Table of Contents](https://sre.google/workbook/table-of-contents/)：從目錄進入〈Postmortem Culture: Learning from Failure〉一章，看寫得不好與改寫後的 postmortem 對照範例。
