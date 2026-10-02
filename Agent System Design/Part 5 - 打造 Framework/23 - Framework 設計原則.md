---
chapter: 23
title: Framework 設計原則與核心抽象
part: 5
---

# 第 23 章　Framework 設計原則與核心抽象

> [!abstract] 本章地圖
> **核心問題**：當三個 agent 各自複製了一份 loop，要抽出哪些共用的抽象、抽到什麼程度，才能讓 framework 帶來一致性，而不是多一層讓人看不懂的包裝？
>
> **你會學到**：
> - 判斷該自己做 framework、直接採用現成 SDK，還是只寫一層薄薄的內部函式庫
> - 用「最少抽象原則」篩選抽象：每個抽象都要說得出它保護了什麼不變式
> - 定義 loom v0.5 的八個核心抽象：Agent、Tool、Runner、Session、Event、Handoff、Guardrail、Hook／middleware，並說清楚誰持有狀態
> - 設計 middleware 鏈與 lifecycle hooks，理解洋蔥模型的順序如何決定語意
> - 畫出 loom v0.5 的架構圖與模組依賴圖，把前面各章的模組放到正確的擴充點上
> - 制定 API 設計與向後相容規則：公開介面、deprecation、事件 schema 版本與 upcaster
>
> **前置知識**：第 4 章（`loom` v0.1 的 loop、dispatch 與停止條件）、第 5 章（tool 的副作用分級與 idempotency）、第 9 章與第 12 章（context 與 memory 模組）、第 13 章（tool registry）、第 19 章（graph 與 checkpoint）、第 20 章（handoff）、第 22 章（事件日誌與 durable execution）

## 23.1 故事：三份 loop，三種 guardrail

青鳥科技的三個 agent 都上線了。客服 agent 從第 4 章的 100 行 loop 長出來，一路加上第 5 章的副作用分級、第 9 章的 context builder、第 12 章的 memory 與第 21 章的核准流程；內部 coding agent 由平台組維護，跑在第 17 章的 sandbox 裡，用第 13 章的 registry 管理幾十個開發工具；營運 research agent 則是資料組的作品，為了撐過部署與 rate limit，改寫成第 22 章的事件日誌 runner。三個 agent 的 loop 都源自同一份 `loom` v0.1，但半年下來，三份程式已經長成三種樣子。

這件事在一個月內咬了青鳥三次。第一次，Maya 做季度審查時問：「三個 agent 的 guardrail 分別在哪一行執行？」客服 agent 的身分檢查寫在 dispatch 裡；coding agent 的檢查寫成 sandbox 的設定；research agent 的版本在改寫成事件日誌時，把那段檢查連同舊的 dispatch 一起刪掉了，沒有人發現，因為所有測試都只測「正常路徑」。第二次，coding agent 在凌晨連續收到 API 400：第 4 章修過的「tool call 沒有對應結果」錯誤又出現了，因為平台組的分支在那次修正之前就分出去了。第三次，阿哲要求所有 agent 都套上「每個租戶每月的 token 預算」，三個團隊各寫了一份，月底帳單上三個 agent 對同一個租戶算出了三個不同的用量，原因是有人把 cache 命中的 token 算進去，有人沒有。

老陳在白板上畫了三條從同一點分岔的線。「這三個事故有一個共同點：同一件事在三個地方各做一次，而且做法不一樣。」Iris 說那就把三份 loop 合成一份。老陳搖頭：「合成一份只解決了今天。你要決定的是：哪些東西是**每一個** agent 都該有、而且行為必須一致的；哪些東西是每個 agent 都不一樣、應該留給它自己的。前者放進核心，後者要有地方可以插進來。這就是 framework 和『共用的程式碼』的差別。」

```text
                      loom v0.1（第 4 章，100 行）
                               │
          ┌────────────────────┼─────────────────────┐
          ▼                    ▼                     ▼
   客服 agent 的 loop     coding agent 的 loop    research agent 的 loop
   ＋effect／intent       ＋registry、sandbox      ＋事件日誌、重播
   ＋context、memory      ＋自己的預算計算         ＋自己的預算計算
   ＋核准、身分檢查       ＋配對修正之前分出去     ＋身分檢查在改寫時遺失
          │                    │                     │
          ▼                    ▼                     ▼
   用量算法 A             用量算法 B（含 cache）  用量算法 C
   guardrail 在 dispatch  guardrail 在 sandbox    guardrail：無
```

這張圖是 framework 存在的理由。三條分支各自加上了合理的功能，但每一條都在某個「本該一致」的地方走偏了：預算的算法、guardrail 的位置、配對不變式的修正。注意圖上沒有一個分支是「錯的設計」，問題在於沒有一個地方規定「這些事只能有一種做法」。framework 要做的，就是把這些必須一致的東西收進核心，並給必須不同的東西留下明確的擴充點。

這一章是 Part 5 的第一章，和第 24、25 章一起把 `loom` 重構成 v0.5。本章負責核心抽象、擴充點與 API 規則；第 24 章把 Runner 換成支援串流、並行與取消的 `loom.runtime`；第 25 章把模型呼叫抽成 provider adapter 與 router，也就是 `loom.models`。本章只定義它們要實作的介面，細節留給那兩章。最後在「動手做」，我們會實作 v0.5 的核心介面與 middleware 鏈，把日誌、預算與 guardrail 用同一種擴充機制掛上去，再用 ScriptedModel 跑一遍青鳥客服的分流、handoff 與攔截情境。

## 23.2 要不要自己做 framework

先回答一個常被跳過的問題：真的需要自己做嗎？**framework**（框架）和 **library**（函式庫）的分界在於「誰呼叫誰」。library 是你的程式去呼叫它，例如你呼叫 `json.dumps`；framework 則是它呼叫你的程式，你把 tool 函式、guardrail 規則交給它，由它決定什麼時候執行。這種**控制反轉**（inversion of control）讓 framework 能保證一致性，例如保證每個 tool 呼叫前都過 guardrail；代價是你的程式要照它的規矩寫，出問題時也要先理解它的執行順序才能除錯。

市面上已經有很多成熟的 agent SDK（第 26 章會完整比較），它們都內建了 loop、tool 定義、handoff 與 tracing。自己做 framework 的理由必須比「我想要」更具體。常見的好理由有三種：第一，你有多個 agent，而且需要某些行為在所有 agent 上一致，例如稽核、預算、租戶隔離；第二，你的限制是現成 SDK 不支援或很難支援的，例如必須接自家的事件日誌、必須同時支援多家模型、必須在受監管環境中控制每一個網路呼叫；第三，agent 是你的核心產品，你需要掌握每一行行為，才能在模型升級時快速調整 harness。

```text
 有幾個 agent 會共用這套東西？
   │
   ├─ 1 個 ─────────────────────────────► 直接用現成 SDK，或保持一個乾淨的 loop
   │
   └─ 2 個以上
        │
        需要「全部一致」的行為（稽核、預算、guardrail、租戶隔離）？
        │
        ├─ 否 ──────────────────────────► 各自用 SDK；共用 tools 與 prompt 模組即可
        │
        └─ 是
             │
             現成 SDK 的擴充點（hooks、middleware、session 介面）能滿足嗎？
             │
             ├─ 能 ─────────────────────► 薄的內部層：SDK ＋ 自家 middleware 套件
             │
             └─ 不能（自家事件日誌、多 provider、監管限制、agent 是核心產品）
                  │
                  └────────────────────► 自建核心，介面對齊主流 SDK 以利遷移
```

這張決策圖由上往下看。第一關是數量：只有一個 agent 時，抽象沒有第二個使用者可以驗證，做出來的往往是「為這一個 agent 量身訂做、卻假裝很通用」的程式。第二關問的是一致性需求，這是 framework 真正的價值所在；如果每個 agent 都可以各做各的，共用幾個 tool 模組就夠了。第三關最容易被忽略：主流 SDK 大多提供 hooks、middleware、session 等擴充點，很多「必須自建」的理由其實是沒讀完文件。只有在擴充點也撐不住時，才走到最下面的自建；即使自建，介面也應該對齊主流 SDK 的概念，讓團隊之後要換或要混用時成本可控。

| 選項 | 適合的情況 | 主要成本 | 主要風險 |
|---|---|---|---|
| 直接用現成 SDK | 單一 agent、團隊小、要快速驗證 | 學習 SDK 的概念與預設值 | 預設值不適合產品；版本升級的 breaking change |
| SDK＋內部 middleware 套件 | 多個 agent 要共用稽核、預算、guardrail | 維護一份中介層並追 SDK 版本 | SDK 擴充點改版時要跟著改 |
| 自建核心（像 loom） | 有特殊限制，或 agent 是核心產品 | 長期維護、文件、測試、onboarding | 抽象設計錯誤後很難回頭；變成只有作者懂的框架 |
| 不做任何共用 | 原型期、每個 agent 都還在劇烈變化 | 幾乎沒有 | 一致性問題會在上線後一次爆發（23.1 節） |

青鳥選擇自建 `loom`，理由落在第三列：三個 agent 已經存在、第 22 章的事件日誌是自家設計、模型要同時接兩家供應商，而且客服 agent 是公司的核心產品。但老陳定了一條規矩：**loom 的每個概念都要能對應到至少一個主流 SDK 的概念**。這是給自己留退路：哪天改用現成 SDK，概念一一對上，遷移只是改寫介面。

> [!warning] 常見誤解
> 「自己寫 framework 才能完全掌控。」掌控不是來自「程式是自己寫的」，而是來自「知道每一條邊在做什麼」。用現成 SDK 但讀懂它的 loop、預設值與擴充點，掌控度往往比一份沒有文件、只有作者懂的自建框架更高。自建的真正理由是一致性需求加上特殊限制，不是掌控感。

## 23.3 最少抽象原則：每個抽象都要付得起房租

決定自建之後，最大的誘惑是把所有東西都變成抽象。Iris 的第一版設計草稿有十九個類別：Agent、Tool、Memory、Planner、Crew、Task、Workflow、Retriever、Context、Prompt……每一個看起來都合理。老陳只問了一個問題：「這十九個裡面，哪幾個拿掉之後，會有不變式沒人保護？」

這就是本書採用的**最少抽象原則**（principle of least abstraction）：一個概念要成為 framework 的核心抽象，必須同時通過三個檢驗。第一，**它保護了一個不變式**：拿掉它，某個必須成立的性質就沒人保證。例如 Runner 保護「每個 tool call 都有對應結果」，拿掉 Runner，這件事就散落到每個呼叫端。第二，**它至少有兩種真實的實作或用法**：Session 有記憶體版、資料庫版與第 22 章的事件日誌版；只有一種實作的「介面」通常只是多了一層間接。第三，**它的概念在主流 SDK 與模型供應商之間是穩定的**：tool call 的概念三家 API 都有，可以放心抽象；某一家獨有的功能，放進 adapter 就好。

抽象是有房租的。每多一個公開類別，使用者就要多學一個概念，文件要多寫一章，向後相容要多守一份契約，除錯時 stack trace 也多一層。更隱晦的成本是**洩漏的抽象**（leaky abstraction）：抽象想隱藏的細節，出問題時還是會冒出來。例如把 memory 做成自動決定記什麼的神奇抽象，agent 記錯東西時使用者無從下手，最後還是要打開框架原始碼。

| 候選抽象 | 保護的不變式 | 兩種以上實作？ | 跨 SDK 穩定？ | loom v0.5 的決定 |
|---|---|---|---|---|
| Runner | tool call 配對、停止條件、事件順序 | 同步參考版、第 24 章 async 版 | 是 | 核心 |
| Session | 對話狀態只有一個權威來源 | 記憶體、資料庫、事件日誌 | 是 | 核心 |
| Guardrail | 政策在固定位置、一定會被執行 | 規則、分類器、policy engine | 是 | 核心（資料）＋middleware（機制） |
| Memory | 無獨立的不變式 | 檔案、向量、圖 | 否，各家差異大 | 不進核心：做成 tool＋context provider（第 12 章） |
| Planner | 無：規劃是模型的行為 | — | 否 | 不進核心：用 prompt 或第 8 章的 pattern |
| Crew／Team | 與 handoff、agents-as-tools 重疊 | — | 否 | 不進核心：用 Handoff 與 `loom.agents` 組合 |
| Workflow／Graph | 確定性的流程與 checkpoint | 第 18、19 章 | 是，但屬於另一層 | 不進核心：`loom.workflows`、`loom.graph` 建在 Runner 之上 |

這張表是篩選的結果。前三列通過了全部三個檢驗。Memory 是最常見的爭議：它很重要，但它沒有自己的不變式；第 12 章已經示範，memory 就是一個 tool（讓模型讀寫）加上一個 context provider（在組裝 context 時放進半穩定層），用現有的兩個擴充點就能表達。Planner 與 Crew 則是把「模型的行為」或「組合方式」誤當成「framework 的元件」，做成抽象只會限制模型。Workflow 與 Graph 是真正有價值的抽象，但它們屬於 orchestration 層，應該建在核心之上，而不是塞進核心。

最少抽象原則還有一個推論：**能用組合表達的，就不要新增概念**。agents-as-tools（把一個 agent 包成另一個 agent 的 tool）不需要新類別，只要一個把 Runner 包成 Tool 的函式；平行執行三個 subagent 也不需要新類別，用第 18 章的 parallelization 寫幾行程式就好。老陳的說法是：「核心要小到可以在一個下午讀完。你沒辦法在一個下午讀完的東西，出事的時候也沒辦法在一個下午修好。」

