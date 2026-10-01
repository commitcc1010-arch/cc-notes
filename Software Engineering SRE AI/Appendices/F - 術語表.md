---
title: 術語表
---

# 附錄 F　術語表

這份術語表收錄全書反覆用到的重要詞彙。每一條依序列出英文術語（含常見縮寫）、中文說法、一句白話定義，以及第一次詳細說明它的章節。若某個詞在較前面的章節先以粗體出現、但只是順帶提及，章節欄會寫成「第 2 章（詳見第 32 章）」這樣的形式，前者是第一次碰到它的位置，後者是真正展開說明的位置。

術語依英文字母排序；數字開頭的放在「0–9」，沒有通用英文說法的中文概念放在最後的「中文術語」。同一個英文詞在不同領域有不同意思時（例如 label、quarantine、batching），會分成不同條目並在括號中註明語境。定義是為了快速回想而寫的濃縮版本，完整的推導、例子與 trade-off 請回到對應章節閱讀。

## 0–9

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| 1:1:1 規則 | 一目錄一 BUILD 一 target 規則 | 讓每個目錄、BUILD 檔與 target 盡量一對一對應，target 越細，依賴圖越精確，重建與重測範圍越小。 | 第 27 章 |
| 1:1（one-on-one） | 一對一會談 | manager 或 lead 與成員定期的私下對話，討論的是「這個人」的狀態與成長，而不是進度報告。 | 第 12 章 |
| 3-2-1 備份原則 | 3-2-1 rule | 至少 3 份資料、2 種不同儲存媒介或系統、1 份放在異地的備份經驗法則。 | 第 42 章 |
| 429 Too Many Requests | 請求過多 | HTTP 狀態碼，通常表示 client 超過配額，可附 Retry-After 告訴對方多久後再試。 | 第 38 章 |
| 5 whys | 五個為什麼 | 從問題出發連續追問「為什麼」找根因的方法；容易停在人身上，也容易把多因的事故簡化成一條線。 | 第 45 章 |
| 50% 上限（SRE operational work cap） | 維運工作 50% 上限 | SRE 團隊花在 ticket、on-call、手動操作等維運工作的時間整體不超過一半，其餘用在工程改善。 | 第 30 章 |
| 503 Service Unavailable | 服務暫時無法使用 | HTTP 狀態碼，表示 server 暫時無法服務，是過載時明確拒絕的常見方式。 | 第 38 章 |

## A

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| A/B diff | 差異比較 | 把同一批請求同時送給舊版與新版，比較輸出差異再判斷是否預期；不需要知道正確答案，只要確認不該變的沒變。 | 第 25 章 |
| Acceptor | 接受者 | Paxos 中負責回應 proposer、承諾不再接受較小編號提議並接受值的角色。 | 第 40 章 |
| Accessibility tree | 無障礙樹 | 瀏覽器或作業系統從元件結構產生的樹，每個節點有名稱、角色與狀態，螢幕閱讀器讀的是它而不是像素。 | 第 11 章 |
| Accessibility（a11y） | 無障礙、可及性 | 產品能被視覺、聽覺、肢體、認知等不同能力的人使用。 | 第 11 章 |
| Accidental complexity | 偶然複雜度 | 解法本身帶來、原本可以避免的複雜度，例如為早已不存在的問題加的快取層。 | 第 35 章 |
| Action bias | 行動偏誤 | 壓力下覺得「做點什麼」比「先看清楚」更好，即使那個動作沒有根據。 | 第 43 章 |
| Action cache | 動作快取 | 記錄「某個 action key 以前算出的輸出是哪個 digest」的表。 | 第 27 章 |
| Action items | 改進事項 | postmortem 最終落地的具體工作，依作用分為預防、緩解、偵測、流程等類別，要有 owner 與期限。 | 第 45 章 |
| Action key | 動作鍵 | 把 action 的指令、輸入內容雜湊、toolchain 版本與相關環境變數一起雜湊得到的字串；相同就應得到相同輸出。 | 第 27 章 |
| Action（build） | 建置動作 | build 中的單一步驟，理想上是「宣告的輸入 → 確定的輸出」，因此可以安全快取。 | 第 27 章 |
| Active-active | 雙活 | 兩個區域平常都在服務，出事時把流量集中到健康的一邊，兩邊都持續被真實流量驗證。 | 第 37 章 |
| Active-passive | 主備 | 平常只用主區域，備援區域只在災難時接手；簡單，但平常沒在用的東西需要時常常不能用。 | 第 37 章 |
| Adapter | 轉接層 | 在外部套件或舊介面之外包一層自己定義的介面，外部改變時只改這一層；淘汰時也用來保留舊介面、內部轉呼叫新版（也叫 shim）。 | 第 4 章（詳見第 18 章） |
| Adaptive concurrency limit | 自適應並行上限 | 持續觀察延遲，延遲上升就調低並行上限、回穩再慢慢調高，借自 TCP 擁塞控制的想法。 | 第 38 章 |
| Adaptive LIFO | 自適應後進先出 | 平常 FIFO，queue 超過某個長度時才切換成先服務最新請求，避免舊請求永遠排不到。 | 第 38 章 |
| Adaptive throttling | 自適應節流 | client 依最近一段時間的 requests 與 accepts 計算拒絕機率，在本地先擋掉一部分請求，保護過載的 backend。 | 第 38 章 |
| Admission control | 准入控制 | 在昂貴的工作開始之前判斷「這個請求做得完、值得做嗎」，做不完就立刻拒絕。 | 第 38 章 |
| ADR（Architecture Decision Record） | 架構決策紀錄 | 一份記錄一個重大技術決策的背景、選項、理由、關鍵假設與狀態的短文件，讓「為什麼」能被檢查與重新評估。 | 第 1 章（詳見第 7 章） |
| Advisory deprecation | 建議式淘汰 | 沒有截止日、不強制遷移，只標記舊系統並提供替代方案，期待使用者自己搬家。 | 第 18 章 |
| Agent bundle | agent 組合包 | 把模型識別碼與參數、system prompt、工具定義、規則版本、知識庫引用等打包成一個版本，與映像一起建置、簽章並記錄 provenance。 | 第 48 章 |
| AI agent | AI 代理 | 把 model 放進迴圈，讓它根據目標選擇行動、透過工具改變外部世界、觀察結果再決定下一步的系統。 | 第 2 章 |
| AI coding agent | AI 程式助理 | 能讀懂 repository、修改程式碼、執行測試、開 pull request 的 AI 助手。 | 第 1 章 |
| AI 客服 agent | AI customer service agent | Harbor 面向買家的 AI 客服，從只能查訂單，逐步演進到能在額度內經由 refund-gateway 執行退款。 | 第 1 章（詳見第 48 章） |
| Alert | 告警 | 監控系統主動通知人的機制；它會打斷人，所以每一則都要對應真正需要人行動的事。 | 第 1 章（詳見第 34 章） |
| Alert fatigue | 告警疲勞 | 誤報太多讓值班者開始忽略告警，結果真正的事故也被忽略。 | 第 2 章（詳見第 34 章） |
| Alternatives considered | 考慮過的方案 | design doc 中說明其他方案與為什麼沒選它們的段落，證明作者真的思考過。 | 第 17 章 |
| Always Be Deciding | 持續做決定 | 資深領導者在資訊不完整時持續做取捨，並在情況改變時重新決定。 | 第 13 章 |
| Always Be Leaving | 持續讓自己可以離開 | 建立一個不需要你也能運作的組織。 | 第 13 章 |
| Always Be Scaling | 持續擴展自己 | 主動管理隨成功而來的責任，保護自己有限的時間、注意力與精力。 | 第 13 章 |
| Anacron | anacron | 會記錄每個工作上次啟動時間、開機後補跑錯過的每日工作的 cron 變體。 | 第 41 章 |
| Anchoring | 錨定偏誤 | 第一個看到的線索決定了後續所有判斷。 | 第 43 章 |
| Anycast | 任播 | 同一個 IP 位址從多個地點對外宣告，網路路由把封包送到最近的入口。 | 第 37 章 |
| API contract | API 契約 | 元件對使用者承諾的完整行為：能送什麼、會收到什麼、出錯時怎麼表現、哪些行為可以依賴。 | 第 17 章 |
| API（Application Programming Interface） | 應用程式介面 | 服務讓別人呼叫它的方式：有哪些操作、要傳什麼參數、會回傳什麼。 | 第 2 章 |
| Approval theater | 核准劇場 | checklist 每題都勾「是」卻沒有人真的檢查的形式化審查。 | 第 46 章 |
| Arrange-Act-Assert（AAA） | 準備、執行、斷言 | 與 Given-When-Then 同義的測試三段結構。 | 第 23 章 |
| Arrival rate（λ） | 到達速率 | 單位時間進入系統的工作量；長期大於 service rate 時 queue 一定會一直變長。 | 第 38 章 |
| Artifact | 產物（建置產物） | build 把原始碼轉成的可部署東西，例如容器映像；最重要的性質是不可變且可追溯。 | 第 1 章（詳見第 27 章） |
| Artifact-based build | 以產出物為中心的建置 | 工程師宣告要哪些 artifact、由哪些輸入構成，執行順序、平行與跳過交給 build system 決定，例如 Bazel。 | 第 27 章 |
| AST（Abstract Syntax Tree） | 抽象語法樹 | 程式碼被解析後的樹狀結構；linter 與 codemod 在它上面工作，能分辨真正的語法節點與註解、字串。 | 第 15 章（詳見第 21 章） |
| At-least-once | 至少一次 | 沒收到確認就重試，保證不漏但可能重複，因此要求重複執行是安全的。 | 第 41 章 |
| At-most-once | 最多一次 | 送出後不重試，保證不重複但可能漏掉。 | 第 41 章 |
| Autofix | 自動修正 | 工具報告問題的同時提供可直接套用的修改，分為 safe fix 與 unsafe fix。 | 第 15 章 |
| Autonomy, mastery, purpose | 自主、精通、目的 | 驅動知識工作者的三個內在動機要素：能決定怎麼做、能持續變好、知道為什麼重要。 | 第 12 章 |
| Autoscaling | 自動擴縮 | 定期量一個指標、和目標比較、調整台數的控制迴路；反應有延遲，無法取代事前的容量計畫。 | 第 36 章 |
| Availability heuristic | 可得性捷思 | 最近發生過、印象深刻的事件被高估，例如上次是部署出事，這次就先懷疑部署。 | 第 43 章 |
| Availability zone（AZ） | 可用區 | 雲端供應商內電力與網路彼此獨立的機房；部署與容量冗餘常以它為單位。 | 第 29 章 |
| Availability（SLI 類型） | 可用性 | 請求是否成功；最常見的 SLI 類型。 | 第 30 章（詳見第 32 章） |

## B

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Backfill | 回補 | 修正 bug 或停擺後，對一段時間範圍的 run 重新執行；前提是每次 run 可識別且副作用 idempotent。 | 第 41 章 |
| Backpressure | 背壓 | 下游把「我處理不了更多」的訊號傳回上游，讓上游減速、停下或改道。 | 第 38 章 |
| Backsliding | 倒退 | 遷移進行到一半，卻有新程式碼又開始使用舊系統。 | 第 18 章 |
| Backward compatibility | 向後相容 | 新版本能正確處理舊版本產生的輸入，例如新 server 仍接受舊 client 的請求。 | 第 17 章 |
| Baggage | 行李（追蹤上下文附帶鍵值） | 在整條 trace 路徑上傳遞的業務鍵值；會送往所有下游，不能放個資或機密。 | 第 33 章 |
| Baseline | 基準線 | 規則上線時把現存違規記成清單，CI 只擋清單外的新違規，清單只能變短（也叫 ratchet）。 | 第 15 章 |
| Batch pipeline | 批次管線 | 每隔一段時間處理一批累積的資料；簡單、容易重跑，但結果天生有延遲。 | 第 42 章 |
| Batching（merge queue） | 批次驗證 | 把多個 PR 合成一批驗證，通過就一起合併，失敗再切半找出問題 PR。 | 第 28 章 |
| Batching（共識） | 批次 | 把多筆請求打包成一次共識，攤平網路往返與持久寫入成本。 | 第 40 章 |
| Bazel | Bazel | Google 內部 Blaze 的開源版本，代表性的 artifact-based build system。 | 第 27 章 |
| Beyoncé Rule | 碧昂絲規則 | 「If you liked it, you should have put a CI test on it」：在乎某個行為就用測試保護它，否則被別人改壞不能怪別人。 | 第 1 章（詳見第 4 章） |
| Bimodal latency | 雙峰延遲 | 大部分請求很快，但一小部分卡到 deadline 才失敗，平均值看不出來卻佔滿資源。 | 第 39 章 |
| Black-box monitoring | 黑箱監控 | 從外部像使用者一樣測試系統，看到的是症狀。 | 第 33 章 |
| Blameless | 不究責 | 聚焦在「系統為什麼允許這個錯誤發生」，而不是「誰犯了錯」；否則大家會隱藏錯誤，組織學不到東西。 | 第 1 章（詳見第 9 章） |
| Blast radius | 爆炸半徑 | 一次錯誤或一次實驗最多能影響的範圍；很多護欄本質上都在限制它。 | 第 25 章（詳見第 31 章） |
| Blue/green deployment | 藍綠部署 | 準備一整套新環境，測好後把 router 從舊環境切到新環境；切回很快，但要負擔雙倍資源。 | 第 29 章 |
| Boring（system） | 無聊、可預測 | 行為可以被預測的系統；出問題時可能原因只有少數幾個，是 production 軟體的優點。 | 第 35 章 |
| Branch | 分支 | Git 中一個會移動、指向某個 commit 的標籤；開分支便宜，合併才貴。 | 第 19 章 |
| Branch by abstraction | 以抽象層取代分支 | 先在舊實作前加一層抽象，在主線上逐步做出新實作並切換，最後移除舊實作，取代長命分支。 | 第 19 章 |
| Branch coverage | 分支覆蓋率 | 每個 if、else 等分支方向是否都被走過。 | 第 26 章 |
| Break-glass | 打破玻璃 | 事先設計的緊急存取機制：平常鎖住，緊急時可快速取得，但每次使用都被記錄、通知並事後檢討。 | 第 44 章 |
| Brittle test | 脆弱測試 | production 程式碼沒有引入 bug 的變更，卻讓測試失敗。 | 第 23 章 |
| Broker（contract） | 契約中介 | 集中保存 consumer 契約與驗證結果、知道各環境部署版本的服務，例如 Pact Broker。 | 第 25 章 |
| Brooks's law | 布魯克斯定律 | 對已經延誤的軟體專案增加人力，只會讓它更延誤。 | 第 6 章 |
| Brownout | 計畫性短暫中斷 | 在事先公告的時段刻意讓舊 API 回傳錯誤，讓還沒遷移的使用者現身。 | 第 18 章 |
| Bug pattern | 錯誤模式 | 已知會出錯的寫法，例如沒有 timeout 的 HTTP 呼叫、比較浮點數是否相等。 | 第 21 章 |
| Build cop | 主線看守者 | 負責讓專案測試保持通過的輪值者，收到主線失敗通知時要放下手邊事讓主線回到綠色。 | 第 28 章 |
| Build once, promote many | 建置一次、多次晉升 | 只 build 一次，讓同一個 digest 依序晉升到各環境，確保 production 跑的就是被測過的 bytes。 | 第 29 章 |
| Build system | 建置系統 | 給定一組輸入，以正確順序、最少工作量、盡量平行地產生正確輸出的工具。 | 第 27 章 |
| Bulkhead | 艙壁 | 把資源切成彼此隔離的池子，一個依賴出問題時只耗盡自己那一份。 | 第 39 章 |
| Burn rate | 燃燒率 | 實際錯誤率除以 SLO 允許的錯誤率；等於 1 代表窗口結束時剛好用完預算。 | 第 32 章（詳見第 34 章） |
| Burst | 突發流量 | 短時間內湧入的大量請求；queue 可以吸收短暫的 burst，但不能創造容量。 | 第 38 章 |
| Bus factor（truck factor、lottery factor） | 巴士因子 | 要有幾個人同時突然消失，專案才會停擺；等於 1 代表知識只在一個人身上。 | 第 3 章（詳見第 8 章） |

