---
chapter: 28
title: OAuth 2.0 與 2.1
part: 6
---

# 第 28 章　OAuth 2.0 與 2.1

> [!abstract] 本章地圖
> **核心問題**：怎麼讓第三方 App 代替使用者存取 API，卻永遠拿不到使用者的密碼，而且拿到的權限剛好夠用、隨時能收回？
>
> **你會學到**：
> - 說清楚 OAuth 解決的「委派授權」問題，分辨 resource owner、client、authorization server、resource server 四個角色，以及 front channel 與 back channel
> - 畫出 authorization code＋PKCE 的完整時序圖，解釋 state、redirect URI 精確比對、code 一次性與 `code_verifier` 各自擋住哪一種攻擊
> - 依情境選擇 grant：使用者在場用 authorization code，service 之間用 client credentials，並設計 refresh token 輪替與重複使用偵測
> - 設計 scope 與同意畫面，分辨 public client 與 confidential client，知道 SPA 與手機 App 該怎麼接
> - 列出 OAuth 2.1 相對 2.0 的變化，理解 DPoP 怎麼讓偷到的 token 無法使用
> - 用 Python 在 127.0.0.1 上架起三個角色，跑完一次 authorization code＋PKCE，並逐一重現每道檢查擋下的錯誤
>
> **前置知識**：第 21 章（redirect 與 cookie）、第 23 章（same-origin、CSRF、XSS）、第 26 章（authentication 與 session）、第 27 章（token 與 JWT）

## 28.1 故事：合作夥伴想要學生的密碼

2026 年 9 月，聲聲 Live 和一個單字卡 App「詞卡島」談成合作：學生上完日文課後，老師美咲在課堂筆記裡標記的生字，可以一鍵匯入詞卡島複習，複習成績再回寫到聲聲 Live 的學習紀錄。詞卡島的 PM 寄來的整合提案只有一段話：「請學生在詞卡島 App 輸入聲聲 Live 的帳號密碼，我們的 server 每天用這組帳密登入一次，抓生字表、寫回成績。」

資安工程師 Rita 在提案上直接畫了一個大叉，寫下三個問題：第一，學生的密碼會躺在別家公司的資料庫裡，對方一旦外洩，攻擊者拿到的是學生的完整帳號，連付款與上課紀錄都能動；第二，詞卡島只需要「讀生字、寫成績」，帳密卻等於全部權限；第三，學生想取消授權只能改密碼，而改密碼會讓所有裝置一起登出。更麻煩的是，聲聲 Live 的登入已經有 TOTP 和 passkeys（第 26、29 章），一組帳密根本無法替學生完成這些驗證。

團隊決定在 `auth.shengsheng.example` 開放 OAuth。小晴被指派寫第一版的設定與串接規格，交出的草稿是這樣：詞卡島登記的 redirect URI「允許以 `cards.example.net` 開頭的任何網址」；詞卡島是 server 端程式、有 client secret，所以「不需要 PKCE」；`state` 參數「選填」；access token 有效 30 天，省得處理 refresh token；scope 只有一個 `all`。Rita 在每一條旁邊都標了紅字。

```text
 ┌──────────────────────────┐ ── ① 點「從聲聲 Live 匯入」──► ┌──────────────────────────┐
 │ 學生的瀏覽器               │                                │ 詞卡島 web 後端            │
 │ （家用網路 198.51.100.23） │ ── ③ 帶著 code 回到詞卡島 ───► │ cards.example.net          │
 └─────────────┬────────────┘                                │ 198.51.100.120             │
               │ ② 在聲聲 Live 自己的頁面                     └──────┬──────────────┬──────┘
               │   登入＋同意（密碼只輸入在這裡）                     │              │
               ▼                                                    │ ④ 用 code    │ ⑤ Authorization:
 ┌──────────────────────────┐                                       │   換 token   │   Bearer <token>
 │ auth.shengsheng.example   │ ◄═════（server 對 server）════════════┘              ▼
 │ （authorization server）   │                            ┌───────────────────────────────┐
 └──────────────────────────┘                            │ api.shengsheng.example          │
                                                          │ （resource server，203.0.113.80）│
                                                          └───────────────────────────────┘
 小晴草稿的五個紅字：✗ redirect URI 用「開頭符合」   ✗ 有 secret 就不用 PKCE   ✗ state 選填
                     ✗ access token 30 天、沒有 refresh token   ✗ 只有一個 scope：all
```

這張圖是 Rita 在審查會議上畫的。學生的密碼只在 ② 輸入給聲聲 Live 自己的登入頁，詞卡島從頭到尾看不到；詞卡島在 ④ 拿到的是一張只能讀生字、寫成績的 access token，⑤ 再用它呼叫 API。最下面的五個紅字，每一個都對應一種真實發生過的攻擊：偷走 code、偷走 token、把攻擊者的帳號塞給受害者、權限過大、無法收回。

不懂 OAuth 的細節，你會覺得這些參數是儀式，能省就省；懂了以後，你會發現每個參數都在回答一個具體的問題：「這個 code 真的是發給你的嗎？」「回來的瀏覽器真的是剛才出發的那個嗎？」「拿著 token 的人真的是 token 的主人嗎？」本章依序回答它們，章末的動手做會在你的電腦上架起三個角色，把小晴的草稿修好，並讓每一道檢查實際擋下一次攻擊。

## 28.2 OAuth 解決什麼問題：委派授權

第 26 章區分過 **authentication**（驗證你是誰）與 **authorization**（決定你能做什麼）。OAuth 處理的是第二件事的一個特殊版本：**委派授權**（delegated authorization），也就是「資源的主人同意讓另一個程式，以有限的權限、在有限的時間內，代替自己存取資源」。日常生活的類比是飯店的房卡：你在櫃檯證明身分（authentication），櫃檯發給清潔人員一張只能開你房門、只到今天下午三點有效的卡，而不是把你的身分證和保險箱密碼交給對方。

在 OAuth 出現之前，第三方整合常見的做法就是詞卡島提案裡的「給我你的密碼」，業界稱為 **password anti-pattern**。它的問題不只是外洩風險，而是密碼這個憑證本身無法表達「部分權限」與「單獨撤銷」。OAuth 的核心想法是**多加一層間接**：使用者在資源擁有者自己的網站上驗證身分並同意授權，網站發給第三方一張代表「這次同意」的 **access token**（存取權杖，例如一串 43 個字元的亂數）。API 只認 token，不認密碼。

| 比較項目 | 交出密碼 | OAuth access token |
|---|---|---|
| 第三方拿到什麼 | 使用者的完整憑證 | 一張只代表這次同意的 token |
| 權限範圍 | 與使用者本人相同 | 由 scope 限制，例如只有 `vocab:read` |
| 有效時間 | 直到使用者改密碼 | 數分鐘到數小時，可用 refresh token 延續 |
| 撤銷 | 改密碼，所有裝置一起登出 | 只撤銷這個 App 的授權 |
| MFA、passkeys | 第三方無法完成 | 由 authorization server 處理，第三方不必知道 |
| 稽核 | 看不出是本人還是第三方 | 每個請求都知道是哪個 client 代表誰 |

最容易被忽略的是 MFA 那一列：OAuth 讓「怎麼驗證使用者」完全留在聲聲 Live 手上，今天用密碼加 TOTP、明天改用 passkeys，詞卡島的程式一行都不用改。

> [!warning] 常見誤解
> **OAuth 不是登入協定。** access token 是「給 API 看的通行證」，不是「給 client 看的身分證明」。如果 client 想知道「現在是誰在用我的 App」，需要的是 OpenID Connect 在 OAuth 之上加的 ID token（第 29 章）。拿「能不能用 access token 呼叫某個 API」來判斷使用者身分，曾經造成「用別的 App 拿到的 token 登入你的 App」這類漏洞。

## 28.3 四個角色與兩條通道

OAuth 2.0（RFC 6749）把參與者分成四個角色。用聲聲 Live 的例子對照，比背定義容易得多：

| 角色 | 定義 | 聲聲 Live 的例子 | 手上有什麼 |
|---|---|---|---|
| **resource owner** | 能同意授權的人，通常是使用者 | 學生（登入帳號 `student23`，內部 ID `stu_1024`） | 自己的帳號、密碼、passkey |
| **client** | 想代替使用者存取資源的程式 | 詞卡島的 web 後端、聲聲 Live 自家的手機 App | `client_id`，有些還有 client secret |
| **authorization server**（AS） | 驗證使用者、取得同意、發 token | `auth.shengsheng.example` | 使用者資料庫、client 登記資料、簽章金鑰 |
| **resource server**（RS） | 保管資源、檢查 token 的 API | `api.shengsheng.example` 的生字表與學習紀錄 API | 資源本身、驗證 token 的方法 |

注意「client」在 OAuth 裡的意思和一般說的「瀏覽器是 client」不同：它指的是**想拿 token 的那個應用程式**，可以是一個 web 後端、一個手機 App，甚至是一個沒有使用者介面的排程服務。另外，AS 與 RS 在小型系統裡常常是同一個服務，但概念上分開有好處：RS 只需要會驗 token，不必知道使用者怎麼登入的。

四個角色之間的訊息走兩種不同的路徑，這是理解所有 OAuth 安全設計的鑰匙。**front channel**（前端通道）指的是透過瀏覽器的 redirect 傳遞的訊息：client 回應一個 302，讓瀏覽器帶著參數跳到 AS；AS 再回一個 302，讓瀏覽器帶著結果跳回 client。**back channel**（後端通道）則是 client 直接對 AS 發出的 HTTPS 請求，不經過瀏覽器。

```text
            front channel：經過瀏覽器，參數在 URL 上，看得到也改得了
   ┌────────────── 302 Location: AS/authorize?... ──────────────┐
   │                                                             ▼
 ┌─┴──────┐                  ┌──────────┐                 ┌───────────┐
 │ client │                  │ 瀏覽器    │                 │    AS     │
 └─┬──────┘                  └──────────┘                 └─────┬─────┘
   ▲                                                             │
   └────────────── 302 Location: client/callback?code=... ───────┘

   ┌─────────┐   back channel：TLS 直連，可做 client 驗證，瀏覽器看不到   ┌─────┐
   │ client  │ ════════════ POST /token（code、verifier、secret）══════► │ AS  │
   └─────────┘ ◄═════════════ 200 {"access_token": ...} ════════════════ └─────┘
```

上半部是 front channel。它的好處是能把使用者帶到 AS 的登入頁，讓使用者在「正牌的網址列」下輸入密碼；壞處是所有參數都出現在 URL 上，會進入瀏覽器歷史、可能進入 log（第 1 章提醒過 query 會被記錄），而且使用者或攻擊者都能任意修改，還可能被手機上的其他 App 攔截。下半部是 back channel：client 和 AS 之間是一條 TLS 連線，AS 能驗證 client 的身分，回應也只有 client 收得到。

OAuth 的設計原則因此是：**front channel 只傳「沒有用、或用完就作廢」的東西，值錢的 token 走 back channel**。authorization code 就是這個原則的產物：它本身不能呼叫 API，必須在 back channel 搭配只有 client 知道的東西才能換成 token。本章後面的防禦，都是在補強 front channel 的弱點。

## 28.4 Client 的身分：註冊、public 與 confidential

AS 在發 token 之前，要知道「是哪個 client 在要」。所以每個 client 都要先**註冊**（registration）：在 AS 登記名稱、允許的 redirect URI、允許的 scope 與 client 類型，AS 發給它一個 **`client_id`**（公開的識別碼，例如 `cards`）。`client_id` 會出現在 front channel 的 URL 上，所以它不是秘密，只是名字。

真正的分水嶺是 client 能不能保守秘密。**confidential client**（機密 client）跑在自己控制的伺服器上，能安全保存 client secret 或私鑰，例如詞卡島的 web 後端、聲聲 Live 的推薦服務 `reco`。**public client**（公開 client）的程式碼跑在使用者的裝置上，任何秘密都能被拆出來，例如手機 App（安裝包可以被反組譯）、純前端的 SPA（JavaScript 原始碼人人看得到）、桌面程式。對 public client 來說，「把 secret 寫死在程式裡」等於公開它。

| 項目 | confidential client | public client |
|---|---|---|
| 例子 | 詞卡島 web 後端、`reco` 服務 | 聲聲 Live 手機 App、純前端 SPA、桌面程式 |
| token endpoint 的 client 驗證 | 有：secret、私鑰簽章或 mTLS | 無，只送 `client_id` |
| PKCE | RFC 9700 建議、OAuth 2.1 原則上要求 | 必須，而且是唯一能證明「換 code 的是同一個 client」的機制 |
| refresh token | 可以發，搭配 client 驗證 | 要輪替或綁定金鑰（28.10、28.14 節） |
| 可用的 grant | authorization code、client credentials | 只有 authorization code |

confidential client 在 token endpoint 證明身分的方式有好幾種：最常見的 `client_secret_basic` 用 HTTP Basic 帶 `client_id:secret`；`private_key_jwt` 讓 client 用私鑰簽一個短效 JWT（第 27 章），AS 只保存公鑰，資料庫外洩也不會洩漏 client 的憑證；`tls_client_auth` 用 mTLS 的 client 憑證（第 30 章）。聲聲 Live 對外部合作夥伴先用 `client_secret_basic`，secret 在 AS 端只存 hash；內部服務改走 `private_key_jwt` 或 workload identity。

## 28.5 Authorization code 流程：一步一步

