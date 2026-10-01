---
chapter: 21
title: Code Search、Static Analysis 與 Large-Scale Changes
part: 3
---

# 第 21 章　Code Search、Static Analysis 與 Large-Scale Changes

> [!abstract] 本章地圖
> **核心問題**：當同一個錯誤散落在幾十個服務、幾百個呼叫點時，要怎麼找得完整、擋住新的、再安全地把舊的全部改掉？
>
> **你會學到**：
> - 說明 code search 解決什麼問題，以及文字搜尋、symbol 索引、AST、型別資訊與 runtime 資料各自能看到與看不到什麼
> - 理解 static analysis 的能力邊界，並用 Tricorder 的原則（低 effective false positive、可行動、整合進工作流）設計團隊的檢查
> - 定義 large-scale change（LSC），說明它為什麼無法一次原子提交，以及「由專家集中遷移」為何比「請每個團隊自己改」便宜
> - 走過一次 LSC 的完整流程：提案、產生變更、依 owner 拆分、自動測試、全域 approver、清理與防止回退
> - 寫出保守、可重跑、保留排版的 codemod，並把「機械性變更」和「需要判斷的例外」分開
> - 設計 AI agent 參與大規模變更時的分工、權限與驗證方式
>
> **前置知識**：第 15 章（formatter、linter 與規則自動化）、第 18 章（deprecation）、第 19 章（monorepo、trunk-based development 與小批次）
>
> **對應原書**：SWE 第 17 章〈Code Search〉、第 20 章〈Static Analysis〉、第 22 章〈Large-Scale Changes〉

## 21.1 故事：一行少了 timeout 的程式碼

Harbor 成長到 40 位工程師、五個團隊（checkout、payments、search、seller、platform）的那年秋天，發生了一次讓所有人印象深刻的事故。inventory 服務會向供應商查詢即時庫存，那段程式碼是三年前寫的：`requests.get(url)`，沒有設定 timeout。某天晚上供應商的 API 沒有回錯誤，而是「接受連線、然後什麼都不回」。Python 的 requests 函式庫在沒有 timeout 時會一直等下去，inventory 的 worker thread 一個接一個卡住，checkout 呼叫 inventory 也跟著卡住，四十分鐘內整個結帳流程幾乎停擺。

SRE 志明在 postmortem 寫下一條 action item：「所有對外的 HTTP 呼叫都必須設定 timeout。」工程經理 Kevin 把它指派給初階工程師阿凱。阿凱很認真，打開終端機在主要的 monolith repo 跑 `grep -rn "requests.get("`，得到四百多筆結果。一筆一筆看下去，發現有些是註解、有些是測試、有些是早就沒人用的腳本；更糟的是，有些服務寫的是 `import requests as rq`，有些是 `from requests import get`，這個 grep 完全沒找到；而 monolith 之外那十幾個小 repo（第 19 章 19.7 節），阿凱根本沒有 clone 下來。

阿凱花了兩週，開了一個改動 monolith 裡 120 個檔案的 PR。這個 PR 牽涉全部五個團隊，沒有人敢 approve；三個團隊說「下個 sprint 再看」，一個團隊發現其中一處改錯：那是下載大型商品圖檔的呼叫，10 秒的 timeout 讓它每次都失敗。一個月後 PR 還沒合併，而同一段時間裡，codebase 又新增了七個沒有 timeout 的呼叫。

tech lead 美華看完整件事，對阿凱說：「這不是你不夠努力，而是我們缺了三樣工具。第一樣讓你**知道**問題在哪裡，第二樣**擋住**新的問題，第三樣讓你**安全地改掉**舊的問題。」這三樣工具就是本章的主角：code search、static analysis 與 large-scale change。它們各自都有價值，但真正的威力來自三者串在一起：搜尋提供盤點，分析提供防線與精確定位，LSC 提供把修正推到每個角落的流程。

## 21.2 Code Search：工程師讀程式碼的時間比寫多

### 為什麼需要專門的 code search

剛入行時，我們以為工程師的工作主要是「寫」程式。但在一個有幾十個服務、幾十萬行程式碼的組織裡，大部分時間其實花在「讀」與「找」：這個函式是誰定義的？別人怎麼呼叫這個 API？這個奇怪的設定值是什麼時候、為什麼加的？出錯訊息裡的那個字串是從哪裡印出來的？

《Software Engineering at Google》第 17 章整理了 Google 工程師使用內部 Code Search 的主要目的，可以歸納成幾類問題：**在哪裡**（某個東西定義在哪，約 16%）、**在做什麼**（瀏覽並理解一段程式碼的行為，約四分之一）、**怎麼用**（看別人怎麼呼叫某個 API，約三分之一，是最常見的一類）、**為什麼**（為什麼程式碼長這樣、為什麼行為和預期不同，約 16%）、**誰與何時**（誰改的、什麼時候改的，約 8%）。注意這些問題大多是「理解」而不是「修改」。好的 code search 是一個閱讀工具，它讓你在幾秒內看到整個組織的程式碼，而不是只看你電腦上 checkout 下來的那一小部分。

IDE 的搜尋只看得到本機的專案，`grep` 只看得到你 clone 下來的 repo。Harbor 還是 8 人新創、只有一個 repo 時這沒問題；現在主要的 monolith 之外還有 12 個小 repo（行動 app、幾個獨立服務、`harbor-common` 共用函式庫，見第 19 章），每個人只 clone 自己需要的那幾個，「這個 API 在全公司被誰呼叫」就變成一個沒有人能完整回答的問題。這正是 Hyrum's Law（第 5 章）的實務困境：你無法保護你看不見的使用者。

### 怎麼運作：從 trigram 索引到 cross-reference

在幾百萬行程式碼裡逐字掃描太慢，code search 引擎的核心是**索引**。最常見的做法之一是 **trigram index**（三字元索引）：把每個檔案切成所有連續三個字元的片段，記錄「哪些檔案包含這個片段」。

```text
檔案內容：rq.get(url)
trigram ：rq.  q.g  .ge  get  et(  t(u  (ur  url  rl)

索引（倒排表）：
  "get" → {inventory/supplier.py, search/indexer.py, ...}
  "et(" → {inventory/supplier.py, search/indexer.py, ...}
  "q.g" → {inventory/supplier.py}

查詢 "rq.get(" ：
  ① 拆成 trigram：rq. q.g .ge get et(
  ② 取各倒排表的交集 → 候選檔案（很少）
  ③ 只對候選檔案逐行比對，確認真的出現
```

步驟 ② 是關鍵：任何一個 trigram 沒出現的檔案，就不可能包含整個查詢字串，所以可以直接排除。交集通常只剩極少數檔案，步驟 ③ 的逐行確認就很便宜。正規表示式查詢也能用類似的方式，先從 regex 推導出「必須出現的 trigram」來縮小範圍。Google 的 Code Search 早期就採用 trigram 索引，後來為了在更大的規模下更有效率，陸續換成自訂的 suffix array 與 sparse n-gram 索引；開源的 Zoekt 則是以 trigram 為基礎的程式碼搜尋引擎，常被用作自架 code search 的後端。

文字索引回答的是「這串字出現在哪」，但工程師常問的是「這個**符號**在哪裡被使用」。兩個不同 class 都有 `charge` 方法，文字搜尋分不出來。要回答符號層級的問題，需要 **cross-reference index**（交叉參照索引）：由編譯器或語言工具分析程式碼，記錄每個名稱的定義在哪、每次使用指向哪個定義。Google 用 Kythe（已開源）利用完整的 build 資訊建立這種跨語言的語意索引，所以能分辨同名的不同符號；開源世界常見的做法是由各語言的 indexer 輸出 SCIP 或 LSIF 格式的索引檔，再由 code search 平台讀取。有了它，你可以在網頁上點一個函式名稱就跳到定義，或列出「所有呼叫者」。