## C

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| CAB（Change Advisory Board） | 變更諮詢委員會 | 由不直接參與開發的人定期開會核准 production 變更的傳統機制；研究顯示重量級外部核准對交付表現有負面影響。 | 第 35 章 |
| Cache poisoning | 快取投毒 | 把錯誤或惡意的結果寫進共用快取，讓所有信任快取的人都拿到它。 | 第 27 章 |
| Calendar freeze | 日曆凍結 | 在業務關鍵或人力不足的時段短暫、範圍明確地避免風險變更。 | 第 35 章 |
| Calendar window | 日曆窗口 | 以自然月等固定期間計算 SLO；容易和 SLA 對帳，但有月初重置效應。 | 第 32 章 |
| Calibration（fairness） | 校準 | 模型給出相同分數時，各群體實際是正例的機率相同。 | 第 11 章 |
| Can-i-deploy | 能否部署檢查 | Pact 中檢查「這個版本與 production 上所有相關版本的契約是否都驗證過」的部署閘門。 | 第 25 章 |
| Canary | 金絲雀發布 | 先把新版本部署給一小部分流量，和舊版本比較錯誤率、延遲與業務指標，沒問題才逐步擴大。 | 第 1 章（詳見第 29 章） |
| Cancellation propagation | 取消傳遞 | 上游放棄請求時，下游也立刻停止工作、釋放資源，避免白工。 | 第 39 章 |
| CAP theorem | CAP 定理 | 網路分割發生時，系統必須在一致性與可用性之間取捨；不是平時三選二。 | 第 40 章 |
| Capacity planning | 容量規劃 | 在需求到來之前，決定要準備多少、什麼樣的資源，並和品質目標綁在一起。 | 第 30 章（詳見第 36 章） |
| Cardinality | 基數 | 一個指標的 label 組合數，也就是時間序列數；高基數 label 會讓 metrics 系統成本爆炸。 | 第 33 章 |
| Cascading failure | 連鎖故障 | 一個元件的故障透過正回饋迴路造成其他元件接連故障，而且隨時間擴大。 | 第 39 章 |
| CAS（content-addressable storage） | 內容定址儲存 | 以內容雜湊為鍵存放檔案，同樣內容只存一份，拿到 digest 就能驗證內容。 | 第 27 章 |
| Cause | 原因 | 監控訊號中的「為什麼壞」，通常來自系統內部；適合用於診斷而不是 page。 | 第 34 章 |
| CDC（change data capture） | 變更資料擷取 | 把資料庫的每筆新增、修改轉成事件送出。 | 第 42 章 |
| Cell-based architecture | 單元化架構 | 把整個服務堆疊複製成多個獨立 cell，每個只服務一部分使用者，一個 cell 壞掉只影響那部分。 | 第 39 章 |
| Change failure rate | 變更失敗率 | 部署後造成服務降級、需要修補或 rollback 的比例；DORA 指標之一。 | 第 14 章 |
| Change-detector test | 變更偵測測試 | 只要 production 程式碼有任何變動就失敗，即使行為完全沒變的測試，常見於過度使用 interaction testing。 | 第 24 章 |
| Chaos engineering | 混沌工程 | 在受控條件下主動注入故障，驗證系統在故障下仍維持穩態的實驗方法。 | 第 25 章 |
| Characterization test | 特徵測試 | 不判斷舊行為對不對，只記錄舊系統在各種輸入下的輸出，作為遷移後比對的基準。 | 第 4 章 |
| ChatOps | 聊天維運 | 在事故頻道中透過指令操作與查詢，讓所有人看到同樣的資訊，也自然形成時間軸。 | 第 43 章 |
| Cherry-pick | 挑選提交 | 把某個 commit 的變更複製到另一條分支，例如先修在主線再套到 release 分支。 | 第 19 章 |
| Chesterton's fence | 切斯特頓的籬笆 | 看到不知用途的東西，先弄清楚當初為什麼立它，再決定要不要拆。 | 第 4 章 |
| Churn Rule | 變動規則 | 基礎設施團隊若要讓使用者跟著改，就必須自己完成遷移或以向後相容方式原地更新。 | 第 6 章（詳見第 18 章） |
| Circuit breaker | 斷路器 | 偵測到對某個下游持續失敗時暫時停止呼叫、讓請求立刻失敗或走 fallback，並經 closed、open、half-open 三種狀態自動恢復。 | 第 39 章 |
| CI（Continuous Integration） | 持續整合 | 每個變更都頻繁合併到主線，每次合併都自動 build 與測試，讓整合問題在變更還小時就被發現。 | 第 1 章（詳見第 28 章） |
| Classical testing | 古典派測試 | 偏好真實物件，只在不方便時才用替身，並以 state 驗證結果。 | 第 24 章 |
| Client-side load balancing | 客戶端負載平衡 | 服務之間的呼叫由 client 自己決定要打哪一台 backend，而不經中央 proxy。 | 第 37 章 |
| Client-side throttling | 客戶端節流 | client 預期 backend 會拒絕時，直接在本地失敗，以免拒絕本身也壓垮 backend。 | 第 38 章 |
| Closed-loop load generator | 閉環負載產生器 | 收到回應才送下一個請求；系統變慢時會自動少送，掩蓋排隊延遲。 | 第 36 章 |
| Cluster | 叢集 | 一群被當成單一資源池管理的 node。 | 第 2 章 |
| Code coverage | 程式碼覆蓋率 | 測試執行時被跑到的程式碼比例；只能說明哪裡完全沒被測，不能說明被跑到的地方有沒有被驗證。 | 第 22 章（詳見第 26 章） |
| Code review | 程式碼審查 | 變更進入主線前由作者以外的人閱讀並同意的過程，目的包括正確性、理解、一致性與知識傳遞。 | 第 1 章（詳見第 16 章） |
| Codelab | 引導式動手教學 | 需要動手做一遍才能理解的技能，用一步步的練習來傳遞。 | 第 10 章 |
| CoDel（Controlled Delay） | 受控延遲 | 觀察最短等待時間，發現形成常駐隊伍時縮短允許的等待時間並主動丟棄的佇列管理演算法。 | 第 38 章 |
| Codemod | 自動改寫程式碼工具 | 自動改寫程式碼的程式，可基於 regex、AST 或 CST 實作，是 large-scale change 的主力。 | 第 18 章（詳見第 21 章） |
| CODEOWNERS | 程式碼擁有者設定 | GitHub 等平台為路徑指定 owner、自動指派 review 的機制。 | 第 8 章 |
| Cognitive load | 認知負荷 | 完成工作需要記住、理解多少東西；DevEx 的三個維度之一。 | 第 14 章 |
| Collective ownership | 集體所有權 | 沒有個別 owner，整個團隊對所有程式碼負責；規模大時容易變成沒人負責。 | 第 8 章 |
| Commit | 提交 | Git 中整個專案在某一刻的快照，加上作者、時間、說明與指向 parent 的指標。 | 第 19 章 |
| Committed（consensus） | 已提交 | 共識中被多數節點持久寫入、不會再被推翻、可以套用到狀態機的 log 項目。 | 第 40 章 |
| Comms lead | 溝通負責人 | 事故中負責所有對人溝通的角色，也是 ops lead 的防火牆。 | 第 44 章 |
| Complicated-subsystem team | 複雜子系統團隊 | 負責需要深度專業的子系統的團隊，Team Topologies 四種團隊類型之一。 | 第 47 章 |
| Compression | 壓縮 | cycle of success 中，用約一半的人力與時間繼續維持原有問題，以騰出另一半處理新問題的那一步。 | 第 13 章 |
| Compulsory deprecation | 強制式淘汰 | 有明確截止日，到期後舊系統被關閉，通常需要專責團隊推動並替使用者完成遷移。 | 第 18 章 |
| Concurrency limit | 並行數上限 | 限制同時處理中的請求數，能自動適應請求成本變化。 | 第 38 章 |
| Condition coverage | 條件覆蓋率 | 複合條件中每個子條件的真假是否都被測過。 | 第 26 章 |
| Confirmation bias | 確認偏誤 | 只找支持自己想法的證據。 | 第 43 章 |
| Confused deputy | 混淆代理人 | 擁有較多權限的代理人被權限較少的一方誘導去做越權的事；prompt injection 是它在 AI 時代最常見的形式。 | 第 47 章 |
| Congestion collapse | 擁塞崩潰 | 送入負載越多，goodput 反而越少的過載現象。 | 第 38 章 |
| Connection draining | 連線排空 | 把 backend 移出輪替時停止分配新請求，等進行中的請求完成，超過上限才強制關閉。 | 第 37 章 |
| Connection tracking | 連線追蹤 | L4 load balancer 記住每條連線對應哪個 backend，讓同一條連線的封包去同一個地方。 | 第 37 章 |
| Consensus vs consent | 共識與同意不反對 | consensus 是所有人都同意；consent 是沒有人有足以否決的強烈反對，更適合多數雙向門決策。 | 第 7 章 |
| Consistent hashing | 一致性雜湊 | 以 hash 決定對應的 backend，backend 增減時只有少部分對應改變。 | 第 37 章 |
| Consulting（SRE engagement） | 顧問模式 | SRE 提供諮詢與設計審查，服務由產品團隊自己運作的參與模式。 | 第 30 章 |
| Consumer lag | 消費落後 | 非同步 queue 中 consumer 落後 producer 的程度；只要在可接受範圍且最終追得上就不是問題。 | 第 38 章 |
| Consumer-driven contract | 消費者驅動契約 | 由使用方寫下「我會這樣呼叫你、我需要回應裡有這些」，提供方每次變更都要通過所有使用方的契約，代表工具是 Pact。 | 第 17 章（詳見第 25 章） |
| Container | 容器 | 把程式與依賴打包、能在任何 node 上以相同方式執行的格式。 | 第 2 章 |
| Context engineering | 上下文工程 | 設計 agent 能看到哪些資訊，讓關鍵規則與事實出現在 context 裡。 | 第 2 章 |
| Context propagation | 上下文傳遞 | 呼叫下游時把 trace 上下文放進請求一起送出，讓下游建立正確的子 span。 | 第 33 章 |
| Context（agent） | 上下文 | 模型做決定時看得到的所有內容：指示、檔案、文件、工具輸出；它是 agent 世界的全部。 | 第 2 章 |
| Continuing change | 持續變化 | 真實世界中被使用的系統必須持續調整，否則價值會逐漸下降。 | 第 4 章 |
| Continuous delivery（CD） | 持續交付 | 主線上的每個版本隨時都可以安全地發布到 production，發布只需要一個決定。 | 第 29 章 |
| Continuous deployment | 持續部署 | 每個通過 pipeline 所有關卡的變更都自動部署到 production，中間沒有人按按鈕。 | 第 29 章 |
| Continuous pipeline | 持續管線 | 一直在運作、資料到了就處理、不再依賴固定排程的 pipeline。 | 第 42 章 |
| Continuous profiling | 持續剖析 | 以低取樣頻率在 production 持續收集 profile，回答「CPU 多花在哪個函式」。 | 第 33 章 |
| Contract | 契約 | 服務對呼叫者的完整承諾，包含語法、語意與非功能面，範圍比 API 格式大得多。 | 第 2 章 |
| Contract test（替身與真實實作） | 合約測試 | 寫一套描述介面行為的測試，讓 fake 與真實實作都跑同一套，確保兩者行為一致。 | 第 24 章 |
| Contract test（服務之間） | 契約測試 | 把雙方對互動的共同理解寫成可自動執行的檢查，防止 provider 改壞 consumer 依賴的行為。 | 第 5 章（詳見第 25 章） |
| Contributing factors | 促成因素 | postmortem 中列出的、共同讓事故發生的多個系統與流程因素，取代單一「根因」。 | 第 48 章 |
| Control loop | 控制迴路 | 不斷重複「觀察、比較、行動」把實際狀態拉向期望狀態的自動機制。 | 第 2 章 |
| Control plane | 控制平面 | 管理資料平面的部分，例如 scheduler、設定推送、部署 pipeline、憑證系統；一個錯誤可能同時影響所有東西。 | 第 2 章 |
| Conway's law | 康威定律 | 系統的結構會反映設計它的組織的溝通結構。 | 第 6 章 |
| Coordinated omission | 協同遺漏 | 負載產生器與受測系統「協同」地漏掉最糟的那段延遲，通常來自 closed-loop 產生器。 | 第 25 章 |
| Correctness（SLI 類型） | 正確性 | 結果是否正確，例如庫存數字與實際一致、營收與金流商撥款明細相符。 | 第 32 章 |
| Cost of delay | 延遲成本 | 拖著不決定的代價：團隊在不確定中重複討論、各自做出不一致的假設。 | 第 7 章 |
| Counter | 計數器 | 只會增加的累計值，查詢時取變化率得到每秒數量。 | 第 33 章 |
| Counter-metric | 制衡指標 | 用來偵測主要指標被操弄或產生副作用的指標。 | 第 14 章 |
| Counterfactual reasoning | 反事實推理 | 「如果當時有做 X 就不會發生」式的推論；有用但容易變成責怪，應轉成對系統的問題。 | 第 45 章 |
| Crash-recovery | 當機後恢復模型 | 節點可能當機後重啟並帶著磁碟資料回來的故障模型，協定必須把承諾持久化。 | 第 40 章 |
| Crash-stop | 當機即停模型 | 節點壞了就永遠不回來的故障模型；最簡單但不符合現實。 | 第 40 章 |
| Credit-based flow control | 額度制流量控制 | 接收方明確告訴傳送方還能收多少，例如 TCP receive window、HTTP/2 flow control。 | 第 38 章 |
| Critical path（build） | 關鍵路徑 | 依賴圖中最長的一條路徑；無限多機器也無法讓 build 短於它。 | 第 27 章 |
| Critical state | 關鍵狀態 | 不同機器看法不一致就會造成錯誤、而且很難事後修復的狀態，需要分散式共識保護。 | 第 40 章 |
| Criticality | 關鍵程度 | 請求的重要性等級，跟著請求往下傳，過載時決定先丟什麼。 | 第 38 章 |
| Cron / crontab | 排程工具與排程表 | Unix 上的定期排程工具，crond 每分鐘檢查 crontab 中到時間的工作並啟動。 | 第 41 章 |
| Cross-reference index | 交叉參照索引 | 由編譯器或語言工具記錄每個名稱的定義與使用位置的語意索引，能分辨同名的不同符號。 | 第 21 章 |
| Crypto-shredding | 加密銷毀 | 每位使用者資料用專屬金鑰加密，刪除時銷毀金鑰，讓備份中的對應資料也無法解讀。 | 第 42 章 |
| CST（Concrete Syntax Tree） | 具體語法樹 | 保留空白、註解與括號等所有原始資訊的語法樹，讓 codemod 改結構時保持其他部分原樣。 | 第 21 章 |
| CUJ（Critical User Journey） | 關鍵使用者旅程 | 使用者完成一件重要的事所經過的一連串步驟，是找 SLI 的起點。 | 第 32 章 |
| Curb-cut effect | 路緣斜坡效應 | 為特定障礙設計的改善最後讓更多人受益。 | 第 11 章 |
| CVE（Common Vulnerabilities and Exposures） | 公開漏洞編號 | 公開漏洞的統一識別編號。 | 第 20 章 |
| Cycle of success | 成功的循環 | 分析、掙扎、進展、回報，然後被交付更多問題的循環，更像一道向外擴張的螺旋。 | 第 13 章 |

