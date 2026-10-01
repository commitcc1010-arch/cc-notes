---
chapter: 17
title: Documentation、Design Doc 與 API Contract
part: 3
---

# 第 17 章　Documentation、Design Doc 與 API Contract

> [!abstract] 本章地圖
> **核心問題**：當團隊、程式碼與 AI agent 都在持續變動時，哪些知識必須寫下來、寫成什麼形式、由誰維護，才能讓別人安全地使用與修改你的系統？
>
> **你會學到**：
> - 分辨 reference、design doc、tutorial、conceptual、landing page 等文件類型，並用 Diátaxis 判斷一份文件該回答什麼問題
> - 用 docs as code 的方式讓文件和程式碼一起被 review、測試與發布
> - 寫出一份能在動工前抓出問題的 design doc，並知道如何 review 它
> - 把 API 的承諾寫成 OpenAPI 或 protobuf 這類機器可讀的 contract，並判斷哪些變更會破壞相容性
> - 替文件設定 owner 與新鮮度機制，讓過時的文件被發現、更新或下架
> - 安全地使用 AI 草擬文件，並驗證它寫出來的內容
>
> **前置知識**：第 5 章（Hyrum's Law）、第 7 章（ADR）、第 10 章（Knowledge Sharing）
>
> **對應原書**：SWE 第 10 章〈Documentation〉

## 17.1 故事：一次「內部重構」弄壞了三個團隊

Harbor 成立第二年，公司從 8 個人長到 40 多人，分成 checkout、payments、search、seller、platform 五個團隊；行動 app 由 search 團隊裡的 app 小組維護。以前大家坐在同一張長桌，有問題轉頭就問；現在 checkout 團隊在三樓，payments 團隊在另一層樓，app 小組有一半人在台中遠端工作。

那個月，checkout 團隊要支援海外買家用美金付款。tech lead 美華把訂單 API 的 `total` 欄位從整數（新台幣元）改成字串（例如 `"1234.50"`），再加上一個 `currency` 欄位。程式碼 review 很順利，測試全部通過，因為 checkout 自己的測試只驗證 checkout 自己的行為。

上線後一個小時，三件事接連發生。payments 團隊的請款服務把 `total` 當整數比較，遇到字串直接丟出例外，所有新訂單卡在「待請款」；行動 app 的舊版本解析 JSON 失敗，訂單頁一片空白；seller 團隊的賣家後台對帳報表把 `"1234.50"` 當成 123450 元，一個賣家打電話來問為什麼營收暴增一百倍。

事後檢討時，payments 團隊說：「我們找不到訂單 API 的文件，只好去讀 checkout 的程式碼，再看 production 回傳的樣子。」app 小組說他們看的是 wiki 上一份一年多前的頁面，那時 `total` 還叫 `amount`。美華則說：「我不知道有這麼多人在用這個欄位，我以為這是我們內部的格式。」

同一週，checkout 團隊的小芸被指派調整付款重試的邏輯。小芸在程式裡看到 `max_attempts = 3`，wiki 上寫的是 5，Slack 搜尋結果裡有人說「金流商規定最多 3 次」，也有人說「那是以前的事」。當初寫這段程式的人已經離職。小芸花了兩天才從一封舊郵件找到答案：金流商的合約規定同一筆交易 10 分鐘內最多重送 3 次，超過會被當成詐欺而封鎖商家帳號。

這兩件事的共同點是：**知識存在，但不在需要它的人手上**。程式碼說明了系統「怎麼做」，卻沒有說明「為什麼這樣做」、「別人可以依賴什麼」、「改它會影響誰」。這一章要處理的，就是這些寫不進程式碼、卻決定系統能不能被安全修改的知識。

## 17.2 程式碼說不出的事：文件為什麼存在

### 程式碼與文件各自回答什麼

很多工程師相信「好的程式碼自己會說話」。這句話有一半是對的：清楚的命名、短小的函式、好的型別，確實能讓讀者看懂程式**做了什麼**。但有幾類資訊，再好的程式碼也表達不出來：

- **為什麼**：`max_attempts = 3` 是金流商合約規定、一次事故後的保守設定，還是隨手寫的數字？三種答案代表三種完全不同的修改風險。
- **承諾**：`total` 是 checkout 對外承諾的欄位，還是剛好被看見的內部細節？程式碼只呈現現在的樣子，不會告訴你哪些部分「可以依賴」。
- **怎麼用**：一個新加入 search 團隊、要做「買過的商品」推薦的工程師要串接訂單 API，真正需要的是「先呼叫哪個 endpoint、要帶什麼、失敗怎麼處理」，而不是整個 checkout 的原始碼。
- **被否決的選項**：當初為什麼不用 message queue？如果沒寫下來，下一個人會花兩週重新評估一次，或者在不知道原因的情況下把它改回去。

所以文件與程式碼不是二選一，而是分工：**程式碼、測試與 schema 是可執行的真相（executable truth），文件負責意圖、承諾、導航與判斷**。能從程式碼可靠推導出來的東西，應該從程式碼產生；推導不出來的東西，才是文件真正的價值所在。

### 為什麼工程師總是不寫文件

《Software Engineering at Google》（以下簡稱 SWE 書）在文件那一章坦白承認，工程師普遍覺得文件難寫，原因很具體：很多工程師把寫作看成和寫程式不同的技能，也不覺得自己擅長；寫文件被看成是「工作之外」的額外負擔；寫的人付出成本，受益的卻常常是別人，而且是幾個月以後；文件和程式碼放在不同的系統裡，改程式碼時根本想不到要改文件。

但同一章也列出寫文件對作者本身的好處。最被低估的一個是：**寫文件會逼你把設計想清楚**。如果你沒辦法用三句話解釋一個 API 的行為，問題通常不在你的文筆，而在 API 本身太複雜。另一個好處是減少重複的問題：每個被文件回答的問題，都是一次不必被打斷的專注時間。

在 8 人團隊裡，知識靠口耳相傳還算可行；到了 40 人，同一個問題可能被問十次，而且回答的人每次說法不一樣。第 6 章提過的規模化原則在這裡同樣成立：**和人數線性成長的人工溝通成本，是需要被制度化的訊號**。文件就是把「問人」變成「查得到」的制度。

> [!warning] 常見誤解
> 「文件寫越多越好。」錯。一份沒人維護的長文件，比一份三段話但正確的短文件更有害，因為它會讓讀者自信地做錯事。文件的目標不是篇幅，而是讓正確的讀者在最短時間內建立正確的心智模型。

## 17.3 先問讀者是誰

### 讀者的三個維度

寫文件最常見的錯誤，是寫給「所有人」，結果誰都看不懂。SWE 書建議先界定讀者，常用的維度有三個：

- **經驗程度**：資深工程師需要精確的參數與邊界條件；新人需要先知道整體長什麼樣子。
- **領域知識**：search 團隊的工程師很懂程式，但不知道「授權」和「請款」在金流裡是兩個步驟。
- **目的**：讀者是來找一個特定答案，還是來建立整體理解？

SWE 書把第三點描述成兩種讀者：**seeker**（尋找者）知道自己要找什麼，例如「訂單 API 的錯誤碼 409 是什麼意思」；**stumbler**（漫遊者）只有模糊的需求，例如「我剛加入 search 團隊，checkout 到底是怎麼運作的」。原書的觀點是：seeker 需要的是**一致性**，例如每份 reference 都用相同的結構，讓他們能快速掃到答案；stumbler 需要的是**清晰**，例如開頭先有概觀或一句話摘要，再引導到細節。

另一個常見的區分是 **customer** 與 **provider**：customer 是使用你系統的人（payments 團隊呼叫訂單 API），provider 是維護你系統的人（checkout 團隊自己）。給 customer 的文件應該只談介面與承諾；給 provider 的文件可以談內部實作。Harbor 的 `total` 事故部分源於這兩者沒有分開：外部團隊只能讀內部程式碼，於是內部細節自然變成了外部依賴（這正是第 5 章 Hyrum's Law 的情境）。

### 每份文件開頭先回答五個問題

一個實用的習慣是讓每份文件的前幾行回答 **who、what、when、where、why**：

```text
Who   這份文件寫給誰？         → 要串接訂單 API 的內部團隊
What  它涵蓋什麼、不涵蓋什麼？ → 建立與查詢訂單；不含退款（見 refunds.md）
When  什麼時候寫、何時複查？   → 2024-08 建立，每 90 天複查
Where 正本在哪裡？             → checkout repo 的 docs/api/orders.md
Why   讀完能做到什麼？         → 能在一天內完成串接並正確處理錯誤
```

