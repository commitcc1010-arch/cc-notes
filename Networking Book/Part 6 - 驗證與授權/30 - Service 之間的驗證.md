---
chapter: 30
title: Service 之間的驗證與簽章
part: 6
---

# 第 30 章　Service 之間的驗證與簽章

> [!abstract] 本章地圖
> **核心問題**：呼叫你的不是人，而是另一個程式時，要怎麼確認「是誰在呼叫、內容沒被改過、不是舊訊息重送」？
>
> **你會學到**：
> - 設計一套 API key：可辨識的前綴、只存雜湊、權限範圍、雙 key 並行的輪替流程，以及外洩時的處理
> - 說清楚 HMAC 請求簽章的 canonical request、timestamp、nonce 各自防什麼，並用 constant-time 比較驗證簽章
> - 把第 17 章的 webhook 驗證帶上 production：分辨「重放攻擊」與「正常重試」，用資料庫唯一約束做跨 worker 的冪等處理，並避開 raw body 被框架改寫的陷阱
> - 比較 mTLS、service mesh、workload identity（SPIFFE、雲端 IAM role）的取捨，知道什麼時候該從「共用秘密」升級到「工作負載身分」
> - 把 secrets 放在對的地方：secret manager、短效憑證、輪替自動化，以及 log 與錯誤頁的防漏
> - 在 127.0.0.1 上重現 WSGI middleware 改寫 body 導致簽章失敗、跨 worker 去重失效，並實作通用的 HMAC 請求簽章與 API key 模組
>
> **前置知識**：第 17 章（hash、HMAC、隨機數）、第 18 章（TLS 與 mTLS）、第 24 章（webhook、idempotency key）、第 25 章（X-Forwarded-For 與信任邊界）、第 26–28 章（密碼儲存、JWT、OAuth client credentials）

## 30.1 故事：週五晚上被多加的課堂點數

第 17 章裡，小晴在 Rita 的審查下寫出了一個正確的金流 webhook 驗證：`Pay-Signature: t=…,v1=…`、HMAC-SHA256 計算 `"{t}." + 原始 body`、300 秒時間窗、`compare_digest`、新舊 secret（k2、k1）並存、用 event id 去重。那段程式上線三個月都很平靜，直到週五晚上九點「秋季課程包」開賣。學生付款後，金流供應商 `pay.example.net` 對 `api.shengsheng.example/v1/webhooks/pay` 送出付款成功的通知，Flask 替學生加上課堂點數。

當天下午，另一位同事合併了一個看起來無害的 PR：為了統一 log 格式並遮蔽卡號末四碼，加了一個 WSGI middleware，把每個 JSON 請求先解析、刪掉敏感欄位、再重新序列化後交給後面的 view。九點零二分，告警響起：`/v1/webhooks/pay` 的回應 100% 是 401，錯誤訊息是 `signature mismatch`。學生付了錢，點數卻沒有入帳，客服頻道開始湧進截圖。

值班的同事為了止血，九點十五分推了一個 hotfix：暫時跳過簽章驗證，改成「只要 `X-Forwarded-For` 的第一個位址落在金流供應商公告的 `198.51.100.64/26` 就放行」。點數開始入帳，但累積的重試同時湧進來，handler 又在同步寄送確認信，回應時間一度超過供應商的逾時，供應商把這些「其實已經處理了」的通知也記成失敗，排進下一輪重試。九點四十分，小晴找到真正的原因、修好 middleware、恢復簽章驗證，部署時所有 gunicorn worker 重新啟動。接著第二波問題出現：有 37 位學生的點數被加了兩到三次。

```text
 21:00  開賣，webhook 正常
 21:02  middleware 上線：所有 webhook → 401 signature mismatch
        └─ 金流供應商：收到非 2xx → 依退避策略稍後重試
 21:15  hotfix：關掉簽章驗證，改看 X-Forwarded-For 第一段是否在 198.51.100.64/26
        ├─ Rita：「這個 header 誰都能寫。」
        └─ 重試湧入＋同步寄信 → 回應超過供應商逾時 → 已入帳的事件也被排進重試
 21:40  修好 middleware、恢復驗證；部署重啟 3 台主機 × 4 個 worker
        └─ 每個 worker 記在記憶體裡的 seen_events 全部清空
 21:41  重試落在「沒看過這個 event id」的 worker → 37 人重複加點
 22:30  人工對帳、回補；週一事後檢討
```

這條時間軸上有三個獨立的錯誤，週一的事後檢討裡，資安工程師 Rita 一條一條拆開。第一，middleware 改寫了 body，簽章驗證的對象從「金流供應商簽的 bytes」變成「我們自己重組的 bytes」，第 17 章提醒過的事，換了一個地方發生。第二，hotfix 用 IP 取代簽章，而且讀的是請求裡任何人都能寫的 header；就算讀對了來源位址，IP 也只是輔助，不是身分。第三，第 17 章的去重是寫在 process 記憶體裡的 `set`，示範時夠用，到了 production 卻有 12 個 worker 各記各的，重啟就全忘了；webhook 的投遞語意是「至少一次」（at-least-once），去重必須是所有 worker 共用、而且和入帳同生共死的紀錄，處理才真正是冪等（idempotent，同一件事做幾次結果都一樣）。

Rita 順便翻了一下設定檔，又找到一個問題：Flask 呼叫內部推薦服務 `reco` 用的是一把寫死在 repo 裡的 API key，五個服務共用、三年沒換過，也不知道誰還在用。阿德聽完說：「我們一直在處理『使用者是誰』，卻很少問『呼叫我的程式是誰』。」這一章就從這兩個問題出發：外部系統呼叫我們（webhook、合作夥伴 API），以及我們自己的服務彼此呼叫（API → reco、API → 物件儲存）。讀完後，你會知道每一種機制證明了什麼、沒證明什麼，以及事故中的每一個錯誤該怎麼從設計上避免。

## 30.2 Service 之間的驗證要回答什麼問題

第 26 到 29 章處理的是**人**的驗證，背後都假設有個使用者可以輸入密碼、按下同意、碰一下指紋感應器。程式之間沒有人可以互動，憑證必須事先放在程式拿得到的地方，並在凌晨三點自動運作。因此 service 的憑證是**長期存放**的、數量多（每個服務、環境、合作夥伴各一份），而且外洩時往往沒人察覺。

不論用什麼機制，service 之間的驗證都在回答三個問題。**身分**（authentication）：送請求來的是誰？例如「這是金流供應商」或「這是 `live` namespace 裡的 API 服務」。**完整性**（integrity）：內容在路上有沒有被改？例如金額從 10 點被改成 99 點。**新鮮度**（freshness）：這是剛發出的請求，還是有人把一個合法的舊請求重送一次？這叫**重放攻擊**（replay attack），例如把一筆「加 10 點」的通知錄下來，隔天再送一次。驗證之後還有**授權**（authorization）：就算確定是誰，這個身分能不能做這件事。

下面這張圖是聲聲 Live 需要處理的幾種「程式對程式」呼叫，每一條箭頭的信任邊界不同：

```text
                 公網（不可信）                    │            VPC 10.20.0.0/16（較可信，但不是零風險）
                                                   │
  pay.example.net ──① webhook（HMAC 簽章）────────►│ LB 203.0.113.80 ─► nginx ─► Flask API
  198.51.100.64/26                                 │                               │
                                                   │                               ├─③ 呼叫 reco（API key → mTLS）
  合作學校的排課系統 ──② 呼叫我們的 API（API key）─►│                               │    reco.live.svc.cluster.local
                                                   │                               │
  我們 ◄──────────────④ 我們呼叫金流 API（對方發的 secret key）──────────────────── ┤
                                                   │                               └─⑤ 寫入物件儲存（雲端 IAM role，
                                                   │                                    不放任何長期 key）
```

① 是故事的主角：外部系統主動打進來，要確認它真的是金流供應商、內容沒被改、不是重放。② 是我們發 API key 給合作學校，我們要負責格式、儲存、權限範圍與輪替。③ 是內部服務互相呼叫，故事裡用的是共用 API key，本章會說明為什麼應該升級到 mTLS 或 workload identity。④ 方向相反：金流供應商發 secret key 給我們，我們負責保管。⑤ 呼叫雲端服務時，最好不持有任何長期 key，由平台依「這個 Pod 是誰」發短效憑證。

常見的機制可以依「證明了什麼」排成一張表。本章會由上而下逐一展開：

| 機制 | 證明身分的方式 | 完整性 | 防重放 | 秘密會不會在網路上傳 | 典型用途 |
|---|---|---|---|---|---|
| 來源 IP 允許清單 | 封包從哪裡來（可被共用、被冒用） | 無 | 無 | 無秘密 | 輔助過濾，不能單獨當驗證 |
| API key（bearer） | 持有這串字 | 靠 TLS | 無 | 每個請求都送 | 合作夥伴 API、簡單的內部呼叫 |
| HMAC 請求簽章 | 持有共用 secret 才算得出簽章 | 有（簽到的部分） | timestamp＋nonce | 不送，只送簽章 | webhook、雲端 API（例如 SigV4） |
| mTLS | 持有憑證的私鑰，憑證由信任的 CA 簽發 | TLS 保護整條連線 | TLS 內建 | 私鑰不離開本機 | 內部服務、service mesh、金融 API |
| Workload identity | 平台依執行環境發短效身分（憑證或 token） | 依載體 | 短效降低風險 | 不需要長期秘密 | 雲端 IAM、SPIFFE、CI 部署 |

這張表有兩個值得先記住的觀察。第一，越往下，秘密越少在網路上出現：API key 每次都整串送出，被任何中間層的 log 記下就等於外洩；HMAC 只送簽章；mTLS 的私鑰永遠不離開本機。第二，越往下，營運成本越集中在平台：API key 只要一個資料表，mTLS 需要 CA 與憑證輪替，workload identity 需要雲端或 mesh 的基礎設施。工程上的判斷是「在這條信任邊界上，值得花多少成本換多少保證」。

> [!warning] 常見誤解
> 「在 VPC 裡就不用驗證」是很多事故的起點。內網裡任何一個服務被入侵（例如有 SSRF 漏洞），攻擊者就能以內網位置呼叫所有不驗證的服務。**zero trust**（零信任）的原則是：網路位置不代表身分，每一次呼叫都要驗證是誰、能做什麼；內網防火牆仍有用，但只是多層防禦中的一層。

## 30.3 API key：最簡單、也最容易做錯的憑證

**API key** 是一串由 server 發給 client 的隨機字串，client 每次呼叫都附上它，server 查表確認「這把 key 屬於誰、能做什麼」。例如聲聲 Live 發給新竹某所合作學校一把 key，對方的排課系統每天凌晨用它呼叫 `GET /v1/courses` 同步課表。它的語意是 **bearer**（持有者）：誰拿到這串字，誰就是它的主人，就像一張不記名的門禁卡。這個特性讓它極為簡單，也讓它的設計細節非常重要，因為所有的保護都落在「這串字不能外洩、外洩了要能立刻發現並撤銷」。

### 格式：讓人和機器都認得出來

一把設計良好的 key 不只是一串亂碼。聲聲 Live 採用的格式如下，每一段都有用途：

```text
  ssk _ live _ 767bb9ca _ 4v5mQ……（共 43 個 base62 字元）……tBNm 0Q9cV0
  └┬┘   └┬─┘   └──┬───┘   └──────────────────┬───────────────────┘ └──┬──┘
   │     │        │                          │                        └─ checksum（6 字元，緊接在 secret 後）：
   │     │        │                          │                           CRC32 編成 base62，查資料庫前就擋下打錯的 key
   │     │        │                          └─ secret（≈ 256 bit 隨機數）：真正的秘密，只在發放時出現一次
   │     │        └─ key id（8 個 hex）：公開的索引，可以寫進 log、顯示在後台
   │     └─ 環境：live／test，test key 打到 live 環境直接拒絕
   └─ 前綴：一看就知道是「聲聲 Live 的 secret key」，secret scanning 用它比對
```

**前綴**（prefix）讓這串字可以被辨識：在 log 或 Slack 看到 `ssk_live_` 就知道是正式環境的 secret，程式碼代管平台的 **secret scanning**（掃描 commit 裡是否有憑證的功能）也能精準比對，例如 GitHub 的 personal access token 以 `ghp_` 開頭。**環境標記**讓設定錯環境的 test key 在第一步就被擋下。

**key id** 是公開的部分，資料庫用它查表，log 與後台用它指稱「哪一把 key」而不寫出秘密。**secret** 用 `secrets` 模組產生（第 17 章），256 bit 的熵讓暴力猜測不可能。**checksum** 不是安全機制（CRC32 是公開演算法），用途是不查資料庫就擋掉打錯、截斷的字串，並降低 secret scanning 的誤判。

### 儲存：只存雜湊，而且不必用慢雜湊

API key 和密碼一樣，**資料庫裡只存雜湊**：備份、唯讀副本、資料倉儲經手的人與系統遠比正式環境多，任何一處外洩都不該讓攻擊者直接拿到能用的 key。明文只在發放時顯示一次，客戶弄丟了就撤銷再發新的。

