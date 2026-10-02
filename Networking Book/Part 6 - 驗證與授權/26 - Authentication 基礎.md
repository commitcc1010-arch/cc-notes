---
chapter: 26
title: Authentication 基礎：密碼、Session 與 MFA
part: 6
---

# 第 26 章　Authentication 基礎：密碼、Session 與 MFA

> [!abstract] 本章地圖
> **核心問題**：使用者輸入帳號密碼以後，server 要怎麼確認「你就是你」、把這個結論安全地記住，並在密碼外洩、有人大量猜測時依然守得住？
>
> **你會學到**：
> - 分清楚 authentication 與 authorization，正確使用 401 與 403
> - 用 salt 加上 memory-hard 的 scrypt 儲存密碼，設計可以不停機升級的雜湊格式，並用 constant-time 比較驗證
> - 設計 server-side session：session ID 怎麼產生、cookie 屬性怎麼設、登入後為什麼要輪替、登出與閒置／絕對逾時怎麼落實
> - 用 token bucket 依帳號、IP 與兩者組合做登入限速，分辨暴力破解、撞庫與 password spraying 的防法
> - 從 HMAC 開始實作 RFC 4226 HOTP 與 RFC 6238 TOTP，用 RFC 的測試向量驗證，並處理時鐘誤差與重放
> - 設計安全的忘記密碼流程，知道 passkeys 為什麼是下一步（第 29 章）
>
> **前置知識**：第 17 章（hash、HMAC、隨機數）、第 18 章（TLS 保護傳輸中的密碼）、第 21 章（cookie 語法與屬性）、第 23 章（SameSite 與 CSRF）

## 26.1 故事：週五晚上的撞庫

週五晚上九點七分，聲聲 Live 的登入服務 `auth.shengsheng.example` 觸發告警：`POST /login` 從平常每分鐘約 250 次，衝到每分鐘 9,000 次，失敗率 99.9%。小晴打開 log，看到的不是有人對同一個帳號猛猜密碼，而是成千上萬個不同的 email，每個只試一到兩次，來源 IP 在十分鐘內就超過 2,700 個。四個小時後攻擊停止，總共約 21 萬次嘗試，其中 186 次登入成功。隔天早上，有學生在社群上貼出「我的帳號被人登入，上課紀錄和個人資料都被看光了」。

資安工程師 Rita 判斷這是**撞庫**（credential stuffing）：攻擊者拿別的網站外洩的「email 與密碼」清單，到其他網站逐一嘗試，賭的是很多人在不同網站用同一組密碼。聲聲 Live 的資料庫並沒有外洩，那 186 個帳號的密碼也不是被「猜」出來的，而是使用者在別處早已外洩的密碼。小晴不解：「密碼是對的，系統照規則讓他們登入，這樣也算我們的問題嗎？」

阿德的回答是：authentication（身分驗證）從來不只是「比對密碼」。Rita 隔週對整個登入系統做了審查，列出五個問題，每一個都讓這次事故更嚴重，或者讓下一次事故更危險：

| Rita 的發現 | 風險 | 本章哪一節修 |
|---|---|---|
| 2019 年以前註冊的帳號，密碼存的是沒有 salt 的 SHA-256；之後的帳號用 scrypt，但參數是多年前定的 | 一旦資料庫外洩，舊帳號的密碼能在很短時間內大量還原 | 26.3、26.10 實驗一 |
| 登入 API 沒有任何限速 | 撞庫與暴力破解可以全速進行 | 26.7、26.10 實驗三 |
| 登入成功後沿用登入前的 session ID | session fixation：登入前就被植入的 ID，登入後就變成有效身分 | 26.6、26.10 實驗二 |
| 登出只叫瀏覽器刪 cookie，server 端的 session 永不過期 | 被複製走的 cookie 永遠有效 | 26.6 |
| 只有密碼，沒有 MFA；忘記密碼的 token 明文存在資料庫、沒有期限 | 密碼一洩漏就等於帳號被接管 | 26.8、26.9 |

```text
 外洩清單（別的網站）          聲聲 Live 的登入系統
 ┌──────────────────┐     ┌──────────────────────────────────────────────────┐
 │ email : password │     │ ① 沒有限速 ──► 21 萬次嘗試全部被處理               │
 │ 數十萬筆         │────►│ ② 只有密碼 ──► 密碼對了就等於本人（186 個帳號）   │
 └──────────────────┘     │ ③ session 不過期 ──► 攻擊者拿到的 cookie 長期有效 │
                          │ ④ 無 salt 的舊雜湊 ──► 若資料庫外洩，損害會放大   │
                          │ ⑤ 監控只看 5xx ──► 401 暴增沒有人收到告警         │
                          └──────────────────────────────────────────────────┘
```

這張圖從左往右讀。外洩清單是攻擊的燃料，聲聲 Live 控制不了；但右邊每一道防線都是自己可以補的。① 讓攻擊的速度不受限制；② 讓「知道密碼」直接等於「接管帳號」；③ 讓接管之後的存取時間沒有上限；④ 這次沒有發生，但它決定了下一次如果資料庫外洩，損害會有多大；⑤ 讓團隊晚了將近一小時才知道。這一章依序把這幾道防線補起來：先講清楚 authentication 和 authorization 的分工，再講密碼怎麼存、session 怎麼管、登入怎麼限速、MFA 怎麼做，最後是忘記密碼。章末的動手做會在 127.0.0.1 上把整套機制寫一次。

## 26.2 Authentication 與 Authorization：先問「你是誰」，再問「你能做什麼」

**Authentication**（身分驗證，常縮寫成 AuthN）回答「你是誰」：使用者出示某種證據，server 確認證據有效，得出「這個請求來自 student23」的結論。**Authorization**（授權，AuthZ）回答「你能做什麼」：已經知道是 student23 了，這個人可不可以看這堂課的錄影、可不可以改老師的時薪。兩者經常被混在一起講，但它們在程式裡是兩個不同的步驟，失敗時也該回不同的錯誤。例如學生登入後想打開別的學生的上課紀錄：身分驗證成功了（確實是 student23），授權失敗了（student23 沒有權限看別人的紀錄）。

證據的種類傳統上分成三類，稱為驗證**因子**（factor）：你知道的東西（密碼、PIN）、你擁有的東西（手機上的 authenticator app、硬體金鑰）、你本身的特徵（指紋、臉）。**MFA**（multi-factor authentication，多因子驗證）要求至少兩個不同類別的因子；「密碼加上安全提問」仍然是兩個「你知道的東西」，不算 MFA。這個分類的意義在於：不同類別的因子要被不同方式攻破，攻擊者拿到外洩的密碼清單，並不會順便拿到你的手機。

在一個 Web 應用裡，一個請求通過的順序是這樣：

```text
 請求 ──► ① 解析憑證 ──► ② 驗證身分（AuthN）──► ③ 載入身分與權限 ──► ④ 授權判斷（AuthZ）──► 業務邏輯
          cookie /        session 存在？          user=student23        能看 lesson 8812 嗎？
          Authorization    沒過期？簽章對？        role=student
          header
            │                    │                                          │
            │ 沒有憑證            │ 憑證無效／過期                            │ 身分有效但不允許
            ▼                    ▼                                          ▼
          401 Unauthorized ◄─────┘                                     403 Forbidden
         （請先證明你是誰）                                            （知道你是誰，但不行）
```

① 從請求中找出憑證：瀏覽器應用通常是 session cookie，API 常見的是 `Authorization: Bearer …` header（第 27 章）。② 驗證憑證：session 存不存在、過期沒有。③ 由憑證得出身分，再從資料庫載入角色與權限。④ 拿身分與要存取的資源做授權判斷。圖下方的兩個出口是兩種不同的失敗：沒有或無效的憑證是 401，有效身分但不被允許是 403。

| 情況 | 狀態碼 | 意思 | 例子 |
|---|---|---|---|
| 沒帶憑證，或憑證無效、過期 | 401 Unauthorized | 「我不知道你是誰，請先驗證」 | 未登入打 `/me`、session 逾時 |
| 身分有效，但沒有權限 | 403 Forbidden | 「我知道你是誰，但你不能做這件事」 | 學生打 `/admin/payouts` |
| 不想透露資源是否存在 | 404 Not Found | 對沒權限的人假裝資源不存在 | 打別人私人課程的網址 |
| 嘗試太多次 | 429 Too Many Requests | 「慢一點」，搭配 `Retry-After` | 登入限速觸發（26.7 節） |

名稱有點誤導：401 的英文是 Unauthorized，實際上指的是「未驗證」。HTTP 規格（RFC 9110）要求 401 回應附上 `WWW-Authenticate` header 說明驗證方式，這對 HTTP Basic 或 Bearer token 很自然；用 cookie 登入的網頁應用，實務上很多只回 401 加 JSON 錯誤訊息，前端看到 401 就導向登入頁。常見的錯誤是把兩者顛倒：權限不足回 401，前端就會把一個已登入的使用者踢回登入頁，使用者重新登入後還是 401，陷入迴圈。

最後一個觀念是：**authentication 是一次事件，session 是這個事件的記憶**。使用者只在登入時出示密碼；之後的每一個請求，server 靠的是登入時發下去的 session ID 或 token。所以整個系統的安全性取決於兩段：登入那一刻的驗證夠不夠強（26.3–26.4、26.7–26.8 節），以及那份記憶會不會被偷、被偽造、過期了有沒有真的作廢（26.5–26.6 節）。

## 26.3 密碼怎麼存：salt、慢雜湊與 memory-hard

server 需要驗證密碼，卻不應該知道密碼。做法是只存一個由密碼算出來、無法反推的值，登入時用同樣的方法再算一次比對。這個「無法反推」要對抗的不是線上的攻擊者，而是**資料庫外洩以後**的離線攻擊：攻擊者拿到整張表，可以在自己的機器上無限次嘗試，不受任何限速。密碼儲存設計的唯一目標，就是讓這種離線嘗試變得極度昂貴。

### 為什麼不能用 SHA-256

第 17 章介紹的 SHA-256 是密碼學 hash：單向、抗碰撞。但它被設計成**快**，一般 CPU 一秒可以算數百萬次，GPU 更快好幾個數量級。人類選的密碼空間很小：常見密碼字典、加上「單字＋年份」「首字大寫＋驚嘆號」之類的變形規則，總共也就幾十億到幾兆個候選。對一個快速 hash 來說，把這些候選全部算一遍是很實際的事，所以「用 SHA-256 存密碼」幾乎等於只是把明文換了一種寫法。

問題還不只在快。Rita 的審查發現，在沒有 salt 的舊表裡，用同一個密碼的帳號會有完全相同的雜湊值。攻擊者只要算一次 `sha256("sunflower88")`，就能一次找出所有用這個密碼的人；更糟的是可以事先把常見密碼的雜湊全部算好存起來（這類預先計算的表，常見的形式叫 **rainbow table**），拿到資料庫後直接查表。

### Salt 與 pepper

**Salt** 是每個帳號各自產生的一段隨機 bytes（例如 16 bytes），和密碼一起送進雜湊函式，並且**明文存在雜湊旁邊**。例如 student23 的 salt 是 `kO/N2hBgDJ…`，存的是 `scrypt(密碼, salt)`；student77 即使用同一個密碼，salt 不同，結果也完全不同。salt 不需要保密，它的作用是讓攻擊者無法「算一次、套用到所有人」，也讓預先算好的表失效：每個帳號都必須從頭獨立攻擊。

**Pepper** 是另一個常被提到的概念：一把全站共用、**不存在資料庫裡**的秘密，例如放在 secrets manager，用 HMAC 先把密碼和 pepper 混合再雜湊。它的價值在於「只偷到資料庫、沒偷到應用程式設定」的情況下，攻擊者連嘗試都做不了。代價是 pepper 的輪替很麻煩（換了 pepper，舊雜湊就無法驗證，必須保留舊 pepper 直到使用者登入升級）。pepper 是加分項，不能取代 salt 與慢雜湊。

### PBKDF2、bcrypt、scrypt 與 Argon2id

salt 解決了「一次算給所有人」，但對單一帳號的攻擊仍然取決於每次嘗試的成本。專為密碼設計的函式，核心思想都是**刻意變慢**，而且慢的程度可以用參數調整；後來的設計更進一步讓它**吃記憶體**。

```text
 scrypt 的核心（ROMix，簡化）：先填滿一張大表，再隨機讀它

 階段一：依序產生 N 個區塊，全部存起來（每塊 128 × r bytes）
   X ──►[V0]──►[V1]──►[V2]──► … ──►[V(N-1)]       N=2^17、r=8 → 128 MiB
          │      │      │               │
 階段二：重複 N 次，每次依「目前的 X」決定讀哪一塊，混進 X
   X ──► 讀 V[j1] ──► 讀 V[j5] ──► 讀 V[j2] ──► … ──► 輸出
          ▲ j 取決於上一步的結果，無法事先知道要哪一塊

 想省記憶體？只存一部分 V，缺的現場重算 → 時間暴增。記憶體與時間只能二選一。
```

這張圖說明 **memory-hard**（記憶體困難）的意思。階段一產生 N 個區塊並全部存起來；階段二每一步要讀哪一塊，取決於上一步的結果，所以無法預測、也無法跳過。攻擊者若想在 GPU 或專用晶片上同時跑幾千個嘗試，每個嘗試都需要 128 MiB 的記憶體；記憶體不夠，就得把缺的區塊即時重算，時間成本暴增。GPU 擅長的是大量平行的計算，而不是給每個執行緒一大塊獨立的記憶體，memory-hard 正是瞄準這個弱點。