### 實務上怎麼做

一個 40 人的團隊不需要自己蓋搜尋引擎，但需要做出明確的選擇：

| 需求 | 常見做法 | 限制 |
|---|---|---|
| 本機快速搜尋 | `ripgrep`、`git grep`、IDE | 只看得到已 clone 的程式碼 |
| 全組織文字／regex 搜尋 | 託管平台的 code search、Sourcegraph、Zoekt | 要維護索引與權限設定 |
| 跳到定義、找所有呼叫者 | 語言伺服器索引、Kythe、SCIP | 要接進 build，動態語言較不精確 |
| 歷史與原因 | `git log -S`、`git blame`、連到 PR 與設計文件 | commit message 品質決定能找到多少 |

Harbor 在這次事故後做了兩件事：把所有 repo 接進同一個 code search 平台，並要求 commit message 連結到 PR 或 issue。後者看似無關，但「為什麼這樣寫」的答案通常不在程式碼裡，而在當初的討論中；搜尋工具若能從一行程式碼一路連到那段討論，新人理解系統的速度會快很多。

搜尋速度本身也是一個設計目標。原書強調 Code Search 的回應必須非常快，因為搜尋是思考過程的一部分：工程師常常連續下好幾個查詢、邊看邊修正。原書給的經驗界線是：200 毫秒以內使用者會覺得即時；超過一秒，注意力就開始飄走；再等十秒，人多半已經切換去做別的事。查詢一慢，工程師就會改成「猜」而不是「查」。

> [!warning] 常見誤解
> 「搜尋到 0 筆，代表沒有人在用。」這是 LSC 與 deprecation 最危險的假設。文字搜尋看不到別名、反射（例如 Python 的 `getattr(module, name)`）、由設定檔或資料庫字串決定的呼叫、其他公司或其他 repo 的使用者，也看不到 generated code。「沒搜到」只是證據之一，還需要下一節的其他證據。

## 21.3 從「找到字」到「知道誰在用」：證據的層次

阿凱的 grep 同時犯了兩種錯：**false positive**（誤報，找到的其實不是問題，例如註解）與 **false negative**（漏報，真正的問題沒找到，例如別名）。要回答「這個 API 到底有多少使用者」，需要疊加不同精確度的證據：

| 證據 | 能看到 | 看不到 | Harbor 例子 |
|---|---|---|---|
| 文字／regex 搜尋 | 任何出現過的字串，包含設定檔、文件 | 別名、動態呼叫；分不出同名符號 | 找到註解裡的 `requests.get(` |
| Symbol 索引 | 解析後的定義與參照 | 未被索引的 repo、反射 | 知道 `rq.get` 指向 `requests.get` |
| AST 分析 | 呼叫的形狀：有幾個參數、有沒有某個 keyword | 執行期才決定的值 | 判斷呼叫有沒有 `timeout=` |
| 型別資訊 | 物件真正的型別、方法屬於哪個 class | 型別標註不完整的程式碼 | 區分 `session.get` 是 HTTP 還是 dict |
| Runtime telemetry | 真的有被執行的路徑與呼叫者 | 很少跑的路徑（例如年度報表） | 由 HTTP client 的 metrics 看出哪些服務在呼叫外部 API |

**AST**（Abstract Syntax Tree，抽象語法樹）是程式碼被解析後的樹狀結構：一個函式呼叫是一個節點，它的子節點是被呼叫的函式與每個參數。文字搜尋把程式碼看成一串字，AST 把它看成有結構的物件，所以能回答「這個呼叫有沒有傳 timeout」這種文字很難可靠回答的問題（參數可能換行、可能有預設值、可能在 `**kwargs` 裡）。

越往表格下方，證據越精確但取得成本越高。實務上的規則是：用便宜的方法建立初始清單，用精確的方法確認與修正，最後用 runtime 資料驗證「真的沒有人在用了」。第 18 章淘汰舊付款 API 時，Harbor 就是先用搜尋找出靜態呼叫者，再用 API gateway 的遙測看每個呼叫來源的真實流量，最後搭配 brownout 逼出剩下的使用者，直到流量歸零才敢刪除。

## 21.4 Static Analysis：不執行程式就找到 bug

### 它是什麼、能做到什麼程度

**Static analysis**（靜態分析）是在不執行程式的情況下，分析程式碼的結構、型別或資料流來找出問題。它是一個光譜：

```text
簡單、快、誤報少                                       深入、慢、誤報多
│                                                                    │
formatter → linter → type checker → bug pattern → data flow / taint → 形式驗證
（排版）   （風格、   （型別錯誤）   （已知錯誤    （不可信資料是否    （證明性質
           明顯錯誤）              寫法，如少了   流到危險位置，     永遠成立）
                                  timeout）      如 SQL injection）
```

第 15 章已經談過光譜左端的 formatter 與 linter，它們關心一致性與可讀性。本章關心的是中段：**bug pattern**（已知會出錯的寫法，例如沒有 timeout 的 HTTP 呼叫、在迴圈裡修改正在迭代的 list、比較浮點數是否相等），以及 **data flow analysis**（資料流分析，追蹤一個值從哪裡來、流到哪裡去）。安全領域常見的 **taint analysis**（污染分析）就是一種資料流分析：把使用者輸入標記為「不可信」，檢查它是否未經處理就流進 SQL 查詢或 shell 指令。

靜態分析有一個根本限制：一般而言，沒有任何分析器能對所有程式都同時做到「不漏報」與「不誤報」（這是計算理論的結果，直覺是「判斷任意程式的行為」等價於判斷它會不會停止）。所以每個分析器都在兩者間取捨：寧可漏一些、也不要誤報太多；或寧可誤報、也不能漏。對大多數開發者面向的檢查而言，正確的選擇是前者，原因就是下一小節的 Tricorder 經驗。

### Tricorder 的教訓：開發者會不會照著做，才是唯一的標準

原書提到，**Tricorder**（Google 在 code review 中整合各種分析器的平台）是在幾次失敗的整合嘗試之後才誕生的。原書引用的論文〈Lessons from Building Static Analysis Tools at Google〉描述過其中一類做法：把 FindBugs 這類工具的結果集中放在儀表板上，請工程師自己去看。結果很少有人看：結果太多、不少是誤報，而且出現在工程師早已不在想那段程式碼的時候。Tricorder 和之前的嘗試最大的不同，是近乎執著地只把有價值的結果送到開發者面前。原書第 20 章描述的做法，可以整理成五個原則：

**第一，以 effective false positive 衡量品質。** 傳統的 false positive 是「工具說有問題，但技術上沒問題」。Tricorder 改用 **effective false positive**（有效誤報）：只要開發者看到結果後**沒有採取正面行動**，不論技術上對不對，都算誤報。一個技術上完全正確、但開發者看不懂或覺得不重要的警告，在實務上和誤報一樣沒有價值，還會消耗開發者對所有警告的信任。反過來，如果工具其實判斷錯了，但開發者看了覺得改一下更清楚、也樂意照改，這就不算 effective false positive。Tricorder 要求每個新檢查的 effective false positive 低於 10%，也就是開發者至少九成的時候覺得它指出的是真問題；原書提到整體的 effective false positive 率略低於 5%。

**第二，結果必須可行動。** 好的分析結果告訴你「錯在哪、為什麼錯、怎麼修」，最好直接附上 **suggested fix**（建議修正），讓開發者按一下就能套用。「這段程式碼複雜度太高」不可行動；「`requests.get` 沒有設定 timeout，網路異常時會無限等待，建議加上 `timeout=DEFAULT_TIMEOUT`」可行動。