但和密碼不同，API key **不需要** bcrypt、scrypt 這類刻意很慢的雜湊（第 26 章）。慢雜湊對抗的是「人選的密碼熵很低」；256 bit 隨機數產生的 key，就算用最快的 SHA-256 也不可能被猜中。反過來，API key 每個請求都要驗證，每次花 100 毫秒跑 bcrypt 會拖垮延遲與 CPU。聲聲 Live 用 HMAC-SHA256 加上一把 **pepper**（和資料庫分開保存的秘密值）計算雜湊，只偷到資料庫的人連驗證猜測都做不到。

驗證流程是：解析格式 → 檢查 checksum → 用 key id 查表 → 重算雜湊並用 constant-time 比較（第 17 章）→ 檢查撤銷、到期、環境 → 檢查權限範圍。資料表大致長這樣：

| 欄位 | 例子 | 用途 |
|---|---|---|
| `key_id` | `767bb9ca` | 主鍵或唯一索引，查詢用；可公開 |
| `key_hash` | HMAC-SHA256(pepper, key) 的 hex | 驗證用；不可逆 |
| `owner` | `school_hsinchu` | 這把 key 代表誰；授權與稽核的主體 |
| `env` | `live` | 防止 test key 用在正式環境 |
| `scopes` | `courses:read` | 權限範圍，最小權限 |
| `created_at`／`expires_at` | 2026-10-02／2027-10-02 | 強制到期，避免永久有效的 key |
| `last_used_at`／`last_used_ip` | 2026-10-02 03:00、198.51.100.140 | 判斷是否還在用、偵測異常來源 |
| `revoked_at` | 空值 | 撤銷時間；撤銷後保留資料列供稽核 |

### 權限範圍與附加限制

**scope**（權限範圍）把 key 能做的事列出來，例如合作學校的 key 只有 `courses:read`，不能退款、不能讀學生個資。這是**最小權限原則**（least privilege）：key 遲早會外洩，損害由它的權限決定。還可以加上**附加限制**：來源網段、每把 key 的 rate limit、有效期限。這裡的來源網段是「驗證身分之後」的額外條件，和故事裡「用 IP 取代驗證」是兩回事。

key 放在 header 裡送（`Authorization: Bearer ssk_live_…` 或 `X-API-Key`），**絕不放在 URL 的 query string**：URL 會被寫進 nginx 與 CDN 的 access log、瀏覽器歷史與 `Referer`，而多數工具預設不記 `Authorization`。bearer 憑證也只能走 HTTPS（第 18 章）。

### 輪替：雙 key 並行，而不是「換掉就好」

**輪替**（rotation）是定期把舊 key 換成新 key，讓「過去某時外洩但沒人發現」的 key 自動失效。輪替的難處在於：client 端的設定不會在同一瞬間全部更新。合作學校可能有三台排課主機、一套備援、一份忘記的 cron job；如果 server 換了 key 就立刻讓舊的失效，總有一台會在凌晨三點開始報錯。解法是讓同一個 owner 在一段時間內**同時擁有兩把有效的 key**：

```text
 時間 ─────────────────────────────────────────────────────────────────────►
        ① 發新 key B           ② 客戶逐台換成 B          ③ A 的 last_used 停止更新   ④ 撤銷 A
 key A  ████████████████████████████████████████████████████████████████████┤ revoked
 key B                 ├████████████████████████████████████████████████████████████████████
                       │◄──────────── 並行期：A、B 都有效（例如 14 天）─────────►│
 監控                   A 的使用量：100% ──► 60% ──► 5% ──► 0%（連續 7 天）──────► 才撤銷
```

① 為同一個 owner 發第二把 key B，A 仍然有效。② 客戶在並行期內逐台換成 B，不會中斷。③ 觀察 A 的 `last_used_at`：使用量降到 0 並持續一段時間（例如 7 天，涵蓋每週一次的批次工作），才代表真的換完了。④ 撤銷 A。關鍵在第三步：撤銷的依據是資料，不是「我已經通知客戶了」；資料表也因此必須允許一個 owner 有多把 key。

緊急情況則不同：key 已經外洩時，並行期就是攻擊者的窗口，應該立即撤銷、接受短暫中斷，再查 `last_used_ip` 與存取 log 確認是否被濫用。反過來，30.2 節圖中的 ④ 是我們持有別人發的 key，同樣的規則套用在自己身上：放 secret manager（30.8 節）、只給需要的服務、啟用對方提供的 IP 與權限限制，並登記使用位置，輪替時才知道要改哪裡。

## 30.4 HMAC 請求簽章：秘密不上線

API key 的根本弱點是「秘密本身每次都在網路上傳」。就算全程 HTTPS，請求在 TLS 終結之後（LB、nginx、應用程式）仍是明文，任何一層的 debug log 都可能把 header 整個記下來。**HMAC 請求簽章**換了一種思路：client 和 server 事先共享一把 secret，client 用 secret 對「這個請求的內容」算出一個 **HMAC**（keyed hash，只有知道 secret 的人才算得出來，第 17 章），把結果放在 header 裡送出；server 用同一把 secret 重算一次，結果相同就代表「送的人持有 secret，而且簽到的內容一個 byte 都沒改」。被記進 log 的只是這個請求專屬的簽章，拿去改別的請求完全沒用。

### Canonical request：先約定「簽的到底是哪些 bytes」

簽章最難的部分不是 HMAC，而是**決定要簽什麼**。一個 HTTP 請求從 client 走到 server，中間的 proxy、LB、框架可能做出許多「語意不變、bytes 改變」的動作：header 名稱大小寫被改（HTTP/2 一律小寫）、header 順序被重排、query 參數順序改變、多個空白被壓縮。如果 client 簽的是「它送出的原始 bytes」，server 收到的 bytes 早就不一樣了。解法是雙方約定一個**標準化形式**（canonical request）：把請求的各部分按照固定規則整理成一段字串，雙方各自從自己看到的請求重建這段字串，再對它簽章。

```text
 canonical request（每段一行，用 \n 串接）
 ┌───────────────────────────────────────────────────────────────────────┐
 │ POST                                   ← method，大寫                 │
 │ /v1/recommend                          ← path，依規則做 percent-encode│
 │ lang=ja&limit=5                        ← query：參數依名稱排序後編碼  │
 │ content-type:application/json          ← 要簽的 header：名稱小寫、    │
 │ host:reco.live.svc.cluster.local          依名稱排序、值壓縮空白      │
 │ content-type;host                      ← signed headers 清單          │
 │ 361b2e6f…ee419603                      ← SHA-256(body) 的 hex         │
 └───────────────────────────────────────────────────────────────────────┘
                     │ SHA-256
                     ▼
 string to sign：  "SS-HMAC-SHA256" \n ts \n nonce \n hex(SHA-256(canonical request))
                     │ HMAC-SHA256(secret, ·)
                     ▼
 Authorization: SS-HMAC-SHA256 keyId=api-2026q4,ts=1791000000,nonce=…,signedHeaders=content-type;host,signature=…
```

由上往下讀。method 和 path 決定「做什麼事」，一定要簽，否則攻擊者可以把一個簽好的 `GET /v1/recommend` 改成 `POST /v1/admin`。query 參數排序後再簽，proxy 重排參數也不會讓驗證失敗。header 只簽**列在 signed headers 裡的那幾個**，因為路上一定會被加上新的 header（例如 `X-Forwarded-For`），簽全部只會讓驗證永遠失敗；但 `host` 必須在清單裡，否則同一個簽章可以被拿去打另一個服務。body 不直接放進來，而是放它的 SHA-256，讓 canonical request 長度固定、也讓大 body 可以邊收邊算。

接著把 canonical request 再雜湊一次，和**演算法名稱、timestamp、nonce** 組成 string to sign，最後用 secret 算 HMAC；timestamp 與 nonce 被簽進去，攻擊者就無法只改它們把舊請求偽裝成新的。header 另外帶著 **key id**，讓 server 知道用哪一把 secret 驗證，也讓輪替時新舊 secret 可以並存。AWS 的 **SigV4** 是同一套思路：`Authorization: AWS4-HMAC-SHA256 Credential=AKIA…/20261002/ap-northeast-1/s3/aws4_request, SignedHeaders=…, Signature=…`，它還用日期、區域、服務逐層衍生出當天專用的簽章金鑰，縮小衍生金鑰外洩的影響。

### Timestamp 與 nonce：防止合法請求被重送

HMAC 擋不住**重放**：把一個完整的合法請求原封不動再送一次，簽章當然是對的。防重放靠兩個欄位合作。**timestamp** 讓 server 拒絕 `|server 時間 − ts| > 300 秒` 的請求，錄下的請求五分鐘後就作廢。**nonce**（number used once，只用一次的隨機值）處理這五分鐘內的重送：server 記下見過的 nonce，第二次看到就拒絕；更舊的請求已被 timestamp 擋掉，所以 nonce 只需記住視窗長度那麼久。

```text
 Client（Flask API）                                            Server（reco）
   │ ① 組 canonical request，取 ts=現在、nonce=隨機 16 hex       │
   │ ② signature = HMAC(secret[api-2026q4], string to sign)      │
   │──── POST /v1/recommend  Authorization: SS-HMAC-SHA256 … ───►│
   │                                                             │ ③ keyId 存在？      否 → 401
   │                                                             │ ④ |now − ts| ≤ 300？ 否 → 401
   │                                                             │ ⑤ host 有被簽？      否 → 401
   │                                                             │ ⑥ 重建 canonical request、重算 HMAC
   │                                                             │ ⑦ compare_digest 相同？ 否 → 401
   │                                                             │ ⑧ nonce 見過？      是 → 401
   │                                                             │ ⑨ 記下 nonce（到 ts+300 過期）
   │◄─── 200 OK ─────────────────────────────────────────────────│ ⑩ 授權檢查後處理
```

順序有講究。③ 到 ⑤ 是便宜的檢查，先做可以擋掉大量垃圾請求。⑥ ⑦ 驗簽章。⑧ ⑨ 記錄 nonce 一定要在**簽章驗證成功之後**，否則攻擊者可以送一堆假簽章的請求，把正常 client 將要用的 nonce 或整個快取塞滿。多台 server 時，nonce 快取要放在共用的地方（例如 Redis 加上 TTL），否則同一個請求重放到另一台就檢查不到。timestamp 視窗也帶來一個營運需求：所有機器的時鐘必須同步（NTP），時鐘偏差超過視窗，合法請求也會被拒絕，這是 HMAC 簽章最常見的「莫名其妙 401」來源。

下面的程式實作上面這套簽章，並模擬幾種情況：正常請求、同一個請求重送、proxy 重排 query 與改變 header 大小寫、path 被竄改、body 多一個空白、以及十分鐘後重送。

```python
import hashlib
import hmac
import secrets
from urllib.parse import quote, urlsplit, parse_qsl

KEYS = {"api-2026q4": b"shared-secret-from-secret-manager"}   # key id → secret
WINDOW = 300
seen_nonces = {}                                               # nonce → 到期時間


def canonical_request(method, url, headers, body, signed):
    parts = urlsplit(url)
    query = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}"
                     for k, v in sorted(parse_qsl(parts.query, keep_blank_values=True)))
    lines = [method.upper(), quote(parts.path or "/", safe="/"), query]
    lines += [f"{h}:{' '.join(headers[h].split())}" for h in signed]   # 小寫名稱、壓縮空白
    lines += [";".join(signed), hashlib.sha256(body).hexdigest()]
    return "\n".join(lines)


def sign(key_id, method, url, headers, body, ts, nonce):
    headers = {k.lower(): v for k, v in headers.items()}
    signed = sorted(headers)
    creq = canonical_request(method, url, headers, body, signed)
    to_sign = f"SS-HMAC-SHA256\n{ts}\n{nonce}\n{hashlib.sha256(creq.encode()).hexdigest()}"
    sig = hmac.new(KEYS[key_id], to_sign.encode(), hashlib.sha256).hexdigest()
    return (f"SS-HMAC-SHA256 keyId={key_id},ts={ts},nonce={nonce},"
            f"signedHeaders={';'.join(signed)},signature={sig}"), creq


def verify(auth, method, url, headers, body, now):
    fields = dict(p.split("=", 1) for p in auth.removeprefix("SS-HMAC-SHA256 ").split(","))
    if fields["keyId"] not in KEYS:
        return "unknown key id"
    ts = int(fields["ts"])
    if abs(now - ts) > WINDOW:
        return "stale timestamp"
    lower = {k.lower(): v for k, v in headers.items()}
    signed = fields["signedHeaders"].split(";")
    if "host" not in signed or any(h not in lower for h in signed):
        return "required header not signed"
    creq = canonical_request(method, url, lower, body, signed)
    to_sign = f"SS-HMAC-SHA256\n{ts}\n{fields['nonce']}\n{hashlib.sha256(creq.encode()).hexdigest()}"
    expected = hmac.new(KEYS[fields["keyId"]], to_sign.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, fields["signature"]):
        return "signature mismatch"
    for n, exp in list(seen_nonces.items()):                   # 過了視窗的 nonce 可以忘掉
        if exp < now:
            del seen_nonces[n]
    if fields["nonce"] in seen_nonces:
        return "replayed nonce"
    seen_nonces[fields["nonce"]] = ts + WINDOW
    return "ok"


now = 1_791_000_000
body = b'{"lesson":"L-778","teacher":"misaki"}'
hdrs = {"Host": "reco.live.svc.cluster.local", "Content-Type": "application/json"}
url = "http://reco.live.svc.cluster.local/v1/recommend?limit=5&lang=ja"
auth, creq = sign("api-2026q4", "POST", url, hdrs, body, now, secrets.token_hex(8))
print("canonical request：\n" + creq)
print("Authorization：", auth[:72] + "…")

reordered = "http://reco.live.svc.cluster.local/v1/recommend?lang=ja&limit=5"
proxy_hdrs = {"host": "reco.live.svc.cluster.local", "content-type": "application/json"}
results = {
    "原封不動": verify(auth, "POST", url, hdrs, body, now + 2),
    "同一份請求再送一次": verify(auth, "POST", url, hdrs, body, now + 3),
}
auth2, _ = sign("api-2026q4", "POST", url, hdrs, body, now + 5, secrets.token_hex(8))
results["proxy 重排 query、改 header 大小寫"] = verify(auth2, "POST", reordered, proxy_hdrs, body, now + 6)
auth3, _ = sign("api-2026q4", "POST", url, hdrs, body, now + 7, secrets.token_hex(8))
results["path 被改成 /v1/admin"] = verify(auth3, "POST", url.replace("recommend", "admin"), hdrs, body, now + 8)
results["body 多一個空白"] = verify(auth3, "POST", url, hdrs, body + b" ", now + 8)
results["十分鐘後重送"] = verify(auth3, "POST", url, hdrs, body, now + 607)
for label, outcome in results.items():
    print(f"{label} → {outcome}")
assert list(results.values()) == ["ok", "replayed nonce", "ok", "signature mismatch",
                                  "signature mismatch", "stale timestamp"]
```