這五行看起來簡單，但它強迫作者做出取捨：一份文件只服務一群讀者、一個目的。當你發現「why」寫不出一句話，通常代表這份文件想做的事太多，應該拆開。

## 17.4 文件的種類：從 SWE 分類到 Diátaxis

### SWE 書的五種文件

SWE 書把工程文件分成幾類，每一類有不同的讀者與維護方式：

| 類型 | 回答什麼 | Harbor 的例子 | 維護特性 |
|---|---|---|---|
| **Reference**（參考文件，含程式碼註解） | 這個介面精確地做什麼 | 訂單 API 每個欄位的型別、單位、錯誤碼 | 必須和程式碼同步，最好自動產生 |
| **Design doc**（設計文件） | 我們打算怎麼解決一個問題、為什麼 | 「支援多幣別訂單」的設計 | 動工前寫，實作後主要作為決策的歷史紀錄 |
| **Tutorial**（教學） | 新手如何從零完成第一件事 | 「30 分鐘內在本機建立一筆測試訂單」 | 每一步都要能照做，環境改變就會壞 |
| **Conceptual**（概念文件） | 系統為什麼長這樣、核心概念是什麼 | 「Harbor 的訂單狀態機與金流流程」 | 變動慢，但架構大改時要重寫 |
| **Landing page**（入口頁） | 我該去哪裡找 | checkout 團隊首頁：連到 API、設計、儀表板、值班 | 只放連結與一句說明，不放內容 |

**Landing page** 特別值得一提。很多團隊的 wiki 首頁變成了什麼都往裡丟的大雜燴：會議記錄、半年前的公告、某人的筆記。SWE 書的建議是讓 landing page 像交通指揮：它只負責把讀者導向正確的文件，自己不承載內容。Harbor checkout 團隊重整後的首頁只有八個連結：服務簡介、API reference、串接教學、架構概念、近期 design doc、SLO 儀表板、runbook（第 43 章）、聯絡方式與值班表。

另外幾種文件在本書其他章有專門的討論：記錄單一決策的 ADR 見第 7 章；值班時照著操作的 runbook 見第 43 章；事故後的 postmortem 見第 45 章。它們都遵守本章的原則，只是讀者與時機不同。

### Diátaxis：用兩個問題替文件分類

SWE 書的分類來自 Google 的實務；業界另一個被廣泛採用的框架是 **Diátaxis**（由 Daniele Procida 提出）。它用兩個問題把文件分成四類：讀者現在是要「動手做」還是「理解」？讀者是在「學習」還是在「工作」？

```text
                    動手做（action）
                          │
         Tutorial         │        How-to guide
     （學習中，跟著做）    │    （工作中，解決特定問題）
   「第一次建立測試訂單」  │   「如何對一筆訂單補發通知」
                          │
 學習 ────────────────────┼──────────────────── 工作
 （acquisition）          │            （application）
                          │
       Explanation        │         Reference
     （學習中，想理解）    │    （工作中，查精確資訊）
   「為什麼訂單要分授權    │   「POST /orders 的欄位與
     與請款兩階段」        │     錯誤碼一覽」
                          │
                    理解（cognition）
```

這張圖的讀法是：先問讀者的狀態，再決定文件該長什麼樣子。左上的 **tutorial** 帶新手完成一件保證會成功的事，重點是建立信心，不需要解釋所有選項。右上的 **how-to guide** 給已經會基本操作的人解決特定問題，假設讀者知道自己要什麼。右下的 **reference** 像字典，精確、完整、結構一致，讓 seeker 快速查到答案。左下的 **explanation** 談背景、設計理由與取捨，讓 stumbler 建立心智模型。

Diátaxis 最有用的地方，是它解釋了為什麼很多文件「什麼都寫了卻沒人能用」：它們把四種東西混在同一頁。一份串接教學寫到一半開始解釋金流的歷史，再插入一張 40 個欄位的表格，新手被細節淹沒，老手找不到表格在哪裡。拆成四份短文件，彼此互相連結，每一份都更容易寫、也更容易維護。

SWE 的分類與 Diátaxis 並不衝突：SWE 的 tutorial、reference、conceptual 大致對應 Diátaxis 的 tutorial、reference、explanation；design doc 與 landing page 是 Diátaxis 沒有涵蓋的工程內部文件。實務上可以用 Diátaxis 規劃「給使用者的文件」，用 SWE 的分類規劃「團隊內部的工程文件」。

> [!warning] 常見誤解
> 「README 就是全部的文件。」README 是很好的 landing page，但當它同時想當教學、參考與設計說明時，就會長成上千行、沒人讀完的檔案。讓 README 回答「這是什麼、怎麼開始、去哪裡找更多」，其他內容拆到 `docs/` 底下。

## 17.5 Reference 文件與程式碼註解

### 註解寫「為什麼」與「承諾」

程式碼註解是離程式最近的 reference 文件。SWE 書區分了幾種層級：檔案層級的註解說明這個檔案的用途；類別層級的註解說明這個型別代表什麼、該怎麼使用；函式層級的註解說明呼叫者需要知道的承諾。

最常見的錯誤是註解重述程式碼：

```python
# not-runnable
# 不好：只是把程式翻譯成中文
attempts += 1  # attempts 加一

# 好：說明程式碼本身無法表達的限制與來源
# 金流商合約（2023 版第 7.2 條）：同一筆交易 10 分鐘內最多重送 3 次，
# 超過會被視為異常並暫停商家帳號。調整前請先確認合約版本。
MAX_ATTEMPTS = 3
```

第二個註解救了小芸兩天。它說明了數字的來源、違反的後果，以及修改前該做什麼。這種「為什麼」的註解，是任何重構工具或 AI 都無法從程式碼本身推導出來的。

函式層級的註解則要寫出呼叫者需要的承諾：輸入的單位與範圍、回傳值的意義、會丟出哪些錯誤、是否 thread-safe、是否冪等（同樣的請求做兩次，結果和做一次相同）。一個簡單的檢查方式是：**如果呼叫者必須讀函式內部才能正確使用它，註解就不完整**。

### 能產生的就不要手寫

Reference 文件最大的敵人是漂移：程式改了，文件沒改。最可靠的解法是讓 reference 從單一來源自動產生。Python 可以用 Sphinx 從 docstring 產生 API 文件；HTTP API 可以從 OpenAPI 規格產生互動式文件頁；命令列工具的 `--help` 輸出可以直接嵌入使用說明；設定檔的欄位說明可以從設定的 schema 產生。

自動產生不代表不需要人。產生器只能搬運你寫在 docstring 或 schema 裡的內容；如果 schema 只寫了 `total: string`，產生出來的文件也只會說「total 是字串」，不會說它的單位、格式與精度。所以真正的工作是**把語意寫進單一來源**，再讓工具把它散布到各處。

## 17.6 Docs as Code：讓文件和程式碼走同一條路

### 為什麼要把文件當程式碼

SWE 書提出一個核心主張：文件應該像程式碼一樣被對待。具體來說，文件要有明確的 owner、放在版本控制裡、修改要經過 review、問題要能被追蹤、要定期被評估是否仍然正確。業界把這種做法稱為 **docs as code**：文件用純文字格式（通常是 Markdown）寫成，和程式碼放在同一個 repository，走同一套 pull request、review 與 CI 流程。

這帶來幾個直接的好處。第一，程式碼與文件可以在**同一個 commit** 裡修改，review 的人能同時看到兩者，「改了 API 卻忘了改文件」會在 review 時被發現。第二，文件有完整的歷史，可以知道某段描述是何時、由誰、因為哪個變更而寫的。第三，文件可以被自動檢查，就像程式碼會被 lint 與測試一樣。

```text
  工程師修改 checkout/api/orders.py 與 docs/api/orders.md
                   │
                   ▼
            Pull request（同一個）
                   │
     ┌─────────────┼──────────────┬──────────────────┐
     ▼             ▼              ▼                  ▼
  程式碼測試   文件 build     連結檢查          範例程式執行
              （能否產生網站） （有沒有死連結）  （doctest／範例 API 呼叫）
     │             │              │                  │
     └─────────────┴──────┬───────┴──────────────────┘
                          ▼
           CODEOWNERS 指定的 reviewer 核准
           （程式碼 owner ＋ 文件 owner）
                          ▼
             合併 → 自動發布文件網站
```

這條流水線的重點在中間那排檢查。文件 build 確保格式正確、可以產生網站；連結檢查找出指向已刪除頁面的死連結；範例程式執行則確保文件裡的程式碼範例真的能跑。最後由 **CODEOWNERS**（一種依檔案路徑指定 reviewer 的設定檔）確保改到 API 文件時，負責的團隊一定會看到。

### 讓文件裡的範例被測試

