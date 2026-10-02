---
chapter: 2
title: Agent System 全景：十個組成元件
part: 0
---

# 第 2 章　Agent System 全景：十個組成元件

> [!abstract] 本章地圖
> **核心問題**：一個能上線的 agent system 由哪些元件組成？每個元件各自回答什麼問題，彼此之間的資料和控制權又怎麼流動？
>
> **你會學到**：
> - 用 Model／Harness／Environment 三層心智模型，判斷一個問題該在哪一層解決
> - 說出十個組成元件各自回答的問題、缺了它會出現什麼症狀，以及全書哪幾章會深入它
> - 畫出一次請求流經十個元件的時序圖，分清楚「資料流」和「控制流」
> - 拿一份 agent 設計文件逐一盤點元件，找出還沒有人負責的缺口
> - 用 Python 組出一個十元件俱全的極簡骨架，並讀懂它印出的追蹤
> - 看懂 2026 年的生態地圖：模型廠商、SDK、協定、託管 agent 服務、觀測與評估工具各自落在哪個元件
>
> **前置知識**：第 1 章（agent 的定義、workflow 與 agent 的光譜、autonomy 等級）

## 2.1 故事：demo 很成功，然後呢？

青鳥科技的客服 agent v1 是 Iris 花一週做出來的。它能查訂單、查物流、在使用者要求時退款。週五的 demo 上，阿哲親自扮演買家，說「訂單 A1001 的耳機壞了，我要退款」，agent 先查了訂單，確認已送達，退了 490 元，還很有禮貌地說明會退回原信用卡。會議室裡一陣掌聲，阿哲當場決定：下週開始找三家網店內部試用兩週。

試用的第一週就出了四件事。第一件，一位買家前一天被告知「明天會有專人回電」，隔天再問時 agent 完全不記得，還重新問了一次訂單號碼。第二件，ERP 在尖峰時段逾時，Iris 寫的 retry 讓同一筆退款送出了兩次，網店老闆打電話來抱怨帳對不起來。第三件，Iris 為了讓回答更簡潔改了 system prompt，結果 agent 開始跳過「先查訂單再退款」這一步，三天後才被客服主管發現。第四件，Maya 在審查會上問了一句：「這筆退款是誰授權的？如果是買家用話術騙 agent 退的，我們的紀錄能證明什麼？」Iris 答不出來。

阿哲在週會上問：「離正式上線還差多少？」Iris 列出的待辦清單全是 prompt 和 tool 的修改。老陳聽完，走到白板前畫了十個方塊，然後說：「你現在做好的是其中四個半。剛剛那四件事，分別出在另外四個方塊上：記憶、執行環境、評估、治理。改 prompt 修不好它們，因為問題根本不在 prompt 裡。」

```text
 Iris 的 v1（demo 版）                       試用第一週出事的地方

   網頁聊天 ──► while loop ──► 前沿模型          ✗ 隔天不記得承諾        → Memory
                   │                            ✗ 逾時重試，退款兩次     → Runtime／Tools
                   ▼                            ✗ 改 prompt 後漏步驟     → Evaluation
              get_order / refund                ✗ 說不出誰授權了退款     → Guardrails／Governance
```

左邊是 Iris 的 v1：一個聊天元件、一個 loop、一個模型、兩個 tool，這已經是一個貨真價實的 agent。右邊是試用中出的四件事，每一件都指向一個 v1 沒有設計的元件。這張圖的重點是：demo 成功證明「模型能做決定」，但上線需要的是「整個系統在模型做錯、外部系統出錯、有人惡意操作時，仍然可靠、可查、可改」。本章就是老陳那塊白板：先建立整體地圖，後面四十多章再逐一深入每個方塊。

## 2.2 從一個 loop 到一個 system

第 1 章把 agent 定義成「模型在 loop 中自己決定下一步、自己決定何時停止」的系統。這個定義抓住了 agent 和一般程式最不一樣的地方，但它只描述了系統的心臟。心臟能跳，不代表人能跑馬拉松；loop 能轉，也不代表 agent 能在 production 裡連續服務數千家網店。

為什麼需要把系統拆成元件？因為 agent 的失敗很少只有一個原因。退款退了兩次，表面上是 tool 的問題，追下去會發現同時牽涉 runtime 的重試策略、tool 缺少 idempotency key（同一個請求重複送出也只生效一次的識別碼）、guardrail 沒有「同一訂單只能退一次」的規則，以及評估集裡沒有「外部系統逾時」這類案例。如果腦中只有「prompt＋模型＋tools」三個詞，除錯時就只能在這三個地方打轉。

所謂**元件（component）**，在本書指的是「一個必須有人負責回答的設計問題」，而不是一個獨立部署的服務。舉例來說，「這一輪模型看到什麼？」是 context 元件的問題；v1 裡它的答案是「system prompt 加完整對話」，只是一行程式，但那仍然是一個設計決策，而且是會在長對話時壞掉的決策。元件可以全部塞在同一個 Python process 裡，也可以拆成十幾個服務；拆不拆是部署問題，有沒有人回答它才是設計問題。

這種思考方式和傳統 system design 很像：設計一個電商網站時，你會分別問「資料存哪裡、快取放哪裡、流量怎麼分、出錯怎麼辦」。agent system 多了一個特殊角色：一個會自己做決定、但偶爾會判斷錯誤的模型。所以大部分元件的存在理由，都可以歸結成一句話：**讓模型的決定變得有用，同時讓它的錯誤變得有界、可見、可修**。

## 2.3 三層心智模型：Model、Harness、Environment

在進入十個元件之前，先用一個更粗的三層模型建立直覺。這三層的分法來自業界對 coding agent 與託管 agent 服務的公開討論，本書把它整理成判斷「問題該在哪裡修」的工具。

**Model（模型層）** 是做決定的那一層：讀進一段 context，輸出文字或 tool call。你通常無法改它的權重，只能選擇用哪個模型、用什麼參數（例如推理強度）、給它什麼輸入。**Harness（駕馭層）** 是包住模型的程式：loop、prompt 組裝、tool 的定義與分派、停止條件、context 管理、錯誤處理。「harness」原意是馬具，意思是把一匹有力但不受控的馬接到馬車上；這個比喻很貼切，因為 harness 的工作就是把模型的能力導向有用的方向。**Environment（環境層）** 是 agent 行動的對象與場地：ERP、資料庫、檔案系統、瀏覽器、sandbox，以及在另一端看著結果的人。

```text
 ┌──────────────────────────────────────────────────────────────┐
 │ Environment（環境層）：agent 行動的對象與場地                  │
 │   ERP、物流 API、資料庫、檔案系統、sandbox、瀏覽器、真人審核者    │
 │      ▲  動作（tool 呼叫的實際效果）       │ 觀察（tool result）  │
 │ ┌────┼───────────────────────────────────┼────────────────────┐ │
 │ │ Harness（駕馭層）：包住模型的程式         ▼                    │ │
 │ │   loop、prompt 組裝、tool 分派、停止條件、context 管理、權限   │ │
 │ │      ▲ 決定（文字或 tool call）     │ context（這一輪的輸入） │ │
 │ │ ┌────┼──────────────────────────────┼─────────────────────┐ │ │
 │ │ │ Model（模型層）：讀 context，決定下一步 ▼                 │ │ │
 │ │ └─────────────────────────────────────────────────────────┘ │ │
 │ └─────────────────────────────────────────────────────────────┘ │
 └──────────────────────────────────────────────────────────────┘
```

這張圖由內往外讀。最內層的模型只做一件事：拿到 harness 組好的 context，吐出一個決定。中間的 harness 把這個決定翻譯成真正的動作，送到最外層的環境；環境回傳的觀察（例如 ERP 回的訂單資料）再由 harness 整理後放進下一輪的 context。注意箭頭從不直接連接模型和環境：模型永遠不會「自己」碰到 ERP，所有動作都經過 harness。這正是能在 harness 裡加上權限檢查、在環境裡加上 sandbox 的原因。

三層模型最實用的地方，是讓除錯有方向。回到青鳥的四件事：「改 prompt 後漏步驟」是 harness 的問題（prompt 屬於 harness），也是評估的問題；「退款兩次」是 harness 的重試策略和環境的 idempotency 一起造成的；「說不出誰授權」是環境層缺少稽核紀錄。沒有一件是「模型不夠聰明」。業界有一句常被引用的觀察：多數 agent 失敗出在系統設計與驗證，而不是模型本身。第 34 章會用研究文獻整理的 failure taxonomy 印證這一點。

| 層 | 包含什麼 | 誰能改、多常改 | 典型錯誤歸因 |
|---|---|---|---|
| Model | 模型選擇、推理強度等參數、模型本身的能力 | 換模型是一個設定，但影響全面；廠商每隔幾個月就推新版 | 把 harness 的 bug 誤認為「模型太笨」，急著換模型 |
| Harness | loop、system prompt、tool schema、context 策略、停止條件、權限檢查 | 自己的程式碼，每週都在改 | 用越來越長的 prompt 補洞，卻沒有 eval 確認是否真的變好 |
| Environment | 外部系統、sandbox、資料、真人審核者 | 常由其他團隊擁有，改動慢 | 假設外部系統可靠、操作可重做，沒有設計逾時與重複送出 |

表格的第三欄提醒一件事：三層的改動頻率差很多。模型會在你不注意時變強（或變得不一樣），harness 每週都在改，環境則常屬於別的團隊。好的設計會讓每一層的改變不會悄悄弄壞其他層，例如換模型前跑 eval（第 27 章）、harness 改 prompt 時有版本紀錄（第 6 章）、環境的寫入操作都帶 idempotency key（第 5 章）。

> [!warning] 常見誤解
> 「模型越來越強，harness 會消失。」實際上變薄的是 harness 中「補模型弱點」的部分，例如冗長的禁止事項、強迫模型先規劃的提示；但權限、sandbox、稽核、成本控制這些「對環境負責」的部分不會因為模型變強而消失，反而因為模型能做的事變多而更重要。第 30 章會談怎麼隨模型升級安全地刪減 harness。

## 2.4 十個組成元件總覽

三層模型適合定位問題，但要真正設計和分工，需要更細的拆法。本書把 agent system 拆成十個元件，每個元件回答一個設計問題。下圖是全書最重要的一張架構圖，之後每一章開頭都可以回來看「我們現在在哪個方塊」。