```text
canonical request：
POST
/v1/recommend
lang=ja&limit=5
content-type:application/json
host:reco.live.svc.cluster.local
content-type;host
361b2e6fce76ed58e6081aa0356644af3cc2f12b8206459f8a7022d9ee419603
Authorization： SS-HMAC-SHA256 keyId=api-2026q4,ts=1791000000,nonce=ca1aab78980384ae,sig…
原封不動 → ok
同一份請求再送一次 → replayed nonce
proxy 重排 query、改 header 大小寫 → ok
path 被改成 /v1/admin → signature mismatch
body 多一個空白 → signature mismatch
十分鐘後重送 → stale timestamp
```

nonce 每次執行都不同，其他輸出固定。前七行就是 canonical request 本身：注意 query 已經被排序成 `lang=ja&limit=5`，header 名稱都是小寫，最後一行是 body 的 SHA-256。結果的第一行是正常請求；第二行把**完全相同**的請求再送一次，簽章、timestamp 都合法，只有 nonce 快取能擋下它。第三行模擬 proxy 把 query 順序與 header 大小寫改掉，驗證仍然通過，這正是 canonical request 存在的理由。第四、五行說明簽章涵蓋了 path 與 body：path 被改、body 多一個空白，簽章就不對了。最後一行是十分鐘後重送：nonce 快取只記得視窗內的值，是 timestamp 視窗在更前面一步把它擋下。

### 驗證端的三個細節

第一，比較簽章用 `hmac.compare_digest` 而不是 `==`，原因第 17、26 章都示範過：`==` 的比較時間會洩漏「前面猜對了幾個 byte」。比較任何秘密或從秘密衍生的值（簽章、token、API key 的雜湊），一律這樣做。

第二，驗證端要**自己決定哪些 header 必須被簽**，不能完全聽 client 的 `signedHeaders`。如果 client 宣告「我只簽了 content-type」，server 照單全收，攻擊者就能把同一個簽章搬到另一個 host 使用；程式裡的 `"host" not in signed` 檢查就是為了擋這種情況。需要防竄改的 header（例如 `content-type`、自訂的 `x-idempotency-key`）也應該列在 server 端的必簽清單裡。

第三，**失敗原因只寫進 log，不回給 client**。對外只回「驗證失敗」，log 記錄失敗在哪一步、key id 與時間差，但不記錄 secret 或完整簽章。

### 真實世界的簽章方案比較

不同系統的簽章方案大同小異，差別在於簽了哪些東西、怎麼防重放。下表整理幾個你很可能在工作上碰到的例子，可以拿來檢查自己設計的方案缺了什麼：

| 方案 | 簽的內容 | 放在哪裡 | 防重放 | 備註 |
|---|---|---|---|---|
| AWS SigV4 | method、path、query、選定 header、body 雜湊、時間、區域與服務 | `Authorization`（或 query 的預簽 URL） | 時間戳記，偏差過大即拒絕 | 衍生金鑰；預簽 URL 有到期時間 |
| Stripe webhook | `t` 加上 `.` 加上原始 body | `Stripe-Signature: t=…,v1=…` | 時間窗（官方函式庫預設 300 秒）＋事件 id 去重 | 輪替期間可能同時帶多個 `v1` |
| GitHub webhook | 原始 body | `X-Hub-Signature-256: sha256=…` | 簽章不含時間；用 `X-GitHub-Delivery` 的 id 去重 | 只靠 body 簽章，重放要另外處理 |
| Slack 請求 | `v0:` 加 timestamp 加 `:` 加原始 body | `X-Slack-Signature`、`X-Slack-Request-Timestamp` | 時間窗 5 分鐘 | 和 Stripe 的想法相同 |
| 本章的內部方案 | 演算法、ts、nonce、canonical request 雜湊 | `Authorization` | 時間窗＋nonce 快取 | 簽 method、path、host，可跨 proxy |

webhook 類的方案大多只簽 body（加上時間），因為它們只有一個固定的接收端點；通用 API 類的方案（SigV4、本章的內部方案）必須簽 method、path、host，否則簽章可以被搬到其他端點使用。

> [!note] 2026 現況
> 截至 2026 年 10 月（依知識整理，未逐項查證）：IETF 的 RFC 9421〈HTTP Message Signatures〉定義了通用的 `Signature-Input` 與 `Signature` header，但多數 webhook 供應商仍用各自的格式；社群的 Standard Webhooks 規格約定 `webhook-id`、`webhook-timestamp`、`webhook-signature` 三個 header，把事件 id、時間與 body 一起簽。新設計可以參考這兩者，不必再發明一套。

## 30.5 Webhook：讓外部系統安全地呼叫你

webhook 把一般 API 的方向反過來：不是我們去問金流供應商「付款了沒」，而是供應商在事件發生時打給我們。這讓 `/v1/webhooks/pay` 成為一個**對公網開放、而且由外人觸發狀態改變**的端點。第 17 章已經把驗證的核心寫好了：簽章確認是供應商送的、時間窗確認不是舊通知、event id 確認同一個事件只生效一次。這一節不重複那段程式，而是處理故事裡暴露的 production 問題：請求經過 LB 與 nginx、由十幾個 worker 處理、會被重試、會亂序、會遇到部署重啟，驗證與去重要怎麼做才站得住。

### Production 上的投遞流程

```text
 pay.example.net             LB 10.20.16.5      nginx 10.20.3.11     gunicorn：3 台 × 4 worker          資料庫 10.20.17.15
 （198.51.100.64/26）              │                   │                   │                                  │
   │── POST /v1/webhooks/pay ─────►│──────────────────►│──────────────────►│ worker 7：                       │
   │   Pay-Signature: t=…,v1=…     │  XFF 附加來源     │ body 原封不動     │ ① 原始 bytes 驗簽（第 17 章）   │
   │   body = 原始 bytes           │                   │                   │── ② BEGIN；INSERT event_id ─────►│ UNIQUE
   │                               │                   │                   │      UPDATE 點數；COMMIT ───────►│
   │                               │                   │                   │── ③ 寄信、通知老師 → 佇列        │
   │◄────────────── 200（2 秒內）──│◄──────────────────│◄──────────────────│                                  │
   │                               │                   │                   │                                  │
   │ 逾時或非 2xx → 退避後重試：新的 t、新的簽章、同一個 event id                                            │
   │── POST（重試）───────────────►│──────────────────►│──────────────────►│ worker 2（另一台、或剛重啟）：    │
   │                               │                   │                   │── INSERT 撞到 UNIQUE ───────────►│ 已存在
   │◄────────────── 200 duplicate ─│◄──────────────────│◄──────────────────│   ROLLBACK，回 200               │
```

這張圖和第 17 章的流程圖有三個差別。第一，請求經過 LB 與 nginx，應用程式看到的 TCP 來源是 nginx 的 10.20.3.11，body 必須被**原封不動**轉送，路徑上任何一層改寫 body，① 的驗簽就會失敗。第二，同一個事件的首次投遞與重試，幾乎一定落在**不同的 worker**，甚至是部署後剛啟動的 worker，所以去重紀錄不能放在 process 記憶體裡，而要放在所有 worker 共用的資料庫。② 把「記錄 event id」和「加點數」放在**同一個交易**裡：兩者一起成功或一起回滾，不會出現「記錄說處理過，點數卻沒加」或反過來的情況；重複的 event id 撞到唯一約束，交易回滾，回 200。

第三，③ 把耗時的工作放進佇列。handler 要在供應商的逾時之內回應（通常是數秒，依供應商而定），否則供應商會把已經成功入帳的通知記成失敗並重試，故事裡的同步寄信正是這樣把重試量放大的。回應的狀態碼也有語意：驗證失敗回 4xx，讓供應商的儀表板顯示錯誤；處理成功或「已經處理過」都回 200；處理到一半遇到暫時性錯誤（例如資料庫連不上）回 5xx，交易已回滾，讓供應商稍後重試。

### 重放與重試：看起來很像，處理方式不同

故事的第二波問題提醒我們：重試是常態，而且它和重放看起來很像。**重放**是攻擊者把簽好的舊請求原封不動再送一次，timestamp 是舊的。**重試**是供應商沒收到 2xx 而再送一次同一個事件，而且會**重新簽章**，timestamp 與簽章都是新的、完全合法，只有事件 id 相同。時間窗擋得住重放，擋不住重試，也不該擋；能讓重試不造成重複入帳的，只有事件 id 去重。

| 情況 | timestamp | 簽章 | event id | 誰擋下或處理它 |
|---|---|---|---|---|
| 正常首次送達 | 新 | 合法 | 新 | 驗證通過，處理 |
| 供應商重試（我們上次回 5xx 或逾時） | 新 | 合法（重新簽） | 相同 | event id 去重：回 200，不重複處理 |
| 攻擊者重放錄下的請求（五分鐘後） | 舊 | 合法（但針對舊 t） | 相同 | 時間窗拒絕 |
| 攻擊者在五分鐘內重放 | 舊，但仍在窗內 | 合法 | 相同 | event id 去重（或 nonce 快取） |
| 攻擊者竄改金額 | 任意 | 不合法 | 任意 | 簽章驗證失敗 |
| 攻擊者偽造新事件 | 任意 | 算不出來 | 新 | 簽章驗證失敗 |

這張表也決定了保存期限。nonce 只需要記住幾分鐘；event id 的去重紀錄則要比**供應商的重試期限**更久（例如 Stripe 在正式環境最長約重試三天），所以通常直接沿用業務資料表，例如付款紀錄表的 `provider_event_id` 欄位加上唯一約束，而不是放在會過期的快取裡。

另一個陷阱是 webhook **不保證順序**：「退款」可能比還在重試的「付款成功」先到。把每筆通知當成「這個物件的狀態可能變了」的提示，依狀態機判斷是否合法轉移；重要的物件可以再用供應商的 API 查一次最新狀態。

### Raw body 的陷阱

簽章是對「供應商送出的那一串 bytes」算的，而 JSON 的同一份資料可以有很多種 bytes：key 的順序、分隔符號後的空白、中文寫 UTF-8 還是 `\u7f8e` 跳脫序列、`10.0` 還是 `10`。先解析再重新序列化，資料相同，HMAC 也會完全不同。

```text
 供應商簽的 bytes（144）  {"id":"evt_8812",…,"note":"秋季課程包","card_last4":"4242"}
        │                 ← UTF-8、沒有空白
        │ middleware：json.loads → 刪掉 card_last4 → json.dumps
        ▼
 view 收到的 bytes（150） {"id": "evt_8812", …, "note": "\u79cb\u5b63\u8ab2\u7a0b\u5305"}
        │                 ← 少了一個欄位、多了空白、中文被跳脫
        ▼
 HMAC(k2, "1791000000." + view 收到的 bytes) ≠ header 裡的 v1   → 401 signature mismatch
```

