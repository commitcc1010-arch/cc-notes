---
chapter: 23
title: Unit Testing：保護 Behavior，不綁死 Implementation
part: 4
---

# 第 23 章　Unit Testing：保護 Behavior，不綁死 Implementation

> [!abstract] 本章地圖
> **核心問題**：為什麼有些 unit test 讓重構變安全，有些卻讓任何內部修改都要重寫一大片測試，而且真正的 bug 還是溜得過去？
>
> **你會學到**：
> - 用「四種變更」判斷一個測試是否 brittle（脆弱），並找出它脆弱的原因
> - 透過 public API 測試，選擇正確的測試邊界，而不是替每個 private method 寫測試
> - 用 Given-When-Then 結構與行為導向的命名，寫出「一個測試一個行為」的測試
> - 分辨測試程式碼裡什麼時候要 DAMP、什麼時候可以 DRY
> - 寫出不必打開測試原始碼就能看懂的失敗訊息
> - 用 property-based testing 保護不變量，用 mutation testing 檢查測試本身有沒有辨識力
>
> **前置知識**：第 22 章（test size 與 scope、testing pyramid）、第 5 章（Hyrum's Law）
>
> **對應原書**：SWE 第 12 章〈Unit Testing〉

## 23.1 故事：重構弄出三百個紅燈，真正的 bug 卻一直是綠燈

Harbor 已經成長到四十多人、分成五個團隊。checkout 團隊負責計價模組 `pricing`：會員九折、折價券、滿千免運，全部集中在這裡。為了下個月的週年慶，產品經理 Lisa 要加入「滿額贈點」「指定品牌加碼折扣」等五種新規則。checkout 團隊的初階工程師小芸判斷，原本一層層 `if` 疊起來的寫法已經撐不住，決定把它重構成「規則表」：每條規則是一個小函式，依序套用。

重構花了一天。小芸很小心，沒有改變任何計價結果。但按下測試的那一刻，螢幕上出現 312 個失敗。小芸一個個打開來看，發現它們失敗的理由都和計價結果無關：有的測試直接呼叫 `_apply_member_discount()` 這個 private method，而它在重構後已經不存在；有的測試用 mock 驗證「先呼叫會員折扣，再呼叫折價券」的順序；還有一批測試把整個計價物件的內部欄位逐一比對。小芸花了兩天把測試「修好」，其實就是照著新的實作重寫一遍。

更讓人不安的是 tech lead 美華在 review 時發現的事。三週前有一個小改動，把免運門檻的判斷不小心改成用「折價前」的金額：一張 1,050 元的訂單用了 100 元折價券，實付 950 元，卻被判成免運。這個 bug 在 production 跑了兩週，直到財務對帳時發現運費收入對不上才被抓到。那段期間，計價模組的 312 個測試全部是綠燈。

美華在團隊週會上把這兩件事放在一起講：「我們的測試在不該失敗的時候失敗，在該失敗的時候又沒失敗。三百多個測試，保護的是我們怎麼寫程式，而不是程式該做什麼。」工程經理 Kevin 補了一句：「如果每次重構都要花兩天修測試，大家就會停止重構。」

這一章要回答的就是：什麼樣的 unit test 能在重構時保持安靜、在 bug 出現時大聲報警？答案的核心只有一句話：**測試要保護 behavior（行為），不要綁死 implementation（實作）**。接下來我們把這句話拆成可以照著做的規則。

## 23.2 Unit test 的工作：讓人敢改程式

### 什麼是 unit test

**Unit test**（單元測試）是驗證一小段程式行為的測試，通常針對一個函式、一個類別或一個小模組。第 22 章介紹過兩個維度：**size** 指測試耗用的資源（small test 只在單一 process 內、不碰網路與磁碟），**scope** 指測試驗證的程式範圍。Unit test 通常是 small size、narrow scope：跑起來以毫秒計，失敗時範圍小到能立刻定位問題。

Unit test 之所以是測試組合的主體，是因為它便宜：寫起來快、跑起來快、結果穩定，開發者可以每改幾行就跑一次。但「便宜」只說明了寫和跑的成本。真正決定一套 unit test 值不值得的，是**維護成本**：在程式長期演化的過程中，這些測試需要被修改多少次，以及每次修改是不是在做有意義的事。Harbor 的 312 個測試寫起來不貴，維護起來卻非常貴。

### 測試的四種結果

一個測試每次執行，結果只有四種可能：

```text
                       程式真的有 bug          程式其實沒問題
                 ┌───────────────────────┬───────────────────────┐
  測試失敗（紅） │ ✔ 正確報警            │ ✘ 誤報（false alarm）  │
                 │  （true positive）    │   → brittle test       │
                 ├───────────────────────┼───────────────────────┤
  測試通過（綠） │ ✘ 漏報（miss）         │ ✔ 正確安靜            │
                 │   → 沒有辨識力的測試   │  （true negative）     │
                 └───────────────────────┴───────────────────────┘
```

這張圖要從兩個「✘」格子讀。右上角是誤報：程式沒壞，測試卻紅了，這就是 **brittle test**（脆弱測試）。原書的定義是：production 程式碼發生了沒有引入任何真正 bug 的變更，測試卻因此失敗。左下角是漏報：程式壞了，測試卻是綠的，代表測試沒有**辨識力**（discriminating power）。Harbor 的故事把兩種錯誤都踩了一遍：重構時的 312 個紅燈全在右上角，免運門檻 bug 則落在左下角。

兩種錯誤的傷害方式不同。漏報的傷害很直接：bug 進了 production。誤報的傷害比較慢，卻同樣致命：每次誤報都在教團隊「紅燈不一定代表有問題」。誤報多了，工程師會習慣性地「照著新實作更新測試」，而這個習慣正好會讓真正的紅燈也被順手改綠。所以誤報不只浪費時間，還會把測試從安全網變成噪音。

### 判斷 brittle 的工具：四種變更

原書提供了一個很實用的判斷方法：把對 production 程式碼的變更分成四類，看測試在每一類變更下「應不應該」被修改。

| 變更類型 | 例子（Harbor 計價模組） | 既有測試應該要改嗎？ |
|---|---|---|
| **Pure refactoring**（純重構） | 把一串 `if` 改成規則表，結果完全相同 | 不應該。若要改，代表測試綁住了實作 |
| **New feature**（新功能） | 加入「滿額贈點」規則 | 不應該改既有測試，只要新增測試 |
| **Bug fix**（修 bug） | 修正免運門檻用錯金額 | 不應該改既有測試，只要新增一個重現 bug 的測試 |
| **Behavior change**（行為改變） | 公司決定免運門檻從 1,000 改成 1,200 | 應該，而且這正是測試存在的意義 |

這張表給出一個可以量測的目標：**努力讓測試只在行為改變時才需要修改**。原書把這叫做 strive for unchanging tests（追求不需要改的測試）。小芸的重構屬於第一類，卻需要改 312 個測試，這就是一個明確的警訊。下次你在 code review 中看到一個「純重構」的 PR 同時改了大量測試，應該先問：這些測試改的是期望值，還是只是跟著實作調整呼叫方式？

## 23.3 透過 public API 測試

### 為什麼不要直接測 private method

讓測試不需要隨重構修改，最有效的方法是**只透過 public API 呼叫被測程式**，也就是用和真正的呼叫者一樣的方式使用它。**Public API** 在這裡的意思是「這個單元對外承諾的介面」：函式簽名、它接受的輸入、回傳的輸出、會丟出的錯誤，以及它對外可觀察的副作用。

