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
