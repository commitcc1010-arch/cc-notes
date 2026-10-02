---
chapter: 27
title: Build Systems、Reproducibility 與 Provenance
part: 4
---

# 第 27 章　Build Systems、Reproducibility 與 Provenance

> [!abstract] 本章地圖
> **核心問題**：「在我的電腦上 build 得出來」為什麼不能當成部署的證據？我們要怎麼確定 production 上跑的那些 bytes，到底是由哪些輸入、在哪裡、被誰做出來的？
>
> **你會學到**：
> - 分辨 task-based 與 artifact-based build system，說清楚後者為什麼能安全地平行化與增量建置
> - 讀懂依賴圖，知道它如何決定建置順序、平行度與「改了什麼要重 build／重測什麼」
> - 理解 hermetic build、sandbox、remote cache 與 remote execution 的運作，以及 cache 什麼時候會給你錯的答案
> - 找出讓 build 不可重現的常見來源（時間戳記、檔案順序、浮動版本），並知道怎麼消除
> - 寫出可快取、可追溯的容器映像建置流程，堅持「build once, deploy many」
> - 理解 artifact provenance 與 SLSA Build Levels，並在部署前驗證 artifact 的來源
>
> **前置知識**：第 20 章（dependency 與 supply chain）、第 26 章（hermetic test）
>
> **對應原書**：SWE 第 18 章〈Build Systems and Build Philosophy〉

## 27.1 故事：同一個 tag，兩份不同的 bytes

Harbor 成立第二年年底，公司已經四十多人，分成 checkout、payments、search、seller、platform 五個團隊。checkout 團隊週一修好了一個 checkout 折扣計算的 bug，CI 建出容器映像 `checkout:1.8.2`，部署到 staging，QA 跑完整套結帳流程，一切正常。上線排在週四。

週三，有人發現 CI pipeline 的某個步驟因為網路抖動失敗過一次，順手按了「重新執行」。pipeline 重新跑了 `pip install -r requirements.txt`，又建了一次映像，推到 registry，標籤一樣是 `checkout:1.8.2`，蓋掉了週一那一份。沒有人注意到，因為 tag 沒變、commit 沒變、pipeline 是綠的。

週四上線後二十分鐘，付款成功率從 99.9% 掉到 96%。值班的 platform 工程師志明先懷疑金流商，再懷疑網路，最後才想到「是不是新版本」。但 staging 上的 `1.8.2` 明明測過。直到 checkout 團隊的 tech lead 美華比對兩台機器上的映像 digest（由內容計算出的雜湊值），才發現 staging 跑的和 production 跑的根本不是同一份東西。原因是 `requirements.txt` 只寫了 `httpclient>=2.1`，週二上游發布了 2.3 版，改了連線池的預設行為；週三那次重新建置自動拿到了新版本。

回滾花了四十分鐘，因為團隊一開始不敢確定 `1.8.1` 這個 tag 有沒有也被重建過。事後檢討時，platform 團隊的志明問了三個問題：production 上現在跑的 bytes 是從哪個 commit 來的？裡面有哪些依賴、各是什麼版本？是哪台機器、用什麼指令做出來的？會議室裡沒有人能用證據回答。

同一場會議上，seller 團隊的初階工程師阿凱也提出一個長期的抱怨：CI 每次都要 25 分鐘，因為 build script 不管改了什麼都從頭編譯、從頭安裝依賴。大家為了省時間，常在自己的筆電上 build 好再手動推映像，而每個人的筆電環境都不一樣。

這兩件事看起來一個是「慢」、一個是「錯」，其實是同一個問題的兩面：Harbor 的 build 沒有明確知道自己的輸入是什麼。這一章要回答的就是：一個好的 build system 怎麼知道它的輸入、怎麼因此變快、怎麼讓結果可以重現，以及怎麼留下證據，讓任何人都能驗證 production 上的 artifact 是怎麼來的。

## 27.2 Build system 到底在做什麼

### 從原始碼到 artifact

**Build**（建置）是把原始碼、依賴、工具與設定，轉換成可以執行或部署的東西的過程。轉換出來的東西叫 **建置產物**（artifact），例如一個 Java 的 jar 檔、一個 Go 的執行檔、一個 Python wheel，或一個容器映像。Harbor 的 checkout 服務從一堆 `.py` 檔加上 `requirements.txt`，最後變成一個可以在 Kubernetes 上執行的映像，這就是一次 build。

參與 build 的東西可以分成五類，理解這五類是本章的基礎：

| 類別 | 是什麼 | Harbor 的例子 | 被忽略時的後果 |
|---|---|---|---|
| Source | 自己寫的程式碼 | `checkout/*.py` | 很少被忽略 |
| Dependencies | 第三方或內部套件 | `httpclient`、`harbor-money` | 版本浮動，週三重建拿到新版 |
| **Toolchain**（工具鏈） | 編譯器、直譯器、打包工具本身 | Python 3.12.4、pip 24.x、Docker | 不同機器產生不同結果 |
| Configuration | build 時讀取的設定、旗標 | `config/tax.json`、編譯旗標 | 改了設定卻沒觸發重建 |
| Environment | 機器狀態 | 時區、locale、環境變數、使用者名稱、目前時間 | 「在我電腦上可以」 |

### 為什麼不能只靠 compiler

最小的專案只需要一個指令：`python app.py` 或 `javac Main.java`。但當專案有上百個檔案、幾十個內部模組、上百個外部依賴，事情就變了。你需要知道模組之間誰依賴誰、該用什麼順序編譯、哪些東西可以同時編譯、改了一個檔案之後哪些東西需要重做。

很多團隊的下一步是寫 shell script：先裝依賴、再編譯 A、再編譯 B、再跑測試、再打包。這在一開始很有效，但隨著專案變大，script 會變成沒人敢動的怪物：它總是從頭做全部的事，所以很慢；它沒有記錄「為什麼要這個順序」，所以很難平行化；它依賴執行者機器上剛好裝了什麼，所以每個人跑出來的結果不一樣。

**Build system**（建置系統）就是為了解決這些問題而存在的工具。它的工作可以濃縮成一句話：**給定一組輸入，以正確的順序、盡量少的工作量、盡量平行地產生正確的輸出**。《Software Engineering at Google》把 build system 視為工程師生產力的基礎設施，理由很直接：每一次修改、每一次測試、每一次部署都要經過它。它慢一分鐘，全公司每天就慢上千分鐘；它錯一次，所有下游的證據都不可信。

## 27.3 Task-based build：告訴系統「怎麼做」

### 運作方式

第一代、也是今天仍然最常見的 build system 是 **task-based**（以任務為中心）的：你定義一組 task（任務），每個 task 是一段要執行的指令，並宣告它依賴哪些其他 task。Make、Ant、Maven、Gradle、npm scripts 都屬於這一類。

一個簡化的 Makefile 長這樣：

```text
checkout.tar: pricing.so checkout.py
	./package.sh checkout.tar

pricing.so: pricing.c
	gcc -O2 -shared -o pricing.so pricing.c
```

Make 讀到 `checkout.tar` 依賴 `pricing.so` 與 `checkout.py`，會先確保 `pricing.so` 是新的，再執行打包指令。判斷「是否需要重做」的方法是比較檔案的修改時間：如果 `pricing.c` 比 `pricing.so` 新，就重新編譯。

### 為什麼它在大型專案會出問題

Task-based build 的根本特徵是：**task 是一段任意的指令，build system 不知道它實際讀了什麼、寫了什麼**。這帶來三個隨規模放大的問題。

第一，**難以安全平行化**。兩個 task 如果沒有宣告依賴關係，build system 會認為可以同時執行。但如果它們其實都寫入同一個暫存目錄，或一個偷偷讀了另一個的輸出，平行執行就會產生時好時壞的結果。因為系統看不到 task 的內部，它無法替你檢查。

第二，**難以正確地增量建置**。**Incremental build**（增量建置）是只重做受影響的部分。Make 用修改時間判斷，但修改時間會被 `git checkout`、複製檔案、時鐘不同步弄亂；更麻煩的是，task 可能讀了沒有宣告的檔案或環境變數，那些東西改了，系統完全不知道。結果是工程師學會一句咒語：「怪怪的？先 `make clean` 再 build 一次。」每次 clean build 都是對增量建置失去信任的證據。

第三，**難以維護與除錯**。task 是程式，而且往往是沒人測試的程式。一個大型 Gradle 或 Maven 專案的 build 邏輯分散在 plugin、繼承的設定與自訂 script 中，出問題時要追查「到底是哪段邏輯改了這個檔案」非常困難。

> [!note]
> 現代的 task-based 工具也在往前走。例如 Gradle 鼓勵 task 宣告 inputs 與 outputs 以支援 build cache，npm 生態系的 monorepo 工具也會依宣告的輸入快取任務結果。兩種模式的界線因此變得模糊。真正的差別在於：宣告是選擇性的「最佳化提示」，還是強制的、被 sandbox 檢查的「契約」。

## 27.4 Artifact-based build：宣告你要「什麼」

### 換一個問題問

