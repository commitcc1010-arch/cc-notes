---
chapter: 29
title: OpenID Connect、SSO 與 Passkeys
part: 6
---

# 第 29 章　OpenID Connect、SSO 與 Passkeys

> [!abstract] 本章地圖
> **核心問題**：使用者在別人的系統（Google、公司的 IdP）登入，我們要怎麼安全地相信「這個人就是某某某」？又要怎麼做出一種連釣魚網站都騙不走的登入方式？
>
> **你會學到**：
> - 說清楚 OpenID Connect 在 OAuth 2.0 之上補了哪些東西（ID token、nonce、userinfo、discovery、JWKS），以及為什麼「用 OAuth 做登入」會出事
> - 畫出 OIDC 的 authorization code＋PKCE 登入時序圖，逐步驗證一個 ID token（alg、簽章、iss、aud、azp、exp、nonce、auth_time）
> - 分辨 SSO 裡的 IdP session、RP session 與 token 三層生命週期，並把 OIDC 的概念對照到 SAML
> - 設計企業 IdP 整合：多租戶設定、home realm discovery、just-in-time provisioning、帳號連結與 SCIM 停權
> - 比較 RP-initiated、front-channel、back-channel 三種 logout，知道哪一種在第三方 cookie 受限的瀏覽器裡還可靠
> - 畫出 WebAuthn 的註冊與驗證流程，解釋 challenge、origin 與 RP ID 綁定為什麼讓 passkeys 抗釣魚，並用 Python 模擬一次被擋下的釣魚登入
>
> **前置知識**：第 23 章（origin、cookie 的 SameSite 與第三方情境）、第 26 章（session cookie、TOTP）、第 27 章（JWT 結構與驗證）、第 28 章（OAuth 2.0 的角色、authorization code＋PKCE、state）

## 29.1 故事：企業 SSO 上線前的審查

聲聲 Live 簽下第一個企業客戶「北辰物流」：八百名員工可以用公司福利上語言課。合約裡有三個條件。第一，員工必須用公司帳號登入，北辰的身分系統是一套支援 OpenID Connect 的 IdP，網域是 `login.beichen.example`，聲聲 Live 不可以替這些員工另外設密碼。第二，員工離職當天就要失去存取權。第三，員工在北辰的內部入口網站按下登出時，聲聲 Live 也要一起登出。

小晴花兩天做出原型。登入按鈕把使用者導到北辰的 IdP，使用者輸入公司帳密，IdP 把瀏覽器導回 `auth.shengsheng.example/callback`，程式用授權碼向 IdP 換到一包 JSON，裡面有一個叫 `id_token` 的長字串。小晴發現把中間那段做 base64 解碼就能看到 `email`，於是用 email 查使用者：查得到就登入，查不到就建一個新帳號。示範時一切順利，北辰的窗口很滿意。

上線前，資安工程師 Rita 做了審查，在 PR 上留了三則意見。第一則：「這段程式沒有驗證簽章、iss、aud 和 nonce。任何人都能自己組一個 `email` 是北辰執行長的 token 送到 callback。」第二則：「不要用 email 當帳號的主鍵。北辰的 IdP 管理員可以改員工的 email，而且我們之後還會接其他公司的 IdP。」第三則：「登出和離職停權沒有任何處理。」Rita 還補了一句：「另外，上個月老師帳號被盜的事件，我想順便用 passkeys 解決。」

那次事件小晴也有印象：有人架了一個長得和聲聲 Live 一模一樣的網站 `shengsheng-login.example`，寄信給老師說「課酬帳戶需要重新驗證」。三位老師在假網站輸入了密碼和手機上的六位數 TOTP，假網站即時把它們轉送到真網站登入，接著改掉課酬的收款帳戶。密碼加 TOTP 的兩步驟驗證完全沒擋住。

```text
 ① 企業 SSO 原型（Rita 擋下）                     ② 老師帳號被盜（上個月）
 員工 ──► login.beichen.example（北辰 IdP）      老師 ──► shengsheng-login.example（釣魚網站）
              │ 登入成功，帶 code 導回                       │ 輸入密碼＋TOTP 六位數
              ▼                                              ▼ 攻擊者即時轉送
 auth.shengsheng.example/callback                 www.shengsheng.example（真網站）
   │ 用 code 換到 id_token                           │ 密碼對、TOTP 也對 → 登入成功
   │ ✗ 只做 base64 解碼，沒驗簽章／iss／aud／nonce   │ ✗ 伺服器分不出「是誰在輸入」
   │ ✗ 用 email 找帳號                               ▼
   ▼                                              課酬帳戶被改
 任何人都能偽造身分登入
```

這張圖把兩個問題並排。左邊的問題在**驗證身分證明**：IdP 給的 ID token 是一張有簽章的身分證明，但小晴的程式只是「讀」它，沒有「驗」它，等於把任何人遞過來的紙條都當真。右邊的問題在**驗證管道**：密碼和 TOTP 都是使用者「知道」或「看得到」的值，誰拿到都能轉交，伺服器無從分辨輸入的是老師本人，還是站在中間的釣魚網站。

這一章依序解決這兩件事：先講 OpenID Connect 怎麼在 OAuth 上加出「登入」這一層、ID token 為什麼每個欄位都要驗；再看 SSO 的多層 session、企業 IdP 整合與 logout；最後講 passkeys 怎麼讓瀏覽器替使用者檢查網址。章末的動手做會把 Rita 的意見和釣魚事件都重演一次。

## 29.2 OAuth 不是登入：OIDC 補上的那一層

第 28 章的 OAuth 2.0 解決的是**委派授權**：使用者允許某個應用程式「代替我存取某個資源」，例如允許聲聲 Live 讀取自己的 Google 日曆。應用程式拿到的 **access token** 是給 resource server（日曆 API）看的通行證，對 client 來說是不透明的字串；OAuth 規格完全沒有定義「這個 token 屬於誰」「使用者什麼時候登入的」這些問題。

早年很多網站直接拿 OAuth 當登入用：拿到 access token 後，呼叫一支「取得我的資料」API，把回來的使用者 ID 當成登入成功。這個做法有一個根本缺陷：access token 沒有綁定「發給哪個 client」。如果攻擊者經營另一個也接了同一個 IdP 的應用程式（例如一個小遊戲），使用者在那裡登入後，攻擊者手上就有一個屬於該使用者的 access token；把它送到聲聲 Live 的登入端點，聲聲 Live 呼叫 API，發現 token 有效、屬於那位使用者，就讓攻擊者以使用者身分登入。這類問題叫 **token substitution**（token 替換）：一個本來發給 A 的憑證，被拿到 B 那裡冒用。

**OpenID Connect**（OIDC）是 OpenID Foundation 制定、建在 OAuth 2.0 之上的身分層。它保留 OAuth 的角色與流程，但多定義了一份**專門寫給 client 看**的身分證明，並規定 client 怎麼驗證它。在 OIDC 的術語裡，負責驗證使用者的 authorization server 叫 **OpenID Provider**（OP，業界常稱 **IdP**，identity provider），想知道使用者是誰的 client 叫 **Relying Party**（RP，依賴方）。北辰的 `login.beichen.example` 是 IdP，聲聲 Live 是 RP。

| OIDC 加了什麼 | 它是什麼 | 解決什麼問題 | 本章位置 |
|---|---|---|---|
| `openid` scope | 授權請求帶上它，代表「我要做 OIDC 登入」 | 讓 IdP 知道要回傳 ID token | 29.3 |
| **ID token** | IdP 簽章的 JWT，寫明誰、在何時、為哪個 client 登入 | client 能自己驗證身分，不必信任某支 API 的回應 | 29.4 |
| `nonce` | client 產生的一次性隨機值，IdP 原封不動放進 ID token | 把 ID token 綁定到這一次瀏覽器登入，擋重放與注入 | 29.3、29.6 |
| **UserInfo endpoint** | 用 access token 呼叫，取得使用者的其他 claims | ID token 保持精簡，詳細資料另外拿 | 29.4 |
| **Discovery** | issuer 底下的一份 JSON metadata，列出所有端點與能力 | client 不必寫死端點；可以自動設定 | 29.5 |
| **JWKS** | IdP 公開的驗章金鑰集合 | client 能驗證簽章、IdP 能輪替金鑰 | 29.5 |
| 標準 claims 與 logout 規格 | `sub`、`email`、`auth_time`、`amr`；RP-initiated、front-channel、back-channel logout | 跨 IdP 的一致欄位與登出機制 | 29.4、29.10 |

這張表的第二列是核心。ID token 的 `aud`（audience）欄位寫著「這張證明是發給哪個 client 的」，所以前面那個 token substitution 在 OIDC 裡會被擋下：小遊戲拿到的 ID token，`aud` 是小遊戲的 client ID，聲聲 Live 一驗就知道不是給自己的。換句話說，**access token 回答「可以做什麼」，ID token 回答「是誰、給誰」**，兩者分工不同，不能互相取代。

> [!warning] 常見誤解
> 「OIDC 是 OAuth 的新版本」是錯的。OIDC 是 OAuth 2.0 之上的一層擴充，同一個 authorization server 可以同時做 OAuth 授權與 OIDC 登入。另一個常見誤解是把 ID token 當成呼叫自家 API 的 bearer token：ID token 的 `aud` 是前端 client，不是 API，API 應該收 access token（第 27、28 章）。

## 29.3 OIDC 登入流程：authorization code、PKCE 與 nonce

OIDC 定義了幾種流程，現在推薦、也是本章唯一詳細介紹的是 **authorization code flow**：瀏覽器只經手一次性的授權碼，ID token 與 access token 由 RP 的後端直接向 IdP 的 token endpoint 換取。它和第 28 章的 OAuth 流程幾乎一樣，差別是 scope 裡多了 `openid`、請求多了 `nonce`、回應多了 `id_token`。

```text
 瀏覽器                          聲聲 Live RP（auth.shengsheng.example）          北辰 IdP（login.beichen.example）
   │── ① GET /login?org=beichen ────►│                                                │
   │                                 │ 產生 state、nonce、code_verifier，存進 session │
   │◄── ② 302 Location: IdP /authorize?response_type=code&scope=openid email          │
   │        &client_id=shengsheng-live&redirect_uri=…/callback                        │
   │        &state=S&nonce=N&code_challenge=C&code_challenge_method=S256              │
   │── ③ GET /authorize?… ───────────────────────────────────────────────────────────►│
   │◄═══ ④ 登入頁：帳密、MFA（若 IdP 已有 session 就跳過）═══════════════════════════►│
   │◄── ⑤ 302 Location: …/callback?code=X&state=S&iss=… ──────────────────────────────│
   │── ⑥ GET /callback?code=X&state=S ►│                                              │
   │                                   │ 檢查 state 與 session 相符                   │
   │                                   │── ⑦ POST /token  code=X、code_verifier、 ───►│
   │                                   │        client 驗證（secret 或 private_key_jwt）│
   │                                   │◄─ ⑧ {access_token, id_token, expires_in, …} ─│
   │                                   │ 驗證 ID token（29.6 節），含 nonce == N      │
   │◄── ⑨ Set-Cookie: 聲聲 Live 的 session；302 到首頁 ─│                             │
```

逐步看。① 使用者在聲聲 Live 點「用公司帳號登入」。② RP 產生三個隨機值並存在使用者的 session：**state** 用來確認稍後回來的 callback 是這個瀏覽器發起的（擋 CSRF，第 28 章）；**nonce** 會被 IdP 寫進 ID token；**code_verifier** 是 PKCE 的祕密，送出去的只有它的雜湊 `code_challenge`。③④ 瀏覽器到 IdP 登入；如果使用者今天早上已經登入過北辰的其他系統，IdP 認得自己的 session cookie，會直接跳過登入頁，這就是 SSO 的來源（29.7 節）。

⑤ IdP 把授權碼放在 redirect 網址裡交回；支援 RFC 9207 的 IdP 還會附上 `iss` 參數，讓同時接了好幾家 IdP 的 RP 確認「這個 code 是哪一家發的」，避免 **mix-up attack**（把 A 家的 code 拿去 B 家換）。⑥⑦ RP 檢查 state 後，在後端用授權碼加上 code_verifier 向 token endpoint 換 token，同時用自己的 client 憑證證明身分。⑧ 回應裡有 `id_token`。⑨ RP 驗證通過後，才建立**自己的** session cookie（第 26 章），從此使用者和聲聲 Live 之間的關係與 IdP 無關。

三個隨機值各防一件事，混在一起很容易搞混：

| 參數 | 誰產生、存在哪 | 在哪裡被檢查 | 擋的是什麼 |
|---|---|---|---|
| `state` | RP 產生，存在瀏覽器 session | ⑥ callback 時比對 | 攻擊者把自己的授權碼塞給受害者的瀏覽器（login CSRF） |
| `code_verifier`／`code_challenge` | RP 產生 verifier，送出 challenge | ⑦ token endpoint 由 IdP 比對 | 授權碼被攔截後拿去換 token |
| `nonce` | RP 產生，存在瀏覽器 session | ⑧ 之後 RP 驗 ID token 時比對 | 舊的或別處的 ID token 被重放、注入到這次登入 |

在 code flow 裡，OIDC 規格把 nonce 列為選用，因為 PKCE 與 state 已經擋掉大部分攻擊；但只要送了 nonce，ID token 裡就必須有，而且 RP 必須比對。實務上建議一律送，成本是一個隨機字串，換來的是即使其他防線出錯，ID token 仍然綁在這一次登入上。