**grant**（授權許可）是「client 用什麼方式拿到 token」的流程類型。最重要、也是使用者在場時唯一推薦的 grant 是 **authorization code**：AS 先在 front channel 發一個短效、一次性的**授權碼**（authorization code），client 再到 back channel 用它換 token。下圖是詞卡島匯入生字的完整流程，已經包含 28.6 到 28.8 節要講的 state、redirect URI 比對與 PKCE：

```text
 學生瀏覽器                  詞卡島（client）                 auth（AS）                  api（RS）
    │ ① GET /import             │                               │                            │
    │──────────────────────────►│ 產生 state、code_verifier       │                            │
    │                           │ 存進 server 端 session          │                            │
    │◄── ② 302 Location: auth/authorize?response_type=code       │                            │
    │        &client_id=cards&redirect_uri=…/oauth/callback       │                            │
    │        &scope=vocab:read vocab:write&state=xyz              │                            │
    │        &code_challenge=E9Mel…&code_challenge_method=S256    │                            │
    │        Set-Cookie: sid=…（HttpOnly; SameSite=Lax）           │                            │
    │──── ③ GET /authorize?… ───────────────────────────────────►│ 檢查 client_id、            │
    │                                                            │ redirect_uri 精確比對、      │
    │◄─── ④ 登入頁（密碼＋TOTP 或 passkey）、同意畫面 ─────────────│ scope、PKCE 參數            │
    │──── ⑤ 學生按「允許」 ──────────────────────────────────────►│ 產生 code，記下 challenge、 │
    │                                                            │ redirect_uri、scope、學生    │
    │◄─── ⑥ 302 Location: cards…/oauth/callback?code=SplxlO…&state=xyz&iss=…                  │
    │──── ⑦ GET /oauth/callback?code=…&state=xyz ──►│ 比對 state 與 session             │
    │                           │═══ ⑧ POST /token ═════════════►│ 驗 client、code 一次性、     │
    │                           │  grant_type=authorization_code │ 未過期、redirect_uri 相同、  │
    │                           │  code、redirect_uri、          │ SHA256(verifier)==challenge │
    │                           │  code_verifier、client 驗證     │                            │
    │                           │◄══ ⑨ 200 access_token、refresh_token、expires_in、scope ═══│
    │                           │══════ ⑩ GET /vocab  Authorization: Bearer … ══════════════►│
    │                           │◄═════ ⑪ 200 生字表（RS 檢查 token 有效、aud、scope）══════════│
    │◄── ⑫ 匯入完成 ─────────────│                               │                            │
```

逐步看。① 學生在詞卡島按下匯入，詞卡島的後端產生兩個隨機值：`state`（28.6 節）與 `code_verifier`（28.8 節），存在自己的 server 端 session 裡，瀏覽器只拿到一個 session cookie。② 詞卡島回 302，把瀏覽器送到 AS 的 **authorization endpoint**；這個 URL 上的參數就是「授權請求」。③ AS 收到後先做靜態檢查：`client_id` 存在嗎？`redirect_uri` 和登記的值逐字相同嗎？要求的 scope 在這個 client 的允許範圍內嗎？有沒有帶 PKCE 參數？任何一項不過，就不往下走。

④⑤ 學生在 AS 自己的頁面登入、看到同意畫面並按下允許；這一段完全在聲聲 Live 的網域裡，詞卡島看不到。⑥ AS 產生授權碼，在資料庫記下「這個 code 屬於哪個 client、哪個學生、哪些 scope、哪個 redirect_uri、哪個 code_challenge、幾點過期」，然後把瀏覽器送回 redirect URI，附上 `code`、原封不動的 `state`，以及 AS 自己的識別 `iss`。⑦ 詞卡島先比對 `state`，確認這個回呼屬於剛才那個 session。

⑧ 詞卡島在 back channel 呼叫 **token endpoint**，帶著 code、同一個 redirect_uri、原始的 `code_verifier`，以及自己的 client 驗證。AS 依序檢查：client 是不是 code 的主人、code 是否用過、是否過期、redirect_uri 是否相同、`code_verifier` 的雜湊是否等於當初的 `code_challenge`。⑨ 全部通過才回 token。⑩⑪ 詞卡島拿 access token 呼叫 API，RS 檢查 token 是否有效、是否是發給自己的（audience）、scope 夠不夠。整個流程中，token 從未出現在瀏覽器裡。

授權請求的參數不多，但每一個都有明確的任務：

| 參數 | 例子 | 用途 | 漏了會怎樣 |
|---|---|---|---|
| `response_type` | `code` | 指定 authorization code 流程 | AS 回 `unsupported_response_type` |
| `client_id` | `cards` | 告訴 AS 是哪個 client | AS 無法查登記資料，不能導回 |
| `redirect_uri` | 詞卡島的 `/oauth/callback` | 結果要送回哪裡，必須和登記值逐字相同 | 只有一個登記值時可省略，但建議永遠帶上 |
| `scope` | `vocab:read vocab:write` | 要求的權限，以空白分隔 | 由 AS 決定預設值，常常比需要的多 |
| `state` | 22 個字元的亂數 | 把回呼綁回發起的 session（28.6 節） | 回呼可能被偽造 |
| `code_challenge` | `E9Melhoa…` | PKCE：verifier 的 SHA-256（28.8 節） | 攔到 code 的人可以兌換 |
| `code_challenge_method` | `S256` | 雜湊方法，只該用 S256 | 預設是 `plain`，等於沒保護 |

AS 對授權碼本身也有要求。RFC 6749 規定授權碼必須短效（建議最長 10 分鐘，實務上常設 30 到 60 秒）、只能使用一次；如果同一個 code 被兌換第二次，AS 必須拒絕，並且應該撤銷先前用這個 code 換出的所有 token，因為「被兌換兩次」代表 code 已經外洩，而且不知道先換到 token 的是正主還是攻擊者。token endpoint 的回應必須帶 `Cache-Control: no-store`，避免 token 被任何快取保存（第 21 章）。

```text
 token endpoint 的成功回應（RFC 6749 §5.1 的格式，內容為示意）

 HTTP/1.1 200 OK
 Content-Type: application/json
 Cache-Control: no-store
 ┌──────────────────────────────────────────────────────────────────────┐
 │ {                                                                    │
 │   "access_token":  "Kz~8mXK1EalYznwH-LC-1fBAo.4Ljp~zsPE_NeO.gxU",    │ ← 呼叫 API 用
 │   "token_type":    "Bearer",                                         │ ← 怎麼出示（28.14 節的 DPoP 不同）
 │   "expires_in":    600,                                              │ ← 秒；client 自己記下到期時間
 │   "refresh_token": "8xLOxBtZp8",                                     │ ← 只給 token endpoint 看
 │   "scope":         "vocab:read"                                      │ ← 實際核准的，可能比要求的少
 │ }                                                                    │
 └──────────────────────────────────────────────────────────────────────┘
```

這張圖要注意兩件事。第一，回應裡的 `scope` 是**實際核准**的範圍，可能比 client 要求的少（學生在同意畫面取消勾選了寫入權限），client 必須讀它，而不是假設自己拿到了全部。第二，`refresh_token` 和 `access_token` 的對象不同：access token 送給 RS，refresh token 只送回 AS 的 token endpoint，兩者永遠不該混用。

## 28.6 state：確認回來的是自己發出去的請求

⑦ 那一步的 redirect URI 是一個公開的網址，任何人都能讓受害者的瀏覽器打開它，帶上任意的 `code`。這就是 OAuth 版本的 CSRF（第 23 章）：攻擊者先用**自己的**聲聲 Live 帳號走完前半段流程，拿到一個合法的 code，但不兌換；接著誘使受害者打開「詞卡島 callback＋攻擊者的 code」這個網址。如果詞卡島不檢查，就會用攻擊者的 code 換到**攻擊者帳號**的 token，並把它綁到受害者的詞卡島帳號上。之後受害者在詞卡島做的複習紀錄，都寫進了攻擊者的聲聲 Live 帳號，攻擊者因此看得到。

`state` 的防禦方式很直接：client 在發起授權時產生一個無法猜測的亂數，存在這個瀏覽器的 session 裡，並放進授權請求；AS 把它原封不動地帶回來；client 在 callback 比對兩者，不相同就拒絕，而且**比對完立刻刪掉**，讓同一個 state 不能用第二次。攻擊者沒辦法知道受害者 session 裡的 state，所以偽造的回呼一定對不上。

實作 state 有兩個常見錯誤。第一是把 state 存在 client 端可以修改的地方又不簽章，例如存在一般 cookie 裡卻沒有和 session 綁定，攻擊者可以同時塞 cookie 和參數。第二是只檢查「有沒有帶 state」而不比對值。小晴草稿寫的「state 選填」，在 2.0 的語境下確實是規格寫法（RFC 6749 把它列為 RECOMMENDED），但 Rita 的立場是：聲聲 Live 的所有 client 一律強制。

PKCE（28.8 節）其實也能擋住這種注入：攻擊者塞進來的 code 綁的是攻擊者自己的 `code_challenge`，和受害者 session 裡的 `code_verifier` 對不上。因此 OAuth 2.1 草案允許「確定 AS 支援 PKCE 時，可以靠 PKCE 防 CSRF」。但 state 能在收到回呼的第一時間就擋下偽造請求，還能當索引，把「使用者原本想去的頁面」帶過整個流程，所以實務上兩者都用。

## 28.7 Redirect URI：為什麼一定要精確比對

redirect URI 決定了 AS 要把 code 交給誰。如果攻擊者能讓 AS 把 code 送到攻擊者控制的網址，即使有 state，攻擊者也已經拿到了一個屬於受害者的 code。小晴草稿的「以 `cards.example.net` 開頭即可」就是這類漏洞的教科書例子：字串前綴比對看起來合理，實際上會放過很多完全不同的網址。

| 攻擊者送來的 redirect_uri（概念示意） | 前綴比對 | 只比對 host | 精確比對 |
|---|---|---|---|
| 詞卡島的 `/oauth/callback`（登記值） | 通過 | 通過 | 通過 |
| `cards.example.net.attacker.example/...` | **通過**（前綴相同，實際是別的網域） | 擋下 | 擋下 |
| `cards.example.net/oauth/callback/../redirect?to=…` | **通過** | **通過** | 擋下 |
| 詞卡島網站上任何一個 open redirect 頁面 | **通過** | **通過** | 擋下 |
| 把 https 換成 http | 依實作 | **通過** | 擋下 |

第二列最直觀：前綴比對不懂網域邊界，`cards.example.net.attacker.example` 是攻擊者註冊的網域。第三、四列更隱蔽：host 沒錯，但詞卡島網站上只要有一個 **open redirect**（把使用者轉到參數指定網址的頁面，例如登入後跳轉的 `?next=`），code 就會被轉給攻擊者，出現在對方收到的 URL 或 Referer 中。第五列讓 code 走明文 HTTP。

因此 RFC 9700（OAuth 2.0 安全最佳實務）與 OAuth 2.1 都要求 AS 用**精確字串比對**（exact string matching）：client 登記完整的 redirect URI，授權請求帶來的值必須逐字元相同，不做正規化、不允許萬用字元、不允許路徑前綴。唯一的例外是原生 App 使用 loopback 位址（127.0.0.1 或 `[::1]`）接收回呼時，AS 必須允許 port 不同，因為 App 每次啟動時臨時 listen 的 port 由作業系統分配（28.12 節）。

精確比對還有兩個配套。第一，AS 遇到 `client_id` 不存在或 redirect URI 不符時，**不能**把錯誤導回那個網址，只能在自己的頁面顯示錯誤；否則 AS 就變成一個 open redirect。動手做會實際示範這一點：其他錯誤（例如缺 PKCE）是 302 導回 client，redirect URI 錯誤則是 400 停在 AS。第二，token endpoint 要再比對一次：授權請求帶了哪個 redirect_uri，換 token 時就必須帶同一個，這能擋下「在 A 網址拿到的 code，拿到 B 網址的流程裡兌換」的混用。

> [!tip] 多一個 `iss`，擋下 mix-up
> 如果一個 client 同時串接多個 AS（例如同時支援聲聲 Live 與另一家平台），攻擊者可能讓 client 把 A 的 code 送去 B 兌換，這叫 **mix-up attack**。RFC 9207 讓 AS 在授權回應中加上 `iss` 參數，client 比對它是否等於「這次是向哪個 AS 發起的」。動手做的 client 也做了這個檢查。

## 28.8 PKCE：讓攔到的 code 沒有用

精確比對保證 AS 把 code 送到正確的網址，但「送到正確的網址」不等於「只有正確的程式收得到」。PKCE 最初就是為手機 App 設計的：App 常用自訂的 URI scheme（例如 `com.shengsheng.app:/callback`）接收回呼，而手機上任何 App 都能宣告處理同一個 scheme，惡意 App 就可能先收到 code。public client 沒有 secret，攔到 code 的惡意 App 可以直接拿去兌換。code 也可能從瀏覽器歷史、代理伺服器 log、或被植入的瀏覽器擴充功能外洩。

**PKCE**（Proof Key for Code Exchange，RFC 7636，讀作 pixy）的想法是：「兌換 code 的人，必須證明自己就是發起授權請求的人。」client 每次發起授權前，產生一個只有自己知道的亂數 **`code_verifier`**（43 到 128 個字元，只能用英數字與 `-._~`），計算它的雜湊 **`code_challenge`**，只把雜湊放在 front channel 上；換 token 時才在 back channel 送出原始的 verifier。AS 重算雜湊，相同才發 token。

