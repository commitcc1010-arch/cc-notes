---
chapter: 25
title: Proxy、Load Balancer 與 CDN
part: 5
---

# 第 25 章　Proxy、Load Balancer 與 CDN

> [!abstract] 本章地圖
> **核心問題**：一個請求從學生的瀏覽器到 Flask view，中間會經過好幾個「替別人轉送」的程式；它們各自做了什麼決定，又各自會在什麼情況下把事情搞砸？
>
> **你會學到**：
> - 分辨 forward proxy、reverse proxy、L4 與 L7 load balancer、CDN 與 API gateway，說出每一層看得到什麼、能做什麼決定
> - 比較 round robin、least connections、power of two choices 與 hash 類演算法，知道哪一種會在後端變慢時把流量送進黑洞
> - 設計 active 與 passive health check，算出故障被偵測前會損失多少請求
> - 用 consistent hashing 做 sticky session 與快取分片，並知道 sticky 的代價
> - 正確解析 `X-Forwarded-For`／`Forwarded`：只信任已知 proxy 加上的那幾段，從右往左找出真正的 client
> - 解釋 CDN 的 cache key、TTL、purge、request collapsing 與 origin shield，並估算命中率對 origin 的影響
> - 用 Python asyncio 在 127.0.0.1 寫出一個會做 round robin、least connections、health check 與 `X-Forwarded-For` 的 L7 reverse proxy
>
> **前置知識**：第 10 章（TCP 連線與 RST）、第 19 章（TLS 終結的位置）、第 20 章（HTTP/1.1 訊息格式與 keep-alive）、第 21 章（Cache-Control 與 ETag）

## 25.1 故事：美咲講座開場前的二十分鐘

週五晚上八點，日文老師美咲要開一場免費的公開講座，報名人數破了四千，是聲聲 Live 開站以來最大的一場。七點四十分，前端同事發現講座頁的按鈕顏色錯了，改完 CSS 後順手在 CDN 後台按下「Purge Everything」，想確保所有人都拿到新版。七點五十八分，學生開始湧入；八點零二分，告警同時從三個地方響起。

第一個告警是 origin 的請求量：平常 CDN 的命中率超過九成，`www.shengsheng.example` 打回聲聲 Live 自己機房的請求每秒只有六百多個；purge 之後的兩分鐘，所有快取都是空的，回源請求衝到每秒五千八百個。第二個告警是 504：兩台 gunicorn 主機 app-a（10.20.3.21）與 app-b（10.20.3.22）之中，app-b 的資料庫連線池被慢查詢佔滿，worker 全部卡住；但 load balancer 的 health check 只檢查 TCP 8000 port 能不能連上，核心照樣替卡住的 gunicorn 完成交握（第 10 章），所以 app-b 一直被當成健康的，round robin 照樣把一半的請求送過去，然後一律逾時。第三個告警最奇怪：登入 API 對幾乎所有學生回 `429 Too Many Requests`。

小晴負責登入服務，打開 log 一看，每筆請求的 `remote_addr` 都是 `10.20.3.11`，那是 nginx 的位址。上週 Rita 要求登入 API 加上「每個 IP 每分鐘 300 次」的限速，平常晚上全站每分鐘只有一百多次登入，從來沒觸發過；今晚兩千人在同一分鐘登入，而限速器看到的「IP」全都是 nginx，於是所有人共用一個額度。小晴在混亂中把程式改成讀 `X-Forwarded-For` 的第一個值，429 消失了，講座總算順利開始。

```text
 學生 198.51.100.45
   │  HTTPS
   ▼
 CDN edge（203.0.113.10）── ① purge everything：快取全空，命中率從 92% 掉到接近 0
   │  回源（CDN 出口 198.51.100.224/27）
   ▼
 API／應用 LB 203.0.113.80（VPC 內 10.20.16.5）── ② health check 只看 TCP port
   │                                                   app-b 卡死仍被當成健康
   ▼
 nginx 10.20.3.11 ── ③ 對 gunicorn 而言，所有請求都「來自」10.20.3.11
   │
   ├──► app-a 10.20.3.21:8000（gunicorn → Flask）
   └──► app-b 10.20.3.22:8000（worker 全卡在資料庫 10.20.17.15:5432）
```

這是阿德在事後檢討時畫的圖，三個編號就是三個中間人各自犯下的錯。① 是 CDN 層：一次全站 purge 讓 edge 失去所有快取，數千個 edge 請求在同一瞬間回源，origin 從來沒有承受過這種流量。② 是 load balancer 層：health check 問錯了問題，「port 有沒有開」不等於「能不能處理請求」。③ 是信任邊界：經過 proxy 之後，TCP 連線的對端位址只剩最近一跳，真正的 client 位址藏在 header 裡，而那個 header 有一部分是 client 自己可以亂寫的。

隔天早上，Rita 在檢討會上補了一刀：「小晴昨天的修法讓 429 消失了，但現在任何人只要自己帶一個 `X-Forwarded-For: 隨便一個 IP`，每次換一個值，就能無限次嘗試登入。登入限速等於沒有了。」三個問題其實是同一件事：不了解請求路上的每一個 proxy 看到了什麼、改了什麼、相信了什麼。這一章一層一層把這張圖拆開，最後在 127.0.0.1 上親手寫一個 reverse proxy，把三個錯誤都重現並修好。

## 25.2 Proxy：替別人轉送請求的程式

**Proxy**（代理）是一個站在 client 與 server 中間、替其中一方轉送請求的程式。它對 client 而言像 server（接受連線、讀取請求），對 server 而言像 client（建立連線、送出請求）。例如公司辦公室的網路要求所有對外連線都經過一台 proxy，員工的瀏覽器先把請求交給它，它再替員工連到外面的網站。關鍵問題永遠是：這個 proxy 替誰工作？是誰把它放在那裡的？

```text
 forward proxy：替 client 工作（client 知道它存在）
   ┌──────────────── 辦公室 10.40.0.0/24 ────────────────┐
   │ 小晴筆電 ─┐                                          │
   │ Rita 筆電 ─┼──► forward proxy ──────────────────────┼──► 任何網站
   │ 阿德筆電 ─┘   （過濾、稽核、快取）                  │     （看到的來源是 proxy）
   └──────────────────────────────────────────────────────┘

 reverse proxy：替 server 工作（client 通常不知道它存在）
                         ┌──────────── 聲聲 Live ────────────┐
   任何 client ─────────►│ reverse proxy ──┬──► app-a          │
   （以為自己連到的       │ （TLS、分流、   ├──► app-b          │
     就是 server）        │   快取、限速）  └──► 靜態檔案        │
                         └────────────────────────────────────┘
```

上半部是 **forward proxy**（正向代理）。它由 client 這一側設定：瀏覽器或作業系統的 proxy 設定、`HTTPS_PROXY` 環境變數、公司派發的 PAC 檔。它可以替整個辦公室做網址過濾、稽核與快取，目的端網站看到的來源位址是 proxy，而不是每台筆電。下半部是 **reverse proxy**（反向代理），由 server 這一側部署，client 連到 `www.shengsheng.example` 時以為自己在跟 server 說話，其實是 nginx 或 CDN 在替後面的程式接電話。聲聲 Live 架構裡的 CDN、load balancer、nginx、API gateway，全部都是 reverse proxy 的不同形態。

兩者在協定上的差別看得到。送給 forward proxy 的 HTTP 請求，請求行寫的是包含 scheme 與 host 的完整 URL（規格稱為 absolute-form），因為 proxy 需要知道要替你連去哪裡；送給 reverse proxy 的請求跟送給一般 server 一模一樣，只有路徑（origin-form），再加上 `Host` header（第 20 章），reverse proxy 依自己的設定決定往哪裡轉：

```text
送給 forward proxy：   GET http://example.com/status HTTP/1.1
                      Host: example.com

送給 reverse proxy：   GET /status HTTP/1.1
                      Host: www.shengsheng.example
```

兩種寫法的差別只在請求行的第二個欄位。HTTPS 經過 forward proxy 時，client 不能讓 proxy 看到明文，於是改用 `CONNECT` 方法請 proxy 開一條 TCP 隧道：

```text
 小晴筆電                         forward proxy                     api.shengsheng.example
    │── CONNECT api.shengsheng.example:443 HTTP/1.1 ──►│                         │
    │                                                  │── TCP 交握（SYN…）────►│
    │◄─────────── HTTP/1.1 200 Connection Established ─│                         │
    │══════════ TLS ClientHello（SNI 看得到）══════════╪════════════════════════►│
    │◄═════════ TLS 交握、加密的 HTTP 請求與回應 ═══════╪═════════════════════════│
    │           （proxy 只是把 bytes 原封不動地雙向搬運） │                         │
```

第一行是 client 請 proxy 連到 `api.shengsheng.example:443`；proxy 自己完成 TCP 交握後回 `200`，從這一刻起，它不再解析任何內容，只把兩邊的 bytes 互相搬過去。TLS 交握是 client 與真正的 server 直接進行的（第 18 章），所以 proxy 只看得到目的地的名稱與 port，以及 ClientHello 裡的 SNI，看不到 URL 路徑、cookie 或回應內容。企業若想檢查 HTTPS 內容，只能做 **TLS 攔截**：proxy 用公司自己的 CA 即時簽發假憑證，並把這個 CA 安裝到員工電腦上；這屬於政策與信任的決定，也是某些內部工具在公司網路上突然出現憑證錯誤的原因。

還有一種 **transparent proxy**（透明代理）：client 沒有設定任何 proxy，網路設備把封包導向 proxy（常見於學校、旅館與部分行動網路）。它對 client 來說是隱形的，卻可能改寫 header、緩衝回應，造成「在家正常、在學校壞掉」的怪問題，第 31 章的 SSE 與第 32 章的 WebSocket 都會遇到。下表整理三種 proxy 的差別：

| 類型 | 誰部署、誰設定 | client 知道它嗎 | 典型用途 | 聲聲 Live 的例子 |
|---|---|---|---|---|
| forward proxy | client 這一側（公司 IT、使用者） | 知道，要設定 | 對外連線的過濾、稽核、快取 | 辦公室 10.40.0.0/24 的上網 proxy |
| reverse proxy | server 這一側（服務的維運者） | 通常不知道 | TLS 終結、分流、快取、限速、隱藏後端 | CDN、LB、nginx、API gateway |
| transparent proxy | 網路營運者（ISP、學校） | 不知道 | 強制過濾、快取、流量整形 | 某些學校網路，會影響長連線 |

> [!warning] 常見誤解
> 「設了 `HTTPS_PROXY`，HTTPS 的內容就會被 proxy 看光。」不會。一般情況下 client 用 `CONNECT` 開隧道，TLS 在 client 與 server 之間端到端完成，proxy 只看得到目的地名稱與 port。只有在電腦上安裝了 proxy 的 CA、讓 proxy 做 TLS 攔截時，內容才會被解開。另外，Python 的 `urllib` 會讀取 `HTTP_PROXY`、`HTTPS_PROXY` 與 `NO_PROXY`；容器或 CI 裡殘留的 proxy 設定，常讓呼叫內部服務的請求繞到外面去，除錯時先印出這幾個環境變數。

## 25.3 L4 與 L7 load balancer

**Load balancer**（負載平衡器，常簡稱 LB）是一種 reverse proxy，主要工作是把流量分散到一群後端（又稱 upstream 或 backend，例如 app-a、app-b），並在後端故障時把它移出。依照它讀到哪一層的資訊做決定，分成兩大類。**L4 load balancer** 只看 IP 位址與 port（第 9 章的五元組），以「連線」為單位分配：一條 TCP 連線一旦被分到 app-a，這條連線上的所有 bytes 都去 app-a。**L7 load balancer** 會完整讀懂 HTTP，可以依 `Host`、路徑、header、cookie 決定每一個「請求」要去哪裡，例如 `/api/` 送到 API 叢集、`/static/` 送到靜態檔案伺服器。

```text
 L4（以連線為單位，不拆開內容）
   client ══════════ 一條 TCP 連線（seq／ack 可以原樣穿過）══════════► app-a
                 ▲
           L4 LB 只改寫 IP／port 或轉發封包，不讀 HTTP

 L7（以請求為單位，兩條各自獨立的連線）
   client ════ TCP＋TLS 連線 ①（client ↔ LB）════► L7 LB ════ 連線 ②（LB ↔ app，可重用）═══► app-a
                                                        │ 讀完整個 HTTP 請求再決定去哪
                                                        └══ 連線 ③ ════════════════════════► app-b
```

上半部的 L4 LB 對 TCP 連線是「透明」的：它可以只改寫目的位址（NAT 模式），也可以讓後端直接把回應送回 client，不再經過 LB（**DSR**，direct server return，常用在回應流量遠大於請求的影片服務），還可以把原封包包在另一層 IP 裡送到後端（tunnel 模式）。不管哪種模式，L4 LB 都不需要讀懂內容，所以速度快、每台能撐的連線數極大，也能處理 HTTP 以外的協定，例如資料庫、SRT 直播的 UDP、TURN（第 36 章）。下半部的 L7 LB 則是兩條完全獨立的連線：它和 client 完成 TCP 與 TLS 交握、讀完整個 HTTP 請求，再從自己的連線池挑一條通往後端的連線送出去。因為讀得懂 HTTP，它能做路徑分流、加 header、重試、回應壓縮、依請求做限速，代價是每個請求都要解析，CPU 成本高得多。