## 23.4 八個核心抽象與它們的關係

通過篩選的核心抽象有八個。先用一句話定義每一個，再看它們之間的關係。**Agent** 是一份宣告式的設定：名字、指令、可用的 tools、可以交接的對象、要套用的 guardrails。**Tool** 是模型可以請求執行的一個能力，帶著 schema、副作用等級與實作函式。**Runner** 是執行引擎：拿著 Agent 與使用者輸入跑 loop，負責所有不變式。**Session** 是一段對話的狀態存放處，讓第二輪對話接得上第一輪。**Event** 是 run 過程中發生的每一件事的不可變紀錄，是唯一的事實來源。**Handoff** 是把控制權交給另一個 Agent 的宣告。**Guardrail** 是一條在固定位置執行的政策檢查。**Hook／middleware** 是讓外部程式在 lifecycle 的固定位置觀察或改變行為的擴充點。

```text
          宣告（不可變的資料）                      執行與狀態
 ┌──────────────────────────────────┐
 │ Agent                            │    run(agent, input, session, deps)
 │  ├─ instructions                 │ ──────────────────────────────► Runner
 │  ├─ tools: Tool …  ──────────────┼──► 由 Runner 經 middleware 執行   │
 │  ├─ handoffs: Handoff ─► Agent   │                                  │ 呼叫
 │  └─ guardrails: Guardrail …      │                                  ▼
 └──────────────────────────────────┘                        Model（介面；第 25 章）
                                                                     │
   Middleware／Hook ◄──── on_event、wrap_model、wrap_tool ───────────┤
   （日誌、預算、guardrail、核准、tracing）                            │ 每一件事
                                                                     ▼
                                                             Event（不可變）
                                                                     │ append
                                                                     ▼
                                                     Session（load／append；可換實作）
                                                                     │ 投影
                                                                     ▼
                                       messages（給模型）／trace（給人）／帳單（給財務）
```

這張圖分成左右兩半，這個分法本身就是最重要的設計決定。左邊是**宣告**：Agent、Tool、Handoff、Guardrail 都是不可變的資料，描述「這個 agent 是什麼、能做什麼、受什麼約束」，不持有任何連線或對話狀態。右邊是**執行與狀態**：Runner 讀宣告、呼叫模型、執行 tool；每一件發生的事變成 Event，寫進 Session；messages、trace、帳單都是從事件**投影**（projection，從同一份資料算出不同的視圖）出來的。Middleware 夾在中間，在固定的位置觀察或介入執行。

為什麼要這樣分？因為宣告與狀態的生命週期完全不同。一個 Agent 設定在 process 啟動時建立，會被成千上萬個並行的對話共用；一個 Session 只屬於一段對話，可能活好幾天。把兩者混在同一個物件裡（像 v0.1 的 `Agent` 同時持有 model 與 messages），共用時就會互相污染，也無法把設定放進版本控制、把狀態放進資料庫。這也是主流 SDK 普遍收斂的形態：Agent 是設定，Runner 是執行者，Session 是狀態。

| 抽象 | 是什麼 | 可變嗎 | 誰建立、活多久 | 保護的不變式 | 來自哪一章 |
|---|---|---|---|---|---|
| Agent | 宣告式設定 | 否 | 啟動時建立，所有對話共用 | 設定可版本控制、可安全共用 | 第 4、6 章 |
| Tool | 能力＋schema＋副作用等級 | 否 | 啟動時建立 | 未標註即 destructive；schema 不含 harness 注入的欄位 | 第 4、5、7、13 章 |
| Runner | 執行引擎 | 無狀態 | 啟動時建立 | tool 配對、停止條件、事件順序 | 第 4 章；第 24 章換成 async |
| Session | 對話狀態 | 只能追加 | 每段對話一個，可活數天 | 單一權威來源、只在尾端追加 | 第 10、22 章 |
| Event | 一件事的紀錄 | 否 | 每一步產生，永久保存 | 有序、可重播、有 schema 版本 | 第 10、22 章 |
| Handoff | 交接宣告 | 否 | 隨 Agent 宣告 | 任何時刻只有一個 active agent | 第 20 章 |
| Guardrail | 政策檢查 | 否 | 隨 Agent 或 Runner 宣告 | 檢查在固定位置、不可被跳過 | 第 21、32 章 |
| Hook／middleware | 擴充點 | 各自管理 | 隨 Runner 設定 | 擴充只能從公開的點進入 | 本章 |

這張表的「可變嗎」一欄值得反覆看：八個抽象裡只有 Session 會變，而且只能追加。所以設定可以放心共用、事件可以放心重播。最後一欄則說明 v0.5 沒有發明新東西，只是把前面各章驗證過的機制放到該在的位置。

## 23.5 Agent 與 Tool：宣告式的設定

**宣告式**（declarative）的意思是描述「要什麼」，而不是寫出「怎麼做」的步驟。`Agent("refund", "你負責退款。", tools=(get_order, refund))` 只說「有一個叫 refund 的 agent，它能用這兩個 tool」，沒有說要怎麼跑 loop。好處是設定可以被檢查、比較與序列化：審查時可以直接列出每個 agent 能用哪些 destructive tool，canary 部署時可以用一行 `replace()` 產生只改了指令的新版本，而不必複製整個類別。

Tool 的設計延續第 5 章與第 13 章的規則。每個 Tool 帶著 `effect`（read、write、destructive）、`intent_fields`（定義同一個業務意圖的參數，harness 依此推導 idempotency key）與 `code_callable`（能不能從 code-as-action 的程式中呼叫）。v0.5 把這些欄位從「某個 agent 的 dispatch 裡的慣例」提升成 Tool 的正式欄位，讓所有 agent 用同一套規則。有兩個預設值是刻意選的：`effect` 預設為 destructive，因為忘記標註時應該選最保守的值；`code_callable` 只有 read 才開放，有副作用的 tool 必須走一般 tool call 與核准流程。

另一個 v0.5 的改變是**依賴注入**（dependency injection）：tool 函式的第一個參數是 `deps`，由 Runner 在執行時傳入，內容是目前的使用者、租戶、資料庫連線等。模型看不到 `deps`，也填不了它。例如退款 tool 需要知道「目前登入的是誰」，這個資訊絕對不能來自模型產生的參數，否則一則 prompt injection 就能讓模型替別人退款。Pydantic AI 的 `RunContext[Deps]` 是同樣的想法：把「誰在操作、用什麼資源」和「模型決定的參數」放在兩條不同的路上。

下面的程式用一個裝飾器把函式變成 Tool，並示範 Agent 的不可變性。

```python
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, dataclass, replace
from typing import Any, Callable, get_type_hints

JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]
    effect: str = "destructive"            # 忘了標註時選最保守的值，而不是最方便的值
    intent_fields: tuple[str, ...] = ()
    code_callable: bool = False


def tool(effect: str = "destructive", intent_fields: tuple[str, ...] = ()) -> Callable[[Callable], Tool]:
    """把函式變成 Tool。第一個參數 deps 由 Runner 注入，不會出現在模型看得到的 schema 裡。"""
    def wrap(fn: Callable) -> Tool:
        hints = get_type_hints(fn)
        params = list(inspect.signature(fn).parameters.values())[1:]      # 跳過 deps
        props = {p.name: {"type": JSON_TYPES[hints[p.name]]} for p in params}
        required = [p.name for p in params if p.default is inspect.Parameter.empty]
        return Tool(fn.__name__, (inspect.getdoc(fn) or "").splitlines()[0],
                    {"type": "object", "properties": props, "required": required}, fn,
                    effect=effect, intent_fields=intent_fields,
                    code_callable=(effect == "read"))                         # 有副作用一律不開放給 code-as-action
    return wrap


@dataclass(frozen=True)
class Agent:
    name: str
    instructions: str
    tools: tuple[Tool, ...] = ()
    max_steps: int = 8


@tool(effect="read")
def get_order(deps: dict, order_id: str) -> dict:
    """查詢訂單狀態與金額"""
    return {"order_id": order_id, "status": "shipped"}


@tool(effect="destructive", intent_fields=("order_id", "amount"))
def refund(deps: dict, order_id: str, amount: int, reason: str = "") -> str:
    """未出貨訂單直接退款"""
    return "ok"


@tool()
def send_coupon(deps: dict, user_id: str) -> str:
    """發優惠券給使用者"""
    return "ok"


for t in (get_order, refund, send_coupon):
    print(f"{t.name:<12} effect={t.effect:<12} code_callable={t.code_callable!s:<5} "
          f"required={t.parameters['required']}")

base = Agent("refund", "你負責退款。", tools=(get_order, refund))
try:
    base.max_steps = 99                    # 共用的設定物件被某個請求偷偷改掉，是最難查的 bug 之一
except FrozenInstanceError:
    print("Agent 是不可變的：要改設定就用 replace() 產生新物件")
canary = replace(base, instructions="你負責退款。退款前先複述金額。")
print("base   →", base.instructions)
print("canary →", canary.instructions, "｜共用同一組 tools：", canary.tools is base.tools)

assert send_coupon.effect == "destructive" and not send_coupon.code_callable
assert "deps" not in refund.parameters["properties"] and refund.parameters["required"] == ["order_id", "amount"]
assert base.instructions == "你負責退款。"
```

```text
get_order    effect=read         code_callable=True  required=['order_id']
refund       effect=destructive  code_callable=False required=['order_id', 'amount']
send_coupon  effect=destructive  code_callable=False required=['user_id']
Agent 是不可變的：要改設定就用 replace() 產生新物件
base   → 你負責退款。
canary → 你負責退款。退款前先複述金額。 ｜共用同一組 tools： True
```

前三行是三個 tool 的宣告結果。`get_order` 標了 read，所以 `code_callable` 自動為 True；`refund` 標了 destructive，不開放給程式呼叫；`send_coupon` 什麼都沒標，於是落到預設的 destructive，這正是「未標註一律當 destructive」的效果：寫 tool 的人忘了，系統選擇保守，而不是選擇方便。三個 tool 的 `required` 都不含 `deps`，證明注入的參數不會出現在 schema 裡。第四行是試圖修改共用 Agent 的結果：`FrozenInstanceError` 讓這種錯誤在開發時就炸出來，而不是在 production 讓某個請求偷偷改掉所有請求共用的步數上限。最後兩行用 `replace()` 產生 canary 版本，只改了指令，tools 仍是同一個物件，所以複製的成本幾乎為零。

> [!tip] 宣告要能被機器讀
> 設定是資料，就能被程式檢查。青鳥在 CI 裡加了一個檢查：列出每個 Agent 能用的 destructive tool，和 Maya 核准過的清單比對，多出來的就讓 build 失敗。這種檢查在「agent 是一個有 `run()` 方法的類別、tool 寫在方法裡」的設計下幾乎做不到。

## 23.6 Runner、Session 與 Event：執行、狀態與紀錄

**Runner** 是 framework 的心臟，但它本身沒有狀態：同一個 Runner 物件可以同時服務上千段對話，每一次 `run()` 的狀態都在參數與 Session 裡。v0.1 的所有保證都搬進 Runner：步數上限、max_tokens 不執行半截的 tool call、tool 例外轉成觀察、每個 tool call 都有對應結果；另外加上第 25 章正規化後才會出現的第四種停止原因 refusal（模型拒答）：不執行任何 tool，以 status=refusal 結束，交給產品政策處理。v0.5 再加上兩個責任：把每一件事寫成 Event，以及在 lifecycle 的固定位置呼叫 middleware。本章的 Runner 是同步的參考實作，目的是把語意定清楚；第 24 章的 `loom.runtime` 會用 asyncio 實作同一份契約，加上串流、平行 tool call、取消與重試。

**Session** 的介面只有兩個方法：`load()` 讀回這段對話的所有事件，`append(event)` 追加一個事件。介面這麼小是刻意的，因為它要容納差異很大的實作：記憶體版用於測試；資料庫版用於一般的線上服務；第 22 章的事件日誌版在 crash 後可以重播。主流 SDK 也是同樣的設計：OpenAI Agents SDK 提供多種 session 後端，ADK 有 SessionService，介面都小，實作可以換。

**Event** 是本章最重要的抽象。第 10 章說過「context 是 log 的可重建視圖」，第 22 章把每次 model call 與 tool call 記成事件來重播；v0.5 把這個想法定為全框架的規則：**事件是唯一的事實來源，其他一切都是投影**。messages 是給模型看的投影，只包含 user、assistant 與 tool 結果；trace 是給工程師看的投影，包含 guardrail 觸發、handoff、usage；帳單是給財務看的投影，只加總 usage。這解決了 23.1 節的第三個事故：三個 agent 的用量之所以算出三個數字，是因為各自從不同的地方「數」用量；如果用量都來自同一種事件，就只會有一種算法。用量的欄位本身也要統一：第 25 章會把各家的 usage 正規化成四個互不重疊的桶（未命中快取的輸入 `input_tokens`、快取讀 `cache_read_tokens`、快取寫 `cache_write_tokens`、輸出 `output_tokens`），所以 23.12 節的 `RunContext.usage` 一開始就採用這四個欄位，預算 middleware 加總的也是這四個桶。

