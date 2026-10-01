---
chapter: 40
title: Distributed Consensus 與 Critical State
part: 6
---

# 第 40 章　Distributed Consensus 與 Critical State

> [!abstract] 本章地圖
> **核心問題**：當訊息會延遲、機器會暫停、網路會分割，多台機器要怎麼對「誰是 leader」「庫存剩多少」「這把鎖在誰手上」得到同一個、不會反悔的答案？
>
> **你會學到**：
> - 分辨 critical state 與一般狀態，說明為什麼 heartbeat 加 timeout 做不出正確的 failover
> - 正確解讀 CAP 與 PACELC，判斷一個功能在網路分割時該選一致性還是可用性
> - 用 quorum 交集解釋為什麼 2f+1 個節點能容忍 f 個故障，以及為什麼偶數節點沒有幫助
> - 用 term、投票與 log 的直覺讀懂 Paxos／Raft 在做什麼
> - 用 lease 與 fencing token 擋住「以為自己還是 leader」的舊節點
> - 估算 consensus 的延遲與吞吐，設計 replica 的數量與地理位置，並知道何時直接用 etcd／ZooKeeper
>
> **前置知識**：第 37 章（health check 與 lame duck）、第 39 章（timeout、retry 與 backoff）
>
> **對應原書**：SRE 第 23 章〈Managing Critical State: Distributed Consensus for Reliability〉

## 40.1 故事：兩個 primary 的十二分鐘

Harbor 第四年三月的週年慶，行銷團隊推出一檔限量 500 組的聯名保溫瓶，晚上八點整開賣。這是 Harbor 開始為當年雙十一做準備之前的事。那時 Harbor 的 inventory（庫存）服務已經搬到雲端的兩個可用區（availability zone，同一地區內電力與網路彼此獨立的機房）：zone A 放主要資料庫（primary），zone B 放一份即時複製的備援（replica）。為了「高可用」，platform 團隊寫了一支 watchdog 程式跑在 zone B：每 2 秒 ping 一次 primary，連續三次沒回應，就自動把 replica 升級成新的 primary，並更新 DNS。

八點零三分，兩個 zone 之間的網路因為流量暴增開始掉封包。不是完全斷線，只是一部分封包遲到或消失。zone B 的 watchdog 連續三次 ping 失敗，判斷 primary 死了，把 replica 升級。問題是舊 primary 根本沒死，它和 zone A 的應用伺服器之間連線完全正常，繼續接受下單。DNS 的快取又讓一部分應用伺服器在幾分鐘內仍連到舊 primary。

接下來十二分鐘（大約八點零三分到八點十五分），Harbor 有兩個都認為自己是唯一真相的資料庫，各自扣庫存。等 SRE 志明發現 checkout 的成功數超過 500、手動把舊 primary 關掉時，保溫瓶已經賣出 731 組。客服要向 231 位客人道歉退款，checkout 團隊花了兩天把兩邊分岔的訂單歷史對齊，有些訂單在兩邊各有一個版本，誰才是對的已經說不清楚。

事後檢討時，seller 團隊的阿凱問：「watchdog 判斷錯了，那把 timeout 從 6 秒調成 30 秒不就好了？」checkout 的 tech lead 美華搖頭：「調長只會讓真正當機時恢復得更慢，誤判還是會發生。只要網路夠慢，任何 timeout 都可能誤判。問題不在數字，而在我們用 timeout 回答了一個 timeout 回答不了的問題：『現在誰才是 primary？』」

這一章要講的，就是如何讓一群機器在不可靠的網路上，對這種問題得到唯一、不會反悔的答案。這類問題叫 **distributed consensus**（分散式共識），而需要用它保護的資料，叫 **critical state**（關鍵狀態）。

## 40.2 Critical state：為什麼單機的直覺在這裡失效

### 什麼是 critical state

**Critical state** 是「如果不同機器對它的看法不一致，就會造成錯誤、而且很難事後修復」的狀態。判斷方式很簡單：問「如果兩台機器同時認為不同的答案是對的，會發生什麼事？」如果答案是「有點慢」或「稍後會自己對齊」，那不是 critical state；如果答案是「超賣」「重複扣款」「兩個程式同時改同一份資料」，那就是。

Harbor 的例子：

| 狀態 | 兩邊不一致的後果 | 是否 critical |
|---|---|---|
| 誰是 inventory 的 primary | 兩邊各自扣庫存，超賣 | 是 |
| 限量商品剩餘數量 | 賣出超過實際庫存 | 是 |
| 哪個 worker 持有「發送賣家撥款」這個工作 | 同一筆款項付兩次 | 是 |
| 目前生效的金流路由設定 | 一半的請求送到已停用的金流商 | 是 |
| 商品頁的瀏覽次數 | 數字晚幾分鐘對齊 | 否 |
| 推薦結果的快取 | 不同使用者看到稍舊的推薦 | 否 |

大部分系統的 critical state 其實很小：一個 leader 的名字、一份設定、一個鎖、幾個計數器。這個觀察很重要，因為本章的工具很昂貴，只該用在這一小塊資料上。

### 分散式系統的三個殘酷事實

單機程式裡，「讀一個變數」得到的就是那個變數現在的值。分散式系統沒有這種奢侈，原因有三。

**第一，沒有共同的「現在」。** 每台機器有自己的時鐘，時鐘會漂移（clock drift），NTP 校時也只能把誤差壓到某個範圍，無法歸零。你無法單靠時間戳判斷兩件發生在不同機器上的事誰先誰後。

**第二，你分不出「慢」和「死」。** 送出請求後沒收到回應，可能是對方當機、對方還活著但 process 正卡在 garbage collection（GC，記憶體回收）停頓、對方回了但回應在網路上遲到、或是去程的封包就掉了。從發送端看，這幾種情況完全一樣。Harbor 的 watchdog 就是把「網路慢」誤判成「primary 死了」。

**第三，故障是局部的。** 單機壞掉時通常整台一起壞；分散式系統壞掉時，常常是 A 看得到 B、B 看不到 C、C 只看得到一半的請求。網路分割（network partition）也不一定乾淨：可能只有單向不通，或只有部分封包丟失。

這三件事組合起來，導出分散式計算裡一個著名的結果：**FLP impossibility**（由 Fischer、Lynch、Paterson 三位作者在 1985 年發表）。它說，在訊息延遲沒有上限的非同步網路裡，只要可能有一個節點當機，就沒有任何確定性的演算法能保證一定在有限時間內達成共識。實務系統繞過它的方式，是假設網路「大部分時間」夠好，並用隨機化的 timeout 與 backoff 讓僵局終究會被打破。

這聽起來很絕望，但實務上的意義是：**共識演算法把正確性和進度分開保證**。

- **Safety**（安全性）：壞事永遠不會發生。例如永遠不會有兩個不同的值被 commit、不會有兩個 leader 在同一個世代同時成功寫入。這一點在任何網路狀況下都必須成立。
- **Liveness**（活性）：好事最終會發生。例如最終會選出 leader、請求最終會被處理。這一點只在「網路夠好、多數節點活著」時才保證。

好的協定在網路很糟時寧可停下來（犧牲 liveness），也不會給出錯的答案（犧牲 safety）。Harbor 的 watchdog 剛好相反：網路一糟，它選擇繼續服務，代價是給出兩個互相矛盾的答案。

### Failure model：你假設會壞成什麼樣子

設計或選擇協定時，要先說清楚你預期的故障種類，也就是 **failure model**：

- **Crash-stop**：節點壞了就永遠不回來。最簡單，但不符合現實。
- **Crash-recovery**：節點可能當機後重啟，帶著磁碟上的資料回來。這是實務上最常用的假設，也代表協定必須把承諾寫進持久儲存，重啟後才能遵守。
- **Byzantine**：節點可能送出錯誤甚至惡意的訊息。處理它的代價高得多（需要 3f+1 個節點才能容忍 f 個），一般企業內部系統很少用，區塊鏈這類互不信任的環境才需要。

本章討論的 Paxos、Raft、Zab 都是 crash-recovery、非 Byzantine 的協定。它們假設節點可能當機、重啟、變慢，但不會說謊。

> [!warning] 常見誤解
> 「用 STONITH（Shoot The Other Node In The Head，偵測到對方失聯就把對方強制關機）就能避免 split-brain。」SRE 書舉過這樣的案例：網路變慢時，兩台機器都覺得對方死了，各自送出關機指令，結果可能兩台都被關掉，或關機指令沒送到、兩台都繼續當主。STONITH 本身仍然是靠 timeout 做判斷，只是把誤判的後果換了一種形式。

## 40.3 CAP 與 PACELC：一致性要付的帳

### 先定義「一致」