圖的上半是供應商送出的 144 bytes。middleware 做了兩件事：刪掉一個欄位（改了資料），再用 `json.dumps` 的預設值序列化，加空白、跳脫非 ASCII 字元（改了表示法）；就算只做第二件事，bytes 也變了。下半是結果：我們驗證的是一份供應商從沒簽過的 bytes。144 與 150 這兩個數字會在 30.9 節的實驗中實際出現。

常見的變形還有：middleware 為了記錄 body 把 `wsgi.input` 串流讀完卻沒放回去，view 讀到空的 body（第 41 章）；body 被解碼成字串再編碼回去；proxy 自動解壓縮；`\r\n` 被正規化。原則只有一條：**驗證簽章用框架提供的原始 bytes**（Flask 的 `request.get_data()`），整條路徑上不能有元件改寫 webhook 的 body。做法上，讓 webhook 端點不經過「好心」處理 body 的 middleware；需要記錄 body 的 middleware 只讀一次、原封不動放回去，log 只記長度與 SHA-256；並讓 CI 用含中文的真實格式 payload 跑一次「完整 middleware 堆疊」的驗簽測試，而不是只測 view 函式。

### 來源 IP 是輔助，不是身分

金流供應商公告了 webhook 來源網段（`198.51.100.64/26`、`2001:db8:beef::/48`）。IP 檢查的價值是**縮小攻擊面**，但不能取代簽章：網段可能被其他租戶共用（雲端出口常常如此）、會變更；而且在 LB 與 nginx 後面，應用程式看到的 TCP 來源是 nginx，真正的來源只在 `X-Forwarded-For` 裡，讀錯了就等於讓 client 自己填寫來源。

第 25 章實作過正確的解析：每一層 proxy 把它看到的對端**附加在最右邊**，所以從右往左走、跳過自己信任的 proxy，第一個不可信的位址才是來源；最左邊那段是 client 自己寫的。故事裡的 hotfix 讀最左邊，檢查形同虛設。更穩妥的是讓 nginx 用 `set_real_ip_from` 與 `real_ip_header` 統一處理，或直接在 LB 的安全規則限制來源。

| 防線 | 擋下什麼 | 擋不下什麼 | 在故事中 |
|---|---|---|---|
| 網路層來源限制（LB 安全規則） | 非供應商網段的連線 | 同網段的其他租戶、網段變更 | 沒有設定 |
| 應用程式解析 XFF | 同上（解析正確時） | 解析錯誤時什麼都擋不下 | hotfix 讀最左邊，形同虛設 |
| HMAC 簽章＋時間窗 | 偽造、竄改、過期的重放 | 正常的重試（也不該擋） | middleware 改寫 body，合法通知全被拒 |
| event id 唯一約束 | 重試與窗口內重放造成的重複處理 | 偽造事件（要靠簽章） | 記在記憶體，重啟就失效 |

每一層只負責一件事，任何一層都不能取代另一層。止血時最容易犯的錯，是為了讓一層恢復運作而拆掉另一層；故事裡比較安全的 hotfix，是暫時移除那個改寫 body 的 middleware，而不是關掉簽章驗證。

> [!example] 例子：聲聲 Live 對外送出的 webhook
> 聲聲 Live 也會發 webhook 給合作學校（例如「課程已取消」）。這時我們是送出方，責任反過來：每個學校一把獨立的 webhook secret；簽 `t`、事件 id 與原始 body；輪替時同時用新舊 secret 簽；失敗時指數退避重試並保證事件 id 不變；在後台讓學校看到投遞紀錄。學校可以自己填 webhook URL，所以送出前必須檢查 URL 解析出的位址不是內網或 metadata 位址，避免 webhook 系統被當成 SSRF（伺服器端請求偽造）的跳板。

## 30.6 mTLS 與 service mesh

回到故事的另一個問題：五個服務共用一把 API key 呼叫 `reco`。`reco` 因此無法分辨是誰在呼叫、無法給不同權限；任何一個服務外洩，五個一起暴露；輪替要五個團隊同時配合。改成 HMAC 只解決「秘密不上線」，沒解決「秘密怎麼發、怎麼換」。這一節與下一節的方向是：讓每個服務有**自己的身分**，由平台自動發放與輪替。

### mTLS：雙方都出示憑證

一般的 TLS 只有 server 出示憑證（第 18 章）。**mTLS**（mutual TLS，雙向 TLS）讓 client 也出示憑證，並用私鑰簽交握內容證明自己持有私鑰。交握完成後，server 不只知道連線是加密的，還知道「對面是誰」，而且這個身分由 server 信任的 CA 背書。

```text
 Client（Flask API，持有 api 的憑證與私鑰）                Server（reco，信任內部 CA）
   │──── ClientHello ──────────────────────────────────────────►│
   │◄─── ServerHello ───────────────────────────────────────────│
   │◄─── {EncryptedExtensions} ─────────────────────────────────│
   │◄─── {CertificateRequest}  ← 「請出示你的憑證」              │
   │◄─── {Certificate}  reco 的憑證鏈                            │
   │◄─── {CertificateVerify, Finished} ─────────────────────────│
   │ 驗證 reco：鏈到內部 CA、名稱符合、未過期                    │
   │──── {Certificate}  api 的憑證（URI SAN: spiffe://…/sa/api）►│
   │──── {CertificateVerify}  用 api 的私鑰簽交握紀錄 ──────────►│ 驗證：鏈到內部 CA、未過期、
   │──── {Finished} ────────────────────────────────────────────►│ 簽章正確 → 取出身分
   │════════════ 加密的應用資料（reco 知道對方是 api）═══════════│ 依身分做授權
```

括號 `{}` 表示加密的訊息。和一般 TLS 1.3 交握相比，新角色是 server 送出的 CertificateRequest，以及 client 回傳的 Certificate 與 CertificateVerify；server 驗證憑證鏈到內部 CA、驗證簽章，就確定對方持有私鑰。最後一行很關鍵：mTLS 只是驗證，`reco` 還要依身分決定「api 可以呼叫 `/v1/recommend`，不能呼叫 `/v1/admin`」。

身分寫在憑證的 **SAN**（Subject Alternative Name）欄位；服務身分常用 **URI SAN**，例如 `spiffe://shengsheng.example/ns/live/sa/api`（下一節的 SPIFFE 格式）。和 API key 相比，mTLS 的私鑰不離開本機、網路上只有憑證與簽章；憑證可以發得很短（例如 24 小時）；應用程式也不必處理秘密。

代價是營運：內部 CA、憑證發放與輪替、到期監控。手動管理幾十個服務的憑證幾乎一定出事，所以 mTLS 實務上都和自動化綁在一起。下面是檢查 mTLS 設定的指令（示意輸出），以及 Python `ssl` 要求 client 憑證的設定：

```bash
# 以 api 的身分連 reco，並印出對方憑證的 SAN（需要 api 的憑證、私鑰與內部 CA）
openssl s_client -connect reco.live.svc.cluster.local:8443 \
  -cert api.crt -key api.key -CAfile internal-ca.crt -brief </dev/null
# ↓ 示意輸出
CONNECTION ESTABLISHED
Protocol version: TLSv1.3
Peer certificate: CN = reco
Verification: OK

openssl x509 -in api.crt -noout -ext subjectAltName -enddate
# ↓ 示意輸出
X509v3 Subject Alternative Name:
    URI:spiffe://shengsheng.example/ns/live/sa/api
notAfter=Oct  3 12:00:00 2026 GMT
```

```python
# not-runnable：需要事先準備憑證檔案；示範 Python ssl 模組要求 client 憑證的設定
import ssl

server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)  # 不用 create_default_context：它會載入系統的公開 CA
server_ctx.load_cert_chain("reco.crt", "reco.key")
server_ctx.load_verify_locations("internal-ca.crt")   # 只信任內部 CA，不信任公開 CA
server_ctx.verify_mode = ssl.CERT_REQUIRED            # 沒有 client 憑證就中止交握
# 交握後：conn.getpeercert()["subjectAltName"] 取出 ('URI', 'spiffe://…/sa/api')，再做授權

client_ctx = ssl.create_default_context(cafile="internal-ca.crt")
client_ctx.load_cert_chain("api.crt", "api.key")      # client 出示自己的憑證
```

第一個指令確認交握成功；若 server 要求 client 憑證而你沒給，交握會以 alert 失敗。第二個指令印出 SAN 與到期時間，這是排查「為什麼 reco 認不得我」時最先看的兩個欄位。Python 範例的重點是 server 端的 `CERT_REQUIRED` 與「只載入內部 CA」：如果信任了公開 CA，任何人買一張公開憑證都能通過驗證。

### Service mesh：把 mTLS 交給基礎設施

**service mesh** 是一層專門處理服務之間通訊的基礎設施：在每個服務旁邊放一個 proxy（常見的是 Envoy），服務之間的流量都經過這些 proxy，由 proxy 負責 mTLS、重試、逾時、流量統計與授權政策。應用程式只跟本機的 proxy 說明文 HTTP，完全不必處理憑證。控制平面（control plane）負責替每個工作負載發憑證、定期輪替、把授權政策推送給 proxy。

```text
 Pod：api（namespace live）                              Pod：reco（namespace live）
 ┌─────────────────────────────────┐                    ┌─────────────────────────────────┐
 │ Flask ──明文 HTTP──► sidecar ───┼═══ mTLS（自動）════┼─► sidecar ──明文 HTTP──► reco   │
 │  127.0.0.1           proxy      │  身分：            │   proxy       127.0.0.1         │
 │                      ▲          │  spiffe://shengsheng.example/ns/live/sa/api          │
 └──────────────────────┼──────────┘                    └──────▲──────────────────────────┘
                        │ 憑證（例如 24 小時效期，自動輪替）    │ 授權政策：
                 ┌──────┴────────────────────────────────────────┴──────┐
                 │ 控制平面：內部 CA、發憑證、推送政策                   │
                 │ 「sa/api 可以 POST /v1/recommend；其他身分一律拒絕」  │
                 └───────────────────────────────────────────────────────┘
```

Flask 送出普通的 HTTP 請求，被本機的 sidecar 攔截（通常靠 iptables 之類的機制），兩邊的 proxy 建立 mTLS，對面驗證身分、檢查授權政策，再把明文轉給 `reco`。控制平面負責人最容易忘記的事：憑證多短、何時換、誰能呼叫誰。Istio 這類 mesh 預設使用 `spiffe://<trust domain>/ns/<namespace>/sa/<service account>` 格式的身分，trust domain 預設是 `cluster.local`；聲聲 Live 把它設定成 `shengsheng.example`，讓 mesh 發出的身分和 30.6 節 mTLS 憑證裡的 `spiffe://shengsheng.example/ns/live/sa/api` 一致。

應用程式若要知道呼叫方是誰，可以讀 proxy 加上的 header，例如 Envoy 的 `X-Forwarded-Client-Cert`（XFCC）。它的信任規則和 XFF 一樣：proxy 必須先移除 client 自帶的同名 header，應用程式也只能聽 `127.0.0.1`，否則繞過 proxy 的人就能自己寫這個 header。

| 面向 | 應用程式自己做 mTLS | Service mesh（sidecar 或節點層 proxy） |
|---|---|---|
| 憑證發放與輪替 | 自己整合 CA 與輪替流程，每種語言各做一次 | 控制平面自動處理 |
| 應用程式改動 | 每個 client 與 server 都要設定 `ssl` | 幾乎不用改，對 localhost 說明文 |
| 授權政策 | 寫在每個服務的程式碼裡 | 集中宣告，proxy 執行；細粒度業務規則仍在應用程式 |
| 延遲與資源 | 只有 TLS 本身的成本 | 每一跳多經過兩個 proxy，每個 Pod 多一份記憶體與 CPU |
| 適合 | 少量服務、跨平台的呼叫、對外的 B2B API | 大量服務在同一個叢集或平台 |

mesh 的代價是複雜度：proxy 設定錯誤會讓整個叢集的流量中斷，除錯時還要分清楚錯誤是應用程式還是 proxy 回的。聲聲 Live 的判斷是：叢集內服務多、團隊多，值得導入 mesh；對外的合作夥伴 API 仍用 API key 或 OAuth client credentials（第 28 章），因為要求每所學校管理 client 憑證，等於把營運成本轉嫁給對方。

> [!note] 2026 現況
> 截至 2026 年 10 月（依知識整理，未逐項查證）：Istio 除了傳統的 sidecar 模式，也提供不需要 sidecar 的 ambient 模式，由每個節點上的 L4 proxy（ztunnel）負責 mTLS，需要 L7 政策時才加上 waypoint proxy；Linkerd 使用自己的 Rust proxy。Kubernetes Gateway API 的 GAMMA 規範讓 mesh 也能用 HTTPRoute 等資源描述服務之間的路由（第 44 章）。導入前請以各專案的官方文件確認目前的穩定狀態。

## 30.7 Workload identity：讓身分取代秘密

前面每一種機制都會遇到同一個問題：**第一個秘密從哪裡來？** 就連 mTLS 的私鑰，也要先證明「我是 api」才領得到憑證；用另一把秘密去領，只是把問題往後推，這叫 **secret zero** 問題。**workload identity**（工作負載身分）的答案是讓平台作證：Kubernetes、雲端虛擬機、CI 系統本來就知道「這個 process 是哪個 Pod、屬於哪個 service account」，由它發出短效的身分文件，程式不必持有任何長期秘密。