小芸遇到的第一批失敗測試直接呼叫 `_apply_member_discount()`。在 Python 中，底線開頭代表「內部使用」；在 Java 中可能是 `private` 或 package-private 的方法。這種方法存在的理由是「目前這樣實作比較方便」，它不是對任何人的承諾。一旦測試直接呼叫它，測試就替這個方法建立了一份它本來沒有的合約：方法名稱、參數順序、回傳格式都被固定下來。重構時拆掉這個方法，測試就紅了，但沒有任何使用者受到影響。

透過 public API 測試還有第二個好處：**測試同時是使用範例**。新同事讀 `test_free_shipping_threshold_uses_amount_after_coupon`，看到的是 `quote(1050, False, 100)` 得到 `(1010, 60)`，立刻知道這個函式怎麼用、規則是什麼。如果測試讀起來是一堆對內部 helper 的呼叫，它就只對寫它的人有意義。

### 「單元」的邊界怎麼畫

「透過 public API 測試」的前提是先決定什麼是一個單元。這不是一個語法問題（是不是 `public` 關鍵字），而是一個設計問題。原書給的判斷原則大致如下：

- 一個 helper 類別如果只被另一個類別使用，是那個類別的實作細節，它不是獨立的單元，應該透過使用它的類別來測。
- 一個模組如果是設計給多個呼叫者使用的（例如共用的金額格式化工具），它就是一個獨立的單元，有自己的 public API，值得直接測。
- 一個公開給外部使用者的 API（例如其他團隊呼叫的 library 或服務介面），一定要從使用者的角度測。

```text
         pricing 模組（單元邊界）
   ┌──────────────────────────────────────┐
   │  quote(subtotal, is_member, coupon)  │ ◀── 測試從這裡進去
   │        │                             │
   │        ├─▶ _member_rule()            │ ◀── 實作細節：不直接測
   │        ├─▶ _coupon_rule()            │
   │        └─▶ _shipping_fee()           │
   └──────────────┬───────────────────────┘
                  │ 使用
                  ▼
   money.format_twd()  ◀── 被多個模組共用：獨立單元，有自己的測試
```

圖中外框是 `pricing` 的單元邊界。測試只從 `quote` 進去，透過輸入與輸出驗證會員折扣、折價券與運費。框內三個底線開頭的函式隨時可以被合併、拆開或改名，不會影響任何測試。框外的 `money.format_twd()` 被訂單、發票、通知等模組共用，它的行為本身就是一份承諾，因此有自己的單元測試。

> [!warning] 常見誤解
> 「透過 public API 測試，就是只能做黑箱測試，不能測細節。」不對。如果某段複雜演算法（例如運費的分區計算）值得單獨驗證，正確的做法是把它抽成一個有清楚介面的模組，讓它成為一個正式的單元，再透過它的 public API 測。你改變的是設計，而不是讓測試偷看 private 細節。反過來，也不要為了測試方便就把內部方法改成 public，那等於向全世界承諾了一個你不想維護的介面。

### 測 state，不測 interaction

小芸的第二批失敗測試用 mock 驗證呼叫順序。這是另一種綁死實作的方式：測試不看「結果對不對」，而看「程式是不是照某個步驟做」。原書把兩種驗證方式分開：**state testing**（狀態測試）檢查呼叫之後系統的狀態或回傳值；**interaction testing**（互動測試）檢查被測程式是否以特定方式呼叫了它的依賴。大多數情況下應該偏好 state testing，因為使用者只在乎結果，不在乎你按什麼順序算出來。互動測試何時合理、mock 該怎麼用，是第 24 章（24.8 節）的主題；在本章，只要記住「驗證結果，而不是驗證步驟」。

## 23.4 一個測試，一個行為

### 測行為，不是測方法

很多人寫測試的直覺是「一個方法配一個測試」：`quote()` 有一個 `test_quote()`，裡面塞滿各種情況。原書建議換個角度：**test behaviors, not methods**。一個 **behavior**（行為）是「在某個前提下，做某件事，會得到某個結果」的承諾。

方法和行為之間不是一對一的關係：

```text
  方法                         行為（每一條是一個測試）
  ─────────────               ──────────────────────────────────────
  quote()          ───┬──▶   會員享九折
                      ├──▶   折價券不會讓金額變成負數
                      ├──▶   折價後滿 1,000 元免運（含剛好 1,000）
                      └──▶   負數折價券會被拒絕
  add_item()  ─┐
               ├───────▶    購物車移除最後一件商品後，總額歸零
  remove_item()┘
```

左邊一個 `quote()` 對應右邊四個行為，所以應該有四個測試；左下兩個方法（`add_item`、`remove_item`）共同構成一個行為，就用一個測試同時呼叫它們。把行為分開，有三個好處：每個測試短而好讀；一個測試失敗時，名稱本身就說明了哪個承諾被打破；新增行為時只要新增測試，不必擠進一個越來越長的 `test_quote()`。

### Given-When-Then

一個行為的測試通常有三段，業界最常用的說法是 **Given-When-Then**：

- **Given**（前提）：準備好系統的初始狀態與輸入。「一位會員，購物車小計 500 元，沒有折價券。」
- **When**（動作）：執行被測的那一個行為。「向計價模組報價。」
- **Then**（結果）：驗證可觀察的結果。「應付 510 元，其中運費 60 元。」

同樣的結構也常被稱為 **Arrange-Act-Assert**（AAA）。兩者意思相同，重點是讓讀者一眼看出三段的邊界。一個實際的寫法如下：

```python
# not-runnable：示意測試結構
def test_free_shipping_threshold_uses_amount_after_coupon(self):
    # Given：非會員，小計 1,050 元，使用 100 元折價券
    subtotal, coupon = 1050, 100

    # When
    total, shipping = quote(subtotal, is_member=False, coupon=coupon)

    # Then：折價後 950 元未達免運門檻，應收運費
    self.assertEqual(shipping, 60)
    self.assertEqual(total, 1010)
```

如果一個測試需要多個 When-Then（例如「加入商品後總額為 X，再套用折價券後總額為 Y」），可以用 Given-When-Then-When-Then 的形式，但前提是它們確實描述同一個行為的連續步驟。如果是兩個不相關的行為，就拆成兩個測試。

### 用行為命名

測試名稱是失敗時第一個被看到的資訊，在 CI 報告裡它甚至是唯一被看到的資訊。`test_quote_2`、`test_shipping` 這種名字在失敗時什麼都沒說。好的測試名稱應該描述行為：前提與預期結果。

| 不好的名稱 | 好的名稱 |
|---|---|
| `test_quote` | `test_member_pays_ninety_percent_plus_shipping` |
| `test_coupon` | `test_coupon_larger_than_subtotal_does_not_go_negative` |
| `test_shipping_edge` | `test_free_shipping_starts_exactly_at_1000` |
| `test_error` | `test_negative_coupon_is_rejected` |

一個實用的檢查方法：把所有測試名稱列出來，它應該讀起來像這個單元的規格書。如果你發現名稱裡出現「and」（例如 `test_discount_and_shipping_and_points`），通常代表這個測試驗證了不只一個行為，可以考慮拆開。

### 不要在測試裡寫邏輯

測試裡應該盡量避免迴圈、條件判斷與計算。原書的例子很典型：一個測試用字串拼接算出「預期的 URL」，結果拼接本身多出一個斜線，錯的是測試的期望值，但讀者很難一眼看出來；如果 production 程式碼犯了同樣的錯，這個測試也抓不到。把期望值直接寫成完整的字串，錯誤就一目了然。

在 Harbor 的計價模組裡，最常見的版本是這樣：