## D

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| DACI | DACI 決策框架 | Driver、Approver、Contributors、Informed 四種角色，常用於推動單一決策。 | 第 12 章 |
| DAG（directed acyclic graph） | 有向無環圖 | 箭頭有方向、不會繞回自己的圖；build 依賴圖與 data pipeline 的 stage 關係都必須是 DAG。 | 第 27 章 |
| DAMP（Descriptive And Meaningful Phrases） | 描述性且有意義的語句 | 測試寧可有一點重複，也要讓每個測試單獨讀起來就清楚。 | 第 23 章 |
| Dark launch | 暗中上線 | 新程式碼已在 production 處理真實流量（或已部署但未曝光），但結果不給使用者看。 | 第 19 章（詳見第 29 章） |
| Dashboard as code | 儀表板即程式碼 | dashboard 定義放進版本控制、經過 review、用樣板產生。 | 第 33 章 |
| Data contract | 資料契約 | 資料生產者與消費者之間對格式與語意的明文約定，並在管線中強制執行。 | 第 42 章 |
| Data flow analysis | 資料流分析 | 追蹤一個值從哪裡來、流到哪裡去的靜態分析。 | 第 21 章 |
| Data integrity | 資料完整性 | 以使用者為中心：提供足夠服務水準所需的資料能不能被存取、是不是正確。 | 第 42 章 |
| Data pipeline | 資料管線 | 一連串把資料從來源搬到目的地、途中做轉換的處理步驟。 | 第 42 章 |
| Data plane | 資料平面 | 實際處理使用者請求的部分，例如 load balancer 轉送與服務處理請求。 | 第 2 章 |
| Data quality check | 資料品質檢查 | stage 輸出在發布前要通過的檢查，從 schema、筆數到業務不變條件與獨立來源對帳。 | 第 42 章 |
| De facto contract | 事實上的契約 | 沒有人承諾、卻已被足夠多使用者依賴，以至於實際上改不動的行為。 | 第 5 章 |
| Dead letter queue（dead-letter） | 死信佇列 | 存放重試多次仍失敗的訊息或工作，讓人工檢查，不阻塞其他工作。 | 第 38 章 |
| Dead man's switch | 死人開關 | 設一個持續發出的心跳，心跳停止就告警，用來偵測告警管線或排程本身失效。 | 第 34 章 |
| Deadline | 截止時間 | 整個使用者操作最晚必須完成的時間點，與單一步驟的 timeout 不同。 | 第 39 章 |
| Deadline propagation | 截止時間傳遞 | 讓每一層都知道請求還剩多少時間，不夠就立刻放棄。 | 第 39 章 |
| Decision owner | 決策負責人 | 最後拍板並為結果負責的人，通常是最接近問題、也會承擔後果的人。 | 第 7 章 |
| Decision rights | 決策權 | 某一類決定由誰做、誰要被諮詢、誰只需要被告知。 | 第 12 章 |
| Declared contract | 宣告的契約 | 作者主動承諾的部分，例如 OpenAPI 文件寫明的欄位與型別。 | 第 5 章 |
| Deliberate vs inadvertent debt | 刻意與無意的技術債 | 技術債依是否刻意與是否謹慎分類；刻意且謹慎的債可以是正當的商業決策。 | 第 4 章 |
| Demographic parity | 人口均等 | 各群體被判定（例如被擋單）的比例相同。 | 第 11 章 |
| Dependability | 可靠（團隊成員） | Project Aristotle 五因素之一：成員能否準時、以高品質完成承諾的工作。 | 第 9 章 |
| Dependency | 依賴 | 服務或程式為了完成工作需要、但不由自己控制的東西：其他服務、資料庫、外部 API、函式庫。 | 第 2 章（詳見第 20 章） |
| Dependency confusion | 依賴混淆 | 攻擊者在公開 registry 註冊與內部私有套件同名、版本更高的套件，誘使安裝工具選錯。 | 第 20 章 |
| Dependency injection（DI） | 依賴注入 | 物件不自己建立依賴，而由外部注入，最常見的是 constructor injection。 | 第 24 章 |
| Dependency management | 依賴管理 | 管理依賴的版本、來源、更新與移除的工作。 | 第 20 章 |
| Deploy | 部署 | 把新的 artifact 放到 production 機器上執行；和 release 是兩件事。 | 第 1 章（詳見第 29 章） |
| Deployment frequency | 部署頻率 | 多久成功部署一次到 production；DORA 指標之一。 | 第 14 章 |
| Deprecation | 淘汰 | 有計畫地讓使用者從舊系統遷移到替代方案，並最終移除舊系統的過程。 | 第 18 章 |
| Design doc | 設計文件 | 說明要解決的問題、考慮過的方案、選擇的理由與風險的文件。 | 第 1 章（詳見第 17 章） |
| Detection time | 偵測時間 | 從問題開始到告警觸發要多久；告警品質的四個指標之一。 | 第 34 章 |
| Deterministic subsetting | 確定性子集化 | 把 client 分輪、每輪用相同種子洗牌切 subset，讓每台 backend 被連的次數接近。 | 第 37 章 |
| DevEx（Developer Experience） | 開發者體驗 | 聚焦 feedback loops、cognitive load、flow state 三個維度的開發者生產力框架。 | 第 14 章 |
| DevOps | DevOps | 打破開發與維運之間的牆、讓同一群人對軟體整個生命週期負責的業界文化運動。 | 第 30 章 |
| Diamond dependency | 菱形依賴 | 兩個依賴都依賴同一個套件、但要求的版本範圍沒有交集的衝突。 | 第 19 章（詳見第 20 章） |
| Difference-in-differences | 差異中的差異 | 比較導入組與對照組的前後變化差，估計一項改變本身的效果。 | 第 14 章 |
| Diffusion of responsibility | 責任分散 | 要求很多人 approve，結果每個人都以為別人會仔細看。 | 第 16 章 |
| Digest | 內容摘要 | 以內容雜湊作為身分，例如容器映像的 sha256；內容改一個 byte，digest 就改變。 | 第 27 章 |
| DiRT（Disaster Recovery Testing） | 災難復原測試 | Google 定期舉行、全公司層級、在真實環境模擬大規模故障的演練計畫。 | 第 46 章 |
| Disagree and commit | 保留異議但全力執行 | 決策前充分表達反對，決策後全力支持，並把反對意見與擔心的情境寫進紀錄。 | 第 7 章 |
| Disaster recovery（DR） | 災難復原 | 在區域失效、大規模誤刪、勒索軟體等大規模故障後恢復服務與資料的能力。 | 第 46 章 |
| Divide and conquer | 分而治之 | 從長路徑中間切一刀判斷問題在哪一半，再繼續切的排查技巧。 | 第 43 章 |
| Diátaxis | Diátaxis 文件框架 | 依「動手做或理解」與「學習或工作」把文件分成 tutorial、how-to guide、reference、explanation 四類。 | 第 17 章 |
| DNS load balancing | DNS 負載平衡 | 最外層、最粗的負載平衡，用 DNS 回答決定使用者去哪個 region；回答會被快取，改了難以立刻收回。 | 第 37 章 |
| Docs as code | 文件即程式碼 | 文件用純文字寫、和程式碼放在同一 repository，走同一套 PR、review 與 CI。 | 第 10 章（詳見第 17 章） |
| DOC（Depended-On Component） | 被依賴元件 | SUT 依賴的元件，test double 替換的對象。 | 第 24 章 |
| DORA（DevOps Research and Assessment） | DORA 研究計畫 | 長期研究軟體交付表現的計畫，提出 deployment frequency、lead time for changes、change failure rate、failed deployment recovery time 等指標。 | 第 14 章 |
| Draft PR | 草稿 PR | 程式還沒完成就開 PR、請人先看整體方向，讓方向錯誤能早被指出。 | 第 8 章 |
| Dry-run | 試跑 | 預設只輸出「將會做什麼」，加上明確參數才真的執行。 | 第 31 章 |
| DRY（Don't Repeat Yourself） | 不要重複自己 | 同樣的邏輯只寫一次；在 production 程式碼合理，在測試中過度使用會傷害可讀性。 | 第 23 章 |
| Dueling proposers | 決鬥的提議者 | 多個 proposer 不斷用更大編號互相打斷、誰都 commit 不了的 livelock。 | 第 40 章 |
| Dummy | 填充物 | 只為填參數、從不會被真正使用的 test double。 | 第 24 章 |
| Durability（SLI 類型） | 耐久性 | 寫入的資料能否在之後被讀回。 | 第 32 章 |

## E

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| E2E test（end-to-end test） | 端到端測試 | 從使用者入口出發、穿過整套系統驗證完整使用者旅程的測試；應只保留關鍵旅程。 | 第 25 章 |
| Early cutoff | 提早截斷 | 某步驟輸出 bytes 沒變時，下游 action key 不變，整串下游直接命中快取。 | 第 27 章 |
| Effective false positive | 有效誤報 | 開發者看到分析結果後沒有採取正面行動，不論技術上對不對都算誤報。 | 第 21 章 |
| Effectively-once | 效果上恰好一次 | 用 at-least-once 確保不漏，再讓副作用 idempotent，使重複執行的效果等同執行一次。 | 第 41 章 |
| Embedded SRE | 派駐 SRE | 一位 SRE 暫時加入產品團隊幾個月，協助建立 SLO、告警與 runbook 的參與模式。 | 第 30 章 |
| Emulator | 模擬器 | 依賴官方提供、可在本機執行的版本，例如資料庫或雲端服務的 emulator，保真度通常高於自製 fake。 | 第 24 章 |
| Enabling team | 賦能團隊 | 暫時協助其他團隊學會新能力，而不是永久替他們做事的團隊。 | 第 30 章 |
| Engagement charter | 合作章程 | 寫明 SRE 提供什麼、服務團隊承諾什麼、何時 hand-back 的簡短約定。 | 第 47 章 |
| Engagement model | 參與模式 | SRE 與產品團隊合作的方式，例如完整支援、派駐、顧問、PRR、平台。 | 第 30 章 |
| Engineering Manager（EM） | 工程經理 | 負責團隊每個人的表現、成長、工作狀態與招募，以及與商業目標的對齊。 | 第 12 章 |
| Ephemeral environment | 臨時環境 | 每次測試建立、測完即丟的完整環境，接近 hermetic 但成本較高。 | 第 25 章 |
| Equal opportunity（fairness） | 機會均等 | 在真正是正例的人中，各群體被正確判定的比例相同。 | 第 11 章 |
| Equality vs equity | 平等與公平 | equality 是給每個人相同的東西；equity 是考慮不同的起點與障礙，讓每個人都能合理得到相同結果。 | 第 11 章 |
| Equalized odds | 均等勝算 | 誤判率與漏判率在各群體都相同。 | 第 11 章 |
| Equivalent mutant | 等價突變 | 改動後行為完全相同的 mutant，沒有測試能殺死它，也不需要殺死。 | 第 23 章 |
| Error budget | 錯誤預算 | 1 − SLO：允許的壞事件量，是開發團隊可以用來承擔風險的預算。 | 第 30 章（詳見第 32 章） |
| Error budget freeze | 錯誤預算凍結 | 預算耗盡時把工程力氣轉到可靠性工作，直到可靠性真的恢復，而不是直到日曆到期。 | 第 35 章 |
| Error budget policy | 錯誤預算政策 | 事先由產品、開發、SRE 主管共同簽署的規則，說明預算在不同狀態下團隊要做什麼。 | 第 32 章 |
| Errors（golden signal） | 錯誤 | 失敗請求的比例，包括回 200 但內容是錯誤的情況。 | 第 33 章 |
| Escalation policy | 升級政策 | 規定多久沒確認就通知下一層、什麼情況要叫醒誰的規則。 | 第 43 章 |
| Escape hatch | 逃生門 | paved road 之外公開、有紀錄、有 owner 與期限的例外流程。 | 第 13 章 |
| Essential complexity | 本質複雜度 | 問題本身帶來、無法去除的複雜度。 | 第 35 章 |
| Eval（evaluation） | 評估 | 用一組代表性任務與評分規則，量測 agent 或 AI 服務是否做得好、做得安全，是 agent 的測試。 | 第 2 章（詳見第 25 章） |
| Event time vs processing time | 事件時間與處理時間 | event time 是事情真正發生的時間，processing time 是 pipeline 處理到它的時間；依日期歸屬的計算要用 event time。 | 第 42 章 |
| Eventual consistency | 最終一致性 | 不再有寫入時各副本最終會收斂，但收斂前允許讀到舊值。 | 第 40 章 |
| Exactly-once | 恰好一次 | 每個動作恰好執行一次；在會當機、會遺失訊息的系統裡無法單靠傳遞機制達成。 | 第 41 章 |
| Excessive agency | 過度授權 | 給 agent 的工具、權限或自主性超過任務需要，是 LLM 應用的主要風險之一。 | 第 2 章 |
| Executor load average | 執行器負載平均 | 計算 process 中正在執行或等 CPU 的 thread 數並平滑，超過分配的處理器數就開始拒絕請求。 | 第 38 章 |
| Exemplar | 範例（指標到 trace 的連結） | 在 histogram 區間上附一個落在該區間的請求 trace ID，讓人從延遲圖直接跳到真實慢請求。 | 第 33 章 |
| Expand/contract | 擴充與收縮 | 改資料結構或 API 時先讓新舊並存（expand），驗證、搬遷讀取後再移除舊的（contract），每一步都可回復。 | 第 7 章（詳見第 29 章） |
| Experiment toggle | 實驗開關 | 用於 A/B 實驗分流的 feature flag，存在於實驗期間。 | 第 29 章 |
| Explicit knowledge | 明確知識 | 可以寫下來的知識，例如 API 參數、部署步驟。 | 第 10 章 |
| Exploratory testing | 探索式測試 | 由人主動嘗試奇怪操作、尋找沒想過的問題的手動測試。 | 第 22 章 |
| Exponential backoff | 指數退避 | 每次重試前的等待時間成倍增加，並設上限。 | 第 39 章 |

