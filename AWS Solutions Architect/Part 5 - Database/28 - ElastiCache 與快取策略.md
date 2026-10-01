---
chapter: 28
title: ElastiCache 與快取策略
part: 5
---

# 第 28 章　ElastiCache 與快取策略：Cache-aside、TTL、Valkey／Redis OSS、Memcached 與 MemoryDB

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚快取為什麼能讓系統變快、變便宜，以及它在什麼情況下會讓系統出錯
> - 實作 cache-aside 與 write-through，選擇合理的 TTL 與失效（invalidation）方式
> - 辨認 cache stampede、cache penetration、hot key 與 eviction 這四種常見故障，並說出對應的解法
> - 在 Valkey／Redis OSS、Memcached、ElastiCache Serverless、MemoryDB、DAX、CloudFront 之間做正確選型
> - 設計一個跨 AZ、可自動 failover、加密且可監控的 ElastiCache 叢集
>
> **前置知識**：第 4 章（cache、consistency、replication 的基本觀念）、第 26 章（RDS／Aurora）、第 27 章（DynamoDB）
> **考試比重**：SAA ★★★（Domain 2 高可用、Domain 3 資料庫效能、Domain 4 資料庫成本）｜SAP ★★☆（Domain 2 效能目標、Domain 3 改善既有系統）

## 28.1 故事：促銷夜，資料庫先倒下

Wanderly 進入成長期後，每季會辦一次「午夜限時優惠」。去年冬季的促銷在晚上 12 點整開跑，三分鐘內湧入平常 40 倍的使用者。Web tier 有 Auto Scaling（第 18 章），EC2 很快從 6 台擴到 60 台；但所有新機器做的第一件事，都是對同一個 Aurora MySQL 執行同一組查詢：「東京、大阪、沖繩三個熱門城市，今晚有空房的旅館與最低價」。

Aurora 的 writer CPU 在 40 秒內衝到 100%。查詢從平常的 30 毫秒變成 8 秒，應用程式的連線池被占滿，連帶付款、登入這些和促銷無關的功能也開始逾時。工程師小林緊急加了兩個 Aurora Replica，但新的 replica 啟動需要幾分鐘，等它們上線時，促銷的黃金十分鐘已經過去了。

事後檢討時，資料庫團隊的阿哲指出一個關鍵事實：那十分鐘內，資料庫執行了超過 200 萬次查詢，但**真正不同的查詢結果只有大約 3,000 種**，而且旅館列表每分鐘才變動幾次。換句話說，資料庫花了 99% 以上的力氣，在重複計算一模一樣的答案。

技術主管給小林的新任務是：在資料庫前面加一層快取，讓重複的讀取不再打到 Aurora；但快取不能讓使用者看到「明明已經賣完卻顯示有房」的錯誤資料太久，快取本身掛掉時網站也不能跟著掛。這一章就從「快取到底是什麼」開始，一路講到 AWS 上的 ElastiCache、MemoryDB、DAX，以及怎麼把它們組成一個不會在下一次促銷倒下的架構。

## 28.2 快取是什麼：用一份可以丟掉的副本換時間

**快取（cache）** 是把「取得成本高的資料」暫存在「取得成本低的地方」的一份副本。成本高可能是因為要做複雜的 SQL join、要跨網路呼叫外部 API、要從磁碟讀；成本低的地方通常是記憶體，而且離使用者或應用程式更近。

為什麼記憶體比較快？資料庫即使把熱資料放在自己的 buffer pool 裡，每次查詢仍然要解析 SQL、規劃執行計畫、取得鎖、組合結果。快取則只做一件事：「給我 key 對應的 value」。一次 in-memory key-value 讀取通常在 1 毫秒以內（sub-millisecond），而且一個節點每秒可以處理數十萬次這種操作。

### 幾個一定要懂的詞

- **Cache hit（命中）**：要的資料在快取裡，直接回傳。
- **Cache miss（未命中）**：快取裡沒有，必須回到原始資料來源去拿。
- **Hit ratio（命中率）**：hit ÷（hit + miss）。命中率 95% 代表只有 5% 的請求會打到資料庫，資料庫負載降為原本的 1/20。
- **Source of truth（真相來源）**：資料「正式」保存的地方，例如 Aurora 或 DynamoDB。快取裡的資料只是它的副本。
- **Stale data（過期資料）**：快取裡的副本已經和真相來源不一致。

命中率對資料庫負載的影響是非線性的：命中率從 90% 提高到 99%，看起來只差 9 個百分點，但打到資料庫的請求從 10% 降到 1%，負載降為原本的十分之一。這也是為什麼快取調校常常比幫資料庫升級規格更有效。

### 快取的第一條鐵律：它不是 source of truth

快取的價值來自「可以丟」：它可以因為記憶體不足而丟掉資料、可以重新開機、可以整個清空，系統仍然要能從真相來源重建出正確答案。只要你開始依賴「這筆資料只在快取裡」，快取就不再是快取，而是一個沒有完整耐久性保證的資料庫。

> [!warning] 常見誤解
> 「ElastiCache 有 replica、有 snapshot，所以可以把訂單先寫進去，之後再慢慢寫回資料庫。」ElastiCache 的複寫是**非同步**的，snapshot 是**定時**的；primary 故障時，最後幾筆尚未複寫的寫入可能遺失，兩次 snapshot 之間的資料也可能遺失。不可遺失的業務資料要寫進有耐久性保證的資料庫；如果真的需要「記憶體速度＋耐久性」，選的是 28.11 節的 MemoryDB，而不是把 ElastiCache 當資料庫用。

### 快取可以放在哪一層？

一個請求從使用者到資料庫，沿路有很多地方可以放快取：

| 層級 | 例子 | 快取的東西 | 本書章節 |
|---|---|---|---|
| 瀏覽器／App | HTTP `Cache-Control` 標頭 | 靜態檔案、API 回應 | 第 11 章 |
| 邊緣（edge） | CloudFront | HTTP 回應（圖片、HTML、可共用的 API 回應） | 第 11 章 |
| API 層 | API Gateway REST API caching | 依 request 參數快取 API 回應 | 第 20 章 |
| 應用程式記憶體 | 程式內的 local cache（例如 LRU map） | 極熱、極少變動的設定或字典資料 | 本章 |
| 分散式快取 | ElastiCache（Valkey、Redis OSS、Memcached） | 查詢結果、物件、session、計數器 | 本章 |
| 資料庫專用加速 | DynamoDB Accelerator（DAX） | DynamoDB 的 item 與 query 結果 | 本章、第 27 章 |
| 資料庫內部 | Aurora buffer pool | 資料頁 | 第 26 章 |

越靠近使用者的快取，省下的路程越多，但能控制的範圍越小（CloudFront 看不到你的資料庫結構）；越靠近資料庫的快取，越能精準快取「某一筆資料」，但每個請求仍然要走到應用程式。本章的主角是中間那層「分散式快取」，最後在 28.12 節把各層組起來。

## 28.3 讀取策略：Cache-aside 與 Read-through

有了快取，第一個要決定的是：**誰負責在 miss 時去資料庫拿資料、再放進快取？**

### Cache-aside（lazy loading，延遲載入）

**Cache-aside** 是最常見、也是考試最常出現的模式：應用程式自己管理快取。讀取流程如下：

```text
[應用程式]
   │ ① GET hotel:search:tokyo:2025-12-24
   ▼
[ElastiCache]
   ├─ ② 命中 → 直接回傳結果（< 1 ms）
   │
   └─ ③ 未命中（nil）
         │
         ▼
[應用程式] ── ④ 執行 SQL 查詢 ──► [Aurora]（真相來源）
   │                                    │
   │ ◄──────── ⑤ 查詢結果 ──────────────┘
   │
   │ ⑥ SET hotel:search:tokyo:2025-12-24 <結果> EX 60
   ▼
[ElastiCache]
   │
   ⑦ 回傳結果給使用者
```

① 應用程式依請求內容組出一個 **cache key**（快取鍵），先查快取。② 命中就直接回傳，資料庫完全不知道這個請求存在。③ 未命中時，快取回傳空值。④⑤ 應用程式自己去資料庫查。⑥ 把結果寫進快取，並設定 **TTL（Time To Live，存活時間）**，這裡是 60 秒，60 秒後這筆資料自動過期。⑦ 回傳給使用者。下一個相同請求在 60 秒內都會命中。

Cache-aside 的特性：

- **只快取真的被讀過的資料**，記憶體不會浪費在沒人要的資料上。這就是「lazy」的意思。
- **快取故障不會讓系統錯誤，只會讓系統變慢**：快取連不上時，應用程式可以直接查資料庫（當然要確保資料庫撐得住，見 28.5 節）。
- **第一次讀取一定 miss**：新節點上線、快取被清空後，會有一段「冷啟動」期間命中率很低。
- **資料可能過期**：資料庫被更新後，快取裡的舊值要等 TTL 到期或被主動刪除才會消失。

用 Python 實作大致如下（`redis-py` 這個 client 也能連 Valkey）：

```python
import json
import random
import redis

cache = redis.Redis(host="wanderly-cache.xxxxxx.apne1.cache.amazonaws.com",
                    port=6379, ssl=True, decode_responses=True)

def search_hotels(city: str, date: str) -> list[dict]:
    key = f"hotel:search:{city}:{date}"
    cached = cache.get(key)
    if cached is not None:                 # cache hit
        return json.loads(cached)

    rows = query_aurora(city, date)        # cache miss：回到真相來源
    ttl = 60 + random.randint(0, 15)       # TTL 加上隨機抖動，見 28.5 節
    cache.set(key, json.dumps(rows), ex=ttl)
    return rows
```

注意 TTL 不是固定的 60 秒，而是 60～75 秒之間的隨機值，這個細節在 28.5 節會救小林一命。

### Read-through

**Read-through** 的流程和 cache-aside 一樣，差別在於「miss 時去資料庫拿資料」的工作由**快取層自己**完成，應用程式只跟快取說話。DynamoDB Accelerator（DAX）就是典型的 read-through 快取：應用程式把 DynamoDB 的 `GetItem` 送給 DAX，DAX 沒有時自己去 DynamoDB 拿。ElastiCache 本身不會主動連你的資料庫，所以在 ElastiCache 上只能做 cache-aside，或由你自己的程式庫包裝成 read-through 的樣子。

### Cache key 的設計

Cache key 必須**完整描述「什麼會讓結果不同」**。旅館搜尋結果會隨城市、日期、人數、語言、幣別而不同，key 漏掉幣別，日本使用者就可能看到台幣價格。反過來，把不影響結果的東西（例如 request ID、時間戳）放進 key，每個請求都變成不同的 key，命中率趨近於零。

常見的命名習慣是用冒號分層：`<物件類型>:<用途>:<參數...>`，例如 `hotel:detail:1234`、`user:session:ab12cd`。這樣在除錯與統計時一眼就能看出 key 的用途，也方便用前綴做批次失效。

