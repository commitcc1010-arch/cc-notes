---
chapter: 3
title: 給 Agent 建造者的 LLM 基礎
part: 0
---

# 第 3 章　給 Agent 建造者的 LLM 基礎

> [!abstract] 本章地圖
> **核心問題**：要設計可上線的 agent，關於 LLM 你到底需要懂到什麼程度，才能算得出成本、延遲，並看懂各家 API 的差異？
>
> **你會學到**：
> - 用 token 的角度思考：tokenizer 怎麼切字、為什麼中文和英文的 token 數不同、agent 的輸入為什麼會隨輪數快速累積
> - 解釋 context window、sampling（temperature、top_p）、reasoning model 與 effort 對 agent 行為與帳單的影響
> - 看懂 function calling 在 messages、items、steps 三種 API 形態下的樣子，並設計一個不會弄丟 provider 欄位的 adapter
> - 分辨 JSON mode、strict schema、structured outputs 的保證層級
> - 說明 prompt caching 的原理（prefix match、TTL、寫入溢價與讀取折扣），並判斷什麼時候會回本
> - 用 Python 寫出 token、成本、延遲估算器與 cache 命中模擬，並讀懂一份 model card
>
> **前置知識**：第 1 章（agent 的定義與光譜）、第 2 章（Model／Harness／Environment 三層心智模型）

## 3.1 故事：一次對話到底要多少錢？

青鳥科技的客服 agent v1 已經有了雛形：Iris 用一個前沿模型接上 `get_order`、`get_shipping`、`refund` 三個 tool，在內部 demo 時順利回答了「我的訂單到哪了」。產品經理阿哲很滿意，接著問了兩個問題：「一次對話要多少錢？使用者要等多久？」Iris 打開供應商的價格頁，看到每百萬 input token 幾美元，心算了一下使用者那句話大概三十個字，得出「一次不到一分錢」的結論。

一週後內部試用的帳單出來，平均每段對話的成本是 Iris 估計的二十幾倍，而且使用者反映「每問一句都要等好幾秒」。staff engineer 老陳拿 trace 一看，指出三件事。第一，每次呼叫模型送出去的不只是使用者那句話，而是 system prompt、二十幾個 tool 定義、整段對話歷史和 tool 回傳的整包 JSON；一段對話呼叫模型七次，每次都重送一遍。第二，Iris 在 system prompt 開頭放了「現在時間：2026-10-02 14:03:27」，精確到秒，讓供應商的 prompt cache 一次都沒命中。第三，模型會先「想」再回答，那些看不見的 thinking token 也照 output 價格計費，而 output 單價通常是 input 的數倍。

老陳最後說：「你不需要會訓練模型，但你要像 DBA 懂 query planner 那樣懂 LLM 的計價與延遲模型。不然你沒辦法做任何架構決策。」本章就是補這一課：從 token 開始，一路講到 context window、sampling、reasoning、function calling、structured outputs、prompt caching 與延遲，最後在動手做裡寫一個估算器，把 Iris 的那段對話算清楚。

## 3.2 Token：模型眼中的最小單位

### 為什麼要從 token 談起

**Token** 是模型讀寫文字的最小單位，可能是一個完整的英文單字、一個字首、一個中文字，或一個位元組片段。例如「refund」常常是一個 token，而「refunds」可能被切成「refund」加「s」兩個。模型的價格、context window 上限、輸出速度、rate limit 全部以 token 計算，所以 agent 建造者的第一個習慣是：看到任何文字，就要能大致估出它有多少 token。

### Tokenizer 怎麼運作

把文字切成 token 的元件叫 **tokenizer**。主流做法是 **BPE**（byte pair encoding，位元組對編碼）及其變體：從單一位元組或字元開始，反覆把語料中最常一起出現的相鄰片段合併成新的詞彙，直到詞表達到預定大小（通常是十萬級）。因為合併規則是從訓練語料統計出來的，常見的字串會被壓成一個 token，罕見的字串則被切成好幾塊。下面用一個迷你 BPE 說明這個現象：

```python
from collections import Counter

# 迷你 BPE：反覆把「最常相鄰出現的一對符號」合併成新符號。
# 真實 tokenizer 用數十億字的語料訓練出十萬級詞表，原理相同。
corpus = ["refund", "refund", "refund", "refunds", "order", "order", "orders", "reorder"] * 50


def train_bpe(words: list[str], n_merges: int) -> list[tuple[str, str]]:
    seqs = Counter(tuple(w) for w in words)
    merges = []
    for _ in range(n_merges):
        pairs = Counter()
        for seq, freq in seqs.items():
            for a, b in zip(seq, seq[1:]):
                pairs[(a, b)] += freq
        if not pairs:
            break
        best = max(pairs, key=lambda p: (pairs[p], p))
        merges.append(best)
        new = Counter()
        for seq, freq in seqs.items():
            out, i = [], 0
            while i < len(seq):
                if i + 1 < len(seq) and (seq[i], seq[i + 1]) == best:
                    out.append(seq[i] + seq[i + 1])
                    i += 2
                else:
                    out.append(seq[i])
                    i += 1
            new[tuple(out)] += freq
        seqs = new
    return merges


def tokenize(word: str, merges: list[tuple[str, str]]) -> list[str]:
    seq = list(word)
    for a, b in merges:  # 依訓練時的順序套用合併規則
        out, i = [], 0
        while i < len(seq):
            if i + 1 < len(seq) and seq[i] == a and seq[i + 1] == b:
                out.append(a + b)
                i += 2
            else:
                out.append(seq[i])
                i += 1
        seq = out
    return seq


merges = train_bpe(corpus, n_merges=10)
for w in ["refund", "orders", "reorder", "rebound", "退款"]:
    toks = tokenize(w, merges)
    print(f"{w:<8} -> {toks}  ({len(toks)} tokens)")

assert tokenize("refund", merges) == ["refund"]          # 常見字被壓成一個 token
assert len(tokenize("rebound", merges)) > 1               # 沒見過的字被切碎
assert tokenize("退款", merges) == ["退", "款"]            # 語料沒有中文，只能逐字
```

```text
refund   -> ['refund']  (1 tokens)
orders   -> ['order', 's']  (2 tokens)
reorder  -> ['re', 'order']  (2 tokens)
rebound  -> ['re', 'b', 'o', 'und']  (4 tokens)
退款       -> ['退', '款']  (2 tokens)
```

輸出的第一行顯示，語料裡出現最多次的「refund」被合併成單一 token。「orders」與「reorder」沿用了已學到的「order」，只多切出字尾或字首。「rebound」從未出現在語料中，只能拆成四塊；「退款」更極端，語料完全沒有中文，只能逐字處理。真實的 tokenizer 是在位元組層級運作，沒學過的字甚至可能被拆成多個位元組 token。這就是為什麼同樣意思的內容，用不同語言、不同 tokenizer 計算，token 數可能差上一截。

### 文字到 token 再到文字的流程

```text
 "我的訂單 BB-1024 到哪了？"
        │ tokenizer（編碼）
        ▼
 [ 我 | 的 | 訂 | 單 | ␣BB | -10 | 24 | 到 | 哪 | 了 | ？ ]  ← 每格是一個 token id
        │ 模型：讀入全部 token，算出「下一個 token」的機率分佈
        ▼
 { 您: 0.41, 親: 0.22, 好: 0.09, ... }   ← logits 經 softmax
        │ sampling（3.4 節）選出一個 token，接回輸入尾端，重複
        ▼
 "您好，訂單 BB-1024 已出貨……"         ← tokenizer（解碼）
```

這張圖從上往下讀。第一步，tokenizer 把字串轉成一串整數 id，圖中的切法只是示意，實際切法依 tokenizer 而定。第二步，模型一次讀完所有輸入 token，對詞表中每個 token 給出分數。第三步，sampling 從分佈中挑出一個 token，把它接到輸入尾端，再預測下一個，這種一次產生一個 token 的方式叫 **autoregressive**（自迴歸）生成。最後 tokenizer 把產生的 id 解碼回文字。理解這個流程有兩個直接的工程意義：輸入可以一次平行處理，輸出只能逐個產生，所以輸出遠比輸入慢；而且輸出的每個 token 都要花一次「前向計算」，所以單價也比較高。

### 估算 token 的實用規則

| 內容類型 | 粗估方式 | 對 agent 的意義 |
|---|---|---|
| 英文散文 | 約每 3–4 個字元一個 token | 英文 system prompt 比較省 |
| 中文 | 依 tokenizer 不同，約每字 1–2 個 token | 中文客服對話的 token 數不能用英文經驗推估 |
| JSON、程式碼 | 括號、引號、縮排都吃 token，常比等量散文多 | tool 回傳的 JSON 是 context 膨脹的主因 |
| 數字、ID、雜湊 | 常被切得很碎 | 訂單號、UUID、時間戳很貴，也容易打斷 cache |
| 圖片、PDF | 依解析度或頁數換算 | 截圖型 agent 的成本主要在這裡（第 16 章） |

這張表只是讓你在白板上估算時有個量級。真正要算準時，用供應商提供的 token 計數 API 或官方 tokenizer，而且要針對你自己的真實資料取樣，因為同一段文字換一代模型的 tokenizer，token 數也可能改變。

> [!warning] 常見誤解
> 「中文一個字就是一個 token」。這只在某些 tokenizer、某些常用字上成立。罕用字、全形標點、混排的英數字都可能讓比例變高。估算成本時要用自己的語料實測，不要套用網路上的換算比例。

## 3.3 Context window：模型唯一的工作記憶

### 為什麼它是 agent 設計的核心約束

**Context window** 是模型單次呼叫能處理的 token 總量上限，輸入與輸出共用這個額度。例如一個 context window 為 200K 的模型，如果你送入 190K token 的輸入，它最多只能再產生 10K token。模型本身沒有記憶，每次呼叫都是「從零讀一遍你送給它的全部內容」，所以 context window 就是 agent 在這一步能「知道」的全部。agent 記得前面查過的訂單，是因為 harness 把前面的 tool 結果一起送進去，而不是模型記住了。

