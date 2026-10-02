---
chapter: 17
title: Code Execution 與 Sandbox
part: 3
---

# 第 17 章　Code Execution 與 Sandbox

> [!abstract] 本章地圖
> **核心問題**：agent 寫出來的程式要在哪裡跑、被關在多牢的籠子裡，才能既算得出報表，又不會拖垮服務、外洩資料或拿到不該拿的憑證？
>
> **你會學到**：
> - 說清楚 agent 為什麼需要執行環境，以及為什麼模型產生的程式必須一律當成不可信的程式
> - 比較 process、container、gVisor、microVM 四種隔離層級的邊界、成本與相容性，依情境選出合適的一層
> - 設計資源限制（CPU 時間、wall clock、記憶體、檔案大小、輸出長度）與檔案系統邊界，知道 rlimit 與 cgroup 的差別
> - 設計預設拒絕的網路 egress，並用 credential proxy 讓 secret 從頭到尾不進 sandbox
> - 規劃 sandbox 的生命週期與 warm pool，在冷啟動延遲與閒置成本之間取捨
> - 用 subprocess 加 `resource` 寫出可在 macOS 與 Linux 執行的概念版執行器，並清楚知道它不是安全邊界
>
> **前置知識**：第 4 章（agent loop、tool 結果回填與截斷）、第 5 章（tool 的副作用分級）、第 13 章（code-as-action：用程式取代多次 tool call）、第 14 章（MCP 的授權與禁止 token passthrough）

## 17.1 故事：報表助理把客服 API 拖垮的那個下午

青鳥科技的客服 agent 穩定上線之後，阿哲帶來下一個需求：店家常問「上個月各品類的退貨率是多少」「哪幾個商品的退貨原因最常是尺寸不合」，客服只能手動匯出 CSV 再用試算表算。第 13 章講過，這種「把幾萬列資料算成幾個數字」的工作，與其把資料塞進 context 讓模型硬算，不如讓 agent 寫一段 Python，在程式裡算完，只把結果帶回來。Iris 很快做出「營運報表助理」：模型拿到店家的訂單匯出檔，寫一段分析程式，harness 執行它，再把輸出交回模型寫成報告。

為了趕內部試用，Iris 的第一版用了最省事的寫法：在 agent 的 API 服務裡直接 `exec()` 模型產生的程式。第一週就出了三件事。第一件，模型對兩百萬列訂單寫了一個雙層迴圈，那個 worker 的 CPU 衝到滿載整整四分鐘，同一個 worker 上的客服對話全部逾時。第二件，另一段程式把一個 3 GB 的匯出檔整個讀進記憶體，撞上 container 的記憶體上限，整個 pod 被 OOM 終止，連帶中斷了二十幾個進行中的客服 session。第三件最嚴重，卻沒有造成任何事故：Maya 在資安審查時只問了一句「這段程式能不能 `import os` 讀環境變數？」答案是能，而 agent 服務的環境變數裡有 ERP 的 API token 和資料庫密碼。

「模型寫的程式，要當成陌生人寫的程式。」Maya 在審查會上這樣說。重點不在模型是不是有惡意，而在它的輸出會被 context 裡的任何東西影響：店家匯出的 CSV 裡有顧客留言，留言裡可以寫任何字；第 31 章會談到，當一個系統同時能讀私有資料、會讀到不可信內容、又能對外通訊，資料外洩只差一個被誘導的步驟。老陳接著把問題拆成五個：程式跑在哪一層隔離裡？能用多少 CPU、記憶體、磁碟與時間？能連到哪裡？手上有哪些憑證？用完之後環境怎麼處理？

這一章就是回答這五個問題。我們先說明為什麼 agent 需要執行環境、為什麼它不可信，再依序談隔離層級、資源與檔案系統、網路 egress、credential proxy、sandbox 的生命週期與 pool，最後在「動手做」寫一個概念版執行器，重現並擋下 Iris 遇到的資源事故，同時誠實地印出它擋不住什麼。

## 17.2 為什麼 agent 需要執行環境，又為什麼不能信任它

**code execution**（程式執行）指的是 agent 產生一段程式，由 harness 在某個環境裡實際執行，再把結果回填給模型。例如報表助理寫出「讀 orders.csv、依品類分組、算退貨率」的 Python，執行後只回傳 `{'服飾': 0.67, '家電': 0.5}` 這一行。它解決三類問題：模型不擅長的精確計算（數萬列加總、日期運算、統計檢定）；需要真實回饋的任務（coding agent 跑測試、編譯、看錯誤訊息）；以及第 13 章談的 code-as-action，用一段程式串起多次 tool 呼叫，中間結果留在程式裡，不必每一步都經過 context。

執行環境的另一個名字是 **sandbox**（沙箱）：一個把程式關在裡面、限制它能碰到哪些資源的執行環境。白話地說，sandbox 是一份「這段程式能做什麼」的保證書，例如「最多用 1 顆 CPU 跑 60 秒、只能讀寫 /workspace、只能連到公司的套件鏡像站、看不到任何憑證」。保證書的可信度，取決於負責執行限制的那一層有多可靠，這就是下一節隔離層級的主題。

為什麼不能信任模型產生的程式？有兩類完全不同的原因。第一類是**意外**：模型寫出無窮迴圈、把整個檔案讀進記憶體、遞迴刪除了錯的目錄，這些都不需要任何人有惡意，只是程式有 bug。第二類是**被誘導**：模型讀到的資料裡藏著指令（prompt injection，第 31 章），讓它寫出把資料送到外部、讀取憑證或探索內網的程式。第一類主要靠資源限制與用完即丟的環境；第二類主要靠網路 egress 控制與「secret 根本不在裡面」。兩類都要防，而且都不能靠模型自律，因為模型正是被影響的那一方。

```text
 ┌──────────── 信任區（青鳥的服務） ─────────────┐
 │                                               │
 │  Agent Runner ──► Model                       │
 │    │  持有：ERP token、DB 密碼、使用者身分    │
 │    │                                          │
 │    │ (1) run_code(code, inputs)               │
 │    ▼                                          │
 │  Sandbox Manager ── 選 pool、設限制、收產物   │
 └────┼──────────────────────────────────────────┘
      │ (2) 只傳入：程式、輸入檔、短效 session token
 ═════╪═══════════════ 隔離邊界 ═══════════════════════
      ▼
 ┌──────────── 不可信區（sandbox） ──────────────┐
 │  /workspace（可寫）  /data（唯讀輸入）        │
 │  CPU、記憶體、磁碟、pids、時間都有上限        │
 │  沒有憑證、沒有直接對外路由                   │
 └────┼──────────────────────────────────────────┘
      │ (3) 所有對外連線只能走這裡
      ▼
 Egress／Credential Proxy ── allowlist 比對、注入真憑證、稽核
      │
      ├──► erp.internal（允許的唯讀 API）
      └──✕ 其他網域（拒絕並記錄）
```

這張圖是全章的地圖。上方的信任區是 agent 服務本身，它持有所有憑證與使用者身分；模型決定要執行一段程式時，Runner 透過第 (1) 步呼叫 Sandbox Manager。第 (2) 步跨過隔離邊界時，只傳入三樣東西：程式、這次任務需要的輸入檔，以及一個只在這次 session 有效的 token。sandbox 裡的程式能用的資源全部有上限，而且沒有任何能直接連到外部的路由。第 (3) 步，任何對外連線都必須經過 egress proxy，由它比對 allowlist、在邊界外注入真正的憑證並留下稽核紀錄。注意 agent loop 本身在 sandbox 外面：模型的決策、對話歷史與憑證都留在信任區，進入 sandbox 的只有「要執行的程式」。

先看 Iris 的 v0 錯在哪裡。下面這段程式模擬「在 agent process 裡直接 exec」：

```python
from __future__ import annotations

import os

# agent 服務本身的狀態：為了呼叫 ERP，它持有 token；為了服務多個店家，它記著所有進行中的 session
os.environ["BLUEBIRD_ERP_TOKEN"] = "erp-live-THIS-SHOULD-NEVER-LEAK"
SESSIONS = {"shop42": {"orders": 1284}, "shop17": {"orders": 311}}

# 模型為 shop42 產生的「報表程式」。它沒有惡意，只是多看了一眼環境
generated = """
import os, sys
secret_names = sorted(k for k in os.environ if k.startswith('BLUEBIRD_'))
other_tenants = sorted(sys.modules['__main__'].SESSIONS)
pid = os.getpid()
"""

ns: dict = {}
exec(generated, ns)                                   # Iris v0 的做法：直接在 agent process 裡執行
print("看得到的 secret：", ns["secret_names"])
print("看得到的店家：  ", ns["other_tenants"])
print("和 agent 是同一個 process：", ns["pid"] == os.getpid())

assert ns["secret_names"] == ["BLUEBIRD_ERP_TOKEN"] and "shop17" in ns["other_tenants"]
```

```text
看得到的 secret： ['BLUEBIRD_ERP_TOKEN']
看得到的店家：   ['shop17', 'shop42']
和 agent 是同一個 process： True
```

第一行說明 secret 在同一個 process 的環境變數裡，被執行的程式一行就能讀到。第二行更糟：程式只是為 shop42 產生的，卻能透過 `sys.modules` 看到 agent 記憶體裡其他店家的 session，這是多租戶系統最不能發生的事。第三行解釋了 Iris 前兩個事故：既然是同一個 process，程式吃滿 CPU 就是 agent 吃滿 CPU，程式被 OOM 收掉就是 agent 被收掉。給 `exec` 一個乾淨的 namespace、拿掉 `__builtins__` 都不能改變這個事實，Python 本身也沒有提供在同一個直譯器裡安全執行不可信程式的機制（早年的 `rexec` 模組就因為無法保證安全而被移除）；部分 agent framework 提供以 AST 檢查為基礎的「本地執行器」，它們的文件同樣強調那不是 sandbox，正式環境要接遠端隔離環境。

| 要保護的東西 | 意外造成的威脅 | 被誘導造成的威脅 | 主要控制 | 本章小節 |
|---|---|---|---|---|
| agent 服務與其他 session | CPU 滿載、OOM、磁碟寫滿 | 刻意耗盡資源 | 獨立 process 以上的隔離、資源上限 | 17.3、17.4 |
| host 與其他租戶 | 誤刪、寫錯路徑 | 嘗試突破隔離層 | container 以上的隔離、唯讀根目錄、kernel 攻擊面最小化 | 17.3、17.4 |
| 憑證與身分 | 程式把環境變數印進 log | 讀取並外傳憑證 | secret 不進 sandbox、credential proxy | 17.6 |
| 資料 | 結果檔帶出過多資料 | 透過網路外洩 | egress 預設拒絕、產物大小與格式檢查 | 17.4、17.5 |
| 外部世界與公司信譽 | 迴圈中狂打外部 API | 以你的 IP 濫用他人服務 | egress allowlist、速率限制、稽核 | 17.5 |
| 下一個任務 | 殘留檔案影響下次結果 | 植入檔案等待下一個使用者 | 用完即丟、不跨任務重用 | 17.7 |

這張表把「sandbox」拆成六個獨立的保證。常見的誤解是把 sandbox 當成單一開關，裝了 Docker 就算完成；實際上每一列都需要各自的機制，而且彼此不能替代。例如 microVM 能把程式和 host 隔得很開，但如果 VM 裡有網路又有憑證，第三、四列仍然完全沒防。設計審查時，最有效的做法是逐列問「這一列靠什麼保證、誰負責、怎麼測」。

## 17.3 隔離層級：process、container、gVisor、microVM

隔離層級要回答的問題是：**sandbox 裡的程式和外面的世界，共用了哪些東西？** 共用得越多，隔離越弱、成本越低。所有程式最終都要透過 **system call**（系統呼叫，程式請 kernel 幫忙開檔案、配置記憶體、建立連線的介面）和 kernel 打交道，所以「程式能直接碰到哪一個 kernel」是區分隔離層級最關鍵的一條線。我們用 **attack surface**（攻擊面，不可信程式能直接互動的介面總和）來描述它：攻擊面越小，隔離層本身出現漏洞時的影響就越小。