```python
# not-runnable：反例
def test_member_discount(self):
    subtotal = 500
    expected = subtotal * 90 // 100 + (0 if subtotal * 90 // 100 >= 1000 else 60)
    self.assertEqual(quote(subtotal, True, 0)[0], expected)
```

這個測試把計價公式在測試裡重寫一遍。如果 production 程式碼的公式錯了，寫測試的人很可能用同樣的思路寫錯；更糟的是，讀者無法一眼看出「500 元的會員到底該付多少」。改成直接寫出 `510`，測試就變得**顯而易見地正確**（obviously correct；原書的說法是讀一眼就能確認它是對的）：任何人都能用心算驗證 500 × 0.9 + 60 = 510。測試的期望值應該來自需求或手算，而不是來自另一份實作。

### 完整而簡潔

「一個測試一個行為」不代表測試越短越好。原書的說法是測試要 **complete and concise**（完整且簡潔）：完整，指讀者需要的資訊都在測試本體裡，不必跳到別的檔案才看得懂；簡潔，指不相關的雜訊都被藏起來。例如建立一個訂單需要十個欄位，但這個測試只在乎「會員」與「小計」，那麼另外八個欄位應該由 helper 用合理預設值填好，測試裡只寫出這兩個。下一節會回到「什麼該藏、什麼不該藏」這個問題。

## 23.5 DAMP 與 DRY：測試程式碼有不同的規則

### Production 程式碼為什麼要 DRY

寫 production 程式碼時，我們從小被教 **DRY**（Don't Repeat Yourself，不要重複自己）：同樣的邏輯只寫一次，改的時候只改一個地方。這個原則在 production 程式碼裡很合理，因為重複的邏輯會在修改時漏改，造成不一致。

### 測試為什麼要 DAMP

測試程式碼的目的不同。Production 程式碼的正確性由測試保護，但測試本身沒有「測試的測試」，它的正確性只能靠**人讀了以後覺得顯然正確**。因此原書建議測試追求 **DAMP**（Descriptive And Meaningful Phrases，描述性且有意義的語句）：寧可有一點重複，也要讓每個測試單獨讀起來就清楚。

看一個過度 DRY 的例子：

```python
# not-runnable：過度 DRY 的測試
class QuoteTest(unittest.TestCase):
    def setUp(self):
        self.cart = make_cart(CART_FIXTURES["standard"])   # 定義在另一個檔案
        self.user = USERS[2]                                # 第 3 位使用者是誰？

    def test_total(self):
        self.assertEqual(quote_cart(self.cart, self.user), EXPECTED["standard"][2])
```

這個測試讀不出任何東西：購物車裡有什麼？第三位使用者是不是會員？預期值為什麼是那個數字？要回答這些問題，讀者必須打開三個地方。更麻煩的是，`CART_FIXTURES["standard"]` 被五十個測試共用，有人為了新測試改了它，另外四十九個測試的意義就悄悄改變了。

DAMP 的版本會把「對這個測試重要的資訊」直接寫在測試裡：

```python
# not-runnable：DAMP 的測試
def test_member_pays_ninety_percent_plus_shipping(self):
    cart = make_cart(subtotal=500)          # helper 只負責填入不重要的欄位
    member = make_user(is_member=True)
    self.assertEqual(quote_cart(cart, member), 510)
```

這裡仍然使用 helper（`make_cart`、`make_user`），但 helper 的參數就是這個測試在乎的值。讀者不需要離開這個函式，就知道「小計 500 的會員該付 510」。

### 哪些共用是好的

DAMP 不是禁止共用。原書把測試中的共用分成幾種，判斷方式各不相同：

| 共用的東西 | 建議 | 理由 |
|---|---|---|
| **共用的值**（例如全域的 `USERS[2]`） | 盡量避免 | 讀者看不出值的意義，修改時會牽動許多測試 |
| **共用的 setup**（`setUp` 方法） | 謹慎使用，只放與每個測試都無關的準備工作 | 若測試依賴 setup 裡的特定值，應在測試中明確寫出或覆寫 |
| **Helper 方法**（建立物件） | 鼓勵，搭配具名參數與合理預設值 | 隱藏雜訊，凸顯重要的值 |
| **驗證 helper**（例如 `assert_valid_invoice`） | 可以，但要只驗證一個概念 | 一個「檢查所有東西」的 helper 會讓失敗原因變模糊 |
| **測試基礎設施**（fake、測試框架擴充） | 可以 DRY，但它本身要有測試 | 它被許多團隊依賴，地位接近 production 程式碼 |

最後一列值得多說一句。像 Harbor 的 `FakePaymentGateway` 這種被很多團隊使用的測試工具，已經不是「某個測試的一部分」，而是一個被依賴的產品，它應該有 owner、有自己的測試、有文件。第 24 章會詳細討論 fake 的維護。

> [!tip] 一個快速檢查
> 讀一個測試時，如果你需要捲動到檔案別處、或打開另一個檔案，才能回答「這個測試的期望值為什麼是這個數字」，那它就不夠 DAMP。

## 23.6 清晰的失敗訊息

### 失敗訊息是寫給未來的人

測試寫出來是為了在某一天失敗。那一天看到失敗的人，很可能不是寫測試的人，而是半年後修改計價模組的某位同事，或者是在 CI 裡看到紅燈的 on-call 工程師。他們手上只有測試名稱和失敗訊息。原書的標準是：**好的失敗訊息讓人不必打開測試原始碼，就能理解發生了什麼**。

比較兩種失敗訊息：

```text
✘ 不好的訊息
  AssertionError: False is not true

✔ 好的訊息
  test_free_shipping_threshold_uses_amount_after_coupon
  AssertionError: Tuples differ: (950, 0) != (1010, 60)
  - (950, 0)
  + (1010, 60) : 折價後 950 元未達門檻，應收運費
```

第一種來自 `assertTrue(total == 1010)`：測試框架只知道你給它一個 `False`，不知道你在比較什麼。第二種來自 `assertEqual(..., msg=...)`：框架印出實際值與期望值的差異，加上你寫的一句人話，再配上行為導向的測試名稱，讀者立刻知道「免運門檻的判斷錯了，而且錯在用了折價前的金額」。

### 實務上怎麼做

- **用最具體的 assertion**。`assertEqual(a, b)` 比 `assertTrue(a == b)` 好，`assertIn(x, items)` 比 `assertTrue(x in items)` 好，`assertRaises(ValueError)` 比自己 try/except 好。具體的 assertion 讓框架能印出有意義的差異。
- **比較 domain 值，而不是巨大的結構**。如果你只在乎總額與運費，就只比較這兩個值；不要把整個訂單物件序列化成一大段 JSON 再比較，否則失敗時讀者要在幾百行差異裡找重點。
- **在 msg 裡寫「為什麼」**。期望值本身說明了「是什麼」；msg 最有價值的是說明規則，例如「門檻含等於」「折價後才判斷免運」。
- **在迴圈或隨機測試中印出輸入**。Property-based 測試失敗時，最重要的資訊是「哪一組輸入讓它失敗」，所以要把輸入放進訊息（23.10 的程式就是這樣做）。

> [!warning] 常見誤解
> 「Snapshot test（快照測試）可以一次比對所有輸出，最省事。」快照測試把整份輸出存起來，下次比對是否相同。它對「確保沒有任何改變」很有用，例如序列化格式。但它的失敗訊息只會說「有東西變了」，讀者很難判斷改變是 bug 還是預期中的行為改變；久而久之，大家習慣直接按「更新快照」。若要使用，讓快照小而聚焦，並在 code review 中把快照差異當成正式的行為改變來審查。

## 23.7 Brittle test 從哪裡來