**第三，整合進開發者已經在用的工作流程。** 結果要出現在開發者正在看那段程式碼的時候：寫程式時的 IDE、送出變更時的 presubmit、以及 code review 的留言中。Tricorder 主要把分析結果顯示在 code review 裡，而且通常只顯示這次變更修改到的檔案或行，因為那是作者最有動機、也最有上下文去修的時刻；送出 review 後作者本來就在等 reviewer，分析即使要跑幾分鐘也不會擋到誰。

**第四，收集回饋並據此淘汰分析器。** 每個結果旁都有「Not useful」按鈕，按下後可以直接對分析器的作者開 bug；reviewer 則可以按「Please fix」要求作者處理。Tricorder 團隊追蹤每個分析器的「Not useful」點擊率（特別是相對於「Please fix」的比例），比例過高、作者又不改善的分析器會被停用。有時候修正很簡單：原書舉過一個例子，某條檢查一直收到「Not useful」回報，原因只是訊息沒講清楚；改寫訊息文字後，回報就停了。這讓分析器的作者對開發者體驗負責，而不是「寫了規則就不管」。

**第五，讓領域專家貢獻分析器。** 安全團隊最懂安全漏洞、資料庫團隊最懂錯誤的查詢寫法。平台提供簡單的介面讓這些團隊寫自己的檢查，平台團隊負責執行、顯示與收集回饋。

原書另一個值得記住的觀察是關於**警告**：Google 一再發現開發者會忽略編譯器的 warning，因為它不阻擋任何事、又會隨時間累積到沒人看。所以 Google 的 Java 與 C++ 編譯器原則上不輸出 warning：一個檢查要嘛直接變成編譯錯誤，要嘛不在編譯輸出中出現（改放到 code review 由 Tricorder 顯示，或乾脆不顯示）。能放進編譯器的檢查門檻很高，例如 Error Prone 的「ERROR」等級檢查：要可行動且容易修正（盡可能附上可機械套用的修正）、沒有 effective false positive（絕不能讓正確的程式碼編譯失敗）、而且只關乎正確性而非風格。啟用前還要先把整個 codebase 裡的既有違規清乾淨，這本身就是一次 LSC。「警告但不擋」是最差的中間地帶。

### 把分析放在工作流程的哪裡

```text
 寫程式          送出變更          code review           合併後
┌───────┐      ┌───────────┐     ┌──────────────┐     ┌─────────────┐
│  IDE  │ ───▶ │ presubmit │ ──▶ │ review 留言  │ ──▶ │ 定期全庫掃描 │
└───────┘      └───────────┘     └──────────────┘     └─────────────┘
 即時、最便宜    擋下確定的錯誤     需要判斷的問題        找出舊程式碼的問題
 只是提示        （非常低誤報）     附 suggested fix      作為 LSC 的輸入
```

這張圖由左到右，越往右發現問題的成本越高，但能做的分析也越重。IDE 提示最便宜，但開發者可以忽略；presubmit 會阻擋變更，所以只能放幾乎零誤報的規則；code review 留言適合「多半是問題、但需要人判斷」的情況；合併後的全庫掃描不打擾任何人的日常工作，它的產出是一份待修清單，而這份清單正好是下一節 LSC 的起點。

Harbor 的做法是：寫一條自訂規則「`requests` 的 HTTP 呼叫必須有 `timeout`」，在 presubmit 中只對**新增或修改的程式碼**強制執行，舊程式碼的違規先記錄在一份 **baseline**（基準清單）裡不阻擋。這種做法叫 **ratchet**（棘輪）：數字只能往下、不能往上。它讓規則可以今天就上線擋住新問題，而不必等所有舊問題修完。阿凱 PR 期間又新增七個違規的狀況，從此不會再發生。

> [!tip] 寫第一條自訂規則的檢查清單
> 規則的說明是否包含「為什麼」與「怎麼修」？誤報情境有沒有逃生口（例如可以加註解標記例外，並要求寫理由）？能不能提供自動修正？誰是規則的 owner、誰處理「這條規則錯了」的回報？這些問題回答不了，規則就還不該擋住任何人的 PR。

## 21.5 Large-Scale Change：為什麼不能一次改完

### 定義與困難

原書把 **large-scale change**（LSC，大規模變更）定義為：一組邏輯上相關、但實務上無法以單一原子單位提交的變更。例子包括：把某個函式庫的所有呼叫點遷移到新 API、為所有 HTTP 呼叫加上 timeout、把語言版本升一級、把某個欄位的型別從 float 改為 Decimal。

「無法一次提交」聽起來是技術問題，但真正的原因大多和人與流程有關：

- **太多人要 review。** 一個改動五個團隊程式碼的 PR，每個團隊只關心自己的那部分，卻要對整個 PR 負責，結果是沒人 approve。
- **合併衝突。** 改動越多檔案，在 review 期間被別人改到的機率越高，PR 越拖越難合併。
- **測試範圍太大。** 一個 PR 觸發全公司的測試，任何一個無關的 flaky test 失敗都會擋住整件事。
- **失敗時無法局部回退。** 120 個檔案中有一處改錯（例如阿凱的圖檔下載），整個 PR 都得 revert。
- **技術限制。** 在非常大的 codebase 中，單一 commit 改動數萬個檔案，版本控制與 code review 工具本身就可能撐不住。

### 誰來改：集中遷移比分散遷移便宜

在許多組織中，基礎設施團隊推出新 API 後，做法是「發公告、請各團隊在季底前自行遷移」。原書指出這種做法的總成本非常高：每個團隊都要重新理解一次新 API、各自寫一次遷移、各自踩一次同樣的坑，而且總有團隊因為優先順序拖到最後，舊 API 永遠刪不掉。

Google 的做法相反：**由最懂這個變更的人（通常是推出新 API 的團隊）集中負責遷移所有使用者**。他們寫一次自動化工具，就能套用到幾千個呼叫點；他們最清楚邊界情況，也能一致地處理。各團隊的角色從「執行遷移」變成「review 屬於自己的那一小塊」。原書還給了兩個理由：沒有人喜歡沒有附帶資源的強制要求（unfunded mandate），新系統的好處分散在全組織，對單一團隊來說往往不值得主動升級；而且靠各團隊自發完成的遷移很少真正做完，因為工程師寫新程式時會拿既有程式碼當範例，舊寫法會一直被複製。這也呼應第 6 章的 churn rule：與 codebase 規模成線性成長的人工工作，就是應該被集中化與自動化的訊號。原書的說法是，產生變更所需的人力應該隨 codebase 規模次線性成長。

這個做法有一個前提：第 6 章介紹過的 **Beyoncé Rule**。原書的說法是「If you liked it, you should have put a CI test on it」：如果你在乎某個行為，就該用 CI 測試保護它。LSC 的作者不可能理解每個服務的所有細節，只能依賴每個服務自己的測試來發現遷移造成的破壞。如果某個團隊的重要行為沒有測試、因此被 LSC 改壞了，責任不在 LSC 的作者。這條規則讓集中遷移變得可行，也給了每個團隊寫測試的強烈理由（第 22 章會從測試策略的角度再談它）。

## 21.6 LSC 的流程：從提案到清理

原書描述的 LSC 流程大致分成四個階段（原書也提醒，階段之間的界線很模糊）：取得授權、產生變更、shard 管理（拆分、測試、寄送 review、提交）、清理。以下用 Harbor 的 timeout 遷移把它展開：

```text
① 提案與授權           ② 產生變更             ③ 拆分、測試、review、提交        ④ 清理與防回退
┌──────────────┐      ┌──────────────┐      ┌─────────────────────────────┐     ┌──────────────┐
│ 一頁提案：     │      │ code search   │      │  依 owner 拆成 shard          │     │ 例外逐一處理   │
│ 為什麼、範圍、 │ ───▶ │ + 分析器找點  │ ───▶ │  ┌────┐ ┌────┐ ┌────┐       │ ──▶ │ 規則從 ratchet │
│ 怎麼驗證、     │      │ + codemod 改寫│      │  │ A  │ │ B  │ │ C  │ ...   │     │ 改為全面強制   │
│ 風險與回退     │      │ + 抽樣人工檢查│      │  └─┬──┘ └─┬──┘ └─┬──┘       │     │ 刪除 baseline  │
└──────────────┘      └──────────────┘      │  各自跑測試 → review → 合併    │     └──────────────┘
   少數資深者核准         可重跑、可重現        │  失敗的 shard 單獨處理、重跑    │
                                            └─────────────────────────────┘
```