## 28.4 寫入策略與資料新鮮度：TTL、Invalidation、Write-through

Cache-aside 解決了「讀」，但資料一定會被修改：旅館調價、房間賣完、會員改名。快取裡的舊值要怎麼處理？這是快取設計裡最難的部分，有一句流傳很廣的話說，電腦科學只有兩件難事：快取失效與命名。

### 方法一：只靠 TTL

最簡單的做法是什麼都不做，讓 TTL 到期後自然失效。這等於對使用者承諾：「你看到的資料最多晚 TTL 秒」。TTL 的選擇是業務決策：

| 資料 | 可接受的過期時間 | 合理 TTL |
|---|---|---|
| 城市列表、設施分類 | 幾小時到一天 | 1–24 小時 |
| 旅館介紹、照片清單 | 幾分鐘 | 5–30 分鐘 |
| 搜尋結果（含價格） | 幾十秒 | 30–120 秒 |
| 剩餘房間數、付款狀態 | 幾乎不能過期 | 不快取，或寫入時主動更新 |

TTL 太短，命中率下降，快取的效果有限；TTL 太長，使用者看到舊資料的時間變長。**TTL 也是一道安全網**：即使下面介紹的主動失效有 bug 漏掉了某些 key，TTL 仍保證它們最終會過期，所以幾乎所有快取資料都應該設 TTL。

### 方法二：寫入資料庫後刪除快取（invalidate）

需要更即時時，在更新資料庫之後**刪除**對應的 cache key，下一次讀取自然 miss，從資料庫重建最新值：

```python
def update_hotel_price(hotel_id: int, new_price: int) -> None:
    update_aurora_price(hotel_id, new_price)   # ① 先提交資料庫
    cache.delete(f"hotel:detail:{hotel_id}")   # ② 再刪除快取
```

為什麼是「刪除」而不是「直接把新值寫進快取」？因為兩個並行的更新可能以不同順序抵達快取：請求 A 把價格改成 3,000、請求 B 改成 3,200，資料庫最後是 3,200，但如果 B 先寫快取、A 後寫快取，快取裡就會一直是錯的 3,000。刪除沒有這個問題，下一次讀取一定從資料庫拿最新值。

為什麼是「先寫資料庫、再刪快取」？如果先刪快取再寫資料庫，中間空檔有讀取請求進來，會把**舊值**重新載入快取，而且一直留到 TTL 到期。先寫資料庫再刪快取仍有很小的競態窗口，但已經是實務上最常用的折衷；搭配 TTL，最壞情況也只會過期一個 TTL。

還有一種失敗：資料庫已經成功提交，但刪除快取時網路斷了。這種「兩個系統各寫一次」的問題叫 **dual write**，無法靠一次請求保證兩邊都成功。可靠一點的做法是讓失效動作由資料庫的變更事件驅動，例如 DynamoDB Streams（第 27 章）或 transactional outbox（第 33 章）觸發 Lambda 去刪除 key，失敗會自動重試。

### 方法三：Write-through（寫入時同步更新快取）

**Write-through** 是在每次寫入資料庫時，**同時把新值寫進快取**。這樣快取裡的資料永遠是新的，讀取時幾乎不會 miss。

- 優點：讀到的資料新、讀取延遲穩定，適合「寫完馬上會被讀」的資料，例如使用者剛改完的個人資料。
- 缺點：每次寫入都多一次快取寫入，寫入延遲增加；很多被寫入的資料可能根本沒人讀，浪費記憶體（通常要搭配 TTL 清掉冷資料）；快取節點重建後，沒被寫過的資料仍然不在快取裡，所以**實務上常把 write-through 和 cache-aside 一起用**：寫入時更新，讀取 miss 時仍會回資料庫載入。

### Write-behind（write-back）：小心使用

**Write-behind** 是先寫快取、立刻回應使用者，再由背景程序批次把資料寫回資料庫。寫入速度最快，也能把大量小寫入合併。但在資料寫回之前，**資料只存在快取裡**，快取故障就會遺失。它適合「遺失一點也沒關係」的資料，例如瀏覽次數統計；不適合訂單、付款、庫存這類資料。

| 策略 | 讀到舊資料的風險 | 寫入延遲 | 快取故障的後果 | 典型用途 |
|---|---|---|---|---|
| Cache-aside + TTL | 最多一個 TTL | 不受影響 | 變慢，不出錯 | 搜尋結果、商品頁 |
| Cache-aside + 寫後刪除 | 很小的競態窗口 | 多一次刪除 | 變慢，不出錯 | 旅館詳情、會員資料 |
| Write-through | 很低 | 增加 | 變慢，不出錯 | 寫完立刻要讀的資料 |
| Write-behind | 很低 | 最低 | **可能遺失資料** | 計數、統計等可容忍遺失的資料 |

## 28.5 快取怎麼把系統拖垮：Stampede、Penetration、Hot Key 與 Eviction

快取讓系統在正常時變快，但設計不好時，它會在最糟的時機製造故障。小林在第一版上線後，就一次遇到了下面四種問題中的三種。

### Cache stampede 與 thundering herd

第一版的搜尋快取每個 key 的 TTL 都是整整 60 秒。促銷開始時，數千個熱門 key 在幾秒內被同時建立，於是 60 秒後**同時過期**。下一秒，數萬個請求同時 miss，同時去查 Aurora，同時寫回快取，資料庫又被打垮一次。

這種「大量請求在同一時間因為快取失效而湧向後端」的現象叫 **cache stampede（快取踩踏）**；更廣義地，大量等待者被同一個事件同時喚醒、一起衝向同一資源的現象稱為 **thundering herd（驚群效應）**。解法有幾層：

1. **TTL 加隨機抖動（jitter）**：把 TTL 設成「基準值＋隨機秒數」，讓過期時間自然分散。這就是 28.3 節程式碼裡 `random.randint(0, 15)` 的用途。
2. **Request coalescing（請求合併，也叫 single-flight）**：同一個 key 同時 miss 時，只讓一個請求去資料庫，其他請求等它的結果。在分散式環境可以用快取本身做一把短期鎖：`SET lock:<key> <id> NX EX 5`，`NX` 表示只有 key 不存在時才設定成功，搶到鎖的請求去查資料庫，沒搶到的稍等後重讀快取。
3. **提早刷新（refresh ahead）**：在 TTL 到期前，由背景工作或「剩餘 TTL 很短時被讀取」的請求先重新載入，讓熱門 key 永遠不會真正過期。
4. **預熱（warming）**：已知的活動或新節點上線前，先用腳本把熱門 key 載入快取。
5. **保護資料庫**：限制應用程式對資料庫的並行查詢數（連線池上限、RDS Proxy，第 26 章），寧可讓部分請求慢一點，也不要讓資料庫整個崩潰。

### Cache penetration：查不存在的東西

有人寫了爬蟲，用隨機旅館 ID 呼叫 `GET /hotels/{id}`。這些 ID 根本不存在，資料庫查不到，cache-aside 也就沒有東西可以寫回快取，於是**每一個請求都穿透快取直接打到資料庫**。

解法是 **negative caching（快取「不存在」這個結果）**：查不到時也寫一筆特殊值（例如 `NOT_FOUND`），設定較短的 TTL（例如 30 秒）。對於可預測的攻擊，還應該在前面用 WAF 的 rate-based rule（第 16 章）限制單一來源的請求速率。

### Hot key：一個 key 撐不住

分散式快取會把不同的 key 分散到不同節點，但**同一個 key 永遠在同一個位置**。促銷首頁的「今晚特價清單」只有一個 key，所有使用者都讀它，結果某一個節點的 CPU 100%，其他節點閒著。這叫 **hot key（熱點鍵）**。

- **讀取熱點**：增加 replica 並讓讀取分散到 replica（28.7 節）；或在應用程式內加一層存活幾秒的 local cache，60 台 EC2 每台每 5 秒只讀一次快取；也可以把同一份資料複製成多個 key（`deals:tonight:0`～`deals:tonight:9`），讀取時隨機挑一個。
- **寫入熱點**：例如所有使用者都對同一個計數器 `INCR`。replica 幫不上忙，因為所有寫入都要到 primary。解法是把一個邏輯計數器拆成多個子 key 分散到不同 shard，讀取時再加總。

### Eviction：記憶體滿了怎麼辦

快取的記憶體是有限的。寫入新資料時記憶體已滿，快取必須丟掉一些舊資料騰出空間，這叫 **eviction（驅逐）**。驅逐和 TTL 過期是兩件不同的事：TTL 過期是「資料時間到了」，eviction 是「空間不夠了」，即使 key 還沒過期也可能被丟掉。

Valkey 與 Redis OSS 用參數 `maxmemory-policy` 決定怎麼挑選要丟的 key：

| Policy | 行為 | 適合 |
|---|---|---|
| `volatile-lru` | 只在「有設 TTL 的 key」中，丟最久沒被用到的（**ElastiCache 預設**） | 快取與不可丟的資料混放（不建議混放） |
| `allkeys-lru` | 在所有 key 中丟最久沒用到的 | 純快取用途，最常見的選擇 |
| `allkeys-lfu` / `volatile-lfu` | 丟最少被使用的 | 有明顯長期熱門資料 |
| `volatile-ttl` | 丟最快要過期的 | TTL 能反映資料重要性 |
| `noeviction` | 不丟任何 key，寫入直接回錯誤 | 不能丟資料的用途（例如當作 queue），但要嚴密監控記憶體 |

> [!warning] 常見誤解
> 「設定了 `volatile-lru`，記憶體就不會爆。」如果大部分 key 都沒有設 TTL，`volatile-lru` 找不到可以丟的 key，行為就和 `noeviction` 一樣：寫入開始失敗。純快取用途通常選 `allkeys-lru`，或確保每個 key 都有 TTL。

`Evictions` 指標持續上升，代表快取裝不下工作集（working set，常用資料的總量），命中率會跟著下降。解法是擴充記憶體（更大的 node type 或更多 shard，見 28.7 節）、縮短冷資料的 TTL，或壓縮 value 的大小。

## 28.6 ElastiCache 全貌：受管的 Valkey、Redis OSS 與 Memcached

到這裡我們談的都是「快取模式」，和用哪個產品無關。現在把 AWS 的名字放回來。

**Amazon ElastiCache** 是 AWS 受管的 in-memory 資料存放服務。「受管」的意思是：AWS 負責佈建節點、作業系統與引擎 patch、偵測節點故障並替換、執行備份與 failover；你負責選擇引擎與容量、設計 key 與 TTL、設定網路與安全。ElastiCache 一律部署在你的 VPC 裡（serverless 也是透過你 VPC 中的 endpoint 存取），沒有 public endpoint，從 VPC 外存取需要經由 VPN、Direct Connect 或 VPC 內的應用程式。

### 三種引擎

ElastiCache 支援三種開源引擎：

