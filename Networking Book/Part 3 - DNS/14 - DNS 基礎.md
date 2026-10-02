---
chapter: 14
title: DNS 基礎：從網域名稱到 IP
part: 3
---

# 第 14 章　DNS 基礎：從網域名稱到 IP

> [!abstract] 本章地圖
> **核心問題**：瀏覽器拿到 `api.shengsheng.example` 這個名字之後，是誰、經過幾站、用什麼格式的訊息，把它變成一個 IP 位址？答案又為什麼會「改了卻沒生效」？
>
> **你會學到**：
> - 畫出 DNS 的階層（root、TLD、authoritative）與 zone 的授權關係，說明 stub resolver、recursive resolver、authoritative server 各自的工作
> - 逐步追蹤一次遞迴加迭代的解析流程，包括 referral、glue 與 CNAME 的重新解析
> - 讀懂並正確使用 A、AAAA、CNAME、MX、TXT、NS、SOA、SRV、CAA、HTTPS／SVCB 等 record
> - 用 TTL 與多層快取解釋「DNS 生效要多久」，規劃不出事的 DNS 變更
> - 看懂 DNS 訊息的 header、question、answer 與 name compression，用 Python 手組查詢、解析回應，並寫出帶 TTL 快取的 stub resolver
> - 用 `dig` 判斷問題出在快取、recursive resolver 還是權威 server
>
> **前置知識**：第 5 章（IPv4 與 IPv6 位址）、第 9 章（UDP 與 socket API）；第 2 章的 byte order 與 header 解析

## 14.1 故事：改了 DNS，舊機器卻還在接流量

週五晚上九點，聲聲 Live 要把 API 從舊機房搬到雲端的新 load balancer。小晴負責最後一步：在 DNS 代管服務的後台，把 `api.shengsheng.example` 的 A record 從舊機房的 `203.0.113.20` 改成新 LB 的 `203.0.113.80`。按下儲存後，後台立刻顯示新值；小晴在自己的筆電上執行 `dig api.shengsheng.example`，也看到 `203.0.113.80`。確認無誤，小晴在九點十分把舊機房的 API 伺服器關機，準備收工。

九點十五分，客服群組開始湧進訊息：「學生說 App 一直轉圈圈」「老師的課表載不出來」。監控圖表上，新 LB 的流量只有平常的三成。小晴很困惑：DNS 明明已經改了，自己也查到新 IP 了，為什麼還有七成的使用者連不上？

阿德看了一眼 DNS 後台的設定，指著 TTL 欄位的 `3600`：「這筆 record 的 TTL 是一小時。九點之前查過這個名字的 resolver，會把舊答案留在快取裡，最晚留到十點才會再問一次。你的筆電剛好問到一台快取裡沒有這筆資料的 resolver，所以看到新值；那不代表全世界都看到新值。」兩人立刻把舊機器開回來，等到十點多舊流量歸零，才真正下線。

事後檢討時，阿德在白板上寫了一句話：「DNS 沒有『生效』這回事，只有快取過期。」小晴這才發現，自己對 DNS 的理解只停在「把名字變成 IP」：不知道答案是誰給的、中間經過幾台機器、每一台會記住多久，也看不懂 `dig` 輸出裡那些 `flags: qr rd ra` 和 `AUTHORITY SECTION` 代表什麼。

同一週還有兩件事排隊等著：行銷要把 `www.shengsheng.example` 改指到 CDN，CDN 廠商要求「設一筆 CNAME」；Rita 則要在網域上加一筆 TXT 做網域所有權驗證，另外再加一筆 CAA 限制哪些 CA 能幫聲聲 Live 發憑證。這一章就從這三件事出發，把 DNS 從階層、流程、record、快取一路拆到訊息的每一個 byte，最後親手寫一台假的權威 DNS server、一個手組封包的 client，以及一個會依 TTL 快取的 stub resolver。

## 14.2 為什麼需要 DNS：名字和位址必須分開

網路層只認得 IP 位址（第 5 章），但人記不住 `203.0.113.80`，更重要的是位址會變：搬機房、換雲端、加 CDN、做災難切換，IP 都會改。如果 App 和瀏覽器直接寫死 IP，每次搬家都得發新版本。所以需要一層**間接層**：程式只記名字，名字對應到哪個位址，交給一個可以隨時更新的系統來回答。這個系統就是 **DNS（Domain Name System，網域名稱系統）**。例如聲聲 Live 的 App 只寫 `api.shengsheng.example`，今天搬到新 LB，只要改 DNS，App 一行都不用動。

早期的 ARPANET 用一個集中維護的 `HOSTS.TXT` 檔案做這件事：所有主機名稱和位址寫在一個檔案裡，各站定期下載。主機數量一多，這個方法就撐不住：單一維護單位變成瓶頸、檔案越來越大、名字容易衝突、更新延遲很長。DNS 在 1980 年代被設計出來，核心想法有三個，到今天都沒變：

1. **階層式命名**：名字像檔案路徑一樣分層，每一層由不同單位管理，名字衝突只需要在同一層內解決。
2. **分散式授權（delegation）**：上層只記得「下一層歸誰管」，不必知道下層的所有資料。`.example` 的管理者只需要知道 `shengsheng.example` 的權威 server 是誰，至於 `api.shengsheng.example` 指到哪裡，由聲聲 Live 自己決定。
3. **大量快取**：每個答案都帶有可以被記住的時間（TTL），讓絕大多數查詢在離使用者很近的地方就被回答，不必每次都問到最上層。

這三個設計讓 DNS 成為網際網路上規模最大的分散式資料庫之一，但也直接造成了故事裡的問題：快取讓 DNS 很快、很耐用，代價是更新不會立刻被所有人看見。理解 DNS，基本上就是理解「誰是權威」和「誰在快取」這兩件事。

`/etc/hosts` 其實就是 `HOSTS.TXT` 的後代，今天的作業系統仍然會先查它再問 DNS；這部分和 resolv.conf、search domain 等系統設定留到第 16 章。

## 14.3 網域名稱的結構：label、樹與 zone

**網域名稱（domain name）** 是一串用點分隔的 **label**，從右往左越來越具體。`api.shengsheng.example` 有三個 label：`example`、`shengsheng`、`api`。最右邊其實還有一個看不見的空 label，代表樹的根，也就是 **root**；寫成 `api.shengsheng.example.`（結尾有點）時稱為 **FQDN（Fully Qualified Domain Name，完整網域名稱）**，意思是「這個名字已經寫到根了，不要再幫我補任何後綴」。例如在 zone 檔裡寫 `www` 而沒有結尾的點，代管軟體會自動補成 `www.shengsheng.example.`；如果寫成 `web.shengsheng.example` 卻忘了結尾的點，有些軟體會補成 `web.shengsheng.example.shengsheng.example.`，這是非常經典的設定錯誤。

幾個硬性限制要記住：每個 label 最長 63 bytes；整個名字編碼成 wire format（封包裡的格式，見 14.8 節）後最長 255 bytes；比對名字時不分大小寫，`API.ShengSheng.Example` 和 `api.shengsheng.example` 是同一個名字。中文等非 ASCII 的網域名稱（IDN）在 DNS 封包裡會先轉成以 `xn--` 開頭的 ASCII 形式（Punycode），DNS 協定本身只看到 ASCII。

```text
                              . （root）
               ┌──────────────┼──────────────────┐
             com             example             test          ← TLD
                    ┌─────────┼──────────┐        │
              shengsheng   other-site   ...    cdnedge         ← 第二層
        ┌──────┬────┴───┬───────┐               │
       www    api      rt     live              ss
                                                
  zone 切點（delegation）：
  ┌ root zone ──────────────┐  只記得 com、example、test 的 NS
  ├ example zone ───────────┤  只記得 shengsheng.example 的 NS
  └ shengsheng.example zone ┘  真正存放 www、api、rt、live 的 record
```

這張圖由上往下讀：最上面是 root，下一層是 **TLD（Top-Level Domain，頂級網域）**，例如 `com`、各國的 `tw`、`jp`，以及本書範例用的保留名稱 `example` 和 `test`；再下一層是組織註冊的網域，例如 `shengsheng.example`。圖下半部標出了 **zone** 的邊界：zone 是「由同一個單位管理、存在同一組權威 server 上」的一段樹。root zone 只記得每個 TLD 交給誰管，`example` zone 只記得 `shengsheng.example` 交給誰管；`www.shengsheng.example` 的實際 IP 只存在聲聲 Live 自己的 zone 裡。

**domain** 和 **zone** 常被混用，但意思不同。domain 是樹上某個節點加上它底下的全部子樹；zone 是實際的管理單位。`shengsheng.example` 這個 domain 包含 `rt.shengsheng.example`；但如果聲聲 Live 把 `rt.shengsheng.example` 再授權給即時服務團隊自己的 DNS server，那 `rt` 就變成另一個 zone，雖然它仍屬於 `shengsheng.example` 這個 domain。把子樹交出去的動作叫 **delegation（授權）**：上層 zone 放一組 NS record，說「這個名字以下，去問這幾台 server」。

## 14.4 三種角色：stub、recursive 與 authoritative

一次 DNS 查詢牽涉三種角色，故事裡小晴的困惑，有一大半來自把它們混為一談。

**stub resolver** 是作業系統或程式裡最簡單的那一層：它不會自己去爬樹，只會把問題丟給一台設定好的 resolver，等答案回來。Python 的 `socket.getaddrinfo()`、瀏覽器呼叫的系統 API，最後都會經過某個 stub resolver。例如 macOS 上的 mDNSResponder、Linux 上的 systemd-resolved 或 glibc 的解析函式，都扮演這個角色（細節見第 16 章）。

**recursive resolver（遞迴 resolver）** 是真正會「跑腿」的那台：收到 stub 的問題後，它從 root 開始一站一站往下問，直到拿到答案，再把答案交回給 stub，並把沿途的結果放進快取。家用路由器轉送到的 ISP DNS、公司內部的 DNS、Google Public DNS、Cloudflare 的公共 DNS，都是 recursive resolver。它也常被叫做 **caching resolver** 或 **full resolver**。有些機器只是把查詢轉給另一台 recursive resolver，自己不爬樹，這種叫 **forwarder**，家用路由器內建的 DNS 多半就是 forwarder。

**authoritative server（權威 server）** 是某個 zone 的資料來源：它不問別人，只回答自己 zone 內的資料，或告訴你「這部分我授權給誰了」。root server、TLD server、聲聲 Live 使用的 DNS 代管服務，都是 authoritative server，只是負責的 zone 不同。小晴在後台改的，正是 authoritative server 上的資料。