談 CAP 之前，要先把「一致」講精確。分散式系統裡最強、也最符合直覺的一致性叫 **linearizability**（線性一致性）：整個系統表現得好像只有一份資料，每個操作在它開始與結束之間的某一個瞬間「原子地」生效，而且一旦某個讀取看到了新值，之後任何人的讀取都不會再看到舊值。

例子：志明在 zone A 把保溫瓶庫存從 10 改成 9，寫入成功回傳。之後阿凱在 zone B 讀取，linearizable 的系統保證阿凱讀到 9 或更新的值，絕不會讀到 10。很多系統只提供較弱的保證，例如 **eventual consistency**（最終一致性）：如果之後不再有寫入，各副本最終會收斂到同一個值，但在收斂之前，讀到舊值是允許的。

### CAP 的正確讀法

**CAP theorem**（由 Eric Brewer 在 2000 年 PODC 研討會的主題演講中提出猜想，Seth Gilbert 與 Nancy Lynch 在 2002 年把它形式化並證明）常被簡化成「Consistency、Availability、Partition tolerance 三選二」。這個說法誤導了很多人，因為網路分割不是你能「不選」的東西：線路會被挖斷、交換器會故障、壅塞會讓封包遲到。

比較準確的讀法是：**當網路分割發生時，系統必須在一致性與可用性之間二選一。**

```text
         zone A                    ✂ 網路分割 ✂                 zone B
  ┌──────────────────┐                                  ┌──────────────────┐
  │ client ──► 副本 1 │  ←──────── 互相聯絡不到 ───────→  │ 副本 2 ◄── client │
  └──────────────────┘                                  └──────────────────┘

  選擇 C（一致性）：無法確認另一側狀態的那一側拒絕寫入（甚至拒絕讀取）
                   → 資料永遠只有一個版本，但部分使用者收到錯誤
  選擇 A（可用性）：兩側都繼續接受讀寫
                   → 每個人都得到回應，但兩側資料會分岔，之後要合併
```

左右兩個副本聯絡不到彼此。如果選一致性，至少有一側必須停止接受寫入，因為它無法確認另一側沒有寫入衝突的值；如果選可用性，兩側都繼續服務，代價是資料暫時（或永久）不一致，事後必須用某種規則合併。Harbor 的保溫瓶事故，等於是在一個需要一致性的資料上，無意間選擇了可用性。

### PACELC：沒有分割時也有取捨

CAP 只談分割發生時。但多數時候網路是正常的，這時系統仍有取捨：要等多數副本確認才回應（一致但慢），還是寫入本地就回應（快但副本間有落差）？**PACELC**（Daniel Abadi 在 2010 年的部落格文章中提出，2012 年在 IEEE Computer 的論文中正式發表）把這件事補上：

```text
if Partition:  在 Availability 與 Consistency 之間選
Else:          在 Latency 與 Consistency 之間選
```

幾個典型例子：

| 系統類型 | 分割時（PA／PC） | 平常（EL／EC） | 適合 |
|---|---|---|---|
| etcd、ZooKeeper 等 consensus 系統 | PC：少數側停止寫入 | EC：每次寫入等 quorum | leader、鎖、設定 |
| Dynamo 風格的 key-value store（可調參數） | PA：兩側都接受寫入 | EL：寫入少數副本即回應 | 購物車、session、計數 |
| 傳統資料庫非同步複製 | 取決於 failover 設計 | EL：primary 寫完就回應，replica 落後 | 一般業務資料 |
| Google Spanner | PC | EC：用 TrueTime 等待時鐘不確定區間（commit wait） | 全球一致的交易資料 |

Harbor 的不同功能可以有不同選擇。購物車在分割時應該繼續可用，事後把兩邊加入的商品合併就好（最壞情況是使用者看到一件自己刪掉的商品又出現）；限量商品的庫存扣減必須選一致性，少數側寧可回「系統忙碌，請稍後再試」，也不能多賣。

> [!warning] 常見誤解
> 「我們的資料庫是 CP，所以整個服務都是一致的。」一致性是端到端的性質。如果應用層在資料庫前面加了一層沒有失效機制的快取，或者 client 在 timeout 後直接用本地狀態重試，整條路徑仍然可能讀到舊值或寫入重複。

## 40.4 Consensus 解決什麼：從「同意一個值」到 replicated state machine

### 最小的問題：大家同意一個值

**Distributed consensus** 最原始的定義是：一群節點各自可能提議不同的值，協定要讓它們最終同意同一個值，而且這個值一定是某個節點提議過的，一旦決定就不會改變。聽起來很小，但幾乎所有協調問題都可以化成它。

把「同意一個值」重複很多次，就得到一串大家都同意順序的操作，也就是一份 **replicated log**（複製日誌）：第 1 格是「庫存設為 500」、第 2 格是「扣 1」、第 3 格是「扣 1」……。每台機器依同樣順序執行同一份 log，就會得到同樣的狀態。這種架構叫 **replicated state machine**（RSM，複製狀態機），它是 etcd、ZooKeeper、Consul、以及許多分散式資料庫的核心。

```text
  client 請求
      │
      ▼
 ┌─────────┐  共識層：決定「第 N 格放哪個操作」
 │ Leader  │──────────────┬───────────────┐
 └─────────┘              ▼               ▼
      │              ┌─────────┐     ┌─────────┐
      ▼              │Follower │     │Follower │
 log: [1][2][3][4]   │[1][2][3]│     │[1][2][3][4]│
      │              └─────────┘     └─────────┘
      ▼                   │               │
 狀態機依序套用：     狀態機依序套用     狀態機依序套用
 stock = 497          stock = 498       stock = 497
                    （稍微落後，但順序相同，終會追上）
```

共識層只負責「每一格放什麼、順序是什麼」；狀態機只負責「照順序執行」。只要操作是確定性的（同樣輸入一定得到同樣結果），所有副本終將處於相同狀態。落後的副本不會給出「不同的」答案，只會給出「較舊的」答案，而協定可以確保需要最新答案的讀取不會從落後的副本拿到舊值（40.8 節）。

### 建立在共識上的常見元件

SRE 書指出，共識演算法本身很底層，真正有用的是建在它上面的元件：

- **設定與 metadata 儲存**：Kubernetes 把整個叢集狀態存在 etcd，就是一例。
- **Leader election**（領導者選舉）：一群相同的 process 中選一個來做事，其他待命。
- **分散式鎖與 lease**：保證同一時間只有一個持有者，並在持有者當機時自動釋放。
- **Group membership**（成員資格）：大家同意「現在這個叢集有哪些成員」。
- **可靠的佇列與 atomic broadcast**：所有人以相同順序收到同一串訊息。

SRE 書的建議很直接：**只要你看到 leader election、critical shared state 或 distributed locking，就應該用經過形式化證明且被充分測試的共識系統**；用 heartbeat、gossip 或自己寫的 timeout 邏輯拼湊，遲早會遇到資料不一致的問題，而且這類問題特別難查。

## 40.5 Quorum：為什麼是 2f+1

### 交集是一切的基礎

**Quorum** 是「足以代表整體做決定」的節點集合。最常用的是 **majority quorum**（多數決）：n 個節點中，超過一半（⌊n/2⌋+1）同意才算數。

多數決的魔力在於：**任意兩個 majority 一定至少有一個共同成員**。如果 5 個節點中，{A, B, C} 同意了「第 7 格是扣 1」，之後任何 quorum，例如 {C, D, E}，一定包含 A、B、C 中的至少一個。新的決策在做之前，一定會遇到一個「知道舊決策」的節點，協定就能藉此避免推翻已 commit 的結果。

這也是為什麼網路分割時，最多只有一側能繼續寫入：兩側不可能同時都擁有超過一半的節點。Harbor 事故的根本問題，就是 zone B 的 watchdog 只憑「一個節點自己的觀察」就做了決定，那不是 quorum。

### 2f+1 的算術

要容忍 f 個節點同時故障，剩下的節點必須仍然構成多數，所以需要 n ≥ 2f+1：

| 節點數 n | Quorum 大小 | 可容忍同時故障 f | 說明 |
|---|---|---|---|
| 1 | 1 | 0 | 沒有容錯 |
| 2 | 2 | 0 | 壞一台就停，比 1 台更容易停（兩台都得活著） |
| 3 | 2 | 1 | 最小的實用規模 |
| 4 | 3 | 1 | 容錯和 3 台一樣，卻多一台可能壞的機器 |
| 5 | 3 | 2 | 常見的生產規模 |
| 7 | 4 | 3 | 容錯更高，但每次寫入要等更多節點 |

算例：5 個節點，quorum 是 3。壞 2 台，剩 3 台仍能寫入；壞 3 台，剩 2 台，無法寫入，系統停止（但不會給錯答案）。

