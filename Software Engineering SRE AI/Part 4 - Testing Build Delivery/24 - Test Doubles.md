---
chapter: 24
title: Test Doubles：Fake、Stub、Mock 的選擇
part: 4
---

# 第 24 章　Test Doubles：Fake、Stub、Mock 的選擇

> [!abstract] 本章地圖
> **核心問題**：測試需要替換掉真實依賴時，怎麼選擇替身，才不會讓測試只證明「mock 照劇本演出」，卻和 production 的真實行為脫節？
>
> **你會學到**：
> - 分辨 dummy、stub、spy、mock、fake 五種 test double，以及它們各自回答的問題
> - 用 dependency injection 在程式中建立 seam，讓依賴可以被替換
> - 依「real → fake → stub／mock」的順序選擇替身，並說明每一步放棄了什麼
> - 判斷 interaction testing 什麼時候合理、什麼時候是 over-mocking
> - 用 contract test 讓 fake 和真實實作保持一致，並設計 fake 的故障注入
>
> **前置知識**：第 23 章（透過 public API 測試、state testing）、第 22 章（test size 與 scope）
>
> **對應原書**：SWE 第 13 章〈Test Doubles〉

## 24.1 故事：mock 說一切正常，金流商卻退了兩次款

Harbor 的 AI 客服 agent 開放「送出退款申請」半年後，大部分退款都從它開始：它查詢訂單、確認符合退款規則，送出一筆退款申請；客服人員在後台核准後，系統再呼叫內部的 `RefundService`，由這個服務向外部金流商發出退款。`RefundService` 由 payments 團隊維護，最重要的保護機制是 idempotency key（冪等鍵，第 41 章詳談）：同一筆退款申請不論送幾次，金流商都只會退一次錢。網路逾時時，`RefundService` 會用同一把 key 重試，確保不會重複退款。

某個週一，payments 團隊的小林為了讓 log 更好追蹤，重構了 `RefundService` 的重試迴圈，順手把產生 key 的那一行移進了迴圈裡。PR 附上的 unit test 全部通過，美華 review 時也沒看出問題。週四下午，金流商的 API 出現幾分鐘的網路抖動：有些退款請求在金流商那邊已經成功，回應卻在半路遺失。`RefundService` 判斷為逾時，用一把**新的** key 重試，金流商當然把它當成一筆新的退款。那幾分鐘內，有 23 筆已核准的退款申請被退了兩次款。沒有任何告警響起，因為每一次呼叫在系統看來都「成功」了；直到週五早上 payments 團隊和金流商做每日對帳，才發現退款總額對不上。

事後，platform 團隊的志明和 payments 團隊一起看測試，發現問題不在於「沒有測試」。重試邏輯有測試，而且寫得很認真：

```python
# not-runnable：事故前的測試
def test_retries_after_timeout(self):
    gateway = mock.Mock()
    gateway.refund.side_effect = [TimeoutError(), "rf_1"]
    self.assertEqual(RefundService(gateway).refund("ch_1", 300, "req-9"), "rf_1")
    self.assertEqual(gateway.refund.call_count, 2)
```

這個測試驗證了「逾時後會重試，第二次成功就回傳結果」。但 mock 版的 gateway 沒有任何記憶：它不知道第一次呼叫其實已經退款成功，也不在乎兩次呼叫的 key 是否相同。測試只證明了 `RefundService` 照著 mock 的劇本演出，而這份劇本正好漏掉了真實金流商最重要的行為。

團隊當初選擇 mock，是有理由的。更早之前，退款測試直接連到金流商的 sandbox 環境：每個測試要花兩三秒，sandbox 偶爾維護，CI 就整片紅掉。改成 mock 之後，測試變得又快又穩定，卻也從此和真實世界斷了線。

這一章要回答的問題是：測試裡什麼時候該換掉真實依賴？換成什麼？怎麼確保替身不說謊？

## 24.2 為什麼需要 test double

### 定義

**Test double**（測試替身）是在測試中代替真實依賴的物件或元件。名稱借自電影的「替身演員」：在危險或不方便的鏡頭裡，由替身上場。程式裡的「危險或不方便」包括：真的扣款、真的寄信、要等網路、要啟動資料庫。

被測的程式通常叫 **SUT**（System Under Test，被測系統）；SUT 依賴的元件叫 **DOC**（Depended-On Component，被依賴元件），也常直接叫 dependency。Test double 替換的就是 DOC。

### 為什麼需要

使用真實依賴的測試，常常會碰到下面幾種問題：

- **慢**：呼叫遠端 API、讀寫資料庫，一次可能數百毫秒到數秒。一千個測試就是十幾分鐘，開發者不會每改幾行就跑。
- **不穩定**：網路抖動、sandbox 維護、共用的測試資料被別人改掉，讓測試時好時壞（第 26 章的 flaky test）。
- **有副作用**：真的刷卡、真的寄通知簡訊給使用者，測試不能這樣做。
- **難以製造特定情況**：「金流商在處理成功後回應遺失」「庫存服務回傳 503」「時間剛好跨過午夜」這些情況，用真實依賴幾乎無法穩定重現，偏偏它們是 bug 最常藏身的地方。
- **還不存在或無法取得**：依賴的服務還在開發中，或屬於另一個公司。

Test double 解決這些問題的方式，是用一個**在測試中可控制**的替身取代依賴。但它要付出一個代價：**fidelity**（保真度），也就是替身的行為有多接近真實依賴。

```text
   保真度高 ◀──────────────────────────────────────────▶ 保真度低
   速度慢                                                速度快

   真實依賴        emulator／         fake            stub／mock
  （真的金流商     本地容器         （in-memory      （寫死回應、
    sandbox）    （真的資料庫）      實作）            記錄呼叫）
       │               │                │                 │
   最可信，但慢、   接近真實，        有真實語意的       最快最可控，
   不穩定、有副作用  啟動成本中等     簡化版本           但只知道你告訴它的事
```

這條光譜是本章的主軸。越往右，測試越快、越容易控制；越往左，測試越能代表真實世界。Harbor 的退款測試從最左邊（sandbox）直接跳到最右邊（mock），中間的選項全被跳過，結果是快了，卻失去了「金流商會記住 idempotency key」這個關鍵語意。

## 24.3 Seam 與 dependency injection

### 沒有 seam，就沒有替身

要使用 test double，程式必須留下一個可以替換依賴的位置。這個位置叫 **seam**（接縫）。看一個沒有 seam 的版本：

```python
# not-runnable：依賴寫死在函式裡
class RefundService:
    def refund(self, charge_id, amount, request_id):
        gateway = HttpPaymentGateway(PROVIDER_URL, api_key=load_secret())
        return gateway.refund(charge_id, amount, idempotency_key=f"refund-{request_id}")
```

`RefundService` 自己建立 `HttpPaymentGateway`，測試沒有任何辦法讓它改用別的 gateway，只能真的連到金流商，或者用 monkey patching（下面會說明）硬換。

### Dependency injection

**Dependency injection**（依賴注入，簡稱 DI）的意思是：物件不自己建立依賴，而是由外部「注入」給它。最簡單也最常見的形式是 **constructor injection**（建構子注入）：

```python
# not-runnable：用建構子注入依賴
class RefundService:
    def __init__(self, gateway, clock):
        self.gateway = gateway          # production 傳入 HttpPaymentGateway
        self.clock = clock              # 測試傳入 FakePaymentGateway、FakeClock

    def refund(self, charge_id, amount, request_id):
        ...
```

Production 程式在啟動時組裝真實依賴，測試則傳入替身。這個改動很小，卻讓 `RefundService` 從「只能和真的金流商一起測」變成「可以和任何符合介面的 gateway 一起測」。大型專案常用 DI 框架（Java 的 Dagger、Guice、Spring）自動組裝依賴；在 Python 這類動態語言中，多半直接用建構子參數或函式參數就夠了。

最值得注入的依賴，除了外部服務，還有三種常被忽略的隱性依賴：**時間**（`datetime.now()`）、**隨機**（`random`、UUID）與**環境**（環境變數、時區、locale）。它們不像外部服務那樣顯眼，卻是 flaky test 的常見來源（成因的完整分類在第 26 章）。把它們包成可注入的 `Clock`、`IdGenerator`，測試就能精確控制「現在幾點」「下一個 ID 是什麼」：

```python
# not-runnable：把時間與隨機變成可注入的依賴
class SystemClock:
    def now(self):
        return datetime.now(timezone.utc)

class FakeClock:
    def __init__(self, start):
        self.current = start
    def now(self):
        return self.current
    def advance(self, **delta):            # 測試可以一行跳過七天
        self.current += timedelta(**delta)

class CouponService:
    def __init__(self, clock, rng):
        self.clock = clock                 # production：SystemClock()
        self.rng = rng                     # production：random.Random()；測試：random.Random(42)

    def is_expired(self, coupon):
        return self.clock.now() >= coupon.expires_at

# 測試：精確落在邊界上，不必 sleep，也不受跑測試的時刻影響
clock = FakeClock(datetime(2024, 11, 11, 23, 59, 59, tzinfo=timezone.utc))
service = CouponService(clock, random.Random(42))
assert not service.is_expired(coupon_expiring_at_midnight)
clock.advance(seconds=1)
assert service.is_expired(coupon_expiring_at_midnight)
```

