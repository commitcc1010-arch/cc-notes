---
chapter: 16
title: Computer Use 與 Browser Agent
part: 3
---

# 第 16 章　Computer Use 與 Browser Agent

> [!abstract] 本章地圖
> **核心問題**：當目標系統沒有 API、只有給人用的畫面時，怎麼讓 agent 可靠地操作它，而且在看錯、點錯、遇到登入與 CAPTCHA 時，不會造成無法挽回的後果？
>
> **你會學到**：
> - 判斷一個任務該走 API、結構化網頁工具、accessibility tree 還是截圖座標，並說出每一層的代價
> - 畫出 perception–action loop，說清楚「世界不會等模型想完」帶來的問題與對策
> - 比較截圖座標與 accessibility tree 兩種觀察方式在成本、穩健度、覆蓋範圍與安全上的取捨
> - 為每個動作設計等待、前置檢查、後置驗證與重試規則，區分可以重試與不能重試的動作
> - 用 checkpoint、副作用帳本與人工接手，讓長流程在遇到登入、CAPTCHA 或當機時能安全地暫停與續跑
> - 用純 Python 模擬一個會延遲載入、會跳版的網頁，親手量出兩種觀察方式的差異
>
> **前置知識**：第 4 章（agent loop、停止條件、RunResult 的 status）、第 5 章（tool 設計與副作用分級）、第 14 章（MCP：有 API 時優先走協定）

## 16.1 故事：一顆往下掉 48 像素的按鈕

青鳥科技的營運團隊每天要替商家處理物流異常：包裹遺失、毀損、延遲。第 14 章之後，大型物流商都已經透過 MCP 接進來，agent 可以直接呼叫 `file_claim` 建立申報。剩下一個麻煩：區域型的「山貓快遞」只提供網頁版商家後台，沒有 API；每天二、三十筆遺失申報，都是營運專員打開後台、點「遺失申報」、貼上託運單號與金額、按「送出申報」，再把案件編號抄回青鳥的工單。阿哲算過，這件事一個月吃掉一位專員將近一週的時間。

Iris 的第一版很直接：每一步把瀏覽器畫面截圖送給模型，模型回答「點 (120, 449)」，程式就用滑鼠點那個座標。前三筆都順利完成，大家很興奮。第四筆出事了：模型看完截圖、正在想下一步的那兩秒，後台頂端滑出一條「系統公告：今晚 23:00 維護」，把整個表單往下推了 48 像素。模型回答的座標原本是「送出申報」，現在落在上面那顆「取消此託運」上。幸好山貓快遞跳出了確認對話框，專員在旁邊看到，按了「否」。

那天下午又出了兩件小事。一是頁面剛載入時點「遺失申報」沒有反應，模型認定網站壞了，回報「無法完成」；其實只是頁面的腳本還沒接上，晚半秒再點就好。二是登入逾時，畫面跳回登入頁，模型很熱心地問：「請提供帳號密碼，我來登入。」隔天後台還加了 CAPTCHA，模型的回答是：「我可以嘗試辨識驗證碼。」資安的 Maya 當場把這兩句話截圖貼到頻道裡：「密碼不會進 context，CAPTCHA 也不會由 agent 去解。這兩條沒有討論空間。」

老陳看完 trace，下了一個結論：「API 有合約，網頁只有『它現在長這樣』。你的 loop 假設世界會停下來等模型想完，但網頁不會。」老陳列出 Iris 要補的東西：看畫面的方式要能抵抗跳版；每個動作前要等元素真的可以點，動作後要驗證結果真的發生；送出這種不可逆的動作要有人核准、而且絕不能重送；遇到登入與 CAPTCHA 要存檔、交給人、等人處理完再續跑。這一章就是 Iris 把這個 browser agent 從 demo 做到能每天跑的過程，第 16.10 節會用一個純 Python 模擬的山貓快遞後台，把上面四個事故全部重現並修好。

## 16.2 什麼時候該讓 agent 操作畫面

**computer use**（電腦操作）指的是讓模型透過「看螢幕、動滑鼠鍵盤」來使用電腦，就像人坐在電腦前一樣；例如模型收到一張桌面截圖，回答「在 (512, 300) 按左鍵」。**browser agent**（瀏覽器 agent）是範圍較窄的版本，只操作網頁瀏覽器；因為瀏覽器內部有結構化的頁面資料，browser agent 除了截圖之外，還可以讀取頁面元素、用元素而不是座標來下指令。兩者的共同點是：agent 面對的是**給人設計的介面**，而不是給程式設計的 API。

為什麼需要它？因為世界上大量的系統沒有 API，或 API 不開放給你：物流商與供應商的入口網站、政府申報系統、二十年前的內部 ERP、只能在桌面程式裡操作的會計軟體。另一類需求是**介面本身就是測試對象**：coding agent 改完前端，要像使用者一樣打開頁面點點看，才知道功能有沒有壞。這兩類需求都無法用「再寫一個 tool」解決，因為沒有後端可以接，或者你要驗證的正是前端。

但畫面是所有介面裡最貴、最脆弱的一種。同一個「建立遺失申報」的意圖，可以在四個層級完成，越往下越通用，也越慢、越貴、越容易壞：

```text
 同一個意圖：「替 TC-77120 申報遺失，金額 1800 元」

 層級 1  API／MCP tool        file_claim(tracking="TC-77120", amount=1800)
         1 次呼叫 · 有 schema · 錯誤有代碼 · 可加 idempotency key
            │ 沒有 API 才往下
            ▼
 層級 2  網站主動提供的        網頁宣告「我提供 submit_claim 這個工具」
         結構化工具            agent 直接呼叫，不必理解版面
            │ 網站沒提供才往下
            ▼
 層級 3  DOM／accessibility    fill([e5] 託運單號) → fill([e6] 金額) → click([e8] 送出)
         tree（元素層級）      數步 · 要等待與驗證 · 版面改了通常仍可用
            │ 沒有結構可讀（canvas、遠端桌面、原生程式）才往下
            ▼
 層級 4  截圖＋座標            screenshot → click(120,449) → type(...) → screenshot ...
         （像素層級）          最多步 · 每步一張圖 · 跳版、縮放、解析度都會點錯
```

這張圖由上往下讀。層級 1 是第 5 章與第 14 章的世界：一次呼叫、參數有 schema、錯誤有明確的意義，副作用可以用 idempotency key 保護。層級 2 是近年出現的方向：網站自己宣告一組給 agent 用的工具，agent 不必理解版面就能完成動作（2026 現況見 16.11 節的 callout）。層級 3 是本章的主角：透過瀏覽器自動化讀取頁面結構，用「哪一個元素」而不是「哪一個像素」下指令。層級 4 是最後手段：只有像素可用時（canvas 畫出來的介面、遠端桌面、原生桌面程式），才用截圖加座標。設計原則只有一句：**能往上走就不要往下走**；就算整個流程只有一步必須用畫面，其他步驟也應該盡量用上層的介面完成。

| 任務特徵 | 適合讓 agent 操作畫面 | 不適合，應該改用其他做法 |
|---|---|---|
| 目標系統 | 沒有 API 的供應商入口、舊系統、政府網站 | 有 API 或 MCP server 的系統 |
| 頻率與量 | 低到中頻、長尾、每次略有不同 | 高頻且步驟固定（改寫成確定性腳本或要求對方開 API） |
| 錯誤成本 | 可回復：草稿、查詢、可撤銷的申報 | 金流、刪除、對外發送且無法撤回 |
| 驗證方式 | 結果能在畫面或其他系統中被確認 | 結果看不到、只能相信 agent 說「完成了」 |
| 存取限制 | 允許自動化存取、帳號可專用且權限可縮小 | 服務條款禁止自動化、需要個人帳號與強驗證 |
| 延遲要求 | 背景工作、幾分鐘內完成即可 | 使用者在線上等、要求秒級回應 |

這張表其實是第 1 章「任務適合度三問」（開放、可驗證、可回復）在畫面操作上的展開。山貓快遞的遺失申報剛好落在左欄：沒有 API、每天幾十筆、申報可以撤回、案件編號能在後台查到、不需要即時回應。反過來，如果是每天上萬筆的出貨單匯入，正確的做法是去談 API，或至少把流程錄成確定性腳本，而不是讓模型每天看幾萬張截圖。

> [!warning] 常見誤解
> 「computer use 是萬用轉接頭，有了它就不必再做 API 整合。」它確實能接上任何有畫面的系統，但每一步的成本、延遲與失敗率都比 API 高出一個數量級以上，而且對方改版就可能整個失效。把它當成「沒有 API 時的橋」，並在橋旁邊持續推動真正的整合，才是可長可久的做法。

## 16.3 Perception–action loop：世界不會等模型想完

**perception–action loop**（感知—行動迴圈）是 computer use 的核心節奏：觀察畫面、決定動作、執行動作、再觀察結果。它和第 4 章的 agent loop 是同一個 loop，差別在於 tool 的回傳值不再是一個函式的結果，而是**環境當下的狀態**。第 4 章的 `get_order` 是「呼叫才會動」的函式；網頁卻是「自己會動」的環境：網路回應、動畫、計時器、別人推送的公告，都會在 agent 沒有任何動作時改變畫面。

```text
 ┌──────────────────────────── Harness（browser agent 的外殼）─────────────────────────────┐
 │                                                                                        │
 │  (1) Observer ──── 觀察：截圖／accessibility tree／兩者混合 ───────────────► Model     │
 │        ▲                                                                       │       │
 │        │                                                (2) 動作提議：click(e8)│       │
 │        │                                                    或 click(120,449)  ▼       │
 │        │   (6) Recorder ◄── (5) Verifier ◄── (4) Executor ◄── (3) Guard               │
 │        │       trace、         預期結果有沒有   等待元素可用      人工專用畫面？        │
 │        │       checkpoint、    真的出現？       再點、再打字      不可逆動作要核准？     │
 │        │       副作用帳本                                         目標還是同一個元素？   │
 │        │                                             │                     │           │
 └────────┼─────────────────────────────────────────────┼─────────────────────┼───────────┘
          │                                             ▼                     ▼
          └──────────────────────────── 瀏覽器／VM（環境，自己會變） ◄── 真人接手通道
```

逐一看這張圖的六個元件。(1) Observer 把環境轉成模型讀得懂的觀察，16.4 節會比較三種形式。(2) 模型根據觀察提出一個動作，可能是元素層級（點 `e8`）或像素層級（點 (120, 449)）。(3) Guard 在執行前把關：畫面是不是登入頁或 CAPTCHA、這個動作是不是不可逆、要點的目標是不是還是模型看到的那一個。(4) Executor 等待元素真的可以操作，才送出點擊或鍵入。(5) Verifier 檢查這個動作預期的結果有沒有在環境中出現，而不是相信模型說「我點了」。(6) Recorder 寫下 trace、存 checkpoint、記錄已經發生的副作用。右下角的真人接手通道，是 16.7 與 16.8 節的主題：有些畫面本來就該由人處理。

這個 loop 最容易被忽略的性質是：**模型做決定所根據的觀察，在動作發生時可能已經過期**。這叫**stale observation**（過期觀察）。模型處理一張截圖往往要好幾秒，這段時間裡網頁可能載入了新內容、跑完了動畫、彈出了公告。下面的時序圖就是 Iris 的第四筆申報：

```text
 時間 ─────────────────────────────────────────────────────────────────────────►
      t=0ms            t=300ms                     t=2,500ms        t=2,800ms
 harness  截圖 ───────► 送給模型                                     依座標點擊 (120,449)
                                                                       │
 模型               │◄────────── 讀圖、推理，約 2.5 秒 ─────────►│ 回答「點 (120,449)，
                                                                    那是送出申報」
 網頁     「送出申報」在 y=428–468                  公告滑入（300ms 動畫）
                                                    整頁往下推 48px
                                                    「取消此託運」移到 y=428–468
                                                                       │
 結果                                                                  ▼
                                                     點到的是「取消此託運」
```

時序圖由左到右讀。t=0 時 harness 截圖，那一刻「送出申報」確實在 y=428 到 468 之間。截圖送給模型後，模型花了約 2.5 秒才回答。就在這段時間裡，公告從頂端滑入，把整個表單往下推 48 像素，原本在上方的「取消此託運」剛好移到舊座標。harness 依照過期的座標點下去，點到了另一顆按鈕。注意這裡沒有任何一方犯錯：模型看圖看得很準，harness 也忠實執行了指令，問題出在「觀察」與「動作」之間的時間差。

