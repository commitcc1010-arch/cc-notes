---
chapter: 27
title: Token 與 JWT：簽發、驗證與撤銷
part: 6
---

# 第 27 章　Token 與 JWT：簽發、驗證與撤銷

> [!abstract] 本章地圖
> **核心問題**：API 只看一串 token 就決定「你是誰、能做什麼」。這串 token 要怎麼簽、怎麼驗、放在哪裡、出事時怎麼收回，才不會變成一把誰撿到都能用的萬能鑰匙？
>
> **你會學到**：
> - 分辨 opaque token 與 self-contained token，說清楚 JWT 用「不必查資料庫」換來了什麼代價
> - 逐段拆開一個 JWT，手動做 base64url 編解碼，並理解「簽章不等於加密」
> - 比較 HS256、RS256、ES256 的金鑰分工，知道什麼時候一定要用非對稱簽章
> - 寫出完整的驗證清單（alg 允許清單、kid、簽章、exp／nbf／iat 與時鐘偏差、iss、aud、typ），並說出每一步擋下哪一種錯誤 token
> - 設計 JWKS 發布與金鑰輪替的時間表，以及短效 access token 加 refresh token 輪替與重用偵測
> - 依 XSS 與 CSRF 的風險，決定 token 放在 cookie 還是 Authorization header
>
> **前置知識**：第 21 章（cookie 的語法）、第 23 章（SameSite、CSRF、XSS 與 CORS）、第 26 章（session 與密碼驗證）

## 27.1 故事：停權三小時後還在改課表的帳號

星期三下午兩點零五分，聲聲 Live 的營運團隊停權了一位違規私下收費的老師，帳號 `teacher:1024`。後台顯示「已停權」，網站上的 session 也立刻失效，大家以為事情結束了。五點二十分，客服收到學生的抱怨：這位老師剛剛又把自己下週的課全部改了時間。營運同事截圖給小晴看，API 的 access log 清清楚楚寫著 `PUT /v1/classes/7781/schedule 200`，而且是從這位老師的手機 App 發出的。

小晴負責維護 API 的驗證 middleware。網站用的是 server-side session（第 26 章），停權時直接刪掉 session 就好；手機 App 則在登入後拿到一個 JWT，之後每個 API 請求都放在 `Authorization` header 裡。小晴打開 token 一看，`exp` 減掉 `iat` 是 604,800 秒，整整七天。API 收到 token 只驗簽章與效期，從來不查資料庫，所以停權這件事 API 根本不知道。

資安工程師 Rita 聽說後，順手審查了整段驗證程式，報告列出另外三個問題：演算法是從 token 的 header 讀出來決定的；沒有檢查 `aud`，發給教室聊天服務的 token 拿來呼叫課表 API 也會通過；簽 token 的 HS256 secret 同時放在 API、聊天服務 `chat`、推薦服務 `reco` 的設定檔裡。阿德看完報告只說了一句：「第一個問題是今天的事故，後面三個是還沒發生的事故。」

```text
 14:00        14:05             17:20                          隔週三 14:00
   │            │                 │                                 │
   ●────────────┼─────────────────┼────────────────────────────────►│
 App 登入，     後台停權          老師用同一個 token                  token 的 exp
 拿到 7 天的    · 網站 session    PUT /schedule → 200                （到這時 API 才會拒絕）
 JWT           立刻刪除          API 只驗簽章與 exp，
               · JWT 沒人管得到   不知道帳號已停權
```

這條時間軸說明了 JWT 最根本的取捨。網站的 session 是一筆存在伺服器上的紀錄，刪掉它，下一個請求就失敗；JWT 則是一張「自己帶著證明」的通行證，API 驗完簽章就相信它，簽出去以後伺服器沒有地方可以「刪掉」它。效期七天，就代表停權最慢要七天才生效。這不是 JWT 的 bug，而是設計時沒有把撤銷算進去。

這一章要回答小晴當天的所有疑問：token 有哪幾種、JWT 裡面裝了什麼、簽章到底保護了什麼、一個正確的驗證函式要檢查哪些欄位、金鑰怎麼換、怎麼把一張已經發出去的通行證收回來，以及 token 應該放在瀏覽器的哪裡。章末的動手做會用 Python 標準函式庫寫出一個驗證器，再用十八個錯誤 token 逐一證明每個檢查都有用。

## 27.2 Token 是什麼：opaque token 與 self-contained token

**Token**（權杖）是「登入之後拿到、之後每次請求都出示的一串字」，用來代替每次重送帳號密碼。它像遊樂園的手環：入口驗過票之後給你手環，之後每個設施只看手環，不再看門票。API 世界最常見的是 **bearer token**（持有者權杖）：誰拿著它，誰就能用它，伺服器不會再問「你是不是當初那個人」。這個「撿到就能用」的特性，是本章所有防禦措施的出發點。

Token 依「伺服器怎麼知道它代表誰」分成兩類。**Opaque token**（不透明 token）只是一串隨機字元，例如 `secrets.token_urlsafe(32)` 產生的 43 個字元；它本身不帶任何資訊，伺服器要拿它去資料庫或 auth server 查「這串是誰的、還有效嗎」，就像衣帽間的號碼牌。**Self-contained token**（自帶資訊的 token）則把「是誰、能做什麼、何時到期」直接寫在 token 裡，再加上簽章防止竄改，伺服器只要驗簽章就能相信內容，就像蓋了鋼印的通行證。JWT 是 self-contained token 最主流的格式。

```text
 (a) opaque token：每次都要問發行者                (b) self-contained token（JWT）：自己驗
 App ── Bearer 9f3k…x2 ──► API                     App ── Bearer eyJhbGci… ──► API
                            │                                                   │
                            │ 查：這串是誰？還有效嗎？                          │ 用公鑰／secret 驗簽章
                            ▼                                                   │ 讀 payload：sub、scope、exp
                   token 資料表／auth server                                    │（不連任何外部系統）
                   （introspection）                                            ▼
                            │                                            直接決定 200 或 401
                            ▼
                   撤銷 = 刪掉這一筆，下一個請求立刻失敗
```

左邊的 (a) 每個請求都多一次查詢：API 拿 token 去自己的資料表查，或呼叫 auth server 的 **introspection** 端點（RFC 7662 定義的「請告訴我這個 token 的狀態」API）。好處是控制權集中，撤銷立即生效；代價是每個請求多一次往返，auth server 一掛，所有 API 一起掛。右邊的 (b) 在 API 本地就能完成驗證，延遲低、可以水平擴展，也不怕 auth server 短暫故障；代價就是故事裡的問題：簽出去的 token 在到期前一直有效，而且 token 裡的資訊（例如角色）是簽發當下的快照，之後改了權限也不會反映出來。

| 面向 | opaque token | self-contained token（JWT） |
|---|---|---|
| 驗證方式 | 查資料庫或 introspection | 本地驗簽章與 claims |
| 每個請求的額外成本 | 一次查詢（可快取） | 一次簽章驗證（微秒到毫秒等級） |
| 撤銷 | 刪掉紀錄即生效 | 等到過期，或另建撤銷機制 |
| 權限變更 | 下一個請求就反映 | 要等 token 換新 |
| 大小 | 數十個字元 | 數百到上千個字元 |
| 內容外洩風險 | 本身沒有資訊 | payload 任何人都讀得到 |
| 適合 | 瀏覽器 session、refresh token、需要即時撤銷的場合 | 微服務之間、多個 API 共用同一個發行者、要求低延遲的 access token |

實務上兩者常常一起用。聲聲 Live 修正後的設計是：access token 用 JWT，效期五分鐘，讓 API 不必每次查資料庫；refresh token 用 opaque token，存在 auth server，用來換新的 access token，也是撤銷的控制點。這樣「最慢多久生效」從七天縮短到五分鐘，而大部分請求仍然不必查資料庫。27.8 節會把這套設計完整走一遍。

> [!warning] 常見誤解
> 「JWT 比 session 安全」或「session 比 JWT 安全」都是錯的比較。兩者解決的是不同的分工問題：session 把狀態留在伺服器，JWT 把狀態交給 token。網站本身用 HttpOnly session cookie 通常最簡單（第 26 章）；JWT 的價值在於「發行者」和「驗證者」是不同系統時，驗證者不必回頭問發行者。

## 27.3 JWT 的結構：三段 base64url

**JWT**（JSON Web Token，RFC 7519）是一段用兩個句點分成三段的文字：header、payload、signature。嚴格說，我們天天看到的 JWT 是 **JWS**（JSON Web Signature，RFC 7515）的 compact 格式，也就是「加了簽章的 JSON」；另一種 **JWE**（JSON Web Encryption，RFC 7516）才是加密的版本，有五段。本章說的 JWT 都是 JWS 形式。

```text
 eyJhbGciOiJIUzI1NiIs…  .  eyJpc3MiOiJodHRwczovL2F1…  .  voHBqRjnMrxtdwGnjnEd…
 └────── header ──────┘     └─────── payload ───────┘     └───── signature ─────┘
  base64url(JSON)            base64url(JSON)               base64url(32 bytes，HS256)
  {"alg":"HS256",            {"iss":"…auth…",              HMAC-SHA256(key,
   "typ":"at+jwt",            "sub":"teacher:1024",          ASCII(header "." payload))
   "kid":"k2026-10"}          "aud":"api.shengsheng…",
                              "iat":1790000000,
                              "exp":1790000300,
                              "scope":"schedule:write"}
 ├───────────────── signing input（被簽章保護的範圍）────────────┤
```

由左而右讀。**header** 是一個 JSON 物件，說明「這個 token 怎麼簽的」：`alg` 是演算法，`typ` 是 token 的種類，`kid`（key ID）指出用哪一把金鑰簽。**payload** 是另一個 JSON 物件，裝著 **claims**（聲明，也就是 token 對持有者做的陳述），例如「這是 `teacher:1024`」「可以寫課表」。兩者各自用 base64url 編碼，用句點接起來，這串文字就是 **signing input**；signature 是對這串**文字**計算出來的簽章，再做一次 base64url。注意簽章保護的是 header 與 payload 兩段，所以連 header 裡的 `alg` 被改都會讓簽章失效；但驗證者必須先讀 header 才知道要怎麼驗，這個「先讀未經驗證的資料」的順序問題，就是 27.6 節大部分漏洞的根源。

**base64url**（RFC 4648 第 5 節）是 base64 的變形。base64 把每 3 個 byte 切成 4 組 6 bit，各對應一個可列印字元；標準字母表的第 62、63 個字元是 `+` 和 `/`，不足 3 byte 時用 `=` 補齊。這三個字元在 URL 與 header 裡都有特殊意義，所以 base64url 把 `+` 換成 `-`、`/` 換成 `_`，並且在 JWT 裡**省略結尾的 `=`**。解碼時要自己把 padding 補回去，長度除以 4 餘 2 補兩個 `=`、餘 3 補一個，餘 1 則不可能是合法的編碼。

```python
import base64
import hashlib
import hmac
import json


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))  # 補回被省略的 padding


# 同一串 bytes：標準 base64 會出現 + / =，放進 URL 或 header 都要再轉義；base64url 不會
sample = bytes([0xFB, 0xEF, 0xFF, 0xFE])
print("base64    :", base64.b64encode(sample).decode())
print("base64url :", b64url_encode(sample))

header = {"alg": "HS256", "typ": "at+jwt", "kid": "k2026-10"}
payload = {"iss": "https://auth.shengsheng.example", "sub": "teacher:1024",
           "aud": "api.shengsheng.example", "iat": 1790000000, "exp": 1790000300,
           "scope": "schedule:write"}
secret = hashlib.sha256(b"demo-k2026-10").digest()   # 示範用；真實金鑰用 secrets.token_bytes(32)

h = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
p = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
signing_input = f"{h}.{p}"                              # 簽的是「編碼後的文字」，不是 JSON 物件
s = b64url_encode(hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest())
token = f"{signing_input}.{s}"

print("token 長度:", len(token), "字元")
for name, part in zip(("header", "payload", "signature"), token.split(".")):
    print(f"{name:<9}: {part[:40]}{'…' if len(part) > 40 else ''}（{len(part)} 字元）")

# 任何拿到 token 的人，不需要金鑰就能讀出內容：JWT 預設只簽章、不加密
peek = json.loads(b64url_decode(token.split(".")[1]))
print("不用金鑰解出 payload:", peek["sub"], peek["scope"])
print("簽章原始長度:", len(b64url_decode(s)), "bytes")
assert peek == payload and "=" not in token and len(b64url_decode(s)) == 32
```

```text
base64    : ++///g==
base64url : --___g
token 長度: 311 字元
header   : eyJhbGciOiJIUzI1NiIsInR5cCI6ImF0K2p3dCIs…（63 字元）
payload  : eyJpc3MiOiJodHRwczovL2F1dGguc2hlbmdzaGVu…（203 字元）
signature: voHBqRjnMrxtdwGnjnEdj6kmKgzFUMoX4daFd0Qd…（43 字元）
不用金鑰解出 payload: teacher:1024 schedule:write
簽章原始長度: 32 bytes
```

