---
chapter: 34
title: Actionable Alerting 與 Multi-window Burn Rate
part: 5
---

# 第 34 章　Actionable Alerting 與 Multi-window Burn Rate

> [!abstract] 本章地圖
> **核心問題**：什麼事情值得在半夜叫醒一個人？要怎麼設計告警，才能幾分鐘內抓到大事故、幾小時內抓到慢性傷害，又不會讓值班者被雜訊淹沒？
>
> **你會學到**：
> - 判斷一個 alert 是否值得 page：緊急、可行動、使用者可見，並把其他訊號分流到 ticket 或 dashboard
> - 區分 symptom alert 與 cause alert，知道何時 cause alert 仍然合理
> - 用 precision、recall、detection time、reset time 四個尺度評估任何告警規則
> - 從 burn rate 的定義一步步推導出 multi-window multi-burn-rate 的參數（14.4、6、1 與它們的短窗）
> - 設計告警的傳遞與去重（routing、grouping、inhibition、silence），以及 alert 的生命週期與定期檢討
> - 把 AI 放在告警流程中適合的位置，而不是放進 pager 的關鍵路徑
>
> **前置知識**：第 32 章（SLI、SLO、error budget 與 burn rate 的定義）、第 33 章（metrics 與 four golden signals）
>
> **對應原書**：SRE 第 6 章〈Monitoring Distributed Systems〉、第 10 章〈Practical Alerting〉；SRE Workbook 第 5 章〈Alerting on SLOs〉

## 34.1 故事：一週 37 次 page，卻漏掉真正燒掉預算的那一個

Harbor 在第 32 章訂出 checkout 的 SLO（30 天 rolling，99.9%）之後，SRE 志明以為最難的部分已經完成。三個月後的一次 on-call 交接會，初階工程師阿凱第一次輪完一整週的班，交出一份讓所有人沉默的紀錄：這週 pager 響了 37 次，其中 22 次是「某台機器 CPU 超過 85%」，9 次是「磁碟使用率超過 80%」，4 次是 search 的錯誤率在一分鐘內跳到 2% 又自己恢復。阿凱坦白，從第三天開始，聽到手機震動就先猜「應該又是 CPU」，然後繼續睡。

真正嚴重的事情恰好發生在同一週，卻一次都沒有 page。週三上午上線的折價券功能有一個邊界條件錯誤：使用特定組合折扣的訂單會在付款確認階段失敗。失敗率只有 0.8%，從每分鐘的圖上看幾乎是一條平線。但它連續跑了兩天多，到週五下午產品經理 Lisa 從營收報表發現異常時，checkout 這個月的 error budget 已經用掉了 58%。

同一週還有一次相反的狀況。週四晚上外部金流商的 API 中斷了 12 分鐘，checkout 幾乎全部失敗。告警規則寫的是「錯誤率超過 5% 且持續 10 分鐘才發送」，原意是避免誤報，結果 pager 在第 10 分鐘才響，阿凱登入時事故已經接近尾聲。這 12 分鐘在 99.9% 的 SLO 下，就是 30 天預算的四分之一以上。

事後檢討時，tech lead 美華把問題歸納成三句話：會響的大多不重要，重要的不夠快，慢的完全不響。這三個症狀其實是同一個病：告警規則是從「我們能量到什麼」出發，而不是從「使用者受到多少傷害、值班者能做什麼」出發。

這一章就是要把 Harbor 的告警從頭設計一遍。先講清楚什麼東西值得 page，再用第 32 章的 burn rate 一步步推導出一套能同時抓快、抓慢、又安靜的規則，最後處理告警送出之後的事：路由、去重、檢討與退場。

## 34.2 好的 alert 長什麼樣子

### Alert 是一個打斷人的 API

**Alert**（告警）是監控系統主動通知人的機制。它和 dashboard 最大的差別是：dashboard 要人去看，alert 會打斷人。被打斷是有成本的：半夜被叫醒的值班者要花時間清醒、登入、理解狀況；白天被打斷的工程師會失去正在進行的工作脈絡。所以一個 alert 本質上是一個「花掉別人注意力」的 API 呼叫，設計它的人要為這個成本負責。

SRE 原書把通知分成三種輸出，這個分類到今天仍是最實用的起點：

| 輸出 | 意思 | 回應時間 | Harbor 的例子 |
|---|---|---|---|
| **Page**（呼叫） | 立刻通知值班者，人類必須馬上行動 | 分鐘級 | checkout 的 error budget 正以 14 倍速度燃燒 |
| **Ticket**（工單） | 需要人處理，但可以等到上班時間 | 小時到天 | 3 天內 checkout 已用掉 10% 預算，速度略高於可持續水準 |
| **Log／Dashboard**（記錄） | 不需要任何人立即看，只在診斷時使用 | 不需要回應 | 單台機器 CPU 85%、某個 pod 重啟一次 |

很多團隊只有「page」與「什麼都沒有」兩種，於是所有覺得「應該有人知道」的事情都變成 page。阿凱那週的 22 次 CPU page，本來應該是 dashboard 上的一條線，最多是一張 ticket。

### 值得 page 的三個條件

一個 alert 值得變成 page，通常要同時滿足三個條件：

1. **緊急**：等到明天早上再處理，傷害會明顯擴大。磁碟用了 80% 但以目前速度要兩週才會滿，這不緊急；磁碟兩小時內會滿，這才緊急。
2. **可行動**：值班者收到後有具體的事可以做，例如 rollback、切換流量、擴容、關閉 feature flag。如果唯一能做的是「看著它，等它自己恢復」，這個 page 只是在製造焦慮。
3. **使用者可見或即將可見**：使用者正在受傷，或很快會受傷。機器層面的異常若沒有轉化成使用者傷害，就不是 page 的理由。

SRE 原書還補充了一個條件：page 應該需要人的判斷。如果每次收到某個 page，值班者都做完全一樣的步驟，這件事應該被自動化（第 31 章的 toil），而不是繼續叫醒人。

> [!warning] 常見誤解
> 「多設一點告警比較保險，寧可誤報也不要漏報。」這在直覺上很合理，但在人身上不成立。值班者每天能認真回應的 page 數量很有限，當大部分 page 都是雜訊，人會學會忽略 pager，結果真正的事故反而被忽略，這就是 **alert fatigue**（告警疲勞）。誤報不是免費的保險，它在消耗整個告警系統的可信度。

## 34.3 Symptom 與 Cause：要告警「什麼壞了」，不是「為什麼壞」

### 兩種訊號

SRE 原書用一組簡單的問題區分監控訊號：**什麼壞了**（what's broken）是 **symptom**（症狀），**為什麼壞**（why）是 **cause**（原因）。

| Symptom（使用者看到的） | 可能的 Cause（系統內部的） |
|---|---|
| checkout 回傳 5xx 的比例上升 | 資料庫連線池耗盡、金流商 API 中斷、新版本有 bug |
| 搜尋 p99 延遲從 300 ms 升到 3 秒 | 索引節點 GC 停頓、快取命中率下降、某個查詢模式變多 |
| 訂單通知延遲超過 10 分鐘 | 訊息佇列堆積、notification worker 當機 |

同一個 symptom 可能有很多 cause，同一個 cause 也可能不造成任何 symptom。CPU 85% 是一個 cause 層級的訊號：有時它代表系統快撐不住，但更多時候它只是代表機器被有效利用。如果對每一個可能的 cause 都設 page，你會得到一大堆「不一定有影響」的 page，卻仍然會漏掉沒想到的 cause。Symptom alert 則反過來：不管背後是哪個原因，只要使用者受傷就會響。

所以實務上的原則是：**用 symptom 來 page，用 cause 來診斷**。Symptom 告訴你「該起床了」，cause 層級的 metrics、logs、traces（第 33 章）幫你找到要修什麼。

### Black-box 與 white-box

另一組相關的詞是 **black-box monitoring**（黑箱監控）與 **white-box monitoring**（白箱監控）。Black-box 是從外部像使用者一樣測試系統，例如每分鐘由外部 probe 走一次「加入購物車 → 結帳」；它看到的是 symptom，而且能抓到「請求根本沒進來」的問題。White-box 是讀取系統內部暴露的 metrics 與 logs，可以看到佇列長度、連線池使用量這類「快要壞」的訊號。好的告警系統兩者都用：black-box 與 SLO 告警負責 page，white-box 負責診斷與部分預測性告警。