## F

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Fail closed | 失敗即關閉 | 資料檢查失敗時停止發布，下游繼續用上一個好版本並告警。 | 第 42 章 |
| Fail fast | 快速失敗 | 先跑最快、最常失敗的檢查，失敗就立刻回報。 | 第 28 章 |
| Failback | 切回 | 災難後從備援環境切回原本主要環境；往往比 failover 更難，需要同步與對帳。 | 第 46 章 |
| Failed deployment recovery time（舊稱 MTTR、time to restore） | 失敗部署恢復時間 | 部署造成失敗後恢復服務所需的時間；DORA 指標之一。 | 第 14 章 |
| Failover | 切換到備援 | 主要環境失效時把服務切到備援環境。 | 第 46 章 |
| Failure domain | 故障域 | 會一起失敗的單位，例如同一主機、機架、zone、region；容量冗餘要以它為單位計算。 | 第 36 章 |
| Failure model | 故障模型 | 設計分散式協定時預期的故障種類，例如 crash-stop、crash-recovery、Byzantine。 | 第 40 章 |
| Fake | 偽實作 | 真的能運作但簡化過的實作，例如 in-memory 的金流 gateway，有狀態與語意。 | 第 24 章 |
| Fallback | 備援行為 | circuit breaker 跳開或依賴失效時的明確替代行為，不能破壞不變量。 | 第 39 章 |
| False negative | 漏報、假綠燈 | 真正的問題沒被找到；在測試中是程式有問題測試卻通過。 | 第 21 章（詳見第 22 章） |
| False positive | 誤報、假紅燈 | 找到的其實不是問題；在測試中是程式沒問題測試卻失敗。 | 第 21 章（詳見第 22 章） |
| Fan-out ratio | 扇出比 | 一個業務動作會在每個服務上產生多少請求，是把業務預測換算成各服務容量的橋樑。 | 第 36 章 |
| Faster is safer | 越快越安全 | 部署越頻繁、每次越小，整體反而越安全。 | 第 29 章 |
| Fault injection | 故障注入 | 讓測試或實驗精確製造不正常情況，例如讓回應在網路上遺失。 | 第 24 章 |
| Feature flag（feature toggle） | 功能開關 | 在執行期決定要不要走新程式路徑的開關，讓部署與發布分開。 | 第 1 章（詳見第 19 章） |
| Feedback loop | 回饋迴路 | 採取行動、觀察結果、根據結果調整下一次行動；越快的迴路越便宜，而且必須是閉合的。 | 第 2 章 |
| Fencing token | 隔離權杖 | 共識系統隨 lease 發出的單調遞增數字，資源拒絕比已見過最大值更小的 token，防止過期持有者寫入。 | 第 40 章 |
| Fidelity | 保真度 | test double 或測試環境的行為有多接近真實依賴或 production。 | 第 24 章 |
| Flaky test | 不穩定測試 | 程式碼與測試都沒變，卻有時通過、有時失敗的測試，根源是某種不確定性。 | 第 23 章（詳見第 26 章） |
| Flow state | 心流狀態 | 工程師能否進入並維持深度專注；DevEx 三維度之一。 | 第 14 章 |
| FLP impossibility | FLP 不可能性 | 在訊息延遲無上限的非同步網路中，只要可能有一個節點當機，就沒有確定性演算法能保證在有限時間內達成共識。 | 第 40 章 |
| Formatter | 格式化工具 | 把程式碼排版成唯一標準形式、不改變程式意義的工具。 | 第 15 章 |
| Forward compatibility | 向前相容 | 舊版本能容忍新版本產生的輸入，例如舊 client 遇到新欄位不會壞。 | 第 17 章 |
| Four golden signals | 四大黃金訊號 | latency、traffic、errors、saturation：面向使用者的系統只能量四個指標時就量這四個。 | 第 33 章 |
| Freelancing | 各自為政 | 事故中 responder 沒經協調就自行動手，讓變更互相衝突、效果無法歸因。 | 第 44 章 |
| Freeze | 凍結 | 暫時停止某些變更；分為 error budget freeze、calendar freeze、incident freeze。 | 第 35 章 |
| Freshness（SLI 類型） | 新鮮度 | 資料落後現實多久，例如搜尋索引或營收報表的延遲。 | 第 32 章 |
| Full jitter | 完全抖動 | 等待時間在 0 到退避上限之間完全隨機；另有 equal jitter、decorrelated jitter 等變形。 | 第 39 章 |

## G

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Game day | 演練日 | 事先排定時間，刻意製造或模擬故障，觀察系統與人如何反應的活動。 | 第 25 章（詳見第 46 章） |
| Gate | 關卡 | pipeline 中自動判斷「能不能往下走」的檢查。 | 第 29 章 |
| Gauge | 量表 | 會上下變動的當下值，例如 queue 長度、記憶體用量。 | 第 33 章 |
| Genius myth | 天才迷思 | 把成果歸功給一個天才的傾向，讓人以為只要夠強就不需要依賴別人。 | 第 8 章 |
| Geo DNS | 地理 DNS | 依查詢來源的地理位置回傳不同 region 的 IP。 | 第 37 章 |
| Git bisect | 二分搜尋找出問題提交 | 用二分搜尋找出哪個 commit 引入問題的 Git 工具，n 個 commit 約需 log₂ n 步。 | 第 19 章 |
| GitFlow | GitFlow 分支模型 | develop、feature、release、hotfix 多條長期分支的模型，適合多版本並存維護的產品。 | 第 19 章 |
| GitHub flow | GitHub flow | main 加短命 feature branch 與 PR 的模型，適合持續部署的 web 服務。 | 第 19 章 |
| Given-When-Then | 前提、動作、結果 | 測試的三段結構：準備初始狀態、執行一個行為、驗證可觀察的結果。 | 第 23 章 |
| Global approver | 全域核准者 | LSC 中負責審核所有 shard 的單一核准者，事先與作者對齊預期，再用工具檢查並自動核准符合預期者。 | 第 21 章 |
| Golden file | 黃金檔案 | 預先保存的預期輸出，測試比對實際輸出是否一致；更新要經 review。 | 第 26 章 |
| Golden path | 黃金路徑 | 平台提供的一條預設、受支援、內建最佳實務的做事方式，走這條路最省力。 | 第 13 章（詳見第 30 章） |
| Good events / valid events | 好事件與有效事件 | valid events 是服務有機會表現好或壞的事件，good events 是其中結果夠好的部分；SLI = good / valid。 | 第 32 章 |
| Goodput | 有效吞吐量 | throughput 中對使用者有用的部分：在 deadline 內完成、結果正確、使用者還在等。 | 第 38 章 |
| Graceful degradation | 優雅降級 | 過載或依賴失效時用較便宜的方式提供部分功能，而不是完全失敗。 | 第 38 章 |
| GREASE | GREASE 機制 | 在協定可擴充欄位中隨機放入保留的無意義值，強迫實作從一開始就正確忽略不認識的值，防止協定僵化。 | 第 5 章 |
| Grouping（alerts） | 告警分組 | 把同一原因觸發的多個告警合併成一則通知。 | 第 34 章 |
| GSM 框架（Goals/Signals/Metrics） | 目標、訊號、指標框架 | 先寫目標，再寫達成時會觀察到的訊號，最後才選可量測的指標，讓每個指標可追溯。 | 第 14 章 |

## H

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Half-open | 半開 | circuit breaker 只放行少量探測請求的狀態，探測成功回到 closed、失敗回到 open。 | 第 39 章 |
| Hand-back | 交還 | 服務維運負擔持續超標且團隊未投入改善時，SRE 把 on-call 交還給開發團隊。 | 第 30 章（詳見第 47 章） |
| Handoff | 交接 | 值班每班結束時的交接，讓進行中的問題不會在換班時消失。 | 第 43 章 |
| Hanging chunk | 卡住的分片 | 一個分片卡住整批 periodic pipeline 的狀況。 | 第 42 章 |
| Hard dependency vs soft dependency | 硬依賴與軟依賴 | 硬依賴壞了服務無法完成工作；軟依賴壞了服務可以降級但仍可運作。 | 第 2 章 |
| Hash flooding | 雜湊洪水攻擊 | 刻意送出大量 hash 值相同的鍵，讓雜湊表退化成很慢的串列。 | 第 5 章 |
| Head sampling | 頭部取樣 | 請求一進來就決定是否保留整條 trace；簡單便宜，但決定時還不知道它會不會出錯。 | 第 33 章 |
| Headroom | 餘裕 | 在預測尖峰之上額外保留、用來吸收預測誤差與不確定性的容量。 | 第 36 章 |
| Health check | 健康檢查 | load balancer 判斷 backend 能否接流量的方法，分主動探測與被動觀察。 | 第 2 章（詳見第 37 章） |
| Hedged request | 對沖請求 | 送出請求後一段時間沒回應，就向另一個 replica 再送一份，誰先回來用誰。 | 第 39 章 |
| Hermetic build | 密封式建置 | build 的每一步只能看到宣告的輸入，看不到機器上的其他東西。 | 第 27 章 |
| Hermetic test | 密閉測試 | 結果只取決於明確宣告的輸入、不依賴外部網路、機器、時間與其他測試的測試。 | 第 22 章（詳見第 26 章） |
| Hierarchy of controls | 控制層級 | 消除、工程隔離、行政流程、個人注意力，效果由強到弱的改善手段排序。 | 第 45 章 |
| Hindsight bias | 後見之明偏誤 | 知道結果之後，覺得結果「早就很明顯」。 | 第 45 章 |
| Histogram | 直方圖 | 把觀測值放進預先定義的區間並計數，可以跨機器相加，用來算百分位數。 | 第 33 章 |
| Hope is not a strategy | 希望不是一種策略 | SRE 格言：可靠性要靠工程與事先同意的數字，而不是祈禱。 | 第 30 章 |
| Hourglass（testing） | 沙漏 | 很多 unit test、很多 E2E、幾乎沒有 integration test 的測試組合反模式。 | 第 22 章 |
| How-to guide | 操作指南 | 給已會基本操作的人解決特定問題的文件。 | 第 17 章 |
| HRT（Humility、Respect、Trust） | 謙遜、尊重、信任 | 健康團隊合作的三個原則；幾乎所有人際衝突都能追溯到缺少其中之一。 | 第 8 章 |
| Hypothetico-deductive method | 假設演繹法 | 根據觀察提出假設、推導可檢驗的預測、再用觀察或實驗檢驗的排查方法。 | 第 43 章 |
| Hyrum's Law | 海倫定律 | API 使用者夠多時，你在契約中承諾什麼都不重要：系統所有可觀察的行為都會被某人依賴。 | 第 5 章 |
| Hysteresis | 遲滯 | 擴容立即反應、縮容要連續多次確認才執行，避免控制迴路來回振盪。 | 第 2 章 |

## I

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Ice cream cone | 冰淇淋甜筒 | 大量手動測試與 E2E、很少 unit test 的倒金字塔測試組合。 | 第 22 章 |
| IC（individual contributor） | 個人貢獻者 | 主要透過自己的工作產生價值、不帶人的工程師。 | 第 12 章 |
| Idempotency key | 冪等鍵 | 同一個操作的唯一識別碼，伺服器看到相同 key 時直接回傳上次結果，不重複執行。 | 第 2 章（詳見第 41 章） |
| Idempotent（idempotency） | 冪等 | 同樣的操作執行一次或多次結果相同。 | 第 15 章（詳見第 41 章） |
| Immutable backup | 不可變備份 | 在保留期內任何人（包括管理員）都無法修改或刪除的備份。 | 第 42 章 |
| Incident | 事故 | 需要立即、協調一致的回應才能降低傷害的事件；一個事故可能包含多個 page。 | 第 43 章（詳見第 44 章） |
| Incident Command System（ICS） | 事故指揮系統 | 源自野火應變的標準化角色與指揮結構，是事故管理的基礎。 | 第 44 章 |
| Incident Commander（IC） | 事故指揮官 | 事故中唯一的決策者，維持全局、指派角色、核准高風險動作；沒被指派出去的責任都在 IC 身上。 | 第 44 章 |
| Incident freeze | 事故凍結 | 事故處理期間暫停無關變更，避免干擾判斷。 | 第 35 章 |
| Incremental build | 增量建置 | 只重做受變更影響的部分。 | 第 27 章 |
| Influence without authority | 沒有權力的影響力 | 在無法命令對方時讓對方願意改變做法的能力。 | 第 13 章 |
| Inhibition（alerts） | 告警抑制 | 上游根因告警觸發時，抑制同一原因造成的下游症狀告警。 | 第 34 章 |
| Instance | 實例 | 服務的一個執行單位，通常是某台機器或容器裡的一個 process。 | 第 2 章 |
| Intent-based capacity planning | 以意圖為基礎的容量規劃 | 以「服務要達到什麼目標」描述需求，讓系統推導需要哪些資源，而不是指定機器數。 | 第 36 章 |
| Interaction testing | 互動測試 | 檢查被測程式是否以特定方式呼叫依賴；只在無法做 state testing 或呼叫本身就是重點時使用。 | 第 23 章（詳見第 24 章） |
| Internal developer platform（IDP） | 內部開發者平台 | 把部署、監控、憑證等共同需求做成自助產品的內部平台。 | 第 30 章（詳見第 47 章） |
| Interrupt rotation | 干擾輪值 | 每週由一位工程師負責回應外部詢問與小型支援，其他人可以專心開發。 | 第 13 章 |
| Intersectionality | 交織性 | 多重身份交會處常出現任何單一切片都看不到的嚴重問題。 | 第 11 章 |
| Invariant | 不變量 | 任何時候、任何操作之後都必須成立的規則，描述系統永遠不能變成什麼樣子。 | 第 2 章 |

