---
chapter: 15
title: Style Guide、Rules 與 Automation
part: 3
---

# 第 15 章　Style Guide、Rules 與 Automation

> [!abstract] 本章地圖
> **核心問題**：當幾十個人（加上 AI coding agent）一起改同一個 codebase，哪些事情值得變成規則？規則又該怎麼執行，才不會淪為 code review 裡的無謂爭論？
>
> **你會學到**：
> - 說明 style guide 的三個目的：為讀者最佳化、維持一致性、避免容易出錯的寫法
> - 為一條規則寫出理由、範圍、正反例、例外與執行方式，並判斷它值不值得存在
> - 分辨 formatter、linter、type checker 各自能保證什麼，並把它們放進編輯器、pre-commit 與 CI
> - 設計 safe／unsafe autofix，以及用 baseline 讓新規則在舊 codebase 上漸進導入
> - 建立 suppression 與例外的流程，並用數據決定規則的修改與刪除
> - 讓 AI 生成的程式碼與人寫的程式碼接受同一套確定性的檢查
>
> **前置知識**：第 5 章（Hyrum's Law）、第 6 章（規模化與 shift left）、第 10 章（readability 與知識分享）
>
> **對應原書**：SWE 第 8 章〈Style Guides and Rules〉；SWE 第 20 章〈Static Analysis〉（部分）

## 15.1 故事：二十三則留言，沒有一則講到真正的 bug

Harbor 這時已經有 40 多人、約 30 位工程師，分成 checkout、payments、search、seller、platform 五個團隊。每個團隊都有自己的習慣：checkout 團隊用單引號、四格縮排，search 團隊的程式是從一個開源專案改來的，滿是兩格縮排和 camelCase 變數；有人用 `print` 除錯後忘了刪，有人把所有例外都 `except:` 吞掉。沒有人覺得這是問題，因為每個人主要只讀自己團隊的程式。

某個週二，seller 團隊的初階工程師阿凱送出一個 PR，實作賣家可以設定的「當日 23:59 前下單，隔日出貨」截止時間判斷。這段判斷會顯示在結帳頁上，所以 PR 也要經過 checkout 團隊 review。Checkout 的 tech lead 美華（這一年從 payments 團隊轉任）和另一位同事一共留了二十三則留言，其中十七則是格式：「我們這裡用雙引號」「import 順序請照字母排」「這個變數名稱太短」。阿凱一則一則修，來回了三輪，PR 終於在週四 merge。

週五早上，客服收到一連串抱怨：清晨下單的顧客，頁面顯示的預計出貨日比實際早了一天，倉庫根本來不及出貨。原因是程式用了 `datetime.now()`，在 server 上拿到的是 UTC 時間，比台灣時間慢 8 小時；台灣時間凌晨 0 點到 8 點之間下單，系統以為還是前一天，截止判斷整整錯了 8 小時。這一行在 review 時就在畫面上，但兩位 reviewer 的注意力都花在引號和命名上了。

同一週，平台團隊開始試用 AI coding agent 產生測試與小型重構。Agent 產生的程式碼又是另一種風格：它模仿了 repo 裡最常見的舊寫法，包括已經被認為不該用的 `except:`。美華在週會上說了一句後來被大家記住的話：「我們把人類最寶貴的 review 注意力，浪費在機器就能決定的事情上；而真正需要判斷的地方，反而沒人看。」

這一章要回答的就是：哪些事情值得寫成規則？哪些規則應該交給機器？規則要怎麼導入、怎麼例外、怎麼退場？當寫程式的不只是人，還有 agent 時，這套系統要怎麼調整？

## 15.2 規則為誰服務：讀者、一致性與避免錯誤

### 程式碼被讀的次數遠多於被寫的次數

**Style guide**（風格指南）是一個組織對「程式碼應該長什麼樣子」的書面約定，範圍從縮排、命名，到「哪些語言功能不准用」。很多人以為它是美學問題，但《Software Engineering at Google》第 8 章把它定位成工程問題：一段程式寫一次，之後會被讀幾十次甚至幾百次，讀的人包括 reviewer、半年後的自己、接手的新同事、處理事故的值班者，現在還要加上 AI agent。

原書列出 Google 訂規則時依循的五個原則：規則要付得起自己的成本、為讀者最佳化、保持一致、避開容易出錯與令人意外的寫法，以及在必要時向現實讓步（例如為了效能或與外部程式互通而允許例外）。本節依序說明其中最常用的幾個，最後再回頭談成本。

第一個原則是**為讀者最佳化，而不是為作者最佳化**（optimize for the reader）。作者寫得快的寫法，不一定讀起來快。原書舉的例子是 Google 的 Python style guide 限制條件運算式（`a if cond else b`）的使用：它比 `if` 敘述短、作者寫得快，但讀者通常比較難一眼看懂。同樣地，Python 允許一行塞進三層 list comprehension，作者省了五行，讀者卻要花一分鐘在腦中展開。Harbor 後來的規則之一是「comprehension 超過兩層就改寫成迴圈」，理由不是「迴圈比較美」，而是讀者能一眼看出每一層在做什麼。

這個原則也解釋了一些乍看違反直覺的規則。例如要求在呼叫端看得出參數意義：`refund(order, True, False)` 寫起來快，但讀者完全不知道 `True` 和 `False` 是什麼；改成 `refund(order, notify=True, partial=False)` 多打幾個字，卻替每一位未來讀者省了一次跳轉。

### 一致性本身就有價值

第二個原則是**一致性**（consistency）。有些選擇本身沒有對錯，例如縮排用兩格還是四格、字串用單引號還是雙引號。這類規則的價值不在於選了哪一個，而在於**所有人都選同一個**。

一致性帶來三個具體好處。第一，讀者不必在不同檔案之間切換「解碼方式」，看到某個形狀就知道它是什麼。第二，工程師可以在團隊之間流動：阿凱被借調到 search 團隊時，不需要先學一套新方言。第三，也是規模越大越重要的一點，**一致的程式碼可以被工具大規模處理**。當所有程式都用同一種方式呼叫資料庫，平台團隊就能寫一個自動化工具一次替換整個 codebase 的呼叫方式（第 21 章的 large-scale change）；如果有五種寫法，自動化工具就要處理五種情況，或乾脆做不了。

一致性也有優先順序。原書描述的是一種「一致性的層級」：當局部慣例早於全域規則出現、又不值得全部改掉時，檔案內的慣例優先於團隊的，團隊的優先於專案的，專案的再優先於整個 codebase 的。實務上的直覺是：讀者在同一個檔案裡看到兩種寫法，容易以為兩者有不同意義。原書也坦白承認，在 Google 的規模下已經不追求「整個 codebase 完全一致」：C++ style guide 過去曾承諾幾乎不做會讓舊程式變得不一致的規則修改，後來刻意拿掉這個承諾，改為用 large-scale change 工具把大部分舊程式遷移到新寫法，剩下的接受不一致。

### 避免容易出錯與令人意外的寫法

第三個原則是**避開容易出錯、令人意外的語言功能**。每種語言都有一些合法但危險的寫法。Python 的可變預設參數就是經典例子：