### 一次 agent 呼叫的 context 版面

```text
 ┌──────────────────────── context window ────────────────────────┐
 │ ① tool 定義（名稱、描述、JSON schema）       穩定，幾千 token    │
 │ ② system prompt（角色、政策、輸出規則）       穩定，幾千 token    │
 │ ③ 對話歷史：user / assistant / tool_use / tool_result           │
 │    （含先前 turn 的 thinking 區塊）            每輪成長           │
 │ ④ 本輪新輸入：最新的 user 訊息或 tool_result                     │
 ├────────────────────────────────────────────────────────────────┤
 │ ⑤ 本輪輸出預留：thinking ＋ 文字 ＋ tool call 參數 ≤ max_tokens  │
 └────────────────────────────────────────────────────────────────┘
```

這張版面圖由上而下對應送給模型的順序。①② 幾乎每次呼叫都一樣，是 prompt caching 最好的對象（3.8 節）。③ 隨著 agent 每做一步就變長，是成本與延遲成長的來源，也是第 9、10 章 context engineering 與 compaction 要處理的對象。④ 是這一輪真正的新資訊。⑤ 是輸出預留的空間，由 **max_tokens** 參數控制：它是單次回應的輸出上限，模型寫到上限就會被截斷，回應的 stop_reason 會是 `max_tokens`，tool call 的參數可能只寫了一半。

### 長 context 不等於完美記憶

模型標示的 context window 是「能放得下」，不是「都能同樣專心地用上」。研究與實務都觀察到，當 context 越長、無關內容越多，模型找到並正確使用某條關鍵資訊的能力會下降，業界稱為 **context rot**（第 9 章詳述）。對 agent 來說，這意味著兩件事：不要因為放得下就把整份文件塞進去，以及要把最重要的指令放在穩定、明確的位置。context window 越大，越需要紀律，而不是越不需要。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 的 Claude Fable 5.1、Opus 5.5、Sonnet 5.5 都是 1M token context、128K 最大輸出，Haiku 4.5 為 200K。Anthropic 表示從 Opus 4.7 開始使用新 tokenizer，同樣的文字在新 tokenizer 下 token 數約為舊版的 1 到 1.35 倍。各家模型的 context 與輸出上限可以從模型清單 API 或 model card 查詢，換模型時要重新量測 token 數。

## 3.4 生成與 sampling：同一個問題為什麼答案不同

### 從機率分佈挑出下一個 token

模型每一步輸出的是「下一個 token 的機率分佈」，**sampling**（取樣）是從這個分佈選出實際 token 的規則。最直接的規則是 **greedy decoding**：永遠選機率最高的那個。但 greedy 容易產生重複、呆板的文字，所以 API 提供幾個旋鈕。**temperature** 調整分佈的尖銳程度：低於 1 會放大高分選項的優勢，高於 1 會讓分佈變平。**top_p**（nucleus sampling）只保留累積機率達到 p 的最小候選集合，砍掉長尾。**top_k** 只保留分數最高的 k 個候選。

```python
import math
import random
from collections import Counter

# 模型對「下一個 token」給出的分數（logits）。情境：客服回覆的第一個字。
logits = {"您好": 4.0, "親愛的": 3.0, "嗨": 2.0, "喂": 0.5, "退款": -1.0}


def softmax(scores: dict[str, float], temperature: float) -> dict[str, float]:
    # temperature 越低，分數差距被放大，分佈越尖；越高越平
    t = max(temperature, 1e-6)
    m = max(scores.values())
    exps = {k: math.exp((v - m) / t) for k, v in scores.items()}
    z = sum(exps.values())
    return {k: e / z for k, e in exps.items()}


def top_p_filter(probs: dict[str, float], p: float) -> dict[str, float]:
    # nucleus sampling：只保留累積機率達 p 的最小候選集合，再重新正規化
    kept, total = {}, 0.0
    for tok, pr in sorted(probs.items(), key=lambda kv: -kv[1]):
        kept[tok] = pr
        total += pr
        if total >= p:
            break
    return {k: v / total for k, v in kept.items()}


def sample(probs: dict[str, float], rng: random.Random) -> str:
    r, acc = rng.random(), 0.0
    for tok, pr in probs.items():
        acc += pr
        if r <= acc:
            return tok
    return tok


rng = random.Random(42)
results = {}
for label, t, p in [("T=0.2", 0.2, 1.0), ("T=1.0", 1.0, 1.0), ("T=1.0, top_p=0.9", 1.0, 0.9), ("T=2.0", 2.0, 1.0)]:
    probs = top_p_filter(softmax(logits, t), p)
    counts = Counter(sample(probs, rng) for _ in range(1000))
    results[label] = counts
    print(f"{label:<17}", "  ".join(f"{k}:{counts.get(k, 0):>4}" for k in logits))

assert results["T=0.2"]["您好"] > 950                    # 幾乎是 greedy
assert results["T=1.0, top_p=0.9"]["退款"] == 0          # 長尾被 top_p 砍掉
assert results["T=2.0"]["退款"] > results["T=1.0"]["退款"]  # 高溫讓怪選項變多
```

```text
T=0.2             您好: 988  親愛的:  12  嗨:   0  喂:   0  退款:   0
T=1.0             您好: 650  親愛的: 253  嗨:  76  喂:  17  退款:   4
T=1.0, top_p=0.9  您好: 657  親愛的: 238  嗨: 105  喂:   0  退款:   0
T=2.0             您好: 441  親愛的: 290  嗨: 168  喂:  68  退款:  33
```

每一行是同一組分數在不同設定下抽 1,000 次的結果。T=0.2 時幾乎每次都選「您好」，行為接近 greedy。T=1.0 是模型原本的分佈，偶爾會出現「退款」這種完全不合語境的開頭。加上 top_p=0.9 之後，「喂」和「退款」被砍掉，多樣性保留在合理範圍內。T=2.0 讓長尾選項大幅增加，33 次以「退款」開頭的回覆在客服情境裡就是事故。對 agent 而言，每一步的小機率怪選擇會在多步之後累積成軌跡偏離，所以需要穩定行為的步驟通常用低溫或供應商預設值，而不是調高溫度來「增加創意」。

### Sampling 參數對照

| 參數 | 作用 | agent 的常見設定 | 常見誤解 |
|---|---|---|---|
| temperature | 調整分佈尖銳度 | 依供應商預設；工具決策偏低 | 「設 0 就完全可重現」：伺服器端的批次與數值誤差仍可能造成差異 |
| top_p | 砍掉累積機率以外的長尾 | 通常和 temperature 擇一調整 | 兩個同時大幅調整，效果難以預測 |
| top_k | 只保留前 k 名 | 很少需要動 | 對推理模型常不開放 |
| seed | 讓取樣可重現（部分 API 提供） | eval 重跑時有用 | 不保證跨模型版本一致 |
| max_tokens | 單次輸出上限 | 留足 thinking 與 tool 參數空間 | 設太小會讓 tool call 被截斷 |

這張表最需要記住的是最後一欄。agent 的可重現性主要靠 harness 層面的設計（記錄完整 trajectory、用 ScriptedModel 重播、對 tool 結果做快照），而不是靠 temperature=0。第 27 章的 eval 會再談為什麼同一題要跑多次並看 pass^k。

> [!note] 2026 現況
> 截至 2026 年 10 月，推理模型逐漸收回 sampling 參數的控制權：部分新模型不再接受手動調整 temperature、top_p、top_k，改用 effort 控制行為。哪些模型、送出時是被忽略還是回錯誤，各家與各代模型不同，本書未逐一查證，請以官方模型文件為準。寫 adapter 時不要假設每個模型都接受這些參數。

## 3.5 Reasoning models 與 effort

### 什麼是 reasoning model

**Reasoning model**（推理模型）是被訓練成「先產生一段內部推理，再給出答案或動作」的模型。那段推理叫 **thinking**（也稱 reasoning tokens），例如模型在決定要不要退款前，先在 thinking 中比對訂單日期與七天鑑賞期。thinking 對使用者通常不可見，或只提供摘要，但它是真實產生的輸出 token，照 output 單價計費，也佔用輸出時間。對 agent 來說，推理模型的價值在於：它能在每次 tool 結果回來之後重新思考，而不是一開始就把計畫寫死。

### Interleaved thinking：在 tool 之間思考

```text
 Harness                     Model                          Tools
   │  user: 退款 BB-1024        │                               │
   │──────────────────────────►│ thinking: 先查訂單狀態          │
   │◄──────────────────────────│ tool_use get_order             │
   │──────────── get_order ──────────────────────────────────►│
   │◄─────────── {status: delivered, day: 9} ─────────────────│
   │  tool_result ────────────►│ thinking: 已過七天，需查例外政策 │
   │◄──────────────────────────│ tool_use search_kb             │
   │──────────── search_kb ──────────────────────────────────►│
   │◄─────────── 瑕疵品不受七天限制 ───────────────────────────│
   │  tool_result ────────────►│ thinking: 問使用者是否瑕疵      │
   │◄──────────────────────────│ text: 請問商品是否有瑕疵？       │
```

這張時序圖由上往下是時間。每次 tool_result 回到模型，模型都先產生一段 thinking 再決定下一步，這種模式叫 **interleaved thinking**（交錯式思考）。第一段 thinking 決定先查訂單；第二段看到「已過七天」後改變方向去查例外政策；第三段決定把問題丟回給使用者，而不是直接拒絕。如果模型只在一開始想一次，第二步的轉向就不會發生。工程上要注意兩點：thinking 區塊是 assistant 回應的一部分，harness 回填歷史時要原樣保留；以及每段 thinking 都是 output token，步數越多，花費越高。

### Effort：品質、成本與延遲的主旋鈕

早期 API 讓你直接設定「最多想幾個 token」的 thinking budget，後來主流方向轉成 **adaptive thinking**（模型自己決定想不想、想多少）加上 **effort** 參數。effort 是一個等級（例如 low、medium、high），影響的不只是 thinking 長度，而是所有輸出：低 effort 時模型傾向少說明、把多個動作合併成較少的 tool call、直接行動；高 effort 時會做更多 tool call、先講計畫、檢查得更仔細。