### SPIFFE：服務身分的共同語言

**SPIFFE**（Secure Production Identity Framework For Everyone）是一套定義服務身分的開放規範，它規定了三件事。第一，身分的名字：**SPIFFE ID**，格式是 `spiffe://<trust domain>/<路徑>`，例如 `spiffe://shengsheng.example/ns/live/sa/api`，trust domain 是一個信任範圍（通常是一個組織或一個環境）。第二，身分的載體：**SVID**（SPIFFE Verifiable Identity Document），有兩種形式，X.509-SVID 是把 SPIFFE ID 放在 URI SAN 的短效憑證，用於 mTLS；JWT-SVID 是一個簽章的 JWT（第 27 章），用於無法做 mTLS 的場合，例如經過 L7 proxy 的請求。第三，怎麼領：**Workload API**，工作負載透過本機的 Unix domain socket 向 agent 索取自己的 SVID，不需要帶任何憑證。

agent 怎麼知道呼叫者是誰？這一步叫 **attestation**（證明）：**節點證明**用雲端簽發的機器身分文件確認 agent 所在的機器；**工作負載證明**透過核心取得呼叫 socket 的 process PID，查出它屬於哪個 Pod、service account 與容器映像。SPIRE 是 SPIFFE 的參考實作。重點在模型本身：**身分由可驗證的執行環境推導出來，以短效文件呈現，自動輪替**。

### 雲端 IAM role：不在機器上放任何 access key

雲端是 workload identity 最常見的實例。在 AWS 上，與其把一組長期的 access key（`AKIA` 開頭）放進環境變數，不如替虛擬機或容器指定一個 **IAM role**：程式需要呼叫雲端 API 時，SDK 自動向平台索取這個 role 的**臨時憑證**（`ASIA` 開頭的 access key、secret 與 session token，數小時內到期），用它做 SigV4 簽章。程式碼裡完全不出現 key，憑證到期前 SDK 自動換新。

虛擬機上，臨時憑證來自 **instance metadata service**（IMDS），一個只有那台機器能存取的 link-local 位址 `169.254.169.254`。它曾是知名外洩事件的入口：應用程式若有 SSRF 漏洞（伺服器替攻擊者去抓任意 URL），攻擊者就能讓伺服器去讀 metadata，拿到臨時憑證。**IMDSv2** 的防禦是要求先用 `PUT` 取得一個 session token，再用帶著 token header 的 `GET` 讀資料，一般的 SSRF 只能讓伺服器發出簡單的 GET，做不到這兩步；回應封包的 hop limit 也可以設成 1，讓多經過一層網路的容器拿不到。新建的環境應該強制只允許 IMDSv2。

Kubernetes 上，Pod 的身分是它的 service account。kubelet 會把一個**投射的 service account token**（projected token，有指定 audience 與到期時間的 JWT，由叢集的簽章金鑰簽發）掛進 Pod。雲端的 **workload identity federation** 讓這個 token 能換成雲端的臨時憑證：

```text
 Pod api（sa: api，namespace live）           雲端 STS                         物件儲存
   │ ① kubelet 掛入 projected token（JWT）     │                                │
   │    iss=叢集 OIDC issuer                   │                                │
   │    sub=system:serviceaccount:live:api     │                                │
   │    aud=sts，exp=1 小時後                  │                                │
   │── ② AssumeRoleWithWebIdentity（token）───►│ ③ 用 issuer 的 JWKS 驗簽章       │
   │                                           │   檢查 aud、exp                  │
   │                                           │   role 的信任政策：只接受         │
   │                                           │   sub=…:live:api                 │
   │◄── ④ 臨時憑證（ASIA…，1 小時後到期）──────│                                │
   │── ⑤ PUT /recordings/L-778.mp4（SigV4 用臨時憑證簽）───────────────────────►│ ⑥ 依 role 的權限政策授權
```

① kubelet 替 Pod 掛入短效 JWT，宣告「我是 live namespace 的 api」，由叢集的 OIDC issuer 簽章。② SDK 拿它呼叫雲端的 STS（Security Token Service）。③ STS 用叢集公開的 JWKS（第 27 章）驗簽章，再檢查 role 的**信任政策**：只接受 `sub` 是 `system:serviceaccount:live:api` 的 token。④ STS 發出臨時憑證。⑤ ⑥ SDK 用它簽 SigV4 請求，物件儲存依 role 的權限政策授權。整條鏈上沒有人手動保管長期 key。

同一個模式也適用於 CI：GitHub Actions 等平台可以為每次 workflow 執行發出 OIDC token（workflow 要授予 `id-token: write` 權限），雲端的信任政策限定「只接受某個 repo 的 main 分支」，CI 裡就不必存放雲端 access key。

> [!warning] 常見誤解
> 「用了 IAM role 就安全了」只對了一半。role 解決的是憑證的保管與輪替，權限仍然要最小化：一個能讀寫所有 bucket 的 role，被 SSRF 拿到臨時憑證時，一小時內就能造成全部的損害。信任政策也要寫精確，`sub` 用萬用字元允許整個叢集的所有 service account，等於讓任何一個被入侵的 Pod 都能扮演這個 role。

## 30.8 Secrets 管理

不論用哪種機制，系統裡總會留下一些秘密：webhook secret、金流供應商發給我們的 API key、資料庫密碼、Flask 的 `SECRET_KEY`、簽 JWT 的私鑰。**secrets 管理**要回答四個問題：秘密存在哪裡、怎麼交給程式、誰能讀、怎麼換。故事裡那把 `RECO_API_KEY` 在每一題都答錯：存在 git、用設定檔交付、所有能讀 repo 的人都能讀、三年沒換。

### 秘密不該出現的地方

最常見的外洩不是加密被攻破，而是秘密出現在不該出現的地方。**git repo**：commit 後就留在歷史裡，任何 clone 都有，正確處理是**撤銷並輪替**，改寫歷史只是附帶清理。**容器映像**：每一層都能被拆開，`COPY .env` 或 build argument 帶入的秘密都留在裡面。**log 與錯誤追蹤**：印出整個 header 或設定物件的 debug log。**錯誤頁**：Werkzeug 的 interactive debugger 能看到所有變數甚至執行任意程式碼，絕不能在 production 開啟（第 41 章）。

**環境變數**比寫死在程式碼裡好得多，但不是保險箱：它會被子 process 繼承、出現在 crash dump 與監控工具收集的 process 資訊裡、在 Linux 上可從 `/proc/<pid>/environ` 讀到，也常被「印出所有設定」的 debug 端點輸出。更好的做法是由 secret manager 的 agent 或 Kubernetes 的 CSI driver 把秘密寫成**只有該 process 能讀的檔案**（通常在記憶體檔案系統上），輪替時重新讀取。

```text
 Secret manager（Vault、雲端 secret manager）
   │  存放：加密後的秘密；權限：依 workload identity 授權（30.7 節）
   │  稽核：誰在什麼時候讀了哪個版本
   ▼
 Agent／CSI driver（在節點或 Pod 內）
   │ ① 用 Pod 的身分驗證自己（不需要另一把秘密）
   │ ② 取回 pay/webhook-secret 的目前版本（v7）與前一版（v6）
   ▼
 /run/secrets/pay-webhook（tmpfs、權限 0400、只掛進 api 的 Pod）
   │ ③ 新版本發布時，agent 更新檔案
   ▼
 Flask：啟動時讀檔；收到通知或定期重新讀取；驗證時新舊版本都接受
```

這條鏈的起點是 30.7 節的 workload identity：agent 用 Pod 的身分證明自己，secret zero 問題因此有了終點。② 同時取回目前與前一版，讓輪替期間的驗證兩者都接受，和雙 key 並行是同一個想法。③ 秘密以檔案交付，不出現在環境變數與映像裡；secret manager 的稽核紀錄則讓「誰讀過這把秘密」可以回答。

### 輪替與短效：讓外洩自動過期

最好的秘密是不存在的秘密（workload identity），其次是**短效**的秘密：secret manager 的**動態秘密**（dynamic secrets）在需要時才產生一組資料庫帳密，附上幾小時的租期（lease），到期自動刪除。無法短效的秘密，就讓**輪替變成例行公事**。平順輪替的關鍵在本章出現過好幾次：驗證端同時接受新舊版本，簽章或 token 帶著 key id。Flask 3.1 起的 `SECRET_KEY_FALLBACKS` 就是一例：新 key 簽發 session cookie，舊 key 只用來驗證，輪替時使用者不會全部被登出。

需要加密大量資料時，常用**信封加密**（envelope encryption）：資料用資料金鑰加密，資料金鑰再由 KMS 裡永不離開 KMS 的主金鑰加密後和資料存在一起；輪替主金鑰時只要重新加密資料金鑰。

| 秘密 | 建議的存放與交付 | 輪替方式 | 外洩時的影響範圍 |
|---|---|---|---|
| 金流 webhook secret | secret manager → 檔案，只給 api | 供應商後台產生新 secret，新舊並行後移除舊的 | 可偽造付款通知：最高風險 |
| 金流供應商發給我們的 API key | secret manager；啟用供應商的 IP 與權限限制 | 供應商後台發新 key，部署後撤銷舊 key | 可代表我們退款、查交易 |
| 內部服務呼叫（api → reco） | 改用 mTLS 或 workload identity，不存秘密 | 平台自動，憑證每天換 | 單一服務身分，短時間內有效 |
| 雲端 API 存取 | IAM role 的臨時憑證，不建立 access key | 平台自動，數小時到期 | 依 role 的權限；到期後失效 |
| Flask `SECRET_KEY` | secret manager → 檔案 | 新 key 簽發，舊 key 放 `SECRET_KEY_FALLBACKS` | 可偽造 session cookie |
| 資料庫密碼 | 動態秘密（租期數小時）或 secret manager | 動態秘密自動到期；靜態密碼定期輪替 | 資料外洩 |

這張表是 Rita 留給團隊的作業。保護的強度應該依最後一欄「外洩時的影響範圍」決定：webhook secret 與 `SECRET_KEY` 能讓攻擊者偽造「系統以為是自己人」的東西，等級最高；能交給平台自動處理的，就不要再用人工管理的秘密。

## 30.9 動手做：webhook receiver 的 production 陷阱與 API key 模組

第 17 章的動手做已經驗證過簽章、時間窗與輪替的基本行為，這一節不再重複，而是把故事裡的兩個 production 陷阱縮小重現，再實作 30.3 節的 API key 模組。三段程式都只用標準函式庫，HTTP 部分在 127.0.0.1 上用 port 0，時間用固定的模擬值。

### 實驗一：WSGI middleware 讓合法的 webhook 驗證失敗

這段程式用 `wsgiref` 在 127.0.0.1 上起一個 WSGI server，view 沿用第 17 章的驗證規則（`Pay-Signature`、k2／k1、300 秒）。我們把同一個 view 放進四種 middleware 堆疊：沒有 middleware、故事裡的「解析後重新序列化」（A）、「為了記 log 把串流讀完卻沒放回」（B），以及修正版。四次都送出**完全相同、完全合法**的通知。

