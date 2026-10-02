# 《CS:APP 系統思維學習手冊》寫作規範

所有章節與附錄都必須遵守本規範。`tools/check_csapp_systems_book.py` 會自動檢查可機器驗證的部分。

## 1. 讀者與目標

- **讀者**：會寫程式（Python、Java、JavaScript 等高階語言），大學修過或沒修過計算機組織，但從來沒有真正理解「程式在機器上到底怎麼跑」的工程師與學生。C 只學過一點，沒用過 gdb。
- **目標**：讀完後能理解 CS:APP 3e 全部 12 章的核心觀念，並能把它們用在工作上：看懂 segfault 與 core dump、分析效能瓶頸、處理 link error、寫正確的 I/O 與網路程式、找出 race 與 memory leak。
- **自給自足**：不需要另外買書或查資料就能理解。原書與官方文件只是延伸閱讀；不能用「詳見原書」取代解釋。
- **不是原書摘要**：用自己的話、新的例子、逐步推導把概念講透，並補上原書出版後的業界現況（ARM64、sanitizer、現代 allocator、epoll、Spectre 等）。
- 引用本書其他章節寫「第 N 章」。

## 2. 語言與格式

- 繁體中文（台灣用語：記憶體、位元組、暫存器、程式、檔案、設定）。業界通用的英文術語保留英文（page table、cache miss、system call、file descriptor），第一次出現時附中文解釋。
- **中英文之間一定加半形空格**：「把 virtual address 轉成 physical address」，不能寫成「把virtual address轉成physical address」。舊版最大的可讀性問題就是中英文黏在一起。
- 中文句子用全形標點。段落 3–6 句，一段一件事。主體是有因果的敘事文字；條列、表格、圖是輔助。
- 新名詞第一次出現時用粗體並立即白話定義，緊接一個具體例子。
- **視覺化是必要的**：每章至少 3 個 ```` ```text ```` 圖（流程、記憶體配置、位元布局、資料結構、時間軸等），至少 3 張 Markdown 表格（比較、對照、算例、查表）。每張圖後要用文字逐步解說。
- 位元布局、記憶體位址、stack frame 這類內容一定要畫圖，例如：

```text
 高位址
 ┌──────────────────┐
 │  caller 的 frame │
 ├──────────────────┤ ← call 之前的 %rsp
 │  return address  │
 ├──────────────────┤
 │  saved %rbx      │
 │  local 變數      │
 └──────────────────┘ ← 目前的 %rsp
 低位址
```

## 3. 章節固定結構

```markdown
---
chapter: 23
title: 位址轉譯
part: 7
---

# 第 23 章　位址轉譯：Page Table、TLB 與 Page Fault

> [!abstract] 本章地圖
> **核心問題**：（一句話）
>
> **你會學到**：
> - （3–6 點，讀完能「做到」什麼）
>
> **前置知識**：第 N 章（…）
>
> **對應 CS:APP 3e**：第 9 章 9.1–9.6 節

## 23.1 故事：（thumbd 遇到的問題）
## 23.2 ～ 23.k（核心概念，由淺入深，節與節之間有承接句）
## 23.x 動手做：（主題）
## 23.x 在工作上怎麼用
## 23.x 常見錯誤與除錯
## 23.x 動手練習
## 本章重點整理
## 延伸問答
## 延伸閱讀
```

- 節號格式「## 23.3 標題」。最後三個 H2 依序固定為「本章重點整理」「延伸問答」「延伸閱讀」。
- 「動手做」「在工作上怎麼用」「常見錯誤與除錯」「動手練習」四節必須存在（標題要以這些字開頭，冒號後可加副題）。
- **故事**：用 `thumbd` 或拾光相簿的具體問題開場，說清楚「不懂本章的東西，會卡在哪裡」。
- **核心概念**：每個概念依序講：為什麼需要 → 怎麼運作（原理、推導、算例）→ 在真實系統長什麼樣（C、組合語言、Linux）→ 常見誤解。數值類主題（整數、浮點、位址轉譯、cache）一定要有完整手算算例。
- **動手做**：至少一段可執行程式（C 或 Python 3），緊接 ```` ```text ```` 區塊貼上**實際執行**的輸出，再逐步解說。
- **在工作上怎麼用**：具體的工作情境（後端、SRE、效能、安全、嵌入式），附工具指令、判斷流程或檢查清單。這是本書和教科書最大的差別，要寫得具體。
- **常見錯誤與除錯**：表格列出 4 項以上常見錯誤：症狀｜原因｜怎麼確認｜怎麼修。
- **動手練習**：4–6 個讀者可以實際做的練習，至少一個延伸本章程式，至少一個手算題（附答案或驗證方法）。
- **本章重點整理**：8–15 條完整句子。
- **延伸問答**：依大綱數量（8 題），格式見第 5 節。
- 可用 callout：`> [!note]`、`> [!tip]`、`> [!warning] 常見誤解`、`> [!example] 例子`、`> [!abstract] 本章地圖`（只用於開頭）、`> [!question]- Qn. …`（只用於延伸問答）。
- 字數：正文（不含延伸問答與程式碼）約 14,000–25,000 可見字元。

## 4. 程式碼規則（checker 會執行）