```text
 client 端                                     AS 端
 ─────────────────────────────────────         ─────────────────────────────────────
 code_verifier = base64url(32 bytes 亂數)
   = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"   （43 字元，只存在 client 記憶體）
        │
        │ SHA-256（對 ASCII bytes）
        ▼
 13d31e961a1ad8ec…acb70f9c3（32 bytes）
        │
        │ base64url，去掉 "="
        ▼
 code_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        │
        └─ front channel：/authorize?…&code_challenge=E9Mel…&code_challenge_method=S256 ─►  記在 code 上

 ……學生登入、同意，code 經 front channel 回到 client（可能被攔截）……

 back channel：POST /token  code=…&code_verifier=dBjft…  ══════════════════════════►  SHA-256＋base64url
                                                                                      == 記下的 challenge？
                                                                                      是 → 發 token
                                                                                      否 → invalid_grant
```

這張圖由上往下讀。verifier 是 32 bytes 亂數經 base64url 編碼的結果，剛好 43 個字元、256 bit 的熵，猜中的機率可以忽略。challenge 是對 verifier 的 ASCII 字串做 SHA-256，再用 base64url（第 27 章介紹過，用 `-_` 取代 `+/` 並去掉 `=`）編碼，也是 43 個字元。攻擊者在 front channel 上能看到 challenge 和 code，但 SHA-256 無法反推，所以算不出 verifier；到 back channel 兌換時，攻擊者拿不出正確的 verifier，code 就只是一串廢字。

`code_challenge_method` 有兩個值：`S256` 與 `plain`。`plain` 表示 challenge 就是 verifier 本身，只防得住「攻擊者只看得到授權回應、看不到授權請求」的情況，現在沒有理由使用；規格把它留著只是為了相容無法計算 SHA-256 的古老環境。聲聲 Live 的 AS 只接受 S256。另一個常見誤解是「confidential client 有 secret，不需要 PKCE」：secret 能證明「是詞卡島在兌換」，但不能證明「是詞卡島**這一次**發起的流程在兌換」。攻擊者若把偷來的 code 注入到詞卡島自己的 callback（28.6 節的情境），詞卡島會用自己的 secret 幫攻擊者兌換；PKCE 讓這個 code 和受害者 session 裡的 verifier 對不上。這就是 OAuth 2.1 要求所有 client 都用 PKCE 的原因。

下面的程式用 RFC 7636 附錄的範例驗證計算方式，並示範三種常見的錯誤 verifier：

```python
import base64
import hashlib
import re
import secrets

UNRESERVED = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")   # RFC 7636 允許的字元與長度


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_verifier() -> str:
    # 32 bytes 亂數 → base64url 剛好 43 個字元，熵 256 bit
    return b64url(secrets.token_bytes(32))


def challenge_s256(verifier: str) -> str:
    if not UNRESERVED.match(verifier):
        raise ValueError("code_verifier 必須是 43–128 個 unreserved 字元")
    return b64url(hashlib.sha256(verifier.encode("ascii")).digest())


# 1. 規格附錄的範例：任何實作都應該算出同一個值
rfc_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
rfc_challenge = challenge_s256(rfc_verifier)
print("RFC 7636 範例 verifier :", rfc_verifier)
print("SHA-256（hex）         :", hashlib.sha256(rfc_verifier.encode()).hexdigest())
print("code_challenge（S256） :", rfc_challenge)
assert rfc_challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

# 2. 自己產生一組：每次執行都不同
v = make_verifier()
print(f"新的 verifier 長度 {len(v)}，challenge 長度 {len(challenge_s256(v))}")

# 3. 常見錯誤：verifier 太短、含不允許的字元、或用標準 base64（有 + / =）
for bad in ["short", "a" * 42, "Kv+Gc6/nqVFj" + "x" * 40]:
    try:
        challenge_s256(bad)
    except ValueError as exc:
        print(f"拒絕 {bad[:12]!r:16}（長度 {len(bad)}）：{exc}")
```

```text
RFC 7636 範例 verifier : dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
SHA-256（hex）         : 13d31e961a1ad8ec2f16b10c4c982e0876a878ad6df144566ee1894acb70f9c3
code_challenge（S256） : E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
新的 verifier 長度 43，challenge 長度 43
拒絕 'short'         （長度 5）：code_verifier 必須是 43–128 個 unreserved 字元
拒絕 'aaaaaaaaaaaa'  （長度 42）：code_verifier 必須是 43–128 個 unreserved 字元
拒絕 'Kv+Gc6/nqVFj'  （長度 52）：code_verifier 必須是 43–128 個 unreserved 字元
```

第三行的 hex 就是圖中那 32 bytes，第四行的 challenge 和 RFC 範例完全相同，你可以用它來測試任何 PKCE 實作。新產生的 verifier 與 challenge 都是 43 字元，這是 32 bytes 亂數最自然的選擇。最後三行是實作時要拒絕的情況：長度不到 43、含有 `+` 與 `/`（用了標準 base64 而不是 base64url，是最常見的跨語言 bug），都會讓 AS 端算出不同的雜湊。

## 28.9 Access token、scope 與 consent

拿到 access token 之後，client 依 RFC 6750 把它放在 `Authorization: Bearer <token>` header 送給 RS。**bearer token** 的意思是「持有者即可使用」，像現金而不像信用卡：誰拿到誰就能用，RS 不會問「你是誰」。這也是為什麼 RFC 6750 雖然允許把 token 放在 URL 的 `access_token` 參數，OAuth 2.1 卻把這個做法刪掉：URL 會進入 log、瀏覽器歷史與 Referer。

RS 收到 token 後要回答三個問題：token 有效嗎（簽章、未過期、未撤銷）？token 是發給我的嗎（audience）？token 的 scope 夠不夠這個操作？token 的格式有兩種，第 27 章詳細比較過：**opaque token** 是一串亂數，RS 要呼叫 AS 的 **introspection endpoint**（RFC 7662）查詢它代表什麼，好處是能即時撤銷；**JWT access token**（RFC 9068 定義了標準 profile）讓 RS 自己驗簽章就知道內容，省下一次網路往返，代價是撤銷要等 token 過期。聲聲 Live 對外部合作夥伴用 opaque token、10 分鐘有效，動手做也採用這個設計。

RS 拒絕請求時，要用 `WWW-Authenticate` header 說清楚原因，client 才知道該怎麼補救：

| 情況 | 狀態碼 | `WWW-Authenticate` | client 該做什麼 |
|---|---|---|---|
| 沒帶 token | 401 | `Bearer realm="api"` | 走授權流程 |
| token 格式錯誤、參數重複 | 400 | `Bearer error="invalid_request"` | 修程式 |
| token 過期、被撤銷、audience 不符 | 401 | `Bearer error="invalid_token"` | 用 refresh token 換新的，失敗就重新授權 |
| token 有效但 scope 不夠 | 403 | `Bearer error="insufficient_scope", scope="vocab:write"` | 請使用者授權更多 scope，不要重試 |

401 與 403 之分很重要：401 換一張 token 可能就好，403 則必須回頭請使用者同意更多權限。把 scope 不足回成 401，會讓 client 進入「refresh、重試、再 401」的無窮迴圈。

**scope**（權限範圍）是 client 向使用者要求、AS 記在 token 上的權限清單，格式是以空白分隔的字串，意義完全由 AS 與 RS 自己定義。小晴草稿只有一個 `all`，等於回到「給密碼」的權限模型。Rita 和小晴重新設計後，聲聲 Live 的 scope 是這樣：`vocab:read`（讀課堂生字）、`vocab:write`（寫回複習成績）、`schedule:read`（讀課表）、`profile:read`（讀暱稱與頭像）。付款與帳號設定沒有對外的 scope，第三方永遠拿不到。

設計 scope 有三個原則：以「使用者能理解的動作」為單位，因為 scope 會出現在同意畫面上（`vocab:read` 能翻成「讀取你的課堂生字」，`db:table42` 不行）；讀寫分開；只在需要時才要求（incremental authorization），例如詞卡島等學生第一次按「同步成績」時，才再要 `vocab:write`。

```text
 ┌──────────────────────────────────────────────────────────┐
 │  auth.shengsheng.example                                 │  ← 網址列是聲聲 Live 自己的網域
 │                                                          │
 │  「詞卡島」想存取你的聲聲 Live 帳號（student23）         │  ← 登記時審核過的 client 名稱
 │                                                          │
 │   ☑ 讀取你的課堂生字（vocab:read）                       │
 │   ☑ 寫回你的單字複習成績（vocab:write）                  │  ← 使用者可以取消勾選
 │                                                          │
 │   詞卡島不會取得你的密碼；你可以隨時在「帳號 > 已連結    │
 │   的 App」取消授權。                                     │
 │                                                          │
 │            [ 取消 ]                [ 允許 ]              │
 └──────────────────────────────────────────────────────────┘
```

這就是 **consent**（同意）畫面，OAuth 的「委派」在這一刻發生。最上面的網址列讓學生確認自己是在聲聲 Live 的網站上，這也是為什麼原生 App 必須用系統瀏覽器而不是嵌入式 webview（28.12 節）：webview 的網址列由 App 控制，使用者無從確認。client 名稱來自 AS 的登記資料，而不是授權請求的參數，避免惡意 client 自稱「聲聲 Live 官方」。如果學生取消勾選 `vocab:write`，token 回應的 `scope` 就只剩 `vocab:read`。聲聲 Live 自家的第一方 App（first-party client）通常會跳過同意畫面，因為 client 和資源屬於同一家公司，但這個決定要記錄在 AS 的 client 登記上，而不是由請求參數控制。

## 28.10 Refresh token 與輪替

小晴草稿裡的「access token 30 天」是為了避開 refresh token 的複雜度，但它讓一張外洩的 bearer token 能被使用整整一個月。正確的做法是讓 access token 短效（聲聲 Live 用 10 分鐘），另外發一張 **refresh token**（更新權杖）：access token 過期時，client 在 back channel 用 `grant_type=refresh_token` 換一張新的，使用者完全不用重新登入。

兩種 token 分工的道理在於曝光面不同。access token 會送到每一個 RS，經過 API gateway、出現在服務間的呼叫中，曝光的機會多，所以要短；refresh token 只在 client 與 AS 之間傳遞，confidential client 換的時候還要驗 client 身分，所以可以長。refresh 時 client 也可以帶較小的 scope，替特定操作換一張權限更少的 access token（**downscoping**），但不能擴大到原本沒有同意的範圍。

public client 的 refresh token 沒有 client 驗證的保護，被偷就等於被冒用。OAuth 2.1 因此要求 public client 的 refresh token 必須「綁定 sender」（28.14 節的 DPoP）或「輪替」。**refresh token 輪替**（rotation）是指每次使用 refresh token，AS 都發一張新的 refresh token 並讓舊的作廢；AS 把同一次登入衍生出的所有 refresh token 視為一個**家族**（family）。如果一張已經作廢的舊 token 又被拿來使用，AS 知道有兩個人手上有同一系列的 token，卻分不出誰是正主，於是撤銷整個家族。

```text
 時間 ──────────────────────────────────────────────────────────────────────►
 day 0       day 1              day 1+                   day 2              day 2
   │           │                  │                        │                  │
 登入        App 用 RT1         App 用 RT2               攻擊者用偷來的     App 用 RT3
 發 RT1      → 發 RT2           → 發 RT3                 RT1（已作廢）       → 被拒，
   │         RT1 作廢           RT2 作廢                 → AS 偵測重複使用   請學生重新登入
   │           │                  │                    → 整個家族撤銷      （攻擊者也被踢出）
   └─────────── 家族 F：RT1 → RT2 → RT3 ─────────────────────┘
```

時間軸的關鍵在 day 2：攻擊者拿的是過去某個時間點偷到的 RT1。輪替讓它在 day 1 就已作廢，攻擊者一使用就觸發偵測，AS 撤銷整個家族，正牌 App 下次 refresh 也會失敗，只好請學生重新登入。這個「連累正主」的設計是刻意的：AS 無法判斷誰是攻擊者，寧可讓兩邊都失效，由使用者重新驗證身分來決勝負。如果是攻擊者先 refresh、正主後到，結果一樣：正主拿著被輪替掉的 token 觸發偵測，攻擊者手上的新 token 也被撤銷。

下面的程式實作了輪替、重複使用偵測與 scope 只能縮小的規則。AS 端只保存 refresh token 的 SHA-256，資料庫外洩也拿不到可用的 token：