這個差別在 HTTP/2 與 gRPC 上會變成真正的故障。gRPC 用一條長時間存在的 HTTP/2 連線，在上面多工傳送成千上萬個請求（第 22、24 章）。如果放在 L4 LB 後面，LB 只在連線建立時分配一次，於是某個 client 的所有請求永遠落在同一台後端；後端擴容到十台，新加的九台卻幾乎沒有流量。解法是改用懂 HTTP/2 的 L7 LB，讓它以「stream」為單位分配，或讓 client 自己做負載分散。同樣地，WebSocket 經過 upgrade 之後也是一條長連線（第 32 章），L7 LB 對它只能在 upgrade 那一刻做一次決定，之後就退化成 L4 式的轉送。

| 比較項目 | L4 load balancer | L7 load balancer |
|---|---|---|
| 決策依據 | 五元組（IP、port、協定） | HTTP 的 Host、路徑、header、cookie |
| 分配單位 | 一條連線（UDP 則是一個 flow） | 一個請求（HTTP/2 是一個 stream） |
| TLS | 通常直接穿透，後端自己終結 | 通常在 LB 終結，可選擇對後端重新加密 |
| 後端看到的 client 位址 | 依模式而定：DSR／tunnel 保留原始位址，NAT 模式可能被換掉 | 一定是 LB 的位址，client 位址要靠 header 傳遞 |
| 能做的事 | 分流、health check、連線層級的保護 | 路徑分流、重試、改寫 header、快取、WAF、限速 |
| 常見實作 | Linux IPVS、雲端 L4 LB（例如 AWS NLB）、Google Maglev | nginx、HAProxy、Envoy、雲端 L7 LB（例如 AWS ALB） |
| 適合 | 非 HTTP 協定、極高連線量、要保留 client IP | Web、API、需要依內容分流的服務 |

實務上兩種常常疊在一起：大型網站最外層用 L4 LB（或 anycast，第 6 章）把連線分到一群 L7 proxy，再依請求分到各服務；聲聲 Live 規模較小，雲端 LB 203.0.113.80 直接做 L7 並終結 TLS（第 19 章），後面接 nginx。QUIC 讓 L4 LB 多了一個難題：它跑在 UDP 上，client 換網路時五元組會變，LB 必須改看 QUIC header 裡的 connection ID 才能把封包送回同一台後端（第 13 章）。

### client 位址怎麼穿過 L4：PROXY protocol

L4 LB 若用 NAT 或 full proxy 模式，後端看到的來源位址就變成 LB；而它又不懂 HTTP，無法加上 `X-Forwarded-For`。**PROXY protocol** 是 HAProxy 提出、被廣泛採用的解法：LB 在每條 TCP 連線的最前面，先送一小段描述原始連線的資料，後面才接 client 原本送出的 bytes。後端必須明確啟用並且只接受來自 LB 的 PROXY protocol，否則任何人都能在連線開頭自己寫一段假的。下面用 `struct` 組出 v1（文字）與 v2（二進位）兩種格式並解析回來：

```python
import ipaddress
import struct

V2_SIGNATURE = b"\r\n\r\n\x00\r\nQUIT\n"       # 12 bytes，刻意不像任何正常協定的開頭


def proxy_v1(src, dst, sport, dport) -> bytes:
    return f"PROXY TCP4 {src} {dst} {sport} {dport}\r\n".encode()


def proxy_v2(src, dst, sport, dport) -> bytes:
    addrs = ipaddress.IPv4Address(src).packed + ipaddress.IPv4Address(dst).packed
    addrs += struct.pack("!HH", sport, dport)
    # 0x21 = 版本 2、命令 PROXY；0x11 = AF_INET + STREAM（TCP over IPv4）
    return V2_SIGNATURE + struct.pack("!BBH", 0x21, 0x11, len(addrs)) + addrs


def parse(data: bytes):
    if data.startswith(V2_SIGNATURE):
        ver_cmd, fam, length = struct.unpack("!BBH", data[12:16])
        body = data[16:16 + length]
        src, dst = ipaddress.IPv4Address(body[:4]), ipaddress.IPv4Address(body[4:8])
        sport, dport = struct.unpack("!HH", body[8:12])
        return "v2", str(src), sport, data[16 + length:]
    line, _, rest = data.partition(b"\r\n")
    _, proto, src, dst, sport, dport = line.decode().split(" ")
    return "v1", src, int(sport), rest


# LB 在 TCP 連線的最前面加上這段，後面才是 client 原本送的 bytes（這裡是 TLS ClientHello 的開頭）
payload = b"\x16\x03\x01\x02\x00"
for build in (proxy_v1, proxy_v2):
    wire = build("198.51.100.45", "203.0.113.80", 51514, 443) + payload
    version, ip, port, rest = parse(wire)
    print(f"{version}: 前置 {len(wire) - len(payload):2d} bytes → client {ip}:{port}，剩下 {rest.hex(' ')}")
    assert (ip, port, rest) == ("198.51.100.45", 51514, payload)
```

```text
v1: 前置 49 bytes → client 198.51.100.45:51514，剩下 16 03 01 02 00
v2: 前置 28 bytes → client 198.51.100.45:51514，剩下 16 03 01 02 00
```

```text
 byte 0 ─────────────────────── 11   12        13        14 ─── 15
 ┌────────────────────────────────┬─────────┬─────────┬───────────┐
 │ 簽章（12 bytes）               │ ver│cmd │ fam│prot│ 長度      │
 │ 0D 0A 0D 0A 00 0D 0A 51 55 49  │  2 │ 1  │  1 │ 1  │ (16 bit)  │
 │ 54 0A                          │         │         │ = 12      │
 ├───────────────┬────────────────┼─────────┴─────┬───┴───────────┤
 │ 來源 IPv4 (4) │ 目的 IPv4 (4)  │ 來源 port (2) │ 目的 port (2) │  bytes 16-27
 └───────────────┴────────────────┴───────────────┴───────────────┘
   之後：client 原本的 bytes（例如 TLS ClientHello）
```

v1 是一行人類可讀的文字：`PROXY TCP4 198.51.100.45 203.0.113.80 51514 443\r\n`，依序是協定、來源位址、目的位址、來源 port、目的 port，加上換行共 49 bytes。v2 的布局如上圖：12 bytes 的固定簽章之後，byte 12 的高 4 bit 是版本 2、低 4 bit 是命令（1 代表 PROXY）；byte 13 的高 4 bit 是位址族（1 代表 IPv4）、低 4 bit 是傳輸協定（1 代表 TCP）；byte 14–15 是後面位址區塊的長度，IPv4 的兩個位址與兩個 port 共 12 bytes，所以總共 28 bytes。兩種格式解析完後，剩下的 `16 03 01 02 00` 是原封不動的 TLS 紀錄開頭，後端照常進行 TLS 交握。注意 PROXY protocol 只出現在每條連線的最開頭一次，它和 HTTP header 無關；對沒有啟用它的 server 送 PROXY protocol，server 會把它當成亂碼而回錯誤。

## 25.4 負載分散演算法

LB 每收到一個新連線或新請求，都要從健康的後端中挑一台。最直覺的 **round robin**（輪詢）依序輪流：第一個給 app-a、第二個給 app-b、第三個再給 app-a。它假設每台後端一樣強、每個請求一樣重，兩個假設在 production 都常常不成立：主機規格不同、某台被同一實體機上的其他租戶拖慢（noisy neighbor）、某些請求要查十秒的報表。**weighted round robin** 依權重分配，例如新機器權重 2、舊機器權重 1，處理的是「規格不同」，但仍然看不見「暫時變慢」。

**least connections**（最少連線）挑目前進行中連線數最少的後端。這是一個簡單卻強大的回饋訊號：變慢的後端處理得慢，手上的請求就會累積，LB 自然少送給它。進一步的變形有 **least response time**（以最近的回應時間加權，例如以 EWMA，指數加權移動平均，追蹤延遲），以及 **power of two choices**（簡稱 P2C）：隨機挑兩台，再選其中負載較輕的一台。P2C 聽起來像折衷，但它有很好的數學性質，而且在「很多台 LB、各自只知道自己送出的連線數」的分散式環境裡，比每台 LB 都去搶「全域最閒」的那一台更穩定，不會讓所有 LB 同時湧向同一台後端。

下面這段程式用離散事件模擬比較四種演算法：三台後端各有 4 個 worker，其中 app-c 的服務時間是另外兩台的三倍，每秒 180 個請求以 Poisson 過程到達。

```python
import heapq
import random

# 三台 app 各有 4 個 worker；app-c 因為鄰居吵（noisy neighbor）變慢三倍
BACKENDS = {"app-a": 0.020, "app-b": 0.020, "app-c": 0.060}   # 平均服務時間（秒）
WORKERS, RATE, N = 4, 180, 30_000                             # 每秒 180 個請求


def simulate(algo, seed=7):
    rng = random.Random(seed)
    names = list(BACKENDS)
    busy_until = {n: [0.0] * WORKERS for n in names}          # 每個 worker 何時有空
    inflight = {n: [] for n in names}                          # 尚未完成的請求的完成時間
    latencies, sent, rr, t = [], dict.fromkeys(names, 0), 0, 0.0
    for _ in range(N):
        t += rng.expovariate(RATE)                             # Poisson 到達
        for n in names:                                        # 清掉已完成的請求
            while inflight[n] and inflight[n][0] <= t:
                heapq.heappop(inflight[n])
        if algo == "round_robin":
            n = names[rr % 3]; rr += 1
        elif algo == "random":
            n = rng.choice(names)
        elif algo == "least_conn":
            n = min(names, key=lambda x: (len(inflight[x]), rng.random()))
        else:                                                  # power of two choices
            x, y = rng.sample(names, 2)
            n = x if len(inflight[x]) <= len(inflight[y]) else y
        worker = min(range(WORKERS), key=lambda i: busy_until[n][i])
        start = max(t, busy_until[n][worker])                  # 沒有空 worker 就排隊
        done = start + rng.expovariate(1 / BACKENDS[n])
        busy_until[n][worker] = done
        heapq.heappush(inflight[n], done)
        latencies.append(done - t)
        sent[n] += 1
    latencies.sort()
    p50, p99 = latencies[N // 2] * 1000, latencies[int(N * 0.99)] * 1000
    share = " ".join(f"{n[-1]}={sent[n] * 100 // N:2d}%" for n in names)
    return p50, p99, share


print(f"{'演算法':12s} {'p50':>7s} {'p99':>8s}   分配比例")
for algo in ("round_robin", "random", "least_conn", "p2c"):
    p50, p99, share = simulate(algo)
    print(f"{algo:12s} {p50:5.0f}ms {p99:6.0f}ms   {share}")
rr_p99, lc_p99 = simulate("round_robin")[1], simulate("least_conn")[1]
assert lc_p99 < rr_p99
```

```text
演算法              p50      p99   分配比例
round_robin     24ms    554ms   a=33% b=33% c=33%
random          23ms    549ms   a=33% b=33% c=32%
least_conn      16ms    173ms   a=41% b=40% c=18%
p2c             16ms    175ms   a=40% b=39% c=19%
```

先看分配比例：round robin 與 random 都很「公平」，每台約三分之一，問題就出在公平。app-c 的 4 個 worker 每秒最多處理約 67 個請求，三分之一的流量是每秒 60 個，使用率高達九成，排隊時間暴增，於是 p99 衝到半秒以上，而 p50 看起來還好，這正是「平均正常、少數使用者卡住」的典型樣貌。least connections 與 P2C 都只給 app-c 不到兩成的流量，p50 與 p99 同時下降。P2C 只比較兩台，效果卻和看遍所有後端的 least connections 幾乎一樣，這就是它被 Envoy、Linkerd 等現代 proxy 廣泛採用的原因。

| 演算法 | 怎麼選 | 優點 | 弱點 | 適合 |
|---|---|---|---|---|
| round robin | 依序輪流 | 簡單、無狀態、可預測 | 看不見後端變慢或請求輕重不一 | 後端同質、請求短而均勻 |
| weighted round robin | 依權重輪流 | 處理規格差異 | 權重是靜態的 | 新舊機器混用、灰度發布 |
| random | 隨機 | 不需共享狀態 | 短時間內可能不均 | 非常多台 LB 的環境 |
| least connections | 進行中連線最少者 | 自動避開變慢的後端 | 快速失敗的後端會吸走流量；長連線時失準 | 請求處理時間差異大 |
| least response time／EWMA | 最近延遲最低者 | 直接優化延遲 | 需要量測與平滑，參數敏感 | 延遲敏感的 API |
| power of two choices | 隨機兩台取較閒者 | 接近最佳、分散式環境穩定 | 需要後端負載資訊（本機觀察即可） | 多台 LB、service mesh |
| hash（來源 IP、header、URL） | 依 key 算出固定後端 | 同一個 key 永遠落在同一台 | 熱門 key 造成熱點；後端增減時會重新分配 | sticky、快取分片（25.6 節） |

> [!warning] 常見誤解
> 「least connections 一定比 round robin 安全。」有一個經典陷阱：如果某台後端壞掉、對每個請求在 1 毫秒內就回 500，它手上的進行中連線永遠最少，least connections 反而把**更多**流量送給它，錯誤率暴增。這叫黑洞效應。防禦方法是讓 LB 把錯誤也當成訊號：被動 health check 在連續出現 5xx 時把它暫時移出（25.5 節），或在演算法裡把錯誤回應的權重拉高。

演算法之外還有兩個實務細節。第一是 **slow start**：新加入或剛恢復的後端快取是冷的、連線池是空的，若 least connections 看到它「完全沒連線」就一口氣送一大堆過去，它很可能馬上被打垮；HAProxy 的 `slowstart`、Envoy 的 slow start 設定都讓新後端的權重在一段時間內逐步爬升。第二，連線重用越普遍，L4「以連線為單位」的分配就越不均，L7「以請求為單位」才準確。

