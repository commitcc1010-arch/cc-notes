---
chapter: 9
title: Context Engineering：有限注意力的預算
part: 2
---

# 第 9 章　Context Engineering：有限注意力的預算

> [!abstract] 本章地圖
> **核心問題**：context window 放得下，不代表模型用得好、帳單付得起；每一次呼叫模型之前，該放進哪些 token、用什麼順序放、放多少？
>
> **你會學到**：
> - 說明 context 為什麼是稀缺資源：金錢、延遲與注意力三種成本，以及 context rot 的成因與四種典型失敗
> - 依變動頻率把 context 分成穩定前綴、半穩定層、動態層，並決定 cache breakpoint 放在哪裡
> - 找出會讓 prompt cache 失效的變更，改用「追加而不改寫」的做法，例如不在中途改 tool 定義
> - 為每一層訂 token 預算、用供應商回報的 usage 校正 token 估算，並在超出預算時依優先序削減
> - 用 just-in-time 載入與檔案系統當外部 context，讓 context 只帶引用、不帶整包內容
> - 實作一個 context builder：依預算組裝、量測每層 token、模擬 cache 命中率，並重現中途改 tool 定義造成的 cache 失效
>
> **前置知識**：第 3 章（token、context window、prompt caching 的原理與計價）、第 4 章（messages 格式、穩定前綴與尾端追加、`loom` v0.1）、第 6 章（system prompt 的結構）

## 9.1 故事：加了知識庫之後，agent 變貴也變笨

客服 agent v1 以 L3 上線兩個月後，阿哲帶來下一階段的需求：「店家一直抱怨 agent 不懂他們的退貨規則，也看不到顧客以前買過什麼。把退換貨手冊和訂單紀錄接進去吧。」Iris 覺得這次很簡單，因為模型的 context window 已經大到能放下一整本手冊。於是 Iris 做了四件事：把 30 頁的退換貨手冊整份放進 system prompt；把顧客最近 90 天的訂單全部查出來塞在手冊後面；在 system prompt 最上方加上「現在時間」與「今日促銷活動」，讓 agent 能回答時效問題；另外，只要使用者提到「優惠券」，harness 就動態掛上 `apply_coupon` 與 `list_coupons` 兩個 tool，免得平常的對話帶著用不到的定義。

內部試用一週，結果三面失守。成本面：每次呼叫的 input 從約 4,000 tokens 漲到約 38,000 tokens，帳單上的 cache 命中率只有個位數，因為每一次請求的開頭都不一樣。品質面：手冊裡同時留著 2024 年的舊版規定（退貨期限 14 天）與今年的新版（7 天），agent 有三成的時候引用了舊版；有一次它把顧客的 B-1042 和 B-1024 搞混，因為兩張單號在 90 天的訂單列表裡只隔了幾行。安全面：資安工程師 Maya 在 trace 裡看到每一次呼叫都帶著顧客的地址與電話，即使問題只是「優惠券怎麼用」，那些個資也被送到模型、寫進 log。

老陳看完 trace，在白板上寫了一句話：「context 是預算，不是倉庫。」老陳的意思是，context window 的大小是上限，不是目標；每一個放進去的 token 都要付三種成本：錢、延遲、模型的注意力，所以每個 token 都要有理由出現在那裡。Iris 的四個改動各自都有道理，但合在一起，讓 context 變成一個又大、又亂、每次都在變的倉庫。

這一章把 Iris 的修正過程拆成幾個問題。第一，為什麼放得下不等於用得好（9.2 節）。第二，context 要怎麼排版，才能讓 prompt cache 一直命中（9.3、9.4 節）。第三，預算怎麼訂、token 怎麼算（9.5 節）。第四，不放進 context 的資訊，要怎麼讓 agent 需要時拿得到（9.6、9.7 節）。第五，怎麼量測與視覺化，讓問題在帳單出來之前就被看見（9.8 節）。最後在動手做裡，Iris 會寫一個 context builder，把 v1 的失敗在離線環境裡重現並修好。長對話的 compaction 與 session log 是第 10 章的主題，檢索品質是第 11 章，跨 session 的 memory 是第 12 章，大量 tool 的延遲載入是第 13 章；本章是它們共同的地基。

## 9.2 Context 是預算，不是倉庫

### 什麼是 context engineering

**context engineering**（情境工程）是決定「每一次呼叫模型時，context window 裡要放哪些 token、用什麼順序與形式放」的工作。例如青鳥客服回答「外套可以退嗎」時，要放的是退貨政策的那一節與那張訂單，而不是整本手冊與 90 天的訂單。它和 **prompt engineering**（提示工程）不同：prompt engineering 關心的是指令怎麼措辭，context engineering 關心的是整個輸入的組成，包括 system prompt、tool 定義、對話歷史、tool 結果、檢索到的文件、memory 與執行時注入的提醒。agent 跑在 loop 裡，每一步都會產生新的 tool 結果，所以 context 不是寫一次就好的 prompt，而是每一輪都要重新組裝的資料結構。

Anthropic 在 2025 年的文章把目標描述為：找出能讓模型做對事情的、最小的一組高訊號 token。這句話的重點是「最小」與「高訊號」同時成立。少放會讓模型缺資訊而猜測；多放則會稀釋注意力、拖慢回應、增加成本。context engineering 不是一味壓縮，而是讓每個 token 的邊際價值都值得它的成本。

### 三種成本

每一個放進 context 的 token，都同時付三種成本。第一是**錢**：第 3 章算過，agent 每一步都重送完整歷史，累計 input 約和步數平方成正比，cache 命中與否又讓單價差上一個數量級。第二是**延遲**：沒有命中 cache 的輸入要在 prefill 階段重新計算，輸入越長，TTFT 越長，同步的客服對話對這一點特別敏感。第三是**注意力**：模型用注意力機制讓每個 token 和其他 token 互相參照，token 越多，兩兩之間的關係越多，任何一條關鍵資訊分到的「注意力」就越被稀釋。前兩種成本會出現在帳單與監控上，第三種只會出現在品質下降裡，所以最容易被忽略。

### Context rot：越長越不可靠

**context rot**（情境腐化）是指輸入越長，模型找到並正確使用其中關鍵資訊的能力越差的現象。例如同一個「退貨期限是幾天」的問題，只附上政策那一節時幾乎總是答對，附上整本手冊加上 90 天訂單後，答錯的機率明顯上升。幾個公開研究都觀察到這個趨勢：Liu 等人在 2023 年的〈Lost in the Middle〉發現，關鍵資訊放在長輸入的開頭或結尾時表現較好，放在中間時明顯變差；2025 年 Chroma 的報告測試了多個模型，發現即使任務很簡單，表現也會隨輸入變長而下降，而且干擾資訊的傷害會隨長度放大。這種衰退是漸進的斜坡，不是到某個長度才突然崩潰的懸崖，所以你不會在測試時看到一個明確的「爆掉」點。

```text
 Iris v1 的一次呼叫：context 裡有什麼、這一題真正用到什麼

 ┌──────────────────────────────────────────────┬───────────┬──────────┐
 │ 區塊                                         │  tokens   │ 這題用到 │
 ├──────────────────────────────────────────────┼───────────┼──────────┤
 │ 現在時間 14:03:27＋今日促銷（放在最上面）    │     600   │    否    │ ← 每次都變：cache 從這裡斷
 │ tool 定義（含動態掛上的 coupon tools）       │   3,400   │   部分   │ ← 中途增減：cache 再斷一次
 │ 角色與規則                                   │   1,200   │    是    │
 │ 退換貨手冊全文（新舊兩版並存）               │  21,000   │  約 600  │ ← 舊版 14 天 vs 新版 7 天：衝突
 │ 90 天訂單（含地址、電話）                    │  10,500   │  1 筆    │ ← B-1042 與 B-1024 相鄰：混淆
 │ 對話歷史與 tool 結果                         │   1,300   │    是    │
 ├──────────────────────────────────────────────┼───────────┼──────────┤
 │ 合計                                         │  38,000   │ 約 3,500 │   訊號比例不到 10%
 └──────────────────────────────────────────────┴───────────┴──────────┘
```

這張解剖圖是老陳和 Iris 一起從 trace 拆出來的。由上往下看：第一列放在最前面、每次都變，讓之後所有內容都無法命中 cache；第二列的 tool 定義會在對話中途增減，是第二個 cache 斷點；第四列的手冊佔了一半以上的 token，這一題卻只用到其中一節，而且新舊兩版同時存在；第五列的訂單列表只需要一筆，卻帶進了 150 筆以及每筆的個資。最後一列是結論：38,000 個 token 中，這一題真正用到的不到一成，剩下的九成都在付錢、拖延遲、稀釋注意力，甚至直接誤導模型。

### 四種典型的 context 失敗

context 出問題時，症狀常常只是「模型答錯了」，看起來像模型不夠聰明。業界常把長 context 的失敗歸納成幾種類型，本書整理成下面四種，拆開來看比較容易對症下藥。

| 失敗類型 | 白話說明 | 青鳥的例子 | 主要對策 |
|---|---|---|---|
| 干擾（distraction） | 無關內容太多，模型抓不到重點 | 90 天訂單淹沒了要問的那一筆 | 只放需要的、用 just-in-time 載入（9.6 節） |
| 混淆（confusion） | 相似的內容並存，模型拿錯 | B-1042 與 B-1024；名稱相近的兩個 tool | 用 handle 精確引用；tool 命名與分組（第 5 章） |
| 衝突（clash） | 互相矛盾的資訊同時存在 | 舊版 14 天與新版 7 天的退貨期限 | 來源只保留一個有效版本，標明生效日期 |
| 污染（poisoning） | 錯誤的內容進入 context 後被反覆引用 | 模型第 2 步猜錯單號，之後每一步都沿用 | 錯誤要明確標示、驗證關鍵事實；長任務做 compaction 時修正（第 10 章） |

這張表的四種失敗有一個共同點：它們都不是 context window 太小造成的，而是放進去的東西太多、太像、太矛盾或太髒。所以「換一個 context 更大的模型」通常不能解決它們，有時甚至讓情況更糟，因為更大的 window 讓團隊更放心地往裡面塞東西。表中最後一欄的對策，就是本章接下來幾節的內容。

> [!warning] 常見誤解
> 「1M context 的模型出來之後，context engineering 就不重要了。」實際上剛好相反。window 變大只是提高了上限，三種成本仍然隨 token 數成長，context rot 也沒有消失。能放下 100 萬個 token，意思是你有更多空間犯錯，而不是不需要做選擇。

> [!note] 2026 現況
> 截至 2026 年 10 月，1M token 的 context window 已經普及：Anthropic 的 Claude Fable 5.1、Opus 5.5、Sonnet 5.5 與 Google 的 Gemini 3 系列都是 1M。Anthropic〈Effective context engineering for AI agents〉（2025-09-29）提出 attention budget 的說法，指出 context rot 在所有模型上都存在，是漸進的斜坡。Chroma 的 context rot 報告（2025-07-14）測試 18 個模型，都隨輸入變長而變差；在 LongMemEval 上，只給聚焦的約 300 token 輸入，表現遠勝給完整的約 113K token 輸入。

## 9.3 Context 版面配置：依變動頻率分三層

### 為什麼需要分層

9.2 節的解剖圖說明了「放什麼」的問題，但還有一個同樣重要的問題是「放在哪裡」。第 3 章講過，prompt caching 比對的是從第一個 token 起完全相同的前綴；只要前面某處改了一個位元組，後面全部重算。這代表 context 的排列順序直接決定成本：如果會變的東西放在前面，就算後面 3 萬個 token 一模一樣也無法命中。反過來，如果依照「變動頻率」由慢到快排列，每次請求就只有尾端一小段是新的。