把前面的規則反過來看，就是 brittle test 的常見成因。下表整理 Harbor 計價模組 312 個失敗測試中出現的原因，以及其他團隊常見的變形：

| 成因 | 典型寫法 | 為什麼脆弱 | 改法 |
|---|---|---|---|
| 測 private method | 直接呼叫 `_apply_member_discount()` | 重構刪掉方法就失敗 | 透過 `quote()` 驗證結果 |
| 驗證呼叫順序 | mock 檢查「先會員折扣、再折價券」 | 改成規則表就失敗，結果卻相同 | 驗證最終金額（state testing） |
| 比對內部欄位 | `assertEqual(engine._steps, [...])` | 內部資料結構一改就失敗 | 只比對對外可觀察的值 |
| 過度精確的期望 | 比對完整錯誤訊息字串、dict 的列印順序 | 改一個標點或 Python 版本就失敗 | 比對錯誤類型與關鍵欄位；比較集合而非順序 |
| 依賴時間與隨機 | 用 `datetime.now()` 判斷優惠是否過期 | 跨日、跨時區、跑太慢就失敗 | 注入 clock 與 random seed（第 24 章） |
| 共享可變狀態 | 測試 A 修改全域設定，測試 B 依賴它 | 執行順序一變就失敗 | 每個測試自己建立狀態，結束時不留下痕跡 |
| 巨大的共用 fixture | 五十個測試共用 `CART_FIXTURES["standard"]` | 為一個測試改 fixture，其他測試意義改變 | 每個測試用 helper 建立自己需要的資料 |

其中「過度精確的期望」和第 5 章的 Hyrum's Law 是同一件事的兩面。Hyrum's Law 說，只要使用者夠多，你系統的所有可觀察行為都會被某人依賴。測試也是一種使用者：一個比對完整錯誤訊息的測試，就是依賴了錯誤訊息的每一個字。你在寫測試的時候，其實是在決定「哪些行為是承諾」。只斷言承諾，不要斷言碰巧成立的細節。

時間、隨機與共享狀態造成的問題，除了 brittle 之外還會造成 **flaky test**（不穩定測試）：同一份程式碼，有時過、有時不過。Flaky 的成因、量化與 quarantine（隔離）流程在第 26 章（26.4–26.6 節）展開，這裡只要記住：unit test 必須 **deterministic**（給定相同輸入一定得到相同結果）、**independent**（不依賴其他測試或執行順序）、**fast**（毫秒級，才能頻繁執行）。

## 23.8 Property-based testing：從例子到不變量

### 例子測試的盲點

到目前為止，我們寫的都是 **example-based test**（例子測試）：挑一組輸入、寫出預期輸出。例子測試好讀、好除錯，是 unit test 的主體。但它有一個天生的盲點：它只檢查你想得到的例子。Harbor 的免運門檻 bug 之所以溜過去，就是因為沒有人寫過「有折價券、而且折價後跨過門檻」的例子。

### Property 是什麼

**Property-based testing**（性質測試）換一個問法：不問「這組輸入該得到什麼」，而問「對所有合法輸入，什麼一定成立」。這些「一定成立」的規則叫做 **invariant**（不變量）或 property。Harbor 計價模組的幾個不變量：

- 運費只可能是 0 或 60。
- 應付金額永遠不小於運費（商品金額不會變成負數）。
- 應付金額不會超過小計加運費（折扣只會讓價格下降）。
- 同樣的購物車與折價券，會員付的錢不會比非會員多。

最後一條很有意思：九折可能讓會員的金額掉到 1,000 元以下而需要付運費，直覺上似乎有可能讓會員付更多。但仔細推導，會發生這種情況時小計至少 1,000 元，九折省下的至少 100 元，大於 60 元運費，所以這條性質成立。寫 property 的過程，常常逼你把規則想得比寫例子時更透徹。

### 怎麼運作

一個 property-based 測試框架做三件事：

```text
  ① 產生輸入          ② 執行並檢查 property        ③ 失敗時縮小（shrink）
  ┌───────────┐       ┌──────────────────────┐      ┌──────────────────────┐
  │ 隨機購物車 │ ───▶ │ quote(...) 的結果     │ ───▶ │ 從失敗的大例子出發，   │
  │ 隨機折價券 │       │ 是否滿足所有不變量？  │  ✘   │ 逐步簡化，找出最小的   │
  │ 是否會員   │       └──────────────────────┘      │ 反例：(1000, F, 1)     │
  └───────────┘               │ ✔                    └──────────────────────┘
        ▲                     │
        └──── 重複數百次 ──────┘
```

① 依照你描述的輸入範圍產生大量隨機輸入；② 對每組輸入檢查所有 property；③ 一旦找到反例，**shrinking**（縮小）會嘗試把它簡化成最容易理解的版本，例如把「小計 2,817、折價券 433」縮小成「小計 1,000、折價券 1」，讓你直接看出問題出在門檻。這個想法源自 Haskell 的 QuickCheck，Python 生態系最常用的是 Hypothesis。本章的動手寫只用標準函式庫，以固定 seed 的隨機產生器做前兩步；shrinking 則留給真正的框架。

### 實務上怎麼用

Property 適合有明確不變量的程式：計價與金額計算（總和守恆、不為負）、序列化（`decode(encode(x)) == x`，叫做 round-trip property）、排序（輸出有序且元素集合不變）、狀態機（任何操作序列之後，庫存不會變成負數）。它不適合「規則本身就是一張任意的表」的程式，例如「台北市運費 60、離島運費 150」，這種情況寫例子比較清楚。

兩種測試是互補的：例子測試說明規則、記錄已知的邊界與歷史 bug；property 測試在廣大的輸入空間中替你找你沒想到的例子。一個好習慣是：property 找到的每個反例，修好之後都轉成一個具名的例子測試，讓它成為規格的一部分。

> [!warning] 常見誤解
> 「隨機測試會讓結果不穩定。」如果每次執行都用不同的 seed，確實可能一次過、一次不過。解法是：在 CI 中使用固定或記錄下來的 seed，讓失敗可以重現；框架如 Hypothesis 也會把找到的反例存起來，下次優先重跑。隨機是用來探索輸入空間，不是用來製造不確定性。

## 23.9 Mutation testing：測試的測試

### Coverage 的盲點

要怎麼知道一套測試夠不夠好？最常見的指標是 **code coverage**（覆蓋率）：測試執行時，有多少比例的程式碼被跑到。Coverage 能告訴你「哪裡完全沒被測」，但不能告訴你「被跑到的地方有沒有被驗證」。23.10 的程式裡有一個只寫了 `assertGreater(total, 0)` 的測試：它會跑過 `quote()` 的大部分程式碼，coverage 很漂亮，但幾乎任何 bug 都抓不到。Coverage 的正確用途與誤用在第 26 章詳談。

### Mutation testing 怎麼運作

**Mutation testing**（突變測試）直接回答「測試能不能抓到 bug」：故意在程式碼裡製造小 bug，看測試會不會失敗。

```text
  原始程式碼                 mutant（突變版本）            執行測試
  ───────────               ────────────────────          ──────────────────
  after >= 1000      ──▶    after > 1000           ──▶   有測試失敗 → killed ✔
  subtotal * 90      ──▶    subtotal * 80          ──▶   有測試失敗 → killed ✔
  max(0, x - c)      ──▶    (x - c)                ──▶   全部通過   → survived ✘
                                                           ↑
                                         代表沒有測試在保護「金額不為負」
```

這張圖假設的是一套「有測會員折扣與免運門檻、卻沒有任何折價券大於小計的例子」的測試：前兩個 mutant 被抓到，第三個溜過去，而溜過去的那個正好指出缺了哪一條保護。