```text
 (a) process            (b) container           (c) gVisor               (d) microVM
 ┌──────────────┐       ┌──────────────┐        ┌──────────────┐         ┌──────────────┐
 │ 不可信程式   │       │ 不可信程式   │        │ 不可信程式   │         │ 不可信程式   │
 ├──────────────┤       ├──────────────┤        ├──────────────┤         ├──────────────┤
 │              │       │ namespace    │        │ Sentry：     │         │ guest kernel │
 │              │       │ cgroup       │        │ user-space   │         │ （VM 自己的）│
 │              │       │ seccomp      │        │ kernel       │         ├──────────────┤
 │              │       │              │        ├──────────────┤         │ VMM（精簡的  │
 │              │       │              │        │ 少量 syscall │         │ 虛擬硬體）   │
 ├──────────────┤       ├──────────────┤        ├──────────────┤         ├──────────────┤
 │ host kernel  │       │ host kernel  │        │ host kernel  │         │ KVM／host    │
 │ （完整介面） │       │ （完整介面） │        │ （大幅縮小） │         │ kernel       │
 └──────────────┘       └──────────────┘        └──────────────┘         └──────────────┘
 邊界：使用者權限       邊界：kernel 的         邊界：Sentry 加上        邊界：hypervisor
                        namespace 實作          縮小的 syscall 集合      與虛擬硬體介面
```

由左到右逐一看。(a) 普通的 **process**：不可信程式和 agent 服務跑在同一個 OS 使用者底下，共用檔案系統、網路與 kernel，唯一的邊界是 Unix 使用者權限；本章動手做的概念版就在這一層，只多加了資源上限。(b) **container**：用 Linux 的 **namespace**（讓 process 看到自己獨立的檔案系統、process 清單、網路介面）與 **cgroup**（限制一組 process 能用的 CPU、記憶體、pids）把程式圍起來，再用 **seccomp**（過濾程式能呼叫哪些 system call）縮小介面；但它仍然直接使用 host kernel，kernel 的漏洞就是隔離的漏洞。(c) **gVisor**：在 container 與 host kernel 之間插入一個用 Go 寫成的 user-space kernel（稱為 Sentry），程式的 system call 先由 Sentry 處理，Sentry 自己只用少量 system call 和 host 互動，大幅縮小 host kernel 的攻擊面。(d) **microVM**：每個 sandbox 是一台精簡的虛擬機，有自己的 guest kernel；邊界變成 hypervisor 與一組極少的虛擬裝置，Firecracker 是這類 VMM（virtual machine monitor，虛擬機監控程式）最知名的例子。

| 層級 | 共用什麼 | 啟動速度（量級） | 執行期額外負擔 | 相容性 | 典型用途 |
|---|---|---|---|---|---|
| process ＋ rlimit | kernel、檔案系統、網路、使用者 | 最快 | 幾乎沒有 | 完全相容 | 開發機上的概念驗證、可信程式的資源保護 |
| OS 原生 sandbox（Seatbelt、bubblewrap、Landlock） | kernel；檔案與網路受政策限制 | 很快 | 很低 | 高，政策寫得太緊會壞 | 本機 coding agent CLI |
| container（強化設定） | host kernel | 快 | 低 | 高 | 可信團隊的 CI、內部工具 |
| gVisor | host kernel 的一小部分 | 快，略慢於 container | syscall 密集或 I/O 密集時明顯 | 中高，少數 syscall 與檔案系統行為不同 | 多租戶執行不可信程式 |
| microVM（Firecracker、Cloud Hypervisor、Kata） | hypervisor 與虛擬硬體 | 較慢，可用 snapshot 加速 | 中，記憶體需預先切分 | 最高，可跑完整 OS 與 Docker | 多租戶、需要完整 Linux 環境、長時間 session |

這張表最重要的一欄是「共用什麼」，其他欄都是它的結果。共用越少，隔離越強，但啟動與資源成本越高，相容性問題也從「kernel 行為不同」變成「要管理一整台 VM」。啟動速度只寫量級，因為實際數字取決於映像大小、是否用 snapshot 還原、是否預先暖機，下一節的 pool 會再談。另外兩種常見選項也值得知道：**WebAssembly** 執行環境預設沒有任何 I/O，所有能力都要明確授予，很適合純運算的小工具，但不適合需要完整 Python 生態系的資料分析；**OS 原生 sandbox** 則是 macOS 的 Seatbelt、Linux 的 bubblewrap 與 Landlock，它們不建立新的作業系統環境，而是限制「這個 process 能讀寫哪些路徑、能不能連網」，主流 coding agent 的本機 CLI 大多用它。

怎麼選？原則是**隔離強度要配合「誰寫的程式」與「誰會受害」**：

| 情境 | 誰寫的程式 | 主要風險 | 建議層級 |
|---|---|---|---|
| 開發者在自己筆電上用 coding agent | 模型，開發者在旁監看 | 誤刪檔案、讀到 home 目錄的憑證 | OS 原生 sandbox：寫入限 workspace、網路預設拒絕 |
| 公司內部 CI 跑 agent 修測試 | 模型，輸入是自家 repo | 外洩原始碼、拖垮 CI 機器 | 強化設定的 container 起跳；碰到不可信 PR 就升級 |
| 青鳥報表助理（店家資料、多租戶） | 模型，輸入含顧客留言 | 跨租戶、外洩、資源耗盡 | gVisor 或 microVM，每任務一個 |
| 對外開放的 code interpreter 產品 | 任何網路使用者 | 刻意攻擊隔離層 | microVM 或 gVisor，加上 egress 與濫用偵測 |
| 需要在 sandbox 裡跑 Docker 或瀏覽器 | 模型 | 同上，且需要完整 OS | microVM |

這張決策表的邏輯是：只要「寫程式的一方」和「受害的一方」不是同一個人，而且受害者不只一個（多租戶），就不能停在共用 host kernel 的那幾層。青鳥的報表助理同時符合三個條件：程式由模型寫、模型會讀到顧客寫的文字、受害者是數千家店家，所以老陳的結論是 gVisor 或 microVM，不考慮單純的 container。

如果你必須用 container，至少要把預設值收緊。下面是 Docker 常見的強化參數，用意是讓 container 從「方便開發的環境」變成「最小權限的執行環境」：

```bash
docker run --rm \
  --network=none \
  --read-only --tmpfs /tmp:rw,size=64m \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=128 --memory=512m --cpus=1 \
  --user 65534:65534 \
  --runtime=runsc \
  -v "$PWD/job:/workspace:rw" sandbox-python:3.12 python /workspace/main.py
```

每一行對應前一節表格的一列：`--network=none` 管網路（需要對外時改接只能到達 egress proxy 的內部網路），`--read-only` 與 tmpfs 管檔案系統，`--cap-drop` 與 `no-new-privileges` 縮小權限，`--pids-limit`、`--memory`、`--cpus` 是 cgroup 資源上限，`--user` 讓程式不以 root 執行，`--runtime=runsc` 則是在已安裝 gVisor 的機器上把隔離從 (b) 換成 (c)。注意 Docker daemon 的 socket 絕對不能掛進 sandbox，拿到它等於拿到 host 的控制權。

> [!warning] 常見誤解
> 「container 就是 sandbox。」container 最初是為了打包與部署而設計的，它的隔離來自 kernel 的 namespace 與 cgroup，邊界的強度等於 host kernel 的實作品質加上你的設定。預設設定的 container（root 使用者、完整 capabilities、有網路）對不可信程式幾乎沒有防護力。另一個相反的誤解是「用了 microVM 就安全了」：VM 只處理隔離層級這一列，網路、憑證與資源上限仍然要各自設計。

## 17.4 資源限制與檔案系統

隔離層決定「程式碰得到什麼」，資源限制決定「它能用多少」。Iris 的前兩個事故都是資源事故，而且都不需要惡意。每一種資源都要有上限，因為任何一種被耗盡，影響的都不只這段程式。下表列出要限制的資源、不限制的後果，以及概念版與 production 分別用什麼機制。

| 資源 | 不限制的後果 | 概念版（rlimit） | production（Linux） | macOS 上的概念版 |
|---|---|---|---|---|
| CPU 時間 | 無窮迴圈吃滿核心 | `RLIMIT_CPU`，超過送 SIGXCPU | cgroup `cpu.max`（限速）＋ CPU 時間上限 | 有效 |
| wall clock（實際經過時間） | 卡在 sleep 或等待 I/O，永遠不結束 | 父行程計時後整組砍掉 | 同左，由 sandbox manager 執行 | 有效 |
| 記憶體 | OOM 波及同機其他服務 | `RLIMIT_AS`／`RLIMIT_DATA` | cgroup `memory.max`，或 VM 的記憶體大小 | 通常無法設定，需降級回報 |
| 單一檔案大小 | 寫出巨大檔案塞滿磁碟 | `RLIMIT_FSIZE` | 加上磁碟配額或固定大小的 tmpfs | 有效 |
| process 數量 | 不斷建立子行程拖垮機器 | `RLIMIT_NPROC` 是以使用者為單位，不適合 | cgroup `pids.max` | 不建議用 rlimit |
| 輸出長度 | 洗版的 stdout 撐爆 context 與帳單 | 父行程只讀前 N 個字元 | 同左，另存完整輸出供下載 | 有效 |

這張表有兩個容易忽略的地方。第一，**CPU 時間和 wall clock 是兩件事**：一段 `sleep(3600)` 幾乎不用 CPU，`RLIMIT_CPU` 永遠不會觸發，所以 wall clock 上限必須由外面的父行程執行。第二，**rlimit 是以單一 process 為單位**，子行程會繼承同樣的上限，但不會合併計算；程式開十個子行程，每個都能用滿各自的額度。cgroup 則是以一組 process 為單位計算總量，這是 production 必須用 cgroup 或 VM 的主要原因。macOS 那一欄說明了概念版為什麼要「優雅降級」：同一段程式在 macOS 上設定記憶體 rlimit 會被拒絕，執行器不能假裝它生效了。

檔案系統的設計原則是：**sandbox 只看得到這次任務需要的東西，而且寫入只能落在可以整個丟掉的地方**。實務上分成四塊：唯讀的基礎映像（Python 與常用套件）、唯讀掛載的輸入（店家這次的匯出檔）、可寫但有容量上限的 workspace、以及約定好的輸出目錄。任務結束時，harness 只從輸出目錄收集「宣告過的產物」，檢查大小與格式之後才帶出邊界，其餘全部隨 sandbox 銷毀。產物本身也是不可信資料：一份 HTML 報表可能內嵌 script，一份 CSV 的儲存格可能被試算表當成公式，交給使用者之前要依格式做轉義或轉成安全的呈現方式。

在 container 或 VM 裡，路徑邊界由 mount namespace 保證，程式根本看不到沒掛進去的路徑。但 harness 端常常也有「檔案 tool」在 sandbox 外面替模型讀寫檔案，例如把產物複製出來、讓模型讀取 workspace 裡的某個檔案。這些 tool 必須自己做路徑檢查，而且要先展開 `..` 與 symlink 再比對，否則一個指向外部的 symlink 就能讓「workspace 裡的檔案」變成服務設定檔。

```python
from __future__ import annotations

import os
import tempfile
from pathlib import Path


class PathPolicy:
    """檔案 tool 的路徑檢查：先 resolve（展開 .. 與 symlink），再確認落在允許的根目錄內。"""

    def __init__(self, workspace: Path, read_only: list[Path]):
        self.workspace = workspace.resolve()
        self.read_only = [p.resolve() for p in read_only]

    def check(self, user_path: str, write: bool) -> str:
        target = (self.workspace / user_path).resolve()      # 相對路徑一律以 workspace 為基準
        if target.is_relative_to(self.workspace):
            return f"允許{'寫入' if write else '讀取'}"
        if not write and any(target.is_relative_to(r) for r in self.read_only):
            return "允許讀取（唯讀掛載）"
        return f"拒絕：解析後是 {target.name}，在允許的根目錄之外"


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    ws, data, secret_dir = root / "workspace", root / "datasets", root / "agent-service"
    for d in (ws, data, secret_dir):
        d.mkdir()
    (data / "orders.csv").write_text("id,amount\n", encoding="utf-8")
    (secret_dir / ".env").write_text("ERP_TOKEN=...\n", encoding="utf-8")
    os.symlink(secret_dir / ".env", ws / "notes.txt")          # 看起來在 workspace 內，其實指向外面
    policy = PathPolicy(ws, read_only=[data])

    cases = [("report.md", True), ("out/charts/a.png", True), ("../datasets/orders.csv", False),
             ("../datasets/orders.csv", True), ("../agent-service/.env", False), ("notes.txt", False)]
    results = []
    for p, write in cases:
        verdict = policy.check(p, write)
        results.append(verdict)
        print(f"{'寫' if write else '讀'} {p:<26} → {verdict}")

assert results[0].startswith("允許") and results[2] == "允許讀取（唯讀掛載）"
assert results[3].startswith("拒絕") and results[4].startswith("拒絕") and results[5].startswith("拒絕")
```