## 25.5 Health check：怎麼知道後端還活著

LB 只能把流量送給它認為健康的後端，而判斷健康的方式決定了故障時會損失多少請求。**Active health check**（主動檢查）由 LB 定期對每台後端送一個探測：可以是 TCP 連線（port 開著就算健康）、HTTP 請求（例如 `GET /healthz` 必須在 2 秒內回 200），或 gRPC 定義的 health checking 協定。故事裡的事故就是 TCP 檢查的盲點：交握由核心完成，gunicorn 的 worker 就算全卡死，port 依然「開著」。HTTP 檢查會走進應用程式，才問得出「你能不能處理請求」。

為了避免一次網路抖動就把後端移出，health check 有兩個門檻：連續失敗幾次才判定不健康（unhealthy threshold，也叫 fall），連續成功幾次才重新加回（healthy threshold，也叫 rise）。下圖是一台後端在 LB 眼中的狀態機：

```text
                 連續成功 rise 次
         ┌──────────────────────────────────┐
         ▼                                  │
   ┌──────────┐   連續失敗 fall 次   ┌───────────┐
   │ HEALTHY  │─────────────────────►│ UNHEALTHY │
   │ 接收流量 │                      │ 不送流量   │
   └────┬─────┘                      │ 繼續探測   │
        │ 部署：要求下線              └───────────┘
        ▼
   ┌──────────┐  進行中請求完成或     ┌──────────┐
   │ DRAINING │──draining 逾時───────►│ REMOVED  │
   │ 不收新的 │                      │          │
   │ 做完舊的 │                      └──────────┘
   └──────────┘
```

從左上開始讀。HEALTHY 的後端接收流量；探測連續失敗 fall 次就進入 UNHEALTHY，LB 停止送新流量，但繼續探測，連續成功 rise 次後才回到 HEALTHY。左下的 DRAINING 是部署時的優雅下線：LB 不再分配新請求，但讓已經在處理的請求做完，等它們結束或超過 draining 時間（雲端 LB 常稱為 deregistration delay）才真正移除，這是 zero-downtime deploy 的關鍵（第 43 章）。少了 draining，每次部署都會砍斷一批進行中的請求，WebSocket 使用者更會整批斷線。

偵測需要時間，這段時間的請求就是損失。假設 interval 5 秒、timeout 2 秒、fall 2 次，最壞情況下後端剛通過一次檢查就掛掉，要再經過兩輪探測才被移出：

```text
 時間（秒） 0        5        7        10       12
            │        │        │        │        │
 app-b      掛了 ✗
 探測       ✓（剛好在掛之前）  第 1 次送出  逾時   第 2 次送出  逾時 → 移出
                     └─ 2 秒 ─┘        └─ 2 秒 ─┘
 流量       ◄──────── 這 12 秒內 round robin 仍送一半的請求給 app-b ────────►
```

逐步算：第 5 秒送出第一次探測，等到第 7 秒逾時，算一次失敗；第 10 秒送出第二次，第 12 秒逾時，達到 fall 次數，移出。所以最壞情況約為 interval × fall ＋ timeout ＝ 12 秒。即使只是平常的流量，origin 每秒 600 個請求、一半送給 app-b，這 12 秒就有 600 × 0.5 × 12 ＝ 3,600 個請求失敗。把 interval 縮短會增加探測流量（每台 LB 節點都會探測每台後端，雲端 LB 背後常有幾十個節點），所以只靠主動檢查永遠不夠快。

**Passive health check**（被動檢查，Envoy 稱為 outlier detection）補上這個缺口：LB 觀察真實流量的結果，連續出現連線失敗或 5xx 就暫時把後端移出一段時間。nginx 開源版的 `max_fails` 與 `fail_timeout` 就是這一類，例如 10 秒內失敗 3 次就停用 10 秒。被動檢查反應快，在每秒數百個請求下幾十毫秒內就能察覺，但它需要「有流量」才能發現問題，而且要小心不要把 client 自己造成的錯誤（例如 400、404）也算進去。實務上兩者並用：被動檢查負責快速反應，主動檢查負責確認恢復。L7 proxy 對 GET 這類 idempotent 請求還能在連線失敗時自動改送下一台（nginx 的 `proxy_next_upstream`），把一次失敗藏起來；POST 則不能盲目重試，因為後端可能已經處理過了（第 24 章的 idempotency key）。

health check 端點本身也要設計。第 3 章已經提過 liveness 與 readiness 的區分；從 LB 的角度再補兩點。第一，readiness 若檢查太多下游，資料庫一抖動就讓所有後端同時「不健康」，LB 沒有任何後端可送。很多 LB 因此設計成 **fail open**：當全部或大多數後端都被判定不健康時，乾脆把流量送給所有後端，因為「也許還能服務一部分請求」好過「保證全部失敗」（Envoy 的 panic threshold 預設是健康比例低於 50% 就進入這個模式）。第二，health check 請求要便宜、不需要驗證、不寫 log 或另外取樣，否則每秒幾十個探測會淹沒真正的 log。

## 25.6 Sticky session 與 consistent hashing

有些服務希望同一個使用者的請求每次都落在同一台後端，這叫 **sticky session**（又稱 session affinity）。常見的理由有三個：session 存在某台後端的記憶體裡、後端有該使用者的本機快取、WebSocket 斷線重連時希望回到原本那台教室伺服器（第 33 章）。實作方式主要有兩種：LB 自己發一個 cookie 記住「你屬於 app-a」，或依某個 key（來源 IP、使用者 ID、教室 ID）做 hash。

| 方式 | 怎麼做 | 優點 | 問題 |
|---|---|---|---|
| LB 插入 cookie | 第一次回應時加 `Set-Cookie: lb=app-a`，之後依 cookie 轉送 | 精確，不受 IP 變化影響 | 只適用 HTTP；後端下線時 cookie 指向的機器不在了 |
| 應用程式 cookie | LB 依應用程式自己的 session cookie 做 hash | 不需要額外的 cookie | 依賴 LB 支援 |
| 來源 IP hash | hash(client IP) 選後端 | 不需要 cookie，L4 也能做 | 整棟學校共用一個 NAT 出口（第 7 章）全擠到同一台；手機換網路 IP 就變（第 13 章） |
| 業務 key hash | hash(教室 ID) 選後端 | 同一間教室的人都在同一台，方便廣播 | 熱門教室造成熱點 |

sticky 的代價常被低估。它讓負載不均（一個熱門教室就壓垮一台）、讓故障的影響變大（那台掛了，上面所有 session 全部遺失）、也讓擴容與部署變慢（舊連線不肯走）。所以第一選擇通常是讓後端**無狀態**：session 放在 Redis 或簽章 cookie 裡（第 26 章），任何一台都能處理任何請求。真正需要 sticky 的地方，例如即時教室與快取分片，要用好的 hash 方法，讓後端增減時受影響的 key 越少越好。

最天真的做法是 `hash(key) % N`：N 台後端時落在第 `hash % N` 台。問題在 N 改變時，幾乎所有 key 的結果都會變。**Consistent hashing**（一致性雜湊）把後端與 key 都 hash 到同一個環上，key 順時針找到的第一個後端就是它的歸屬：

```text
                        0 / 2^64
                    ┌──── ● a#17 ────┐
              ● c#3                    ● b#88
             ╱       key「sess-0042」→ ○          ← 順時針遇到的第一個點是 a#5
            │                            ● a#5      所以這個 session 歸 app-a
            │                            │
             ╲ ● b#41                    ╱
              ● d#9（新加入的 app-d）  ● c#60
                    └──── ● a#71 ────┘
      ● = 後端的虛擬節點（每台後端放 100 個點）　○ = key 的 hash 位置
```

從環的頂端順時針讀。每台後端用 `名稱#編號` hash 出許多個點，稱為**虛擬節點**（virtual node，vnode）；每個 key 也 hash 成環上一點，往順時針方向遇到的第一個虛擬節點就決定它的歸屬。新加入的 app-d 只會「搶走」落在它的點逆時針方向那一小段的 key，其他 key 的歸屬完全不變；某台後端移除時，也只有原本屬於它的 key 需要搬家。虛擬節點的用途是讓每台後端在環上分散成很多小段，否則四個點把環切成四段，長度可能差好幾倍。

```python
import bisect
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit


def h(key: str) -> int:
    # 取 SHA-256 前 8 bytes 當 64-bit 雜湊值；不能用內建 hash()，它每次執行加了隨機鹽
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


class Ring:
    def __init__(self, nodes, vnodes=100):
        self.points = sorted((h(f"{n}#{i}"), n) for n in nodes for i in range(vnodes))
        self.keys = [p for p, _ in self.points]

    def lookup(self, key: str) -> str:
        i = bisect.bisect(self.keys, h(key)) % len(self.points)   # 順時針第一個點
        return self.points[i][1]


def mod_n(nodes, key):
    return nodes[h(key) % len(nodes)]


sessions = [f"sess-{i:05d}" for i in range(20_000)]
old, new = ["app-a", "app-b", "app-c"], ["app-a", "app-b", "app-c", "app-d"]

moved_mod = sum(mod_n(old, s) != mod_n(new, s) for s in sessions) / len(sessions)
r_old, r_new = Ring(old), Ring(new)
moved_ring = sum(r_old.lookup(s) != r_new.lookup(s) for s in sessions) / len(sessions)
print(f"加入第 4 台：hash mod N 搬動 {moved_mod:.0%} 的 session，consistent hashing 搬動 {moved_ring:.0%}")

for v in (1, 10, 100):
    ring = Ring(new, vnodes=v)
    counts = {n: 0 for n in new}
    for s in sessions:
        counts[ring.lookup(s)] += 1
    print(f"  vnodes={v:3d}：各台比例 " + " ".join(f"{n[-1]}={c / len(sessions):.0%}" for n, c in counts.items()))

r_less = Ring(["app-a", "app-c", "app-d"])                    # app-b 故障被移出
moved = [s for s in sessions if r_new.lookup(s) != r_less.lookup(s)]
assert all(r_new.lookup(s) == "app-b" for s in moved)           # 只有 app-b 的 session 要搬
print(f"移除 app-b：搬動 {len(moved) / len(sessions):.0%}，而且全部原本都在 app-b")

# ---- CDN cache key：同一個檔案，四種寫法 ----
TRACKING = {"utm_source", "utm_medium", "fbclid", "gclid"}


def cache_key(url: str) -> str:
    u = urlsplit(url)
    query = sorted((k, v) for k, v in parse_qsl(u.query) if k not in TRACKING)
    return f"{u.scheme}://{u.hostname}{u.path}" + (f"?{urlencode(query)}" if query else "")


urls = ["https://www.shengsheng.example/img/misaki.webp?w=320&q=80",
        "https://WWW.shengsheng.example/img/misaki.webp?q=80&w=320",
        "https://www.shengsheng.example/img/misaki.webp?w=320&q=80&utm_source=line",
        "https://www.shengsheng.example/img/misaki.webp?w=320&q=80&fbclid=x9"]
keys = {cache_key(u) for u in urls}
print(f"原始 URL {len(set(urls))} 種 → 正規化後 cache key {len(keys)} 種：{keys.pop()}")
caches = Ring([f"cache-{i}" for i in range(1, 9)])             # 一個 PoP 內 8 台快取機
print(f"這個 key 在 PoP 內固定由 {caches.lookup(cache_key(urls[0]))} 負責")
```

```text
加入第 4 台：hash mod N 搬動 75% 的 session，consistent hashing 搬動 24%
  vnodes=  1：各台比例 a=24% b=10% c=48% d=18%
  vnodes= 10：各台比例 a=16% b=29% c=25% d=30%
  vnodes=100：各台比例 a=24% b=25% c=27% d=24%
移除 app-b：搬動 25%，而且全部原本都在 app-b
原始 URL 4 種 → 正規化後 cache key 1 種：https://www.shengsheng.example/img/misaki.webp?q=80&w=320
這個 key 在 PoP 內固定由 cache-5 負責
```

第一行是核心結論：從 3 台加到 4 台，`hash mod N` 讓 75% 的 session 換了後端（理論值是 N/(N+1)），consistent hashing 只搬了 24%，接近理想的 1/(N+1) ＝ 25%，而且搬的都是新機器該接手的那一份。接下來三行顯示虛擬節點的效果：每台只有 1 個點時，比例從 10% 到 48% 差了將近五倍；100 個點時就收斂到 24%～27%。移除 app-b 那一行驗證了另一個性質：被搬動的 25% 全部原本都在 app-b，其他後端上的 session 一個都沒受影響。

程式的後半部把同樣的工具用在 CDN。四個 URL 其實指向同一張老師照片，只是 query 參數順序不同、host 大小寫不同、帶了行銷追蹤參數；如果 cache key 直接用原始 URL，同一個檔案會被存四份、回源四次。正規化後只剩一個 key，再用 consistent hashing 決定 PoP 內由哪一台快取機負責，同一個物件就只會被存一次，PoP 內增減機器時也只有一小部分物件需要重新從上游取得。

consistent hashing 有兩個重要的變形值得知道名字。**Maglev** 是 Google 為 L4 LB 設計的方法，用預先算好的查詢表取代環，查詢更快、分配更均勻；每台 LB 節點對同一條連線都算出相同的後端，所以連線換了一台 LB 節點也不會斷，後端增減時也只有少數連線受影響。**Consistent hashing with bounded loads** 則替每台後端設上限，例如不超過平均負載的 1.25 倍，超過時就把 key 讓給環上的下一台，緩解熱門 key 造成的熱點；HAProxy 的 `hash-balance-factor` 就是這個想法。