每個小改動叫做一個 **mutant**。常見的改法（mutation operator，突變運算子）有：把 `>=` 換成 `>`、把 `+` 換成 `-`、把常數換掉、把條件反轉、刪掉一行。如果有測試因此失敗，這個 mutant 就被 **killed**（殺死），代表測試保護了這段邏輯；如果所有測試都通過，它就 **survived**（存活），代表這個 bug 可以悄悄溜過去。**Mutation score**（突變分數）粗略地說就是被殺死的 mutant 比例；嚴格的算法會把下面說的 equivalent mutant 從分母扣掉，第 26 章（26.8 節）會從量測的角度詳談這個公式。

存活的 mutant 要逐一判斷，常見有三種情況：

1. **測試真的有缺口**：應該補一個測試。這是 mutation testing 最有價值的產出。
2. **Equivalent mutant**（等價突變）：改動後行為完全相同，例如整數運算中 `x * 90 // 100` 改成 `x * 9 // 10`。沒有任何測試能殺死它，也不需要殺死。
3. **不重要的行為**：例如只改了 log 訊息的 mutant。可以接受它存活。

### 實務上怎麼做

對寫 unit test 的人來說，mutation testing 最實用的用法是當成**自我檢查**：寫完一組測試後，手動或用工具改壞幾個關鍵的地方（門檻、折扣率、下限），看測試會不會叫。23.10 的程式就是這樣一個迷你版本。

把它放大到整個團隊時，主要的問題是成本：每個 mutant 都要跑一次測試，大型 codebase 可能有數十萬個。實務上的共識是只對這次變更的程式碼與高風險模組（例如 Harbor 的計價、退款、庫存扣減）產生 mutant，把存活的 mutant 當成 code review 中的建議而不是合併門檻，也不把分數當 KPI。這些做法、常見工具，以及 Google 把 mutation testing 整合進 code review 的經驗，在第 26 章（26.8 節）詳談。

## 23.10 動手寫：用 unittest 驗證「改得動、抓得到」

下面的程式把本章的主要觀念放在同一個實驗裡：一組行為導向的測試，先證明它在「純重構」時保持綠燈，再用一個迷你 mutation testing 證明它在出現 bug 時會變紅，並和只有 happy path 的測試比較。程式只用標準函式庫，可直接執行。

```python
import io
import random
import unittest

# 被測程式以字串保存，方便之後產生 mutant（突變版本）
PRICING_SRC = '''
def quote(subtotal, is_member, coupon):
    """回傳 (應付金額, 運費)。金額單位：新台幣元，整數。"""
    if subtotal < 0 or coupon < 0:
        raise ValueError("金額不可為負")
    discounted = subtotal * 90 // 100 if is_member else subtotal
    after_coupon = max(0, discounted - coupon)
    shipping = 0 if after_coupon >= 1000 else 60
    return after_coupon + shipping, shipping
'''

# 行為相同、結構不同的重構版本：改成規則表
REFACTORED_SRC = '''
RULES = [
    lambda amount, ctx: amount * 90 // 100 if ctx["member"] else amount,
    lambda amount, ctx: max(0, amount - ctx["coupon"]),
]

def quote(subtotal, is_member, coupon):
    if min(subtotal, coupon) < 0:
        raise ValueError("金額不可為負")
    amount = subtotal
    for rule in RULES:
        amount = rule(amount, {"member": is_member, "coupon": coupon})
    shipping = 60 if amount < 1000 else 0
    return amount + shipping, shipping
'''

IMPL = {}


def load(source):
    namespace = {}
    exec(source, namespace)
    IMPL["quote"] = namespace["quote"]


class HappyPathOnly(unittest.TestCase):
    def test_quote_returns_something(self):
        total, _ = IMPL["quote"](500, True, 0)
        self.assertGreater(total, 0)


class QuoteBehavior(unittest.TestCase):
    def test_member_pays_ninety_percent_plus_shipping(self):
        # Given 會員、小計 500、沒有折價券  When 報價  Then 450 + 運費 60
        self.assertEqual(IMPL["quote"](500, True, 0), (510, 60))

    def test_coupon_larger_than_subtotal_does_not_go_negative(self):
        self.assertEqual(IMPL["quote"](100, False, 200), (60, 60))

    def test_free_shipping_starts_exactly_at_1000(self):
        self.assertEqual(IMPL["quote"](1000, False, 0), (1000, 0),
                         "小計剛好 1000 元應免運（門檻含等於）")

    def test_free_shipping_threshold_uses_amount_after_coupon(self):
        self.assertEqual(IMPL["quote"](1050, False, 100), (1010, 60),
                         "折價後 950 元未達門檻，應收運費")

    def test_negative_coupon_is_rejected(self):
        with self.assertRaises(ValueError):
            IMPL["quote"](100, False, -1)


class QuoteProperties(unittest.TestCase):
    def test_invariants_hold_for_random_carts(self):
        rng = random.Random(2026)
        for _ in range(500):
            subtotal, coupon = rng.randint(0, 3000), rng.randint(0, 500)
            member = rng.random() < 0.5
            total, shipping = IMPL["quote"](subtotal, member, coupon)
            case = f"subtotal={subtotal}, member={member}, coupon={coupon}"
            self.assertIn(shipping, (0, 60), case)
            self.assertGreaterEqual(total, shipping, case)
            self.assertLessEqual(total, subtotal + 60, case)
            if member:
                plain_total, _ = IMPL["quote"](subtotal, False, coupon)
                self.assertLessEqual(total, plain_total, "會員不應付得比非會員多：" + case)


def run(*cases):
    suite = unittest.TestSuite()
    for case in cases:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return result


MUTANTS = [
    ("折扣率 90→80", "90 // 100", "80 // 100"),
    ("門檻 >= 改成 >", "after_coupon >= 1000", "after_coupon > 1000"),
    ("拿掉下限 max(0, …)", "max(0, discounted - coupon)", "(discounted - coupon)"),
    ("不檢查負數折價券", "subtotal < 0 or coupon < 0", "subtotal < 0"),
    ("運費 60→0", "else 60", "else 0"),
    ("門檻改用折價前金額", "0 if after_coupon >= 1000", "0 if discounted >= 1000"),
    ("會員判斷反轉", "if is_member else", "if not is_member else"),
    ("90//100 改寫成 9//10", "90 // 100", "9 // 10"),
]

print("== 1. 原始實作 ==")
load(PRICING_SRC)
r = run(QuoteBehavior, QuoteProperties)
print(f"跑了 {r.testsRun} 個測試，失敗 {len(r.failures) + len(r.errors)} 個")

print("\n== 2. 重構成規則表（行為不變）==")
load(REFACTORED_SRC)
r = run(QuoteBehavior, QuoteProperties)
print(f"跑了 {r.testsRun} 個測試，失敗 {len(r.failures) + len(r.errors)} 個")

print("\n== 3. Mutation testing ==")
print("mutant｜只有 happy path｜行為測試＋性質")
score = {"weak": 0, "strong": 0}
sample_message = None
for name, old, new in MUTANTS:
    assert old in PRICING_SRC, name
    load(PRICING_SRC.replace(old, new))
    weak = run(HappyPathOnly)
    strong = run(QuoteBehavior, QuoteProperties)
    weak_killed, strong_killed = not weak.wasSuccessful(), not strong.wasSuccessful()
    score["weak"] += weak_killed
    score["strong"] += strong_killed
    if name.startswith("門檻改用"):
        trace = strong.failures[0][1]
        sample_message = trace[trace.index("AssertionError"):].strip()
    label = lambda k: "killed" if k else "SURVIVED"
    print(f"{name}｜{label(weak_killed)}｜{label(strong_killed)}")
n = len(MUTANTS)
print(f"mutation score：happy path {score['weak']}/{n}，行為測試＋性質 {score['strong']}/{n}")
print("\n「門檻改用折價前金額」的失敗訊息：")
print(sample_message)
```

