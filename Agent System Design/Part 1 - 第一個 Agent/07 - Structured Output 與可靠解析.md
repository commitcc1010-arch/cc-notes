---
chapter: 7
title: Structured Output 與可靠解析
part: 1
---

# 第 7 章　Structured Output 與可靠解析

> [!abstract] 本章地圖
> **核心問題**：模型是機率性的生產者，下游程式是確定性的消費者；兩者之間要怎麼設計契約、檢查與修復，才能讓「模型說的話」安全地變成「程式能用的資料」？
>
> **你會學到**：
> - 說清楚 structured output 在 agent system 中出現的位置，以及每一層保證（prompt、JSON mode、strict schema、程式驗證）各自擋住哪些錯誤
> - 為模型設計 JSON Schema：欄位命名、enum、可為 null 的選填欄位、描述與欄位順序
> - 理解 constrained decoding 怎麼運作、為什麼它只保證形狀不保證正確，以及 schema 寫太緊的代價
> - 用 dataclass 建立「一份定義、兩種用途」的資料模型，並用 discriminated union 表達「多種動作擇一」
> - 實作語法、schema、語意三層驗證，以及有次數上限的 validate-and-repair 迴圈
> - 寫一個能解析「還沒結束的 JSON」的串流解析器，分辨哪些欄位可以顯示、哪些可以執行
>
> **前置知識**：第 3 章（structured outputs 的三個保證層級與 constrained decoding 的直覺）、第 4 章（`loom` v0.1 的 dispatch、錯誤回填與 streaming 組裝）、第 5 章（tool schema 的命名與描述）

## 7.1 故事：退款確認卡上的「1,200」

客服 agent v1 上線三週後，青鳥科技的客服團隊開始依賴一個新畫面：**處理確認卡**。agent 和顧客聊完之後，不直接退款，而是產生一份「處理結果」：判斷這是哪一類問題、要回覆顧客什麼、建議採取哪個動作（退款、建立退貨單或轉給專人），再由客服人員在卡片上按「核准」才真的執行。這正是第 1 章說的 L3：查詢自主，寫入要人確認。卡片要能顯示金額、訂單編號與理由，所以 agent 的最後一步必須輸出一段程式讀得懂的 JSON。

Iris 的做法是在 system prompt 最後加一句「請只輸出 JSON，格式如下」，附上一個範例。測試環境裡一切正常。上線第一個週二，客服主管在群組裡貼了三張截圖：一張卡片整個空白，一張顯示「解析失敗」，還有一張的退款理由欄寫著「退款」兩個中文字，下拉選單直接報錯。Iris 拉出 log 一看，模型的輸出五花八門：有的包在 Markdown 的 code fence 裡、前面還有一句「好的，以下是處理結果」；有的陣列最後多了一個逗號；有的把金額寫成字串 `"1,200"`；有的把英文 enum 值換成了中文同義詞。每一種單獨看都很罕見，合起來大約每五十張卡片就壞一張。

Iris 寫了一個 regex 把第一個 `{` 到最後一個 `}` 之間的內容抓出來，修好了 code fence 的問題，結果隔天又壞了另一批：顧客的留言裡有「{急件}」這樣的大括號，模型在 JSON 後面補了一句帶括號的說明，貪婪比對把兩段黏在一起。更嚇人的是第三件事：有一張卡片格式完全正確，所有欄位都在，型別也對，退款金額卻是 12,000 元，而那張訂單的總額只有 1,200 元。值班的客服差一點就按下核准。

同一週，產品經理阿哲又提了一個需求：顧客等回覆時畫面一片空白太久，希望 agent 的回覆文字能像聊天一樣一個字一個字出現。Iris 打開串流，卡片上卻開始閃爍一堆 `{"intent": "ref` 之類的半截字元。資安工程師 Maya 則問了一個 Iris 答不出來的問題：「如果串流到一半，訂單編號只收到 `B-10`，你的程式會不會拿它去查、甚至去退款？」

老陳聽完，在白板上畫了一條線，左邊寫「模型」，右邊寫「程式」。「左邊是機率性的生產者，右邊是確定性的消費者。你現在是讓貨物直接越過邊界，」老陳說，「中間要有一道海關：先講好貨物長什麼樣子（schema），能在生產時就限制形狀的盡量限制（constrained decoding），通關時逐層檢查（驗證），不合格的退回重做但有次數上限（修復迴圈），還沒到齊的貨不能拆箱使用（串流解析）。」這一章就是這道海關的設計與實作，最後它會成為給 `loom` 加上的 `loom.schema` 模組：第 4 章 dispatch 裡只檢查必填與未知參數的驗證，會換成本章完整的 schema 驗證器。

## 7.2 Structured output 在 agent system 中的位置

**Structured output**（結構化輸出）是指模型的輸出不是給人讀的自由文字，而是符合事先約定結構、要交給程式處理的資料，最常見的形式是 JSON。例如「這張工單屬於退款類、優先度 2、訂單 B-1042」寫成 `{"category": "refund", "priority": 2, "order_id": "B-1042"}`。第 3 章已經介紹過它的三個保證層級；這一章要從 agent 建造者的角度問更實際的問題：它在系統裡出現在哪裡、壞掉時會造成什麼後果、每一層防線要放在哪裡。

在一個 agent system 裡，structured output 至少出現在五個地方。第一是 **tool call 的參數**：第 4 章的 `get_order(order_id="B-1042")` 本身就是一段結構化輸出，12-Factor Agents 的說法是「tool 就是 structured output」。第二是**最終答案**：像青鳥的處理確認卡，agent 的終點不是一段話，而是一個給下游系統的物件。第三是**路由與分類**：workflow 裡「這張工單交給哪個子流程」的判斷（第 18 章）。第四是**agent 之間的交接**：orchestrator 交給 subagent 的任務描述、subagent 回報的結果（第 20 章）。第五是**評估與監控**：LLM-as-judge 給出的分數與理由（第 27 章）。五個地方的共同點是，輸出的消費者是程式，而程式不會「大概看懂」。

```text
 模型的原始輸出（一段文字）
     │
     ▼
 (1) 擷取 extract ── 從文字中找出 JSON：去 code fence、去前言、配對括號
     │                失敗 ──► 語法錯誤
     ▼
 (2) 解析 parse ──── json.loads：字串 → dict／list
     │                失敗 ──► 語法錯誤（尾逗號、單引號、被截斷）
     ▼
 (3) Schema 驗證 ─── 型別、必填、enum、巢狀結構、union 分支
     │                失敗 ──► schema 錯誤（"1,200" 不是 integer、"退款" 不在 enum）
     ▼
 (4) 語意驗證 ────── 業務規則：訂單存在嗎？金額超過總額嗎？intent 與 action 一致嗎？
     │                失敗 ──► 語意錯誤（12,000 > 1,200）
     ▼
 (5) 轉成型別物件 ── dataclass：下游只拿到「已經通過全部檢查」的資料
     │
     ▼
 下游：確認卡 UI、退款 API、路由、資料庫
```

這張資料流圖就是老陳說的海關，由上到下有五道關卡。第 (1) 步處理「JSON 被包在文字裡」的問題，這是 prompt 指示最常見的失敗；第 (2) 步把文字變成資料結構，失敗代表語法壞了。第 (3) 步檢查「形狀」：每個欄位在不在、型別對不對、值是不是允許的那幾個。第 (4) 步檢查「內容」：形狀完全正確的資料，仍可能說出不可能的事，例如退款金額超過訂單總額，或引用一個不存在的訂單編號。第 (5) 步把通過的資料轉成有型別的物件，下游的程式碼因此可以放心地寫 `resolution.action.amount`，不必再到處防禦性地檢查。圖中左側每一個「失敗」都會在 7.7 節變成修復迴圈的輸入。

把關卡分層的好處，是每一層的錯誤有不同的成因與處理方式。下表整理 Iris 在週二看到的失敗，以及它們分別該在哪一層被擋下：

| 失敗現象 | 例子 | 發生在哪一層 | 根本原因 | 能不能在生成時就避免 |
|---|---|---|---|---|
| JSON 被包在文字裡 | 「好的，以下是結果：」加 code fence | 擷取 | 模型習慣用聊天格式回答 | 能：JSON mode 或 strict schema |
| 語法錯誤 | 尾逗號、單引號、少一個括號 | 解析 | 模型逐 token 生成，沒有語法檢查 | 能：JSON mode 以上 |
| 被截斷 | 輸出撞到 max_tokens，JSON 只有一半 | 解析 | 輸出上限太小或回覆太長 | 不能：要檢查 stop_reason |
| 型別錯誤 | 金額寫成 `"1,200"` | schema | 模型模仿人類書寫習慣 | 能：strict schema |
| enum 外的值 | 「退款」、`"refunded"` | schema | 模型用同義詞或翻譯 | 能：strict schema |
| 欄位缺漏或多出 | 少了 `reason`、多了 `note` | schema | 範例不完整、模型自行發揮 | 能：strict schema |
| 內容不可能 | 退款 12,000 元，訂單總額 1,200 元 | 語意 | 模型推理錯誤或看錯資料 | 不能：一定要程式驗證 |
| 內容捏造 | 引用不存在的訂單編號 | 語意 | 模型補齊它沒看到的資訊 | 不能：一定要程式驗證 |

這張表最重要的一欄是最後一欄。前六種失敗都屬於「形狀」問題，主流 API 的 strict 模式可以在生成時就消除大部分；但最後兩種是「內容」問題，任何解碼技術都無能為力，因為 12,000 是一個完全合法的整數。換句話說，**生成時的約束可以減少修復的次數，但永遠取代不了程式驗證**。常見的誤解是「開了 strict 就不用驗證」，另一個相反的誤解是「反正要驗證，就不必開 strict」：前者會讓語意錯誤直通下游，後者會讓大量可以免費避免的形狀錯誤變成要多付一輪模型呼叫的修復。

## 7.3 JSON Schema：寫給模型、也寫給程式的契約

**JSON Schema** 是描述 JSON 資料長相的標準格式：它本身也是一段 JSON，說明「這個物件有哪些欄位、各是什麼型別、哪些必填、值可以是哪些」。例如 `{"type": "object", "properties": {"priority": {"type": "integer"}}, "required": ["priority"]}` 的意思是「一個物件，必須有整數型別的 priority 欄位」。在 agent system 裡，同一份 schema 同時有兩個讀者：模型讀它來決定要產生什麼，程式讀它來檢查收到了什麼。這個雙重身分決定了 schema 的寫法：對程式來說它要精確，對模型來說它要好懂。

本章的驗證器只實作最常用的一小組關鍵字，但它們已經足以表達絕大多數 agent 的輸出：

| 關鍵字 | 意思 | 例子 | 寫給模型時的提醒 |
|---|---|---|---|
| `type` | 型別：object、array、string、integer、number、boolean、null | `{"type": "integer"}` | 金額用 integer（以「元」或「分」為單位），不要用帶千分位的字串 |
| `properties` | object 的每個欄位各自的 schema | `{"order_id": {...}}` | 欄位名稱要自我說明：`refund_amount` 比 `amt` 好 |
| `required` | 必填欄位清單 | `["order_id"]` | strict 模式通常要求全部列入，選填改用可為 null |
| `enum` | 只能是這幾個值之一 | `["refund", "shipping"]` | 值用穩定的英文代碼，顯示文字交給 UI 翻譯；保留 `other` |
| `const` | 只能是這一個值 | `{"const": "refund"}` | 用在 union 的標籤欄位 |
| `items` | array 裡每個元素的 schema | `{"items": {"type": "string"}}` | 需要時加上數量上限，避免模型列出幾百項 |
| `oneOf`／`anyOf` | 符合其中一個分支 | 退款、退貨、轉專人三選一 | 每個分支都要有標籤欄位（7.6 節） |
| `additionalProperties` | 是否允許 schema 沒列出的欄位 | `false` | 設成 false，避免模型夾帶自創欄位 |
| `description` | 給人與模型看的說明 | 「新台幣元，整數」 | 寫單位、格式、例子與何時填 null |