第一組輸出用同樣四個 byte 對照兩種編碼：標準 base64 是 `++///g==`，base64url 是 `--___g`，字元換掉、padding 去掉。接著程式手工組出一個 HS256 token，三段分別是 63、203、43 個字元。header 與 payload 都以 `eyJ` 開頭，因為 `{"` 的 base64 恰好是 `eyJ`；在 log 或錯誤訊息裡看到 `eyJ` 開頭的字串，幾乎可以確定是 JWT，這也是很多 secret 掃描工具的偵測規則。簽章段 43 個字元解碼後是 32 bytes，正是 SHA-256 的輸出長度。

最重要的是倒數第二行：程式**完全沒用到金鑰**就讀出了 `sub` 與 `scope`。JWT 的簽章只保證「內容沒被改過、確實是持有金鑰的人簽的」，不保證保密。所以 payload 不能放密碼、身分證號、病歷這類資料；也要記得 token 會出現在 log、瀏覽器 DevTools、當機回報裡，任何看得到 token 的人都看得到 payload。真的需要保密，用 JWE，或乾脆改用 opaque token 讓資料留在伺服器上。

RFC 7519 定義了七個**註冊 claims**（registered claims），名稱刻意只用三個字母以節省空間。時間類 claims 的值是 **NumericDate**：從 1970-01-01 UTC 起算的秒數，例如 1790000000 就是 2026 年 9 月下旬的某個時刻。

| claim | 全名 | 意思 | 驗證者要做什麼 |
|---|---|---|---|
| `iss` | issuer | 誰簽發的，例如 `auth.shengsheng.example` 的 https 網址 | 和設定值精確比對 |
| `sub` | subject | 這個 token 代表誰，例如 `teacher:1024` | 在 iss 範圍內唯一；授權判斷的主體 |
| `aud` | audience | 這個 token 是給誰用的，字串或字串陣列 | 必須包含自己的識別字，否則拒絕 |
| `exp` | expiration time | 這個時間點（含）之後不得接受 | 目前時間要早於 exp（可加時鐘偏差） |
| `nbf` | not before | 這個時間點之前不得接受 | 目前時間不能早於 nbf（可加時鐘偏差） |
| `iat` | issued at | 簽發時間 | 用來算 token 年齡、和「某時間點之後才有效」的規則比較 |
| `jti` | JWT ID | 這個 token 的唯一編號 | 用於撤銷清單與防重放 |

除了這七個，payload 可以放任何自訂 claims，例如 OAuth 常用的 `scope`（以空白分隔的權限清單）、`client_id`，或聲聲 Live 自己的 `tenant`。自訂 claim 的名稱要避免和註冊名稱衝突，也要克制：每多一個 claim，每個請求就多帶幾十個 byte，而 token 越大，越容易撞上 cookie 與 header 的大小上限（27.9 節）。

## 27.4 簽章演算法：HS256、RS256 與 ES256

header 的 `alg` 說明簽章用的演算法，名稱定義在 JWA（JSON Web Algorithms，RFC 7518）。工作上最常見的三種，代表兩種完全不同的金鑰分工。

**HS256** 是 HMAC-SHA256：簽章與驗證用**同一把**秘密金鑰（對稱金鑰）。計算方式和第 17 章的 webhook 簽章一樣，對 signing input 算 HMAC，結果 32 bytes。它快、實作簡單、token 短，但有一個結構性的問題：**能驗證的人就能簽發**。RFC 7518 也規定 HS256 的金鑰至少要和雜湊輸出一樣長，也就是 256 bit；用人想得出來的字串當 secret，拿到任何一個 token 的人都能離線猜測金鑰，所以金鑰一定要用 `secrets.token_bytes(32)` 這類密碼學亂數產生。

**RS256** 是 RSA 簽章（RSASSA-PKCS1-v1_5 搭配 SHA-256），**ES256** 是 ECDSA 搭配 P-256 曲線與 SHA-256：兩者都是**非對稱**簽章，私鑰簽、公鑰驗。私鑰只放在 auth server，公鑰可以公開發布給所有 API。RSA 2048 bit 的簽章長 256 bytes，base64url 後約 342 個字元；ES256 的簽章是兩個 32 bytes 整數 r 與 s 直接相接的 64 bytes（注意 JWS 用的是這種固定長度格式，不是其他場合常見的 DER 編碼），base64url 後 86 個字元。另外還有 PS256（RSA-PSS）與 EdDSA 等選項，選用前要確認所有驗證端的函式庫都支援。

```text
 HS256：一把共用 secret，人人都能簽                 RS256／ES256：私鑰只在一處
 ┌───────────────┐                                  ┌───────────────────────────┐
 │ auth server   │ secret S                         │ auth.shengsheng.example   │ 私鑰（只有這裡有）
 └───────┬───────┘                                  └─────────────┬─────────────┘
         │ 同一把 S 複製到各處                                     │ 公開發布公鑰（JWKS）
   ┌─────┼──────────────┐                           ┌──────────────┼──────────────┐
   ▼     ▼              ▼                           ▼              ▼              ▼
 ┌─────┐ ┌──────┐ ┌──────┐                       ┌─────┐       ┌──────┐       ┌──────┐
 │ API │ │ chat │ │ reco │                       │ API │       │ chat │       │ reco │
 │  S  │ │  S   │ │  S   │                       │ pub │       │ pub  │       │ pub  │
 └─────┘ └──────┘ └──────┘                       └─────┘       └──────┘       └──────┘
 任何一處外洩 S → 可以簽出被所有服務接受的 token    公鑰外洩無妨：拿到公鑰也簽不出 token
```

左邊是故事裡聲聲 Live 原本的樣子：同一把 S 放在三個服務的設定檔裡，攻擊面是三個服務加上它們的設定管理系統、CI log、備份，只要其中一處外洩，對方就能簽出 API 接受的任何 token，包括 `sub` 是管理員的那種。右邊把簽發能力集中在 auth server，其他服務只拿公鑰（圖中的 pub）；公鑰本來就是公開的，外洩不會讓任何人多出簽發能力。下面這段程式把左邊的風險具體化：

```python
import base64
import hashlib
import hmac
import json

SHARED = hashlib.sha256(b"demo-shared-secret").digest()   # auth、API、聊天服務三方都有這把


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def hs256(secret: bytes, claims: dict) -> str:
    h = b64(json.dumps({"alg": "HS256", "typ": "at+jwt"}).encode())
    p = b64(json.dumps(claims, sort_keys=True).encode())
    sig = hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64(sig)}"


def api_accepts(token: str) -> bool:
    h, p, s = token.split(".")
    expected = b64(hmac.new(SHARED, f"{h}.{p}".encode(), hashlib.sha256).digest())
    return hmac.compare_digest(expected, s)           # 固定時間比較，不洩漏「前幾個字元對了」


real = hs256(SHARED, {"sub": "stu_1024", "scope": "chat:send"})
print("auth 簽的 token，API 接受？", api_accepts(real))

# 改 payload 裡的一個字：簽章完全對不上
h, p, s = real.split(".")
p2 = b64(json.dumps({"scope": "chat:send", "sub": "stu_1025"}, sort_keys=True).encode())
print("改了 sub 沿用舊簽章，API 接受？", api_accepts(f"{h}.{p2}.{s}"))

# 對稱金鑰的問題：只要能「驗」就能「簽」。聊天服務的設定檔一旦外洩……
minted = hs256(SHARED, {"sub": "teacher:1024", "scope": "schedule:write"})
print("聊天服務自己簽的 token，API 接受？", api_accepts(minted))
assert api_accepts(real) and not api_accepts(f"{h}.{p2}.{s}") and api_accepts(minted)
```

```text
auth 簽的 token，API 接受？ True
改了 sub 沿用舊簽章，API 接受？ False
聊天服務自己簽的 token，API 接受？ True
```

前兩行是 HMAC 的正常行為：auth server 簽的 token 通過；只改 `sub` 一個字元卻沿用舊簽章，驗證失敗，因為簽章涵蓋整段 signing input。第三行就是 Rita 擔心的事：聊天服務的程式碼裡有同一把 secret，它簽出 `teacher:1024` 加上 `schedule:write` 的 token，API 無從分辨真偽。HMAC 數學上沒有任何漏洞，問題完全出在金鑰分工。程式裡的 `hmac.compare_digest` 也值得記住：用一般的 `==` 比較字串，比較到第一個不同的字元就會提早結束，回應時間會透露「前面幾個字元對了」；固定時間的比較函式不會有這個差異。

| 演算法 | 類型 | 簽章大小 | 誰能簽 | 適合的情境 |
|---|---|---|---|---|
| HS256 | 對稱（HMAC-SHA256） | 32 bytes | 任何持有 secret 的系統 | 發行者與驗證者是同一個服務，例如 auth server 簽給自己驗的短效 token |
| RS256 | 非對稱（RSA 2048 bit 以上） | 256 bytes（2048 bit） | 只有私鑰持有者 | 多個 API 共用發行者；與舊系統相容性最好 |
| ES256 | 非對稱（ECDSA P-256） | 64 bytes | 只有私鑰持有者 | 同上，token 更短、金鑰更小 |
| none | 無簽章 | 0 | 任何人 | 不能用在任何需要信任的地方，驗證端必須拒絕 |

聲聲 Live 修正後的規則是：發給 API、聊天、推薦等其他服務驗證的 access token 一律用 ES256；HS256 只保留給「auth server 簽、auth server 自己驗」的內部用途。真實系統裡，非對稱簽章交給成熟的函式庫處理，不要自己實作。下面是 Python 最常用的 PyJWT 的介面（需要另外安裝 PyJWT 與 cryptography，本書的 checker 不會執行它）：

```python
# not-runnable：需要 pip install "pyjwt[crypto]"，示範 PyJWT 2.x 的介面
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa

# --- auth.shengsheng.example：只有這裡持有私鑰 ---
ec_private = ec.generate_private_key(ec.SECP256R1())           # ES256 用 P-256
rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

now = int(time.time())
claims = {"iss": "https://auth.shengsheng.example", "sub": "teacher:1024",
          "aud": "api.shengsheng.example", "iat": now, "exp": now + 300,
          "scope": "schedule:write"}
es_token = jwt.encode(claims, ec_private, algorithm="ES256",
                      headers={"kid": "es-2026-10", "typ": "at+jwt"})
rs_token = jwt.encode(claims, rsa_private, algorithm="RS256",
                      headers={"kid": "rs-2026-10", "typ": "at+jwt"})

# --- api.shengsheng.example：只拿到公鑰 ---
ec_public = ec_private.public_key()
payload = jwt.decode(
    es_token,
    ec_public,
    algorithms=["ES256"],                      # 固定允許清單：由我們決定，不看 header
    audience="api.shengsheng.example",
    issuer="https://auth.shengsheng.example",
    leeway=60,                                 # 時鐘偏差（秒）；PyJWT 預設是 0
    options={"require": ["exp", "iat", "iss", "aud", "sub"]},
)
# decode 成功之後 header 已確定受簽章保護；PyJWT 預設不檢查 typ，要自己檢查
if jwt.get_unverified_header(es_token).get("typ") != "at+jwt":
    raise jwt.InvalidTokenError("not an access token")
print(payload["sub"])
```

這段程式裡最值得注意的是 `jwt.decode` 的參數，它們就是下一節驗證清單的縮影：`algorithms` 是允許清單，`audience` 與 `issuer` 要求精確比對，`leeway` 處理時鐘偏差，`require` 讓缺少必要 claim 的 token 直接失敗。PyJWT 會在 `algorithms` 沒給時拒絕解碼，這是函式庫替你擋下的坑；但 `typ` 與自訂的授權 claims 仍然要自己檢查。

## 27.5 驗證清單：每一步擋下什麼

驗證 JWT 不是「解開來看 exp」，而是一連串順序有意義的檢查。原則只有一句：**簽章通過之前，token 裡的任何東西都只能拿來「挑選」我們事先允許的選項，不能拿來「決定」怎麼驗**。下面是聲聲 Live 修正後的驗證流程，動手做會把它寫成程式：