| 演算法 | 年代 | 可調參數 | 是否 memory-hard | 要注意的地方 |
|---|---|---|---|---|
| PBKDF2-HMAC-SHA256 | 2000（PKCS #5） | 迭代次數 | 否 | GPU 友善，需要很高的迭代次數；FIPS 環境常被要求使用 |
| bcrypt | 1999 | cost（2 的次方） | 少量（約 4 KiB） | 只取密碼前 72 bytes，超過的部分被忽略 |
| scrypt | 2009（RFC 7914） | N、r、p | 是，約 128 × N × r bytes | 參數之間有關聯，記憶體上限要一起設 |
| Argon2id | 2015 密碼雜湊競賽勝出（RFC 9106） | 記憶體 m、迭代 t、平行度 p | 是 | 新系統的首選；Python 標準函式庫沒有，需第三方套件 |

表格的最後一欄是實務中最常踩的坑。bcrypt 的 72 bytes 限制意味著兩個前 72 bytes 相同的長密碼會被當成同一個；有些系統為了繞過限制，先把密碼 SHA-256 再交給 bcrypt，但若把 raw bytes 直接交出去，遇到 `\x00` 還可能被截斷，所以一般建議用 base64 後的 digest。scrypt 的 N 每增加一倍，時間與記憶體也各增加一倍。本書程式只能用標準函式庫，所以用 `hashlib.scrypt` 示範；如果是全新的系統而且可以裝套件，Argon2id 是多數指引的首選。

> [!note] 2026 現況：參數建議（截至 2026 年 10 月）
> 常被引用的 OWASP Password Storage Cheat Sheet 建議值為：Argon2id 記憶體 19 MiB、迭代 2、平行度 1；scrypt N=2^17、r=8、p=1；bcrypt cost 至少 10；PBKDF2-HMAC-SHA256 約 600,000 次迭代。這些數字會隨硬體進步定期上調，正式上線前請再查一次當下的版本，並在自己的機器上量時間：登入一次的雜湊時間大約落在幾十到幾百毫秒，是常見的取捨區間。

### 儲存格式與升級策略

參數一定會隨時間調高，演算法也可能更換，所以存下來的雜湊必須**自我描述**：從字串本身就能看出用了什麼演算法、什麼參數。常見的寫法仿照 PHC string format：

```text
 $scrypt$ln=17,r=8,p=1$kO/N2hBgDJ5kQ3k0qkQ9Xg$Hc2u0e…（43 個 base64 字元）
 └──┬──┘└─────┬──────┘└──────────┬──────────┘└──────────┬──────────┘
  演算法      參數          salt（16 bytes）         雜湊結果（32 bytes）
            ln = log2(N)    base64、去掉 =            base64、去掉 =
```

四個欄位用 `$` 分隔。演算法名稱讓驗證程式知道該走哪一條路；參數欄讓舊雜湊在參數調高之後仍能正確驗證；salt 和雜湊結果用 base64 編碼成可以放進一般文字欄位的字串。有了這個格式，同一張表裡可以同時存在三種世代的雜湊，驗證程式依前綴分流即可。

升級的關鍵限制是：**server 只有在使用者登入的那一刻才拿得到明文密碼**。所以策略分成兩步：

```text
 遺留：sha256$5e88…（無 salt）
   │
   │ ① 離線批次：不需要明文，把舊雜湊當成輸入再做一次 scrypt
   ▼
 包裝：$scrypt-sha256$ln=17,r=8,p=1$salt$hash      驗證時：scrypt(sha256(密碼))
   │
   │ ② 使用者下次登入成功、手上有明文的那一刻
   ▼
 標準：$scrypt$ln=17,r=8,p=1$salt$hash             驗證時：scrypt(密碼)

 參數過時（例如 ln=14）的標準雜湊，同樣在登入成功時直接走 ②
```

① 是最重要的一步，因為很多帳號可能好幾年都不會登入。離線把每個 `sha256(密碼)` 當成「密碼」再做一次 scrypt，整張表立刻不再有快速雜湊，也不再有「相同密碼、相同雜湊」的問題；驗證時先算 SHA-256 再算 scrypt 即可。② 則在使用者登入時，把包裝格式或參數過時的雜湊換成目前的標準格式。這種「洋蔥式」包裝的安全性取決於最外層的 scrypt，裡面那層 SHA-256 只是多一步計算。完整程式在 26.10 節的實驗一。

### Constant-time 比較：別讓比較本身洩漏資訊

算出候選雜湊以後，要和資料庫裡的值比較。直覺的寫法是 `candidate == stored`，但 `==` 的實作通常是「遇到第一個不同的 byte 就回傳」，比較時間會隨著「前面有幾個 byte 相同」而變長。這種差異叫 **timing side channel**（計時旁通道）：攻擊者若能精確測量回應時間，就有機會逐個 byte 逼近正確值。對密碼雜湊來說，因為攻擊者無法控制雜湊輸出，實際可利用性很低；但同樣的比較也出現在 HMAC 簽章、API key、重設 token、TOTP 驗證，這些地方攻擊者可以直接控制輸入，就是真實的風險。下面的程式不量時間（時間雜訊太大），而是直接數「比了幾個 byte」，讓洩漏變得看得見：

```python
import hmac


def naive_equal(a: bytes, b: bytes) -> tuple[bool, int]:
    """和 == 一樣：遇到第一個不同的 byte 就回傳。多回傳「比了幾個 byte」來看出洩漏。"""
    if len(a) != len(b):
        return False, 0
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return False, i + 1
    return True, len(a)


def constant_time_equal(a: bytes, b: bytes) -> tuple[bool, int]:
    """把每個 byte 的差異 OR 起來，不論在哪裡不同，都比完全部。"""
    if len(a) != len(b):
        return False, 0
    diff = 0
    for x, y in zip(a, b):
        diff |= x ^ y
    return diff == 0, len(a)


secret = bytes.fromhex("9f3a6c01d2e4b7a85566778899aabbcc")   # 例如 server 端算出的 MAC
guesses = {
    "第 1 個 byte 就錯": bytes.fromhex("00" * 16),
    "前 4 個 byte 對  ": bytes.fromhex("9f3a6c01" + "00" * 12),
    "前 15 個 byte 對 ": secret[:15] + b"\x00",
}
for label, guess in guesses.items():
    _, n1 = naive_equal(secret, guess)
    _, n2 = constant_time_equal(secret, guess)
    print(f"{label}  naive 比了 {n1:>2} bytes   constant-time 比了 {n2} bytes")
    assert hmac.compare_digest(secret, guess) is False
assert hmac.compare_digest(secret, bytes(secret))
```

```text
第 1 個 byte 就錯  naive 比了  1 bytes   constant-time 比了 16 bytes
前 4 個 byte 對    naive 比了  5 bytes   constant-time 比了 16 bytes
前 15 個 byte 對   naive 比了 16 bytes   constant-time 比了 16 bytes
```

`naive_equal` 和 `==` 一樣提早結束，比較的長度直接反映出「猜對了幾個 byte」，這就是攻擊者想量的訊號。`constant_time_equal` 不論哪裡不同都比完 16 個 byte，執行路徑與輸入無關。實務上不要自己寫，直接用標準函式庫的 `hmac.compare_digest`，它就是為這個目的實作的；兩個參數要同型別（都是 bytes 或都是 ASCII str）。同樣的道理延伸到整個登入流程：帳號不存在時，如果 server 直接回傳而不做雜湊，回應時間就會比「帳號存在但密碼錯」快上幾百毫秒，等於告訴外人哪些 email 有註冊。正確做法是帳號不存在時也拿一組假的 salt 跑一次雜湊，26.10 節的實驗二就是這樣寫的。

## 26.4 密碼政策：長度、外洩清單，以及不要做的事

雜湊保護的是「資料庫外洩之後」，密碼政策則決定使用者選的密碼本身有多難猜。過去流行的規則是「至少 8 碼、要有大小寫、數字、符號、每 90 天換一次」，研究和實務都發現這些規則的效果很差：使用者會選 `Password1!`，每 90 天改成 `Password2!`，或者寫在便利貼上。現在主流的指引反過來，重點放在長度、檢查外洩清單，以及別讓使用者的密碼管理工具難用。

具體做法有幾項。第一，**長度優先**：設定足夠的最小長度，並允許很長的密碼（至少 64 個字元），讓使用者可以用一句話當密碼；為了避免有人送幾 MB 的「密碼」拖慢雜湊，可以設一個寬鬆的上限，例如 256 個字元。第二，**檢查外洩與常見密碼清單**：註冊與改密碼時，拒絕出現在已知外洩資料或常見密碼清單裡的密碼，並告訴使用者原因。查詢外部服務時要用 k-anonymity 的方式（只送出密碼 SHA-1 的前 5 個十六進位字元，在本機比對回傳的候選清單），不要把完整雜湊送出去。第三，**不要強迫定期更換**，只在有外洩跡象時要求更換。第四，**允許貼上與密碼管理工具**，登入欄位加上 `autocomplete="current-password"`，註冊欄位用 `new-password`，讓瀏覽器與密碼管理工具能正確運作。第五，**正規化 Unicode**：同一個字在不同輸入法可能產生不同的碼位，雜湊前先做 NFKC 正規化，避免使用者「明明輸入一樣卻登不進去」。

第二項對撞庫特別有用。聲聲 Live 那 186 個被登入的帳號，密碼全都出現在公開的外洩資料裡；如果在註冊或登入時檢查到這件事，就能提示使用者更換，或者要求額外驗證。這也說明了為什麼光靠密碼政策不夠：使用者在別的網站重複使用密碼，這件事 server 無法阻止，只能偵測與補強，所以後面要講限速與 MFA。

> [!note] 2026 現況：NIST 的數位身分指引（截至 2026 年 10 月）
> 美國 NIST SP 800-63B 第 4 版（2025 年定稿）是很多公司制定密碼政策時參考的文件。重點包括：密碼是唯一因子時最少 15 個字元、作為 MFA 一部分時最少 8 個字元；應允許至少 64 個字元；不得要求組成規則（例如必須含符號）；不得要求定期更換；必須比對外洩與常見密碼清單；不應使用安全提問作為驗證方式。實際條文與用語請以 NIST 發布的版本為準。

## 26.5 Server-side session 與 session cookie

HTTP 本身是無狀態的（第 20 章）：每個請求都獨立，server 不會自動記得「上一個請求的人已經登入了」。使用者總不能每點一個頁面就輸入一次密碼，所以登入成功時，server 要發一張「通行證」，之後瀏覽器每次請求都帶上它。最傳統、也最容易做對的做法是 **server-side session**：server 產生一個隨機的 **session ID**，在自己的儲存（記憶體、Redis、資料庫）裡記下「這個 ID 屬於 student23，什麼時候建立、最後一次活動是什麼時候」，再把 ID 用 cookie 交給瀏覽器。

```text
 Browser                               auth / app server                    Session store
   │── POST /login（帳號、密碼）────────────►│                                       │
   │                                        │ 驗證密碼（scrypt + compare_digest）     │
   │                                        │ sid = secrets.token_urlsafe(32)       │
   │                                        │──── SET sha256(sid) → {user, created, seen} ─►│
   │◄─ 200  Set-Cookie: __Host-sid=<sid>; ───│                                       │
   │        Path=/; Secure; HttpOnly; SameSite=Lax                                  │
   │                                        │                                       │
   │── GET /me   Cookie: __Host-sid=<sid> ──►│──── GET sha256(sid) ──────────────────►│
   │                                        │◄─── {user: student23, …} ─────────────│
   │                                        │ 檢查閒置與絕對逾時，更新 seen           │
   │◄─ 200 {"user": "student23"} ───────────│                                       │
```

這張時序圖有三個值得注意的細節。第一，session ID 用 `secrets.token_urlsafe(32)` 產生，是 256 bit 的密碼學安全隨機數；不能用 `random` 模組、時間戳記或自增的數字，因為那些都可以被預測。session ID 本身不帶任何意義，它只是一把鑰匙，所有資料都在 server 端。第二，store 裡的 key 是 `sha256(sid)` 而不是 sid 本身：萬一 session store 被讀走（備份外洩、除錯工具），攻擊者拿到的只是雜湊，無法拿來冒用。session ID 是高熵的隨機值，所以這裡用一次快速的 SHA-256 就夠了，不需要像密碼那樣用慢雜湊。第三，每個帶身分的請求都要回到 store 查一次，這是 server-side session 的主要成本，也是它的主要優點：server 隨時可以讓某個 session 失效。

### Set-Cookie 的每一個屬性

cookie 的語法在第 21 章介紹過，跨站相關的屬性在第 23 章有完整討論。這裡只看登入用的 session cookie 該怎麼設：

```text
 Set-Cookie: __Host-sid=Vx3k…43 字元…Qe; Path=/; Secure; HttpOnly; SameSite=Lax
             └───┬───┘ └──────┬──────┘ └──┬──┘ └──┬──┘ └──┬───┘ └─────┬─────┘
              名稱前綴      值（隨機）     全站    只走     JS 讀     跨站請求
           瀏覽器強制檢查               有效    HTTPS   不到       的限制
           Secure、Path=/、不得帶 Domain
           （沒有 Max-Age／Expires：瀏覽器的 session cookie；真正的期限由 server 管）
```