```python
import hashlib
import hmac
import io
import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

SECRETS = {"k2": b"whsec-k2-current", "k1": b"whsec-k1-rotating"}
NOW, TOLERANCE = 1_791_000_000, 300


def verify(header: str, raw: bytes) -> str:
    """第 17 章的驗證規則：t 在 300 秒內，HMAC(secret, "{t}." + 原始 body) 與 v1 相符。"""
    fields = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    if abs(NOW - int(fields.get("t", 0))) > TOLERANCE:
        return "timestamp outside tolerance"
    for kid, secret in SECRETS.items():
        mac = hmac.new(secret, f"{fields['t']}.".encode() + raw, hashlib.sha256).hexdigest()
        if hmac.compare_digest(mac, fields.get("v1", "")):
            return f"ok ({kid})"
    return "signature mismatch"


def webhook_app(environ, start_response):
    size = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(size)                 # view 看到的「原始」body
    result = verify(environ.get("HTTP_PAY_SIGNATURE", ""), raw)
    status = "200 OK" if result.startswith("ok") else "401 Unauthorized"
    body = f"{result}; view 收到 {len(raw)} bytes".encode()
    start_response(status, [("Content-Type", "text/plain; charset=utf-8")])
    return [body]


def redacting_logger(app):
    """錯誤示範 A：解析 JSON、遮蔽欄位後「重新序列化」再交給 view。"""
    def middleware(environ, start_response):
        data = json.loads(environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"])))
        data.pop("card_last4", None)
        new = json.dumps(data).encode()                    # 預設會加空白、把中文跳脫
        environ["wsgi.input"], environ["CONTENT_LENGTH"] = io.BytesIO(new), str(len(new))
        return app(environ, start_response)
    return middleware


def peeking_logger(app):
    """錯誤示範 B：只是想記錄 body，卻把串流讀完了沒有放回去。"""
    def middleware(environ, start_response):
        # gunicorn、Werkzeug 會把輸入包成有長度上限的串流，讀完再讀只會得到 b""；
        # 這裡用 BytesIO 模擬那種串流（wsgiref 不設上限，再讀會一直等到逾時）
        stream = io.BytesIO(environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"])))
        print("   B 記下的 log：", stream.read()[:24], "…")      # 讀完了，卻沒有倒帶
        environ["wsgi.input"] = stream
        return app(environ, start_response)
    return middleware


def safe_logger(app, log):
    """修正版：讀一次原始 bytes，原封不動放回去；log 只記長度與雜湊。"""
    def middleware(environ, start_response):
        raw = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))
        log.append(f"len={len(raw)} sha256={hashlib.sha256(raw).hexdigest()[:12]}")
        environ["wsgi.input"] = io.BytesIO(raw)
        return app(environ, start_response)
    return middleware


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


raw = json.dumps({"id": "evt_8812", "type": "payment.succeeded", "order": "A1024",
                  "amount": 1200, "student": "student-0457", "note": "秋季課程包",
                  "card_last4": "4242"}, ensure_ascii=False, separators=(",", ":")).encode()
mac = hmac.new(SECRETS["k2"], f"{NOW}.".encode() + raw, hashlib.sha256).hexdigest()
header = f"t={NOW},v1={mac}"
log = []
stacks = {"沒有 middleware": webhook_app,
          "A 重新序列化": redacting_logger(webhook_app),
          "B 讀完沒放回": peeking_logger(webhook_app),
          "修正版": safe_logger(webhook_app, log)}
results = {}
for label, app in stacks.items():
    server = make_server("127.0.0.1", 0, app, handler_class=Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/webhooks/pay", data=raw,
                                 headers={"Pay-Signature": header, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            results[label] = (resp.status, resp.read().decode())
    except urllib.error.HTTPError as err:
        results[label] = (err.code, err.read().decode())
    server.shutdown()
    server.server_close()
    print(f"{label} → {results[label][0]} {results[label][1]}")

print(f"供應商送出 {len(raw)} bytes；修正版的 log：{log[0]}")
rebuilt = json.loads(raw)
rebuilt.pop("card_last4")
print("供應商簽的 body 結尾：", raw.decode()[-45:])
print("A 交給 view 的結尾：  ", json.dumps(rebuilt)[-52:])
assert [r[0] for r in results.values()] == [200, 401, 401, 200]
```

```text
沒有 middleware → 200 ok (k2); view 收到 144 bytes
A 重新序列化 → 401 signature mismatch; view 收到 150 bytes
   B 記下的 log： b'{"id":"evt_8812","type":' …
B 讀完沒放回 → 401 signature mismatch; view 收到 0 bytes
修正版 → 200 ok (k2); view 收到 144 bytes
供應商送出 144 bytes；修正版的 log：len=144 sha256=1df1d1ef0e78
供應商簽的 body 結尾： ent-0457","note":"秋季課程包","card_last4":"4242"}
A 交給 view 的結尾：   ent-0457", "note": "\u79cb\u5b63\u8ab2\u7a0b\u5305"}
```

逐行看。第 1 行是基準：沒有 middleware，view 收到供應商送出的 144 bytes，用 k2 驗證通過。第 2 行是故事的現場：middleware A 刪掉 `card_last4`、再用預設參數序列化，view 收到 150 bytes，HMAC 對不上，合法通知被當成偽造。最後兩行把差異印出來：原本的 `"note":"秋季課程包"` 變成了帶空白、以 `\uXXXX` 跳脫的版本，`card_last4` 也不見了。

第 3、4 行是 middleware B：只想記 log，讀完串流卻沒倒帶，view 收到 0 bytes，同樣回 401。gunicorn 與 Werkzeug 的輸入串流有長度上限，讀完再讀得到空 bytes，程式用 `BytesIO` 模擬這種行為；在不設上限的 `wsgiref` 上，第二次讀取會一直等到 client 逾時，症狀變成「webhook 偶爾卡住」。第 5 行是修正版：只讀一次、原封不動放回 `wsgi.input`，log 只記長度與雜湊前 12 碼（第 6 行），既有除錯線索，也沒把卡號寫進 log。

### 實驗二：去重要跨 worker、跨重啟，而且和入帳同一個交易

這段程式不需要 HTTP，直接模擬故事的投遞順序：首次投遞、落在另一個 worker 的重試、部署重啟之後的再一次重試。上半用第 17 章的「每個 worker 一個記憶體 set」，下半用 `sqlite3` 模擬共用的資料庫，event id 有唯一約束，並且讓第一次處理在 commit 前「被殺掉」。

```python
import os
import sqlite3
import tempfile

EVENT = {"id": "evt_8812", "order": "A1024", "student": "student-0457", "points": 12}


class MemoryWorker:
    """第 17 章示範用的寫法：每個 worker 自己記一個 set（重啟或換 worker 就忘了）。"""
    def __init__(self, ledger):
        self.seen, self.ledger = set(), ledger

    def handle(self, event):
        if event["id"] in self.seen:
            return "duplicate"
        self.seen.add(event["id"])
        self.ledger.append(event["points"])
        return "processed"


class DbWorker:
    """正式寫法：event id 的唯一約束與入帳在同一個交易裡，所有 worker 共用同一個資料庫。"""
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)   # 自己控制 BEGIN／COMMIT

    def handle(self, event, crash_after_insert=False):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT INTO webhook_events(event_id, order_id) VALUES (?, ?)",
                            (event["id"], event["order"]))
            self.db.execute("UPDATE wallets SET points = points + ? WHERE student = ?",
                            (event["points"], event["student"]))
            if crash_after_insert:
                raise RuntimeError("worker 在 commit 前被殺掉")
            self.db.execute("COMMIT")
            return "processed"
        except sqlite3.IntegrityError:          # 唯一約束：這個事件處理過了
            self.db.execute("ROLLBACK")
            return "duplicate"
        except RuntimeError:
            self.db.execute("ROLLBACK")         # 記錄與入帳一起回滾，留給供應商重試
            return "crashed → 回 500"


# 情境一：三台主機各 4 個 worker，重試落在不同 worker 上，又遇到一次部署重啟
ledger = []
workers = [MemoryWorker(ledger) for _ in range(12)]
log = [workers[0].handle(EVENT), workers[7].handle(EVENT)]   # 重試被分到另一個 worker
workers[7] = MemoryWorker(ledger)                            # 部署重啟：set 清空
log.append(workers[7].handle(EVENT))
print("記憶體 set：", log, f"→ 加了 {sum(ledger)} 點")

# 情境二：同樣的投遞順序，改成共用資料庫
path = os.path.join(tempfile.mkdtemp(), "live.db")
setup = sqlite3.connect(path)
setup.executescript("""
    CREATE TABLE webhook_events(event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL);
    CREATE TABLE wallets(student TEXT PRIMARY KEY, points INTEGER NOT NULL);
    INSERT INTO wallets VALUES ('student-0457', 0);
""")
setup.commit()
a, b, c = DbWorker(path), DbWorker(path), DbWorker(path)
log = [a.handle(EVENT, crash_after_insert=True),   # 第一次：處理到一半 worker 掛了
       b.handle(EVENT),                            # 供應商重試：落在另一台
       c.handle(EVENT)]                            # 部署後又重試一次
points = setup.execute("SELECT points FROM wallets").fetchone()[0]
rows = setup.execute("SELECT COUNT(*) FROM webhook_events").fetchone()[0]
print("共用資料庫：", log, f"→ 加了 {points} 點，事件紀錄 {rows} 筆")

assert sum(ledger) == 36 and points == 12 and rows == 1
for conn in (a.db, b.db, c.db, setup):
    conn.close()
```

```text
記憶體 set： ['processed', 'processed', 'processed'] → 加了 36 點
共用資料庫： ['crashed → 回 500', 'processed', 'duplicate'] → 加了 12 點，事件紀錄 1 筆
```

第 1 行是故事裡 37 位學生遇到的事：三次投遞落在三個「沒看過這個 event id」的 worker 上（其中一個是部署後剛啟動的），12 點變成 36 點。記憶體 set 在單一 process 的測試裡完全正確，所以能通過所有單元測試，卻在多 worker、會重啟的 production 出事。

第 2 行是修正版。第一次處理在 INSERT 之後、COMMIT 之前崩潰，交易回滾，event id 與點數**一起**消失，回 500 讓供應商重試；如果 event id 先另外寫入，崩潰後就會留下「記錄說處理過、點數卻沒加」的永久錯誤。第二次投遞落在另一個 worker，正常入帳；第三次撞到唯一約束，回 `duplicate`。最後點數 12、事件紀錄 1 筆。PostgreSQL 或 MySQL 寫法相同，也可以用 `INSERT … ON CONFLICT DO NOTHING` 再檢查影響的列數。

### 實驗三：API key 的產生、雜湊儲存與驗證

這個模組依 30.3 節的設計：key 的格式是 `ssk_<env>_<key id>_<secret><checksum>`，資料庫只存以 pepper 計算的 HMAC 雜湊，驗證時先檢查格式與 checksum，再用 key id 查表、constant-time 比較雜湊，最後檢查撤銷與 scope。程式最後模擬一次雙 key 並行的輪替。

```python
import hashlib
import hmac
import secrets
import zlib

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
PEPPER = b"pepper-from-secret-manager"   # 不和資料庫放在一起；資料庫外洩時多一層保護


def base62(n: int, width: int) -> str:
    out = ""
    for _ in range(width):
        n, r = divmod(n, 62)
        out = ALPHABET[r] + out
    return out


def checksum(body: str) -> str:
    return base62(zlib.crc32(body.encode()), 6)   # 不是安全機制，只用來離線抓打錯與掃描誤判


def digest(key: str) -> str:
    return hmac.new(PEPPER, key.encode(), hashlib.sha256).hexdigest()


class KeyStore:
    def __init__(self):
        self.rows = {}                            # key_id → 資料列；模擬資料表

    def issue(self, owner, scopes, env="live", now=0):
        key_id = secrets.token_hex(4)             # 公開的部分：給 log、儀表板、查詢用
        secret = base62(int.from_bytes(secrets.token_bytes(32), "big"), 43)  # 256 bit
        body = f"ssk_{env}_{key_id}_{secret}"
        key = body + checksum(body)
        self.rows[key_id] = {"owner": owner, "env": env, "scopes": set(scopes),
                             "hash": digest(key), "created": now, "last_used": None,
                             "revoked": False}
        return key                                # 明文只在這裡出現一次

    def verify(self, key, needed_scope, now):
        parts = key.split("_")
        if len(parts) != 4 or parts[0] != "ssk" or len(parts[3]) != 49:
            return "malformed"
        body, check = key[:-6], key[-6:]
        if not hmac.compare_digest(checksum(body), check):
            return "bad checksum"                 # 不必查資料庫就能擋掉打錯的 key
        row = self.rows.get(parts[2])
        computed = digest(key)                    # 找不到也照樣算，讓回應時間差不多
        if row is None or not hmac.compare_digest(row["hash"], computed):
            return "unknown key"
        if row["revoked"]:
            return "revoked"
        if needed_scope not in row["scopes"]:
            return f"missing scope {needed_scope}"
        row["last_used"] = now
        return f"ok owner={row['owner']}"


store = KeyStore()
old = store.issue("school_hsinchu", ["courses:read"], now=100)
print("發給客戶的 key：", old[:22] + "…" + old[-6:], f"（長度 {len(old)}）")
row = store.rows[old.split("_")[2]]
print("資料庫存的列：  ", {**row, "hash": row["hash"][:16] + "…", "scopes": sorted(row["scopes"])})
assert old not in str(store.rows)                 # 資料庫裡沒有明文

typo = old[:30] + ("x" if old[30] != "x" else "y") + old[31:]
results = [
    ("正確的 key，讀課程", store.verify(old, "courses:read", now=200)),
    ("同一把 key，想退款", store.verify(old, "payments:refund", now=201)),
    ("打錯一個字元", store.verify(typo, "courses:read", now=202)),
    ("通過 checksum 的偽造 key", store.verify("ssk_live_deadbeef_" + "A" * 43 + checksum("ssk_live_deadbeef_" + "A" * 43), "courses:read", now=203)),
]
new = store.issue("school_hsinchu", ["courses:read"], now=300)   # 輪替：先發新的
results += [
    ("輪替期間：舊 key", store.verify(old, "courses:read", now=310)),
    ("輪替期間：新 key", store.verify(new, "courses:read", now=311)),
]
store.rows[old.split("_")[2]]["revoked"] = True                  # 確認舊 key 沒人用了才撤銷
results += [("撤銷後：舊 key", store.verify(old, "courses:read", now=400)),
            ("撤銷後：新 key", store.verify(new, "courses:read", now=401))]
for label, outcome in results:
    print(f"{label} → {outcome}")
print("舊 key 最後使用時間：", row["last_used"], "（撤銷前先看這個欄位，確認客戶已換新）")

assert [r[1].split()[0] for r in results] == ["ok", "missing", "bad", "unknown", "ok", "ok", "revoked", "ok"]
```

