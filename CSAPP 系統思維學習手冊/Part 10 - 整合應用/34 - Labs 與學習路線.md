---
chapter: 34
title: CS:APP Labs 實作指南與學習路線
part: 10
---

# 第 34 章　CS:APP Labs 實作指南與學習路線

> [!abstract] 本章地圖
> **核心問題**：CS:APP 的九個 Labs 各自在訓練什麼能力？要怎麼做，才能確定自己是「真的懂」，而不只是「分數過了」？
>
> **你會學到**：
> - 說出九個 Labs（Data、Bomb、Attack、Architecture、Cache、Performance、Shell、Malloc、Proxy）各自練習的能力、需要的先備章節與最常見的卡關點
> - 用「建模 → 打造驗證工具 → 對抗測試」的流程做任何一個 Lab，並寫出有用的 lab notebook
> - 自己寫窮舉 oracle 與切塊測試這類驗證工具，用證據判斷程式是否正確
> - 依自己的時間與目標排出學習順序與時程
> - 把 Labs 練出來的能力對應到後端、SRE、嵌入式、安全與效能工程的日常工作
>
> **前置知識**：本章是全書的收尾，會引用第 2–32 章；不必全部讀完才開始，34.13 節會說明每個 Lab 最少要先讀哪幾章。
>
> **對應 CS:APP 3e**：全書，以及官方網站的 Lab Assignments 頁面

本章**不提供任何 Lab 的解答、關卡答案、payload 或可直接套用的程式碼**。理由很實際：Lab 的價值全在「自己卡住、自己找到證據、自己解開」的過程，拿到答案就等於把這個過程丟掉。本章給的是地圖、方法與自我檢驗的標準。

## 34.1 故事：照抄來的炸彈

小安入職滿一年那天，團隊來了一位新同事小葉，剛從資工系畢業，也是第一次寫 C。老周把小葉的 onboarding 交給小安：「你帶小葉，用 CS:APP 的 Labs 當練習題，排一個三個月的計畫。」

小安有點心虛。大學的計算機組織課也做過 Bomb Lab，當時全班在流傳一份答案，小安照著輸入，六關一次全過，拿了滿分。可是半年前 `thumbd` 在 production 發生 segfault，老周丟給小安一個 core dump，小安在 `gdb` 裡打 `bt` 看到一串沒有符號的位址，再用 `disassemble` 看到一堆 `mov`、`cmp`、`jle`，完全不知道從哪裡讀起。那一刻小安才發現：當年那顆「拆掉」的炸彈，其實一個字都沒讀懂。

老周聽完笑了：「Bomb Lab 練的不是答案，是在沒有原始碼的情況下，從組合語言還原程式的意圖。這正是你那天在 core dump 前需要的能力。分數只是副產品。」

那天下午兩個人一起把九個 Labs 攤開來，一個一個討論：它在練什麼、要先讀哪幾章、大家都卡在哪裡、做完以後要怎麼證明自己真的懂。這一章就是那份討論的整理。

## 34.2 Labs 是什麼，從哪裡取得

CS:APP 的作者在官方網站提供一系列 **Lab**（實作作業），原本是給大學課程使用的。每個 Lab 都是一個小而完整的系統問題：一份 writeup（題目說明）、一組起始程式（handout）、一套自動評分工具。

對自學者最重要的是：每個 Lab 都有 **self-study handout**（自學版材料），任何人都可以從官方的 Lab Assignments 頁面下載。自學版與課堂版的差別主要在評分：例如 Bomb Lab 的課堂版每次「爆炸」都會通知課程的評分伺服器，通常會因此扣分（扣多少由開課的老師決定），自學版關掉了這個通知；Attack Lab 的自學版要加 `-q` 參數執行，讓它不去連線評分伺服器。

| Lab | 一句話描述 | 主要對應章節 | 手上會拿到什麼 |
|---|---|---|---|
| Data Lab | 只用極少數的位元運算子，實作整數與浮點數的函式 | 第 3–6 章 | 一個要填寫的 C 檔，以及檢查規則與正確性的工具 |
| Bomb Lab | 沒有原始碼的執行檔要你輸入六個字串，答錯就「爆炸」 | 第 7–10 章 | 一個 x86-64 執行檔與它 `main` 的一小段 C |
| Attack Lab | 對兩個有 buffer overflow 的程式做 code injection 與 ROP 攻擊 | 第 9、11 章 | 兩個執行檔、一個把十六進位轉成位元組的工具 |
| Architecture Lab | 寫 Y86-64 程式、為處理器加新指令、最佳化 pipeline 版本的 CPE | 第 12–14 章 | Y86-64 組譯器、模擬器與 HCL 原始碼 |
| Cache Lab | 寫一個 cache 模擬器，再最佳化矩陣轉置以減少 miss | 第 15–17 章 | trace 檔、參考模擬器、測試程式 |
| Performance Lab | 最佳化一個應用程式 kernel 函式（官網舉的例子是 convolution 或矩陣轉置）的效能 | 第 14、17 章 | kernel 原始碼與量測 CPE 的 driver |
| Shell Lab | 寫一個支援 job control 的 Unix shell | 第 20–22 章 | 骨架程式、16 個 trace、參考 shell |
| Malloc Lab | 寫自己的 `malloc`、`free`、`realloc` | 第 10、24–26 章 | 要填寫的 `mm.c`、模擬 heap 的 `memlib.c`、driver |
| Proxy Lab | 寫一個支援並行與快取的 HTTP proxy | 第 27–32 章 | 骨架程式、一個小 web server、評分 script |

表中的「Performance Lab」比較特別：官方網站註明卡內基美隆大學（CMU）現在用 Cache Lab 取代它，但材料仍可下載。Attack Lab 則是舊版 32-bit Buffer Lab 的 64-bit 後繼版本，自學請直接做 Attack Lab。

### 執行環境

大部分 Lab 預設在 **Linux x86-64** 上執行：Bomb Lab 與 Attack Lab 的執行檔是 x86-64 Linux 機器碼，Cache Lab 要用 Valgrind 在 x86-64 上產生位址 trace。在 Apple Silicon 的 Mac 上無法直接執行，常見的作法有三種：

| 作法 | 優點 | 要注意的地方 |
|---|---|---|
| 雲端的 x86-64 Linux 虛擬機 | 和原始環境最接近，`gdb`、Valgrind 都正常 | 需要網路與一點費用；記得用完關機 |
| 舊的 x86-64 筆電灌 Linux | 免費、完全本機 | 硬體可能較慢，但 Lab 的運算量都很小 |
| Mac 上用模擬 x86-64 的容器或虛擬機 | 不必另外準備機器 | 指令轉譯會影響 `gdb` 的單步與效能量測，效能類 Lab 的數字不可信；遇到怪問題先懷疑環境 |

Data Lab、Shell Lab、Malloc Lab、Proxy Lab 的程式碼本身大多是可攜的 C，但 handout 的 Makefile 可能使用 `-m32` 之類的選項或特定的系統工具，依版本與發行版而定；遇到編譯問題先讀 README 與 Makefile，而不是急著改程式。

### 學術誠信與公開解答

網路上有大量 Lab 的公開解答。如果你正在修一門使用這些 Lab 的課，抄襲違反課程規定；即使是自學，看答案也會讓你失去唯一的收穫。也請不要把自己的解答放到公開的 GitHub repo：這些 Lab 至今仍在許多學校使用，公開解答會傷害後面的學生。可以公開的是你的方法、你寫的驗證工具（只要不含解答）、以及你的 lab notebook 裡「學到什麼」的部分。

## 34.3 做任何一個 Lab 的共同方法

九個 Lab 主題不同，但卡關的原因驚人地相似：沒有先建立正確的模型，就開始改程式；沒有驗證工具，只靠評分 script 的一個分數判斷對錯；只測了「正常」的輸入。所以在進入個別 Lab 之前，先建立一套共同的工作方法。

```text
 ┌────────────────────────────────────────────────────────────┐
 │ 第 1 輪：建模                                                │
 │   寫下：輸入是什麼？狀態存在哪裡？每一步之後什麼必須成立？  │
 │   先讓最簡單、最慢、但顯然正確的版本跑起來                  │
 └───────────────────────────┬────────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────────┐
 │ 第 2 輪：打造驗證工具                                        │
 │   參考實作（oracle）、窮舉小範圍、checker、trace、計數器    │
 │   讓錯誤在「第一次發生」時就被抓到，而不是很久以後才當機    │
 └───────────────────────────┬────────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────────┐
 │ 第 3 輪：對抗測試與最佳化                                    │
 │   邊界值、隨機順序、壞時機（signal、慢連線）、資源壓力      │
 │   最佳化之後重跑全部驗證，只保留有量測證據的改善            │
 └───────────────────────────┬────────────────────────────────┘
                             ▼
         正確性與效能都有證據支持 → 才算完成
```