偶數節點不增加容錯：4 台的 quorum 是 3，只能壞 1 台，和 3 台相同，卻多了一台會故障的機器、多一份網路流量。這就是為什麼共識叢集幾乎都是奇數。SRE 書還提到一個更細的情境：一個組織有 5 個資料中心、每個放一個 replica，quorum 是 3，失去任何一個資料中心後還剩一台餘裕；若在其中一個資料中心多放第 6 個，quorum 變成 4，那個資料中心一斷就同時失去兩個 replica，剩下的 4 個剛好等於 quorum，沒有任何餘裕。多放一台反而讓系統更脆弱。

### 3 個還是 5 個？

SRE 書的推理值得照著走一遍：大部分停機來自計畫內的維護。3 個 replica 時，維護一台還剩 2 台，仍然能運作，但已經沒有容錯；這時若再意外壞一台，整個系統就停了。5 個 replica 則能在維護一台的同時，再承受一台意外故障。所以承載關鍵狀態、不能停的共識系統，常見做法是 5 個。

### 失去 quorum 是災難

如果同時壞掉的節點多到湊不出 quorum，系統就會停在原地，而且這不是重啟就能解決的問題：缺席的節點身上可能有某筆已 commit 的決策。管理者可以強制修改成員資格，讓剩下的節點繼續，但這可能丟資料。這時要做的判斷是「等那些機器回來」還是「接受可能的資料遺失並強制恢復」，這需要事先寫好的 runbook 和清楚的決策權（第 44 章），而不是凌晨三點臨場發揮。

> [!tip] 維運原則
> 5 個 replica 剩 4 個時不必緊急處理；剩 3 個時就該盡快補一到兩個。把「健康 replica 數等於 quorum（已經沒有餘裕）」設成 page，而不是等到失去 quorum 才知道。

## 40.6 Paxos 與 Raft 的直覺

你不需要能從頭實作共識演算法，但要能讀懂它的日誌、指標與故障行為。以下用直覺講兩個最常見的協定。

### Paxos：兩階段的「先佔位、再提交」

**Paxos** 是 Leslie Lamport 提出、最早也最有影響力的共識協定之一（論文〈The Part-Time Parliament〉在 1998 年正式發表）。角色有 **proposer**（提議者）與 **acceptor**（接受者）。每個提議帶一個全域唯一、可以比大小的編號（proposal number）。

1. **Prepare／Promise**：proposer 對 acceptors 說「我要用編號 n 提議」。acceptor 若沒見過比 n 更大的編號，就承諾「之後不再接受比 n 小的提議」，並把自己已經接受過的最高編號提議回報給 proposer。
2. **Accept／Accepted**：proposer 收到多數承諾後，送出「請接受編號 n、值 v」。如果第一階段有 acceptor 回報已接受過某個值，proposer 必須沿用其中**編號最高**的那個值，而不是自己的。多數 acceptor 接受，這個值就被選定。

兩個關鍵：第一，多數決的交集保證新 proposer 一定會在第一階段發現已被選定的值；第二，acceptor 每次承諾或接受都要先寫入持久儲存，否則重啟後忘記自己的承諾，就會違反協定。

單一 Paxos 只能決定一個值。實務上用的是 **Multi-Paxos**：選出一個穩定的 leader，它做過一次第一階段之後，後續每個 log 格子只需要第二階段，也就是一次往返就能 commit。如果多個 proposer 同時搶著當 leader，它們會不斷用更大的編號打斷對方，誰都 commit 不了，這叫 **dueling proposers**，是一種 livelock（活鎖：大家都在動，但沒有進展）。解法是隨機化的 backoff，這和第 39 章 retry 加 jitter 的道理一樣。

### Raft：為了好懂而設計

**Raft**（Diego Ongaro 與 John Ousterhout 的論文〈In Search of an Understandable Consensus Algorithm〉，2014 年發表於 USENIX ATC）解的是同一個問題，但刻意設計得容易理解與實作，今天 etcd、Consul 等系統都用 Raft。ZooKeeper 則用一個叫 Zab 的類似協定。Raft 把問題拆成三塊：

**一、Term（任期）。** 時間被切成一段段編號遞增的 term，每個 term 最多一個 leader。term 就像「朝代編號」：任何節點收到帶有更大 term 的訊息，立刻更新自己的 term 並退回 follower；收到更小 term 的訊息，直接拒絕。舊 leader 回來時，一看到更大的 term 就知道自己已經被取代。

**二、Leader election。** Follower 一段時間沒收到 leader 的 heartbeat，就把 term 加一，成為 candidate，向其他節點拉票。每個節點在一個 term 裡只投一票，而且**只投給 log 至少和自己一樣新的候選者**。拿到多數票就當選。為了避免大家同時參選、票被瓜分，每個節點的選舉 timeout 是隨機的（Raft 論文的例子是 150–300 毫秒之間），通常只有一個節點最先醒來參選。

注意這裡也用了 timeout，但角色完全不同：timeout 只負責「觸發選舉」，真正決定誰是 leader 的是多數投票。timeout 誤判的後果只是一次多餘的選舉，不會產生兩個同時有效的 leader。

**三、Log replication。** Client 的寫入只送給 leader。leader 把操作附加到自己的 log，平行送給 followers（AppendEntries）。當多數節點都把這一格寫進持久儲存，leader 就把它標為 **committed**，套用到狀態機並回應 client。每次 AppendEntries 都附上「前一格的位置與 term」，follower 對不上就拒絕，leader 往前退一格重送，直到兩邊找到共同的起點，再用 leader 的版本覆蓋 follower 不一致的部分。

```text
 term 1：A 是 leader                       term 2：分割後 C 當選
 ┌───┬───────────────┐                   ┌───┬───────────────────────────┐
 │ A │ [1:stock=100] │                   │ A │ [1:stock=100][1:stock=99✗] │ ← 少數側，未 commit
 │ B │ [1:stock=100] │                   │ B │ [1:stock=100][1:stock=99✗] │
 │ C │ [1:stock=100] │   網路分割         │ C │ [1:stock=100][2:stock=97✓] │ ← 多數側 commit
 │ D │ [1:stock=100] │  {A,B} | {C,D,E}  │ D │ [1:stock=100][2:stock=97✓] │
 │ E │ [1:stock=100] │  ───────────────► │ E │ [1:stock=100][2:stock=97✓] │
 └───┴───────────────┘                   └───┴───────────────────────────┘
                                          分割恢復後：A 看到 term 2，退回 follower；
                                          A、B 第 2 格未 commit 的內容被 C 的版本覆蓋
```

逐步解讀這張圖：分割前，A 是 term 1 的 leader，第 1 格已經在所有節點上 commit。分割後，A 仍然以為自己是 leader，它把「stock=99」寫進自己和 B 的 log，但只有 2 個 ack，不到 3，所以不能 commit，也不能回覆 client「成功」。多數側的 C 等不到 heartbeat，以 term 2 參選，拿到 C、D、E 三票當選，它寫入的「stock=97」得到 3 個 ack，順利 commit。分割恢復後，A 一聯絡其他節點就看到 term 2，立刻退回 follower；A、B 第 2 格那筆從未 commit 的內容被覆蓋。從頭到尾，**沒有任何 client 被告知過兩個互相衝突的成功結果**。

> [!warning] 常見誤解
> 「網路分割時不會有兩個 leader。」其實可能會短暫出現兩個「自認為」的 leader，就像圖中的 A 和 C。協定保證的不是「不會有人誤以為自己是 leader」，而是「舊 leader 沒有辦法 commit」。這個區別在 40.7 節會變得非常重要：如果舊 leader 不只是寫 log，而是直接去操作外部系統，協定就保護不到了。

### Safety 的關鍵規則

Raft 為什麼能保證已 commit 的資料不會遺失？靠的是投票規則：一筆資料要 commit，必須已經在多數節點上；一個候選者要當選，也必須得到多數票，而投票者只投給 log 至少和自己一樣新的人。兩個多數一定有交集，所以新 leader 的 log 必然包含所有已 commit 的內容。這叫 **leader completeness**（領導者完整性）。這也是 SRE 書提到的一個實務推論：5 個節點的 Raft 叢集即使只剩 leader 活著，leader 也知道所有已 commit 的決策；但如果失去的多數中包含 leader，剩下的節點就無法保證自己有最新資料。

## 40.7 Leader election、lease 與 fencing token

### 為什麼需要 leader

很多服務的工作本身適合由一個 process 做，例如 Harbor 的「限量商品配額分配器」、第 41 章的分散式 cron 排程器。最簡單的高可用做法是：把同一個程式跑三份，用共識系統選出一個 leader 做事，其他兩份待命。SRE 書把這描述成「把高可用服務寫得像一個簡單的單機程式，然後複製它，用 leader election 保證同一時間只有一個在工作」。這種用法裡，共識系統不在每個請求的關鍵路徑上，只負責選舉，吞吐量通常不是問題。