這裡有兩個細節。第一，`FakeClock` 是 fake 而不是 stub：它有狀態（目前時間），還能被測試推進，所以「剛好到期」與「差一秒到期」可以寫成同一個測試裡的兩個步驟。第二，隨機不是被「關掉」，而是換成固定 seed 的 `random.Random(42)` 實例：每次執行產生同一串數字，測試可重現；production 傳入沒有固定 seed 的實例。注入的是 `Random` 物件，而不是在全域呼叫 `random.seed()`，因為全域 seed 會影響同一個 process 中的其他程式碼與測試。

### Monkey patching 的位置

**Monkey patching** 是在執行期間直接替換模組或物件上的屬性，Python 的 `unittest.mock.patch` 就是這種工具：

```python
# not-runnable：用 patch 在執行期替換
with mock.patch("harbor.refunds.HttpPaymentGateway") as fake_cls:
    ...
```

它的好處是不用修改 production 程式碼就能替換依賴，在處理沒有 seam 的舊程式碼時很實用。代價是它依賴「被替換的東西在哪個模組、叫什麼名字」這個實作細節：有人把 import 改個位置，patch 就悄悄失效或報錯。因此 monkey patching 適合當成過渡手段，長期還是應該把依賴改成顯式注入。

> [!warning] 常見誤解
> 「為了可測試，每一個 library 呼叫都要包一層介面。」不需要。Seam 應該畫在有意義的邊界上：跨網路的服務、時間與隨機、昂貴或有副作用的資源。為了 `json.dumps` 或 `math.floor` 建立介面，只會增加一層沒有人需要的抽象。判斷標準是：這個依賴會不會讓測試變慢、不穩定或有副作用？會的話才值得一個 seam。

## 24.4 五種 test double

業界常用的分類來自 Gerard Meszaros 的《xUnit Test Patterns》（2007），把替身依「它在測試中扮演什麼角色」分成五種；Martin Fowler 的文章〈Mocks Aren't Stubs〉沿用這套用語，讓它廣為流傳。用 Harbor 的 `PaymentGateway` 為例：

| 類型 | 是什麼 | Harbor 的例子 | 回答的問題 |
|---|---|---|---|
| **Dummy** | 只是為了填參數，從來不會被真正使用 | 測試「金額為負就拒絕」時，傳入一個 `None` 或空物件當 gateway，因為程式在呼叫它之前就會先拒絕 | 「這個參數在這個測試裡根本不重要」 |
| **Stub** | 對呼叫回傳預先寫好的答案 | `gateway.refund` 永遠回傳 `"rf_1"`，或永遠丟出 `TimeoutError` | 「依賴回這個值時，SUT 會怎麼做？」 |
| **Spy** | Stub 加上「記錄被怎麼呼叫」，事後讓測試查詢 | 記下每次 `refund` 的參數，測試結束後檢查 key 是否相同 | 「SUT 實際上呼叫了什麼？」 |
| **Mock** | 預先設定「應該被怎麼呼叫」的期望，並驗證這些期望 | 期望 `refund` 被呼叫恰好一次，參數為 `("ch_1", 300)` | 「SUT 有沒有照約定的方式呼叫依賴？」 |
| **Fake** | 一個真的能運作、但簡化過的實作 | In-memory 的 `FakePaymentGateway`：會記錄每筆 charge 的已退金額、拒絕超額退款、記得 idempotency key | 「在接近真實的依賴下，SUT 的結果是否正確？」 |

《Software Engineering at Google》的第 13 章用的是另一組更精簡的詞：**faking**（使用 fake）、**stubbing**（指定回傳值）與 **interaction testing**（驗證呼叫方式，對應 spy 與 mock）。兩組詞描述的是同一件事，本章兩種都會用。Spy 與 mock 的差別在於「期望何時寫」：mock 在執行前就宣告期望（Fowler 的說法是，五種替身中只有 mock 堅持做行為驗證），spy 則先記錄、事後再由測試查詢。Python 的 `unittest.mock` 實際上比較接近 spy 的用法：先執行，事後用 `assert_called_once_with` 或 `call_args_list` 檢查。

有一個常見的混淆值得先澄清：**mocking framework**（例如 Python 的 `unittest.mock`、Java 的 Mockito）是一種工具，可以用來做 stub、spy 和 mock。所以「我用 `mock.Mock()`」不代表你在做 mock 意義上的 interaction testing；如果你只設定了 `return_value`、從來沒有驗證呼叫，那其實是 stubbing。Harbor 事故前的測試用 `side_effect` 設定回應（stubbing），又用 `call_count` 驗證呼叫次數（interaction testing），兩者混在一起，卻沒有一個在檢查真正重要的 state：金流商那邊到底退了多少錢。

## 24.5 選擇順序：real、fake，最後才是 stub 與 mock

### Prefer realism over isolation

原書給的核心建議是：**偏好真實，勝過隔離**（prefer realism over isolation）。能用真實實作就用真實實作；不能的話用 fake；fake 也沒有的時候，才考慮 stub 或 mock。理由很直接：替身越接近真實，測試通過時你越能相信 production 也會通過。反過來，如果 unit test 太依賴替身，工程師就得另外跑整合測試或手動驗證才能得到同樣的信心，而這些額外步驟一旦太費時，就常常被跳過。

原書也提醒一件常被誤會成缺點的事：使用真實實作時，依賴裡的 bug 會讓你的測試失敗，有時還會連帶讓一批測試一起紅。這是好事，因為它代表你的程式在 production 也會壞；有 CI 記錄每次變更的結果，通常很快就能找出是哪個變更造成的。

```text
            這個依賴可以直接用真的嗎？
            （夠快、deterministic、容易建立）
                 │                 │
                是                 否
                 │                 │
          ┌──────▼─────┐    有維護良好的 fake 嗎？
          │ 用真實實作  │        │            │
          └────────────┘       是            否
                                │            │
                         ┌──────▼─────┐   測試需要的是什麼？
                         │  用 fake    │     │                      │
                         └────────────┘   讓依賴回某個值      呼叫本身就是要驗證的行為
                                           或丟出錯誤         （只能呼叫一次、不能呼叫）
                                             │                      │
                                       ┌─────▼─────┐         ┌──────▼──────┐
                                       │  stub      │         │ mock／spy   │
                                       └───────────┘         └─────────────┘
                                 （並考慮：是不是該請 owner 提供 fake？）
```

這張決策圖從上往下讀。第一個問題是「真的能不能用」：很多依賴其實很適合直接使用，例如純計算的工具類別、資料結構、Harbor 自己的 `money.format_twd()`。不要因為「這是 unit test」就反射性地 mock 掉所有東西。第二個問題是「有沒有 fake」：如果依賴的 owner 提供了經過驗證的 fake，它幾乎總是比自己寫 stub 更好。只有在前兩條路都走不通時，才進入 stub 或 mock，並且根據「測試要的是回傳值，還是呼叫本身」決定用哪一種。

### 什麼時候可以用真實實作

原書列了三個判斷因素：

1. **執行時間**：真實實作夠快嗎？一個在記憶體中運算的類別通常沒問題；需要網路往返的服務通常不行。
2. **Determinism**：每次執行結果都一樣嗎？依賴時間、隨機或外部狀態的實作，會讓測試 flaky。
3. **建立依賴的成本**：建立這個真實物件，是否需要再建立一長串它的依賴？如果建立一個 `OrderRepository` 需要真的資料庫、連線池、schema migration，那它不適合出現在 small test 裡。

這三個問題沒有一個是「它是不是另一個類別」。同一個 process 內、行為 deterministic 的依賴，直接使用真實實作往往最好。

### Classical 與 mockist

社群中有兩種測試風格的長期討論（這組名稱也因 Fowler 的〈Mocks Aren't Stubs〉而普及）。**Classical testing**（古典派）偏好使用真實物件，只在不方便使用真實物件時才用替身，並以 state 驗證結果；**mockist testing**（mock 派）則傾向把有行為的協作者都換成 mock，以 interaction 驗證 SUT 的行為。原書承認業界有人實踐 mockist 風格（包括最早一批 mocking framework 的作者），但表明 Google 偏好古典派。理由有兩層：一是 mockist 風格難以規模化，它要求工程師在設計 SUT 時遵守嚴格的準則，而大多數工程師寫出來的程式自然比較適合古典派；二是 Google 觀察到過度使用 mocking framework 會讓測試充滿重複的設定程式碼，這些設定和真實實作逐漸脫節，也讓重構變得困難。本章的立場也是如此，但這不代表 mock 永遠是錯的，24.8 會說明它真正合理的場合。

