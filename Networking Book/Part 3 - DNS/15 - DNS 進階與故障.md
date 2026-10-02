---
chapter: 15
title: DNS 進階：負載、安全與常見故障
part: 3
---

# 第 15 章　DNS 進階：負載、安全與常見故障

> [!abstract] 本章地圖
> **核心問題**：DNS 的答案會被很多層快取記住、可能被竄改、也能拿來分流，改一筆紀錄時要怎麼讓全世界「安全又準時」地看到新答案？
>
> **你會學到**：
> - 解釋一筆紀錄被哪些快取層記住，規劃「先降 TTL、再搬遷、最後關舊節點」的換 IP 流程，並估算最壞情況要等多久
> - 分辨 NXDOMAIN 與 NODATA，從 SOA 算出負面快取會維持多久
> - 說明 CNAME 為什麼不能放在 apex，比較 ALIAS／flattening 與 HTTPS record 的 AliasMode
> - 設計 weighted、GeoDNS 與 health check 的 DNS 分流，知道它們的極限在哪裡
> - 說清楚 DNSSEC 的信任鏈（DNSKEY、RRSIG、DS）與 DoT／DoH 各自保護哪一段
> - 用 dig 判斷 NXDOMAIN、SERVFAIL 與「換了紀錄後還連到舊端點」的根因
>
> **前置知識**：第 14 章（DNS 階層、遞迴查詢、record types、TTL、訊息格式）；第 17 章的 hash 與數位簽章概念會在 DNSSEC 一節用到，先讀過更好，沒讀也能跟上。

## 15.1 故事：換了 CDN，為什麼還有人連到舊的 edge？

第 14 章那次 API 搬遷之後，團隊記住了一條規則：「改紀錄之前先降 TTL。」這個月輪到網站本身換 CDN 供應商。`www.shengsheng.example` 目前 CNAME 到舊 CDN 的 `ss.cdnedge.test`（edge 位址 198.51.100.7、198.51.100.8），這家 CDN 在亞洲的表現不如預期，團隊決定改用另一家，把 `www` 改成 CNAME 到新 CDN 給的主機名稱 `ss.newedge.test`，它會解析到新 CDN 分配給聲聲 Live 的 edge 位址 203.0.113.10、203.0.113.11。週五晚上九點五十分，小晴先把 `www` 那筆 CNAME 的 TTL 從 86400 降到 300，等了十分鐘，確定已經超過新的 TTL，十點整才把目標改成新 CDN，自己用 `dig` 查了一下，看到的已經是新答案。十一點，團隊照計畫在舊 CDN 的後台停用了聲聲 Live 的服務設定，舊 edge 從此對 `www.shengsheng.example` 的請求一律回錯誤。

週六早上，客服收到一連串回報：有學生打開網站一直轉圈或看到錯誤頁，有老師說課程頁的圖片與講義下載不了，但同一個城市的另一位學生完全正常。小晴被拉進事故頻道，第一反應是：「這次我有先降 TTL 啊，而且我這邊查到的是新 CDN。」阿德看了變更紀錄，指出問題：「你降 TTL 的時候，各地 resolver 手上拿的還是 TTL 86400 的那一份。降 TTL 這個動作本身，也要等舊的 TTL 過期才會被看見；你只等了十分鐘，等於沒降。」這筆 CNAME 是第 14 章那週接上舊 CDN 時照廠商文件的範例填的，TTL 86400，當時沒人想過這麼快就會換供應商。第 14 章的教訓是「TTL 太長、舊機器關太早」；這次團隊記得降 TTL，卻栽在另一種問題上：降得太晚，而且舊 CDN 停得太早。

同一天還冒出另外三件事。Joe 前一天先用 `curl` 試了新的子網域 `classroom-v2.shengsheng.example`，那時紀錄還沒建立；紀錄建好後，Joe 的筆電仍然回報「找不到主機」將近一小時。公司辦公室裡的同事全部連到舊 CDN，因為內網有一份只給辦公室用的 DNS zone，裡面的 `www` 還指著舊供應商，沒人記得要一起改。再來是行銷同事想讓 `shengsheng.example`（沒有 www 的裸網域）也直接 CNAME 到新 CDN 的主機名稱，DNS 供應商的後台卻拒絕儲存。

事後檢討會上，Rita 補了一句：「我們之後要開 DNSSEC。到時候換 DNS 供應商，如果忘了更新上層的 DS 紀錄，整個網域會對所有驗證 DNSSEC 的使用者直接消失。」小晴這才意識到，第 14 章學的「名字換 IP」只是 DNS 的骨架，真正在 production 出事的，都是快取、負面快取、CNAME 的規則、分流策略與信任鏈這些細節。本章就從這次換 CDN 的事故出發，一層一層拆開。

## 15.2 快取是一層一層的：DNS 沒有「傳播」

很多人說「DNS 要傳播 24 到 48 小時」，這個說法讓人以為新答案是從權威伺服器一路推送出去的。實際上 DNS 沒有推播機制：權威伺服器改了紀錄之後，什麼都不會主動通知各地的 resolver。新答案之所以「慢慢生效」，是因為世界上無數個快取各自拿著舊答案，要等到自己手上那份的 TTL 倒數到零，下一次有人查詢時才會回頭去問權威伺服器。所以正確的心智模型是**快取過期**，不是傳播。

**快取層**指的是查詢路徑上每一個會把答案記下來、在 TTL 內直接回覆的元件。以聲聲 Live 的學生為例，一次查詢可能經過瀏覽器自己的 DNS 快取、作業系統的 stub resolver 快取、家用路由器內建的轉送器、ISP 或公共 recursive resolver 的快取，最後才到權威伺服器。下圖是這條路徑：

```text
 學生的瀏覽器        作業系統            家用路由器         ISP／公共 resolver        權威伺服器
 ┌──────────┐    ┌──────────┐     ┌──────────┐      ┌──────────────┐      ┌──────────────┐
 │ 瀏覽器快取 │───►│ stub 快取 │───►│ 轉送器快取 │────►│ recursive 快取 │────►│ shengsheng.  │
 │ （短）     │    │（依 OS）  │     │（依韌體）  │      │（主要的一層） │      │ example zone │
 └──────────┘    └──────────┘     └──────────┘      └──────────────┘      └──────────────┘
      ▲                                                     │
      │          每一層都把「剩餘 TTL」往下傳                  │ TTL=86400 時，這一層最多
      └─────────────────────────────────────────────────────┘ 會把舊答案留一整天

 另外兩種不在這條路上、但同樣讓人連到舊 IP 的東西：
   (1) 程式自己快取 IP（某些語言 runtime、連線池、SDK）
   (2) 已經建立的長連線（keep-alive、WebSocket）根本不會重新查 DNS
```

逐步看這張圖。第一，recursive resolver 是最重要的一層，它服務成千上萬個使用者，熱門名稱幾乎永遠在它的快取裡。第二，守規矩的快取會把**剩餘 TTL** 往下傳：resolver 在快取 1000 秒後回答 client，給的 TTL 是 86400 − 1000 = 85400，所以下游各層的過期時刻會和 resolver 對齊，不會疊加變更長。第三，真正讓時間拉長的是「不守規矩」的元件：有些 resolver 會設定 TTL 下限或上限，有些程式拿到 IP 後自己記住很久。第四，圖的最下方提醒一件常被忽略的事：已經建立好的 TCP 連線不會因為 DNS 改了就斷開，已經開著聲聲 Live 頁面的瀏覽器，會沿用連到舊 CDN edge 的 HTTP/2 連線（教室的 WebSocket 也一樣），直到連線斷開、重新建立時才會再查 DNS。

各層的行為差異很大，下表整理誰控制它、怎麼清除：

| 快取層 | 誰控制 | 是否遵守 TTL | 怎麼清除或觀察 |
|---|---|---|---|
| 瀏覽器內部快取 | 瀏覽器 | 大致遵守，另有自己的上限 | Chromium 系可在內部的 net-internals 頁面清除；重開瀏覽器 |
| 作業系統 stub 快取 | OS（systemd-resolved、mDNSResponder 等） | 遵守 | `resolvectl flush-caches`（Linux）、macOS 用 `dscacheutil -flushcache` 搭配重啟 mDNSResponder |
| 家用路由器轉送器 | 路由器韌體 | 依實作而定 | 重開路由器；通常無法觀察 |
| ISP／公共 recursive resolver | ISP 或 resolver 營運者 | 多數遵守，可能有上下限 | 無法替別人清除；部分公共 resolver 提供清除單一名稱的網頁工具 |
| 程式與 runtime 內的快取 | 你的程式或語言 runtime | 依 runtime 設定（第 16 章） | 調整 runtime 設定、重啟程序 |
| 既有長連線 | 應用程式 | 與 DNS 無關 | 讓舊節點主動優雅關閉連線，迫使 client 重連 |

> [!warning] 常見誤解
> 「我這邊 `dig` 查到新 IP，所以 DNS 已經生效了。」你查到的只是**你的** resolver 剛好回源過。另一個 ISP 的 resolver 可能在你改紀錄前一分鐘才快取了舊答案，接下來還會再用將近 TTL 這麼久。要判斷「最壞還要多久」，看的是**改之前**那筆紀錄的 TTL，不是改之後的。

那麼，權威伺服器自己會不會也慢？大型 DNS 供應商通常有很多台分散各地的權威伺服器（常搭配第 6 章的 anycast），自建的則常用一台 primary 加多台 secondary。primary 改了 zone 之後，會遞增 SOA 的 serial 並送出 NOTIFY，secondary 再用 zone transfer（完整的 AXFR 或增量的 IXFR）同步。若 NOTIFY 被防火牆擋掉，secondary 就要等 SOA 的 refresh 計時器到期才會同步，於是不同權威伺服器在一段時間內會回不同答案。用 `dig @每一台權威伺服器 SOA` 比對 serial，是確認這一層有沒有到位的標準動作。

## 15.3 TTL 策略：搬遷前提早降 TTL

知道了「舊答案最多活一個舊 TTL」，搬遷策略就呼之欲出：如果 TTL 是 86400，你要等一整天才能確定所有人都換到新 IP；但如果在搬遷**之前**先把 TTL 降到 300，並等待至少一個舊 TTL 讓全世界的快取都換成「TTL 300 的版本」，那麼真正改 IP 的時候，最壞只要等 5 分鐘。這個做法的關鍵在於降 TTL 本身也要等快取過期才會生效，所以必須提早做。

下面是聲聲 Live 事後重新規劃的時間軸（T 是切換 IP 的時刻）：

```text
 時間 ─────────────────────────────────────────────────────────────────────────►
  T-48h            T-24h                T             T+1h            T+24h      T+7d
   │                 │                  │               │                │          │
   ▼                 ▼                  ▼               ▼                ▼          ▼
 TTL 86400→300    最後一份 TTL=86400    www 的 CNAME    檢查舊 CDN 流量  舊 CDN 流量≈0   TTL 調回
 （只改 TTL）      的快取到期          改指新 CDN      只剩長連線與    才停用舊 CDN    3600 或更高
                  之後所有快取都是                      不守規的快取
                  TTL=300 的版本
 ├── 等至少一個舊 TTL ──┤        ├─ 最壞 5 分鐘 ─┤    ├──── 新舊兩邊同時服務 ────┤
```

逐步解說：第一步在 T-48h 只改 TTL、不改 IP，這樣即使出錯也沒有影響。第二步等待至少一個舊 TTL（這裡是 24 小時，多留一天緩衝），讓每個快取都至少回源一次、拿到 TTL=300 的版本；小晴這次只等了十分鐘，缺的就是這一步。第三步在 T 改紀錄（這次是把 `www` 的 CNAME 改指新 CDN），守規矩的快取最多 300 秒後就會改答新答案。第四步是事故當天同樣漏掉的：**舊端點不能馬上停**。即使 DNS 都換好了，還有設定 TTL 下限的 resolver、自己快取 IP 的程式，以及已經建立的長連線，要看著舊 CDN（或舊 LB）的連線數與請求數降到接近零才停用。最後再把 TTL 調回較高的值，降低查詢量。

TTL 不是越低越好。低 TTL 讓變更生效快、故障切換快，代價是 resolver 更常回源：權威伺服器的查詢量增加，使用者也更常遇到快取 miss，多一次往返的解析延遲。更重要的是，低 TTL 讓你更依賴權威 DNS 本身的可用性：2016 年 10 月 DNS 供應商 Dyn 遭到大規模 DDoS 時，TTL 很短的網站幾乎立刻無法解析，TTL 較長的網站則靠著各地快取多撐了一段時間。下表是常見的選擇：

| 紀錄用途 | 常見 TTL | 理由 | 取捨 |
|---|---|---|---|
| 穩定的 NS、MX、驗證用 TXT | 3600–86400 秒 | 很少變更，查詢量低 | 真要改時需提早規劃 |
| 網站與 API 的 A／AAAA | 300–3600 秒 | 兼顧變更速度與快取命中 | 搬遷前仍建議先降 |
| 搬遷或故障切換中的紀錄 | 30–300 秒 | 要快速生效 | 回源多、更依賴權威 DNS 可用性 |
| 由 health check 動態調整的紀錄 | 30–60 秒 | 故障節點要快速被移除 | 低於 30 秒時，部分 resolver 會套用自己的下限 |
| NS 與 DS 這類委派紀錄 | 依上層 registry 而定 | 父區 TTL 由 TLD 決定，你無法自己縮短 | 換 DNS 供應商時要以上層 TTL 規劃 |

> [!tip]
> 降 TTL 時也要記得 NS 紀錄。換 DNS 供應商時，父區（例如 TLD）的 NS 委派有自己的 TTL，通常是一到兩天，你無法調整。這段期間新舊兩家供應商的 zone 內容必須完全一致，兩邊都要能正確回答。

## 15.4 Negative caching：「不存在」也會被快取

