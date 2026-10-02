---
chapter: 32
title: 並行效能、Thread Safety 與記憶體模型入門
part: 9
---

# 第 32 章　並行效能、Thread Safety 與記憶體模型入門

> [!abstract] 本章地圖
> **核心問題**：程式已經沒有 race 了，為什麼加更多 thread 反而變慢？哪些函式可以放心在多個 thread 裡同時呼叫？一個 thread 寫入的資料，另一個 thread 什麼時候「看得到」？
>
> **你會學到**：
> - 用 speedup、efficiency 量測平行程式，並用 Amdahl 與 Gustafson 定律手算可擴展的上限
> - 說出 mutex、atomic、context switch 與 cache line 在核心之間搬家各自的代價，並解釋「加 thread 反而變慢」
> - 認出 false sharing，並用 padding 或 per-thread 資料修好它
> - 分辨 thread-safe 與 reentrant，認得 `strtok`、`localtime`、`rand` 這類 thread-unsafe 函式並換成安全版本
> - 用 C11 atomic 與 acquire／release 正確地在 thread 之間發布資料，知道 lock-free 的代價
>
> **前置知識**：第 16 章（cache line、寫入策略）、第 17 章（locality 與 false sharing 預告）、第 30 章（thread 與 thread pool）、第 31 章（race、mutex、semaphore、deadlock）
>
> **對應 CS:APP 3e**：第 12 章 12.6–12.7 節

## 32.1 故事：thread 加倍，吞吐量卻掉了兩成

第 31 章結束時，小安修好了 `thumbd` 快取計數器的 race：所有共享的統計數字都改成用一把 mutex 保護，ThreadSanitizer 也不再報錯。拾光相簿的流量在年底活動前預估會成長一倍，產品經理 Lisa 問能不能先把 `thumbd` 的容量拉高。

小安的想法很直接：機器有 8 個核心，thread pool 目前開 8 個 worker，那就開到 16 個、32 個。壓測結果卻讓人困惑：

| worker 數 | 每秒處理請求數 | p99 延遲 | CPU 使用率 |
|---|---|---|---|
| 8 | 1,900 | 38 ms | 約 760% |
| 16 | 1,750 | 71 ms | 約 790% |
| 32 | 1,520 | 140 ms | 約 795% |

CPU 已經幾乎全滿，吞吐量卻不升反降，延遲還翻倍。小安又注意到另一件怪事：log 裡偶爾會出現時間戳記錯亂的行，例如某一行寫著「03:15:42」，緊接著下一行卻是「03:15:07」，而且只在 thread 多的時候出現。

老周看完數字說：「沒有 race 只代表結果正確，不代表跑得快。你現在遇到的是三件事疊在一起：一把每個請求都要搶的大鎖、幾個看起來互不相干其實擠在同一條 cache line 上的計數器，以及一個不是 thread-safe 的時間函式。」這一章就沿著這三件事，回答「並行程式怎麼量、為什麼會慢、哪些函式可以安心共用、以及 thread 之間的寫入什麼時候看得見」。

## 32.2 量測平行效能：speedup 與 efficiency

在討論「為什麼慢」之前，要先能說清楚「多快才算快」。平行程式的效能用兩個數字描述。

**Speedup**（加速比）是同一份工作在 1 個核心上的時間除以在 p 個核心上的時間：S_p = T_1 / T_p。例如縮放 1,000 張圖，單核心要 40 秒、4 核心要 12 秒，speedup 就是 40 / 12 ≈ 3.33。如果 T_1 用的是「平行版程式只開 1 個 thread」的時間，叫 **relative speedup**；如果用的是最好的循序版本（沒有任何鎖與 thread 開銷），叫 **absolute speedup**。後者比較誠實，因為平行版程式即使只開 1 個 thread，也要付加鎖、建立 thread 的成本。

**Efficiency**（效率）是 speedup 除以核心數：E_p = S_p / p，代表每個核心平均有多少比例的時間在做有用的事。上面的例子 E_4 = 3.33 / 4 ≈ 83%。效率 100% 表示完美的線性加速，實務上幾乎不會發生；剩下的部分花在同步、等待、通訊與負載不平均上。

用 `thumbd` 的批次重算縮圖工具做一次完整手算。量到的時間如下：

| 核心數 p | T_p（秒） | speedup S_p = T_1 / T_p | efficiency E_p = S_p / p |
|---|---|---|---|
| 1 | 48.0 | 1.00 | 100% |
| 2 | 25.3 | 48.0 / 25.3 ≈ 1.90 | 95% |
| 4 | 13.7 | 48.0 / 13.7 ≈ 3.50 | 88% |
| 8 | 8.2 | 48.0 / 8.2 ≈ 5.85 | 73% |
| 16 | 7.9 | 48.0 / 7.9 ≈ 6.08 | 38% |

從 8 到 16 核心，時間只少了 0.3 秒，效率從 73% 掉到 38%。這種「越往後加核心越沒用」的形狀幾乎出現在所有平行程式上，畫成長條圖長這樣：

```text
 核心數   speedup（█ 實測，░ 理想線性加速還差多少）
   1     █                                  1.00
   2     █▉                                 1.90（理想 2）
   4     ███▌░                              3.50（理想 4）
   8     █████▊░░                           5.85（理想 8）
  16     ██████░░░░░░░░░░                   6.08（理想 16）
         └ 每一格代表 speedup 1
```

實心部分是實測的 speedup，空心部分是離理想線性加速還差多少。核心越多，空心部分越長，這段差距就是這一章要找的東西。造成差距的原因可以分成兩類：一類是程式本質上就有不能平行的部分，下一節的 Amdahl 定律處理它；另一類是平行化本身帶來的額外成本（鎖、cache line 搬家、context switch），32.4 與 32.5 節處理它。

另外兩個名詞在讀論文或做容量規劃時常見。**Strong scaling**（強擴展）是問題大小固定、增加核心數，看時間能縮短多少，上表就是 strong scaling。**Weak scaling**（弱擴展）是每個核心分到的工作量固定、核心數與總工作量一起增加，看時間能不能維持不變。`thumbd` 這種線上服務比較接近 weak scaling：核心多了，我們期待的是能服務更多請求，而不是單一請求變快。

## 32.3 Amdahl 與 Gustafson：序列部分決定上限

第 1 章與第 14 章已經介紹過 **Amdahl's law**，這裡把它用在平行程式上。假設一個程式的執行時間中，比例 s 的部分只能循序執行（serial fraction），剩下 1 − s 可以完美平分給 n 個核心，那麼：

```text
S(n) = 1 / ( s + (1 − s) / n )
S(∞) = 1 / s
```

手算一次。批次工具中「掃描目錄、讀取清單、寫出彙總報告」只能單執行緒做，佔單核心時間的 5%，所以 s = 0.05：

```text
S(8)  = 1 / (0.05 + 0.95 / 8)  = 1 / (0.05 + 0.11875) = 1 / 0.16875 ≈ 5.93
S(16) = 1 / (0.05 + 0.95 / 16) = 1 / (0.05 + 0.059375) = 1 / 0.109375 ≈ 9.14
S(∞)  = 1 / 0.05 = 20
```

5% 的循序部分，就讓 16 核心最多只有 9 倍、無限多核心也只有 20 倍。對照 32.2 節的實測值，8 核心的 5.85 幾乎貼著 Amdahl 的上限 5.93；16 核心的 6.08 則明顯低於 9.14，多出來的差距來自平行化本身的額外成本（32.4 節）。不管是哪一種，要再快都得先縮小 s 與同步成本，而不是加核心。

**Gustafson's law** 從另一個角度看。它觀察到：核心變多時，人們通常不是拿來把同一份工作做得更快，而是在同樣時間內做更大的工作。如果在 n 核心的系統上量到循序部分佔 s，那麼同樣時間內完成的工作量相當於單核心的：

```text
S_scaled(n) = s + (1 − s) × n
```

同樣 s = 0.05、n = 16：S_scaled = 0.05 + 0.95 × 16 = 15.25。兩個定律並不矛盾，它們回答的是不同的問題：

| | Amdahl | Gustafson |
|---|---|---|
| 固定的是什麼 | 問題大小 | 執行時間 |
| 回答的問題 | 同一份工作最多能快幾倍 | 同樣時間內能多做幾倍的工作 |
| s 在哪裡量 | 單核心執行時的循序比例 | n 核心執行時的循序比例 |
| s = 5%、n = 16 | 9.14 | 15.25 |
| 對 `thumbd` 的意義 | 單一超大圖的縮放延遲能降多少 | 一台機器每秒能多服務多少請求 |

下面的 Python 程式把兩個公式算成表，方便你對照：

```python
# Amdahl（固定問題大小）與 Gustafson（固定時間、問題隨核心數變大）
def amdahl(serial, n):
    return 1 / (serial + (1 - serial) / n)

def gustafson(serial, n):
    return serial + (1 - serial) * n

print(f"{'核心數':>4} | {'Amdahl s=5%':>11} | {'Amdahl s=20%':>12} | {'Gustafson s=5%':>14}")
for n in (1, 2, 4, 8, 16, 64):
    print(f"{n:>7} | {amdahl(0.05, n):>11.2f} | {amdahl(0.20, n):>12.2f} | {gustafson(0.05, n):>14.2f}")
print(f"上限（n → ∞）：s=5% 為 {1/0.05:.0f}x，s=20% 為 {1/0.20:.0f}x")
```

執行結果（macOS arm64，Python 3）：

```text
 核心數 | Amdahl s=5% | Amdahl s=20% | Gustafson s=5%
      1 |        1.00 |         1.00 |           1.00
      2 |        1.90 |         1.67 |           1.95
      4 |        3.48 |         2.50 |           3.85
      8 |        5.93 |         3.33 |           7.65
     16 |        9.14 |         4.00 |          15.25
     64 |       15.42 |         4.71 |          60.85
上限（n → ∞）：s=5% 為 20x，s=20% 為 5x
```