```text
 呼叫端          Runner                  Middleware 鏈            Model / Tool        Session
   │ run(agent,     │                          │                        │                │
   │  input,        │── emit run_started ──────┼────────────────────────┼──────────────► │ append #0
   │  session,deps)►│── before_run(input) ────►│ input guardrail        │                │
   │                │── emit user_message ─────┼────────────────────────┼──────────────► │ append #1
   │                │── load() → to_messages ◄─┼────────────────────────┼─────────────── │
   │                │── wrap_model(req) ──────►│ 日誌 → 預算 → … ──────►│ complete()     │
   │                │◄──────────────────────── │◄──────── ModelResponse │                │
   │                │── emit model_response ───┼────────────────────────┼──────────────► │ append #2
   │                │── wrap_tool(call) ──────►│ … → tool guardrail ───►│ get_order()    │
   │                │◄──────────────────────── │◄────────── ToolResult  │                │
   │                │── emit tool_result ──────┼────────────────────────┼──────────────► │ append #3
   │                │   …（回到 load，直到停止條件成立）                                 │
   │◄── RunResult ──│── emit run_finished ─────┼────────────────────────┼──────────────► │ append #n
```

這張時序圖是一次 run 的完整節奏。每個 emit 都做兩件事：先寫進 Session，再通知所有 middleware 的 `on_event`。順序不能顛倒：如果先通知 middleware，某個 hook 丟例外時，事件可能沒寫進去，事實來源就出現缺口。注意 `before_run` 在 `user_message` 之前：input guardrail 要在輸入「落地」之前檢查，否則使用者貼上的卡號已經寫進資料庫，事後再攔也來不及。每一輪呼叫模型之前，Runner 都從 Session 重新投影 messages，而不是在記憶體裡維護另一份清單；這讓「同一段對話的第二輪」與「crash 後重播」走的是同一條路。

| 事件類型 | 何時產生 | 主要欄位 | 模型看得到？ | 主要用途 |
|---|---|---|---|---|
| `run_started` | run 開始 | agent | 否 | 切分同一 session 內的多次 run |
| `user_message` | 輸入通過 input guardrail 後 | text | 是 | 投影成 user 訊息 |
| `model_response` | 每次模型回應 | text、tool_calls、usage（第 24 章新增 attempts） | 是 | 投影成 assistant 訊息；計費 |
| `tool_result` | 每個 tool call 結束（含被攔、被取消） | id、name、is_error、content（第 24 章新增 status） | 是 | 投影成 tool 訊息；配對不變式 |
| `handoff` | active agent 改變 | source、target、note | 否 | 追蹤「誰在負責」；下一輪從誰開始 |
| `guardrail_tripped` | 任何 guardrail 攔下 | guardrail、stage、reason | 否 | 安全稽核、誤判率統計 |
| `run_finished` | run 結束 | status、output | 否 | 成功率、轉真人率等營運指標 |

這張表的第四欄是 Event 抽象的關鍵：模型只看得到三種事件，其他四種是給系統自己用的。如果沒有 Event，只有 messages，guardrail 觸發與 handoff 這類資訊就只能塞進 messages（干擾模型、浪費 token），或另外寫一份 log（和 messages 不同步）。第二欄的「含被攔、被取消」也很重要：被 guardrail 攔下的 tool call、因預算用完而取消的 tool call，都要產生 `tool_result`，配對不變式才不會在例外路徑上破功。

> [!warning] 常見誤解
> 「事件就是 log，隨便寫寫就好。」事件和 log 的差別在於事件是**契約**：messages、重播、計費、稽核都從它推導，它的欄位一旦被下游依賴就不能隨便改。log 可以每版重寫格式，事件不行；所以每個事件都帶著 schema 版本，23.10 節會看到怎麼升級舊事件。

## 23.7 Handoff 與 Guardrail：兩個「看起來像 tool」的抽象

Handoff 與 Guardrail 都可以用 tool 或 middleware 硬做出來，為什麼要升格成核心抽象？因為它們各自保護了一個 tool 保護不了的不變式。

**Handoff** 的不變式是「任何時刻只有一個 active agent，而且交接一定被記錄」。第 20 章已經說明，handoff 通常設計成一種特殊的 tool call：模型呼叫 `transfer_to_refund`，Runner 不碰外部世界，只把 active agent 換掉。如果把它當成普通 tool，tool 函式就得想辦法改 Runner 的內部狀態，這等於打破「tool 不能碰 harness」的邊界。v0.5 的做法是讓 Agent 宣告 `handoffs`，Runner 自動為每個 handoff 產生一個 `transfer_to_<名稱>` 的 tool 定義（帶一個 `note` 參數當交接筆記），模型呼叫時由 Runner 處理：回填一則「已轉給 X」的 tool 結果維持配對、寫一個 `handoff` 事件、換掉 active agent。`RunResult.last_agent` 告訴呼叫端下一輪要從哪個 agent 繼續，否則使用者追問時又會回到分流 agent，重新被分流一次。

**Guardrail** 的不變式是「政策在固定位置執行，不能被跳過」。本書把 guardrail 依位置分成三種：**input guardrail** 在使用者輸入進入系統前檢查（例如卡號、明顯越權的要求）；**tool guardrail** 在 tool 執行前檢查參數（例如訂單是否屬於目前的使用者）；**output guardrail** 在回答送出前檢查（例如是否洩漏內部資訊）。第 32 章會深入談防禦設計，第 21 章談核准；本章只處理它在 framework 中的位置。關鍵的設計是把 guardrail 拆成兩半：**宣告**是 Agent 上的資料（`Guardrail(name, stage, check)`），**執行機制**是一個普通的 middleware。這樣審查時可以從設定直接列出每個 agent 有哪些 guardrail，而執行邏輯只有一份。

guardrail 有一個主流 SDK 之間差異很大的取捨：**阻塞還是並行**。阻塞式是先檢查、通過才繼續，安全但增加延遲；並行式是 guardrail 與 agent 同時跑，guardrail 一旦觸發就中止 agent（fail-fast），延遲低但 agent 可能已經多花了一點 token。依公開文件，OpenAI Agents SDK 的 input guardrail 採並行加 fail-fast 的設計。判斷原則是看「被攔之前多跑的那一段」有沒有副作用：只呼叫模型、沒有執行 tool，可以並行；會執行 tool 的路徑，tool guardrail 一定要阻塞。loom v0.5 的核心版本全部採阻塞式，因為同步 Runner 沒有並行；第 24 章的 async runtime 可以把 input guardrail 改成並行。

> [!warning] 常見誤解
> 「guardrail 掛在 Agent 上就安全了。」掛在 Agent 上的 guardrail 只在那個 agent 是 active 時生效。handoff 之後，新的 agent 如果沒有宣告同一條 guardrail，它就消失了。全域必須成立的政策（例如不收卡號）應該設在 Runner 層的 middleware，每個 agent 都跑；只有 agent 專屬的政策（例如退款專員的訂單歸屬檢查）才宣告在 Agent 上。23.12 節的程式裡，分流 agent 的卡號檢查在交接給退款專員後就不會再執行，這正是一個要在設計時決定的取捨。

## 23.8 Hooks 與 middleware：擴充點的設計

framework 的價值有一半在核心，另一半在**擴充點**（extension point）：使用者能在哪裡、用什麼方式改變行為，而不必修改框架原始碼。設計不好的框架只有兩種結局：使用者 fork 一份自己改（回到 23.1 節的三條分岔），或用 monkey patch 硬改內部函式（下一次升級就壞）。

擴充點有兩種基本形態。**hook**（掛鉤）是在 lifecycle 的某個時間點呼叫你的函式，例如「每產生一個事件就通知我」；hook 適合觀察，通常不能改變流程。**middleware**（中介層）則是把某個呼叫整個包起來：它拿到請求，可以檢查、修改、決定要不要呼叫下一層，也可以修改結果再往外回傳。多個 middleware 疊起來就是**洋蔥模型**（onion model）：請求從最外層一路穿到最內層的真正動作，結果再從內往外一路傳回。Web 框架的 middleware（例如 WSGI 或 Express 的 middleware）就是這個結構。

```text
                         wrap_tool(create_return)
 ┌──────────────────────── LoggingMiddleware ────────────────────────┐
 │ ┌──────────────────────── BudgetMiddleware ─────────────────────┐ │
 │ │ ┌────────────────────── GuardrailMiddleware ────────────────┐ │ │
 │ │ │                                                           │ │ │
 │ │ │   ──► 檢查 owns_order ── 不通過 ──► 短路：回傳 is_error   │ │ │
 │ │ │            │                                              │ │ │
 │ │ │            └─ 通過 ──► 最內層：dispatch → Tool.fn(deps,…) │ │ │
 │ │ │                                                           │ │ │
 │ │ └───────────────────────────────────────────────────────────┘ │ │
 │ └───────────────────────────────────────────────────────────────┘ │
 └───────────────────────────────────────────────────────────────────┘
   進：外 → 內；出：內 → 外。清單第一個 middleware 在最外層，看得到所有結果。
```

這張洋蔥圖說明了順序為什麼就是語意。請求從最外層的 logging 進入，經過 budget，再到 guardrail；guardrail 決定短路時，結果直接往外回傳，最內層的 tool 不會執行，但外面兩層仍然會看到這個被攔下的結果。如果把順序反過來，讓 guardrail 在最外層，它短路時 logging 根本沒被呼叫，稽核紀錄裡就看不到這次攔截。一般的排列原則是：觀察類（日誌、tracing）放最外層，資源類（預算、rate limit）在中間，政策類（guardrail、核准）最靠近真正的動作。

```python
from __future__ import annotations

from typing import Callable

trace: list[str] = []


class Middleware:
    def __init__(self, name: str, block: bool = False):
        self.name, self.block = name, block

    def wrap_tool(self, call: str, nxt: Callable[[str], str]) -> str:
        trace.append(f"→ {self.name}")
        if self.block:                                     # 短路：不呼叫 nxt，內層與 tool 都不會執行
            result = f"{self.name} 攔下 {call}"
        else:
            result = nxt(call)
        trace.append(f"← {self.name}")
        return result


def chain(middleware: list[Middleware], terminal: Callable[[str], str]) -> Callable[[str], str]:
    fn = terminal
    for mw in reversed(middleware):                       # 由內往外包，清單第一個在最外層
        fn = (lambda m, nxt: lambda c: m.wrap_tool(c, nxt))(mw, fn)
    return fn


def tool(call: str) -> str:
    trace.append(f"  ★ 執行 {call}")
    return f"{call} 完成"


for order in (["logging", "budget", "guardrail"], ["guardrail", "budget", "logging"]):
    trace.clear()
    mws = [Middleware(n, block=(n == "guardrail")) for n in order]
    result = chain(mws, tool)("create_return(B-2077)")
    print(f"順序 {order}：{result}")
    print("   " + "  ".join(trace))

trace.clear()
print("全部放行：", chain([Middleware("logging"), Middleware("budget")], tool)("get_order(B-1042)"))
print("   " + "  ".join(trace))
assert trace == ["→ logging", "→ budget", "  ★ 執行 get_order(B-1042)", "← budget", "← logging"]
```

```text
順序 ['logging', 'budget', 'guardrail']：guardrail 攔下 create_return(B-2077)
   → logging  → budget  → guardrail  ← guardrail  ← budget  ← logging
順序 ['guardrail', 'budget', 'logging']：guardrail 攔下 create_return(B-2077)
   → guardrail  ← guardrail
全部放行： get_order(B-1042) 完成
   → logging  → budget    ★ 執行 get_order(B-1042)  ← budget  ← logging
```

第一組輸出是建議的順序：請求依序穿過 logging、budget、guardrail，guardrail 短路後，結果依序穿回 budget 與 logging，兩層都看得到「攔下」。第二組把 guardrail 放到最外層：它一短路，trace 裡只有 `→ guardrail ← guardrail`，logging 從頭到尾沒有出現，這就是稽核紀錄的缺口。第三組是全部放行的正常路徑，tool 在洋蔥正中間執行。`chain()` 裡 `(lambda m, nxt: ...)(mw, fn)` 的寫法是為了在迴圈中把當下的 `mw` 與 `fn` 綁進 closure；直接寫 `lambda c: mw.wrap_tool(c, fn)` 的話，closure 要到被呼叫時才讀取 `mw` 與 `fn`，讀到的是迴圈結束時的值，這是 Python 很經典的 late binding 陷阱（延伸問答 Q5）。

loom v0.5 定義了四個擴充點，刻意只有四個：

| 擴充點 | 形態 | 何時呼叫 | 可以做什麼 | 典型用途 |
|---|---|---|---|---|
| `before_run(ctx, input)` | hook | 輸入落地之前 | 丟 `StopRun` 結束 run | input guardrail、租戶配額檢查 |
| `wrap_model(ctx, req, nxt)` | middleware | 每次呼叫模型 | 修改請求、短路、修改回應、丟 `StopRun` | 預算、context 組裝、output guardrail、cache 標記 |
| `wrap_tool(ctx, call, nxt)` | middleware | 每次執行 tool | 檢查參數、短路回傳錯誤、改寫結果 | tool guardrail、核准、idempotency key、結果遮蔽 |
| `on_event(ctx, event)` | hook | 每個事件寫入 Session 之後 | 只能觀察 | 日誌、tracing、計費、AG-UI 串流 |