## 24.6 Fake：有真實語意的替身

### Fake 是什麼

**Fake** 是依賴的一個輕量實作：它真的會運作，只是用比較簡單的方式。最常見的例子是用 in-memory 的 dict 實作一個 repository，取代真的資料庫；或者用一個記憶體中的帳本實作金流商 gateway。

Fake 和 stub 最大的差別在於 **fake 有狀態與語意**。Stub 只會回答你預先寫好的問題，問到劇本外的事它就不知道；fake 則像一個小型的真實系統：你先 charge 1,000 元、再退 800 元，它會記得；再退 300 元，它會拒絕，因為超過可退金額。測試不需要預先替每一步寫好劇本，只要像使用真實依賴一樣使用它，然後檢查最終狀態。

### 為什麼 fake 很重要

在 Harbor 的事故裡，如果 `RefundService` 的測試用的是一個會記住 idempotency key 的 fake，再加上「回應遺失」的故障注入，測試會發現：第一次退款已經成功，重試用了新的 key，於是總共退了 600 元而不是 300 元。這個 bug 不是靠更多的 mock 設定抓到的，而是靠替身本身帶有真實世界的語意。

Fake 還讓測試更容易寫、更容易讀。用 mock 測試「退款超過可退金額會被拒絕」，你得手動設定 mock 在第二次呼叫時丟出例外，等於在測試裡重新描述一次金流商的規則；用 fake，只要先 charge、再退兩次，讓 fake 自己判斷。規則只寫一次，寫在 fake 裡。

### 誰來寫 fake

寫一個好的 fake 需要對真實依賴有深入理解：哪些行為重要、哪些錯誤會發生、邊界在哪裡。因此原書建議 **fake 由擁有真實實作的團隊撰寫與維護**。在 Harbor，`FakePaymentGateway` 由 payments 團隊提供，和 `HttpPaymentGateway` 放在同一個套件裡，每次 gateway 的行為改變，fake 也一起改。使用它的團隊（客服、訂單、AI agent 團隊）不需要各自寫一份，也不會各自寫錯。

不是每個依賴都值得一個 fake。Fake 的成本是開發與長期維護，值得投資的通常是：被很多團隊使用的依賴、語意複雜（有狀態、有規則）的依賴、真實版本難以在測試中使用的依賴。一個只有一個呼叫者、只有一個方法的依賴，用 stub 可能就夠了。原書的判斷方式是比較「fake 帶來的生產力」與「撰寫加維護的成本」：只有少數使用者時可能不划算，有上百個使用者時收益就很明顯。

Fake 也要放在對的層次。原書建議 fake 只建在「無法在測試中使用」的那個根部：如果資料庫不能在測試中使用，就替資料庫 API 寫一個 fake，而不是替每個呼叫資料庫的類別各寫一個。在 Harbor，這代表 fake 的是 `PaymentGateway` 這一層，而不是 `RefundService`、`CheckoutService` 各自一份。

### Fidelity：要像到什麼程度

Fake 不需要、也不可能百分之百模擬真實系統。關鍵問題是：**它要對誰忠實？** 答案是對 **API 合約**忠實，也就是使用者依賴的那些行為。`FakePaymentGateway` 必須忠實的部分：

- 金額規則：已退金額加上這次退款不能超過原始 charge。
- Idempotency：同一把 key 的重複請求，回傳第一次的結果，而且不重複退款。
- 錯誤語意：找不到 charge、金額超過時，丟出和真實 adapter 相同的例外類型。

可以不忠實的部分：真實的網路延遲、金流商內部的風控流程、清算時間。原書的說法是，fake 要對真實實作完全忠實，但只需要「從測試的角度」忠實：例如雜湊 API 的 fake 不必算出和真實版本一樣的雜湊值，只要滿足測試真正依賴的性質（例如同一個輸入每次得到同一個值），因為合約本來就沒有保證具體的值。如果某個測試真的需要延遲或資源用量這類行為，它就不適合用 fake，應該往光譜左邊移，使用 sandbox 或 larger test（第 25 章）。

Fake 也不必實作真實版本的每一個功能，尤其是少有測試用到的罕見錯誤處理。但遇到不支援的路徑時，fake 應該**快速失敗**（fail fast），直接丟出「fake 不支援這個操作」的錯誤，而不是默默回傳一個看似合理的值。前者告訴工程師「這個測試不適合用 fake」，後者則會產生一個有自信的錯誤答案。

### 故障注入

好的 fake 不只模擬「正常」行為，也讓測試能精確製造「不正常」的情況。這叫 **fault injection**（故障注入）。Harbor 的 fake 提供 `lose_next_response()`：下一次退款在「金流商端」成功，但回應在網路上遺失。真實系統裡，這種情況幾秒鐘才出現一次，幾乎不可能用 sandbox 穩定重現；用 fake，一行程式就能製造。對分散式系統來說，最危險的 bug 往往藏在這些「部分成功」的情況裡，第 39 章與第 41 章會從 retry 與 idempotency 的角度再談一次。

### 沒有 fake 怎麼辦

如果依賴的 owner 沒有提供 fake，可以依序考慮：請 owner 提供（這是最根本的解法，也能讓其他團隊受益；owner 有時只是不知道 fake 對使用者的價值）；自己寫一個，做法是把所有對該 API 的呼叫包進一個自己的類別，再替這個類別寫 fake，因為你通常只用到 API 的一小部分，並用 contract test（24.10）驗證它和真實版本一致，日後也可以把它回饋給 owner；使用依賴官方提供的 **emulator**，例如許多資料庫與雲端服務有可以在本機執行的版本；或者在本機用容器啟動真實依賴，把測試升級成 medium test。

> [!warning] 常見誤解
> 「In-memory 資料庫就是資料庫的 fake，可以放心使用。」要看你依賴的是什麼語意。如果 production 用 PostgreSQL，測試用另一套 in-memory 資料庫，兩者在交易隔離等級、unique constraint 的檢查時機、日期與字串的比較規則上都可能不同。測試通過，代表程式在那套資料庫上正確，不代表在 PostgreSQL 上正確。對資料庫這類語意複雜的依賴，至少要有一部分測試跑在和 production 相同的資料庫上。

## 24.7 Stub：控制依賴的回應

### 什麼時候適合

**Stubbing** 是指定依賴在某次呼叫時回傳什麼。它最適合的場合是：**你需要讓依賴回傳一個特定的值，把 SUT 帶進某個狀態**，而且這個值本身不需要複雜的語意。例如：

- 讓庫存服務回傳 503，測試 checkout 會不會顯示「暫時無法結帳」而不是 500 錯誤頁。
- 讓匯率服務回傳固定的 31.5，測試外幣訂單的換算。
- 讓 gateway 永遠逾時，測試 `RefundService` 在重試三次後會丟出例外，而不是無限重試。

這些情況的共同點是：測試只關心「依賴回這個值之後，SUT 怎麼反應」，不在乎依賴內部的狀態。

### 過度 stubbing 的三個問題

原書指出，過度使用 stubbing 會讓測試出現三個問題：

**Unclear（難以理解）。** 一個測試如果有十行 `when(...).thenReturn(...)` 或 `side_effect = [...]`，讀者要先讀懂這十行劇本，才能理解測試在測什麼。劇本越長，越難看出哪一行是測試的重點、哪一行只是讓程式能跑下去。

**Brittle（脆弱）。** Stub 把「SUT 會用什麼參數、按什麼順序呼叫依賴」寫死在測試裡。這些都是實作細節：SUT 改成先查快取、改成批次呼叫、改了參數順序，stub 就不再匹配，測試就失敗了，即使 SUT 的結果完全正確。這和第 23 章的 brittle test 是同一個問題。

**Less effective（效果較差）。** Stub 的回應是測試作者寫的，它沒有辦法確認真實依賴真的會這樣回應。第 22 章開頭的事故就是這個機制：checkout 的測試用一份手寫的 payments 回應，裡面還是舊的 `amount` 欄位，payments 早已改成 `amount_cents`，兩邊的測試各自全綠。Harbor 還有過另一個例子：checkout 的測試 stub 金流商 SDK 回傳 `{"status": "ok"}`，但金流商的 v2 API 改成回傳 `"succeeded"`。所有測試都通過，因為 stub 永遠回 `"ok"`；上線之後，每一筆付款都被判斷成失敗。Stub 不會隨真實世界更新，它會靜靜地過期。

原書對 stub 的實用建議是：每一個被 stub 的函式都應該和測試的 assertion 有直接關係。如果拿掉某一行 stub 設定，測試的結論不變，那一行多半只是在讓程式跑下去，應該考慮改用 fake 或真實實作。