- **Redis OSS**：功能豐富的 in-memory 資料結構伺服器，長期以來最受歡迎的快取引擎。
- **Valkey**：2024 年 Redis 改變授權條款後，由 Linux Foundation 主導、從 Redis OSS 7.2 分支出來的開源專案。指令、協定與 Redis OSS 相容，既有的 Redis client 可以直接連線；ElastiCache 可以把 Redis OSS 叢集原地升級為 Valkey，而且 AWS 對 Valkey 的定價比 Redis OSS 低。新建專案通常直接選 Valkey。
- **Memcached**：歷史悠久、設計極簡的分散式 key-value 快取。

Valkey 和 Redis OSS 在本章大多數情境下可以視為同一類，以下合稱「Valkey／Redis OSS」。

| 比較 | Valkey／Redis OSS | Memcached |
|---|---|---|
| 資料型別 | string、hash、list、set、sorted set、stream、bitmap、HyperLogLog、geospatial 等 | 只有 string（任意 bytes） |
| 複寫與 replica | 支援，每個 shard 最多 5 個 replica | 不支援，節點之間互不複寫 |
| Multi-AZ 自動 failover | 支援 | 不支援，節點故障時該節點上的資料遺失 |
| 備份與還原（snapshot） | 支援 | 不支援（node-based） |
| 分片（sharding） | cluster mode enabled 時由服務管理 | 由 client 依 key 雜湊分散到各節點 |
| 執行緒 | 指令執行主要為單執行緒（ElastiCache 另有加強 I/O 多執行緒） | 多執行緒，可用滿大節點的所有 CPU |
| Pub/Sub、交易、Lua script | 支援 | 不支援 |
| 跨 Region 複寫 | Global Datastore | 不支援 |
| 適合 | 幾乎所有新專案；需要資料結構、高可用、持久化 | 純粹、簡單、可隨時丟失的物件快取，且已有 Memcached 程式 |

> [!tip] 考試提示
> 題目只要出現 **sorted set、排行榜（leaderboard）、pub/sub、地理位置查詢、複寫、自動 failover、備份、持久化** 任何一個，答案就是 Valkey／Redis OSS。只有在題目強調「最簡單的快取、多執行緒、可以水平加節點、資料遺失可接受」而且沒有上述需求時，才會選 Memcached。

### Node-based 與 Serverless 兩種部署方式

ElastiCache 有兩種部署選項：

- **Node-based cluster（自行設計叢集）**：你選擇 node type（例如 `cache.r7g.large`）、shard 數與 replica 數，按節點時數計費。適合流量穩定、需要細緻控制參數與拓撲的工作負載。
- **ElastiCache Serverless**：你只要給一個名字，服務自動依流量擴縮容量，按「實際儲存的資料量」與「處理請求消耗的運算單位（ECPU）」計費。28.9 節會詳細比較。

接下來先深入 node-based 的 Valkey／Redis OSS 拓撲，因為 replica、shard、failover 這些觀念是理解所有選項的基礎。

## 28.7 Valkey／Redis OSS 的拓撲：Shard、Replica、Cluster Mode 與 Failover

### 基本單位：node、shard、replication group

- **Node（節點）**：一台執行快取引擎的受管機器，有固定的記憶體與 CPU。
- **Shard（分片，也叫 node group）**：一個 primary node 加上 0～5 個 replica node。Primary 負責讀寫，replica 透過**非同步複寫**跟上 primary 的資料，可以分擔讀取，也是 primary 故障時的接班人。
- **Replication group**：一或多個 shard 組成的叢集，也就是你在 console 上看到的那個「Valkey／Redis OSS cluster」。

### Cluster mode disabled：一個 shard

**Cluster mode disabled** 的叢集只有一個 shard，所有資料都在同一個 primary 上：

- 資料量受限於**單一節點的記憶體**；要擴充只能換更大的 node type（scale up）。
- 寫入能力受限於單一 primary；讀取可以加 replica 擴充。
- 提供兩個 endpoint：**primary endpoint**（永遠指向目前的 primary，寫入用）與 **reader endpoint**（把連線分散到各 replica，讀取用）。
- 優點是 client 最簡單，所有多 key 指令都能用。

### Cluster mode enabled：多個 shard

當資料量或寫入量超過單一節點時，改用 **cluster mode enabled**。Valkey／Redis OSS cluster 把整個 key 空間切成 **16,384 個 hash slot**，每個 key 依 CRC16 雜湊值落在某個 slot，每個 shard 負責一段 slot：

```text
                       [應用程式（cluster-aware client）]
                                  │
                     ① 連線到 configuration endpoint，取得 slot 對應表
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   Shard 1（slot 0–5460）  Shard 2（slot 5461–10922） Shard 3（slot 10923–16383）
 ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
 │ Primary   (AZ-a)    │ │ Primary   (AZ-c)    │ │ Primary   (AZ-d)    │
 │   │ ② 非同步複寫     │ │   │                 │ │   │                 │
 │   ▼                 │ │   ▼                 │ │   ▼                 │
 │ Replica   (AZ-c)    │ │ Replica   (AZ-d)    │ │ Replica   (AZ-a)    │
 └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          ③ key「hotel:detail:1234」→ CRC16 → slot 8001 → 直接連 Shard 2 的 primary
          ④ 若 Shard 2 primary 故障 → 其 replica 被提升為 primary，slot 對應表更新
```

① **Cluster-aware client**（支援 cluster 協定的 client 程式庫）先透過 **configuration endpoint** 取得「哪個 slot 在哪個節點」的對應表，之後每個指令直接送到正確的 shard，不經過任何代理。② 每個 shard 的 primary 把寫入非同步複寫給自己的 replica，而且 primary 與 replica 被刻意放在不同 AZ。③ client 自己計算 key 屬於哪個 slot。④ 某個 primary 故障時，只有那個 shard 需要 failover，其他 shard 不受影響；client 會收到重新導向，更新對應表。

Cluster mode enabled 的重點：

- **寫入與記憶體都能水平擴充**：增加 shard 就增加寫入能力與總記憶體。ElastiCache 支援**線上 resharding**，在不停機的情況下增減 shard、搬移 slot。
- **Client 必須是 cluster-aware**，否則會收到 `MOVED` 錯誤。
- **跨 slot 的多 key 指令受限**：`MGET`、交易、Lua script 中的多個 key 必須在同一個 slot。需要時用 **hash tag**：key 裡用 `{}` 包住的部分才拿去雜湊，例如 `{user:42}:cart` 與 `{user:42}:profile` 一定在同一個 slot。
- 每個 shard 一樣是 1 個 primary 加最多 5 個 replica。

### Multi-AZ 與自動 failover

在 replication group 啟用 **Multi-AZ** 與 **automatic failover** 後，ElastiCache 持續監控 primary。primary 故障（節點故障、AZ 故障）時：

1. ElastiCache 從同一 shard 的 replica 中挑一個（通常是複寫延遲最小的）提升為新 primary。
2. **Primary endpoint 的 DNS 改指向新 primary**；cluster mode enabled 則更新 slot 對應表。
3. 舊 primary 所在位置會建立新的 replica 補回。

整個過程是秒級到數十秒等級，期間寫入會失敗、部分連線會中斷。要讓這個機制真的生效，有幾個條件：

- **每個 shard 至少要有 1 個 replica**，而且 replica 要放在與 primary 不同的 AZ。沒有 replica 的 shard 無法 failover，只能等節點被替換並從頭開始（資料全空）。
- **應用程式必須連 endpoint，而不是個別節點的位址**。連 node endpoint 的程式在 failover 後仍會試圖連到舊節點。
- **Client 要能重連**：設定合理的連線逾時、重試與 DNS 不要永久快取。既有的 TCP 連線不會自動「搬」到新 primary。
- 因為複寫是非同步的，**failover 可能遺失最後幾毫秒的寫入**。對快取而言這通常無所謂，這也再次說明為什麼不能拿它當 source of truth。

> [!tip] 考試提示
> 「Redis 快取要能承受 AZ 故障，且 LEAST operational overhead」→ 啟用 Multi-AZ automatic failover，每個 shard 至少一個位於其他 AZ 的 replica，應用程式使用 primary／configuration endpoint。看到「定期 snapshot 然後故障時手動還原」通常是錯的，因為 RTO 太長。

### 持久化與備份

Valkey／Redis OSS 在 ElastiCache 上可以建立 **snapshot（備份）**：

- **自動備份**：每天在你指定的時段執行，保留天數可設定（最長 35 天）。
- **手動備份**：隨時建立，保留到你刪除為止；可以**匯出到 S3**，用來跨 Region 或跨帳號複製。
- 從 snapshot 可以還原成新的叢集，用來重建環境、預熱，或把資料搬到不同 node type。

Snapshot 是「某一個時間點的副本」，兩次 snapshot 之間的寫入沒有被保存。它解決的是「整個叢集被誤刪或要重建時，不用從零開始」，而不是「每一筆寫入都不能遺失」。要求每一筆寫入都耐久的需求，對應的是 MemoryDB（28.11 節）。

### 擴充方式總整理

| 問題 | Cluster mode disabled | Cluster mode enabled |
|---|---|---|
| 讀取量太大 | 增加 replica（最多 5 個），讀取走 reader endpoint | 每個 shard 增加 replica，client 開啟從 replica 讀取 |
| 寫入量太大 | 只能換更大的 node type | 增加 shard（線上 resharding） |
| 記憶體不夠 | 換更大的 node type | 增加 shard 或換更大 node type |
| 單一 hot key | replica 或 local cache 分散讀取 | 同左；寫入熱點要拆 key |

ElastiCache 另有 **data tiering**：使用附帶本機 NVMe SSD 的節點類型（例如 `r6gd`），把較少存取的 value 自動移到 SSD，記憶體只保留熱資料。適合「資料量很大、但每天只有一小部分被頻繁存取」的情境，能以較低成本換取略高的冷資料延遲。

## 28.8 不只是查詢快取：Session、排行榜、限流與即時訊息

Valkey／Redis OSS 豐富的資料結構，讓它在 Wanderly 裡除了快取查詢結果，還承擔了好幾個角色。

### Session store：讓 web tier 變成 stateless

Wanderly 的會員登入後，伺服器要記住「這個 cookie 屬於哪個使用者、購物車裡有什麼草稿」。如果 session 存在 EC2 的記憶體裡，Auto Scaling 縮減（scale in）掉那台 EC2 時，使用者就被登出；ALB 的 sticky session（第 10 章）能讓同一使用者固定連到同一台，但 scale in 或 instance 故障時一樣會遺失，而且流量分配會不平均。

把 session 外部化到 ElastiCache 後，每台 EC2 都是 **stateless（無狀態）** 的，任何一台都能處理任何使用者的請求，scale in 也不影響登入狀態（第 18 章）：

```text
SET session:9f8e7d '{"user_id":42,"lang":"zh-TW"}' EX 1800
```