s = 20% 的那一欄特別值得看：64 核心只換到 4.71 倍。這就是為什麼「拿到更多核心」之前，先要問程式有多少部分是循序的。

### 鎖就是一段循序程式

對線上服務來說，最常見的「循序部分」不是程式開頭的初始化，而是**被鎖保護的 critical section**（臨界區，同一時間只允許一個 thread 執行的程式段）。不管有多少 worker，同一把鎖保護的程式段在時間軸上只能一段接一段執行。

這給了一個很好用的上限公式：如果每個請求都要持有同一把鎖 L 秒，那麼整個服務的吞吐量不可能超過 1 / L 個請求每秒，不管有幾個核心。回到 32.1 節，小安後來用 log 量到：每個請求在全域快取鎖裡平均停留 0.5 ms（因為把縮圖整塊 `memcpy` 進快取的動作寫在鎖裡面）。

```text
吞吐量上限 = 1 / 0.5 ms = 2,000 個請求／秒
8 個 worker、每個請求 CPU 時間約 4 ms → CPU 上限 = 8 / 4 ms = 2,000 個請求／秒
```

兩個上限剛好碰在一起，所以 8 個 worker 時跑到 1,900 已經接近天花板。再加 worker 不會讓鎖的上限變高，只會讓更多 thread 排隊等鎖，額外付出下一節要講的成本，吞吐量於是開始下降。修法是把 `memcpy` 移出鎖外：先在鎖外準備好整個快取項目，鎖裡只做「把指標掛進雜湊表」這一步，持有時間降到幾微秒，鎖的上限就遠高於 CPU 的上限了。

## 32.4 同步的成本：鎖、context switch 與 cache line 搬家

Amdahl 定律假設平行部分可以「完美平分」。現實中，讓多個 thread 協調一致本身就要付錢。這些成本由便宜到昂貴，大致有四層。

### 第一層：沒有競爭的 atomic 與 mutex

一個 **atomic 操作**（不可分割的操作，其他 thread 看不到它做到一半的狀態）在 x86-64 上通常是一條帶 `lock` 前綴的指令。下面用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables` 編譯一個普通遞增與一個 atomic 遞增：

```c
#include <stdatomic.h>
long plain_counter;
atomic_long atomic_counter;
void inc_plain(void)  { plain_counter++; }
void inc_atomic(void) { atomic_fetch_add_explicit(&atomic_counter, 1, memory_order_relaxed); }
```

```asm
inc_plain:
	incq	plain_counter(%rip)
	retq
inc_atomic:
	lock		incq	atomic_counter(%rip)
	retq
```

兩者只差一個 `lock`。注意 `inc_plain` 雖然也只有一條 `incq`，但它**不是** atomic：沒有 `lock` 前綴時，CPU 內部仍然是「讀出、加一、寫回」三步，兩個核心可以交錯執行（第 31 章的 progress graph）。`lock` 前綴要求這個核心在整個讀改寫期間獨佔那條 cache line。同一段 C 編譯成 ARM64 時，`atomic_fetch_add` 會變成 `ldxr`／`stxr` 的重試迴圈，或在支援 LSE 擴充（ARMv8.1 以後）的處理器上變成一條 `ldadd` 指令；概念相同，都是硬體保證的讀改寫。

沒有競爭時，一次 atomic 操作大約是數 ns 量級。**mutex**（互斥鎖）在沒有競爭時也很便宜：Linux 的 `pthread_mutex_lock` 底層是 **futex**（fast user-space mutex），鎖沒人拿時只在 user space 做一次 atomic 比較交換，不需要 system call。32.11 節會量到，在沒有競爭的情況下，一組 lock、遞增、unlock 只要幾 ns。

### 第二層：cache line 在核心之間搬家

真正的成本出現在多個核心**頻繁寫入同一條 cache line** 時。每個核心有自己的 L1、L2 cache（第 16 章），同一條 line 可能同時被好幾個核心快取。為了讓大家看到一致的值，硬體使用 **cache coherence protocol**（快取一致性協定），最常被拿來教學的是 **MESI**：每條 line 在每個核心的 cache 裡處於四種狀態之一。

| 狀態 | 意義 | 這個核心可以直接… |
|---|---|---|
| M（Modified） | 只有我有，而且我改過，記憶體裡的是舊值 | 讀、寫 |
| E（Exclusive） | 只有我有，和記憶體一致 | 讀；寫的話直接變成 M |
| S（Shared） | 好幾個核心都有唯讀副本 | 讀；要寫必須先讓別人的副本失效 |
| I（Invalid） | 我手上這份已經失效 | 都不行，要重新取得 |

規則的核心只有一句：**要寫一條 line，必須先讓其他核心的副本全部失效，自己獨佔它**。實際處理器用的是 MESI 的變體（例如 Intel 的 MESIF、AMD 的 MOESI），但這句規則不變。當兩個核心輪流寫同一條 line，這條 line 就會在兩個核心之間來回彈跳：

```text
 時間 →
 核心 0 的 L1：  [M: counter=5] ──失效──▶ [I]          ──取回──▶ [M: counter=7]
                       │                    ▲                      │
                       │ 核心 1 要寫，       │ 核心 0 又要寫，       │
                       │ 發出 invalidate    │ 再搶回來             │
                       ▼                    │                      ▼
 核心 1 的 L1：  [I]   ──取得──▶ [M: counter=6] ──失效──▶ [I]

 每一次「搶回來」都要經過核心之間的互連網路，代價是數十到上百個 cycle，
 而不是 L1 hit 的幾個 cycle。這種現象叫 cache line ping-pong。
```

所以「4 個 thread 一起對同一個 atomic 計數器加一」不但不會比 1 個 thread 快，通常還慢好幾倍：每次加一都要把 line 從另一個核心搶過來。32.11 節的實驗會看到，在我們的機器上這個情況只有單執行緒速度的五分之一左右。

### 第三層：搶不到鎖時，thread 要睡覺

當 mutex 被別人拿著，搶鎖的 thread 會透過 futex system call 請 kernel 把它放進等待佇列、換別的 thread 執行。有些實作會先在 user space 空轉（spin）一小段時間再睡，賭持有者很快就會放鎖，例如 glibc 的 adaptive mutex（`PTHREAD_MUTEX_ADAPTIVE_NP`）；glibc 預設類型的 mutex 則不空轉，搶不到就直接進 kernel 等待。持有者 unlock 時，如果有人在等，就要再呼叫一次 system call 喚醒對方。這牽涉到 **context switch**（第 20 章）：保存與恢復暫存器、切換 kernel stack，被喚醒的 thread 很可能被排到另一個核心，它的資料在新核心的 cache 裡全部是 miss。直接成本依平台大約是 1 到數 µs，間接的 cache 成本常常更大。

### 第四層：thread 比核心多

CPU-bound 的 worker（例如 `thumbd` 的縮放）數量超過核心數時，排程器只能輪流讓它們執行。每個 thread 的時間片用完就被換下來，工作集被下一個 thread 擠出 cache，換回來時又要重新載入。thread 越多，每個 thread 分到的連續執行時間越短，花在暖 cache 上的比例越高。這叫 **oversubscription**（超額訂閱）。

| 成本來源 | 量級（依平台而定） | 什麼時候出現 | 怎麼看到 |
|---|---|---|---|
| 無競爭的 atomic／mutex | 數 ns | 每次同步 | 通常看不到，可以忽略 |
| cache line ping-pong | 每次數十到上百 cycle | 多核心頻繁寫同一條 line | `perf c2c`、`perf stat` 的 cache miss |
| 鎖競爭導致睡眠與喚醒 | 每次 µs 級，含 system call 與 context switch | 熱門的鎖 | `pidstat -w`、`strace -c` 看 `futex` 次數 |
| oversubscription | 吞吐量下降、延遲上升 | CPU-bound thread 數 > 核心數 | `vmstat` 的 `cs` 與 run queue（`r` 欄） |

`thumbd` 從 8 個 worker 加到 32 個時，四層成本同時出現：全域鎖從「偶爾有人等」變成「隨時有十幾個人排隊」，每次 unlock 都要喚醒別人；32 個 CPU-bound thread 輪流使用 8 個核心；統計計數器所在的 cache line 在核心之間來回彈跳。下一節專門看最後這一項裡最難察覺的一種。

## 32.5 False sharing：沒有共享變數，卻在共享 cache line

小安修掉全域大鎖之後，想到另一個優化：與其讓所有 worker 搶一個統計計數器，不如每個 worker 自己有一格，最後再加總。

```c
struct worker_stats {
    long requests;     /* 這個 worker 處理過的請求數 */
    long bytes_out;    /* 送出的位元組數 */
};
struct worker_stats stats[8];   /* stats[i] 只有 worker i 會寫 */
```

邏輯上這完全正確：每個 worker 只寫自己的那一格，沒有任何兩個 thread 寫同一個變數，不需要鎖，也沒有 race。但效能幾乎沒有改善。原因要從記憶體布局看：

```text
 struct worker_stats 每個 16 bytes，8 個共 128 bytes
 位址：0        16       32       48       64       80       96       112      128
       ├────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┤
       │stats[0]│stats[1]│stats[2]│stats[3]│stats[4]│stats[5]│stats[6]│stats[7]│
       └────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘
       └──────────── cache line A（64 B）──┘└──────────── cache line B（64 B）──┘
         worker 0～3 都寫在 line A 裡             worker 4～7 都寫在 line B 裡
