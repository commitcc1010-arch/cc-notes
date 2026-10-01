# EPUB 產生工具

把倉庫根目錄的每一本書（`*.html`，除了 `index.html`）轉成 EPUB 3，輸出到 `epub/`。
產出的 `.epub` 會一起 commit，因為 GitHub Pages 只能提供靜態檔案。

## 加了新書之後

```bash
python3 -m venv .venv-epub && ./.venv-epub/bin/pip install pygments markdown   # 只需第一次
./.venv-epub/bin/python tools/build_epub.py                            # 全部重建
./.venv-epub/bin/python tools/build_epub.py 新書.html                   # 只建一本
./.venv-epub/bin/python tools/check_epub.py                            # 結構自我檢查
```

`Coding Interview Patterns/` 是多份 Obsidian Markdown 組成的來源書。先合併成 HTML：

```bash
python3 tools/enrich_coding_interview_patterns.py
./.venv-epub/bin/python tools/build_coding_interview_patterns.py
./.venv-epub/bin/python tools/build_epub.py coding-interview-patterns-160.html
```

第一個指令會為 160 題重建可重複產生的視覺學習層與 640 組 Follow-up；
區塊有 marker，因此可安全重跑，不會重複插入。

`NGINX Source Code Journey/` 的內容由固定版本源碼課程資料產生。重建 Markdown、HTML
與 EPUB：

```bash
./.venv-epub/bin/python tools/build_nginx_source_journey.py
./.venv-epub/bin/python tools/build_epub.py nginx-source-code-journey.html
./.venv-epub/bin/python tools/check_epub.py epub/nginx-source-code-journey.epub
```

技術基準固定為 NGINX `release-1.31.5`；生成器會產出 1 篇零背景導讀、
48 個主章節、288 組 Follow-up Q&A、9 份附錄，以及可在 EPUB 中完整展開的
閱讀版本。每章的 beginner guide 由
`tools/nginx_source_journey_beginner_guides.py` 提供，包括全書定位、component
contract、完整 flow、source-reading 注意點與 implementation patterns。
`tools/nginx_source_journey_examples.py` 另外提供 48 組可執行 Python 概念模型、
Python 與 NGINX C 的逐項映射、source microscope，以及 48 個直接內嵌書中的官方
C 源碼視窗。讀者可以先跑懂簡化模型，再在同一頁對照真實 object、callback、
return code 與生命週期，不必先跳出書外。

`Software Engineering SRE AI/` 是《從 Commit 到可靠服務：Software Engineering
× SRE × AI》的可重建來源。重建 Markdown、HTML、執行內容品質閘門，再產生 EPUB：

```bash
./.venv-epub/bin/python tools/build_swe_sre_ai_book.py
PYTHONPATH=tools ./.venv-epub/bin/python tools/check_swe_sre_ai_book.py
./.venv-epub/bin/python tools/build_epub.py software-engineering-sre-ai.html
./.venv-epub/bin/python tools/check_epub.py epub/software-engineering-sre-ai.epub
epubcheck epub/software-engineering-sre-ai.epub
```

全書含 48 個主章節、195 張章內先備概念卡、48 段可解析的 Python
coding／實務例子、337 組 Follow-up Q&A、194 個動手驗證步驟，以及 7 份附錄。
每章固定包含 context、use case、完整 flow、心智模型、implementation walkthrough、
trade-offs、AI Shift、業界 practices 與 guardrails、domain expert lens。專用
`check_swe_sre_ai_book.py` 會逐章驗證這些欄位、可見正文深度、內部連結與離線
自包含性。EPUB builder 會把 337 個 `<details>` 全部改為常駐展開內容。

`CSAPP_系統思維學習手冊.html` 的深化內容由可重複執行的 enrichment layer
產生。它保留原始章節，再逐章加入 context、component contract、先備概念卡、
Big Picture、完整機制、可執行實驗、錯誤模型、來源與詳細問答：

```bash
./.venv-epub/bin/python tools/enrich_csapp_systems_book.py
PYTHONPATH=tools ./.venv-epub/bin/python tools/check_csapp_systems_book.py
./.venv-epub/bin/python tools/build_epub.py CSAPP_系統思維學習手冊.html
./.venv-epub/bin/python tools/check_epub.py epub/csapp-系統思維學習手冊.epub
epubcheck epub/csapp-系統思維學習手冊.epub
```