一個實用的警訊是：如果你發現自己在 stub 中寫出了依賴的業務規則（例如「如果參數是負數就丟例外，否則回傳金額乘以 100」），那你其實在寫一個沒有人驗證過的 fake。這時應該停下來，改用或請 owner 提供真正的 fake。

## 24.8 Interaction testing：什麼時候該驗證呼叫

### State testing 與 interaction testing

第 23 章介紹過兩種驗證方式。**State testing** 觀察 SUT 執行後的結果：回傳值、fake 中的狀態、資料庫中的資料。**Interaction testing** 觀察 SUT 怎麼呼叫依賴：呼叫了哪個方法、幾次、用什麼參數。

用退款為例，兩種測試問的是不同的問題：

```text
  Interaction testing                       State testing
  ───────────────────                       ─────────────
  「refund 有被呼叫兩次嗎？」               「這筆 charge 最後被退了多少錢？」
          │                                          │
  只知道 SUT 送出了什麼                      知道這些呼叫在真實語意下的結果
          │                                          │
  重試用了新的 key → 仍然是兩次呼叫 → ✔      重試用了新的 key → 退了 600 元 → ✘
```

左邊的測試在事故版本上仍然通過，因為它驗證的是「SUT 做了什麼動作」，而不是「這些動作造成了什麼結果」。右邊的測試直接檢查使用者在乎的事：錢有沒有被退對。這就是原書建議 **prefer state testing over interaction testing** 的原因。原書指出 interaction testing 的兩個根本問題：第一，它無法告訴你 SUT 真的正確，只能告訴你某些函式被照預期呼叫了，等於假設「呼叫了 `refund()`，錢就會被正確地退」；state testing 則實際驗證這個假設。第二，它把「SUT 會呼叫這個函式」這個實作細節洩漏進測試，讓測試變脆弱。Google 內部有人開玩笑地把過度使用 interaction testing 的測試叫做 **change-detector test**：production 程式碼一有任何變動就失敗，即使行為完全沒變。

### 什麼時候 interaction testing 是合理的

Interaction testing 不是錯的，它在兩類情況下是正確的選擇（這兩類也是原書列出的）：

1. **無法做 state testing**：沒有真實實作可用，也沒有 fake，無法觀察依賴的狀態。例如第三方的簡訊服務沒有提供任何查詢 API，你只能驗證「有沒有用正確的參數呼叫它」。這時 interaction testing 是退而求其次的選擇，應該同時考慮是否值得為它建立 fake。
2. **呼叫的次數或順序本身會造成問題**：例如快取的目的是「不要重複呼叫後端」，那麼「後端只被呼叫一次」就是快取的行為本身；「審計 log 一定要在退款前寫入」這種合規要求，順序就是需求。

即使在這兩種情況下，interaction testing 也不能完全取代 state testing。原書的建議是：如果某個行為在 unit test 中只能用 interaction 驗證，就認真考慮補一個更大範圍、能做 state testing 的測試，例如對真實資料庫跑一次 integration test（第 25 章）。

### 兩條實務規則

原書給了兩條很實用的規則：

**只對會改變狀態的呼叫做 interaction testing。** 呼叫可以分成兩類：**state-changing**（改變狀態，例如 `refund()`、`send_email()`、`save()`）與 **non-state-changing**（不改變狀態，例如 `get_order()`、`lookup_rate()`）。驗證「SUT 有沒有呼叫 `get_order()`」幾乎沒有價值：SUT 用什麼方式取得資料是實作細節，換成快取或批次查詢都不影響結果。驗證「SUT 有沒有用正確的金額呼叫 `refund()`」則有意義，因為這個呼叫會改變世界。

**避免 overspecification（過度規定）。** 只驗證和這個測試的行為有關的參數與呼叫。如果測試的行為是「退款金額正確」，就只檢查金額，不要同時規定 log 訊息、呼叫順序與每個參數的完整值。每多規定一件事，就多一個讓測試在無關變更時失敗的理由。

### Don't mock what you don't own

另一條常被引用的經驗法則是：**不要 mock 你不擁有的型別**（常見出處是 Steve Freeman 與 Nat Pryce 的《Growing Object-Oriented Software, Guided by Tests》）。直接 mock 第三方 SDK（例如金流商的 Python client），測試就綁死在這個 SDK 的介面細節上，而且你對它的行為只能用猜的。比較好的做法是在中間放一層自己擁有的 **adapter**：Harbor 定義自己的 `PaymentGateway` 介面（`charge`、`refund`、`refunded_total`），用 `HttpPaymentGateway` 把它翻譯成金流商的 API。業務程式只依賴這個介面，測試替換的是 Harbor 自己的介面，而 adapter 本身則用 contract test 和 sandbox 驗證。

有些組織更進一步，讓 API owner 直接標記「這個型別不要被 mock」。原書的案例是 Google 為 Java 建立的 `@DoNotMock` 標註，收錄在 Google 的 Java 靜態分析工具 Error Prone 中：工程師用 mocking framework 替被標註的型別建立 mock 時，會得到一個錯誤（不只是提醒），錯誤訊息引導改用 owner 指定的替代方案，例如真實實作或 fake。原書說它最常用在兩種型別上：簡單到可以直接使用的 value object，以及已經有設計良好的 fake 的 API。Owner 在意這件事的原因是，每一份 mock 設定都複製了一小段 API 的行為；當同一個型別在整個 codebase 被 mock 了成千上萬次，這些複本很可能違反真實合約，也讓 owner 幾乎無法修改實作。

### 讓 mock 至少知道介面

如果真的需要 mock，至少讓它知道真實介面長什麼樣子。Python 的 `mock.Mock()` 預設接受任何屬性與任何參數：打錯方法名稱、少傳一個參數，mock 都照單全收，測試照樣通過。`mock.create_autospec(SomeClass)` 會依照真實類別的方法簽名建立 mock：呼叫不存在的方法會丟出 `AttributeError`，參數不符會丟出 `TypeError`。這能抓到「介面漂移」，例如有人重新命名了方法，但它抓不到「語意漂移」，例如金流商改了回傳的狀態字串。語意漂移需要 fake 加上 contract test。

## 24.9 Over-mocking：症狀與修復路線

把前面的問題放在一起看，**over-mocking**（過度 mock）的症狀很容易辨認：

| 症狀 | 背後的問題 | 修復方向 |
|---|---|---|
| 測試的 setup 有十幾行 mock 設定，assert 只有一行 | 測試的主要內容是劇本，不是行為 | 改用 fake，讓依賴自己產生合理的回應 |
| 每次重構都有一批「呼叫方式改變」的測試失敗 | 測試驗證了 non-state-changing 呼叫或呼叫順序 | 改成 state testing；只對 state-changing 呼叫驗證關鍵參數 |
| Mock 被設定成回傳另一個 mock，再回傳另一個 mock | SUT 違反了 Law of Demeter（一路往依賴的內部伸手），或測試替換的層次太低 | 調整 SUT 的設計，讓它只依賴直接的協作者 |
| 單元測試全綠，整合後馬上壞 | Mock 的行為和真實依賴不一致 | 為依賴建立 fake 並跑 contract test；補上 larger test |
| 測試裡寫出了依賴的業務規則 | 正在寫一個沒有驗證過的 fake | 把規則移到正式的 fake，由 owner 維護 |
| 被測類別所有協作者都被 mock，包括純計算的工具類別 | 反射性地隔離，而不是依需要隔離 | 依 24.5 的決策圖，能用真實實作的就用真實實作 |

修復 over-mocking 通常不是一次重寫，而是一條漸進的路線：先替最常被 mock 的依賴建立一個 fake（通常是資料存取層或對外的 gateway）；新測試一律使用 fake；舊測試在下次因重構而失敗時，順手改寫成使用 fake，而不是更新 mock 的劇本。幾個月後，團隊會發現「重構要修測試」的時間明顯下降。

## 24.10 Contract test：讓 fake 不說謊

### Fake 也會漂移

Fake 比 stub 更接近真實，但它仍然是另一份實作，仍然可能和真實版本**漂移**（drift）：真實的金流商改了規則，fake 沒有跟著改；或者寫 fake 的人一開始就誤解了某個行為。漂移的 fake 比沒有 fake 更危險，因為它讓測試給出有自信的錯誤答案。

### 同一套測試，兩個實作

解法是 **contract test**（合約測試）：寫一套描述介面行為的測試，讓 fake 與真實實作**都跑同一套**。只要兩者都通過，就能確定它們在這些行為上一致。

```text
                ┌──────────────────────────────┐
                │   GatewayContract（一套測試） │
                │  · 部分退款會被記錄            │
                │  · 超額退款會被拒絕            │
                │  · 同一把 key 只退一次         │
                │  · 不存在的 charge 會被拒絕    │
                └──────────────┬───────────────┘
                   ┌───────────┴────────────┐
                   ▼                        ▼
       HttpPaymentGateway              FakePaymentGateway
       ＋ 金流商 sandbox                （in-memory）
       每晚或 adapter 變更時執行          每次 presubmit 執行
                   │                        │
                   └──── 兩邊都通過 ─────────┘
                    → 使用 fake 的所有測試，結論可信
```