Joe 的筆電為什麼在紀錄建好之後，還一直說找不到 `classroom-v2`？因為「這個名字不存在」本身也是一個答案，也會被快取。如果 resolver 每次遇到不存在的名字都回頭問權威伺服器，打錯字的流量、掃描器與設定錯誤的程式就會不斷打爆權威端。所以 DNS 定義了 **negative caching（負面快取）**：把「不存在」的結果也記住一段時間。例子：某支 app 每秒查一次拼錯的 `api.shengsheng.exmaple`，有了負面快取，resolver 只需要每隔一段時間問一次上層。

「不存在」有兩種，要先分清楚。**NXDOMAIN**（rcode 3）表示這個名稱底下什麼紀錄都沒有，例如還沒建立的 `classroom-v2.shengsheng.example`。**NODATA** 則是名稱存在、但沒有你問的 type：rcode 是 NOERROR（0），answer section 卻是空的，例如直播 ingest `live.shengsheng.example` 只有 A 紀錄、沒有 AAAA，你問 AAAA 就會得到 NODATA。兩者都會在 authority section 附上該 zone 的 SOA 紀錄，resolver 靠它決定負面快取要記多久。

依照負面快取的規格（RFC 2308），負面答案的 TTL 取「SOA 紀錄本身的 TTL」與「SOA 的 MINIMUM 欄位」兩者的較小值。MINIMUM 這個欄位名稱是歷史遺留，早期另有用途，現在的意義就是負面快取時間。SOA 的 RDATA 布局如下：

```text
 SOA RDATA（接在 RR 的 name、type=6、class、TTL、RDLENGTH 之後）
 ┌───────────────────────────────────────────────┐
 │ MNAME：primary 名稱伺服器（可變長度的名稱）           │  ns1.shengsheng.example.
 ├───────────────────────────────────────────────┤
 │ RNAME：管理者信箱，@ 換成 .（可變長度）              │  hostmaster.shengsheng.example.
 ├───────────────────────────────────────────────┤
 │ SERIAL   (32 bits)  zone 版本號，每次修改都要遞增   │  2026100201
 │ REFRESH  (32 bits)  secondary 多久檢查一次 serial  │  7200
 │ RETRY    (32 bits)  檢查失敗後多久重試            │  900
 │ EXPIRE   (32 bits)  多久聯絡不上 primary 就停止回答 │  1209600
 │ MINIMUM  (32 bits)  負面快取 TTL 的上限            │  900
 └───────────────────────────────────────────────┘
   負面快取 TTL = min(SOA RR 的 TTL, MINIMUM) = min(3600, 900) = 900 秒
```

逐行看：MNAME 與 RNAME 是可變長度的名稱，所以後面五個 32 位元整數的位置要先跳過兩個名稱才找得到；程式解析時通常直接取 RDATA 的最後 4 bytes 當作 MINIMUM，本章的動手做就是這樣做的。SERIAL、REFRESH、RETRY、EXPIRE 控制上一節提到的 primary／secondary 同步。最下面那行就是 Joe 卡住的原因：如果聲聲 Live 的 SOA TTL 是 3600、MINIMUM 也是 3600，那麼在紀錄建立前查過一次，就要最多等一小時。

這個過程畫成時序圖：

```text
 Joe 的筆電       recursive resolver               shengsheng.example 權威伺服器
    │  classroom-v2 A?  │                                    │
    │──────────────────►│──────── classroom-v2 A? ──────────►│
    │                   │◄──── NXDOMAIN + SOA(TTL 3600, MIN 900)─│
    │◄── NXDOMAIN ──────│  記下「不存在」900 秒                 │
    │                   │                                    │  t=60s 維運新增 A 紀錄
    │  classroom-v2 A?  │                                    │
    │──────────────────►│  快取命中，不回源                      │
    │◄── NXDOMAIN ──────│  （剩 780 秒）                        │
    │        ...        │                                    │
    │  t=901s 再查       │──────── classroom-v2 A? ──────────►│
    │◄── 203.0.113.80 ──│◄──────── A 203.0.113.80 ────────────│
```

圖中最關鍵的是中段：權威伺服器在 t=60 秒就已經有新紀錄，但 resolver 根本沒有去問，因為它手上那份「不存在」還沒過期。修法因此不在權威端，而是在流程上：**先建立紀錄，再讓任何人查詢**；新服務的健康檢查、CI 腳本、監控探測都不要在紀錄建立前就開始跑。如果真的已經被快取，只能等，或請使用者改用另一個 resolver 暫時繞過。

負面快取還有兩個延伸。第一，很多 resolver 會對負面 TTL 設上限（例如 BIND 的 `max-ncache-ttl`），數值依實作與設定而定，所以 MINIMUM 設得很大也不一定會照用。第二，開啟 DNSSEC 的 zone 會用 NSEC／NSEC3 紀錄「證明」某個範圍內沒有名稱，支援積極快取（RFC 8198）的 resolver 可以直接用這份證明回答範圍內其他不存在的名字，連問都不用問。這在減輕隨機子網域查詢的負載上很有用，15.9 節會再談 NSEC。

## 15.5 CNAME 的限制與 apex 的難題

**CNAME** 是「這個名字其實是另一個名字的別名」，例如 `www.shengsheng.example` CNAME 到新 CDN 的 `ss.newedge.test`，resolver 會接著去解析後者。雲端 LB 和 CDN 的 IP 會變，供應商只給你一個主機名稱，所以 CNAME 在現代架構裡到處都是。但 CNAME 有一條硬規則：**一個名稱如果有 CNAME，就不能再有任何其他紀錄**（DNSSEC 用的 RRSIG、NSEC 除外）。原因很直覺：CNAME 的意思是「去問別人」，如果同名又有 MX 或 TXT，resolver 就不知道該用哪一份。

這條規則撞上了 **zone apex**。apex 是 zone 的頂點，也就是裸網域 `shengsheng.example` 本身。apex 一定要有 SOA 與 NS 紀錄（zone 才成立），通常還有 MX 和各種驗證用 TXT。既然已經有其他紀錄，就不能放 CNAME，這就是行銷同事被後台拒絕的原因。下圖對照兩種名稱：

```text
 shengsheng.example.（apex）               www.shengsheng.example.
 ┌──────────────────────────────┐          ┌──────────────────────────────┐
 │ SOA  ns1... hostmaster... ✔ 必要 │          │ CNAME ss.newedge.test          │
 │ NS   ns1.shengsheng.example ✔ 必要│          │（同名不能再有其他紀錄）          │
 │ MX   10 mail.shengsheng...      │          └──────────────────────────────┘
 │ TXT  "site-verification=..."    │                       │
 │ CNAME ss.newedge... ✘ 與上面衝突   │                       ▼
 └──────────────────────────────┘          ss.newedge.test. A 203.0.113.10, 203.0.113.11
        │
        │ 解法：在權威端「攤平」
        ▼
 ALIAS／flattening：DNS 供應商自己去解析 ss.newedge.test，把得到的 A／AAAA 直接當成 apex 的答案
```

逐步看：左邊的 apex 已經有 SOA、NS、MX、TXT，加上 CNAME 就違反規則；右邊的 www 只有一筆 CNAME，完全合法，這也是很多網站讓 www 當主要入口、裸網域只做轉址的原因。左下方是業界的解法：**ALIAS／ANAME／CNAME flattening**。它們不是標準的 DNS type，而是 DNS 供應商在權威端的功能：設定時你寫「apex 指向某個主機名稱」，供應商在收到查詢時自己去解析目標，再把得到的 A／AAAA 當成 apex 的答案回出去。對 resolver 來說，它看到的就是普通的 A 紀錄。雲端供應商的 alias record 是同一類做法，但通常只能指向該雲端自己的資源。

第三條路是 **HTTPS record**（第 14 章介紹的 HTTPS／SVCB 紀錄）。它有兩種模式：priority 為 0 的 **AliasMode** 表示「這個名稱的 HTTPS 服務請去找另一個名稱」，而且可以合法地放在 apex，因為它只是一種新的 type，不是 CNAME；priority 大於 0 的 ServiceMode 則直接帶參數，例如 `alpn="h2,h3"` 告訴瀏覽器可以直接用 HTTP/3（第 22 章），`ipv4hint` 給位址提示，`ech` 帶 ECH 設定（第 18 章）。問題在於 client 支援度：只有會查 HTTPS record 的 client 才看得懂，所以實務上仍要保留 A／AAAA 讓舊 client 能用。

| 做法 | 能放在 apex？ | 是否標準 | 誰去解析目標 | 主要取捨 |
|---|---|---|---|---|
| CNAME | 不行 | 標準 | resolver | 最通用；同名不能有其他紀錄 |
| ALIAS／flattening | 可以 | 供應商私有功能 | 權威 DNS 供應商 | 綁定供應商；回給使用者的 TTL 與地理判斷由供應商決定 |
| 雲端 alias record | 可以 | 供應商私有功能 | 雲端 DNS | 通常只能指向同一雲端的資源 |
| HTTPS record AliasMode | 可以 | 標準 | 支援的 client | 舊 client 看不懂，需同時保留 A／AAAA |
| 直接寫 A／AAAA | 可以 | 標準 | 不需要 | 目標 IP 變動時要自己同步 |

CNAME 還有兩個常被忽略的規則。MX 與 NS 的目標必須是有 A／AAAA 的名稱，不能指向 CNAME。另外 CNAME 鏈越長，resolver 需要的查詢越多，任何一段的 TTL 最短者決定了整條鏈多快重新解析。最危險的則是 **dangling CNAME（懸空別名）**：例如 `promo.shengsheng.example` CNAME 到某個雲端儲存桶，活動結束後儲存桶被刪了，CNAME 卻還在。如果那個雲端服務允許任何人重新建立同名資源，別人就可能以你的子網域名義提供內容，這叫 **subdomain takeover**。防禦方法是讓「刪資源」與「刪 DNS 紀錄」在同一個流程裡完成，並定期掃描所有 CNAME 的目標是否還屬於自己。

下面這段小程式是一個簡化的 zone 檢查器，可以放在 CI 裡，在 zone 變更發布前擋下本節提到的錯誤：

```python
# 簡化的 zone 檢查器：在變更進權威 DNS 前，先擋下常見的設定錯誤
ZONE = "shengsheng.example."
records = [
    ("shengsheng.example.", "SOA", "ns1.shengsheng.example. hostmaster.shengsheng.example."),
    ("shengsheng.example.", "NS", "ns1.shengsheng.example."),
    ("shengsheng.example.", "CNAME", "ss.newedge.test."),                # 想讓 apex 指到新 CDN
    ("www.shengsheng.example.", "CNAME", "ss.newedge.test."),
    ("www.shengsheng.example.", "TXT", "site-verification=abc"),         # 和 CNAME 同名
    ("shengsheng.example.", "MX", "10 mail.shengsheng.example."),
    ("mail.shengsheng.example.", "CNAME", "mx.mailhost.example.org."),   # MX 指向 CNAME
    ("promo.shengsheng.example.", "CNAME", "shengsheng-promo.storage.example.com."),
]
# 外部供應商那邊還存在的資源；不在這裡的 CNAME 目標代表資源已刪除
live_targets = {"ss.newedge.test.", "mx.mailhost.example.org."}
EXTERNAL = (".example.com.", ".example.net.", ".example.org.", ".test.")   # 不歸聲聲 Live 管的網域


def lint(records):
    problems = []
    by_name = {}
    for name, rtype, value in records:
        by_name.setdefault(name, []).append((rtype, value))
    for name, rrs in by_name.items():
        types = {t for t, _ in rrs}
        if "CNAME" in types and name == ZONE:
            problems.append(f"{name} apex 不能放 CNAME（必須有 SOA、NS），改用 ALIAS/flattening 或 A/AAAA")
        elif "CNAME" in types and len(types) > 1:
            problems.append(f"{name} CNAME 不能和 {sorted(types - {'CNAME'})} 共存")
        for rtype, value in rrs:
            if rtype == "CNAME" and value.endswith(EXTERNAL) and value not in live_targets:
                problems.append(f"{name} 指向已不存在的資源 {value}（dangling，可能被別人認領）")
            if rtype in ("MX", "NS"):
                target = value.split()[-1]
                if "CNAME" in {t for t, _ in by_name.get(target, [])}:
                    problems.append(f"{name} 的 {rtype} 指向 CNAME {target}，應指向有 A/AAAA 的名稱")
    return problems


found = lint(records)
for p in found:
    print("ERROR", p)
assert len(found) == 4
print(f"共 {len(found)} 個問題，修好之前不要發布這次 zone 變更")
```

```text
ERROR shengsheng.example. apex 不能放 CNAME（必須有 SOA、NS），改用 ALIAS/flattening 或 A/AAAA
ERROR shengsheng.example. 的 MX 指向 CNAME mail.shengsheng.example.，應指向有 A/AAAA 的名稱
ERROR www.shengsheng.example. CNAME 不能和 ['TXT'] 共存
ERROR promo.shengsheng.example. 指向已不存在的資源 shengsheng-promo.storage.example.com.（dangling，可能被別人認領）
共 4 個問題，修好之前不要發布這次 zone 變更
```

檢查器找到四個問題：apex 的 CNAME（行銷同事想做的事）、MX 指向 CNAME、www 的 CNAME 和 TXT 共存，以及 `promo` 指向已不存在的儲存資源。真實的 zone 檢查工具（例如 BIND 附的 `named-checkzone`）會做更完整的語法與語意檢查；dangling 的偵測則需要和你的雲端資源清單比對，只看 DNS 本身是看不出來的。

## 15.6 用 DNS 分散負載：round robin、weighted、GeoDNS 與 health check

換 CDN 的事故後，阿德想換一種更穩的切換方式：不要一口氣把所有人搬過去，而是先讓 10% 的使用者連新 CDN，觀察沒問題再逐步提高。這需要 DNS 依「策略」挑選答案，而不是永遠回同一份紀錄。DNS 層的負載分散成本低、不用在資料路徑上多放一台機器，是全球服務分流的第一道關卡；但它的控制力也有明確的極限，下面逐一說明。

