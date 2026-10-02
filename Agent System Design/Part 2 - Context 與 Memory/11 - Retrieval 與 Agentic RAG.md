---
chapter: 11
title: Retrieval 與 Agentic RAG
part: 2
---

# 第 11 章　Retrieval 與 Agentic RAG

> [!abstract] 本章地圖
> **核心問題**：知識庫比 context window 大、比模型的訓練資料新，而且每個租戶都不一樣；agent 要怎麼在對的時候找到對的段落、只用它能看的資料回答，並且讓每一句話都能追溯到出處？
>
> **你會學到**：
> - 說清楚 RAG 的離線索引與線上查詢兩條管線，並依文件結構選擇 chunking 策略
> - 用純 Python 實作 BM25 與向量檢索，理解兩者各自擅長與失敗的查詢，並用 RRF 做 hybrid 融合
> - 判斷什麼時候該用一次性的傳統 RAG、什麼時候該讓 agent 透過 search tool 多輪查詢
> - 設計可驗證的 citation：引用只能來自本次檢索結果，數字與主張要找得到出處，找不到就轉真人
> - 用 recall@k、MRR、nDCG 量測檢索品質，並把「檢索錯」和「生成錯」分開診斷
> - 在多租戶系統中把權限過濾放在排序之前，避免跨租戶洩漏
>
> **前置知識**：第 4 章（agent loop、tool 結果回填）、第 5 章（tool 設計與回傳格式）、第 9 章（context 是稀缺資源、just-in-time 載入）

## 11.1 故事：一句「7 天內可以退」引發的客訴

客服 agent v1 上線幾個月後，查訂單、查物流、建立退貨單已經很穩定，第 9 章的退換貨手冊也改成了按需讀取。阿哲帶來下一個需求：「客服每天有三成的問題不是查訂單，而是問政策：生鮮能不能退、店到店退貨運費誰付、信用卡退刷多久入帳。這些答案都在說明中心裡，讓 agent 自己去看。」青鳥的說明中心有八百多篇平台文章，另外每一家商家還能寫自己的退換貨規則，數千家商家加起來是好幾萬段文字，而且每週都有人改。

Iris 先試了最直覺的做法：把說明中心整份塞進 system prompt。光是平台文章就佔掉幾十萬 tokens，每一題的成本和延遲都變得無法接受，商家自訂規則更是不可能全放。於是 Iris 改成第二版：把文章切成段落、用 embedding 服務轉成向量，存進向量資料庫；使用者每問一題，就取最相近的五段貼到 prompt 前面，再讓模型回答。這就是教科書上的 RAG，demo 時答得很漂亮。

上線第一週就出了三件事。第一件，顧客問「結帳出現 E-4012 是什麼意思」，向量檢索回傳了五段泛泛的「付款方式說明」，真正寫著 E-4012 的那一段排在第十一名，模型就照著付款說明自己編了一個解釋。第二件最嚴重：小花花藝的顧客問「鮮花到貨就壞了可以退嗎」，檢索拿到的是平台通則「一般商品享有 7 天鑑賞期」，agent 回答「7 天內可以退」；但小花花藝的規則是「鮮花不接受個人因素退貨，損壞請 24 小時內附照片申請」。顧客第五天來退，商家拒絕，客訴直接打到青鳥。資安工程師 Maya 追查時還發現，另一題的檢索結果裡混進了阿鞋鞋舖的退貨規則：向量資料庫是共用的，權限過濾是在取完前五名之後才做，偶爾會漏。第三件是阿哲的問題：「你說改了切段方式之後比較準，怎麼證明？」Iris 答不出來，因為沒有任何量測。

老陳看完 trace，在白板上寫了三行字：「找得到、只找該找的、說得出出處。」接著說：「RAG 的 R 是 retrieval，它首先是一個搜尋引擎問題，搜尋引擎有幾十年的成熟做法；你只用了向量檢索，等於只用了一半的工具。再來，現在的 agent 不必只查一次，它可以像人一樣，查不到就換個關鍵字再查。最後，每一句話都要能指回某一段原文，指不回來就不要說。」這一章就是 Iris 重做知識庫檢索的過程：先把索引管線與 chunking 做對，再實作 BM25、向量檢索與 hybrid 融合，接著把檢索包成 agent 的 search tool，加上 citation 驗證，最後用 recall@k 與 nDCG 證明它真的變好了。

## 11.2 為什麼需要 retrieval：知識不在模型裡，也塞不進 context

模型知道的東西有兩種來源。第一種是 **parametric knowledge**（參數化知識），也就是訓練時壓進模型權重裡的知識，例如「信用卡 3D 驗證是什麼」；它有截止日、不知道青鳥的內部規則，也無法針對某一家商家修改。第二種是 **non-parametric knowledge**（非參數化知識），也就是放在模型外面、需要時才查的資料，例如說明中心、商家政策、訂單資料庫。青鳥要的答案幾乎都屬於第二種：小花花藝的鮮花規則不在任何模型的訓練資料裡，就算在，上週改過的版本也不會在。

**RAG**（Retrieval-Augmented Generation，檢索增強生成）是把這兩者接起來的做法：先從外部資料找出和問題相關的片段，放進 context，再讓模型根據這些片段生成答案。這個名稱來自 Lewis 等人 2020 年的論文，但概念更早就存在於問答系統中。舉例來說，「店到店退貨運費誰付」這題，RAG 會先找到「退貨運費」那一段，把它和問題一起交給模型，模型只要做閱讀理解，而不必回憶。

```text
 離線：索引管線（文件變更時執行）
 ┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌────────────────────────┐
 │ 說明中心 │──►│ 解析清理 │──►│ chunking     │──►│ 索引                   │
 │ 商家政策 │   │ 去版面   │   │ ＋metadata   │   │  倒排索引（BM25）      │
 │ FAQ      │   │ 留標題   │   │ tenant、日期 │   │  向量索引（embedding） │
 └──────────┘   └──────────┘   └──────────────┘   └───────────┬────────────┘
                                                              │
 線上：查詢管線（每次提問執行）                               │
 使用者問題 ──► 查詢處理 ──► 權限過濾＋召回 ◄─────────────────┘
               （改寫、拆解）  BM25 / 向量 / hybrid
                                    │ 數十到數百個候選
                                    ▼
                              rerank（精排）──► 前 3–8 段 ──► 放進 context
                                                                 │
                                                                 ▼
                                                 模型生成答案＋citation ──► 驗證
```

這張圖分成上下兩半。上半部是**離線**的索引管線：文件從來源系統進來，先清掉 HTML 版面與導覽列，但保留標題結構；接著切成段落（chunk），每段附上租戶、更新日期、來源 id 等 metadata；最後寫進兩種索引。下半部是**線上**的查詢管線：問題可能先被改寫或拆成子問題，接著在使用者有權限看的範圍內召回候選段落，再用更精細的模型重新排序，取前幾段放進 context，最後讓模型生成答案並附上出處。Iris 的第二版只有「向量索引→取前五名→生成」三步，圖中的權限過濾、BM25、rerank 與驗證全部缺席，三件事故剛好落在這些缺口上。

為什麼不乾脆等 context window 夠大，全部塞進去？這是 2026 年最常被問的問題，下表把幾種讓模型「知道」外部知識的做法放在一起比較。

| 做法 | 怎麼運作 | 適合 | 不適合 | 主要成本 |
|---|---|---|---|---|
| 全部放進 context | 把整份文件放在 prompt | 單份長文件（一份合約、一份報告） | 數萬段、多租戶、常更新的知識庫 | 每題都付全部 tokens；context rot |
| fine-tuning | 把知識訓練進權重 | 語氣、格式、領域用語 | 會變動的事實、需要出處的答案 | 訓練與重訓；無法逐條刪除或引用 |
| 傳統 RAG | 每題檢索一次，前 k 段放進 context | 問題單純、延遲敏感 | 需要多步推理或改寫查詢的問題 | 索引維運；檢索錯就答錯 |
| agentic RAG | agent 透過 search tool 自己決定查什麼、查幾次 | 複合問題、查詢需要改寫、多來源 | 極低延遲的場景 | 多輪模型呼叫的延遲與 tokens |
| agentic search（grep、讀檔） | agent 用 grep、glob、讀檔直接搜原始檔 | 程式碼、結構化文件、量不大 | 大量非結構化文件、需要語意比對 | 幾乎零維運；查詢次數較多 |

表中的關鍵是最後一欄。把所有東西放進 context，看起來省掉了檢索的工程，其實是把成本轉嫁到每一次呼叫，而且第 9 章談過的 **context rot**（context 越長，模型越難從中找到並使用正確資訊）會讓答案品質下降，大 context window 只是讓你「能塞」，不代表「該塞」。fine-tuning 則有一個致命缺點：它無法告訴你答案出自哪一段，也無法在商家修改政策的當天生效。所以青鳥的選擇是 RAG，而且如後面幾節所示，是讓 agent 主導的 RAG。

> [!warning] 常見誤解
> 「RAG 就是向量資料庫。」向量資料庫只是其中一種索引。RAG 的本質是「先找再答」，找的方式可以是 BM25、向量、hybrid、SQL、grep，甚至呼叫另一個搜尋 API。把 RAG 等同於向量資料庫，常常讓團隊漏掉最便宜也最可靠的關鍵字檢索，Iris 的 E-4012 事故就是這樣發生的。

## 11.3 Chunking 與索引管線：檢索品質的上限在這裡決定

**chunk**（片段）是檢索的最小單位：索引裡的每一筆，就是一段可以被找到、被放進 context、被引用的文字。chunking 就是決定怎麼把文件切成 chunk。這一步看起來只是前處理，卻決定了檢索品質的上限：如果「鮮花損壞請 24 小時內附照片申請」被切成兩半，前半在一塊、後半在另一塊，任何一塊都不完整，後面的檢索再好也拿不到完整答案。

切得太大和太小都有問題。chunk 太大（例如一整篇文章），一段裡混了好幾個主題，向量會變成各主題的平均，和任何具體問題都不夠像；放進 context 時也浪費 tokens。chunk 太小（例如一句話），每一塊缺少上下文：「運費由買家負擔」這句話單獨看，不知道是在講退貨、換貨還是超商取貨。實務上常見的起點是每塊數百 tokens、相鄰重疊一兩句，但真正的值要用 11.9 節的量測決定。

```text
 一個 chunk 在索引裡的樣子（不只是文字）

 ┌─ id ──────────── kb-returns#3 ───────────────────────────────┐
 │ breadcrumb       退換貨說明 > 退貨運費                       │ ◄─ 標題路徑：補上下文
 │ text             商品瑕疵造成的退貨，運費由賣家負擔。個人因  │
 │                  素退貨，運費由買家負擔，超商店到店退貨每件  │
 │                  60 元。                                     │
 ├─ metadata ───────────────────────────────────────────────────┤
 │ tenant           *（平台共用）          ◄─ 權限過濾的依據    │
 │ source           help-center/returns.md ◄─ citation 連回原文 │
 │ updated_at       2026-08-01             ◄─ 新舊版本衝突時用  │
 │ doc_version      v14                    ◄─ 重建索引、比對用  │
 ├─ 索引欄位 ───────────────────────────────────────────────────┤
 │ terms            [退貨, 運費, 賣家, 買家, 店到店, ...] → BM25│
 │ vector           [0.12, -0.03, ..., 0.08]           → 向量   │
 └──────────────────────────────────────────────────────────────┘
```

這張圖說明一個 chunk 至少要帶四類資訊。最上面是 id 與文字本身，id 要穩定，因為 citation、評估標註與快取都靠它；breadcrumb（標題路徑）把「這段在哪篇文章的哪個標題下」接在文字前面，讓「運費由買家負擔」這種句子自帶上下文。中間是 metadata：`tenant` 決定誰能看到它，`source` 讓 citation 能連回原文，`updated_at` 與 `doc_version` 處理新舊版本與重建索引。最下面是兩種索引欄位，分別給 BM25 與向量檢索使用。Iris 第二版的 chunk 只有文字與向量，所以無法做權限過濾，也無法回答「這段是哪一版」。

下面的程式示範一個實用的 chunker：先依 Markdown 標題切（標題是作者留下的語意邊界），段落太長再依句子打包，相鄰兩塊重疊一句，並在每塊加上標題路徑。