```text
寫 report.md                  → 允許寫入
寫 out/charts/a.png           → 允許寫入
讀 ../datasets/orders.csv     → 允許讀取（唯讀掛載）
寫 ../datasets/orders.csv     → 拒絕：解析後是 orders.csv，在允許的根目錄之外
讀 ../agent-service/.env      → 拒絕：解析後是 .env，在允許的根目錄之外
讀 notes.txt                  → 拒絕：解析後是 .env，在允許的根目錄之外
```

前兩行是 workspace 內的正常寫入。第三、四行是同一個輸入檔：讀取被允許，因為它在唯讀掛載清單裡；寫入被拒絕，因為輸入資料不該被這次任務修改。第五行是直接用 `..` 走出 workspace，被 resolve 後的比對擋下。最後一行最關鍵：`notes.txt` 的名字看起來無害、位置也在 workspace 內，但它是指向服務設定檔的 symlink，resolve 之後真正的目標是 `.env`，所以被拒絕。如果只用字串比對「路徑是否以 workspace 開頭」，這一行就會放行。這個檢查仍有限制：檢查與實際開檔之間若有其他程式改動檔案，就會出現檢查時與使用時不一致的競態問題，所以它是檔案 tool 的防線之一，不能取代 mount namespace 這種由 kernel 保證的邊界。

## 17.5 網路 egress 控制

**egress**（出站流量）指的是從 sandbox 往外發出的網路連線。為什麼 egress 是整個 sandbox 設計裡最關鍵的一環？因為第 31 章談的資料外洩，最後一步幾乎都是「把資料送出去」。只要程式讀得到資料、又能任意連網，任何一次被誘導的程式產生，就足以把資料送到外部；反過來說，只要 egress 被確定性地鎖住，即使模型被誘導，資料也出不了門。Anthropic 在 2026 年公開的 containment 經驗中也提到，紅隊演練裡能可靠擋住憑證外洩的，是 egress 與檔案邊界，而不是模型自己的判斷。

| 模式 | 做法 | 適用 | 風險與代價 |
|---|---|---|---|
| 完全無網路 | sandbox 沒有網路介面，只能讀寫檔案 | 純計算的報表、轉檔 | 不能裝套件、不能呼叫內部 API，需事先準備好映像 |
| allowlist proxy | 唯一出口是 proxy，比對網域、方法、路徑後才轉送 | 需要套件鏡像站或少數內部 API | allowlist 本身就是權限，要像審 IAM 一樣審 |
| 開放但監控 | 可連外，記錄並偵測異常流量 | 研究型任務、需要瀏覽網頁 | 偵測是事後的，資料可能已經出去 |
| 完全開放 | 不做限制 | 不建議用於任何會接觸私有資料的 sandbox | 外洩、濫用你的 IP 攻擊他人 |

這張表由上到下，能力越多、風險越高。預設應該是第一列，只有任務真的需要時才往下移，而且每往下一列都要寫明理由。最常見的錯誤是為了「方便裝套件」直接開到第四列；更好的做法是把常用套件預先裝進映像，少數需要動態安裝的情況，只允許連到公司自己的套件鏡像站。

```text
 sandbox（沒有預設路由、沒有對外 DNS）
   │  程式送出 GET https://erp.internal/v1/orders?week=39
   │  只帶 session token：sess-7f3a
   ▼
 Egress Proxy（sandbox 唯一能連到的位址）
   │ (1) 驗證 session token：存在？過期？屬於哪個租戶？
   │ (2) 正規化：去掉 query、展開 ..、統一大小寫與編碼
   │ (3) 比對 allowlist：(host, method, path 前綴) 是否明確允許
   │ (4) 檢查流量：請求大小、頻率、回應大小
   │ (5) 寫稽核紀錄：誰、何時、連到哪裡、結果
   ├── 通過 ──► 由 proxy 自己解析 DNS 並轉送 ──► erp.internal
   └── 拒絕 ──► 回 403 給 sandbox，計數並告警
```

這張資料流圖說明 egress 控制要在**網路層**做，而不是在程式裡做。sandbox 沒有預設路由，也不能直接查詢外部 DNS，所以就算程式忽略 `HTTP_PROXY` 環境變數、自己開 socket，也連不到任何地方；proxy 是它唯一能到達的位址。第 (1) 步把連線歸屬到某個 session 與租戶；第 (2) 步先正規化再比對，避免用 `..` 或編碼差異繞過路徑前綴；第 (3) 步是預設拒絕的 allowlist；第 (4) 步限制資料量與頻率，即使連到允許的服務，也不能一次搬走整個資料庫；第 (5) 步留下稽核紀錄。DNS 由 proxy 解析，是因為 DNS 查詢本身也是一條可以夾帶資料的對外通道。雲端環境裡還有一個必擋的目標：VM 的 instance metadata 端點，它可能發出該機器的雲端憑證，sandbox 不該有任何路徑連到它。

設計 allowlist 時最容易被忽略的一句話是：**allowlist 等同授權**。允許連到某個網域，就是授予「把資料送到那個網域上任何人控制的地方」的能力。允許一個可以讓任何人上傳內容的公開網域（程式碼託管、檔案分享、貼文服務），等於允許把資料上傳到攻擊者在那裡開的帳號；即使是允許你自己的模型供應商 API，也要確認 sandbox 只能用你的帳號、不能用別人的 key。所以 allowlist 要細到路徑與方法，並且盡量只放「只能讀、不能寫」的端點。

## 17.6 Secrets 不進 sandbox：credential proxy

報表助理有時確實需要呼叫內部 API，例如程式要分頁抓取這週的訂單。最直覺的做法是把 ERP token 放進 sandbox 的環境變數，這正是 Maya 擋下的設計。原則很簡單：**任何放進 sandbox 的東西，都要假設 sandbox 裡的程式讀得到，因此模型讀得到，因此任何能影響模型的人都可能讀得到。** 用「叮嚀模型不要讀環境變數」或「把 token 的權限縮小」都只是降低損害；結構上讓 secret 不在 sandbox 裡，才是消除這條路徑。

**credential proxy**（憑證代理）是實現這個原則的標準做法：sandbox 只拿到一個短效、只在這個 session 有效、只能在 proxy 上使用的 **session token**；真正的憑證存放在 proxy 背後的 vault，proxy 在比對 allowlist 之後，於邊界外把真憑證注入到轉送出去的請求裡。sandbox 裡的程式從頭到尾只看過 session token；即使它被外洩，也只能在 session 存活期間、透過 proxy、存取 allowlist 允許的那幾個端點。

```text
 sandbox 內的程式          Credential Proxy                 Vault            ERP
     │                          │                            │                │
     │─ GET /v1/orders ────────►│                            │                │
     │  token=sess-7f3a         │ 驗證 session、比對規則     │                │
     │                          │─ 取 erp 憑證 ─────────────►│                │
     │                          │◄──────────── erp-live-…  ──│                │
     │                          │ 移除 sandbox 自帶的        │                │
     │                          │ Authorization，注入真憑證  │                │
     │                          │─ GET /v1/orders（Bearer 真憑證）───────────►│
     │                          │◄──────────────────────────────── 訂單資料 ──│
     │                          │ 回應中若出現 secret 就遮蔽 │                │
     │◄──────── 訂單資料 ───────│ 寫稽核紀錄                 │                │
     │                          │                            │                │
     │   session 結束：proxy 撤銷 sess-7f3a，之後任何請求都回 403              │
```

時序圖由上往下讀。sandbox 送出的請求只帶 session token；proxy 驗證之後才向 vault 取真憑證，並且先移除 sandbox 自己附上的 `Authorization` header，避免程式用猜測或偷來的憑證直接打上游。轉送時注入真憑證，回應回來後再檢查一次：有些上游服務會在錯誤訊息或 debug 端點回顯收到的 header，proxy 必須把回應中出現的 secret 遮蔽掉，否則 secret 會從回應繞回 sandbox。最後一行是生命週期：session 結束時 token 立即撤銷，所以 token 的價值和 sandbox 的壽命綁在一起。這個設計和第 14 章 MCP 授權規範禁止 token passthrough（server 不得把收到的 token 原樣轉給下游）是同一個精神：憑證不跨越信任邊界。

```python
from __future__ import annotations

import posixpath
from dataclasses import dataclass, field


@dataclass
class Rule:
    host: str
    method: str
    path_prefix: str
    secret: str | None = None          # 這條規則要注入哪一把 secret（None 代表不需要憑證）


@dataclass
class Session:
    token: str
    tenant: str
    expires_at: float
    rules: list[Rule]


@dataclass
class CredentialProxy:
    """sandbox 唯一能連到的出口。真正的 secret 只存在這裡，sandbox 只拿到短效的 session token。"""
    vault: dict[str, str]
    sessions: dict[str, Session] = field(default_factory=dict)
    audit: list[str] = field(default_factory=list)
    now: float = 0.0                   # 模擬時鐘，讓輸出可重現

    def handle(self, token: str, method: str, host: str, path: str, headers: dict[str, str]) -> tuple[int, str]:
        s = self.sessions.get(token)
        if s is None or self.now >= s.expires_at:
            return self._log(403, "session 無效或已過期", method, host, path)
        clean = posixpath.normpath(path.split("?", 1)[0])   # 先正規化再比對，避免 /v1/orders/../ 繞過前綴
        rule = next((r for r in s.rules if r.host == host and r.method == method
                     and clean.startswith(r.path_prefix)), None)
        if rule is None:               # 預設拒絕：沒有明確允許的 (host, method, path) 一律擋下
            return self._log(403, "egress 不在 allowlist", method, host, path, s.tenant)
        upstream = {k: v for k, v in headers.items() if k.lower() != "authorization"}  # 丟掉 sandbox 自帶的憑證
        if rule.secret:
            upstream["Authorization"] = f"Bearer {self.vault[rule.secret]}"            # 在邊界外注入
        body = fake_upstream(method, host, path, upstream, s.tenant)
        for secret in self.vault.values():                                              # 回應若回顯 secret 就遮掉
            body = body.replace(secret, "[REDACTED]")
        return self._log(200, body, method, host, path, s.tenant)

    def _log(self, code: int, body: str, method: str, host: str, path: str, tenant: str = "?") -> tuple[int, str]:
        self.audit.append(f"t={self.now:>4} tenant={tenant:<6} {code} {method} {host}{path}")
        return code, body


def fake_upstream(method: str, host: str, path: str, headers: dict[str, str], tenant: str) -> str:
    """假的 ERP：檢查憑證，並且（很糟地）把收到的 header 回顯在錯誤訊息裡。"""
    if headers.get("Authorization") != "Bearer erp-live-9f2c":
        return "401 unauthorized"
    if path.startswith("/v1/orders"):
        return f'{{"tenant": "{tenant}", "orders": 1284, "returned": 97}}'
    return f"debug: got headers {headers}"


proxy = CredentialProxy(vault={"erp": "erp-live-9f2c"})
proxy.sessions["sess-7f3a"] = Session("sess-7f3a", "shop42", expires_at=900, rules=[
    Rule("erp.internal", "GET", "/v1/orders", secret="erp"),
    Rule("erp.internal", "GET", "/v1/debug", secret="erp"),
    Rule("pypi-mirror.internal", "GET", "/simple/"),
])

requests = [
    (10, "sess-7f3a", "GET", "erp.internal", "/v1/orders?week=39", {}),
    (20, "sess-7f3a", "POST", "erp.internal", "/v1/refunds", {}),
    (30, "sess-7f3a", "GET", "paste.example.com", "/upload", {}),
    (35, "sess-7f3a", "GET", "erp.internal", "/v1/orders/../refunds", {}),
    (40, "sess-7f3a", "GET", "erp.internal", "/v1/orders", {"Authorization": "Bearer guessed"}),
    (50, "sess-7f3a", "GET", "erp.internal", "/v1/debug", {}),
    (999, "sess-7f3a", "GET", "erp.internal", "/v1/orders", {}),
]
seen_by_sandbox = []
for t, token, method, host, path, headers in requests:
    proxy.now = t
    code, body = proxy.handle(token, method, host, path, headers)
    seen_by_sandbox.append(body)
    print(f"{method:<4} {host + path:<38} → {code} {body[:52]}")

print("\n稽核紀錄：")
print("\n".join(proxy.audit))
assert all("erp-live-9f2c" not in b for b in seen_by_sandbox)     # sandbox 從頭到尾沒看過真的 secret
assert [line.split()[-3] for line in proxy.audit] == ["200", "403", "403", "403", "200", "200", "403"]
```