表中「寫給模型時的提醒」那一欄，才是 schema 設計真正的功夫。schema 的每個欄位都是在對模型下指令，而模型會照字面理解。以金額為例：如果欄位叫 `amount`、型別是 string，模型很自然地寫出 `"NT$1,200"`；改成 integer 並在 description 寫「新台幣元，整數，例如 1200」，問題就消失了大半。enum 也一樣：值用穩定的英文代碼（`not_needed`），而不是會被翻譯的顯示文字（「不需要了」），因為代碼是程式的契約，顯示文字是 UI 的責任，混在一起，下次產品要改文案就得動 schema。

選填欄位是另一個常見的設計點。直覺的寫法是「不放進 required 就是選填」，但主流 API 的 strict 模式普遍要求所有欄位都列在 required 裡，選填的意思改用「型別可以是 null」表達，例如 `"order_id": {"type": ["string", "null"]}`。這個限制看起來麻煩，其實讓語意更清楚：「欄位不存在」和「欄位存在但值是 null」在程式裡是兩回事，前者常常是模型漏了，後者才是模型明確地說「對話中沒有訂單編號」。在 description 裡寫清楚「什麼情況填 null」，模型就不會為了填滿欄位而捏造一個訂單編號。

還有一個容易被忽略的細節：**欄位順序**。模型是逐 token 從左到右生成的，多數實作會依 schema 中 properties 的順序產生欄位，所以先寫的欄位會影響後寫的欄位。如果需要模型先想清楚再下結論，可以把理由欄位（例如 `reasoning`）放在決策欄位之前；如果需要串流顯示回覆文字，就把 `customer_reply` 放在 `action` 之前，7.8 節會看到這個安排的效果。反過來，把 `decision` 放第一個、`reasoning` 放最後，理由往往只是在替已經做出的決定找說詞。至於推理模型，它們在輸出之前已經有獨立的思考階段，理由欄位對正確率的幫助通常比較小，但對稽核與除錯仍然有價值。

> [!warning] 常見誤解
> 「schema 越詳細、限制越多越安全。」限制要對應真實世界。enum 漏掉了真實存在的情況（例如物流狀態沒有 `delivered`），模型在 strict 模式下只能從允許的值裡挑一個「最接近」的錯誤答案，下一節會用程式重現這件事。好的 schema 要有出口：enum 保留 `other` 並搭配一個說明欄位，數值範圍留給語意驗證處理，而不是寫死在 schema 裡讓模型被迫說謊。

## 7.4 Constrained decoding 與 strict mode

只在 prompt 裡寫「請輸出 JSON」，是請求模型遵守格式；**constrained decoding**（受限解碼）則是讓模型在物理上無法違反格式。第 3 章介紹過它的直覺：模型每產生一個 token 之前，會對整個詞彙表給出機率分布，受限解碼在 sampling 之前，把「接上去之後就不可能符合 schema」的 token 機率設成零，再從剩下的候選中選。主流 API 把這個能力包裝成 **strict mode**（嚴格模式）：你提供 schema 並打開 strict，供應商保證回傳的 JSON 符合 schema。

```text
 schema 編譯成狀態機（只畫 status 欄位的值）

            "            s / sh         hipped / ipped       "
 [開始] ──────► (S0) ───────────► (S1) ──────────────► (S2) ────► [接受：shipped]
                  │
                  │ pen               ding                "
                  └──────────► (P1) ──────────► (P2) ────────────► [接受：pending]

 每一步：目前狀態 ──► 允許的 token 集合 ──► 把其餘 token 的機率設為 0 ──► sampling
 (S0) 允許 {s, sh, pen}    遮掉 {deli, 已, ...}
 (S1) 允許 {hipped, ipped} （依已輸出的是 s 或 sh 而定）
```

這張狀態機圖說明 strict mode 在底層做了什麼。供應商先把 schema 編譯成一個語法（grammar），再轉成可以逐步追蹤的狀態機：每個狀態代表「到目前為止輸出了什麼」，每條邊是一個允許的 token。解碼時，引擎記住目前在哪個狀態，只開放從這個狀態出發的邊，其餘 token 一律遮掉。這也解釋了第 3 章提過的現象：第一次使用新 schema 時，供應商需要額外時間編譯這個狀態機，之後才會快取起來。真實系統的難處在於 token 和 schema 的字元邊界不對齊（一個 token 可能同時包含引號、逗號和下一個欄位名稱的開頭），以及詞彙表有十萬個以上的 token，每一步都要有效率地算出遮罩；開源的受限解碼引擎主要就是在解決這兩個工程問題。

下面用一個極小的詞彙表重現這個過程。假模型看到的物流紀錄寫著「已簽收」，所以它最想輸出 `delivered` 或中文的「已出貨」；但 schema 的 enum 只有 `shipped` 和 `pending`，是 Iris 早期版本漏掉了 delivered。

```python
from __future__ import annotations

# 一個極小的「詞彙表」：真實 tokenizer 有十萬個以上的 token，原理相同
VOCAB = ['"', "s", "sh", "hipped", "ipped", "pen", "ding", "deli", "vered", "已", "出貨"]
ENUM = ["shipped", "pending"]                    # schema：status 只能是這兩個值


def model_scores(prefix: str) -> dict[str, float]:
    """假模型：看到「已簽收」的物流紀錄，它最想說 delivered 或中文的「已出貨」。"""
    nxt = {'"': {"deli": 0.40, "已": 0.30, "sh": 0.18, "pen": 0.07, "s": 0.05},
           "deli": {"vered": 0.90, "ding": 0.10},
           "已": {"出貨": 0.95, '"': 0.05},
           "sh": {"ipped": 0.80, "hipped": 0.20},
           "s": {"hipped": 0.90, "ipped": 0.10},
           "pen": {"ding": 0.95, "ipped": 0.05}}
    last = next((t for t in sorted(VOCAB, key=len, reverse=True) if prefix.endswith(t)), '"')
    return nxt.get(last, {'"': 1.0})              # 其他情況：結束這個字串


def allowed(prefix: str, token: str) -> bool:
    """接上 token 之後，是否仍可能長成某個合法值（含結尾的引號）？"""
    return any(f'"{v}"'.startswith(prefix + token) for v in ENUM)


def decode(constrained: bool) -> str:
    out = '"'                                    # 值的開頭引號由 schema 決定，直接寫入
    for step in range(1, 6):
        scores = model_scores(out)
        if constrained:                          # 遮罩：違反 schema 的 token 機率歸零
            scores = {t: p for t, p in scores.items() if allowed(out, t)}
        total = sum(scores.values())
        token = max(scores, key=scores.get)      # greedy：選機率最高的
        print(f"  step {step}: 已輸出 {out:<10} 可選 {sorted(scores)} → {token}（{scores[token] / total:.2f}）")
        out += token
        if out.endswith('"'):
            return out
    return out


print("不受限：")
free = decode(constrained=False)
print("受限解碼：")
strict = decode(constrained=True)
print("結果：", free, "vs", strict)
assert free == '"delivered"' and strict == '"shipped"'
```

```text
不受限：
  step 1: 已輸出 "          可選 ['deli', 'pen', 's', 'sh', '已'] → deli（0.40）
  step 2: 已輸出 "deli      可選 ['ding', 'vered'] → vered（0.90）
  step 3: 已輸出 "delivered 可選 ['"'] → "（1.00）
受限解碼：
  step 1: 已輸出 "          可選 ['pen', 's', 'sh'] → sh（0.60）
  step 2: 已輸出 "sh        可選 ['ipped'] → ipped（1.00）
  step 3: 已輸出 "shipped   可選 ['"'] → "（1.00）
結果： "delivered" vs "shipped"
```

「不受限」底下的三行：模型在第一步選了機率最高的 `deli`，接著自然地寫完 `delivered`，這是**正確的事實、錯誤的格式**，下游的 enum 檢查會拒絕它。「受限解碼」底下的三行：第一步的五個候選只剩三個（`deli` 和「已」被遮掉），剩下的機率重新正規化後，`sh` 從 0.18 變成 0.60 被選中，接著只剩 `ipped` 一條路，最後輸出 `shipped`。這是**正確的格式、錯誤的事實**：包裹明明已經簽收，卻被報告成剛出貨。

這個例子濃縮了 constrained decoding 最重要的一課：它保證的是「輸出屬於 schema 允許的集合」，而不是「輸出是真的」。當 schema 和真實世界不一致時，受限解碼不會讓模型說「你的選項不對」，而是逼它挑一個最接近的錯誤答案，而且這個錯誤答案格式完美，任何格式檢查都抓不到。所以 enum 的設計要覆蓋真實情況，或保留 `other` 與說明欄位；語意驗證要能比對來源資料（例如物流紀錄的原始狀態）。另一個常被討論的代價是格式約束可能影響推理品質：有研究（例如 Tam 等人 2024 年的〈Let Me Speak Freely?〉）報告在某些任務上，嚴格的格式限制會讓推理表現下降，也有後續討論認為影響大小取決於實作方式與 schema 設計。實務上的折衷是讓需要推理的部分先發生（推理模型的思考階段，或 schema 中排在前面的理由欄位），格式約束只套在最後的結論上。

strict mode 還有幾個實務限制。第一，各家支援的是 JSON Schema 的**子集**：常見的限制包括所有欄位必須列入 required、object 必須設 `additionalProperties: false`、部分關鍵字（例如字串格式、數值範圍、某些組合關鍵字）不支援或只支援一部分，根節點可能必須是 object。第二，strict 保證的是「完成的輸出」：如果模型因安全理由拒答，或輸出撞到 max_tokens，你拿到的可能是拒答訊息或半截 JSON，程式必須先檢查 stop_reason 或回應狀態，再進入解析。第三，strict 是供應商的能力，不是你的系統的能力：同一個 agent 換到一個不支援 strict 的模型，或者經過一個會改寫輸出的中介層，保證就消失了。因此 `loom` 的設計是「能開 strict 就開，但驗證永遠在」，把 strict 當成降低修復率的最佳化，而不是正確性的來源。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各家公開文件整理（參數名稱以官方文件為準）：OpenAI Responses API 以 `text: {format: {type: "json_schema", name, schema, strict: true}}` 要求結構化輸出，所有 object 需 `additionalProperties: false`、所有欄位列入 `required`、選填欄位以可為 null 的型別表示，支援 `$ref`／`$defs`，拒答以 `refusal` 類型回傳，`status: "incomplete"` 時要檢查原因；function tool 也可設定 `strict: true`。依 OpenAI 公開資料，另有 custom tools 可以用 CFG grammar 限制自由文字輸出（本書未逐項查證細節）。Anthropic 的 tool 定義可加 `strict: true` 保證 tool 參數符合 schema，最終答案的 JSON schema 格式設定請查官方 structured outputs 文件。Gemini 以 function calling 的 `validated` 模式保證呼叫符合 schema，legacy 介面用 `responseMimeType: application/json` 加 `responseSchema`／`responseJsonSchema`。自架模型方面，vLLM、SGLang、llama.cpp 等推論引擎都提供 JSON schema 或文法約束的生成功能，背後常見的開源引擎包括 Outlines、XGrammar、llguidance；各自支援的 schema 範圍與效能差異請以其文件為準。

## 7.5 用 dataclass 做 Pydantic 式的資料模型

有了 schema，下一個問題是：schema 寫在哪裡？Iris 最初的做法是在 prompt 裡手寫一份 JSON 範例，在程式裡另外寫一堆 `if "amount" in data and isinstance(...)`。兩份定義很快就不同步：有人在 prompt 加了 `tags` 欄位，忘了改程式；有人把程式的 enum 改了，prompt 裡還是舊的。業界通行的解法是 **single source of truth**（單一事實來源）：用程式語言的型別定義資料模型，從它**自動產生** schema 給模型，也用它**解析**模型的輸出。Python 生態裡最常見的是 Pydantic，TypeScript 生態則常用 Zod；主流 SDK 都能直接接受這類模型當作輸出格式。

