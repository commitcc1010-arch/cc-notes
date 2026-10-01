---
chapter: 20
title: Dependency Management 與 Supply Chain
part: 3
---

# 第 20 章　Dependency Management 與 Supply Chain

> [!abstract] 本章地圖
> **核心問題**：加入一個套件只要一行指令，為什麼它會帶來多年的升級、相容性與安全成本？我們要怎麼知道自己依賴了什麼、讓依賴可以持續更新，並防止有人透過依賴把惡意程式送進 production？
>
> **你會學到**：
> - 畫出 direct 與 transitive dependency 圖，並回答「我們到底有沒有用到某個套件」
> - 理解 SemVer 的承諾與限制，以及 diamond dependency 為什麼會讓升級卡住
> - 分辨 manifest 與 lock file 的角色，用雜湊確保每次安裝的內容一致
> - 比較靜態依賴、SemVer、bundled distribution、live at head 與 vendoring 幾種管理模型
> - 辨認 typosquatting、dependency confusion、維護者帳號被接管等供應鏈攻擊，並用 SBOM、SLSA、簽章與 registry 政策防禦
> - 用 Dependabot／Renovate 類工具讓升級變成日常，並為 AI agent 新增依賴設下 guardrails
>
> **前置知識**：第 4 章（time and change）、第 5 章（Hyrum's Law）、第 19 章（One Version rule）
>
> **對應原書**：SWE 第 21 章〈Dependency Management〉

## 20.1 故事：「我們到底有沒有用到它？」

一個週一早上，資安社群公布了一個 HTTP 函式庫的嚴重漏洞，這裡叫它 `httpkit`。只要攻擊者能控制某個 HTTP header，就可能在伺服器上執行任意程式。修補版本已經發布：2.x 系列修在 2.7.2，3.x 系列修在 3.1.0。工程經理 Kevin 在群組裡只問了一句：「我們有沒有用到？」

沒有人能立刻回答。結帳服務的 `requirements.txt` 裡沒有 `httpkit`，搜尋服務的也沒有。初階工程師阿凱翻了半天才發現，`httpkit` 是被兩個套件間接帶進來的：外部金流商提供的 `payments-sdk`，以及推播服務用的 `notify-client`。結帳服務 14 個月前產生的 lock file 把 `httpkit` 釘在 2.4.1，從那之後沒有人更新過，因為「它一直都能跑」。最後花了一天半，才把五個服務、三個行動 app 後端與兩個批次工作全部確認完。

更糟的是升級本身。阿凱想一併把 `notify-client` 升到 1.5，因為新版才支援 Lisa 要的 LINE 推播；但 `notify-client` 1.5 要求 `httpkit` 3.x，而結帳用的 `payments-sdk` 2.x 只能接受 `httpkit` 2.x。同一個程式裡不能同時裝兩個版本的 `httpkit`，套件管理工具直接回報「無法解析」。團隊只能先把 `httpkit` 修到 2.7.2，LINE 推播延到金流商出 3.x 版 SDK 之後。

同一週還發生了另一件事。阿凱請 AI coding agent 幫忙找一個「解析台灣地址」的 Python 套件，agent 建議了一個看起來很合理的名稱，並在 PR 裡直接加上 `pip install`。SRE 志明在 review 時順手查了一下：這個套件在公開 registry 上根本不存在。如果有人事先註冊了這個名稱並放進惡意程式，CI 會毫不猶豫地把它下載、安裝、執行。

這一章要處理的，就是這三個問題：我們依賴了什麼、依賴之間的版本要怎麼協調，以及如何確保進到 build 裡的程式碼真的是我們以為的那一份。

## 20.2 為什麼依賴管理這麼難

### 定義：管理你無法控制的程式碼

**Dependency**（依賴）是你的程式運作時需要、但不是你寫的東西：函式庫、框架、語言 runtime、作業系統套件、container base image，甚至外部 API。**Dependency management**（依賴管理）是管理這些東西的版本、來源、更新與移除的工作。

原書在這一章開頭坦白地說，依賴管理是軟體工程中最難、也最沒有完美解法的問題之一。它的難處可以用兩個維度說明。第一是**時間**：今天能用的版本，明天可能發現漏洞、後天可能被作者放棄；你不升級，世界也會往前走（第 4 章）。第二是**規模**：一個依賴會帶來它自己的依賴，一個組織有幾十個服務、每個服務有幾百個間接依賴，任何一個改變都可能和其他幾百個互相影響。

原書在這一章給出的最強烈建議是：**在其他條件相同時，寧可面對 source control 的問題，也不要面對依賴管理的問題**，因為前者比較便宜、也比較容易推理。在同一個 repository 裡，你可以一次改完函式庫與所有呼叫端（第 19 章的 One Version）；但外部依賴的作者不認識你，不會配合你的時程，也看不到你怎麼用他們的程式。所以「把東西放進自己的 repo」與「從外部引入」是兩種不同等級的承諾。

### 引入一個依賴，實際上在買什麼

加入一個依賴時，你得到的是一份現成的功能，但你同時承接了：

| 你承接的東西 | 具體意思 | Harbor 的例子 |
|---|---|---|
| 它的 bug 與漏洞 | 它的問題就是你的問題，而且你不一定能自己修 | `httpkit` 漏洞要等上游發布修補 |
| 它的發布節奏 | 它決定何時出新版、何時停止支援舊版 | 金流商的 SDK 一年才出一次 major |
| 它的依賴 | 它帶進來的每一個套件，你都要承擔 | `payments-sdk` 帶進 23 個間接依賴 |
| 它的相容性承諾 | 它說「不會破壞相容性」的範圍與可信度 | `notify-client` 小版本升級改變了重試行為 |
| 它的授權條款 | 能否用在商業產品、是否要求公開原始碼 | 法務要求避開特定授權 |
| 它的可用性 | 安裝時 registry 要可用、套件不能被下架 | 2016 年 npm 的 `left-pad` 被作者下架，大量專案的 build 一夕之間失敗 |

`left-pad` 是一個只有十幾行、把字串左邊補空白的小套件。作者因為另一個套件的名稱爭議不滿 npm 的處理方式，下架了自己發布的所有套件，結果許多知名專案因為間接依賴它而無法建置。npm 之後修改了下架政策。這個事件說明：依賴的大小和風險不成比例，一個十幾行的套件也能讓你的 build 停擺。

> [!warning] 常見誤解
> 「開源套件是免費的。」下載是免費的，但評估、升級、修補漏洞、處理相容性與最終替換都要花工程時間。原書的說法是：引入依賴時要考慮的是它在整個生命週期中的成本，而不只是今天省下多少開發時間。

## 20.3 依賴圖：direct 與 transitive

### 看見完整的圖

你在 manifest（例如 `requirements.txt`、`package.json`、`pyproject.toml`）中直接列出的是 **direct dependency**（直接依賴）。這些套件自己的依賴，以及依賴的依賴，都是 **transitive dependency**（間接依賴，或稱遞移依賴）。Harbor 結帳服務的依賴圖一部分長這樣（這是修補完成後的狀態，`httpkit` 已從 2.4.1 升到 2.7.2；當初的 lock file 對應的是較舊的 `payments-sdk` 2.3.0）：

```text
                  checkout-service
                 ╱        │        ╲
        payments-sdk   notify-client   web-framework
         2.4.0          1.4.0           5.2.0
         │   ╲          │                 │
         │    crypto-lib│               template-engine
         │     1.9.3    │                 │
         ▼              ▼               markup-utils
            httpkit 2.7.2  ◀── 兩條路徑都指向同一個套件
               │
            idna-codec 3.4

   第一層：direct dependencies（3 個，寫在 manifest 裡）
   其他層：transitive dependencies（真實服務常有數十到數百個）
```

讀這張圖時，注意 `httpkit` 不在第一層，但有兩條路徑通到它。這就是故事中「`requirements.txt` 裡沒有它，但它確實在 production 裡跑」的原因。漏洞、授權、可用性問題不會因為你沒有直接 import 就消失：只要它被安裝在你的 build 或 runtime 裡，它就是你的攻擊面。

實務上，大多數語言的工具都能印出完整的依賴樹，例如 Python 的 `pipdeptree`、npm 的 `npm ls`、Go 的 `go mod graph`、Maven 的 `mvn dependency:tree`。Harbor 從這次事件學到的第一課很樸素：**每個服務都要能在幾分鐘內回答「我們有沒有用到 X 的哪個版本」**。這個問題的正式答案，是 20.9 會講的 SBOM。