`EX 1800` 讓 session 在 30 分鐘沒有更新後自動過期，等於實作了「閒置登出」。Session 遺失的後果是使用者要重新登入，屬於可以接受的程度，所以適合放在快取；若 session 裡有不可遺失的資料（例如結帳中的訂單），那部分應該寫入資料庫。DynamoDB 也是常見的 session store 選項（有 TTL、serverless、耐久），當需求強調「耐久、無需管理容量」時題目可能偏向 DynamoDB；強調「sub-millisecond 延遲」時偏向 ElastiCache。

### Leaderboard：sorted set

**Sorted set（有序集合）** 是每個成員都帶一個分數、自動依分數排序的集合。Wanderly 的「本週最熱門旅館」排行榜：

```text
ZINCRBY hotels:popular:2025w51 1 hotel:1234      # 每次被預訂，分數 +1
ZREVRANGE hotels:popular:2025w51 0 9 WITHSCORES  # 取前 10 名
ZREVRANK hotels:popular:2025w51 hotel:1234       # 查某間旅館的名次
```

在關聯式資料庫裡，即時排名需要對整張表做 `ORDER BY ... LIMIT`，資料量大時很昂貴；sorted set 的插入與查名次都是對數時間複雜度，數百萬成員也能在毫秒內完成。

### Rate limiting：計數器加 TTL

要限制每個 API key 每分鐘最多 100 次呼叫：

```text
INCR ratelimit:apikey-77:202512241201   # 回傳目前次數
EXPIRE ratelimit:apikey-77:202512241201 60
```

`INCR` 是原子操作，多台伺服器同時遞增也不會算錯；超過 100 就拒絕請求。這種計數器遺失的後果只是「這一分鐘的額度被重置」，很適合放在快取。

### Pub/Sub 與其他

Valkey／Redis OSS 支援 **pub/sub（發布／訂閱）**，可以把「價格變動」即時推播給所有訂閱的 WebSocket 伺服器；**geospatial** 指令可以查「方圓 2 公里內的旅館」；**stream** 可以當作輕量的事件日誌。不過 pub/sub 訊息不會保存，訂閱者離線就收不到；需要可靠的訊息傳遞時，應該用 SQS、SNS、EventBridge（第 32 章）或 Kinesis（第 31 章）。

## 28.9 ElastiCache Serverless：不必規劃節點的快取

小林在規劃新的「AI 行程推薦」服務時遇到另一種難題：這個服務剛上線，沒人知道流量會是每秒 100 次還是 10 萬次，選錯 node type 不是浪費錢就是被打爆。

**ElastiCache Serverless** 就是為這種情境設計的：

- 建立時只需要名字（與 VPC、subnet、security group 設定），通常一分鐘左右就能使用。
- 服務**自動依流量與資料量擴縮**，不需要選 node type、shard 數或 replica 數。
- **資料預設跨多個 AZ 複寫**，具高可用性。
- 提供**單一 endpoint**，client 不需要理解叢集拓撲；連線**一律使用 TLS 加密**。
- 支援 Valkey、Redis OSS 與 Memcached 三種引擎。
- 計費依兩項用量：**儲存的資料量（以 GB-hour 計）** 與 **ElastiCache Processing Units（ECPU）**，ECPU 反映請求消耗的 CPU 與傳輸的資料量。
- 可以設定**用量上限**（最大資料量、最大 ECPU／秒），避免失控的流量造成意外帳單。達到 ECPU 上限時請求會被節流（throttle）；達到資料量上限時，服務會以 LRU 逐出有設 TTL 的資料，沒有可逐出的資料時，新的寫入會收到 out-of-memory 錯誤。反過來也可以設定**最小值**做預熱（pre-scaling），在已知的大活動前先把容量拉高。

用 CLI 建立一個 Valkey serverless cache：

```bash
aws elasticache create-serverless-cache \
  --serverless-cache-name wanderly-reco-cache \
  --engine valkey \
  --subnet-ids subnet-0a1b2c3d subnet-0e4f5a6b \
  --security-group-ids sg-0123456789abcdef0 \
  --cache-usage-limits 'DataStorage={Maximum=50,Unit=GB},ECPUPerSecond={Maximum=100000}'
```

### Serverless 還是 node-based？

| 考量 | ElastiCache Serverless | Node-based cluster |
|---|---|---|
| 容量規劃 | 不需要 | 要選 node type、shard、replica |
| 流量特性 | 尖峰難預測、變化大、新服務 | 穩定、可預測 |
| 計費 | 依資料量與 ECPU 用量 | 依節點時數；可買 **reserved nodes** 折扣 |
| 參數與拓撲控制 | 有限 | 完整（parameter group、node type、data tiering） |
| 高可用 | 預設跨 AZ | 需自己設定 replica 與 Multi-AZ |
| 典型考試關鍵字 | unpredictable、LEAST operational overhead、no capacity planning | steady-state、需要特定參數、reserved 長期折扣 |

Serverless 降低的是「容量規劃與擴縮」的營運負擔，但它不會幫你設計 cache key、TTL 或失效邏輯，也不會修好 hot key。

> [!note] Node-based 的成本最佳化
> 穩定的 node-based 叢集可以購買 **reserved nodes**（1 年或 3 年承諾，換取大幅折扣，第 39 章）；選擇 Graviton 節點（`r7g`、`m7g` 等）通常有更好的性價比；資料量大但熱資料比例小時考慮 data tiering；從 Redis OSS 升級到 Valkey 也能直接降低單價。

## 28.10 安全與監控：快取也裝著敏感資料

快取裡常有 session token、會員資料、價格策略，它和資料庫一樣需要保護。

### 網路與加密

- **網路隔離**：ElastiCache 位於 VPC 的 private（通常是 isolated）subnet，透過 **cache subnet group** 指定可用的 subnet（至少跨兩個 AZ，第 5 章）。用 **security group** 只允許應用程式的 security group 連到快取的 port（Valkey／Redis OSS 預設 6379，Memcached 預設 11211）（第 6 章）。
- **傳輸加密（in-transit encryption）**：啟用 TLS，避免 VPC 內的流量被竊聽。Serverless 一律使用 TLS；node-based 要在建立時或之後啟用，client 也要支援 TLS。
- **靜態加密（at-rest encryption）**：加密磁碟上的資料（包括 snapshot 與 swap），可以使用 AWS 受管的 key 或你自己的 KMS customer managed key（第 15 章）。Node-based 叢集的 at-rest encryption 只能在建立時啟用，既有未加密叢集要從 backup 還原成新的加密叢集；Serverless 預設就會加密。

### 身份驗證與授權

Security group 只能決定「誰的封包能到達 port 6379」，**不能決定「誰可以執行哪個指令、讀哪些 key」**。Valkey／Redis OSS 的應用層權限控制有三種方式：

- **AUTH token**：單一密碼，所有知道密碼的 client 都有完整權限。簡單，但無法區分角色。
- **RBAC（Role-Based Access Control）**：建立多個 **user**，每個 user 有一條 **access string** 規定可執行的指令與可存取的 key pattern，再把 user 加入 **user group** 並關聯到叢集。例如客服工具只能 `GET` `session:*`，結帳服務可以讀寫 `cart:*`。
- **IAM authentication**：用 IAM 身份產生短期的驗證 token 連線，不需要在程式裡保存長期密碼。

一個 RBAC user 的 access string 例子：`on ~cart:* +@read +@write -@dangerous`，意思是「啟用、只能存取 `cart:` 開頭的 key、允許讀寫類指令、禁止危險指令（如 `FLUSHALL`）」。

用 CLI 建立一個加密、跨三個 AZ、cluster mode enabled 的 node-based Valkey 叢集（`num-node-groups` 大於 1 時，必須使用 `cluster-enabled` 為 yes 的 parameter group，例如 `default.valkey7.cluster.on`）：

```bash
aws elasticache create-replication-group \
  --replication-group-id wanderly-search-cache \
  --replication-group-description "Hotel search cache" \
  --engine valkey \
  --engine-version 7.2 \
  --cache-parameter-group-name default.valkey7.cluster.on \
  --cache-node-type cache.r7g.large \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --cache-subnet-group-name wanderly-data-subnets \
  --security-group-ids sg-0cache0000000001 \
  --user-group-ids wanderly-app-users \
  --snapshot-retention-limit 7
```

### 要盯哪些指標

| CloudWatch 指標 | 代表什麼 | 異常時的動作 |
|---|---|---|
| `CacheHitRate`（或 `CacheHits`／`CacheMisses`） | 命中率 | 下降時檢查 TTL、key 設計、是否在 evict |
| `Evictions` | 因記憶體不足被丟掉的 key 數 | 持續上升就要擴充記憶體或縮短 TTL |
| `DatabaseMemoryUsagePercentage` | 記憶體使用率 | 接近上限時擴充 |
| `EngineCPUUtilization` | 引擎執行緒的 CPU（比整機 CPU 更準） | 高時考慮加 shard、加 replica、處理 hot key |
| `CurrConnections` / `NewConnections` | 連線數 | 暴增常代表 client 沒有重用連線 |
| `ReplicationLag` | replica 落後 primary 的時間 | 偏高代表寫入量太大或 replica 規格不足 |

這些指標的告警設定與 dashboard 做法在第 36 章詳述。

## 28.11 不是 ElastiCache 的時候：MemoryDB 與 DAX

小林的快取上線後，其他團隊也來詢問：「我們能不能也用 ElastiCache？」其中兩個需求，答案是「應該用別的服務」。

### MemoryDB：需要耐久性的 in-memory 資料庫

庫存團隊想用 Redis 的資料結構管理即時的房間庫存，要求讀取微秒級、寫入耐久、可以作為**主要資料庫**。這正是 ElastiCache 做不到的：它的非同步複寫與定時 snapshot 無法保證每一筆確認過的寫入都不遺失。

**Amazon MemoryDB** 是相容 Valkey 與 Redis OSS 的**耐久性 in-memory 資料庫**。它和 ElastiCache 最大的差異是：每一筆寫入在回應 client 之前，都會先寫進一個**跨多個 AZ 的分散式交易日誌（Multi-AZ transactional log）**。即使整個節點甚至一個 AZ 故障，已確認的寫入都能從日誌中恢復。

| 比較 | ElastiCache（Valkey／Redis OSS） | MemoryDB |
|---|---|---|
| 定位 | 快取，資料可重建 | 主要資料庫（primary database） |
| 寫入耐久性 | 非同步複寫，failover 可能遺失最近寫入 | 寫入確認前已持久化到跨 AZ 交易日誌 |
| 讀取延遲 | 微秒到 sub-millisecond | 微秒級 |
| 寫入延遲 | 微秒到 sub-millisecond | 個位數毫秒（要等日誌持久化） |
| 一致性 | primary 讀取為最新，replica 最終一致 | primary 讀取強一致，replica 最終一致 |
| 成本 | 較低 | 較高 |
| 什麼時候選 | 加速另一個資料庫、session、可重建資料 | 想用 Redis 資料結構當唯一資料庫，且不能遺失資料 |

