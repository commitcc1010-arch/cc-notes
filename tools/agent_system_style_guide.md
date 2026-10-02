# 《Agent System 設計全書》寫作規範

所有章節與附錄都必須遵守本規範。`tools/check_agent_system_book.py` 會自動檢查可機器驗證的部分。

## 1. 讀者與目標

- **讀者**：會寫 Python 的軟體工程師（後端、全端、資料、SRE），用過 ChatGPT 或 LLM API，但沒有從零設計過 agent system。也包含想系統化整理知識的 AI 工程師與技術主管。
- **目標**：讀者**只靠這本書**就能從零打造一個可上線的 agent，或設計自己的 agentic framework，並能在 system design 討論中完整說明架構、取捨、風險與營運。深度與廣度兼備，循序漸進：每章都建立在前面章節之上。
- **自給自足**：每個概念第一次出現就白話解釋並舉例；不能用「請參考官方文件」取代解釋。官方文件只是延伸閱讀。
- **以原理為主、現況為輔**：正文講不容易過時的原理與設計取捨。版本號、價格、benchmark 分數、產品細節一律放在標題含「2026 現況」的小節或 `> [!note] 2026 現況` callout 中，並寫明「截至 2026 年 10 月」。
- 引用本書其他章節寫「第 N 章」。

## 2. 語言與格式

- 繁體中文（台灣用語：程式、檔案、設定、資料、記憶體、預設）。業界通用的英文術語保留英文（agent、tool、context window、prompt caching、sandbox、trace），第一次出現時附中文解釋。
- **中英文之間一定加半形空格**；中文句子用全形標點。
- 段落 3–6 句，一段一件事。主體是有因果的敘事文字（「因為……所以……」）；條列、表格、圖是輔助。
- 新名詞第一次出現用粗體並立即白話定義，緊接一個具體例子。
- **視覺化是必要的**：每章至少 4 個 ````text```` 圖（架構圖、流程圖、時序圖、狀態機、資料流、context 版面配置、trajectory 追蹤），至少 3 張 Markdown 表格（比較、取捨、決策、對照）。每張圖後要用文字逐步解說。例如：

```text
 使用者 ──► Agent Runner ──► Model（決定下一步）
              ▲    │
              │    ▼ tool_use
              │  Tool Dispatcher ──► get_order / refund / search_kb
              │    │
              └────┘ tool_result 回填 messages，直到 end_turn 或超出預算
```

## 3. 章節固定結構

```markdown
---
chapter: 4
title: 100 行的最小 Agent Loop
part: 1
---

# 第 4 章　100 行的最小 Agent Loop

> [!abstract] 本章地圖
> **核心問題**：（一句話）
>
> **你會學到**：
> - （3–6 點，讀完能「做到」什麼）
>
> **前置知識**：第 N 章（…）

## 4.1 故事：（青鳥科技遇到的問題）
## 4.2 ～ 4.k（核心概念，由淺入深，節與節之間有承接句）
## 4.x 動手做：（主題）
## 4.x 實務應用
## 4.x 設計檢查清單
## 4.x 常見錯誤與除錯
## 本章重點整理
## 延伸問答
## 延伸閱讀
```

- 節號格式「## 4.3 標題」，連續編號。最後三個 H2 依序固定為「本章重點整理」「延伸問答」「延伸閱讀」。
- 「動手做」「實務應用」「設計檢查清單」「常見錯誤與除錯」四節必須存在（標題以這些字開頭，冒號後可加副題）。第一節必須是「故事」。
- **故事**：用青鳥科技的具體情境開場，說清楚「不懂本章的東西，會卡在哪裡」，並在整章中持續使用。
- **核心概念**：每個概念依序講：為什麼需要 → 怎麼運作（原理、流程圖、逐步追蹤）→ 在真實系統長什麼樣（主流產品／框架怎麼做）→ 取捨與常見誤解。
- **動手做**：至少一段可執行的 Python，跑完印出結果；緊接 ````text```` 區塊貼上**實際執行**的輸出，再逐步解說。
- **實務應用**：至少三個具體的應用情境（不同產業或產品類型），說明本章的技術在其中怎麼用、要注意什麼；並說明市面上成功產品或主流框架的對應做法（只寫公開資訊）。
- **設計檢查清單**：設計或審查時要逐項確認的問題，至少 8 項，每項是可以回答「是／否」或「選哪個」的具體問題。
- **常見錯誤與除錯**：表格列出 5 項以上：症狀｜原因｜怎麼確認｜怎麼修。
- **本章重點整理**：8–15 條完整句子。
- **延伸問答**：8 題，格式見第 5 節。
- **延伸閱讀**：3–8 項，只寫名稱與出處（例如「Anthropic Engineering Blog〈Building effective agents〉（2024）」），**不放 URL**。
- 可用 callout：`> [!note]`、`> [!tip]`、`> [!warning] 常見誤解`、`> [!example] 例子`、`> [!note] 2026 現況`、`> [!abstract] 本章地圖`（只用於開頭）、`> [!question]- Qn. …`（只用於延伸問答）。
- 字數：正文（不含延伸問答與程式碼）約 15,000–28,000 可見字元。

案例章（第 39–41 章）與設計演練章（第 42–44 章）同樣遵守此結構；「動手做」可以是用 Python 模擬該架構的關鍵機制（例如 sandbox pool 排程、compaction 策略、research fan-out）。設計演練章的核心概念部分依 system design interview 流程展開：需求釐清 → 估算 → 高階架構 → 深入元件 → 擴展與取捨 → 面試官追問。