**① 提案與授權。** 在 Google，LSC 作者先寫一份簡短的文件：為什麼要改、預估影響範圍（會拆出多少個 shard）、預先回答 reviewer 可能會問的問題（寫成 FAQ 與變更說明的草稿），並取得被重構 API 的 owner 的「domain review」。提案接著寄給一個約十幾人的小組，成員是熟悉各語言細節的資深工程師，必要時再邀請該領域的專家。這個小組的目的不是阻止 LSC，而是幫作者做出最好的變更：核准通常很寬鬆，明顯的變更可以快速通過；偶爾也會建議某個清理不值得做，例如修正一個常見錯字、卻沒有辦法防止它再出現。小組也是 local owner 對 LSC 有異議時的仲裁窗口。Harbor 規模小，這個角色由各團隊 tech lead 組成的架構會議擔任，提案就是一份一頁的文件，連結到事故的 postmortem。

**② 產生變更。** 用 code search 與分析器找出所有位置，用 codemod 產生修改（下一節詳述），再人工抽樣檢查各種典型形狀的結果。這一階段的產出應該是**可重跑的工具**而不是一堆手改的檔案：如果需要修正規則，只要改工具再跑一次，所有地方就一致地更新。

**③ 拆分、測試、review、提交。** Google 用一個叫 **Rosie** 的工具處理這一步：它把一個巨大的變更依照專案邊界與 ownership 規則（OWNERS 檔案）拆成許多可以各自原子提交的小變更，原書稱為 **shard**（分片）。每個 shard 走一條獨立的「測試、寄送 review、提交」流程：先在 CI 上跑所有可能受影響的測試，通過後寄給合適的 reviewer，核准後獨立提交；失敗的 shard 可以單獨修正、重跑，不影響其他 shard。為了不壓垮共用的基礎設施，Rosie 會限制同一個 LSC 同時在途的 shard 數量，並以較低的優先順序執行。這樣，一個無關的 flaky test 只會卡住一個 shard，一處改錯也只需要 revert 一個小變更。原書也提到，大量跑測試時 flaky test 是 LSC 吞吐量的主要敵人，Google 的自動化工具在提交 LSC 時甚至會忽略近期有 flaky 紀錄的測試；flaky 的成因與處理方式在第 26 章詳談。

Review 是另一個瓶頸。如果每個 shard 都要等該團隊的 owner 有空，一個 LSC 可能被最慢的那個團隊拖住幾個月。原書描述的做法是：審核小組最常給的建議之一，就是把這個 LSC 的所有 review 都交給單一的 **global approver**（全域核准者）。這個人熟悉相關的語言或函式庫，事先和 LSC 作者對齊「這次的變更應該長什麼樣子、可能怎麼出錯」，再用模式比對的工具檢查每個 shard，自動核准符合預期的那些，只需要人工細看少數因合併衝突或工具異常而顯得奇怪的 shard。原書也坦白指出，實務上 local owner 常常太信任 LSC 作者、只草草看過，所以 Google 後來只把「需要 owner 提供上下文」的變更送給 local owner，而不是只為了取得核准權限。換句話說，global approver 適用的是「內容是機械性、已經過授權」的那一類變更；需要判斷的例外，仍然要由真正的 owner 決定。

**④ 清理與防回退。** 自動化通常能處理大部分的呼叫點，剩下的長尾是真正需要人的地方：動態呼叫、特殊用途、需要不同參數值的情況。這些要開 issue 給 owner，附上具體的位置與建議。所有位置處理完後，把 21.4 節的 ratchet 規則改成全面強制、刪除 baseline。原書提到，不同 LSC 對「完成」的定義不同，從完全移除舊系統，到只遷移高價值的使用點、讓其餘自然消失都有；但幾乎所有情況都需要一個機制擋住新的使用，Google 用的正是 Tricorder：在 code review 時標出新加入的 deprecated 用法。沒有這一步，遷移就會在完成的那一刻開始倒退。

一個實務上的小細節：shard 的大小也是一種取捨。Shard 太大，又回到「一個 PR 牽涉太多人」的問題；shard 太小，owner 一天收到三十個 review 請求，同樣會被忽略。常見的切法是「每個 owner 一個 shard」，再對特別大的 owner 依目錄細分。

## 21.7 Codemod：用程式改程式

### 從 regex 到 AST 到 CST

**Codemod**（code modification 的縮寫）是自動改寫程式碼的程式。它可以用三種層次的方法實作：

**Regex 取代**最簡單，例如 `sed 's/requests.get(\(.*\))/requests.get(\1, timeout=10)/'`。它的問題和 21.3 節的文字搜尋一樣：會改到註解與字串，處理不了跨行的呼叫、別名與巢狀括號。Regex 適合一次性、範圍明確、改完人工確認的小修改。

**AST 改寫**把程式碼解析成語法樹，找到符合條件的節點再修改。它理解結構，所以能精確地只改「`requests` 模組的 `get` 呼叫、而且沒有 `timeout` 參數」的那些。缺點是 AST 通常會丟掉註解與排版：Python 標準函式庫的 `ast` 解析後再 `ast.unparse` 寫回，註解就消失了。

**CST**（Concrete Syntax Tree，具體語法樹）保留了所有原始資訊，包括空白、註解與括號，所以能在修改結構的同時讓其他部分保持原樣。實務上能保留排版的工具有幾類：Python 的 LibCST 是真正的 CST；JavaScript 的 jscodeshift 透過 recast 只重印被改動的節點，其餘原樣保留；Java 生態的 OpenRewrite 用保留格式、並附帶型別資訊的語法樹做改寫；另外還有跨語言、以「程式碼樣式比對」為主的 ast-grep（基於 tree-sitter 語法樹）、Comby（以括號等結構做比對，不需要完整的語言 parser）與 Semgrep（以樣式寫檢查規則，也能附自動修正）。原書提到 Google 在編譯器產生的索引之上，用 ClangMR（C++）、JavacFlume、Refaster（Java）等工具平行地做 AST 層級的分析與轉換；其中 Refaster 用「改寫前」與「改寫後」兩段範例程式來描述規則。Error Prone 的檢查也常附帶 suggested fix，同一套修正既能在 code review 中提示，也能在 LSC 中批次套用。

另一個常見技巧是：用 AST 找出要改的**位置**（行號與欄位），再直接在原始文字上做最小的插入，其他字元一個都不動。本章的動手寫就用這個方法，它的好處是 diff 非常乾淨，reviewer 一眼就能看出改了什麼。

### 好的 codemod 的五個性質

1. **保守（conservative）。** 只改你確定理解的形狀，其餘全部跳過並報告。阿凱的 PR 把串流下載的呼叫也加了 10 秒 timeout，就是缺少這個性質。寧可留下 20 個需要人處理的例外，也不要產生 1 個悄悄改錯的地方。
2. **確定且可重跑（deterministic）。** 同樣的輸入永遠產生同樣的輸出，這樣才能在規則修正後重新產生所有 shard，也才能讓 reviewer 信任「review 規則與抽樣」就等於 review 了全部。
3. **Idempotent（冪等）。** 對已經改過的程式碼再跑一次，不應該再產生任何 diff。這讓你可以在遷移期間反覆執行，處理新合併進來的程式碼。
4. **最小 diff。** 只改必要的字元，保留註解與排版，改完跑一次 formatter。Reviewer 要看的應該是語意變化，而不是一堆縮排差異。
5. **機械與判斷分開。** 自動產生的變更與人工修改放在不同的 commit 或不同的 shard。機械性的 shard 可以走 global approver；含人工判斷的部分必須由 owner 仔細看。