## 25.7 X-Forwarded-For、Forwarded 與信任邊界

經過 L7 proxy 之後，後端的 TCP 對端永遠是最近的那一跳。故事裡 gunicorn 看到的 `remote_addr` 全是 nginx 的 10.20.3.11，因為對 gunicorn 而言，連線確實是 nginx 建立的。真正的 client 位址只能靠 proxy 寫進 HTTP header 往後傳。業界最常見的是 **`X-Forwarded-For`**（XFF）：每個 proxy 把「連到我的那個位址」附加到這個 header 的最右邊，形成一串以逗號分隔的位址鏈。它從來不是正式標準，只是約定俗成；正式標準是 RFC 7239 定義的 **`Forwarded`** header，把位址、協定、host 放在同一個結構裡。

```text
 學生 198.51.100.45 ──► CDN edge ──► LB 10.20.16.5 ──► nginx 10.20.3.11 ──► gunicorn
                       出口 198.51.100.230

 每一跳收到的 X-Forwarded-For（以及 TCP 對端）：
   CDN edge  收到：（沒有）                                   對端 198.51.100.45
   LB        收到：198.51.100.45                              對端 198.51.100.230
   nginx     收到：198.51.100.45, 198.51.100.230              對端 10.20.16.5
   gunicorn  收到：198.51.100.45, 198.51.100.230, 10.20.16.5  對端 10.20.3.11
                   └── 由 CDN 附加 ┘ └ 由 LB 附加 ┘ └由 nginx 附加┘
```

從上往下讀。CDN edge 直接和學生建立連線，所以它知道的 client 位址是 TCP 對端 198.51.100.45，轉送時把它寫進 XFF。LB 看到的對端是 CDN 的回源出口 198.51.100.230，它把這個位址附加在右邊；nginx 再附加 LB 在 VPC 內的位址 10.20.16.5。到了 gunicorn，XFF 有三段，加上 TCP 對端 10.20.3.11，正好是整條路徑由左到右的每一跳。這張圖揭露了 XFF 的本質：**每一段都是「寫下它的那個 proxy」看到的對端**，可信度完全取決於是誰寫的。

問題在於最左邊那一段是誰寫的。如果學生自己在請求裡帶了 `X-Forwarded-For: 192.0.2.66`，CDN 照慣例「附加」而不是取代，到了 gunicorn 就變成 `192.0.2.66, 198.51.100.45, 198.51.100.230, 10.20.16.5`。最左邊那個 192.0.2.66 是 client 自己寫的，任何人都能寫任何值；小晴的「取第一個」修法，等於讓攻擊者自己決定限速器看到的 IP。這就是**信任邊界**（trust boundary）：只有你部署、你掌控的 proxy 寫下的那幾段才可信，越過邊界之後的內容一律是 client 說了算。

```text
                     信任邊界
 不可信任（internet）   ┊   可信任（聲聲 Live 掌控的 proxy）
                        ┊
 192.0.2.66 ,  198.51.100.45 ,  198.51.100.230 ,  10.20.16.5    ← XFF（左到右）
 client 自己寫的  CDN 寫的         LB 寫的            nginx 寫的      對端：10.20.3.11
      ✗          ✓（它看到的對端）  ✓                 ✓              ✓（TCP，無法偽造）
                        ┊
     從右往左走：10.20.3.11 可信 → 10.20.16.5 可信 → 198.51.100.230 是 CDN 出口，可信
                 → 198.51.100.45 不在可信清單 → 它就是 client，停止
```

正確的演算法是**從右往左走**：先從 TCP 對端開始（這一跳無法偽造），只要目前這個位址屬於你信任的 proxy，就相信它寫下的下一段，繼續往左；遇到第一個不屬於可信清單的位址，它就是 client，停下來，左邊的一律不看。可信清單要寫成明確的網段：VPC 10.20.0.0/16（LB 與 nginx），加上 CDN 公布的回源出口網段（本書範例用 198.51.100.224/27）。下面把這個演算法和兩種常見錯誤寫法放在五種情境下比較：

```python
import ipaddress

# 聲聲 Live 信任的 proxy：VPC 內的 LB 與 nginx，以及 CDN 回源用的出口網段
TRUSTED = [ipaddress.ip_network(n) for n in ("10.20.0.0/16", "198.51.100.224/27")]


def is_trusted(ip, trusted):
    return any(ip in net for net in trusted)


def client_ip(peer: str, xff: str | None, trusted=TRUSTED) -> str:
    """從右往左走：跳過可信任的 proxy，第一個不可信任的位址就是 client。"""
    chain = [p.strip() for p in xff.split(",")] if xff else []
    chain.append(peer)                         # TCP 對端是最可靠的一跳，放在最右邊
    for hop in reversed(chain):
        try:
            ip = ipaddress.ip_address(hop)
        except ValueError:                     # 亂寫的值：不能再往左相信任何東西
            return "invalid"
        if not is_trusted(ip, trusted):
            return str(ip)
    return chain[0]                            # 整條鏈都可信（例如內部呼叫）


def leftmost(peer, xff):                       # 常見的錯誤寫法：直接拿第一個
    return xff.split(",")[0].strip() if xff else peer


def nth_from_right(peer, xff, n=3):            # 固定跳數：假設路徑上剛好有 n 個 proxy
    chain = [p.strip() for p in xff.split(",")] if xff else []
    return chain[-n] if len(chain) >= n else peer


NGINX = "10.20.3.11"                           # gunicorn 看到的 TCP 對端永遠是 nginx
cases = [
    ("學生經 CDN 進站", "198.51.100.45, 198.51.100.230, 10.20.16.5", "198.51.100.45"),
    ("學生直連 API LB", "198.51.100.23, 10.20.16.5", "198.51.100.23"),
    ("經 CDN，但自帶偽造 XFF", "192.0.2.66, 198.51.100.45, 198.51.100.230, 10.20.16.5", "198.51.100.45"),
    ("繞過 CDN 直打 LB 並偽造", "192.0.2.66, 198.51.100.230, 198.51.100.99, 10.20.16.5", "198.51.100.99"),
    ("XFF 塞入非 IP 的值", "<script>, 198.51.100.45, 198.51.100.230, 10.20.16.5", "198.51.100.45"),
]
for label, xff, truth in cases:
    right, left, fixed = client_ip(NGINX, xff), leftmost(NGINX, xff), nth_from_right(NGINX, xff)
    mark = lambda v: v + ("" if v == truth else " ✗")
    print(f"{label}（真正的 client：{truth}）")
    print(f"    從右信任 {mark(right):18s} 取最左 {mark(left):18s} 右數第 3 個 {mark(fixed)}")
    assert right == truth
```

```text
學生經 CDN 進站（真正的 client：198.51.100.45）
    從右信任 198.51.100.45      取最左 198.51.100.45      右數第 3 個 198.51.100.45
學生直連 API LB（真正的 client：198.51.100.23）
    從右信任 198.51.100.23      取最左 198.51.100.23      右數第 3 個 10.20.3.11 ✗
經 CDN，但自帶偽造 XFF（真正的 client：198.51.100.45）
    從右信任 198.51.100.45      取最左 192.0.2.66 ✗       右數第 3 個 198.51.100.45
繞過 CDN 直打 LB 並偽造（真正的 client：198.51.100.99）
    從右信任 198.51.100.99      取最左 192.0.2.66 ✗       右數第 3 個 198.51.100.230 ✗
XFF 塞入非 IP 的值（真正的 client：198.51.100.45）
    從右信任 198.51.100.45      取最左 <script> ✗         右數第 3 個 198.51.100.45
```

第一種情境三種方法都對，這也是錯誤寫法能通過測試、上線後才出事的原因。第二種情境是 API 不經過 CDN、直連 LB，路徑上只有兩個 proxy；「右數第 3 個」這種固定跳數的寫法因為鏈不夠長，退回成 nginx 的位址，等於所有使用者又共用一個限速額度，正是故事裡 429 的翻版。固定跳數只有在「所有請求的路徑都完全一樣」時才正確，而真實系統很少如此。

第三種情境是 client 自帶偽造值，「取最左」直接被騙；從右信任的方法在遇到 CDN 寫下的 198.51.100.45 時就停了，偽造值根本沒被看到。第四種最值得注意：攻擊者繞過 CDN，直接連到 LB 的公開位址 203.0.113.80，還在 XFF 裡偽造了一個看起來像 CDN 出口的 198.51.100.230。從右信任的方法依然正確，因為 LB 附加的是它真正看到的對端 198.51.100.99，這一段攻擊者改不了；而 198.51.100.99 不在可信清單，演算法就停在這裡。固定跳數的寫法則上當，拿到攻擊者偽造的 CDN 位址。最後一種是 XFF 被塞了不是 IP 的字串，從右信任的方法在碰到它之前就停了；就算碰到，也要把它當成不可信任的終點，而不是拿去寫進 log 或資料庫，否則就可能變成 log injection 或 XSS 的入口。

除了位址，proxy 還會傳遞另外兩個重要資訊：client 原本用的協定與 host。TLS 在 LB 終結之後，後端收到的都是明文 HTTP；如果 Flask 不知道原始請求是 HTTPS，`url_for(..., _external=True)` 會產生以 `http` 開頭的連結，「強制轉向 HTTPS」的邏輯會造成無限 redirect，帶 `Secure` 屬性的 cookie 判斷也會出錯。所以 LB 會加上 `X-Forwarded-Proto: https` 與 `X-Forwarded-Host`，它們和 XFF 一樣只能信任你自己的 proxy 寫下的值。nginx 的 realip 模組（`set_real_ip_from`、`real_ip_header`、`real_ip_recursive on`）做的就是從右往左、跳過可信網段的同一件事。Werkzeug 的 `ProxyFix` middleware 則採用固定跳數：你設定每個 header 信任右邊幾層 proxy，它據此改寫 WSGI environ。這在「所有請求都經過同樣幾層 proxy」時正確，所以常見的做法是讓最外層的自家 proxy 依網段解析好 client 位址，再交給後面固定的層數，第 43 章會實際設定。

| header | 格式範例 | 誰定義 | 注意事項 |
|---|---|---|---|
| `X-Forwarded-For` | `198.51.100.45, 198.51.100.230` | 慣例，無正式規格 | 每跳附加對端；多個同名 header 要依序合併後再解析 |
| `X-Forwarded-Proto` | `https` | 慣例 | 只信任最外層終結 TLS 的 proxy 寫的值 |
| `X-Forwarded-Host` | `www.shengsheng.example` | 慣例 | 未過濾就拿來組 URL 會造成 host header 汙染 |
| `X-Real-IP` | `198.51.100.45` | nginx 的慣用法 | 只有一個值，看不出經過幾跳 |
| `Forwarded` | `for=198.51.100.45;proto=https;by=203.0.113.80` | RFC 7239 | IPv6 要加引號與方括號，例如 `for="[2001:db8:5a5a::23]"` |
| `Via` | `1.1 lab-proxy, 1.1 edge-tpe` | RFC 9110 | 記錄經過的 proxy 與協定版本，可用來偵測轉送迴圈 |

信任邊界不只在應用程式裡，也在網路上。聲聲 Live 的 origin LB 203.0.113.80 有一個公開位址，如果它接受來自任何地方的連線，攻擊者就能繞過 CDN 的 WAF 與 DDoS 防護直接打 origin。常見的防禦是把 origin 鎖起來：security group 只放行 CDN 公布的回源網段，或要求 CDN 回源時帶一個只有雙方知道的 secret header、甚至用 mTLS 讓 CDN 向 origin 證明身分（第 30 章）。這樣 XFF 解析時「把 CDN 出口當作可信」的假設才真的成立。最後，Rita 也提醒：就算正確取出了 client IP，也要記得 CGNAT（第 7 章）會讓上千個使用者共用一個 IPv4 位址，而 IPv6 使用者通常有一整個 /64（第 5 章），所以登入限速應該同時看帳號、IP 與 IPv6 前綴，而不是只看單一 IP。

## 25.8 CDN：把內容放到使用者旁邊

**CDN**（Content Delivery Network）是分布在世界各地的 reverse proxy 與快取叢集。每個機房稱為一個 **PoP**（point of presence），PoP 裡直接面對使用者的伺服器稱為 **edge**。使用者被導向最近的 PoP 有兩種主要方式：anycast 讓所有 PoP 宣告同一個 IP，由 BGP 把封包送到路徑最短的那個（第 6 章）；DNS 導向則讓權威 DNS 依查詢來源回應不同 PoP 的位址（第 15 章）。就近終結交握帶來的好處第 1 章已經說明，這一節看快取本身怎麼運作，以及它在故事裡怎麼出事。

```text
 學生（台北） ──► PoP 台北 edge ─┐
 學生（東京） ──► PoP 東京 edge ─┼──► origin shield（中間層快取，一個區域一個）──► origin
 學生（洛杉磯）─► PoP 洛杉磯 edge ┘          │                                      203.0.113.80
                    │                        │                                      （LB → nginx → app）
                    │ ① edge 命中：直接回應   │ ② shield 命中：edge 從 shield 取，不打 origin
                    │                        │ ③ 都沒命中：shield 回源一次，存起來再往下發
                    ▼                        ▼
      學生看到的延遲：① 幾毫秒～數十毫秒　② 多一段 PoP 到 shield 的 RTT　③ 再多一段到 origin 的 RTT
```