這張圖的重點是兩側的執行頻率不同。Fake 那一側很快，可以在每次 presubmit 中執行；真實實作那一側要連 sandbox，比較慢也比較不穩定，因此放在每晚的排程或 adapter 有變更時執行。原書也點出為什麼這個成本可以接受：慢的那一側只需要由 fake 的 owner 執行，數百個使用 fake 的測試完全不用付這個代價。當 sandbox 那一側失敗、fake 那一側通過時，就代表 fake 已經漂移，或金流商的行為改變了：payments 團隊必須在其他團隊被錯誤的 fake 誤導之前修正它。

### Contract test 要寫什麼

Contract test 寫的是**使用者依賴的語意**，正好是 24.6 所說「fake 要對誰忠實」的那份清單：正常路徑、錯誤路徑、邊界條件、冪等性等。它不需要窮舉真實系統的所有細節，但每一條使用者依賴的行為都應該出現。實務上，contract test 通常和 fake 放在同一個套件裡，由同一個 owner 維護；新增一條行為時，先寫 contract test，再讓 fake 與 adapter 都通過。

### 錄製回應的做法

另一種常見的做法是 **record／replay**：在某次執行時錄下真實依賴的回應，之後的測試播放錄音。它能提高 fidelity，但有兩個要注意的地方：錄音會過期（真實 API 改了，錄音不會改），因此要記錄錄製日期與 API 版本並定期重錄；錄音可能含有敏感資料（token、個人資料、卡號），必須先做遮罩才能放進 repository。

Contract test 在這裡處理的是「fake 與真實實作是否一致」。另一個相關但不同的問題是「兩個服務之間的 API 合約是否一致」，例如 checkout 服務對 inventory 服務的期望，業界常用 consumer-driven contract test（例如 Pact）來處理：第 5 章從 Hyrum's Law 的角度介紹過它，第 25 章（25.5 節）詳談實作。兩者的差別在於誰寫合約、比對的對象是什麼：本節的 contract test 由 fake 的 owner 撰寫，比對「fake 與真實實作」；consumer-driven contract 由呼叫方撰寫，比對「呼叫方的期望與提供方的真實服務」。

## 24.11 動手寫：mock、fake 與 contract test 的對照實驗

下面的程式重現 24.1 的事故。它包含一個模擬金流商 API 的 `SandboxProvider`、Harbor 的 production adapter `HttpPaymentGateway`、payments 團隊提供的 `FakePaymentGateway`，以及正確版與重構後有 bug 的 `RefundService`。程式用同一個行為分別寫成 mock 風格與 fake 風格的測試，再用 contract test 檢查 fake 是否漂移，最後示範 `create_autospec` 能抓到什麼。

```python
import io
import itertools
import unittest
from unittest import mock


class RefundRejected(Exception):
    pass


# ---------- 外部金流商（真實世界中在網路另一端）----------
class SandboxProvider:
    """模擬金流商 HTTP API：金額以「分」計，支援 idempotency key。"""

    def __init__(self):
        self.charges = {}
        self.responses = {}           # idempotency key → 第一次的回應
        self.ids = itertools.count(1)

    def post(self, path, body, idempotency_key):
        if idempotency_key in self.responses:
            return self.responses[idempotency_key]
        if path == "/v2/charges":
            cid = f"ch_{next(self.ids)}"
            self.charges[cid] = {"amount": body["amount"], "refunded": 0}
            resp = {"status": 201, "id": cid}
        elif path == "/v2/refunds":
            charge = self.charges.get(body["charge"])
            if charge is None:
                resp = {"status": 404, "error": "no_such_charge"}
            elif charge["refunded"] + body["amount"] > charge["amount"]:
                resp = {"status": 400, "error": "amount_exceeds_refundable"}
            else:
                charge["refunded"] += body["amount"]
                resp = {"status": 201, "id": f"rf_{next(self.ids)}"}
        else:
            resp = {"status": 404, "error": "no_such_path"}
        self.responses[idempotency_key] = resp
        return resp


# ---------- Harbor 自己的介面與兩個實作 ----------
class HttpPaymentGateway:
    """Production adapter：把 Harbor 的介面（元）翻譯成金流商 API（分）。"""

    def __init__(self, provider):
        self.provider = provider

    def charge(self, order_id, amount):
        resp = self.provider.post("/v2/charges", {"amount": amount * 100}, f"charge-{order_id}")
        return resp["id"]

    def refund(self, charge_id, amount, idempotency_key):
        resp = self.provider.post("/v2/refunds", {"charge": charge_id, "amount": amount * 100},
                                  idempotency_key)
        if resp["status"] != 201:
            raise RefundRejected(resp["error"])
        return resp["id"]

    def refunded_total(self, charge_id):
        return self.provider.charges[charge_id]["refunded"] // 100


class FakePaymentGateway:
    """In-memory fake：由 payments 團隊維護，必須通過同一套 contract tests。"""

    def __init__(self, honor_idempotency=True):
        self.charges, self.seen = {}, {}
        self.ids = itertools.count(1)
        self.honor_idempotency = honor_idempotency
        self._lose_next = False

    def lose_next_response(self):
        """故障注入：下一次 refund 在金流商端成功，但回應在網路上遺失。"""
        self._lose_next = True

    def charge(self, order_id, amount):
        cid = f"ch_{next(self.ids)}"
        self.charges[cid] = {"amount": amount, "refunded": 0}
        return cid

    def refund(self, charge_id, amount, idempotency_key):
        if self.honor_idempotency and idempotency_key in self.seen:
            return self.seen[idempotency_key]
        charge = self.charges.get(charge_id)
        if charge is None:
            raise RefundRejected("no_such_charge")
        if charge["refunded"] + amount > charge["amount"]:
            raise RefundRejected("amount_exceeds_refundable")
        charge["refunded"] += amount
        rid = self.seen[idempotency_key] = f"rf_{next(self.ids)}"
        if self._lose_next:
            self._lose_next = False
            raise TimeoutError("response lost")
        return rid

    def refunded_total(self, charge_id):
        return self.charges[charge_id]["refunded"]


# ---------- 被測系統：退款服務（客服人員核准 AI 客服送出的退款申請後，由它執行退款）----------
class RefundService:
    def __init__(self, gateway, max_attempts=3):
        self.gateway, self.max_attempts = gateway, max_attempts

    def refund(self, charge_id, amount, request_id):
        key = f"refund-{request_id}"                 # 每次重試都用同一把 key
        for _ in range(self.max_attempts):
            try:
                return self.gateway.refund(charge_id, amount, idempotency_key=key)
            except TimeoutError:
                continue
        raise TimeoutError("gateway unavailable")


class RefundServiceAfterRefactor(RefundService):
    counter = itertools.count(1)

    def refund(self, charge_id, amount, request_id):
        for _ in range(self.max_attempts):
            key = f"refund-{request_id}-{next(self.counter)}"   # bug：key 移進迴圈
            try:
                return self.gateway.refund(charge_id, amount, idempotency_key=key)
            except TimeoutError:
                continue
        raise TimeoutError("gateway unavailable")


# ---------- 兩種測試風格 ----------
class MockStyleTest(unittest.TestCase):
    SERVICE = RefundService

    def test_retries_after_timeout(self):
        gateway = mock.Mock()
        gateway.refund.side_effect = [TimeoutError(), "rf_1"]
        self.assertEqual(self.SERVICE(gateway).refund("ch_1", 300, "req-9"), "rf_1")
        self.assertEqual(gateway.refund.call_count, 2)


class FakeStyleTest(unittest.TestCase):
    SERVICE = RefundService

    def test_lost_response_then_retry_refunds_exactly_once(self):
        gateway = FakePaymentGateway()
        charge_id = gateway.charge("order-1", 1000)
        gateway.lose_next_response()
        self.SERVICE(gateway).refund(charge_id, 300, "req-9")
        self.assertEqual(gateway.refunded_total(charge_id), 300, "重試不可重複退款")


# ---------- Contract tests：fake 與 production adapter 跑同一套 ----------
class GatewayContract:
    def make_gateway(self):
        raise NotImplementedError

    def setUp(self):
        self.gw = self.make_gateway()
        self.charge_id = self.gw.charge("order-1", 1000)

    def test_partial_refund_is_recorded(self):
        self.gw.refund(self.charge_id, 300, "k1")
        self.assertEqual(self.gw.refunded_total(self.charge_id), 300)

    def test_refund_beyond_charge_is_rejected(self):
        self.gw.refund(self.charge_id, 800, "k1")
        with self.assertRaises(RefundRejected):
            self.gw.refund(self.charge_id, 300, "k2")

    def test_same_idempotency_key_refunds_once(self):
        first = self.gw.refund(self.charge_id, 300, "k1")
        second = self.gw.refund(self.charge_id, 300, "k1")
        self.assertEqual((first, self.gw.refunded_total(self.charge_id)), (second, 300))

    def test_unknown_charge_is_rejected(self):
        with self.assertRaises(RefundRejected):
            self.gw.refund("ch_404", 100, "k1")


class HttpGatewayContract(GatewayContract, unittest.TestCase):
    def make_gateway(self):
        return HttpPaymentGateway(SandboxProvider())


class FakeGatewayContract(GatewayContract, unittest.TestCase):
    def make_gateway(self):
        return FakePaymentGateway()


class DriftedFakeContract(GatewayContract, unittest.TestCase):
    def make_gateway(self):
        return FakePaymentGateway(honor_idempotency=False)


def run(case, **attrs):
    case = type(case.__name__, (case,), attrs) if attrs else case
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    failed = [t.id().split(".")[-1] for t, _ in result.failures + result.errors]
    return f"{result.testsRun - len(failed)}/{result.testsRun} 通過" + (f"，失敗：{failed}" if failed else "")


print("== 1. 同一個測試，分別用 mock 與 fake ==")
for service in (RefundService, RefundServiceAfterRefactor):
    print(f"{service.__name__}")
    print(f"  mock 風格：{run(MockStyleTest, SERVICE=service)}")
    print(f"  fake 風格：{run(FakeStyleTest, SERVICE=service)}")

print("\n== 2. Contract tests ==")
for case in (HttpGatewayContract, FakeGatewayContract, DriftedFakeContract):
    print(f"{case.__name__}：{run(case)}")

print("\n== 3. 沒有 spec 的 mock 會接受不存在的呼叫 ==")
loose = mock.Mock()
loose.refund_order("ch_1", 300)                     # 方法名稱打錯
print("Mock()：refund_order(...) 沒有報錯")
strict = mock.create_autospec(FakePaymentGateway, instance=True)
for label, call in [("refund_order(...)", lambda: strict.refund_order("ch_1", 300)),
                    ("refund(ch, amount) 少了 key", lambda: strict.refund("ch_1", 300))]:
    try:
        call()
    except (AttributeError, TypeError) as exc:
        print(f"autospec：{label} → {type(exc).__name__}")
```