```text
 小晴的筆電／學生的手機          ISP、公司或公共 DNS                權威 server 群
 ┌─────────────────────┐       ┌──────────────────────┐        ┌────────────────────┐
 │ App → getaddrinfo() │ 遞迴   │  recursive resolver  │ 迭代   │ root servers       │
 │ stub resolver       │──────►│  ┌────────────────┐  │──────► │ 13 組名稱，anycast  │
 │ （OS 快取）          │ RD=1  │  │ 快取（依 TTL）   │  │        ├────────────────────┤
 └─────────────────────┘◄──────│  └────────────────┘  │──────► │ .example TLD       │
                       最終答案 └──────────────────────┘        ├────────────────────┤
                                 快取命中就不往右走       ──────► │ shengsheng.example │
 瀏覽器自己也可能有一層快取                                       │ （DNS 代管服務）     │
                                                                └────────────────────┘
```

這張拓撲圖從左往右讀。最左邊的 App 透過 stub resolver 發出查詢，查詢裡的 **RD（Recursion Desired）** 旗標設為 1，意思是「請幫我問到底」。中間的 recursive resolver 先看自己的快取；沒有的話才往右邊的權威 server 群一站一站問。右邊的三層權威 server 各管一段 zone，彼此不互相轉送。最後答案原路回到 stub。要注意每一層都可能有快取：瀏覽器、OS 的 stub、recursive resolver 都會記住答案，所以「我查到的值」只代表「我這條路徑上的快取或權威 server 給的值」。

root server 常被說成「全世界只有 13 台」，這是誤解。13 指的是 `a` 到 `m` 這 13 組名稱與位址，每一組背後都用 **anycast**（第 6 章）部署在世界各地，總共有上千個實體，查詢會被路由到最近的一個。

| 角色 | 典型例子 | 會不會自己爬樹 | 有沒有快取 | 回答的權威性 |
|---|---|---|---|---|
| stub resolver | OS 的解析函式、`getaddrinfo()` | 不會，只問設定好的 resolver | 視實作，常有短暫快取 | 轉述別人的答案 |
| forwarder | 家用路由器、部分公司 DNS | 不會，轉給上游 | 通常有 | 轉述別人的答案 |
| recursive resolver | ISP DNS、公共 DNS、公司內部 DNS | 會，從 root 往下迭代 | 有，依 TTL | 轉述（回應的 AA=0） |
| authoritative server | root、TLD、DNS 代管服務 | 不會 | 不需要，資料就在本地 | 權威（回應的 AA=1） |

表格最後一欄的 **AA（Authoritative Answer）** 是回應 header 裡的一個旗標：權威 server 回答自己 zone 內的資料時會設 AA=1；recursive resolver 轉述快取裡的答案時 AA=0。後面用 `dig` 除錯時，看 AA 就能分辨「這是權威來源說的」還是「這是某台快取說的」。

## 14.5 一次完整的解析：遞迴與迭代

DNS 查詢有兩種問法。**遞迴查詢（recursive query）**：「請你幫我問到最終答案再回我」，stub 問 recursive resolver 用的就是這種。**迭代查詢（iterative query）**：「你知道多少就告訴我多少」，被問的 server 要嘛直接給答案，要嘛給一個 **referral（轉介）**：「這個名字我沒有，但我知道該去問誰」。recursive resolver 問權威 server 用的就是迭代。整個流程是「一次遞迴，包著好幾次迭代」。

以學生的手機第一次查 `www.shengsheng.example` 為例，而且假設 recursive resolver 的快取是空的，CDN 那邊的名字是 `ss.cdnedge.test`：

```text
 stub          recursive resolver        root         .example TLD     shengsheng 權威     .test TLD     cdnedge 權威
  │ www.shengsheng.example A? (RD=1)       │                │                │               │               │
  │──────────────►│                        │                │                │               │               │
  │               │── www...example A? ───►│                │                │               │               │
  │               │◄── referral: example NS a.nic.example + glue IP          │               │               │
  │               │── www...example A? ────────────────────►│                │               │               │
  │               │◄── referral: shengsheng.example NS ns1.shengsheng.example + glue         │               │
  │               │── www...example A? ─────────────────────────────────────►│               │               │
  │               │◄── answer (AA=1): www CNAME ss.cdnedge.test ─────────────│               │               │
  │               │   （名字換了，從頭解析 ss.cdnedge.test）                    │               │               │
  │               │── ss.cdnedge.test A? ─►│                │                │               │               │
  │               │◄── referral: test NS a.nic.test + glue  │                │               │               │
  │               │── ss.cdnedge.test A? ───────────────────────────────────────────────────►│               │
  │               │◄── referral: cdnedge.test NS ns.cdnedge.test + glue ─────────────────────│               │
  │               │── ss.cdnedge.test A? ───────────────────────────────────────────────────────────────────►│
  │               │◄── answer (AA=1): 198.51.100.7, 198.51.100.8 ─────────────────────────────────────────────│
  │◄── www CNAME ss.cdnedge.test; ss.cdnedge.test A 198.51.100.7, 198.51.100.8 (RA=1)        │               │
```

逐步看這張時序圖：

1. stub 送出一個 RD=1 的查詢給 recursive resolver，之後就只是等待。
2. recursive resolver 快取是空的，只好從 **root hints** 開始。root hints 是內建在 resolver 軟體裡的一份 root server 名單與位址，是整個系統唯一需要「寫死」的資料。root 不知道 `www.shengsheng.example`，但知道 `example` 這個 TLD 授權給 `a.nic.example`，於是回一個 referral。
3. referral 裡除了 NS 名稱，還附上 `a.nic.example` 的 IP，這叫 **glue record**。為什麼需要 glue？因為要找到 `a.nic.example` 的 IP，本來得去問 `example` 的 server，但那正是我們要找的 server，會變成雞生蛋問題。所以上層直接把位址「黏」在 referral 裡一起給。
4. TLD 再給一次 referral，指向聲聲 Live 的權威 server `ns1.shengsheng.example`，同樣附 glue。
5. 聲聲 Live 的權威 server 回答 AA=1 的答案：`www` 是 `ss.cdnedge.test` 的 CNAME。名字換了，recursive resolver 必須以新名字重新解析，而 `cdnedge.test` 在完全不同的 TLD 底下，於是再從 root 問起。
6. 經過 `test` TLD 和 CDN 的權威 server，最後拿到兩個 A record。
7. recursive resolver 把整條 CNAME 鏈和最後的 A record 一起交給 stub，並設 **RA（Recursion Available）** 旗標表示「我提供遞迴服務」。

第一次解析送出了六個查詢，看起來很慢；但這些 referral 和答案都會被快取。下一位學生再查 `api.shengsheng.example` 時，resolver 已經記得 `shengsheng.example` 的權威 server 是誰，直接問最後一站就好。root 和 TLD 的 NS record 通常 TTL 長達一天以上，因此實際上 recursive resolver 很少需要問 root。14.11 節會用純 Python 模擬這整個過程，並數出查詢次數。

> [!warning] 常見誤解
> 「DNS 查詢是一路轉送上去的」不正確。權威 server 之間不互相轉送，也不知道誰在問；所有跑腿都由 recursive resolver 完成。也因此聲聲 Live 的權威 server 看到的來源位址，是 recursive resolver 的 IP，而不是學生手機的 IP。這點對第 15 章的 GeoDNS 很重要。

現代 recursive resolver 多半還會做 **QNAME minimisation**：問 root 時只問「`example` 的 NS 是誰」，而不是把完整的 `www.shengsheng.example` 告訴每一層，減少不必要的隱私外洩。流程的骨架不變，只是每一站看到的問題比較少。

## 14.6 Resource record：DNS 裡的每一筆資料

DNS 的資料單位叫 **resource record（RR，資源紀錄）**，每一筆都有五個欄位：名稱（owner name）、類型（type）、類別（class，幾乎永遠是 `IN`，代表 Internet）、TTL（秒）、資料（RDATA）。用 zone 檔的文字格式寫出來長這樣：

```text
 owner name                 TTL    class  type    RDATA
 api.shengsheng.example.    60     IN     A       203.0.113.20
 web.shengsheng.example.    300    IN     AAAA    2001:db8:5::10
 www.shengsheng.example.    300    IN     CNAME   web.shengsheng.example.
 shengsheng.example.        3600   IN     MX      10 mail.shengsheng.example.
 shengsheng.example.        3600   IN     TXT     "shengsheng-verify=7f3a9c"
 shengsheng.example.        86400  IN     NS      ns1.shengsheng.example.
 shengsheng.example.        3600   IN     CAA     0 issue "ca.example.net"
 _turn._udp.shengsheng.example. 300 IN    SRV     10 50 3478 turn.shengsheng.example.
 api.shengsheng.example.    300    IN     HTTPS   1 . alpn="h2,h3"
```

每一行由左到右是「哪個名字、可以被快取多久、哪個類別、什麼類型、內容是什麼」。同一個名字、同一個類型可以有多筆，例如 `web.shengsheng.example` 可以有兩筆 A record，合起來叫一個 **RRset**；DNS 永遠以 RRset 為單位回答與快取，不會只給你其中一筆。下面這張表整理本章要求認識的類型，type 編號是在封包裡實際出現的數字。

| 類型（編號） | 用途 | RDATA 範例 | 聲聲 Live 的用法與注意事項 |
|---|---|---|---|
| A（1） | 名字對應 IPv4 位址 | `203.0.113.20` | `api` 指到 LB；可多筆做簡單分散 |
| AAAA（28） | 名字對應 IPv6 位址 | `2001:db8:5::10` | dual stack 時與 A 並存，client 通常兩者都查 |
| CNAME（5） | 這個名字是另一個名字的別名 | `ss.cdnedge.test.` | `www` 指到 CDN；同名不能再有其他類型的 record |
| MX（15） | 收信伺服器，數字小的優先 | `10 mail.shengsheng.example.` | 目標必須是有 A／AAAA 的名字，不能是 CNAME |
| TXT（16） | 任意文字 | `"shengsheng-verify=7f3a9c"` | 網域所有權驗證、SPF 等郵件政策 |
| NS（2） | 這個 zone 由哪些權威 server 負責 | `ns1.shengsheng.example.` | 出現在上層（delegation）與 zone 自己的 apex |
| SOA（6） | zone 的起始資訊：主要 server、管理信箱、序號、計時參數 | `ns1... hostmaster... 2026100201 ...` | 每個 zone 恰好一筆；序號用於同步，負面快取時間也看它 |
| SRV（33） | 某個服務在哪台主機、哪個 port | `10 50 3478 turn.shengsheng.example.` | 名字格式是 `_服務._協定.網域` |
| CAA（257） | 允許哪些 CA 為這個網域簽發憑證 | `0 issue "ca.example.net"` | Rita 用它限制發證來源（第 19 章） |
| SVCB（64）／HTTPS（65） | 服務繫結：告訴 client 支援的協定、port、位址提示 | `1 . alpn="h2,h3"` | 讓瀏覽器在連線前就知道可以用 HTTP/3（第 22 章） |
| PTR（12） | 反查：IP 對應回名字 | `api.shengsheng.example.` | 放在 `in-addr.arpa`／`ip6.arpa` 樹下，郵件與 log 常用 |