這是加了 **origin shield** 的分層快取架構，從左往右讀。每個 PoP 的 edge 先查自己的快取，命中就直接回應（①）。沒命中時，edge 不直接回源，而是去問 shield；shield 是一個指定的中間層 PoP，所有 edge 的 miss 都匯集到這裡（②）。只有 shield 也沒有時，才由 shield 向 origin 發出一次請求（③），拿到後存在 shield，再一路發回 edge。沒有 shield 時，二十個 PoP 各自 miss 就是二十次回源；有了 shield，同一個物件最多回源一次。代價是 miss 時多一段到 shield 的延遲，shield 本身也要做容量規劃。

### cache key：什麼算「同一個東西」

**cache key** 是 CDN 用來判斷兩個請求能不能共用同一份快取的字串。多數 CDN 預設用 scheme、host、路徑與完整 query string 組成 key，再依 origin 回應的 `Vary` header 加上指定 header 的值（第 21 章）。key 太粗會出大事：如果 key 沒包含某個會改變回應的因素，例如語言或登入狀態，A 使用者的內容就會被送給 B。key 太細則會讓命中率崩潰：25.6 節的程式裡，同一張照片因為參數順序與追蹤參數被拆成四個 key。實務上要做的是**正規化**：排序 query 參數、移除 `utm_*` 這類不影響內容的參數、統一 host 大小寫，並避免 `Vary: User-Agent`、`Vary: Cookie` 這種幾乎每個使用者都不同的值。

快取多久由 origin 的回應 header 決定。`Cache-Control: max-age=60` 同時約束瀏覽器與 CDN；`s-maxage` 只約束共享快取（CDN、proxy），所以可以讓 CDN 存 10 分鐘、瀏覽器只存 1 分鐘；RFC 9213 定義的 `CDN-Cache-Control` 則只給 CDN 看。`Cache-Control: private` 或 `no-store` 告訴 CDN 不能存，聲聲 Live 個人化的首頁就是這樣（第 1 章）。過期之後，CDN 可以用 `If-None-Match` 帶著 ETag 回源做條件請求，origin 回 304 就不用重傳內容（第 21 章）。RFC 5861 定義的 `stale-while-revalidate` 允許 CDN 在背景更新的同時先回舊版，`stale-if-error` 允許 origin 出錯時繼續回舊版，這兩個指令是讓 origin 短暫故障不被使用者看見的重要保險。

> [!warning] 常見誤解
> 「把 API 回應放上 CDN 只要加 `Cache-Control: public` 就好。」要先確認回應內容和誰在請求無關。帶 `Authorization` header 的請求，共享快取預設不會存它的回應；但如果 origin 對需要登入的頁面回了 `public`，或 CDN 被設定成「依副檔名快取 `.css`、`.jpg`」，攻擊者就可能誘使 CDN 存下別人的個人頁面（web cache deception）。防禦方法是由 origin 對所有個人化回應明確送 `Cache-Control: private, no-store`，CDN 依 origin 的 header 決定能不能快取，而不是依網址長相。

### purge、request collapsing 與命中率

內容更新時要讓 CDN 丟掉舊版，這叫 **purge**（或 invalidation）。不同粒度的 purge 有完全不同的風險：

| 方式 | 做法 | 優點 | 風險 |
|---|---|---|---|
| 版本化檔名 | `app.3f9c1a.css`，內容改了檔名就變，HTML 指向新檔名 | 不需要 purge，舊版可以快取一年 | HTML 本身仍要短 TTL 或 purge |
| 單一 URL purge | 指定 URL 失效 | 精準 | URL 的寫法變體（query、大小寫）要一起清 |
| tag／surrogate key purge | 回應帶標籤（例如「teacher-misaki」），依標籤一次清一群 | 依業務關係清，不必列 URL | 需要 CDN 支援，標籤要設計 |
| soft purge | 標記為過期而不刪除，下次請求時回源驗證 | 搭配 stale 指令，origin 出錯時仍有舊版 | 使用者可能短暫看到舊內容 |
| purge everything | 全部清空 | 簡單 | 所有 PoP 同時回源，就是故事裡的事故 |

故事裡的 CSS 如果用版本化檔名，根本不需要 purge；就算要清，也只要清那一支 CSS 與講座頁。purge 本身不是壞工具：第 21 章的首頁快取事故（21:58 起，個人化首頁被 CDN 共用），就是靠 purge 首頁這一個 URL 在十二分鐘內止血；那次清的是單一 URL，這次清的是全站，差別在粒度。全站 purge 之後，最熱門的物件會同時在每個 PoP 被成千上萬個請求要求，這時第二道保險是 **request collapsing**（請求合併，nginx 稱為 `proxy_cache_lock`）：同一個 key 正在回源時，後到的請求不再各自回源，而是等第一個請求拿回來的結果。下面的模擬用 Zipf 分布（少數熱門檔案佔大多數請求，正是真實網站的樣貌）比較不同的 edge 容量與 shield，最後再模擬 purge 後同一張講座海報被 1,200 個請求同時要求的瞬間：

```python
import asyncio
import random
from collections import OrderedDict
from itertools import accumulate


class LRU:
    def __init__(self, capacity):
        self.capacity, self.data = capacity, OrderedDict()

    def get_or_fill(self, key) -> bool:
        """命中回 True；沒命中就放進快取（擠掉最久沒用的），回 False。"""
        if key in self.data:
            self.data.move_to_end(key)
            return True
        self.data[key] = True
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
        return False


OBJECTS, REQUESTS, EDGES = 50_000, 300_000, 8            # 5 萬個檔案、8 個 PoP
rng = random.Random(25)
weights = list(accumulate(1 / (rank ** 0.9) for rank in range(1, OBJECTS + 1)))  # Zipf 分布
stream = [(rng.randrange(EDGES), obj)
          for obj in rng.choices(range(OBJECTS), cum_weights=weights, k=REQUESTS)]


def run(edge_capacity, shield_capacity=None):
    edges = [LRU(edge_capacity) for _ in range(EDGES)]
    shield = LRU(shield_capacity) if shield_capacity else None
    edge_hits = origin = 0
    for pop, obj in stream:
        if edges[pop].get_or_fill(obj):
            edge_hits += 1
        elif shield is None or not shield.get_or_fill(obj):
            origin += 1                                   # 真正打到聲聲 Live 的 origin
    return edge_hits / REQUESTS, origin


print(f"{'設定':24s} {'edge 命中率':>10s} {'origin 請求':>10s} {'offload':>8s}")
for label, cap, shield in [("edge 2k／無 shield", 2_000, None),
                           ("edge 5k／無 shield", 5_000, None),
                           ("edge 5k＋shield 20k", 5_000, 20_000)]:
    hit, origin = run(cap, shield)
    print(f"{label:24s} {hit:10.1%} {origin:10,d} {1 - origin / REQUESTS:8.1%}")
no_shield, with_shield = run(5_000)[1], run(5_000, 20_000)[1]
assert with_shield < no_shield

# ---- purge 之後的瞬間：同一張講座海報被 8 個 PoP 的 1,200 個請求同時要 ----
class Tier:
    """一層快取；collapse=True 時，同一個 key 只送一個請求往上游，其他人等它。"""
    def __init__(self, upstream, collapse):
        self.upstream, self.collapse, self.cache, self.inflight = upstream, collapse, set(), {}

    async def get(self, key):
        if key in self.cache:
            return
        if self.collapse and key in self.inflight:
            return await self.inflight[key]
        fut = asyncio.get_running_loop().create_future()
        if self.collapse:
            self.inflight[key] = fut
        await self.upstream(key)
        self.cache.add(key)
        fut.set_result(None)
        self.inflight.pop(key, None)


async def purge_storm(collapse, use_shield):
    origin_calls = 0

    async def origin(key):
        nonlocal origin_calls
        origin_calls += 1
        await asyncio.sleep(0.05)                          # 回源要 50 ms，這段時間請求持續湧入

    upstream = Tier(origin, collapse).get if use_shield else origin
    pops = [Tier(upstream, collapse) for _ in range(EDGES)]
    await asyncio.gather(*(pops[i % EDGES].get("/img/lecture-poster.webp") for i in range(1_200)))
    return origin_calls


results = []
for label, collapse, use_shield in [("不合併、無 shield", False, False),
                                    ("PoP 內合併、無 shield", True, False),
                                    ("PoP 內合併＋shield", True, True)]:
    results.append(asyncio.run(purge_storm(collapse, use_shield)))
    print(f"purge 後 1,200 個同時請求｜{label}：origin 收到 {results[-1]:,d} 個")
assert results == [1_200, EDGES, 1]
```

```text
設定                         edge 命中率  origin 請求  offload
edge 2k／無 shield              46.5%    160,407    46.5%
edge 5k／無 shield              56.7%    129,908    56.7%
edge 5k＋shield 20k            56.7%     62,380    79.2%
purge 後 1,200 個同時請求｜不合併、無 shield：origin 收到 1,200 個
purge 後 1,200 個同時請求｜PoP 內合併、無 shield：origin 收到 8 個
purge 後 1,200 個同時請求｜PoP 內合併＋shield：origin 收到 1 個
```

先看前三列。edge 容量從 2,000 個物件增加到 5,000 個，命中率從 46.5% 升到 56.7%；這裡的 **request hit ratio** 是「被 edge 直接回應的請求比例」，而 **offload** 是「不必打到 origin 的請求比例」，對 origin 的容量規劃來說後者才是重點。加上一個 20,000 個物件的 shield 之後，edge 命中率完全不變，因為 shield 不改變 edge 的行為；但 origin 請求從 129,908 降到 62,380，少了一半以上。原因是 8 個 PoP 各自 miss 的長尾物件，有很多是同一批物件，shield 讓它們只回源一次。

後三行是 purge 後的瞬間。沒有合併時，1,200 個請求在回源的 50 毫秒內全部 miss，origin 收到 1,200 個一模一樣的請求；每個 PoP 內合併後剩 8 個（每個 PoP 一個）；再加上 shield 也合併，origin 只收到 1 個。故事裡的 origin 從每秒六百多個請求暴增到五千八百個，就是因為 purge 讓上千個物件同時進入第一種情況。實際的 CDN 命中率還受 TTL、物件大小、purge 頻率與 cache key 設計影響，這個模擬的數字只用來比較設定之間的相對差異。

CDN 也越來越常處理不能快取的動態請求。edge 終結 TLS、與 origin 維持長連線與連線重用、在 PoP 之間走優化過的路徑，就算每個請求都回源，也比使用者直接跨洋連 origin 快。CDN 同時是第一道安全防線：WAF、bot 偵測、DDoS 吸收都在 edge 完成，這也是為什麼 25.7 節要把 origin 鎖起來，只讓 CDN 連得到。

> [!note] 2026 現況
> 截至 2026 年 10 月，主要 CDN 都支援 HTTP/3 與 TLS 1.3，`Cache-Status` 回應 header（RFC 9211）讓不同 CDN 用一致的格式回報 hit／miss，但許多 CDN 仍同時保留自家的 `X-Cache`、`CF-Cache-Status` 之類的 header。依 tag purge 的命名各家不同（例如 surrogate key、cache tag），使用前要看你用的 CDN 的文件。

## 25.9 API gateway：放在 API 前面的那一層

**API gateway** 是專門放在 API 前面的 L7 reverse proxy，除了分流之外，還集中處理每支 API 都需要、但不屬於業務邏輯的事：驗證 JWT 或 API key（第 27、30 章）、依 client 或方案做限速與配額、依版本或路徑路由到不同服務、統一錯誤格式與 CORS（第 23 章）、記錄每個請求的 metrics 與 trace。例如聲聲 Live 開放給合作學校的 API，每個學校有自己的 API key 與每日配額，gateway 在請求進到 Flask 之前就把沒帶 key、超過配額的請求擋掉。

```text
                    ┌──────────────────── API gateway ────────────────────┐
 合作學校的系統 ───► │ TLS 終結 → 驗證 API key／JWT → 限速與配額 → 路由      │
                    │      ✗ 401         ✗ 403          ✗ 429               │
                    │                      加上 x-request-id、XFF、trace header│
                    └───────┬──────────────────┬──────────────────┬───────────┘
                            ▼                  ▼                  ▼
                     /v1/courses          /v1/bookings        /v1/reco
                     課程服務（Flask）     預約服務（Flask）    推薦服務 reco
```

由左往右讀。請求在 gateway 依序通過 TLS 終結、身分驗證、限速，任何一關失敗就直接回 401、403 或 429，不會打擾後端；通過的請求被加上 `x-request-id`（全書用它串接各層 log）、XFF 與 trace header，再依路徑送到對應的服務。好處是每個服務不必各自實作驗證與限速，政策也能集中稽核。代價同樣明顯：gateway 成了所有 API 的單點，要能水平擴充、要有高可用；而且業務邏輯很容易偷偷長進 gateway 的設定裡，最後變成沒人敢改的「第二個應用程式」。

| 元件 | 主要關心 | 看得懂什麼 | 典型位置 |
|---|---|---|---|
| L4 load balancer | 連線分散、可用性 | IP、port | 最外層，或非 HTTP 服務前面 |
| L7 load balancer／reverse proxy | 請求分散、TLS、路由 | HTTP | CDN 之後、服務之前 |
| CDN | 快取、就近終結、防護 | HTTP 與快取語意 | 最靠近使用者 |
| API gateway | 驗證、配額、版本、API 政策 | HTTP 加上 API 的身分與方案 | 對外 API 的入口 |
| service mesh sidecar | 服務之間的 mTLS、重試、觀測 | HTTP／gRPC | 每個服務旁邊（第 44 章） |