### Lease：會過期的權力

選出 leader 之後，還有一個問題：leader 怎麼知道自己「仍然」是 leader？如果它每做一件事都要問一次共識系統，就太慢了。常見做法是 **lease**（租約）：共識系統授予 leader 一段有期限的權力，例如 10 秒；leader 必須在到期前續約（renew），否則權力自動失效，其他節點可以接手。

Lease 比無限期的鎖好，因為持有者當機時，不需要任何人手動解鎖，時間到了就自然釋放。SRE 書特別強調：實務上一定要用**可續約、會過期的 lease**，不要用無限期的鎖。

但 lease 有一個根本性的弱點：它依賴時間。leader 判斷「我的 lease 還沒過期」用的是自己的時鐘，共識系統判斷「lease 已經過期、可以給別人」用的是自己的時鐘。如果 leader 的時鐘走得慢，或者 process 在關鍵時刻停頓，兩邊對「現在」的認知就會不同。

### 那個醒來的舊 leader

想像 Harbor 的配額分配器 A 取得 lease，然後：

```text
時間 →
A:   取得 lease ─┬─ 檢查：lease 還有效 ─── [ GC 停頓 15 秒 ] ─── 醒來，寫入 stock=99 ✗
                 │
共識系統:         └───────── lease 10 秒到期 ──┬─ 授予 C 新 lease
                                              │
C:                                            └─ 取得 lease，寫入 stock=97
```

A 在「檢查 lease 有效」與「真正寫入」之間停頓了 15 秒。對 A 來說，它剛剛才確認過自己是 leader；它完全不知道時間已經過了 15 秒、lease 已經給了 C。這不是罕見的邊界情況：GC 停頓、虛擬機被 hypervisor 暫停、容器被限制 CPU、甚至 laptop 闔上螢幕，都可能讓一個 process 在任意兩行程式之間「消失」一段時間。無論 A 檢查 lease 多少次，檢查和動作之間永遠有一個縫隙。

### Fencing token：讓資源自己拒絕舊世代

解法是把檢查移到資源那一側。每次授予 lease 時，共識系統同時給一個**單調遞增的數字**，叫 **fencing token**。A 拿到 33，C 拿到 34。持有者每次寫入資源時都附上自己的 token；資源記住它見過的最大 token，**任何比它小的 token 一律拒絕**。

```text
A（token 33）──┐
               ├──► 資源：見過的最大 token = 34
C（token 34）──┘     收到 33 → 拒絕；收到 34 → 接受
```

這樣即使 A 醒來後真的送出寫入，也會被資源擋下。token 的來源必須是共識系統本身，因為只有它能保證數字全域遞增：在 Raft 系統中，term 就是天然的 token；etcd 每次修改都會產生全域遞增的 revision，可以拿 key 建立時的 revision 當 token；ZooKeeper 有遞增的交易編號（zxid），也能用 sequential znode 的序號；Google 的 Chubby 鎖服務把同樣的概念稱為 sequencer。

Fencing 的前提是**資源願意檢查 token**。Harbor 的庫存資料庫可以這樣做：

```text
UPDATE stock
   SET qty = qty - 1, fence = :token
 WHERE sku = :sku AND qty > 0 AND fence <= :token;
-- 影響 0 列 → 若 qty 仍 > 0，表示 token 過期，持有者必須立刻停止工作
```

如果資源無法檢查 token（例如一個不支援條件寫入的外部 API），就要退而求其次：在資源前放一個會檢查 token 的代理、讓操作本身是 idempotent 的（第 41 章），或者接受風險並用事後對帳偵測。

> [!example] Harbor 的修正
> 事故後，Harbor 把 inventory 的資料庫擴成三個 zone、一主兩 replica，並把 failover 改成：三個 zone 各跑一個 etcd 成員；資料庫 HA 工具（這類工具例如 PostgreSQL 的 Patroni，可以用 etcd、Consul、ZooKeeper 或 Kubernetes 存放「誰是 primary」）透過 etcd 上一把有 TTL、需要定期續約的 leader key 選出 primary，舊 primary 一旦無法續約，就自行降級、停止接受寫入；應用程式不再依賴 DNS 找 primary，而是透過連線代理，代理只把寫入送到 HA 工具確認的現任 primary。庫存扣減這類應用層的工作者，則另外用 etcd lease 加上前面那條帶 fencing 條件的 SQL。分割時，只有和多數 etcd 成員連得上的那一側能保有 primary；另一側的下單請求會失敗，但不會超賣。第 39 章雙十一當晚 inventory 主資料庫的 failover 能在二十幾秒內自動、安全地完成，靠的就是這次改造。
>
> 要注意「無法續約就降級」本身仍依賴時間：舊 primary 必須在新 primary 被選出之前就先停手，所以 HA 工具會讓 leader key 的 TTL 明顯長於續約間隔與降級所需的時間。這是設計上的安全餘裕，不是數學保證，這也是為什麼連線代理和應用層 fencing 仍然要有。

### 失去 leader 身分時要立刻停手

SRE 書描述 Google 分散式 cron 時強調：leader 一旦因為任何原因失去領導權，必須**立刻停止**和外部系統互動。實作上，這代表 leader 的每一個「動作迴圈」開頭都要檢查 lease 狀態、每一個外部寫入都帶 fencing token，而且續約失敗時要主動中斷進行中的工作，而不是「做完這一批再說」。

## 40.8 效能、讀取一致性與地理部署

### 一次寫入要花多少時間

共識不是免費的。一次 commit 至少要付兩筆帳：**網路往返**（leader 到多數 follower 再回來）與**持久寫入**（每個節點把 log 寫進磁碟並 fsync，確保斷電也不會遺失）。

```text
commit 延遲 ≈ 到「第 (quorum−1) 近」的 follower 的 RTT + 該 follower 的 fsync
（leader 自己算一票，所以 5 節點時要等第 2 近的 follower 回應；
  leader 本地的 fsync 通常和送出複製平行進行，但若它比較慢，就由它決定延遲）
```

SRE 書給了幾個量級：同一資料中心內的 RTT 約 1 毫秒；美國境內典型約 45 毫秒；紐約到倫敦約 70 毫秒。磁碟寫入依硬體與虛擬化環境不同，從 1 毫秒到數毫秒不等。

算例：如果 fsync 要 10 毫秒，且每次只處理一筆，一秒最多約 100 次 commit。這就是為什麼共識系統普遍使用 **batching**（批次：把多筆請求打包成一次共識）與 **pipelining**（管線：不等上一批完成就送出下一批）。兩者都不破壞順序，因為每一批仍然有明確的 log 位置。

這也解釋了一個常見的事故模式：etcd 叢集放在共享的慢速磁碟上，fsync 延遲升高，heartbeat 跟著延遲，follower 以為 leader 死了而發起選舉，叢集不停換 leader（leader flapping），寫入幾乎停擺。所以共識系統的磁碟延遲本身就是需要監控的指標，最好使用專用、低延遲的磁碟。

### 讀取也有一致性選擇

寫入一定要經過共識，讀取則有好幾種選擇，差別在於「保證多新」與「多快」：

| 讀取方式 | 保證 | 代價 | 適合 |
|---|---|---|---|
| 經過共識的讀取（把讀當成一筆 log） | Linearizable | 和寫入一樣慢 | 極少數必須最新的讀取 |
| Leader 確認自己仍是 leader 後讀取（Raft 的 ReadIndex 一類做法） | Linearizable | 一次 heartbeat 往返 | 大部分強一致讀取 |
| Leader 憑 lease 直接讀本地 | Linearizable，但依賴時鐘誤差有上限 | 幾乎沒有額外延遲 | 時鐘可信的環境 |
| 從任一 follower 讀 | 可能讀到舊值（stale read） | 最快、可水平擴充 | 讀到舊值只會「多做事」、不會「做錯事」的場景 |

SRE 書提到 Google 的 Photon 系統：狀態修改必須用強一致的 compare-and-set，但讀取可以從任何副本來，因為讀到舊資料的後果只是多做一點工作，不會產生錯誤結果。這是一個很好的判斷範例：**一致性需求要依操作分別決定，不必整個系統一刀切**。

### Replica 放在哪裡

Replica 的位置決定兩件事：能承受多大範圍的故障，以及寫入延遲有多高。距離越遠，能扛的災難越大，每次寫入也越慢。