```text
                         ⑧ Interfaces（UI／API／協定：MCP、A2A、AG-UI）
                                   │ 請求進來、事件串流出去
                                   ▼
 ⑩ Guardrails／Governance ──► ⑥ Orchestration（routing、workflow、multi-agent、人工審核）
   輸入檢查、動作政策、             │ 交給某個 agent 或某一步
   身分授權、稽核                   ▼
      │  ┌────────────────── ② Harness／Loop ──────────────────┐
      │  │                                                      │
      ├─►│  ④ Context 組裝 ──► ① Model ──► 決定：tool call／回答  │◄── ⑤ Memory
      │  │       ▲                              │                │    （跨 session
      │  │       │ tool result 回填             ▼                │      的事實與偏好）
      └─►│       └──────────────── ③ Tools（schema、分派、副作用）│
         └───────────────────────────────────┬──────────────────┘
                                             ▼ 實際執行
                          ⑦ Runtime／Sandbox（執行環境、隔離、session log、durability）
                                             │
                                             ▼
                                 外部系統：ERP、物流、資料庫、檔案系統

 ⑨ Evaluation（eval、tracing、監控）──── 觀察以上所有元件，回饋給設計與上線決策
```

先看中間的大框：② harness 包住 ④ context、① model、③ tools，形成第 1 章講的那個 loop。⑤ memory 在框外，因為它跨越 session 存在，每次只由 context 挑一部分帶進來。框的下方是 ⑦ runtime，tool 的實際執行和 session 紀錄都發生在這裡；再往下才是外部系統。框的上方，⑧ interfaces 是請求的入口與結果的出口，⑥ orchestration 決定請求交給哪個 agent、按什麼流程走。左邊的 ⑩ guardrails 不只一個箭頭：它在入口檢查輸入、在 tool 執行前檢查動作、在 orchestration 層決定什麼需要人工核准。最底下的 ⑨ evaluation 不在請求的路徑上，而是觀察整個系統，把觀察結果回饋到設計與上線決策。

下面這張表是十個元件的速查表，也是本章其餘部分的索引。「缺了會怎樣」一欄特別值得記住，因為在 production 裡你通常是先看到症狀，再回推是哪個元件缺席。

| # | 元件 | 回答的問題 | 缺了會怎樣 | 全書深入章節 |
|---|---|---|---|---|
| ① | Model | 誰來決定下一步？用哪個、多強、多貴？ | 成本或延遲失控，或能力不足卻怪到 prompt 頭上 | 第 3、25 章 |
| ② | Harness／Loop | loop 怎麼跑、什麼時候停、出錯怎麼辦？ | 無限迴圈、例外讓整個請求崩潰、提早宣告完成 | 第 4、8、24 章 |
| ③ | Tools | agent 能做哪些動作、怎麼描述給模型？ | 選錯 tool、參數亂填、重複執行有副作用的動作 | 第 5、13 章 |
| ④ | Context | 這一輪模型看到什麼、按什麼順序？ | 長對話變笨、成本隨輪數暴增、cache 命中率低 | 第 9、10、11 章 |
| ⑤ | Memory | 跨 session 要記得什麼、何時忘記？ | 每次都從零開始，或記住錯誤與不該記的個資 | 第 12 章 |
| ⑥ | Orchestration | 誰做哪一段、按什麼流程、何時交給人？ | 單一 agent 被塞進太多職責，或 multi-agent 互相打架 | 第 18–22 章 |
| ⑦ | Runtime／Sandbox | 動作在哪裡執行、怎麼隔離、crash 後怎麼接續？ | 程式碼碰到不該碰的檔案、部署一次就丟掉進行中的任務 | 第 16、17、22 章 |
| ⑧ | Interfaces | 誰怎麼呼叫它、結果怎麼送出、怎麼和別的系統互通？ | 只能在一個網頁用，每接一個系統都重寫一次整合 | 第 14、15、37 章 |
| ⑨ | Evaluation | 怎麼知道它做對了、改了之後有沒有變好？ | 改 prompt 漏步驟三天後才被發現 | 第 27–30 章 |
| ⑩ | Guardrails／Governance | 什麼不准做、誰授權、出事時怎麼追查？ | 被話術騙去退款、資料外洩、說不出誰授權了動作 | 第 21、31–34 章 |

設計審查時，老陳的做法很簡單：把這十個問題逐一念出來，問「目前是誰、用什麼方式回答它」。答不出來的，就是缺口。下面這段小程式把這個流程寫成十幾行，拿 Iris 的 v1 設計文件來跑一次。

```python
# 十個元件各自回答一個問題；設計審查時，把「誰負責回答」逐一填上。
COMPONENTS = {
    "model": "誰來決定下一步？",
    "harness": "loop 怎麼跑、何時停？",
    "tools": "agent 能做哪些動作？",
    "context": "這一輪模型看到什麼？",
    "memory": "跨 session 要記得什麼？",
    "orchestration": "誰做哪一段、交給誰？",
    "runtime": "動作在哪裡、用什麼隔離執行？",
    "interfaces": "誰怎麼呼叫它、結果怎麼送出去？",
    "evaluation": "怎麼知道它做對了？",
    "guardrails": "什麼不准做、出事誰負責？",
}

# Iris 的 v1 設計文件：只寫了 demo 用得到的部分。
iris_v1 = {
    "model": "前沿模型 API",
    "harness": "while loop，最多 10 步",
    "tools": "get_order、refund",
    "context": "system prompt＋完整對話",
    "interfaces": "網頁聊天元件",
}


def audit(design: dict[str, str]) -> list[str]:
    return [f"{name:<13} 沒有答案：{q}" for name, q in COMPONENTS.items() if name not in design]


gaps = audit(iris_v1)
print(f"已覆蓋 {len(iris_v1)}/10 個元件，缺口：")
print("\n".join(gaps))
assert len(gaps) == 5 and gaps[0].startswith("memory")
```

```text
已覆蓋 5/10 個元件，缺口：
memory        沒有答案：跨 session 要記得什麼？
orchestration 沒有答案：誰做哪一段、交給誰？
runtime       沒有答案：動作在哪裡、用什麼隔離執行？
evaluation    沒有答案：怎麼知道它做對了？
guardrails    沒有答案：什麼不准做、出事誰負責？
```

輸出列出五個缺口，正好對應試用第一週的事故，外加一個 orchestration。老陳說 Iris 做好了「四個半」，那半個是 interfaces：網頁聊天元件能用，但網店老闆想接 LINE 時就要重寫。orchestration 在 v1 裡「沒有答案」其實也是一種合理答案（只有一個 agent，不需要 routing），重點是要明確寫下「目前不需要，因為……」，而不是沒想過。這段程式當然太簡化了，真正的審查要看每個答案的品質；第 35 章會把它擴充成完整的設計審查流程。

## 2.5 決策核心：Model、Harness、Tools

前三個元件構成 agent 的最小可運作單位。第 4 章會用 100 行程式把它們組起來；這一節先說明每個元件為什麼存在、真實系統長什麼樣，以及最常見的誤解。

### ① Model：做決定的元件

**為什麼需要**：agent 和 workflow 的差別，就在於下一步由模型決定。模型是系統裡唯一能讀懂「耳機壞了，想退款」這種自然語言、並把它轉成「先查 A1001 的訂單」的元件。**怎麼運作**：每一輪，模型收到 harness 組好的輸入（system prompt、對話、tool 定義），輸出文字、tool call，或兩者都有，並附上一個停止原因，例如 `end_turn`（說完了）或 `tool_use`（要呼叫工具）。

**真實系統長什麼樣**：production 系統很少只用一個模型。常見的配置是一個前沿模型負責主要推理，一個小型快速模型負責分類、摘要、guardrail 判斷這類量大但簡單的工作。推理模型（reasoning model，回答前會先產生內部推理的模型）還多了一個旋鈕：推理強度。推理越深，品質通常越好，但延遲和成本也越高。第 3 章會解釋這些參數背後的原理，第 25 章會實作依難度與成本路由的 model router。

**取捨與誤解**：最常見的誤解是「選最強的模型就對了」。在青鳥的情境裡，查物流這種單步任務用小模型就夠，延遲從數秒降到一秒內，成本差距可以到一個數量級。反過來，把需要多步判斷的退款爭議交給小模型，省下的成本會在轉人工與客訴中加倍付出。模型選擇是一個要用 eval 數據回答的問題，不是憑印象。

### ② Harness／Loop：讓模型的決定變成行動

**為什麼需要**：模型只會輸出「我想呼叫 refund，參數是 A1001 和 490」，它不會自己執行，也不會自己決定「已經跑了 30 輪，該停了」。harness 就是負責這些事的程式。**怎麼運作**：最核心的 loop 只有四步：呼叫模型 → 如果有 tool call，就執行並把結果回填到對話 → 檢查停止條件 → 重複。停止條件至少有三種：模型說完了、超過最大步數、超過 token 或金額預算。

**真實系統長什麼樣**：公開資料顯示，主流 coding agent 的核心都是單一主 loop。例如 Claude Code 的官方文件把它描述成「收集 context → 採取行動 → 驗證結果」三個階段交錯進行；OpenAI 的 agent 建構指南也把一次 run 定義為「loop 直到滿足結束條件」，結束條件包括沒有 tool call、呼叫了最終輸出 tool、錯誤或達到最大輪數。差異化不在 loop 本身，而在 loop 周圍的錯誤處理、context 管理與權限。

**取捨與誤解**：第一個誤解是「loop 很簡單，所以 harness 不重要」。loop 確實簡單，但 harness 的預設值會直接左右品質，例如預設推理強度、tool 回傳的截斷長度、哪些舊訊息要清掉。第二個誤解是把所有邏輯都塞進 harness 的 if-else：當你發現 harness 裡有一長串「如果使用者說 X 就做 Y」，那部分大概應該變成 workflow（⑥）或 tool 的設計（③）。第 8 章會比較 ReAct、plan-and-execute 等 loop 形態，第 24 章處理串流、並行與取消。

### ③ Tools：agent 能做的動作

**為什麼需要**：沒有 tool 的模型只能說話；tool 讓它能查資料、改狀態、和外部系統互動。**怎麼運作**：每個 tool 有名稱、給模型看的描述、參數的 JSON Schema（描述參數型別與限制的標準格式），以及真正執行的程式。模型依描述決定要不要呼叫、填什麼參數，harness 依名稱找到實作並執行。