> [!note]
> 舊的 **implicit flow**（`response_type=id_token token`）讓 token 直接出現在瀏覽器網址的 fragment 裡，容易外洩在瀏覽紀錄與 Referer 中；OAuth 2.1 草案已經移除 implicit grant。**hybrid flow** 則混合兩者，主要見於舊系統。新系統一律用 authorization code＋PKCE。

## 29.4 ID token：一張寫給 client 的身分證明

ID token 是一個 JWT（第 27 章）：三段 base64url 字串，用點分隔，依序是 header、payload（claims）與簽章。下圖是北辰 IdP 發給聲聲 Live 的 ID token 解開之後的樣子：

```text
 eyJhbGciOiJFUzI1NiIs… . eyJpc3MiOiJodHRwczovL2xvZ2lu… . kTq0W3…（64 bytes 的 ES256 簽章）
 └──────── header ─────┘ └──────────── payload ──────────┘ └──────── signature ─────────┘
           │                          │                                 │
           ▼                          ▼                                 ▼
 {"alg": "ES256",          {"iss": "https://login.beichen.example",    ECDSA P-256＋SHA-256
  "kid": "es-2026-09",      "sub": "e-20931",                           簽在「header.payload」
  "typ": "JWT"}             "aud": "shengsheng-live",                   這串 ASCII 上
                            "exp": 1790000300, "iat": 1790000000,
  kid 指向 JWKS 裡           "auth_time": 1789999980,
  的哪一把公鑰               "nonce": "n-0S6_WzA2Mj",
                            "amr": ["pwd", "mfa"],
                            "at_hash": "7ACodrWhCDH4cc_El5ALkA",
                            "email": "mei.lin@beichen.example",
                            "email_verified": true}
```

header 告訴你用什麼演算法簽、用哪一把金鑰（`kid`）。payload 是一組 **claims**（宣告，也就是 key-value 的欄位）。簽章蓋住的是 header 與 payload 的 base64url 字串本身，所以任何一個字元被改，簽章就對不上。注意 payload **沒有加密**，任何人拿到都能解開來看，所以 ID token 裡不該放機密資料，也不能因為「解得開」就相信它。

| claim | 意思 | RP 怎麼用 |
|---|---|---|
| `iss` | issuer，發行者的識別字串（一個 https 網址） | 必須和設定值逐字相同 |
| `sub` | subject，IdP 內部替這個使用者取的穩定 ID | 和 `iss` 合起來當帳號主鍵 |
| `aud` | audience，這張證明給哪個 client（字串或陣列） | 必須包含自己的 client ID |
| `azp` | authorized party，實際取得 token 的 client | `aud` 有多個值時必須是自己 |
| `exp`／`iat` | 到期時間、發行時間（Unix 秒） | 過期就拒絕；`iat` 不能在未來 |
| `nonce` | 授權請求時 RP 送出的值 | 必須等於 session 裡存的那一個 |
| `auth_time` | 使用者實際輸入憑證的時間 | 敏感操作要求最近登入過（`max_age`） |
| `acr`／`amr` | 驗證強度等級、用了哪些方法（例如 `pwd`、`mfa`、`hwk`） | 依政策要求 MFA；值的意義依 IdP 而定 |
| `at_hash` | access token 雜湊的左半段 | 確認 access token 和 ID token 是同一批發的 |
| `email`、`email_verified`、`name` | 個人資料類 claims | 顯示用；不能當主鍵 |

`sub` 值得多說兩句。它在同一個 IdP 內**永遠不變也不重複**，但只在那個 `iss` 底下有意義：北辰的 `e-20931` 和 Google 的 `e-20931` 是兩個人。所以帳號主鍵是 `(iss, sub)` 這一對，不是 email。email 可以被改、可以被回收再分配給新員工，部分 IdP 甚至允許租戶管理員填入未經驗證的 email。有些 IdP 還支援 **pairwise subject**：同一個人對不同 RP 給出不同的 `sub`，讓 RP 之間無法串聯使用者，這也是不要假設 `sub` 跨 RP 相同的理由。

除了 ID token，RP 還可以拿 access token 呼叫 **UserInfo endpoint**，取得 ID token 裡沒放的 claims（例如部門、電話）。UserInfo 的回應通常是一般的 JSON，可信度來自 TLS 與 access token；規格要求 RP 確認回應裡的 `sub` 和 ID token 的 `sub` 相同，避免拿到別人的資料。登入本身只需要 ID token，要更多資料才呼叫 UserInfo。

下面這段程式組出上圖的 token，再把它拆開，讓你看清楚三段的長度與內容，也示範 `at_hash` 的算法。簽章部分只放了佔位用的 bytes，因為本段只看結構：

```python
import base64
import hashlib
import json


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


access_token = "SlAV32hkKG-beichen-at-7731"
# at_hash：access token 的 SHA-256 取左半（16 bytes）再 base64url，把兩個 token 綁在一起
at_hash = b64url(hashlib.sha256(access_token.encode()).digest()[:16])

header = {"alg": "ES256", "kid": "es-2026-09", "typ": "JWT"}
claims = {"iss": "https://login.beichen.example", "sub": "e-20931", "aud": "shengsheng-live",
          "exp": 1790000300, "iat": 1790000000, "auth_time": 1789999980,
          "nonce": "n-0S6_WzA2Mj", "amr": ["pwd", "mfa"], "at_hash": at_hash,
          "email": "mei.lin@beichen.example", "email_verified": True}
# 簽章部分在這裡只放佔位用的 bytes：本段只看結構，驗證在 29.13 節
token = ".".join([b64url(json.dumps(header, separators=(",", ":")).encode()),
                  b64url(json.dumps(claims, separators=(",", ":")).encode()),
                  b64url(b"\x00" * 64)])

h64, p64, s64 = token.split(".")
print(f"token 長度 {len(token)} 字元，三段長度 {len(h64)} / {len(p64)} / {len(s64)}")
print("header :", json.loads(b64url_decode(h64)))
payload = json.loads(b64url_decode(p64))
for name in ("iss", "sub", "aud", "nonce", "amr", "at_hash"):
    print(f"  {name:<8} = {payload[name]}")
print("簽章   :", len(b64url_decode(s64)), "bytes（ES256：r、s 各 32 bytes）")
# 解得開不等於可信：任何人都能做出一段「解得開」的 payload。這一步只能用來除錯。
assert payload["at_hash"] == b64url(hashlib.sha256(access_token.encode()).digest()[:16])
```

```text
token 長度 510 字元，三段長度 62 / 360 / 86
header : {'alg': 'ES256', 'kid': 'es-2026-09', 'typ': 'JWT'}
  iss      = https://login.beichen.example
  sub      = e-20931
  aud      = shengsheng-live
  nonce    = n-0S6_WzA2Mj
  amr      = ['pwd', 'mfa']
  at_hash  = 7ACodrWhCDH4cc_El5ALkA
簽章   : 64 bytes（ES256：r、s 各 32 bytes）
```

第一行顯示一個帶十幾個 claims 的 ID token 大約五百字元，中間的 payload 最長；ES256 的簽章是 64 bytes，base64url 後是 86 字元。如果 IdP 改用 RS256 搭配 2048 位元的 RSA 金鑰，光簽章就是 256 bytes、342 字元，整個 token 會超過七百字元，所以 ID token 不適合塞進每個請求的 header 裡傳來傳去。北辰的 IdP 和第 27 章聲聲 Live 自己的 issuer 一樣用 ES256，kid 也恰好採用相同的 `es-年-月` 命名；但 kid 只在各自 issuer 的 JWKS 裡有意義，兩邊的 `es-2026-09` 是不同的金鑰。`at_hash` 是把 access token 做 SHA-256、取前 16 bytes 再 base64url，讓 RP 能確認手上的 access token 與 ID token 出自同一次發行。最後一行的註解是小晴原型的根本錯誤：這段程式也「成功解出」了一個完全沒有有效簽章的 token。解碼只能用來除錯，信任必須來自驗證。

## 29.5 Discovery 與 JWKS：從 issuer 找到一切

RP 要驗證 ID token，至少要知道 IdP 的 authorization endpoint、token endpoint、驗章公鑰在哪裡。早年這些都靠人工設定，換一個端點就要改程式。**OpenID Connect Discovery** 規定：IdP 把這些資訊放在「issuer 後面接 `/.well-known/openid-configuration`」這個固定路徑的 JSON 文件裡，RP 只要設定 issuer 一個值，其他都能自動找到。

```text
 RP 只設定一個值：issuer = https://login.beichen.example
   │
   │ ① GET {issuer}/.well-known/openid-configuration
   ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ {"issuer": "https://login.beichen.example",   ← 必須與設定值逐字相同  │
 │  "authorization_endpoint": ".../authorize",                            │
 │  "token_endpoint": ".../token",                                        │
 │  "userinfo_endpoint": ".../userinfo",                                  │
 │  "jwks_uri": ".../jwks.json",                 ─────────┐               │
 │  "end_session_endpoint": ".../logout",                 │               │
 │  "id_token_signing_alg_values_supported": ["RS256", "ES256"], …}       │
 └────────────────────────────────────────────────────────┼───────────────┘
                                                          │ ② GET jwks_uri
                                                          ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ {"keys": [ {"kid": "es-2026-09", "kty": "EC", "crv": "P-256", "alg": "ES256", "x": …, "y": …},
 │            {"kid": "es-2026-10", "kty": "EC", "crv": "P-256", "alg": "ES256", "x": …, "y": …} ]}
 └────────────────────────────────────────────────────────────────────────┘
   ③ 收到 ID token：讀 header 的 kid → 在快取的 JWKS 裡找對應公鑰 → 驗簽章
```

① RP 啟動時（或定期）抓 discovery 文件。文件裡的 `issuer` 必須和 RP 設定的值完全一樣，這條規則擋的是「有人在路徑上替換了 metadata，把端點指到別處」，以及多 IdP 環境下的混淆。② 依 `jwks_uri` 抓 **JWKS**（JSON Web Key Set），裡面每一把金鑰用 **JWK** 格式表示：EC 公鑰是曲線名稱 `crv` 加上座標 `x`、`y`，RSA 公鑰則是模數 `n` 與指數 `e`。③ 驗證 ID token 時，用 header 的 `kid` 找到對應的那一把。

JWKS 是一個集合，原因是**金鑰輪替**：IdP 要定期換簽章金鑰，但換的那一刻，世界上還有大量用舊金鑰簽的 token 尚未過期，而各個 RP 也還快取著舊的 JWKS。正確的輪替是三個階段：

```text
 時間 ─────────────────────────────────────────────────────────────────────────►
 JWKS 內容   [es-2026-09]   [es-2026-09, es-2026-10]     [es-2026-09, es-2026-10]   [es-2026-10]
 簽章用      es-2026-09     es-2026-09                   es-2026-10                 es-2026-10
                            （新鑰只發布、不使用）
             │              │                            │                          │
             │        ① 發布新公鑰                ② 等所有 RP 的快取都更新後      ③ 舊 token 全部過期後
             │           （等待 ≥ RP 快取時間）       才開始用新鑰簽章              才移除舊公鑰
```

① 先把新公鑰加進 JWKS，但暫時不用它簽章，等待的時間至少要超過 RP 一般的快取時間。② 確定 RP 都看得到新鑰之後，才改用新鑰簽章。③ 等舊鑰簽出的最後一批 token 也過期，才把舊公鑰移除。RP 這一側的對應策略是：平常用快取，遇到不認得的 `kid` 才重抓一次，而且重抓要有冷卻時間，否則攻擊者只要送大量填了亂數 `kid` 的 token，就能讓你的服務狂打 IdP。下面的程式模擬這個快取，也故意讓 IdP 犯一個錯：新鑰一發布就立刻拿來簽章。

```python
import json

ISSUER = "https://login.beichen.example"

# 模擬 IdP 對外公開的兩份文件：discovery metadata 與 JWKS（金鑰集合）
DISCOVERY = {
    "issuer": ISSUER,
    "authorization_endpoint": ISSUER + "/authorize",
    "token_endpoint": ISSUER + "/token",
    "userinfo_endpoint": ISSUER + "/userinfo",
    "jwks_uri": ISSUER + "/jwks.json",
    "end_session_endpoint": ISSUER + "/logout",
    "id_token_signing_alg_values_supported": ["RS256", "ES256"],
    "scopes_supported": ["openid", "profile", "email", "offline_access"],
}
idp_keys = {"keys": [{"kid": "es-2026-09", "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig"}]}


class JwksCache:
    """RP 端的 JWKS 快取：平常用快取；遇到不認得的 kid 才重抓，而且有冷卻時間。"""

    def __init__(self, fetch, refetch_cooldown=60):
        self.fetch, self.cooldown = fetch, refetch_cooldown
        self.keys, self.last_fetch, self.fetch_count = {}, None, 0

    def _refresh(self, now):
        self.keys = {k["kid"]: k for k in self.fetch()["keys"]}
        self.last_fetch, self.fetch_count = now, self.fetch_count + 1

    def key_for(self, kid, now):
        if kid in self.keys:
            return self.keys[kid]
        # 不認得的 kid：可能是 IdP 剛輪替金鑰，也可能是亂填的 token。
        # 冷卻時間內不重抓，避免攻擊者用大量假 kid 讓我們狂打 IdP。
        if self.last_fetch is None or now - self.last_fetch >= self.cooldown:
            self._refresh(now)
        return self.keys.get(kid)


# 啟動時先讀 discovery，並確認 issuer 和我們設定的完全一致（防止 IdP 混淆）
meta = json.loads(json.dumps(DISCOVERY))  # 模擬從 HTTP 取回並解析 JSON
assert meta["issuer"] == ISSUER, "discovery 裡的 issuer 必須和設定值逐字相同"
print("jwks_uri =", meta["jwks_uri"])

cache = JwksCache(fetch=lambda: idp_keys)
t = 0
print(f"t={t:>4}s kid=es-2026-09 → {cache.key_for('es-2026-09', t)['kid']}（抓 {cache.fetch_count} 次）")

# IdP 輪替金鑰：新金鑰一加進 JWKS 就立刻拿來簽 token（不理想的做法，下面會看到後果）
idp_keys["keys"].append({"kid": "es-2026-10", "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig"})
t = 30
print(f"t={t:>4}s kid=es-2026-10 → {cache.key_for('es-2026-10', t)}（冷卻中，不重抓；抓 {cache.fetch_count} 次）")
t = 90
print(f"t={t:>4}s kid=es-2026-10 → {cache.key_for('es-2026-10', t)['kid']}（重抓後找到；抓 {cache.fetch_count} 次）")
for i in range(3):
    t += 1
    found = cache.key_for(f"bogus-{i}", t)
    assert found is None
print(f"t={t:>4}s 連續 3 個假 kid → 都拒絕（仍只抓 {cache.fetch_count} 次）")
assert cache.fetch_count == 2
```