執行結果：

```text
== 1. 原始實作 ==
跑了 6 個測試，失敗 0 個

== 2. 重構成規則表（行為不變）==
跑了 6 個測試，失敗 0 個

== 3. Mutation testing ==
mutant｜只有 happy path｜行為測試＋性質
折扣率 90→80｜SURVIVED｜killed
門檻 >= 改成 >｜SURVIVED｜killed
拿掉下限 max(0, …)｜SURVIVED｜killed
不檢查負數折價券｜SURVIVED｜killed
運費 60→0｜SURVIVED｜killed
門檻改用折價前金額｜SURVIVED｜killed
會員判斷反轉｜SURVIVED｜killed
90//100 改寫成 9//10｜SURVIVED｜SURVIVED
mutation score：happy path 0/8，行為測試＋性質 7/8

「門檻改用折價前金額」的失敗訊息：
AssertionError: Tuples differ: (950, 0) != (1010, 60)

First differing element 0:
950
1010

- (950, 0)
+ (1010, 60) : 折價後 950 元未達門檻，應收運費
```

逐段解讀：

1. **被測程式放在字串裡**（`PRICING_SRC`），由 `load()` 用 `exec` 載入，並把 `quote` 放進 `IMPL`。這只是為了讓同一套測試能輪流跑在原始版、重構版與各個 mutant 上。真實專案不會這樣寫；mutation testing 工具會在檔案或 bytecode 層級做同樣的替換。
2. **`QuoteBehavior` 的五個測試各自對應一個行為**，名稱就是規格，期望值是手算得出的常數。注意它們只透過 `quote()` 的輸入與輸出驗證，完全不知道內部有沒有 `discounted` 這個變數。
3. **`QuoteProperties` 是一個用標準函式庫寫的 property 測試**：固定 seed 產生 500 組隨機購物車，檢查 23.8 列出的四條不變量，並把輸入寫進失敗訊息。真實專案可以用 Hypothesis 取得 shrinking 與反例資料庫。
4. **第 2 段是「四種變更」中的純重構**：`REFACTORED_SRC` 把計價改成規則表，門檻判斷從 `>= 1000` 改寫成 `< 1000` 的反向條件，結構完全不同，但 6 個測試全部通過，一個都不用改。這就是故事中小芸應該得到的結果。
5. **第 3 段是迷你 mutation testing**：每個 mutant 是一次字串替換，分別用「只有 happy path」與「行為測試＋性質」兩套測試去跑。Happy path 那個測試即使執行了 `quote()` 的大部分程式碼，一個 mutant 都殺不死；行為導向的測試殺死了 7 個。
6. **第 6 個 mutant 正是故事中的 bug**。它被 `test_free_shipping_threshold_uses_amount_after_coupon` 殺死，而失敗訊息同時給出實際值、期望值與規則說明，讀者不必打開測試檔就知道錯在哪。
7. **最後一個 mutant 存活了**，因為 `x * 9 // 10` 和 `x * 90 // 100` 對整數完全等價。這是 equivalent mutant 的實例：程式印出的 7/8 是未扣除 equivalent mutant 的原始比例，若依 26.8 節的公式把它從分母扣掉，分數是 7/7。7/8 不代表測試有缺口，而是提醒你 score 必須逐一解讀，不能只看數字。

把這個實驗對應回真實系統：「重構時保持綠燈」是 brittle 程度的檢驗，「mutant 被殺死」是辨識力的檢驗。一套好的 unit test 要同時通過這兩個檢驗；只追求其中一個是很容易的：完全不 assert 的測試永遠不會 brittle，把實作逐行抄進測試則什麼 mutant 都殺得死，但兩者都沒有用。

## 23.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 只透過 public API 測試 | 單元太大，public API 離複雜邏輯太遠，測試需要很長的 setup 才能觸及某個分支 | 整個 checkout 流程只有一個入口，想測運費分區規則必須先建立會員、購物車、地址、付款方式 | 這是設計訊號：把分區規則抽成獨立單元，有自己的 public API |
| DAMP 優先 | 重複多到讓修改變得危險 | 50 個測試各自手寫建立訂單的 15 行程式碼，訂單新增必填欄位時要改 50 處 | 用具名參數加預設值的 helper 收斂重複，測試裡只寫重要的值 |
| 一個測試一個行為 | 測試數量膨脹，執行時間與閱讀負擔上升 | 為每個輸入組合寫一個測試，結果有 400 個幾乎一樣的測試 | 用 table-driven（`subTest`）表達同一行為的多個例子；用 property 取代窮舉 |
| Property-based testing | 不變量寫得太弱或寫錯，給人假的信心 | 只檢查「金額 ≥ 0」，任何計價錯誤只要不是負數都會通過 | Property 與例子測試並用；用 mutation testing 檢驗 property 的辨識力 |
| Mutation testing | 運算成本高、equivalent mutant 造成噪音 | 對整個 monorepo 每晚跑，結果報告有上萬個存活 mutant 沒人看 | 只針對變更與高風險模組，存活 mutant 以 review 建議呈現 |
| 避免測試 interaction | 某些行為本身就是互動，只看 state 無法驗證 | 「每筆退款只能呼叫金流商一次」看不到 state | 這時互動就是 behavior，用 fake 或有限度的 mock 驗證（第 24 章） |
| 快照測試 | 輸出大量變動，reviewer 習慣直接更新快照 | 前端元件快照每次都有幾百行差異 | 縮小快照範圍，或改成對關鍵欄位的明確 assertion |

最後要說明的是：unit test 不能取代更大範圍的測試。一個計價模組的 unit test 全綠，不代表 checkout 服務在 production 中會用對的參數呼叫它，也不代表它和金流商的整合正確。Unit test 擅長的是「這個單元的規則對不對」；跨元件的契約、真實依賴的語意、效能與部署，需要第 25 章的 larger tests 來補。

## 23.12 AI 時代：什麼變了？

AI coding agent 已經能在幾秒內為一個函式產生幾十個測試。第 22 章（22.12 節）整理過 AI 生成測試的五個一般陷阱；這裡用本章的「四種結果」來看，它們在 unit test 層會變成哪兩種錯誤，以及 AI 能幫上什麼忙。

**第一種風險是漏報：鏡像測試（mirror test）。** Agent 讀懂實作再寫期望值，於是實作的 bug 也被寫成規格：如果免運門檻寫錯了，鏡像測試會認真地斷言「1,050 元用 100 元折價券應該免運」。用 23.2 的四格圖來說，這種測試永遠落在左下角，coverage 很高、辨識力接近零。本章的對策是 23.4 的「期望值要顯然正確」：期望值來自需求文件、產品規則或人手算的例子，agent 負責把它們展開成 Given-When-Then 測試。

**第二種風險是誤報：implementation-coupled（綁死實作的）測試。** Agent 為了讓測試快速通過，常常 mock 掉所有依賴、驗證內部呼叫，或直接呼叫 private method。這些測試在今天看起來都對，在下一次重構時就會變成小芸的 312 個紅燈。Review AI 產生的測試時，可以直接用本章的規則逐條檢查：是否只透過 public API？是否驗證 state 而非步驟？名稱是否描述行為？期望值是否顯然正確？