**真實系統長什麼樣**：Anthropic 在 2024 年的〈Building effective agents〉一文中提出 ACI（agent-computer interface，給 agent 用的介面）的說法，主張花在 tool 設計上的心力應該和設計人機介面一樣多。成熟的系統還會替每個 tool 標上副作用等級：唯讀（查訂單）、可逆的寫入（建立草稿）、不可逆或對外的動作（退款、寄信）；第 5 章把這三級正式命名為 read、write、destructive，並規定未標註的 tool 一律當 destructive。這個等級會被 guardrails（⑩）和人工審核（⑥）使用。當 tool 數量上百時，還需要 tool search 與延遲載入，避免所有定義擠爆 context，這是第 13 章的主題。

**取捨與誤解**：最常見的錯誤是把既有 API 一對一包成 tool。ERP 有 40 個 endpoint，不代表 agent 需要 40 個 tool；把「查訂單＋查物流＋查退款紀錄」合成一個 `get_order_overview`，往往比讓模型自己組合三個 CRUD 呼叫更準、更省 token。第 5 章會用青鳥的訂單與退款 tool 重構示範這件事。

## 2.6 資訊管理：Context 與 Memory

Context 和 memory 最常被混為一談。一個簡單的分法是：context 是「這一輪模型眼前的桌面」，memory 是「桌子旁邊的檔案櫃」。桌面大小有限，每一輪都要重新整理；檔案櫃可以很大，但要有人決定什麼放進去、什麼拿出來。

### ④ Context：這一輪模型看到什麼

**為什麼需要**：模型每一輪只看得到 context window（模型單次能讀入的 token 上限）裡的內容。而且研究與實務都觀察到 **context rot**：context 越長，模型越容易漏看或誤用其中的資訊，這是逐漸下滑的斜坡，不是到了上限才突然壞掉。所以「放什麼、不放什麼」是一個主動的設計，而不是把所有東西都塞進去。

**怎麼運作**：典型的 context 由穩定到動態依序排列：最前面是幾乎不變的 system prompt 與 tool 定義，中間是這個 session 的摘要與記憶片段，最後是最近幾輪對話與 tool 結果。這個順序和 **prompt caching**（模型服務把相同前綴的計算結果快取起來，下次重複使用，以降低成本與延遲）直接相關：前綴越穩定，cache 命中率越高。

```text
 ┌─────────────────────────────────────────────┐  ← 穩定前綴（每輪相同，可快取）
 │ system prompt：角色、規則、退款政策            │
 │ tool 定義：get_order、get_shipment、refund    │
 ├─────────────────────────────────────────────┤  ← 半穩定（每個 session 變一次）
 │ 記憶片段：「u42 偏好退回原信用卡」              │
 │ 先前對話的摘要（compaction 的產物）            │
 ├─────────────────────────────────────────────┤  ← 動態（每輪都變）
 │ 最近幾輪：使用者訊息、tool call、tool result    │
 │ 本輪新訊息：「那物流單號是多少？」              │
 └─────────────────────────────────────────────┘
```

這張圖由上往下讀，就是 context 從「最不常變」到「每輪都變」的排列。上層一旦在 session 中途被改動，例如為了「節省 token」臨時刪掉一個 tool 定義，後面所有內容的 cache 都會失效，反而更貴。中層是 memory（⑤）與 compaction 的交會點：記憶系統挑出相關事實，compaction 把太長的舊對話壓成摘要。下層則是 harness 每輪 append 的新內容。第 9 章會用 token 計數與視覺化工具量測這個版面，第 10 章處理長任務的 compaction，第 11 章則說明檢索（retrieval）怎麼把知識庫內容按需放進中層或下層。

**真實系統與取捨**：Anthropic 的 context engineering 文章把目標描述為「找出最小但訊號最強的 token 集合」；託管 agent 服務的公開設計則把完整的 session log 和 context window 刻意分開，context 只是 log 的一個可重建視圖。這帶出一個重要取捨：compaction 會丟資訊而且不可逆，所以完整紀錄應該存在 runtime（⑦）的 session log，context 只放當下需要的部分。常見誤解是「context window 有一百萬 token，就不需要管理 context」，window 變大只是讓 context rot 晚一點出現，成本卻照樣隨長度增加。

### ⑤ Memory：跨 session 要記得什麼

**為什麼需要**：context 在 session 結束時就消失了。試用中「隔天不記得承諾」的事故，就是因為 v1 沒有任何跨 session 的儲存。**怎麼運作**：memory 系統至少要回答三個問題：什麼時候寫入（每輪都記，還是任務結束時萃取）、記什麼（事實、偏好、做過的事、做事的方法）、什麼時候讀出與遺忘。常見的分類有三種：**episodic memory**（發生過的事件，例如「上週承諾回電」）、**semantic memory**（事實與偏好，例如「偏好退回原信用卡」）、**procedural memory**（怎麼做事，例如一份處理退貨爭議的步驟說明）。

**真實系統與取捨**：2025–2026 年的明顯趨勢是記憶往「檔案系統」收斂：coding agent 用專案裡的說明檔當長期記憶，模型廠商提供讓模型自己讀寫記憶目錄的 memory tool，Agent Skills（可按需載入的指令與腳本包）則被視為 procedural memory 的產品化。取捨在於寫入政策：記太少會健忘，記太多會讓錯誤或過期資訊污染之後的每一次對話，還會碰到個資刪除權的問題。常見誤解是「memory 就是向量資料庫」，向量檢索只是讀取方式之一，寫入政策與衝突處理才是難點。第 12 章會完整處理這些問題。

## 2.7 執行與編排：Orchestration 與 Runtime

前五個元件讓「一個 agent」能好好工作。接下來兩個元件處理「多個步驟、多個 agent、長時間執行」帶來的問題。

### ⑥ Orchestration：誰做哪一段、交給誰

**為什麼需要**：真實的業務很少只有一種任務。青鳥的客服入口同時會收到退款、物流查詢、商品問答、帳號問題，把所有 tool 和規則都塞給同一個 agent，context 會變大、選錯 tool 的機率會上升。orchestration 負責決定「請求交給誰、按什麼流程走、何時停下來等人」。

**怎麼運作**：光譜的一端是確定性的 workflow：規則式 routing、prompt chaining（把任務拆成固定的幾步，每步一次模型呼叫）、平行處理；另一端是由模型動態決定的 multi-agent：orchestrator 把子任務派給 subagent、agent 之間 handoff（把對話控制權交給另一個 agent）。**human-in-the-loop**（在流程中安排真人審核或接手的設計）也屬於 orchestration：退款超過門檻時，流程暫停，等主管核准後再繼續。

**真實系統與取捨**：Anthropic 在〈Building effective agents〉整理了五種 workflow pattern，第 18 章會逐一實作；LangGraph、Google ADK、Microsoft Agent Framework 等主流框架都同時提供「模型自主的 agent」與「確定性的 graph」兩種模式，並允許互相嵌套。Microsoft Agent Framework 的官方文件甚至直接寫著：如果能寫一個函式處理任務，就寫函式，不要用 agent。最常見的錯誤是太早上 multi-agent：多個 agent 之間要共享 context，每多一個 agent，token 成本與協調失敗的機會都跟著增加。第 20 章會說明什麼情況值得（可平行、讀多寫少），什麼情況不值得（緊耦合的寫入）。

### ⑦ Runtime／Sandbox：動作在哪裡執行

**為什麼需要**：tool 的程式碼總要在某個地方執行。查訂單只是一次 HTTP 呼叫，但當 agent 能執行自己寫的程式碼（例如第 17 章的報表 agent），「在哪裡執行」就變成安全問題；當任務要跑二十分鐘，「部署時進行中的任務怎麼辦」就變成可靠性問題。試用中「退款兩次」的事故，就是 runtime 在逾時後盲目重試造成的。

**怎麼運作**：runtime 元件包含三件事。第一是**執行環境與隔離**：一般 tool 在服務的 process 裡執行；會跑任意程式碼的 tool 必須進 **sandbox**（隔離的執行環境，限制它能讀的檔案、能連的網路、能用的資源），隔離強度從 process、container 到 microVM 不等。第二是 **session 狀態與事件紀錄**：每一次模型呼叫、tool 呼叫與結果都寫進一份 append-only（只新增、不修改）的 session log，讓系統能恢復、重播與稽核。第三是 **durable execution**（可持久執行：crash 或重新部署後，從上次記錄的位置接續，而不是從頭來過）。

**真實系統與取捨**：公開資料顯示，主流 coding agent CLI 在本機用作業系統內建的 sandbox 機制限制檔案寫入與網路，雲端的託管服務則多半為每個 session 配置獨立的 container 或 microVM。Temporal、Restate 等 durable execution 系統都有 agent 整合範例，把每次模型呼叫與 tool 呼叫當成一個可記錄、可重播的步驟。取捨在於隔離越強，啟動越慢、成本越高；所以常見做法是「只在需要執行程式碼時才配置 sandbox」。常見誤解是「sandbox 是安全的全部」，sandbox 只限制了程式碼能碰到什麼，不限制 agent 透過合法 tool 能做什麼，那是 guardrails（⑩）的工作。

## 2.8 對外與把關：Interfaces、Evaluation、Guardrails

最後三個元件決定 agent 能不能被使用、能不能被信任、能不能被持續改進。它們最常在 demo 階段被省略，也最常是上線卡關的原因。

### ⑧ Interfaces：誰怎麼呼叫它

**為什麼需要**：agent 總要被某人或某系統呼叫，結果也總要送到某個地方。網店老闆問「能不能接 LINE」，就是在問 interfaces。**怎麼運作**：本書把 interfaces 分成三個方向。**面向使用者**：聊天 UI、串流回應、顯示進度與計畫、讓使用者核准或撤銷。**面向應用程式**：同步 API、非同步任務 API（送出任務、查詢狀態、收 webhook）、事件串流。**面向其他系統的協定**：讓 agent 連接工具與資料的 **MCP**（Model Context Protocol）、讓 agent 和 agent 互通的 **A2A**（Agent2Agent）、讓 agent 後端和前端交換事件的 **AG-UI**。

MCP 需要特別說明，因為它橫跨兩個元件：MCP server 提供的是 tool（③），但「用什麼協定把 tool 接進來」是 interface 的決策。用一個標準協定的好處是，同一個 ERP MCP server 可以同時給客服 agent、內部 coding agent 和 IDE 使用，不必各寫一次整合。

