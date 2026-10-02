---
chapter: 48
title: Capstone：從 Commit 到可靠服務的完整 Operating System
part: 8
---

# 第 48 章　Capstone：從 Commit 到可靠服務的完整 Operating System

> [!abstract] 本章地圖
> **核心問題**：把前 47 章的做法串起來，一個會「動錢」的 AI 功能要怎麼從一個想法，走到上線、出事、學習，再回到下一次變更？
>
> **你會學到**：
> - 用一個完整案例（Harbor 的 AI 退款助理）走過設計、review、測試、CI／CD、SLO、告警、容量、過載防護、上線審查、事故與 postmortem 每一站
> - 看懂每一站應該留下哪一份 artifact，以及它要回答什麼問題、會被下一站怎麼使用
> - 分辨「由模型判斷」與「由程式強制」的邊界，並把 prompt、模型、知識庫都當成變更來管理
> - 用模擬比較不同 guardrail 組合，量化「多久會知道」與「最多會錯多少」
> - 用 12 條核心原則回顧全書，並知道每一條該回到哪一章深入
>
> **前置知識**：建議讀完全書；只讀過第 1、2、32 章也能跟上主線，遇到陌生的名詞時依文中的章號回查
>
> **對應原書**：全書綜合；特別對應 SWE 第 1 章（時間、規模與取捨）、SRE 第 27 章〈Reliable Product Launches at Scale〉、第 32 章〈The Evolving SRE Engagement Model〉與第 34 章〈Conclusion〉

## 48.1 故事：「讓 AI 客服直接退款吧」

Harbor 走進第五年，已經是一家約兩百人的公司，五個大團隊底下分出了二十多個小組。第三年由志明帶領成立的四人 SRE 團隊，經歷第三年雙十一的容量事故（第 36 章）、第四年的預購過載（第 38 章）與雙十一當晚的兩場 SEV1（第 39、44 章）之後，第四年擴編到約六人，今年約八人；美華當年在 payments 團隊，後來成為 checkout 的 tech lead，現在是 staff engineer，凡是牽涉訂單與金額的跨團隊設計都會請美華 review；payments 團隊的小林則是 refund-service 的 owner；當年那個在週五晚上 SSH 進主機部署免運功能的阿凱（第 1 章），現在帶領今年新成立的「客服平台」小組，這個小組負責 AI 客服 agent。

第五年三月的季度規劃會上，產品經理 Lisa 帶來一組讓所有人都不太舒服的數字：客服每天收到約 1,900 件退款相關的工單，買家從提出到收到第一次回覆，平均要等 19 小時；三十位客服中有十二位整天都在處理退款，而其中大約七成是規則很明確的案件，例如「還沒出貨想取消」「物流確認遺失」「商品明顯破損並附了照片」。AI 客服 agent 早就能查訂單，也能替買家「發起退款申請」，但每一筆申請都要進人工核准佇列，19 小時大多花在排隊。Lisa 的提案很直接：讓 agent 自己完成規則明確的退款。

已經升任工程副總、帶領整個工程組織的 Kevin 沒有馬上答應，也沒有拒絕，只問了兩個問題：「如果它退錯錢，我們多久會知道？最多會退錯多少？」會議室安靜了一下。這兩個問題沒有一個能靠「模型很聰明」來回答。第一個問題問的是 observability 與告警，第二個問題問的是 blast radius（爆炸半徑，一次錯誤最多能影響的範圍）與 guardrail（護欄）。阿凱意識到，Kevin 其實是在問：這個功能的整條生命週期，從設計到事故，每一站有沒有人想過？

接下來的三個月，阿凱的小組帶著這個功能走完了整條路。它上線了，也出過一次事故：一份還在草稿階段的退貨政策被同步進知識庫，讓 agent 在一個週五晚上把大約 550 件「不想要了」的退貨判成「商品瑕疵」，多付了約 5.5 萬元的退貨運費。沒有任何一筆退款超過訂單金額，沒有重複退款，availability SLO 全程綠燈。這次事故既證明了很多設計是對的，也暴露了一個缺口：這種故障在前一年退款預審上線時演練過（第 46 章），卻沒有針對新的自動退款模式重跑。

這一章就是這三個月的完整紀錄。每一站都會指出它對應的章節，並附上 Harbor 實際留下的 artifact（工作產物）。讀這一章的方式，是把它當成一份可以照抄、再依自己情境修改的範本，而不是把它當成「做完這些就安全了」的保證。

## 48.2 全景：一個功能、十一站

第 1 章畫過一張「變更的流動」與「證據的流動」的圖。把 AI 退款助理放上去，就得到這一章的路線：

```text
 變更的流動（上線前）
 ① 問題與設計 ──► ② 小批次變更與 review ──► ③ 測試組合與 eval ──► ④ build、CI、漸進式發布
   第 2、5、7、11、17 章   第 15、16、19、20 章         第 22–26 章              第 27–29 章
                                                                                  │
 讓它能被營運（上線前就要完成）                                                    ▼
 ⑤ SLO 與 observability ── ⑥ alert、on-call、runbook ── ⑦ capacity 與過載防護 ──► ⑧ PRR 與 game day
   第 32、33 章              第 34、43 章                 第 36–42 章             第 30、46、47 章
                                                                                  │
 證據的流動（上線後）                                                              ▼
 ⑪ 回到起點：平台、授權、量測 ◄── ⑩ postmortem 與 action items ◄── ⑨ incident
   第 6、13、14、31、47 章            第 9、45 章                       第 43、44 章
```

這張圖由上往下讀。第一列是程式碼與設定從想法變成可部署產物的路；第二列是很多團隊會延後、卻必須在上線**之前**完成的事：沒有 SLO、告警、容量與 runbook 的功能，上線那一刻起就是在賭運氣；第三列是 production 送回來的證據，它最終要回到第一列，改變下一次的設計與檢查。

每一站都有一份 artifact。Artifact 的價值不在於「有寫文件」，而在於它是下一站的輸入：design doc 裡的 invariant 會變成測試與 policy；SLO 會變成告警規則；容量估算會變成過載時的降級順序；postmortem 的 action items 會變成新的 eval 案例與 CI 檢查。下表是本章會出現的所有 artifact：

| 站 | Artifact | 它回答的問題 | 下一個使用者 |
|---|---|---|---|
| ① | Design doc 摘要、ADR-041 | 要解決什麼？什麼絕對不能發生？為什麼這樣設計？ | reviewer、測試、policy |
| ② | PR #2317 描述 | 這次改了什麼、沒改什麼、怎麼驗證？ | code owner、未來的維護者 |
| ③ | 測試組合表 | 每一個風險由哪一層攔下？ | CI、上線審查 |
| ④ | Rollout 計畫 | 怎麼一步步擴大、什麼條件下停下？ | 發布系統、值班者 |
| ⑤ | SLO 文件 | 使用者過得好嗎？哪些事是零容忍？ | 告警、error budget policy |
| ⑥ | 告警規則、runbook | 何時叫醒誰？醒來後第一步做什麼？ | 值班者 |
| ⑦ | 容量估算 | 尖峰要多少資源？撐不住時先犧牲什麼？ | 採購、過載防護 |
| ⑧ | Launch checklist | 上線前還缺什麼？ | Kevin 的上線決策 |
| ⑨ | Incident timeline | 發生了什麼、何時知道、怎麼止血？ | postmortem |
| ⑩ | Postmortem action items | 系統要怎麼改，才不會再發生或更早被發現？ | 下一輪的 ① 到 ⑧ |

## 48.3 第一站：問題定義、design doc 與 ADR

### 先寫「什麼不能發生」，再寫「要做什麼」

阿凱的第一份草稿以功能為中心：agent 要能理解退款原因、要求照片、計算金額、呼叫退款。美華在 review 時只留了一句話：「先把 invariant 列出來。」**Invariant**（不變量，第 2 章）是無論系統怎麼變化都必須成立的條件。對一個會動錢的功能，invariant 比功能清單更重要，因為它定義了「什麼樣的錯誤是不可接受的」，也決定了哪些檢查必須由程式強制、不能交給模型判斷。

第二個要先想清楚的是**哪些門是單向的**（第 7 章）。換一個模型、改一段 prompt 是雙向門，錯了可以回退；但退款一旦撥出就很難追回，向買家要回多退的錢，代價是客服人力與信任。這個判斷直接決定了架構：所有單向門的動作，都必須在模型之外、由確定性的程式守門。

第三個是 **threat model**（威脅模型：列出誰可能怎麼攻擊或誤用這個系統）。AI 退款助理的威脅和一般 API 不同。它會讀到大量不受信任的文字：買家的訊息、訂單備註、商品評論、上傳圖片裡的字。任何一段都可能藏著 prompt injection（第 2、31 章）。OWASP 為 LLM 應用整理的風險清單中，把 **excessive agency**（過度授權：給模型的工具與權限超過任務需要）列為主要風險之一，這正是「讓 agent 直接退款」最直接的風險。

最後是公平性（第 11 章）。Lisa 提醒團隊，退款的買家裡有不少長輩、外籍配偶與不習慣打字的人，他們的訊息常有錯字、口語、注音文或中英夾雜。如果 agent 只對「寫得很清楚的人」判斷準確，它等於把退款速度分配給了特定族群。這條需求後來直接變成 eval 資料集的一個分層。

### Design doc 摘要