為什麼不多開幾個，例如 `before_handoff`、`after_tool_success`、`on_guardrail_tripped`？因為每個擴充點都是一份向後相容的契約，開了就很難收回。上面四個已經能表達大部分需求：handoff 與 guardrail 觸發都是事件，`on_event` 看得到；「tool 成功後」就是 `wrap_tool` 裡 `nxt()` 回傳之後。另一個刻意的限制是 `on_event` 只能觀察、不能改變流程：觀察類的程式（例如 tracing）常常由不同團隊維護，如果它們也能改變流程，一個 tracing 套件的 bug 就可能讓 agent 行為改變，這是最難除錯的一種故障。

主流 SDK 的擴充點設計各有側重。Claude Agent SDK 的 hooks（例如 PreToolUse、PostToolUse、UserPromptSubmit、Stop）沿用 Claude Code 的設計，以事件名稱掛上處理函式，PreToolUse 可以決定是否放行 tool；ADK 提供 before／after agent、model、tool 的 callbacks，以及可以跨 agent 套用的 plugins；Microsoft Agent Framework 的 middleware 可以攔截 agent、function 與 chat 呼叫；LangChain 1.x 的 `create_agent` 以 middleware 清單提供 model 呼叫前後與包裹式的擴充；Mastra 用 processors 管線統一 guardrail、路由與分類。名稱不同，但都落在「時間點 hook」與「包裹式 middleware」這兩種形態上，詳細介面放在 23.11 節的 2026 現況。

> [!tip] middleware 的失敗語意要寫進文件
> middleware 丟出未預期的例外時，framework 要決定：整個 run 失敗？略過這個 middleware？loom v0.5 的規則是：`StopRun` 是正常的控制流（預算、攔截），其他例外一律讓 run 失敗並保留已寫入的事件，不悄悄略過。悄悄略過一個 guardrail middleware 的錯誤，等於在安全檢查壞掉時預設放行。

## 23.9 loom v0.5 的架構與模組依賴

有了核心抽象與擴充點，就可以把前面各章做出來的模組放到正確的位置。原則只有一條：**核心不依賴任何模組，所有模組只依賴核心**。核心（`loom.core`）定義八個抽象、Model 與 Session 的介面，以及同步的參考 Runner；其他模組都是「實作某個介面」或「掛在某個擴充點上」。

```text
 ┌──────────────────────────────── 應用層 ────────────────────────────────┐
 │  客服 agent         coding agent           research agent               │
 └───────────┬─────────────────┬──────────────────────┬────────────────────┘
             ▼                 ▼                      ▼
 ┌──────────────────────── Orchestration 層 ─────────────────────────────┐
 │  loom.workflows（第 18 章）  loom.graph（第 19 章）  loom.agents（第 20 章）│
 └───────────────────────────────┬────────────────────────────────────────┘
                                 ▼  只透過 Runner.run() 使用核心
 ┌─────────────────────────── loom.core（本章）───────────────────────────┐
 │ Agent  Tool  Handoff  Guardrail │ Runner │ Event  Session 介面 │ Model 介面 │
 │                Middleware：before_run｜wrap_model｜wrap_tool｜on_event     │
 └──────┬──────────────┬───────────────┬────────────────┬───────────────────┘
        │ 實作介面      │ 掛在 wrap_*    │ 掛在 on_event   │ 實作 Model／Runner
        ▼              ▼               ▼                ▼
  Session 實作     政策與資源         觀察              執行與模型
  loom.durable    loom.guardrails    loom.tracing      loom.runtime（第 24 章）
  （第 22 章）     loom.approval      loom.evals        loom.models（第 25 章）
                  loom.context
  Tool 來源       loom.compaction
  loom.tools、loom.schema、loom.registry、loom.mcp、loom.memory、loom.sandbox
```

這張分層圖由上往下讀。最上面是三個應用，它們只碰兩層：orchestration 層與核心。orchestration 層（workflow、graph、multi-agent）建在核心之上，而且只透過 `Runner.run()` 使用核心：第 19 章 graph 裡的某個節點如果是 agent，就是在節點裡呼叫一次 Runner。核心下方是四類外掛：Session 的實作（`loom.durable`）、掛在 `wrap_model`／`wrap_tool` 的政策與資源模組、掛在 `on_event` 的觀察模組，以及實作 Model 或 Runner 介面的執行模組。tool 的各種來源（自己寫的函式、registry、MCP server、memory tool）最後都產出同一種 `Tool`，核心不需要知道 tool 從哪裡來。

```text
                                 loom.core
          ▲        ▲        ▲        ▲        ▲        ▲        ▲
          │        │        │        │        │        │        │
     loom.tools loom.context loom.guardrails loom.tracing loom.durable loom.models loom.runtime
          ▲        ▲               ▲                                ▲
          │        │               │                                │
    loom.schema loom.compaction loom.approval                 （adapter 依賴各家
    loom.registry loom.memory                                   SDK，但只在這一層）
    loom.mcp      loom.retrieval
          ▲
          │                        ┌─────────────────────────────────────┐
    loom.workflows  loom.graph  loom.agents ── 只依賴 loom.core 的公開 API │
                                   └─────────────────────────────────────┘
 規則：箭頭只往上指；同層模組不互相 import；第三方依賴只出現在最外圈的 adapter
```

這張依賴圖比分層圖更嚴格，它規定誰可以 import 誰。所有箭頭都指向 `loom.core`，核心本身沒有任何往外的箭頭，所以核心可以單獨測試、單獨發版。同一層的模組不互相 import：`loom.tracing` 不知道 `loom.guardrails` 的存在，它只是在 `on_event` 看到 `guardrail_tripped` 事件；這讓任何一個模組都能被拿掉或替換。第三方依賴（各家模型 SDK、資料庫驅動）只能出現在最外圈的 adapter，例如 `loom.models` 的 provider adapter；核心與中間層只用標準函式庫，這也是全書程式碼能離線執行的原因。這條規則可以用一個簡單的 CI 檢查保護：解析每個模組的 import，發現往核心以外的方向依賴就失敗。

| 模組 | 來自 | 在 v0.5 中的位置 | 依賴 |
|---|---|---|---|
| `loom.tools`、`loom.schema` | 第 4、5、7 章 | 產生 `Tool`；最內層 dispatch 用 schema 驗證 | core |
| `loom.context`、`loom.compaction` | 第 9、10 章 | `wrap_model`：依預算組裝 context、必要時壓縮 | core |
| `loom.memory`、`loom.retrieval` | 第 11、12 章 | 一個 Tool＋一個 context provider | core、context |
| `loom.registry`、`loom.mcp` | 第 13、14 章 | 產生 `Tool`；deferred loading 只往 tool 清單尾端追加 | core、tools |
| `loom.guardrails`、`loom.approval` | 第 21、32 章 | `before_run`、`wrap_tool`、`wrap_model` | core |
| `loom.durable` | 第 22 章 | 實作 Session；重播時已完成的呼叫不再執行（v1.0 與 runtime 組裝） | core |
| `loom.workflows`、`loom.graph`、`loom.agents` | 第 18–20 章 | orchestration 層：呼叫 `Runner.run()` | core |
| `loom.runtime` | 第 24 章 | 實作 Runner 契約：async、串流、並行、取消、重試 | core |
| `loom.models` | 第 25 章 | 實作 Model 介面：provider adapter、fallback、routing | core |
| `loom.tracing`、`loom.evals` | 第 27、29 章 | `on_event`：從事件產生 span 與評估資料 | core |

這張表是 v0.5 的「搬家清單」。大部分模組的程式碼幾乎不用改，改的是它們接上核心的方式：第 9 章的 context builder 原本在 loop 裡被直接呼叫，現在變成一個 `wrap_model` middleware，在請求送出前把 messages 換成依預算組裝的版本；第 21 章的 PolicyEngine 原本寫在 dispatch 裡，現在是一個 `wrap_tool` middleware；第 22 章的事件日誌原本自己跑一份 loop，現在只實作 Session 介面；「重播時先查日誌、已完成的呼叫不再執行」則是 runtime 與 `loom.durable` 之間的協定：第 24 章的 runtime 負責在 crash 後補齊未完成的 tool call，重播本身由 `loom.durable` 提供，第 45 章的 `loom` v1.0 把兩者組裝起來。

兩個介面值得在這裡先定下來，細節留給後兩章。**Model 介面**就是全書一直在用的 `complete(messages, tools, system) -> ModelResponse`，ScriptedModel 本身就是一個合格的實作；第 25 章的 provider adapter、fallback 與 router 都實作這個介面，所以 router 對 Runner 來說只是另一個 Model。第 24 章的 async runtime 另外需要一個串流介面 `stream()`：先送出若干 `text_delta`，最後送出帶著完整 `ModelResponse` 的 `stop`；只實作 `complete()` 的模型，可以用一個小轉接函式包成「只有一個 `stop` 事件」的串流。路由放在 Model 層而不是 `wrap_model` middleware，是因為它需要知道各家 provider 的差異；middleware 只處理與 provider 無關的橫切關注點。**Runner 契約**則是本章參考 Runner 的行為：同樣的 Agent、輸入與劇本，第 24 章的 async runtime 必須產生同樣的事件序列，這個性質可以直接寫成測試。

## 23.10 API 設計與向後相容

framework 有使用者之後，最大的工程成本不是寫新功能，而是**不弄壞舊功能**。Google 的工程師 Hyrum Wright 有一個被廣為引用的觀察，稱為 **Hyrum's Law**：當一個 API 的使用者夠多，你在契約中承諾了什麼已經不重要，系統所有可觀察的行為都會被某個人依賴。例如 loom 從來沒承諾事件的 seq 從 0 開始，但只要它一直從 0 開始，就會有人寫出 `events[0]` 是 `run_started` 的程式。

因此 API 設計的第一步是劃清**公開介面**（public API）的邊界：哪些名稱是承諾、哪些是實作細節。loom 的規則是：模組頂層 `__all__` 列出的名稱、這些類別的公開欄位與方法、四個擴充點的簽名、事件類型與欄位，是公開介面；底線開頭的名稱（例如 `Runner._execute`）與未列出的模組是內部的，可以隨時改。第二步是讓 API 容易**只增不改**：建構子參數一律 keyword-only，日後新增參數不會打亂位置；回傳值用 dataclass 而不是 tuple，新增欄位不會讓解包的程式出錯（v0.1 的 `run()` 回傳 tuple 的版本就沒有這個彈性）；enum 類的值（例如 status）文件寫明「可能新增新的值，呼叫端要處理未知值」。

第三步是**漸進揭露**（progressive disclosure）的 API：最簡單的用法要一行就能跑，進階的能力才需要多設定。`Runner(model).run(agent, "B-1042 到哪了？", session)` 不需要任何 middleware 就能動；要預算就加一個 middleware，要 durable 就換一個 Session 實作。反面的例子是要求使用者先建立五個設定物件才能跑第一個 hello world，這種框架在 onboarding 時就會流失使用者。

| 變更類型 | 例子 | 相容嗎？ | loom 的做法 |
|---|---|---|---|
| 新增選用參數 | `Runner(..., max_result_chars=2000)` | 相容 | keyword-only，給安全的預設值 |
| 新增事件類型 | 新增 `approval_requested` | 對讀取端相容 | 文件寫明「未知事件類型要略過」 |
| 新增事件欄位 | `tool_result` 加上 `effect` | 相容 | 舊事件由 upcaster 補預設值 |
| 參數或欄位改名 | `token_budget` → `max_tokens` | 不相容 | 過渡期兩個名稱都收，發 DeprecationWarning，寫明移除版本 |
| 改變預設值 | `effect` 預設從 destructive 改 read | 不相容，且有安全風險 | 不做；安全相關的預設只能變得更保守 |
| 改變語意 | middleware 順序改成由內往外 | 不相容 | 只能在大版本做，並提供遷移指南 |
| 移除公開名稱 | 移除 v0.1 的 `Agent.run()` | 不相容 | 先 deprecation 至少一個版本週期，再移除 |

這張表裡最容易被低估的是「改變預設值」與「改變語意」。它們不會讓程式編譯失敗，也不會丟例外，只會讓行為悄悄改變，所以比改名更危險。安全相關的預設值是特例：只能往更保守的方向改。新增事件類型對讀取端相容的前提是讀取端會略過未知類型，這個要求要寫在文件裡，並在 loom 自己的投影函式中示範（`to_messages` 對不認得的事件直接略過）。

v0.1 到 v0.5 本身就是一次不相容的改版：v0.1 的 `Agent` 持有 model 並有 `run()` 方法，v0.5 的 Agent 是純設定、由 Runner 執行。loom 的做法是保留一個相容層 `loom.compat`：舊的 `Agent(model, tools).run(text)` 仍然可用，內部轉成 v0.5 的 Runner，並發出 DeprecationWarning，寫明 v1.0 移除。依**語意化版本**（Semantic Versioning）的規則，主版本號為 0 時任何改動都可能不相容；但對內部使用者來說，「規則允許」不等於「可以不管」，相容層是讓三個團隊能按自己的節奏遷移的必要成本。

事件需要特別小心，因為事件會被持久化：Session 裡可能留著半年前用舊版 loom 寫下的事件，第 22 章的重播也要能讀它們。所以每個事件帶 schema 版本 `v`，讀取時用 **upcaster**（升級器）逐版轉成最新格式；寫入一律用最新版。這是 event sourcing 系統處理 schema 演進的標準做法。