執行結果：

```text
== 1. 同一個測試，分別用 mock 與 fake ==
RefundService
  mock 風格：1/1 通過
  fake 風格：1/1 通過
RefundServiceAfterRefactor
  mock 風格：1/1 通過
  fake 風格：0/1 通過，失敗：['test_lost_response_then_retry_refunds_exactly_once']

== 2. Contract tests ==
HttpGatewayContract：4/4 通過
FakeGatewayContract：4/4 通過
DriftedFakeContract：3/4 通過，失敗：['test_same_idempotency_key_refunds_once']

== 3. 沒有 spec 的 mock 會接受不存在的呼叫 ==
Mock()：refund_order(...) 沒有報錯
autospec：refund_order(...) → AttributeError
autospec：refund(ch, amount) 少了 key → TypeError
```

逐段解讀：

1. **`SandboxProvider` 代表網路另一端的金流商**。它以「分」為單位、用 dict 保存每筆 charge 的已退金額，並記住每把 idempotency key 的第一次回應。真實世界裡這是金流商的系統；在這個程式裡它讓我們有一個「真實語意」的參考點。
2. **`HttpPaymentGateway` 是 production adapter**，把 Harbor 自己的介面（元）翻譯成金流商的 API（分）。業務程式只依賴 `charge`、`refund`、`refunded_total` 這三個方法，這就是 24.8 說的「替換你擁有的介面」。
3. **`FakePaymentGateway` 是 payments 團隊維護的 fake**。它用更簡單的方式實作同樣的語意：金額上限、idempotency、錯誤類型。`lose_next_response()` 是故障注入：退款在 fake 內部已經成功，卻丟出 `TimeoutError`，正好模擬事故當天的情況。
4. **第 1 段結果是事故的核心**。Mock 風格的測試在正確版與有 bug 的版本上都通過，因為 mock 只知道「被呼叫了兩次」；fake 風格的測試在有 bug 的版本上失敗，失敗訊息是「重試不可重複退款」，因為 fake 記得第一次已經退過，第二把新的 key 讓它又退了一次，最終已退金額是 600 而不是 300。這個測試檢查的是 state，而且不需要知道 `RefundService` 內部怎麼重試。
5. **第 2 段是 contract test**。`GatewayContract` 是一個不繼承 `TestCase` 的 mixin，裡面的四個測試只透過介面操作 gateway；三個子類別分別用 sandbox adapter、正確的 fake 與一個「忘了實作 idempotency」的漂移 fake 來跑。前兩者 4/4 通過，代表 fake 可信；漂移的 fake 在 `test_same_idempotency_key_refunds_once` 失敗，在任何團隊被它誤導之前就被抓出來。
6. **第 3 段示範 mock 的介面檢查**。沒有 spec 的 `Mock()` 接受打錯名稱的 `refund_order`；`create_autospec` 依照 `FakePaymentGateway` 的真實簽名，對不存在的方法丟出 `AttributeError`、對少了參數的呼叫丟出 `TypeError`。但要注意它只檢查介面形狀，不知道任何語意：第 1 段的 bug 換成 autospec 一樣抓不到。

把這個實驗對應回 Harbor 的真實系統：`SandboxProvider` 的位置是金流商的 sandbox 環境，contract test 的 sandbox 那一側每晚執行；`FakePaymentGateway` 與 contract test 由 payments 團隊放在同一個套件中發布；客服、訂單與 AI agent 團隊的 unit test 一律使用這個 fake。事故之後，Harbor 也把「重試時 key 必須不變」這個行為加進了 `RefundService` 的 unit test，正是第 1 段的 fake 風格測試。

## 24.12 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 直接使用真實依賴 | 依賴變慢、不穩定或有副作用 | Checkout 測試直接連金流商 sandbox，sandbox 維護時 CI 全紅，開發者開始忽略失敗 | 把真實依賴的測試移到 larger test 或每晚的 contract test，unit test 改用 fake |
| 使用 fake | Fake 與真實版本漂移，給出有自信的錯誤答案 | 金流商改成「部分退款需要至少 1 元」，fake 沒更新，測試接受 0 元退款 | Fake 由 owner 維護，與真實實作跑同一套 contract test，真實那一側定期執行 |
| 使用 fake | 寫 fake 的成本高於收益 | 只有一個呼叫者、只用到一個查詢方法的內部依賴，卻花一週寫 fake | 依呼叫者數量與語意複雜度決定；簡單依賴用 stub 即可 |
| 使用 stub | Stub 的回應過期，和真實依賴不一致 | Stub 回傳 `"ok"`，金流商 v2 改成 `"succeeded"`，所有測試通過、上線後付款全被判失敗 | 回應格式由 adapter 處理並以 contract test 驗證；業務程式的測試替換 adapter，而不是 SDK |
| Interaction testing | 驗證了實作細節，重構就失敗 | Mock 規定「先查快取再查資料庫」，改成同時查詢後全部失敗 | 只驗證 state-changing 呼叫的關鍵參數；其餘用 state testing |
| Interaction testing | 驗證了「呼叫了」，卻沒驗證「結果對」 | 24.1 的事故：重試兩次的呼叫次數正確，但重複退款 | 對有語意的依賴（金額、冪等）使用 fake 並檢查最終狀態 |
| Monkey patching | Patch 的目標路徑隨 import 位置改變而失效 | 有人把 `from gateway import Http...` 改成 `import gateway`，patch 不再生效，測試真的打到網路 | 改成顯式的 dependency injection；必須 patch 時 patch 在被使用的位置，並讓測試環境禁止對外連線 |
| Record／replay | 錄音過期或洩漏敏感資料 | 一年前的錄音含真實卡號末四碼與 token，且早已不符合現行 API | 錄音遮罩敏感欄位、記錄 API 版本與錄製日期、定期重錄 |

## 24.13 AI 時代：什麼變了？

AI 生成測試傾向過度 mock，這是第 22 章（22.12 節）列出的一般品質陷阱之一，這裡不再重複。本節聚焦在 test double 特有的幾個角度。

**Agent 寫的 stub 是「猜出來的合約」。** Agent 替依賴寫 stub 時，回傳值通常不是從真實系統觀察來的，而是從函式名稱、型別提示與訓練資料中常見的 API 形狀推測出來的：它可能讓金流商回傳 `{"status": "success"}`，而真實 API 回的是 `"succeeded"`；它可能假設逾時一定代表沒有扣款。這比人手寫的 stub 更危險，因為它看起來很合理，而且一次產生幾十個。24.7 說的「stub 會靜靜過期」在這裡變成「stub 一開始就是錯的」。判斷方式是看 stub 的回應有沒有出處：來自 contract test 驗證過的 fake、錄製的真實回應，還是 agent 的想像。