這背後有一個更深的原則，常被稱為 **parse, don't validate**（解析，而不是驗證）：不要讓未經檢查的 dict 在程式裡到處流動、每個用到它的地方各自檢查一次；而是在邊界上一次完成檢查，並把結果轉成「型別本身就保證正確」的物件。通過邊界之後，`ticket.priority` 一定是整數，`ticket.category` 一定是四個值之一，下游程式碼不需要再寫任何防禦性檢查。對 agent 來說，這個邊界就是 7.2 節圖中的第 (5) 步。

本書只能用標準函式庫，所以下面用 `dataclass` 加上型別提示做一個最小版本：`Literal` 變成 enum、`X | None` 變成可為 null、`list[X]` 變成 array，欄位的 `metadata` 放 description。

```python
from __future__ import annotations

import dataclasses
import json
import types
from dataclasses import dataclass, field
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

PRIMITIVES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def to_schema(tp: Any) -> dict[str, Any]:
    """把型別提示翻成 JSON Schema：同一份 dataclass 同時是 prompt 裡的 schema 與程式裡的型別。"""
    origin, args = get_origin(tp), get_args(tp)
    if tp in PRIMITIVES:
        return {"type": PRIMITIVES[tp]}
    if origin is Literal:                                    # Literal["a", "b"] → enum
        return {"type": "string", "enum": list(args)}
    if origin is list:
        return {"type": "array", "items": to_schema(args[0])}
    if origin in (Union, types.UnionType) and type(None) in args:   # X | None → 可為 null
        inner = to_schema(next(a for a in args if a is not type(None)))
        return {**inner, "type": [inner["type"], "null"]}
    if dataclasses.is_dataclass(tp):
        hints = get_type_hints(tp)
        props = {}
        for f in dataclasses.fields(tp):
            props[f.name] = to_schema(hints[f.name])
            if "desc" in f.metadata:
                props[f.name]["description"] = f.metadata["desc"]
        # strict 模式的慣例：所有欄位都列為 required，選填用「可為 null」表示
        return {"type": "object", "properties": props, "required": list(props),
                "additionalProperties": False}
    raise TypeError(f"不支援的型別：{tp}")


def from_dict(tp: Any, data: Any) -> Any:
    """Parse, don't validate：通過這一關的資料，就是有型別的物件，下游不必再檢查。"""
    if dataclasses.is_dataclass(tp):
        hints = get_type_hints(tp)
        return tp(**{f.name: from_dict(hints[f.name], data[f.name]) for f in dataclasses.fields(tp)})
    if get_origin(tp) is list:
        return [from_dict(get_args(tp)[0], x) for x in data]
    return data


@dataclass
class Ticket:
    """客服工單的分類結果。"""
    category: Literal["refund", "shipping", "account", "other"] = field(
        metadata={"desc": "工單類別；無法歸類時用 other"})
    order_id: str | None = field(metadata={"desc": "訂單編號，例如 B-1042；對話中沒有就填 null"})
    priority: int = field(metadata={"desc": "1 最急，5 最不急"})
    tags: list[str] = field(default_factory=list)


schema = to_schema(Ticket)
for name, spec in schema["properties"].items():
    extra = f" enum={spec['enum']}" if "enum" in spec else ""
    print(f"{name:<9} type={json.dumps(spec['type'])}{extra}")
ticket = from_dict(Ticket, {"category": "refund", "order_id": None, "priority": 2, "tags": ["vip"]})
print(ticket)
assert schema["required"] == ["category", "order_id", "priority", "tags"]
assert schema["properties"]["order_id"]["type"] == ["string", "null"]
assert ticket.category == "refund" and ticket.order_id is None
```

```text
category  type="string" enum=['refund', 'shipping', 'account', 'other']
order_id  type=["string", "null"]
priority  type="integer"
tags      type="array"
Ticket(category='refund', order_id=None, priority=2, tags=['vip'])
```

輸出的前四行是從 `Ticket` 自動產生的 schema：`category` 的 `Literal` 變成了 string 加 enum，`order_id: str | None` 變成 `["string", "null"]`，`priority` 是 integer，`tags` 是 array。assert 驗證了一件重要的事：四個欄位**全部**被列進 required，包括有預設值的 `tags` 和可為 null 的 `order_id`，這正是 strict 模式的慣例，選填的語意由 null 表達。最後一行是用同一個型別解析出來的物件，型別檢查器與 IDE 都能看懂它。

這個最小版本省略了很多 Pydantic 會做的事，值得知道差距在哪裡：它沒有驗證就直接建立物件（本章的驗證器在 7.10 節，實務上要先驗證再 `from_dict`），不支援巢狀 union 的自動標籤，不做型別轉換（Pydantic 預設的寬鬆模式會把字串 `"2"` 轉成整數 2，嚴格模式則拒絕），也沒有欄位層級的自訂驗證器。型別轉換尤其值得討論：把 `"2"` 轉成 2 看起來很貼心，但把 `"1,200"` 轉成 1200 就已經是在猜測語意了（是一千兩百，還是歐洲寫法的一點二？）。`loom` 的選擇是 schema 層不做任何轉換，形狀不對就退回給模型修，讓所有「猜測」都留下紀錄。

> [!tip]
> 資料模型的 description 就是 prompt 的一部分，而且是離決策最近的那一部分。與其在 system prompt 裡寫一段「priority 的判斷標準」，不如直接寫在 `priority` 欄位的 description 裡：模型產生這個欄位時，說明就在 schema 中對應的位置。第 6 章談 system prompt 的抽象高度時，同樣的原則也適用：欄位層級的規則放在欄位旁邊。

## 7.6 Enum 與 discriminated union：表達「多種動作擇一」

青鳥的處理確認卡有一個難題：agent 建議的動作有三種，每一種需要的欄位都不同。退款需要訂單編號、金額與理由；建立退貨單需要訂單編號與取件時間；轉給專人需要隊列名稱與摘要。Iris 的第一版把所有欄位攤平成一個大物件，`amount`、`pickup`、`queue` 全部設成選填，結果模型經常產生「type 是退貨，卻填了退款金額」這種自相矛盾的組合，程式還得寫一大串 if 判斷哪些欄位在什麼情況下該出現。

更好的表達方式是 **discriminated union**（帶標籤的聯集，也叫 tagged union）：一個值是「幾種形狀中的恰好一種」，並用一個共同的**標籤欄位**（discriminator，通常叫 `type` 或 `kind`）標明是哪一種。例如 `{"type": "refund", "order_id": ..., "amount": ...}` 和 `{"type": "escalate", "queue": ..., "summary": ...}` 是同一個 union 的兩個分支。每個分支只列自己需要的欄位，而且全部必填，自相矛盾的組合在 schema 層就不可能存在。

```text
 action 的值
     │
     ▼
 讀標籤欄位 type ─────────────────────────────────────────────┐
     │                                                       │ 不是三者之一
     ├─ "refund" ────────► 只驗證 refund 分支                  ▼
     │                    order_id: string  （必填）       錯誤：/action/type 必須是
     │                    amount:   integer （必填）       ["refund","create_return",
     │                    reason:   enum    （必填）        "escalate"] 之一
     │
     ├─ "create_return" ─► 只驗證 create_return 分支
     │                    order_id、pickup
     │
     └─ "escalate" ──────► 只驗證 escalate 分支
                          queue: enum、summary: string

 沒有標籤時：把值拿去和三個分支逐一比對 ──► 0 個符合 ──► 「不符合任何分支」
                                       （不知道模型「想要」哪一支，說不出哪裡錯）
```

這張決策圖說明標籤欄位的兩個價值。第一個價值在驗證：有標籤時，驗證器先讀 `type`，只拿對應的那一個分支來檢查，所以錯誤訊息可以精確到「refund 分支的 amount 應該是 integer」；沒有標籤時，驗證器只能把值和每個分支逐一比對，三支都不符合，它唯一能說的是「不符合任何分支」，模型拿到這種錯誤訊息幾乎不可能修對。第二個價值在下游：程式拿到通過驗證的 action，只要 `match action["type"]` 就能分派到對應的處理函式，和第 4 章 dispatch 依 tool 名稱分派是同一個模式。事實上，tool call 本身就是一個以 tool 名稱為標籤的 discriminated union。

標籤設計有幾個實務要點。標籤值用動詞或名詞的穩定代碼（`refund`、`create_return`），不要用顯示文字；每個分支的標籤欄位用 `const` 固定，讓 schema 本身就說明「這一支的 type 只能是 refund」；分支數量多時，在 description 裡用一句話說明每一支的適用情況，這比任何範例都更能幫助模型選對分支。另外要知道一個標準上的細節：`discriminator` 這個關鍵字來自 OpenAPI 規格，純 JSON Schema 並沒有定義它；在純 JSON Schema 中，標籤的效果是靠每個分支裡的 `const` 達成的，驗證器能不能利用它產生精準的錯誤訊息，取決於實作。本章的驗證器兩者都支援：有 `discriminator` 就直接查表，沒有就退回逐支比對。

| 表達「多種動作擇一」的方式 | 例子 | 優點 | 缺點 | 適合 |
|---|---|---|---|---|
| 攤平成一個物件，欄位全部選填 | `{type, order_id?, amount?, queue?}` | schema 最短 | 允許自相矛盾的組合；驗證邏輯散落在程式裡 | 不建議 |
| 沒有標籤的 oneOf／anyOf | 三個分支各自列欄位 | 形狀精確 | 錯誤訊息模糊；分支重疊時會同時符合多支 | 分支極少且形狀差異大 |
| Discriminated union | 每支有 `type: const` | 驗證精準、下游分派簡單、可擴充 | schema 較長 | 動作、事件、訊息類型 |
| 每種動作一個 tool | `refund()`、`create_return()` | 沿用 tool 機制；可各自設權限 | 「恰好選一個」要靠 prompt 或 tool_choice | agent loop 中的行動 |

最後一列值得多說一句。在 agent loop 裡，「多種動作擇一」最自然的表達其實是多個 tool：模型呼叫哪個 tool，就等於選了哪個分支，而且每個 tool 可以有各自的權限與核准政策（第 21 章）。青鳥的確認卡之所以用 union 而不是 tool，是因為這裡的動作不會被立即執行，而是要先呈現給客服核准；它是一份**提案**，不是一個**呼叫**。判斷準則是：如果輸出的下一步是「立刻執行」，用 tool；如果下一步是「呈現、儲存、審核或交給另一個系統」，用 structured output 的 union。

## 7.7 驗證與修復迴圈

即使開了 strict，驗證仍會失敗：語意錯誤 strict 管不到，有些模型或部署環境不支援 strict，輸出也可能被截斷。失敗之後怎麼辦？最簡單的答案是「再問一次」，但「怎麼問」決定了第二次會不會成功。這一節的主角是 **validate-and-repair loop**（驗證與修復迴圈）：驗證失敗時，先嘗試不改變語意的本地修復；仍然失敗，就把具體的錯誤回饋給模型、要求它修正，並設定次數上限，用完就走後備路徑。

### 第一步：只做不改變語意的本地修復

有些錯誤不值得多付一輪模型呼叫：code fence、前後的說明文字、尾逗號，都可以用確定性的程式修好，而且修完的資料和模型「想表達的」完全相同。判斷準則是：**修復前後的語意必須一樣**。去掉 code fence 沒有改變任何資料；但把 `"1,200"` 轉成 1200、把「退款」對應到 `refund`，都是在替模型做決定，應該退回給模型。

擷取 JSON 本身也有陷阱。Iris 的 regex `\{.*\}` 是貪婪比對，會一路吃到文字中最後一個右大括號。下面的程式重現週二的第二個事故，並示範正確做法：從第一個左大括號開始掃描，追蹤「是否在字串裡」與跳脫字元，找到配對的右大括號。