文件中最容易過時的是範例。Python 內建的 `doctest` 模組可以把 docstring 裡的互動範例當成測試執行：

```python
import doctest


def shipping_fee(total: int, region: str) -> int:
    """回傳運費（新台幣元，整數）。

    total 是訂單商品金額（元）；滿 1,000 元免運，離島加收 60 元。

    >>> shipping_fee(999, "taipei")
    80
    >>> shipping_fee(1000, "taipei")
    0
    >>> shipping_fee(500, "penghu")
    140
    """
    if total >= 1000:
        return 0
    return 80 + (60 if region in {"penghu", "kinmen", "matsu"} else 0)


print(doctest.testmod())
```

```text
TestResults(failed=0, attempted=3)
```

這三個 `>>>` 範例同時是文件與測試。如果有人把免運門檻改成 1,200 元卻沒更新 docstring，CI 會在 `shipping_fee(1000, "taipei")` 這一行失敗，逼作者同時修正文件。HTTP API 也可以用同樣的精神：把文件裡的 `curl` 範例在 staging 環境實際執行一次，確認回應格式和文件一致。

### 實務上的工具與流程

常見的 docs as code 工具組合包括：用 MkDocs、Sphinx 或 Docusaurus 這類靜態網站產生器把 Markdown 變成可搜尋的網站；用連結檢查工具找死連結；用 Vale 這類文字 linter 檢查用語一致（例如統一寫「訂單」而不是混用「訂單」「order」「單」）。這些工具的選擇不重要，重要的是文件和程式碼走同一個 review 與 CI 流程。

SWE 書也建議文件 review 可以分成三種角度：**technical review** 由熟悉系統的人檢查內容是否正確；**audience review** 由不熟悉系統、接近目標讀者的人檢查是否看得懂；**writing review** 由擅長寫作的人（有時是 technical writer）檢查結構與表達。Harbor 的做法是：API 文件的 PR 至少要有一位 checkout 工程師（technical）和一位其他團隊的工程師（audience）核准。後者常常抓到前者完全沒注意到的問題，例如「文件裡說的『授權』是什麼意思？」

> [!tip] 先從觸發條件開始
> 在 PR 模板加上「我已更新文件」的勾選框，效果通常很有限，因為勾選很快會變成反射動作。更有效的做法是依路徑觸發：修改 `checkout/api/` 底下的檔案時，CI 自動檢查 `docs/api/` 是否也有變更；如果沒有，要求作者在 PR 描述說明「為什麼不需要更新文件」。

Docs as code 也有邊界。產品使用說明、對非工程師的內部流程、早期的腦力激盪，可能更適合放在協作編輯工具裡。原則是：**描述程式碼行為與承諾的文件，跟著程式碼走**；其他文件至少要有 owner 與正本位置。

## 17.7 Design Doc：在寫程式之前先寫下來

### 為什麼在動工前寫

**Design doc**（設計文件）是在實作一個重要變更之前，描述「要解決什麼問題、打算怎麼解決、考慮過哪些替代方案、有哪些風險」的文件。它的價值來自一個簡單的成本事實：在文件上改設計，只需要改幾段文字；寫完程式後改設計，要改程式、測試、資料與所有依賴它的團隊。

Harbor 的多幣別事故，如果事前有一份 design doc，並請 payments、app 小組與 seller 團隊 review，「把 `total` 改成字串」這一行幾乎一定會被問：「誰在讀這個欄位？舊版 app 怎麼辦？」在文件上，這個問題的成本是一則留言；在 production，它的成本是三個團隊的事故。

### 什麼時候需要 design doc

不是每個變更都需要 design doc。修一個 bug、加一個內部函式，寫 design doc 只是浪費時間。Harbor 的經驗法則是，符合下列任一條件就寫：

- 影響其他團隊，或改變對外的 API 與資料格式
- 引入新的儲存系統、資料模型或關鍵依賴
- 涉及安全、隱私、金流或法規
- 預計超過兩週的工作量
- 難以回復的決策（第 7 章的 one-way door）

規模也可以彈性調整。一個中等變更可能只需要一到兩頁的「mini design doc」，一個跨團隊的平台改造可能需要十幾頁。重點不是篇幅，而是讓關鍵假設在還便宜的時候被挑戰。

### 一份 design doc 的結構

各家公司的模板不同，但好的 design doc 通常包含以下部分：

| 段落 | 回答什麼 | 常見的錯誤 |
|---|---|---|
| Context 與 scope | 現在的狀況、為什麼要改、範圍多大 | 寫成產品宣傳，沒有說清楚現況的問題 |
| Goals 與 non-goals | 成功的標準；明確**不**處理的事 | 沒有 non-goals，導致 review 時範圍不斷擴大 |
| 設計概觀 | 一張圖加幾段文字，讓讀者五分鐘內懂整體 | 直接跳進細節 |
| 詳細設計 | API、資料模型、資料流、狀態轉換 | 列出每個 class，卻沒寫資料怎麼流動 |
| Alternatives considered | 考慮過哪些方案、為什麼不選 | 只寫選中的方案，或把替代方案寫成稻草人 |
| Cross-cutting concerns | 安全、隱私、可靠性（SLO，第 32 章）、可觀測性（第 33 章）、容量、成本 | 「之後再處理」 |
| Rollout、migration 與 rollback | 怎麼漸進上線、舊資料怎麼轉、出事怎麼退 | 假設一次就能全部切換 |
| Open questions | 還沒有答案、需要 reviewer 幫忙判斷的問題 | 假裝所有問題都已解決 |

其中 **non-goals** 與 **alternatives considered** 是新手最常省略、資深工程師最先看的兩段。Non-goals 讓 review 聚焦，避免每個 reviewer 都要求加一個功能；alternatives 證明作者真的思考過，也讓未來的人知道某個看似更好的方案為什麼當初沒有被選。

下面是 Harbor 重寫後的多幣別 design doc 節錄：

```text
Design Doc：訂單支援多幣別（v2，狀態：Approved）
作者：美華｜Reviewers：payments（小林）、app 小組（雅婷，search 團隊）、seller（家明）、platform（志明）

Context
  海外買家需要以美金付款。現有 total 欄位為整數新台幣元，
  被至少 4 個服務與所有 app 版本讀取（來源：API gateway 日誌，近 30 天）。

Goals
  - 訂單可記錄任意 ISO 4217 幣別的金額
  - 既有 consumer 不需任何修改即可繼續運作
Non-goals
  - 匯率換算與顯示（由另一份 design doc 處理）
  - 退款流程改造

Design
  保留 total（整數，新台幣元，語意不變；海外訂單填換算後金額）。
  新增 amount: { value: "1234.50", currency: "USD" }，value 以字串表示避免浮點誤差。

Alternatives considered
  A. 直接把 total 改為字串 → 否決：破壞所有既有 consumer（見 2024-07 事故）
  B. 新增 /v2/orders → 暫不採用：遷移成本高，目前的需求以新增欄位即可滿足

Rollout
  1. 新欄位上線，僅內部帳號可見  2. payments 與 seller 改讀 amount
  3. 開放海外買家  4. total 何時淘汰另開 deprecation 計畫（第 18 章）
```

這份節錄有幾個值得注意的地方：context 引用了實際的使用資料，而不是猜測；alternatives 直接寫出被否決的方案和理由；rollout 把「淘汰舊欄位」明確留給另一個流程，而不是含糊帶過。

### Design doc 的 review

Design doc 的 review 和 code review（第 16 章）有一個關鍵差異：code review 檢查「這段程式是否正確實作了意圖」，design review 檢查「這個意圖本身是否正確」。所以好的 design reviewer 不看錯字，而是問這類問題：

- 「如果依賴 X 掛掉 10 分鐘，使用者會看到什麼？」
- 「這個設計在流量變成十倍時，哪裡先撐不住？」
- 「上線一半發現問題，要怎麼退回？資料會不會已經寫成新格式？」
- 「哪些團隊會受到影響？他們看過這份文件嗎？」

Harbor 的流程分三步：先給一兩位熟悉領域的人看草稿，確認方向沒有大錯；再發給所有受影響的團隊，用文件留言非同步討論；只有留言解決不了的爭議，才開 design review 會議。最後由文件開頭列出的 approver 簽核，並把狀態從 Draft 改成 Approved。

### Design doc 的生命週期

Design doc 有一個常被忽略的特性：**它描述的是決策當下的意圖，不是系統現在的樣子**。實作過程中，設計一定會有調整；上線一年後，系統可能已經和文件差很多。