對策有三類，本章會逐一實作。第一類是**晚綁定**（late binding）：模型只說「點送出申報這個元素」，由 harness 在動作的那一刻才去找它現在在哪裡，這是 accessibility tree 模式天生的優勢（16.4、16.5 節）。第二類是**動作前檢查**：真的要用座標時，點擊前先問瀏覽器「這一點上現在是什麼元素」，不是預期的就不點，重新觀察（16.5 節）。第三類是**動作後驗證**：每個動作都宣告預期的結果，harness 等它出現才算成功（16.6 節）。三者疊在一起，才能把「看錯一次就闖禍」變成「看錯一次就多花一步」。

## 16.4 觀察：截圖、DOM 與 accessibility tree

模型看不到瀏覽器，它只看得到 harness 給它的**觀察**（observation）。觀察的形式決定了 agent 能看到什麼、會被什麼騙、每一步要花多少錢。主流有三種形式，外加混合用法。

**截圖**（screenshot）是最直覺的形式：把畫面拍成影像交給具備視覺能力的模型。它的好處是「人看到什麼，模型就看到什麼」，連 canvas 畫出來的圖表、遠端桌面、桌面程式都能處理；壞處是每一步都要付一張圖的 token，而且模型必須從像素裡推論出「哪裡可以點」，輸出的動作只能是座標。

**DOM**（Document Object Model，文件物件模型）是瀏覽器把 HTML 解析成的樹狀結構，每個節點是一個標籤，例如 `<button class="btn btn-primary">送出申報</button>`。把原始 DOM 丟給模型看起來很完整，實際上充滿對 agent 沒用的東西：樣式 class、追蹤屬性、看不見的節點、上千個排版用的 `div`。一個普通的商家後台頁面，原始 HTML 動輒幾十萬字元。

**accessibility tree**（無障礙樹）是瀏覽器為螢幕閱讀器等輔助科技算出來的另一棵樹：它從 DOM 出發，丟掉純排版與看不見的節點，為每個有意義的節點算出三樣東西：**role**（角色，例如 button、textbox、link、heading）、**accessible name**（無障礙名稱，例如按鈕上的字、輸入框的 label、圖片的替代文字），以及**state**（狀態，例如 disabled、checked、expanded）。視障使用者用螢幕閱讀器「聽」網頁時，聽到的就是這棵樹：「按鈕，送出申報，不可用」。因為它本來就是為「不看畫面也能操作」而設計的，所以非常適合給 agent 當觀察。

下面的程式模擬 harness 把一個頁面轉成 accessibility tree 的文字表示，並為每個節點配一個短代號 **ref**（參照，例如 `e8`），讓模型可以用「點 e8」來下指令，而不必講座標。

```python
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Node:
    tag: str                      # 原始 HTML 標籤
    role: str                     # 瀏覽器算出的 accessibility role
    name: str                     # accessible name：label、aria-label 或文字內容
    box: tuple[int, int, int, int]  # x, y, w, h（CSS 像素）
    depth: int = 0
    hidden: bool = False          # display:none 或 aria-hidden
    disabled: bool = False
    value: str = ""
    css: str = ""                 # 對 agent 沒用、卻很佔空間的樣式與屬性


PAGE = [
    Node("nav", "navigation", "", (0, 0, 1280, 64), 0, css="class='nav nav-dark sticky' data-v-3f2a"),
    Node("img", "img", "", (16, 12, 120, 40), 1, css="src='/static/logo.8c1e.svg'"),   # 裝飾圖，沒有 alt
    Node("a", "link", "遺失申報", (1040, 20, 96, 24), 1, css="class='nav-link' href='/claims/new'"),
    Node("main", "main", "", (0, 64, 1280, 736), 0),
    Node("h1", "heading", "遺失／毀損申報", (40, 88, 400, 40), 1),
    Node("input", "textbox", "託運單號", (40, 160, 320, 40), 1, css="class='form-control' id='f-3'"),
    Node("input", "textbox", "申報金額（元）", (40, 220, 320, 40), 1, css="class='form-control' id='f-4'"),
    Node("div", "generic", "", (40, 280, 320, 40), 1, hidden=True, css="class='toast' style='display:none'"),
    Node("button", "button", "取消此託運", (40, 380, 160, 40), 1, css="class='btn btn-outline-danger'"),
    Node("button", "button", "送出申報", (40, 428, 160, 40), 1, disabled=True, css="class='btn btn-primary'"),
]


def raw_dom(nodes: list[Node]) -> str:
    """模擬把 HTML 原封不動丟給模型：標籤、class、樣式全都在。"""
    return "\n".join("  " * n.depth + f"<{n.tag} {n.css} style='left:{n.box[0]}px;top:{n.box[1]}px'>{n.name}</{n.tag}>"
                     for n in nodes)


def a11y_tree(nodes: list[Node]) -> tuple[str, dict[str, Node]]:
    """只留下「使用者看得到、能互動或有語意」的節點，並給每個節點一個短 ref。"""
    lines, refs = [], {}
    for n in nodes:
        if n.hidden or (n.role in ("generic", "img") and not n.name):
            continue                              # 看不到的、純裝飾的都不給模型
        ref = f"e{len(refs) + 1}"
        refs[ref] = n
        state = " disabled" if n.disabled else ""
        value = f" value={json.dumps(n.value, ensure_ascii=False)}" if n.role == "textbox" else ""
        label = f"「{n.name}」" if n.name else ""
        lines.append("  " * n.depth + f"[{ref}] {n.role}{label}{value}{state}")
    return "\n".join(lines), refs


tree, refs = a11y_tree(PAGE)
print(tree)
print(f"\n原始 DOM {len(raw_dom(PAGE))} 字元 → accessibility tree {len(tree)} 字元")
print("e8 指向：", refs["e8"].name, refs["e8"].box)
assert "toast" not in tree and "logo" not in tree           # 隱藏與裝飾節點被濾掉
assert refs["e8"].name == "送出申報" and refs["e8"].disabled
assert len(tree) < len(raw_dom(PAGE)) / 2
```

```text
[e1] navigation
  [e2] link「遺失申報」
[e3] main
  [e4] heading「遺失／毀損申報」
  [e5] textbox「託運單號」 value=""
  [e6] textbox「申報金額（元）」 value=""
  [e7] button「取消此託運」
  [e8] button「送出申報」 disabled

原始 DOM 712 字元 → accessibility tree 180 字元
e8 指向： 送出申報 (40, 428, 160, 40)
```

輸出的前八行就是模型會看到的觀察。每一行是一個節點：方括號裡是 ref，接著是 role，「」裡是 accessible name，最後是狀態；縮排代表樹的層級，例如「遺失申報」連結在 navigation 底下。比較兩份資料：原始 DOM 裡有 logo 圖片、一個 `display:none` 的提示框，以及一堆 class 與座標樣式，在 accessibility tree 裡全部消失，長度從 712 字元縮到 180 字元。最後一行示範 ref 的用途：`e8` 對回「送出申報」這個節點，而且 harness 知道它目前是 disabled，在模型提出「點 e8」時，可以直接告訴它「這顆按鈕還不能按」，而不是讓它對著一顆灰色按鈕反覆點擊。真實頁面的壓縮比例差異很大，但方向一致：只留下使用者能感知、能互動的部分。

```text
 每一步送給模型的觀察（context 版面）

 截圖模式                                    accessibility tree 模式
 ┌────────────────────────────────────┐      ┌────────────────────────────────────┐
 │ system：你是山貓快遞後台的操作助理 │      │ system：你是山貓快遞後台的操作助理 │
 │ tools：click(x,y) type(text)       │      │ tools：click(ref) fill(ref,text)   │
 │        key(k) scroll(dy)           │      │        wait_for(text)              │
 ├────────────────────────────────────┤      ├────────────────────────────────────┤
 │ 任務：替 TC-77120 申報遺失         │      │ 任務：替 TC-77120 申報遺失         │
 │ [圖] 第 1 步截圖   ← 舊圖可丟棄    │      │ 第 1 步：[e2] link「遺失申報」…    │
 │ [圖] 第 2 步截圖   ← 舊圖可丟棄    │      │ 第 2 步：[e5] textbox「託運單號」… │
 │ [圖] 第 3 步截圖（最新）           │      │ 第 3 步：完整的最新 tree           │
 │   每張圖的成本固定、和內容無關     │      │   成本隨頁面複雜度變化             │
 │   動作只能用座標表達               │      │   動作直接指名元素                 │
 └────────────────────────────────────┘      └────────────────────────────────────┘
```

這張版面圖對照兩種模式在 context 裡的樣子。上半部是穩定前綴：system 指令與 tool 定義，兩種模式都一樣要放在最前面以利 prompt caching（第 9 章）。差別在下半部。截圖模式每一步都附一張圖，圖的 token 數只取決於解析度、與內容無關，歷史越長、圖越多，所以實務上常只保留最近幾張，舊圖換成一行文字摘要。accessibility tree 模式每一步附一段文字，長度隨頁面複雜度變化；舊的 tree 同樣可以只留摘要，最新那份保留完整。另一個關鍵差異在 tools：截圖模式的動作只能用座標表達，accessibility tree 模式可以直接指名元素。

| 維度 | 截圖＋座標 | 原始 DOM | accessibility tree | 混合（tree 為主，按需截圖） |
|---|---|---|---|---|
| 每步 token | 每張圖固定上千，與內容無關 | 極大，常需大幅裁剪 | 中，隨頁面複雜度變化 | 平常同 tree，必要時加一張圖 |
| 動作表達 | 座標，受縮放與跳版影響 | 選擇器（CSS、XPath），易因改版失效 | ref 或 role＋name，晚綁定 | 以 ref 為主 |
| 版面變動時 | 容易點錯 | 選擇器可能失效 | 通常仍可用 | 通常仍可用 |
| 覆蓋範圍 | 任何畫面：canvas、遠端桌面、桌面程式 | 只限網頁 | 只限有結構的介面；無障礙做得差的網站會缺名稱 | 兩者互補 |
| 視覺資訊 | 看得到顏色、圖示、圖表、排版 | 看不到實際呈現 | 看不到；只知道語意 | 需要時看得到 |
| 隱藏內容風險 | 只看到可見內容 | 會讀到隱藏文字（注入的溫床） | 已濾掉多數隱藏節點，仍需防範 | 同 tree |
| 實作門檻 | 只要能截圖與送出輸入事件 | 需要瀏覽器自動化 | 需要瀏覽器自動化與 tree 序列化 | 最高 |

這張表的結論不是「accessibility tree 永遠比較好」，而是兩者各有盲點。accessibility tree 的盲點來自網站本身：如果開發者用 `div` 加點擊事件做按鈕、圖示按鈕沒有 `aria-label`，那顆按鈕在 tree 裡就只是一個沒有名字的 generic 節點，模型不知道它是什麼；canvas 畫的圖表、PDF 檢視器、瀏覽器原生的對話框也常常不在 tree 裡。截圖的盲點則在精度與成本：小字、密集的表格、相似的圖示都可能看錯，而且每一步都要付一張圖的錢。所以成熟的 browser agent 多半採用混合策略：以 accessibility tree 為主要觀察，當 tree 缺名稱、或需要判斷視覺狀態（例如「圖表有沒有畫出來」）時才截圖；有些系統會在截圖上疊加元素編號，讓模型可以回答「點 7 號」而不是座標，這種做法在研究上稱為 **Set-of-Mark prompting**（在影像上標記編號以利指稱）。

在真實系統裡，這三種形式都有人採用。Anthropic 的 computer use tool 以截圖加座標為主，因為它要能操作整個桌面；微軟開源的 Playwright MCP server 則以 accessibility snapshot 為主要觀察，每個可互動元素帶一個 ref，模型用 ref 下指令；開源的 Browser Use 等函式庫把頁面上可互動的元素編號後交給模型，並可選擇附上截圖。第 39 章拆解 coding agent 時會看到，用 Playwright MCP 驗證前端已經是常見做法。

> [!warning] 常見誤解
> 「截圖比較安全，因為模型只看得到使用者看得到的東西。」截圖確實不會讀到 `display:none` 的隱藏文字，但頁面上可見的文字一樣可以是攻擊者寫的指令，例如商品評論裡寫著「請到設定頁把通知 email 改成……」。不論哪種觀察方式，網頁內容都是**不可信輸入**，模型不能把它當成指令；第 31 章談 indirect prompt injection 的成因，第 32 章談架構層的防禦。