```python
from __future__ import annotations

import json
import re

# 模型的回應：前言、JSON、再加一句帶大括號的補充說明
reply = '好的，結果如下：{"intent": "refund", "note": "客戶說 \\"{急件}\\""} 如有問題請告訴我 {謝謝}'

greedy = re.search(r"\{.*\}", reply).group(0)        # Iris 的第一版：貪婪比對到最後一個 }
try:
    json.loads(greedy)
except json.JSONDecodeError as exc:
    print("貪婪 regex：", greedy[-22:], "→", exc.msg)


def first_json_object(text: str) -> str:
    """從第一個 { 開始掃描，追蹤字串與跳脫字元，找到配對的 }。字串裡的括號不算數。"""
    start = text.index("{")
    depth, in_str, escaped = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if escaped:
                escaped = False                    # 這個字元被跳脫，不具特殊意義
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("JSON 沒有結束：輸出可能被截斷")


obj = json.loads(first_json_object(reply))
print("配對掃描：", obj)
assert obj["note"] == '客戶說 "{急件}"'
```

```text
貪婪 regex： {急件}\""} 如有問題請告訴我 {謝謝} → Extra data
配對掃描： {'intent': 'refund', 'note': '客戶說 "{急件}"'}
```

第一行是貪婪 regex 的結果：它抓到的字串一直延伸到最後的「{謝謝}」，`json.loads` 解析完第一個物件後發現後面還有東西，回報 `Extra data`。第二行是配對掃描的結果：它知道 `\"{急件}\"` 在字串裡面，這對括號不影響深度計算，所以在物件真正結束的地方停下，note 欄位完整保留了顧客原文的引號與括號。這個掃描器在找不到配對時會丟出「可能被截斷」的錯誤，這比回傳半截字串讓下游自己出錯好得多。

### 第二步：帶著具體錯誤重問

本地修復之後仍然不合格，就要回到模型。修復提示的品質，取決於錯誤訊息是否告訴模型三件事：**哪裡錯**（用 JSON Pointer 這種路徑表示法，例如 `/action/amount`，指向巢狀結構中的確切位置）、**錯成什麼**（實際收到 `"1,200"`）、**應該長怎樣**（integer；或允許值清單）。這和第 4 章「可行動的錯誤訊息」是同一個原則，只是對象從 tool 錯誤換成了格式錯誤。

```text
 harness                                         Model
   │── (1) messages＋schema ────────────────────►│
   │◄──────────────────── 輸出 #1：code fence＋JSON ─│
   │ 擷取、本地修復：去 fence、去尾逗號             │
   │ schema 驗證：2 個錯誤                          │
   │   /action/amount  應為 integer，收到 "1,200"   │
   │   /action/reason  "退款" 不在允許值中          │
   │                                                │
   │── (2) 原歷史＋assistant: 輸出 #1 ──────────────►│
   │       ＋user: 「請只輸出修正後的完整 JSON：     │
   │               - /action/amount ...             │
   │               - /action/reason ...」           │
   │◄──────────────────────────── 輸出 #2：修正版 ─│
   │ schema 通過 → 語意驗證通過 → 轉成型別物件      │
   │                                                │
   │ 若到第 N 次仍失敗：status=failed ──► 後備路徑  │
   │   （轉真人、退回較簡單的流程、回傳明確錯誤）   │
```

這張時序圖是 7.10 節情境 A 的實際流程。第 (1) 輪，模型的輸出經過本地修復後仍有兩個 schema 錯誤。第 (2) 輪，harness 不是從頭再問一次，而是把模型的錯誤輸出留在歷史裡（作為 assistant 訊息），再附上一則 user 訊息列出具體錯誤。保留原輸出有兩個好處：模型可以只改錯的地方，不必重新推理整個問題；錯誤訊息裡的路徑也有了對照的對象。代價是 context 變長、每一輪都更貴，所以修復迴圈的次數上限通常很小（兩到三次），而且只對可能修好的錯誤重試。圖的最後一段是重試用完的後備路徑：在青鳥的情境裡，就是不產生確認卡，直接轉給真人客服並附上最後一次的錯誤。

不是每種錯誤都值得重試。下表是 `loom` 對各層錯誤的預設政策：

| 錯誤層 | 例子 | 本地修復 | 重問模型 | 上限與後備 |
|---|---|---|---|---|
| 擷取 | code fence、前言、後記 | 是 | 否 | 修不好才當語法錯誤 |
| 語法 | 尾逗號 | 是 | 少見才需要 | 1–2 次 |
| 語法 | 被截斷（max_tokens） | 否 | 是，但要調高上限或要求縮短 | 1 次；再失敗就轉人工 |
| Schema | 型別、enum、缺欄位 | 否（不猜語意） | 是，附路徑與允許值 | 2 次 |
| 語意：可修 | 金額超過總額、intent 與 action 矛盾 | 否 | 是，附具體規則 | 1–2 次 |
| 語意：不可修 | 訂單根本不存在、使用者要求超出權限 | 否 | 否 | 直接走後備，不浪費重試 |
| 拒答 | 模型因安全理由拒絕 | 否 | 否 | 記錄並轉人工 |

這張表有兩個判斷值得解釋。第一，被截斷的輸出不要用同樣的設定重試，因為同樣的上限多半會在同樣的地方截斷；要嘛提高輸出上限，要嘛在修復提示中要求縮短某個欄位（例如 `customer_reply`）。第二，語意錯誤要區分「模型能修」和「模型修不好」：金額超過總額，模型讀了規則可以改成正確的金額或改建退貨單；訂單根本不存在，代表模型缺少資訊，重問只會得到另一個捏造的編號，應該讓 agent 回頭去問使用者或查資料，而不是在修復迴圈裡打轉。這和第 4 章「模型能不能靠改變行為修正它」的判斷完全相同。

修復迴圈還有幾個容易踩的坑。一是**無限重試的成本**：每次重試都是一次完整的模型呼叫，而且 context 一次比一次長；如果有 2% 的輸出需要一次修復，平均成本只增加約 2% 多一點，但如果某個 prompt 改版讓失敗率升到 30%，修復迴圈會悄悄把帳單和延遲放大，所以修復次數一定要當成指標監控（第 29 章）。二是**重試掩蓋問題**：修復迴圈成功率很高時，團隊容易忽略根因；每一類反覆出現的修復，都應該回頭改 schema、description 或 prompt。三是**修復提示也是 prompt**：它可能被使用者內容影響，錯誤訊息中引用的值（例如模型輸出的字串）要截斷，避免把一大段可能含有注入指令的內容原封不動地放回 context（第 31 章）。

> [!warning] 常見誤解
> 「修復迴圈用 temperature 0 重問同一個問題就好。」不附錯誤訊息的重問，等於期待模型碰運氣。在 temperature 0 的設定下，同樣的輸入很可能得到同樣的錯誤輸出，白白多付一輪。修復的價值在於**新資訊**：具體的錯誤路徑、允許值、違反的規則。沒有新資訊，就沒有理由期待不同的結果。

## 7.8 部分輸出與 streaming 解析

第 4 章說過 streaming 的原則：文字可以邊收邊顯示，tool 參數要等完整才執行。structured output 讓這條原則變得更細緻，因為一份 JSON 裡同時有「適合邊收邊顯示的部分」（`customer_reply` 是一段給顧客看的文字）和「必須完整才能使用的部分」（`action` 是要交給退款 API 的指令）。阿哲要的打字效果，和 Maya 擔心的「收到 `B-10` 就去退款」，是同一個問題的兩面：我們需要一個能解析**還沒結束的 JSON** 的解析器，並且清楚地知道每個欄位是「還在變」還是「已經確定」。

標準的 `json.loads` 對這件事無能為力：只要文件沒結束，它就丟出錯誤。**partial JSON parsing**（部分 JSON 解析）的作法是寫一個容忍「文件突然結束」的解析器：遇到沒結束的字串，就回傳目前收到的部分並標記為未完成；遇到沒結束的物件或陣列，就回傳目前有的欄位；遇到可能還沒寫完的數字或 `true`／`false`／`null`，就先不回傳，因為 `12` 可能是 `120` 的前綴，`tr` 也還不是任何值。

```text
 時間 ─────────────────────────────────────────────────────────────────────►
 收到的前綴         {"intent": "refund", "customer_reply": "已為您申請退款 1,2 ... "action": {"type": "refund", "order_id": "B-10 ... "B-1042", ...}}
                         │                         │                                         │                            │
 parse_partial      intent 確定               reply 未完成（可顯示）                  action 未完成                   全部確定
                                                   │                                  order_id="B-10"（危險）              │
 UI                 顯示「退款」標籤          逐字顯示回覆文字                        卡片顯示「處理中」             顯示完整確認卡
 下游               ─                        ─                                       不執行、不查詢               驗證通過後才允許核准
```

這張時序圖把一次串流拆成四個時間點。第一個時間點，`intent` 的字串已經收到結尾引號，解析器把它標記為「確定」，UI 可以先顯示分類標籤。第二個時間點，`customer_reply` 正在進行中，它的值每收到一段就變長，UI 逐字顯示，這就是阿哲要的打字效果。第三個時間點最危險：`action` 物件剛開始，`order_id` 只收到 `B-10`。這是一個格式完全正確的字串，如果程式看到「有 order_id」就去查訂單，就會查到一張完全不同的訂單，或者更糟。第四個時間點，整個物件結束，所有欄位都確定，這時才進入 7.7 節的驗證流程，通過之後才讓客服按核准。

從這張圖可以整理出串流解析的三條規則。第一，**顯示可以樂觀，動作必須保守**：未完成的字串可以顯示給人看，因為人看到半句話不會造成副作用；但任何會觸發查詢、寫入或分支判斷的程式邏輯，只能使用已確定的欄位。第二，**「欄位確定」不等於「整份通過驗證」**：`action` 物件結束了，代表它不會再變，但它仍可能違反 schema 或業務規則，所以有副作用的動作要等整份文件完成並通過驗證。第三，**欄位順序是 UX 設計**：把要串流顯示的欄位放在前面、要執行的欄位放在後面，使用者才能早點看到內容；反過來排，UI 要等到 action 寫完才看得到第一個字。7.10 節的程式會實作這個解析器，並追蹤每個欄位何時從「還在變」變成「已確定」。

串流解析還要注意兩個邊界情況。一是跳脫序列被切在半路，例如 `\u7` 只收到一部分，解析器不能把它當成字面字元顯示，要等完整的六個字元到齊；中文在 JSON 中如果被編碼成 `\uXXXX`，這個情況會很常見，所以輸出端最好不要強制 ASCII 編碼。二是串流中斷：和第 4 章一樣，中斷之後收到的部分全部作廢，已經顯示在畫面上的半段回覆要標示為「重新產生中」，不能把半截的物件當成最終結果送去驗證。主流 SDK 與框架大多提供「部分物件」的串流介面，讓前端直接拿到逐步長大的物件，但「哪些欄位已經確定」的判斷，以及「何時可以執行」的決定，仍然是你的應用程式要負責的。

## 7.9 何時讓模型輸出程式碼而非 JSON

JSON 很適合表達「一個決定」：分類、抽取出的欄位、一個帶參數的動作。但有些輸出天生不是一個決定，而是一串有邏輯的步驟，例如「先查這三張訂單，把金額加總，超過 5,000 元的標記為大額」。硬要用 JSON 表達，你會發明出一個有迴圈、條件與變數的 JSON 格式，這時其實是在重新發明一個很難用的程式語言。這一節討論輸出格式的光譜：自由文字、JSON、領域特定語言、程式碼，各自適合什麼。

**CodeAct** 是這個方向的代表研究（Wang 等人，2024）：讓模型直接輸出可執行的 Python 作為行動，而不是一個一個的 JSON tool call。論文在其基準上報告，程式碼作為行動的成功率比 JSON 或文字格式更高，理由很直觀：程式碼天生能表達迴圈、條件、變數與組合，模型在訓練資料中也看過大量程式碼。smolagents 的 CodeAgent 是知名的實作；主流 API 推出的 programmatic tool calling 與 code mode，也是讓模型寫一段程式去呼叫多個 tool，只把最終結果帶回 context。第 13 章會深入討論 code-as-action 的 token 與正確率取捨，第 17 章討論執行它所需要的 sandbox。