### Cause alert 何時仍然合理

Symptom 優先不代表 cause alert 一律禁止。有幾種情況，等到 symptom 出現就太晚了：

- **即將耗盡的資源**：磁碟、憑證、配額這類資源一旦耗盡，傷害是立即且全面的。關鍵是用「多久會耗盡」而不是「用了多少百分比」來判斷。Prometheus 的 `predict_linear` 函式就常被用來估計「依目前趨勢，磁碟 4 小時內會滿」，這種條件才值得 page；30 天後才會到期的憑證則應該是 ticket。
- **沒有流量就看不到的故障**：凌晨流量很低，某個區域的 backend 全部掛掉，但因為沒有使用者請求，SLI 沒有變化。這時 synthetic probe 或「健康 backend 數量低於安全下限」的告警能在早上流量進來之前發現問題。
- **資料正確性與安全**：備份連續失敗、資料完整性檢查出現差異、偵測到異常的權限操作。這些在使用者察覺之前可能已經造成不可逆的損失。

這些例外的共同點是：它們有明確的行動、有明確的時間壓力，而且不是「可能有關」而已。

## 34.4 評估一條告警規則的四把尺

在討論具體公式之前，先建立評估工具。SRE Workbook 在〈Alerting on SLOs〉中用四個指標衡量告警規則，之後的每一個設計都會用它們打分數：

| 指標 | 意思 | 太差時的症狀 |
|---|---|---|
| **Precision**（精確率） | 觸發的告警中，有多少是真正重要的事件 | 值班者被誤報淹沒，開始忽略 pager |
| **Recall**（召回率） | 真正重要的事件中，有多少被告警抓到 | 事故由客服或營收報表發現，而不是由監控發現 |
| **Detection time**（偵測時間） | 從問題開始到告警觸發要多久 | 預算在等待中被大量燒掉 |
| **Reset time**（解除時間） | 問題結束後，告警還要響多久才停 | 修好了還在響，值班者分不清是否真的恢復，甚至以為出現新問題 |

這四個指標彼此拉扯。把門檻降低能提高 recall、縮短偵測時間，但 precision 會變差；把觀察窗口拉長能讓訊號平滑、precision 變好，但 reset time 會變長。告警設計的工作，就是找到一組規則，讓四個指標同時落在可以接受的範圍。

「什麼算重要事件」也需要定義，而第 32 章已經給了答案：**以 error budget 為尺度**。一個事件如果消耗了顯著比例的預算，它就是重要的；如果只消耗了微不足道的一點，即使看起來很嚇人，也不值得叫醒人。這把尺讓「重要」從感覺變成可以計算的數字。

## 34.5 Burn rate 的數學：從定義到三個公式

### 回顧定義

第 32 章定義了 **burn rate**：

```text
burn rate b = 實際錯誤率 e / SLO 允許的錯誤率 (1 − SLO)
```

Checkout 的 SLO 是 99.9%，允許的錯誤率是 0.1%。如果現在的錯誤率是 0.1%，burn rate 是 1，代表照這個速度，30 天的預算剛好在 30 天用完；錯誤率 1.44%，burn rate 是 14.4。這個數字的好處是它和 SLO 目標無關：不管服務是 99% 還是 99.99%，burn rate 10 都代表「比可持續速度快 10 倍」。

### 公式一：一個窗口內燒掉多少預算

設 SLO 窗口長度為 T（30 天 = 720 小時），我們觀察一段長度為 w 的時間，這段時間內的平均 burn rate 是 b。這段時間燒掉的預算比例是：

```text
預算消耗比例 f = b × w / T

算例：b = 14.4，w = 1 小時，T = 720 小時
      f = 14.4 × 1 / 720 = 0.02 = 2%
```

直覺上，burn rate 1 持續整個 T 會燒掉 100%；burn rate b 持續 w 時間，燒掉的就是 b × (w / T)。把公式反過來，就是設計告警參數的核心：

```text
b = f × T / w
「如果我希望在 w 時間內燒掉 f 比例的預算時告警，門檻就是 b」
```

### 公式二：照目前速度多久會燒完

```text
預算耗盡時間 = T / b

算例：b = 14.4 → 720 / 14.4 = 50 小時（約 2 天）
      b = 6    → 720 / 6    = 120 小時（5 天）
      b = 1    → 720 小時（剛好 30 天）
```

這個公式讓 burn rate 有了直覺意義：14.4 代表「兩天內燒完整個月的預算」，這顯然需要有人立刻處理；1 代表「剛好在月底用完」，需要注意但不急。

### 公式三：偵測要多久、偵測時燒了多少

假設錯誤率在某一刻突然從 0 跳到 e（burn rate b_e），告警規則是「w 窗口內的平均 burn rate ≥ 門檻 b_th」。窗口剛開始包含故障時，平均值會隨時間線性上升，到達門檻所需的時間是：

```text
偵測時間 t = w × b_th / b_e        （b_e ≥ b_th 時才會觸發）

算例（99.9% SLO，w = 1 小時，b_th = 14.4）：
  全面中斷 e = 100%  → b_e = 1000 → t = 60 × 14.4 / 1000 ≈ 0.86 分鐘（約 52 秒）
  錯誤率 e = 2%      → b_e = 20   → t = 60 × 14.4 / 20   = 43.2 分鐘
  錯誤率 e = 1.44%   → b_e = 14.4 → t = 60 分鐘
  錯誤率 e = 1%      → b_e = 10   → 永遠不會觸發
```

再算偵測那一刻已經燒掉多少預算：

```text
燒掉的預算 = b_e × t / T = b_e × (w × b_th / b_e) / T = b_th × w / T
```

b_e 被消掉了。這是一個很漂亮的結果：**不管故障多嚴重，這條規則觸發時燒掉的預算都是同一個數字**（上例是 2%）。嚴重的故障燒得快，所以很快就觸發；輕微的故障燒得慢，所以要等久一點。規則本身的意思就是「當預算被燒掉 2%、而且燒得夠快的時候叫我」，這正是我們想要的 precision 保證：每一次 page，背後至少是 2% 的預算。

## 34.6 從最天真的規則一路推導到 multi-window multi-burn-rate

有了四把尺與三個公式，就可以重走 SRE Workbook 的推導路線。每一步都修正上一步的一個缺點，最後得到業界普遍採用的設計。以下都以 Harbor checkout 的 99.9%、30 天 SLO 為例。

### 第一步：錯誤率超過 SLO 就告警

最直覺的規則是「過去 10 分鐘的錯誤率 ≥ 0.1% 就 page」，也就是 burn rate ≥ 1。

- **Detection time 很好**：全面中斷幾秒內就觸發。
- **Precision 極差**：10 分鐘的 burn rate 1 只燒掉 10 / 43,200 ≈ 0.02% 的預算。一個月有 4,320 個 10 分鐘，理論上每天最多可以響 144 次，而每一次都不構成真正的威脅。阿凱那週 search 的 4 次「一分鐘 2%」就是這類規則的產物。

### 第二步：把窗口拉長

改成「過去 36 小時的錯誤率 ≥ 0.1%」。36 小時是 30 天的 5%，所以觸發時至少燒掉 5% 的預算，precision 大幅改善，全面中斷的偵測時間也只要 36 × 60 × 0.001 ≈ 2 分鐘。

- **Reset time 極差**：一次 15 分鐘的全面中斷結束後，36 小時窗口的平均錯誤率要一天半才會降下來，告警會一直響。
- 長窗口的查詢也比較昂貴，需要保存與計算更多資料。

### 第三步：加上持續時間（for）

很多團隊的直覺修法是「錯誤率超過門檻且持續 1 小時才 page」，Prometheus 規則裡的 `for: 1h` 就是這個意思。Harbor 原本「持續 10 分鐘」的規則屬於這一類。