因此不要試圖讓 design doc 永遠和系統同步，那會讓它變成一份永遠過時的 reference。比較好的做法是：在文件開頭標示狀態（Draft、In review、Approved、Implemented、Superseded），實作完成後補一段「實作時的差異」；把需要長期維護的部分抽出來，系統的現況寫進 conceptual 與 reference 文件，重要的決策寫成 ADR（第 7 章）。被新設計取代時，標上 Superseded 並連到新文件。

> [!warning] 常見誤解
> 「Design doc 是瀑布式開發，會拖慢速度。」Design doc 不要求事先預測每一行程式，也不禁止邊做邊學。它要求的是：在投入大量工程時間前，把最貴的假設攤開來讓別人挑戰。原型可以先做，甚至應該先做，再把原型的發現寫進 design doc。

## 17.8 API Contract：把承諾寫成機器讀得懂的格式

### Contract 包含什麼

**API contract**（API 契約）是一個元件對使用者承諾的完整行為：可以送什麼、會收到什麼、出錯時怎麼表現、哪些行為可以依賴。它比「欄位清單」大得多：

| 面向 | 內容 | 訂單 API 的例子 |
|---|---|---|
| 結構 | 欄位、型別、必填與否 | `cart_id` 必填字串 |
| 語意 | 單位、格式、精度、時區 | `total` 是整數新台幣元；時間為 UTC 的 RFC 3339 格式 |
| 錯誤 | 錯誤碼、錯誤格式、是否可重試 | 409 代表同一個 idempotency key 被用在內容不同的請求上，不可重試 |
| 冪等性 | 重送同一請求的結果 | 相同 `idempotency_key` 在 24 小時內只會建立一筆訂單 |
| 順序與分頁 | 排序保證、分頁方式 | 依建立時間遞減；用 cursor 分頁，不保證頁數穩定 |
| 非功能 | 速率限制、延遲目標、可用性 | 每個 client 每秒 50 次；p99 延遲目標 500 ms |
| 演進 | 相容性政策、淘汰流程 | 只做向後相容的新增；破壞性變更需開新版本並至少保留 6 個月 |

最後一列尤其重要。第 5 章的 Hyrum's Law 告訴我們：只要有夠多使用者，系統所有可觀察的行為都會被某人依賴。Contract 無法阻止這件事，但它劃出一條線：**寫在 contract 裡的，是我們承諾維持的；沒寫的，是我們保留改變權利的**。當 Harbor 的賣家後台依賴了 contract 沒有承諾的排序，checkout 團隊改變排序時仍應該通知他們，但責任的歸屬至少是清楚的。

### Schema first：OpenAPI 與 protobuf

把 contract 寫成散文很容易產生歧義。更好的方式是寫成機器可讀的 **schema**（結構定義），再從它產生文件、client 程式庫、server 骨架、mock 與驗證器。這種先寫 schema 再寫實作的方式稱為 **schema first**（或 API first）。

HTTP／JSON API 最常用的是 **OpenAPI**：用 YAML 或 JSON 描述每個 endpoint 的路徑、參數、請求與回應格式。Harbor 的訂單 API 節錄如下：

```yaml
openapi: 3.1.0
info: { title: Harbor Orders API, version: 1.4.0 }
paths:
  /orders:
    post:
      summary: 建立訂單（冪等）
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema: { type: string, maxLength: 64 }
      requestBody:
        content:
          application/json:
            schema: { $ref: "#/components/schemas/CreateOrder" }
      responses:
        "201": { description: 已建立 }
        "409": { description: 相同 Idempotency-Key 但內容不同，不可重試 }
components:
  schemas:
    # CreateOrder（請求內容）的定義在此省略
    Order:
      type: object
      required: [order_id, total, status]
      properties:
        order_id: { type: string }
        total:
          type: integer
          description: 新台幣元，含稅，不含運費
        status:
          type: string
          enum: [pending, paid, cancelled]
          description: Client 必須能處理未知的新狀態值
```

注意 `description` 欄位承載了 schema 型別無法表達的語意：單位、含不含稅、client 對未知 enum 值的義務。這些描述會被產生到文件網站上，也會出現在自動產生的 client 程式碼註解裡。

服務之間的內部呼叫常用 **Protocol Buffers**（protobuf）搭配 gRPC。protobuf 的特點是每個欄位都有一個**欄位編號**，序列化成二進位時只寫編號、不寫名稱：

```text
message Order {
  string order_id = 1;
  int64  total    = 2;   // 新台幣元
  Status status   = 3;
  Money  amount   = 5;   // 多幣別金額，2024-09 新增
  reserved 4;            // 曾經是 coupon_code，已移除；編號永不重用
  reserved "coupon_code";
}
```

這個設計決定了 protobuf 的相容性規則：只要欄位編號與型別不變，改欄位名稱不影響二進位格式（但若同一份資料也以 JSON 格式傳輸，JSON 用的是欄位名稱，改名仍然是破壞性的）；新增欄位時，舊程式讀到不認識的編號會把它當成未知欄位，不會出錯。最危險的事是**重用一個已刪除欄位的編號**：舊 client 會把新欄位的資料當成舊欄位解讀，產生無聲的資料錯誤。所以刪除欄位時要用 `reserved` 把編號和名稱鎖住。

### 一個 contract，多種產物

```text
                       orders.yaml / order.proto
                     （contract 的單一正本，放在 repo）
                                  │
        ┌──────────────┬──────────┼───────────┬────────────────┐
        ▼              ▼          ▼           ▼                ▼
   文件網站       Client SDK   Server 驗證   Mock server    相容性檢查
 （reference）  （各語言）    （拒絕不合格  （consumer 在   （CI 比較新舊
                              的請求）      開發時使用）   版本，擋下破壞性變更）
```

這張圖說明了 schema first 的真正價值：所有產物都從同一個正本產生，所以它們不可能彼此矛盾。文件不會說 `total` 是整數，而 SDK 卻把它當字串。最右邊的相容性檢查，是下一節的主題。

## 17.9 相容性：哪些改變會弄壞別人

### 兩個方向的相容

**Backward compatibility**（向後相容）指新版本能正確處理舊版本產生的輸入：新的 server 仍能接受舊 client 的請求。**Forward compatibility**（向前相容）指舊版本能容忍新版本產生的輸入：舊的 client 收到新 server 多出來的欄位時不會壞掉。

兩者都重要，因為在真實系統裡，新舊版本永遠同時存在。server 部署是漸進的（第 29 章的 canary），同一時間會有新舊兩種 server；行動 app 無法強制所有人更新，一兩年前的版本可能還在某支手機上執行。Harbor 的 app 小組統計過，任何時候都有約 5% 的使用者停留在半年以前的版本。

### 變更的分類

| 變更 | 對舊 client 的影響 | 判斷 |
|---|---|---|
| 新增 endpoint | 無 | 安全 |
| 回應新增欄位 | 若 client 忽略未知欄位則無影響 | 通常安全，前提要寫進 contract |
| 請求新增**選填**欄位 | 舊 client 不送，使用預設值 | 安全 |
| 請求新增**必填**欄位 | 舊 client 不會送，請求被拒絕 | 破壞性 |
| 回應移除欄位或改名 | 讀它的 client 會出錯 | 破壞性 |
| 改變欄位型別或單位 | 解析失敗，或更糟，解析成功但意義錯誤 | 破壞性 |
| Enum 新增值（回應） | 窮舉處理每個值的 client 可能出錯 | 有條件，要事先要求 client 處理未知值 |
| 收緊驗證（例如字串長度上限從 100 改 50） | 原本合法的請求被拒絕 | 破壞性 |
| 改變錯誤碼或錯誤格式 | 依錯誤碼重試或顯示訊息的 client 出錯 | 破壞性 |
| 改變語意但格式不變（例如 `total` 從含運改成不含運） | 程式不會報錯，但結果錯誤 | 最危險的破壞性變更 |

最後一列值得特別強調。型別改變在 CI 的 schema 比對中看得出來（17.11 節的程式會把它判成 BREAKING），而且很多 consumer 會在解析時立刻出錯；語意改變則連 schema 比對都通過，可能幾週後才在對帳時被發現。要注意的是，型別改變也不保證會「大聲」失敗：Harbor 的賣家後台遇到字串 `"1234.50"` 時沒有報錯，而是去掉小數點後讀成 123450 元。所以真正的防線是在合併前就攔下變更，而不是指望 consumer 會當場壞掉。

### 讓 client 能安全地面對變化

相容性是雙方的責任。Server 端要避免破壞性變更；client 端要寫成能容忍合理的演進，這種做法常被稱為 **tolerant reader**：只讀自己需要的欄位、忽略不認識的欄位、對未知的 enum 值有預設處理。Harbor 的 contract 明確寫著「client 必須忽略未知欄位，並把未知的 status 當成『處理中』顯示」，這讓 checkout 團隊未來新增狀態時不必等所有 app 更新。