```text
 收到 Authorization: Bearer <token>
   │
   ├─ ① 格式：恰好三段？每段是嚴格的 base64url？header 是 JSON 物件？ ── 否 ─► 401 malformed
   ├─ ② alg 在允許清單裡？（清單寫在設定裡，例如只有 ES256）       ── 否 ─► 401（擋 none、混淆）
   ├─ ③ typ 是 at+jwt？                                            ── 否 ─► 401（擋拿 ID token 冒充）
   ├─ ④ kid 在目前的金鑰集合裡？（只查表，不拿去組路徑或 URL）     ── 否 ─► 401（擋退役與偽造的 kid）
   ├─ ⑤ 用「該 kid 的金鑰＋允許的 alg」驗簽章                      ── 否 ─► 401 bad_signature
   │      ── 從這裡開始，payload 才可信 ──
   ├─ ⑥ 必要 claims 都在？型別正確？                               ── 否 ─► 401
   ├─ ⑦ exp、nbf、iat 在時鐘偏差容許範圍內？效期不超過上限？        ── 否 ─► 401 expired／not_yet_valid
   ├─ ⑧ iss 等於我們信任的發行者？                                 ── 否 ─► 401 wrong_issuer
   ├─ ⑨ aud 包含我自己？                                           ── 否 ─► 401 wrong_audience
   └─ ⑩ 授權：scope／角色允許這個操作？帳號沒有被撤銷？            ── 否 ─► 403 insufficient_scope
```

由上往下看。① 到 ④ 只讀 header，而且每一步都是「拿 header 的值去比對我們的設定」，不是「照 header 的指示做事」。② 的允許清單是整張圖最重要的一格：演算法由驗證端的設定決定，header 的 `alg` 只用來確認「它宣稱的和我們期待的一致」。⑤ 是唯一的密碼學步驟，用 ④ 查到的金鑰與 ② 允許的演算法計算。⑥ 到 ⑨ 才讀 payload，因為這時才知道 payload 沒被改過。⑩ 已經不是 JWT 本身的檢查，而是應用程式的授權邏輯：token 有效不代表這個人可以做這件事。

時間檢查需要多想一步。簽發 token 的 auth server 與驗證的 API 是不同機器，時鐘不可能完全一致；如果 API 的時鐘比 auth server 慢 30 秒，剛簽出的 token 的 `iat` 在 API 看來就在「未來」。所以時間比較都會加上一個**時鐘偏差容許值**（leeway 或 clock skew），通常 30 到 60 秒，搭配 NTP 讓所有機器校時。具體規則是：目前時間大於等於 `exp + leeway` 就算過期；目前時間加 leeway 仍早於 `nbf` 就算還沒生效。leeway 不能設太大，設成一小時，等於所有 token 的效期都偷偷多了一小時。

```text
                  nbf−60        nbf                    exp      exp+60
 ────────────────────┬───────────┬──────────────────────┬──────────┬─────►  驗證端時間
                     │◄─leeway──►│                      │◄─leeway─►│
 拒絕：not_yet_valid │◄────────────────── 接受 ───────────────────►│ 拒絕：expired
```

這條時間軸上，接受的範圍比 token 宣告的 `nbf` 到 `exp` 前後各寬 60 秒。本章的驗證器另外加了兩條 RFC 7519 沒有要求、但很實用的政策檢查：`iat` 不能在「現在加 leeway」之後，代表簽發端的時鐘或程式出錯；`exp − iat` 不能超過 15 分鐘，代表簽發端被設定成發長效 token，也就是故事裡那個七天的 token，會在 API 這一端就被擋下。

⑧ 與 ⑨ 是最常被省略的兩步，也最常出事。`iss` 回答「這是我信任的發行者簽的嗎」：staging 與 production 的 auth server 如果剛好共用同一把金鑰（這本身就是錯誤），沒有 iss 檢查就會讓 staging 的 token 在 production 通過。`aud` 回答「這張 token 是發給我的嗎」：同一個 auth server 簽給聊天服務的 token，簽章完全正確，但它不是給課表 API 的。少了 aud 檢查，任何一個服務收到的 token（例如被記進 log、或該服務本身被攻破）都可以拿去呼叫其他所有服務，這叫 **token 轉用**（token substitution 或 cross-service relay）。

> [!tip] 驗證失敗時回什麼
> 依 RFC 6750（OAuth 2.0 Bearer Token Usage），token 無效回 401 並帶 `WWW-Authenticate: Bearer error="invalid_token"`；token 有效但權限不足回 403 並帶 `error="insufficient_scope"`。給 client 的錯誤不要說明是哪一項檢查失敗，以免替攻擊者除錯；詳細原因寫進伺服器 log，並記錄 `kid`、`iss`、`aud` 與 token 的雜湊值，不要記錄整個 token。

> [!note] 2026 現況
> 截至 2026 年 10 月，JWT 的最佳實務仍以 RFC 8725〈JSON Web Token Best Current Practices〉為準，本節的允許清單、驗證 iss 與 aud、明確的 typ、不信任 header 中的 kid 與金鑰網址，都是它的建議。更新版 `draft-ietf-oauth-rfc8725bis-10`（2026-08-21）依 2026 年 10 月查證已獲 IESG 核准、進入 RFC Editor 佇列，但尚未取得 RFC 編號；正式發布後會取代 RFC 8725 並更新 RFC 7519，內容細節以正式版為準。access token 使用 `typ: at+jwt` 的做法來自 RFC 9068（OAuth 2.0 Access Token 的 JWT profile）。

## 27.6 JWT 的典型漏洞：成因與防禦

JWT 的漏洞很少出在密碼學本身，幾乎都出在「驗證端相信了不該相信的東西」。這一節只談成因與防禦，每一種都能對應回上一節驗證清單的某一格。

**alg 為 none。** JOSE 的演算法規格（RFC 7518）定義了 `none`，代表「沒有簽章」，原本是給已經由其他方式（例如 TLS 雙向驗證）保護的情境使用。早期有些函式庫的 `decode(token, key)` 會照 header 的指示選演算法，看到 `none` 就跳過簽章檢查，於是任何人都能把 payload 改成任意內容、把簽章段留空。防禦是驗證清單的 ②：演算法來自驗證端設定，`none` 永遠不在允許清單裡；使用函式庫時一定要明確傳入允許的演算法清單。

**演算法混淆**（algorithm confusion）。驗證端原本用 RS256，程式寫成「用這把 key 驗證，演算法看 header」。如果某人送來的 token 宣稱 `HS256`，有問題的函式庫會把手上那把 RSA **公鑰**的文字內容當成 HMAC 的 secret 來驗證；而公鑰是公開的，任何人都能用同樣的文字算出「正確」的 HMAC。整條攻擊鏈的根因只有一個：讓 token 決定金鑰的用法。

```text
 驗證端的設定：「這把是 RSA 公鑰，用來驗 RS256」
                │
 有問題的寫法：  decode(token, key=公鑰文字, alg=header["alg"])
                │                                   ▲
                │                       token 宣稱 HS256（未經驗證的資料）
                ▼
   把公鑰文字當成 HMAC secret ──► 公鑰人人可得 ──► 任何人都能算出通過的簽章
 ──────────────────────────────────────────────────────────────────────────────
 正確的寫法：    alg 由設定固定（只允許 ES256／RS256）；
                金鑰物件帶著型別（EC／RSA 公鑰），不是一串可以挪作他用的文字；
                kid → (金鑰, 允許的 alg) 一起查表
```

上半部是錯誤的資料流：`alg` 這個未經驗證的輸入，決定了金鑰被拿來做什麼。下半部是三層防禦：允許清單讓 HS256 根本進不來；把金鑰載入成有型別的物件，讓「RSA 公鑰」不可能被當成 HMAC secret；最好再把每個 kid 綁定到唯一的演算法，JWKS 裡的 `alg` 欄位就是為此存在。部分函式庫已經會拒絕把看起來像公鑰的字串當成 HMAC secret，但不能把安全建立在這種補救上。

**沒驗 aud 或 iss。** 上一節已經說明：簽章正確只證明「是我們的 auth server 簽的」，不證明「是簽給我的」。聲聲 Live 原本的 middleware 就是這樣，教室聊天服務 `rt.shengsheng.example` 的 token 能拿來改課表。防禦是每個服務都有自己的 audience 識別字，auth server 依 client 要求的資源簽出對應 aud 的 token（OAuth 的 resource indicators，RFC 8707，第 28 章），每個服務都只接受 aud 包含自己的 token。

**拿錯種類的 JWT。** 同一個 auth server 可能簽好幾種 JWT：OIDC 的 ID token（給 client 看「誰登入了」，第 29 章）、access token（給 API 看「可以做什麼」）、email 驗證連結裡的 token。它們都是同一把金鑰簽的，如果 API 只看簽章，就可能接受一個 ID token 當作 access token。防禦是 RFC 8725 說的**明確型別**（explicit typing）：access token 的 header 帶 `typ: at+jwt`，驗證端只接受這個型別，並且讓不同種類的 token 驗證規則互斥，例如 aud 不同、必要 claims 不同。

**相信 header 裡的金鑰來源。** JWS header 可以帶 `jku`（金鑰集合的網址）、`x5u`（憑證網址）甚至 `jwk`（直接內嵌一把公鑰）。如果驗證端照著這些欄位去取得金鑰，等於讓 token 自己指定「請用我提供的金鑰驗我」，任何人都能自備金鑰簽出通過的 token；去抓網址還會變成 SSRF（讓伺服器替攻擊者連線到內部網址）。`kid` 也一樣：它只是一個提示，有些實作把它拼進檔案路徑或 SQL 查詢，造成路徑穿越或注入。防禦是金鑰只來自設定好的發行者（固定的 JWKS 網址或本地 keyring），kid 只當查表用的 key，查不到就拒絕。

**弱 secret 與外洩的 token。** HS256 的 secret 如果是短字串，拿到一個合法 token 的人就能在自己的電腦上無限次嘗試猜測，完全不會觸發伺服器的任何告警。防禦是 256 bit 以上的隨機金鑰、存放在 secrets manager（第 30 章），並且定期輪替。token 本身的外洩則常見於 log：nginx 記錄完整的 query string、應用程式在錯誤處理時把整個 request header 印出來、前端把 token 放進網址。防禦是 token 只放在 header 或 cookie、log 遮罩 `Authorization`，並讓 access token 短效，縮小外洩之後的有效期間。

| 漏洞 | 成因（驗證端相信了什麼） | 擋下它的檢查 | 本章測試案例 |
|---|---|---|---|
| alg none | header 的 alg | ② 允許清單 | 「alg 宣稱 none」 |
| 演算法混淆 | header 的 alg 決定金鑰用法 | ② 允許清單＋有型別的金鑰 | 「alg 宣稱 RS256」 |
| 竄改 payload | 沒驗或驗錯簽章 | ⑤ 簽章 | 「payload 被竄改」 |
| token 轉用 | 只看簽章不看 aud | ⑨ aud | 「發給聊天服務的 token」 |
| 跨環境 token | 只看簽章不看 iss | ⑧ iss | 「iss 是 staging」 |
| 拿 ID token 當 access token | 不看 typ | ③ typ | 「typ 是 JWT」 |
| 自備金鑰、kid 注入 | header 的 jku／jwk／kid | ④ 只查表 | 「舊 kid，退役之後」 |
| 長效 token、停權不生效 | 簽發端設定 | ⑦ 效期上限＋27.8 節 | 「效期 7 天」 |

## 27.7 JWKS 與金鑰輪替

用了非對稱簽章，API 要怎麼拿到公鑰？最常見的做法是 auth server 在固定網址公布一份 **JWKS**（JSON Web Key Set，RFC 7517）：一個 JSON 物件，`keys` 陣列裡每個元素是一把 **JWK**（JSON Web Key，用 JSON 表示的金鑰）。OIDC 與 OAuth 的 metadata 文件（第 29 章的 discovery）會用 `jwks_uri` 欄位告訴大家這份 JWKS 在哪裡。一份只含公鑰的 JWKS 長這樣（座標值為示意）：

```text
{
  "keys": [
    { "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": "es-2026-09",
      "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU", "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0" },
    { "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": "es-2026-10",
      "x": "（另一把公鑰的 x 座標）", "y": "（y 座標）" }
  ]
}
```

每把 JWK 的 `kty` 是金鑰種類（EC、RSA、oct），`crv` 是曲線，`x` 與 `y` 是 EC 公鑰的兩個座標（RSA 公鑰則是 `n` 與 `e`），`use: sig` 表示用於簽章，`alg` 綁定這把金鑰唯一允許的演算法，`kid` 對應 token header 裡的 `kid`。驗證端收到 token，用 header 的 kid 在 JWKS 裡找到同名的公鑰，再用這把公鑰與它綁定的演算法驗簽章。JWKS 裡絕對不能出現私鑰欄位（EC 的 `d`、RSA 的 `d`、`p`、`q` 等）；發布前用程式檢查，是很便宜的保險。

**金鑰輪替**（key rotation）是定期換掉簽章金鑰，讓外洩的金鑰有使用期限，也讓團隊熟練「真的需要緊急換鑰」時的流程。輪替的難處在於：已經簽出去的 token 還在用舊金鑰，驗證端的 JWKS 快取也還是舊的。kid 讓新舊金鑰可以並存，正確的順序是「先發布、再使用、最後才移除」：