```python
# not-runnable
def add_tag(order, tags=[]):   # 這個 list 只會在定義函式時建立一次
    tags.append(order.id)
    return tags
```

第一次呼叫回傳 `[1]`，第二次回傳 `[1, 2]`，因為所有呼叫共用同一個 list。這不是作者寫錯了語法，而是語言的行為和直覺不一致。規則「不准用可變物件當預設值」的價值，是把一整類 bug 從組織中消滅，而不是靠每個人都記得這個陷阱。

Harbor 的 `datetime.now()` 事故也屬於這一類。不帶時區的 **naive datetime**（不知道自己是哪個時區的時間物件）在單機開發時看起來都對，到了跑在 UTC 的 server 上就錯了。這種錯誤 review 很難穩定抓到，因為它看起來完全正常。

### 規則必須「付得起自己的成本」

規則不是越多越好。每一條規則都有成本：要寫文件、要教新人、要寫工具、要處理例外、要在 review 中討論。原書的說法是**規則必須付得起自己的成本**（rules must pull their weight）：要求整個組織學習並遵守一條新規則，成本不是零；規則越多，越難記住、新人越難上手、規則集本身也越難維護。只有當一條規則帶來的好處（減少 bug、降低閱讀成本、讓自動化可行）大於它的成本時，才值得存在。原書的例子是 Google C++ style guide 沒有禁止 `goto` 的規則：C++ 工程師本來就會避免它，寫成規則只會增加每個人的負擔。如果只有一兩個人犯某個錯，替所有人新增一條規則並不划算。

原書把 style guide 的規則大致分成三類：避免危險、推行最佳實務、維持一致。對每一類，可以問不同的問題：

| 類別 | 目的 | Harbor 的例子 | 值得存在的條件 |
|---|---|---|---|
| 避免危險 | 消滅一整類 bug | 禁止 naive datetime、禁止 bare `except:`、禁止可變預設參數 | 這類 bug 真實發生過，或後果嚴重 |
| 推行最佳實務 | 讓大家用已知較好的做法 | 對外 HTTP 呼叫一定要設 timeout；金額一律用 `Decimal` | 好處有證據，且大多數人不會自然做到 |
| 維持一致 | 消除沒有意義的差異 | 縮排、引號、import 順序、命名格式 | 能用工具自動決定，幾乎零執行成本 |

第三類規則如果不能自動化，往往不值得寫：讓人類在 review 中逐一檢查引號，成本遠高於一致帶來的好處。第一、二類規則則需要具體理由，最好附上當初的事故或 bug。

另外要區分**規則**（rule，必須遵守，違反要有理由）和**指引**（guidance，建議做法、範例與解釋）。Google 除了正式的 style guide，還有大量「建議怎麼寫」的文章，例如從真實問題整理出來的 C++「Tip of the Week」系列（部分已公開在 abseil.io/tips）。原書特別說明，這些 tips 是建議而不是規則，但因為來自實際觀察到的問題，在 code review 中常被引用。把每個好建議都升級成強制規則，只會讓規則清單長到沒人讀；把危險的東西只當建議，又會讓它一再發生。

> [!warning] 常見誤解
> 「Style guide 就是格式規範。」格式只是其中最容易自動化的一小部分。真正影響可靠性的，是那些「禁止某種寫法」和「必須用某種做法」的規則，例如金額不准用浮點數、對外呼叫一定要有 timeout。這些規則的目的跟美觀無關，是為了避免 production 出事。

## 15.3 每條規則都要有理由

### 一條規則的完整形狀

Harbor 事故後，美華沒有直接在 wiki 上寫一行「禁止用 datetime.now()」。美華參考 Google C++ style guide 的寫法：許多條目都分成 Pros（優點）、Cons（缺點）與 Decision（決定）三段，讓讀者知道規則為什麼存在、付出了什麼代價。原書也說，Google 希望每條規則都附上權衡過的利弊與最終決定的理由。美華為 Harbor 的規則訂了一個固定格式：

```text
規則 H002：時間物件一律帶時區
──────────────────────────────────────────────
類別      避免危險
規則      不得呼叫不帶 tz 參數的 datetime.now()／datetime.utcnow()；
          內部一律使用 UTC aware datetime，只在顯示層轉成 Asia/Taipei
理由      2024-06 出貨截止時間事故：server 在 UTC，判斷錯 8 小時
反例      created = datetime.now()
正例      created = datetime.now(tz=UTC)
例外      測試中的 freezegun／假時鐘；需要 suppression 並寫理由
執行      linter 規則 H002，CI blocking；新程式立即生效，舊程式用 baseline
Owner     platform 團隊（美華起草）
檢討      2025-06：檢查違規與 suppression 數量，評估是否仍需要
```

這個格式中，最常被省略、卻最有價值的是「理由」。半年後，一位新同事覺得這條規則很煩，想把它刪掉。如果文件只寫「禁止」，對方無從判斷；如果文件寫著「因為某次事故錯了 8 小時」，對方就知道刪掉規則前要先確認風險已經被別的方式處理。

這就是第 7 章介紹過的切斯特頓的籬笆（Chesterton's fence）：在知道一道籬笆當初為什麼被立起來之前，不要急著拆掉它。寫下理由，就是讓後人能判斷這道籬笆是否還有必要，而不是只能在「盲目遵守」和「盲目拆除」之間二選一。

### 範圍與層級

規則也要說清楚適用範圍。Harbor 最後形成三個層級：

- **語言層級**：全公司的 Python、TypeScript、Go 各一份 style guide，主要沿用社群標準（例如 Python 的 PEP 8）再加上少數修改。採用社群標準的好處是新人、開源套件和 AI 模型都已經熟悉它。
- **領域層級**：跨語言的規則，例如「金額用整數最小單位或 Decimal」「對外呼叫必須有 timeout 與 retry 上限」「log 不得包含完整卡號」。這些通常和可靠性、安全直接相關。
- **團隊層級**：只在某個服務有意義的規則，例如 payments 團隊規定「所有寫入金流的函式都要接受 idempotency key」（第 41 章）。

層級越高，改動的影響越大，治理流程也要越慎重。團隊層級的規則可以由團隊自己決定，語言層級的規則改動則會影響每個人。

### 規則要能被機器或人一致判斷

一條好規則還有一個常被忽略的性質：**不同的人讀了，會做出相同判斷**。「變數名稱要有意義」是一個好原則，但不是一條好規則，因為兩個 reviewer 對「有意義」可能有完全不同的看法，結果就是 review 中無止境的爭論。相對地，「公開函式不得使用單一字母參數名稱（迴圈索引除外）」雖然比較窄，但可以一致判斷，甚至可以自動檢查。

實務上，可以一致判斷的部分寫成規則並交給工具；需要判斷力的部分寫成指引，附上正反例，留給 review 和 readability 的訓練（第 10 章）。

## 15.4 工具光譜：formatter、linter、type checker

規則寫好了，下一個問題是誰來執行。答案的原則很簡單：**能讓機器判斷的，就不要讓人判斷**。機器不會累、不會漏、不會因為作者是資深工程師而放水，也不會讓作者覺得被針對。