最簡單的是 **round robin**：同一個名稱放多筆 A 紀錄，權威伺服器或 resolver 每次以不同順序回覆，client 多半挑第一筆。它幾乎不需要設定，但 client 怎麼挑、挑到的連不上時會不會換下一筆，完全依實作而定；有些 client 會依 IPv6 的位址選擇規則重新排序，讓「輪流」失準。**Weighted（加權）回應**則是權威端依權重隨機挑選：新 CDN 權重 10、舊 CDN 權重 90，就有約一成的回答指向新 CDN，適合用來做金絲雀式的搬遷。要注意的是，權重作用在「resolver 的查詢」上而不是「使用者」上：一個大型 ISP resolver 抽到新 CDN 後，會在 TTL 內把這個答案給它背後所有使用者，所以實際流量比例會比權重粗糙得多。

**GeoDNS** 依查詢來源的地理位置回不同答案，讓台灣的學生連到亞洲的 edge、美國的學生連到美國的 edge；延遲導向（latency-based）的做法則依量測到的延遲挑選。關鍵限制是：權威伺服器看到的來源 IP 是 **resolver** 的位址，不是使用者的。使用者在台灣、卻設定了一個實際位在美國節點的公共 resolver 時，GeoDNS 就會判斷錯誤。為了解決這個問題，有 **EDNS Client Subnet（ECS）** 這個擴充（RFC 7871）：resolver 在查詢中附上使用者 IP 的前綴（例如 /24），讓權威端用它判斷。

```text
 台灣的學生 198.51.100.23                      shengsheng.example 權威（GeoDNS）
      │                                                 ▲
      │ 設定了位在美國的公共 resolver                      │
      ▼                                                 │
 公共 resolver 192.0.2.53 ──── 查詢 www A? ──────────────┘
   │  沒帶 ECS：權威只看到 192.0.2.53 → 判斷為 us → 回美國 edge 203.0.113.11（繞遠路）
   │  帶 ECS 198.51.100.0/24：權威看到使用者子網 → 判斷為 asia → 回亞洲 edge 203.0.113.10
   ▼
 resolver 快取時也要以「子網」為單位分開存，否則不同地區的使用者會拿到彼此的答案
```

這張圖說明三件事。第一，沒有 ECS 時，地理判斷的依據是 resolver 位置，誤差可能大到跨洲。第二，帶 ECS 時判斷準確了，但使用者 IP 的一部分被送到了權威伺服器，這是隱私上的取捨；有些注重隱私的公共 resolver 刻意不送 ECS，改以在各地廣設節點、靠 anycast 讓 resolver 本身就在使用者附近。第三，resolver 必須依子網分開快取，快取效率因此下降。所以 GeoDNS 是「大致正確」的分流，精準的就近接入通常還要配合第 6 章的 anycast 或 CDN（第 25 章）。

DNS 分流最常搭配的是 **health check**：權威 DNS 供應商從多個地點定期探測每個端點（例如每 10 秒對 `/healthz` 發 HTTP 請求），連續失敗達門檻就把它從答案中移除。這讓 DNS 有了自動故障切換的能力，但切換時間永遠受快取限制。下面是新 CDN 的亞洲 edge 故障的時間軸：

```text
 t(秒)   0        30       40       50                100
         │        │        │        │                  │
 edge    正常 ────►故障──────────────────────────────────────────►
 健康檢查  ✔        ✘ (1)    ✘ (2)    ✘ (3) → 從答案移除
 resolver          t=40 剛好回源，拿到「還沒移除」的答案
 快取              ├────────────── TTL 60 秒 ───────────┤
 使用者    ─── 連到故障的 edge，請求失敗 ───────────────────►│ 快取過期，拿到備援 IP
          最壞的切換時間 ≈ 偵測時間（間隔 × 門檻）＋ TTL ＋ client 自己的快取
```

逐步看：故障發生在 t=30，健康檢查在 30、40、50 秒連續失敗三次，權威端在 t=50 才移除它；偏偏某台 resolver 在 t=40 回源，拿到的還是故障節點，並快取 60 秒，直到 t=100 才重新查詢。使用者因此多受了 70 秒的影響。這個公式告訴你調參的方向：縮短檢查間隔、降低門檻、降低 TTL，但每一項都有代價（誤判、探測流量、查詢量）。此外還要決定**全部端點都被判定不健康**時怎麼辦。多數設計選擇 fail open，也就是照樣回全部端點，因為「所有節點同時掛掉」更常見的原因其實是健康檢查本身出了問題（探測端網路斷了、檢查路徑寫錯），此時回空答案等於讓整個服務自己下線。

DNS 分流和第 25 章的 load balancer 分流是互補的，不是二選一：

| 面向 | DNS 層分流 | Load balancer 分流（第 25 章） |
|---|---|---|
| 決策單位 | 每次查詢（實際上是每個 resolver × TTL） | 每條連線或每個請求 |
| 生效速度 | 受 TTL 與各層快取限制，分鐘級 | 立即 |
| 是否看得到使用者 | 只看得到 resolver（除非有 ECS） | 看得到 client IP 與請求內容 |
| 健康檢查後的切換 | 偵測時間＋TTL | 偵測時間 |
| 適合的用途 | 跨地區、跨雲、跨供應商的粗分流與災難切換 | 同一地區內的精細分流、sticky session、逐步上線 |

聲聲 Live 最後的做法是兩層並用：`www` 的就近接入交給 CDN 自己的 GeoDNS 與 anycast，`api` 則由 API LB 再把請求分給後面的 nginx；之後不論換 CDN 還是搬 LB，都用 weighted 紀錄從 10% 開始逐步調到 100%，並保留舊端點直到流量歸零。

## 15.7 Split-horizon DNS：同一個名字，內外不同答案

辦公室同事全部連到舊 CDN，原因是 **split-horizon DNS（分割視野 DNS）**：同一個名稱，依查詢者在內網或外網回不同答案。例如公司內部的 resolver 把 `api.shengsheng.example` 解析成 API LB 在 VPC 內的私有位址 10.20.16.5，讓內部服務直接走內網；外部使用者則拿到公網的 203.0.113.80。雲端的私有 DNS zone（只在特定 VPC 內生效，第 44 章）就是同一個概念。

```text
                         ┌───────────── 內部 view ─────────────┐
 辦公室／VPC 內的機器 ───►│ 內部 resolver                        │──► api.shengsheng.example = 10.20.16.5
                         │ （有內部 zone，優先於公網答案）         │    ops.shengsheng.example = 10.20.3.17
                         │                                    │    www CNAME ss.cdnedge.test（舊 CDN）
                         └───────────────────────────────────┘
                         ┌───────────── 外部 view ─────────────┐
 網際網路上的使用者 ─────►│ 公網權威伺服器                       │──► api.shengsheng.example = 203.0.113.80
                         │                                    │    ops.shengsheng.example → NXDOMAIN
                         │                                    │    www CNAME ss.newedge.test（新 CDN）
                         └───────────────────────────────────┘
 事故：換 CDN 時只改了外部 view，內部 view 的 www 仍指向舊 CDN
```

這張圖顯示 split-horizon 的兩個價值與一個陷阱。價值一，內部流量走私有位址，不必繞到公網再回來。價值二，內部才有的名稱（例如內部後台 `ops`）不會出現在公網 DNS 裡，減少對外暴露的資訊。陷阱則是圖的最下方：同一個名字有兩份資料來源，變更時很容易只改一份。除錯時更讓人困惑，因為「我這邊查到的」與「使用者查到的」本來就不一樣。

實務上的建議有三點。第一，把內外兩份 zone 放在同一個版本控制與變更流程裡，用工具產生，避免手動各改各的。第二，除錯時明確指定 resolver，例如 `dig @內部 resolver` 與 `dig @公共 resolver` 各查一次比對。第三，留意 VPN 與 DoH：遠端工作的同事若沒有走公司 resolver，或瀏覽器自己啟用了 DoH 直接問公共 resolver，就會拿到外部 view 的答案，連不到內部服務。15.10 節會再談這個衝突。名稱解析在作業系統裡怎麼挑 resolver、search domain 怎麼影響查詢，屬於第 16 章的主題。

## 15.8 DNS 被竄改的風險：劫持與 cache poisoning 的防禦

DNS 最初設計時沒有任何驗證機制：resolver 收到一個 UDP 回應，只要 ID 和問題對得上，就相信它。這代表任何能在路徑上改封包、或能搶先送出假回應的人，都可能讓使用者連到錯誤的 IP。對聲聲 Live 來說，這會讓學生連到假的登入頁；雖然第 18 章的 TLS 憑證驗證會擋下大部分這類情況（假伺服器拿不出 `www.shengsheng.example` 的有效憑證），DNS 的完整性仍然是第一道防線，而且對沒有 TLS 的流量（例如郵件伺服器之間的查詢）更加關鍵。本節只談成因、偵測與防禦。

**DNS 劫持**泛指答案在路徑上被替換。常見的來源有：公共 Wi-Fi 或 ISP 在使用者查不存在的名字時，改回一個廣告頁的 IP（NXDOMAIN 重寫）；家用路由器的 DNS 設定被惡意軟體改掉；或是攻擊者取得網域註冊商帳號，直接把 NS 改到自己的伺服器。最後這種影響最大，因為它改的是「權威來源」本身，所有 resolver 都會照著新的委派去問。

**Cache poisoning（快取投毒）**則是讓 recursive resolver 快取一個偽造的答案，之後所有使用這台 resolver 的人都會受影響。它的成因是「判斷回應真偽的依據太少」：早期 resolver 只靠 16 位元的 transaction ID，而且來源 port 固定，偽造者只要猜對 65536 種可能之一。2008 年公開的 Kaminsky 漏洞說明了這個弱點可以被有效地利用，促使各家 resolver 全面加入防禦。防禦的核心想法是增加偽造回應必須「剛好猜中」的隨機性，並減少可以被塞進快取的資料範圍：

- **來源 port 隨機化**：每次查詢用隨機的來源 port，偽造的回應必須同時猜中 port 與 ID。
- **0x20 大小寫隨機化**：送出的查詢名稱隨機混合大小寫，例如 `wWw.ShEngsheng.example`；DNS 比對名稱不分大小寫，所以權威端照常回答，而且會把 question section 原樣複製回來，resolver 就能逐字元比對。
- **Bailiwick 檢查**：resolver 只接受與問題相關、屬於該權威伺服器管轄範圍的紀錄，不會因為回應的 additional section 夾帶了其他網域的資料就快取起來。
- **DNS Cookies（RFC 7873）**：client 與 server 交換一個輕量的 cookie，讓 server 和 client 能辨認對方確實是之前通訊過的那一方。
- **DNSSEC**：從根本上讓答案可以被驗證，下一節詳談。

下面這段程式估算前三種隨機性加總後，一次偽造回應剛好猜中的機率，並示範 0x20 的比對方式：

```python
import math
import secrets

name = "www.shengsheng.example"
letters = sum(c.isalpha() for c in name)

# 防禦方能讓「偽造回應剛好猜中」變難的隨機性來源（以 bits 計）
sources = {
    "只有 16-bit transaction ID": 16,
    "+ 隨機來源 port（約 64512 個）": 16 + math.log2(65536 - 1024),
    f"+ 0x20 大小寫隨機（{letters} 個字母）": 16 + math.log2(65536 - 1024) + letters,
}
for label, bits in sources.items():
    print(f"{label:<34} {bits:5.1f} bits，單次猜中機率 1/{2 ** bits:,.0f}")


def randomize_case(qname):
    """0x20 技巧：resolver 送出的名稱大小寫隨機，回應必須原樣帶回。"""
    return "".join(c.upper() if c.isalpha() and secrets.randbits(1) else c.lower() for c in qname)


def accept(sent_qname, echoed_qname):
    return echoed_qname == sent_qname           # 逐字元比對，大小寫也要一樣


sent = randomize_case(name)
assert sent.lower() == name                     # DNS 名稱不分大小寫，權威端照樣能回答
print("送出的 question（每次執行不同）：", sent)
print("回應照原樣帶回 question ->", "接受" if accept(sent, sent) else "丟棄")
print("回應的大小寫對不上     ->", "接受" if accept(sent, sent.swapcase()) else "丟棄")
assert not accept(sent, sent.swapcase())
```

```text
只有 16-bit transaction ID            16.0 bits，單次猜中機率 1/65,536
+ 隨機來源 port（約 64512 個）              32.0 bits，單次猜中機率 1/4,227,858,432
+ 0x20 大小寫隨機（20 個字母）                52.0 bits，單次猜中機率 1/4,433,230,883,192,824
送出的 question（每次執行不同）： Www.sHeNGshENG.EXamplE
回應照原樣帶回 question -> 接受
回應的大小寫對不上     -> 丟棄
```

輸出的第一行是只靠 transaction ID 的情況：一次猜中的機率是六萬五千分之一，偽造者只要能在真正回應到達前送出大量候選，就可能成功。加上隨機來源 port 之後，可能性多了約 16 位元（這裡用 1024 到 65535 的範圍做上限估算，實際可用的範圍依作業系統與 resolver 設定而定）。0x20 的效果和名稱裡的字母數成正比，對短名稱幫助較小。最後兩行示範比對：權威端照原樣帶回大小寫的回應被接受，大小寫對不上的回應被丟棄。這些措施只是把偽造的難度拉高到不切實際，並沒有「證明」答案是真的；要證明，需要密碼學。

| 威脅 | 成因 | 怎麼偵測 | 防禦 |
|---|---|---|---|
| 路徑上的竄改（Wi-Fi、ISP） | DNS 明文、無完整性保護 | 比對不同 resolver 的答案；監控 TLS 憑證錯誤 | DoT／DoH 保護 stub 到 resolver；DNSSEC 驗證 |
| Recursive 快取投毒 | 回應真偽的判斷依據不足 | resolver 的異常回應統計；DNSSEC bogus 計數 | port 與 0x20 隨機化、bailiwick 檢查、DNS Cookies、DNSSEC 驗證 |
| 註冊商帳號被盜、NS 被改 | 帳號安全不足 | 監控 NS 與 DS 紀錄變更、註冊商的變更通知 | MFA、registry lock、限制可操作人員 |
| Dangling CNAME 被認領 | 資源已刪、紀錄還在 | 定期掃描 CNAME 目標歸屬 | 刪資源與刪紀錄同一流程 |
| 憑證被錯誤簽發 | 攻擊者暫時控制 DNS 後申請憑證 | Certificate Transparency 監控（第 19 章） | CAA 紀錄限制可簽發的 CA；DNSSEC |