```

Cache coherence 是以 **line** 為單位，不是以變數為單位。worker 0 寫 `stats[0]` 時，必須獨佔整條 line A，worker 1、2、3 手上的 line A 全部失效；接著 worker 1 寫 `stats[1]`，又把 line A 搶走。四個 worker 寫的是四個不同的變數，硬體卻把它們當成在搶同一個東西。這叫 **false sharing**（偽共享）：程式邏輯上沒有共享，硬體層面卻在共享 cache line。

修法是讓每個 thread 頻繁寫入的資料各自佔一條 line：

```c
#include <stdalign.h>
#define CACHE_LINE 64          /* x86-64 常見值；Apple M 系列是 128 */
struct worker_stats {
    alignas(CACHE_LINE) long requests;   /* 整個 struct 對齊到 line 邊界 */
    long bytes_out;
};                             /* sizeof 會被補到 64 的倍數 */
struct worker_stats stats[8];  /* 每個 worker 各佔一條 line */
```

`alignas(CACHE_LINE)` 讓 struct 的對齊要求變成 64，編譯器會在結尾補 padding，使 `sizeof(struct worker_stats)` 成為 64 的倍數（第 10 章的對齊規則）。代價是多用一些記憶體：8 個 worker 從 128 bytes 變成 512 bytes，完全值得。

還有另一種更好的做法：根本不要讓統計資料放在共享的陣列裡。每個 worker 把計數放在自己的 local 變數或 **thread-local storage**（每個 thread 各有一份的變數，C11 寫成 `_Thread_local`），累積一段時間（例如每 1,000 個請求或每秒）再用一次 atomic 加到全域總數。這樣共享 line 被寫入的頻率降低了一千倍。

> [!warning] 常見誤解
> 「只要不同 thread 寫不同變數，就不會互相影響。」在正確性上是對的，在效能上不一定。效能看的是 cache line，相鄰的小變數（陣列元素、struct 欄位、連續宣告的全域變數）很容易落在同一條 line 上。另一個誤解是 cache line 一定是 64 bytes：大部分 x86-64 是 64 bytes，但 Apple M 系列回報 128 bytes（`sysctl hw.cachelinesize`），Linux 上可以看 `getconf LEVEL1_DCACHE_LINESIZE`。

False sharing 只在**頻繁寫入**時才嚴重。如果多個 thread 只是讀同一條 line，它可以在每個核心的 cache 裡都處於 S 狀態，大家各讀各的，完全沒有成本。所以唯讀的設定、查表用的常數陣列不需要 padding；需要 padding 的是每秒被寫入上百萬次的計數器、佇列的頭尾指標、鎖本身。

## 32.6 Thread safety：四類不安全的函式

32.1 節的第三個問題是 log 的時間戳記錯亂。這和效能無關，是正確性問題，而且第 31 章教的「找出共享變數、加鎖」不容易看出來，因為共享變數藏在函式庫裡面。

一個函式是 **thread-safe**（執行緒安全）的意思是：多個 thread 同時重複呼叫它，結果永遠和「一次只有一個 thread 呼叫」一樣正確。CS:APP 把 thread-unsafe 的函式分成四類，每一類的修法不同：

| 類別 | 問題 | 例子 | 修法 |
|---|---|---|---|
| 第 1 類：沒有保護共享變數 | 函式內讀寫全域或 static 變數，沒有加鎖 | 第 31 章不加鎖的 `cnt++` | 用 mutex 或 atomic 保護；函式本身與呼叫者都不用改介面 |
| 第 2 類：跨呼叫保存狀態 | 函式用 static 變數記住上一次呼叫的結果，下一次接著用 | `rand()` 用 static 種子；`strtok()` 記住上次切到哪裡 | 只能改介面，讓呼叫者自己保存狀態：`rand_r(&seed)`、`strtok_r(s, delim, &saveptr)` |
| 第 3 類：回傳指向 static 資料的指標 | 結果放在函式內的 static buffer，下一次呼叫會覆寫 | `ctime()`、`localtime()`、`gethostbyname()`、`inet_ntoa()` | 改用呼叫者提供 buffer 的 `_r` 版本；或在呼叫端用 lock-and-copy |
| 第 4 類：呼叫了 thread-unsafe 函式 | 自己沒有共享狀態，但內部呼叫了上面三類的函式 | 自己寫的 `log_line()` 呼叫了 `localtime()` | 找出被呼叫的函式並換成安全版本 |

`thumbd` 的時間戳記錯亂正是第 3 類加第 4 類。log 函式長這樣：

```c
void log_line(const char *msg) {
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);      /* 回傳指向 static struct tm 的指標 */
    fprintf(logf, "%02d:%02d:%02d %s\n", tm->tm_hour, tm->tm_min, tm->tm_sec, msg);
}
```

`localtime` 把結果放在一個函式庫內部的 static `struct tm` 裡，回傳它的位址。worker A 拿到指標、還沒讀完三個欄位，worker B 也呼叫 `localtime`，同一塊 static 記憶體被覆寫成 B 的時間。A 印出的可能是 A 的小時、B 的分鐘與秒，甚至是更早一個 thread 留下的值。thread 越多，兩個呼叫重疊的機率越高，所以只在高併發時出現。

修法是改用 `localtime_r`，由呼叫者提供 `struct tm`：

```c
void log_line(const char *msg) {
    time_t now = time(NULL);
    struct tm tm;                          /* 每次呼叫在自己的 stack 上一份 */
    localtime_r(&now, &tm);
    fprintf(logf, "%02d:%02d:%02d %s\n", tm.tm_hour, tm.tm_min, tm.tm_sec, msg);
}
```

第 3 類還有一種不改介面的權宜做法，叫 **lock-and-copy**：用一把 mutex 包住「呼叫 unsafe 函式、把結果複製到自己的 buffer」這兩步。它能用，但所有呼叫者都要遵守同一把鎖，而且重新引入了 32.3 節講的循序瓶頸，只適合找不到 `_r` 版本的老函式庫。

### 一個容易漏掉的第 2 類：`strtok`

`thumbd` 解析 query string 時用了 `strtok`：

```c
char *key = strtok(query, "&");         /* 第一次：傳入字串 */
while (key) {
    handle_param(key);
    key = strtok(NULL, "&");            /* 之後：傳 NULL，表示「接著上次的位置」 */
}
```

「接著上次的位置」記在 `strtok` 內部的 static 指標裡，所有 thread 共用同一個。兩個 worker 同時解析各自的 query string，就會切到對方的字串上。這類 bug 的症狀非常詭異：偶爾某個請求拿到別人的參數，例如縮圖尺寸是另一個使用者要求的大小。修法是 `strtok_r`，把「上次的位置」交給呼叫者保存：

```c
char *saveptr;
for (char *key = strtok_r(query, "&", &saveptr); key; key = strtok_r(NULL, "&", &saveptr))
    handle_param(key);
```

## 32.7 Reentrant 函式與常見的 thread-unsafe 函式庫

### Reentrant：比 thread-safe 更強的保證

**Reentrant function**（可重入函式）是一種特別的 thread-safe 函式：它完全不碰任何共享資料，所有狀態都來自參數與 local 變數。因為沒有共享資料，就不需要同步，多個 thread 同時執行它也不會互相影響，而且也可以在執行到一半時被「再進入一次」（例如被 signal handler 打斷後，handler 又呼叫同一個函式）。

```text
 ┌──────────────────────────────── 所有函式 ────────────────────────────────┐
 │                                                                         │
 │   ┌──────────────── thread-safe 函式 ────────────────┐                  │
 │   │                                                  │   thread-unsafe  │
 │   │   用鎖保護共享資料的函式      ┌── reentrant ──┐   │   函式            │
 │   │   （例如 malloc、printf）     │ 不碰共享資料  │   │   （strtok、       │
 │   │                              │ （strtok_r、  │   │    localtime、    │
 │   │                              │  localtime_r）│   │    rand）         │
 │   │                              └───────────────┘   │                  │
 │   └──────────────────────────────────────────────────┘                  │
 └─────────────────────────────────────────────────────────────────────────┘