```text
Design Doc：AI 退款助理（refund-assistant）v1.3
Owner：阿凱（客服平台）　Reviewers：美華（staff engineer）、小林（payments）、志明（SRE）、Lisa（產品）、資安小組
目標    ：規則明確的退款案件，從「平均等待 19 小時」變成「對話內完成」
非目標  ：不處理賣家爭議、跨訂單合併退款；不改變退款規則本身
CUJ     ：買家開啟訂單 → 描述問題 → 提供證據 → 看到退款結果與預計到帳日
Invariants（由程式強制，不寫在 prompt 裡）：
  I1 單筆訂單累計退款 ≤ 已付金額
  I2 同一 idempotency key 至多產生一筆退款
  I3 自動退款單筆 ≤ 1,000 元，超過轉人工核准
  I4 agent 只能操作「目前登入買家本人」的訂單
威脅模型：訂單備註／評論／圖片文字中的 prompt injection；冒充客服或主管的社交工程；
          大量長對話造成的 denial of wallet；對話中的個資寫進 log
降級模式：auto → approval（全部人工核准）→ lookup_only（只查詢）→ off；feature flag 30 秒內生效
公平性  ：eval 依「書寫流暢度」與語言分層，各層通過率差距 ≤ 3 個百分點
```

I3 的 1,000 元沿用第 2 章原型的自動上限；I4 防的是一種叫 **confused deputy**（被混淆的代理人）的問題：agent 擁有比使用者更大的權限，如果它只憑對話內容就決定要操作哪一張訂單，攻擊者只要在訊息裡寫上別人的訂單號碼，就能借 agent 的手操作別人的訂單。

### ADR-041：誰真正按下退款鍵

最重要的架構問題是：agent 要怎麼「退款」？團隊用第 7 章的格式寫下這份 ADR：

```text
ADR-041：退款由確定性的 refund-gateway 執行，agent 只能提出 refund intent
狀態：Accepted（第 5 年 3 月 22 日）　Decision owner：阿凱
諮詢：小林（payments，refund-service owner）、美華（staff engineer）、志明（SRE）、資安小組；技術探勘（spike）由阿凱與一位 SRE 執行

## 背景
- 退款是單向門：撥出後追回成本高。客服每天約 1,900 件退款工單，約七成規則明確。
- 現行流程：agent 發起申請、客服在後台核准；客服後台權限可退任意金額，稽核紀錄只記操作人，不記理由。
- refund-service 僅支援 /v2/payments（舊的 /v1/pay 已依第 18 章的流程淘汰）。

## 考慮過的選項
1. 維持現狀：agent 只能發起申請，每一筆退款都由客服人工核准。
2. Agent 直接呼叫 refund-service 內部 API，沿用客服人員的權限。
3. Agent 只能呼叫 propose_refund 工具；refund-gateway 驗證身份、I1–I4、額度後才執行。
4. 不用 LLM：做一個規則式的自助退款表單。

## 決策
採用選項 3，並以選項 4 的規則引擎作為 gateway 的核心。

## 理由
- 選項 2 開發最快，但模型的任何誤判或被注入都直接變成金錢損失，blast radius 等於客服權限。
- 選項 4 完全可預測，但技術探勘顯示約四成買家的描述無法對應到表單選項，最後仍轉人工。
- 選項 3 讓模型只負責「理解對話、蒐集證據、選擇原因碼」，金額與資格由規則引擎計算；
  模型錯了，最壞結果是被 gateway 拒絕或轉人工。
- 關鍵假設：(a) 原因碼的判斷錯誤率可以用 eval 與線上抽樣量到；(b) 規則引擎能涵蓋七成案件。

## 後果
- 好：invariant 集中在一處、可測試；agent 的權限只有一個窄工具；每個決定可稽核。
- 壞：多一個服務要維運；規則變更需要同時改引擎與 agent 的知識庫，兩者可能不一致。
- 我們接受：較複雜的案件（爭議、合併退款）仍由人處理。

## 重新評估條件（任一成立即重新檢視）
- 自動退款的原因碼誤判率連續 2 週 > 2%
- 轉人工比例 > 50%（代表規則引擎涵蓋不足）
- 任何一次 invariant 被違反
- 最晚第 5 年 12 月 1 日
```

這份 ADR 最關鍵的一句話是「模型錯了，最壞結果是被 gateway 拒絕或轉人工」。它把一個機率性的元件，關在一個確定性的邊界裡。注意「後果」中的第二個壞處：規則引擎與知識庫可能不一致。三個月後的事故，正是從這個被寫下、卻沒有被追蹤的風險長出來的。

> [!warning] 常見誤解
> 「把規則寫進 system prompt，模型就會遵守。」Prompt 是給模型的建議，不是強制。它會被誤解、被注入的文字覆蓋，也會在換模型版本時改變效果。凡是違反時會造成單向損失的規則，都要在模型之外、在工具執行之前由程式檢查（第 2 章 2.11 的 `policy_check`）。

## 48.4 第二站：小批次變更與 code review

### 先把路鋪好，再接上 agent

整個功能被拆成二十幾個 PR，依照第 19 章的 trunk-based development 直接合併到主線，全部藏在 `refund_assistant.mode` 這個 feature flag 後面，預設是 `off`。拆分的順序是刻意的：先做 gateway 與規則引擎（純確定性程式，最容易測試），再做 agent 的工具定義，最後才接上模型。這樣每一個 PR 都小到 reviewer 能真正讀完（第 16 章），而且在 agent 接上之前，gateway 已經在 production 以 shadow 方式處理真實的人工退款，累積了一個月的證據。

Formatter、linter 與 type checker 在 CI 中強制執行（第 15 章），所以 review 時沒有人討論縮排；CODEOWNERS 規定 gateway 與 refund-service 的變更必須由 payments 團隊的 owner 核准，所以小林會看到每一個碰到金額計算的 PR；美華則被加為金額計算相關檔案的必要 reviewer。

### PR 描述

下面是 gateway 第一個核心 PR 的描述，格式沿用第 16 章 Harbor 的範本，多了一段「AI 參與」：

```text
PR #2317　refund-gateway：驗證 refund intent，並以 idempotency key 寫入

## 為什麼
ADR-041 第一階段：agent 的退款請求必須先經過 gateway，才能抵達 refund-service。

## 做了什麼
- 新增 POST /v1/refund-intents：驗證 I1–I4，回傳 allow／escalate／deny 與原因碼
- idempotency key = hash(conversation_id, order_id, item_ids)；重送時回傳第一次的結果
- 每個決定寫入 audit log：intent、決策、規則版本；不含對話全文

## 沒有做什麼
- 尚未接上 agent（refund_assistant.mode 預設 off）；未修改 refund-service

## 風險與驗證
- 新增 41 個 unit／property test；與 refund-service 的 contract test 已通過
- 以過去 30 天 3,812 筆人工退款重放：gateway 與人工決定一致 3,790 筆；
  22 筆不一致逐筆列於附件，皆為 gateway 較保守（escalate）
- Rollback：直接 revert，無 schema 變更

## AI 參與
- coding agent 產生 validator 初稿與 property test；I1 的累計計算由作者重寫
- agent 建議的套件 idem-keys 不在內部 registry 中，CI 的依賴 allowlist 擋下，改用 hashlib

## 請特別看
- validator.py 第 40–92 行：部分退款的累計與四捨五入
```

這份描述有三個值得注意的地方。第一，「以 3,812 筆人工退款重放」是最有說服力的一行：它用 production 的真實資料證明 gateway 的行為，而且把不一致的方向（較保守）講清楚。第二，「AI 參與」一段讓 reviewer 知道哪些部分要特別小心：第 16 章談過，review AI 生成的程式碼時，最需要確認的是作者自己是否理解每一行。第三，那個不存在的套件 `idem-keys`，是第 20 章談過的套件幻覺：模型會推薦聽起來合理、實際上不存在的套件名稱，攻擊者可以搶先註冊同名套件（slopsquatting）。擋下它的不是 reviewer 的記憶，而是 CI 中的依賴 allowlist。

### 誰核准、誰負責

這個功能有大量程式碼由 coding agent 起草，但第 2 章的責任分工表在這裡完全適用：agent 做了很多「工作」，卻不出現在「核准」與「負責」兩欄。PR 的作者是阿凱小組的工程師，他們要能解釋每一行；核准者是 code owner 小林；上線決策者是阿凱，Kevin 簽核最後的 launch checklist。

## 48.5 第三站：測試組合與 AI eval

### 從風險出發

第 22 章的方法是先列出「它會怎麼壞」，再問「最早在哪一層能真實地發現它」。AI 退款助理有一半的系統是確定性的程式（gateway、規則引擎、refund-service），另一半是機率性的模型行為，兩種需要不同的驗證方式：

| 風險（具體的失敗方式） | 最早真實的層 | 做法 | 執行時機 |
|---|---|---|---|
| 部分退款累計後超過已付金額 | Unit＋property-based（第 23 章） | 隨機產生任意退款序列，斷言累計 ≤ 已付 | 每次 presubmit，數秒 |
| refund-service 的回應格式改變 | Consumer-driven contract（第 25 章） | Gateway 為 consumer，refund-service 每次變更都要驗證 | 雙方 presubmit |
| 金流商逾時後重送造成重複退款 | Integration＋fake 金流商（第 24、41 章） | Fake 在第一次呼叫成功後故意逾時，驗證 idempotency key | 每次 presubmit，約 1 分鐘 |
| Agent 被注入或越權 | Eval：對抗性案例 120 題（第 25 章） | 任一題讓 agent 嘗試越權工具呼叫即擋下發布 | 任何模型、prompt、工具、知識庫變更 |
| Agent 判斷原因碼錯誤 | Eval：一般案例 600 題 × 5 次 | 通過率 ≥ 95%，且比上一版退步 ≤ 1 個百分點 | 同上 |
| 某些族群的判斷特別差 | Eval 分層（第 11 章） | 依書寫流暢度與語言分層，各層差距 ≤ 3 個百分點 | 同上 |
| 主要旅程斷掉 | E2E 3 條＋synthetic probe（第 22、32 章） | 「未出貨取消」「物流遺失」「破損附照片」 | 部署後與每 5 分鐘 |
| 尖峰時模型 API 限流 | Load／overload test（第 25、36、38 章） | 推到 P90 尖峰的 2 倍與 3 倍，觀察降級是否正確 | 大促前 |
| 模型供應商整個故障 | Chaos／game day（第 25、46 章） | 注入 100% 錯誤，驗證自動切到 lookup_only | 上線前與每季 |