```python
import hashlib
import secrets

CLOCK = {"now": 0}


class RefreshStore:
    """refresh token 輪替＋重複使用偵測。只存 hash，資料庫外洩也拿不到可用的 token。"""

    def __init__(self, ttl=30 * 86400):
        self.ttl = ttl
        self.by_hash = {}            # sha256(token) → 紀錄
        self.families = {}           # family id → 是否有效

    def _issue(self, family, sub, scope):
        token = secrets.token_urlsafe(32)
        h = hashlib.sha256(token.encode()).hexdigest()
        self.by_hash[h] = dict(family=family, sub=sub, scope=scope, used=False, exp=CLOCK["now"] + self.ttl)
        return token

    def login(self, sub, scope):     # 使用者完成 authorization code 流程時建立新家族
        family = secrets.token_hex(4)
        self.families[family] = True
        return family, self._issue(family, sub, scope)

    def refresh(self, token, scope=None):
        rec = self.by_hash.get(hashlib.sha256(token.encode()).hexdigest())
        if rec is None or not self.families[rec["family"]] or CLOCK["now"] >= rec["exp"]:
            return "invalid_grant", None
        if rec["used"]:              # 舊的 refresh token 又出現：有人複製了它
            self.families[rec["family"]] = False
            return "invalid_grant（偵測到重複使用，整個家族撤銷）", None
        if scope and not set(scope.split()) <= set(rec["scope"].split()):
            return "invalid_scope（只能縮小，不能擴大）", None
        rec["used"] = True
        return "ok", self._issue(rec["family"], rec["sub"], scope or rec["scope"])


store = RefreshStore()
family, rt1 = store.login("stu_1024", "vocab:read vocab:write")
print("day 0   學生完成登入，建立新的 token 家族，拿到 RT1")

CLOCK["now"] += 86400
result, rt2 = store.refresh(rt1)
print(f"day 1   App 用 RT1 換 → {result}，拿到 RT2（RT1 從此作廢）")

result, _ = store.refresh(rt2, scope="vocab:read admin")
print(f"day 1   App 想用 RT2 擴大 scope → {result}")

CLOCK["now"] += 3600
result, rt3 = store.refresh(rt2, scope="vocab:read")
print(f"day 1+  App 用 RT2 換（縮小成 vocab:read）→ {result}，拿到 RT3")

CLOCK["now"] += 86400
result, _ = store.refresh(rt1)       # 攻擊者手上是從舊備份偷來的 RT1
print(f"day 2   有人拿 RT1 來換 → {result}")
result, _ = store.refresh(rt3)
print(f"day 2   App 用 RT3 換 → {result}，只好請學生重新登入")
assert result == "invalid_grant" and store.families[family] is False
```

```text
day 0   學生完成登入，建立新的 token 家族，拿到 RT1
day 1   App 用 RT1 換 → ok，拿到 RT2（RT1 從此作廢）
day 1   App 想用 RT2 擴大 scope → invalid_scope（只能縮小，不能擴大）
day 1+  App 用 RT2 換（縮小成 vocab:read）→ ok，拿到 RT3
day 2   有人拿 RT1 來換 → invalid_grant（偵測到重複使用，整個家族撤銷）
day 2   App 用 RT3 換 → invalid_grant，只好請學生重新登入
```

前四行是正常使用：每次 refresh 都換新 token，擴大 scope 被拒絕，但縮小可以。第五行是攻擊：RT1 已經被用過，再出現代表它被複製了，家族立刻撤銷；第六行是正牌 App 的下場。實務上要處理一個副作用：手機網路不穩時，App 送出 refresh 請求、AS 已經輪替，但回應在路上遺失，App 只好用舊 token 重試，結果誤觸偵測。很多 AS 因此提供數秒的寬限期，期間內重複使用舊 token 會拿到同一組新 token；寬限期越長，偵測就越遲鈍，要依風險取捨。

refresh token 也要能主動撤銷：學生在「已連結的 App」按下取消，AS 就撤銷該 client 的所有 refresh token；client 也可以在使用者登出時呼叫 revocation endpoint（RFC 7009）。搭配 10 分鐘的 access token，撤銷最慢 10 分鐘生效。

## 28.11 Client credentials：沒有使用者的時候

聲聲 Live 內部的推薦服務 `reco`，每晚要讀全站的課表來計算「你可能喜歡的老師」。這裡沒有學生在場，沒有人能按「允許」，`reco` 是在以**自己的身分**存取資源。這種 machine-to-machine 的情境用 **client credentials** grant：client 直接在 token endpoint 驗證自己的身分，換到一張代表自己的 access token。

```text
 reco（confidential client）                    auth（AS）                       api（RS）
    │                                              │                                 │
    │══ POST /token ══════════════════════════════►│ 驗證 client（secret、            │
    │   grant_type=client_credentials              │ private_key_jwt 或 mTLS）       │
    │   scope=lessons:read                         │ scope 在 reco 的登記範圍內？    │
    │   （client 驗證）                             │                                 │
    │◄═ 200 access_token、expires_in=300 ══════════│ 沒有 refresh_token               │
    │                                              │                                 │
    │══ GET /lessons  Authorization: Bearer … ════════════════════════════════════►│ 檢查 aud、scope
    │◄═ 200 ═════════════════════════════════════════════════════════════════════════│
    │    （token 快取到過期前 30 秒，再重新要一張）    │                                 │
```

這個流程沒有 front channel，所以沒有 redirect URI、state、PKCE，也沒有 refresh token：client 隨時可以用自己的憑證再要一張，refresh token 只會多一個要保管的秘密。圖中有兩個實務重點。第一，token 要快取，不要每個 API 呼叫都去 token endpoint 要一次，否則 AS 會變成全公司最大的單點流量；第二，在過期前留一點餘裕就換新，避免「剛好在邊界上過期」的請求被拒。

```python
import base64
import json
import secrets
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode

CLOCK = {"now": 0.0}
SERVICES = {"reco": ("reco-secret", {"lessons:read"})}     # client_id → (secret, 允許的 scope)
issued = []


class TokenEndpoint(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()).items()}
        cid, _, secret = base64.b64decode(self.headers["Authorization"][6:]).decode().partition(":")
        known = SERVICES.get(cid)
        scope = set(form.get("scope", "").split())
        if form.get("grant_type") != "client_credentials" or not known or secret != known[0]:
            status, body = 401, {"error": "invalid_client"}
        elif not scope <= known[1]:
            status, body = 400, {"error": "invalid_scope"}
        else:
            issued.append(CLOCK["now"])
            status, body = 200, {"access_token": secrets.token_urlsafe(24), "token_type": "Bearer",
                                 "expires_in": 300, "scope": " ".join(sorted(scope))}   # 沒有 refresh_token
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ServiceToken:
    """service 端的 token 快取：過期前 30 秒就換新的，避免邊界上的請求被拒。"""

    def __init__(self, url, cid, secret, scope, skew=30):
        self.url, self.scope, self.skew = url, scope, skew
        self.auth = "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()
        self.token, self.expires_at = None, 0.0

    def get(self):
        if self.token is None or CLOCK["now"] >= self.expires_at - self.skew:
            body = urlencode({"grant_type": "client_credentials", "scope": self.scope}).encode()
            req = urllib.request.Request(self.url, body, {"Authorization": self.auth})
            with urllib.request.urlopen(req, timeout=3) as resp:
                tok = json.load(resp)
            self.token, self.expires_at = tok["access_token"], CLOCK["now"] + tok["expires_in"]
            assert "refresh_token" not in tok
        return self.token


srv = ThreadingHTTPServer(("127.0.0.1", 0), TokenEndpoint)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/token"

reco = ServiceToken(url, "reco", "reco-secret", "lessons:read")
for t in range(0, 601, 20):            # 模擬 10 分鐘內每 20 秒呼叫一次 API
    CLOCK["now"] = float(t)
    reco.get()
print(f"31 次 API 呼叫，只向 token endpoint 要了 {len(issued)} 次，時間點 {issued}")

try:
    ServiceToken(url, "reco", "reco-secret", "lessons:read payments:write").get()
except urllib.error.HTTPError as exc:
    print(f"reco 要 payments:write → {exc.code} {json.load(exc)['error']}")
srv.shutdown()
srv.server_close()
```

```text
31 次 API 呼叫，只向 token endpoint 要了 3 次，時間點 [0.0, 280.0, 560.0]
reco 要 payments:write → 400 invalid_scope
```

31 次呼叫只要了 3 次 token：第 0 秒拿到 300 秒的 token，第 280 秒（過期前 30 秒內）換新，第 560 秒再換一次。第二行顯示 AS 依登記資料限制 scope，推薦服務要不到付款權限。client credentials 的真正難題不在流程，而在「service 的憑證放在哪裡、怎麼輪替」；把 client secret 換成雲端的 workload identity 或 mTLS，是第 30 章的主題。

> [!warning] 常見誤解
> client credentials 拿到的 token 代表 service 本身，不代表任何使用者。如果 `reco` 用它去呼叫「讀某個學生的私人筆記」，RS 不能因為「呼叫方是內部服務」就放行，否則任何一個被入侵的內部服務都能讀所有人的資料。需要「代表某個使用者」時，要把使用者的授權一路傳下去，或用 token exchange（RFC 8693）換一張範圍更小的 token。

## 28.12 瀏覽器與手機 App：public client 的實務

聲聲 Live 自己也有 OAuth client：老師後台是一個 SPA，學生用的是 iOS 與 Android App。它們都是 public client，各有一組實務規則。

**原生 App**依 RFC 8252〈OAuth 2.0 for Native Apps〉的建議：授權流程必須在**外部的使用者代理**（系統瀏覽器，或 iOS 的 `ASWebAuthenticationSession`、Android 的 Custom Tabs）中進行，不能用 App 內嵌的 webview。因為內嵌 webview 的 App 能讀取使用者輸入的密碼，使用者也無法從網址列確認自己在正牌網站；系統瀏覽器還能共用既有的登入狀態。回呼的接收方式依安全性排序是：claimed HTTPS（iOS Universal Links、Android App Links）、反向網域名稱的自訂 scheme（例如 `com.shengsheng.app:/oauth`）、loopback 位址（桌面程式臨時 listen 在 127.0.0.1 的 port），而且都必須搭配 PKCE。

**SPA** 的難題是 token 放在哪裡。把 access token 或 refresh token 放在 `localStorage`，一旦網站有任何 XSS（第 23 章），攻擊者的 script 就能把 token 送走，而且離開網站之後還能繼續用。RFC 10017〈OAuth 2.0 for Browser-Based Applications〉（見 28.13 節的現況）的首選建議是 **BFF**（Backend for Frontend）：SPA 不直接當 OAuth client，而是由同網域的一個小型後端擔任 confidential client，token 只留在後端，瀏覽器只拿到一個 `HttpOnly`、`Secure`、`SameSite` 的 session cookie。

```text
 ❶ SPA 直接當 public client（不建議用於敏感資料）
 瀏覽器 ┌──────────────────────────────┐
        │ SPA JavaScript                │── Bearer token ──► api
        │ access_token、refresh_token    │
        │ 在 JS 記憶體或 localStorage    │ ◄── XSS 可直接讀走並帶離網站
        └──────────────────────────────┘

 ❷ BFF（RFC 10017 的首選）
 瀏覽器 ┌──────────────────┐   cookie（HttpOnly; Secure;   ┌───────────────────┐   Bearer   ┌─────┐
        │ SPA JavaScript   │── SameSite）────────────────► │ BFF（同網域後端）   │──────────►│ api │
        │ 看不到任何 token  │                              │ confidential client │           └─────┘
        └──────────────────┘ ◄───── JSON ──────────────── │ token 存在 server 端 │
                                                          └─────────┬─────────┘
                                                                    │ back channel：code＋PKCE、refresh
                                                                    ▼
                                                                  auth
```

兩種架構的差別在 XSS 發生時的損害。❶ 的 token 在 JavaScript 能碰到的地方，XSS 的 script 可以把它送到攻擊者的伺服器，攻擊者之後在自己的電腦上隨意使用，直到過期；❷ 的 token 不在瀏覽器裡，XSS 頂多在使用者開著頁面的期間透過 BFF 送請求，無法把憑證帶走。代價是多一個要維運的後端，以及 cookie 帶來的 CSRF 考量（SameSite 與 CSRF token，第 23 章）。聲聲 Live 的老師後台因為能看到學生的聯絡資料，採用 BFF。

**沒有鍵盤的裝置**（例如智慧電視上的直播 App）用 **device authorization grant**（RFC 8628）：電視顯示短碼，學生用手機登入並輸入短碼，電視在背景輪詢 token endpoint 直到授權完成。

## 28.13 OAuth 2.1：把十年的教訓寫進規格

RFC 6749 在 2012 年發布時，瀏覽器還沒有普遍支援 CORS，手機 App 剛起步，很多今天看來危險的流程在當時是合理的妥協。之後十多年，PKCE、Bearer token 用法、native app 指引、安全最佳實務等文件陸續補上。**OAuth 2.1** 不是新協定，而是把這些補充合併成一份文件，並刪掉已被證明不安全的部分。

| 項目 | OAuth 2.0（RFC 6749 與當年的實務） | OAuth 2.1（草案） | 為什麼 |
|---|---|---|---|
| PKCE | 選用，主要給 public client | authorization code 原則上都必須用 | 防 code 攔截與注入，對 confidential client 也有效 |
| implicit grant | 有：token 直接放在 redirect 的 fragment | **移除** | token 經 front channel 外洩，無法綁定 client，也不能安全發 refresh token |
| password grant（ROPC） | 有：client 直接收使用者密碼 | **移除** | 就是 password anti-pattern，也無法支援 MFA 與 passkeys |
| redirect URI 比對 | 規格允許部分比對 | 精確字串比對（loopback 的 port 例外） | 前綴與萬用字元比對造成大量 code 外洩 |
| URL 中的 bearer token | RFC 6750 允許 `?access_token=` | **移除** | URL 會進入 log 與 Referer |
| public client 的 refresh token | 未特別規定 | 必須 sender-constrained 或輪替 | 沒有 client 驗證保護 |
| state | RECOMMENDED | 必須防 CSRF；可用 PKCE 或 state | 寫清楚 CSRF 的防禦責任 |

第 1 章提過的 **implicit grant**，是讓 AS 在 redirect 時直接把 access token 放在 fragment（`#access_token=…`）交給頁面上的 JavaScript，因為當年的 SPA 無法跨網域呼叫 token endpoint。代價是 token 走 front channel：留在瀏覽器歷史、在某些 redirect 中被瀏覽器帶到下一個網址、任何能在頁面執行 script 的人都拿得到。如今瀏覽器都支援 CORS，SPA 可以直接走 authorization code＋PKCE，implicit 已經沒有存在的理由。