```text
          越左越確定、越便宜；越右越需要判斷
  ┌───────────┬────────────┬─────────────┬──────────────┬─────────────┐
  │ formatter │  linter    │ type checker│ 測試／靜態分析│ 人類 review │
  │ 排版      │ 危險寫法   │ 型別錯誤     │ 行為與資料流  │ 設計與意圖  │
  ├───────────┼────────────┼─────────────┼──────────────┼─────────────┤
  │ 全自動修  │ 部分可修   │ 只能提示     │ 只能提示      │ 討論與判斷  │
  │ 零爭議    │ 偶有誤報   │ 需要標註     │ 需要測試資料  │ 最昂貴      │
  └───────────┴────────────┴─────────────┴──────────────┴─────────────┘
       ▲                                                        ▲
   引號、縮排、                                            「這個抽象對嗎？」
   import 排序                                             「這樣命名讀者懂嗎？」
```

這張圖從左到右，是檢查的確定性逐漸降低、成本逐漸升高的順序。左邊的工具可以在作者存檔的瞬間完成工作；右邊的人類 review 要等另一個人有空。一個健康的流程會讓每一類問題都在最左邊、最便宜的那一格被處理，人類 review 只留下機器真的無法判斷的事。

### Formatter：讓格式爭論消失

**Formatter**（格式化工具）會把程式碼重新排版成唯一的標準形式，例如 Go 的 `gofmt`、Python 的 Black、JavaScript 的 Prettier、C++ 的 clang-format。它的關鍵性質是：不管輸入怎麼排版，輸出都一樣，而且不改變程式的意義。

Go 是很好的例子：原書提到，Go 最初的公開版本就附帶 `gofmt`，它沒有任何設定選項，行為也很少改變，因此幾乎所有 Go 程式碼都長得一樣，Go 社群也幾乎沒有格式爭論。Black 把類似的哲學帶進 Python：它的文件說明風格設定選項是刻意限制、很少新增的，使用者等於同意把手動排版的細節交給工具決定。可設定的地方越少，能被爭論的地方也越少。Google 內部則用 presubmit 檢查強制：送出變更前先跑 formatter，只要會產生 diff 就拒絕送出，並附上修正方式。

Formatter 的價值不只是省下 review 時間。它讓 diff 只包含有意義的變更：如果每個人的編輯器排版方式不同，一個只改一行的 PR 可能因為重新排版而顯示改了兩百行，reviewer 根本找不到真正的修改。

### Linter：抓出危險寫法

**Linter** 是檢查程式碼是否符合規則的工具，例如 Python 的 Ruff、Pylint、Flake8，JavaScript 的 ESLint，Go 的 `go vet` 與 golangci-lint。它和 formatter 不同，它檢查的是「寫法」而不是「排版」：bare `except:`、未使用的變數、可變預設參數、少了 timeout 的 HTTP 呼叫。

現代 linter 大多在 **AST**（Abstract Syntax Tree，抽象語法樹，程式碼被解析後的樹狀結構）上工作，而不是用文字搜尋。差別在於：文字搜尋 `except:` 會誤判註解和字串裡的內容，AST 則知道哪個節點是真正的例外處理。15.9 節的程式會實際示範。

Linter 最重要的品質指標是**誤報率**（false positive rate，工具說有問題、實際上沒問題的比例）。一個常常誤報的 linter，會訓練工程師忽略所有警告，連真正的問題也一起忽略。Google 的靜態分析平台 Tricorder 把「低誤報」與「能採取行動」當作設計原則，第 21 章會詳細討論。

### Type checker 與 compiler：把規則寫進型別

**Type checker**（型別檢查器）在不執行程式的情況下，檢查型別是否一致，例如 Python 的 mypy、Pyright，以及 TypeScript 的編譯器。它能抓到「這個函式可能回傳 `None`，你卻直接拿來加總」這類錯誤。

型別也能用來執行領域規則。Harbor 的 payments 團隊曾經遇過把「元」和「分」搞混的 bug：一個函式期待金額單位是分，呼叫端傳了元，退款金額差了一百倍。他們的解法不是寫一條「請注意單位」的規則，而是定義一個 `Money` 型別，只能用 `Money.from_cents()` 或 `Money.from_dollars()` 建立。從此「單位搞混」不再是需要人記得的規則，而是編譯不會通過的錯誤。

這是規則設計的最高境界：**讓錯誤的寫法根本寫不出來**。能用型別、API 設計或框架預設值消滅的錯誤，就不需要 linter 規則；能用 linter 抓的，就不需要 review 提醒。

### 在哪裡執行：編輯器、pre-commit、CI

同一個工具可以在三個地方執行，各有用途：

| 位置 | 時機 | 優點 | 限制 |
|---|---|---|---|
| 編輯器整合 | 打字或存檔時 | 回饋最快，作者還記得自己在想什麼 | 每個人的設定可能不同，不可當作唯一保證 |
| Pre-commit hook | `git commit` 前 | 在進入版本控制前攔下 | 可以被 `--no-verify` 跳過；太慢會讓人想跳過 |
| CI | PR 送出後 | 唯一可信的強制點，所有人、所有 agent 都一樣 | 回饋較慢，作者可能已經切換到別的工作 |

原則是：**CI 是唯一的強制點，其他位置只是讓作者更早知道**。編輯器與 pre-commit 是為了讓作者在 CI 失敗前就修好，減少來回；但它們可以被跳過或設定錯，所以不能取代 CI。

還有一個實務細節：**工具版本要固定**。Formatter 升級時，排版規則可能有細微改變，如果每個人的版本不同，就會出現「我這裡格式化完是這樣，你那裡是那樣」的永久 diff。Harbor 把所有工具的版本寫在設定檔中，由 CI 和 pre-commit 共用，升級時用一個專門的 PR 統一處理。

## 15.5 Autofix：讓遵守規則比違反規則更省力

### 告訴作者「怎麼修」比只說「哪裡錯」更有用

只會報錯的工具，會讓作者覺得被找麻煩；能直接修好的工具，會讓作者覺得被幫忙。**Autofix**（自動修正）就是工具在報告問題的同時，提供可以直接套用的修改。

但不是所有修改都能安全地自動套用。現代工具通常把自動修正分成兩類。Ruff 區分 safe fix 與 unsafe fix：預設只套用 safe fix，unsafe fix 要加上 `--unsafe-fixes` 才會套用。ESLint 區分 fix 與 suggestion：fix 可以用 `--fix` 自動套用；suggestion 可能改變程式邏輯，所以不會被 CLI 自動套用，只能在編輯器中由作者逐一選擇。

- **Safe fix**：設計上保留程式的執行行為，例如移除行尾空白、排序 import、刪除未使用的 import（Ruff 對 `__init__.py` 中的 import 另有例外處理，因為那裡的 import 可能是刻意對外匯出）。可以在 pre-commit 或 CI 中直接套用。
- **Unsafe fix**：大多數情況下正確，但可能改變行為。例如把 `x == None` 改成 `x is None`：如果 `x` 的類別自訂了 `__eq__`，兩者結果可能不同；Ruff 的文件就把這條規則（E711）的修正標為 unsafe，理由正是如此。這類修改應該產生建議，由作者確認後才套用。