> [!warning] 常見誤解
> 「codemod 改完，測試都過了，就代表正確。」測試只能證明「被測到的行為沒壞」。LSC 的作者還必須思考語意：這次的 timeout 值對每個呼叫都合理嗎？哪些呼叫原本就預期要等很久？這些問題要在 codemod 的規則與例外清單中回答，測試只是最後一道網。

## 21.8 動手寫：搜尋、分析、改寫、拆分

下面的程式把本章的四個工具串成一條迷你的 LSC 管線：用 trigram 索引做文字搜尋、用 AST 分析找出缺少 timeout 的 HTTP 呼叫（能理解 import 別名）、用保留排版的 codemod 自動修正、最後依 owner 拆成 shard，並把需要判斷的例外分開。

```python
import ast
from collections import defaultdict

# 迷你 Harbor codebase：路徑 → 原始碼
FILES = {
    "checkout/pay.py": (
        "import requests\n"
        "\n"
        "def charge(order):\n"
        "    # 呼叫金流商\n"
        "    r = requests.post(PSP_URL, json=order.payload())\n"
        "    return r.json()\n"
    ),
    "checkout/notes.py": (
        "# TODO: 以前這裡用 requests.get(url) 抓匯率，已移除\n"
        "RATE = 1.0\n"
    ),
    "inventory/supplier.py": (
        "import requests as rq\n"
        "\n"
        "def stock(sku):\n"
        "    return rq.get(f'{SUPPLIER}/stock/{sku}',\n"
        "                  headers=AUTH).json()\n"
    ),
    "search/indexer.py": (
        "from requests import get\n"
        "\n"
        "def fetch_feed():\n"
        "    return get(FEED_URL, timeout=5).text\n"
        "\n"
        "def fetch_dump():\n"
        "    return get(DUMP_URL, stream=True)\n"
    ),
    "notification/sms.py": (
        "import requests\n"
        "\n"
        "def send(msg, **opts):\n"
        "    requests.post(SMS_URL, data=msg, **opts)  # 簡訊商\n"
    ),
}
OWNERS = {"checkout/": "checkout-team", "inventory/": "seller-team",
          "search/": "search-team", "notification/": "platform-team"}
HTTP_VERBS = {"get", "post", "put", "delete"}


# ---------- 1. Code search：trigram 索引 ----------
def trigrams(s):
    return {s[i:i + 3] for i in range(len(s) - 2)}

def build_index(files):
    index = defaultdict(set)
    for path, src in files.items():
        for t in trigrams(src):
            index[t].add(path)
    return index

def search(index, files, query):
    candidates = set(files)
    for t in trigrams(query):              # 先用索引交集縮小範圍
        candidates &= index.get(t, set())
    hits = []
    for path in sorted(candidates):        # 再逐行確認真的出現
        for no, line in enumerate(files[path].splitlines(), 1):
            if query in line:
                hits.append(f"{path}:{no}: {line.strip()}")
    return hits


# ---------- 2. Static analysis：理解 import 別名的 AST 檢查 ----------
def http_aliases(tree):
    """回傳 (模組別名集合, 直接匯入的函式名集合)"""
    modules, funcs = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "requests":
                    modules.add(a.asname or "requests")
        elif isinstance(node, ast.ImportFrom) and node.module == "requests":
            for a in node.names:
                if a.name in HTTP_VERBS:
                    funcs.add(a.asname or a.name)
    return modules, funcs

def find_missing_timeout(src):
    tree = ast.parse(src)
    modules, funcs = http_aliases(tree)
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_http = (isinstance(f, ast.Attribute) and f.attr in HTTP_VERBS
                   and isinstance(f.value, ast.Name) and f.value.id in modules) or \
                  (isinstance(f, ast.Name) and f.id in funcs)
        if not is_http:
            continue
        kws = {k.arg for k in node.keywords}
        if "timeout" in kws:
            continue
        if None in kws:                    # 有 **kwargs，timeout 可能藏在裡面
            findings.append((node, "needs-human: 有 **kwargs，無法確定"))
        elif "stream" in kws:              # 串流下載，10 秒可能不夠
            findings.append((node, "needs-human: stream=True，timeout 值要人決定"))
        else:
            findings.append((node, "autofix"))
    return findings


# ---------- 3. Codemod：只在 ')' 前插入參數，保留註解與排版 ----------
def apply_fix(src, findings, value="DEFAULT_TIMEOUT"):
    lines = src.splitlines(keepends=True)
    fixable = [n for n, kind in findings if kind == "autofix"]
    # 從檔案尾端往前改，前面的位置才不會被位移
    for node in sorted(fixable, key=lambda n: (n.end_lineno, n.end_col_offset), reverse=True):
        raw = lines[node.end_lineno - 1].encode("utf-8")   # col_offset 是 UTF-8 位元組位置
        cut = node.end_col_offset - 1                      # 指向結尾的 ')'
        sep = ", " if (node.args or node.keywords) else ""
        raw = raw[:cut] + f"{sep}timeout={value}".encode() + raw[cut:]
        lines[node.end_lineno - 1] = raw.decode("utf-8")
    return "".join(lines), len(fixable)


# ---------- 4. 依 owner 拆分 shard（Rosie 的概念） ----------
def owner_of(path):
    return next(team for prefix, team in OWNERS.items() if path.startswith(prefix))


print("== 1. 文字搜尋 'requests.get(' ==")
idx = build_index(FILES)
for h in search(idx, FILES, "requests.get("):
    print("  ", h)
print("   （命中的是註解；真正的 rq.get 與 get 都沒找到）\n")

print("== 2. AST 分析 ==")
results = {}
for path, src in FILES.items():
    results[path] = find_missing_timeout(src)
    for node, kind in results[path]:
        print(f"   {path}:{node.lineno}  {kind}")

print("\n== 3. 套用 codemod ==")
new_files, shards = {}, defaultdict(list)
for path, src in FILES.items():
    new_src, n = apply_fix(src, results[path])
    new_files[path] = new_src
    if n:
        ast.parse(new_src)                                  # 改完仍是合法 Python
        shards[owner_of(path)].append((path, n))
print(new_files["inventory/supplier.py"])
again = sum(k == "autofix" for s in new_files.values() for _, k in find_missing_timeout(s))
print(f"   重跑分析器：剩 {again} 個可自動修的問題（idempotent）")
twice = all(apply_fix(s, find_missing_timeout(s))[0] == s for s in new_files.values())
print(f"   再跑一次 codemod 不產生新 diff：{twice}")

print("\n== 4. Shard 計畫 ==")
for team, items in sorted(shards.items()):
    detail = ", ".join(f"{p}({n})" for p, n in items)
    print(f"   {team:15s} {detail}  → 機械性變更，可走 global approver")
manual = [(p, node.lineno) for p, fs in results.items() for node, k in fs if k != "autofix"]
for p, line in manual:
    print(f"   {owner_of(p):15s} {p}:{line}  → 例外，開 issue 請 owner 決定")
```

執行結果：