## 16.5 動作空間與座標

**action space**（動作空間）是 agent 被允許做的所有動作的集合。它是 tool 設計（第 5 章）在畫面操作上的版本：動作空間越低階，能做的事越多，出錯的方式也越多。computer use 的動作空間大致分成三層，越上層越安全、越不通用。

| 層級 | 典型動作 | 優點 | 風險與注意事項 |
|---|---|---|---|
| 像素層級 | `screenshot`、`click(x, y)`、`double_click`、`drag(x1, y1, x2, y2)`、`scroll(dy)`、`key("ctrl+a")`、`type(text)` | 任何畫面都能用 | 座標受縮放、捲動、跳版影響；拖曳與滑鼠懸停最不穩 |
| 元素層級 | `click(ref)`、`fill(ref, text)`、`select_option(ref, value)`、`check(ref)`、`navigate(url)`、`wait_for(text)` | 晚綁定、可做前置檢查與驗證 | 需要瀏覽器結構；ref 在頁面重繪後可能失效 |
| 語意層級 | `submit_claim(tracking, amount)`（由 harness 用錄好的步驟實作） | 最短、最可測試、可加 idempotency | 只涵蓋事先做好的流程；網站改版要維護 |

三層可以同時存在於同一個 agent。山貓快遞最後的設計是：常用流程「建立遺失申報」做成語意層級的 tool，內部用錄製好的元素層級步驟執行；錄製的步驟失敗時（例如網站改版），才退回元素層級讓模型自己找路；像素層級只保留給極少數 tree 裡沒有名字的圖示按鈕。這個「先走確定性路徑、失敗才交給模型」的分層，在 16.9 節談成本時會再出現。

座標動作有幾個很具體的陷阱。第一是**縮放**：為了省 token，送給模型的截圖常常比實際螢幕小，例如螢幕是 1440×900，截圖縮成 1024×640；模型回答的是截圖上的座標，harness 必須換算回螢幕座標再點。第二是**裝置像素比**（device pixel ratio）：高解析度螢幕上，一個 CSS 像素可能等於兩個實體像素，截圖的像素與瀏覽器的座標系不一定相同。第三是**捲動與 iframe**：元素的座標是相對於視窗、頁面還是內嵌框架，要說清楚。第四就是 16.3 節的**跳版**，網頁效能指標裡稱為 layout shift：載入中的圖片、廣告、公告把內容往下推。下面的程式把縮放與跳版兩個陷阱放在一起重現。

```python
from __future__ import annotations

SCREEN = (1440, 900)                       # 實際螢幕（CSS 像素）
SHOT = (1024, 640)                         # 送給模型的截圖：縮小以省 token
BUTTONS = {"取消此託運": [40, 380, 160, 40], "送出申報": [40, 428, 160, 40]}


def hit_test(x: int, y: int) -> str:
    """回傳 (x, y) 這一點上最上層的元素名稱。"""
    for name, (bx, by, w, h) in BUTTONS.items():
        if bx <= x < bx + w and by <= y < by + h:
            return name
    return "（空白處）"


def model_sees(name: str) -> tuple[int, int]:
    """模擬視覺模型：在縮小後的截圖上找到按鈕，回答它的中心點（截圖座標）。"""
    bx, by, w, h = BUTTONS[name]
    sx, sy = SHOT[0] / SCREEN[0], SHOT[1] / SCREEN[1]
    return round((bx + w / 2) * sx), round((by + h / 2) * sy)


def to_screen(x: int, y: int) -> tuple[int, int]:
    """把截圖座標換回螢幕座標；漏掉這一步是最常見的座標錯誤。"""
    return round(x * SCREEN[0] / SHOT[0]), round(y * SCREEN[1] / SHOT[1])


x, y = model_sees("送出申報")
print(f"模型在截圖上回答：({x}, {y})")
print(f"  忘了換算直接點 → {hit_test(x, y)}")
print(f"  換算成 {to_screen(x, y)} 再點 → {hit_test(*to_screen(x, y))}")

# 版面在「截圖之後、點擊之前」變了：頂端插入 48px 高的系統公告
x, y = to_screen(*model_sees("送出申報"))
for box in BUTTONS.values():
    box[1] += 48
print(f"公告出現後，同一個座標 ({x}, {y}) → {hit_test(x, y)}")

assert hit_test(*to_screen(*model_sees("取消此託運"))) == "取消此託運"
assert hit_test(x, y) == "取消此託運"      # 舊座標落在被推下來的另一顆按鈕上
```

```text
模型在截圖上回答：(85, 319)
  忘了換算直接點 → （空白處）
  換算成 (120, 449) 再點 → 送出申報
公告出現後，同一個座標 (120, 449) → 取消此託運
```

第一行是模型在縮小後的截圖上找到的「送出申報」中心點 (85, 319)。第二行是最常見的 bug：harness 忘了換算，直接拿截圖座標去點真實螢幕，結果點在空白處；這種 bug 在開發者自己的螢幕上可能剛好不出現（截圖沒有縮放），換到不同解析度的 VM 才爆發。第三行換算成 (120, 449) 之後正確點到「送出申報」。最後一行重現 16.1 節的事故：版面在截圖之後被推下 48 像素，同一個座標落在「取消此託運」上。兩個 assert 鎖住這兩件事：換算正確時能點到對的按鈕，跳版後舊座標會點到另一顆。

晚綁定也有自己的陷阱：**stale ref**（失效的參照）。現代網頁框架常常在狀態改變時重新產生整段 DOM，模型看到的 `e8` 對應的節點可能已經被替換掉了。因此 harness 不應該把 ref 當成指向某個 DOM 節點的指標，而應該在觀察時記下它的語意特徵（role、name、在樹中的位置），動作當下再依這些特徵重新尋找；找不到、或找到不只一個，就回報模型並附上新的觀察。這和 Playwright 的 locator 是同一個思路：locator 描述「怎麼找到元素」，每次動作時才真正去找。

輸入文字也值得一提。逐鍵模擬鍵盤事件（`type`）最接近真人，但對中文很不友善：中文輸入法的選字過程無法用逐鍵事件可靠重現，而且逐鍵輸入很慢。元素層級的 `fill` 直接把整段文字設進輸入框並觸發相應事件，對中文與長文字都穩定得多；只有網站依賴逐鍵事件做即時驗證時，才需要退回逐鍵輸入。不論哪一種，輸入後都要讀回輸入框的值確認，這就是下一節的驗證。

## 16.6 等待、驗證與重試

網頁是非同步的。點下「遺失申報」之後，瀏覽器要發請求、等回應、執行腳本、畫出表單，每一段都需要時間，而且每次不同。更麻煩的是 **hydration**（水合）：許多網站先送出一份看起來完整的 HTML，再由 JavaScript 把事件處理接上去；在接上之前，按鈕看得到、卻點了沒反應。Iris 遇到的「點了遺失申報沒反應」就是這個現象。agent 如果不懂得等，就會在對的元素上做出無效的動作，然後得出錯誤的結論。

| 等待策略 | 做法 | 優點 | 缺點 |
|---|---|---|---|
| 固定 sleep | 每個動作後睡 2 秒 | 最簡單 | 太短會失敗、太長會浪費；兩者常同時發生 |
| 輪詢條件 | 每 250ms 檢查一次「某文字出現」，有逾時上限 | 只等必要的時間 | 要知道該等什麼條件 |
| 可操作性自動等待 | 動作前自動等元素：存在、可見、位置穩定、可用、不被遮擋 | 涵蓋多數「點太早」問題 | 檢查不到「事件處理還沒接上」 |
| 網路閒置 | 等一段時間內沒有網路請求 | 適合整頁載入 | 有輪詢或長連線的頁面永遠不閒置 |
| 讓模型重新觀察 | 動作失敗就回填新的觀察，讓模型決定 | 最有彈性 | 每次多花一輪模型呼叫 |

這五種策略不是互斥的，成熟的 harness 會疊著用。可操作性自動等待是第一道防線，Playwright 在每個動作前都會做這類檢查（元素已接上 DOM、可見、位置穩定、可接收事件、可用），這也是它常被認為比早期自動化工具穩定的原因之一。輪詢條件用在「我知道接下來應該出現什麼」的場合，例如送出後等「申報成功」。固定 sleep 只該用在沒有任何條件可等的少數情況，而且要記錄下來，因為它通常代表觀察手段不足。下面的程式用模擬時鐘實作「等到可以點為止」，不真的 sleep，所以測試又快又可重現。

```python
from __future__ import annotations

from dataclasses import dataclass


class Clock:
    """模擬時鐘：wait 只是把時間往前撥，不真的 sleep，所以測試可重現又快。"""
    def __init__(self) -> None:
        self.ms = 0

    def advance(self, ms: int) -> None:
        self.ms += ms


@dataclass
class Button:
    name: str
    appear_at: int          # 何時插入 DOM（非同步載入）
    enable_at: int          # 何時變成可按（例如表單驗證完成）
    moving_until: int       # 進場動畫結束前，位置還在變


def actionable(b: Button, now: int) -> str | None:
    """回傳不能點的原因；None 代表可以點。順序跟 Playwright 的 actionability 檢查同一個精神。"""
    if now < b.appear_at:
        return "尚未出現"
    if now < b.moving_until:
        return "位置還在變（動畫中）"
    if now < b.enable_at:
        return "disabled"
    return None


def wait_until_actionable(b: Button, clock: Clock, timeout: int = 3000, poll: int = 250) -> bool:
    deadline = clock.ms + timeout
    while True:
        reason = actionable(b, clock.ms)
        print(f"  t={clock.ms:>4}ms  {b.name}：{reason or '可以點'}")
        if reason is None:
            return True
        if clock.ms + poll > deadline:
            return False                     # 逾時：交回給 harness 決定重試或求助
        clock.advance(poll)


clock = Clock()
submit = Button("送出申報", appear_at=400, enable_at=900, moving_until=600)
print("情境一：元素晚一點才可用")
assert wait_until_actionable(submit, clock)
print(f"→ 等了 {clock.ms}ms 才點；固定 sleep(500) 會太早，sleep(3000) 則白等 {3000 - clock.ms}ms")

clock = Clock()
broken = Button("送出申報", appear_at=0, enable_at=10**9, moving_until=0)   # 必填欄位沒填，永遠 disabled
print("情境二：元素永遠不會可用")
assert not wait_until_actionable(broken, clock, timeout=1000, poll=500)
print("→ 逾時，回報『送出申報 一直是 disabled』給模型，而不是硬點下去")
```

```text
情境一：元素晚一點才可用
  t=   0ms  送出申報：尚未出現
  t= 250ms  送出申報：尚未出現
  t= 500ms  送出申報：位置還在變（動畫中）
  t= 750ms  送出申報：disabled
  t=1000ms  送出申報：可以點
→ 等了 1000ms 才點；固定 sleep(500) 會太早，sleep(3000) 則白等 2000ms
情境二：元素永遠不會可用
  t=   0ms  送出申報：disabled
  t= 500ms  送出申報：disabled
  t=1000ms  送出申報：disabled
→ 逾時，回報『送出申報 一直是 disabled』給模型，而不是硬點下去
```

情境一的五行輪詢紀錄，依序經歷了三個「還不能點」的原因：0 到 250ms 元素尚未插入頁面，500ms 時元素出現但進場動畫還在移動（這時點下去，座標可能落在別處），750ms 時位置穩定但表單驗證還沒完成而是 disabled，到 1000ms 才可以點。這說明了為什麼固定 sleep 不可靠：sleep(500) 會在動畫中點擊，sleep(3000) 則白等兩秒；每一頁、每一次載入的時間都不同。情境二是另一個重要的教訓：送出鈕因為必填欄位沒填而永遠 disabled，等待必須有上限，逾時後要把**原因**（「一直是 disabled」）回報給模型，模型才會想到「我是不是漏填了什麼」，而不是對著灰色按鈕硬點。

等到可以點只是一半，另一半是**驗證**（verification）：每個動作都要宣告它預期造成的結果，harness 到環境裡確認結果真的出現。點「遺失申報」的預期是出現「遺失／毀損申報」標題；填入託運單號的預期是輸入框的值變成 TC-77120；送出的預期是出現「申報成功」與案件編號。驗證的對象是環境，不是模型的自我報告，這和第 4 章「end_turn 只是模型的提議」是同一個原則。任務層級還要再驗證一次：申報送出後，到「我的申報」列表確認那一筆真的存在，必要時用其他管道（例如對方寄來的確認信）交叉比對。