但容忍也有限度。網路協定界有一句常被引用的 **Postel's law**：「送出時要保守，接收時要寬容」。過度寬容的 server 會接受各種格式錯誤的請求，而這些「被接受的錯誤」很快就會因為 Hyrum's Law 變成別人的依賴，讓你永遠無法收緊驗證。實務上的平衡是：**對未知的新欄位寬容，對格式錯誤的已知欄位嚴格**。

### 錯誤也是 contract

錯誤回應常被當成附屬品，但 client 的重試邏輯、使用者看到的訊息、告警規則，都依賴錯誤的格式與語意。好的錯誤 contract 至少要說明：錯誤碼的意義、是否可重試、需不需要使用者採取動作。HTTP API 可以參考 RFC 9457（Problem Details for HTTP APIs）定義的標準錯誤格式，用 `type`、`title`、`status`、`detail` 等欄位描述錯誤，讓不同服務的錯誤長得一致。

### 版本化：最後手段，不是預設手段

當破壞性變更無法避免時，就需要開一個新版本，例如 `/v2/orders` 或新的 protobuf package。但版本化有真實的成本：新舊版本要同時維護、測試與監控，而且舊版本的淘汰往往比想像中困難（這是第 18 章的主題）。所以大多數團隊的原則是：**優先用新增的方式演進**，例如新增 `amount` 欄位而不是改變 `total`；只有在新增無法解決、或舊設計有安全問題時，才開新版本。

### 把相容性檢查放進 CI

人工判斷相容性容易漏看。比較可靠的做法是在 CI 中自動比較新舊 schema：protobuf 生態系有像 `buf breaking` 這樣的工具，可以依規則偵測刪除欄位、改型別、重用編號等破壞性變更；OpenAPI 也有比較兩版規格差異的工具。偵測到破壞性變更時擋下合併，除非作者明確標示這是新版本並附上遷移計畫。

自動檢查只能看到 schema 層級的差異，看不到語意改變，也看不到 consumer 實際依賴的未文件化行為。這兩個缺口要靠 design review 與第 25 章的 **consumer-driven contract test**（由使用方寫下「我依賴哪些行為」，提供方在 CI 中執行）補上。

## 17.10 文件新鮮度：沒人維護的文件比沒有更糟

### 過時文件的代價

沒有文件時，讀者知道自己不知道，會去問人或讀程式碼。過時的文件更危險：它讓讀者**自信地做錯事**。Harbor 的 app 小組照著一年多前的 wiki 頁面寫程式，花了一天才發現欄位早就改名。更糟的情況發生在 runbook：值班者在半夜照著過時的步驟操作，可能讓事故擴大。

到了 AI 時代，這個代價又被放大。AI coding agent 會把 repository 裡的文件當成 context，過時的文件會讓它自信地產生錯誤的程式碼，而且產生速度比人快得多（17.13 節會再談）。

### Owner：每份文件都要有人負責

**Owner** 是對文件正確性負責、接收回饋並決定何時更新或下架的人或團隊。最好是團隊而不是個人，因為個人會換組或離職；Harbor 的 checkout 文件 owner 是「checkout-team」，由 CODEOWNERS 設定，任何修改都會通知到團隊。

沒有 owner 的文件會慢慢變成「大家都能改、沒人負責」的狀態。Harbor 在整理 wiki 時發現，超過一半的頁面最後修改者已經離職或換組。他們的處理方式是：有人認領的頁面搬進對應 repo 的 `docs/`；沒人認領的頁面加上「未維護，可能過時」的警示橫幅，三個月後沒人認領就封存。

### 新鮮度機制

只有 owner 還不夠，owner 也會忘記。實務上常見的新鮮度機制有三種：

1. **定期複查**：在文件的 metadata 寫下上次複查日期與複查週期，到期時自動開 issue 給 owner。複查的意思是「有人確認過內容仍然正確」，即使內容沒有改，也要更新複查日期。SWE 書描述過 Google 內部的類似做法：文件 metadata 記錄最後複查日期（freshness date），超過期限（例如三個月）就自動寄信提醒 owner。
2. **變更觸發**：文件宣告它描述哪些程式碼路徑，當這些路徑被修改後，文件就被標記為「需要複查」。這比定期複查更精準，因為它在真正可能過時的時刻提醒。
3. **使用回饋**：文件頁面上的「這頁有幫助嗎？」、搜尋時找不到結果的查詢、聊天頻道裡反覆出現的同一個問題，都是文件缺漏或過時的訊號。

Harbor 的文件 metadata 長這樣：

```text
---
owner: checkout-team
last_reviewed: 2024-08-20
review_every_days: 90
covers:
  - checkout/api/
status: current      # current | deprecated | archived
superseded_by:       # 被取代時填入新文件路徑
---
```

`status` 與 `superseded_by` 處理的是文件自己的淘汰。SWE 書也提醒，文件和程式碼一樣需要被淘汰：與其讓過時的頁面在搜尋結果裡和新頁面競爭，不如明確標示「已過時，請改看某某文件」，必要時直接刪除。保留歷史可以靠版本控制，不需要靠留著舊頁面。

### 怎麼知道文件有沒有用

量測文件時要小心第 14 章的 Goodhart's law：如果獎勵「寫了幾頁文件」，你會得到大量沒人讀的頁面。比較有意義的訊號包括：新人完成第一個任務所需的時間、內部支援頻道裡重複問題的數量、搜尋失敗率，以及文件複查逾期的比例。這些訊號都和「讀者是否得到答案」相關，而不是和「作者寫了多少」相關。

## 17.11 動手寫：API 相容性檢查與文件新鮮度 linter

這一節用兩段程式把本章的兩個核心機制做出來：在 CI 中比較新舊 API schema 並擋下破壞性變更，以及檢查文件是否有 owner、是否過期、是否在程式碼改變後被複查。

### 程式一：比較兩版 API schema

```python
# 比較兩版 API schema，把差異分成 BREAKING／WARN／SAFE
OLD = {
    "POST /orders": {
        "request": {"cart_id": ("string", True), "coupon": ("string", False)},
        "response": {"order_id": ("string", True), "total": ("integer", True),
                     "status": ("enum:pending|paid", True)},
    },
    "GET /orders/{id}": {
        "request": {},
        "response": {"order_id": ("string", True), "total": ("integer", True)},
    },
}

NEW = {
    "POST /orders": {
        "request": {"cart_id": ("string", True),                   # coupon 被拿掉
                    "idempotency_key": ("string", True)},        # 新增必填欄位
        "response": {"order_id": ("string", True), "total": ("string", True),  # 型別改變
                     "status": ("enum:pending|paid|on_hold", True),            # enum 多一個值
                     "currency": ("string", True)},                            # 回應新增欄位
    },
    # GET /orders/{id} 被移除
    "GET /v2/orders/{id}": {
        "request": {},
        "response": {"order_id": ("string", True), "total": ("string", True)},
    },
}


def enum_values(t):
    return set(t.split(":", 1)[1].split("|")) if t.startswith("enum:") else None


def compare(old, new):
    findings = []
    for ep in old.keys() - new.keys():
        findings.append(("BREAKING", ep, "endpoint 被移除，既有呼叫會 404"))
    for ep in new.keys() - old.keys():
        findings.append(("SAFE", ep, "新增 endpoint"))
    for ep in old.keys() & new.keys():
        o, n = old[ep], new[ep]
        # 請求：呼叫者送進來的東西
        for f, (t, req) in n["request"].items():
            if f not in o["request"]:
                level = "BREAKING" if req else "SAFE"
                findings.append((level, ep, f"請求新增{'必填' if req else '選填'}欄位 {f}"))
        for f in o["request"].keys() - n["request"].keys():
            findings.append(("WARN", ep, f"請求移除欄位 {f}：舊 client 仍會送，server 必須忽略而非拒絕"))
        # 回應：呼叫者讀取的東西
        for f, (t, _) in o["response"].items():
            if f not in n["response"]:
                findings.append(("BREAKING", ep, f"回應移除欄位 {f}"))
                continue
            nt = n["response"][f][0]
            oe, ne = enum_values(t), enum_values(nt)
            if oe is not None and ne is not None:
                if oe - ne:
                    findings.append(("BREAKING", ep, f"{f} 移除 enum 值 {sorted(oe - ne)}"))
                if ne - oe:
                    findings.append(("WARN", ep, f"{f} 新增 enum 值 {sorted(ne - oe)}：窮舉 switch 的 client 可能出錯"))
            elif t != nt:
                findings.append(("BREAKING", ep, f"回應欄位 {f} 型別 {t} → {nt}"))
        for f in n["response"].keys() - o["response"].keys():
            findings.append(("SAFE", ep, f"回應新增欄位 {f}（前提：client 忽略未知欄位）"))
    order = {"BREAKING": 0, "WARN": 1, "SAFE": 2}
    return sorted(findings, key=lambda x: (order[x[0]], x[1], x[2]))


results = compare(OLD, NEW)
for level, ep, msg in results:
    print(f"{level:<8} {ep:<20} {msg}")
breaking = sum(1 for r in results if r[0] == "BREAKING")
print(f"\n共 {len(results)} 項差異，其中 {breaking} 項 BREAKING → {'擋下合併' if breaking else '可以合併'}")
```