- **Recall 與 detection time 都變差**：全面中斷要等滿 1 小時才 page，而 99.9% 的整個月預算只有 43.2 分鐘的全面中斷，等到 page 時已經燒掉超過 100%。
- 斷斷續續的故障（例如錯誤率在門檻上下跳動）會一直重置計時器，可能永遠不觸發。

持續時間不是不能用，但它延遲的是「確認」，不是「計算」，不能代替正確的窗口設計。

### 第四步：用 burn rate 告警

回到公式 `b = f × T / w`。我們決定：「1 小時內燒掉 2% 預算」值得 page。代入得到 b = 0.02 × 720 / 1 = 14.4。規則變成「過去 1 小時的 burn rate ≥ 14.4」，也就是錯誤率 ≥ 1.44%。

- **Precision 好**：每次觸發至少燒掉 2%。
- **Detection time 好**：全面中斷約 52 秒觸發。
- **Recall 不足**：burn rate 10（錯誤率 1%）永遠不會觸發，但它會在 3 天內燒完整個月的預算。Harbor 折價券 bug 的 0.8% 錯誤率（burn rate 8）也一樣抓不到。
- **Reset time 不夠好**：一次夠長的全面中斷結束後，1 小時窗口要等到窗內故障分鐘數降到門檻以下才會停，大約是 60 × (1 − 14.4 / 1000) ≈ 59 分鐘（SRE Workbook 原文寫約 58 分鐘，差別只在取整與假設細節）。

補充一點：SRE Workbook 在這一步的原始例子用的是「1 小時燒掉 5%」，門檻是 36；它指出 burn rate 35 永遠不會觸發，卻能在約 20.5 小時燒完整個月的預算。這裡直接用下一步會採用的 2%（14.4）示範，結論相同：單一門檻一定有一段「夠傷但不會響」的盲區。

### 第五步：多個 burn rate

為了補上 recall，再加兩條較慢、較長的規則。SRE Workbook 建議的起點是：

| 嚴重度 | 燒掉的預算 | 長窗口 | burn rate 門檻 | 推導 |
|---|---|---|---|---|
| Page | 2% | 1 小時 | 14.4 | 0.02 × 720 / 1 |
| Page | 5% | 6 小時 | 6 | 0.05 × 720 / 6 |
| Ticket | 10% | 3 天 | 1 | 0.10 × 720 / 72 |

這三條規則對應三種故障型態：14.4 抓「兩天內會燒完」的急性故障；6 抓「五天內會燒完」、需要今天就處理的中度故障，Harbor 的折價券 bug 就屬於這一類；1 抓「照這樣下去月底會超標」的慢性問題，交給白天處理就好。

這一步解決了 recall，但 reset time 更糟了：6 小時與 3 天窗口在故障結束後要很久才會降下來。而且一次嚴重故障會讓三條規則同時觸發，值班者會收到多個通知。

### 第六步：每個長窗口配一個短窗口

最後一步是 **multi-window**：每條規則除了長窗口，再加一個**短窗口**，兩者都超過門檻才觸發。短窗口的長度通常取長窗口的 1/12：

```text
Page   ：1h  burn ≥ 14.4  且  5m  burn ≥ 14.4
Page   ：6h  burn ≥ 6     且  30m burn ≥ 6
Ticket ：3d  burn ≥ 1     且  6h  burn ≥ 1
```

短窗口的作用是回答「**現在**還在燒嗎？」。長窗口保證事件夠重要（燒掉足夠的預算），短窗口保證事件仍在發生。故障結束後，5 分鐘窗口在大約 5 分鐘內就降到門檻以下，整條規則跟著解除，reset time 從 59 分鐘縮短到約 5 分鐘。短窗口不會明顯拖慢偵測，因為錯誤率從平常的低水準突然升高時，短窗口的平均值會比長窗口上升得更快（全面中斷時，5 分鐘窗口約 4 秒就超過 14.4，1 小時窗口要約 52 秒），偵測時間仍由長窗口決定。

下面的圖把兩個窗口的關係畫出來：

```text
錯誤率
 100% ┤      ┌─────┐
      │      │故障 │
      │      │15 分│
   0% ┼──────┘     └──────────────────────────────────▶ 時間
             ▲     ▲    ▲                        ▲
             │     │    │                        │
          開始   結束  5m 窗口已不含故障          1h 窗口才不含故障
             │          → 短窗口低於門檻          → 若只有長窗口，告警響到這裡
          約 52 秒後兩窗口都 ≥ 14.4
          → page 觸發                    multi-window：在這裡就解除
```

逐步讀這張圖：故障開始後，1 小時與 5 分鐘窗口的平均 burn rate 都快速上升，大約 52 秒後兩者都超過 14.4，page 觸發。故障在第 15 分鐘結束，5 分鐘窗口再過約 5 分鐘就不再包含故障，短窗口條件失效，告警解除。如果只有 1 小時窗口，告警會一直響到故障完全滑出窗口，大約故障結束後 59 分鐘。

> [!tip] 短窗口為什麼是 1/12
> 1/12 不是物理常數，而是 SRE Workbook 建議的經驗值：短到能讓 reset time 夠短，又長到不會被單一分鐘的抖動觸發。你可以依服務流量調整，但調整前先用歷史資料回放，看 precision 與 reset time 的變化。

### 這套參數背後的假設

這組數字是起點，不是規定。它建立在幾個假設上，假設改變時參數也要跟著改：

- **SLO 窗口是 30 天**。若改成 28 天（T = 672 小時），「1 小時燒 2%」對應的門檻變成 0.02 × 672 = 13.44。很多工具直接沿用 14.4，差距不大，但要知道它從哪裡來。
- **「2%／1 小時值得 page」是一個政策選擇**。對很少發布、預算很寶貴的服務，可以把 page 的門檻降到 1%；對可以容忍較多波動的內部服務，可以只保留 6× 與 1× 兩條。
- **流量足夠大**。5 分鐘窗口要有足夠的請求數，平均值才有意義，下一節處理低流量的情況。

## 34.7 實務落地：規則、不同 SLO 的門檻與特殊服務

### 寫成 Prometheus 規則

Harbor 用 Prometheus 收集 metrics。實務上會先用 **recording rule**（預先計算並儲存結果的查詢）算出各窗口的錯誤率，告警規則再引用它們，避免每次評估都重新掃描大量資料。下面是 fast burn 那一條的寫法：

```yaml
groups:
  - name: checkout-slo
    rules:
      - record: job:checkout_errors:ratio_rate1h
        expr: |
          sum(rate(http_requests_total{job="checkout", code=~"5.."}[1h]))
          /
          sum(rate(http_requests_total{job="checkout"}[1h]))
      - record: job:checkout_errors:ratio_rate5m
        expr: |
          sum(rate(http_requests_total{job="checkout", code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{job="checkout"}[5m]))
      - alert: CheckoutErrorBudgetFastBurn
        expr: |
          job:checkout_errors:ratio_rate1h > (14.4 * 0.001)
          and
          job:checkout_errors:ratio_rate5m > (14.4 * 0.001)
        labels:
          severity: page
          team: payments
        annotations:
          summary: "checkout 正以 ≥14.4 倍速度燃燒 error budget（約 2 天燒完 30 天預算）"
          runbook: "runbooks/checkout-slo-burn.md"
```

這裡有幾個值得注意的細節。`code=~"5.."` 只是示意，真實的 good／bad 定義必須和第 32 章 SLO 文件裡的 SLI 定義一致，包括分母的排除規則；告警和 SLO 報表若用不同的定義，就會出現「報表說沒事、pager 卻在響」或反過來的狀況。`0.001` 是 1 − SLO，最好從同一個設定來源產生，而不是手動寫在每一條規則裡。另外，Prometheus 提供 `promtool test rules` 可以替告警規則寫單元測試：給定一段假的時間序列，驗證規則是否在預期的時間觸發。告警規則是程式碼，應該和程式碼一樣經過 review 與測試。

### 不同 SLO 下的門檻

Burn rate 門檻固定，但換算成錯誤率會隨 SLO 改變：