```text
 時間 ──────────────────────────────────────────────────────────────────────►
                T0 之前     │ T1 發布新公鑰       │ T2 改用新私鑰簽     │ T3 移除舊公鑰
 JWKS 內容      [舊]        │ [舊, 新]            │ [舊, 新]            │ [新]
 簽章金鑰       舊          │ 舊                  │ 新                  │ 新
 可驗的 token   舊          │ 舊                  │ 舊與新              │ 新
                            │◄─ ≥ JWKS 快取時間 ─►│◄─ ≥ 效期＋leeway ──►│
```

表格的每一欄是一個階段，最下面一列是兩段等待時間。T1 先把新公鑰加進 JWKS，但還不拿新私鑰簽任何 token；等待時間至少要等於驗證端的 JWKS 快取時間，確保每個 API 都已經看過新公鑰。T2 才切換簽章金鑰，這時新舊 token 混在一起流通，JWKS 裡兩把都在，所以都能驗。T3 等最後一個舊 token 也過期（token 的最長效期加上 leeway）才移除舊公鑰，所以「可驗的 token」那一列在 T2 之後同時包含新舊兩種。順序反過來就會出事：先用新私鑰簽、後發布公鑰，驗證端在快取更新前會拒絕所有新 token；太早移除舊公鑰，還在效期內的舊 token 會突然失效。聲聲 Live 用 HS256 的內部 keyring 也是同樣的三個階段，動手做的「舊 kid，輪替重疊期內」與「舊 kid，退役之後」兩個案例就是 T2 與 T3 之後的情況。

緊急輪替（私鑰疑似外洩）則反過來犧牲可用性：立刻移除舊公鑰，接受所有舊 token 失效、使用者重新整理或重新登入。如果 access token 短效、refresh token 存在伺服器端，這個代價只是一波 refresh 流量，這也是短效 token 的另一個好處。

驗證端怎麼快取 JWKS 也有學問。每個請求都去抓 JWKS 會讓 auth server 被自己的流量打垮；完全不更新又會錯過新金鑰。常見的做法是快取一段時間（並參考回應的 `Cache-Control`），遇到「沒看過的 kid」時提早重抓一次，但要有頻率上限，否則任何人送一堆亂編 kid 的 token，就能讓你的 API 去轟炸 auth server。下面的程式模擬這個策略：

```python
class JwksCache:
    """資源伺服器端的 JWKS 快取：定期更新，遇到沒看過的 kid 才提早重抓，而且有頻率上限。"""

    def __init__(self, fetch, ttl=3600, min_refetch=60):
        self.fetch, self.ttl, self.min_refetch = fetch, ttl, min_refetch
        self.keys, self.fetched_at, self.fetches = {}, None, 0

    def _refresh(self, now):
        self.keys = {k["kid"]: k for k in self.fetch(now)["keys"]}
        self.fetched_at, self.fetches = now, self.fetches + 1

    def get(self, kid, now):
        if self.fetched_at is None or now - self.fetched_at >= self.ttl:
            self._refresh(now)                        # 一般的定期更新
        if kid not in self.keys and now - self.fetched_at >= self.min_refetch:
            self._refresh(now)                        # 新金鑰可能剛發布：重抓一次
        if kid not in self.keys:
            raise KeyError(kid)                       # 仍然沒有：拒絕，不要一直打 auth server
        return self.keys[kid]


def auth_server_jwks(now):
    """模擬 auth server 在不同時間發布的 JWKS（只留下和本例有關的欄位）。"""
    keys = [{"kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": "es-2026-09"}]
    if now >= 1000:                                   # t=1000 預先發布新金鑰
        keys.append({"kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": "es-2026-10"})
    if now >= 5000:                                   # t=5000 舊金鑰退役
        keys.pop(0)
    return {"keys": keys}


cache = JwksCache(auth_server_jwks)
timeline = [(0, "es-2026-09"), (100, "es-2026-09"), (1100, "es-2026-10"),
            (1110, "junk-1"), (1120, "junk-2"), (1130, "junk-3"),
            (5400, "es-2026-09"), (5410, "es-2026-10")]
results = []
for t, kid in timeline:
    before = cache.fetches
    try:
        cache.get(kid, t)
        outcome = "找到"
    except KeyError:
        outcome = "拒絕"
    results.append(outcome)
    print(f"t={t:>4}  kid={kid:<11} → {outcome}  （這次抓了 {cache.fetches - before} 次 JWKS）")
print("總共抓 JWKS", cache.fetches, "次")
assert results == ["找到", "找到", "找到", "拒絕", "拒絕", "拒絕", "拒絕", "找到"]
assert cache.fetches == 3
```

```text
t=   0  kid=es-2026-09  → 找到  （這次抓了 1 次 JWKS）
t= 100  kid=es-2026-09  → 找到  （這次抓了 0 次 JWKS）
t=1100  kid=es-2026-10  → 找到  （這次抓了 1 次 JWKS）
t=1110  kid=junk-1      → 拒絕  （這次抓了 0 次 JWKS）
t=1120  kid=junk-2      → 拒絕  （這次抓了 0 次 JWKS）
t=1130  kid=junk-3      → 拒絕  （這次抓了 0 次 JWKS）
t=5400  kid=es-2026-09  → 拒絕  （這次抓了 1 次 JWKS）
t=5410  kid=es-2026-10  → 找到  （這次抓了 0 次 JWKS）
總共抓 JWKS 3 次
```

t=0 第一次使用時抓了 JWKS，t=100 直接用快取。t=1100 出現新的 `es-2026-10`，這時快取還沒到期，但因為 kid 沒看過、距離上次抓取也超過 60 秒，於是提早重抓一次並找到新公鑰，這就是輪替 T1 到 T2 之間會發生的事。接下來三個亂編的 kid 在 60 秒內連續出現，快取不再重抓，直接拒絕，auth server 完全不受影響。t=5400 快取到期而重抓，舊金鑰已經退役，用舊 kid 的 token 被拒絕。整段時間只抓了 3 次 JWKS。真實的函式庫也提供這類快取，例如 PyJWT 的 `PyJWKClient`：

```python
# not-runnable：需要 pip install "pyjwt[crypto]"
import jwt

# jwks_uri 來自 auth server 的 metadata；PyJWKClient 會快取抓到的 JWK Set
jwks_client = jwt.PyJWKClient("https://auth.shengsheng.example/.well-known/jwks.json")


def verify_access_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)  # 依 header 的 kid 找公鑰
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],                                  # 允許清單仍由我們決定
        audience="api.shengsheng.example",
        issuer="https://auth.shengsheng.example",
        leeway=60,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )
    if jwt.get_unverified_header(token).get("typ") != "at+jwt":  # 簽章已驗過，header 可信
        raise jwt.InvalidTokenError("not an access token")
    return payload
```

`get_signing_key_from_jwt` 只是用 header 的 kid 從 JWKS 挑出金鑰，挑選範圍是我們設定的那一個 JWKS 網址，不是 token 指定的地方；之後的 `decode` 和 27.4 節一樣，允許清單、aud、iss、leeway、必要 claims 一個都不能少。JWKS 網址本身也要寫在設定裡並使用 HTTPS（第 18 章），因為能竄改 JWKS 回應的人，就能讓你信任任何金鑰。

## 27.8 撤銷：短效 access token 與 refresh token 輪替

回到故事的根本問題：JWT 簽出去之後收不回來。撤銷的方法有好幾種，各自用不同程度的「狀態」換取即時性：

| 方法 | 怎麼做 | 生效時間 | 代價 |
|---|---|---|---|
| 只靠短效期 | access token 只活 5 分鐘 | 最長一個效期 | 需要 refresh 機制，否則使用者一直重新登入 |
| 撤銷清單（denylist） | 把要撤銷的 `jti` 放進共享快取，保存到它的 exp 為止 | 下一個請求 | 每個請求查一次快取，回到「有狀態」 |
| 使用者層級的時間戳記 | 停權或改密碼時記下時間，`iat` 早於它的 token 一律拒絕 | 下一個請求 | 每個請求查一次使用者狀態（可快取數秒） |
| introspection | 每次問 auth server 這個 token 的狀態 | 下一個請求 | 最重、最即時，等於改用 opaque token |
| 撤銷 refresh token | 刪掉 auth server 上的 refresh token 紀錄 | 目前的 access token 過期時 | 需要 refresh token 存在伺服器端 |

這張表沒有完美的答案，只有「你願意為多快生效付多少成本」。聲聲 Live 的組合是：access token 5 分鐘、refresh token 存在 auth server 並且每次使用都輪替；停權時刪掉該帳號所有 refresh token，並把停權時間寫進一個 API 會快取 30 秒的「使用者狀態」表，給修改課表、提款這類高風險操作額外檢查。一般讀取請求最多晚 5 分鐘生效，高風險操作最多晚 30 秒。

**refresh token**（更新權杖）是一個效期較長（例如 14 天）、只用來向 auth server 換新 access token 的憑證。它只送往 auth server，不送往 API，所以暴露面比 access token 小得多。但它活得久，外洩的傷害也大，於是有了**refresh token 輪替**（rotation）：每次用 refresh token 換新的 access token 時，auth server 同時發一個新的 refresh token，舊的立刻作廢。同一條登入產生的一連串 refresh token 叫做一個**家族**（family）。輪替帶來一個很漂亮的副作用：**重用偵測**（reuse detection）。

```text
 App                       竊取者                         auth server
  │── 登入 ──────────────────────────────────────────────►│ 家族 F：RT1（有效）
  │◄────────────────────────────── AT1（5 分鐘）＋ RT1 ───│
  │       （RT1 不小心被寫進一份外流的 debug log）        │
  │── t=290 用 RT1 換新 ─────────────────────────────────►│ RT1 → 已使用；RT2（有效）
  │◄─────────────────────────────────────── AT2 ＋ RT2 ───│
  │                          │── t=400 用 RT1 ───────────►│ RT1 已使用過又出現！
  │                          │◄──── 拒絕 ─────────────────│ 撤銷整個家族 F（RT2 也失效）
  │── t=590 用 RT2 換新 ─────────────────────────────────►│ 家族已撤銷
  │◄─────────────────────────────────── 拒絕，請重新登入 ─│ 通知使用者、留下資安事件紀錄
```

逐步看。App 登入後拿到 AT1 與 RT1；t=290 正常輪替，RT1 被標記為已使用，App 拿到 RT2。t=400 竊取者拿出 RT1，auth server 發現「一個已經用過的 refresh token 又出現了」，這只有兩種可能：合法 App 的舊副本，或者有人偷了它。auth server 分不出是哪一種，所以最安全的做法是撤銷整個家族，連還沒用過的 RT2 一起作廢。t=590 合法 App 也被拒絕，只能重新登入；這對使用者有一點打擾，但竊取者手上的東西全部失效了。注意順序反過來也成立：如果竊取者先用 RT1 換到 RT2'，合法 App 接著拿 RT1 來換，同樣會觸發重用偵測。

OAuth 2.0 Security BCP（RFC 9700）要求發給 public client（手機 App、單頁應用這種無法保管 client secret 的 client）的 refresh token，必須做 sender-constrained（綁定持有者的金鑰，例如 DPoP 或 mTLS）或輪替，第 28 章會從 OAuth 的角度再談一次。實作上要留意一個副作用：App 在網路不穩時可能重送同一個 refresh 請求，第二次就會被當成重用；有些系統會給極短的寬限期（例如幾秒內的重送回傳同一組結果），這是可用性與安全性的取捨，寬限期越長，偷來的 token 越容易混過去。

> [!warning] 常見誤解
> 「把 access token 改成 24 小時，refresh 次數少一點，對 auth server 比較好。」auth server 的負擔確實會降低，但換來的是故事裡的問題：停權、改密碼、權限調降最慢 24 小時才生效，外洩的 token 也能用 24 小時。5 到 15 分鐘的 access token 加上 refresh，是業界常見的平衡點；真正需要減輕 auth server 負擔時，該做的是讓 refresh 請求便宜（例如資料表索引、快取使用者狀態），而不是延長 access token。

## 27.9 token 放在哪裡：cookie 還是 Authorization header

token 簽得再好，放錯地方一樣會被偷。在瀏覽器裡，選擇主要有兩條路，各自對應第 23 章的兩種攻擊。

**放在 JavaScript 可以讀的地方**（記憶體、`localStorage`、`sessionStorage`），每個請求由前端程式手動加上 `Authorization: Bearer …`。好處是瀏覽器不會自動帶上它，**CSRF**（跨站請求偽造：別的網站讓使用者的瀏覽器送出請求，順便帶上自動附加的憑證）天生無效。壞處是任何一段在你的頁面上執行的 JavaScript 都讀得到它：一個 **XSS** 漏洞（讓攻擊者的腳本在你的網頁裡執行）就能把 token 送到外面，而且是可以在攻擊者自己的電腦上繼續使用的 bearer token。`localStorage` 的內容還會一直留在磁碟上，直到程式刪除。