```

這張圖的重點是包含關係：reentrant 是 thread-safe 的子集合。用鎖做到的 thread-safe 函式（例如 glibc 的 `malloc`）在多個 thread 之間是安全的，但它不是 reentrant：如果某個 thread 在 `malloc` 裡持有鎖時被 signal 打斷，handler 又呼叫 `malloc`，同一個 thread 會試圖再拿一次自己已經拿著的鎖，結果是 deadlock。這正是第 22 章說 signal handler 只能呼叫 async-signal-safe 函式的原因之一。

CS:APP 還區分兩種 reentrant：**explicitly reentrant**（明確可重入）指所有參數都是傳值、沒有指標，不可能碰到共享資料；**implicitly reentrant**（隱含可重入）指參數裡有指標，只要呼叫者傳進來的是各自不共享的資料，函式就是可重入的。`localtime_r` 屬於後者：如果兩個 thread 傳進同一個 `struct tm *`，它一樣會出錯，責任落在呼叫者身上。

為什麼 reentrant 函式受歡迎？除了能在 signal handler 中使用，它們通常也比較快：沒有鎖，就沒有 32.4 節的任何同步成本。設計自己的函式庫時，「把狀態放在呼叫者傳入的 context 結構」幾乎永遠比「函式內部用 static 變數再加鎖」好。

### 常見的 thread-unsafe 函式與替代品

| 函式 | 類別 | 替代品 | 備註 |
|---|---|---|---|
| `rand` | 2 | `rand_r`，或每個 thread 各自的亂數產生器 | `rand_r` 的品質很差，正式用途改用更好的演算法 |
| `strtok` | 2 | `strtok_r` | 也會修改原字串，要注意 |
| `asctime`、`ctime` | 3 | `asctime_r`、`ctime_r`，或 `strftime` 搭配 `localtime_r` | |
| `localtime`、`gmtime` | 3 | `localtime_r`、`gmtime_r` | |
| `gethostbyname`、`gethostbyaddr` | 3 | `getaddrinfo`、`getnameinfo`（第 28 章） | 新程式本來就該用後者，還支援 IPv6 |
| `inet_ntoa` | 3 | `inet_ntop` | |
| `strerror` | 3（依實作而定） | `strerror_r`（注意 glibc 有 GNU 與 POSIX 兩種版本） | POSIX 不要求它 thread-safe；glibc 2.32 起標為 MT-Safe，但舊版 glibc 與其他平台不保證 |
| `getenv`／`setenv` | 1 | 啟動時讀完環境變數，之後不再呼叫 `setenv` | 一個 thread `setenv` 時，另一個 thread `getenv` 可能讀到被釋放的字串 |

有幾件事在 POSIX 系統上是安全的，不必過度擔心：`errno` 在多執行緒程式中是 **thread-local** 的，每個 thread 各有一份；`malloc`／`free` 是 thread-safe 的（現代 allocator 還會為不同 thread 準備不同的 arena，減少搶鎖，第 25 章）；`printf` 這類 stdio 函式會對 `FILE` 加鎖，所以一次呼叫印出的一行不會和別人的一行交錯，但兩次呼叫之間可能被插入別人的輸出。

要確認某個函式是否 thread-safe，最可靠的方法是查 man page：`pthreads(7)` 列出 POSIX 不要求 thread-safe 的函式清單；Linux man-pages 大多數函式頁面的 ATTRIBUTES 段落會寫出 `MT-Safe` 或 `MT-Unsafe`，以及原因（例如 `MT-Unsafe race:strtok`）。

### 另一種 race：把迴圈變數的位址傳給 thread

在講記憶體模型之前，再看一個 CS:APP 特別指出、新手幾乎一定會寫錯的例子。它不是函式庫的問題，而是**生命週期**與**共享**的問題：

```c
// not-runnable
for (int i = 0; i < N; i++)
    pthread_create(&tid[i], NULL, worker, &i);   /* bug：所有 thread 拿到同一個 &i */
```

每個新 thread 拿到的都是同一個變數 `i` 的位址。主執行緒繼續跑迴圈、把 `i` 加一時，新 thread 可能還沒來得及讀 `*arg`，於是好幾個 thread 讀到同一個編號，有些編號沒人拿到。修法是讓每個 thread 有自己的參數：用一個 `int ids[N]` 陣列，傳 `&ids[i]`；或用 `malloc` 為每個 thread 配置一份，由 thread 自己 `free`。這也說明了「哪些變數是共享的」看的不是變數宣告在哪裡，而是它的位址被交給了誰。

## 32.8 記憶體模型入門：為什麼別的 thread 看到的順序不一樣

到目前為止，我們假設一個 thread 寫入的值，其他 thread「之後」就看得到，而且看到的順序和程式碼順序一樣。這個假設叫 **sequential consistency**（循序一致性）：所有 thread 的操作好像被排成一條總順序，每個 thread 自己的操作在總順序裡維持程式碼順序。它很直覺，但現代的編譯器和 CPU 為了速度都不完全遵守它。

### 編譯器會重排與刪除

先看一個用普通變數做「通知」的例子：一個 thread 設定 `ready = 1` 通知另一個 thread 資料好了，另一個 thread 在迴圈裡等它。

```c
int ready;      /* 沒有 atomic：data race */
int payload;
int wait_plain(void) {
    while (!ready) { }
    return payload;
}
```

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables` 編譯：

```asm
wait_plain:
	cmpl	$0, ready(%rip)
	je	.LBB0_1
	movl	payload(%rip), %eax
	retq
.LBB0_1:
	jmp	.LBB0_1
```

編譯器只讀了 `ready` 一次：如果是 0，就跳到 `.LBB0_1`，那是一個**永遠跳回自己**的無窮迴圈。從編譯器的角度，這是合法的最佳化：在單執行緒的世界裡，迴圈裡沒有任何東西會改變 `ready`，讀一次和讀一萬次結果一樣。C 標準規定，兩個 thread 沒有同步地存取同一個變數、而且其中至少一個是寫入，叫 **data race**，是 undefined behavior；編譯器可以假設它不會發生。

### CPU 也會重排

即使編譯器完全照程式碼順序產生指令，CPU 也不一定照順序讓其他核心看到。原因之一是 **store buffer**（寫入緩衝區）：核心執行 store 時，先把值放進自己的 store buffer，稍後才寫進 cache；在這之前，其他核心看不到這個值，但後面的 load 已經可以先執行（第 13 章的 out-of-order 執行）。

```text
 初始：x = 0, y = 0

 核心 0                          核心 1
 ┌──────────────────┐           ┌──────────────────┐
 │ x = 1            │──┐        │ y = 1            │──┐
 │ r0 = y           │  │        │ r1 = x           │  │
 └──────────────────┘  │        └──────────────────┘  │
          │            ▼                 │            ▼
          │   store buffer: [x=1]        │   store buffer: [y=1]
          │   （還沒寫進 cache）           │   （還沒寫進 cache）
          ▼                              ▼
     讀 y：cache 裡還是 0            讀 x：cache 裡還是 0

 結果 r0 = 0 且 r1 = 0：在 sequential consistency 下不可能，
 但在 x86-64 與 ARM64 上都可能真的發生。
```

在任何一種「把兩個 thread 的操作排成一條總順序」的方式裡，至少有一個 store 會排在對方的 load 前面，所以 r0 和 r1 不可能同時是 0。但在真實硬體上，兩個 store 都還在各自的 store buffer 裡，兩個 load 都讀到舊值。不同架構允許的重排程度不同：

| 架構 | 記憶體模型 | 允許的重排（不加 fence 時） |
|---|---|---|
| x86-64 | TSO（total store order），相對嚴格 | 只允許「store 之後的 load」先完成（上圖的情況） |
| ARM64 | 弱記憶體模型 | load 與 store 之間大多數的重排都允許 |
| 程式語言（C11） | 以 happens-before 定義 | 沒有同步的 data race 是 UB，正確同步的程式表現得像 sequential consistency |

最後一列是關鍵：寫 C 的人不需要記住每種 CPU 的規則。C11 定義了一套跨平台的**記憶體模型**（memory model）：只要程式正確地使用 mutex 或 atomic 同步、沒有 data race，結果就保證和 sequential consistency 一樣；編譯器負責在每個平台插入適當的指令。第 31 章的 mutex 之所以能「讓別人看到你寫的東西」，就是因為 unlock 與下一次 lock 之間建立了同步關係。

> [!warning] 常見誤解
> 「用 `volatile` 就能讓 thread 之間看到彼此的寫入。」在 C 裡，`volatile` 只要求編譯器每次都真的去讀寫記憶體，不提供 atomicity，也不阻止 CPU 重排，更不建立 thread 之間的同步關係。它適合 memory-mapped I/O，以及第 22 章 signal handler 搭配 `volatile sig_atomic_t` 的情境。thread 之間的通知要用 `_Atomic` 或 mutex。（Java 的 `volatile` 是另一回事，它確實有同步語意，不要混為一談。）

## 32.9 Atomic 操作與 memory ordering

C11 的 `<stdatomic.h>` 提供 atomic 型別（`atomic_int`、`atomic_long`，或用 `_Atomic` 修飾任意型別）與操作（`atomic_load`、`atomic_store`、`atomic_fetch_add`、`atomic_compare_exchange_strong` 等）。每個操作都可以指定一個 **memory order**（記憶體順序），說明它除了自己不可分割以外，還要對**周圍其他記憶體操作**提供多少順序保證。

### 發布資料：release 與 acquire

最常見、也最值得學會的模式是「一個 thread 準備好資料，再用一個旗標通知另一個 thread」。

```c
#include <stdatomic.h>
int payload;
atomic_int ready;
void publish_release(void) { payload = 42; atomic_store_explicit(&ready, 1, memory_order_release); }
void publish_seq_cst(void) { payload = 42; atomic_store(&ready, 1); }
int consume_acquire(void) {
    while (!atomic_load_explicit(&ready, memory_order_acquire)) { }
    return payload;
}
```

**Release** store 的意思是：在它之前的所有讀寫，不能被重排到它之後。**Acquire** load 的意思是：在它之後的所有讀寫，不能被重排到它之前。當 acquire load 讀到了 release store 寫入的值，兩者之間就建立了 **happens-before**（先發生於）關係：

```text
 producer thread                         consumer thread
 ────────────────                        ────────────────
 payload = 42          ┐                 
                       │ 不能往下移
 store(ready, 1)  ═════╪════ release ──────▶ load(ready) == 1   ═══ acquire
   （release）         ┘                 ┌     （acquire）
                                         │ 不能往上移
                                         └  讀 payload → 保證看到 42

 「release 之前的所有寫入」 happens-before 「acquire 之後的所有讀取」
```

所以 consumer 讀到 `ready == 1` 之後，一定看得到 `payload = 42`。注意 `payload` 本身是普通變數，它的安全性完全來自旗標上的 release／acquire 配對。

這三個函式編譯成兩種架構的結果很能說明問題。下面同樣用 `-O1` 產生（ARM64 用 `-target aarch64-linux-gnu`）：

```asm
# x86-64（clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables）
publish_release:
	movl	$42, payload(%rip)
	movl	$1, ready(%rip)
	retq
publish_seq_cst:
	movl	$42, payload(%rip)
	movl	$1, %eax
	xchgl	%eax, ready(%rip)
	retq
consume_acquire:
.LBB2_1:
	movl	ready(%rip), %eax
	testl	%eax, %eax
	je	.LBB2_1
	movl	payload(%rip), %eax
	retq
```