## 4. 程式碼規則（checker 會執行）

- 只用 Python 3.11+ 與**標準函式庫**。不能 import 第三方套件（openai、anthropic、langgraph…），因為讀者要能離線執行，checker 也會執行每一段。
- 每段 ````python```` 程式都會被**單獨執行**（10 秒逾時），所以每段要自給自足：需要的類別要在同一段裡定義。最後用 `assert` 驗證行為，並印出結果。
- 需要模型時用 **ScriptedModel**（依劇本回應的假模型）。全書統一使用下面這份核心介面，直接複製到需要的程式段落開頭（可以省略用不到的部分，但名稱與欄位不要改）：

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


class ScriptedModel:
    """依劇本回應的假模型。劇本的每一步是 ModelResponse，或「收到 messages 後回傳 ModelResponse」的函式。"""

    def __init__(self, script: list[ModelResponse | Callable[[list[dict]], ModelResponse]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse:
        self.calls.append(json.loads(json.dumps(messages)))
        if not self.script:
            raise RuntimeError("劇本已用完：agent 呼叫模型的次數比預期多")
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def call(name: str, call_id: str = "c1", **args: Any) -> ModelResponse:
    """劇本小工具：產生一個「呼叫 name 工具」的回應。"""
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)
```

- 訊息格式全書統一：`{"role": "user", "content": "..."}`、`{"role": "assistant", "content": "...", "tool_calls": [ToolCall, ...]}`（tool_calls 存成 dict：`{"id", "name", "args"}`）、`{"role": "tool", "tool_call_id": "c1", "name": "get_order", "content": "..."}`。
- 示範如何接真實 API（Anthropic Messages、OpenAI Responses、Gemini）或第三方框架的程式，第一行寫 `# not-runnable`，checker 會略過；這類程式要依官方 SDK 的真實介面撰寫，不確定的參數名稱不要寫，並在前文註明「依 2026-10 的 SDK 介面，請以官方文件為準」。
- 需要時間、網路、隨機性的程式要可重現：用固定 seed、模擬時鐘、假的 HTTP 層。不要真的連網，也不要 sleep 超過 0.5 秒。
- 程式長度一般 30–150 行；有意義的命名；註解說「為什麼」。
- ````text```` 中的執行輸出必須是實際執行得到的。

## 5. 延伸問答格式（checker 會解析）

```markdown
## 延伸問答

> [!question]- Q1. 為什麼 agent 的停止條件不能只靠模型說「完成了」？
> 第一段答案……
>
> 第二段答案……
```

- 題號 Q1–Q8 連續。答案至少 150 可見字元，要解釋判斷依據，不能只給結論。
- 題型多樣：概念辨析、設計取捨（「A 和 B 怎麼選」）、情境判斷（「你在 production 看到…」）、system design 面試追問、程式找錯、估算。

## 6. 貫穿案例：青鳥科技與 loom

青鳥科技（Bluebird）做電商營運 SaaS，客戶是數千家中小型網店。全書的發展：

```text
 Part 0–1  客服 agent v1：查訂單、查物流、退款（單一 agent、少量 tools）
 Part 2    加上知識庫檢索、長對話 compaction、使用者 memory
 Part 3    透過 MCP 接上 ERP 與物流商；加入 code execution 做報表
 Part 4    內部 coding agent 與營運 research agent；multi-agent 與人工審核
 Part 5    把三個 agent 共用的部分抽成自家 framework「loom」
 Part 6–7  建立 eval、tracing、安全審查與治理流程
 Part 8–10 平台化、多租戶上線、設計演練與 capstone
```

人物：
- **Iris**：剛轉職的 AI 工程師，後端背景，第一次負責 agent 專案。
- **老陳**：staff engineer，經歷過多次分散式系統上線，Iris 的 mentor。
- **阿哲**：產品經理，關心使用者體驗、成本與上線時程。
- **Maya**：資安工程師，負責 threat modeling 與審查。
- 人物一律不用性別代名詞（他／她），用名字或「對方」。

## 7. 準確性重點

- 只寫公開、可查證的資訊；不確定的產品細節不寫或明說「公開資料未說明」。不捏造數字、benchmark 分數、客戶名稱或引言。
- 技術現況參考 `tools/.agent_survey_frameworks.md`、`tools/.agent_survey_techniques.md`、`tools/.agent_survey_production.md`（2026-10 的 survey，每項標了查證狀態）。標為「未經網路查證」或「不確定」的內容，正文只能以保留語氣寫或不寫；具體版本號與分數只放在「2026 現況」區塊。
- 不要寫特定模型的確切名稱與分數作為正文論據；用「前沿模型」「推理模型」「小型快速模型」等描述，具體名稱只出現在「2026 現況」區塊。
- 安全章節只談成因、偵測與防禦設計，不提供攻擊操作步驟或可直接使用的攻擊 payload。

## 8. 禁止事項

- 禁止範本化套句與空泛句（「在這個快速變化的時代」「總而言之，agent 非常強大」）。
- 禁止中英文黏在一起。
- 禁止在正文放 URL（程式碼區塊中作為範例資料的網址可以使用，例如 `https://api.example.com`；只用 example.com 等保留網域）。
- 禁止捏造數據、引言、產品功能。
- 禁止使用非包容性用語（master/slave、whitelist/blacklist），改用 primary/replica、allowlist/denylist。
- 禁止對人物使用性別代名詞（她、他）；用名字、「對方」或「這位顧客」。checker 會報錯（「其他」「他們」「他人」不受影響）。