如果你的架構是「Aurora／DynamoDB 是 source of truth，前面加一層快取」，用 ElastiCache；如果你的架構是「根本沒有另一個資料庫，Redis 資料結構本身就是資料」，用 MemoryDB。MemoryDB 也會出現在第 29 章的 purpose-built 資料庫選型中。

### DAX：DynamoDB 專用的 read-through 快取

會員服務的資料在 DynamoDB，讀取量很大、需要微秒級延遲。他們可以用 ElastiCache 做 cache-aside，但要自己寫 key 設計、失效邏輯；更簡單的選擇是 **DynamoDB Accelerator（DAX）**（第 27 章）：

- **API 相容 DynamoDB**：把 DynamoDB SDK client 換成 DAX client，程式邏輯幾乎不用改。
- **Read-through 與 write-through**：讀取 miss 時 DAX 自己去 DynamoDB 拿；寫入經過 DAX 時，同時寫入 DynamoDB 並更新 item cache。
- 有 **item cache**（`GetItem`／`BatchGetItem`）與 **query cache**（`Query`／`Scan` 結果）兩種快取，預設 TTL 為 5 分鐘。
- **只加速 eventually consistent reads**：strongly consistent read 與 transactional 操作會直接轉送到 DynamoDB，不經過快取。
- 部署在 VPC 中，是 node-based 叢集，可跨 AZ 放置多個節點。

| 比較 | DAX | ElastiCache |
|---|---|---|
| 資料來源 | 只能是 DynamoDB | 任何資料來源（RDS、DynamoDB、外部 API…） |
| 程式改動 | 換 client 即可 | 要自己寫 cache-aside 與失效邏輯 |
| 資料結構 | DynamoDB item 與查詢結果 | 豐富的 Valkey／Redis OSS 資料結構 |
| 一致性 | eventually consistent；strongly consistent 讀取直接穿透 | 由你的失效設計決定 |
| 典型題目關鍵字 | DynamoDB、microsecond、minimal code changes | 多種資料來源、session、leaderboard、RDS 加速 |

> [!warning] 常見誤解
> 「DAX 可以讓 strongly consistent read 也變成微秒級。」不行。Strongly consistent read 要求讀到最新寫入，快取無法保證，所以 DAX 會直接轉給 DynamoDB。題目若要求「所有讀取都要強一致」，加 DAX 並不會改善這些讀取的延遲。

## 28.12 分層快取：把 CloudFront、API Gateway 與 ElastiCache 組起來

最後回到 Wanderly 的促銷夜。小林在檢討後設計的新架構，讓每一層快取各自吸收它最適合的流量：

```text
使用者（全球）
   │
   ▼
① [CloudFront]  快取：旅館照片、JS/CSS、未登入的熱門城市頁（TTL 60 秒）
   │ miss 或個人化請求
   ▼
② [ALB] ──► [Web/App EC2 × N（stateless）]
                │   ③ 程式內 local cache：特價清單、幣別匯率（TTL 5 秒）
                │
                ├──► ④ [ElastiCache for Valkey，cluster mode enabled，Multi-AZ]
                │        · hotel:search:*   cache-aside，TTL 60–75 秒
                │        · hotel:detail:*   寫後刪除 + TTL 10 分鐘
                │        · session:*        TTL 30 分鐘
                │        · hotels:popular:* sorted set 排行榜
                │
                │   ⑤ miss（已做 request coalescing 與並行上限）
                ▼
           [RDS Proxy] ──► [Aurora MySQL]（source of truth）
                               │
                               └─ ⑥ 變更事件 → Lambda → 刪除相關 cache key
```

① **CloudFront**（第 11 章）在全球 edge 快取「所有人看到都一樣」的 HTTP 回應，連 ALB 都不需要經過。關鍵是 cache key 只包含真正影響內容的部分（例如城市、語言），並且**絕不快取個人化回應**，否則會把 A 使用者的頁面給 B 看。② 個人化與動態請求才進入 ALB 與應用程式。③ 對極熱門、所有人共用的少量資料，每台 EC2 自己在記憶體保留幾秒，解決 hot key。④ ElastiCache 承擔主要的查詢快取、session 與排行榜。⑤ 真正 miss 的請求經 RDS Proxy（第 26 章）控制連線數，再打到 Aurora，並以 request coalescing 避免 stampede。⑥ 資料變更時由事件驅動失效，即使應用程式忘了刪 key，TTL 也會兜底。

下一次促銷，Aurora 的 CPU 最高只到 35%。更重要的是，小林刻意演練了「把 ElastiCache 整個關掉」的情境：網站變慢、但仍能運作，因為資料庫前面還有並行上限保護，而且所有資料都能從 Aurora 重建。這就是「快取可以丟」的真正意義。

## 28.13 比較與選型

### 我該用哪一種快取？

```text
要快取的是什麼？
├─ 可共用的 HTTP 內容（圖片、靜態檔、公開頁面、可共用的 API 回應）
│    └─ CloudFront（全球）；只需 API 層快取 → API Gateway caching
├─ DynamoDB 的讀取，希望幾乎不改程式
│    └─ DAX（只加速 eventually consistent reads）
└─ 應用程式層的查詢結果、物件、session、計數器
     ├─ 資料不可遺失，且沒有其他資料庫作為真相來源？
     │    └─ 是 → MemoryDB（耐久性 in-memory 資料庫）
     └─ 否（可從資料庫重建）→ ElastiCache
          ├─ 需要資料結構、replica、failover、備份、Global Datastore？
          │    └─ 是 → Valkey（或 Redis OSS）
          │    └─ 否，只要極簡多執行緒快取且已有 Memcached 程式 → Memcached
          └─ 容量部署方式
               ├─ 流量難預測、想零容量規劃 → ElastiCache Serverless
               └─ 流量穩定、要細緻控制或 reserved 折扣 → Node-based
```

### 服務對照

| 服務 | 本質 | 耐久性 | 高可用 | 最佳用途 |
|---|---|---|---|---|
| ElastiCache for Valkey／Redis OSS | 受管 in-memory 資料結構快取 | 非同步複寫 + snapshot | Multi-AZ 自動 failover | 查詢快取、session、排行榜、限流 |
| ElastiCache for Memcached | 受管簡單 key-value 快取 | 無 | 無 failover，節點可分散 AZ | 簡單物件快取 |
| ElastiCache Serverless | 自動擴縮的 ElastiCache | 依引擎 | 預設跨 AZ | 流量難預測的新服務 |
| MemoryDB | 相容 Valkey／Redis OSS 的耐久資料庫 | 跨 AZ 交易日誌 | Multi-AZ | 以 Redis 資料結構作為主要資料庫 |
| DAX | DynamoDB 專用 read/write-through 快取 | 不是真相來源 | 多節點跨 AZ | DynamoDB 微秒讀取 |
| CloudFront | 邊緣 HTTP 快取 | 不適用 | 全球受管 | 靜態內容與可共用的 HTTP 回應 |
| RDS／Aurora read replica | 資料庫副本（第 26 章） | 是資料庫 | 可 promote | 需要 SQL、讀取量大、可接受複寫延遲 |

> [!tip] 考試提示：read replica 還是快取？
> 兩者都能分擔讀取。題目若強調「同樣的查詢重複很多次」「sub-millisecond」「降低資料庫成本」，選 ElastiCache；若強調「需要執行各種不同的 SQL 查詢（例如報表）」「不想改應用程式的查詢邏輯」，選 read replica。

## 28.14 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 相同查詢重複、資料庫 CPU 高、讀多寫少 | ElastiCache + cache-aside |
| sub-millisecond、in-memory | ElastiCache（Valkey／Redis OSS） |
| leaderboard、ranking、sorted sets | Valkey／Redis OSS sorted set |
| 多執行緒、最簡單、資料可遺失、不需要複寫 | Memcached |
| Redis 快取要撐過 AZ 故障 | Multi-AZ + automatic failover，每 shard 至少一個其他 AZ 的 replica |
| 資料量／寫入量超過單一節點 | Cluster mode enabled，增加 shard |
| 使用者在 scale in 後被登出 | Session 外部化到 ElastiCache（或 DynamoDB） |
| 快取資料過期太久 | 縮短 TTL、寫入後刪除 key、write-through |
| 大量 key 同時過期、資料庫瞬間被打爆 | TTL jitter、request coalescing、預熱 |
| 流量難預測、不想規劃容量 | ElastiCache Serverless |
| Redis 相容且需要耐久、作為主要資料庫 | MemoryDB |
| DynamoDB 微秒讀取、最少程式改動 | DAX |
| 全球使用者、靜態內容延遲高 | CloudFront |
| 快取要加密、限制指令權限 | TLS + at-rest encryption + RBAC／IAM authentication |
| 跨 Region 低延遲讀取 Redis 資料 | Global Datastore（SAP，見 28.15 節） |

**常見陷阱**：

1. 把 ElastiCache 當成不可遺失資料的唯一存放處：它是快取，複寫非同步、snapshot 有間隔；耐久需求選 MemoryDB 或資料庫。
2. 以為增加 replica 能分散寫入：replica 只分擔讀取，寫入一定到 primary；寫入擴充要加 shard。
3. 選 Memcached 卻要求 failover、備份或排行榜：Memcached 沒有這些功能。
4. 以為 DAX 能加速 strongly consistent read 或能快取 RDS：DAX 只服務 DynamoDB 的 eventually consistent reads。
5. 只靠 security group 控制「誰能執行哪些指令」：security group 只管網路可達性，指令與 key 權限要靠 RBAC。
6. 只有 primary、沒有 replica 卻宣稱高可用：沒有 replica 就沒有 failover 對象。

## 28.15 SAP 加深：全球快取、遷移暖機與成本治理

SAA 題目關心「一個應用程式怎麼加快取」；SAP 題目則會把快取放進多 Region、遷移與大規模營運的脈絡。

### Global Datastore：跨 Region 的 Valkey／Redis OSS

Wanderly 進軍東南亞後，新加坡的使用者要讀取東京的熱門旅館資料。**Global Datastore** 讓一個 node-based Valkey／Redis OSS 叢集（primary cluster）把資料非同步複寫到其他 Region 的 secondary cluster：

- **只有 primary Region 可以寫入**，secondary Region 提供低延遲的本地讀取；跨 Region 複寫延遲通常在一秒以內。
- Primary Region 故障時，可以把某個 secondary cluster **提升（promote）為新的 primary**，作為災難復原手段。
- 寫入路徑仍要回到 primary Region，所以它適合「讀遠多於寫、能容忍短暫延遲」的資料。多 Region 的寫入路由與一致性取捨在第 42 章詳述。

另一種做法是每個 Region 各自有獨立的快取，各自從本地的資料庫副本（例如 Aurora Global Database 或 DynamoDB global tables）以 cache-aside 載入。這種做法沒有跨 Region 的快取依賴，故障隔離更好，代價是每個 Region 都要承受自己的冷啟動。