| 輸出格式 | 適合的任務 | 可驗證性 | 主要風險 | 青鳥的例子 |
|---|---|---|---|---|
| 自由文字 | 給人看的回覆、摘要、說明 | 低：只能靠 eval 或另一個模型評分 | 下游程式無法可靠使用 | 給顧客的回覆內容 |
| JSON（strict schema） | 單一決定、分類、抽取、帶參數的動作 | 高：schema＋語意驗證 | schema 與真實世界不一致時被迫說謊 | 處理確認卡、工單分類 |
| 領域特定語言或受限格式 | 結構固定的編輯、查詢、設定 | 中到高：可以寫專用 parser 與 linter | 格式需要教模型；設計成本 | 報表篩選條件、程式碼的 diff |
| 程式碼 | 多步驟計算、組合多個 tool、資料處理 | 中：可以執行與測試，但行為難以事先證明 | 需要 sandbox；權限與副作用控制更難 | 營運 research agent 的月度分析 |

這張表的判斷軸是「輸出的結構複雜度」與「可驗證性」的取捨。JSON 的可驗證性最高，因為它的形狀可以被 schema 完整描述、每個值可以被規則檢查；程式碼的表達能力最高，但「這段程式會做什麼」無法只靠看就完全確定，只能在 sandbox 裡執行、用測試或結果檢查。所以準則是：**能用 JSON 表達的決定就用 JSON；當你發現自己在 JSON 裡發明迴圈與變數時，改用程式碼，並把驗證從「檢查形狀」改成「在隔離環境中執行並檢查結果」**。中間那一列常被忽略：coding agent 修改檔案時，業界常見的不是把整個檔案包進 JSON，而是用專門的編輯格式，例如「指定要被取代的原文與新內容」的字串取代工具，或統一 diff 格式，因為這些格式對模型來說好寫、對程式來說好驗證（原文找不到就是錯）。

還有一個實務上的混合做法：**JSON 包文字**。例如處理結果中 `customer_reply` 是自由文字，`action` 是結構化資料，兩者放在同一個 JSON 裡；或者讓模型先自由地寫出分析，再用第二次呼叫（或同一次的後段）把結論抽成 JSON。混合時要注意，自由文字欄位裡的內容不要被下游程式當成指令解析，它只是要顯示給人的資料；這也是 Maya 在第 31 章會反覆強調的原則：模型的輸出要當成不可信輸入處理。

## 7.10 動手做：驗證器、修復迴圈與串流解析

這一節把本章的機制寫成兩段可以獨立執行的程式。第一段實作小型 JSON Schema 驗證器（type、required、enum、const、properties、items、additionalProperties，以及帶 discriminator 的 oneOf），再用它組成 validate-and-repair 迴圈，用 ScriptedModel 重現週二的事故：第一次給出包在 code fence 裡、型別與 enum 都錯的 JSON，第二次讀了修復提示後修好；另一個情境是重試用完、走後備路徑。第二段實作串流的部分 JSON 解析器，追蹤處理結果的每個欄位何時可以顯示、何時可以執行。

### 第一部分：驗證器與 validate-and-repair 迴圈

程式的結構對應 7.2 節的五道關卡：`extract_json` 是擷取與本地修復，`json.loads` 是解析，`validate` 是 schema 驗證，`business_rules` 是語意驗證，`structured_call` 把它們串成有次數上限的迴圈。`validate` 回傳的每則錯誤都以 JSON Pointer 開頭，這是修復提示品質的關鍵。為了讓程式短一點，`extract_json` 用「第一個左大括號到最後一個右大括號」做擷取，真實系統應該換成 7.7 節的配對掃描。

```python
from __future__ import annotations

import json
import re
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


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


# ───────── 第一部分：小型 JSON Schema 驗證器（type、required、enum、const、properties、items、oneOf）─────────
JSON_TYPES: dict[str, Callable[[Any], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),   # Python 的 True 也是 int
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def jtype(v: Any) -> str:
    return next(t for t in ("null", "boolean", "integer", "number", "string", "array", "object") if JSON_TYPES[t](v))


def validate(value: Any, schema: dict, path: str = "") -> list[str]:
    """回傳錯誤清單；每則錯誤以 JSON Pointer 開頭，讓模型知道「哪裡」錯、「該長怎樣」。"""
    where, errors = path or "/", []
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(JSON_TYPES[t](value) for t in allowed):     # 型別錯了，底下的檢查都沒有意義
            return [f"{where}: 型別應為 {'|'.join(allowed)}，實際是 {jtype(value)} {json.dumps(value, ensure_ascii=False)}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: 必須是 {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {json.dumps(value, ensure_ascii=False)} 不在允許值 {json.dumps(schema['enum'])} 中")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errors += [f"{path}/{k}: 缺少必填欄位" for k in schema.get("required", []) if k not in value]
        for k, v in value.items():
            if k in props:
                errors += validate(v, props[k], f"{path}/{k}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}/{k}: 不允許的欄位，可用欄位為 {list(props)}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors += validate(item, schema["items"], f"{path}/{i}")
    if "oneOf" in schema:
        errors += validate_one_of(value, schema, path)
    return errors


def validate_one_of(value: Any, schema: dict, path: str) -> list[str]:
    branches = schema["oneOf"]
    disc = schema.get("discriminator", {}).get("propertyName")
    if disc and isinstance(value, dict):          # 有標籤：只驗證標籤指定的那一支，錯誤訊息才會精準
        by_tag = {b["properties"][disc]["const"]: b for b in branches}
        if value.get(disc) not in by_tag:
            return [f"{path}/{disc}: 必須是 {list(by_tag)} 之一，實際是 {value.get(disc)!r}"]
        return validate(value, by_tag[value[disc]], path)
    passed = [b for b in branches if not validate(value, b, path)]
    if len(passed) == 1:
        return []
    return [f"{path or '/'}: 應恰好符合 1 個 oneOf 分支，實際符合 {len(passed)} 個（共 {len(branches)} 個）"]


# ───────── 青鳥客服的「處理結果」schema：action 是以 type 為標籤的 discriminated union ─────────
def branch(tag: str, props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": {"type": {"const": tag}, **props},
            "required": ["type", *required], "additionalProperties": False}


ORDER_ID = {"type": "string", "description": "訂單編號，例如 B-1042"}
ACTION = {"oneOf": [
    branch("refund", {"order_id": ORDER_ID, "amount": {"type": "integer", "description": "新台幣元，整數"},
                      "reason": {"enum": ["damaged", "wrong_item", "not_needed", "other"]}},
           ["order_id", "amount", "reason"]),
    branch("create_return", {"order_id": ORDER_ID, "pickup": {"type": "string"}}, ["order_id", "pickup"]),
    branch("escalate", {"queue": {"enum": ["billing", "logistics", "general"]}, "summary": {"type": "string"}},
           ["queue", "summary"]),
], "discriminator": {"propertyName": "type"}}
RESOLUTION = {"type": "object", "additionalProperties": False,
              "required": ["intent", "customer_reply", "action", "tags"],
              "properties": {"intent": {"enum": ["refund", "return", "shipping", "other"]},
                             "customer_reply": {"type": "string"}, "action": ACTION,
                             "tags": {"type": "array", "items": {"enum": ["urgent", "vip", "repeat_contact"]}}}}

bad_action = {"type": "refund", "order_id": "B-1042", "amount": "1,200", "reason": "退款"}
no_tag = {k: v for k, v in ACTION.items() if k != "discriminator"}
print("有 discriminator：", validate(bad_action, ACTION, "/action"))
print("沒有 discriminator：", validate(bad_action, no_tag, "/action"))
assert len(validate(bad_action, ACTION, "/action")) == 2


# ───────── 第二部分：validate-and-repair 迴圈 ─────────
FENCE = "`" * 3
ORDERS = {"B-1042": {"total": 1200, "status": "delivered"}}


def extract_json(text: str) -> tuple[str, list[str]]:
    """確定性的本地修復：只做「不會改變語意」的修正，並記錄做了什麼。"""
    fixes = []
    if (m := re.search(FENCE + r"(?:json)?\s*(.*?)" + FENCE, text, re.S)):
        text, fixes = m.group(1).strip(), ["去掉 code fence"]
    start, end = text.find("{"), text.rfind("}")
    if start < 0:
        raise ValueError("回應中找不到 JSON 物件")
    if end < start:
        raise ValueError("JSON 物件沒有結束，輸出可能被截斷")
    if start > 0 or end < len(text) - 1:
        fixes.append("去掉前後的說明文字")
    body = text[start:end + 1]           # 簡化：真實系統要用 7.7 節的配對掃描
    cleaned = re.sub(r",\s*([}\]])", r"\1", body)
    if cleaned != body:
        fixes.append("移除尾逗號")
    return cleaned, fixes


def business_rules(obj: dict) -> list[str]:
    """語意驗證：schema 管不到的事，例如訂單是否存在、金額是否超過訂單總額。"""
    a = obj["action"]
    if "order_id" in a and a["order_id"] not in ORDERS:
        return [f"/action/order_id: 找不到訂單 {a['order_id']}，不要自行編造編號"]
    if a["type"] == "refund" and a["amount"] > ORDERS[a["order_id"]]["total"]:
        return [f"/action/amount: {a['amount']} 超過訂單總額 {ORDERS[a['order_id']]['total']}"]
    return []


@dataclass
class Parsed:
    status: str                          # ok｜failed
    value: dict | None
    attempts: list[dict]


def structured_call(model: ScriptedModel, messages: list[dict], max_attempts: int = 3) -> Parsed:
    history, attempts = list(messages), []
    for n in range(1, max_attempts + 1):
        resp = model.complete(history, system="只輸出符合 schema 的 JSON：" + json.dumps(RESOLUTION))
        fixes: list[str] = []
        if resp.stop_reason == "max_tokens":
            layer, errors = "截斷", ["輸出被截斷，請縮短 customer_reply"]
        else:
            try:
                raw, fixes = extract_json(resp.text)
                value = json.loads(raw)
                layer, errors = "schema", validate(value, RESOLUTION)
                if not errors:
                    layer, errors = "語意", business_rules(value)
            except ValueError as exc:    # json.JSONDecodeError 是 ValueError 的子類別
                layer, errors = "語法", [f"JSON 無法解析：{exc}"]
        attempts.append({"n": n, "layer": layer, "fixes": fixes, "errors": errors})
        if not errors:
            return Parsed("ok", value, attempts)
        # 修復提示：原輸出留在歷史裡，錯誤用條列給出路徑，要求「只回修正後的 JSON」
        history += [{"role": "assistant", "content": resp.text},
                    {"role": "user", "content": "上一個輸出沒有通過驗證，請只輸出修正後的完整 JSON：\n"
                                                + "\n".join(f"- {e}" for e in errors)}]
    return Parsed("failed", None, attempts)


def show(title: str, r: Parsed) -> None:
    print(f"── {title}：status={r.status}")
    for a in r.attempts:
        print(f"  第 {a['n']} 次  本地修復={a['fixes'] or '無'}  {'通過' if not a['errors'] else '失敗於 ' + a['layer']}")
        for e in a["errors"]:
            print(f"      {e}")


first = (f'好的，以下是處理結果：\n{FENCE}json\n{{"intent": "refund", "customer_reply": "已為您申請退款。", '
         f'"action": {{"type": "refund", "order_id": "B-1042", "amount": "1,200", "reason": "退款"}}, '
         f'"tags": ["vip",],}}\n{FENCE}')
fixed = json.dumps({"intent": "refund", "customer_reply": "已為您申請退款 1,200 元，3–5 個工作天入帳。",
                    "action": {"type": "refund", "order_id": "B-1042", "amount": 1200, "reason": "not_needed"},
                    "tags": ["vip"]}, ensure_ascii=False)