### 依賴的數量是一種成本

依賴圖的大小本身就是風險指標。每多一個節點，就多一個可能發布壞版本、被接管、被放棄的點。原書提醒，評估要不要引入一個依賴時，要看的不只是它本身，還有它會帶進多少間接依賴。為了一個格式化日期的小功能，引入一個帶了 40 個間接依賴的大套件，通常不划算；如果標準函式庫或組織內已經核准的套件能做到，就優先用它們。

## 20.4 SemVer：一個有用但不完美的承諾

### 規則

**Semantic Versioning**（SemVer，語意化版本）用 `MAJOR.MINOR.PATCH` 三個數字表達一個版本和前一版的相容性：

- **PATCH**（例如 2.7.1 → 2.7.2）：只修 bug，不改 API。
- **MINOR**（例如 2.6 → 2.7）：新增功能，向下相容，原本能用的程式不需要修改。
- **MAJOR**（例如 2.x → 3.0）：有不相容的變更，使用者可能要改程式。
- `0.x` 版本代表開發初期，任何變更都可能不相容。

使用者在 manifest 中用**版本範圍**表達「我能接受哪些版本」。不同生態系的語法不同，但概念相近：

```text
npm / Cargo 的 ^2.4.0   ⇒  ≥ 2.4.0 且 < 3.0.0   （同一個 major 內都可以）
npm 的 ~2.4.0           ⇒  ≥ 2.4.0 且 < 2.5.0   （只接受 patch 更新）
Python 的 ~=2.4         ⇒  ≥ 2.4   且 < 3.0     （compatible release）
Python 的 ==2.4.1       ⇒  只接受這一個版本
```

SemVer 的價值在於讓工具能自動挑選版本：如果所有套件都誠實地遵守規則，解析器就能在範圍內選出最新、又彼此相容的組合。

### 限制：它是作者的猜測

原書對 SemVer 的評價很精準：版本號是發布者對相容性的**估計**，是把「這個變更有多危險」壓縮成三個數字的有損簡寫，而不是保證。一個 MINOR 版本「向下相容」，是作者認為的相容；但依照第 5 章的 Hyrum's Law，只要使用者夠多，任何可觀察的行為都會被某人依賴。作者改了錯誤訊息的文字、調整了重試的時間間隔、讓一個函式快了一點導致某個 race condition 不再被掩蓋，在作者眼中都不是 API 變更，在某些使用者眼中卻是破壞。Harbor 就遇過 `notify-client` 一個 MINOR 升級把預設 timeout 從 30 秒改成 10 秒，作者認為這是「改善」，推播服務卻在尖峰時段開始大量逾時。

原書因此說 SemVer 會同時犯兩種錯：**過度限制**與**保護不足**。過度限制是：上游發了一個 major 版本，可能只是刪掉一個你從沒用過的函式，對你其實完全相容，但版本範圍會讓解析器拒絕這次升級。保護不足是：上游發了一個「相容」的 MINOR，卻因為 Hyrum's Law 弄壞了你，解析器照樣放行。兩種錯的根源相同：三個數字裝不下「這個變更對**你的用法**是否相容」這麼細的資訊。

使用者自己寫的範圍也會放大這兩種錯：寫 `==2.4.1` 太嚴，任何修補都進不來，還很容易和別人的限制衝突；寫 `>=2.0` 太鬆，未來不相容的 3.0 也會被接受。

所以實務上，SemVer 要搭配兩樣東西才可靠：**測試**（升級後用你自己的測試確認行為），以及 **lock file**（20.6，把「範圍」變成「確切版本」）。

> [!tip] 不同的解析策略
> 大多數套件管理工具選「範圍內最新的版本」。Go modules 採用不同的策略，稱為 minimal version selection（MVS，原書也有討論）：每個依賴者宣告的是「至少需要哪一版」，對每個套件，選這些最低需求中最高的那個，而不是 registry 上最新的那個。這樣使用者建置出來的組合會盡量接近作者當初開發、測試時用的版本，也不會因為上游今天發布了新版就自動被升級。兩種策略各有取捨：前者較快拿到修補，後者較可預測。

## 20.5 Diamond dependency：兩條路徑，一個版本

### 問題的形狀

**Diamond dependency**（菱形依賴）是依賴管理中最典型的衝突。你的程式依賴 A 與 B，A 與 B 都依賴 C，但要求的版本範圍沒有交集：

```text
                checkout-service
                 ╱             ╲
        payments-sdk 2.x     notify-client 1.5
        需要 httpkit ^2.6     需要 httpkit ^3.0
                 ╲             ╱
                   httpkit  ??
           （同一個程式只能載入一個版本）
```

圖的上半部看起來沒問題：checkout 只是想用兩個套件。問題出在底部的交會點：`^2.6` 代表 2.6 以上、3.0 以下；`^3.0` 代表 3.0 以上、4.0 以下；兩個範圍沒有任何一個版本同時滿足。在 Python 這類「一個環境只能安裝一個版本」的生態系中，這就是無解。

### 各生態系怎麼處理

不同語言的處理方式不同，沒有一種是免費的：

| 做法 | 代表 | 好處 | 代價 |
|---|---|---|---|
| 只允許一個版本，無解就報錯 | Python（pip）、大多數系統套件管理工具 | 行為明確，不會有兩份 C 同時存在 | 遇到不相容的範圍就卡住，只能等上游 |
| 依某種規則選一個，不一定報錯 | Java 的 classpath（例如 Maven 選離根最近的版本） | 通常能建置成功 | 執行時才出現 `NoSuchMethodError` 之類的錯誤，比建置失敗更難查 |
| 允許多個版本並存 | npm（巢狀 `node_modules`）、Cargo（不同 major 可以並存） | 很少卡住 | 兩份 C 的狀態不共享；把 A 產生的物件傳給 B 時型別可能不相容；程式體積變大 |
| 改名打包（shading） | Java 生態常見的做法 | 把 C 改名後塞進 A 裡，避開衝突 | 漏洞修補時，要找出所有被改名藏起來的副本 |

故事中的 Harbor 用 Python，所以只剩三條路：等金流商出支援 `httpkit` 3.x 的 SDK、不升級 `notify-client`、或自己 fork 其中一個套件修改它的依賴範圍。Fork 看起來最快，但它會創造一份「只有 Harbor 在維護的版本」，未來每次上游更新都要手動合併，這正是第 19 章 One Version rule 要避免的情況。團隊最後選擇等待，並在 ADR 中記錄了理由與重新評估的日期。

Diamond dependency 也解釋了為什麼原書那麼重視 One Version：在組織內部，如果每個共用函式庫只有一個版本，內部依賴就不會形成菱形衝突，剩下的只有外部依賴的問題。

## 20.6 Lock file：把「範圍」變成「確切的版本」

### Manifest 與 lock file 的分工

Manifest 寫的是**意圖**：「我需要 `payments-sdk` 2.3 以上、3.0 以下。」但今天執行安裝和下個月執行安裝，可能因為上游發布新版而得到不同的結果。一個「我的電腦上可以跑、CI 上卻壞了」的 bug，常常就是兩邊安裝到了不同的間接依賴版本。

**Lock file**（鎖定檔）記錄的是**某次解析的結果**：每一個套件（包括所有間接依賴）的確切版本，通常還有下載內容的雜湊值。常見的例子有 `package-lock.json`（npm）、`poetry.lock`、`uv.lock`（Python）、`Cargo.lock`（Rust）、`go.sum`（Go，記錄雜湊），以及用 `pip-compile` 產生、加上 `--hash` 的 `requirements.txt`。

```text
manifest（人寫，表達意圖）          lock file（工具產生，記錄結果）
──────────────────────────          ─────────────────────────────────────
payments-sdk >=2.3,<3               payments-sdk==2.4.0   sha256:9f2c…
notify-client >=1.4,<2      ──解析──▶ notify-client==1.4.0  sha256:41ab…
                                    httpkit==2.7.2        sha256:335a…
                                    crypto-lib==1.9.3     sha256:c07e…
                                    idna-codec==3.4       sha256:8d1f…
```

左邊是人維護的少數幾行，右邊是工具產生、應該提交進 VCS 的完整清單。有了 lock file，CI、同事的電腦與 production 的 build 會安裝**完全相同**的東西；升級變成一個明確的動作：重新解析、產生新的 lock file、在 PR 中 review 差異。