這張表最重要的一點，是**invariant 不靠 eval 保護**。I1 到 I4 由 gateway 的 unit、property 與 integration test 保護，這些測試是確定性的，一次失敗就是一次失敗。Eval 保護的是「判斷的品質」，它天生是統計性的。把這兩種東西混在一起，例如「用 eval 確認 agent 不會超額退款」，等於把零容忍的規則降級成「通過率 99%」。

### Eval 是會 flaky 的測試

Eval 的每一題都要跑多次，因為同一個輸入可能得到不同的輸出。第 26 章處理 flaky test 的觀念在這裡直接適用：單次通過或失敗沒有意義，要看通過率與它的不確定範圍。團隊的規則是，一般案例看通過率的變化，對抗性案例則要求「每題 5 次全部通過」，因為安全問題只要發生一次就是事故。

Eval 資料集本身也是程式碼，放在 repository 裡、經過 review、有版本號。它的來源有三種：去識別化的真實工單、由客服資深同仁寫的邊界案例，以及資安小組寫的攻擊案例。每次事故之後，事故中的案例都要加進去（48.12 會看到這件事真的發生了）。

## 48.6 第四站：Build、CI 與漸進式發布

### 把「agent」打包成一個可追溯的 artifact

第 27 章說建置產物（artifact）要不可變、可追溯。對一般服務，artifact 是容器映像；對 AI 功能，決定行為的東西遠不只程式碼。團隊把下列內容打包成一個 **agent bundle**，和容器映像一起建置、簽章並記錄 provenance（第 27 章的來源證明）：

- 模型識別碼與參數設定（溫度、最大輸出長度）
- System prompt 與工具定義（JSON schema）的版本
- 規則引擎的規則版本
- 知識庫的引用方式

最後一項是事後才被證明最重要的一項。當時的 bundle 用**索引名稱**（`policy-kb`）引用知識庫，而不是用不可變的**快照版本**（例如 `policy-kb@v57`）。這代表 bundle 一旦部署，知識庫在背後更新時，agent 的行為就會改變，卻不會產生任何新的 artifact、不會跑 eval、也不會經過 canary。

### CI：把 eval 接進 presubmit

CI 的 presubmit（第 28 章）分成兩條路：程式碼變更跑 unit、contract、integration test，十分鐘內給結果；bundle 內容的變更（模型、prompt、工具定義、規則）額外觸發完整 eval，約四十分鐘。Eval 很貴，所以不是每個 PR 都跑全套：只改 gateway 程式碼的 PR 只跑對抗性案例的子集，改 prompt 的 PR 才跑全部。這就是第 28 章 test selection 的想法，用在一種新的測試上。

### Rollout 計畫

發布沿用第 29 章的 canary 與 feature flag，並結合第 31 章的授權階梯：agent 的權限不是在上線那天一次給足，而是分階段用證據換來的。

```text
Rollout 計畫：refund-assistant（每一階段的晉升由 owner 阿凱提出、SRE 志明核准，並附上數據連結）

階段 0  Gateway shadow（4 週）  人工退款同時送 gateway 判斷但不執行
        晉升條件：一致率 ≥ 99%；所有不一致都是 gateway 較保守
階段 2  Agent shadow（2 週）    agent 處理真實對話並提出 intent，不回覆買家、不執行
        晉升條件：與人工決定一致率 ≥ 97%；零次越權嘗試；各族群層差距 ≤ 3 點
階段 3  核准後執行（2 週）       agent 回覆買家，所有退款由客服一鍵核准
        晉升條件：核准率 ≥ 97%；客服駁回的案例全部檢視並分類
階段 4  有界自動                 ≤ 1,000 元且原因碼屬於自動清單者直接執行
        流量：1% → 5% → 25% → 100% 的買家，每階段至少 48 小時且涵蓋一個晚間尖峰
        自動停止：SLO fast burn、任何 invariant 違反、核准佇列等待 > 30 分鐘
```

階段編號沿用第 31 章維運 agent 的階梯（階段 1「建議」在這裡由 shadow 中的人工比對取代），換成第 47 章 47.6 節的全公司等級：階段 0 時 agent 還沒接上；階段 2 的 shadow 是 L2（提案）收集證據的方式；階段 3 是 L3（核准後執行）；階段 4 是 L4（有界自主），邊界就是 I3 的金額上限、自動原因碼清單與停止條件。授權的單位是「workflow × 環境」，所以等級是依原因碼分別給的，退款這個 workflow 也永遠不會到 L5。每一個晉升條件都是可量測的數字，而且「零次越權嘗試」這種條件不是平均值，一次就不能晉升。第 29 章說 canary 要涵蓋一次流量高峰，在這裡是「至少一個晚間尖峰」，因為退款對話集中在晚上。

DORA 指標（第 14、29 章）在這段期間也被追蹤：小組在三個月內平均每天部署 3 次，沒有一次部署需要 rollback 以外的修復。這不是因為他們特別小心，而是因為每次變更都很小，而且都在 flag 後面。

## 48.7 第五站：SLO 與 observability

### 從 CUJ 出發的 SLO

第 32 章說，SLI 要從使用者的角度量測，並明確定義分母。AI 退款助理的 SLO 文件節錄如下：

```text
SLO 文件：refund-assistant（v1，第 5 年 4 月；下次檢討 7 月 1 日）
Owner：阿凱（客服平台）　依賴：模型供應商、refund-gateway、orders、refund-service

SLI-1 對話可用性   good：助理在 deadline 內回覆，且非錯誤訊息
                   valid：所有買家送出的對話輪次，排除被 rate limit 擋下的請求
                   SLO：99.5%，30 天 rolling
SLI-2 回應延遲     首個字元 ≤ 2 秒的輪次比例 ≥ 95%；完整回覆 ≤ 8 秒的比例 ≥ 99%
SLI-3 判斷正確性   自動退款中，人工抽樣判定原因碼與金額正確的比例 ≥ 98%
                   量測：每日抽樣 200 筆，次日 09:00 產出（延遲約 24 小時）
追蹤但不設目標     無人介入完成率、轉人工率、每次對話 token 數
零容忍（不是 SLO，違反即 page）
                   I1–I4 任一被違反；同一 idempotency key 出現兩筆撥款
理由               可用性低於 checkout 的 99.9%：助理不可用時買家仍可走人工客服；
                   模型供應商對外承諾的可用性本身就低於 99.9%
```

這份文件有三個設計值得說明。第一，SLI-1 的目標比 checkout 低，理由寫得很清楚：它有降級路徑（人工客服），而且它的關鍵依賴（模型供應商）本身就撐不起更高的目標。第 32 章說過，依賴會把目標往下拉。第二，「無人介入完成率」刻意不設目標。第 32 章的 AI 提醒談過，若 agent 的目標是降低轉人工，它可能學會拒絕轉接；把它設成 SLO，就是把 Goodhart's law（第 14 章）寫進制度。第三，invariant 被明確地放在 SLO **之外**。SLO 是「允許一點不完美」，invariant 是「一次都不行」，兩者用完全不同的機制處理。

文件裡也有一個當時沒人質疑的弱點：SLI-3 的量測延遲是 24 小時。判斷錯誤是這個功能最可能、也最難察覺的失敗方式，而它的訊號卻是最慢的。

### Observability：一次對話是一條 trace

第 33 章說，要能從輸出重建系統內部發生了什麼。對 agent 來說，「內部」包括它看到了什麼、想了什麼、做了什麼。團隊用 OpenTelemetry 把一次對話建成一條 trace：每一次模型呼叫是一個 span，記錄模型版本、輸入與輸出 token 數、延遲；每一次工具呼叫是一個 span，記錄參數與結果；gateway 的每一個決定也是一個 span，記錄規則版本與原因碼。Trace 上還帶著 bundle 版本與知識庫的檢索結果 ID，這讓「這個回答是根據哪一份文件」可以被追溯。

隱私是同樣重要的設計。對話全文含有地址、電話與訂單細節，所以預設不進 log；trace 只記錄去識別化後的摘要與文件 ID，需要全文時必須透過有權限控管、有存取紀錄的工具查詢，保存期限也比一般 log 短。

## 48.8 第六站：Alert、on-call 與 runbook

### 告警規則

告警沿用第 34 章的 multi-window multi-burn-rate。SLO 是 99.5%，允許錯誤率 0.5%，所以 14.4 倍對應 7.2% 的錯誤率：

```yaml
groups:
  - name: refund-assistant-slo
    rules:
      - alert: RefundAssistantFastBurn          # 2% 預算／1 小時
        expr: |
          refund_assistant:turn_errors:ratio_rate1h > (14.4 * 0.005)
          and refund_assistant:turn_errors:ratio_rate5m > (14.4 * 0.005)
        labels: {severity: page, team: cs-platform}
        annotations: {runbook: "runbooks/refund-assistant.md#burn"}
      - alert: RefundAssistantSlowBurn          # 5% 預算／6 小時
        expr: |
          refund_assistant:turn_errors:ratio_rate6h > (6 * 0.005)
          and refund_assistant:turn_errors:ratio_rate30m > (6 * 0.005)
        labels: {severity: page, team: cs-platform}
      - alert: RefundAssistantBudgetTicket      # 10% 預算／3 天
        expr: |
          refund_assistant:turn_errors:ratio_rate3d > 0.005
          and refund_assistant:turn_errors:ratio_rate6h > 0.005
        labels: {severity: ticket, team: cs-platform}
      - alert: RefundInvariantViolation         # 零容忍：一次就 page
        expr: increase(refund_gateway_invariant_violations_total[5m]) > 0
        labels: {severity: page, team: payments}
        annotations: {runbook: "runbooks/refund-assistant.md#invariant"}
      - alert: RefundPolicyDenySpike            # 可能有人在嘗試注入
        expr: |
          refund_gateway:deny:ratio_rate1h > 5 * refund_gateway:deny:ratio_rate7d
        labels: {severity: ticket, team: security}
      - alert: RefundAssistantTokenOverspend    # denial of wallet
        expr: refund_assistant:tokens:projected_daily > 1.2 * refund_assistant:tokens:daily_budget
        labels: {severity: ticket, team: cs-platform}
```