執行結果：

```text
BREAKING GET /orders/{id}     endpoint 被移除，既有呼叫會 404
BREAKING POST /orders         回應欄位 total 型別 integer → string
BREAKING POST /orders         請求新增必填欄位 idempotency_key
WARN     POST /orders         status 新增 enum 值 ['on_hold']：窮舉 switch 的 client 可能出錯
WARN     POST /orders         請求移除欄位 coupon：舊 client 仍會送，server 必須忽略而非拒絕
SAFE     GET /v2/orders/{id}  新增 endpoint
SAFE     POST /orders         回應新增欄位 currency（前提：client 忽略未知欄位）

共 7 項差異，其中 3 項 BREAKING → 擋下合併
```

逐段解讀：

1. `OLD` 與 `NEW` 是簡化版的 schema。真實系統中，它們分別來自 main branch 與 PR branch 上的 OpenAPI 檔案或 `.proto` 檔案，CI 會把兩者都取出來比較。
2. 程式最關鍵的設計是**把請求與回應分開判斷**，因為兩者的相容方向相反。請求是 client 送給 server 的：server 新增必填欄位，舊 client 不會送，所以是破壞性；server 新增選填欄位則安全。回應是 server 送給 client 的：server 移除欄位，讀它的 client 會壞；server 新增欄位，只要 client 忽略未知欄位就安全。
3. `total` 從 `integer` 變成 `string` 被判為 BREAKING，這正是 17.1 節的事故。如果 Harbor 當時有這個檢查，美華的 PR 會在 CI 就被擋下，逼美華回頭寫 design doc。
4. Enum 新增值被歸為 WARN 而不是 SAFE。它在 schema 層級是「新增」，但如果 client 用窮舉的 `switch` 處理每個狀態，遇到 `on_hold` 就可能走到錯誤分支。這類情況的處理方式是事先在 contract 寫明「client 必須處理未知值」，然後才能把它降為 SAFE。
5. 請求移除 `coupon` 也是 WARN：舊 client 仍然會送這個欄位，server 若設定成「遇到未知欄位就拒絕」，就會變成破壞性變更。
6. 最後一行把結果變成一個決定：有 BREAKING 就擋下合併。真實的工具還會支援「這次是有意的新版本」的例外標記，並要求附上遷移計畫。

這個程式**看不到**的東西同樣重要：它不知道 `total` 的單位從元改成分（型別都是 integer），也不知道哪些 consumer 實際讀了哪些欄位。前者要靠 schema 裡的 description 與 design review，後者要靠存取日誌與 consumer-driven contract test。

### 程式二：文件新鮮度 linter

```python
# 文件新鮮度檢查：owner、複查期限、程式碼漂移
from datetime import date

TODAY = date(2024, 9, 15)

DOCS = [
    # 路徑, owner, 上次複查, 複查週期(天), 這份文件描述的程式碼路徑
    ("docs/checkout/api.md", "checkout-team", date(2024, 8, 20), 90, ["checkout/api/"]),
    ("docs/checkout/retry.md", "checkout-team", date(2023, 12, 1), 180, ["checkout/retry.py"]),
    ("docs/search/index.md", None, date(2024, 5, 2), 90, ["search/indexer/"]),
    ("docs/onboarding.md", "eng-enablement", date(2024, 7, 10), 120, []),
]

# 每個程式碼路徑最近一次被修改的日期（真實系統從 git log 取得）
LAST_CODE_CHANGE = {
    "checkout/api/": date(2024, 9, 2),
    "checkout/retry.py": date(2023, 11, 20),
    "search/indexer/": date(2024, 8, 28),
}


def check(doc):
    path, owner, reviewed, every, code_paths = doc
    problems = []
    if owner is None:
        problems.append("沒有 owner")
    overdue = (TODAY - reviewed).days - every
    if overdue > 0:
        problems.append(f"複查逾期 {overdue} 天")
    for cp in code_paths:
        changed = LAST_CODE_CHANGE.get(cp)
        if changed and changed > reviewed:
            problems.append(f"{cp} 在 {changed} 改過，文件之後沒有複查")
    return path, problems


for path, problems in map(check, DOCS):
    status = "OK  " if not problems else "FIX "
    print(f"{status}{path}")
    for p in problems:
        print(f"      - {p}")
```

執行結果：

```text
FIX docs/checkout/api.md
      - checkout/api/ 在 2024-09-02 改過，文件之後沒有複查
FIX docs/checkout/retry.md
      - 複查逾期 109 天
FIX docs/search/index.md
      - 沒有 owner
      - 複查逾期 46 天
      - search/indexer/ 在 2024-08-28 改過，文件之後沒有複查
OK  docs/onboarding.md
```

逐段解讀：

1. `DOCS` 對應 17.10 節的 metadata 欄位。真實系統會掃描 repo 中所有 Markdown 檔案的 front matter，而不是寫死在程式裡。
2. `docs/checkout/api.md` 在 90 天的週期內，按定期複查的標準是「健康」的；但它描述的 `checkout/api/` 在上次複查之後被改過，所以仍被標記。這就是**變更觸發**比定期複查更精準的地方：多幣別的 PR 合併後，這份文件會立刻被點名。
3. `docs/checkout/retry.md` 的程式碼最近沒有改動，但已超過複查週期 109 天。即使程式沒變，外部世界可能變了，例如金流商換了新版合約，所以仍需要有人確認。
4. `docs/search/index.md` 三個問題同時出現，這是最典型的「孤兒文件」：沒有 owner，所以沒人收到逾期提醒，程式碼改了也沒人更新。修復的第一步永遠是找到 owner，否則其他兩個問題修好了也會再發生。
5. 真實系統中，`LAST_CODE_CHANGE` 來自 `git log -1 --format=%cs -- <path>` 這類查詢；結果可以每週自動開 issue 給 owner，或在 PR 修改 `covers` 路徑時直接留言提醒。

兩段程式背後是同一個想法：**把「人應該記得做的事」變成「機器會提醒的事」**。Contract 檢查在破壞性變更進入 main 之前攔下它；新鮮度檢查在文件悄悄過時之前點名它。

## 17.12 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 所有知識都寫進一份大文件 | 讀者找不到需要的部分，作者沒人敢改 | Harbor 的「Checkout 全攻略」長達 80 頁，新人看三天仍不會串接 | 依 Diátaxis 拆成 tutorial、how-to、reference、explanation，用 landing page 串起來 |
| Design doc 審查流於形式 | 只挑錯字與格式，沒人挑戰核心假設 | Reviewer 留了 30 則用詞建議，沒有一則問「舊 app 怎麼辦」 | 在模板中列出必答的風險問題；邀請受影響團隊而不只是同組同事 |
| 每個變更都要求 design doc | 小變更被流程拖慢，大家開始敷衍 | 修一個顯示錯誤也要寫三頁設計 | 明確的觸發條件；小變更用 PR 描述即可 |
| 只依賴 schema 自動檢查 | 語意改變沒有被偵測 | `total` 從含運改成不含運，型別不變，CI 全綠 | Schema description 寫清語意；語意變更必須走 design review；consumer contract test |
| 把 design doc 當成現況文件維護 | 文件永遠過時，讀者被誤導 | 新人照一年多前的設計圖找服務，那個服務早已拆分 | 標示狀態與日期；現況寫進 conceptual／reference，決策抽成 ADR |
| 定期複查變成蓋章 | Owner 只改日期不看內容 | 一年內 40 份文件全部在到期日當天「複查通過」 | 以變更觸發為主；抽查複查品質；讓讀者回饋直接開 issue 給 owner |
| 過度寬容的 API 解析 | 錯誤輸入變成無法收回的依賴 | Server 接受 `"total": "1,234"`，三年後想收緊驗證，發現十個 client 都這樣送 | 對未知欄位寬容，對已知欄位格式嚴格；從第一天就驗證 |
| 文件全部交給 AI 產生 | 大量流暢但沒人驗證的文字淹沒正確文件 | Agent 為每個模組產生 README，其中三分之一的描述與程式不符 | AI 產出要標示來源並由 owner 驗證；只產生能被程式碼檢查的部分 |