```python
from __future__ import annotations

import warnings
from typing import Any, Callable

# ── 1) 事件 upcaster：舊版事件永遠讀得回來 ──
# schema 第 1 版的 tool_result 用 error；第 2 版改名為 is_error，並新增 effect（舊資料不知道等級，依全書規則當 destructive）。
# 寫入一律用最新版；讀取時逐版升級，因為 session 與 durable log 裡會留著好幾年前的事件。
UPCASTERS: dict[tuple[str, int], Callable[[dict], dict]] = {
    ("tool_result", 1): lambda d: {**{k: v for k, v in d.items() if k != "error"},
                                   "is_error": d.get("error", False), "effect": "destructive"},
}
LATEST = {"tool_result": 2}


def upcast(event: dict) -> dict:
    while event["v"] < LATEST.get(event["type"], event["v"]):
        fn = UPCASTERS[(event["type"], event["v"])]
        event = {**event, "data": fn(event["data"]), "v": event["v"] + 1}
    return event


old = {"type": "tool_result", "v": 1, "data": {"id": "c1", "content": "已出貨", "error": False}}
new = upcast(old)
print("schema v1 →", old["data"])
print("schema v2 →", new["data"])
assert new["v"] == 2 and new["data"]["is_error"] is False and "error" not in new["data"]
assert upcast(new) == new                                     # 已是最新版就原樣回傳


# ── 2) 參數改名的過渡期：舊名照收、發出警告、寫明移除版本 ──
def renamed(old_name: str, new_name: str, remove_in: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if old_name in kwargs:
                warnings.warn(f"{old_name} 已改名為 {new_name}，將在 {remove_in} 移除",
                              DeprecationWarning, stacklevel=2)
                kwargs[new_name] = kwargs.pop(old_name)
            return fn(*args, **kwargs)
        return wrapper
    return deco


@renamed("token_budget", "max_tokens", remove_in="v1.0")
def make_budget(*, max_tokens: int = 50_000) -> dict:          # keyword-only：日後加參數不會打亂位置
    return {"max_tokens": max_tokens}


with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    legacy = make_budget(token_budget=8_000)                   # v0.1 時代的呼叫方式
    modern = make_budget(max_tokens=8_000)
print("舊名呼叫 →", legacy, "｜警告：", caught[0].message)
print("新名呼叫 →", modern, "｜警告數：", len(caught))
assert legacy == modern and len(caught) == 1 and caught[0].category is DeprecationWarning
```

```text
schema v1 → {'id': 'c1', 'content': '已出貨', 'error': False}
schema v2 → {'id': 'c1', 'content': '已出貨', 'is_error': False, 'effect': 'destructive'}
舊名呼叫 → {'max_tokens': 8000} ｜警告： token_budget 已改名為 max_tokens，將在 v1.0 移除
新名呼叫 → {'max_tokens': 8000} ｜警告數： 1
```

前兩行是事件升級：schema 第 1 版的 `tool_result` 用 `error` 欄位，升級後改名為 `is_error`，並補上第 2 版新增的 `effect`。補什麼值是一個設計決定：舊資料不知道 tool 的副作用等級，依全書規則「未標註一律當 destructive」，所以補 destructive，而不是補一個看起來比較無害的值。程式中的第二個 assert 確認已是最新版的事件原樣通過，所以 upcaster 可以放心在每次讀取時執行。後兩行是參數改名的過渡期：用舊名 `token_budget` 呼叫仍然得到正確結果，但會收到一則寫明移除版本的警告；用新名呼叫則沒有警告。警告要寫明「改成什麼」與「什麼時候移除」，只寫「已棄用」的警告，使用者不知道該怎麼改，也不知道有多急。

## 23.11 主流 SDK 的抽象選擇

把 loom 的八個抽象拿去對照主流 SDK，可以看到業界大致收斂到同一組概念，差異在於「核心有多厚」與「擴充用什麼形態」。第 26 章會從選型角度完整比較，這裡只看抽象設計。

**OpenAI Agents SDK** 是「少量 primitive、用程式碼編排」的代表：Agent 是設定（指令、tools、handoffs、guardrails、輸出型別），Runner 負責執行，handoff 設計成特殊的 tool call，guardrail 分成 input、output 與 tool 三種，session 有多種後端。loom 的核心形態和它最接近。**Google ADK** 的特色是把 Event 串流當作唯一的真相：Runner 產出事件，session 就是事件日誌，state 由事件中的變更推導；擴充用 before／after callbacks 與 plugins。loom 的「事件是唯一事實來源」與 ADK 的設計方向一致。**Claude Agent SDK** 走的是另一條路，稱為 harness-first：它把 Claude Code 的整套 harness（檔案與 shell 工具、權限、context 管理、subagents）當成 library 使用，擴充主要靠 hooks 與權限模式，而不是讓你組裝抽象。

**LangGraph** 的核心抽象是帶 checkpoint 的 state graph，agent 是 graph 的一種用法；LangChain 1.x 的高階 `create_agent` 建在 LangGraph 之上，用 middleware 擴充。**Microsoft Agent Framework** 同時提供 agent 與 graph workflow 兩層，middleware 可以攔截 agent、function 與 chat 呼叫，官方文件也明確建議「能用一般函式處理的任務，就不要用 AI agent」。**Pydantic AI** 把 agent 看成有型別的函式，以 `RunContext` 做依賴注入，durability 做成可抽換的後端。**Strands Agents** 則是「相信模型」的 model-driven loop，核心很薄，需要確定性時再加 graph 或 workflow。

| SDK | Agent 的形態 | 執行者 | 狀態與紀錄 | 擴充形態 | Handoff | Guardrail |
|---|---|---|---|---|---|---|
| loom v0.5 | 不可變設定 | Runner | Session（事件） | 4 個擴充點：hook＋middleware | 特殊 tool call | 宣告在 Agent，middleware 執行 |
| OpenAI Agents SDK | 設定物件 | Runner | Sessions、可序列化的 run state | guardrails、tracing processors | 特殊 tool call | input、output、tool 三種 |
| Google ADK | LlmAgent＋workflow agents | Runner（產出 Event） | SessionService（事件＋state） | callbacks、plugins | sub-agents 轉移 | callbacks、plugins |
| Claude Agent SDK | 選項設定＋完整 harness | SDK 驅動的 harness | sessions（resume、fork）、檔案系統 | hooks、權限模式 | subagents | hooks、權限檢查 |
| LangGraph／LangChain | graph 節點／`create_agent` | graph runtime | checkpointer、store | middleware、節點 | graph 邊、`Command` | middleware |
| Microsoft Agent Framework | Agent＋workflow | agent／workflow runtime | agent session、checkpoint | middleware（agent、function、chat） | 內建 handoff orchestration | middleware |
| Pydantic AI | 有型別的 Agent | `agent.run()` | message history、durability 後端 | toolsets、依賴注入 | agent delegation | 輸出驗證 |

這張表要橫著讀，看同一個概念在不同 SDK 長什麼樣。「Agent 的形態」一欄幾乎都是設定物件，差別在設定有多厚：Claude Agent SDK 的設定背後是一整套 harness，Strands 與 OpenAI 的設定則很薄。「狀態與紀錄」一欄分成兩派：以事件為中心（ADK、loom）與以 checkpoint 為中心（LangGraph、MAF 的 workflow），前者適合重播與稽核，後者適合從任意點恢復與 time travel，第 19 章與第 22 章分別談過兩者。「擴充形態」一欄則證明 hook 與 middleware 是業界的共同語言，只是命名不同。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各專案的公開文件與 release 紀錄：OpenAI Agents SDK（Python 版仍為 0.x，約 v0.23）的 `Agent` 參數包含 `instructions`、`tools`、`handoffs`、`output_type`、`input_guardrails`、`output_guardrails`，執行入口為 `Runner.run()`、`run_sync()`、`run_streamed()`，HITL 透過 tool 的 `needs_approval` 產生 interruptions，再以 `RunState` 序列化後恢復。Claude Agent SDK（Python 約 v0.2.16x）提供 `query()` 與 `ClaudeSDKClient`，hooks 包含 PreToolUse、PostToolUse、UserPromptSubmit、Stop 等。Google ADK 已進入 2.x，新增顯式 graph workflow。LangChain 1.x 的 `create_agent` 接受 middleware 清單，公開資料提到 `before_model`、`after_model`、`wrap_model_call`、`wrap_tool_call` 等 hook。Microsoft Agent Framework 為 .NET 1.2x／Python 1.1x，minor 版本仍可能有 breaking change。Pydantic AI 主線為 v2。各 SDK 發版頻繁，類別與參數名稱請以官方文件為準。

## 23.12 動手做：loom v0.5 核心介面與 middleware 鏈

這一節把前面的設計寫成可執行的程式。上半部是 `loom.core`：Tool、Guardrail、Handoff、Agent 四個不可變的宣告；Event 與 InMemorySession；`to_messages` 投影；Middleware 基底類別與四個擴充點；以及同步的參考 Runner。中段是三個只用公開擴充點寫成的 middleware：`LoggingMiddleware` 掛在 `on_event`，`BudgetMiddleware` 掛在 `wrap_model`，`GuardrailMiddleware` 掛在 `before_run` 與 `wrap_tool`，負責執行 Agent 上宣告的 guardrail。下半部是青鳥客服的分流與退款兩個 agent，以及四個情境。

情境 A 是正常路徑：分流 agent 把退款需求交接給退款專員，專員查單、建立退貨單，使用者再追問一句，驗證同一個 session 的第二輪接得上。情境 B 讓退款專員試圖替別人的訂單建立退貨單，由 tool guardrail 攔下。情境 C 是使用者在訊息中貼了卡號，input guardrail 在呼叫模型之前就結束 run。情境 D 是每一步都合理、但累計 token 超過租戶預算。最後檢查所有 run 的配對不變式。