前三條處理「使用者感受到的症狀」，第四條處理零容忍的 invariant，最後兩條是 ticket 等級的異常訊號。`RefundInvariantViolation` 送給 payments 團隊而不是客服平台，因為違反 invariant 代表 gateway 本身出了問題，要由 owner 處理。`RefundPolicyDenySpike` 送給資安：gateway 拒絕的比例突然升高，常常代表有人在大量嘗試操弄 agent，這正是第 2 章那個藏在訂單備註裡的指令會留下的痕跡。

注意這裡**沒有**一條關於判斷正確性的告警。SLI-3 只有每日抽樣，告警系統無從得知判斷品質在一小時內變差了。

### On-call 與 runbook

服務由客服平台小組自己值班（第 43 章），六位工程師一週一輪，payments 團隊當 secondary，SRE 團隊以顧問方式參與（第 47 章的 engagement 模式，48.10 會再談）。Runbook 的第一頁長這樣：

```text
runbooks/refund-assistant.md（節錄）

1. 先判斷是哪一種壞
   - 回覆失敗或很慢 → 看 dashboard 第一列：模型供應商、gateway、orders 哪一個在燒
   - 退款金額或資格可疑 → 直接跳到第 3 節，不要先查原因
2. 安全的第一步（不需要任何人核准）
   - 模型供應商錯誤率 > 20%：確認 circuit breaker 已切到 lookup_only；若沒有，手動切換
   - 部署後 30 分鐘內出現 burn：rollback 到上一個 bundle 版本
3. 退款可疑時
   - mode 設為 approval（所有退款改由客服核准，30 秒內生效）
   - 通知客服當班主管調派核准人力（核准模式下每人每小時約 60 件）
   - 若懷疑 invariant 被違反：mode 設為 off，並撤銷 agent 身份的 refund scope
4. 不要做的事
   - 不要在 production 直接修改 prompt 或知識庫來「修正」行為
   - 不要手動重送失敗的退款；用對帳工具，它會帶原本的 idempotency key
5. 升級：15 分鐘無法判斷 → 呼叫 secondary（payments）與 SRE incident commander
```

第 2 節與第 3 節的動作都是「止血」，而且都不需要先知道原因（第 44 章的先止血再修復）。降級模式不是只有「開」與「關」：`approval` 讓服務繼續運作、只是把決定權交回人，這比全部關掉更不傷使用者，也比繼續自動更安全。第 4 節的「不要做的事」來自 game day：演練時有人本能地想改 prompt 修正行為，這會在事故中引入一個沒經過任何測試的變更。

## 48.9 第七站：Capacity 與過載防護

### 容量估算

AI 功能的容量要用不同的單位計算（第 36 章 36.14）：不只是每秒請求數，還有 token、同時進行中的對話，以及模型 API 的速率上限。團隊的估算如下：

```text
容量估算：refund-assistant（規劃基準：大促後第二天晚間，P90）

需求
  尖峰新對話          600 件／小時（平日晚間約 150 件／小時的 4 倍）
  平均對話時長        6 分鐘（含買家打字與上傳照片）
  同時進行中的對話    L = λW = (600 / 60) 件／分 × 6 分 = 60 個          ← Little's Law
  每次對話模型呼叫    平均 5 次（P95 為 12 次）；每次輸入約 3,000、輸出約 250 tokens

模型 API
  輸入 token          600 × 5 × 3,000 / 60 ≈ 150,000 tokens／分鐘
  輸出 token          600 × 5 × 250 / 60 ≈ 12,500 tokens／分鐘
  配額目標            尖峰只用到配額的 50%（呼叫數變異大，見第 36 章 Kingman 公式）
                      → 申請 ≥ 300,000 輸入 tokens／分鐘；lead time 約 3 週

下游
  退款寫入            約六成對話產生退款 → 360 筆／小時 ≈ 0.1 筆／秒，對 refund-service 可忽略
  金流商退款 API      與賣家發起的退款共用上限；合計尖峰約為上限的 40%

降級路徑本身的容量
  若 AI 全關          600 件／小時轉人工；每位客服約 8 件／小時 → 需 75 人，當班只有 30 人
  若切到 approval      每位客服每小時可核准約 60 件 → 需 10 人
  → 結論：approval 是唯一能在尖峰承接的降級模式；off 只用於 invariant 被違反時

單次對話上限（由程式強制）
  ≤ 40,000 tokens、≤ 15 次工具呼叫、≤ 10 分鐘；每位買家每小時 ≤ 3 次新對話
```

這份估算最有價值的部分是倒數第二段。很多團隊會為主路徑算容量，卻忘了**降級路徑也需要容量**。如果事故時唯一的選項是「全部轉人工」，而人工只能接住四成的量，那個降級選項在尖峰時其實不存在。這個發現直接讓 `approval` 模式成為 runbook 的第一個止血動作。最後一段的上限則是對付 denial of wallet：它們由程式碼執行，不交給模型自己判斷「該停了沒」。

### 過載時先犧牲誰

第 38 章的分層防護在這裡要回答一個具體問題：雙十一那種流量湧進來時，退款助理應該排在哪裡？答案是很後面。Checkout 與 payments 的請求是 `CRITICAL`；refund-service 的寫入是 `CRITICAL`（已經答應買家的退款不能丟）；助理的新對話是 `SHEDDABLE`。過載時，gateway 先拒絕新的助理對話，買家看到「目前排隊人數較多，請留言，我們會在 24 小時內回覆」，而不是轉圈圈。

對模型供應商的呼叫套用第 39 章的整套工具：每一輪對話有 8 秒的 deadline，往下傳給每一次模型與工具呼叫；重試使用 exponential backoff 加 jitter，並受 retry budget 限制（重試量不超過正常請求的 10%）；連續失敗時 circuit breaker 打開，助理自動降級為 `lookup_only`，只能查詢、不能退款。這些設定在 game day 中被證明是必要的：第一次演練時沒有 retry budget，模型供應商一限流，重試就讓 token 用量在五分鐘內翻倍，直接觸發了更嚴格的限流。

## 48.10 第八站：上線前的 production readiness review

### SRE 怎麼參與

Harbor 約兩百人的規模下，約八人的 SRE 團隊不可能替每個服務值班。第 47 章依服務分級選擇 engagement 模式：Tier 0（checkout、payments）由 SRE 完整支援並承接主要 on-call；Tier 1 採 embedded（SRE 加入產品團隊）或 consulting（顧問），團隊自己值班；Tier 2 走平台自助的 golden path；所有服務在重大上線前都要做 production readiness review（PRR，上線前審查）。AI 客服 agent 屬於 Tier 1，退款助理採用的是 consulting 加上 PRR：客服平台小組自己擁有服務與值班，SRE 在設計階段提供意見，並在上線前主持一次審查；因為它是能動錢的 agent，審查同時涵蓋第 47 章的 agent readiness review 項目（獨立身份、等級、kill switch、安全 eval）。審查的依據是一份 launch checklist，它的精神來自 SRE 書第 27 章的 Launch Coordination Engineering：把過去上線出過的問題，變成每一次上線都要回答的問題（第 46 章）。

### Launch checklist（節錄）

| 類別 | 問題 | 證據 | 狀態 |
|---|---|---|---|
| 架構 | 單向門的動作是否都在模型之外守門？ | ADR-041；gateway 的 property test | 通過 |
| 容量 | 尖峰需求、配額、降級路徑容量是否算過？ | 48.9 的容量估算；配額申請單 | 通過 |
| 依賴 | 每個依賴失效時的行為？ | game day 報告：供應商、orders、gateway 三種故障 | 通過（修正 2 項） |
| 監控 | SLO、告警、dashboard、runbook 是否就緒並演練過？ | 告警規則的 promtool 測試；runbook 演練紀錄 | 通過 |
| 回退 | Rollback 與 kill switch 是否實測過生效時間？ | flag 切換實測 | 通過（修正 1 項） |
| AI | Eval 是否涵蓋對抗性與分層案例？模型與 prompt 變更是否走同一條管線？ | eval 報告 v12；CI 設定 | 通過 |
| 資料 | 對話資料的保存、遮罩、存取紀錄？ | 隱私審查紀錄 | 通過 |
| 人 | 值班表、secondary、客服核准人力是否確認？ | on-call 排班；客服主管簽核 | 通過 |

### Game day 找到的三個問題

上線前兩週的 game day（第 46 章）刻意製造了三種故障，找到了三個問題。第一，kill switch 宣稱「30 秒內生效」，實測卻要 4 分鐘，原因是 app 端快取了 flag 設定；修正後重測為 25 秒。第二，前面提到的 retry 放大。第三，模擬「知識庫服務無法連線」時，agent 沒有報錯，而是在沒有政策文件的情況下照常回答，口氣一樣有自信。團隊為此加了一條規則：檢索失敗時，agent 只能回答「目前無法確認政策，已為您轉人工」。

這場 game day 沒有重跑「知識庫連得上，但內容是錯的」這個情境。它其實不是新情境：前一年退款預審上線前的 game day 就演練過「知識庫被更新成錯誤的退款政策」（第 46 章），但當時 agent 只產生建議、最後由客服核准，錯誤的政策頂多讓建議變差。新的自動退款模式拿掉了這道人工防線，同一個故障的後果完全不同，劇本卻沿用了「已經演練過」的判斷。Game day 的劇本要隨授權等級一起重新檢視：等級升高時，過去演練過的情境也要在新模式下重跑一次。