- ```` ```c ````：含 `int main` 的區塊，checker 會用 `cc -std=c17 -O1 -Wall -Wextra -o` 編譯並執行（10 秒逾時，回傳值必須是 0）。不含 `main` 的片段只做顯示。執行環境是 macOS（arm64）與 Linux 都應能編譯的標準 C 與 POSIX。
  - 只能在 Linux 上編譯的程式（例如用 `epoll`、`/proc`、`<sys/sysinfo.h>`），第一行寫 `// linux-only`，checker 會略過。
  - 刻意示範錯誤、會當機或無法編譯的程式，第一行寫 `// not-runnable`。
  - 示範 undefined behavior 的程式要明說「結果依編譯器而定」，並貼上你實際得到的輸出與編譯器版本。
- ```` ```python ````：checker 會執行（同上規則，用 `# not-runnable` 標記不執行）。
- ```` ```asm ````：x86-64 AT&T 語法，只顯示。**必須是真實編譯器產生的**：用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - file.c` 產生，可刪去無關的 directive，並在區塊前寫出產生它的指令與最佳化等級。不要憑記憶手寫組合語言。本機沒有 Linux 的系統標頭檔，所以要產生組合語言的程式碼片段最好不 include 系統標頭（自行宣告用到的函式，例如 `char *strcpy(char *, const char *);`）；若一定要 include，先在本機用 `clang -E` 展開成 `.i` 再以 `-target x86_64-linux-gnu` 編譯，並在文中說明。
- ```` ```bash ````／```` ```text ````：顯示用。終端機輸出若不是實際執行得到（例如 Linux 專屬工具），要標明「示意輸出」。
- 程式要短（一般 20–80 行）、有意義的變數名稱、必要的註解（說「為什麼」）。

## 5. 延伸問答格式（checker 會解析）

```markdown
## 延伸問答

> [!question]- Q1. 為什麼 TLB miss 不等於 page fault？
> 第一段答案……
>
> 第二段答案……
```

- 題號從 Q1 連續；數量依大綱。
- 答案至少 120 可見字元，要解釋判斷依據。
- 題目類型多樣：概念辨析、手算、情境判斷（「你在 production 看到…」）、面試題、程式找錯。

## 6. 貫穿案例：拾光相簿與 thumbd

拾光相簿是一個線上相簿服務。後端的 `thumbd` 是用 C 寫的縮圖服務：

```text
使用者 ─HTTP→ nginx ─HTTP→ thumbd（C，thread pool）
                             ├─ 解析 HTTP request（第 28–29 章）
                             ├─ 讀原圖檔（mmap／read，第 24、27 章）
                             ├─ 解碼（libjpeg／libpng，動態連結，第 19 章）
                             ├─ 縮放、旋轉（像素矩陣運算，第 14、17 章）
                             ├─ 快取縮圖（malloc／free，第 25–26 章）
                             └─ 回傳結果；用 fork/exec 呼叫外部工具處理少數格式（第 21 章）
```

人物：
- **小安**：剛入職的初階後端工程師，熟悉 Python 與 Java，C 只在大學學過。
- **老周**：資深系統工程師，`thumbd` 的原作者之一，小安的 mentor。
- 可以有配角（例如 SRE 阿哲、產品經理 Lisa），但要寫明角色。人物一律不用性別代名詞（他／她），用名字或「對方」。

每章故事盡量是 `thumbd` 真實可能遇到的問題（bug、效能、當機、資源洩漏、部署問題），讓讀者理解「這些底層知識在工作上什麼時候會用到」。

## 7. 準確性重點

- x86-64 System V ABI：前六個整數參數 %rdi、%rsi、%rdx、%rcx、%r8、%r9；回傳值 %rax；callee-saved：%rbx、%rbp、%r12–%r15；stack 16-byte 對齊（call 之前）；red zone 128 bytes。
- 二補數 w 位元：TMin = −2^(w−1)，TMax = 2^(w−1) − 1，UMax = 2^w − 1。C 中 signed overflow 是 undefined behavior；unsigned overflow 定義為模 2^w。
- IEEE 754 double：1 sign、11 exponent（bias 1023）、52 fraction；single：1、8（bias 127）、23。
- Cache 位址切分：block offset b = log2(B)，set index s = log2(S)，tag = m − s − b。
- 4 KiB page → page offset 12 bits。
- fork 回傳：子行程得到 0，父行程得到子行程 PID，失敗回傳 −1。
- `read`／`write` 可能回傳少於要求的位元組數（short count），網路與 pipe 尤其常見。
- signal 不排隊（同一種 pending signal 只記一次）；handler 只能呼叫 async-signal-safe 函式。
- 延遲數量級（只給量級）：L1 約 1 ns、L2 約數 ns、DRAM 約 100 ns、SSD 隨機讀約數十到上百 µs、HDD seek 約數 ms。

## 8. 禁止事項

- 禁止範本化套句，尤其舊版用語：「CORE COMPLETION LAYER」「DSA → SYSTEMS BRIDGE」「進入細節前的三個定位點」「輸入與壓力」「內部責任」「讀完輸出」「術語卡住？回到零背景」「WHY IT MATTERS」。
- 禁止中英文黏在一起（中文與英文單字之間沒有空格）。
- 禁止空泛句、捏造數據、虛構 URL（只能用 `tools/csapp_reference_urls.txt` 中的連結，或完全確定存在的官方頁面）。
- 禁止收錄 CS:APP Labs 的解答。
- 不要大段照抄原書文字或原書範例程式；用自己的話與新例子。