Enrichment markers 讓腳本可安全重跑而不重複插入。目前成品先提供一章只假設
資料結構與演算法背景的 Freshman Systems Primer，從 bit/byte、CPU、記憶體、
OS/kernel、system call，一路解釋到 executable/process、object format、
GDB/watchpoint、stack corruption 與 ASan。全書含 49 張零背景定義卡，Chapter
0–12 每章另有一條 DSA → Systems 橋梁；加上原有章內先備卡共 115 張。

其餘成品包括 13 個引導章、13 個實際執行驗證的 Python 概念模型、168 組折疊
問答、35 張架構／流程圖，以及完整 coverage、Labs、跨層診斷、公式工具、研究
方法與術語附錄。每個 Python 模型後都提供逐步 C／CPU／OS 映射、至少三個實際
應用與三個跨領域同型設計。品質閘門除了原有深度、問答、Python、圖解、連結與
離線資產檢查，現在也會強制驗證 Primer 位於所有章節之前、49 張基礎卡與 10 組
Primer 問答齊全、關鍵術語有具名解釋，且 13 章皆有背景橋梁；EPUB 會將全部
168 組答案轉為常駐展開內容。

`tools/nginx_source_journey_foundations.py` 提供 114 個零背景術語定義，依各章
需求在正文首次設計討論前放入至少 4 張「白話定義／具體例子／在 NGINX 中」
先備概念卡，目前合計 213 張；附錄 H 也會自動產生完整術語表。第 12 章另有
blocking server、select/poll、epoll interest set、keep-alive、WebSocket 與
能力邊界的完整 primer。每章的 Design Decision 區塊則明列外部壓力、use case、
NGINX 的選擇、state owner 與代價。

建立真實源碼視窗時，生成器依序讀取 `NGINX_SOURCE_ROOT` 指定的 checkout、
`/tmp/nginx-source-1.31.5.*` 的本機 checkout，最後才從固定 tag 的官方 raw
source 讀取。產出的 Markdown、HTML 與 EPUB 都已包含摘錄，不依賴讀者的網路或
本機 source tree。

然後在 `index.html` 對應的卡片裡加一個下載按鈕（照現有 `<a class="dl">` 的格式，
`href` 指向 `epub/<slug>.epub`，並把檔案大小寫進 `<span class="sz">`）。

`.venv-epub/` 已被 gitignore。

## 規範驗證

`check_epub.py` 是自己寫的快速檢查。正式驗證用 epubcheck：

```bash
brew install epubcheck
for f in epub/*.epub; do epubcheck "$f"; done
```

正式書架的 EPUB 清單與數量以 `index.html` 為準。

## 轉換時保留了什麼

- **每本書自己的 CSS** 原樣帶入，所以彩色區塊、表格、配色都跟網頁版一致。
- **程式碼上色**：網頁版靠 highlight.js 在瀏覽器端上色，但 EPUB 閱讀器不執行
  JavaScript，所以這裡改用 Pygments 在建置時就把 token 產生成靜態 `<span>`。
  已經有伺服器端 Pygments span 的區塊不會被重新處理。
- **ASCII 圖表**：`.diagram` / `.ascii-diagram` 與 `<pre>` 都強制 `white-space: pre-wrap`。
- **分章**：每章一個 XHTML 檔，因此閱讀器有真正的目錄與正常的翻頁。
  章節層級自動判斷（h1 夠多就用 h1，否則用 h2）。
- **書內連結**：`#id` 會被改寫成 `檔名.xhtml#id`；指向不存在目標的連結會被拿掉
  `href`（保留文字），因為懸空連結是 epubcheck 的 error。

## 已知限制

- **數學公式**：少數書用 MathJax 在瀏覽器端渲染 LaTeX。EPUB 裡會看到原始的
  `$...$` / `\(...\)`（各書 1–22 處）。
- **無語言標記的程式碼區塊**：來源沒有標語言時，用保守的特徵比對推測語言，
  推不出來就維持不上色，避免把 ASCII 圖表或輸出誤上色。