### 遷移與切換時的快取

從地端遷移到 AWS、或做 Blue/Green 部署（第 37 章）時，新環境的快取是空的。若直接把 100% 流量切過去，所有請求同時 miss，等於自己製造一場 stampede。SAP 題常見的正確做法是：

- 從既有 Redis 的 RDB 備份檔（放到 S3）**還原**成新的 ElastiCache 叢集，或用線上遷移把自建 Redis 的資料同步到 ElastiCache。
- 用加權路由（Route 53 weighted、ALB weighted target groups）**逐步增加流量**，讓快取有時間暖機。
- 切換前先以腳本**預熱**最熱門的 key。

### 多團隊共用快取的治理

當多個團隊共用一個大叢集時，一個團隊的 hot key 或 `KEYS *` 指令可能拖垮所有人。常見治理手段：依 blast radius 拆成多個叢集（或每個服務各自的 serverless cache）、用 RBAC 限制每個服務的 key 前綴與危險指令、為每個叢集設定 CloudWatch 告警，並以 tag 做成本分攤（第 39、43 章）。

### 用快取省錢的計算方式

SAP 的成本題常要求比較「升級資料庫」與「加快取」。思考方式是：資料庫的成本隨「每秒查詢數」線性成長，快取則用很便宜的單次讀取吸收重複查詢。如果命中率能達到 90% 以上，往往用一個小型 ElastiCache 叢集就能讓資料庫降級或少開幾個 read replica，總成本反而下降。但若資料幾乎不重複被讀（例如每個請求查詢條件都不同的報表），命中率很低，快取只是增加成本與複雜度，這時應該考慮 read replica、查詢最佳化或把分析工作移到資料倉儲（第 30 章）。

## 本章重點整理

- 快取是一份「可以丟掉」的資料副本，它不是 source of truth；任何快取資料都必須能從資料庫重建。
- 命中率對資料庫負載的影響是非線性的：命中率從 90% 提高到 99%，打到資料庫的請求減少為十分之一。
- Cache-aside（lazy loading）由應用程式在 miss 時查資料庫並寫回快取，只快取被讀過的資料，快取故障只會變慢不會出錯。
- TTL 決定資料最多過期多久，也是失效邏輯出錯時的安全網；更新資料時應「先寫資料庫、再刪除 cache key」。
- Write-through 寫入時同步更新快取，讀取新鮮但增加寫入延遲；write-behind 速度最快但資料在寫回前可能遺失。
- Cache stampede 用 TTL jitter、request coalescing、提早刷新與預熱處理；cache penetration 用 negative caching；hot key 用 replica、local cache 或拆 key。
- Eviction 是記憶體不足時丟資料，和 TTL 過期不同；ElastiCache 預設 `volatile-lru`，純快取通常改用 `allkeys-lru`。
- Valkey／Redis OSS 提供豐富資料結構、replica、Multi-AZ 自動 failover、snapshot 與 Global Datastore；Memcached 只有簡單 key-value、多執行緒、沒有複寫與備份。
- 每個 shard 是 1 個 primary 加最多 5 個 replica；replica 分擔讀取，寫入擴充要靠 cluster mode enabled 增加 shard。
- 自動 failover 需要每個 shard 至少一個其他 AZ 的 replica，應用程式要連 endpoint 並能重連；複寫是非同步的，可能遺失最近寫入。
- ElastiCache Serverless 自動擴縮、預設跨 AZ、按資料量與 ECPU 計費，適合流量難預測的工作負載；穩定負載用 node-based 搭配 reserved nodes。
- Security group 控制網路可達性，TLS 與 at-rest encryption 保護資料，RBAC 或 IAM authentication 控制誰能執行哪些指令。
- MemoryDB 以跨 AZ 交易日誌提供耐久性，可作為 Redis 相容的主要資料庫；ElastiCache 用來加速其他資料庫。
- DAX 是 DynamoDB 專用、API 相容的 read-through／write-through 快取，只加速 eventually consistent reads。
- CloudFront 快取可共用的 HTTP 回應，ElastiCache 快取應用程式層的資料；分層快取讓每一層吸收它最適合的流量。

## 本章練習題

### 練習 28-1｜SAA｜單選｜Cache-aside 讀取流程

Wanderly 的旅館詳情 API 從 Aurora MySQL 讀取資料，讀取量是寫入量的 200 倍。團隊決定在前面加上 ElastiCache for Valkey。需求是：只快取真正被讀取的旅館、快取節點被替換而清空時系統仍能回傳正確資料、不需要修改資料庫。

應用程式的讀取流程應如何設計？

- A. 每次寫入 Aurora 時同時寫入快取，讀取時只查快取，查不到就回傳 404
- B. 先查快取；未命中時查詢 Aurora，把結果連同 TTL 寫入快取後再回傳
- C. 每天凌晨用排程把整張旅館表載入快取，白天只從快取讀取
- D. 同時查詢快取與 Aurora，採用較先回來的結果

> [!answer]- 答案：B
> **A ✗** 讀取只查快取、miss 就回 404，會在快取清空或資料被 evict 後把存在的旅館誤判為不存在，違反「清空時仍能回傳正確資料」。Write-through 可以搭配使用，但讀取 miss 時仍必須回到資料庫。
>
> **B ✓** 這是 cache-aside（lazy loading）：應用程式在 miss 時回到 source of truth 讀取並寫回快取，只有被讀過的資料才會進快取，快取清空後也能自動重建。TTL 讓資料最終過期。
>
> **C ✗** 全量預載會浪費記憶體在沒人讀的資料上，而且一天內的資料變更不會反映；快取節點在白天被替換時也沒有重建機制。
>
> **D ✗** 同時查兩邊沒有降低資料庫負載（每個請求仍打到 Aurora），而且可能拿到過期的快取結果。
>
> **考點**：SAA-3.3、SAA-2.1｜cache-aside 讀取路徑

### 練習 28-2｜SAA｜單選｜更新資料後的快取失效

旅館業者在後台調整房價後，Wanderly 要求使用者在數秒內就能看到新價格。目前旅館詳情使用 cache-aside，TTL 為 30 分鐘；團隊不希望把 TTL 大幅縮短，因為會讓 Aurora 的讀取量上升好幾倍。後台調價的頻率很低。

最合適的做法是什麼？

- A. 把 TTL 改為 5 秒，讓所有旅館詳情都頻繁重新載入
- B. 調價時先刪除快取中的 key，再更新 Aurora
- C. 調價時只更新快取中的價格，再由夜間批次把快取的價格寫回 Aurora
- D. 調價時先提交 Aurora 的更新，再刪除該旅館的 cache key，並保留 TTL 作為安全網

> [!answer]- 答案：D
> **A ✗** 縮短全部 TTL 能讓價格更快更新，但正是團隊想避免的做法：命中率大幅下降，Aurora 讀取量暴增。
>
> **B ✗** 先刪快取再寫資料庫，中間如果有讀取請求進來，會把舊價格重新載入快取並留到 TTL 到期（最多 30 分鐘），反而更容易出錯。
>
> **C ✗** 這是 write-behind，價格在夜間寫回前只存在快取，快取故障或 eviction 就會遺失已確認的調價，而且 Aurora 上的資料整天都是錯的。
>
> **D ✓** 先寫 source of truth 再刪除 key，下一次讀取會 miss 並載入新價格；刪除比直接寫入新值更不容易因並行更新的順序而寫錯。TTL 保證即使刪除失敗，舊值最終也會過期。
>
> **考點**：SAA-3.3｜寫入後失效與 TTL 安全網

### 練習 28-3｜SAA｜單選｜即時排行榜的引擎選擇

Wanderly 要做「本週最熱門旅館」排行榜：每次預訂都要即時更新分數，首頁要能在毫秒內取得前 20 名，並能查詢任一旅館的名次。排行榜服務必須在一個 AZ 故障時自動恢復，團隊希望營運負擔最小。

哪個方案最合適？

- A. ElastiCache for Valkey，使用 sorted set，並啟用 Multi-AZ 與自動 failover
- B. ElastiCache for Memcached，在多個 AZ 各放一個節點，由應用程式排序
- C. 在 Aurora 建立排行榜資料表，每次首頁請求執行 `ORDER BY score DESC LIMIT 20`
- D. 用 CloudFront 快取首頁，TTL 設為 24 小時

> [!answer]- 答案：A
> **A ✓** Sorted set 會自動依分數排序，`ZINCRBY` 更新分數、`ZREVRANGE` 取前幾名、`ZREVRANK` 查名次都非常快。Valkey 的 replication group 支援 Multi-AZ 自動 failover，符合 AZ 故障自動恢復與低營運負擔。
>
> **B ✗** Memcached 只有簡單的 string，沒有排序資料結構；應用程式要自己讀出全部資料排序，效能差。Memcached 也沒有複寫與 failover，節點故障時資料直接遺失。
>
> **C ✗** 每個首頁請求都在資料庫排序，正是要避免的高成本重複查詢；高流量下會拖累 Aurora。
>
> **D ✗** 24 小時的 TTL 讓排行榜完全不即時，違反「每次預訂即時更新」。
>
> **考點**：SAA-3.3、SAA-2.2｜Valkey／Redis OSS sorted set 與 Multi-AZ

### 練習 28-4｜SAA｜單選｜Memcached 的適用情境

一個既有的內容管理系統已經使用 Memcached client 程式庫，以一致性雜湊把渲染好的 HTML 片段分散到多個節點。這些片段隨時可以從原始資料重新產生，遺失也沒有關係。團隊要搬到 AWS，希望使用受管服務、能用滿大節點的多個 CPU 核心，並且盡量不修改程式。

最合適的選擇是什麼？

- A. MemoryDB，因為它提供跨 AZ 交易日誌保護每一筆快取資料
- B. ElastiCache for Valkey，並啟用 cluster mode enabled 與每個 shard 兩個 replica
- C. ElastiCache for Memcached
- D. DynamoDB Accelerator（DAX）

> [!answer]- 答案：C
> **A ✗** MemoryDB 是耐久性資料庫，成本較高；這些片段可以重建、遺失無妨，不需要付耐久性的成本。
>
> **B ✗** Valkey 功能完整，若是新專案也是好選擇，但題目要求盡量不修改 Memcached 程式，而且不需要 replica、failover 等功能，多加 replica 只是增加成本。
>
> **C ✓** 需求完全符合 Memcached 的定位：簡單的 key-value、資料可遺失、多執行緒能利用多核心、client 端分散 key；既有 Memcached client 可以直接連 ElastiCache for Memcached。
>
> **D ✗** DAX 只能作為 DynamoDB 的快取，無法存放任意的 HTML 片段。
>
> **考點**：SAA-3.3、SAA-4.3｜Memcached 與 Valkey 選型

