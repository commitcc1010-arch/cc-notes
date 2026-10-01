---
chapter: 12
title: IAM：身份、權限與 Policy 評估邏輯
part: 2
---

# 第 12 章　IAM：身份、權限與 Policy 評估邏輯

> [!abstract] 本章地圖
> **你會學到**：
> - 把一個 AWS 請求拆成 principal、action、resource、context 四個元素，並分辨「憑證錯了」（簽章失敗）與「policy 不允許」（AccessDenied）兩種失敗
> - 說清楚 root user、IAM user、group、role 的差別，以及「人」與「程式」各自該用哪一種身份
> - 讀懂並寫出一份 IAM policy JSON，知道 Effect、Action、Resource、Condition、Principal 每個欄位在做什麼
> - 分辨 identity-based 與 resource-based policy、AWS managed／customer managed／inline policy，並選對類型
> - 一步一步推演 AWS 怎麼決定一個請求「允許」還是「拒絕」，包含 SCP、permissions boundary、session policy 的交集效果
> - 用 instance profile、`iam:PassRole`、condition keys、ABAC 設計最小權限，並用 IAM Access Analyzer 與 credential report 持續收斂權限
>
> **前置知識**：第 2 章（AWS 帳號與 root user）、第 4 章（API 與 stateless 的概念）
> **考試比重**：SAA ★★★（Domain 1 安全，task 1.1 幾乎每份考卷都有）｜SAP ★★★（Domain 1、2、3 的安全控制與改善題）

## 12.1 故事：一把被推上 GitHub 的鑰匙

Part 1 走到第 11 章，Wanderly 的網路已經從 VPC 一路鋪到 CloudFront：封包走哪條路、誰能從外面連進來，都說得清楚了。但那七章管的全是「網路層能不能通」。還有一個完全不同的問題從創業第一天就沒人管過：**誰可以對 AWS 本身下指令**。能呼叫 API 的人不必經過你的 security group，網路做得再緊也擋不住一組外洩的金鑰。

Wanderly 創業第一年，帳號裡只有一組登入方式：註冊 AWS 時用的那個 email 和密碼，也就是 **root user**。三位工程師共用這組密碼登入 console；為了讓訂房程式能把照片上傳到 S3，小林還在 root user 底下產生了一組 **access key**（長期有效的程式金鑰），直接寫進設定檔。

某個週五晚上，實習生把整個專案推到一個公開的 GitHub repository。不到二十分鐘，帳號在好幾個 Region 被開出上百台大型 EC2 挖礦。AWS 寄來可疑活動通知，小林手忙腳亂停用金鑰，週一收到一張遠超過預算的帳單。事後檢討時，技術主管問了三個問題：為什麼一組程式用的金鑰能做「任何事」？為什麼這組金鑰永遠不會過期？為什麼出事後我們說不出「是誰、在什麼時候、做了什麼」？

這三個問題對應到本章的三個核心觀念。第一，**權限要最小化**：上傳照片的程式只該能寫某個 bucket 的某個資料夾。第二，**憑證要短期化**：程式應該使用會自動過期、自動更新的臨時憑證，而不是寫死的長期金鑰。第三，**身份要可追溯**：每個人、每個程式都要有自己的身份，稽核紀錄才有意義。

AWS 用來實現這三件事的服務就是 **IAM（Identity and Access Management，身份與存取管理）**。這一章從「誰在呼叫 AWS」開始，接著學會讀寫 policy，最後把 AWS 判斷一個請求能不能執行的完整邏輯畫成流程圖。第 13 章再把範圍擴大到跨帳號與企業登入。

## 12.2 每一次 API 呼叫都要回答兩個問題

在 AWS 上做任何事，不論是在 console 點按鈕、用 CLI 下指令、還是程式透過 SDK 呼叫，最後都會變成一個送到 AWS 服務的 **API 請求**。例如「上傳一個檔案到 S3」就是對 S3 發出 `PutObject` 請求。每個請求進來時，AWS 都要回答兩個問題：

1. **Authentication（驗證）：你是誰？** 請求必須用某組憑證簽章。AWS 驗證簽章後，就知道這個請求來自哪一個 **principal**（主體，也就是發出請求的身份，例如某個 IAM user 或某個 role 的 session）。
2. **Authorization（授權）：你可以做這件事嗎？** 知道是誰之後，AWS 收集所有與這個請求相關的 **policy**（權限規則文件），依照固定的評估邏輯算出「允許」或「拒絕」。

這兩件事要分開想。很多除錯困難來自混在一起：`InvalidClientTokenId` 或 `SignatureDoesNotMatch` 是驗證失敗（憑證錯了或過期），而 `AccessDenied`／`UnauthorizedOperation` 是授權失敗（身份沒問題，但 policy 不允許）。前者要檢查憑證，後者要檢查 policy。

一個請求在授權階段會被拆成四個元素，後面所有的 policy 都在描述這四件事的組合：

| 元素 | 意思 | 例子 |
|---|---|---|
| Principal | 誰發出請求 | `arn:aws:iam::111122223333:role/photo-uploader` |
| Action | 要做什麼操作 | `s3:PutObject` |
| Resource | 對哪個資源 | `arn:aws:s3:::wanderly-photos/hotels/123.jpg` |
| Context（情境） | 請求的其他屬性 | 來源 IP、是否用了 MFA、時間、Region、是否走 HTTPS、身份與資源上的 tag |

第 2 章提過的 **ARN（Amazon Resource Name）** 在這裡要看清楚格式了。它是 AWS 用來唯一識別資源的字串，寫成 `arn:partition:service:region:account-id:resource`。IAM 是 global（全域）服務，所以 IAM 資源的 ARN 沒有 Region 欄位（`arn:aws:iam::111122223333:role/...` 中間是空的）；S3 bucket 名稱全球唯一，所以 bucket ARN 連帳號都省略了。

> [!note] IAM 是全域服務，而且是 eventually consistent
> 在 IAM 建立的 user、role、policy 在所有 Region 都有效，不需要每個 Region 各建一份。但 IAM 的變更會複寫到全球的端點，剛建立或修改的 policy 可能要幾秒後才生效。自動化腳本「建好 role 立刻使用」偶爾失敗，原因常常就是這個，解法是加上重試。

## 12.3 身份的種類：root user、IAM user、group 與 role

知道每個請求都要對應一個 principal 之後，下一個問題是：AWS 帳號裡有哪些身份可以用？它們各自適合誰？

### Root user：只在少數場合使用的萬能鑰匙

**Root user** 是建立 AWS 帳號時的那個 email 身份。它對帳號內所有資源擁有完整權限，而且**無法用 IAM policy 限制**（在 Organizations 的成員帳號中，SCP 可以限制它，見第 14 章）。正因為它無法被收斂，root user 外洩就等於整個帳號外洩。

有一小部分工作只有 root user 能做，例如：變更帳號的 root email 與帳號設定、關閉帳號、變更 AWS Support 方案、在誤設定的 bucket policy 把所有人鎖在外面時修復它、在 IAM 管理員全部失去權限時恢復權限。除此之外，日常工作都不該使用 root user。

保護 root user 的標準清單：

- 啟用 **MFA（Multi-Factor Authentication，多因素驗證）**：登入時除了密碼，還需要第二個因素，例如手機上的驗證器 App 產生的一次性密碼，或支援 FIDO2 的 passkey／實體安全金鑰。AWS 已逐步要求 root user 必須啟用 MFA，實體安全金鑰是最能抵抗釣魚的選擇。
- **不要為 root user 建立 access key**；若已存在，刪除它。
- 使用一個由團隊共管、而不是個人信箱的 email，並設定強密碼。
- 建立日常使用的管理員身份（第 13 章的 IAM Identity Center，或小型帳號中的 IAM 管理員），之後把 root 密碼與 MFA 裝置鎖起來。
- 用 CloudTrail 與 alarm 監控 root user 登入（第 16、36 章）。

### IAM user：有長期憑證的個別身份

**IAM user** 是在帳號內建立的身份，可以擁有兩種**長期憑證（long-term credentials）**：

- **Console 密碼**：給人用 console 登入。可以設定帳號層級的 password policy（長度、複雜度、到期）。
- **Access key**：由 access key ID 與 secret access key 組成，給 CLI 或程式簽章 API 請求用。每個 IAM user 最多有兩組 access key（方便輪替：先建新的、切換、再停用舊的）。

「長期」是 IAM user 的根本問題：access key 不會自己過期，被寫進程式碼、設定檔、CI 系統或某人的筆電後，就很難確定還有誰持有。這正是 Wanderly 事故的根源。所以 AWS 現在的建議是：

- **人**：透過 IAM Identity Center 或企業 IdP 聯合登入，取得臨時憑證（第 13 章），不要每人一個 IAM user。
- **在 AWS 上跑的程式**：用 role（下面會講），完全不需要 access key。
- **在 AWS 外跑的程式**（地端伺服器、其他雲）：優先用 IAM Roles Anywhere 或 OIDC 聯合取得臨時憑證（第 13 章）；真的只能用 access key 時，權限壓到最小並定期輪替。

IAM user 仍然存在合理用途，例如少數無法使用聯合登入的第三方工具，或緊急存取（break-glass）帳號。

### IAM group：方便管理，但不是身份

**IAM group** 是一群 IAM user 的集合。把 policy 附加在 group 上，group 裡的所有 user 都會繼承這些權限；新人加入 `developers` group 就自動得到開發者權限，離職時從 group 移出即可。

要記住 group 的三個限制：

1. Group **不是 principal**：它沒有自己的憑證，不能「以 group 的身份」登入，也不能在 resource-based policy 的 `Principal` 欄位寫 group。
2. Group **不能巢狀**：group 裡面只能放 user，不能放另一個 group。
3. Group 只能放 IAM user，不能放 role。

### IAM role：會被「扮演」的身份，只發臨時憑證

**IAM role** 是一個帶有權限、但**沒有長期憑證**的身份。它不屬於特定的人，而是讓「被允許的對象」去**扮演（assume）** 它。扮演成功時，AWS 的 **STS（Security Token Service，安全權杖服務）** 會發一組臨時憑證：access key ID、secret access key、session token 與到期時間。這組憑證過期後就失效，即使外洩，影響時間也有限。

每個 role 有兩份性質不同的 policy，這是理解 role 的關鍵：

| | Trust policy（信任政策） | Permissions policy（權限政策） |
|---|---|---|
| 回答的問題 | **誰**可以扮演這個 role？ | 扮演之後**能做什麼**？ |
| 性質 | Role 的 resource-based policy，必須有 `Principal` | Identity-based policy，沒有 `Principal` |
| 例子 | 允許 EC2 服務、Lambda 服務、另一個帳號、某個 IdP 來扮演 | 允許讀寫某個 S3 bucket |