## 15.9 DNSSEC：替答案簽名的信任鏈

**DNSSEC（DNS Security Extensions）**讓 zone 的擁有者用私鑰替紀錄簽名，resolver 用公鑰驗證，從而確認「這份答案確實來自 zone 擁有者，而且沒被改過」。它提供的是**完整性與來源真實性**，不提供機密性：查詢與答案仍然是明文，任何人都看得到你查了什麼。這一點常被誤解，也是 DNSSEC 與下一節 DoH 的分工所在。數位簽章與 hash 的原理在第 17 章有完整說明，這裡只需要知道：用私鑰產生的簽章，任何持有對應公鑰的人都能驗證，但沒有私鑰就產生不出有效簽章。

DNSSEC 新增了四種紀錄。**DNSKEY** 放 zone 的公鑰；**RRSIG** 是對某一組紀錄（RRset，也就是同名、同 type 的所有紀錄）的簽章；**DS（Delegation Signer）** 放在父區，內容是子區公鑰的 hash；**NSEC／NSEC3** 用來簽名證明「某個名稱或 type 不存在」。多數 zone 用兩把金鑰：**KSK（Key Signing Key）**只負責簽 DNSKEY 這組紀錄，**ZSK（Zone Signing Key）**負責簽 zone 裡其他所有紀錄。分開的原因是 KSK 的 hash 登記在父區，換 KSK 要和父區協調；ZSK 則可以自己頻繁輪替，不必麻煩父區。

三種紀錄的 RDATA 布局如下，本章動手做的模擬程式就是照這些格式組 bytes 的：

```text
 DNSKEY RDATA                              DS RDATA（放在父區）
  0               15 16      23 24      31   0              15 16     23 24      31
 ┌──────────────────┬─────────┬──────────┐ ┌─────────────────┬────────┬──────────┐
 │ Flags (16)       │Protocol │Algorithm │ │ Key Tag (16)     │Algorithm│Digest Type│
 │ 256=ZSK 257=KSK  │ 固定 3   │ 13、15…  │ │ 指向子區哪把 KSK  │         │ 2=SHA-256 │
 ├──────────────────┴─────────┴──────────┤ ├─────────────────┴────────┴──────────┤
 │ Public Key（可變長度）                   │ │ Digest = hash(子區名稱 ‖ DNSKEY RDATA) │
 └───────────────────────────────────────┘ └──────────────────────────────────────┘

 RRSIG RDATA
  0                              15 16             23 24             31
 ┌─────────────────────────────────┬────────────────┬────────────────┐
 │ Type Covered (16)  例：1 = A     │ Algorithm (8)  │ Labels (8)     │
 ├─────────────────────────────────┴────────────────┴────────────────┤
 │ Original TTL (32)                                                  │
 │ Signature Expiration (32)   簽章過期時間（UTC 秒）                    │
 │ Signature Inception (32)    簽章生效時間                             │
 ├─────────────────────────────────┬──────────────────────────────────┤
 │ Key Tag (16)  用哪把 DNSKEY 驗證  │ Signer's Name（可變長度）…          │
 ├─────────────────────────────────┴──────────────────────────────────┤
 │ Signature（可變長度）＝ 對「RRSIG 欄位＋排序後的 RRset」的簽章           │
 └────────────────────────────────────────────────────────────────────┘
```

逐欄看：DNSKEY 的 Flags 裡有一個 SEP 位元，值 257 慣例上代表 KSK、256 代表 ZSK；Protocol 永遠是 3；Algorithm 指出用哪種簽章演算法，現在建議使用 13（ECDSA P-256 搭配 SHA-256）或 15（Ed25519），舊的 RSA／SHA-1 組合已不建議。DS 的 Key Tag 是從 DNSKEY RDATA 算出的 16 位元短識別碼，方便快速找到對應的金鑰；Digest 是子區名稱接上 DNSKEY RDATA 後的 hash。RRSIG 帶有生效與過期時間，這是 DNSSEC 營運上最常出事的地方：如果自動重簽的排程壞了，簽章一過期，整個 zone 就會在所有驗證者眼中失效。

把這些紀錄串起來就是**信任鏈**。resolver 預先內建 root zone KSK 的資訊，稱為 **trust anchor（信任錨）**；從這裡往下，每一層都用父區的 DS 認可子區的 KSK，再用 KSK 認可 ZSK，最後用 ZSK 驗證答案：

```text
 trust anchor（resolver 內建 root KSK 的 hash）
        │ 比對
        ▼
 .（root） DNSKEY {KSK, ZSK} ── RRSIG(由 root KSK 簽) ── 驗證通過 → 信任 root ZSK
        │ root ZSK 簽了 ↓
        ▼
 DS(example.) ── RRSIG(由 root ZSK 簽)      「example. 的 KSK 長這樣」
        │ 比對
        ▼
 example.（TLD） DNSKEY {KSK, ZSK} ── RRSIG(由 TLD KSK 簽) → 信任 TLD ZSK
        │ TLD ZSK 簽了 ↓
        ▼
 DS(shengsheng.example.) ── RRSIG(由 TLD ZSK 簽)
        │ 比對
        ▼
 shengsheng.example. DNSKEY {KSK, ZSK} ── RRSIG(由自己的 KSK 簽) → 信任 ZSK
        │ ZSK 簽了 ↓
        ▼
 api.shengsheng.example. A 203.0.113.80 ── RRSIG(由 ZSK 簽)  → SECURE，設 AD 位元
```

由上往下讀：每一個箭頭都是「已經信任的東西」替「下一個東西」背書。root 的 DNSKEY 組先跟 trust anchor 比對，通過後 root ZSK 就可信；root ZSK 簽了 TLD 的 DS，所以 TLD 的 KSK 可信；依此類推，一路到 `api` 的 A 紀錄。任何一環對不上，結果就是 **bogus**，驗證型 resolver 會回 **SERVFAIL**，而不是把可疑的答案交給使用者。如果某一層的父區明確沒有 DS（並用 NSEC 證明沒有），這一層以下就是 **insecure**，照一般 DNS 處理；這也是 DNSSEC 能逐步部署的原因。

DNS 標頭與 EDNS 中有三個和 DNSSEC 相關的旗標，用 `dig` 時會看到：**DO**（DNSSEC OK，放在 EDNS 的 OPT 紀錄裡）表示 client 想收到 RRSIG 等 DNSSEC 紀錄；**AD**（Authenticated Data）是驗證型 resolver 在回應裡宣告「我驗證過了，是 SECURE」；**CD**（Checking Disabled）是 client 要求 resolver「先別驗證，把資料原樣給我」。CD 在除錯時非常有用：同一個查詢不帶 CD 回 SERVFAIL、帶 `+cd` 卻有答案，幾乎可以確定是 DNSSEC 驗證失敗，而不是權威伺服器掛了。

DNSSEC 的取捨要說清楚。它讓 cache poisoning 與路徑竄改無法偽造出能通過驗證的答案；但它也引入了新的故障模式：簽章過期、金鑰輪替做錯、換 DNS 供應商時 DS 沒同步，都會讓網域在驗證型 resolver 上完全消失。它讓回應變大（帶著簽章與金鑰），更容易超過 UDP 的大小限制而需要改用 TCP。它只保護到驗證發生的地方：多數使用者的作業系統不自己驗證，而是相信 resolver 設的 AD 位元，所以 resolver 到使用者這一段仍然需要其他保護。Rita 提醒的那句話指的就是 DS：換供應商的標準做法是先在新供應商用新金鑰簽好 zone，讓父區同時掛新舊兩組 DS（或採用新舊供應商互相匯入金鑰的方式），等快取過期後再移除舊的，絕不能直接切換。

> [!note] 2026 現況
> 依 2026 年 10 月查證，IANA 公布的 root zone KSK 輪替時程是：新的 KSK-2024（key tag 38696）已於 2025 年 1 月發布在 root zone，預定於 2026 年 10 月 11 日開始簽署 root 的 DNSKEY RRset，取代 KSK-2017；讀到這裡時，這一步很可能已經完成，實際進度請以 IANA 公告為準。會自動追蹤 trust anchor 的 resolver（依 RFC 5011 的機制）應該早已信任新金鑰；自己維護 trust anchor 檔案的系統，則要確認檔案裡已經有 KSK-2024。演算法方面，新部署建議使用 ECDSA P-256（13）或 Ed25519（15）。TLD 層的簽章普及率高，但第二層網域的簽章比例與驗證型 resolver 的使用比例仍有限，且各國差異很大；具體數字變動快，需要時請查 APNIC Labs 等量測來源的最新資料並標註日期。

## 15.10 DoT 與 DoH：把最後一哩加密

DNSSEC 保護的是資料本身，但查詢仍是明文：咖啡廳的 Wi-Fi 營運者能看到學生查了 `live.shengsheng.example`，也能在 stub 與 resolver 之間竄改沒經過驗證的答案。**加密 DNS** 處理的是 stub resolver 到 recursive resolver 這一段的**機密性與完整性**。**DoT（DNS over TLS）**把 DNS 訊息放進 TCP 853 埠上的 TLS 連線；**DoH（DNS over HTTPS）**把 DNS 訊息包在 HTTP 請求裡（媒體類型 `application/dns-message`；POST 時放在 body，GET 時以 base64url 編碼放進 URL 的 `dns` 參數），走 443 埠的 HTTPS；**DoQ（DNS over QUIC）**則跑在第 13 章的 QUIC 上。三者傳的都是同樣的 DNS 二進位訊息，差別只在外面那層傳輸。

```text
 一般 DNS            DoT                     DoH                          DoQ
 ┌─────────┐      ┌─────────┐           ┌──────────────┐            ┌─────────┐
 │ DNS 訊息 │      │ DNS 訊息 │           │ DNS 訊息        │            │ DNS 訊息 │
 ├─────────┤      ├─────────┤           ├──────────────┤            ├─────────┤
 │ UDP 53  │      │ TLS     │           │ HTTP/2 或 3    │            │ QUIC    │
 └─────────┘      ├─────────┤           ├──────────────┤            ├─────────┤
   明文            │ TCP 853 │           │ TLS（或 QUIC）  │            │ UDP 853 │
                  └─────────┘           ├──────────────┤            └─────────┘
                  專用埠，網管一眼可辨      │ TCP／UDP 443   │
                                        └──────────────┘
                                        和一般網頁流量混在一起
```

由左到右看：一般 DNS 直接放在 UDP 上，沒有任何保護。DoT 用專用的 853 埠，網路管理者能清楚看出「這是加密 DNS」，可以選擇放行或封鎖。DoH 走 443，和一般 HTTPS 流量混在一起，難以單獨封鎖，而且可以重用瀏覽器已經建立的 HTTP/2 或 HTTP/3 連線。DoQ 用 QUIC，省去 TCP 與 TLS 分開交握的延遲。

| 面向 | 一般 DNS | DoT | DoH | DNSSEC |
|---|---|---|---|---|
| 保護哪一段 | 無 | stub ↔ resolver | stub ↔ resolver | 權威資料到驗證者，與路徑無關 |
| 機密性 | 無 | 有 | 有 | 無 |
| 完整性 | 無 | 有（只限這一段） | 有（只限這一段） | 有（端到端驗證資料） |
| 傳輸 | UDP／TCP 53 | TCP 853 + TLS | HTTPS 443 | 沿用一般 DNS |
| 誰常用 | 傳統預設 | 作業系統層（例如 Android 的 Private DNS） | 瀏覽器與作業系統 | zone 擁有者簽、resolver 驗 |
| 對企業網路的影響 | 易監控 | 可辨識、可管理 | 可能繞過公司 resolver | 需要營運金鑰 |

這張表的重點是：DoH／DoT 與 DNSSEC 互補。DoH 讓路上的人看不到也改不了你和 resolver 之間的對話，但如果 resolver 本身被投毒或作假，DoH 只會把錯誤答案安全地送到你手上；DNSSEC 則讓資料本身可驗證，不管它經過誰。兩者都開，才同時涵蓋「傳輸途中」與「資料來源」。

加密 DNS 對企業與 split-horizon 有實際影響。如果瀏覽器自行改用公共 DoH resolver，就會繞過公司的內部 resolver，查不到內部名稱，也繞過公司以 DNS 實作的安全過濾。為此，瀏覽器與作業系統發展出幾種協調機制：瀏覽器在偵測到企業政策（例如裝置管理設定）時停用自己的 DoH；「同一 provider 自動升級」模式只在使用者原本的 resolver 也支援 DoH 時才升級；網路也可以透過 DDR（Discovery of Designated Resolvers，RFC 9462）或 DNR（以 DHCP／RA 宣告加密 resolver，RFC 9463）告訴 client「這個網路的 resolver 支援哪種加密方式」。聲聲 Live 的辦公室最後的做法是：讓內部 resolver 本身提供 DoH，並透過裝置管理政策指定瀏覽器使用它。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流瀏覽器都支援 DoH，但預設行為不同，以下依一般了解整理、未逐一查證，請以各瀏覽器當期文件為準：Chromium 系瀏覽器預設採「若目前 resolver 的營運者也提供 DoH，就自動升級」；Firefox 在部分地區預設開啟 DoH；Windows 11、Android（Private DNS，使用 DoT）與 Apple 平台都有系統層級的加密 DNS 設定。HTTPS record 的 `ech` 參數已在 2026 年 3 月成為 RFC 9848，ECH 本身是 RFC 9849（依 2026 年 10 月查證）；由於瀏覽器要先取得 HTTPS record 才能使用 ECH，實務上 ECH 多半和 DoH 一起出現（第 18 章）。