```text
GET  erp.internal/v1/orders?week=39         → 200 {"tenant": "shop42", "orders": 1284, "returned": 97}
POST erp.internal/v1/refunds                → 403 egress 不在 allowlist
GET  paste.example.com/upload               → 403 egress 不在 allowlist
GET  erp.internal/v1/orders/../refunds      → 403 egress 不在 allowlist
GET  erp.internal/v1/orders                 → 200 {"tenant": "shop42", "orders": 1284, "returned": 97}
GET  erp.internal/v1/debug                  → 200 debug: got headers {'Authorization': 'Bearer [REDACT
GET  erp.internal/v1/orders                 → 403 session 無效或已過期

稽核紀錄：
t=  10 tenant=shop42 200 GET erp.internal/v1/orders?week=39
t=  20 tenant=shop42 403 POST erp.internal/v1/refunds
t=  30 tenant=shop42 403 GET paste.example.com/upload
t=  35 tenant=shop42 403 GET erp.internal/v1/orders/../refunds
t=  40 tenant=shop42 200 GET erp.internal/v1/orders
t=  50 tenant=shop42 200 GET erp.internal/v1/debug
t= 999 tenant=?      403 GET erp.internal/v1/orders
```

輸出的前七行是 sandbox 看到的回應，後七行是 proxy 留下的稽核紀錄。第一行是正常查詢：sandbox 沒帶任何憑證，proxy 注入後上游回傳資料。第二行是同一個 host 的 `POST /v1/refunds`，這個 session 只被授予唯讀規則，所以被擋。第三行是不在 allowlist 的外部網域，這就是 17.5 節說的外洩出口。第四行用 `..` 想從允許的前綴走到退款端點，正規化之後變成 `/v1/refunds`，沒有對應的 GET 規則，被擋下。第五行 sandbox 自己帶了一個猜測的 `Authorization`，proxy 先丟掉它再注入真憑證，所以請求照常成功，但 sandbox 的憑證完全沒被使用。第六行是那個會回顯 header 的 debug 端點：上游確實把真憑證放進了回應，proxy 在送回 sandbox 前把它換成 `[REDACTED]`。最後一行發生在 t=999，session 已過期，稽核紀錄的租戶欄是 `?`，因為 proxy 已經無法把這個 token 對應到任何租戶。程式最後的 assert 保證：七個回應裡沒有任何一個含有真正的 secret。

| 做法 | secret 在 sandbox 裡嗎 | 外洩後的影響 | 適用 |
|---|---|---|---|
| 環境變數或設定檔放長效 token | 在 | 直到人工輪替前都有效，範圍是 token 的全部權限 | 不建議 |
| 放短效、窄範圍的 token | 在，但很快過期 | 有效期間內仍可在任何地方使用 | 上游不支援 proxy 時的折衷 |
| credential proxy 注入 | 不在，只有 session token | 只能在 session 期間、透過 proxy、存取 allowlist 端點 | 預設做法 |
| 改由 harness 端的 tool 執行 | 不在，sandbox 只發出 tool 請求 | sandbox 拿不到任何網路能力 | 呼叫次數少、需要人工核准或審計的動作 |

最後一列值得多說一句。另一種讓 secret 不進 sandbox 的做法，是根本不讓 sandbox 打 API：sandbox 裡的程式呼叫的是一個「轉回 harness 的函式」，由 harness 在信任區用自己的權限執行對應的 tool，再把結果交回程式。第 13 章介紹的 programmatic tool calling 就是這種形態：程式在 sandbox 裡跑，tool 呼叫回到 harness，只有結果進入程式。它的好處是每一次 tool 呼叫都經過 harness 的權限檢查；而且依第 13 章的 `code_callable` 規則，只有唯讀 tool 開放從程式呼叫，有副作用（write／destructive）的 tool 一律 `code_callable=False`，必須回到一般 tool call、走第 21 章的核准流程，不會藏在程式的迴圈裡繞過核准。代價是每次呼叫都要跨越邊界，不適合大量的資料抓取。

## 17.7 Sandbox 生命週期與 pool

sandbox 不是一次性的函式呼叫，而是有生命週期的資源：要建立、要等它開機、要租給某個任務、要回收。生命週期的設計同時決定了安全（狀態會不會跨任務殘留）、延遲（使用者要等多久）與成本（有多少台開著卻沒人用）。先看狀態機：

```text
            ┌──────────┐  開機完成   ┌──────────┐  任務取用   ┌────────────┐
 建立請求 ─►│ booting  │────────────►│  warm    │────────────►│  leased    │
            └────┬─────┘             └────┬─────┘             │ （執行中／ │
                 │ 開機失敗               │ 閒置超過 TTL      │   閒置中） │
                 ▼                        ▼                   └──┬──┬──┬───┘
            ┌──────────────────────────────────────┐   正常結束  │  │  │
            │              destroyed               │◄────────────┘  │  │
            │  （連同檔案系統、session token 一起  │◄── 租期上限 ───┘  │
            │    銷毀；不會回到 warm）             │◄── 健康檢查失敗 ──┘
            └──────────────────────────────────────┘
                 ▲
                 └── 需要暫停時：leased ─► snapshot ─► 之後由 snapshot 還原成新的 sandbox
```

這張狀態機的關鍵是**只有一個終點，而且沒有往回的箭頭**。sandbox 從 booting 開機成 warm 待命，被任務取用後進入 leased；leased 可以是執行中，也可以是兩次執行之間的閒置（例如 coding agent 在等模型想下一步）。不論是正常結束、超過租期上限，還是健康檢查失敗，都走向 destroyed，連同檔案系統與 session token 一起銷毀。圖中刻意沒有「leased 回到 warm」的箭頭：把用過的 sandbox 清理後給下一個任務，需要保證清得乾淨（暫存檔、背景 process、環境中被改過的設定），這比重新開一台難驗證得多。需要暫停的長任務，則用 **snapshot**（把 sandbox 的檔案系統與記憶體狀態存成映像）保存，之後還原成一台新的 sandbox 繼續，而不是讓原來那台一直開著。

sandbox 的**範圍**也要明確定義：

| 範圍 | 狀態保留 | 成本 | 適用 | 注意 |
|---|---|---|---|---|
| 每次執行一台 | 不保留，每段程式都從乾淨環境開始 | 開機次數最多 | 一次性的計算、轉檔 | 模型要在每段程式裡重新讀資料 |
| 每個 session 一台 | 同一個任務的多段程式共享檔案與變數 | 中，閒置時仍佔資源 | 資料分析、coding agent | 要有閒置 TTL 與租期上限 |
| 每個租戶長駐一台 | 跨任務保留 | 最高，且累積風險 | 很少適用 | 跨任務殘留，違反用完即丟的原則 |

報表助理選擇「每個 session 一台」：店家問完第一個問題後常常追問「那換成看上一季呢」，模型可以沿用已經讀進來的資料，不必重新載入。但 session 一結束、或閒置超過十分鐘，sandbox 就銷毀。

冷啟動的延遲問題由 **warm pool**（預熱池）處理：事先開好幾台待命的 sandbox，任務一來就直接取用，取走一台就補開一台。代價是待命的 sandbox 雖然沒人用，仍然佔記憶體與計費時間。下面用模擬時鐘比較「不預熱」與「保持兩台待命」：

```python
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from itertools import count


@dataclass
class Sandbox:
    id: str
    ready_at: float
    state: str = "booting"            # booting → warm → leased → destroyed（不會回到 warm）
    tenant: str | None = None
    history: list[str] = field(default_factory=list)


class SandboxPool:
    """warm pool：預先開好 min_warm 台待命；每台只服務一個任務，用完即銷毀，再補一台新的。"""

    def __init__(self, min_warm: int, max_total: int, boot_s: float, max_lease_s: float):
        self.min_warm, self.max_total = min_warm, max_total
        self.boot_s, self.max_lease_s = boot_s, max_lease_s
        self.boxes: dict[str, Sandbox] = {}
        self._ids = count(1)
        self.idle_seconds = 0.0           # 開好卻沒人用的時間：warm pool 的成本

    def alive(self) -> list[Sandbox]:
        return [b for b in self.boxes.values() if b.state != "destroyed"]

    def _boot(self, now: float) -> Sandbox:
        b = Sandbox(f"sbx-{next(self._ids):02d}", ready_at=now + self.boot_s)
        b.history.append(f"{now:.1f} boot")
        self.boxes[b.id] = b
        return b

    def refill(self, now: float) -> None:
        for b in self.alive():
            if b.state == "booting" and b.ready_at <= now:
                b.state = "warm"
        spare = [b for b in self.alive() if b.state in ("booting", "warm")]
        while len(spare) < self.min_warm and len(self.alive()) < self.max_total:
            spare.append(self._boot(now))

    def acquire(self, tenant: str, now: float) -> tuple[Sandbox | None, float, str]:
        self.refill(now)
        spare = sorted((b for b in self.alive() if b.state in ("booting", "warm")), key=lambda b: b.ready_at)
        if spare:                                              # 有待命的就用；還在開機就等它開完
            b = spare[0]
            wait, how = max(0.0, b.ready_at - now), ("warm" if b.ready_at <= now else "booting")
        elif len(self.alive()) < self.max_total:
            b = self._boot(now)
            wait, how = self.boot_s, "cold"                    # 冷啟動：使用者要等完整開機時間
        else:
            return None, 0.0, "queued"                         # 滿了：交給上層排隊或回 429
        self.idle_seconds += max(0.0, now - b.ready_at)
        b.state, b.tenant = "leased", tenant
        b.history.append(f"{now:.1f} lease {tenant}")
        self.refill(now)                                       # 租出一台就立刻補一台
        return b, wait, how

    def release(self, b: Sandbox, now: float, reason: str) -> None:
        b.state = "destroyed"                                  # 不 reset、不給下一個任務：直接丟掉
        b.history.append(f"{now:.1f} destroy ({reason})")
        self.refill(now)


def simulate(min_warm: int, tasks: list[tuple[float, str, float]], end: float = 20.0):
    pool = SandboxPool(min_warm=min_warm, max_total=4, boot_s=2.0, max_lease_s=10.0)
    pool.refill(-5.0)                                          # 服務啟動時先把 pool 暖好
    events, lines, seq = [], [], count()
    for arrive, tenant, dur in tasks:
        heapq.heappush(events, (arrive, next(seq), "arrive", tenant, dur))
    while events:
        now, _, kind, who, payload = heapq.heappop(events)
        if kind == "arrive":
            b, wait, how = pool.acquire(who, now)
            lines.append((now, who, how, wait, b.id if b else "-"))
            if b:                                              # 超過租期上限就強制收回，避免卡死的任務佔住名額
                reason = "done" if payload <= pool.max_lease_s else "lease_timeout"
                heapq.heappush(events, (now + wait + min(payload, pool.max_lease_s), next(seq),
                                        "release", b.id, reason))
        else:
            pool.release(pool.boxes[who], now, payload)
    pool.refill(end)
    pool.idle_seconds += sum(end - b.ready_at for b in pool.alive() if b.state == "warm")
    return lines, pool


TASKS = [(0.0, "shop42", 3.0), (0.5, "shop17", 4.0), (1.0, "shop42", 2.0),
         (1.2, "shop88", 30.0), (4.0, "shop17", 1.0), (9.0, "shop42", 2.0)]
summary = {}
for min_warm in (0, 2):
    lines, pool = simulate(min_warm, TASKS)
    waits = [w for *_, how, w, _id in lines if how != "queued"]
    summary[min_warm] = (sum(waits) / len(waits), pool.idle_seconds)
    print(f"── min_warm={min_warm}")
    for now, who, how, wait, sid in lines:
        print(f"t={now:>4.1f} {who:<7} {how:<8} wait={wait:.1f}s  {sid}")
    queued = sum(how == "queued" for _, _, how, _, _ in lines)
    print(f"   平均等待 {summary[min_warm][0]:.2f}s，排隊 {queued} 筆，共開機 {len(pool.boxes)} 台，"
          f"warm 閒置累計 {pool.idle_seconds:.1f} 台秒\n")
    assert all(sum(h.split()[1] == "lease" for h in b.history) <= 1 for b in pool.boxes.values())  # 一台只租一次

long_task = next(b for b in pool.boxes.values() if b.tenant == "shop88")
print(f"{long_task.id} 的生命週期：", " → ".join(long_task.history))
assert "lease_timeout" in long_task.history[-1]
assert summary[2][0] < summary[0][0] and summary[2][1] > summary[0][1]   # 用閒置成本換等待時間
```