### 練習 28-5｜SAA｜單選｜Stateless web tier 與 session

Wanderly 的 web tier 是 Auto Scaling group 後面接 ALB，session 存在每台 EC2 的記憶體中，並啟用 ALB sticky session。每次晚上 scale in，部分使用者就被登出，購物車草稿也消失。團隊要求 session 讀寫延遲在 1 毫秒以內，並且使用受管服務。

最合適的改善方式是什麼？

- A. 延長 sticky session 的 cookie 有效時間，讓使用者固定在同一台 EC2
- B. 把 session 存到 ElastiCache for Valkey（啟用 Multi-AZ），設定符合閒置登出時間的 TTL，讓 EC2 成為 stateless
- C. 把 session 寫入每台 EC2 的 EBS volume，scale in 前先做 snapshot
- D. 關閉 Auto Scaling 的 scale in，只允許 scale out

> [!answer]- 答案：B
> **A ✗** Sticky session 只是把使用者固定在某台 EC2；那台 EC2 被 scale in 或故障時，session 一樣會消失。延長 cookie 時間不能解決根因。
>
> **B ✓** 把 session 外部化到 ElastiCache 後，任何 EC2 都能讀到任何使用者的 session，scale in 不再影響登入狀態；in-memory 讀寫可以達到 sub-millisecond，TTL 自然實作閒置登出，Multi-AZ 讓 AZ 故障時也能 failover。
>
> **C ✗** EBS 綁定單一 instance 與 AZ，其他 EC2 讀不到；snapshot 還原既慢又複雜，完全不適合即時 session。
>
> **D ✗** 停止 scale in 會讓成本隨尖峰只增不減，而且 instance 故障時 session 仍會遺失。
>
> **考點**：SAA-2.1、SAA-3.3｜session 外部化與 stateless 設計

### 練習 28-6｜SAA｜單選｜整點同時失效

Wanderly 的活動頁快取有約 5,000 個熱門 key，全部在活動開始時建立，TTL 統一為 300 秒。監控顯示每隔 5 分鐘 Aurora 的 CPU 就突然衝到 100% 數秒，同一時間 ElastiCache 的記憶體使用率只有 40%，`Evictions` 為 0。

哪個做法最能直接處理問題的根因？

- A. 把 ElastiCache 換成更大的 node type，讓更多 key 留在記憶體中
- B. 把 `maxmemory-policy` 改為 `noeviction`，避免 key 被丟掉
- C. 在 TTL 加上隨機抖動，並讓同一個 key 同時未命中時只有一個請求回資料庫載入
- D. 為 Aurora 增加 read replica，並讓應用程式在 miss 後立即無限重試

> [!answer]- 答案：C
> **A ✗** 記憶體使用率只有 40% 且沒有 eviction，代表記憶體不是問題。更大的節點不會改變所有 key 在同一時間過期的事實。
>
> **B ✗** Eviction 和 TTL 過期是兩種不同機制，`noeviction` 不會讓已設定 TTL 的 key 不過期；而且目前根本沒有 eviction。
>
> **C ✓** 問題是 cache stampede：大量 key 在同一秒過期，所有 miss 同時打向 Aurora。TTL jitter 讓過期時間分散，request coalescing 讓同一 key 只有一個請求回源，直接消除尖峰。
>
> **D ✗** Read replica 能分擔部分讀取，但沒有處理同時過期的根因；無限重試會進一步放大尖峰負載。
>
> **考點**：SAA-3.3、SAA-2.2｜cache stampede 與 TTL jitter

### 練習 28-7｜SAA｜單選｜DynamoDB 的微秒級讀取

Wanderly 的會員服務把會員資料存在 DynamoDB，讀取量非常大且大多是重複讀取同一批會員，目前讀取延遲是個位數毫秒。產品團隊要求降到微秒級，同時讀取可以接受最終一致；開發團隊希望程式碼的改動越少越好。

最合適的方案是什麼？

- A. 在應用程式中實作 ElastiCache for Redis OSS 的 cache-aside，並撰寫 key 失效邏輯
- B. 把 DynamoDB 表改為 provisioned capacity 並大幅提高 RCU
- C. 啟用 DynamoDB global tables，把資料複製到多個 Region
- D. 部署 DynamoDB Accelerator（DAX），把應用程式的 DynamoDB client 換成 DAX client

> [!answer]- 答案：D
> **A ✗** ElastiCache 可以達到類似延遲，但需要自己設計 key、寫 cache-aside 與失效邏輯，程式改動遠多於 DAX。
>
> **B ✗** 增加 RCU 提高的是吞吐量上限，不會把單次讀取延遲從毫秒降到微秒。
>
> **C ✗** Global tables 用於多 Region 複寫與就近讀取，不會讓同一 Region 的讀取變成微秒級。
>
> **D ✓** DAX 是 DynamoDB API 相容的 in-memory read-through 快取，把 eventually consistent reads 降到微秒級，只要換用 DAX client，程式邏輯幾乎不用改。
>
> **考點**：SAA-3.3｜DAX 與 ElastiCache 的選擇

### 練習 28-8｜SAA｜單選｜命中率下降的原因

Wanderly 的 ElastiCache for Valkey 叢集（cluster mode disabled，單一 shard）上線三個月後，命中率從 95% 掉到 70%。CloudWatch 顯示 `DatabaseMemoryUsagePercentage` 長期在 98% 以上，`Evictions` 持續上升，`EngineCPUUtilization` 只有 20%。業務量在這段時間成長了兩倍，key 與 TTL 設計沒有改變。

最合適的處理方式是什麼？

- A. 擴充快取記憶體，例如換成更大的 node type，或改用 cluster mode enabled 增加 shard
- B. 增加兩個 read replica，讓讀取分散到 replica
- C. 把所有 key 的 TTL 延長為原本的三倍
- D. 關閉 Multi-AZ 以釋放 replica 使用的記憶體

> [!answer]- 答案：A
> **A ✓** 記憶體滿、eviction 持續上升而 CPU 很低，代表工作集已經超過快取容量，常用資料被擠掉才導致命中率下降。擴充總記憶體（scale up 或增加 shard）能讓工作集重新放得下。
>
> **B ✗** Replica 保存的是 primary 的完整複本，不會增加可用的總記憶體；CPU 也不是瓶頸。
>
> **C ✗** 延長 TTL 會讓更多資料停留在已經滿的記憶體中，eviction 只會更嚴重。
>
> **D ✗** Replica 在另一個節點上，不占用 primary 的記憶體；關閉 Multi-AZ 只會讓叢集失去 failover 能力。
>
> **考點**：SAA-3.3｜eviction 與快取容量

### 練習 28-9｜SAA｜選兩項｜讓 failover 真的生效

Wanderly 的 ElastiCache for Valkey 叢集目前只有一個位於 AZ-a 的 primary node，應用程式設定中寫的是該節點的 node endpoint。一次 AZ-a 的故障讓快取中斷了 20 分鐘，恢復後快取是空的。團隊希望下次 AZ 故障時快取能在短時間內自動恢復。

哪兩個變更是必要的？（選兩項）

- A. 每天建立手動 snapshot，故障時從 snapshot 還原新叢集
- B. 在不同 AZ 新增 replica，並啟用 Multi-AZ 與 automatic failover
- C. 把 `maxmemory-policy` 改為 `allkeys-lru`
- D. 在應用程式中把 node endpoint 的 IP 位址固定寫入設定檔
- E. 讓應用程式改用 primary endpoint，並設定合理的連線逾時與自動重連

> [!answer]- 答案：B、E
> **A ✗** Snapshot 能在叢集遺失時還原資料，但還原需要時間且需人工操作，無法提供「短時間內自動恢復」。
>
> **B ✓** 沒有 replica 就沒有可以提升的對象。在其他 AZ 放 replica 並啟用 Multi-AZ automatic failover，primary 故障時 ElastiCache 會自動提升 replica。
>
> **C ✗** Eviction policy 決定記憶體滿時丟哪些 key，與故障恢復無關。
>
> **D ✗** 固定寫死節點 IP 讓應用程式在 failover 後仍連到舊節點，問題反而更嚴重。
>
> **E ✓** Failover 時 primary endpoint 的 DNS 會改指向新 primary；應用程式必須使用這個 endpoint，並在連線中斷後重新連線，否則仍會卡在舊連線上。
>
> **考點**：SAA-2.2｜Multi-AZ automatic failover 的前提

### 練習 28-10｜SAA｜單選｜流量難以預測的新服務

Wanderly 推出 AI 行程推薦服務，需要一個 Valkey 相容的快取保存推薦結果。服務剛上線，流量可能在幾天內從每秒數百次變成數萬次，也可能長期很低。團隊沒有人力做容量規劃，希望快取能承受 AZ 故障，並且以 LEAST operational overhead 達成。

最合適的做法是什麼？

- A. 建立 node-based 叢集，選最大的 node type 並配置 5 個 replica 以應付任何尖峰
- B. 建立 ElastiCache Serverless（Valkey），並設定用量上限避免帳單失控
- C. 在 EC2 Auto Scaling group 上自行安裝 Valkey，並撰寫腳本處理 resharding
- D. 建立 node-based 叢集，並購買 3 年期 reserved nodes 降低成本

> [!answer]- 答案：B
> **A ✗** 一開始就配置最大規格能撐住尖峰，但在流量長期很低時非常浪費，而且之後仍需要人工調整。
>
> **B ✓** ElastiCache Serverless 不需選 node type 或 shard 數，會依流量自動擴縮，資料預設跨多個 AZ 複寫，按實際用量計費；設定用量上限可以控制成本風險，營運負擔最低。
>
> **C ✗** 自建 Valkey 需要自己處理 patch、failover、resharding 與監控，營運負擔最高。
>
> **D ✗** Reserved nodes 適合長期穩定的負載；對流量完全不確定的新服務做 3 年承諾，風險很高，也沒有解決容量規劃問題。
>
> **考點**：SAA-3.3、SAA-4.3｜ElastiCache Serverless 的使用時機

### 練習 28-11｜SAP｜單選｜Redis 相容的主要資料庫

Wanderly 的庫存團隊要重新設計即時房間庫存服務。他們想直接使用 Redis 的 hash 與 sorted set 作為**唯一**的資料存放處，不再另外維護關聯式資料庫；讀取需要微秒級延遲、寫入可以接受個位數毫秒；任何已回應成功的扣庫存操作都不能因為節點或 AZ 故障而遺失。團隊希望使用受管服務並降低營運負擔。

最合適的方案是什麼？

- A. ElastiCache for Valkey，啟用 Multi-AZ automatic failover，並把自動備份保留期設為 35 天
- B. ElastiCache for Valkey，讓每筆寫入同時以 write-behind 方式非同步寫入 S3
- C. Amazon MemoryDB，使用 Multi-AZ 部署
- D. 在 EC2 上自建 Redis OSS，開啟 AOF 並把 `appendfsync` 設為 `always`