所以本書把 context 分成三層，稱為 context 的**版面配置**（layout）。**穩定前綴**是幾乎不變的內容，只有發版時才改，例如 tool 定義、system prompt、核心政策與少量範例，它在所有使用者、所有 session 之間共用。**半穩定層**是在一段 session 內不變、但不同 session 或不同租戶會不同的內容，例如店家設定、使用者的 memory 摘要、這次 session 載入的 skill 清單。**動態層**是每一步都在成長的內容，例如對話歷史、tool 結果、本輪的使用者訊息、時間與狀態提醒。

```text
 送給模型的 context 版面（由上而下 = 序列化順序）

 ┌─ 穩定前綴 ──────────────────────────────────────────────── 所有 session 共用 ─┐
 │ ① tool 定義    get_order、get_shipment、search_orders、read_policy、...      │
 │                （固定集合、固定順序、key 排序後序列化）                        │
 │ ② system       角色、規則、政策目錄、輸出格式（不放時間、不放使用者資料）     │
 └───────────────────────────────────────────────────────────────── ◆ BP1 ──────┘
 ┌─ 半穩定層 ──────────────────────────────────────── 同一 session／租戶內共用 ─┐
 │ ③ 租戶設定     商店：小森選物｜退貨 7 天｜只退原付款方式                     │
 │ ④ memory 摘要  顧客偏好簡短回覆｜曾退貨 1 次（第 12 章）                     │
 └───────────────────────────────────────────────────────────────── ◆ BP2 ──────┘
 ┌─ 動態層 ──────────────────────────────────────────────── 只會在尾端追加 ─────┐
 │ ⑤ 對話歷史     user / assistant(tool_calls) / tool 結果 ...                  │
 │ ⑥ 本輪輸入     最新的 user 訊息或 tool 結果＋狀態提醒（今天 10/02、待辦）     │
 └───────────────────────────────────────────────────────────────── ◆ BP3 ──────┘
 ┌─ 輸出保留 ──────────────────────────────────────────────────────────────────┐
 │ ⑦ thinking＋回答＋tool call 參數 ≤ max_tokens                               │
 └─────────────────────────────────────────────────────────────────────────────┘
 ◆ = cache breakpoint：「到這裡為止請快取」的標記
```

逐層看這張圖。①② 是穩定前綴，序列化的方式也要固定：tool 用固定順序，JSON 的 key 排序，否則同樣的內容也會產生不同的位元組。BP1 放在穩定前綴之後，這一段可以被所有顧客的所有對話共用，是命中率最高、最值錢的一段。③④ 是半穩定層，BP2 放在它之後，讓同一個 session 的後續呼叫都能命中到這裡；換一個顧客時，只有這一段與之後的內容需要重寫，穩定前綴照樣命中。⑤⑥ 是動態層，只在尾端追加，BP3 放在最後一則訊息上，而且會隨著對話成長往後移動，讓下一次呼叫能命中「到上一則訊息為止」的整段歷史。⑦ 不是輸入，但它和輸入共用 window，所以要在預算裡事先保留。

### Cache breakpoint 放在哪裡

**cache breakpoint**（快取斷點）是在請求中標記「從開頭到這裡為止，請把計算結果快取起來」的位置。有些供應商要你明確標記，有些會自動處理，但原理一樣：快取以「斷點之前的完整前綴」為單位寫入與查找。斷點的位置決定了兩件事：哪些內容能被共用，以及內容改變時損失多少。

放斷點的規則可以歸納成三條。第一，在每一個「變動頻率改變」的邊界放一個：穩定層與半穩定層之間、半穩定層與動態層之間。這樣半穩定層改變時，穩定前綴的快取還在；只有一個斷點放在最後的話，任何一層改變都會讓整段重算。第二，最後一個斷點放在最新一則訊息上，跟著對話往後移；agent loop 的每一步只追加一兩則訊息，所以上一輪的前綴幾乎全部能命中。第三，斷點之前不要放每次都不同的內容，因為只用一次的快取寫入通常比一般輸入更貴，第 3 章算過這筆帳。

這三條規則也說明了為什麼「時間」要放在動態層。Iris 把「現在時間 14:03:27」放在 system prompt 最上方，等於在 BP1 之前放了一個每秒都變的值。正確做法是把時間放在本輪輸入的狀態提醒裡，或者只精確到日期並放在半穩定層，讓它一天只改變一次。同樣的道理，「今日促銷」應該由 tool 查詢，或放在半穩定層，而不是插在穩定前綴裡。

| 層 | 典型內容 | 變動頻率 | 共用範圍 | cache 策略 | 青鳥的做法 |
|---|---|---|---|---|---|
| 穩定前綴 | tool 定義、system prompt、核心政策、canonical 範例 | 發版時 | 全部租戶與 session | BP1；確定性序列化；版本號管理 | 12 個 tool 固定順序；手冊只放目錄 |
| 半穩定層 | 租戶設定、memory 摘要、skill 清單、當日資訊 | 每個 session 或每天 | 同租戶或同 session | BP2；session 開始時組好就不改 | 店家退貨規則、顧客偏好 |
| 動態層 | 對話歷史、tool 結果、本輪提醒 | 每一步 | 單一 session | BP3 跟著尾端移動；只追加 | 大型 tool 結果存檔、只留 handle |
| 輸出保留 | thinking、回答、tool 參數 | 每一步 | 無 | 不快取；預算中預留 | 客服回覆保留 4K |

這張表最右欄的做法，就是 Iris 修正後的版面。值得注意的是共用範圍那一欄：越往上的層共用範圍越大，它的快取就越值錢，所以越要避免改動。多租戶系統尤其如此，第 42 章的設計演練會看到，穩定前綴能否在所有租戶之間共用，會直接影響平台的單位成本。

### 位置與注意力的拉扯

分層有一個值得說清楚的取捨。cache 希望穩定的內容放前面，但 9.2 節提到，模型對長輸入中間的資訊比較不敏感，對最後面的內容比較敏感。如果一個長任務的目標寫在最前面的 system prompt，經過四、五十步之後，它就被埋在大量 tool 結果的「中間」了。

實務上的解法是**複述**（recitation）：在動態層的尾端，定期追加一段簡短的目標與進度，例如「目前任務：為 B-1042 建立退貨單；已完成：確認送達時間；待做：確認退款方式」。Manus 公開描述過這個做法：agent 會反覆改寫一個 `todo.md`，讓目標一直出現在 context 的最近處。複述是追加而不是改寫，所以不破壞 cache；它付出的代價是每次多幾十個 token，換來的是長任務中目標不被遺忘。第 10 章會把這個概念延伸成長任務的進度檔。

> [!warning] 常見誤解
> 「把最重要的規則放在 system prompt 最前面，模型就一定會遵守。」放在前面的好處是穩定、可快取，但不保證注意力。真正重要的約束（例如退款上限）應該由 harness 在程式中強制，而不是只靠 context 的位置；需要模型時時記得的目標與狀態，則在尾端複述。

## 9.4 Cache 友善的變更：追加，不要改寫

### 為什麼不能在中途改 tool 定義

以 Anthropic 的公開文件為例，快取前綴依 tools、system、messages 的順序建立，tool 定義位置比 system prompt 還早；其他供應商的內部順序不一定公開，但 tool 定義同樣屬於每次請求都要送的前段內容。這代表 tool 清單是整個前綴的第一塊磚：在 loop 中途新增、移除或調換任何一個 tool，從第一個 token 開始的前綴就不一樣了，後面的 system prompt、半穩定層與整段歷史全部無法命中，即使它們一個字都沒變。Iris 的「提到優惠券才掛上 coupon tools」就是這種情況，每一段提到優惠券的對話都在中途把快取整個打掉一次。

除了成本，中途移除 tool 還有一個正確性問題。假設第 3 步模型呼叫過 `list_coupons`，第 5 步 harness 把它移除了，歷史裡卻還留著那次呼叫與結果。模型看到一個「用過、但現在不存在」的工具，可能繼續呼叫它，也可能被弄糊塗而改用名稱相近的錯誤 tool；harness 則要額外處理「呼叫了已移除的 tool」這種本來不必存在的錯誤。

```text
 同一段對話的五次請求：第 3 次之前，harness 掛上 apply_coupon

           [tools        ][system ][tenant][memory][#0..#1 ][#2..#3 ][#4..#5 ][#6..#7 ]
 請求 #1   ■■■■■■■■■■■■■■ ■■■■■■■■ □□□□□□□ □□□□□□□ □□□□□□□□                              ← 穩定層由別的 session 暖好
 請求 #2   ■■■■■■■■■■■■■■ ■■■■■■■■ ■■■■■■■ ■■■■■■■ ■■■■■■■■ □□□□□□□□
 請求 #3   □□□□□□□□□□□□□□□ □□□□□□□□ □□□□□□□ □□□□□□□ □□□□□□□□ □□□□□□□□ □□□□□□□□          ← tools 改了：全部重算
 請求 #4   ■■■■■■■■■■■■■■■ ■■■■■■■■ ■■■■■■■ ■■■■■■■ ■■■■■■■■ ■■■■■■■■ ■■■■■■■■ □□□□□□□□
 請求 #5   ■■■■■■■■■■■■■■■ ■■■■■■■■ ■■■■■■■ ■■■■■■■ ■■■■■■■■ ■■■■■■■■ ■■■■■■■■ ■■■■■■■■ □□
            ■ = cache read（便宜）   □ = 未命中，需重算並寫入（較貴）
```

這張時序圖由上往下是五次連續的請求。請求 #1 的穩定層已經被其他顧客的對話暖好，所以 tools 與 system 命中，只有這位顧客的半穩定層與第一則訊息要寫入。請求 #2 是理想狀態：除了新追加的兩則訊息，全部命中。請求 #3 之前，harness 在 tools 裡加了一個 `apply_coupon`，整列變成空心：連 system prompt 與早已存在的歷史都要重算並重新寫入，這一次呼叫的輸入成本比沒有快取還貴。請求 #4、#5 恢復正常，但 #3 付出的代價已經收不回來。9.9 節的程式會實際量出這張圖的數字。

### 替代做法：遮罩、拒絕、追加

如果某個 tool 只在特定情況下可以用，有三種不動前綴的做法。第一種是**固定超集合加上 harness 端拒絕**：`apply_coupon` 從一開始就在 tool 清單裡，描述寫明使用條件；狀態不允許時，harness 的 dispatch 直接回填「目前不可使用優惠券：尚未確認換貨訂單」。這和第 4 章的參數驗證是同一個位置，而且有副作用的 tool 本來就應該由程式把關，而不是靠模型看不到它。第二種是**遮罩**（masking）：不改 tool 清單，而是在解碼時限制本輪可以選擇的 tool。Manus 公開描述過它用 state machine 在解碼時遮罩 tool 選擇，並讓同類 tool 共用前綴（例如 `browser_`、`shell_`），方便一次遮罩一整組；託管 API 是否提供類似的參數、叫什麼名字，各家不同，要查當時的文件。第三種是**追加新定義**：真的需要新能力時，把 tool 定義附加在尾端，而不是插回開頭，這就是第 13 章 tool search 與 deferred loading 的做法，它的前提是不動既有的前綴。

用狀態機的角度看這件事，會更清楚為什麼「遮罩」比「移除」好：

```text
 客服對話的狀態與可用 tool（tool 清單始終是全集，變的只是允許集合）

   ┌──────────┐ 查到訂單   ┌──────────┐ 顧客確認換貨 ┌──────────┐
   │ 釐清問題 │──────────►│ 已定位訂單│────────────►│ 換貨處理中│
   └──────────┘            └──────────┘              └──────────┘
   允許：search_orders     允許：＋read_policy        允許：＋apply_coupon
         get_order               get_shipment               create_exchange
                                 create_return

   模型若在「已定位訂單」狀態呼叫 apply_coupon
     → dispatch 不執行，回填：「目前不可使用優惠券：需先確認換貨」
     → tools 前綴不變，cache 不受影響；歷史中的呼叫與結果維持配對
```