**Agent 修測試時，最容易改的是劇本。** 當重構讓 mock 測試失敗，agent 最快的修法是更新 `side_effect` 與 `assert_called_with`，讓劇本重新符合新的實作。這會把 change-detector test 永久保存下來，而且每次都「修好」。Harbor 的規則是：mock 測試因重構失敗時，agent 的任務是把它改寫成使用 fake 的 state test（24.9 的修復路線），而不是更新劇本。

**Agent 偏好「有 seam 的地方」。** 程式沒有 seam 時，agent 常用 `mock.patch` 硬換模組路徑上的依賴，因為這不需要修改 production 程式碼。這正是 24.3 說的過渡手段被當成常態。比較好的指令是請 agent 提出 dependency injection 的重構，讓人決定 seam 畫在哪裡。

對策不是禁止 agent 使用 mock，而是把團隊的選擇順序變成 agent 的指令與檢查。在 Harbor，給 coding agent 的 repository 說明文件裡寫明：「優先使用真實實作；外部服務一律使用 `harbor.testing` 提供的 fake；只有在驗證 state-changing 呼叫時才使用 mock，且必須用 `create_autospec`。」CI 中則有一個簡單的靜態檢查：新增的測試若對 `PaymentGateway`、`InventoryClient` 等已有 fake 的介面使用 `Mock()`，就在 code review 中提出警告。

**AI 讓 fake 與 contract test 變得更便宜。** 過去 fake 最大的障礙是撰寫成本。現在可以請 agent 根據介面定義、API 文件與既有的 adapter 程式碼草擬 fake 與 contract test，再讓 contract test 在 sandbox 上跑，用結果檢驗 fake 是否正確。這裡的順序很重要：contract test 的每一條行為由 owner 審查確認，因為它定義的是「真實世界的語意」，而 agent 只能從文件與程式碼推測這個語意。

**AI agent 本身也需要 test double。** Harbor 的 AI 客服 agent 會呼叫「查詢訂單」「送出退款申請」等工具（tool）。測試 agent 的行為時，不能讓它真的送出申請，所以這些工具需要 fake：一個有假訂單資料、會記錄退款申請、能注入「訂單不存在」「退款服務逾時」等錯誤的工具環境。Agent 的 eval 也常在這種 fake 環境中進行。這裡同樣適用 state testing 的原則：檢查「agent 最後對這筆訂單做了什麼」（例如退款總額沒有超過訂單金額、沒有對不符資格的訂單退款），比檢查「agent 呼叫工具的順序」更穩定，也更貼近真正的風險。Agent eval 的設計在第 25 章（25.12 節）詳談，第 48 章的 capstone 會把它用在 AI 退款助理上。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 把既有的 mock-heavy 測試分類：哪些 mock 其實是 stub、哪些驗證了 non-state-changing 呼叫、哪些可以改用 fake | 哪些呼叫是需要驗證的行為（例如「只能退款一次」），由服務 owner 決定 |
| 根據介面與 API 文件草擬 fake 與 contract test，並在 sandbox 上執行驗證 | Contract test 的每一條行為由 owner 審查；fake 必須有 owner 與文件記載的已知差異 |
| 找出程式中寫死的時間、隨機、環境變數與外部呼叫，提出 dependency injection 的重構 | 決定 seam 畫在哪裡；不為每個 library 呼叫建立介面 |
| 為 fake 產生故障注入情境：逾時、回應遺失、部分成功、格式錯誤 | Agent 不得因為測試難以使用真實依賴就刪除 larger test 或 contract test |
| 為 AI 客服 agent 的工具建立 fake 環境並撰寫 eval 情境 | Fake 工具環境不得連到真實的退款或付款系統；eval 的通過標準（例如不可超額退款）由產品與風控決定 |

> [!ai] AI 提醒
> Review AI 產生的測試時，先搜尋 `Mock(` 與 `patch(`，對每一個問：「這個依賴有 fake 嗎？這個 mock 驗證的是結果，還是步驟？如果真實依賴的行為和這個 mock 設定的不一樣，哪一個測試會告訴我們？」三個問題答不出來的 mock，就是下一次事故的候選。

## 24.14 專家怎麼想

- **「如果這個替身說謊，誰會發現？多久會發現？」** 每個 test double 都是用保真度換速度。專家不問「能不能 mock」，而是問替身與真實行為不一致時，哪一層測試會抓到：contract test 每晚會抓到，還是要等到 production 的對帳？答不出來，就代表這個替身沒有安全網。
- **Fake 是產品，不是測試的附屬品。** 被很多團隊使用的 fake 需要 owner、版本、文件與自己的測試。資深工程師會把「提供一個好的 fake」當成發布一個 library 時的必要交付，就像提供 API 文件一樣。
- **先問「真的不能用真的嗎？」** 很多 mock 是反射性的：看到另一個類別就 mock。專家會先確認依賴是否真的慢、不穩定或有副作用；純計算、同一個 process 內的協作者，直接使用真實實作通常最好。
- **Mock 的 setup 越長，越要懷疑設計。** 一個測試需要 mock 五個協作者，常代表 SUT 承擔了太多責任，或者它往依賴的內部伸手太深。測試的痛苦是設計的回饋，不是要靠更強的 mocking 框架解決的問題。
- **把「部分成功」放進 fake。** 分散式系統中最難的 bug，常發生在「對方處理成功、我方以為失敗」這類情況。專家設計 fake 時一定會提供這類故障注入，因為用真實依賴幾乎無法穩定重現它們。

## 24.15 動手練習

1. 執行 24.11 的程式，然後在 `MockStyleTest` 中加入一個 assertion，檢查兩次呼叫使用的 `idempotency_key` 相同（提示：`gateway.refund.call_args_list`）。這個 mock 測試現在能抓到 bug 了嗎？比較它和 fake 風格測試的可讀性與脆弱程度。
2. 替 `GatewayContract` 新增一條行為：「退款金額必須大於 0」。先寫 contract test，讓它在 `HttpGatewayContract` 與 `FakeGatewayContract` 上都失敗，再修改 `SandboxProvider` 與 `FakePaymentGateway` 讓兩者都通過。
3. 為 `FakePaymentGateway` 加入一個新的故障注入：「請求在送達金流商前就逾時」（退款沒有發生）。寫一個測試確認 `RefundService` 在這種情況下重試後只退款一次。
4. 從你手上的專案找一個 mock-heavy 的測試，用 24.9 的症狀表診斷它，並依 24.5 的決策圖判斷每個 mock 應該換成真實實作、fake、stub 還是保留。
5. 找一段直接呼叫 `datetime.now()` 或 `random` 的程式，把它改成注入 `Clock` 或隨機產生器，並寫一個測試精確驗證「剛好到期」與「差一秒到期」兩種邊界。
6. 請 AI coding agent 替一個有外部依賴的類別產生 unit test，然後統計其中 `Mock()` 的數量、驗證 non-state-changing 呼叫的數量，並嘗試把它們改寫成使用 fake。記錄改寫前後在一次小型重構中需要修改的測試數。

## 本章重點整理

- Test double 用保真度換取速度、穩定性與可控制性；選擇替身就是在決定願意放棄多少真實性。
- 要能使用替身，程式必須有 seam；dependency injection（尤其是建構子注入）是最清楚的做法，時間、隨機與環境也應該被注入。
- Monkey patching 適合處理沒有 seam 的舊程式碼，但它依賴模組路徑等實作細節，長期應改為顯式注入。
- 五種替身各有角色：dummy 填參數、stub 給固定回應、spy 記錄呼叫、mock 驗證期望、fake 是有真實語意的簡化實作。
- Mocking framework 是工具，用它設定回傳值是 stubbing，用它驗證呼叫才是 interaction testing。
- 選擇順序是 real → fake → stub／mock；能用真實實作時，依執行時間、determinism 與建立成本判斷。
- Fake 有狀態與語意，能讓測試用 state testing 檢查結果；它應由擁有真實實作的團隊維護，並對 API 合約忠實。
- 好的 fake 提供故障注入，讓「回應遺失」「部分成功」這類難以重現的情況可以被穩定測試。
- 過度 stubbing 會讓測試難懂、脆弱且效果差；在 stub 裡寫業務規則，就是在寫一個未經驗證的 fake。
- 偏好 state testing；interaction testing 只在無法觀察狀態，或呼叫次數與順序本身就是需求時使用，且只針對 state-changing 呼叫、避免過度規定。
- 不要 mock 你不擁有的型別：在第三方 SDK 前放一層自己的 adapter，業務程式依賴 adapter 的介面。
- Contract test 讓 fake 與真實實作跑同一套行為測試，是防止 fake 漂移的主要機制；真實那一側可以較低頻率執行。
- AI coding agent 傾向產生 mock-heavy 的測試；要把選擇順序寫進 agent 的指令與 CI 檢查，並用 fake 與 contract test 取代劇本式的 mock。