### 雜湊：確認拿到的是同一份內容

Lock file 中的雜湊值解決另一個問題：即使版本號相同，下載到的內容也可能不同。可能是 registry 被入侵、鏡像被竄改，或中間的網路被攔截。安裝工具在下載後重新計算雜湊，和 lock file 中記錄的比對，不符就拒絕安裝。例如 pip 的 `--require-hashes` 模式要求每個套件都必須有雜湊，否則整個安裝失敗。20.12 的程式會示範這個檢查。

### 常見的誤用

- **Lock file 不進 VCS**：每次建置重新解析，等於沒有 lock。應用程式（會被部署的服務）一定要提交 lock file。
- **Lock 了就永遠不動**：Harbor 的 `httpkit` 2.4.1 被鎖了 14 個月。Lock file 保證的是可重現，不是安全；它必須搭配 20.10 的自動更新，否則只是把漏洞也一起鎖住。
- **函式庫把依賴範圍寫死**：如果你在寫一個要給別人用的函式庫，manifest 中的範圍應該盡量寬（只排除已知不相容的版本），讓使用者的解析器有空間處理菱形依賴。釘死確切版本是應用程式 lock file 的工作，不是函式庫的。

## 20.7 依賴管理的幾種模型

原書比較了幾種組織處理依賴的基本模型。了解它們，就能看懂各種工具與政策背後的假設。

**一、靜態依賴：什麼都不變。** 選定版本之後永遠不升級。這在短命的專案中可行，但對長壽系統是一顆定時炸彈：漏洞要修時，你可能要一次跨越好幾個 major 版本，而且舊版本早已沒有人支援。Harbor 的 `httpkit` 2.4.1 就是無意間落入這個模型。

**二、SemVer：依範圍自動解析。** 目前最主流的模型。它的強項是去中心化：沒有人需要協調全世界的套件，各自宣告版本與範圍即可。弱點就是 20.4 講的：版本號只是估計，範圍可能過嚴或過鬆，菱形依賴可能無解。

**三、Bundled distribution：由別人挑好一整組。** Linux 發行版（例如 Debian、Ubuntu）就是這種模型：發行版的維護者挑選一組彼此相容的套件版本，一起測試、一起發布，使用者整組採用。好處是相容性由專人負責；代價是版本通常比較舊，而你要信任發行版的選擇。很多組織的「內部核准套件清單」與「平台團隊維護的 base image」，就是組織內的 bundled distribution。

**四、Live at head：永遠用最新版，由提供者負責不弄壞你。** 這是原書描述的 Google 內部做法，也是第 19 章 One Version 的延伸。依賴的提供者在發布任何變更前，要先跑所有使用者的測試；如果會弄壞某個使用者，提供者要先幫對方修好（或提供遷移工具），再提交變更。使用者則永遠依賴最新版本，不用自己決定何時升級。這需要很強的基礎設施：能找到所有使用者（code search）、能跑所有使用者的測試（CI）、能大規模修改呼叫端（第 21 章的 large-scale change）。在組織內部，live at head 能做得很好；對外部開源套件則很難，因為你無法要求全世界的作者在發布前跑你的測試。

**Vendoring** 是常和上述模型搭配的手段：把依賴的原始碼複製一份放進自己的 repository，而不是在建置時從 registry 下載。好處是 build 不依賴外部 registry 的可用性（`left-pad` 事件不會影響你），所有程式碼都能被搜尋、被 review；代價是升級要手動執行，而且如果有人直接修改 vendored 的程式碼，你就默默地擁有了一個 fork。Go 的 `go mod vendor` 與很多 monorepo 的 `third_party/` 目錄都是這種做法。原書描述 Google 把引入的開源套件放在 monorepo 的 `third_party` 目錄，引入前要確認沒有已存在的版本，並至少列出兩位 owner；原書也坦承這個流程常出問題：owner 換組、使用者透過間接依賴越來越多，等到被迫升級時成本已經很高。

| 模型 | 誰決定版本 | 升級何時發生 | 適合 |
|---|---|---|---|
| 靜態 | 一開始選定 | 幾乎從不 | 短命專案、一次性工具 |
| SemVer＋lock file | 解析器在範圍內選，lock 固定結果 | 有人更新 lock 時 | 大多數使用開源生態的團隊 |
| Bundled distribution | 發行版或平台團隊 | 跟著整組發布 | 作業系統套件、組織內 base image |
| Live at head | 永遠最新，提供者負責相容 | 每次提供者變更 | 有強大 CI 與 code search 的組織內部依賴 |

Harbor 最後採用混合模型：內部的 `harbor-common` 朝 live at head 靠近（第 19 章：先把搜尋、賣家後台、結帳三條版本線收斂成單一版本，之後每次發布都由 CI 自動對所有使用者的 repo 發升級 PR），外部套件走 SemVer＋lock file＋自動更新，container base image 由平台團隊統一維護。

## 20.8 Supply chain：攻擊從依賴進來

### 什麼是軟體供應鏈

**Software supply chain**（軟體供應鏈）是從原始碼到 production artifact 之間的所有環節：你的程式碼、你的依賴、依賴的作者與他們的帳號、套件 registry、build 系統、container base image、簽章與部署工具。任何一個環節被攻破，惡意程式就能進入你的產品，而且看起來像是「正常的依賴」。

供應鏈攻擊特別危險的原因是它繞過了你所有的程式碼審查：你 review 了自己的每一行程式，但你不會 review 幾百個間接依賴的每一次更新。而很多套件管理工具在安裝時就會執行套件自帶的腳本（例如 npm 的 `postinstall`、Python 套件的建置腳本），所以惡意程式不需要等到 production，在開發者筆電或 CI 上安裝時就已經執行了，那裡通常有 cloud credential 與 deploy key。

### 常見的攻擊手法

**Typosquatting**（錯字搶註）：註冊和熱門套件只差一兩個字元的名稱，例如把 `requests` 拼成 `reqeusts`，等開發者打錯字時安裝到惡意版本。也有用 `-` 與 `_` 互換、加上 `python-` 前綴等變形。

**Dependency confusion**（依賴混淆）：組織內部有一個私有套件，例如 `harbor-payments-core`，只放在內部 registry。攻擊者在公開 registry 上註冊同名套件，並給它一個很高的版本號。如果安裝工具同時查詢內部與公開 registry，並且「選版本號最高的」，就會裝到攻擊者的版本。2021 年，資安研究員 Alex Birsan 公開了這種手法，並展示它能影響多家大型科技公司的內部 build。

**維護者帳號被接管或主動作惡**：攻擊者取得合法套件的發布權限，然後發布一個帶有惡意程式的新版本。2018 年的 `event-stream` 事件中，一個熱門 npm 套件的原作者把維護權交給一位自願接手的陌生人，對方加入一個惡意的間接依賴，目標是竊取特定加密貨幣錢包。2024 年的 xz utils 事件更具警示性：一個身份不明的貢獻者花了兩年多的時間取得這個壓縮函式庫的維護者信任，然後在發布檔中植入能影響 SSH 的後門（CVE-2024-3094）。它在大規模進入穩定版 Linux 發行版之前，被一位工程師因為注意到 SSH 登入變慢、追查下去而發現。

**已知漏洞**：不是攻擊者埋的，而是普通的 bug。2021 年底的 Log4Shell（CVE-2021-44228）是 Java 日誌函式庫 Log4j 2 的一個遠端執行漏洞，因為 Log4j 被大量專案間接依賴，許多組織和 Harbor 一樣，花了好幾天才搞清楚自己哪裡用到了它。

**Build 系統被入侵**：原始碼是乾淨的，但 build 過程被竄改，產出的 artifact 和原始碼不一致。這類攻擊要靠第 27 章的 hermetic build 與 provenance 來防禦。

```text
  開發者 ──▶ 原始碼 repo ──▶ build 系統 ──▶ artifact registry ──▶ production
    ▲            ▲              ▲                 ▲
    │            │              │                 │
  帳號被盜     惡意 commit     build 被竄改      artifact 被替換
                 
  依賴作者 ──▶ 公開 registry ──┘（安裝進 build）
    ▲              ▲
  帳號被接管     typosquatting／dependency confusion／已知漏洞
```

這張圖把攻擊點標在每一個環節上。上面一排是你自己的流程，下面一排是外部依賴進入 build 的路徑。下一節的每一種防禦，都對應保護其中一兩個箭頭。

