# 《從 Commit 到可靠服務：Software Engineering × SRE × AI》寫作規範

所有章節與附錄都必須遵守本規範。`tools/check_swe_sre_ai_book.py` 會自動檢查可機器驗證的部分。

## 1. 讀者與目標

- **讀者**：會寫程式、有 0–3 年經驗的工程師。知道 Git、HTTP、資料庫是什麼，但沒有帶過團隊、沒有值過班、沒讀過《Software Engineering at Google》與《Site Reliability Engineering》。
- **目標**：讀完能理解大型組織如何讓軟體長期可修改、在 production 可靠運作，並知道 AI（coding agent、AI 維運、AI 產品）在這條路上改變了什麼、哪些責任不能交給 AI。
- **自給自足**：不需要讀原書或跳出去查資料就能理解。原書與官方文件只是延伸閱讀；不能用「詳見原書」取代解釋。
- **不是原書摘要**：要用自己的話、具體例子與推導把概念講透，並補上原書出版後的業界演進（DORA、OpenTelemetry、SLSA、platform engineering、AI-assisted development 等）。
- 引用本書其他章節寫「第 N 章」。

## 2. 語言與格式

- 繁體中文（台灣用語）。業界通用的英文術語保留英文（code review、canary、error budget、on-call），第一次出現時附中文解釋。不要為了用英文而用英文。
- 中英文之間加半形空格；中文句子用全形標點。
- 段落 3–6 句，一段一件事。主體是有因果的敘事文字；條列、表格、圖是輔助。
- 新名詞第一次出現時用粗體並立即白話定義，最好緊接一個具體例子。
- 圖用 ```` ```text ```` 的 ASCII 圖，圖後要用文字逐步解說。
- 數學或公式用 ```` ```text ```` 區塊，並附算例。

## 3. 章節固定結構

```markdown
---
chapter: 32
title: SLI、SLO、SLA 與 Error Budget
part: 5
---

# 第 32 章　SLI、SLO、SLA 與 Error Budget

> [!abstract] 本章地圖
> **核心問題**：（一句話，本章要回答的問題）
>
> **你會學到**：
> - （3–6 點，讀完能「做到」什麼）
>
> **前置知識**：第 N 章（…）
>
> **對應原書**：SRE 第 3、4 章；SRE Workbook 第 2 章

## 32.1 故事：（Harbor 遇到的問題）
## 32.2 ～ 32.k（核心概念，由淺入深，節與節之間有承接句）
## 32.x 動手寫：（主題）
## 32.x Trade-offs 與 Failure Modes
## 32.x AI 時代：什麼變了？
## 32.x 專家怎麼想
## 32.x 動手練習
## 本章重點整理
## 延伸問答
## 延伸閱讀
```

- 節號格式「## 32.3 標題」。最後三個 H2 依序固定為「本章重點整理」「延伸問答」「延伸閱讀」。
- 「動手寫」「Trade-offs 與 Failure Modes」「AI 時代：什麼變了？」「專家怎麼想」「動手練習」五節必須存在（標題要以這些字開頭，冒號後可加副題）。
- **故事**：用 Harbor 案例或具體場景開場，說清楚「沒有本章的東西會怎樣」。
- **核心概念**：每個概念依序講：為什麼需要 → 怎麼運作（原理、推導）→ 實務上怎麼做（工具、流程、範例）→ 常見誤解。至少一張 ASCII 圖。
- **動手寫**：至少一段可執行的 Python（只用標準函式庫，Python 3.11+），模擬本章機制（例如 error budget 計算、burn rate alert、retry 放大、consistent hashing、flaky 偵測）。程式碼要能直接執行並產生輸出；緊接 ```` ```text ```` 區塊貼上**實際執行**的輸出；再逐步解說程式與它對應的真實系統。若某段程式只是片段、刻意不可執行，第一行寫 `# not-runnable`。
- **Trade-offs 與 Failure Modes**：用表格或段落說明「什麼情況下這個做法會失敗、會被取代」，至少 4 項，每項有具體情境。
- **AI 時代：什麼變了？**：具體說明 AI（coding agent、AI 維運 agent、AI 產品）如何改變本章主題；附一張表「適合交給 AI 的工作｜必須保留的人類判斷與 guardrails」；避免空泛口號，寫出可執行的做法。AI 產品、模型變化快，描述原則與模式，不寫特定模型版本或未查證的產品功能。
- **專家怎麼想**：資深工程師／SRE 的判斷方式、經驗法則、會問的問題（3–6 點，帶理由）。
- **動手練習**：4–6 個讀者可以實際做的練習，至少一個延伸本章程式碼。
- **本章重點整理**：8–15 條完整句子。
- **延伸問答**：依大綱數量（8 題），格式見第 5 節。
- **延伸閱讀**：只列已查證連結（見第 4 節），加一句說明讀什麼。
- 可用 callout：`> [!note]`、`> [!tip]`、`> [!warning] 常見誤解`、`> [!example] 例子`、`> [!ai] AI 提醒`、`> [!abstract] 本章地圖`（只用於開頭）、`> [!question]- Qn. …`（只用於延伸問答）。
- 字數：正文（不含延伸問答與程式碼）約 14,000–25,000 可見字元。深度優先，但不灌水。