## 延伸問答

> [!question]- Q1. Stub、mock、fake 最核心的差別是什麼？用一句話各自說明它們適合回答的問題。
> Stub 回答「依賴回傳這個值時，被測程式會怎麼反應」，它只提供預先寫好的回應，沒有自己的狀態與規則。Mock 回答「被測程式有沒有用約定的方式呼叫依賴」，它的重點在事後驗證呼叫的方法、次數與參數。Fake 回答「在接近真實語意的依賴下，被測程式的最終結果是否正確」，它是一個能運作的簡化實作，會記住狀態並套用規則。
>
> 選擇時要先問測試要觀察什麼。如果要觀察的是結果，fake 通常最好；如果只需要把程式帶進某個分支，stub 就夠了；如果呼叫本身就是要保護的行為，例如付款只能送出一次，才需要 mock 或 spy。三者經常可以用同一個 mocking framework 實作，所以要看的是用途，而不是使用了哪個類別。

> [!question]- Q2. 原書說「prefer realism over isolation」。但 unit test 不就是要隔離嗎？這兩者怎麼不矛盾？
> Unit test 需要的隔離是「讓測試快、穩定、沒有副作用、失敗時容易定位」，而不是「被測類別之外的所有程式碼都必須被替換」。一個純計算、同一個 process 內、行為 deterministic 的協作者，使用真實實作並不會讓測試變慢或變得不穩定，因此不需要隔離它。反過來，把它換成 mock，只會讓測試和實作綁得更緊，並且失去「兩個元件真的能一起運作」的證據。
>
> 所以兩者的關係是：隔離是為了解決慢、不穩定、副作用這些具體問題的手段，不是目標本身。只在依賴造成這些問題時才替換它，並且在替換時選擇最接近真實的替身。原書所說的偏好真實，就是提醒我們不要為了隔離而隔離。

> [!question]- Q3. 你是 payments 團隊的成員，有三個團隊在測試中各自 mock 了你們的 PaymentGateway，而且每個團隊 mock 的行為都略有不同。你會怎麼處理？
> 這代表三個團隊各自寫了一份對 PaymentGateway 行為的猜測，而且至少有兩份是錯的。我會由 payments 團隊提供一個正式的 FakePaymentGateway，和真實 adapter 放在同一個套件中發布，並寫一套 contract test，讓 fake 與連到金流商 sandbox 的真實 adapter 都跑同一套行為，例如超額退款會被拒絕、同一把 idempotency key 只退一次。
>
> 接著是遷移：通知三個團隊改用 fake，先從最重要的退款流程開始，並在文件中列出 fake 的已知差異。可以加一個靜態檢查或 code review 規則，在新的測試對 PaymentGateway 使用 Mock 時提出提醒。這樣做的效果是把「金流商的語意」集中在一個有 owner、有驗證的地方，而不是散落在幾十個測試的 mock 設定裡。

> [!question]- Q4. 什麼情況下 interaction testing 是正確的選擇？請舉一個 Harbor 的例子。
> 第一種情況是無法做 state testing：依賴沒有真實實作可用，也沒有 fake，無法查詢它的狀態。例如 Harbor 串接的某家簡訊服務只提供「送出」的 API，沒有任何查詢或 sandbox，測試只能驗證通知服務有沒有用正確的手機號碼與內容呼叫它。這時 interaction testing 是退而求其次的做法，也可以考慮由通知團隊建立一個會記錄已送出簡訊的 fake。
>
> 第二種情況是呼叫的次數或順序本身就是需求。例如 Harbor 的商品快取的目的就是「短時間內同一商品只查一次 inventory」，驗證後端只被呼叫一次就是在驗證快取的行為；合規要求「退款前必須先寫入審計紀錄」，順序就是需求。即使在這些情況，也只驗證和需求有關的呼叫與參數，避免連帶規定 log 內容或不相關的查詢。

> [!question]- Q5. 團隊的 fake 和真實實作的 contract test 平常都通過，某天晚上 sandbox 那一側失敗了，fake 那一側仍然通過。這代表什麼？該怎麼處理？
> 這代表 fake 與真實世界之間出現了差異，可能有三種原因：金流商改變了行為（例如新增了一條驗證規則）；sandbox 環境本身暫時有問題；或 adapter 的程式碼有變更導致它和 fake 不一致。第一步是區分這三者：重跑一次排除 sandbox 的暫時性問題，查看金流商的變更公告，並檢查最近 adapter 的變更紀錄。
>
> 如果確認是真實行為改變，處理順序是先更新 contract test 描述新的行為，再修改 fake 與 adapter 讓兩邊都通過，並通知使用 fake 的團隊。這段期間，使用 fake 的測試可能在錯誤的假設下通過，所以修正要優先處理。這也是 contract test 真實那一側要定期執行的原因：越早發現漂移，被錯誤 fake 誤導的測試越少。

> [!question]- Q6. 為什麼時間（clock）是最值得注入的依賴之一？直接在測試中 patch datetime.now 不行嗎？
> 時間幾乎影響所有業務規則：優惠券是否過期、訂單是否超過退款期限、快取是否失效、session 是否到期。如果程式直接呼叫系統時間，測試就無法穩定驗證「剛好到期」這種邊界，只能用 sleep 等待或接受依日期而變的結果，造成慢又 flaky 的測試。注入一個 Clock 介面，測試就能用 fake clock 精確設定與前進時間，一行程式就能跳過七天。
>
> 直接 patch datetime.now 在小範圍內可行，但有幾個問題：patch 必須作用在被使用的模組路徑上，import 方式一改就失效；全域 patch 可能影響同一 process 中的其他程式碼與測試框架本身；而且它把「這段程式依賴時間」這件事藏了起來。顯式注入讓依賴在介面上一目了然，也讓 production 可以在需要時統一控制時間來源，例如在 replay 或模擬時使用。

> [!question]- Q7. 你請 AI coding agent 為 RefundService 補測試，它產生的測試把 gateway、logger、metrics、clock 全部用 Mock() 替換，並驗證了每一個呼叫。你會怎麼 review？
> 我會依照選擇順序逐一檢查每個 mock。Gateway 已經有 payments 團隊提供的 fake，應該改用 fake，並以最終的已退金額做 state testing，而不是驗證呼叫次數；clock 應該使用 fake clock，以便精確控制時間；logger 與 metrics 通常不是被測行為的一部分，可以使用真實的 in-memory 實作或 dummy，不需要驗證它們被如何呼叫，除非某個 metric 本身是需求。
>
> 接著檢查 interaction 的部分：每個被驗證的呼叫，是 state-changing 且和需求有關的嗎？像是驗證 log 訊息內容或查詢方法被呼叫，都是會讓下次重構失敗的過度規定。最後我會要求補一個故障注入的情境，例如回應遺失後重試，並確認重試不會重複退款，因為這是退款服務最重要的風險，而全 mock 的測試正好最難表達它。

> [!question]- Q8. 面試題：請說明你會如何為一個依賴外部金流商的退款服務設計測試組合，包括各層使用什麼樣的 test double。
> 我會分三層。最底層是大量的 unit test：RefundService 透過自己的 PaymentGateway 介面依賴金流商，unit test 使用由 payments 團隊維護的 in-memory fake，以 state testing 驗證退款金額、超額拒絕、重試時 idempotency key 不變等行為，並用 fake 的故障注入覆蓋逾時與回應遺失；時間與 ID 產生器也透過注入使用 fake。少數只需要把程式帶進錯誤分支的情況可以用 stub。
>
> 中間層是 contract test：同一套描述 gateway 行為的測試，同時跑在 fake 與連到金流商 sandbox 的真實 adapter 上，fake 那一側在每次 presubmit 執行，sandbox 那一側每晚或 adapter 變更時執行，用來偵測 fake 漂移與金流商行為改變。最上層是少量的 larger test 與 production 端的保護：端對端的退款流程測試、上線時的 canary，以及每日與金流商的對帳。對帳不是測試，但它是最後一道能發現「所有替身都說謊」的防線，Harbor 的事故正是靠它發現的。

## 延伸閱讀

- [Software Engineering at Google — Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)：本章對應的原書章節，包含 faking、stubbing、interaction testing 的完整論述，以及 fake 的 fidelity 與 contract test。
- [Software Engineering at Google — Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)：第 23 章的對應章節，說明為什麼偏好 state testing 與透過 public API 測試。
- [Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)：當 test double 不夠時，如何用更大範圍的測試驗證真實依賴，接續到第 25 章。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：審查 AI 產生的程式碼與測試時可以參考的檢查方向。