**放在 HttpOnly cookie**。HttpOnly 讓 JavaScript 讀不到 cookie，XSS 無法把它偷走；Secure 讓它只在 HTTPS 上傳送。代價是 cookie 會由瀏覽器自動附加，回到 CSRF 的戰場，需要 SameSite、CSRF token 或檢查 Origin header 等防禦（第 23 章）。還要知道 HttpOnly 是「防偷不防用」：XSS 雖然拿不走 cookie，仍然可以在受害者的頁面上直接呼叫你的 API，瀏覽器照樣附上 cookie。所以 cookie 方案降低的是「外洩之後在別處使用」的傷害，不是讓 XSS 變得無害；CSP 與輸出跳脫仍然是根本防線。

```text
 (a) SPA 自己拿 token（不建議用在處理敏感資料的瀏覽器應用）
 瀏覽器 JS ── Authorization: Bearer <AT> ──► api.shengsheng.example
   └─ AT／RT 在 JS 可讀的地方：XSS 一次就能帶走，帶走後可在任何地方使用

 (b) BFF（Backend for Frontend）：瀏覽器只有 session cookie
 瀏覽器 ── Cookie: __Host-sid=…（HttpOnly; Secure; SameSite=Lax）──► www 的 BFF
                                                                        │ 伺服器端保管 AT／RT
                                                                        │ 代為加上 Authorization
                                                                        ▼
                                                              api.shengsheng.example

 (c) 手機 App：沒有瀏覽器的 cookie 與 CSRF 問題
 App ── Authorization: Bearer <AT> ──► api.shengsheng.example
   └─ RT 放在系統提供的安全儲存（iOS Keychain、Android Keystore 保護的儲存）
```

(a) 是許多單頁應用（SPA）的預設寫法，簡單但把最敏感的東西放在最容易被 XSS 接觸的地方。(b) 是 **BFF**（Backend for Frontend）模式：瀏覽器只拿到一個不透明的 session cookie，真正的 access token 與 refresh token 留在和網站同 origin 的後端，由後端代為呼叫 API；token 從來不進入 JavaScript，CSRF 則用 SameSite 與第 23 章的方法處理。(c) 是手機 App：原生 App 沒有「別的網站順便帶 cookie」的問題，用 Authorization header 最直接，refresh token 放在作業系統提供的安全儲存。聲聲 Live 的網站走 (b)，手機 App 走 (c)。

```python
import secrets
from http.cookies import SimpleCookie

# 瀏覽器（BFF 模式）：只拿到一個不透明的 session id，token 留在伺服器端
cookie = SimpleCookie()
cookie["__Host-sid"] = secrets.token_urlsafe(32)
attrs = cookie["__Host-sid"]
attrs["path"] = "/"            # __Host- 前綴要求 Path=/、Secure，而且不能有 Domain
attrs["secure"] = True
attrs["httponly"] = True       # JavaScript 讀不到：XSS 偷不走它
attrs["samesite"] = "Lax"      # 跨站的 POST 不帶它：CSRF 的第一道防線
# 不設 Max-Age：沿用第 26 章的規則，閒置 30 分鐘、絕對 12 小時由 server 端執行
line = cookie.output()
print(line.split("=", 2)[0] + "=<隨機 43 字元>;" + line.split(";", 1)[1])

# 手機 App：自己保管 access token，每個請求放在 Authorization header
access_token = "eyJhbGciOiJIUzI1NiIs…（省略）"
print("Authorization: Bearer " + access_token)

assert "HttpOnly" in line and "Secure" in line and "SameSite=Lax" in line and "Domain" not in line
```

```text
Set-Cookie: __Host-sid=<隨機 43 字元>; HttpOnly; Path=/; SameSite=Lax; Secure
Authorization: Bearer eyJhbGciOiJIUzI1NiIs…（省略）
```

第一行是 BFF 發給瀏覽器的 cookie，名稱與屬性沿用第 21、26 章的 session cookie `__Host-sid`，也同樣不設 Max-Age，期限由 server 端執行：`__Host-` 前綴要求瀏覽器只接受帶 Secure、Path 為 `/`、而且沒有 Domain 屬性的 cookie，避免子網域設定同名 cookie 來覆蓋它；HttpOnly 擋住 JavaScript；`SameSite=Lax` 讓跨站的 POST 不帶這個 cookie。cookie 的值只是隨機 session id，不是 JWT，所以就算被看到也無法拿去呼叫 API。第二行是手機 App 的寫法：`Bearer` 後面一個空白，接著 token 本身。

| 放法 | XSS 的影響 | CSRF 的影響 | 其他注意事項 |
|---|---|---|---|
| `localStorage`＋Authorization header | token 被偷走，可在別處使用 | 不受影響 | 內容留在磁碟；同 origin 的所有腳本都讀得到 |
| JS 記憶體＋Authorization header | 頁面存活期間仍可被讀取 | 不受影響 | 重新整理就消失，常需搭配 refresh 機制 |
| HttpOnly＋Secure＋SameSite cookie 直接放 JWT | 偷不走，但可被就地使用 | 需要 SameSite 與 CSRF 防禦 | 單一 cookie 約 4 KB 上限；JWT 太大會被截斷 |
| BFF：cookie 只放 session id | 偷不走 token，但可被就地使用 | 需要 SameSite 與 CSRF 防禦 | 多一層後端；最適合處理敏感資料的網站 |
| 手機 App：安全儲存＋Authorization header | 不適用（沒有網頁腳本） | 不適用 | 不要寫進 App 的 log 或分析事件 |

還有幾個和網路層有關的細節。第一，`Authorization` 不在 CORS 的 safelisted header 裡，所以 SPA 從 www 跨 origin 帶 Authorization 呼叫 API 時，瀏覽器會先送 preflight（第 23 章），多一個 RTT；BFF 模式下請求是同 origin，沒有這個成本。第二，bearer token 一律只在 HTTPS 上傳送，否則路徑上任何人都能撿到。第三，**不要把 token 放在 URL**：URL 會出現在瀏覽器歷史、`Referer` header、nginx 與 CDN 的 access log 裡（第 1 章）。WebSocket 的瀏覽器 API 不能自訂 header，常見的替代做法是先用 cookie 或一次性的短效 ticket 完成 handshake 驗證，第 32 章會詳談。

> [!note] 2026 現況
> 截至 2026 年 10 月（依 2026 年 10 月查證），IETF 的〈OAuth 2.0 for Browser-Based Applications〉已發布為 RFC 10017（BCP 212，2026-08），推薦 BFF 模式作為處理敏感資料的瀏覽器應用的首選架構。OAuth 2.1 仍是草案（draft-16，2026-09），尚未成為 RFC；cookie 的更新規格 RFC 6265bis 仍在 RFC Editor 佇列中，目前引用 RFC 6265（將由 6265bis 取代）。

## 27.10 動手做：只用標準函式庫簽發與驗證 JWT

這一節用三段程式把前面的設計落地。實驗一實作 base64url、HS256 的簽發與完整驗證（固定 alg、拒絕 none、typ、kid 對應金鑰輪替、exp／nbf／iat 含時鐘偏差、效期上限、iss、aud），並用十八個測試案例證明每一項檢查各自擋下哪一種錯誤 token。實驗二模擬 refresh token 輪替、重用偵測與停權。實驗三把驗證器放進一個真正的 HTTP server，觀察 401、403 與 `WWW-Authenticate` header。

> [!note] 自己實作只為了理解
> 這裡只用標準函式庫，是為了把每一步攤開來看。production 請用維護良好的函式庫（例如 PyJWT 或 Authlib 的 JOSE 實作），並依本節的清單設定參數；非對稱演算法更不要自己實作。

### 實驗一：一個驗證器與十八個錯誤 token

程式的 `verify()` 依 27.5 節的順序檢查，每一種失敗回傳一個機器可讀的原因代碼。`KEYRING` 模擬輪替中的 HS256 金鑰集合：`k2026-10` 是現行簽發金鑰，`k2026-09` 是只驗不簽的舊金鑰。測試時間固定為 `NOW`，所以輸出每次都一樣。

```python
import base64
import hashlib
import hmac
import json
import re

ISSUER = "https://auth.shengsheng.example"
ALLOWED_ALGS = {"HS256"}          # 固定允許清單：絕不讀 header 決定要用哪種演算法
LEEWAY = 60                       # 容許的時鐘偏差（秒）
MAX_LIFETIME = 15 * 60            # access token 最長效期；超過代表簽發端設定錯了
REQUIRED = ("iss", "sub", "aud", "exp", "iat")
B64URL = re.compile(r"^[A-Za-z0-9_-]*$")


class JWTError(Exception):
    pass


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    # 嚴格解碼：只收 base64url 字元、不收 padding，且必須是「唯一」的編碼方式
    if not B64URL.match(text) or len(text) % 4 == 1:
        raise JWTError("malformed")
    raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    if b64url_encode(raw) != text:
        raise JWTError("malformed")
    return raw


# kid → (secret, 狀態)。示範用固定值；真實系統用 secrets.token_bytes(32) 並放在 secrets manager
KEYRING = {
    "k2026-09": (hashlib.sha256(b"demo-k2026-09").digest(), "verify-only"),  # 舊金鑰：只驗不簽
    "k2026-10": (hashlib.sha256(b"demo-k2026-10").digest(), "active"),       # 現行簽發金鑰
}


def sign(claims: dict, kid: str = "k2026-10", header: dict | None = None) -> str:
    head = header or {"alg": "HS256", "typ": "at+jwt", "kid": kid}
    h = b64url_encode(json.dumps(head, separators=(",", ":")).encode())
    p = b64url_encode(json.dumps(claims, separators=(",", ":")).encode())
    secret = KEYRING[kid][0]
    sig = hmac.new(secret, f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url_encode(sig)}"


def verify(token: str, *, now: int, audience: str, keyring=KEYRING) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("malformed")
    h_b64, p_b64, s_b64 = parts
    try:
        header = json.loads(b64url_decode(h_b64))
    except ValueError:
        raise JWTError("malformed") from None
    if not isinstance(header, dict):
        raise JWTError("malformed")
    # 1. 演算法只看我們的允許清單；none、HS512、RS256 都在這裡被擋下
    if header.get("alg") not in ALLOWED_ALGS:
        raise JWTError("alg_not_allowed")
    # 2. 明確型別：OIDC 的 ID token（typ 不是 at+jwt）不能拿來當 access token
    if header.get("typ") != "at+jwt":
        raise JWTError("wrong_typ")
    # 3. kid 只當查表的 key，查不到就拒絕；不拿它組檔名、SQL 或 URL
    kid = header.get("kid")
    if not isinstance(kid, str) or kid not in keyring:
        raise JWTError("unknown_kid")
    # 4. 先驗簽章，簽章通過之前 payload 裡的任何東西都不可信
    expected = hmac.new(keyring[kid][0], f"{h_b64}.{p_b64}".encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64url_decode(s_b64)):
        raise JWTError("bad_signature")
    try:
        claims = json.loads(b64url_decode(p_b64))
    except ValueError:
        raise JWTError("malformed") from None
    if not isinstance(claims, dict) or any(k not in claims for k in REQUIRED):
        raise JWTError("missing_claim")
    for name in ("exp", "iat", "nbf"):
        value = claims.get(name, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise JWTError("malformed")
    # 5. 時間：都給同一個 LEEWAY，吸收簽發端與驗證端的時鐘差
    if now >= claims["exp"] + LEEWAY:
        raise JWTError("expired")
    if "nbf" in claims and now + LEEWAY < claims["nbf"]:
        raise JWTError("not_yet_valid")
    if claims["iat"] > now + LEEWAY:
        raise JWTError("issued_in_future")
    if claims["exp"] - claims["iat"] > MAX_LIFETIME:
        raise JWTError("lifetime_too_long")
    # 6. 誰發的、發給誰：兩個都要精確比對
    if claims["iss"] != ISSUER:
        raise JWTError("wrong_issuer")
    aud = claims["aud"] if isinstance(claims["aud"], list) else [claims["aud"]]
    if audience not in aud:
        raise JWTError("wrong_audience")
    return claims


NOW = 1_790_000_000
API = "api.shengsheng.example"
base = {"iss": ISSUER, "sub": "teacher:1024", "aud": API, "iat": NOW - 120,
        "exp": NOW + 180, "scope": "schedule:write"}


def with_claims(**changes):
    return sign({**base, **changes})


def tamper_payload(token):
    h, _, s = token.split(".")
    evil = b64url_encode(json.dumps({**base, "sub": "admin:1"}, separators=(",", ":")).encode())
    return f"{h}.{evil}.{s}"                     # 換掉 payload、沿用原簽章


def unsigned(alg):                               # 負面測試：header 宣稱不同演算法、沒有有效簽章
    h = b64url_encode(json.dumps({"alg": alg, "typ": "at+jwt", "kid": "k2026-10"}).encode())
    p = b64url_encode(json.dumps(base).encode())
    return f"{h}.{p}."


retired = dict(KEYRING)
del retired["k2026-09"]                          # 舊金鑰退役之後的 keyring

cases = [
    ("正常的 token", sign(base), API, KEYRING, "ok"),
    ("aud 是清單且包含 api", with_claims(aud=["rt.shengsheng.example", API]), API, KEYRING, "ok"),
    ("過期 40 秒（在偏差內）", with_claims(iat=NOW - 340, exp=NOW - 40), API, KEYRING, "ok"),
    ("舊 kid，輪替重疊期內", sign(base, kid="k2026-09"), API, KEYRING, "ok"),
    ("payload 被竄改", tamper_payload(sign(base)), API, KEYRING, "bad_signature"),
    ("alg 宣稱 none", unsigned("none"), API, KEYRING, "alg_not_allowed"),
    ("alg 宣稱 RS256", unsigned("RS256"), API, KEYRING, "alg_not_allowed"),
    ("typ 是 JWT（像 ID token）", sign(base, header={"alg": "HS256", "typ": "JWT", "kid": "k2026-10"}),
     API, KEYRING, "wrong_typ"),
    ("舊 kid，退役之後", sign(base, kid="k2026-09"), API, retired, "unknown_kid"),
    ("過期 61 秒", with_claims(iat=NOW - 361, exp=NOW - 61), API, KEYRING, "expired"),
    ("nbf 在 5 分鐘後", with_claims(nbf=NOW + 300), API, KEYRING, "not_yet_valid"),
    ("iat 在 10 分鐘後", with_claims(iat=NOW + 600, exp=NOW + 900), API, KEYRING, "issued_in_future"),
    ("效期 7 天", with_claims(exp=NOW + 7 * 86400), API, KEYRING, "lifetime_too_long"),
    ("iss 是 staging", with_claims(iss="https://auth.staging.shengsheng.example"), API, KEYRING, "wrong_issuer"),
    ("發給聊天服務的 token", with_claims(aud="rt.shengsheng.example"), API, KEYRING, "wrong_audience"),
    ("缺 exp", sign({k: v for k, v in base.items() if k != "exp"}), API, KEYRING, "missing_claim"),
    ("只有兩段", "abc.def", API, KEYRING, "malformed"),
    ("簽章帶 padding", sign(base) + "=", API, KEYRING, "malformed"),
]

for label, token, audience, keyring, want in cases:
    try:
        verify(token, now=NOW, audience=audience, keyring=keyring)
        got = "ok"
    except JWTError as exc:
        got = str(exc)
    result = "接受" if got == "ok" else f"拒絕 {got}"
    print(f"{label:<{26 - sum(1 for ch in label if ord(ch) > 127)}} → {result}")
    assert got == want, (label, got, want)
print(f"{len(cases)} 個案例全部符合預期")
```