```text
── min_warm=0
t= 0.0 shop42  cold     wait=2.0s  sbx-01
t= 0.5 shop17  cold     wait=2.0s  sbx-02
t= 1.0 shop42  cold     wait=2.0s  sbx-03
t= 1.2 shop88  cold     wait=2.0s  sbx-04
t= 4.0 shop17  queued   wait=0.0s  -
t= 9.0 shop42  cold     wait=2.0s  sbx-05
   平均等待 2.00s，排隊 1 筆，共開機 5 台，warm 閒置累計 0.0 台秒

── min_warm=2
t= 0.0 shop42  warm     wait=0.0s  sbx-01
t= 0.5 shop17  warm     wait=0.0s  sbx-02
t= 1.0 shop42  booting  wait=1.0s  sbx-03
t= 1.2 shop88  booting  wait=1.3s  sbx-04
t= 4.0 shop17  booting  wait=1.0s  sbx-05
t= 9.0 shop42  warm     wait=0.0s  sbx-06
   平均等待 0.55s，排隊 0 筆，共開機 8 台，warm 閒置累計 32.0 台秒

sbx-04 的生命週期： 0.5 boot → 1.2 lease shop88 → 12.5 destroy (lease_timeout)
```

逐段解讀。`min_warm=0` 時每個任務都是冷啟動，每次都要等完整的 2 秒開機；t=4.0 時四台都被佔用（其中 shop88 那一台跑的是一個 30 秒的任務），容量達到 `max_total=4`，這個請求只能排隊。`min_warm=2` 時，前兩個任務直接拿到暖好的 sandbox，等待 0 秒；第三、四個任務來得太密，pool 正在補開的機器還沒開完，只好等它開完，所以出現 `booting` 狀態，等待時間介於 0 與 2 秒之間。平均等待從 2.00 秒降到 0.55 秒，代價是多開了 3 台、累積了 32 台秒的閒置時間，這就是 warm pool 的取捨：**用閒置成本換使用者等待**。

最後一行是 shop88 那個 30 秒任務的生命週期：它在 t=12.5 被以 `lease_timeout` 強制銷毀，因為租期上限是 10 秒（從開始執行起算）。沒有租期上限，一個卡住的任務會永久佔住一個名額，pool 的實際容量會隨時間慢慢流失。程式裡的兩個 assert 鎖住了這一節的兩條原則：每台 sandbox 最多只被租一次；預熱降低了等待，也一定增加閒置成本。

pool 的大小可以用 **Little's law**（排隊理論的基本關係：系統中的平均數量＝到達率 × 平均停留時間）粗估。假設尖峰時每秒有 2 個新任務要 sandbox、開機要 2 秒，那麼「正在補開」的機器平均約有 4 台；要讓大多數任務不必等開機，待命的數量至少要能覆蓋這段補開時間，再依尖峰波動加上緩衝。同時執行中的 sandbox 數量則是「到達率 × 平均租用時間」，它決定了 `max_total` 與底層機器的容量。第 36 章與第 43 章會把這個估算放進完整的平台設計。

## 17.8 動手做：概念版的受限執行器

這一節把 17.4 節的資源限制寫成一個可以在 macOS 與 Linux 執行的執行器 `run_untrusted()`。它做五件事：每次執行建立獨立的暫存目錄、用乾淨的環境變數啟動子行程、在子行程裡設定 rlimit（CPU 時間、記憶體、檔案大小、core dump）、由父行程執行 wall clock 逾時並整組砍掉、只把截斷後的輸出帶回來。最重要的一點是：**它會回報哪些限制真的生效**，在不支援的平台上照樣執行，但明確告訴呼叫端「這個限制沒有生效」，而不是默默假裝安全。

> [!warning] 這不是安全邊界
> 本節的執行器只是 17.3 節的 (a) process 層加上資源上限。它沒有檔案系統隔離（程式讀得到所有目前使用者讀得到的檔案）、沒有網路隔離、沒有 system call 過濾，也不能防止程式建立大量子行程。它適合用來理解機制、在開發機上保護自己的程式不被意外拖垮；處理任何不可信輸入、多租戶或 production 流量時，必須換成 gVisor 或 microVM，搭配 cgroup、預設拒絕的 egress 與 credential proxy。

```text
 run_untrusted(code, limits, inputs)
   │
   ├─ (1) 建立 sbx-XXXX/work（cwd、HOME、TMPDIR）與 sbx-XXXX/out（stdout、stderr 檔）
   ├─ (2) 只放入這次的輸入檔與 main.py；環境變數只給 PATH、HOME、TMPDIR、LANG
   ├─ (3) Popen：python -I -c BOOTSTRAP（新的 process group，傳入一個 pipe fd）
   │        │
   │        └─ 子行程 bootstrap：逐項 setrlimit
   │             ├─ 成功 → 記錄「生效」
   │             └─ 失敗 → 記錄「未生效」與原因（例如 macOS 的記憶體限制）
   │           把報告寫進 pipe、關閉 pipe，才執行 main.py
   ├─ (4) 父行程 wait(timeout=wall_seconds)
   │        ├─ 正常結束 → ok／error
   │        ├─ 被 SIGXCPU 終止 → cpu_limit
   │        └─ 逾時 → killpg 整組砍掉 → timeout
   ├─ (5) 讀 stdout 前 N 字元（超過就截斷並註明原始大小）、stderr 最後一行、產物清單
   └─ (6) 離開 TemporaryDirectory：整個目錄連同產物一起刪除
```

流程圖的第 (3) 步是這個設計的關鍵。Python 的 `subprocess` 提供 `preexec_fn` 讓你在子行程啟動前設定 rlimit，但只要其中一項 `setrlimit` 失敗，整個子行程就啟動失敗，沒辦法「這項不支援就跳過並回報」；`preexec_fn` 在多執行緒程式裡也不安全。所以這裡改用一小段 bootstrap 程式：子行程自己逐項設定，把結果寫進一個只有它拿得到的 pipe，關閉 pipe 之後才執行使用者程式，使用者程式因此無法偽造這份報告。`-I` 是 Python 的隔離模式，會忽略 `PYTHON*` 環境變數與使用者的 site-packages，避免環境影響執行結果。第 (4) 步用 `start_new_session=True` 讓子行程自成一個 process group，逾時時用 `killpg` 連同它開出來的子行程一起結束。

```python
from __future__ import annotations

import json
import os
import platform
import resource
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# 子行程裡先跑這段 bootstrap：自己設定 rlimit、把「哪些限制生效」寫進 pipe、關掉 pipe，才執行使用者程式。
# 用 bootstrap 而不用 preexec_fn，是因為 setrlimit 失敗時 preexec_fn 只能整個失敗，無法優雅降級。
BOOTSTRAP = r"""
import json, os, resource, runpy, sys
fd, limits, script = int(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3]
report = {}
for logical, candidates, value in limits:
    report[logical], tried = "未生效：此平台沒有對應的 rlimit", []
    for name in candidates:
        res = getattr(resource, name, None)
        if res is None:
            continue
        try:
            hard = value + 1 if name == "RLIMIT_CPU" else value   # CPU：soft 先送 SIGXCPU
            resource.setrlimit(res, (value, hard))                # 同時壓低 hard，程式無法自己調回去
            report[logical] = f"生效（{name}）"
            break
        except (ValueError, OSError) as exc:
            tried.append(name)
            report[logical] = f"未生效（{'、'.join(tried)} 皆被拒絕：{exc}）"
os.write(fd, json.dumps(report, ensure_ascii=False).encode())
os.close(fd)                                                      # 使用者程式拿不到這個 fd，無法偽造報告
sys.argv = [script]
runpy.run_path(script, run_name="__main__")
"""


@dataclass
class Limits:
    cpu_seconds: int = 2
    memory_mb: int = 256
    file_mb: int = 1
    wall_seconds: float = 3.0
    max_output: int = 600              # 帶回 context 的 stdout 上限（字元）


@dataclass
class ExecResult:
    status: str                        # ok｜error｜cpu_limit｜timeout｜killed
    exit_code: int | None
    stdout: str
    stderr_tail: str
    truncated: bool
    cpu_seconds: float
    applied: dict[str, str]
    warnings: list[str]
    artifacts: dict[str, int] = field(default_factory=dict)


def run_untrusted(code: str, limits: Limits, inputs: dict[str, str] | None = None) -> ExecResult:
    with tempfile.TemporaryDirectory(prefix="sbx-") as root:
        work, out = Path(root, "work"), Path(root, "out")
        work.mkdir(); out.mkdir()
        for name, content in (inputs or {}).items():       # 只放進這次任務需要的輸入
            (work / name).write_text(content, encoding="utf-8")
        (work / "main.py").write_text(code, encoding="utf-8")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(work), "TMPDIR": str(work), "LANG": "C.UTF-8"}
        spec = [("cpu", ["RLIMIT_CPU"], limits.cpu_seconds),
                ("memory", ["RLIMIT_AS", "RLIMIT_DATA"], limits.memory_mb << 20),
                ("file_size", ["RLIMIT_FSIZE"], limits.file_mb << 20),
                ("core_dump", ["RLIMIT_CORE"], 0)]
        r_fd, w_fd = os.pipe()
        before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
        with open(out / "stdout", "wb") as so, open(out / "stderr", "wb") as se:
            proc = subprocess.Popen(
                [sys.executable, "-I", "-c", BOOTSTRAP, str(w_fd), json.dumps(spec), "main.py"],
                cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=so, stderr=se,
                pass_fds=(w_fd,), start_new_session=True)       # 自己一個 process group，逾時可整組砍掉
            os.close(w_fd)
            try:
                code_ = proc.wait(timeout=limits.wall_seconds)
                status = "ok" if code_ == 0 else "error"
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                code_, status = None, "timeout"
        applied = json.loads(os.read(r_fd, 65536) or b"{}")
        os.close(r_fd)
        if code_ is not None and code_ < 0:
            status = "cpu_limit" if -code_ == signal.SIGXCPU else "killed"   # 其他訊號：例如被 OOM killer 收掉
        raw = (out / "stdout").read_bytes()
        text = raw[: limits.max_output * 4].decode("utf-8", "replace")
        truncated = len(text) > limits.max_output or len(raw) > limits.max_output * 4
        if truncated:
            text = text[: limits.max_output] + f"\n…（已截斷：原始輸出 {len(raw):,} bytes）"
        err_lines = (out / "stderr").read_bytes()[-2000:].decode("utf-8", "replace").strip().splitlines()
        artifacts = {p.name: p.stat().st_size for p in work.iterdir()
                     if p.is_file() and p.name not in (inputs or {}) and p.name != "main.py"}
        cpu = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime - before
        warnings = [f"{k} 限制{v}" for k, v in applied.items() if not v.startswith("生效")]
        return ExecResult(status, code_, text, err_lines[-1] if err_lines else "", truncated,
                          round(cpu, 2), applied, warnings, artifacts)
    # 離開 with：整個暫存目錄連同產物一起刪除，下一次執行看不到這次留下的任何東西


os.environ["BLUEBIRD_ERP_TOKEN"] = "erp-live-THIS-SHOULD-NEVER-LEAK"   # 模擬 agent 服務本身持有的 secret
ORDERS_CSV = "category,returned\n服飾,1\n服飾,0\n家電,0\n服飾,1\n家電,1\n"
CASES = {
    "A 正常報表": ("import csv, collections, json\n"
                 "rows = list(csv.DictReader(open('orders.csv', encoding='utf-8')))\n"
                 "rate = collections.defaultdict(list)\n"
                 "for r in rows: rate[r['category']].append(int(r['returned']))\n"
                 "res = {k: round(sum(v) / len(v), 2) for k, v in rate.items()}\n"
                 "json.dump(res, open('report.json', 'w'), ensure_ascii=False)\n"
                 "print(res)", Limits()),
    "B 看得到哪些環境變數": ("import os; print(sorted(os.environ))", Limits()),
    "C 無窮迴圈（吃 CPU）": ("while True: pass", Limits(cpu_seconds=1)),
    "D 卡住不動（不吃 CPU）": ("import time; time.sleep(30)", Limits(wall_seconds=1.0)),
    "E 輸出洗版": ("for i in range(20000): print('row', i)", Limits()),
    "F 寫出巨大檔案": ("open('dump.bin', 'wb').write(b'0' * (5 << 20))", Limits(file_mb=1)),
    "G 吃記憶體": ("x = bytearray(400 << 20); print('配置成功', len(x) >> 20, 'MB')", Limits(memory_mb=256)),
    "H 概念版擋不住的事": ("import os, socket\n"
                       "s = socket.socket(); s.close()\n"
                       "print('讀得到 /etc/hosts:', os.access('/etc/hosts', os.R_OK), '| 可建立 socket:', s.fileno() == -1)",
                       Limits()),
}

print(f"平台：{platform.system()}\n")
results = {}
for title, (code, lim) in CASES.items():
    r = run_untrusted(code, lim, inputs={"orders.csv": ORDERS_CSV})
    results[title] = r
    first = r.stdout.splitlines()[0] if r.stdout else ""
    print(f"── {title}: status={r.status} exit={r.exit_code} cpu={r.cpu_seconds}s")
    if first: print(f"   stdout: {first[:70]}")
    if r.stderr_tail: print(f"   stderr: {r.stderr_tail[:70]}")
    if r.truncated: print(f"   {r.stdout.splitlines()[-1]}")
    if r.artifacts: print(f"   產物: {r.artifacts}")
print("\n限制實際生效情況（每次執行都會回報）：")
for k, v in results["G 吃記憶體"].applied.items():
    print(f"   {k:<10} {v}")
for w in results["G 吃記憶體"].warnings:
    print(f"   WARN {w}")

assert results["A 正常報表"].status == "ok" and "report.json" in results["A 正常報表"].artifacts
assert "BLUEBIRD_ERP_TOKEN" not in results["B 看得到哪些環境變數"].stdout
assert results["C 無窮迴圈（吃 CPU）"].status == "cpu_limit"
assert results["D 卡住不動（不吃 CPU）"].status == "timeout"
assert results["E 輸出洗版"].truncated and len(results["E 輸出洗版"].stdout) < 700
assert "True" in results["H 概念版擋不住的事"].stdout       # 檔案與網路都沒有被隔離：這不是安全邊界
assert results["F 寫出巨大檔案"].status == "error" and "too large" in results["F 寫出巨大檔案"].stderr_tail
g = results["G 吃記憶體"]
if g.applied["memory"].startswith("生效"):
    assert g.status == "error" and "MemoryError" in g.stderr_tail
else:
    assert g.status == "ok" and g.warnings                  # 降級：照樣執行，但明確回報限制沒生效
    print("\n注意：此平台的記憶體 rlimit 沒有生效，G 的配置成功了。概念版只能如實回報，")
    print("      production 必須改用 cgroup memory.max 或 microVM 的記憶體上限。")
```