> [!note] 2026 現況
> 以下依 2026 年 10 月查證（`tools/.network_survey.md`），截至 2026 年 10 月：
>
> - **OAuth 2.1 仍是草案**：最新版是 `draft-ietf-oauth-v2-1-16`（2026-09-03），還沒有 RFC 編號，不要預測編號。工作小組的 milestone 是 2026 年 12 月送 IESG；通過後將取代 RFC 6749 與 RFC 6750。主要內容就是上表：PKCE 必要、移除 implicit 與 password grant、redirect URI 精確比對。
> - **RFC 10017**〈OAuth 2.0 for Browser-Based Applications〉於 2026-08 發布，屬 BCP 212，作者為 Parecki、De Ryck、Waite，推薦 BFF 模式（已查證）。
> - **RFC 9700**〈OAuth 2.0 Security Best Current Practice〉於 2025-01 發布，是目前談 OAuth 安全時最主要的引用文件（依知識，未經本次網路查證）。
> - 其他常一起出現的規格（依知識）：DPoP 是 RFC 9449；PAR（Pushed Authorization Requests）是 RFC 9126；Resource Indicators 是 RFC 8707；JWT access token profile 是 RFC 9068；Protected Resource Metadata 是 RFC 9728。
> - 對實務的意義：你今天就可以照 2.1 的規則實作，因為它的每一條都已經出現在 RFC 9700 等既有文件裡；成熟的 AS 產品多半已經預設要求 PKCE、禁止 implicit。

## 28.14 DPoP：讓偷到的 token 用不了

前面所有的防禦都在保護「token 不要被偷」。但 token 終究會經過 client 的記憶體、log、除錯工具，bearer token 一旦外洩，持有者就能使用。**sender-constrained token**（綁定持有者的 token）換了一個方向：讓 token 只有原本的 client 能用，偷走也沒用。做法有兩種：mTLS（RFC 8705，token 綁定 client 的 TLS 憑證，適合 service 之間）與 **DPoP**（Demonstrating Proof of Possession，RFC 9449，在應用層證明持有私鑰，適合手機 App 與瀏覽器）。

DPoP 的流程是：client 在裝置上產生一組非對稱金鑰（例如 P-256 的 ES256），私鑰不離開裝置。之後**每一個請求**都附上一個 `DPoP` header，內容是用私鑰簽的短 JWT，稱為 **DPoP proof**，裡面寫著「我要對哪個 URL 做什麼 method、在什麼時間、這是第幾個不重複的 proof」。AS 發 token 時，把公鑰的指紋寫進 token 的 `cnf.jkt`（confirmation，JWK thumbprint），回應的 `token_type` 是 `DPoP` 而不是 `Bearer`；RS 收到請求時，除了驗 token，還要驗 proof 的簽章、內容，並確認 proof 的公鑰指紋等於 token 綁定的那一個。

```text
 DPoP proof（JWT，三段 base64url，以 "." 連接）
 ┌─ header ───────────────────────────────────────────────┐
 │ "typ": "dpop+jwt"     ← 專用型別，防止拿別種 JWT 冒充    │
 │ "alg": "ES256"        ← 必須是非對稱演算法               │
 │ "jwk": { 公鑰 }        ← RS 用它驗簽章，並算 thumbprint   │
 ├─ payload ──────────────────────────────────────────────┤
 │ "jti": 唯一 ID         ← RS 記住用過的，防重放           │
 │ "htm": "GET"           ← 這個 proof 只能用在這個 method  │
 │ "htu": api…/vocab      ← 只能用在這個 URL（不含 query）  │
 │ "iat": 1790000000      ← 簽發時間，RS 只接受很短的窗口   │
 │ "ath": base64url(SHA-256(access token)) ← 只配這張 token │
 │ "nonce": 伺服器給的值   ← 選用，用 DPoP-Nonce header 下發 │
 ├─ signature ────────────────────────────────────────────┤
 │ ES256(私鑰, header.payload)  ← 私鑰永遠不離開裝置        │
 └────────────────────────────────────────────────────────┘

 GET /vocab HTTP/1.1
 Host: api.shengsheng.example
 Authorization: DPoP Kz~8mXK1EalYznwH-LC-1fBAo.4Ljp~zsPE_NeO.gxU
 DPoP: eyJ0eXAiOiJkcG9wK2p3dCIs…（上面那個 proof）
```

由上往下讀。header 的 `typ` 是固定的 `dpop+jwt`，RS 不接受其他型別，避免攻擊者拿某個合法的 ID token 冒充；`jwk` 直接帶上公鑰。payload 的 `htm` 與 `htu` 讓 proof 只對一個 method＋URL 有效，`iat` 與 `jti` 讓它只在很短的時間內有效、而且只能用一次；`ath` 是 access token 的雜湊，把 proof 和這張 token 綁在一起。最下面是實際的請求：注意 `Authorization` 的 scheme 是 `DPoP` 而不是 `Bearer`，告訴 RS「請同時檢查 DPoP header」。

攻擊者偷到 access token 時，手上沒有私鑰，簽不出公鑰指紋相符的 proof；偷到一個 proof，也只能在幾十秒內、對同一個 URL 用一次，而 RS 記得 `jti` 會擋下重放。DPoP 也能綁定 refresh token：public client 每次 refresh 都要附上 proof，偷到 refresh token 的人無法使用，這就是 OAuth 2.1「sender-constrained 或輪替」的前一個選項。它擋不住的是：攻擊者已經能在裝置上執行程式並呼叫簽章功能（例如 XSS 期間），這時攻擊者可以當場簽出合法的 proof，所以 DPoP 是縮小外洩後果，不是取代 XSS 防禦。

Python 標準函式庫沒有 ES256 簽章，下面的程式略過簽章驗證，只示範其餘的計算與檢查。範例公鑰與 access token 取自 RFC 9449 的範例，算出的 thumbprint 可以和規格對照：

```python
import base64
import hashlib
import json
import secrets
import unicodedata


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def jwk_thumbprint(jwk: dict) -> str:
    # RFC 7638：只取必要欄位、key 依字母排序、不留空白，再做 SHA-256
    required = {k: jwk[k] for k in ("crv", "kty", "x", "y")}
    canonical = json.dumps(required, separators=(",", ":"), sort_keys=True)
    return b64url(hashlib.sha256(canonical.encode()).digest())


# App 在裝置上產生的 P-256 公鑰（座標用固定值示意；私鑰永遠不離開裝置）
public_jwk = {"kty": "EC", "crv": "P-256",
              "x": "l8tFrhx-34tV3hRICRDY9zCkDlpBhF42UQUfWVAWBFs",
              "y": "9VE4jf_Ok_o64zbTTlcuNJajHmt6v9TDVrU0CdvGRDA"}
access_token = "Kz~8mXK1EalYznwH-LC-1fBAo.4Ljp~zsPE_NeO.gxU"

header = {"typ": "dpop+jwt", "alg": "ES256", "jwk": public_jwk}
claims = {"jti": secrets.token_urlsafe(12), "htm": "GET", "htu": "https://api.shengsheng.example/vocab",
          "iat": 1_790_000_000, "ath": b64url(hashlib.sha256(access_token.encode("ascii")).digest())}
print("cnf.jkt（AS 寫進 access token）:", jwk_thumbprint(public_jwk))
print("ath（綁定這一個 access token）  :", claims["ath"])
assert jwk_thumbprint(public_jwk) == "0ZcOCORZNYy-DWpqq30jZyJGHTN0d2HglBV3uiguA4I"   # 與 RFC 9449 範例一致


def rs_check(header, claims, method, url, token, bound_jkt, seen, now):
    """resource server 驗 DPoP proof 的順序（ES256 簽章驗證需第三方套件，這裡略過）。"""
    if header.get("typ") != "dpop+jwt" or header.get("alg") in (None, "none") or header["alg"].startswith("HS"):
        return "typ／alg 不合格"
    if claims["htm"] != method or claims["htu"] != url:
        return "proof 不是給這個請求的（htm／htu 不符）"
    if abs(now - claims["iat"]) > 60:
        return "proof 太舊或來自未來（iat）"
    if claims["jti"] in seen:
        return "proof 被重放（jti 重複）"
    if claims.get("ath") != b64url(hashlib.sha256(token.encode()).digest()):
        return "proof 綁的是別的 access token（ath）"
    if jwk_thumbprint(header["jwk"]) != bound_jkt:
        return "proof 的金鑰不是 token 綁定的那把（jkt）"
    seen.add(claims["jti"])
    return "通過"


def show(label, result):
    width = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in label)
    print(f"{label}{' ' * (24 - width)}→ {result}")
    return result


jkt, seen, url = jwk_thumbprint(public_jwk), set(), "https://api.shengsheng.example/vocab"
assert show("正常請求", rs_check(header, claims, "GET", url, access_token, jkt, seen, 1_790_000_005)) == "通過"
show("同一個 proof 再送一次", rs_check(header, claims, "GET", url, access_token, jkt, seen, 1_790_000_006))
show("改成 POST 去寫入", rs_check(header, {**claims, "jti": "n2"}, "POST", url, access_token, jkt, seen, 1_790_000_007))
show("五分鐘前的 proof", rs_check(header, {**claims, "jti": "n3"}, "GET", url, access_token, jkt, seen, 1_790_000_300))
other_key = {**public_jwk, "x": "c29tZS1vdGhlci1rZXktbm90LWJvdW5kLXRvLXRva2Vu"}
show("偷 token、配自己的金鑰", rs_check({**header, "jwk": other_key}, {**claims, "jti": "n4"}, "GET", url,
                                    access_token, jkt, seen, 1_790_000_009))
```

```text
cnf.jkt（AS 寫進 access token）: 0ZcOCORZNYy-DWpqq30jZyJGHTN0d2HglBV3uiguA4I
ath（綁定這一個 access token）  : fUHyO2r2Z3DZ53EsNrWBb0xWXoaNy59IiKCAqksmQEo
正常請求                → 通過
同一個 proof 再送一次   → proof 被重放（jti 重複）
改成 POST 去寫入        → proof 不是給這個請求的（htm／htu 不符）
五分鐘前的 proof        → proof 太舊或來自未來（iat）
偷 token、配自己的金鑰  → proof 的金鑰不是 token 綁定的那把（jkt）
```

第一行是 JWK thumbprint（RFC 7638）：只取 EC 公鑰的必要欄位、依字母排序、去掉空白後做 SHA-256，也就是 AS 寫進 `cnf.jkt` 的值。接下來五行依序是：正常請求通過、重送被 `jti` 擋、換 method 被 `htm` 擋、過期被 `iat` 擋；最後一行模擬攻擊者偷到 access token、用自己的金鑰簽 proof，公鑰指紋和 token 綁定的不同而失敗。真實的 RS 在這些檢查之前，還要先驗 ES256 簽章。

## 28.15 動手做：在 127.0.0.1 上跑完整的 authorization code＋PKCE

這一節把前面的內容組裝起來。程式在 127.0.0.1 上用 port 0 起三個 `http.server`：authorization server（`/authorize`、`/token`、`/introspect`）、resource server（`/vocab` 要 `vocab:read`、`/progress` 要 `vocab:write`）、詞卡島 client（`/login`、`/callback`）。一個模擬的瀏覽器跟著 302 在三者之間跑完正常流程，接著逐一重現每一道檢查擋下的錯誤情境。

```text
             模擬的瀏覽器（http.client，自己處理 302 與 cookie）
              │ GET /login           │ GET /authorize          │ GET /callback
              ▼                      ▼                         ▼
 ┌──────────────────────┐   ┌──────────────────────────┐
 │ client  127.0.0.1:P1 │   │ AS  127.0.0.1:P2          │   CLIENTS：cards（secret hash、
 │ /login  /callback    │══►│ /authorize /token         │            redirect_uris、scopes）
 │ SESSIONS：state、     │   │ /introspect              │   CODES：一次性、60 秒
 │ verifier（server 端） │   └────────────▲─────────────┘   TOKENS：opaque、600 秒、aud
 └──────────┬───────────┘                │ introspect（RS 用自己的憑證）
            │ Bearer                     │
            ▼                            │
 ┌──────────────────────┐                │
 │ RS  127.0.0.1:P3     │────────────────┘
 │ /vocab  /progress    │
 └──────────────────────┘
```

圖中的雙線是 back channel：client 換 token、RS 呼叫 introspection，都不經過模擬的瀏覽器。AS 有三張表：`CLIENTS` 記錄登記資料（secret 只存 SHA-256），`CODES` 記錄每個授權碼的綁定資訊，`TOKENS` 記錄 access token 的 scope 與 audience。為了不必真的等待，程式用 `CLOCK` 模擬時間。學生的登入與同意畫面在這裡省略，AS 假設學生 `stu_1024` 已經按下允許。正式環境的每一個 URL 都必須是 HTTPS；這裡用 loopback 上的 HTTP 只是為了離線執行。