```text
選項一：同一地區、三個 zone           選項二：跨三個地區
 zone A   zone B   zone C              台灣    日本    新加坡
  [e1]     [e2]     [e3]               [e1]    [e2]    [e3]
  RTT ≈ 1–2 ms                          RTT ≈ 數十 ms
  扛得住：一個 zone 失效                扛得住：整個地區失效
  扛不住：整個地區失效                  代價：每次寫入多數十毫秒
```

選項一的 RTT 很小，寫入快；任何一個 zone 斷電或斷網，剩下兩個仍是多數。選項二能在整個地區失效時存活，但每次寫入都要跨國往返。要選哪一個，SRE 書的建議是回到 client：**如果所有使用這個共識系統的服務都在同一個地區，地區整個失效時它們也一起停了，把共識系統部署到更遠只會多付延遲，換不到任何可用性**。Harbor 的服務都在同一地區，所以 etcd 跨三個 zone 就夠了；真正的跨地區災難復原，靠的是定期把快照備份到另一個地區（第 42、46 章）。

SRE 書還指出幾個地理部署的陷阱：

- **Leader 的位置很重要**：所有寫入都經過 leader，離 leader 遠的 client 延遲較高；leader 的對外網路頻寬也是瓶頸，因為只有它送出完整資料。
- **關鍵的「連結 replica」**：5 個 replica 分在兩群加中間一個時，中間那台同時屬於兩邊最近的 quorum；它一壞，每次寫入都要跨越最遠的距離，延遲可能突然大增。
- **Leader 集中的連鎖反應**：如果很多共識群組的 leader 都剛好集中在同一個資料中心，那裡一出事，所有 leader 一起搬家，其他資料中心之間的網路流量會瞬間暴增。
- **跨地區的大量 client**：用區域代理（regional proxy）維持到共識叢集的長連線，避免每個 client 都跨地區建立 TCP 連線。

### 該監控什麼

依 SRE 書的建議整理，Harbor 為 etcd 叢集設定的監控如下：

| 指標 | 為什麼重要 | 告警方向 |
|---|---|---|
| 健康成員數 | 剩 quorum 數時已無容錯 | 少於 n−1 開 ticket；等於 quorum 就 page |
| 是否存在 leader | 沒有 leader 就完全無法寫入 | 持續數秒無 leader 即 page |
| Leader 變更次數（term 增加速度） | 頻繁換 leader 代表網路或磁碟有問題；term 變小代表嚴重 bug | 短時間內多次變更即告警 |
| Commit 的 log 位置是否持續前進 | 確認系統真的有進展 | 有寫入流量但不前進即 page |
| 提議數與成功數 | 大量提議失敗代表協定運作不正常 | 失敗比例升高告警 |
| Commit 延遲分佈、fsync 延遲 | 延遲是 leader flapping 的前兆 | p99 超過門檻告警 |
| 落後的 follower | 長期落後的成員在下次故障時幫不上忙 | 落後超過一段時間告警 |
| 儲存大小 | 接近配額時寫入會被拒絕 | 達配額一定比例告警 |

## 40.9 何時用 etcd／ZooKeeper，何時根本不需要 consensus

### 不要自己實作

共識協定的論文只有十幾頁，但正確的實作要處理成員變更、快照與 log 壓縮、磁碟損壞、時鐘異常、各種訊息重排與遺失。業界多次用 Jepsen 這類測試工具（Kyle Kingsbury 開發的分散式系統正確性測試）在成熟的資料庫與協調系統中找到違反一致性的 bug；連專門團隊都會出錯，一個產品團隊在兩個 sprint 內寫出的版本更不可能正確。

所以第一條規則是：**用現成、被廣泛驗證的系統，而且最好透過它提供的高階功能**，例如 etcd 的 lease、election 與交易 API，ZooKeeper 的 ephemeral znode（持有者 session 斷線就自動消失的節點）與 sequential znode，或雲端託管資料庫的條件寫入與交易。SRE 書引用 Chubby 的設計經驗：把共識做成一個服務而非函式庫，應用程式就不必自己處理 replica 數量、成員資格與效能調校這些難題。

| 需求 | 建議做法 |
|---|---|
| 選一個 leader 做排程或協調 | etcd／ZooKeeper／Consul 的 election 或 lease，加 fencing token |
| 少量、讀多寫少的關鍵設定 | etcd／ZooKeeper 的 key-value 與 watch |
| 業務資料的一致性（庫存、訂單、帳務） | 支援交易與條件寫入的資料庫；需要跨地區強一致時，考慮底層使用共識的分散式資料庫 |
| 大量、可合併的資料（購物車、計數） | 不需要共識：最終一致的儲存、CRDT（可自動合併的資料結構）、事後對帳 |
| 可以重新計算的資料（快取、推薦） | 不需要共識：失效時重算 |

### 協調系統不是資料庫

第二條規則是：**只把真正的 critical state 放進協調系統**。etcd、ZooKeeper 這類系統為小量、強一致的 metadata 設計：所有寫入都經過單一 leader，所有資料通常都要能放進每個節點的記憶體或有限的儲存配額。以 etcd 為例，官方文件寫明預設的單筆請求大小上限是 1.5 MiB、儲存配額預設是 2 GiB（可以用參數調整，但官方建議一般環境不要超過 8 GiB）。把大量業務資料或高頻寫入的計數器塞進去，會讓 leader 的頻寬、fsync 延遲與快照大小一起惡化，最後連真正需要它的 leader election 也變慢。Harbor 曾經有人把每次商品瀏覽的計數寫進 ZooKeeper，結果整個叢集的寫入延遲升高，連帶讓好幾個服務的 leader 頻繁更換。

### 有時候最好的共識是不需要共識

第三條規則是先問「能不能把問題改寫成不需要共識」：

- **分區 ownership**：把庫存依商品切成很多分片，每個分片由一個固定的服務實例擁有，只有「分片歸誰」需要共識，大部分寫入只是單機操作。
- **可合併的設計**：購物車用「加入」「移除」事件的集合表示，兩邊都可寫，合併時取聯集再套用。
- **單一權威來源**：如果一份資料本來就由一個高可用的資料庫管理，直接用它的交易語意，不要在應用層再做一層「誰說了算」的協調。
- **接受短暫的重複並讓它無害**：這是第 41 章的主題，用 idempotency 讓「多做一次」不會造成傷害。

## 40.10 動手寫：quorum、term 與 fencing token

下面的程式用三段模擬串起本章的核心：quorum 交集、簡化版 Raft 在網路分割下的行為，以及 fencing token 擋下醒來的舊 leader。它刻意省略了很多細節（例如 follower 的 log 一致性檢查與逐格回退），只保留決定 safety 的部分。程式中的節點數、分割方式、token 33／34（沿用 Martin Kleppmann 文章中的示意數字）、lease 10 秒與 GC 停頓 15 秒都是假設的示意參數，不代表任何真實系統的預設值。