這張狀態機有三個狀態。每個狀態允許的 tool 是全集的一個子集，而且越往後允許越多。關鍵在於：狀態改變的只是 harness 裡的「允許集合」，送給模型的 tool 清單從頭到尾都是同一份全集。模型在錯誤的狀態呼叫了不允許的 tool，harness 回填一則可行動的錯誤訊息，模型下一步就會先去確認換貨。這同時滿足了三件事：前綴不變、歷史不出現「消失的 tool」、有副作用的動作由程式把關。

### 其他會打斷 cache 的 agent 特有變更

第 3 章列過讓 cache 失效的一般原因。agent 系統另外有一批「看起來很合理」的變更，它們的共同點是在前綴裡改寫內容，而不是在尾端追加。

| 想做的事 | 打斷 cache 的做法 | cache 友善的做法 | 代價 |
|---|---|---|---|
| 讓 agent 知道現在時間 | system prompt 開頭放精確到秒的時間 | 本輪訊息尾端附上時間，或日期放半穩定層 | 幾個 token |
| 某些情況才能用某個 tool | 中途增刪 tool 定義 | 固定全集＋dispatch 拒絕；或遮罩 | tool 定義常駐的 token |
| 需要新能力 | 把新 tool 插進清單開頭或中間 | tool search 把定義追加在尾端（第 13 章） | 一次額外的搜尋呼叫 |
| memory 更新了 | 改寫 system prompt 裡的 memory 段 | 本 session 不改，新事實追加到對話；下個 session 才更新半穩定層 | 本 session 內 memory 稍舊 |
| 檢索到新文件 | 把文件插進 system prompt | 以 tool 結果的形式追加在尾端 | 無 |
| 舊 tool 結果太佔空間 | 每一步都刪改不同的舊結果 | 寫入時就決定大小；真要清就一次清一大批 | 清理那一步 cache miss |
| 改變推理強度或換模型 | 任意一步就切換 | 固定設定；必須切換時選在 compaction 等「反正要重算」的時刻 | 切換時機較不彈性 |

這張表的每一列都在做同一個判斷：這個變更能不能用「追加」取代「改寫」？大多數情況可以，代價只是一點 token 或一點延後。少數真的必須改寫前綴的情況（清理舊結果、換模型、compaction），原則是**批次化**：一次改一大塊，讓 cache miss 的次數最少，而不是每一步都小改一點。第 10 章的 compaction 就是最典型的批次改寫，那一步注定要重算，所以也是切換模型或更新 memory 的好時機。

### 用分層指紋找出哪一層變了

上線後要怎麼知道前綴在哪裡被改了？最實用的做法是在 trace 裡記錄每一個區塊的**累積指紋**：從開頭到這個區塊為止的內容雜湊。兩次請求的指紋從第一個區塊開始比，第一個不同的位置，就是 cache 斷掉的地方。

```python
from __future__ import annotations

import hashlib
import json


def fingerprints(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """每個區塊記錄「從開頭到這裡」的累積雜湊；兩次請求第一個不同的位置，就是 cache 斷掉的地方。"""
    h, out = hashlib.sha256(), []
    for name, text in blocks:
        h.update(text.encode())
        out.append((name, h.hexdigest()[:8]))
    return out


def first_divergence(a: list[tuple[str, str]], b: list[tuple[str, str]]) -> str:
    for (name, fa), (_, fb) in zip(a, b):
        if fa != fb:
            return name
    return "（無：前綴完全相同）"


TOOLS = {"get_order": "查詢訂單", "get_shipment": "查詢貨態", "read_policy": "讀取政策"}


def request(system: str, tool_names: list[str]) -> list[tuple[str, str]]:
    tools = [{"name": n, "description": TOOLS[n]} for n in tool_names]
    return [("tools", json.dumps(tools, ensure_ascii=False, sort_keys=True)),
            ("system", system),
            ("tenant", "商店：小森選物｜退貨期限 7 天"),
            ("#0 user", "B-1042 到哪了？")]


base = fingerprints(request("你是青鳥客服。", ["get_order", "get_shipment", "read_policy"]))
cases = {
    "system 加上精確到秒的時間": request("你是青鳥客服。現在 14:03:27", ["get_order", "get_shipment", "read_policy"]),
    "tool 清單換了順序": request("你是青鳥客服。", ["get_shipment", "get_order", "read_policy"]),
    "只改了使用者訊息": request("你是青鳥客服。", ["get_order", "get_shipment", "read_policy"])[:3] + [("#0 user", "B-1042 呢？")],
}
for label, req in cases.items():
    print(f"{label:<16} → 第一個不同的區塊：{first_divergence(base, fingerprints(req))}")

assert first_divergence(base, fingerprints(cases["tool 清單換了順序"])) == "tools"
assert first_divergence(base, fingerprints(cases["只改了使用者訊息"])) == "#0 user"
```

```text
system 加上精確到秒的時間 → 第一個不同的區塊：system
tool 清單換了順序      → 第一個不同的區塊：tools
只改了使用者訊息         → 第一個不同的區塊：#0 user
```

三個情境對應三種典型的變更。加上時間後，第一個不同的區塊是 system，代表 tools 還能命中，但 system 與之後的一切都要重算。tool 清單換了順序，第一個不同的就是 tools，整個請求都要重算，即使集合完全相同。只改使用者訊息的情況，前三個區塊都相同，是正常的 append。實務上，把每個區塊的指紋與 token 數一起寫進 trace（第 29 章），cache 命中率掉下來時，就不必猜是誰改了 prompt，直接看第一個變色的區塊。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 Anthropic 文件，快取前綴依 tools、system、messages 的順序建立，每次請求最多 4 個明確的 breakpoint，另有自動 caching；系統會在 breakpoint 之前約 20 個 block 的範圍內往回找可命中的位置；中途改 top-level effort 或切換 thinking 設定會讓 cache 失效，另有 beta 的 per-message effort 切換可保留 cache。Manus（2025-07-18）把 KV-cache 命中率稱為 production agent 最重要的單一指標，並主張「mask, don't remove」。Cursor（2026-09-23）在穩定層之後設顯式 breakpoint，把會變動的 skills、subagents、環境資訊移到 breakpoint 之後的一則使用者訊息，cold cache miss 降約 20%。MCP 2026-07-28 版規格建議 `tools/list` 以固定順序回傳以利 prompt cache；Claude Agent SDK 在 resume 時保留 system prompt 快照以提升命中；Cognition 的 Devin Fusion 選在 compaction 時切換模型，避免額外的 cache 懲罰。

## 9.5 Token 預算與計數

### 為什麼預算要比 window 小

**token 預算**是你替每次呼叫設定的 input 與 output 上限，通常遠小於模型的 context window。例如模型支援 1M tokens，青鳥客服的每次呼叫卻只給 24K。理由是 9.2 節的三種成本：錢與延遲隨 token 線性甚至平方成長，注意力隨長度衰退，而客服問題的有用資訊很少超過幾千個 token。預算不是要省到極致，而是逼團隊在超出時做選擇：要壓縮、要存檔，還是真的需要更多空間。

第 4 章的 token 預算限制的是「整個 run 累計花多少」，是成本的保險絲；本節的預算限制的是「單次呼叫的 context 有多大」，是品質與延遲的保險絲。兩者要分開設定。單次預算再往下切成每一層的配額，就像部門預算：tool 定義與 system 有固定額度，檢索文件有上限，對話歷史拿剩下的，輸出保留一塊不能被挪用。

```text
 青鳥客服的單次呼叫預算（24K）

 0                 5K          9K    10.5K                         20K       24K
 ├─────────────────┼───────────┼──────┼─────────────────────────────┼─────────┤
 │ tools＋system   │ few-shot  │租戶＋│ 檢索政策 ≤6K ／ 對話歷史      │ 輸出保留 │
 │ 5K（固定）      │ ≤2K       │memory│ （兩者共用，超出時依優先序削減）│ 4K       │
 └─────────────────┴───────────┴──────┴─────────────────────────────┴─────────┘
  不可削減          最先削減    可縮到   歷史超出 → 舊 tool 結果存檔、    不可挪用
                               0.5K    仍超出 → compaction（第 10 章）
```

這張預算條由左到右對應版面配置的順序。左邊的 tools 與 system 是固定成本，不能在 run 中途削減，否則就是 9.4 節的中途改前綴。few-shot 範例是最先被削減的，因為模型在對話已經有幾輪實際示範之後，對範例的依賴會下降。租戶設定與 memory 可以縮到只留最關鍵的幾條。檢索政策與對話歷史共用中間最大的一塊，超出時先把舊的大型 tool 結果存檔、只留 handle，仍然超出才觸發 compaction。最右邊的輸出保留不能被挪用，否則模型在長 context 下會因為沒有空間而被截斷，出現第 4 章談過的 max_tokens 截斷（回應不完整、tool 參數只剩半截）。

### Token 怎麼算

要執行預算，就要知道每一段內容有多少 token。精確的方法是用供應商提供的 token 計數 API 或官方 tokenizer，但每次組裝 context 都呼叫一次 API 太慢，也不是每家都提供本地 tokenizer。實務上的做法是兩段式：組裝時用快速的粗估規則，事後用模型回應中的 `usage.input_tokens` 校正。粗估規則可以很簡單，例如中文每字約 1 個 token、英數字約每 4 個字元 1 個 token；校正則是持續記錄「實際值 ÷ 粗估值」的比例，用移動平均修正下一次的估算。

估算不準時，寧可高估。高估的代價是 context 用得比較保守；低估的代價是請求超出 window 被拒絕，或者輸出保留被吃掉而截斷。換模型或換 tokenizer 時，比例會改變，所以校正係數要以模型為單位分開記錄，而且新模型上線時要重新量測。

### 超出預算時削減什麼

當各層想要的 token 加起來超過預算，就要依優先序削減。下面的程式把這個決策寫成一個小函式：每一層有「想要多少」「最少保留多少」與「優先序」，從優先序最低的層開始削到底線，直到放得下為止；連底線都放不下，就明確地失敗，交給 compaction 或升級模型處理。

```python
from __future__ import annotations

from dataclasses import dataclass


def rough_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    return cjk + (len(text) - cjk + 3) // 4


class Calibrated:
    """用 API 回傳的真實 input_tokens 校正粗估值：取「實際 ÷ 粗估」的移動平均。"""

    def __init__(self, alpha: float = 0.3):
        self.ratio, self.alpha = 1.0, alpha

    def observe(self, text: str, actual: int) -> None:
        self.ratio = (1 - self.alpha) * self.ratio + self.alpha * actual / rough_tokens(text)

    def __call__(self, text: str) -> int:
        return round(rough_tokens(text) * self.ratio)


@dataclass
class Slot:
    name: str
    want: int          # 這一層想要的 tokens
    floor: int         # 最少要保留多少（0 代表可以整層拿掉）
    priority: int      # 數字越小越先被削減


def allocate(slots: list[Slot], budget: int) -> dict[str, int]:
    """超出預算時，從優先序最低的層開始削減到 floor，直到放得下為止。"""
    got = {s.name: s.want for s in slots}
    over = sum(got.values()) - budget
    for s in sorted(slots, key=lambda s: s.priority):
        if over <= 0:
            break
        cut = min(over, s.want - s.floor)
        got[s.name] -= cut
        over -= cut
    if over > 0:
        raise ValueError(f"連最低需求都放不下，還差 {over} tokens：需要 compaction 或換大 context 的模型")
    return got


est = Calibrated()
for text, actual in [("您的訂單 B-1042 已出貨", 14), ('{"status": "shipped", "tracking": "TC-88301"}', 19)]:
    est.observe(text, actual)                     # actual 是 API 回應 usage 裡的 input_tokens（這裡是假設值）
    print(f"粗估 {rough_tokens(text):>3}  實際 {actual:>3}  → 校正係數 {est.ratio:.2f}")

slots = [Slot("輸出保留", 4_000, 4_000, 99), Slot("tools＋system", 5_000, 5_000, 98),
         Slot("租戶設定與 memory", 1_500, 500, 3), Slot("檢索到的政策", 6_000, 1_500, 2),
         Slot("對話歷史", 14_000, 4_000, 1), Slot("few-shot 範例", 2_000, 0, 0)]
plan = allocate(slots, budget=24_000)
for s in slots:
    print(f"{s.name:<12} 想要 {s.want:>6,}  分到 {plan[s.name]:>6,}")
assert sum(plan.values()) == 24_000 and plan["few-shot 範例"] == 0 and plan["輸出保留"] == 4_000
```