```text
jwks_uri = https://login.beichen.example/jwks.json
t=   0s kid=es-2026-09 → es-2026-09（抓 1 次）
t=  30s kid=es-2026-10 → None（冷卻中，不重抓；抓 1 次）
t=  90s kid=es-2026-10 → es-2026-10（重抓後找到；抓 2 次）
t=  93s 連續 3 個假 kid → 都拒絕（仍只抓 2 次）
```

前兩行是正常情況：啟動時抓一次 JWKS，之後用快取。第三行就是 IdP 犯錯的後果：新鑰發布後 30 秒就有用它簽的 token 到達，RP 雖然不認得這個 `kid`，但距離上次抓取還在 60 秒冷卻期內，於是拒絕，使用者這時會看到登入失敗。第四行冷卻結束、重抓後找到新鑰。最後一行顯示冷卻機制的價值：三個亂填的 `kid` 沒有觸發任何額外抓取。實務上 RP 也應該依 JWKS 回應的 `Cache-Control` 設定快取時間，讓 IdP 有辦法控制輪替的節奏。

## 29.6 ID token 驗證的完整步驟

有了 ID token 和公鑰，RP 要做的檢查可以排成一條固定的管線。順序有道理：先確認「這張紙條是真的」（演算法與簽章），才去讀紙條上寫什麼（iss、aud、時間），最後確認「這張紙條屬於這一次登入」（nonce）。任何一步失敗就整體拒絕，不要「大部分通過就好」。

```text
 收到 id_token
   │
   ├─① 切成三段、解 header ─────────── 格式錯 ─────────────────────────► 拒絕
   ├─② alg 是否在允許清單？（由 RP 設定，例如只允許 ES256）── 否（含 none）─► 拒絕
   ├─③ 用 kid 從 JWKS 取公鑰，驗簽章 ── 找不到金鑰／簽章不符 ─────────────► 拒絕
   ├─④ iss == 設定的 issuer（逐字）？ ── 否 ────────────────────────────► 拒絕
   ├─⑤ aud 包含我的 client_id？多個 aud 時 azp == 我？ ── 否 ──────────────► 拒絕
   ├─⑥ exp > now − leeway？iat <= now + leeway？ ── 否 ─────────────────► 拒絕
   ├─⑦ 有要求 max_age：now − auth_time <= max_age？ ── 否 ──────────────► 要求重新登入
   ├─⑧ nonce == session 裡這次登入的值？用完即刪 ── 否 ─────────────────► 拒絕
   └─⑨ （依政策）acr／amr 是否符合？例如必須有 mfa ─── 否 ─────────────► 要求加強驗證
   ▼
 以 (iss, sub) 找到或建立帳號 → 建立 RP 自己的 session
```

逐步說明幾個關鍵點。② 的「允許的演算法」是 RP 事先決定的，不能照 token header 說的去驗；否則攻擊者只要把 header 改成 `alg: none`（不簽章），或把 RS256 改成 HS256 並拿公開的公鑰當 HMAC 金鑰（演算法混淆），寫得不好的函式庫就會放行，這是第 27 章講過的經典錯誤。③ 簽章比對要用常數時間比較。④ 的「逐字」包括結尾斜線：issuer 字串後面多一個 `/`，就是另一個 issuer。

⑤ 是擋 token substitution 的關鍵：北辰的報帳系統也接了同一個 IdP，它收到的 ID token `aud` 是報帳系統，聲聲 Live 必須拒絕。⑥ 的 **leeway** 是容忍兩台機器時鐘不完全同步的誤差，通常設幾十秒到幾分鐘，不能設成幾小時。⑦ 用在敏感操作，例如修改課酬帳戶前，依第 26 章的政策要求使用者在 10 分鐘內實際輸入過憑證，RP 在授權請求帶 `max_age=600`，再檢查 `auth_time`。⑧ 的 nonce 要**用完即刪**，同一個 token 第二次出現就失敗。

| 漏掉的步驟 | 會發生什麼 | 例子 |
|---|---|---|
| 不驗簽章（只 base64 解碼） | 任何人都能組出任意身分 | 小晴的原型 |
| 不固定 alg | `none` 或 HS256／RS256 混淆被放行 | header 改成 `none` 的 token 直接通過 |
| 不驗 iss | 別的 IdP（甚至攻擊者自架的 IdP）發的 token 被接受 | 多租戶系統中 A 公司的 token 登入 B 公司的租戶 |
| 不驗 aud／azp | 發給別的應用的 ID token 被拿來登入 | 報帳系統收到的 token 被轉送到聲聲 Live |
| 不驗 exp | 外洩的舊 token 永遠有效 | log 裡撈到的 token 一週後仍能登入 |
| 不驗 nonce | ID token 可以被重放或注入到別人的登入流程 | 同一個 token 送兩次都成功 |
| 用 email 當主鍵 | email 被改或被回收後，帳號落到別人手上 | 新員工拿到離職同事的舊 email，登入看到對方的課程紀錄 |

> [!tip]
> 實務上不要自己寫 ID token 驗證，要用成熟的 OIDC 函式庫，並把上面九個步驟當成**驗收清單**：逐項確認函式庫有做、設定有開。OIDC 規格還允許一個例外：ID token 是 RP 透過 TLS 直接從 token endpoint 取得時，可以用 TLS 的伺服器驗證取代簽章驗證。但 token 之後常被存下或轉交給其他元件，一律驗簽章是比較穩妥的預設。

## 29.7 SSO：一次登入與多層 session

**SSO**（Single Sign-On，單一登入）的意思是：使用者登入一次，就能進入多個應用程式。北辰的員工早上登入公司入口網站後，點開報帳系統、請假系統、聲聲 Live，都不必再輸入密碼。SSO 不是什麼特別的協定，它是 29.3 節流程第 ④ 步的副作用：IdP 自己也有 session cookie，第二個應用程式把使用者導過來時，IdP 認得這個 cookie，就直接發授權碼。

```text
 瀏覽器                       報帳系統 RP              聲聲 Live RP                北辰 IdP
   │ 08:55 登入入口網站 ──────────────────────────────────────────────────────────►│ 輸入帳密＋MFA
   │◄─────────────────────────────────── Set-Cookie: idp_session（login.beichen.example）
   │                                                                              │
   │ 09:10 打開報帳系統 ────►│ 302 → IdP /authorize                               │
   │── /authorize（帶 idp_session）──────────────────────────────────────────────►│ 認得 session
   │◄──────────────────────── 302 → 報帳 /callback?code=… ────────────────────────│ 不顯示登入頁
   │──►│ 換 token、建立報帳的 session                                              │
   │                                                                              │
   │ 19:30 打開聲聲 Live ─────────────────────────►│ 302 → IdP /authorize          │
   │── /authorize（帶 idp_session）──────────────────────────────────────────────►│ 認得 session
   │◄──────────────────────────────────────────────── 302 → 聲聲 /callback?code=… │
   │──────────────────────────────────────────────►│ 驗 ID token、建立聲聲的 session
```

08:55 員工在 IdP 輸入帳密與 MFA，IdP 在自己的網域設下 `idp_session`。09:10 打開報帳系統，報帳系統沒有這個人的 session，就把瀏覽器導到 IdP；瀏覽器自動帶上 `idp_session`，IdP 直接回授權碼，使用者只看到畫面閃了一下。19:30 打開聲聲 Live 也一樣。每個 RP 拿到的 ID token `aud` 各不相同，`sub` 則在同一個 IdP 下一致（除非用 pairwise）。

這張圖也揭露了 SSO 最重要的性質：**session 不只一個**。這一刻，瀏覽器裡至少有三種彼此獨立的登入狀態，各有各的到期時間與撤銷方法：

```text
 ┌─ 第 1 層：IdP session（login.beichen.example 的 cookie）──────────────────────────────┐
 │  北辰的政策：工作日 10 小時；IdP 管理員可以停權、強制登出                              │
 │                                                                                         │
 │   ┌─ 第 2 層：RP session（各應用自己的 cookie）────────────────────────────────────┐   │
 │   │  報帳系統：閒置 15 分鐘      聲聲 Live：閒置 30 分鐘、最長 12 小時（第 26 章）  │   │
 │   │                                                                                 │   │
 │   │   ┌─ 第 3 層：token（給 API 用）──────────────────────────────────────────────┐ │   │
 │   │   │  access token 5 分鐘（JWT，到期前無法撤銷）；refresh token 可撤銷與輪替   │ │   │
 │   │   └───────────────────────────────────────────────────────────────────────────┘ │   │
 │   └─────────────────────────────────────────────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

圖畫成巢狀，但真實的關係並不是巢狀：外層結束時，內層**不會**自動結束。IdP session 過期了，聲聲 Live 的 session 還活著，使用者繼續上課不受影響；反過來，聲聲 Live 的 session 過期了，只要 IdP session 還在，使用者按「登入」就會無聲地回來。下表整理三層的差異，這是理解 29.10 節 logout 難題的基礎：

| 層 | 存在哪裡 | 誰決定壽命 | 怎麼結束 | 結束後的效果 |
|---|---|---|---|---|
| IdP session | IdP 網域的 cookie＋IdP 的 session 儲存 | IdP（企業政策） | 使用者在 IdP 登出、管理員停權、到期 | 之後的新登入要重新輸入憑證；**已存在的 RP session 不受影響** |
| RP session | RP 網域的 cookie＋RP 的 session 儲存（第 26 章） | RP | RP 登出、到期、收到 back-channel logout | 這個應用登出；再按登入可能被 IdP 無聲帶回 |
| access token | client 記憶體或 BFF 後端 | 發行者（authorization server） | 到期；self-contained JWT 中途通常無法撤銷 | API 呼叫失敗，需要用 refresh token 換新 |
| refresh token | BFF 後端或安全儲存 | authorization server | 撤銷、輪替、到期 | 無法再換新的 access token |

RP 可以在授權請求加參數來控制 IdP 那一層的行為：`prompt=login` 強制重新輸入憑證、`prompt=none` 只在 IdP 已有 session 時無聲完成（沒有就回錯誤 `login_required`，不顯示任何畫面）、`max_age` 要求最近登入過、`login_hint` 預先填入帳號。過去 SPA 常在隱藏的 iframe 裡用 `prompt=none` 做「無聲續期」，但 iframe 裡的 IdP 是第三方情境，在封鎖或分區第三方 cookie 的瀏覽器裡帶不到 `idp_session`，這個技巧已經不可靠，改由 refresh token 或 BFF 模式處理（29.13 節）。

## 29.8 SAML：企業世界的前輩

很多企業 IdP 在 OIDC 出現前就已經用 **SAML 2.0**（Security Assertion Markup Language，OASIS 在 2005 年發布的標準）做 SSO。接企業客戶時，你很可能聽到「我們只支援 SAML」。好消息是，概念幾乎一一對應：

| 概念 | OIDC | SAML 2.0 |
|---|---|---|
| 驗證使用者的一方 | OpenID Provider（IdP） | Identity Provider（IdP） |
| 依賴身分的一方 | Relying Party（RP） | Service Provider（SP） |
| 身分證明 | ID token（JWT，JSON） | Assertion（XML，放在 Response 裡） |
| 簽章 | JWS，金鑰在 JWKS | XML Signature，憑證在 metadata XML |
| 使用者識別 | `sub` | `NameID`（可能是持久 ID、email 或暫時 ID） |
| 給誰 | `aud` | `AudienceRestriction` 裡的 SP EntityID |
| 有效期間 | `exp`、`iat` | `NotBefore`、`NotOnOrAfter` |
| 綁定這一次請求 | `nonce`、`state` | `InResponseTo`（對應 AuthnRequest 的 ID）、`RelayState` |
| 回傳路徑 | `redirect_uri` | ACS（Assertion Consumer Service）URL |
| 自動設定 | Discovery JSON | metadata XML |
| 傳遞方式 | 授權碼經瀏覽器，token 走後端 | Assertion 本身經瀏覽器以表單 POST 送達 SP |

最後一列是兩者在網路行為上最大的差別。SAML 最常見的 Web Browser SSO 流程裡，IdP 驗證完使用者後，回傳一個會自動送出的 HTML 表單，把整份簽過章的 XML Response 透過瀏覽器 POST 到 SP 的 ACS URL，沒有「後端換 token」這一步：

```text
 瀏覽器                                   聲聲 Live（SP）                         北辰 IdP
   │── ① GET /sso/saml?org=beichen ─────────►│                                      │
   │◄── ② 302 → IdP?SAMLRequest=<AuthnRequest ID=_a91>（HTTP-Redirect binding）&RelayState=R
   │── ③ GET /sso?SAMLRequest=… ───────────────────────────────────────────────────►│ 登入
   │◄── ④ HTML：<form method=POST action=ACS> SAMLResponse=<簽章的 XML> RelayState=R ─│
   │── ⑤ POST /saml/acs（瀏覽器自動送出表單）►│                                      │
   │                                          │ 驗 XML 簽章、Issuer、Audience、       │
   │                                          │ Destination、時間、InResponseTo=_a91、│
   │                                          │ Assertion ID 只能用一次               │
   │◄── ⑥ Set-Cookie：聲聲 Live 的 session ───│                                      │