| SLO | 允許錯誤率 | 14.4× 對應錯誤率 | 6× 對應錯誤率 | 1× 對應錯誤率 | 可能的最大 burn rate |
|---|---|---|---|---|---|
| 99% | 1% | 14.4% | 6% | 1% | 100 |
| 99.9% | 0.1% | 1.44% | 0.6% | 0.1% | 1,000 |
| 99.95% | 0.05% | 0.72% | 0.3% | 0.05% | 2,000 |
| 99.99% | 0.01% | 0.144% | 0.06% | 0.01% | 10,000 |

最後一欄是全面中斷時的 burn rate，也就是 1 / (1 − SLO)。它揭露了一個容易忽略的問題：**SLO 越低，最大 burn rate 越小**。一個 90% 的 SLO，全面中斷的 burn rate 只有 10，永遠到不了 14.4，fast burn 規則形同虛設。SLO 低於約 93% 時（1 / 14.4 ≈ 6.9% 的允許錯誤率），就必須改用較低的門檻，或重新思考這個 SLO 是否真的代表使用者需要的品質。

反過來，99.99% 的服務全面中斷時 burn rate 高達 10,000，fast burn 規則幾秒就能觸發，但這類服務的問題在另一端：整個月只有 4.32 分鐘的預算，任何需要人類介入的流程都太慢，告警只能作為自動化恢復失敗時的最後保險。

### 低流量服務

Harbor 的賣家後台每小時只有幾十個請求。在這種流量下，1 小時窗口裡 1 次失敗就可能是 3% 的錯誤率，burn rate 30，立刻 page，而那可能只是一個使用者的網路斷了。常見的對策有：

- **產生 synthetic traffic**：用 probe 定期執行關鍵操作，讓分母穩定。代價是 probe 未必覆蓋真實使用者的所有路徑。
- **合併服務**：把幾個相關的低流量內部服務合併成一個 SLO 與一組告警，讓事件數足夠。
- **加上最低事件數條件**：例如「窗口內至少 50 個請求才評估」。這能減少誤報，但要清楚它也會讓真正的低流量故障不被告警，必須搭配 probe。
- **在產品上降低單次失敗的影響**：例如 client 自動重試，讓單一失敗不再是使用者失敗。
- **接受較寬的 SLO 或較長的窗口**，把 page 留給真正有使用者規模的服務。

### 服務很多時：用類別而不是逐一調整

當 Harbor 長到幾十個服務、上百個 endpoint，為每個 endpoint 調一組門檻會變成沒人維護得了的工作。SRE Workbook 建議的做法是把請求依重要性分成少數幾個類別（原書的例子是 `CRITICAL`、`HIGH_FAST`、`HIGH_SLOW`、`LOW`、`NO_SLO` 五類；Harbor 可以簡化成「關鍵互動」「一般互動」「背景作業」），每個類別共用一組 SLO 與告警參數，新服務只要宣告自己屬於哪一類。這樣告警設定的數量和類別數成正比，而不是和 endpoint 數成正比。

## 34.8 Alert 送出之後：路由、去重與內容

規則決定「何時觸發」，但值班者實際收到什麼，還取決於告警的傳遞層。以 Prometheus 生態系的 Alertmanager 為例，這一層負責把原始告警整理成人能處理的通知：

```text
Prometheus 規則評估
        │  （每條規則每次評估都可能產生告警）
        ▼
┌─────────────────────────────────────────┐
│ Alertmanager                            │
│  grouping   ：同一服務、同一類的告警合併 │
│  inhibition ：上游故障時抑制下游症狀     │
│  silence    ：計畫中的維護暫時靜音       │
│  routing    ：依 team／severity 分派     │
└──────────────┬──────────────────────────┘
               ├── severity=page   → 值班 pager（未 ack 則升級給 secondary）
               ├── severity=ticket → 工單系統，指定 owner 與期限
               └── 其他            → 聊天頻道或只留在 dashboard
```

這張圖由上往下讀：規則評估產生原始告警後，先經過合併、抑制、靜音三道整理，再依標籤路由到不同的出口。

- **Grouping**（分組）：一次資料庫故障可能讓 50 個 endpoint 同時觸發告警。依服務與告警名稱分組後，值班者收到的是一則「checkout 有 50 個 endpoint 異常」，而不是 50 則通知。
- **Inhibition**（抑制）：如果「整個區域網路中斷」的告警已經觸發，同一區域內所有下游服務的告警可以被抑制，因為它們只是同一個原因的症狀。Harbor 上游的 payments 掛掉時，checkout、訂單、通知都會跟著出錯，只有 payments 的 owner 需要被叫醒，其他團隊收到資訊性通知即可。
- **Silence**（靜音）：計畫中的資料庫維護期間，事先建立有時限的靜音，結束時間到了自動失效。永久的 silence 是一種隱藏的告警刪除，應該定期清理。
- **Routing 與 escalation**（路由與升級）：page 送給服務 owner 團隊的值班者；如果 primary 在一定時間內沒有 ack（確認收到），自動升級給 secondary。

### 一則好的 page 包含什麼

值班者被叫醒的第一分鐘最需要的是脈絡。Harbor 的 page 範本規定至少包含：

```text
[PAGE] checkout error budget fast burn（severity: page）
影響    ：checkout 錯誤率 3.1%（1h），burn rate 31；約 23 小時燒完 30 天預算
範圍    ：全部區域；集中在付款確認步驟
SLO     ：checkout availability 99.9% / 30d，本月已用 41%
最近變更：14:02 checkout v2026.10.01-3 部署至 100%；13:40 coupon flag 開啟 50%
連結    ：SLO dashboard、相關 trace 查詢、runbook
第一步  ：若與最近部署時間吻合，先 rollback 再調查（runbook 第 2 節）
```

「最近變更」與「第一步」是最有價值的兩行。第 32 章提過，預算突然下降時第一個問題通常是「那時候發布了什麼」，把答案直接放進 page，能省下事故最初幾分鐘的摸索。Runbook 則要寫清楚安全的第一步，例如 rollback 或關閉 flag，而不是「聯絡某某人」（第 43 章會詳談 runbook 與 troubleshooting）。

### 監控監控系統本身

告警系統本身也會壞：Prometheus 當機、Alertmanager 設定錯誤、pager 服務的整合 token 過期。最危險的是這些故障都很「安靜」，因為壞掉的正是負責發出聲音的那一層。常見的保護是 **dead man's switch**：設一條永遠在觸發的告警，送到外部的監看服務；如果外部服務一段時間沒收到它，就代表告警管線斷了，由另一條獨立的路徑通知人。另外，從不同網路、不同供應商執行的外部 probe，也能在整個監控系統和服務一起掛掉時提供最後一道訊號。

## 34.9 Alert fatigue 與 alert 的生命週期

### 疲勞是設計問題，不是個人問題

阿凱聽到震動就繼續睡，不是因為阿凱不負責任，而是人對重複且多半無害的刺激會自然習慣化。把這當成個人紀律問題來要求「每個 page 都要認真看」，只會讓值班變得更痛苦，而不會讓告警變得更有用。正確的做法是把 page 數量當成一個需要被管理的系統指標。

SRE 原書在〈Being On-Call〉中提到，Google 的經驗是處理一次事故（包括調查、修復、postmortem）平均需要約 6 小時，因此一個 12 小時的班次最多只能承受約 2 次事故。這個數字不需要照抄，但它提供了一個量級感：如果你的值班者每個班次收到十幾個 page，那裡面必然大多是雜訊，或者系統本身有需要投資的可靠性問題。第 43 章會完整討論 on-call 的負荷與輪值設計。

### 一條 alert 的一生

告警和程式碼一樣有生命週期，而且同樣需要 owner：

```text
提案 ──▶ 影子期 ──▶ 正式上線 ──▶ 定期檢討 ──┬─▶ 保留
 │        │                                  ├─▶ 調整門檻／降級成 ticket
 │        │                                  ├─▶ 自動化（每次動作都一樣）
 │        │                                  └─▶ 刪除
 │        └ 送到非 page 頻道 1–2 週，量它會響幾次、有幾次需要行動
 └ 回答：保護哪個 SLO／哪種傷害？誰會被叫醒？能做什麼？預期多久響一次？
```