**第三，AI 讓 mutation testing 與 property 變得更實用。** 過去 mutation testing 最大的成本是人要逐一判斷存活的 mutant；現在可以讓 agent 先分類（真正缺口、equivalent、不重要），並為真正的缺口草擬測試，人只需要確認。同樣地，agent 擅長從需求文字中提出候選不變量，例如「任何折扣組合都不會讓總額為負」，人負責判斷這條性質是否真的是業務規則。

一個在 Harbor 運作良好的流程是：

```text
① 人寫下行為清單與關鍵例子（含邊界、錯誤情況、歷史 bug）
        │
② agent 展開成測試，並提出候選 property
        │
③ 在「已知正確」的版本上跑：全部要綠
        │
④ 跑 mutation testing（只針對變更的程式碼）：存活 mutant 交給 agent 分類
        │
⑤ 人 review：期望值是否來自需求？是否只用 public API？存活 mutant 的判斷是否合理？
```

這個流程的關鍵在第 ③、④ 步：用「改得動」與「抓得到」兩個客觀檢驗來評估 AI 產生的測試，而不是用測試數量或 coverage。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 從行為清單展開成 Given-When-Then 測試，補齊邊界值與錯誤情況 | 期望值必須來自需求或人工驗算，不能由 agent 讀實作後反推 |
| 從需求文字提出候選不變量，並寫成 property 測試 | 每條 property 是否為真正的業務規則，由 domain owner 確認 |
| 執行 mutation testing，把存活 mutant 分類並為缺口草擬測試 | Equivalent 與「不重要」的判斷要由 reviewer 確認；不把 mutation score 當成 KPI |
| 找出 brittle 測試：呼叫 private method、驗證呼叫順序、比對內部欄位 | 決定哪些行為是對外承諾、哪些只是實作細節 |
| 重構後大量測試失敗時，判斷哪些失敗是誤報、哪些是真的行為改變 | Agent 不得為了讓測試通過而修改 production 行為或刪除既有測試；需要改期望值時必須在 PR 中說明理由 |

> [!ai] AI 提醒
> 第 22 章建議把「修改既有測試的期望值」設成需要人類核准的動作。在 unit test 層可以再具體一點，直接套用 23.2 的四種變更：請 agent 在 PR 中標明這次是純重構、新功能、修 bug 還是行為改變。前三類的 PR 若修改了既有測試的期望值，CI 或 reviewer 就應該要求拆開或說明理由；只有標明為行為改變、並經 domain owner 確認的 PR，才可以改期望值。

## 23.13 專家怎麼想

- **「這個測試會因為什麼而失敗？」** 資深工程師 review 測試時，會想像三種未來：重構、新增功能、真正的 bug。好的測試只會在第三種情況失敗。如果能想到一個合理的重構會讓它變紅，就值得改寫。
- **測試難寫，先懷疑設計。** 如果測一個行為需要 mock 五個依賴、建立二十個物件，問題通常不在測試，而在單元的邊界畫錯了。測試是設計的第一個使用者，它的痛苦是最早的回饋。
- **期望值要「顯然正確」。** 專家寫 `assertEqual(total, 510)` 而不是 `assertEqual(total, compute_expected(...))`。測試沒有自己的測試，它的可信度只來自讀者一眼就能驗證。
- **把 bug 變成測試，再修 bug。** 每個 production bug 都先寫一個會失敗的測試重現它，再修程式碼讓它變綠。這保證 bug 被真正理解，也保證它不會回來；Harbor 的免運 bug 修好之後，`test_free_shipping_threshold_uses_amount_after_coupon` 就是這樣來的。
- **用 mutation 抽查，不用 coverage 驕傲。** Coverage 100% 只說明程式碼被執行過。專家會挑一個重要模組，手動改壞幾個地方，看測試會不會叫，這比任何儀表板都更能說明測試的品質。
- **測試名稱就是規格。** 把一個模組的測試名稱全部列出來，如果讀起來能當成這個模組的需求文件，這套測試大致就是健康的。

## 23.14 動手練習

1. 執行 23.10 的程式，然後在 `MUTANTS` 中再加入三個 mutant（例如把運費 60 改成 61、把 `coupon < 0` 改成 `coupon <= 0`、把 `max(0, …)` 改成 `max(1, …)`）。哪些被殺死？如果有存活的，補一個測試把它殺死。
2. 為 `quote()` 加入「指定品牌加碼 5% 折扣」的新規則，先寫出行為清單與至少 3 個例子測試（含邊界），再修改實作。確認既有的 6 個測試都不需要修改。
3. 從你手上的專案找出 3 個在最近一次重構中被修改過的測試，依 23.2 的「四種變更」判斷它們是否 brittle，並依 23.7 的表格找出原因與改法。
4. 把 23.10 中的 property 測試改成「先找出第一個反例，再把小計與折價券逐步減半，直到找不到更小的反例」，自己實作一個最簡單的 shrinking，並用一個故意寫錯的 mutant 測試它。
5. 寫一個過度 DRY 的測試類別（共用的 fixture dict、在 `setUp` 中建立所有資料），再改寫成 DAMP 版本，請一位同事分別讀兩個版本，記錄理解每個測試所花的時間。
6. 請 AI coding agent 為一段你熟悉的程式產生測試，然後用本章的規則逐條 review：期望值從哪裡來？有沒有呼叫 private method？有沒有驗證呼叫順序？最後用 mutation testing 比較 AI 測試與你手寫測試的辨識力。

## 本章重點整理

- 一套 unit test 的價值主要由維護成本與辨識力決定，而不是測試數量或寫起來多快。
- 測試會犯兩種錯：程式沒壞卻失敗（brittle），以及程式壞了卻通過（沒有辨識力）；兩者都會讓團隊不再信任測試。
- 用四種變更判斷 brittle：純重構、新功能、修 bug 都不應該需要修改既有測試，只有行為改變才應該。
- 透過 public API 測試，讓測試和真正的呼叫者使用同一個介面；想測的細節若值得測，就把它抽成有自己 API 的單元。
- 偏好 state testing：驗證結果，不驗證程式走了哪些步驟。
- 測行為而不是測方法；每個測試描述一個行為，用 Given-When-Then 結構組織，名稱描述前提與結果。
- 測試裡避免邏輯與計算，期望值要顯然正確，來自需求或手算。
- 測試程式碼追求 DAMP：寧可少量重複，也要讓每個測試單獨讀得懂；helper 用具名參數凸顯重要的值，測試基礎設施則可以 DRY 但要有自己的測試。
- 好的失敗訊息讓人不必打開測試原始碼就知道出了什麼錯：用具體的 assertion、比較 domain 值、在訊息中寫出規則與輸入。
- Property-based testing 以不變量探索大量輸入，與例子測試互補；找到的反例應轉成具名的例子測試。
- Coverage 只說明程式碼被執行，mutation testing 才檢驗測試能不能抓到 bug；存活的 mutant 要逐一判斷，equivalent mutant 無需殺死。
- AI 產生的測試最常見的問題是鏡像實作與綁死實作；以「重構時保持綠燈」與「mutant 會被殺死」兩個客觀檢驗來評估它們。

## 延伸問答

> [!question]- Q1. 「測 behavior 而不是 implementation」聽起來很抽象，實際寫測試時要怎麼判斷自己有沒有做到？
> 最直接的方法是做一個思想實驗：想像另一位工程師用完全不同的方式重新實作這個單元，例如把一串 if 改成規則表、把迴圈改成遞迴、把一個類別拆成三個，但對外結果完全相同。如果你的測試在這種重寫之後全部仍然通過，它測的就是 behavior；如果有測試因此失敗，那些測試綁住了 implementation。
>
> 寫測試時也可以檢查幾個具體訊號：測試是否只呼叫 public API；斷言的是回傳值與對外可觀察的狀態，還是 mock 的呼叫紀錄與內部欄位；期望值能否只靠需求文件寫出來，而不需要讀實作。三個問題都答「是」，通常就做到了。