以下是在 macOS 上實際執行的輸出：

```text
平台：Darwin

── A 正常報表: status=ok exit=0 cpu=0.02s
   stdout: {'服飾': 0.67, '家電': 0.5}
   產物: {'report.json': 31}
── B 看得到哪些環境變數: status=ok exit=0 cpu=0.02s
   stdout: ['HOME', 'LANG', 'PATH', 'TMPDIR', '__CF_USER_TEXT_ENCODING']
── C 無窮迴圈（吃 CPU）: status=cpu_limit exit=-24 cpu=0.99s
── D 卡住不動（不吃 CPU）: status=timeout exit=None cpu=0.01s
── E 輸出洗版: status=ok exit=0 cpu=0.03s
   stdout: row 0
   …（已截斷：原始輸出 188,890 bytes）
── F 寫出巨大檔案: status=error exit=1 cpu=0.02s
   stderr: OSError: [Errno 27] File too large
   產物: {'dump.bin': 1048576}
── G 吃記憶體: status=ok exit=0 cpu=0.02s
   stdout: 配置成功 400 MB
── H 概念版擋不住的事: status=ok exit=0 cpu=0.02s
   stdout: 讀得到 /etc/hosts: True | 可建立 socket: True

限制實際生效情況（每次執行都會回報）：
   cpu        生效（RLIMIT_CPU）
   memory     未生效（RLIMIT_AS、RLIMIT_DATA 皆被拒絕：current limit exceeds maximum limit）
   file_size  生效（RLIMIT_FSIZE）
   core_dump  生效（RLIMIT_CORE）
   WARN memory 限制未生效（RLIMIT_AS、RLIMIT_DATA 皆被拒絕：current limit exceeds maximum limit）

注意：此平台的記憶體 rlimit 沒有生效，G 的配置成功了。概念版只能如實回報，
      production 必須改用 cgroup memory.max 或 microVM 的記憶體上限。
```

逐個情境解說。

**A（正常報表）**是報表助理的主路徑：程式讀取放進 workspace 的 `orders.csv`，算出各品類退貨率，印出一行結果並寫出 `report.json`。執行器把 `report.json` 列為產物（31 bytes），輸入檔與 `main.py` 不算在內。實際系統會在這一步檢查產物大小與格式後才帶出邊界，然後整個暫存目錄被刪除。

**B（環境變數）**驗證 secret 沒有被繼承：父行程的環境裡有 `BLUEBIRD_ERP_TOKEN`，但子行程只看到執行器明確給的四個變數。第五個 `__CF_USER_TEXT_ENCODING` 是 macOS 在啟動行程時自動加入的文字編碼設定，不是從父行程洩漏的，在 Linux 上不會出現。這也提醒我們：「傳入一個乾淨的 env」才是正確做法，「從 os.environ 複製再刪掉敏感的」永遠會漏掉某一個。

**C 與 D** 是一組對照，正好對應 17.4 節「CPU 時間和 wall clock 是兩件事」。C 的無窮迴圈在用滿約 1 秒 CPU 後被 kernel 送出 SIGXCPU，exit code 是 -24（被第 24 號訊號終止），執行器把它歸類為 `cpu_limit`。D 只是 sleep，CPU 用量是 0.01 秒，`RLIMIT_CPU` 永遠不會觸發；擋下它的是父行程的 1 秒 wall clock 逾時，`killpg` 把整個 process group 砍掉，exit code 因此是 `None`。只設其中一種上限，另一種情境就會永遠卡住。

**E（輸出洗版）**印了將近 19 萬 bytes，執行器只帶回前 600 個字元，並在最後一行註明原始大小。這行註記是寫給模型看的，和第 4 章 tool 結果截斷的原則相同：讓模型知道自己沒看到全部，下一步改成先彙總再印。輸出先寫到檔案再讀前段，而不是用 `communicate()` 收進記憶體，是為了避免洗版的程式把父行程的記憶體也撐爆；而 stdout 檔本身也受 `RLIMIT_FSIZE` 限制。

**F（巨大檔案）**想寫 5 MB，寫到 1 MB 時被 `RLIMIT_FSIZE` 擋下，Python 收到 `OSError: File too large`（Python 啟動時會忽略 SIGXFSZ 訊號，所以表現為例外而不是被訊號終止）。注意產物清單裡留下一個剛好 1,048,576 bytes 的半截檔案：限制生效不代表狀態乾淨，半截的產物不能當成有效結果交給使用者，這也是 sandbox 要整個丟棄的理由之一。

**G（記憶體）**是優雅降級的示範。在這台 macOS 上，kernel 拒絕了 `RLIMIT_AS` 與 `RLIMIT_DATA` 的設定（setrlimit 回傳錯誤，Python 轉成 `ValueError`），兩個候選都失敗，所以 400 MB 的配置成功了。執行器沒有假裝成功：報告裡寫明「未生效」與原因，`warnings` 欄位帶著這則警告，上層可以據此決定拒絕執行、改用更嚴格的環境，或至少把這次執行標記為未受記憶體保護。在 Linux 上，`RLIMIT_AS` 通常可以設定成功，同一個情境會變成 `status=error`，stderr 最後一行是 `MemoryError`，程式最後的 if 分支就是為兩種平台各自驗證；不過 `RLIMIT_AS` 限制的是虛擬位址空間而不是實際用量，對多執行緒程式或會預先保留大量位址空間的執行環境容易誤殺，所以 production 一律用 cgroup 的 `memory.max`。

**H（擋不住的事）**刻意印出這個執行器的盲點：子行程讀得到 `/etc/hosts`（代表它讀得到目前使用者能讀的所有檔案），也能建立 socket（代表網路沒有被隔離）。這兩行是整個動手做最重要的輸出，它把「這不是安全邊界」從一句警告變成可以驗證的事實。把這個情境留在測試裡也有實際用途：當你把執行器換成真正的 sandbox 時，H 應該改成兩個 False，這就成了驗收測試。

| 能力 | 概念版做到了嗎 | production 對應的機制 |
|---|---|---|
| 不繼承 secret | 是，乾淨的 env | 加上 credential proxy，sandbox 裡根本沒有 secret |
| CPU 時間上限 | 是，`RLIMIT_CPU` | cgroup `cpu.max` ＋ 執行時間上限 |
| wall clock 上限 | 是，父行程計時並整組砍掉 | sandbox manager 的租期上限與強制銷毀 |
| 記憶體上限 | 視平台，可能降級 | cgroup `memory.max` 或 microVM 的記憶體大小 |
| 檔案大小與磁碟 | 部分，只限單一檔案 | 固定大小的 tmpfs 或磁碟配額 |
| 輸出截斷 | 是 | 同左，另存完整輸出供下載 |
| 用完即丟 | 是，暫存目錄刪除 | 整台 sandbox 銷毀，不重用 |
| 檔案系統隔離 | 否 | mount namespace、唯讀根目錄、只掛載輸入 |
| 網路隔離 | 否 | 無網路介面，或只能連到 egress proxy |
| process 數量、system call 過濾 | 否 | cgroup `pids.max`、seccomp、gVisor、microVM |

這張表是把概念版升級到 production 的檢查清單：上半部的能力可以沿用同樣的介面（`Limits`、`ExecResult`、`warnings`），只是底層換成更強的機制；下半部是 process 層根本做不到、必須靠隔離層級提供的能力。介面不變、實作替換，也是 `loom.sandbox` 模組處理 sandbox 的方式：agent loop 只依賴 `run_code(code, limits) -> ExecResult` 這個抽象，開發機上接概念版，正式環境接 gVisor 或 microVM 的 pool。

## 17.9 託管 sandbox 服務：自建還是購買

看完前面幾節就會發現，一個合格的 sandbox 平台包含隔離層、映像管理、資源控制、egress proxy、credential proxy、pool 排程、snapshot 與稽核，自建的工程量不小。市面上因此出現了專門提供 agent sandbox 的託管服務，主要的模型供應商與雲端平台也把 code execution 做成 agent 平台的內建能力。選擇時，不要只比價格與啟動速度，而要回到 17.2 節那張表，逐列確認每一個保證由誰提供。

| 評估面向 | 要問的問題 | 為什麼重要 |
|---|---|---|
| 隔離技術 | 用 container、gVisor 還是 microVM？租戶之間共用什麼？ | 決定 17.3 節的隔離強度 |
| egress 控制 | 能否預設拒絕？allowlist 能細到路徑與方法嗎？DNS 怎麼處理？ | 防外洩的關鍵，很多服務預設是開放網路 |
| 憑證 | 能否不把 secret 放進 sandbox？有沒有 proxy 或 vault 整合？ | 決定 17.6 節的設計能否實現 |
| 生命週期 | session 最長多久？能否 snapshot、fork、暫停？閒置怎麼計費？ | 決定能否支援長任務與成本 |
| 映像 | 能否自帶映像？套件怎麼預裝？ | 決定 egress 能鎖多緊 |
| 資料與合規 | 資料存在哪個區域？暫存磁碟何時清除？能否自行託管？ | 多租戶 SaaS 與受監管產業的硬需求 |
| 觀測 | 能否取得每次執行的資源用量、網路連線紀錄？ | 稽核與事故調查 |