Google 內部的 Blaze，以及它的開源版本 **Bazel**，代表另一種思路：**artifact-based**（以建置產物為中心）的 build。工程師不再寫「要執行哪些指令」，而是宣告「我要哪些 artifact、它們由哪些輸入構成」。怎麼執行、用什麼順序、哪些可以平行、哪些可以跳過，全部交給 build system 決定。同類的工具還有 Buck2、Pants、Please 等。

在 Bazel 中，這些宣告寫在每個目錄的 `BUILD` 檔裡，語言是 Python 風格的 **Starlark**。Harbor 若改用 Bazel，checkout 的 BUILD 檔可能長這樣：

```text
py_library(
    name = "pricing",
    srcs = ["pricing.py"],
    data = ["//config:tax.json"],
    deps = ["//lib/money", "@pypi//httpclient"],
)

py_binary(
    name = "server",
    srcs = ["server.py"],
    deps = [":pricing"],
    visibility = ["//deploy:__pkg__"],
)
```

每一個 `name` 就是一個 **target**（目標），用 **label** 指稱，例如 `//checkout:pricing`。`srcs` 是原始碼，`deps` 是它依賴的其他 target，`data` 是執行時需要的資料檔，`@pypi//httpclient` 是外部依賴。工程師執行 `bazel build //checkout:server`，系統就會從這個 target 往下展開整棵依賴樹，建出所需的一切。

### 把 build 當成函數

這種設計的核心想法是把 build 當成**純函數**：輸出只由宣告的輸入決定。相同的原始碼、相同的依賴版本、相同的 toolchain，就一定得到相同的 artifact。這個假設一旦成立，很多原本困難的事都變簡單了：

- **平行化**：沒有依賴關係的 target 一定可以同時建，因為它們的輸入互不相干。
- **增量建置**：只要某個 target 的輸入沒變，它的輸出就不用重做；不再需要比較修改時間，而是比較內容雜湊。
- **快取與分散式執行**：既然輸出只由輸入決定，任何一台機器算出來的結果都可以給其他機器用（27.7 節）。

《Software Engineering at Google》把這個轉變比喻成從命令式程式設計走向函數式程式設計：你描述結果，而不是描述步驟，系統因此有空間替你做最佳化。代價是你必須把依賴「講清楚」，這比隨手寫一段 script 麻煩，也需要團隊學習新工具。原書把這一章的核心教訓歸結為一個反直覺的觀點：適度限制工程師在 build 中的權力與彈性，反而能提高整體生產力。

### 細粒度模組與可見性

Artifact-based build 鼓勵把程式切成很小的 target。原書指出，Google 傾向使用比 task-based build 常見寫法細得多的模組：以 Java 為例，每個目錄通常只有一個 package、一個 target 與一個 BUILD 檔，這種做法在另一個源自 Blaze 的系統 Pants 中被稱為 **1:1:1 規則**。原因是 target 越細，依賴圖越精確：改了 `pricing.py`，只有真正依賴 `pricing` 的東西要重建和重測，而不是整個 checkout 目錄下的一切。代價是 BUILD 檔變多，需要工具自動產生與維護依賴宣告。

兩個配套機制讓依賴圖保持健康：

- **Visibility**（可見性）：上例中 `server` 只開放給 `//deploy` 使用。沒有被允許的 target 不能依賴它，這讓團隊可以控制「誰能依賴我」，避免內部實作被到處引用（這正是第 5 章 Hyrum's Law 的防線之一）。
- **Strict dependencies**（嚴格依賴）：如果 `server.py` 直接 import 了 `money` 模組，就必須在自己的 `deps` 中宣告 `//lib/money`，不能靠 `pricing` 間接帶進來。否則哪天 `pricing` 不再依賴 `money`，`server` 就莫名其妙壞掉。

> [!warning] 常見誤解
> 「導入 Bazel 就會變快。」不一定。Artifact-based build 的速度來自精確的依賴圖、有效的快取與沒有偷讀的輸入。如果 BUILD 檔把整個 repository 包成一個巨大的 target，或大量使用會打破 hermeticity 的規則，你只是換了一個更難學的 Make。工具是必要條件，依賴圖的品質才是關鍵。

## 27.5 依賴圖：build 的地圖

### DAG 與拓撲順序

不管哪種 build system，背後都是一張 **dependency graph**（依賴圖）：節點是 target，箭頭表示「依賴」。這張圖必須是 **DAG**（directed acyclic graph，有向無環圖），也就是不能有循環依賴；如果 A 依賴 B、B 又依賴 A，就沒有任何順序能把兩者都建出來。

Harbor 的部分依賴圖如下：

```text
                    //deploy:checkout_image
                     /                   \
        //checkout:server            //base:python_runtime
           /          \                        |
 //checkout:pricing   //checkout:api      (外部) python:3.12 base image
      /       \              |
//lib/money  //config:tax  //lib/http
                              |
                       (外部) @pypi//httpclient==2.1.4
```

讀這張圖的方法是從下往上：最底層的葉子節點（`//lib/money`、`//config:tax`、外部套件）沒有依賴，可以最先、也可以同時處理；`//checkout:pricing` 要等 `money` 與 `tax` 好了才能開始；最頂端的映像要等所有東西都完成。把節點排成「每個節點都在它的依賴之後」的順序，叫做**拓撲排序**（topological sort），這就是 build system 決定執行順序的方式。

### 依賴圖回答的三個問題

**第一，最快能多快？** 圖中最長的一條路徑叫 **critical path**（關鍵路徑）。就算你有無限多台機器，build 時間也不會短於關鍵路徑上所有步驟的總和。想讓 build 變快，與其加機器，不如找出關鍵路徑上最慢的步驟，把它拆小或移出路徑。

**第二，改了什麼要重做？** 把箭頭反過來看，就得到 **reverse dependencies**（反向依賴）：誰依賴我。改了 `//lib/money`，受影響的是 `pricing`、`server`、映像，以及其他所有直接或間接用到 `money` 的 target，但 `//checkout:api` 不受影響。第 28 章的 test selection 就是用這個方法決定 presubmit 該跑哪些測試。

**第三，誰會被我影響？** 這是第二個問題在組織層面的版本。一個被三百個 target 依賴的共用函式庫，任何修改都有三百個潛在的受害者。依賴圖讓這個風險變得可見，也讓「這個函式庫該不該再拆小」成為一個有數據的討論。

### 外部依賴要釘死

依賴圖的葉子常常是外部套件，這也是 Harbor 週三事故的源頭：`httpclient>=2.1` 是一個「範圍」，不是一個輸入。範圍代表「今天解析出來的版本」和「明天解析出來的版本」可能不同，同一份原始碼就不再對應同一個 artifact。

可靠的 build 會把每個外部依賴解析成精確版本，並用內容雜湊驗證下載的檔案：Python 用帶 hash 的 lock file 配合 `pip install --require-hashes`，或使用 uv、Poetry 這類會產生 lock file 的工具；Bazel 的外部依賴宣告可以附上 `sha256`，下載內容不符就直接失敗。第 20 章討論了 lock file、SemVer 與依賴升級策略；這裡要強調的是 build 的角度：**範圍是給人看的意圖，雜湊才是給 build system 的輸入**。

## 27.6 Hermetic build：只用宣告的東西

### 定義

**Hermetic build**（封閉式建置）是指 build 的每一個步驟只能看到它宣告的輸入，看不到機器上其他任何東西。它不能讀使用者家目錄裡的設定、不能用系統上剛好裝了的某個版本的 compiler、不能在 build 途中上網下載東西。第 26 章談過 hermetic test，觀念相同：結果只取決於明確給定的輸入。

Hermeticity 有兩個常被忽略的部分：

- **Toolchain 也是輸入**。Python 3.11 和 3.12 產生的 bytecode 不同，不同版本的 gcc 可能產生不同的機器碼；就連 patch 版本之間，打包工具的行為也可能有細微差異。在 hermetic build 中，toolchain 本身被當成一個有版本、有雜湊的依賴，由 build system 下載與管理，而不是「用機器上的 `python3`」。
- **網路是最大的隱藏輸入**。一個在 build 途中執行 `curl https://.../latest.tar.gz` 的步驟，等於把「那個網址此刻的內容」當成輸入，而這個輸入隨時會變，也可能被攻擊者替換。

### Sandbox：讓偷讀變成錯誤

光靠紀律很難維持 hermeticity，因為偷讀通常是無意的：某個工具預設會讀 `~/.npmrc`、某個測試剛好用到系統時區。所以 artifact-based build system 會用 **sandbox**（沙箱）執行每個步驟：在一個只放了宣告輸入的臨時目錄中執行指令，並視平台限制網路與檔案系統存取。在 sandbox 中，沒宣告的檔案根本不存在，偷讀就會立刻失敗。

這聽起來很嚴格，實際效果是把「三個月後才發現的神祕快取錯誤」變成「今天就看到的明確錯誤訊息」。錯誤越早、越明確，修起來越便宜，這和第 28 章 CI 的核心想法一致。