## 20.9 防禦：知道你有什麼、驗證它從哪裡來

### 漏洞掃描

**Software composition analysis**（SCA，軟體組成分析）工具會讀取 lock file 或 artifact，列出所有依賴與版本，再和漏洞資料庫比對。漏洞通常以 **CVE**（Common Vulnerabilities and Exposures，公開漏洞的統一編號）識別；開源生態常用的資料庫包括 OSV（Open Source Vulnerabilities）與各平台的 security advisory。工具例子有 `pip-audit`、`npm audit`、`govulncheck`，以及各 CI 平台內建的掃描功能。

掃描最大的實務問題是**噪音**。一個中型服務可能同時被回報幾十個漏洞，其中很多出現在根本沒被呼叫的程式路徑上。有些工具（例如 `govulncheck`）會做 reachability analysis（可達性分析），判斷你的程式是否真的呼叫到有漏洞的函式，以降低噪音。Harbor 的處理規則是依嚴重度與可達性分級：嚴重且可達的漏洞 48 小時內修補，其他排進每週的依賴更新；不修補的決定要有 owner 簽核並設定到期日，而不是讓警告一直掛著。

### SBOM：依賴的清單

**SBOM**（Software Bill of Materials，軟體物料清單）是一份機器可讀的清單，列出一個 artifact 包含的所有元件、版本、來源與授權，就像食品包裝上的成分表。兩種主要格式是 SPDX 與 CycloneDX。SBOM 通常在 build 時由工具自動產生，和 artifact 一起保存。

SBOM 的價值在故事中看得最清楚：如果 Harbor 每個部署出去的 artifact 都有 SBOM，並集中存放、可以查詢，Kevin 的「我們有沒有用到 `httpkit`」就是一條查詢，幾分鐘就能回答，而且答案是「production 上實際跑的那份」，不是「某個人的 repo 裡寫的那份」。美國在 2021 年發布的改善國家網路安全行政命令（Executive Order 14028）中，把向採購方提供 SBOM 列入聯邦政府軟體供應鏈安全指引要涵蓋的做法，這讓它從資安團隊的好習慣，逐漸變成許多採購流程會詢問的項目。

SBOM 只是清單，不是防禦本身。一份從來沒有人查詢的 SBOM，和沒有 SBOM 差不多。

### SLSA：build 過程的可信度

**SLSA**（Supply-chain Levels for Software Artifacts，唸作 salsa）是一個開放的框架，描述 build 過程要做到什麼程度，artifact 才值得信任。SLSA 目前的版本（v1.2）分成 build track 與 source track 兩條軌道，這裡只介紹 build track。它分成幾個等級，概念上是逐步提高：

| 等級 | 要求（簡化） | 能防什麼 |
|---|---|---|
| Build L0 | 沒有要求，代表還沒有導入 SLSA | 無 |
| Build L1 | Build 產生 **provenance**（來源證明）：這個 artifact 是由哪個 build、從哪份原始碼、用什麼指令產生 | 讓人能追溯、發現發布錯誤（例如從不在 repo 裡的 commit 建置）；但 provenance 很容易被偽造 |
| Build L2 | 在託管的 build 平台上建置，provenance 由平台產生並簽章，使用者驗證簽章 | 簽章防止 build 完成後竄改 provenance 或 artifact |
| Build L3 | Build 平台經過強化：不同 build（即使是同一個專案）互相隔離，使用者定義的 build 步驟拿不到簽 provenance 的密鑰 | 防止 build 過程被內部人員、外洩的 credential 或同平台上的其他工作竄改 |

SLSA 把「我們的 build 安不安全」從一個模糊的問題，變成可以逐級檢查的清單。Provenance 的產生與驗證、hermetic build 與 reproducible build 的細節在第 27 章。

### 簽章與 Sigstore

**簽章**（signature）讓使用者能驗證「這個 artifact 確實是某個身份發布的，而且內容沒有被改過」。傳統做法是發布者保管一把長期的私鑰，但私鑰的保管、輪替與撤銷本身就很困難，很多專案因此根本不簽章。

**Sigstore** 是一個開源專案，目標是讓簽章變得簡單。它的核心想法是 **keyless signing**（無長期金鑰簽章）：發布者用既有的身份（例如 CI 系統的 OIDC 身份）向 Sigstore 的憑證機構 Fulcio 取得一張短效憑證，用它簽章後，簽章紀錄會寫入公開、只能附加的 transparency log Rekor。驗證者可以檢查「這個 artifact 是由某個 repo 的某個 CI workflow 簽章的」，並在 log 中確認這筆紀錄存在。常用的命令列工具是 `cosign`，常用來簽 container image。套件 registry 也開始支援以 Sigstore 為基礎的 provenance 或 attestation，例如 npm 的 provenance 與 PyPI 的 attestation，讓使用者能驗證套件是從哪個 repo 與 CI workflow 建置出來的。

### Registry 與安裝政策

前面的工具都偏向「事後知道」，以下幾個做法則在入口處擋下攻擊，Harbor 全部採用：

- **內部 registry 鏡像**：所有 build 只從內部鏡像安裝套件，鏡像再從公開 registry 同步。這讓組織有一個統一的檢查點，也能在公開 registry 故障時繼續建置。
- **內部套件名稱保留**：所有內部套件使用固定前綴（例如 `harbor-`）或 scope（例如 npm 的 `@harbor/`），並設定安裝工具「這個前綴只能從內部 registry 解析」，直接消除 dependency confusion。必要時也在公開 registry 先註冊這些名稱。
- **雜湊鎖定**：lock file 必須包含雜湊，CI 以要求雜湊的模式安裝。
- **新依賴審查**：新增一個 direct dependency 要經過輕量審查（20.11），已核准的套件清單由平台團隊維護。
- **限制安裝時的權限**：CI 安裝依賴的步驟不持有部署權限與 production credential，並限制對外網路，降低安裝腳本作惡的影響範圍。

## 20.10 更新自動化：讓升級變成日常

### 為什麼小步升級比較便宜

第 4 章講過升級成本隨時間加速成長。依賴更新是這個道理最直接的應用：每週升級一個 PATCH，每次的差異很小，壞了也很容易找到原因；兩年不升級，一次跨越三個 major 版本，就要同時處理幾十個 breaking change，而且分不清是哪一個造成問題。Harbor 的 `httpkit` 如果一直有在小步更新，漏洞公布那天只需要合併一個自動產生的 PR。

### Dependabot 與 Renovate

**Dependabot**（GitHub 提供）與 **Renovate**（開源，可自架）是兩個常見的依賴更新機器人。它們定期檢查 manifest 與 lock file，發現新版本時自動開 PR，PR 中包含版本差異、changelog 摘要與相容性資訊，CI 會自動跑測試。發現已知漏洞時，它們也能優先開安全更新 PR。

導入後最常見的失敗是**PR 太多，沒人看**。一個服務有兩百個依賴，每週可能有幾十個更新；如果每一個都開一個 PR，工程師很快就會學會忽略它們。Harbor 的設定是：

```text
Harbor 依賴更新政策（v2）
- 安全更新：立即開 PR，嚴重且可達的漏洞 48 小時內合併
- PATCH 與 MINOR：每週一彙整成一個 PR（依生態系分組），CI 全綠且
  套件不在「高風險清單」（金流、認證、加密相關）時自動合併
- MAJOR：每個套件獨立開 PR，指派 code owner，附 changelog 中的 breaking changes
- 高風險清單中的套件：任何版本變更都需要人工 review 並經過 canary
- 新版本發布未滿 3 天不自動升級（給社群時間發現被入侵的版本）
- 每季檢視：落後最新 major 超過一個版本的依賴列入技術債清單
```

這份政策有幾個值得注意的地方。分組與排程把噪音降到每週一個 PR。自動合併只在測試可信時才安全，所以它和第 22 到 26 章的測試品質直接相關：如果測試抓不到依賴升級造成的行為改變，自動合併就只是自動把 regression 送進 production。「新版本未滿 3 天不升級」是在速度與安全之間的一個取捨：大多數被入侵的版本會在發布後短時間內被發現並撤下，稍等幾天可以避開，但也代表一般修補會晚幾天進來，所以安全更新不受這條限制。

## 20.11 引入與移除依賴的決策

### 引入前要問的問題