```python
from __future__ import annotations

import re

DOC = """# 退換貨說明
## 退貨期限
一般商品到貨後享有 7 天鑑賞期。鑑賞期不是試用期，商品須保持完整包裝與配件。生鮮、冷藏與冷凍食品不適用鑑賞期，到貨損壞請於 24 小時內拍照申訴。
## 退貨運費
商品瑕疵造成的退貨，運費由賣家負擔。個人因素退貨，運費由買家負擔，超商店到店退貨每件 60 元。
## 退款時程
退貨商品入倉驗收後 3 個工作天內退款。信用卡退刷約 7 到 14 天入帳，依發卡銀行而定。
"""


def pack(sentences: list[str], max_chars: int) -> list[str]:
    """把句子依序裝箱，超過 max_chars 就開新箱；新箱以上一箱的最後一句開頭（重疊一句）。"""
    boxes, box = [], []
    for s in sentences:
        if box and len("".join(box + [s])) > max_chars:
            boxes.append("".join(box))
            box = box[-1:]
        box.append(s)
    return boxes + ["".join(box)] if box else boxes


def chunk_markdown(doc_id: str, text: str, max_chars: int = 50) -> list[dict]:
    """先依標題切（語意邊界），段落太長再依句子打包，並在每塊前面加上標題路徑。"""
    chunks, path = [], []
    for block in re.split(r"(?m)^(?=#)", text.strip()):
        heading, _, body = block.partition("\n")
        level = len(heading) - len(heading.lstrip("#"))
        path = path[: level - 1] + [heading.lstrip("# ").strip()]
        sentences = [s for s in re.split(r"(?<=。)", body.strip()) if s]
        for piece in pack(sentences, max_chars):
            chunks.append({"id": f"{doc_id}#{len(chunks) + 1}", "breadcrumb": " > ".join(path), "text": piece})
    return chunks


chunks = chunk_markdown("kb-returns", DOC)
for c in chunks:
    print(f"{c['id']:<13} [{c['breadcrumb']}] {c['text']}")
assert chunks[0]["breadcrumb"] == "退換貨說明 > 退貨期限"
assert chunks[1]["text"].startswith("鑑賞期不是試用期")       # 第 2 塊以第 1 塊的最後一句開頭
assert all(c["text"].endswith("。") for c in chunks)         # 不會在句子中間切斷
```

```text
kb-returns#1  [退換貨說明 > 退貨期限] 一般商品到貨後享有 7 天鑑賞期。鑑賞期不是試用期，商品須保持完整包裝與配件。
kb-returns#2  [退換貨說明 > 退貨期限] 鑑賞期不是試用期，商品須保持完整包裝與配件。生鮮、冷藏與冷凍食品不適用鑑賞期，到貨損壞請於 24 小時內拍照申訴。
kb-returns#3  [退換貨說明 > 退貨運費] 商品瑕疵造成的退貨，運費由賣家負擔。個人因素退貨，運費由買家負擔，超商店到店退貨每件 60 元。
kb-returns#4  [退換貨說明 > 退款時程] 退貨商品入倉驗收後 3 個工作天內退款。信用卡退刷約 7 到 14 天入帳，依發卡銀行而定。
```

四個 chunk 都以句號結尾，沒有任何一句被切斷，這是依句子打包而不是固定字數切割的好處；如果用固定 50 字切，「依發卡銀行而定」很可能被拆成「依發」和「卡銀行而定」兩半。第 2 塊以第 1 塊的最後一句「鑑賞期不是試用期……」開頭，這就是重疊：假設使用者問「鑑賞期能不能先用用看」，答案句子在兩塊裡都有，不會因為剛好落在邊界而找不到。注意第 2 塊超過了 50 字，因為重疊句加上一個長句已經超過上限，而程式選擇保留完整句子；`max_chars` 是軟上限。每塊前面的 `[退換貨說明 > 退貨運費]` 是標題路徑，建立索引時會和內文一起被搜尋。

| 策略 | 怎麼切 | 優點 | 缺點 | 適合 |
|---|---|---|---|---|
| 固定長度＋重疊 | 每 N 字或 N tokens 切一刀，重疊 M | 簡單、可預測 | 會切斷句子與表格 | 沒有結構的純文字、快速原型 |
| 結構感知 | 依標題、段落、條列、表格切 | 保留作者的語意邊界 | 依賴文件格式品質 | 說明文件、規章、Markdown、HTML |
| 句子打包 | 句子依序裝箱到上限 | 不切斷句子 | 長句或長表格仍要特別處理 | 中文客服文件、FAQ |
| 小塊檢索、大塊閱讀 | 用小 chunk 檢索，命中後回傳所在的整節 | 檢索精準又有完整上下文 | 索引與回傳邏輯較複雜 | 長篇規章、合約、技術手冊 |
| 加上下文前綴 | 每塊前面加上由模型產生的「這段在講什麼」說明 | 補足短句缺少的上下文 | 索引時要對每塊呼叫模型 | 大量短段落、彼此相似的文件 |
| 程式碼依語法切 | 依函式、類別切 | 不切斷程式結構 | 需要語言解析器 | 程式碼庫（但 agent 常直接 grep） |

表中「小塊檢索、大塊閱讀」與「加上下文前綴」是兩個實務上常用的進階做法。前者有時被稱為 parent-child 或 small-to-big：索引用小塊，所以命中精準；命中之後回傳它所在的整節，模型讀到完整上下文。後者的代表是 Anthropic 在 2024 年發表的 Contextual Retrieval：建立索引時，讓模型讀整篇文件，為每個 chunk 寫一兩句說明（例如「這段出自小花花藝的退貨規則，講鮮花損壞的處理」），把說明接在 chunk 前面再建 BM25 與向量索引；上面程式的標題路徑，可以看成這個做法的便宜版本。

索引管線還有三件容易被忽略的事。第一是**增量更新**：商家改了一條規則，只要重建那篇文件的 chunk，並刪掉舊版本的 chunk，否則新舊兩版同時被檢索到，模型會拿到互相矛盾的資料。第二是**刪除**：商家退出平台或要求刪除資料時，所有衍生物（chunk、向量、快取、評估集）都要能找到並刪掉，這要靠 metadata 裡的 `source` 與 `tenant`，第 12 章談 memory 的刪除權時會再遇到同樣的問題。第三是**解析品質**：PDF 的表格、多欄排版、頁首頁尾，若解析錯了，後面全部白做；導入新文件來源時，先抽樣檢查解析結果，比調整任何檢索參數都划算。

## 11.4 詞彙檢索與 BM25：精確比對的老將

**詞彙檢索**（lexical retrieval，也叫關鍵字檢索、稀疏檢索）的想法很直接：問題裡的詞，出現在哪些 chunk 裡，就把那些 chunk 找出來。它靠的資料結構叫**倒排索引**（inverted index）：對每個詞記錄「它出現在哪些 chunk、各出現幾次」，就像書末的索引頁記錄每個名詞出現在第幾頁。查詢時只要翻開查詢詞對應的那幾列，不必掃描全部文件，所以即使有上千萬個 chunk 也能在毫秒內完成。

```text
 倒排索引（每個詞 → 出現在哪些 chunk、出現幾次）

 詞          df   posting list（chunk id：詞頻）
 ─────────────────────────────────────────────────────
 退貨         6   kb-01:2  kb-02:1  kb-03:4  kb-04:1  kb-07:1  kb-10:3
 運費         3   kb-03:3  kb-06:1  kb-11:1
 店到         2   kb-03:1  kb-06:1
 e-4012       1   kb-05:2                    ◄─ df 小、idf 大：命中就是強訊號
 ─────────────────────────────────────────────────────
 查詢「店到店退貨運費誰付」→ 取出 店到、到店、退貨、運費 … 四列 → 合併計分
```

這張圖的每一列是一個詞的 **posting list**（出現清單）。`df`（document frequency，文件頻率）是這個詞出現在幾個 chunk 裡：「退貨」幾乎到處都有，df 很大；「e-4012」只出現在一個 chunk，df 是 1。查詢時，系統把查詢詞對應的幾列取出，對每個出現過的 chunk 計分再排序。中文沒有空格分詞，這裡用最簡單的做法：把連續的中文字切成相鄰兩字的 **bigram**（二元組），「店到店」變成「店到」「到店」；正式系統通常會用中文斷詞器，或混合使用 bigram 與斷詞結果。

計分的標準做法是 **BM25**（Best Matching 25，源自 1990 年代 Okapi 檢索系統的計分公式，至今仍是 Elasticsearch、OpenSearch 等搜尋引擎的預設）。它把三個直覺組合在一起。第一是 **IDF**（inverse document frequency，逆文件頻率）：越少見的詞越有鑑別力，「E-4012」命中的價值遠高於「退貨」。第二是**詞頻飽和**：一個詞在 chunk 裡出現越多次越相關，但第十次的價值遠小於第一次。第三是**長度正規化**：同樣出現兩次，在短 chunk 裡比在長 chunk 裡更有意義。公式寫成：對查詢中的每個詞 t，分數加上 `idf(t) × tf × (k1 + 1) / (tf + k1 × (1 − b + b × 文件長度 / 平均長度))`，其中 `k1` 控制飽和速度（常用 1.2），`b` 控制長度正規化的強度（常用 0.75）。下面的程式把後兩個直覺算給你看。

```python
from __future__ import annotations


def term_score(tf: int, doc_len: float, avg_len: float, idf: float, k1: float = 1.2, b: float = 0.75) -> float:
    """BM25 中單一查詢詞對一份文件的貢獻。"""
    return idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_len))


print("詞頻飽和（文件長度＝平均長度，idf＝1）")
for tf in (1, 2, 3, 5, 10):
    print(f"  tf={tf:<3} score={term_score(tf, 100, 100, 1.0):.2f}")
print("長度正規化（tf＝2，idf＝1）")
for ratio in (0.5, 1.0, 2.0, 4.0):
    print(f"  文件長度＝平均的 {ratio:<3} 倍 score={term_score(2, 100 * ratio, 100, 1.0):.2f}")

assert term_score(10, 100, 100, 1.0) < 2.2                      # 上限是 k1 + 1：重複再多次也不會無限加分
assert term_score(2, 50, 100, 1.0) > term_score(2, 400, 100, 1.0)  # 同樣出現兩次，短文件更相關
```

```text
詞頻飽和（文件長度＝平均長度，idf＝1）
  tf=1   score=1.00
  tf=2   score=1.38
  tf=3   score=1.57
  tf=5   score=1.77
  tf=10  score=1.96
長度正規化（tf＝2，idf＝1）
  文件長度＝平均的 0.5 倍 score=1.60
  文件長度＝平均的 1.0 倍 score=1.38
  文件長度＝平均的 2.0 倍 score=1.07
  文件長度＝平均的 4.0 倍 score=0.75
```

上半部是詞頻飽和：tf 從 1 到 2，分數從 1.00 升到 1.38；從 5 到 10，只從 1.77 升到 1.96，而且永遠不會超過 `k1 + 1 = 2.2`。這個設計防止一段文字靠重複關鍵字「洗分數」，例如一篇把「退貨」寫了二十次的行銷文章，不會因此壓過真正講退貨規則的那一段。下半部是長度正規化：同樣出現兩次，長度只有平均一半的 chunk 得 1.60，四倍長的只得 0.75。直覺是長 chunk 本來就容易碰巧含有某個詞，出現兩次的證據力比較弱。`b = 0` 會完全關掉長度正規化，`b = 1` 則完全依長度比例調整，0.75 是經驗上的折衷。

BM25 的強項正是 Iris 第二版的弱點：**精確字串**。錯誤碼（E-4012）、訂單編號、SKU、商家名稱、法條編號、API 名稱，這類查詢的使用者要的就是「含有這個字串的那一段」，BM25 一查就中，而且你能清楚解釋為什麼中。它的弱點是**用詞不一致**（vocabulary mismatch）：使用者說「退錢」，文件寫「退款」；使用者說「包裹會晚到嗎」，文件寫「物流延遲」。字面不重疊，BM25 的分數就是零。這正是下一節向量檢索要補的洞。

## 11.5 Embedding 與向量檢索：用「意思」找資料

**embedding**（嵌入向量）是把一段文字轉成一串固定長度的數字（例如 768 或 1,536 維），讓**意思相近的文字在向量空間裡距離也相近**。產生它的 **embedding model** 是一個專門訓練過的模型：訓練時給它大量「問題—相關段落」的配對，讓配對的向量靠近、不相關的向量遠離。結果是「退錢要等多久」和「退款時程：驗收後 3 個工作天內退款」雖然只共用一個「退」字，向量卻會很接近，因為模型學過這兩種說法講的是同一件事。

兩個向量有多像，最常用 **cosine similarity**（餘弦相似度）衡量：兩個向量夾角的餘弦值，1 代表方向完全相同，0 代表無關。如果向量事先做過 L2 正規化（長度變成 1），cosine 就等於內積，計算更快。**向量檢索**（vector retrieval，也叫 dense retrieval，稠密檢索）的流程是：離線時把每個 chunk 轉成向量存起來；查詢時把問題用同一個 embedding model 轉成向量，找出最接近的 k 個 chunk。這種「問題和文件各自獨立編碼、再比距離」的架構叫 **bi-encoder**（雙塔編碼器），它的好處是文件向量可以預先算好，查詢時只要編碼一次問題。

```text
 向量空間（示意：實際是數百到數千維）

            「退款時程」●
     「退錢要等多久」○ ╲ ← 距離近：意思相同（真實 embedding）
                        ╲
     「信用卡多久入帳」○──● 「信用卡退刷」
                                                   ● 「颱風物流延遲」
                                              ○ 「包裹會晚到嗎」
   ● 「E-4012」
     ↑ 真實 embedding 對代碼、編號常常不敏感：
       「E-4012」和「E-4021」的向量可能幾乎一樣

 查詢時：ANN 索引（例如 HNSW）
   第 2 層  ●─────────────────●                  稀疏的「高速公路」，大步跳躍
   第 1 層  ●──────●────────●──────●             較密，逐步靠近
   第 0 層  ●──●──●──●──●──●──●──●──●──●         全部節點，精細搜尋
           從上層入口出發，每層貪婪地走向離查詢最近的鄰居，再往下一層
```