```text
ARM64（clang -target aarch64-linux-gnu -O1 -S），擷取關鍵指令：
publish_release:  str  w9, [x8, :lo12:payload]    ; 普通 store
                  stlr w10, [x8]                   ; store-release
publish_seq_cst:  str  w9, [x8, :lo12:payload]
                  stlr w10, [x8]                   ; 和 release 版完全相同
consume_acquire:  ldar w9, [x8]                    ; load-acquire（在迴圈裡）
                  cbz  w9, .LBB2_1
                  ldr  w0, [x8, :lo12:payload]     ; 普通 load
```

逐點解讀：

1. 在 x86-64 上，release store 與 acquire load 都只是普通的 `mov`。因為 TSO 本來就不會把 store 和前面的 store 重排、也不會把 load 和後面的 load 重排，硬體已經免費提供了 release／acquire。它們的作用只剩下「禁止編譯器重排」，以及讓 `consume_acquire` 每次迴圈都真的重新讀 `ready`（對照 32.8 節那個變成無窮迴圈的版本）。
2. 預設的 `atomic_store`（`memory_order_seq_cst`）在 x86-64 上變成 `xchgl`。`xchg` 對記憶體運算元隱含 `lock`，會等 store buffer 清空，這正是為了禁止 32.8 節圖中「store 之後的 load 先完成」那種 TSO 唯一允許的重排。
3. 在 ARM64 上，硬體不會免費提供順序，所以編譯器用專門的 `stlr`（store-release）與 `ldar`（load-acquire）指令。有趣的是 seq_cst store 在這裡也是 `stlr`：ARM64 規定 `stlr` 不會和後面的 `ldar` 重排，所以只要 seq_cst load 也用 `ldar`，就足以得到總順序，不必另外加 fence。同一段 C 程式碼，在兩個平台得到不同的指令、相同的保證，這就是語言記憶體模型的價值。

### 五種 memory order

| memory order | 保證 | 典型用途 | 常見誤用 |
|---|---|---|---|
| `relaxed` | 只保證這個操作本身不可分割，不約束周圍操作 | 統計計數器、只需要最終總數的累加 | 拿 relaxed 的旗標去發布資料，對方看到旗標卻看不到資料 |
| `acquire` | 用在 load：之後的讀寫不能移到它前面 | 讀取旗標或指標，之後才使用資料 | 用在 store 上（沒有意義） |
| `release` | 用在 store：之前的讀寫不能移到它後面 | 準備好資料後設定旗標或發布指標 | 只有一邊用 release，另一邊用 relaxed 讀 |
| `acq_rel` | 讀改寫操作同時有 acquire 與 release | `fetch_add`、CAS 同時當作取得與發布 | |
| `seq_cst`（預設） | acquire／release 之外，所有 seq_cst 操作有一條全域總順序 | 不確定時就用它；像 32.8 節圖中 Dekker 式的互相檢查 | 以為它「太慢」而過早換成較弱的 order |

C11 還有一個 `memory_order_consume`，因為規格難以實作，主流編譯器都把它當成 acquire 處理，新程式不建議使用。實務守則很簡單：預設用 `seq_cst`；只有在量測證明它是瓶頸、而且你能畫出 happens-before 關係時，才換成 acquire／release；`relaxed` 只用在「只關心最後總數」的計數器。

> [!warning] 常見誤解
> 「把變數都改成 atomic，程式就 thread-safe 了。」atomic 只保證**單一變數的單一操作**不可分割。`if (atomic_load(&stock) > 0) atomic_fetch_sub(&stock, 1);` 兩步各自 atomic，中間仍然可以被別的 thread 插進來，兩個 thread 都看到 stock 為 1，結果扣成 −1。跨越多個步驟或多個變數的不變量（invariant），仍然需要 mutex，或下一節的 compare-and-swap 迴圈。

## 32.10 Lock-free 的代價

學會 atomic 之後，很容易想把所有鎖都換掉。**Lock-free**（無鎖）資料結構指的是：不使用 mutex，只用 atomic 操作實作，保證任何時刻至少有一個 thread 能完成操作，不會因為某個 thread 被暫停（例如持有鎖時被換下 CPU）而讓所有人卡住。它的核心工具是 **compare-and-swap**（CAS）：「如果這個位址的值還是我預期的 A，就把它換成 B；否則告訴我現在的值是多少」。

```c
/* 用 CAS 迴圈做「有庫存才扣一」：check 與 update 合成一個不可分割的轉換 */
#include <stdatomic.h>
#include <stdbool.h>
bool take_one(atomic_int *stock) {
    int cur = atomic_load(stock);
    while (cur > 0) {
        if (atomic_compare_exchange_weak(stock, &cur, cur - 1))
            return true;          /* 成功：從 cur 換成 cur − 1 */
        /* 失敗：別人先改了，cur 已被更新成最新值，重新判斷 */
    }
    return false;
}
```

這段程式解決了 32.9 節最後那個庫存扣成負數的問題。但 lock-free 的代價常被低估：

1. **競爭時一樣慢。** CAS 也要獨佔 cache line。很多 thread 同時對同一個位址做 CAS，大部分都會失敗重試，line 在核心之間彈跳，32.4 節的 ping-pong 一點也沒少。lock-free 解決的是「持有者被暫停時大家卡住」，不是「熱點資料」。
2. **ABA 問題。** CAS 只比較值。thread A 讀到堆疊頂端是節點 X，準備把頂端換成 X 的下一個節點；此時 thread B 彈出 X、彈出 Y、又把 X（同一塊記憶體被重新使用）推回去。A 的 CAS 看到頂端「還是 X」就成功了，但 X 的下一個節點早就不是原來那個，資料結構被破壞。
3. **記憶體回收很難。** 在有鎖的程式裡，從串列移除節點後可以馬上 `free`；在 lock-free 結構裡，別的 thread 可能剛讀到這個節點的指標、正準備存取它。什麼時候能安全 `free`，需要 hazard pointer、epoch-based reclamation 或 Linux kernel 的 RCU 這類專門機制，否則就是 use-after-free（第 26 章）。
4. **正確性難以驗證。** 一個 lock-free 佇列的正確實作往往是學術論文等級的成果，測試很難覆蓋所有交錯情況，而且在 x86-64 上正常不代表在 ARM64 上正常（32.8 節的記憶體模型差異）。

| 做法 | 適合 | 不適合 |
|---|---|---|
| 一把 mutex，critical section 很短 | 絕大多數情況；容易證明正確 | 持有時間長的熱門鎖 |
| 分片（sharding）：N 把鎖各管一部分資料 | 雜湊表、快取、連線表 | 需要跨分片的一致操作 |
| per-thread 資料，定期合併 | 統計計數、log buffer | 需要即時精確全域值的情況 |
| 單一 atomic 變數 | 旗標、計數器、引用計數 | 多個欄位必須一起變化的狀態 |
| 成熟函式庫提供的 lock-free 結構 | 已量測證明鎖是瓶頸的佇列 | 自己從頭寫一個 |

`thumbd` 最後採用的組合很典型：統計數字改成 per-thread 計數、每秒合併一次；快取改成 16 個分片、每片一把 mutex，鎖裡只做指標操作；快取項目的引用計數用 atomic。沒有寫任何一行自製的 lock-free 程式碼。

## 32.11 動手做：量測同步成本與 false sharing

### 程式一：四種計數方式的擴展性

這個程式用四種方式完成同一份工作（總共遞增 4,000 萬次），分別用 1 個與 4 個 thread 執行，算出加速比：

- A：所有 thread 對**同一個** atomic 變數遞增。
- B：每個 thread 有自己的 atomic 計數器，但四個計數器**緊鄰**在一個陣列裡。
- C：每個 thread 有自己的計數器，而且用 `alignas` 讓它們**各佔一條 cache line**。
- D：所有 thread 用一把 mutex 保護同一個普通變數。

B 與 C 也用 atomic 遞增，是為了讓每次遞增都真的對記憶體做讀改寫，不會被編譯器縮成一次加法；因為每個計數器只有一個 thread 寫，這裡用 `relaxed` 就夠了。