## J

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Jevons paradox | 傑文斯悖論 | 資源使用效率提高後，總使用量可能反而增加。 | 第 6 章 |
| Jitter | 抖動 | 在重試等待時間中加入隨機性，避免大量 client 同時重試。 | 第 39 章 |
| Just culture | 公正文化 | 把行為分成無心之失、風險行為、魯莽行為並以安慰、教練、處分分別回應的框架。 | 第 9 章 |

## K

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Keyless signing | 無長期金鑰簽章 | 用 CI 等既有身份換取短效憑證來簽章，並把紀錄寫入公開透明日誌。 | 第 20 章 |
| Kill switch | 停止開關 | 任何值班者都能立即關掉自動化、功能或 agent 的開關。 | 第 31 章 |
| Knee | 膝點 | 負載增加時延遲開始往上彎的點；過了它使用者已在等待，即使 throughput 還在上升。 | 第 36 章 |

## L

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| L4 load balancer（network load balancer） | 第四層負載平衡器 | 在連線層級決定 backend，同一條 TCP 連線的封包都去同一個地方。 | 第 37 章 |
| L7 proxy（L7 load balancer） | 第七層代理 | 看得懂 HTTP，能對每個請求各自決定 backend 並依路徑、header 路由。 | 第 37 章 |
| Label（Bazel） | 標籤（建置） | 指稱一個 target 的名稱，例如 //checkout:pricing。 | 第 27 章 |
| Label（metrics） | 標籤（指標維度） | 區分同一指標不同切面的鍵值，例如 endpoint、status；每組組合都是一條時間序列。 | 第 33 章 |
| Lame duck | 跛腳鴨狀態 | backend 還能服務，但明確告訴 client 不要再送新請求，讓停機前的請求自然消化。 | 第 37 章 |
| Large-scale change（LSC） | 大規模變更 | 邏輯上相關、但實務上無法以單一原子單位提交的一組變更。 | 第 18 章（詳見第 21 章） |
| Last responsible moment | 最後負責時刻 | 在「再不決定就會失去重要選項」之前做決定，以帶著更多資訊決策。 | 第 7 章 |
| Latency（SLI 與 golden signal） | 延遲 | 請求是否夠快、處理請求花多久；成功與失敗的延遲要分開看。 | 第 30 章（詳見第 32 章） |
| Latent failure | 潛伏故障 | 只在特定情況下才會暴露的問題，例如備份每天顯示成功但檔案其實是空的。 | 第 46 章 |
| Launch | 上線 | 任何會讓應用程式產生外部可見變化的新程式碼。 | 第 46 章 |
| LCE（Launch Coordination Engineering） | 上線協調工程 | SRE 中專門協調多團隊上線、維護 checklist 與最佳實務的顧問團隊。 | 第 46 章 |
| Lead time for changes | 變更前置時間 | 從 commit 到該變更在 production 執行所需的時間；DORA 指標之一。 | 第 14 章 |
| Leader election | 領導者選舉 | 在一群相同的 process 中選一個做事、其他待命，通常以共識系統實作。 | 第 40 章 |
| Leader of leaders | 帶領 leader 的 leader | 帶的是另一群做決策的人，而不是直接寫程式的人的領導者。 | 第 13 章 |
| Learn to drop balls | 學會讓球掉下來 | 既然一定有事做不完，就刻意選擇讓哪些不重要的事掉下來。 | 第 13 章 |
| Lease | 租約 | 共識系統授予的一段有期限的權力，到期前必須續約，否則自動失效。 | 第 40 章 |
| Least connections（least outstanding requests） | 最少連線 | 每次選目前進行中請求最少的 backend；壞掉而快速失敗的 backend 可能反而吸走流量。 | 第 37 章 |
| Least privilege | 最小權限 | 身份只拿到完成任務所需的最小權限，例如清理 agent 在 production 只能讀取。 | 第 47 章 |
| LGTM（Looks Good To Me） | 我看沒問題 | code review 中確認變更正確、看得懂的核准。 | 第 16 章 |
| Libyear | 依賴落後年數 | 每個依賴落後最新版本的年數總和，適合看趨勢，不適合當 KPI。 | 第 4 章 |
| LIFO | 後進先出 | 塞車時先服務最新的請求，它們的使用者還在等。 | 第 38 章 |
| Line coverage | 行覆蓋率 | 被執行到的行數除以總行數。 | 第 26 章 |
| Lineage | 血緣 | 把所有 provenance 串起來的圖，可以往上游追根因、往下游追影響。 | 第 42 章 |
| Linearizability | 線性一致性 | 系統表現得像只有一份資料，每個操作在開始與結束之間的某一瞬間原子生效，讀到新值後不會再讀到舊值。 | 第 40 章 |
| Linter | 程式碼檢查工具 | 檢查程式碼寫法是否符合規則、抓出危險寫法的工具。 | 第 15 章 |
| Little's Law | 利特爾定律 | 穩定系統中 L = λW：平均同時存在的工作數等於到達速率乘以平均停留時間。 | 第 36 章 |
| Liveness probe | 存活探測 | Kubernetes 中失敗時重啟 container 的探測；不應放入依賴檢查。 | 第 37 章 |
| Liveness（consensus） | 活性 | 好事最終會發生，例如最終選出 leader；只在網路夠好、多數節點活著時保證。 | 第 40 章 |
| LLM-as-judge | 以模型評分 | 用另一個經過人工校準的模型評估 AI 輸出品質。 | 第 32 章 |
| LLM（Large Language Model） | 大型語言模型 | 根據輸入文字產生輸出文字的模型，只知道當下輸入與訓練知識，同樣輸入可能得到不同輸出。 | 第 2 章 |
| Load balancer | 負載平衡器 | 接收請求並分散到多個健康 instance 的元件。 | 第 2 章 |
| Load balancing | 負載平衡 | 決定「這個請求要給誰處理」的機制，要同時避免過載、避開不健康 backend、就近服務並控制成本。 | 第 37 章 |
| Load shedding | 負載卸除 | server 依自己當下狀態主動丟掉一部分工作，保護其餘工作。 | 第 38 章 |
| Load test | 負載測試 | 在預期流量下驗證是否符合 SLO，並畫出負載與品質的曲線。 | 第 25 章（詳見第 36 章） |
| Lock file | 鎖定檔 | 記錄某次依賴解析結果的確切版本與雜湊，讓每次安裝完全相同。 | 第 20 章 |
| Log | 日誌 | 系統在某個時間點記下的離散事件，保留完整細節但量大且貴。 | 第 1 章（詳見第 33 章） |

## M

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Majority quorum | 多數決法定人數 | n 個節點中超過一半同意才算數；任意兩個 majority 必有交集。 | 第 40 章 |
| Maker's schedule vs manager's schedule | 創造者與管理者的時間表 | 前者需要整塊時間專注，後者以一小時為單位切成會議；lead 常同時被兩者拉扯。 | 第 12 章 |
| Manifest（container image） | 映像清單 | 列出容器映像所有 layer digest 的檔案，其雜湊就是映像的 digest。 | 第 27 章 |
| Memory（agent） | 記憶 | 跨對話或跨任務保存的資訊，例如專案慣例與過去的決定。 | 第 2 章 |
| Merge conflict | 合併衝突 | 兩邊改了同一段文字，Git 無法自動合併、需要人決定。 | 第 19 章 |
| Merge gate | 合併關卡 | 依 OWNERS 規則與 CI 結果判斷 PR 能否合併的自動檢查。 | 第 16 章 |
| Merge queue | 合併佇列 | PR 通過 review 後進入佇列，依序放在最新主線加前面所有 PR 之上再驗證，通過才合併。 | 第 19 章（詳見第 28 章） |
| Metastable failure | 亞穩態故障 | 觸發原因消失後，系統仍被自身的維持效應（例如重試、冷快取）困在壞狀態。 | 第 39 章 |
| Metrics | 指標 | 數值隨時間的變化，例如每秒請求數、錯誤率；便宜、適合告警與趨勢。 | 第 1 章（詳見第 33 章） |
| Mitigated vs Resolved | 已止血與已解決 | mitigated 代表使用者傷害已停止；resolved 代表系統回到正常、臨時措施都已移除或轉成正式工作。 | 第 44 章 |
| Mitigation vs repair | 止血與修復 | mitigation 是還不知道原因時就能減少使用者傷害的動作；repair 是處理原因本身。 | 第 44 章 |
| Mock | 模擬物件 | 預先設定「應該被怎麼呼叫」的期望並驗證的 test double。 | 第 24 章 |
| Mockist testing | mock 派測試 | 把有行為的協作者都換成 mock，以 interaction 驗證 SUT 的風格。 | 第 24 章 |
| Model（agent） | 模型 | agent 中負責根據輸入產生輸出的 LLM；只能「說」，要靠工具才能「做」。 | 第 2 章 |
| Moiré load pattern | 疊紋負載型態 | 多個週期性負載疊加出的高低起伏。 | 第 42 章 |
| Monitoring | 監控 | 收集、彙整並顯示事先知道要看的量化資料，並在超出預期時通知人。 | 第 30 章（詳見第 33 章） |
| Monkey patching | 猴子補丁 | 在執行期間直接替換模組或物件上的屬性，例如 unittest.mock.patch。 | 第 24 章 |
| Monorepo vs polyrepo | 單一倉庫與多倉庫 | monorepo 把許多專案放在同一個 repository；polyrepo 是每個服務或函式庫一個 repository。 | 第 19 章 |
| Multi-Paxos | 多重 Paxos | 選出穩定 leader 後，後續每個 log 格子只需第二階段、一次往返就能 commit 的 Paxos 用法。 | 第 40 章 |
| Multi-stage build | 多階段建置 | 第一階段安裝與編譯，第二階段只複製執行需要的檔案，讓映像更小、攻擊面更少。 | 第 27 章 |
| Multi-window multi-burn-rate alerting | 多窗口多燃燒率告警 | 每條 burn rate 規則同時要求長窗口與約 1/12 長度的短窗口都超過門檻，兼顧偵測速度與解除速度。 | 第 34 章 |
| Mutant | 突變體 | mutation testing 中被故意改了一處的程式版本；測試失敗代表 killed，全部通過代表 survived。 | 第 23 章 |
| Mutation score | 突變分數 | 被殺死的 mutant 比例（嚴格算法扣除 equivalent mutant）。 | 第 23 章（詳見第 26 章） |
| Mutation testing | 突變測試 | 故意在程式碼裡製造小 bug，看測試會不會失敗，以量測測試的辨識力。 | 第 23 章（詳見第 26 章） |

## N

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| N+1 / N+2 | N+1、N+2 冗餘 | 尖峰需要 N 個單位時多準備 1 或 2 個；N+2 能同時承受一次計畫中停機與一次非計畫故障。 | 第 36 章 |
| Naive datetime | 無時區時間 | 不帶時區資訊、不知道自己是哪個時區的時間物件。 | 第 15 章 |
| Narrow integration test | 窄整合測試 | 只把一條邊界換成真的元件的整合測試，比啟動整套系統快、也更容易定位失敗。 | 第 25 章 |
| Near miss | 險些發生的事故 | 防線剛好擋住或運氣好沒造成傷害的事件；學習價值高、代價低。 | 第 45 章 |
| Negative Results Are Magic | 否定的結果很有價值 | 被推翻的假設同樣是有結論的實驗，縮小了可能性，應被記錄。 | 第 43 章 |
| Nit:（review 標記） | 小問題 | code review 中標示建議修但不阻擋的小問題；同類標記還有 Optional:、Question:、FYI:。 | 第 16 章 |
| Node | 節點 | 一台實體或虛擬的機器。 | 第 2 章 |
| Noise | 雜訊 | 不應改變某個決定的資訊；同一筆資料對不同決定可能是 signal 也可能是 noise。 | 第 2 章 |
| Non-goals | 非目標 | design doc 中明確寫出不做什麼，讓 review 聚焦。 | 第 17 章 |
| Non-human identity | 非人類身份 | agent 與服務帳號的身份，要有短效憑證、最小權限並綁定人類 owner。 | 第 47 章 |