幾個類型值得多說幾句。

**CNAME** 的意思是「我只是別名，所有問題都去問正名」。所以規格要求：一個名字如果有 CNAME，就不能再有其他類型的資料。這帶來一個實務限制：zone 的頂端（**apex**，例如 `shengsheng.example` 本身）一定要有 SOA 和 NS，因此 apex 不能設 CNAME。行銷想把「不帶 www 的網址」也指到 CDN 時就會撞到這面牆，解法（ALIAS、CNAME flattening、HTTPS record 的 AliasMode）留到第 15 章。另外，CNAME 每多一層，resolver 就可能多跑一輪解析，像 14.5 節那樣從 root 再問一次，所以 CNAME 鏈不要拉太長。

**SOA（Start of Authority）** 的 RDATA 有七個欄位：主要權威 server 名稱、管理者信箱（第一個點代表 @）、序號（serial）、refresh、retry、expire，以及 minimum。序號讓次要 server 判斷 zone 是否更新、需不需要做 zone transfer，常見的寫法是 `YYYYMMDDnn`，例如 `2026100201`。最後一個欄位在現代用來決定「查無此名」這種負面答案可以被快取多久，第 15 章談 negative caching 時會用到。

**SRV** 讓 client 不必寫死 port：`_turn._udp.shengsheng.example` 的 SRV 說「TURN 服務用 UDP，在 `turn.shengsheng.example` 的 3478 port，priority 10、weight 50」。priority 越小越優先，相同 priority 時依 weight 比例分配。SIP、XMPP、部分服務發現系統都使用 SRV；瀏覽器的 HTTP 則不看 SRV，這也是 HTTPS record 被發明的原因之一。

**HTTPS／SVCB** 是比較新的類型。HTTPS record 的第一個欄位是 priority：0 代表 **AliasMode**（類似「去看另一個名字」，而且可以放在 apex），1 以上代表 **ServiceMode**，後面接參數，例如 `alpn="h2,h3"` 告訴瀏覽器這個網站支援 HTTP/3，`ipv4hint` 給位址提示，還有供 TLS ECH 使用的 `ech` 參數。好處是瀏覽器在連線之前，就能從 DNS 知道該用哪個協定，省下一次「先用 HTTP/2 連、再從 `Alt-Svc` 得知可以升級」的來回。

> [!note] 2026 現況
> 截至 2026 年 10 月：SVCB／HTTPS record 定義在 RFC 9460；依 2026 年 10 月查證，HTTPS／SVCB 的 `ech` 參數由 RFC 9848 定義，ECH 本身是 RFC 9849。瀏覽器是否查詢 HTTPS record，依瀏覽器、作業系統與是否使用 DoH 而定，例如部分瀏覽器只在使用 DoH 時才查。不要假設所有使用者都會讀到 HTTPS record；它是加速與升級的提示，不能取代 A／AAAA。

> [!example] 例子
> Rita 要加的兩筆 record：`shengsheng.example. 3600 IN TXT "shengsheng-verify=7f3a9c"` 讓驗證服務確認聲聲 Live 確實控制這個網域；`shengsheng.example. 3600 IN CAA 0 issue "ca.example.net"` 告訴所有 CA「只有 ca.example.net 可以為這個網域發憑證」，其他 CA 在簽發前查到 CAA 就必須拒絕。ACME 的 DNS-01 驗證也是靠 TXT record，詳見第 16 章與第 19 章。

## 14.7 TTL 與快取：「生效」其實是「過期」

**TTL（Time To Live）** 是每筆 record 附帶的秒數，意思是「拿到這個答案的人，最多可以把它記住這麼久」。TTL 由權威 server 的設定決定，recursive resolver 把答案放進快取後開始倒數；倒數期間有人再問，resolver 直接從快取回答，並把**剩下的秒數**當成 TTL 回傳。所以同一筆 record，從權威 server 查到的 TTL 是固定的 3600，從 recursive resolver 查到的可能是 2741、1012、15，每次都在變小。

用故事裡的時間軸看就很清楚：

```text
 時間 →     20:30         21:00          21:10           21:15            22:00         22:30
            │             │              │               │                │             │
 resolver X ●查詢，快取舊值 203.0.113.20（TTL 3600，到 21:30 過期）──────────┐ 21:30 過期
            │             │              │               │          21:30 再問，拿到新值 │
 resolver Y │             │ ●20:59 查詢，快取舊值（到 21:59 過期）──────────────┐ 21:59 過期
            │             │              │               │                │             │
 權威 server │  舊值 .20    │◄─21:00 改成 203.0.113.80 ──────────────────────────────────────►
            │             │              │               │                │             │
 小晴的筆電   │             │  ●21:02 問到 resolver Z（快取是空的）→ 新值 .80    │             │
            │             │              │               │                │             │
 舊機器      │◄──────── 開機 ───────────►│ 21:10 關機 ✗   │ 21:15 客服湧入 │ 開回來，等到 22:00 後再下線
```

這張時間軸由上往下讀，每一列是一個角色：

1. resolver X 在 20:30 查過一次，把舊值記到 21:30。21:00 權威 server 改了，但 X 不會知道，因為權威 server 不會通知任何快取；X 要等到 21:30 過期、有人再問，才會拿到新值。
2. resolver Y 在 20:59 才查，舊值一路留到 21:59。這就是「最壞情況要等一個完整 TTL」的來源：改動前最後一刻被快取的答案，會在改動後再活一整個 TTL。
3. 小晴的筆電剛好用到快取是空的 resolver Z，所以 21:02 就看到新值，造成「已經生效」的錯覺。
4. 舊機器 21:10 關機時，X 和 Y 背後的使用者還在連舊 IP，事故就發生了。

所以阿德說「沒有生效，只有過期」：DNS 沒有推播機制，權威 server 改完之後，世界上每一份快取都會在各自的時間點過期，最晚的那份要等到「改動時間＋舊 TTL」。網路上常說的「DNS propagation 要 24 到 48 小時」，其實就是在描述長 TTL 加上各層快取的效果，而不是 DNS 有什麼緩慢的傳播程序。

快取不只一層。瀏覽器有自己的 DNS 快取，作業系統的 stub 可能有，recursive resolver 一定有，有些語言 runtime 或 HTTP client library 也會自己快取，甚至有應用程式在啟動時解析一次就永遠不再解析。最後這種最麻煩：不管 TTL 多短，程式都會一直連舊 IP，直到重新啟動。第 16 章會專門處理應用程式層的 DNS 快取。

| TTL 長度 | 優點 | 缺點 | 適合的 record |
|---|---|---|---|
| 短（30–300 秒） | 變更與切換很快被看見 | 查詢量大、權威 server 故障時影響很快浮現 | 需要快速切換的 LB、CDN 入口、準備搬遷中的名字 |
| 中（300–3600 秒） | 查詢量與彈性的折衷 | 變更最多要等一小時 | 一般網站與 API |
| 長（數小時到數天） | 查詢量極小、權威 server 短暫故障時快取還撐得住 | 改錯了要很久才能修正 | NS、很少變動的 MX、TXT 驗證 |

表格說明 TTL 是一個取捨，不是越短越好。TTL 很短時，recursive resolver 幾乎每分鐘都要回來問權威 server，權威 server 一旦故障，使用者很快就解析不到；TTL 很長時，權威 server 掛掉幾小時都還有快取撐著，但改錯了也要很久才救得回來。實務上的做法是平常用中等 TTL，計畫變更前先把 TTL 調低，等舊 TTL 過完再改值，改完確認穩定後再把 TTL 調回去，14.12 節會把它寫成檢查清單。

還有兩個細節。第一，recursive resolver 可以把 TTL 截短（例如設上限），也有些實作會設下限，不一定百分之百照權威 server 的 TTL，這依實作與營運者設定而定。第二，「查無此名」也會被快取，叫 **negative caching**：如果有人在 record 建立前就查過並得到 NXDOMAIN，這個「不存在」也會被記住一段時間，時間長短由 SOA 決定，第 15 章詳談。

## 14.8 DNS 訊息格式：12 bytes 的 header 加四個區段

DNS 的查詢和回應用同一種訊息格式。理解它，`dig` 的輸出和 Wireshark 裡的每一行就都看得懂了。一個 DNS 訊息由五個部分依序組成：

```text
 ┌──────────────────────────────┐
 │ Header（固定 12 bytes）        │  ID、旗標、四個區段各有幾筆
 ├──────────────────────────────┤
 │ Question                     │  問什麼：QNAME、QTYPE、QCLASS（通常 1 筆）
 ├──────────────────────────────┤
 │ Answer                       │  直接回答問題的 RR（含 CNAME 鏈）
 ├──────────────────────────────┤
 │ Authority                    │  referral 時放 NS；NXDOMAIN 時放 SOA
 ├──────────────────────────────┤
 │ Additional                   │  glue 的 A／AAAA、EDNS 的 OPT
 └──────────────────────────────┘
```

查詢通常只有 header 和 question；回應會把 question 原樣帶回，再加上三個 RR 區段。三個區段的分工很重要：answer 是「你問的答案」；authority 是「關於誰有權威的資訊」，referral 的 NS 就放這裡，NXDOMAIN 回應也會在這裡放 zone 的 SOA，讓 resolver 知道負面答案能快取多久；additional 是「你接下來大概會需要的東西」，例如 glue 位址，以及 14.9 節要講的 EDNS OPT。

Header 的位元布局如下，每列 16 bits，全部用 big-endian（網路位元組順序，第 2 章）：

```text
  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
 ┌───────────────────────────────────────────────┐
 │                      ID                       │  bytes 0-1
 ├──┬───────────┬──┬──┬──┬──┬──┬──┬──┬───────────┤
 │QR│  Opcode   │AA│TC│RD│RA│Z │AD│CD│   RCODE   │  bytes 2-3（flags）
 ├──┴───────────┴──┴──┴──┴──┴──┴──┴──┴───────────┤
 │                   QDCOUNT                     │  bytes 4-5  question 筆數
 ├───────────────────────────────────────────────┤
 │                   ANCOUNT                     │  bytes 6-7  answer 筆數
 ├───────────────────────────────────────────────┤
 │                   NSCOUNT                     │  bytes 8-9  authority 筆數
 ├───────────────────────────────────────────────┤
 │                   ARCOUNT                     │  bytes 10-11 additional 筆數
 └───────────────────────────────────────────────┘
```