```text
== 1. 文字搜尋 'requests.get(' ==
   checkout/notes.py:1: # TODO: 以前這裡用 requests.get(url) 抓匯率，已移除
   （命中的是註解；真正的 rq.get 與 get 都沒找到）

== 2. AST 分析 ==
   checkout/pay.py:5  autofix
   inventory/supplier.py:4  autofix
   search/indexer.py:7  needs-human: stream=True，timeout 值要人決定
   notification/sms.py:4  needs-human: 有 **kwargs，無法確定

== 3. 套用 codemod ==
import requests as rq

def stock(sku):
    return rq.get(f'{SUPPLIER}/stock/{sku}',
                  headers=AUTH, timeout=DEFAULT_TIMEOUT).json()

   重跑分析器：剩 0 個可自動修的問題（idempotent）
   再跑一次 codemod 不產生新 diff：True

== 4. Shard 計畫 ==
   checkout-team   checkout/pay.py(1)  → 機械性變更，可走 global approver
   seller-team     inventory/supplier.py(1)  → 機械性變更，可走 global approver
   search-team     search/indexer.py:7  → 例外，開 issue 請 owner 決定
   platform-team   notification/sms.py:4  → 例外，開 issue 請 owner 決定
```

逐段解讀：

1. **搜尋階段**重現了阿凱的困境。trigram 索引先用交集排除不可能的檔案，再逐行確認，速度很快，但它只懂字串：唯一的命中是註解（false positive），而 `rq.get` 與 `get` 兩個真正的問題都漏掉了（false negative）。真實的 code search 平台運作方式類似，只是索引規模大得多，並且通常搭配 symbol 索引。
2. **分析階段**的 `http_aliases` 先讀 import，知道 `rq` 就是 `requests`、`get` 就是 `requests.get`，這是文字搜尋做不到的。`find_missing_timeout` 再看每個呼叫的 keyword 參數，並把結果分成三類：已經有 timeout 的直接略過；可以安全自動修的標為 `autofix`；有 `**kwargs` 或 `stream=True` 的標為 `needs-human`。這個三分法就是「保守」原則的實作：分析器承認自己不知道的事。同一個函式稍作修改，就能放進 presubmit 當成 21.4 節的 ratchet 規則。
3. **改寫階段**沒有用 `ast.unparse` 重寫整個檔案，而是利用 AST 給的結尾位置（`end_lineno`、`end_col_offset`）在右括號前插入文字。所以 `inventory/supplier.py` 的跨行排版完全保留，diff 只有一個參數。程式特別處理了一個容易踩的坑：Python AST 的欄位位置以 UTF-8 位元組計算，如果同一行前面有中文，直接用字元索引會插錯位置。改完後用 `ast.parse` 確認仍是合法程式，再重跑分析器與 codemod，證明它是 idempotent 的。
4. **拆分階段**依 `OWNERS` 把機械性變更分成每個團隊一個 shard，例外則開 issue 給 owner。在真實系統中，每個 shard 會變成一個獨立的 PR，觸發該團隊的 CI 測試，通過後由 global approver 或 owner 核准合併。

這段程式刻意留下一個缺口：改寫後的程式碼使用了 `DEFAULT_TIMEOUT`，卻沒有加上對應的 import。真實的 codemod 必須同時處理 import 與常數定義，否則每個 shard 都會在 CI 失敗。這也說明了為什麼 shard 的自動測試不可省略：它會抓到 codemod 作者沒想到的事。

## 21.9 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會失敗 | 具體情境 | 對策 |
|---|---|---|---|
| 只靠文字搜尋盤點使用者 | 別名、動態呼叫、其他 repo 的使用者被漏掉 | 搜尋 0 筆就刪除舊 API，結果用 `getattr` 動態呼叫的報表工具壞了 | 疊加 symbol 索引、AST 與 runtime metrics；刪除前觀察一段時間的實際流量 |
| 分析器誤報率太高 | 開發者學會無視所有警告，連真的問題也一起忽略 | 新的 SQL injection 規則把所有字串串接都標出來，一週後大家開始直接按「忽略」 | 追蹤 effective false positive；誤報高的規則改成只在 review 提示或先停用 |
| 新規則一上線就對全庫強制 | 所有團隊的 PR 同時被擋，規則被迫撤回 | timeout 規則對舊程式碼也強制，當天有十幾個無關 PR 被卡住 | 用 baseline 與 ratchet：只擋新程式碼，舊程式碼交給 LSC |
| 一個巨大的 LSC PR | 無人 review、合併衝突、一處錯誤就整個 revert | 阿凱的 120 檔 PR 拖了一個月仍未合併 | 依 owner 拆 shard，每個 shard 獨立測試、核准、回退 |
| Codemod 不夠保守 | 語意改錯但測試沒抓到 | 串流下載被加上 10 秒 timeout，只在大檔案時失敗 | 未知形狀一律跳過並報告；抽樣檢查每一種形狀 |
| Global approver 被濫用 | 含判斷的變更繞過真正的 owner | 有人把「順便重構」夾在機械性 shard 裡，用 global approval 合併 | 只對經授權的機械性變更使用；機械與人工修改分開提交 |
| 遷移完成卻沒有清理 | 舊寫法在幾個月內回來，或兩套 API 永久並存 | 遷移宣布完成後沒有把規則改為全面強制，新人又複製了舊範例 | 把「規則全面強制、刪除 baseline 與舊 API」寫進完成條件 |

## 21.10 AI 時代：什麼變了？

AI coding agent 讓本章的三個主題都發生了變化，但方向不一樣。

**第一，搜尋與理解變便宜了，但證據標準沒有降低。** 過去要理解「這個 API 有哪些用法」，需要人讀幾十個搜尋結果並自己歸納。現在可以讓 agent 執行 code search、讀取結果，再把呼叫點依形狀分群：「有 120 個是單純的兩參數呼叫、15 個帶 `**kwargs`、8 個是串流下載、3 個用 `getattr` 動態取得。」這種分群正是設計 codemod 時最需要的資訊。但 agent 的摘要只是假說：每一群都要附上具體的檔案與行號，讓人能抽查；agent 宣稱「沒有其他用法」時，仍然要用 symbol 索引與 runtime 資料驗證，因為模型的 context 裝不下整個 codebase，它看過的也只是搜尋結果的一部分。

**第二，大規模執行應該交給確定性的工具，而不是讓模型逐檔改寫。** 讓 agent 直接打開 500 個檔案逐一修改，看起來最省事，但它違反了 21.7 節 codemod 的幾乎每個性質：同樣的輸入可能產生不同的輸出、無法重跑、reviewer 無法用「review 規則」代替「review 每個檔案」。比較穩健的分工是：

```text
agent：探索與分群 ──▶ agent：草擬 codemod 規則與測試案例 ──▶ 人：review 規則與例外清單
                                                                    │
       ┌────────────────────────────────────────────────────────────┘
       ▼
codemod：確定性地套用到所有標準形狀 ──▶ Rosie 式拆分：每個 shard 跑 CI、owner／global approver 核准
       │
       ▼
agent：處理長尾例外，每個例外一個小 PR，附上原因與證據 ──▶ owner 逐一 review
```

這張圖的重點是：模型負責「需要理解」的部分（分群、寫規則、處理例外），確定性工具負責「需要一致」的部分（大量套用），人負責「需要判斷與負責」的部分（規則是否正確、例外怎麼處理、是否合併）。

**第三，AI 讓程式碼的產量變大，靜態分析變得更重要。** 當 agent 一天能產生的 PR 比人多很多時，人類 reviewer 的注意力就成了瓶頸。確定性的分析器不會疲倦，它應該先過濾掉所有已知的錯誤寫法，讓 reviewer 把時間花在設計與語意上。Harbor 的 timeout 規則同樣適用於 agent 產生的程式碼：agent 很容易從訓練資料或舊程式碼中學到 `requests.get(url)` 這種寫法，ratchet 規則會在 presubmit 擋下它，並且 agent 可以讀取規則訊息自己修正。換句話說，**好的分析器同時是給人與給 agent 的回饋迴路**。