```python
from itertools import combinations


# ── Part 1：quorum 大小與容錯 ─────────────────────────────
def majority(n: int) -> int:
    return n // 2 + 1


print("節點數  quorum  可容忍故障")
for n in range(3, 8):
    print(f"{n:>4}  {majority(n):>6}  {n - majority(n):>8}")

nodes = "ABCDE"
quorums = [set(q) for q in combinations(nodes, majority(5))]
ok = all(a & b for a, b in combinations(quorums, 2))
print(f"5 節點共有 {len(quorums)} 種 quorum，任兩個都有交集：{ok}\n")


# ── Part 2：簡化版 Raft：term、投票、只有 quorum 才能 commit ──
class Node:
    def __init__(self, name):
        self.name = name
        self.term = 0
        self.voted_for = None
        self.log = []              # [(term, command)]
        self.commit_index = 0      # 前幾筆已經 commit
        self.role = "follower"

    def last(self):
        return (self.log[-1][0], len(self.log)) if self.log else (0, 0)


class Cluster:
    def __init__(self, names):
        self.nodes = {n: Node(n) for n in names}
        self.links = {frozenset((a, b)) for a, b in combinations(names, 2)}

    def partition(self, *groups):
        self.links = {frozenset((a, b)) for g in groups for a, b in combinations(g, 2)}

    def heal(self):
        names = list(self.nodes)
        self.links = {frozenset((a, b)) for a, b in combinations(names, 2)}

    def reachable(self, a, b):
        return a == b or frozenset((a, b)) in self.links

    def elect(self, cand_name):
        cand = self.nodes[cand_name]
        cand.term += 1
        cand.role, cand.voted_for = "candidate", cand_name
        votes = [cand_name]
        for peer in self.nodes.values():
            if peer is cand or not self.reachable(cand_name, peer.name):
                continue
            if cand.term > peer.term:                 # 看到更大的 term：更新並退回 follower
                peer.term, peer.voted_for, peer.role = cand.term, None, "follower"
            up_to_date = cand.last() >= peer.last()   # 候選者的 log 至少一樣新
            if peer.voted_for is None and up_to_date:
                peer.voted_for = cand_name
                votes.append(peer.name)
        won = len(votes) >= majority(len(self.nodes))
        cand.role = "leader" if won else "follower"
        print(f"[選舉] {cand_name} 以 term {cand.term} 參選，得票 {votes} → {'當選' if won else '落選'}")
        return won

    def write(self, leader_name, command):
        leader = self.nodes[leader_name]
        peers = [p for p in self.nodes.values()
                 if p is not leader and self.reachable(leader_name, p.name)]
        newer = max((p.term for p in peers), default=0)
        if newer > leader.term:                       # 遇到更新的世代：舊 leader 下台
            leader.role, leader.term = "follower", newer
            print(f"[寫入] {leader_name} 想寫 {command!r}，但發現 term {newer} > 自己，退回 follower")
            return False
        leader.log.append((leader.term, command))
        acks = [leader_name]
        for peer in peers:                            # 簡化：follower 直接複製 leader 的 log
            peer.term, peer.log = leader.term, list(leader.log)
            acks.append(peer.name)
        committed = len(acks) >= majority(len(self.nodes))
        if committed:
            for name in acks:
                self.nodes[name].commit_index = len(leader.log)
        print(f"[寫入] {leader_name}(term {leader.term}) 寫 {command!r}，ack={acks} → "
              f"{'COMMIT' if committed else '未達 quorum，不能 commit'}")
        return committed

    def sync_from(self, leader_name):
        leader = self.nodes[leader_name]
        for peer in self.nodes.values():
            if self.reachable(leader_name, peer.name) and peer is not leader:
                peer.log, peer.term, peer.role = list(leader.log), leader.term, "follower"
                peer.commit_index = leader.commit_index

    def show(self):
        for n in self.nodes.values():
            cmds = [c for _, c in n.log]
            print(f"   {n.name}: term={n.term} {n.role:<9} log={cmds} commit={n.commit_index}")


c = Cluster("ABCDE")
c.elect("A")
c.write("A", "stock=100")
c.sync_from("A")

print("\n--- 網路分割：{A,B} | {C,D,E} ---")
c.partition("AB", "CDE")
c.write("A", "stock=99")          # 舊 leader 在少數側
c.elect("C")                      # 多數側選出新 leader
c.write("C", "stock=97")
c.show()

print("\n--- 網路恢復 ---")
c.heal()
c.write("A", "stock=98")          # 舊 leader 嘗試再寫
c.sync_from("C")
c.show()


# ── Part 3：lease 過期後醒來的舊 leader 與 fencing token ──
class Storage:
    def __init__(self):
        self.max_token = 0
        self.value = None

    def write(self, token, value, who):
        if token < self.max_token:
            print(f"[儲存] 拒絕 {who} 的寫入：token {token} < 已見過的 {self.max_token}")
            return False
        self.max_token, self.value = token, value
        print(f"[儲存] 接受 {who} 的寫入（token {token}）：{value}")
        return True


print()
store = Storage()
token_a = 33                       # A 取得 lease，lock service 給它 token 33
print("A 取得 lease（token 33），接著 GC 停頓 15 秒，lease 已過期")
token_c = 34                       # lease 過期，C 取得新 lease
store.write(token_c, "stock=97", "C")
store.write(token_a, "stock=99", "A（剛醒來）")
print(f"最後的值：{store.value}")
```

執行結果：

```text
節點數  quorum  可容忍故障
   3       2         1
   4       3         1
   5       3         2
   6       4         2
   7       4         3
5 節點共有 10 種 quorum，任兩個都有交集：True

[選舉] A 以 term 1 參選，得票 ['A', 'B', 'C', 'D', 'E'] → 當選
[寫入] A(term 1) 寫 'stock=100'，ack=['A', 'B', 'C', 'D', 'E'] → COMMIT

--- 網路分割：{A,B} | {C,D,E} ---
[寫入] A(term 1) 寫 'stock=99'，ack=['A', 'B'] → 未達 quorum，不能 commit
[選舉] C 以 term 2 參選，得票 ['C', 'D', 'E'] → 當選
[寫入] C(term 2) 寫 'stock=97'，ack=['C', 'D', 'E'] → COMMIT
   A: term=1 leader    log=['stock=100', 'stock=99'] commit=1
   B: term=1 follower  log=['stock=100', 'stock=99'] commit=1
   C: term=2 leader    log=['stock=100', 'stock=97'] commit=2
   D: term=2 follower  log=['stock=100', 'stock=97'] commit=2
   E: term=2 follower  log=['stock=100', 'stock=97'] commit=2

--- 網路恢復 ---
[寫入] A 想寫 'stock=98'，但發現 term 2 > 自己，退回 follower
   A: term=2 follower  log=['stock=100', 'stock=97'] commit=2
   B: term=2 follower  log=['stock=100', 'stock=97'] commit=2
   C: term=2 leader    log=['stock=100', 'stock=97'] commit=2
   D: term=2 follower  log=['stock=100', 'stock=97'] commit=2
   E: term=2 follower  log=['stock=100', 'stock=97'] commit=2

A 取得 lease（token 33），接著 GC 停頓 15 秒，lease 已過期
[儲存] 接受 C 的寫入（token 34）：stock=97
[儲存] 拒絕 A（剛醒來） 的寫入：token 33 < 已見過的 34
最後的值：stock=97
```

逐段解讀：

1. **Part 1** 印出 2f+1 的表，並窮舉 5 個節點所有 10 種 3 人組合，確認任兩組都有交集。你可以把 `majority(5)` 換成 2，會看到交集檢查變成 `False`：少於多數的「quorum」允許兩個互不相識的群組各自做決定，這正是 Harbor watchdog 的問題。
2. **Part 2 分割期間**的輸出最值得細看：A 和 C 的 `role` 同時都是 `leader`。這不是 bug，而是真實系統也會出現的情況。差別在於 A 的 `commit=1`，它寫的 `stock=99` 永遠停在未 commit 狀態，不能回覆 client 成功；C 的寫入才是真正生效的。
3. **網路恢復後**，A 一接觸到 term 2 的節點就退回 follower，A、B 未 commit 的 `stock=99` 被 leader C 的版本覆蓋。真實的 Raft 用 AppendEntries 的「前一格 term 與位置」檢查逐格找出分岔點，程式用 `sync_from` 一次覆蓋代替。
4. **Part 3** 示範 Part 2 保護不到的地方：當舊 leader 不是寫 log，而是直接寫外部資源時，term 規則管不到它，只有資源端的 fencing 檢查能擋下。真實系統中，`Storage.write` 對應的就是 40.7 節那條帶 `fence <= :token` 條件的 SQL。

程式省略了持久化、選舉 timeout、heartbeat、log 一致性檢查與成員變更。這些正是實作共識最難、也最容易出 bug 的部分，也是本章一再建議使用現成系統的原因。

## 40.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| Heartbeat + timeout 自動 failover | 網路慢或掉封包時誤判，產生兩個 primary | Harbor 週年慶保溫瓶超賣 231 組（賣出 731、限量 500） | 用共識系統做選舉，資源端加 fencing |
| 只靠 lease，沒有 fencing | Process 停頓超過 lease 後醒來繼續寫 | GC 停頓 15 秒的配額分配器覆蓋新 leader 的結果 | 每次外部寫入帶 token，資源拒絕舊 token |
| 把共識系統當一般資料庫 | Leader 頻寬、fsync 與快照惡化，選舉變慢 | 瀏覽計數寫進 ZooKeeper，連帶多個服務 leader flapping | 只放 critical metadata；業務資料放資料庫 |
| 為了「更可靠」部署偶數或過多 replica | 容錯沒增加，寫入變慢，單一機房失效時失去餘裕 | 第 6 個 replica 放在已有一個 replica 的機房 | 奇數、每個 failure domain 一個，依需要選 3 或 5 |
| 跨地區部署共識叢集卻沒有對應需求 | 每次寫入多付數十毫秒，換不到可用性 | Client 全在台灣，etcd 卻橫跨三國 | 依 client 位置與要承受的故障範圍決定 |
| 共識系統放在共享慢速磁碟 | Fsync 延遲讓 heartbeat 遲到，leader 不停更換 | 和 log 收集程式共用一顆雲端磁碟 | 專用低延遲磁碟，監控 fsync 與 leader 變更次數 |
| 失去 quorum 時臨場強制恢復 | 已 commit 的資料可能遺失，且決策沒有依據 | 兩個 zone 同時維護，剩一個成員被強制設成單節點叢集 | 事先寫 runbook，規定誰能決定、需要哪些證據；維護時避免同時動多個成員 |

## 40.12 AI 時代：什麼變了？