圖的上半部是向量空間的示意：實心點是 chunk，空心點是查詢，意思相近的落在附近，所以向量檢索能解決 BM25 的用詞不一致。但圖中也標了它的盲點：embedding 擅長「意思」，不擅長「字面精確」，兩個只差一個數字的錯誤碼，向量可能幾乎相同。下半部是**近似最近鄰搜尋**（ANN，approximate nearest neighbor）的示意。上百萬個向量逐一比對太慢，所以向量資料庫會建立特殊索引，最常見的是 **HNSW**（Hierarchical Navigable Small World，多層的近鄰圖）：上層節點少、連線長，用來大步接近目標區域；下層節點多，用來精細搜尋。它是「近似」的：用少量的召回損失換取數量級的速度提升，參數（例如搜尋時探索多少個鄰居）就是在調這個取捨。另一類常見的 ANN 索引是 IVF（先分群，只搜最近的幾群）與 PQ（把向量壓縮成短碼以節省記憶體）。

本章的程式只用標準函式庫，沒辦法跑真正的 embedding model，所以用一個替身：把文字拆成字元的 1-gram 與 2-gram，用雜湊函數映射到 256 維，再正規化。這個技巧叫 **feature hashing**（特徵雜湊），它產生的是一個「軟化的詞彙向量」，能處理部分字面重疊，但完全不懂意思。下面的程式直接展示它和真實 embedding 的差距。

```python
from __future__ import annotations

import math
import zlib


def hash_vector(text: str, dim: int = 256) -> list[float]:
    """字元 1-gram＋2-gram 雜湊成固定維度的向量（feature hashing），再 L2 正規化。"""
    chars = [c for c in text.lower() if c.isalnum()]
    v = [0.0] * dim
    for g in chars + [a + b for a, b in zip(chars, chars[1:])]:
        h = zlib.crc32(g.encode())                   # 不用內建 hash()：字串 hash 每次啟動的 seed 不同
        v[h % dim] += 1.0 if (h >> 16) & 1 else -1.0   # 用另一個位元決定正負號，讓碰撞互相抵銷
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def cosine(a: str, b: str) -> float:
    return sum(x * y for x, y in zip(hash_vector(a), hash_vector(b)))


DOC = "退款時程：驗收後 3 個工作天內退款"
pairs = [
    ("退款要幾天", "共用「退款」字面"),
    ("退錢要等多久", "只共用「退」一個字"),
    ("錢什麼時候回到我的卡上", "意思相同，字面幾乎不同"),
    ("退款時程表下載失敗", "字面很像，意思無關"),
]
scores = {q: cosine(DOC, q) for q, _ in pairs}
for q, note in pairs:
    print(f"{scores[q]:+.3f}  {q:<12}（{note}）")
assert scores["退款時程表下載失敗"] > scores["錢什麼時候回到我的卡上"]   # 字面重疊贏過語意相同
assert abs(cosine(DOC, DOC) - 1.0) < 1e-9
```

```text
+0.384  退款要幾天       （共用「退款」字面）
+0.099  退錢要等多久      （只共用「退」一個字）
+0.036  錢什麼時候回到我的卡上 （意思相同，字面幾乎不同）
+0.399  退款時程表下載失敗   （字面很像，意思無關）
```

四行輸出把替身的本質攤開來看。「退款要幾天」和文件共用「退款」，分數 0.384；「退錢要等多久」只共用一個「退」字，分數掉到 0.099；「錢什麼時候回到我的卡上」意思和文件完全相同，分數只有 0.036，幾乎等於無關。最諷刺的是最後一行：「退款時程表下載失敗」講的是完全不同的事，卻因為字面很像而拿到最高分 0.399。真實的 embedding model 會把第三句排得很前面、把第四句排得比較後面，這正是它值得花錢的地方；而我們的替身只是「有部分比對能力的 BM25」。所以讀本章的動手做時要記住：程式裡的「向量檢索」展示的是**管線與融合的機制**，不代表真實 embedding 的效果。程式裡用 `zlib.crc32` 而不是 Python 內建的 `hash()`，是因為內建的字串雜湊每次啟動都會換 seed，同一段文字在兩次執行中會得到不同向量，索引就無法重用。

在真實系統裡，embedding 還有幾個工程上的約束。第一，**查詢與文件必須用同一個模型、同一個版本編碼**；換模型就要重建整個索引，因為不同模型的向量空間互不相容，本章延伸問答 Q8 會談怎麼安全地升級。第二，有些 embedding model 要求在查詢與文件前面加不同的指令前綴（例如標明這是 query 還是 passage），漏掉會明顯降低品質，要照模型文件做。第三，向量維度直接決定儲存與記憶體成本：一百萬個 1,536 維的 float32 向量就要約 6 GB，部分模型支援截短維度或量化以換取成本。第四，embedding 對長文字會「平均化」，所以 chunk 大小對向量檢索的影響比對 BM25 更大。

> [!warning] 常見誤解
> 「向量檢索比關鍵字檢索先進，所以可以取代它。」兩者擅長的查詢正好互補：向量檢索擅長改寫過的說法與語意相近的問題，BM25 擅長代碼、編號、專有名詞與罕見詞。客服、法律、程式碼這類充滿精確字串的領域，只用向量檢索幾乎一定會出現 E-4012 那種事故。下一節的 hybrid search 就是把兩者合起來。

> [!note] 2026 現況
> 截至 2026 年 10 月，向量檢索的部署形態大致分成三類：在既有資料庫或搜尋引擎中加上向量欄位（例如 PostgreSQL 的 pgvector 擴充、Elasticsearch／OpenSearch 的向量欄位，它們同時支援 BM25，做 hybrid 很方便）、專用的向量資料庫服務，以及模型平台內建的檔案檢索工具（例如 OpenAI 的 file search、Gemini Deep Research 可接的 File Search，由平台代管切塊、embedding 與索引）。embedding model 由模型廠商與開源社群持續推出，維度、上下文長度與多語言能力差異很大；選型時請用自己的評估集比較，而不是看公開排行榜。各服務的具體功能與參數以官方文件為準。

## 11.6 Hybrid search 與 rerank：先廣撈，再精排

既然 BM25 與向量檢索各有盲點，最直接的做法就是兩個都跑，再把結果合併，這叫 **hybrid search**（混合檢索）。困難在「合併」：BM25 的分數沒有上限，會隨查詢長度變動，可能是 9.8 也可能是 0.7；cosine 落在 −1 到 1 之間，而且常常擠在 0.5 到 0.7 這個窄區間。兩種分數直接相加，等於讓 BM25 獨斷，下面的程式示範這個問題，以及最常用的解法 RRF。

```python
from __future__ import annotations

from collections import Counter

# 同一個查詢「店到店退貨運費誰付」，兩個 retriever 的原始分數尺度完全不同
bm25 = [("kb-03", 9.8), ("kb-06", 7.1), ("kb-11", 2.4)]          # BM25：沒有上限，依查詢長短而變
vector = [("kb-06", 0.62), ("kb-03", 0.58), ("kb-10", 0.55)]      # cosine：落在 -1 到 1


def naive_sum(*runs):
    total: Counter[str] = Counter()
    for run in runs:
        for doc, score in run:
            total[doc] += score
    return [d for d, _ in total.most_common()]


def rrf(*runs, k: int = 60):
    total: Counter[str] = Counter()
    for run in runs:
        for rank, (doc, _score) in enumerate(run, 1):
            total[doc] += 1 / (k + rank)                  # 只用名次：第 1 名 1/61，第 2 名 1/62……
    return [(d, round(s, 4)) for d, s in total.most_common()]


print("分數直接相加：", naive_sum(bm25, vector))
print("RRF（k=60）：", rrf(bm25, vector))
assert naive_sum(bm25, vector)[2] == "kb-11"                     # 向量那邊的 kb-10 幾乎沒有發言權
assert [d for d, _ in rrf(bm25, vector)][:2] == ["kb-03", "kb-06"]  # 兩邊都排前面的文件勝出
```

```text
分數直接相加： ['kb-03', 'kb-06', 'kb-11', 'kb-10']
RRF（k=60）： [('kb-03', 0.0325), ('kb-06', 0.0325), ('kb-11', 0.0159), ('kb-10', 0.0159)]
```

第一行是分數直接相加的結果：第三名是 `kb-11`，只因為它的 BM25 分數 2.4 比向量那邊最高的 0.62 還大；向量檢索認為相關的 `kb-10` 被擠到最後，向量那一路幾乎沒有發言權。第二行是 **RRF**（Reciprocal Rank Fusion，倒數名次融合，Cormack 等人 2009 年提出）：它完全不看分數，只看名次，每一路的第 r 名貢獻 `1 / (k + r)`，k 通常取 60。`kb-03` 在兩邊分別是第 1 與第 2 名，`kb-06` 是第 2 與第 1 名，所以兩者同分並列第一；只在單一路出現的 `kb-11` 與 `kb-10` 則並列第三。RRF 的優點是不需要任何分數校準，任何「能排名」的檢索器都能加進來；k 的作用是讓名次差異變平緩，k 越大，第 1 名和第 5 名的差距越小，避免某一路的第一名獨大。如果你有足夠的標註資料，也可以改用分數正規化後加權相加，並用評估集調權重；但沒有資料時，RRF 是穩健的預設。

hybrid 解決的是「召回」（recall）：把可能相關的 chunk 盡量撈進候選集。但候選集裡的排序仍然粗糙，因為 BM25 與 bi-encoder 都是把問題與文件**分開**處理，沒有真正「一起讀」。這時用第二階段的 **rerank**（重新排序）來精排：**cross-encoder**（交叉編碼器）把問題和每一個候選 chunk **接在一起**送進模型，直接輸出一個相關度分數。因為它能看到問題與文件之間逐字的互動，判斷比 bi-encoder 準得多；代價是每個候選都要跑一次模型，所以只能用在前幾十到前一百個候選上，不能拿來掃全庫。

```text
 兩階段檢索的漏斗（數字是青鳥一題的典型量級）

 全部可見 chunk         ~30,000 （該商家＋平台共用；其他租戶已在這一步排除）
        │
        ├── BM25 前 50 ────┐
        │                  ├─► RRF 融合 ─► 候選 ~80（去重後）
        └── 向量 前 50 ────┘     便宜：毫秒級、不用模型
                                      │
                                      ▼
                         rerank（cross-encoder 或 LLM）
                         貴：每個候選一次模型推論、數十到數百毫秒
                                      │
                                      ▼
                         前 3–8 段 ─► 放進 context（每段數百 tokens）
```

這張漏斗圖的每一層都在用「更貴、更準」換「更少的候選」。最上層是權限過濾後的可見範圍，注意這一步發生在任何排序之前，11.8 節會解釋為什麼。第二層是兩路便宜的召回，各取前 50，融合去重後大約 80 個。第三層 rerank 只處理這 80 個，最後只留前幾段放進 context。設計時的兩個旋鈕是「召回取多少」與「最後留多少」：召回太少，rerank 再準也救不回沒被撈到的答案；留太多，context 變長、成本上升，而且研究（例如 Liu 等人 2023 年的〈Lost in the Middle〉）顯示模型對放在長 context 中段的資訊利用得比較差。

| 方法 | 擅長 | 失敗情境 | 延遲與成本 | 可解釋性 |
|---|---|---|---|---|
| BM25 | 代碼、編號、專有名詞、罕見詞 | 用詞不一致、同義詞、口語改寫 | 極低；不需要模型 | 高：看得出哪些詞命中 |
| 向量檢索（bi-encoder） | 改寫、同義、跨語言的語意相近 | 精確字串、否定句、數字差異 | 低；索引需要 embedding | 低：很難說明為何相近 |
| hybrid（RRF） | 兩者互補，召回最穩 | 兩路都沒撈到的答案 | 兩路的總和 | 中 |
| cross-encoder rerank | 精細判斷相關度 | 候選集中沒有答案時無能為力 | 中到高；只能處理少量候選 | 低到中 |
| LLM 當 reranker | 需要推理或領域判斷的相關度 | 成本高、可能不穩定 | 高 | 可要求給理由 |

這張表的閱讀方式是由上往下疊加，而不是擇一。青鳥最後的配置是：BM25 加向量做召回、RRF 融合、小型 cross-encoder 做 rerank；只有在 agent 判斷結果不夠好時，才由 agent 自己換關鍵字重查，這是下一節的主題。公開資料中，專做客服 agent 的 Intercom 就在研究網站上發表過自建 reranker 與「用 LLM 當 reranker」的文章（這裡只依標題與日期判斷其主題，內容細節請以原文為準），至少顯示專業客服廠商把 rerank 視為值得投入研究的一層。

## 11.7 傳統 RAG vs agentic RAG：讓 agent 決定查什麼、查幾次