| 屬性 | 建議值 | 防的是什麼 | 沒設的後果 |
|---|---|---|---|
| `Secure` | 一定要 | cookie 只在 HTTPS 上送出 | 任何一個 HTTP 請求（例如被降級的連結）都會把 session ID 明文送出 |
| `HttpOnly` | 一定要 | 頁面上的 JavaScript 讀不到 | 一個 XSS 漏洞就能把 session ID 讀走送出去（第 23 章） |
| `SameSite` | `Lax`（或 `Strict`） | 限制跨站請求自動帶 cookie | CSRF 的風險變高；仍需搭配 CSRF token（第 23 章） |
| `Path` | `/` | cookie 的有效路徑 | 設成子路徑並不能當作安全邊界 |
| `Domain` | 不要設 | 不設時只送回發出 cookie 的那個 host | 設成 `.shengsheng.example` 會送給所有子網域，任何一個子網域被攻破都會外洩 |
| `__Host-` 前綴 | 建議 | 瀏覽器強制要求 Secure、Path=/、無 Domain | 子網域或非 HTTPS 頁面可能覆寫同名 cookie |
| `Max-Age`／`Expires` | 依需求 | 瀏覽器端保留多久 | 不設是瀏覽器 session cookie；但瀏覽器的「還原分頁」功能可能讓它活得比預期久 |

最後一列是常見的誤解：以為「不設 `Max-Age`，關掉瀏覽器 session 就結束了」。實際上很多瀏覽器在還原上次的分頁時，也會還原這些 cookie；而且 cookie 的期限只是給瀏覽器看的，複製走 cookie 的人根本不會遵守。**session 的有效期限必須由 server 端決定與執行**，這是 26.6 節的主題。

### Server-side session 與簽章 cookie

另一種做法是把 session 資料直接放進 cookie，再用 HMAC 簽章防止竄改，server 不必存任何東西。Flask 內建的 `session` 就是這種**簽章 cookie**（signed cookie）：資料經過 `SECRET_KEY` 簽章，但**沒有加密**，使用者把 cookie 拿去 base64 解碼就看得到內容。兩種做法的取捨如下：

| 面向 | Server-side session | 簽章 cookie（如 Flask 預設） |
|---|---|---|
| cookie 內容 | 隨機 ID，不含任何資料 | 資料本身＋簽章，可以被讀取 |
| server 狀態 | 需要 session store（如 Redis） | 不需要 |
| 立即撤銷（登出、改密碼、封鎖帳號） | 刪掉 store 裡的紀錄即可 | 做不到，只能等期限到期，或換掉整把 `SECRET_KEY` |
| 每個請求的成本 | 一次 store 查詢 | 一次 HMAC 驗證 |
| 多台 server | 共用 store | 共用同一把 `SECRET_KEY` |
| 適合 | 登入身分、需要撤銷的狀態 | 不敏感的偏好設定、短期的 UI 狀態 |

「立即撤銷」那一列是聲聲 Live 最後決定改用 server-side session 的原因：撞庫事件後，Rita 需要讓那 186 個帳號的所有 session 立刻失效，簽章 cookie 做不到這件事。第 27 章的 JWT 本質上也是簽章過的自含式 token，會遇到同樣的撤銷問題，到時候會看到「短效 token 加 refresh token」這種折衷。

## 26.6 Session 的生命週期：輪替、登出與逾時

session ID 等於身分，所以它的每一個生命階段都要考慮「如果這個 ID 被別人知道了會怎樣」。

```text
                 GET /（第一次造訪）
   ┌──────┐      發匿名 session         ┌──────────┐   POST /login 成功    ┌──────────┐
   │ 無    │ ─────────────────────────► │ 匿名      │ ──────────────────► │ 已登入    │
   │ cookie│                            │ sid=A    │  刪除 A、發新的 B    │ sid=B    │
   └──────┘                             └──────────┘ （輪替）            └────┬─────┘
       ▲                                                                     │
       │        ┌────────────────────────────────────────────────────────────┤
       │        │ POST /logout：server 刪除 B，回 Set-Cookie Max-Age=0       │
       │        │ 閒置超過 30 分鐘：server 刪除 B                             │
       └────────┤ 登入超過 12 小時（絕對逾時）：server 刪除 B                 │
                │ 改密碼／重設密碼／管理者封鎖：刪除這個帳號的所有 session    │
                └────────────────────────────────────────────────────────────┘
   權限提升（例如完成 MFA、進入金流設定前重新驗證）：同樣刪除舊 ID、發新 ID
```

這張狀態圖從左上開始。使用者第一次造訪時可能就拿到一個匿名 session（例如記住介面語言），這時 sid=A。登入成功的那一刻，server **刪除 A，發一個全新的 B**，這叫 **session 輪替**（session rotation）。右下的已登入狀態有四條離開的路，全部都是由 server 端刪除紀錄，而不只是請瀏覽器刪 cookie。最下面一行補充：只要權限等級改變，都要再輪替一次。

### Session fixation：為什麼登入後一定要換 ID

**Session fixation**（session 固定）是這樣的問題：如果 server 在登入後沿用登入前的 session ID，那麼任何能在登入「之前」讓受害者的瀏覽器帶著某個已知 ID 的人（例如透過某個子網域設定 cookie，或利用接受網址參數當 session ID 的舊式設計），就能在受害者登入之後，用同一個 ID 取得已登入的身分。成因很單純：server 把「登入前就存在的 ID」升級成了「已登入的 ID」。

防禦也很單純，而且完全由 server 掌控：**登入成功時一律產生新的 session ID，並讓舊的立刻失效**；除了 cookie 以外不接受任何其他來源的 session ID（例如網址參數）；配合 `__Host-` 前綴讓子網域無法設定同名 cookie。Rita 發現的第三個問題就是這個：聲聲 Live 的登入程式把 `user_id` 寫進現有的 session 就結束了。修正只需要兩行，在 26.10 節的實驗二裡可以看到登入後舊的匿名 ID 立刻變成 401。順帶一提，登入表單本身也需要 CSRF 防護，否則外站可以讓使用者在不知情的情況下登入攻擊者的帳號，這個「login CSRF」的防禦在第 23 章。

### 登出與逾時：期限只能由 server 執行

登出時要做兩件事：在 server 端刪除 session 紀錄，以及回一個 `Max-Age=0` 的 `Set-Cookie` 讓瀏覽器刪除 cookie。只做後者等於沒有登出，因為被複製走的 cookie 仍然有效，這正是 Rita 的第四項發現。

逾時有兩種，缺一不可。**閒置逾時**（idle timeout）：一段時間沒有任何請求就失效，例如 30 分鐘，每次請求都會把計時歸零，用來處理「在網咖登入後忘了登出」。**絕對逾時**（absolute timeout）：不論多活躍，從登入算起超過一段時間就必須重新登入，例如 12 小時。只有閒置逾時的話，一個被偷走的 session ID 只要每 20 分鐘被使用一次，就能永遠有效；絕對逾時替任何外洩的 session 設定了存活上限。實驗二用模擬時鐘把這兩種逾時都跑一次。

時間長短是風險與便利的取捨。學生瀏覽課表的 session 可以給比較長的閒置時間；老師進入「提領收入」或「修改銀行帳號」這類敏感操作時，聲聲 Live 的設計是**重新驗證**（step-up／re-authentication）：在 session 裡記錄最後一次驗證的時間，超過 10 分鐘就要求再輸入一次密碼或 TOTP，完成後再輪替一次 session ID。「記住我」功能則是另外發一個長效、可輪替、server 端可撤銷的 token，而不是把一般 session 的期限拉到三十天。

最後是「登出所有裝置」：session store 除了 `sha256(sid) → session` 以外，還要維護 `user → {該使用者的所有 session}` 的索引。改密碼、重設密碼、偵測到帳號被接管時，用這個索引一次刪除全部。撞庫事件的善後就是這樣做的：186 個帳號的 session 全部撤銷，並強制重設密碼。

## 26.7 登入限速與帳號鎖定

前面幾節讓「離線攻擊」與「session 被偷」變難，這一節處理**線上攻擊**：攻擊者直接對登入 API 送出大量嘗試。依照攻擊者手上有什麼，可以分成三種形態，各自需要不同的偵測維度：

| 形態 | 長相 | 依 IP 限速 | 依帳號限速 | 其他有效的防禦 |
|---|---|---|---|---|
| 暴力破解（brute force） | 對少數帳號嘗試大量密碼 | 有效（若來源集中） | 有效 | MFA |
| 撞庫（credential stuffing） | 大量帳號，每個帳號只試一兩組外洩的密碼 | 來源集中時有效；分散時無效 | 無效（每個帳號只試一次） | 外洩密碼檢查、MFA、異常偵測 |
| Password spraying | 大量帳號，每個帳號只試幾個最常見的密碼 | 分散時無效 | 無效 | 禁止常見密碼、MFA、全站失敗率監控 |

這張表的結論是：**沒有一個維度能單獨擋住所有攻擊**。依 IP 限速擋得住來源集中的攻擊，但聲聲 Live 遇到的撞庫來自 2,700 個 IP，每個 IP 只送幾十次；依帳號限速擋得住對單一帳號的猛猜，卻對每個帳號只試一次的撞庫毫無作用。所以實務上要多個維度一起用，再加上全站層級的監控（登入失敗率、新 IP 比例），並靠 MFA 讓「密碼正確」不再等於「帳號被接管」。

### Token bucket

限速最常用的演算法是 **token bucket**（權杖桶）：每個 key（例如一個 IP）有一個容量固定的桶子，裡面放著 token；每次嘗試要拿走一個 token，桶子空了就拒絕；token 以固定速率補回，最多補到滿。

```text
            每 5 分鐘補 1 個（rate = 1/300 每秒）
                    │
                    ▼
            ┌───────────────┐
            │ ● ● ● ● ●     │  容量 5：允許短時間內連續失敗 5 次（打錯字很正常）
            └───────┬───────┘
                    │ 每次失敗拿走 1 個
                    ▼
     t=0s   ●●●●●   允許   ── 密碼錯 ──► ●●●●○
     t=6s   ●●●●○   允許   ── 密碼錯 ──► ●●●○○
     …（連錯 5 次）
     t=30s  ○○○○○   拒絕：429，Retry-After ≈ 270 秒（還要等多久才補滿 1 個）
     t=330s ●○○○○   允許 1 次
```

桶子的兩個參數有清楚的意義。**容量**決定可以容忍多少「爆量」：正常使用者偶爾連打錯三四次，不應該被擋。**補充速率**決定長期的上限：每 5 分鐘補 1 個，代表一個來源對一個帳號一天最多大約 288 次嘗試，再多也不行。被拒絕時回 429，並用 `Retry-After` 告訴 client 要等多久，圖中的 270 秒就是「再過多久桶子裡才會有一個完整的 token」。token bucket 的狀態只有兩個數字（目前的 token 數與上次更新的時間），補充是在每次查詢時依經過的時間計算，不需要背景計時器，很適合放在 Redis 這類共用儲存裡讓多台 server 共用。

### 依什麼當 key

聲聲 Live 最後採用三個桶子：

- **(帳號, IP)**：容量 5、每 5 分鐘補 1 個，只在失敗時消耗，成功登入後重置。這個桶子最精準，擋得住「從一個地方猛猜一個帳號」，又不會影響同一個帳號從其他地方登入。
- **IP**：容量 60、每小時約補 60 個，每次嘗試都消耗。擋單一來源的撞庫。
- **帳號**：容量 20、每小時約補 20 個，只在失敗時消耗。用完時**不拒絕，而是要求額外驗證**（例如 TOTP 或寄到 email 的確認連結）。

為什麼帳號這一層不直接鎖住？因為**硬性的帳號鎖定本身就是一種阻斷服務**：任何人只要知道老師的 email，故意打錯幾次密碼，就能讓老師在上課前登不進去。所以對帳號的反應要「升級驗證」而不是「封鎖」，並通知帳號擁有者。IP 這一層的取捨則來自第 7 章的 CGNAT：電信業者讓成千上萬個手機用戶共用同一個對外 IP（例如第 7 章的 198.51.100.200），IP 限額太緊，一棟宿舍或一整個電信網段的使用者就會一起被擋。IPv6 則相反，一個使用者通常拿到一整個 /64，限速應該以 /64 為單位而不是單一位址。

還有一個容易出錯的地方：「IP 是什麼」。登入服務在 load balancer 與 nginx 後面，TCP 連線的來源 IP 是 nginx，不是使用者。真正的 client IP 要從 `X-Forwarded-For` 取，但只能信任自家 proxy 加上的那一段，否則攻擊者在 header 裡隨便填一個 IP，每次請求都換一個，限速就形同虛設；這個信任邊界的處理方式在第 25 章。實驗三會把這五種情境跑一次，包括一種三個桶子都擋不住的攻擊。

## 26.8 MFA 與 TOTP

撞庫之所以能成功，是因為「知道密碼」就等於「是本人」。MFA 要求第二個不同類別的因子，讓外洩的密碼不再足以接管帳號。聲聲 Live 第一階段導入的是 **TOTP**（Time-based One-Time Password，基於時間的一次性密碼）：使用者在手機的 authenticator app 裡綁定聲聲 Live，app 每 30 秒顯示一組 6 位數，登入時除了密碼還要輸入當下的數字。

TOTP 好用的地方在於它完全離線：手機不需要連網，server 也不需要發簡訊。它能運作的原因是手機和 server 在綁定時共享了一把秘密金鑰，之後雙方各自用「金鑰＋目前時間」算出同一組數字。這個算法分兩層：RFC 4226 定義的 HOTP，以及在它之上把計數器換成時間的 RFC 6238 TOTP。