| 工作類型 | 建議起點 | 理由 |
|---|---|---|
| 分類、路由、簡單抽取 | 低 | 不需要多步推理，延遲敏感 |
| 互動式客服回覆 | 低到中 | 使用者在等；多數問題是查詢型 |
| 多步 tool use、退款判斷 | 中到高 | 需要在 tool 之間修正方向 |
| 長時間 coding、研究任務 | 高或更高 | 正確性比延遲重要，任務價值高 |
| 平行 subagent 的子任務 | 低 | 由 orchestrator 負責整體判斷（第 20 章） |

這張表是起點，不是定論。effort 是「每個任務的成本」與「成功率」的取捨，正確做法是在自己的 eval 上掃過幾個等級，看每次**成功**任務的成本，而不是單次請求的成本。一個較便宜但需要多跑兩輪才完成的設定，最後不一定比較便宜。

> [!warning] 常見誤解
> 「為了省錢，把歷史中舊的 thinking 區塊刪掉」。對會保留先前 thinking 的模型，刪掉會讓推理失去連續性，也會改變 prompt 前綴而造成 cache miss。是否保留、保留幾輪，要用供應商提供的機制（例如 context editing）處理，而不是在 harness 裡自己改寫歷史。

> [!note] 2026 現況
> 截至 2026 年 10 月：Anthropic 的手動 thinking budget（`budget_tokens`）在 4.6 世代 deprecated，4.7 以後的模型改用 adaptive thinking 加 `output_config.effort`（`low`／`medium`／`high`／`xhigh`／`max`）。Opus 5.5 的 thinking 無法關閉，預設 effort 為 `medium`；其他多數現役模型預設 `high`。Sonnet 5.5 提供 `thinking: {type: "between_tools"}`，不做前置思考、只在 tool 之間思考。中途改 top-level effort 會讓 prompt cache 失效，Anthropic 另提供 beta 的 per-message effort 切換以保留 cache。Anthropic 2026-04-23 的 postmortem 也記錄了一次教訓：Claude Code 把預設 effort 從 high 降到 medium 以降低延遲，使用者明顯感覺品質下降，之後回滾。OpenAI 的推理模型以 reasoning items 表示推理內容，可帶 `encrypted_content` 跨輪傳遞（此細節未經本書網路查證）。

## 3.6 Function calling：三種 API 形態

### 模型不會執行 tool

**Function calling**（也叫 tool use）是讓模型輸出「我想呼叫哪個 tool、參數是什麼」的結構化請求，再由你的程式真正執行。模型本身不會連到你的資料庫，它只產生一段符合 schema 的 JSON；執行、權限檢查、錯誤處理、把結果送回去，全是 harness 的工作（第 4 章實作）。12-Factor Agents 的說法很精準：tool 就是 structured output，由確定性的程式碼決定怎麼處理。

### 三種形態

各家 API 在「歷史怎麼表示」上走向了三種形態。**Messages 形態**以 role 為單位（user、assistant），一則 assistant 訊息裡可以包含多個內容區塊，例如 text、thinking、tool_use；tool 結果則放在下一則 user 訊息的 tool_result 區塊裡。**Items 形態**把歷史攤平成一串型別各異的 item，例如 message、reasoning、function_call、function_call_output，每個 item 都是一等公民。**Steps 形態**把一次互動拆成 steps，例如 thought、function_call、function_result、model_output、user_input。三者表達的是同一件事，差別在資料結構與誰保存狀態。

```text
 Messages 形態                  Items 形態                     Steps 形態
 ─────────────                  ──────────                     ──────────
 user: 訂單到哪了？              message(user)                  user_input
 assistant:                     reasoning(encrypted)           thought
   [thinking]                   function_call                  function_call
   [tool_use id=t1]               call_id=c1, args="{...}"       name, args
 user:                          function_call_output           function_result
   [tool_result t1]               call_id=c1, output           model_output
 assistant: [text]              message(assistant)
 ── client 每次送完整歷史 ──     ── 可用 previous_response_id ── ── 可用 previous_interaction_id ──
                                   交給伺服器保存                   交給伺服器保存
```

這張對照圖三欄由上往下都是同一段對話。左欄的 tool_use 與 tool_result 以 id 配對，並寄生在 assistant／user 訊息裡。中欄每個 function_call 是獨立 item，以 call_id 配對，而且 arguments 是 JSON 字串，需要自己 parse。右欄把思考、呼叫、結果都變成 step。最底下一列是最大的架構差異：後兩種形態都提供伺服器端狀態，你可以只送「上一次回應的 id」加上新的 item，不必每次重送全部歷史；但這也表示 trace、稽核與 replay 要依賴供應商保存的資料，第 22 章的 durable execution 與第 25 章的 adapter 設計都要考慮這點。

| 面向 | Messages（Anthropic） | Items（OpenAI Responses） | Steps（Gemini Interactions） |
|---|---|---|---|
| tool 定義 | `name`、`description`、`input_schema`，可加 `strict` | `type: "function"`、`name`、`description`、`parameters`，可加 `strict` | `type: "function"`、`name`、`description`、`parameters` |
| 模型要求呼叫 | `stop_reason: "tool_use"` 加 `tool_use` 區塊 | `function_call` item（`call_id`、`arguments` 字串） | `function_call` step |
| 回傳結果 | user 訊息中的 `tool_result`（`tool_use_id`，可帶 `is_error`） | `function_call_output` item | `function_result` step |
| schema 保證 | `strict: true` | `strict: true` | `tool_choice` 的 `validated` 模式 |
| 伺服器端狀態 | 無（client 送完整歷史） | `previous_response_id` 或 Conversations | `previous_interaction_id` |
| 不透明欄位 | thinking 區塊與簽章 | reasoning item | thought signatures |

這張表的欄位名稱依各家公開文件整理。設計 adapter 時最容易出錯的是最後一列：這些不透明欄位你看不懂也不該修改，但必須原樣保存並在下一輪送回，否則多輪 tool use 會失去推理連續性，甚至直接報錯。

### 真實 SDK 長什麼樣

下面兩段程式依 2026-10 的 SDK 介面撰寫，請以官方文件為準；它們需要網路與 API key，所以標記為不可執行。`MODEL_ID`、`SYSTEM_PROMPT`、`run_tool` 是你自己的設定與函式。第一段是 Anthropic Messages API：

```python
# not-runnable
import anthropic

client = anthropic.Anthropic()
tools = [{
    "name": "get_order",
    "description": "依訂單編號查詢訂單狀態、品項與金額。",
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
        "additionalProperties": False,
    },
    "strict": True,
}]
messages = [{"role": "user", "content": "我的訂單 BB-1024 到哪了？"}]
resp = client.messages.create(
    model=MODEL_ID,
    max_tokens=16000,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    tools=tools,
    messages=messages,
    output_config={"effort": "medium"},
)
if resp.stop_reason == "tool_use":
    messages.append({"role": "assistant", "content": resp.content})   # 整包原樣回填，含 thinking
    results = [{"type": "tool_result", "tool_use_id": b.id, "content": run_tool(b.name, b.input)}
               for b in resp.content if b.type == "tool_use"]
    messages.append({"role": "user", "content": results})              # 所有結果放在同一則訊息
print(resp.usage.input_tokens, resp.usage.output_tokens,
      resp.usage.cache_read_input_tokens, resp.usage.cache_creation_input_tokens)
```

第二段是 OpenAI Responses API，用 `previous_response_id` 讓伺服器保存歷史：

```python
# not-runnable
import json
from openai import OpenAI

client = OpenAI()
tools = [{
    "type": "function",
    "name": "get_order",
    "description": "依訂單編號查詢訂單狀態、品項與金額。",
    "parameters": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
        "additionalProperties": False,
    },
    "strict": True,
}]
resp = client.responses.create(model=MODEL_ID, tools=tools,
                               input=[{"role": "user", "content": "我的訂單 BB-1024 到哪了？"}])
outputs = []
for item in resp.output:
    if item.type == "function_call":
        args = json.loads(item.arguments)            # arguments 是 JSON 字串
        outputs.append({"type": "function_call_output", "call_id": item.call_id,
                        "output": run_tool(item.name, args)})
if outputs:
    resp = client.responses.create(model=MODEL_ID, tools=tools,
                                   previous_response_id=resp.id, input=outputs)
```

比較兩段可以看出幾個實務差異。Anthropic 版本把 cache 斷點、effort 都寫在請求裡，而且 tool 結果必須放在同一則 user 訊息；如果把平行呼叫的結果拆成多則訊息，會在無形中讓模型學到「不要平行呼叫」。OpenAI 版本用伺服器端狀態，所以第二次請求只送新的 item，但 `tools` 仍要每次帶上。Gemini 的 Interactions API 同樣有伺服器端狀態，官方說明只有對話歷史會延續，tools、system instruction 與生成設定每次都要重新傳。

### 統一抽象：把三種形態收斂成 ToolCall

既然形態不同，自己的 harness 就需要一層 adapter，把各家回應轉成全書統一的 `ToolCall{id, name, args}`，同時保留原始區塊。下面用 dict 模擬兩家回應的形狀：

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# 全書統一的 ToolCall：上層 loop 只認得這個形狀
@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw: list[dict] = field(default_factory=list)   # 保留 provider 原始區塊（thinking、簽章等）


# 兩家 API 回傳的「形狀」（簡化成 dict；欄位名稱依各家公開文件）
anthropic_like = {
    "stop_reason": "tool_use",
    "content": [
        {"type": "thinking", "thinking": "", "signature": "opaque-abc"},
        {"type": "text", "text": "我先查一下訂單。"},
        {"type": "tool_use", "id": "toolu_1", "name": "get_order", "input": {"order_id": "BB-1024"}},
    ],
    "usage": {"input_tokens": 1200, "output_tokens": 85},
}
openai_like = {
    "status": "completed",
    "output": [
        {"type": "reasoning", "encrypted_content": "opaque-xyz"},
        {"type": "function_call", "call_id": "call_1", "name": "get_order",
         "arguments": "{\"order_id\": \"BB-1024\"}"},   # 注意：arguments 是 JSON 字串
    ],
    "usage": {"input_tokens": 1180, "output_tokens": 90},
}