- **提案**：新增 page 前先回答四個問題：它保護哪個 SLO 或哪種不可逆傷害、誰會被叫醒、收到後能做什麼（runbook 是什麼）、預期多久響一次。答不出來的，先做成 dashboard。
- **影子期**：新規則先送到一個不會叫醒人的頻道，觀察一到兩週。若影子期內響了 20 次，其中只有 1 次需要行動，這條規則不應該上線成 page。
- **定期檢討**：Harbor 在每週 on-call 交接時花 15 分鐘看上週的每一個 page，標記它是否需要行動、是否有用、是否重複。每季再看一次所有告警的統計：觸發次數、可行動比例、夜間觸發比例、從觸發到 ack 的時間。
- **退場**：長期不觸發的告警不一定該刪（它可能保護的是罕見但嚴重的事件），但長期觸發卻沒人行動的告警一定要處理：調整、降級、自動化或刪除。

檢討時最有用的單一問題是：「**這個 page 讓值班者做了什麼？**」如果答案是「什麼都沒做」，它就不是 page。如果答案是「每次都做同一件事」，它應該變成自動化。如果答案是「做了，但其實可以等到早上」，它應該是 ticket。

> [!example] 例子
> Harbor 第一次檢討時，把 37 條會 page 的規則降到 9 條：checkout、search、cart、payments 各 2 條 burn rate page（fast 與 slow），加上一條「磁碟 4 小時內會滿」的預測性 page。CPU、記憶體、單次 pod 重啟全部移到 dashboard；憑證到期與 3 天 slow burn 改成 ticket。下一個月的 page 數從每週 37 次降到每週 3 次，而折價券那類的慢性問題會在大約 4–5 小時內觸發 6× 規則。

## 34.10 動手寫：模擬三種告警策略

下面的程式模擬 Harbor checkout 的每分鐘流量（每分鐘 2,000 個請求、平常有 0.02% 的背景錯誤，這兩個都是為了示範而假設的參數；前 3 天只當作歷史資料，讓 3 天窗口有值，告警只在之後的 4 天評估），注入不同型態的故障，比較三種策略的表現：天真的「5 分鐘錯誤率超過 SLO」、單一的「1 小時 burn rate ≥ 14.4」，以及完整的 multi-window multi-burn-rate。

```python
import math
import random

SLO = 0.999
BUDGET = 1 - SLO                   # 允許的錯誤率 0.1%
PERIOD_MIN = 30 * 24 * 60          # SLO 窗口：30 天（分鐘）
RPM = 2000                         # 每分鐘請求數
BASE_ERR = 0.0002                  # 平常的背景錯誤率（burn rate 0.2）
HISTORY = 3 * 24 * 60              # 事故前先跑 3 天，讓 3 天窗口有資料
HORIZON = 7 * 24 * 60              # 每個情境模擬 7 天


def poisson(rng, lam):
    if lam > 50:                   # 大量時用常態近似
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def timeline(incidents, blips_per_day=0, seed=7):
    """incidents: [(開始分鐘, 持續分鐘, 錯誤率)]，回傳每分鐘的 (總數, 錯誤數)。"""
    rng = random.Random(seed)
    err = [BASE_ERR] * HORIZON
    for _ in range(blips_per_day * HORIZON // 1440):   # 短暫抖動：重啟、GC、部署切換
        start = rng.randrange(HORIZON - 2)
        for m in range(start, start + rng.choice((1, 2))):
            err[m] = max(err[m], 0.01)
    for start, length, rate in incidents:
        for m in range(start, start + length):
            err[m] = rate
    total = [RPM] * HORIZON
    bad = [poisson(rng, RPM * e) for e in err]
    return total, bad


class Windows:
    def __init__(self, total, bad):
        self.t, self.b = [0], [0]
        for x, y in zip(total, bad):
            self.t.append(self.t[-1] + x)
            self.b.append(self.b[-1] + y)

    def burn(self, minute, length):
        lo = max(0, minute + 1 - length)
        t = self.t[minute + 1] - self.t[lo]
        b = self.b[minute + 1] - self.b[lo]
        return (b / t) / BUDGET if t else 0.0


H = 60
STRATEGIES = {
    "naive 5m>SLO": [("page", 5, None, 1.0)],
    "1h burn>=14.4": [("page", H, None, 14.4)],
    "multi-window": [("page", H, 5, 14.4), ("page", 6 * H, 30, 6.0),
                     ("ticket", 72 * H, 6 * H, 1.0)],
}


def firing(rules, w, minute, severity):
    return any(w.burn(minute, long_w) >= threshold
               and (short_w is None or w.burn(minute, short_w) >= threshold)
               for sev, long_w, short_w, threshold in rules if sev == severity)


def run(name, incidents, blips_per_day=0):
    total, bad = timeline(incidents, blips_per_day)
    w = Windows(total, bad)
    allowed_bad = RPM * PERIOD_MIN * BUDGET
    print(f"\n== {name}")
    for label, rules in STRATEGIES.items():
        parts = []
        for sev in ("page", "ticket"):
            on = [m for m in range(HISTORY, HORIZON) if firing(rules, w, m, sev)]
            if not incidents:
                if sev == "page":
                    episodes = sum(1 for m in on if m - 1 not in on)
                    parts.append(f"{(HORIZON - HISTORY) // 1440} 天內 page {episodes} 次")
                continue
            if not on:
                parts.append(f"{sev} 無")
                continue
            start, length, _ = incidents[0]
            first, last = on[0], on[-1]
            used = sum(bad[start:first + 1]) - RPM * BASE_ERR * (first + 1 - start)
            text = f"{sev} 第 {first - start} 分（已燒 {used / allowed_bad:.1%}）"
            if sev == "page":
                text += f"，結束後 {max(0, last - start - length)} 分才解除"
            parts.append(text)
        print(f"  {label:<14} " + "；".join(parts))


T0 = HISTORY
run("A. 全面中斷 100% × 15 分鐘", [(T0, 15, 1.0)])
run("B. 2% 錯誤 × 3 小時（burn 20）", [(T0, 180, 0.02)])
run("C. 0.8% 錯誤 × 12 小時（burn 8）", [(T0, 720, 0.008)])
run("D. 0.25% 錯誤 × 3 天（burn 2.5）", [(T0, 72 * H, 0.0025)])
run("E. 沒有事故，只有每天 4 次 1–2 分鐘的 1% 抖動", [], blips_per_day=4)
```

執行結果：

```text
== A. 全面中斷 100% × 15 分鐘
  naive 5m>SLO   page 第 0 分（已燒 2.3%），結束後 3 分才解除；ticket 無
  1h burn>=14.4  page 第 0 分（已燒 2.3%），結束後 58 分才解除；ticket 無
  multi-window   page 第 0 分（已燒 2.3%），結束後 28 分才解除；ticket 第 3 分（已燒 9.3%）

== B. 2% 錯誤 × 3 小時（burn 20）
  naive 5m>SLO   page 第 0 分（已燒 0.0%），結束後 3 分才解除；ticket 無
  1h burn>=14.4  page 第 43 分（已燒 2.0%），結束後 15 分才解除；ticket 無
  multi-window   page 第 43 分（已燒 2.0%），結束後 20 分才解除；ticket 第 173 分（已燒 8.0%）

== C. 0.8% 錯誤 × 12 小時（burn 8）
  naive 5m>SLO   page 第 0 分（已燒 0.0%），結束後 3 分才解除；ticket 無
  1h burn>=14.4  page 無；ticket 無
  multi-window   page 第 263 分（已燒 4.8%），結束後 6 分才解除；ticket 第 442 分（已燒 8.0%）

== D. 0.25% 錯誤 × 3 天（burn 2.5）
  naive 5m>SLO   page 第 1 分（已燒 0.0%），結束後 2 分才解除；ticket 無
  1h burn>=14.4  page 無；ticket 無
  multi-window   page 無；ticket 第 1500 分（已燒 8.0%）

== E. 沒有事故，只有每天 4 次 1–2 分鐘的 1% 抖動
  naive 5m>SLO   4 天內 page 16 次
  1h burn>=14.4  4 天內 page 0 次
  multi-window   4 天內 page 0 次
```

逐段解讀：