> [!example] 例子
> Harbor 的一個測試在阿凱的筆電上通過、在 CI 失敗，錯誤是日期格式不同。原因是筆電的 locale 是 `zh_TW.UTF-8`，CI 機器是 `C.UTF-8`，而程式用了依賴 locale 的格式化函式。在 sandbox 中固定 locale 與時區後，兩邊行為一致；更好的修法是程式本身不依賴系統 locale。

### 實務上怎麼逐步做到

完全 hermetic 是一個方向，不是一天能達成的狀態。Harbor 採取的順序是：先把所有外部依賴釘到精確版本並驗證雜湊；再把 build 放進固定的 builder 映像中執行，而不是在開發者筆電上；接著禁止 build 步驟存取網路，所有依賴改從內部的 artifact mirror（依賴鏡像，一個代理並快取外部套件的內部服務）取得；最後才導入 artifact-based 工具，對個別步驟做 sandbox。每一步都讓「同樣輸入、同樣輸出」更接近真實。

## 27.7 Cache：速度的來源，也是錯誤的來源

### Action key 與 content-addressable storage

一旦 build 的每個步驟（稱為 **action**）都是「宣告的輸入 → 確定的輸出」，就可以安全地快取。做法是替每個 action 計算一個 **action key**：把它的指令、所有輸入檔案的內容雜湊、toolchain 版本、相關環境變數一起雜湊，得到一個字串。只要 action key 相同，輸出就應該相同，可以直接重用。

```text
action key = hash( 指令與參數
                 + 每個輸入檔案的內容 digest
                 + 依賴 target 的輸出 digest
                 + toolchain 版本
                 + 宣告的環境變數 )

Action Cache:   action key   ──→  輸出的 digest
CAS:            輸出的 digest ──→  輸出的實際 bytes
```

這裡有兩張表。**Action cache** 記錄「這個 action 以前算出的輸出是哪個 digest」；**CAS**（content-addressable storage，內容定址儲存）以內容的雜湊為鍵，存放實際的檔案。用內容雜湊當鍵有兩個好處：同樣的內容只存一份；拿到一個 digest 就能驗證內容有沒有被改過。

注意這裡用內容雜湊，而不是 Make 的修改時間。這帶來一個實用的效果，叫 **early cutoff**（提早截斷）：如果你只改了 `pricing.py` 的註解，編譯後的輸出 bytes 可能完全相同，那麼依賴 `pricing` 的下游 action key 就不會變，整串下游都可以直接命中快取。

### Local cache、remote cache 與 remote execution

**Local cache** 存在你自己的機器上，讓第二次 build 很快。**Remote cache**（遠端快取）把 action cache 與 CAS 放在團隊共用的服務上：CI 建過的東西，阿凱的筆電可以直接下載，不必自己編譯。對 Harbor 這種四十多人、每天上百次 build 的組織，remote cache 常常是讓 CI 從 25 分鐘降到幾分鐘的最大因素，因為大部分 target 在大部分變更中都沒有變。

再進一步是 **remote execution**（遠端執行）：build system 不只是下載快取結果，連沒命中快取的 action 也送到一群遠端機器上平行執行。開發者的筆電只負責分析依賴圖與發送工作，實際的編譯與測試在幾十或幾百台機器上同時進行。Bazel 使用開放的 Remote Execution API，有多個開源與商業實作；Google 內部的大規模分散式建置正是原書描述的這種模式。Remote execution 天然要求 hermeticity：遠端機器上沒有你筆電的任何狀態，沒宣告的輸入就是不存在。

```text
開發者 / CI
   │ 1. 分析依賴圖，算出每個 action key
   ▼
┌──────────────────┐   2. 查 action cache    ┌──────────────┐
│  build client    │ ───────────────────────▶│ Action Cache │
│ (bazel 等)       │◀── 命中：回傳輸出 digest ─│              │
└──────────────────┘                          └──────────────┘
   │ 3. 未命中：送出 action                       ▲
   ▼                                              │ 5. 寫入結果
┌──────────────────┐   4. 從 CAS 取輸入、執行     │
│ remote executors │ ─────────────────────────────┘
│ (sandbox, 多台)   │ ──▶ CAS（輸出 bytes，以 digest 為鍵）
└──────────────────┘
```

流程是：client 先算出 action key（第 1 步）並查詢 action cache（第 2 步）；命中就直接從 CAS 下載輸出，完全不執行。未命中才把 action 交給遠端執行器（第 3 步），執行器從 CAS 取得輸入檔案、在 sandbox 中執行（第 4 步），再把輸出寫回 CAS、把 action key 與輸出 digest 的對應寫回 action cache（第 5 步）。下一個人做同樣的 action 時，就會在第 2 步命中。

### 快取何時會說謊

快取的正確性建立在一個前提上：**action key 涵蓋了所有會影響輸出的東西**。這個前提被打破時，快取會很有信心地給你錯的答案，而且沒有任何錯誤訊息。常見的破口有三種。

第一，**沒宣告的輸入**。一個步驟偷讀了某個設定檔、環境變數或系統時間，而它們沒有進入 action key。設定改了，key 沒變，快取回傳舊的輸出。27.11 節的程式會重現這個情況：稅率從 5% 改成 8%，build 卻全部命中快取，映像裡還是 5%。

第二，**不確定的輸出**。如果同一個 action 每次執行都產生不同 bytes（例如嵌入了建置時間），快取不會「錯」，但會失效：下游的 action key 每次都不同，early cutoff 不再發生，快取命中率大幅下降。這是 27.8 節 reproducible build 與快取效率的連結。

第三，**快取被污染**。Remote cache 是共用的，如果任何人都能寫入，一台被入侵或設定錯誤的開發者筆電就可以把錯誤甚至惡意的輸出放進快取，而所有人都會信任它。這種攻擊叫 **cache poisoning**（快取投毒）。實務上的防線是：只有受信任的 CI builder 能寫入 remote cache，開發者機器只能讀；寫入的結果要能追溯到哪個 builder、哪次執行。

> [!warning] 常見誤解
> 「快取出問題就清掉重建。」清快取只能讓這一次結果正確，不會修好原因。每次「清快取就好了」的經驗，都代表依賴圖裡有一條沒宣告的邊。正確的做法是找出那個沒宣告的輸入、把它加進宣告，或讓 sandbox 把它擋掉。

## 27.8 Reproducible build：同樣輸入，同樣 bytes

### 定義與為什麼重要

**Reproducible build**（可重現建置）是指：給定相同的原始碼、相同的建置環境與相同的建置指令，任何人都能重新做出逐位元相同（bit-for-bit identical）的 artifact。這個定義來自開源社群的 Reproducible Builds 專案，Debian 等 Linux 發行版投入多年讓大部分套件可以重現。

它重要的理由有三個。**除錯**：當 production 出問題時，你能在本機重建出一模一樣的 bytes 來調查，而不是一份「應該差不多」的東西。**快取效率**：如上一節所說，確定的輸出讓下游快取能命中。**安全驗證**：如果兩個彼此獨立的 builder 從同一份 source 建出相同的 digest，就很難相信其中一個被動了手腳；反之，若官方發布的 binary 與你自己從 source 建出的不同，就值得追查。

要分清楚三個相關但不同的詞：**hermetic** 描述的是過程（只用宣告的輸入）；**deterministic**（確定性）描述的是單一步驟（同樣輸入每次得到同樣輸出）；**reproducible** 描述的是結果（任何人都能重建出相同 bytes）。Hermetic 是 reproducible 的必要基礎，但不充分：一個完全 hermetic 的步驟，若把建置時間寫進輸出，結果仍然不可重現。

### 不可重現的常見來源

| 來源 | 例子 | 常見解法 |
|---|---|---|
| 時間戳記 | 壓縮檔記錄每個檔案的修改時間；程式碼嵌入「建置於 2024-12-12 14:03」 | 使用 `SOURCE_DATE_EPOCH` 環境變數（通常設為最後一次 commit 的時間）取代目前時間 |
| 檔案順序 | 目錄列舉順序依檔案系統而異，打包時順序不同 | 打包前排序檔名 |
| 使用者與路徑 | 壓縮檔記錄 uid／gid；除錯資訊嵌入 `/home/akai/harbor` 這種絕對路徑 | 正規化擁有者；使用編譯器的路徑重映射選項（例如 Go 的 `-trimpath`） |
| 浮動依賴 | `>=2.1`、`latest`、`apt-get update` 的結果每天不同 | Lock file 加雜湊；套件來源使用固定的快照或內部 mirror |
| 隨機性與雜湊順序 | 輸出 dict 或 set 的順序；隨機產生的 ID | 輸出前排序；固定種子 |
| 平行度 | 多執行緒寫同一個檔案的順序不同 | 讓輸出順序不依賴執行順序 |
| 語言特有快取 | Python `.pyc` 預設記錄原始檔的修改時間 | 使用 hash-based `.pyc`（PEP 552）或不打包 `.pyc` |

這張表的共同點是：每一項都是「沒有被當成輸入的環境」偷偷進入了輸出。消除它們的方法也一樣：要嘛把它固定下來（排序、固定時間），要嘛把它從輸出中移除（不嵌入路徑與使用者）。

