---
chapter: 26
title: 記憶體錯誤與 Garbage Collection
part: 7
---

# 第 26 章　記憶體錯誤與 Garbage Collection

> [!abstract] 本章地圖
> **核心問題**：C 程式自己管理 heap 記憶體時，最常犯哪些錯？這些錯為什麼常常在「離 bug 很遠的地方」才爆出來？工具怎麼幫我們抓到它們，而有 garbage collection 的語言又是怎麼從根本上避開其中一部分？
>
> **你會學到**：
> - 認出十種典型的 C 記憶體錯誤，並說出每一種在 `thumbd` 這類服務裡長什麼樣
> - 解釋 use-after-free 與 double free 為什麼會破壞 allocator 的資料結構，導致之後無關的 `malloc` 當機
> - 讀懂 AddressSanitizer 的報告，並用 shadow memory 的規則手算「這次存取為什麼被判定越界」
> - 比較 ASan、UBSan、LeakSanitizer、Valgrind 與 macOS `leaks` 的能力與代價，選對工具
> - 說明 reachability、mark-and-sweep 與保守式 GC 的原理，並解釋為什麼有 GC 的語言仍然會 leak
> - 用「所有權」的觀念設計 C 程式的配置與釋放，並診斷「RSS 持續上升」到底是不是 leak
>
> **前置知識**：第 2 章（指標與 sanitizer 的基本用法）、第 11 章（stack buffer overflow）、第 23–24 章（page fault、RSS）、第 25 章（malloc 的 free list 與 boundary tag）
>
> **對應 CS:APP 3e**：第 9 章 9.10–9.11 節

## 26.1 故事：每天長 300 MB 的縮圖服務

拾光相簿上線新版 `thumbd` 兩週後，SRE 阿哲在監控面板上畫了一條線給小安看：每台機器上 `thumbd` 的 RSS 從啟動時的 600 MB 開始，每天穩定增加大約 300 MB，一週後逼近容器的記憶體上限，被 OOM killer（第 24 章）殺掉重啟。「每週日凌晨自動重啟一次可以撐住，但這不是辦法。」

同一段時間還有另一個更怪的現象：大約每兩三天，某台機器上的 `thumbd` 會當機，core dump 的 backtrace 停在 `malloc` 內部，glibc 印出 `malloc(): corrupted top size` 之類的訊息。小安翻遍呼叫 `malloc` 的那一行，參數完全正常，程式碼看起來沒有任何問題。

老周看完兩件事，說：「第一件很可能是 leak，第二件幾乎可以確定是 heap 被寫壞了。兩個都是 C 程式最經典的記憶體錯誤。第二種最麻煩：當機的地方通常不是犯錯的地方。你在 `malloc` 裡面找不到 bug，因為 bug 在更早之前、某個寫過頭或釋放後還在用指標的地方。」

這一章要回答三個問題：C 程式的記憶體錯誤有哪幾種、為什麼它們的症狀常常離原因很遠；有哪些工具可以把「遠處的症狀」拉回「真正的原因」；以及 Java、Python、Go 這些有 garbage collection 的語言，是怎麼讓工程師不用自己 `free` 的，它們又留下了哪些問題。

## 26.2 為什麼 C 的記憶體錯誤特別難抓

在 Python 或 Java 裡，存取陣列越界會立刻丟出例外，告訴你是哪一行。C 不會。C 標準把越界存取、使用已釋放的記憶體、讀取未初始化的變數都歸為 **undefined behavior**（未定義行為，第 2 章）：標準不規定會發生什麼事，編譯器與執行環境可以做任何事，包括「看起來正常」。

這造成一個關鍵的困難：**犯錯的時間點與出現症狀的時間點可以相隔很遠。** 下面是 `thumbd` 當機的一種典型時間軸：

```text
 時間 ─────────────────────────────────────────────────────────────▶

 t1 請求 A：解析 EXIF，寫入 heap 緩衝區時多寫了 8 bytes
    │  多寫的 8 bytes 剛好蓋到「下一個 block 的 header」（第 25 章的 boundary tag）
    │  此時沒有任何錯誤，請求 A 正常回傳
    ▼
 t2 數千個請求過去，被蓋壞的 header 靜靜躺在 heap 裡
    ▼
 t3 請求 B：malloc 走訪 free list，讀到被蓋壞的 size 欄位
    │  allocator 的一致性檢查失敗 → abort()，或者根據錯誤的 size 切出重疊的 block
    ▼
 core dump 的 backtrace：main → handle(B) → malloc → ...（完全看不到請求 A）
```

t1 的錯誤寫入沒有立刻被發現，因為 MMU（第 23 章）只檢查「這個 page 能不能寫」，而越界的 8 bytes 仍然落在同一個合法的 heap page 裡。硬體的保護粒度是 page，C 物件的大小是 bytes，中間這段落差就是記憶體錯誤藏身的地方。

所以除錯 C 的記憶體錯誤，最有效的策略不是盯著當機的那一行，而是**讓錯誤在發生的當下就被抓到**。這正是 26.6 節 sanitizer 的設計目標。在那之前，先把常見錯誤一一認清楚。

| 錯誤發生的位置 | 硬體會不會立刻發現 | 常見後果 |
|---|---|---|
| 寫到未映射的位址（例如 NULL 附近） | 會，page fault 後 kernel 送出 SIGSEGV | 立刻當機，最好抓 |
| 寫到唯讀的 page（例如字串常數） | 會，protection fault | 立刻當機 |
| 越界寫到同一個 heap page 的鄰居 | 不會 | 鄰居資料被改、allocator metadata 損壞，之後才當機 |
| 讀取已釋放但尚未歸還 kernel 的 block | 不會 | 讀到舊資料或別人的新資料，結果錯誤但不當機 |
| 忘記 `free` | 不會，也不算錯誤存取 | RSS 慢慢上升，最後 OOM |

## 26.3 C 記憶體錯誤圖鑑

CS:APP 第 9.11 節列出了十種最常見的記憶體相關錯誤。下面用 `thumbd` 可能寫出的程式碼逐一說明，每一種都附上「為什麼錯」和「正確寫法」。這些片段只是示意，不是完整程式。

### 錯誤一：dereference 壞指標

**Dereference**（解參考）就是透過指標去讀寫它指向的記憶體，也就是 `*p` 這個動作。如果 `p` 本身的值不是合法位址，就會出事。最經典的例子是 `scanf` 少了 `&`：

```c
int quality;
sscanf(query, "q=%d", quality);    /* 錯：把 quality 的「值」當成位址 */
sscanf(query, "q=%d", &quality);   /* 對：傳 quality 的位址 */
```

錯誤版本把 `quality` 裡的垃圾值當成位址寫入。運氣好時那個值指向未映射的區域，立刻 segfault；運氣不好時它剛好指向某個合法的資料，就靜靜地改掉別人的變數。現代編譯器開 `-Wall` 會對這行發出格式不符的警告，所以永遠要開警告並把警告當成錯誤處理。

### 錯誤二：讀取未初始化的記憶體

`.bss` 的全域變數會被載入器清成 0（第 18 章），但 `malloc` 回傳的 heap 記憶體和 stack 上的 local 變數**不會**被清零，裡面是之前留下的任何內容。

```c
unsigned *hist = malloc(256 * sizeof *hist);   /* 亮度直方圖，內容是垃圾 */
for (size_t i = 0; i < npixels; i++)
    hist[px[i]]++;                             /* 在垃圾值上累加 */
/* 修法：用 calloc(256, sizeof *hist)，或 malloc 後 memset 為 0 */
```

這類錯誤的症狀是「結果偶爾不對、而且不穩定」：同一張圖有時候算出的直方圖不一樣，因為 heap 裡殘留的內容隨著之前處理過哪些請求而改變。

### 錯誤三：stack buffer overflow

第 11 章已經詳細看過 `gets` 與 stack smashing。重點是：任何「把長度不受控的輸入複製進固定大小陣列」的程式碼都屬於這類，例如用 `strcpy` 把 HTTP header 複製進 `char host[64]`。修法是使用帶長度的介面（`snprintf`、`memcpy` 前先檢查長度），並且讓長度檢查發生在複製之前。

### 錯誤四：以為指標和它指向的物件一樣大

```c
/* 配置 h 個「列指標」，每個指向一列像素 */
uint8_t **rows = malloc(h * sizeof(uint8_t));     /* 錯：配置了 h 個 byte */
uint8_t **rows = malloc(h * sizeof(uint8_t *));   /* 對：配置 h 個指標，每個 8 bytes */
uint8_t **rows = malloc(h * sizeof *rows);        /* 更好：讓編譯器從變數推型別 */
```

錯誤版本在 LP64（第 3 章）下只配置了需要量的八分之一，之後寫入 `rows[i]` 會一路寫出 block 的尾端，蓋掉鄰居。`sizeof *rows` 的寫法讓型別永遠跟著變數走，改了變數型別也不會忘記改這裡。

### 錯誤五：off-by-one

**Off-by-one**（差一錯誤）是邊界多算或少算一個。C 裡最常見的兩種：迴圈寫成 `i <= n`，以及配置字串時忘了結尾的 `'\0'`。

```c
char *copy = malloc(strlen(name));        /* 錯：少了 '\0' 那 1 byte */
strcpy(copy, name);
char *copy = malloc(strlen(name) + 1);    /* 對 */
```

只差 1 byte，聽起來無害，但如果那 1 byte 剛好落在下一個 block 的 header 上，就會造成 26.2 節描述的延遲當機。26.10 節會用 ASan 實際抓一次這個 bug。

### 錯誤六：參照指標而不是它指向的物件

這類錯誤來自運算子優先順序。假設有個函式要把佇列長度減一：