逐欄解說：**ID** 是 client 隨機挑的 16 bit 數字，回應會原樣帶回，client 靠它把回應和查詢配對，對不上就丟掉。第二列的 flags 從最高位開始：QR 為 0 表示查詢、1 表示回應；Opcode 4 bits，一般查詢是 0；AA、RD、RA 前面介紹過；**TC（Truncated）** 表示回應被截斷了，14.9 節會解釋；Z 保留為 0；AD 和 CD 是 DNSSEC 相關旗標（第 15 章）；最後 4 bits 的 **RCODE** 是結果代碼。後面四個計數欄位告訴解析程式每個區段有幾筆，因為 RR 長度不固定，必須依序一筆一筆讀。

| flag／欄位 | 位元數 | 查詢時 | 回應時 | 故事裡的意義 |
|---|---|---|---|---|
| QR | 1 | 0 | 1 | 區分查詢與回應 |
| Opcode | 4 | 0（QUERY） | 複製查詢的值 | 幾乎永遠是 0 |
| AA | 1 | 0 | 權威回答時為 1 | 判斷答案來自權威還是快取 |
| TC | 1 | 0 | 被截斷時為 1 | 看到它要改用 TCP 重問 |
| RD | 1 | stub 設 1 | 複製查詢的值 | 「請幫我問到底」 |
| RA | 1 | 0 | recursive resolver 設 1 | 「我提供遞迴服務」 |
| RCODE | 4 | 0 | 結果代碼 | 見下表 |

| RCODE | 名稱 | 意思 | 常見原因 |
|---|---|---|---|
| 0 | NOERROR | 成功；但 answer 可能是空的 | 名字存在。answer 為空時叫 NODATA：名字存在但沒有這個類型 |
| 1 | FORMERR | 查詢格式錯誤 | 自己組的封包有 bug |
| 2 | SERVFAIL | server 無法完成查詢 | 權威 server 都不回應、DNSSEC 驗證失敗、上游逾時 |
| 3 | NXDOMAIN | 名字不存在 | 打錯名字、record 還沒建、負面快取 |
| 5 | REFUSED | server 拒絕回答 | 問了不開放遞迴的 server，或問權威 server 不屬於它的 zone |

NOERROR 加上空的 answer 是很多人會看錯的情況：例如 `api.shengsheng.example` 只有 A record 沒有 AAAA，查 AAAA 會得到 NOERROR、ANCOUNT=0，這不是錯誤，而是「名字在，但沒有 IPv6 位址」。它和 NXDOMAIN 的差別，會影響負面快取與應用程式的行為。

Question 區段只有三個欄位：**QNAME**（名字的 wire format）、**QTYPE**（例如 A=1、AAAA=28）、**QCLASS**（IN=1）。名字在封包裡不是用點分隔的字串，而是「長度＋內容」的 label 串，最後以長度 0 的 root label 結尾。下面這段程式親手組出 header 和 question，印出每一個 byte：

```python
import struct

# 一個查詢 www.shengsheng.example 的 A 記錄、要求遞迴（RD=1）的 DNS 訊息
qid = 0x1A2B
qr, opcode, aa, tc, rd, ra, z, rcode = 0, 0, 0, 0, 1, 0, 0, 0
flags = (qr << 15) | (opcode << 11) | (aa << 10) | (tc << 9) | (rd << 8) \
        | (ra << 7) | (z << 4) | rcode
# 6 個 16-bit 欄位，網路位元組順序（big-endian，"!"）
header = struct.pack("!HHHHHH", qid, flags, 1, 0, 0, 0)

def encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")
        assert 0 < len(raw) <= 63, "label 長度必須是 1-63"
        out += bytes([len(raw)]) + raw
    return out + b"\x00"            # 長度 0 的 label 就是 root

qname = encode_name("www.shengsheng.example")
question = qname + struct.pack("!HH", 1, 1)   # QTYPE=A(1)、QCLASS=IN(1)
msg = header + question

print("flags 二進位:", format(flags, "016b"))
print("header  :", header.hex(" "))
print("qname   :", qname.hex(" "))
print("qtype/qc:", question[-4:].hex(" "))
print("總長度  :", len(msg), "bytes")
assert len(header) == 12 and flags == 0x0100
assert len(qname) == 1 + 3 + 1 + 10 + 1 + 7 + 1
```

```text
flags 二進位: 0000000100000000
header  : 1a 2b 01 00 00 01 00 00 00 00 00 00
qname   : 03 77 77 77 0a 73 68 65 6e 67 73 68 65 6e 67 07 65 78 61 6d 70 6c 65 00
qtype/qc: 00 01 00 01
總長度  : 40 bytes
```

輸出逐行看：flags 的二進位只有從左數第 8 位（RD）是 1，所以十六進位是 `01 00`。header 的 12 bytes 是 ID `1a 2b`、flags `01 00`、QDCOUNT `00 01`，其餘三個計數都是 0。qname 的第一個 byte `03` 是長度，後面接 `77 77 77`（`www`）；`0a` 是 10，後面 10 bytes 是 `shengsheng`；`07` 加上 `example`；最後的 `00` 是 root。點並不出現在封包裡，取而代之的是每個 label 前面的長度 byte。最後 4 bytes `00 01 00 01` 是 QTYPE=A、QCLASS=IN。整個查詢只有 40 bytes，一個 UDP 封包綽綽有餘，這也是 DNS 選 UDP 的原因之一。

回應裡的 RR 格式是：NAME、TYPE（2 bytes）、CLASS（2 bytes）、TTL（4 bytes，無號整數，單位秒）、RDLENGTH（2 bytes）、RDATA（RDLENGTH 個 bytes）。A 的 RDATA 是 4 bytes 位址，AAAA 是 16 bytes，CNAME 和 NS 的 RDATA 是另一個名字，TXT 是一個或多個「1 byte 長度＋最多 255 bytes 文字」的字串。

**Name compression（名稱壓縮）** 是讀 DNS 封包最容易卡住的地方。一個回應裡，同一個網域後綴會重複出現很多次：question 有 `www.shengsheng.example`，answer 的 owner name 又是同一個名字，CNAME 目標 `web.shengsheng.example` 也以 `shengsheng.example` 結尾。為了省空間，DNS 允許用 2 bytes 的**指標**取代「從這裡開始的剩餘名稱」：

```text
 一般 label：   ┌─┬─┬──────────────────────┐
               │0│0│ 長度 (6 bits, 1-63)  │ 後面接該長度的文字
               └─┴─┴──────────────────────┘
 壓縮指標：     ┌─┬─┬──────────────────────────────────────────────┐
               │1│1│ offset (14 bits)：從訊息開頭算起的位置          │  共 2 bytes
               └─┴─┴──────────────────────────────────────────────┘

 offset  12: 03 'www' 0a 'shengsheng' 07 'example' 00     ← question 的 QNAME
              ▲       ▲
              │       └── offset 16：從這裡開始就是 "shengsheng.example"
              └────────── offset 12
 answer 1 的 NAME:  c0 0c                → 指向 offset 12 = www.shengsheng.example
 CNAME 的 RDATA:    03 'web' c0 10       → "web" + 指向 offset 16 = web.shengsheng.example
```

上半部說明怎麼區分：長度 byte 的最高兩個 bit 正常一定是 00，因為 label 最長 63，用不到那兩個 bit；如果是 11，這個 byte 和下一個 byte 合起來就是指標，後 14 bits 是 offset。下半部是 14.10 節程式實際產生的回應：question 的名字從 offset 12 開始（緊接在 12 bytes 的 header 之後），所以 answer 的 NAME 只要寫 `c0 0c`；CNAME 目標寫出 `web` 這個 label 之後，剩下的 `shengsheng.example` 用 `c0 10` 指回 offset 16。名字可以是「幾個 label 加一個指標」，指標一定在結尾，而且讀到指標後要跳過去繼續讀，讀完再回到指標後面 2 bytes 的位置。解析器必須防範指標互相指成迴圈，這是很多 DNS 解析 bug 和安全問題的來源。

## 14.9 傳輸：UDP 53、截斷、TCP 與 EDNS(0)

DNS 傳統上走 **UDP port 53**。理由很直接：一次查詢通常只是一問一答，資料量小，UDP 不必像 TCP 那樣先做三向交握（第 10 章），一來一回就結束。代價是 UDP 不保證送達（第 9 章），所以 stub 和 recursive resolver 都要自己處理逾時重送，通常是等一段時間沒回應就重問，或改問下一台 server。

最初的規格把 UDP 上的 DNS 訊息限制在 512 bytes。回應超過時，server 只送出能放進去的部分，並把 header 的 **TC** 設為 1；client 看到 TC=1，就要改用 **TCP port 53** 重問一次。走 TCP 時，每個 DNS 訊息前面多一個 2 bytes 的長度欄位，因為 TCP 是 byte stream，沒有訊息邊界（第 11 章）。zone transfer（AXFR、IXFR，次要權威 server 從主要 server 同步整個 zone）也一律用 TCP。現代規格要求 DNS 實作必須支援 TCP，不能把 TCP 53 當成可有可無而在防火牆擋掉。

512 bytes 對今天的 DNS 太小了：IPv6 位址、多筆 record、DNSSEC 簽章都會讓回應變大。**EDNS(0)**（Extension Mechanisms for DNS）的做法是在 additional 區段放一筆特殊的 **OPT pseudo-RR**，它不是真的 record，而是借用 RR 的格式來攜帶擴充資訊，其中最重要的是「我能接收多大的 UDP 回應」。常見的建議值是 1232 bytes，目的是讓回應加上 IPv6 與 UDP header 後仍放得進最小 MTU 1280，避免 IP 分片（第 8 章）。分片的 UDP 封包容易被防火牆丟掉，也比較容易被偽造。

```text
 stub／resolver                           server
   │── query（EDNS: 我可收 1232 bytes）────►│
   │◄── response 1100 bytes（TC=0）─────────│   放得下：一次結束
   │                                       │
   │── query（EDNS: 1232）─────────────────►│
   │◄── response（TC=1，內容不完整）──────────│   放不下：截斷
   │══ TCP 三向交握（port 53）══════════════►│
   │── [2-byte 長度] query ────────────────►│
   │◄── [2-byte 長度] 完整 response ─────────│
```

這張時序圖分兩段。上半段是常態：client 用 EDNS 宣告可接收 1232 bytes，回應放得下就一次結束。下半段是回應太大：server 回一個 TC=1 的截斷回應，client 必須建立 TCP 連線重問，多付一次交握的 RTT。如果防火牆擋了 TCP 53，這種查詢就會一直失敗，表現成「某些名字偶爾解析不到」，很難查。