```text
粗估   9  實際  14  → 校正係數 1.17
粗估  12  實際  19  → 校正係數 1.29
輸出保留         想要  4,000  分到  4,000
tools＋system 想要  5,000  分到  5,000
租戶設定與 memory 想要  1,500  分到  1,500
檢索到的政策       想要  6,000  分到  6,000
對話歷史         想要 14,000  分到  7,500
few-shot 範例  想要  2,000  分到      0
```

前兩行是校正：程式裡的「實際值」是假設的 usage 數字，粗估規則對這兩段含英數字與 JSON 的文字都低估了，校正係數從 1.0 往上調到 1.29，之後的估算會跟著放大。實務上 JSON 常比自然語言更容易被低估，因為引號、冒號與括號都會吃 token，這也是 tool 結果常常比預期更佔空間的原因；所以校正係數最好依內容類型（自然語言、JSON、程式碼）分開記錄。後六行是預算分配：六層想要的總量是 32,500，預算是 24,000，超出 8,500。few-shot 範例優先序最低，先被削到 0；剩下的 6,500 由對話歷史吸收，從 14,000 削到 7,500。輸出保留與 tools＋system 的優先序最高，一個 token 都沒少。對話歷史被削減在實作上代表什麼，是第 10 章的主題：先清掉舊的 tool 結果，再做摘要。

優先序本身是設計決策，要依產品調整。下表是青鳥客服採用的順序，以及每一項「為什麼排在這裡」。

| 削減順序 | 內容 | 削減方式 | 為什麼排在這裡 |
|---|---|---|---|
| 1（最先） | few-shot 範例 | 整段拿掉 | 對話中已有實際示範，邊際價值最低 |
| 2 | 舊的大型 tool 結果 | 存檔後換成 handle 與摘要 | 可還原，需要時能再讀回來 |
| 3 | 低分的檢索文件 | 只保留前 k 名 | 分數低的最可能是干擾 |
| 4 | 較早的對話輪次 | compaction 成交接摘要（第 10 章） | 不可完全還原，代價較高 |
| 5 | memory 摘要 | 縮到最關鍵的幾條 | 影響個人化，但不影響正確性 |
| 不削減 | tools、system、最新使用者訊息、未配對的 tool 結果、輸出保留 | 不動 | 削了就會破壞 cache、正確性或配對不變式 |

這張表的關鍵是第 2 項與第 4 項的差別：**可還原**的削減優先於不可還原的削減。存檔換 handle 之後，資訊並沒有消失，只是搬到 context 之外；摘要則會永久丟掉細節。最後一列的「不削減」也值得逐項記住，尤其是未配對的 tool 結果：第 4 章說過，每個 tool call 都要有對應的結果，削減時刪掉其中一半，API 會直接拒絕請求。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 提供 `count_tokens` 端點，可以在送出前計算請求的 input tokens，也能預覽 context editing 的效果；Anthropic 表示從 Opus 4.7 起改用新 tokenizer，同樣文字的 token 數約為舊版的 1 到 1.35 倍。Claude Code 把單次 tool 回傳上限預設為 25,000 tokens。Gemini CLI 的原始碼在超過模型上限 50% 時壓縮歷史，並保留最近約 30% 的原文。各家的計數方法與上限會隨版本調整，以官方文件為準。

## 9.6 Just-in-time 載入：帶引用，不帶內容

### 預先載入與按需載入

Iris v1 的做法叫**預先載入**（pre-loading）：在第一次呼叫模型之前，就把所有可能用到的資料放進 context。它的好處是簡單、模型不必多花步驟去拿；壞處是 9.2 節列出的所有成本。另一種做法是 **just-in-time 載入**（按需載入）：context 裡只放輕量的**引用**（reference），例如章節名稱、訂單編號、檔案路徑、查詢條件，模型判斷需要時再用 tool 把內容讀進來。這就像圖書館的目錄卡：你不會把整座圖書館搬到桌上，只會帶著目錄，需要哪本書再去拿。

```text
 just-in-time 載入一次「外套可以退嗎」

 harness                         Model                         政策庫／訂單庫
   │ context：tools＋system         │                               │
   │   ＋政策目錄（77 tokens）       │                               │
   │──── 呼叫 #1 ──────────────────►│                               │
   │◄─── read_policy("02 已出貨退貨")│                               │
   │──── 讀取該節 ────────────────────────────────────────────────►│
   │◄──────────────────────────────────────────── 約 530 tokens ───│
   │ 追加 tool 結果（尾端）          │                               │
   │──── 呼叫 #2 ──────────────────►│                               │
   │◄─── 回答：到貨 7 天內可退       │                               │
```

這張時序圖顯示 just-in-time 的完整節奏。第一次呼叫時，context 裡只有 tools、system 與一份 77 tokens 的政策目錄；模型從目錄判斷問題屬於「已出貨退貨」，於是呼叫 `read_policy` 只讀那一節。harness 把結果以 tool 訊息的形式追加在尾端，所以穩定前綴完全不受影響。第二次呼叫時，模型帶著剛讀進來的政策回答。整個過程多了一次 tool 呼叫，但 context 裡只出現了真正需要的那一節。

下面的程式比較青鳥退換貨手冊的兩種載入方式：全部預載，或只放目錄、按需讀取。

```python
from __future__ import annotations


def tokens(text: str) -> int:
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    return cjk + (len(text) - cjk + 3) // 4


# 青鳥的退換貨手冊：12 節，每節數百字（這裡用重複句子模擬長度）
HANDBOOK = {f"{i:02d} {title}": f"{title}的規定與例外說明。" * 40 for i, title in enumerate(
    ["未出貨取消", "已出貨退貨", "換貨", "瑕疵品", "預購商品", "海外訂單", "發票與折讓",
     "優惠券與點數", "分期付款", "禮品卡", "大型家具", "生鮮食品"], start=1)}
INDEX = "退換貨手冊章節（用 read_policy(section) 讀取）：" + "、".join(HANDBOOK)

questions = {"外套已送達想退貨": ["02 已出貨退貨"],
             "退貨後優惠券還在嗎": ["02 已出貨退貨", "08 優惠券與點數"],
             "B-1042 到哪了": []}

preload = tokens("".join(HANDBOOK.values()))
print(f"全部預先載入：每次呼叫都帶 {preload:,} tokens")
print(f"只放目錄：常駐 {tokens(INDEX)} tokens，其餘按需讀取")
for q, sections in questions.items():
    jit = tokens(INDEX) + sum(tokens(HANDBOOK[s]) for s in sections)
    print(f"  {q:<12} 讀 {len(sections)} 節 → context 約 {jit:>5,} tokens（預載的 {jit / preload:.0%}），多 {len(sections)} 次 tool 呼叫")
assert tokens(INDEX) < preload / 20
```

```text
全部預先載入：每次呼叫都帶 5,920 tokens
只放目錄：常駐 77 tokens，其餘按需讀取
  外套已送達想退貨     讀 1 節 → context 約   607 tokens（預載的 10%），多 1 次 tool 呼叫
  退貨後優惠券還在嗎    讀 2 節 → context 約 1,177 tokens（預載的 20%），多 2 次 tool 呼叫
  B-1042 到哪了   讀 0 節 → context 約    77 tokens（預載的 1%），多 0 次 tool 呼叫
```

第一行是預載的成本：12 節手冊共約 5,920 tokens，每次呼叫都要帶著，不管問題和退貨有沒有關係。第二行是 just-in-time 的常駐成本：目錄只有 77 tokens，因為每一節只留下標題。後三行是三個不同的問題：問退貨只讀 1 節，context 約是預載的 10%；問退貨與優惠券要讀 2 節，約 20%；問物流根本不需要讀手冊，只付目錄的 1%。代價是最右欄的額外 tool 呼叫：每多讀一節，就多一次模型往返的延遲。這個數字在真實手冊上會更懸殊，因為真實手冊有數十頁，但每個問題通常仍然只用到一兩節。

### 什麼時候預載、什麼時候按需

just-in-time 不是永遠比較好。它要求模型「知道自己不知道」，並且主動去讀；如果目錄寫得模糊，或模型過度自信，它可能不讀政策就直接回答，這比預載更危險。它也增加延遲，每一次讀取都是一次模型往返。所以實務上多半是混合式：少量、每次都要用、錯了代價很高的內容預載；大量、只有部分問題需要的內容按需載入。

| 判斷條件 | 傾向預載 | 傾向 just-in-time |
|---|---|---|
| 每次呼叫都會用到嗎？ | 是（角色、核心規則） | 否（某一節政策、某一筆訂單） |
| 內容大小 | 小（幾百到幾千 tokens） | 大，或大小無法預測 |
| 錯過它的後果 | 嚴重（例如退款上限沒看到） | 可以由 harness 或驗證補救 |
| 變動頻率 | 穩定，可以放進快取 | 常變，放前綴會打斷 cache |
| 延遲要求 | 嚴格，不能多一次往返 | 可以接受多一兩次 tool 呼叫 |
| 模型能否判斷何時需要 | 很難判斷 | 有清楚的目錄或描述可依循 |

這張表要整列一起看，而不是只看一個條件。青鳥最後的做法是：核心政策（退款上限、轉真人條件、寫入要確認）約 800 tokens 預載在 system；手冊其餘部分只放目錄，用 `read_policy` 按需讀取；訂單只放「顧客有 150 筆訂單，最近一筆是 B-1149」這樣的摘要，用 `search_orders` 搭配篩選條件查詢。另外，Iris 在 system prompt 裡加了一條規則：「回答政策問題前，一定先用 read_policy 讀取相關章節」，並在第 27 章的 eval 中檢查 agent 是否真的有讀。

> [!tip] 引用要能直接拿來用
> just-in-time 的引用要設計成模型可以直接當參數使用的形式。目錄裡寫「02 已出貨退貨」，`read_policy` 的參數就接受同樣的字串；tool 結果裡回傳 `"stored_at": "results/c1_search_orders.json"`，`read_file` 就接受同樣的路徑。模型需要自己改寫或猜測引用格式時，就是 9.2 節混淆與污染的開始。

just-in-time 也是第 11 章 agentic RAG 與第 12、13 章 Skills 漸進揭露的共同原則。Skills 的做法是把每個 skill 的名稱與一句描述放在 context 裡，判斷相關時才讀入完整說明，需要時再讀附加檔案或執行腳本，一層一層按需展開。檢索則是把「讀哪一節」的判斷從目錄擴展到搜尋。三者的差別在於引用的形式：目錄、搜尋查詢、skill 描述；共同點是 context 裡先放引用，內容按需進來。

## 9.7 檔案系統當外部 context

### 為什麼需要 context 之外的空間

just-in-time 解決的是「資料原本就在外部系統」的情況，例如政策庫與訂單庫。但 agent 在執行過程中也會自己產生大量資料：一次查詢回傳 150 筆訂單、一份 3,000 行的測試 log、一個網頁的全文。這些資料剛產生時在 context 裡，佔掉大量預算，之後的每一步都要重送。我們需要一個 agent 可以寫入、可以讀回、不限大小、而且不佔 context 的地方。