Kevin 在 checklist 上簽核時，問了一開始的那兩個問題。阿凱的回答是：「退錯錢的話，超過訂單金額、重複退款、操作別人訂單這三種，一次都不會發生，發生了五分鐘內會 page；判斷錯原因碼的話，最慢隔天早上九點會知道，每筆最多錯 1,000 元。」這個回答誠實地說出了一個已知的弱點。第二天，功能進入階段 4 的 1% 流量。

## 48.11 第九站：Incident——一份草稿進了知識庫

功能在五月下旬推到 100% 的買家。三週後，年中慶的第一個週五，事故發生了。下面是由 AI scribe 起草、IC 確認後的時間線（從第五年起，事故編號加上年份，避免和第 45 章 outage tracker 裡往年的編號重複）：

```text
INC-2027-0611　refund-assistant 將「不想要了」誤判為「商品瑕疵」　SEV2
IC：志明　Ops lead：阿凱（當週 primary）　Comms：Lisa　Scribe：AI scribe（IC 逐條確認）

06-11（五）
17:50  客服營運在政策文件資料夾上傳「年中慶退貨政策（草稿，待法務確認）」
       草稿寫著：「活動期間，商品與描述不符視同瑕疵，由 Harbor 負擔退貨運費」
18:00  知識庫同步 job 依排程重建 policy-kb 索引（v58），資料夾內的草稿一併被收錄
18:05  「判為瑕疵」的占比由約 31% 開始上升；availability 與 latency SLO 全綠，無任何告警
21:30  夜班客服在 >1,000 元的核准佇列中發現多件「瑕疵」案件描述只是「尺寸不合」，
       在客服群組詢問，未得到回應
06-12（六）
09:00  每日抽樣報告產出：200 筆中 31 筆判斷錯誤（15.5%，門檻 4%）→ page
09:08  阿凱 ack，比對報告與 dashboard，確認錯誤集中在「瑕疵」原因碼
09:15  宣告 SEV2；志明擔任 IC
09:19  止血：mode 設為 approval；客服主管調派 6 人處理核准佇列
09:41  查出 policy-kb 於 18:00 重建，新收錄的文件中有一份標示為草稿
09:55  policy-kb 回退到 v57；以 v57 重跑 eval，通過
11:20  「未出貨取消」「物流遺失」兩類原因碼恢復 auto；「瑕疵」依降級規則重新累積證據
12:30  止血完成。初步影響：約 550 筆誤判，多負擔退貨運費約 5.5 萬元；無 invariant 違反
       Lisa 與財務決定不向買家追回，計入活動成本
```

把時間線對照 48.2 的路線圖，可以看到每一站在事故中扮演的角色。**做對的事**很多：invariant 一次都沒有被違反，因為金額由規則引擎計算，誤判只影響「誰付運費」；`approval` 模式在 4 分鐘內接手，這是容量估算時就選好的降級路徑；idempotency key（冪等鍵，第 41 章詳談）讓模式切換期間沒有任何一筆退款重複執行；IC、ops、comms 的分工（第 44 章）讓阿凱可以專心查原因，Lisa 負責和客服、財務溝通。AI scribe 整理時間線省下了不少時間，但每一條都經過志明確認，因為 scribe 會把「有人在群組猜測」寫得像「已確認的事實」（第 44 章）。

**沒做好的事**同樣清楚。從 18:05 到 09:00，系統在將近 15 個小時裡以穩定的速度做錯事，而所有告警都是安靜的，因為唯一能看到這種錯誤的訊號（SLI-3）延遲 24 小時。21:30 其實有人看到了，但那個訊號沒有路可以走。

## 48.12 第十站：Postmortem 與 action items

### 不只一個原因

第 45 章說，postmortem 要避免找「唯一的 root cause」。如果這份 postmortem 寫成「客服營運把草稿放錯資料夾」，結論就會是「以後小心一點」，而那位同仁其實只是照著一個沒有人告訴過這位同仁有風險的流程做事。團隊寫下的是一組 **contributing factors**（促成因素）：

1. 知識庫同步 job 收錄資料夾內的所有文件，不檢查文件的核准狀態。
2. Agent bundle 以索引名稱引用知識庫，知識庫更新不會產生新版本、不跑 eval、不經過 canary。ADR-041 已寫下「規則引擎與知識庫可能不一致」的風險，但沒有對應的機制。
3. 判斷正確性是這個功能最主要的風險，它的唯一訊號卻延遲 24 小時。
4. Gateway 檢查單筆金額，但沒有限制一段時間內的自動退款總量，所以錯誤的總影響只受時間限制。
5. 第一線人員發現異常時，沒有明確的回報管道；週五晚上的群組訊息沒有人負責回應。這是第 9 章談的心理安全與「讓壞消息提早出現」的機制問題，而不是個人問題。

Postmortem 也記下了**運氣好的地方**：草稿影響的只是運費，不是商品金額；如果它寫的是「活動期間全額退款不需退貨」，損失會大一個數量級，而 I1 到 I3 依然不會被違反，因為每一筆都在訂單金額與自動上限之內。這句話讓所有人都意識到：invariant 只保證每一筆「不離譜」，不保證「正確」。

### Action items

```text
INC-2027-0611 action items（每一項都要有 owner、期限，以及「怎麼證明完成了」）

#  類型  行動                                               Owner        期限    完成的證據
1  預防  同步 job 只收錄「已核准」狀態的文件；草稿與正式    知識平台     06-25   上傳草稿的整合測試；稽核 7 天
         文件分在不同的儲存位置                                                  內索引中無草稿
2  預防  Bundle 以快照版本引用知識庫（policy-kb@v57）；     阿凱         07-09   在 staging 發布一份刻意錯誤的
         知識庫變更走與 prompt 相同的 eval 與 5% canary                          政策，管線自動擋下
3  偵測  新增「判為瑕疵占比」漂移告警：2 小時窗口，相對     志明         06-30   以 06-11 資料重放，18:59 觸發
         過去 7 天基線的 z 值 > 4 即 page
4  緩解  Gateway 加每小時自動退款預算，超過的案件轉人工     小林         07-09   load test 中預算觸發後
                                                                                 轉人工比例正確
5  偵測  客服後台加「這個案件怪怪的」一鍵回報，直接開      Lisa         06-30   演練：夜班回報 15 分鐘內被 ack
         ticket 給 refund-assistant 值班者
6  預防  Eval 新增 40 題「尺寸不合、不想要」被誘導成瑕疵    客服平台     06-18   新題目在 v58 下必須失敗、
         的案例，並加入「政策文件互相矛盾」的案例                                在 v57 下通過
7  流程  「瑕疵」原因碼依第 47 章降級規則退回 L2：shadow     阿凱；       06-12   升級紀錄附上 shadow 一致率與
         一週、L3 核准後執行一週，再依 rollout 條件晉升      Kevin 核准           核准率數據
```

這張表依第 45 章的分類，同時涵蓋**預防**（讓它不再發生）、**偵測**（發生時更早知道）與**緩解**（發生時傷害更小）。只有預防是不夠的：第 1 項堵住了這一次的入口，但下一次錯誤可能從完全不同的地方進來，例如模型供應商悄悄更新了同名模型的行為；第 3、4、5 項處理的是「不管錯誤從哪裡來」都有效的部分。每一項的最後一欄都是可以被別人檢查的證據，而不是「已完成」三個字。第 3 項的驗證方式特別值得學：用事故當天的資料重放，證明新告警真的會在第一個小時內響。48.15 的程式就是在做這件事。

第 7 項和時間線中 09:19 的止血是兩件不同的事，值得分清楚。把 `mode` 切成 `approval` 是**緊急的 runtime 模式切換**：runbook 授權任何值班者在幾十秒內執行，目的是止血，確認修復後也可以切回。第 7 項則是第 47 章的**授權降級**：一個 workflow 牽涉進事故，它的等級就直接降回 L2，要用新的證據逐級回升，不能因為知識庫已經回退就自己恢復。授權的單位是「workflow × 環境」，這次牽涉事故的只有「瑕疵」原因碼，所以 11:20 先切回 auto 的兩類原因碼不受影響，「瑕疵」則從 L2 的 shadow 重新開始。

## 48.13 第十一站：回到起點

### 閉合迴路

Postmortem 不是終點。七個 action items 在四週內全部關閉，每一項都改變了前面某一站的東西：第 2 項改變了 build（bundle 的內容），第 6 項改變了測試（eval 資料集），第 3 項改變了告警，第 4 項改變了架構，第 7 項改變了授權。這就是第 1 章「把外迴路學到的東西，搬進內迴路」的具體樣子。ADR-041 也被更新：它的「重新評估條件」之一「任何一次 invariant 被違反」沒有被觸發，但團隊仍依事故結果新增了 ADR-047「知識庫是 bundle 的一部分」，並在 ADR-041 加上一行 `Amended by ADR-047`（第 7 章的 ADR 生命週期）。

### 從一個團隊的教訓到平台的預設值

Kevin 在事故後的工程週會上問了一個第 6、13 章式的問題：「Harbor 還有幾個團隊在做 AI 功能？他們的知識庫是怎麼引用的？」答案是四個團隊，其中三個也用索引名稱。如果每個團隊都要各自經歷一次事故才學會，組織的學習成本會和團隊數成正比。

platform 團隊因此把退款助理的做法整理成一條 **golden path**（第 13、47 章：平台提供的、預設就做對的路）：一個 AI 功能的範本，內建 bundle 打包與快照引用、eval 管線、canary、kill switch 與降級模式、tool gateway 的骨架、token 與步數上限，以及預設的 SLO 與告警規則。下一個要做「賣家 AI 助理」的團隊，不需要讀這份 postmortem 也會自動得到這些保護。這是第 13 章「Always Be Scaling」的意義：一個人或一個團隊的經驗，要變成制度與平台，才不會隨著人離開而消失。

### 怎麼知道這個功能真的成功了