**第四，用模型做分析器時，Tricorder 的原則更重要。** 以 LLM 為基礎的 code review 工具可以找出規則難以描述的問題，例如「這個錯誤處理吞掉了例外」。但它的結果不確定、誤報率通常高於傳統規則。把它放進工作流程時，應該套用同樣的標準：追蹤 effective false positive、只在 review 中提示而不擋 presubmit、讓開發者能回報「沒用」，並定期淘汰表現差的提示類型。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 執行 code search，把呼叫點依形狀分群並統計，每群附檔案與行號 | 「沒有其他使用者」的結論必須由 symbol 索引與 runtime metrics 驗證，不能只採信模型摘要 |
| 根據分群草擬 codemod 規則、正向與反向測試案例 | 規則與例外清單由 LSC 作者 review；codemod 必須確定、可重跑、idempotent |
| 為長尾例外各自開小 PR，說明原因與建議 | Agent 不能使用 global approval；含判斷的變更必須由該目錄的 owner 核准 |
| 讀取分析器與 CI 的失敗訊息，自行修正自己產生的程式碼 | Agent 的權限限定在指定範圍（例如只能改某些目錄），不能停用規則、加入例外標記或刪除測試來讓 CI 通過 |
| 摘要遷移進度、卡住的 shard 與重複出現的例外 | 每個 shard 都要通過該團隊的 CI；遷移完成條件（規則全面強制、刪除舊 API）由人確認 |
| 撰寫新分析規則的初稿與說明文字 | 規則上線前用歷史程式碼量測誤報；上線後追蹤 effective false positive 並指定 owner |

> [!ai] AI 提醒
> 一個常見的陷阱是讓 agent「讓 CI 變綠」。如果 agent 的目標只有通過檢查，它可能學會在程式碼加上「忽略此規則」的註解、把失敗的測試標成 skip，或把 timeout 設成一個極大的值。這些都會讓檢查通過，卻完全違背規則的目的。對策是把這些「逃生口」本身也變成需要人類核准的變更，並在 PR 描述中要求 agent 明列它使用了哪些例外。

## 21.11 專家怎麼想

- **「這個問題會不會再發生？」先於「怎麼修掉現有的？」** 資深工程師看到 postmortem 的 action item「所有呼叫都加 timeout」，第一個反應是先寫一條規則擋住新的，再處理舊的。順序反過來，修多少就會新增多少。
- **把分析器當產品，而不是當規範。** 他們會問：這條規則的 effective false positive 是多少？開發者看到訊息後知道怎麼做嗎？有沒有自動修正？誰負責處理回報？一條讓大家厭煩的規則，會讓下一條好的規則也被無視。
- **由懂的人集中遷移。** 「請各團隊自行遷移」聽起來尊重 ownership，但總成本通常最高、完成率最低。專家會把遷移當成推出新 API 的團隊的責任，各團隊只負責 review 與處理自己的例外。
- **相信工具的確定性，不相信自己的細心。** 手動修改 100 個地方，總會錯一兩個；寫一個 codemod 並 review 它的規則與樣本，錯誤率更低，而且可以重跑。他們寧可花一天寫工具，也不花三天手改。
- **保守地自動化，誠實地報告例外。** 好的 codemod 會說「我改了 412 個，跳過 23 個，這是跳過的清單與原因」。一個宣稱 100% 自動完成的遷移，反而會讓有經驗的人起疑。
- **完成的定義包含清理。** 他們會問：舊 API 什麼時候刪？規則什麼時候改為全面強制？沒有這兩個日期的遷移，通常不會真的結束。

## 21.12 動手練習

1. 延伸 21.8 的程式：讓 codemod 在檔案沒有 `DEFAULT_TIMEOUT` 時自動加上 `from harbor.http import DEFAULT_TIMEOUT`，並確保重跑時不會重複加入 import。
2. 在 21.8 的 `FILES` 加入三種新案例：`session = requests.Session(); session.get(url)`、`getattr(requests, "get")(url)`、以及字串 `"requests.get"` 出現在設定檔中。觀察分析器各自的行為，並決定每一種應該自動修、報告為例外、還是需要型別資訊才能判斷。
3. 為你的專案（或 Harbor）設計一條自訂的靜態分析規則，寫下：規則說明（包含為什麼與怎麼修）、三個應該報告的例子、三個不應該報告的例子、例外標記方式，以及你會如何量測它的 effective false positive。
4. 選一個你熟悉的 API 遷移（例如函式庫大版本升級），寫一頁 LSC 提案：範圍、證據來源（搜尋、索引、runtime）、codemod 策略、shard 切法、驗證方式、例外處理、完成條件。
5. 用 `git log -S "某個函式名"` 在一個真實 repo 中追蹤某個函式是何時被引入、何時被改名或移除，練習用版本歷史回答「為什麼」的問題。
6. 讓一個 AI coding agent 對一段程式碼列出某個 API 的所有使用方式並分群，再用 `ripgrep` 與 AST 腳本獨立驗證：它漏了哪些？多報了哪些？把結果整理成「agent 摘要需要附什麼證據」的檢查清單。

## 本章重點整理

- 工程師讀與找程式碼的時間遠多於寫；全組織的 code search 讓人能回答「在哪裡、怎麼用、為什麼、誰改的」，也是保護隱性使用者（Hyrum's Law）的前提。
- Trigram 索引讓文字與 regex 搜尋在大型 codebase 中仍然快速；cross-reference 索引則回答符號層級的「定義在哪、誰在呼叫」。
- 文字搜尋同時會誤報與漏報；盤點使用者要疊加 symbol 索引、AST、型別資訊與 runtime telemetry，「搜不到」不等於「沒人用」。
- 靜態分析無法同時做到不漏報與不誤報；開發者面向的檢查應該寧可漏一些，也不要誤報太多。
- Tricorder 以 effective false positive（開發者沒有採取行動的結果）衡量分析器，目標低於 10%，並要求結果可行動、附 suggested fix、整合進 code review 與 presubmit。
- 只警告不阻擋的檢查最終會被忽略；確定的錯誤直接擋下，需要判斷的放到 review。
- 用 baseline 與 ratchet 讓新規則立即擋住新問題，舊問題交給 LSC，避免規則一上線就卡住所有人。
- LSC 是邏輯上相關、但無法原子提交的一組變更；困難主要來自 review 協調、合併衝突、測試範圍與局部回退。
- 由最懂變更的團隊集中遷移所有使用者，比請每個團隊各自遷移便宜得多；Beyoncé Rule 讓這種做法可行。
- LSC 流程包含提案授權、產生變更、依 owner 拆分 shard（Rosie）並各自測試與核准、以及清理與防回退。
- Global approver 只用於已授權的機械性變更，需要判斷的例外仍由真正的 owner 決定。
- 好的 codemod 保守、確定、idempotent、最小 diff，並把機械性變更與人工判斷分開；AST 或 CST 比 regex 安全。
- AI agent 適合探索、分群、草擬規則與處理長尾例外；大量套用交給確定性工具，結論要附可驗證的證據。
- AI 讓程式碼產量增加，確定性的靜態分析成為人與 agent 共用的回饋迴路；agent 不得以停用規則或跳過測試的方式讓 CI 通過。

## 延伸問答

> [!question]- Q1. 文字搜尋、symbol 索引與 AST 分析的差別是什麼？什麼時候文字搜尋反而是最好的選擇？
> 文字搜尋把程式碼當成字串，只回答「這串字出現在哪」；symbol 索引理解名稱的定義與參照，能區分兩個同名但屬於不同 class 的方法；AST 分析理解呼叫的結構，能判斷參數的數量、有沒有某個 keyword。越精確的方法越需要語言工具與 build 資訊，成本也越高。
>
> 文字搜尋在幾種情況下反而最適合：搜尋設定檔、文件、SQL、shell 腳本這些沒有語言索引的檔案；搜尋錯誤訊息字串，找出它是從哪裡印出來的；以及跨多種語言做第一輪盤點。它的價值在於「什麼都看得到」，缺點是「什麼都分不清」。實務上通常先用文字搜尋建立寬鬆的候選清單，再用精確的方法篩選與補漏。