def from_anthropic(resp: dict) -> ModelResponse:
    blocks = resp["content"]
    calls = [ToolCall(b["id"], b["name"], b["input"]) for b in blocks if b["type"] == "tool_use"]
    text = "".join(b["text"] for b in blocks if b["type"] == "text")
    return ModelResponse(text, calls, resp["stop_reason"], dict(resp["usage"]), raw=blocks)


def from_openai(resp: dict) -> ModelResponse:
    items = resp["output"]
    calls = [ToolCall(i["call_id"], i["name"], json.loads(i["arguments"]))
             for i in items if i["type"] == "function_call"]
    text = "".join(c["text"] for i in items if i["type"] == "message" for c in i.get("content", []))
    stop = "tool_use" if calls else "end_turn"   # Responses 沒有 stop_reason，要自己推導
    return ModelResponse(text, calls, stop, dict(resp["usage"]), raw=items)


def tool_result_for(provider: str, call: ToolCall, content: str) -> dict:
    # 回填格式也不同：Anthropic 放在 user 訊息的 tool_result 區塊；OpenAI 是獨立的 item
    if provider == "anthropic":
        return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "content": content}]}
    return {"type": "function_call_output", "call_id": call.id, "output": content}


a, o = from_anthropic(anthropic_like), from_openai(openai_like)
for name, r in [("anthropic", a), ("openai", o)]:
    c = r.tool_calls[0]
    print(f"{name:<9} stop={r.stop_reason:<8} call={c.name}({c.args}) raw_blocks={len(r.raw)}")
    print("          回填:", json.dumps(tool_result_for(name, c, '{"status": "shipped"}'), ensure_ascii=False))

assert a.tool_calls[0].args == o.tool_calls[0].args == {"order_id": "BB-1024"}
assert a.stop_reason == o.stop_reason == "tool_use"
assert any(b["type"] == "thinking" for b in a.raw)   # 不透明欄位要原樣保留，下一輪送回
```

```text
anthropic stop=tool_use call=get_order({'order_id': 'BB-1024'}) raw_blocks=3
          回填: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "{\"status\": \"shipped\"}"}]}
openai    stop=tool_use call=get_order({'order_id': 'BB-1024'}) raw_blocks=2
          回填: {"type": "function_call_output", "call_id": "call_1", "output": "{\"status\": \"shipped\"}"}