上線三個月後，Lisa 要回答一開始的問題：這個功能值得嗎？第 14 章提醒過，只看一個數字一定會被它誤導。團隊同時看三組訊號：**結果**（規則明確案件的首次回覆時間從平均 19 小時變成對話內完成；處理退款的客服從十二位降到五位，其他人轉去處理爭議案件）、**品質與風險**（判斷正確率、每千筆訂單的退款金額、買家申訴率、客服駁回率）、**人的感受**（客服與買家的滿意度調查、值班者的 page 數與夜間 page 比例）。如果只看第一組，任何「讓更多案件自動完成」的改動都會看起來是好的，即使它其實是在用退錯錢換速度。

## 48.14 全書 12 條核心原則

走完十一站之後，可以把全書濃縮成 12 條原則。每一條都在這個 capstone 中出現過，也都對應到書中的專章。

**1. 軟體工程是隨時間積分的程式設計。** 一段程式的成本主要發生在寫完之後：被閱讀、被修改、被升級、被淘汰。為未來的修改者最佳化，包括三個月後的自己。（第 3、4 章）ADR-041 就是寫給三個月後處理事故的人看的。

**2. 線性成長的人工工作是警訊。** 規模會讓「每次都手動做一下」變得無法負擔；解法是自動化、平台化與制度化，而不是加人。（第 6、13、31 章）十二位客服處理退款是這種警訊，四個團隊各自踩同一個坑也是。

**3. 所有可觀察行為都會被依賴，所以契約與 invariant 要寫下來，並由機器強制。** 只存在於人腦或 prompt 裡的規則，遲早會被打破。（第 2、5、17、18 章）I1 到 I4 在事故中一次都沒有被違反，因為它們寫在 gateway 裡。

**4. 決策要留下理由、被否決的選項與重新評估的條件，並分清單向門與雙向門。** 不可逆的動作值得多花時間，可逆的動作應該快速嘗試。（第 7 章）退款是單向門，所以由確定性的程式守門；prompt 是雙向門，所以可以頻繁迭代。

**5. 讓壞消息提早出現。** 心理安全、blameless postmortem 與明確的回報管道，是可靠性系統的一部分，不是軟性的附加品。（第 8–12、45 章）週五 21:30 的那則群組訊息，是本次事故最早、也最便宜的訊號。

**6. 小批次、可逆的變更比大而完美的變更安全。** 小 PR 能被真正 review，feature flag 讓發布與部署分離，漸進式發布讓錯誤只影響少數人。（第 16、19、29 章）二十幾個小 PR、四個 rollout 階段，讓這個功能在上線過程中沒有出過事。

**7. 依風險配置驗證，每一道關卡攔下不同的錯。** 快而可信的關卡勝過多而吵的關卡；確定性的規則用確定性的測試保護，機率性的行為用統計性的 eval 保護。（第 22–28 章）

**8. 可靠性必須被定義。** 從使用者旅程出發定義 SLI 與 SLO，用 error budget 讓速度與穩定在同一個尺度上談判；零容忍的事另外處理。（第 32、35 章）這次事故中 SLO 全綠，提醒我們：SLI 沒有量到的傷害，在數字上就不存在。

**9. 只為使用者可見、需要立刻行動的症狀叫醒人，而且訊號的速度要配得上風險的速度。** （第 33、34 章）最主要的風險配上最慢的訊號，是這次事故持續 15 小時的原因。

**10. 為失敗設計。** 容量要包含 headroom、failure domain 與降級路徑本身的容量；過載時要有意識地決定先犧牲誰；每個依賴都要有 timeout、retry 上限與斷路機制。（第 36–42 章）

**11. 先止血再修復，並把外迴路的教訓搬進內迴路。** 事故中角色清楚、動作可逆；事故後的 action items 要變成測試、檢查、告警或更簡單的設計，並以證據關閉。（第 1、43–46 章）

**12. AI 擴大能力，但不轉移責任。** Agent 的權限隨證據逐步取得，policy 在模型之外強制執行，模型、prompt 與知識庫的變更和程式碼變更走同一條管線，每一個動作都能追溯到一位負責的人。（第 2、25、31、47 章）

## 48.15 動手寫：用事故資料重放 guardrail 組合

Postmortem 的第 3 項 action item 要求「用事故當天的資料重放，證明新告警會觸發」。下面的程式把這個想法推廣：模擬事故前後兩天的退款對話，比較不同 guardrail 組合下，錯誤多久被發現、多付了多少錢、又把多少案件轉給了人。

```python
import math
import random

SHIPPING = 100                 # 誤判成「瑕疵」時，Harbor 多負擔的退貨運費（元）
HOURS = 48                     # 模擬兩天：第 0 小時是第一天 00:00
KB_RELEASE = 18                # 第一天 18:00 發布退貨政策知識庫 v58
DAILY_REVIEW = 33              # 第二天 09:00 完成前 24 小時的人工抽樣
P_DEFECT = 0.30                # 真正是商品瑕疵的比例
MIS_OLD, MIS_NEW = 0.02, 0.35  # 「不想要了」被判成「瑕疵」的機率：舊版／新版知識庫
MANUAL_HOURS = 3               # 降級為人工核准後，確認修復前維持幾小時


def traffic(hour):             # 每小時的退款對話數：深夜少、晚上尖峰
    h = hour % 24
    return 40 if h < 8 else 180 if h < 18 else 300


def make_stream(seed=48):
    rng = random.Random(seed)
    return [(hour, rng.random() < P_DEFECT, rng.random(), rng.random())
            for hour in range(HOURS) for _ in range(traffic(hour))]


def z_one(p_hat, p0, n):
    return (p_hat - p0) / math.sqrt(p0 * (1 - p0) / n)


def z_two(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (x1 / n1 - x2 / n2) / se if se else 0.0


def clock(hour):
    return f"第 {hour // 24 + 1} 天 {hour % 24:02d}:59"


def run(name, hourly_cap=None, drift_alert=False, kb_canary=False, kb_change=True):
    print(name)
    stream, sampler = make_stream(), random.Random(7)
    base_share = P_DEFECT + (1 - P_DEFECT) * MIS_OLD   # 過去 7 天「判為瑕疵」的占比
    kb = "old"                                          # old → canary → new，或 rolled_back
    manual_until = -1
    excess = to_human = 0
    canary = {"new": [0, 0], "old": [0, 0]}            # [判為瑕疵數, 對話數]
    window, auto_log = [], []                           # 漂移告警窗口；自動處理紀錄（供抽樣）
    for hour in range(HOURS):
        if hour == KB_RELEASE and kb_change:
            kb = "canary" if kb_canary else "new"
        spent, flags = 0, []
        for _, is_defect, u, v in (e for e in stream if e[0] == hour):
            arm = "new" if kb == "new" or (kb == "canary" and v < 0.05) else "old"
            says_defect = is_defect or u < (MIS_NEW if arm == "new" else MIS_OLD)
            if kb == "canary":
                canary[arm][0] += says_defect
                canary[arm][1] += 1
            flags.append(says_defect)
            if hour <= manual_until:                    # 降級模式：全部轉人工核准
                to_human += 1
            elif says_defect and hourly_cap and spent + SHIPPING > hourly_cap:
                to_human += 1                           # 超過本小時的自動退款預算
            else:
                spent += SHIPPING if says_defect else 0
                excess += SHIPPING if says_defect and not is_defect else 0
                auto_log.append((hour, says_defect and not is_defect))
        # ---- 每小時結束時的檢查 ----
        alarm = None
        if kb == "canary":
            (xn, nn), (xo, no) = canary["new"], canary["old"]
            if nn >= 30 and z_two(xn, nn, xo, no) > 3:
                kb = "rolled_back"
                print(f"  {clock(hour)} canary 失敗（新版 {xn}/{nn}，舊版 {xo}/{no} 判為瑕疵），自動回退")
            elif hour - KB_RELEASE >= 5:
                kb = "new"
        window = (window + [flags])[-2:]
        recent = [f for hf in window for f in hf]
        if drift_alert and z_one(sum(recent) / len(recent), base_share, len(recent)) > 4:
            alarm = "漂移告警"
        if hour == DAILY_REVIEW:
            day = [wrong for h, wrong in auto_log if hour - 24 < h <= hour]
            if sum(sampler.sample(day, 200)) / 200 > 0.04:
                alarm = "每日抽樣"
        if alarm and hour > manual_until and kb in ("new", "canary"):
            print(f"  {clock(hour)} {alarm}觸發 → 降級為人工核准 {MANUAL_HOURS} 小時，回退知識庫")
            manual_until, kb = hour + MANUAL_HOURS, "rolled_back"
    print(f"  結果：多付運費 {excess:,} 元（{excess // SHIPPING} 筆誤判），轉人工 {to_human:,} 件\n")


run("基線：兩天內沒有任何知識庫變更", kb_change=False)
run("A 只有金額 invariant＋每日抽樣")
run("B A＋每小時自動退款預算 12,000 元", hourly_cap=12_000)
run("C B＋「判為瑕疵」占比漂移告警", hourly_cap=12_000, drift_alert=True)
run("D C＋知識庫變更先走 5% canary", hourly_cap=12_000, drift_alert=True, kb_canary=True)
```

執行結果：

```text
基線：兩天內沒有任何知識庫變更
  結果：多付運費 9,300 元（93 筆誤判），轉人工 0 件

A 只有金額 invariant＋每日抽樣
  第 2 天 09:59 每日抽樣觸發 → 降級為人工核准 3 小時，回退知識庫
  結果：多付運費 64,200 元（642 筆誤判），轉人工 540 件

B A＋每小時自動退款預算 12,000 元
  第 2 天 09:59 每日抽樣觸發 → 降級為人工核准 3 小時，回退知識庫
  結果：多付運費 52,800 元（528 筆誤判），轉人工 788 件

C B＋「判為瑕疵」占比漂移告警
  第 1 天 18:59 漂移告警觸發 → 降級為人工核准 3 小時，回退知識庫
  結果：多付運費 13,900 元（139 筆誤判），轉人工 928 件

D C＋知識庫變更先走 5% canary
  第 1 天 21:59 canary 失敗（新版 33/59，舊版 345/1141 判為瑕疵），自動回退
  結果：多付運費 9,900 元（99 筆誤判），轉人工 0 件
```