**取捨與誤解**：同步聊天介面最直覺，但不適合要跑十分鐘的任務；非同步介面能處理長任務，卻需要設計進度通知與中途接手。常見誤解是「協定選好了，整合就完成了」，協定只規定訊息格式，授權、錯誤處理與 tool 品質仍然是你的責任。第 14、15 章深入 MCP、A2A 與 AG-UI，第 37 章談使用者體驗與信任設計。

### ⑨ Evaluation：怎麼知道它做對了

**為什麼需要**：agent 的輸出是開放的、非確定性的，而且同一個改動可能讓 A 類任務變好、B 類任務變差。「改 prompt 後漏步驟三天才發現」就是沒有 eval 的直接後果。**怎麼運作**：evaluation 元件包含離線評估與線上觀測兩部分。離線評估用一組代表性任務（eval set）跑 agent，用程式檢查最終狀態（例如資料庫裡是否真的只有一筆退款），或用另一個模型當評審（LLM-as-judge）。線上觀測則靠 **trace**（把一次請求中每個模型呼叫、tool 呼叫的輸入、輸出、耗時、token 都記錄成樹狀結構）與監控指標。本書把 observability 歸在這個元件，因為 trace 是評估與除錯的共同原料。

**真實系統與取捨**：業界共識是評估以 outcome（環境的最終狀態）為主、trajectory（agent 走過的步驟）為輔，因為 agent 說「已退款」不代表真的退了。可靠度則要看 pass^k（同一題跑 k 次全部成功的比例），而不只看 pass@k（k 次中至少成功一次）。客服 agent 每天處理數千次對話，「十次裡偶爾錯一次」在規模上就是每天數百個錯誤。第 27 章實作 eval harness，第 28 章解讀公開 benchmark，第 29 章實作 tracer，第 30 章用 eval 驅動優化。

> [!note] 2026 現況
> 截至 2026 年 10 月，一個公開案例說明了 harness 預設值與 eval 的關係：Anthropic 在 2026-04-23 的 postmortem 中說明，Claude Code 曾為了降低延遲把預設推理強度從 high 調成 medium，使用者明顯感覺品質下降，之後回滾；另一個 cache 優化的 bug 讓舊的推理內容在每一輪被裁掉，造成健忘與重複。該文的結論是：任何可能和智慧程度互相取捨的改動，都要做逐模型的 eval、觀察期與漸進式 rollout。

### ⑩ Guardrails／Governance：什麼不准做、出事誰負責

**為什麼需要**：模型會被騙。**prompt injection**（把惡意指令藏在使用者輸入或 tool 回傳的內容裡，誘使模型做出開發者不允許的事）目前沒有可靠的模型層解法。所以凡是不能出錯的規則，例如「單筆退款超過 500 元要人工核准」，必須由模型之外的確定性程式執行，而不是寫在 prompt 裡拜託模型遵守。Maya 問的「誰授權了這筆退款」，則是治理問題：系統必須能證明每個動作代表誰、依據什麼權限、在什麼時間發生。

**怎麼運作**：guardrails 分布在請求路徑的多個位置：入口的輸入檢查、tool 執行前的動作政策（依副作用等級與參數決定放行、拒絕或送審）、輸出前的檢查（例如遮蔽個資）。governance 則在更高的層次：agent 的身分與授權（代表哪位使用者、拿到哪些 scope）、稽核日誌、風險分級與上線審查流程、法規要求。

**真實系統與取捨**：安全研究者 Simon Willison 提出的 **lethal trifecta** 是一個好用的判斷工具：當一個 agent 同時能讀私有資料、會接觸不可信的內容、又能對外傳送資料時，就存在資料外洩的結構性風險，應該在架構上切斷其中一邊。各大託管 agent 平台也普遍把政策檢查放在 tool gateway 這類確定性的位置，和模型推理分開。取捨在於規則太嚴，agent 動不動就轉人工，使用者體驗變差；太鬆又有風險。常見誤解是「加一個安全分類器就好」，分類器是第二道防線，第一道防線是權限切分與環境隔離。第 31–34 章會從威脅模型講到治理流程。

## 2.9 資料流與控制流：一次請求走過十個元件

元件拆完了，接下來要看它們怎麼連起來。描述元件之間的關係有兩個視角：**資料流**（什麼資訊從哪裡流到哪裡）與**控制流**（誰決定下一步做什麼）。在一般的後端服務裡，兩者幾乎重合，程式碼寫什麼順序就做什麼。agent 的特別之處在於，控制權有一部分交給了模型，所以必須刻意設計「其他元件在什麼時候可以收回控制權」。

下面是青鳥客服 agent 處理一次退款請求的時序圖，假設金額在自動核准的門檻之內（第 1 章 L4「500 元以下退款自動」的邊界）。

```text
 步驟  發起者 ──► 接收者                    傳遞的內容／做的決定
 ────  ───────────────────────────────  ─────────────────────────────────────
  1    使用者 ──► ⑧ Interface              「訂單 A1001 的耳機壞了，想退款」
  2    ⑧ Interface ──► ⑩ Guardrail         輸入檢查：通過
  3    ⑩ Guardrail ──► ⑥ Orchestration     路由：交給客服 agent
  4    ⑥ Orchestration ──► ② Harness       啟動 loop（最多 N 步、預算 B）
  5    ② Harness ──► ④ Context ◄── ⑤ Memory 組裝輸入，帶入「偏好退回原信用卡」
  6    ② Harness ──► ① Model               第 1 輪 → tool_use: get_order(A1001)
  7    ② Harness ──► ⑩ Guardrail           唯讀動作：放行
  8    ② Harness ──► ⑦ Runtime／③ Tools    查 ERP，寫 session log，結果回填
  9    ② Harness ──► ① Model               第 2 輪 → tool_use: refund(A1001, 490)
 10    ② Harness ──► ⑩ Guardrail           不可逆寫入：檢查金額 ≤ 門檻，放行
 11    ② Harness ──► ⑦ Runtime／③ Tools    帶 idempotency key 退款，寫 session log
 12    ② Harness ──► ① Model               第 3 輪 → end_turn
 13    ② Harness ──► ⑤ Memory              寫入「A1001 已退款」
 14    ② Harness ──► ⑧ Interface ──► 使用者  串流回覆
  *    每一步 ──► ⑨ Evaluation／Trace       記錄 span；請求結束後檢查 outcome
```

逐步讀這張圖。步驟 1–3：使用者的訊息先到 interface，經過 guardrail 的輸入檢查，再由 orchestration 決定交給客服 agent（目前只有一個 agent，所以這一步很單純，但它保留了日後加入物流 agent 的位置）。步驟 4–5：harness 接手後，向 context 元件要這一輪的輸入，context 從 memory 挑出相關事實。步驟 6–8：模型第一次回應要呼叫 `get_order`，harness 先問 guardrail，唯讀動作直接放行，再交給 runtime 執行並寫入 session log。步驟 9–11：結果回填後進入下一輪，模型要求 `refund`，guardrail 這次要檢查金額，通過後 runtime 帶著 idempotency key 執行退款。步驟 12–14：模型第三次回應 `end_turn`，harness 把新事實寫進 memory，interface 把回覆串流給使用者。最後一列的 evaluation 不參與決策，但每一步都留下紀錄。

把同一個請求換成兩個視角整理，可以看出哪些元件「搬資料」、哪些元件「做決定」：

| 元件 | 在資料流中的角色 | 在控制流中的角色 |
|---|---|---|
| Interface | 接收請求、輸出串流事件 | 決定請求能不能進來（認證、限流） |
| Orchestration | 傳遞任務描述與共享狀態 | 決定交給哪個 agent、何時暫停等人 |
| Harness | 搬運 messages、tool result | 執行停止條件，最終決定 loop 是否繼續 |
| Context／Memory | 決定模型看到哪些資訊 | 不直接決定，但「看不到」等於間接控制 |
| Model | 產生文字與 tool call | 在允許範圍內決定下一步，是唯一的非確定性決策者 |
| Tools／Runtime | 讀寫外部系統、記錄 session log | 可以回報錯誤或逾時，讓 loop 改道 |
| Guardrails | 檢查輸入、動作、輸出 | 擁有否決權：可以拒絕、改送人工審核 |
| Evaluation | 收集 trace 與結果 | 不在單次請求中控制，但控制「改動能不能上線」 |

這張表最重要的一列是 model：它是唯一的非確定性決策者，而其他元件的控制權都是確定性的。好的 agent 設計就是把這兩種控制權擺在對的位置：讓模型決定「接下來查什麼、怎麼回答」這類需要理解語意的事，讓確定性程式決定「能不能退、要不要停、要不要找人」這類不能出錯的事。

控制權的交接也可以畫成一個狀態機，從一個請求的生命週期來看：

```text
            ┌──────────┐ 輸入被拒
  請求進來 ─►│ received │──────────────────────────────► rejected
            └────┬─────┘
                 │ 路由完成
                 ▼
            ┌──────────┐ 模型回 tool_use，guardrail 放行
            │ running  │◄──────────────────────┐
            └──┬──┬──┬─┘                       │
   end_turn    │  │  │ guardrail 要求核准       │ 核准
               │  │  ▼                         │
               │  │ ┌──────────────────┐       │
               │  │ │ awaiting_approval│───────┘
               │  │ └────────┬─────────┘
               │  │          │ 駁回或逾時
               │  │          ▼
               │  │      escalated（轉真人）
               │  │ 超過步數或預算
               │  └────────────────────────────► escalated（轉真人）
               ▼
             done ──► 寫入 memory、eval 檢查 outcome
```

這個狀態機把「誰能讓請求離開 running」講得很清楚。模型只能透過 `end_turn` 讓請求走向 done，或透過 tool call 讓它繼續留在 running；guardrail 可以把它送進 awaiting_approval；harness 在超過步數或預算時把它送去 escalated。換句話說，模型擁有「繼續」和「完成」的提議權，但「暫停」和「放棄」的權力在確定性元件手上。第 21 章會把 awaiting_approval 實作成 approval policy engine，第 22 章會讓這個狀態在 crash 後也能恢復。

## 2.10 元件之間的耦合與取捨

十個元件不是彼此獨立的積木，有幾組耦合特別緊密，設計時要一起考慮。