這張表的分界其實很模糊：Envoy 同時可以是 L7 LB、API gateway 與 mesh 的資料平面，nginx 也能做快取與限速。選型時與其問「這是哪一種產品」，不如問「這個功能放在哪一層，失敗時影響範圍最小、也最容易觀察」。例如登入限速不能放在一個看不到真正 client IP 的位置，這正是故事的第三個錯誤。

> [!note] 2026 現況
> 依 2026 年 10 月查證：Kubernetes 社群的 ingress-nginx 專案已於 2026-03-24 封存（archived），不再發布修補，官方建議改用 Gateway API 的實作；Ingress API 本身仍存在，但功能已凍結。Gateway API 最新為 v1.6.2（2026-09），v1.6 讓 TCPRoute、UDPRoute 升為 GA，SessionPersistence（sticky session）仍屬 Experimental。gunicorn 24.1 起支援 PROXY protocol v2，並可用 CIDR 指定可信任的來源網段。第 44 章會再談 Gateway API 在叢集網路中的角色。

## 25.10 動手做：用 asyncio 寫一個 L7 reverse proxy

這一節把前面的概念全部寫成程式：兩台 upstream、一個 reverse proxy、一個主動 health check，再加上 `X-Forwarded-For` 的兩種處理方式。程式只用標準函式庫的 asyncio，全部跑在 127.0.0.1 上，port 由系統分配。為了讓行為容易觀察，做了三個刻意的簡化：每條連線只處理一個請求（`Connection: close`）、只支援 `Content-Length` 的 body、upstream 用一把 `asyncio.Lock` 模擬「只有一個 sync worker 的 gunicorn」，所以一個慢請求會讓排在後面的請求等待。

程式分成四塊。`read_message()` 讀取 HTTP/1.1 的起始行、header 與 body（第 20 章的格式）。`Upstream` 是假的 app 主機，`/slow` 會佔住 worker 0.3 秒，回應內容則把它收到的 `X-Forwarded-For`、`X-Forwarded-Proto` 與 `Via` 原樣回報，讓我們看到 proxy 做了什麼。`Proxy` 是主角：`pick()` 實作 round robin 與 least connections，`rewrite()` 移除 hop-by-hop header 並處理 XFF，`handle()` 在連線失敗時對 GET 改送下一台，`health_loop()` 是 fall／rise 各 2 次的主動檢查。最後的 `main()` 依序跑三個實驗。

```python
import asyncio
import json
import time

HOP_BY_HOP = {"connection", "keep-alive", "proxy-connection", "te", "trailer",
              "transfer-encoding", "upgrade", "proxy-authorization", "proxy-authenticate"}


async def read_message(reader):
    """讀一個 HTTP/1.1 訊息的起始行、header 與 Content-Length body。"""
    head = await reader.readuntil(b"\r\n\r\n")
    start, *lines = head.decode("latin-1").split("\r\n")[:-2]
    headers = [tuple(part.strip() for part in ln.split(":", 1)) for ln in lines]
    length = int(next((v for k, v in headers if k.lower() == "content-length"), "0"))
    body = await reader.readexactly(length) if length else b""
    return start, headers, body


# ---------- upstream：模擬 gunicorn 的 sync worker，一次只處理一個請求 ----------
class Upstream:
    def __init__(self, name):
        self.name, self.worker = name, asyncio.Lock()

    async def handle(self, reader, writer):
        start, headers, _ = await read_message(reader)
        path = start.split()[1]
        async with self.worker:                       # 單一 worker：後到的請求要排隊
            if path == "/slow":
                await asyncio.sleep(0.3)              # 模擬一個慢查詢
        h = {k.lower(): v for k, v in headers}
        body = json.dumps({"by": self.name, "xff": h.get("x-forwarded-for"),
                           "proto": h.get("x-forwarded-proto"), "via": h.get("via")}).encode()
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                     b"Content-Length: %d\r\nConnection: close\r\n\r\n%s" % (len(body), body))
        await writer.drain()
        writer.close()

    async def start(self, port=0):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", port)
        self.port = self.server.sockets[0].getsockname()[1]


# ---------- L7 reverse proxy ----------
class Proxy:
    def __init__(self, upstreams, algo="rr", xff_mode="overwrite"):
        self.pool = {u: {"healthy": True, "active": 0} for u in upstreams}
        self.algo, self.xff_mode, self.rr, self.events = algo, xff_mode, 0, []

    def log(self, msg):
        self.events.append(msg)
        print(f"  [proxy] {msg}")

    def pick(self, exclude=()):
        alive = [p for p, s in self.pool.items() if s["healthy"] and p not in exclude]
        if not alive:
            return None
        if self.algo == "least_conn":                 # 平手時依清單順序，結果可重現
            return min(alive, key=lambda p: self.pool[p]["active"])
        choice = alive[self.rr % len(alive)]
        self.rr += 1
        return choice

    def rewrite(self, headers, peer_ip):
        out = [(k, v) for k, v in headers if k.lower() not in HOP_BY_HOP]
        incoming = [v for k, v in out if k.lower() == "x-forwarded-for"]
        out = [(k, v) for k, v in out if k.lower() != "x-forwarded-for"]
        if self.xff_mode == "append" and incoming:     # 只有前一跳可信時才該這樣做
            xff = ", ".join(incoming + [peer_ip])
        else:                                          # 邊緣 proxy：不信任 client 帶來的值
            xff = peer_ip
        return out + [("X-Forwarded-For", xff), ("X-Forwarded-Proto", "http"),
                      ("Via", "1.1 lab-proxy"), ("Connection", "close")]

    async def forward(self, port, start, headers, body):
        r, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 0.5)
        try:
            w.write(f"{start}\r\n".encode() + "".join(f"{k}: {v}\r\n" for k, v in headers).encode()
                    + b"\r\n" + body)
            await w.drain()
            return await asyncio.wait_for(r.read(), 2)   # upstream 回完會關閉連線
        finally:
            w.close()

    async def handle(self, reader, writer):
        start, headers, body = await read_message(reader)
        peer_ip = writer.get_extra_info("peername")[0]
        headers, tried = self.rewrite(headers, peer_ip), []
        while (port := self.pick(exclude=tried)) is not None:
            tried.append(port)
            self.pool[port]["active"] += 1
            try:
                resp = await self.forward(port, start, headers, body)
                break
            except OSError as exc:                     # 被動偵測：連線失敗就換下一台
                self.log(f"{names[port]} 連線失敗（{type(exc).__name__}），改送下一台")
                if not start.startswith(("GET", "HEAD")):
                    resp = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"
                    break                              # 非 idempotent 的請求不自動重試
            finally:
                self.pool[port]["active"] -= 1
        else:
            resp = b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n"
        writer.write(resp)
        await writer.drain()
        writer.close()

    async def health_loop(self, interval=0.05, fall=2, rise=2):
        while True:
            for port, s in self.pool.items():
                try:
                    resp = await self.forward(port, "GET /healthz HTTP/1.1",
                                              [("Host", "health"), ("Connection", "close")], b"")
                    good = resp.startswith(b"HTTP/1.1 200")
                except (OSError, asyncio.TimeoutError):
                    good = False
                s["ok_streak"] = s.get("ok_streak", 0) + 1 if good else 0
                s["fail_streak"] = 0 if good else s.get("fail_streak", 0) + 1
                if s["healthy"] and s["fail_streak"] >= fall:
                    s["healthy"] = False
                    self.log(f"health check：{names[port]} 連續失敗 {fall} 次 → 移出")
                elif not s["healthy"] and s["ok_streak"] >= rise:
                    s["healthy"] = True
                    self.log(f"health check：{names[port]} 連續成功 {rise} 次 → 加回")
            await asyncio.sleep(interval)


async def request(port, path="/", extra=""):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(f"GET {path} HTTP/1.1\r\nHost: www.shengsheng.example\r\n{extra}\r\n".encode())
    await w.drain()
    raw = await r.read()
    w.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    status = int(head.split()[1])
    return status, (json.loads(body) if body else {})


async def burst(proxy_port):
    """先送一個慢請求，緊接著送 4 個快請求，量每個快請求的延遲。"""
    async def timed(path):
        t0 = time.perf_counter()
        _, data = await request(proxy_port, path)
        return data["by"], round((time.perf_counter() - t0) * 10) * 100
    slow = asyncio.create_task(timed("/slow"))
    await asyncio.sleep(0.02)
    quick = [await timed("/") for _ in range(4)]          # 依序送出，方便看出分配
    return await slow, quick


names = {}


async def main():
    a, b = Upstream("app-a"), Upstream("app-b")
    await a.start(); await b.start()
    names.update({a.port: "app-a", b.port: "app-b"})

    for algo in ("rr", "least_conn"):
        proxy = Proxy([a.port, b.port], algo=algo)
        srv = await asyncio.start_server(proxy.handle, "127.0.0.1", 0)
        slow, quick = await burst(srv.sockets[0].getsockname()[1])
        print(f"{algo:10s} 慢請求 {slow}；快請求 {quick}")
        srv.close()

    print("--- health check：app-b 掛掉再恢復 ---")
    proxy = Proxy([a.port, b.port], algo="rr")
    srv = await asyncio.start_server(proxy.handle, "127.0.0.1", 0)
    pport = srv.sockets[0].getsockname()[1]
    b.server.close(); await b.server.wait_closed()       # 模擬 app-b 的 process 停掉
    checker = asyncio.create_task(proxy.health_loop())
    for i in (1, 2):                                      # health check 還來不及發現
        status, data = await request(pport)
        print(f"  請求 {i} → {status} by {data['by']}")
        assert status == 200
    await asyncio.sleep(0.2)
    got = [(await request(pport))[1]["by"] for _ in range(4)]
    print(f"  移出後 4 個請求 → {got}")
    assert got == ["app-a"] * 4
    await b.start(port=b.port)                            # 同一個 port 重新啟動
    await asyncio.sleep(0.2)
    got = [(await request(pport))[1]["by"] for _ in range(4)]
    print(f"  恢復後 4 個請求 → {got}")
    assert set(got) == {"app-a", "app-b"}
    checker.cancel(); srv.close()

    print("--- X-Forwarded-For：client 自己帶了一個偽造值 ---")
    forged = "X-Forwarded-For: 192.0.2.66\r\n"
    for mode in ("append", "overwrite"):
        proxy = Proxy([a.port], xff_mode=mode)
        srv = await asyncio.start_server(proxy.handle, "127.0.0.1", 0)
        _, data = await request(srv.sockets[0].getsockname()[1], extra=forged)
        print(f"  {mode:9s} upstream 看到 XFF = {data['xff']!r}，proto={data['proto']}，via={data['via']!r}")
        srv.close()
    assert data["xff"] == "127.0.0.1"
    a.server.close(); b.server.close()


asyncio.run(main())
```

```text
rr         慢請求 ('app-a', 300)；快請求 [('app-b', 0), ('app-a', 300), ('app-b', 0), ('app-a', 0)]
least_conn 慢請求 ('app-a', 300)；快請求 [('app-b', 0), ('app-b', 0), ('app-b', 0), ('app-b', 0)]
--- health check：app-b 掛掉再恢復 ---
  請求 1 → 200 by app-a
  [proxy] app-b 連線失敗（ConnectionRefusedError），改送下一台
  請求 2 → 200 by app-a
  [proxy] health check：app-b 連續失敗 2 次 → 移出
  移出後 4 個請求 → ['app-a', 'app-a', 'app-a', 'app-a']
  [proxy] health check：app-b 連續成功 2 次 → 加回
  恢復後 4 個請求 → ['app-b', 'app-a', 'app-b', 'app-a']
--- X-Forwarded-For：client 自己帶了一個偽造值 ---
  append    upstream 看到 XFF = '192.0.2.66, 127.0.0.1'，proto=http，via='1.1 lab-proxy'
  overwrite upstream 看到 XFF = '127.0.0.1'，proto=http，via='1.1 lab-proxy'
```

**實驗一：演算法。** 兩種演算法都先送一個 `/slow`，接著依序送 4 個快請求。round robin 把慢請求給了 app-a，快請求依序輪到 b、a、b、a；第二個快請求被送到 app-a 時，app-a 唯一的 worker 還被慢請求佔著，只好排隊約 300 毫秒。第四個快請求雖然也去 app-a，但這時慢請求已經結束，所以不用等。least connections 在慢請求進行中看到 app-a 有 1 條進行中連線、app-b 是 0，於是 4 個快請求全部送給 app-b，沒有任何一個需要等待。這就是 25.4 節模擬結果的縮小版：演算法只要能看到「誰手上比較忙」，就能避開排隊。

**實驗二：health check 與被動重試。** 程式關掉 app-b 的 server，模擬 process 停止。第 1 個請求依 round robin 輪到 app-a，正常完成；第 2 個請求輪到 app-b，proxy 連線時得到 `ConnectionRefusedError`（對方核心回了 RST，第 10 章），因為這是 GET，proxy 立刻改送 app-a，client 看到的是 200，完全不知道發生過失敗，這就是被動偵測加重試的效果。接著背景的 health check 連續兩次失敗，把 app-b 移出，之後 4 個請求全部去 app-a。app-b 在同一個 port 重新啟動後，health check 連續兩次成功才把它加回，流量恢復輪流分配。如果把 `handle()` 裡的重試拿掉，第 2 個請求就會變成 502，這正是 health check 偵測空窗期內使用者會遇到的錯誤。