### 實務上做到什麼程度

不是每個團隊都需要逐位元可重現。對大多數服務團隊，務實的目標分三級：第一級，**每個 artifact 都能追溯到確切的 source 與依賴**（下一節的 provenance），這是必須的；第二級，**在同一個 builder 映像中重建，得到相同 digest**，這讓除錯與快取都受益，大部分語言花一些功夫就能做到；第三級，**任何人在任何環境獨立重建都相同**，這對開源發行版、安全敏感的軟體很有價值，但成本較高。

驗證可重現性的方法很直接：在乾淨的環境中建兩次（最好在不同時間、不同機器），比較 digest。不同就用 diff 工具（例如 diffoscope）比較兩個 artifact 的內容，找出差異來自哪一項。Harbor 把「同一個 commit 建兩次 digest 相同」加入每週的定期檢查，一旦失敗就開 ticket，而不是等到哪天需要重建時才發現做不到。

## 27.9 容器映像建置

### 映像是一疊 layer

容器映像是今天最常見的部署 artifact。一個映像由多層 **layer** 組成，每一層是一組檔案變更，以內容雜湊識別；映像的 **manifest** 列出所有 layer 的 digest，manifest 本身的雜湊就是映像的 **digest**。因為是內容定址，改了任何一個 byte，digest 就會改變；反過來，只要 digest 相同，內容就一定相同。

這就引出 Harbor 週三事故的核心：**tag 和 digest 是兩種完全不同的東西**。

| | Tag（例如 `checkout:1.8.2`） | Digest（例如 `checkout@sha256:4f1e…`） |
|---|---|---|
| 是什麼 | 一個指向某份 manifest 的名稱 | 內容的雜湊 |
| 可變嗎 | 可以被重新指向另一份內容 | 不可變，內容改了 digest 就不同 |
| 適合 | 給人閱讀、搜尋 | 部署、驗證、記錄證據 |

Registry 可以設定 tag 不可覆寫（immutable tags），這能防止 Harbor 的週三事故再次發生。但更根本的做法是：**部署設定一律引用 digest**，tag 只當成方便人類閱讀的別名。

### 寫一個好的 Dockerfile

Dockerfile 是一種 task-based 的 build 描述：每一行指令產生一層 layer，Docker（或 BuildKit）以「指令內容加上前一層」判斷能否重用快取。因此指令的順序直接決定快取效率。Harbor 原本的 Dockerfile 與改善後的版本對照如下：

```text
# 改善前                               # 改善後
FROM python:3.12                       FROM python:3.12-slim@sha256:<固定的 digest> AS build
COPY . /app                            WORKDIR /app
RUN pip install -r /app/requirements.txt COPY requirements.lock .
CMD ["python", "/app/server.py"]       RUN pip install --require-hashes --no-cache-dir \
                                           --target=/deps -r requirements.lock
                                       COPY checkout/ ./checkout/

                                       FROM python:3.12-slim@sha256:<固定的 digest>
                                       COPY --from=build /deps /deps
                                       COPY --from=build /app/checkout /app/checkout
                                       ENV PYTHONPATH=/deps
                                       USER 10001
                                       CMD ["python", "/app/checkout/server.py"]
```

改善的地方逐一說明：

1. **Base image 用 digest 固定**。`python:3.12` 是一個會隨上游更新而移動的 tag，今天和下個月拿到的內容不同。用 digest 固定後，更新 base image 變成一個明確、可 review 的變更（可以交給 Renovate 這類工具定期開 PR）。
2. **先複製 lock file、安裝依賴，再複製原始碼**。改善前的版本先 `COPY . /app`，任何一行程式碼改動都會讓後面的 `pip install` 快取失效，每次都重裝依賴。調整順序後，只有 lock file 改變時才重裝。
3. **依賴用雜湊驗證**。`--require-hashes` 讓 pip 拒絕任何雜湊不符的套件，週三那種「範圍解析到新版本」不會再發生。
4. **Multi-stage build**（多階段建置）。第一階段負責安裝與編譯，第二階段只複製執行需要的檔案。最終映像不含 build 工具與暫存檔，更小、攻擊面也更少。
5. **以非 root 使用者執行**，降低容器被攻破時的影響範圍。

還有幾個 Dockerfile 範例裡看不到、但同樣重要的做法：用 `.dockerignore` 排除 `.git`、本機虛擬環境與測試資料，避免它們進入 build context 並污染快取；build 時需要的憑證（例如私有套件庫的 token）用 BuildKit 的 secret mount 傳入，絕不寫進 `ENV` 或 `COPY`，因為任何進入 layer 的檔案都會永久留在映像歷史中，即使後面一層把它刪掉也一樣。

要做到可重現的映像，還要處理 layer 中的檔案時間戳記。較新版本的 BuildKit 支援以 `SOURCE_DATE_EPOCH` 固定映像中繼資料裡的時間，並可選擇一併改寫 layer 內檔案的時間戳記（細節依版本而定，導入前要查對應版本的文件）；也有不透過 Dockerfile、直接由 build system 組裝映像的工具（例如 Go 的 ko、Java 的 Jib，以及 Bazel 的映像規則），它們更容易產生確定的 layer。

### Build once, deploy many

Harbor 事故的另一個教訓是：**每個環境都不應該各自重建**。如果 staging 用一次 build、production 再 build 一次，就算 commit 相同，你也無法保證兩份 bytes 相同，staging 上做的所有測試與 canary 都無法轉移成 production 的證據。

正確的流程是：CI 對一個 commit 只建一次，得到一個 digest；這個 digest 依序被部署到 staging、canary、production。環境之間的差異（資料庫位址、功能開關、資源配額）在部署時以設定注入，而不是建進映像。這樣「staging 測過的東西」和「production 跑的東西」在數學上是同一個，第 29 章的 canary 分析才有意義。

## 27.10 Provenance 與 SLSA：讓 artifact 自帶出生證明

### Digest 回答「是什麼」，provenance 回答「怎麼來的」

Digest 能證明兩份 bytes 是否相同，但它沒辦法告訴你這份 bytes 是從哪裡來的。志明在檢討會上的三個問題（哪個 commit、哪些依賴、哪台機器用什麼指令）需要另一種資料：**provenance**（來源證明）。

Provenance 是一份描述 artifact 如何被產生的紀錄，由 builder 在建置時自動產生。業界常用的格式是 SLSA Provenance，包裝在 in-toto attestation（一種「對某個 artifact 做出聲明」的標準格式）中。它的主要內容是：

- **Subject**：這份紀錄描述的 artifact，以 digest 識別。
- **Build definition**：建置的類型、外部參數（哪個 repository、哪個 branch 或 tag）、解析後的依賴（精確的 commit 與套件 digest）。
- **Run details**：由哪個 builder 執行（builder ID）、這次執行的識別碼、時間等。

Provenance 本身也必須被保護，否則任何人都能偽造一份。做法是由 builder **簽章**：只有受信任的 builder 持有簽章的身分或私鑰，驗證者用對應的公開資訊確認紀錄是真的、沒被改過。開源生態常用 **Sigstore** 處理簽章：它以 CI 的 OIDC 身分換取短效憑證來簽章（因此不必長期保管私鑰），並把簽章紀錄寫入公開的透明日誌。第 20 章從依賴管理的角度介紹過 SBOM 與 Sigstore；本章關注的是 build 的那一端：artifact 怎麼帶著可驗證的出身資料離開 builder。

### SLSA Build Levels

**SLSA**（Supply-chain Levels for Software Artifacts，讀作 salsa）是一個由業界共同維護的框架，把「build 有多可信」分成幾個等級。SLSA v1.0 的 Build track 定義如下：

| 等級 | 要求 | 能防止什麼 | Harbor 的狀態 |
|---|---|---|---|
| Build L0 | 沒有要求 | 什麼都防不了 | 事故前：筆電也能推映像 |
| Build L1 | 產生 provenance，描述 artifact 如何被建置 | 錯誤與疏忽：可以查出用了哪個 commit、哪些依賴 | 第一步：CI 每次 build 輸出 provenance |
| Build L2 | 在託管的 build 平台上執行，由平台產生並簽章 provenance | 建置後的竄改；開發者自行偽造紀錄 | 第二步：只接受 CI 簽章的 provenance |
| Build L3 | Build 平台經過強化：不同次 build 互相隔離，簽章用的秘密不會暴露給使用者定義的 build 步驟 | Build 過程中被同一平台上的其他 build 或惡意 build script 影響、竊取簽章金鑰 | 目標：隔離的 ephemeral builder |

幾個重點值得注意。第一，等級描述的是 **build 平台與 provenance 的可信度**，不是「程式碼沒有漏洞」；SLSA L3 的 artifact 仍然可能包含有 bug 或有漏洞的依賴。第二，早期的 SLSA 草案（v0.1）曾有 L4，要求雙人 review 與 hermetic、reproducible build；v1.0 把範圍縮小到 build，原始碼管理等面向另外以獨立的 track 發展。第三，主流的託管 CI 平台與 SLSA 社群已提供產生 provenance 的工具，L1 到 L2 的門檻通常比想像中低。