這張圖的重點在第 2 輪。很多人做 Malloc Lab 時，第一個版本跑 driver 就 segfault，於是開始在各處加 `printf`、反覆修改，三天後仍然不知道問題在哪。原因是 allocator 的錯誤通常在很早的某一次 `free` 就破壞了 heap 的結構，卻要到很多次操作之後才當機。如果有一個在每次操作後檢查 heap 是否一致的 **checker**（檢查器：一段專門驗證資料結構「不變量」的程式），錯誤會在發生的那一刻被抓到。這裡的 **invariant**（不變量）是指「無論執行到哪一步都必須成立的條件」，例如「heap 中相鄰的兩個區塊不會同時是空閒的」。

### Lab notebook

第二個共同工具是 **lab notebook**（實驗筆記）：每次做實驗時記錄的固定格式筆記。它的用意是讓你區分「我改了什麼」和「我知道了什麼」，後者才是學習。

```text
日期／Lab／目前分數或狀態
  假說：我認為目前的現象是 ___ 造成的；如果對，應該會看到 ___
  實驗：固定 ___，只改變 ___；指令是 ___
  原始證據：（貼上實際輸出，不要只寫「失敗了」）
  解讀：證據支持／推翻了假說；還有哪些其他解釋？
  下一步：下一個最小的實驗是什麼？
```

這和工作上寫 incident 調查紀錄的格式幾乎一樣（第 33 章）。習慣用這種格式做 Lab，等於提早練習 production 除錯。

### 四層驗證

| 層次 | 問的問題 | 例子 |
|---|---|---|
| 功能 | 正常輸入的輸出對嗎？ | proxy 能抓到一個普通的網頁 |
| 邊界 | 0、1、最大值、空輸入、重複輸入呢？ | `malloc(0)`、`realloc(NULL, n)`、最大的整數 |
| 不變量 | 每一步之後，內部結構都合法嗎？ | free list 的前後指標互相一致；cache 的每個 set 不超過 E 行 |
| 對抗 | 壞時機、壞順序、資源不足時呢？ | signal 在任意兩行之間到達；連線一次只送 1 byte |

評分 script 通常只覆蓋前兩層。真正的理解在後兩層：你能不能自己想出會讓程式失敗的輸入？

## 34.4 Data Lab：位元層級的整數與浮點數

### 練什麼

Data Lab 要你實作一系列小函式，例如判斷兩個數的大小關係、算出表示一個數需要的位元數、對浮點數的位元表示做運算。限制非常嚴格：整數題只能用少數的位元運算子（例如 `!`、`~`、`&`、`^`、`|`、`+`、`<<`、`>>`），不能用 `if`、迴圈、比較運算子，常數不能大於 `0xFF`，而且每題有運算子數量上限。浮點數題則是拿到一個 `unsigned` 形式的位元表示，要你在位元層級完成浮點運算；這類題目可以用 `if` 與迴圈，但不能直接使用 `float` 型別與浮點運算。

這些限制的目的，是逼你放棄「用高階語意思考」，改成「用位元與二補數的性質思考」。在 Python 裡寫 `x < y` 是理所當然的事；在 Data Lab 裡你必須回答：比較大小在位元層級上到底是什麼？減法什麼時候會溢位？符號位元在溢位時告訴你什麼？

### 先備知識

第 3 章（位元運算、shift、遮罩）、第 4 章（二補數、TMin 與 TMax、sign extension）、第 5 章（溢位的條件）、第 6 章（IEEE 754 的 sign、exponent、fraction，以及 normalized、denormalized、∞、NaN）。浮點題特別依賴第 6 章的「三種情況」分類：exponent 全 0、全 1、其他。

### 常見卡關

1. **用到違規的運算子或常數。** handout 附的檢查工具（`dlc`）會檢查是否違反規則；寫完一題就跑一次，不要累積到最後。
2. **測試通過，但其實不對。** 測試程式只測了一部分輸入，邊界值（TMin、0、−1、NaN、最小的 denormalized 數）最容易漏掉。有些版本的教師材料另外附有以 BDD（binary decision diagram）為基礎的形式化檢查工具，能對所有可能的輸入做驗證；自學版不一定包含它，所以要自己補邊界測試。
3. **把 undefined behavior 當成定義好的行為。** 一般 C 程式中 signed overflow 是 UB（第 5 章）；Data Lab 的 writeup 會明確寫出它假設的機器行為（例如右移是算術右移），解題時只依賴這些明文假設。
4. **浮點題漏了特殊值的分支。** 每個浮點題都要先問：輸入是 NaN 嗎？是 ∞ 嗎？是 denormalized 嗎？結果會不會溢位成 ∞ 或下溢成 0？

### 怎麼驗證自己真的懂

- 對每一題，能用一句話說出「這個式子成立的不變量」，而不是背下式子。例如能解釋「為什麼 `~x + 1` 等於 `-x`」（第 4 章）。
- 能在 4-bit 或 8-bit 的世界裡手算你的式子，並對全部輸入窮舉驗證。34.12 節的第一個程式就是這種窮舉 oracle。
- 給你一題沒做過的位元題（例如「不用分支算絕對值」），能在合理時間內推導出來，並說出它在哪個輸入上最容易錯。

## 34.5 Bomb Lab：從組合語言還原程式的意圖

### 練什麼

Bomb Lab 給你一個執行檔，裡面有六個關卡（phase）。每一關讀入一行字串，答對就進下一關，答錯就「爆炸」。你只有 `main` 的一小段 C 原始碼，其餘只能靠反組譯與除錯器。課堂版的每個學生拿到的炸彈都不同，所以別人的答案原則上不適用；自學版則是官方網站上同一顆公開的炸彈，網路上的答案確實能直接套用，這也是為什麼自學者更需要自我約束。

它真正練的是**逆向工程**（reverse engineering：在沒有原始碼的情況下，從機器碼理解程式的行為）的基本功：讀 x86-64 組合語言、辨認編譯器產生的常見結構（比較與分支、迴圈、switch 的 jump table、遞迴、陣列與鏈結串列的走訪），並用 `gdb` 在執行時觀察暫存器與記憶體。

### 練習讀組合語言：用自己的程式

拆炸彈之前，先拿自己寫的小函式練習「看組合語言、還原 C」。以下是 `thumbd` 裡檢查縮圖參數的函式，我們假裝不知道原始碼，只看組合語言：

```c
/* thumbd：檢查縮圖參數是否合法 */
int check_dims(int w, int h, int max_side) {
    if (w <= 0 || h <= 0)
        return -1;
    if (w > max_side || h > max_side)
        return -2;
    return w * h > 4000000 ? -3 : 0;
}
```

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - dims.c` 產生（Apple clang 21，`-O1`，刪去部分 directive）：

```asm
check_dims:
	testl	%edi, %edi
	setle	%al
	testl	%esi, %esi
	setle	%cl
	orb	%al, %cl
	movl	$-1, %eax
	jne	.LBB0_3
	cmpl	%edx, %edi
	setg	%al
	cmpl	%edx, %esi
	setg	%cl
	orb	%al, %cl
	movl	$-2, %eax
	jne	.LBB0_3
	imull	%edi, %esi
	xorl	%eax, %eax
	cmpl	$4000001, %esi
	setl	%al
	leal	(%rax,%rax,2), %eax
	addl	$-3, %eax
.LBB0_3:
	retq