```c
#include <pthread.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <stdio.h>
#include <time.h>

#define NTHREADS 4
#define TOTAL 40000000L     /* 總工作量：4,000 萬次遞增，由 1 個或 4 個 thread 分攤 */
#define LINE 128            /* Apple M 系列的 cache line 是 128 bytes；x86-64 通常是 64 */

static atomic_long shared;                                   /* A：所有 thread 共用一個 */
static atomic_long packed[NTHREADS];                         /* B：每人一個，但緊鄰 */
static struct { alignas(LINE) atomic_long v; } padded[NTHREADS]; /* C：每人一個，各佔一條 line */
static long locked_count;                                    /* D：mutex 保護 */
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static int wrong;                                            /* 計數不對的次數 */

typedef struct { int id, mode; long iters; } job_t;

static void *worker(void *p) {
    job_t *j = p;
    for (long i = 0; i < j->iters; i++) {
        switch (j->mode) {
        case 0: atomic_fetch_add_explicit(&shared, 1, memory_order_relaxed); break;
        case 1: atomic_fetch_add_explicit(&packed[j->id], 1, memory_order_relaxed); break;
        case 2: atomic_fetch_add_explicit(&padded[j->id].v, 1, memory_order_relaxed); break;
        case 3: pthread_mutex_lock(&mu); locked_count++; pthread_mutex_unlock(&mu); break;
        }
    }
    return NULL;
}

static long reset_and_read(int mode, int reset) {   /* 讀出（或歸零）該方案的計數 */
    long sum = 0;
    for (int i = 0; i < NTHREADS; i++) {
        if (reset) { atomic_store(&packed[i], 0); atomic_store(&padded[i].v, 0); }
        sum += mode == 1 ? packed[i] : padded[i].v;
    }
    if (reset) { atomic_store(&shared, 0); locked_count = 0; }
    return mode == 0 ? (long)shared : mode == 3 ? locked_count : sum;
}

static double run_ms(int mode, int nthreads, long total) {
    pthread_t t[NTHREADS];
    job_t jobs[NTHREADS];
    struct timespec s, e;
    reset_and_read(mode, 1);
    clock_gettime(CLOCK_MONOTONIC, &s);
    for (int i = 0; i < nthreads; i++) {
        jobs[i] = (job_t){i, mode, total / nthreads};
        pthread_create(&t[i], NULL, worker, &jobs[i]);
    }
    for (int i = 0; i < nthreads; i++) pthread_join(t[i], NULL);
    clock_gettime(CLOCK_MONOTONIC, &e);
    if (reset_and_read(mode, 0) != total) wrong++;
    return (e.tv_sec - s.tv_sec) * 1e3 + (e.tv_nsec - s.tv_nsec) / 1e6;
}

int main(void) {
    const char *name[] = {"A 共享一個 atomic", "B 緊鄰的 per-thread", "C padding 的 per-thread", "D mutex 保護"};
    printf("1 thread (ms) | 4 threads (ms) | 加速比 | 方案\n");
    for (int mode = 0; mode < 4; mode++) {
        long total = mode == 3 ? TOTAL / 4 : TOTAL;      /* mutex 搶鎖時很慢，只做四分之一 */
        double t1 = run_ms(mode, 1, total);
        double t4 = run_ms(mode, NTHREADS, total);
        printf("%13.1f | %14.1f | %5.2fx | %s\n", t1, t4, t1 / t4, name[mode]);
    }
    if (wrong) printf("有 %d 次計數錯誤\n", wrong);
    else printf("每次執行後的計數都等於預期的總工作量\n");
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，`cc -std=c17 -O1`）上執行的結果：

```text
1 thread (ms) | 4 threads (ms) | 加速比 | 方案
         71.4 |          342.6 |  0.21x | A 共享一個 atomic
         72.4 |          390.6 |  0.19x | B 緊鄰的 per-thread
         72.6 |           19.7 |  3.69x | C padding 的 per-thread
         41.0 |          170.8 |  0.24x | D mutex 保護
每次執行後的計數都等於預期的總工作量
```

逐行解讀：

1. **四種方案的結果都正確**（最後一行），差別全在速度。這呼應本章開頭老周說的：沒有 race 只代表正確，不代表快。
2. **A：加 thread 變慢約 5 倍。** 1 個 thread 時，每次 atomic 遞增約 71.4 ms ÷ 4,000 萬 ≈ 1.8 ns，line 一直在自己的 L1 裡。4 個 thread 時，每次遞增都要把 line 從別的核心搶過來，總時間變成 342.6 ms。這就是 32.4 節的 cache line ping-pong。
3. **B：邏輯上和 C 完全一樣，速度卻和 A 一樣差。** 四個 `atomic_long` 共 32 bytes 緊鄰存放，幾乎一定落在同一條（最多跨兩條）128-byte 的 line 裡，四個 thread 寫不同變數，硬體卻在搶同一條 line。這是 32.5 節的 false sharing，而且光看程式碼完全看不出來。
4. **C：只加了 `alignas(128)`，加速比從 0.19 倍變成 3.69 倍**，接近 4 核心的理想值。每個 thread 的 line 一直留在自己的 L1 裡，處於 M 狀態，不必和任何人協調。
5. **D：mutex 在沒有競爭時很便宜**，1 個 thread 做 1,000 萬次 lock、遞增、unlock 只要 41.0 ms，平均約 4 ns 一組；4 個 thread 搶同一把鎖時，時間變成 4 倍多，和 A 一樣是負的擴展。

數字會隨機器、核心種類（這台有效能核心與節能核心）與當下負載變動，多跑幾次，加速比會在一個範圍內浮動，但四者的相對關係很穩定。在 Linux x86-64 上把 `LINE` 改成 64 可以得到類似的結果。

> [!note] 實驗的一個細節
> 我們最初把 B、C 寫成普通的 `volatile long` 遞增，在這台 M4 Pro 上 B 與 C 的差距就不明顯。改成 atomic 讀改寫之後差距才清楚出現。一種可能的解釋是：普通 store 可以先停在 store buffer 裡，處理器有機會把多次寫入合併，對 line 所有權的需求比較少；atomic 讀改寫則每次都必須獨佔 line。但處理器內部怎麼做並沒有公開文件可以確認，這只是推測，而且依平台而定；它提醒我們，false sharing 有多嚴重要用實驗與 profiler 確認，不能只靠推論。

### 程式二：thread-unsafe 函式的實際後果

第二段程式重現 32.6 節第 3 類的問題：一個回傳 static buffer 的格式化函式，對照由呼叫者提供 buffer 的 `_r` 版本。

```c
#include <pthread.h>
#include <stdio.h>
#include <string.h>

/* thread-unsafe 版：回傳指向 static buffer 的指標，像 ctime()、localtime() 一樣 */
static const char *fmt_dims_unsafe(int w, int h) {
    static char buf[32];
    snprintf(buf, sizeof buf, "%dx%d", w, h);
    return buf;
}

/* reentrant 版：由呼叫者提供 buffer，像 ctime_r()、localtime_r() 一樣 */
static const char *fmt_dims_r(int w, int h, char *buf, size_t n) {
    snprintf(buf, n, "%dx%d", w, h);
    return buf;
}

#define ROUNDS 200000
typedef struct { int w, h, use_r; long bad; } job_t;

static void *worker(void *p) {
    job_t *j = p;
    char mine[32], expect[32];
    snprintf(expect, sizeof expect, "%dx%d", j->w, j->h);
    for (int i = 0; i < ROUNDS; i++) {
        const char *s = j->use_r ? fmt_dims_r(j->w, j->h, mine, sizeof mine)
                                 : fmt_dims_unsafe(j->w, j->h);
        if (strcmp(s, expect) != 0) j->bad++;   /* 拿到的不是自己的結果 */
    }
    return NULL;
}

static long trial(int use_r) {
    job_t a = {1920, 1080, use_r, 0}, b = {64, 64, use_r, 0};
    pthread_t ta, tb;
    pthread_create(&ta, NULL, worker, &a);
    pthread_create(&tb, NULL, worker, &b);
    pthread_join(ta, NULL);
    pthread_join(tb, NULL);
    return a.bad + b.bad;
}

int main(void) {
    printf("static buffer 版：%d 次呼叫中有 %ld 次拿到錯誤字串\n", 2 * ROUNDS, trial(0));
    printf("_r 版          ：%d 次呼叫中有 %ld 次拿到錯誤字串\n", 2 * ROUNDS, trial(1));
    return 0;
}
```

在 macOS arm64 上連續執行三次：

```text
static buffer 版：400000 次呼叫中有 393 次拿到錯誤字串
_r 版          ：400000 次呼叫中有 0 次拿到錯誤字串
static buffer 版：400000 次呼叫中有 216 次拿到錯誤字串
_r 版          ：400000 次呼叫中有 0 次拿到錯誤字串
static buffer 版：400000 次呼叫中有 571 次拿到錯誤字串
_r 版          ：400000 次呼叫中有 0 次拿到錯誤字串
```

解讀：

1. static buffer 版每次執行都有幾百次拿到「不是自己的」字串，而且次數每次不同。這正是 `thumbd` log 時間戳記偶爾錯亂的機制：機率低、不可重現，但一定會發生。
2. 這三次的錯誤率在萬分之五到千分之一點五之間；就算只取萬分之五，換算成 `thumbd` 每秒近 2,000 個請求，也大約每秒就會出現一次。「很少發生」在 production 的流量下等於「一直在發生」。
3. 這個程式本身含有 data race，嚴格說是 undefined behavior，錯誤次數依編譯器、機器與時機而定；它的用途是讓你親眼看到後果，修法則是第二行：改用 reentrant 版本後，錯誤是 0，而且不需要任何鎖。

## 32.12 在工作上怎麼用

### 情境一：「加 thread 沒變快」的診斷流程

這是並行效能最常見的工作情境。下面的流程從最便宜的觀察開始，每一步都有對應的工具：

```text
症狀：加了 thread（或加了核心），吞吐量不升或下降
  │
  ├─ 1. CPU 真的滿了嗎？ top -H -p <PID>、mpstat -P ALL 1
  │      ├─ CPU 沒滿，thread 都在等 → 是鎖或 I/O：看第 2 步
  │      └─ CPU 滿了 → 是計算或同步開銷：看第 3 步
  │
  ├─ 2. 在等什麼？
  │      ├─ pidstat -wt -p <PID> 1：自願 context switch（cswch/s）很高 → 常是搶鎖或 I/O
  │      ├─ strace -f -c -p <PID>（短時間）：futex 次數很多 → 搶鎖
  │      └─ gdb 或 lldb 附加後印出所有 thread 的 backtrace，數一數多少 thread 停在同一個 lock 呼叫
  │
  ├─ 3. CPU 花在哪？
  │      ├─ perf top -p <PID>：熱點在 lock／unlock、atomic 函式 → 同步熱點
  │      ├─ perf c2c record -p <PID>，再 perf c2c report：找出被多核心寫入的 cache line（false sharing）
  │      └─ vmstat 1：r 欄長期 > 核心數、cs 欄很高 → oversubscription
  │
  └─ 4. 對策
         ├─ 縮短 critical section（把 memcpy、配置、I/O 移出鎖外）
         ├─ 分片（一把鎖拆成 N 把）、per-thread 資料定期合併
         ├─ 頻繁寫入的資料各佔一條 cache line
         └─ CPU-bound worker 數 ≈ 核心數；I/O-bound 的部分改用非阻塞 I/O（第 30 章）