```

② SP 產生 AuthnRequest 並記下它的 ID。④ IdP 回傳自動送出的表單；⑤ 瀏覽器把 assertion 送到 ACS。SP 要做的驗證和 29.6 節同一個精神：簽章、發行者、受眾、時間、是否對應自己發出的請求、是否重放。SAML 特有的風險來自 XML：**XML signature wrapping** 是指文件裡同時有一個被簽章的元素和一個沒被簽章的元素，程式驗了前者、讀了後者；XML 解析器也要關掉外部實體等危險功能。另外，SAML 支援 **IdP-initiated SSO**（使用者從 IdP 入口直接點進 SP，沒有 AuthnRequest），此時沒有 `InResponseTo` 可以比對，更容易被重放或注入，能不開就不開。

給 junior 的實務建議是：**不要自己解析 SAML**。使用維護良好的函式庫或身分平台，讓它把 SAML 轉成你的 session；如果平台能同時接 SAML 與 OIDC，對內統一用 OIDC 的概念處理，可以少維護一套驗證邏輯。

## 29.9 企業 IdP 整合：多租戶、JIT provisioning 與 SCIM

接一家 IdP 是設定問題，接十家就是架構問題。北辰之後，聲聲 Live 預計還會有其他企業客戶，各自有自己的 IdP。Rita 和阿德把需求整理成四件事：找到該去哪家 IdP、每家 IdP 的設定隔離、第一次登入時建立帳號、離職時停權。

**第一件事：home realm discovery**（找到使用者的「家」）。登入頁只放一個 email 欄位，使用者輸入 `mei.lin@beichen.example`，系統依網域 `beichen.example` 查到這是北辰租戶，把使用者導到北辰的 IdP；查不到就走一般的密碼或 passkey 登入。這裡有一個陷阱：誰能宣稱「`beichen.example` 是我的」？如果任何租戶管理員都能自己填網域，攻擊者就能宣稱別人的網域，把該網域的使用者導到自己的 IdP。正確做法是要求租戶用 DNS TXT 紀錄證明網域所有權（第 16 章的網域驗證），驗證通過才啟用。

```text
 使用者輸入 email ── mei.lin@beichen.example
   │
   ├─ 網域 beichen.example 是否屬於某個「已驗證網域」的租戶？
   │     ├─ 是：讀取租戶設定 ─► issuer、client_id、client 驗證方式、允許的 acr、群組→角色對應
   │     │        └─► 導到該 IdP（29.3 節流程）─► callback：用「該租戶的」issuer 驗 ID token
   │     └─ 否：一般登入（密碼＋TOTP 或 passkey，第 26 章、29.11 節）
   │
   └─ callback 驗證通過 ─► 以 (iss, sub) 查帳號
          ├─ 找到：登入，順便更新姓名、群組等可變資料
          └─ 找不到：JIT provisioning ─► 在該租戶下建立帳號，角色依群組對應，預設最小權限
```

**第二件事：設定隔離**。每個租戶的 issuer、client ID、金鑰、redirect URI 都要分開存放，callback 驗證時要用「這次登入流程開始時選定的那個租戶」的 issuer，而不是「token 自己說的 iss」。這是多 IdP 版本的 29.6 節第 ④ 步：如果你接受任何一家已設定 IdP 的 token 進入任何租戶，A 公司的 IdP 管理員就能替 B 公司的員工簽發 token。有些 IdP 的多租戶端點，不同租戶的 issuer 字串不同，驗證時也要依租戶個別比對。

**第三件事：just-in-time provisioning**（JIT，即時建立帳號）。員工第一次透過 SSO 登入時，RP 依 ID token 的 claims 當場建立帳號，不必事先匯入名單。它簡單、好上線，但有兩個要小心的地方。一是**帳號連結**：如果聲聲 Live 已經有一個用 `mei.lin@beichen.example` 註冊的個人帳號，不能因為 email 相同就自動合併，除非該租戶的網域已驗證、而且 IdP 宣告 `email_verified`；更穩妥的做法是要求使用者先用原本的方式登入舊帳號，再主動連結。二是**權限**：從 `groups` claim 對應角色時，預設給最小權限，IdP 裡誰被加進哪個群組，就等於在你的系統裡授權。

**第四件事：停權**。JIT 只在「登入時」有機會更新資料，員工離職、IdP 停用帳號後，如果那個人不再登入，聲聲 Live 根本不會知道。而且已經存在的聲聲 Live session 不受 IdP 停權影響（29.7 節的分層）。解法是 **SCIM**（System for Cross-domain Identity Management，RFC 7643 與 7644）：IdP 主動透過 REST API 對 RP 建立、更新、停用使用者。北辰停用員工帳號時，IdP 送一個把 `active` 設成 false 的請求，聲聲 Live 收到後停用帳號、刪除所有 session、撤銷 refresh token。

| 機制 | 何時同步 | 優點 | 缺點 |
|---|---|---|---|
| JIT provisioning | 使用者登入時 | 不必事先匯入；設定簡單 | 不登入就不更新；無法得知離職 |
| SCIM | IdP 端有變動就推送 | 建立、更新、停權都即時 | RP 要實作並保護 SCIM API；設定較複雜 |
| 定期重新驗證 | RP 每隔一段時間強制走一次 IdP | 不必額外 API；停權最晚在週期內生效 | 有延遲；使用者偶爾要多跳轉一次 |
| back-channel logout | IdP 端 session 結束時 | 登出能即時傳到 RP | 只處理「登出」，不處理帳號屬性 |

合約裡「離職當天失去存取」的條件，最後的設計是三者並用：SCIM 負責停權，RP session 最長 12 小時並在到期時重新走 IdP（即使 SCIM 出問題，最晚隔天也會失效），back-channel logout 負責即時登出。

## 29.10 Logout：最難的一步

合約的第三個條件「北辰入口網站按登出，聲聲 Live 也要登出」聽起來很簡單，卻是 SSO 裡最難做對的部分。回顧 29.7 節的三層 session：使用者按下登出時，至少有三個問題要回答。只清掉聲聲 Live 自己的 session 嗎？要不要也結束北辰 IdP 的 session？同一個 IdP 底下的其他 RP（報帳系統）要不要一起登出？每一個「要」，都需要一條訊息從某個系統傳到另一個系統，而這些系統分屬不同網域、不同公司。

最簡單的是**本地登出**：聲聲 Live 刪除自己的 session。問題是 IdP session 還在，使用者按「登入」會被無聲地帶回去，在共用電腦上這很危險，使用者也會困惑「我明明登出了」。進一步是 **RP-initiated logout**：聲聲 Live 刪掉自己的 session 後，把瀏覽器導到 discovery 裡的 `end_session_endpoint`，帶上 `id_token_hint`（讓 IdP 知道是誰要登出）與 `post_logout_redirect_uri`，IdP 結束自己的 session 後再導回來。這解決了「無聲帶回」，但報帳系統的 session 仍然活著。

要讓 IdP 通知所有 RP，OIDC 定義了兩種做法：

- **Front-channel logout**：IdP 的登出頁面為每個 RP 嵌一個隱藏的 iframe，載入 RP 註冊的登出網址，RP 在 iframe 裡讀到自己的 session cookie 並清除。它全程經過瀏覽器，RP 不需要對外開放後端端點。但 iframe 裡的 RP 是第三方情境：Safari 封鎖第三方 cookie、Firefox 依頂層網站分區、Chrome 也提供封鎖選項，RP 的 session cookie 很可能根本送不進去（第 23 章）。使用者在登出頁載完之前關掉分頁，通知也就沒送出去。
- **Back-channel logout**：IdP 的伺服器直接對每個 RP 註冊的 back-channel 登出端點送 HTTP POST，內容是一個簽章的 **logout token**（也是 JWT）。不經過瀏覽器，所以不受 cookie 政策與分頁是否開著影響。代價是 RP 必須能被 IdP 的伺服器連到，而且 RP 的 session 必須存在伺服器端、能依 IdP 給的識別找到並刪除。

```text
 員工瀏覽器               北辰 IdP                         聲聲 Live RP                  報帳系統 RP
   │ 在入口網站按登出 ──►│                                    │                              │
   │                      │ 結束 idp_session（sid=7f3a）       │                              │
   │                      │── ① POST /oidc/backchannel-logout ►│                              │
   │                      │     logout_token=<JWT>             │ ② 驗簽章、iss、aud、iat、jti │
   │                      │                                    │    events 正確、沒有 nonce   │
   │                      │                                    │ ③ 刪除 (iss, sid=7f3a) 的    │
   │                      │                                    │    所有 session、撤銷 refresh│
   │                      │◄──────────── ④ 200 OK ─────────────│                              │
   │                      │── ① POST /logout/bc ───────────────────────────────────────────►│
   │                      │◄──────────────────────────────────────────────── ④ 200 OK ───────│
   │◄── 登出完成頁 ────────│                                    │                              │
   │ 下次打開聲聲 Live：瀏覽器仍帶著舊 cookie，但伺服器端 session 已刪 → 視為未登入         │
```

① IdP 對每個曾經登入過的 RP 送 logout token。② RP 驗證 logout token 的方式和 ID token 類似，但有幾個專屬規則：它必須帶 `events` claim，裡面有 back-channel logout 的事件識別字串；必須有 `sub` 或 `sid`（IdP session 的識別）至少一個；而且**不能**有 `nonce`，這條規則讓攻擊者無法把一個 ID token 冒充成 logout token。`jti` 用來防重放。③ RP 依 `(iss, sid)` 或 `(iss, sub)` 找到並刪除對應的 session，這要求 RP 在登入時就把 ID token 裡的 `sid` 記在 session 旁邊。最後一行說明 back-channel 的關鍵前提：瀏覽器裡的 cookie 沒被刪，但伺服器端 session 已經不存在，cookie 就成了廢紙；如果 RP 的 session 是一個不查伺服器的 self-contained JWT cookie，back-channel logout 就無從生效。

| 機制 | 通知路徑 | 能登出其他 RP | 受第三方 cookie 限制 | RP 需要什麼 | 主要缺點 |
|---|---|---|---|---|---|
| 本地登出 | 無 | 否 | 否 | 刪 session | IdP session 還在，會被無聲帶回 |
| RP-initiated logout | 瀏覽器導向 IdP | 否（只結束 IdP session） | 否 | 導向 `end_session_endpoint` | 其他 RP 仍登入 |
| Front-channel logout | IdP 頁面裡的 iframe | 是 | **是**，現代瀏覽器常失效 | 可在 iframe 中被載入的登出網址 | 不可靠；分頁關掉就沒送 |
| Back-channel logout | IdP 伺服器直接 POST | 是 | 否 | 對 IdP 開放的端點、伺服器端 session、依 sid 查詢 | RP 要能被連到；IdP 重送策略依實作而定 |
| SAML Single Logout | 瀏覽器或 SOAP | 是 | 瀏覽器版本會受影響 | 實作 SLO | 實作複雜、互通性差，常被關閉 |

聲聲 Live 最後的組合是：使用者在聲聲 Live 按登出，走 RP-initiated logout；在北辰那邊登出，靠 back-channel logout；兩者之外再加上 RP session 的最長壽命與 SCIM 停權當保底。另外，即使 RP session 刪了，已經發出的 access token 在到期前仍然有效（第 27 章），所以 access token 要短，敏感 API 可以另外查詢撤銷狀態。logout 永遠是「盡力而為＋有上限」，沒有一種機制能保證瞬間清除所有地方的登入狀態。

## 29.11 Passkeys 與 WebAuthn：讓釣魚失效的登入

回到故事的第二個問題。密碼與 TOTP 為什麼擋不住釣魚？因為它們都是**可以轉交的秘密**：值本身不包含「是在哪個網站輸入的」這個資訊。老師在 `shengsheng-login.example` 輸入的六位數，和在真網站輸入的六位數一模一樣；攻擊者在三十秒內轉送過去，伺服器看到的只是一個正確的值。要求使用者「看清楚網址」是把防線放在最容易出錯的人身上。抗釣魚的驗證方式必須讓**機器**檢查網址，而且讓檢查結果進入密碼學證明裡。

**WebAuthn**（Web Authentication，W3C 規格）就是這樣的設計，**passkey** 則是業界對「可用於 WebAuthn、通常可跨裝置同步、不需要輸入帳號的 credential」的通稱。它的基本原理是公開金鑰密碼學（第 17 章）：註冊時，裝置為這個網站產生一對新的金鑰，私鑰留在裝置裡，公鑰交給網站；登入時，網站送一個隨機的 **challenge**，裝置用私鑰簽章，網站用公鑰驗證。網站資料庫只存公鑰，外洩了也無法拿來登入；每個網站一對金鑰，也就沒有「密碼重複使用」的問題。

先認識四個角色。**Relying Party**（RP）是網站，也就是聲聲 Live 的伺服器。**authenticator**（驗證器）是保存私鑰、執行簽章的元件：手機或筆電內建的安全硬體叫 platform authenticator，USB 或 NFC 的安全金鑰叫 roaming authenticator。**client** 是瀏覽器或作業系統，負責在網頁與 authenticator 之間傳話，並且**替使用者檢查網址**。**RP ID** 是 credential 綁定的網域，聲聲 Live 用 `shengsheng.example`。

```text
 authenticator（老師的手機）        瀏覽器（client）                      聲聲 Live 伺服器（RP）
   │                                  │── ① 我要註冊 passkey ──────────────────►│
   │                                  │◄── ② options：challenge（隨機 32 bytes）、│
   │                                  │      rp.id=shengsheng.example、user.id（隨機）、
   │                                  │      pubKeyCredParams=[ES256(-7), RS256(-257)]
   │                                  │ ③ 檢查 rp.id 與網址列 origin 相符        │
   │                                  │    組 clientDataJSON：type=webauthn.create、
   │                                  │    challenge、origin（取自網址列）       │
   │◄── ④ 建立 credential：rpIdHash、SHA-256(clientDataJSON) ─│                 │
   │ ⑤ 使用者驗證（指紋／臉／PIN，在本機完成）                  │                 │
   │ 產生新金鑰對；私鑰留在裝置（或同步到使用者的雲端帳號）     │                 │
   │── ⑥ credential ID、公鑰、authenticatorData（+ 選用的 attestation）──►│      │
   │                                  │── ⑦ attestationObject＋clientDataJSON ─►│
   │                                  │                                          │ ⑧ 驗 type、challenge、
   │                                  │                                          │   origin、rpIdHash、旗標
   │                                  │                                          │   存 (credential ID, 公鑰,
   │                                  │                                          │   user, signCount)