UDP 沒有連線，回應只靠 ID 和 port 配對，所以理論上別人可以偽造回應塞進 resolver 的快取，這叫 **cache poisoning**。基本的防禦是 ID 與來源 port 都要隨機，讓偽造者很難猜中；更完整的防禦（DNSSEC）和加密傳輸（DoT、DoH）都在第 15 章。本章的程式為了讓輸出固定，ID 用了固定值，真實的 client 必須用 `secrets` 之類的安全亂數產生 ID，並讓作業系統分配隨機的來源 port。

## 14.10 動手做：假的權威 DNS server、手組 client 與 TTL 快取

這一節把前面所有東西串起來。程式在 `127.0.0.1` 上用 port 0 開一個 UDP socket，扮演 `shengsheng.example` 的權威 server，zone 裡有 A、AAAA、CNAME、TXT 四種 record；client 不用任何 DNS 函式庫，自己用 `struct` 組出 header 與 question，解析回應時處理 name compression 指標；最後的 `StubResolver` 用模擬時鐘示範 TTL 快取：還沒過期就從快取回答，並回傳剩餘的 TTL。

server 端的 `handle()` 做三件事：讀出 question；如果問的名字有 CNAME，就在 zone 內把 CNAME 鏈跟到底，把每一段都放進 answer；最後決定 RCODE：名字不在 zone 裡回 NXDOMAIN（3），名字在但沒有這個類型就是 NOERROR 加空 answer。回應的 flags 設 QR=1、AA=1，並複製查詢的 RD。`Writer` 類別在寫名字時記住每個後綴的位置，重複出現就寫指標，和真實 server 的壓縮方式相同。

```python
import socket, struct, threading, ipaddress

A, NS, CNAME, SOA, TXT, AAAA = 1, 2, 5, 6, 16, 28
TYPE_NAME = {A: "A", CNAME: "CNAME", TXT: "TXT", AAAA: "AAAA"}
ZONE = {  # (name, type) -> [(ttl, rdata)]；假的 shengsheng.example zone
    ("shengsheng.example", A): [(300, "203.0.113.10")],
    ("shengsheng.example", TXT): [(3600, "shengsheng-verify=7f3a9c")],
    ("www.shengsheng.example", CNAME): [(300, "web.shengsheng.example")],
    ("web.shengsheng.example", A): [(300, "203.0.113.10"), (300, "203.0.113.11")],
    ("web.shengsheng.example", AAAA): [(300, "2001:db8:5::10")],
    ("api.shengsheng.example", A): [(60, "203.0.113.20")],
}
NAMES = {name for name, _ in ZONE}

class Writer:
    """組訊息時記住每個名稱後綴的位置，之後重複出現就寫 2-byte 指標。"""
    def __init__(self): self.buf, self.seen = bytearray(), {}
    def name(self, name):
        labels = name.rstrip(".").split(".")
        for i in range(len(labels)):
            suffix = ".".join(labels[i:]).lower()
            if suffix in self.seen:                      # 後綴出現過：指回去
                self.buf += struct.pack("!H", 0xC000 | self.seen[suffix]); return
            if len(self.buf) < 0x3FFF: self.seen[suffix] = len(self.buf)
            raw = labels[i].encode(); self.buf += bytes([len(raw)]) + raw
        self.buf.append(0)

def rdata(w, rtype, value):
    start = len(w.buf); w.buf += b"\0\0"                 # 先佔 RDLENGTH，寫完回填
    if rtype == A: w.buf += ipaddress.IPv4Address(value).packed
    elif rtype == AAAA: w.buf += ipaddress.IPv6Address(value).packed
    elif rtype == CNAME: w.name(value)
    elif rtype == TXT: raw = value.encode(); w.buf += bytes([len(raw)]) + raw
    struct.pack_into("!H", w.buf, start, len(w.buf) - start - 2)

def read_name(msg, off):
    labels, jumps, end = [], 0, None
    while True:
        n = msg[off]
        if n & 0xC0 == 0xC0:                              # 壓縮指標：前兩個 bit 是 11
            if end is None: end = off + 2
            off = struct.unpack_from("!H", msg, off)[0] & 0x3FFF
            jumps += 1; assert jumps < 20, "指標迴圈"
        elif n == 0:
            return ".".join(labels), (end if end is not None else off + 1)
        else:
            labels.append(msg[off + 1: off + 1 + n].decode()); off += 1 + n

def handle(query):
    qid, qflags = struct.unpack_from("!HH", query)
    qname, off = read_name(query, 12)
    qtype, _ = struct.unpack_from("!HH", query, off)
    qname = qname.lower(); answers, name = [], qname
    while (name, CNAME) in ZONE and qtype != CNAME:      # zone 內的 CNAME 一路跟下去
        answers += [(name, CNAME, *r) for r in ZONE[(name, CNAME)]]
        name = ZONE[(name, CNAME)][0][1]
    answers += [(name, qtype, *r) for r in ZONE.get((name, qtype), [])]
    rcode = 0 if qname in NAMES else 3                   # 3 = NXDOMAIN
    flags = 0x8000 | 0x0400 | (qflags & 0x0100) | rcode  # QR=1、AA=1、複製 RD
    w = Writer(); w.buf += struct.pack("!HHHHHH", qid, flags, 1, len(answers), 0, 0)
    w.name(qname); w.buf += struct.pack("!HH", qtype, 1)
    for rname, rtype, ttl, value in answers:
        w.name(rname); w.buf += struct.pack("!HHI", rtype, 1, ttl); rdata(w, rtype, value)
    return bytes(w.buf)

def parse_response(msg):
    qid, flags, qd, an, ns, ar = struct.unpack_from("!HHHHHH", msg)
    off = 12
    for _ in range(qd): _, off = read_name(msg, off); off += 4
    records = []
    for _ in range(an):
        name, off = read_name(msg, off)
        rtype, _cls, ttl, rdlen = struct.unpack_from("!HHIH", msg, off); off += 10
        raw = msg[off: off + rdlen]
        if rtype == A: value = str(ipaddress.IPv4Address(raw))
        elif rtype == AAAA: value = str(ipaddress.IPv6Address(raw))
        elif rtype == CNAME: value = read_name(msg, off)[0]   # rdata 內也可能有指標
        elif rtype == TXT: value = raw[1:1 + raw[0]].decode()
        else: value = raw.hex()
        records.append((name, TYPE_NAME.get(rtype, rtype), ttl, value)); off += rdlen
    return qid, flags, records

def query(server, name, qtype, qid):
    w = Writer(); w.buf += struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0)   # RD=1
    w.name(name); w.buf += struct.pack("!HH", qtype, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(2); s.sendto(bytes(w.buf), server)
        msg, _ = s.recvfrom(4096)
    rid, flags, records = parse_response(msg)
    assert rid == qid, "ID 不符，丟掉這個回應"
    return flags & 0xF, records, msg

class StubResolver:
    """最小的 stub resolver：問一台 server，答案依 TTL 放進快取。"""
    def __init__(self, server, clock):
        self.server, self.clock, self.cache, self.sent = server, clock, {}, 0
    def resolve(self, name, qtype):
        key, now = (name.lower(), qtype), self.clock()
        hit = self.cache.get(key)
        if hit and now < hit[0]:                          # 還沒過期：回剩餘 TTL
            return "cache", [(n, t, int(hit[0] - now), v) for n, t, _, v in hit[1]]
        self.sent += 1
        rcode, recs, _ = query(self.server, name, qtype, 0x3000 + self.sent)
        if rcode == 0 and recs:                           # 整組答案以最短 TTL 為準
            self.cache[key] = (now + min(r[2] for r in recs), recs)
        return "network", recs

srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); srv.bind(("127.0.0.1", 0))
srv.settimeout(0.1); stop = threading.Event()
def serve():
    while not stop.is_set():
        try: data, addr = srv.recvfrom(512)
        except socket.timeout: continue
        srv.sendto(handle(data), addr)
t = threading.Thread(target=serve); t.start()
server = srv.getsockname()
try:
    rcode, recs, raw = query(server, "www.shengsheng.example", A, 0x1A2B)
    print(f"www A -> rcode={rcode}，回應 {len(raw)} bytes")
    for r in recs: print("   ", r)
    print("    answer 區第一個 NAME 欄位:", raw[40:42].hex(" "), "（指向 offset 12）")
    assert raw[40:42] == b"\xc0\x0c" and recs[-1][3] == "203.0.113.11"
    print("    完整回應:")
    for i in range(0, len(raw), 16): print(f"    {i:04x}  {raw[i:i+16].hex(' ')}")
    for name, qt in [("www.shengsheng.example", AAAA), ("shengsheng.example", TXT),
                     ("api.shengsheng.example", AAAA), ("nope.shengsheng.example", A)]:
        rcode, recs, _ = query(server, name, qt, 0x2000 + qt)
        print(f"{name} {TYPE_NAME[qt]} -> rcode={rcode}，{len(recs)} 筆:", [r[3] for r in recs])
    now = [0.0]                                           # 模擬時鐘，不用真的等
    stub = StubResolver(server, lambda: now[0])
    for t_, name in [(0, "api"), (0, "www"), (30, "api"), (59, "api"), (60, "api"), (100, "www")]:
        now[0] = t_
        where, recs = stub.resolve(name + ".shengsheng.example", A)
        print(f"t={t_:>3}s {name:<3} {where:<7} TTL={recs[-1][2]:>3} -> {recs[-1][3]}")
    assert stub.sent == 3, stub.sent                       # api 兩次、www 一次
finally:
    stop.set(); t.join(); srv.close()
```

```text
www A -> rcode=0，回應 90 bytes
    ('www.shengsheng.example', 'CNAME', 300, 'web.shengsheng.example')
    ('web.shengsheng.example', 'A', 300, '203.0.113.10')
    ('web.shengsheng.example', 'A', 300, '203.0.113.11')
    answer 區第一個 NAME 欄位: c0 0c （指向 offset 12）
    完整回應:
    0000  1a 2b 85 00 00 01 00 03 00 00 00 00 03 77 77 77
    0010  0a 73 68 65 6e 67 73 68 65 6e 67 07 65 78 61 6d
    0020  70 6c 65 00 00 01 00 01 c0 0c 00 05 00 01 00 00
    0030  01 2c 00 06 03 77 65 62 c0 10 c0 34 00 01 00 01
    0040  00 00 01 2c 00 04 cb 00 71 0a c0 34 00 01 00 01
    0050  00 00 01 2c 00 04 cb 00 71 0b
www.shengsheng.example AAAA -> rcode=0，2 筆: ['web.shengsheng.example', '2001:db8:5::10']
shengsheng.example TXT -> rcode=0，1 筆: ['shengsheng-verify=7f3a9c']
api.shengsheng.example AAAA -> rcode=0，0 筆: []
nope.shengsheng.example A -> rcode=3，0 筆: []
t=  0s api network TTL= 60 -> 203.0.113.20
t=  0s www network TTL=300 -> 203.0.113.11
t= 30s api cache   TTL= 30 -> 203.0.113.20
t= 59s api cache   TTL=  1 -> 203.0.113.20
t= 60s api network TTL= 60 -> 203.0.113.20
t=100s www cache   TTL=200 -> 203.0.113.11
```