**檔案系統當外部 context** 就是這個答案：大型內容寫進檔案（或任何以路徑定址的儲存），context 裡只留路徑、大小與一小段預覽，agent 需要時再用 `read_file`、`grep` 這類 tool 讀取其中一部分。Manus 公開描述過這個設計：把檔案系統當成「無限、持久、agent 可以直接操作」的 context，並且要求壓縮必須**可還原**，例如丟掉網頁內容但保留 URL、丟掉文件內容但保留路徑。可還原是關鍵：被移出 context 的資訊沒有消失，只是需要多一步才能拿回來。

```text
 context window 與外部 workspace 的資料流

          context window（有限、每步重送）            workspace（不限大小、持久）
 ┌─────────────────────────────────────────┐      ┌─────────────────────────────────┐
 │ #2 tool search_orders 結果：            │      │ results/c1_search_orders.json  │
 │   {stored_at: results/c1_...json,      │ ◄─┐  │   150 筆訂單（約 3,400 tokens） │
 │    total_tokens: 3424,                 │   │  │                                 │
 │    preview: "[{"item": "商品0"...",     │   │  │ notes/progress.md               │
 │    hint: 用 read_file(path, query)}]    │   │  │   目標、已完成、待做            │
 │                                         │   │  └─────────────────────────────────┘
 │ #3 assistant：read_file(path, "外套")   │ ──┼──► 只讀出符合 query 的列
 │ #4 tool：[{"order_id": "B-1042", ...}]  │ ◄─┘
 └─────────────────────────────────────────┘
   寫入時就決定：超過 200 tokens 的 tool 結果一律存檔，context 只留 handle
```

圖的左邊是 context window，右邊是外部 workspace。`search_orders` 回傳 150 筆訂單時，harness 不把它直接放進 context，而是寫成 `results/c1_search_orders.json`，在 context 裡留下一則小小的 tool 結果：存放路徑、原始大小、一段預覽與使用提示。接著模型用 `read_file` 帶著路徑與查詢條件「外套」，只讀回符合的那一筆。圖的最下方是一條重要的設計決定：**在寫入時就決定大小**。如果先把 3,400 tokens 放進歷史，幾步之後才回頭把它換成 handle，那就是改寫歷史，cache 會在那一步斷掉；寫入時就存檔，歷史從一開始就是小的，之後永遠只需要追加。

### workspace 的三種用途

外部 context 在 agent 系統中有三種常見用途。第一種是**大型結果的卸載**，就是上圖的情況，適用於查詢結果、log、網頁、檔案內容。第二種是**筆記與進度檔**：agent 把目標、已完成的步驟、待做清單、重要發現寫進 `notes/progress.md` 這類檔案，長任務中斷或 compaction 之後，讀回這份筆記就能接續；它同時也是 9.3 節「複述」的來源。第三種是**跨步驟的中間產物**：research agent 的草稿、coding agent 的 patch、分析 agent 的中間表格，它們太大或太多，不適合一直放在 context 裡。第 10 章會深入第二種用途，第 17 章會談 coding agent 的真實檔案系統與 sandbox。

客服 agent 不一定有真實的檔案系統，但概念一樣適用：workspace 可以是 session 範圍的 key-value 儲存，路徑只是 key。重點是三個介面：寫入時回傳 handle、按 handle 與條件讀取部分內容、session 結束時依政策清除。

### 取捨與安全

外部 context 有三個代價。第一是多一步：模型要讀資料就要多一次 tool 呼叫，所以 handle 的預覽與提示要寫得足夠讓模型判斷「要不要讀、讀哪部分」。第二是一致性：檔案可能被後續步驟改寫，模型手上的舊預覽就過時了；需要的話在 handle 裡帶版本號或時間。第三是安全：workspace 裡的內容來自外部系統與網頁，可能夾帶指示模型做事的文字，讀回 context 時要和其他 tool 結果一樣視為不可信資料（第 31 章）；workspace 也必須以租戶與 session 隔離，路徑參數要由 harness 正規化與檢查，不能讓模型讀到別人的檔案（第 33 章）。

Maya 對青鳥的版本另外加了一條規則：寫進 workspace 的訂單資料先去除地址與電話，只保留客服需要的欄位，而且 session 結束 24 小時後清除。這同時解決了 9.1 節的個資問題：不需要的個資既不進 context，也不長期留在 workspace。

> [!note] 2026 現況
> 截至 2026 年 10 月，Claude Code 採用混合式載入：CLAUDE.md 等專案說明在開始時載入，其餘程式碼用 glob、grep 按需搜尋，不建向量索引。Gemini CLI 的原始碼會把超過門檻的舊 tool 輸出遮罩，並把原文落地到 `tool-outputs/` 目錄。Anthropic〈Effective harnesses for long-running agents〉（2025-11-26）描述長任務 agent 以 progress 檔與 JSON 格式的 feature 清單交接，並指出模型比較不會亂改 JSON。Agent Skills 以名稱與描述常駐、說明與附件按需讀取的三層漸進揭露運作。Manus（2025-07-18）描述以反覆改寫 `todo.md` 把目標複述到 context 尾端，其典型任務約 50 次 tool 呼叫。

## 9.8 Context 視覺化與量測

### 看不見的東西就無法管理

context 的問題很少會自己報錯。cache 命中率下降不會讓請求失敗，只會讓帳單變高；干擾與衝突不會丟例外，只會讓答案偶爾錯。所以 context 必須被量測與視覺化，而且要細到「每一層」。只看每次呼叫的總 input tokens，你只會知道「變大了」，不會知道是哪一層、從哪一次部署開始。

最有用的視覺化是**每一步的 context 組成圖**：把每一次呼叫的穩定層、半穩定層、動態層 token 數畫成堆疊長條，並標出 cache 命中比例。9.9 節的程式會印出這張圖。看這張圖時，健康的形狀是穩定層與半穩定層的長度固定、動態層緩慢成長、命中率隨步數升高；不健康的形狀是穩定層長度在 session 中途改變（有人改了前綴）、動態層某一步突然暴增（有未截斷的大結果）、或命中率在某一步掉到零（前綴斷了）。

```text
 trace 中每一次模型呼叫應該記錄的 context 欄位

 span: chat  step=3  session=s-7781  tenant=小森選物
 ├─ layout
 │   ├─ stable   tokens=567   fingerprint=9f2c41ab   version=prompt-v14/tools-v9
 │   ├─ semi     tokens=126   fingerprint=03be77d1
 │   └─ dynamic  tokens=232   messages=6   largest=#2 tool(search_orders, 94)
 ├─ usage（供應商回報）
 │   ├─ input=925  cache_read=842  cache_write=83  output=48
 │   └─ hit_rate=91%   estimate_error=+4%（粗估 vs 實際）
 ├─ budget  used=925 / 3,200（輸出保留 800 另計）
 └─ workspace  offloaded=[results/c1_search_orders.json: 3,424]
```

這是一個 trace span 的示意，span 名稱 `chat` 沿用 OpenTelemetry GenAI 語意慣例中「一次模型呼叫」的名稱（第 29 章），下面分成四組欄位。layout 記錄每一層的 token 數、指紋與版本，指紋用來找出 9.4 節「哪一層變了」，版本讓你把命中率的變化對上部署紀錄。usage 記錄供應商回報的真實數字，包含 cache read 與 cache write，並和粗估值比較，持續校正 9.5 節的估算係數。budget 記錄這次用了多少預算，接近上限的 session 是 compaction 的候選。workspace 記錄這一步卸載了哪些大結果，讓你在除錯時知道模型「看到的」和「實際存在的」差在哪裡。這些欄位大多可以對應到 OpenTelemetry 的 GenAI 語意慣例，第 29 章會實作完整的 tracer。

### 要盯哪些指標

| 指標 | 定義 | 警訊 | 常見原因與動作 |
|---|---|---|---|
| cache 命中率 | cache_read ÷ input tokens（依 session 或部署聚合） | 部署後明顯下降 | 比對各層指紋；找出改了前綴的變更 |
| 各層 token 數 | 每次呼叫的 stable／semi／dynamic | stable 在 session 內變動 | 中途改 tool 或 system；改為追加 |
| 單次 input 的 p95 | 單次呼叫 input tokens 的 95 百分位 | 持續上升或出現長尾 | 未截斷的大結果；加卸載門檻 |
| 預算使用率 | used ÷ 單次預算 | 大量 session 超過八成 | 檢查是否該 compaction 或調整配額 |
| 最大單一區塊佔比 | 最大一則 tool 結果 ÷ 動態層 | 單一區塊超過一半 | 改成寫入時存檔、回傳 handle |
| 估算誤差 | （實際 − 粗估）÷ 實際 | 換模型後誤差變大 | 重新校正係數，必要時改用計數 API |
| 引用後讀取率 | 拿到 handle 後實際讀取的比例 | 接近 0 或接近 100% | 0：預覽不夠或模型偷懶；100%：該直接給內容 |

這張表的前兩列是成本面，第三到第五列是容量面，最後兩列是 context 設計本身的品質。最後一列特別值得說明：如果模型拿到 handle 後幾乎從不讀取，要確認它是不是在沒看資料的情況下就回答；如果幾乎每次都讀取，代表這類資料其實每次都需要，直接放進 context 反而省一次往返。量測的目的不是讓數字好看，而是讓 9.3 到 9.7 節的每一個設計決定都有回饋。

> [!note] 2026 現況
> 截至 2026 年 10 月，Claude Code 提供 `/context` 指令，顯示目前 context 中各類內容的佔用情況。OpenTelemetry 的 GenAI 語意慣例定義了 input、output tokens 等 usage 屬性，並包含 cache read 與 cache write 的細分；各家觀測平台的支援程度不同。主流 API 會在回應的 usage 中回報快取命中的 token 數，Anthropic 另外回報快取寫入量，欄位名稱依供應商而異。

## 9.9 動手做：依預算組裝 context 的 builder

這一節把本章的概念組成一個 context builder，並用 ScriptedModel 跑一段完整的退貨對話。程式有四個部分。`tokens()` 是 9.5 節的粗估規則，`render()` 用排序 key 的 JSON 做確定性序列化。`ContextBuilder` 依「tools、system → 半穩定層 → 動態層」的順序組裝，在三個層的邊界放 breakpoint，並在超出預算時拒絕組裝；它的 `tool_message()` 在寫入時就檢查 tool 結果的大小，超過門檻就存進 workspace、只留 handle。`PrefixCache` 模擬供應商的 prefix cache：只在 breakpoint 寫入，查找時往回找最長的已快取前綴。最後的 `run()` 跑三個情境：A 版面穩定，`apply_coupon` 從一開始就在 tool 清單裡；B 在第 2 步之後才把 `apply_coupon` 掛上去；C 在第 2 步之後更新了半穩定層的 memory。

為了讓情境更接近真實，每個情境開始前，都先用「另一位顧客」的請求暖一次 cache，模擬穩定前綴已經被其他 session 快取的狀況。成本倍率沿用第 3 章的示意值：cache read 為一般輸入價的 0.1 倍，cache write 為 1.25 倍。