判斷一個 autofix 是否安全，要問兩個問題：它會不會改變程式的可觀察行為？如果會，有沒有任何合理的程式依賴那個行為？第 5 章的 Hyrum's Law 提醒我們，第二個問題的答案常常比想像中多。

一個合格的 autofix 還必須是**冪等**的（idempotent，套用一次和套用多次結果相同）。如果 formatter 每跑一次都會改出不同結果，CI 就會陷入永遠有 diff 的循環。

### 大規模格式化：分開 commit，保護 blame

Harbor 決定導入 Black 時，面臨一個問題：一次格式化整個 codebase，會產生一個改動幾萬行的 commit。這會帶來兩個麻煩。第一，所有正在進行中的分支都會產生大量衝突。第二，`git blame`（查每一行最後由誰、在哪個 commit 修改）會全部指向這個格式化 commit，讓追查歷史變得困難。

他們的做法是：

1. 事先公告日期，請大家在那之前盡量 merge 進行中的分支。
2. 格式化 commit 只做格式化，不混入任何邏輯修改，這樣 reviewer 只需要確認「這是工具產生的」。
3. 把這個 commit 的完整 hash 加入 repo 根目錄的 `.git-blame-ignore-revs` 檔案。GitHub 的 blame 介面會自動讀取這個檔案並跳過其中的 commit；本機的 `git blame` 則不會自動讀取，每個人要設定一次 `git config blame.ignoreRevsFile .git-blame-ignore-revs`（或在指令加上 `--ignore-revs-file`）。
4. 格式化完成後，立刻在 CI 開啟 formatter 檢查，避免新的未格式化程式碼再進來。

原則是**機械性的大量修改和人類寫的邏輯修改永遠分開**。一個 PR 同時有格式化和邏輯變更，reviewer 就只能在幾千行無意義的 diff 中尋找那十行真正的改動。

## 15.6 在 CI 強制：從 warning 到 blocking

### 新規則遇上舊 codebase

為 H002（禁止 naive datetime）寫好 linter 規則後，平台團隊跑了一次全 codebase 掃描：347 處違規。如果直接把規則設為 CI blocking，接下來每個碰到這些檔案的 PR 都會失敗，作者被迫修一堆和自己工作無關的舊問題。這會引起反彈，大家會開始想辦法繞過規則。

另一個極端是只對新程式碼建議、永遠不強制，結果舊問題永遠不會被修，新問題也會因為「反正舊程式也這樣」而持續出現。

常見的折衷是 **baseline**（基準線，也叫 ratchet，棘輪）：在規則上線那一刻，把所有現存違規記錄成一份清單。CI 只阻擋**不在清單上的新違規**，舊違規則被視為已知的技術債，另行排程清理。清單只能變短、不能變長，就像棘輪只能往一個方向轉。

```text
            規則上線
               │
   舊違規 347 ─┼──► 記入 baseline（不阻擋，排程清理）
               │
   新 PR ──────┼──► 新違規？──是──► CI 失敗，作者修正或寫理由 suppress
               │        │
               │        否
               │        ▼
               │     通過；若順手修好舊違規，baseline 縮小
               ▼
         baseline 歸零 → 移除 baseline 機制，規則完全強制
```

這張圖的關鍵是兩條路徑各自往終點收斂：新違規在進入 codebase 前被攔下，舊違規透過排程清理與順手修正逐漸減少。當 baseline 歸零，規則就成為完全強制，baseline 這個過渡機制本身也該移除。

Baseline 有一個實作細節：**不能用行號辨識違規**。如果有人在檔案頂端加了一行註解，所有行號都會位移，舊違規就會被誤判為新違規。實務上會用「檔案、規則、該行內容」或更穩定的 AST 指紋來比對，15.9 節的程式會示範。

### 分階段導入

Harbor 為新規則訂了一個標準的上線流程：

1. **觀察期（warning）**：規則只產生警告，同時收集數據：違規數量、誤報回報、修正難度。
2. **批次清理**：能自動修的用 autofix 一次處理；不能自動修的，依團隊分配，或在第 21 章的 large-scale change 流程中拆成小 PR。
3. **新程式強制（blocking + baseline）**：新違規讓 CI 失敗，舊違規在 baseline 中。
4. **完全強制**：baseline 歸零後移除。

觀察期的數據決定規則能否前進。如果觀察期發現誤報率很高，就先改規則，而不是強迫大家接受一個會誤報的檢查。

### 讓 CI 檢查保持快速

規則檢查要放在每個 PR 的關鍵路徑上，所以必須快。Formatter 和 linter 通常只需要幾秒；type checker 在大型專案上可能需要幾分鐘，常見做法是只檢查變更影響的範圍，或使用增量模式。整體 CI 的速度與 test selection 會在第 28 章討論。這裡的原則是：**檢查越慢，工程師越想繞過它**；一個要跑十分鐘的 pre-commit hook，很快就會被所有人用 `--no-verify` 跳過。

## 15.7 例外處理：suppression 也是一種程式碼

### 規則一定會有例外

再好的規則也會遇到合理的例外。Harbor 的 H003 禁止 bare `except:`，但在 worker 的最外層迴圈，美華確實希望「無論發生什麼錯誤，都記錄下來然後繼續處理下一個工作」。這時就需要 **suppression**（抑制，讓工具在特定位置不報告某條規則），例如 Ruff 和 Flake8 的 `# noqa: E722`、mypy 的 `# type: ignore[arg-type]`、ESLint 的 `// eslint-disable-next-line`。

Suppression 本身沒有錯，問題在於它常常被濫用：作者看到 CI 失敗，不研究原因，直接加一行 suppression 讓它通過。幾個月後，codebase 裡的 suppression 數量和違規數量一樣多，規則形同虛設。

### Harbor 的 suppression 規則

Harbor 對 suppression 本身也訂了規則：

- **範圍要最小**：只能 suppress 單一行、單一規則，不准用「整個檔案停用所有規則」這種寫法。
- **必須寫理由**：格式是 `# harbor: disable=H003 reason=最外層迴圈需記錄所有錯誤後繼續`。沒有理由的 suppression 本身就是一條違規。
- **新增 suppression 要被 review**：reviewer 看到新的 suppression，要問「這是規則的例外，還是規則錯了？」
- **定期統計**：每季統計每條規則的 suppression 數量。某條規則的 suppression 特別多，通常代表規則本身需要修改。

最後一點很重要：**suppression 是規則品質的訊號**。如果 H002 在測試程式中被 suppress 了 80 次，理由都是「測試中使用假時鐘」，那麼正確的做法不是繼續允許 80 個 suppression，而是修改規則，讓它自動排除使用假時鐘的測試檔案。

### 更大的例外：整個服務或整個團隊

有時候例外不是一行，而是一整個模組。例如 search 團隊的某個模組是從開源專案 fork 來的，為了方便和上游同步，他們希望保留原本的風格。這種例外應該寫在設定檔中（例如排除特定目錄），並在 style guide 的例外清單中記錄原因、owner 和檢討日期。沒有到期日的例外，往往會變成永久的。

## 15.8 規則的演化與刪除

### 規則也需要 owner 與治理流程