```

輸出前兩行說明，兩種形狀被轉成同一個 `ToolCall`，參數也都還原成 dict，上層的 agent loop 從此不必知道背後是哪一家。注意 `stop=tool_use` 在 OpenAI 那邊是 adapter 自己推導的，因為 Responses 的回應以 status 與 item 型別表達結果，沒有完全相同的 stop_reason 欄位。`raw_blocks` 數字顯示 thinking 與 reasoning item 都被保留下來。回填那兩行則提醒你，送回結果時要轉回各家的格式。第 25 章會把這段擴充成完整的 provider adapter，加入 streaming、錯誤分類與 fallback。

> [!note] 2026 現況
> 截至 2026 年 10 月：OpenAI Assistants API 已於 2026-08-26 停止服務，改用 Responses 加 Conversations；Gemini Interactions API 在 2026-06 GA 並被官方建議用於新專案，`generateContent` 標為 legacy 但仍完整支援。Anthropic 的 `tool_choice` 有 `auto`、`any`、`tool`、`none` 四種，但部分新模型對強制 tool（`any`／`tool`）有限制（本書未逐一查證各模型的支援情況），需要固定結構時建議優先用 `strict: true` 或 structured outputs。Anthropic 文件也列出 tool use 本身會帶來一段固定的 system prompt token 成本（例如 Opus 5.5／Sonnet 5.5 為 286 tokens）。

## 3.7 Structured outputs：保證到哪一層

### 為什麼需要

agent 系統有很多地方需要機器可讀的輸出：tool call 的參數、路由決策（「這張工單屬於退款還是物流」）、交給下游程式的抽取結果。如果只在 prompt 裡寫「請輸出 JSON」，模型多數時候會照做，但偶爾多一段前言、少一個括號、或把 enum 寫成同義詞，這種低機率錯誤在每天數萬次呼叫下一定會發生。

### 三個保證層級

| 機制 | 保證什麼 | 不保證什麼 | 典型用途 |
|---|---|---|---|
| prompt 指示 | 什麼都不保證 | 格式、欄位、型別 | 原型階段 |
| JSON mode | 輸出是合法 JSON | 欄位是否齊全、型別是否正確 | 結構簡單的輸出 |
| strict schema／structured outputs | 輸出符合你提供的 JSON schema | 內容是否**正確**（日期合理、金額對得上） | tool 參數、抽取、路由 |
| tool 當輸出 | 透過 tool schema 取得結構化結果 | 模型可能選擇不呼叫 | 舊 API 上的替代做法 |

strict schema 的原理是 **constrained decoding**（受限解碼）：在 sampling 的每一步，把會讓輸出違反 schema 的 token 機率設成零。例如 schema 規定 `status` 只能是 `"shipped"` 或 `"pending"`，那麼在寫到這個欄位時，任何其他字串的開頭都不會被選中。這個機制解決的是「形狀」問題，不是「內容」問題：模型仍可能填一個格式正確但根本不存在的訂單號。所以驗證邏輯（金額上限、日期範圍、ID 是否存在）仍要在程式裡做，第 7 章會實作驗證與修復迴圈。

```text
 schema: {"status": enum["shipped","pending"], "eta_days": integer}

 已輸出：{"status": "          下一步候選       受限解碼後
                               s   0.52   ──►   s   0.83   ✓ 可能走向 shipped
                               p   0.11   ──►   p   0.17   ✓ 可能走向 pending
                               d   0.30   ──►   d   0      ✗ delivered 不在 enum
                               已  0.07   ──►   已  0      ✗ 中文不在 enum
```

這張資料流圖顯示受限解碼的一步。模型原本給「d」（delivered）相當高的機率，但 schema 不允許，所以被歸零，剩下的候選重新正規化。這也解釋了兩個實務現象：第一次使用新 schema 時，供應商可能需要額外時間把 schema 編譯成解碼約束；schema 寫得越緊，模型越不可能「說出 schema 外的真話」，所以 enum 要涵蓋真實情況，或保留 `other` 加說明欄位。

> [!warning] 常見誤解
> 「用了 structured outputs 就不必驗證」。schema 保證的是語法，不是語意。另一個常被忽略的情況是拒答與截斷：模型因安全理由拒答，或撞到 max_tokens，回應可能不是你預期的物件，程式要先檢查 stop_reason 或 status 再解析。

> [!note] 2026 現況
> 截至 2026 年 10 月：OpenAI Responses 用 `text: {format: {type: "json_schema", name, schema, strict: true}}`，所有 object 需 `additionalProperties: false`、所有欄位列入 `required`，optional 欄位以可為 null 的型別表示，拒答以 `refusal` 類型回傳。Anthropic 提供 JSON schema 形式的 structured outputs（確切參數名稱與 GA 狀態本書未經網路查證，請以官方文件為準），tool 參數則用 `strict: true`。Gemini 以 `tool_choice` 的 `validated` 模式保證 function call 符合 schema，legacy 介面用 `responseMimeType` 加 `responseSchema`／`responseJsonSchema`。

## 3.8 Prompt caching：原理與計價

### 為什麼 agent 特別需要它

回到 3.3 節的版面圖：每次呼叫，①② 和大部分的 ③ 都和上一次一模一樣。模型處理輸入時，會為每個 token 算出一組中間結果，稱為 **KV cache**（key-value cache，注意力機制要用的鍵值向量）。如果這次請求的開頭和上次完全相同，供應商就可以直接拿上次算好的 KV cache 接著算，不必重新處理那一段。這就是 **prompt caching**：對重複的前綴收較低的價格，並縮短首字延遲。agent 每一步都重送幾乎相同的歷史，所以 cache 命中率幾乎直接決定成本。Manus 在 2025 年的公開文章中就把 KV-cache 命中率稱為 production agent 最重要的單一指標。

### Prefix match 怎麼運作

```text
 請求 #1： [tools][system][user1]                     → 全部寫入 cache
 請求 #2： [tools][system][user1][tool_use][result]   → 前三段命中，後兩段寫入
 請求 #3： [tools][system'][user1][tool_use][result]  → system 改了一個字
              ▲      ▲
              │      └─ 從這裡開始全部 miss：之後的歷史即使一模一樣也要重算
              └─ 只有 tools 命中

 cache 規則：
   命中條件 = 從第一個 token 起逐位元組相同的「前綴」
   有效期間 = TTL（例如 5 分鐘），每次命中會刷新
   breakpoint = 你標記「到這裡為止請 cache」的位置（依供應商而定，可能自動）
```

這張圖由上往下是同一段對話的三次請求。請求 #2 是理想情況：前綴沒變，只有新增的部分要付全價。請求 #3 示範最常見的失敗：system prompt 裡任何一個位元組改變（Iris 的時間戳、隨機排序的 tool 列表、每次重新序列化而 key 順序不同的 JSON），從那個位置之後全部失效，即使後面幾千 token 的歷史完全相同。因為比對的是前綴，順序就是一切：穩定的內容放前面，會變的內容放後面，而且歷史只能 append，不能回頭修改。

### 計價模型

prompt caching 的計價通常有三個價格：**cache write**（第一次寫入，常比一般輸入貴一些）、**cache read**（命中時，遠比一般輸入便宜）、以及沒有使用 cache 的一般輸入價。下面用 base input 單價等於 1.0，算一個前綴被 N 次請求共用時的輸入成本：

```python
# 同一個前綴被 N 次請求共用時，不同快取策略的「輸入成本倍數」
# （以未快取的 base input 單價 = 1.0 計；寫入溢價與讀取折扣用常見的計價結構示意）
WRITE_5M, WRITE_1H, READ = 1.25, 2.0, 0.10


def cost(n_requests: int, write_mult: float | None) -> float:
    if write_mult is None:                     # 不用快取：每次都全價
        return n_requests * 1.0
    return write_mult + (n_requests - 1) * READ   # 第一次寫入，其餘讀取


print(" N  無快取   5 分鐘 TTL   1 小時 TTL")
rows = {}
for n in [1, 2, 3, 5, 10, 50]:
    rows[n] = (cost(n, None), cost(n, WRITE_5M), cost(n, WRITE_1H))
    print(f"{n:>2}  {rows[n][0]:>6.2f}   {rows[n][1]:>9.2f}   {rows[n][2]:>9.2f}")

assert rows[1][1] > rows[1][0]          # 只用一次：快取反而更貴
assert rows[2][1] < rows[2][0]          # 5 分鐘 TTL：第二次就回本
assert rows[2][2] > rows[2][0] and rows[3][2] < rows[3][0]   # 1 小時 TTL：要第三次才回本
```

```text
 N  無快取   5 分鐘 TTL   1 小時 TTL
 1    1.00        1.25        2.00
 2    2.00        1.35        2.10
 3    3.00        1.45        2.20
 5    5.00        1.65        2.40
10   10.00        2.15        2.90
50   50.00        6.15        6.90
```

第一列說明，只用一次的前綴標記 cache 反而多付 25% 到 100%，所以每次都不同的內容不該放在 breakpoint 之前。第二、三列是回本點：短 TTL 的寫入溢價低，第二次請求就回本；長 TTL 寫入較貴，要第三次。最後兩列是 agent 的日常：一段 50 步的 coding 任務，共用前綴的輸入成本可以降到約八分之一。選 TTL 的依據是「共用同一前綴的兩次請求，開始時間相隔多久」：agent loop 每一步通常在幾秒到幾十秒內接續，短 TTL 就夠；使用者可能隔二十分鐘才回覆的對話，或在背景跑很久的步驟，才值得付長 TTL 的溢價。

### 讓 cache 失效的常見原因

| 失效原因 | 例子 | 修法 |
|---|---|---|
| 前綴放了會變的值 | system prompt 開頭的時間戳、request id | 移到最後一則訊息，或只精確到日 |
| tool 列表不穩定 | 依使用者動態增減 tool、每次順序不同 | 固定集合與順序；需要時用 tool search（第 13 章） |
| 非確定性序列化 | dict 轉 JSON 時 key 順序不同 | `sort_keys=True` 或固定欄位順序 |
| 改寫歷史 | 回頭修改或刪除舊的 tool_result、thinking | append-only；用供應商的 context editing |
| 切換設定 | 中途換模型、改 top-level effort 或 thinking 設定 | 固定設定；cache 是依模型分開的 |
| 間隔超過 TTL | 使用者隔很久才回覆 | 評估長 TTL 或接受 miss |
| 前綴太短 | 低於供應商的最小可快取長度 | 合併穩定內容，或放棄 cache |

最後要養成的習慣是：**用回應中的 usage 欄位驗證，而不是假設**。每次呼叫都把 cache read 與 cache write 的 token 數記到 trace（第 29 章），如果一段多輪對話的 cache read 一直是零，就表示前綴某處在變。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 的 cache write 價格長期是 base input 的 1.25 倍（5 分鐘 TTL）或 2 倍（1 小時 TTL）（本書撰寫時未重新查證寫入倍數），cache read 一般為 0.1 倍，但 Opus 5.5 為 0.05 倍、Fable 5.1 為 0.025 倍。breakpoint 數量上限、是否提供自動 caching、最小可快取前綴長度（太短會靜默地不快取）都依模型與 API 而定，本書未逐一查證，請以官方文件為準。Cursor 在 2026-09 的文章提到，在 GPT-5.6 的顯式 cache breakpoint 之後放會變動的內容，讓 cold cache miss 降低約 20%。Gemini Interactions API 目前尚未支援 explicit caching。

## 3.9 延遲模型：TTFT、tokens/s 與 agent 的時間線

### 一次呼叫的兩個階段

模型處理一次請求分成兩個階段。**Prefill**：把所有輸入 token 一次平行算完，建立 KV cache。**Decode**：一次產生一個輸出 token。使用者感受到的第一個指標是 **TTFT**（time to first token，首字延遲），它主要由排隊、網路與 prefill 決定，輸入越長、cache 命中越少，TTFT 越長。第二個指標是 **tokens/s**（輸出速度），決定 decode 階段要多久。一次呼叫的總時間可以近似成：

```text
 總時間 ≈ 固定開銷 ＋ 未命中輸入 ÷ prefill 速度 ＋ 命中輸入 ÷ cached 速度 ＋ 輸出 token ÷ tokens/s
```

這條公式的重點在最後一項。prefill 每秒可以處理數千到上萬 token，decode 通常只有每秒數十到數百 token，差距一到兩個數量級。所以多 1,000 個輸入 token 可能只多零點幾秒，多 1,000 個輸出 token（包含看不見的 thinking）卻可能多十幾秒。想讓 agent 變快，先砍輸出與步數，再談輸入。

### Agent 的時間線

```text
 時間 ─────────────────────────────────────────────────────────────────►
 使用者送出
 │
 ├─[ttft 0.5s]─[thinking 3s]─[tool_use 0.5s]─┐                呼叫 #1
 │                                           ├─[get_order 0.8s]
 ├───────────────────────────────────────────┴─[ttft 0.4s]─[thinking 2s]─[tool_use]─┐  呼叫 #2
 │                                                                       ├─[get_shipping 1.2s]
 ├───────────────────────────────────────────────────────────────────────┴─[ttft]─[回覆 2.5s]  呼叫 #3
 │                                                                                    ▲
 └──── 使用者看到第一個字：若不串流中間進度，要等到這裡（約 12 秒）──────────────────┘
```

這張時間線把一個三步的客服回合攤開。每次模型呼叫都要付一次 TTFT 加 decode，再加上 tool 本身的延遲，三者依序串起來。Iris 的使用者說「要等好幾秒」，原因不是模型慢，而是三次串行的呼叫加總。改善方式依效果大小大致是：減少步數（把兩個 tool 合併成一個 workflow 級 tool，第 5 章）、平行呼叫互不相依的唯讀 tool（第 24 章）、降低 effort 讓 thinking 變短、提高 cache 命中以縮短 TTFT，最後是用 **streaming**（串流）把中間進度與最終回覆逐字送給使用者，讓體感延遲接近第一次 TTFT。

### 同步與背景的延遲預算不同

互動式客服的延遲預算可能是「幾秒內看到第一個字、二十秒內完成」，背景 coding agent 則可能是「一小時內交出 PR」。兩者的最佳設定完全不同：前者用低 effort、少步數、積極串流；後者寧可用高 effort 換成功率，延遲反而不是主要指標。設計時先寫下延遲預算，再回推步數上限、每步 effort 與是否需要較小的快速模型。

> [!note] 2026 現況
> 截至 2026 年 10 月，部分供應商提供「同模型、較高輸出速度、較高價格」的選項（例如 Anthropic 的 fast mode，倍率與適用模型本書未經網路查證）。這類選項通常屬於請求設定的一部分，中途切換很可能讓 prompt cache 失效，採用前要確認計價與 cache 行為。各家實際的 TTFT 與 tokens/s 會隨負載與區域變動，要以自己的量測為準。

## 3.10 成本模型：從單次請求到每次成功任務

### Agent 的輸入為什麼會快速累積

一般聊天應用，一次問答呼叫一次模型。agent 則在一個 session 內呼叫模型 k 次，而且第 i 次呼叫的輸入包含前面所有步驟的結果。假設固定前綴（tool 定義加 system prompt）是 P 個 token，每一步新增 d 個 token，第 i 次呼叫的輸入就是 P＋d×(i−1)，把 i 從 1 加到 k，總輸入是 k×P＋d×(0＋1＋…＋(k−1))＝k×P＋d×k(k−1)/2。前一項隨步數線性成長，後一項隨步數平方成長（k 大時約為 d×k²/2）。本書之後的估算都沿用這組記號：k 是每 session 的模型呼叫次數、P 是固定前綴、d 是每步新增的 token，再加上 **h**（cache 命中率，也就是輸入中以 cache read 計價的比例）。這就是 Iris 估算錯了二十幾倍的原因：Iris 只算了使用者那句話，忽略了 P 被重送 k 次，也忽略了歷史的平方項。

### 完整的成本公式

把 cache 與 output 都放進來，一段 session 的模型成本可以寫成：

```text
 成本 = Σ 每次呼叫 [ cache_read × 輸入價 × 讀取倍數
                    ＋ cache_write × 輸入價 × 寫入倍數
                    ＋ 未快取輸入 × 輸入價
                    ＋ 輸出（含 thinking）× 輸出價 ]
       ＋ tool 與 sandbox 的外部成本（搜尋 API、執行秒數）

 每次成功任務成本 = 總成本 ÷ 成功完成的任務數
```

第一行到第四行對應 API 回應 usage 裡的四個數字，所以成本應該在每次呼叫時就用當時的價格表算好並寫進 trace，而不是月底再回推，因為價格表會變。第五行常被忽略：一個每步都要呼叫付費搜尋 API 的 research agent，tool 成本可能超過模型成本。最後一行是做決策時真正該看的指標：一個每次便宜三成、但成功率從九成掉到六成的設定，換算成每次成功任務反而更貴。

## 3.11 模型選擇與 model card 怎麼讀

### 為什麼要會讀 model card

**Model card** 是模型供應商發佈的模型說明文件，通常包含能力、限制、評測結果、安全測試與已知問題。對 agent 建造者來說，它和 API 文件的模型清單一起，是做模型選擇時的第一手資料。但 model card 是行銷與技術的混合體，benchmark 分數告訴你模型在**別人的任務**上的表現，你的客服退款流程不在其中。所以讀 model card 的目的是篩選候選、找出限制，最後用自己的 eval 決定（第 27、28 章）。

| 欄位 | 要回答的問題 | 對青鳥客服 agent 的意義 |
|---|---|---|
| context window／最大輸出 | 放得下最長的 session 嗎？輸出夠寫完 thinking 加回覆嗎？ | 決定何時需要 compaction |
| 價格（input、output、cache） | 每次成功任務多少錢？ | 代入 3.10 節的公式 |
| thinking／effort 控制方式 | 能不能關、預設等級是什麼？ | 影響延遲與 adapter 參數 |
| tool use 支援與限制 | 支援平行呼叫、strict、強制 tool 嗎？ | 影響 harness 寫法 |
| 知識截止日 | 模型「知道」到哪一天？ | 政策與商品資訊必須由 tool 提供 |
| 多模態 | 能讀截圖、PDF 嗎？ | 使用者上傳的破損照片 |
| 安全與拒答行為 | 哪些類別可能被拒？回應長什麼樣？ | 要處理拒答 stop_reason |
| 資料保留與部署地區 | 能否零資料保留？資料在哪處理？ | 法遵與多租戶要求（第 33 章） |
| 生命週期 | 何時 deprecated、retire？ | 規劃遷移與回歸 eval |

這張表的使用方式是：先用前三列篩掉明顯不合適的模型，再用中間幾列確認 harness 能不能支援，最後兩列交給法遵與平台團隊。選定後仍要把「主模型加一個便宜的輔助模型」放進 eval，因為很多步驟（分類、摘要、子任務）不需要最強的模型，第 25 章會實作 routing。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic API 價格（每百萬 token 的 input／output）為 Fable 5.1 $10／$50、Opus 5.5 $4／$20、Sonnet 5.5 $2／$10、Haiku 4.5 $1／$5。OpenAI 在 2026-09 推出 GPT-6 Sol／Luna 與 GPT-6.1 Sol；Google 的穩定版包含 Gemini 3.8 Flash 與 3.5 Flash-Lite，Gemini 3.1 Pro 仍是 preview。模型更新非常快，以上僅作為讀 model card 時的參照，請以供應商當下的模型頁為準。

## 3.12 動手做：token、成本、延遲估算器與 cache 命中模擬

現在把本章的概念組起來，替 Iris 的客服 agent 做一個估算器。它用 ScriptedModel 跑一段三個使用者回合、共七次模型呼叫的 session，每次呼叫都：用粗估規則算出輸入 token、用前綴雜湊模擬 cache 命中與 TTL、依示意價格算成本、依 3.9 節的公式算延遲。最後比較四種情境：不用 cache、穩定前綴加 cache、system prompt 放時間戳、以及 cache 加高 effort。

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


def call(name: str, call_id: str = "c1", out: int = 60, **args: Any) -> ModelResponse:
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use",
                         usage={"input_tokens": 0, "output_tokens": out})


def say(text: str, out: int = 150) -> ModelResponse:
    return ModelResponse(text=text, usage={"input_tokens": 0, "output_tokens": out})


# ---------- 1. 粗估 token：中文約 1 字 1 token，其他字元約 4 字元 1 token（只做估算）----------
def estimate_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    return cjk + (len(text) - cjk + 3) // 4


# ---------- 2. 價格與延遲（示意數字，不代表任何特定模型）----------
@dataclass
class Pricing:                    # 美元 / 每百萬 token
    input: float = 3.0
    output: float = 15.0
    cache_write_mult: float = 1.25
    cache_read_mult: float = 0.10


@dataclass
class Latency:
    base_ttft: float = 0.35       # 排隊、網路、第一個 token 的固定開銷（秒）
    prefill_tps: float = 8000.0   # 未命中快取的輸入，每秒能處理多少 token
    cached_tps: float = 80000.0   # 命中快取的部分幾乎不用重算
    decode_tps: float = 60.0      # 輸出速度（tokens/s）


# ---------- 3. 前綴快取：以「區塊邊界的累積雜湊」模擬 prefix match 與 TTL ----------
class PrefixCache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self.entries: dict[str, float] = {}       # 前綴雜湊 -> 到期時間

    @staticmethod
    def boundaries(blocks: list[str]) -> list[tuple[str, int]]:
        h, total, out = hashlib.sha256(), 0, []
        for b in blocks:
            h.update(b.encode())
            total += estimate_tokens(b)
            out.append((h.hexdigest(), total))
        return out

    def lookup_and_write(self, blocks: list[str], now: float) -> tuple[int, int]:
        bounds = self.boundaries(blocks)
        hit = 0
        for digest, tokens in bounds:             # 找最長、尚未過期的相同前綴
            if self.entries.get(digest, -1) >= now:
                hit = tokens
                self.entries[digest] = now + self.ttl  # 讀取會刷新 TTL
        for digest, _ in bounds:                  # 這次請求的整個前綴寫入快取
            self.entries[digest] = max(self.entries.get(digest, 0), now + self.ttl)
        return hit, bounds[-1][1] - hit           # (cache_read, cache_write)


# ---------- 4. 跑一次 agent session，逐次記帳 ----------
POLICY = "退款政策：鑑賞期七天內可退，已出貨需先取回商品，金額超過五千元需主管核准。" * 150
TOOLS = json.dumps([{"name": n, "description": f"{n} tool", "input_schema": {"type": "object"}}
                    for n in ["get_order", "get_shipping", "refund", "search_kb"]] * 25)


def run_session(use_cache: bool, timestamp_in_system: bool, effort_mult: float = 1.0):
    model = ScriptedModel([
        call("get_order", "c1", order_id="BB-1024"), call("get_shipping", "c2", order_id="BB-1024"),
        say("您的訂單已在配送中，預計明天送達。"),
        call("search_kb", "c3", q="退貨流程"), say("七天內可申請退貨，流程如下……"),
        call("refund", "c4", order_id="BB-1024"), say("已為您送出退款申請。"),
    ])
    user_turns = [(0.0, "我的訂單 BB-1024 到哪了？"), (180.0, "如果想退貨怎麼辦？"), (600.0, "那幫我退款")]
    tool_output = json.dumps({"order_id": "BB-1024", "status": "shipped", "items": ["藍色帆布鞋"] * 30},
                             ensure_ascii=False)
    price, lat, cache = Pricing(), Latency(), PrefixCache(ttl=300.0)
    messages: list[dict] = []
    log, clock = [], 0.0
    for start, text in user_turns:
        clock = max(clock, start)
        messages.append({"role": "user", "content": text})
        while True:
            system = POLICY + (f"\n現在時間：{clock:.0f}" if timestamp_in_system else "")
            blocks = [TOOLS, system] + [json.dumps(m, ensure_ascii=False) for m in messages]
            total_in = sum(estimate_tokens(b) for b in blocks)
            if use_cache:
                read, write = cache.lookup_and_write(blocks, clock)
            else:
                read, write = 0, total_in
            resp = model.complete(messages)
            out = int(resp.usage["output_tokens"] * effort_mult)   # 較高 effort ⇒ 更多 thinking 輸出
            wmult = price.cache_write_mult if use_cache else 1.0
            cost = (read * price.input * price.cache_read_mult + write * price.input * wmult
                    + out * price.output) / 1e6
            ttft = lat.base_ttft + write / lat.prefill_tps + read / lat.cached_tps
            seconds = ttft + out / lat.decode_tps
            log.append({"in": total_in, "read": read, "out": out, "cost": cost, "ttft": ttft, "sec": seconds})
            clock += seconds
            if resp.stop_reason != "tool_use":
                messages.append({"role": "assistant", "content": resp.text})
                break
            tc = resp.tool_calls[0]
            messages.append({"role": "assistant", "content": "", "tool_calls": [tc.__dict__]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": tool_output})
            clock += 0.8                                            # tool 本身的延遲
    return log


def summarize(name: str, log: list[dict]) -> dict:
    tin = sum(r["in"] for r in log)
    s = {"calls": len(log), "input": tin, "hit": sum(r["read"] for r in log) / tin,
         "cost": sum(r["cost"] for r in log), "ttft": sum(r["ttft"] for r in log) / len(log),
         "sec": sum(r["sec"] for r in log)}
    print(f"輸入 {s['input']:>6,}  命中率 {s['hit']:>4.0%}  成本 ${s['cost']:.4f}  "
          f"平均 TTFT {s['ttft']:.2f}s  總時間 {s['sec']:>4.1f}s  ← {name}")
    return s


cached = run_session(use_cache=True, timestamp_in_system=False)
print("逐次呼叫（穩定前綴＋快取）")
for i, r in enumerate(cached, 1):
    print(f"  #{i} 輸入 {r['in']:>5}  命中 {r['read']:>5}  輸出 {r['out']:>3}  "
          f"TTFT {r['ttft']:.2f}s  ${r['cost']:.4f}")
print()
base = summarize("無快取", run_session(False, False))
good = summarize("穩定前綴＋快取", cached)
bad = summarize("system 放時間戳", run_session(True, True))
high = summarize("快取＋高 effort", run_session(True, False, effort_mult=4.0))

assert good["cost"] < base["cost"] * 0.5            # 快取讓輸入成本大幅下降
assert bad["hit"] < good["hit"] / 2               # 時間戳讓 system 之後的前綴每次都不同
assert good["ttft"] < base["ttft"]                  # 命中快取也降低首字延遲
assert high["cost"] > good["cost"] and high["sec"] > good["sec"]  # 輸出 token 貴又慢
```

```text
逐次呼叫（穩定前綴＋快取）
  #1 輸入  7418  命中     0  輸出  60  TTFT 1.28s  $0.0287
  #2 輸入  7678  命中  7418  輸出  60  TTFT 0.48s  $0.0041
  #3 輸入  7940  命中  7678  輸出 150  TTFT 0.48s  $0.0055
  #4 輸入  7981  命中  7940  輸出  60  TTFT 0.45s  $0.0034
  #5 輸入  8242  命中  7981  輸出 150  TTFT 0.48s  $0.0056
  #6 輸入  8277  命中     0  輸出  60  TTFT 1.38s  $0.0319
  #7 輸入  8536  命中  8277  輸出 150  TTFT 0.49s  $0.0057

輸入 56,072  命中率   0%  成本 $0.1786  平均 TTFT 1.35s  總時間 21.0s  ← 無快取
輸入 56,072  命中率  70%  成本 $0.0851  平均 TTFT 0.72s  總時間 16.5s  ← 穩定前綴＋快取
輸入 56,111  命中率  20%  成本 $0.1811  平均 TTFT 1.17s  總時間 19.7s  ← system 放時間戳
輸入 56,072  命中率  70%  成本 $0.1161  平均 TTFT 0.72s  總時間 51.0s  ← 快取＋高 effort
```

先看逐次呼叫的表。#1 是冷啟動，七千多 token 全部要寫入，成本與 TTFT 都最高。#2 到 #5 每次只多了幾百 token，命中幾乎整個前綴，單次成本降到 #1 的七分之一左右，TTFT 也從 1.28 秒降到 0.48 秒。#6 是一個值得注意的細節：第三個使用者回合在第 600 秒才開始，距離上一次呼叫超過 300 秒的 TTL，cache 已經過期，成本又跳回冷啟動的水準。這正是 3.8 節「依請求間隔選 TTL」的具體樣子。

再看彙總的四行。第一，這段只有三句話的 session 總輸入是五萬六千 token，大約是使用者實際輸入字數的上千倍，這就是 Iris 估錯的原因。第二，穩定前綴加 cache 讓成本降到一半以下，平均 TTFT 也幾乎減半。第三，system prompt 放時間戳的版本命中率只剩 20%（只有放在最前面的 tool 定義還能命中），成本甚至比不用 cache 還高，因為每次都在付寫入溢價。第四，高 effort 情境假設輸出變成四倍，輸入完全相同，成本卻增加了三成多，總時間更是變成三倍，因為輸出 token 又貴又慢。

最後提醒這個估算器的限制。token 估算是粗估規則，真實數字要用供應商的計數 API；價格與延遲參數是示意值，使用前要換成你量測到的數字；cache 模擬以訊息為單位比對前綴，真實系統以 token 為單位，並受 breakpoint 位置與最小可快取長度影響。即使如此，它已經足以回答阿哲的兩個問題的量級，並且讓你在設計審查時，能用數字說明「為什麼時間戳不能放在 system prompt」。第 29 章會把同樣的記帳邏輯接到真實的 trace 上。

## 3.13 實務應用

### 情境一：電商客服 agent（互動、延遲敏感）

青鳥的客服 agent 是本章的主角。它的特徵是：每個 session 有多個使用者回合、回合之間可能隔幾分鐘、使用者在畫面前等待。根據本章的分析，Iris 做了四個改動：把時間戳從 system prompt 移到最新一則 user 訊息；固定 tool 列表與順序，並用確定性的 JSON 序列化；預設 effort 調低，只有退款判斷這類步驟才提高；開啟 streaming 並在 tool 執行時顯示「正在查詢物流」。市面上的客服 agent 產品普遍強調在回覆中串流進度、控制步數，並把政策與商品資料交給 tool 或檢索提供，而不依賴模型的內建知識，這和 model card 中「知識截止日」那一列直接相關。

### 情境二：背景 coding agent（長任務、成本與成功率）

青鳥在 Part 4 會做內部 coding agent。它的特徵和客服相反：使用者不在線上等，一個任務可能跑幾十到上百步，context 長到數十萬 token。這時 cache 命中率是成本的決定因素，任何改寫歷史的優化都可能讓成本暴增；effort 則傾向設高，因為一次失敗的 PR 浪費的工程師時間遠比 token 貴。公開資料顯示，Claude Code 等 coding agent 在 harness 裡把穩定的工具與指令放在前綴、避免中途改設定；Anthropic 的 2026-04-23 postmortem 記錄了一次 cache 相關 bug 讓舊 thinking 每輪被裁掉，結果是模型健忘、重複且 cache miss。這個案例說明本章的機制在 production 中會直接變成品質事故。

### 情境三：批次報表與研究 agent（吞吐量與 tool 成本）

營運團隊希望每天晚上替數千家網店產生一份「異常訂單摘要」。這類工作不需要即時回應，延遲預算以小時計，所以可以選更便宜的模型或較低 effort，並使用供應商的批次 API（通常有價格折扣，代價是結果非同步回來）。成本模型的重點從 TTFT 轉移到總 token 量與 tool 成本：如果每份摘要都要呼叫外部搜尋或執行 SQL，tool 成本可能超過模型成本。Anthropic 公開的多 agent research 系統文章也指出，multi-agent 架構的 token 用量約為一般聊天的 15 倍，所以只在任務價值足夠高時才值得（第 20 章）。

### 情境四：多供應商部署（adapter 與 fallback）

有些租戶要求資料只能在特定雲端區域處理，青鳥因此需要同時支援兩家供應商。3.6 節的 adapter 在這裡變成必要元件：上層 loop 只看 `ToolCall`，下層保留各家的不透明欄位。要特別注意 cache 是依模型分開的，fallback 到另一個模型時，第一次呼叫一定是冷啟動，延遲與成本都會跳升；而且 thinking 區塊通常不能跨模型使用。所以 fallback 路徑也要有自己的 eval 與成本預算，第 25 章會實作 router 與熔斷。

## 3.14 設計檢查清單

- 你是否已用真實資料取樣，量測過一個典型 session 的總輸入 token、總輸出 token 與模型呼叫次數，而不是只估使用者輸入？
- 每次呼叫的 usage（input、output、cache read、cache write）是否都記錄到 trace，並在寫入時依當時價格表算好成本？
- system prompt 與 tool 定義中是否沒有任何每次請求都會變的內容（時間戳、request id、隨機排序）？
- 對話歷史是否嚴格 append-only，並使用確定性的序列化（固定 key 順序）？
- 你的 cache TTL 選擇是否依據「共用前綴的請求間隔」做過計算，而不是隨意選長 TTL？
- 每個步驟的 effort 是否依任務類型設定，並在 eval 上比較過「每次成功任務成本」？
- max_tokens 是否留足了 thinking 與 tool 參數的空間，且程式會處理 `max_tokens` 截斷？
- provider adapter 是否原樣保留 thinking 區塊、reasoning item、thought signature 等不透明欄位？
- 需要機器可讀的輸出是否使用 strict schema 或 structured outputs，並仍在程式中做語意驗證？
- 是否處理了拒答（refusal）與不完整（incomplete）的回應，而不是直接解析內容？
- 互動式與背景式工作是否各自定義了延遲預算（TTFT、總時間）與步數上限？
- 選模型時是否讀過 model card 的 context、價格、thinking 控制、tool 限制、知識截止日與生命週期，並用自家 eval 做最後決定？

## 3.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 帳單比估算高一個數量級 | 只算了使用者輸入，沒算前綴重送與歷史累積 | 從 trace 加總每次呼叫的 input_tokens | 用 3.10 節公式重估；縮短 tool 輸出、做 compaction |
| 多輪對話 cache read 一直是 0 | 前綴中有會變的值，或序列化不確定 | 比對連續兩次請求的 payload，找第一個不同的位元組 | 把變動內容移到尾端；`sort_keys=True`；固定 tool 順序 |
| 用了 cache 反而更貴 | 每次都寫入但很少讀到（前綴太短、請求間隔超過 TTL） | 看 cache write 與 cache read 的比例 | 把 breakpoint 放在真正共用的部分；調整 TTL 或不用 cache |
| tool call 參數 JSON 解析失敗 | 撞到 max_tokens 被截斷，或沒有用 strict | 檢查 stop_reason 是否為 `max_tokens` | 提高 max_tokens；開 strict；解析失敗時回填錯誤讓模型重試 |
| 多輪 tool use 之後模型「忘了」前面的推理或 API 報錯 | adapter 丟掉了 thinking 區塊或 reasoning item | 比對送出的歷史與上一輪原始回應 | 原樣保存並回送不透明欄位 |
| 回應變慢但輸入沒變長 | effort 或 thinking 設定改變，輸出 token 暴增 | 看 output_tokens 的分佈與 p95 | 依步驟設定 effort；限制步數；串流中間進度 |
| 同一題在 eval 中時好時壞 | sampling 隨機性加上多步累積 | 同一題重跑多次看 pass^k | 不要依賴 temperature=0；改善 tool 與 prompt；用 ScriptedModel 重播定位 |
| 結構化輸出格式正確但內容錯 | schema 只保證語法 | 抽樣人工檢查或寫語意驗證 | 加入程式驗證與修復迴圈（第 7 章） |

## 本章重點整理

- token 是 LLM 計價、context 上限與速度的共同單位；中文、JSON、ID 與時間戳的 token 密度和英文散文不同，必須用自己的資料量測。
- 模型沒有記憶，每次呼叫都重讀整個 context；agent 「記得」的一切都是 harness 送進去的。
- context window 是輸入與輸出共用的上限，max_tokens 不足會截斷 thinking 或 tool 參數；放得下不等於用得好，長 context 仍需要紀律。
- sampling 參數決定從機率分佈中如何選字，但 agent 的可重現性主要靠 trajectory 記錄與重播，而不是 temperature=0。
- reasoning model 的 thinking 是照 output 價格計費的真實輸出；interleaved thinking 讓模型在每次 tool 結果後修正方向，effort 是品質、成本與延遲的主旋鈕。
- function calling 在各家 API 呈現為 messages、items、steps 三種形態，模型只產生呼叫請求，執行與權限都由 harness 負責。
- provider adapter 要把回應收斂成統一的 ToolCall，同時原樣保留 thinking、reasoning item、thought signature 等不透明欄位。
- structured outputs 用受限解碼保證輸出符合 schema，但只保證形狀不保證內容，語意驗證與拒答處理仍不可少。
- prompt caching 依前綴逐位元組比對，穩定內容放前面、會變的內容放後面、歷史 append-only，是 agent 成本最重要的設計紀律。
- cache 有寫入溢價與讀取折扣，短 TTL 第二次請求就回本，長 TTL 要更多次讀取；要用 usage 欄位驗證命中，而不是假設。
- 延遲由 TTFT 與輸出速度組成，輸出 token 比輸入 token 慢一到兩個數量級；減少步數與輸出，比縮短輸入更有效。
- agent 的總輸入隨步數有線性與平方兩項成長，決策時要看每次成功任務的成本，而不是單次請求成本。
- model card 用來篩選候選與找出限制，最後的模型選擇要由自家 eval 決定。

## 延伸問答

> [!question]- Q1. 一個 agent 的固定前綴是 6,000 token，每一步新增 500 token，一次任務跑 20 步。不考慮 cache，總輸入大約多少？如果前綴與歷史都能命中 cache，成本大約變成多少比例？
> 第 i 步的輸入約為 6,000 加 500×(i−1)。20 步加總是 20×6,000＝120,000，加上 500×(0＋1＋…＋19)＝500×190＝95,000，合計約 21.5 萬 token。注意這只是一個 20 步的任務，前綴重送佔了一半以上，歷史累積的平方項佔了另一半，而且步數再翻倍時，平方項會變成四倍。
>
> 若以讀取倍數 0.1、寫入倍數 1.25 估算，每一步只有新增的 500 token 要寫入（第一步是整個 6,000），其餘都是讀取。寫入約 6,000＋19×500＝15,500 token，乘 1.25 約等於 19,375；讀取約 215,000−15,500＝199,500，乘 0.1 約等於 19,950。合計約 39,300 個「base 單價 token」，大約是無 cache 的 18%。這也說明為什麼 cache 命中率會被稱為 agent 成本最重要的單一指標。

> [!question]- Q2. 同事說「我們把 temperature 設成 0，所以 agent 是確定性的，eval 只要跑一次就好」。你怎麼回應？
> 第一，temperature＝0 只是讓每一步盡量選機率最高的 token，伺服器端的批次組合、浮點運算順序與基礎設施差異，仍可能讓同一個輸入得到不同結果；而且許多推理模型根本不開放 sampling 參數。第二，即使單步完全確定，agent 的輸入還包含 tool 結果，真實環境的 tool 回傳（庫存、物流狀態、時間）本身就會變。
>
> 第三，eval 的目的是估計「這個設定在一群任務上的成功率」，跑一次只能得到一個樣本。正確做法是同一題跑多次，看 pass@k 與 pass^k（第 27 章），並把 tool 結果做快照或用 ScriptedModel 重播，讓可重現性來自 harness 的設計，而不是寄望模型參數。

> [!question]- Q3. 為了省 input token，Iris 想在每次呼叫前把歷史中舊的 thinking 區塊刪掉。這個做法有什麼風險？應該怎麼做？
> 風險有三個。第一，對會保留先前 thinking 的模型，舊的推理是模型理解「自己為什麼走到這一步」的依據，刪掉會讓它重複探索或前後矛盾。第二，刪除會改變 prompt 前綴，從被刪的位置之後全部 cache miss，省下的 input 可能遠少於多付的寫入成本。第三，有些供應商會驗證 thinking 區塊與對話的對應關係，任意改寫歷史可能直接報錯。
>
> 比較好的做法是先量測：thinking 實際佔了多少 input？如果真的需要裁剪，使用供應商提供的 context editing 或 compaction 機制，它們的行為與 cache、驗證規則是一致的。另一個方向是降低 effort，讓 thinking 本來就產生得少。Anthropic 2026-04 的 postmortem 正好記錄了「舊 thinking 被每輪裁掉」造成模型健忘與 cache miss 的真實事故。

> [!question]- Q4. 需要模型輸出一個「工單分類結果」給下游程式，用 strict tool 和用 structured outputs 怎麼選？
> 兩者底層都可以是受限解碼，差別在語意與流程。structured outputs 是「這次回應的最終答案就是這個 JSON」，適合單次呼叫的分類、抽取，程式拿到就用，不會進入 tool loop。strict tool 是「模型決定要呼叫某個動作，參數必須符合 schema」，適合 agent 在多步過程中可能呼叫、也可能不呼叫的動作。
>
> 實務上的判斷準則是：如果你一定需要這個結構、而且這是流程的終點，用 structured outputs；如果它是 agent 可選的行動之一，用 strict tool。過去常見的「強制呼叫某個 tool 來拿 JSON」做法，在一些新模型上受到限制，主流建議是改用 structured outputs。無論哪一種，分類值是否合理（例如是否真的是退款問題）都要靠 eval 與程式檢查，schema 不會替你判斷。

> [!question]- Q5. 你在 production 的儀表板上看到，某租戶的多輪對話 cache read 一直是 0，其他租戶正常。你會怎麼查？
> 先確認範圍：只有這個租戶，表示問題可能在租戶專屬的內容。第一步是抓同一 session 的連續兩次請求 payload，做位元組層級的 diff，找出第一個不同的位置。常見元兇包括：租戶設定裡有動態欄位（例如即時庫存、促銷倒數）被塞進 system prompt；這個租戶啟用的 tool 集合每次組裝順序不同；或租戶的語系設定讓某段文字每次重新產生。
>
> 第二步檢查非內容因素：這個租戶的使用者是否回覆間隔特別長、超過 TTL；前綴是否低於最小可快取長度；請求是否被分散到不同的 workspace 或模型。找到原因後，把變動內容移到 breakpoint 之後，並在 CI 加一個測試：同一 session 連續兩次組 prompt，前綴必須一致。這類問題用 usage 欄位就能發現，所以 cache read 比例應該是每租戶的監控指標。

> [!question]- Q6. 模型已經有 1M token 的 context window，青鳥的客服 agent 還需要 compaction 或檢索嗎？
> 需要，理由有三個。第一是品質：context 越長、無關內容越多，模型使用關鍵資訊的能力越差（context rot），把三個月的訂單歷史全塞進去，反而可能讓它抓錯訂單。第二是成本與延遲：依 3.10 節的公式，輸入會隨步數累積，每一步都重送幾十萬 token，即使有 cache，讀取也不是免費的，TTFT 也會變長。
>
> 第三是邊界情況：最長的 session 終究會撞到上限，屆時沒有 compaction 的 agent 只能失敗。大 context window 的真正價值是讓你有更多空間做「選擇」，例如一次讀完一份長合約再回答，而不是讓你免去 context engineering。第 9、10、11 章分別處理 context 版面、compaction 與檢索。

> [!question]- Q7. System design 面試追問：「你要設計一個支援多家 LLM 供應商的 model adapter，介面要長什麼樣？哪些地方最容易出錯？」
> 介面上，對上層提供統一的 `complete(messages, tools, config)`，回傳 `ModelResponse{text, tool_calls, stop_reason, usage, raw}`。tool_calls 統一成 `{id, name, args}`，args 一律是已解析的 dict；stop_reason 收斂成 end_turn、tool_use、max_tokens、refusal 等少數值；usage 用四個互不重疊的欄位計費：未命中快取的 input、cache read、cache write、output；reasoning token 只做參考，因為它通常已經含在 output 裡，不能重複計費。config 裡的 effort、cache 策略要由 adapter 翻譯成各家參數，不支援的參數要明確報錯，而不是靜默忽略。
>
> 最容易出錯的有四處。一是不透明欄位：thinking 區塊、reasoning item、thought signature 必須存在 raw 裡並原樣送回。二是狀態模式：有的供應商用伺服器端狀態，有的要 client 送完整歷史，adapter 要決定由誰保存真實歷史，通常建議自己保存一份 durable log。三是平行 tool 結果的回填規則不同。四是 fallback：cache 依模型分開、thinking 不能跨模型，所以切換模型時要預期冷啟動，並讓 fallback 路徑有自己的 eval。

> [!question]- Q8. 估算題：青鳥每天有 20,000 個客服 session，每個 session 的情況與 3.12 節的模擬相同。用模擬裡的示意價格，每天的模型成本大約多少？最值得投資的優化是什麼？
> 直接用模擬結果：不用 cache 時每個 session 約 0.1786 美元，乘以 20,000 約為每天 3,572 美元；穩定前綴加 cache 約 0.0851 美元，約為每天 1,702 美元，一個月差距超過五萬美元。如果不小心把時間戳放進 system prompt，成本會回到甚至超過無 cache 的水準，所以第一個投資是「cache 命中率監控加前綴一致性測試」，成本極低、效益最大。
>
> 接下來看剩餘成本的組成。模擬中 #1 與 #6 兩次冷啟動佔了 cached 版本超過七成的成本，其中 #6 是因為使用者隔太久回覆而超過 TTL；可以評估對這類 session 使用較長 TTL，或縮小前綴（精簡政策文字、只載入相關 tool）。再來是輸出：高 effort 情境顯示輸出變成四倍時成本與延遲都明顯上升，所以依步驟調整 effort 是第三個槓桿。所有優化都要在 eval 上確認每次成功任務的成本真的下降，而不只是單次請求變便宜。

## 延伸閱讀

- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
- Manus Blog〈Context Engineering for AI Agents: Lessons from Building Manus〉（2025）
- Anthropic Engineering Blog 關於 Claude Code 品質問題的 postmortem（2026-04-23）
- Anthropic Claude 開發者文件：Prompt caching、Extended thinking、Effort、Tool use 各章（2026）
- OpenAI 開發者文件：Responses API、Function calling、Structured Outputs（2026）
- Google Gemini API 文件：Interactions API 與 Function calling（2026）
- HumanLayer〈12-Factor Agents〉（GitHub，2025）
- Sennrich, Haddow, Birch〈Neural Machine Translation of Rare Words with Subword Units〉（ACL 2016，BPE 的原始論文）