逐段解讀輸出：

1. 第一行：查 `www` 的 A 得到 rcode=0，回應 90 bytes。answer 有三筆：先是 `www` 的 CNAME 指向 `web`，再是 `web` 的兩筆 A record。server 自動把 zone 內的 CNAME 鏈跟到底，所以 client 一次就拿到最終位址；如果 CNAME 指向別的 zone，權威 server 只會回 CNAME，剩下的要靠 recursive resolver 重新解析，就像 14.5 節的 CDN 例子。
2. 「answer 區第一個 NAME 欄位: c0 0c」：offset 40 剛好是 12 bytes header 加 28 bytes question 之後，第一筆 answer 的名字被壓縮成指向 offset 12 的指標，也就是 question 裡的 `www.shengsheng.example`。
3. 完整回應的 hex dump 對照 14.8 節的圖：第一列 `1a 2b` 是我們送出的 ID，`85 00` 是 flags，二進位 `1000 0101 0000 0000`，依序是 QR=1、Opcode=0、AA=1、TC=0、RD=1、RA=0，RCODE=0。RA 是 0，因為這是權威 server，它不提供遞迴。接著 `00 01 00 03 00 00 00 00` 表示 1 個 question、3 個 answer。offset `0x28` 開始的 `c0 0c 00 05 00 01 00 00 01 2c 00 06` 依序是 NAME 指標、TYPE=5（CNAME）、CLASS=1、TTL=0x12c（300 秒）、RDLENGTH=6；RDATA `03 77 65 62 c0 10` 就是 `web` 加上指向 offset 16 的指標，只用 6 bytes 就表達了 `web.shengsheng.example`。後面兩筆 A record 的 NAME 是 `c0 34`，offset 0x34=52 正是 CNAME RDATA 裡 `web` 的位置，指標可以指向 RDATA 內部；RDATA `cb 00 71 0a` 就是 203.0.113.10。
4. 接下來四個查詢展示不同結果：`www` 的 AAAA 一樣先經過 CNAME；TXT 回傳驗證字串；`api` 的 AAAA 是 NOERROR 但 0 筆，也就是 NODATA；`nope` 不存在，rcode=3 是 NXDOMAIN。這兩種「沒有答案」在程式裡要分開處理。
5. 最後六行是 stub resolver 的快取。`api` 的 TTL 是 60：t=0 走網路；t=30 命中快取，回傳剩餘 TTL 30；t=59 剩 1 秒；t=60 剛好過期，再走一次網路，拿到新的 60。`www` 的三筆答案 TTL 都是 300，t=100 時剩 200。`assert stub.sent == 3` 確認六次解析只送出三個封包。

這個 stub resolver 刻意保持簡單，和真實實作有幾個差別值得記住：它以整組答案中最短的 TTL 作為快取期限，因為 CNAME 和 A 任一段過期，整個答案都可能不再正確；它沒有快取 NXDOMAIN 與 NODATA，真實的 resolver 會依 SOA 做負面快取；它沒有處理 TC 位元與 TCP fallback，也沒有在逾時後重送或換 server。14.14 節的練習會讓你補上其中幾項。

## 14.11 動手做：用純 Python 模擬 root → TLD → authoritative

上一節的 server 是權威 server，client 直接問它。真實世界裡，stub 問的是 recursive resolver，而 recursive resolver 要從 root 一路問下來。這段程式不開任何 socket，用字典模擬五台權威 server：root、`.example` TLD、`.test` TLD、聲聲 Live 的權威 server，以及 CDN 的權威 server。`ask()` 模擬一台權威 server 的行為：有答案就回答案，名字是 CNAME 就回 CNAME，屬於已授權出去的子 zone 就回 referral 加 glue，否則回 NXDOMAIN。`Recursive` 類別模擬 recursive resolver：從快取中找最接近的已知 zone，找不到就從 root hints 開始，並把每個 referral 記進快取。

```python
# 純 Python 模擬遞迴 resolver 的迭代查詢：root → TLD → authoritative。
# 伺服器位址都是文件用範例 IP，不是真實的 root／TLD server。
SERVERS = {
    "192.0.2.1": {"zone": ".", "records": {               # 模擬的 root server
        ("example", "NS"): ["a.nic.example"], ("a.nic.example", "A"): ["192.0.2.10"],
        ("test", "NS"): ["a.nic.test"], ("a.nic.test", "A"): ["192.0.2.20"]}},
    "192.0.2.10": {"zone": "example", "records": {        # .example TLD
        ("shengsheng.example", "NS"): ["ns1.shengsheng.example"],
        ("ns1.shengsheng.example", "A"): ["203.0.113.53"]}},          # glue
    "192.0.2.20": {"zone": "test", "records": {           # .test TLD
        ("cdnedge.test", "NS"): ["ns.cdnedge.test"], ("ns.cdnedge.test", "A"): ["198.51.100.60"]}},
    "203.0.113.53": {"zone": "shengsheng.example", "records": {
        ("www.shengsheng.example", "CNAME"): ["ss.cdnedge.test"],
        ("api.shengsheng.example", "A"): ["203.0.113.20"]}},
    "198.51.100.60": {"zone": "cdnedge.test", "records": {
        ("ss.cdnedge.test", "A"): ["198.51.100.7", "198.51.100.8"]}},
}
ROOT_HINTS = ["192.0.2.1"]                               # resolver 出廠就知道 root 在哪

def ask(ip, name, qtype):
    """一台權威 server 只回答自己知道的：答案、CNAME、referral 或 NXDOMAIN。"""
    recs = SERVERS[ip]["records"]
    if (name, qtype) in recs: return "ANSWER", recs[(name, qtype)]
    if (name, "CNAME") in recs: return "CNAME", recs[(name, "CNAME")]
    labels = name.split(".")
    for i in range(1, len(labels)):                      # 找最長的、已授權出去的祖先
        child = ".".join(labels[i:])
        if (child, "NS") in recs:
            ns = recs[(child, "NS")]
            glue = [addr for n in ns for addr in recs.get((n, "A"), [])]
            return "REFERRAL", (child, glue)
    return "NXDOMAIN", []

class Recursive:
    def __init__(self): self.ns_cache, self.sent = {}, 0   # zone -> 該 zone 的 server IP
    def closest(self, name):
        labels = name.split(".")
        for i in range(len(labels)):                      # 由長到短找快取過的 zone
            if (z := ".".join(labels[i:])) in self.ns_cache: return z, self.ns_cache[z]
        return ".", ROOT_HINTS
    def resolve(self, name, qtype="A", depth=0):
        assert depth < 8, "CNAME 鏈太長"
        zone, servers = self.closest(name)
        print(f"  [開始] {name} {qtype}，從 zone「{zone}」的 {servers[0]} 問起")
        while True:
            self.sent += 1
            kind, data = ask(servers[0], name, qtype)
            print(f"   #{self.sent} 問 {servers[0]:<13} -> {kind} {data}")
            if kind == "ANSWER": return data
            if kind == "NXDOMAIN": return []
            if kind == "CNAME": return self.resolve(data[0], qtype, depth + 1)  # 換名字重來
            zone, servers = data
            self.ns_cache[zone] = servers                 # 記住 referral，下次直接跳過

r = Recursive()
print("查詢 1：www.shengsheng.example")
print("  結果:", r.resolve("www.shengsheng.example"), f"（累計送出 {r.sent} 個查詢）")
first = r.sent
print("查詢 2：api.shengsheng.example")
print("  結果:", r.resolve("api.shengsheng.example"), f"（這次只送 {r.sent - first} 個）")
assert first == 6 and r.sent - first == 1
print("快取的 zone:", sorted(r.ns_cache))
```

```text
查詢 1：www.shengsheng.example
  [開始] www.shengsheng.example A，從 zone「.」的 192.0.2.1 問起
   #1 問 192.0.2.1     -> REFERRAL ('example', ['192.0.2.10'])
   #2 問 192.0.2.10    -> REFERRAL ('shengsheng.example', ['203.0.113.53'])
   #3 問 203.0.113.53  -> CNAME ['ss.cdnedge.test']
  [開始] ss.cdnedge.test A，從 zone「.」的 192.0.2.1 問起
   #4 問 192.0.2.1     -> REFERRAL ('test', ['192.0.2.20'])
   #5 問 192.0.2.20    -> REFERRAL ('cdnedge.test', ['198.51.100.60'])
   #6 問 198.51.100.60 -> ANSWER ['198.51.100.7', '198.51.100.8']
  結果: ['198.51.100.7', '198.51.100.8'] （累計送出 6 個查詢）
查詢 2：api.shengsheng.example
  [開始] api.shengsheng.example A，從 zone「shengsheng.example」的 203.0.113.53 問起
   #7 問 203.0.113.53  -> ANSWER ['203.0.113.20']
  結果: ['203.0.113.20'] （這次只送 1 個）
快取的 zone: ['cdnedge.test', 'example', 'shengsheng.example', 'test']
```

對照 14.5 節的時序圖逐行看：

1. 查詢 1 從 root（192.0.2.1）開始。#1 root 回 referral：`example` 歸 192.0.2.10 管；#2 TLD 再回 referral：`shengsheng.example` 歸 203.0.113.53 管，這個位址就是 glue，因為 `ns1.shengsheng.example` 本身就在它要負責的 zone 裡，沒有 glue 就找不到它。
2. #3 聲聲 Live 的權威 server 回 CNAME。名字換成 `ss.cdnedge.test`，它在不同的 TLD 下，resolver 的快取裡只有 `example` 和 `shengsheng.example`，沒有 `test` 相關的 zone，只好從 root 重新開始：#4、#5 是兩次 referral，#6 才拿到兩個 A record。第一次解析總共送出 6 個查詢。
3. 查詢 2 是 `api.shengsheng.example`。`closest()` 由長到短比對快取，找到 `shengsheng.example`，直接問 203.0.113.53，一個查詢就拿到答案。這就是 NS 快取的威力：熱門網域的 TLD 與 root 幾乎不會被反覆詢問。
4. 最後印出的快取裡有四個 zone，`test` 和 `cdnedge.test` 是追 CNAME 時順便學到的。