驗證失敗之後要不要**重試**，取決於動作的性質。導航、填寫欄位、展開選單這類動作是可重做的：再做一次的結果和做一次相同（`fill` 是覆寫，不是附加），所以可以重新觀察、重新定位、再做一次，並設上次數上限。送出、付款、寄信、刪除這類動作則不能盲目重試：驗證失敗不代表動作沒發生，可能是送出成功了、只是成功畫面還沒出來，或網路在回應途中斷掉。這種狀態叫**結果不明**（unknown outcome），正確做法是先查證（到列表裡找那一筆），查不到才考慮重做，查證本身也失敗就交給人。注意重試的意思永遠是「重新觀察、重新定位」，不是「用同一個座標再點一次」；後者在跳版的情境下只會再點錯一次。

```text
 單一動作的狀態機

            ┌──────────────┐
            │   PROPOSED   │ 模型提出：click(e8)，預期「申報成功」
            └──────┬───────┘
                   ▼
            ┌──────────────┐  人工專用畫面 ─────────────► NEEDS_HUMAN
            │    GUARD     │  不可逆且未核准 ───────────► REJECTED（回報模型）
            └──────┬───────┘  已執行過（帳本有紀錄）────► REJECTED（不重送）
                   ▼
            ┌──────────────┐  逾時：找不到、一直 disabled
            │   LOCATING   │ ───────────────────────────► REPORT（回報原因＋新觀察）
            └──────┬───────┘
                   ▼ 存在、可見、穩定、可用
            ┌──────────────┐
            │    ACTING    │ 送出點擊／輸入
            └──────┬───────┘
                   ▼
            ┌──────────────┐  預期結果出現 ─────────────► OK（寫入 checkpoint）
            │  VERIFYING   │  逾時且動作可重做 ─────────► REPORT → 模型重新觀察後再試
            └──────────────┘  逾時且動作不可逆 ─────────► UNKNOWN → 先查證，查不到才交給人
```

這張狀態機是 16.10 節 harness 的骨架，由上往下走。GUARD 有三個出口：畫面是登入頁或 CAPTCHA 就暫停交給人；不可逆動作要先經過核准；副作用帳本裡已經有紀錄的不可逆動作一律不重送。LOCATING 對應前面的可操作性等待，逾時就把原因與新的觀察回報模型。ACTING 之後一定進 VERIFYING，三個出口分別是成功（寫入 checkpoint）、可重做的失敗（讓模型重新觀察再決定）、不可逆的失敗（標成結果不明，先查證）。整張圖最重要的一條規則是：**只有 VERIFYING 通過，才算這一步完成**；模型說「我點了」不算，harness 送出了點擊也不算。

## 16.7 登入、CAPTCHA 與敏感動作：交給人，不繞過

登入與 CAPTCHA 是 browser agent 一定會遇到、也最容易做錯的兩件事。本書的立場很明確，下面四條原則沒有例外。

第一，**憑證不進 context**。帳號密碼、一次性驗證碼、session cookie 都不能出現在模型看得到的任何地方：不在 prompt、不在觀察、不在 trace。理由有兩個：context 裡的東西可能因為 prompt injection 被帶出去（第 31 章的 data exfiltration），也會被寫進 log 與 trace，散布到你無法控制的地方。登入的做法依安全程度排序：最好是由真人在接手畫面中登入，agent 只接手已登入的 session；其次是由 harness 從 secrets 管理系統取出憑證、直接填入登入表單，模型只看到「已登入」這個結果（第 33 章談 secrets 管理）。不論哪種，帳號都應該是專用的、權限最小的服務帳號，而不是某位員工的個人帳號；多因素驗證由真人完成。

第二，**CAPTCHA 交給人，不嘗試解，也不找方法繞過**。CAPTCHA 的存在本身就是網站在說「這裡要真人」；讓模型辨識驗證碼、接第三方解碼服務、偽裝瀏覽器指紋去避開風控，都是在對抗網站的明確意圖，可能違反服務條款與法律，也會讓青鳥的帳號被封鎖。正確的處理是：偵測到 CAPTCHA 就暫停、存 checkpoint、通知真人在同一個瀏覽器 session 裡完成，再交回給 agent 續跑。如果 CAPTCHA 頻繁到影響營運，那是商務問題，不是技術問題：去和對方談 API、把青鳥的服務帳號列入對方的 allowlist（允許清單），或改走批次上傳的管道。同樣的精神也適用於服務條款與存取頻率：只自動化對方允許的操作，控制請求速度，不要讓 agent 對別人的網站造成負擔。

第三，**有後果的動作要人確認，而且確認的是「效果」**。送出申報、付款、寄信、接受條款、刪除資料，這些動作執行前要經過核准（第 21 章的 approval gate）。這裡有一個 computer use 特有的陷阱：核准的對象必須是 harness 確認過的實際目標，而不只是模型宣稱的意圖。純座標模式下，模型說「我要點送出申報」，專員按了核准，但點下去的是「取消此託運」；核准了意圖，卻沒有核准到效果。所以核准畫面應該顯示 harness 從環境查到的目標（元素名稱、所在表單、要送出的欄位值），最好附上一張標出目標位置的截圖。

第四，**網頁內容是資料，不是指令**。agent 在網頁上讀到的任何文字，包括看起來像系統通知的橫幅、評論區、隱藏欄位，都不能改變它的任務與權限。設計上的防線包括：限制 agent 可以造訪的網域（allowlist）、把「讀取不可信網頁」與「執行高權限動作」拆成不同階段或不同 agent、所有寫入動作都過核准。這些防禦的原理在第 32 章。

```text
 遇到 CAPTCHA 時的人工接手（時序）

 Agent／Harness            Checkpoint Store        真人（營運專員）         瀏覽器 session
     │── 送出申報（已核准）─────────────────────────────────────────────────►│
     │◄──────────────────────────────────────────────── 畫面：請完成人機驗證 ─│
     │ GUARD：人工專用畫面                                                  │
     │── 存檔：任務、已驗證步驟、                                           │
     │   副作用帳本「送出申報：結果不明」──►│                               │
     │── 通知：「TC-77135 需要人機驗證」────────────────►│                  │
     │   status=needs_human，釋放 worker                  │── 接手同一個 ───►│
     │                                                    │   session、完成驗證
     │                                                    │◄── 申報成功 ─────│
     │◄──────────────────────── 交回：「已完成驗證」───────│                  │
     │── 讀取 checkpoint ◄──────────────────│                               │
     │── 重新觀察（不沿用舊的 ref 與座標）──────────────────────────────────►│
     │◄──────────────────────────────────────── 畫面：申報成功 CL-5531 ───────│
     │ 驗證通過，帳本更新為「已完成，CL-5531」，status=done                 │
```

這張時序圖有四個值得注意的地方。第一，暫停是 harness 決定的，不是模型決定的：GUARD 一看到人機驗證的畫面就停，模型根本沒有機會「嘗試辨識」。第二，存檔的內容包含副作用帳本，而且把送出標成「結果不明」，因為 agent 不知道驗證完成後申報會不會自動成立。第三，真人接手的是**同一個瀏覽器 session**，不是重新開一個；否則表單內容與登入狀態都會遺失。第四，交回之後 agent 先重新觀察，不沿用暫停前的 ref 與座標，因為真人可能捲動了頁面、甚至換了分頁；看到「申報成功」之後，帳本才從結果不明更新為完成。

> [!note] 為什麼這些原則要寫在 harness，而不是 system prompt？
> 在 system prompt 寫「遇到 CAPTCHA 請停止」當然有幫助，但它是對模型的請求，不是保證。模型可能誤判畫面、可能被網頁上的文字說服，也可能在新版本中行為改變。人工專用畫面的偵測、不可逆動作的核准、憑證不進 context，這些都應該是 harness 的確定性邏輯；prompt 負責讓模型理解為什麼，程式負責保證一定做到。這是第 4 章「模型提議、harness 保證」在安全上的應用。

## 16.8 可靠性設計：checkpoint 與人工接手

一筆遺失申報大約十步，一次批次跑三十筆就是三百步。三百步裡，網站逾時、session 過期、CAPTCHA、worker 被重新部署，幾乎一定會發生其中一件。如果每次中斷都要從頭來，最糟的情況不是浪費時間，而是重複送出：第一次送出其實成功了，重跑時又送了一次。可靠性設計要回答三個問題：中斷時存什麼、續跑時怎麼確定從哪裡開始、哪些情況要交給人。

**checkpoint**（檢查點）是任務在某個時刻的可恢復狀態。browser agent 的 checkpoint 至少要有四樣東西：任務描述與參數；已經**驗證通過**的步驟清單（只記驗證過的，不記模型以為做過的）；**副作用帳本**（side-effect ledger），記錄每一個不可逆動作是否已執行、結果是什麼（例如「送出申報：已完成，CL-5531」或「結果不明」）；以及瀏覽器 session 的參照（cookie 與 storage 存在 secrets 管理系統或隔離的瀏覽器 profile 中，checkpoint 只存參照，不存內容）。不要存的東西也很重要：舊的截圖、ref 與座標都不該被當成續跑的依據，因為它們描述的是過去的畫面。

```text
 任務層級的狀態機（每筆申報一個）

                 ┌─────────┐  worker 取得任務、載入 checkpoint
     ┌──────────►│ RUNNING │◄──────────────────────────────┐
     │           └────┬────┘                               │
     │                │ 每個動作驗證通過 → 寫 checkpoint    │ 重新觀察、
     │                │                                    │ 對帳完成
     │   ┌────────────┼──────────────┬────────────────┐    │
     │   ▼            ▼              ▼                ▼    │
     │ ┌──────┐  ┌───────────┐  ┌──────────┐   ┌──────────┴─┐
     │ │ DONE │  │  FAILED   │  │ NEEDS_   │   │ RESUMING   │
     │ │      │  │（步數或預 │  │ HUMAN    │──►│ 讀帳本、到 │
     │ └──────┘  │ 算用盡，  │  │ 登入、   │人 │ 環境查證不 │
     │           │ 附 trace）│  │ CAPTCHA、│處 │ 可逆動作的 │
     │           └───────────┘  │ 結果不明 │理 │ 結果       │
     │                          └──────────┘完 └────────────┘
     │                               ▲
     └── worker 當機或重新部署 ───────┘（從最後一個 checkpoint 進 RESUMING）
```

這張狀態機描述一筆申報的一生。RUNNING 是正常執行，每個動作驗證通過就寫一次 checkpoint。從 RUNNING 有三個出口：DONE（任務驗證完成）、FAILED（步數或預算用盡，附上 trace 給人分析）、NEEDS_HUMAN（遇到登入、CAPTCHA，或不可逆動作結果不明）。NEEDS_HUMAN 不是失敗，而是一種等待狀態：真人處理完，任務進入 RESUMING。worker 當機或重新部署時，任務也從最後一個 checkpoint 進入 RESUMING。RESUMING 是整張圖的關鍵：它先讀副作用帳本，對每一個「已執行」或「結果不明」的不可逆動作，到環境裡查證實際結果，然後才回到 RUNNING。這個「先對帳、再前進」的順序，是避免重複送出的唯一可靠方法。第 22 章的 durable execution 會把同樣的概念推廣到所有長時間任務。

**人工接手**（human takeover）的使用者體驗決定了這套設計實際上好不好用。接手畫面要能即時看到 agent 正在操作的瀏覽器（live view），讓真人一鍵取得控制權，處理完再一鍵交回；交回時最好讓真人附一句說明（「已完成驗證」「這筆其實已經申報過了」），寫進 trace 與 checkpoint。對於敏感網站，有些產品採用「watch mode」：agent 在這類網站上操作時，要求使用者保持在畫面前觀看，使用者離開就暫停。接手通知要帶足夠的上下文：哪一筆任務、卡在哪一步、畫面截圖、agent 希望真人做什麼，否則真人要從頭理解一次，接手的成本會吃掉自動化的收益。

最後是隔離。每個任務應該跑在獨立的瀏覽器 profile 或容器裡，任務結束就丟棄，避免 A 商家的 session 被 B 商家的任務用到，也避免一個被惡意網頁污染的瀏覽器影響下一個任務。瀏覽器本身也是執行環境，第 17 章的 sandbox 原則（隔離、egress 控制、資源限制、secrets 不進 sandbox）全部適用；託管的瀏覽器服務通常就是把這一層做成雲端資源。