```

`perf c2c`（cache-to-cache）是 Linux 上專門找 false sharing 的工具：它利用硬體的取樣功能，找出哪些 cache line 經常在核心之間以 Modified 狀態轉手（報告裡的 HITM），並列出是哪些程式位置、哪些 offset 在讀寫它。看到同一條 line 上有好幾個不同 offset 被不同 thread 寫入，就是 false sharing 的典型特徵。

### 情境二：決定 thread pool 的大小

| 工作類型 | 建議起點 | 理由 |
|---|---|---|
| 純 CPU-bound（縮放、壓縮、編碼） | 約等於可用核心數 | 再多只會 oversubscription；容器內要看 CPU 配額而不是主機核心數 |
| 混合型（計算加阻塞 I/O） | 核心數 × (1 + 等待時間 ÷ 計算時間) | 等待時讓別的 thread 用 CPU；這只是起點，要用壓測確認 |
| 大量網路連線 | 少數 event loop thread 加一個 CPU-bound pool | 第 30 章的混合架構，不要一個連線一個 thread |

最後一定要壓測：畫出 worker 數對吞吐量與 p99 延遲的曲線，選在吞吐量剛到頂、延遲還沒開始爬升的那一點。在容器裡執行時特別注意：`nproc` 或 `sysconf(_SC_NPROCESSORS_ONLN)` 回報的可能是主機的核心數，而 cgroup 的 CPU 配額只給了你其中幾個。

### 情境三：審查程式碼的 thread safety 清單

接手一個多執行緒的 C 服務，或審查一個要加進 thread pool 的模組時，可以照這份清單逐項檢查：

1. 用 `grep -nE '\b(strtok|localtime|gmtime|ctime|asctime|rand|gethostbyname|inet_ntoa|strerror)\s*\('` 找出第 2、3 類函式，換成安全版本。
2. 列出所有 `static` 區域變數與全域變數，逐一回答：誰寫它？誰讀它？用什麼同步？
3. 傳給 `pthread_create` 的參數指標，指向的物件活得比 thread 久嗎？會被下一輪迴圈改掉嗎？
4. 第三方函式庫的文件有沒有寫 thread-safe？有些函式庫要求每個 thread 用自己的 context 物件（例如解碼器的 handle）。
5. 用 `-fsanitize=thread` 編譯，在壓測流量下跑測試（第 31 章）。但要知道 TSan 只看得到被 instrument 的程式碼與它攔截的函式：如果對共享 buffer 的寫入發生在 libc 內部（例如 `snprintf`、`localtime`），TSan 可能完全不報。在 macOS arm64（Apple clang 21）上用 TSan 跑 32.11 節程式二，錯誤字串照樣出現，TSan 卻沒有任何警告。所以第 1 步的 grep 與第 2 步的人工審查不能省。
6. 熱門的共享計數器與鎖，旁邊有沒有其他被頻繁寫入的欄位？必要時加 `alignas`。

## 32.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 加 thread 後吞吐量下降、CPU 卻很滿 | 熱門鎖的 critical section 太長，或 oversubscription | `perf top` 熱點在鎖；`vmstat` 的 `r`、`cs` 很高；`strace -c` 中 `futex` 很多 | 把耗時工作移出鎖外、分片；CPU-bound worker 數設為核心數 |
| 改成 per-thread 計數器後還是不會擴展 | false sharing：計數器緊鄰在同一條 cache line | `perf c2c` 報告同一條 line 有多個 offset 被不同 thread 寫入 | `alignas(64)`（或平台的 line 大小）、thread-local 變數定期合併 |
| log 時間、解析結果偶爾錯亂，只在高併發出現 | 用了 `localtime`、`strtok` 等第 2、3 類函式 | `grep` 這些函式；TSan 不一定抓得到（libc 內部沒有被 instrument），以程式碼審查為主 | 換成 `_r` 版本或 `strftime` 搭配 `localtime_r` |
| 某個 thread 永遠等不到旗標變成 1 | 用普通變數或 `volatile` 做 thread 間通知，編譯器把讀取移出迴圈 | 看組合語言，迴圈裡沒有重新讀取；TSan 回報 data race | 改用 `atomic_int` 搭配 release／acquire，或 mutex 加 condition variable |
| 在 x86 上正常，搬到 ARM 伺服器後偶爾讀到舊資料 | 依賴了 x86 TSO 的順序保證，沒有正確使用 atomic | 在 ARM 上用 TSan 與壓測重現；檢查所有跨 thread 的旗標與指標發布 | 依 C11 記憶體模型寫：發布用 release，讀取用 acquire |
| 所有變數都改成 atomic，庫存或配額仍然算錯 | 「先檢查再更新」跨越兩個 atomic 操作 | 用 barrier 讓兩個 thread 同時執行 check 與 update，重現問題 | 用 mutex 包住整個轉換，或改成 CAS 迴圈 |
| 自製 lock-free 結構偶爾 crash | ABA 或記憶體回收過早造成 use-after-free | ASan 或 TSan 回報；只在高競爭時發生 | 改用成熟函式庫或簡單的鎖；需要時採用 hazard pointer、epoch 等回收機制 |

## 32.14 動手練習

1. **手算**：一個影像批次工具在單核心要 120 秒，其中 18 秒只能循序執行。用 Amdahl 定律算出 4、8、16 核心的 speedup 與 efficiency，以及無限多核心的上限。（答案：s = 0.15；S(4) ≈ 2.76、E ≈ 69%；S(8) ≈ 3.90、E ≈ 49%；S(16) ≈ 4.92、E ≈ 31%；上限約 6.67。可以把 32.3 節的 Python 程式改成 s = 0.15 驗證。）
2. **手算**：`thumbd` 每個請求要持有全域快取鎖 0.2 ms，每個請求的 CPU 時間是 3 ms，機器有 16 核心。吞吐量的上限是多少？瓶頸在鎖還是 CPU？如果把鎖分成 8 片、請求平均分散，上限變成多少？（提示：鎖的上限是 1 / 0.2 ms；分片後每片各自有這個上限。）
3. 修改 32.11 節程式一，把 `LINE` 改成 64、32、16，觀察 C 方案的加速比怎麼變化。在你的機器上，padding 要多大才能消除 false sharing？用 `sysctl hw.cachelinesize`（macOS）或 `getconf LEVEL1_DCACHE_LINESIZE`（Linux）對照。
4. 在程式一加入方案 E：每個 thread 先累加到自己的 local 變數，結束時才用一次 `atomic_fetch_add` 加到 `shared`。預測它的加速比，再實際量測，並解釋它為什麼比 C 還好。
5. 用 `clang -fsanitize=thread -g` 編譯 32.11 節程式二並執行，TSan 有沒有回報？（在 macOS 上我們沒有得到任何報告。）想想原因：對 `buf` 的寫入發生在哪個函式裡？把 `snprintf` 換成自己寫的迴圈逐字元寫入 `buf`，用 `-O0` 重新編譯再跑一次 TSan（我們在 `-O1` 下沒有得到報告，`-O0` 才有），看它指出哪一行、哪兩個 thread。最後把 `static` 改成 `static _Thread_local`，錯誤次數變成多少？為什麼這是另一種修法？
6. 把 32.9 節的 `publish_release`／`consume_acquire` 寫成一個完整程式：一個 thread 發布 `payload`，另一個等待後讀取。分別用 `seq_cst`、acquire／release、relaxed 實作，再用 `clang -target aarch64-linux-gnu -O1 -S` 比較三者產生的指令。哪一個在理論上是錯的？

## 本章重點整理

- Speedup 是 T_1 / T_p，efficiency 是 speedup 除以核心數；用最好的循序版本當 T_1 才是誠實的 absolute speedup。
- Amdahl 定律說固定問題大小時，循序比例 s 讓加速比上限為 1 / s；Gustafson 定律說固定時間時，可完成的工作量隨核心數近乎線性成長，兩者回答不同的問題。
- 被同一把鎖保護的 critical section 就是循序部分；每個請求持鎖 L 秒，吞吐量上限就是 1 / L，與核心數無關。
- 同步的成本由便宜到昂貴：無競爭的 atomic 與 mutex（數 ns）、cache line 在核心之間搬家（數十到上百 cycle）、搶鎖導致的睡眠與喚醒（µs 級）、CPU-bound thread 多於核心時的 oversubscription。
- Cache coherence 以 line 為單位：要寫一條 line 必須先讓其他核心的副本失效，因此多核心頻繁寫同一條 line 會產生 ping-pong。
- False sharing 是不同 thread 寫不同變數、但變數落在同一條 cache line；用 `alignas` 讓熱門資料各佔一條 line，或改用 per-thread 資料定期合併。
- Cache line 大小依平台而定：多數 x86-64 是 64 bytes，Apple M 系列是 128 bytes，要用 `sysctl` 或 `getconf` 確認。
- Thread-unsafe 函式分四類：未保護共享變數、跨呼叫保存狀態、回傳 static 資料的指標、呼叫了 thread-unsafe 函式；後兩類常藏在 `localtime`、`strtok`、`rand` 這些標準函式裡。
- Reentrant 函式不碰任何共享資料，是 thread-safe 函式的子集合；用鎖實作的 thread-safe 函式（例如 `malloc`）不是 reentrant，不能在 signal handler 中使用。
- 編譯器與 CPU 都會重排記憶體操作；沒有同步的 data race 在 C 中是 undefined behavior，編譯器甚至可以把等待旗標的迴圈變成無窮迴圈。
- `volatile` 不是同步工具；thread 之間的通知與發布要用 C11 atomic 或 mutex。
- Release store 與 acquire load 配對時建立 happens-before：release 之前的寫入，在 acquire 之後一定看得見；預設的 `seq_cst` 最容易推理，`relaxed` 只適合只關心總數的計數器。
- Atomic 只保證單一操作不可分割，跨越多個步驟的不變量仍需要 mutex 或 CAS 迴圈。
- Lock-free 不等於快：競爭時 CAS 一樣要搶 cache line，還要處理 ABA 與記憶體回收；大多數情況下，短 critical section、分片與 per-thread 資料是更好的選擇。

## 延伸問答

> [!question]- Q1. 為什麼「4 個 thread 對同一個 atomic 計數器遞增」會比 1 個 thread 慢好幾倍？atomic 不是已經很快了嗎？
> atomic 快，是指在沒有競爭時：那條 cache line 一直在同一個核心的 L1 裡，處於 Modified 狀態，一次讀改寫只要幾 ns。問題出在多核心輪流寫入時，cache coherence 協定規定寫入前必須獨佔整條 line，所以每一次遞增都要先讓其他核心的副本失效、再把 line 從上一個寫入者那裡搬過來。
>
> 這一搬就是數十到上百個 cycle，而且四個核心的遞增實際上被序列化了：同一時間只有一個核心擁有那條 line。結果是工作沒有被平行化，還多付了搬運成本。32.11 節的實驗中，A 方案 4 個 thread 的時間是 1 個 thread 的將近 5 倍。解法不是換更快的 atomic，而是避免共享寫入：per-thread 計數、定期合併。

> [!question]- Q2. 手算題：一個服務每個請求要花 6 ms CPU 時間，其中 0.3 ms 持有一把全域鎖。在 4、16、64 核心的機器上，吞吐量上限分別是多少？
> 先算兩個上限。CPU 上限是「核心數 ÷ 每個請求的 CPU 時間」：4 核心為 4 / 6 ms ≈ 667 個請求／秒，16 核心約 2,667，64 核心約 10,667。鎖的上限與核心數無關：同一時間只有一個請求能持有鎖，所以最多 1 / 0.3 ms ≈ 3,333 個請求／秒。
>
> 實際上限取兩者較小值：4 核心約 667（CPU 是瓶頸），16 核心約 2,667（仍是 CPU，但已接近鎖的上限），64 核心約 3,333（鎖成為瓶頸，多出來的 48 個核心幾乎用不上）。而且接近鎖上限時，排隊與喚醒的成本會讓實際值更低。這說明在大機器上，縮短 critical section 或分片比加核心更有效。

> [!question]- Q3. thread-safe 和 reentrant 有什麼差別？為什麼 `malloc` 是 thread-safe 卻不能在 signal handler 裡呼叫？
> thread-safe 是指多個 thread 同時呼叫時結果正確，實作方式可以是加鎖保護共享資料。reentrant 更嚴格：函式完全不碰共享資料，所有狀態都來自參數與 local 變數，所以不需要任何鎖，在執行到一半被打斷、再次進入時也安全。reentrant 是 thread-safe 的子集合。
>
> glibc 的 `malloc` 用鎖保護 heap 的資料結構，所以多個 thread 同時呼叫沒問題。但如果某個 thread 正在 `malloc` 裡持有鎖時收到 signal，handler 在**同一個 thread** 上執行，又呼叫 `malloc` 去拿同一把鎖，就會等待自己釋放，造成 deadlock；或者在沒有鎖保護的路徑上看到被改到一半的資料結構。所以 signal handler 只能呼叫 async-signal-safe 函式（第 22 章），這個要求比 thread-safe 更嚴格。

> [!question]- Q4. 程式找錯：下面這段 log 程式在多執行緒下偶爾印出錯亂的時間，原因是什麼？怎麼修？`char *t = ctime(&now); log_write(t);`
> `ctime` 屬於第 3 類 thread-unsafe 函式：它把格式化後的字串放在函式庫內部的一個 static buffer 裡，回傳指向這塊 buffer 的指標。所有 thread 共用同一塊 buffer，thread A 拿到指標後、還沒把字串寫進 log 之前，thread B 呼叫 `ctime` 就把內容覆寫成 B 的時間，於是 A 寫出的是 B 的時間，甚至是寫到一半的混合字串。
>
> 修法是使用由呼叫者提供 buffer 的版本，例如 `char buf[32]; ctime_r(&now, buf);`，或更好的 `localtime_r` 搭配 `strftime`，可以自訂格式而且沒有固定的換行字元。如果只能用某個沒有 `_r` 版本的老函式，可以用 lock-and-copy：在一把專用 mutex 裡呼叫它並把結果複製出來，但這會引入新的循序瓶頸。

> [!question]- Q5. 你在 production 看到：某服務從 8 個 worker 改成 32 個之後，`vmstat` 的 `cs` 欄從每秒 2 萬升到 30 萬，吞吐量下降。你會怎麼判斷與處理？
> context switch 暴增有兩個常見來源。一是自願切換（thread 主動睡眠）：搶鎖失敗後透過 futex 睡眠，或在等 I/O；二是非自願切換（時間片用完被搶占）：CPU-bound thread 數遠多於核心數的 oversubscription。可以用 `pidstat -wt -p <PID> 1` 分別看每個 thread 的 `cswch/s`（自願）與 `nvcswch/s`（非自願）。
>
> 如果是自願切換為主，再用 `strace -f -c` 短時間取樣看 `futex` 次數、或用 `perf top` 看熱點是否在鎖，然後縮短或拆分熱門的 critical section。如果是非自願切換為主，且 `vmstat` 的 `r` 欄長期大於核心數，就是 thread 太多：把 CPU-bound worker 數降回接近核心數，用佇列吸收突發流量。兩種情況都說明「加 thread」不是提升吞吐量的通用解法。

> [!question]- Q6. 為什麼在 x86-64 上，release store 編譯出來只是一條普通的 `mov`，但預設的 `atomic_store`（seq_cst）會變成 `xchg`？
> x86-64 的記憶體模型是 TSO：硬體保證 store 不會和前面的 store 重排、load 不會和後面的 load 重排，所以 release（之前的讀寫不能移到 store 之後）與 acquire（之後的讀寫不能移到 load 之前）的硬體部分本來就成立，編譯器只需要保證自己不重排，用普通 `mov` 即可。
>
> TSO 唯一允許的重排是「store 之後的 load 可以先完成」，因為 store 還停在 store buffer 裡。seq_cst 要求所有 seq_cst 操作有一條全域總順序，必須禁止這種重排，所以 seq_cst store 要等 store buffer 清空，編譯器用隱含 `lock` 的 `xchg`（或 `mov` 加 `mfence`）達成。在 ARM64 上則不同，release 與 acquire 本身就需要 `stlr`、`ldar` 這類專門指令。這也說明語言的記憶體模型把平台差異藏了起來。

> [!question]- Q7. 一個工程師把共享的 `int stock` 改成 `atomic_int`，然後寫 `if (atomic_load(&stock) > 0) atomic_fetch_sub(&stock, 1);`，為什麼庫存還是可能變成負數？
> atomic 保證的是**單一操作**不可分割：`atomic_load` 本身不會讀到寫到一半的值，`atomic_fetch_sub` 本身不會遺失更新。但這段程式的不變量「扣之前庫存必須大於 0」跨越了兩個操作，兩者之間沒有任何保護。stock 為 1 時，兩個 thread 可以都先執行 `atomic_load` 看到 1、都通過檢查，再各自扣 1，結果是 −1。
>
> 這是 check-then-act 的邏輯 race，消除 data race 並不能消除它。修法是把檢查與更新合成一個不可分割的轉換：用 mutex 包住整段，或用 CAS 迴圈，讀出目前值 cur，只有在 cur > 0 時嘗試把它從 cur 換成 cur − 1，失敗就用最新值重試，如 32.10 節的 `take_one`。多個欄位必須一起變化時，mutex 通常更清楚。

> [!question]- Q8. 面試題：什麼是 false sharing？你會怎麼在一個真實服務裡找出它？
> false sharing 是指不同 thread 寫入不同的變數，但這些變數剛好落在同一條 cache line 上。cache coherence 以 line 為單位運作，一個核心寫入時必須讓其他核心的整條 line 失效，於是邏輯上互不相干的寫入，在硬體層面變成互相搶奪同一條 line，效能和真的共享同一個變數一樣差。常見於 per-thread 計數器陣列、相鄰的鎖、佇列的頭尾指標。
>
> 找它的方法：先從症狀判斷，例如「每個 thread 只寫自己的資料，卻完全不會擴展」。在 Linux 上用 `perf c2c record` 取樣、`perf c2c report` 看哪些 cache line 有大量 HITM（在別的核心以 Modified 狀態命中），報告會列出同一條 line 上各 offset 的讀寫程式位置；看到多個 offset 被不同 thread 寫入，就能確認。修法是用 `alignas` 讓熱門資料各佔一條 line，或改成 thread-local 累積、定期合併，並以量測確認改善。回答時提到 line 大小依平台而定（64 或 128 bytes）會加分。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 12 章 12.6 節（用 thread 做平行計算、效能特性）與 12.7 節（thread safety、reentrancy、race、deadlock）。
- [ThreadSanitizer 文件](https://clang.llvm.org/docs/ThreadSanitizer.html)：TSan 的用法、支援平台與限制。
- [Linux man pages](https://man7.org/linux/man-pages/)：`pthreads(7)` 列出 POSIX 規定不必是 thread-safe 的函式；各函式頁面的 ATTRIBUTES 段落標示 `MT-Safe`／`MT-Unsafe`；`futex(2)`、`perf-c2c(1)`。
- [POSIX.1-2024（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`_r` 系列函式與 thread safety 的正式規格。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：第 3 卷的 memory ordering 章節，x86 記憶體模型的權威描述。