## 4. 禁止事項

- 禁止範本化套句，尤其舊版常見句：「先沿箭頭讀一次」「不要把上面的 trade-off 背成口號」「本章位於 Part」「你現在位於哪裡」「開始前：四個一定要先懂的概念」「不是工具清單，而是判斷邊界」「交付能力」「問題壓力」。
- 禁止空泛句（「要兼顧品質與速度」這類沒有具體內容的話）。
- 禁止捏造數據、研究結果、引言或產品功能。引用研究（DORA、Project Aristotle 等）時只寫你有把握的結論；不確定就不寫數字。
- 禁止虛構 URL：只能用 `tools/swe_sre_reference_urls.txt` 中的連結，或你完全確定存在的官方頁面（sre.google、abseil.io/resources/swe-book、dora.dev、opentelemetry.io、slsa.dev 等的根頁）。寧可不放。
- 不要大段照抄原書文字；用自己的話解釋並舉新例子。

## 5. 延伸問答格式（checker 會解析）

```markdown
## 延伸問答

> [!question]- Q1. 為什麼 99.99% 的 SLO 不一定比 99.9% 好？
> 第一段答案……
>
> 第二段答案……

> [!question]- Q2. ……
> ……
```

- 題號連續，從 Q1 開始；數量依大綱。
- 答案 3–8 句以上（至少 120 可見字元），要解釋判斷依據，不是一句提示。
- 題目類型要多樣：概念辨析、情境判斷（「如果你是值班者……」）、計算、反例、面試題、AI 情境。

## 6. 貫穿案例：Harbor 港灣市集

Harbor 是一個台灣的線上市集。服務：web／app、search、cart、checkout、payments（串接外部金流）、inventory、notification、推薦。兩種 AI：工程團隊的 AI coding agent，以及面向客戶的 AI 客服 agent（能查訂單、發起退款）。人物：初階工程師阿凱、tech lead 美華、SRE 志明、產品經理 Lisa、工程經理 Kevin。人物代名詞一律避免性別化（用名字或「他們」）。

時間線：Part 0–1 是 8 人新創；Part 2–3 成長到 40 人、多個團隊；Part 4–5 建立 CI/CD 與 SRE；Part 6–7 面對大流量與重大事故（雙十一）；Part 8 是 200 人組織，全面導入 AI agent。每章故事盡量和 Harbor 有關，但可以加入其他具體情境。

### Harbor 標準設定（全書以此為準）

年份對應：第 1 年 = 2023、第 2 年 = 2024、第 3 年 = 2025、第 4 年 = 2026（雙十一 2026-11-11）、第 5 年 = 2027。能用相對年份就用相對年份。