```text
正常的 token               → 接受
aud 是清單且包含 api       → 接受
過期 40 秒（在偏差內）     → 接受
舊 kid，輪替重疊期內       → 接受
payload 被竄改             → 拒絕 bad_signature
alg 宣稱 none              → 拒絕 alg_not_allowed
alg 宣稱 RS256             → 拒絕 alg_not_allowed
typ 是 JWT（像 ID token）  → 拒絕 wrong_typ
舊 kid，退役之後           → 拒絕 unknown_kid
過期 61 秒                 → 拒絕 expired
nbf 在 5 分鐘後            → 拒絕 not_yet_valid
iat 在 10 分鐘後           → 拒絕 issued_in_future
效期 7 天                  → 拒絕 lifetime_too_long
iss 是 staging             → 拒絕 wrong_issuer
發給聊天服務的 token       → 拒絕 wrong_audience
缺 exp                     → 拒絕 missing_claim
只有兩段                   → 拒絕 malformed
簽章帶 padding             → 拒絕 malformed
18 個案例全部符合預期
```

前四個案例是**應該接受**的 token，這和拒絕案例一樣重要：驗證器太嚴，同樣會造成事故。「aud 是清單且包含 api」說明 aud 可以是陣列，只要包含自己就接受；「過期 40 秒（在偏差內）」說明 leeway 讓時鐘慢一點的 API 不會誤殺剛過期的 token；「舊 kid，輪替重疊期內」對應 27.7 節的 T2 到 T3 之間，舊金鑰仍在 keyring 裡。

接下來每一行都對應驗證清單的一格。「payload 被竄改」換掉 payload 但沿用原簽章，在 ⑤ 被擋下。「alg 宣稱 none」與「alg 宣稱 RS256」在 ② 就被拒絕，驗證器連金鑰都還沒拿出來；這兩個測試案例是用程式產生的負面測試，用來證明允許清單有效。「typ 是 JWT」模擬拿 ID token 來冒充，在 ③ 被擋。「舊 kid，退役之後」用的是一個簽章完全正確的 token，只是它的金鑰已經從 keyring 移除，所以在 ④ 失敗，這就是 27.7 節 T3 之後的行為。

時間類案例畫出了 leeway 的邊界：過期 40 秒接受、過期 61 秒拒絕；`nbf` 在 5 分鐘後、`iat` 在 10 分鐘後都超出 60 秒的容許範圍。「效期 7 天」就是故事裡的那種 token，它的簽章、iss、aud 全部正確，只因為 `exp − iat` 超過 15 分鐘的政策上限而被拒絕；把這條政策放在驗證端，簽發端的設定錯誤就不會無聲地擴散。「iss 是 staging」與「發給聊天服務的 token」在 ⑧ 與 ⑨ 被擋，它們的簽章同樣正確。最後三個是格式問題：缺少必要 claim、只有兩段、簽章段多了一個 `=`；嚴格的 base64url 解碼會拒絕 padding 與「解得開但不是唯一寫法」的字串，避免同一個 token 有多種寫法而繞過以字串比對為基礎的撤銷清單。

把每個案例的預期結果寫成 `assert`，這份清單就是驗證器的回歸測試。任何人日後修改 `verify()`，不小心拿掉 aud 檢查或放寬 alg，測試會立刻失敗。這是 Rita 對每一個驗證 middleware 的要求：不只要有正向測試，每一條拒絕規則都要有一個負面測試。

### 實驗二：refresh token 輪替、重用偵測與停權

這段程式模擬 27.8 節的兩個情境。auth server 用 `secrets.token_urlsafe(32)` 產生 opaque refresh token，資料庫只存 SHA-256 雜湊；每次使用就標記為已使用並發一個新的，同一個家族的舊 token 再次出現就撤銷整個家族。時間是模擬的秒數。

```python
import hashlib
import secrets

ACCESS_TTL = 300               # access token 5 分鐘
REFRESH_TTL = 14 * 86400       # refresh token 14 天（每次使用都換新的）


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()   # 資料庫只存雜湊，外洩也不能直接拿來用


class AuthServer:
    def __init__(self):
        self.refresh = {}          # 雜湊 → {family, sub, exp, used}
        self.families = {}         # family id → 是否已撤銷
        self.active_users = {"teacher:1024"}

    def _issue(self, sub, family, now):
        rt = secrets.token_urlsafe(32)                   # opaque：refresh token 只有 auth server 看得懂
        self.refresh[digest(rt)] = {"family": family, "sub": sub, "exp": now + REFRESH_TTL, "used": False}
        access = {"sub": sub, "exp": now + ACCESS_TTL}   # 代表一個短效 JWT（簽章部分見實驗一）
        return access, rt

    def login(self, sub, now):
        family = secrets.token_hex(4)
        self.families[family] = False
        return self._issue(sub, family, now)

    def use_refresh(self, rt, now):
        rec = self.refresh.get(digest(rt))
        if rec is None or now >= rec["exp"]:
            raise PermissionError("invalid_grant")
        if rec["used"]:                                  # 用過的又出現：有人拿著舊的副本
            self.families[rec["family"]] = True
            raise PermissionError("reuse_detected，整個家族撤銷")
        if self.families[rec["family"]]:
            raise PermissionError("family_revoked")
        if rec["sub"] not in self.active_users:
            raise PermissionError("user_suspended")
        rec["used"] = True
        return self._issue(rec["sub"], rec["family"], now)


def api_call(access, now):
    return "200" if now < access["exp"] else "401 token 過期"


auth = AuthServer()
log = []


def step(t, who, action):
    """執行一個動作並記錄結果；被拒絕時把原因印出來。"""
    try:
        result = action()
    except PermissionError as exc:
        result = f"拒絕：{exc}"
    log.append(result if isinstance(result, str) else "ok")
    pad = 6 - sum(ord(ch) > 127 for ch in who)        # 中文字佔兩格，對齊用
    print(f"t={t:>4}s  {who:<{pad}} {result if isinstance(result, str) else '換到新的 AT 與 RT'}")
    return result


# 情境一：refresh token 被偷。合法 App 先輪替，竊取者後用，舊 token 再出現就是警訊
at, rt1 = auth.login("teacher:1024", now=0)
stolen = rt1                                   # 假設 rt1 曾被寫進一份外流的 debug log
print("t=   0s  App    登入，拿到 AT 與 RT1")
at, rt2 = step(290, "App", lambda: auth.use_refresh(rt1, 290))
step(400, "竊取者", lambda: auth.use_refresh(stolen, 400))
step(590, "App", lambda: auth.use_refresh(rt2, 590))

# 情境二：停權。已簽出的 access token 撐到過期為止，refresh 則立刻被擋
at, rt = auth.login("teacher:1024", now=1000)
auth.active_users.discard("teacher:1024")
print("t=1100s  後台   停權 teacher:1024")
step(1200, "App", lambda: api_call(at, 1200))
step(1310, "App", lambda: api_call(at, 1310))
step(1310, "App", lambda: auth.use_refresh(rt, 1310))

assert log == ["ok", "拒絕：reuse_detected，整個家族撤銷", "拒絕：family_revoked",
               "200", "401 token 過期", "拒絕：user_suspended"]
```

```text
t=   0s  App    登入，拿到 AT 與 RT1
t= 290s  App    換到新的 AT 與 RT
t= 400s  竊取者 拒絕：reuse_detected，整個家族撤銷
t= 590s  App    拒絕：family_revoked
t=1100s  後台   停權 teacher:1024
t=1200s  App    200
t=1310s  App    401 token 過期
t=1310s  App    拒絕：user_suspended
```

前四行是重用偵測。t=290 App 正常輪替，拿到新的 AT 與 RT；t=400 竊取者拿出已經用過的 RT1，auth server 拒絕並撤銷整個家族；t=590 合法 App 手上的 RT2 也因為家族被撤銷而失效。竊取者偷到的 token 原本還有將近 14 天效期，現在只換來一次失敗與一筆資安告警。資料庫只存雜湊值的設計也值得注意：就算 refresh token 資料表外洩，拿到雜湊也無法反推出可用的 token，這和第 26 章「密碼只存雜湊」的道理相同；不過 refresh token 本身是 256 bit 的亂數，不需要 scrypt 這類刻意變慢的雜湊，一次 SHA-256 就足夠。

後四行是故事的修正版。t=1100 後台停權，t=1200 App 用還沒過期的 access token 呼叫 API 仍然成功，這是短效 token 刻意接受的殘留時間；t=1310 access token 過期（它在 t=1300 到期），App 嘗試 refresh，auth server 檢查帳號狀態後拒絕。停權從「最慢七天」變成「最慢五分鐘」。如果五分鐘仍然太長，就在 API 端為高風險操作加上 27.8 節表格裡的使用者狀態檢查。

### 實驗三：把驗證器放進 HTTP server

最後把精簡版的驗證放進 `http.server`，模擬課表 API 的 `PUT /v1/classes/7781/schedule`，觀察四種請求得到的狀態碼與 `WWW-Authenticate` header。