1. **`timeline` 產生資料**。每分鐘的錯誤數用 Poisson 分佈抽樣，模擬真實流量的隨機波動；`blips_per_day` 注入短暫的 1% 抖動，代表 pod 重啟、GC 停頓或部署切換這類「看起來像事故但其實不重要」的事件。真實系統裡，這兩個陣列就是 Prometheus 裡 `http_requests_total` 依狀態碼拆開的 counter。
2. **`Windows` 用前綴和計算任意窗口的 burn rate**。前綴和讓「過去 1 小時」「過去 3 天」的錯誤比例都能在常數時間算出。Prometheus 的 `rate()` 搭配 recording rule 做的是同一件事：預先把常用窗口算好，告警只做比較。
3. **`STRATEGIES` 是三套規則**。每條規則是（嚴重度、長窗口、短窗口、門檻）。multi-window 的三條正是 34.6 推導出的 14.4／6／1，短窗口都是長窗口的 1/12。
4. **情境 A（全面中斷）**：三種策略都在第一分鐘就 page（真實的偵測時間約 52 秒，這裡以分鐘為解析度）。差別在解除：單一 1 小時窗口在故障結束後還響了 58 分鐘，和 34.6 算出的約 59 分鐘吻合（程式以分鐘為解析度，印出的是最後一個仍在觸發的分鐘，所以比理論值少約 1 分鐘）。multi-window 的 page 在 28 分鐘後解除，這是 6× 規則的 30 分鐘短窗口造成的；14.4× 規則本身大約 5 分鐘就解除了。這也說明為什麼 fast 與 slow 兩條 page 要在 Alertmanager 中 group 成一則通知。注意 multi-window 同時開了一張 ticket：15 分鐘全面中斷等於燒掉三分之一的月預算，即使已經恢復，也值得在白天追蹤 postmortem。
5. **情境 B（2% 錯誤）**：天真規則立刻 page，看起來最快，但同一條規則在情境 E 的 4 天內誤報了 16 次（每天 4 次）。burn rate 規則在第 43 分鐘觸發，和公式 `60 × 14.4 / 20 = 43.2` 完全一致，此時燒掉的預算正好是 2%。
6. **情境 C（0.8% 錯誤，對應 Harbor 的折價券 bug）**：單一 1 小時規則完全抓不到。multi-window 的 6× 規則在第 263 分鐘觸發，理論值是 `360 × 6 / 8 = 270` 分鐘，略早是因為背景錯誤也貢獻了一點 burn rate（約提早 3 分鐘），其餘是 Poisson 抽樣的隨機波動。這時燒掉約 5% 的預算，與 6× 規則「6 小時燒 5%」的設計一致。
7. **情境 D（0.25% 錯誤三天）**：沒有 page，只有 ticket，在第 25 小時左右開出，此時已燒 8%。這是一個慢性問題該有的待遇：需要處理，但不需要叫醒任何人。
8. **情境 E（只有抖動）**：天真規則 4 天 page 16 次，全部是誤報；burn rate 規則一次都沒有。這就是阿凱那一週的翻版。

把結果用四把尺總結：天真規則 detection time 最好、precision 最差；單一 burn rate 規則 precision 好，但 recall 與 reset time 不足；multi-window multi-burn-rate 在四個指標上都沒有明顯短板。在真實系統中，你會用歷史資料（過去幾個月的事故與平常日子）跑同樣的回放，來驗證門檻是否適合自己的服務。

## 34.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會失敗 | 具體情境 | 對策 |
|---|---|---|---|
| 只靠 SLO burn rate 告警 | 傷害不在 SLI 裡 | SLI 只量 HTTP 狀態碼，重複扣款的回應都是 200，burn rate 毫無變化 | SLI 定義要隨事故檢討更新；資料正確性另設檢查與告警 |
| Multi-window 參數照抄 | 服務特性和假設不同 | SLO 只有 90%，14.4× 規則永遠不會觸發 | 依 `b = f × T / w` 重新推導，並用歷史資料回放驗證 |
| 低流量服務套用一般規則 | 單一失敗就觸發 page | 賣家後台夜間每小時 10 個請求，一次失敗 burn rate 就破百 | Synthetic probe、合併服務、最低事件數、較長窗口 |
| 用 `for` 持續時間壓誤報 | 嚴重故障被延遲 | Harbor 原本「持續 10 分鐘才 page」，金流中斷第 10 分鐘才通知 | 用 burn rate 與短窗口控制 precision，`for` 只做很短的確認 |
| 太積極的 inhibition | 真正的獨立故障被藏起來 | 區域網路告警抑制所有下游，但同時另一個服務因自己的部署而壞 | 抑制範圍以明確的依賴關係限定，被抑制的告警仍可在 dashboard 查到 |
| 告警與 SLO 報表用不同定義 | 兩邊數字對不上，信任崩潰 | 告警排除 429，報表沒有排除，週報說燒了 30%，告警從沒響過 | 告警規則與 SLO 報表從同一份 SLI 設定產生 |
| 告警管線本身故障 | 所有告警一起沉默 | Pager 整合 token 過期，三天內沒有任何 page，大家以為系統很穩 | Dead man's switch、外部 probe、定期測試 page |

## 34.12 AI 時代：什麼變了？

AI 在告警上的影響分成兩面：AI 可以讓告警系統更好用，但 AI 也帶來了新的告警對象。

**第一，AI 適合讓 page 更有脈絡，而不是決定要不要 page。** Pager 的關鍵路徑需要確定性：同樣的資料進來，同樣的告警出去，而且能被事後重現與稽核。大型語言模型的輸出有隨機性，模型版本升級可能改變判斷，模型服務本身也可能在事故中不可用（特別是當事故就是雲端或網路問題時）。因此比較穩健的做法是：觸發條件維持在版本化、可測試的 burn rate 規則；AI 在 page 送出**之後**做 **enrichment**（加料），例如整理最近的部署、錯誤最多的 endpoint、相關 trace、類似的歷史事故，附在 page 後面。Enrichment 要有時間上限與 fallback：AI 慢了或失敗了，原始 page 照樣準時送達。

**第二，AI 適合做告警的檢討工作。** 每季檢討上百條告警、上千次觸發，是很耗時的分析工作。AI 可以讀取觸發紀錄、ack 時間、後續動作與 postmortem，整理出「長期觸發但沒人行動」「總是和另一條一起響」「夜間觸發比例異常高」的候選清單，並草擬調整方案與對應的 `promtool` 測試。最後決定刪除或降級的仍然是服務 owner，因為只有 owner 知道某條很少響的告警是不是在保護一個罕見但致命的情況。

**第三，告警風暴時的分群與摘要。** 一次大故障可能在幾分鐘內產生數百則告警。AI 可以依時間、拓撲與錯誤訊息把它們分群，指出最可能的起點，幫助 incident commander（第 44 章）快速建立全貌。這是輔助判斷，不是結論：摘要必須附上它依據的原始告警與查詢，讓人能驗證。

**第四，AI 產品本身需要新的告警設計。** 第 32 章為 Harbor 的 AI 客服 agent 定義了 task success、groundedness、unsafe action rate 等 SLI。它們在告警上的特性很不一樣：

- **品質類 SLI 通常有延遲**：groundedness 靠抽樣標註或 LLM-as-judge 評分，可能晚幾小時才有資料。這類 SLI 不適合 fast burn page，比較適合 6× 或 1× 的 slow burn 與 ticket。
- **安全類事件適合計數告警**：「agent 嘗試超出授權的退款」即使比例很低也不能接受，適合用「窗口內出現 N 次」直接 page，而不是用比例的 burn rate。
- **成本也可以有 burn rate**：如果 AI 客服每月有固定的模型呼叫預算，同一套 `b = f × T / w` 的邏輯可以用在 token 花費上，例如「1 小時內燒掉月預算的 2%」就通知，用來抓 prompt 迴圈或被濫用的情況。
- **快速訊號仍然來自傳統指標**：tool 呼叫錯誤率、guardrail 阻擋率、回應延遲，這些都是即時可得的，應該和一般服務一樣用 multi-window burn rate。