這個模擬省略了很多真實細節：NS 快取沒有 TTL、只用每個 zone 的第一台 server、沒有 QNAME minimisation、glue 缺漏時沒有另外去解析 NS 的位址。但骨架與真實 resolver 一致，也解釋了一個重要的效能事實：CNAME 指向另一個 TLD 的名字，冷快取時會讓解析多跑一整輪。

## 14.12 在工作上怎麼用

**情境一：後端搬遷，規劃一次不出事的 DNS 變更。** 回到故事，阿德事後替聲聲 Live 寫了一份 DNS 變更檢查清單：

1. 變更前至少一個「舊 TTL」的時間，把 TTL 調低。例如原本 3600，就在搬遷前一天把 `api` 的 TTL 改成 60。注意：調低 TTL 這個動作本身，也要等舊的 3600 秒過完才會到處生效。
2. 搬遷當下修改 record 值，新舊兩邊同時提供服務。
3. 用 `dig @權威server +norecurse` 確認權威 server 已經是新值，再用幾台不同的 recursive resolver 確認舊值逐漸消失。
4. 至少等「新 TTL＋監控上舊流量歸零」之後再關舊機器。有些 client 或應用程式不遵守 TTL，所以要看舊機器的實際流量，而不是只看時間。
5. 確認穩定後，把 TTL 調回平常的值，降低查詢量並讓快取能撐過權威 server 的短暫故障。

**情境二：用 `dig` 分辨問題在哪一層。** 遇到「我這邊查到的 IP 和你不一樣」時，依序問三個地方：

```bash
# 1. 直接問權威 server，不要遞迴：這是「真相」
dig @ns1.shengsheng.example api.shengsheng.example A +norecurse

# 2. 問自己用的 recursive resolver：看到的是快取，注意 TTL 是否在倒數
dig api.shengsheng.example A

# 3. 從 root 開始一步步追，檢查授權鏈是否正確
dig +trace www.shengsheng.example
```

下面是第 2 個指令的示意輸出（聲聲 Live 的名字是範例，實際執行不會有這個結果）：

```text
; <<>> DiG 9.18 <<>> api.shengsheng.example A
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4242
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232

;; QUESTION SECTION:
;api.shengsheng.example.        IN      A

;; ANSWER SECTION:
api.shengsheng.example. 2741    IN      A       203.0.113.20

;; Query time: 3 msec
;; SERVER: 10.20.0.2#53(10.20.0.2) (UDP)
```

把它和 14.8 節的 header 對起來讀：`status: NOERROR` 是 RCODE 0；`id: 4242` 是 ID；`flags: qr rd ra` 表示這是回應、有要求遞迴、server 提供遞迴，而且**沒有** `aa`，所以這是快取的答案。TTL 2741 比權威設定的 3600 小，表示這筆資料已在快取裡待了 859 秒，還要 2741 秒才會過期；如果權威 server 已改成新值，這台 resolver 背後的使用者還要等這麼久。`ADDITIONAL: 1` 是 OPT pseudo-RR，`udp: 1232` 是 EDNS 宣告的 UDP 大小。`Query time: 3 msec` 很短，也是命中快取的跡象；冷快取時通常要數十到數百毫秒。

**情境三：前端或 SRE 判斷「慢」是不是 DNS。** 用 `curl -w` 可以把 DNS 解析時間獨立出來：

```bash
curl -o /dev/null -s -w 'dns=%{time_namelookup}s connect=%{time_connect}s total=%{time_total}s\n' https://www.shengsheng.example/
```

`time_namelookup` 如果偶爾跳到幾百毫秒甚至數秒，通常代表冷快取加上長 CNAME 鏈、某台權威 server 不回應導致 resolver 逾時重試，或 UDP 封包遺失後等待重送。瀏覽器 DevTools 的 Network 面板裡，每個請求的 Timing 也有「DNS Lookup」一欄，可以看出哪些第三方網域在拖慢首次載入。

**情境四：新增驗證與政策 record 的檢查。** Rita 加 TXT 和 CAA 之前，先確認同一個名字沒有 CNAME（有 CNAME 就不能再加其他類型）；TXT 的值超過 255 bytes 時要拆成多個字串；加完後用 `dig shengsheng.example TXT +short` 與 `dig shengsheng.example CAA +short` 從外部確認，並記得驗證服務那端也有自己的 resolver 快取，剛加的 record 如果先前被查過而得到 NODATA，可能要等負面快取過期。

## 14.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 改了 record，部分使用者還連舊 IP | 舊答案還在各層快取裡，最長要等「改動時間＋舊 TTL」 | `dig @權威 +norecurse` 是新值，`dig` 公共 resolver 看到舊值且 TTL 在倒數 | 變更前先降 TTL；舊服務保留到舊流量歸零 |
| 新建的名字一直 NXDOMAIN | 建立前被查過，NXDOMAIN 被負面快取；或建在錯的 zone | 權威 server 查得到、resolver 查不到；看 authority 區段 SOA | 等負面快取過期；確認建在正確的 zone 與代管帳號 |
| 名字解析成 `web.shengsheng.example.shengsheng.example` | zone 檔裡 CNAME 目標沒寫結尾的點，被自動補上 zone 名 | `dig www.shengsheng.example CNAME` 看目標 | 目標寫成 FQDN（結尾加點），或依代管後台的格式輸入 |
| 加 TXT 或 MX 時後台報錯，或加了查不到 | 同名已有 CNAME，CNAME 不能和其他類型並存 | `dig 名字 CNAME` | 把 TXT／MX 放在沒有 CNAME 的名字，apex 改用 ALIAS 類方案（第 15 章） |
| 換了 DNS 代管後網域整個解析不到 | 註冊商那邊（上層 zone）的 NS 沒改，或 glue 還是舊位址 | `dig +trace` 看 TLD 給的 referral 指到哪 | 在註冊商更新 NS 與 glue；新舊代管並行一段時間 |
| 某些名字偶爾解析失敗，多半是回應很大的那些 | 回應超過 UDP 大小被截斷，TCP 53 被防火牆擋 | `dig +tcp 名字` 失敗、`dig +notcp` 得到 TC 旗標 | 開放 TCP 53；精簡回應；EDNS 大小設 1232 |
| 查 AAAA 得到 NOERROR 但沒有答案，程式卻當成錯誤 | 把 NODATA 誤當失敗，或以為沒有 AAAA 就是網域不存在 | 看 RCODE 與 ANCOUNT | 程式分開處理 NXDOMAIN 與 NODATA；client 應同時查 A 與 AAAA |
| 服務改 IP 後，某個長時間執行的程式一直連舊位址 | 程式啟動時解析一次就永久保存，或 runtime 有自己的長快取 | 重啟後恢復正常；看程式或 library 的 DNS 快取設定 | 依 TTL 重新解析，或設定 runtime 的 DNS 快取上限（第 16 章） |

除錯的大方向是「由近而遠、由快取到權威」：先看應用程式和 OS 快取，再看 recursive resolver，再直接問權威 server，最後用 `dig +trace` 檢查授權鏈。每一步都記下 RCODE、AA 旗標與 TTL，這三個欄位通常就足以判斷問題在哪一層。SERVFAIL 是最需要往下追的結果，它代表 resolver 自己也拿不到可信的答案，可能是權威 server 全部不回應、授權鏈錯誤，或 DNSSEC 驗證失敗；第 15 章會專門處理 SERVFAIL 與各種進階故障。

## 14.14 動手練習

1. **加上 MX 與 SOA**：在 14.10 節的 zone 加入 `shengsheng.example` 的 MX（RDATA 是 2 bytes preference 加一個名字）與 SOA，並讓 NXDOMAIN 回應在 authority 區段附上 SOA。**驗證**：client 解析 MX 時能印出 `10 mail.shengsheng.example`；NXDOMAIN 回應的 NSCOUNT 為 1。提示：MX 的目標名字也可以壓縮，解析時記得 preference 之後才是名字。
2. **負面快取**：延伸 `StubResolver`，收到 NXDOMAIN 時用 SOA 的 TTL 與 minimum 欄位中較小的值作為負面快取時間。**驗證**：用模擬時鐘證明在負面快取期限內，即使 zone 已加上該名字，stub 仍回 NXDOMAIN 且不送封包；過期後才看到新 record。這正是 14.13 節第二列的現象。
3. **截斷與 TCP fallback**：讓 server 在回應超過 100 bytes 時只回 header 與 question 並設 TC=1，同時開一個 TCP 版本的 server（訊息前加 2 bytes 長度）。client 看到 TC=1 就改用 TCP 重問。**驗證**：`www` 的 A 查詢（90 bytes）走 UDP，在 zone 裡多加幾筆 A 讓回應變大後改走 TCP，兩者解析結果一致。
4. **用 dig 觀察真實 DNS**：在有網路的環境，對你公司或個人擁有的網域執行 `dig +trace`、`dig +norecurse @某個權威server`，以及連續兩次 `dig` 同一個名字。**觀察重點**：trace 裡每一站的 referral 與 glue；權威回應有 `aa`、recursive 回應沒有；第二次查詢的 TTL 變小、Query time 變短。
5. **用 Wireshark 或 tcpdump 看封包**：在本機執行 14.10 節的程式時，用 `sudo tcpdump -i lo0 -X udp`（Linux 為 `-i lo`）抓 loopback 上的封包，或用 Wireshark 以 `dns` 為顯示過濾條件。**驗證**：Wireshark 會把封包解碼成 DNS，對照 14.8 節的 header 圖找出 ID、flags 與壓縮指標；注意 port 不是 53，Wireshark 可能需要用「Decode As」指定為 DNS。
6. **手算壓縮效益**：如果不做 name compression，14.10 節 `www` 的回應會是幾 bytes？**答案要點**：三筆 answer 的 NAME 各從 2 bytes 變成完整名字（`www...` 24 bytes、`web...` 24 bytes 兩次），CNAME RDATA 從 6 bytes 變成 24 bytes，總共多出 22＋22＋22＋18＝84 bytes，回應會從 90 變成 174 bytes。

## 本章重點整理