**第一，「多個 agent 投票」不是 consensus。** 有些團隊讓幾個 AI agent 各自分析，再取多數意見做決定。這可以提高判斷品質，但它和本章的共識是兩回事：模型的回答沒有持久化的 log、沒有 term、沒有「已 commit 就不會改變」的保證，同樣的輸入下次可能得到不同的多數。凡是「誰是 primary」「這把鎖在誰手上」「這份設定是否生效」這種問題，答案必須來自確定性的協定，AI 的輸出只能當作建議。

**第二，AI agent 本身成了需要被 fencing 的 actor。** Harbor 的 AI 維運 agent 可以重啟服務、調整設定。如果同時有兩個 agent 實例（例如一個卡住、平台又啟動了一個新的），它們就和兩個 leader 一樣可能做出衝突的動作。實務做法：

- Agent 執行有副作用的操作前，必須透過 etcd 這類系統取得 lease，並把 fencing token 帶到每個 mutating API。
- Agent 只能透過高階工具（「申請維護 lease」「提出設定變更」）操作，而不是直接寫入協調系統的 key。
- Agent 的 lease 比人類操作的 lease 短，續約失敗就立刻中止並回報，不做「做完這一步再說」。

**第三，AI 很適合讀懂共識系統的遙測，但不適合決定強制恢復。** 共識系統的故障常常需要對照多個節點的 log、term 變化、fsync 延遲與網路指標，這正是 AI 擅長整理的資料。但失去 quorum 時是否強制重組成員，可能導致資料遺失，必須由人決定。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 彙整各成員的 term、commit 位置、fsync 延遲，產生「leader 為什麼一直換」的時間線，並附上原始查詢 | 結論要能用指標與 log 驗證；AI 的時間線只是調查起點 |
| 審查程式碼中自製的 leader election 或分散式鎖，標出「靠 timeout 決定唯一性」「外部寫入沒帶 token」的地方 | 是否改用現成協調系統、以及 fencing 的設計，由服務 owner 與 SRE 決定 |
| 產生故障注入情境：分割、單向丟包、process 暫停、磁碟變慢、時鐘跳躍 | 在 production 執行故障注入需要事先核准的範圍與中止條件（第 46 章） |
| 依 runbook 草擬失去 quorum 時的處理選項，並列出各選項可能遺失的資料範圍 | 強制成員變更、從快照恢復一律由人類核准，且需要兩人確認 |
| 代替人類取得維護 lease、執行例行的成員替換 | Agent 使用獨立身分、最小權限（只能操作指定 key prefix），所有動作帶 fencing token 並留審計紀錄 |

> [!ai] AI 提醒
> 請 coding agent「幫我寫一個分散式鎖」時，它很可能產出看起來合理、在測試中也能通過的 `SET key NX EX 10` 加續約邏輯。這段程式在一般情況下運作正常，只在 process 停頓或網路分割時出錯，而單元測試幾乎不會涵蓋這些情況。正確的 prompt 應該要求它使用既有的協調系統、說明 fencing token 從哪裡來、以及資源端如何拒絕舊 token。

## 40.13 專家怎麼想

- **「兩台機器同時以為自己對，會怎樣？」** 這是專家判斷一份狀態是否 critical 的第一個問題。答案若是「之後會對齊」，就不要為它付共識的代價；答案若是「錢會算錯」，就不要用任何比共識更弱的方法。
- **看到 timeout 決定唯一性，就當成 bug。** Timeout 可以觸發選舉、可以觸發重試，但不能單獨決定「現在只有我能做這件事」。資深工程師 review 程式時會特別找這種模式。
- **Fencing 要做到資源那一側。** 只要檢查發生在 actor 自己身上，檢查和動作之間就有縫隙。能在資源端檢查的，絕不在 client 端檢查。
- **共識系統是基礎設施的基礎設施，依賴越少越好。** 它壞了，所有靠它選 leader 的服務都會受影響。所以它要有專用磁碟、獨立的監控、保守的升級節奏，而且不能反過來依賴它所支撐的服務。
- **部署位置跟著 client 走。** 不是越分散越好，而是「讓它和依賴它的服務一起存活就夠」，再用快照備份處理更大的災難。
- **先試著把問題改寫成不需要共識。** 分區 ownership、可合併的資料結構、idempotent 操作，常常比引入一個新的協調系統更簡單、更可靠。

## 40.14 動手練習

1. 列出你熟悉的系統（或 Harbor）中的 8 份狀態，用「兩台機器同時以為自己對會怎樣」判斷哪些是 critical state，並為每一份 critical state 寫下現在是用什麼機制保護的。
2. 修改 40.10 的 Part 2：改成 7 個節點，分割成 {A, B, C} 與 {D, E, F, G}，讓 A 在分割前是 leader。觀察哪一側能 commit。再試試三方分割 {A, B} | {C, D} | {E, F, G}，說明為什麼沒有任何一側能選出 leader。
3. 延伸 40.10 的 Part 3：加入一個「不檢查 token」的資源，重跑同一個情境，觀察最後的值，並說明在 Harbor 的哪些外部系統（金流、物流、通知）上可能遇到這個問題、各自要怎麼補救。
4. 畫出 Harbor inventory 修正後的架構：三個 etcd 成員、資料庫 primary 與 replica、連線代理。標出 zone A 與其他兩個 zone 分割時，每個元件的行為與使用者看到的結果。
5. 為 Harbor 的 etcd 叢集寫一份一頁的 runbook：「只剩一個成員健康」時，值班者要收集哪些資訊、可以選擇哪些行動、各行動可能遺失什麼資料、誰有權核准。
6. 請 AI coding agent 實作一個「確保同時只有一個 worker 執行」的機制，然後逐條檢查它的程式：唯一性是否靠 timeout 決定？有沒有 fencing token？process 在檢查後停頓會怎樣？把你找到的問題整理成 code review 意見。

## 本章重點整理

- Critical state 是「不同機器看法不一致就會造成難以修復錯誤」的狀態，通常很小：leader 身分、鎖、關鍵設定、少數計數器。
- 分散式系統沒有共同的現在、分不出慢與死、故障是局部的，所以 heartbeat 加 timeout 無法正確決定「誰是唯一的 leader」。
- 共識協定把 safety（永遠不給錯答案）與 liveness（網路夠好時會有進展）分開保證；網路很糟時寧可停下來。
- CAP 的正確讀法是「網路分割時，在一致性與可用性之間選一個」；PACELC 補上平常狀態下延遲與一致性的取捨。同一個產品的不同功能可以有不同選擇。
- 共識把操作排成一份 replicated log，各副本依同樣順序執行，形成 replicated state machine；etcd、ZooKeeper、Consul 都建立在這個模型上。
- 任意兩個 majority 必有交集，這是共識 safety 的基礎；2f+1 個節點可容忍 f 個故障，偶數節點不增加容錯。
- 關鍵的共識系統常用 5 個 replica，讓維護一台時仍能承受一台意外故障；失去 quorum 時的強制恢復可能遺失資料，必須事先寫好流程。
- Raft 用 term 區分世代、用隨機 timeout 觸發選舉、用多數投票決定 leader、用多數 ack 決定 commit；短暫出現兩個自認的 leader 是可能的，但舊 leader 無法 commit。
- Lease 讓權力自動過期，但依賴時間；process 停頓可能讓舊持有者在 lease 過期後繼續動作。
- Fencing token 是共識系統發出的單調遞增數字，由資源端檢查並拒絕舊 token，是擋住「醒來的舊 leader」唯一可靠的方式。
- 一次 commit 至少要付網路往返與 fsync；batching 與 pipelining 提高吞吐，讀取可依需求選擇 linearizable 或允許舊值的方式。
- Replica 位置在故障範圍與延遲之間取捨；如果 client 都在同一地區，跨地區部署共識系統只會多付延遲。
- 不要自己實作共識，使用 etcd、ZooKeeper、Consul 或資料庫的交易與條件寫入，並且只放真正的 critical state。
- AI agent 的多數意見不是共識；有副作用的 agent 本身也需要 lease、fencing token 與最小權限，強制恢復這類可能遺失資料的決定必須由人類核准。

## 延伸問答

> [!question]- Q1. 為什麼把 watchdog 的 timeout 從 6 秒調到 30 秒，不能解決 Harbor 的 split-brain？
> Timeout 只能回答「我多久沒收到回應」，不能回答「對方是不是真的死了」。網路變慢、單向掉包、對方 process 停頓，都會讓任何長度的 timeout 在某些情況下誤判。把 timeout 調長，只是讓誤判變少一點，代價是真正當機時要等更久才 failover，可用性變差。
>
> 更根本的問題是決策者只有一個節點的視角。zone B 的 watchdog 看不到 zone A 的應用伺服器仍然連得上舊 primary。正確做法是讓決策由 quorum 做出（例如三個 zone 的 etcd 成員投票），並且讓資源端用 fencing token 拒絕舊 primary 的寫入。這樣即使誤判發生，也只會造成一次多餘的切換，而不會出現兩個同時有效的 primary。