這張表的前三列是安全問題，後四列是營運問題。實務上，安全問題要先有滿意的答案才進入比價；如果某個服務在 egress 或憑證上做不到你的要求，就算便宜也要在它前面再自建一層 proxy，總成本未必划算。另一個常見的混合做法是：託管服務負責隔離與 pool，自己負責 egress proxy 與 credential proxy，因為這兩層和公司的身分系統、內部 API 緊密相關，第 33 章會再談。

### 2026 現況

截至 2026 年 10 月，以下依各家公開文件與 engineering blog 整理，產品功能與價格變動很快，細節請以官方文件為準：

- Anthropic 在 2026 年 5 月的〈How we contain Claude across products〉中描述了三種產品的隔離方式：claude.ai 的 code execution 使用 gVisor 容器、每個 session 獨立的檔案系統與 seccomp；Claude Code 在本機使用 OS 原生 sandbox（macOS 用 Seatbelt、Linux 用 bubblewrap），寫入限於 workspace、網路預設拒絕，無人值守時建議用 devcontainer；Cowork 則在本機 VM 中執行程式，只掛載 workspace，憑證留在 host 的 keychain，並使用 egress allowlist。該文的經驗包括：allowlist 等同授權、symlink 要先解析再驗證，以及成熟的隔離元件（gVisor、seccomp、hypervisor）比自製元件可靠。
- Claude Managed Agents（beta）公開說明其憑證在結構上不可達 sandbox：git token 只在初始化 clone 時使用，MCP 的 OAuth token 存放在 vault，透過 proxy 以 session token 換取。
- OpenAI Codex 的本機 sandbox 在 macOS 使用 Seatbelt、在 Linux 使用 bubblewrap，並有 Windows 原生 sandbox；提供 `read-only`、`workspace-write`（預設）、`danger-full-access` 等模式。Gemini CLI 的原始碼同樣包含 bubblewrap、Seatbelt 與 Windows 的 sandbox 實作。
- OpenAI Agents SDK 提供 sandbox agents 相關抽象，可接本機 Unix、Docker、Modal 等 sandbox client；OpenAI 的 Agents API 中，sandbox 可以是 OpenAI 託管、自行託管或不使用。
- Amazon Bedrock AgentCore 提供 Code Interpreter 與 Browser 服務，其 Harness 服務說明每個 session 在隔離的 microVM 中執行；Google 的 Agent Platform（原 Vertex AI Agent Engine 相關頁面）提供含 snapshot 與 templates 的 Code Execution sandbox。
- 獨立的 agent sandbox 服務包括 E2B、Modal Sandboxes、Daytona、Cloudflare Sandbox、Vercel Sandbox 等。依一般公開介紹（本書未逐項查證），E2B 以 Firecracker microVM 為基礎、Modal 使用 gVisor；各家的隔離技術、egress 控制與計費方式差異很大，評估時請以表中的問題逐項向供應商確認。
- 開源 framework 方面，smolagents 的本地執行器以 AST 檢查限制可用的操作，文件明確強調正式使用要搭配遠端 sandbox；DSPy 的 `LocalInterpreter` 文件也明說它不是 sandbox。評估框架 Inspect 的 eval sandbox 支援 Docker、Kubernetes、Modal 等後端。

## 17.10 實務應用

**情境一：青鳥的營運報表助理（多租戶資料分析）**。這是本章的主線。最後的設計是：每個 session 一台 gVisor sandbox，映像預裝常用的資料分析套件，完全不開網路；店家的匯出檔以唯讀方式掛載，產物只能寫到輸出目錄，且限制為 CSV、PNG 與 Markdown 三種格式。少數需要分頁抓取 ERP 資料的情況，不讓 sandbox 打 API，而是由 harness 先用店家的授權把資料抓好、寫成檔案再掛進去，所以這個 sandbox 裡沒有任何憑證，也沒有任何網路能力。閒置 10 分鐘或 session 結束就銷毀，pool 在上班時段保持數台待命、夜間縮到零。Maya 驗收時用的就是動手做的情境 B 與 H：sandbox 裡看不到 secret，讀不到掛載以外的檔案，也建立不了對外連線。

**情境二：內部 coding agent 在 CI 中修測試**。第 39 章與第 43 章會詳談這類系統。和報表助理不同，coding agent 需要安裝相依套件、執行測試、有時還要啟動資料庫，所以 sandbox 通常是一台有完整 Linux 環境的 microVM 或強化過的 container，生命週期是「每個任務一台」，可能持續數十分鐘。網路只允許連到公司的套件鏡像站與 git server；git 推送用的憑證留在 sandbox 外面，由 harness 在任務結束時取出 diff、經過審查後才推送。主流做法類似：公開文件中，GitHub 的 Copilot coding agent 在 GitHub Actions 的臨時環境中執行（較早的文件也提到限制對外連線的防火牆，現況以官方文件為準），Claude Code 建議無人值守時使用 devcontainer。多個任務平行時，每個任務各自一台 sandbox 與各自的 branch，避免第 20 章談的並行寫入衝突。

**情境三：對外開放的 code interpreter 功能**。如果青鳥未來讓店家直接在產品裡「用自然語言做分析」，寫程式的一方實際上是任何能操作該帳號的人，攻擊者會刻意嘗試突破隔離。這時隔離層級要用 microVM 或 gVisor，搭配嚴格的資源上限與濫用偵測（例如偵測長時間滿載的 CPU 用量，那常常是有人在拿你的運算資源挖礦）。主流聊天產品的資料分析功能都在隔離的 sandbox 中執行使用者上傳的檔案，並限制網路。這類產品還要考慮免費帳號被大量註冊來濫用運算資源，所以 sandbox 配額要和帳號信任等級掛鉤。

**情境四：本機 coding agent 與 MCP server**。開發者在自己的電腦上用 coding agent，程式和開發者的檔案、SSH key、雲端憑證在同一台機器上。這裡啟動 VM 太重，主流做法是 OS 原生 sandbox：寫入限於目前的 workspace，網路預設拒絕或只允許指定網域，超出邊界的操作才跳出核准請求（第 21 章）。第 14 章談的本機 MCP server 也是同一個問題：它們是第三方程式，最好也放進 sandbox 執行，只授予需要的路徑與網域。

| 情境 | 隔離層級 | 範圍 | 網路 | 憑證 | 特別注意 |
|---|---|---|---|---|---|
| 報表助理（多租戶） | gVisor 或 microVM | 每 session 一台 | 無 | 無，由 harness 預先抓資料 | 產物格式檢查、跨租戶絕不重用 |
| CI coding agent | microVM 或強化 container | 每任務一台 | 只到鏡像站與 git | 留在外面，harness 推送 | 平行任務各自隔離 |
| 對外 code interpreter | microVM 或 gVisor | 每 session 一台 | 無或嚴格 allowlist | 無 | 濫用偵測、配額與帳號信任掛鉤 |
| 本機 coding agent | OS 原生 sandbox | 每個 process | 預設拒絕 | 留在 host，不掛進 workspace | 核准疲勞、MCP server 也要隔離 |

這張表顯示，同一套概念在四個情境中組合出不同的答案。共同點是：網路與憑證的預設值永遠是「沒有」，需要時才按任務最小化地開；不同點主要在隔離層級與範圍，取決於「誰寫的程式」與「狀態要保留多久」。

## 17.11 設計檢查清單

1. 模型產生的程式是否在 agent 服務以外的隔離環境執行，而不是在同一個 process 裡 `exec`？
2. 隔離層級選了 process、OS 原生 sandbox、container、gVisor 還是 microVM？選擇理由是否對應「誰寫的程式」與「誰會受害」？
3. 若使用 container，是否已關閉網路、唯讀根目錄、移除 capabilities、禁止提升權限、以非 root 執行，且沒有掛載 Docker socket？
4. CPU 時間、wall clock、記憶體、磁碟、process 數量、輸出長度，六種資源是否都有上限？是以 cgroup 或 VM 執行，而不是只靠 rlimit？
5. 執行器是否回報每項限制是否真的生效？限制未生效時，上層是拒絕執行還是明確標記風險？
6. sandbox 只看得到這次任務的輸入嗎？輸入是唯讀掛載嗎？harness 端的檔案 tool 是否先展開 symlink 再比對路徑？
7. 產物帶出邊界前，是否檢查了大小、數量與格式，並把內容當成不可信資料處理？
8. 網路 egress 是否預設拒絕？若需要對外，是否只能經過 proxy，且 allowlist 細到 host、方法與路徑？DNS 與雲端 metadata 端點是否被封鎖？
9. sandbox 裡是否完全沒有長效憑證？需要呼叫 API 時，是用 credential proxy 注入，還是改由 harness 端的 tool 執行？
10. sandbox 的範圍是每次執行、每個 session 還是每個任務？是否保證用完即銷毀、不跨任務或跨租戶重用？
11. 是否設定了閒置 TTL 與租期上限，並有定期回收遺失 sandbox 的機制？
12. warm pool 的大小是否依到達率與開機時間估算過？是否有尖峰時的排隊或拒絕策略？
13. 每次執行的資源用量、限制觸發、egress 允許與拒絕紀錄，是否寫入稽核並能對應到 trace 與租戶？
14. 是否有驗收測試證明 sandbox 讀不到 secret、讀不到掛載以外的檔案、連不到 allowlist 以外的網域？

## 17.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 一段程式讓同機的其他 session 一起逾時或被 OOM 收掉 | 程式在 agent process 內執行，或 sandbox 沒有 cgroup 上限 | 看事故時段的 process 樹與 cgroup 記錄，確認執行位置 | 移到獨立 sandbox，以 cgroup 或 VM 設定 CPU 與記憶體上限 |
| 程式永遠不結束，但 CPU 用量很低 | 只設了 CPU 時間上限，程式卡在 sleep 或等待 I/O | 比較執行時間與 CPU 時間 | 加上由外部執行的 wall clock 上限，並整組砍掉 process group |
| 逾時後仍有殘留 process 在跑 | 只砍了主 process，子行程沒有被結束 | 列出 sandbox 內或同一 session 的 process | 讓 sandbox 自成 process group 或 cgroup，逾時時整組結束；最終以銷毀整台 sandbox 為準 |
| 在 macOS 開發機測試通過，Linux 上出現 MemoryError | 記憶體 rlimit 在 macOS 未生效，測試其實沒有受記憶體限制 | 檢查執行器回報的 applied 與 warnings | 測試中斷言限制是否生效；以 Linux 或真正的 sandbox 跑 CI |
| 稽核發現 sandbox 曾連到不明網域 | egress 沒有預設拒絕，或 allowlist 包含可上傳內容的公開網域 | 查 proxy 的允許紀錄與 allowlist 版本歷史 | 改成預設拒絕，allowlist 細到路徑與方法，移除可上傳內容的網域 |
| 程式繞過了 HTTP proxy 直接連外 | egress 控制只靠環境變數，sandbox 仍有預設路由 | 在 sandbox 內測試不經 proxy 的連線是否成功 | 移除預設路由與對外 DNS，讓 proxy 成為唯一可到達的位址 |
| log 或模型輸出中出現 API token | secret 以環境變數或檔案放進 sandbox，或上游回應回顯了憑證 | 搜尋 trace 與產物中的 token 前綴 | 改用 credential proxy；proxy 對回應做 secret 遮蔽；立即輪替已外洩的憑證 |
| 下一個任務讀到上一個任務的檔案 | sandbox 被清理後重用，清理不完整 | 比對 sandbox id 是否出現在多個任務的 trace 中 | 改成用完即銷毀；需要加速時用 snapshot 還原新機器，而不是重用舊機器 |
| 尖峰時段使用者等很久才開始執行 | pool 沒有預熱，或待命數量不足以覆蓋開機時間 | 看 acquire 的等待時間分布與冷啟動比例 | 依到達率與開機時間調整待命數量；用 snapshot 縮短開機 |

## 本章重點整理