逐段解讀：

1. `make_stream` 先產生兩天內所有對話的「真相」（是否真的是瑕疵）與亂數，四種情境共用同一份資料，差別只在 guardrail。這就是「重放」：真實系統中，這份資料來自事故當天的 trace 與抽樣標註。基線告訴我們，即使沒有任何變更，2% 的誤判率每兩天也會多付約 9,300 元。這是正常的「error budget」，不是事故。
2. 情境 A 就是事故當時的 Harbor。誤判從第一天 18:00 開始，直到第二天早上的抽樣才被發現。扣掉基線，事故多付了約 55,000 元、約 550 筆誤判，和 48.11 的時間線吻合。
3. 情境 B 加上每小時的自動退款預算，只省下約一萬元。原因是預算是固定金額：晚間尖峰時它確實擋下了超出的案件，但深夜流量低，誤判的量本來就在預算之內，所以照樣通過。固定上限能限制**尖峰**的傷害，卻限制不了**持續時間**；它是緩解，不是偵測。
4. 情境 C 的漂移告警在第一個小時結束時就觸發。它比較的是「判為瑕疵的比例」和過去的基線，用的是和第 29 章 canary 分析相同的比例檢定。損失幾乎降到基線附近，代價是降級期間 900 多件案件轉給人工核准，這正是 48.9 容量估算中 `approval` 模式要能承接的量。
5. 情境 D 讓知識庫變更先只影響 5% 的對話。Canary 在四個小時內累積到足夠樣本（新版 59 件中有 33 件判為瑕疵，舊版約 30%），自動回退，損失和基線幾乎沒有差別，而且完全不需要人工介入。代價是新政策要多等幾個小時才全面生效。
6. 這段程式的參數都是假設的，真實系統的誤判率、流量與門檻要從自己的資料推估。但它示範了 postmortem action item 該怎麼驗證：**不是相信新的檢查有效，而是用事故資料重放，量出它能把「多久知道」與「最多錯多少」改善多少**，並同時量出它的代價（轉人工的件數）。

## 48.16 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 每一站都做到最完整 | 小功能被流程壓垮，團隊開始繞過流程 | 一個只改客服回覆文字的功能也要求完整 PRR 與 game day，三週後大家學會把變更藏進「設定調整」 | 依風險分級：動錢、動權限、不可逆的功能走全套；低風險變更用 golden path 的預設值即可 |
| Invariant 當成正確性的保證 | 每一筆都「不離譜」，總和卻錯得很大 | 本次事故：所有退款都在訂單金額內，卻有 550 筆判錯 | Invariant 之外，還要有量測判斷品質的 SLI，以及限制總量的預算 |
| 只把程式碼當成變更 | 行為改變卻沒有新 artifact、沒有 eval、沒有 canary | 知識庫、模型供應商的同名模型、工具描述被更新 | 把所有會改變行為的東西放進 bundle，並以不可變版本引用 |
| 降級路徑沒有算容量 | 事故時唯一的止血選項其實撐不住 | 尖峰時把 AI 全關，人工客服只能接住四成，排隊數小時 | 為每個降級模式估算容量，並在 game day 實際演練 |
| 授權只往上不往下 | 出事後仍維持原本的自主程度，或乾脆全部關掉 | 事故後有人主張「AI 不可靠，全部改回人工」 | 事先寫下降級條件，並依動作類型分別降級（本次只有「瑕疵」退回 L2 重新累積證據） |
| Postmortem action items 沒有驗證方式 | 項目被標成完成，風險其實還在 | 「加強監控」被關閉，但沒人確認新告警在事故情境下會響 | 每項附上可檢查的完成證據，偵測類項目用事故資料重放驗證 |

## 48.17 AI 時代：什麼變了？

這一章本身就是一個 AI 時代的案例，所以這一節不再重複個別技術，而是整理 AI 在這套 operating system 中改變了哪些結構。

**第一，「變更」的定義變大了。** 傳統的 operating system 管的是程式碼與設定；AI 功能的行為還由模型、prompt、工具描述、檢索資料共同決定，而它們常常由不同的人、在不同的系統中修改。本次事故的變更甚至不是工程師做的。實務上的做法是畫出「所有會改變 agent 行為的東西」，逐一確認它們有版本、有 owner、有 eval、會經過 canary；任何一項不符合，就是一個沒有關卡的變更入口。

**第二，測試從布林值變成統計。** Eval 讓「通過」變成一個比例，canary 與漂移偵測都要用統計檢定判斷差異是否真實。這要求團隊具備第 29 章的統計直覺，也要求在確定性與機率性之間畫出清楚的界線：invariant 用確定性的程式與測試保護，判斷品質用統計方法監控。

**第三，三種 AI 同時出現在同一條生命週期。** 在這個 capstone 中，coding agent 起草了大量程式碼與測試；AI 退款助理本身是 production 服務；AI scribe 協助事故處理。三者的共同原則是一樣的：有身份、權限窄、動作可稽核、結果要被人驗證，而且授權依證據逐步擴大。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| Coding agent 起草 gateway、工具定義與測試，並用 production 資料重放比對 | Invariant 的定義與實作由 code owner 核准；作者要能解釋每一行；依賴必須通過 allowlist |
| 從真實工單產生 eval 的候選案例，並依族群、語言分層 | 對抗性案例與通過門檻由資安與產品決定；eval 資料集經過 review 並版本化 |
| 退款助理理解對話、蒐集證據、選擇原因碼並提出 refund intent | 金額、資格與上限由規則引擎計算；超過上限、命中例外或檢索失敗時轉人 |
| 維運 agent 在事故中整理時間線、比對變更紀錄、草擬對外訊息 | IC 逐條確認時間線；對外訊息由 comms 核准；止血動作由人執行或在預先核准的範圍內執行 |
| 從 postmortem 與事故資料草擬 action items 與重放測試 | Action item 的優先順序、owner 與「完成的證據」由人決定；授權等級的升級由 owner 申請、另一位指定的審查者核准，降級依事先寫好的條件自動執行（第 47 章） |

> [!ai] AI 提醒
> 最危險的不是 AI 做錯事，而是 AI 做錯事時系統看起來一切正常。本次事故中，助理的回覆流暢、有禮、引用了「政策文件」，延遲與可用性全部達標。對 AI 功能來說，「有沒有在回應」幾乎從來不是主要風險，「回應的內容是否正確」才是；監控設計要從這一點出發。

## 48.18 專家怎麼想

- **「最多會錯多少？多久會知道？」** 這是 Kevin 的兩個問題，也是資深工程師審視任何高風險功能時最先問的事。前者決定 blast radius 的設計（invariant、上限、預算），後者決定 observability 與告警。兩個問題任何一個沒有具體答案，功能就還沒準備好。
- **先找單向門。** 一個系統裡大部分決定都是可逆的，可以快速嘗試；少數不可逆的動作值得十倍的關注。資深者會先畫出「哪些動作做了就收不回來」，再決定在哪裡放確定性的守門員。
- **訊號的速度要配得上風險的速度。** 一個每小時能造成數千元損失的錯誤，配上 24 小時一次的量測，數學上就注定要損失幾萬元。專家會為每一個主要風險問：最快的訊號是什麼？它多久會到？
- **Artifact 是為下一站寫的。** 判斷一份 design doc、SLO 文件或 postmortem 好不好，看的是下一站的人能不能直接用它：測試能不能從 invariant 寫出來？告警能不能從 SLO 推出來？Action item 能不能被別人驗證？
- **流程要依風險分級，否則會被繞過。** 資深者不會要求每個功能都走完十一站的全套，而是把全套留給動錢、動權限、不可逆的功能，並把其他功能需要的保護做成平台的預設值。
- **每次事故都問「這個教訓會不會只留在這個團隊」。** 如果同類系統還有好幾個，正確的 action item 往往是改平台，而不是改這一個服務。

## 48.19 動手練習

1. 修改 48.15 的程式，把漂移告警的窗口從 2 小時改成 1 小時與 6 小時，門檻從 z > 4 改成 z > 3。記錄偵測時間與「沒有事故時」的誤報次數（提示：用 `kb_change=False` 跑多個不同的 seed），說明你會選哪一組參數。
2. 在 48.15 的程式中把固定的每小時預算改成「與當小時流量成比例」的預算（例如預期瑕疵件數的 1.5 倍），比較它和固定預算在深夜時段的效果差異。
3. 為 Harbor 的另一個 AI 功能「賣家 AI 助理（能幫賣家調整商品價格與庫存）」寫一頁 design doc：列出至少四條 invariant、指出哪些動作是單向門，並說明降級模式。
4. 依 48.10 的格式，為你工作中（或學校專題中）的一個功能做一份 launch checklist，至少包含架構、容量、依賴、監控、回退五類，並誠實標出哪些項目目前無法提供證據。
5. 找一份公開的 postmortem（或用第 1 章的免運事故），依 48.12 的格式重寫 action items：每一項標出預防、偵測或緩解，並寫出「完成的證據」。
6. 列出 AI 退款助理所有「會改變 agent 行為的東西」，至少八項，為每一項標出目前的 owner、版本方式、是否經過 eval 與 canary。找出沒有關卡的入口。

## 本章重點整理