```

逆向的步驟和拆炸彈完全一樣：

1. **先認參數。** 依 System V ABI（第 9 章），前三個整數參數在 `%edi`、`%esi`、`%edx`，回傳值在 `%eax`。所以 `%edi` 是第一個參數、`%esi` 是第二個、`%edx` 是第三個。
2. **切出基本區塊。** 有兩個 `jne .LBB0_3`，目標都是 `retq`，代表兩個「提早返回」的出口；在跳躍之前，`%eax` 已經先放好 −1 或 −2。這是編譯器常見的手法：先把回傳值放好，再決定要不要跳走。
3. **還原條件。** `testl %edi,%edi` 加 `setle %al` 表示「`%al` = 第一個參數 ≤ 0」；第二個參數同理；`orb` 把兩者 OR 起來。所以第一個出口的條件是「任一個參數 ≤ 0」。編譯器沒有用兩次條件跳躍，而是用 `setle` 加 `orb` 合成一次跳躍（第 8 章）。
4. **讀懂最後的算術技巧。** `setl %al` 讓 `%al` 在「乘積 < 4000001」時為 1，否則為 0；`leal (%rax,%rax,2)` 算出 3 × `%eax`，再加 −3。所以結果是 1 → 0、0 → −3。這是用算術代替分支的 branchless 寫法。注意比較的常數是 4000001 而不是 4000000：`> 4000000` 被改寫成「`< 4000001` 的相反」。

這四步就是 Bomb Lab 每一關的節奏：認參數與回傳值、切區塊、還原條件、辨認編譯器的技巧。差別只在炸彈的函式更長，而且會呼叫其他函式。

### 先備知識

第 2 章（`gdb` 的 `break`、`stepi`、`x`、`info registers`）、第 7 章（暫存器、addressing mode、AT&T 語法）、第 8 章（條件碼、跳躍、迴圈與 switch 的翻譯）、第 9 章（stack frame 與參數傳遞）、第 10 章（陣列、struct 與指標在記憶體裡的樣子）。

### 常見卡關

1. **逐行翻譯，見樹不見林。** 一行一行翻成 C，翻完仍不知道這一關要什麼。應該先找出函式的整體結構：哪裡是迴圈？哪裡會呼叫引爆的函式？每個分支通往哪裡？先畫控制流程圖（control flow graph），再看細節。
2. **AT&T 語法的運算元順序。** `cmpl %edx, %edi` 比較的是 `%edi − %edx`，接下來的 `setg` 代表 `%edi > %edx`。順序搞反，整個條件就反了（第 7、8 章）。
3. **不會看記憶體裡的資料。** 函式常常拿一個位址當參數，位址上是字串、陣列或 struct。要學會用 `gdb` 的 `x` 指令以不同格式（字串、十進位、十六進位、位址）查看記憶體。
4. **害怕爆炸而不敢實驗。** 自學版爆炸沒有任何懲罰。更好的作法是先學會讓程式在危險的地方停下來（設中斷點），把每次執行都變成安全的實驗。

### 怎麼驗證自己真的懂

- 每一關都能寫出一段等價的 C 程式（不是答案，而是「這一關在檢查什麼」），並用它解釋為什麼你的輸入會被接受。
- 如果某一關的合法答案不只一個，能說出全部答案的集合是什麼，並實際試另一個答案。
- 拿一個沒看過的執行檔（例如自己用 `-O2` 編譯、刪掉符號的小程式），能在 `gdb` 中找到 `main`、還原它的邏輯。這才是 34.1 節小安在 core dump 前需要的能力。

## 34.6 Attack Lab：親手體會 buffer overflow 與防禦

### 練什麼

Attack Lab 給你兩個有 buffer overflow 漏洞的程式。第一個沒有開啟 stack 不可執行與位址隨機化，讓你練習 **code injection**（把機器碼放進輸入，再讓程式跳過去執行）；第二個開啟了這些防禦，你只能用 **ROP**（return-oriented programming：串接程式裡已經存在、以 `ret` 結尾的指令片段）達成目標。輸入是一串位元組，handout 附了把十六進位文字轉成原始位元組的工具。

這個 Lab 的意義不在於「學會攻擊」，而在於把第 9 章的 stack frame 與第 11 章的防禦機制變成親身經驗：return address 確實就在那裡，覆寫它確實就能改變控制流程；NX、ASLR、stack canary 各自擋下哪一種攻擊，又留下了哪些縫隙。

```text
 一般的 stack frame 與 overflow 的方向（概念圖，與 Lab 的實際配置無關）

 高位址
 ┌──────────────────────┐
 │ caller 的 frame      │
 ├──────────────────────┤
 │ return address       │ ← 被覆寫時，ret 會跳到攻擊者指定的地方
 ├──────────────────────┤
 │ （可能有 canary）     │ ← 開啟 stack protector 時，覆寫會先破壞它
 ├──────────────────────┤
 │ 區域陣列 buf[]       │ ↑ 寫入方向：從 buf 的低位址往高位址
 └──────────────────────┘ ← %rsp
 低位址
```

這張圖說明了 overflow 的本質：陣列由低位址往高位址寫，而 return address 位在陣列的「上方」，所以寫超過陣列長度就會覆蓋到它。Lab 裡你要自己用反組譯算出陣列離 return address 有多遠，這個數字因程式而異。

### 先備知識

第 3 章（little endian：多位元組的值在記憶體裡低位元組在前）、第 9 章（call／ret、stack frame）、第 11 章（stack smashing、NX、ASLR、canary、ROP 的概念），以及 Bomb Lab 練出的 `gdb` 與反組譯能力。強烈建議先完成 Bomb Lab。

### 常見卡關

1. **位元組順序。** 位址在輸入中要以 little endian 排列（第 3 章），寫反是最常見的錯誤。
2. **輸入被截斷。** 讀取輸入的函式遇到換行字元（`0x0a`）就停止，payload 中間如果出現這個位元組，後面全部會被丟掉。writeup 中有說明這類限制。
3. **跳過去之後當機。** 控制流程確實被改變了，但目標函式內部當機。常見原因是 stack 不符合 16-byte 對齊（第 9 章），或你的程式碼破壞了目標函式依賴的暫存器。
4. **忘記加 `-q`。** 自學版要用這個參數執行，否則程式會嘗試連線不存在的評分伺服器。

### 怎麼驗證自己真的懂

- 每一關都能畫出攻擊前後的 stack 圖，標出每一個位元組的用途，並解釋 `ret` 執行那一刻 `%rsp` 指向哪裡。
- 能說明：如果這個程式開啟了 stack canary，你的哪一關會失敗？如果開啟 ASLR，code injection 為什麼變困難，ROP 又為什麼仍然可行？
- 能回到 C 原始碼層級，指出漏洞的根源（例如沒有長度限制的讀取），並寫出安全的版本（第 11 章的 `fgets`、`snprintf`、長度檢查）。這是安全工程師與一般開發者都需要的能力。

## 34.7 Architecture Lab：在模擬器裡改造處理器

### 練什麼

Architecture Lab 使用第 12、13 章的 Y86-64 指令集與模擬器，分成三部分：先用 Y86-64 組合語言寫幾個小程式（例如走訪鏈結串列）；再修改循序處理器 SEQ 的 HCL 描述，加入一個新指令；最後同時修改一個陣列複製函式與 pipeline 處理器的設計，降低 **CPE**（cycles per element：每處理一個元素平均花幾個時脈週期，第 14 章）。

這是九個 Lab 中唯一碰觸硬體設計的。你會親手體會「一條新指令要動到 datapath 的哪些階段」，以及 pipeline 中 data hazard、load-use hazard、分支預測錯誤各自造成多少 bubble。

### 先備知識

第 12 章（Y86-64 指令集、HCL、SEQ 的六個階段）、第 13 章（pipeline、forwarding、hazard、分支預測）、第 14 章（CPE、loop unrolling）。

### 常見卡關

1. **模擬器編不起來。** handout 的模擬器有圖形介面（GUI）版本，需要 Tcl/Tk 的開發套件；如果環境沒有，可以依 README 的說明只建置文字（TTY）版。
2. **加了新指令，卻漏改某個階段。** 新指令在 fetch、decode、execute、memory、write back、PC update 六個階段各要做什麼，要先在紙上填一張表，再對照 HCL 逐一修改。
3. **為了 CPE 犧牲正確性。** 最佳化後的函式必須在各種陣列長度（包含 0 與 1）都正確。handout 附有正確性與效能的檢查 script，writeup 也限制了組譯後的程式長度（3e 版的上限是 1000 bytes，附有檢查長度的 script）；每次修改都要把這些檢查一起跑。
4. **只改程式、不看 pipeline。** 有些 bubble 來自 load-use hazard，調整指令順序就能消除；有些來自分支預測錯誤，要改控制流程。不先找出 bubble 的來源，只能亂試。

### 怎麼驗證自己真的懂

- 對一段五、六條指令的 Y86-64 程式，能手畫 pipeline 時序圖，標出每一個 stall 與 bubble 的原因，再用模擬器驗證。
- 在修改之前預測「這樣改 CPE 會降多少」，修改後比對預測與實測，解釋差距。
- 能解釋 Y86-64 的 pipeline 和現代 out-of-order 處理器（第 13 章）的差別：哪些技巧在真實 CPU 上仍然有效，哪些已經由硬體自動處理。

## 34.8 Cache Lab 與 Performance Lab：讓程式配合記憶體階層

### Cache Lab 練什麼

Cache Lab 分兩部分。Part A 要你寫一個 cache 模擬器：讀入 Valgrind 產生的記憶體存取 trace，依照命令列給定的 set 數、每個 set 的行數、block 大小，模擬 LRU 替換，算出 hit、miss、eviction 次數，並和參考模擬器比對。Part B 要你為一個小型的 direct-mapped cache 最佳化矩陣轉置，在幾種不同大小的矩陣上把 miss 數壓到門檻以下，並且限制可用的區域變數數量。

Part A 把第 16 章的「位址切成 tag、set index、block offset」從手算變成程式；Part B 把第 17 章的 blocking 變成實戰，你會發現同樣是 blocking，不同的矩陣大小需要不同的策略，因為 conflict miss 的位置不同。

### Performance Lab 練什麼

依官方 labs 頁的描述，Performance Lab 要你最佳化一個應用程式的 kernel 函式，例如 convolution 或矩陣轉置（實際題目以你拿到的 writeup 為準）。這類 kernel 都是對二維資料做大量重複存取的迴圈，和 `thumbd` 縮圖的內層迴圈是同一類問題（第 14、17 章的 `thumbd` 範例）：一邊要減少每個元素的指令數（第 14 章），一邊要讓存取順序配合 cache（第 17 章）。driver 會在不同大小的輸入上量測 CPE，跟基準版本比較。

### 先備知識

第 15 章（locality、記憶體階層）、第 16 章（cache 組織、三種 miss）、第 17 章（迴圈順序、blocking）、第 14 章（量測、loop unrolling、減少函式呼叫）。Cache Lab Part A 也需要第 2 章的 C 基本功：`getopt` 處理命令列、`fscanf` 讀檔、`malloc` 配置二維結構。

### 常見卡關

1. **trace 格式的細節。** trace 中有四種存取：指令讀取、資料讀取、資料寫入，以及「讀後寫」的資料修改，各自對 cache 的影響不同。哪一種要忽略、哪一種要算兩次存取，writeup 都寫得很清楚，請逐字讀。
2. **LRU 的記錄方式錯了，但總數碰巧對。** 只比對最後的 hit／miss 總數，可能掩蓋 eviction 選錯的 bug。用小 trace 印出每一步之後每個 set 的狀態，和手算比對。
3. **Part B 只在一種矩陣大小上成功。** 把同一套 blocking 套到另一種大小，miss 反而可能變多。原因通常是對角線上的元素或兩個矩陣的對應位置映射到同一個 set（第 16 章的 conflict miss）。先手算「A 的第 i 列和 B 的第 j 列落在哪個 set」，再設計。
4. **效能量測不穩定。** Performance Lab 的數字會受機器負載、CPU 頻率調整影響。重複量測、看中位數，並且固定環境（第 14 章）。在模擬 x86-64 的環境中量到的數字沒有參考價值。

### 怎麼驗證自己真的懂

- 給一段小 trace 與 cache 參數，能完全手算每一次存取的結果，並和你的模擬器逐步輸出比對。
- 在動手最佳化轉置之前，能先預估 baseline 的 miss 數大約是多少，並解釋來源（哪些是 cold miss、哪些是 conflict miss）。
- 能把學到的東西帶回真實機器：用 `perf stat -e cache-misses`（第 17 章）在 `thumbd` 的旋轉函式上驗證 blocking 是否真的有效。

## 34.9 Shell Lab：process、signal 與 race

### 練什麼

Shell Lab 要你完成一個叫 `tsh` 的小 shell：能執行前景與背景的程式、支援 `jobs`、`fg`、`bg` 等內建指令，並正確處理 Ctrl-C 與 Ctrl-Z。handout 提供骨架程式、16 個測試 trace、一個參考 shell，以及會把 trace 餵給 shell 的 driver。你的 shell 對每個 trace 的輸出要和參考 shell 一致。

這是許多人第一次真正面對**並行**（concurrency）：主程式和 signal handler 是兩條會交錯執行的控制流程，`SIGCHLD` 可能在任何兩行之間到達。第 22 章講的 race、`sigprocmask`、async-signal-safe，在這裡全部會變成你必須親手解決的 bug。

```text
 一個典型的 race（概念時間軸）

 主程式（shell）                      kernel / 子程序
 ───────────────                      ───────────────
 fork() ───────────────────────────▶ 子程序開始執行
                                       子程序很快就結束
                                       kernel 送出 SIGCHLD
 ◀──────────── SIGCHLD handler 執行：在 job 表裡找這個子程序 → 找不到
 把子程序加入 job 表                   （handler 已經跑完了）
 → job 表裡留下一個永遠不會被移除的 job
