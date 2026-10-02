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
× SRE × AI》的手寫 Markdown 來源（唯一內容來源；builder 只負責組裝）：

```bash
PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py        # 品質閘門（會執行每段 Python）
PYTHONPATH=tools ./.venv-epub/bin/python tools/build_swe_sre_ai_book.py
./.venv-epub/bin/python tools/build_epub.py software-engineering-sre-ai.html
./.venv-epub/bin/python tools/check_epub.py epub/software-engineering-sre-ai.epub
epubcheck epub/software-engineering-sre-ai.epub
```

全書 9 個 Part、48 章，以虛構線上市集 Harbor 從 8 人新創成長為 200 人組織的故事貫穿；
每章固定包含故事開場、循序的核心概念、可執行的 Python 模擬（附實際輸出）、
Trade-offs 與 Failure Modes、AI 時代的分工與 guardrails、專家視角、動手練習、
重點整理與 8 組延伸問答，另有 7 份附錄（讀書路線、原書概念對照、AI Autonomy
Maturity Model、工程模板、Reliability Math、術語表、延伸閱讀）。章節順序、檔名與
必須涵蓋的知識點定義在 `tools/swe_sre_ai_outline.md`；寫作規範與 Harbor 標準設定在
`tools/swe_sre_ai_style_guide.md`。`check_swe_sre_ai_book.py` 會檢查章節結構、
禁用的範本化套句、正文深度、問答數量與長度、跨章重複段落、未查證連結，並實際執行
每一段 Python。

`AWS Solutions Architect/` 是《AWS Solutions Architect 雙證全攻略》的手寫 Markdown 來源
（資料基準日 2026-10-01，以 SAA-C03 與 SAP-C02 exam guide 為準；SAP-C03 自 2026-10-27
開放報名，第 1 章與前言有說明）。Markdown 是唯一內容來源，builder 只負責組裝：

```bash
PYTHONPATH=tools python3 tools/check_aws_architect_book.py            # 品質閘門
PYTHONPATH=tools ./.venv-epub/bin/python tools/build_aws_architect_book.py
./.venv-epub/bin/python tools/build_epub.py aws-solutions-architect-saa-sap.html
./.venv-epub/bin/python tools/check_epub.py epub/aws-solutions-architect-saa-sap.epub
```

全書 12 個 Part、54 章（以虛構公司 Wanderly 從新創成長為跨國企業的故事貫穿），
5 份附錄（易混淆服務對照、關鍵數字與限制、題目關鍵字速查、術語表、讀書計畫與錯題本），
以及 5 回原創模擬考（SAA 3 回 × 65 題、SAP 2 回 × 75 題，依官方 domain 比重出題）。
章節順序、檔名與每章題數定義在 `tools/aws_architect_outline.md`；寫作與題目格式規範在
`tools/aws_architect_style_guide.md`（撰寫／審查 agent 的任務說明為同目錄的
`aws_architect_*_brief.md`）。

`check_aws_architect_book.py` 會解析每一題（題號、選項數、答案與 ✓／✗ 解析一致、官方
task ID）、檢查章節結構（本章地圖、節號、考試這樣考、重點整理、練習題）、禁用的範本化
套句、正文深度、跨章重複段落與題幹、未查證連結，以及模擬考的 domain 分布與 task 覆蓋。
HTML builder 會自動把「第 N 章」轉成書內連結，EPUB builder 會把所有答案 `<details>`
展開為常駐內容。

`CSAPP 系統思維學習手冊/` 是《CS:APP 系統思維學習手冊》的手寫 Markdown 來源（唯一內容
來源；builder 只負責組裝）：

```bash
python3 tools/check_csapp_systems_book.py            # 品質閘門（會編譯並執行每段 C／Python）
PYTHONPATH=tools ./.venv-epub/bin/python tools/build_csapp_systems_book.py
./.venv-epub/bin/python tools/build_epub.py CSAPP_系統思維學習手冊.html
./.venv-epub/bin/python tools/check_epub.py epub/csapp-系統思維學習手冊.epub
epubcheck epub/csapp-系統思維學習手冊.epub
```