```c
void pop(size_t *len) {
    *len--;      /* 錯：後置 -- 比 * 先結合，等於 *(len--)：指標往回移一格，長度沒變 */
    (*len)--;    /* 對：先取物件，再減一 */
}
```

錯誤版本編譯得過，開 `-Wall` 時 clang 會警告 `expression result unused`（表達式結果未使用，`-Wunused-value`），這是一個很好的線索。ASan 抓不到這種錯：移動後的指標沒有被拿去存取，記憶體層面一切合法，只是邏輯錯了，要靠警告與單元測試。遇到 `*`、`++`、`--`、`->` 混用時，加括號永遠比記優先順序表安全。

### 錯誤七：誤解指標運算

指標加一，前進的是「一個元素」，不是「一個 byte」（第 10 章）。

```c
uint32_t *p = pixels;               /* 每個像素 4 bytes（RGBA） */
p += sizeof(uint32_t);              /* 錯：跳過了 4 個像素，不是 1 個 */
p += 1;                             /* 對：前進一個像素，位址增加 4 */
```

這個錯誤在影像處理裡特別常見，因為工程師腦中想的是「一個像素 4 bytes」，手卻把 byte 數加到了指標上。結果是只處理了四分之一的像素，然後跑出緩衝區尾端。

### 錯誤八：參照已經不存在的變數

Local 變數住在 stack frame 裡（第 9 章），函式回傳時 frame 就被收回。回傳 local 變數的位址，等於回傳一個「之後會被別的函式覆寫」的位址：

```c
char *format_key(const char *name, int w) {
    char key[64];
    snprintf(key, sizeof key, "%s@%d", name, w);
    return key;           /* 錯：key 在函式回傳後就不存在了 */
}
```

clang 與 gcc 對這種最直接的寫法會發出警告，但如果位址先存進 struct 或全域變數再帶出去，編譯器就看不出來。修法是由呼叫者提供緩衝區，或者在 heap 上配置並清楚註明「呼叫者負責 free」。

### 錯誤九：使用已釋放的 heap 記憶體

**Use-after-free**（UAF，釋放後使用）是指一塊記憶體已經 `free`，程式卻還透過舊指標讀寫它。指向已釋放記憶體的指標叫 **dangling pointer**（懸置指標）。`thumbd` 的快取淘汰就很容易寫出這種 bug：淘汰執行緒 `free` 了一個縮圖，但另一個請求手上還拿著指向它的指標。下一節會詳細看它為什麼會破壞 allocator。

### 錯誤十：memory leak

**Memory leak**（記憶體洩漏）是配置了記憶體，卻在不再需要之後沒有釋放，而且程式已經沒辦法再釋放它（指向它的指標都沒了）。單次 leak 通常很小，但長時間執行的服務會一點一點累積，正是 26.1 節 RSS 每天上升 300 MB 的樣子。

把十種錯誤整理成一張表，方便日後對照：

| # | 錯誤 | `thumbd` 裡的樣子 | 最可能抓到它的工具 |
|---|---|---|---|
| 1 | dereference 壞指標 | `sscanf` 忘了 `&` | 編譯器警告、segfault＋gdb |
| 2 | 讀未初始化記憶體 | 直方圖用 `malloc` 而非 `calloc` | 編譯器警告、Valgrind、MSan |
| 3 | stack buffer overflow | `strcpy` 複製 Host header | ASan、stack canary |
| 4 | 指標與物件大小混淆 | `sizeof(uint8_t)` 寫成列指標陣列大小 | ASan |
| 5 | off-by-one | 字串少配 1 byte、`i <= n` | ASan |
| 6 | 參照指標而非物件 | `*len--` | 編譯器警告、單元測試 |
| 7 | 誤解指標運算 | `p += sizeof(uint32_t)` | ASan |
| 8 | 參照不存在的變數 | 回傳 local 陣列位址 | 編譯器警告、ASan（stack-use-after-return 偵測，Linux 上預設開啟） |
| 9 | use-after-free | 快取淘汰後仍使用縮圖 | ASan、Valgrind |
| 10 | memory leak | 解碼失敗的錯誤路徑漏了 `free` | LSan、Valgrind、heap profiler |

## 26.4 Use-after-free 與 double free 如何破壞 heap

第 25 章介紹過，allocator 會把 free block 串成 free list，而「下一個 free block 在哪裡」這個指標，就存放在 free block 自己的 payload 裡，因為那段空間反正已經沒人用了。這個省空間的設計，正是 use-after-free 與 double free 危險的原因。

```text
 ① malloc 之後：程式擁有 payload
    ┌────────┬─────────────────────────────┬────────┐
    │ header │ payload：縮圖的像素資料      │ footer │
    │ 48 | a │ 程式透過 thumb 指標讀寫       │ 48 | a │
    └────────┴─────────────────────────────┴────────┘
             ▲ thumb

 ② free(thumb) 之後：allocator 把 payload 的開頭拿去存 free list 指標
    ┌────────┬───────────┬───────────┬─────┬────────┐
    │ header │ next 指標 │ prev 指標 │ ... │ footer │
    │ 48 | f │ 0x6020..  │ 0x6030..  │     │ 48 | f │
    └────────┴───────────┴───────────┴─────┴────────┘
             ▲ thumb（dangling pointer，仍然指向這裡）

 ③ use-after-free：thumb->pixels[0] = 0 寫到 next 指標上
    → free list 的鏈結被改成 0 或任意值
    → 之後某次 malloc 沿著 free list 走，跳到錯誤的位址，當機或回傳重疊的 block
```

在 ②，`thumb` 這個指標的值沒有任何改變，`free` 不會（也無法）把所有指向這塊記憶體的指標清掉。程式在 ③ 透過它寫入，寫到的是 allocator 的內部資料。這就是 26.1 節「當機在 `malloc` 裡」的典型成因：犯錯的是 `thumbd` 自己的程式碼，但第一個發現資料不一致的是 allocator。

Double free 也是同樣的道理。對同一塊記憶體 `free` 兩次，allocator 會把它插進 free list 兩次，之後兩次 `malloc` 可能回傳**同一塊**記憶體給兩個不同的使用者。兩個請求以為自己各有一塊緩衝區，其實在互相覆寫。現代的 glibc、jemalloc 對最簡單的 double free 有檢查，但檢查有限，不能依賴。

UAF 也是嚴重的安全問題。攻擊者如果能控制「釋放之後，這塊記憶體被重新配置給誰、填入什麼內容」，就能讓程式透過 dangling pointer 讀到攻擊者準備的資料，例如一個被偽造的函式指標（第 10 章）。瀏覽器與作業系統 kernel 的高風險漏洞中，UAF 長年佔了很大比例，這也是 Chrome、Android 等專案大量投資 sanitizer 與更安全語言的原因之一。

> [!warning] 常見誤解
> 「`free(p)` 之後加一行 `p = NULL` 就不會有 use-after-free。」這只能保護 `p` 這一個變數。如果同一塊記憶體的位址還被複製到別的地方（快取的 hash table、另一個 thread 的 local 變數、某個 struct 的欄位），那些副本仍然是 dangling pointer。真正的解法是釐清「誰擁有這塊記憶體、誰只是借用」，見 26.9 節。

## 26.5 Leak 的三種面貌：別把 RSS 上升都叫 leak

在回頭解決 26.1 節的 RSS 問題之前，要先釐清一件事：**RSS 持續上升不一定是 leak。** 第 23–25 章已經提過幾個會讓 RSS 變大的正常原因。把可能性分清楚，才不會花一週追一個不存在的 bug。

| 類型 | 意義 | 怎麼分辨 | 典型例子 |
|---|---|---|---|
| 真正的 leak（unreachable） | 配置後所有指向它的指標都消失，程式再也無法釋放 | leak 偵測工具在結束時報告「definitely lost」 | 錯誤處理路徑提早 `return`，漏了 `free` |
| 邏輯 leak（reachable but unused） | 指標還在，但程式永遠不會再用它 | 工具不會報；要看 heap profile 中哪個資料結構一直長 | 快取沒有上限、全域 list 只加不刪 |
| allocator 保留 | 程式已經 `free`，allocator 留著準備重用，沒有還給 kernel | 配置量（in-use bytes）穩定，但 RSS 不下降 | glibc 多個 arena、碎片讓 heap 頂端無法縮回（第 25 章） |
| 非 heap 的成長 | 增加的不是 malloc 的記憶體 | `/proc/PID/smaps` 看是哪個區域在長 | thread 數增加（每個 stack）、mmap 的檔案頁 |

這張表的關鍵是第二列：**邏輯 leak 是任何工具都抓不到的**，因為從記憶體的角度看，那些物件仍然「有人指著」。這也是為什麼有 GC 的語言仍然會 leak，26.8 節會再回來談。

判斷流程大致如下：

```text
 RSS 持續上升
   │
   ├─ 1. smaps_rollup／pmap：成長的是 heap（anonymous）還是檔案映射、stack？
   │       └─ 不是 heap → 查 thread 數、mmap 的使用，不是 malloc 的問題
   │
   ├─ 2. allocator 統計：in-use bytes 有沒有一起成長？
   │       （glibc malloc_info、jemalloc stats、自己加的計數器）
   │       └─ in-use 穩定、RSS 上升 → allocator 保留或碎片，考慮調整 allocator
   │
   ├─ 3. in-use 跟著上升 → 用 heap profiler 找「哪個呼叫點配置的記憶體一直沒有被釋放」
   │       （heaptrack、jemalloc prof、tcmalloc heap profiler）
   │
   └─ 4. 在測試環境用 LSan／Valgrind 重現
           ├─ 報告 definitely lost → 真正的 leak，看配置的 stack trace
           └─ 什麼都沒報 → 邏輯 leak，回頭看 profiler 指出的資料結構
```