## 17.13 AI 時代：什麼變了？

### 文件的讀者多了 AI agent

過去文件的讀者只有人；現在 Harbor 的 AI coding agent 每天會讀上百次 repo 裡的文件，作為它修改程式碼的 context。這帶來兩個直接的變化。

第一，**過時文件的傷害被放大**。一個人讀到過時文件，可能覺得不對勁而去問同事；agent 通常會照單全收。Harbor 曾經發生過：agent 依照一份已過時的串接說明，在新功能裡呼叫了準備淘汰的 `GET /orders/{id}`，而 review 的人以為 agent「讀過文件」就沒有細看。因此文件的 `status: deprecated` 與 `superseded_by` 這類 metadata，對 agent 比對人更重要：它們是機器能判斷的訊號。

第二，**為 agent 寫的指引成為新的文件類型**。很多 coding agent 支援在 repo 根目錄放一份給 agent 讀的說明檔（例如 `AGENTS.md`，不同工具的檔名慣例不同），內容是如何 build、如何測試、哪些目錄不能動、程式風格與常見陷阱。它本質上是給 agent 的 tutorial 加 how-to，應該和其他文件一樣有 owner、走 review、保持簡短，並且只寫可以被驗證的指令（「執行 `make test`」比「請確保品質」有用得多）。

### AI 很會寫，但不知道「為什麼」

AI 擅長從程式碼產生描述「做了什麼」的文字：函式摘要、參數說明、範例呼叫。但本章反覆強調，文件最有價值的部分是程式碼推導不出來的東西：`max_attempts = 3` 背後的合約條款、`total` 是對外承諾、某個方案被否決的原因。AI 沒有這些資訊，卻可能用流暢的文字「補」出一個看似合理的理由。這種**看起來權威、實際上是猜測**的內容，比空白更危險。

因此 Harbor 的規則是：AI 草擬的文件必須區分「可以從程式碼驗證的事實」與「推測」，推測的部分要標記出來，交給 owner 確認或刪除。

### 可執行的做法

1. **讓 AI 找漂移，而不是只讓它寫**：請 agent 比較 OpenAPI schema、程式碼與文件，列出不一致的地方（例如文件說 `amount`，schema 說 `total`），每一項附上檔案與行號，讓人逐一確認。
2. **Design doc 的「紅隊」reviewer**：把 design doc 交給 AI，請它分別扮演 SRE、資安、app 小組與新進工程師提出問題。這能幫作者在送給真人 review 前補上明顯的缺漏，但不能取代受影響團隊的真人 review，因為 AI 不知道 payments 團隊實際讀了哪些欄位。
3. **AI 產生的 reference 要被測試**：AI 寫的範例程式碼要能被 doctest 或 CI 執行；AI 寫的 API 範例要在 staging 實際呼叫一次。無法驗證的範例不合併。
4. **把相容性檢查放在 agent 的必經之路**：agent 修改 API 時，CI 的 schema 相容性檢查與 contract test 照樣執行；agent 不能自行加上「這是有意的破壞性變更」的例外標記，這個標記必須由人類 owner 加。
5. **注意資料外洩**：把內部 design doc 或客戶資料貼給未經公司核准的 AI 服務，可能違反資安與隱私規範。使用公司核准的工具與權限範圍。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 從 docstring、schema 與程式碼草擬 reference 與範例 | 範例必須能被自動執行驗證；語意（單位、承諾、理由）由 owner 確認 |
| 比較程式碼、schema 與文件，列出漂移候選並附位置 | 每一項由 owner 判斷是文件錯還是程式錯，AI 不能直接「修正」任一邊 |
| 為 design doc 模擬不同角色提出問題、檢查是否缺少 rollback 與 non-goals | 受影響團隊的真人 review 與 approver 簽核不能被省略 |
| 依 diff 草擬 changelog、遷移說明與 release note | 破壞性變更的判定與例外核准由人類 owner 負責並留下紀錄 |
| 把長篇 design doc 摘要成不同讀者的導讀 | 摘要不是正本；高風險決策要能追溯回原始文件與證據 |
| 維護給 agent 的指引檔（如 build、測試指令） | 指引檔走 code review；不得包含秘密或繞過檢查的指示 |

> [!ai] AI 提醒
> 當 AI 讓「產生文字」的成本趨近於零，稀缺的資源就變成「可信的來源」與「刪除的勇氣」。一個 repo 若有 500 份 AI 產生、沒人驗證的 README，搜尋與 agent 的 context 都會被雜訊淹沒。寧可少而正確，也不要多而可疑。

## 17.14 專家怎麼想

- **「這份文件的讀者是誰？讀完要能做什麼？」** 資深工程師拿到一份文件，第一件事是看它的目標讀者與目的。答不出來的文件，通常內容再多也幫不上忙；答得出來的文件，篇幅短也很有價值。
- **能產生的就產生，能測試的就測試。** 專家把精力花在只有人能寫的部分：為什麼、承諾、取捨。欄位清單、範例、指令說明盡量從單一來源產生並在 CI 驗證，因為人工同步一定會漂移。
- **Design doc 先看 non-goals 與 alternatives。** 這兩段最能看出作者是否真的想清楚。沒有 non-goals 的設計，範圍會在 review 中失控；沒有 alternatives 的設計，通常只考慮過一種做法。
- **API 一旦公開就很難收回，所以第一版要保守。** 少暴露一個欄位、少接受一種格式，未來就少一份 Hyrum's Law 的負擔。新增永遠比刪除容易，第 18 章會說明刪除有多難。
- **把語意寫在型別旁邊。** `total: integer` 不夠，`total: integer，新台幣元，含稅不含運` 才是 contract。專家 review schema 時，會逐一問每個數字欄位的單位與每個時間欄位的時區。
- **文件也需要淘汰。** 定期刪除或封存過時的文件，和寫新文件一樣重要。搜尋結果裡的每一份過時頁面，都在消耗讀者的信任。

## 17.15 動手練習

1. 為你熟悉的一個服務（或 Harbor 的搜尋服務）設計一個 landing page，只列 6–10 個連結，每個連結附一句說明，並用 Diátaxis 標出每份文件屬於哪一類。
2. 找一段你寫過的程式碼，挑出三個「魔術數字」或特殊判斷，為每一個寫一段說明「為什麼」的註解。如果你自己也不知道為什麼，記錄你要去問誰。
3. 擴充 17.11 節的相容性檢查程式：加入「請求欄位從選填改為必填」與「回應欄位從必填改為可為 null」兩種規則，並思考它們分別屬於 BREAKING 還是 WARN、理由是什麼。
4. 為 Harbor「訂單支援分期付款」寫一份兩頁的 mini design doc，至少包含 context、goals、non-goals、兩個 alternatives、rollout 與 rollback，以及三個 open questions。
5. 擴充文件新鮮度 linter：讀取一個真實 repo 中所有 Markdown 檔案的 front matter，用 `git log` 取得 `covers` 路徑的最後修改日期，輸出需要複查的清單。
6. 請 AI 為一個你熟悉的模組產生 README，然後逐句標記：哪些可以從程式碼驗證、哪些是推測、哪些是錯的。計算三類的比例，並寫下你從中學到的 review 重點。

## 本章重點整理

- 程式碼、測試與 schema 是可執行的真相；文件負責程式碼說不出的意圖、承諾、導航與取捨。
- 寫文件前先界定讀者：經驗、領域知識與目的，並分辨 seeker 與 stumbler、customer 與 provider。
- 每份文件只服務一群讀者、一個目的；用 who、what、when、where、why 開頭能逼作者做出取捨。
- SWE 書把文件分為 reference、design doc、tutorial、conceptual 與 landing page；Diátaxis 用「動手或理解」「學習或工作」兩軸分出 tutorial、how-to、reference、explanation。
- 程式碼註解要寫「為什麼」與「承諾」，不要重述程式；能從單一來源產生的 reference 就不要手寫。
- Docs as code 讓文件與程式碼在同一個 PR 裡被修改、review 與測試，並由 CODEOWNERS 確保 owner 看得到。
- Design doc 的價值在於讓昂貴的假設在動工前被挑戰；non-goals、alternatives、rollout 與 rollback 是最關鍵的段落。
- Design doc 描述決策當下的意圖，不需永遠同步；現況寫進 reference 與 conceptual 文件，重要決策抽成 ADR。
- API contract 包含結構、語意、錯誤、冪等性、非功能需求與演進政策；寫在 contract 裡的才是承諾。
- Schema first（OpenAPI、protobuf）讓文件、SDK、驗證與 mock 從同一個正本產生，彼此不會矛盾。
- 相容性分向後與向前兩個方向；請求與回應的相容規則方向相反，語意改變是最危險的破壞性變更。
- protobuf 刪除欄位要用 `reserved` 鎖住編號，永遠不要重用欄位編號。
- 優先以新增的方式演進 API，版本化是最後手段，因為每個舊版本都需要日後的淘汰。
- 過時文件比沒有文件更危險；owner、定期複查、變更觸發與使用回饋共同維持文件新鮮度。
- AI 讓產生文字變便宜，但無法知道程式碼背後的理由；AI 草擬的文件要區分事實與推測，並由 owner 驗證。