```python
from __future__ import annotations

import json
import re
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
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens｜refusal（第 25 章）
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


# ═════════════════════════ loom v0.5 核心（loom.core）═════════════════════════
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]
    effect: str = "destructive"                 # 未標註的 tool 一律當 destructive（第 5 章）
    intent_fields: tuple[str, ...] = ()
    code_callable: bool = False                 # 有副作用的 tool 不開放給 code-as-action（第 13 章）

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass(frozen=True)
class Guardrail:
    name: str
    stage: str                                  # input｜tool｜output
    check: Callable[..., str | None]            # 回傳 None 代表通過；回傳字串代表攔下的理由


@dataclass(frozen=True)
class Handoff:
    target: "Agent"
    description: str

    @property
    def tool_name(self) -> str:
        return f"transfer_to_{self.target.name}"


@dataclass(frozen=True)
class Agent:                                    # 純設定：不持有 model 連線、不持有對話狀態
    name: str
    instructions: str
    tools: tuple[Tool, ...] = ()
    handoffs: tuple[Handoff, ...] = ()
    guardrails: tuple[Guardrail, ...] = ()
    max_steps: int = 8


@dataclass(frozen=True)
class Event:                                    # 唯一的事實紀錄；messages 只是它的一個投影
    seq: int
    type: str
    agent: str
    data: dict[str, Any]
    v: int = 1                                  # 事件 schema 版本：持久化的東西一定要能升級


class InMemorySession:
    """Session 介面只有兩個方法；換成資料庫或第 22 章的 durable log 時，Runner 不必改。"""

    def __init__(self, session_id: str):
        self.id, self._events = session_id, []

    def load(self) -> list[Event]:
        return list(self._events)

    def append(self, event: Event) -> None:
        self._events.append(event)


def to_messages(events: list[Event]) -> list[dict]:
    """把事件投影成模型看得懂的 messages。guardrail、handoff、usage 等事件模型看不到。"""
    out: list[dict] = []
    for e in events:
        if e.type == "user_message":
            out.append({"role": "user", "content": e.data["text"]})
        elif e.type == "model_response":
            out.append({"role": "assistant", "content": e.data["text"], "tool_calls": e.data["tool_calls"]})
        elif e.type == "tool_result":
            out.append({"role": "tool", "tool_call_id": e.data["id"], "name": e.data["name"],
                        "content": e.data["content"], "is_error": e.data["is_error"]})
    return out


@dataclass
class ModelRequest:
    system: str
    messages: list[dict]
    tools: list[dict]


@dataclass
class ToolResult:
    is_error: bool
    content: str


class StopRun(Exception):
    """middleware 用來結束整個 run（預算用完、輸入被攔下）。Runner 保證 tool 配對不變式。"""

    def __init__(self, status: str, output: str):
        super().__init__(status)
        self.status, self.output = status, output


@dataclass
class RunContext:
    run_id: str
    agent: Agent
    session: InMemorySession
    deps: dict[str, Any]                        # 依賴注入：使用者、租戶、DB client，tool 與 guardrail 共用
    # 用量一開始就採用第 25 章四個互不重疊的桶；少了快取的桶，預算會在快取命中率高時嚴重低估
    usage: dict[str, int] = field(default_factory=lambda: dict.fromkeys(
        ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens"), 0))
    emit: Callable[..., Any] = lambda *a, **k: None   # Runner 建立 context 後換成真正的 emit


class Middleware:
    """擴充點的基底類別。預設全部「直接放行」，子類別只覆寫自己關心的那幾個。"""

    def before_run(self, ctx: RunContext, user_input: str) -> None: ...
    def on_event(self, ctx: RunContext, event: Event) -> None: ...

    def wrap_model(self, ctx: RunContext, req: ModelRequest, nxt: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return nxt(req)

    def wrap_tool(self, ctx: RunContext, tc: ToolCall, nxt: Callable[[ToolCall], ToolResult]) -> ToolResult:
        return nxt(tc)


@dataclass
class RunResult:
    status: str                                 # done｜max_steps｜max_tokens｜refusal｜budget｜blocked
    output: str
    last_agent: Agent                           # 下一輪對話要從這個 agent 繼續（handoff 之後不是起點那個）
    usage: dict[str, int]
    events: list[Event]


class Runner:
    def __init__(self, model, middleware: list[Middleware] | None = None, max_result_chars: int = 2_000):
        self.model, self.middleware, self.max_result_chars = model, list(middleware or []), max_result_chars

    def _chain(self, method: str, terminal: Callable, ctx: RunContext) -> Callable:
        fn = terminal                           # 由內往外包：清單第一個 middleware 在最外層
        for mw in reversed(self.middleware):
            fn = (lambda m, nxt: lambda x: getattr(m, method)(ctx, x, nxt))(mw, fn)
        return fn

    def run(self, agent: Agent, user_input: str, session: InMemorySession, deps: dict | None = None) -> RunResult:
        start = len(session.load())
        ctx = RunContext(f"{session.id}#{start}", agent, session, dict(deps or {}))

        def emit(type_: str, **data: Any) -> Event:
            ev = Event(len(session.load()), type_, ctx.agent.name, data)
            session.append(ev)                  # 先寫進 session，再通知 middleware：紀錄不會因 hook 失敗而遺失
            for mw in self.middleware:
                mw.on_event(ctx, ev)
            return ev

        ctx.emit = emit

        def finish(status: str, output: str) -> RunResult:
            emit("run_finished", status=status, output=output)
            return RunResult(status, output, ctx.agent, dict(ctx.usage), session.load()[start:])

        emit("run_started", agent=agent.name)
        call_model = self._chain("wrap_model", self._call_model, ctx)
        call_tool = self._chain("wrap_tool", lambda tc: self._execute(ctx, tc), ctx)
        pending: list[ToolCall] = []
        try:
            for mw in self.middleware:          # 先過 input guardrail，再落地：被攔下的輸入不進 session
                mw.before_run(ctx, user_input)
            emit("user_message", text=user_input)
            for _ in range(ctx.agent.max_steps):
                a = ctx.agent
                tools = [t.schema() for t in a.tools] + [
                    {"name": h.tool_name, "description": h.description,
                     "parameters": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}}
                    for h in a.handoffs]
                resp = call_model(ModelRequest(a.instructions, to_messages(session.load()), tools))
                for k in ctx.usage:
                    ctx.usage[k] += resp.usage.get(k, 0)
                if resp.stop_reason in ("max_tokens", "refusal"):   # 半截的 tool call 不執行；拒答交給產品政策
                    emit("model_response", text=resp.text, tool_calls=[], usage=resp.usage)
                    return finish(resp.stop_reason, resp.text)
                emit("model_response", text=resp.text, tool_calls=[vars(tc) for tc in resp.tool_calls],
                     usage=resp.usage)
                if not resp.tool_calls:
                    return finish("done", resp.text)
                pending = list(resp.tool_calls)
                while pending:
                    tc = pending[0]
                    handoff = next((h for h in a.handoffs if h.tool_name == tc.name), None)
                    if handoff:                              # handoff 是特殊的 tool call：不碰外部世界，只換 active agent
                        emit("tool_result", id=tc.id, name=tc.name, is_error=False,
                             content=f"已轉給 {handoff.target.name}")
                        emit("handoff", source=a.name, target=handoff.target.name, note=tc.args.get("note", ""))
                        ctx.agent = handoff.target
                    else:
                        r = call_tool(tc)
                        emit("tool_result", id=tc.id, name=tc.name, is_error=r.is_error, content=r.content)
                    pending.pop(0)
            return finish("max_steps", "步驟用完了，我先整理目前進度並轉給真人同事。")
        except StopRun as stop:
            for tc in pending:                               # 不論怎麼停，每個 tool call 都要有結果
                emit("tool_result", id=tc.id, name=tc.name, is_error=True, content=f"已取消：{stop.status}")
            return finish(stop.status, stop.output)

    def _call_model(self, req: ModelRequest) -> ModelResponse:
        return self.model.complete(req.messages, tools=req.tools, system=req.system)

    def _execute(self, ctx: RunContext, tc: ToolCall) -> ToolResult:
        """洋蔥最內層：第 4 章的 dispatch（名稱、參數驗證、例外回填、截斷）。"""
        tool = next((t for t in ctx.agent.tools if t.name == tc.name), None)
        if tool is None:
            return ToolResult(True, f"沒有名為 {tc.name} 的工具。")
        missing = [p for p in tool.parameters.get("required", []) if p not in tc.args]
        unknown = [p for p in tc.args if p not in tool.parameters.get("properties", {})]
        if missing or unknown:
            return ToolResult(True, f"參數錯誤：缺少 {missing}，不認得 {unknown}。")
        try:
            out = tool.fn(ctx.deps, **tc.args)
        except Exception as exc:
            return ToolResult(True, f"{type(exc).__name__}: {exc}")
        text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        return ToolResult(False, text[: self.max_result_chars])


# ─────────────── 三個 middleware：日誌、預算、guardrail（都只用公開擴充點）───────────────
class LoggingMiddleware(Middleware):
    def __init__(self):
        self.lines: list[str] = []

    def on_event(self, ctx, ev):
        detail = {"user_message": lambda d: d["text"][:24],
                  "model_response": lambda d: [c["name"] for c in d["tool_calls"]] or d["text"][:22],
                  "tool_result": lambda d: ("ERR " if d["is_error"] else "") + d["content"][:30],
                  "handoff": lambda d: f"{d['source']} → {d['target']}｜{d['note']}",
                  "guardrail_tripped": lambda d: f"{d['guardrail']}：{d['reason']}",
                  "run_finished": lambda d: d["status"]}.get(ev.type)
        if detail:
            self.lines.append(f"  #{ev.seq:<2} {ev.agent:<7} {ev.type:<17} {detail(ev.data)}")


class BudgetMiddleware(Middleware):
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def wrap_model(self, ctx, req, nxt):
        if sum(ctx.usage.values()) >= self.max_tokens:      # 呼叫前檢查：呼叫模型就是花錢的動作
            raise StopRun("budget", "這個問題處理得比預期久，我先轉給真人同事協助。")
        return nxt(req)


class GuardrailMiddleware(Middleware):
    """Guardrail 是宣告在 Agent 上的資料；執行它的機制是一個普通的 middleware。"""

    def _trip(self, ctx, g, reason):
        ctx.emit("guardrail_tripped", guardrail=g.name, stage=g.stage, reason=reason)

    def before_run(self, ctx, user_input):
        for g in ctx.agent.guardrails:
            if g.stage == "input" and (reason := g.check(ctx.deps, user_input)):
                self._trip(ctx, g, reason)
                raise StopRun("blocked", "為了保護您的資料，請不要在對話中提供完整卡號。")

    def wrap_tool(self, ctx, tc, nxt):
        for g in ctx.agent.guardrails:
            if g.stage == "tool" and (reason := g.check(ctx.deps, tc)):
                self._trip(ctx, g, reason)
                return ToolResult(True, f"已被安全規則攔下：{reason}。請向使用者說明，不要改用其他工具繞過。")
        return nxt(tc)
# ═════════════════════════════ loom v0.5 核心結束 ═════════════════════════════


# 青鳥的假後端：tool 的第一個參數是 deps（依賴注入），不從模型拿身分
ORDERS = {"B-1042": {"owner": "u42", "status": "shipped", "amount": 1280},
          "B-2077": {"owner": "u99", "status": "shipped", "amount": 560}}


def get_order(deps, order_id: str) -> dict:
    if order_id not in ORDERS:
        raise KeyError(f"找不到訂單 {order_id}")
    return {"order_id": order_id, **{k: v for k, v in ORDERS[order_id].items() if k != "owner"}}


def create_return(deps, order_id: str) -> dict:
    return {"return_id": "R-7781", "order_id": order_id, "pickup": "後天"}


def obj(**props: str) -> dict:
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


def no_card_number(deps, text: str) -> str | None:
    return "訊息中疑似有完整卡號" if re.search(r"\b(?:\d[ -]?){16}\b", text) else None


def owns_order(deps, tc: ToolCall) -> str | None:
    oid = tc.args.get("order_id")
    if tc.name == "create_return" and ORDERS.get(oid, {}).get("owner") != deps["user_id"]:
        return f"訂單 {oid} 不屬於目前登入的使用者"
    return None


T_GET = Tool("get_order", "查詢訂單狀態與金額", obj(order_id="訂單編號，例如 B-1042"), get_order, effect="read")
T_RET = Tool("create_return", "已出貨訂單建立退貨單", obj(order_id="訂單編號"), create_return,
             effect="write", intent_fields=("order_id",))
refund_agent = Agent("refund", "你負責退貨與退款。", tools=(T_GET, T_RET),
                     guardrails=(Guardrail("owns_order", "tool", owns_order),))
triage = Agent("triage", "你是青鳥客服的分流助理。", tools=(T_GET,),
               handoffs=(Handoff(refund_agent, "退款、退貨問題交給退款專員"),),
               guardrails=(Guardrail("no_card_number", "input", no_card_number),))


def make_runner(script, budget: int = 10_000) -> tuple[Runner, LoggingMiddleware, ScriptedModel]:
    log, model = LoggingMiddleware(), ScriptedModel(script)
    # 順序就是語意：日誌在最外層（看得到所有事件）、預算其次、guardrail 最靠近 tool
    return Runner(model, [log, BudgetMiddleware(budget), GuardrailMiddleware()]), log, model


def paired(events: list[Event]) -> bool:
    ids = [c["id"] for e in events if e.type == "model_response" for c in e.data["tool_calls"]]
    return ids == [e.data["id"] for e in events if e.type == "tool_result"]


def priced(r: ModelResponse, tokens: int = 900) -> ModelResponse:
    r.usage = {"input_tokens": tokens, "output_tokens": 100}
    return r


# 情境 A：分流 → handoff → 退款專員查單、建立退貨單；同一個 session 再追問一輪
runner, log, model = make_runner([
    call("transfer_to_refund", note="u42 要退 B-1042"),
    call("get_order", "c2", order_id="B-1042"),
    call("create_return", "c3", order_id="B-1042"),
    say("B-1042 已出貨，已建立退貨單 R-7781，後天到府取件。"),
    say("取件時間是後天，物流會先打電話給您。"),
])
s1 = InMemorySession("s-u42")
a = runner.run(triage, "B-1042 我不要了，幫我退款", s1, deps={"user_id": "u42"})
a2 = runner.run(a.last_agent, "那什麼時候來收？", s1, deps={"user_id": "u42"})
print("── A 分流、handoff 與同一個 session 的第二輪")
print("\n".join(log.lines))
assert a.status == "done" and a.last_agent.name == "refund" and a2.status == "done"
assert len(model.calls[-1]) == 9                 # 第二輪模型看到 user＋前一輪 7 則＋新的 user
print(f"  第二輪送給模型的 messages：{len(model.calls[-1])} 則；session 事件總數：{len(s1.load())}\n")

# 情境 B：退款專員想替別人的訂單建立退貨單，tool guardrail 攔下，模型改口
runner, log, model = make_runner([
    call("transfer_to_refund", note="u42 要退 B-2077"),
    call("create_return", "c2", order_id="B-2077"),
    lambda msgs: say("這張訂單不在您的帳號下，我無法處理，請確認訂單編號。")
    if "安全規則" in msgs[-1]["content"] else say("已建立退貨單"),
])
b = runner.run(triage, "幫我退 B-2077", InMemorySession("s-b"), deps={"user_id": "u42"})
print("── B tool guardrail")
print("\n".join(log.lines))
assert b.status == "done" and "無法處理" in b.output

# 情境 C：輸入含卡號，input guardrail 在呼叫模型之前就結束 run
runner, log, model = make_runner([say("（不應該被呼叫）")])
c = runner.run(triage, "我的卡號 4111 1111 1111 1111 被扣了兩次", InMemorySession("s-c"), deps={"user_id": "u42"})
print("\n── C input guardrail")
print("\n".join(log.lines))
assert c.status == "blocked" and model.calls == []
assert not [e for e in c.events if e.type == "user_message"]   # 卡號沒有寫進 session

# 情境 D：每一步都合理，但累計 tokens 超過租戶預算
runner, log, model = make_runner([priced(call("get_order", f"c{i}", order_id="B-1042")) for i in range(6)],
                                 budget=2_500)
d = runner.run(refund_agent, "一直幫我查 B-1042", InMemorySession("s-d"), deps={"user_id": "u42"})
print("\n── D 預算 middleware")
print("\n".join(log.lines[-3:]))
assert d.status == "budget" and len(model.calls) == 3 and d.usage["input_tokens"] == 2_700

for r in (a, a2, b, c, d):
    assert paired(r.events)
print("\n五個 run 全部通過；每個 tool call 都有對應的 tool_result 事件")
```