> [!answer]- 答案：C
> **A ✗** ElastiCache 的複寫是非同步的，failover 時可能遺失最近已確認的寫入；每天的自動備份也無法保護兩次備份之間的資料，不符合「已確認的寫入不能遺失」。
>
> **B ✗** Write-behind 在寫回之前資料只在快取中，故障時仍會遺失；從 S3 重建庫存狀態也不是可行的即時恢復方式。
>
> **C ✓** MemoryDB 相容 Valkey／Redis OSS，寫入在確認前已持久化到跨多個 AZ 的交易日誌，讀取為微秒級、寫入為個位數毫秒，定位就是可以作為主要資料庫的耐久性 in-memory 資料庫。
>
> **D ✗** 自建 Redis 搭配每次寫入 fsync 可以提高單機耐久性，但仍需自己處理跨 AZ 複寫、failover 與 patch，營運負擔高，而且單一 AZ 的磁碟無法承受 AZ 故障。
>
> **考點**：SAP-2.4、SAP-4.3｜MemoryDB 與 ElastiCache 的耐久性差異

### 練習 28-12｜SAP｜單選｜讀取熱點鍵

Wanderly 的 ElastiCache for Valkey 叢集使用 cluster mode enabled，共 8 個 shard，每個 shard 1 個 replica。每次促銷時，首頁的 `deals:tonight` 這一個 key 每秒被讀取 30 萬次，造成它所在 shard 的 `EngineCPUUtilization` 達 95%，其他 shard 都低於 20%。這個 key 每 30 秒才更新一次。團隊希望以最小成本解決，且不改變其他 key 的配置。

最合適的做法是什麼？

- A. 增加 shard 數到 16 個，讓 key 分散到更多節點
- B. 把該 shard 的 node type 換成更大的規格，其他 shard 維持不變
- C. 把整個叢集改為 cluster mode disabled，所有讀取集中到單一 primary
- D. 在每台應用程式伺服器加入存活數秒的 local cache 保存 `deals:tonight`，並讓 client 從 replica 讀取

> [!answer]- 答案：D
> **A ✗** 一個 key 永遠只屬於一個 hash slot、一個 shard，增加 shard 不會把單一 key 的讀取分散出去，只會增加成本。
>
> **B ✗** 同一個 replication group 中各 shard 使用相同的 node type，無法只放大一個 shard；放大整個叢集成本高，也只是延後問題。
>
> **C ✗** 改成單一 shard 會讓所有 key 的讀寫都集中到一個 primary，熱點更嚴重。
>
> **D ✓** 這是讀取熱點，而且資料每 30 秒才變一次。應用程式內的短 TTL local cache 能吸收絕大多數讀取，讓每台伺服器每幾秒才讀一次 ElastiCache；從 replica 讀取再把剩餘負載分給 replica，幾乎不增加成本。
>
> **考點**：SAP-2.5、SAP-3.3｜hot key 與多層快取

### 練習 28-13｜SAP｜選兩項｜快取的安全控制

Wanderly 的支付合規稽核要求：所有存放 session 與購物車資料的快取必須在傳輸中與靜態時加密；只有結帳服務可以寫入 `cart:` 開頭的 key，客服工具只能讀取 `session:` 開頭的 key，任何服務都不能執行 `FLUSHALL` 等危險指令；應用程式不得在程式碼中保存長期共用密碼。快取目前是 node-based ElastiCache for Valkey。

哪兩個做法能滿足需求？（選兩項）

- A. 啟用 in-transit（TLS）與 at-rest encryption（使用 KMS key），並以 security group 只允許兩個服務的 security group 連到快取 port
- B. 設定一組 AUTH token，透過環境變數提供給兩個服務
- C. 在 security group 規則中限制每個來源可以使用的 Valkey 指令
- D. 為每個服務建立 RBAC user，以 access string 限制 key pattern 與指令類別，並使用 IAM authentication 取得短期驗證 token
- E. 把快取改放到 public subnet，並用 WAF 過濾危險指令

> [!answer]- 答案：A、D
> **A ✓** TLS 與 at-rest encryption 滿足加密要求；security group 把網路可達性限制在兩個服務上。這是必要的網路與加密層，但它還不能區分指令權限。
>
> **B ✗** 單一 AUTH token 讓所有持有者擁有相同的完整權限，無法區分結帳與客服；而且它是長期共用密碼，違反要求。
>
> **C ✗** Security group 只根據來源、協定與 port 判斷，看不懂 Valkey 指令或 key 名稱。
>
> **D ✓** RBAC 讓每個 user 有自己的 access string，可以限制 key pattern（`~cart:*`、`~session:*`）與指令類別（例如 `+@read`、`-@dangerous`）；IAM authentication 以短期 token 取代長期密碼。
>
> **E ✗** ElastiCache 沒有 public endpoint 的設計，放到 public subnet 只會增加暴露面；WAF 處理的是 HTTP 流量，無法檢查 Valkey 協定。
>
> **考點**：SAP-2.3、SAP-1.2｜ElastiCache 加密、RBAC 與 IAM authentication

### 練習 28-14｜SAP｜單選｜大量資料、少量熱資料的成本最佳化

Wanderly 的價格比較服務在 node-based ElastiCache for Redis OSS 上保存 1.5 TB 的歷史價格資料，目前需要很多大記憶體節點。分析顯示每天只有約 15% 的 key 被頻繁存取，其餘偶爾被讀取時可以接受稍高的延遲。工作負載穩定且預計長期使用。財務團隊要求大幅降低成本，且不想重寫應用程式。

哪個做法最能降低成本？

- A. 升級到 Valkey，改用支援 data tiering 的節點類型讓冷資料移到本機 SSD，並為穩定的節點購買 reserved nodes
- B. 改用 ElastiCache for Memcached，因為它沒有複寫成本
- C. 把所有資料移到 MemoryDB 以獲得耐久性
- D. 把叢集改為 ElastiCache Serverless，讓它自動把冷資料刪除

> [!answer]- 答案：A
> **A ✓** Valkey 與 Redis OSS 相容且單價較低；data tiering 讓只有熱資料留在記憶體、冷資料放在本機 SSD，適合「資料量大、熱資料比例小、冷資料可接受稍高延遲」；穩定工作負載搭配 reserved nodes 再取得長期折扣。應用程式不需重寫。
>
> **B ✗** Memcached 沒有 data tiering，1.5 TB 仍需全部放在記憶體；而且應用程式若使用 Redis 資料結構就必須重寫。
>
> **C ✗** MemoryDB 提供耐久性，但成本更高，題目沒有耐久性需求。
>
> **D ✗** Serverless 依儲存的資料量計費，1.5 TB 仍要付費；它不會自動刪除冷資料，對穩定的大型工作負載也不一定較便宜。
>
> **考點**：SAP-2.6、SAP-3.5｜data tiering、Valkey 與 reserved nodes

### 練習 28-15｜SAP｜單選｜跨 Region 低延遲讀取

Wanderly 在東京的 node-based ElastiCache for Valkey 保存熱門旅館與匯率資料，這些資料只由東京的後台服務寫入。新開的新加坡 Region 應用程式需要以低延遲讀取相同資料，可以接受約一秒的延遲；東京 Region 發生災難時，新加坡要能在短時間內接手成為可寫入的快取。團隊希望不撰寫自訂同步程式。

最合適的方案是什麼？

- A. 每 5 分鐘從東京建立 snapshot 並匯出到 S3，再複製到新加坡還原新叢集
- B. 建立 ElastiCache Global Datastore，以東京為 primary cluster、新加坡為 secondary cluster，災難時提升新加坡叢集
- C. 讓新加坡的應用程式直接透過 Transit Gateway 跨 Region 連到東京的快取
- D. 在兩個 Region 各自建立 ElastiCache，並讓後台服務同時寫入兩邊

> [!answer]- 答案：B
> **A ✗** Snapshot 匯出、複製與還原至少需要數分鐘，資料延遲遠超過一秒，而且需要大量自訂流程。
>
> **B ✓** Global Datastore 把 primary cluster 的資料非同步複寫到其他 Region 的 secondary cluster，延遲通常在一秒以內，secondary 提供本地低延遲讀取；primary Region 故障時可以把 secondary 提升為 primary。不需要自訂同步程式。
>
> **C ✗** 跨 Region 讀取每次都要付出跨 Region 的網路延遲，失去本地快取的意義；東京故障時新加坡也一起失去快取。
>
> **D ✗** 雙寫需要自訂程式，還要處理一邊成功、一邊失敗造成的不一致，正是題目希望避免的。
>
> **考點**：SAP-2.2、SAP-2.5｜ElastiCache Global Datastore

### 練習 28-16｜SAP｜選兩項｜分層快取設計

Wanderly 的全球使用者抱怨旅館頁面載入慢。頁面由三部分組成：旅館照片與 JS／CSS（所有人相同）、旅館基本資訊與評分（所有人相同、每 10 分鐘更新）、會員專屬價格與收藏狀態（每個人不同）。目前所有請求都經 ALB 打到東京的應用程式，再查 Aurora。團隊希望改善全球延遲並降低 Aurora 負載，且不能讓任何使用者看到別人的個人化資料。

哪兩個做法最合適？（選兩項）

- A. 在 CloudFront 快取所有頁面回應，並把 cache key 設為只包含 URL 路徑，以獲得最高命中率
- B. 把 Aurora 換成 DynamoDB，再在前面加上 DAX
- C. 用 CloudFront 快取照片、JS／CSS 以及旅館基本資訊的 API 回應，cache key 只包含影響內容的參數，並且不快取個人化 API
- D. 只在應用程式伺服器的記憶體中快取所有資料，不使用分散式快取
- E. 個人化價格與收藏狀態由應用程式透過 ElastiCache 以 cache-aside 快取（key 包含會員 ID），旅館基本資訊在 Aurora 更新後刪除對應 key

> [!answer]- 答案：C、E
> **A ✗** Cache key 只包含路徑時，所有人的個人化頁面會被當成同一個物件，第一個使用者的會員價格會被快取並顯示給其他人，違反隱私要求。
>
> **B ✗** 更換資料庫的成本與風險很高，題目沒有理由需要這麼大的改變；DAX 也不處理全球延遲。
>
> **C ✓** 所有人相同的內容最適合在全球 edge 快取，能同時改善延遲與減少回源；只把真正影響內容的參數放進 cache key，並把個人化 API 排除在快取之外，避免資料外洩。
>
> **D ✗** 每台伺服器各自快取會造成大量重複載入與不一致，scale out 時新伺服器全部冷啟動，命中率低。
>
> **E ✓** 個人化資料不能在 edge 共用，但可以在應用程式層以 ElastiCache 快取，cache key 包含會員 ID 確保隔離；旅館資訊在更新後刪除 key，讓應用程式層資料保持新鮮。
>
> **考點**：SAP-2.5、SAP-3.3｜CloudFront 與 ElastiCache 分層快取