```python
import base64
import hashlib
import hmac
import http.client
import json
import secrets
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

CLOCK = {"now": 1_790_000_000}          # 模擬時鐘：測過期不必真的等
CLIENTS, CODES, TOKENS, SESSIONS = {}, {}, {}, {}
JSON = {"Content-Type": "application/json", "Cache-Control": "no-store"}


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def s256(verifier: str) -> str:
    return b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def basic(user, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def call(method, url, form=None, headers=None):
    u = urlsplit(url)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=3)
    headers = dict(headers or {})
    body = urlencode(form) if form is not None else None
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, u.path + ("?" + u.query if u.query else ""), body, headers)
    resp = conn.getresponse()
    status, hdrs, data = resp.status, dict(resp.getheaders()), resp.read()
    conn.close()
    return status, hdrs, (json.loads(data) if data else {})


def serve(routes):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_one(self, method):
            u = urlsplit(self.path)
            params = {k: v[0] for k, v in parse_qs(u.query).items()}
            if method == "POST":
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
                params.update({k: v[0] for k, v in parse_qs(raw).items()})
            status, headers, body = routes[(method, u.path)](self, params)
            data = json.dumps(body, ensure_ascii=False).encode() if body else b""
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = lambda self: self.handle_one("GET")
        do_POST = lambda self: self.handle_one("POST")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def client_auth(handler):
    """解析 HTTP Basic，回傳通過驗證的 client_id 或 None。"""
    try:
        cid, secret = base64.b64decode(handler.headers["Authorization"][6:]).decode().split(":", 1)
    except Exception:
        return None
    rec = CLIENTS.get(cid)
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return cid if rec and hmac.compare_digest(digest, rec["secret_sha256"]) else None


# ───────── Authorization server（auth.shengsheng.example 的縮小版）─────────
def authorize(h, q):
    client = CLIENTS.get(q.get("client_id"))
    redirect = q.get("redirect_uri", "")
    if client is None or redirect not in client["redirect_uris"]:      # 精確字串比對
        return 400, JSON, {"error": "invalid_request", "error_description": "redirect_uri 未登記，不導回"}

    def back(**params):                                                  # 只導回已驗證的網址
        params.update(state=q.get("state", ""), iss=AS)
        return 302, {"Location": redirect + "?" + urlencode(params)}, None

    if q.get("response_type") != "code":
        return back(error="unsupported_response_type")
    if q.get("code_challenge_method") != "S256" or len(q.get("code_challenge", "")) != 43:
        return back(error="invalid_request", error_description="PKCE S256 required")
    scope = set(q.get("scope", "").split())
    if not scope or not scope <= client["scopes"]:
        return back(error="invalid_scope")
    # （真實系統在這裡確認學生已登入，並顯示同意畫面；本實驗假設 stu_1024 已按下同意）
    code = secrets.token_urlsafe(32)
    CODES[code] = dict(client_id=q["client_id"], redirect_uri=redirect, challenge=q["code_challenge"],
                       scope=" ".join(sorted(scope)), sub="stu_1024", exp=CLOCK["now"] + 60,
                       used=False, issued=[])
    return back(code=code)


def token(h, q):
    cid = client_auth(h)
    if cid is None:
        return 401, {**JSON, "WWW-Authenticate": 'Basic realm="token"'}, {"error": "invalid_client"}
    if q.get("grant_type") != "authorization_code":
        return 400, JSON, {"error": "unsupported_grant_type"}
    rec = CODES.get(q.get("code", ""))
    fail = lambda why: (400, JSON, {"error": "invalid_grant", "error_description": why})
    if rec is None:
        return fail("unknown code")
    if rec["used"]:                                   # 重複兌換：撤銷這個 code 換出的所有 token
        for t in rec["issued"]:
            TOKENS[t]["active"] = False
        return fail("code reused; tokens revoked")
    rec["used"] = True                                # 不論成敗，兌換過一次就作廢
    if rec["client_id"] != cid:
        return fail("code was issued to another client")
    if CLOCK["now"] >= rec["exp"]:
        return fail("code expired")
    if q.get("redirect_uri") != rec["redirect_uri"]:
        return fail("redirect_uri mismatch")
    if not hmac.compare_digest(s256(q.get("code_verifier", "")), rec["challenge"]):
        return fail("PKCE verification failed")
    access = secrets.token_urlsafe(32)
    TOKENS[access] = dict(active=True, scope=rec["scope"], client_id=cid, sub=rec["sub"],
                          aud=API, exp=CLOCK["now"] + 600)
    rec["issued"].append(access)
    return 200, JSON, {"access_token": access, "token_type": "Bearer", "expires_in": 600, "scope": rec["scope"]}


def introspect(h, q):
    if client_auth(h) != "api":                       # 只有 resource server 能查
        return 401, JSON, {"error": "invalid_client"}
    rec = TOKENS.get(q.get("token", ""))
    if not rec or not rec["active"] or CLOCK["now"] >= rec["exp"]:
        return 200, JSON, {"active": False}
    return 200, JSON, {"active": True, **{k: rec[k] for k in ("scope", "client_id", "sub", "aud", "exp")}}


# ───────── Resource server（api.shengsheng.example 的縮小版）─────────
def guard(h, needed):
    auth = h.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return (401, {"WWW-Authenticate": 'Bearer realm="api"'}, {"error": "no token"}), None
    _, _, info = call("POST", AS + "/introspect", {"token": auth[7:]}, basic("api", "api-secret"))
    if not info.get("active") or info.get("aud") != API:
        return (401, {"WWW-Authenticate": 'Bearer error="invalid_token"'}, {"error": "invalid_token"}), None
    if needed not in info["scope"].split():
        hdr = f'Bearer error="insufficient_scope", scope="{needed}"'
        return (403, {"WWW-Authenticate": hdr}, {"error": "insufficient_scope"}), None
    return None, info


def vocab(h, q):
    denied, info = guard(h, "vocab:read")
    return denied or (200, JSON, {"sub": info["sub"], "words": ["こんにちは", "ありがとう"]})


def progress(h, q):
    denied, info = guard(h, "vocab:write")
    return denied or (200, JSON, {"saved": True})


# ───────── Client：詞卡島的 web 後端（confidential client）─────────
def login(h, q):
    sid, state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(16), secrets.token_urlsafe(48)
    SESSIONS[sid] = {"state": state, "verifier": verifier}           # 都留在 server 端
    params = dict(response_type="code", client_id="cards", redirect_uri=CB, scope="vocab:read",
                  state=state, code_challenge=s256(verifier), code_challenge_method="S256")
    return 302, {"Location": AS + "/authorize?" + urlencode(params),
                 "Set-Cookie": f"sid={sid}; HttpOnly; SameSite=Lax; Path=/"}, None


def callback(h, q):
    sid = (h.headers.get("Cookie") or "").removeprefix("sid=")
    sess = SESSIONS.get(sid)
    expected = sess.pop("state", None) if sess else None              # state 只能用一次
    if not expected or not hmac.compare_digest(q.get("state", ""), expected):
        return 400, JSON, {"error": "state mismatch：不是這個瀏覽器發起的登入"}
    if q.get("iss") != AS:
        return 400, JSON, {"error": "iss mismatch"}
    if "error" in q:
        return 400, JSON, {"error": q["error"]}
    st, _, tok = call("POST", AS + "/token", {"grant_type": "authorization_code", "code": q["code"],
                      "redirect_uri": CB, "code_verifier": sess["verifier"]}, basic("cards", "cards-secret"))
    if st != 200:
        return 502, JSON, tok
    st, _, data = call("GET", API + "/vocab", headers={"Authorization": "Bearer " + tok["access_token"]})
    return 200, JSON, {"scope": tok["scope"], "api_status": st, "vocab": data}


as_srv, AS = serve({("GET", "/authorize"): authorize, ("POST", "/token"): token,
                    ("POST", "/introspect"): introspect})
api_srv, API = serve({("GET", "/vocab"): vocab, ("POST", "/progress"): progress})
cl_srv, CL = serve({("GET", "/login"): login, ("GET", "/callback"): callback})
CB = CL + "/callback"
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
CLIENTS["cards"] = {"secret_sha256": sha("cards-secret"), "redirect_uris": {CB}, "scopes": {"vocab:read", "vocab:write"}}
CLIENTS["api"] = {"secret_sha256": sha("api-secret"), "redirect_uris": set(), "scopes": set()}
name = {AS: "AS", API: "API", CL: "client"}

# ── 1. 正常流程：瀏覽器跟著 302 在三個角色之間跑 ──
url, cookie = CL + "/login", ""
for _ in range(4):
    st, hdrs, body = call("GET", url, headers={"Cookie": cookie} if url.startswith(CL) else {})
    u = urlsplit(url)
    keys = ",".join(parse_qs(u.query)) or "-"
    print(f"瀏覽器 GET {name[f'{u.scheme}://{u.netloc}']:6} {u.path:10} 參數[{keys}] → {st}")
    cookie = hdrs.get("Set-Cookie", "").split(";")[0] or cookie
    if st != 302:
        break
    url = hdrs["Location"]
print(f"  結果：scope={body['scope']}，API {body['api_status']}，words={body['vocab']['words']}")
assert st == 200 and body["api_status"] == 200


# ── 2. 逐一示範每道檢查擋下的情境 ──
def get_code(**override):
    verifier = secrets.token_urlsafe(48)
    p = dict(response_type="code", client_id="cards", redirect_uri=CB, scope="vocab:read",
             state="s1", code_challenge=s256(verifier), code_challenge_method="S256")
    p.update(override)
    st, hdrs, body = call("GET", AS + "/authorize?" + urlencode(p))
    back = {k: v[0] for k, v in parse_qs(urlsplit(hdrs.get("Location", "")).query).items()}
    return st, back, body, verifier


def exchange(code, verifier, redirect=None, secret="cards-secret"):
    return call("POST", AS + "/token", {"grant_type": "authorization_code", "code": code,
                "redirect_uri": redirect or CB, "code_verifier": verifier}, basic("cards", secret))


def report(label, got):
    width = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in label)
    print(f"  {label}{' ' * (32 - width)}→ {got}")


print("被擋下的情境：")
st, _, body, _ = get_code(redirect_uri=CB + ".evil.example")
report("A redirect_uri 多了尾巴", f"{st} {body['error']}（停在 AS）")
st, _, body, _ = get_code(redirect_uri=CB.replace("127.0.0.1", "localhost"))
report("B redirect_uri 換成 localhost", f"{st} {body['error']}（停在 AS）")
st, back, _, _ = get_code(code_challenge="", code_challenge_method="")
report("C 沒帶 PKCE", f"{st} 導回 error={back['error']}")
st, back, _, _ = get_code(code_challenge_method="plain")
report("D PKCE method=plain", f"{st} 導回 error={back['error']}")
st, back, _, _ = get_code(scope="vocab:read admin")
report("E 要求未登記的 scope", f"{st} 導回 error={back['error']}")

st, hdrs, _ = call("GET", CL + "/login")                      # 受害者的瀏覽器開始登入
_, back, _, _ = get_code()                                     # 另一個 code 被塞進回呼網址
st, _, body = call("GET", f"{CB}?code={back['code']}&state=forged&iss={AS}",
                   headers={"Cookie": hdrs["Set-Cookie"].split(";")[0]})
report("F callback 的 state 不符", f"{st}（client 拒絕，不去換 token）")

_, back, _, verifier = get_code()
st, _, body = exchange(back["code"], secrets.token_urlsafe(48))
report("G 攔到 code、沒有 verifier", f"{st} {body['error']}：{body['error_description']}")
_, back, _, verifier = get_code()
st, _, body = exchange(back["code"], verifier, redirect=CL + "/other")
report("H 換 token 時 redirect_uri 不同", f"{st} {body['error']}：{body['error_description']}")
_, back, _, verifier = get_code()
CLOCK["now"] += 61
st, _, body = exchange(back["code"], verifier)
report("I code 超過 60 秒才兌換", f"{st} {body['error']}：{body['error_description']}")
_, back, _, verifier = get_code()
st, _, body = exchange(back["code"], verifier, secret="guess")
report("J client secret 錯誤", f"{st} {body['error']}")

_, back, _, verifier = get_code()
st, _, tok = exchange(back["code"], verifier)
bearer = {"Authorization": "Bearer " + tok["access_token"]}
st_ok, _, _ = call("GET", API + "/vocab", headers=bearer)
st, hdrs, _ = call("POST", API + "/progress", {}, bearer)
report("K vocab:read 的 token 去寫入", f"{st} {hdrs['WWW-Authenticate']}")
st, _, _ = call("GET", API + "/vocab")
report("L 沒帶 token", f"{st}")
st, _, body = exchange(back["code"], verifier)                 # 同一個 code 再兌換一次
st_after, hdrs, _ = call("GET", API + "/vocab", headers=bearer)
report("M 同一個 code 兌換第二次", f"{st} {body['error_description']}")
report("  └ 先前換到的 token", f"兌換前 {st_ok}，現在 {st_after} {hdrs['WWW-Authenticate']}")
assert st_ok == 200 and st_after == 401

for srv in (as_srv, api_srv, cl_srv):
    srv.shutdown()
    srv.server_close()
```

```text
瀏覽器 GET client /login     參數[-] → 302
瀏覽器 GET AS     /authorize 參數[response_type,client_id,redirect_uri,scope,state,code_challenge,code_challenge_method] → 302
瀏覽器 GET client /callback  參數[code,state,iss] → 200
  結果：scope=vocab:read，API 200，words=['こんにちは', 'ありがとう']
被擋下的情境：
  A redirect_uri 多了尾巴         → 400 invalid_request（停在 AS）
  B redirect_uri 換成 localhost   → 400 invalid_request（停在 AS）
  C 沒帶 PKCE                     → 302 導回 error=invalid_request
  D PKCE method=plain             → 302 導回 error=invalid_request
  E 要求未登記的 scope            → 302 導回 error=invalid_scope
  F callback 的 state 不符        → 400（client 拒絕，不去換 token）
  G 攔到 code、沒有 verifier      → 400 invalid_grant：PKCE verification failed
  H 換 token 時 redirect_uri 不同 → 400 invalid_grant：redirect_uri mismatch
  I code 超過 60 秒才兌換         → 400 invalid_grant：code expired
  J client secret 錯誤            → 401 invalid_client
  K vocab:read 的 token 去寫入    → 403 Bearer error="insufficient_scope", scope="vocab:write"
  L 沒帶 token                    → 401
  M 同一個 code 兌換第二次        → 400 code reused; tokens revoked
    └ 先前換到的 token            → 兌換前 200，現在 401 Bearer error="invalid_token"
```

