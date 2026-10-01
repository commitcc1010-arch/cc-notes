# 模擬考撰寫任務說明

你要為《AWS Solutions Architect 雙證全攻略》撰寫一回完整的原創模擬考。

## 必讀

1. `tools/aws_architect_style_guide.md`：特別是第 5 節題目格式、官方 task ID 清單、第 7 節準確性重點、第 4 節禁止事項（不得收錄或改寫真實考題 dumps）。
2. `AWS Solutions Architect/Part 1 - Networking/05 - VPC 從零到可上線.md` 的「本章練習題」：題目與解析品質範本。
3. `tools/aws_architect_outline.md`：全書章節，解析中可寫「延伸閱讀：第 N 章」指回相關章節。

## 檔案格式

```markdown
---
title: SAA 模擬考 1
exam: SAA-C03
---

# SAA 模擬考 1

> [!abstract] 作答說明
> （題數、建議時間、及格參考、作答方式：先作答再展開答案、建議計時、錯題記錄方式）

## 題目

### 第 1 題｜SAA｜單選｜D1 跨帳號 S3 存取

（情境）

- A. …
- B. …
- C. …
- D. …

> [!answer]- 答案：B
> **A ✗** …
>
> **B ✓** …
>
> **C ✗** …
>
> **D ✗** …
>
> **考點**：SAA-1.1｜一句話考點｜延伸閱讀：第 13 章

（……依序到最後一題）

## 答案速查與 Domain 分析

（表格：題號｜答案｜Domain｜Task｜相關章節。之後附各 domain 題數與「錯題對應複習章節」建議。）
```

- 題目標題格式：`### 第 <n> 題｜<SAA 或 SAP>｜<單選 或 選兩項 或 選三項>｜D<1-4> <主題>`，n 從 1 連號。
- 單選 4 選項；選兩項 5 選項；選三項 6 選項。每個選項都要有 ✓／✗ 解析。
- 考點行只能列本考試的 task ID（SAA 考卷只用 SAA-x.x；SAP 考卷只用 SAP-x.x），且整回要涵蓋該考試**全部** task。
- Domain 題數：SAA（65 題）D1 20、D2 17、D3 15、D4 13；SAP（75 題）D1 20、D2 22、D3 19、D4 14。題目依 domain 混合排列（不要按 domain 分段），像真實考試。
- 多選題約 15–20%；SAP 可有 1–3 題選三項。單選答案 A／B／C／D 各約 25%。

## 品質要求

- **像真實考試**：每題有公司背景、現況、限制、一個最佳化目標（MOST cost-effective、LEAST operational overhead、MOST secure、highest availability…）。SAA 題 3–6 句；SAP 題 5–10 句、多重限制（跨帳號、既有系統、遷移時程、合規、預算），選項常是多步驟方案。
- 選項都要看似可行、長度相近；錯誤選項錯在一個關鍵點。避免一眼可刪的選項。
- 解析要教學：正確答案為何最好、每個錯誤選項錯在哪、什麼情況下它會變成正確答案。
- **不要使用 Wanderly**（那是章內練習用的公司）；使用各種產業的虛構公司，題與題之間情境不重複。
- 題目不能與書中章內練習題雷同；請先瀏覽 `AWS Solutions Architect/` 現有章節的練習題主題，避開相同情境。
- 技術必須正確；不確定的細節不要當成考點。

## 自我檢查

```bash
cd /Users/chouwleo/Projects/cc-notes
PYTHONPATH=tools python3 tools/check_aws_architect_book.py --mocks --partial
```

只看與你的檔案有關的 ERROR／WARN，修到 0（其他模擬考檔案可能正由別人撰寫，不要動它們）。

## 完成回報

簡短回報：檔案、題數、各 domain 題數、多選題數、答案分布、checker 結果、需人工複查的技術敘述。