```python
import base64
import hashlib
import hmac
import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRET = hashlib.sha256(b"demo-k2026-10").digest()
AUDIENCE = "api.shengsheng.example"


def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(scope, exp_in=300):
    h = b64e(json.dumps({"alg": "HS256", "typ": "at+jwt", "kid": "k2026-10"}).encode())
    claims = {"sub": "teacher:1024", "aud": AUDIENCE, "exp": int(time.time()) + exp_in, "scope": scope}
    p = b64e(json.dumps(claims).encode())
    return f"{h}.{p}.{b64e(hmac.new(SECRET, f'{h}.{p}'.encode(), hashlib.sha256).digest())}"


def check(token):
    """精簡版驗證（完整清單見實驗一）。回傳 claims，失敗回傳 None。"""
    try:
        h, p, s = token.split(".")
        if json.loads(b64d(h)).get("alg") != "HS256":
            return None
        if not hmac.compare_digest(hmac.new(SECRET, f"{h}.{p}".encode(), hashlib.sha256).digest(), b64d(s)):
            return None
        claims = json.loads(b64d(p))
    except ValueError:
        return None
    if time.time() >= claims["exp"] or claims.get("aud") != AUDIENCE:
        return None
    return claims


class ScheduleAPI(BaseHTTPRequestHandler):
    def do_PUT(self):
        auth = self.headers.get("Authorization", "")
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return self.reply(401, 'Bearer realm="api"')            # 沒帶憑證：只告訴對方要用 Bearer
        claims = check(token)
        if claims is None:
            return self.reply(401, 'Bearer error="invalid_token"')  # 帶了但無效：重新取得 token
        if "schedule:write" not in claims["scope"].split():
            return self.reply(403, 'Bearer error="insufficient_scope", scope="schedule:write"')
        self.reply(200, None)

    def reply(self, status, challenge):
        self.send_response(status)
        if challenge:
            self.send_header("WWW-Authenticate", challenge)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), ScheduleAPI)
threading.Thread(target=server.serve_forever, daemon=True).start()
tokens = {
    "沒有 Authorization": None,
    "過期的 token": make_token("schedule:write", exp_in=-5),
    "scope 只有讀": make_token("schedule:read"),
    "正確的 token": make_token("schedule:read schedule:write"),
}
statuses = []
for label, token in tokens.items():
    conn = http.client.HTTPConnection(*server.server_address, timeout=2)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    conn.request("PUT", "/v1/classes/7781/schedule", headers=headers)
    resp = conn.getresponse()
    statuses.append(resp.status)
    print(f"{label:<{20 - sum(ord(c) > 127 for c in label)}} → {resp.status}  {resp.getheader('WWW-Authenticate') or ''}")
    conn.close()
server.shutdown()
server.server_close()
assert statuses == [401, 401, 403, 200]
```

```text
沒有 Authorization   → 401  Bearer realm="api"
過期的 token         → 401  Bearer error="invalid_token"
scope 只有讀         → 403  Bearer error="insufficient_scope", scope="schedule:write"
正確的 token         → 200  
```

第一行沒有帶任何憑證，回 401，`WWW-Authenticate` 只說明「請用 Bearer」，不附錯誤代碼，這是 RFC 6750 對「請求沒有帶驗證資訊」的建議。第二行 token 已過期，回 401 並帶 `error="invalid_token"`，告訴 client「這張 token 不能用了，去 refresh」，手機 App 的 HTTP 攔截器通常就是看到這個才觸發 refresh。第三行 token 有效但 scope 只有讀，回 **403** 與 `insufficient_scope`，並說明需要的 scope；這裡用 403 而不是 401，因為重新取得同樣的 token 沒有用，需要的是更多權限。第四行才成功。

這四種回應的差別對 client 很重要。401 代表「你的憑證有問題，換一張再來」，403 代表「你的憑證沒問題，但你不能做這件事」；把兩者混用，App 可能在權限不足時無限 refresh，或在 token 過期時直接把使用者登出。回應也加了 `Cache-Control: no-store`，避免任何快取保存與授權相關的回應（第 21 章）。

## 27.11 在工作上怎麼用

事故修正之後，Rita 和小晴把 token 相關的規則整理成團隊的檢查清單，依角色分工。

**後端工程師：驗證 token 的程式碼審查清單。** 每次看到驗證 JWT 的程式碼，逐條確認：演算法是寫死的允許清單，而不是從 header 讀出來；明確傳入 audience 與 issuer；leeway 有設定且不超過幾分鐘；必要 claims 有列出來；檢查了 typ；授權判斷（scope、角色、資源擁有者）在驗證之後另外做；錯誤回應不洩漏失敗原因，log 不記錄完整 token。新增一個服務時，先向 auth server 註冊它的 audience 識別字，再寫驗證程式。

**auth server 負責人：簽發端的設定。** 發給其他服務的 token 一律用非對稱簽章；access token 效期 5 到 15 分鐘；每個 token 都帶 `iss`、`sub`、`aud`、`exp`、`iat`、`jti` 與 `typ: at+jwt`；payload 不放個人資料，需要的資訊讓 API 用 `sub` 去查。金鑰輪替寫成自動化流程並定期演練，緊急輪替要有一份照著做就能完成的 runbook。refresh token 存雜湊、每次輪替、偵測重用，停權與改密碼時撤銷該帳號所有家族。

**前端工程師：token 不進 JavaScript。** 網站採用 BFF，瀏覽器只持有 `__Host-` 前綴的 HttpOnly session cookie；SPA 若無法避免自己持有 token，就只放在記憶體、效期短、並且嚴格執行 CSP。絕不把 token 放進 URL、`console.log` 或錯誤回報工具。

**SRE：觀察 token 的健康度。** 驗證失敗依原因代碼分類計數，任何一類突然升高都有意義：`expired` 暴增通常是某台機器時鐘漂移或 refresh 機制壞了；`unknown_kid` 暴增通常是輪替順序錯了；`wrong_audience` 出現代表有服務拿錯 token；`reuse_detected` 則直接是資安事件。下面是排查時常用的指令（示意）：

```bash
# 在本機安全地看 token 的 header 與 payload（不要貼到第三方網站解碼）
python3 -c 'import sys,base64,json; t=sys.argv[1].split("."); [print(json.dumps(json.loads(base64.urlsafe_b64decode(p+"="*(-len(p)%4))),indent=1)) for p in t[:2]]' "$TOKEN"

# 檢查各機器的時鐘偏移（Linux，chrony）
chronyc tracking | grep -E 'System time|Last offset'

# 看 auth server 目前公布的 kid 與快取設定
curl -s https://auth.shengsheng.example/.well-known/jwks.json | python3 -m json.tool | grep kid
curl -sI https://auth.shengsheng.example/.well-known/jwks.json | grep -i cache-control
```

第一行用 Python 在本機解開 token 的前兩段，這只是「讀」，不是驗證；它的用途是快速看 `exp`、`aud`、`kid` 對不對。千萬不要把 production 的 token 貼到網路上的解碼網站，那等於把一張還有效的通行證交給陌生人。第二行確認時鐘，偏移超過 leeway 的機器會讓 token 被誤判。最後兩行確認 JWKS 裡有哪些 kid、驗證端會快取多久，輪替出問題時第一個要看。

判斷「這個 401 到底是誰的錯」可以照這張流程走：

```text
 API 回 401／403
   │
   ├─ 403 insufficient_scope ──► token 本身沒問題：查 auth server 發的 scope 與 client 要求的 scope
   │
   └─ 401：看伺服器 log 的原因代碼
        ├─ expired、not_yet_valid、issued_in_future ──► 比對兩邊時鐘；refresh 有沒有被觸發
        ├─ unknown_kid ──► JWKS 是否已包含這個 kid？輪替順序？驗證端快取是否卡住？
        ├─ bad_signature ──► token 被截斷或改動？用錯環境的金鑰？
        ├─ wrong_audience、wrong_issuer ──► client 拿錯 token，或打錯環境（staging 對 production）
        └─ alg_not_allowed、wrong_typ ──► 有人送了不該出現的 token：拿 ID token 當 access token，或可疑流量
```

這張流程圖的價值在於原因代碼。如果驗證失敗只記一句「invalid token」，每次都要從頭猜；有了分類，大部分問題在看到代碼的那一刻就有了方向。

## 27.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 停權、改密碼後，帳號仍能呼叫 API 好幾個小時 | access token 效期太長，又沒有撤銷機制 | 解開 token 計算 `exp − iat`；確認 API 是否查使用者狀態 | access token 縮到 5–15 分鐘；refresh token 存伺服器並在停權時撤銷；高風險操作檢查使用者狀態 |
| 發給 A 服務的 token 能呼叫 B 服務 | 驗證時沒檢查 `aud`，或所有 token 都簽同一個 aud | 拿 aud 為 A 的 token 呼叫 B 的測試環境 | 每個服務有自己的 audience，驗證時精確比對；為此寫負面測試 |
| 部分機器間歇性回 401 `expired` 或 `not_yet_valid`，同一個 token 換台機器就過 | 機器時鐘漂移，偏移超過 leeway | 比較失敗機器與 auth server 的時間；`chronyc tracking` | 修 NTP；leeway 設 30–60 秒；監控時鐘偏移 |
| 金鑰輪替當天大量 401 `unknown_kid` | 先用新私鑰簽章，才發布公鑰；或驗證端 JWKS 快取太久不更新 | 比對 401 的 kid 與當下 JWKS 內容及快取時間 | 依「發布、等待快取、切換、等待效期、移除」的順序；遇未知 kid 限速重抓 |
| 輪替後舊 token 突然全部失效 | 太早從 JWKS 或 keyring 移除舊金鑰 | 失敗 token 的 `iat` 都早於切換時間 | 舊金鑰至少保留「最長效期＋leeway」 |
| 使用者的 cookie 偶爾消失、登入狀態不穩 | JWT 放 cookie，加上自訂 claims 後超過約 4 KB 的 cookie 上限 | DevTools 看 `Set-Cookie` 是否被瀏覽器拒絕；量 token 長度 | 精簡 claims；改用 BFF，cookie 只放 session id |
| App 在網路不穩時頻繁被登出 | refresh token 輪替遇到重送，被當成重用 | auth server log 的 `reuse_detected` 與 client 重試紀錄對照 | client 端序列化 refresh 請求；評估極短的重送寬限期 |
| 安全掃描在 log 或錯誤回報中找到 `eyJ` 開頭的字串 | 程式把 Authorization header 或含 token 的 URL 寫進 log | 搜尋 log 與 APM 的 `eyJ` 樣式 | log 遮罩 Authorization；token 不放 URL；撤銷已外洩的 token |
| 權限不足時 App 無限迴圈 refresh | API 對權限不足回 401 而不是 403 | 看回應碼與 `WWW-Authenticate` 的 error | token 無效回 401 `invalid_token`，權限不足回 403 `insufficient_scope` |

除錯 JWT 問題的通則是：**先分清楚是「token 錯」還是「驗證端錯」**。在本機解開 token 看 `iss`、`aud`、`exp`、`kid`，和驗證端的設定逐項比對，大部分問題不需要看任何程式碼就能找到；確定 token 內容正確之後，才去看金鑰、時鐘與快取。

## 27.13 動手練習

1. **加上 jti 撤銷清單**（延伸實驗一）。替 `verify()` 加一個 `revoked_jti` 集合參數，簽發時在 payload 放 `jti`（用 `secrets.token_hex(8)`），在驗證清單的哪一步檢查它？再加一個測試案例「jti 已撤銷」。
   答案要點：要在簽章驗證**之後**檢查，否則任何人都能在偽造的 token 裡放一個已撤銷的 jti 來探測清單內容，也沒有意義；撤銷清單的項目只需保存到該 token 的 `exp` 加 leeway 為止，之後它自然會因過期被拒絕，所以清單大小有上限。

2. **加上使用者層級的撤銷時間**（延伸實驗一與實驗二）。新增一個 `revoked_before = {"teacher:1024": 時間}`，`iat` 早於這個時間的 token 一律拒絕。用它重新模擬故事：停權之後的下一個請求就被拒絕。
   答案要點：這把「最慢一個效期」縮短成「下一個請求」，代價是每個請求要查一次使用者狀態。可以在 API 端快取這張表幾秒，讓查詢成本與生效延遲取得平衡；比較時同樣要考慮時鐘偏差。

3. **把 kid 綁定演算法**（延伸實驗一）。把 `KEYRING` 的每一筆改成 `(secret, 狀態, 允許的 alg)`，驗證時要求 header 的 alg 等於該 kid 綁定的 alg。思考這和全域的 `ALLOWED_ALGS` 有什麼不同。
   答案要點：全域清單只能保證「alg 是我們支援的其中一種」；綁定到 kid 才能保證「這把金鑰只會以一種方式被使用」，在同時支援多種演算法的過渡期，這是防止演算法混淆的最後一道防線，也是 JWK 的 `alg` 欄位的用途。

4. **用 DevTools 觀察真實的 token**（真實工具）。登入一個你自己的、使用 OAuth 或 OIDC 的測試帳號（例如公司內部的測試環境），在 DevTools 的 Network 面板找出帶 `Authorization: Bearer` 的請求，或在 Application 面板的 Cookies 與 Local Storage 裡找 `eyJ` 開頭的值，用 27.11 節的本機指令解開它。
   答案要點：記錄 `alg`、`typ`、`kid`、`aud`、`exp − iat`，判斷它屬於 27.9 節表格的哪一種放法，並評估 XSS 時的影響。只在自己有權限的帳號與環境做，不要把 token 貼到任何第三方網站。

5. **計算 JWKS 輪替的時間表**。聲聲 Live 的 API 快取 JWKS 1 小時，access token 效期 15 分鐘，leeway 60 秒。若要在 10 月 15 日 00:00 開始用新金鑰簽章，新公鑰最晚何時要發布？舊公鑰最早何時可以移除？
   答案要點：發布時間最晚是 10 月 14 日 23:00（提前至少一個快取時間，實務上再留緩衝，例如提前一天）；移除時間最早是 10 月 15 日 00:16（15 分鐘效期加 1 分鐘 leeway），但驗證端如果還有其他更長效的 token 種類，要以最長的為準。