到目前為止的管線，有一個隱含假設：**使用者的原話就是好的查詢，而且查一次就夠**。這在單純的問題上成立，但小花花藝那一題「鮮花到貨就壞了，可以退錢嗎？退錢要等多久？」其實是兩個問題，而且「退錢要等多久」用的是口語，知識庫寫的是「退款時程」。傳統 RAG 會把整句話拿去查一次，取前五段，不管結果好不好都交給模型；模型看到不相關的段落，只能硬答或說不知道。

**agentic RAG**（agent 主導的檢索）把檢索從「生成前的固定步驟」變成「agent 可以反覆呼叫的 tool」。模型在 loop 中自己決定：要不要查、用什麼關鍵字查、結果夠不夠、要不要換個說法再查、要不要先查 A 再根據 A 的結果查 B。這正是第 4 章 agent loop 的自然延伸：search 只是一個唯讀 tool，它的結果和查訂單一樣回填成 observation。

```text
 使用者            Agent（模型）                     search_kb（hybrid＋權限過濾）
   │── 鮮花壞了可以退錢嗎？要等多久？ ─►│                        │
   │                │ 拆成兩個子問題                            │
   │                │── search("鮮花 到貨損壞 退貨") ──────────►│
   │                │◄──────────── kb-21 小花花藝鮮花退貨、kb-02 ─│
   │                │ 子問題一有答案                            │
   │                │── search("退錢要等多久") ────────────────►│
   │                │◄──────────── kb-07 發票、kb-21、kb-10 ────│
   │                │ 結果不相關 → 改寫：退錢 → 退款時程        │
   │                │── search("退款時程 入帳") ───────────────►│
   │                │◄──────────── kb-04 退款時程 ──────────────│
   │                │ 兩個子問題都有出處，寫答案＋[kb-21][kb-04]│
   │                │── 交給 harness 驗證 citation              │
   │◄── 可以，24 小時內附照片申請…[kb-21]；3 個工作天…[kb-04] ─│
```

這張時序圖就是本章動手做要實作的 trajectory。第一步，模型把複合問題拆成兩個子問題，這叫 **query decomposition**（查詢拆解）。第二步，第一個子問題的結果直接命中商家自己的規則。第三步，第二個子問題用使用者的原話查，結果是發票、後台審核這些不相關的段落；模型讀了結果的標題，判斷不夠好，於是把「退錢」改寫成知識庫的用語「退款時程」再查一次，這叫 **query rewriting**（查詢改寫）。最後模型手上有兩段出處，寫出附 citation 的答案，交給 harness 驗證。傳統 RAG 在這一題會失敗兩次：一次是兩個問題混在一起查，一次是口語查不到；agentic RAG 用兩次額外的模型呼叫換來了正確答案。

| 面向 | 傳統 RAG（一次檢索） | agentic RAG（search tool） |
|---|---|---|
| 誰決定查詢 | 程式碼：直接用使用者原話 | 模型：可以拆解、改寫、追問 |
| 查幾次 | 固定一次 | 視需要多次，由 harness 設上限 |
| 結果不好時 | 照樣交給模型 | 模型可以換關鍵字重查或改用別的 tool |
| 延遲 | 低且可預測：一次檢索＋一次生成 | 較高：每多查一次就多一輪模型呼叫 |
| 成本 | 低 | 數倍；每輪都要重讀歷史 |
| 失敗模式 | 檢索錯就答錯，模型無從補救 | 查太多次、原地打轉、過早停止查詢 |
| 適合 | FAQ 式單一問題、延遲極敏感 | 複合問題、口語查詢、多來源、research |

這張表說明兩者不是新舊之分，而是取捨。青鳥的做法是混合：對話第一輪由 harness 先用使用者原話跑一次 hybrid 檢索，把前三段放進 context（這是傳統 RAG，覆蓋大部分單純問題，延遲最低）；同時提供 `search_kb` tool，讓模型在結果不夠時自己再查。這對應第 1 章的光譜：第一輪檢索是 workflow 步驟（程式碼決定），後續檢索是 agent 行為（模型決定）。

search tool 的設計直接決定 agent 會不會用它，這是第 5 章 tool 設計原則在檢索上的應用。下面是青鳥 `search_kb` 的 schema 與結果格式。

```python
from __future__ import annotations

import json

SEARCH_KB = {
    "name": "search_kb",
    "description": ("搜尋青鳥客服知識庫（退換貨、物流、金流、發票政策）。回傳最相關的段落與 id；"
                    "回答時用 [id] 引用。查不到時換同義詞或拆成更小的問題再查，不要憑印象回答。"),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "關鍵字或短句，例如「生鮮 退貨」「E-4012」"},
            "top_k": {"type": "integer", "description": "回傳幾筆，預設 3，最多 8"},
            "offset": {"type": "integer", "description": "分頁起點；看完前幾筆仍不夠時才用"},
        },
        "required": ["query"],
    },
}


def format_hits(query: str, ranked: list[dict], top_k: int = 3, offset: int = 0, max_chars: int = 24) -> str:
    """把檢索結果整理成模型好讀、好引用的格式：id、標題、更新日期、截斷的內文，以及「還有沒有更多」。"""
    page = ranked[offset:offset + top_k]
    if not page:
        return json.dumps({"query": query, "hits": [],
                           "hint": "沒有結果。可以換同義詞（例如 退錢→退款）或拆成更小的問題。"}, ensure_ascii=False)
    hits = [{"id": h["id"], "title": h["title"], "updated": h["updated"],
             "text": h["text"][:max_chars] + ("…" if len(h["text"]) > max_chars else "")} for h in page]
    more = offset + top_k < len(ranked)
    return json.dumps({"query": query, "total": len(ranked), "hits": hits,
                       "next_offset": offset + top_k if more else None}, ensure_ascii=False)


RANKED = [
    {"id": "kb-02", "title": "生鮮與食品退貨", "updated": "2026-08-01",
     "text": "生鮮、冷藏與冷凍食品不適用 7 天鑑賞期；到貨損壞請於 24 小時內拍照申訴。"},
    {"id": "kb-01", "title": "退貨政策總則", "updated": "2026-03-15",
     "text": "一般商品到貨後享有 7 天鑑賞期，可申請退貨。"},
    {"id": "kb-03", "title": "退貨運費", "updated": "2025-11-20",
     "text": "個人因素退貨，運費由買家負擔。"},
]
out = format_hits("生鮮 退貨", RANKED, top_k=2)
print(out)
print(format_hits("退錢", []))
assert json.loads(out)["next_offset"] == 2 and json.loads(out)["hits"][0]["text"].endswith("…")
assert len(SEARCH_KB["description"]) < 120          # 描述要短而具體：它每一輪都佔 context
```

```text
{"query": "生鮮 退貨", "total": 3, "hits": [{"id": "kb-02", "title": "生鮮與食品退貨", "updated": "2026-08-01", "text": "生鮮、冷藏與冷凍食品不適用 7 天鑑賞期；到貨損…"}, {"id": "kb-01", "title": "退貨政策總則", "updated": "2026-03-15", "text": "一般商品到貨後享有 7 天鑑賞期，可申請退貨。"}], "next_offset": 2}
{"query": "退錢", "hits": [], "hint": "沒有結果。可以換同義詞（例如 退錢→退款）或拆成更小的問題。"}
```

輸出的第一行是有結果時的格式。每筆結果都帶 `id`，因為模型要用它來引用；帶 `title` 與 `updated`，讓模型不必讀完內文就能判斷相關性與新舊；內文截斷並以「…」標示，避免一次塞太多 tokens，模型需要全文時可以再用另一個 `fetch` 類 tool 讀取。`total` 與 `next_offset` 告訴模型「還有更多」，這比默默只回前幾筆好，模型才知道可以翻頁。第二行是沒有結果時的格式：不是回一個空陣列了事，而是附上可行動的提示「換同義詞或拆成更小的問題」，這和第 4 章「錯誤訊息要可行動」是同一個原則。tool 描述裡明寫「不要憑印象回答」，是為了對抗模型用 parametric knowledge 硬答的傾向。

agentic search 還有一個更極端的形態：完全不建索引，讓 agent 用 **grep**（以字串或正規表示式搜尋檔案內容）、glob（依檔名樣式列出檔案）與讀檔來找資料。這在程式碼上特別有效：函式名稱、錯誤訊息都是精確字串，grep 一查就中；檔案隨時在改，維護向量索引反而是負擔。代價是查詢次數多、對非結構化文件的語意比對能力弱。對青鳥來說，內部 coding agent（第 39 章）適合 grep，客服知識庫則需要 hybrid 檢索包成的 search tool。

agentic RAG 也帶來新的失敗模式，要在 harness 裡設防。第一是**查太多次**：模型對結果永遠不滿意，一直換說法重查；要設每題的搜尋次數上限，達到上限時回填「請根據現有結果回答或說明找不到」。第二是**過早停止**：模型查一次、拿到半相關的結果就開始寫答案；這要靠 tool 描述、system prompt 中的指引，以及 11.8 節的 citation 驗證把關。第三是**原地打轉**：用幾乎相同的關鍵字重查，第 4 章的重複呼叫偵測可以直接沿用。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各家公開資料：Anthropic 在 context engineering 文章中說明 Claude Code 採用混合策略，專案說明檔預先載入，其餘用 glob 與 grep 即時檢索，而不建立向量索引；Anthropic 的 multi-agent research system 文章明確對比「靜態 RAG」與「動態多步搜尋」，並以專門的 CitationAgent 在最後為主張補上出處。OpenAI 的 Deep Research API 文件要求接入的 remote MCP server 必須提供 `search` 與 `fetch` 兩個 tool，正是「先搜尋拿 id、再依 id 讀全文」的分工；Gemini 的 Deep Research Agent 預設使用 Google Search 等工具，也可以加上 MCP 與 File Search。Harvey 在 2026 年 9 月發表了以「Agentic Search」為題的文章，並另文描述用程式碼在 REPL 中遍歷大型 data room 的 RLM harness（屬於自建 benchmark 的自報結果）。細節以各家原文為準。

## 11.8 Citation 與 grounding：每一句話都要指得回原文

**grounding**（落地、有據）是指模型的回答建立在提供給它的資料上，而不是它自己的記憶或想像；**citation**（引用）則是 grounding 的可見證據：每個主張後面標出它來自哪一段。對客服來說，citation 有三個用途：讓顧客與客服主管能核對、讓評估能自動檢查回答有沒有依據、出事時能追查是「資料錯」還是「模型錯」。小花花藝事故中，如果答案旁邊標著「出處：平台退貨政策總則」，客服主管一眼就能看出它沒有用到商家自己的規則。

citation 最常見的問題不是模型忘記引用，而是**引用了但不可信**：模型可能標一個根本沒檢索到的 id、引用一段其實沒有支持該主張的文字，或者把兩段的數字混在一起。所以 citation 不能只是 prompt 裡的一句「請附出處」，harness 要驗證它。下面這張狀態圖是青鳥答案從草稿到送出的流程。

```text
                  ┌──────────────────────────────────────────┐
                  ▼                                          │ 修正（最多 N 次）
 ┌───────────┐  草稿  ┌────────────────────┐  失敗   ┌──────┴──────┐
 │ 檢索中    │──────►│ 驗證 citation      │───────►│ 回饋問題給   │
 │ search…   │       │ (1) id 在本次結果中 │        │ 模型重寫     │
 └───────────┘       │ (2) 數字有出處      │        └──────┬──────┘
      ▲              │ (3) 至少一個引用    │               │ 超過次數
      │ 需要更多資料 └─────────┬──────────┘               ▼
      └────────────────────────┤ 通過              ┌──────────────┐
                               ▼                   │ ungrounded： │
                        ┌─────────────┐            │ 不硬答，     │
                        │ done：送出  │            │ 轉真人客服   │
                        │ 附出處連結  │            └──────────────┘
                        └─────────────┘
```

這張狀態機有三個出口以外的關鍵設計。第一，驗證的允許清單是「**本次 run 實際檢索到的 chunk**」，不是整個知識庫，這同時擋掉了捏造的 id 與跨租戶的 id：模型就算「知道」阿鞋鞋舖的規則 id，也引用不了。第二，驗證失敗時不是直接放棄，而是把具體問題（哪個 id 不存在、哪個數字找不到出處）回饋給模型，給它有限次數的修正機會；這和第 4 章把錯誤變成觀察是同一個原則。第三，修正仍然失敗時，狀態是 `ungrounded`，回應「找不到可靠依據，轉真人」，而不是送出一個沒有依據的答案。對客服而言，「我不確定，幫您轉專人」遠比自信的錯誤答案便宜。

本章的驗證是便宜的規則檢查：id 是否存在、數字是否出現在被引用的段落裡。它抓不到「引用了相關段落，但對內容的解讀錯了」這類錯誤，例如段落寫「不接受個人因素退貨」，模型說成「不接受退貨」。更嚴格的做法有兩種：要求模型對每個主張附上原文的逐字引述（quote），由程式檢查引述確實出現在段落中；或者用另一個模型逐句判斷「這段文字是否支持這個主張」，這就是第 27 章 LLM-as-judge 的一種應用，要注意它的成本與偏誤。