```

這張時間軸說明了為什麼「通常會成功」的程式並不正確：只要子行程結束得夠快，handler 就會在主程式更新 job 表之前執行。第 22 章介紹了用 signal mask 關閉這個時間窗口的原則；Lab 裡你要自己判斷在哪些地方需要這麼做。

### 先備知識

第 20 章（process、system call 的錯誤處理）、第 21 章（`fork`、`execve`、`waitpid` 的選項、zombie）、第 22 章（signal 的 pending／blocked、handler 的守則、`sigprocmask`、`sigsuspend`）。

### 常見卡關

1. **按 Ctrl-C 把 shell 自己也殺掉了。** 終端機把 signal 送給整個前景 **process group**（行程群組：一組可以一起接收 signal 的 process）。先搞清楚 shell 與它的子行程各自屬於哪個 group，以及這對 signal 的傳遞有什麼影響。
2. **用 `sleep` 讓測試通過。** 加了 `sleep` 之後 race 變得不容易發生，但沒有消失；換一台機器或負載變高就會再出現。正確作法是用 signal mask 與 `sigsuspend` 建立確定的先後順序（第 22 章）。
3. **handler 一次只回收一個子行程。** signal 不排隊（第 22 章）：多個子行程幾乎同時結束時，handler 可能只被呼叫一次，所以 handler 必須回收「所有」已結束的子行程。
4. **在 handler 裡呼叫不安全的函式。** `printf` 不是 async-signal-safe。Lab 的骨架可能為了方便讓你在 handler 中輸出，但你要知道這在真實程式中為什麼危險。

### 怎麼驗證自己真的懂

- 16 個 trace 的輸出都和參考 shell 一致（process ID 不同是正常的）。
- 對程式中每一個存取 job 表的地方，能說出「此時哪些 signal 被阻擋、為什麼」。
- 能寫一個壓力測試：連續啟動數百個很快結束的背景程式，確認 job 表最後是空的、沒有 zombie（`ps` 中狀態為 `Z` 的程序）殘留。這和第 21 章 `thumbd` 的 zombie 累積問題是同一件事。

## 34.10 Malloc Lab：自己管理 heap

### 練什麼

Malloc Lab 要你實作 `mm_init`、`mm_malloc`、`mm_free`、`mm_realloc`。handout 提供一個模擬的 heap（用類似 `sbrk` 的函式向它要記憶體）以及一個 driver：driver 讀入 trace 檔（一連串的配置與釋放請求），檢查你的實作是否正確，並同時評估 **utilization**（空間利用率：heap 的峰值大小中，有多少是真正在使用的 payload）與 **throughput**（每秒能完成多少次操作），兩者合成一個分數。

官方網站形容這個 Lab：做完之後，學生就真的懂指標了。原因是你必須把同一塊記憶體一下當成 header、一下當成 payload、一下當成 free list 的指標，全靠指標運算與型別轉換完成，任何一個位元組算錯，錯誤都會在很遠的地方才爆發。

### 先備知識

第 10 章（alignment、指標運算、型別轉換）、第 24 章（heap、`brk`／`sbrk`、`mmap`）、第 25 章（implicit／explicit／segregated free list、placement、splitting、coalescing、boundary tag）、第 26 章（記憶體錯誤的類型與除錯工具）。

### 常見卡關

1. **指標運算的單位。** 對 `char *` 加 1 前進 1 byte，對 `size_t *` 加 1 前進 8 bytes（第 10 章）。用巨集包裝存取時，括號與型別少一個就是錯的位址。
2. **對齊。** 回傳的指標必須符合 handout 規定的對齊（依版本為 8 或 16 bytes），header 與 footer 的配置要讓 payload 落在對齊的位址上。
3. **錯誤在很遠的地方爆發。** coalesce 少更新一個 footer，十萬次操作之後才 segfault。這正是 34.3 節說的：先寫 heap checker，在每次操作之後檢查不變量，再談分數。
4. **自學版 trace 不夠。** 自學版 handout 附的 trace 可能很少，只靠它們無法發現大多數 bug。要自己寫 trace：大量小區塊、交錯的大小、反覆 `realloc` 變大變小、釋放順序與配置順序相反等。
5. **過早追求 throughput。** 先求正確，再求 utilization，最後才追 throughput。沒有正確性為基礎，分數無法解釋。

### 怎麼驗證自己真的懂

- 你的 heap checker 能檢查哪些不變量？至少要包含：每個區塊對齊、header 與 footer 一致、沒有兩個相鄰的空閒區塊、free list 中的區塊都真的是空閒的，而且所有空閒區塊都在 free list 裡。
- 對每個 trace，能解釋你的 utilization 損失來自 internal 還是 external fragmentation（第 25 章），並畫出某一刻的 heap 圖。
- 能說明你的設計和 glibc 的 ptmalloc、jemalloc 這些真實 allocator（第 25 章）有什麼相同與不同，以及為什麼真實 allocator 要額外處理多執行緒。

## 34.11 Proxy Lab：把整本書串起來

### 練什麼

Proxy Lab 要你寫一個 HTTP proxy：瀏覽器把請求送給 proxy，proxy 解析請求、連到真正的伺服器、把回應轉回瀏覽器。它分三階段：先做循序的版本，再加上並行（同時服務多個連線），最後加上快取（把最近的回應存在記憶體中，有大小上限）。handout 附有一個小 web server 作為測試用的上游，以及會測試基本功能、並行與快取的評分 script。

官方網站說這個 Lab 把 byte order、caching、process control、signal、file I/O、並行與同步全部串在一起，這也是為什麼它通常是課程的最後一個 Lab。它和 `thumbd` 前面那層 nginx 做的事情是同一類：一個在兩端之間轉送 byte stream 的伺服器。

```text
 瀏覽器／curl ──HTTP──▶ ┌──────── proxy ────────┐ ──HTTP──▶ 上游伺服器
                        │ 1. 讀 request line 與 header（short read，第 27–28 章）
                        │ 2. 改寫 header、決定上游（HTTP，第 29 章）
                        │ 3. 查快取（readers-writers，第 31 章）
                        │ 4. 連線、轉送、逐塊讀回應（RIO，第 27 章）
                        │ 5. 存入快取、回傳（大小限制、替換策略）
                        └── 每個連線一個 thread 或 thread pool（第 30 章）