`thumbd` 的案例走到第 3 步就有了答案：heap profiler 顯示，持續成長的記憶體幾乎全部來自 JPEG 解碼函式配置的原圖緩衝區。再看程式碼，解碼失敗時的錯誤處理路徑提早 `return`，忘了釋放已經配置的緩衝區。每天大約有一定比例的上傳圖片是損毀的，每張漏掉一個緩衝區，日積月累就是那條上升的線。26.10 節會用一個小程式重現這個情況。

## 26.6 AddressSanitizer：讓錯誤在發生的當下被抓到

### 為什麼需要它

26.2 節說過，記憶體錯誤難抓是因為「硬體的保護粒度是 page，C 物件是 bytes」。**AddressSanitizer**（ASan）的想法很直接：既然硬體不幫忙，就由編譯器在每一次記憶體存取前插入一小段檢查程式碼，以 byte 等級判斷這次存取是否合法。

用法只要在編譯與連結時加上旗標：

```bash
cc -g -O1 -fsanitize=address -fno-omit-frame-pointer thumbd.c -o thumbd-asan
```

`-g` 讓報告能顯示檔名與行號，`-fno-omit-frame-pointer` 讓 stack trace 更完整（第 9 章）。執行時一旦偵測到錯誤，ASan 會印出報告並結束程式。

### 怎麼運作：shadow memory 與 redzone

ASan 由三個部分組成：

1. **Shadow memory**（影子記憶體）：ASan 在位址空間中保留一大塊區域，每 8 bytes 的應用程式記憶體對應 1 byte 的 shadow，記錄這 8 bytes 裡有多少是可以存取的。
2. **Redzone**（紅區）：ASan 替換掉 `malloc`，每次配置時在 block 前後多留一段「禁區」，並在 shadow 中標記為不可存取。stack 上的陣列與全域變數周圍也會插入 redzone。越界存取一定會先踩進 redzone。
3. **Quarantine**（隔離區）：`free` 之後的記憶體不會馬上給下一個 `malloc` 重用，而是先標記為「已釋放」並放進一個先進先出的隔離區，延後重用。這讓 use-after-free 在一段時間內都能被抓到。

Shadow byte 的值有固定的意義：

| shadow 值 | 意義 |
|---|---|
| `00` | 對應的 8 bytes 全部可以存取 |
| `01`–`07`（記為 k） | 只有前 k bytes 可以存取，剩下的不行（物件大小不是 8 的倍數時的尾端） |
| `fa` | heap redzone（block 前後的禁區） |
| `fd` | 已釋放的 heap 記憶體 |
| `f1`、`f2`、`f3` | stack 陣列左、中、右的 redzone |
| `f9` | 全域變數的 redzone |

在 Linux x86-64 上，應用程式位址與 shadow 位址的換算是：

```text
shadow 位址 = (位址 >> 3) + 0x7fff8000
```

右移 3 位就是除以 8，對應「每 8 bytes 一個 shadow byte」。加上的常數是 shadow 區域的起點，不同平台的值不同（macOS arm64 上就不一樣），但原理相同。

編譯器在每一次讀寫之前插入的檢查，概念上是這樣（以 1 到 7 bytes 的小存取為例）：

```c
/* 編譯器在 *addr 之前插入的檢查（概念示意） */
int8_t k = *(int8_t *)((addr >> 3) + SHADOW_OFFSET);
if (k != 0 && (int8_t)((addr & 7) + size - 1) >= k)
    report_error(addr, size);       /* 印出報告並結束 */
```

如果 shadow 是 0，整個 8-byte 區塊都合法，一次比較就結束，這是絕大多數存取走的快速路徑。只有 shadow 不是 0 時，才需要再算「這次存取的最後一個 byte 落在區塊內的第幾個」。

### 手算一次：少配 1 byte 的字串

用 26.3 節錯誤五的情境：`malloc(strlen("200x200"))` 只配置了 7 bytes，ASan 把它放在位址 `0x6020000000f0`。接著 `strcpy` 要寫 8 bytes（7 個字元加上 `'\0'`）。

先看這 7 bytes 對應的 shadow。它們全部落在 `0x6020000000f0`–`0x6020000000f7` 這個 8-byte 區塊內（`0xf0` 是 8 的倍數），區塊中只有前 7 bytes 屬於這個物件，所以 shadow 值是 `07`。區塊後面接著的是 redzone，shadow 是 `fa`。

| 寫入的位址 | 區塊內位移 `addr & 7` | shadow 值 k | 判斷 `(addr & 7) + 1 − 1 >= k`？ | 結果 |
|---|---|---|---|---|
| `0x6020000000f0`（'2'） | 0 | 7 | 0 ≥ 7？否 | 合法 |
| `0x6020000000f6`（最後的 '0'） | 6 | 7 | 6 ≥ 7？否 | 合法 |
| `0x6020000000f7`（'\0'） | 7 | 7 | 7 ≥ 7？是 | **越界，回報** |

第一個越界的 byte 是 `0x6020000000f7`，正好就是 26.10 節 ASan 報告上寫的位址，報告還說它「located 0 bytes after 7-byte region」。如果是在 Linux x86-64 上，這個位址的 shadow 位於 `(0x6020000000f7 >> 3) + 0x7fff8000`，前半段 `0x6020000000f7 >> 3 = 0xc040000001e`，這是全部手算可以驗證的。

### 在真實系統長什麼樣：代價與限制

ASan 的代價不小，但通常可以接受。clang 的官方文件提到典型的執行速度大約變慢 2 倍；記憶體用量會因為 shadow、redzone 與 quarantine 而多出數倍，實際倍數依程式的配置模式而定。這個代價適合放在 CI 與測試環境，一般不會直接用在 production。

它也有明確的盲點：

| ASan 抓不到的情況 | 原因 | 補救 |
|---|---|---|
| 讀取未初始化的記憶體 | ASan 只追蹤「可不可以存取」，不追蹤「有沒有寫過」 | MemorySanitizer（clang，Linux）、Valgrind |
| 越界跳過整個 redzone，落在另一個合法物件上 | 例如 `a[10000]` 直接跳到很遠的另一個 block | 這種情況少見，但存在；配合程式碼審查與 fuzzing |
| struct 內部欄位之間的越界 | redzone 只放在整個物件周圍 | 把易越界的陣列獨立配置 |
| 釋放很久以後才發生的 UAF | quarantine 大小有限，舊的 block 最後還是會被重用 | 加大 `quarantine_size_mb` |
| 自訂的記憶體池（pool allocator） | ASan 只看到一大塊 `malloc`，看不到池內的小物件 | 用 ASan 提供的 `ASAN_POISON_MEMORY_REGION` 手動標記 |
| 沒有用 ASan 重新編譯的 library | 檢查是在編譯時插入的 | 關鍵的相依函式庫也用 ASan 編譯 |

> [!warning] 常見誤解
> 「ASan 跑過沒報錯，所以程式沒有記憶體錯誤。」ASan 只檢查**實際執行到**的路徑。如果測試沒有涵蓋「上傳一張損毀的 JPEG」，錯誤處理路徑上的 bug 就永遠不會被執行到。所以 ASan 最好搭配 fuzzing（自動產生大量奇怪輸入的測試方法），讓更多路徑被走到。

## 26.7 其他工具：UBSan、LeakSanitizer、Valgrind 與 macOS leaks

ASan 不是唯一的工具。每個工具抓不同類型的問題，代價也不同。

**UndefinedBehaviorSanitizer**（UBSan）用 `-fsanitize=undefined` 開啟，在可能觸發 undefined behavior 的運算前插入檢查：signed integer overflow（第 5 章）、shift 量超過型別寬度（第 3 章）、未對齊的指標存取、NULL 指標的成員存取等。它的代價比 ASan 小很多，而且預設在偵測到問題時只印出訊息、程式繼續執行，很適合長時間開著跑測試。

**LeakSanitizer**（LSan）是專門找 leak 的工具。在 Linux 上，它預設整合在 ASan 裡：程式結束時，LSan 從 stack、暫存器與全域變數出發，掃描所有還能被找到的 heap block，找不到的就是 leak，並印出它們被配置時的 stack trace。注意這個「從 root 出發找得到的才算活著」的想法，和 26.8 節的 garbage collection 完全一樣。macOS 的 Apple clang 不支援 LSan：在本機設 `ASAN_OPTIONS=detect_leaks=1` 執行，會得到「detect_leaks is not supported on this platform」的訊息。

**Valgrind** 的 Memcheck 工具走的是另一條路：不重新編譯，而是在執行時把程式的每一條機器碼翻譯成加上檢查的版本再執行（dynamic binary instrumentation，動態二進位插樁）。它的優點是不需要原始碼也能檢查，還能追蹤每個 bit 是否被初始化過，所以抓得到「讀取未初始化記憶體」；缺點是非常慢，程式通常會慢上數十倍。Valgrind 主要支援 Linux，Apple Silicon 的 macOS 上無法使用。

**macOS 的 `leaks`** 是系統內建的 leak 偵測工具，不需要重新編譯，用 `leaks --atExit -- ./程式` 執行即可在程式結束時掃描 heap。它和 LSan 一樣是從 root 出發掃描。