### HOTP：HMAC 加上計數器

**HOTP**（HMAC-based One-Time Password）的輸入是共享金鑰 K 與一個 8 byte 的計數器 C，算法只有三步：算 `HMAC-SHA1(K, C)` 得到 20 bytes；用 **dynamic truncation**（動態截斷）從中取出 31 bit 的整數；取它除以 10^6 的餘數，補零到 6 位數。HMAC 在第 17 章介紹過，它保證沒有金鑰的人算不出結果，也無法從結果反推金鑰。動態截斷的步驟如下，以 RFC 測試金鑰 `"12345678901234567890"`、計數器 1 為例：

```text
 HMAC-SHA1(K, C=1) = 20 bytes
 byte:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
       75 a4 8a 19 d4 cb e1 00 64 4e 8a c1 39 7e ea 74 7a 2d 33 ab
                                        └────┬────┘              └┬┘
                                        取 4 bytes           最後一個 byte 0xab
                                        從 offset 開始        低 4 bit = 0xb = 11 → offset
 ① offset = 0xab & 0x0f = 11
 ② bytes[11..14] = c1 39 7e ea → 0xc1397eea
 ③ 清掉最高 bit：0xc1397eea & 0x7fffffff = 0x41397eea = 1094287082
 ④ 6 位數：1094287082 mod 10^6 = 287082        8 位數：mod 10^8 = 94287082
```

逐步看：① 最後一個 byte 的低 4 bit 是 0 到 15，決定從哪個位置開始截取，所以每次截取的位置都不同（「動態」的由來）；最大的 offset 15 加上 4 bytes 剛好到第 19 個 byte，不會越界。② 從 offset 取連續 4 bytes，以 big-endian 解讀成 32 bit 整數。③ 把最高位元清掉，避免不同語言對有號、無號整數的處理差異造成結果不一致。④ 取餘數得到要顯示的位數。這組 HMAC 正是 RFC 4226 附錄 D 中計數器 1 的值，6 位數結果 `287082` 也與 RFC 吻合；而 8 位數的 `94287082`，下一小節會在 RFC 6238 的測試向量裡再見到它。

### TOTP：把計數器換成時間

HOTP 的計數器需要兩端同步遞增，按了沒用就會不同步。**TOTP** 把計數器換成時間：`T = floor((目前 Unix 時間 − T0) / X)`，T0 預設 0、時間步長 X 預設 30 秒，其餘完全沿用 HOTP。所以在 Unix 時間 59 秒時，T = 1，算出來的就是上面那組 `94287082`。

```text
 Unix 時間（秒）  … 1789999980   1790000010   1790000040   1790000070 …
                    │ T=59666666 │ T=59666667 │ T=59666668 │
                    ├────────────┼────────────┼────────────┤
 server 現在 ─────────────────────────▲ 1790000015（T=59666667）
 server 接受的範圍：  ◄── T−1 ───►◄──── T ────►◄── T+1 ──►   （window = 1）
 手機慢 30 秒，送出 T−1 的碼 → 接受，並記錄 last_step = T−1
 同一個碼再送一次          → 拒絕（重放）
 T−4（兩分鐘前）的碼        → 拒絕（超出範圍）
```

這張時間軸說明 server 端驗證時的兩個規則。第一是**容許時鐘誤差**：手機與 server 的時鐘可能差幾秒到幾十秒，使用者輸入也要時間，所以 server 通常接受前後各一個時間步的碼（window = 1），也就是約 90 秒的有效範圍。RFC 6238 建議這個範圍不要開太大，因為每多接受一個時間步，猜中的機率就多一份。第二是**防止重放**：一組碼在有效時間內可能被看到（例如肩後偷看、被釣魚網站轉送），所以 server 要記錄這個帳號最後一次成功使用的時間步，同一步或更早的碼一律拒絕。

### 綁定、儲存與復原

綁定時，server 用 `secrets.token_bytes(20)` 產生 160 bit 的金鑰（RFC 4226 要求至少 128 bit、建議 160 bit），轉成 base32 文字，放進一個 `otpauth://totp/…` 格式的 URI 再做成 QR code 讓 app 掃描。這個 URI 格式不是 RFC，而是由 authenticator app 生態系約定俗成；有些 app 只支援 SHA-1、6 位數、30 秒這組預設值，所以多數服務都使用這組預設。綁定流程的最後一步一定要請使用者輸入一組當下的碼，確認 app 已經正確設定，才把 MFA 標記為啟用。

TOTP 的金鑰和密碼有一個根本差異：**server 必須能取回金鑰的原值**，因為驗證時要用它計算 HMAC，所以不能像密碼一樣只存雜湊。正確的做法是加密後存放（例如用 KMS 管理的金鑰做 envelope encryption），並嚴格限制能解密的服務。這也是 TOTP 的結構性弱點：server 端的秘密一旦外洩，攻擊者就能產生任何使用者的碼。

使用者換手機、手機遺失時要有**復原碼**（recovery codes）：綁定時產生 8 到 10 組一次性的隨機碼，只顯示一次，server 像密碼一樣用 salt 與雜湊存放，每組用過就作廢。復原流程是攻擊者最愛找的弱點，如果「忘記 MFA」只要回答一個安全提問就能關掉，前面所有的努力都白費了。TOTP 的驗證也要限速，而且要比密碼更嚴格，因為 6 位數只有一百萬種可能（延伸問答 Q6 會手算這件事）。

### MFA 的種類與 passkeys 預告

| 方式 | 屬於哪類因子 | 防撞庫 | 防釣魚 | 主要弱點 |
|---|---|---|---|---|
| 簡訊（SMS）或語音 OTP | 擁有（電話號碼） | 是 | 否 | SIM swap、門號轉移、簡訊被攔截；成本高 |
| Email OTP 或連結 | 擁有（信箱） | 是 | 否 | 信箱本身被接管；常與密碼重設共用同一個信箱 |
| TOTP（authenticator app） | 擁有（手機上的金鑰） | 是 | 否 | 使用者可能在釣魚網站輸入碼；server 端要保管金鑰 |
| 推播核准 | 擁有（已登入的 app） | 是 | 部分 | 使用者被連續推播騷擾後誤按同意（push fatigue），需要「輸入畫面上的數字」等設計 |
| Passkeys／WebAuthn | 擁有（裝置上的私鑰），常再加上生物辨識或 PIN | 是 | 是 | 需要瀏覽器與裝置支援；帳號復原流程要另外設計 |

表中「防釣魚」那一欄是 TOTP 的天花板。如果使用者在一個長得很像聲聲 Live 的假網站上輸入密碼與當下的 TOTP 碼，假網站可以在 30 秒內把它們轉送到真網站登入；TOTP 碼本身不知道自己被輸入到哪個網站。**Passkeys**（基於 WebAuthn 規格）從根本上解決這個問題：裝置上保存一把私鑰，server 只存公鑰；登入時 server 送出隨機的 challenge，裝置用私鑰簽章，而且瀏覽器會把「目前網站的 origin」綁進簽章內容，假網站拿到的簽章對真網站無效。server 端也不再有可以被偷走後拿來登入的秘密。passkeys 的完整原理與流程在第 29 章。

> [!note] 2026 現況：passkeys（截至 2026 年 10 月）
> WebAuthn Level 3 已於 2026 年 8 月成為 W3C Recommendation（依 2026 年 10 月查證）。主要作業系統平台都支援可在裝置間同步的 passkeys，第三方密碼管理工具也能保存 passkeys。聲聲 Live 的規劃是：TOTP 作為所有帳號的 MFA 基本選項，passkeys 作為建議選項並逐步推廣到老師帳號，細節見第 29 章。

## 26.9 忘記密碼與帳號復原

忘記密碼的流程本質上是「用另一個因子（信箱）重新建立身分」，所以它的強度決定了整個帳號的強度上限：密碼再長、MFA 再好，只要重設流程有漏洞，攻擊者就從這裡進來。Rita 的最後一項發現就在這裡：重設 token 明文存在資料庫、沒有期限、用過也不會作廢。

```text
 Browser                       auth server                        Mail
   │── POST /forgot email=… ────►│                                  │
   │                             │ 不論 email 是否存在：             │
   │                             │   回應內容與時間都一樣             │
   │◄─ 200 「如果有註冊，已寄出」 ─│                                  │
   │                             │ 若存在：token = secrets.token_urlsafe(32)
   │                             │   存 sha256(token) → (帳號, 30 分鐘後到期)
   │                             │── 連結（base URL 取自設定）────────►│ ──► 使用者信箱
   │── GET /reset?token=…  ─────►│ 頁面加上 Referrer-Policy: no-referrer
   │── POST /reset token + 新密碼►│ 查 sha256(token)：存在？沒過期？→ 立刻刪除（單次）
   │                             │ 更新密碼雜湊；刪除該帳號所有 session；寄通知信
   │◄─ 200 請重新登入 ────────────│                                  │
```

這張時序圖裡每一個註記都對應一個常見錯誤。第一，回應必須與 email 是否存在無關，否則這個 API 就成了查詢「誰在聲聲 Live 有帳號」的工具；寄信這種慢動作最好放進背景工作，讓兩種情況的回應時間也一致。第二，token 是 256 bit 隨機數，資料庫只存它的 SHA-256，理由與 session ID 相同。第三，有效期限要短（例如 30 分鐘），而且用過一次就刪除。第四，信裡連結的網域必須來自設定檔，而不是請求的 `Host` header；否則攻擊者可以送出帶著假 Host 的重設請求，讓系統寄出指向別的網域的連結。第五，重設頁面設定 `Referrer-Policy: no-referrer`，並確認 access log 不記錄 query string，避免 token 經由 Referer 或 log 外洩。最後，重設成功後刪除該帳號的所有 session 並寄通知信，萬一重設不是本人發起的，使用者也能立刻知道。

```python
import hashlib
import hmac
import secrets

RESET_TTL = 30 * 60                     # 重設連結 30 分鐘內有效
RESETS = {}                             # sha256(token) → (帳號, 到期時間)；明文 token 只出現在信裡
SESSIONS = {"student23@example.com": {"laptop", "phone"}}  # 每個帳號目前有效的 session（簡化表示）


def request_reset(email: str, now: int, known: set) -> tuple[str, str | None]:
    message = "如果這個 email 有註冊，我們已寄出重設連結。"   # 不論存在與否，回應一樣
    if email not in known:
        return message, None
    token = secrets.token_urlsafe(32)
    RESETS[hashlib.sha256(token.encode()).hexdigest()] = (email, now + RESET_TTL)
    link = f"https://auth.shengsheng.example/reset?token={token}"  # base URL 用設定值，不信任 Host header
    return message, link


def complete_reset(token: str, now: int) -> str:
    key = hashlib.sha256(token.encode()).hexdigest()
    entry = RESETS.pop(key, None)       # pop：不論成功與否，一個 token 只能用一次
    if entry is None:
        return "invalid"
    email, expires = entry
    if now > expires:
        return "expired"
    SESSIONS[email] = set()           # 換了密碼就讓所有舊 session 失效
    return f"ok({email})"


known = {"student23@example.com"}
m1, _ = request_reset("nobody@example.com", 0, known)
m2, link = request_reset("student23@example.com", 0, known)
print("回應相同？", m1 == m2, "；資料庫存的是雜湊？", link.split("=")[1] not in str(RESETS))
token = link.split("=")[1]
print("第 1 次使用 →", complete_reset(token, 600), "；舊 session =", SESSIONS["student23@example.com"])
print("第 2 次使用 →", complete_reset(token, 601))
_, link2 = request_reset("student23@example.com", 1000, known)
print("31 分鐘後才點 →", complete_reset(link2.split("=")[1], 1000 + 31 * 60))
assert complete_reset("guess", 0) == "invalid" and not RESETS
```

```text
回應相同？ True ；資料庫存的是雜湊？ True
第 1 次使用 → ok(student23@example.com) ；舊 session = set()
第 2 次使用 → invalid
31 分鐘後才點 → expired
```

第一行驗證兩件事：不存在與存在的 email 得到完全相同的回應，以及資料庫裡找不到明文 token。第二行是正常的重設：成功後該帳號的 session 集合被清空，代表筆電和手機上的舊登入都失效了。第三行把同一個 token 再用一次，因為第一次使用時就已經 `pop` 掉，結果是 invalid。第四行是過期：同一個流程，只是 31 分鐘後才點連結。為了專注在 token 的生命週期，這段程式省略了「設定新密碼」本身，實務上那一步就是呼叫 26.3 節的 `hash_password`。

如果帳號已經啟用 MFA，忘記密碼後仍應要求 MFA，否則「能收信」就足以同時繞過密碼與 MFA。反過來，「遺失 MFA 裝置」的復原流程（使用復原碼、或人工審核身分）要比忘記密碼更嚴格，並且在完成後一段時間內限制敏感操作，例如 24 小時內不能修改提領帳號。

## 26.10 動手做：從密碼雜湊到 TOTP 的一套登入系統

這一節用四段程式把本章的機制做一次：密碼雜湊與升級、server-side session 的登入流程、依帳號與 IP 的限速，以及從零實作 TOTP。每段都只用標準函式庫，可以單獨執行；網路相關的部分只在 127.0.0.1 上用 port 0。

### 實驗一：密碼雜湊、驗證與升級