全書 11 個 Part、34 章，對應 CS:APP 3e 全部 12 章，以一個用 C 寫的縮圖服務 `thumbd`
在 production 遇到的問題貫穿。每章固定包含故事開場、循序的核心概念與手算算例、
可執行的 C／Python（附實際輸出）、真實編譯器產生的 x86-64 組合語言、「在工作上怎麼用」、
常見錯誤與除錯表、動手練習、重點整理與 8 組延伸問答，並有大量 ASCII 圖與表格；另有
5 份附錄（公式與數字速查、工具指令速查、術語表、讀書路線、延伸閱讀）。章節與必須涵蓋的
知識點定義在 `tools/csapp_outline.md`，寫作規範在 `tools/csapp_style_guide.md`。
`check_csapp_systems_book.py` 會檢查章節結構、禁用的範本化套句、中英文之間的空格、
圖表數量、正文深度、問答，並實際編譯執行範例（標記 `// linux-only` 或 `// not-runnable`
的除外）。Labs 只提供學習指南，不含解答。

`Agent System Design/` 是《Agent System 設計全書：從 0 到 1 打造 Agent 與 Agentic Framework》的手寫
Markdown 來源：

```bash
python3 tools/check_agent_system_book.py              # 品質閘門（會單獨執行每段 Python）
(cd "Agent System Design/code" && python3 -m unittest discover -s tests)   # 隨書 loom 套件
PYTHONPATH=tools ./.venv-epub/bin/python tools/build_agent_system_book.py
./.venv-epub/bin/python tools/build_epub.py agent-system-design.html
./.venv-epub/bin/python tools/check_epub.py epub/agent-system-design.epub
epubcheck epub/agent-system-design.epub
```

全書 11 個 Part、46 章與 6 份附錄，以青鳥科技從一個 100 行的 agent loop 長成三個 agent 與自家
framework `loom` 貫穿。每章固定包含故事開場、核心概念、可離線執行的 Python（統一用
`ScriptedModel` 假模型，只用標準函式庫）與實際輸出、實務應用、設計檢查清單、常見錯誤與除錯、
重點整理、8 組延伸問答與延伸閱讀；版本與產品細節集中在標明「2026 現況」的區塊。章節與必須涵蓋的
知識點定義在 `tools/agent_system_outline.md`，寫作規範在 `tools/agent_system_style_guide.md`，
全書共用定義在 `tools/agent_system_canon.md`，撰寫 agent 的任務說明在
`tools/agent_system_agent_brief.md`。隨書程式碼 `Agent System Design/code/` 是第 45 章組裝的
`loom` v1.0（標準函式庫、附 unittest）。`check_agent_system_book.py` 會檢查章節結構、圖表數量、
正文深度、問答、中英文空格、URL、第三方 import、性別代名詞與非包容性用語，並執行每段 Python。

`Coding Interview Pattern Playbook/` 是《Coding Interview Pattern Playbook》的手寫 Markdown
來源（與舊書 `Coding Interview Patterns/` 互相獨立，舊書的工具與輸出不受影響）：

```bash
python3 tools/check_coding_interview_book.py          # 品質閘門（會執行每段 Python）
PYTHONPATH=tools ./.venv-epub/bin/python tools/build_coding_interview_playbook.py
./.venv-epub/bin/python tools/build_epub.py coding-interview-pattern-playbook.html
./.venv-epub/bin/python tools/check_epub.py epub/coding-interview-pattern-playbook.epub
epubcheck epub/coding-interview-pattern-playbook.epub
```

全書 8 個 Part、31 章，以 Google L5 等級的 coding interview 為標準：3 章面試方法、
26 個 pattern 章（每章 5 道核心題與 5 道難題，共 260 題，只用 Python）、2 章衝刺與
模擬面試，另有 4 份附錄（Python 工具箱、複雜度速查、全題索引、21 天讀書計畫）。
每題都有完整題目重述、從暴力解出發的思路、文字視覺化、附 assert 的可執行解法、
複雜度與邊界，以及至少 3 個附答案的 follow-up；難題另有三段漸進提示、詳解與心得。
章節與題目定義在 `tools/coding_interview_outline.md`，寫作規範在
`tools/coding_interview_style_guide.md`，撰寫 agent 的任務說明在
`tools/coding_interview_agent_brief.md`。`check_coding_interview_book.py` 會檢查題號與
大綱一致、每題的小節順序、follow-up 與提示數量、禁用套句、中英文空格，並執行每段
Python（第一行為 `# not-runnable` 的除外）。四本手寫書共用的 HTML 模板與 Markdown
工具在 `tools/book_template.py`。

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