```

每一個步驟都對應前面的某一章，每一步也都有自己的陷阱。

### 先備知識

第 27 章（short count、RIO、不能用字串函式處理二進位資料）、第 28 章（socket、`getaddrinfo`、TCP 是 byte stream）、第 29 章（HTTP 格式、Tiny server）、第 30 章（thread-based server）、第 31 章（semaphore、readers-writers）、第 32 章（thread-safe 函式）。

### 常見卡關

1. **用字串函式處理回應內容。** 圖片是二進位資料，中間可能有 `\0`；用 `strcpy`、`strlen` 處理會截斷內容。header 可以當文字處理，body 必須依實際讀到的位元組數處理（第 27 章）。
2. **對方提早關閉連線，整個 proxy 跟著結束。** 寫入已被對方關閉的 socket 會收到 `SIGPIPE`，預設行為是結束 process。要決定怎麼處理這個 signal，以及 `write` 回傳 `EPIPE` 時怎麼辦（第 22、28 章）。
3. **只在本機測試正常就以為完成了。** localhost 上資料常常一次就全部到達，真實網路則會分成很多塊。34.12 節的第二個程式示範怎麼系統化地測試這件事。
4. **快取的 race。** 多個 thread 同時讀寫快取，替換時又要更新使用紀錄。先想清楚哪些操作是「讀」、哪些會改變共享狀態，再決定鎖的範圍（第 31 章）。
5. **使用 thread-unsafe 的函式。** 舊式的位址解析函式回傳指向靜態資料的指標，多個 thread 同時呼叫會互相覆蓋（第 32 章）。

### 怎麼驗證自己真的懂

- 除了評分 script，還能用 `curl` 指定 proxy、用 `nc`（netcat）手動一個字一個字輸入請求，確認 proxy 在資料分批到達時仍然正確。
- 能用 ThreadSanitizer（第 31 章）跑過並行測試而沒有 race 報告，並解釋每一把鎖保護的是哪個不變量。
- 能列出你的 proxy 在 production 上還缺什麼：timeout、連線數上限、header 大小上限、HTTPS、keep-alive。這些就是 nginx 這類伺服器多出來的工作（第 29 章）。

## 34.12 動手做：自己打造驗證工具

34.3 節說，Lab 的關鍵在第 2 輪：打造驗證工具。這一節用兩個和 Lab 無關、但方法完全相同的 `thumbd` 例子，示範兩種最常用的工具。它們不是任何 Lab 的解答，而是你在每個 Lab 都可以自己重做一次的「方法」。

### 程式一：窮舉 oracle（Data Lab、Cache Lab 的方法）

`thumbd` 調整亮度時需要「飽和加法」：兩個 0–255 的像素值相加，超過 255 就停在 255。為了速度，有人寫了不用分支的版本。怎麼確定它是對的？輸入只有 256 × 256 = 65,536 種組合，全部試一遍只需要幾毫秒。

**oracle**（神諭、參考答案）是一個慢但顯然正確的實作，拿來和要驗證的版本逐一比對。

```c
#include <stdint.h>
#include <stdio.h>

/* 參考實作：慢但顯然正確。 */
static uint8_t sat_add_ref(uint8_t a, uint8_t b) {
    unsigned s = (unsigned)a + b;
    return s > 255 ? 255 : (uint8_t)s;
}

/* 版本一：不用分支。sum 的第 8 位元（0x100）表示溢位。 */
static uint8_t sat_add_v1(uint8_t a, uint8_t b) {
    unsigned s = (unsigned)a + b;
    unsigned overflow = s >> 8;              /* 0 或 1 */
    return (uint8_t)(s | (0u - overflow));   /* 溢位時 OR 上全 1 */
}

/* 版本二：一個「看起來也對」的寫法，在 8-bit 內判斷溢位。 */
static uint8_t sat_add_v2(uint8_t a, uint8_t b) {
    uint8_t s = (uint8_t)(a + b);
    return s < a ? 255 : (s == 255 ? 254 : s);   /* 多手改了一個邊界 */
}

typedef uint8_t (*impl_t)(uint8_t, uint8_t);

/* 窮舉全部 65,536 組輸入，回報錯誤數與第一個反例。 */
static void check(const char *name, impl_t f) {
    long bad = 0;
    int fa = -1, fb = -1;
    for (int a = 0; a < 256; a++)
        for (int b = 0; b < 256; b++)
            if (f((uint8_t)a, (uint8_t)b) != sat_add_ref((uint8_t)a, (uint8_t)b)) {
                if (bad++ == 0) { fa = a; fb = b; }
            }
    if (bad == 0)
        printf("%-10s 65536 組全部正確\n", name);
    else
        printf("%-10s 錯 %ld 組，第一個反例 a=%d b=%d：得到 %d，應為 %d\n", name, bad,
               fa, fb, f((uint8_t)fa, (uint8_t)fb), sat_add_ref((uint8_t)fa, (uint8_t)fb));
}

int main(void) {
    /* 只測幾個「直覺上的」案例：兩個版本都會通過。 */
    int samples[][2] = {{10, 20}, {200, 100}, {255, 1}, {0, 0}};
    int ok1 = 1, ok2 = 1;
    for (int i = 0; i < 4; i++) {
        uint8_t a = (uint8_t)samples[i][0], b = (uint8_t)samples[i][1];
        ok1 &= sat_add_v1(a, b) == sat_add_ref(a, b);
        ok2 &= sat_add_v2(a, b) == sat_add_ref(a, b);
    }
    printf("抽樣 4 組：v1 %s，v2 %s\n", ok1 ? "通過" : "失敗", ok2 ? "通過" : "失敗");
    check("sat_add_v1", sat_add_v1);
    check("sat_add_v2", sat_add_v2);
    return 0;
}
```

在 macOS arm64（Apple clang 21，`cc -std=c17 -O1 -Wall -Wextra`）上執行；這段程式只用標準 C，在 Linux x86-64 上結果相同：

```text
抽樣 4 組：v1 通過，v2 通過
sat_add_v1 65536 組全部正確
sat_add_v2 錯 256 組，第一個反例 a=0 b=255：得到 254，應為 255
```

逐行解讀：

1. **抽樣測試兩個版本都通過。** 四組「看起來有代表性」的輸入（小數、會溢位、剛好溢位、零）都對，這正是 Data Lab 的測試通過、但其實有錯的情況。
2. **v1 窮舉全對。** 它的不變量是：`a + b` 最大是 510，最多 9 個位元，所以第 8 位元剛好表示是否溢位；`0u - overflow` 在溢位時是全 1（unsigned 的模運算，第 5 章），OR 上去就變成 255。能這樣說出理由，才算懂這個式子。
3. **v2 錯了 256 組。** 錯在所有「和剛好是 255」的輸入，也就是 a + b = 255 的 256 種組合（a 從 0 到 255，b 由 a 決定）。四組抽樣裡沒有一組的和是 255，所以抽樣永遠抓不到。
4. **第一個反例就是最好的除錯起點。** a=0、b=255 這種極端值，一看就知道邊界寫錯了。

這個方法的適用條件是「輸入空間夠小」。輸入是 32-bit 時，可以把同樣的式子縮小成 8-bit 版本來窮舉（位元運算的性質通常不依賴寬度），或改用隨機測試加上所有邊界值。Cache Lab 的模擬器也一樣：寫一個「顯然正確」的慢版本（例如每次都線性搜尋所有行），和你的版本在大量隨機 trace 上比對。

### 程式二：切塊測試（Proxy Lab、Shell Lab 的方法）

`thumbd` 要判斷 HTTP header 什麼時候收完：看到連續的 `\r\n\r\n` 就代表 header 結束。資料從 socket 讀進來時，每次 `read` 可能只拿到一部分（short count，第 27、28 章）。下面的程式把同一份請求用所有可能的方式切成 1 到 3 塊，餵給兩種 parser。

```python
"""把同一份 HTTP request 用各種方式切開餵給 parser，檢查結果是否一致。"""
import itertools

REQUEST = (b"GET /thumb/42?w=320 HTTP/1.0\r\n"
           b"Host: photos.example\r\n"
           b"\r\n")


class NaiveParser:
    """每收到一塊資料，就在『這一塊』裡找 header 結尾。"""
    def __init__(self):
        self.done = False

    def feed(self, chunk):
        if b"\r\n\r\n" in chunk:
            self.done = True


class BufferedParser:
    """把資料累積在 buffer 裡，在『全部已收到的資料』中找結尾。"""
    def __init__(self):
        self.buf = b""
        self.done = False

    def feed(self, chunk):
        self.buf += chunk
        if b"\r\n\r\n" in self.buf:
            self.done = True


def split_at(data, cuts):
    """依切點把 data 切成多塊，模擬 read() 的 short count。"""
    edges = [0, *cuts, len(data)]
    return [data[i:j] for i, j in zip(edges, edges[1:])]


def run(parser_cls, max_cuts=2):
    total = failed = 0
    first_bad = None
    positions = range(1, len(REQUEST))
    for k in range(max_cuts + 1):
        for cuts in itertools.combinations(positions, k):
            total += 1
            p = parser_cls()
            for chunk in split_at(REQUEST, cuts):
                p.feed(chunk)
            if not p.done:
                failed += 1
                first_bad = first_bad or cuts
    return total, failed, first_bad


