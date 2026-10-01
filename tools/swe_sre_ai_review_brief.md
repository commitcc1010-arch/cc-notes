# 技術審查任務說明（給審查 agent）

你是《從 Commit 到可靠服務：Software Engineering × SRE × AI》的技術審稿人兼編輯。指定章節已由作者完成並通過格式 checker；你的工作是確保**技術與引用正確、程式與輸出一致、讀起來通順易懂、和其他章節一致**，並直接修改檔案。

## 必讀

1. `tools/swe_sre_ai_style_guide.md`（尤其第 4、6、7 節）
2. `tools/swe_sre_ai_outline.md`（確認「必須涵蓋」都有講到）
3. `tools/.swe_review_flags.md`：作者自己標記「不確定」的敘述，找到你負責章節的部分逐條查證。

## 查證方式

- 能查就查：用 ToolSearch 載入 WebFetch（`select:WebFetch`），讀原書線上版（abseil.io/resources/swe-book、sre.google/sre-book、sre.google/workbook）、dora.dev、opentelemetry.io、slsa.dev、官方文件。
- 查不到又不確定的：改成保守寫法或刪除。不確定的研究數字、引言、出處一律不要保留為確定事實。對原書的引用若無法確認原文，改成「原書的觀點是……」這類轉述，不要加引號當成原句。

## 審查清單

1. **技術與引用正確性**：逐段閱讀，找出錯誤、過時、誤導、張冠李戴的敘述。
2. **程式**：執行每段 Python，確認輸出與文中 ```` ```text ```` 區塊一致；確認程式邏輯正確、解說與程式相符、模擬參數若是假設有標明。
3. **延伸問答**：答案是否正確、有深度、和正文一致。
4. **可讀性**：零經驗讀者是否看得懂？新名詞是否在第一次出現時解釋？段落是否過長？有沒有範本化或空泛句子？順手改善。
5. **一致性**：Harbor 的人物、公司規模時間線（style guide 第 6 節）、數字與設定是否和其他已存在章節一致；交叉引用「第 N 章」是否指向正確內容。人物與泛稱避免性別代名詞（用名字、「對方」「他們」）。
6. 不要大幅改結構或刪減有價值內容；以修正與補強為主。

## 修改後

```bash
cd /Users/chouwleo/Projects/cc-notes
PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py <你的章號>
```

必須維持 0 errors。只修改你負責的章節檔案。

## 完成回報

簡短列出：每章修正的技術／引用錯誤（原→改）、程式問題、查證後確認無誤的 flag、改成保守寫法的項目、發現的跨章不一致（若涉及其他章，只回報不修改）。