Role 可以被以下對象扮演：

- **AWS 服務**：EC2、Lambda、ECS task 等服務代替你的程式扮演 role（本章 12.8 節）。
- **同帳號或其他帳號的 IAM principal**：跨帳號存取的標準做法（第 13 章）。
- **外部身份**：透過 SAML 2.0 或 OIDC 聯合登入的使用者，例如企業目錄的員工、GitHub Actions 的 workflow（第 13 章）。

> [!warning] 常見誤解
> 「Role 是一種 group。」不是。Group 是把權限「發給」一群 user 的管理工具，user 永遠用自己的身份；role 是一個獨立的身份，扮演它的人在那段 session 中**暫時放下原本的身份與權限**，換成 role 的權限。在 CloudTrail 中，這個 session 會顯示為 `assumed-role/角色名稱/session 名稱`。

## 12.4 Policy 的 JSON 結構：一份 policy 怎麼讀

有了身份之後，下一步是告訴 AWS「這個身份可以做什麼」。IAM 的權限都寫在 **policy** 裡，policy 是一份 JSON 文件。先看一份完整的例子：Wanderly 的照片上傳程式只能在 `wanderly-photos` bucket 的 `hotels/` 資料夾讀寫物件，並能列出這個資料夾。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListHotelPrefixOnly",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::wanderly-photos",
      "Condition": {
        "StringLike": {
          "s3:prefix": ["hotels/*"]
        }
      }
    },
    {
      "Sid": "ReadWriteHotelPhotos",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::wanderly-photos/hotels/*"
    }
  ]
}
```

逐欄說明：

- **`Version`**：policy 語言版本。永遠寫 `"2012-10-17"`，這是目前的版本；寫舊版本會讓 `${aws:username}` 這類 policy variable 無法運作。它不是日期，不用改成今天。
- **`Statement`**：一個或多個陳述句的陣列。每個 statement 是一條獨立規則，彼此沒有先後順序之分（下一節會解釋為什麼順序不重要）。
- **`Sid`**：選填的說明標籤，方便人讀與除錯。
- **`Effect`**：`Allow` 或 `Deny`，沒有第三種。
- **`Action`**：允許或拒絕的 API 操作，格式是 `服務前綴:操作名稱`，可以用萬用字元，例如 `s3:Get*`。也可以用 **`NotAction`** 表示「除了這些操作以外的所有操作」。
- **`Resource`**：作用的資源 ARN，可以用 `*` 萬用字元。也有 **`NotResource`**。
- **`Condition`**：選填，只有條件成立時這條 statement 才生效（12.7 節詳談）。
- **`Principal`**：只出現在 resource-based policy（例如 bucket policy、role 的 trust policy），指定這條規則適用於誰。附加在 user／role 上的 identity-based policy 不寫 `Principal`，因為「誰」就是被附加的那個身份。

### 看懂這份 policy 的兩個細節

第一，`s3:ListBucket` 的 Resource 是 **bucket 本身**（`arn:aws:s3:::wanderly-photos`），而 `GetObject`／`PutObject` 的 Resource 是 **bucket 裡的物件**（`arn:aws:s3:::wanderly-photos/hotels/*`）。這是 SAA 最常考的 policy 錯誤：把 `ListBucket` 寫在 `/*` 上，結果能讀檔卻不能列目錄。每個 action 作用在哪種資源上，由該服務決定，可以在 AWS 的 Service Authorization Reference 查到。

第二，限制「只能列出 `hotels/` 底下」是用 `s3:prefix` condition 做的，因為 `ListBucket` 的資源是整個 bucket，無法在 Resource 欄位指定資料夾。

### 多個值、多個條件時的邏輯

| 寫法 | 邏輯 |
|---|---|
| `Action` 陣列有多個值 | OR：符合任一個 action 即可 |
| `Resource` 陣列有多個值 | OR |
| 同一個 condition key 有多個值 | OR：符合任一值即可 |
| 同一個 condition operator 下有多個 key | AND：每個 key 都要符合 |
| 多個 condition operator | AND |
| 多條 statement | 各自獨立評估，再依 12.6 節的邏輯合併 |

> [!warning] 常見誤解：`NotAction` 搭配 `Allow`
> `"Effect": "Allow", "NotAction": "iam:*", "Resource": "*"` 的意思是「允許 IAM 以外的**所有**操作」，等於接近管理員權限，而不是「拒絕 IAM」。`NotAction` 最安全的用法是搭配 `Deny`，例如「拒絕在核准 Region 以外呼叫的所有操作，但排除 IAM、CloudFront 這類全域服務」（第 14 章的 SCP 範例）。

## 12.5 Policy 的種類：附加在誰身上、由誰管理

同樣的 JSON 語法，可以附加在不同地方，效果也不同。這一節先把種類分清楚，下一節才能理解它們怎麼合併。

### Identity-based vs resource-based

- **Identity-based policy（身份型政策）**：附加在 IAM user、group 或 role 上，描述「這個身份可以對哪些資源做什麼」。沒有 `Principal` 欄位。
- **Resource-based policy（資源型政策）**：附加在資源上，描述「哪些 principal 可以對我做什麼」。必須有 `Principal` 欄位。常見的有 S3 bucket policy、SQS queue policy、SNS topic policy、KMS key policy、Lambda function 的 resource policy、Secrets Manager secret policy、ECR repository policy，以及 IAM role 的 trust policy。

下面是一份 bucket policy：只允許 Wanderly 的照片處理 role 讀取，並且拒絕任何不走 HTTPS 的請求。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowPhotoProcessorRead",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111122223333:role/photo-processor"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::wanderly-photos/*"
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::wanderly-photos",
        "arn:aws:s3:::wanderly-photos/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

Resource-based policy 最重要的能力是**跨帳號授權**：它可以把 `Principal` 寫成另一個帳號的身份，讓對方不必先扮演你帳號的 role 就能直接存取（第 13 章會比較這兩種跨帳號方式）。

### AWS managed、customer managed 與 inline

Identity-based policy 依「誰管理、能否重用」再分三種：

| 類型 | 誰建立與維護 | 能否附加到多個身份 | 適合 |
|---|---|---|---|
| **AWS managed policy** | AWS，會隨新服務自動更新 | 可以 | 快速起步、標準職能（例如 `ReadOnlyAccess`、`AdministratorAccess`、`PowerUserAccess`、`ViewOnlyAccess`） |
| **Customer managed policy** | 你自己 | 可以 | 公司自訂、需要最小權限且要在很多 role 重用的權限 |
| **Inline policy** | 你自己，直接嵌在某個身份裡 | 不行，與身份同生同死 | 嚴格一對一、不希望被誤附加到別的身份的權限 |

選擇的原則：

- AWS managed policy 方便，但通常比實際需要寬，而且 AWS 更新它時你的權限也跟著變。適合起步，不適合當作最終的最小權限。
- Customer managed policy 是大多數情況的最佳選擇：集中修改一次，所有附加它的身份同時生效；它有版本（最多保留 5 個版本），改壞了可以切回舊版本。
- Inline policy 適合「這份權限只屬於這個 role，刪除 role 時也要一起消失」的情境，但數量多了就很難稽核。

> [!note] 大小與數量限制
> Policy 有字元數上限（customer managed policy 為 6,144 個字元，不含空白），每個 user／role 可附加的 managed policy 數量也有限制（預設 10 個，可申請提高）。設計時與其堆疊大量 policy，不如依職能整理成少數幾份。

### 其他會影響權限的 policy 類型

除了上面兩大類，還有幾種「不授權、只設上限」的 policy，下一節的評估邏輯會用到：

- **Permissions boundary（權限邊界）**：附加在 user 或 role 上的一份 managed policy，定義這個身份「最多」能擁有的權限。
- **SCP（Service Control Policy）** 與 **RCP（Resource Control Policy）**：AWS Organizations 的政策，分別限制帳號內 principal 能做的事、以及帳號內資源能被誰存取的上限（第 14 章）。
- **Session policy**：扮演 role 或建立聯合 session 時傳入的 policy，只限制這一次 session 的權限。
- **ACL（Access Control List）**：S3 等少數服務的舊式跨帳號授權機制。新建的 S3 bucket 預設停用 ACL（Object Ownership 設為 Bucket owner enforced），一般不再使用（第 22 章）。

## 12.6 Policy 評估邏輯：AWS 怎麼決定允許或拒絕

現在一個請求可能同時牽涉好幾份 policy：user 自己的、它所屬 group 的、資源上的、Organizations 的、permissions boundary……AWS 怎麼把它們合併成一個答案？這是本章最重要、也是 SAA 與 SAP 都一定會考的一節。

### 三條基本規則

先記住三條規則，後面的流程圖只是把它們排出順序：

1. **預設拒絕（implicit deny）**：沒有任何 policy 明確允許，就是拒絕。新建的 IAM user 什麼都不能做。
2. **明確拒絕永遠優先（explicit deny wins）**：只要任何一份適用的 policy 有符合的 `Deny`，不論其他地方有多少 `Allow`，結果都是拒絕。
3. **上限類 policy 只能縮小、不能放大**：SCP、RCP、permissions boundary、session policy 本身不授予任何權限。它們像篩子，請求必須同時通過每一道篩子，**還要**有 identity-based 或 resource-based policy 真正給出 `Allow`。

因為有規則 2，statement 的順序完全不重要：AWS 不是「由上往下找到第一條符合的規則就停」，而是收集所有符合的 statement，只要其中有 Deny 就拒絕。這點和第 6 章的 NACL（依規則號碼由小到大、第一條符合即停）完全不同。

### 單一帳號內的評估流程

```text
                請求進來：principal + action + resource + context
                                      │
                                      ▼
       ① 所有適用的 policy 中，有沒有符合的 explicit Deny？ ── 有 ──► 拒絕
                                      │ 沒有
                                      ▼
       ② 帳號在 Organizations 中？SCP 允許這個 action？
          資源帳號的 RCP 允許？                          ── 不允許 ──► 拒絕
                                      │ 允許（或不在 Organizations）
                                      ▼
       ③ 資源有 resource-based policy，且它 Allow
          這個 principal？                               ── 是 ──► 允許 *
                                      │ 否
                                      ▼
       ④ Identity-based policy（user／group／role）
          有 Allow？                                     ── 否 ──► 拒絕
                                      │ 是
                                      ▼
       ⑤ 這個身份有 permissions boundary？
          boundary 也允許這個 action？                   ── 不允許 ──► 拒絕
                                      │ 允許（或沒有 boundary）
                                      ▼
       ⑥ 這是帶有 session policy 的 session？
          session policy 也允許？                        ── 不允許 ──► 拒絕
                                      │ 允許（或沒有 session policy）
                                      ▼
                                    允許

  * 同帳號內，resource-based policy 的 Allow 不需要 identity-based policy 再允許一次；
    但若它的 Principal 寫的是 role ARN，該 role 的 permissions boundary 與 session policy
    仍會限制結果。KMS key policy 與 role trust policy 有各自的特殊規則（見下文）。
```

逐步解說：

① **先找 explicit Deny。** AWS 會檢查所有類型的 policy（identity、resource、SCP、RCP、boundary、session），只要有一條符合的 Deny，評估立刻結束。這是為什麼「用一條 Deny 擋住危險操作」是最可靠的防護。

② **Organizations 的上限。** 如果帳號屬於 AWS Organizations，請求者帳號的 SCP 必須允許這個 action，資源所在帳號的 RCP 也必須允許。從 root 到帳號路徑上每一層（root、OU、帳號）的 SCP 都要允許，任何一層沒有允許就是 implicit deny。SCP 不影響 management account 與 service-linked role，細節在第 14 章。

③ **Resource-based policy。** 在同一個帳號內，如果資源上的 policy 直接允許這個 principal，請求就可以被允許，即使這個 user 的 identity-based policy 沒有提到這個資源。這是「同帳號內 identity 與 resource 是聯集（union）」的意思。

④ **Identity-based policy。** 如果 resource-based policy 沒有允許，就要靠 user／group／role 上的 policy 給出 Allow。一個 user 的有效 identity 權限是它自己的 policy 加上所有 group 的 policy 的聯集。

⑤ **Permissions boundary。** 若身份設了 boundary，identity-based policy 允許的 action 還必須落在 boundary 內。有效權限是兩者的**交集**。

⑥ **Session policy。** 若這次 session 傳入了 session policy，有效權限再和 session policy 取交集。

### 把結果畫成集合

```text
  ┌──────────── SCP（帳號的上限）───────────────────────┐
  │       ┌────── Permissions boundary（身份的上限）─────┼────┐
  │       │       ┌──── Session policy（這次 session）───┼──┐ │
  │  ┌────┼───────┼─────────┐                            │  │ │
  │  │    │       │ ███████ │◄── 有效權限：               │  │ │
  │  │    │       │ ███████ │    四者都允許的交集         │  │ │
  │  │    │       └─────────┼──────────────────────────────┼──┘ │
  │  │    └─────────────────┼──────────────────────────────┼────┘
  │  │ Identity-based policy│（真正授權的來源）            │
  │  └──────────────────────┘                              │
  └────────────────────────────────────────────────────────┘
  再減去任何地方的 explicit Deny
```

圖中只有 identity-based policy（或 resource-based policy）是「授權來源」，其他三個框都是「上限」。所以「我在 SCP 裡寫了 Allow s3:*，為什麼使用者還是不能讀 S3？」答案是 SCP 不授權，使用者自己的 policy 還是得 Allow。反過來，「使用者有 `AdministratorAccess`，為什麼不能在某個 Region 開機器？」答案是上限之一沒有允許，或有 explicit Deny。

### 跨帳號時：兩邊都要同意

當 principal 在帳號 A、資源在帳號 B 時，規則變得更嚴格：**A 這一側必須允許（A 的 identity-based policy、A 的 SCP、boundary 等），B 這一側也必須允許（B 資源上的 resource-based policy、B 的 RCP）。** 兩邊是交集，不是聯集。只在 B 的 bucket policy 寫了允許 A 的 role，A 的 role 自己卻沒有 `s3:GetObject` 權限，請求一樣被拒絕。第 13 章會用完整例子演練。

### 兩個特殊的 resource-based policy

- **KMS key policy**：KMS key 的存取一定要 key policy 允許。key policy 可以直接列出 principal，或寫一條把權限「委派給帳號 IAM」的 statement（Principal 是帳號本身），之後 IAM policy 才有作用。沒有這條委派時，就算 IAM policy 給了 `kms:Decrypt` 也沒用（第 15 章）。
- **Role trust policy**：扮演 role 時，trust policy 必須允許呼叫者；跨帳號時，呼叫者自己的 identity-based policy 也要允許 `sts:AssumeRole`（第 13 章）。

### 用一個例子走一遍

Wanderly 的 `analyst` user 屬於 `analytics` group。group 的 policy 允許 `s3:GetObject` 於 `wanderly-reports/*`；user 自己有一份 inline policy 寫著 Deny `s3:GetObject` 於 `wanderly-reports/finance/*`；帳號不在 Organizations；沒有 boundary。

- 讀 `wanderly-reports/daily/2026-09-30.csv`：① 沒有符合的 Deny（Deny 只針對 `finance/`）；② 不適用；③ 沒有 bucket policy 允許；④ group policy 允許 → **允許**。
- 讀 `wanderly-reports/finance/q3.xlsx`：① inline policy 的 Deny 符合 → **拒絕**，不論 group 怎麼允許。
- 執行 `s3:PutObject` 到 `wanderly-reports/daily/x.csv`：① 沒有 Deny；④ 沒有任何 Allow 涵蓋 PutObject → **implicit deny**。

> [!tip] 考試提示
> 題目描述一個權限很大的身份（例如 `AdministratorAccess`）卻被拒絕時，答案幾乎都是「某處有 explicit Deny」或「某個上限（SCP、boundary、session policy）沒有允許」。若選項說「再加一條更具體的 Allow 就能蓋過 Deny」，一定是錯的。

## 12.7 Condition：讓權限看「情境」

前面的 policy 只看「誰、做什麼、對哪個資源」。實務上還需要更細的規則：只能從公司網路呼叫、只能在東京 Region 開機器、刪除前必須用過 MFA、只能存取和自己同專案的資源。這些都靠 **condition** 實現。

### Condition 的寫法

```text
"Condition": {
  "條件運算子": {
    "condition key": "值或值陣列"
  }
}
```

**Condition key** 是請求情境中的某個屬性。以 `aws:` 開頭的是 **global condition key**（所有服務都可能提供），以服務前綴開頭的是服務專屬 key（例如 `s3:prefix`、`ec2:InstanceType`、`iam:PassedToService`）。**條件運算子** 決定怎麼比較，常用的有：

| 運算子 | 用途 | 例子 |
|---|---|---|
| `StringEquals`／`StringNotEquals` | 字串完全相等（區分大小寫） | Region、tag 值 |
| `StringLike` | 支援 `*`、`?` 萬用字元 | S3 prefix |
| `ArnEquals`／`ArnLike` | 比較 ARN | `aws:SourceArn` |
| `IpAddress`／`NotIpAddress` | CIDR 範圍 | `aws:SourceIp` |
| `Bool` | 布林 | `aws:SecureTransport`、`aws:MultiFactorAuthPresent` |
| `NumericLessThan` 等 | 數字比較 | `aws:MultiFactorAuthAge` |
| `DateGreaterThan` 等 | 時間比較 | `aws:CurrentTime`、`aws:TokenIssueTime` |
| `Null` | 判斷 key 是否存在 | 要求請求必須帶某個 tag |
| `...IfExists` 後綴 | key 不存在時視為符合 | `BoolIfExists` |
| `ForAnyValue:`／`ForAllValues:` 前綴 | 比較多值 key（例如一次帶多個 tag key） | `aws:TagKeys` |

### 考試最常見的 global condition keys

| Condition key | 意思 | 典型用途 |
|---|---|---|
| `aws:SourceIp` | 請求來源的 public IP | 只允許從公司出口 IP 呼叫 |
| `aws:SourceVpce`／`aws:SourceVpc` | 請求經過哪個 VPC endpoint／VPC | Bucket 只接受從指定 endpoint 來的請求（第 6 章） |
| `aws:RequestedRegion` | 請求呼叫的 Region | 限制只能在核准 Region 操作 |
| `aws:MultiFactorAuthPresent` | 這組臨時憑證是否經過 MFA | 危險操作要求 MFA |
| `aws:SecureTransport` | 是否用 HTTPS | 拒絕明文傳輸 |
| `aws:PrincipalOrgID` | Principal 所屬的 Organization ID | Resource policy 只允許自家組織的帳號（第 13 章） |
| `aws:PrincipalTag/鍵` | 呼叫者身份上的 tag | ABAC |
| `aws:ResourceTag/鍵` | 目標資源上的 tag | ABAC |
| `aws:RequestTag/鍵`、`aws:TagKeys` | 請求中要建立或修改的 tag | 強制建立資源時必須帶 tag |
| `aws:SourceArn`／`aws:SourceAccount` | AWS 服務代表哪個資源／帳號發出請求 | 防止跨服務的 confused deputy（第 13 章） |
| `aws:PrincipalArn` | 呼叫者的 ARN | 在 Deny 中排除特定管理 role |
| `aws:ViaAWSService`、`aws:CalledVia` | 是否由 AWS 服務代為發出 | 讓 CloudFormation 等服務代呼叫時不被 IP 條件擋住 |

### 例子：刪除資源前必須使用 MFA

Wanderly 要求：任何人終止 EC2 instance 或刪除 S3 物件，都必須是用 MFA 登入的 session。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDestructiveActionsWithoutMfa",
      "Effect": "Deny",
      "Action": [
        "ec2:TerminateInstances",
        "s3:DeleteObject"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

為什麼用 `BoolIfExists` 而不是 `Bool`？因為用**長期 access key** 直接簽章的請求，根本不會帶 `aws:MultiFactorAuthPresent` 這個 key。如果寫 `Bool`，key 不存在時條件不成立，Deny 就不會套用，等於讓長期金鑰繞過 MFA 要求。`BoolIfExists` 的意思是「key 存在且為 false，或 key 不存在」都視為符合，因此兩種情況都會被拒絕。

### 例子：只能在核准的 Region 開機器

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEc2OnlyInTokyo",
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-1"
        }
      }
    }
  ]
}
```

這份 Allow 只對單一身份有效。若要對**整個帳號或整個 OU** 強制 Region 限制，應該用 SCP 寫 Deny（第 14 章），因為 identity policy 可能被別的 policy 用 Allow 補上，而 explicit Deny 不會被蓋過。

> [!warning] 常見誤解：`aws:SourceIp` 的兩個盲點
> 1. 請求經過 **VPC endpoint** 時，請求情境中**根本沒有** `aws:SourceIp` 這個 key（發出請求的私有 IP 改放在 `aws:VpcSourceIp`），所以「只允許公司 public IP」的條件對這些請求不會成立。這時應改用 `aws:SourceVpce` 或 `aws:SourceVpc`。
> 2. 由 **AWS 服務代為呼叫**時（例如 CloudFormation 代你建立資源、Athena 代你讀 S3），來源 IP 是 AWS 服務的位址。單純用 `aws:SourceIp` 拒絕會把這些操作也擋掉，常見做法是在 Deny 中加上 `"Bool": {"aws:ViaAWSService": "false"}`。

## 12.8 讓 AWS 上的程式取得權限：service role、instance profile 與 PassRole

回到 Wanderly 的事故：照片上傳程式用了寫死的 access key。正確做法是讓程式使用 role，AWS 會自動把臨時憑證交給它、並在過期前自動更新。不同運算服務的做法名稱不同，但原理一樣。

### Service role 與 trust policy

**Service role** 是一個讓 AWS 服務扮演的 role。它的 trust policy 把 `Principal` 寫成服務：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

換成 Lambda 就寫 `lambda.amazonaws.com`，ECS task 寫 `ecs-tasks.amazonaws.com`。這份 trust policy 只說明「EC2 服務可以扮演我」，能做什麼仍由 role 的 permissions policy 決定。

### EC2：instance profile

EC2 instance 不能直接「掛」一個 role，中間需要一個容器叫 **instance profile**：一個 instance profile 包含一個 role，instance 啟動時指定 instance profile。用 console 建立 EC2 用的 role 時，AWS 會自動建立同名的 instance profile，所以很多人沒意識到它存在；用 CLI 或 CloudFormation 時則要另外建立 `AWS::IAM::InstanceProfile`。

```text
  ┌──────────── EC2 instance ────────────┐
  │  應用程式（AWS SDK）                   │
  │     │ ① SDK 依預設順序尋找憑證          │
  │     ▼                                │
  │  Instance metadata service（IMDS）    │
  │  169.254.169.254                     │
  └─────┼────────────────────────────────┘
        │ ② IMDS 回傳 role 的臨時憑證（自動輪替）
        ▼
  ┌──────────────┐   ③ EC2 服務以 instance profile 中的 role
  │ Instance     │      向 STS 取得臨時憑證
  │ profile      │──────────────► STS
  │  └ role      │
  └──────────────┘
        │
        ▼ ④ 應用程式用臨時憑證呼叫 S3；CloudTrail 記錄為
          assumed-role/photo-uploader/i-0abc123...
```

① AWS SDK 會依序尋找憑證：環境變數、設定檔……最後是 instance metadata。程式碼裡**完全不需要**寫任何金鑰。② 臨時憑證從 IMDS 取得，在到期前自動更新。③ 背後是 EC2 服務替 instance 扮演 role。④ CloudTrail 的身份會包含 instance ID，可以追溯到是哪一台機器。IMDS 應該強制使用 IMDSv2（需要 session token 的版本），以防 SSRF 攻擊竊取憑證，細節在第 17 章。

Lambda 的對應概念是 **execution role**，ECS 則分成 **task role**（給容器內的程式用）與 **task execution role**（給 ECS agent 拉 image、寫 log 用），分別在第 19、21 章介紹。

### `iam:PassRole`：防止權限提升的關鍵

假設 Wanderly 的開發者小陳只有「建立 EC2」的權限，但帳號裡有一個擁有 `AdministratorAccess` 的 role。如果小陳可以啟動一台 instance 並把那個 admin role 掛上去，他登入那台機器後就能取得管理員權限。這種「透過把高權限 role 交給服務，間接取得更多權限」的手法叫 **權限提升（privilege escalation）**。

AWS 用 **`iam:PassRole`** 權限擋住它：把 role 交給某個服務（EC2 instance profile、Lambda function、ECS task definition、CloudFormation stack、Glue job……）時，呼叫者必須對那個 role 擁有 `iam:PassRole`。`iam:PassRole` 不是一個獨立的 API，而是在這些服務的建立／更新 API 中被檢查的權限。正確的寫法是限定 role 的 ARN 與能交給哪個服務：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PassOnlyAppRolesToLambda",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::111122223333:role/app-lambda-*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "lambda.amazonaws.com"
        }
      }
    }
  ]
}
```

部署失敗訊息出現 `is not authorized to perform: iam:PassRole` 時，修正方式是給部署者對**特定 role** 的 PassRole，而不是把 `iam:PassRole` 開成 `Resource: "*"`。

### Service-linked role

**Service-linked role** 是一種由 AWS 服務預先定義的特殊 role，例如 Auto Scaling、ELB、RDS 用來代你管理資源的 role。它的 trust policy 與權限由服務決定，你不能修改權限，只能在不再使用該服務資源時刪除。它不受 SCP 限制，這是 AWS 確保服務本身能正常運作的設計。題目若說「SCP 擋住了 Auto Scaling 啟動 instance」，要想到 service-linked role 不受 SCP 影響，問題通常在別處。

## 12.9 最小權限的設計方法：從 RBAC 到 ABAC

知道 policy 怎麼寫、怎麼評估之後，接下來的問題是：權限要給多少？**Least privilege（最小權限）** 的原則是「只給完成工作所需的權限，不多給」。原則好講，做起來的難處在於：一開始常常不知道程式到底需要哪些權限，而且團隊、專案、資源一直在變。

### RBAC：依職能給權限

**RBAC（Role-Based Access Control，以角色為基礎的存取控制）** 是傳統做法：先定義職能（開發者、維運、分析師、帳務），為每個職能寫一份 policy，再把人放到對應的 group 或 role。它直觀、容易稽核，但當資源一直增加時，policy 也必須跟著修改，例如每新增一個專案，就要更新所有相關 policy 的 Resource 清單。

### ABAC：依 tag 比對給權限

**ABAC（Attribute-Based Access Control，以屬性為基礎的存取控制）** 改用屬性（在 AWS 就是 tag）做規則：**身份的 tag 和資源的 tag 相符時才允許**。Wanderly 有三個專案團隊（booking、search、payment），每個工程師的身份帶 `project` tag，每台 EC2 也帶 `project` tag：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ManageOwnProjectInstances",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "arn:aws:ec2:*:111122223333:instance/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/project": "${aws:PrincipalTag/project}"
        }
      }
    },
    {
      "Sid": "DenyChangingProjectTag",
      "Effect": "Deny",
      "Action": [
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "*",
      "Condition": {
        "ForAnyValue:StringEquals": {
          "aws:TagKeys": ["project"]
        }
      }
    }
  ]
}
```

`${aws:PrincipalTag/project}` 是 **policy variable**：評估時會被換成呼叫者身上 `project` tag 的值。booking 團隊的人只能操作 `project=booking` 的 instance；新增第四個專案時，只要給新同事與新資源貼上 tag，**policy 一個字都不用改**。第二條 statement 很重要：如果使用者可以自己改資源的 tag，ABAC 就形同虛設，所以要禁止他們修改用於授權的 tag。這份範例只授權操作既有的 instance；若也要讓工程師自己建立 instance，還要另外允許 `ec2:RunInstances` 與「建立時一併貼 tag」（EC2 的 tag-on-create 也會檢查 `ec2:CreateTags`），並用 `aws:RequestTag/project` 等於 `${aws:PrincipalTag/project}` 的條件要求新資源一定帶上自己的專案值，同時調整上面的 Deny 讓這個建立情境例外。

| 比較 | RBAC | ABAC |
|---|---|---|
| 授權依據 | 職能對應的 policy 與資源清單 | 身份 tag 與資源 tag 的比對 |
| 新增專案或資源 | 要改 policy | 只要正確打 tag |
| policy 數量 | 隨職能 × 專案增加 | 少量通用 policy |
| 前提 | 職能清楚 | tag 治理嚴格、tag 不可被任意修改 |
| 適合 | 小型團隊、職能穩定 | 多專案、快速成長、多租戶 SaaS（第 49 章） |

身份上的 tag 可以來自 IAM user／role 的 tag，也可以在聯合登入時由企業 IdP 以 **session tag** 傳入（第 13 章），後者讓「員工的部門屬性」直接成為 AWS 的授權依據。

### 從寬到窄：收斂權限的實際流程

實務上很少能一開始就寫出完美的最小權限。比較可行的流程是：

1. 開發階段先用範圍適中的 policy（例如某服務的 AWS managed policy），限定在開發帳號。
2. 讓程式跑過完整測試，CloudTrail 會記錄它實際呼叫過的 API。
3. 用 **IAM Access Analyzer 的 policy generation** 依 CloudTrail 紀錄產生一份只包含實際用到的 action 的 policy 草稿，人工檢查後替換。
4. 上線後定期查看 **last accessed information**（IAM console 的 Access Advisor），移除長期沒用到的服務權限。

## 12.10 稽核與持續改善：Access Analyzer 與 credential report

權限設計不是一次性的工作。人員異動、專案結束、有人為了趕進度暫時開了大權限，都會讓權限慢慢膨脹。IAM 提供幾個工具找出問題。

### IAM Access Analyzer

**IAM Access Analyzer** 是一組分析權限的功能：

- **External access analysis（外部存取分析）**：你選定一個 **zone of trust（信任範圍）**，可以是單一帳號或整個 Organization。Analyzer 不是比對樣板，而是用數學方法把 policy 的所有可能結果算過一遍（AWS 稱為 provable security），因此能檢查 S3 bucket、IAM role trust policy、KMS key、Lambda function、SQS queue、Secrets Manager secret 等資源的 resource-based policy，找出「被信任範圍以外的 principal 可以存取」的資源，產生 finding。這個功能免費，但它是 Regional 的，要在每個使用中的 Region 建立 analyzer。
- **Unused access analysis（未使用存取分析）**：找出長期未使用的 role、access key、密碼與權限（付費功能）。
- **Policy validation**：在 console 或 API 撰寫 policy 時檢查語法錯誤、安全警告（例如 `iam:PassRole` 配 `*`）與最佳實務建議。
- **Policy generation**：依 CloudTrail 活動產生最小權限 policy 草稿（上一節）。
- **Custom policy checks**：在 CI/CD 中自動檢查新 policy 是否授予了不該有的權限，例如「這次修改是否新增了對外公開的存取」（付費功能）。

### Credential report

**Credential report** 是一份帳號層級的 CSV 報表，列出所有 IAM user（含 root user）的憑證狀態：密碼是否啟用、上次使用時間、是否啟用 MFA、每組 access key 的建立時間與上次使用時間。AWS 最多每 4 小時產生一份新報表。它適合回答稽核問題，例如「列出所有沒有啟用 MFA 的 user」「找出超過 90 天沒有輪替的 access key」。

### 比較：誰回答什麼問題

| 工具 | 回答的問題 | 層級 |
|---|---|---|
| Credential report | 哪些 user 沒 MFA、哪些 key 太舊或沒用？ | 帳號內所有 IAM user |
| Last accessed information | 這個身份上次用某服務是什麼時候？ | 單一 user／role／group／policy |
| Access Analyzer external access | 哪些資源被組織或帳號外的人存取？ | Resource-based policy |
| Access Analyzer unused access | 哪些 role、key、權限長期沒用？ | 帳號或組織 |
| Access Analyzer policy generation | 這個 role 實際需要哪些權限？ | 單一 role／user |
| CloudTrail | 誰在什麼時候做了什麼？ | API 呼叫紀錄（第 16 章） |

> [!example] 例子：Wanderly 事故後的改善
> 小林在事故後做了五件事：(1) 刪除 root access key、root 啟用實體安全金鑰 MFA；(2) 工程師改用 IAM Identity Center 登入（第 13 章）；(3) 上傳程式改用 EC2 instance profile，原本的 IAM user 與 access key 刪除；(4) 用 Access Analyzer 產生 policy 草稿，把權限從 `AmazonS3FullAccess` 收斂到 `wanderly-photos/hotels/*`；(5) 每月檢查 credential report 與 Access Analyzer finding。

## 12.11 比較與選型

### 這個身份該用哪一種？

```text
需要存取 AWS 的是誰？
├─ 人（員工、承包商）
│   ├─ 一般情況 → IAM Identity Center／企業 IdP 聯合登入（第 13 章）
│   └─ 緊急存取（IdP 故障時）→ 少數受嚴格保護、具 MFA 的 break-glass 身份
├─ 在 AWS 上執行的程式
│   ├─ EC2 → instance profile 中的 role
│   ├─ Lambda → execution role
│   └─ ECS／EKS → task role／Pod 身份（第 21 章）
├─ 在 AWS 外執行的程式
│   ├─ 支援 OIDC 的 CI/CD（例如 GitHub Actions）→ OIDC 聯合 + role（第 13 章）
│   ├─ 地端伺服器可配發 X.509 憑證 → IAM Roles Anywhere（第 13 章）
│   └─ 都不行 → IAM user + 最小權限 access key + 定期輪替
├─ 另一個 AWS 帳號或第三方廠商 → 跨帳號 role（第三方加 external ID）或 resource-based policy（第 13 章）
└─ 網站／App 的終端使用者 → Amazon Cognito，不是 IAM user（第 13 章）
```

### Policy 類型對照

| Policy 類型 | 附加在 | 會授權嗎 | 有 Principal 嗎 | 典型用途 |
|---|---|---|---|---|
| Identity-based（managed／inline） | User、group、role | 會 | 沒有 | 一般權限 |
| Resource-based | 資源（bucket、queue、key、role trust） | 會 | 有 | 跨帳號、指定誰能存取資源 |
| Permissions boundary | User、role | 不會，只設上限 | 沒有 | 讓開發者自建 role 但不能越權（第 14 章） |
| SCP | Organizations root／OU／帳號 | 不會，只設上限 | 沒有 | 組織層的 principal 防護欄（第 14 章） |
| RCP | Organizations root／OU／帳號 | 不會，只設上限 | 有（必須寫成 `"*"`） | 組織層的資源防護欄（第 14 章） |
| Session policy | 單次 session | 不會，只設上限 | 沒有 | 臨時縮小 role 權限 |
| ACL | S3 bucket／object（舊） | 會 | 以帳號表示 | 舊式跨帳號，新 bucket 預設停用 |

### Managed、inline 與 boundary 的選擇

| 需求 | 選擇 |
|---|---|
| 快速給予標準職能權限 | AWS managed policy |
| 同一份最小權限要用在很多 role，且要集中更新、有版本 | Customer managed policy |
| 權限只屬於單一 role，刪 role 時一併刪除 | Inline policy |
| 允許別人建立 role，但新 role 不能超過某範圍 | Permissions boundary |
| 整個帳號都不能做某件事 | SCP（第 14 章） |

## 12.12 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 新帳號、保護最高權限身份 | Root user 啟用 MFA、刪除 root access key、日常改用其他身份 |
| EC2 上的程式要存取 S3／DynamoDB，不要存放憑證 | IAM role + instance profile |
| Lambda／ECS 的權限 | Execution role／task role |
| 有 Allow 也有 Deny，結果？ | Explicit deny 優先 |
| 沒有任何 policy 提到 | Implicit deny |
| 使用者有 AdministratorAccess 仍被拒 | SCP、permissions boundary、session policy 或 explicit Deny |
| 能讀物件但不能列出 bucket | `s3:ListBucket` 的 Resource 要寫 bucket ARN（不帶 `/*`） |
| 刪除／終止前必須 MFA | Deny + `BoolIfExists` `aws:MultiFactorAuthPresent` = false |
| 只能在某 Region 操作 | `aws:RequestedRegion`（全帳號強制用 SCP） |
| 部署失敗：not authorized to perform `iam:PassRole` | 對特定 role 授予 `iam:PassRole`，可加 `iam:PassedToService` |
| 允許開發者建立 role 但不能提升權限 | Permissions boundary + 建立 role 時強制附加 boundary 的條件 |
| 專案越來越多，不想一直改 policy | ABAC：`aws:PrincipalTag` 比對 `aws:ResourceTag` |
| 找出被帳號／組織外部存取的資源 | IAM Access Analyzer（external access，zone of trust） |
| 依實際使用產生最小權限 | Access Analyzer policy generation（CloudTrail）、last accessed information |
| 列出沒有 MFA 或 access key 太舊的 user | Credential report |
| 多個使用者需要相同權限 | IAM group（或 Identity Center permission set） |

**常見陷阱**：

1. 以為 SCP 或 permissions boundary 可以「授予」權限。它們只設上限，真正的 Allow 必須來自 identity-based 或 resource-based policy。
2. 以為 statement 順序或「更精確的 Allow」能蓋過 Deny。IAM 沒有順序，explicit Deny 永遠勝出。
3. 把 group 寫進 bucket policy 的 `Principal`。Group 不是 principal，要寫 user、role 或帳號。
4. 用 `Bool` 檢查 MFA。長期 access key 的請求不帶這個 key，必須用 `BoolIfExists` 才能一併擋下。
5. 選項建議「建立 IAM user 並把 access key 放在 EC2 或程式設定檔」。在 AWS 上執行的程式一律用 role。
6. 把 `iam:PassRole` 授予 `Resource: "*"`。這等於允許把任何 role（包括管理員 role）交給服務，是典型的權限提升漏洞。

## 12.13 SAP 加深：大型組織的權限治理

SAA 題目通常只有一個帳號、一兩份 policy；SAP 題目則是幾十個帳號、上百個團隊，問的是「怎麼讓權限在規模化之下仍然可控」。

### 權限的分層防護

大型組織通常把權限分成三層，每層由不同團隊負責：

| 層級 | 工具 | 誰負責 | 目的 |
|---|---|---|---|
| 組織防護欄 | SCP、RCP（第 14 章） | 雲端平台／資安團隊 | 任何帳號都不能做的事：關閉 CloudTrail、離開組織、使用未核准 Region |
| 委派邊界 | Permissions boundary | 平台團隊定義，應用團隊使用 | 應用團隊可以自建 role，但不能超出邊界 |
| 工作權限 | Identity-based、resource-based policy | 應用團隊 | 完成工作所需的最小權限 |

這種分層的好處是應用團隊有自主權（不必每建一個 Lambda role 都開單給資安），而資安團隊仍能保證最壞情況。第 14 章會示範「只有附加指定 boundary 才能建立 role」的完整寫法。

### Resource-based policy 中 Principal 的細節

同帳號內，resource-based policy 的 `Principal` 寫成什麼會影響結果：

- 寫 **IAM user ARN**：授權直接給這個 user，user 的 identity policy 沒有 Allow 也能存取，permissions boundary 的 implicit deny 也不會限制它（boundary 裡的 explicit Deny 仍然有效）。
- 寫 **role ARN**：授權給這個 role 的所有 session，但 role 的 permissions boundary 與 session policy 的 implicit deny 仍會限制。
- 寫 **role session ARN**（`arn:aws:sts::111122223333:assumed-role/角色名稱/session 名稱`）：授權直接給這一個 session，不受 identity policy、boundary 或 session policy 的 implicit deny 限制。實務上很少這樣寫，因為 session 名稱每次可能不同。
- 寫**帳號**（`arn:aws:iam::111122223333:root` 或帳號 ID）：意思是「把決定權交給這個帳號的 IAM」，帳號內的 principal 還必須有 identity policy 允許。這是跨帳號授權最常用、也最容易被誤解的寫法：它**不是**只授權給 root user。

### 資料邊界（data perimeter）

企業常見的需求是「我們的資料只能被我們組織的身份、從我們的網路存取」。這可以用三組 condition key 組合成**資料邊界**：

- **身份邊界**：resource policy 或 RCP 中 `aws:PrincipalOrgID` 必須是自己的組織 → 只有自家身份能存取自家資源。
- **資源邊界**：SCP 或 VPC endpoint policy 中 `aws:ResourceOrgID` 必須是自己的組織 → 自家身份不能把資料寫到別人的 bucket。
- **網路邊界**：`aws:SourceVpce`／`aws:SourceVpc`／`aws:SourceIp` → 只能從公司網路存取。

這三者都有例外需要處理，例如 AWS 服務代為存取時用 `aws:PrincipalIsAWSService` 或 `aws:ViaAWSService` 排除。完整的組織級設計在第 40 章。

### Root user 的集中管理

在 AWS Organizations 中，AWS 提供集中管理成員帳號 root 存取的功能：管理帳號（或 delegated administrator）可以移除成員帳號的 root 憑證，需要執行少數 root 專屬工作（例如修復鎖死的 bucket policy）時，再由中央取得短時間、限定任務的 root session。這讓「每個成員帳號都要保管一組 root 密碼與 MFA」的負擔大幅降低。題目若描述「數百個成員帳號的 root 憑證難以保管」，可以考慮這個功能，並搭配 SCP 禁止成員帳號 root user 的日常操作。

### 規模化的持續改善

- 以 Organization 為 zone of trust 建立 Access Analyzer，由 delegated administrator 帳號集中檢視所有帳號的外部存取 finding。
- 在 CI/CD 管線中使用 Access Analyzer 的 policy validation 與 custom policy checks，在 policy 上線前就擋下過寬的權限。
- 用 unused access analysis 找出閒置的 role 與權限，定期清理。
- 用 CloudTrail organization trail 集中保留所有帳號的 API 紀錄，作為事故調查依據（第 16、40 章）。

## 本章重點整理

- 每個 AWS API 請求都要先通過驗證（你是誰）再通過授權（你能不能做），`AccessDenied` 是授權問題，簽章錯誤是驗證問題。
- Root user 擁有無法用 IAM 限制的完整權限，只用於少數 root 專屬工作；要啟用 MFA、刪除 access key、日常改用其他身份。
- IAM user 有長期憑證（密碼、最多兩組 access key），風險在於不會過期；人應改用聯合登入，程式應改用 role。
- Group 是管理 user 權限的集合，不是 principal、不能巢狀，也不能寫在 resource-based policy 的 Principal。
- Role 沒有長期憑證，被扮演時由 STS 發臨時憑證；trust policy 決定誰能扮演，permissions policy 決定扮演後能做什麼。
- Policy 由 Version、Statement、Effect、Action、Resource、Condition 組成，Principal 只出現在 resource-based policy；`s3:ListBucket` 作用在 bucket ARN，物件操作作用在 `bucket/*`。
- 評估邏輯：預設拒絕、explicit Deny 永遠優先、SCP／RCP／permissions boundary／session policy 只設上限不授權，有效權限是授權來源與所有上限的交集。
- 同帳號內 identity-based 與 resource-based policy 是聯集；跨帳號時請求者這側與資源這側都必須允許。
- Condition 讓權限依情境生效；MFA 要求要用 `BoolIfExists`，經 VPC endpoint 的請求要用 `aws:SourceVpce` 而非 `aws:SourceIp`。
- EC2 透過 instance profile 取得 role 的臨時憑證，程式中不需任何金鑰；Lambda 用 execution role，ECS 用 task role。
- 把 role 交給服務需要 `iam:PassRole`，應限定 role ARN 與 `iam:PassedToService`，避免權限提升。
- Service-linked role 由服務定義、不能修改權限，也不受 SCP 限制。
- ABAC 以 `aws:PrincipalTag` 比對 `aws:ResourceTag`，新增專案不必改 policy，但必須禁止使用者修改授權用的 tag。
- IAM Access Analyzer 找出外部存取、未使用權限並依 CloudTrail 產生最小權限 policy；credential report 列出所有 user 的密碼、MFA 與 access key 狀態。

## 本章練習題

### 練習 12-1｜SAA｜單選｜新帳號的 root user 保護

Wanderly 剛建立一個新的 AWS 帳號給資料分析團隊使用。目前只有 root user，創辦人用個人信箱註冊，並在 root user 下建立了一組 access key 給分析腳本使用。資安顧問要求以最少的工作量，立即降低這個帳號最高權限身份外洩的風險，同時保留日常管理能力。

哪個做法最合適？

- A. 為 root user 設定更長的密碼，並把 root access key 存放到 Secrets Manager 中讓腳本讀取
- B. 為 root user 啟用 MFA 並刪除 root access key，建立另一個具管理權限的身份供日常使用，腳本改用最小權限的 role
- C. 建立 IAM policy 附加到 root user，拒絕 root user 執行 EC2 與 IAM 相關操作
- D. 把 root user 的 email 改成共用信箱，並保留 access key 但每 90 天輪替一次

> [!answer]- 答案：B
> **A ✗** 把 root access key 搬到 Secrets Manager 仍然保留了一組擁有無限權限的長期金鑰，只要腳本或讀取 secret 的身份被入侵，整個帳號就外洩。Root user 本來就不應該有 access key。
>
> **B ✓** Root user 啟用 MFA、刪除 root access key、日常改用其他管理身份，是保護 root user 的標準做法；腳本改用最小權限的 role，同時解決了「長期金鑰」與「權限過大」兩個問題。
>
> **C ✗** IAM policy 無法限制 root user，也不能附加到 root user 上。只有在 Organizations 成員帳號中，SCP 才能限制 root user。
>
> **D ✗** 使用共用信箱是好習慣，但保留 root access key 並輪替並不能消除「無法限制的長期金鑰」這個根本風險，也沒有啟用 MFA。
>
> **考點**：SAA-1.1｜root user 保護與最小權限

### 練習 12-2｜SAA｜單選｜EC2 存取 S3 的憑證

Wanderly 的訂房網站在一組 Auto Scaling 管理的 EC2 instance 上執行，需要把使用者上傳的照片寫入 `wanderly-photos` bucket。目前做法是把一個 IAM user 的 access key 寫在 AMI 內的設定檔。資安團隊要求移除所有長期憑證，而且不希望應用程式修改憑證處理邏輯。

最合適的做法是什麼？

- A. 把 access key 改存到 Systems Manager Parameter Store 的 SecureString，應用程式啟動時讀取
- B. 在 bucket policy 中允許 EC2 instance 的 private IP 範圍寫入，並移除 access key
- C. 使用 user data 在每次啟動時呼叫 `aws iam create-access-key` 產生新的 access key
- D. 建立一個 trust policy 允許 `ec2.amazonaws.com` 的 role，授予寫入該 bucket 的最小權限，透過 instance profile 掛到 launch template

> [!answer]- 答案：D
> **A ✗** 把 access key 移到 Parameter Store 只是換個地方存放，它仍是長期憑證，也需要另外處理讀取 parameter 的權限。
>
> **B ✗** Bucket policy 可以用 `aws:SourceVpce` 或 `aws:SourceIp` 加條件，但請求仍必須由某個 principal 簽章；而且經 NAT 出去的流量來源也不是 private IP。這無法取代身份。
>
> **C ✗** 每次啟動都建立新 access key 會讓長期憑證越來越多，而且執行這個指令本身也需要憑證，治標不治本。
>
> **D ✓** Instance profile 讓 EC2 透過 instance metadata 取得 role 的臨時憑證並自動輪替。AWS SDK 會自動從 metadata 讀取憑證，應用程式不需要修改憑證邏輯，也沒有任何長期金鑰。
>
> **考點**：SAA-1.1｜instance profile 與臨時憑證

### 練習 12-3｜SAA｜單選｜Explicit deny 與 group 權限

分析師 Amy 屬於 `analytics` group，該 group 附加了一份允許 `s3:*` 於 `wanderly-reports` bucket 與其中所有物件的 customer managed policy。Amy 的 IAM user 另外有一份 inline policy，Deny `s3:DeleteObject` 於 `wanderly-reports/*`。帳號不屬於 Organizations，bucket 沒有 bucket policy。

Amy 嘗試刪除 `wanderly-reports/daily/old.csv` 時會發生什麼事？

- A. 被拒絕，因為 inline policy 中符合的 explicit Deny 會優先於 group policy 的 Allow
- B. 被允許，因為 group policy 使用 `s3:*`，萬用字元的權限優先於單一 action
- C. 被允許，因為 group 的 policy 是 managed policy，優先權高於 inline policy
- D. 被拒絕，因為 bucket 沒有 bucket policy，任何刪除操作都需要 bucket policy 允許

> [!answer]- 答案：A
> **A ✓** IAM 會收集所有適用的 policy（user 的 inline policy 與 group 的 managed policy），只要有任何一條符合的 Deny，就直接拒絕，不論其他地方有多少 Allow。
>
> **B ✗** IAM 沒有「萬用字元優先」或「越具體越優先」的規則；Allow 永遠無法蓋過 explicit Deny。
>
> **C ✗** Managed 與 inline 只差在管理方式與能否重用，評估時沒有優先權差異。
>
> **D ✗** 同帳號內 identity-based policy 允許就足以存取 S3，不需要 bucket policy；這題被拒絕的原因是 explicit Deny。
>
> **考點**：SAA-1.1｜explicit deny 優先與 policy 聯集

### 練習 12-4｜SAA｜單選｜ListBucket 的 Resource

工程師為報表服務的 role 寫了以下權限：Allow `s3:GetObject` 與 `s3:ListBucket`，Resource 為 `arn:aws:s3:::wanderly-reports/*`。服務可以用完整 key 下載檔案，但列出 bucket 內容時收到 AccessDenied。沒有任何 Deny 或 bucket policy。

應如何修正，並維持最小權限？

- A. 把 Resource 改為 `*`，讓兩個 action 都能作用在所有 bucket
- B. 在 bucket policy 加上 `Principal: "*"` 並允許 `s3:ListBucket`
- C. 新增一條 statement，對 `arn:aws:s3:::wanderly-reports` 允許 `s3:ListBucket`，原本對 `wanderly-reports/*` 的 statement 保留 `s3:GetObject`
- D. 把 `s3:ListBucket` 改成 `s3:ListAllMyBuckets`，Resource 維持不變

> [!answer]- 答案：C
> **A ✗** 改成 `*` 雖然能運作，但會讓 role 可以列出與讀取帳號內所有 bucket，違反最小權限。
>
> **B ✗** `Principal: "*"` 會讓任何人都能列出 bucket 內容，等於公開資料夾結構，而且 Block Public Access 也可能擋下這個 policy。
>
> **C ✓** `s3:ListBucket` 作用在 bucket 本身，Resource 必須是不帶 `/*` 的 bucket ARN；物件操作（GetObject）才作用在 `bucket/*`。把兩種資源分成兩條 statement 是標準寫法，必要時還能用 `s3:prefix` 限制可列出的資料夾。
>
> **D ✗** `s3:ListAllMyBuckets` 是列出帳號內所有 bucket 名稱，不是列出某個 bucket 的物件。
>
> **考點**：SAA-1.1｜S3 action 與資源層級

### 練習 12-5｜SAP｜選兩項｜依實際使用收斂權限

Wanderly 有 40 個 Lambda function，三年前為了趕上線，全部使用附加 `AmazonDynamoDBFullAccess` 與 `AmazonS3FullAccess` 的 execution role。資安團隊要求在不影響功能的前提下收斂成最小權限，並希望盡量依據實際使用資料而不是人工猜測。CloudTrail 已啟用超過一年。

哪兩個做法最合適？（選兩項）

- A. 直接把所有 role 換成 `ReadOnlyAccess`，再依錯誤訊息逐一補權限
- B. 使用 IAM Access Analyzer 依 CloudTrail 活動為每個 role 產生 policy 草稿，審查後替換原本的 managed policy
- C. 為所有 role 加上 permissions boundary `AdministratorAccess`，限制最大權限
- D. 刪除 CloudTrail 舊紀錄，從今天開始重新蒐集使用資料
- E. 檢查每個 role 的 last accessed information，找出長期未使用的服務權限並移除

> [!answer]- 答案：B、E
> **A ✗** 換成唯讀權限會讓需要寫入的 function 立即失敗，用正式環境的錯誤當作權限需求清單，不符合「不影響功能」。
>
> **B ✓** Access Analyzer 的 policy generation 會分析 CloudTrail 中這個 role 實際呼叫的 API，產生只包含使用過的 action 的 policy 草稿。人工補上資源 ARN 等細節並測試後替換，是以實際資料收斂權限的標準做法。
>
> **C ✗** 以 `AdministratorAccess` 當 boundary 等於沒有上限，無法收斂任何權限。
>
> **D ✗** 刪除 CloudTrail 紀錄會失去產生 policy 所需的使用資料，也破壞稽核證據。
>
> **E ✓** Last accessed information 顯示 role 上次使用各服務（部分服務可到 action 層級）的時間，能快速找出可以移除的權限，適合搭配 policy generation 持續檢查。
>
> **考點**：SAP-3.2、SAA-1.1｜Access Analyzer policy generation 與 last accessed

### 練習 12-6｜SAA｜單選｜破壞性操作要求 MFA

Wanderly 規定：任何身份終止 EC2 instance 時，必須使用經過 MFA 驗證的 session。部分維運人員仍在 CLI 使用 IAM user 的長期 access key。工程師寫了一條 Deny `ec2:TerminateInstances` 的 statement，需要加入適當的 condition。

哪個 condition 能同時擋下「未經 MFA 的 console session」與「直接使用長期 access key 的請求」？

- A. `"Bool": {"aws:MultiFactorAuthPresent": "false"}`
- B. `"BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}`
- C. `"Null": {"aws:MultiFactorAuthAge": "false"}`
- D. `"NumericGreaterThan": {"aws:MultiFactorAuthAge": "0"}`

> [!answer]- 答案：B
> **A ✗** 直接用長期 access key 簽章的請求不包含 `aws:MultiFactorAuthPresent`；使用 `Bool` 時 key 不存在，條件不成立，Deny 不會套用，長期金鑰就繞過了要求。
>
> **B ✓** `BoolIfExists` 在 key 存在且為 false 時符合，key 不存在時也視為符合，因此「沒用 MFA 的 session」與「長期 access key」都會被 Deny 擋下。
>
> **C ✗** `Null` 為 false 表示「key 存在」，這會對**有** MFA age 的請求（也就是用過 MFA 的請求）套用 Deny，方向剛好相反。
>
> **D ✗** 這會拒絕所有 MFA 驗證時間大於 0 秒的 session，也就是幾乎所有用過 MFA 的人，同樣方向錯誤；而且長期金鑰請求沒有這個 key，反而不會被擋。
>
> **考點**：SAA-1.1｜MFA condition 與 IfExists

### 練習 12-7｜SAA｜單選｜部署 Lambda 時的 PassRole 錯誤

Wanderly 的 CI/CD role 負責建立 Lambda function，最近部署失敗，錯誤訊息是：`User: arn:aws:sts::111122223333:assumed-role/cicd-deployer/build-42 is not authorized to perform: iam:PassRole on resource: arn:aws:iam::111122223333:role/app-lambda-booking`。CI/CD role 已有 `lambda:CreateFunction` 權限。資安團隊要求修正後，CI/CD 仍不能把管理員 role 交給任何服務。

應如何修正？

- A. 為 CI/CD role 附加 `IAMFullAccess` managed policy
- B. 在 `app-lambda-booking` 的 trust policy 中把 CI/CD role 加入 Principal
- C. 允許 CI/CD role 執行 `iam:PassRole`，Resource 設為 `*`，並依靠 SCP 防護
- D. 允許 CI/CD role 對 `arn:aws:iam::111122223333:role/app-lambda-*` 執行 `iam:PassRole`，並以 `iam:PassedToService` 限定為 `lambda.amazonaws.com`

> [!answer]- 答案：D
> **A ✗** `IAMFullAccess` 讓 CI/CD role 可以建立任意 role 與 policy，等於可以自行提升成管理員，遠超過需求。
>
> **B ✗** Trust policy 決定誰能「扮演」這個 role；PassRole 是把 role 交給 Lambda 服務，由 Lambda 去扮演。Trust policy 的 Principal 應該是 `lambda.amazonaws.com`，而缺少的是呼叫者這一側的 `iam:PassRole` 權限。
>
> **C ✗** `iam:PassRole` 配 `Resource: "*"` 允許把任何 role（包括管理員 role）交給服務，是典型的權限提升漏洞。SCP 是組織防護欄，不是為了補這種過寬授權。
>
> **D ✓** 把 PassRole 限定在應用程式 role 的命名範圍，並用 `iam:PassedToService` 限定只能交給 Lambda，既解決部署錯誤，也確保 CI/CD 無法把其他 role 交給服務。
>
> **考點**：SAA-1.1、SAA-1.2｜iam:PassRole 與權限提升

### 練習 12-8｜SAA｜單選｜Managed 還是 inline

Wanderly 有 30 個微服務，各自有自己的 role。每個 role 都需要同一組權限：寫入 CloudWatch Logs、讀取共用設定的 Parameter Store 路徑、使用 X-Ray。平台團隊希望修改這組權限時只改一個地方，改錯時能快速還原，並且能看出哪些 role 使用了它。

應如何提供這組共用權限？

- A. 在每個 role 建立內容相同的 inline policy，並用腳本同步修改
- B. 附加 AWS managed policy `PowerUserAccess`，涵蓋所有需要的服務
- C. 建立一份 customer managed policy，附加到 30 個 role
- D. 建立一個 IAM group 放入 30 個 role，再把 policy 附加到 group

> [!answer]- 答案：C
> **A ✗** Inline policy 無法重用，30 份內容要各自修改，容易不一致，也沒有版本可以還原。
>
> **B ✗** `PowerUserAccess` 幾乎允許 IAM 以外的所有操作，遠超過三項需求，違反最小權限。
>
> **C ✓** Customer managed policy 可以附加到多個身份，修改一次就同時生效；它保留版本（最多 5 個），可以把預設版本切回舊版；也能在 console 查看哪些身份附加了它。
>
> **D ✗** IAM group 只能包含 IAM user，不能包含 role。
>
> **考點**：SAA-1.1｜customer managed policy 的重用與版本

### 練習 12-9｜SAA｜單選｜限制操作 Region

Wanderly 的資料必須保存在日本。一位外包工程師的 IAM user 只需要在東京 Region（`ap-northeast-1`）管理 EC2。帳號目前沒有使用 AWS Organizations，短期內也不會導入。管理者希望這位工程師在其他 Region 呼叫 EC2 API 時被拒絕。

應如何設定這位工程師的權限？

- A. 在 user 的 policy 中允許 `ec2:*`，並加上 condition `StringEquals` `aws:RequestedRegion` 為 `ap-northeast-1`
- B. 在 user 的 policy 中允許 `ec2:*`，並把 Resource 設為 `arn:aws:ec2:ap-northeast-1:*:*`，這樣就能涵蓋所有 EC2 API
- C. 建立 SCP 拒絕東京以外的 Region，附加到這位 user
- D. 在每個非東京 Region 建立 VPC 並移除 Internet Gateway，讓工程師無法建立機器

> [!answer]- 答案：A
> **A ✓** `aws:RequestedRegion` 是請求要呼叫的 Region。只在值為 `ap-northeast-1` 時允許，其他 Region 的請求沒有任何 Allow，就是 implicit deny。這在不使用 Organizations 時是最直接的做法。
>
> **B ✗** 部分 EC2 API（例如 `DescribeInstances` 這類 Describe 操作）不支援資源層級權限，只能用 `Resource: "*"`。只靠 Resource 中的 Region 無法完整控制，也會讓需要的操作失效。
>
> **C ✗** SCP 屬於 AWS Organizations，帳號沒有使用 Organizations；而且 SCP 附加在 root、OU 或帳號上，不能附加到單一 IAM user。
>
> **D ✗** 移除 IGW 只影響網路連線，完全不影響 IAM 是否允許在該 Region 呼叫 EC2 API。
>
> **考點**：SAA-1.1｜aws:RequestedRegion condition

### 練習 12-10｜SAA｜單選｜稽核 user 的 MFA 與金鑰狀態

稽核人員要求 Wanderly 在一週內提供一份清單：帳號內所有 IAM user 是否啟用 MFA、每組 access key 的建立時間與上次使用時間，並找出超過 90 天未輪替的金鑰。帳號內有 120 個 IAM user。團隊希望以最少的工作量取得資料。

應使用哪個功能？

- A. IAM Access Analyzer 的 external access findings
- B. CloudTrail Lake 查詢過去 90 天的 `CreateAccessKey` 事件
- C. IAM credential report
- D. 為每個 user 逐一查看 Access Advisor 頁籤

> [!answer]- 答案：C
> **A ✗** External access findings 分析的是 resource-based policy 是否讓外部 principal 存取資源，不提供 user 的 MFA 或金鑰狀態。
>
> **B ✗** CloudTrail 只能看到期間內發生的建立事件；超過保留範圍前建立的金鑰會漏掉，也看不到 MFA 狀態，需要額外整理。另外 CloudTrail Lake 自 2026 年 5 月 31 日起不再開放新客戶（第 16 章）。
>
> **C ✓** Credential report 是一份帳號層級的 CSV，一次列出所有 IAM user（含 root）的密碼狀態、MFA 是否啟用、每組 access key 的建立時間、是否啟用與上次使用時間，正好符合稽核需求。
>
> **D ✗** Access Advisor 顯示的是各服務的上次存取時間，不是憑證狀態；逐一查看 120 個 user 也不符合最少工作量。
>
> **考點**：SAA-1.1｜IAM credential report

### 練習 12-11｜SAP｜單選｜Permissions boundary 的有效權限

Wanderly 的平台團隊讓應用團隊自己建立 Lambda role，但所有新 role 都必須附加名為 `app-boundary` 的 permissions boundary。`app-boundary` 允許 `s3:*`、`dynamodb:*`、`logs:*`。某應用團隊建立了 `booking-fn` role，並附加 `AdministratorAccess`。帳號的 SCP 允許所有操作，沒有 session policy 或 explicit Deny。

`booking-fn` 能執行哪些操作？

- A. 所有操作，因為 identity-based policy `AdministratorAccess` 優先於 boundary
- B. 只有 S3、DynamoDB、CloudWatch Logs 的操作，因為有效權限是 identity policy 與 boundary 的交集
- C. 什麼都不能做，因為 boundary 與 identity policy 衝突時會整體拒絕
- D. S3、DynamoDB、Logs 加上 IAM 的操作，因為 boundary 只限制資料服務

> [!answer]- 答案：B
> **A ✗** Identity-based policy 沒有優先權；有 boundary 時，請求必須同時被 identity policy 與 boundary 允許。
>
> **B ✓** Permissions boundary 只設上限、不授權。`AdministratorAccess` 允許一切，boundary 只允許 S3、DynamoDB、Logs，兩者的交集就是這三個服務的操作。這正是讓應用團隊自建 role 卻不能越權的機制。
>
> **C ✗** Boundary 與 identity policy 是取交集，不是「衝突就全部拒絕」；交集內的操作仍然被允許。
>
> **D ✗** Boundary 限制的是它沒有列出的所有操作，IAM 不在 boundary 的允許範圍內，所以會被 implicit deny。
>
> **考點**：SAP-1.2、SAA-1.1｜permissions boundary 交集

### 練習 12-12｜SAP｜選兩項｜以 ABAC 管理多專案權限

Wanderly 有 25 個專案團隊，每個團隊在同一個帳號中管理自己的 EC2 instance 與 Secrets Manager secret。目前每新增一個專案，資安團隊都要修改十幾份 policy 的 Resource 清單，常常出錯。公司已透過企業 IdP 登入，IdP 中每位員工都有 `project` 屬性。資安團隊希望新增專案時不用修改 policy，且團隊之間不能互相操作資源。

哪兩個做法組合起來最合適？（選兩項）

- A. 寫一份通用 policy，允許相關操作，條件是 `aws:ResourceTag/project` 等於 `${aws:PrincipalTag/project}`，並讓 IdP 以 session tag 傳入員工的 `project` 屬性
- B. 為每個專案建立獨立的 IAM group，把該專案資源的 ARN 列在 group policy 中
- C. 在每份 policy 中允許 `ec2:CreateTags`，讓團隊可以自行調整資源上的 `project` tag
- D. 以 explicit Deny 禁止一般使用者新增、修改或刪除既有資源上的 `project` tag，並要求建立資源時必須帶有與自己相同的 `project` tag
- E. 把所有資源的 Resource 寫成 `*`，再用 CloudTrail 事後稽核是否有人越權

> [!answer]- 答案：A、D
> **A ✓** ABAC 以身份 tag 比對資源 tag，一份通用 policy 就能涵蓋所有專案；員工的 `project` 屬性由 IdP 以 session tag 傳入，新增專案時只需給人員與資源正確屬性，不必修改 policy。
>
> **B ✗** 這是 RBAC 的做法，仍然要為每個新專案建立 group 並維護 ARN 清單，正是目前的痛點。
>
> **C ✗** 讓使用者自行修改授權用的 tag，等於讓他們能把別的專案資源改成自己的 tag 再操作，ABAC 的隔離就失效了。
>
> **D ✓** ABAC 的安全前提是授權用的 tag 不可被任意修改。用 explicit Deny 禁止修改 `project` tag，並用 `aws:RequestTag/project` 要求建立資源時必須帶上與自己相同的值，才能確保每個資源都落在正確的專案範圍。
>
> **E ✗** 事後稽核只能發現越權，無法預防；`Resource: "*"` 也讓團隊可以互相操作資源。
>
> **考點**：SAP-1.2、SAP-2.3｜ABAC 設計與 tag 防護

### 練習 12-13｜SAP｜單選｜Session policy 的效果

Wanderly 的資料平台有一個 `data-pipeline` role，permissions policy 允許讀寫 `wanderly-lake` bucket 的所有路徑。排程系統為每個租戶的批次作業扮演這個 role，並在 `AssumeRole` 時傳入一份 session policy，只允許 `s3:GetObject` 與 `s3:PutObject` 於 `wanderly-lake/tenant-a/*`。沒有 permissions boundary，也沒有 explicit Deny。

這個 session 能做什麼？

- A. 能讀寫 `wanderly-lake` 的所有路徑，因為 session policy 只是附加說明，不影響 role 的權限
- B. 能讀寫 `wanderly-lake` 的所有路徑，外加 session policy 中額外列出的權限
- C. 只能讀取 `tenant-a/*`，因為 session policy 傳入後所有寫入都會被拒絕
- D. 只能讀寫 `wanderly-lake/tenant-a/*`，因為有效權限是 role permissions policy 與 session policy 的交集

> [!answer]- 答案：D
> **A ✗** Session policy 會實際參與評估，它是這次 session 的權限上限。
>
> **B ✗** Session policy 不會授予額外權限，即使它列出 role 沒有的操作，那些操作也不會被允許。
>
> **C ✗** Session policy 允許了 `PutObject`，role 也允許寫入，所以交集內的寫入仍然有效。
>
> **D ✓** 有效權限是 role 的 identity-based policy 與 session policy 的交集。這讓同一個 role 可以依每次作業動態縮小權限，不必為每個租戶建立不同的 role。
>
> **考點**：SAP-2.3、SAP-1.2｜session policy 交集

### 練習 12-14｜SAP｜單選｜找出被組織外部存取的資源

Wanderly 已經使用 AWS Organizations 管理 35 個帳號，主要使用東京與新加坡兩個 Region。資安團隊擔心有團隊把 S3 bucket、KMS key 或 IAM role 的存取權開給組織外的帳號，希望集中、持續地找出這些資源，並由資安帳號統一檢視。

最合適的做法是什麼？

- A. 在 Organizations 中把資安帳號設為 IAM Access Analyzer 的 delegated administrator，於使用中的每個 Region 建立以整個 organization 為 zone of trust 的 analyzer
- B. 每週在每個帳號下載 credential report，找出有 access key 的 user
- C. 在管理帳號啟用 CloudTrail，搜尋 `PutBucketPolicy` 事件並人工檢查內容
- D. 在每個帳號建立以單一帳號為 zone of trust 的 analyzer，並把 finding 寄到各帳號負責人信箱

> [!answer]- 答案：A
> **A ✓** 以 organization 為 zone of trust 時，只有分享到組織外的存取才會產生 finding，組織內帳號之間的正常分享不會成為雜訊。由 delegated administrator 集中管理可在資安帳號檢視所有成員帳號的結果。External access analyzer 是 Regional 的，所以每個使用中的 Region 都要建立。
>
> **B ✗** Credential report 只列 IAM user 的憑證狀態，無法看出 resource-based policy 是否開放給外部。
>
> **C ✗** 人工檢查 CloudTrail 事件無法持續、全面地評估 policy 的實際效果，也容易漏掉 KMS key policy、role trust policy 等其他資源類型。
>
> **D ✗** 以單一帳號為 zone of trust 會把組織內帳號之間的合法分享也視為外部存取，產生大量雜訊；分散寄給各帳號也不符合集中檢視的需求。
>
> **考點**：SAP-1.2、SAP-3.2｜Access Analyzer 與 organization zone of trust

### 練習 12-15｜SAP｜單選｜Resource policy 授權給 role ARN 與 boundary

在 Wanderly 的同一個帳號中，bucket `wanderly-exports` 的 bucket policy 允許 `Principal` 為 `arn:aws:iam::111122223333:role/report-runner` 執行 `s3:GetObject`。`report-runner` 的 permissions policy 沒有任何 S3 權限；它附加了一份 permissions boundary，只允許 `dynamodb:*` 與 `logs:*`。沒有 SCP、session policy 或 explicit Deny 影響此請求。

`report-runner` 的 session 讀取 `wanderly-exports` 中的物件會怎樣？

- A. 被允許，因為同帳號內 resource-based policy 的 Allow 不受任何其他 policy 影響
- B. 被拒絕，因為 bucket policy 不能把 role ARN 寫在 Principal
- C. 被拒絕，因為 bucket policy 授權對象是 role ARN 時，role 的 permissions boundary 仍會限制，而 boundary 沒有允許 S3
- D. 被允許，因為 permissions boundary 只限制 identity-based policy 的範圍，與 resource-based policy 完全無關

> [!answer]- 答案：C
> **A ✗** 同帳號內 resource-based policy 的 Allow 確實可以不需要 identity-based policy 再允許，但當 Principal 是 role ARN 時，role 的 permissions boundary 與 session policy 的 implicit deny 仍然有效。
>
> **B ✗** Bucket policy 可以指定 IAM role ARN 作為 Principal，這是很常見的寫法。
>
> **C ✓** 授權給 role ARN 的 resource-based policy，仍受該 role 的 permissions boundary 限制。Boundary 只允許 DynamoDB 與 Logs，S3 不在範圍內，所以請求被拒絕。這讓 boundary 能可靠地成為 role 的權限上限，不會被資源端的授權繞過。
>
> **D ✗** 對 role 而言，boundary 也會限制透過 resource-based policy 取得的權限；只有授權直接給 IAM user ARN 或特定 session ARN 時，情況才不同。
>
> **考點**：SAP-1.2、SAP-2.3｜resource-based policy 與 permissions boundary 的交互作用

### 練習 12-16｜SAA｜選兩項｜外洩的 access key

Wanderly 收到 GitHub 的通知：一位工程師的 IAM user access key 出現在公開 repository 中，這組 key 被一支在地端伺服器執行的報表腳本使用。帳號內目前沒有發現異常資源，但團隊必須立即止血，並避免同類事件再發生。

哪兩個步驟最合適？（選兩項）

- A. 把 repository 改成 private，由於金鑰已不再公開，因此保留這組 key 繼續使用
- B. 為該 IAM user 加上 permissions boundary，之後再決定是否處理 key
- C. 立即停用（inactive）並刪除外洩的 access key，再用 CloudTrail 檢查這組 key 外洩後的所有 API 活動
- D. 把 IAM user 加入一個沒有任何權限的 group，因為 group 的空權限會覆蓋 user 的權限
- E. 讓報表腳本改用臨時憑證（例如透過 IAM Roles Anywhere 取得 role 憑證），不再依賴長期 access key

> [!answer]- 答案：C、E
> **A ✗** 金鑰一旦公開，就要假設已被他人取得；把 repository 改為 private 無法收回已經被複製的金鑰。
>
> **B ✗** Boundary 可以縮小權限，但不會讓金鑰失效；先處理金鑰本身才是止血，延後處理會讓攻擊者持續使用。
>
> **C ✓** 停用並刪除外洩的金鑰是立即止血的第一步；接著用 CloudTrail 依 access key ID 查詢外洩期間的活動，確認是否有被建立的資源、新增的身份或被讀取的資料。
>
> **D ✗** IAM 權限是聯集，加入空權限的 group 不會減少 user 原有的權限；group 也不能覆蓋 user 的 policy。
>
> **E ✓** 根本解法是消除長期憑證。地端伺服器可以用 IAM Roles Anywhere 以 X.509 憑證換取 role 的臨時憑證，即使未來外洩，影響時間也有限。
>
> **考點**：SAA-1.1、SAA-1.2｜長期憑證風險與臨時憑證