| 工具 | 啟用方式 | 抓得到 | 速度代價 | 平台 |
|---|---|---|---|---|
| ASan | `-fsanitize=address` 重新編譯 | 越界（heap／stack／global）、UAF、double free | 約 2 倍 | Linux、macOS、Windows |
| LSan | Linux 上 ASan 預設附帶，或 `-fsanitize=leak` | leak（程式結束時） | 執行時幾乎無，結束時掃描 | Linux（macOS 的 Apple clang 不支援） |
| UBSan | `-fsanitize=undefined` | signed overflow、錯誤 shift、未對齊存取等 UB | 小 | Linux、macOS |
| MSan | `-fsanitize=memory`（clang） | 讀取未初始化記憶體 | 約 3 倍，且所有程式碼都需用 MSan 編譯 | Linux |
| Valgrind Memcheck | `valgrind ./程式`，不需重新編譯 | 越界、UAF、未初始化、leak | 數十倍 | Linux 為主 |
| macOS `leaks` | `leaks --atExit -- ./程式` | leak | 小 | macOS |

一個實務上的組合是：CI 裡同時跑一個 ASan＋UBSan 的建置（在 Linux 上順便得到 LSan），定期跑一次 Valgrind 或 MSan 抓未初始化讀取，production 只用 heap profiler 觀察趨勢。

> [!note] Production 上的抽樣偵測
> 因為 ASan 太昂貴，有些大型專案在 production 用「抽樣」的方式偵測記憶體錯誤：只對極少數的配置加上保護頁，大部分配置照常進行。GWP-ASan 就是這類技術的代表。它抓不到每一個 bug，但在大量機器上長時間執行，累積起來仍能發現測試沒涵蓋到的錯誤。

## 26.8 Garbage collection：讓機器判斷什麼是垃圾

### 為什麼需要

前面七節的錯誤，有一大半來自同一個根源：**程式設計師必須自己決定「什麼時候 free」。** 太早 free 就是 use-after-free，free 兩次是 double free，忘了 free 就是 leak。**Garbage collection**（GC，垃圾回收）的想法是把這個決定交給執行環境：程式只管配置，不再呼叫 `free`；由 **garbage collector**（垃圾回收器）找出「不可能再被用到」的記憶體並自動回收。

### 怎麼運作：把記憶體看成一張圖

問題是：collector 怎麼知道哪些記憶體「不可能再被用到」？CS:APP 用一個很清楚的模型回答：把記憶體看成一張**有向圖**（directed graph）。

- 每一個 heap block 是一個節點。
- 如果 block A 裡存了指向 block B 的指標，就有一條邊 A → B。
- 有一類特殊的節點叫 **root**（根）：它們不在 heap 裡，但存著指向 heap 的指標，包括暫存器、stack 上的 local 變數、全域變數。

如果從任何一個 root 出發，沿著邊走得到某個 block，這個 block 就是 **reachable**（可達的），程式還有可能用到它；走不到的就是 **unreachable**（不可達的），程式再也不可能存取它，這就是垃圾。

```text
  roots（不在 heap 裡）                    heap
 ┌───────────────────┐
 │ 全域變數 cache  ──┼──────────▶ [thumb_A]
 │                   │
 │ stack：request ✗  │        ┌──▶ [thumb_B] ──▶ [meta]
 │（請求已結束，     │        │        ▲            │
 │  變數已不存在）   │        │        └────────────┘   B 與 meta 互相指著
 └───────────────────┘   (原本 request → B 的邊已經消失)

 從 roots 出發走得到：thumb_A                 → reachable，保留
 走不到：thumb_B、meta（即使它們互相指著）     → unreachable，回收
```

這張圖說明了一個重要觀念：**判斷垃圾的依據是「從 root 走不走得到」，不是「有沒有人指著它」。** `thumb_B` 和 `meta` 互相指著，但沒有任何 root 能走到它們，所以它們都是垃圾。

### Mark-and-sweep

**Mark-and-sweep**（標記－清除）是最基本的 tracing GC（追蹤式回收）演算法，分兩個階段：

1. **Mark（標記）**：從每一個 root 出發，對走到的每個 block 設一個 mark bit，並繼續走訪它指向的 block。已經標記過的就不再走，所以循環不會造成無窮迴圈。
2. **Sweep（清除）**：線性掃過整個 heap，沒有 mark bit 的 block 就呼叫 `free` 回收；有 mark bit 的清掉 bit，留給下一輪。

Mark 階段需要回答「這個值是不是指向某個 block 的指標，如果是，那個 block 從哪裡開始」。在 Java 這類語言裡，執行環境確切知道物件的每個欄位是什麼型別，所以能精確地找出指標。

### 保守式 GC：在 C 裡做 GC

C 沒有這種型別資訊。一個 8-byte 的值 `0x00007f3a12345678`，可能是指標，也可能只是剛好長這樣的整數或像素資料。CS:APP 討論的 C 語言 collector 採用**保守式**（conservative）策略：只要一個值「看起來像」指向某個已配置 block 的位址，就當它是指標。

這帶來兩個後果。第一，判斷錯誤只會往「保留」的方向錯：把整數誤認為指標，最多讓一個垃圾 block 被留下，不會把活著的 block 誤回收，所以 GC 仍然是安全的，只是可能回收得不夠乾淨。第二，因為不能確定某個值真的是指標，collector **不能移動物件**（移動了就得改寫所有指向它的指標，但它不敢改一個可能是整數的值），也就無法透過壓縮（compaction）消除碎片。

另外，C 的指標可以指向 block 的**中間**（例如 `p = buf + 100`），所以 collector 需要一種資料結構，能從任意位址快速找到「包含這個位址的 block」。CS:APP 提到的做法是用平衡二元樹記錄所有已配置的 block，依位址排序，查詢時找出起點不大於該位址的最後一個 block，再檢查位址是否落在它的範圍內。真實世界中，Boehm–Demers–Weiser 保守式 GC 就是這類 collector，可以直接用在 C 與 C++ 程式中。

### Reference counting 與現代 GC

除了 tracing，另一大類做法是 **reference counting**（參照計數）：每個物件記錄「有幾個指標指著我」，計數降到 0 就立刻回收。它的優點是回收及時、不需要停下來掃描整個 heap；缺點是每次指標賦值都要更新計數（多執行緒時還得用 atomic 操作），而且**無法回收循環參照**：上圖的 `thumb_B` 與 `meta` 互相指著，計數永遠至少是 1。

| 策略 | 怎麼判斷垃圾 | 能處理循環嗎 | 主要代價 | 代表 |
|---|---|---|---|---|
| Mark-and-sweep | 從 roots 追蹤，走不到的回收 | 能 | 掃描時的暫停、碎片 | CS:APP 的保守式 collector、Go（並行標記、不移動物件） |
| Copying／compacting | 把活著的物件搬到新區域，舊區域整塊回收 | 能 | 需要額外空間、要更新指標 | JVM 的年輕代 |
| Generational（分代） | 依「大多數物件很短命」的觀察，頻繁回收新物件、少回收老物件 | 能 | 實作複雜，需要記錄跨代指標 | JVM、.NET、V8 |
| Reference counting | 計數為 0 就回收 | 不能（需額外的循環偵測） | 每次賦值都更新計數 | CPython（另有循環偵測器）、Swift 與 Objective-C 的 ARC |

### 常見誤解：有 GC 就不會 leak

GC 回收的是 **unreachable** 的物件。26.5 節的「邏輯 leak」是 reachable 但不會再用到的物件，GC 對它無能為力。Java 服務裡沒有上限的 `HashMap` 快取、註冊了卻從不移除的 listener、放在 static 欄位裡的大集合，都會讓記憶體一直上升。GC 消除的是 use-after-free、double free 與「忘記 free」這三類錯誤，消除不了「設計上一直持有」的問題。

GC 也不管 file descriptor、socket、lock 這些非記憶體資源（第 27 章）。Java 的 `try-with-resources`、Python 的 `with` 存在的原因，就是 GC 回收物件的時間不確定，不能依賴它來關檔案。

## 26.9 RAII 與所有權：不靠 GC 也能管好記憶體

C++ 與 Rust 都沒有 tracing GC，卻能大幅減少記憶體錯誤。它們依靠的觀念叫**所有權**（ownership）：每一塊資源在任何時刻都有一個明確的「擁有者」，擁有者負責釋放它；其他人只能「借用」，借用期間不能超過擁有者的生命週期。

C++ 的 **RAII**（Resource Acquisition Is Initialization，資源取得即初始化）把所有權綁在物件的生命週期上：資源在建構函式中取得，在解構函式中釋放；物件離開作用域時，編譯器保證解構函式一定會被呼叫，不管是正常 `return`、提早 `return` 還是丟出例外。`std::unique_ptr` 代表「唯一擁有者」，`std::shared_ptr` 用 reference counting 代表「共同擁有」。Rust 更進一步，由編譯器的 borrow checker 在編譯時就拒絕「借用活得比擁有者久」的程式碼，從根本上排除 use-after-free。

C 沒有這些語言機制，但可以用紀律模仿同樣的想法。`thumbd` 團隊後來採用了以下規則：

```c
/* 規則一：一個函式內配置的資源，統一在函式尾端的 cleanup 區塊釋放 */
int handle_request(const req_t *req, resp_t *out) {
    int rc = -1;
    uint8_t *src = NULL, *dst = NULL;
    if (!(src = malloc(req->len))) goto out;
    if (decode_jpeg(req->body, req->len, src) < 0) goto out;   /* 錯誤路徑也走 out */
    if (!(dst = malloc(THUMB_BYTES))) goto out;
    resize(src, dst);
    out->body = dst;      /* 規則二：所有權轉移給呼叫者，明確寫出來 */
    dst = NULL;           /* 轉移後本地不再擁有，避免下面誤釋放 */
    rc = 0;
out:
    free(src);            /* free(NULL) 是合法的空操作，所以不必逐一判斷 */
    free(dst);
    return rc;
}
```