## 本章重點整理

- Token 分成 opaque token（要回頭查發行者，撤銷即時）與 self-contained token（本地驗證，撤銷困難）；JWT 是後者最主流的格式，常和 opaque 的 refresh token 搭配使用。
- JWT 是三段以句點分隔的 base64url 文字：header、payload、signature；簽章涵蓋前兩段的編碼文字，所以 header 被改也會失效。
- base64url 把 `+`、`/` 換成 `-`、`_` 並省略 padding；JWT 預設只簽章、不加密，任何人不用金鑰都能讀出 payload，所以不能放敏感資料。
- HS256 是對稱簽章，能驗證的系統就能簽發；需要多個服務驗證時，改用 RS256 或 ES256，私鑰只放在 auth server，公鑰透過 JWKS 公開。
- 驗證的核心原則是：簽章通過之前，token 的內容只能用來挑選事先允許的選項，不能決定怎麼驗；alg 一律來自驗證端的允許清單，none 永遠不允許。
- 完整的驗證清單包括格式、alg、typ、kid、簽章、必要 claims、exp／nbf／iat 加上時鐘偏差、iss、aud，最後才是應用程式自己的授權判斷。
- 少了 aud 檢查，任何服務收到的 token 都能拿去呼叫其他服務；少了 iss 檢查，其他環境的 token 可能被接受；少了 typ，ID token 可能被當成 access token。
- kid、jku、jwk 等 header 欄位都是未經驗證的輸入：kid 只能當查表的 key，金鑰只能來自設定好的發行者。
- 金鑰輪替的順序是先發布新公鑰並等待快取更新、再切換簽章金鑰、最後等舊 token 全部過期才移除舊公鑰；驗證端遇到未知 kid 時要限速重抓 JWKS。
- 撤銷是用狀態換即時性：短效 access token、jti 撤銷清單、使用者層級的撤銷時間、introspection 各有成本，常見組合是 5–15 分鐘的 access token 加上存在伺服器端的 refresh token。
- refresh token 每次使用都輪替，已使用的 refresh token 再次出現就撤銷整個家族，讓被偷的 refresh token 只能換來一次失敗與一筆告警。
- 在瀏覽器裡，JavaScript 可讀的 token 怕 XSS，自動附加的 cookie 怕 CSRF；處理敏感資料的網站優先採用 BFF，瀏覽器只持有 HttpOnly、Secure、SameSite 的 session cookie。
- token 無效回 401 與 `invalid_token`，權限不足回 403 與 `insufficient_scope`；token 不放 URL、不寫進 log，錯誤訊息不透露是哪一項檢查失敗。

## 延伸問答

> [!question]- Q1. 面試題：JWT 和 session cookie 哪一個比較好？你會怎麼回答？
> 這題的陷阱是把兩個不同層次的東西放在一起比。session cookie 是「憑證放在哪裡、怎麼傳送」的選擇，背後通常是一筆存在伺服器上的 session 紀錄；JWT 是「憑證本身長什麼樣」的格式，把狀態寫進簽過章的 token 裡。兩者可以組合，例如把 JWT 放進 cookie，或像 BFF 一樣用 session cookie 對應伺服器端保管的 JWT。
>
> 真正的取捨是「狀態放哪裡」。伺服器端 session 撤銷即時、內容不外露、cookie 很小，但每個請求要查 session 儲存；JWT 讓驗證者不必回頭問發行者，適合多個服務共用同一個 auth server，代價是撤銷困難、payload 可被讀取、token 較大。所以好的回答是：單一網站用 HttpOnly session cookie 通常最簡單；多個 API 要各自驗證時用短效 JWT，並搭配伺服器端的 refresh token 處理撤銷。

> [!question]- Q2. 你在 code review 看到 `jwt.decode(token, key, algorithms=jwt.get_unverified_header(token)["alg"])`。這行有什麼問題？
> 這行把「允許哪些演算法」交給 token 自己決定，等於沒有允許清單。`get_unverified_header` 讀出的是未經驗證的資料，任何人都能把 header 的 alg 改成任何值。如果 `key` 是一把 RSA 公鑰的文字，攻擊者宣稱 HS256 就可能構成演算法混淆；如果函式庫或某個版本接受 none，就可能完全跳過簽章。即使目前的函式庫版本恰好會拒絕這些情況，安全性也建立在函式庫的補救上，而不是程式本身的設計。
>
> 正確的寫法是把演算法寫在設定裡，例如 `algorithms=["ES256"]`，並且同時傳入 audience、issuer、leeway 與必要 claims。若系統在輪替期間需要支援兩種演算法，就用 kid 查到金鑰後，以該金鑰綁定的演算法作為唯一允許值。這也提醒我們，code review 時看到任何「先讀 header 再決定怎麼驗」的寫法，都要停下來問：這個值是誰控制的？

> [!question]- Q3. 手算：一個 JWT 的 payload 是 150 bytes 的 JSON，header 是 40 bytes，用 ES256 簽章。整個 token 有幾個字元？若改用 RS256（2048 bit）呢？
> base64url 每 3 個 byte 產生 4 個字元，不足 3 byte 的尾巴不補 padding：n bytes 會產生 ceil(4n/3) 個字元。header 40 bytes → 54 個字元（40×4/3＝53.33，進位成 54）；payload 150 bytes → 200 個字元；ES256 簽章 64 bytes → 86 個字元。加上兩個句點，總共 54＋200＋86＋2＝342 個字元。
>
> 改用 RS256 時，2048 bit 的 RSA 簽章長 256 bytes，編碼後是 342 個字元（256×4/3＝341.33，進位成 342），整個 token 變成 54＋200＋342＋2＝598 個字元，比 ES256 多了約 75%。這對每個請求都要帶 token 的 API 是實際的頻寬與 header 大小成本，也是許多新系統偏好 ES256 的原因之一。若 token 還要放進 cookie，更要留意約 4 KB 的上限。

> [!question]- Q4. 你在 production 看到某一台 API 主機的 401 `not_yet_valid` 比例特別高，其他主機正常。可能是什麼？怎麼確認？
> `not_yet_valid` 代表驗證端認為「現在」還早於 token 的 `nbf`（或依實作，iat 在未來）。同一批 token 在其他主機都正常，問題幾乎可以確定在這台主機本身，而最常見的原因是時鐘落後：auth server 在 10:00:00 簽出 `nbf=10:00:00` 的 token，這台主機的時鐘若是 09:58:30，落後 90 秒，超過 60 秒的 leeway，就會拒絕剛簽出的 token。
>
> 確認方法是在這台主機上看 NTP 狀態（例如 `chronyc tracking` 的 offset），並與 auth server 或可信的時間來源比較；也可以從 log 取出被拒 token 的 nbf，與主機當下時間相減，差值應該剛好超過 leeway。修正是恢復 NTP 同步並找出時鐘漂移的原因（例如 VM 暫停後恢復、NTP 被防火牆擋住 UDP 123），而不是把 leeway 調大，因為 leeway 放大會讓所有主機都接受過期更久的 token。另外要把時鐘偏移納入監控。

> [!question]- Q5. 設計取捨：聲聲 Live 的 auth server 每秒要處理 3,000 個 refresh 請求，有人提議把 access token 從 5 分鐘改成 24 小時。你會怎麼評估？
> 先算清楚這個提議換來什麼。access token 效期從 5 分鐘變成 24 小時，refresh 請求量大約降為原本的 1/288，auth server 的負擔確實大幅降低。但代價是所有「需要讓 token 失效」的事件都延遲到最長 24 小時：停權、改密碼、權限調降、token 外洩後的止血，都要等 token 自然過期，除非另外建置撤銷清單，而那又讓每個 API 請求回到「要查狀態」的模式，抵消了 JWT 的好處。
>
> 比較好的方向是讓 refresh 變便宜，而不是讓 access token 變長：refresh token 資料表依雜湊值建索引、帳號狀態快取幾秒、auth server 水平擴展，每秒 3,000 次查詢對一個設計良好的服務並不算高。也可以依風險分級，例如唯讀的公開課程資訊用較長的 token，修改課表與付款的 scope 用較短的 token，或對高風險操作額外檢查使用者狀態。關鍵是把「最慢多久生效」當作明確的需求寫下來，再選擇成本最低的實作。

> [!question]- Q6. 看 log 找原因：金鑰輪替當天 00:00 到 00:10，API 的 401 `unknown_kid` 從 0 衝到 30%，之後慢慢下降到 0。發生了什麼？
> `unknown_kid` 代表 token 的 kid 不在驗證端目前的金鑰集合裡。比例在切換簽章金鑰的時間點暴增、十分鐘後恢復，最符合的解釋是輪替順序錯了：auth server 在 00:00 同時發布新公鑰並開始用新私鑰簽章，而 API 的 JWKS 快取時間是 10 分鐘。在快取到期前，各 API 手上的 JWKS 還沒有新 kid，所以新簽出的 token 都被拒絕；比例「慢慢」下降，是因為各台 API 的快取在不同時間到期。
>
> 修正有兩層。流程上，新公鑰要至少提前一個快取時間（實務上留更多緩衝）發布，等所有驗證端都抓到之後才切換簽章金鑰。實作上，驗證端遇到未知 kid 時應該限速地提早重抓一次 JWKS，這樣即使流程出錯，影響也只有幾秒。確認方法是對照 auth server 的發布時間、JWKS 回應的 `Cache-Control` 與各 API 主機的快取更新時間。

> [!question]- Q7. 概念辨析：既然 refresh token 也可能被偷，為什麼「輪替」能提高安全性？它擋不住哪些情況？
> 不輪替的 refresh token 被偷之後，竊取者和合法使用者可以各自無限期地用它換 access token，auth server 看不出任何異常，直到 refresh token 過期為止。輪替讓每個 refresh token 只能用一次，於是只要合法 App 和竊取者都還在使用，遲早會有一方拿出「已經用過的」token；auth server 看到重用就撤銷整個家族，把一次無聲的外洩轉變成一個可偵測的事件，並且終止雙方的存取。
>
> 它擋不住的情況也要清楚。第一，如果竊取者偷到 token 後搶先使用，而合法 App 之後再也沒有上線，重用永遠不會發生，竊取者可以一直輪替下去，只能靠 refresh token 的絕對效期、異常偵測（裝置、地點）或使用者主動登出所有裝置。第二，如果攻擊者能持續控制裝置（例如惡意軟體），可以直接偷每一個新的 token。這也是 sender-constrained token（DPoP、mTLS）存在的原因：把 token 綁定到 client 的私鑰，光偷到 token 本身不夠用。

> [!question]- Q8. 情境判斷：前端同事說「我們把 JWT 放進 HttpOnly cookie，所以 XSS 已經不是問題了」。你同意嗎？
> 只同意一半。HttpOnly 確實讓 JavaScript 讀不到 cookie，XSS 無法把 token 送到攻擊者自己的機器上長期使用，這相對於 `localStorage` 是實質的改善，因為外洩的傷害被限制在「受害者開著頁面的時候」。但 XSS 的腳本是在你的 origin 裡執行，它可以直接呼叫你的 API，瀏覽器會自動附上那個 HttpOnly cookie；也就是說，攻擊者雖然拿不走鑰匙，卻能在現場用它開門。
>
> 此外，把憑證放進自動附加的 cookie，就要處理 CSRF：需要 SameSite、CSRF token 或 Origin 檢查（第 23 章）。所以正確的說法是「HttpOnly cookie 降低了 token 外洩的影響，但 XSS 仍然是嚴重漏洞」，根本防線依然是輸出跳脫、CSP 與避免危險的 DOM API。另外，JWT 放 cookie 還要注意大小上限；若 token 的 claims 越來越多，改用 BFF 讓 cookie 只放 session id 會更穩定。

## 延伸閱讀

- RFC 7519〈JSON Web Token (JWT)〉：JWT 的格式與註冊 claims
- RFC 7515〈JSON Web Signature (JWS)〉與 RFC 7518〈JSON Web Algorithms (JWA)〉：簽章格式、compact serialization 與演算法定義
- RFC 7517〈JSON Web Key (JWK)〉：JWK 與 JWK Set 的格式
- RFC 8725〈JSON Web Token Best Current Practices〉：JWT 安全實務；更新版 draft-ietf-oauth-rfc8725bis 截至 2026 年 10 月尚未取得 RFC 編號
- RFC 9068〈JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens〉：access token 的 claims 與 `at+jwt` 型別
- RFC 6750〈The OAuth 2.0 Authorization Framework: Bearer Token Usage〉：Authorization header、401／403 與 `WWW-Authenticate` 錯誤代碼
- RFC 9700〈Best Current Practice for OAuth 2.0 Security〉：refresh token 輪替與 sender-constrained token 的要求
- OWASP〈JSON Web Token Cheat Sheet〉與〈Session Management Cheat Sheet〉：實作檢查清單