```text
── A 分流、handoff 與同一個 session 的第二輪
  #1  triage  user_message      B-1042 我不要了，幫我退款
  #2  triage  model_response    ['transfer_to_refund']
  #3  triage  tool_result       已轉給 refund
  #4  triage  handoff           triage → refund｜u42 要退 B-1042
  #5  refund  model_response    ['get_order']
  #6  refund  tool_result       {"order_id": "B-1042", "status
  #7  refund  model_response    ['create_return']
  #8  refund  tool_result       {"return_id": "R-7781", "order
  #9  refund  model_response    B-1042 已出貨，已建立退貨單 R-77
  #10 refund  run_finished      done
  #12 refund  user_message      那什麼時候來收？
  #13 refund  model_response    取件時間是後天，物流會先打電話給您。
  #14 refund  run_finished      done
  第二輪送給模型的 messages：9 則；session 事件總數：15

── B tool guardrail
  #1  triage  user_message      幫我退 B-2077
  #2  triage  model_response    ['transfer_to_refund']
  #3  triage  tool_result       已轉給 refund
  #4  triage  handoff           triage → refund｜u42 要退 B-2077
  #5  refund  model_response    ['create_return']
  #6  refund  guardrail_tripped owns_order：訂單 B-2077 不屬於目前登入的使用者
  #7  refund  tool_result       ERR 已被安全規則攔下：訂單 B-2077 不屬於目前登入的使用者
  #8  refund  model_response    這張訂單不在您的帳號下，我無法處理，請確認訂
  #9  refund  run_finished      done

── C input guardrail
  #1  triage  guardrail_tripped no_card_number：訊息中疑似有完整卡號
  #2  triage  run_finished      blocked

── D 預算 middleware
  #6  refund  model_response    ['get_order']
  #7  refund  tool_result       {"order_id": "B-1042", "status
  #8  refund  run_finished      budget

五個 run 全部通過；每個 tool call 都有對應的 tool_result 事件
```

逐段解說這份輸出。

**情境 A** 的每一行都是一個事件，`#` 後面是事件在 session 中的序號。#1 是使用者訊息；#2 分流 agent 呼叫 `transfer_to_refund`；#3 是 Runner 為這個 handoff 回填的 tool 結果，維持配對不變式；#4 是 `handoff` 事件，帶著交接筆記「u42 要退 B-1042」。從 #5 開始，事件的 agent 欄位變成 refund：退款專員查單、建立退貨單、回答。#10 之後是同一個 session 的第二輪（#11 的 `run_started` 沒有印出），#12 的使用者追問直接由 refund 處理，因為呼叫端用的是 `a.last_agent`。最後一行顯示第二輪模型看到 9 則 messages：第一輪的 8 則（不含 handoff 事件，模型看不到它）加上新的追問。session 一共 15 個事件，比 messages 多出來的就是 `run_started`、`handoff`、`run_finished` 這些只給系統看的事件。

**情境 B** 的 #6 是關鍵：退款專員呼叫 `create_return(B-2077)`，`GuardrailMiddleware.wrap_tool` 用 `deps` 中的 user_id 比對訂單歸屬，發現 B-2077 屬於 u99，於是寫一個 `guardrail_tripped` 事件並短路；#7 的 tool 結果是 `ERR 已被安全規則攔下`，`create_return` 本體從頭到尾沒有執行。劇本中的模型讀到這則錯誤後改口告知使用者。注意身分來自 `deps`，不是來自模型的參數：模型就算被誘導在參數裡寫「我是 u99」，tool guardrail 也不會採信。

**情境 C** 只有兩個事件：`guardrail_tripped` 與 `run_finished`，status 是 blocked。assert 確認模型一次都沒被呼叫，也確認 session 裡沒有 `user_message` 事件：卡號沒有落地。這就是 23.6 節把 `before_run` 放在 `user_message` 之前的原因。如果順序反過來，卡號會先寫進 session，之後的 tracing、備份、分析管線都會帶著它。

**情境 D** 印出最後三個事件。劇本中每次模型回應用掉 1,000 tokens（900 input＋100 output），預算是 2,500；前兩次呼叫後累計 2,000，第三次呼叫前檢查仍未超過，於是放行；第三次之後累計 3,000，第四次呼叫前 `BudgetMiddleware` 丟出 `StopRun("budget")`，run 結束。assert 驗證模型被呼叫恰好 3 次、input tokens 累計 2,700。這仍然是第 4 章說的軟上限，超出的幅度最多一輪；差別在於現在預算是一個 middleware，三個 agent 掛同一個，用量都從 `model_response` 事件累加，23.1 節「三個 agent 算出三個數字」的問題就消失了。

最後一行是整個核心最重要的保證：五個 run 不論以 done、blocked、budget 哪一種方式結束，每個 tool call 都有對應的 `tool_result` 事件。這個保證寫在 Runner 裡，不依賴任何 middleware 的正確性：middleware 丟 `StopRun` 時，Runner 會替還沒處理的 tool call 補上「已取消」的結果。

| 23.1 節的事故 | 根本原因 | v0.5 的機制 | 本節驗證的斷言 |
|---|---|---|---|
| research agent 的身分檢查在改寫時遺失 | guardrail 寫在各自的 dispatch 裡 | Guardrail 宣告在 Agent 上，由同一個 middleware 執行 | 情境 B：別人的訂單被攔下，tool 本體未執行 |
| coding agent 重新出現配對錯誤 | 配對修正只在某一份 loop 裡 | 配對不變式只存在於 Runner 一處 | 五個 run 的 `paired()` 全部成立 |
| 三個 agent 算出三種用量 | 各自從不同地方計算 | 用量只來自 `model_response` 事件；預算是共用 middleware | 情境 D：用量與停止點可預測 |
| 敏感輸入寫進資料庫 | 檢查發生在落地之後 | `before_run` 在 `user_message` 之前 | 情境 C：session 中沒有使用者訊息 |

這段程式刻意沒有做的事也要列清楚。Runner 是同步、序列執行的，沒有串流、平行 tool call、取消與重試，這些是第 24 章 `loom.runtime` 的工作；模型直接用 ScriptedModel，provider adapter 與 routing 在第 25 章；重複呼叫偵測沒有搬進來，第 24 章會把它做成 loop guard；output guardrail 的位置已經定好（`wrap_model` 中檢查沒有 tool call 的回應），但沒有實作；handoff 一律帶完整歷史，第 20 章的過濾策略可以做成 Handoff 的一個選用欄位；Session 是記憶體版，換成第 22 章的事件日誌時要補上並行控制。核心約 220 行，加上三個 middleware 約 260 行，維持在「一個下午讀得完」的範圍內。

## 23.13 實務應用

核心抽象與擴充點的設計，在不同組織中會長成不同的樣子。以下四個情境說明本章的原則怎麼落地。

**情境一：青鳥三個 agent 遷移到 loom v0.5**。遷移的順序是先統一最容易出事的部分：三個團隊第一週只做一件事，把各自的 loop 換成 `Runner.run()`，並掛上同一組全域 middleware（稽核日誌、租戶預算、全域 guardrail）；agent 專屬的邏輯先原封不動包成 Tool 或 Agent 上的 guardrail。客服 agent 的核准流程變成 `loom.approval` 的 `wrap_tool` middleware；coding agent 的 sandbox 設定仍是 tool 層的事，但「哪些指令要核准」移到 guardrail 宣告；research agent 的事件日誌改成實作 Session 介面。遷移期間 `loom.compat` 讓舊的呼叫方式繼續運作，CI 裡統計 DeprecationWarning 的數量，降到零才移除相容層。

**情境二：金融或保險公司的內部 agent 平台**。受監管的組織最在意的是「每一個 agent 都一定有稽核紀錄、都一定過資料外洩檢查」。這類平台團隊通常不會讓各業務團隊自由組裝 middleware，而是提供一個「已經掛好強制 middleware 的 Runner 工廠」，業務團隊只能在後面追加自己的 middleware，不能移除前面的。事件 schema 也會被當成稽核資料的格式，版本變更要經過審查，upcaster 要有測試。這和 Microsoft Agent Framework 強調的企業功能（middleware、telemetry、session）方向一致；託管平台如 Amazon Bedrock AgentCore 則把 policy 做成平台層的確定性管控，與框架無關。

**情境三：在 SaaS 產品中內嵌 agent 的新創**。團隊小、模型常換、要快速出貨。這時自建完整框架不划算，比較好的做法是 23.2 節的第二列：直接用一個主流 SDK，再寫一個很薄的內部套件，只包含自家的 middleware（租戶預算、PII 遮蔽）、Session 實作（接自家資料庫）與 tool 定義。本章的抽象對照表在這裡的用途是避免 lock-in：內部套件的介面用 loom 這種中性的概念命名，SDK 只出現在 adapter 裡；哪天要換 SDK，改的是 adapter，不是業務程式。OpenAI Agents SDK 與 Pydantic AI 都支援自訂 model provider 與 session 後端，這類需求通常能在擴充點內解決。

**情境四：開發者工具公司提供給客戶擴充的 agent**。例如 IDE 或 coding agent 產品，讓使用者自己寫 hook 來阻擋危險指令、在每次修改檔案後自動跑格式化。這裡的擴充點是對外的公開 API，向後相容的要求最高：一個 hook 的簽名改了，成千上萬個使用者的設定一起壞掉。公開資料中，Claude Code 與 Claude Agent SDK 的 hooks 以事件名稱與 JSON 輸入輸出定義，PreToolUse 類的 hook 可以阻擋 tool 執行；GitHub Copilot coding agent 的公開文件也提到 hooks 與自訂 agents。這類產品要特別注意 hook 的信任邊界：使用者 clone 下來的專案裡如果帶著 hook 設定，在使用者確認信任之前就不應該執行。

| 情境 | 核心要多厚 | 擴充點由誰寫 | 最重要的相容性 | 特別注意 |
|---|---|---|---|---|
| 青鳥內部三個 agent | 中（自建核心） | 內部團隊 | Session 事件 schema | 先統一全域 middleware，再遷移細節 |
| 受監管的企業平台 | 中，強制 middleware 不可移除 | 平台團隊＋業務團隊 | 稽核事件格式 | 事件 schema 變更要審查 |
| SaaS 新創 | 薄（SDK＋內部套件） | 產品團隊 | 內部套件介面 | SDK 只出現在 adapter，避免 lock-in |
| 開發者工具的公開 hooks | 厚（完整 harness） | 外部使用者 | hook 簽名與輸入輸出格式 | hook 的信任邊界與執行時機 |

「核心要多厚」沒有標準答案：外部使用者越多，核心越要穩定、擴充點越要少而精；需求變得越快，核心越要薄。

## 23.14 設計檢查清單

設計或審查一個 agent framework 時，逐項回答下面的問題。

1. 是否有兩個以上的 agent 會使用這個 framework？必須一致的行為（稽核、預算、guardrail、租戶隔離）是否已經列成清單？
2. 每個核心抽象是否都說得出它保護的不變式？是否至少有兩種實作或用法？
3. Agent 與 Tool 是否是不可變的設定，不持有 model 連線或對話狀態？
4. 未標註副作用等級的 tool 是否預設為 destructive？有副作用的 tool 是否預設 `code_callable=False`？
5. tool 需要的身分與資源是否經由依賴注入傳入，而不是出現在模型看得到的 schema 裡？
6. 是否只有一個事實來源（事件），messages、trace、計費都從它投影？用量是否只有一種算法？
7. input guardrail 是否在輸入寫入 Session 之前執行？
8. 全域政策是否放在 Runner 層的 middleware，而不是只宣告在某個 Agent 上（handoff 後會失效）？
9. middleware 的順序是否寫進文件？觀察類是否在最外層、政策類是否最靠近動作？
10. middleware 丟出未預期例外時的語意是否明確？是否保證不會悄悄略過 guardrail？
11. 不論以哪種方式結束（含 middleware 中止），是否保證每個 tool call 都有對應結果？
12. 模組依賴是否只指向核心？第三方依賴是否只出現在最外圈的 adapter？是否有 CI 檢查保護？
13. 公開介面的邊界是否明確（`__all__`、底線命名）？建構子參數是否 keyword-only？
14. 事件是否帶 schema 版本？是否有 upcaster 與測試，保證舊事件永遠讀得回來？
15. 不相容的變更是否有 deprecation 期、明確的移除版本與遷移指南？安全相關的預設值是否只往保守方向改？