```

①② 伺服器產生 challenge 與註冊選項，其中 `user.id` 是一個隨機的使用者識別（不要用 email），`pubKeyCredParams` 依序列出接受的簽章演算法，數字是 COSE 的演算法編號，-7 是 ES256、-257 是 RS256。③ 瀏覽器確認網頁要求的 RP ID 和網址列的 origin 相符，並把 **origin 寫進 clientDataJSON**，這個 origin 由瀏覽器填，網頁的 JavaScript 無法改寫。④⑤ authenticator 要求使用者在本機驗證：指紋或臉部資料從不離開裝置，伺服器只會知道「使用者驗證過了」。⑥⑦ 新的公鑰與 credential ID 送回伺服器。⑧ 伺服器檢查 challenge 是自己發的、origin 是自己的網站、RP ID 的雜湊正確，再把公鑰存起來。

登入流程更短，而且如果 credential 是 **discoverable credential**（可被發現的 credential，存有使用者識別，passkey 通常是這種），使用者連帳號都不必輸入：

```text
 authenticator                      瀏覽器                                  聲聲 Live 伺服器
   │                                  │── ① 開始登入 ────────────────────────────►│
   │                                  │◄── ② challenge（新的隨機值）、rpId、      │
   │                                  │      userVerification=preferred           │
   │                                  │ ③ 檢查 rpId 與 origin；組 clientDataJSON  │
   │                                  │    type=webauthn.get、challenge、origin   │
   │◄── ④ 對 rpId 找 credential ──────│                                           │
   │ ⑤ 使用者驗證；signCount 加 1                                                 │
   │ ⑥ 簽章 = Sign(私鑰, authenticatorData ‖ SHA-256(clientDataJSON))             │
   │── credential ID、authenticatorData、簽章、userHandle ►│                      │
   │                                  │── ⑦ 全部轉給伺服器 ──────────────────────►│
   │                                  │                                           │ ⑧ 用 credential ID 找公鑰，
   │                                  │                                           │   驗 challenge、origin、
   │                                  │                                           │   rpIdHash、UP／UV、簽章、
   │                                  │                                           │   signCount → 建立 session
```

整個抗釣魚的保證都在 ③④⑥ 這三步。**簽章蓋住的是 authenticatorData 與 clientDataJSON 的雜湊**：前者包含 RP ID 的雜湊，後者包含 challenge 與 origin。於是，一個簽章同時證明了三件事：私鑰持有者在場（簽得出來）、這是對**這一次** challenge 的回應（不能重放）、而且是在**這個 origin** 上發生的（不能轉交）。

### 為什麼釣魚網站騙不走

把上個月的事件換成 passkey 重演一次。攻擊者的網站是 `shengsheng-login.example`，它可以向真網站要一個 challenge，再把 challenge 交給老師的瀏覽器，但接下來每一條路都走不通：

```text
 釣魚網站 shengsheng-login.example 拿著真網站發的 challenge，三條路：

 (a) 要求 rpId = shengsheng.example
     瀏覽器：網址列是 shengsheng-login.example，不是 shengsheng.example 或其子網域
     ─► SecurityError，authenticator 根本沒被呼叫

 (b) 改用自己的 rpId = shengsheng-login.example
     authenticator：這個 RP ID 底下沒有任何 credential
     ─► 沒有可用的 passkey（使用者只看到「找不到登入方式」）

 (c) 假設有個壞掉的 client 不檢查 rpId，讓 authenticator 替真 RP ID 簽了
     clientDataJSON 裡的 origin 仍是瀏覽器填的 shengsheng-login.example
     ─► 真網站驗 origin 不符，拒絕
```

(a) 是瀏覽器的檢查：RP ID 必須等於目前網頁的網域，或是它的上層可註冊網域（`www.shengsheng.example` 可以用 `shengsheng.example`，`shengsheng-login.example` 不行），而且不能是 `.example` 這類公開後綴；頁面也必須是 HTTPS（`localhost` 例外）。(b) 是 authenticator 的隔離：credential 依 RP ID 存放，釣魚網站拿自己的 RP ID 只會找到空集合。(c) 是伺服器的檢查：即使前兩道都失守，origin 已被寫進簽章範圍，伺服器比對就會發現。三道防線都不依賴使用者判斷網址，使用者也沒有任何可以「抄下來轉交」的值。這就是 passkey 被稱為 **phishing-resistant**（抗釣魚）的原因。

用手機掃描電腦螢幕上的 QR code 登入（跨裝置的 hybrid 流程）也維持這個性質：手機與電腦之間除了透過網路中繼，還要求藍牙近距離連線，遠端的攻擊者無法只靠轉傳 QR code 完成驗證。

### authenticatorData 的位元布局

伺服器要驗的 authenticatorData 是一段緊湊的二進位資料，格式固定：

```text
 byte 0                               32      33              37
 ┌──────────────────────────────────┬───────┬───────────────┬─────────────────────────────────┐
 │ rpIdHash = SHA-256(RP ID)（32）  │ flags │ signCount（4，│ attestedCredentialData（只在註冊│
 │                                  │  (1)  │ big-endian）  │ 時，AT=1）＋ extensions（ED=1） │
 └──────────────────────────────────┴───────┴───────────────┴─────────────────────────────────┘
 flags 位元：  bit 7   bit 6   bit 5   bit 4   bit 3   bit 2   bit 1   bit 0
               ED      AT      保留    BS      BE      UV      保留    UP
 attestedCredentialData：AAGUID（16）│ credentialId 長度（2）│ credentialId │ 公鑰（COSE_Key，CBOR）
```

前 32 bytes 是 RP ID 的 SHA-256，伺服器用它確認簽章是針對自己的 RP ID。flags 的 **UP**（user present）表示使用者有實際觸碰或確認，**UV**（user verified）表示做了指紋、臉部或 PIN 驗證；**BE**（backup eligible）表示這個 credential 可以被同步備份，**BS**（backup state）表示目前已經同步，兩者都是 1 通常代表一個雲端同步的 passkey；**AT** 表示後面接著新 credential 的資料（只在註冊時），**ED** 表示有 extensions。**signCount** 是 authenticator 每次簽章遞增的計數器，伺服器若看到計數倒退，可能代表 authenticator 被複製；但同步型 passkey 多半固定回傳 0，此時這項檢查不適用。

### passkeys 的取捨

| 方式 | 可被釣魚轉交 | 伺服器外洩的後果 | 使用者體驗 | 遺失裝置 |
|---|---|---|---|---|
| 密碼 | 是 | 雜湊外洩可被離線破解（第 26 章） | 要記、要打 | 不受影響 |
| 密碼＋TOTP | 是（可即時中繼） | TOTP 種子外洩可產生驗證碼 | 多一步輸入 | 要有備援碼 |
| 密碼＋簡訊碼 | 是，另有 SIM 換卡風險 | 同上 | 等簡訊 | 換號麻煩 |
| passkey（同步型） | 否 | 只外洩公鑰，無法登入 | 指紋或臉一下 | 其他裝置與雲端帳號仍有 |
| passkey（裝置綁定、安全金鑰） | 否 | 同上 | 需要帶著裝置 | 要有第二把或備援流程 |

passkey 不是萬靈丹。第一，**帳號復原**是新的最弱環節：如果「忘記 passkey」可以用 email 連結或客服重設，攻擊者就會改攻這條路，所以復原流程要和登入同等嚴格。第二，passkey 保護的是**登入的那一刻**，登入後的 session cookie 若被惡意程式偷走，passkey 幫不上忙，要靠短效 session、敏感操作重新驗證等措施。第三，同步型 passkey 的安全性依賴使用者的平台帳號（例如手機廠商的雲端帳號）。第四，攻擊者若已經透過其他方式進入帳號，可能會替自己註冊一把 passkey，所以新增 passkey 這個動作本身要通知使用者、要求重新驗證。

聲聲 Live 的上線計畫是：老師帳號強制使用 passkey，修改課酬帳戶要求 UV；學生在密碼登入成功後提示「建立 passkey」，登入頁的帳號欄位支援瀏覽器自動填入 passkey（conditional mediation）；保留密碼＋TOTP 作為備援，但復原流程需要客服人工核對。企業員工則由北辰的 IdP 負責驗證方式，聲聲 Live 用 ID token 的 `amr` 或 `acr` 確認對方做了 MFA。

## 29.12 2026 現況：OIDC、passkeys 與相關規格

> [!note] 2026 現況
> 以下依 2026 年 10 月查證（標示「未查證」的項目請在引用前再確認一次）：
> - **WebAuthn Level 3** 已於 2026 年 8 月 25 日成為 W3C Recommendation，前一個階段是 2026 年 5 月的 Candidate Recommendation Snapshot；Level 2 是 2021 年 4 月。Level 3 收錄的功能包括以 JSON 解析與輸出選項的 API、`getClientCapabilities()`、Related Origin Requests（讓多個網域共用一個 RP ID，透過 RP ID 網域下的 `/.well-known/webauthn` 宣告）、hints、conditional mediation、Signal API、`credProps` 與 `prf` extension，以及 BE／BS 旗標的定義（功能清單依知識整理，細節請對照規格本文）。
> - Apple、Google、Microsoft 平台都支援同步型 passkey；第三方密碼管理工具可在較新的 iOS 與 Android 上提供 passkey（依知識，未查證）。FIDO Alliance 正推動跨 provider 匯出入 passkey 的 Credential Exchange Protocol／Format，標準化進度不確定。
> - **OpenID Connect Core 1.0** 有 errata set 2 的更新版；2024 年 OIDC 系列規格被採納為 ISO/IEC 26131～26141（依知識，未查證）。FAPI 2.0 Security Profile 已是 Final（依知識，未查證）；OpenID Federation 1.0 是否已 Final 不確定。
> - **OAuth 2.1** 仍是 IETF 草案（draft-ietf-oauth-v2-1-16，2026 年 9 月），尚未成為 RFC。**OAuth 2.0 for Browser-Based Applications** 已發布為 RFC 10017（BCP 212，2026 年 8 月），推薦 BFF（Backend for Frontend）模式：token 留在後端，瀏覽器只持有 session cookie，這也讓 SPA 不再依賴 iframe 無聲續期。
> - 第三方 cookie：Safari 預設封鎖、Firefox 依頂層網站分區；Chrome 預設仍允許，但 2025 年 10 月宣布逐步淘汰多數 Privacy Sandbox 技術，同時保留 FedCM（瀏覽器原生的聯合登入 API）等少數項目。對 OIDC 的影響是：front-channel logout、OIDC Session Management 的 iframe 檢查、隱藏 iframe 的 `prompt=none`，在主流瀏覽器中都不能當成可靠機制。

## 29.13 動手做：驗證 ID token 與模擬 passkey 抗釣魚

這一節用兩段程式把 Rita 的審查意見與釣魚事件都重演一次。兩段都只用標準函式庫，而且為了不依賴第三方密碼學套件，都用 HMAC 代替真正的非對稱簽章；程式開頭與以下解說都會標明真實系統的差別。

### 實驗一：一步一步驗證 ID token

這段程式扮演北辰的 IdP 與聲聲 Live 的 RP。IdP 用 HS256 簽發 ID token；真實的 IdP 多用 RS256 或 ES256，RP 只持有 JWKS 裡的公鑰。差別不只是演算法：用 HS256 時 RP 也持有簽章金鑰，等於 RP 自己也能「簽發」ID token，所以多 RP 的環境一定要用非對稱簽章。`verify_id_token()` 依 29.6 節的順序檢查，每一步失敗都帶著明確的原因。測試案例涵蓋 Rita 擔心的每一種情況。

```python
import base64
import hashlib
import hmac
import json
import secrets