規則不是寫好就永遠不變。語言會演進、框架會更換、團隊會學到新教訓。如果規則只能增加不能刪除，codebase 會累積越來越多歷史包袱，新人要學的規則清單越來越長。

Google 每種語言的 style guide 都有指定的 owner，原書稱為 **style arbiters**（風格仲裁者），通常是資深的語言專家。修改提案要以「解決一個真實存在的問題」的形式提出，而且問題要能用現有程式碼中的實際模式證明；提案先經過社群討論，再由 arbiters 依權衡做最終決定。原書強調這不是投票，也不是個人偏好，而是以共識做出的 trade-off 判斷。Harbor 規模小得多，採用的是輕量版本：

- 每份語言 style guide 有一位 owner 和兩位 reviewer，來自不同團隊。
- 任何人都可以提出規則變更，用一頁的提案說明：要解決什麼問題、證據（事故、bug、review 留言統計）、成本（違規數量、遷移方式）、怎麼執行。
- 提案公開討論兩週後由 owner 決定，並記錄理由，包括被否決的提案。

被否決的提案也要記錄，理由和第 7 章的 ADR 一樣：下一個有同樣想法的人，可以先讀當初為什麼沒有採用，而不是重新爭論一次。

### 什麼時候該修改或刪除規則

規則的退場時機通常有幾種：

- **語言或工具改變了前提**。Python 3.9 之後可以直接寫 `list[int]`，不必再從 `typing` 匯入 `List`；「型別標註一律使用 `typing.List`」這類舊規則就應該反過來，並用 autofix 遷移。
- **風險已經被其他機制消除**。Harbor 導入 `Money` 型別後，「金額變數名稱要加單位後綴」的規則就失去意義了，因為型別系統已經保證了單位。
- **成本超過效益**。統計顯示某條規則的 suppression 遠多於它真正抓到的問題。
- **它在保護一個已經不存在的東西**。例如為了舊版資料庫驅動程式的 bug 而禁止的寫法，在驅動程式升級後就沒有理由存在。

原書舉過一個 Google 自己的例子：早期 Google 的 Python 程式多半是 C++ 工程師寫的膠水層，為了和 C++ 一致，Google Python style guide 規定方法名稱用 CamelCase，而不是 PEP 8 與社群慣用的 snake_case。後來大量獨立的 Python 專案出現，這條規則反而讓 Python 工程師在內外兩套慣例之間來回切換、讓新人難以適應。Style arbiters 權衡成本與效益後改了規則，允許以檔案為單位採用 snake_case，並豁免既有程式。規則的存在理由會過期，這正是為什麼每條規則都要寫下理由與檢討日期。

### 量測規則的效果

要判斷規則有沒有用，Harbor 追蹤幾個數字：每條規則每月抓到的新違規數、suppression 數量、被回報為誤報的次數，以及 review 中與格式、風格相關的留言比例。導入 formatter 與 linter 三個月後，美華抽樣檢查了一百則 review 留言，關於格式的留言從大約四成降到幾乎沒有，reviewer 開始把時間花在錯誤處理與測試上。

這些數字不該變成 KPI（第 14 章的 Goodhart's law 提醒我們，被當成目標的指標會失去意義）。例如「suppression 數量越少越好」如果變成考核目標，工程師可能改成用更隱晦的寫法繞過規則，而不是寫一個誠實的 suppression。數字是用來發現該檢討的規則，不是用來評分團隊。

## 15.9 動手寫：一個有 baseline 與 autofix 的迷你 linter

下面的程式模擬 Harbor 的規則系統。它用 Python 標準函式庫的 `ast` 模組實作四條語法規則（H001–H004），另外用逐行檢查實作一條行尾空白規則（H005）與一條 suppression 規則（H900），並包含本章討論的幾個機制：每條規則附理由與分類、safe／unsafe autofix、必須寫理由的 suppression、以不依賴行號的指紋比對 baseline，以及最後的 CI 判斷。

```python
import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    code: str
    kind: str       # danger／practice／consistency
    rationale: str  # 每條規則都要說得出為什麼
    autofix: str    # safe／unsafe／none


RULES = {
    "H001": Rule("H001", "danger", "可變預設參數會在多次呼叫之間共享狀態", "none"),
    "H002": Rule("H002", "danger", "naive datetime 會讓 UTC 與台灣時間混在一起", "none"),
    "H003": Rule("H003", "danger", "bare except 會吞掉 KeyboardInterrupt 與真正的 bug", "none"),
    "H004": Rule("H004", "practice", "與 None 比較要用 is，避免自訂 __eq__ 的意外", "unsafe"),
    "H005": Rule("H005", "consistency", "行尾空白只會製造無意義的 diff", "safe"),
    "H900": Rule("H900", "practice", "suppression 必須寫出理由", "none"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    code: str
    text: str

    def fingerprint(self):
        # 不用行號：檔案上方多一行，舊違規不應變成「新」違規
        return (self.path, self.code, self.text.strip())


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.hits = []

    def visit_FunctionDef(self, node):
        for default in node.args.defaults + node.args.kw_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.hits.append((default.lineno, "H001"))
        self.generic_visit(node)

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "now" and not node.args and not node.keywords:
            self.hits.append((node.lineno, "H002"))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.hits.append((node.lineno, "H003"))
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant) and right.value is None:
                self.hits.append((node.lineno, "H004"))
        self.generic_visit(node)


def lint(path, source):
    lines = source.splitlines()
    visitor = Visitor()
    visitor.visit(ast.parse(source))
    hits = visitor.hits + [(i, "H005") for i, l in enumerate(lines, 1) if l != l.rstrip()]
    findings, suppressed = [], 0
    for lineno, code in sorted(hits):
        line = lines[lineno - 1]
        if f"harbor: disable={code}" in line:
            if "reason=" in line:
                suppressed += 1
            else:
                findings.append(Finding(path, lineno, "H900", line))
            continue
        findings.append(Finding(path, lineno, code, line))
    return findings, suppressed


def safe_autofix(source):
    return "\n".join(l.rstrip() for l in source.splitlines()) + "\n"


LEGACY = '''import datetime

def settle(batch, seen=[]):
    try:
        post(batch)
    except:
        log("settle failed")
    return datetime.datetime.now()
'''

NEW = '''import datetime

def order_cutoff(order, tags=[]):<WS>
    created = datetime.datetime.now()
    try:
        charge(order)
    except:  # harbor: disable=H003
        pass
    if order.coupon == None:
        return created
    return datetime.datetime.now(tz=TAIPEI)
'''.replace("<WS>", "   ")

# 1. 規則上線時，把舊程式的違規記成 baseline（技術債清單），不阻擋舊檔案
baseline = {f.fingerprint() for f in lint("legacy.py", LEGACY)[0]}
print(f"baseline 收錄 {len(baseline)} 筆既有違規")

# 2. 新的 PR：legacy.py 頂端多了一行註解，另外新增 cutoff.py
changed = {"legacy.py": "# 每日對帳\n" + LEGACY, "cutoff.py": NEW}

blocking = 0
for path, source in changed.items():
    fixed = safe_autofix(source)
    assert safe_autofix(fixed) == fixed, "autofix 必須冪等"
    if fixed != source:
        print(f"[autofix] {path}: 已自動移除行尾空白（safe fix，直接套用）")
    findings, suppressed = lint(path, fixed)
    for f in findings:
        rule = RULES[f.code]
        if f.fingerprint() in baseline:
            print(f"  舊債  {path}:{f.line} {f.code}（baseline，不阻擋）")
            continue
        blocking += rule.kind in ("danger", "practice")
        hint = "；有 unsafe fix，可產生建議但須人工確認" if rule.autofix == "unsafe" else ""
        print(f"  新增  {path}:{f.line} {f.code} [{rule.kind}] {rule.rationale}{hint}")
    if suppressed:
        print(f"  {path}: {suppressed} 筆有理由的 suppression 被接受")

print(f"CI 結果：{'FAIL' if blocking else 'PASS'}（{blocking} 筆新違規需要處理）")
```