| 時間 | 規模 | 對應 Part | 狀態 |
|---|---|---|---|
| 第 1 年～第 2 年初 | 全公司 8 人（5 位工程師），一個團隊 | Part 0–1 | 單體服務、手動部署 |
| 第 2 年～第 3 年初 | 約 40–45 人，五個團隊 | Part 2–4 | code review、style guide、design doc；逐步建立測試、build、CI/CD |
| 第 3 年 | 約 60 人 | Part 5 | Kevin 成立 4 人 SRE 團隊（志明帶領）；導入 SLO |
| 第 4 年 | 約 120 人 | Part 6–7 | 雙十一大流量與重大事故；SRE 團隊約 6 人 |
| 第 5 年 | 約 200 人 | Part 8 | 全面導入 AI agent；platform engineering；SRE 團隊約 8 人；Kevin 升任工程副總 |

五個團隊（第 2 年起）：

- **checkout**：cart、checkout、inventory。小芸、阿哲在此。
- **payments**：金流串接、退款、對帳。美華最初在此（後來成為 tech lead）；小林在此。
- **search**：搜尋與推薦。柏翰、家豪在此。
- **seller**：賣家後台、商品上架、通知。阿凱（8 人時期什麼都做，第 2 年起在此）、思妤（負責通知）在此。
- **platform**：CI/CD、基礎設施。志明最初在此，第 3 年起帶領 SRE 團隊。

第 5 年成立「客服平台」小組，由阿凱帶領，負責 AI 客服 agent。其他配角可以出現，但要寫明所屬團隊。

AI 客服的能力時間線：Part 0–2 只能查訂單；Part 3 起可以送出退款申請，由客服人員核准（工程團隊建立了退款工具 API）；第 5 年（Part 8）起可在額度內直接執行退款，經由 deterministic 的 refund-gateway。

Repository（第 2 年起，第 19 章定案）：混合 polyrepo，一個主要 monolith repo 加 12 個小 repo（共 13 個；含行動 app、幾個獨立服務、共用函式庫 `harbor-common`）。`checkout/` 目錄的 owner 是 `checkout-team`。

機器規模（checkout 服務）：第 3 年平時約 24 台；第 4 年平時約 50 台，雙十一尖峰擴展到約 150 台。其他服務依比例描述，避免各章數字互相矛盾。

流量（checkout）：第 3 年平日約每分鐘 600 筆 checkout 嘗試（30 天約 2,600 萬次）；第 4 年平日 checkout API 約 2,400 RPS、約每分鐘 1,800 筆訂單；雙十一午夜尖峰為平日 6 倍（約 14,400 RPS、每分鐘 10,800 筆訂單）。金流商合約 300 → 600 TPS。

第 4 年雙十一事件線（第 36–41 章定案）：T−14 天容量計畫凍結、T−3 天預先擴容、T+3 天縮回；雙十一前兩週 20:00 預購事故（第 38 章）；11/10 22:00（午夜尖峰前）流量 4 倍、22:03 inventory DB failover、22:06 全站不可用、22:40 恢復（第 39 章，INC-1110）；11/11 00:00 起付款重複扣款事故 INC-1111（第 44–45 章；v2.31 於 11/10 18:00 部署）；11/12 02:00 重複撥款（第 41 章）。第 40 章的雙主事故發生在同年三月週年慶。美華的角色：第 2 年在 payments，之後成為 checkout 的 tech lead／owner。

## 7. 準確性重點

- 《Software Engineering at Google》核心句：「Software engineering is programming integrated over time」；Hyrum's Law；Beyoncé Rule（「If you liked it, you should have put a CI test on it」）；Chesterton's fence 等用語要正確。
- SRE：toil 的定義（manual、repetitive、automatable、tactical、no enduring value、scales linearly）；SRE 50% 上限；four golden signals（latency、traffic、errors、saturation）。
- 九的換算（30 天）：99% ≈ 7.2 小時、99.9% ≈ 43.2 分鐘、99.95% ≈ 21.6 分鐘、99.99% ≈ 4.32 分鐘。
- Multi-window multi-burn-rate（SRE Workbook 建議，30 天 SLO）：2% budget／1 小時 → burn rate 14.4（短窗 5 分鐘）；5%／6 小時 → 6（短窗 30 分鐘）；10%／3 天 → 1（ticket）。
- DORA 四大指標：deployment frequency、lead time for changes、change failure rate、failed deployment recovery time（舊稱 MTTR／time to restore）；2024 年起另有 rework rate。
- Quorum：2f+1 個節點可容忍 f 個故障。
- Little's Law：L = λW。