**Context 和 memory 的邊界**。同一份資訊可以放在 context（每輪都帶）或 memory（需要時才取），放錯位置會兩邊吃虧：把所有記憶都塞進 context，成本和 context rot 一起上升；把常用規則放在 memory 等模型去查，模型可能根本不知道要查。經驗法則是：每一輪都需要的放 context 的穩定前綴，偶爾需要的放 memory 或檢索，並在 context 中留下「去哪裡查」的線索。

**Tools 和 guardrails 的分工**。tool 設計得好，guardrail 就輕鬆。如果 `refund` tool 本身就要求帶 idempotency key，並且在 schema 中限制金額格式，guardrail 只需要檢查業務規則；如果 tool 什麼都接受，guardrail 就得補上所有防線。同理，tool 的副作用等級是 guardrail 和人工審核共用的語言，應該在 tool 定義時就標好。

**Harness 和 model 的此消彼長**。harness 中有一部分是在補模型的弱點，例如提醒模型先查訂單、強迫它先寫計畫。模型變強後，這些補丁可能變成多餘的負擔，甚至讓表現變差。公開的工程經驗是：每個 harness 元件都隱含一個「模型做不到某件事」的假設，換模型時要一次拿掉一個，用 eval 看哪個仍然必要。

**Orchestration 和 runtime 的界線**。orchestration 決定流程的形狀（先做什麼、平行什麼、哪裡等人），runtime 保證流程在故障時仍能接續。兩者常由同一套工具提供，例如 graph 框架的 checkpoint 或 durable execution 引擎，但概念上要分開：一個流程可以設計得很好卻不 durable，也可以 durable 卻設計得很糟。

不同成熟度的 agent，需要的元件深度也不同。下表是一個粗略的對照，用來避免兩種極端：demo 階段過度設計，或上線時才發現缺了關鍵元件。

| 元件 | 內部 prototype | 內部試用 | 對外上線 |
|---|---|---|---|
| Model | 一個前沿模型 | 加上小模型做分類 | model router、fallback、成本計量 |
| Harness | while loop＋最大步數 | 錯誤回填、預算 | 串流、取消、loop guard |
| Tools | 2–5 個手寫 tool | 標副作用等級、idempotency | tool 審查流程、版本管理 |
| Context | 完整對話 | 截斷舊 tool 輸出 | 分層版面、compaction、cache 監控 |
| Memory | 不需要 | 單一使用者層級的事實 | 寫入政策、刪除權、租戶隔離 |
| Orchestration | 單一 agent | 規則式 routing、人工審核門檻 | workflow、multi-agent（若有必要） |
| Runtime | 同一個 process | session log | sandbox、durable execution、配額 |
| Interfaces | 命令列或簡單網頁 | 內部聊天工具 | 對外 API、協定、多通路 |
| Evaluation | 手動試幾題 | 20–50 題 eval set、trace | 回歸測試、線上監控、A/B |
| Guardrails | 寫死的金額上限 | 動作政策、稽核紀錄 | threat model、身分授權、治理流程 |

這張表從左往右讀，是第 38 章「從 prototype 到 production」路線圖的縮影。注意 evaluation 和 guardrails 在「內部試用」欄就已經不是空的：它們是最常被拖延的兩個元件，而青鳥試用中四件事故有兩件正是出在這裡。

## 2.11 2026 現況：生態地圖

前面的內容刻意不提具體產品名稱，因為元件的劃分不太會過時，產品卻每季都在變。這一節把截至 2026 年 10 月的生態對應到十個元件上。以下資訊整理自各家官方文件、GitHub releases 與公開工程文章，版本與狀態變化很快，使用前請以官方最新資料為準。