> [!question]- Q2. 計算題：一個共識叢集有 5 個節點，分佈在三個 zone，配置是 2-2-1。任一 zone 失效時，系統還能寫入嗎？如果改成 3 個節點、每個 zone 1 個呢？
> 5 個節點的 quorum 是 3。配置 2-2-1 時，失去有 2 個節點的 zone，剩 3 個，剛好等於 quorum，仍能寫入，但已經沒有任何餘裕，此時再壞一台就停；失去只有 1 個節點的 zone，剩 4 個，還能再承受一台故障。所以任一 zone 失效都能繼續寫入。
>
> 3 個節點、每個 zone 1 個時，quorum 是 2，任一 zone 失效剩 2 個，也能寫入，同樣沒有餘裕。兩者都能扛單一 zone 失效，差別在「zone 失效期間再壞一台」或「維護時同時發生故障」：5 節點在失去小 zone 時仍有一台餘裕，3 節點則完全沒有。如果你只有三個 zone，5 節點的 2-2-1 比 3 節點多了一些韌性，代價是更多機器、更多網路流量，以及 leader 要多等一個 follower 的 ack。

> [!question]- Q3. 「我們用 Redis 的 SET key NX EX 10 做分散式鎖，運作一年都沒問題。」你會怎麼回應？
> 一年沒出問題，通常代表還沒遇到觸發條件，而不是機制正確。這種鎖有幾個典型漏洞：持有者在取得鎖後停頓（GC、CPU 限制、VM 暫停）超過 10 秒，鎖過期被別人拿走，原持有者醒來後仍以為自己有鎖；若 Redis 本身是非同步複製的主從架構，主節點在把鎖複製出去之前當機，新的主節點上沒有這把鎖，另一個 client 就能再拿一次。
>
> 是否需要改，要看鎖保護的是什麼。如果只是避免重複做一件可重做的工作（例如重建快取），偶爾兩個人同時做只是浪費，現有做法可以接受。如果保護的是 critical state（扣款、庫存、撥款），就應該改用共識系統的 lease，並讓資源端檢查 fencing token；或者把操作設計成 idempotent，讓「兩個人同時做」不會造成傷害。回應時要具體指出失敗情境，而不是只說「這樣不安全」。

> [!question]- Q4. Raft 叢集在網路分割時，可能同時存在兩個 leader 嗎？這會不會破壞一致性？
> 可能同時存在兩個「自認為」的 leader。分割前的 leader 在少數側，它沒收到任何更大 term 的訊息，所以仍然以為自己是 leader；多數側則在 election timeout 後選出 term 更大的新 leader。本章的模擬程式就展示了這個狀況。
>
> 但這不會破壞 log 的一致性，因為舊 leader 只能聯絡到少數節點，任何寫入都湊不到多數 ack，因此無法 commit，也不能回覆 client 成功。分割恢復後，它看到更大的 term 就退回 follower，未 commit 的內容被覆蓋。真正的風險在協定之外：如果舊 leader 除了寫 log，還直接操作外部系統（寄信、呼叫金流），協定就管不到了。這就是為什麼 leader 要在失去 lease 時立即停手，且外部操作要帶 fencing token。

> [!question]- Q5. 你是 Harbor 的值班者，收到告警「etcd leader 在 10 分鐘內換了 14 次」。你會怎麼調查？
> 頻繁換 leader 通常不是共識協定本身的問題，而是 heartbeat 送不到或來不及處理。調查順序可以是：先看各成員的 fsync 延遲與磁碟 I/O，因為慢速磁碟是最常見的原因；再看成員之間的網路延遲與掉包，特別是跨 zone 的鏈路；接著看 leader 所在機器的 CPU 是否被其他工作搶走、process 是否有長時間停頓；最後確認最近有沒有變更，例如 etcd 版本升級、調整了 heartbeat 或 election timeout 參數、或有新的大量寫入者。
>
> 同時要評估影響：依賴 etcd 的服務是否也在頻繁換 leader 或寫入失敗。止血的選項包括把產生大量寫入的 client 暫停、把成員搬到較不擁擠的機器或磁碟。調查時要記錄每一次 term 變化的時間點，並和磁碟、網路指標對照，這比直接猜測原因有效得多。

> [!question]- Q6. 為什麼說「如果所有 client 都在同一地區，就不必把共識叢集部署到多個地區」？這個推理什麼時候不成立？
> 共識叢集的可用性只有在有 client 使用時才有價值。如果所有使用它的服務都在台灣的一個地區，那麼整個地區失效時，這些服務本身也停了，沒有人會來寫入；此時讓共識叢集在日本繼續運作，換不到任何使用者看得到的可用性。反過來，跨地區部署要讓每一次寫入多付數十毫秒的往返延遲，這是每天都在付的成本。
>
> 這個推理在幾種情況下不成立：一是 client 本身就是多地區部署，例如服務在台灣與日本都有實例、需要共享同一份 leader 資訊；二是共識叢集保存的是不能遺失的資料，即使暫時沒有 client，也需要在另一地區保有最新副本（不過這通常可以用定期快照備份到其他地區來達成，代價小很多）；三是法規或業務要求某些狀態必須在地區失效後立即可用。判斷時要先問「這個系統要扛的是哪一層級的故障，而它的使用者是否也扛得住」。

> [!question]- Q7. 一位同事提議：「讓三個 AI agent 各自判斷要不要 failover，兩個以上同意就執行，這樣就是 quorum 了。」這個設計有什麼問題？
> 這個設計借用了 quorum 的形式，卻沒有它的保證。共識協定的 quorum 之所以有效，是因為每個節點的投票有持久化的紀錄、有 term 區分世代、一旦投了就不會在同一個 term 改投，兩個 majority 的交集保證新決策一定看得到舊決策。三個 agent 的判斷則是各自獨立地讀取（可能不同時間點的）監控資料，沒有世代編號，下一分鐘可能又投出相反的結果；更重要的是，它們可能看到的是同一個錯誤的資料來源，三票同意並不代表三個獨立的證據。
>
> 比較好的分工是：failover 的決定與執行交給共識系統的 leader election 與 fencing，那是確定性、可證明的機制；AI agent 負責在旁邊觀察與解釋，例如整理各 zone 的網路與磁碟指標、判斷是不是需要人類介入，或者在失去 quorum 這種需要人類決策的情況下，準備好各選項的資料讓值班者判斷。

> [!question]- Q8. 面試題：設計一個「同一時間只能有一個 instance 執行」的排程服務，你會怎麼做？
> 先釐清需求：這個工作重複執行的後果是什麼、漏掉一次的後果是什麼、可以容忍多久沒有 leader。接著提出架構：排程服務跑 3 個 instance，透過 etcd 或 ZooKeeper 的 lease 做 leader election；只有持有 lease 的 instance 執行工作，lease 期限遠大於一次續約所需的時間，續約失敗就立即中止工作。
>
> 關鍵是說出 lease 的弱點與補救：process 可能在檢查 lease 後停頓，所以每次對外部資源的寫入都帶上 fencing token（例如 etcd 的 revision），由資源端拒絕舊 token；對於無法檢查 token 的外部系統，把操作設計成 idempotent，或在操作前後記錄狀態以便恢復時判斷是否已執行。最後補充監控：leader 是否存在、換 leader 的頻率、工作是否按時完成。能講到 fencing 與 idempotency，代表你理解「選出唯一 leader」和「保證只有一個人在動作」是兩件不同的事，這通常是面試官想聽到的重點。第 41 章會把這個設計完整展開。

## 延伸閱讀

- [Site Reliability Engineering — Managing Critical State: Distributed Consensus for Reliability](https://sre.google/sre-book/managing-critical-state/)：本章的主要來源，包含 split-brain 案例、共識系統的架構模式、效能分析、replica 數量與位置的取捨，以及監控清單。
- [Site Reliability Engineering — Distributed Periodic Scheduling with Cron](https://sre.google/sre-book/distributed-periodic-scheduling/)：Google 如何用 Paxos 建立分散式 cron，是 leader election 與「失去領導權要立刻停手」的具體應用，也是第 41 章的主要來源。
- [The Raft Consensus Algorithm](https://raft.github.io/)：Raft 官方網站，有論文、互動式視覺化（RaftScope）與各語言實作清單，適合搭配 40.6 節觀察選舉與 log 複製。
- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：共識叢集的讀取過載與 leader 集中失效，都可能演變成第 39 章討論的連鎖故障。