**實驗三：XFF 的信任邊界。** client 刻意帶了 `X-Forwarded-For: 192.0.2.66`。append 模式把它當成前一跳寫的值，附加自己看到的對端，upstream 收到 `192.0.2.66, 127.0.0.1`，任何「取最左」的後端程式都會相信 client 來自 192.0.2.66。overwrite 模式是**邊緣 proxy**（直接面對 internet 的那一層）應有的行為：丟掉 client 帶來的值，只寫下自己親眼看到的 TCP 對端，upstream 收到的就只有 `127.0.0.1`。兩種模式的 upstream 也都看到 `X-Forwarded-Proto` 與 `Via`，前者告訴後端原始協定，後者記錄經過了哪個 proxy。

所以規則是：**面對 internet 的那一層覆寫，內部的每一層附加，後端從右往左解析**。append 本身不是錯，nginx 的 `$proxy_add_x_forwarded_for` 就是附加；錯的是讓 internet 上的 client 也被當作「前一跳」。

> [!tip]
> `rewrite()` 裡移除的 hop-by-hop header（`Connection`、`Keep-Alive`、`Transfer-Encoding`、`Upgrade` 等）只對單一連線有意義，proxy 不能原樣轉送：client 與 proxy 之間的 keep-alive 設定，和 proxy 與 upstream 之間完全無關。`Connection` header 裡列出的其他 header 名稱也屬於 hop-by-hop，要一併移除，這個簡化版沒有實作。另外，真正的 proxy 必須對 `Content-Length` 與 `Transfer-Encoding` 的組合做嚴格檢查，前後兩層對請求邊界的解讀不一致，就是 request smuggling 的成因；新版 gunicorn 已經會拒絕這類有歧義的請求（見第 20 章與第 43 章）。

## 25.11 在工作上怎麼用

事故檢討後，阿德和小晴把聲聲 Live 的設定改成下面的樣子，並整理出每個角色的檢查清單。

**SRE：把 health check、演算法與重試寫進設定。** LB 的 health check 改打 `/readyz`（interval 5 秒、timeout 2 秒、fall 2、rise 3），nginx 改用 least connections，並對連線錯誤與逾時重試一次。以下是 nginx 的對應設定，每一行的用意寫在註解裡：

```nginx
upstream app {
    least_conn;                                   # 避開變慢的後端
    server 10.20.3.21:8000 max_fails=3 fail_timeout=10s;   # 被動 health check
    server 10.20.3.22:8000 max_fails=3 fail_timeout=10s;
    keepalive 32;                                 # 重用到 gunicorn 的連線
}

server {
    listen 80;
    location / {
        proxy_pass http://app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";           # 讓 upstream keepalive 生效
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;   # 內部層：附加
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;    # 沿用 LB 寫的值
        proxy_next_upstream error timeout;        # 預設不會對 POST 等非 idempotent 請求重試
        proxy_next_upstream_tries 2;
        proxy_connect_timeout 2s;
        proxy_read_timeout 30s;
    }
}
```

這份設定把本章的四個概念對應到具體指令：`least_conn` 是 25.4 節的演算法，`max_fails`／`fail_timeout` 是被動 health check，`proxy_next_upstream` 是實驗二的重試，`$proxy_add_x_forwarded_for` 則是內部層的附加。主動 health check 由前面的雲端 LB 負責；nginx 開源版沒有主動檢查，NGINX Plus、HAProxy、Envoy 才有。

**後端工程師：用一個函式取得 client IP，全站共用。** 小晴把 25.7 節的 `client_ip()` 放進共用模組，可信網段從設定檔讀取（VPC 網段與 CDN 公布的回源網段，後者要定期更新），限速、稽核 log、風險判斷全部呼叫同一個函式，禁止任何地方直接讀 `X-Forwarded-For`。上線前用 curl 自己測一次信任邊界：

```bash
# 正常請求：log 裡的 client IP 應該是你自己的對外位址
curl -s https://www.shengsheng.example/api/whoami
# 自帶偽造值：client IP 必須仍然是你的真實位址，不能是 192.0.2.66
curl -s -H 'X-Forwarded-For: 192.0.2.66' https://www.shengsheng.example/api/whoami
# 繞過 CDN 直連 origin：應該被 security group 擋下（逾時），而不是回 200
curl -s --connect-timeout 3 --resolve www.shengsheng.example:443:203.0.113.80 \
     https://www.shengsheng.example/api/whoami
```

這三個請求分別驗證正常路徑、偽造 header 與繞過 CDN 三種情境。`--resolve` 讓 curl 把名稱直接對應到指定 IP，同時保持 SNI 與 `Host` 不變，是測試「特定 edge 或 origin」最方便的方法。`/api/whoami` 是一個只回傳伺服器判定的 client IP、不含任何敏感資訊的除錯端點，只開在 staging 或要求內部驗證。

**前端與 SRE：用回應 header 判斷 CDN 的行為。** 下面是對一張老師照片連續請求兩次的示意輸出：

```bash
curl -sI https://www.shengsheng.example/img/misaki.webp | grep -iE 'cache|age|via|etag'
```

```text
cache-control: public, max-age=86400
etag: "5d1-7f3a9c"
age: 0
cache-status: ExampleCDN; fwd=miss; stored
via: 1.1 edge-tpe

（第二次）
cache-control: public, max-age=86400
etag: "5d1-7f3a9c"
age: 37
cache-status: ExampleCDN; hit
via: 1.1 edge-tpe
```

這是示意輸出，實際 header 名稱依 CDN 而定。第一次的 `cache-status` 寫著 `fwd=miss; stored`，代表 edge 沒有這份內容、回源取得並存了下來，`age: 0` 表示剛從 origin 拿到。第二次變成 `hit`，`age: 37` 表示這份快取已經在 edge 待了 37 秒。如果每次都是 miss，依序檢查：回應是否帶 `private`、`no-store` 或 `Set-Cookie`；`Vary` 是否包含每個人都不同的 header；URL 是否帶著每次都不一樣的參數。

**影音工程師：長連線與 LB 的閒置逾時。** Joe 的 WebSocket 教室與直播控制通道都經過 L7 LB，LB 的 idle timeout 預設常是 60 秒左右；心跳間隔要比路徑上最短的 idle timeout 短，部署時 draining 時間要長到足以讓 client 收到 close frame 並重連（第 33 章）。SRT ingest（第 38 章）走 UDP，前面只能用 L4 LB，而且同一個串流的封包必須一直落在同一台 ingest 伺服器，所以要用五元組 hash 或專屬的 IP，不能用輪詢。

**資安工程師：把信任邊界寫成可以稽核的清單。** Rita 要求每一層 proxy 都寫明：接受誰的連線、相信誰寫的 header、對 internet 送來的 `X-Forwarded-*` 是覆寫還是附加。任何一層說不清楚，XFF 就不能用於安全決策。

## 25.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 某台後端卡死，LB 仍持續送流量，504 約占一半 | health check 只檢查 TCP port，交握由核心完成 | LB 的 target 狀態顯示 healthy；對該後端 `curl /readyz` 逾時 | 改用 HTTP health check；加上被動 outlier detection |
| 所有使用者同時被限速（429），log 的 client IP 全是同一個內網位址 | 應用程式讀的是 TCP 對端（proxy 的位址） | log 印出 `remote_addr` 與 XFF 比對 | 用從右往左的 `client_ip()`，可信網段明確列出 |
| 限速形同虛設，攻擊流量的 client IP 每次都不同 | 直接取 XFF 最左邊的值，被 client 偽造 | 用 curl 帶 `X-Forwarded-For: 192.0.2.66` 測試 | 邊緣 proxy 覆寫，後端只信任可信 proxy 加的段落 |
| 加了後端機器，新機器幾乎沒有流量（gRPC） | L4 LB 以連線為單位，HTTP/2 長連線不會重新分配 | 看各後端的連線數與請求數；client 連線數很少 | 改用 L7 LB 依 stream 分配，或 client 端負載分散 |
| 全站 purge 後 origin 過載、504 激增 | 所有 PoP 同時回源，沒有 request collapsing 或 shield | CDN 的回源請求數與 origin 的 RPS 同時暴增 | 版本化檔名、依 tag purge、開啟 collapsing 與 origin shield、soft purge |
| CDN 命中率很低，每個請求都回源 | cache key 含追蹤參數、`Vary: Cookie`、回應帶 `Set-Cookie` | 看 `cache-status`／`age`；比對 miss 請求的 URL 與 header | 正規化 cache key；靜態資源不設 cookie；修正 `Vary` |
| 部署時固定出現一批 502 與 WebSocket 斷線 | 沒有 draining，process 被直接停掉 | 比對錯誤時間點與部署事件 | 先從 LB 下線、等待 draining，再停 process |
| HTTPS 網站 redirect 迴圈，或產生的連結變成 `http` 開頭 | TLS 在 LB 終結，後端不知道原始協定 | 看後端收到的 `X-Forwarded-Proto` | 正確傳遞並只信任自家 proxy 的 `X-Forwarded-Proto`（ProxyFix，第 43 章） |
| 一台後端每個請求都快速回 500，錯誤率卻越來越高 | least connections 的黑洞效應 | 各後端的請求比例與錯誤率；壞的那台請求數最多 | 開啟被動 health check，連續 5xx 就移出 |
| 改了 sticky 設定後，某台後端負載是其他台的數倍 | 來源 IP hash 遇到大型 NAT 出口，或熱門教室集中 | 依 hash key 統計流量分布 | 改用 cookie 或業務 key；bounded load；能無狀態就無狀態 |

除錯 proxy 問題時，第一步永遠是**畫出路徑**：請求經過幾層、每一層的 TCP 對端是誰、逾時多少、加了什麼 header。每一層的 log 都記下 `x-request-id`、上游位址與上游回應時間（nginx 的 `$upstream_addr`、`$upstream_response_time`），就能從一筆失敗請求追到出問題的那一層與那一台。502 多半是上游連線被拒或被重置，504 多半是上游太慢，499（nginx 特有）則是 client 先放棄了。

## 25.13 動手練習

1. **延伸 proxy：加上 P2C 與被動 health check。** 在 25.10 節的 `Proxy.pick()` 加入 `algo="p2c"`（隨機挑兩台，選 `active` 較小者），並在 `handle()` 裡記錄每台 upstream 連續失敗的次數，連續 3 次就把它標成不健康 5 秒。
   答案要點：P2C 在只有兩台時等同 least connections，要加到三台以上才看得出差別。被動檢查應該在主動檢查之前就把 app-b 移出；測試方法是把 health check 的 interval 改成 1 秒，觀察第幾個請求之後就不再出現重試 log。

2. **延伸 proxy：讓它支援 keep-alive。** 把 upstream 回應改用 `Content-Length` 判斷結束而不是等 EOF，並替每台 upstream 維護一個連線池。
   答案要點：要先讀完回應的 header 取得長度，再讀剛好那麼多 bytes；連線池要處理 upstream 主動關閉閒置連線的情況（第 10 章的 CLOSE_WAIT 事故），重用前檢查連線是否已收到 EOF。量一下 100 個請求的總時間，重用連線應明顯較快。

3. **手算 health check 的損失。** origin 每秒 800 個請求，三台後端 round robin，health check 的 interval 10 秒、timeout 5 秒、fall 3。其中一台卡死時，最壞情況會有多少請求送到它那裡？若加上 nginx 的 `proxy_next_upstream timeout` 而 `proxy_read_timeout` 是 30 秒，使用者看到的是什麼？
   答案要點：最壞偵測時間約 10 × 3 ＋ 5 ＝ 35 秒，800 ÷ 3 × 35 ≈ 9,300 個請求。加上重試後，這些請求不一定失敗，但每個都要先等 30 秒逾時才改送下一台，使用者看到的是極慢而不是錯誤；所以讀取逾時要依 p99 延遲設定，並搭配被動檢查。

4. **用真實工具觀察 CDN。**（真實工具）選一個你常用、放在 CDN 後面的網站，用 `curl -sI` 對同一個靜態資源請求兩次，再對它加上一個無意義的 query 參數（例如 `?x=1`）請求。
   答案要點：觀察 `age`、`cache-status` 或 `x-cache` 的變化；加了參數後通常會變成 miss，因為 cache key 包含 query string。也可以在 DevTools 的 Network 面板看同樣的 header，並注意 `via` 或 `server-timing` 透露的 PoP 名稱。

5. **延伸 consistent hashing：bounded loads。** 修改 25.6 節的 `Ring.lookup()`，讓每台後端最多只能分到平均值的 1.25 倍，超過時順時針找下一台；再讓 1% 的 session 佔 30% 的請求（熱門教室），比較有無上限時的最大負載。
   答案要點：沒有上限時，熱門 key 所在的那台負載會遠高於其他台；加上上限後最大負載被壓在 1.25 倍附近，代價是一部分 key 不在「原本」的位置，後端增減時搬動的比例會略為增加。

6. **找出你的服務的信任邊界。**（真實工具）在你工作的系統（或 staging）用 25.11 節的三個 curl 指令測試，並在後端 log 中找出每個請求被判定的 client IP。
   答案要點：第二個請求若判定成 192.0.2.66，代表後端信任了 client 寫的值；第三個請求若成功回應，代表 origin 沒有鎖起來。兩個問題都要在修好之後，才能把 client IP 用於限速或稽核。

## 本章重點整理