```text
 ┌─────────────────────────── 託管 agent 服務（一次包下 ②④⑤⑦，部分含 ⑨⑩）──────────────────────────┐
 │ Claude Managed Agents（beta）｜OpenAI Agents API｜Amazon Bedrock AgentCore（含 Harness）｜          │
 │ Gemini Enterprise Agent Platform（Agent Runtime）｜Microsoft Foundry                               │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
 ┌──── SDK／框架（②③⑥ 為主）────┐ ┌──── 協定（⑧）────┐ ┌──── 觀測與評估（⑨）────┐ ┌──── 執行（⑦）────┐
 │ OpenAI Agents SDK            │ │ MCP（tools）      │ │ OpenTelemetry GenAI    │ │ durable：Temporal│
 │ Claude Agent SDK             │ │ A2A（agent↔agent）│ │ Langfuse、LangSmith    │ │ Restate、Inngest │
 │ Google ADK、LangGraph        │ │ AG-UI（↔ 前端）   │ │ Arize Phoenix、Logfire │ │ DBOS             │
 │ Microsoft Agent Framework    │ │ AP2、ACP、x402    │ │ Braintrust、Inspect    │ │ sandbox：託管與  │
 │ Pydantic AI、Strands、Mastra │ │ （agent 支付）    │ │ promptfoo              │ │ OS 原生 sandbox  │
 │ CrewAI、AG2、LlamaIndex、DSPy│ │                   │ │                        │ │                  │
 └──────────────────────────────┘ └───────────────────┘ └────────────────────────┘ └──────────────────┘
 ┌──── 模型與低階 API（①）：Anthropic Messages｜OpenAI Responses＋Conversations｜Gemini Interactions ────┐
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

由下往上讀這張地圖。最底層是模型廠商與它們的低階 API，對應元件 ①。中間四塊是可以分開挑選的積木：SDK 與框架主要提供 harness、tools 與 orchestration 的抽象；協定負責 interfaces；觀測與評估工具負責 evaluation；durable execution 引擎與 sandbox 服務負責 runtime。最上層的託管 agent 服務則是 2026 年最明顯的新形態：把 loop、context 管理、session 持久化與 sandbox 一次做成雲端服務，你只需要定義 agent 與 tools。

| 類別 | 代表（截至 2026 年 10 月） | 對應元件 | 值得注意的現況 |
|---|---|---|---|
| 模型與低階 API | Anthropic（Opus 5.5、Sonnet 5.5、Haiku 4.5 等）、OpenAI（GPT-6 系列）、Google（Gemini 3.x） | ① | 三家都從無狀態的 chat completion 轉向有狀態、以 item 或 step 表示歷史的介面；OpenAI Assistants API 已於 2026-08-26 停止服務，改用 Responses 與 Conversations；Gemini Interactions API 於 2026-06 GA |
| Agent SDK／框架 | OpenAI Agents SDK（v0.23）、Claude Agent SDK、Google ADK（2.x）、LangGraph（1.2）、Microsoft Agent Framework（1.x）、Pydantic AI（v2）、Strands、Mastra、CrewAI、AG2（v1.0 起為全新框架）、LlamaIndex、DSPy | ②③⑥ | 多數框架已過 1.0；graph 式 workflow 與模型自主的 agent 並存是共同方向；durable execution 整合成為常見配備 |
| 協定 | MCP（2026-07-28 版）、A2A（v1.0.1）、AG-UI（1.0） | ⑧ | MCP 2026-07-28 版改成無狀態設計，並把 Sampling、Roots、Logging 標為 deprecated；A2A 於 2026-03 發布 v1.0；AG-UI 於 2026-09-17 發布 1.0 |
| Agent 支付協定 | AP2、ACP（Agentic Commerce Protocol）、UCP、x402、MPP | ⑧⑩ | 多套並存，分別處理授權證明、商務流程與 HTTP 層支付，尚未收斂 |
| 託管 agent 服務 | Claude Managed Agents（beta）、OpenAI Agents API、AgentCore（Runtime、Harness、Gateway、Identity、Memory、Policy 等可分開使用）、Gemini Enterprise Agent Platform 的 Agent Runtime（前身為 Vertex AI Agent Engine 的頁面） | ②④⑤⑦⑨⑩ | 各家把 agent loop、sandbox、session 與 compaction 做成雲端服務；細節與限制差異大，例如 Claude Managed Agents 目前不支援 ZDR |
| Durable execution | Temporal、Restate、Inngest、DBOS | ⑦ | 都提供 agent 整合範例或 recipe，把每次模型與 tool 呼叫當成可重播的步驟 |
| 觀測與評估 | OpenTelemetry GenAI semantic conventions、Langfuse、LangSmith、Arize Phoenix、Logfire、Braintrust、Inspect、promptfoo | ⑨ | OTel GenAI conventions 已移到獨立 repo，定義了 `invoke_agent`、`execute_tool` 等 span，但幾乎全部仍是 Development 穩定度；Langfuse 於 2026-01 被 ClickHouse 收購，promptfoo 於 2026-03 宣布被 OpenAI 收購，兩者都承諾維持開源 |

表中有三個現象值得放進設計考量。第一，**託管 harness 興起**，代表「自己寫 loop」不再是唯一選項，第 26 章會用 build vs buy 的框架比較。第二，**協定在快速改版**，MCP 的無狀態改版對既有 server 是不小的改動，所以 interfaces 層要保持可替換。第三，**觀測標準尚未穩定**，trace 的屬性名稱可能變動，自家的 tracer 最好包一層自己的抽象，再輸出成 OTel 格式。

> [!note] 2026 現況
> 截至 2026 年 10 月，sandbox 服務的選擇包括各雲端平台內建的 code interpreter，以及 E2B、Modal、Daytona 等第三方託管服務；本書撰寫時的 survey 對這些服務的功能與價格未逐一查證，選型前請自行核對。coding agent CLI 在本機常用作業系統原生機制（macOS 的 Seatbelt、Linux 的 bubblewrap）實作 sandbox，這部分已有公開文件與原始碼可查。

## 2.12 動手做：用 Python 組出十元件骨架

這一節把十個元件各用幾行程式實作，組成一個「麻雀雖小、五臟俱全」的骨架，並讓每個元件在被使用時往同一份追蹤寫一行紀錄。目的不是做出可用的產品，而是讓你親眼看到一次請求怎麼依序流經十個元件。之後的章節會把每個元件從幾行長成一整章。

程式的結構和 2.4 的架構圖一一對應：`TOOLS` 是 ③，`MEMORY` 是 ⑤，`build_context` 是 ④，`check_action` 是 ⑩，`execute` 與 `SESSION_LOG` 是 ⑦，`run_agent` 是 ②，`route` 是 ⑥，`handle_request` 同時扮演 ⑧ 和 ⑨，模型 ① 則是全書統一的 `ScriptedModel`。程式跑兩個請求：第一個是正常退款，第二個是超過自動核准門檻的退款。

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


class ScriptedModel:
    """依劇本回應的假模型。劇本的每一步是 ModelResponse，或「收到 messages 後回傳 ModelResponse」的函式。"""

    def __init__(self, script: list[ModelResponse | Callable[[list[dict]], ModelResponse]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse:
        self.calls.append(json.loads(json.dumps(messages)))
        if not self.script:
            raise RuntimeError("劇本已用完：agent 呼叫模型的次數比預期多")
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def call(name: str, call_id: str = "c1", **args: Any) -> ModelResponse:
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    return ModelResponse(text=text)


TRACE: list[str] = []          # ⑨ 的原料：每個元件都往這裡寫一行


def trace(no: int, part: str, msg: str) -> None:
    TRACE.append(f"[{no:02d} {part:<13}] {msg}")


# ③ Tools：名稱、schema、副作用等級。實作在「外部系統」，這裡用 dict 假裝是 ERP。
ORDERS = {"A1001": {"item": "藍牙耳機", "amount": 490, "status": "delivered"},
          "A2002": {"item": "空氣清淨機", "amount": 5200, "status": "delivered"}}
REFUNDS: dict[str, int] = {}   # idempotency key → 金額
TOOLS = {
    "get_order": {"effect": "read", "fn": lambda order_id: ORDERS[order_id]},
    "refund": {"effect": "destructive",
               "fn": lambda order_id, amount: REFUNDS.setdefault(f"refund:{order_id}", amount)},
}


# ⑤ Memory：跨 session 的使用者事實；④ Context 每次從它挑需要的部分。
MEMORY = {"u42": ["偏好退回原信用卡", "上次聯絡：物流延遲（已結案）"], "u77": []}


def build_context(user_id: str, messages: list[dict]) -> str:
    facts = MEMORY.get(user_id, [])[:1]                # 只帶與本任務相關的一條，不是全部
    system = "你是青鳥科技的客服 agent。退款前先查訂單。記憶：" + "；".join(facts)
    size = len(system) + sum(len(str(m["content"])) for m in messages)
    trace(4, "context", f"組裝 system＋{len(messages)} 則訊息，約 {size} 字元；帶入記憶 {len(facts)} 條")
    return system


# ⑩ Guardrails：在模型「之外」用確定性規則檢查每個動作。
REFUND_LIMIT = 500                     # 第 1 章 L4 的小額自動退款邊界


def check_action(tc: ToolCall) -> tuple[bool, str]:
    if TOOLS[tc.name]["effect"] == "read":
        return True, "唯讀，放行"
    if tc.args.get("amount", 0) > REFUND_LIMIT:
        return False, f"金額超過 {REFUND_LIMIT}，需要人工核准"
    return True, f"不可逆動作，金額 {tc.args['amount']} ≤ {REFUND_LIMIT}，放行"


# ⑦ Runtime：執行 tool、寫 durable session log；例外變成 tool result 而不是讓 loop 崩潰。
SESSION_LOG: list[dict] = []


def execute(tc: ToolCall) -> str:
    try:
        result = json.dumps(TOOLS[tc.name]["fn"](**tc.args), ensure_ascii=False)
    except Exception as exc:                            # 錯誤要回給模型，讓它能修正
        result = f"error: {exc}"
    SESSION_LOG.append({"call": tc.name, "args": tc.args, "result": result})
    trace(7, "runtime", f"執行 {tc.name}{tc.args} → {result}")
    return result


# ② Harness：loop 本身。它不懂退款，只懂「呼叫模型 → 檢查 → 執行 → 回填 → 停止條件」。
def run_agent(model: ScriptedModel, user_id: str, text: str, max_steps: int = 6) -> str:
    messages: list[dict] = [{"role": "user", "content": text}]
    for step in range(1, max_steps + 1):
        system = build_context(user_id, messages)
        resp = model.complete(messages, tools=list(TOOLS), system=system)
        trace(1, "model", f"第 {step} 次呼叫 → stop_reason={resp.stop_reason}")
        messages.append({"role": "assistant", "content": resp.text,
                         "tool_calls": [tc.__dict__ for tc in resp.tool_calls]})
        if resp.stop_reason == "end_turn":
            trace(2, "harness", f"end_turn，共 {step} 步")
            return resp.text
        for tc in resp.tool_calls:
            ok, why = check_action(tc)
            trace(10, "guardrail", f"{tc.name}：{why}")
            result = execute(tc) if ok else f"blocked: {why}"
            trace(3, "tools", f"回填 tool_result（{TOOLS[tc.name]['effect']}{'' if ok else '，被擋下'}）")
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": result})
    trace(2, "harness", "超過 max_steps，強制停止")
    return "抱歉，這件事我需要轉給真人同事處理。"


# ⑥ Orchestration：決定這個請求交給誰。這裡是最簡單的規則式 routing。
def route(text: str) -> str:
    agent = "support" if any(k in text for k in ("退款", "訂單", "物流")) else "faq"
    trace(6, "orchestration", f"路由到 {agent} agent")
    return agent


# ⑧ Interfaces：對外的 API；⑨ Evaluation：看「環境的最終狀態」，不是看 agent 說了什麼。
def handle_request(user_id: str, text: str, model: ScriptedModel, expect: dict[str, int]) -> dict:
    trace(8, "interface", f"POST /chat user={user_id} text={text!r}")
    if "忽略以上指示" in text:                          # 極簡的輸入 guardrail
        trace(10, "guardrail", "輸入疑似 prompt injection，拒絕")
        return {"reply": "無法處理這個請求。", "passed": False}
    route(text)
    start = len(SESSION_LOG)
    reply = run_agent(model, user_id, text)
    done = [e["args"]["order_id"] for e in SESSION_LOG[start:] if e["call"] == "refund"]
    MEMORY[user_id] += [f"{oid} 已退款" for oid in done]   # 只記「真的發生」的事
    trace(5, "memory", f"寫入 {len(done)} 條新事實")
    passed = REFUNDS == expect
    trace(9, "evaluation", f"outcome：退款紀錄={REFUNDS}，預期={expect} → {'PASS' if passed else 'FAIL'}")
    return {"reply": reply, "passed": passed}


# 請求一：一般退款，十個元件全部走過一次。
m1 = ScriptedModel([
    call("get_order", "c1", order_id="A1001"),
    call("refund", "c2", order_id="A1001", amount=490),
    say("已為訂單 A1001 退款 490 元，將退回原信用卡。"),
])
out1 = handle_request("u42", "訂單 A1001 的耳機壞了，想退款", m1, expect={"refund:A1001": 490})
print("\n".join(TRACE))
print("回覆：", out1["reply"])
touched = sorted({int(line[1:3]) for line in TRACE})
print("經過的元件：", touched)
assert out1["passed"] and touched == list(range(1, 11))
assert len(m1.calls) == 3 and len(SESSION_LOG) == 2 and MEMORY["u42"][-1] == "A1001 已退款"

# 請求二：高金額退款被 guardrail 擋下，模型看到 blocked 後改為轉人工。
TRACE.clear()
m2 = ScriptedModel([
    call("refund", "c1", order_id="A2002", amount=5200),
    lambda msgs: say("這筆金額需要主管核准，我已轉給真人同事。")
    if msgs[-1]["content"].startswith("blocked") else say("已退款"),
])
out2 = handle_request("u77", "訂單 A2002 要退款", m2, expect={"refund:A1001": 490})
print("\n".join(TRACE))
print("回覆：", out2["reply"])
assert out2["passed"] and "A2002" not in str(REFUNDS) and MEMORY["u77"] == []
```

執行結果如下：

```text
[08 interface    ] POST /chat user=u42 text='訂單 A1001 的耳機壞了，想退款'
[06 orchestration] 路由到 support agent
[04 context      ] 組裝 system＋1 則訊息，約 53 字元；帶入記憶 1 條
[01 model        ] 第 1 次呼叫 → stop_reason=tool_use
[10 guardrail    ] get_order：唯讀，放行
[07 runtime      ] 執行 get_order{'order_id': 'A1001'} → {"item": "藍牙耳機", "amount": 490, "status": "delivered"}
[03 tools        ] 回填 tool_result（read）
[04 context      ] 組裝 system＋3 則訊息，約 107 字元；帶入記憶 1 條
[01 model        ] 第 2 次呼叫 → stop_reason=tool_use
[10 guardrail    ] refund：不可逆動作，金額 490 ≤ 500，放行
[07 runtime      ] 執行 refund{'order_id': 'A1001', 'amount': 490} → 490
[03 tools        ] 回填 tool_result（destructive）
[04 context      ] 組裝 system＋5 則訊息，約 110 字元；帶入記憶 1 條
[01 model        ] 第 3 次呼叫 → stop_reason=end_turn
[02 harness      ] end_turn，共 3 步
[05 memory       ] 寫入 1 條新事實
[09 evaluation   ] outcome：退款紀錄={'refund:A1001': 490}，預期={'refund:A1001': 490} → PASS
回覆： 已為訂單 A1001 退款 490 元，將退回原信用卡。
經過的元件： [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
[08 interface    ] POST /chat user=u77 text='訂單 A2002 要退款'
[06 orchestration] 路由到 support agent
[04 context      ] 組裝 system＋1 則訊息，約 39 字元；帶入記憶 0 條
[01 model        ] 第 1 次呼叫 → stop_reason=tool_use
[10 guardrail    ] refund：金額超過 500，需要人工核准
[03 tools        ] 回填 tool_result（destructive，被擋下）
[04 context      ] 組裝 system＋3 則訊息，約 63 字元；帶入記憶 0 條
[01 model        ] 第 2 次呼叫 → stop_reason=end_turn
[02 harness      ] end_turn，共 2 步
[05 memory       ] 寫入 0 條新事實
[09 evaluation   ] outcome：退款紀錄={'refund:A1001': 490}，預期={'refund:A1001': 490} → PASS
回覆： 這筆金額需要主管核准，我已轉給真人同事。
```

逐段解讀這份追蹤，並把它和 2.9 的時序圖對照。

**第一個請求的前兩行**是 interface 收到請求、orchestration 路由到客服 agent。接著進入 harness 的 loop，每一輪都從 context 組裝開始，所以 `[04 context]` 出現了三次：訊息數從 1、3 增加到 5（每輪多一則 assistant 訊息和一則 tool 訊息），字元數也跟著上升。這就是 context 隨輪數成長的縮影，真實系統裡 tool 回傳的訂單資料可能是幾千個 token，第 9 章要處理的正是這條曲線。