前四行是正常流程：瀏覽器打開詞卡島的 `/login`，拿到 302 與 session cookie；跳到 AS 的 `/authorize`，帶著授權請求的七個參數；再帶著 `code`、`state`、`iss` 回到 callback，client 在 back channel 換到 token 並呼叫 API，拿到美咲老師標記的兩個生字。模擬的瀏覽器從頭到尾沒看到 access token。

A 到 E 是 authorization endpoint 的檢查。A 在登記的 redirect URI 後面多了一段，B 把 `127.0.0.1` 換成意義相同的 `localhost`，精確比對都不放過，而且 AS 回 400 停在自己的頁面，不導回這個沒驗證過的網址。C、D、E 的 redirect URI 是正確的，所以 AS 用 302 把錯誤帶回 client：沒帶 PKCE、用 `plain`、要求 client 沒登記的 `admin` scope，都在發出 code 之前就被拒絕。

F 是 client 端的 state 檢查：受害者的瀏覽器剛發起登入，攻擊者塞進一個不是這次流程產生的 code 與偽造的 state，client 在 callback 直接回 400，連 token endpoint 都不去。G 到 J 是 token endpoint 的檢查：G 是攔到 code 卻沒有 verifier 的攻擊者（假設對方也握有 secret，或 client 本來就是沒有 secret 的 public client）；H 是 redirect_uri 和授權請求不同；I 是 code 過期；J 是 secret 錯誤，回 401 `invalid_client`。

K、L 是 resource server 的檢查：只有 `vocab:read` 的 token 去呼叫寫入 API，得到 403 與 `insufficient_scope`，`WWW-Authenticate` 還告訴 client 缺的是 `vocab:write`；沒帶 token 則是 401。最後的 M 最值得細看：同一個 code 被兌換第二次時，AS 不只拒絕，還撤銷了第一次換出的 token，於是原本能用的 token（兌換前 200）立刻變成 401 `invalid_token`。這就是 28.5 節「code 被兌換兩次代表已經外洩」的規則，也只有 opaque token 加 introspection 能讓撤銷這麼即時；若 RS 用 JWT 自行驗證，撤銷要等到 token 過期。

程式裡還有幾個刻意的細節。第一，token endpoint 在檢查之前就把 code 標成已使用，任何一次兌換嘗試（包括失敗的）都會讓它作廢，攻擊者不能拿同一個 code 反覆猜 verifier。第二，比對 secret、state、challenge 都用 `hmac.compare_digest`，避免逐字元比較洩漏時間差。第三，client 的 state 用 `pop` 取出，比對過就消失。第四，RS 除了 `active` 還檢查 `aud`，避免拿發給別的 API 的 token 來呼叫。

## 28.16 在工作上怎麼用

小晴修完草稿後，Rita 把審查重點整理成聲聲 Live 的 OAuth 檢查清單，依角色分工。

**後端工程師（串接第三方 OAuth 的 client 端）**：用成熟的函式庫，不要自己拼 URL；但要能逐項確認它有做到這些事。一律用 authorization code＋PKCE（S256）；state 綁 server 端 session、比對後刪除；回呼時檢查 `iss`；redirect URI 在 AS 登記完整網址，正式環境只用 HTTPS；token 存在 server 端，不放進前端、不寫進 log；讀 token 回應裡的 `scope` 與 `expires_in`；收到 401 `invalid_token` 才 refresh，收到 403 `insufficient_scope` 則請使用者授權。

**後端工程師（維運 AS 與 RS）**：redirect URI 精確比對，不符時不導回；授權碼 60 秒內有效、一次性、重複兌換時撤銷衍生 token；token endpoint 回 `Cache-Control: no-store`；client secret 只存 hash，提供輪替機制（新舊並存一段時間）；RS 驗 token 時檢查有效性、audience 與 scope，三者缺一不可；access token 短效，public client 的 refresh token 輪替並偵測重複使用。

**SRE**：OAuth 的故障多半表現成「登入失敗」或「突然全部 401」，要能快速定位。

```bash
# 看 AS 的 metadata（RFC 8414）：支援哪些 grant、PKCE method、endpoint 在哪
curl -s https://auth.shengsheng.example/.well-known/oauth-authorization-server | python3 -m json.tool

# 從 AS 的結構化 log 統計 token endpoint 的錯誤分布（error 在回應 body，nginx 的 access log 看不到）
grep '"path":"/token"' auth.log | grep -o '"error":"[a-z_]*"' | sort | uniq -c

# 驗證 RS 對 scope 不足的回應：應是 403 加 WWW-Authenticate，而不是 401
curl -si -H "Authorization: Bearer $TOKEN" -X POST https://api.shengsheng.example/progress | grep -i -E '^HTTP|www-authenticate'
```

其中 token endpoint 的錯誤分布最有診斷價值：`invalid_grant` 突增通常是 client 重試導致 code 重複兌換、或 refresh token 輪替後回應遺失；`invalid_client` 突增通常是 secret 輪替沒同步；時鐘不同步則會讓 JWT 類的 token 與 DPoP proof 被判定過期，記得檢查 NTP。

判斷 OAuth 問題時，先問「錯誤發生在哪一段」：

```text
 使用者說「登入詞卡島失敗」
   │
   ├─ 停在 AS 的錯誤頁、沒有跳回 client
   │     └─► redirect_uri 或 client_id 不符（看 AS log 的比對失敗紀錄，常見：結尾斜線、http/https、port）
   │
   ├─ 跳回 client，URL 帶 error=…
   │     ├─ access_denied ─► 使用者按了取消，正常
   │     ├─ invalid_scope ─► client 要了沒登記的 scope
   │     └─ invalid_request ─► 缺 PKCE、method 不是 S256、參數重複
   │
   ├─ 跳回 client，client 回 400「state mismatch」
   │     └─► session cookie 沒帶回來（SameSite、cookie 網域、多台 server 的 session 不共用）、使用者開了兩個分頁
   │
   └─ client 換 token 失敗
         ├─ invalid_client ─► secret 錯、client 驗證方式不符
         └─ invalid_grant ─► code 過期、已用過、redirect_uri 不同、verifier 不符（常見：base64 用錯）
```

這張圖把 28.5 節的十二個步驟切成四段，每一段的錯誤來源幾乎不重疊。最常被誤判的是 state mismatch：多半不是攻擊，而是 cookie 在回呼時沒被帶回來，例如 session cookie 設了 `SameSite=Strict`，從 AS 跳回時是跨站導覽，瀏覽器不送 Strict cookie；改成 `Lax` 就能在頂層 GET 導覽時送出（第 23 章）。

**前端工程師**：SPA 優先採用 BFF；若必須當 public client，token 只放記憶體、refresh token 輪替或用 DPoP，並做好 CSP。

**資安工程師**：Rita 審查新 client 時檢查 redirect URI 是否都是完整網址、所屬網域有沒有 open redirect、scope 是否最小、同意畫面的名稱是否經過審核，並定期撤銷長期未使用的授權。

## 28.17 常見錯誤與除錯

下表整理聲聲 Live 開放平台上線前後遇到、以及業界最常見的 OAuth 錯誤。每一列都能用本章的程式或工具重現與確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| AS 顯示「redirect_uri 不符」，但看起來一模一樣 | 結尾斜線、大小寫、http 與 https、port、多一個 query 參數 | 把請求的值與登記值逐字元比對（印出 `repr`） | 登記與請求使用完全相同的字串；不要為此放寬成前綴比對 |
| 換 token 回 `invalid_grant`，偶發 | 網路重試讓同一個 code 被兌換兩次；或 code 在使用者停在同意頁太久後過期 | AS log 看同一個 code 出現兩次兌換；比對發碼與兌換的時間差 | token 請求不要自動重試；過期就重新發起授權 |
| PKCE 一直驗證失敗 | 用了標準 base64（`+/=`）而不是 base64url；對 verifier 的 base64 解碼結果而不是 ASCII 字串做雜湊；session 裡存的 verifier 被覆蓋 | 用 RFC 7636 的範例值測試自己的實作 | 依 28.8 節的程式修正；一次授權一組 verifier，用 state 當索引 |
| callback 經常 state mismatch | session cookie 沒帶回來（`SameSite=Strict`、網域不符、多台 server 不共用 session） | DevTools 看回呼請求有沒有帶 cookie | session cookie 用 `SameSite=Lax`；session 集中存放 |
| 呼叫 API 一直 401，refresh 也沒用 | RS 檢查的 audience 與 token 不符；或 token 其實是 403 的情況被回成 401 | 用 introspection 看 token 的 `aud` 與 `scope`；看 `WWW-Authenticate` | 授權時用 resource indicators 指定 audience；RS 正確區分 401 與 403 |
| 手機 App 的使用者頻繁被登出 | refresh token 輪替後回應遺失，App 用舊 token 重試觸發重複使用偵測 | AS log 看「重複使用」事件集中在行動網路 | 設定數秒的寬限期；App 端序列化 refresh 請求，避免並發 |
| access token 出現在 log 或分析工具 | 用了 `?access_token=` 或 implicit 流程；log 記錄了完整 header | 搜尋 log 中的 token 前綴 | 改用 header 傳 token；log 遮蔽 `Authorization`；撤銷已外洩的 token |
| 第三方 App 拿到了不該有的權限 | scope 過粗（例如 `all`）、第一方與第三方共用 client 登記 | 檢查 client 登記的允許 scope | 拆細 scope；第三方 client 只允許對外 scope；同意畫面列出每一項 |
| 內部服務用 client credentials 讀到使用者私人資料 | RS 以「呼叫方是內部服務」為由放行 | 稽核 token 的 `sub` 與 `client_id` | RS 對使用者資料要求使用者授權；需要代理時用 token exchange 縮小範圍 |

除錯 OAuth 的通則是：**先確認是哪一段、哪一個角色拒絕了請求，再看 error 欄位**。每個錯誤碼都對應一道明確的檢查，動手做的 A 到 M 就是這些檢查各自擋下的場景。

## 28.18 動手練習

1. **延伸動手做：加上 refresh token**。在 28.15 節的 AS 加上 `grant_type=refresh_token`：token 回應附上 refresh token，兌換時輪替，並把 28.10 節的家族偵測整合進去。再加一個情境：攻擊者用舊的 refresh token 兌換後，正牌 client 的 access token 是否也該失效？
   答案要點：輪替時要記錄每張 refresh token 屬於哪個家族、由哪個授權碼衍生；偵測到重複使用時撤銷整個家族，並撤銷該家族發出的 access token（opaque token 可以立即生效）。refresh 時也要驗證 client 身分，且只允許縮小 scope。

2. **用 DevTools 觀察真實的授權請求**（真實工具）。找一個支援「用某平台帳號登入」的網站，打開 DevTools 的 Network 面板並勾選 Preserve log，走一次登入流程，找出授權請求與回呼。
   答案要點：在 authorization endpoint 的請求上找到 `response_type=code`、`client_id`、`redirect_uri`、`state`，多半還有 `code_challenge` 與 `code_challenge_method=S256`（以及 OIDC 的 `nonce`）；回呼的 URL 帶著 `code` 與相同的 `state`。token endpoint 的請求通常看不到，因為它由網站後端在 back channel 發出；如果在瀏覽器裡看得到，代表這是 public client 或 BFF 以外的架構。

3. **手算 PKCE**。不看程式，用命令列計算 RFC 7636 範例 verifier 的 challenge：`printf %s 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk' | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '='`，並解釋每一段管線做什麼。
   答案要點：輸出應為 `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`。`printf %s` 避免多一個換行（用 `echo` 會讓雜湊完全不同，這是常見 bug）；`-binary` 輸出原始 32 bytes；`tr` 把標準 base64 轉成 base64url 並去掉 padding。

4. **讓 redirect URI 比對「看起來友善」會怎樣**。把 28.15 節 AS 的 `redirect not in client["redirect_uris"]` 改成 `not any(redirect.startswith(u) for u in ...)`，重新執行，看情境 A 的結果；再思考有沒有任何「安全的放寬方式」。
   答案要點：情境 A 會被放行並拿到 code，code 被送到一個不同的網址。唯一被規格允許的放寬是原生 App 的 loopback redirect 可以換 port；其他需求（例如多個環境）應該登記多個完整的 redirect URI。

5. **設計聲聲 Live 的 scope 與 grant**。聲聲 Live 要再開放兩個整合：一個家長 App 能看孩子的課表與出席紀錄；一個排課機器人（沒有使用者介面）每小時讀取所有老師的空堂。分別設計 client 類型、grant、scope 與 token 有效期。
   答案要點：家長 App 是 public client，用 authorization code＋PKCE，scope 如 `schedule:read attendance:read`，access token 短效、refresh token 輪替或 DPoP；排課機器人是 confidential client，用 client credentials，scope 如 `availability:read`，token 快取到接近過期，不發 refresh token，且 RS 不允許它讀學生的私人資料。