- forward proxy 替 client 工作、由 client 設定；reverse proxy 替 server 工作、client 通常不知道它存在。CDN、LB、nginx 與 API gateway 都是 reverse proxy 的不同形態。
- HTTPS 經過 forward proxy 時用 `CONNECT` 建立隧道，TLS 仍是端到端，proxy 只看得到目的地名稱與 port；只有安裝了 proxy 的 CA 時內容才會被攔截。
- L4 load balancer 以連線為單位、只看五元組，快速且協定無關；L7 load balancer 以請求為單位、讀懂 HTTP，能做路徑分流、重試與改寫 header，但後端只看得到 LB 的位址。
- HTTP/2 與 gRPC 的長連線放在 L4 LB 後面會造成嚴重的負載不均，要改用以 stream 為單位分配的 L7 LB。
- round robin 看不見後端變慢；least connections 與 power of two choices 用「手上有多少請求」作為回饋，能自動避開慢的後端，但要提防快速失敗的後端變成黑洞。
- TCP health check 只證明核心還能交握；HTTP health check 才能確認應用程式能處理請求。最壞偵測時間約為 interval × fall ＋ timeout，期間的請求要靠被動檢查與 idempotent 請求的重試保護。
- draining 讓部署時進行中的請求做完再移除後端，是 zero-downtime deploy 與長連線服務的必要條件。
- sticky session 會造成負載不均並放大故障影響，能無狀態就無狀態；需要依 key 分配時用 consistent hashing，後端增減時只有約 1/(N+1) 的 key 需要搬動，虛擬節點讓分配均勻。
- `X-Forwarded-For` 的每一段都是寫下它的 proxy 看到的對端，可信度取決於是誰寫的；正確的解析是從 TCP 對端開始、從右往左跳過可信網段，遇到第一個不可信的位址就停。
- 面對 internet 的 proxy 要覆寫 client 帶來的 `X-Forwarded-*`，內部 proxy 附加；origin 要鎖成只接受 CDN 與自家 LB 的連線，否則信任邊界可以被繞過。
- CDN 的 cache key 決定什麼算同一個物件，要正規化 query 並避免高變異的 `Vary`；`s-maxage`、`stale-while-revalidate`、`stale-if-error` 讓 CDN 的行為可以獨立於瀏覽器調整。
- 全站 purge 會讓所有 PoP 同時回源；版本化檔名、依 tag purge、request collapsing 與 origin shield 能把同一物件的回源次數從上千次降到一次。
- API gateway 集中處理驗證、配額、路由與觀測，但會成為所有 API 的單點，業務邏輯不應長進 gateway。

## 延伸問答

> [!question]- Q1. 公司要求所有對外流量經過一台 proxy，聲聲 Live 自己也用 CDN。兩者都叫 proxy，差在哪裡？請從「誰設定、誰受益、client 看到什麼」三個角度比較。
> 公司的 proxy 是 forward proxy：由 client 這一側（公司 IT）部署，瀏覽器或作業系統要設定它，它替員工連到外面的任何網站，受益的是公司（過濾、稽核、快取）。員工的 HTTP 請求會用完整 URL 的 absolute-form，HTTPS 則用 `CONNECT` 開隧道，所以 proxy 知道目的地，但看不到加密內容，除非公司在電腦上安裝了自己的 CA 做 TLS 攔截。
>
> CDN 是 reverse proxy：由 server 這一側（聲聲 Live）部署，client 完全不需要設定，DNS 把 `www.shengsheng.example` 解析到 edge，client 以為自己連的就是聲聲 Live。它替特定的網站服務所有使用者，受益的是網站（就近終結、快取、防護）。CDN 終結 TLS，所以看得到完整的 HTTP 內容，憑證也由聲聲 Live 交給 CDN 管理。判斷一個 proxy 屬於哪一種，只要問「它是替誰工作、由誰放進路徑的」。

> [!question]- Q2. 聲聲 Live 要讓推薦服務 reco 用 gRPC 對外提供 API，有人提議直接放在現有的 L4 LB 後面。你會怎麼評估？
> 先看 gRPC 的連線模式。gRPC 建在 HTTP/2 上，client 通常只開一條長連線，在上面多工傳送所有請求。L4 LB 只在 TCP 連線建立時做一次分配，之後這條連線上的所有請求都落在同一台後端；如果 client 數量少（例如只有幾台 API 主機在呼叫 reco），後端之間的負載會非常不均，擴容也幾乎沒有效果，因為新機器拿不到既有的連線。
>
> 比較好的做法是用懂 HTTP/2 的 L7 LB 或 proxy（例如 Envoy），依 stream 把請求分到各後端；或在 client 端做負載分散，讓 client 對每台後端各開連線並自己挑選。若因為效能或架構一定要用 L4，至少要讓 client 定期重建連線（設定連線的最長壽命），讓分配有機會重新平衡。另外 L7 LB 也能提供 gRPC health checking、依方法名稱的 metrics 與重試，這些都是 L4 做不到的。

> [!question]- Q3. 手算：LB 每 10 秒對每台後端打一次 `/healthz`，timeout 3 秒，連續失敗 3 次才移出。兩台後端 round robin，每秒 400 個請求。其中一台突然當機（port 也關了），使用者會遇到多少錯誤？如果是 worker 卡死但 port 還開著呢？
> 最壞的偵測時間是 interval × fall ＋ timeout。port 關閉時，探測會立刻收到 RST，不必等 timeout，所以約為 10 × 3 ＝ 30 秒；期間一半的請求送到壞掉的那台，約 400 × 0.5 × 30 ＝ 6,000 個請求遇到連線被拒。不過連線被拒是 L7 proxy 能立刻察覺的錯誤，如果 proxy 對 GET 設定了重試（例如 nginx 的 `proxy_next_upstream error`），這些 GET 會被改送另一台，使用者幾乎看不到錯誤，只有 POST 之類不重試的請求會失敗。
>
> worker 卡死而 port 開著時，每次探測都要等滿 3 秒 timeout，偵測時間約 10 × 3 ＋ 3 ＝ 33 秒，期間約 6,600 個請求送到卡死的機器。更糟的是 proxy 要等讀取逾時才知道失敗，如果讀取逾時是 30 秒，每個使用者要等半分鐘才得到 504 或被重試。這就是被動 health check 重要的原因：觀察到連續逾時就提早移出，不必等主動檢查湊滿次數。

> [!question]- Q4. 你在 gunicorn 的 log 看到一筆登入請求的 `X-Forwarded-For: 192.0.2.77, 192.0.2.66, 198.51.100.45, 10.20.16.5`，TCP 對端是 nginx 10.20.3.11。可信網段是 10.20.0.0/16 與 CDN 回源網段 198.51.100.224/27。這個請求真正的 client 是誰？發生了什麼事？
> 從右往左走。TCP 對端 10.20.3.11 屬於 VPC，可信，所以相信它寫下的最後一段 10.20.16.5；10.20.16.5 也屬於 VPC（LB），可信，再往左是 198.51.100.45。198.51.100.45 不在 CDN 回源網段 198.51.100.224/27（範圍 .224 到 .255）裡，也不屬於 VPC，所以它就是 client，停止，左邊的 192.0.2.66 與 192.0.2.77 一律不看。
>
> 這個 XFF 透露了請求的路徑：LB 看到的對端是 198.51.100.45，而不是 CDN 的出口，代表這個請求沒有經過 CDN，而是直接連到 LB 的公開位址。左邊兩段是 client 自己帶的，可能是它前面還有其他 proxy，也可能是刻意偽造。若 `api.shengsheng.example` 本來就直連 LB，這是正常路徑；若這是只應經過 CDN 的 `www`，就代表 origin 沒有鎖好，應該讓 security group 只放行 CDN 回源網段。

> [!question]- Q5. CDN 的一個 PoP 裡有 8 台快取機，用 consistent hashing 分配物件。擴充成 10 台時，大約有多少比例的物件需要重新回源？如果改用 hash mod N 呢？為什麼虛擬節點數量重要？
> consistent hashing 在新增節點時，只有落在新節點「負責區段」裡的 key 會改變歸屬。從 8 台到 10 台，新的兩台理想上各負責十分之一，所以約 2/10 ＝ 20% 的物件需要從上游重新取得，其他 80% 仍在原本的快取機上。hash mod N 則會讓絕大多數 key 換位置：一個 key 在 mod 8 與 mod 10 時落在同一台的機率很低（在這個例子約五分之一），所以約八成的物件都要重新回源，等於擴容的那一刻命中率崩潰，origin 承受一次小型的 purge 風暴。
>
> 虛擬節點決定分配是否均勻。每台只有一個點時，環被切成長短差異很大的幾段，25.6 節的程式顯示比例可以從 10% 差到 48%，最大的那台會先被塞滿而淘汰更多物件。每台放上百個虛擬節點，每台負責的區段就由許多小段組成，總長度接近平均值。代價是查詢表變大，但對快取叢集的規模來說微不足道。

> [!question]- Q6. 新版前端上線後，CDN 對靜態資源的命中率從 95% 掉到 40%，origin 的頻寬費用暴增。你會依什麼順序排查？
> 先拿一個 miss 的請求與回應，用 `curl -sI` 看 header。第一個要查回應是否變得不可快取：新版是否讓靜態檔案也帶上 `Set-Cookie`（例如框架的 session middleware 套到了所有路徑），或 `Cache-Control` 被改成 `private`、`no-cache`。第二個查 `Vary`：若回應加了 `Vary: Cookie` 或 `Vary: User-Agent`，CDN 會依每個使用者的 header 值分開存，命中率自然崩潰。
>
> 第三個查 URL：新版是否在資源 URL 上加了每次都不同的參數，例如時間戳記或隨機數來「避免快取」，或行銷工具帶進來的追蹤參數沒有從 cache key 移除。可以比對 CDN log 中 miss 請求的 URL 分布，看是否大量 URL 只差在 query。最後確認部署流程是否每次都做全站 purge。修法依序是：靜態資源路徑不經過 session middleware、移除不必要的 `Vary`、改用版本化檔名並設長 TTL、在 CDN 設定 cache key 正規化。

> [!question]- Q7. 面試題：設計一個「每個 client 每分鐘最多嘗試登入 20 次」的限速，服務前面有 CDN、LB 與 nginx。client 是誰要怎麼判斷？有哪些陷阱？
> 第一步是取得可信的 client 位址。限速必須在一個看得到真實 client 的位置，用從右往左的演算法解析 `X-Forwarded-For`：從 TCP 對端開始，跳過明確列出的可信網段（VPC 內的 LB 與 nginx、CDN 公布的回源網段），遇到第一個不可信的位址就是 client。同時要讓 origin 只接受 CDN 與自家 LB 的連線，否則攻擊者繞過 CDN 時，「CDN 出口可信」的假設就失效。直接取 XFF 最左邊的值，攻擊者每次換一個偽造值就能完全繞過限速。
>
> 第二步是承認 IP 不等於使用者。CGNAT 與學校、公司的 NAT 讓上千人共用一個 IPv4 位址，嚴格的 per-IP 限制會誤傷整棟大樓；IPv6 使用者通常擁有整個 /64，per-address 的限制擋不住同一個人換位址。所以實務上會組合多個維度：per-account（防止針對單一帳號猜密碼）、per-IP 或 per-/64（防止單一來源大量嘗試）、全站的異常偵測，搭配逐步加嚴的回應（延遲、CAPTCHA、暫時鎖定），細節見第 26 章。最後，限速狀態要放在所有後端共用的儲存（例如 Redis），否則多台後端各算各的，實際上限會變成 20 × 後端數。

> [!question]- Q8. 三台後端用 least connections，其中 app-c 因為設定錯誤，每個請求都在 1 毫秒內回 500。觀察一段時間後，app-c 處理的請求比例會變高還是變低？為什麼？要怎麼預防？
> 會變高。least connections 的訊號是「進行中的連線數」，而 app-c 每個請求 1 毫秒就結束，手上幾乎永遠是 0 條進行中連線；健康的 app-a、app-b 正常處理請求要幾十毫秒，手上總有幾條。LB 每次比較時都會發現 app-c 最閒，於是把越來越多請求送給它，錯誤率從三分之一一路往上升。這種「壞掉的後端因為失敗得快而吸走流量」的現象叫黑洞效應，least response time 類的演算法也有同樣的問題，因為錯誤回應的延遲最短。
>
> 預防方法是讓錯誤本身成為訊號。被動 health check（outlier detection）在連續出現 5xx 或錯誤率超過門檻時把後端移出一段時間；主動 health check 的 `/readyz` 要走過會因設定錯誤而失敗的程式路徑，而不是只回固定的 200。部分 proxy 也支援在計算負載時對錯誤加權。另外，監控要看「各後端的請求比例」與「各後端的錯誤率」，只看全站錯誤率時，很難發現是某一台在吸流量。

## 延伸閱讀

- RFC 7239〈Forwarded HTTP Extension〉：`Forwarded` header 的語法與隱私考量
- RFC 9110〈HTTP Semantics〉：proxy 與 gateway 的角色、`CONNECT`、`Via` 與 hop-by-hop header
- RFC 9111〈HTTP Caching〉：共享快取的規則、`s-maxage` 與 `private`
- RFC 5861〈HTTP Cache-Control Extensions for Stale Content〉與 RFC 9213〈Targeted HTTP Cache Control〉
- HAProxy〈The PROXY protocol Versions 1 & 2〉：PROXY protocol 的規格文件
- David Karger 等〈Consistent Hashing and Random Trees〉（STOC 1997）：consistent hashing 的原始論文
- Daniel E. Eisenbud 等〈Maglev: A Fast and Reliable Software Network Load Balancer〉（NSDI 2016）
- Michael Mitzenmacher〈The Power of Two Choices in Randomized Load Balancing〉：P2C 的理論基礎