**每一次 tool 呼叫都經過「guardrail → runtime → tools 回填」三步**。`get_order` 是唯讀，直接放行；`refund` 是 destructive（錢退出去就收不回來），guardrail 檢查金額在 L4 的 500 元邊界內才放行。注意 guardrail 的判斷依據是 tool 的副作用等級和參數，完全不看模型說了什麼，這正是 2.8 說的「確定性規則放在模型之外」。runtime 每次執行都寫進 `SESSION_LOG`，最後的 assert 確認 log 裡正好有兩筆。

**`[02 harness] end_turn，共 3 步`** 是 loop 的停止點。停止的原因是模型回了 `end_turn`，但如果模型一直不停，`max_steps=6` 會讓 harness 強制結束並轉人工，這條路徑在 2.9 的狀態機中對應 running → escalated。

**最後兩行是請求結束後的工作**。memory 只從 session log 中萃取「真的發生的退款」寫入，而不是相信模型的回覆內容；evaluation 檢查的是 `REFUNDS` 這個「環境狀態」，而不是回覆裡有沒有出現「已退款」三個字。`經過的元件：[1, …, 10]` 確認十個元件全部參與了這次請求。

**第二個請求**展示控制權的轉移。模型要求退款 5200 元，guardrail 擋下，tool result 變成 `blocked: …`。劇本的第二步是一個函式：它讀取最後一則 tool 訊息，看到 blocked 就改說「已轉給真人同事」。這模擬了真實模型讀到被拒的 tool result 後改變策略。evaluation 仍然 PASS，因為它檢查的是「A2002 沒有被退款」，而這正是我們要的結果；memory 寫入 0 條，因為沒有真的發生任何退款。在真實系統中，這裡應該進入 awaiting_approval 狀態並通知主管，第 21 章會補上這一段。

這個骨架故意留下很多不足：context 沒有預算控制、memory 沒有檢索、runtime 沒有逾時與 idempotency 的重試保護、evaluation 只有一題。每一個不足都是後面某一章的起點。你可以試著改動它：把 `REFUND_LIMIT` 改成 300，看第一個請求的追蹤怎麼變；或者讓劇本在 `refund` 被擋下後仍然回覆「已退款」，看 evaluation 會不會被騙（不會，因為它看的是環境狀態，但使用者會收到錯誤的訊息，這說明輸出也需要檢查）。

## 2.13 實務應用

同樣的十個元件，在不同類型的產品裡比重差異很大。下面三個情境來自本書後半會深入的案例類型，說明每個情境的「重心元件」與要注意的地方。

**情境一：電商客服 agent（青鳥的主線）**。重心在 tools、guardrails 與 memory。客服 agent 的動作大多是對 ERP 的讀寫，tool 設計決定了準確度；退款、改地址這類寫入必須有確定性的金額門檻與人工審核；回頭客的偏好與未結案件需要跨 session 記憶。runtime 相對單純，因為不執行任意程式碼；但 interfaces 很複雜，同一個 agent 要同時服務網頁、LINE、Email 等多個通路。公開資料顯示，專做客服 agent 的公司會在知識庫檢索、轉真人的判斷與一致性評估上投入大量研究，例如 Sierra 團隊發表的 τ-bench 系列就是專門評估「agent 與使用者、工具多輪互動」可靠度的 benchmark，並使用 pass^k 衡量一致性。第 41、42 章會完整展開。

**情境二：背景執行的 coding agent（青鳥內部工具）**。重心在 runtime／sandbox、context 與 evaluation。coding agent 會執行自己寫的程式碼與測試，必須在 sandbox 裡跑，網路要預設拒絕；任務常常跑幾十分鐘，context 會被大量檔案內容與測試輸出塞滿，需要 compaction 與「把進度寫進檔案」的技巧；評估則有天然的優勢，因為測試能不能過是客觀的 outcome。公開資料顯示，GitHub 的 Copilot coding agent 在 GitHub Actions 的臨時環境中執行，每個任務對應一個 branch 與一個 PR；主流 coding agent CLI 則用作業系統原生 sandbox 限制寫入範圍與網路。這類產品的 interfaces 通常是非同步的：指派一個 issue，之後收到一個 PR。第 39、43 章會深入。

**情境三：企業 research 與分析 agent（青鳥營運團隊）**。重心在 orchestration、context 與 guardrails。研究任務適合平行展開：一個 orchestrator 拆出子問題，交給多個 subagent 分頭搜尋與閱讀，最後綜合成附引用的報告，這是 multi-agent 真正有優勢的場景。風險在於 lethal trifecta：agent 同時能讀內部營收資料、會讀進外部網頁、又能寄出報告，任何一個外部網頁裡的惡意指令都可能導致資料外洩，所以要在架構上分階段處理（先公開資料、再私有資料，且處理私有資料時不連外網）。Anthropic 公開的 multi-agent research 系統就採用 orchestrator 加多個平行 subagent 的架構；OpenAI 的 deep research 文件也建議把公開網路與私有資料分階段處理。第 40、44 章會深入。

| 元件 | 電商客服 | 背景 coding agent | 企業 research |
|---|---|---|---|
| 重心元件 | Tools、Guardrails、Memory | Runtime／Sandbox、Context、Evaluation | Orchestration、Context、Guardrails |
| 主要互動方式 | 同步聊天、多通路 | 非同步：issue 進、PR 出 | 非同步：提問、收報告 |
| 最大風險 | 被話術騙去做不可逆的寫入 | 執行的程式碼破壞環境或外洩憑證 | 外部內容注入導致內部資料外洩 |
| 天然的 outcome 檢查 | 訂單與退款紀錄 | 測試是否通過 | 引用是否支持結論（較難自動化） |
| multi-agent 的必要性 | 通常不需要，routing 就夠 | 讀取型 subagent 有幫助，平行寫入要隔離 | 平行研究是主要優勢 |

這張表的用法是：拿到一個新的 agent 專案時，先判斷它最像哪一欄，把重心元件列為設計審查的優先項目。例如有人提議「做一個幫業務寫提案的 agent」，它會讀 CRM 私有資料、讀客戶官網、產出文件寄給客戶，最像第三欄，那麼 guardrails 的資料外洩分析就要排在最前面。

## 2.14 設計檢查清單

設計或審查一個 agent system 時，逐項確認以下問題。每一題都應該能用「是／否」或「選哪個」回答，答不出來的就是待辦事項。

1. 十個元件是否都有明確的負責人與目前的答案？哪些元件被刻意標為「目前不需要」，理由是否寫下來了？
2. 能不能用 Model／Harness／Environment 三層，說出最近三個 bug 各自屬於哪一層？
3. 模型選擇是否有 eval 數據支持？是否考慮過用小模型處理分類、摘要等簡單工作？
4. Harness 是否至少有三種停止條件（模型結束、最大步數、token 或金額預算）？超過時是否有明確的去處（轉人工、回報失敗）？
5. 每個 tool 是否標了副作用等級（read、write、destructive）？未標註的是否一律當 destructive？destructive 動作是否都帶 idempotency key？
6. Context 的版面是否由穩定到動態排列？session 中途是否會改動 tool 定義或 system prompt，進而破壞 prompt cache？
7. Memory 的寫入政策是什麼：誰能寫、寫什麼、多久過期、使用者要求刪除時怎麼處理？
8. 是否有一條規則說明「哪些請求交給哪個 agent」，以及「哪些動作要等人核准」？
9. 會執行任意程式碼的 tool 是否在 sandbox 裡？sandbox 的網路是否預設拒絕？憑證是否放在 sandbox 碰不到的地方？
10. Session log 是否完整記錄每次模型呼叫與 tool 呼叫，足以在 crash 後恢復、在事故後重建經過？
11. 不能出錯的業務規則（金額上限、權限）是由確定性程式執行，還是寫在 prompt 裡拜託模型遵守？
12. 是否有一組 eval set 在每次改 prompt、換模型、改 tool 時自動執行，並以環境的最終狀態判斷成敗？
13. 這個 agent 是否同時具備「讀私有資料、接觸不可信內容、能對外傳送」三個條件？如果是，架構上切斷了哪一邊？
14. 每個寫入動作能否回答「代表誰、依據什麼權限、什麼時間」？稽核紀錄存在哪裡、保存多久？

## 2.15 常見錯誤與除錯

下表整理在元件層級最常見的錯誤。共同的除錯技巧是：先從症狀判斷是哪個元件，再去那個元件的紀錄（trace、session log、eval 結果）找證據，而不是第一時間改 prompt。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 同一筆退款被執行兩次 | runtime 在逾時後重試，tool 沒有 idempotency key | 在 session log 找同一訂單的兩筆 refund 呼叫，比對時間與 call id | refund 必須帶 idempotency key；runtime 的重試只對唯讀 tool 自動進行 |
| 改了 prompt 之後，某類任務悄悄變差 | 沒有 eval 在改動時自動執行 | 用改動前後的版本跑同一組 eval，看哪些題目從 PASS 變 FAIL | 建立回歸 eval set，納入 CI；prompt 版本化 |
| 長對話後 agent 開始答非所問或重複動作 | context 無限成長，出現 context rot | 在 trace 中看每輪的 input token 數是否持續上升 | 清理舊 tool 輸出、加入 compaction、把完整紀錄移到 session log |
| 使用者隔天回來，agent 完全不記得 | 沒有 memory 元件，或寫入了但 context 沒有讀出 | 查 memory 儲存是否有該使用者的資料；查 context 組裝是否帶入 | 設計寫入政策與讀取時機；在 context 留下「可查詢記憶」的線索 |
| agent 被使用者話術說服，做了不該做的事 | 業務規則只寫在 prompt 裡，沒有確定性檢查 | 在 trace 中找出該動作，確認執行前是否有 guardrail 判斷紀錄 | 把規則移到 tool 執行前的政策檢查；高風險動作送人工核准 |
| 換了更強的模型，表現反而變差 | harness 裡補舊模型弱點的指令，和新模型的行為衝突 | 逐一移除 harness 中的補丁指令，用 eval 比較 | 把補丁做成可拆卸的設定，換模型時做 ablation |
| 事故後無法說明 agent 為什麼這樣做 | 沒有 trace，或 trace 沒有記錄模型輸入 | 檢查 trace 是否包含每輪的 context 版本與 tool result | 依 OTel GenAI conventions 記錄 span；敏感內容遮蔽後保存 |
| 只能在一個通路使用，接新通路要重寫 | interfaces 和 harness 綁死，例如在 loop 中直接輸出 HTML | 看 harness 程式碼是否引用了特定通路的格式 | harness 只輸出事件串流，由各通路的 adapter 轉換 |