這段程式實作 26.3 節的完整設計：NFKC 正規化與長度上限、每個帳號獨立的 16 bytes salt、自我描述的儲存格式、`hmac.compare_digest`，以及「離線包裝遺留雜湊、登入時再升級」的兩階段策略。注意 `MAXMEM`：N=2^17、r=8 需要約 128 MiB，而 OpenSSL 預設只允許 32 MiB，不調高會直接拋出錯誤。

```python
import base64
import hashlib
import hmac
import secrets
import time
import unicodedata

CURRENT = {"ln": 17, "r": 8, "p": 1}      # N = 2**17：記憶體約 128 × N × r = 128 MiB
MAXMEM = 256 * 1024 * 1024                # OpenSSL 預設上限 32 MiB，不調高會直接報錯
MAX_PASSWORD_CHARS = 256                  # 允許長密碼，但替每次雜湊的成本設上限


def b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode().rstrip("=")


def b64d(text: str) -> bytes:
    return base64.b64decode(text + "=" * (-len(text) % 4))


def normalize(password: str) -> bytes:
    if len(password) > MAX_PASSWORD_CHARS:
        raise ValueError("password too long")
    # 同一個字在不同輸入法可能是不同的碼位，先正規化再雜湊
    return unicodedata.normalize("NFKC", password).encode("utf-8")


def scrypt(secret: bytes, salt: bytes, ln: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(secret, salt=salt, n=2 ** ln, r=r, p=p, maxmem=MAXMEM, dklen=32)


def encode(scheme: str, secret: bytes, params: dict) -> str:
    salt = secrets.token_bytes(16)        # 每個帳號一把獨立的隨機 salt
    dk = scrypt(secret, salt, **params)
    p = params
    return f"${scheme}$ln={p['ln']},r={p['r']},p={p['p']}${b64e(salt)}${b64e(dk)}"


def hash_password(password: str, params=CURRENT) -> str:
    return encode("scrypt", normalize(password), params)


def wrap_legacy(sha256_hex: str) -> str:
    # 不需要明文：把舊的快速雜湊當成「密碼」再做一次 scrypt
    return encode("scrypt-sha256", sha256_hex.encode(), CURRENT)


def verify_password(password: str, stored: str) -> tuple[bool, bool]:
    """回傳 (密碼正確, 需要升級雜湊)。"""
    if stored.startswith("sha256$"):                      # 早期遺留：無 salt 的 SHA-256
        digest = hashlib.sha256(normalize(password)).hexdigest()
        return hmac.compare_digest(digest, stored[7:]), True
    _, scheme, param_text, salt_text, hash_text = stored.split("$")
    params = {k: int(v) for k, v in (kv.split("=") for kv in param_text.split(","))}
    secret = normalize(password)
    if scheme == "scrypt-sha256":                         # 離線包起來的遺留雜湊
        secret = hashlib.sha256(secret).hexdigest().encode()
    elif scheme != "scrypt":
        raise ValueError(f"unknown scheme {scheme}")
    candidate = scrypt(secret, b64d(salt_text), **params)
    ok = hmac.compare_digest(candidate, b64d(hash_text))  # 不能用 ==，見 26.3 節
    return ok, (scheme != "scrypt" or params != CURRENT)


def login(db: dict, user: str, password: str) -> bool:
    ok, upgrade = verify_password(password, db[user])
    if ok and upgrade:                                    # 只有在拿到明文的這一刻才能升級
        db[user] = hash_password(password)
    return ok


# 1. 同一個密碼雜湊兩次：salt 不同，結果就不同
t0 = time.perf_counter()
h1 = hash_password("Kyoto-Matcha-2026")
cost_ms = (time.perf_counter() - t0) * 1000
h2 = hash_password("Kyoto-Matcha-2026")
print("1. stored :", h1[:32] + "…")
print(f"   兩次結果相同？{h1 == h2}；每次雜湊約 {cost_ms:.0f} ms")
print("   verify(正確) =", verify_password("Kyoto-Matcha-2026", h1))
print("   verify(錯誤) =", verify_password("kyoto-matcha-2026", h1))

# 2. 遺留資料：無 salt，兩個帳號用同一個密碼，雜湊一眼就看得出來
db = {
    "student23": "sha256$" + hashlib.sha256(b"sunflower88").hexdigest(),
    "student77": "sha256$" + hashlib.sha256(b"sunflower88").hexdigest(),
    "teacher05": hash_password("old-but-fine", params={"ln": 14, "r": 8, "p": 1}),
}
print("2. 遺留表中 student23 與 student77 的雜湊相同？", db["student23"] == db["student77"])

# 3. 先離線把所有 sha256 雜湊包進 scrypt：不需要明文，資料庫外洩時也不再是快速雜湊
for user, stored in db.items():
    if stored.startswith("sha256$"):
        db[user] = wrap_legacy(stored[7:])
print("3. 包裝後 student23 :", db["student23"][:39] + "…")

# 4. 使用者登入時再換成目前的標準格式
for user, pw in [("student23", "sunflower88"), ("teacher05", "old-but-fine")]:
    before = db[user].split("$")[1:3]
    assert login(db, user, pw)
    print(f"4. {user} 登入成功：{before} → {db[user].split('$')[1:3]}")
assert not login(db, "student77", "Sunflower88")          # 錯的密碼不會觸發升級
assert db["student77"].startswith("$scrypt-sha256$")
ok, upgrade = verify_password("sunflower88", db["student77"])
print("5. student77 還沒登入，仍是包裝格式；verify =", (ok, upgrade))
assert ok and upgrade and verify_password("Kyoto-Matcha-2026", h1) == (True, False)
```

```text
1. stored : $scrypt$ln=17,r=8,p=1$eirRoMzjig…
   兩次結果相同？False；每次雜湊約 223 ms
   verify(正確) = (True, False)
   verify(錯誤) = (False, False)
2. 遺留表中 student23 與 student77 的雜湊相同？ True
3. 包裝後 student23 : $scrypt-sha256$ln=17,r=8,p=1$yFFRG+ivzs…
4. student23 登入成功：['scrypt-sha256', 'ln=17,r=8,p=1'] → ['scrypt', 'ln=17,r=8,p=1']
4. teacher05 登入成功：['scrypt', 'ln=14,r=8,p=1'] → ['scrypt', 'ln=17,r=8,p=1']
5. student77 還沒登入，仍是包裝格式；verify = (True, True)
```

（salt 是隨機的，所以每次執行時 `stored` 的內容不同；雜湊時間依機器而定，這是在筆電上的結果。）

逐行解說。第 1 段：同一個密碼雜湊兩次得到不同的結果，因為 salt 不同；一次雜湊約 220 毫秒，對登入一次來說可以接受，對想嘗試數十億個候選密碼的攻擊者則是天文數字。驗證錯誤的密碼（只差大小寫）回傳 `(False, False)`。第 2 段重現 Rita 的發現：遺留表裡用同一個密碼的兩個帳號，雜湊完全相同。第 3 段是離線包裝，程式沒有碰到任何明文密碼，只拿舊的 SHA-256 十六進位字串當輸入；包裝後的格式前綴是 `scrypt-sha256`，參數已經是目前的標準。

第 4 段是登入時升級：student23 從包裝格式換成標準格式，teacher05 從過時的 ln=14 換成 ln=17，兩者都只在密碼驗證成功、手上有明文的那一刻發生。第 5 段確認兩個邊界：用錯的密碼登入不會觸發升級（程式中的 assert），而還沒登入過的 student77 仍停留在包裝格式，但已經能正確驗證，`needs_rehash` 為 True 等著下一次登入。

### 實驗二：server-side session 的登入流程

這段程式用 `http.server` 在 127.0.0.1 上跑一個登入服務，實作 26.5、26.6 節的設計：未登入就發匿名 session、登入成功後輪替 ID、閒置 30 分鐘與絕對 12 小時逾時、登出時刪除 server 端紀錄，並且帳號不存在時也跑一次雜湊。時間用 `Clock` 模擬，讓我們可以「快轉」12 小時而不用真的等待。client 端用 `http.client` 手動帶 `Cookie` header，這樣每一步帶了哪個 session ID 都清清楚楚。

```python
import hashlib
import hmac
import http.client
import json
import secrets
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

COOKIE = "__Host-sid"                 # __Host-：必須 Secure、Path=/、不能帶 Domain
IDLE_TIMEOUT = 30 * 60                # 30 分鐘沒有活動就失效
ABSOLUTE_TIMEOUT = 12 * 3600          # 不論多活躍，登入 12 小時後一定要重新登入


class Clock:                          # 模擬時鐘：測試可以「快轉」而不用真的等
    now = 1_790_000_000.0


def kdf(password: str, salt: bytes) -> bytes:
    # 示範用較低的 N 讓程式跑得快；正式參數見 26.3 節
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


SALT = secrets.token_bytes(16)
USERS = {"student23": (SALT, kdf("Kyoto-Matcha-2026", SALT))}
DUMMY = (secrets.token_bytes(16), b"\0" * 32)      # 帳號不存在時也做一次雜湊，讓時間一致
SESSIONS = {}                                      # sha256(sid) → session 資料
LOCK = threading.Lock()


def sid_key(sid: str) -> str:
    return hashlib.sha256(sid.encode()).hexdigest()  # 存雜湊：store 外洩也拿不到可用的 sid


def new_session(user=None) -> str:
    sid = secrets.token_urlsafe(32)                  # 256 bit 隨機數
    with LOCK:
        SESSIONS[sid_key(sid)] = {"user": user, "created": Clock.now, "seen": Clock.now}
    return sid


def load_session(sid):
    if not sid:
        return None
    with LOCK:
        s = SESSIONS.get(sid_key(sid))
        if s is None:
            return None
        if Clock.now - s["seen"] > IDLE_TIMEOUT or Clock.now - s["created"] > ABSOLUTE_TIMEOUT:
            del SESSIONS[sid_key(sid)]               # 逾時就在 server 端刪除，不只是不認
            return None
        s["seen"] = Clock.now                        # 滑動的閒置計時
        return s


def destroy(sid):
    with LOCK:
        SESSIONS.pop(sid_key(sid or ""), None)


def set_cookie(value: str, max_age=None) -> str:
    attrs = f"{COOKIE}={value}; Path=/; Secure; HttpOnly; SameSite=Lax"
    return attrs + (f"; Max-Age={max_age}" if max_age is not None else "")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def sid(self):
        jar = SimpleCookie(self.headers.get("Cookie", ""))
        return jar[COOKIE].value if COOKIE in jar else None

    def reply(self, code, body, cookie=None):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")  # 帶身分的回應不要進任何快取
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":                         # 未登入也發 session（例如存語言偏好）
            sid = self.sid() if load_session(self.sid()) else new_session()
            return self.reply(200, {"page": "home"}, set_cookie(sid))
        s = load_session(self.sid())
        if self.path == "/me" and s and s["user"]:
            return self.reply(200, {"user": s["user"]})
        self.reply(401, {"error": "login required"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        if self.path == "/login":
            salt, expected = USERS.get(form.get("user"), DUMMY)
            ok = hmac.compare_digest(kdf(form.get("password", ""), salt), expected)
            if not ok:
                return self.reply(401, {"error": "帳號或密碼錯誤"})  # 不透露是哪一個錯
            destroy(self.sid())                       # 輪替：登入前的 sid 立刻作廢
            return self.reply(200, {"user": form["user"]}, set_cookie(new_session(form["user"])))
        if self.path == "/logout":
            destroy(self.sid())                       # 真正的登出發生在 server 端
            return self.reply(200, {"bye": True}, set_cookie("", max_age=0))
        self.reply(404, {})


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
conn = http.client.HTTPConnection(*server.server_address)


def call(method, path, sid=None, form=None):
    headers = {"Cookie": f"{COOKIE}={sid}"} if sid else {}
    body = None
    if form:
        body = "&".join(f"{k}={v}" for k, v in form.items())
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    data = json.loads(resp.read())
    jar = SimpleCookie(resp.getheader("Set-Cookie") or "")
    new_sid = jar[COOKIE].value if COOKIE in jar else None
    return resp.status, data, new_sid, resp.getheader("Set-Cookie")


status, _, anon, raw = call("GET", "/")
print("1. 首頁 Set-Cookie:", raw.replace(anon, "<sid>"))
print("   未登入 /me →", call("GET", "/me", anon)[0])
status, data, _, _ = call("POST", "/login", anon, {"user": "student23", "password": "wrong"})
print("2. 密碼錯誤 →", status, data["error"])
status, data, _, _ = call("POST", "/login", anon, {"user": "nobody", "password": "wrong"})
print("   帳號不存在 →", status, data["error"])
status, _, sid, _ = call("POST", "/login", anon, {"user": "student23", "password": "Kyoto-Matcha-2026"})
print("3. 登入成功 →", status, "；sid 換了嗎？", sid != anon)
print("   舊的匿名 sid 打 /me →", call("GET", "/me", anon)[0], "；新 sid →", call("GET", "/me", sid)[:2])

Clock.now += 29 * 60
print("4. 閒置 29 分鐘 →", call("GET", "/me", sid)[0])
Clock.now += 31 * 60
print("   再閒置 31 分鐘 →", call("GET", "/me", sid)[0], "；server 端 session 數 =", len(SESSIONS))

_, _, sid, _ = call("POST", "/login", None, {"user": "student23", "password": "Kyoto-Matcha-2026"})
codes = []
for _ in range(37):                               # 每 20 分鐘點一次，持續 12 小時以上
    Clock.now += 20 * 60
    codes.append(call("GET", "/me", sid)[0])
print(f"5. 每 20 分鐘活動一次：前 {codes.index(401)} 次 200，第 {codes.index(401) + 1} 次（{(codes.index(401) + 1) * 20 / 60:.1f} 小時）→ 401")

_, _, sid, _ = call("POST", "/login", None, {"user": "student23", "password": "Kyoto-Matcha-2026"})
status, _, cleared, raw = call("POST", "/logout", sid)
print("6. 登出 Set-Cookie:", raw)
print("   登出後重送舊 cookie →", call("GET", "/me", sid)[0])

assert codes.index(401) == 36 and call("GET", "/me", anon)[0] == 401
conn.close()
server.shutdown()
server.server_close()
```