## 16.9 成本與延遲

computer use 的成本結構和第 4 章的客服 agent 很不一樣。客服 agent 一題三、五步，每步的 tool 結果是幾百字的 JSON；browser agent 一個任務十到數十步，每步的觀察是一張圖或一棵樹，而且因為每一步都要重送歷史，觀察的大小會被放大好幾倍。下表用一組明確的假設，估算一筆山貓快遞申報的觀察成本（數字是假設，不是量測；真正的數字請用自己的 trace 算）。

| 項目 | 截圖模式 | accessibility tree 模式 | 假設 |
|---|---|---|---|
| 每筆申報的步數 | 10 | 8 | 截圖模式多出捲動與確認畫面的步驟 |
| 每步觀察的 token | 約 1,400 | 約 600 | 截圖約 1280×800；tree 為中等複雜度頁面 |
| 每步帶入的歷史觀察 | 最近 3 張圖 | 最近 1 棵完整 tree＋舊步驟摘要 | 舊圖與舊 tree 改成一行摘要 |
| 每步 input 的觀察部分 | 約 4,200 | 約 600＋摘要 | 未計 system、tools 與動作紀錄 |
| 每筆申報的觀察 token 總量 | 約 4 萬 | 約 6 千 | 步數 × 每步 input |
| 每步延遲 | 數秒（看圖） | 1 到數秒 | 加上等待與驗證時間 |

這張表最重要的不是數字，而是三個結構性結論。第一，截圖的成本和頁面內容無關，一張幾乎空白的確認頁和一張密密麻麻的報表一樣貴；accessibility tree 的成本則隨頁面複雜度變化，簡單頁面便宜很多，但一張有上千列的表格可能比截圖還貴，所以 tree 也需要裁剪（只保留視窗內的節點、表格只給前幾列並註明總數）。第二，歷史觀察是成本的放大器：保留越多張舊截圖，每一步就越貴，而舊截圖的資訊價值通常很低；只保留最近幾張、其餘改成文字摘要，是最划算的優化。第三，延遲主要來自步數：每一步都要等模型、等網頁、等驗證，十步就是一分鐘起跳，所以 browser agent 天生適合背景工作，不適合讓使用者在線上等。

降低成本與延遲最有效的方法，往往不是讓每一步更便宜，而是讓模型參與的步數更少。一個常見的模式是**探索後固化**：agent 第一次走通流程時記錄下元素層級的步驟（哪個 role、哪個 name、填什麼值、預期什麼結果），之後的同類任務由 harness 直接重播這份確定性腳本，每一步照樣做等待與驗證，只有重播失敗時（例如網站改版、出現沒見過的對話框）才把模型叫回來接手，並在成功後更新腳本。這把大部分任務的模型呼叫從十次降到零次，同時保留應對變化的能力；代價是要維護腳本的版本，並且監控重播的失敗率，失敗率上升通常代表對方改版了。

| 優化手段 | 省下什麼 | 代價或風險 |
|---|---|---|
| 能用 API／結構化工具的步驟就不用畫面 | 整段畫面操作 | 要先盤點與整合 |
| accessibility tree 為主、按需截圖 | 每步觀察 token | tree 缺名稱時需要退回截圖 |
| 只保留最近幾張截圖，其餘改摘要 | 歷史觀察 token | 摘要可能漏掉需要回頭看的細節 |
| tree 只保留視窗內與可互動節點 | 大頁面的 token | 模型可能看不到需要捲動才出現的元素 |
| 探索後固化成腳本，失敗才交給模型 | 多數任務的全部模型呼叫 | 腳本維護與改版偵測 |
| 小型快速模型做例行步驟，前沿模型處理例外 | 單步成本與延遲 | 需要路由與升級規則（第 25 章） |

## 16.10 動手做：模擬山貓快遞後台，比較兩種觀察方式

這一節把前面所有機制寫成一個可以離線執行的程式。程式分成三部分。第一部分是 `Portal`：用純 Python 模擬山貓快遞的商家後台，它有一個模擬時鐘，並刻意做出 16.1 節的所有麻煩：頁面腳本在 600ms 前還沒接上（點擊會被吞掉）、送出鈕要等表單載入 800ms 後才出現、而且必填欄位填完才能按、系統公告會在指定時間滑入並把版面推下 48 像素、送出時可能要求人機驗證。第二部分是 `BrowserAgent`：實作 16.3 節的 Guard、Executor、Verifier 與 Recorder，支援三種模式：`ref`（accessibility tree＋晚綁定）、`xy`（截圖座標，直接點）、`xy_guard`（截圖座標，點擊前先 hit-test 確認目標）。第三部分是模擬的模型策略：用 ScriptedModel 的函式劇本，讀最新的觀察決定下一步，就像一個看得懂畫面、但不知道畫面之後會變的模型。

在座標模式下，觀察裡的 `@(x,y)` 代表「視覺模型從截圖讀出的元素中心點」：真實系統送給模型的是影像，這裡用文字模擬一個看得很準的視覺模型，以便把問題聚焦在時間差而不是辨識錯誤。`think_ms` 是模擬的模型思考時間，截圖模式設得比較長（影像輸入較大），這是模擬參數，不是量測值。