## O

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Observability | 可觀測性 | 能回答事先沒想到的問題、從外部輸出推斷系統內部狀態的能力。 | 第 33 章 |
| Obsolete | 過時 | 有更好的替代品出現、舊系統不再是首選的狀態；過時不等於已淘汰。 | 第 18 章 |
| Offered load | 送入負載 | 所有想要被處理的工作量。 | 第 38 章 |
| Office hours | 固定答疑時段 | 專家固定開放的時段，集中回答某領域的零散問題。 | 第 10 章 |
| On-call | 值班 | 在指定時間內負責接收 production 緊急告警並在約定時間內回應處理；責任是止血與協調，不一定是修好。 | 第 43 章 |
| One Version rule | 單一版本規則 | 組織內任何元件只有一個正式版本，開發者永遠不必選擇要依賴哪個版本。 | 第 19 章 |
| One-way door vs two-way door（Type 1 / Type 2） | 單向門與雙向門 | Type 1 是不可逆、需謹慎的決策；Type 2 是可逆、應由小團隊快速決定的決策。 | 第 7 章 |
| Open-loop load generator | 開環負載產生器 | 照固定到達速率送請求，不管前一個回來沒，更接近真實使用者。 | 第 36 章 |
| OpenAPI | OpenAPI | 用 YAML 或 JSON 描述 HTTP API 路徑、參數與請求回應格式的 schema 標準。 | 第 17 章 |
| OpenTelemetry（OTel） | OpenTelemetry | CNCF 下讓 telemetry 產生與收集標準化、與後端廠商無關的開源專案。 | 第 33 章 |
| Operational overload vs underload | 維運過載與維運不足 | 前者是事件太多讓值班者疲憊；後者是值班太安靜讓人對系統生疏。 | 第 43 章 |
| Opportunity cost | 機會成本 | 因為選了 A 而放棄的 B 本來能帶來的價值；不出現在報表上，最容易被忘記。 | 第 3 章（詳見第 7 章） |
| Ops lead | 操作負責人 | 事故中負責技術排查與修復，也是唯一能對 production 執行變更的人。 | 第 44 章 |
| Ops toggle | 維運開關 | 出事時關掉昂貴或危險功能的長期 feature flag，即 kill switch。 | 第 29 章 |
| Oracle（testing） | 判定準則 | 判斷測試結果對不對的依據，可以是期望值或一條性質。 | 第 22 章 |
| Organic vs inorganic growth | 自然成長與非自然成長 | organic 是可從歷史推估的平滑成長；inorganic 是活動、上線、媒體報導等事件造成的跳躍。 | 第 36 章 |
| Oscillation（flapping） | 振盪 | 控制迴路在太多與太少之間來回擺盪。 | 第 2 章 |
| Outcome bias | 結果偏誤 | 用結果好壞判斷決策好壞，而不是看當時的資訊下是否合理。 | 第 45 章 |
| Outlier detection | 離群偵測 | 被動觀察 backend 錯誤率，把連續出錯的暫時踢出輪替。 | 第 37 章 |
| Over-mocking | 過度 mock | 測試主要內容變成 mock 劇本而不是行為，導致脆弱又抓不到真問題。 | 第 24 章 |
| Overhead | 行政負擔 | 開會、填考核等和 production 無直接關係的工作；需要減少但不是 toil。 | 第 31 章 |
| Owner | 負責人 | 對服務、程式碼、資料或文件的長期健康負責的人或團隊；不是「別人不准碰」。 | 第 2 章 |
| Owner approval | 擁有者核准 | 由目錄 owner 確認變更適合放在這裡、符合長期方向的核准。 | 第 16 章 |
| OWNERS | OWNERS 檔案 | 每個目錄列出能核准該目錄變更的人的檔案，階層式疊加。 | 第 8 章 |
| Ownership（strong、weak、collective） | 所有權、負責制 | 誰負責讓系統長期健康；strong 只有 owner 能改，weak 任何人可改但 owner 要 review，collective 全隊共同負責。 | 第 8 章 |

## P

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| p50 / p99 | 第 50、99 百分位數 | p50 是中位數，p99 是 99% 請求比它快的值，用來看尾端延遲。 | 第 32 章 |
| PACELC | PACELC | 補充 CAP：分割時在可用性與一致性間取捨，否則（else）在延遲與一致性間取捨。 | 第 40 章 |
| Page | 呼叫 | 立刻叫醒或通知值班者、要求人類馬上行動的告警。 | 第 34 章 |
| Path coverage | 路徑覆蓋率 | 所有可能執行路徑組合是否都被走過；數量隨分支數指數成長。 | 第 26 章 |
| Paved road | 鋪好的路 | 中央團隊提供預設、好用、有支援的標準路線，同時保留 escape hatch。 | 第 6 章（詳見第 13 章） |
| Paxos | Paxos | 以 Prepare/Promise 與 Accept/Accepted 兩階段「先佔位、再提交」達成共識的協定。 | 第 40 章 |
| Peer bonus | 同儕獎金 | 任何員工都能給同事的小額獎金加正式認可，讓幫助別人被看見；更輕量的是 kudos。 | 第 10 章 |
| Per-customer quota | 每客戶配額 | 給每個客戶獨立的資源配額，超量時只拒絕該客戶的超額請求。 | 第 38 章 |
| Percentile | 百分位數 | 把觀測值排序後某個比例位置的值，比平均值更能看出尾端問題；不能直接平均。 | 第 32 章 |
| Periodic pipeline | 定期管線 | 由排程器定期啟動、處理一批資料就結束的 pipeline。 | 第 42 章 |
| Permission toggle | 權限開關 | 只對特定使用者開放功能的長期 feature flag。 | 第 29 章 |
| PITR（point-in-time recovery） | 時間點還原 | 以基礎備份加交易日誌還原到任意時間點。 | 第 42 章 |
| Platform engineering | 平台工程 | 把常見需求做成內部自助產品、像對外產品一樣經營的做法。 | 第 30 章（詳見第 47 章） |
| Platform team | 平台團隊 | 提供自助服務讓 stream-aligned team 減少負擔的團隊。 | 第 30 章 |
| Playbook | 應對手冊 | 範圍較大的應對方案，例如區域故障或資料外洩時的整體流程。 | 第 43 章 |
| Poison job | 毒藥工作 | 每次執行都必然失敗的工作，無限重試會一直佔用 worker。 | 第 41 章 |
| Policy（agent） | 政策 | agent 被允許做什麼的規則，必須由 agent 之外的程式強制執行，而不是寫在 prompt 裡。 | 第 2 章 |
| Positive feedback | 正回饋 | 結果回頭加強原因的迴路，是 cascading failure 的本質。 | 第 39 章 |
| Postel's law（robustness principle） | 伯斯塔爾定律 | 「送出時保守，接收時寬容」；過度寬容會成為 Hyrum's Law 的溫床。 | 第 5 章 |
| Postmortem | 事後檢討 | 書面記錄事故影響、經過、促成因素、有效與無效的處理，以及接下來要做什麼。 | 第 1 章（詳見第 45 章） |
| Postsubmit | 提交後檢查 | 變更合併後在主線上持續執行的檢查，範圍更廣但失敗時主線已包含問題。 | 第 28 章 |
| POUR | POUR 原則 | WCAG 的四個原則：Perceivable 可感知、Operable 可操作、Understandable 可理解、Robust 穩健。 | 第 11 章 |
| Power of two choices（P2C） | 兩選一 | 每次隨機挑兩台 backend，把請求送給負載較低的那台。 | 第 37 章 |
| Pre-mortem | 事前驗屍 | 決策或上線前請所有人想像「它失敗了，原因是什麼」，讓擔憂能被說出來。 | 第 7 章 |
| Precision | 精確度（精確率） | 告警或檢查發出的警報中，真的需要處理的比例。 | 第 2 章（詳見第 34 章） |
| Presubmit | 提交前檢查 | 變更合併進主線之前執行、失敗就不能合併的檢查。 | 第 28 章 |
| Primary / Secondary（on-call） | 主值班與副值班 | primary 是第一個被通知的人；secondary 是 primary 未回應時的備援或需要時的支援者。 | 第 43 章 |
| Processing time | 處理時間 | pipeline 處理到這筆資料的時間（對照 event time）。 | 第 42 章 |
| Production | 正式環境 | 真實使用者、真實資料與真實金錢所在的執行環境。 | 第 2 章（詳見第 30 章） |
| Production readiness review（PRR） | 上線準備度審查 | SRE 接手 on-call 或服務上線前，檢查監控、容量、回退、依賴等是否達到可維運標準。 | 第 30 章（詳見第 46 章） |
| Profile | 效能剖析 | 記錄程式在一段時間內 CPU 時間或記憶體配置花在哪些函式上。 | 第 33 章 |
| Programming | 程式設計 | 在某個時間點讓程式能動：理解需求、選擇演算法、寫出正確的程式碼。 | 第 1 章（詳見第 3 章） |
| Progressive delivery | 漸進式交付 | 依證據逐步擴大曝光的整套做法：canary、逐步擴大、自動 gate 與 feature flag。 | 第 29 章 |
| Project Aristotle | 亞里斯多德計畫 | Google 研究有效團隊的計畫，結論是心理安全最重要，其次是可靠、結構與清晰、意義、影響。 | 第 9 章 |
| Prompt injection | 提示注入 | 輸入中藏著的文字被模型當成指令執行。 | 第 2 章 |
| Prompt trace | 提示追蹤 | 一段對話的根 span 下依序掛著每次模型呼叫、檢索、工具呼叫與 policy 檢查結果。 | 第 33 章 |
| Proposer | 提議者 | Paxos 中帶著編號提出值的角色。 | 第 40 章 |
| Protocol Buffers（protobuf） | Protocol Buffers | 以欄位編號序列化的二進位 schema 格式，常搭配 gRPC。 | 第 17 章 |
| Protocol ossification | 協定僵化 | 中間設備只見過固定幾種值、看到新值就丟棄，讓協定預留的擴充空間實際上無法使用。 | 第 5 章 |
| Prototype | 原型 | 為了驗證產品假設而做的最小版本。 | 第 3 章 |
| Provenance | 來源證明 | 描述 artifact 由哪個 build、哪份原始碼、什麼指令產生的紀錄；資料也有同樣的 provenance。 | 第 20 章（詳見第 27 章） |
| Provider state | 提供者狀態 | 契約中每個互動附帶的前置條件，provider 重放請求前依此準備資料。 | 第 25 章 |
| Proxy variable | 代理變數 | 和敏感屬性高度相關的欄位，模型可能透過它學到歧視，即使沒用敏感欄位。 | 第 11 章 |
| Psychological safety | 心理安全 | 團隊成員共有的信念：在這個團隊裡冒人際風險是安全的。 | 第 9 章 |
| Pull-based（backpressure） | 拉取式 | consumer 主動拉工作，自然不會拿超過自己能處理的量，壓力表現為 lag。 | 第 38 章 |

## Q

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| QUANTS | QUANTS 檢查清單 | 評估一項工程變化時至少要看的五個面向：程式碼品質、工程師注意力、智力複雜度、節奏與速度、滿意度。 | 第 14 章 |
| Quarantine（data） | 隔離（資料） | 把不合格的資料列移到有 owner 與期限的隔離區，其餘照常發布。 | 第 42 章 |
| Quarantine（flaky test） | 隔離（測試） | 把 flaky test 從阻擋提交的閘門暫時移出，但繼續執行與追蹤直到修好。 | 第 26 章 |
| Queue | 佇列 | 讓工作排隊等待處理的地方；能吸收 burst，但只能搬移時間，不能創造容量。 | 第 38 章 |
| Queue depth vs queue age | 隊伍長度與隊伍年齡 | depth 是排隊數量；age 是最老項目已等待的時間，可直接和 deadline 比較，更適合告警。 | 第 38 章 |
| Quorum | 法定人數 | 足以代表整體做決定的節點集合；2f+1 個節點可容忍 f 個故障。 | 第 40 章 |

## R

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Race condition | 競態條件 | 結果取決於多個操作誰先完成的缺陷。 | 第 5 章 |
| RACI 矩陣 | RACI 責任矩陣 | 為每類決策標出 Responsible、Accountable（只能一個）、Consulted、Informed 四種角色。 | 第 12 章 |
| Raft | Raft | 為了好懂而設計的共識協定，以 leader、term 與 AppendEntries 複製 log。 | 第 40 章 |
| RAG（Retrieval-Augmented Generation） | 檢索增強生成 | 先從文件庫搜尋相關段落，再讓模型根據這些段落回答；回答要附來源並遵守原始權限。 | 第 10 章 |
| RAPID | RAPID 決策框架 | Recommend、Agree、Perform、Input、Decide 五種角色的決策框架。 | 第 12 章 |
| Ratchet | 棘輪 | 只能往一個方向轉的機制：舊使用者或舊違規名單只能變短，新的使用一律被 CI 擋下。 | 第 18 章 |
| Rate limiting | 速率限制 | 限制單位時間內的請求數，最常見實作是 token bucket。 | 第 38 章 |
| Readability | 可讀性認證 | Google 針對特定語言的標準化 mentoring 與認證制度。 | 第 10 章 |
| Readability approval | 可讀性核准 | 由具備該語言 readability 的人確認變更符合語言慣例的核准。 | 第 10 章 |
| Readiness probe | 就緒探測 | 失敗時從 Service endpoints 移除、不再收流量但不重啟的探測。 | 第 37 章 |
| Recall | 召回率 | 真正發生的問題中被偵測到的比例；通常和 precision 互相拉扯。 | 第 2 章（詳見第 34 章） |
| Reconciliation | 對帳 | 獨立工作從多個來源比對應有結果與實際結果，抓出系統紀錄沒發現的差異。 | 第 41 章 |
| Record/replay | 錄製與重放 | 錄下真實依賴的回應供之後的測試播放；錄音會過期，也可能含敏感資料。 | 第 24 章 |
| Recording rule | 記錄規則 | 預先計算並儲存結果的查詢，供告警規則引用。 | 第 34 章 |
| RED（Rate、Errors、Duration） | RED 方法 | 給請求驅動服務的三個指標：每秒請求數、錯誤、耗時分佈。 | 第 33 章 |
| Reference（documentation） | 參考文件 | 精確、完整、結構一致、像字典的文件，最好從程式碼自動產生。 | 第 17 章 |
| Regression | 回歸 | 原本正常的功能因為新的修改而壞掉。 | 第 1 章 |
| Release | 發布 | 讓使用者實際用到新功能；可以和 deploy 分開。 | 第 1 章（詳見第 29 章） |
| Release branch | 發行分支 | 從 main 切出要發布的版本，只接受修補，修補先進 main 再 cherry-pick。 | 第 19 章 |
| Release engineering | 發布工程 | 把建置、打包、發布軟體當成工程來做，強調自助、高頻、hermetic build 與政策強制。 | 第 35 章 |
| Release toggle | 發布開關 | 讓未完成或未驗證的功能先關著的短期 feature flag，開完就刪。 | 第 29 章 |
| Release train | 發布列車 | 固定時間發車，已完成的搭上車，沒完成的等下一班；列車不等人。 | 第 29 章 |
| Remote cache | 遠端快取 | 把 action cache 與 CAS 放在團隊共用的服務上，CI 建過的東西開發者可直接下載。 | 第 27 章 |
| Remote execution | 遠端執行 | 沒命中快取的 action 也送到遠端機器群平行執行。 | 第 27 章 |
| Renovate / Dependabot | 依賴更新機器人 | 定期檢查 manifest 與 lock file、發現新版本或漏洞時自動開 PR 的工具。 | 第 20 章 |
| Replicated log | 複製日誌 | 大家都同意順序的一串操作，每台機器依序執行就得到相同狀態。 | 第 40 章 |
| Replicated state machine（RSM） | 複製狀態機 | 以共識維護 replicated log、各節點依序執行的架構，是 etcd、ZooKeeper 的核心。 | 第 40 章 |
| Replication | 複製 | 把資料即時同步到其他機器或區域，防硬體與站點故障；它不是備份，錯誤刪除也會被忠實複製。 | 第 42 章 |
| Replica（instance） | 副本 | 服務的一個執行實例（與 instance 同義）；資料庫語境中則指唯讀副本。 | 第 2 章 |
| Reproducible build | 可重現建置 | 給定相同原始碼、環境與指令，任何人都能做出逐位元相同的 artifact。 | 第 27 章 |
| Reset time | 解除時間 | 問題結束後告警還要響多久才停；告警品質的四個指標之一。 | 第 34 章 |
| Restore drill | 還原演練 | 在隔離環境真的還原備份、驗證內容並量測真實時間的演練。 | 第 42 章 |
| Reverse dependencies | 反向依賴 | 誰依賴我；改了某個 target 時，用它找出所有受影響的 target。 | 第 27 章 |
| Reverse shadow | 反向跟班 | 新人擔任 primary、資深者在旁必要時才介入的值班培訓階段。 | 第 43 章 |
| Revert | 撤回 | 產生一個反向變更的新 commit；主線壞了時通常是最快回到綠色的方法。 | 第 19 章（詳見第 28 章） |
| Rework rate | 重工率 | 非計畫中、因 production 問題而做的部署占所有部署的比例；DORA 2024 年新增。 | 第 14 章 |
| Rollback vs roll forward | 回退與往前修 | rollback 回到上一個已知良好的版本；roll forward 部署一個包含修正的新版本。預設先 rollback 再 debug。 | 第 16 章（詳見第 29 章） |
| Rolling update | 滾動更新 | 一批一批替換機器上的版本，是一般無狀態服務的預設。 | 第 29 章 |
| Rolling window | 滾動窗口 | 永遠看「過去 30 天」的 SLO 窗口，平滑且沒有月初重置效應。 | 第 32 章 |
| Rosie | Rosie | Google 把巨大變更依專案邊界與 OWNERS 拆成許多可獨立提交 shard 的工具。 | 第 21 章 |
| Round robin / random | 輪流與隨機 | 最簡單的負載平衡演算法，前提是請求成本與 backend 能力都差不多。 | 第 37 章 |
| Routing 與 escalation（alerts） | 告警路由與升級 | page 送給服務 owner 的值班者，未確認則自動升級給 secondary。 | 第 34 章 |
| RPO（Recovery Point Objective） | 復原點目標 | 恢復後最多可以遺失多久的資料。 | 第 42 章（詳見第 46 章） |
| RTO（Recovery Time Objective） | 復原時間目標 | 從事件到服務恢復最多可以花多久。 | 第 42 章（詳見第 46 章） |
| Rule of three | 三法則 | n 次獨立試驗觀察到 0 次失敗時，真實失敗率的 95% 信賴上限約為 3/n。 | 第 26 章 |
| Run ledger | 執行帳本 | 為每一次排定的執行保存一列狀態的表，是分散式 cron 的事實來源。 | 第 41 章 |
| Runbook | 操作手冊 | 針對特定告警或操作的逐步指引：先看什麼、怎麼判斷、可以安全地做什麼。 | 第 31 章（詳見第 43 章） |