```python
from __future__ import annotations

import hashlib
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
    """劇本小工具：產生一個「呼叫 name 工具」的回應。"""
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


# ───────────── context builder：分層、量測、預算、外部 context ─────────────
def tokens(text: str) -> int:
    """粗估：中文每字約 1 token，其他字元約 4 個 1 token。上線前要用供應商的計數 API 校正。"""
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    return cjk + (len(text) - cjk + 3) // 4


def render(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)   # 確定性序列化：同樣的資料永遠同樣的位元組


@dataclass
class Segment:
    layer: str                                  # stable｜semi｜dynamic
    name: str
    text: str


class BudgetExceeded(Exception):
    pass


class ContextBuilder:
    def __init__(self, tools: list[dict], system: str, budget: int, output_reserve: int, max_tool_tokens: int):
        self.tools, self.system = tools, system
        self.budget, self.output_reserve, self.max_tool_tokens = budget, output_reserve, max_tool_tokens
        self.workspace: dict[str, str] = {}      # 外部 context：大結果存這裡，context 只留 handle

    def tool_message(self, tc: ToolCall, result: Any) -> dict:
        """在「寫入時」就決定大小：之後不必回頭刪改歷史，前綴才保得住。"""
        text = result if isinstance(result, str) else render(result)
        if tokens(text) > self.max_tool_tokens:
            path = f"results/{tc.id}_{tc.name}.json"
            self.workspace[path] = text
            text = render({"stored_at": path, "total_tokens": tokens(text), "preview": text[:60],
                           "hint": "完整內容已存檔，用 read_file(path, query) 只讀需要的部分"})
        return {"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": text}

    def build(self, semi: dict[str, str], messages: list[dict]) -> tuple[list[Segment], list[int]]:
        segs = [Segment("stable", "tools", render(self.tools)), Segment("stable", "system", self.system)]
        segs += [Segment("semi", k, v) for k, v in semi.items()]
        segs += [Segment("dynamic", f"#{i} {m['role']}", render(m)) for i, m in enumerate(messages)]
        breakpoints = [1, 1 + len(semi), len(segs) - 1]   # 穩定層之後、半穩定層之後、最後一則訊息
        used = sum(tokens(s.text) for s in segs)
        if used + self.output_reserve > self.budget:
            raise BudgetExceeded(f"需要 {used}＋輸出保留 {self.output_reserve}，超過預算 {self.budget}")
        return segs, breakpoints


class PrefixCache:
    """模擬供應商的 prefix cache：只在 breakpoint 查找與寫入，比對從第一個位元組起的完整前綴。"""

    def __init__(self):
        self.store: set[str] = set()

    def lookup(self, segs: list[Segment], breakpoints: list[int]) -> tuple[int, int]:
        h, cum, read, writes = hashlib.sha256(), 0, 0, []
        for i, s in enumerate(segs):
            h.update(s.text.encode())
            cum += tokens(s.text)
            key = h.hexdigest()
            if key in self.store:               # 查找：往回找「曾經在 breakpoint 寫入過」的最長前綴
                read = cum
            if i in breakpoints:                # 寫入：只發生在 breakpoint
                writes.append(key)
        self.store.update(writes)
        return read, cum                         # (cache 命中的 tokens, 這次的 input tokens)


# ───────────── 青鳥客服的假後端 ─────────────
ORDERS = [{"order_id": f"B-{1000 + i}", "item": "藍色外套" if i == 42 else f"商品{i}", "status": "shipped",
           "tracking": f"TC-{88259 + i}"} for i in range(150)]
POLICY = {"已出貨退貨": "已出貨訂單在到貨 7 天內可建立退貨單，物流到府取件；退款於收到退貨後 3 個工作天內完成。"}
IMPL = {
    "search_orders": lambda email: ORDERS,
    "read_file": None,                                     # 由 builder.workspace 提供，見下方
    "read_policy": lambda section: POLICY[section],
    "get_shipment": lambda tracking: {"tracking": tracking, "status": "已送達", "delivered": "3 天前"},
    "apply_coupon": lambda order_id, code: {"ok": True},
}


def tool(name: str, desc: str, **params: str) -> dict:
    return {"name": name, "description": desc, "parameters": {"type": "object", "required": list(params),
            "properties": {k: {"type": "string", "description": v} for k, v in params.items()}}}


BASE_TOOLS = [
    tool("search_orders", "依顧客 email 列出最近 90 天訂單", email="顧客 email"),
    tool("read_file", "讀取已存檔的大型結果，只回傳和 query 相關的列", path="存檔路徑", query="關鍵字"),
    tool("read_policy", "讀取退換貨政策的某一節；可用章節：已出貨退貨、未出貨取消、換貨", section="章節名稱"),
    tool("get_shipment", "用物流單號查詢貨態", tracking="物流單號，例如 TC-88301"),
]
COUPON = tool("apply_coupon", "把優惠券套用到換貨訂單；只有政策允許時才能用", order_id="訂單編號", code="優惠碼")
SYSTEM = ("你是青鳥科技的客服助理，只處理訂單、物流與退換貨。查不到的事情要說查不到，不可猜測。"
          "政策以 read_policy 的內容為準；寫入動作（退貨、套用優惠券）先向使用者確認。" * 3)


def script() -> list:
    def read_handle(msgs: list[dict]):          # 模型從 tool 結果裡拿到 handle，再按需讀取
        handle = json.loads(msgs[-1]["content"])["stored_at"]
        return call("read_file", "c2", path=handle, query="外套")
    return [call("search_orders", "c1", email="amy@example.com"), read_handle,
            call("read_policy", "c3", section="已出貨退貨"), call("get_shipment", "c4", tracking="TC-88301"),
            say("您的藍色外套（B-1042）3 天前送達，可在 7 天內退貨；要幫您建立退貨單嗎？")]


def run(scenario: str) -> list[dict]:
    tools = BASE_TOOLS + ([] if scenario == "B 中途加入 tool" else [COUPON])
    b = ContextBuilder(tools, SYSTEM, budget=4_000, output_reserve=800, max_tool_tokens=200)
    impl = dict(IMPL, read_file=lambda path, query: [l for l in json.loads(b.workspace[path]) if query in l["item"]])
    semi = {"tenant": "商店：小森選物｜退貨期限 7 天｜只退回原付款方式｜換貨免運一次｜" * 4,
            "memory": "顧客 amy@example.com｜偏好簡短回覆｜曾退貨 1 次"}
    cache = PrefixCache()
    cache.lookup(*b.build(dict(semi, memory="（另一位顧客）"), [{"role": "user", "content": "你好"}]))  # 別的 session 先暖好穩定層
    model, messages, log = ScriptedModel(script()), [{"role": "user", "content": "上個月買的外套想退貨"}], []
    for step in range(1, 9):
        segs, bps = b.build(semi, messages)
        read, total = cache.lookup(segs, bps)
        layers = {k: sum(tokens(s.text) for s in segs if s.layer == k) for k in ("stable", "semi", "dynamic")}
        log.append({"step": step, "read": read, "total": total, **layers})
        resp = model.complete(messages, tools=b.tools, system=b.system)
        messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
        if not resp.tool_calls:
            break
        for tc in resp.tool_calls:
            messages.append(b.tool_message(tc, impl[tc.name](**tc.args)))
        if step == 2 and scenario == "B 中途加入 tool":
            b.tools = b.tools + [COUPON]                 # 反模式：在 loop 中途改 tool 定義
        if step == 2 and scenario == "C 中途更新 memory":
            semi = dict(semi, memory="顧客偏好：簡短回覆｜傾向換貨")
    log[-1]["workspace"] = {p: tokens(t) for p, t in b.workspace.items()}
    return log


results = {s: run(s) for s in ("A 穩定版面", "B 中途加入 tool", "C 中途更新 memory")}

print("A 每次呼叫的 context 組成（tokens）與 cache 命中")
for r in results["A 穩定版面"]:
    bar = "█" * (r["stable"] // 40) + "▒" * (r["semi"] // 40) + "░" * (r["dynamic"] // 40)
    print(f" step {r['step']}  穩定 {r['stable']:>3}  半穩定 {r['semi']:>2}  動態 {r['dynamic']:>3}"
          f"  命中 {r['read'] / r['total']:>4.0%}  {bar}")
last = results["A 穩定版面"][-1]
print(f" 最後一步用掉 {last['total']} / 可用 {4_000 - 800}（預算 4000 − 輸出保留 800）")
print(" 存到 workspace 的大結果：", last["workspace"])
print()
summary = {}
for name, log in results.items():
    read, total = sum(r["read"] for r in log), sum(r["total"] for r in log)
    cost = (read * 0.10 + (total - read) * 1.25) / total       # 示意倍率：讀取 0.1、寫入 1.25（第 3 章）
    summary[name] = (read / total, cost)
    rates = " ".join(f"{r['read'] / r['total']:>4.0%}" for r in log)
    print(f"{name:<13} 各步命中率 {rates}｜input {total}｜命中 {read}｜輸入成本 {cost:.2f}（無快取 = 1）")

a, bb, c = summary["A 穩定版面"], summary["B 中途加入 tool"], summary["C 中途更新 memory"]
assert a[0] > c[0] > bb[0]                      # 改 tools 傷害最大，改半穩定層只傷一部分
assert results["B 中途加入 tool"][2]["read"] == 0  # 加 tool 的下一步：整段前綴失效，連穩定層都要重寫
assert results["C 中途更新 memory"][2]["read"] == results["C 中途更新 memory"][2]["stable"]  # 只保住穩定層
assert all(r["total"] + 800 <= 4_000 for log in results.values() for r in log)
try:
    ContextBuilder(BASE_TOOLS, SYSTEM, 4_000, 800, 10**6).build({}, [{"role": "tool", "content": render(ORDERS)}])
except BudgetExceeded as exc:
    print("\n不存檔、把 150 筆訂單直接塞進 context：", exc)
```

```text
A 每次呼叫的 context 組成（tokens）與 cache 命中
 step 1  穩定 567  半穩定 126  動態  18  命中  80%  ██████████████▒▒▒
 step 2  穩定 567  半穩定 126  動態 145  命中  85%  ██████████████▒▒▒░░░
 step 3  穩定 567  半穩定 126  動態 232  命中  91%  ██████████████▒▒▒░░░░░
 step 4  穩定 567  半穩定 126  動態 325  命中  91%  ██████████████▒▒▒░░░░░░░░
 step 5  穩定 567  半穩定 126  動態 398  命中  93%  ██████████████▒▒▒░░░░░░░░░
 最後一步用掉 1091 / 可用 3200（預算 4000 − 輸出保留 800）
 存到 workspace 的大結果： {'results/c1_search_orders.json': 3424}

A 穩定版面        各步命中率  80%  85%  91%  91%  93%｜input 4583｜命中 4059｜輸入成本 0.23（無快取 = 1）
B 中途加入 tool   各步命中率  77%  83%   0%  91%  93%｜input 4413｜命中 3051｜輸入成本 0.45（無快取 = 1）
C 中途更新 memory 各步命中率  80%  85%  62%  91%  93%｜input 4568｜命中 3778｜輸入成本 0.30（無快取 = 1）

不存檔、把 150 筆訂單直接塞進 context： 需要 4514＋輸出保留 800，超過預算 4000
```

逐段解說這份輸出。

**第一段是情境 A 每一步的 context 組成。** 穩定層固定 567 tokens、半穩定層固定 126 tokens，五步都沒變，這正是健康的形狀。動態層從 18 成長到 398，每一步只追加一則 assistant 訊息與一則 tool 結果。長條圖的 █ 是穩定層、▒ 是半穩定層、░ 是動態層，一眼就能看出成長只發生在尾端。命中率從 80% 升到 93%：step 1 只命中由別的 session 暖好的穩定層（567 ÷ 711），因為這位顧客的半穩定層是第一次出現；step 2 起，上一步寫入的整段前綴都能命中，只有新追加的兩則訊息需要寫入。

**第二段是預算與 workspace。** 最後一步只用了 1,091 tokens，遠低於可用的 3,200。原因在 workspace 那一行：`search_orders` 回傳的 150 筆訂單約 3,424 tokens，超過 200 tokens 的門檻，在寫入時就被存進 `results/c1_search_orders.json`，context 裡只留下 handle。劇本的第 2 步是一個函式，它從上一則 tool 結果裡取出 `stored_at`，再呼叫 `read_file(path, "外套")`，模擬模型「拿到引用、按需讀取」的行為，結果只讀回 B-1042 那一筆。