## 15.11 故障判斷：NXDOMAIN、SERVFAIL 與搬遷後還連到舊端點

DNS 故障在使用者端常常只表現為「網站打不開」，所以第一步是把它分類。DNS 回應的 **rcode（回應碼）**是最直接的線索，搭配 **EDE（Extended DNS Errors，RFC 8914）**提供的詳細原因，大部分問題都能快速定位：

| rcode | 名稱 | 白話意思 | 常見原因 |
|---|---|---|---|
| 0 | NOERROR | 查詢成功；answer 可能是空的（NODATA） | 正常；或名稱存在但沒有這個 type |
| 1 | FORMERR | 查詢格式錯誤 | 中間設備不支援 EDNS、封包被截斷或改寫 |
| 2 | SERVFAIL | resolver 無法給出可靠答案 | 權威伺服器全掛或逾時、DNSSEC 驗證失敗（bogus）、委派錯誤 |
| 3 | NXDOMAIN | 名稱不存在 | 打錯字、紀錄還沒建、負面快取還沒過期、search domain 加錯後綴 |
| 5 | REFUSED | 伺服器拒絕回答 | 問了不負責這個 zone 的權威伺服器、resolver 不對外開放遞迴 |

EDE 是附在 EDNS 裡的額外錯誤碼，例如 6（DNSSEC Bogus）、7（Signature Expired）、9（DNSKEY Missing）、22（No Reachable Authority）、3（Stale Answer，表示 resolver 用了過期的快取來回答）。不是所有 resolver 都會附上 EDE，但新版的 `dig` 會在輸出中直接印出。下面是一次 DNSSEC 簽章過期時的示意輸出：

```bash
# 示意輸出：不帶與帶 +cd 各查一次
$ dig api.shengsheng.example A
;; ->>HEADER<<- opcode: QUERY, status: SERVFAIL, id: 41250
;; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1
; EDE: 7 (Signature Expired)

$ dig +cd api.shengsheng.example A
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 5121
;; flags: qr rd ra cd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
api.shengsheng.example. 60 IN A 203.0.113.80
```

第一次查詢 status 是 SERVFAIL，EDE 直接寫明簽章過期；第二次加了 `+cd` 要求 resolver 不驗證，就拿到了答案，而且 flags 裡沒有 `ad`。兩者對照，就能確定權威伺服器活著、資料也在，問題出在簽章。如果 `+cd` 也拿不到答案，再往委派或權威伺服器可用性查。

把三類故障整理成一張判斷流程：

```text
 使用者回報「連不上」
        │
        ▼
 dig 名稱（用使用者那邊的 resolver）── status? ──┬── NXDOMAIN ──► dig @權威伺服器 直接問
        │                                     │                ├ 權威也 NXDOMAIN → 紀錄真的不存在／打錯／search domain
        │                                     │                └ 權威有答案 → 負面快取未過期（看 SOA MINIMUM）
        │                                     │
        │                                     ├── SERVFAIL ──► dig +cd 再查一次
        │                                     │                ├ +cd 有答案 → DNSSEC 驗證失敗（DS、簽章期限、金鑰）
        │                                     │                └ +cd 也失敗 → dig +trace 看委派；權威伺服器是否回應
        │                                     │
        │                                     └── NOERROR ──► 答案是新 IP 嗎？
        │                                                      ├ 是舊答案 → 快取未過期（看舊 TTL）／split-horizon 的另一份 zone
        │                                                      └ 是新答案 → 問題不在 DNS：程式快取 IP？長連線還在舊端點？
        ▼
 每一步都記下：問的是哪台 resolver、什麼時間、回的 TTL 剩多少
```

這張流程圖的核心是「換位置問」。第一，從使用者的角度出發：用使用者實際使用的 resolver 查詢，而不是你自己的。第二，NXDOMAIN 時直接問權威伺服器，分辨「真的不存在」和「快取還記著不存在」。第三，SERVFAIL 時用 `+cd` 切開 DNSSEC 與其他原因，再用 `dig +trace` 從 root 一路走委派，找出哪一層斷掉。第四，NOERROR 但使用者仍連到舊 IP 時，比對回應中的 TTL：剩餘 TTL 很大代表快取還很新鮮；若 DNS 答案已經正確，就要看 DNS 以外的東西，例如程式自己記住的 IP 或還沒斷的長連線。最後一行提醒：DNS 的答案會隨時間和地點改變，所以記錄「誰、何時、從哪裡問」是除錯紀錄的基本格式。

聲聲 Live 事故的四個現象，套進這張圖就各有歸屬：大部分學生連不上是「NOERROR 但仍是舊 CDN，因為降 TTL 時各地快取拿的仍是 TTL 86400 的版本」；`classroom-v2` 是「權威有答案但 resolver 回 NXDOMAIN，負面快取」；辦公室是「split-horizon 的內部 zone 沒改」；而那些 resolver 已經給新答案、頁面卻仍然出錯的老師，是瀏覽器還沿用連到舊 CDN edge 的長連線，舊 CDN 一停用就全部出錯。下一節把其中幾個機制寫成可以執行的模擬。

## 15.12 動手做：模擬 TTL 傳播、負面快取、負載選擇與 DNSSEC 驗證

本節有四段程式，各自獨立執行，都只用標準函式庫、不連外網。第一段模擬多層快取下的 TTL 變更，比較三種搬遷策略；第二段在 127.0.0.1 上起一個假的權威 DNS server，觀察負面快取；第三段模擬 weighted、GeoDNS 與 health check；第四段用簡化的簽章鏈說明 DNSSEC 的信任鏈。

### 模擬一：三種搬遷策略

程式模擬 1000 台 recursive resolver。每台 resolver 快取同一個熱門名稱，快取一過期就馬上有人查，於是立刻回源。其中 10% 的 resolver 被設定為「TTL 至少 3600 秒」，用來代表不完全照規矩的快取（這是模擬假設，不是真實比例）。三種策略分別是：A 完全不降 TTL、B 搬前 10 分鐘才降 TTL、C 搬前 48 小時先降 TTL 到 300 秒。程式在切換後的幾個時間點統計還在回答舊 IP 的 resolver 比例：

```python
import bisect
import random

OLD_IP, NEW_IP = "198.51.100.7", "203.0.113.10"   # 舊 CDN edge → 新 CDN edge（代表 www 的答案）
H = 3600
OLD_TTL, LOW_TTL = 86400, 300
FLOOR = 3600          # 模擬假設：部分 resolver 把 TTL 下限墊高到 1 小時
N_RESOLVERS = 1000


def authoritative(t, lower_at, switch_at):
    """權威伺服器在時間 t 會回什麼：IP 由切換時間決定，TTL 由降 TTL 時間決定。"""
    ip = NEW_IP if t >= switch_at else OLD_IP
    ttl = LOW_TTL if t >= lower_at else OLD_TTL
    return ip, ttl


def build_timeline(rng, clamp, lower_at, switch_at, horizon):
    """回傳某台 resolver 每次回源的 (時間, IP)。熱門名稱一過期就會被重新查詢。"""
    first_ttl = max(OLD_TTL, FLOOR) if clamp else OLD_TTL
    t = -4 * 86400 - rng.uniform(0, first_ttl)  # 起點早於所有事件；快取年齡均勻分布
    times, ips = [], []
    while t <= horizon:
        ip, ttl = authoritative(t, lower_at, switch_at)
        times.append(t)
        ips.append(ip)
        t += max(ttl, FLOOR) if clamp else ttl
    return times, ips


def old_ratio(timelines, t):
    old = 0
    for times, ips in timelines:
        i = bisect.bisect_right(times, t) - 1   # t 當下快取裡的是最近一次回源的結果
        old += ips[i] == OLD_IP
    return old / len(timelines)


STRATEGIES = {
    "A 直接搬（TTL 86400）": None,
    "B 搬前 10 分鐘才降": -10 * 60,
    "C 搬前 48 小時先降": -48 * H,
}
CHECKPOINTS = [("+1m", 60), ("+10m", 600), ("+1h", H), ("+2h", 2 * H), ("+6h", 6 * H), ("+25h", 25 * H)]

print(f"{'策略':<20}" + "".join(f"{name:>7}" for name, _ in CHECKPOINTS) + "  全部切完")
results = {}
for label, lower in STRATEGIES.items():
    rng = random.Random(15)
    lower_at = 10**9 if lower is None else lower   # None 代表從未降 TTL
    timelines = [build_timeline(rng, rng.random() < 0.10, lower_at, 0, 30 * H)
                 for _ in range(N_RESOLVERS)]
    ratios = [old_ratio(timelines, t) for _, t in CHECKPOINTS]
    results[label] = ratios
    # 每台 resolver 第一次拿到新 IP 的時間，取最大值就是「舊 IP 完全消失」的時刻
    done = max(times[ips.index(NEW_IP)] for times, ips in timelines)
    print(f"{label:<20}" + "".join(f"{r:>7.1%}" for r in ratios) + f"  {done / H:6.2f}h")

a, b, c = results.values()
assert a[-2] > 0.6 and a[-1] == 0.0      # 不降 TTL：6 小時後大多數還在舊 IP
assert b[2] > 0.8                        # 太晚降等於沒降
assert c[1] < 0.15 and c[3] == 0.0       # 先降：10 分鐘內大多切完，2 小時內清空
print("結論：只有 C 能在切換後 2 小時內讓所有 resolver 都改答新 IP")
```

```text
策略                      +1m   +10m    +1h    +2h    +6h   +25h  全部切完
A 直接搬（TTL 86400）      99.7%  98.3%  94.8%  90.5%  73.4%   0.0%   23.99h
B 搬前 10 分鐘才降          99.5%  97.8%  94.3%  90.0%  72.9%   0.0%   23.82h
C 搬前 48 小時先降          79.9%   7.7%   0.0%   0.0%   0.0%   0.0%    0.99h
結論：只有 C 能在切換後 2 小時內讓所有 resolver 都改答新 IP
```

逐行解讀。策略 A 在切換後一分鐘，99.7% 的 resolver 仍回答舊 IP；六小時後仍有 73.4%，大約符合「快取年齡均勻分布在一天之內」的預期：還沒過期的比例約為 1 − 6/24 = 75%。要等將近 24 小時才全部切完。

策略 B 的數字幾乎和 A 一樣，這正是小晴這次的做法，也是本模擬最想強調的一點：在切換前 10 分鐘才降 TTL，只有那 10 分鐘內剛好過期回源的 resolver 拿到了 TTL 300 的版本，其他 resolver 手上仍是 TTL 86400 的舊快取，降了等於沒降。降 TTL 本身也要等一個舊 TTL 才會全面生效；週五晚上切、週六早上大半使用者還在舊 CDN，就是這個原因。

策略 C 在切換後一分鐘還有 79.9% 回答舊 IP，因為 TTL 300 秒的快取在第一分鐘只有約五分之一過期（1 − 60/300 = 80%）；十分鐘後只剩 7.7%，幾乎都是那 10% 墊高 TTL 下限的 resolver（理論值 10% × (3600 − 600)/3600 ≈ 8.3%）；一小時後全部清空。「全部切完」欄位顯示最壞情況是 0.99 小時，正好就是那個 3600 秒的下限，而不是 300 秒。這告訴我們，規劃關閉舊節點的時間時，不能只看自己設定的 TTL，還要為不照規矩的快取留緩衝，並以舊節點的實際流量作為最終依據。

### 模擬二：本機假權威伺服器與負面快取

第二段程式在 127.0.0.1 的隨機 UDP 埠上跑一個極簡的權威 DNS server，負責 `shengsheng.example` zone，它的 SOA TTL 是 3600、MINIMUM 是 900。旁邊是一個有快取的 resolver，用模擬時鐘重現 Joe 遇到的情況：先查一個還不存在的名字，維運隨後新增紀錄，再查一次：