- agent 需要執行環境來做精確計算、取得真實回饋與 code-as-action，但模型產生的程式必須一律當成不可信的程式，因為它會被 context 中的任何內容影響。
- 在 agent 服務的 process 裡直接 `exec` 會讓程式共用 secret、其他租戶的狀態、CPU 與記憶體，限制 namespace 或 builtins 都不能改變這個事實。
- sandbox 不是單一開關，而是六個獨立的保證：保護服務、host 與其他租戶、憑證、資料、外部世界與下一個任務，每一個都需要各自的機制。
- 隔離層級的核心問題是「共用了什麼」：process 與 container 共用 host kernel，gVisor 大幅縮小 host kernel 的攻擊面，microVM 的邊界是 hypervisor。
- 隔離強度要配合「誰寫的程式」與「誰會受害」：多租戶執行不可信程式時，不應停在共用 host kernel 的那幾層。
- CPU 時間與 wall clock 是兩件事，兩種上限都要有；rlimit 以單一 process 計算，production 要用 cgroup 或 VM 限制整組資源。
- 執行器必須回報每項限制是否真的生效，平台不支援時優雅降級並明確警告，而不是默默假裝安全。
- 檔案系統只放這次任務需要的輸入並唯讀掛載，寫入只落在可整個丟棄的地方；harness 端的檔案 tool 要先展開 symlink 再比對路徑。
- egress 要在網路層預設拒絕，sandbox 唯一能到達的位址是 proxy；allowlist 等同授權，要細到 host、方法與路徑。
- secret 不進 sandbox：用 credential proxy 在邊界外注入真憑證，sandbox 只拿短效的 session token，回應中回顯的 secret 也要遮蔽。
- sandbox 的生命週期只有一個終點：用完即銷毀，不跨任務或跨租戶重用；長任務用 snapshot 保存，並設定閒置 TTL 與租期上限。
- warm pool 用閒置成本換使用者等待時間，大小可以用到達率乘以開機時間粗估，再加上尖峰緩衝。
- 概念版執行器適合理解機制與保護開發機，它沒有檔案、網路與 system call 隔離，不是安全邊界；production 要換成 gVisor 或 microVM，並維持相同的執行器介面。

## 延伸問答

> [!question]- Q1. container、gVisor、microVM 的隔離差別到底在哪裡？為什麼不能說「都是隔離，差不多」？
> 差別在「不可信程式能直接碰到的介面」有多大。container 透過 namespace 與 cgroup 讓程式看到獨立的檔案系統、process 清單與網路，但它的 system call 仍然直接由 host kernel 處理，所以 host kernel 的整個介面都在攻擊面裡；namespace 的實作若有漏洞，影響的就是整台機器上的所有租戶。gVisor 在中間插入 user-space kernel，程式的 system call 先由它處理，它自己只用少量 system call 和 host 互動，攻擊面大幅縮小，代價是部分 system call 的相容性與 I/O 密集工作負載的效能。
>
> microVM 則讓每個 sandbox 有自己的 guest kernel，邊界變成 hypervisor 與一組極少的虛擬裝置。guest kernel 出問題只影響那台 VM，要影響 host 必須突破 hypervisor 這一層。所以三者不是「差不多」，而是三種不同的邊界：kernel 的 namespace 實作、縮小過的 kernel 介面、hypervisor。選擇時要問的是：若這一層出現漏洞，受害的是誰、有幾個？只要答案是「很多租戶」，就應該往邊界更小的那一側選。

> [!question]- Q2. 為什麼 CPU 時間上限和 wall clock 上限都要設？只設一個不行嗎？
> 它們防的是不同的失敗。CPU 時間上限防的是「一直在算」：無窮迴圈、效率極差的演算法，它們會吃滿核心，影響同機的其他工作。wall clock 上限防的是「一直在等」：sleep、等待永遠不會來的網路回應、死結，這類程式幾乎不用 CPU，CPU 時間上限永遠不會觸發，但它會佔住 sandbox 名額與使用者的耐心。動手做的情境 C 與 D 正好示範了兩者：C 被 SIGXCPU 終止，D 的 CPU 用量只有 0.01 秒，是被外部的逾時砍掉的。
>
> 反過來，只設 wall clock 也不夠。在多租戶的機器上，一段程式在 60 秒的 wall clock 內吃滿 8 顆核心，同機其他租戶就要承受 60 秒的效能下降；CPU 上限（以 cgroup 的 `cpu.max` 限速）才能保證它最多只用到分配的份額。此外 wall clock 要由 sandbox 外面的元件執行，因為 sandbox 裡的程式可以忽略或攔截自己收到的部分訊號，只有外部的強制銷毀是確定的。

> [!question]- Q3. 情境判斷：你在 production 的稽核紀錄看到，某個報表 session 在 30 秒內透過 egress proxy 對允許的內部 API 發了 4,000 個請求，每個都成功。這是問題嗎？你會怎麼處理？
> 是問題，而且是 allowlist 設計不完整的典型訊號。每個請求都「被允許」，代表 allowlist 只回答了「能不能連」，沒有回答「能連多少」。4,000 個請求可能是無害的 bug（模型寫了逐筆查詢的迴圈），也可能是被誘導的大量資料蒐集，兩者在 proxy 層看起來一樣。第一步是看這些請求的路徑與參數分布：如果是逐筆遍歷訂單編號，資料量很可能遠超過這個報表需要的範圍。
>
> 處理上分成短期與長期。短期先撤銷這個 session token，讓 sandbox 立即失去對外能力，並保留紀錄供調查。長期要在 proxy 加上每個 session 的速率與總量上限（請求數、回應 bytes），超過時拒絕並告警；同時檢討這個 API 是否該由 sandbox 直接呼叫，或改成 harness 先用批次查詢把資料準備好再掛進去。最後把這條 trajectory 變成回歸測試，確認新的上限能擋下同類行為，又不會誤擋正常的報表。

> [!question]- Q4. 為什麼「把短效 token 放進 sandbox」還不夠好？credential proxy 多出來的價值是什麼？
> 短效 token 縮短了外洩後的有效時間，但沒有改變「sandbox 裡的程式拿得到真憑證」這件事。在有效期間內，程式可以把 token 送到任何它連得到的地方，在 sandbox 外面以 token 的完整權限使用，你的 egress 控制與稽核都看不到這些使用。而且短效 token 的權限通常以「這個服務帳號能做什麼」為單位，很難細到「只能 GET 這兩個路徑」。
>
> credential proxy 改變了結構：sandbox 只拿到一個只在 proxy 上有意義的 session token，外洩到外面沒有任何用處；真憑證只在 proxy 轉送時於邊界外注入，每一次使用都經過 allowlist 比對，細到 host、方法與路徑，並留下稽核紀錄；session 結束就整個撤銷。它還能處理一個常被忽略的路徑：上游在回應裡回顯憑證，proxy 可以在回應送回 sandbox 前遮蔽。代價是多一個需要高可用的元件，以及對上游協定的理解（HTTP 容易，自訂協定較難）。

> [!question]- Q5. 程式找錯：下面的執行器有三個會在 production 出事的問題，請指出並說明後果。
> ```python
> def run(code):
>     env = dict(os.environ)
>     env.pop("ERP_TOKEN", None)
>     p = subprocess.run([sys.executable, "-c", code], env=env,
>                        capture_output=True, text=True, timeout=30)
>     return p.stdout
> ```
> 第一個問題是 env 的建立方式：從 `os.environ` 複製再刪掉已知的敏感變數，是 denylist 思維，永遠會漏掉某一個，例如新加的 `DB_PASSWORD`、雲端 SDK 的憑證變數或 CI 自動注入的 token。正確做法是 allowlist：從空 dict 開始，只放入 PATH、HOME 等明確需要的變數，也就是動手做的寫法。
>
> 第二個問題是 `capture_output=True` 搭配沒有上限的 stdout：程式印出幾 GB 的輸出時，父行程會把它全部收進記憶體，被撐爆的是 agent 服務本身；回傳的 stdout 也沒有截斷，會直接灌進 context。應該把輸出導到有大小上限的檔案，只讀前段並註明截斷。第三個問題是逾時處理：`subprocess.run` 的 timeout 只會砍掉直接的子行程，程式自己開出的孫行程會繼續跑；而且沒有任何 CPU、記憶體、檔案大小限制，也沒有獨立的工作目錄，程式會在 agent 服務的目錄裡讀寫。修法是設定 process group 並在逾時時整組結束、加上資源上限與獨立暫存目錄，最終仍要換成真正的 sandbox。

> [!question]- Q6. 用完的 sandbox，為什麼寧可銷毀也不要清理後重用？重用不是比較省嗎？
> 重用的前提是「清理得乾淨」，但這件事很難證明。一個執行過任意程式的環境，可能留下暫存檔、背景 process、修改過的設定檔、被替換的套件、快取裡的資料，甚至在記憶體或磁碟中殘留上一個任務的內容。清理腳本只能清掉你想得到的東西；任何一個漏網之魚，下一個任務就能看到上一個任務的資料，或執行上一個任務留下的檔案。在多租戶系統裡，這就是跨租戶資料外洩。
>
> 銷毀則讓保證變得簡單：每個任務都從同一份已知乾淨的映像開始。省錢的需求可以用其他方式滿足：warm pool 讓開機延遲不落在使用者身上，snapshot 讓開機本身變快，而不是讓舊機器活得更久。若真的因成本必須重用，至少要限制在同一租戶、同一使用者的任務之間，並把「清理後與初始映像一致」當成要驗證的條件，而不是假設。

> [!question]- Q7. 估算題：報表助理尖峰時每分鐘有 120 個新 session，每個 session 平均持有 sandbox 6 分鐘，開機需要 3 秒。同時存活的 sandbox 大約有幾台？warm pool 至少要保持幾台待命？
> 用 Little's law：同時存活數量 ≈ 到達率 × 平均停留時間。到達率是每分鐘 120 個，也就是每秒 2 個；平均持有 6 分鐘即 360 秒，所以同時被租用的 sandbox 約 2 × 360 ＝ 720 台。這個數字決定了底層機器的容量與 `max_total`，例如每台主機能跑 40 台 sandbox，就至少需要 18 台主機，再加上尖峰波動與故障備援。
>
> warm pool 的大小取決於「補開需要多久」。每取走一台就要補開一台，補開需要 3 秒，這 3 秒內平均又會來 2 × 3 ＝ 6 個新請求；所以待命數量至少要約 6 台，才能讓多數請求不必等開機。到達不是均勻的，實務上會依尖峰的突發程度加上緩衝，例如保持 10 到 15 台，再觀察 acquire 等待時間的 p99 調整。和 720 台的執行中數量相比，這個 pool 的閒置成本很小，所以通常值得；真正昂貴的是那 720 台的平均持有時間，縮短閒置 TTL 才是主要的成本手段。

> [!question]- Q8. 面試追問：如果要你設計一個給多個 agent 產品共用的 code execution 服務，你會提供什麼介面？哪些決定要由平台統一做、哪些讓各產品自己決定？
> 介面要讓呼叫端描述「需要什麼」，而不是「怎麼隔離」。核心是三個操作：建立 session（指定映像、資源等級、egress 政策名稱、需要的輸入檔、存活上限）、在 session 中執行程式（回傳 status、截斷後的輸出、產物清單、資源用量、各項限制是否生效）、結束 session。另外提供 snapshot 與還原，以及查詢稽核紀錄的介面。這和動手做的 `run_untrusted(code, limits) -> ExecResult` 是同一個形狀，只是加上 session 與政策的概念。
>
> 平台統一決定的是安全底線：隔離層級（多租戶一律 gVisor 或 microVM）、egress 預設拒絕且只能經過平台的 proxy、secret 一律不進 sandbox、用完即銷毀、稽核格式與保存期限。讓各產品決定的是在底線之內的參數：映像內容、資源等級、session 存活時間、egress allowlist 的具體內容（但要經過審查，因為 allowlist 等同授權）、pool 的預熱策略。面試時要特別說明：把安全底線放在平台，是因為每個產品團隊都有「先開放一點比較方便」的壓力，而底線一旦可以被單一產品調低，整個平台的保證就只剩最弱的那一個產品。

## 延伸閱讀

- Anthropic Engineering Blog〈How we contain Claude across products〉（2026）
- Anthropic Engineering Blog〈Code execution with MCP: building more efficient agents〉（2025）
- Agache et al.〈Firecracker: Lightweight Virtualization for Serverless Applications〉（NSDI 2020）
- gVisor 官方文件〈Security Model〉
- Linux Kernel 文件〈Control Group v2〉
- Simon Willison〈The lethal trifecta for AI agents: private data, untrusted content, and external communication〉（2025）
- Python 官方文件〈resource — Resource usage information〉與〈subprocess — Subprocess management〉