這種 `goto out` 的寫法在 Linux kernel 等大型 C 專案中非常普遍。它的好處是：不管從哪個錯誤點離開，都只有一個出口，釋放邏輯只寫一次，新增一個資源時也只要在 `out` 補一行。26.5 節那個「解碼失敗時漏 free」的 bug，用這種結構幾乎不可能寫出來。

| 做法 | 語言 | 誰保證釋放 | 能防止的錯誤 |
|---|---|---|---|
| 單一出口＋`goto out` | C | 程式設計師的紀律 | 錯誤路徑的 leak |
| `__attribute__((cleanup))` | C（gcc、clang 擴充） | 編譯器在變數離開作用域時呼叫指定函式 | leak |
| RAII、`unique_ptr` | C++ | 解構函式 | leak、double free（唯一擁有者） |
| `shared_ptr` | C++ | 參照計數歸零時 | 多個擁有者時的提早釋放；循環仍會 leak |
| ownership＋borrow checker | Rust | 編譯器 | leak 之外的大多數錯誤，包括 UAF 與 double free |
| tracing GC | Java、Go、C# | 執行環境 | UAF、double free、忘了 free（不含邏輯 leak） |

> [!tip] 在 C 的介面上寫清楚所有權
> 每個回傳指標的函式，都在註解或命名上寫明「呼叫者要不要 free」。例如 `char *thumb_key_new(...)` 用 `_new` 表示呼叫者擁有、要負責釋放；`const char *thumb_key_peek(...)` 用 `const` 與 `_peek` 表示只是借用，不能 free、也不能在物件被淘汰後繼續使用。

## 26.10 動手做：用 ASan 抓錯，用小程式重現 leak 與 GC

這一節有四個實驗：前兩個用 ASan 實際抓 bug（程式會被 ASan 中止、非 0 結束，所以標為 not-runnable），後兩個是可以直接執行的程式。執行環境都是 macOS arm64、Apple clang 21.0.0。

### 實驗一：快取淘汰後的 use-after-free

```c
// not-runnable：用 ASan 編譯時會被中止
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char key[32];
    unsigned char *pixels;
    size_t len;
} thumb_t;

static thumb_t *cache_slot;

int main(void) {
    thumb_t *t = malloc(sizeof *t);
    strcpy(t->key, "cat.jpg@200x200");
    t->len = 16;
    t->pixels = calloc(t->len, 1);
    cache_slot = t;                 /* 快取保留一份指標 */
    free(t->pixels);
    free(t);                        /* 淘汰：釋放了，卻忘了清掉 cache_slot */
    printf("key = %s\n", cache_slot->key);   /* use-after-free */
    return 0;
}
```

用 `cc -g -O1 -fsanitize=address -fno-omit-frame-pointer uaf.c -o uaf && ./uaf` 執行，輸出（擷取前半；結束碼 134，即 128 + 6，表示被 SIGABRT 終止）：

```text
==82395==ERROR: AddressSanitizer: heap-use-after-free on address 0x604000000410 at pc 0x0001009aee08 bp 0x00016fce1010 sp 0x00016fce07a0
READ of size 2 at 0x604000000410 thread T0
    #0 0x0001009aee04 in printf_common(void*, char const*, char*)+0x800 (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x1ee04)
    #1 0x0001009af9bc in printf+0x64 (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x1f9bc)
    #2 0x00010011c8e8 in main uaf.c:22
    #3 0x0001878004e0 in start+0x1b4c (dyld:arm64e+0x204e0)

0x604000000410 is located 0 bytes inside of 48-byte region [0x604000000410,0x604000000440)
freed by thread T0 here:
    #0 0x0001009d1258 in free+0x7c (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x41258)
    #1 0x00010011c8d8 in main uaf.c:21
    #2 0x0001878004e0 in start+0x1b4c (dyld:arm64e+0x204e0)

previously allocated by thread T0 here:
    #0 0x0001009d1164 in malloc+0x78 (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x41164)
    #1 0x00010011c878 in main uaf.c:15
    #2 0x0001878004e0 in start+0x1b4c (dyld:arm64e+0x204e0)

SUMMARY: AddressSanitizer: heap-use-after-free uaf.c:22 in main
Shadow bytes around the buggy address:
  0x604000000380: fa fa 00 00 00 00 00 00 fa fa 00 00 00 00 00 05
=>0x604000000400: fa fa[fd]fd fd fd fd fd fa fa fa fa fa fa fa fa
  0x604000000480: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
```

這份報告要由上往下讀，它一次回答了三個問題：

1. **發生了什麼、在哪裡**：第一行是錯誤類型 `heap-use-after-free`；`READ of size 2` 表示這次是讀取；stack trace 的 `#2 main uaf.c:22` 是我們程式中的那一行 `printf`。前兩層 `printf_common`、`printf` 是 ASan 攔截的 libc 函式，`printf` 在讀 `%s` 字串時被抓到。
2. **這塊記憶體是誰的**：`48-byte region` 就是 `sizeof(thumb_t)`（32 bytes 的 `key`、8 bytes 的指標、8 bytes 的 `len`）。`freed by thread T0 here` 指出它在第 21 行被釋放，`previously allocated` 指出它在第 15 行被配置。對 UAF 來說，「在哪裡被釋放」往往是最關鍵的線索，因為那裡就是所有權出問題的地方。
3. **shadow 長什麼樣**：中括號標出的 `[fd]` 就是被存取的位址，`fd` 代表已釋放；它加上後面連續五個 `fd`，共 6 個 shadow byte，對應 6 × 8 = 48 bytes，剛好是整個 block。前後的 `fa` 是 redzone。

沒有 ASan 時，這支程式在大多數情況下會「正常」印出 `key = cat.jpg@200x200`，因為被釋放的記憶體內容還沒被覆寫。這正是 UAF 危險的地方：測試會通過。

### 實驗二：少配 1 byte 與 double free

把 26.3 節錯誤五的情境寫成一個小函式 `dup_size`，用 `-O0` 編譯讓 `strcpy` 保持為函式呼叫：

```c
// not-runnable：用 ASan 編譯時會被中止
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 把 "200x200" 這種尺寸字串複製到 heap：少算了結尾的 '\0' */
static char *dup_size(const char *s) {
    char *p = malloc(strlen(s));        /* bug：應該是 strlen(s) + 1 */
    strcpy(p, s);
    return p;
}

int main(void) {
    char *size = dup_size("200x200");
    printf("size = %s\n", size);
    free(size);
    return 0;
}
```

`cc -g -O0 -fsanitize=address obo.c -o obo && ./obo` 的輸出（擷取）：

```text
==82578==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000000f7 at pc 0x000100f72a20 bp 0x00016f7e9040 sp 0x00016f7e87f0
WRITE of size 8 at 0x6020000000f7 thread T0
    #0 0x000100f72a1c in strcpy+0x458 (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x3aa1c)
    #1 0x000100614888 in dup_size obo.c:9
    #2 0x000100614828 in main obo.c:14
    #3 0x0001878004e0 in start+0x1b4c (dyld:arm64e+0x204e0)

0x6020000000f7 is located 0 bytes after 7-byte region [0x6020000000f0,0x6020000000f7)
allocated by thread T0 here:
    #0 0x000100f79164 in malloc+0x78 (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x41164)
    #1 0x000100614878 in dup_size obo.c:8
    #2 0x000100614828 in main obo.c:14
    #3 0x0001878004e0 in start+0x1b4c (dyld:arm64e+0x204e0)

SUMMARY: AddressSanitizer: heap-buffer-overflow obo.c:9 in dup_size
```

`WRITE of size 8` 是 `strcpy` 這次呼叫要寫的總量（7 個字元加 `'\0'`），回報的位址是第一個越界的 byte `0x6020000000f7`，和 26.6 節的手算表完全一致。`0 bytes after 7-byte region` 是 off-by-one 的招牌描述：剛好超出尾端 0 個 byte，也就是緊貼著的第一個 byte。

同樣的方法對 double free 也有效。把一個 1,024 bytes 的緩衝區用同一個 `image_release` 函式釋放兩次，ASan 的報告是：

```text
==83399==ERROR: AddressSanitizer: attempting double-free on 0x619000000580 in thread T0:
    #0 0x000102d61258 in free+0x7c (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x41258)
    #1 0x0001026187f8 in image_release df.c:5
    #2 0x000102618710 in main df.c:10

0x619000000580 is located 0 bytes inside of 1024-byte region [0x619000000580,0x619000000980)
freed by thread T0 here:
    #0 0x000102d61258 in free+0x7c (libclang_rt.asan_osx_dynamic.dylib:arm64e+0x41258)
    #1 0x0001026187f8 in image_release df.c:5
    #2 0x000102618708 in main df.c:9
```

兩次 `free` 都在第 5 行，但呼叫者分別是第 9 行與第 10 行，stack trace 讓你一眼看出「同一個釋放函式被兩條路徑呼叫」。

順帶看 UBSan。把 `int bytes = width * height * 4;` 用 40000 × 30000 去算，並把 `1u << 32` 寫進程式，以 `cc -g -O0 -fsanitize=undefined ub.c` 編譯執行：

```text
ub.c:7:32: runtime error: signed integer overflow: 1200000000 * 4 cannot be represented in type 'int'
SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ub.c:7:32 
ub.c:9:24: runtime error: shift exponent 32 is too large for 32-bit type 'unsigned int'
SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ub.c:9:24 
bytes = 505032704, mask = 1
```

UBSan 回報兩處 undefined behavior 後讓程式繼續跑，最後一行是這次實際得到的值；這兩個值本身是 UB 的結果，換編譯器或最佳化等級可能不同，不能依賴。第 5 章的 `thumbd` 寬×高×4 溢位，用 UBSan 在測試中就能直接抓到。