### 在部署前驗證

產生 provenance 只是一半，另一半是**在部署前驗證它**。沒有人檢查的出生證明沒有價值。Harbor 的部署流程最後加上了一道 admission check（准入檢查），規則如下：

```text
允許部署 checkout@sha256:X，若且唯若：
  1. 存在一份 provenance，其 subject digest == X
  2. 簽章有效，且簽章者是 Harbor 的受信任 CI builder
  3. 來源 repository == payments/checkout，branch == main（或 release tag）
  4. 該 digest 已通過 CI 的必要檢查（測試、漏洞掃描）
否則：拒絕，並告知缺少哪一項
```

這條規則把本章所有東西串在一起：digest 確保部署的就是那份 bytes，provenance 確保那份 bytes 來自受信任的 builder 與正確的 source，簽章確保紀錄沒被改過，必要檢查確保測試是對同一份 bytes 做的。阿凱在筆電上 build 的映像，因為沒有受信任的 provenance，會被直接擋下；週三那種「同 tag 重建」的映像，即使 provenance 存在，部署設定引用的 digest 也會對不上。

```text
 commit 9f3c2ab
      │
      ▼
 ┌────────────┐   build once   ┌──────────────────────┐
 │ CI builder │ ─────────────▶ │ artifact sha256:X    │
 │ (受信任)    │ ─────────────▶ │ provenance（已簽章）  │
 └────────────┘                └──────────────────────┘
                                         │
              ┌──────────────────────────┼────────────────────────┐
              ▼                          ▼                        ▼
         staging（X）               canary（X）            production（X）
              ▲                          ▲                        ▲
              └────── 每次部署前：驗證簽章、builder、source、digest ───┘
```

圖的重點是同一個 X 一路往右走：只建一次，每個環境部署的都是同一個 digest，而每次部署前都重新驗證它的 provenance。若有人在中途換掉 bytes，digest 會變；若有人偽造紀錄，簽章會失敗。

## 27.11 動手寫：模擬 artifact-based build、快取與 provenance 驗證

第一段程式實作一個極簡的 artifact-based build system：每個 target 宣告 `srcs` 與 `deps`，系統依拓撲順序建置，以內容雜湊計算 action key，並用 action cache 與 CAS 快取結果。其中 `compile_pricing` 會偷讀一個沒有宣告的設定檔，用來重現「快取說謊」的情況。

```python
import hashlib
import json


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


class BuildSystem:
    """極簡的 artifact-based build：target 宣告輸入，系統負責排序、執行與快取。"""

    def __init__(self, files: dict[str, str], toolchain: str):
        self.files = files            # 模擬工作目錄：路徑 → 內容
        self.toolchain = toolchain    # toolchain 版本也是輸入
        self.targets = {}
        self.cas = {}                 # content-addressable storage：digest → 內容
        self.action_cache = {}        # action key → 輸出 digest

    def target(self, name, srcs=(), deps=(), cmd=None):
        self.targets[name] = {"srcs": sorted(srcs), "deps": list(deps), "cmd": cmd}

    def build(self, name, done=None):
        done = {} if done is None else done
        if name in done:
            return done[name]
        t = self.targets[name]
        dep_outs = [self.build(d, done) for d in t["deps"]]          # 先建依賴（拓撲順序）
        srcs = {p: digest(self.files[p].encode()) for p in t["srcs"]}
        key = digest(json.dumps({"cmd": t["cmd"].__name__, "srcs": srcs,
                                 "deps": dep_outs, "toolchain": self.toolchain},
                                sort_keys=True).encode())
        if key in self.action_cache:
            out = self.action_cache[key]
            print(f"  cache hit  {name:<13} key={key}")
        else:
            inputs = {p: self.files[p] for p in t["srcs"]}
            content = t["cmd"](inputs, [self.cas[d] for d in dep_outs], self.files)
            out = digest(content.encode())
            self.cas[out] = content
            self.action_cache[key] = out
            print(f"  execute    {name:<13} key={key} -> {out}")
        done[name] = out
        return out


def compile_pricing(inputs, deps, files):
    tax = json.loads(files["config/tax.json"])["rate"]   # 偷讀：沒有宣告成輸入！
    return f"pricing[{inputs['pricing.py'].strip()}; tax={tax}]"

def compile_checkout(inputs, deps, files):
    return f"checkout[{inputs['checkout.py'].strip()}] <- {deps[0]}"

def compile_search(inputs, deps, files):
    return f"search[{inputs['search.py'].strip()}]"

def package_image(inputs, deps, files):
    return " | ".join(deps)


files = {
    "pricing.py": "v1", "checkout.py": "v1", "search.py": "v1",
    "config/tax.json": '{"rate": 0.05}',
}
bs = BuildSystem(files, toolchain="python-3.12.4")
bs.target("//pricing", srcs=["pricing.py"], cmd=compile_pricing)
bs.target("//checkout", srcs=["checkout.py"], deps=["//pricing"], cmd=compile_checkout)
bs.target("//search", srcs=["search.py"], cmd=compile_search)
bs.target("//image", deps=["//checkout", "//search"], cmd=package_image)

print("1) 乾淨的第一次 build")
bs.build("//image")
print("2) 什麼都沒改，再 build 一次")
bs.build("//image")
print("3) 只改 search.py")
files["search.py"] = "v2"
bs.build("//image")
print("4) 稅率從 5% 改成 8%（但 tax.json 沒有被宣告）")
files["config/tax.json"] = '{"rate": 0.08}'
out = bs.build("//image")
print("   image 內容：", bs.cas[out])
print("5) 修正：把 tax.json 宣告為 //pricing 的輸入")
bs.target("//pricing", srcs=["pricing.py", "config/tax.json"], cmd=compile_pricing)
out = bs.build("//image")
print("   image 內容：", bs.cas[out])
```

執行結果：

```text
1) 乾淨的第一次 build
  execute    //pricing     key=de3746cf490f -> 1111a34c4436
  execute    //checkout    key=b154537c4a66 -> c93c2d50e162
  execute    //search      key=f361195361fd -> af5816dc4739
  execute    //image       key=fa149309a6cc -> 56e56d3321f8
2) 什麼都沒改，再 build 一次
  cache hit  //pricing     key=de3746cf490f
  cache hit  //checkout    key=b154537c4a66
  cache hit  //search      key=f361195361fd
  cache hit  //image       key=fa149309a6cc
3) 只改 search.py
  cache hit  //pricing     key=de3746cf490f
  cache hit  //checkout    key=b154537c4a66
  execute    //search      key=849c5eadcaab -> e5544cb93355
  execute    //image       key=2aaf81275889 -> fd016c79b627
4) 稅率從 5% 改成 8%（但 tax.json 沒有被宣告）
  cache hit  //pricing     key=de3746cf490f
  cache hit  //checkout    key=b154537c4a66
  cache hit  //search      key=849c5eadcaab
  cache hit  //image       key=2aaf81275889
   image 內容： checkout[v1] <- pricing[v1; tax=0.05] | search[v2]
5) 修正：把 tax.json 宣告為 //pricing 的輸入
  execute    //pricing     key=34c9e91de8d0 -> e184ee386145
  execute    //checkout    key=ccd19e851e28 -> ea7c3f0af827
  cache hit  //search      key=849c5eadcaab
  execute    //image       key=acd93217d792 -> a036b265b4ec
   image 內容： checkout[v1] <- pricing[v1; tax=0.08] | search[v2]
```

逐段解讀：

1. `build` 是遞迴的：先建完所有 `deps`，才計算自己的 action key。這就是拓撲排序，也是依賴圖決定順序的方式。真實系統會把沒有依賴關係的 target（這裡的 `//checkout` 分支與 `//search`）同時執行。
2. Action key 由指令名稱、每個 src 的內容 digest、依賴的輸出 digest 與 toolchain 版本組成。第 2 步什麼都沒改，四個 key 都相同，全部命中快取，一個 action 都沒執行。
3. 第 3 步只改了 `search.py`，只有 `//search` 與依賴它的 `//image` 重做；`//pricing` 與 `//checkout` 命中快取。這就是增量建置：工作量與「受影響的範圍」成正比，而不是與 repository 大小成正比。
4. 第 4 步是本章最重要的示範。`tax.json` 真的改了，但它不在任何 action key 裡，所以所有 key 不變、全部命中快取，產出的映像裡稅率還是 5%。沒有錯誤、沒有警告，pipeline 是綠的。這就是「快取說謊」：錯的不是快取，而是依賴宣告。
5. 宣告之後，`//pricing` 的 key 改變，連帶讓依賴它的 `//checkout` 與 `//image` 的 key 也改變（因為它們的 key 包含依賴的輸出 digest），而與稅率無關的 `//search` 繼續命中快取。

