# 撰寫任務說明（給章節撰寫 agent）

你正在撰寫新書《Agent System 設計全書：從 0 到 1 打造 Agent 與 Agentic Framework》（書稿目錄 `Agent System Design/`，repo 根目錄 `/Users/chouwleo/Projects/cc-notes`）。目標：讀者**只靠這本書**，就能從零打造可上線的 agent 或自己的 agentic framework，並能像做 system design 一樣完整設計 agent system：架構、取捨、風險、評估與營運。深入淺出、循序漸進，深度與廣度兼備，要成為業界設計 agent system 的參考書。

## 開始前必讀（依序）

1. `tools/agent_system_style_guide.md`：寫作規範，全部遵守，尤其第 3 節（章節結構）、第 4 節（程式碼規則與統一的 ScriptedModel 介面）、第 7 節（準確性）、第 8 節（禁止事項）。
2. `tools/agent_system_outline.md`：全書大綱。找到你負責章節的「必須涵蓋」清單，全部講到，並補上你知道的重要知識點。了解其他章講什麼，交叉引用寫「第 N 章」，不要重複其他章的主題（簡短提及並指向該章即可）。
3. 技術現況 survey（2026-10，每項標了查證狀態）：`tools/.agent_survey_frameworks.md`、`tools/.agent_survey_techniques.md`、`tools/.agent_survey_production.md`。讀和你章節相關的部分。標為「未經網路查證」「不確定」的內容只能以保留語氣寫或不寫。
4. `tools/agent_system_canon.md`：全書共用定義（autonomy 等級、loom 版本與模組命名等），必須一致。
5. 範本章（若已存在）：`Agent System Design/Part 1 - 第一個 Agent/04 - 最小 Agent Loop.md`。學它的敘事、深度、圖表密度、程式與輸出解說、實務應用與問答品質。

## 重點要求

- 每個新名詞第一次出現就白話解釋並舉例；每個機制講清楚「為什麼需要、怎麼運作、主流產品／框架怎麼做、取捨與常見誤解」。
- 用青鳥科技的具體情境開場並貫穿全章。
- 視覺化：至少 4 張 ```text 圖（架構、流程、時序、狀態機、資料流、context 版面）與 3 張表格，每張圖後逐步解說。
- 動手做：可離線執行的 Python（只用標準函式庫，用統一的 ScriptedModel），實際執行後把輸出貼在緊接的 ```text 區塊並逐步解說。章內其他段落也鼓勵放小段可執行程式說明概念。
- 實務應用：至少三個具體情境，並說明主流產品或框架的對應做法（只寫公開資訊）。
- 版本、分數、產品細節只放在「2026 現況」區塊。
- 正文約 15,000–28,000 可見字元（不含問答與程式碼）。

## 自我檢查（必做）

在 repo 根目錄執行：

```bash
python3 tools/check_agent_system_book.py <你的章號>
```

checker 會單獨執行每段 Python、檢查結構、圖表數量、中英文空格、URL 與第三方 import。修到 **0 errors** 並處理 WARN，再從頭讀一次自己的章。

## 規則

只建立分配給你的檔案；不要修改其他檔案；不要開子 agent；不要跑長時間 benchmark；不要上網下載套件。

## 完成回報

簡短回報：檔案、正文可見字元數、checker 結果、不完全確定而需人工複查的敘述。