### 實驗三：重現 `thumbd` 的錯誤路徑 leak

這支可以直接執行的程式用巨集包住 `malloc`／`free`，記錄每一塊配置來自哪一行，結束時列出還沒釋放的配置。這正是 heap profiler 與 LSan 背後的核心想法，只是簡化到極致。

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 極簡配置追蹤器：每次配置記下「哪一行要的」，free 時劃掉。
 * 程式結束前列出還活著的配置，就是 leak 的候選名單。 */
#define MAX_LIVE 1024
typedef struct { void *p; size_t n; const char *file; int line; } rec_t;
static rec_t live[MAX_LIVE];

static void *track_malloc(size_t n, const char *file, int line) {
    void *p = malloc(n);
    for (int i = 0; p && i < MAX_LIVE; i++)
        if (!live[i].p) { live[i] = (rec_t){p, n, file, line}; break; }
    return p;
}
static void track_free(void *p) {
    for (int i = 0; p && i < MAX_LIVE; i++)
        if (live[i].p == p) { live[i].p = NULL; break; }
    free(p);
}
#define MALLOC(n) track_malloc((n), __FILE__, __LINE__)
#define FREE(p)   track_free(p)

/* 模擬 thumbd 處理一個請求：解碼 → 縮放 → 回傳 */
static int handle_request(int id, int corrupt) {
    unsigned char *src = MALLOC(64 * 1024);   /* 原圖解碼緩衝區 */
    unsigned char *dst = MALLOC(16 * 1024);   /* 縮圖輸出緩衝區 */
    if (!src || !dst) { FREE(src); FREE(dst); return -1; }
    memset(src, id, 64 * 1024);
    if (corrupt) {          /* 解碼失敗的錯誤路徑：只釋放了 dst */
        FREE(dst);
        return -1;          /* bug：src 沒有釋放 */
    }
    memcpy(dst, src, 16 * 1024);
    FREE(src);
    FREE(dst);
    return 0;
}

int main(void) {
    int failed = 0;
    for (int id = 0; id < 100; id++)
        if (handle_request(id, id % 25 == 7) != 0) failed++;   /* 每 25 個請求有 1 張壞圖 */
    size_t bytes = 0; int count = 0;
    for (int i = 0; i < MAX_LIVE; i++)
        if (live[i].p) {
            if (count == 0) printf("仍未釋放的配置來自 %s:%d\n", live[i].file, live[i].line);
            bytes += live[i].n; count++;
        }
    printf("處理 100 個請求，失敗 %d 個\n", failed);
    printf("結束時仍有 %d 塊、共 %zu bytes 沒有釋放\n", count, bytes);
    return 0;
}
```

存成 `track.c`，以 `cc -std=c17 -O1 -Wall -Wextra track.c -o track && ./track` 在 macOS arm64 上執行：

```text
仍未釋放的配置來自 track.c:27
處理 100 個請求，失敗 4 個
結束時仍有 4 塊、共 262144 bytes 沒有釋放
```

逐行解讀：

1. `track.c:27` 是 `src` 的那一行 `MALLOC`。工具只能告訴你「誰配置的沒被釋放」，不能告訴你「該在哪裡釋放」；但知道配置點後，往下看它的所有離開路徑，就會找到第 33 行那個提早的 `return`。
2. 100 個請求中 id 為 7、32、57、82 的四個是壞圖，每個漏掉 64 KiB，合計 4 × 65,536 = 262,144 bytes，數字完全對得上。
3. 換算到 production：如果 `thumbd` 每天處理數百萬個請求，其中一小部分是損毀的圖片，每個漏 64 KiB 以上（真實的解碼緩衝區通常更大），就足以產生 26.1 節每天數百 MB 的成長。

修法就是 26.9 節的 `goto out` 結構。也可以在 macOS 上不改程式，直接用系統的 `leaks` 檢查。把一支「配置三次 4,096 bytes、從不釋放」的小程式以 `MallocStackLogging=1 leaks --atExit -- ./leak2` 執行，報告的關鍵部分是：

```text
Process 79510: 2 leaks for 10240 total leaked bytes.

STACK OF 2 INSTANCES OF 'ROOT LEAK: <malloc in make_thumb>':
3   dyld                                  0x1878004e4 start + 6992
2   leak2                                 0x10058c440 main + 48  leak.c:5
1   leak2                                 0x10058c480 make_thumb + 24  leak.c:3
0   libsystem_malloc.dylib                0x1879f71fc _malloc_zone_malloc_instrumented_or_legacy + 152 
```

這裡有兩個值得注意的細節。第一，每塊記為 5,120 bytes 而不是 4,096 bytes。這不是正常執行時的大小：同一支程式不設 `MallocStackLogging` 時，`malloc_size` 回報的是 4,096；設了之後，配置改走 libmalloc 會記錄 stack 的另一條路徑（報告中的 `_malloc_zone_malloc_instrumented_or_legacy`），`malloc_size` 變成 5,104，block 被放大到 5,120。換句話說，除錯工具本身也會改變配置的方式，報告中的大小要當成近似值看。第二，程式漏了三塊，工具只報了兩塊。`leaks` 和 LSan 一樣是從 stack 與暫存器出發做保守式掃描，最後一次配置的指標很可能還殘留在某個 stack 位置或暫存器裡，看起來仍然 reachable，所以沒被算成 leak。這正是 26.8 節保守式 GC 的特性（Q5 會再解釋）：寧可少報，也不誤報。

### 實驗四：mark-and-sweep 與 reference counting 的差別

這支程式建立 26.8 節那張圖：`cache → thumb_A`、`request → thumb_B`、`thumb_B ↔ meta` 互相指著。請求結束後，比較兩種回收方法的判斷。

```c
#include <stdio.h>

/* 玩具 heap：8 個物件，每個最多指向 2 個物件。
 * 比較 reference counting 與 mark-and-sweep 對「循環參照」的處理。 */
#define N 8
typedef struct { int in_use, marked, refcnt; int ref[2]; const char *name; } obj_t;
static obj_t heap[N];
static int roots[N], nroots;

static int new_obj(const char *name) {
    for (int i = 0; i < N; i++)
        if (!heap[i].in_use) {
            heap[i] = (obj_t){1, 0, 0, {-1, -1}, name};
            return i;
        }
    return -1;
}
static void link_to(int from, int slot, int to) { heap[from].ref[slot] = to; heap[to].refcnt++; }

static void mark(int i) {                 /* 從 root 出發做深度優先走訪 */
    if (i < 0 || heap[i].marked) return;  /* 已標記就停，循環不會無窮遞迴 */
    heap[i].marked = 1;
    mark(heap[i].ref[0]);
    mark(heap[i].ref[1]);
}
static void sweep(void) {                 /* 沒被標記的就是垃圾 */
    for (int i = 0; i < N; i++) {
        if (!heap[i].in_use) continue;
        if (!heap[i].marked) { printf("  回收 %-10s（refcnt 仍是 %d）\n", heap[i].name, heap[i].refcnt); heap[i].in_use = 0; }
        heap[i].marked = 0;
    }
}

int main(void) {
    int cache = new_obj("cache"), a = new_obj("thumb_A"), b = new_obj("thumb_B");
    int req = new_obj("request"), meta = new_obj("meta");
    link_to(cache, 0, a);                 /* cache → A */
    link_to(req, 0, b);                   /* request → B */
    link_to(b, 0, meta);                  /* B → meta */
    link_to(meta, 0, b);                  /* meta → B：循環參照 */
    roots[nroots++] = cache;              /* 全域變數 cache 是 root */
    roots[nroots++] = req;                /* stack 上的 request 也是 root */

    nroots--;                             /* 請求結束，request 離開 stack */
    heap[b].refcnt--;                     /* 只有 request 不在了，但 B ↔ meta 仍互指 */
    printf("reference counting 的看法：B 的 refcnt = %d、meta 的 refcnt = %d → 都不會被回收\n",
           heap[b].refcnt, heap[meta].refcnt);

    printf("mark-and-sweep：\n");
    for (int r = 0; r < nroots; r++) mark(roots[r]);
    sweep();
    for (int i = 0; i < N; i++) if (heap[i].in_use) printf("  存活 %s\n", heap[i].name);
    return 0;
}
```

在 macOS arm64 上以 `cc -std=c17 -O1 -Wall -Wextra gc.c -o gc && ./gc` 執行：

```text
reference counting 的看法：B 的 refcnt = 1、meta 的 refcnt = 1 → 都不會被回收
mark-and-sweep：
  回收 thumb_B   （refcnt 仍是 1）
  回收 request   （refcnt 仍是 0）
  回收 meta      （refcnt 仍是 1）
  存活 cache
  存活 thumb_A
```

解讀：

1. 請求結束後，`request` 不再是 root。reference counting 看到 `thumb_B` 與 `meta` 的計數都還是 1（它們互相指著），所以認為兩者都還活著，這兩個物件就永遠漏掉了。
2. Mark-and-sweep 從唯一剩下的 root `cache` 出發，只標記到 `cache` 與 `thumb_A`。Sweep 時，沒被標記的 `thumb_B`、`request`、`meta` 全部回收，即使其中兩個的 refcnt 不是 0。
3. `mark` 函式開頭的 `heap[i].marked` 檢查是處理循環的關鍵：如果 `cache` 也指向 `thumb_B`，走到 `meta → thumb_B` 時會發現已經標記過，就不會無窮遞迴。

這就是 CPython 為什麼除了 reference counting 之外，還需要一個定期執行的循環偵測器（`gc` 模組）：只靠計數，互相參照的物件群永遠不會被回收。

## 26.11 在工作上怎麼用

### 情境一：把 sanitizer 放進 CI

最划算的投資是讓每一次提交都經過 sanitizer。`thumbd` 團隊的 CI 有三個建置：

```bash
# 一般建置：開最多警告，警告視為錯誤
cc -O2 -Wall -Wextra -Werror ...