```python
import socket
import struct
import threading

ZONE = "shengsheng.example"
SOA_TTL, SOA_MINIMUM = 3600, 900          # 負面快取 TTL = min(兩者) = 900 秒
records = {("live.shengsheng.example", 1): "203.0.113.25"}  # (名稱, type) -> IPv4；live 只有 A
queries_seen = []                                             # 權威端實際收到的查詢


def encode_name(name):
    return b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"


def read_name(msg, off):
    labels = []
    while True:
        n = msg[off]
        if n & 0xC0 == 0xC0:                      # 壓縮指標：跳到別處讀完名稱
            labels.append(read_name(msg, ((n & 0x3F) << 8) | msg[off + 1])[0])
            return ".".join(labels), off + 2
        if n == 0:
            return ".".join(labels), off + 1
        labels.append(msg[off + 1:off + 1 + n].decode())
        off += 1 + n


def soa_rr():
    rdata = (encode_name("ns1." + ZONE) + encode_name("hostmaster." + ZONE)
             + struct.pack("!5I", 2026100201, 7200, 900, 1209600, SOA_MINIMUM))
    return encode_name(ZONE) + struct.pack("!HHIH", 6, 1, SOA_TTL, len(rdata)) + rdata


def serve(sock):
    while True:
        data, addr = sock.recvfrom(512)
        if data == b"stop":
            return
        qid, flags = struct.unpack("!HH", data[:4])
        qname, off = read_name(data, 12)
        qtype, _ = struct.unpack("!HH", data[off:off + 4])
        queries_seen.append((qname, qtype))
        question = data[12:off + 4]
        ip = records.get((qname, qtype))
        name_exists = any(name == qname for name, _ in records)
        rcode = 0 if name_exists else 3          # 3 = NXDOMAIN
        if ip:
            ans = encode_name(qname) + struct.pack("!HHIH", 1, 1, 300, 4) + socket.inet_aton(ip)
            header = struct.pack("!6H", qid, 0x8400 | rcode, 1, 1, 0, 0)
            sock.sendto(header + question + ans, addr)
        else:                                    # NXDOMAIN 或 NODATA：authority 放 SOA
            header = struct.pack("!6H", qid, 0x8400 | rcode, 1, 0, 1, 0)
            sock.sendto(header + question + soa_rr(), addr)


class CachingResolver:
    def __init__(self, server):
        self.server, self.cache, self.next_id = server, {}, 1

    def lookup(self, name, qtype, now):
        key = (name, qtype)
        if key in self.cache and self.cache[key][0] > now:
            expires, result = self.cache[key]
            return result + f"（快取，剩 {expires - now} 秒）"
        query = struct.pack("!6H", self.next_id, 0x0100, 1, 0, 0, 0) + encode_name(name) + struct.pack("!HH", qtype, 1)
        self.next_id += 1
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2)
            s.sendto(query, self.server)
            msg, _ = s.recvfrom(512)
        _, flags, _, an, ns, _ = struct.unpack("!6H", msg[:12])
        off = read_name(msg, 12)[1] + 4
        _, off = read_name(msg, off)
        rtype, _, ttl, rdlen = struct.unpack("!HHIH", msg[off:off + 10])
        rdata = msg[off + 10:off + 10 + rdlen]
        if an:
            result, cache_ttl = f"A {socket.inet_ntoa(rdata)}", ttl
        else:                                    # RFC 2308：負面 TTL 取 SOA TTL 與 MINIMUM 的較小者
            minimum = struct.unpack("!I", rdata[-4:])[0]
            cache_ttl = min(ttl, minimum)
            result = "NXDOMAIN" if flags & 0xF == 3 else "NODATA（名稱存在、沒有這個 type）"
        self.cache[key] = (now + cache_ttl, result)
        return result + f"（問權威，快取 {cache_ttl} 秒）"


srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
srv.bind(("127.0.0.1", 0))
thread = threading.Thread(target=serve, args=(srv,))
thread.start()
r = CachingResolver(srv.getsockname())
new = "classroom-v2.shengsheng.example"
steps = [
    (0, new, 1, "上線前有人先查了一次"),
    (60, None, None, "維運在權威端新增 A 紀錄"),
    (120, new, 1, "正式上線，學生開始連"),
    (901, new, 1, "負面快取過期"),
    (905, "live.shengsheng.example", 28, "查 live 的 AAAA"),
]
log = []
for now, name, qtype, note in steps:
    if name is None:
        records[(new, 1)] = "203.0.113.80"
        print(f"t={now:>4}s  {note}")
        continue
    result = r.lookup(name, qtype, now)
    log.append(result)
    print(f"t={now:>4}s  {note:<16} -> {result}")
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(b"stop", srv.getsockname())               # 通知 server thread 結束
thread.join()
srv.close()
assert log[1].startswith("NXDOMAIN（快取") and log[2].startswith("A 203.0.113.80")
assert log[3].startswith("NODATA") and len(queries_seen) == 3
print(f"權威端只收到 {len(queries_seen)} 次查詢：{queries_seen}")
```

```text
t=   0s  上線前有人先查了一次       -> NXDOMAIN（問權威，快取 900 秒）
t=  60s  維運在權威端新增 A 紀錄
t= 120s  正式上線，學生開始連       -> NXDOMAIN（快取，剩 780 秒）
t= 901s  負面快取過期           -> A 203.0.113.80（問權威，快取 300 秒）
t= 905s  查 live 的 AAAA    -> NODATA（名稱存在、沒有這個 type）（問權威，快取 900 秒）
權威端只收到 3 次查詢：[('classroom-v2.shengsheng.example', 1), ('classroom-v2.shengsheng.example', 1), ('live.shengsheng.example', 28)]
```

逐行看輸出。t=0 時 `classroom-v2` 還不存在，權威端回 NXDOMAIN 並附上 SOA，resolver 依 min(3600, 900) 決定快取 900 秒。t=60 時維運新增了紀錄，但 t=120 的查詢直接從快取回答「不存在」，剩 780 秒，權威端根本沒被問到。到 t=901 負面快取過期，resolver 回源，才拿到 203.0.113.80。最後一次查 `live` 的 AAAA 得到 NODATA：名稱存在、rcode 是 NOERROR、answer 是空的，同樣依 SOA 快取 900 秒。最下面的查詢紀錄證實，權威端在整段期間只收到 3 次查詢，t=120 那次完全被快取吸收。

### 模擬三：weighted、GeoDNS 與 health check

第三段程式模擬一個帶有策略的權威 DNS：依來源判斷地區、依權重挑選端點，並依 health check 結果移除故障節點：

```python
import ipaddress
import random

# 權威端的「地理資料庫」：用文件用位址假裝不同地區
GEO_DB = {
    ipaddress.ip_network("198.51.100.0/24"): "asia",   # 台灣 ISP 的使用者與 resolver
    ipaddress.ip_network("192.0.2.0/24"): "us",        # 位在美國的公共 resolver
}
POOLS = {
    # 換 CDN 的最後階段：新 CDN 亞洲 edge 90、舊 CDN edge 10（舊的還沒停，順便當退路）
    "asia": [{"ip": "203.0.113.10", "weight": 90}, {"ip": "198.51.100.7", "weight": 10}],
    "us": [{"ip": "203.0.113.11", "weight": 100}],          # 新 CDN 的美國 edge
}
health = {"203.0.113.10": 0, "198.51.100.7": 0, "203.0.113.11": 0}  # 連續失敗次數
FAIL_THRESHOLD = 3


def region_of(resolver_ip, ecs_subnet=None):
    """有 ECS 就用使用者子網判斷，否則只能用 resolver 自己的位址。"""
    addr = ipaddress.ip_network(ecs_subnet) if ecs_subnet else ipaddress.ip_network(resolver_ip)
    for net, region in GEO_DB.items():
        if addr.subnet_of(net):
            return region
    return "us"


def answer(resolver_ip, rng, ecs_subnet=None):
    pool = POOLS[region_of(resolver_ip, ecs_subnet)]
    healthy = [e for e in pool if health[e["ip"]] < FAIL_THRESHOLD]
    candidates = healthy or pool          # 全部不健康時 fail open，總比回空答案好
    weights = [e["weight"] for e in candidates]
    return rng.choices(candidates, weights=weights)[0]["ip"]


rng = random.Random(15)
counts = {}
for _ in range(10_000):
    ip = answer("198.51.100.53", rng)
    counts[ip] = counts.get(ip, 0) + 1
print("1) weighted（新 CDN 90、舊 CDN 10）回答 10000 次：", counts)
assert 8800 < counts["203.0.113.10"] < 9200

print("2) GeoDNS 只看得到 resolver：")
print("   台灣 ISP resolver 198.51.100.53         ->", region_of("198.51.100.53"))
print("   美國公共 resolver 192.0.2.53（無 ECS）  ->", region_of("192.0.2.53"))
print("   美國公共 resolver 帶 ECS 198.51.100.0/24 ->", region_of("192.0.2.53", "198.51.100.0/24"))
assert region_of("192.0.2.53", "198.51.100.0/24") == "asia"

print("3) health check 每 10 秒一次，連續 3 次失敗才移除；resolver 快取 TTL 60 秒")
TTL, INTERVAL = 60, 10
# 最倒楣的時機：resolver 在 t=40 s 剛回源（還沒移除），拿到新 CDN 的亞洲 edge 並快取 60 秒
cached_ip, cache_expires, removed_at, recovered_at = "203.0.113.10", 100, None, None
for now in range(30, 200, INTERVAL):
    health["203.0.113.10"] += 1                     # t=30 s 起亞洲 edge 每次檢查都失敗
    if health["203.0.113.10"] == FAIL_THRESHOLD:
        removed_at = now
        print(f"   t={now:>3}s 連續失敗 {FAIL_THRESHOLD} 次，權威端不再回答 203.0.113.10")
    if now >= cache_expires:                        # resolver 快取過期才會回頭問權威
        cached_ip, cache_expires = answer("198.51.100.53", rng), now + TTL
        if recovered_at is None and cached_ip != "203.0.113.10":
            recovered_at = now
            print(f"   t={now:>3}s resolver 快取過期，重新查詢拿到 {cached_ip}")
print(f"   故障 t=30s -> 使用者在 t={recovered_at}s 才離開故障節點，共 {recovered_at - 30} 秒")
assert removed_at == 50 and recovered_at - 30 <= FAIL_THRESHOLD * INTERVAL + TTL

for ip in health:
    health[ip] = FAIL_THRESHOLD                     # 假設 health checker 自己的網路斷了
print("4) 全部判定不健康時 fail open ->", answer("198.51.100.53", rng))
```

```text
1) weighted（新 CDN 90、舊 CDN 10）回答 10000 次： {'198.51.100.7': 982, '203.0.113.10': 9018}
2) GeoDNS 只看得到 resolver：
   台灣 ISP resolver 198.51.100.53         -> asia
   美國公共 resolver 192.0.2.53（無 ECS）  -> us
   美國公共 resolver 帶 ECS 198.51.100.0/24 -> asia
3) health check 每 10 秒一次，連續 3 次失敗才移除；resolver 快取 TTL 60 秒
   t= 50s 連續失敗 3 次，權威端不再回答 203.0.113.10
   t=100s resolver 快取過期，重新查詢拿到 198.51.100.7
   故障 t=30s -> 使用者在 t=100s 才離開故障節點，共 70 秒
4) 全部判定不健康時 fail open -> 198.51.100.7
```

第 1 部分是 weighted：一萬次回答中約 90% 是新 CDN、約 10% 是舊 CDN，符合 90 比 10 的權重；但如前面所說，真實流量的比例還要乘上每台 resolver 背後的使用者數，會比這裡粗糙。第 2 部分是 GeoDNS 的限制：同一位台灣的學生，透過台灣 ISP 的 resolver 被判為 asia；改用美國的公共 resolver 且沒有 ECS，就被判為 us；同一台 resolver 帶上 ECS 子網後，又正確判為 asia。

第 3 部分重現 15.6 節的時間軸：新 CDN 的亞洲 edge 在 t=30 故障，連續三次失敗後在 t=50 被移除，但 resolver 在 t=40 剛回源並快取 60 秒，使用者一直到 t=100 才拿到備援的舊 CDN edge 198.51.100.7，總共受影響 70 秒，沒有超過「檢查間隔 × 門檻 + TTL」的 90 秒上限。這也說明了為什麼搬遷期間要保留舊 CDN：它在這裡就是故障時的退路。第 4 部分把所有端點都標成不健康，模擬 health checker 自己出問題的情況；程式選擇 fail open，照權重回答，而不是回空答案。

### 模擬四：DNSSEC 信任鏈

最後一段用 Python 建立 root、`example.` 與 `shengsheng.example.` 三層 zone，每層有 KSK 與 ZSK，父區放子區的 DS，然後從 trust anchor 往下驗證。程式裡的 DNSKEY、DS 與 RRSIG 欄位布局、key tag 計算（RFC 4034 附錄 B 的演算法）、DS 的 SHA-256 摘要都照真實格式；**唯一刻意替換的是簽章本身：用 HMAC 代替非對稱簽章**。這只是為了讓程式能只用標準函式庫執行；HMAC 是對稱的，驗證者拿到的「公鑰」其實就是能產生簽章的金鑰，所以它完全不具備真實 DNSSEC 的安全性，只用來展示信任鏈的結構。演算法欄位填 253，這是保留給私有演算法的編號，用來標明它不是真的演算法：