```text
1. 首頁 Set-Cookie: __Host-sid=<sid>; Path=/; Secure; HttpOnly; SameSite=Lax
   未登入 /me → 401
2. 密碼錯誤 → 401 帳號或密碼錯誤
   帳號不存在 → 401 帳號或密碼錯誤
3. 登入成功 → 200 ；sid 換了嗎？ True
   舊的匿名 sid 打 /me → 401 ；新 sid → (200, {'user': 'student23'})
4. 閒置 29 分鐘 → 200
   再閒置 31 分鐘 → 401 ；server 端 session 數 = 0
5. 每 20 分鐘活動一次：前 36 次 200，第 37 次（12.3 小時）→ 401
6. 登出 Set-Cookie: __Host-sid=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0
   登出後重送舊 cookie → 401
```

逐行對照。第 1 行是 cookie 的完整屬性，和 26.5 節的圖一致；沒有 `Max-Age`，期限交給 server。這裡用的是 HTTP，而 `Secure` 屬性要求 HTTPS，真正的瀏覽器在 HTTP 頁面不會接受這個 cookie；`http.client` 不實作 cookie 規則，所以實驗照樣能跑，正式環境前面一定有 TLS（第 18、19 章）。第 2 行，「密碼錯誤」與「帳號不存在」得到同一個狀態碼與同一句訊息，而且兩條路徑都跑了一次 scrypt，回應時間也相近。

第 3 行是本實驗的重點：登入成功後 session ID 換了，而且拿登入前的匿名 ID 去打 `/me` 得到 401，表示舊 ID 已經從 store 裡刪除，session fixation 的前提不存在了。第 4 行驗證閒置逾時：29 分鐘後仍有效（而且這次請求把閒置計時歸零），之後再過 31 分鐘才失效，server 端的紀錄也一併刪除，store 裡剩下 0 筆。

第 5 行驗證絕對逾時：重新登入後每 20 分鐘活動一次，閒置計時永遠不會到期，但第 37 次請求（登入後 12.3 小時）仍然得到 401。這就是 26.6 節說的「一個被偷走的 session，就算持續被使用也有存活上限」。第 6 行是登出：`Set-Cookie` 用 `Max-Age=0` 叫瀏覽器刪除，同時 server 端的紀錄也刪了，所以重送登出前複製的 cookie 依然是 401。

### 實驗三：依帳號與 IP 的 token bucket 限速

這段程式實作 26.7 節的三個桶子，再用模擬的時間與 IP 跑五種情境：正常使用者、單一來源的暴力破解、單一來源的撞庫、分散式撞庫，以及多個來源輪流猜同一個老師帳號。

```python
from collections import Counter


class Bucket:
    """Token bucket：容量 capacity，每秒補 rate 個 token，最多補到滿。"""

    def __init__(self, capacity: float, rate: float, now: float):
        self.capacity, self.rate = capacity, rate
        self.tokens, self.updated = capacity, now   # 新的 key 從滿桶開始

    def _refill(self, now):
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def available(self, now) -> bool:
        self._refill(now)
        return self.tokens >= 1

    def take(self, now):
        self._refill(now)
        self.tokens = max(0.0, self.tokens - 1)

    def retry_after(self, now) -> int:
        self._refill(now)
        return max(0, round((1 - self.tokens) / self.rate))


class LoginLimiter:
    # (參數為示範值，依自己的流量調整)
    RULES = {
        "ip": (60, 60 / 3600),      # 每個來源 IP：每小時約 60 次嘗試，不論帳號
        "pair": (5, 1 / 300),       # (帳號, IP)：連錯 5 次後，每 5 分鐘才多 1 次
        "account": (20, 20 / 3600), # 每個帳號：不論來源，每小時約 20 次失敗
    }

    def __init__(self):
        self.buckets = {}

    def _bucket(self, kind, key, now):
        if (kind, key) not in self.buckets:
            self.buckets[(kind, key)] = Bucket(*self.RULES[kind], now)
        return self.buckets[(kind, key)]

    def check(self, user, ip, now) -> str:
        b_ip, b_pair = self._bucket("ip", ip, now), self._bucket("pair", (user, ip), now)
        if not b_ip.available(now):
            return "deny:ip"
        if not b_pair.available(now):
            return f"deny:pair(retry {b_pair.retry_after(now)}s)"
        b_ip.take(now)                               # 每次放行的嘗試都消耗 IP 額度
        if not self._bucket("account", user, now).available(now):
            return "challenge"                       # 不鎖死帳號，改要求額外驗證
        return "allow"

    def failed(self, user, ip, now):                 # 只有失敗才消耗帳號相關額度
        self._bucket("pair", (user, ip), now).take(now)
        self._bucket("account", user, now).take(now)

    def succeeded(self, user, ip):
        self.buckets.pop(("pair", (user, ip)), None)


def run(title, attempts, limiter, correct=None):
    seen, first = Counter(), {}
    for t, user, ip in attempts:
        decision = limiter.check(user, ip, t)
        seen[decision.split("(")[0]] += 1
        first.setdefault(decision.split("(")[0], decision)
        if decision == "allow":
            if (user, t) == correct:
                limiter.succeeded(user, ip)
            else:
                limiter.failed(user, ip, t)
    print(f"{title} → {dict(seen)}")
    return seen, first


HOME, ATTACKER = "198.51.100.23", "192.0.2.201"
lim = LoginLimiter()

# A. 學生打錯 3 次，第 4 次成功
a, _ = run("A 學生打錯三次後成功", [(i * 20, "student23", HOME) for i in range(4)], lim, ("student23", 60))
# B. 單一 IP 在一分鐘內對同一帳號猜 10 次
b, first = run("B 單一來源猜同一帳號", [(1000 + i * 6, "student77", ATTACKER) for i in range(10)], lim)
print("  第 6 次的回應：", first["deny:pair"])
# C. 單一 IP 拿外洩清單，每個帳號只試一次（撞庫）
c, _ = run("C 單一來源撞庫 200 帳號", [(2000 + i * 3, f"user{i}", "192.0.2.202") for i in range(200)], lim)
# D. 100 個 IP、每個 IP 只試一個帳號：三種桶子都擋不住
d, _ = run("D 分散撞庫 100 IP", [(3000 + i, f"victim{i}", f"192.0.2.{100 + i}") for i in range(100)], lim)
# E. 100 個 IP 輪流猜同一個老師帳號，接著老師本人從家裡登入
e, _ = run("E 分散猜 teacher05", [(4000 + i * 2, "teacher05", f"192.0.2.{100 + i}") for i in range(30)], lim)
print("  老師本人從家裡登入：", lim.check("teacher05", "198.51.100.30", 4100))

assert a == Counter(allow=4) and b == Counter(allow=5, **{"deny:pair": 5})
assert c["allow"] == 69 and c["deny:ip"] == 131 and d == Counter(allow=100)
assert e == Counter(allow=20, challenge=10)
```

```text
A 學生打錯三次後成功 → {'allow': 4}
B 單一來源猜同一帳號 → {'allow': 5, 'deny:pair': 5}
  第 6 次的回應： deny:pair(retry 270s)
C 單一來源撞庫 200 帳號 → {'allow': 69, 'deny:ip': 131}
D 分散撞庫 100 IP → {'allow': 100}
E 分散猜 teacher05 → {'allow': 20, 'challenge': 10}
  老師本人從家裡登入： challenge
```

逐行解說。A：學生打錯三次後成功，四次全部放行，限速對正常使用者沒有影響，成功後 (帳號, IP) 的桶子也被重置。B：同一個來源一分鐘內猜 student77 十次，前 5 次放行（失敗），第 6 次起被 (帳號, IP) 的桶子擋下，`Retry-After` 約 270 秒，和 26.7 節的圖一樣。C：單一來源用外洩清單撞 200 個帳號，每個帳號只試一次，帳號相關的桶子完全沒反應，擋下它的是 IP 桶子；放行的 69 次是初始容量 60，其餘是這 10 分鐘內陸續補回的 token。

D 是本實驗最重要的一行：100 個 IP 各自只試一個帳號，三個桶子全部放行。這就是週五晚上的撞庫型態，也說明限速只是其中一道防線，擋這種攻擊要靠外洩密碼檢查、MFA，以及「全站登入失敗率突然飆高」的告警。E：多個 IP 輪流猜 teacher05，帳號桶子在 20 次失敗後轉為 `challenge`；最後一行是老師本人從家裡登入，得到的也是 `challenge` 而不是拒絕，意思是「請完成 TOTP 再進來」。如果這裡用的是硬性鎖定，攻擊者就成功讓老師在上課前登不進去了。

### 實驗四：從零實作 TOTP 並用 RFC 測試向量驗證

這段程式只用 `hmac`、`hashlib` 與 `struct` 實作 HOTP 與 TOTP，先跑 RFC 4226 附錄 D 的 10 組 HOTP 測試向量，再跑 RFC 6238 附錄 B 的 18 組 TOTP 測試向量（6 個時間點 × SHA-1、SHA-256、SHA-512），最後實作 server 端的驗證規則：前後一個時間步的容許範圍與重放防護。

```python
import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote


def hotp(key: bytes, counter: int, digits: int = 6, algo=hashlib.sha1) -> str:
    """RFC 4226：HMAC(key, 8-byte counter) → dynamic truncation → 取 digits 位數。"""
    mac = hmac.new(key, struct.pack(">Q", counter), algo).digest()
    offset = mac[-1] & 0x0F                       # 最後一個 byte 的低 4 bit 決定從哪裡截
    code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFF_FFFF  # 去掉最高 bit
    return str(code % 10 ** digits).zfill(digits)


def totp(key: bytes, unix_time: int, step: int = 30, digits: int = 6, algo=hashlib.sha1) -> str:
    """RFC 6238：counter = floor((時間 - T0) / 步長)，T0 = 0。"""
    return hotp(key, unix_time // step, digits, algo)


# 1. RFC 4226 附錄 D 的 HOTP 測試向量
key20 = b"12345678901234567890"
expected_hotp = ["755224", "287082", "359152", "969429", "338314",
                 "254676", "287922", "162583", "399871", "520489"]
assert [hotp(key20, c) for c in range(10)] == expected_hotp
print("RFC 4226 HOTP counter 0-9 全部吻合")

# 2. RFC 6238 附錄 B 的 TOTP 測試向量（8 位數，三種 hash 各用不同長度的 key）
keys = {"SHA1": (key20, hashlib.sha1),
        "SHA256": (b"12345678901234567890123456789012", hashlib.sha256),
        "SHA512": (b"1234567890" * 6 + b"1234", hashlib.sha512)}
vectors = [(59, "94287082", "46119246", "90693936"),
           (1111111109, "07081804", "68084774", "25091201"),
           (1111111111, "14050471", "67062674", "99943326"),
           (1234567890, "89005924", "91819424", "93441116"),
           (2000000000, "69279037", "90698825", "38618901"),
           (20000000000, "65353130", "77737706", "47863826")]
print(f"{'time':>12} {'T (hex)':>18}  SHA1      SHA256    SHA512")
for t, *want in vectors:
    got = [totp(k, t, digits=8, algo=a) for k, a in keys.values()]
    assert got == want, (t, got, want)
    print(f"{t:>12} {t // 30:016X}  {'  '.join(got)}")


class TotpVerifier:
    """伺服器端驗證：允許前後一個時間步的時鐘誤差，並拒絕重放同一步的碼。"""

    def __init__(self, key: bytes, window: int = 1):
        self.key, self.window, self.last_step = key, window, -1

    def verify(self, code: str, now: int) -> str:
        current = now // 30
        for step in range(current - self.window, current + self.window + 1):
            if hmac.compare_digest(hotp(self.key, step), code):
                if step <= self.last_step:           # 這一步（或更早）已經用過
                    return "replay"
                self.last_step = step
                return f"ok(step {step - current:+d})"
        return "invalid"


# 3. 綁定：產生 160 bit 秘密、以 base32 交給 authenticator app（通常做成 QR code）
secret = secrets.token_bytes(20)
b32 = base64.b32encode(secret).decode().rstrip("=")
uri = (f"otpauth://totp/{quote('聲聲 Live:student23')}?secret={b32}"
       f"&issuer={quote('聲聲 Live')}&algorithm=SHA1&digits=6&period=30")
print("otpauth URI 長度", len(uri), "，secret 有", len(b32), "個 base32 字元")
assert base64.b32decode(b32 + "=" * (-len(b32) % 8)) == secret

# 4. 用固定的 key 與時間示範驗證規則
v = TotpVerifier(key20)
now = 1_790_000_015
phone_slow = totp(key20, now - 30)                  # 手機時鐘慢了 30 秒
print("手機慢 30 秒 →", v.verify(phone_slow, now))
print("同一個碼再送一次 →", v.verify(phone_slow, now))
print("目前的碼 →", v.verify(totp(key20, now), now))
print("兩分鐘前的碼 →", v.verify(totp(key20, now - 120), now))
assert v.verify(totp(key20, now + 30), now) == "ok(step +1)"
```