## 延伸問答

> [!question]- Q1. 「好的程式碼不需要文件」這句話哪裡對、哪裡錯？
> 對的部分是：清楚的命名、小而專注的函式與明確的型別，確實能讓讀者看懂程式「做了什麼」，因此不需要逐行重述程式的註解。很多過時的註解正是來自這種重述：程式改了，翻譯沒改。
>
> 錯的部分是：程式碼無法表達「為什麼」、「承諾什麼」與「被否決的替代方案」。`max_attempts = 3` 不會告訴你這是金流商合約的限制，`total` 欄位不會告訴你它是對外承諾還是內部細節。另外，使用你系統的人（customer）不應該需要讀你的實作才能正確使用它。所以比較精確的說法是：好的程式碼減少了「描述做什麼」的文件需求，但「為什麼」與「contract」的文件仍然必要。

> [!question]- Q2. Tutorial 與 how-to guide 有什麼差別？為什麼不要把它們寫在同一份文件裡？
> Tutorial 的讀者是正在學習的新手，目標是讓讀者從零開始完成一件保證會成功的事，建立信心與基本概念；它可以刻意簡化，不必列出所有選項。How-to guide 的讀者已經會基本操作，正在工作中解決特定問題，例如「如何對一筆訂單補發通知」；它假設讀者知道背景，直接給步驟與變化情況。
>
> 混在一起時，兩種讀者都不滿意：新手在 tutorial 中遇到大量「如果你的情況是 X，請改用 Y」的分支而迷路；老手要解決問題時，得跳過一大段入門說明。拆開後各自簡短、目標明確，也比較容易維護，因為環境改變時你知道該更新哪一份。

> [!question]- Q3. 什麼樣的變更需要寫 design doc？如果你是 tech lead，會怎麼避免它變成形式主義？
> 需要 design doc 的通常是：影響其他團隊或對外 API 的變更、引入新的儲存或關鍵依賴、涉及安全隱私或金流、工作量超過一兩週、以及難以回復的決策。共同點是「改錯的代價很高，而且在動工前討論的成本遠低於動工後」。
>
> 避免形式主義的做法包括：把觸發條件寫清楚，小變更明確豁免；提供可以縮放的模板，中等變更用一兩頁的 mini design doc；在模板中列出必答的風險問題（依賴失效、rollback、受影響團隊），讓 review 聚焦在實質內容；並追蹤 review 的週期，如果一份 design doc 卡了三週沒人看，問題在流程而不在作者。最重要的是 tech lead 自己 review 時示範該問什麼，而不是挑錯字。

> [!question]- Q4. 下列哪些 API 變更是破壞性的？(a) 回應新增欄位；(b) 請求新增必填欄位；(c) 把錯誤碼從 400 改成 422；(d) `total` 從含運改為不含運，型別不變。
> (a) 通常不是破壞性的，前提是 contract 要求 client 忽略未知欄位；如果某個 client 用嚴格模式解析、遇到未知欄位就失敗，它仍會壞，所以這個前提要寫進文件。(b) 是破壞性的：舊 client 不會送這個欄位，請求會被拒絕。若要加入新的必要資訊，可以先以選填欄位上線並提供預設行為，等 client 都更新後再考慮收緊。
>
> (c) 是破壞性的：client 可能依錯誤碼決定是否重試或顯示什麼訊息，改碼會改變它們的行為。(d) 是最危險的一種：格式完全相同，所有自動化的 schema 檢查都會通過，但每個用 `total` 計算的 consumer 都會算錯，而且可能要到對帳時才發現。語意變更應該用新增欄位（例如 `subtotal`）的方式處理，並走 design review。

> [!question]- Q5. 為什麼 protobuf 刪除欄位時要使用 `reserved`？如果沒有這麼做，會發生什麼事？
> protobuf 的二進位格式只寫欄位編號，不寫欄位名稱。假設 `coupon_code` 原本是欄位 4，被刪除後，有人新增 `discount_amount` 並也用了編號 4。還在執行舊版本的服務收到新訊息時，會把 `discount_amount` 的位元組當成 `coupon_code` 解讀；如果兩者型別相容，就不會出錯，只會產生錯誤的資料。
>
> 這種錯誤沒有例外、沒有錯誤碼，只會在資料裡留下無聲的污染，非常難追查。`reserved 4;` 與 `reserved "coupon_code";` 讓編譯器拒絕任何重用這個編號或名稱的嘗試，把一個需要靠人記住的規則變成機器強制的規則。這也是本章反覆出現的模式：重要的約束要寫進工具，而不是寫進口頭傳統。

> [!question]- Q6. 你接手一個服務，發現它的 wiki 有 60 頁文件，最後修改日期從一年前到四年前不等。你會怎麼處理？
> 先不要急著逐頁更新，那會耗掉幾週卻不知道哪些頁面有人在讀。第一步是找出讀者真正需要的東西：看頁面瀏覽紀錄、搜尋紀錄、團隊頻道裡常被問的問題，並請一兩位新人說出他們最需要的資訊。通常會發現 60 頁裡只有十幾頁真的被使用。
>
> 接著分三類處理：被使用而且內容重要的頁面，確認正確性後搬進 repo 的 `docs/`，加上 owner 與複查週期；仍有參考價值但不再維護的頁面，加上「已過時」橫幅並連到新的正本；沒有人使用、內容也過時的頁面直接封存。最後建立一個 landing page 把留下來的文件串起來，並加上新鮮度檢查，避免一年後再次回到同樣的狀態。

> [!question]- Q7. Harbor 的 AI coding agent 依照一份過時的文件，在新功能中呼叫了準備淘汰的 API，而 review 的人沒有發現。這次事件應該改善哪些地方？
> 這不是單一環節的問題，至少有三個層次可以改善。第一是文件本身：那份文件應該被標上 `status: deprecated` 與 `superseded_by`，新鮮度檢查也應該在 API 被標為淘汰時點名所有提到它的文件。這類 metadata 對 agent 特別重要，因為 agent 會把文件當成可信的 context。
>
> 第二是工具：被淘汰的 API 應該有機器強制的防線，例如 lint 規則禁止新的呼叫、或 API gateway 拒絕新 client 使用（第 18 章會詳談防止新使用者加入的做法）。第三是 review 習慣：reviewer 不能因為「agent 讀過文件」就降低標準，review AI 產生的變更時要特別檢查它呼叫了哪些 API、依據的是哪份文件。事後也應該把這個案例加入 agent 的指引檔與 review checklist。

> [!question]- Q8. 面試題：你要設計一個會被十幾個內部團隊與外部合作夥伴使用的 API。在寫第一行程式之前，你會先做哪些事？
> 第一，先寫 design doc，釐清這個 API 要解決的問題、使用者是誰、明確的 non-goals，並請代表性的 consumer 團隊 review。這能在最便宜的時候發現需求誤解。第二，以 schema first 的方式寫出 OpenAPI 或 protobuf 定義，在 description 中寫清每個欄位的單位、格式與語意，定義錯誤格式、冪等性、分頁與速率限制。
>
> 第三，在 contract 中寫下演進政策：只做向後相容的新增、client 必須忽略未知欄位與處理未知 enum 值、破壞性變更的版本化與淘汰時程。第四，把 schema 相容性檢查放進 CI，並從 schema 產生文件、SDK 與 mock，讓 consumer 能在 server 完成前開始開發。回答時可以強調：第一版要保守，少暴露一個欄位就少一份未來的相容性負擔，因為根據 Hyrum's Law，任何暴露出去的行為都可能被依賴。

## 延伸閱讀

- [Software Engineering at Google — Documentation](https://abseil.io/resources/swe-book/html/ch10.html)：本章對應的原書章節，包含讀者類型、文件種類、文件 review 與文件淘汰的討論。
- [Software Engineering at Google — Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)：從組織角度談知識如何流動，與第 10 章互相補充。
- [Software Engineering at Google — Code Review](https://abseil.io/resources/swe-book/html/ch09.html)：理解 code review 與 design review 的分工。