```text
發給客戶的 key： ssk_live_928f199d_qWYe…2KDHmc （長度 67）
資料庫存的列：   {'owner': 'school_hsinchu', 'env': 'live', 'scopes': ['courses:read'], 'hash': 'bd388baf20cb6188…', 'created': 100, 'last_used': None, 'revoked': False}
正確的 key，讀課程 → ok owner=school_hsinchu
同一把 key，想退款 → missing scope payments:refund
打錯一個字元 → bad checksum
通過 checksum 的偽造 key → unknown key
輪替期間：舊 key → ok owner=school_hsinchu
輪替期間：新 key → ok owner=school_hsinchu
撤銷後：舊 key → revoked
撤銷後：新 key → ok owner=school_hsinchu
舊 key 最後使用時間： 310 （撤銷前先看這個欄位，確認客戶已換新）
```

key、key id 與雜湊每次執行都不同，其他輸出固定。第 1 行是發給客戶的 key，只印頭尾，就像後台在發放後只顯示前綴與末幾碼。第 2 行是資料庫那一列：有 owner、環境、scope、雜湊，沒有明文，`assert` 也確認了這一點。

接下來四行：正確的 key 讀課程通過；同一把 key 想退款，因 scope 只有 `courses:read` 被拒；打錯一個字元在 checksum 就被擋下，不必查資料庫；自己算出正確 checksum 的偽造 key 通過格式檢查，卻在雜湊比對失敗，證明 checksum 只是過濾器。最後五行是輪替：發出新 key 後兩把都能用，撤銷後只剩新 key 有效；`last_used` 顯示舊 key 最後在 310 被使用，真實系統要等它停止更新一段時間才撤銷。

## 30.10 在工作上怎麼用

事後檢討之後，Rita 和阿德把本章的內容整理成幾份檢查清單，貼在團隊的 wiki 上。

**後端工程師：接一個新的 webhook 來源。** 先從供應商文件確認：簽了哪些內容、時間窗建議值、重試策略與最長期限、輪替時會不會帶多個簽章。實作時讓 webhook 端點跳過會改寫 body 的 middleware；event id 寫進有唯一約束的資料表，和業務處理同一個交易；兩秒內回 2xx，其餘進佇列。回歸測試至少包含：正確與錯誤簽章、過期 timestamp、同一事件送兩次、含中文的 body，而且要跑完整的 middleware 堆疊。

第 17 章介紹過用 `openssl dgst -hmac` 重算簽章。到了 production，更常用的是下面這組「確認身分與 bytes」的指令（示意輸出）：

```bash
# 1. 這個 Pod 現在到底以誰的身分呼叫雲端？（排查 AccessDenied 的第一步）
kubectl -n live exec deploy/api -- aws sts get-caller-identity
# ↓ 示意輸出
{ "Arn": "arn:aws:sts::111122223333:assumed-role/live-api-recordings/botocore-session-1791000000" }

# 2. 看 Pod 掛載的 projected token 宣告了什麼（只解 payload，不驗簽，僅供除錯）
kubectl -n live exec deploy/api -- cat /var/run/secrets/kubernetes.io/serviceaccount/token \
  | cut -d. -f2 | python3 -c 'import sys,base64,json; p=sys.stdin.read().strip(); print(json.loads(base64.urlsafe_b64decode(p+"="*(-len(p)%4))))'
# ↓ 示意輸出（節錄）
{'aud': ['https://kubernetes.default.svc'], 'exp': 1791003600, 'sub': 'system:serviceaccount:live:api'}

# 3. 在 log 裡找有沒有不該出現的憑證（API key 前綴、Authorization header）
grep -rEc 'ssk_(live|test)_[0-9a-f]{8}_' /var/log/nginx/ | grep -v ':0$'
```

第一個指令回答「我是誰」：ARN 是 assumed-role，代表走的是 IAM role 的臨時憑證；若是某個 IAM user，代表有長期 key 殘留在環境裡（延伸問答 Q6）。第二個指令只把 JWT 的 payload 用 base64url 解開（第 27 章），確認 `sub`、`aud`、`exp`；它**沒有驗證簽章**，只能用來除錯。第三個指令依前綴搜尋 log，這是 30.3 節替 key 加前綴的回報：計數不是 0，就代表有 key 進了 URL 或被某個元件記下，要追查並輪替。

**平台與 SRE：選擇內部服務的驗證方式。** 新服務上線時，依下面的流程決定用什麼：

```text
 這個呼叫的雙方都在我們的平台上嗎？
   ├─ 是 ─► 平台有 mesh 或 workload identity？
   │          ├─ 有 ─► 用 mTLS／SPIFFE 身分＋授權政策（不發任何秘密）
   │          └─ 沒有 ─► 短期：每個服務一把獨立的 HMAC secret（放 secret manager）
   │                     長期：導入 workload identity
   ├─ 呼叫雲端 API ─► IAM role＋臨時憑證；禁止建立長期 access key
   └─ 否（外部合作夥伴）
          ├─ 對方呼叫我們 ─► API key（有 scope、到期、輪替流程）或 OAuth client credentials
          │                   需要防竄改或高價值操作 ─► 加上 HMAC 簽章或 mTLS
          └─ 對方通知我們（webhook）─► 驗證對方的簽章＋時間窗＋event id 去重；來源 IP 只當輔助
```

第一個分岔是「雙方是否都在自己的平台」，只有這時才能讓平台作證、完全不需要秘密；外部合作夥伴只能靠事先交換的憑證，重點轉為格式、權限、輪替與外洩應變。webhook 那一支對應故事的教訓：簽章是驗證，IP 是輔助。

**資安：API key 或 secret 外洩時的應變。** 依序是：立即撤銷（不要等「確認是否被濫用」）、發新的並協助使用方更換、從 `last_used_ip` 與存取 log 判斷外洩期間是否有異常使用、找出外洩路徑並修補（commit、log、截圖、第三方工具）、最後才是清理 git 歷史。平時要做的是：開啟 repo 的 secret scanning 與 push protection、在 CI 加入秘密掃描、log 的序列化器預設遮蔽 `Authorization`、`Cookie`、`*-Signature`、`*secret*` 等欄位、為每一把秘密登記擁有者與使用位置。

**影音工程師：推流與 TURN 也是同一件事。** Joe 的直播 ingest 用 SRT 的 stream ID 帶入推流憑證（第 38 章），TURN 常用以 HMAC 產生、帶到期時間的短效帳密（第 36 章）：不發永久有效的金鑰，讓憑證帶著到期時間並由 server 簽章。

## 30.11 常見錯誤與除錯

大多數錯誤的症狀都是「401，而且不知道為什麼」，所以第一件事是讓驗證失敗的 log 寫清楚**失敗在哪一步**（格式、時間窗、key id、簽章、nonce、scope），但不寫出秘密或完整簽章。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| webhook 突然全部 `signature mismatch` | 驗證前 body 被改寫（middleware 重新序列化、解壓縮、字元集轉換），或用錯 secret（test／live） | 記錄收到 body 的 SHA-256 與長度，和供應商後台比對；檢查最近上線的 middleware | 用框架的原始 bytes 驗證；webhook 端點排除改寫 body 的 middleware；確認環境對應的 secret |
| 部分機器的請求 401 `stale timestamp` | 時鐘偏差超過時間窗 | `timedatectl` 或 `chronyc tracking` 看偏差；log 印出 `now − ts` | 修好 NTP；監控時鐘偏差；不要用放大時間窗掩蓋 |
| 同一筆付款被處理多次 | 沒有 event id 去重，或去重和業務處理不在同一個交易 | 依 event id 查處理紀錄；看重試時間點 | 唯一約束＋同一個交易；重複時回 200 |
| 供應商一直重試已成功的事件 | handler 回應太慢（超過供應商逾時）或回了非 2xx | 供應商後台的投遞紀錄；我們的 access log 看回應時間 | 同步只做驗證與入帳，其餘進佇列；「已處理過」回 200 |
| 只靠 IP 允許清單，卻被偽造的請求通過 | 讀了 `X-Forwarded-For` 最左邊的值，或 proxy 沒有覆寫 client 帶來的 header | 用 curl 自帶 XFF 打 staging，看應用程式判定的來源 | 依信任的 proxy 從右往左解析；簽章才是驗證，IP 只是輔助 |
| 輪替 key 後某台主機凌晨開始 401 | 立刻撤銷舊 key，沒有並行期，或沒確認所有使用者都已更換 | 舊 key 的 `last_used_at` 與來源位址 | 雙 key 並行；以使用紀錄決定撤銷時間 |
| mTLS 交握失敗，`certificate required` 或 `unknown ca` | client 沒送憑證、憑證過期，或兩邊信任的 CA 不同 | `openssl s_client -cert … -key … -CAfile …`；看憑證 `notAfter` 與 SAN | 修正憑證路徑與信任的 CA；監控憑證到期；交給自動輪替 |
| 雲端 API 回 `AccessDenied`，但 role 權限看起來沒錯 | 信任政策的 `sub`／`aud` 不符，程式其實拿到了別的身分（例如環境變數裡殘留的長期 key） | 呼叫 STS 的 `get-caller-identity` 確認目前身分 | 移除殘留的 access key；修正信任政策的條件 |
| HMAC 簽章在某些請求失敗（含特殊字元的 path 或 query） | client 與 server 的 canonical 規則不一致（percent-encoding、排序、空白） | 兩邊都在 debug 模式印出 canonical request 逐行比對 | 依規格統一編碼規則；用共用的簽章函式庫，不要兩邊各寫 |

除錯 HMAC 類問題最有效的技巧是**比對 canonical request，而不是比對簽章**：簽章只告訴你「不一樣」，canonical request 告訴你「哪一行不一樣」。在 staging 讓兩邊都印出 canonical request（不含 secret）逐行 diff，通常是 path 編碼、query 排序或某個 header 被 proxy 改了。

## 30.12 動手練習

1. **延伸 30.4 節的簽章程式：非 ASCII 的 path 與重複的 query 參數**。讓 client 呼叫 `/teachers/美咲?tag=n5&tag=kaiwa`，server 端收到的 path 是已經 percent-encode 過的 `/teachers/%E7%BE%8E%E5%92%B2`、query 的順序也被 proxy 對調。修改 `canonical_request()`，讓兩邊算出相同的 canonical request。
   答案要點：canonical 形式要先把 path 解碼再用固定規則重新編碼（例如 `quote(unquote(path), safe="/")`），否則一邊簽原字元、一邊簽 `%E7…`；重複的參數要依「名稱、再依值」排序，`parse_qsl` 加 `sorted` 已經做到。驗證方法是在兩邊各印出 canonical request 逐行比對，這也是 30.11 節建議的除錯方式。

2. **延伸實驗三：撤銷前的使用量監控**。替 `KeyStore` 加上 `usage_since(key_id, t)`，回傳某時間點之後的使用次數，並寫一個 `safe_to_revoke(old_key_id, now, quiet_period)`：只有在舊 key 已經 `quiet_period` 沒被使用、且同一個 owner 有另一把有效的 key 時才回傳 True。
   答案要點：需要記錄每次使用的時間（或至少 `last_used`）；第二個條件避免把 owner 唯一的 key 撤銷。思考 quiet period 為什麼要涵蓋最長的批次週期（例如每週一次的同步工作）。

3. **看 SigV4 長什麼樣**（真實工具）。在一個終端執行 `nc -l 8765`（部分系統要寫 `nc -l -p 8765`），另一個終端執行 `curl --aws-sigv4 "aws:amz:ap-northeast-1:s3" --user "AKIDEXAMPLE:examplesecret" 127.0.0.1:8765/recordings/L-778.mp4`，在 nc 的畫面觀察 curl 送出的 header，看完按 Ctrl-C 結束兩邊（nc 不會回應）。curl 需要 7.75 以上的版本。
   答案要點：你會看到 `Authorization: AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/<日期>/ap-northeast-1/s3/aws4_request, SignedHeaders=…, Signature=…` 以及 `x-amz-date`，對照 30.4 節的結構：key id（Credential）、簽了哪些 header、時間與簽章。用的是假的 key 與本機的 nc，不會連到任何雲端服務；連續執行兩次，`x-amz-date` 與 Signature 都會改變。

4. **觀察 TLS 的 client 憑證要求**（真實工具）。找一個你有權限的內部 mTLS 服務（或在本機用 `openssl s_server -verify 1` 起一個測試 server），分別用帶與不帶 `-cert/-key` 的 `openssl s_client` 連線，比較輸出。
   答案要點：不帶 client 憑證時，交握會以 alert 失敗（訊息依版本而異，常見是 `certificate required`）；帶了憑證時連線成功。用 `-msg` 參數可以看到 server 送出的 CertificateRequest 訊息，對照 30.6 節的時序圖。