# 劇本第二步是函式：只有在修復提示真的指出 /action/amount 時，「模型」才修得好
model = ScriptedModel([say(first), lambda msgs: say(fixed if "/action/amount" in msgs[-1]["content"] else first)])
r1 = structured_call(model, [{"role": "user", "content": "B-1042 我不需要了，可以退款嗎？"}])
show("情境 A 第一次錯、第二次修好", r1)
assert r1.status == "ok" and r1.value["action"]["amount"] == 1200 and len(model.calls) == 2
assert "/action/reason" in model.calls[1][-1]["content"]          # 修復提示確實帶著具體錯誤

over = json.dumps({"intent": "refund", "customer_reply": "已退款。", "tags": [],
                   "action": {"type": "refund", "order_id": "B-1042", "amount": 12000, "reason": "damaged"}})
r2 = structured_call(ScriptedModel([say(over), say(over), say('{"intent": "refund"')]),
                     [{"role": "user", "content": "東西壞了，全部退給我"}])
show("情境 B 重試用完", r2)
assert r2.status == "failed" and [a["layer"] for a in r2.attempts] == ["語意", "語意", "語法"]
print("後備：轉給真人客服，附上最後一次的錯誤與原始輸出")
```

```text
有 discriminator： ['/action/amount: 型別應為 integer，實際是 string "1,200"', '/action/reason: "退款" 不在允許值 ["damaged", "wrong_item", "not_needed", "other"] 中']
沒有 discriminator： ['/action: 應恰好符合 1 個 oneOf 分支，實際符合 0 個（共 3 個）']
── 情境 A 第一次錯、第二次修好：status=ok
  第 1 次  本地修復=['去掉 code fence', '移除尾逗號']  失敗於 schema
      /action/amount: 型別應為 integer，實際是 string "1,200"
      /action/reason: "退款" 不在允許值 ["damaged", "wrong_item", "not_needed", "other"] 中
  第 2 次  本地修復=無  通過
── 情境 B 重試用完：status=failed
  第 1 次  本地修復=無  失敗於 語意
      /action/amount: 12000 超過訂單總額 1200
  第 2 次  本地修復=無  失敗於 語意
      /action/amount: 12000 超過訂單總額 1200
  第 3 次  本地修復=無  失敗於 語法
      JSON 無法解析：JSON 物件沒有結束，輸出可能被截斷
後備：轉給真人客服，附上最後一次的錯誤與原始輸出
```

逐段解說這份輸出。

**前兩行是 discriminator 的對照實驗**。同一個錯誤的 action（金額是字串、理由是中文），有 discriminator 的 schema 讀到 `type: refund`，只驗證 refund 分支，回報兩個精準的錯誤：`/action/amount` 應該是 integer，`/action/reason` 不在允許值中，連允許值清單都附上了。拿掉 discriminator 之後，驗證器只能把值和三個分支逐一比對，三支都不符合，回報的是「應恰好符合 1 個 oneOf 分支，實際符合 0 個」，這句話對模型幾乎沒有幫助：它不知道自己錯在哪裡，只知道錯了。這就是 7.6 節說的「標籤讓錯誤訊息可以修」。

**情境 A 是週二事故的重現與修復**。第 1 次的輸出前面有一句「好的，以下是處理結果」，JSON 包在 code fence 裡，`tags` 陣列和最外層物件各有一個尾逗號。本地修復記錄了兩個動作：去掉 code fence（連同前面的說明文字），以及移除尾逗號；這些修完之後語法就合法了，不必浪費一輪模型呼叫。但 schema 驗證仍然失敗，兩個錯誤和前面的對照實驗相同，因為金額與理由的修正涉及語意判斷，本地修復刻意不碰。修復提示把這兩個錯誤帶給模型，劇本的第二步是一個函式：只有當提示裡真的出現 `/action/amount` 時，「模型」才給出修正版，這模擬了「錯誤訊息具體，模型才修得好」。第 2 次通過 schema 與語意兩層，status=ok。assert 另外確認了兩件事：模型只被呼叫 2 次，以及第二次呼叫時看到的最後一則訊息確實包含 `/action/reason` 的錯誤說明。

**情境 B 是重試用完的路徑**。這次的 JSON 格式完美，schema 驗證全部通過，但退款金額 12,000 超過訂單總額 1,200，被語意層擋下；這正是週二那張差一點被核准的卡片。劇本裡的模型第二次仍然給出相同的金額（真實模型偶爾也會這樣固執），第三次則給出一段被截斷的 JSON，擷取階段回報「JSON 物件沒有結束，輸出可能被截斷」。三次用完，status=failed，程式走後備路徑：不產生確認卡，轉給真人客服。assert 驗證了三次失敗分別發生在語意、語意、語法層，這種逐次記錄的 attempts 資料，正是 7.7 節說要監控的修復指標的來源。

這段程式刻意沒有做的事，也值得說清楚。它沒有區分「可修」與「不可修」的語意錯誤（訂單不存在時仍會重問一次）；沒有在修復提示中截斷引用的內容；沒有計算重試的 token 成本。這三件事在 `loom` 的正式版本中分別由錯誤類別、提示模板與 usage 統計處理。另外，`validate` 也是第 4 章 dispatch 的升級：把 tool 的 `parameters` 交給同一個驗證器，tool 參數的型別、enum 與巢狀結構錯誤，就能和最終輸出的錯誤用同一種格式回填給模型。

### 第二部分：串流的部分 JSON 解析

`parse_partial` 是一個容忍文件突然結束的遞迴下降解析器（recursive descent parser，每一種 JSON 值對應一個解析函式，互相呼叫）。它回傳三樣東西：目前能還原的值、整份文件是否完整，以及一組「已經確定、不會再變」的欄位路徑。未完成的字串會出現在值裡（給 UI 顯示），但不會出現在確定集合裡（不給程式邏輯使用）；未完成的數字與 `true`／`false`／`null` 則完全不出現，因為它們的前綴沒有意義。

```python
from __future__ import annotations

import json
from typing import Any

MISSING = object()                       # 「這個值還沒開始出現」，和 null 不同


def parse_partial(s: str) -> tuple[Any, bool, set[str]]:
    """容忍「文件還沒結束」的 JSON 解析器。
    回傳 (目前能還原的值, 整份是否完整, 已經確定不會再變的欄位路徑)。"""
    final: set[str] = set()
    i = 0

    def skip_ws() -> None:
        nonlocal i
        while i < len(s) and s[i] in " \t\r\n":
            i += 1

    def string() -> tuple[str, bool]:
        nonlocal i
        i += 1                                           # 開頭的引號
        out = []
        while i < len(s):
            ch = s[i]
            if ch == '"':
                i += 1
                return "".join(out), True
            if ch == "\\":
                seq_len = 6 if s[i + 1:i + 2] == "u" else 2
                if i + seq_len > len(s):                 # 跳脫序列被切在半路：先不顯示
                    i = len(s)
                    break
                out.append(json.loads('"' + s[i:i + seq_len] + '"'))
                i += seq_len
                continue
            out.append(ch)
            i += 1
        return "".join(out), False                       # 字串還沒結束：可以顯示，但不是最終值

    def scalar() -> tuple[Any, bool]:
        nonlocal i
        start = i
        while i < len(s) and s[i] not in ",}] \t\r\n":
            i += 1
        if i == len(s):                                  # 12 可能是 120、tr 可能是 true：不猜
            return MISSING, False
        return json.loads(s[start:i]), True

    def value(path: str) -> tuple[Any, bool]:
        skip_ws()
        if i >= len(s):
            return MISSING, False
        if s[i] in "{[":
            return container(path, s[i])
        return string() if s[i] == '"' else scalar()

    def container(path: str, opener: str) -> tuple[Any, bool]:
        nonlocal i
        i += 1
        out: Any = {} if opener == "{" else []
        closer = "}" if opener == "{" else "]"
        while True:
            skip_ws()
            if i >= len(s):
                return out, False
            if s[i] == closer:
                i += 1
                return out, True
            if s[i] == ",":
                i += 1
                continue
            if opener == "{":
                key, done = string()
                skip_ws()
                if not done or i >= len(s) or s[i] != ":":
                    return out, False                    # key 還沒寫完：整個欄位先不出現
                i += 1
                child = f"{path}/{key}"
            else:
                child = f"{path}/{len(out)}"
            v, done = value(child)
            if v is not MISSING:
                if opener == "{":
                    out[key] = v
                else:
                    out.append(v)
            if not done:
                return out, False
            final.add(child)

    v, done = value("")
    return (None if v is MISSING else v), done, final


# 模型串流輸出一份處理結果；customer_reply 放在 action 前面，UI 才能先顯示
doc = json.dumps({"intent": "refund", "customer_reply": "已為您申請退款 1,200 元，3–5 個工作天入帳。",
                  "action": {"type": "refund", "order_id": "B-1042", "amount": 1200, "reason": "not_needed"}},
                 ensure_ascii=False)
chunks = [doc[k:k + 23] for k in range(0, len(doc), 23)]
executed = None
for n, chunk in enumerate(chunks, 1):
    prefix = "".join(chunks[:n])
    obj, done, final = parse_partial(prefix)
    reply = obj.get("customer_reply", "") if obj else ""
    action = obj.get("action") if obj else None
    ready = "/action" in final
    settled = [p[1:] for p in sorted(final) if p.count("/") == 1]
    print(f"#{n} 已確定={settled} reply 已顯示 {len(reply):>2} 字 "
          f"action={json.dumps(action, ensure_ascii=False)[:40]}{'  → 可執行' if ready else ''}")
    if ready and executed is None:
        executed = action                       # 只在 action 整個結束後才交給下游（真實系統還要先驗證）