**第五，AI 維運 agent 收到告警後的動作要有邊界。** 如果讓 agent 在收到 page 後自動執行 runbook 的第一步，例如 rollback 最近一次部署，這個動作必須是事先核准、可逆、範圍有限的，並且留下完整紀錄。Page 仍然要送給人：agent 可以先動手止血，但「是否已經恢復、是否需要升級」的判斷，以及對結果的責任，仍在值班者身上（第 31 章的漸進授權）。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 在 page 送出後附上最近變更、主要錯誤、相關 trace 與類似歷史事故 | 觸發條件是版本化、可測試的確定性規則；enrichment 有 timeout，失敗時原始 page 照常送出 |
| 分析告警歷史，列出長期無行動、重複、夜間過多的候選規則並草擬修改 | 刪除或降級由服務 owner 核准；罕見但高嚴重度的告警要特別說明保留理由 |
| 草擬 burn rate recording rule、告警規則與 `promtool` 測試案例 | 規則經 code review；SLI 定義必須與 SLO 文件一致，AI 不能自行改變分母排除條件 |
| 告警風暴時依拓撲與時間分群，推測起點服務 | 摘要附上原始告警與查詢；incident commander 決定處理方向 |
| 依核准的 runbook 執行有限度、可逆的第一步止血動作 | 動作清單事先核准並經 game day 驗證；每次執行都通知值班者並留下審計紀錄 |

> [!ai] AI 提醒
> 不要讓 AI 決定「這個 page 是不是誤報，所以不用通知人」。這等於把 recall 的責任交給一個無法事後重現的判斷。如果某條規則誤報多到需要 AI 過濾，正確的做法是修規則，而不是在規則和人之間加一層模型。

## 34.13 專家怎麼想

- **「這個 page 讓值班者做了什麼？」** 資深 SRE 檢討告警時，第一個問題永遠是行動。沒有行動的 page 是雜訊，每次行動都一樣的 page 是待自動化的 toil，可以等到早上的 page 是 ticket。
- **用預算說話，而不是用感覺。** 「錯誤率 5% 很嚴重」這句話沒有意義，除非你知道它持續多久、SLO 是多少。專家會把任何告警門檻換算成「觸發時燒掉多少預算、多久會燒完」，再判斷它是否值得叫醒人。
- **先問 SLO，再問告警。** 很多告警問題其實是 SLO 問題：SLI 沒有量到真正的傷害，或者 SLO 訂得不合理。如果使用者很痛但 burn rate 沒動，該修的是 SLI，而不是多加一條 CPU 告警。
- **Page 數量是值班者健康與系統可靠性的共同指標。** 每個班次的 page 太多，若大多是誤報就修告警，若大多是真事故就投資可靠性。兩種情況都不應該靠「值班者多努力一點」解決。
- **告警是程式碼，要測試、review、有 owner。** 一條沒有人知道為什麼存在的告警，跟一段沒有人敢刪的程式碼一樣危險。專家會要求每條 page 都連到 runbook 與 SLO，並在 repo 中和服務一起版本化。
- **定期驗證告警會響。** 告警最常見的失敗不是誤報，而是在需要的時候沒有響。用 game day（第 46 章）或在 staging 注入故障，確認整條路徑從 metrics 到 pager 都是通的。

## 34.14 動手練習

1. 對一個 99.95%、30 天的 SLO，用 `b = f × T / w` 算出 fast burn（2%／1 小時）、slow burn（5%／6 小時）與 ticket（10%／3 天）的門檻，並換算成錯誤率。若 SLO 窗口改成 28 天，門檻各變成多少？
2. 修改 34.10 的程式，加入情境 F：錯誤率在 0% 與 3% 之間每 10 分鐘交替一次，持續 6 小時。比較三種策略的偵測時間，並說明為什麼這種「斷斷續續」的故障特別容易讓 `for` 持續時間類的規則失效（可以自己加一個「錯誤率 > 1.44% 持續 10 分鐘」的策略來驗證）。
3. 修改程式，把 `RPM` 改成 5（低流量服務），重新執行情境 E。觀察 multi-window 規則的誤報次數，然後實作一個「窗口內至少 100 個請求才評估」的條件，比較前後差異，並說明這個條件的代價。
4. 列出你熟悉的系統（或 Harbor）目前所有會 page 的告警，逐一回答：它保護哪個 SLO 或哪種傷害？收到後能做什麼？上個月響了幾次、有幾次需要行動？最後提出要保留、降級、自動化或刪除的建議。
5. 為 Harbor 的 checkout 寫一份 page 範本與對應的 runbook 前三步，確保值班者在不認識這個服務的情況下，第一分鐘就知道影響、範圍與最安全的第一個動作。
6. 為 Harbor 的 AI 客服 agent 設計告警：哪些 SLI 用 multi-window burn rate、哪些用計數告警、哪些只做 ticket？為每一條說明理由，並設計 AI enrichment 的 timeout 與 fallback。

## 本章重點整理

- Alert 是打斷人的 API，每一次 page 都在消耗值班者的注意力與整個告警系統的可信度。
- 通知分成 page、ticket、log／dashboard 三種；值得 page 的事件要同時緊急、可行動、對使用者可見，而且需要人的判斷。
- 用 symptom 來 page、用 cause 來診斷；即將耗盡的資源、無流量時段的故障、資料正確性與安全是 cause alert 的合理例外。
- 評估告警規則用四把尺：precision、recall、detection time、reset time，它們彼此拉扯，設計就是找平衡。
- 窗口 w 內平均 burn rate b 燒掉的預算是 b × w / T，反推門檻是 b = f × T / w；預算耗盡時間是 T / b。
- 單一窗口的 burn rate 規則觸發時燒掉的預算固定是 b_th × w / T，與故障嚴重度無關，這保證了 page 的 precision。
- 30 天 SLO 的建議起點：14.4×（1 小時，短窗 5 分鐘）與 6×（6 小時，短窗 30 分鐘）page，1×（3 天，短窗 6 小時）ticket。
- 短窗口回答「現在還在燒嗎」，讓 reset time 從長窗口的數十分鐘縮短到幾分鐘，又幾乎不拖慢偵測。
- 參數依賴假設：SLO 低於約 93% 時 14.4× 永遠無法觸發；28 天窗口的對應門檻是 13.44；低流量服務需要 probe、合併或最低事件數。
- 告警規則與 SLO 報表必須從同一份 SLI 定義產生，並像程式碼一樣 review 與測試。
- Grouping、inhibition、silence、routing 與 escalation 決定值班者實際收到什麼；好的 page 附上影響、範圍、最近變更與安全的第一步。
- 告警系統本身要被監控，dead man's switch 與外部 probe 是常見做法。
- Alert fatigue 是設計問題；每條告警都要經過提案、影子期、上線、定期檢討與退場的生命週期。
- AI 適合做 enrichment、告警檢討與風暴分群，不適合放在決定是否 page 的關鍵路徑；AI 產品的品質、安全、成本訊號需要不同類型的告警。

## 延伸問答

> [!question]- Q1. Harbor 的 search 服務 SLO 是 99.95%（30 天）。過去 1 小時的錯誤率是 1%，fast burn 規則會觸發嗎？如果錯誤率從 1 小時前才開始，大約什麼時候觸發？
> 先算 burn rate：99.95% 允許的錯誤率是 0.05%，所以 b = 1% / 0.05% = 20。Fast burn 的門檻是 14.4，20 大於 14.4，所以會觸發；同時短窗口（5 分鐘）只要錯誤仍在持續，也會是 20，兩個條件都成立。
>
> 偵測時間用 t = w × b_th / b_e = 60 × 14.4 / 20 = 43.2 分鐘。也就是錯誤率從 0 跳到 1% 之後大約 43 分鐘 page。這時燒掉的預算是 b_th × w / T = 14.4 / 720 = 2%，和 SLO 是多少無關。這題的重點是：同樣 1% 的錯誤率，對 99% 的服務是 burn rate 1、只需要 ticket；對 99.95% 的服務是 burn rate 20、需要 page。錯誤率本身沒有意義，要和 SLO 一起看。