# ASan + UBSan 建置：跑完整的單元測試與整合測試
cc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer ...
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ./run_tests

# 每晚：Valgrind 跑一次較慢的完整測試，抓未初始化讀取
valgrind --leak-check=full --error-exitcode=1 ./thumbd-test
```

`UBSAN_OPTIONS=halt_on_error=1` 讓 UBSan 在第一個錯誤就以非 0 結束，否則 CI 會因為程式繼續執行而顯示綠燈。ASan 的報告一律要求開發者在修好之前不能合併，因為記憶體錯誤不會「自己好」。另外，`thumbd` 團隊針對 JPEG、PNG 解析器寫了 fuzzing 測試，用 ASan 建置執行，專門產生各種損毀的圖片，讓錯誤處理路徑被大量走到。

### 情境二：production 的 RSS 一直漲

照 26.5 節的流程圖做，以下是實際會用到的指令（Linux 上；輸出依系統而定）：

```bash
# 1. 看 RSS 趨勢：每分鐘記一次
ps -o pid,rss,vsz,etime -p "$(pgrep thumbd)"

# 2. 拆分記憶體來源：Anonymous（heap、stack）還是檔案映射
cat /proc/$(pgrep thumbd)/smaps_rollup

# 3. 找出最大的映射區域
pmap -x $(pgrep thumbd) | sort -k3 -n | tail