這段程式沒有 sandbox，所以 `compile_pricing` 能偷讀 `files`。在 Bazel 這類系統中，sandbox 只會放入宣告的檔案，第 4 步會直接以「找不到 config/tax.json」失敗，把錯誤從「靜默的錯誤結果」變成「明確的 build 失敗」。

第二段程式模擬兩件事：同一份原始碼在筆電與 CI 上打包，正規化前後 digest 是否相同；以及部署前如何驗證 provenance。

```python
import hashlib
import hmac
import io
import json
import tarfile

SOURCE = {
    "app/main.py": b"from app.pricing import total\n",
    "app/pricing.py": b"TAX = 0.05\n",
    "requirements.lock": b"flask==3.0.3 --hash=sha256:...\n",
}


def package(files, order, mtime, uid, normalize):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name in (sorted(files) if normalize else order):
            info = tarfile.TarInfo(name)
            info.size = len(files[name])
            info.mtime = 0 if normalize else mtime     # 時間戳記
            info.uid = info.gid = 0 if normalize else uid  # 建置者的使用者 ID
            tar.addfile(info, io.BytesIO(files[name]))
    return buf.getvalue()


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


laptop = dict(order=["requirements.lock", "app/pricing.py", "app/main.py"], mtime=1767225600, uid=501)
ci     = dict(order=["app/main.py", "app/pricing.py", "requirements.lock"], mtime=1767229200, uid=1001)

print("== Reproducibility ==")
for normalize in (False, True):
    a = sha(package(SOURCE, normalize=normalize, **laptop))
    b = sha(package(SOURCE, normalize=normalize, **ci))
    print(f"normalize={normalize!s:<5} laptop={a[7:19]} ci={b[7:19]} 相同={a == b}")

# ---- Provenance：誰、從哪個 source、怎麼 build 出這個 digest ----
BUILDER_KEY = b"held-only-by-the-ci-builder"     # 真實系統用非對稱簽章（如 Sigstore）
TRUSTED_BUILDERS = {"https://ci.harbor.example/builders/hosted-v2"}
EXPECTED_REPO = "git+https://git.harbor.example/payments/checkout"

artifact = package(SOURCE, normalize=True, **ci)


def make_provenance(art: bytes, commit: str) -> dict:
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "checkout", "digest": {"sha256": sha(art)[7:]}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://ci.harbor.example/oci-build/v1",
                "externalParameters": {"repository": EXPECTED_REPO, "ref": "refs/heads/main"},
                "resolvedDependencies": [{"uri": EXPECTED_REPO, "digest": {"gitCommit": commit}}],
            },
            "runDetails": {"builder": {"id": "https://ci.harbor.example/builders/hosted-v2"},
                           "metadata": {"invocationId": "build-18842"}},
        },
    }
    body = json.dumps(statement, sort_keys=True).encode()
    return {"statement": statement, "sig": hmac.new(BUILDER_KEY, body, "sha256").hexdigest()}


def verify(art: bytes, prov: dict | None) -> str:
    if prov is None:
        return "DENY：沒有 provenance"
    body = json.dumps(prov["statement"], sort_keys=True).encode()
    if not hmac.compare_digest(prov["sig"], hmac.new(BUILDER_KEY, body, "sha256").hexdigest()):
        return "DENY：簽章不符（provenance 被竄改）"
    st = prov["statement"]
    if st["predicate"]["runDetails"]["builder"]["id"] not in TRUSTED_BUILDERS:
        return "DENY：builder 不受信任"
    if st["predicate"]["buildDefinition"]["externalParameters"]["repository"] != EXPECTED_REPO:
        return "DENY：來源 repository 不符"
    if st["subject"][0]["digest"]["sha256"] != sha(art)[7:]:
        return "DENY：要部署的 bytes 與 provenance 描述的不同"
    return "ALLOW"


prov = make_provenance(artifact, commit="9f3c2ab")
rebuilt = package({**SOURCE, "requirements.lock": b"flask==3.1.0\n"}, normalize=True, **ci)
tampered = json.loads(json.dumps(prov))
tampered["statement"]["predicate"]["buildDefinition"]["externalParameters"]["repository"] = "git+https://evil.example/fork"

print("\n== Deploy-time verification ==")
print("CI 產出的 artifact       ->", verify(artifact, prov))
print("筆電 build、沒有來源紀錄 ->", verify(package(SOURCE, normalize=False, **laptop), None))
print("同 tag 重新 build 的映像 ->", verify(rebuilt, prov))
print("改過 repository 的紀錄   ->", verify(artifact, tampered))
```

執行結果：

```text
== Reproducibility ==
normalize=False laptop=4b884209fbe3 ci=7db20d58914d 相同=False
normalize=True  laptop=26caa7fe5d46 ci=26caa7fe5d46 相同=True

== Deploy-time verification ==
CI 產出的 artifact       -> ALLOW
筆電 build、沒有來源紀錄 -> DENY：沒有 provenance
同 tag 重新 build 的映像 -> DENY：要部署的 bytes 與 provenance 描述的不同
改過 repository 的紀錄   -> DENY：簽章不符（provenance 被竄改）
```

逐段解讀：

1. `package` 以 tar 格式打包同樣三個檔案。未正規化時，筆電與 CI 的檔案列舉順序、時間戳記與使用者 ID 都不同，得到兩個不同的 digest，即使檔案內容一模一樣。正規化（排序檔名、時間設為 0、擁有者設為 0）之後，兩邊得到相同的 digest。真實系統通常把時間設為 `SOURCE_DATE_EPOCH`，而不是 0。
2. `make_provenance` 產生的結構仿照 SLSA Provenance v1：`subject` 用 digest 指向 artifact，`buildDefinition` 記錄 repository、ref 與解析後的 commit，`runDetails` 記錄 builder ID 與這次執行的識別碼。
3. 簽章用 `hmac` 模擬，只是為了只用標準函式庫。真實系統一定使用非對稱簽章或 Sigstore 這類機制：builder 用私密的身分簽章，部署端只持有公開的驗證資訊，因此驗證者無法偽造紀錄。用 HMAC 時驗證者也持有同一把秘密，這在真實環境中是不可接受的。
4. `verify` 的檢查順序是先驗簽章、再驗內容：沒有 provenance、紀錄被改過、builder 不在信任清單、來源不符、digest 對不上，任何一項不通過就拒絕。四個測試案例分別對應本章故事中的情境：正常 CI 產出、筆電手動 build、同 tag 重建、以及被竄改的紀錄。

把這兩段程式放回真實世界：第一段對應 Bazel 等工具的 action cache、CAS 與 sandbox；第二段對應 CI 平台的 provenance 產生、Sigstore 簽章，以及部署端（例如 Kubernetes 的 admission policy）的驗證。原理相同：**用內容雜湊識別東西，用宣告取代猜測，用簽章取代信任**。

## 27.12 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 嚴格 hermetic，build 完全禁止網路 | 沒有提供替代的依賴來源，團隊開始繞過 | 禁網後套件抓不到，大家改回在筆電 build 再手動推映像，狀況比以前更糟 | 先建好內部 artifact mirror 與 toolchain 管理，再逐步收緊；提供清楚的錯誤訊息與文件 |
| 共用 remote cache 開放所有人寫入 | 一台被入侵或設定錯誤的機器污染快取 | 某工程師的本機 toolchain 版本不同，產出被寫進快取，CI 拿到後測試莫名失敗 | 只有受信任的 CI builder 可寫入；開發者唯讀；action key 包含 toolchain |
| 細粒度 target 與嚴格依賴 | BUILD 檔維護成本超過收益 | 小團隊的 50 個 target 由人工維護依賴，每次重構都要改十幾個 BUILD 檔 | 用工具自動產生依賴宣告；規模尚小時，粗一點的 target 也可接受 |
| 每個環境各自 build | Staging 的測試證據無法轉移到 production | Harbor 週三事故：同 commit 重建拿到不同依賴版本 | Build once, deploy many；部署引用 digest；registry 啟用不可覆寫的 tag |
| 追求逐位元可重現 | 成本高於價值 | 一個內部報表工具花兩週處理某個語言工具鏈的非確定輸出 | 先確保可追溯（provenance）與在同一 builder 內可重現；逐位元獨立重現留給高風險 artifact |
| 只產生 provenance、不驗證 | 紀錄存在但沒人看，攻擊者照樣能部署 | 部署系統接受任何 digest，provenance 存在 registry 裡卻從未被檢查 | 在部署准入處強制驗證，先用「只記錄不阻擋」模式觀察，再切到阻擋 |
| 為了快取命中率而少宣告輸入 | 快取命中率漂亮，結果卻是錯的 | 把 `config/` 整個排除在輸入外「因為它常改」，設定變更不再觸發重建 | 正確性優先於命中率；常改的設定應移到部署時注入，而不是排除在 build 輸入外 |

## 27.13 AI 時代：什麼變了？

AI coding agent 讓 build system 的重要性變得更高，原因有三個。