## S

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Safe capacity | 安全容量 | 在 SLO 門檻以下、離 knee 還有一點距離的負載。 | 第 36 章 |
| Safe fix vs unsafe fix | 安全修正與不安全修正 | safe fix 保留執行行為可自動套用；unsafe fix 可能改變行為，應作為建議由人確認。 | 第 15 章 |
| Safety valve | 安全閥 | 維運工作超過上限時把多出的工作或 on-call 退回給開發團隊的機制。 | 第 30 章 |
| Safety（consensus） | 安全性 | 壞事永遠不會發生，例如不會有兩個不同的值被 commit；任何網路狀況下都必須成立。 | 第 40 章 |
| Sampling（trace） | 取樣 | 只保留一部分 trace，分 head sampling 與 tail sampling。 | 第 33 章 |
| Sandbox（build） | 沙箱 | 只放宣告輸入的臨時執行環境，沒宣告的東西根本不存在。 | 第 27 章 |
| Saturation | 飽和度 | 系統有多「滿」，例如連線池使用率、queue 長度；最容易被忽略也最有預測力。 | 第 33 章 |
| SBI 模型（Situation、Behavior、Impact） | 情境、行為、影響模型 | 給回饋時具體描述情境、可觀察的行為與造成的影響。 | 第 12 章 |
| SBOM（Software Bill of Materials） | 軟體物料清單 | 機器可讀的清單，列出 artifact 包含的所有元件、版本、來源與授權。 | 第 20 章 |
| Scheduler | 排程器 | cluster 的大腦，決定每個容器放在哪個 node，並在故障時重新安排。 | 第 2 章 |
| Schema / schema first | 結構定義與 schema 優先 | schema 是機器可讀的介面結構定義；schema first 是先寫 schema、再從它產生文件與程式碼。 | 第 17 章 |
| Scope（test scope） | 測試範圍 | 測試驗證了多少程式碼路徑，分 narrow、medium、large，和資源用量無關。 | 第 22 章 |
| Scribe | 記錄者 | 事故中記下每個觀察、假設、決策、變更與時間點的角色。 | 第 44 章 |
| Seam | 接縫 | 程式中可以替換依賴的位置。 | 第 24 章 |
| Seeded data / test traffic | 預置資料與測試流量 | 測試前寫進 SUT 的資料，以及測試中送進 SUT 的請求；前者應透過正式 API 寫入以滿足不變量。 | 第 25 章 |
| Seeker vs stumbler | 尋找者與漫遊者 | seeker 知道要找什麼、需要一致性；stumbler 只有模糊需求、需要清晰。 | 第 17 章 |
| Self-service | 自助服務 | 把工作從「排隊等某個團隊」變成「需求方隨時自己完成」，並把權限規則寫進系統。 | 第 31 章 |
| Semantic conflict | 語意衝突 | 兩邊改的是不同行，Git 順利合併，但合起來的邏輯是錯的。 | 第 19 章 |
| Semantic conventions | 語意慣例 | OpenTelemetry 規定的 HTTP 方法、狀態碼等屬性標準名稱。 | 第 33 章 |
| Semantic Versioning（SemVer） | 語意化版本 | 用 MAJOR.MINOR.PATCH 溝通變更性質：不相容升 MAJOR、相容新功能升 MINOR、相容修正升 PATCH；只是估計，不是保證。 | 第 5 章（詳見第 20 章） |
| Separation of duties | 職責分離 | 同一個身份不能自己核准自己的變更，agent 也不能修改自己的 policy 或等級。 | 第 47 章 |
| Servant leadership | 僕人式領導 | 領導者的工作是服務團隊、營造 HRT 環境、移除障礙，而不是下指令。 | 第 12 章 |
| Service | 服務 | 長時間運行、透過網路介面提供某種能力的軟體；是責任邊界，不是一台機器。 | 第 2 章 |
| Service catalog | 服務目錄 | 記錄每個服務 owner、tier、依賴、on-call、runbook、SLO 與 PRR 狀態的資料。 | 第 47 章 |
| Service mesh | 服務網格 | 以 sidecar proxy 在每個 client 旁執行負載平衡等邏輯，由中央控制平面下發設定。 | 第 37 章 |
| Service rate（μ） | 服務速率 | 系統單位時間能處理完的工作量。 | 第 38 章 |
| Severity（SEV） | 嚴重度 | 事故大小的分級，用可觀察的影響描述，決定動員多少人、通知誰與更新頻率。 | 第 44 章 |
| Shadow AI | 影子 AI | 在組織管控範圍外使用的 AI 工具或 agent。 | 第 47 章 |
| Shadow mode | 影子模式 | agent 對真實案件做判斷但只記錄、不生效，用來和人的判斷比對。 | 第 31 章 |
| Shadow traffic | 影子流量 | 把 production 真實請求複製一份送給新版本，回應丟棄，只比對輸出與效能。 | 第 25 章 |
| Shadow（on-call） | 跟班 | 新人跟著資深值班者一起收 page、觀察判斷但不負主責的培訓階段。 | 第 43 章 |
| Shard（LSC） | 分片 | LSC 被拆成可各自測試、review、原子提交的小變更。 | 第 21 章 |
| Shift left | 左移 | 把檢查盡量往開發時間軸的早期移動，越早發現越便宜。 | 第 6 章 |
| Short-lived credentials | 短效憑證 | 每次執行時取得有效期很短的憑證，限制外洩的影響時間。 | 第 47 章 |
| Shrinking | 縮小反例 | property-based testing 找到反例後，自動把它簡化成最容易理解的版本。 | 第 23 章 |
| Signal | 訊號 | 應該改變某個決定的資訊；在 GSM 框架中則指目標達成時會觀察到的現象。 | 第 2 章 |
| Sigstore | Sigstore | 讓簽章變簡單的開源專案，以 keyless signing 與公開透明日誌提供可驗證的出身。 | 第 20 章 |
| Silence（alerts） | 靜音 | 計畫維護期間事先建立、有時限的告警靜音。 | 第 34 章 |
| Single point of failure（SPOF） | 單點故障 | 一個壞掉就讓整體停擺的元件；在知識上指關鍵知識只在一個人身上。 | 第 10 章 |
| Single source of truth（canonical source） | 單一事實來源 | 每種知識或資料有一個被指定的家，其他地方需要時連結過去而不是複製。 | 第 10 章 |
| Site Reliability Engineering（SRE） | 網站可靠性工程 | 用軟體工程方法處理維運問題、以 SLO 與 error budget 管理可靠性的做法與職能。 | 第 30 章 |
| SLA（Service Level Agreement） | 服務水準協議 | 對客戶的正式承諾，違反時有後果。 | 第 32 章 |
| SLI（Service Level Indicator） | 服務水準指標 | 量測服務品質的指標，通常是 good events / valid events 的比例。 | 第 32 章 |
| Slopsquatting | AI 幻覺套件搶註 | AI 建議了不存在的套件名稱，攻擊者搶先註冊同名惡意套件。 | 第 20 章 |
| SLO（Service Level Objective） | 服務水準目標 | SLI 在一段時間內要達到的目標，由產品與工程共同決定。 | 第 32 章 |
| SLSA（Supply-chain Levels for Software Artifacts） | 軟體供應鏈等級框架 | 把 build 過程的可信度分成數個等級的框架，從產生 provenance 到託管、防偽造的 builder。 | 第 20 章（詳見第 27 章） |
| Soak test | 浸泡測試 | 接近日常流量長時間運作，觀察記憶體或連線洩漏等慢慢變差的問題。 | 第 25 章 |
| Soft delete | 軟刪除 | 刪除時先標記並隱藏、保留一段期間才真正清除，處理最常見的誤刪。 | 第 42 章 |
| Software composition analysis（SCA） | 軟體組成分析 | 讀取 lock file 或 artifact 列出所有依賴，並和漏洞資料庫比對的工具。 | 第 20 章 |
| Software engineering | 軟體工程 | programming integrated over time：讓程式在整個壽命中面對需求、人員、規模改變時，仍能以合理成本被理解、修改與運作。 | 第 1 章（詳見第 3 章） |
| Software supply chain | 軟體供應鏈 | 從原始碼到 production artifact 之間的所有環節，任何一環被攻破都可能把惡意程式送進去。 | 第 20 章 |
| SPACE 框架 | SPACE 生產力框架 | 主張開發者生產力至少有五個維度：滿意度與身心狀態、成果、活動量、溝通與協作、效率與心流。 | 第 14 章 |
| Span | 追蹤片段 | trace 中代表一段工作的單位，記錄開始時間、耗時、所屬服務與 parent span。 | 第 33 章 |
| Span of control | 控制幅度 | 一個人能有效協調的直接報告者數量，ICS 經驗約三到七人。 | 第 44 章 |
| Speculative execution（merge queue） | 推測執行 | 同時驗證 M+A、M+A+B 等組合，假設前面都會通過，以運算換等待時間。 | 第 28 章 |
| Spike test | 尖峰測試 | 模擬流量在幾秒內暴增，觀察系統與 autoscaling 跟不跟得上。 | 第 25 章 |
| Spike（technical） | 技術探勘 | 有時間上限、為回答一個具體技術問題而做的探索工作，做完程式碼通常丟掉。 | 第 3 章（詳見第 7 章） |
| Spy | 間諜 | stub 加上記錄被怎麼呼叫、事後讓測試查詢的 test double。 | 第 24 章 |
| SRE（見 Site Reliability Engineering） | 網站可靠性工程 | 見 Site Reliability Engineering。 | 第 30 章 |
| Stacked changes（stacked PR） | 堆疊式變更 | 一連串互相依賴的小 PR 疊在一起，可平行 review、依序合併。 | 第 16 章 |
| Staff engineer | 資深個人貢獻者 | 有跨團隊技術影響力、卻不帶人的資深工程師職位。 | 第 12 章 |
| Standing queue | 常駐隊伍 | 長時間從未清空的 queue，代表持續過載而不是短暫 burst。 | 第 38 章 |
| Starlark | Starlark | Bazel BUILD 檔使用的 Python 風格語言。 | 第 27 章 |
| State | 狀態 | 跨越多次請求被保存下來的資料；它讓擴展、替換、部署與恢復都變困難。 | 第 2 章 |
| State testing | 狀態測試 | 檢查呼叫之後系統的狀態或回傳值；大多數情況下優先於 interaction testing。 | 第 23 章（詳見第 24 章） |
| Stateless vs stateful | 無狀態與有狀態 | stateless 不保存跨請求資料，容易擴展與替換；stateful 保存資料，例如資料庫。 | 第 2 章 |
| Static analysis | 靜態分析 | 不執行程式，分析程式碼結構、型別或資料流來找問題。 | 第 21 章 |
| Steady state | 穩態 | 可量測、代表系統正常的輸出；chaos 實驗假設它在故障下仍會維持。 | 第 25 章 |
| Sticky session（session affinity） | 黏性會話 | 讓同一使用者的請求總是去同一台 backend；代價是負載不均與故障時狀態消失。 | 第 37 章 |
| Strangler fig | 絞殺榕模式 | 在舊系統外建立入口，新功能用新系統，舊功能一塊塊搬過去，直到舊系統被完全取代。 | 第 4 章 |
| Stream-aligned team | 對齊價值流的團隊 | 面向產品價值流的團隊，例如 checkout。 | 第 30 章 |
| Streaming pipeline | 串流管線 | 資料一進來就持續處理；延遲低但要處理亂序、遲到與重複事件。 | 第 42 章 |
| Stress test | 壓力測試 | 逐步加壓直到失敗，找出極限以及超過極限時怎麼壞。 | 第 25 章 |
| Strict dependencies | 嚴格依賴 | 直接用到的模組必須自己宣告依賴，不能靠別的 target 間接帶進來。 | 第 27 章 |
| Structure & clarity | 結構與清晰 | Project Aristotle 五因素之一：角色、計畫與目標是否清楚。 | 第 9 章 |
| Structured logging | 結構化日誌 | 把每筆日誌寫成固定欄位的資料，例如每行一個 JSON 物件。 | 第 33 章 |
| Stub | 樁 | 對呼叫回傳預先寫好答案的 test double。 | 第 24 章 |
| Style arbiters | 風格仲裁者 | style guide 的指定 owner，依真實問題與權衡做最終決定。 | 第 15 章 |
| Style guide | 風格指南 | 組織對「程式碼應該長什麼樣子」的書面約定，是工程問題而不是美學問題。 | 第 15 章 |
| Sublinear scaling | 次線性成長 | SRE 人數應隨系統規模次線性成長，系統變大十倍，SRE 遠不需要多十倍。 | 第 47 章 |
| Subsetting | 子集化 | 讓每個 client 只連 backend 的一部分，控制連線數。 | 第 37 章 |
| Suggested fix | 建議修正 | 分析工具附上、開發者按一下就能套用的修改。 | 第 21 章 |
| Sunk cost fallacy | 沉沒成本謬誤 | 因為已經投入很多而不肯放棄；決策只應該看未來的成本與收益。 | 第 7 章 |
| Suppression | 抑制 | 讓工具在特定位置不報告某條規則，範圍要最小並寫明理由。 | 第 15 章 |
| Sustainable | 可持續的 | 在軟體的預期壽命內，有能力回應任何有價值的技術或業務變更。 | 第 3 章 |
| SUT（System Under Test） | 被測系統 | 測試要驗證的那部分程式碼，可能是函式、服務或整個網站。 | 第 22 章 |
| Swiss cheese model | 瑞士起司模型 | 多層防線各有漏洞，事故發生在多層的洞剛好對齊時。 | 第 45 章 |
| Symptom vs cause | 症狀與原因 | symptom 是「什麼壞了」、使用者看得到；cause 是「為什麼壞」、系統內部的。page 應以 symptom 為主。 | 第 34 章 |
| Synthetic monitoring（probe） | 合成監控 | 定期由程式模擬使用者執行一次 CUJ，低流量時特別有用。 | 第 32 章 |
| Synthetic probe | 合成探測 | 定期由程式模擬使用者執行一次旅程，同一份定義可在 CI 當測試、在 production 當探測。 | 第 25 章 |