# 教學簡化：用 HS256（HMAC）簽章。真實 IdP 多用 RS256／ES256，RP 只拿 JWKS 裡的公鑰驗證。
ISSUER = "https://login.beichen.example"
CLIENT_ID = "shengsheng-live"
KEYS = {"k2026-09": secrets.token_bytes(32)}   # kid → 金鑰（真實情況：kid → 公鑰）
NOW = 1_790_000_000                            # 模擬時鐘（Unix 秒）
LEEWAY = 60                                    # 容忍的時鐘誤差


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(header: dict, claims: dict, key: bytes) -> str:
    signing_input = b64url(json.dumps(header).encode()) + "." + b64url(json.dumps(claims).encode())
    sig = hmac.new(key, signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + b64url(sig)


def issue(nonce, **overrides):
    """模擬 IdP 在 token endpoint 回傳的 ID token。"""
    claims = {"iss": ISSUER, "sub": "e-20931", "aud": CLIENT_ID, "iat": NOW - 5,
              "exp": NOW + 300, "auth_time": NOW - 20, "nonce": nonce,
              "email": "mei.lin@beichen.example", "email_verified": True}
    claims.update(overrides)
    return sign({"alg": "HS256", "typ": "JWT", "kid": "k2026-09"}, claims, KEYS["k2026-09"])


class InvalidToken(Exception):
    pass


def verify_id_token(token: str, pending_nonces: set, now: int, max_age=None) -> dict:
    try:
        h64, p64, s64 = token.split(".")
        header = json.loads(b64url_decode(h64))
        claims = json.loads(b64url_decode(p64))
    except ValueError:
        raise InvalidToken("格式錯誤")
    # 1. alg 由我們決定，不由 token 決定（擋 alg=none 與演算法混淆）
    if header.get("alg") != "HS256":
        raise InvalidToken(f"alg 不允許：{header.get('alg')}")
    key = KEYS.get(header.get("kid"))
    if key is None:
        raise InvalidToken("找不到 kid 對應的金鑰")
    # 2. 簽章：用常數時間比較
    expected = hmac.new(key, f"{h64}.{p64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64url_decode(s64)):
        raise InvalidToken("簽章不符")
    # 3. iss 逐字比對
    if claims.get("iss") != ISSUER:
        raise InvalidToken(f"iss 不符：{claims.get('iss')}")
    # 4. aud 必須包含自己；多個 aud 時 azp 必須是自己
    aud = claims.get("aud")
    auds = aud if isinstance(aud, list) else [aud]
    if CLIENT_ID not in auds:
        raise InvalidToken(f"aud 不是我：{aud}")
    if len(auds) > 1 and claims.get("azp") != CLIENT_ID:
        raise InvalidToken(f"多個 aud，但 azp={claims.get('azp')}")
    # 5. 時間：exp、iat（容忍時鐘誤差）
    if now > claims["exp"] + LEEWAY:
        raise InvalidToken("已過期")
    if claims["iat"] > now + LEEWAY:
        raise InvalidToken("iat 在未來")
    if max_age is not None and now - claims.get("auth_time", 0) > max_age + LEEWAY:
        raise InvalidToken("登入時間太久以前，需重新驗證")
    # 6. nonce 必須是這個瀏覽器 session 發出、還沒用過的那一個（用完即刪 → 擋重放）
    if claims.get("nonce") not in pending_nonces:
        raise InvalidToken("nonce 不符或已用過")
    pending_nonces.discard(claims["nonce"])
    return claims


pending = set()                               # 存在 RP 的 session（或簽過的 cookie）裡


def start_login() -> str:
    """每次把使用者導去 IdP 前產生一個新 nonce，記在 session。"""
    n = secrets.token_urlsafe(16)
    pending.add(n)
    return n


good = issue(start_login())
body = json.loads(b64url_decode(good.split(".")[1]))
forged = good.split(".")
forged[1] = b64url(json.dumps({**body, "email": "ceo@beichen.example"}).encode())
none_alg = b64url(b'{"alg":"none"}') + "." + good.split(".")[1] + "."

cases = [
    ("正常登入", good, None),
    ("同一個 token 再送一次", good, None),
    ("發給別的應用（aud）", issue(start_login(), aud="beichen-expense"), None),
    ("過期", issue(start_login(), exp=NOW - 600), None),
    ("假 IdP（iss）", issue(start_login(), iss="https://login.beichen-sso.example"), None),
    ("alg=none", none_alg, None),
    ("竄改 email", ".".join(forged), None),
    ("多個 aud、azp 不是我", issue(start_login(), aud=[CLIENT_ID, "beichen-expense"], azp="beichen-expense"), None),
    ("改課酬帳戶前要求 max_age=600", issue(start_login(), auth_time=NOW - 900), 600),
]
results = []
for label, token, max_age in cases:
    try:
        c = verify_id_token(token, pending, NOW, max_age)
        results.append("OK")
        print(f"{label} → 通過：使用者鍵 (iss, sub) = ({c['iss']}, {c['sub']})")
    except InvalidToken as exc:
        results.append(str(exc))
        print(f"{label} → 拒絕：{exc}")

assert results[0] == "OK" and results[1] == "nonce 不符或已用過"
assert results[2].startswith("aud") and results[3] == "已過期" and results[4].startswith("iss")
assert results[5].startswith("alg") and results[6] == "簽章不符" and results[7].startswith("多個 aud")
assert results[8].startswith("登入時間")
```

```text
正常登入 → 通過：使用者鍵 (iss, sub) = (https://login.beichen.example, e-20931)
同一個 token 再送一次 → 拒絕：nonce 不符或已用過
發給別的應用（aud） → 拒絕：aud 不是我：beichen-expense
過期 → 拒絕：已過期
假 IdP（iss） → 拒絕：iss 不符：https://login.beichen-sso.example
alg=none → 拒絕：alg 不允許：none
竄改 email → 拒絕：簽章不符
多個 aud、azp 不是我 → 拒絕：多個 aud，但 azp=beichen-expense
改課酬帳戶前要求 max_age=600 → 拒絕：登入時間太久以前，需重新驗證
```

第一行是正常登入：簽章、iss、aud、時間、nonce 都通過，程式回報的帳號鍵是 `(iss, sub)`，而不是 email。第二行把同一個 token 再送一次，前面每一步都會通過（它確實是 IdP 簽的、還沒過期），只有 nonce 擋下它，因為第一次使用時已經從 session 刪掉了；這就是 nonce「用完即刪」的價值。第三行是 token substitution：IdP 發給北辰報帳系統的 token 簽章完全有效，但 `aud` 不是聲聲 Live。第四、五行分別是過期與發行者不符，`login.beichen-sso.example` 是一個看起來很像的假 IdP。程式為了單獨觀察 iss 檢查，讓它用同一把金鑰簽章；真實的假 IdP 多半在簽章那一步就失敗，但在多租戶系統裡，「另一家合法 IdP」簽出的 token 簽章完全有效，只能靠 iss 擋下。

第六行的 token header 寫著 `alg: none`，因為程式只接受自己設定的 HS256，看都不看就拒絕；如果程式改成「照 header 寫的演算法去驗」，這個沒有簽章的 token 就可能通過。第七行把 payload 的 email 改成執行長，簽章立刻對不上，這正是小晴原型最大的漏洞：原型根本沒有這一步。第八行的 token 同時發給兩個 client，`azp` 卻是報帳系統，表示實際取得 token 的不是我們。最後一行模擬改課酬帳戶前要求 10 分鐘內登入過，`auth_time` 是 15 分鐘前，程式要求重新驗證。把這九行和 29.6 節的表格對照，就是一份可以拿去驗收任何 OIDC 函式庫設定的清單。

### 實驗二：passkey 的 challenge-response 與 origin 綁定

第二段程式模擬 WebAuthn 的三個角色：`Authenticator`（老師的手機，credential 依 RP ID 存放）、`Browser`（從網址列取 origin、檢查 RP ID）、`RelyingParty`（聲聲 Live 的伺服器，驗 challenge、origin、rpIdHash、旗標與簽章）。**真實的 WebAuthn 用非對稱簽章**：私鑰只在 authenticator 裡，伺服器只存公鑰；這裡為了只用標準函式庫，改用 HMAC，伺服器因此持有同一把金鑰，這在真實系統中是不可接受的，模擬只保留「簽章蓋住 authenticatorData 與 clientDataJSON 雜湊」這個結構。authenticatorData 依上一節的位元布局組成。

```python
import base64
import hashlib
import hmac
import json
import secrets
import struct
from urllib.parse import urlsplit

# 教學簡化：用 HMAC 代替數位簽章。真實的 WebAuthn 用非對稱金鑰（多為 ES256）：
# 私鑰只在 authenticator 裡，RP 只存公鑰，所以 RP 的資料庫外洩也簽不出 assertion。
UP, UV, AT = 0x01, 0x04, 0x40                      # authenticatorData 的旗標位元


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Authenticator:
    """手機或筆電裡的 authenticator：credential 依 RP ID 分開存放。"""

    def __init__(self):
        self.creds = {}                             # rp_id → (cred_id, key, sign_count)

    def make_credential(self, rp_id, client_data_hash):
        cred_id, key = secrets.token_bytes(16), secrets.token_bytes(32)
        self.creds[rp_id] = [cred_id, key, 0]
        auth_data = (hashlib.sha256(rp_id.encode()).digest() + bytes([UP | UV | AT])
                     + struct.pack("!I", 0) + struct.pack("!H", len(cred_id)) + cred_id)
        return cred_id, key, auth_data              # 真實情況回傳的是公鑰（COSE 格式）

    def get_assertion(self, rp_id, client_data_hash):
        if rp_id not in self.creds:                 # 這個 RP ID 根本沒有 credential
            raise PermissionError("NotAllowedError：沒有這個網站的 passkey")
        entry = self.creds[rp_id]
        entry[2] += 1
        auth_data = hashlib.sha256(rp_id.encode()).digest() + bytes([UP | UV]) + struct.pack("!I", entry[2])
        sig = hmac.new(entry[1], auth_data + client_data_hash, hashlib.sha256).digest()
        return entry[0], auth_data, sig


class Browser:
    """瀏覽器：origin 取自網址列，網頁無法偽造；並檢查網頁要求的 RP ID 是否合法。"""

    def __init__(self, authenticator):
        self.authn = authenticator

    def _client_data(self, kind, origin, rp_id, challenge):
        host = urlsplit(origin).hostname
        if urlsplit(origin).scheme != "https" or not (host == rp_id or host.endswith("." + rp_id)):
            raise PermissionError(f"SecurityError：{origin} 不能使用 RP ID {rp_id}")
        return json.dumps({"type": kind, "challenge": b64url(challenge), "origin": origin}).encode()

    def create(self, origin, rp_id, challenge):
        cd = self._client_data("webauthn.create", origin, rp_id, challenge)
        return (cd, *self.authn.make_credential(rp_id, hashlib.sha256(cd).digest()))

    def get(self, origin, rp_id, challenge):
        cd = self._client_data("webauthn.get", origin, rp_id, challenge)
        return (cd, *self.authn.get_assertion(rp_id, hashlib.sha256(cd).digest()))


class RelyingParty:
    RP_ID, ORIGIN = "shengsheng.example", "https://www.shengsheng.example"

    def __init__(self):
        self.challenges, self.creds = set(), {}

    def new_challenge(self):
        c = secrets.token_bytes(32)                 # 每次都是新的隨機值，用一次就作廢
        self.challenges.add(c)
        return c

    def _check(self, cd_bytes, kind, auth_data):
        cd = json.loads(cd_bytes)
        challenge = base64.urlsafe_b64decode(cd["challenge"] + "==")
        if cd["type"] != kind:
            raise ValueError("type 不符")
        if challenge not in self.challenges:
            raise ValueError("challenge 不是我發的或已用過")
        self.challenges.discard(challenge)
        if cd["origin"] != self.ORIGIN:
            raise ValueError(f"origin 不符：{cd['origin']}")
        if auth_data[:32] != hashlib.sha256(self.RP_ID.encode()).digest():
            raise ValueError("rpIdHash 不符")
        if not auth_data[32] & UP:
            raise ValueError("使用者不在場（UP=0）")

    def register(self, cd, cred_id, key, auth_data):
        self._check(cd, "webauthn.create", auth_data)
        self.creds[cred_id] = {"key": key, "count": 0}
        return "註冊成功"

    def login(self, cd, cred_id, auth_data, sig):
        self._check(cd, "webauthn.get", auth_data)
        cred = self.creds.get(cred_id) or {}
        expected = hmac.new(cred.get("key", b""), auth_data + hashlib.sha256(cd).digest(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("簽章不符")
        count = struct.unpack("!I", auth_data[33:37])[0]
        if count and count <= cred["count"]:
            raise ValueError("signCount 倒退，疑似複製的 authenticator")
        cred["count"] = count
        return f"登入成功（flags={auth_data[32]:#04x}，signCount={count}）"


def attempt(label, fn):
    try:
        result = fn()
    except (PermissionError, ValueError) as exc:
        result = f"拒絕：{exc}"
    print(f"{label} → {result}")
    return result


rp, phone = RelyingParty(), Authenticator()
browser = Browser(phone)
real, phish = RelyingParty.ORIGIN, "https://shengsheng-login.example"

r1 = attempt("1. 真網站註冊", lambda: rp.register(*browser.create(real, rp.RP_ID, rp.new_challenge())))
r2 = attempt("2. 真網站登入", lambda: rp.login(*browser.get(real, rp.RP_ID, rp.new_challenge())))
# 釣魚網站把 rp 發的 challenge 中繼過來，想讓使用者的 passkey 替它簽
c3 = rp.new_challenge()
r3 = attempt("3. 釣魚頁要求 RP ID=shengsheng.example", lambda: browser.get(phish, rp.RP_ID, c3))
r4 = attempt("4. 釣魚頁改用自己的 RP ID", lambda: browser.get(phish, "shengsheng-login.example", c3))


class BrokenClient(Browser):
    """假設有個不檢查 RP ID 的壞 client：authenticator 簽了，但 origin 仍誠實寫進 clientData。"""

    def _client_data(self, kind, origin, rp_id, challenge):
        return json.dumps({"type": kind, "challenge": b64url(challenge), "origin": origin}).encode()


r5 = attempt("5. 壞 client 替釣魚頁簽章", lambda: rp.login(*BrokenClient(phone).get(phish, rp.RP_ID, c3)))
old = browser.get(real, rp.RP_ID, rp.new_challenge())
rp.login(*old)
r6 = attempt("6. 重放上一次的 assertion", lambda: rp.login(*old))

assert r1 == "註冊成功" and r2.startswith("登入成功")
assert "SecurityError" in r3 and "NotAllowedError" in r4
assert "origin 不符" in r5 and "challenge" in r6
```

```text
1. 真網站註冊 → 註冊成功
2. 真網站登入 → 登入成功（flags=0x05，signCount=1）
3. 釣魚頁要求 RP ID=shengsheng.example → 拒絕：SecurityError：https://shengsheng-login.example 不能使用 RP ID shengsheng.example
4. 釣魚頁改用自己的 RP ID → 拒絕：NotAllowedError：沒有這個網站的 passkey
5. 壞 client 替釣魚頁簽章 → 拒絕：origin 不符：https://shengsheng-login.example
6. 重放上一次的 assertion → 拒絕：challenge 不是我發的或已用過
```

第 1、2 行是正常的註冊與登入。登入成功的 flags 是 `0x05`，也就是 UP（0x01）與 UV（0x04）都打開；signCount 從 0 變成 1。第 3 行是釣魚網站直接要求真網站的 RP ID：瀏覽器比對網址列發現網域不符，丟出 SecurityError，authenticator 根本沒被呼叫，對應前一節的 (a)。第 4 行釣魚網站改用自己的 RP ID，authenticator 找不到任何 credential，對應 (b)。

第 5 行假設 client 本身被繞過，不檢查 RP ID，authenticator 也替真網站的 RP ID 簽了章；但 clientDataJSON 裡的 origin 依然是釣魚網站，伺服器比對 origin 後拒絕，對應 (c)。這個案例說明伺服器端的 origin 檢查不是多餘的：它是在 client 失守時的最後一道防線。第 6 行把一次成功登入的完整 assertion 原封不動再送一次，challenge 已經用過而被拒絕，這是 challenge「每次新產生、用一次就作廢」的效果。

## 29.14 在工作上怎麼用

**後端工程師：接 OIDC 時的驗收清單。** 選用成熟的 OIDC 函式庫，然後逐項確認：只用 authorization code＋PKCE；state、nonce、code_verifier 存在伺服器端 session 或有簽章的 cookie，並且用完即刪；redirect URI 在 IdP 端精確註冊；ID token 驗證涵蓋 29.6 節九個步驟，允許的演算法寫死在設定裡；帳號主鍵是 `(iss, sub)`；登入時把 `sid` 存在 session 旁邊供 back-channel logout 使用；client 憑證放在 secrets 管理系統（第 30 章），能用 `private_key_jwt` 就不要用共用的 client secret。

**SRE：觀察 OIDC 相依性。** IdP 是登入的關鍵相依，要監控 discovery 與 JWKS 的抓取成功率、callback 的錯誤率（依原因分類：state 不符、nonce 不符、iss 不符、kid 找不到）、token endpoint 延遲。下面是排查時常用的指令（`$ISSUER` 換成你的 IdP，示意）：

```bash
# 讀 discovery，確認 issuer 字串與端點
curl -s "$ISSUER/.well-known/openid-configuration" | python3 -m json.tool | head -20
# 列出目前 JWKS 裡的 kid，與 log 中「kid 找不到」的值比對
curl -s "$(curl -s "$ISSUER/.well-known/openid-configuration" | python3 -c 'import json,sys; print(json.load(sys.stdin)["jwks_uri"])')" \
  | python3 -c 'import json,sys; print([k["kid"] for k in json.load(sys.stdin)["keys"]])'
# 本機與 IdP 的時鐘差：exp／iat 錯誤常常是時鐘問題
curl -sI "$ISSUER/.well-known/openid-configuration" | grep -i '^date:' ; date -u
```

第一條指令確認 issuer 字串與各端點，常見的設定錯誤（結尾斜線、http 與 https、租戶 ID）一眼就能看出。第二條列出目前的 `kid`，如果 log 裡出現的 `kid` 不在清單中，可能是 IdP 剛輪替、RP 快取還沒更新，或是 token 根本不是這個 IdP 發的。第三條比較伺服器時鐘，`iat` 在未來或剛發就過期的錯誤，多半是某一台機器的 NTP 壞了。

**前端工程師：不要在瀏覽器裡處理 token。** 依 OAuth 2.0 for Browser-Based Applications 推薦的 BFF 模式（規格狀態見 29.12 節），瀏覽器只持有 RP 的 session cookie（`HttpOnly`、`Secure`、`SameSite`，第 23 章），code 交換與 token 都在後端。passkey 相關的前端工作是呼叫 `navigator.credentials.create()`／`get()`，把伺服器給的 options 轉成 API 需要的格式；登入欄位加上 `autocomplete="username webauthn"` 啟用自動填入。在 DevTools 的 Application 面板看 cookie 是否被設在正確的網域，在 WebAuthn 面板可以建立虛擬 authenticator 來測試流程。

**資安工程師：審查清單與事件應變。** Rita 的 SSO 審查清單包括：租戶網域經過 DNS 驗證才啟用 home realm discovery；每個租戶的 issuer 隔離；JIT 建立的帳號預設最小權限；帳號連結不靠未驗證的 email；新增 passkey、變更 MFA、修改收款帳戶都要求最近的強驗證並通知使用者。發生 IdP 端帳號被盜時，處理順序是：在 IdP 停用帳號 → 透過 SCIM 或管理介面在 RP 停用 → 撤銷 refresh token 並刪除 session → 檢查期間新增的 passkey 與 MFA 裝置。

**影音工程師：長時間的課堂與 session 到期。** Joe 遇過的情況是：一堂 90 分鐘的課上到一半，RP session 或 access token 到期，WebSocket 重連（第 32 章）時驗證失敗，學生被踢出教室。解法是在進教室時確認剩餘的 session 時間足夠，或讓即時服務在連線建立時驗證一次、連線期間依自己的票據續期，而不是每次重連都依賴可能已過期的 token。

## 29.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 任何人都能用偽造的 token 登入 | callback 只 base64 解碼 ID token，沒驗簽章 | 送一個改過 payload 的 token 測試；檢查程式是否呼叫驗證函式 | 用 OIDC 函式庫驗證；把 29.6 節的步驟寫成自動化測試 |
| callback 偶發「invalid state」 | state 存在會被輪替或過期的地方；使用者同時開兩個分頁登入；cookie 的 SameSite 設定讓 callback 帶不到 session | 看失敗的請求有沒有帶 session cookie；DevTools 看 cookie 屬性 | 以 state 為鍵存多筆進行中的登入；callback 用的 cookie 設 `SameSite=Lax` |
| IdP 輪替金鑰後一段時間登入全失敗 | RP 的 JWKS 快取寫死或沒有 kid 重抓機制；IdP 新鑰一發布就使用 | log 中的 kid 不在 RP 快取，但在 IdP 目前的 JWKS 裡 | 遇到未知 kid 重抓（加冷卻）；依 `Cache-Control` 快取；與 IdP 協調預先發布 |
| 剛拿到的 token 就被判定過期，或「iat 在未來」 | 機器時鐘偏差；leeway 為 0 | 比對 RP 主機與 IdP 回應的 `Date` header | 修 NTP；設定合理的 leeway（例如 60 秒） |
| 使用者按了登出，再按登入卻沒輸入密碼就進來了 | 只做本地登出，IdP session 還在 | 登出後檢查是否有導向 `end_session_endpoint` | 實作 RP-initiated logout；共用電腦情境可在登入時帶 `prompt=login` |
| 在 IdP 登出後，聲聲 Live 仍登入著（特別是 Safari） | 依賴 front-channel logout，iframe 裡的第三方 cookie 被封鎖 | 比較不同瀏覽器的行為；看 iframe 請求是否帶 cookie | 改用 back-channel logout；RP session 存在伺服器端並以 sid 索引 |
| 員工離職一週後仍能使用 | 只有 JIT，沒有停權管道；RP session 很長 | 查該帳號最後一次經過 IdP 的時間 | 接 SCIM；限制 RP session 最長壽命；定期重新走 IdP |
| 企業員工登入後看到別人的課程紀錄 | 用 email 當主鍵，email 被回收給新員工 | 比對帳號綁定的 `(iss, sub)` 與這次登入的 `sub` | 主鍵改成 `(iss, sub)`；遷移既有資料並人工處理衝突 |
| passkey 註冊時出現 SecurityError | RP ID 不是目前網域或其上層網域；頁面不是 HTTPS；在 `localhost` 以外用 IP 測試 | DevTools console 的錯誤訊息；比對 `rp.id` 與網址列 | RP ID 設為可註冊網域（例如 `shengsheng.example`）；測試環境用 HTTPS 或 `localhost` |
| passkey 驗證在伺服器端失敗：origin 不符 | 伺服器允許的 origin 清單沒包含實際網址（子網域、port、App 的 origin） | log 印出 clientDataJSON 的 origin 欄位 | 明確列出允許的 origin；跨網域需求評估 Related Origin Requests |
| signCount 檢查讓部分使用者無法登入 | 同步型 passkey 固定回傳 0，程式誤判為倒退 | 看失敗者的 signCount 是否為 0、BE／BS 旗標 | 計數為 0 時跳過這項檢查；只對非 0 的計數判斷倒退 |

## 29.16 動手練習

1. **延伸實驗一：加入 back-channel logout token 的驗證**。在實驗一的程式中新增 `verify_logout_token()`：檢查簽章、iss、aud、iat、`jti` 不重複、`events` 裡有 back-channel logout 的事件鍵、至少有 `sub` 或 `sid`，而且**沒有** `nonce`。再建一個以 `(iss, sid)` 為鍵的 session 表，驗證通過就刪除對應的 session。
   答案要點：拿實驗一的正常 ID token 冒充 logout token 時，應因為缺少 `events` 或帶有 `nonce` 而被拒絕，這正是規格禁止 nonce 的目的。同一個 `jti` 送第二次要拒絕。刪除後再查 session 表，應找不到該 sid。

2. **延伸實驗二：RP ID 的選擇**。把 `RelyingParty.RP_ID` 改成 `www.shengsheng.example`，再新增一個 origin 為 `teacher.shengsheng.example` 的老師後台，試著用同一把 passkey 登入。
   答案要點：瀏覽器會拒絕，因為 `teacher.shengsheng.example` 不是 `www.shengsheng.example` 或其子網域。RP ID 選上層的可註冊網域（`shengsheng.example`），所有子網域才能共用；RP ID 一旦選定，改變它等於讓所有既有 passkey 失效，所以要在第一次上線前決定。

3. **讀一份真實的 discovery 文件**（真實工具）。對你工作或個人使用的任一 IdP，用 29.14 節的 `curl` 指令讀取 discovery 與 JWKS。
   答案要點：確認 `issuer` 與你抓取的網址前綴逐字相同；找出 `id_token_signing_alg_values_supported`、`end_session_endpoint`、`backchannel_logout_supported` 等欄位；JWKS 裡常同時有兩把以上的 `kid`，代表正在輪替或預先發布。

4. **用瀏覽器的虛擬 authenticator 觀察 passkey**（真實工具）。在 Chromium 系瀏覽器開啟 DevTools 的 WebAuthn 面板，啟用虛擬 authenticator，然後在任一支援 passkey 的測試網站（或你自己用 `localhost` 架的頁面）註冊並登入兩次。
   答案要點：面板會列出 credential ID、RP ID 與 sign count；每次登入 sign count 遞增。把網頁的 `rp.id` 改成不相符的網域，console 會出現 SecurityError，對應實驗二的第 3 行。

5. **設計聲聲 Live 的 logout 矩陣**。列出四種登出起點（使用者在聲聲 Live 按登出、在北辰入口登出、北辰停用帳號、聲聲 Live 管理員強制登出），對每一種寫出：哪幾層 session 會結束、透過哪個機制、最晚多久生效。
   答案要點：第一種走 RP-initiated logout，結束 RP 與 IdP session；第二種靠 back-channel logout，若失敗則由 RP session 最長壽命兜底；第三種靠 SCIM，並撤銷 refresh token；第四種刪除 RP session 與 refresh token，但已發出的 access token 要等到期（第 27 章的 5 分鐘），所以表格要寫出這個上限。

## 本章重點整理

- OAuth 的 access token 回答「可以做什麼」，不帶「發給哪個 client」的保證，直接拿來當登入證明會遭遇 token substitution；OIDC 用 ID token 補上「是誰、給誰、何時登入」。
- OIDC 推薦的流程是 authorization code＋PKCE：state 擋 login CSRF，PKCE 擋授權碼被攔截後換 token，nonce 把 ID token 綁定到這一次瀏覽器登入。
- ID token 是 IdP 簽章的 JWT，payload 沒有加密；能解碼不代表可信，必須驗證後才能使用。
- ID token 的驗證步驟依序是：固定允許的 alg、用 kid 找公鑰驗簽章、iss 逐字相符、aud 包含自己（多 aud 時檢查 azp）、exp 與 iat 在容忍範圍內、需要時檢查 auth_time、nonce 相符且用完即刪。
- 帳號主鍵是 `(iss, sub)`，不是 email；email 可被修改、回收，部分 IdP 的 email 不一定經過驗證。
- Discovery 讓 RP 只需設定 issuer；JWKS 支援金鑰輪替，正確的輪替是先發布、再使用、最後移除，RP 遇到未知 kid 才重抓並加上冷卻時間。
- SSO 來自 IdP 自己的 session cookie；IdP session、RP session 與 token 是彼此獨立的三層，外層結束不會讓內層自動結束。
- SAML 2.0 的概念與 OIDC 一一對應（SP、Assertion、NameID、Audience、InResponseTo、ACS），差別在 XML 簽章與 assertion 經由瀏覽器 POST 送達，實作時不要自己解析 XML。
- 企業 IdP 整合需要經 DNS 驗證的網域做 home realm discovery、每個租戶獨立的 issuer 設定、預設最小權限的 JIT provisioning，以及用 SCIM 處理停權。
- Logout 分本地、RP-initiated、front-channel、back-channel 四類；front-channel 依賴 iframe 裡的第三方 cookie，在現代瀏覽器中不可靠，back-channel 需要伺服器端 session 與 sid 索引。
- 密碼與 TOTP 是可轉交的秘密，能被釣魚網站即時中繼；passkey 的簽章蓋住 challenge、origin 與 RP ID 雜湊，讓轉交失去意義。
- 瀏覽器拒絕與網址不符的 RP ID、authenticator 依 RP ID 隔離 credential、伺服器驗證 clientDataJSON 的 origin，三道防線都不依賴使用者辨識網址。
- passkey 之後的最弱環節是帳號復原、登入後的 session 竊取與新增 passkey 的流程，這些都要和登入同等嚴格地保護。
- WebAuthn Level 3 已於 2026 年 8 月成為 W3C Recommendation；OAuth 2.1 仍是草案，瀏覽器應用推薦 BFF 模式，讓 token 留在後端。

## 延伸問答

> [!question]- Q1. 同事說：「我們拿到 Google 的 access token 後呼叫它的使用者資訊 API，拿到 user ID 就當作登入成功，這樣和 OIDC 有什麼差別？」你會怎麼回答？
> 差別在「這個憑證是發給誰的」。access token 是給 resource server 用的通行證，OAuth 沒有規定它要綁定哪個 client，resource server 驗證時只確認 token 有效、屬於哪個使用者。如果攻擊者經營另一個也接了同一個 IdP 的應用，誘使使用者在那裡登入，就能拿到屬於該使用者的 access token；把它送到你的登入端點，你呼叫 API 會得到「有效、屬於某使用者」的回應，於是讓攻擊者登入，這就是 token substitution。
>
> OIDC 的 ID token 是寫給 client 的身分證明，`aud` 明確寫著發給哪個 client，`nonce` 綁定這一次登入，簽章讓 client 能自行驗證，不必相信某支 API 的回應。所以正確做法是要求 `openid` scope，驗證 ID token，以 `(iss, sub)` 識別使用者；access token 只拿來呼叫 API。如果某個 IdP 不支援 OIDC，就要另外確認它提供的「token 是發給哪個 client」的驗證方式。

> [!question]- Q2. 面試題：authorization code flow 已經有 PKCE 和 state，為什麼 OIDC 還要 nonce？可以不送嗎？
> 三者擋的東西不同。state 在 callback 時比對，確認這個回應屬於這個瀏覽器發起的流程，擋 login CSRF。PKCE 在 token endpoint 由 IdP 比對，確認拿授權碼來換 token 的是當初發起請求的 client，擋授權碼被攔截後的兌換。nonce 則寫在 ID token 裡、由 RP 驗證，確認這張身分證明是針對這一次登入簽發的，擋的是 ID token 被重放或從其他流程注入。
>
> 在純粹的 code flow 裡，OIDC 規格把 nonce 列為選用，因為 PKCE 與 state 加上後端直接取得 token，已經擋掉大部分注入路徑。但 nonce 的成本很低，它是在其他防線出錯時（例如 state 處理有 bug、token 經過其他元件轉交）仍然有效的一層，而且 implicit 與 hybrid flow 規定必須使用。所以實務答案是：可以不送，但建議一律送；一旦送了，ID token 裡就必須有，RP 就必須比對，並在使用後刪除。

> [!question]- Q3. 你在 production 看到：每隔幾個月的某一天早上，登入錯誤率突然升高到 20%，錯誤原因是「找不到 kid」，大約一小時後自行恢復。可能的原因是什麼？怎麼修？
> 「找不到 kid」代表 ID token header 指定的金鑰不在 RP 的 JWKS 快取裡。週期性發生、自行恢復，最符合的解釋是 IdP 在輪替簽章金鑰：IdP 開始用新金鑰簽 token 時，RP 的快取還是舊的 JWKS，直到快取到期（這裡約一小時）重新抓取才恢復。20% 而不是 100%，可能是 RP 有多個執行個體，各自的快取到期時間不同，或 IdP 也有多個節點逐步切換。
>
> 確認方法是比對錯誤 log 裡的 kid 與當下 IdP 的 JWKS，並詢問 IdP 的輪替時程。RP 端的修正是：遇到未知的 kid 時立即重抓一次 JWKS（加上冷卻時間防止被濫用），並依 JWKS 回應的快取 header 決定快取時間，而不是寫死一小時。IdP 端的正確做法是先發布新公鑰、等待超過 RP 快取時間後才開始使用。兩邊各做一半，輪替就不會被使用者察覺。

> [!question]- Q4. 北辰回報：「員工在入口網站登出後，用 Chrome 時聲聲 Live 會一起登出，用 Safari 時不會。」你會怎麼判斷與修正？
> 瀏覽器之間有差異，通常指向依賴瀏覽器的機制，最可能是 front-channel logout。IdP 的登出頁會為每個 RP 嵌入隱藏的 iframe 載入 RP 的登出網址，RP 依靠 iframe 裡帶上的 session cookie 找到要刪的 session。iframe 裡的 RP 對頂層頁面（IdP）而言是第三方，Safari 預設封鎖第三方 cookie，請求送到 RP 時沒有 cookie，RP 不知道要登出誰。在 Chrome 若使用者沒有封鎖第三方 cookie，才會正常運作。
>
> 確認方法是在兩個瀏覽器的 DevTools 裡看 iframe 對 RP 的請求是否帶 cookie。修正方向是改用 back-channel logout：IdP 伺服器直接 POST logout token 給 RP，RP 依 `(iss, sid)` 刪除伺服器端的 session，不經過瀏覽器，也就不受 cookie 政策影響。前提是 RP 的 session 存在伺服器端、登入時記錄了 sid，且 RP 的端點能被 IdP 連到。最後再用 RP session 的最長壽命作為保底。

> [!question]- Q5. 設計取捨：產品經理希望企業客戶「設定好 IdP 就能用」，不想實作 SCIM。只用 JIT provisioning 會有什麼風險？怎麼降低？
> JIT 只在使用者登入時建立或更新帳號，所以它天生無法處理「不再登入的人」。最大的風險是停權：員工離職、IdP 停用帳號後，只要聲聲 Live 的 session 還沒到期，這個人仍然能使用，而且 RP 永遠不會收到帳號被停用的訊號，帳號會一直留在系統裡。另外，部門、角色等屬性只在登入時更新，被降權的人在下次登入前仍保有舊權限。
>
> 不實作 SCIM 時，可以用三個措施降低風險：限制 RP session 的最長壽命（例如 12 小時），到期後必須重新經過 IdP，停用的帳號就無法再進來；實作 back-channel logout，讓 IdP 端的登出能即時傳到 RP；對敏感操作要求最近的驗證（`max_age`）。同時要在合約與文件中明確寫出「停權最晚多久生效」。若客戶要求「當天停權」且 session 壽命必須很長，SCIM 就是必要的。

> [!question]- Q6. 為什麼密碼加 TOTP 擋不住釣魚，passkey 卻可以？如果攻擊者在釣魚網站上即時轉送 passkey 的 challenge，會發生什麼？
> 密碼與 TOTP 都是使用者可以「看到並輸入」的值，值本身不包含它是在哪個網站被輸入的資訊。釣魚網站收下之後在有效期限內轉送到真網站，伺服器只能判斷值是否正確，無法分辨輸入者是誰，所以 TOTP 只提高了攻擊的時間壓力，沒有改變攻擊的可行性。
>
> passkey 的回應是一個簽章，簽章範圍包含 clientDataJSON（challenge 與 origin）與 authenticatorData（RP ID 的雜湊）。攻擊者把真網站的 challenge 轉給受害者的瀏覽器時，瀏覽器看網址列是釣魚網域，會拒絕使用真網站的 RP ID；釣魚網站若改用自己的 RP ID，authenticator 裡沒有對應的 credential；即使有個不檢查的壞 client 讓 authenticator 簽了，origin 也會是釣魚網域，真網站驗證時拒絕。使用者沒有任何可轉交的值，這就是本章實驗二第 3 到 5 行展示的三道防線。

> [!question]- Q7. 聲聲 Live 目前只有 `www.shengsheng.example`，之後會加 `teacher.shengsheng.example` 與一個不同網域的合作品牌網站。RP ID 應該怎麼選？
> RP ID 決定 credential 屬於哪個網域，瀏覽器只允許 RP ID 等於目前網頁的網域或其上層的可註冊網域。如果現在把 RP ID 設成 `www.shengsheng.example`，之後的 `teacher.shengsheng.example` 不是它的子網域，無法使用同一把 passkey；而 RP ID 一旦用於註冊就無法更改，改了等於讓所有使用者的 passkey 失效。所以應該一開始就選 `shengsheng.example`，讓所有子網域共用。
>
> 不同網域的合作品牌網站則不能直接使用 `shengsheng.example` 這個 RP ID。WebAuthn Level 3 的 Related Origin Requests 允許 RP ID 網域在固定的 well-known 路徑宣告「哪些其他 origin 可以使用我的 RP ID」，瀏覽器支援時就能共用；另一個常見做法是讓合作網站透過 OIDC 導到 `auth.shengsheng.example` 登入，passkey 只在聲聲 Live 自己的網域上使用。伺服器端也要明確列出允許的 origin，不能只檢查 RP ID。

> [!question]- Q8. 手算：某次 passkey 登入的 authenticatorData 前 37 bytes，最後 5 個 byte 是 `1d 00 00 00 00`。這代表什麼？伺服器該怎麼處理 signCount？
> authenticatorData 的前 32 bytes 是 RP ID 的 SHA-256，第 33 個 byte 是 flags，接著 4 bytes 是 big-endian 的 signCount。所以 flags 是 `0x1d`，二進位 0001 1101：bit 0 的 UP 是 1（使用者在場），bit 2 的 UV 是 1（做了指紋、臉部或 PIN 驗證），bit 3 的 BE 是 1（可備份），bit 4 的 BS 是 1（目前已備份），bit 6 的 AT 與 bit 7 的 ED 都是 0，表示這是登入而非註冊，也沒有 extensions。signCount 是 `00 00 00 00`，也就是 0。
>
> BE 與 BS 都是 1、signCount 為 0，最符合的解釋是一個雲端同步的 passkey：同步型 credential 存在多台裝置上，無法維持單一遞增的計數器，所以多半固定回報 0。伺服器應該把計數 0 視為「不支援計數」，跳過倒退檢查，否則會誤判並擋下正常使用者；只有當儲存的值與新值都不是 0、而新值沒有大於舊值時，才把它當成可能被複製的警訊。UV 為 1 則表示這次登入可以滿足要求使用者驗證的政策，例如修改課酬帳戶。

## 延伸閱讀

- OpenID Foundation〈OpenID Connect Core 1.0〉：ID token、claims、驗證步驟與各種流程的定義
- OpenID Foundation〈OpenID Connect Discovery 1.0〉、〈OpenID Connect RP-Initiated Logout 1.0〉、〈OpenID Connect Front-Channel Logout 1.0〉、〈OpenID Connect Back-Channel Logout 1.0〉
- W3C〈Web Authentication: An API for accessing Public Key Credentials Level 3〉：WebAuthn 的註冊、驗證與資料結構
- RFC 7519〈JSON Web Token (JWT)〉與 RFC 7517〈JSON Web Key (JWK)〉
- RFC 9207〈OAuth 2.0 Authorization Server Issuer Identification〉：用 `iss` 參數防止 mix-up attack
- RFC 7643〈System for Cross-domain Identity Management: Core Schema〉與 RFC 7644〈SCIM: Protocol〉
- OASIS〈Assertions and Protocols for the OASIS Security Assertion Markup Language (SAML) V2.0〉
- FIDO Alliance 關於 passkeys 的技術文件與部署指南