**第一，變更量增加，build 速度直接決定 agent 的迭代速度。** Agent 的工作方式是「修改 → build → 測試 → 讀錯誤 → 再修改」的迴圈，一個任務可能跑幾十次 build。如果每次 build 要 25 分鐘，agent 一小時只能試兩次；如果增量建置加上 remote cache 讓大部分 build 在一分鐘內完成，同樣的時間可以完成更多驗證。精確的依賴圖也讓 agent 知道「我改的這個檔案影響了哪些 target」，可以只跑相關的測試。反過來，不可靠的增量建置會讓 agent 陷入「清快取重來」的迴圈，或者更糟，被快取的舊結果誤導，以為自己的修改通過了。

**第二，agent 會修改 build 本身，而 build 是供應鏈中最有權限的位置之一。** Build 步驟可以執行任意程式、讀取環境中的憑證、從網路下載東西。Agent 在修一個 build 錯誤時，可能「順手」加一個依賴、改一個 Dockerfile 的 base image、在 build script 裡加一行下載指令，或把一個失敗的 sandbox 限制關掉。這些變更在 diff 裡看起來很小，風險卻很大。還要注意 **slopsquatting**（AI 建議了不存在的套件名稱，攻擊者搶先註冊同名惡意套件，第 20 章）：在 build 中自動安裝 agent 建議的新依賴，是讓這類攻擊成功的最短路徑。

**第三，provenance 需要涵蓋「誰做了這個變更」。** 當 commit 由 agent 產生時，provenance 鏈的上游多了一環：哪個 agent、在誰的授權下、依據哪個任務產生了這個變更。SLSA Build track 主要處理的是 build 平台的可信度，但組織同樣需要能從一個 production artifact 追溯到原始的變更請求與核准者。

具體的做法：

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 讀 build 錯誤與依賴圖，找出缺少或多餘的依賴宣告，並提出 BUILD 檔修改 | Agent 的 build 在 sandbox 中執行：網路只能連內部 mirror，沒有 production 憑證，有 CPU 與時間上限 |
| 比較兩次 build 的 artifact 與 manifest，解釋不可重現的來源（時間戳記、檔案順序、浮動版本） | 新增外部依賴、更換 base image、修改 toolchain 版本，一律需要人類 review，並由 CODEOWNERS 指定的 owner 核准 |
| 草擬 Dockerfile 最佳化（指令順序、multi-stage、`.dockerignore`），附上 build 時間與映像大小的前後對照 | Agent 不能關閉 sandbox、放寬 hermeticity 設定或修改快取寫入權限來「讓 build 通過」；這類修改視同安全變更 |
| 依 lock file 與漏洞資料草擬依賴升級 PR，說明影響範圍 | Agent 不持有簽章金鑰，也不能自行推送映像；artifact 只能由受信任的 CI builder 產生並簽章 |
| 分析 remote cache 命中率，指出哪些 target 因非確定輸出而一再重建 | Provenance 與部署准入規則由人類維護；規則變更需要安全與 platform 團隊共同核准 |

> [!ai] AI 提醒
> 當 agent 回報「build 失敗是因為 sandbox 限制太嚴，我已把這個 target 標記為不使用 sandbox」時，要把它當成一個紅旗，而不是一個修復。Sandbox 擋下的通常正是那條沒宣告的依賴邊；關掉它等於讓快取在未來某天給出錯誤結果。正確的回應是請 agent 找出被擋下的檔案或網路存取，並把它變成明確的宣告。

## 27.14 專家怎麼想

- **「這個 build 的輸入是什麼？說得出來嗎？」** 資深工程師看到 build 問題時，第一個問題不是工具，而是輸入。說不出完整輸入的 build，快取不可信、結果不可重現、事故時無法調查。這也是為什麼他們對「清快取就好了」特別警覺。
- **正確性先於速度，但速度是正確性的槓桿。** 一個錯的快快取比慢的 build 更危險，所以先確保輸入宣告完整；但 build 慢到讓人想繞過（在筆電 build、跳過 CI），正確性也會跟著崩壞。兩者要一起投資。
- **把 build 系統當成 production 系統。** CI builder、remote cache、artifact registry 是全公司每次變更都要經過的路徑，它們需要 owner、監控、容量規劃與存取控制。被入侵的 builder 比被入侵的單一服務影響更大。
- **部署設定裡看到 tag，就問 digest 在哪。** Tag 方便人看，digest 才是證據。專家會要求部署紀錄、事故報告與 rollback 指令都引用 digest，因為事故當下最需要的就是「確定」。
- **先做可追溯，再做可重現。** 對大多數團隊，最有價值的第一步是每個 artifact 都有簽章的 provenance 並在部署時驗證；逐位元可重現是很好的目標，但不該擋住第一步。
- **依賴圖是組織的地圖。** 一個被大量依賴的 target 是組織的單點風險；過多的循環或「大雜燴」target 通常反映了模糊的模組邊界。專家會定期看依賴圖的形狀，就像看系統架構圖一樣。

## 27.15 動手練習

1. 選一個你熟悉的專案，依 27.2 節的五類（source、dependencies、toolchain、configuration、environment）列出它的所有 build 輸入。標出哪些目前沒有被版本控制或固定下來。
2. 延伸 27.11 第一段程式：加入「sandbox 模式」，讓 `cmd` 只能拿到宣告的 `inputs`（不傳 `files`），確認第 4 步會直接拋出錯誤而不是靜默地回傳舊結果。再加入 early cutoff：讓 `compile_pricing` 忽略 `pricing.py` 中以 `#` 開頭的註解行，驗證只改註解時下游會命中快取。
3. 對同一個 commit，在乾淨環境中建兩次容器映像（相隔幾分鐘），比較 digest。如果不同，找出差異的來源，並嘗試用固定 base image digest、lock file 雜湊與 `SOURCE_DATE_EPOCH` 消除。
4. 檢查你的部署設定（Kubernetes manifest、Terraform、部署 script），找出所有以 tag 而非 digest 引用映像的地方，寫一份把它們改成 digest 的計畫，並說明 rollback 時如何找到前一個 digest。
5. 為 Harbor 畫一張從 commit 到 production 的 provenance 流程：哪個系統產生 provenance、簽章身分是什麼、在哪裡驗證、驗證失敗時誰收到通知。對照 SLSA Build L1–L3 的要求，指出 Harbor 目前在哪一級、下一級缺什麼。
6. 為 AI coding agent 設計一份 build sandbox 規格：檔案系統可讀寫範圍、網路允許清單、可用的憑證（應該幾乎沒有）、CPU 與時間上限，以及哪些檔案（Dockerfile、lock file、CI 設定）被修改時必須升級為人類 review。

## 本章重點整理

- Build 的輸入不只有原始碼，還包括依賴、toolchain、設定與環境；任何沒被固定的輸入都會讓同一份 source 產生不同的 artifact。
- Task-based build（Make、Maven、Gradle 等）以指令為中心，系統看不到 task 實際讀寫什麼，因此難以安全地平行化、增量建置與除錯。
- Artifact-based build（Bazel 等）讓工程師宣告「要什麼、由什麼構成」，把 build 當成純函數，換來可靠的平行化、增量建置、快取與遠端執行。
- 依賴圖是一張 DAG：拓撲排序決定順序，critical path 決定最快能多快，反向依賴決定改了什麼要重建與重測。
- 外部依賴要解析成精確版本並以雜湊驗證；版本範圍是給人看的意圖，雜湊才是 build 的輸入。
- Hermetic build 只使用宣告的輸入，toolchain 與網路都必須被管理；sandbox 讓偷讀變成明確的錯誤。
- Action key 由指令、輸入內容雜湊、依賴輸出與 toolchain 組成；快取的正確性完全取決於 action key 是否涵蓋所有影響輸出的因素。
- 「清快取就好了」代表依賴圖有一條沒宣告的邊；remote cache 只能由受信任的 builder 寫入，以防 cache poisoning。
- Reproducible build 指相同輸入能重建出逐位元相同的 artifact；時間戳記、檔案順序、使用者與路徑、浮動依賴是常見的破壞來源。
- 容器映像以 digest 識別內容、以 tag 方便閱讀；部署要引用 digest，base image 要以 digest 固定，Dockerfile 的指令順序決定快取效率。
- Build once, deploy many：同一個 digest 依序部署到各環境，環境差異在部署時以設定注入，測試證據才能轉移到 production。
- Provenance 記錄 artifact 由哪個 source、哪些依賴、哪個 builder 產生，並由 builder 簽章；沒有在部署前驗證的 provenance 沒有價值。
- SLSA v1.0 Build Levels 從 L1（有 provenance）、L2（託管平台簽章）到 L3（強化隔離的 build 平台），描述的是 build 的可信度，不是程式碼的品質。
- AI agent 讓 build 速度與正確性的重要性更高；agent 的 build 必須在 sandbox 中執行，修改依賴、base image、sandbox 設定與簽章流程的變更需要人類核准。

## 延伸問答