```python
# 教學模擬：真實 DNSSEC 用非對稱簽章（ECDSA、Ed25519、RSA），驗證者只需要公鑰。
# 這裡為了只用標準函式庫，用 HMAC 代替簽章；HMAC 的金鑰一旦公開誰都能偽造，
# 所以這段只示範「信任鏈怎麼串」，絕不能當成真的安全機制。
import hashlib
import hmac
import struct

ALG = 253            # 253 是保留給私有演算法的編號，用來標明這不是真演算法
NOW = 1_790_000_000  # 模擬時鐘（Unix time）


def wire(name):
    labels = [p for p in name.rstrip(".").split(".") if p]
    return b"".join(bytes([len(p)]) + p.lower().encode() for p in labels) + b"\x00"


def key_tag(rdata):
    """RFC 4034 附錄 B 的 key tag 計算（真實演算法）。"""
    acc = sum(b << 8 if i % 2 == 0 else b for i, b in enumerate(rdata))
    return (acc + (acc >> 16)) & 0xFFFF


def dnskey(flags, secret):
    return struct.pack("!HBB", flags, 3, ALG) + secret      # 257 = KSK，256 = ZSK


def make_ds(owner, key_rdata):
    """DS = 父區對子區 KSK 的摘要；digest type 2 = SHA-256（真實格式）。"""
    digest = hashlib.sha256(wire(owner) + key_rdata).digest()
    return struct.pack("!HBB", key_tag(key_rdata), ALG, 2) + digest


def rrset_bytes(owner, rtype, ttl, rdatas):
    return b"".join(wire(owner) + struct.pack("!HHIH", rtype, 1, ttl, len(r)) + r for r in sorted(rdatas))


def sign(owner, rtype, ttl, rdatas, key_rdata, signer, expire=NOW + 86400):
    labels = len([p for p in owner.split(".") if p])     # RRSIG 的 Labels 欄位：root 為 0
    header = struct.pack("!HBBIIIH", rtype, ALG, labels, ttl, expire, NOW - 3600, key_tag(key_rdata))
    data = header + wire(signer) + rrset_bytes(owner, rtype, ttl, rdatas)
    return {"header": header, "signer": signer, "sig": hmac.new(key_rdata[4:], data, "sha256").digest()}


def verify(owner, rtype, ttl, rdatas, rrsig, keys):
    rtype_c, _, _, _, expire, inception, tag = struct.unpack("!HBBIIIH", rrsig["header"])
    if not inception <= NOW <= expire:
        return "簽章不在有效期間"
    key = next((k for k in keys if key_tag(k) == tag), None)
    if key is None:
        return f"找不到 key tag {tag} 的 DNSKEY"
    data = rrsig["header"] + wire(rrsig["signer"]) + rrset_bytes(owner, rtype, ttl, rdatas)
    if not hmac.compare_digest(hmac.new(key[4:], data, "sha256").digest(), rrsig["sig"]):
        return "RRSIG 與資料不符"
    return None


def build_zone(name, parent=None, ksk_secret=None):
    ksk = dnskey(257, ksk_secret or hashlib.sha256(b"ksk" + name.encode()).digest())
    zsk = dnskey(256, hashlib.sha256(b"zsk" + name.encode()).digest())
    zone = {"name": name, "keys": [ksk, zsk], "ksk": ksk, "zsk": zsk, "rrsets": {}}
    zone["keys_sig"] = sign(name, 48, 3600, zone["keys"], ksk, name)    # 48 = DNSKEY，由 KSK 簽
    if parent:
        add_rrset(parent, name, 43, [make_ds(name, ksk)])               # 43 = DS，放在父區
    return zone


def add_rrset(zone, owner, rtype, rdatas, expire=NOW + 86400):
    zone["rrsets"][(owner, rtype)] = (rdatas, sign(owner, rtype, 300, rdatas, zone["zsk"], zone["name"], expire))


def validate(chain, owner, rtype, trust_anchor):
    """從 root 往下走：DS 認可 DNSKEY，DNSKEY 驗證下一層 DS 或最終答案。"""
    trusted_ds = [trust_anchor]
    for depth, zone in enumerate(chain):
        if not trusted_ds:
            return "INSECURE", f"{zone['name']} 沒有 DS，這一段以下沒有簽章保護"
        anchored = [k for k in zone["keys"] if k[1] == 1 and make_ds(zone["name"], k) in trusted_ds]
        if not anchored:
            return "BOGUS", f"{zone['name']} 的 DNSKEY 對不上父區的 DS"
        # DNSKEY RRset 必須由「被 DS 認可的那把 KSK」簽，才能把信任延伸到 ZSK
        if (err := verify(zone["name"], 48, 3600, zone["keys"], zone["keys_sig"], anchored)):
            return "BOGUS", f"{zone['name']} DNSKEY：{err}"
        target = chain[depth + 1]["name"] if depth + 1 < len(chain) else None
        rdatas, rrsig = zone["rrsets"].get((target, 43) if target else (owner, rtype), ([], None))
        if rrsig is None and not target:
            return "BOGUS", f"{zone['name']} 已簽章，答案卻沒有 RRSIG"
        # 簡化：真實驗證器要用 NSEC/NSEC3 證明「父區確實沒有 DS」才能判為 INSECURE
        if rrsig and (err := verify(target or owner, 43 if target else rtype, 300, rdatas, rrsig, zone["keys"])):
            return "BOGUS", f"{zone['name']} 的{'DS' if target else '答案'}：{err}"
        trusted_ds = rdatas if target else None
    return "SECURE", "每一段簽章都驗證通過"


def scenario(label, tamper=None):
    root = build_zone(".")
    tld = build_zone("example.", root)
    child = build_zone("shengsheng.example.", tld)
    add_rrset(child, "api.shengsheng.example.", 1, [bytes([203, 0, 113, 80])])
    anchor = make_ds(".", root["ksk"])        # resolver 內建的 trust anchor
    if tamper:
        tamper(root, tld, child)
    status, why = validate([root, tld, child], "api.shengsheng.example.", 1, anchor)
    rcode = "SERVFAIL" if status == "BOGUS" else "NOERROR"
    print(f"{label:<22} {status:<8} -> {rcode:<8} {why}")
    return status


def forge_answer(root, tld, child):        # 路徑中間有人改了答案，但沒有私鑰重簽
    rdatas, rrsig = child["rrsets"][("api.shengsheng.example.", 1)]
    child["rrsets"][("api.shengsheng.example.", 1)] = ([bytes([192, 0, 2, 66])], rrsig)


def new_provider_no_ds_update(root, tld, child):   # 換 DNS 供應商，新 KSK 沒更新到父區
    fresh = build_zone("shengsheng.example.", None, ksk_secret=b"new-provider-ksk")
    child.update({k: fresh[k] for k in ("keys", "ksk", "zsk", "keys_sig")})
    add_rrset(child, "api.shengsheng.example.", 1, [bytes([203, 0, 113, 80])])


def expired(root, tld, child):              # 自動重簽的排程壞了好幾天
    add_rrset(child, "api.shengsheng.example.", 1, [bytes([203, 0, 113, 80])], expire=NOW - 60)


def unsigned_child(root, tld, child):       # 父區沒有 DS：這個網域根本沒啟用 DNSSEC
    del tld["rrsets"][("shengsheng.example.", 43)]


results = [
    scenario("1 正常"),
    scenario("2 答案被竄改", forge_answer),
    scenario("3 換供應商沒更新 DS", new_provider_no_ds_update),
    scenario("4 RRSIG 過期", expired),
    scenario("5 子區未簽", unsigned_child),
]
print("root KSK key tag =", key_tag(build_zone(".")["ksk"]), "（每次執行相同，因為金鑰由固定字串導出）")
assert results == ["SECURE", "BOGUS", "BOGUS", "BOGUS", "INSECURE"]
```

```text
1 正常                   SECURE   -> NOERROR  每一段簽章都驗證通過
2 答案被竄改                BOGUS    -> SERVFAIL shengsheng.example. 的答案：RRSIG 與資料不符
3 換供應商沒更新 DS           BOGUS    -> SERVFAIL shengsheng.example. 的 DNSKEY 對不上父區的 DS
4 RRSIG 過期             BOGUS    -> SERVFAIL shengsheng.example. 的答案：簽章不在有效期間
5 子區未簽                 INSECURE -> NOERROR  shengsheng.example. 沒有 DS，這一段以下沒有簽章保護
root KSK key tag = 64580 （每次執行相同，因為金鑰由固定字串導出）
```

五個情境對應五種真實世界的狀況。情境 1 一路驗證通過，結果 SECURE，resolver 回 NOERROR 並會設 AD 位元。情境 2 模擬路徑上有人把 A 紀錄換成 192.0.2.66，但沒有私鑰可以重簽，於是 RRSIG 與資料對不上，結果 BOGUS，resolver 回 SERVFAIL：使用者拿不到答案，但也不會被導到錯誤的 IP。情境 3 就是 Rita 擔心的事故：換了 DNS 供應商、用了新的 KSK，父區的 DS 卻還是舊的，信任鏈在 `shengsheng.example.` 這一層斷掉；注意這時 zone 內容完全正確，錯的是父區那一筆 DS。情境 4 是簽章過期，常見於自動重簽排程失效。情境 5 是父區沒有 DS，代表這個網域沒有啟用 DNSSEC，結果是 INSECURE，照一般 DNS 回答。最後一行印出 root KSK 的 key tag；因為金鑰由固定字串導出，每次執行都相同。

## 15.13 在工作上怎麼用

**後端與 SRE：換 IP、換 LB 或換 CDN 的檢查清單。**聲聲 Live 把第 14 章與這次的教訓合寫成一份搬遷 runbook，之後每次換 LB、換 CDN、換雲端區域都照著走：

1. 盤點：列出要改的所有名稱（含 apex、www、api、內部 view），記下每筆的目前 TTL 與父區 NS 的 TTL。
2. 降 TTL：至少在切換前「一個舊 TTL 加緩衝」降到 60–300 秒，只改 TTL、不改值。
3. 確認：用 `dig @每一台權威伺服器` 確認 serial 與新 TTL 都到位；從幾個不同的公共 resolver 查詢，看回應的 TTL 已不超過新值。
4. 切換：建議用 weighted 紀錄先導一小部分流量到新節點，觀察錯誤率與延遲，再逐步提高。
5. 保留舊節點：監控舊節點的請求數與連線數，降到接近零才關閉；對長連線服務（WebSocket），讓舊節點主動送出關閉並讓 client 重連。
6. 收尾：把 TTL 調回正常值；更新內部 view；記錄實際花了多久。

常用的觀察指令：

```bash
# 從不同的 resolver 看到的答案與剩餘 TTL（第二欄就是剩餘秒數）
dig +noall +answer www.shengsheng.example A @192.0.2.53
# 直接問權威伺服器，跳過所有快取；+norec 表示不要求遞迴
dig +norec +noall +answer www.shengsheng.example A @ns1.shengsheng.example
# 比對每一台權威伺服器的 SOA serial，確認 secondary 已同步
dig +short SOA shengsheng.example @ns1.shengsheng.example
# 從 root 一路追委派，找出哪一層的 NS 或 DS 有問題
dig +trace www.shengsheng.example
# 看 DNSSEC 紀錄與 AD 位元
dig +dnssec www.shengsheng.example A
```

**新服務上線：先建紀錄，後查詢。**前端或後端要上線新子網域時，DNS 紀錄要在任何健康檢查、監控探測或 CI 測試開始前就建立，避免負面快取。上線前把 SOA 的 MINIMUM 與 TTL 檢查一遍：負面快取設成 300 到 900 秒是常見的折衷。

**資安：DNS 的資產與變更監控。**Rita 定期執行三件事：第一，監控 `shengsheng.example` 的 NS 與 DS 紀錄，任何變更都觸發告警；第二，掃描所有 CNAME，把目標與雲端資源清單比對，找出 dangling 紀錄；第三，維護 CAA 紀錄，只允許聲聲 Live 實際使用的 CA 簽發憑證，並搭配 Certificate Transparency 監控（第 19 章）。註冊商帳號一律啟用 MFA，重要網域申請 registry lock。

**啟用 DNSSEC 的營運重點。**優先選擇能自動簽章、自動輪替 ZSK 的 DNS 供應商；選用演算法 13 或 15；把「RRSIG 距離過期還有多久」列為監控指標，低於門檻就告警；換供應商或換 KSK 時，照「新 DS 先上、等快取過期、再撤舊 DS」的順序，並在每一步用 `dig +dnssec` 與 `+cd` 對照確認。

**企業網路與 DoH。**如果公司依賴 split-horizon 或 DNS 過濾，要用裝置管理政策設定瀏覽器的 DoH 行為，或讓內部 resolver 本身提供 DoH／DoT，而不是期待使用者別開。

## 15.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 改了 A 紀錄後，部分使用者幾小時還連舊 IP | 改之前的 TTL 很長，各地 resolver 快取未過期 | 從使用者的 resolver 查詢，看回應的剩餘 TTL；檢查舊節點流量 | 下次先降 TTL 並等一個舊 TTL；這次只能保留舊節點直到流量歸零 |
| DNS 已回新 IP，使用者仍連到舊節點 | 長連線未斷、程式或 runtime 自己快取 IP | 舊節點上看連線的建立時間；檢查 client 程式的 DNS 快取設定 | 讓舊節點優雅關閉連線；調整 runtime 快取（第 16 章） |
| 新建的子網域一直 NXDOMAIN | 建立前被查過，負面快取未過期 | `dig @權威` 有答案、`dig @resolver` 仍 NXDOMAIN；看 SOA MINIMUM | 等待負面快取過期；流程上先建紀錄後查詢 |
| 整個網域突然對部分使用者 SERVFAIL | DNSSEC 驗證失敗：DS 不符、簽章過期 | `dig +cd` 有答案；看 EDE；用 DNSSEC 分析工具檢查信任鏈 | 修正父區 DS 或重新簽章；必要時暫時撤下 DS（需等 DS 的 TTL） |
| 裸網域無法設定 CNAME | apex 必須有 SOA、NS，CNAME 不能和其他紀錄共存 | DNS 後台或 zone 檢查工具報錯 | 用 ALIAS／flattening、雲端 alias record，或直接寫 A／AAAA |
| 辦公室和外部使用者看到不同 IP | split-horizon 的內外 zone 不一致 | 分別 `dig @內部 resolver` 與 `dig @公共 resolver` 比對 | 兩份 zone 納入同一變更流程與工具 |
| 不同時間查詢，答案在新舊之間跳動 | secondary 權威伺服器沒同步（NOTIFY 被擋） | 比對每台權威伺服器的 SOA serial | 修正 NOTIFY 與 zone transfer 的網路設定 |
| GeoDNS 把台灣使用者導到美國 | 使用者用的公共 resolver 在國外且沒帶 ECS | 比對 resolver 位置與答案；看權威端記錄的 ECS | 接受誤差並以 anycast 或 CDN 補足；評估 ECS 的隱私取捨 |
| 辦公室筆電查不到內部名稱 | 瀏覽器自行使用公共 DoH resolver | 瀏覽器內部 DNS 頁面或設定顯示 DoH 已啟用 | 以裝置管理政策設定 DoH；內部 resolver 提供 DoH |

## 15.15 動手練習

1. **延伸模擬一：找出安全的關機時間。**修改 TTL 模擬程式，把 10% 墊高下限的 resolver 改成 2%、下限改成 7200 秒，並加入一個「5% 使用者持有長連線、在切換後 0 到 6 小時內均勻重連」的模型，計算舊 CDN 的流量何時降到 0.1% 以下。
   *答案要點*：墊高下限決定了 DNS 層的最壞時間（約 2 小時）；長連線讓舊 CDN 的尾巴延長到 6 小時。結論是關機時間要看實際流量，而不是只看 TTL。

2. **延伸模擬二：NXDOMAIN 與 NODATA 分開快取。**在負面快取程式中新增一筆 `www` 的 AAAA 紀錄，觀察先前快取的 NODATA 要多久才會消失；再把 SOA 的 TTL 改成 300，看負面快取時間怎麼變。
   *答案要點*：NODATA 的快取 key 是（名稱、type），新增 AAAA 後仍要等 900 秒；SOA TTL 改成 300 後，min(300, 900) = 300。

3. **用真實工具觀察 TTL 倒數。**挑一個常見的網站名稱，對同一個公共 resolver 連續執行兩次 `dig +noall +answer`，間隔 10 秒，比較第二欄的 TTL；再用 `dig +norec` 直接問它的權威伺服器（用 `dig NS` 查出來），看權威端給的原始 TTL。
   *驗證方法*：resolver 回的 TTL 會遞減約 10；權威伺服器回的 TTL 是固定的設定值。若兩次 TTL 差異不是 10，可能是查到 resolver 的不同節點（anycast 後面有很多台）。