for cls in (NaiveParser, BufferedParser):
    total, failed, bad = run(cls)
    print(f"{cls.__name__:15s} 測了 {total:5d} 種切法，失敗 {failed:4d} 種，第一個失敗切點 {bad}")
```

在 macOS arm64（Python 3）上執行的輸出：

```text
NaiveParser     測了  1432 種切法，失敗  156 種，第一個失敗切點 (51,)
BufferedParser  測了  1432 種切法，失敗    0 種，第一個失敗切點 None
```

逐步解讀：

1. **切法總數。** 請求長 54 bytes，有 53 個可以切的位置。不切 1 種、切一刀 53 種、切兩刀 C(53, 2) = 1,378 種，合計 1,432 種。手算和輸出一致，代表測試本身沒寫錯，這一步常被忽略。
2. **Naive 失敗了 156 種。** 結尾的 `\r\n\r\n` 佔 index 50–53 的 4 個 byte（從 0 起算），只要有一刀切在它中間（位置 51、52、53），這一塊就看不到完整的四個字元。至少一刀落在這三個位置的切法，有 3 種（只切一刀）加 1,378 − C(50, 2) = 153 種（切兩刀），正好 156 種。
3. **在 localhost 上幾乎不會發生。** 54 bytes 的請求在本機通常一次就讀完，所以 naive parser 在開發時看起來完全正常；到了真實網路、或客戶端一次只送一點，才偶爾失敗。這是「偶發錯誤」最典型的來源（第 33 章）。
4. **Buffered 全部通過，但還不夠好。** 它每次都在整個 buffer 裡重新搜尋，header 很大時是 O(n²)；而且 buffer 沒有大小上限，惡意客戶端可以一直送資料而不送結尾。這兩點都是 Proxy Lab 與真實伺服器要處理的（第 29 章的 header 大小限制）。

同樣的「把時機切碎」想法也適用於 Shell Lab：在主程式的關鍵步驟之間插入可控的延遲（只在測試版本中），故意讓 signal 在最壞的時機到達，看程式是否仍然正確。這是用測試主動「找出」race，而不是用 `sleep` 「藏起」race。

## 34.13 學習順序與時程

### Lab 之間的依賴

九個 Lab 不必照編號做，但有幾條清楚的依賴：Bomb Lab 練出的反組譯與 `gdb` 能力是 Attack Lab 的前提；Cache Lab 的模擬經驗讓 Performance Lab 的最佳化有方向；Shell Lab 的 signal 經驗與 Malloc Lab 的指標功力，都會在 Proxy Lab 用上。

```text
 Part 0–1（第 1–6 章）        Part 2（第 7–11 章）       Part 3–4（第 12–17 章）
 ┌─────────┐                  ┌─────────┐              ┌──────────────────┐
 │Data Lab │ ───────────────▶ │Bomb Lab │ ──┐          │Architecture Lab  │（選做）
 └─────────┘                  └────┬────┘   │          └──────────────────┘
                                   ▼        │          ┌──────────┐   ┌──────────────┐
                              ┌──────────┐  │          │Cache Lab │──▶│Performance   │（選做）
                              │Attack Lab│  │          └────┬─────┘   └──────────────┘
                              └──────────┘  │               │
 Part 6（第 20–22 章）        Part 7（第 23–26 章）         │
 ┌──────────┐                 ┌──────────┐                  │
 │Shell Lab │                 │Malloc Lab│◀─────────────────┘（指標、對齊、locality）
 └────┬─────┘                 └────┬─────┘
      │                            │
      └──────────┬─────────────────┘
                 ▼     Part 8–9（第 27–32 章）
           ┌──────────┐
           │Proxy Lab │  ← 全書整合
           └──────────┘
```

圖中標為選做的兩個 Lab：Architecture Lab 對想走硬體、編譯器或極致效能的人價值最高，對一般後端工程師的投資報酬率較低；Performance Lab 和 Cache Lab 的 Part B 重疊很多，時間有限時做其中一個即可。

### 建議時程

以下是給「一邊工作、每週投入約 8–10 小時」的自學者的建議時程，共約 20 週。每個 Lab 的實際所需時間因人差異很大，這裡只是預留時間的參考；如果某個 Lab 超出預留時間一倍以上，通常代表先備章節沒有讀透，回去補讀比硬撐有效。

| 週次 | 閱讀 | Lab | 這段時間的完成標準 |
|---|---|---|---|
| 1–2 | 第 1–2 章 | 準備 Linux x86-64 環境 | 能編譯、用 `gdb` 單步執行一個自己的程式 |
| 3–5 | 第 3–6 章 | Data Lab | 每題都能說出不變量；寫出 8-bit 窮舉 oracle |
| 6–8 | 第 7–10 章 | Bomb Lab | 每一關都有等價的 C 程式與控制流程圖 |
| 9–10 | 第 11 章 | Attack Lab | 每一關都有攻擊前後的 stack 圖 |
| 11–12 | 第 15–17 章（第 12–14 章可先略讀） | Cache Lab | 模擬器逐步輸出與手算一致；能預估 baseline miss |
| 13–14 | 第 20–22 章 | Shell Lab | 16 個 trace 全對；壓力測試沒有 zombie |
| 15–17 | 第 23–26 章 | Malloc Lab | heap checker 完成；能解釋每個 trace 的 fragmentation |
| 18–20 | 第 27–32 章 | Proxy Lab | 切塊測試與 TSan 都通過；列出缺少的 production 功能 |
| 之後 | 第 12–14、33 章 | Architecture Lab、Performance Lab（選做） | 能手畫 pipeline 時序圖；量測有統計依據 |

如果你是學生、有一整個學期，可以照課程的節奏，每 1–2 週一個 Lab。如果只有一個月、目標是準備系統類面試，優先順序是 Bomb、Malloc、Shell、Proxy：這四個最常在面試與工作中被問到，也最能練出「讀懂別人的程式、管理記憶體、處理並行」的能力。

### 卡住的時候

自學最大的風險是卡住太久而放棄。可以用一個簡單的規則：同一個問題卡超過兩小時，就停下來寫 lab notebook，把「我知道什麼、我不知道什麼、我試過什麼」寫清楚。寫清楚的過程常常就會找到答案；如果沒有，回到對應章節重讀相關小節，或去找講解「觀念」的資料（例如 CMU 15-213 課程網站的講義），而不是找「答案」。

## 34.14 在工作上怎麼用

做完 Labs 之後，最常見的疑問是：「我以後又不寫 shell、不寫 malloc，這些有什麼用？」答案是：你不會再寫一模一樣的程式，但你會不斷遇到同一類問題。下表把每個 Lab 練出的能力，對應到不同工作角色的具體情境。

| Lab | 後端工程 | SRE | 嵌入式 | 安全 | 效能工程 |
|---|---|---|---|---|---|
| Data | 解析二進位協定、處理整數溢位 | 讀懂 metrics 的位元欄位與溢位計數器 | 暫存器位元遮罩、定點數運算 | 整數溢位造成的漏洞（第 5 章） | 用位元運算替代分支 |
| Bomb | 讀第三方 library 的反組譯 | 讀 core dump 與沒有符號的 stack trace | 在沒有原始碼的韌體上除錯 | 逆向分析惡意程式與修補檔 | 讀 `perf annotate` 的組合語言熱點 |
| Attack | 寫出不會 overflow 的 C／C++ | 評估編譯選項（PIE、canary）是否開啟 | 在沒有 MMU 保護的系統上更小心 | 漏洞分析、exploit 緩解評估 | — |
| Architecture | — | — | 理解簡單 CPU 的 pipeline 行為 | 理解推測執行類漏洞（第 13 章） | 解讀 IPC、branch miss |
| Cache／Performance | 設計 cache-friendly 的資料結構 | 判斷延遲上升是否來自 cache 或 NUMA | 在小 cache 上安排資料 | — | blocking、SoA、量測方法 |
| Shell | 正確管理子行程與優雅關閉 | 理解 systemd、container 的 PID 1 與 signal | 監控行程與 watchdog | 行程權限與 signal 的安全邊界 | — |
| Malloc | 診斷記憶體成長、選擇 allocator | 區分 leak、碎片與 page cache | 在沒有 OS 的環境寫固定大小的 pool allocator | heap 漏洞（use-after-free、double free） | 降低配置次數、改善 locality |
| Proxy | 寫健壯的網路服務與 client | 理解 proxy、load balancer 的行為與 timeout | 寫裝置上的小型網路服務 | 解析不可信任的輸入 | 並行模型與鎖的競爭 |

### 情境一：後端工程師面對 core dump

`thumbd` 在 production 當機，留下 core dump。Bomb Lab 練過的流程直接適用：

```bash
gdb ./thumbd core.12345        # 載入執行檔與 core dump
(gdb) bt                       # 看當機時的 call stack（第 9 章）
(gdb) frame 2                  # 切到可疑的那一層
(gdb) info registers           # 看參數暫存器的值（%rdi、%rsi…）
(gdb) disassemble              # 看當機前後的指令（第 7–8 章）
(gdb) x/8gx $rsp               # 看 stack 上的內容
(gdb) info proc mappings       # 判斷可疑位址屬於哪個區域（第 23 章）
```

判斷流程：先看 fault 位址屬於哪個區域（NULL 附近、heap、已經 unmap 的區域）；再看當機的那一條指令是讀還是寫、用的是哪個暫存器；最後往上追，這個暫存器的值是從哪裡來的。沒有原始碼行號時，就像拆炸彈一樣，從組合語言還原意圖。

### 情境二：SRE 判斷「記憶體一直漲」

Malloc Lab 讓你知道 heap 會有碎片、allocator 不一定會把記憶體還給 OS。所以看到 RSS 持續上升時，不會直接斷定 leak，而是依序確認（第 24–26 章、第 33 章）：

```text
 RSS 持續上升
   ├─ 是 anonymous 還是 file-backed？（/proc/PID/smaps_rollup）
   │    └─ file-backed：多半是 mmap 的檔案或 page cache，不一定是問題
   ├─ 固定負載下，成長是否趨於平緩？
   │    ├─ 會平緩：可能是快取暖機或碎片，檢查快取上限與 allocator 統計
   │    └─ 線性成長：很可能是 leak → 在測試環境用 ASan／heap profiler 找配置點
   └─ 換 allocator（例如 jemalloc）後行為改變？→ 碎片的可能性高
