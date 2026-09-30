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

然後在 `index.html` 對應的卡片裡加一個下載按鈕（照現有 `<a class="dl">` 的格式，
`href` 指向 `epub/<slug>.epub`，並把檔案大小寫進 `<span class="sz">`）。

`.venv-epub/` 已被 gitignore。

## 規範驗證

`check_epub.py` 是自己寫的快速檢查。正式驗證用 epubcheck：

```bash
brew install epubcheck
for f in epub/*.epub; do epubcheck "$f"; done
```

目前 17 本全部 **0 error、0 warning**。

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