**第三段是三個情境的比較，也是本章最重要的一組數字。** A 的總輸入成本是無快取時的 0.23。B 在第 3 步的命中率是 0%：因為 `apply_coupon` 被加進 tools，而 tools 位於整個前綴的最前面，連穩定層都要重寫，那一步的輸入全部以寫入價計費；第 4 步之後恢復到 91%、93%，但 B 的總成本已經變成 0.45，幾乎是 A 的兩倍。對照組 C 在第 3 步更新了 memory，命中率降到 62%，剛好等於只保住穩定層的比例；因為半穩定層之前有 BP1，穩定前綴的快取保住了，C 的總成本是 0.30，介於 A 與 B 之間。這三個數字說明了兩件事：tool 定義是最不能在中途改的東西；分層放 breakpoint 的價值，在於讓「較慢變動的層」不被較快變動的層拖下水。

**最後一行是對照實驗。** 如果不做卸載，把 150 筆訂單直接放進 context，光是這一則訊息加上穩定層就需要 4,514 tokens，再加上 800 的輸出保留，超過 4,000 的預算，builder 直接拒絕組裝。這是刻意的設計：超出預算時明確失敗，讓上層選擇卸載、compaction 或換模型，而不是悄悄把輸出保留吃掉，等到回答被截斷才發現。

程式末尾的 assert 鎖住了這些行為：三個情境的命中率排序是 A 高於 C、C 高於 B；B 在加 tool 後的那一步命中為 0；C 在更新 memory 後那一步的命中量恰好等於穩定層；所有請求都在預算之內。之後任何人修改 builder，例如為了「省 token」在中途移除用不到的 tool，這幾個 assert 會立刻失敗。

| 零件 | 新增的能力 | 對應小節 | 修掉的 v1 問題 |
|---|---|---|---|
| 確定性序列化 | `render()` 排序 key | 9.4 | 同樣內容不同位元組 |
| 三層版面＋三個 breakpoint | `build()` | 9.3 | 時間戳與 memory 放在前綴打斷 cache |
| 單次預算與輸出保留 | `BudgetExceeded` | 9.5 | 輸出空間被吃掉 |
| 寫入時卸載 | `tool_message()` 與 workspace | 9.6、9.7 | 90 天訂單佔滿 context、個資外露 |
| 每層量測與命中模擬 | `PrefixCache`、組成長條圖 | 9.8 | 問題要等帳單才發現 |

這張表把 builder 的每一個零件對回本章的小節與 9.1 節的問題。`loom` 會把這個 builder 收進 `loom.context` 模組：第 10 章在 `BudgetExceeded` 的位置接上 compaction，第 12 章把 memory 接到半穩定層，第 13 章把 tool search 接到「追加 tool 定義」的路徑上。這個實作刻意沒做的事也要說清楚：cache 模擬沒有 TTL 與最小可快取長度，token 估算沒有真實 tokenizer 精準，workspace 只在記憶體裡、沒有隔離與清除政策。這些在真實系統裡都必須補上，但不影響本節要驗證的結論。

## 9.10 實務應用

本章的分層、預算、按需載入與外部 context，在不同產品裡的比重差很多。以下四個情境說明同一套原則怎麼調整。

**情境一：多租戶電商客服（青鳥的主線）。** 數千家店家共用同一個 agent，穩定前綴（tools 與 system）在所有租戶之間共用，是命中率最高的一段，所以任何租戶特定的內容都不能放進穩定前綴，只能放在半穩定層。店家的退貨規則、語氣設定放在 BP2 之前，在同一個 session 內不改；店家在後台修改規則時，新規則從下一個 session 才生效，並在後台明確告知店家。客服對話通常只有數步，動態層不會太長，所以主要的成本來自穩定前綴與半穩定層的命中率，以及大型 tool 結果是否卸載。同步互動對 TTFT 很敏感，cache 命中率同時也是延遲指標。

**情境二：coding agent。** coding agent 的任務常有數十到數百步，動態層是主要的成本與 context rot 來源。主流 coding agent 的公開做法很一致：專案說明檔（例如 CLAUDE.md、AGENTS.md）在開始時預載，原始碼用 glob、grep、讀檔按需載入，不把整個 repo 放進 context；大型的測試 log 與建置輸出截斷或落地成檔案，只把錯誤所在的段落帶回 context；長任務用進度檔與 todo 清單複述目標。這類 agent 也最常遇到「中途改 tool」的誘惑，例如安裝了新的 MCP server，主流做法是讓這些 tool 延遲載入、以搜尋的方式追加，而不是改動既有的 tool 清單（第 13 章）。

**情境三：營運 research 與數據分析 agent。** 青鳥的營運 research agent 要讀數十份報表與網頁，原始資料的總量遠超過任何 context window。這裡外部 context 是主角：每一份讀過的資料都存檔並留下 URL 或路徑，context 裡只放摘要與引用；研究計畫與中間發現寫進筆記檔，讓 compaction 或中斷之後能接續。Anthropic 公開描述的 multi-agent research 系統也採取類似原則：主導的 agent 把研究計畫存進 memory，避免 context 被截斷時遺失，subagent 在各自乾淨的 context 中探索，只回傳濃縮的結果（第 20 章）。數據分析則常用第 13 章的 code-as-action：與其把上萬列資料放進 context，不如讓 agent 寫程式在 sandbox 裡算完，只把結果帶回來。

**情境四：語音客服 agent。** 語音互動對延遲的容忍度比文字低很多，使用者在電話另一頭等待時，一兩秒的沉默就很明顯。這類 agent 的 context 設計以 TTFT 為第一優先：穩定前綴要盡量命中，動態層要短，just-in-time 的額外往返要謹慎使用，常見問題所需的政策直接預載在 system 裡。另外，語音轉文字的逐字稿常有大量口語贅詞與辨識錯誤，直接全部放進歷史會造成干擾，常見做法是在追加到動態層之前先做正規化，只保留語意內容。

| 產品類型 | context 的主要壓力 | 重點技術 | 特別注意 |
|---|---|---|---|
| 多租戶客服 | 穩定前綴的跨租戶共用 | 三層版面、租戶內容只進半穩定層 | 店家改設定從下個 session 生效 |
| coding agent | 動態層長、tool 結果大 | 說明檔預載＋按需讀檔、log 落地、進度檔 | 新 tool 以追加方式加入 |
| research／分析 | 原始資料遠超 window | 外部 context、筆記檔、subagent 隔離 | 卸載必須可還原（保留 URL 與路徑） |
| 語音客服 | TTFT | 高命中率、短動態層、常用政策預載 | 逐字稿正規化後再進歷史 |

這張表顯示同一套原則的不同側重。共同點是三件事：穩定的放前面且不改，大的放外面且留引用，動態的只追加。差別在於每個產品最貴的資源不同：客服在乎共用，coding 在乎長度，research 在乎總量，語音在乎延遲。

> [!note] 2026 現況
> 截至 2026 年 10 月，依公開資料：Claude Code 的 MCP tool 預設延遲載入，透過 tool search 按需加入，常駐的只有 tool 名稱與 server 說明；Cursor（2026-09-23）把使用率低於兩成對話的內建 tool 改成按需載入，並大幅縮減 system prompt，報告整體 token 降低約 7% 而品質不變；Claude Managed Agents（2026-04-08）把持久的 session log 與 context window 分開，context 被視為 log 的一個可重建視圖（第 10 章）。各產品的實作細節會持續變動，以官方文件與 engineering blog 為準。

## 9.11 設計檢查清單

設計或審查一個 agent 的 context 時，逐項回答下面的問題：

1. 每一個 context 區塊是否都標明了它屬於穩定前綴、半穩定層還是動態層？排列順序是否依變動頻率由慢到快？
2. 穩定前綴中是否完全沒有時間戳、request id、使用者資料、租戶設定這類會變的值？
3. tool 清單在一次 run 中是否固定集合、固定順序？條件式可用的 tool 是用 dispatch 拒絕或遮罩處理，而不是中途增刪？
4. 所有序列化（tool 定義、JSON 結果）是否是確定性的（排序 key、固定欄位順序、不從 set 產生順序）？
5. cache breakpoint 是否放在每個變動頻率的邊界，最後一個是否隨對話尾端移動？
6. 是否為單次呼叫設定了 token 預算與輸出保留，並為每一層訂了配額？超出時的削減順序是否寫成程式？
7. token 估算是否用供應商回報的 usage 持續校正？換模型時是否重新校正？
8. 大型 tool 結果是否在寫入時就決定卸載，而不是事後回頭改寫歷史？卸載的門檻是多少？
9. 被卸載或被削減的資訊是否可還原（保留路徑、URL、handle）？handle 的格式能否直接當 tool 參數使用？
10. 哪些內容預載、哪些按需載入？按需載入的部分，是否有 eval 檢查模型真的會去讀？
11. workspace 是否依租戶與 session 隔離、路徑由 harness 檢查、個資在寫入前去除、並有清除期限？
12. trace 是否記錄每層的 token 數、指紋、版本，以及 cache read／write？是否有命中率下降的告警？
13. 必須改寫前綴的操作（清理舊結果、換模型、更新 memory）是否批次化，並集中在 compaction 等時機？

## 9.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| cache 命中率長期接近零 | 穩定前綴含時間戳或 request id；序列化不確定 | 比對兩次請求的分層指紋，看第一個不同的區塊 | 會變的值移到動態層；序列化排序 key |
| 某類對話的成本突然翻倍 | 對話中途增刪 tool 定義 | trace 中 stable 層 token 數在 session 內改變 | 固定 tool 全集；以 dispatch 拒絕或遮罩取代增刪 |
| 部署後命中率下降 | 新版本改了 system 或 tool 描述；或每個 session 的 tool 順序不同 | 依版本號聚合命中率；檢查 tools 指紋的種類數 | 固定順序；一次部署只改一次前綴並觀察 |
| 模型引用過時或矛盾的政策 | 新舊版本同時在 context 中（衝突） | 在 trace 中搜尋同一條規則的不同版本 | 來源端只保留有效版本；標明生效日期 |
| 模型拿錯相似的訂單或檔案 | 大量相似項目並列（混淆） | 看錯誤回答時 context 中相鄰的項目 | 以 handle 精確引用；只載入需要的那一筆 |
| 回答被截斷、tool 參數不完整 | 長 context 吃掉輸出保留 | stop_reason 為 max_tokens 時檢查 input 大小 | 預算中固定輸出保留；超出時明確失敗並 compaction |
| 拿到 handle 卻從不讀取就回答 | 預覽不足或規則不明，模型直接猜 | 統計引用後讀取率；抽樣看答案是否有依據 | 預覽附上關鍵欄位；規則要求先讀；eval 檢查 |
| 長任務後期忘記目標 | 目標只在最前面，被大量 tool 結果埋在中間 | 比較前期與後期步驟是否偏離原始目標 | 在尾端複述目標與進度；進度檔 |
| 每一步都有少量 cache miss | 每步都回頭清理不同的舊 tool 結果 | 看 cache_write 是否每步都包含歷史中段 | 寫入時卸載；需要清理時一次清一大批 |

## 本章重點整理

- context engineering 是決定每次呼叫要放哪些 token、以什麼順序與形式放的工作，目標是能讓模型做對事的最小一組高訊號 token。
- 每個 token 同時付出錢、延遲、注意力三種成本；前兩種會出現在帳單與監控上，注意力的成本只會表現為品質下降。
- context rot 是輸入越長越不可靠的漸進現象，干擾、混淆、衝突、污染四種失敗都來自放得太多、太像、太矛盾或太髒，而不是 window 太小。
- context 依變動頻率分成穩定前綴、半穩定層、動態層，順序由慢到快；越前面的層共用範圍越大，越不能改。
- cache breakpoint 放在每個變動頻率的邊界，最後一個隨對話尾端移動；這樣較快變動的層改變時，不會拖累較慢變動的層。
- tool 定義位於整個前綴的最前面，中途增刪 tool 會讓整段快取失效，也可能讓歷史引用到不存在的 tool；改用固定全集加 dispatch 拒絕、遮罩，或以追加方式加入新定義。
- 大多數 cache 不友善的變更都能用「追加」取代「改寫」；真的必須改寫前綴時要批次化，集中在 compaction 這類反正要重算的時機。
- 在 trace 中記錄每一層的累積指紋，命中率下降時能直接找到第一個改變的區塊。
- 單次呼叫的 token 預算要遠小於 window，並為每一層訂配額與削減順序；輸出保留不能被挪用。
- token 估算用快速粗估加上供應商回報的 usage 校正，寧可高估；換模型時要重新校正。
- 削減時可還原的方式（存檔留 handle）優先於不可還原的方式（摘要）；未配對的 tool 結果與最新的使用者訊息永遠不削。
- just-in-time 載入讓 context 只帶引用、按需讀取內容；小而常用、錯過代價高的內容預載，大而偶爾用到的內容按需載入。
- 檔案系統或任何以路徑定址的儲存可以當外部 context，用於大型結果卸載、筆記與進度檔、中間產物；寫入時就決定大小，才不會事後改寫歷史。
- 外部 context 的內容要視為不可信資料，並依租戶與 session 隔離、去除不需要的個資、設定清除期限。