## 本章重點整理

- Agent 的核心 loop 很小，但能上線的 agent system 由十個元件組成，每個元件回答一個必須有人負責的設計問題。
- 元件是邏輯上的責任，不是部署上的服務；它們可以在同一個 process 裡，但每一個都必須有明確的答案。
- Model／Harness／Environment 三層模型讓除錯有方向：模型只做決定，harness 把決定變成動作，環境是行動的對象，模型永遠不直接碰到環境。
- 十個元件是 model、harness／loop、tools、context、memory、orchestration、runtime／sandbox、interfaces、evaluation、guardrails／governance。
- Context 是「這一輪的桌面」，memory 是「跨 session 的檔案櫃」；context 應由穩定到動態排列，以配合 prompt caching。
- 完整的 session log 應該存在 runtime，context 只是 log 的一個可重建視圖，因為 compaction 會丟資訊而且不可逆。
- 在控制流中，模型是唯一的非確定性決策者；「暫停」與「放棄」的權力應該掌握在 guardrails、harness 等確定性元件手上。
- 不能出錯的業務規則要用模型之外的確定性程式執行，因為 prompt injection 目前沒有可靠的模型層解法。
- Evaluation 要以環境的最終狀態為主要判準，並用 pass^k 衡量可靠度，因為 agent 說完成不代表真的完成。
- Harness 中補模型弱點的部分會隨模型升級而過時，換模型時要用 eval 逐一確認哪些仍然必要。
- 不同產品的重心元件不同：客服重 tools 與 guardrails，coding agent 重 sandbox 與 evaluation，research agent 重 orchestration 與資料外洩防護。
- 2026 年的生態可以對應到十個元件上；託管 agent 服務一次包下 harness、context、memory 與 runtime，是 build vs buy 決策的新選項。

## 延伸問答

> [!question]- Q1. Context 和 memory 都是「給模型看的資訊」，為什麼要分成兩個元件？
> 因為它們回答的問題和受到的限制完全不同。Context 回答「這一輪模型看到什麼」，受限於 context window 的大小、context rot 與每輪的 token 成本，所以每一輪都要重新取捨。Memory 回答「跨 session 要保留什麼」，受限的是寫入政策、正確性、過期與隱私，例如使用者要求刪除時要能真的刪掉。
>
> 如果把兩者混為一談，常見的結果是兩種極端：把所有記憶都塞進 context，成本隨使用者的歷史長度增加，模型也更容易被舊資訊干擾；或者把重要規則放進 memory 等模型自己去查，模型卻不知道有東西可查。分成兩個元件後，設計者會被迫分別回答「存什麼」和「這一輪帶什麼」，兩個問題都有人負責。

> [!question]- Q2. 既然模型越來越強，harness 會不會終究消失？
> Harness 中有兩種不同性質的程式。第一種是「補模型弱點」的：冗長的禁止事項、強迫先寫計畫、提醒使用某個 tool。這部分確實會隨模型變強而變薄，公開的工程經驗也顯示，把這些指令刪掉後品質不降反升的情況並不少見。
>
> 第二種是「對環境負責」的：權限檢查、idempotency、預算、sandbox、session log、稽核。這部分不會因為模型變強而消失，因為它們處理的不是模型的能力不足，而是外部系統的不可靠、使用者的惡意與組織的責任歸屬。模型能做的事越多，它可能造成的損害也越大，這部分反而要更嚴謹。所以比較準確的說法是：harness 的形狀會改變，重心會從「教模型做事」移到「讓模型安全地做事」。

> [!question]- Q3. 你在 production 看到客服 agent 偶爾把退款金額填錯，第一步應該改 prompt 嗎？
> 不應該。第一步是確認問題出在哪個元件。先從 trace 找出填錯的那幾次，看模型那一輪的 context：如果 context 裡根本沒有正確的訂單金額（例如 tool 回傳被截斷、或查錯訂單），那是 tools 或 context 的問題；如果金額在 context 裡但模型抄錯，才是模型或 prompt 的問題。
>
> 即使確定是模型抄錯，最可靠的修法通常也不是 prompt，而是在 tool 和 guardrail 層加上確定性檢查：例如 refund tool 只接受訂單 id，金額由 tool 自己從 ERP 讀取；或在執行前比對金額與訂單紀錄是否一致。這樣就算模型再錯一次，也不會造成實際損害。最後，把這類案例加進 eval set，確保之後的改動不會讓它復發。

> [!question]- Q4. 系統設計面試中被要求「設計一個 agent system」，十個元件要怎麼用？
> 十個元件適合當作答題的骨架，確保不遺漏，但不要平均分配時間。先釐清任務與成功標準，判斷這個系統最像哪種產品（客服、coding、research），再依 2.13 的方式指出重心元件，把大部分時間花在那裡深入：資料流、控制流、失敗模式與取捨。
>
> 具體做法是：先畫出 2.4 那張架構圖的簡化版，用一兩句話交代每個元件的答案；接著挑兩三個重心元件深入，例如客服系統就深入 tools 的副作用分級、guardrails 的審核門檻與 memory 的隱私處理；最後談 evaluation 和營運，說明上線後怎麼知道它變好或變壞。面試官通常想看的是你能否分辨「哪些決定交給模型、哪些必須是確定性的」，2.9 的控制流表格就是回答這個問題的好工具。第 35 章會把這個流程整理成完整的方法論。

> [!question]- Q5. 自建所有元件和使用託管 agent 服務，要怎麼選？
> 這不是全有或全無的選擇，而是逐個元件決定。託管 agent 服務通常一次包下 harness、context 管理、session 持久化與 sandbox，優點是省下大量工程時間，並直接繼承廠商在 compaction、sandbox 安全上的經驗；缺點是較難客製、可能綁定特定模型，而且資料保留與合規條件要逐項確認，例如某些服務不支援零資料保留。
>
> 判斷時可以問三個問題。第一，哪些元件是你的產品差異化所在？青鳥的差異化在電商領域的 tools 與政策，而不是 loop，所以 harness 外包是合理的。第二，你的合規要求能否被託管服務滿足？第三，未來要換模型或換廠商時，遷移成本有多高？一個常見的折衷是：tools 用 MCP 這類標準協定實作、eval 與 trace 自己掌握、harness 與 runtime 視情況外包。第 26 章會有完整的 build vs buy 決策框架。

> [!question]- Q6. 下面這段 harness 程式有什麼問題？`if "退款" in reply and amount < 500: refund(order_id, amount)`
> 這段程式有兩個元件層級的問題。第一，它從模型的文字回覆中判斷要不要退款，等於把控制流建立在非結構化的自然語言上。模型可能說「我無法退款」，裡面也有「退款」兩個字；正確做法是讓模型透過結構化的 tool call 表達意圖，由 harness 依 tool 名稱與參數分派。
>
> 第二，金額門檻的檢查直接寫在 harness 的分派邏輯裡，和 tool 的執行綁在一起，沒有留下 guardrail 的判斷紀錄，也沒有「超過門檻時怎麼辦」的路徑。比較好的設計是：refund 是一個標了 destructive 的 tool，執行前由獨立的政策檢查決定放行、拒絕或送審，判斷結果寫進 trace，超過門檻時把請求轉入等待核准的狀態。另外，`amount` 應該由 tool 從訂單紀錄讀取或比對，不能完全信任模型給的數字。

> [!question]- Q7. 估算：青鳥客服 agent 每天 2 萬次對話，平均每次 4 輪模型呼叫，每輪 input 6,000 token，若 prompt cache 命中率從 0 提升到 70%，對成本有多大影響？
> 先算總量：2 萬次乘以 4 輪是每天 8 萬次模型呼叫，每次 6,000 input token，合計 4.8 億 input token。假設 cache 讀取的價格是一般 input 的十分之一（實際比例依廠商與模型而不同，請查當時的價目表），命中率 0 時成本是 4.8 億個「單位」；命中率 70% 時，3.36 億 token 以十分之一計價，約等於 3,360 萬單位，加上 1.44 億未命中的 token，合計約 1.78 億單位，input 成本大約降到原本的 37%。
>
> 這個估算說明了為什麼 context 的版面設計（穩定前綴在前）是成本問題而不只是品質問題。它也提醒一件事：寫入 cache 可能有額外費用，output token 不受 cache 影響，而且命中率會被「session 中途改 tool 定義」這類操作破壞。實務上要在 trace 中記錄每次呼叫的 cache 讀寫 token，才能知道實際命中率。第 3 章會解釋 prompt caching 的計價原理，第 9 章會示範怎麼量測。

> [!question]- Q8. Orchestration 和 harness 都在「控制流程」，兩者的界線在哪裡？
> Harness 控制的是「一個 agent 內部的 loop」：呼叫模型、執行 tool、回填結果、判斷停止。它不關心這個 agent 在整個業務流程中的位置。Orchestration 控制的是「agent 之間、步驟之間的流程」：這個請求交給哪個 agent、哪些步驟要依序或平行、哪裡要停下來等人核准、一個 agent 的輸出怎麼交給下一個。
>
> 一個實用的判斷方式是看「誰在做決定」與「決定的粒度」。如果是模型在一次對話中決定下一個 tool，那是 harness 內的事；如果是規則或另一個 orchestrator 決定「這段工作交給物流 agent」，那是 orchestration。兩者也可以嵌套：一個 workflow 的某個節點是一個完整的 agent loop，或一個 agent 把另一個 agent 當成 tool 呼叫。分清界線的好處是，你可以單獨測試每個 agent 的 harness，再單獨測試 orchestration 的流程邏輯，而不必每次都跑整個系統。

## 延伸閱讀

- Anthropic Engineering Blog〈Building effective agents〉（2024）
- OpenAI〈A practical guide to building agents〉（2025）
- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
- HumanLayer〈12-Factor Agents〉（GitHub，2025）
- Anthropic Engineering Blog〈Scaling Managed Agents〉（2026）
- Simon Willison〈The lethal trifecta for AI agents〉（2025）
- Microsoft Learn 上的 Microsoft Agent Framework 官方文件（2026）