```text
RFC 4226 HOTP counter 0-9 全部吻合
        time            T (hex)  SHA1      SHA256    SHA512
          59 0000000000000001  94287082  46119246  90693936
  1111111109 00000000023523EC  07081804  68084774  25091201
  1111111111 00000000023523ED  14050471  67062674  99943326
  1234567890 000000000273EF07  89005924  91819424  93441116
  2000000000 0000000003F940AA  69279037  90698825  38618901
 20000000000 0000000027BC86AA  65353130  77737706  47863826
otpauth URI 長度 159 ，secret 有 32 個 base32 字元
手機慢 30 秒 → ok(step -1)
同一個碼再送一次 → replay
目前的碼 → ok(step +0)
兩分鐘前的碼 → invalid
```

第一行代表 10 組 HOTP 全部吻合，`hotp()` 的動態截斷寫對了。接下來的表格與 RFC 6238 附錄 B 逐欄對照：time 是 Unix 時間，`T (hex)` 是 `floor(time / 30)` 的 16 位十六進位，三欄分別是 SHA-1、SHA-256、SHA-512 的 8 位數結果，18 個值全部通過 assert。注意 RFC 對三種 hash 使用不同長度的測試金鑰（20、32、64 bytes），這是實作時最常對不上的原因。最後一個時間點 20000000000 超過 32 bit 的範圍，`struct.pack(">Q", …)` 用 8 bytes 的計數器才算得對，用 4 bytes 的實作會在 2038 年之後出錯。

綁定那一行顯示 160 bit 的金鑰轉成 32 個 base32 字元，這正是 authenticator app 顯示「手動輸入金鑰」時那串文字的長度。最後四行是驗證規則：手機慢 30 秒送出的碼落在 step −1，被接受；同一個碼再送一次，因為 `last_step` 已經記錄，判定為重放；當下的碼在 step +0，接受；兩分鐘前的碼超出 window，拒絕。

## 26.11 在工作上怎麼用

撞庫事件結束兩週後，聲聲 Live 的登入系統依角色整理出下面的做法。

**後端工程師：先檢查框架預設值。** 很多團隊不會從零寫 session，而是用框架提供的功能，這時要確認預設值是不是符合本章的要求。以 Flask 為例，內建的 `session` 是簽章 cookie（26.5 節），適合存不敏感的狀態；要做 server-side session，可以用擴充套件或自己實作一個 session interface。不論哪種，cookie 屬性都要明確設定：

```python
# not-runnable
from datetime import timedelta
from flask import Flask

app = Flask(__name__)
app.config.update(
    SECRET_KEY=load_from_secrets_manager("flask-secret"),  # 不寫在程式碼或 git 裡
    SESSION_COOKIE_NAME="__Host-session",
    SESSION_COOKIE_SECURE=True,       # 預設 False
    SESSION_COOKIE_HTTPONLY=True,     # 預設就是 True
    SESSION_COOKIE_SAMESITE="Lax",    # 預設不送 SameSite
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),  # 預設 31 天；只在 session.permanent = True 時套用
)
```

這段設定裡的註解是最容易忽略的預設值：`Secure` 預設關閉、`SameSite` 預設不送、存活期預設 31 天。`load_from_secrets_manager` 代表你們自己的秘密管理方式（第 30 章）。登入成功時用 `session.clear()` 清掉登入前的內容再寫入身分；但簽章 cookie 沒有 server 端紀錄，這只能避免舊資料被沿用，不能撤銷已經發出去的 cookie，需要撤銷就要改用 server-side session。

**登入流程的程式碼審查清單。** Rita 要求每個動到登入、註冊、重設密碼的 PR 都對照下面的清單：

- 密碼只用 scrypt、Argon2id、bcrypt 或高迭代的 PBKDF2，salt 每帳號獨立，格式自我描述，有升級路徑。
- 所有秘密值的比較都用 `hmac.compare_digest`；帳號不存在時也做一次雜湊。
- 登入成功、完成 MFA、重新驗證之後都輪替 session ID；登出刪除 server 端紀錄。
- 同時有閒置與絕對逾時；改密碼與重設密碼後撤銷該帳號所有 session。
- 登入、MFA 驗證、重設密碼、復原碼都有限速；client IP 只從受信任的 proxy header 取得。
- 錯誤訊息不區分「帳號不存在」與「密碼錯誤」；註冊與重設流程也不洩漏帳號是否存在。
- 帶身分的回應加上 `Cache-Control: no-store`，避免被共享快取存下（第 21 章）。
- log 裡不出現密碼、session ID、重設 token、TOTP 碼；需要追查時記錄 `sha256(sid)` 的前幾碼。

**SRE：替登入系統建立專屬的指標。** 這次事故晚了將近一小時才被注意到，因為告警只看 5xx，而撞庫產生的全是 401。聲聲 Live 新增的指標是：每分鐘登入嘗試數、失敗率、相異來源 IP 數、相異嘗試帳號數、限速觸發次數（依桶子分類）、MFA challenge 次數，以及「新裝置登入成功」的數量。判斷規則可以寫成下面這樣：

```text
 登入失敗率 > 平常的 5 倍？
   │
   ├─ 相異帳號數 >> 相異 IP 數，每帳號嘗試 1～2 次 ──► 撞庫或 password spraying
   │     └─► 檢查外洩密碼比對、對成功登入加上 MFA challenge、通知 Rita
   │
   ├─ 少數帳號、大量嘗試 ──► 針對性暴力破解
   │     └─► 確認 (帳號, IP) 與帳號桶子生效；通知帳號擁有者
   │
   └─ 失敗集中在某個版本的 app 或某個地區 ──► 多半是自己的 bug（例如前端送錯欄位）
         └─► 對照部署時間與 user agent
```

這個判斷流程的第一刀是「相異帳號數」與「相異 IP 數」的比例：撞庫的特徵是帳號極多、每個帳號只試一兩次，暴力破解則相反。最後一支提醒的是：登入失敗率暴增不一定是攻擊，前端改版送錯欄位名稱也會造成一模一樣的曲線，先看 user agent 與部署時間能省下很多誤判。

**前端工程師：讓瀏覽器與密碼管理工具幫忙。** 登入表單的欄位加上正確的 `autocomplete` 屬性（`username`、`current-password`、`new-password`、`one-time-code`），手機上的 TOTP 欄位用 `inputmode="numeric"`；不要禁止貼上；收到 429 時顯示「請稍後再試」並遵守 `Retry-After`，不要自動重試。錯誤訊息照後端給的通用訊息顯示，不要自己判斷「這個 email 沒有註冊」。

**影音與即時服務：長連線也要尊重 session 的期限。** Joe 負責的教室 WebSocket（第 32 章）在連線建立時驗證一次 session，之後連線可能持續好幾個小時。如果使用者在另一個分頁登出，或者 Rita 撤銷了被接管帳號的 session，已經建立的 WebSocket 也要被關閉；聲聲 Live 的做法是即時服務訂閱「session 撤銷」事件，並在絕對逾時到達時主動送出 close frame，請 client 重新驗證。

## 26.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 部署多台 server 後，使用者每隔幾個請求就被登出 | session 存在各 process 的記憶體裡，或每台 server 的 `SECRET_KEY` 不同 | 在 log 記錄處理請求的主機與 `sha256(sid)` 前綴，看 401 是否集中在特定主機 | 使用共用的 session store；所有實例共用同一把 secret（並規劃輪替） |
| 登入 API 偶爾很慢、CPU 飆高 | 密碼雜湊參數過高，或攻擊流量讓每個請求都跑一次 scrypt | 量單次雜湊時間；看登入請求數與限速觸發次數 | 限速放在雜湊之前；調整 worker 數；參數依實測時間選擇 |
| `ValueError: memory limit exceeded` | `hashlib.scrypt` 的 `maxmem` 小於 128 × N × r | 計算 128 × N × r 是否超過 32 MiB（OpenSSL 預設上限） | 明確設定 `maxmem`；確認容器的記憶體限制足夠支撐同時進行的登入數 |
| 使用者說「明明輸入正確的 TOTP 卻被拒絕」 | 手機或 server 的時鐘偏差超過容許範圍；或同一個碼被送了兩次 | 比對 server 時間與 NTP；看 log 裡的拒絕原因是 invalid 還是 replay | server 啟用 NTP；請使用者開啟手機的自動校時；前端避免重複送出 |
| 登出後按「上一頁」還看得到個人資料 | 瀏覽器快取了帶身分的頁面 | DevTools 看該回應的 `Cache-Control` | 帶身分的回應加上 `Cache-Control: no-store` |
| 有人用登入 API 確認某個 email 是否註冊 | 錯誤訊息或回應時間依帳號是否存在而不同 | 比較兩種情況的回應內容與 p50 時間 | 通用錯誤訊息；帳號不存在時也做一次假雜湊；註冊與重設流程同樣處理 |
| 限速把整間學校或整個電信網段的使用者擋在外面 | 只依 IP 限速，而大量使用者共用 CGNAT 或學校的出口 IP | 看被擋 IP 的成功登入帳號數是否很多 | 以 (帳號, IP) 為主、IP 為輔並放寬；IPv6 以 /64 為單位；用升級驗證取代拒絕 |
| 所有登入看起來都來自同一個 IP | 限速與 log 用的是 TCP 來源位址（proxy），或盲目信任 `X-Forwarded-For` | 比對 log 中的 IP 與 LB 的位址 | 只採信受信任 proxy 加上的那一段 header（第 25 章） |
| 重設密碼的連結指向陌生網域 | 連結的網域取自請求的 `Host` header | 檢查產生連結的程式碼 | base URL 一律來自設定檔；nginx 只接受預期的 `server_name` |

除錯登入問題時有一個通則：**先確認是「驗證失敗」還是「session 失效」**。使用者說「一直被登出」與「登不進去」聽起來很像，但前者出在 session 的儲存、cookie 屬性與逾時，後者出在密碼雜湊、限速與 MFA。log 裡分別記錄「登入失敗的原因」（密碼錯、被限速、MFA 錯）與「session 無效的原因」（不存在、閒置逾時、絕對逾時、已撤銷），就能在幾分鐘內分辨。

## 26.13 動手練習

1. **量出自己機器的雜湊成本**（延伸程式）。改寫實驗一，對 ln = 14 到 18 各量 5 次 `hashlib.scrypt` 的時間，並計算每個參數的記憶體用量。挑一組讓單次雜湊落在 100 到 300 毫秒之間的參數。
   答案要點：時間與記憶體都大致隨 N 線性成長，ln 每加 1 就約略加倍；ln=17、r=8 的記憶體是 128 MiB。還要考慮同時登入的數量：如果尖峰時有 20 個登入同時進行，記憶體需求就是 20 × 128 MiB，這也是限速要放在雜湊之前的另一個理由。

2. **替實驗二加上 MFA 步驟**（延伸程式）。把實驗四的 `totp()` 與 `TotpVerifier` 搬進實驗二：密碼正確後 session 進入「mfa_pending」狀態，只能打 `/login/totp`；TOTP 驗證成功後再輪替一次 session ID 並標記為已登入。
   答案要點：要驗證三件事：mfa_pending 的 session 打 `/me` 仍是 401；TOTP 成功後 session ID 又換了一次；mfa_pending 狀態要有自己的短逾時（例如 5 分鐘）與更嚴格的限速。

3. **用 curl 觀察真實網站的 session cookie**（真實工具）。對一個你有帳號的網站，打開瀏覽器 DevTools 的 Application（或 Storage）面板，觀察登入前後 cookie 的名稱、值是否改變，以及 `Secure`、`HttpOnly`、`SameSite`、期限等屬性。也可以用 `curl -sI` 看登入頁回應的 `Set-Cookie` header。
   答案要點：多數成熟的網站登入後 session cookie 的值會改變（輪替）；記下哪些屬性有設、哪些沒設，並思考沒設的後果。只觀察自己的帳號與公開的回應 header，不要嘗試修改或重放別人的 cookie。

4. **在手機上驗證你的 TOTP 實作**（真實工具）。用實驗四的程式產生一組 base32 金鑰，在 authenticator app 裡選「手動輸入金鑰」輸入，比對 app 顯示的 6 位數與 `totp(secret, int(time.time()))` 的結果。
   答案要點：兩者應該一致；若不一致，檢查 base32 解碼時是否補回了 `=`、時間是否用整數秒、金鑰是否輸入錯誤。把手機時間手動調慢 40 秒，觀察 window = 1 時仍然接受、調慢 70 秒後被拒絕。

5. **手算限速的效果**。實驗三的 (帳號, IP) 桶子是容量 5、每 5 分鐘補 1 個。一個攻擊者只用一個 IP 猜一個帳號，一天最多能試幾次？如果攻擊者有 1,000 個 IP，但帳號桶子（容量 20、每小時補 20 個）也在作用，一天能進行幾次「不需要額外驗證」的嘗試？
   答案要點：單一 IP：5 ＋ 86,400 ÷ 300 ≈ 293 次。1,000 個 IP 時，(帳號, IP) 不再是瓶頸，帳號桶子才是：約 20 ＋ 24 × 20 ＝ 500 次，之後每次都要求 TOTP。這說明了帳號維度的必要性，也說明了為什麼一定要搭配 MFA：每天 500 次對常見密碼清單來說仍然不少。