4. **觀察 DNSSEC 旗標。**對一個已簽章的網域執行 `dig +dnssec`，找出 RRSIG 的過期時間與 key tag，並確認 flags 裡有沒有 `ad`；再用 `dig DS` 查它在父區的 DS，比對 key tag 是否等於 `dig DNSKEY` 中 flags 為 257 那把金鑰。
   *驗證方法*：DS 的 key tag 應該能在 DNSKEY 中找到 flags 257 的對應金鑰；若你的 resolver 不做驗證，`ad` 不會出現，換一個會驗證的 resolver 再試。

5. **延伸模擬四：模擬 KSK 輪替。**在 DNSSEC 程式中寫一個新情境：子區產生新 KSK，父區同時放新舊兩筆 DS，子區的 DNSKEY RRset 同時包含新舊 KSK；確認驗證仍是 SECURE。接著移除舊 KSK、保留舊 DS，再移除舊 DS，觀察每一步的結果。
   *答案要點*：只要父區的 DS 中至少有一筆對得上「簽了 DNSKEY RRset 的那把 KSK」，驗證就會通過；順序做錯（先撤新 DS 或 KSK 先換再補 DS）就會出現 BOGUS。

6. **設計題：聲聲 Live 的 apex。**寫下讓 `shengsheng.example` 和 `www.shengsheng.example` 都能連到新 CDN 的設定方案，說明你選擇 ALIAS、雲端 alias record、HTTPS record 還是固定 A 紀錄，以及下次換 CDN 時要做什麼。
   *答案要點*：常見答案是 www 用 CNAME，apex 用供應商的 ALIAS 或 alias record，並可再加 HTTPS record 給支援的 client；若用固定 A 紀錄，要有流程在 CDN edge 的 IP 變動時同步更新。

## 本章重點整理

- DNS 沒有推播，「傳播」其實是各地快取各自等 TTL 過期；最壞要等多久，取決於改之前那筆紀錄的 TTL。
- 守規矩的快取會往下傳遞剩餘 TTL，所以多層快取不會讓時間疊加；真正拉長時間的是墊高 TTL 下限的 resolver、程式自己快取 IP，以及不會重新解析的長連線。
- 搬遷的正確順序是：至少提前一個舊 TTL 降 TTL、切換、保留舊節點直到實際流量歸零、再調回 TTL；在切換前一刻才降 TTL 等於沒降。
- TTL 越低變更越快，但查詢量越高、越依賴權威 DNS 的可用性；不同用途的紀錄應選不同的 TTL。
- NXDOMAIN 表示名稱不存在，NODATA 表示名稱存在但沒有該 type；兩者都會被負面快取，時間是 SOA 的 TTL 與 MINIMUM 取較小值。
- CNAME 不能與同名的其他紀錄共存，所以不能放在 apex；替代方案有供應商的 ALIAS／flattening、雲端 alias record、HTTPS record 的 AliasMode，或直接寫 A／AAAA。
- 刪除雲端資源時要同時刪除指向它的 CNAME，否則會留下可能被他人認領的 dangling 紀錄。
- DNS 分流（round robin、weighted、GeoDNS）的決策單位是 resolver 與 TTL，比 load balancer 粗糙；GeoDNS 看到的是 resolver 的位置，ECS 能改善準確度但有隱私代價。
- 搭配 health check 的 DNS 故障切換，最壞時間約為「檢查間隔 × 失敗門檻 ＋ TTL」，全部不健康時通常選擇 fail open。
- Split-horizon DNS 讓內外看到不同答案，變更時必須同時更新兩份 zone，除錯時要明確指定 resolver。
- Cache poisoning 的防禦是增加偽造回應需要猜中的隨機性（來源 port、0x20）並限制可快取的資料（bailiwick），根本解法是 DNSSEC。
- DNSSEC 以 DS → DNSKEY（KSK）→ DNSKEY（ZSK）→ RRSIG 的信任鏈保護資料的完整性與來源，不提供機密性；驗證失敗時 resolver 回 SERVFAIL。
- DNSSEC 最常見的事故是簽章過期與換供應商時 DS 沒同步；用 `dig +cd` 對照可以快速判斷是否為驗證失敗。
- DoT 與 DoH 加密的是 stub 到 resolver 這一段，DNSSEC 驗證的是資料本身，兩者互補；DoH 可能繞過企業的內部 resolver，需要用政策協調。

## 延伸問答

> [!question]- Q1. DNSSEC 和 DoH 都說能防止 DNS 被竄改，兩者有什麼不同？只開其中一個夠嗎？
> DoH（以及 DoT）保護的是「stub resolver 到 recursive resolver」這一段傳輸：路上的人看不到你查了什麼，也無法在途中修改回應。但它無法判斷 resolver 給的答案本身是否正確；如果 resolver 的快取已經被投毒，DoH 會把錯誤答案加密後安全地送到你手上。
>
> DNSSEC 則讓資料本身帶有簽章，不論資料經過多少台 resolver、走哪條路，只要驗證者能從 trust anchor 一路驗到答案，就能確定資料來自 zone 擁有者。但 DNSSEC 不加密，查詢內容仍然公開；而且多數使用者的裝置不自己驗證，只相信 resolver 設的 AD 位元，所以 resolver 到裝置這段仍需要 DoH／DoT 才有完整性保護。兩者解決不同層次的問題，最完整的做法是 zone 簽 DNSSEC、resolver 驗證、client 用加密 DNS 連到 resolver。

> [!question]- Q2. 手算：TTL 原本是 3600 秒，你在 10:00 把 TTL 改成 60 秒，10:30 把 IP 換掉。最壞情況下，什麼時候所有守規矩的 resolver 都會回答新 IP？
> 關鍵是「降 TTL」這個動作本身要等快取過期才生效。某台 resolver 可能在 09:59:59 剛好快取了 TTL 3600 的舊版本，這份快取要到 10:59:59 左右才過期。所以在 10:30 換 IP 時，這台 resolver 仍拿著 TTL 3600 的舊資料，最快也要 10:59:59 才會回源拿到新 IP。
>
> 而在 10:00 之後回源的 resolver，拿到的是 TTL 60 的版本，10:30 換 IP 後最多 60 秒就會改答新 IP。所以最壞時間由最早那份舊快取決定：約 11:00（10:00 加一個舊 TTL），而不是 10:31。如果要讓 10:30 的切換最壞只等 60 秒，就要在 09:30 以前降 TTL，也就是至少提前一個舊 TTL。這也是本章模擬中策略 B 失敗的原因。

> [!question]- Q3. 你在 production 看到：DNS 查詢回 NXDOMAIN，但你直接問權威伺服器（dig +norec @ns1）卻有答案。可能的原因有哪些？怎麼確認？
> 最常見的原因是負面快取：在紀錄建立之前，有人（健康檢查、CI、使用者）透過這台 resolver 查過，resolver 記下了「不存在」，時間由 SOA 的 TTL 與 MINIMUM 取較小值決定。確認方法是看 resolver 回應中 authority section 的 SOA，其 TTL 會隨時間遞減，代表正在倒數的負面快取。
>
> 其他可能包括：你問的權威伺服器和 resolver 實際問到的不是同一台（secondary 尚未同步，比對每台權威伺服器的 SOA serial 即可確認）；split-horizon 讓 resolver 走了另一份 zone；或是作業系統的 search domain 讓實際查詢的名稱多了後綴（第 16 章），在 resolver 端看到的查詢名稱就不同了。依序排除這幾項，通常就能找到原因。

> [!question]- Q4. 為什麼 zone apex 不能放 CNAME？ALIAS／flattening 是怎麼繞過這個限制的？它有什麼副作用？
> DNS 規定一個名稱如果有 CNAME，就不能再有其他紀錄，因為 CNAME 的意思是「這個名字的所有資料都去另一個名字找」，同名若還有 MX 或 TXT 就會矛盾。apex 必須有 SOA 與 NS 才能構成 zone，所以 apex 一定違反這條規則，無法放 CNAME。
>
> ALIAS／flattening 是 DNS 供應商在權威端的功能：設定上寫「apex 指向某個主機名稱」，實際收到查詢時由供應商自己解析目標，把得到的 A／AAAA 當作 apex 的答案回出去。resolver 看到的是普通 A 紀錄，所以不違反規則。副作用包括：它綁定特定供應商、不是標準；回給使用者的 TTL 由供應商決定；如果目標本身做了 GeoDNS，判斷依據可能變成供應商解析時的位置，而不是使用者的位置，具體行為依供應商實作而定。

> [!question]- Q5. 面試題：要讓聲聲 Live 某個地區的入口（LB 或 edge）故障時，自動把使用者切到另一個地區，只用 DNS 能做到多快？要更快該怎麼做？
> 只用 DNS 時，切換時間約為「health check 偵測時間 ＋ TTL ＋ client 自己的快取」。假設每 10 秒檢查一次、連續 3 次失敗才移除、TTL 60 秒，最壞約 90 秒，再加上程式或 runtime 自己的快取；部分 resolver 會設 TTL 下限，實際可能更久。縮短間隔與 TTL 能改善，但會增加誤判、探測流量與查詢量，而且有些使用者連到的是已建立的長連線，DNS 改了也不會影響它們。
>
> 要更快，就要讓切換發生在不受快取影響的地方。一種是 anycast（第 6 章）：同一個 IP 由多個地點宣告，故障地點撤回路由宣告後，流量由路由系統導到其他地點，通常比 DNS 快。另一種是讓使用者先連到全球分布的 CDN 或全球 LB（第 25 章），由它們在 L4／L7 層即時改變轉送目標。client 端也可以內建重試與多端點清單。實務上會多層並用，DNS 做地區層級的粗分流與災難切換。

> [!question]- Q6. 換 DNS 供應商時，已經啟用 DNSSEC 的網域要怎麼做才不會讓網域消失？
> 風險在於信任鏈：父區的 DS 記的是舊供應商 KSK 的 hash，如果直接把 NS 改到新供應商，新供應商用自己的 KSK 簽 zone，驗證型 resolver 會發現 DNSKEY 對不上 DS，回 SERVFAIL，網域就對這些使用者消失了。本章模擬四的情境 3 就是這個狀況。
>
> 安全的做法是讓「任何時刻、任何快取組合」都能驗證通過。常見步驟是：在新供應商建好 zone 並簽章；在父區先加上新 KSK 的 DS，與舊 DS 並存；等舊 DS 與 DNSKEY 的快取都過期；再切換 NS，並在新舊兩邊的 DNSKEY RRset 裡互相包含對方的金鑰（多簽者模式），或者依新舊供應商支援的移轉方式進行；最後等 NS 的 TTL 過期，再移除舊 DS。若供應商不支援這類協作，退而求其次的做法是先撤下 DS 讓網域暫時 insecure，等 DS 的 TTL 過期後再換供應商、重新上 DS，但這段期間失去 DNSSEC 保護。

> [!question]- Q7. 看 log 找原因：使用者回報打不開網站，你從對方的網路執行 dig 得到 status: SERVFAIL、EDE: 9 (DNSKEY Missing)，dig +cd 則回傳正確的 A 紀錄。發生了什麼事？
> `+cd` 能拿到答案，代表權威伺服器活著、資料也存在，問題出在 DNSSEC 驗證。EDE 9 表示 resolver 依父區的 DS 去找對應的 DNSKEY，卻在子區的 DNSKEY RRset 裡找不到符合的金鑰。換句話說，父區說「這個網域的 KSK 是某一把」，但 zone 裡已經沒有那一把了。
>
> 典型成因是 KSK 輪替做錯順序（先把舊 KSK 從 zone 移除，父區的 DS 卻還沒換成新的），或是換 DNS 供應商後沒更新 DS。確認方法是用 `dig DS` 查父區的 DS key tag，再用 `dig DNSKEY` 列出 zone 中 flags 為 257 的金鑰與其 key tag，兩者對不上就是原因。修法是在父區更新為正確的 DS，或在 zone 中暫時把舊 KSK 加回去；不論哪一種，都要等相關紀錄的 TTL 過期，使用者端才會恢復。

> [!question]- Q8. 設計取捨：聲聲 Live 的 API 紀錄 TTL 該設多少？請說明你的判斷依據。
> TTL 是「變更速度」與「查詢量、延遲、對權威 DNS 的依賴」之間的取捨。API 的 IP 若由雲端 LB 管理、平常很少變，可以設 300 到 3600 秒；如果搭配 health check 做故障切換，就需要 60 秒左右，讓故障節點能較快被移除。太低（例如 5 秒）時，每個使用者幾乎每次都要等一次解析，部分 resolver 也會套用自己的下限，實際效果有限。
>
> 判斷時可以問幾個問題：這個紀錄多常變更？變更時能否提前規劃降 TTL？DNS 層的故障切換是否真的是主要的高可用機制，還是由 anycast 或全球 LB 負責？權威 DNS 供應商本身的可用性如何，若它故障，較長的 TTL 能讓快取多撐一段時間？對聲聲 Live 來說，合理的答案是平常 300 秒、搬遷期間先降到 60 秒；真正的高可用主要交給 LB 與多地區架構，而不是靠更短的 TTL。

## 延伸閱讀

- RFC 2308〈Negative Caching of DNS Queries (DNS NCACHE)〉
- RFC 4033、RFC 4034、RFC 4035（DNSSEC 的導論、資源紀錄格式與協定修改）
- RFC 9364〈DNS Security Extensions (DNSSEC)〉（BCP 237）
- RFC 7871〈Client Subnet in DNS Queries〉
- RFC 8484〈DNS Queries over HTTPS (DoH)〉與 RFC 7858〈Specification for DNS over Transport Layer Security (TLS)〉
- RFC 9460〈Service Binding and Parameter Specification via the DNS (SVCB and HTTPS Resource Records)〉
- RFC 8914〈Extended DNS Errors〉
- Cricket Liu、Paul Albitz《DNS and BIND》（O'Reilly）