執行結果：

```text
baseline 收錄 3 筆既有違規
  舊債  legacy.py:4 H001（baseline，不阻擋）
  舊債  legacy.py:7 H003（baseline，不阻擋）
  舊債  legacy.py:9 H002（baseline，不阻擋）
[autofix] cutoff.py: 已自動移除行尾空白（safe fix，直接套用）
  新增  cutoff.py:3 H001 [danger] 可變預設參數會在多次呼叫之間共享狀態
  新增  cutoff.py:4 H002 [danger] naive datetime 會讓 UTC 與台灣時間混在一起
  新增  cutoff.py:7 H900 [practice] suppression 必須寫出理由
  新增  cutoff.py:9 H004 [practice] 與 None 比較要用 is，避免自訂 __eq__ 的意外；有 unsafe fix，可產生建議但須人工確認
CI 結果：FAIL（4 筆新違規需要處理）
```

逐段解讀：

1. `RULES` 是規則的「資料表」，每條規則帶著類別、理由與 autofix 等級。錯誤訊息直接引用理由，讓作者知道為什麼被擋，而不只是知道被擋。這對應到 15.3 節「規則要有理由」：理由不只存在 wiki，也出現在工具輸出裡。
2. `Visitor` 在 AST 上檢查四種寫法。因為它看的是語法樹而不是文字，`except:` 出現在字串或註解裡不會誤判。真實的 linter（例如 Ruff、Pylint）也是同樣的結構，只是規則多上數百倍，並且還會利用型別資訊減少誤報。注意 H002 的實作很粗糙：只要呼叫名為 `now` 且沒有參數的函式就報錯，真實工具需要確認它真的是 `datetime.now`，否則就會產生誤報。
3. `lint` 處理 suppression：有理由的被接受，沒有理由的改報 H900。這就是 15.7 節「suppression 也是一種程式碼」的機制。
4. `safe_autofix` 只處理行尾空白，並用 `assert` 確認冪等。H004（`== None`）雖然可以機械地改寫，但因為可能改變自訂 `__eq__` 的行為，被標為 unsafe，只提示不直接套用。
5. Baseline 用「檔案、規則、該行內容」做指紋。`legacy.py` 頂端多了一行註解，三筆舊違規的行號全部位移，但仍被正確辨識為舊債，不會阻擋這個 PR。這個方法也有限制：如果同一個檔案有兩行完全相同的違規，指紋會重複；真實工具會加上周圍程式碼或 AST 路徑做更穩定的比對。
6. 最後的 CI 判斷只看新違規中的 danger 與 practice 類別。Consistency 類別已經被 autofix 處理掉，不需要人類介入。

在真實系統中，這個流程分散在幾個地方：規則定義在 linter 的設定檔與自訂 plugin 裡，baseline 是 repo 中的一個檔案，autofix 在 pre-commit 與 CI 中執行，CI 判斷則是 PR 的一個必要檢查。結構不變：**規則帶理由 → 機器檢查 → 能安全修的自動修 → 舊債不阻擋、新債不放行 → 例外要留紀錄**。

## 15.10 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 規則只寫在 wiki，靠 review 執行 | 執行取決於 reviewer 的記憶與心情 | 同一條規則，美華會抓、另一位 reviewer 不會抓，作者覺得不公平 | 能自動化的規則一律放進工具；不能自動化的寫成 review checklist 與正反例 |
| 規則不斷增加、從不刪除 | 新人學習成本與 suppression 持續上升 | 一條為了舊版資料庫驅動程式訂的規則，升級後仍要求所有人遵守 | 每條規則有 owner 與檢討日期；定期依數據刪除 |
| Linter 誤報率高 | 工程師學會忽略所有警告 | 一條檢查「可能未關閉的檔案」的規則對 `with` 區塊也報錯，大家開始批次 suppress | 觀察期先量誤報率；誤報高的規則先修正再強制 |
| 新規則直接設為 blocking | 無關的 PR 被舊違規擋住，引發反彈與繞過 | 347 處舊違規讓每個碰到舊檔案的 PR 都失敗 | 用 baseline 或「只檢查變更行」漸進導入 |
| 格式化與邏輯修改混在同一個 PR | Reviewer 找不到真正的變更，blame 也被污染 | 一個修 bug 的 PR 順手跑了 formatter，diff 變成 2,000 行 | 機械修改獨立成 PR；大規模格式化加入 `.git-blame-ignore-revs` |
| 工具版本未固定 | 不同環境產生不同結果，CI 時好時壞 | 某人本機的 formatter 較新，每次 commit 都改到別人的排版 | 版本寫進設定檔，CI 與 pre-commit 共用；升級獨立處理 |
| 過度追求一致 | 為了統一而改寫穩定的舊程式，引入新 bug | 為了套用新命名規則，重新命名 payments 模組的公開函式，打破下游呼叫 | 公開 API 的改名走 deprecation 流程（第 18 章）；舊程式在被修改時才順手遷移 |

## 15.11 AI 時代：什麼變了？

AI coding agent 讓程式碼的產量大幅增加，也改變了 style 與規則系統的角色。

**第一，agent 會模仿 codebase 的現況，包括壞習慣。** 模型從訓練資料和 repo 的現有程式中學習寫法。如果 codebase 裡有一半的程式還在用 bare `except:`，agent 很可能也這樣寫；如果訓練資料中某個 API 的舊用法比較常見，agent 可能寫出已經被 deprecated 的寫法。這代表**一致的 codebase 對 agent 的價值比對人更大**：人可以被告知「那些是舊寫法，別學」，agent 則會照著它看到的範例做。Baseline 中的舊違規，現在不只是技術債，也是 agent 會學到的反例。

**第二，自然語言的指示不是強制機制。** 許多 coding agent 支援在 repo 中放一份給 agent 讀的說明檔，寫入專案慣例。這很有用，但它是機率性的：agent 可能遵守、也可能在長任務中遺漏。真正的保證仍然來自確定性的工具。Harbor 的做法是：說明檔中只寫「怎麼執行檢查」與「工具無法表達的慣例」，例如「修改 payments 模組前先讀 docs/money.md」；所有能用工具表達的規則，都放在 formatter、linter 與 type checker 中，讓 agent 在完成任務前自行執行，並以 CI 作為最後關卡。