> [!question]- Q2. 有一個很複雜的 private method，邏輯有十幾個分支，透過 public API 很難一一觸及。這時候可以直接測它嗎？
> 這種情況是一個設計訊號：那段邏輯複雜到值得單獨驗證，代表它可能已經是一個獨立的概念，只是還沒有被正式地抽出來。比較好的做法是把它抽成一個獨立的模組或類別，給它一個清楚、穩定的 public API，然後透過這個 API 測試它。原本的類別改成呼叫這個新模組。
>
> 這樣做和「直接測 private method」的差別在於承諾的方向。直接測 private method 是在不知情的情況下把一個實作細節變成合約；抽出模組則是有意識地決定「這個規則值得被當成合約維護」，名稱、參數與行為都經過設計。如果你判斷這段邏輯不值得被當成合約，那就應該回到透過原本的 public API 測試，接受 setup 會長一點。

> [!question]- Q3. DAMP 和 DRY 衝突時怎麼取捨？測試裡的重複難道不會造成維護問題嗎？
> 測試裡的重複確實有代價，例如訂單新增一個必填欄位時，五十個手寫建立訂單的測試都要改。所以 DAMP 不是鼓勵複製貼上，而是說「可讀性優先於去除重複」。實務上的取捨方式是：與測試意義無關的雜訊（建立物件的樣板、填入不重要的欄位）可以收斂進 helper；與測試意義有關的值（這個測試在乎的會員身份、小計、折價券）一定要寫在測試本體。
>
> 一個好的 helper 長得像 `make_order(subtotal=500, is_member=True)`：具名參數就是測試的重點，其他欄位有合理預設值。這樣既解決了「新增必填欄位要改五十處」的問題，又不會讓讀者需要跳到別處才能理解測試。真正要避免的是共用的資料常數與巨大的共用 fixture，因為它們把「重要的值」也藏了起來。

> [!question]- Q4. 你在 review 一個標題為「重構計價模組，無行為改變」的 PR，發現它同時修改了 40 個測試的期望值。你會怎麼處理？
> 首先要釐清這 40 個修改屬於哪一類。如果只是呼叫方式改變（例如測試原本呼叫已被刪除的 private method，現在改成呼叫 public API），那是在修正 brittle 測試，可以接受，但應該在 PR 描述中說明。如果是期望值改變（原本斷言 510，現在斷言 505），這就和「無行為改變」的標題直接矛盾：要嘛重構其實改變了行為，要嘛原本的測試是錯的。
>
> 兩種情況都不應該在一個「純重構」PR 中一起混過去。比較好的做法是請作者拆成兩個 PR：一個只做重構，所有期望值不變、測試全綠；另一個明確標示為行為改變，說明為什麼期望值要變，並請產品或 domain owner 確認。拆開之後，reviewer 才能分別判斷「重構是否正確」與「行為改變是否被允許」。

> [!question]- Q5. 一個模組的 line coverage 是 100%，mutation score 卻只有 40%。這代表什麼？下一步該做什麼？
> 這代表測試執行了每一行程式碼，但大多數的執行並沒有被有效驗證。常見原因是斷言太弱，例如只檢查結果不是 None、只檢查沒有丟出例外、只檢查金額大於 0；或者測試只覆蓋了 happy path 的輸入，邊界與錯誤情況雖然被執行到，卻沒有對應的期望值。23.10 的 HappyPathOnly 就是極端例子：它執行了大部分程式碼，卻一個 mutant 都殺不死。
>
> 下一步是逐一看存活的 mutant，把它們分成三類：真正的測試缺口（補測試）、equivalent mutant（標記忽略）、不重要的行為（例如 log 內容，可接受）。優先處理落在高風險邏輯上的缺口，例如金額計算與邊界條件。不建議把目標設成「mutation score 達到 80%」，而是設成「高風險模組不存在未經判斷的存活 mutant」。

> [!question]- Q6. Property-based testing 和「用很多組隨機輸入跑例子測試」有什麼差別？
> 隨機輸入的例子測試仍然需要知道每組輸入的期望輸出，而對隨機輸入算出期望輸出，通常只能在測試裡重寫一次實作，這正是本章說的「測試裡不要寫邏輯」。Property-based testing 改問的是對所有輸入都成立的關係，例如「總額不為負」「會員不會比非會員付得多」「decode(encode(x)) 等於 x」，這些關係不需要算出精確答案就能檢查。
>
> 此外，成熟的 property-based 框架還提供兩個隨機測試沒有的能力：shrinking 會把失敗的大輸入縮小成最簡單的反例，讓除錯容易得多；反例資料庫會記住曾經失敗的輸入，下次優先重跑，讓失敗可以重現。所以兩者的差別不只是輸入數量，而是測試的問法與失敗後的除錯體驗。

> [!question]- Q7. 你請 AI coding agent 替一個沒有測試的舊模組補測試，它產生了 60 個測試、coverage 從 0 升到 92%，全部通過。你會如何評估這批測試的品質？
> 先意識到「全部通過」本身不是品質證據：對一個沒有測試的舊模組，agent 最自然的做法是讀懂目前的實作再斷言它的行為，因此舊程式裡的 bug 也會被寫成期望值。評估時我會做幾件事。第一，抽樣閱讀測試，看名稱是否描述行為、是否只透過 public API、有沒有大量 mock 與呼叫順序的驗證。第二，跑 mutation testing，看這批測試能殺死多少 mutant，這比 coverage 更能反映辨識力。
>
> 第三，挑幾個關鍵行為，拿需求文件或請 domain owner 手算期望值，和 agent 寫的期望值對照；如果發現 agent 把一個疑似 bug 寫成了期望行為，應該把它標記出來討論，而不是默默接受。對舊程式來說，這種「記錄目前行為」的測試（常被稱為 characterization test）仍然有價值，它能在重構時偵測行為改變，但要在命名或註解中清楚標明它記錄的是現況而非已確認的需求。

> [!question]- Q8. 面試題：如果要你為一個新團隊制定 unit test 的寫法規範，你會放哪五條？為什麼？
> 我會放這五條：一，只透過 public API 測試，讓重構不需要修改測試；二，每個測試描述一個行為，用 Given-When-Then 組織，名稱寫出前提與預期結果，讓測試清單讀起來像規格；三，期望值寫成顯然正確的常數，測試裡不寫計算與條件邏輯；四，測試要 deterministic 與 independent，時間、隨機、外部依賴一律注入，不共享可變狀態；五，每個 production bug 都先寫一個會失敗的測試，再修程式碼。
>
> 理由是這五條分別對應測試最常見的失敗模式：第一條防 brittle，第二條讓失敗可理解，第三條防止測試與實作一起錯，第四條防 flaky，第五條確保測試持續吸收真實世界的教訓。我還會補充一條檢驗方法而不是規則：重要模組定期跑 mutation testing，用來驗證這些規範真的產生有辨識力的測試，而不是只產生看起來整齊的測試。

## 延伸閱讀

- [Software Engineering at Google — Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)：本章對應的原書章節，包含四種變更、透過 public API 測試、DAMP 與清晰失敗訊息的原始論述與 Java 範例。
- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)：test size 與 scope、Beyoncé Rule 與 Google 測試文化的背景，是第 22 章的對應章節。
- [Software Engineering at Google — Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)：state testing 與 interaction testing 的完整討論，接續到第 24 章。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：審查 AI 產生程式碼與測試時可以參考的檢查方向。