# 4. 用 heap profiler 找出配置點（heaptrack 不需要重新編譯）
heaptrack ./thumbd --config test.conf
heaptrack_print heaptrack.thumbd.*.zst | head -50
```

判斷時的檢查清單：

- RSS 上升的速度和請求量成正比嗎？如果是，leak 多半出在每個請求都會走到的路徑。
- 和「錯誤率」成正比嗎？如果某類錯誤（例如 400 Bad Request、解碼失敗）變多時 RSS 漲得更快，就去看錯誤處理路徑。
- RSS 上升後，重啟以外有沒有任何事件會讓它下降？如果流量低峰時 in-use bytes 下降但 RSS 不降，比較像 allocator 保留而不是 leak。
- 最近有沒有加快取？沒有上限或淘汰機制的快取就是邏輯 leak。

### 情境三：收到「當機在 malloc 裡」的 core dump

這幾乎都是 heap 早就被寫壞了。處理順序：

1. 不要在 `malloc` 周圍找 bug。先記下當機時正在處理什麼請求（log 裡的 request id、圖片格式）。
2. 用 ASan 建置重現：把同一批請求（或同類型的圖片）餵給 ASan 版的 `thumbd`。ASan 會在**第一次**越界或 UAF 時就停下來，指出真正的原因。
3. 如果無法重現，在 staging 上用 ASan 版承接一部分複製流量，或在 production 啟用抽樣式偵測。
4. 修好後，把觸發 bug 的輸入加進 fuzzing 的種子語料與回歸測試。

`thumbd` 的 `malloc(): corrupted top size` 最後就是這樣找到的：ASan 指出 EXIF 解析器在處理某種相機寫入的異常長度欄位時，`memcpy` 多複製了資料，越過了緩衝區尾端。

### 情境四：設計新模組時就決定所有權

在寫程式碼之前，先回答三個問題：每塊資源由誰配置、由誰擁有、在什麼時間點釋放。把答案寫在標頭檔的註解裡，並用 26.9 節的命名慣例反映在函式名稱上。對多執行緒共享的物件（例如快取中的縮圖），擁有權問題會更複雜，常見的解法是讓快取持有參照計數，借用者在使用期間增加計數、用完減少，計數歸零時才真正釋放；第 31 章會討論這類計數本身的 race 問題。

## 26.12 常見錯誤與除錯

| 症狀 | 常見原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 當機在 `malloc`／`free` 內部，訊息如 `corrupted size`、`double free or corruption` | 之前某處越界寫入或 UAF 弄壞了 allocator 的 metadata | 用 ASan 建置重現，看第一個報告 | 修正真正越界的那一行，不是 `malloc` 那一行 |
| 同樣的輸入，結果偶爾不一樣 | 讀到未初始化的 heap 或 stack 記憶體 | `-Wall` 警告；Valgrind 的「uninitialised value」；MSan | `calloc`、宣告時初始化、檢查所有分支都有賦值 |
| RSS 持續上升 | 真正的 leak、邏輯 leak、allocator 保留 | 26.5 節流程：smaps、in-use bytes、heap profiler、LSan | 錯誤路徑用 `goto out`；快取加上上限；調整 allocator |
| 程式在測試環境正常，加上 ASan 後報錯 | 測試原本就有記憶體錯誤，只是沒有症狀 | 讀 ASan 報告的配置與釋放位置 | 修 bug，不要關掉 ASan |
| 加上 `-O2` 後行為改變，`-O0` 正常 | 程式依賴 undefined behavior（溢位、越界、未初始化） | UBSan、ASan 在 `-O2` 下重跑 | 消除 UB，不要以「改回 `-O0`」解決 |
| ASan 報 UAF，但釋放的程式碼看起來沒錯 | 指標的副本被其他資料結構或執行緒保存 | 看報告中的 `freed by thread` 與目前執行緒是否不同 | 釐清所有權，用參照計數或延後釋放 |
| 有 GC 的服務記憶體也一直漲 | 邏輯 leak：無上限快取、未移除的 listener | heap dump 分析哪個集合一直長 | 加上上限與淘汰、用 weak reference、移除註冊 |

> [!tip] 重現困難時先縮小輸入
> 記憶體 bug 常常只在特定輸入下觸發。保留觸發當機的那張圖片，用 fuzzing 工具內建的最小化功能把它縮到最小，再在 ASan 建置下執行。輸入越小，報告越容易對應到程式碼。

## 26.13 動手練習

1. **延伸實驗三的程式**：把 `handle_request` 改寫成 26.9 節的 `goto out` 結構，再次執行，確認「結束時仍有 0 塊」。接著故意引入一個 double free（例如在 `out:` 之前多呼叫一次 `FREE(dst)`），讓 `track_free` 偵測到「要釋放的指標不在 `live` 表中」並印出警告。
2. **手算 shadow**：在 Linux x86-64 上，ASan 把一個 `malloc(13)` 的 block 放在 `0x602000000050`。這 13 bytes 對應幾個 shadow byte？每個的值是多少？對 `0x60200000005c` 與 `0x60200000005d` 各做 1 byte 的寫入，哪一個會被回報？寫出計算過程。（答案：兩個 shadow byte，值為 `00` 與 `05`；`0x5c` 的區塊內位移是 4，4 < 5 合法；`0x5d` 位移 5，5 ≥ 5 回報越界。）
3. **用 ASan 抓自己的 bug**：寫一支程式，在 stack 上宣告 `char key[16]`，用迴圈 `for (int i = 0; i <= 16; i++) key[i] = 'a';` 寫入。分別用一般方式與 `-fsanitize=address` 編譯執行，比較結果，並找出報告中的 `f3`（stack 右側 redzone）。
4. **延伸實驗四的程式**：加上第三個 root（例如一個「最近存取」list）指向 `meta`，預測 mark-and-sweep 會留下哪些物件，再執行驗證。接著實作一個簡單的「循環偵測」：對所有 refcnt 不為 0 的物件，扣掉來自其他 heap 物件的參照，剩下為 0 的就是只被循環撐住的候選。
5. **分辨 leak 的類型**：寫一支程式，一部分配置在函式結束時遺失指標（真正的 leak），另一部分存進一個全域陣列但不再使用（邏輯 leak）。在 Linux 上用 LSan，或在 macOS 上用 `leaks --atExit`，確認工具只報告前者。
6. **在工作上**：挑一個你維護的 C 或 C++ 專案，加上一個 ASan＋UBSan 的建置並執行既有的測試。記錄找到幾個問題、各屬於 26.3 節的哪一類。

## 本章重點整理

- C 的越界、use-after-free、讀取未初始化記憶體都是 undefined behavior；硬體只以 page 為單位保護，所以這些錯誤常常不會立刻當機，而是在之後無關的地方出現症狀。
- CS:APP 列出十種典型錯誤：壞指標、未初始化、stack overflow、指標與物件大小混淆、off-by-one、參照指標而非物件、誤解指標運算、參照不存在的變數、use-after-free、memory leak。
- free block 的 payload 被 allocator 拿去存 free list 指標，所以 use-after-free 與 double free 會直接破壞 allocator 的資料結構，造成「當機在 malloc 裡」。
- RSS 上升可能是真正的 leak、邏輯 leak、allocator 保留或非 heap 的成長；要先用 smaps、allocator 統計與 heap profiler 區分，再決定怎麼修。
- ASan 用 shadow memory（每 8 bytes 一個 shadow byte）、redzone 與 quarantine 在每次存取前檢查合法性，能在錯誤發生的當下抓到越界、UAF 與 double free，代價約 2 倍速度。
- Shadow 值 k 表示 8-byte 區塊中只有前 k bytes 合法；存取的最後一個 byte 位移大於等於 k 就是越界，這個規則可以手算驗證。
- ASan 抓不到未初始化讀取、跳過 redzone 的越界、自訂記憶體池內的錯誤，以及沒有被執行到的路徑；需要搭配 MSan、Valgrind 與 fuzzing。
- UBSan 抓 signed overflow 與錯誤 shift 等 UB；LSan 在 Linux 上與 ASan 一起找 leak；Valgrind 不需重新編譯但慢數十倍；macOS 可用內建的 `leaks`。
- Garbage collection 把記憶體看成以 root 為起點的有向圖，從 root 走不到的 block 就是垃圾；判斷依據是 reachability，不是「有沒有人指著」。
- Mark-and-sweep 先從 root 標記所有 reachable block，再掃過 heap 回收沒有標記的；C 的保守式 GC 把看起來像指標的值都當成指標，安全但可能少回收，而且不能移動物件。
- Reference counting 回收及時，但無法處理循環參照；CPython 因此另外有循環偵測器。
- GC 消除了 UAF、double free 與忘記 free，但不能消除邏輯 leak，也不管理 file descriptor 等非記憶體資源。
- C++ 的 RAII 與 Rust 的 ownership 把釋放綁在作用域或編譯期檢查上；C 可以用單一出口的 `goto out` 結構與清楚的所有權命名，達到類似的效果。

## 延伸問答

> [!question]- Q1. 為什麼 heap 上越界寫入 8 bytes 通常不會立刻 segfault，stack 上的陣列越界也常常沒事？
> Segfault 來自 MMU 的檢查，而 MMU 只看「這個 page 是否映射、權限是否允許」（第 23 章）。heap 上一個 block 的尾端之後，通常緊接著同一個 page 裡的下一個 block 或 allocator 的 metadata，這段記憶體是合法映射、可寫的，所以硬體完全不會阻止。stack 也一樣，陣列後面是其他 local 變數、saved register 與 return address，都在同一段可寫的 stack 區域裡。
>
> 只有越界的距離大到跨進未映射的 page，或碰到唯讀頁時，才會立刻當機。所以「沒有 segfault」完全不能證明沒有越界，這正是需要 ASan 用 byte 等級的 shadow memory 檢查的原因。stack 上的 return address 被蓋掉時，通常要等函式 `return` 才會出事，第 11 章的 stack canary 就是針對這種情況。

> [!question]- Q2. 程式碼審查題：下面這段有什麼問題？`void cache_evict(thumb_t *t) { free(t->pixels); free(t); t = NULL; }`
> `t = NULL` 只改了函式參數這個 local 變數的副本，呼叫者手上的指標、快取 hash table 中的指標都沒有被清掉，它們在函式回傳後全部變成 dangling pointer。所以這一行完全沒有防護效果，反而給人「已經處理過了」的錯覺。
>
> 更根本的問題是所有權：如果其他請求可能還在使用這個縮圖，淘汰時直接 `free` 就是 use-after-free 的來源。比較安全的設計是讓快取與借用者共同持有參照計數，淘汰只是把它從快取移除並減少計數，最後一個使用者用完時才真正釋放；或者在 C 中把參數改成 `thumb_t **`，至少能把呼叫者的那份指標清成 NULL。

> [!question]- Q3. 手算題：ASan 在 Linux x86-64 上，位址 `0x602000000010` 的 shadow byte 在哪裡？如果它的值是 `02`，對 `0x602000000011` 做 2 bytes 的讀取會被回報嗎？
> Shadow 位址是 `(0x602000000010 >> 3) + 0x7fff8000`。右移 3 位得到 `0xc0400000002`，加上 `0x7fff8000` 得到 `0xc047fff8002`。
>
> 值 `02` 表示這個 8-byte 區塊只有前 2 bytes 合法，也就是 `0x...10` 與 `0x...11`。2 bytes 的讀取從 `0x...11` 開始，最後一個 byte 是 `0x...12`，它在區塊內的位移是 `(0x11 & 7) + 2 − 1 = 1 + 1 = 2`。因為 2 ≥ 2，ASan 會回報越界：第一個 byte 合法，但第二個 byte 超出了物件。這個例子說明檢查看的是「存取範圍的最後一個 byte」，而不只是起始位址。

> [!question]- Q4. 你在 production 看到 `thumbd` 的 RSS 一週內從 600 MB 升到 2 GB，但用 LSan 跑完整的測試沒有任何報告。可能是什麼原因？下一步怎麼做？
> 第一種可能是 leak 出現在測試沒涵蓋的路徑上，例如某種只在真實流量中出現的損毀圖片，LSan 只能報告實際執行到的路徑。第二種是邏輯 leak：記憶體仍被某個資料結構持有（例如沒有上限的快取），從 root 走得到，LSan 認為它是活的。第三種是根本不是 leak：allocator 保留、碎片，或 thread 數增加造成的 stack 成長。
>
> 下一步要先用 `/proc/PID/smaps_rollup` 確認成長的是 anonymous 記憶體，再比較 allocator 的 in-use bytes 與 RSS：in-use 也在漲就用 heap profiler（例如 heaptrack）找持續增加的配置點；in-use 穩定而 RSS 漲，就往 allocator 的設定與碎片方向查（第 25 章）。同時觀察 RSS 成長速度和錯誤率、請求類型的關係，常常能直接指出是哪條路徑。

> [!question]- Q5. 為什麼保守式 GC 不會誤回收活著的物件，卻可能讓垃圾留下來？
> 保守式 GC 在掃描 root 與 heap 時，只要遇到一個「數值上落在某個已配置 block 範圍內」的值，就把它當成指標，並標記那個 block。真正的指標一定會被這個規則抓到，所以所有 reachable 的 block 都會被標記，不會有活著的物件被誤回收，這就是它「安全」的原因。
>
> 反過來，一個剛好等於某個 block 位址的整數、像素值或殘留在 stack 上的舊指標，也會被當成指標，讓本來已經是垃圾的 block 繼續存活，甚至連帶撐住它指向的其他 block。因此保守式 GC 只能保證「不多回收」，不保證「回收乾淨」。26.10 節 macOS `leaks` 漏報最後一塊 leak，就是同一種保守式掃描的表現。

> [!question]- Q6. 面試題：Java 有 GC，為什麼還會發生 memory leak？舉例說明。
> GC 回收的是從 root 走不到的物件。Java 的 memory leak 幾乎都是「還走得到，但程式不會再用」的邏輯 leak。常見的例子有：放在 static 欄位裡、只加不刪的 `HashMap` 快取；向事件系統註冊了 listener，但物件不用之後忘了取消註冊，事件系統仍持有它；`ThreadLocal` 在 thread pool 中沒有清除，值跟著長壽的 thread 一直存活。
>
> 這類問題的診斷方法是拍 heap dump，看哪個集合或物件類型的數量隨時間成長，以及它們被誰持有（retention path）。修法則是設計層面的：快取要有上限與淘汰策略，註冊要成對地取消，必要時用 weak reference 讓「只被快取指著」的物件可以被回收。GC 的價值在於消除 UAF 與 double free，不是讓設計者不必思考物件的生命週期。

> [!question]- Q7. 為什麼 CI 裡的 ASan 建置通常用 `-O1` 而不是 `-O0` 或 `-O2`？ASan 版可以直接上 production 嗎？
> `-O0` 會產生大量冗餘的記憶體存取，每一次都要經過 ASan 的檢查，跑得非常慢；`-O2` 以上的激進最佳化可能把一些存取合併或刪掉，讓報告的行號與原始碼對不太起來。`-O1` 是常見的折衷：速度可以接受，報告仍然清楚。不過這不是絕對規則，在 `-O2` 下跑 ASan 也很有價值，因為某些 UB 只在最佳化後才會出現症狀。
>
> ASan 版不建議直接當 production 主力：速度大約慢 2 倍，記憶體用量多出數倍，ASan 的 runtime 本身也不是為了抵抗攻擊而設計的。Production 上更實際的做法是抽樣式偵測（例如 GWP-ASan 這類技術），或在 staging 用 ASan 版承接一部分複製流量。

> [!question]- Q8. 找錯題：下面的程式有幾個記憶體錯誤？`char *join(const char *a, const char *b) { char *r = malloc(strlen(a) + strlen(b)); strcpy(r, a); strcat(r, b); return r; }`，呼叫端 `printf("%s\n", join(dir, name));`
> 至少兩個。第一，配置大小少了結尾 `'\0'` 的 1 byte，應該是 `strlen(a) + strlen(b) + 1`，這是典型的 off-by-one，`strcat` 寫入最後的 `'\0'` 時會越界一個 byte，ASan 會回報 `0 bytes after N-byte region`。第二，沒有檢查 `malloc` 是否回傳 NULL，失敗時 `strcpy` 會 dereference NULL。
>
> 第三個在呼叫端：`join` 回傳的是呼叫者擁有的 heap 記憶體，但 `printf(..., join(...))` 直接把它用完就丟，沒有任何變數保存指標，這是 memory leak。如果這行在每個請求都會執行，就會造成 RSS 持續上升。修法是用變數接住回傳值、用完 `free`，並把函式改名成 `join_new` 之類的名稱，讓「呼叫者要釋放」這件事寫在介面上；或者改用 `snprintf` 寫進呼叫者提供的緩衝區。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 9.10 節（garbage collection）與 9.11 節（常見記憶體錯誤）。
- [AddressSanitizer（Clang 文件）](https://clang.llvm.org/docs/AddressSanitizer.html)：旗標、`ASAN_OPTIONS`、支援平台與已知限制。
- [UndefinedBehaviorSanitizer（Clang 文件）](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)：可檢查的 UB 種類與 `-fsanitize=` 的子選項。
- [Stanford CS107：Pointer pitfalls](https://web.stanford.edu/class/archive/cs/cs107/cs107.1234/resources/pointer_pitfalls.html)：常見指標錯誤的整理，適合搭配 26.3 節複習。
- [Linux man pages](https://man7.org/linux/man-pages/)：`malloc(3)`、`proc(5)` 中 `smaps` 與 `smaps_rollup` 的說明。