> [!question]- Q2. 什麼是 effective false positive？為什麼 Tricorder 不直接用技術上的誤報率？
> Effective false positive 指的是：開發者看到分析結果後，沒有採取任何正面行動的情況，不論這個結果在技術上對不對。例如一個警告技術上完全正確，但訊息看不懂、修正方式不明、或問題不重要，開發者直接略過，它就算一次有效誤報。
>
> Tricorder 採用這個定義，是因為分析器的價值只來自它改變了開發者的行為。技術上正確但沒人理會的警告，不只是沒有價值，還會訓練開發者忽略所有警告，連真正重要的也被一起略過。用開發者的實際反應來衡量，迫使分析器的作者改善訊息、提供自動修正、降低噪音，或乾脆把規則撤下。這和第 32 章「SLI 要從使用者角度量測」是同一種思維。

> [!question]- Q3. 你剛寫好一條「禁止在 checkout 中使用 float 表示金額」的規則，掃描發現既有程式碼有 300 處違規。你會怎麼上線？
> 不能直接在 presubmit 對全庫強制，否則所有碰到這些檔案的 PR 都會被擋，規則很可能當天就被要求撤回。比較好的做法是先建立 baseline，記錄這 300 處既有違規，presubmit 只對新增或修改的程式碼強制，這就是 ratchet：違規數只能減少、不能增加。
>
> 接著把 300 處當成一個 LSC 處理。先分析它們的形狀：哪些是單純的計算可以機械改寫，哪些牽涉 API 介面或資料庫欄位、需要相容性設計。機械性的部分寫 codemod、依 owner 拆 shard；牽涉介面的部分可能需要第 18 章的 deprecation 流程。全部處理完後，把規則改為全面強制並刪除 baseline。上線前也要用歷史程式碼確認誤報率，例如顯示用的格式化字串是否會被誤判。

> [!question]- Q4. 為什麼「請各團隊在季底前自行遷移」通常比集中遷移更貴？集中遷移需要什麼前提？
> 自行遷移時，每個團隊都要重新理解新 API、各自寫一次遷移程式、各自發現同樣的邊界情況，總工作量大約是「團隊數 × 單次學習成本」，而且這些工作和每個團隊的產品優先順序競爭，總有團隊拖到最後，導致舊 API 遲遲無法刪除。集中遷移時，最懂變更的團隊只學一次、寫一次工具，就能一致地套用到所有地方，總成本大幅下降。
>
> 前提有幾個：需要好的 code search 找出所有使用者；需要確定性的 codemod 工具；需要能把變更拆成小 shard 並獨立測試、核准的流程；最重要的是 Beyoncé Rule，每個團隊必須用 CI 測試保護自己在乎的行為。遷移者不可能理解每個服務的細節，只能依靠各服務自己的測試來發現破壞。如果某團隊的重要行為沒有測試，集中遷移就會變得危險。

> [!question]- Q5. Global approver 會不會破壞 code ownership？要怎麼設計才不會？
> 如果濫用，會。Ownership 的意義是「對這段程式碼的正確性與長期健康負責的人，對它的變更有決定權」。若任何人都能透過 global approver 繞過 owner，owner 就無法對自己的程式碼負責。
>
> 正確的設計是限制 global approval 的適用範圍：只用於已經通過 LSC 提案審核、內容純粹機械性、由確定性工具產生的變更；並且要求這些 shard 通過該團隊自己的 CI 測試。Google 的做法也保留了申訴管道：local owner 對 LSC 有異議時，可以找審核小組仲裁。Harbor 再加一條：owner 仍然收得到通知、可以 review 與提出異議。任何含人工判斷的修改，例如 codemod 跳過的例外、順便的重構，都必須和機械性變更分開提交，並由真正的 owner 核准。這樣 global approver 解決的是「等待」的問題，而不是「繞過判斷」。

> [!question]- Q6. 一個 codemod 改了 800 個檔案，所有 shard 的測試都通過了。這樣就能宣布完成嗎？
> 還不能，至少還有三件事要確認。第一，codemod 跳過的例外處理了沒有？保守的 codemod 一定會留下需要人判斷的長尾，這些要逐一開 issue 給 owner 並追蹤到結束。第二，測試通過只代表被測到的行為沒壞。LSC 作者要對語意負責：例如這次的 timeout 值對每一類呼叫都合理嗎？有沒有呼叫原本就預期要等很久？這要靠 codemod 規則的設計與抽樣檢查，而不只是測試。
>
> 第三是防回退與清理：把 ratchet 規則改成全面強制、刪除 baseline、如果是 API 遷移就刪除舊 API。若有動態使用者的可能，刪除前要用 runtime metrics 觀察一段時間確認歸零。完成的定義應該寫在一開始的提案中，而不是在最後才討論。

> [!question]- Q7. 讓 AI agent 直接逐檔修改 500 個呼叫點，和讓 agent 寫 codemod 再執行，差別在哪裡？
> 逐檔修改時，每個檔案的改法都是模型當下產生的，同樣的程式碼形狀可能被改成不同的樣子，偶爾還會順手改到不相關的地方。Reviewer 無法只看規則與樣本，而必須逐一檢查 500 個 diff，這正是 LSC 想避免的成本。修正規則時，也無法「重跑一次」讓所有地方一致更新。
>
> 讓 agent 寫 codemod，則把模型的優勢放在理解與歸納：分析呼叫點的形狀、寫出規則與正反測試案例；執行則交給確定性的工具，確保可重跑、idempotent、最小 diff。Reviewer 只要 review 規則、測試案例與抽樣結果，就能對所有標準形狀建立信心。模型真正需要「逐一處理」的，只剩 codemod 跳過的少數例外，而這些例外本來就需要 owner 的判斷，正好用小 PR 分別送審。

> [!question]- Q8. 面試題：你加入一個 30 個服務的團隊，發現有一種寫法反覆造成事故。請描述你從發現到徹底解決的計畫。
> 第一步是盤點與確認：用全組織的 code search 建立候選清單，再用 AST 或型別感知的工具精確篩選，必要時加上 runtime 資料，得到真實的違規數量與分佈，並和事故紀錄對照確認這種寫法確實是原因。第二步是止血：寫一條靜態分析規則，訊息包含原因與修正方式、盡量附自動修正，用 baseline 與 ratchet 的方式在 presubmit 只擋新程式碼，讓問題不再增加。
>
> 第三步是清理舊程式碼：寫一頁 LSC 提案取得 tech lead 們的同意，寫保守的 codemod 處理標準形狀，依 owner 拆 shard 並讓每個 shard 跑各自的 CI，例外開 issue 給 owner。最後把規則改為全面強制、刪除 baseline，並追蹤規則的 effective false positive。回答時強調「先擋新、再修舊、最後清理」的順序，以及「確定性工具執行、人負責判斷」的分工，會讓面試官看到你理解規模化變更的關鍵。

## 延伸閱讀

- [Software Engineering at Google — Code Search](https://abseil.io/resources/swe-book/html/ch17.html)：Google 工程師如何使用 Code Search、為什麼搜尋速度與 cross-reference 很重要。
- [Software Engineering at Google — Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html)：Tricorder 的設計原則、effective false positive 與整合進 code review 的經驗。
- [Software Engineering at Google — Large-Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)：LSC 的定義、為什麼不原子、Rosie 與 LSC 流程的完整描述。
- [OpenAI — Codex Best Practices](https://learn.chatgpt.com/guides/best-practices)：讓 coding agent 在大型 codebase 中工作時，如何提供 context、驗證方式與限制範圍。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：review AI 產生之變更時要檢查的重點，可搭配本章的 shard 與例外分工使用。