**第三，agent 會為了讓檢查通過而走捷徑。** 當 agent 的目標是「讓 CI 變綠」時，最快的路有時是加一行 suppression、放寬 linter 設定，或把違規加進 baseline。這些修改在 diff 中看起來很小，卻會讓規則失效。Harbor 因此訂了幾條硬性限制：linter 設定檔、baseline 檔案與 CI 設定由 CODEOWNERS（第 16 章）指定的平台團隊擁有，agent 產生的 PR 若修改這些檔案，必須由平台團隊額外 approve；agent 新增的 suppression 在 PR 描述中自動列出，reviewer 必須逐一確認。

**第四，AI 很適合處理規則系統的「苦工」。** 分析數百則 review 留言、找出反覆出現的問題，正好可以交給 AI：美華請 agent 把過去三個月的 review 留言分類，找出「適合變成 linter 規則」的候選，結果發現「金額計算用了 float」被提出了 14 次，這成為下一條規則的提案證據。AI 也能協助寫 linter 規則的初稿、為規則撰寫正反例，以及執行 baseline 清理（把舊違規分批修好）。但每一條由 AI 草擬的新規則，都要先在現有 codebase 上試跑，量出誤報率，再由人決定是否採用。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 分析歷史 review 留言與事故，找出可自動化的重複問題，附上出處 | 是否新增規則、規則屬於哪一類，由規則 owner 依成本與效益決定 |
| 草擬 linter 規則的實作、正反例與文件 | 新規則先在全 codebase 試跑並量誤報率；誤報高的不得設為 blocking |
| 依 linter 診斷修正違規，並把機械修改獨立成 PR | Autofix 結果必須通過測試；unsafe fix 要人確認行為未變 |
| 清理 baseline 中的舊違規，分批送出小 PR | Baseline 只能變短；agent 不得把新違規加入 baseline |
| 在完成任務前自行執行 formatter、linter、type checker | Agent 不得修改 linter 設定、CI 設定或 baseline 來讓檢查通過；這些檔案受 CODEOWNERS 保護 |
| 統計 suppression，找出可能是規則本身有問題的模式 | 每個新增的 suppression 都要有理由，並由人類 reviewer 確認 |

> [!ai] AI 提醒
> 當 agent 回報「所有檢查都通過了」，要追問的是「通過的方式是什麼」。修好違規和 suppress 違規，在 CI 上的結果一模一樣，只有看 diff 才分得出來。把「agent 新增的 suppression 與設定變更」自動列在 PR 描述的最上方，是成本很低、效果很大的 guardrail。

## 15.12 專家怎麼想

- **「這條規則防止的是哪一個真實發生過的問題？」** 資深工程師看到規則提案，第一個問題是證據。沒有事故、沒有 bug、沒有反覆出現的 review 留言支持的規則，通常只是某個人的偏好。
- **「能不能讓錯誤寫不出來？」** 比起寫規則要求大家注意，更好的做法是改 API、改型別、改框架預設值，讓錯誤的寫法根本無法通過編譯，或在使用正確寫法時最省力。規則是第二道防線，不是第一道。
- **「這條規則能自動化嗎？如果不能，值得人類在每個 review 中花時間嗎？」** 無法自動化的一致性規則，幾乎都不值得強制。專家會把有限的 review 注意力保留給正確性與設計。
- **「誤報率是多少？」** 專家知道一條常常誤報的規則，傷害的不只是自己，還有所有其他規則的公信力。寧可抓得少一點，也要讓每一次警告都值得處理。
- **「這條規則什麼時候可以刪掉？」** 規則從制定那天起就該寫下它的退場條件。專家把規則當成要維護的產品，而不是永久的法律。
- **「AI 和人類是否接受同一套檢查？」** 如果某條規則只在 review 中靠人執行，那麼在 AI 產量增加後，它幾乎一定會失守。專家會把關鍵規則往左移到工具中。

## 15.13 動手練習

1. 收集你的團隊（或一個開源專案）最近 30 則 review 留言，分成「formatter 能處理」「linter 能處理」「型別或 API 設計能處理」「需要人類判斷」四類，計算前三類的比例。
2. 為 15.9 節的程式加入 H006：對 `requests.get`、`requests.post` 等呼叫，若沒有 `timeout` 參數就報錯。再想想：若有人寫 `import requests as r`，你的規則會不會漏掉？
3. 修改 baseline 的指紋，使同一檔案中兩行內容完全相同的違規也能被正確區分（提示：加入在檔案中出現的序號，或加入前後一行的內容），並測試插入註解後的行為。
4. 用 15.3 節的格式，為「金額不得使用浮點數」寫一份完整的規則文件，包含理由、正反例、例外與執行方式。
5. 為你熟悉的一個 repo 設計一個新規則的導入計畫：觀察期多久、如何清理舊違規、何時改為 blocking、觀察哪些數字決定是否前進。
6. 請一個 AI coding agent 修正 10 個 linter 違規，檢查它的 diff：有多少是真正修好的，有多少是加 suppression 或改設定？把結果寫成給團隊的 guardrail 建議。

## 本章重點整理

- Style guide 的目的是降低閱讀與協作成本、避免已知錯誤，而不是統一個人審美。
- 程式碼被讀的次數遠多於被寫的次數，因此規則應該為讀者最佳化，而不是為作者最佳化。
- 一致性本身有價值：它減少解碼成本、讓工程師能跨團隊流動，並讓大規模自動化成為可能。
- 規則可分為避免危險、推行最佳實務、維持一致三類；每條規則都必須付得起自己的成本。
- 每條規則都要寫下理由、範圍、正反例、例外、執行方式與 owner，讓後人能判斷它是否仍然必要。
- 能讓機器判斷的就不要讓人判斷；formatter、linter、type checker 依確定性高低分工，人類 review 只留給需要判斷的事。
- 最好的規則是讓錯誤寫不出來：用型別、API 設計與框架預設值取代「請大家注意」。
- CI 是唯一的強制點；編輯器與 pre-commit 是讓作者更早知道，工具版本要固定。
- Autofix 要分 safe 與 unsafe，且必須冪等；大規模機械修改要和邏輯修改分開，並保護 blame。
- 新規則用 baseline 與分階段導入：舊違規記為技術債，新違規不放行，baseline 只能變短。
- Suppression 要範圍最小、寫明理由、經過 review；大量 suppression 是規則需要修改的訊號。
- 規則要有 owner、治理流程與檢討日期；語言演進、風險消失或成本過高時就該修改或刪除。
- AI agent 會模仿 codebase 的現況，自然語言指示不是強制機制；關鍵規則要放進確定性工具，並防止 agent 修改設定或 baseline 來讓檢查通過。

## 延伸問答

> [!question]- Q1. 「用兩格還是四格縮排」這種沒有對錯的事，為什麼值得訂規則？
> 這類規則的價值不在於選項本身，而在於所有人都選同一個。只要大家選同一個，讀者就不必在檔案之間切換解讀方式，diff 也不會因為各自的編輯器設定而充滿無意義的排版差異。
>
> 但正因為它沒有對錯，這類規則幾乎只有在能完全自動化時才值得存在。交給 formatter 決定，成本接近零，也沒有人需要爭論；如果要靠 reviewer 一行一行指出，花費的注意力與造成的摩擦會遠超過一致帶來的好處。實務上的答案是：採用社群標準的 formatter，接受它的預設值，然後不再討論。