grounding 還有兩個和安全直接相關的面向。第一是**權限過濾的位置**：Iris 第二版先取前五名、再濾掉別家商家的段落，這叫 post-filter，它有兩個問題：被濾掉的位置沒有補上，召回率下降；更糟的是過濾邏輯一旦有漏洞，資料就直接進了 context。正確做法是 pre-filter：在召回階段就只在使用者有權限的範圍內搜尋，別家商家的 chunk 根本不進候選集。第 33 章會把它放進多租戶授權的整體設計，第 44 章會處理更複雜的「權限感知檢索」。第二是**檢索內容不可信**：知識庫裡的文字可能被商家或第三方寫入，若其中夾帶對模型的指令，就是第 31 章的 indirect prompt injection。檢索結果要當成資料而不是指令處理，並避免讓 search tool 的結果直接觸發有副作用的動作；OWASP Top 10 for LLM Applications 2025 也把「向量與 embedding 的弱點」（LLM08）列為獨立一項。

> [!note] 2026 現況
> 截至 2026 年 10 月，部分模型 API 提供原生的 citation 功能：開發者把文件或搜尋結果以特定的內容區塊送入，模型的回應會附上引用的來源與位置，由 API 保證引用指向實際送入的內容。這能省下一部分自製驗證的工作，但仍然不會判斷「引用的段落是否真的支持該主張」。欄位名稱與支援的模型以各家官方文件為準。

## 11.9 檢索品質量測：recall@k、MRR 與 nDCG

阿哲的問題「怎麼證明比較準」，答案是建立**檢索評估集**：一批真實的使用者問題，每題由人標出知識庫中哪些 chunk 是相關的。這份標註在資訊檢索領域叫 **qrels**（query relevance judgments，查詢相關性標註）。標註可以是二元的（相關／不相關），也可以是分級的，例如 2 分代表「直接回答問題」、1 分代表「部分相關或提供背景」。有了 qrels，每次改 chunking、換 embedding model、調 RRF 參數，都能跑一次評估，用數字比較。

最常用的三個指標各回答不同的問題。**recall@k**（前 k 名的召回率）：所有相關 chunk 中，有多少比例出現在前 k 名？它回答「答案有沒有被撈到」，對 RAG 最重要，因為沒撈到的東西模型永遠看不到。**MRR**（Mean Reciprocal Rank，平均倒數名次）：第一個相關結果排在第幾名，取倒數再平均；第一名得 1，第三名得 1/3。**nDCG@k**（normalized Discounted Cumulative Gain，正規化折損累計增益，Järvelin 與 Kekäläinen 2002 年提出）：考慮分級相關度與名次，越相關的排越前面分數越高，再除以「理想排序」的分數，正規化到 0 到 1。

```python
from __future__ import annotations

import math


def recall_at_k(ranked: list[str], rel: dict[str, int], k: int) -> float:
    return sum(1 for d in ranked[:k] if d in rel) / len(rel)


def mrr(ranked: list[str], rel: dict[str, int]) -> float:
    return next((1 / i for i, d in enumerate(ranked, 1) if d in rel), 0.0)


def ndcg_at_k(ranked: list[str], rel: dict[str, int], k: int) -> float:
    """分級相關度：gain = 2^rel − 1，名次越後面折扣越大（除以 log2(名次 + 1)）。"""
    dcg = sum((2 ** rel.get(d, 0) - 1) / math.log2(i + 1) for i, d in enumerate(ranked[:k], 1))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(ideal, 1))
    return dcg / idcg


# 「生鮮可以退貨嗎」：kb-02 直接回答（2 分），kb-01 是總則（1 分）
rel = {"kb-02": 2, "kb-01": 1}
systems = {
    "A 最佳答案在第 1 名": ["kb-02", "kb-01", "kb-09"],
    "B 最佳答案在第 3 名": ["kb-01", "kb-09", "kb-02"],
    "C 只找到總則": ["kb-01", "kb-09", "kb-05"],
}
for name, ranked in systems.items():
    print(f"{name:<14} recall@3={recall_at_k(ranked, rel, 3):.2f}  "
          f"MRR={mrr(ranked, rel):.2f}  nDCG@3={ndcg_at_k(ranked, rel, 3):.3f}")
assert recall_at_k(systems["A 最佳答案在第 1 名"], rel, 3) == recall_at_k(systems["B 最佳答案在第 3 名"], rel, 3)
assert ndcg_at_k(systems["A 最佳答案在第 1 名"], rel, 3) == 1.0
assert mrr(systems["B 最佳答案在第 3 名"], rel) == mrr(systems["C 只找到總則"], rel) == 1.0
```

```text
A 最佳答案在第 1 名   recall@3=1.00  MRR=1.00  nDCG@3=1.000
B 最佳答案在第 3 名   recall@3=1.00  MRR=1.00  nDCG@3=0.689
C 只找到總則        recall@3=0.50  MRR=1.00  nDCG@3=0.275
```

三個系統的對照很有啟發性。A 和 B 都把兩個相關 chunk 撈進前三名，recall@3 都是 1.00；差別在 B 把最佳答案排到第三名，nDCG@3 從 1.000 掉到 0.689。這個差距在 RAG 中是有意義的：放進 context 的段落越靠前，模型越容易使用它，而且如果之後把 k 從 3 降到 2 以節省 tokens，B 就會漏掉最佳答案。C 只找到總則，recall 只有 0.50，nDCG 只有 0.275。最值得注意的是 MRR：三個系統的 MRR 都是 1.00，因為它只看「第一個相關結果」，而總則 `kb-01` 也算相關。這說明單一指標會騙人：MRR 適合「只要一個答案」的場景，分級相關度的品質要看 nDCG，召回要看 recall@k。

| 指標 | 回答的問題 | 對 RAG 的意義 | 盲點 |
|---|---|---|---|
| recall@k | 相關的有多少被撈進前 k 名？ | 決定模型「看不看得到」答案；召回階段的首要指標 | 不管排序；k 大時容易好看 |
| precision@k | 前 k 名有多少是相關的？ | 決定 context 裡的雜訊比例 | 相關 chunk 很少時天生偏低 |
| MRR | 第一個相關結果排第幾？ | 適合單一答案的 FAQ 式查詢 | 忽略第二個以後的結果與分級 |
| nDCG@k | 分級相關度＋名次的整體品質 | 適合比較 rerank 與融合策略 | 依賴分級標註的品質 |
| 答案忠實度（faithfulness） | 答案是否只根據檢索內容？ | 衡量生成端有沒有亂編 | 需要 LLM judge 或人工 |
| 端到端正確率 | 最終答案對不對？ | 使用者真正在乎的結果 | 無法分辨是檢索錯還是生成錯 |

表的上四列是**檢索指標**，下兩列是**生成與端到端指標**。兩層要分開量，因為它們的修法完全不同：recall 低，要改 chunking、加 BM25、加大召回數量或改善查詢；recall 高但答案仍錯，要看模型有沒有使用檢索到的內容、prompt 是否鼓勵它在資料不足時說不知道。只量端到端正確率的團隊，常常在模型 prompt 上反覆調整，問題其實出在檢索根本沒撈到答案。

評估集怎麼來？最好的來源是真實的使用者問題，而不是工程師自己想的題目：從客服紀錄中抽樣，涵蓋高頻問題、含代碼與編號的問題、口語化問題、多主題問題，以及「知識庫裡沒有答案」的問題（用來測 agent 會不會說找不到）。起步時幾十到一兩百題就很有用，重點是每次改動都跑、結果可比較。標註可以先讓模型提出候選、再由熟悉業務的人確認，以降低成本。第 27 章會把這套評估接進回歸測試與統計顯著性檢定。上線後也要量：在 trace 中記錄每次檢索的查詢、命中的 id 與名次，第 29 章的 observability 會用到這些欄位。

## 11.10 動手做：純 Python 的 hybrid 檢索與 agentic RAG

這一節把前面的概念組合成兩段可以離線執行的程式。第一段建立一個小型的青鳥知識庫，實作 BM25、雜湊向量檢索與 RRF 融合，並用 8 題帶分級標註的評估集比較三種檢索方式。第二段把 hybrid 檢索包成 `search_kb` tool，用 ScriptedModel 模擬 agent 多輪查詢、改寫查詢、附上 citation，並由 harness 驗證引用。再強調一次：程式中的「向量檢索」是 11.5 節的雜湊替身，只有字面重疊的比對能力；它在這裡的角色是讓 hybrid 融合的機制能完整跑起來，換成真實 embedding model 時，向量那一路的表現會更好，尤其在口語與同義詞查詢上。

### 第一段：BM25、向量、hybrid 的評估

```python
from __future__ import annotations

import math
import re
import zlib
from collections import Counter

# 青鳥知識庫（已切好的 chunk）：id、標題、內容
KB = {
    "kb-01": ("退貨政策總則", "一般商品到貨後享有 7 天鑑賞期，可申請退貨，商品須保持完整包裝與配件。"),
    "kb-02": ("生鮮與食品退貨", "生鮮、冷藏與冷凍食品屬易腐商品，不適用 7 天鑑賞期；若到貨時已損壞，請於 24 小時內拍照申訴。"),
    "kb-03": ("退貨運費", "商品瑕疵造成的退貨，運費由賣家負擔；個人因素退貨，運費由買家負擔，超商店到店退貨每件 60 元。"),
    "kb-04": ("退款時程", "退貨商品入倉驗收後 3 個工作天內退款；信用卡退刷約 7 到 14 天入帳，依發卡銀行而定。"),
    "kb-05": ("金流錯誤碼 E-4012", "結帳時出現 E-4012，代表信用卡 3D 驗證逾時，請買家重新結帳，不會重複扣款。"),
    "kb-06": ("超商取貨", "7-11 與全家店到店取貨期限為 7 天，逾期未取，包裹將退回賣家並酌收運費。"),
    "kb-07": ("發票與折讓", "電子發票於出貨後開立；退貨完成時，系統自動作廢發票或開立折讓單。"),
    "kb-08": ("訂閱商品", "定期配送的訂閱商品，可於下次出貨前 3 天在會員中心取消。"),
    "kb-09": ("物流延遲", "颱風、連假期間物流可能延遲 1 到 3 天，可用物流單號在貨態頁查詢最新狀態。"),
    "kb-10": ("商家後台退貨審核", "商家可在後台「訂單管理 > 退貨申請」審核退貨，並選擇退款或換貨。"),
    "kb-11": ("換貨規則", "尺寸或顏色不合可申請換貨一次，換貨的來回運費由買家負擔。"),
    "kb-12": ("付款方式", "支援信用卡、超商代碼、ATM 轉帳與行動支付，分期付款限信用卡。"),
}

CJK_RUN = re.compile(r"[一-鿿]+")
WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """英數字取整個詞；中文沒有空格，取相鄰兩字（bigram）當詞。"""
    text = text.lower()
    tokens = WORD.findall(text)
    for run in CJK_RUN.findall(text):
        tokens += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
    return tokens


class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = {d: Counter(tokenize(t)) for d, t in docs.items()}
        self.len = {d: sum(c.values()) for d, c in self.tf.items()}
        self.avg = sum(self.len.values()) / len(docs)
        df = Counter(tok for c in self.tf.values() for tok in c)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for d, tf in self.tf.items():
            s = 0.0
            for t in set(tokenize(query)):
                if t in tf:
                    norm = self.k1 * (1 - self.b + self.b * self.len[d] / self.avg)
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm)
            if s > 0:
                scores[d] = s
        return sorted(scores.items(), key=lambda x: -x[1])[:k]


def hash_vector(text: str, dim: int = 256) -> list[float]:
    """模擬 embedding：字元 1-gram 與 2-gram 用 crc32 雜湊到固定維度，再做 L2 正規化。"""
    chars = [c for c in text.lower() if c.isalnum()]
    grams = chars + [a + b for a, b in zip(chars, chars[1:])]
    v = [0.0] * dim
    for g in grams:
        h = zlib.crc32(g.encode())                 # 不用 hash()：它每次執行的 seed 不同
        v[h % dim] += 1.0 if (h >> 16) & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


class VectorIndex:
    def __init__(self, docs: dict[str, str]):
        self.vecs = {d: hash_vector(t) for d, t in docs.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        q = hash_vector(query)
        scores = {d: sum(a * b for a, b in zip(q, v)) for d, v in self.vecs.items()}
        return sorted(scores.items(), key=lambda x: -x[1])[:k]


def rrf(*rankings: list[tuple[str, float]], k: int = 60, top: int = 5) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion：只看名次，不看分數，所以不必把兩種分數換算到同一尺度。"""
    fused: Counter[str] = Counter()
    for ranking in rankings:
        for rank, (doc, _score) in enumerate(ranking, 1):
            fused[doc] += 1 / (k + rank)
    return fused.most_common(top)


def recall_at_k(ranked: list[str], rel: dict[str, int], k: int) -> float:
    return len([d for d in ranked[:k] if d in rel]) / len(rel)


def ndcg_at_k(ranked: list[str], rel: dict[str, int], k: int) -> float:
    dcg = sum((2 ** rel.get(d, 0) - 1) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg


# 評估集：真實客服問題＋人工標註的相關 chunk（2 = 直接回答，1 = 部分相關）
QRELS = {
    "生鮮可以退貨嗎": {"kb-02": 2, "kb-01": 1},
    "E-4012 是什麼錯誤": {"kb-05": 2},
    "店到店退貨運費誰付": {"kb-03": 2, "kb-06": 1},
    "鑑賞期有幾天": {"kb-01": 2, "kb-02": 1},
    "衣服尺寸不合想換": {"kb-11": 2, "kb-10": 1},
    "信用卡退刷多久入帳": {"kb-04": 2},
    "颱風天包裹會晚到嗎": {"kb-09": 2},
    "退錢要等多久": {"kb-04": 2},
}

docs = {d: f"{title} {body}" for d, (title, body) in KB.items()}
bm25, vec = BM25(docs), VectorIndex(docs)
K = 3
totals = {"bm25": [0.0, 0.0], "vector": [0.0, 0.0], "hybrid": [0.0, 0.0]}
print(f"{'bm25':<12}{'vector':<12}{'hybrid':<12}query")
for q, rel in QRELS.items():
    runs = {"bm25": bm25.search(q, 10), "vector": vec.search(q, 10)}
    runs["hybrid"] = rrf(runs["bm25"], runs["vector"], top=10)
    cells = []
    for name, ranking in runs.items():
        ids = [d for d, _ in ranking]
        totals[name][0] += recall_at_k(ids, rel, K)
        totals[name][1] += ndcg_at_k(ids, rel, K)
        cells.append(",".join(i[3:] for i in ids[:K]) or "（無）")
    print("".join(f"{c:<12}" for c in cells) + q)

print()
avg = {name: (r / len(QRELS), n / len(QRELS)) for name, (r, n) in totals.items()}
for name, (r, n) in avg.items():
    print(f"{name:<7} recall@3={r:.3f}  nDCG@3={n:.3f}")
assert avg["hybrid"][0] > max(avg["bm25"][0], avg["vector"][0])      # 融合後找回更多相關 chunk
assert not bm25.search("退錢要等多久")                                 # 用詞不同：BM25 完全找不到
assert "kb-04" not in [d for d, _ in rrf(bm25.search("退錢要等多久"), vec.search("退錢要等多久"))][:K]
```

