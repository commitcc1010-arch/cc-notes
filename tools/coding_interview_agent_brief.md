# 撰寫任務說明（給章節撰寫 agent）

你正在撰寫新書《Coding Interview Pattern Playbook》（書稿目錄 `Coding Interview Pattern Playbook/`）。目標：讓讀者**只靠這本書**，就能準備到 Google L5（以及其他大廠同等級）coding interview 的水準：在 2–3 週內複習完大廠 coding interview 的 26 個 pattern，每個 pattern 5 道核心題、5 道難題，真正理解每題為什麼這樣解，面對沒看過的題目也能判斷 pattern。

書架上已有一本舊書《Coding Interview Patterns》（目錄 `Coding Interview Patterns/`），**不要修改它**。它的內容是範本產生的：每題的推導與 follow-up 都是同一段套句換題名，不要沿用它的結構與文字；只能拿它的題目程式當參考。

## 開始前必讀

1. `tools/coding_interview_style_guide.md`：寫作規範，全部遵守（尤其第 3 節固定結構、第 5 節禁止事項）。
2. `tools/coding_interview_outline.md`：全書大綱，找到你負責的章與指定題目（題號與順序必須一致），也了解其他章，交叉引用寫「第 N 章」。
3. 範本章（若已存在）：`Coding Interview Pattern Playbook/Part 1 - 線性結構/08 - Binary Search.md`。學它的深度、視覺化、follow-up 的具體程度與心得寫法。

## 要求重點

- 每題完整重述題目（用自己的話）、至少兩個範例，讀者不必查 LeetCode。
- 思路從暴力解講起，說清楚瓶頸與關鍵觀察；每題至少一個 ```text 視覺化逐步走過範例。
- 解法是可執行的 Python，附至少 3 個 assert（含邊界），最後 `print("all tests passed")`。**自己先執行確認通過。**
- Follow-up 至少 3 個，必須針對本題、是面試官真的會問的變形，答案具體（做法＋複雜度，必要時附程式）。
- 難題：三段漸進提示、完整詳解（為什麼直覺做法不行、突破點、正確性）、心得。
- Pattern 歸納：所有變形、辨識方式、上下限、和其他 pattern 的關係。
- 正確性第一：複雜度、邊界、最佳解都要正確。

## 自我檢查（必做）

在 repo 根目錄執行 `python3 tools/check_coding_interview_book.py <你的章號>`。checker 會執行每段 Python。修到 0 errors，並處理 WARN（題目內容偏短代表講得不夠完整）。

## 規則

只建立分配給你的檔案；不要開子 agent；不要修改其他任何檔案。

## 完成回報

簡短回報：檔案、題數、checker 結果、不完全確定的地方。