原書建議把引入依賴當成一個工程決策，而不是順手的動作。Harbor 的新依賴審查是一張 PR 範本，只要填幾分鐘：

| 問題 | 為什麼要問 |
|---|---|
| 標準函式庫或已核准的套件能做到嗎？ | 最便宜的依賴是不新增的依賴 |
| 我們用到它多少功能？ | 只用一個函式卻引入整個框架，通常不划算 |
| 會帶進多少間接依賴？ | 依賴圖的大小就是攻擊面與升級成本 |
| 維護狀況如何？最近一年有發布嗎？有幾位維護者？ | 單一維護者的套件，bus factor 是 1（第 8 章） |
| 有沒有安全政策與漏洞回報管道？ | 出事時能不能及時修補 |
| 授權條款是否符合公司政策？ | 法務風險不能事後補救 |
| 如果它被放棄，我們要怎麼替換？ | 退出成本，決定要不要用 wrapper 隔離 |

開源社群也有工具可以輔助評估，例如 OpenSSF Scorecard 會自動檢查一個專案是否有 code review、是否簽章發布、是否有安全政策等項目。分數是參考，不是結論。

**Wrapper**（包裝層）是降低退出成本的常用手段：在程式中只透過一層自己的介面使用外部套件，日後替換時只需要改這一層。但不要過度包裝：如果 wrapper 原封不動地轉發套件的所有功能，它只是多了一層要維護的程式碼。Wrapper 的價值在於只暴露你真正需要的那一小部分。

### 移除依賴同樣重要

依賴只會越來越多，除非有人主動移除。Harbor 每季跑一次未使用依賴的檢查（很多語言都有工具可以找出 manifest 中列出但程式中沒有 import 的套件），並把「移除一個依賴」視為和「新增一個功能」一樣有價值的 PR。移除依賴的流程和第 18 章的 deprecation 相同：找出所有使用者、提供替代方案、遷移、刪除。

## 20.12 動手寫：依賴解析與安裝 gate

### 程式一：一個迷你 SemVer 解析器

這段程式實作一個簡化的依賴解析器，重現故事中的菱形依賴：每個套件只能選一個版本，解析器在版本範圍內優先選最新版，走不通時回溯嘗試較舊的版本。

```python
# 一個迷你的 SemVer 解析器：找出滿足所有限制的版本組合
REGISTRY = {
    # 套件: {版本: {依賴: 限制}}
    "payments-sdk": {
        "2.3.0": {"httpkit": "^2.4"},
        "2.4.0": {"httpkit": "^2.6"},
        "3.0.0": {"httpkit": "^3.0"},
    },
    "notify-client": {
        "1.4.0": {"httpkit": "^2.1"},
        "1.5.0": {"httpkit": "^3.0"},
    },
    "httpkit": {"2.4.1": {}, "2.6.0": {}, "2.7.2": {}, "3.0.0": {}, "3.1.0": {}},
}


def parse(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def satisfies(version: str, constraint: str) -> bool:
    """支援 ^X.Y（同 major、≥ X.Y）與 =X.Y.Z 兩種寫法。"""
    if constraint.startswith("="):
        return version == constraint[1:]
    low = parse(constraint[1:] + ".0")[:3]
    v = parse(version)
    return v[0] == low[0] and v >= low


def resolve(requirements: dict[str, list[str]], chosen: dict[str, str]) -> dict[str, str] | None:
    """回溯搜尋：每個套件只能選一個版本（One Version），優先選最新版。"""
    pending = [p for p in requirements if p not in chosen]
    if not pending:
        return chosen
    name = pending[0]
    for version in sorted(REGISTRY[name], key=parse, reverse=True):
        if not all(satisfies(version, c) for c in requirements[name]):
            continue
        new_req = {k: list(v) for k, v in requirements.items()}
        for dep, constraint in REGISTRY[name][version].items():
            new_req.setdefault(dep, []).append(constraint)
        # 已選定的套件若被新限制排除，這條路走不通
        if any(dep in chosen and not satisfies(chosen[dep], c)
               for dep, c in REGISTRY[name][version].items()):
            continue
        result = resolve(new_req, {**chosen, name: version})
        if result:
            return result
    return None


def show(title: str, top_level: dict[str, str]) -> None:
    reqs = {k: [v] for k, v in top_level.items()}
    result = resolve(reqs, {})
    print(f"[{title}] 需求 {top_level}")
    print("  →", result if result else "無解：httpkit 沒有同時滿足兩邊的版本（diamond dependency）")


show("今天", {"payments-sdk": "^2.3", "notify-client": "^1.4"})
show("強制 notify-client 1.5", {"payments-sdk": "^2.3", "notify-client": "=1.5.0"})
show("payments-sdk 也升到 3.x", {"payments-sdk": "^3.0", "notify-client": "=1.5.0"})
```

執行結果：

```text
[今天] 需求 {'payments-sdk': '^2.3', 'notify-client': '^1.4'}
  → {'payments-sdk': '2.4.0', 'notify-client': '1.4.0', 'httpkit': '2.7.2'}
[強制 notify-client 1.5] 需求 {'payments-sdk': '^2.3', 'notify-client': '=1.5.0'}
  → 無解：httpkit 沒有同時滿足兩邊的版本（diamond dependency）
[payments-sdk 也升到 3.x] 需求 {'payments-sdk': '^3.0', 'notify-client': '=1.5.0'}
  → {'payments-sdk': '3.0.0', 'notify-client': '1.5.0', 'httpkit': '3.1.0'}
```

逐步解讀：

1. `REGISTRY` 模擬一個套件 registry：每個版本宣告自己需要的依賴範圍。`satisfies` 實作 `^` 的規則：同一個 major、且不低於指定版本（為了簡化，沒有處理 `0.x` 的特殊規則）。
2. 第一個情境最值得注意：需求寫的是 `notify-client ^1.4`，registry 上有 1.5.0，但解析結果是 1.4.0。解析器先試 1.5.0，發現它要求的 `httpkit ^3.0` 和 `payments-sdk 2.4.0` 要求的 `^2.6` 沒有交集，於是**默默回溯**選了舊版。這就是為什麼「我明明寫了 ^1.4，怎麼沒拿到新功能」：範圍只是上限，實際版本由整張圖決定。這也是 lock file 必須被 review 的原因，它記錄了你真正拿到什麼。
3. 第二個情境把 `notify-client` 強制鎖在 1.5.0，就沒有退路了，解析失敗。這就是 Harbor 遇到的菱形依賴。
4. 第三個情境顯示真正的解法通常在上游：`payments-sdk` 推出支援 `httpkit` 3.x 的版本後，整張圖就能解開。也說明了為什麼要讓依賴保持接近最新：越落後，越容易卡在「必須同時升級好幾個套件」的狀態。
5. 真實的解析器（例如 pip、Cargo、Poetry、uv）面對的是幾百個套件、每個幾十個版本的搜尋空間；原書也提到，在 SemVer 限制下選版本的問題在一般情況下已被證明是 NP-complete。所以它們使用更聰明的演算法（例如 Poetry 與 uv 採用的 PubGrub）與啟發式規則，但「在限制中搜尋、走不通就回溯」的核心概念相同。

### 程式二：新依賴的入口 gate 與雜湊驗證

第二段程式模擬 Harbor 在 CI 中對「新增依賴」與「安裝依賴」的兩道檢查：入口 gate 擋下錯字搶註、依賴混淆與不存在的套件；安裝時用 lock file 的雜湊確認內容沒有被竄改。