> [!question]- Q2. 既然 1 小時窗口已經能確保事件夠重要，為什麼還要加 5 分鐘的短窗口？只用長窗口有什麼具體問題？
> 長窗口負責「重要性」，但它對「現在」很遲鈍。一次 15 分鐘的全面中斷結束後，1 小時窗口仍然包含那些失敗，平均值要大約 59 分鐘才會降回門檻以下，告警會一直響。這段時間值班者無法從告警狀態判斷系統是否已經恢復，若同時有新的問題發生，也會被這個「殘響」蓋住。
>
> 加上 5 分鐘短窗口後，規則變成「重要而且仍在發生」。故障結束約 5 分鐘後短窗口就低於門檻，告警解除。短窗口不會明顯拖慢偵測，因為故障開始時短窗口的平均值上升得比長窗口快，長窗口才是偵測的瓶頸。另一個附帶好處是：如果規則因為流量資料延遲而在故障結束後才評估，短窗口能避免為一個已經結束的事件叫醒人。

> [!question]- Q3. 你是凌晨 3 點的值班者，收到一個 page：「payments 服務 3 台機器 CPU 超過 90%」。SLO dashboard 上 payments 的 burn rate 是 0.3。你會怎麼處理這個 page，以及這條規則？
> 當下要做的是快速確認使用者沒有受傷：burn rate 0.3 代表錯誤率遠低於 SLO 允許的水準，可以再看一眼延遲 SLI 與飽和度（例如佇列長度、連線池），確認沒有即將惡化的跡象。如果都正常，記下觀察後 ack，不需要在半夜做擴容或重啟這類有風險的動作。
>
> 真正要處理的是規則本身。CPU 高是 cause 層級的訊號，在這個情境下既不緊急、也沒有可行動的步驟、使用者也看不到，不符合 page 的三個條件。隔天在 on-call 交接時應該提出：把它降級成 dashboard 訊號，或改成「CPU 長時間高且延遲 SLI 開始燃燒」的組合條件；如果它代表容量逐漸不足，應該變成容量規劃的 ticket（第 36 章）。記錄這次 page 的「無行動」標記，讓季度檢討有資料。

> [!question]- Q4. 一個內部服務的 SLO 是 90%。團隊照抄了 14.4×／6×／1× 的規則，結果服務完全掛掉兩小時都沒有 page。為什麼？要怎麼修？
> 90% 的 SLO 允許 10% 的錯誤率，全面中斷時錯誤率 100%，burn rate 只有 100% / 10% = 10。Fast burn 的門檻 14.4 永遠到不了，所以那條規則形同不存在。6× 規則理論上能觸發，但 6 小時窗口的平均 burn rate 要到 6，在全面中斷下需要 360 × 6 / 10 = 216 分鐘，也就是 3.6 小時，比這次事故還長。
>
> 修法有兩個方向。第一是重新推導門檻：用 b = f × T / w，決定「多快燒掉多少預算值得 page」，例如改成 1 小時燒掉 1%（b = 7.2）或更短窗口，並確認門檻低於最大 burn rate 10。第二是檢討 SLO 本身：一個允許 10% 失敗的 SLO 是否真的代表使用者需要的品質？如果服務掛掉兩小時大家都覺得是事故，SLO 可能訂得太鬆，應該和使用者一起重新討論。

> [!question]- Q5. Harbor 的上游 payments 中斷時，checkout、訂單、通知、AI 客服四個團隊同時被 page，四個值班者都在查同一個問題。要怎麼設計才能避免這種 page storm？
> 第一層是 inhibition：當 payments 的 SLO 告警觸發時，自動抑制下游服務中「依賴 payments 失敗」所造成的告警，或把它們降級為資訊性通知。抑制的範圍要基於明確的依賴關係，例如只抑制錯誤類型為「payments 呼叫失敗」的部分，避免把下游自己獨立的故障也一起藏起來。
>
> 第二層是 routing 與溝通：只叫醒 payments 的 owner，下游團隊收到「上游事故進行中」的通知與事故頻道連結，需要時再加入。第三層是設計：下游服務若能對 payments 的失敗做降級（例如訂單先接受、付款稍後重試），它們的 SLI 受影響會較小，本來就不會那麼多 page。最後，被抑制的告警仍然要記錄下來，事故結束後可以完整評估各服務受到的影響與 error budget 消耗。

> [!question]- Q6. 告警規則上線前，你會怎麼驗證它「設計得對」？只看公式推導夠嗎？
> 公式推導只能保證規則在理想化的條件下（流量穩定、錯誤瞬間跳變）表現符合預期，真實資料有週期、有尖峰、有缺漏。驗證至少要做三件事。第一，用 `promtool test rules` 這類單元測試，給定人工的時間序列，確認規則在預期的時間點觸發與解除，這能抓到 PromQL 寫錯、標籤對不上這類錯誤。
>
> 第二，用歷史資料回放：拿過去幾個月真實的 metrics，算出這條規則會在哪些時間觸發，對照當時的事故紀錄，看它抓到了哪些、漏了哪些、多報了哪些。第三，影子期：讓規則先送到不會叫醒人的頻道一兩週，觀察實際觸發次數。三者都通過後才變成 page，並在上線後的第一次告警檢討中再看一次表現。

> [!question]- Q7. 有人提議：「讓 LLM 讀每一個告警和相關資料，判斷是不是誤報，只有它認為是真事故的才 page 值班者。」你怎麼評估這個提議？
> 這個提議的動機是對的：誤報太多。但解法把 recall 的責任交給了一個不確定、難以重現的判斷。LLM 的輸出有隨機性、模型升級可能改變判斷，事故時模型服務本身也可能變慢或不可用；更關鍵的是，事後檢討「為什麼這個事故沒有 page」時，很難重現模型當時為什麼那樣判斷。漏報的代價通常遠大於誤報。
>
> 比較好的做法是把力氣花在規則本身：誤報多代表規則門檻或 SLI 設計有問題，應該用 burn rate 與短窗口修好，讓觸發條件保持確定、可測試。AI 可以放在兩個地方：page 送出後做 enrichment，幫值班者更快判斷；以及在告警檢討時分析誤報模式，提出規則修改建議，由 owner 核准。如果真的要試驗 AI 過濾，可以先在影子模式下並行運作，只記錄它的判斷、不影響 page，累積足夠資料再討論。

> [!question]- Q8. 面試題：請為一個剛上線、還沒有任何告警的新服務設計告警策略。你會從哪裡開始、依什麼順序做？
> 我會從使用者與 SLO 開始，而不是從 metrics 開始。第一步是確認關鍵使用者旅程與 SLI（如果還沒有，先和產品一起定義，參考第 32 章），並訂一個初始 SLO。第二步是建立 multi-window multi-burn-rate 告警：兩條 page（14.4× 1 小時加 5 分鐘、6× 6 小時加 30 分鐘）與一條 ticket（1× 3 天加 6 小時），並依實際 SLO 與流量確認門檻合理，低流量就加 synthetic probe。
>
> 第三步是補上少數不在 SLI 裡的關鍵風險：資源即將耗盡的預測性告警、資料完整性與安全事件，每一條都要有 runbook 與 owner。第四步是設計傳遞層：路由給正確的團隊、升級規則、依賴服務的抑制，以及 dead man's switch。最後建立檢討節奏：新規則先跑影子期，上線後每週在 on-call 交接時看 page 是否可行動，每季清理。回答時強調「每個 page 都要能回答它讓值班者做什麼」，以及 CPU、記憶體這類訊號放 dashboard，能讓面試官看到你理解 alert fatigue 的成本。

## 延伸閱讀

- [The Site Reliability Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)：本章 34.6 推導路線的原始資料，包含六種方法的比較與低流量、極高可用性服務的討論。
- [Site Reliability Engineering — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)：symptom vs cause、black-box vs white-box、page 的設計哲學與 four golden signals。
- [Site Reliability Engineering — Practical Alerting](https://sre.google/sre-book/practical-alerting/)：Google 內部以時間序列資料做告警的實作經驗，以及告警規則的維護方式。
- [Site Reliability Engineering — Being On-Call](https://sre.google/sre-book/being-on-call/)：值班負荷的上限、alert fatigue 的成因與值班制度設計。
- [Google Cloud — How Google SRE is using agentic AI to improve operations](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)：AI agent 在維運工作中的應用方式，可對照本章 AI 小節的邊界設計。