```text
bm25        vector      hybrid      query
02,03,10    02,01,10    02,01,10    生鮮可以退貨嗎
05          05,01,06    05,01,06    E-4012 是什麼錯誤
03,06,11    03,06,10    03,06,10    店到店退貨運費誰付
01,02       02,09,04    02,01,09    鑑賞期有幾天
11          11,10,08    11,10,08    衣服尺寸不合想換
04,12,05    12,04,05    04,12,05    信用卡退刷多久入帳
06,09       01,10,06    06,09,01    颱風天包裹會晚到嗎
（無）         10,07,05    10,07,05    退錢要等多久

bm25    recall@3=0.750  nDCG@3=0.785
vector  recall@3=0.688  nDCG@3=0.613
hybrid  recall@3=0.875  nDCG@3=0.803
```

先看每題的前三名（為了節省版面，id 只印數字）。**「E-4012 是什麼錯誤」**：BM25 只回傳一筆，就是正確的 05，因為 `e-4012` 這個詞只出現在那一段；這正是 Iris 事故一的解法。**「生鮮可以退貨嗎」**：BM25 的第二名是 03（退貨運費，因為含很多「退貨」），向量那一路把總則 01 排第二，hybrid 取兩者之長得到 02、01，正好是標註的兩個相關 chunk。**「鑑賞期有幾天」**：BM25 排出 01、02，是理想順序；向量那一路把 01 漏出前三名，RRF 融合後 02 排在 01 前面，recall 不變但 nDCG 略降，這是融合的代價：某一路表現不好時會拖累另一路。**「颱風天包裹會晚到嗎」**：BM25 被「包裹」帶到超商取貨 06，正確答案 09 排第二。

最後一題**「退錢要等多久」**是刻意留下的失敗案例：BM25 一筆都找不到（「退錢」「多久」沒有出現在任何 chunk 裡），雜湊向量只能靠「退」「要」這些單字碰運氣，三種方法都沒有把 04 撈進前三名。程式最後的 assert 把這個失敗鎖住。真實的 embedding model 很可能救得回這題，但也可能不行；第二段會示範另一個不依賴 embedding 的解法：讓 agent 改寫查詢。

底部的平均值顯示：hybrid 的 recall@3 是 0.875，高於 BM25 的 0.750 與向量的 0.688；nDCG@3 是 0.803，也略高於 BM25 的 0.785。在這個小評估集上，hybrid 的主要貢獻是召回，排序的改善有限；這也是為什麼正式系統還要再加 rerank。8 題的評估集太小，不足以下統計結論，它的目的是示範流程：任何改動都能用同一份 qrels 重跑，用數字回答阿哲的問題。

### 第二段：agent 透過 search tool 多輪查詢並附 citation

這一段實作 11.7 節的時序圖與 11.8 節的狀態機。知識庫的每個 chunk 帶 `tenant`：`*` 是平台共用，`flower` 是小花花藝，`shoe` 是阿鞋鞋舖。`search_kb` 在排序之前就依租戶過濾。`run()` 是第 4 章 loop 的精簡版，多了三個檢索專屬的機制：記錄本次 run 實際檢索到的 chunk（`seen`，citation 的允許清單）、每題的搜尋次數上限，以及最終答案的 citation 驗證與有限次數的修正。

```python
from __future__ import annotations

import json
import math
import re
import zlib
from collections import Counter
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


# ───────── 知識庫：每個 chunk 帶 tenant；"*" 是平台共用，其他是個別商家 ─────────
KB = {
    "kb-02": ("*", "生鮮與食品退貨", "生鮮、冷藏與冷凍食品不適用 7 天鑑賞期；到貨損壞請於 24 小時內拍照申訴。"),
    "kb-04": ("*", "退款時程", "退貨商品入倉驗收後 3 個工作天內退款；信用卡退刷約 7 到 14 天入帳。"),
    "kb-07": ("*", "發票與折讓", "退貨完成時，系統自動作廢發票或開立折讓單。"),
    "kb-10": ("*", "商家後台退貨審核", "商家可在後台審核退貨申請，並選擇退款或換貨。"),
    "kb-21": ("flower", "小花花藝 鮮花退貨", "鮮花不接受個人因素退貨；到貨損壞請於 24 小時內附照片申請，確認後全額退款，免寄回。"),
    "kb-31": ("shoe", "阿鞋鞋舖 退貨", "鞋類到貨 14 天內可退貨，需保留鞋盒。"),
}


def tokenize(text: str) -> list[str]:
    text = text.lower()
    toks = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text)
    for run in re.findall(r"[一-鿿]+", text):
        toks += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
    return toks


def hash_vec(text: str, dim: int = 256) -> list[float]:
    cs = [c for c in text.lower() if c.isalnum()]
    v = [0.0] * dim
    for g in cs + [a + b for a, b in zip(cs, cs[1:])]:
        h = zlib.crc32(g.encode())
        v[h % dim] += 1.0 if (h >> 16) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def search_kb(query: str, tenant: str, top_k: int = 3) -> list[dict]:
    """hybrid 檢索。權限過濾放在排序「之前」：別家商家的 chunk 根本不進候選集。"""
    allowed = {d: f"{t} {b}" for d, (ten, t, b) in KB.items() if ten in ("*", tenant)}
    tf = {d: Counter(tokenize(x)) for d, x in allowed.items()}
    avg = sum(sum(c.values()) for c in tf.values()) / len(tf)
    df = Counter(t for c in tf.values() for t in c)
    q_toks = set(tokenize(query))
    bm = {}
    for d, c in tf.items():
        dl = sum(c.values())
        s = sum(math.log(1 + (len(tf) - df[t] + 0.5) / (df[t] + 0.5)) * c[t] * 2.2
                / (c[t] + 1.2 * (0.25 + 0.75 * dl / avg)) for t in q_toks if t in c)
        if s > 0:
            bm[d] = s
    qv = hash_vec(query)
    vec = {d: sum(a * b for a, b in zip(qv, hash_vec(x))) for d, x in allowed.items()}
    fused: Counter[str] = Counter()
    for ranking in (sorted(bm, key=bm.get, reverse=True), sorted(vec, key=vec.get, reverse=True)):
        for rank, d in enumerate(ranking, 1):
            fused[d] += 1 / (60 + rank)
    return [{"id": d, "title": KB[d][1], "text": KB[d][2]} for d, _ in fused.most_common(top_k)]


# ───────── agent：search tool＋citation 驗證 ─────────
CITE = re.compile(r"\[(kb-\d+)\]")
NUM = re.compile(r"\d+")


def verify(answer: str, seen: dict[str, str]) -> list[str]:
    """grounding 檢查：引用必須來自本次檢索結果，答案中的數字必須出現在被引用的 chunk 裡。"""
    cited = CITE.findall(answer)
    problems = [f"{c} 不在本次檢索結果中" for c in cited if c not in seen]
    if not cited:
        problems.append("答案沒有任何引用")
    support = " ".join(seen.get(c, "") for c in cited)
    problems += [f"數字 {n} 找不到出處" for n in NUM.findall(CITE.sub("", answer)) if n not in NUM.findall(support)]
    return problems


def run(model: ScriptedModel, question: str, tenant: str, max_searches: int = 4, max_repairs: int = 1):
    messages: list[dict] = [{"role": "user", "content": question}]
    seen: dict[str, str] = {}                       # 本次 run 實際檢索到的 chunk：citation 的允許清單
    searches = repairs = 0
    for step in range(1, 10):
        resp = model.complete(messages, tools=[{"name": "search_kb"}])
        messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
        if not resp.tool_calls:
            problems = verify(resp.text, seen)
            if not problems:
                return "done", resp.text, messages
            if repairs >= max_repairs:
                return "ungrounded", "這題我找不到可靠的依據，已轉給真人客服。", messages
            repairs += 1
            print(f"  step {step} 驗證失敗 → {problems}")
            messages.append({"role": "user", "content": "引用驗證失敗：" + "；".join(problems) + "。請只根據檢索結果改寫。"})
            continue
        for tc in resp.tool_calls:
            searches += 1
            if searches > max_searches:
                content = "已達本題搜尋上限，請根據現有結果回答，或說明找不到。"
            else:
                hits = search_kb(tc.args["query"], tenant)
                seen.update({h["id"]: h["text"] for h in hits})
                content = json.dumps(hits, ensure_ascii=False)
                print(f"  step {step} search({tc.args['query']!r}) → {[h['id'] for h in hits]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": content})
    return "max_steps", "", messages


def last_hits(msgs: list[dict]) -> list[str]:
    return [h["title"] for h in json.loads(msgs[-1]["content"])]


Q = "我在小花花藝買的鮮花到貨就壞了，可以退錢嗎？退錢要等多久？"

# 劇本：模型拆成兩個子問題；第二次搜尋結果不相關，於是改寫查詢再搜一次
good = ScriptedModel([
    call("search_kb", "c1", query="鮮花 到貨損壞 退貨"),
    call("search_kb", "c2", query="退錢要等多久"),
    lambda m: call("search_kb", "c3", query="退款時程 入帳") if "退款時程" not in last_hits(m) else say("?"),
    say("可以。鮮花到貨損壞請於 24 小時內附照片申請，確認後全額退款，免寄回 [kb-21]。"
        "退款會在驗收後 3 個工作天內處理，信用卡退刷約 7 到 14 天入帳 [kb-04]。"),
])
print("── 情境 A：多輪查詢＋引用")
status, answer, msgs = run(good, Q, tenant="flower")
print(f"  status={status}\n  {answer}")
assert status == "done" and set(CITE.findall(answer)) == {"kb-21", "kb-04"}
assert all("kb-31" not in m["content"] for m in msgs if m["role"] == "tool")   # 別家商家的政策從未外洩

# 劇本：模型憑印象回答，引用了沒檢索到的 chunk 與找不到出處的數字；修正一次後通過
sloppy = ScriptedModel([
    call("search_kb", "c1", query="鮮花 損壞 退貨"),
    say("可以，到貨 14 天內都能退貨 [kb-31]。"),
    say("可以。到貨損壞請於 24 小時內附照片申請，確認後全額退款 [kb-21]。"),
])
print("── 情境 B：引用驗證與修正")
status, answer, _ = run(sloppy, Q, tenant="flower")
print(f"  status={status}\n  {answer}")
assert status == "done" and "kb-31" not in answer

# 劇本：模型不肯修正 → 不硬答，轉真人
stubborn = ScriptedModel([call("search_kb", "c1", query="鮮花 退貨"), say("一定可以退 [kb-99]。"), say("真的可以 [kb-99]。")])
print("── 情境 C：無法 grounding")
status, answer, _ = run(stubborn, Q, tenant="flower")
print(f"  status={status}  {answer}")
assert status == "ungrounded"
```