```python
import hashlib

# 內部 registry 鏡像中「已核准」的套件（真實系統會有數千個）
APPROVED = {"requests", "urllib3", "httpx", "pydantic", "sqlalchemy", "python-dateutil"}
# 公開 registry 上實際存在的名稱（簡化）；攻擊者也能註冊新名稱
PUBLIC_INDEX = APPROVED | {"reqeusts", "python-dateutils", "arrow"}
INTERNAL_PREFIX = "harbor-"   # 內部套件只能從內部 registry 解析


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def admit(name: str, source: str) -> str:
    """新增依賴前的 gate：fail closed，任何不確定都擋下來交給人。"""
    if name.startswith(INTERNAL_PREFIX):
        return "允許" if source == "internal" else "拒絕：內部名稱不得從公開 registry 解析（dependency confusion）"
    if name in APPROVED:
        return "允許"
    near = [a for a in sorted(APPROVED) if edit_distance(name, a) <= 2]
    if near:
        return f"拒絕：名稱與已核准的 {near[0]} 只差 {edit_distance(name, near[0])} 個字元（疑似 typosquatting）"
    if name not in PUBLIC_INDEX:
        return "拒絕：registry 上不存在，可能是 AI 幻覺出的名稱（slopsquatting 風險）"
    return "待審：存在但未核准，需走新依賴審查"


requests_to_add = [
    ("requests", "public"),
    ("reqeusts", "public"),
    ("python-dateutils", "public"),
    ("harbor-payments-core", "public"),
    ("harbor-payments-core", "internal"),
    ("flask-harbor-auth-helper", "public"),
    ("arrow", "public"),
]
for name, source in requests_to_add:
    print(f"{name:<26} 來源={source:<8} → {admit(name, source)}")


# Lock file：記錄確切版本與內容雜湊，安裝時逐一比對
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


lock = {  # 套件: (版本, 建立 lock 時下載內容的雜湊)
    "httpkit": ("2.7.2", sha256(b"httpkit-2.7.2 wheel")),
    "pydantic": ("2.8.2", sha256(b"pydantic-2.8.2 wheel")),
}
downloaded = {  # 今天 CI 實際從 registry 拿到的內容
    "httpkit": b"httpkit-2.7.2 wheel + injected code",
    "pydantic": b"pydantic-2.8.2 wheel",
}
print()
for pkg, (version, expected) in lock.items():
    actual = sha256(downloaded[pkg])
    status = "雜湊相符，安裝" if actual == expected else "雜湊不符，停止安裝並告警"
    print(f"{pkg}=={version}：預期 {expected[:12]}…，實際 {actual[:12]}… → {status}")
```

執行結果：

```text
requests                   來源=public   → 允許
reqeusts                   來源=public   → 拒絕：名稱與已核准的 requests 只差 2 個字元（疑似 typosquatting）
python-dateutils           來源=public   → 拒絕：名稱與已核准的 python-dateutil 只差 1 個字元（疑似 typosquatting）
harbor-payments-core       來源=public   → 拒絕：內部名稱不得從公開 registry 解析（dependency confusion）
harbor-payments-core       來源=internal → 允許
flask-harbor-auth-helper   來源=public   → 拒絕：registry 上不存在，可能是 AI 幻覺出的名稱（slopsquatting 風險）
arrow                      來源=public   → 待審：存在但未核准，需走新依賴審查

httpkit==2.7.2：預期 335af3e210d2…，實際 104917c5eca1… → 雜湊不符，停止安裝並告警
pydantic==2.8.2：預期 273e2b22fc4b…，實際 273e2b22fc4b… → 雜湊相符，安裝
```

逐步解讀：

1. `admit` 的檢查順序有意義。內部前綴最先檢查：凡是 `harbor-` 開頭的名稱，只要來源不是內部 registry 就拒絕，這一條規則就消除了 dependency confusion，不需要比較版本號。
2. 名稱相近的檢查用 edit distance（編輯距離：把一個字串改成另一個需要的最少單字元增刪改次數）。`reqeusts` 與 `requests` 距離 2，`python-dateutils` 與 `python-dateutil` 距離 1，都被擋下。真實的 typosquatting 偵測還會考慮 `-`／`_` 互換、常見前綴後綴、鍵盤相鄰按鍵等變形。
3. 不存在的名稱直接拒絕。這對應故事中 AI agent 建議的套件：今天不存在，不代表明天不會被攻擊者註冊。所以 gate 的最後一層是「存在但未核准」也只能「待審」，而不是「允許」。**存在不等於可信**，這是整個 gate 採用 fail closed（不確定時預設拒絕）的理由。
4. 雜湊驗證那段顯示：版本號完全相同（`httpkit==2.7.2`），但內容被加了東西，雜湊就完全不同，安裝會被中止。真實的 lock file 記錄的是 registry 上發布檔案的 SHA-256，由 pip、npm 等工具在下載後自動比對。
5. 這兩道檢查都是**確定性**的規則，不依賴任何人或模型的判斷。這是刻意的設計：在供應鏈的入口，我們要的是可預測、可稽核、不會被說服的規則。需要判斷的部分（「這個新套件值不值得引入」）才交給人類審查。

## 20.13 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| Lock file 鎖定版本 | 鎖了之後沒人更新，漏洞也被鎖住 | `httpkit` 2.4.1 被鎖 14 個月，漏洞公布時落後多個版本 | Lock file 搭配自動更新與每季落後檢查 |
| 自動合併依賴更新 | 測試抓不到行為改變，regression 被自動送上 production | MINOR 升級把預設 timeout 從 30 秒改成 10 秒，推播在尖峰時段逾時 | 只對測試可信的範圍自動合併；高風險套件人工 review 加 canary |
| 嚴格的 SemVer 範圍（`==`） | 範圍互相衝突，菱形依賴無解；修補進不來 | 函式庫釘死確切版本，使用者無法升級共同依賴 | 函式庫用寬範圍、應用程式用 lock file |
| Vendoring | 升級變成手動，或有人直接修改 vendored 程式碼形成隱性 fork | `third_party/` 中的套件三年沒動，裡面還有人加過一個 patch 沒人記得 | 用工具管理 vendored 版本與 patch 清單；vendored 程式碼也納入自動更新 |
| Fork 外部套件解決衝突 | 組織要永遠維護一份只有自己用的版本 | 為了解開菱形依賴 fork 了 SDK，之後上游的安全修補要手動合併 | 優先等上游或協助上游修正；必須 fork 時設定回歸上游的期限 |
| 漏洞掃描全部當成緊急 | 噪音太多，真正嚴重的被淹沒 | 每週 80 個警告，團隊開始全部忽略 | 依嚴重度與可達性分級；不修補要有簽核與到期日 |
| 只信任「熱門」或「星星多」的套件 | 熱門套件的維護者帳號被接管時，影響最大 | `event-stream` 這類熱門套件被植入惡意依賴 | 雜湊鎖定、延遲數天再升級、限制安裝時的權限與網路 |
| 過厚的 wrapper | 為了「可替換」而重寫了整個套件的 API | Wrapper 比套件本身還大，替換時發現介面早已洩漏實作細節 | Wrapper 只暴露真正需要的少數功能 |

## 20.14 AI 時代：什麼變了？

**第一，新增依賴的門檻變得極低。** 以前工程師要自己搜尋、比較、閱讀文件，才會決定引入一個套件，這個摩擦力本身就是一道篩選。現在 coding agent 在幾秒內就會說「可以用某某套件」並直接修改 manifest。它傾向於引入套件來解決問題，有時一個只需要十行標準函式庫就能完成的功能，也會帶進一個新依賴。依賴圖會在沒有人刻意決定的情況下成長。

**第二，AI 會幻想出不存在的套件，而且這已經成為攻擊手法。** 語言模型可能根據命名習慣，生成一個「聽起來應該存在」的套件名稱。研究者發現這類幻覺名稱會在相似的提示下重複出現，這讓攻擊者有機會預先註冊這些名稱並放入惡意程式，等 agent 或照著 AI 建議操作的開發者來安裝。社群把這種攻擊稱為 **slopsquatting**（由 AI 產出的低品質內容「slop」與 typosquatting 組合而成）。Harbor 故事中那個「解析台灣地址」的套件就是一例：它今天不存在，但只要有人註冊，CI 就會安裝並執行它。

**第三，agent 在安裝時執行程式碼。** 一個有終端機權限的 agent 執行 `pip install` 或 `npm install`，就等於在它的執行環境中執行了該套件的安裝腳本。如果 agent 的環境中有 cloud credential、SSH key 或能 push 到 repo 的 token，一個惡意套件就能取得它們。

**第四，AI 也讓依賴維護變便宜。** 升級一個 major 版本最花時間的部分，是讀 changelog、找出 breaking change 影響的呼叫端、逐一修改。這些正是 agent 擅長的工作。搭配 Renovate 開出的 PR，agent 可以補上必要的程式修改與測試，讓「每季處理 major 升級」從一週的工作變成一天。