- DNS 是把名字與位址分開的間接層，以階層式命名、分散授權與大量快取三個設計，支撐網際網路規模的名稱查詢。
- 網域名稱由右往左分層：root、TLD、組織網域；zone 是實際的管理單位，上層 zone 用 NS record 把子樹授權出去。
- stub resolver 只會把問題交出去；recursive resolver 從 root 開始迭代查詢並快取結果；authoritative server 只回答自己 zone 的資料或給 referral。
- 一次解析是「stub 對 recursive 的一次遞迴查詢，包著 recursive 對各層權威 server 的多次迭代查詢」；glue record 解決 NS 名稱位於自身 zone 內的雞生蛋問題。
- CNAME 會讓 resolver 以新名字重新解析，指向其他 TLD 時冷快取可能要再從 root 問起；有 CNAME 的名字不能有其他類型的 record，所以 apex 不能設 CNAME。
- 常用 record：A／AAAA 放位址，CNAME 是別名，MX 收信，TXT 放驗證與政策，NS 與 SOA 描述 zone，SRV 指出服務的主機與 port，CAA 限制 CA，HTTPS／SVCB 預告協定與參數。
- TTL 決定答案可以被快取多久；權威 server 改了資料不會通知任何快取，最壞情況要等「改動時間＋舊 TTL」，所謂「生效」其實是各處快取陸續過期。
- 搬遷前先把 TTL 調低並等舊 TTL 過完，改值後保留舊服務直到實際流量歸零，再把 TTL 調回來。
- DNS 訊息是 12 bytes header 加 question、answer、authority、additional 四個區段；header 裡的 ID、QR、AA、TC、RD、RA 與 RCODE 是除錯時最常看的欄位。
- NOERROR 加上空 answer（NODATA）與 NXDOMAIN 是兩種不同的「沒有答案」，程式與快取必須分開處理。
- 名字在封包裡是「長度＋label」串並以 0 結尾；name compression 用最高兩 bit 為 11 的 2 bytes 指標指回先前出現的後綴，解析時要防指標迴圈。
- DNS 主要走 UDP 53；回應被截斷（TC=1）時改用 TCP 53，EDNS(0) 的 OPT pseudo-RR 宣告可接收的 UDP 大小，常見建議值是 1232 bytes。
- 用 `dig @權威 +norecurse` 看真相、用 `dig` 看快取、用 `dig +trace` 檢查授權鏈，並從 RCODE、AA 旗標與 TTL 判斷問題在哪一層。

## 延伸問答

> [!question]- Q1. recursive resolver 和 authoritative server 有什麼不同？為什麼一台 server 最好不要同時扮演兩種角色？
> authoritative server 是某個 zone 的資料來源，只回答自己 zone 內的資料或給 referral，回應帶 AA=1，不會替別人去問；recursive resolver 替 client 跑腿，從 root 迭代查詢到答案，並把結果快取，回應帶 RA=1，答案通常 AA=0。兩者的信任方向相反：權威 server 面對整個網際網路提供自己的資料，recursive resolver 只該服務自己的使用者。
>
> 混在一起會出問題。對外開放遞迴的 server（open resolver）會被拿來做放大攻擊，也更容易被 cache poisoning；而權威資料和快取資料混在同一份記憶體裡，除錯時很難判斷答案從哪來。所以實務上權威 server 關閉遞迴（對非自己 zone 的問題回 REFUSED），recursive resolver 只允許內部網段使用。

> [!question]- Q2. 你在 production 用 `dig` 查 `api.shengsheng.example`，連續三次看到的 TTL 是 2741、2738、2735，而權威 server 的設定是 3600。這代表什麼？
> TTL 在倒數，代表這三次都命中同一台 recursive resolver 的快取，答案是在大約 859 秒前從權威 server 拿到的，還要大約 2741 秒才會過期。`dig` 的 flags 裡應該沒有 `aa`，Query time 也會很短，這兩點都能佐證是快取。
>
> 判斷上的意義是：如果權威 server 剛改了這筆 record，這台 resolver 背後的使用者還要再等 45 分鐘左右才會看到新值，這期間舊服務不能下線。要確認權威端是否已更新，應該用 `dig @權威server +norecurse` 直接問，看到 TTL 固定為 3600 且有 `aa` 才是真相。若三次的 TTL 不是遞減而是跳動，可能是背後有多台 resolver 做負載分散，各自有不同的快取。

> [!question]- Q3. 行銷希望 `shengsheng.example`（不帶 www）也指到 CDN，CDN 廠商說「設 CNAME 到 ss.cdnedge.test」。為什麼做不到？有什麼方向？
> 規格規定有 CNAME 的名字不能再有其他類型的 record，因為 CNAME 的語意是「這個名字的一切都去問另一個名字」。而 zone 的 apex 一定要有 SOA 和 NS，否則 zone 不成立，所以 apex 和 CNAME 必然衝突。就算某些代管後台讓你存進去，也可能讓 NS、MX、TXT 查詢出現不可預期的結果，郵件與網域驗證都可能壞掉。
>
> 可行的方向有：DNS 代管服務提供的 ALIAS 或 CNAME flattening（權威 server 自己去解析目標，再以 A／AAAA 回答）；把 apex 用 HTTP redirect 導到 `www`；或使用 HTTPS record 的 AliasMode，讓支援的 client 跳到 CDN 的名字。各方案的取捨，例如 GeoDNS 精準度與 TTL 行為，第 15 章會詳細比較。

> [!question]- Q4. 手算：一個查詢 `api.shengsheng.example` AAAA 的 DNS 訊息有幾 bytes？如果回應帶一筆 AAAA answer 並使用壓縮，回應又是幾 bytes？
> 查詢：header 12 bytes；QNAME 是 `03 api 0a shengsheng 07 example 00`，即 1＋3＋1＋10＋1＋7＋1＝24 bytes；QTYPE 與 QCLASS 各 2 bytes。合計 12＋24＋4＝40 bytes。若加上 EDNS 的 OPT pseudo-RR，會再多 11 bytes（名稱 1 byte 的 root、TYPE、CLASS、TTL、RDLENGTH 共 10 bytes），變成 51 bytes。
>
> 回應：header 與 question 一樣是 40 bytes。answer 的 NAME 用指標 `c0 0c` 是 2 bytes，TYPE、CLASS、TTL、RDLENGTH 共 10 bytes，AAAA 的 RDATA 是 16 bytes，所以一筆 answer 是 28 bytes，回應合計 68 bytes。若不壓縮，NAME 要寫完整的 24 bytes，回應就是 90 bytes。這也說明了為什麼查詢與典型回應都遠小於 512 bytes，適合 UDP。

> [!question]- Q5. NXDOMAIN 和「NOERROR 但 answer 為空」差在哪裡？程式應該怎麼分別處理？
> NXDOMAIN（RCODE 3）表示這個名字本身不存在，任何類型都查不到；NOERROR 加空 answer 叫 NODATA，表示名字存在，只是沒有你問的類型，例如 `api` 有 A 但沒有 AAAA。兩者在回應裡都可能附上 SOA，讓 resolver 做負面快取，但意義不同：NXDOMAIN 會讓 resolver 知道這個名字以下都不存在，NODATA 只對那一個類型有效。
>
> 程式上，NODATA 通常是正常狀況：client 同時查 A 與 AAAA，其中一個為空就用另一個，不應該報錯或重試。NXDOMAIN 則多半代表設定錯誤或打錯字，應該記錄完整名字方便追查，也要小心 search domain 造成的多次查詢（第 16 章）。把兩者混成「解析失敗」，會在 IPv6 不完整的環境裡製造大量誤報，或讓重試邏輯對著根本不存在的名字狂打。

> [!question]- Q6. 面試題：glue record 是什麼？什麼情況下一定要有它？
> glue record 是上層 zone 在做 referral 時，順便附上的 NS 主機位址，放在回應的 additional 區段。之所以需要它，是因為 NS record 只給名字，resolver 還要知道 IP 才能連過去。當 NS 名稱位於它所負責的 zone 內部時，例如 `shengsheng.example` 的 NS 是 `ns1.shengsheng.example`，要查 `ns1` 的位址就得先問 `shengsheng.example` 的權威 server，而那正是我們還不知道位址的 server，形成循環。
>
> 這種「in-bailiwick」的情況一定要在上層放 glue，通常在註冊商設定 NS 時一併提供 IP。如果 NS 名稱在別的網域，例如 `ns1.dnshost.example.net`，resolver 可以另外解析它，不需要 glue，但會多幾次查詢。換 DNS 代管或改權威 server IP 時忘了更新 glue，是「整個網域突然解析不到」的經典原因，用 `dig +trace` 看 TLD 給的 additional 區段就能確認。

> [!question]- Q7. 為什麼 DNS 主要用 UDP？什麼時候一定要用 TCP？只開放 UDP 53 的防火牆會造成什麼問題？
> 典型的 DNS 查詢只是一問一答，資料量在一個封包以內。用 UDP 不需要三向交握，一個 RTT 就結束，server 也不必為每個 client 維護連線狀態，能以很少的資源服務大量查詢；遺失的封包由 client 逾時重送處理即可。這些特性讓 UDP 非常適合 DNS。
>
> 需要 TCP 的情況有：回應超過 UDP 大小被截斷（TC=1）時改用 TCP 重問；zone transfer；以及 DoT 等建立在 TCP 上的加密傳輸。只開 UDP 53 的防火牆，平常看起來一切正常，但遇到回應較大的名字，例如很多筆 record、長 TXT、DNSSEC 簽章，就會出現間歇性的解析失敗，因為 client 拿到截斷的回應卻無法用 TCP 重問。現代規格要求 DNS 實作支援 TCP，防火牆規則應該同時開放 UDP 與 TCP 53。

> [!question]- Q8. 設計取捨：聲聲 Live 的 `api` 要用多長的 TTL？平常、搬遷前後、災難切換各怎麼考慮？
> TTL 決定兩件事：變更多快被看見，以及權威 server 故障時快取能撐多久。短 TTL 讓切換快，但 recursive resolver 會頻繁回來問，查詢量與費用上升，權威 server 或代管服務一出問題，使用者很快就解析不到；長 TTL 剛好相反。對 `api` 這種前面有 LB、IP 不常變的名字，平常用 300 到 3600 秒是常見的折衷。
>
> 搬遷前，至少提前一個舊 TTL 的時間把 TTL 降到 60 左右，搬完確認穩定再調回。若需要靠 DNS 做災難切換，TTL 就必須常態維持較短，並接受較高的查詢量；同時要知道部分 resolver 或應用程式不完全遵守 TTL，所以 DNS 切換的實際收斂時間要看流量監控，而不是只看 TTL。更好的做法往往是讓 IP 本身不變，例如 anycast 或 LB 的固定位址，把切換放在 LB 後面，DNS 只負責粗粒度的指向。

## 延伸閱讀

- RFC 1034〈Domain Names - Concepts and Facilities〉
- RFC 1035〈Domain Names - Implementation and Specification〉
- RFC 9499〈DNS Terminology〉
- RFC 6891〈Extension Mechanisms for DNS (EDNS(0))〉
- RFC 7766〈DNS Transport over TCP - Implementation Requirements〉
- RFC 2308〈Negative Caching of DNS Queries (DNS NCACHE)〉
- RFC 9460〈Service Binding and Parameter Specification via the DNS (SVCB and HTTPS Resource Records)〉
- Cricket Liu、Paul Albitz《DNS and BIND》（O'Reilly）