```python
from __future__ import annotations

import json
import random
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


# ───────── 環境：山貓快遞的商家後台（純 Python 模擬） ─────────
class Portal:
    def __init__(self, banner_at: int | None = None, captcha: bool = False, hydrate_at: int = 600):
        self.t, self.page = 0, "dashboard"
        self.banner_at, self.captcha, self.hydrate_at = banner_at, captcha, hydrate_at
        self.form_at = 0                                   # 表單開啟的時間
        self.values = {"託運單號": "", "申報金額": ""}
        self.focus: str | None = None
        self.events: list[str] = []                        # 真正發生的副作用

    def advance(self, ms: int) -> None:
        self.t += ms

    def shift(self) -> int:                                # 公告滑入動畫 300ms，最後把版面推下 48px
        if self.banner_at is None or self.t < self.banner_at or self.page not in ("dashboard", "form"):
            return 0
        return min(48, (self.t - self.banner_at) * 48 // 300)

    def elements(self) -> list[dict]:
        s, els = self.shift(), []
        def add(role, name, y, value=None, enabled=True):
            els.append({"role": role, "name": name, "box": (40, y + s, 160, 40), "value": value, "enabled": enabled})
        if s:
            els.append({"role": "status", "name": "系統公告：今晚 23:00 維護", "box": (0, 64, 1280, s),
                        "value": None, "enabled": True})
        if self.page == "dashboard":
            add("link", "遺失申報", 120)
        elif self.page == "captcha":
            add("heading", "請完成人機驗證", 120)
        elif self.page == "form":
            add("heading", "遺失／毀損申報", 88)
            add("textbox", "託運單號", 160, self.values["託運單號"])
            add("textbox", "申報金額", 220, self.values["申報金額"])
            add("button", "取消此託運", 380)
            if self.t >= self.form_at + 800:               # 送出鈕要等表單腳本載入完才出現
                add("button", "送出申報", 428, enabled=all(self.values.values()))
        elif self.page == "done":
            add("heading", "申報成功，案件編號 CL-5531", 88)
        elif self.page == "cancel_confirm":
            add("heading", "確定要取消這筆託運嗎？", 88)
        return els

    def element_at(self, x: int, y: int) -> dict | None:
        for el in reversed(self.elements()):
            bx, by, w, h = el["box"]
            if bx <= x < bx + w and by <= y < by + h:
                return el
        return None

    def activate(self, el: dict) -> None:
        if el["role"] == "textbox":
            self.focus = el["name"]
        elif el["name"] == "遺失申報" and self.t >= self.hydrate_at:   # 頁面腳本還沒接上前，點擊會被吞掉
            self.page, self.form_at = "form", self.t
        elif el["name"] == "取消此託運":
            self.page = "cancel_confirm"
            self.events.append("誤觸取消")
        elif el["name"] == "送出申報" and el["enabled"]:
            self.page = "captcha" if self.captcha else "done"   # 風控：送出時要求人機驗證
            if not self.captcha:
                self.events.append(f"建立申報 {self.values['託運單號']} {self.values['申報金額']}")

    def type_text(self, text: str) -> None:
        if self.focus:
            self.values[self.focus] = text

    def human_solves_captcha(self) -> None:               # 真人在接手畫面完成驗證，送出才真正生效
        self.page, self.captcha = "done", False
        self.events.append(f"建立申報 {self.values['託運單號']} {self.values['申報金額']}")


# ───────── Harness：觀察 → 決策 → 等待 → 動作 → 驗證 ─────────
HUMAN_ONLY = ("人機驗證", "請登入")                         # 出現就交給人，agent 不嘗試
IRREVERSIBLE = ("送出申報", "取消此託運")                    # 需要核准、而且不自動重送


class BrowserAgent:
    def __init__(self, model, portal: Portal, mode: str, think_ms: int, approve=lambda label: True,
                 max_steps: int = 12, verbose: bool = True):
        self.model, self.p, self.mode = model, portal, mode   # mode：ref｜xy｜xy_guard
        self.think_ms, self.approve, self.max_steps = think_ms, approve, max_steps
        self.refs: dict[str, tuple[str, str]] = {}
        self.trace: list[str] = []
        self.tokens, self.verbose = 0, verbose

    def log(self, line: str) -> None:
        self.trace.append(line)
        if self.verbose:
            print(line)

    def observe(self) -> str:
        els, lines, self.refs = self.p.elements(), [], {}
        for i, el in enumerate(els, 1):
            self.refs[f"e{i}"] = (el["role"], el["name"])
            val = f" value={json.dumps(el['value'], ensure_ascii=False)}" if el["value"] is not None else ""
            off = "" if el["enabled"] else " disabled"
            x, y, w, h = el["box"]
            where = f"[e{i}] " if self.mode == "ref" else ""
            at = f" @({x + w // 2},{y + h // 2})" if self.mode != "ref" else ""
            lines.append(f"{where}{el['role']}「{el['name']}」{val}{off}{at}")
        text = "\n".join(lines)
        self.tokens += len(text) // 2 if self.mode == "ref" else 1280 * 800 // 750   # 截圖約 W×H/750
        return text

    def locate(self, args: dict) -> tuple[dict | None, str]:
        if self.mode == "ref":                                # 動作當下才用 role＋name 重新找元素
            role, name = self.refs.get(args["ref"], ("?", "?"))
            for _ in range(20):                                # 最多等 2 秒：出現、穩定、可用
                el = next((e for e in self.p.elements() if (e["role"], e["name"]) == (role, name)), None)
                before = el and el["box"]
                self.p.advance(100)
                el = next((e for e in self.p.elements() if (e["role"], e["name"]) == (role, name)), None)
                if el and el["box"] == before and el["enabled"]:
                    return el, name
            return None, name
        el = self.p.element_at(args["x"], args["y"])          # 座標模式：點下去的就是那一點上的東西
        if self.mode == "xy_guard" and (el is None or el["name"] != args["label"]):
            return None, args["label"]                         # 點擊前 hit-test：目標不對就不點
        return el, args["label"]

    def act(self, tc: ToolCall, ckpt: dict) -> tuple[bool, str]:
        if tc.name == "wait_for":                              # 明確等待某個文字出現，有上限
            for _ in range(20):
                if tc.args["text"] in json.dumps(self.p.elements(), ensure_ascii=False):
                    return False, "OK"
                self.p.advance(100)
            return True, f"等了 2 秒仍沒出現「{tc.args['text']}」"
        el, label = self.locate(tc.args)
        if el is None:
            return True, f"找不到可點的「{label}」（可能還沒載入或版面變了），請依新畫面重新決定"
        if label in IRREVERSIBLE:                              # 核准的是「意圖」：純座標模式不知道實際點到什麼
            if label in ckpt["submitted"]:
                return True, f"「{label}」已經執行過，不重複執行"
            if not self.approve(label):
                return True, f"使用者拒絕執行「{label}」"
            ckpt["submitted"].append(label)
        self.p.activate(el)
        if tc.name == "type":
            self.p.type_text(tc.args["text"])
        expect = tc.args.get("expect", "")
        for _ in range(20):                                    # 驗證：動作的預期結果有沒有出現
            screen = json.dumps(self.p.elements(), ensure_ascii=False)
            if expect in screen:
                ckpt["milestones"].append(f"{label}→{expect}")
                return False, "OK"
            if any(m in screen for m in HUMAN_ONLY):
                return True, "畫面要求真人處理（登入或人機驗證）"
            self.p.advance(100)
        return True, f"做了「{label}」但 2 秒內沒看到「{expect}」，畫面可能沒反應"

    def run(self, task: str, ckpt: dict | None = None) -> tuple[str, dict]:
        ckpt = ckpt or {"task": task, "milestones": [], "submitted": []}
        note = f"\n已完成：{ckpt['milestones']}" if ckpt["milestones"] else ""
        messages = [{"role": "user", "content": f"{task}{note}\n畫面：\n{self.observe()}"}]
        for step in range(1, self.max_steps + 1):
            screen = messages[-1]["content"]
            if any(m in screen for m in HUMAN_ONLY):           # 登入、CAPTCHA：存檔並交給人
                self.log(f"step {step}  偵測到需要真人的畫面 → 暫停")
                return "needs_human", ckpt
            resp = self.model.complete(messages)
            self.p.advance(self.think_ms)                      # 模型思考期間，網頁照樣在變
            if not resp.tool_calls:
                self.log(f"step {step}  完成：{resp.text}")
                return ("done" if "CL-" in resp.text else "needs_human"), ckpt
            tc = resp.tool_calls[0]
            is_error, msg = self.act(tc, ckpt)
            what = (f"{tc.args['ref']} {self.refs[tc.args['ref']][1]}" if "ref" in tc.args
                    else tc.args.get("label") or tc.args["text"])
            self.log(f"step {step}  {tc.name}({what}) t={self.p.t}ms → {msg[:28]}")
            messages.append({"role": "assistant", "content": "", "tool_calls": [vars(tc)]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "is_error": is_error,
                             "content": f"{msg}\n畫面：\n{self.observe()}"})
        return "max_steps", ckpt


# ───────── 模擬的模型策略：讀畫面、決定下一步 ─────────
def policy(mode: str, tracking: str, amount: str) -> Callable[[list[dict]], ModelResponse]:
    def decide(messages: list[dict]) -> ModelResponse:
        screen = messages[-1]["content"].split("畫面：\n")[-1].splitlines()
        def find(name: str) -> dict | None:
            for line in screen:
                if f"「{name}」" in line:
                    if mode == "ref":
                        return {"ref": line[1:line.index("]")]}
                    x, y = line.rsplit("@(", 1)[1].rstrip(")").split(",")
                    return {"x": int(x), "y": int(y), "label": name}
            return None
        joined, cid = "\n".join(screen), f"c{len(messages)}"
        if "不重複執行" in messages[-1]["content"]:
            return say("送出申報已執行過一次但結果不明，請真人到後台確認")
        if "申報成功" in joined:
            return say("已完成申報，案件編號 CL-5531")
        if "遺失／毀損申報" not in joined:
            return call("click", cid, **find("遺失申報"), expect="遺失／毀損申報") if find("遺失申報") \
                else say("畫面不是預期的樣子，停止操作")
        if 'textbox「託運單號」 value=""' in joined:
            return call("type", cid, **find("託運單號"), text=tracking, expect=tracking)
        if 'textbox「申報金額」 value=""' in joined:
            return call("type", cid, **find("申報金額"), text=amount, expect=amount)
        if find("送出申報") is None:                           # 送出鈕還沒出現：等它，而不是亂點
            return call("wait_for", cid, text="送出申報")
        return call("click", cid, **find("送出申報"), expect="申報成功")
    return decide


# ① 一次完整的 ref 模式任務：點擊被吞、送出鈕晚出現、中途跳出公告
portal = Portal(banner_at=2500)
agent = BrowserAgent(ScriptedModel([policy("ref", "TC-77120", "1800")] * 12), portal, "ref", think_ms=200,
                     approve=lambda label: print(f"        [核准] 要執行「{label}」嗎？→ 營運專員按下核准") or True)
status, ckpt = agent.run("替託運單 TC-77120 申報遺失，金額 1800 元")
print(f"status={status}  副作用={portal.events}\n")
assert status == "done" and portal.events == ["建立申報 TC-77120 1800"]

# ② 遇到 CAPTCHA：存 checkpoint、交給真人，真人完成後從 checkpoint 續跑
portal = Portal(captcha=True, hydrate_at=0)
model = ScriptedModel([policy("ref", "TC-77135", "950")] * 12)
agent = BrowserAgent(model, portal, "ref", think_ms=200)
status, ckpt = agent.run("替託運單 TC-77135 申報遺失，金額 950 元")
print(f"status={status}  checkpoint={ckpt['milestones']}")
portal.human_solves_captcha()                       # 真人在接手畫面完成驗證，agent 不碰 CAPTCHA
status, ckpt = agent.run(ckpt["task"], ckpt)
print(f"status={status}  副作用={portal.events}  已執行的不可逆動作={ckpt['submitted']}")
assert status == "done" and portal.events == ["建立申報 TC-77135 950"]

# ②b 假設 worker 當機後拿同一份 checkpoint 重跑，畫面卻停在已填好的表單：不會重送第二次
retry = Portal(hydrate_at=0)
retry.page, retry.values = "form", {"託運單號": "TC-77135", "申報金額": "950"}
status, _ = BrowserAgent(ScriptedModel([policy("ref", "TC-77135", "950")] * 4), retry, "ref", 200).run(
    ckpt["task"], ckpt)
print(f"status={status}  重跑造成的副作用={retry.events}\n")
assert status == "needs_human" and retry.events == []

# ③ 同一個任務跑 200 次，公告在隨機時間出現；比較三種觀察／動作方式
rng = random.Random(16)
result = {}
for mode, think in (("xy", 2500), ("xy_guard", 2500), ("ref", 1200)):
    tally = {"正確": 0, "填錯欄位": 0, "誤觸取消": 0, "tokens": 0, "steps": 0}
    for _ in range(200):
        portal = Portal(banner_at=rng.randint(0, 12_000))
        agent = BrowserAgent(ScriptedModel([policy(mode, "TC-1", "500")] * 12), portal, mode, think,
                             verbose=False)
        status, _ = agent.run("替託運單 TC-1 申報遺失，金額 500 元")
        # 以環境裡真正發生的副作用評分，而不是看 agent 回報了什麼
        if portal.events == ["建立申報 TC-1 500"]:
            tally["正確"] += 1
        elif "誤觸取消" in portal.events:
            tally["誤觸取消"] += 1
        else:
            tally["填錯欄位"] += 1
        tally["tokens"] += agent.tokens
        tally["steps"] += len(agent.trace)
    result[mode] = tally
    print(f"{mode:<9} 正確 {tally['正確']:>3}/200  填錯欄位 {tally['填錯欄位']:>2}  誤觸取消 {tally['誤觸取消']:>2}  "
          f"平均步數 {tally['steps'] / 200:.1f}  平均觀察 tokens {tally['tokens'] // 200:,}")
assert result["ref"]["正確"] == 200 and result["xy_guard"]["正確"] == 200
assert result["xy"]["誤觸取消"] > 0 and result["xy"]["填錯欄位"] > 0
assert result["ref"]["tokens"] < result["xy"]["tokens"] / 5
```

```text
step 1  click(e1 遺失申報) t=2300ms → 做了「遺失申報」但 2 秒內沒看到「遺失／毀損申報」，畫
step 2  click(e1 遺失申報) t=2900ms → OK
step 3  type(e3 託運單號) t=3200ms → OK
step 4  type(e4 申報金額) t=3500ms → OK
step 5  wait_for(送出申報) t=3700ms → OK
        [核准] 要執行「送出申報」嗎？→ 營運專員按下核准
step 6  click(e6 送出申報) t=4000ms → OK
step 7  完成：已完成申報，案件編號 CL-5531
status=done  副作用=['建立申報 TC-77120 1800']

step 1  click(e1 遺失申報) t=300ms → OK
step 2  type(e2 託運單號) t=600ms → OK
step 3  type(e3 申報金額) t=900ms → OK
step 4  wait_for(送出申報) t=1100ms → OK
step 5  click(e5 送出申報) t=1400ms → 畫面要求真人處理（登入或人機驗證）
step 6  偵測到需要真人的畫面 → 暫停
status=needs_human  checkpoint=['遺失申報→遺失／毀損申報', '託運單號→TC-77135', '申報金額→950']
step 1  完成：已完成申報，案件編號 CL-5531
status=done  副作用=['建立申報 TC-77135 950']  已執行的不可逆動作=['送出申報']
step 1  wait_for(送出申報) t=800ms → OK
step 2  click(e5 送出申報) t=1100ms → 「送出申報」已經執行過，不重複執行
step 3  完成：送出申報已執行過一次但結果不明，請真人到後台確認
status=needs_human  重跑造成的副作用=[]

xy        正確 126/200  填錯欄位 37  誤觸取消 37  平均步數 5.7  平均觀察 tokens 7,725
xy_guard  正確 200/200  填錯欄位  0  誤觸取消  0  平均步數 5.8  平均觀察 tokens 7,903
ref       正確 200/200  填錯欄位  0  誤觸取消  0  平均步數 5.0  平均觀察 tokens 204
```

逐段解說這份輸出。

**情境 ①（一次完整的 ref 模式任務）**重現了 16.1 節的前兩個麻煩，並證明 harness 能吸收它們。step 1 點「遺失申報」時，模擬時間只過了 300ms，頁面腳本還沒接上，點擊被吞掉；Verifier 等了 2 秒沒看到「遺失／毀損申報」，回報「畫面可能沒反應」並附上新觀察。step 2 模型依新觀察再點一次，這次成功。注意 2,500ms 時公告已經滑入，所以 step 3 的託運單號變成 `e3`（`e1` 是公告），但因為 harness 在動作當下用 role 與 name 重新尋找元素，跳版完全沒有影響。step 5 模型發現送出鈕還沒出現，選擇 `wait_for` 而不是亂點；step 6 的送出是不可逆動作，先印出核准提示，經營運專員核准才執行。最後的副作用只有一筆「建立申報」，和預期完全相同。

**情境 ②（CAPTCHA 與續跑）**示範 16.7 節的時序圖。step 5 送出後畫面變成人機驗證，Verifier 立刻停止等待；step 6 的 GUARD 偵測到人工專用畫面，以 `needs_human` 暫停，模型完全沒有被詢問要怎麼處理驗證碼。這時的 checkpoint 記錄了三個已驗證的步驟。真人完成驗證後，agent 帶著同一份 checkpoint 續跑：重新觀察，看到「申報成功」，一步就結束。最後一行顯示副作用帳本記錄了「送出申報」已執行。

**情境 ②b（重跑不重送）**是本章最重要的一個 assert。假設 worker 在送出之後當機，排程系統拿同一份 checkpoint 重跑，而這次瀏覽器停在已填好的表單上。模型很自然地想再按一次送出，但 GUARD 查到帳本裡已有「送出申報」，拒絕重複執行；模型於是回報「結果不明，請真人確認」，status 是 `needs_human`，重跑造成的副作用是空的。如果沒有這份帳本，這裡就會產生第二筆申報。真實系統在這一步還應該先到「我的申報」列表查證，這是 16.8 節 RESUMING 狀態的工作。

**情境 ③（200 次比較）**用固定 seed 讓公告在 0 到 12 秒之間的隨機時間出現，三種模式各跑 200 次。評分看的是環境裡真正發生的副作用，不是 agent 的回報：

| 模式 | 正確完成 | 填錯欄位 | 誤觸「取消此託運」 | 平均步數 | 平均觀察 tokens |
|---|---|---|---|---|---|
| `xy`（截圖座標，直接點） | 126/200 | 37 | 37 | 5.7 | 7,725 |
| `xy_guard`（點擊前 hit-test） | 200/200 | 0 | 0 | 5.8 | 7,903 |
| `ref`（accessibility tree＋晚綁定） | 200/200 | 0 | 0 | 5.0 | 204 |

`xy` 模式有兩種失敗，都發生在「公告剛好在模型思考期間滑入」的情況。37 次誤觸「取消此託運」是 16.1 節的事故；更值得警惕的是，這 37 次都經過了核准，因為核准的是模型的意圖「送出申報」，而不是實際點到的元素，這正是 16.7 節第三條原則要防的事。另外 37 次「填錯欄位」更隱蔽：模型要在「申報金額」輸入 500，舊座標卻落在被推下來的「託運單號」上；harness 的驗證條件只是「畫面上出現 500」，於是驗證通過，最後送出了一筆託運單號是 500 的申報，agent 還回報了案件編號。這說明驗證條件必須精確到「哪個欄位的值是什麼」，寫得太寬的驗證和沒有驗證差不多。