```text
── 情境 A：多輪查詢＋引用
  step 1 search('鮮花 到貨損壞 退貨') → ['kb-21', 'kb-02', 'kb-10']
  step 2 search('退錢要等多久') → ['kb-07', 'kb-21', 'kb-10']
  step 3 search('退款時程 入帳') → ['kb-04', 'kb-10', 'kb-21']
  status=done
  可以。鮮花到貨損壞請於 24 小時內附照片申請，確認後全額退款，免寄回 [kb-21]。退款會在驗收後 3 個工作天內處理，信用卡退刷約 7 到 14 天入帳 [kb-04]。
── 情境 B：引用驗證與修正
  step 1 search('鮮花 損壞 退貨') → ['kb-21', 'kb-02', 'kb-10']
  step 2 驗證失敗 → ['kb-31 不在本次檢索結果中', '數字 14 找不到出處']
  status=done
  可以。到貨損壞請於 24 小時內附照片申請，確認後全額退款 [kb-21]。
── 情境 C：無法 grounding
  step 1 search('鮮花 退貨') → ['kb-21', 'kb-10', 'kb-04']
  step 2 驗證失敗 → ['kb-99 不在本次檢索結果中']
  status=ungrounded  這題我找不到可靠的依據，已轉給真人客服。
```

**情境 A** 完整重現了 11.7 節的時序圖。step 1 用「鮮花 到貨損壞 退貨」查詢，第一名就是商家自己的 `kb-21`，平台通則 `kb-02` 排第二；注意結果裡沒有 `kb-31`（阿鞋鞋舖），因為它在排序前就被租戶過濾排除了，程式中的 assert 也驗證了所有 tool 結果都不含它。step 2 用使用者原話「退錢要等多久」查詢，結果是發票、鮮花退貨、後台審核，沒有退款時程；劇本的第三步是一個函式，它檢查上一筆結果的標題裡有沒有「退款時程」，沒有才改寫查詢，這模擬了模型「讀了結果、判斷不夠、換說法」的行為。step 3 的「退款時程 入帳」第一名就是 `kb-04`。最後的答案引用 `[kb-21]` 與 `[kb-04]`，兩者都在本次檢索結果中，答案裡的數字 24、3、7、14 也都出現在被引用的段落裡，所以驗證通過，status 是 done。

**情境 B** 是 citation 驗證的價值所在。模型只查了一次，就憑印象回答「14 天內都能退貨 [kb-31]」，這是阿鞋鞋舖的規則，正好是 Maya 最擔心的跨租戶混淆。驗證器指出兩個問題：`kb-31` 不在本次檢索結果中、數字 14 找不到出處。harness 把這兩個問題回饋給模型，模型改寫後只引用 `kb-21`，驗證通過。**情境 C** 是模型堅持引用不存在的 `kb-99`，修正一次後仍然失敗，status 是 ungrounded，回應轉真人客服，而不是把沒有依據的答案送出去。

這個驗證器的限制要清楚：數字檢查是把所有被引用段落合在一起比對，沒有逐句對應，所以若模型把 `kb-04` 的「14 天」錯放到鮮花退貨那一句，只要兩段都被引用，檢查仍會通過；它也不檢查文字敘述的語意。正式系統可以要求逐句引用並檢查逐字引述，或加上 LLM judge。另外，`max_searches=4` 是這一題的搜尋上限，情境 A 用了三次；實務上的數值應該從 trace 中搜尋次數的分布來定，就像第 4 章訂步數上限一樣。

| 機制 | 程式中的位置 | 防止的事故 | 對應小節 |
|---|---|---|---|
| BM25 一路 | `BM25`、`search_kb` 的詞彙計分 | 錯誤碼、編號查不到（E-4012） | 11.4 |
| RRF 融合 | `rrf()`、`search_kb` 的 `fused` | 單一路的盲點；分數尺度不相容 | 11.6 |
| 排序前的租戶過濾 | `search_kb` 的 `allowed` | 跨租戶洩漏（阿鞋鞋舖的規則） | 11.8 |
| 多輪查詢與改寫 | 劇本中依結果決定是否重查 | 口語查不到（退錢 vs 退款） | 11.7 |
| citation 允許清單 | `seen`＋`verify()` | 捏造或跨租戶的引用 | 11.8 |
| 數字出處檢查 | `verify()` 的 `NUM` 比對 | 憑印象寫出的天數與金額 | 11.8 |
| 搜尋上限、修正上限 | `max_searches`、`max_repairs` | 無止境地重查或重寫 | 11.7、第 4 章 |
| 分級評估 | `recall_at_k`、`ndcg_at_k` | 無法證明改動有效 | 11.9 |

## 11.11 實務應用

檢索幾乎出現在每一種 agent 裡，但不同產品要的「找得到」完全不同。以下四個情境說明本章的技術怎麼依需求調整。

**情境一：電商客服知識庫（青鳥的主線）**。資料是平台說明文章加上數千家商家的自訂規則，量中等、更新頻繁、充滿精確字串（錯誤碼、物流商名稱、商品類別），而且**租戶隔離是硬性要求**。配置是：結構感知的 chunking、BM25 加向量的 hybrid 召回、小型 reranker、排序前的租戶過濾；對話第一輪先自動檢索一次以壓低延遲，模型覺得不夠再呼叫 `search_kb`。商家規則與平台通則衝突時，要在 metadata 標明優先順序（商家規則優先），並讓 search tool 的結果把商家規則排在前面或明確標示，而不是讓模型自己猜。citation 驗證失敗就轉真人。公開資料中，Intercom 的 Fin 研究網站有關於自建 reranker、檢索模型 fine-tune 與「structured, agentic RAG for ecommerce」等主題的文章，顯示專業客服 agent 廠商在檢索層投入很深（此處依標題判斷主題，細節以原文為準）。

**情境二：coding agent 搜尋程式碼庫**。程式碼的查詢大多是精確字串：函式名稱、錯誤訊息、設定鍵；檔案隨每次 commit 改變，維護向量索引的成本高、還容易過期。所以主流 coding agent 傾向讓 agent 直接用 grep、glob 與讀檔做 agentic search，Anthropic 公開說明 Claude Code 就是這樣做的。這種場景的「索引」是檔案系統本身，重點在 tool 設計：grep 結果要附檔名與行號、限制回傳行數、提示可以縮小範圍；並把專案的說明檔預先載入，讓 agent 知道去哪裡找。部分 coding 產品也會額外建立語意索引，作為 grep 之外的補充。

**情境三：法律與企業文件**。合約、判決、內部規章的特點是量大、篇幅長、條款之間互相引用，而且答案往往要整合多份文件。這類場景要用「小塊檢索、大塊閱讀」：小 chunk 精準命中條款，再回傳整節給模型閱讀；citation 要精確到段落或條號，因為使用者（律師、法務）一定會核對原文。權限更複雜：不是租戶層級，而是每份文件有自己的存取清單，必須在檢索時套用（第 44 章）。資料量極大時，Harvey 公開描述了另一種做法：把整個 data room 放進 REPL，讓 agent 寫程式遍歷與分派閱讀工作，這已經接近第 13 章的 code-as-action。

**情境四：營運 research agent**。青鳥的營運 research agent（第 40 章）要回答「上季退貨率上升的原因」，資料分散在內部 wiki、客服紀錄摘要與外部新聞。這是 agentic RAG 最能發揮的場景：問題開放、需要多輪搜尋、每輪的查詢依前一輪結果而定，甚至可以平行派出多個 subagent 各自搜尋。成本與延遲不是首要限制，**引用的可信度**才是：每個結論都要指回來源，並區分「資料直接寫的」與「agent 推論的」。OpenAI 的 Deep Research API 要求接入的 MCP server 提供 `search` 與 `fetch`，正是這類 agent 對檢索介面的典型需求。

| 產品類型 | 主要檢索方式 | chunking | 查詢策略 | 最重要的保證 |
|---|---|---|---|---|
| 電商客服 | hybrid＋rerank | 結構感知＋標題路徑 | 首輪自動檢索＋agent 補查 | 租戶隔離、citation 驗證、找不到就轉真人 |
| coding agent | grep、glob、讀檔 | 不切（檔案即單位） | agent 多輪 agentic search | 結果附檔名行號、輸出截斷 |
| 法律與企業文件 | hybrid＋rerank，小塊檢索大塊閱讀 | 依條款與章節 | agent 拆解與交叉引用 | 文件級權限、段落級 citation |
| research agent | web search＋內部 search／fetch | 依來源而定 | 多輪、可平行的 subagent | 每個結論可追溯、區分事實與推論 |

這張表的共同點是：檢索方式由資料的性質決定（精確字串多不多、量多大、改得多快），查詢策略由問題的性質決定（單一還是複合、延遲多敏感），而「最重要的保證」由風險決定。設計時先回答這三個問題，再選技術。

## 11.12 設計檢查清單

設計或審查一個檢索系統時，逐項回答下面的問題。

1. 資料來源有哪些？每個來源的更新頻率、刪除需求與權限模型是什麼？索引管線是否支援增量更新與刪除舊版本？
2. chunking 是否依文件結構切割，並在 chunk 中保留標題路徑等上下文？chunk 大小是否用評估集比較過，而不是隨手設定？
3. 每個 chunk 是否帶有穩定 id、tenant（或存取清單）、來源、更新時間與版本？
4. 權限過濾是在召回之前（pre-filter）還是之後（post-filter）？是否有測試證明其他租戶的 chunk 不會進入候選集？
5. 查詢中常出現的精確字串（代碼、編號、名稱）是否有詞彙檢索（BM25）覆蓋？
6. 若使用向量檢索，查詢與文件是否用同一個 embedding model 與版本？換模型的重建與切換流程是否寫好？
7. 多路召回的融合方式是什麼（RRF 或加權）？召回數量與最後放進 context 的數量各是多少，依據是什麼？
8. 要不要 rerank？用什麼模型、處理多少候選、延遲預算多少？
9. 檢索是一次性的步驟、agent 可呼叫的 tool，還是兩者混合？search tool 的結果是否帶 id、標題、更新日期、截斷標示與「沒有結果時的建議」？
10. 每題的搜尋次數是否有上限？達到上限時回填給模型的訊息是否可行動？
11. 答案的 citation 是否由 harness 驗證（只能引用本次檢索結果、關鍵數字與主張有出處）？驗證失敗時是修正、轉真人還是拒答？
12. 是否有帶分級標註的檢索評估集，涵蓋代碼查詢、口語查詢、複合問題與「知識庫沒有答案」的問題？每次改動是否都跑 recall@k 與 nDCG？
13. trace 中是否記錄每次檢索的查詢、命中的 chunk id、名次與索引版本，足以重現任何一個答案的依據？
14. 檢索內容是否被當成不可信的資料處理，不能直接觸發有副作用的 tool？

## 11.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 含錯誤碼、編號的問題答錯或亂編 | 只用向量檢索，embedding 對精確字串不敏感 | 查該題的檢索結果，看含有該字串的 chunk 排第幾 | 加上 BM25 並用 RRF 融合；字串型查詢可直接走精確比對 |
| 答案引用了別家商家的規則 | 權限過濾在取前 k 名之後（post-filter）或漏濾 | 對多租戶測試帳號跑檢索，檢查候選集是否含其他 tenant | 改成召回前過濾；citation 允許清單限定本次檢索結果；加入跨租戶回歸測試 |
| 政策改了，agent 還在講舊規則 | 增量更新沒有刪除舊版 chunk，新舊並存 | 以 `source` 查索引，看同一來源是否有多個版本 | 依來源整份重建並刪除舊 chunk；metadata 帶版本；檢索結果附更新日期 |
| recall 高，但答案仍然錯 | 生成端沒使用檢索內容，或段落太多、相關段落埋在中間 | 對照檢索結果與答案；量答案忠實度 | 減少放進 context 的段落、把最相關的放前面；加 citation 驗證；prompt 要求資料不足時說不知道 |
| 改了 chunking 之後有些題變好、有些變差，無法判斷 | 沒有評估集，只靠抽查 | 檢查是否有 qrels 與歷次指標 | 建立帶分級標註的評估集，每次改動跑 recall@k 與 nDCG，並看逐題差異 |
| agent 一題搜尋十幾次 | 沒有搜尋上限；結果格式讓模型無法判斷相關性 | 在 trace 中統計每題搜尋次數與查詢字串 | 設搜尋上限；結果附標題與日期；沒有結果時給改寫建議；沿用重複呼叫偵測 |
| 換了 embedding model 後全面變差 | 查詢與文件用不同模型編碼，或漏了模型要求的前綴 | 檢查索引與查詢端的模型版本與前綴設定 | 新模型建立新索引，雙寫並用評估集比較後再切換；查詢端與索引端版本綁定 |
| 每題延遲過高 | rerank 處理太多候選，或每題都走多輪 agentic 查詢 | 在 trace 中拆解各階段的延遲 | 縮小 rerank 候選數；首輪自動檢索、只在需要時讓 agent 補查；快取常見查詢（key 要含 tenant 與索引版本） |

## 本章重點整理