> [!question]- Q1. Hermetic、deterministic、reproducible 三個詞有什麼不同？舉一個「hermetic 但不 reproducible」的例子。
> Hermetic 描述的是過程：build 步驟只能看到宣告的輸入，看不到機器上其他狀態。Deterministic 描述的是單一步驟的性質：同樣的輸入每次執行都得到同樣的輸出。Reproducible 描述的是最終結果：任何人用相同的 source、環境與指令都能重建出逐位元相同的 artifact。
>
> 一個 hermetic 但不 reproducible 的例子：某個打包步驟在 sandbox 中執行，只讀宣告的檔案、不能上網，完全 hermetic；但它把「目前時間」寫進壓縮檔的每個檔案標頭，或在版本資訊中嵌入建置時間。每次執行輸出都不同，所以它不是 deterministic，整個 build 也就不 reproducible。修正方式是用 `SOURCE_DATE_EPOCH` 或固定值取代目前時間。這個例子說明 hermeticity 是可重現的必要條件，但不是充分條件。

> [!question]- Q2. 為什麼 artifact-based build 能安全地平行化，而 task-based build 很難？
> 平行化的前提是知道兩件工作彼此無關。在 task-based build 中，task 是任意指令，系統只知道你宣告的 task 依賴關係，看不到 task 實際讀寫了哪些檔案。如果兩個沒宣告依賴的 task 其實寫同一個暫存檔，或一個偷讀另一個的輸出，平行執行就會產生時好時壞的結果，而系統無法偵測。
>
> Artifact-based build 要求每個 target 宣告完整的輸入與輸出，並用 sandbox 強制執行：步驟只看得到宣告的檔案。因此依賴圖是可信的，圖上沒有路徑相連的兩個 action 就一定互不影響，可以放心同時執行，甚至送到不同的遠端機器上。換句話說，平行化的安全性來自「宣告被強制檢查」，而不是來自工程師的小心。

> [!question]- Q3. 你是 Harbor platform 團隊的成員。一位工程師說：「CI 上 checkout 測試失敗，但我清掉 remote cache 重跑就過了，應該是快取的問題，我們每週清一次快取吧。」你怎麼回應？
> 我會說「清快取讓這次通過」是一個症狀，不是原因，每週清快取只會讓問題更難被發現。快取的正確性取決於 action key 是否涵蓋所有影響輸出的東西；清快取後結果不同，代表有某個輸入（設定檔、環境變數、toolchain 版本、網路下載的內容）影響了輸出卻沒有進入 action key。
>
> 具體的調查步驟：先找出前後兩次 build 中相同 action key 但輸出不同的 action；比較兩次執行的環境與實際讀取的檔案（Bazel 這類工具可以輸出執行紀錄），找出沒宣告的輸入；確認是誰寫入了那筆錯誤的快取，如果是開發者機器寫入的，就要收緊寫入權限，只讓受信任的 CI builder 寫。最後把那個輸入加入宣告，或讓 sandbox 擋掉它，並在 postmortem 中記錄。定期清快取還有一個額外成本：每次清完 CI 都會變慢，大家會更想繞過 CI。

> [!question]- Q4. 容器映像的 tag 和 digest 有什麼差別？為什麼部署設定應該引用 digest？
> Tag 是一個名稱，指向 registry 中某一份 manifest，而且可以被重新指向另一份內容；`checkout:1.8.2` 今天和明天可能是不同的 bytes。Digest 是 manifest 內容的雜湊，內容改一個 byte，digest 就不同，因此它是不可變的身分。
>
> 部署設定引用 digest 有三個理由。第一，確定性：你部署的就是測試過的那份 bytes，Harbor 週三事故中「同 tag 重建」的情況不會影響已經記錄的 digest。第二，可驗證：provenance 與簽章都綁定在 digest 上，用 tag 部署就無法確定驗證的對象和實際執行的是同一份。第三，rollback 可靠：事故時回到「上一個 digest」是精確的操作，回到「上一個 tag」則要先確認那個 tag 沒被改過。Tag 仍然有用，它是給人閱讀和搜尋的別名，但不該是部署與證據的依據。

> [!question]- Q5. 計算題：Harbor 每天約 150 次 CI build。沒有 remote cache 時每次 build 平均 25 分鐘；導入 remote cache 後，平均 80% 的 action 命中快取，命中的部分幾乎不花時間。粗估每天省下多少 build 時間？為什麼實際效果可能比這個估計好或差？
> 粗估的算法是假設 build 時間大致和需要執行的 action 數成正比。80% 命中代表只需要執行 20% 的工作，每次 build 約 25 × 0.2 = 5 分鐘，每次省下 20 分鐘，每天 150 次就是 150 × 20 = 3,000 分鐘，也就是約 50 小時的機器時間，以及工程師等待時間的大幅縮短。
>
> 實際效果可能比估計好：命中的 action 往往包含最慢的依賴安裝與大型編譯，未命中的多是剛修改的小 target。也可能比估計差：build 時間受 critical path 限制，如果未命中的 action 剛好在關鍵路徑上（例如最後的映像打包與大型測試），總時間降得不多；下載快取結果本身也要花時間與網路頻寬；若有非確定輸出，下游命中率會遠低於 80%。所以導入後要實際量測每次 build 的時間分佈與 critical path，而不是只看命中率。

> [!question]- Q6. SLSA Build L3 的 artifact 就是安全的嗎？
> 不是。SLSA Build Levels 回答的是「這個 artifact 是否確實由宣稱的 source 與 build 流程產生、過程有沒有被竄改的可能」，而不是「這個 artifact 有沒有漏洞或惡意程式碼」。如果原始碼本身有 bug、某個依賴本身就是惡意套件，或開發者帳號被盜後提交了惡意程式碼，一個 L3 的 build 平台會忠實地把它建出來，並附上一份完全正確的 provenance。
>
> 所以 SLSA 是供應鏈安全的一部分，需要和其他控制搭配：原始碼端的 code review 與分支保護、依賴端的漏洞掃描與 SBOM、AI 建議套件的驗證（第 20 章），以及部署端的准入驗證。它的價值在於縮小攻擊面：攻擊者不能再在 build 過程中或建置後偷換 bytes，只能攻擊更上游、更容易被 review 發現的地方。

> [!question]- Q7. Harbor 想要 staging 與 production 用不同的資料庫位址與功能開關。有人提議「那就為每個環境各 build 一個映像，把設定建進去」。這有什麼問題？更好的做法是什麼？
> 問題在於每個環境的映像都是不同的 bytes。即使 commit 相同，只要多 build 一次，依賴解析、base image、時間戳記都可能不同，staging 上做過的測試、canary 觀察到的行為都不能證明 production 映像也一樣。這正是 Harbor 週三事故的根源。另外，把設定建進映像也代表改一個開關就要重新 build、重新走一次完整流程，而且秘密資訊（資料庫密碼）可能被寫進映像層。
>
> 更好的做法是 build once, deploy many：CI 只建一次，得到一個 digest，同一個 digest 依序部署到各環境；環境差異透過部署時注入的設定提供，例如環境變數、設定檔掛載、設定服務或功能開關系統，秘密資訊則由 secret manager 提供。這樣映像只包含「程式與依賴」，設定與程式分別版本化、分別 review，測試證據也能完整轉移。

> [!question]- Q8. AI 情境：Harbor 的 coding agent 在修一個 build 失敗時，提交了一個 PR：在 Dockerfile 中把 base image 從固定 digest 改成 `python:3.12`，並加了一行 `RUN pip install fastjson-utils`。PR 描述說「修正相依問題，build 已通過」。你是 reviewer，會怎麼處理？
> 我會拒絕直接合併，並把它當成兩個需要獨立判斷的供應鏈變更。第一，把 base image 從 digest 改回浮動 tag，等於放棄了可重現性與可追溯性：下一次 build 可能拿到不同的 base image，這正是本章事故的類型。如果真的需要更新 base image，應該改成新的固定 digest，並說明為什麼需要更新。第二，新增一個沒有固定版本、沒有雜湊、也沒有寫進 lock file 的套件，必須先驗證這個套件是否真實存在、是否是預期的那個專案、維護狀態與授權如何，因為 AI 建議的套件名稱可能是幻覺，甚至是被搶註的惡意套件（slopsquatting）。
>
> 接著要回到原因：build 為什麼失敗？請 agent 附上原始錯誤訊息與它的推理，通常真正的修法是補上缺少的依賴宣告或更新 lock file。流程上，這類修改 Dockerfile、lock file、base image 的 PR 應該由 CODEOWNERS 規則強制要求 owner review，agent 的 sandbox 也應該只能從內部 mirror 安裝已核准的套件。「build 已通過」只能證明它能編譯，不能證明它是安全或正確的。

## 延伸閱讀

- [Software Engineering at Google — Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)：原書第 18 章，從 shell script、task-based 到 artifact-based build 的演進，以及 Google 管理依賴與模組粒度的做法。
- [Software Engineering at Google — Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html)：外部依賴、版本與 One Version Rule，搭配第 20 章閱讀。
- [SLSA](https://slsa.dev/)：SLSA 規格本身，包括 Build Levels 的要求與 provenance 格式。
- [Site Reliability Engineering — Release Engineering](https://sre.google/sre-book/release-engineering/)：從 SRE 角度看 hermetic build、可重現性與發布流程，也是第 29 章的背景。