Harbor 據此調整了政策：agent 不能直接修改 manifest 或 lock file 而不在 PR 描述中明確列出；任何新增的 direct dependency 都要通過 20.12 那類確定性的 gate，並由人類完成新依賴審查；agent 的執行環境只能透過內部 registry 鏡像安裝套件，且不持有 production credential。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 比較標準函式庫、已核准套件與第三方套件，先回答「能不能不新增依賴」 | 是否引入新依賴由人類決定；新增 direct dependency 必須經過新依賴審查 |
| 閱讀 changelog 與 migration guide，列出 breaking change 影響的呼叫端並產生修改 PR | 高風險套件（金流、認證、加密）的升級需要 code owner review 與 canary；不得以修改或刪除測試讓 CI 通過 |
| 分析依賴圖：找出未使用的依賴、重複的 major 版本、間接依賴中的已知漏洞 | 是否接受一個漏洞的風險（不修補）由 owner 簽核並設定到期日 |
| 在漏洞公布時，查詢 SBOM 並彙整受影響的服務、版本與修補路徑 | 修補的優先順序與停機決策由人類決定；AI 的彙整要能對應到可重現的查詢 |
| 撰寫升級 PR 的描述，摘要版本差異與風險 | 摘要中引用的 changelog 內容要附原始連結，reviewer 抽查 |
| 在受限環境中執行安裝與建置 | 只能使用內部 registry 鏡像；套件名稱必須存在且通過 typosquatting／內部名稱檢查，不存在就 fail closed，不能讓模型「改猜另一個名稱」；安裝環境不持有 production credential，限制對外網路 |

> [!ai] AI 提醒
> 不要要求 AI「確認這個套件安全」然後採信它的回答。模型可能沒有最新的漏洞資料，也可能對一個不存在的套件給出看似合理的描述。套件是否存在、版本、雜湊、授權與已知漏洞，都要由確定性的工具查詢 registry 與漏洞資料庫取得；AI 的角色是整理與解釋這些查詢結果，而不是取代它們。

## 20.15 專家怎麼想

- **「最好的依賴是不新增的依賴。」** 資深工程師看到新增套件的 PR，第一個問題是能不能用標準函式庫或既有的核准套件做到。不是因為依賴不好，而是因為每個依賴都有長期成本，而這個成本由未來的團隊支付。
- **把「我們有沒有用到 X」當成必須在幾分鐘內回答的問題。** 專家會在平時就建立 SBOM 與查詢能力，因為漏洞公布那天沒有時間從頭盤點。能否快速回答，是供應鏈成熟度最直接的指標。
- **升級是持續的小成本，不是偶爾的大工程。** 有經驗的人寧可每週花半小時合併依賴更新，也不要兩年後花兩週處理一次大升級。他們會追蹤「落後最新版本多遠」，把它當成技術債的指標。
- **在入口用確定性的規則，在判斷處用人。** 名稱是否存在、雜湊是否相符、內部名稱是否從內部解析，這些用規則自動擋下；「值不值得引入」「要不要接受風險」才需要人。把兩者混在一起，不是太慢就是太鬆。
- **假設 build 環境會被攻擊。** 專家設計 CI 時會問：如果某個依賴的安裝腳本是惡意的，它能拿到什麼？答案應該是「幾乎什麼都拿不到」：沒有 production credential、網路受限、build 與發布分開。
- **SemVer 是溝通工具，不是保證。** 專家相信自己的測試多過版本號。升級後跑測試、觀察 canary，才是確認相容性的方法。

## 20.16 動手練習

1. 選一個你手上的專案，印出完整的依賴樹，數一數 direct 與 transitive dependency 各有幾個。找出依賴路徑最長的一個套件，以及被最多條路徑依賴的套件。
2. 修改 20.12 的程式一：在 `REGISTRY` 中加入 `crypto-lib` 這一層，讓 `payments-sdk` 2.4.0 依賴 `crypto-lib ^1.9`，而 `crypto-lib` 1.9.x 又依賴 `httpkit ^2.0`。觀察解析結果的變化，並加入一個功能：無解時印出是哪兩個限制衝突。
3. 延伸程式二的 `admit`：加入「`-` 與 `_` 視為相同」「忽略大小寫」兩種正規化，並加入一條規則：套件在 registry 上發布未滿 3 天時回傳「待審」。設計三個測試案例驗證新規則。
4. 為你的專案產生一份 SBOM（可用 SPDX 或 CycloneDX 格式的開源工具），然後假設某個間接依賴剛公布漏洞，寫下你要怎麼在 10 分鐘內確認哪些服務受影響。
5. 寫一份你團隊的依賴更新政策，至少包含：安全更新的時限、PATCH／MINOR／MAJOR 的處理方式、自動合併的條件、高風險套件清單，以及「不修補」的簽核流程。
6. 請一個 AI 助理推薦三個用於某個特定小功能的套件（例如「台灣身分證字號驗證」），逐一用 registry 確認它們是否存在、最近一次發布時間、維護者人數與授權。記錄有沒有不存在或名稱可疑的建議。

## 本章重點整理

- 依賴管理是管理你無法控制的程式碼；它的難處來自時間（世界一直在變）與規模（依賴的依賴）。
- 引入依賴承接的是它的 bug、漏洞、發布節奏、間接依賴、授權與可用性，成本要以整個生命週期估算。
- Transitive dependency 不在 manifest 中，但同樣在 build 與 production 裡，是你的攻擊面；每個服務都要能快速回答「我們有沒有用到某個版本」。
- SemVer 用 MAJOR.MINOR.PATCH 表達相容性，但版本號是作者的估計；依照 Hyrum's Law，「相容」的變更仍可能破壞使用者，所以要靠測試確認。
- Diamond dependency 是兩條路徑要求同一個套件的不相容版本；各生態系用報錯、選一個、並存或改名打包處理，都有代價。
- Manifest 表達意圖，lock file 記錄解析結果與雜湊；應用程式要提交 lock file，函式庫要使用寬範圍。
- Lock file 保證可重現，不保證安全；必須搭配持續的自動更新。
- 依賴管理有靜態、SemVer、bundled distribution、live at head 幾種模型；live at head 適合組織內部，需要強大的 CI 與 code search。
- 供應鏈攻擊包括 typosquatting、dependency confusion、維護者帳號被接管、build 系統被竄改與已知漏洞，且常在安裝時就執行。
- SBOM 是依賴清單，SLSA 定義 build 過程的可信等級，Sigstore 讓簽章與驗證變簡單；它們分別回答「有什麼」「怎麼來的」「是誰發布的」。
- 內部 registry 鏡像、內部名稱保留、雜湊鎖定、新依賴審查與限制安裝權限，能在入口處擋下多數攻擊。
- Dependabot、Renovate 類工具讓升級變成日常；要分組、排程、依風險決定是否自動合併，避免 PR 噪音。
- AI agent 降低了新增依賴的門檻，也會幻想不存在的套件名稱（slopsquatting 風險）；新增依賴要經過確定性的 gate 與人類審查。
- AI 適合處理升級的勞力工作與依賴圖分析，但套件是否存在、是否安全，必須由工具查詢 registry 與漏洞資料庫確認。

## 延伸問答

> [!question]- Q1. Lock file 解決了什麼問題？它沒有解決什麼問題？
> Lock file 解決的是**可重現性**：它把 manifest 中的版本範圍解析成每個套件（包括所有間接依賴）的確切版本，通常還記錄下載內容的雜湊。有了它，開發者的電腦、CI 與 production 的 build 會安裝完全相同的東西，「我這邊能跑、CI 壞了」這類問題大幅減少；雜湊也讓同版本號但內容被竄改的套件無法被安裝。升級也變成一個可 review 的動作：lock file 的差異會清楚出現在 PR 中。
>
> 它沒有解決的是**安全性與新鮮度**。Lock file 會忠實地把一個有漏洞的版本鎖住，Harbor 的 `httpkit` 2.4.1 就是這樣被鎖了 14 個月。它也不判斷套件來源是否可信、授權是否合適、維護者是否還在。所以 lock file 必須搭配漏洞掃描、自動更新與新依賴審查，它是依賴管理的基礎，不是全部。

> [!question]- Q2. 一個套件從 2.6.0 升到 2.7.0，按照 SemVer 應該向下相容，為什麼升級後你的服務還是壞了？
> 因為 SemVer 的「相容」是發布者的估計，範圍通常只涵蓋文件中寫明的 API。依照 Hyrum's Law，只要使用者夠多，任何可觀察的行為都會被某人依賴：預設 timeout、錯誤訊息的文字、回傳串列的順序、效能特性、甚至是某個 bug。作者把預設 timeout 從 30 秒改成 10 秒，可能真心認為這是改善，但對依賴舊行為的服務就是破壞性變更。
>
> 另一個常見原因是間接依賴：2.7.0 本身沒問題，但它把自己的某個依賴範圍放寬或提高，連帶讓解析器選到另一個套件的新版本。處理方式是不把版本號當保證：升級後跑自己的測試，重要服務經過 canary 觀察指標，並在 lock file 的差異中檢查除了目標套件外還有什麼變了。如果發現上游違反了它自己的相容性承諾，也值得回報給維護者。