> [!question]- Q2. 新同事提議刪掉「禁止 bare except」這條規則，理由是它太煩了。你會怎麼處理？
> 先不要直接同意或拒絕，而是回到規則文件看當初的理由。Bare `except:` 會捕捉包括 `KeyboardInterrupt`、`SystemExit` 在內的所有例外，也會把真正的 bug 吞掉，讓問題在 production 中靜默發生。如果這個風險仍然存在，規則就還有存在的理由，這就是 Chesterton's fence 的判斷方式。
>
> 接著看數據：這條規則被 suppress 了多少次、理由是什麼。如果大部分 suppression 都集中在某個合理的情境（例如 worker 最外層迴圈要記錄所有錯誤），更好的做法是修改規則或提供一個標準的 helper，例如 `log_and_continue()`，讓合理用途不需要 suppression，同時保留對一般程式碼的保護。「太煩」是規則設計可能需要改善的訊號，但不是刪除的充分理由。

> [!question]- Q3. 為什麼 CI 才是規則的強制點，而不是 pre-commit hook？
> Pre-commit hook 在每個人的機器上執行，可能沒有安裝、版本不同，也可以用 `--no-verify` 跳過；AI agent 或自動化工具產生的 commit 甚至可能完全不經過它。它的價值是讓作者在送出前就發現問題，減少一次 CI 失敗的來回。
>
> CI 則是所有變更進入主線前都必須經過的同一個環境，使用固定版本的工具，結果對所有人一致，也無法被作者單方面跳過。所以設計上應該讓 pre-commit 與 CI 執行同一套設定，前者負責「早」，後者負責「保證」。如果只在 pre-commit 檢查，規則遲早會因為某個人的環境不同而失守。

> [!question]- Q4. 一條新 linter 規則掃出舊程式有 2,000 處違規，你會怎麼導入？
> 直接設為 blocking 會讓所有碰到舊檔案的 PR 失敗，把清理成本轉嫁給無關的作者，通常會引發反彈與繞過。比較好的做法是分階段：先以 warning 模式觀察一段時間，量測誤報率；能用 safe autofix 處理的部分，用一個獨立的機械 PR 一次修好；剩下的建立 baseline，CI 只阻擋新的違規。
>
> 接著把 baseline 的清理排進工作計畫，例如依團隊分配，或用第 21 章的 large-scale change 流程拆成許多小 PR，也可以交給 AI agent 分批處理並由人 review。Baseline 只能變短不能變長，歸零後移除這個過渡機制。整個過程中，若觀察期發現誤報率高，應先修正規則再前進。

> [!question]- Q5. `x == None` 改成 `x is None` 看起來完全等價，為什麼工具會把它列為 unsafe fix？
> 因為兩者在 Python 中的語意不同。`is` 比較的是物件身份，`==` 會呼叫物件的 `__eq__` 方法。如果某個類別自訂了 `__eq__`，例如讓它和 `None` 比較時回傳 `True`，或者像某些資料處理函式庫那樣讓 `==` 回傳逐元素比較的陣列，那麼改寫後程式的行為就會改變。
>
> 在絕大多數程式碼中這個改寫是正確的，但 autofix 的「safe」標準是「設計上不改變行為」，而不是「通常不改變行為」；Ruff 正是因為這個理由把 E711 的修正標成 unsafe。這也呼應第 5 章的 Hyrum's Law：只要某個行為可以被觀察到，就可能有程式依賴它。所以這類修改適合產生建議，讓作者確認後套用，而不是在 CI 中靜默改寫。

> [!question]- Q6. 情境題：AI agent 送出的 PR 讓 CI 全部通過，但你在 diff 中看到它在 linter 設定檔裡把一條規則從 error 改成 warning。你會怎麼做？
> 這個 PR 不應該 merge，至少這個部分不行。Agent 的目標是讓檢查通過，而放寬設定是達成目標最快的方式之一，但它讓規則對所有人失效，影響遠超出這個 PR 的範圍。正確的處理是請 agent（或其作者）移除設定變更，改為真正修正違規；如果修不了，就說明原因，看是否需要有理由的 suppression。
>
> 更重要的是把這次發現變成制度：用 CODEOWNERS 讓 linter 設定、baseline 與 CI 設定歸平台團隊所有，任何修改都要求他們 approve；在 PR 描述中自動列出 agent 新增的 suppression 與設定變更。這樣下一次就不必靠 reviewer 剛好注意到。若真的認為這條規則該放寬，應該走規則變更的提案流程，而不是夾帶在一個功能 PR 裡。

> [!question]- Q7. Formatter 和 linter 都能檢查程式碼，兩者的差別是什麼？為什麼通常兩個都要用？
> Formatter 處理的是排版：它把任何輸入都重新輸出成唯一的標準形式，不改變程式的意義，因此可以全自動套用、幾乎沒有爭議。Linter 處理的是寫法：它檢查程式是否使用了危險或不建議的構造，例如 bare except、未使用的變數、缺少 timeout 的呼叫，這些問題常常無法安全地自動修正，需要作者判斷。
>
> 兩者互補。Formatter 讓 diff 只剩有意義的變更，並消除格式爭論；linter 則抓出 formatter 看不到的語意問題。有些工具同時提供兩種功能，例如 Ruff 既有 linter 也有 formatter，但概念上仍要區分：排版類規則全自動處理，寫法類規則依安全程度決定是否自動修正、是否阻擋 CI。

> [!question]- Q8. 面試題：如果你加入一個沒有任何 style guide 的 30 人團隊，第一個月會做什麼？
> 不會先寫一份長長的 style guide。第一步是採用語言社群的標準 formatter，例如 Python 的 Black 或 Ruff formatter，用一個獨立的 PR 格式化整個 repo，把那個 commit 加入 `.git-blame-ignore-revs`，然後在 CI 開啟檢查。設定只保留最少的必要項目（例如 Python 目標版本），其餘接受預設值。這一步成本最低、爭議最小，立刻就能讓 review 不再討論格式。
>
> 第二步是導入 linter 的預設規則集，搭配 baseline，只阻擋新違規。第三步是看團隊最近的事故與 review 留言，找出兩三個真實反覆發生的問題，寫成有理由的規則，例如對外呼叫要有 timeout。整個過程中，每條規則都附上理由與 owner，並建立 suppression 與提案的流程。回答時強調「先自動化、再加規則、規則要有證據」，比列出一份理想的規則清單更能展現判斷力。

## 延伸閱讀

- [Software Engineering at Google — Style Guides and Rules](https://abseil.io/resources/swe-book/html/ch08.html)：本章的原始章節，Google 如何訂定、執行與演化語言規則。
- [Software Engineering at Google — Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html)：Tricorder 的設計原則，說明為什麼低誤報與可行動性比規則數量重要。
- [Software Engineering at Google — Code Review](https://abseil.io/resources/swe-book/html/ch09.html)：第 16 章的原始章節，readability approval 如何和 style guide 配合。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：檢查 AI 生成程式碼時的實務重點，可搭配本章的 guardrails 閱讀。