## T

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Tacit knowledge | 隱性知識 | 很難寫下來的直覺、判斷與經驗，主要靠一起工作傳遞。 | 第 10 章 |
| Tail sampling | 尾部取樣 | 暫存整條 trace，請求結束後再決定保留哪些，例如錯誤與慢請求全留。 | 第 33 章 |
| Taint analysis | 污染分析 | 把不可信輸入標記為污染，檢查它是否未經處理就流進 SQL 或 shell 的資料流分析。 | 第 21 章 |
| TAP（Test Automation Platform） | 測試自動化平台 | Google 的 CI 系統，以快速子集做 presubmit、更廣範圍做 postsubmit。 | 第 28 章 |
| Target tracking | 目標追蹤 | autoscaling 的常見策略：依目前指標值與目標值的比例調整台數。 | 第 36 章 |
| Target（build） | 建置目標 | BUILD 檔中宣告的一個建置單位，有 srcs、deps 等屬性。 | 第 27 章 |
| Task-based build | 以任務為中心的建置 | 定義一組要執行的指令與其相依的 task，例如 Make、Gradle；難以安全平行與正確增量建置。 | 第 27 章 |
| Tech Lead Manager（TLM） | 技術負責人兼經理 | 同時負責技術與人的角色，常見於小團隊。 | 第 12 章 |
| Tech Lead（TL） | 技術負責人 | 負責技術方向、架構決策、品質標準與把工作拆給成員，通常仍是主要貢獻者之一。 | 第 12 章 |
| Technical debt | 技術債 | 為了更快交付暫時採用不理想的做法；之後每次修改多付的力氣是利息，改成理想做法的成本是本金。 | 第 4 章 |
| Technical strategy | 技術策略 | 面對一個領域的一連串決定時的方向，由 diagnosis、guiding policy、coherent actions 構成。 | 第 13 章 |
| Telemetry vs feedback | 遙測資料與回饋 | telemetry 是系統輸出的 metrics、logs、traces；feedback 是這些資料真的進入決策並改變了行為。 | 第 2 章 |
| Test behaviors, not methods | 測行為而非方法 | 每個測試驗證一個「在某前提下做某件事會得到某結果」的行為，而不是對應一個方法。 | 第 23 章 |
| Test data builder | 測試資料建構器 | 提供合理預設值、讓測試只寫出和它有關欄位的工具。 | 第 26 章 |
| Test double | 測試替身 | 在測試中代替真實依賴的物件或元件，包括 dummy、stub、spy、mock、fake。 | 第 24 章 |
| Test pollution | 測試污染 | 測試修改共享狀態沒有還原，讓其他測試的結果取決於執行順序。 | 第 26 章 |
| Test selection | 測試選擇 | 根據變更內容與依賴圖決定這次要跑哪些測試。 | 第 28 章 |
| Test size | 測試大小 | 測試被允許使用哪些資源（small、medium、large），和測了多少程式碼無關。 | 第 22 章 |
| Testing blueprint | 測試藍圖 | 為每一種風險選擇合適的測試層，讓整套測試抓得到、跑得快、可信。 | 第 22 章 |
| Testing on the Toilet | 廁所測試報 | Google 貼在廁所隔間的單頁測試技巧電子報，降低接觸知識的成本。 | 第 10 章 |
| Testing pyramid | 測試金字塔 | 底層大量窄範圍 unit test、中間較少 integration test、頂端少量 E2E 的健康測試組合。 | 第 22 章 |
| Threat model | 威脅模型 | 列出誰可能怎麼攻擊或誤用一個系統，並據此設計防護。 | 第 48 章 |
| Throughput | 吞吐量 | 系統每秒實際處理完的工作量；在 SLI 中也指批次系統的處理能力。 | 第 32 章（詳見第 38 章） |
| Thundering herd | 驚群效應 | 大量請求或工作在同一瞬間湧向同一個資源，例如同時重試或午夜整點的排程。 | 第 39 章（詳見第 41 章） |
| Time to detect / declare / mitigate | 偵測、宣告、止血時間 | 把事故時間線拆成從影響開始到被發現、從發現到宣告、從影響開始到止血，直接指出哪一段要改善。 | 第 45 章 |
| Timeout | 逾時 | 單一次操作最多等待多久的上限；首要目的是保護呼叫端自己的資源。 | 第 39 章 |
| Toil | 苦工、重複性維運工作 | manual、repetitive、automatable、tactical、沒有持久價值、隨服務成長線性增加的維運工作。 | 第 30 章（詳見第 31 章） |
| Toil budget | toil 預算 | 團隊允許花在 toil 上的時間上限，超過時自動觸發行動。 | 第 31 章 |
| Toil ledger | toil 帳本 | 記錄每類重複工作的頻率、耗時、成長趨勢與出錯成本的表。 | 第 31 章 |
| Token bucket | 權杖桶 | 以固定速率補充 token、最多存 b 個，請求拿到 token 才能進來的速率限制實作。 | 第 38 章 |
| Tolerant reader | 寬容的讀取者 | 只讀需要的欄位、忽略不認識的欄位、對未知 enum 有預設處理的 client 寫法。 | 第 17 章 |
| Tool broker / tool gateway | 工具代理層、工具閘道 | agent 只能透過它呼叫工具，由確定性程式檢查身份、權限、參數與上限並寫入稽核紀錄。 | 第 31 章（詳見第 47 章） |
| Toolchain | 工具鏈 | 編譯器、直譯器、打包工具本身；它也是 build 的輸入，必須固定版本。 | 第 27 章 |
| Tools（agent） | 工具 | agent 能對外部世界做的動作：搜尋、讀寫檔案、執行指令、呼叫 API。 | 第 2 章 |
| Trace | 追蹤 | 一個請求在多個服務之間經過的完整路徑與耗時，由多個 span 組成。 | 第 1 章（詳見第 33 章） |
| Trace Context | W3C 追蹤上下文 | W3C 定義的 traceparent 等 HTTP header 標準，用於跨服務傳遞 trace 上下文。 | 第 33 章 |
| Traceability | 可追溯性 | 每個指標都能往上追溯到它代表的訊號與目標。 | 第 14 章 |
| Traffic（golden signal） | 流量 | 系統承受多少需求，例如每秒 checkout 請求數。 | 第 33 章 |
| Transactional outbox | 交易性寄件匣 | 在同一個資料庫交易中寫入業務資料與待送訊息，再由另一程式讀出並送出，避免兩者只成功一半。 | 第 41 章 |
| Triangulation | 三角驗證 | 用多種有不同偏差的資料來源觀察同一件事，矛盾本身就是最值得調查的地方。 | 第 14 章 |
| Tribal knowledge | 部落知識 | 存在於成員腦中、尚未寫下來的知識落差。 | 第 10 章 |
| Tricorder | Tricorder | Google 在 code review 中整合各種靜態分析器的平台，以 effective false positive 衡量分析品質。 | 第 21 章 |
| Trigram index | 三字元索引 | 把檔案切成所有連續三字元片段並建立倒排表的程式碼搜尋索引。 | 第 21 章 |
| Trunk-based development | 主幹開發 | 所有開發者頻繁把小變更整合進同一條主幹，feature branch 很短命或不存在。 | 第 19 章 |
| TTL（time to live） | 存活時間 | DNS 回答可以被快取多久；但多層快取未必遵守，切換無法立刻生效。 | 第 37 章 |
| Tutorial | 教學 | 帶新手從零完成第一件事、每一步都能照做的文件。 | 第 17 章 |
| Type checker | 型別檢查器 | 不執行程式就檢查型別是否一致的工具，也能用型別執行領域規則。 | 第 15 章 |
| Typosquatting | 錯字搶註 | 註冊和熱門套件只差一兩個字元的名稱，等開發者打錯字時安裝到惡意版本。 | 第 20 章 |

## U

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Unit test | 單元測試 | 驗證一小段程式行為的測試，通常是 small size、narrow scope。 | 第 23 章 |
| USE（Utilization、Saturation、Errors） | USE 方法 | 給資源的三個指標：使用率、飽和度、錯誤。 | 第 33 章 |
| Utilization（ρ） | 使用率 | 到達速率除以處理能力；越接近 100%，延遲越非線性地上升。 | 第 36 章 |

## V

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Vendoring | 依賴內嵌 | 把依賴的原始碼複製一份放進自己的 repository，而不是在建置時下載。 | 第 20 章 |
| Version control system（VCS） | 版本控制系統 | 記錄檔案隨時間變化的系統，回答歷史、協作、回復三類問題。 | 第 19 章 |
| Version range | 版本範圍 | 在 manifest 中表達「我能接受哪些版本」的語法，例如 ^2.4.0。 | 第 20 章 |
| VIP（virtual IP） | 虛擬 IP | 背後是一整組 load balancer 的位址，讓 load balancer 本身可以擴充與壞掉一台。 | 第 37 章 |
| Visibility（build） | 可見性 | 控制「誰能依賴我」的 target 屬性，防止內部實作被到處引用。 | 第 27 章 |

## W

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Watermark | 水位線 | pipeline 估計「event time 早於 T 的資料應該都到了」的標記，到達後才產生 T 之前的結果。 | 第 42 章 |
| Wave | 波次 | canary 通過後依可用區或叢集逐波擴大 rollout。 | 第 29 章 |
| WCAG（Web Content Accessibility Guidelines） | 網頁內容無障礙指引 | W3C 的無障礙標準，以 POUR 四原則組織，大多數目標以 AA 等級為基準。 | 第 11 章 |
| Weighted round robin | 加權輪流 | 給每台 backend 權重，權重高的分到更多請求；權重可以由 backend 動態回報。 | 第 37 章 |
| What touched it last | 最後誰動過它 | 排查時先找最近的部署、設定變更、流量型態改變等變更的技巧。 | 第 43 章 |
| Wheel of Misfortune | 不幸之輪 | 由資深成員扮演系統、依過去真實事故出題，讓值班者口頭演練的角色扮演。 | 第 43 章 |
| White-box monitoring | 白箱監控 | 使用系統內部暴露的資料，能看到原因，甚至在症狀出現前看到問題醞釀。 | 第 33 章 |
| Wide events | 寬事件 | 每個請求記一筆帶有大量欄位的事件，查詢時才決定怎麼分組，是回答未知問題的能力來源。 | 第 33 章 |
| Workflow（Google） | Workflow 系統 | Google 於 2003 年開發、讓持續處理能在大規模下運作的 continuous pipeline 系統。 | 第 42 章 |
| Workload model | 負載模型 | 描述流量樣子的模型：request mix、arrival pattern、payload 與資料分佈、狀態。 | 第 25 章 |
| Worktree | 工作目錄樹 | Git 讓同一個 repository 同時有多個工作目錄的功能，常用來讓 agent 隔離工作。 | 第 19 章 |
| Wrapper | 包裝層 | 只透過一層自己的介面使用外部套件，降低日後替換成本；只暴露真正需要的部分。 | 第 20 章 |
| Write-audit-publish | 寫入、稽核、發布 | 先寫到暫存位置，驗證通過才發布，讓下游永遠只看到通過檢查的版本。 | 第 42 章 |

## Y

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| You build it, you run it | 你建造它，你就維運它 | 寫服務的團隊也要負責運作它。 | 第 30 章 |

## 中文術語

| 中文術語 | 英文對照 | 定義 | 首次詳細說明 |
|---|---|---|---|
| 停線權 | andon cord（概念借用） | 任何參與者看到異常都可以喊暫停，不需要先證明問題存在，由 owner 回應後再決定是否繼續。 | 第 9 章 |
| 利息與本金 | — | 技術債的兩個成分：利息是每次修改多付的力氣，本金是改成理想做法的成本；只有修改時才付利息。 | 第 4 章 |
| 授權階梯 | — | agent 權限依證據逐步取得的分級，從只讀、建議、shadow mode 到範圍內自動執行。 | 第 31 章（詳見第 47 章） |
| 知識孤島 | knowledge silo | 某件事只有一個人或一個團隊知道，那人休假或離職事情就停擺。 | 第 6 章 |
| 逃逸缺陷分析 | — | 每次 production 事故或使用者回報的 bug 都問「哪一層測試應該最早抓到它？為什麼沒有？」。 | 第 22 章 |
| 雙比例 z 檢定 | two-proportion z-test | 判斷 canary 與 control 的錯誤率差異是否可能只是隨機波動的統計檢定。 | 第 29 章 |
| 順序相依 | — | 測試結果取決於其他測試是否先執行，常由 test pollution 造成，在並行或隨機順序下浮現。 | 第 26 章 |