> [!question]- Q3. 你的服務依賴 A 和 B，A 需要 C 的 1.x，B 的新版需要 C 的 2.x。你會怎麼處理？
> 這是典型的 diamond dependency。我會先確認問題的範圍：B 的新版是不是真的必要？如果只是想升級而沒有迫切需求，最簡單的選擇是暫時留在 B 的舊版，並記錄重新評估的時間。如果 B 的新版有必要（例如安全修補或關鍵功能），下一步是看 A 有沒有支援 C 2.x 的版本，或上游是否已有計畫；很多時候解法就是同時升級 A 與 B。
>
> 如果上游短期內不會支援，選項會變得昂貴：在允許多版本並存的生態系（例如 npm、Cargo 的不同 major）中，可能可以讓兩個版本共存，但要確認 A 與 B 之間不會互相傳遞 C 的物件；在只能有一個版本的生態系（例如 Python），就只能 fork 其中一個套件、修改依賴範圍並自行驗證，或把其中一個功能隔離到另一個 process 或服務中。Fork 會創造一份需要長期維護的版本，所以我會在 ADR 中寫明理由、退出條件與回歸上游的期限，同時考慮向上游貢獻修正。

> [!question]- Q4. Live at head 和 SemVer 有什麼根本差異？為什麼 Google 內部能做到 live at head，一般團隊對外部套件卻很難？
> 根本差異在於**誰負責相容性**。SemVer 模型中，提供者用版本號宣告相容性，使用者自己決定何時升級、在範圍內接受更新，出問題時由使用者發現。Live at head 模型中，使用者永遠依賴最新版本，提供者在提交任何變更前，必須先跑所有使用者的測試；會弄壞誰，就先幫誰修好或提供遷移工具。相容性的責任從「使用者小心升級」移到「提供者不能弄壞別人」。
>
> 這需要提供者能找到所有使用者、能執行他們的測試、能大規模修改他們的程式碼。在一個 monorepo 加上強大 CI 與 code search 的組織中，這些條件都具備，所以 Google 內部可以這樣做。但對外部開源套件，作者不知道全世界有誰在用、也無法跑你的測試，條件根本不存在。所以實務上的組合是：組織內部的共用函式庫可以朝 live at head 靠近，外部依賴則用 SemVer 加 lock file 加自動更新。

> [!question]- Q5. 什麼是 dependency confusion？Harbor 要怎麼防止？
> Dependency confusion 利用的是「安裝工具同時查詢多個 registry，並選版本號最高的那一個」這種行為。假設 Harbor 有一個只放在內部 registry 的私有套件 `harbor-payments-core`，版本 1.3。攻擊者在公開 registry 上註冊同名套件，發布版本 99.0，裡面放惡意的安裝腳本。如果 CI 的安裝設定同時看內部與公開 registry，它會認為 99.0 比較新而安裝攻擊者的版本，惡意程式就在 CI 中執行了。
>
> 防禦的核心是讓內部名稱不可能從公開來源解析。具體做法包括：所有內部套件使用固定前綴或 scope（例如 npm 的 `@harbor/`），並設定該前綴只能從內部 registry 解析；所有 build 只透過內部鏡像安裝，鏡像本身也遵守這個規則；必要時在公開 registry 先註冊這些名稱佔位；lock file 記錄雜湊，任何來源不同的內容都會被拒絕。20.12 的程式把「內部前綴必須來自內部」放在 gate 的第一條，就是因為這一條規則可以完全消除這類攻擊，而不必依賴版本比較。

> [!question]- Q6. 你是 Harbor 的 SRE 志明。一個嚴重漏洞剛被公布，影響一個常見的間接依賴。請描述你接下來 24 小時的行動。
> 第一步是確認影響範圍。如果 Harbor 有集中存放的 SBOM，我會直接查詢「哪些 production artifact 包含這個套件的受影響版本」，得到服務清單、版本與 owner；如果沒有，就只能逐一在各 repo 執行依賴樹指令並檢查 lock file，這也是事後要補的能力。同時我會閱讀漏洞公告，確認攻擊條件，例如是否需要特定設定、是否需要外部可控的輸入，這決定了哪些服務真的暴露在風險中。
>
> 第二步是止血與修補並行。對直接暴露在網際網路、且確定可達的服務，如果修補需要時間，先考慮暫時的緩解措施，例如在 WAF 或設定中關閉受影響的功能。修補時優先升級到修正版本；如果被 diamond dependency 卡住，就評估是否有修正版的同 major 版本，或暫時使用 override 強制指定。修補 PR 走一般的 CI 與 canary，但優先排程。第三步是溝通：在 incident 頻道定期更新哪些服務已修補、哪些還在處理。事後的 postmortem 要回答：我們花了多久知道自己受影響？為什麼這個依賴落後那麼多版本？要補上哪些 SBOM、自動更新或掃描的能力。

> [!question]- Q7. 團隊想對所有依賴更新開啟「CI 綠燈就自動合併」，你支持嗎？
> 我會支持有條件的自動合併，而不是全部。自動合併的前提是測試能抓到依賴升級造成的行為改變；如果測試覆蓋不到某個套件被使用的路徑，自動合併就只是把 regression 更快地送進 production。所以我會先依風險分層：PATCH 與 MINOR 更新、而且套件不在高風險清單（金流、認證、加密、序列化等）時，可以在 CI 綠燈後自動合併；MAJOR 更新與高風險套件一律人工 review，必要時經過 canary。
>
> 另外會加幾個條件：更新要分組與排程，避免每天幾十個 PR；新版本發布未滿幾天不自動升級，給社群時間發現被入侵的版本，但安全更新不受此限；合併後要能快速 revert，並監控依賴更新後的錯誤率。最後要追蹤成效，例如自動合併的更新被 revert 的比例，如果偏高，代表測試不足以支撐自動化，要先投資測試。

> [!question]- Q8. AI 情境：coding agent 在 PR 中新增了一個你沒聽過的套件，CI 全綠。你會怎麼審查？公司層面要建立什麼機制？
> 我不會因為 CI 綠燈就接受。第一步是確認套件真的存在、名稱正確：在 registry 上查詢它的發布歷史、維護者、下載量與原始碼位置，並比對它和知名套件的名稱是否只差幾個字元。AI 可能幻想出不存在的名稱，也可能拼錯成攻擊者註冊的相似名稱；如果套件是最近才出現、只有一個維護者、原始碼和描述對不上，就要高度懷疑。第二步是回到需求：這個功能是否用標準函式庫或已核准的套件就能做到？Agent 很容易為了小功能引入新依賴，而每個依賴都是長期成本。第三步是照一般的新依賴審查檢查授權、間接依賴數量與維護狀況。
>
> 公司層面要把這些檢查變成確定性的機制，而不是依賴每位 reviewer 記得去查。具體包括：agent 與 CI 只能從內部 registry 鏡像安裝；新增 direct dependency 時自動執行存在性、名稱相似度、內部前綴與發布時間的檢查，不確定就 fail closed；agent 不能讓模型在名稱不存在時「改猜另一個」；agent 的執行環境不持有 production credential 並限制網路；PR 中新增的依賴必須明確列在描述裡，並由人類完成新依賴審查。這樣即使 agent 犯錯，錯誤也會在進入 build 之前被擋下。

## 延伸閱讀

- [Software Engineering at Google — Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html)：原書第 21 章，討論 SemVer 的限制、diamond dependency、bundled distribution 與 live at head。
- [Software Engineering at Google — Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)：依賴如何進入 build，以及為什麼外部依賴要被明確宣告與版本化，可搭配第 27 章閱讀。
- [SLSA](https://slsa.dev/)：SLSA 框架的官方說明，包含 build track 各等級的要求與 provenance 格式。
- [OWASP Top 10 for Large Language Model Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)：LLM 應用的主要風險，其中包含供應鏈相關項目，可對照 20.14 的 AI guardrails。