- RAG 的本質是「先找再答」：把模型外部、會變動、需要出處的知識，在需要時放進 context；它首先是一個搜尋問題。
- 大 context window 讓你「能塞」，不代表「該塞」；數萬段、多租戶、常更新的知識庫仍然需要檢索。
- 檢索系統分成離線的索引管線與線上的查詢管線，權限過濾、rerank 與 citation 驗證都是管線中不可省略的環節。
- chunking 決定檢索品質的上限：依文件結構切、不切斷句子、保留標題路徑，並讓每個 chunk 帶穩定 id、tenant、來源與版本。
- BM25 用 IDF、詞頻飽和與長度正規化計分，擅長代碼、編號與專有名詞，弱點是用詞不一致。
- embedding 讓意思相近的文字在向量空間中相近，擅長改寫與同義，弱點是精確字串；查詢與文件必須用同一個模型版本編碼。
- 本章用字元 n-gram 雜湊模擬向量，只有字面比對能力，用來展示管線機制，不代表真實 embedding 的效果。
- hybrid search 用 RRF 只依名次融合多路結果，不需要校準分數；rerank 用 cross-encoder 對少量候選精排。
- agentic RAG 把檢索變成 agent 可反覆呼叫的 tool，模型可以拆解問題、改寫查詢、依結果決定下一步，代價是延遲與成本。
- search tool 的結果要帶 id、標題、日期與截斷標示，沒有結果時要給可行動的改寫建議，並由 harness 設搜尋次數上限。
- citation 要由 harness 驗證：只能引用本次檢索結果、關鍵數字與主張要找得到出處，驗證失敗時修正或轉真人，不送出沒有依據的答案。
- 權限過濾必須放在排序之前，檢索內容要當成不可信的資料，避免跨租戶洩漏與 indirect prompt injection。
- 檢索品質要用帶分級標註的評估集量測：recall@k 看撈不撈得到，nDCG 看排序，MRR 只看第一個相關結果；檢索與生成要分開量。

## 延伸問答

> [!question]- Q1. 估算題：青鳥的平台說明中心約有 2,500 個 chunk，平均每個 300 tokens。全部放進 context 和用 agentic RAG 相比，每題的 input tokens 大約差多少？
> 全部放進 context 時，每題至少要付 2,500 × 300 ＝ 750,000 tokens 的知識庫內容，這已經接近甚至超過許多模型的 context 上限，而且還沒算商家自訂規則。就算有 prompt caching 能讓重複的前綴便宜很多，快取仍有存活時間與寫入成本，而且每家商家的規則不同，前綴無法跨商家共用；更重要的是 context rot：在七十多萬 tokens 裡找一句「鮮花損壞 24 小時內申請」，答案品質會比只給相關段落差。
>
> agentic RAG 的情況：假設 agent 平均查 2 次、每次回傳 3 段，每段截斷後約 150 tokens，加上查詢與 JSON 包裝，每次搜尋大約回填 600 tokens。但要記得第 4 章的累計效應：每多一輪 tool 呼叫，模型就要重讀一次歷史。若固定前綴（system 與 tools）是 3,000 tokens，三次模型呼叫的 input 大約是 3,000、3,600、4,200，總計約 10,800 tokens，比全部塞入少了將近兩個數量級。代價是多了兩輪模型呼叫的延遲，這就是為什麼青鳥在首輪先做一次自動檢索：大部分單純問題一輪就能答完。
>
> 估算的重點不是精確數字，而是結構：全部塞入的成本與知識庫大小成正比，檢索的成本與「查幾次、每次回傳多少」成正比，和知識庫大小幾乎無關。

> [!question]- Q2. BM25 和向量檢索該怎麼選？什麼情況下只用其中一種就夠了？
> 先看查詢裡有多少精確字串。錯誤碼、訂單編號、SKU、法條編號、函式名稱這類查詢，使用者要的就是「含有這個字串的那段」，BM25 一查就中而且可解釋；embedding 對這類字串不敏感，常把只差一個字元的代碼視為相同。反過來，使用者用口語、同義詞或不同語言提問，文件用的是正式用語，BM25 的字面比對會完全失效，這時需要向量檢索。
>
> 只用一種的合理情況有兩個。一是資料幾乎全是精確字串且用語統一，例如程式碼庫，grep 或 BM25 就夠，甚至不必建索引。二是查詢與文件的用語落差極大、幾乎不含專有名詞，例如開放式的閒聊或跨語言檢索，向量檢索是主力。但大多數企業知識庫兩種情況都有，hybrid 的額外成本只是多一路召回與一次 RRF，換來的是兩邊盲點互補，所以 hybrid 是預設，只用一種才需要理由。最後，選擇應該用自己的評估集決定：分別跑 BM25、向量、hybrid 的 recall@k，看逐題差異，而不是依直覺。

> [!question]- Q3. RRF 為什麼只用名次、不用分數？k 值該怎麼理解？
> 不同檢索器的分數尺度不同且不穩定：BM25 分數沒有上限，會隨查詢長度與語料統計而變；cosine 分數集中在窄區間，而且換一個 embedding model 分布就完全不同。直接相加會讓尺度大的那一路獨斷，11.6 節的例子中向量那一路幾乎沒有發言權。若要做分數融合，必須先正規化並用標註資料調權重，而且換模型、換語料都要重調。RRF 只用名次，任何「能排名」的檢索器都能直接加入，不需要校準，這是它成為預設的原因。
>
> k 控制名次之間的差距有多陡。第 r 名的貢獻是 1 / (k + r)；k 很小時（例如 1），第 1 名得 1/2、第 2 名得 1/3，差距很大，某一路的第一名幾乎能決定結果；k 取 60 時，第 1 名是 1/61、第 5 名是 1/65，差距很小，被多路同時排在前面的文件會勝出。所以 k 越大越重視「共識」，越小越重視「某一路的強烈意見」。60 是原論文的經驗值，實務上很少需要調，若要調就用評估集比較。RRF 的代價是丟掉了分數中的資訊：某一路非常確定的結果（例如 BM25 精確命中錯誤碼）不會因為分數特別高而被加權，必要時可以為這類查詢加規則，例如偵測到代碼格式時直接走精確比對。

> [!question]- Q4. 你在 production 看到：檢索評估集的 recall@5 是 0.92，但使用者回報答案錯誤的比例沒有下降。你會怎麼排查？
> 先把問題拆成兩層：答案錯，是因為正確段落沒被撈到（檢索錯），還是撈到了但模型沒用好（生成錯）。recall@5 高只代表評估集上撈得到，第一步要確認評估集和真實流量是否一致：從使用者回報的錯誤案例中抽樣，對每一題看 trace 裡實際的檢索結果。如果這些題的正確段落根本不在結果中，問題在於評估集沒有覆蓋真實的查詢分布（例如真實流量有大量口語或複合問題），要把這些案例加進評估集，並改善查詢改寫或召回。
>
> 如果正確段落在結果中但答案仍錯，問題在生成端。常見原因有：放進 context 的段落太多，相關段落被埋在中間；多段之間互相矛盾（新舊版本並存、商家規則與平台通則衝突），模型選錯；模型拿到資料後仍然用自己的知識補充。對應的修法是減少段落並把最相關的放前面、在 metadata 中標明優先順序並清掉舊版本、加 citation 驗證與數字出處檢查。最後，要建立答案忠實度與端到端正確率的評估，和檢索指標一起看，否則下次還會出現「檢索指標很好、使用者仍然不滿」的落差。

> [!question]- Q5. 程式找錯：下面這段多租戶檢索有兩個問題，請指出並說明後果。
> ```python
> def search(query, tenant, k=5):
>     hits = vector_index.search(query, k=k)          # 全庫搜尋前 k 名
>     return [h for h in hits if h.tenant == tenant]  # 再濾掉別家商家
> ```
> 第一個問題是 post-filter 造成召回率下降。全庫只取前 5 名，如果其中 4 名屬於別家商家，濾完只剩 1 筆，而該商家真正相關的第 6 到第 20 名永遠不會被看到。商家越多、彼此內容越相似，這個問題越嚴重；小商家的段落常常被大商家的相似內容擠出前 k 名，表現為「小商家的 agent 特別笨」。
>
> 第二個問題是過濾條件漏掉了平台共用的段落：`h.tenant == tenant` 會把 `tenant` 為 `*` 的平台通則全部濾掉。反過來，如果有人為了修這個問題把條件放寬，又很容易寫出讓別家商家資料通過的邏輯；而且資料在過濾之前就已經被讀出來，任何後續的 bug（例如記錄 debug log、快取結果）都可能造成洩漏。正確做法是 pre-filter：把 `tenant in (商家, "*")` 當成檢索的過濾條件交給索引，在召回階段就只搜尋允許的範圍，主流向量資料庫與搜尋引擎都支援帶過濾條件的搜尋。再加上兩道保險：citation 允許清單限定本次結果，以及跨租戶的回歸測試。

> [!question]- Q6. 青鳥的客服 agent 該用傳統 RAG 還是 agentic RAG？阿哲擔心延遲，老陳擔心答錯，你會怎麼取捨？
> 兩個擔心都合理，關鍵是不必二選一。從問題分布看：客服的問題大部分是單一主題的 FAQ，例如「店到店退貨運費誰付」，用原話查一次 hybrid 就能撈到答案，這類問題用傳統 RAG 最快，一次檢索加一次生成。少部分是複合問題或口語化的說法，例如小花花藝那題，一次檢索會失敗，需要 agent 拆解與改寫。
>
> 所以青鳥的設計是混合：第一輪由 harness 用使用者原話自動檢索，把前三段放進 context，大部分問題在這一輪就答完，延遲和傳統 RAG 相同；同時提供 `search_kb` tool，模型判斷資料不足時自己補查，代價只發生在需要的問題上。為了控制最壞情況，設定每題的搜尋上限與整體的時間上限，並在 UI 上顯示「正在查詢退款規則」這類進度，降低使用者對等待的感受。老陳擔心的答錯，則靠 citation 驗證與「找不到就轉真人」把關。上線後用 trace 統計多少比例的問題觸發了補查、補查後的正確率提升多少，再決定首輪檢索要取幾段、要不要調整策略。

> [!question]- Q7. 面試追問：設計一個服務數千家商家的知識庫檢索，你會用一個共用索引加過濾，還是每家商家一個索引？
> 兩種都可行，取捨在隔離強度、成本與運維。每家一個索引（或一個 namespace）的好處是隔離最強，刪除商家資料就是刪掉整個索引，也不會有 post-filter 的召回問題；缺點是數千個索引的運維成本高，小商家的索引很小卻仍有固定開銷，平台共用的文件還得在每個索引中複製一份或另外查一次再融合。共用索引加 metadata 過濾的好處是運維簡單、資源利用率高，平台文件只存一份；缺點是隔離完全依賴過濾邏輯的正確性，且必須確認所用的索引在帶過濾條件時仍能維持召回（部分 ANN 實作在過濾條件很嚴格時召回會下降）。
>
> 我的答案會是分層：平台共用文件一個索引；商家文件依規模分流，大商家獨立索引，小商家放在共用索引中以 tenant 過濾；查詢時兩路召回再融合，商家規則在排序或標示上優先。無論哪種，都要有三個保證：過濾在召回前、citation 允許清單、跨租戶回歸測試。面試時還要補充刪除流程（商家退出時所有衍生資料的清除）、索引更新的延遲目標，以及所有快取（語意快取、檢索結果快取）的 key 必須包含 tenant 與設定（索引）版本，否則快取會成為新的洩漏管道，也會在政策改版後回傳舊答案。

> [!question]- Q8. embedding model 要升級到新版本，怎麼做才不會讓線上品質出事？
> 先理解為什麼不能直接換：不同 embedding model 的向量空間互不相容，用新模型編碼的查詢去搜尋舊模型編碼的文件，結果基本上是隨機的。所以升級等於重建整個向量索引，而且查詢端與索引端必須同時切換。最常見的事故就是只換了其中一端。
>
> 安全的流程是：第一，用新模型建立一個新的索引，與舊索引並存，索引管線在過渡期雙寫，確保新文件兩邊都有。第二，用檢索評估集比較新舊索引的 recall@k 與 nDCG，並看逐題差異，特別是含代碼、口語與多語言的題目；若是 hybrid 系統，要比較的是整個 hybrid 結果，因為向量那一路變好不一定讓融合結果變好。第三，用 shadow traffic 讓一部分真實查詢同時跑新索引，記錄結果但不給使用者看，比較兩邊的差異與延遲。第四，以版本號綁定查詢端模型與索引，切換時一起切，並保留舊索引一段時間以便回滾。最後，在 trace 中記錄每次檢索使用的索引版本，第 29 章與第 36 章會把它當成和 prompt、模型同等級的版本化 artifact。

## 延伸閱讀

- Lewis et al.〈Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks〉（NeurIPS 2020）
- Robertson & Zaragoza〈The Probabilistic Relevance Framework: BM25 and Beyond〉（Foundations and Trends in Information Retrieval，2009）
- Cormack, Clarke & Büttcher〈Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods〉（SIGIR 2009）
- Järvelin & Kekäläinen〈Cumulated gain-based evaluation of IR techniques〉（ACM TOIS，2002）
- Malkov & Yashunin〈Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs〉（IEEE TPAMI）
- Liu et al.〈Lost in the Middle: How Language Models Use Long Contexts〉（TACL 2024）
- Anthropic〈Introducing Contextual Retrieval〉（2024）
- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