## 本章重點整理

- Authentication 回答「你是誰」，authorization 回答「你能做什麼」；沒有或無效的憑證回 401，身分有效但沒有權限回 403，兩者顛倒會讓使用者陷入登入迴圈。
- 密碼儲存要對抗的是資料庫外洩後的離線攻擊；SHA-256 這類快速 hash 不適合存密碼，因為攻擊者每秒能嘗試的次數太多。
- Salt 是每個帳號獨立、明文存放的隨機值，讓「相同密碼相同雜湊」與預先計算的表失效；pepper 是存在資料庫以外的全站秘密，是加分項。
- scrypt 與 Argon2id 是 memory-hard 的密碼雜湊，每次嘗試都需要大量記憶體，削弱 GPU 與專用硬體的優勢；scrypt 的記憶體約為 128 × N × r bytes。
- 雜湊要用自我描述的格式存放演算法與參數；升級分兩步：離線把舊雜湊包進新演算法，使用者登入時再換成標準格式。
- 所有秘密值的比較都用 `hmac.compare_digest`；帳號不存在時也要做一次雜湊，避免回應時間洩漏帳號是否存在。
- 密碼政策以長度與外洩清單檢查為主，不強制組成規則與定期更換，並允許密碼管理工具。
- Server-side session 只把 256 bit 的隨機 ID 交給瀏覽器，store 裡存它的雜湊；它的最大優點是 server 能立即撤銷，這是簽章 cookie 做不到的。
- Session cookie 要設 `Secure`、`HttpOnly`、`SameSite`、`Path=/`、不設 `Domain`，並建議使用 `__Host-` 前綴。
- 登入成功與權限提升時都要輪替 session ID，這是防止 session fixation 的根本做法；登出必須刪除 server 端紀錄。
- Session 需要閒置逾時與絕對逾時兩者，期限只能由 server 執行；改密碼或重設密碼後要撤銷該帳號的所有 session。
- 登入限速要同時依 (帳號, IP)、IP 與帳號三個維度，用 token bucket 實作；對帳號的反應應該是升級驗證而不是硬性鎖定，避免被拿來阻斷服務。
- 分散式撞庫可以繞過所有限速，所以必須搭配外洩密碼檢查、MFA 與全站失敗率監控。
- TOTP 是 HOTP 把計數器換成時間：HMAC、動態截斷、取餘數；server 端要容許一個時間步的誤差、拒絕重放，並加密保存金鑰。
- TOTP 擋得住撞庫但擋不住即時轉送的釣魚；passkeys 把簽章綁定 origin，是防釣魚的 MFA，第 29 章詳述。
- 忘記密碼的 token 要隨機、存雜湊、短效、單次使用，回應不洩漏帳號是否存在，連結的網域取自設定而不是 `Host` header。

## 延伸問答

> [!question]- Q1. 一個已登入的學生打開 `/teachers/美咲/earnings`，API 回了 401，前端於是把學生導向登入頁；學生重新登入後又被導回來，一直循環。問題出在哪裡？
> 這是把 authorization 失敗誤報成 authentication 失敗的典型症狀。學生的 session 是有效的，server 也知道請求來自哪個學生，失敗的原因是「學生沒有權限看老師的收入」，應該回 403。前端依照慣例把 401 解讀成「尚未登入或 session 過期」，所以導向登入頁；學生重新登入後拿到新的有效 session，再打同一個 API，還是因為權限不足被拒，又回 401，就形成迴圈。
>
> 修正要在後端：驗證身分與授權判斷分成兩個步驟，前者失敗回 401、後者失敗回 403（或者對不該知道資源存在的人回 404）。前端看到 403 應該顯示「你沒有權限」而不是導向登入。除錯時可以在 log 裡把拒絕原因分類記錄，例如 `authn_failed: session_expired` 與 `authz_denied: role=student resource=earnings`，一眼就能看出是哪一種。

> [!question]- Q2. 手算：scrypt 參數 N=2^17、r=8、p=1。一張有 24 GiB 記憶體的 GPU，同時最多能平行計算幾個雜湊？和 SHA-256 相比，這代表什麼？
> scrypt 的記憶體需求約為 128 × N × r bytes＝128 × 131,072 × 8＝134,217,728 bytes，也就是 128 MiB。24 GiB 是 24 × 1,024＝24,576 MiB，除以 128 MiB 得到 192，所以這張卡最多同時平行進行約 192 個嘗試（實際還要扣掉其他用途的記憶體）。GPU 有上萬個運算單元，但在這組參數下，絕大多數會因為沒有記憶體可用而閒置；若攻擊者只給每個嘗試一部分記憶體，就要在階段二即時重算缺的區塊，時間大幅增加。
>
> SHA-256 幾乎不需要記憶體，所有運算單元都能同時工作，每秒嘗試數比 scrypt 高出好幾個數量級。這就是 memory-hard 的意義：把攻擊者的瓶頸從「算力」換成「記憶體」，而記憶體很難像算力那樣便宜地堆疊。代價是 server 自己每次登入也要用 128 MiB，所以要限制同時進行的雜湊數，並把限速放在雜湊之前。

> [!question]- Q3. Salt 明文存在雜湊旁邊，攻擊者拿到資料庫就拿到 salt，那 salt 到底保護了什麼？Pepper 又應該放在哪裡？
> Salt 不是用來保密的，它的作用是讓每個帳號的雜湊函式「都不一樣」。沒有 salt 時，攻擊者算一次 `hash("sunflower88")`，就能和整張表的所有帳號比對，也能事先把常見密碼的雜湊全部算好再查表；有了 salt，攻擊者必須針對每個帳號、用那個帳號的 salt 從頭計算，預先計算的表完全失效，相同的密碼也不再產生相同的雜湊。攻擊的總成本從「一次」變成「乘以帳號數」。
>
> Pepper 則真的需要保密，它的價值完全建立在「和資料庫存在不同地方」：例如放在 secrets manager 或 HSM，由應用程式在執行時取得，用 HMAC 把密碼與 pepper 混合後再交給 scrypt。這樣只偷到資料庫備份的攻擊者連一次有效的嘗試都做不到。缺點是輪替困難，必須保留舊 pepper 的版本號並在登入時升級，所以它是在 salt 與慢雜湊之上的額外防線，不是替代品。

> [!question]- Q4. 你在 production 看到：登入失敗率從 3% 變成 95%，相異嘗試帳號數每分鐘 8,000 個，相異 IP 數每分鐘 1,500 個，每個帳號平均只試 1.2 次。你會怎麼判斷與處理？要不要把被嘗試的帳號全部鎖住？
> 這組數字的特徵是帳號數遠多於 IP 數、每個帳號只試一次多，符合撞庫（或 password spraying）而不是針對性暴力破解。依帳號限速幾乎沒有作用，因為每個帳號都沒有超過門檻；依 IP 限速只能擋下嘗試量特別大的來源。第一步是確認不是自己的 bug（例如新版前端送錯欄位），看失敗是否集中在特定 user agent 或部署時間點；確定是攻擊後，對成功登入的請求加上額外驗證（要求 MFA，或對新裝置寄確認信），並檢查成功登入的帳號密碼是否出現在外洩清單中。
>
> 不應該把被嘗試的帳號全部鎖住。這 8,000 個帳號大多數的密碼根本沒被猜中，鎖住它們等於攻擊者幫你把正常使用者擋在門外，而且攻擊者只要拿到一份 email 清單就能重複這件事。正確的反應是「升級驗證」：被大量嘗試的帳號下次登入時要求 MFA 或 email 確認；真正登入成功的可疑帳號則撤銷所有 session、強制重設密碼並通知使用者。事後再補上外洩密碼檢查與全站失敗率告警。

> [!question]- Q5. 面試題：網頁應用的登入狀態，要用 server-side session 還是 JWT？
> 先釐清兩者的本質差異：server-side session 的 cookie 只裝一個隨機 ID，狀態在 server；JWT 是簽章過的自含式 token，狀態在 token 裡，server 驗證簽章就能知道是誰，不必查 store。JWT 常被宣傳的優點是「無狀態、好擴展」，但對一般的網頁登入來說，查一次 Redis 的成本通常不是瓶頸，而 JWT 失去的是「立即撤銷」：使用者登出、改密碼、帳號被接管時，已經發出去的 JWT 在過期前都有效，要撤銷就得再加一份 denylist，又回到了有狀態。
>
> 所以常見的答案是：同一個網域下的瀏覽器網頁應用，用 server-side session 加上設定正確的 cookie，簡單而且容易做對；需要讓多個 API、行動 app 或第三方服務驗證身分時，再用短效的 access token（可以是 JWT）配合可撤銷的 refresh token。JWT 放在哪裡、怎麼驗證、怎麼輪替金鑰是第 27 章的主題，第三方授權則是第 28 章的 OAuth。回答時把取捨說清楚，比單純選邊站更重要。

> [!question]- Q6. 手算：TOTP 是 6 位數，server 接受前後各一個時間步。攻擊者已經知道某個帳號的密碼，在沒有額外限制的情況下，每 5 分鐘能試 1 次 TOTP，一年內猜中的機率大約是多少？這告訴你什麼？
> window = 1 時，同一時刻有 3 組碼會被接受，所以每次隨機猜中的機率約為 3 ÷ 1,000,000＝3 × 10^-6。每 5 分鐘 1 次，一天是 288 次，一年約 105,000 次。猜中至少一次的機率是 1 − (1 − 3 × 10^-6)^105,000，約等於 1 − e^(−0.315)，大約 27%。即使每次都只有百萬分之三的機率，長期累積下來仍然相當可觀。
>
> 結論是 TOTP 的驗證需要比密碼更嚴格的限速，而且不能只靠「每 5 分鐘補一次」的穩定速率：例如連續失敗 5 次就讓 mfa_pending 狀態作廢、必須重新輸入密碼，同一帳號每天的 TOTP 失敗設定上限，並在連續失敗時通知使用者「有人知道你的密碼」，引導對方更換。這也說明了為什麼密碼仍然重要：TOTP 的防護是建立在攻擊者必須先通過密碼這一關之上的。

> [!question]- Q7. 看 log 找原因：聲聲 Live 把登入服務從 1 台擴展成 3 台以後，使用者回報「每點幾下就被登出」。log 顯示 `/me` 的 401 有三分之二來自 `session_not_found`。可能是什麼？怎麼確認？
> 「三分之二」這個比例是很強的線索：3 台 server 中，有 2 台不認得某個 session。最可能的原因是 session 存在各自 process 的記憶體裡（例如原本只有一台時，用的是記憶體內的 dict 或預設的本機儲存），使用者登入時落在 A 台，下一個請求被 load balancer 分到 B 或 C，就找不到 session。如果用的是簽章 cookie，同樣的症狀會出現在三台機器的 `SECRET_KEY` 不同時，log 裡會是簽章驗證失敗而不是找不到。
>
> 確認方法是在 log 裡記錄處理請求的主機名稱與 `sha256(sid)` 的前幾碼，追蹤同一個 session 的請求：如果只在登入的那台成功、在其他台都失敗，就是儲存不共用。修正是改用共用的 session store（例如 Redis），而不是開啟 LB 的 sticky session 了事；sticky session 只是把問題藏起來，任何一台重啟或縮容時，那台上的所有使用者都會被登出（第 25 章）。

> [!question]- Q8. 設計取捨：為什麼 TOTP 的金鑰不能像密碼一樣只存雜湊？這對系統設計有什麼影響？Passkeys 在這一點上有什麼不同？
> 密碼驗證只需要「重新算一次、比對結果」，server 不需要原始密碼，所以可以只存雜湊。TOTP 不一樣：驗證時 server 要用金鑰和目前時間計算 HMAC，產生「應該是哪一組數字」再比對，金鑰本身是計算的輸入，所以 server 必須能取得原值。HOTP 與 TOTP 本質上是對稱式的共享秘密：手機和 server 握著同一把金鑰。
>
> 這帶來的設計影響是：TOTP 金鑰要加密後存放，加密金鑰交給 KMS 或 HSM 管理，只有 MFA 驗證服務有權限解密，並且把解密行為記錄稽核；資料庫備份裡只有密文。即使如此，只要 MFA 服務本身被攻破，所有使用者的 TOTP 都可能被產生出來。Passkeys 使用非對稱密碼學：私鑰留在使用者的裝置或其同步的 credential manager，server 只存公鑰，公鑰外洩也無法拿來登入，這是 passkeys 除了防釣魚之外的第二個結構性優勢，第 29 章會詳細說明。

## 延伸閱讀

- RFC 4226〈HOTP: An HMAC-Based One-Time Password Algorithm〉：HOTP 的算法、動態截斷與附錄 D 的測試向量
- RFC 6238〈TOTP: Time-Based One-Time Password Algorithm〉：TOTP 的定義、時間步與重放的建議，以及附錄 B 的測試向量
- RFC 7914〈The scrypt Password-Based Key Derivation Function〉：scrypt 的規格與參數意義
- RFC 9106〈Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications〉：Argon2id 的規格
- RFC 6265〈HTTP State Management Mechanism〉（將由 6265bis 取代）：cookie 的規格
- NIST SP 800-63B〈Digital Identity Guidelines: Authentication and Lifecycle Management〉：密碼政策、MFA 與 session 的指引
- OWASP Cheat Sheet Series：Password Storage、Session Management、Authentication、Forgot Password 各篇
- Python 文件：hashlib（`scrypt`、`pbkdf2_hmac`）、hmac（`compare_digest`）、secrets