```

### 情境三：嵌入式與安全

嵌入式工程師常常在沒有虛擬記憶體、沒有 `malloc` 的環境工作。Malloc Lab 的經驗讓你能寫出固定大小區塊的 pool allocator，並知道它為什麼沒有 external fragmentation。Data Lab 的位元功力則每天都會用到：設定硬體暫存器的某幾個位元，而不能動到其他位元。

安全工程師則會把 Attack Lab 的經驗用在評估上：拿到一個執行檔，第一件事是確認它的防禦是否開啟。

```bash
readelf -h thumbd | grep Type            # DYN 通常代表 PIE（位址可隨機化）
readelf -lW thumbd | grep GNU_STACK      # 旗標沒有 E 代表 stack 不可執行
readelf -sW thumbd | grep __stack_chk    # 有這個符號代表使用了 stack canary
```

這些指令是在 Linux 上檢查 ELF 檔（第 18 章）的方式，輸出格式依 binutils 版本略有不同。

### 情境四：效能工程

Cache Lab 與 Performance Lab 最重要的收穫不是某個最佳化技巧，而是**先量測、再假設、再驗證**的紀律。工作上的流程是：

1. 用 `perf stat` 確認瓶頸的種類：IPC 低嗎？cache miss 多嗎？branch miss 多嗎？
2. 用 `perf record` 與 `perf report` 找出熱點函式，用 `perf annotate` 看熱點的組合語言（Bomb Lab 的能力在這裡又出現了）。
3. 根據瓶頸種類選擇最佳化：cache miss 多就改資料布局或迴圈順序（第 17 章），依賴鏈長就用多個累加器（第 14 章）。
4. 改完之後重跑同一套量測，並確認正確性沒有被破壞（34.12 節的 oracle）。

### 面試

系統類的面試常常直接從 Labs 的主題出題：「實作一個 `malloc`」「寫一個 thread-safe 的 LRU cache」「解釋 fork 之後 signal handler 會怎樣」「這段組合語言在做什麼」。做過 Labs 的人有一個明顯優勢：能講出自己實際遇過的 bug 與除錯過程。面試官想聽的通常不是標準答案，而是「你怎麼知道它是對的」，這正是 34.3 節的四層驗證。

## 34.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 評分 script 全過，換一組輸入就錯 | 只做了功能測試，沒有邊界與對抗測試 | 寫 oracle 或窮舉小範圍，看第一個反例 | 補邊界測試；用不變量檢查取代「看起來對」 |
| Bomb／Attack Lab 的執行檔無法執行或行為怪異 | 不是 x86-64 Linux 環境，或模擬環境有差異 | `uname -m` 應為 `x86_64`；`file bomb` 看檔案格式 | 改用真正的 x86-64 Linux 機器或虛擬機 |
| Malloc Lab 在很後面的操作才 segfault | 早先某次操作破壞了 heap 結構 | 每次操作後呼叫 heap checker，找出第一個違反不變量的操作 | 修正那一次操作；保留 checker 直到最後 |
| Shell Lab 偶爾失敗、重跑又通過 | signal 造成的 race | 重複執行同一個 trace 數十次；在關鍵步驟間加入測試用延遲 | 用 signal mask 建立先後順序，不要用 `sleep` |
| Proxy 抓圖片時內容損壞或被截斷 | 用字串函式處理二進位 body | 比對直接下載與經過 proxy 下載的檔案大小與雜湊值 | body 依實際位元組數處理，使用 RIO 類的函式 |
| Proxy 在客戶端中斷後整個結束 | 收到 `SIGPIPE` | 用 `strace` 或 `gdb` 看 process 結束的原因 | 處理或忽略 `SIGPIPE`，並檢查 `write` 的錯誤 |
| Cache Lab 總數正確但個別 trace 錯 | LRU 或 set 選擇的邏輯有錯 | 用極小的 trace 印出每一步的 set 狀態，與手算比對 | 修正替換邏輯，再跑全部 trace |
| 效能數字每次差很多 | 機器負載、頻率調整、模擬環境 | 重複量測 5–10 次，看分散程度 | 固定環境、取中位數、在真機上量 |

> [!warning] 常見誤解
> 「分數滿分就代表我懂了。」分數只證明你通過了評分 script 的測試。真正的標準是：沒有這份 handout，你能不能在工作上的類似問題中，自己建立模型、打造驗證工具、找出證據。這也是為什麼照抄答案拿到的滿分，在面對 core dump 時一點用都沒有。

## 34.16 動手練習

1. **延伸程式一**：把 `sat_add` 改成「飽和減法」（結果小於 0 就停在 0），寫出不用分支的版本，並用同樣的窮舉 oracle 驗證。再故意引入一個只在 `a == b` 時出錯的 bug，確認 oracle 能抓到，並算出它應該回報幾組錯誤（答案：256 組，驗證方法是看程式輸出）。
2. **延伸程式二**：把 `max_cuts` 改成 3，先手算總切法數（1 + 53 + C(53, 2) + C(53, 3)），再執行驗證；接著寫一個新的 parser，只保留 buffer 最後 3 個 byte 加上新的資料來搜尋，用同一套切塊測試確認它正確，並說明它為什麼比 `BufferedParser` 有效率。
3. **手算**：一個 direct-mapped cache 有 16 個 set、block 64 bytes，兩個 16 × 16 的 `int` 陣列 A 與 B 在記憶體中緊鄰（B 緊接在 A 之後，A 從 block 邊界開始）。A[0][0] 與 B[0][0] 會落在同一個 set 嗎？A[3][5] 與 B[3][5] 呢？（提示：一個陣列是 1,024 bytes，cache 總共也是 1,024 bytes。答案：都會，因為兩者相差 1,024 bytes，剛好是 cache 大小的整數倍，set index 相同。）交替存取 A[i][j] 與 B[i][j] 時會發生哪一種 miss？
4. **反組譯練習**：把 34.5 節的 `check_dims` 改用 `-O0` 與 `-O2` 各編譯一次，比較三種最佳化等級的組合語言，寫下 `-O0` 版本中每個參數被存到 stack 的哪個位置。
5. **lab notebook**：選一個你要做的 Lab，在開始之前用 34.3 節的格式寫下第一輪的模型：輸入、狀態、不變量。做完之後回頭比較，哪些不變量是你一開始沒想到的？
6. **工作對照**：從 34.14 節的表中挑一個和你工作最相關的格子，找一個你過去遇過的實際問題，寫下當時如果具備這個 Lab 的能力，除錯流程會怎麼不同。

## 本章重點整理

- CS:APP 的九個 Labs 各自把一部分書中的觀念變成可以親手操作的系統問題；官方網站為每個 Lab 提供自學版材料，任何人都可以下載。
- 大部分 Lab 預設在 Linux x86-64 上執行；在 Apple Silicon Mac 上建議使用真正的 x86-64 Linux 環境，模擬環境會影響除錯與效能量測。
- Lab 的價值在於卡住、找證據、解開的過程，照抄答案等於丟掉這個過程；也不要公開自己的解答。
- 做任何 Lab 都可以用三輪方法：先建模與寫出不變量、再打造驗證工具、最後做對抗測試與最佳化。
- lab notebook 記錄假說、實驗、原始證據、解讀與下一步，格式和 production 的事件調查紀錄相同。
- 驗證要分四層：功能、邊界、不變量、對抗；評分 script 通常只覆蓋前兩層。
- Data Lab 練位元層級的推理，Bomb Lab 練從組合語言還原意圖，Attack Lab 讓 stack frame 與防禦機制變成親身經驗。
- Architecture Lab 練處理器設計與 pipeline 分析，Cache Lab 與 Performance Lab 練讓程式配合記憶體階層與量測紀律。
- Shell Lab 是第一次面對 signal 造成的並行與 race，Malloc Lab 練指標與資料結構不變量，Proxy Lab 把 I/O、網路、並行與快取全部串起來。
- 窮舉 oracle 適用於輸入空間小的問題，切塊測試能系統化地找出「資料分批到達」造成的錯誤，兩者都能在每個 Lab 中重複使用。
- Lab 之間有依賴：Bomb 在 Attack 之前，Shell 與 Malloc 在 Proxy 之前；時間有限時優先做 Bomb、Malloc、Shell、Proxy。
- 同一個問題卡超過兩小時，先寫 lab notebook、回頭重讀對應章節，找觀念而不是找答案。
- Labs 練出的能力直接對應到工作：讀 core dump、診斷記憶體成長、評估執行檔的防禦、用量測驅動效能最佳化、寫健壯的網路服務。

## 延伸問答

> [!question]- Q1. 為什麼說 Bomb Lab 練的不是「答案」，而是工作上真的會用到的能力？
> Bomb Lab 的設定是「只有執行檔、沒有原始碼」，要你從組合語言還原程式在檢查什麼。這和 production 除錯的處境一模一樣：core dump 裡的 stack trace 可能沒有行號，第三方 library 沒有原始碼，最佳化過的程式碼和你寫的 C 對不起來。這些時候你需要的正是認參數暫存器、切基本區塊、還原條件、辨認編譯器技巧的能力。
>
> 所以照抄答案的人和自己拆的人，分數一樣，能力卻完全不同。判斷自己有沒有真的懂的方法是：拿一個沒看過、刪掉符號的小執行檔，能不能在 `gdb` 裡找到它的邏輯，並寫出等價的 C 程式。

> [!question]- Q2. 你的 Malloc Lab 實作在 driver 跑到一半時 segfault，當機的位置在 `mm_malloc` 裡走訪 free list 的迴圈。你會怎麼找原因？
> 當機的位置通常不是出錯的位置。走訪 free list 時當機，代表 free list 的某個指標已經被破壞了，但破壞它的可能是很久之前的某次 `free`、coalesce 或 split。直接在當機點附近改程式，很難找到根因。
>
> 正確的作法是寫一個 heap checker，檢查每個區塊的對齊、header 與 footer 是否一致、相鄰的空閒區塊是否已經合併、free list 中的每個區塊是否真的是空閒的，並在每次操作之後呼叫它。這樣第一個違反不變量的操作會立刻被指出來，搜尋範圍從「整個 trace」縮小到「一次操作」。這也是工作上用 ASan 找 heap corruption 的同一種思路（第 26 章）。

> [!question]- Q3. 手算題：Cache Lab 的模擬器設定為 s = 4、E = 2、b = 4，位址 `0x1234` 會落在哪個 set？tag 是多少？
> b = 4 表示 block offset 佔最低 4 個 bit，s = 4 表示接下來 4 個 bit 是 set index，其餘是 tag（第 16 章）。`0x1234` 的二進位是 `0001 0010 0011 0100`。最低 4 bits 是 `0100`，offset = 4；接下來 4 bits 是 `0011`，set index = 3；剩下的 `0001 0010` 是 tag，等於 `0x12`。
>
> E = 2 表示每個 set 有 2 行，所以這個位址會在 set 3 的兩行中比對 tag 是否為 `0x12`。這種手算正是驗證模擬器的基礎：先用小 trace 手算每一步，再和程式的逐步輸出比對，而不是只比對最後的總數。

> [!question]- Q4. 有人說 Shell Lab 的測試偶爾失敗，在 fork 之後加一行 `sleep(1)` 就全部通過了。這樣修對嗎？
> 不對。偶爾失敗、加延遲就通過，幾乎可以確定是 race：子行程結束得太快，`SIGCHLD` handler 在主程式把它加入 job 表之前就執行了。`sleep` 只是改變了「通常」的執行順序，讓壞的交錯變得不容易發生，並沒有讓它不可能發生；換一台機器、負載變高，或子行程本身變慢，問題就會回來。而且每個指令都多等一秒，shell 也變得不能用。
>
> 正確的作法是建立確定的先後順序：在可能被 handler 同時存取的共享狀態前後阻擋相關的 signal（第 22 章的 `sigprocmask`），等待前景工作時用 `sigsuspend` 這類原子操作。修好之後要用壓力測試證明：重複執行數百次都不再失敗。

> [!question]- Q5. Attack Lab 的第二個目標程式開啟了 stack 不可執行與位址隨機化，為什麼 ROP 仍然可行？這對真實系統的防禦有什麼啟示？
> stack 不可執行（NX）阻止了「把機器碼放進 stack 再跳過去」，位址隨機化（ASLR）讓攻擊者難以預測 stack 的位置。但 ROP 不需要注入新的程式碼，而是串接程式中已經存在、可執行的指令片段，每個片段以 `ret` 結尾，靠 stack 上排列好的位址一個接一個執行。如果程式本身的程式碼區段位置是固定的（例如沒有編成 PIE），這些片段的位址就是可預測的。
>
> 這說明防禦是層層疊加的：NX 擋 code injection，ASLR 加 PIE 讓片段位址難以預測，stack canary 讓覆寫 return address 時先被偵測，control-flow integrity 類的機制進一步限制跳躍目標。任何一層單獨都不夠，根本的解法仍是不要寫出 overflow（第 11 章）。

> [!question]- Q6. 你只有一個月、目標是準備後端工程師的系統類面試，會怎麼安排 Labs？為什麼？
> 優先做 Bomb、Malloc、Shell、Proxy 四個。Bomb Lab 練讀組合語言與 `gdb`，面試常出「這段組合語言在做什麼」；Malloc Lab 是「實作 malloc」「解釋碎片」這類題目的最佳準備，也最能練指標；Shell Lab 涵蓋 fork、exec、wait、signal 與 race，是作業系統題的核心；Proxy Lab 把 socket、HTTP、並行與 thread-safe 快取串起來，直接對應「設計一個 thread-safe 的 LRU cache」「寫一個並行伺服器」。
>
> 每個 Lab 約一週，並把重點放在能講出來的東西：遇過哪些 bug、怎麼找到、怎麼證明修好了。Data Lab 的位元題可以用零碎時間練習，Architecture 與 Performance Lab 在這個目標下可以先跳過。

> [!question]- Q7. 程式找錯：有人的 proxy 用 `strcpy` 把上游回應存進快取，網頁都正常，但圖片經過 proxy 之後打不開。原因是什麼？怎麼驗證？
> `strcpy` 與 `strlen` 這類字串函式以 `\0` 判斷結尾。HTML 是文字，中間不會有 `\0`，所以網頁正常；圖片是二進位資料，中間幾乎一定有值為 0 的位元組，字串函式複製到那裡就停了，存進快取與回傳給瀏覽器的內容都被截斷。
>
> 驗證方法是直接下載與經過 proxy 下載同一張圖片，比較檔案大小與雜湊值，並找出兩者開始不同的位置，通常就是第一個 `\0` 出現的地方。修法是記錄每次 `read` 實際讀到的位元組數，用 `memcpy` 與明確的長度處理 body（第 27 章）。header 可以當文字處理，body 不行。

> [!question]- Q8. 34.12 節的窮舉 oracle 在 8-bit 輸入上可行，但 Data Lab 的函式是 32-bit，無法窮舉全部 2^64 種雙參數輸入。還有什麼方法能得到足夠的信心？
> 第一，縮小寬度：很多位元技巧的正確性不依賴寬度，可以把同一個式子改寫成 8-bit 或 4-bit 版本完整窮舉，再論證它推廣到 32-bit 時仍成立。第二，測所有邊界值的組合：0、1、−1、TMin、TMax、TMin + 1、TMax − 1，以及浮點數的 0、−0、最小與最大的 denormalized 數、最小的 normalized 數、∞、NaN，兩兩組合。
>
> 第三，大量隨機測試，並且讓隨機數偏向邊界附近，而不是均勻分布。第四，用形式化工具：有些版本的 Data Lab 教師材料附有以 binary decision diagram（BDD）對所有輸入做驗證的檢查器（34.4 節），業界也有 SMT solver 可以證明兩個位元運算式等價。最後，最重要的是能用一句話說出式子成立的理由；測試只能證明有錯，理由才能說服你它是對的。

## 延伸閱讀

- [CS:APP 3e Lab Assignments](https://csapp.cs.cmu.edu/3e/labs.html)：九個 Labs 的官方說明、writeup 與自學版材料下載。
- [CS:APP 3e 學生資源](https://csapp.cs.cmu.edu/3e/students.html)：官方提供給學生的補充資源。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：使用這些 Labs 的原始課程，有講義與時程可以參考進度。
- [GDB 官方文件](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)：Bomb Lab 與 Attack Lab 最常用的工具，`x`、`stepi`、`disassemble` 的完整說明。
- [ThreadSanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html) 與 [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)：Proxy Lab 與 Malloc Lab 之後，把驗證工具帶進日常開發。
- [Linux man pages](https://man7.org/linux/man-pages/)：`signal(7)`、`sigprocmask(2)`、`setpgid(2)`、`socket(7)` 等 Shell Lab 與 Proxy Lab 會用到的頁面。