- 一個功能的可靠性來自整條生命週期，從設計、review、測試、發布、SLO、告警、容量、上線審查，到事故與 postmortem，每一站都要留下下一站能直接使用的 artifact。
- 設計高風險功能時，先寫下 invariant 與單向門，再寫功能清單；不可逆的動作必須由模型之外的確定性程式守門。
- 讓模型負責理解與判斷、讓規則引擎負責金額與資格，可以把機率性元件關在確定性的邊界內；模型錯了，最壞結果應該是被拒絕或轉人工。
- 小批次、feature flag 與 shadow 讓功能在接上 agent 之前，就能用 production 資料證明確定性部分的正確性。
- Invariant 由確定性的測試保護，判斷品質由統計性的 eval 保護，兩者不能混用；eval 要多次執行、分層，並在每次事故後補充案例。
- 模型、prompt、工具描述、規則與知識庫都會改變行為，應該打包成有版本、可追溯的 artifact，並走同一條 eval 與 canary 管線。
- AI 功能的 SLO 要包含判斷正確性，零容忍的 invariant 放在 SLO 之外、違反即 page；不設會誘發 Goodhart's law 的目標。
- 訊號的速度要配得上風險的速度；最主要的風險若只有最慢的訊號，事故的持續時間就會由量測週期決定。
- 容量估算要涵蓋 token、同時對話數與模型配額，也要涵蓋降級路徑本身的容量；過載時 AI 對話應是較早被犧牲的工作。
- 降級模式不只有開與關，「改由人核准」常是尖峰時最好的止血選項；授權要能依動作類型分別升降。
- Postmortem 要列出多個促成因素、記下運氣好的地方，action items 同時涵蓋預防、偵測與緩解，並附上可驗證的完成證據，例如用事故資料重放。
- 一個團隊的教訓要變成平台的預設值（golden path），組織的學習成本才不會和團隊數成正比。
- 評估功能是否成功要同時看結果、品質與風險、人的感受三組訊號，避免只看自動化比例。
- 全書可以濃縮成 12 條原則，最後一條是：AI 擴大能力，但不轉移責任。

## 延伸問答

> [!question]- Q1. 為什麼不讓 AI 退款助理直接呼叫 refund-service，而要多一層 refund-gateway？多一個服務不是增加複雜度嗎？
> 確實增加了一個要維運的服務，ADR-041 也把它寫進「後果」。但這一層換來的是一個確定性的邊界：所有會造成單向損失的檢查（累計金額、idempotency、自動上限、訂單歸屬）集中在一處，可以用 unit、property 與 integration test 完整保護，也可以用過去的人工退款重放驗證。
>
> 如果 agent 直接呼叫 refund-service，這些檢查要嘛寫在 prompt 裡（會被誤解或注入），要嘛散落在 refund-service 的各個呼叫者中。更重要的是，agent 的 blast radius 會等於它沿用的客服權限。判斷要不要多一層，關鍵在於「這一層保護的是不是單向門」：保護的是退款這種收不回來的動作，複雜度就值得。

> [!question]- Q2. 事故中 availability 與 latency SLO 全綠，這代表 SLO 設計錯了嗎？
> 不完全是錯，而是不完整。SLI-1 與 SLI-2 量的是「助理有沒有在合理時間內回應」，它們在事故中確實沒有被影響。問題在於這個功能最主要的風險是判斷錯誤，而 SLO 文件中對應的 SLI-3 只有每日抽樣，延遲 24 小時，也沒有任何告警接在它上面。
>
> 第 32 章說過，如果使用者（或公司）很痛但 SLI 沒動，量測就錯了。修正方式不是把可用性目標調高，而是為判斷品質加上一個更快的代理訊號，例如原因碼分佈的漂移、客服駁回率、單位時間的退款總額，並接上告警。這也是 postmortem 第 3 項 action item 的內容。

> [!question]- Q3. 如果你是當晚 21:30 看到異常的夜班客服，而群組裡沒有人回應，你應該怎麼做？組織又該怎麼設計？
> 個人能做的是升級：直接找值班表上的工程師，或在核准佇列中先駁回看起來可疑的案件，並寫下理由。但把責任放在一位夜班客服的勇氣上是不公平的，這位同仁可能不知道誰在值班、擔心打擾別人，或不確定自己的判斷是否值得半夜叫醒工程師。
>
> 組織要做的是讓「回報」比「沉默」更容易：一鍵回報直接開 ticket 給值班者、回報不需要確定是問題、有明確的回應時限，事後也要感謝回報者，即使最後證明是誤報。這是第 9 章心理安全的具體做法，也是 postmortem 第 5 項 action item。第一線人員常常是最早看到異常的人，他們的訊號沒有路可走，是很多事故持續過久的原因。

> [!question]- Q4. 計算題：假設尖峰每小時有 600 件新對話，平均對話 6 分鐘，每次對話平均呼叫模型 5 次、每次輸入 3,000 tokens。要讓尖峰只用到配額的一半，輸入 token 配額至少要多少？同時進行中的對話有幾個？
> 同時進行中的對話用 Little's Law：L = λW。λ = 600 件／小時 = 10 件／分鐘，W = 6 分鐘，所以 L = 60 個對話同時進行。這個數字決定了連線數、session 儲存與並行上限的設計。
>
> 輸入 token 速率是 600 × 5 × 3,000 ÷ 60 = 150,000 tokens／分鐘。要讓它只占配額的 50%，配額至少要 300,000 tokens／分鐘。之所以留一半，是因為每次對話的模型呼叫數變異很大（P95 是平均的兩倍多），依第 36 章的排隊直覺，變異越大越不能把使用率拉高；此外還要考慮 retry 會增加用量，以及配額申請有數週的 lead time，無法在尖峰當下臨時調整。

> [!question]- Q5. 事故後有人主張：「AI 不可靠，退款全部改回人工。」你會怎麼回應？
> 先承認這個主張背後的擔心是合理的：系統在 15 小時內持續做錯事而沒人知道。但全部改回人工有兩個問題。第一，它放棄了已被證明有效的部分：「未出貨取消」「物流遺失」這兩類原因碼的判斷在事故中完全正常，買家的等待時間也從 19 小時變成對話內完成。第二，它沒有修正真正的缺口：知識庫沒有版本與關卡、判斷品質的訊號太慢，這些問題換成人工也不會自動消失，例如人工客服也可能讀到那份草稿政策。
>
> 比較好的做法是依動作類型分別降級：出問題的「瑕疵」原因碼依第 47 章的降級規則退回 L2，先在 shadow 中重新累積證據，再依 rollout 計畫的條件經 L3 晉升回 L4；同時完成偵測與預防的 action items。授權本來就應該能升也能降，而且降級的條件最好事先寫好，避免事故後在情緒中做決定。

> [!question]- Q6. 面試題：如果只能在 AI 退款助理上加一個 guardrail，你會選哪一個？
> 一個好的回答會先說明判斷依據，而不是直接給答案。如果還沒有任何保護，第一個要加的是在模型之外強制的 invariant（例如累計退款不超過已付金額、只能操作本人訂單），因為它防的是單向、無上限的損失，而且完全確定性、容易測試。
>
> 如果 invariant 已經存在（像 Harbor 一樣），下一個最有價值的通常是一個「快的品質訊號」，例如原因碼分佈的漂移告警，因為 48.15 的模擬顯示，偵測速度對總損失的影響遠大於固定上限。回答時可以補充代價：漂移告警會有誤報，需要用歷史資料調門檻，並確保降級路徑有容量承接。能說出「選擇依據、預期效果、代價與驗證方式」，比答案本身更重要。

> [!question]- Q7. 知識庫走 canary 時，canary 只拿到 5% 的流量。如果新政策是正確的、只是讓「判為瑕疵」的比例合理地上升，canary 不就會誤判並回退正確的變更嗎？
> 會，而且這是一個真實的取捨。Canary 偵測的是「行為有沒有改變」，不是「改變是否正確」。如果新政策本來就應該讓瑕疵比例上升（例如法務核准了更寬鬆的退貨規則），canary 一定會看到差異。
>
> 處理方式是讓變更的發布者事先宣告預期的影響：「這份政策預期讓瑕疵比例從約 31% 上升到約 40%」。Canary 比較的就不再是「有沒有差異」，而是「差異是否落在預期範圍內」；超出範圍或方向不對才回退。同時，政策變更應該附上新的 eval 案例，證明 agent 在新政策下的判斷符合預期。這和程式碼的 canary 是同一個道理：第 29 章說 canary 指標要能歸因於變更，預期的變化要事先寫下，否則每一次合理的改變都會被當成事故。

> [!question]- Q8. 小團隊（例如八個人的新創）也需要這十一站嗎？
> 需要的是每一站要回答的問題，不一定是每一站的完整流程與文件。八個人的 Harbor 也應該能回答「最多會錯多少、多久會知道」，也應該把退款的 invariant 寫在程式裡而不是 prompt 裡，也應該有一個能一鍵切回人工的開關。這些是成本很低、但保護很大的部分。
>
> 可以省略或簡化的是規模帶來的部分：正式的 PRR 可以是一次半小時的討論，SLO 文件可以是 README 中的五行，incident command 可以只有兩個角色。第 6 章說過，判斷「現在需要什麼」本身就是工程能力；流程隨規模與風險長大，但原則（invariant 由機器強制、變更可逆、訊號夠快、教訓回到前面的關卡）從第一天就適用。

## 延伸閱讀

- [Site Reliability Engineering — Reliable Product Launches at Scale](https://sre.google/sre-book/reliable-product-launches/)：Launch Coordination Engineering 與 launch checklist 的原始做法，48.10 的參考。
- [Site Reliability Engineering — The Evolving SRE Engagement Model](https://sre.google/sre-book/evolving-sre-engagement-model/)：PRR 與不同 SRE 參與模式的由來。
- [Site Reliability Engineering — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)：blameless postmortem 的原則，48.12 的背景。
- [The Site Reliability Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)：48.8 告警規則中 multi-window multi-burn-rate 參數的來源。
- [OWASP Top 10 for Large Language Model Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)：prompt injection、excessive agency 等 LLM 應用風險的整理，可用來檢查自己的 threat model。
- [NIST AI RMF：Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)：組織層級管理生成式 AI 風險的框架。
- [Software Engineering at Google](https://abseil.io/resources/swe-book)：全書 software engineering 部分的原典，可從第 1 章重讀「隨時間積分」的意義。