## 23.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 某個請求改了設定，其他請求的行為也跟著變 | Agent 是可變物件，被多個請求共用 | 搜尋對 Agent 欄位的賦值；看設定物件的 id 是否相同 | Agent 改成 frozen dataclass，變更一律用 `replace()` |
| handoff 之後，原本會被攔下的輸入通過了 | 全域政策只宣告在起點 Agent 上 | 看 `handoff` 事件之後是否還有對應的 guardrail 執行 | 全域政策改成 Runner 層的 middleware |
| 稽核紀錄中看不到被攔下的 tool call | guardrail middleware 排在 logging 外層 | 印出 middleware 順序；用 23.8 節的洋蔥測試重現 | 觀察類放最外層；或改用 `on_event` 記錄 `guardrail_tripped` |
| 加上 middleware 後放行的 tool 呼叫出現 RecursionError，短路的路徑卻正常 | 組 chain 時 closure 晚綁定迴圈變數，最外層的 nxt 指回自己 | 在每個 middleware 印出 self 與 nxt，發現 nxt 是同一個 closure | 用參數預設值或工廠函式把當下的值綁進 closure；測試涵蓋放行與短路 |
| 帳單與儀表板的用量對不起來 | 用量從多個地方各自計算 | 比對兩邊的資料來源與 cache tokens 的處理 | 用量只從 `model_response` 事件投影 |
| 升級後讀舊 session 時 KeyError | 事件欄位改名但沒有 upcaster | 看失敗事件的 `v` 與欄位 | 補 upcaster 與「讀最舊版本事件」的回歸測試 |
| 敏感資料出現在 log 或備份 | 輸入先寫進 Session 才檢查 | 搜尋被攔下的 run 是否仍有 `user_message` 事件 | input guardrail 移到 `before_run`，在落地之前執行 |
| 換了 tracing 套件後 agent 行為改變 | 觀察類 hook 能改變流程 | 檢查 hook 是否修改了 ctx 或回傳值被使用 | `on_event` 只能觀察；需要改流程的改寫成 `wrap_*` |

## 本章重點整理

- framework 和共用程式碼的差別，在於它把「必須一致」的行為收進核心，並為「必須不同」的行為提供明確的擴充點。
- 自建 framework 的好理由是多個 agent 的一致性需求加上現成 SDK 擴充點撐不住的限制；只有一個 agent 時，抽象沒有第二個使用者可以驗證。
- 最少抽象原則要求每個核心抽象都保護一個不變式、有兩種以上的實作或用法，而且概念在主流 SDK 之間穩定；能用組合表達的就不新增概念。
- loom v0.5 的八個核心抽象分成兩半：Agent、Tool、Handoff、Guardrail 是不可變的宣告；Runner、Session、Event 負責執行與狀態，middleware 在固定位置介入。
- tool 需要的身分與資源經由依賴注入傳入，不出現在模型看得到的 schema 中；未標註副作用等級的 tool 一律當 destructive。
- 事件是唯一的事實來源，messages、trace、計費都是它的投影；模型只看得到 user、assistant 與 tool 結果三種事件。
- input guardrail 必須在輸入寫入 Session 之前執行，否則被攔下的敏感資料已經落地。
- Handoff 與 Guardrail 升格為核心抽象，是因為它們保護了 tool 保護不了的不變式：只有一個 active agent、政策在固定位置一定執行。
- 掛在 Agent 上的 guardrail 在 handoff 後會失效，全域政策要放在 Runner 層的 middleware。
- middleware 採洋蔥模型，順序就是語意：觀察類在最外層、資源類在中間、政策類最靠近動作；`on_event` 只能觀察，不能改變流程。
- 模組依賴只能指向核心，第三方依賴只出現在最外圈的 adapter；第 24 章的 runtime 與第 25 章的 model adapter 都是實作核心介面的外掛。
- 向後相容的重點是劃清公開介面、只增不改、keyword-only 參數、明確的 deprecation 期，安全相關的預設值只能往保守方向改。
- 事件會被持久化，所以要帶 schema 版本並用 upcaster 逐版升級，保證舊事件永遠讀得回來。

## 延伸問答

> [!question]- Q1. 為什麼 loom v0.5 要把 Agent 設計成不可變的設定，而不是像 v0.1 那樣持有 model 與 messages 的物件？
> 因為設定與狀態的生命週期不同。Agent 設定在啟動時建立，被所有並行的對話共用；messages 只屬於一段對話。把兩者放在同一個物件裡，並行時就要加鎖或為每個請求複製整個物件，而且任何一個請求修改了設定（例如臨時調高步數上限），所有請求都會受影響，這種 bug 在測試中幾乎重現不了。
>
> 不可變的設定還帶來三個好處。第一，可以放進版本控制與 CI 檢查，例如列出每個 agent 能用的 destructive tool。第二，canary 與 A/B 只要用 `replace()` 產生新設定，不必複製類別。第三，除錯時可以確定設定從啟動到現在沒有變過，事件裡記下設定的版本就能完整重現一次 run。代價是使用者要接受「設定」與「執行」分開的心智模型，這也是 v0.1 到 v0.5 需要相容層的原因。

> [!question]- Q2. 一個需求要用 hook（例如 on_event）還是 middleware（wrap_tool）實作，怎麼判斷？
> 判斷標準是「它需不需要改變流程」。只需要知道發生了什麼的需求，例如寫日誌、產生 tracing span、累計計費、把事件推給前端，用 hook；需要檢查之後決定放行、拒絕、修改參數或改寫結果的需求，例如 guardrail、核准、idempotency key 注入、敏感資料遮蔽，用 middleware。
>
> 把兩者分開的理由是故障隔離。觀察類程式常由不同團隊維護，數量也多；如果它們也能改變流程，任何一個套件的 bug 都可能悄悄改變 agent 的行為。限制 hook 只能觀察，最壞的情況是少一筆紀錄，而不是多一筆退款。反過來，middleware 的數量要少、順序要寫進文件、每一個都要有測試，因為它們直接決定語意。

> [!question]- Q3. Guardrail 既然最後是由 middleware 執行，為什麼還要把它做成核心抽象，而不是讓使用者自己寫 middleware？
> 因為宣告與機制分開之後，guardrail 變成可以被檢查的資料。審查者可以直接從 Agent 設定列出「退款專員有哪些 tool guardrail」，CI 可以檢查「每個能用 destructive tool 的 agent 都至少有一條 tool guardrail」，事件裡的 `guardrail_tripped` 也能統一記錄 guardrail 名稱與 stage，方便統計誤判率。如果每個團隊各寫一個 middleware，這些檢查都做不到，執行時機與失敗語意也會不一致，23.1 節的事故就會再發生一次。
>
> 機制只有一份還有另一個好處：執行順序、短路方式、被攔時要回填什麼訊息、要不要寫事件，都在一個地方決定，修一次全部 agent 受惠。使用者仍然可以寫自己的 middleware 處理特殊情況，但最常見的三種位置（input、tool、output）由框架提供標準做法。

> [!question]- Q4. 你在 production 發現：使用者在對話第二輪貼上的卡號出現在資料倉儲裡，但第一輪貼卡號時有被正確攔下。可能的原因是什麼？怎麼排查？
> 最可能的原因是 guardrail 掛在起點 agent 上。第一輪由分流 agent 處理，它宣告了卡號檢查；第一輪中發生了 handoff，呼叫端依 `last_agent` 讓第二輪由退款專員開始，而退款專員沒有宣告這條 guardrail，於是卡號通過並寫進 session，再被同步到資料倉儲。23.12 節的程式就有這個性質：卡號檢查只在 triage 上。
>
> 排查時先找出那段 session 的事件，確認第二輪的 `run_started` 是哪個 agent，以及前面是否有 `handoff` 事件；再列出所有 agent 的 guardrail 宣告，看哪些「全域應該成立」的政策只出現在部分 agent 上。修法是把這類政策改成 Runner 層的 middleware，對所有 agent 生效；同時補一個回歸測試：任意 agent 開始的 run 遇到卡號都必須 blocked。已經落地的資料要依第 12 章的刪除流程處理，並檢查備份與衍生儲存。

> [!question]- Q5. 程式找錯：下面組 middleware 鏈的程式，為什麼一加上 middleware，tool 呼叫就出現 RecursionError？
> ```python
> def chain(middleware, terminal):
>     fn = terminal
>     for mw in reversed(middleware):
>         fn = lambda c: mw.wrap_tool(c, fn)
>     return fn
> ```
> 這是 Python closure 的晚綁定（late binding）：lambda 記住的是變數 `mw` 與 `fn` 本身，而不是建立 lambda 當下的值，要等到被呼叫時才去讀。迴圈結束後，`mw` 指向清單的第一個元素（因為是 reversed 迭代），`fn` 指向最後建立的那個 lambda 自己。呼叫鏈時，lambda 執行 `mw.wrap_tool(c, fn)`，而這個 `fn` 就是它自己；只要那個 middleware 呼叫 `nxt`，就會一直呼叫回自己，直到 RecursionError。只有一個 middleware 時也一樣會壞，所以不是「數量多才出錯」。
>
> 更麻煩的是，如果那個 middleware 剛好短路（例如 guardrail 攔下），它不會呼叫 `nxt`，測試看起來完全正常，只有放行的路徑才炸。修法是在建立 closure 的當下把值綁進去，例如 23.8 節的 `(lambda m, nxt: lambda c: m.wrap_tool(c, nxt))(mw, fn)`，或用預設參數 `lambda c, m=mw, nxt=fn: m.wrap_tool(c, nxt)`，或寫一個小的工廠函式。測試要同時涵蓋放行與短路兩條路徑，並像 23.8 節那樣記錄進出順序。

> [!question]- Q6. 面試追問：如果要讓 loom 支援 durable execution，又不想改任何 Agent 或 Tool 的程式碼，你會怎麼設計？
> 關鍵是 durable execution 需要的兩件事都已經有對應的擴充點。第一是持久化狀態：Session 介面只有 `load` 與 `append`，換成第 22 章的事件日誌實作，事件就會寫進資料庫，crash 後 `load()` 讀得回來。第二是重播時不重複執行外部呼叫：這要在 Runner 層處理，每次 model call 與 tool call 先查事件日誌有沒有對應的完成紀錄，有就直接用紀錄的結果。這是 runtime 與 `loom.durable` 之間的協定：第 24 章的 runtime 負責補齊 crash 時未完成的 tool call，第 22 章的 `loom.durable` 提供重播，第 45 章的 v1.0 把兩者組裝起來，Agent 與 Tool 都不需要知道。
>
> 要特別說明的限制有三個。tool 的副作用仍然需要 idempotency key，因為「執行完、寫紀錄前」的縫隙無法靠重播消除，這由 `intent_fields` 與 `wrap_tool` middleware 提供；middleware 本身必須是確定性的，例如預算檢查要依事件中的 usage，而不是依目前時間；事件 schema 要能演進，舊的日誌才能被新版本重播。Pydantic AI 把 durability 做成可抽換的後端，ADK 把 session 當成事件日誌，都是類似的思路。

> [!question]- Q7. 估算題：青鳥三個 agent 每天合計約 20 萬次 run，平均每次 run 產生 14 個事件，每個事件平均 1.5 KB（tool 結果較大的事件另存）。事件儲存每月需要多少空間？要注意什麼？
> 每天的事件量約 20 萬 × 14 ＝ 280 萬個，乘上 1.5 KB 約為 4.2 GB；一個月 30 天約 126 GB，一年約 1.5 TB，這還不含索引與備份。以資料庫的標準來看不算大，但成長是線性的，而且事件不能隨便刪：重播、稽核與評估都依賴它，所以要一開始就規劃保存期限與分層儲存，例如近 30 天放線上資料庫，之後轉到物件儲存。
>
> 更需要注意的是題目中的「另存」。tool 結果常常是事件裡最大的部分（報表、搜尋結果、檔案內容），如果直接內嵌，平均大小可能變成好幾倍。常見做法是事件只存結果的摘要、雜湊與引用，原始內容放物件儲存，和第 22 章的 payload 外存同一個思路。另外，事件裡可能含個資，保存期限要和第 12 章的刪除權一起設計：刪除請求要能找到並處理所有含該使用者資料的事件與外存內容。

> [!question]- Q8. 某團隊抱怨核准卡片太多，要求把 Tool 的 effect 預設值從 destructive 改成 read。你會怎麼回應？
> 不同意改預設值，但要解決對方的真實問題。預設值改成 read 是一個「不會報錯、只會悄悄改變行為」的不相容變更：所有沒標註等級的既有 tool，包括第 14 章接進來、不是自己寫的 MCP tool，會在升級後一夜之間變成不需要核准、可以從 code-as-action 呼叫。這違反了安全相關預設值只能往保守方向改的原則，也違反全書「未標註一律當 destructive」的規則。
>
> 真正的問題通常是很多唯讀 tool 沒有被標註。可以提供工具協助：在 CI 列出所有使用預設值的 tool，請擁有者逐一標註；在啟動時對使用預設值的 tool 發出警告；對 read tool 提供更簡潔的宣告方式。如果卡片多是因為核准粒度太細，那是第 21 章的核准政策問題，例如依金額分級或把核准綁在意圖上，應該在 approval middleware 中解決，而不是改動所有 tool 的預設安全等級。

## 延伸閱讀

- Anthropic Engineering Blog〈Building effective agents〉（2024）
- OpenAI Agents SDK 文件（Agents、Handoffs、Guardrails、Sessions 等章節）
- Google Agent Development Kit 文件（Runtime、Events、Callbacks 等章節）
- Microsoft Agent Framework 文件（Overview、Middleware 等章節）
- Joshua Bloch〈How to Design a Good API and Why it Matters〉（OOPSLA 2006 Companion）
- Titus Winters、Tom Manshreck、Hyrum Wright《Software Engineering at Google》（O'Reilly，2020），第 1 章關於 Hyrum's Law 的討論
- Tom Preston-Werner〈Semantic Versioning 2.0.0〉
- Martin Fowler〈Event Sourcing〉（2005）