## 延伸問答

> [!question]- Q1. context engineering、prompt engineering 與 RAG 有什麼不同？為什麼說 agent 特別需要 context engineering？
> prompt engineering 關心的是指令的措辭：同一個要求怎麼說，模型比較會照做。RAG 是一種特定的技術：根據問題檢索相關文件，放進 context 讓模型參考。context engineering 的範圍比兩者都大，它管理的是整個輸入的組成：system prompt、tool 定義、歷史、tool 結果、檢索文件、memory、提醒，以及它們的順序、大小與形式。prompt engineering 是其中一層的內容設計，RAG 是其中一種把外部資訊帶進來的手段。
>
> agent 特別需要它，是因為 agent 的 context 每一步都在變。單次呼叫的應用寫一次 prompt 就固定了；agent 在 loop 中每一步都會追加 tool 結果，二十步之後，context 的大部分內容都不是工程師寫的，而是 tool 產生的。如果沒有規則決定哪些結果要卸載、哪些要保留、新資訊放在哪裡，context 會自然地往「又大又亂、每次都在變」的方向演化，成本、延遲與品質一起惡化。

> [!question]- Q2. 模型已經支援 1M context，為什麼不乾脆把整本手冊與全部訂單都放進去，讓模型自己找？
> 第一個理由是成本與延遲。每一步都要重送全部內容，就算命中 cache，讀取也不是免費，而沒命中的部分要在 prefill 重算，直接拉長 TTFT。一個客服對話做五步，就是把整本手冊送五次。第二個理由是 context rot：研究與實務都觀察到，輸入越長，模型使用其中關鍵資訊的能力越差，而且相似或矛盾的內容會造成混淆與衝突，青鳥的新舊兩版退貨期限就是例子。
>
> 第三個理由是安全與合規：整份訂單紀錄包含地址與電話，放進 context 就會被送到模型、寫進 log，違反最小必要原則。大 window 適合的情況是：任務確實需要同時看到大量內容之間的關係，例如比對兩份長合約的差異。即使那樣，也要先確認內容沒有重複與過時版本。判斷標準不是「放得下嗎」，而是「每一段內容的邊際價值，值得它的三種成本嗎」。

> [!question]- Q3. 你在 production 看到部署後 cache 命中率從 85% 掉到 20%，但沒有人說自己改了 prompt，你會怎麼排查？
> 第一步是確認範圍：依版本號、租戶、對話類型聚合命中率，看是全面下降還是某一類對話。如果只有某一類下降，通常是那類對話觸發了某個條件邏輯，例如中途掛上新 tool。第二步是用分層指紋：抽兩次同一 session 內相鄰的請求，比較每一個區塊的累積指紋，第一個不同的區塊就是斷點所在。如果是 tools 區塊，檢查 tool 清單的順序與集合；如果是 system，檢查是否有人加了時間、版本字串或使用者名稱。
>
> 很多「沒有人改 prompt」的案例，其實是非確定性序列化：例如新版程式從 set 產生 tool 名稱清單，而 Python 的字串雜湊在不同 process 之間會隨機化，每台機器、每次重啟的順序都不同；或者某個 dict 改由不同的程式路徑建立，key 的插入順序變了。第三步是檢查設定：是否有人調了推理強度、切換了模型版本或啟用了新的 beta 功能，這些也會讓快取失效。找到原因後，把那兩次請求寫成一個「指紋必須相同」的單元測試。

> [!question]- Q4. 使用者在對話中途提到優惠券，agent 需要 apply_coupon 才能完成任務。你有哪幾種做法？怎麼選？
> 第一種是從一開始就把 apply_coupon 放在 tool 清單裡，描述寫清楚使用條件，由 harness 的 dispatch 在狀態不允許時拒絕並回填可行動的錯誤。優點是前綴永遠不變、有副作用的動作由程式把關；代價是每次呼叫多帶這個 tool 的定義，tool 數量很多時會累積成可觀的 token。第二種是遮罩：清單不變，只在解碼時限制本輪可選的 tool，需要你自架模型或供應商提供對應參數。第三種是 tool search 或 deferred loading：初始清單不含它，需要時把定義追加到尾端，不動既有前綴。
>
> 最不該選的是第四種，也就是 Iris v1 的做法：中途把 tool 插進清單，整段快取失效，歷史中也可能出現「消失的 tool」。選擇的依據主要是 tool 的數量與使用頻率：少量、常用的 tool 用第一種最簡單也最穩；數十個以上、多數對話用不到的 tool 才值得用第三種；第二種適合自架推理、能控制解碼的團隊。不論哪一種，有副作用的 tool 都要在 dispatch 再檢查一次權限與狀態。

> [!question]- Q5. 估算題：穩定前綴 6,000 tokens，一段對話 20 步，每步新增 500 tokens。若第 10 步之前中途改了 tool 定義，相比完全不改，多付多少輸入成本？（cache read 0.1 倍、cache write 1.25 倍）
> 先算不改的情況。假設穩定前綴已被其他 session 暖好，第 k 步的 input 是 6,000 ＋ 500 × k，其中只有最新的 500 tokens 要寫入，其餘 6,000 ＋ 500 ×（k − 1）都能命中。20 步的命中總量是 20 × 6,000 ＋ 500 ×（0 ＋ 1 ＋ … ＋ 19）＝ 120,000 ＋ 95,000 ＝ 215,000 tokens，寫入總量是 20 × 500 ＝ 10,000 tokens。以 base input 單價為 1 計，成本約 215,000 × 0.1 ＋ 10,000 × 1.25 ＝ 21,500 ＋ 12,500 ＝ 34,000 個單位。
>
> 改 tool 定義的那一步（第 10 步），input 是 6,000 ＋ 5,000 ＝ 11,000 tokens，全部以寫入價計費：11,000 × 1.25 ＝ 13,750；不改時這一步只要 10,500 × 0.1 ＋ 500 × 1.25 ＝ 1,675。差額約 12,000 個單位，超過整段對話原本成本的三分之一，而且這只是改一次；之後的步驟會恢復命中，但這筆錢收不回來。如果條件式 tool 讓每段對話都改兩三次，成本就接近翻倍，這和 9.9 節情境 B 的結果一致。這也說明為什麼「每次多帶一個 tool 定義的幾百 tokens」幾乎總是比中途增刪划算。

> [!question]- Q6. 程式找錯：下面的 context 組裝函式有三個會讓 cache 失效或造成錯誤的問題，請指出來。
> ```python
> def build(user, history, tools: set[str]):
>     system = f"現在時間 {datetime.now()}。顧客 {user.name}，偏好 {user.prefs}。" + RULES
>     schemas = [SCHEMAS[name] for name in tools]
>     return {"tools": schemas, "system": system, "messages": history}
> ```
> 第一個問題是 `datetime.now()` 放在 system 的開頭，精確到微秒，每一次請求的 system 都不同，從 system 起全部無法命中。時間應該放到本輪訊息的尾端，或只精確到日期並放在半穩定層。第二個問題是顧客姓名與偏好也放在 system 裡：這讓 system 變成每位顧客都不同，原本可以跨顧客共用的 RULES 也跟著無法共用；應該把它們移到 RULES 之後的半穩定區塊，並在兩者之間放 breakpoint。
>
> 第三個問題最隱晦：`tools` 是 set，而 Python 的字串雜湊在不同 process 之間預設會隨機化，所以同樣的 tool 集合在不同機器或重啟之後，迭代順序可能不同，產生的 tool 清單順序也就不同。tool 清單位於前綴最前面，這會讓整段請求在不同 worker 之間無法共用快取，而且問題只在多台機器上才出現，本機測試看不到。修法是用固定順序的 list 或 `sorted(tools)`，並用 `sort_keys=True` 序列化每個 schema。

> [!question]- Q7. 面試追問：設計一個多租戶的客服 agent 平台，你會怎麼安排 context 版面，讓 cache 共用最大化，同時不造成租戶之間的資料外洩？
> 版面依共用範圍由大到小排列：最前面是所有租戶共用的 tool 定義與平台 system prompt，放第一個 breakpoint；接著是租戶層級的內容（店家規則、語氣、品牌名稱），放第二個 breakpoint；再來是使用者與 session 層級的內容（memory 摘要），最後是對話。這樣平台層的前綴可以在所有租戶之間命中，租戶層在同一店家的所有對話之間命中。要做到這點，平台層必須完全不含租戶特定的字串，包括店名與客製化的 tool 描述；需要客製化的 tool 行為，用參數或 dispatch 端的設定處理，而不是改 tool 的描述。
>
> 外洩問題要分兩層看。供應商端的 prompt cache 依公開文件不會跨組織共用，而且只有完全相同的前綴才會命中，所以共用平台層不會讓 A 租戶看到 B 租戶的內容；真正的風險在自己這一層：應用層的 tool 結果快取、workspace 與 memory，key 必須包含租戶（需要時再加上使用者）與設定版本，semantic cache 尤其要小心錯誤命中（第 42 章的多租戶不變式）。另外，半穩定層的組裝要從已驗證的 session 身分取得租戶 id，而不是從模型輸出或使用者輸入取得，第 33 章會談多租戶隔離與授權。

> [!question]- Q8. just-in-time 載入讓模型自己決定要不要讀政策，如果它不讀就直接回答，不是更危險嗎？怎麼設計才安全？
> 這是 just-in-time 的真實風險：預載保證模型「看得到」，按需載入只保證模型「拿得到」。所以第一個原則是分級：錯過就會造成嚴重後果的規則，例如退款上限、哪些情況必須轉真人、寫入動作要先確認，不能按需載入，要預載在穩定前綴，而且更重要的是由 harness 在程式中強制，不能只靠模型讀到。按需載入只用在「細節」，例如某一類商品的退貨例外。
>
> 第二個原則是讓「讀」變得容易且可檢查。目錄要寫得讓模型能判斷哪一節相關；system prompt 要求回答政策問題前先讀相關章節；回答中引用了政策內容時，要求附上章節名稱，讓後續的驗證能比對答案是否來自實際讀過的內容。第三個原則是量測：在 eval 中統計「政策類問題中，有讀取政策的比例」與「沒讀卻回答政策細節的比例」，後者就是需要修正的案例。這些檢查會在第 27 章的 trajectory 評估中實作。

## 延伸閱讀

- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
- Manus Blog，Yichao "Peak" Ji〈Context Engineering for AI Agents: Lessons from Building Manus〉（2025）
- Chroma Research〈Context Rot: How Increasing Input Tokens Impacts LLM Performance〉（2025）
- Liu et al.〈Lost in the Middle: How Language Models Use Long Contexts〉（TACL 2024）
- Anthropic Engineering Blog〈Effective harnesses for long-running agents〉（2025）
- Cursor Blog〈Improved token efficiency for longer agent runs〉（2026）
- Drew Breunig〈How Long Contexts Fail〉（2025）
- Anthropic 文件〈Prompt caching〉與〈Context editing〉