6. **觀察 SameSite 對 state 的影響**。在 28.15 節的 client 把 cookie 改成 `SameSite=Strict`，思考真實瀏覽器從 AS 的網域跳回 client 時，會不會送出這個 cookie，對 state 檢查有什麼影響。
   答案要點：從 AS 跳回 client 是跨站的頂層導覽，`Strict` 的 cookie 不會被送出，client 找不到 session，所有登入都會 state mismatch；`Lax` 允許頂層 GET 導覽帶 cookie，是 OAuth callback 的正確選擇。模擬瀏覽器不實作 SameSite，所以要用真實瀏覽器驗證。

## 本章重點整理

- OAuth 解決委派授權：使用者在 AS 上驗證並同意，client 拿到一張範圍與時間都有限、可單獨撤銷的 access token，永遠不接觸使用者的密碼。
- OAuth 不是登入協定；access token 是給 API 的通行證，client 想知道使用者是誰要用 OpenID Connect 的 ID token。
- 四個角色是 resource owner、client、authorization server、resource server；front channel 經過瀏覽器、可被看見與竄改，back channel 是 client 與 AS 的直連，token 只走 back channel。
- confidential client 能保管秘密並在 token endpoint 驗證身分；public client（手機 App、SPA）不能，必須靠 PKCE、refresh token 輪替或 DPoP。
- authorization code 流程中，AS 發出短效、一次性的 code，client 在 back channel 搭配 redirect_uri、code_verifier 與 client 驗證兌換；重複兌換時 AS 應撤銷已發出的 token。
- state 把回呼綁回發起授權的 session，擋下把攻擊者帳號塞給受害者的 CSRF；比對後要立刻刪除。
- redirect URI 必須精確字串比對，只有原生 App 的 loopback redirect 可以換 port；不符時 AS 不能導回，只能顯示錯誤。
- PKCE 讓 client 以 `code_challenge = BASE64URL(SHA256(code_verifier))` 證明「兌換 code 的就是發起請求的人」，只該用 S256；OAuth 2.1 要求所有 client 都使用。
- RS 驗 token 要檢查有效性、audience 與 scope；scope 不足回 403 `insufficient_scope`，token 無效才回 401 `invalid_token`。
- scope 以使用者能理解的動作為單位、讀寫分開、需要時才要求；同意畫面的 client 名稱來自登記資料。
- access token 要短效，refresh token 只送 token endpoint；輪替配合家族撤銷能偵測 refresh token 被複製，但要處理回應遺失造成的誤判。
- client credentials 用於沒有使用者的 service 之間，沒有 front channel 與 refresh token；拿到的 token 代表 service 本身，不能用來讀使用者的私人資料。
- 原生 App 要用系統瀏覽器做授權，SPA 優先採用 BFF 讓 token 留在後端；智慧電視等裝置用 device authorization grant。
- OAuth 2.1 截至 2026 年 10 月仍是草案，內容是把 PKCE、精確比對等最佳實務合併進規格，並移除 implicit、password grant 與 URL 中的 bearer token。
- DPoP 把 token 綁定在 client 的私鑰上，每個請求附上 htm、htu、iat、jti、ath 的簽章 proof，讓偷到的 token 與 proof 都無法被重用。

## 延伸問答

> [!question]- Q1. 為什麼 authorization code 流程要「先發 code，再換 token」，而不是 AS 直接在 redirect 時把 token 給 client？
> 因為 redirect 走的是 front channel：AS 回應 302，瀏覽器帶著參數跳到 client，這段路上的資料會進入瀏覽器歷史、可能被代理或 log 記錄、可能被手機上的其他 App 攔截，而且 AS 無法確認最後收到的是誰。直接把 token 放在這裡，就是已被 OAuth 2.1 移除的 implicit grant。
>
> 先發 code 的設計，讓 front channel 上只出現一個「本身不能呼叫 API、短效、只能用一次」的值；真正的 token 在 back channel 上交付，AS 在那裡可以驗證 client 的身分（confidential client 的 secret 或私鑰）與 PKCE 的 verifier，回應也只會到 client 手上。換句話說，code 把「把使用者帶回來」和「交付憑證」拆成兩件事，讓值錢的東西只走安全的路。

> [!question]- Q2. 詞卡島是 confidential client，有 client secret。為什麼 Rita 還是要求它使用 PKCE？
> client secret 證明的是「現在來兌換 code 的程式是詞卡島」，但它無法證明「這個 code 屬於詞卡島這次為這位使用者發起的流程」。攻擊者可以先用自己的帳號取得一個合法的 code，再把它注入到受害者瀏覽器對詞卡島 callback 的請求中；詞卡島會用自己的 secret 替這個 code 兌換，結果受害者的詞卡島帳號被綁到攻擊者的聲聲 Live 帳號，這叫 authorization code injection。
>
> PKCE 的 verifier 存在受害者這次的 session 裡，而攻擊者注入的 code 是用攻擊者自己的 challenge 換到的，兩者對不上，AS 會拒絕兌換。另外，PKCE 也能在 code 外洩時多一道保護：即使攻擊者同時取得了 secret，沒有 verifier 一樣無法兌換。這就是 RFC 9700 建議 confidential client 也使用 PKCE、OAuth 2.1 進一步把它列為原則上必要的原因。

> [!question]- Q3. 你在 AS 的 log 看到某個 client 的 `invalid_grant` 在下午兩點突然從每分鐘 2 次升到 400 次，錯誤描述大多是「code already used」。可能是什麼？怎麼確認？
> 「code already used」代表同一個 code 被兌換了第二次。大規模、突然發生時，最常見的原因不是攻擊，而是 client 端的重試：例如 client 剛部署了新版 HTTP 函式庫或加了一層會自動重試的 proxy，第一次兌換其實成功了，但回應因為逾時沒被讀到，重試時就變成重複兌換，而且依規則 AS 還會撤銷第一次換到的 token，使用者看到的就是登入失敗。另一個可能是使用者在 callback 頁面重新整理，或前端重複送出同一個 callback。
>
> 確認方法是在 AS log 中找同一個 code 的兩次兌換，比對時間差、來源 IP 與 User-Agent：時間差在數百毫秒到數秒、來源是 client 自己的伺服器，就是重試；來源不同的 IP，才需要當成 code 外洩處理。修正方向是 token 請求不要自動重試，失敗就重新發起授權；同時確認那個時間點 client 端有沒有部署或網路異常。

> [!question]- Q4. 手算：client 的 code_verifier 是 `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk`，但它的實作把 SHA-256 的結果用標準 base64 編碼並保留 padding。送出的 challenge 會長什麼樣？AS 會怎麼回應？
> SHA-256 的結果是 32 bytes。base64 每 3 bytes 編成 4 個字元，32 bytes 是 10 組完整的 3 bytes 加上剩下的 2 bytes，剩下的 2 bytes 編成 3 個字元再補一個 `=`，總共 44 個字元。base64url 與標準 base64 的差別只在兩個字元：標準版的 `+` 與 `/` 在 base64url 中換成 `-` 與 `_`，並去掉 `=`。正確的 challenge 是 `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`，裡面有一個 `-`，所以標準 base64 的結果是 `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw+cM=`：同一個位置變成 `+`，結尾多了 `=`。
>
> AS 收到 44 個字元、含 `+` 與 `=` 的 challenge，嚴格的實作會在授權請求就以 `invalid_request` 拒絕，因為長度與字元都不符合規格；寬鬆的實作會先發 code，到 token endpoint 重算 base64url 時得到不同的字串，回 `invalid_grant`。更麻煩的是 `+` 放在 URL query 裡還可能被解讀成空白。如果實作只去掉了 `=`、卻忘了把 `+/` 換成 `-_`，bug 會變成時有時無：雜湊剛好不含這兩個字元時一切正常，含有時才失敗（43 個字元裡出現至少一個 `+` 或 `/` 的機率約 74%），很難從錯誤訊息看出原因。最好的預防是用 RFC 7636 的範例值寫單元測試。

> [!question]- Q5. 面試題：access token 與 refresh token 為什麼要分開？如果把 access token 的有效期設成 30 天，可以不要 refresh token 嗎？
> 兩者的曝光面不同。access token 要送到每一個 resource server，經過 API gateway、內部服務、log 與監控系統，被看到或外洩的機會多；refresh token 只在 client 與 AS 的 token endpoint 之間傳遞，confidential client 使用時還要驗證 client 身分，public client 則可以輪替或綁定金鑰。把權限拆成「短效、廣泛出示」與「長效、只出示給 AS」，就能同時兼顧安全與使用者不用頻繁登入。
>
> 30 天的 access token 意味著外洩後可以被使用 30 天；如果 RS 用 JWT 自行驗證，連撤銷都很難即時生效。refresh token 讓 AS 在每次換發時都有機會重新檢查：使用者是否已取消授權、帳號是否被停用、client 是否被封鎖、refresh token 是否被重複使用。所以短效 access token 加 refresh token，等於把撤銷的生效時間壓到 access token 的有效期以內。

> [!question]- Q6. 設計取捨：聲聲 Live 的老師後台是 SPA。團隊在「SPA 直接當 public client，token 放記憶體」與「BFF」之間猶豫，你怎麼建議？
> 關鍵問題是 XSS 發生時能損失多少。SPA 當 public client 時，即使 token 只放在 JavaScript 記憶體，XSS 的 script 仍能攔截 token 或自己發起一次授權流程拿到新的，並把 token 送到攻擊者的伺服器長期使用；refresh token 輪替與 DPoP 能縮小損害，但 DPoP 的私鑰若在同一個頁面環境中可用，XSS 期間也能被拿來簽 proof。BFF 讓 token 只存在後端，XSS 的 script 只能在使用者開著頁面時透過 BFF 送請求，無法把憑證帶走。
>
> 老師後台能看到學生的聯絡資料與上課紀錄，屬於敏感資料，RFC 10017 對這類應用的首選就是 BFF。代價是多一個後端要維運、要處理 session 與 CSRF（cookie 用 `HttpOnly`、`Secure`、`SameSite`，搭配 CSRF token），以及 API 請求多經過一跳。如果是低風險、只讀公開資料的小工具，public client 加短效 token 與 CSP 也可以接受；決策要依資料敏感度，而不是依開發方便。

> [!question]- Q7. 看 log 找原因：詞卡島回報「每天都有幾位使用者在 callback 看到 state mismatch」。你在 log 中看到這些請求都沒有帶 session cookie，而且多數來自 iOS。可能是什麼？
> 沒有帶 session cookie，代表 client 在 callback 找不到發起授權時的 session，自然無法比對 state；這不是攻擊，而是 cookie 沒有活過整個流程。常見原因有三個：session cookie 設了 `SameSite=Strict`，而從 AS 跳回 client 是跨站導覽，瀏覽器不送 Strict cookie；使用者在 App 內建瀏覽器開始流程，卻在系統瀏覽器完成（或反過來），兩者的 cookie 儲存是分開的；使用者在 AS 的頁面停留太久，session 已經過期。
>
> 多數來自 iOS，指向第二個原因的可能性較高：例如使用者從某個社群 App 的內建瀏覽器點進詞卡島，AS 的登入步驟觸發了 passkey 或跳轉到系統瀏覽器，回呼就落在另一個 cookie 儲存裡。確認方法是比對發起與回呼的 User-Agent。修正方向是 session cookie 用 `SameSite=Lax`、延長授權流程期間的 session 有效時間，並在 state mismatch 時給使用者「重新開始登入」的按鈕，而不是只顯示錯誤。

> [!question]- Q8. Rita 說「DPoP 不能取代 XSS 防禦」，但又說「public client 最好用 DPoP」。這兩句話矛盾嗎？
> 不矛盾，因為它們防的是不同的事。DPoP 讓 token 綁定在 client 的私鑰上：token 從 log、網路側錄、或某個中間服務外洩時，拿到的人沒有私鑰，簽不出相符的 proof，token 就沒用；proof 本身又被 htm、htu、iat、jti、ath 限制在單一請求與短時間內，重放也無效。這大幅降低了「token 離開 client 之後」的風險，對沒有 client 驗證的 public client 尤其重要。
>
> XSS 則是攻擊者的程式碼已經在 client 裡面執行。這時攻擊者不需要把私鑰帶走（瀏覽器可以把金鑰設成不可匯出），只要在頁面還開著的期間呼叫簽章功能，就能簽出完全合法的 proof 並發送請求。所以 DPoP 縮小的是外洩的後果與時間窗，而 XSS 的根本防禦仍然是輸出編碼、CSP 與減少第三方 script。兩者是不同層次的防線，應該一起使用。

## 延伸閱讀

- RFC 6749〈The OAuth 2.0 Authorization Framework〉：OAuth 2.0 的主規格，角色、grant 與 endpoint 的定義
- RFC 6750〈The OAuth 2.0 Authorization Framework: Bearer Token Usage〉：Bearer token 的出示方式與 `WWW-Authenticate` 錯誤碼
- RFC 7636〈Proof Key for Code Exchange by OAuth Public Clients〉：PKCE，附錄有本章使用的範例值
- RFC 9700〈OAuth 2.0 Security Best Current Practice〉：redirect URI 比對、PKCE、refresh token 保護等安全要求的整理
- draft-ietf-oauth-v2-1〈The OAuth 2.1 Authorization Framework〉：截至 2026 年 10 月為 draft-16
- RFC 8252〈OAuth 2.0 for Native Apps〉與 RFC 10017〈OAuth 2.0 for Browser-Based Applications〉：手機 App 與 SPA 的實作指引
- RFC 9449〈OAuth 2.0 Demonstrating Proof of Possession (DPoP)〉：DPoP proof 的格式與驗證規則
- Aaron Parecki《OAuth 2.0 Simplified》：以實作者角度解說各種 grant 的入門書