5. **設計題：聲聲 Live 發給學校的 webhook**。寫出聲聲 Live 對外 webhook 的規格：header 名稱、簽章內容、時間窗、重試策略、secret 輪替方式、學校端該如何驗證，以及送出端如何避免 SSRF。
   答案要點：參考 30.5 節的例子 callout；簽章內容至少包含事件 id、timestamp 與原始 body；重試用指數退避並保持 event id 不變；輪替時同時帶新舊簽章；送出前解析 URL 並拒絕私有、loopback、link-local 位址，且在連線時重新檢查實際連到的位址（避免 DNS 改指向）。

## 本章重點整理

- service 之間的驗證要回答三個問題：身分（是誰）、完整性（內容沒被改）、新鮮度（不是重放），驗證之後還要做授權。
- 來源 IP 允許清單只能縮小攻擊面，不能取代驗證；在 proxy 後面讀來源要依信任的 proxy 從右往左解析 `X-Forwarded-For`。
- API key 是 bearer 憑證：格式要有可辨識的前綴、公開的 key id 與 checksum，資料庫只存雜湊，明文只在發放時出現一次。
- API key 要有最小的 scope 與到期時間，放在 header 不放 URL；輪替用雙 key 並行，依 `last_used_at` 決定何時撤銷，外洩時立即撤銷。
- HMAC 請求簽章讓秘密不在網路上傳；canonical request 統一 method、path、排序後的 query、選定的 header 與 body 雜湊，讓簽章能穿過會改寫格式的 proxy。
- timestamp 擋住過期的重放，nonce 擋住時間窗內的重放；nonce 要在簽章驗證成功後才記錄，所有機器的時鐘必須同步。
- webhook 是至少一次投遞：重試會帶新的 timestamp 與簽章但相同的 event id，只有 event id 去重（唯一約束、與業務處理同一個交易）能防止重複處理。
- webhook 簽章必須對原始 bytes 驗證；任何解析後重新序列化、解壓縮或字元集轉換都會讓合法的通知驗證失敗。
- mTLS 讓 client 也出示憑證，私鑰不離開本機、憑證可以很短效；service mesh 把憑證發放、輪替與授權政策交給基礎設施，代價是複雜度與延遲。
- workload identity 由平台依可驗證的執行環境發出短效身分，解決 secret zero 問題；SPIFFE 定義了身分格式（SPIFFE ID）與載體（X.509-SVID、JWT-SVID）。
- 雲端上用 IAM role 的臨時憑證取代長期 access key，Kubernetes 用投射的 service account token 透過 workload identity federation 換取雲端憑證；權限與信任政策仍要最小化。
- 秘密不該出現在 git、映像、log 與錯誤頁；用 secret manager 依身分授權並以檔案交付，優先使用短效或動態秘密，並讓驗證端在輪替期間同時接受新舊版本。

## 延伸問答

> [!question]- Q1. API key 和密碼都只存雜湊，為什麼密碼要用 bcrypt 或 scrypt，API key 卻可以用 SHA-256？
> 慢雜湊的目的是對抗「離線猜測」：攻擊者偷到雜湊後，用字典與規則大量嘗試可能的密碼。人選的密碼熵很低，常見密碼可能只有幾十 bit 的不確定性，快雜湊每秒能算數十億次，所以要讓每次計算變慢、變耗記憶體，把猜測的成本拉高到不划算（第 26 章）。
>
> 由 `secrets` 產生的 256 bit API key 沒有這個問題：可能的值是 2²⁵⁶ 個，就算每秒算 10¹⁸ 次 SHA-256，猜中所需的時間也遠超過宇宙年齡，慢雜湊多不了任何安全性。反過來，API key 每個請求都要驗證，若用 bcrypt 每次花 100 毫秒，API 的延遲與 CPU 成本會不可接受。所以判斷依據是「秘密的熵」：低熵（人選的）用慢雜湊，高熵（機器產生的）用快雜湊即可，加上 pepper 是額外的防禦層，讓只偷到資料庫的人連驗證猜測都做不到。

> [!question]- Q2. 金流 webhook 已經有 HMAC 簽章與 5 分鐘時間窗，為什麼還需要 event id 去重？反過來，有了 event id 去重，時間窗還有必要嗎？
> 時間窗與簽章防的是「攻擊者」，event id 去重防的是「正常的重試」。供應商沒收到 2xx 時會重新投遞同一個事件，而且每次重新簽章，timestamp 是新的、簽章是合法的，時間窗與簽章完全擋不住它，也不應該擋住，因為重試是至少一次投遞的保證。只有 event id 能辨識「這是同一件事」，讓處理變成冪等，故事裡 37 位學生的重複加點，就是這一層只存在 process 記憶體裡、沒有跨 worker 與重啟的結果。
>
> 反過來，時間窗仍然必要。event id 去重紀錄雖然通常保存很久，但不是永久；而且如果攻擊者重放的是一個我們**從未成功處理**過的舊通知（例如當時驗證失敗、或被我們刻意拒絕的事件），去重表裡沒有它。時間窗讓所有錄下的訊息在幾分鐘後自動作廢，不必依賴去重表的完整性。兩者是不同層次的防線，應該同時存在。

> [!question]- Q3. 手算：你的 HMAC 簽章時間窗是 ±300 秒，每秒收到 2,000 個簽章請求，每個 nonce 在快取中佔 64 bytes（含 Redis 的額外開銷估計）。nonce 快取最多要多少記憶體？如果把時間窗放大到 ±15 分鐘呢？
> nonce 只需要保存到「它所屬的請求會被時間窗擋掉」為止。時間窗是 ±300 秒，一個 timestamp 為 ts 的請求最晚在 ts＋300 還能被接受，所以每個 nonce 記到 ts＋300 就可以刪；但 ts 本身可能比現在早最多 300 秒，也可能晚最多 300 秒（client 時鐘稍快），保守估計某一時刻快取裡最多有 600 秒的 nonce。2,000 × 600 ＝ 1,200,000 個，× 64 bytes ≈ 76.8 MB。
>
> 時間窗放大到 ±15 分鐘，保存期間變成 1,800 秒，數量 3,600,000 個，約 230 MB，是三倍。這說明了時間窗不是越寬越好：它不只擴大了重放窗口，也線性增加了 nonce 快取的成本。正確的做法是修好時鐘同步，讓時間窗維持在數分鐘；遇到時鐘偏差時，要修 NTP，而不是放寬視窗。

> [!question]- Q4. 設計取捨：同事提議 webhook 的去重改用 Redis，`SET evt_id 1 NX EX 86400`，成功才處理，「比查資料庫快」。你同意嗎？
> 這個設計有兩個問題，都和故事有關。第一是**保存期限**：24 小時的 TTL 比許多供應商的重試期限短，有些供應商會在數天內持續重試，第二天之後的重試會被當成新事件再處理一次。第二是**原子性**：Redis 的 SET 與資料庫的入帳是兩個系統，不在同一個交易裡。如果 SET 成功、入帳時 worker 被殺掉，之後所有重試都會因為 key 已存在而被當成重複，這筆付款永遠不會入帳；如果反過來先入帳再 SET，兩者之間崩潰又會造成重複入帳。
>
> 比較穩妥的做法是把去重做在業務資料所在的資料庫，用唯一約束和入帳放在同一個交易裡，30.9 節實驗二示範了崩潰時兩者一起回滾。Redis 可以當作前面的快速過濾層（例如擋掉短時間內大量重複的投遞以減輕資料庫負擔），但不能是唯一的真相來源。這題的判斷原則是：去重紀錄必須和它所保護的副作用「同生共死」，而且要活得比對方的重試期限久。

> [!question]- Q5. 面試題：mTLS 和 API key 都能驗證服務身分，mTLS 好在哪裡？什麼情況下你仍然會選 API key？
> mTLS 的身分證明是「持有私鑰」：交握時 client 用私鑰簽交握紀錄，私鑰本身從不離開本機，網路上只有公開的憑證與一次性的簽章，任何中間層的 log 都偷不到能重複使用的東西。憑證有到期時間，可以發得很短，外洩影響自然受限；驗證在 TLS 層完成，應用程式不必處理秘密。API key 則是 bearer 憑證，每個請求都整串送出，在 TLS 終結之後的任何一層被記錄就等於外洩，而且通常長期有效。
>
> 但 mTLS 需要 CA、憑證發放、輪替與到期監控，這些成本必須有人承擔。對外的合作夥伴 API，要求每個客戶管理 client 憑證，往往會把營運負擔轉嫁給技術能力參差的對方，也可能因為對方的 TLS 終結在 CDN 或 LB 而難以實施。所以對外的 B2B API 常用 API key 或 OAuth client credentials，搭配 scope、到期與輪替；內部服務在有 mesh 或 workload identity 的平台上則優先用 mTLS。高價值的金融 API 也常要求 mTLS，因為那裡值得付出成本。

> [!question]- Q6. 看 log 找原因：你的服務在雲端呼叫物件儲存，log 顯示 `AccessDenied`，但團隊確認 Pod 的 IAM role 有寫入權限。下面是 SDK 的 debug log 片段，可能是什麼原因？「Found credentials in environment variables」。
> 這行 log 是關鍵：SDK 依一個固定順序尋找憑證，通常環境變數排在 web identity token 與 instance metadata 之前。它說「在環境變數找到憑證」，代表程式用的根本不是 Pod 的 IAM role，而是某組殘留的長期 access key，例如某人除錯時在 Deployment 裡加了 `AWS_ACCESS_KEY_ID`，或映像裡帶了舊的設定。那組 key 屬於另一個身分，當然沒有這個 bucket 的權限。
>
> 確認方法是在 Pod 裡呼叫 STS 的 get-caller-identity，看目前的身分是 role 還是某個 IAM user。修正方式是移除環境變數裡的 key（並撤銷那組 key，因為它曾出現在設定裡），讓 SDK 走 web identity 的路徑。這個案例也說明了為什麼應該在組織層級禁止建立長期 access key：只要存在，就可能在你沒注意的地方取代了你以為在用的身分。

> [!question]- Q7. 設計取捨：有人提議「內部服務的 HMAC secret 乾脆所有服務共用一把，管理比較簡單」。你會怎麼回應？
> 共用一把 secret 讓管理在「發放」這一刻變簡單，卻讓其他所有事情變困難。第一，身分消失了：用共用 secret 簽的請求，接收方只知道「是某個持有 secret 的服務」，無法分辨是 api 還是 chat，也就無法給不同服務不同權限，稽核 log 也失去意義。第二，影響範圍最大化：任何一個服務外洩，攻擊者就能冒充所有服務呼叫所有服務。第三，輪替最困難：要所有服務同時更新，任何一個漏掉就中斷，結果往往是永遠不輪替，正如故事裡三年沒換的 `RECO_API_KEY`。
>
> 比較好的回應是「每個呼叫方一把，帶 key id」：接收方用 key id 找到對應的 secret，同時得知呼叫方身分，可以依身分授權；輪替與撤銷都只影響一個服務。管理成本交給 secret manager 自動化。若平台已有 mesh 或 workload identity，更好的答案是不用 HMAC secret，直接用平台發的身分。

> [!question]- Q8. 情境題：Rita 發現一位實習生把含有 `ssk_live_` key 的設定檔 push 到公開的 GitHub repo，十分鐘後刪掉了那個 commit。接下來該怎麼做？順序重要嗎？
> 順序非常重要，第一步是**立即撤銷那把 key**，而不是清理 git 歷史或先調查。公開 repo 上的秘密可能在數秒到數分鐘內就被自動化工具掃描到，刪掉 commit 並不會讓已經 clone、已經被快取、已經被掃描到的副本消失。撤銷之後，馬上為該 owner 發新 key 並協助更換；這是緊急輪替，不能用雙 key 並行期，因為並行期就是攻擊者的窗口。
>
> 接著才是調查與清理：用 key id 查存取 log 與 `last_used_ip`，判斷外洩期間有沒有來自陌生位址的使用、做了哪些操作；檢查同一個設定檔裡是否還有其他秘密，一併輪替；最後再清理 git 歷史，並開啟 secret scanning 與 push protection，讓 `ssk_` 前綴在 push 時就被擋下。事後檢討要問的是「為什麼設定檔裡會有正式環境的 key」，答案通常指向 secret 應該由 secret manager 交付、而不是放在任何會被 commit 的檔案裡。

## 延伸閱讀

- RFC 2104〈HMAC: Keyed-Hashing for Message Authentication〉：HMAC 的原始定義
- RFC 9421〈HTTP Message Signatures〉：通用 HTTP 訊息簽章的標準化方式
- RFC 8705〈OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens〉：在 OAuth 中使用 mTLS 驗證 client
- SPIFFE 規範〈SPIFFE ID〉〈X509-SVID〉〈JWT-SVID〉〈Workload API〉：工作負載身分的格式與取得方式
- AWS 文件〈Signature Version 4 signing process〉與〈Use IMDSv2〉：真實世界的請求簽章與 metadata 防護
- Kubernetes 文件〈Service Account Token Volume Projection〉：投射的 service account token
- OWASP〈Secrets Management Cheat Sheet〉：秘密的存放、交付、輪替與外洩應變