`xy_guard` 只加了一行 hit-test 就把兩種失敗都降到 0，代價是偶爾多一次觀察（平均步數從 5.7 升到 5.8，tokens 也略增），這說明就算只能用截圖，也一定要在點擊前確認目標。`ref` 模式同樣全部正確，而且觀察成本低得多；不過這個模擬頁面只有幾個元素，真實頁面的 tree 會大得多，表中三十幾倍的差距只代表方向，不代表你的系統會得到同樣的比例。

| 機制 | 程式中的位置 | 修掉的事故 | 對應小節 |
|---|---|---|---|
| 晚綁定（role＋name 重新定位） | `locate()` 的 ref 分支 | 跳版點錯 | 16.4、16.5 |
| 點擊前 hit-test | `locate()` 的 `xy_guard` 分支 | 只能用座標時的點錯 | 16.5 |
| 可操作性等待與 `wait_for` | `locate()` 的等待迴圈、`act()` | 點太早、對灰色按鈕硬點 | 16.6 |
| 動作後驗證 | `act()` 的 `expect` 檢查（本例只比對文字，條件偏寬） | 點擊被吞掉卻以為成功 | 16.6 |
| 人工專用畫面偵測 | `run()` 的 `HUMAN_ONLY` 檢查 | 嘗試處理 CAPTCHA、索取密碼 | 16.7 |
| 核准與副作用帳本 | `act()` 的 `IRREVERSIBLE` 分支 | 未經確認送出、重跑重送 | 16.7、16.8 |
| checkpoint 續跑 | `run(task, ckpt)` | 中斷後從頭來 | 16.8 |

這個程式刻意省略了幾件真實系統必須做的事：沒有真的瀏覽器（真實系統會透過 CDP 或 Playwright 之類的自動化層操作瀏覽器）、checkpoint 只存在記憶體（第 22 章會把它寫進事件日誌）、續跑時沒有到「我的申報」列表查證、核准只是一個回呼函式（第 21 章會做成完整的 approval 流程）。驗證條件也刻意寫得簡單（只比對畫面上有沒有某段文字），真實系統應該檢查特定欄位的值。但 harness 的結構已經完整：觀察、決策、Guard、定位與等待、動作、驗證、記錄，每一步都可以獨立替換成真實的實作。這個 harness 可以收成 `loom.browser` 模組，沿用第 21 章的核准與第 22 章的 durable log；第 45 章 45.12 節說明它在 `loom` v1.0 中的掛接點。

## 16.11 實務應用

同一套 perception–action loop，在不同產品裡要調整的重點很不一樣。以下四個情境涵蓋了 browser agent 最常見的用途。

**情境一：供應商入口網站的例行申報（青鳥的主線）**。山貓快遞的申報上線後採用第 1 章定義的 L3：讀取與填寫由 agent 自主，送出由營運專員核准；跑了一個月、驗證準確率穩定後，金額在一定門檻以下的申報移到 L4，自動送出但每天抽查。設計重點是：用專用的服務帳號、每筆任務一個隔離的瀏覽器 profile；常見流程固化成腳本，只有腳本失敗才交給模型；每筆申報送出後到「我的申報」列表對帳；CAPTCHA 與登入一律轉給值班專員。團隊同時保留一張「改版警報」：腳本重播失敗率在一天內明顯上升，就代表山貓快遞改版了，要人去看。

**情境二：coding agent 驗證自己做的前端**。這是近年成長最快的用途：coding agent 改完程式後啟動開發伺服器，用 browser agent 打開頁面、點擊、填表，確認功能真的可用，而不只是測試通過。依公開資料，Anthropic 在長時間開發 harness 的實驗中讓 evaluator 透過 Playwright MCP 實際點擊應用程式來評分，也提到瀏覽器自動化看不到瀏覽器原生的 alert 對話框；GitHub Copilot coding agent 的文件說明它預設啟用 Playwright MCP。這個情境的風險比較低（操作的是自己的開發環境），重點反而在驗證品質：要求 agent 依明確的驗收條件逐項檢查並截圖存證，避免它「看一眼覺得沒問題」就宣告完成（第 27 章的 outcome 評估）。

**情境三：沒有 API 的舊系統資料搬移與對帳**。一家連鎖零售客戶要把舊的桌面版進銷存系統資料搬到新平台，舊系統只能在 Windows 桌面上操作。這裡沒有 DOM 可讀，只能用截圖加座標的 computer use，所以要把可靠性設計做足：在專用 VM 裡跑、固定螢幕解析度與縮放比例、每個動作後驗證（例如讀取畫面上的筆數）、每一批資料搬完就 checkpoint；搬移完成後用新平台的 API 做全量對帳，而不是相信 agent 的回報。這類一次性專案也很適合「探索後固化」：前幾批由 agent 探索，之後由腳本重播。

**情境四：唯讀的研究與比價**。營運 research agent（第 40 章）需要查各物流商公開網站的運費與服務公告。唯讀任務的風險主要在 prompt injection 與資料品質，而不在副作用：agent 讀到的網頁內容不能改變它的任務；所有引用要附來源頁面；能用文字擷取（第 11 章的 fetch 與檢索）就不必開完整的瀏覽器。依公開介紹，ChatGPT agent 同時提供視覺化瀏覽器與文字瀏覽器（本書未逐項查證），可以理解為讓 agent 在兩種成本之間選擇。

| 情境 | 主要觀察方式 | autonomy | 最重要的防線 | 特別注意 |
|---|---|---|---|---|
| 供應商入口例行申報 | accessibility tree＋固化腳本 | L3 → 小額 L4 | 核准、副作用帳本、對帳 | 服務帳號、改版警報、CAPTCHA 轉人 |
| coding agent 驗證前端 | accessibility tree（Playwright 類工具） | 開發環境內 L4 | 明確的驗收條件與截圖存證 | 原生對話框可能看不到 |
| 舊系統資料搬移 | 截圖＋座標 | L3（分批核准） | 每步驗證、批次 checkpoint、全量對帳 | 固定解析度與縮放 |
| 唯讀研究與比價 | 文字擷取為主，必要時開瀏覽器 | L5（預算內） | 不可信內容隔離、引用來源 | 網域 allowlist、不帶憑證 |

這張表的共同點是：觀察方式決定成本與穩健度，autonomy 與防線決定風險。沒有任何一個情境是「讓模型自由操作瀏覽器」就結束了，每一個都要回答「看錯了怎麼辦、點錯了怎麼辦、要停下來找人時怎麼辦」。

> [!note] 2026 現況
> 以下截至 2026 年 10 月，依各家公開文件與產品更新整理，細節變動很快，請以官方文件為準。
> - **Anthropic**：computer use tool 自 2024 年 10 月起提供，屬於「由 Anthropic 定義 schema、在你的應用程式中執行」的 client tool，動作以截圖加座標為主；目前文件中同類工具還包括 browser use。官方建議在權限最小的 VM 或容器中執行、避免讓模型接觸敏感帳號資訊、限制可連線的網域，並對有實際後果的動作（例如金融交易、同意服務條款）要求真人確認。Claude in Chrome 已整合進 Claude Code。依 Anthropic 視覺文件的估算方式，一張圖的 token 數約為寬×高÷750，1280×800 的截圖約 1,400 tokens，和本章的估算表一致；確切公式與解析度上限請查當時文件。
> - **OpenAI**：2025 年 1 月推出 Operator（以 Computer-Using Agent 模型操作截圖與滑鼠鍵盤），2025 年 7 月整合進 ChatGPT agent，公開介紹提到敏感動作前會要求確認、在部分網站要求使用者觀看（watch mode）；這兩點本書未逐項查證。2026 年的產品更新依序加入內建瀏覽器中的 computer use、macOS 與 Windows 的 computer use、瀏覽器開發者模式的 CDP 存取，以及 WebMCP 支援。
> - **WebMCP**：讓網站在頁面中主動宣告結構化工具給 agent 呼叫，對應 16.2 節的層級 2；目前仍屬早期階段，規格與各家支援程度請查最新資料。
> - **Google**：Gemini 2.5 的 computer use preview 模型已被列為停止服務；Vertex AI 的 Agent Engine（現以 Gemini Enterprise Agent Platform 的 Agent Runtime 名稱出現）在 code execution sandbox 中提供 computer use。
> - **託管瀏覽器**：Amazon Bedrock AgentCore 提供託管的 Browser 服務，文件提到可搭配 Playwright 與 Browser Use。
> - **Benchmark**：OSWorld（真實 VM 中的電腦操作，人類基準約 72%）已有 Verified 版與 2026 年 6 月釋出的 OSWorld 2.0；WebArena 系列以自架網站測網頁任務。引用分數時務必註明版本，第 28 章會詳談。

## 16.12 設計檢查清單

設計或審查一個 computer use／browser agent 時，逐項回答下面的問題：

1. 這個任務的每一步，是否都確認過沒有 API、MCP server 或網站提供的結構化工具可用？只有真的沒有的步驟才用畫面操作嗎？
2. 主要觀察方式選哪一種：accessibility tree、截圖，還是混合？選擇的理由是否寫在設計文件裡（覆蓋範圍、成本、穩健度）？
3. 動作是否以元素層級為主，並在動作當下才重新定位元素（晚綁定）？ref 失效時是否有重新尋找與回報的路徑？
4. 如果必須用座標，是否處理了截圖縮放、裝置像素比與捲動偏移？點擊前是否 hit-test 確認目標仍是模型看到的元素？
5. 每個動作是否宣告了預期結果，並由 harness 在環境中驗證？等待是否都有逾時上限，逾時是否回報原因？
6. 動作是否分成可重做與不可逆兩類？不可逆動作驗證失敗時，是否進入「結果不明、先查證」而不是自動重試？
7. 偵測登入頁、CAPTCHA、多因素驗證的邏輯，是否寫在 harness 而非只寫在 prompt？偵測到時是否一定暫停並交給人？
8. 憑證是否完全不進 context、觀察與 trace？使用的是專用且權限最小的帳號嗎？
9. 不可逆動作的核准畫面，顯示的是 harness 確認過的實際目標與欄位值，還是只有模型的意圖？
10. checkpoint 是否包含已驗證步驟與副作用帳本？續跑時是否先對帳再前進，並重新觀察而不沿用舊 ref 與座標？
11. 真人接手時，是否接手同一個瀏覽器 session？接手通知是否附上任務、卡住的步驟與畫面？
12. 每個任務是否跑在隔離、用完即丟的瀏覽器 profile 或容器中？可造訪的網域是否有 allowlist？
13. 是否估算過每個任務的步數、觀察 token 與延遲？舊截圖是否從 context 中移除或改成摘要？
14. 是否有「探索後固化」的路徑，以及偵測對方改版的監控（重播失敗率、驗證失敗率）？

## 16.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 偶爾點到旁邊的按鈕，重跑又正常 | 觀察與動作之間版面變動（公告、圖片載入、動畫） | 比對動作當下與觀察當下的截圖或元素位置 | 改用元素層級晚綁定；座標模式加點擊前 hit-test |
| 在某些機器上一律點偏 | 截圖縮放或裝置像素比沒有換算 | 在 trace 中比較截圖尺寸、螢幕尺寸與點擊座標 | 統一座標換算函式並加單元測試；固定 VM 解析度 |
| 點了沒反應，agent 判定網站壞了 | 頁面尚未 hydration 完成，或元素被透明遮罩擋住 | 看點擊時間與頁面載入時間；檢查元素是否可接收事件 | 動作前可操作性等待；動作後驗證，可重做的動作重新定位再試 |
| agent 回報完成，實際沒有送出 | 只相信模型自述，沒有驗證環境 | 對照 trace 中最後的觀察與後台實際資料 | 每個動作宣告預期結果；任務層級到列表或其他系統對帳 |
| 同一筆申報出現兩次 | 結果不明時自動重試，或續跑時沒有對帳 | 查副作用帳本與重試紀錄的時間點 | 不可逆動作不自動重試；帳本加上續跑前查證 |
| 對灰色按鈕反覆點擊直到步數用完 | 等待沒有上限，或逾時沒回報原因 | 看 trace 中同一元素的 disabled 狀態 | 等待設上限，逾時回報「一直是 disabled」並附新觀察 |
| 模型在登入頁索取密碼或嘗試處理 CAPTCHA | 人工專用畫面只靠 prompt 處理 | 在 trace 中找登入頁或 CAPTCHA 出現後的模型呼叫 | harness 層偵測並暫停；憑證由真人或 secrets 系統處理 |
| 驗證通過、agent 也回報完成，但送出的資料是錯的 | 驗證條件太寬（只看畫面上有沒有某段文字），座標點錯欄位也能通過 | 抽查已送出的資料與任務參數是否一致 | 驗證精確到特定欄位的值；送出前由 harness 讀回所有欄位與任務參數比對 |
| 每筆任務的 token 成本隨步數快速上升 | 每一步都保留所有歷史截圖 | 統計每步 input 中圖片數量 | 只留最近幾張，其餘改文字摘要；改用 tree 為主 |
| 對方改版後整批任務失敗 | 依賴脆弱的選擇器或固定座標 | 看失敗集中在哪一步、哪個元素 | 用 role＋name 定位；改版監控；腳本失敗時交給模型重新探索 |