assert done and obj == json.loads(doc) and executed == obj["action"]
mid = parse_partial(doc[:doc.index("B-1042") + 4])     # 切在訂單編號中間
print("切在半路：", mid[0]["action"], "/action/order_id" in mid[2])
assert mid[0]["action"]["order_id"] == "B-10" and "/action/order_id" not in mid[2]
```

```text
#1 已確定=['intent'] reply 已顯示  0 字 action=null
#2 已確定=['intent'] reply 已顯示  6 字 action=null
#3 已確定=['customer_reply', 'intent'] reply 已顯示 27 字 action=null
#4 已確定=['customer_reply', 'intent'] reply 已顯示 27 字 action={"type": "re"}
#5 已確定=['customer_reply', 'intent'] reply 已顯示 27 字 action={"type": "refund", "order_id": "B-1"}
#6 已確定=['customer_reply', 'intent'] reply 已顯示 27 字 action={"type": "refund", "order_id": "B-1042",
#7 已確定=['action', 'customer_reply', 'intent'] reply 已顯示 27 字 action={"type": "refund", "order_id": "B-1042",  → 可執行
切在半路： {'type': 'refund', 'order_id': 'B-10'} False
```

這份輸出是 7.8 節時序圖的實際數據，每一行是收到一個 23 字元的片段之後的狀態。第 1 行，`intent` 的值已經收到結尾引號，進入「已確定」集合，UI 可以先顯示分類；`customer_reply` 的 key 還沒寫完，所以完全沒出現。第 2 行，回覆文字收到了 6 個字，可以逐字顯示，但它不在已確定集合裡。第 3 行，回覆文字完整了（27 字），變成已確定。

第 4 到第 6 行是 Maya 擔心的時刻：`action` 物件已經開始，第 4 行的 type 只有 `"re"`，第 5 行的 `order_id` 只有 `"B-1"`，這些都是格式合法的字串，但都不是最終值；任何在這時候「看到 order_id 就去查」的程式，都會拿錯誤的編號去打後端。第 7 行，action 物件收到右大括號，`/action` 進入已確定集合，程式這時才把它交給下游，真實系統還要再經過第一部分的驗證。最後一行是刻意切在訂單編號中間的測試：解析結果裡 `order_id` 是 `B-10`，而確定集合裡沒有 `/action/order_id`，assert 鎖住了「半截的值看得到、但不算數」這條規則。

把兩部分合起來，就是給 `loom` 加上的 `loom.schema` 模組（structured output）：串流時用 `parse_partial` 驅動 UI，文件完整後用 `structured_call` 的驗證與修復流程決定是否產生確認卡。

| 機制 | 擋下的事故 | 對應小節 | 在 loom 中的位置 |
|---|---|---|---|
| 配對掃描擷取、本地修復 | code fence、前言、尾逗號、貪婪 regex | 7.7 | `extract_json` |
| Schema 驗證（含 discriminator） | 型別、enum、缺欄位、自創欄位 | 7.3、7.6 | `validate`，也用於 tool 參數 |
| 語意驗證 | 金額超過總額、捏造的訂單 | 7.2、7.7 | 由應用程式註冊的規則 |
| 有上限的修復迴圈 | 偶發錯誤；以及「無限重試」 | 7.7 | `structured_call` |
| 部分 JSON 解析 | 半截欄位被拿去執行；UI 空白太久 | 7.8 | `parse_partial` |

## 7.11 實務應用

structured output 的機制在每一種 agent 產品裡都會出現，但重點各不相同。以下四個情境說明本章的技術在不同場景中要怎麼調整。

**情境一：電商客服的處理確認卡（青鳥的主線）**。這是本章的主線，它的關鍵特徵是「提案要給人核准」。因為有人在迴圈裡，語意驗證失敗不一定要重問模型，也可以在卡片上直接標紅「金額超過訂單總額」，讓客服修改後核准；這比讓模型重試更便宜，也讓客服知道 agent 哪裡不可靠。enum 的值要和下游系統的代碼一致（退款理由直接對應會計系統的理由代碼），顯示文字由 UI 翻譯。串流時先顯示回覆文字與分類，確認卡等整份通過驗證才出現。每週檢查修復迴圈的觸發原因，若「理由不在 enum 中」頻繁出現，代表 enum 漏了真實情況，要和客服主管一起補上，而不是讓模型被迫挑一個不正確的理由。

**情境二：保險理賠或發票的文件抽取**。金融與保險業常見的需求是從掃描文件中抽取欄位：發票號碼、日期、金額、品項明細。這類任務的 schema 通常很大、巢狀很深（明細是一個物件陣列），而且語意驗證特別重要：品項金額加總要等於總額，日期不能在未來，統一編號要通過檢查碼。這裡的修復策略和客服不同：抽取錯誤往往來自文件本身模糊，重問模型不一定有幫助，所以常見的做法是把每個欄位的信心或來源位置（文件第幾頁、哪一行）一起輸出，驗證失敗或信心低的欄位送人工複核，而不是無限重試。可為 null 的設計在這裡尤其重要：文件上沒有的欄位，必須允許模型明確地說「沒有」，否則它會從鄰近的欄位挪一個值過來。

**情境三：coding agent 的檔案編輯**。coding agent 每天產生大量「結構化的修改」，但業界普遍不用 JSON 表達檔案內容，而是用專門的編輯格式。公開資料中，Claude Code 的檔案編輯工具採用「指定原文與取代內容」的形式，原文在檔案中找不到或出現多次時，tool 會回傳錯誤讓模型修正，這本身就是一個修復迴圈；OpenAI 的 Codex 工具鏈則以 `apply_patch` 格式描述修改；開源的 Aider 公開了多種 edit format 的比較，並記錄不同模型適合的格式。共同的設計原則是：格式要讓「錯誤可以被機械地偵測」，例如原文不匹配、patch 套用失敗，然後把錯誤回填給模型。這是 7.9 節「受限格式」那一列在真實產品中的樣子。

**情境四：多 agent 的路由與交接**。在 orchestrator–subagent 架構中（第 20 章），orchestrator 交給 subagent 的任務描述、subagent 回報的結果，都是 structured output。這裡的重點是 schema 的演進與相容：不同 agent 可能由不同團隊維護、使用不同模型，交接物件的 schema 要有版本號，新增欄位要可為 null，移除欄位要經過棄用期，就像設計服務之間的 API。路由決策本身適合用 discriminated union 表達（「交給 billing 隊列，附上摘要」或「交給 logistics，附上物流單號」），讓每個目的地只拿到它需要的欄位。評估 agent（LLM-as-judge）的分數輸出也一樣：用 enum 或整數範圍限制分數，並要求先輸出理由再輸出分數，第 27 章會談這個設計對評分一致性的影響。

| 情境 | schema 的重點 | 語意驗證的重點 | 失敗時的後備 |
|---|---|---|---|
| 客服確認卡 | discriminated union、enum 對應下游代碼 | 金額、訂單存在、intent 與 action 一致 | 卡片標紅給客服修改，或轉真人 |
| 文件抽取 | 大型巢狀 schema、可為 null、來源位置 | 加總、日期、檢查碼 | 低信心欄位送人工複核 |
| coding agent 編輯 | 專用編輯格式而非 JSON | 原文匹配、patch 可套用、測試通過 | 錯誤回填給模型重試 |
| 多 agent 交接 | 版本化 schema、union 路由 | 必要欄位齊全、目的地存在 | 退回 orchestrator 重新規劃 |

這張表的共同點是：schema 決定「能不能機械地檢查」，語意驗證決定「檢查到多深」，後備決定「檢查失敗時誰來接手」。三者缺一，structured output 就只是一段看起來很整齊的文字。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各專案公開文件：OpenAI 的 Python SDK 提供以 Pydantic 模型為輸出格式、直接取得解析後物件的介面，JS SDK 則搭配 Zod；OpenAI Agents SDK 可以為 agent 指定輸出型別；Pydantic AI 支援輸出型別與輸出驗證函式，驗證函式可以要求模型重試；開源函式庫 Instructor 以「Pydantic 模型＋驗證失敗自動帶錯誤重問」聞名，並支援串流部分物件；BAML 主張不依賴 constrained decoding，而是用寬鬆的「schema 對齊解析」從模型輸出中還原結構；Vercel AI SDK 提供串流部分物件的介面；LangChain 的 chat model 介面提供 structured output 的包裝。MCP 規格允許 tool 宣告 `outputSchema` 並回傳 `structuredContent`，讓 tool 的結果也成為可驗證的結構化資料（第 14 章）。各工具的確切 API 與預設重試行為會隨版本調整，請以各自文件為準。

## 7.12 設計檢查清單

設計或審查一個 structured output 時，逐項回答下面的問題。

1. 這個輸出的消費者是誰？是程式（需要 schema 與驗證）、人（可以是自由文字），還是兩者都有（JSON 包文字）？
2. 輸出的下一步是「立刻執行」還是「呈現、儲存、審核」？前者用 tool，後者用 structured output，選對了嗎？
3. 是否有單一事實來源（dataclass、Pydantic、Zod 等）同時產生 schema 與解析輸出，而不是 prompt 與程式各寫一份？
4. 目標模型與部署環境是否支援 strict mode？若支援，是否已開啟？若不支援，修復迴圈是否已準備好承接較高的失敗率？
5. 每個 enum 是否涵蓋真實世界的所有情況，並保留 `other` 加說明欄位？enum 值是穩定的代碼而不是顯示文字嗎？
6. 選填欄位是否用可為 null 表達，並在 description 中寫清楚「什麼情況填 null」？
7. 多種形狀擇一時，是否用帶標籤的 discriminated union，而不是攤平成一個全部選填的大物件？
8. 欄位順序是否刻意安排：理由在結論之前、要串流顯示的欄位在要執行的欄位之前？
9. 語意驗證是否涵蓋 schema 管不到的規則（ID 存在、金額範圍、欄位之間的一致性），並能比對來源資料？
10. 本地修復是否只做不改變語意的修正？會不會偷偷把 `"1,200"` 轉成 1200 這類需要猜測的轉換？
11. 修復迴圈的次數上限是多少？哪些錯誤類別直接走後備而不重試？後備路徑是什麼？
12. 解析前是否先檢查 stop_reason（max_tokens、拒答），避免把半截輸出或拒答訊息當成資料？
13. 串流時，是否只有「已確定」的欄位會觸發程式邏輯？有副作用的動作是否等整份文件完成並通過驗證？
14. 修復次數、失敗層級與後備觸發率是否被記錄為指標，並在模型或 prompt 改版時比較？

## 7.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 偶發 `JSONDecodeError`，log 裡有「好的，以下是結果」 | 只靠 prompt 要求 JSON，模型用聊天格式回答 | 抽樣失敗的原始輸出 | 開 strict 或 JSON mode；加上配對掃描擷取與本地修復 |
| 擷取到的 JSON 多了一段後記，或被切斷 | 貪婪 regex 擷取 `\{.*\}` | 用含大括號的使用者內容做測試 | 改用追蹤字串與跳脫字元的配對掃描 |
| 格式正確但內容不可能（金額過大、編號不存在） | 只有 schema 驗證，沒有語意驗證 | 比對輸出與來源資料（訂單、物流紀錄） | 加上業務規則驗證；可修的錯誤帶規則重問，不可修的走後備 |
| 某個 enum 值的比例異常高 | enum 漏掉真實情況，strict 下模型被迫挑最接近的值 | 抽樣該值的案例，對照原始資料 | 補上缺漏的值，或保留 `other` 加說明欄位 |
| 驗證錯誤訊息只有「不符合任何分支」，修復迴圈常常失敗 | union 沒有標籤，驗證器只能逐支比對 | 看修復提示的內容 | 每個分支加 `type: const` 標籤，驗證器依標籤選分支 |
| 修復迴圈次數上升，帳單與延遲跟著上升 | prompt、schema 或模型改版造成失敗率上升，被重試掩蓋 | 按版本統計每次呼叫的修復次數與失敗層級 | 監控修復率；回頭修 schema 或 description 的根因 |
| 被截斷的輸出重試後仍然被截斷 | 用同樣的輸出上限重問 | 看 stop_reason 是否為 max_tokens | 提高輸出上限或要求縮短長文字欄位；不要原樣重試 |
| 串流時用半截的值觸發了查詢或寫入 | 程式邏輯使用了尚未確定的欄位 | 在 trace 中找串流期間的下游呼叫 | 只讓「已確定」的欄位觸發邏輯；有副作用的動作等整份驗證通過 |
| 選填欄位被填入看似合理但捏造的值 | 欄位不能為 null，或 description 沒說明何時留空 | 抽樣該欄位在對話中無依據的案例 | 型別加上 null，description 寫明「沒有就填 null」 |

## 本章重點整理

- structured output 出現在 tool 參數、最終答案、路由、agent 交接與評估等位置，共同點是消費者是程式，而程式不會「大概看懂」。
- 從模型輸出到下游資料要經過擷取、解析、schema 驗證、語意驗證、轉成型別物件五道關卡，每一層擋下不同成因的錯誤。
- strict mode 透過 constrained decoding 在生成時遮掉違反 schema 的 token，保證的是形狀而不是內容；它能減少修復次數，但取代不了語意驗證。
- schema 和真實世界不一致時，受限解碼會逼模型挑一個格式完美的錯誤答案，所以 enum 要涵蓋真實情況或保留 `other`。
- schema 的每個欄位都是給模型的指令：用 integer 表達金額、用穩定代碼表達 enum、用可為 null 表達選填，並在 description 寫單位、格式與何時留空。
- 欄位順序會影響生成：理由放在結論之前，要串流顯示的欄位放在要執行的欄位之前。
- 用單一資料模型同時產生 schema 與解析輸出，並在邊界上一次完成檢查（parse, don't validate），讓下游只拿到有型別、已通過檢查的物件。
- 多種形狀擇一時用 discriminated union：標籤讓驗證器只檢查對應分支、產生精準的錯誤訊息，也讓下游的分派變得簡單。
- 輸出的下一步是立刻執行時用 tool，是呈現、儲存或審核時用 structured output。
- 本地修復只做不改變語意的修正，例如去 code fence、去尾逗號；任何需要猜測語意的轉換都要退回給模型。
- 修復提示要附上錯誤路徑、實際值與允許值；沒有新資訊的重問只是在碰運氣。
- 修復迴圈要有小的次數上限、區分可修與不可修的錯誤，並把修復次數當成指標監控，避免重試掩蓋根因與放大成本。
- 串流解析時，顯示可以樂觀、動作必須保守：未完成的欄位可以給人看，只有已確定的欄位能觸發程式邏輯，有副作用的動作要等整份驗證通過。
- 當你發現自己在 JSON 裡發明迴圈與變數時，改讓模型輸出程式碼，並把驗證從檢查形狀改成在 sandbox 中執行並檢查結果。

## 延伸問答

> [!question]- Q1. 既然主流 API 都有 strict mode 保證輸出符合 schema，為什麼還需要自己寫驗證器？
> 因為 strict 保證的範圍比你需要的窄。第一，它只保證形狀：12,000 是合法的整數，不存在的訂單編號是合法的字串，這些語意錯誤只有你的程式知道怎麼檢查。第二，它只保證「完成的輸出」：拒答、被 max_tokens 截斷、串流中斷時，你拿到的不是符合 schema 的物件。第三，各家支援的是 JSON Schema 的子集，你真正需要的規則（數值範圍、欄位之間的一致性）常常不在子集裡。
>
> 還有一個架構上的理由：strict 是供應商的能力，不是你系統的不變式。換模型、換供應商、經過 gateway 或 proxy、或者某天有人關掉了 strict，保證就消失了，而你的下游程式不會知道。把驗證放在自己的邊界上，系統的正確性就不依賴於任何一個外部設定。實務上兩者並用：strict 讓形狀錯誤幾乎不發生、降低修復成本，自己的驗證器負責語意與最後一道把關。

> [!question]- Q2. 為什麼 strict 模式通常要求所有欄位都列在 required 裡？選填欄位要怎麼表達？
> 供應商沒有公開完整的設計理由，但從受限解碼的角度可以合理推想：「這個欄位可以出現也可以不出現」會讓語法變得更複雜：每個位置都要同時允許「寫這個欄位」和「跳過它寫下一個」，欄位一多，狀態的組合會快速膨脹，也讓模型更容易漏寫。要求全部列入 required，讓每個物件的欄位序列是固定的，語法簡單、解碼可預測。選填的語意改用「型別可以是 null」表達，例如 `["string", "null"]`。
>
> 這個做法在語意上其實更好。「欄位不存在」在程式裡可能代表很多事：模型漏了、舊版 schema、傳輸時被截掉；「欄位存在而值是 null」則是模型明確地說「沒有這個資訊」。後者可以被稽核，也可以在 description 裡規定「對話中沒有提到訂單編號時填 null」，避免模型為了填滿欄位而捏造。代價是 schema 和輸出都長一點，以及你的程式要處理 null，但這些都是應該處理的情況。

> [!question]- Q3. 本地修復可以把 `"1,200"` 轉成 1200、把「退款」對應到 `refund` 嗎？界線在哪裡？
> 界線是「修復前後的語意是否確定相同」。去掉 code fence、去掉前後的說明文字、移除尾逗號，這些修正不改變任何資料，修完的物件就是模型想表達的物件，可以安全地在本地做。`"1,200"` 轉成 1200 看起來也很安全，但它其實是在猜：在某些地區的寫法中逗號是小數點，在其他欄位裡逗號可能是兩個值的分隔；「退款」對應到 `refund` 更明顯是在替模型做分類決定，而 `not_needed` 和 `damaged` 都可能是「退款」。
>
> 一旦本地修復開始猜語意，就出現兩個問題：錯誤的猜測會靜默地進入下游，而且沒有人知道這筆資料被改過；修復規則會越長越多，變成一個沒有測試的第二套解析器。比較好的做法是讓 schema 本身消除歧義（金額用 integer、理由用英文代碼並附說明），形狀不對就退回給模型修，並記錄每一次修復。如果某個轉換真的有必要（例如舊系統的資料格式），把它寫成明確、有測試、有紀錄的正規化步驟，而不是藏在解析器裡。

> [!question]- Q4. 估算題：處理確認卡每天產生 20,000 張，每次呼叫平均 4,000 input tokens、300 output tokens。未開 strict 時 6% 需要一次修復、1% 需要兩次；開 strict 後只剩語意錯誤 1.5% 需要一次修復。修復迴圈每天多花多少 tokens？
> 每次修復都是一次完整的呼叫，而且 context 更長：要加上上一次的輸出（約 300 tokens）與修復提示（假設約 150 tokens），所以第一次修復的 input 約 4,450 tokens，第二次修復再加約 450，約 4,900 tokens，output 都約 300。未開 strict 時，修復一次的有 6% 加 1% 共 7%，也就是 1,400 張要多做第一次修復；其中 1% 共 200 張還要做第二次。額外 input 約 1,400 × 4,450 ＋ 200 × 4,900 ＝ 6,230,000 ＋ 980,000 ≈ 721 萬 tokens，額外 output 約 1,600 × 300 ＝ 48 萬 tokens。對照基準的 8,000 萬 input tokens，約多 9%。
>
> 開 strict 後只有 300 張需要一次修復，額外 input 約 300 × 4,450 ≈ 134 萬 tokens，只多約 1.7%。延遲的影響更值得注意：需要修復的那幾張卡片，延遲大約變成兩倍或三倍，會直接出現在 p95 或 p99 上；未開 strict 時 7% 的請求要修復，代表 p95 很可能就是一次修復的延遲。這個估算也說明了為什麼修復率要當成指標：當某次 prompt 改版讓失敗率從 2% 變成 20%，成本與尾端延遲會跟著明顯上升，但功能測試完全看不出來。實際數字要以你的 token 量與價目表重算，若前綴能命中 prompt cache，修復呼叫的 input 成本還會更低。

> [!question]- Q5. 程式找錯：下面這段解析程式在 production 會出哪些問題？
> ```python
> def parse_resolution(text):
>     try:
>         data = json.loads(re.search(r"\{.*\}", text, re.S).group())
>     except Exception:
>         return {}
>     if data.get("action", {}).get("type") == "refund":
>         refund_api(data["action"]["order_id"], int(data["action"]["amount"]))
>     return data
> ```
> 第一個問題是貪婪 regex：文字裡只要在 JSON 之後還有右大括號，擷取就會黏到多餘的內容而解析失敗；找不到大括號時 `re.search` 回傳 None，`.group()` 丟出的例外又被一起吞掉。第二個問題是 `except Exception: return {}`：所有失敗都變成一個空 dict，呼叫端分不清「解析失敗」和「沒有動作」，也沒有任何紀錄與修復機會，錯誤被靜默地吞掉。它也沒有先檢查 stop_reason，被截斷的輸出會和其他錯誤混在一起。
>
> 第三個問題最嚴重：在解析函式裡直接呼叫有副作用的 `refund_api`，而且中間沒有任何 schema 或語意驗證。`int(data["action"]["amount"])` 遇到 `"1,200"` 會丟例外，遇到 12000 會照退，`order_id` 是否存在、金額是否超過總額都沒檢查；這也繞過了 L3 設計中「寫入要人核准」的要求。修法是把職責拆開：解析函式只負責擷取、解析、驗證並回傳有型別的結果或明確的失敗狀態；執行由確認卡核准後的另一段程式負責，而且只接受通過驗證的物件。

> [!question]- Q6. 你在 production 看到換了新版模型之後，退款理由 `other` 的比例從 3% 升到 15%，但修復率沒有變化。你會怎麼排查？
> 修復率沒變，代表輸出的形狀都合法，問題出在語意分布上。第一步是抽樣 `other` 的案例，讀說明欄位與原始對話：如果大量案例其實是 `damaged` 或 `not_needed`，代表新模型對分類邊界的理解不同；如果大量案例確實不屬於現有類別（例如新出現的「與商品描述不符」），代表 enum 本來就漏了真實情況，只是舊模型習慣把它們硬塞進某個現有值。這兩種原因的處理方式完全不同。
>
> 第二步是比較 description 與範例：新模型可能更字面地遵守「無法確定時用 other」這類指示，舊 prompt 中依賴舊模型習慣的部分要重新校準（第 6 章談過隨模型升級調整 prompt）。第三步是用固定的評估集比較新舊模型的分類結果，而不是只看線上比例，因為線上的案例組成也可能同時在變。修正後，把幾個代表性案例加進 eval，避免下次換模型時再發生。這個問題也說明了為什麼除了修復率，還要監控 enum 值的分布：strict 讓格式錯誤消失之後，語意漂移只會以「分布改變」的形式出現。

> [!question]- Q7. 面試追問：你要為自家 framework 設計 structured output 模組，必須支援三家模型 API，其中一家的 strict 子集不支援 oneOf。你會怎麼設計？
> 核心是把「你的 schema」和「送給供應商的 schema」分開。應用程式用自家的資料模型（dataclass 或等價物）定義輸出，framework 從它產生一份完整的內部 schema，再由每個供應商的 adapter 轉換成該家支援的子集：例如把 oneOf 改寫成 anyOf 加每支一個 const 標籤，把所有欄位補進 required 並把選填改成可為 null，把不支援的關鍵字（數值範圍、字串格式）從送出的 schema 中移除，但保留在內部 schema 裡。adapter 還要宣告能力旗標：是否支援 strict、是否支援串流部分物件、拒答與截斷的訊號長什麼樣子。
>
> 驗證永遠用完整的內部 schema，在 framework 自己的邊界上執行，所以被 adapter 移除的規則仍然會被檢查，只是從「生成時保證」降級成「驗證後修復」。修復迴圈、後備政策、修復率指標也都放在 framework 層，與供應商無關。最後要有相容性測試：對每個 adapter，用同一組 ScriptedModel 劇本與真實模型的小型 eval 驗證轉換後的 schema 行為一致。這樣換供應商時，應用程式的程式碼與保證都不變，只有修復率可能不同，而修復率是可以被監控的。

> [!question]- Q8. 青鳥的營運 research agent 要回答「上個月各類退貨率與前月比較」，Iris 想讓它輸出一個描述查詢步驟的 JSON 計畫，老陳建議改成輸出程式碼。兩種做法怎麼取捨？
> JSON 計畫的優點是可驗證性高：每個步驟是有限的幾種操作（查詢、篩選、分組、比較），schema 能完整描述，執行前可以逐步檢查權限與參數。但這個任務需要變數（上個月與前月的結果）、迴圈（每一類退貨）與計算（比率與差異），JSON 計畫很快就會長出「參照前一步結果」「對每個元素重複」這類欄位，等於在 JSON 裡發明一個沒有工具鏈、沒有除錯器的程式語言，模型也沒看過這種格式。
>
> 輸出程式碼的表達能力強得多，模型也熟悉，但代價是驗證方式要改變：你無法只靠看就確定一段程式會做什麼，所以必須在 sandbox 裡執行（第 17 章），限制它能存取的資料與網路，只開放唯讀的查詢介面，並用結果檢查（例如比率在 0 到 1 之間、各類加總等於總數）取代形狀檢查。折衷做法是：程式碼負責計算，最終結論仍用 structured output 回傳（例如每類的比率與變化），讓下游的報表系統拿到可驗證的結構。判斷的關鍵是任務是否有副作用：這是一個唯讀的分析任務，在 sandbox 中執行程式碼的風險可控，所以老陳的建議合理；如果任務涉及寫入，就應該回到 tool 加核准的設計。

## 延伸閱讀

- JSON Schema 規格（Draft 2020-12）與〈Understanding JSON Schema〉教學文件
- OpenAI 開發者文件〈Structured Outputs〉與〈Function calling〉
- Anthropic 文件〈Tool use〉與 structured outputs 相關章節
- Alexis King〈Parse, don't validate〉（2019，部落格文章）
- Willard and Louf〈Efficient Guided Generation for Large Language Models〉（2023，arXiv，Outlines 的原理）
- Tam et al.〈Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models〉（2024，arXiv）
- Wang et al.〈Executable Code Actions Elicit Better LLM Agents〉（ICML 2024，CodeAct）
- HumanLayer，Dex Horthy〈12-Factor Agents〉（2025，GitHub）