## 本章重點整理

- computer use 讓模型透過畫面與滑鼠鍵盤操作電腦，browser agent 是只操作瀏覽器、且能讀取頁面結構的版本；兩者面對的都是給人設計的介面。
- 同一個意圖可以在 API、網站結構化工具、accessibility tree、截圖座標四個層級完成，越往下越通用也越貴、越脆弱，能往上走就不要往下走。
- perception–action loop 和一般 agent loop 的關鍵差異是環境自己會變：模型思考期間畫面可能改變，觀察與動作之間的時間差會造成點錯。
- accessibility tree 只保留有意義的節點與 role、name、state，適合當主要觀察；截圖能看到任何畫面與視覺資訊，但每步成本固定且只能用座標動作。
- 晚綁定讓模型指名元素、由 harness 在動作當下重新定位，是抵抗跳版最有效的方法；必須用座標時，點擊前要 hit-test 確認目標。
- 座標動作要處理截圖縮放、裝置像素比、捲動與 iframe；輸入中文優先用整段填入而不是逐鍵模擬。
- 等待要以條件為準並有逾時上限，逾時要回報原因；固定 sleep 通常不是太早就是太晚。
- 每個動作都要宣告預期結果並由 harness 在環境中驗證，模型說「我點了」或 harness 送出了點擊都不算完成。
- 可重做的動作可以重新觀察、重新定位後再試；不可逆動作驗證失敗時進入「結果不明」，先查證、查不到才交給人。
- 憑證不進 context，CAPTCHA 交給人而不嘗試解或繞過，有後果的動作要人確認實際效果，網頁內容永遠是不可信的資料。
- 人工專用畫面的偵測、核准與憑證隔離要寫在 harness 的確定性邏輯裡，prompt 只負責讓模型理解原因。
- checkpoint 要記錄已驗證步驟與副作用帳本；續跑時先對帳、再重新觀察、再前進，才能避免重複送出。
- browser agent 的成本與延遲主要來自步數與歷史觀察；移除舊截圖、以 tree 為主、探索後固化成腳本，是最有效的優化。

## 延伸問答

> [!question]- Q1. 截圖座標與 accessibility tree 兩種觀察方式，要怎麼選？
> 先看覆蓋範圍：目標是網頁、而且網站的無障礙做得還可以，accessibility tree 幾乎總是較好的主要觀察，因為它便宜、可以晚綁定、版面變動時通常仍可用。目標是遠端桌面、原生桌面程式、canvas 畫的介面，或網站的按鈕大量缺少名稱，就只能以截圖為主。再看任務需不需要視覺判斷：確認「圖表有沒有畫出來」「排版有沒有跑掉」，只有截圖做得到。
>
> 實務上的答案通常是混合：以 tree 為主，tree 缺名稱或需要視覺判斷時才截圖，必要時在截圖上標出元素編號，讓模型用編號而不是座標指稱。選擇的理由要寫進設計文件，因為它決定了成本模型、失敗模式與安全邊界；之後對方網站改版或換成新的模型時，才有依據重新評估。

> [!question]- Q2. 為什麼不能在每個動作之後都 sleep 固定的秒數就好？
> 因為網頁載入的時間每次都不同，固定 sleep 同時有兩種失敗：太短時，元素還沒出現、還在動畫中、或事件處理還沒接上，動作變成無效或點錯；太長時，每一步都白白多等，十步的任務就多出好幾十秒。更糟的是，這兩種失敗常常在同一個任務裡同時出現，因為不同頁面的載入時間差很多，沒有一個固定值能同時滿足。
>
> 正確做法是等「條件」：動作前等元素存在、可見、位置穩定、可用；動作後等預期結果出現；兩者都設逾時上限。逾時時要回報原因（「一直是 disabled」「兩秒內沒看到申報成功」），讓模型有線索修正。固定 sleep 只該用在沒有任何條件可等的少數場合，而且要在 trace 裡記錄，因為它通常代表觀察手段不足。

> [!question]- Q3. 情境判斷：你在 production 看到某一天 browser agent 的任務成功率從 95% 掉到 40%，你會怎麼排查？
> 第一步是看失敗集中在哪裡：同一個網站、同一個步驟、同一個元素？browser agent 的成功率突然大幅下降，最常見的原因是對方網站改版，例如按鈕換了文字、表單多了一個欄位、加了新的 cookie 同意橫幅。抽幾條失敗的 trace，看最後一次觀察的內容，通常一眼就能看出畫面和以前不同。
>
> 第二步是排除自己這邊的變更：同一天是否換了模型版本、改了 prompt、調整了截圖解析度或瀏覽器版本。第三步是看是否觸發了對方的風控：CAPTCHA 與登入頁出現的比例是否上升，是否因為請求頻率太高被限流。修復時，改版就更新固化腳本或定位條件，並把這次的畫面加進回歸測試；風控問題則要降低頻率、改用專用帳號，或去和對方談正式的整合管道，不要試圖繞過。

> [!question]- Q4. 估算題：一個 browser agent 每天處理 300 筆申報，每筆平均 10 步，截圖模式每步保留最近 3 張圖、每張約 1,400 tokens。每天光是觀察就要多少 input tokens？改成 accessibility tree 會怎樣？
> 截圖模式下，每步的觀察部分約 3 × 1,400 ＝ 4,200 tokens（前兩步不滿 3 張，先忽略）。每筆 10 步就是約 42,000 tokens，每天 300 筆約 1,260 萬 tokens，這還沒算 system、tool 定義與動作紀錄。如果不移除舊截圖、每步都帶著所有歷史截圖，第 k 步要帶 k 張，10 步加總是 55 張，約 77,000 tokens，每天就超過 2,300 萬，這說明「只保留最近幾張」本身就省掉四成以上。
>
> 改成 accessibility tree，假設中等複雜度的頁面每份 tree 約 600 tokens，每步只帶最新一份完整 tree 加幾行舊步驟摘要，每步約 700 tokens，每筆 7,000，每天約 210 萬，約是截圖模式的六分之一。但要注意兩個前提：tree 的大小隨頁面變化很大，一張大表格可能比截圖還貴；以及步數本身可能不同。最大的省法其實是把例行流程固化成腳本，讓多數任務完全不呼叫模型。

> [!question]- Q5. 程式找錯：下面這段重試邏輯會在 production 出什麼事？
> ```python
> for attempt in range(3):
>     x, y = last_click_xy
>     browser.click(x, y)
>     if wait_for_text("申報成功", timeout=2):
>         break
> ```
> 有兩個問題。第一，重試用的是同一個舊座標。如果第一次失敗是因為跳版或元素還沒出現，舊座標在第二次、第三次一樣是錯的，甚至可能點到另一顆按鈕；重試應該是重新觀察、重新定位目標，座標模式還要在點擊前 hit-test 確認目標。
>
> 第二個問題更嚴重：被重試的是「送出申報」這種不可逆動作。兩秒內沒看到「申報成功」，不代表沒有送出，可能是伺服器慢、成功頁還沒畫出來。這段程式最多會送出三筆申報。正確做法是：送出前在副作用帳本記錄「已嘗試送出」，驗證逾時就標成結果不明，先到「我的申報」列表查證，查不到才考慮再送，查證本身失敗就交給人。

> [!question]- Q6. 為什麼 CAPTCHA 一定要交給人？如果模型其實辨識得出來呢？
> 能不能辨識是技術問題，該不該辨識是授權問題。CAPTCHA 是網站明確表達「這一步要真人」的機制；用模型解它、接第三方解碼服務，或偽裝瀏覽器避開風控，都是在對抗對方的意圖，可能違反服務條款與當地法律，也會讓公司帳號被封鎖，影響的是所有依賴這個帳號的業務。這和「模型能不能讀懂驗證碼」完全無關。
>
> 設計上的做法是讓 harness 偵測到 CAPTCHA 就暫停、存 checkpoint、通知真人在同一個 session 裡完成，再續跑。如果 CAPTCHA 頻繁到影響營運，代表你的使用方式超出了對方對一般使用者的預期，應該去談 API、批次上傳或其他正式管道。把這條寫在 harness 而不是 prompt，是為了確保不論模型怎麼想、網頁上寫了什麼，都不會越線。

> [!question]- Q7. 面試追問：設計一個能處理「每天數千筆、橫跨十幾個供應商網站」的 browser agent 平台，你會怎麼架構？
> 先分層：最上層是任務佇列與排程，每筆任務是一個獨立的狀態機（RUNNING、NEEDS_HUMAN、RESUMING、DONE、FAILED），狀態與 checkpoint 存在持久化的 store；中層是 worker pool，每個 worker 為每筆任務開一個隔離、用完即丟的瀏覽器 profile 或容器，session 憑證從 secrets 系統注入、不進 context；底層是每個供應商網站的適配層，盡量把流程固化成元素層級的腳本，腳本失敗才交給模型探索。
>
> 接著是橫切的能力：人工接手的工作台（live view、取得控制、交回、附註）、不可逆動作的核准佇列、副作用帳本與續跑前的對帳、每個網站的頻率限制與網域 allowlist、改版監控（每個網站、每個步驟的重播失敗率）。容量估算要以步數與觀察 token 為核心，並把 NEEDS_HUMAN 的比例當成一級指標，因為它決定了需要多少值班人力。最後要能回答面試官的取捨問題：為什麼不全部用模型（成本與延遲）、為什麼不全部寫死腳本（改版時沒有彈性）。

> [!question]- Q8. 概念辨析：晚綁定（late binding）、點擊前 hit-test、動作後驗證，三者分別防的是什麼？只做其中一個夠嗎？
> 晚綁定防的是「目標找錯」：模型指名元素，harness 在動作當下才定位，所以觀察之後的版面變動不會讓動作落到錯的地方。點擊前 hit-test 是座標模式下的替代方案，防的也是目標找錯，但它只能偵測、不能修正：目標不對就不點，回去重新觀察。動作後驗證防的是「效果沒發生」：目標對了、也點了，但頁面沒反應、送出失敗、或跳到意料之外的畫面。
>
> 只做一個不夠。只有晚綁定，點擊被吞掉時 agent 會以為成功；只有驗證，點錯按鈕的副作用已經發生了，驗證只能事後發現，對不可逆動作來說太晚。三者疊在一起，才把「看錯一次就闖禍」變成「看錯一次就多花一步」。16.10 節的比較也顯示，`xy` 模式雖然有驗證，仍然有 37 次誤觸，另外 37 次填錯欄位甚至通過了寫得太寬的驗證；加上 hit-test 或改用晚綁定，兩種失敗才都降到零。

## 延伸閱讀

- Anthropic 文件〈Computer use tool〉（Claude Developer Platform）
- Playwright 文件〈Auto-waiting〉與〈Locators〉
- W3C〈Accessible Name and Description Computation〉與〈WAI-ARIA〉規格
- Zhou et al.〈WebArena: A Realistic Web Environment for Building Autonomous Agents〉（ICLR 2024）
- Xie et al.〈OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments〉（NeurIPS 2024）
- Yang et al.〈Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V〉（2023）
- Deng et al.〈Mind2Web: Towards a Generalist Agent for the Web〉（NeurIPS 2023）
- OpenAI〈Computer-Using Agent〉介紹文（2025）
