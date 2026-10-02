---
chapter: 7
title: NAT、Port Forwarding 與防火牆
part: 1
---

# 第 7 章　NAT、Port Forwarding 與防火牆

> [!abstract] 本章地圖
> **核心問題**：你的封包在路上被誰改寫、被誰記住、被誰擋下？為什麼「從裡面連出去」很容易，「從外面連進來」很難？
>
> **你會學到**：
> - 說清楚 NAT 為什麼存在，分辨 SNAT、DNAT、NAPT 與 port forwarding，並畫出它改寫了 header 的哪些欄位
> - 讀懂連線追蹤表（conntrack），知道 mapping 為什麼會逾時，以及長連線該怎麼設定 keepalive
> - 用 RFC 4787 的 mapping 與 filtering 行為描述 NAT 類型，對照 full cone、restricted、port restricted、symmetric 舊稱，推導兩台 NAT 後主機能不能打洞成功
> - 理解 CGNAT 對封鎖 IP、記錄 log 與即時通訊的影響
> - 分辨 stateless 與 stateful 防火牆、security group 與 network ACL，寫出合理的規則順序
> - 用 Python 模擬 NAT 轉換表、hole punching 與 stateful 防火牆規則引擎
>
> **前置知識**：第 2 章（封裝與 header）、第 5 章（私有位址與 CIDR）、第 6 章（路由與 default gateway）

## 7.1 故事：三張看起來無關的工單

星期一早上，小晴的看板上同時出現三張工單。第一張是 Joe 開的：「行動網路上的學生，視訊課幾乎都走 TURN 中繼，這個月 TURN 的流量費用多了一截；有幾所學校的網路甚至完全連不上視訊。」第二張來自客服：「學生反映白板開著不動幾分鐘後，再畫就沒反應，要重新整理才恢復，但聊天室顯示對方一直在線上。」第三張是 Rita 開的：「有人用大量帳號刷試聽課，來源 IP 都是 198.51.100.200，我想直接把這個 IP 擋掉，請後端加一條規則。」

小晴把三張工單貼在一起問阿德，該從哪一張開始。阿德看了一眼就說：「這三張其實是同一件事。學生和我們之間，隔著好幾台會改寫封包、會記住連線、也會忘記連線的盒子。視訊打不通，是因為兩端的盒子不讓對方的封包進來；白板沒反應，是盒子忘了這條連線；那個 IP 不能直接擋，因為那台盒子後面可能坐著上千個學生。」

這台「盒子」就是 **NAT（Network Address Translation，網路位址轉換）**：一台會改寫封包來源或目的位址的設備，最常見的就是家裡的 Wi-Fi 路由器。和它形影不離的是**防火牆（firewall）**：依照規則決定封包放行或丟棄的設備或軟體。如果不懂這兩者，工程師會在三個地方卡住：以為「伺服器有開 port 就連得到」、以為「TCP 連線建立了就會一直在」、以為「一個 IP 就是一個人」。本章就沿著這三張工單，把 NAT 與防火牆從頭講清楚，最後用 Python 把它們模擬出來。

```text
 小晴看到的世界（錯誤的心智模型）
   學生筆電 192.168.1.20 ─────────────────────────────► api.shengsheng.example 203.0.113.80

 實際的世界
   學生筆電            家用路由器               電信 CGNAT                 網際網路          聲聲 Live
   192.168.1.20 ──►  [NAT＋防火牆]  ──►  100.72.18.9 ──► [CGNAT] ──► 198.51.100.200 ──► LB 203.0.113.80
                    改寫來源：             （電信內部）            改寫來源：
                    192.168.1.20:51000     100.72.18.9:51000      198.51.100.200:23017
                    → 100.72.18.9:51000    → 198.51.100.200:23017
                    記住：這條連線是誰的    記住：這條連線是誰的
```

這張圖是本章的地圖。上半是小晴原本的想像：筆電直接連到聲聲 Live。下半是真實情況：封包先經過家用路由器，來源位址被改成電信配給這個家庭的位址 100.72.18.9；再經過電信的大型 NAT（CGNAT，7.8 節），來源又被改成 198.51.100.200 與另一個 port。每經過一台 NAT，就多一份「這條連線屬於誰」的紀錄。聲聲 Live 的 load balancer 最後看到的來源是 198.51.100.200:23017，它完全不知道筆電的真實位址。三張工單的答案，都藏在這兩台盒子的行為裡。

## 7.2 為什麼需要 NAT：IPv4 不夠用

IPv4 位址是 32 位元，總共大約 43 億個（2³² = 4,294,967,296）。扣掉保留給特殊用途的區段，能分配給網際網路上設備的更少，而今天光是手機的數量就已經超過這個數字。各地區的位址管理機構在 2010 年代陸續把可自由分配的 IPv4 位址發完，這件事叫做 **IPv4 位址耗盡（IPv4 exhaustion）**：例如一間新的 ISP 想要一大段 IPv4，已經很難直接申請到，只能向別人購買或租用。

解法分成長期與短期兩條路。長期的解法是 IPv6（第 5 章），128 位元的位址多到每台設備都能有自己的全球位址。短期的解法就是 NAT：讓一整個家庭、一整間公司、甚至一整個城市的設備，共用少數幾個公網位址。為了讓這件事可行，RFC 1918 保留了三段**私有位址（private address）**：10.0.0.0/8、172.16.0.0/12、192.168.0.0/16。私有位址可以在任何內網重複使用，但不會在網際網路上被路由；例如你家筆電的 192.168.1.20 和隔壁鄰居筆電的 192.168.1.20 毫不衝突，因為這兩個位址都不會直接出現在公網上。

私有位址的封包要出去，就必須在邊界被換成一個公網位址，回程再換回來；這個換的動作就是 NAT。後來電信業者連「每個家庭一個公網位址」都給不起，又保留了 100.64.0.0/10 這段**共享位址空間（shared address space）**，專門給電信業者的 NAT 內部使用（RFC 6598），也就是 7.1 節圖中的 100.72.18.9。下面這段程式用 `ipaddress` 模組把聲聲 Live 常見的位址分類，第 5 章已經介紹過這個模組。

```python
import ipaddress

# 依用途分類位址：哪些可以出現在公網、哪些一定在某台 NAT 後面
RANGES = {
    "RFC 1918 私有": [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")],
    "CGNAT 共享（100.64/10）": [ipaddress.ip_network("100.64.0.0/10")],
    "loopback": [ipaddress.ip_network("127.0.0.0/8")],
    "文件範例（當作公網）": [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")],
}

def classify(addr: str) -> str:
    ip = ipaddress.ip_address(addr)
    for label, nets in RANGES.items():
        if any(ip in net for net in nets):
            return label
    return "其他（可能是公網）"

samples = {
    "192.168.1.20": "學生筆電（家用 Wi-Fi）",
    "10.20.1.10": "聲聲 Live 的 VPC 主機",
    "172.20.0.5": "Docker bridge 上的容器",
    "100.72.18.9": "電信 CGNAT 內的家用路由器 WAN 位址",
    "198.51.100.23": "學生家路由器的公網位址",
    "203.0.113.80": "聲聲 Live 的 load balancer",
}
for addr, who in samples.items():
    print(f"{addr:<15} {classify(addr)}｜{who}")

assert classify("100.72.18.9").startswith("CGNAT")
assert classify("172.32.0.1") == "其他（可能是公網）"   # 172.16/12 只到 172.31
shared = ipaddress.ip_network("100.64.0.0/10")
print(f"\n100.64.0.0/10 範圍：{shared[0]} ～ {shared[-1]}，共 {shared.num_addresses:,} 個位址")
```

```text
192.168.1.20    RFC 1918 私有｜學生筆電（家用 Wi-Fi）
10.20.1.10      RFC 1918 私有｜聲聲 Live 的 VPC 主機
172.20.0.5      RFC 1918 私有｜Docker bridge 上的容器
100.72.18.9     CGNAT 共享（100.64/10）｜電信 CGNAT 內的家用路由器 WAN 位址
198.51.100.23   文件範例（當作公網）｜學生家路由器的公網位址
203.0.113.80    文件範例（當作公網）｜聲聲 Live 的 load balancer

100.64.0.0/10 範圍：100.64.0.0 ～ 100.127.255.255，共 4,194,304 個位址
```

輸出逐行看。前三行都是 RFC 1918 私有位址：學生的家用網路、聲聲 Live 雲端 VPC（第 44 章）的主機、Docker 預設 bridge 網段上的容器，三者都不能直接被網際網路連到，出去時一定經過某台 NAT。第四行的 100.72.18.9 落在 100.64.0.0/10，看到這種位址出現在手機或路由器的 WAN 介面上，就可以判斷這台設備在電信的 CGNAT 後面。最後兩行是本書用來代表公網的文件範例位址。程式裡的 `assert` 特別檢查 172.32.0.1 不是私有位址：172.16.0.0/12 只涵蓋 172.16 到 172.31，這是手算 CIDR 最常犯的錯。

> [!warning] 常見誤解
> 不要用 Python 的 `ip.is_private` 當作「是否在 NAT 後面」的判斷。這個屬性依 IANA 的特殊用途位址表判斷，範圍比 RFC 1918 大：文件範例位址 198.51.100.23 的 `is_private` 也是 True；而 100.72.18.9 這種 CGNAT 位址，`is_private` 與 `is_global` 卻都是 False。要判斷「這是不是 RFC 1918」，像上面一樣明確列出網段最可靠。

## 7.3 NAT 怎麼運作：SNAT、NAPT 與連線追蹤表

先看最常見的情況：內網主機主動連出去。NAT 在封包離開時改寫**來源**位址，這叫 **SNAT（Source NAT，來源位址轉換）**；例如筆電送往 203.0.113.80:443 的 SYN，來源從 192.168.1.20 改成路由器的 WAN 位址 198.51.100.23。如果只改 IP，一個公網位址同一時間只能服務一台內網主機，所以實務上的 NAT 同時改寫 port，這叫 **NAPT（Network Address and Port Translation）**，也常被稱為 PAT 或 IP masquerade。家用路由器、手機熱點、雲端的 NAT gateway，做的都是 NAPT；本書後面說「NAT」，若沒特別註明，指的就是 NAPT。

改寫哪些欄位？看 IPv4 與 TCP header 的位元布局（第 2 章與第 10 章有完整說明）就很清楚：

```text
 IPv4 header（最少 20 bytes）
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-------+-------+-----------+---+-------------------------------+
 |Version|  IHL  |   DSCP    |ECN|         Total Length          |
 +-------+-------+-----------+---+-----+-------------------------+
 |        Identification         |Flags|     Fragment Offset     |
 +---------------+---------------+-----+-------------------------+
 | Time to Live  |   Protocol    |  Header Checksum   ◄ 必須重算  |
 +---------------+---------------+-------------------------------+
 |  Source Address              ◄ SNAT 改寫（出去時）             |
 +---------------------------------------------------------------+
 |  Destination Address         ◄ DNAT 改寫（進來時）             |
 +---------------------------------------------------------------+
 TCP header（最少 20 bytes；UDP 的前 4 bytes 也是兩個 port）
 +-------------------------------+-------------------------------+
 |  Source Port   ◄ NAPT 改寫    |  Destination Port ◄ DNAT 改寫 |
 +-------------------------------+-------------------------------+
 |                        Sequence Number                        |
 |                     Acknowledgment Number                     |
 |  ...（offset、flags、window）  |  Checksum   ◄ 必須重算         |
 +-------------------------------+-------------------------------+
```

圖中標了箭頭的欄位就是 NAT 動到的地方。出去的封包改 Source Address 與 Source Port；進來的封包（回程或 port forwarding）改 Destination Address 與 Destination Port。改完之後有兩個 checksum 必須跟著更新：IPv4 header checksum 只涵蓋 IP header，改了位址就要重算；TCP 與 UDP 的 checksum 雖然在 L4 header 裡，但計算時涵蓋一個包含來源與目的 IP 的**虛擬表頭（pseudo-header）**，所以只改 IP 也會讓它失效。NAT 通常用增量更新的方式修正 checksum，不必重新掃過整個 payload。

NAT 改完封包，還必須「記住」自己改了什麼，否則回程封包到了，它不知道要轉給誰。這份紀錄就是**連線追蹤表（connection tracking table）**，Linux 叫它 conntrack。每一列記錄一條連線的原始五元組（第 9 章：協定、來源 IP、來源 port、目的 IP、目的 port）、轉換後的位址、目前狀態與到期時間。下面的時序圖追蹤一位學生筆電的一次 HTTPS 連線；這位學生家的路由器直接拿到公網位址 198.51.100.23，沒有經過 CGNAT：

```text
 筆電 192.168.1.20         家用路由器（NAT）                       聲聲 Live LB 203.0.113.80
      │                     WAN 198.51.100.23                                 │
      │ SYN src=192.168.1.20:51000                                            │
      │     dst=203.0.113.80:443  │                                           │
      │──────────────────────────►│ 查表：沒有 → 新增一列                       │
      │                           │ 192.168.1.20:51000 ⇄ 198.51.100.23:51000  │
      │                           │ SYN src=198.51.100.23:51000               │
      │                           │─────────────────────────────────────────►│
      │                           │          SYN+ACK dst=198.51.100.23:51000  │
      │                           │◄─────────────────────────────────────────│
      │                           │ 查表：找到 → 目的改回 192.168.1.20:51000      │
      │ SYN+ACK dst=192.168.1.20:51000                                        │
      │◄──────────────────────────│                                           │
      │        （之後每個封包都查同一列；閒置太久，這一列被刪除）                │
```

第一步，SYN 從筆電送出，路由器在連線追蹤表找不到對應的列，於是新建一列，並為它挑一個對外 port；這裡剛好保留了原本的 51000，這種「能保留就保留原 port」的行為叫 **port preservation**。第二步，改寫來源後送往網際網路，LB 看到的對方是 198.51.100.23:51000。第三步，SYN+ACK 回到路由器，目的是 198.51.100.23:51000，查表找到那一列，把目的改回 192.168.1.20:51000 交給筆電。之後這條連線的每個封包，不論方向，都靠同一列翻譯。如果家裡另一支手機剛好也用 51000 連同一台 LB，路由器就必須換一個對外 port，否則回程封包無法區分是誰的。

光看示意圖還不夠具體。下面這段程式用真的 UDP socket，在 127.0.0.1 上寫一個使用者空間的迷你 NAPT：「伺服器」把它看到的來源 port 回報給對方，就像第 36 章的 STUN server；中間的 NAT 為每個內部來源開一個新的對外 socket，這個 socket 就是一筆 mapping。

```python
import socket
import threading

def udp(bind_port=0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", bind_port))
    s.settimeout(2)
    return s

# 「網際網路上的伺服器」：回報它看到的來源位址，就像 STUN server 做的事
server = udp()
def serve():
    for _ in range(4):
        data, src = server.recvfrom(2048)
        server.sendto(f"server 看到你是 {src[1]}".encode(), src)
threading.Thread(target=serve, daemon=True).start()

# 使用者空間的迷你 NAPT：inside 面向內網，每個內部來源各配一個 outside socket（＝一筆 mapping）
inside = udp()
mappings = {}            # 內部 (ip, port) -> outside socket
def pump_back(out_sock, client):
    # 回程：從 outside socket 收到的回應，轉回當初那個內部主機
    try:
        while True:
            data, _ = out_sock.recvfrom(2048)
            inside.sendto(data, client)
    except (socket.timeout, OSError):
        pass

def nat_loop():
    for _ in range(4):
        data, client = inside.recvfrom(2048)
        if client not in mappings:
            out = udp()                  # port 0：讓系統配一個對外埠，就像 NAT 從 port pool 取號
            mappings[client] = out
            threading.Thread(target=pump_back, args=(out, client), daemon=True).start()
        mappings[client].sendto(data, server.getsockname())
threading.Thread(target=nat_loop, daemon=True).start()

laptop, phone = udp(), udp()
results = {}
for name, sock in (("筆電", laptop), ("手機", phone)):
    for _ in range(2):
        sock.sendto(b"hello", inside.getsockname())
        reply, _ = sock.recvfrom(2048)
        results.setdefault(name, set()).add(reply.decode())
    own = sock.getsockname()[1]
    nat_port = mappings[sock.getsockname()].getsockname()[1]
    print(f"{name}：自己的埠 {own}，NAT 對外埠 {nat_port}，{results[name]}")
    assert results[name] == {f"server 看到你是 {nat_port}"}   # server 只看得到 NAT 配的埠

assert len({m.getsockname() for m in mappings.values()}) == 2   # 兩台主機各自一筆 mapping
print("mapping 筆數：", len(mappings))
for s in [server, inside, laptop, phone, *mappings.values()]:
    s.close()
```

```text
筆電：自己的埠 55285，NAT 對外埠 59944，{'server 看到你是 59944'}
手機：自己的埠 52138，NAT 對外埠 60153，{'server 看到你是 60153'}
mapping 筆數： 2
```

（埠號由作業系統分配，每次執行數字不同。）筆電自己的 socket 綁在某個 port，但伺服器回報的永遠是 NAT 對外 socket 的 port；手機也一樣，而且拿到的是另一個對外 port。`mappings` 字典就是連線追蹤表的最小版本：key 是內部位址，value 是對外的 socket。`pump_back` 執行緒負責回程：從對外 socket 收到的回應，依照 mapping 轉回原本的內部主機。這正是真實 NAT 的兩個動作：出去時查表或建表，回來時查表；查不到，就沒有人知道該交給誰。

在 Linux 上，這些動作由核心的 **netfilter** 框架完成，conntrack 是它的連線追蹤模組，iptables 與較新的 nftables 是設定規則的工具。封包在核心裡經過幾個固定的掛勾點（hook），NAT 與過濾規則就掛在這些點上：

```text
                     ┌──────────────────────────────────────────┐
  封包從網卡進來 ──►  │ PREROUTING ──► 路由判斷 ──┬──► INPUT ──► 本機程式（nginx、sshd）
                     │ （conntrack 建表、DNAT）    │                    │
                     │                          └──► FORWARD          │ 本機程式送出
                     │                               （轉送過濾）        ▼
                     │                                  │           OUTPUT
                     │                                  ▼             │
  封包從網卡送出 ◄──  │ POSTROUTING（SNAT、MASQUERADE）◄─┴─────────────┘
                     └──────────────────────────────────────────┘
```

從左上開始讀：封包進到 PREROUTING，conntrack 先判斷它屬於哪條連線，DNAT（改目的）在這裡做，因為接下來的路由判斷要依照改寫後的目的決定方向。目的是本機的封包進 INPUT，交給本機程式；要轉送到別台機器的封包（例如家用路由器轉給筆電）進 FORWARD。所有要離開的封包最後都經過 POSTROUTING，SNAT 在這裡做，因為此時才知道封包要從哪張網卡出去、該換成哪個來源位址。**MASQUERADE** 是 SNAT 的一種，自動使用出口網卡當下的位址，適合 WAN 位址會變動的家用網路。

```bash
# 家用路由器或 Linux 閘道的典型設定（需要 root，示意）
iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o eth0 -j MASQUERADE
sysctl -w net.ipv4.ip_forward=1          # 允許轉送；沒開這個，Linux 不會幫別人轉封包

# 檢視連線追蹤表（conntrack-tools 套件）
conntrack -L -p tcp
```

```text
（示意輸出）
tcp      6 431997 ESTABLISHED src=192.168.1.20 dst=203.0.113.80 sport=51000 dport=443 src=203.0.113.80 dst=198.51.100.23 sport=443 dport=51000 [ASSURED] mark=0 use=1
```

conntrack 的每一列有兩組四元組。第一組是「原方向」：筆電送出時的原始位址。第二組是「回程方向」：預期回來的封包長什麼樣子，這裡的 dst=198.51.100.23 就透露了 SNAT 的結果。前面的 431997 是剩餘秒數，`[ASSURED]` 表示雙向都看過流量，表滿時比較不會被優先淘汰。除錯時看這兩組位址是否對稱，就能判斷有沒有做 NAT、做成什麼樣。

> [!note]
> NAT 改的是 header；如果應用協定把 IP 寫在 payload 裡（例如 FTP 的主動模式、SIP 的 SDP 內容），對方會拿到一個私有位址而連不回來。有些路由器內建 **ALG（Application Layer Gateway）**，會偷偷改寫 payload 補救，但 ALG 常常改錯，「關掉路由器的 SIP ALG」是 VoIP 除錯的經典步驟。WebRTC 不依賴 ALG，而是用 ICE 自己探測位址（第 36 章）。

## 7.4 逾時：NAT 為什麼會「忘記」你

連線追蹤表不能無限長大。家用路由器的記憶體有限，CGNAT 要服務成千上萬個用戶，所以每一列都有**閒置逾時（idle timeout）**：一段時間沒有封包經過，這一列就被刪除。TCP 有 FIN 與 RST 可以明確標示「連線結束」，NAT 看到就能較快回收；UDP 沒有連線的概念，NAT 只能靠計時器猜測「應該用完了」。

這就是第二張工單的答案。白板的 WebSocket 是一條 TCP 長連線，學生開著頁面不動時，連線上可能好幾分鐘都沒有任何封包。如果某台 NAT 在這段時間把那一列刪了，兩端的 TCP 都不會知道，因為 TCP 不會主動檢查中間設備。之後伺服器推送更新，封包到了 NAT，查不到對應的列，只能丟棄；學生再畫一筆，封包從筆電出去，NAT 會把它當成新的流量、配一個新的對外 port，伺服器收到一個「不屬於任何連線」的 segment，通常回 RST。前端看到的就是「畫了沒反應，過一陣子才報錯」。

| 對象 | 逾時的規範或常見值 | 說明 |
|---|---|---|
| RFC 4787（UDP） | mapping 不得短於 2 分鐘，建議 5 分鐘以上 | 對 NAT 廠商的要求；DNS 等特定 port 可例外較短 |
| RFC 5382（TCP） | 已建立連線的閒置逾時不得短於 2 小時 4 分 | 這是為了配合 TCP keepalive 預設 2 小時 |
| Linux conntrack | UDP 單向約 30 秒、雙向約 120 秒；TCP 已建立 5 天 | `net.netfilter.nf_conntrack_*_timeout*`，依核心版本而定 |
| 家用路由器、行動網路、企業防火牆 | 從數十秒到數小時都有 | 實際值經常比 RFC 建議短，且無從事先得知 |

這張表的重點在第一列與最後一列的落差。RFC 說 TCP 閒置逾時至少要兩小時多，Linux 預設更是長達 5 天；但真實網路裡，有些設備為了省記憶體，幾分鐘就會清掉閒置的 TCP 列，UDP 甚至可能只有 30 秒。設計長連線時不能假設中間設備遵守 RFC，正確的做法是讓應用層定期送 keepalive：WebSocket 用 ping／pong（第 32 章），WebRTC 由 ICE 定期送 STUN 檢查（第 36 章），一般 TCP 可以調短 keepalive 間隔（第 11 章），讓連線上「每隔一段時間一定有封包」，間隔要比路徑上最短的逾時更短。業界常見的做法是每 20 到 30 秒送一次心跳。

```text
 學生瀏覽器               NAT（閒置逾時假設 5 分鐘）               rt.shengsheng.example
     │── WebSocket 訊息 ───────►│ mapping :51000 ⇄ :40017 ──────────────►│
     │                         │                                        │
     │       （7 分鐘沒有任何封包）│ 5 分鐘到：刪除 mapping                    │
     │                         │                                        │
     │                         │◄────────────── 伺服器推送白板更新 ──────│
     │                         │ 查無 mapping → 丟棄（無聲無息）           │
     │── 學生畫一筆 ───────────►│ 當成新流量 → 配新 port :40388 ─────────►│
     │                         │                                        │ 不認得這個五元組 → RST
     │◄──────────── RST ───────│◄───────────────────────────────────────│
     │  前端：「連線中斷，重新連線」                                         │
```

圖從上往下有三個階段。一開始 mapping 存在，訊息正常往返。中間 7 分鐘完全閒置，NAT 在第 5 分鐘刪掉 mapping，而兩端都不知情；伺服器的推送因此在 NAT 被丟棄，這種失敗沒有任何錯誤訊息，是最難查的一種。最後學生的新封包被配到新的對外 port，伺服器眼中這是一個陌生的五元組，於是回 RST，前端才終於發現斷線。只要在閒置期間每 25 秒送一次 ping，mapping 的到期時間就會不斷被往後延，整個問題就不會發生。

## 7.5 DNAT 與 Port Forwarding：讓外面連進來

NAT 天生只支援「裡面先開口」：連線追蹤表的每一列都是由內部送出的第一個封包建立的。如果外面的主機主動送來一個封包，NAT 找不到對應的列，就不知道要交給哪台內網主機，只能丟棄。要讓外面的人連到裡面的服務，必須事先手動建一條規則，這叫 **port forwarding（連接埠轉送）**：例如「凡是送到 WAN 位址 8080 埠的 TCP，都轉給 192.168.0.31 的 8000 埠」。它在技術上就是 **DNAT（Destination NAT，目的位址轉換）**：改寫進來封包的目的位址與 port。

聲聲 Live 的日文老師美咲想在家裡跑一個測試用的課程素材 server，讓學生從外面連進來看。對方在路由器設了 port forwarding，封包的路徑如下：

```text
 學生 198.51.100.140:62000        老師家路由器 WAN 198.51.100.201        老師筆電 192.168.0.31
        │                         規則：tcp 8080 → 192.168.0.31:8000            │
        │ SYN dst=198.51.100.201:8080│                                         │
        │───────────────────────────►│ PREROUTING：符合規則 → DNAT              │
        │                            │ 新增 conntrack 列                        │
        │                            │ SYN dst=192.168.0.31:8000               │
        │                            │────────────────────────────────────────►│
        │                            │            SYN+ACK src=192.168.0.31:8000│
        │                            │◄────────────────────────────────────────│
        │                            │ 查表：回程 → 來源改回 198.51.100.201:8080  │
        │ SYN+ACK src=198.51.100.201:8080                                      │
        │◄───────────────────────────│                                         │
```

第一步，學生連到老師家的公網位址 8080 埠。第二步，路由器在 PREROUTING 比對到 port forwarding 規則，把目的改成 192.168.0.31:8000，同時在連線追蹤表建立一列。第三步，老師筆電回 SYN+ACK，來源是自己的私有位址；路由器查表發現這是剛才那條連線的回程，把來源改回 198.51.100.201:8080。學生從頭到尾只看到老師家的公網位址，完全不知道 192.168.0.31 的存在。這也說明了 port forwarding 的本質：它不是「打開防火牆」，而是「預先在連線追蹤表外面放一條永久的翻譯規則」。

```bash
# 在 Linux 閘道上設定 port forwarding（需要 root，示意）
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 8080 -j DNAT --to-destination 192.168.0.31:8000
iptables -A FORWARD -p tcp -d 192.168.0.31 --dport 8000 -m conntrack --ctstate NEW -j ACCEPT
```

這兩行分別對應 NAT 與防火牆：第一行在 nat 表做 DNAT，第二行在 filter 表允許轉送給這台主機的新連線。很多人只寫了第一行，結果封包被 FORWARD 鏈預設的 DROP 丟掉，以為 DNAT 沒生效。

手動設定 port forwarding 對一般使用者太麻煩，所以出現了讓程式自動向路由器要求開 port 的協定：**UPnP IGD**、**NAT-PMP** 與它的後繼者 **PCP（Port Control Protocol）**。遊戲主機與一些 P2P 軟體會用它們。它們方便，但也代表內網任何一個程式都能自己替自己開門，所以很多企業網路與資安建議會關閉 UPnP；而在 CGNAT 後面，使用者根本碰不到電信那台 NAT，這些協定也就無效。

還有一個常讓人困惑的現象：老師在自己家裡，用「公網位址:8080」去測試自己的 server，結果連不上，但外面的學生連得到。原因是封包從筆電出發、送往路由器自己的 WAN 位址，路由器必須把它 DNAT 回內網，同時還要 SNAT，否則筆電收到的回應來源是內網位址，對不上原本的連線。這種「從內網繞到公網位址再折回來」的能力叫 **hairpinning（又稱 NAT loopback）**，RFC 4787 要求 NAT 支援，但不少家用路由器沒有實作。在內網測試時直接用私有位址，或在內部 DNS 設 split-horizon（第 15 章），就能避開這個問題。

> [!warning] 常見誤解
> 「我只把 8080 轉給測試機，所以很安全」不成立。port forwarding 會讓整個網際網路都能連到那個服務，任何 port 被公開幾分鐘內就會開始收到自動掃描。測試服務要加上驗證、只綁必要的介面，用完就關掉規則；需要長期對外的服務，應該放在有正式防護的環境，而不是家用路由器後面。

## 7.6 NAT 類型：mapping 與 filtering 兩個問題

到目前為止，NAT 的行為好像只有一種，其實不然。不同廠商、不同設定的 NAT，在兩個關鍵問題上的答案不一樣，而這兩個答案，直接決定了第一張工單裡的視訊能不能 P2P 直連。

第一個問題是 **mapping 行為**：同一個內部位址與 port，送往**不同的目的地**時，NAT 會不會沿用同一個對外 port？第二個問題是 **filtering 行為**：一個對外 port 已經存在 mapping 之後，**誰**可以從外面送封包進來？RFC 4787 把這兩個問題的答案各分成三級，名稱裡的「dependent」指的是「依對方的什麼而定」：

| 行為 | Endpoint-Independent（與對方無關） | Address-Dependent（依對方 IP 而定） | Address and Port-Dependent（依對方 IP 與 port 而定） |
|---|---|---|---|
| Mapping：換目的地時對外 port 是否改變 | 不變：送給誰都用同一個對外 port | 換了對方 IP 才換 port | 換了對方 IP 或 port 就換 port |
| Filtering：誰能送進這個對外 port | 任何人都可以 | 只有內部曾經送過的 IP | 只有內部曾經送過的 IP 加 port |
| 縮寫 | EIM／EIF | ADM／ADF | APDM／APDF |

表的上半列講 mapping，下半列講 filtering，三欄由寬鬆到嚴格。舉例：筆電從 192.168.1.20:5004 先送給 STUN server 192.0.2.1:3478，NAT 配了對外 port 50000；接著筆電從同一個 5004 送給通話的另一端 198.51.100.201:50000（例如美咲老師家的路由器）。如果是 EIM，這次還是用 50000；如果是 APDM，NAT 會另配一個 port，例如 50007。filtering 的例子：如果是 EIF，任何主機送到 50000 都會被轉給筆電；如果是 APDF，只有 192.0.2.1:3478 送來的封包能進來，因為筆電只對它送過封包。

早期的 STUN 規格（RFC 3489）用另一套名稱把 NAT 分成四類，至今仍是最常被提到的說法，對照如下：

| 舊稱 | Mapping | Filtering | 白話 |
|---|---|---|---|
| Full cone | EIM | EIF | 開了一個對外 port，任何人都能從這個 port 打進來 |
| Restricted cone | EIM | ADF | 對外 port 固定，但只收內部聯絡過的 IP |
| Port restricted cone | EIM | APDF | 對外 port 固定，只收內部聯絡過的 IP 加 port |
| Symmetric | APDM（有些文獻也把 ADM 算進來） | APDF | 每個目的地一個對外 port，只收那個目的地的回應 |

「cone（圓錐）」的意象是：一個內部 port 對應一個固定的對外 port，就像圓錐的尖端，從這個尖端可以朝很多不同的外部主機展開。三種 cone 的差別只在 filtering；symmetric 則連 mapping 都不固定。這套舊名稱的問題是它只描述四種組合，卻有很多真實 NAT 不落在這四格裡，例如 ADM 配 ADF，或者 mapping 行為會隨負載改變。RFC 5389 改版 STUN 時，就把「判斷 NAT 類型」的功能拿掉了，因為這種分類在真實網路中並不可靠；RFC 4787 的兩軸描述則比較精確。本書兩套名稱都會用，讀到舊稱時，請在腦中換成「mapping＋filtering」的組合。

```text
 Endpoint-Independent Mapping（cone 類）          Address and Port-Dependent Mapping（symmetric）

  內部 10.0.0.5:5004                              內部 10.0.0.5:5004
        │                                               │
   NAT  ▼  對外 :50000（只有一個）                  NAT  ├─► 對外 :50000 ──► STUN 192.0.2.1:3478
        ├──────────► STUN 192.0.2.1:3478              │
        ├──────────► 對方 B 198.51.100.201:50000       └─► 對外 :50007 ──► 對方 B 198.51.100.201:50000
        └──────────► 任何其他目的地
                                                    STUN 回報「你是 :50000」，
  STUN 回報「你是 :50000」，對 B 也成立              但 B 實際看到的是 :50007
```

左半是 cone 類 NAT：內部只有一個對外 port，送給誰都一樣，所以 STUN server 回報的「你在公網上是 :50000」，對其他任何人也成立。右半是 symmetric NAT：每換一個目的地就配一個新的對外 port，STUN server 看到的是 :50000，學生 B 看到的卻是 :50007。這就是 symmetric NAT 讓 P2P 變困難的根本原因：透過 STUN 學到的公網位址，只對 STUN server 有效，告訴對方也沒用。

RFC 4787 對 NAT 廠商提出的要求是：mapping **必須**是 endpoint-independent（REQ-1）；filtering 方面，若重視應用相容性，建議用 endpoint-independent，若重視嚴格過濾，建議用 address-dependent。也就是說，符合規範的 NAT 不應該是 symmetric。但規範是給新設備的建議，現實中仍有大量企業防火牆、部分 CGNAT 與舊設備採用 APDM，因為它讓外部更難推測內部的 port，在安全團隊眼中有吸引力。

> [!note] 2026 現況
> 截至 2026 年 10 月，家用路由器多半是 EIM 搭配 ADF 或 APDF（舊稱的 restricted 或 port restricted cone）；行動網路與企業網路的 NAT 行為差異很大，同一家電信在不同地區、不同時段的設備也可能不同。因此 WebRTC 不去「判斷 NAT 類型」，而是把所有可能的路徑都試一遍（ICE，第 36 章），失敗就退回 TURN 中繼。各平台公開的 TURN 使用比例差異很大，本書不引用特定數字。

## 7.7 Hole Punching：兩台 NAT 後的主機怎麼直接說話

視訊課最理想的路徑是學生與老師直接互傳 UDP 媒體，不經過聲聲 Live 的伺服器，延遲最低、頻寬成本也最低。問題是雙方都在 NAT 後面：老師的 NAT 不會讓學生的「第一個封包」進來，因為連線追蹤表裡沒有對應的列；學生那邊也一樣。這就像兩個人都住在只能從裡面開門的房子裡。

**Hole punching（打洞）** 的想法很聰明：既然 NAT 只放行「內部曾經送過的對象」的回應，那就讓雙方**同時**往對方的公網位址送封包。A 送出的封包會在 A 的 NAT 建立一列「A 曾經送給 B」；它到了 B 的 NAT 可能被丟棄，但沒關係。B 送出的封包也在 B 的 NAT 建立「B 曾經送給 A」；當它抵達 A 的 NAT，A 的表裡已經有「A 送過給 B」的紀錄，於是被當成回應放行。雙方的門都從裡面被打開了一個洞。下圖的主機 A 是學生的筆電，NAT-A 是學生家的路由器（198.51.100.23）；主機 B 是美咲老師的筆電，NAT-B 是老師家的路由器（198.51.100.201，restricted cone）。

```text
 主機 A        NAT-A（198.51.100.23）   STUN 192.0.2.1   signaling   NAT-B（198.51.100.201）    主機 B
   │── Binding ───────►│───────────────────►│                │                    │                │
   │◄─ 你是 198.51.100.23:50000 ────────────│                │                    │                │
   │                   │                    │◄───────────────────────────────── Binding ───────────│
   │                   │                    │── 你是 198.51.100.201:50000 ──────────────────────────►│
   │── 我的位址是 …:50000 ───────────────────────────────────►│── 轉交 ────────────────────────────►│
   │◄──────────────────────────────── 轉交 ─│◄─ 我的位址是 …:50000 ───────────────────────────────────│
   │── 打洞封包 ──────►│ 記下「送過給 B」 ─────────────────────────────────►│ B 沒送過給 A：丟棄    │
   │                   │◄──────────────────────────────── 記下「送過給 A」 │◄── 打洞封包 ─────│
   │◄──── 放行 ────────│ 表裡有「送過給 B」：放行                            │                    │
   │── 回應 ──────────►│──────────────────────────────────────────────────►│── 放行 ──────────►│
   │                         （雙向打通，之後媒體直接往返）                                          │
```

這張時序圖分成三段。第一段，A 和 B 各自問 STUN server「你看到我是誰」，得到自己的 **server-reflexive 位址**（從 NAT 外面看到的公網位址與 port）。第二段，雙方經由 **signaling**（傳遞連線資訊的管道，聲聲 Live 用 WebSocket；WebRTC 規格本身不定義 signaling）交換這個位址。第三段是打洞：A 先送的封包被 B 的 NAT 丟掉，但已經在 NAT-A 留下紀錄；B 送的封包到了 NAT-A，因為紀錄存在而被放行；A 收到後回應，這次 NAT-B 也有紀錄了，於是雙向打通。

這個流程能成功，靠的是兩個前提。第一，STUN 回報的位址對對方也成立，也就是 mapping 必須是 endpoint-independent；第二，雙方都主動送過封包，讓 filtering 的條件被滿足。只要其中一方是 symmetric NAT，第一個前提就破了：它送給對方的封包來自另一個對外 port，而對方的 NAT 若是 port restricted，只認得「自己送過的那個 IP 加 port」，就會把它丟掉。7.10 節的程式會把四種舊稱兩兩配對，逐一模擬，讓你看到哪些組合會失敗、為什麼失敗。

實務上 ICE 還多做了一步：收到對方封包時，記下封包「實際的來源位址」，就算它和 signaling 給的不同，也當成一個新的候選位址回應過去，這叫 **peer-reflexive candidate**。這一步讓 symmetric NAT 對上 cone NAT 的部分組合也能成功，因為 cone 那一側可以直接回覆 symmetric 那一側的真實對外 port。當兩邊都打不通時，ICE 會改用 **TURN**：一台公網上的中繼伺服器，雙方都主動連向它，由它轉送媒體。TURN 一定成功（只要能連上 TURN），但所有流量都經過伺服器，增加延遲與頻寬成本，這就是 Joe 那張工單在意的費用。

TCP 也能打洞，但難得多：需要雙方在幾乎同一時間送出 SYN（稱為 simultaneous open），很多 NAT 對「沒有先送 SYN 卻收到 SYN」的處理也不一致。這也是即時影音普遍用 UDP 的原因之一；當網路連 UDP 都封鎖時，WebRTC 會退回 TURN over TCP 或 TLS 443（第 36 章）。

## 7.8 CGNAT 與 IPv6：NAT 後面的 NAT

當電信業者連「每個家庭一個公網 IPv4」都給不起時，就在自己的網路裡再加一層大型 NAT，稱為 **CGNAT（Carrier-Grade NAT，電信級 NAT）**，也叫 LSN（Large Scale NAT）。用戶的路由器 WAN 介面拿到的是 100.64.0.0/10 的位址，真正的公網位址在電信的 CGNAT 上，由成百上千個用戶共用。行動網路幾乎都是這樣運作，部分固網也是。

```text
                         電信網路（100.64.0.0/10）
 家庭 1 192.168.1.0/24 ─► 路由器 WAN 100.72.18.9  ─┐
 家庭 2 192.168.0.0/24 ─► 路由器 WAN 100.72.18.10 ─┤
 手機 A（直接拿到）        100.80.3.21             ─┼─►  CGNAT  ──►  198.51.100.200  ──► 網際網路
 手機 B                   100.80.3.22             ─┤    每個用戶分配一段 port，例如
 ……（上千個用戶）                                   ─┘    100.72.18.9 → 198.51.100.200:22000–23999
```

這張拓撲圖有兩層 NAT：家庭的路由器把 192.168.x.x 轉成 100.64/10 的位址，CGNAT 再把 100.64/10 轉成公網的 198.51.100.200。手機通常直接拿到 100.64/10 的位址，只經過一層。圖右下的「每個用戶一段 port」叫 **port block allocation**：CGNAT 不是逐條連線隨機挑 port，而是一次分給每個用戶一段連續的 port，這樣記錄 log 時只需記「哪段時間、哪個用戶、哪段 port」，log 量少很多。代價是每個用戶能同時開的連線數有上限，用完就無法建立新連線。

這解答了 Rita 那張工單。198.51.100.200 後面可能是一整個區域的行動用戶，直接封鎖這個 IP，會把大量正常學生一起擋在門外。CGNAT 也改變了「怎麼查出是誰」：要讓電信追查某個濫用行為，只給 IP 和時間不夠，因為同一秒有上千個用戶共用這個 IP，還必須提供**來源 port** 和精確到秒的時間戳。RFC 6302 就建議面向網際網路的伺服器，log 要記錄來源 port 與精確時間。

| 情境 | 只看 IP 會怎樣 | 比較好的做法 |
|---|---|---|
| 封鎖濫用來源 | CGNAT 後的正常用戶一起被擋 | 以帳號、裝置、行為特徵為主，IP 只是其中一個訊號 |
| 依 IP 限流 | 同一棟宿舍或同一電信區域互相搶額度 | 依帳號或 API key 限流，IP 限流的門檻放寬 |
| 追查事件 | 無法對應到單一用戶 | log 記下來源 IP、來源 port、精確時間戳（含時區） |
| 地理位置判斷 | CGNAT 出口可能在另一個城市 | 只當參考，不作為唯一的授權依據 |

表的每一列都是同一個原則：在 NAT 普及的網路上，IP 位址代表的是「最後一台 NAT」，不是「一個人」。還要注意，聲聲 Live 的應用程式看到的來源 IP 通常是 load balancer 或 nginx，真正的用戶位址要從 X-Forwarded-For 或 PROXY protocol 取得，而且只能信任自己的 proxy 加上的那一段（第 43 章）。

CGNAT 對即時通訊的影響是雙重的：多一層 NAT，就多一層可能是 symmetric 的行為與更短的逾時；而且 CGNAT 後面的用戶完全無法設定 port forwarding 或 UPnP，因為那台 NAT 不歸用戶管。第一張工單裡「行動網路學生幾乎都走 TURN」，很可能就是某家電信的 CGNAT 使用了 APDM。

IPv6 是另一條出路。IPv6 位址充足，每台設備都能有全球位址，理論上不需要 NAT，P2P 也簡單得多。但「沒有 NAT」不代表「沒有防火牆」：家用路由器對 IPv6 預設仍會擋下外部主動進來的連線，只放行內部先聯絡過的對象，像是一台「不改寫位址的 stateful 防火牆」。所以 IPv6 之間仍然需要打洞，只是成功率高很多：位址與 port 都不被改寫，對方看到的就是自己真正的位址，等於天然的 endpoint-independent mapping。另外，有些只提供 IPv6 的行動網路會用 **NAT64**（搭配 DNS64），讓 IPv6 用戶存取只有 IPv4 的網站，這是另一種形式的位址轉換。

> [!warning] 常見誤解
> 「NAT 就是防火牆」「有 NAT 就安全」都不對。NAT 擋下外部主動連線，只是因為它不知道要轉給誰，這是副作用而不是設計目標；port forwarding、UPnP、hairpinning、IPv6 都可能讓內網主機直接暴露。需要的安全性要由明確的防火牆規則提供，下一節就談防火牆。

## 7.9 防火牆：stateless、stateful 與 security group

防火牆依規則決定每個封包的命運：放行（ACCEPT）、丟棄（DROP），或拒絕並通知對方（REJECT）。最簡單的防火牆是 **stateless（無狀態）**：每個封包獨立判斷，只看 header 欄位，例如「目的 port 是 443 就放行」。路由器上的 ACL（Access Control List）、雲端的 network ACL 都屬於這一類。它的問題出在回程：伺服器主動對外查 DNS，回應的目的 port 是一個隨機的 ephemeral port（第 9 章），stateless 規則要放行回應，就只能寫「來源 port 是 53 的 UDP 都放行」，這等於讓任何人只要把來源 port 設成 53，就能把封包送到任意 port。

**Stateful（有狀態）防火牆**用前面講過的連線追蹤表解決這個問題。它記得「這台主機曾經主動送出哪些連線」，所以能分辨一個進來的封包是「某條既有連線的回程」還是「陌生的新連線」。Linux conntrack 為每個封包標上一個狀態：

| conntrack 狀態 | 意思 | 例子 |
|---|---|---|
| NEW | 這個封包開啟一條新連線 | 從外面來的第一個 SYN；第一個 UDP 封包 |
| ESTABLISHED | 屬於一條雙向都看過流量的連線 | SYN 之後的 SYN+ACK、之後的所有資料 |
| RELATED | 和既有連線相關的新流量 | 針對既有連線送回的 ICMP 錯誤（例如第 8 章的 Fragmentation Needed） |
| INVALID | 不屬於任何連線，也不像是合法的開頭 | 沒有先送 SYN 卻冒出的 ACK；表中查無此連線的 RST |

有了狀態，規則就能寫得簡短又安全：第一條「ESTABLISHED、RELATED 一律放行」，接著「INVALID 一律丟棄」，然後才是幾條「允許哪些 NEW 連線」的規則，最後預設丟棄。下面是聲聲 Live API 主機的 nftables 設定：

```bash
# /etc/nftables.conf 的一部分（需要 root，示意）
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    ct state invalid drop
    iif "lo" accept
    tcp dport 443 accept
    ip saddr 10.20.0.0/16 tcp dport 22 accept
  }
}
```

這份規則從上往下讀，第一條符合的生效。`policy drop` 表示沒有任何規則符合時預設丟棄。前兩條處理有狀態的封包：已建立連線的回程直接放行，這也是效能上的考量，因為絕大多數封包都屬於既有連線，越早判斷越省；不合法的封包直接丟。接著放行本機 loopback、所有人的 HTTPS，以及只限 VPC 內部（10.20.0.0/16）的 SSH。注意這裡完全不需要為 DNS 回應或對外 API 呼叫的回程寫規則，conntrack 會自動處理。

DROP 和 REJECT 對除錯的影響很大。DROP 讓封包消失，客戶端只能等到逾時，curl 會卡住數十秒後報 timeout；REJECT 會回一個 TCP RST 或 ICMP port unreachable，客戶端立刻收到「Connection refused」。對外的防火牆常用 DROP，讓掃描的人拿不到資訊；內部網路用 REJECT 比較友善，錯誤會立刻浮現。看到「逾時」與「被拒」時，第一個要想的就是「封包是被防火牆丟了，還是到了主機但沒有程式在聽」（第 45 章會把這個判斷流程化）。

雲端把這兩種防火牆都提供給你。以 AWS 為例，**security group** 是 stateful 的，掛在每個網路介面上，只能寫「允許」規則，回程流量自動放行；**network ACL** 是 stateless 的，掛在 subnet 上，規則有編號、依序比對，可以寫允許也可以寫拒絕，回程的 ephemeral port 要自己開。其他雲端也有類似的分層，細節在第 44 章。

| 比較 | Security group（stateful） | Network ACL（stateless） |
|---|---|---|
| 作用位置 | 網路介面（每台主機） | Subnet（整個網段） |
| 回程流量 | 自動放行 | 要自己寫規則放行 ephemeral port |
| 規則種類 | 只有允許 | 允許與拒絕都可以 |
| 比對方式 | 所有規則一起評估，任一允許即放行 | 依編號由小到大，第一條符合的生效 |
| 典型用途 | 「API 主機只收 LB 來的 443」 | 「整個 subnet 拒絕某個網段」這類粗粒度防護 |

這張表的關鍵是第二列。新手在 network ACL 開了 443 入站，卻忘了開 1024–65535 的出站回程，結果連線建立不起來；在 security group 上則不會有這個問題。實務上以 security group 為主要防線，並用「引用另一個 security group」的方式表達「只允許來自 LB 的流量」，比寫死 IP 範圍更不容易出錯。

## 7.10 動手做：NAT 轉換表、打洞模擬與防火牆規則引擎

這一節用三段程式，把本章的三個核心機制各做一個可以實驗的模型。三段都只用標準函式庫，用模擬時鐘代替真實等待，執行不到一秒。

### 程式一：有連線追蹤、逾時與 port forwarding 的 NAT

第一段模擬學生家的路由器：SNAT 改寫來源、port preservation 與衝突處理、TCP 三向交握的狀態追蹤、UDP 的單向與雙向逾時、陌生封包被丟棄，以及一條 port forwarding 規則。逾時數值是教學用的設定，參考 Linux conntrack 的 UDP 預設值與 RFC 5382 的 TCP 下限。

```python
from dataclasses import dataclass

PUBLIC_IP = "198.51.100.23"                  # 學生家路由器的 WAN 位址
TIMEOUT = {"udp-new": 30, "udp-replied": 120, "tcp-syn": 120, "tcp-est": 7440, "tcp-fin": 120}

@dataclass
class Conn:                                  # 連線追蹤表的一列
    proto: str
    inside: tuple                            # 內部 (ip, port)
    public_port: int                         # 轉換後的對外埠
    remote: tuple                            # 對方 (ip, port)
    state: str
    expires: float

class Nat:
    def __init__(self):
        self.conns, self.forwards, self.log = {}, {}, []
        self.next_port = 40000

    def _alloc(self, proto, inside):
        used = {(c.proto, c.public_port) for c in self.conns.values()}
        used |= set(self.forwards)
        for c in self.conns.values():        # 同一個內部來源沿用既有對外埠（endpoint-independent mapping）
            if c.proto == proto and c.inside == inside:
                return c.public_port
        if (proto, inside[1]) not in used:   # port preservation：能保留原埠就保留
            return inside[1]
        while (proto, self.next_port) in used:
            self.next_port += 1
        return self.next_port

    def _touch(self, c, now, flags):
        if c.proto == "udp":
            c.state = "REPLIED" if c.state == "REPLIED" or flags == "reply" else "NEW"
            c.expires = now + TIMEOUT["udp-replied" if c.state == "REPLIED" else "udp-new"]
        else:
            if flags == "ACK":                # 三向交握的最後一個 ACK 才算 ESTABLISHED
                c.state = "ESTABLISHED" if c.state in ("SYN_RECV", "ESTABLISHED") else c.state
            else:
                c.state = {"SYN": "SYN_SENT", "SYN+ACK": "SYN_RECV", "FIN": "FIN_WAIT"}[flags]
            key = "tcp-est" if c.state == "ESTABLISHED" else "tcp-fin" if c.state == "FIN_WAIT" else "tcp-syn"
            c.expires = now + TIMEOUT[key]

    def outbound(self, now, proto, src, dst, flags=""):
        self.expire(now)
        key = (proto, src, dst)
        if key not in self.conns:
            self.conns[key] = Conn(proto, src, self._alloc(proto, src), dst, "NEW", 0)
        c = self.conns[key]
        self._touch(c, now, flags)
        return (PUBLIC_IP, c.public_port), dst                # SNAT：改寫來源

    def inbound(self, now, proto, src, dport, flags=""):
        self.expire(now)
        for c in self.conns.values():                        # 先查連線追蹤：是不是某條連線的回程？
            if c.proto == proto and c.public_port == dport and c.remote == src:
                self._touch(c, now, "reply" if proto == "udp" else flags)
                return c.inside
        if (proto, dport) in self.forwards and flags in ("", "SYN"):   # 再查 port forwarding（DNAT）
            inside = self.forwards[(proto, dport)]
            c = Conn(proto, inside, dport, src, "NEW", 0)
            self.conns[(proto, inside, src)] = c
            self._touch(c, now, "reply" if proto == "udp" else "SYN")
            return inside
        return None                                          # 沒有對應：丟棄

    def expire(self, now):
        for key in [k for k, c in self.conns.items() if c.expires <= now]:
            c = self.conns.pop(key)
            self.log.append(f"t={now:>5}s 逾時移除 {c.proto} {c.inside[0]}:{c.inside[1]} ↔ :{c.public_port}")

    def show(self, title):
        print(f"--- {title} ---")
        for c in self.conns.values():
            print(f"{c.proto} {c.inside[0]}:{c.inside[1]:<5} → {PUBLIC_IP}:{c.public_port:<5} ↔ "
                  f"{c.remote[0] + ':' + str(c.remote[1]):<20} {c.state:<11} 到期 t={c.expires:g}")

nat = Nat()
LAPTOP, PHONE, WEB, STUN = "192.168.1.20", "192.168.1.30", ("203.0.113.80", 443), ("192.0.2.1", 3478)
nat.forwards[("tcp", 8080)] = ("192.168.1.20", 8000)      # 家中筆電上的測試 server（設定方式同 7.5 節）

print("SNAT 筆電 SYN →", nat.outbound(0, "tcp", (LAPTOP, 51000), WEB, "SYN")[0])
assert nat.inbound(0.03, "tcp", WEB, 51000, "SYN+ACK") == (LAPTOP, 51000)
nat.outbound(0.04, "tcp", (LAPTOP, 51000), WEB, "ACK")
print("SNAT 手機 SYN →", nat.outbound(1, "tcp", (PHONE, 51000), WEB, "SYN")[0])   # 同一個來源埠：衝突
nat.outbound(2, "udp", (LAPTOP, 5004), STUN)
assert nat.inbound(2.05, "udp", STUN, 5004) == (LAPTOP, 5004)
nat.outbound(2.5, "udp", (LAPTOP, 5300), ("192.0.2.99", 53))   # 沒有回應的 UDP
print("陌生主機打 5004：", nat.inbound(3, "udp", ("192.0.2.66", 5555), 5004))
print("外部連 8080（port forwarding）→", nat.inbound(4, "tcp", ("198.51.100.140", 62000), 8080, "SYN"))
nat.outbound(4.01, "tcp", ("192.168.1.20", 8000), ("198.51.100.140", 62000), "SYN+ACK")
assert nat.inbound(4.05, "tcp", ("198.51.100.140", 62000), 8080, "ACK") == ("192.168.1.20", 8000)
nat.show("t=4 秒")

for t in (40, 125, 200):             # 之後完全沒有封包，只有時鐘往前走
    nat.expire(t)
nat.show("t=200 秒")
print("\n".join(nat.log))
print("STUN 回應遲到：", nat.inbound(201, "udp", STUN, 5004))
assert nat.inbound(201, "udp", STUN, 5004) is None
```

```text
SNAT 筆電 SYN → ('198.51.100.23', 51000)
SNAT 手機 SYN → ('198.51.100.23', 40000)
陌生主機打 5004： None
外部連 8080（port forwarding）→ ('192.168.1.20', 8000)
--- t=4 秒 ---
tcp 192.168.1.20:51000 → 198.51.100.23:51000 ↔ 203.0.113.80:443     ESTABLISHED 到期 t=7440.04
tcp 192.168.1.30:51000 → 198.51.100.23:40000 ↔ 203.0.113.80:443     SYN_SENT    到期 t=121
udp 192.168.1.20:5004  → 198.51.100.23:5004  ↔ 192.0.2.1:3478       REPLIED     到期 t=122.05
udp 192.168.1.20:5300  → 198.51.100.23:5300  ↔ 192.0.2.99:53        NEW         到期 t=32.5
tcp 192.168.1.20:8000  → 198.51.100.23:8080  ↔ 198.51.100.140:62000 ESTABLISHED 到期 t=7444.05
--- t=200 秒 ---
tcp 192.168.1.20:51000 → 198.51.100.23:51000 ↔ 203.0.113.80:443     ESTABLISHED 到期 t=7440.04
tcp 192.168.1.20:8000  → 198.51.100.23:8080  ↔ 198.51.100.140:62000 ESTABLISHED 到期 t=7444.05
t=   40s 逾時移除 udp 192.168.1.20:5300 ↔ :5300
t=  125s 逾時移除 tcp 192.168.1.30:51000 ↔ :40000
t=  125s 逾時移除 udp 192.168.1.20:5004 ↔ :5004
STUN 回應遲到： None
```

逐段解讀輸出。第一行，筆電的 SYN 從 51000 出去，NAT 保留了原 port，對外是 198.51.100.23:51000。第二行，手機也從 51000 連同一台伺服器，如果再用 51000，回程封包會分不清是誰的，所以 `_alloc` 改配 40000。第三行，一台陌生主機 192.0.2.66 往 5004 送封包；雖然 5004 上有一筆 mapping（筆電剛問過 STUN），但連線追蹤表裡沒有「和 192.0.2.66:5555 的連線」，也沒有 port forwarding 規則，所以回傳 None，也就是丟棄。這就是 address and port-dependent filtering。第四行，外部連到 8080，命中 port forwarding，轉給筆電的 8000。

`t=4 秒` 的表格就是連線追蹤表。筆電的 HTTPS 連線已經完成三向交握，進入 ESTABLISHED，到期時間是兩個多小時後；手機的連線只送了 SYN、還沒有回應，停在 SYN_SENT，到期時間只有 120 秒，這讓半開的連線很快被回收。兩筆 UDP 的差別在於有沒有收到回應：問 STUN 的那筆收到過回應，標為 REPLIED，給 120 秒；送往 192.0.2.99:53 的那筆從沒收到回應，只給 30 秒。最後一列是 port forwarding 建出來的連線，它的 inside 是筆電的 8000，對外 port 是規則指定的 8080。

接著時鐘走到 200 秒，中間完全沒有封包。逾時紀錄顯示：t=40 時，沒有回應的 UDP 被移除；t=125 時，半開的 TCP 與 STUN 的 UDP 也被移除；兩條 ESTABLISHED 的 TCP 還在。最後一行最關鍵：STUN server 在 t=201 才送來回應，這時 mapping 已經消失，NAT 只能丟棄。這就是 7.4 節白板問題的縮影，也是 WebRTC 需要定期送 STUN keepalive 的原因。

### 程式二：四種 NAT 類型兩兩打洞

第二段把 NAT 的 mapping 與 filtering 做成可以切換的參數，然後讓兩台主機照 7.7 節的流程打洞：先問 STUN 得到 server-reflexive 位址，再輪流往對方送封包；收到封包的一方改回覆「實際看到的來源」，也就是 peer-reflexive candidate。

```python
from itertools import combinations_with_replacement

STUN = ("192.0.2.1", 3478)
# 四種舊稱 = (mapping 行為, filtering 行為)；EI = endpoint-independent，AD = address-dependent，APD = address-and-port-dependent
TYPES = {"full cone": ("EI", "EI"), "restricted": ("EI", "AD"),
         "port restricted": ("EI", "APD"), "symmetric": ("APD", "APD")}

class Nat:
    def __init__(self, public_ip, kind):
        self.ip, (self.mapping, self.filtering) = public_ip, TYPES[kind]
        self.maps, self.sent_to, self.next_port = {}, set(), 50000

    def send(self, dst):
        # mapping 行為決定：「換一個目的地」時要不要換一個對外埠
        key = {"EI": (), "AD": (dst[0],), "APD": (dst,)}[self.mapping]
        if key not in self.maps:
            self.maps[key] = self.next_port
            self.next_port += 7                    # 刻意跳號，讓不同 mapping 一眼看得出來
        port = self.maps[key]
        self.sent_to.add((port, dst))              # 記下「這個埠曾經送給誰」，filtering 要查
        return (self.ip, port)

    def accept(self, src, port):
        # filtering 行為決定：誰可以從外面打進這個對外埠
        if port not in self.maps.values():
            return False
        if self.filtering == "EI":
            return True
        if self.filtering == "AD":
            return any(p == port and d[0] == src[0] for p, d in self.sent_to)
        return (port, src) in self.sent_to

def punch(kind_a, kind_b, rounds=3, trace=False):
    nats = {"A": Nat("198.51.100.23", kind_a), "B": Nat("198.51.100.201", kind_b)}
    # 1. 各自問 STUN：「你看到我是誰？」得到 server-reflexive 位址，經 signaling 交換
    srflx = {host: nat.send(STUN) for host, nat in nats.items()}
    target = {"A": srflx["B"], "B": srflx["A"]}
    heard = {"A": False, "B": False}
    for r in range(1, rounds + 1):
        for me, peer in (("A", "B"), ("B", "A")):
            src = nats[me].send(target[me])        # 2. 對著對方的公網位址送 UDP
            ok = nats[peer].accept(src, target[me][1])
            if trace:
                print(f"  第 {r} 輪 {me} 從 {src[1]} 送往 {target[me][0]}:{target[me][1]}：{'收到' if ok else '被對方 NAT 丟棄'}")
            if ok:
                heard[peer] = True
                target[peer] = src                 # 3. 對方改回覆「實際看到的來源」（peer-reflexive）
        if all(heard.values()):
            return r
    return None

print("示範一：symmetric（A）對 restricted（B）")
assert punch("symmetric", "restricted", trace=True) == 2
print("示範二：symmetric（A）對 port restricted（B）")
assert punch("symmetric", "port restricted", trace=True) is None

print("\n打洞結果矩陣（數字＝第幾輪雙向打通，✗＝要靠 TURN 中繼）")
names = list(TYPES)
print(" " * 16 + "".join(f"{n:>16}" for n in names))
for a in names:
    cells = [punch(a, b) for b in names]
    print(f"{a:<16}" + "".join(f"{(str(c) if c else '✗'):>16}" for c in cells))
fails = [(a, b) for a, b in combinations_with_replacement(names, 2) if punch(a, b) is None]
print("失敗組合：", fails)
assert fails == [("port restricted", "symmetric"), ("symmetric", "symmetric")]
```

```text
示範一：symmetric（A）對 restricted（B）
  第 1 輪 A 從 50007 送往 198.51.100.201:50000：被對方 NAT 丟棄
  第 1 輪 B 從 50000 送往 198.51.100.23:50000：被對方 NAT 丟棄
  第 2 輪 A 從 50007 送往 198.51.100.201:50000：收到
  第 2 輪 B 從 50000 送往 198.51.100.23:50007：收到
示範二：symmetric（A）對 port restricted（B）
  第 1 輪 A 從 50007 送往 198.51.100.201:50000：被對方 NAT 丟棄
  第 1 輪 B 從 50000 送往 198.51.100.23:50000：被對方 NAT 丟棄
  第 2 輪 A 從 50007 送往 198.51.100.201:50000：被對方 NAT 丟棄
  第 2 輪 B 從 50000 送往 198.51.100.23:50000：被對方 NAT 丟棄
  第 3 輪 A 從 50007 送往 198.51.100.201:50000：被對方 NAT 丟棄
  第 3 輪 B 從 50000 送往 198.51.100.23:50000：被對方 NAT 丟棄

打洞結果矩陣（數字＝第幾輪雙向打通，✗＝要靠 TURN 中繼）
                       full cone      restricted port restricted       symmetric
full cone                      1               2               2               2
restricted                     1               2               2               2
port restricted                1               2               2               ✗
symmetric                      1               2               ✗               ✗
失敗組合： [('port restricted', 'symmetric'), ('symmetric', 'symmetric')]
```

先看示範一，A 是 symmetric、B 是 restricted cone。第 1 輪，A 往 B 的 server-reflexive 位址送，但因為目的地和 STUN server 不同，A 的 NAT 配了新的對外 port 50007；B 還沒送過任何東西給 A 的 IP，restricted cone 的 ADF 把它丟掉。B 接著往 A 的 server-reflexive 位址 50000 送，A 那邊是 APDF，50000 只對 STUN server 送過，所以也丟掉。第 2 輪，A 再送一次，這次 B 已經送過給 A 的 IP，而 ADF 只檢查 IP、不檢查 port，於是放行；B 從封包看到 A 的真實對外 port 是 50007，改往 50007 回覆，A 的 NAT 有「50007 送過給 B」的紀錄，雙向打通。

示範二只把 B 換成 port restricted，結果完全不同：B 的 NAT 只放行「B 送過的 IP 加 port」，也就是 A 的 50000；但 A 送來的封包永遠來自 50007。B 收不到，就學不到 50007，只能繼續往 50000 送，而 A 的 50000 只認 STUN server。雙方卡在互相錯過的迴圈裡，輪數再多也沒用。

矩陣把所有組合列出來，列是 A、欄是 B，A 先送。只有兩個組合失敗：port restricted 對 symmetric，以及 symmetric 對 symmetric。規則可以這樣記：**只要一方的 mapping 會隨目的地改變，另一方的 filtering 就必須不檢查 port**，否則打洞失敗。其他格子裡 1 與 2 的差異，只是「A 先送」造成的輪數差別：B 是 full cone 時，A 先送的封包第 1 輪就能進來，B 立刻回覆，當輪就雙向打通；其他情況要等到第 2 輪。真實的 ICE 會反覆重送連線檢查，輪數差異不重要，重要的是 ✗ 的那兩格只能靠 TURN。這張矩陣也解釋了 Joe 的觀察：如果某家電信的 CGNAT 是 symmetric，那麼它的用戶和大多數家用 port restricted 路由器後面的老師配對，都會落在 ✗ 的格子裡。

### 程式三：stateful 防火牆規則引擎

第三段實作一個依序比對、first match wins 的規則引擎，加上連線追蹤，規則與 7.9 節的 nftables 設定對應。最後再用一個 stateless 的版本對照，看看少了狀態會出什麼問題。

```python
import ipaddress
from dataclasses import dataclass

SERVER = "10.20.1.10"                         # 聲聲 Live 的 API 主機（VPC 內）

@dataclass(frozen=True)
class Pkt:
    t: float
    direction: str                            # "in" 進入主機、"out" 離開主機
    proto: str
    src: tuple
    dst: tuple
    flags: str = ""                           # TCP 旗標，例如 "S"（SYN）、"A"（ACK）

# 規則依序比對，第一條符合的生效（first match wins）
RULES = [
    ("1 已建立連線的回程", dict(ct={"ESTABLISHED"}), "ACCEPT"),
    ("2 狀態不合法", dict(ct={"INVALID"}), "DROP"),
    ("3 HTTPS", dict(direction="in", proto="tcp", dport=443), "ACCEPT"),
    ("4 SSH 只限 VPC", dict(direction="in", proto="tcp", dport=22, src="10.20.0.0/16"), "ACCEPT"),
    ("5 對外連線都放行", dict(direction="out"), "ACCEPT"),
]
DEFAULT = "DROP"
UDP_TIMEOUT, TCP_TIMEOUT = 30, 7440

class Firewall:
    def __init__(self):
        self.table = {}                       # 5-tuple（以發起方向為準）-> 到期時間
        self.hits = {name: 0 for name, _, _ in RULES} | {"預設政策": 0}

    def ct_state(self, p):
        fwd, rev = (p.proto, p.src, p.dst), (p.proto, p.dst, p.src)
        for key in (fwd, rev):
            if key in self.table and self.table[key] > p.t:
                return "ESTABLISHED", key
        if p.proto == "tcp" and p.flags != "S":
            return "INVALID", None            # 沒看過 SYN 卻冒出 ACK：不屬於任何連線
        return "NEW", None

    def match(self, cond, p, state):
        if "ct" in cond and state not in cond["ct"]:
            return False
        if "direction" in cond and p.direction != cond["direction"]:
            return False
        if "proto" in cond and p.proto != cond["proto"]:
            return False
        if "dport" in cond and p.dst[1] != cond["dport"]:
            return False
        if "src" in cond and ipaddress.ip_address(p.src[0]) not in ipaddress.ip_network(cond["src"]):
            return False
        return True

    def handle(self, p):
        state, key = self.ct_state(p)
        rule, verdict = "預設政策", DEFAULT
        for name, cond, action in RULES:
            if self.match(cond, p, state):
                rule, verdict = name, action
                break
        self.hits[rule] += 1
        if verdict == "ACCEPT":               # 放行的封包才會建立或延長連線追蹤
            ttl = TCP_TIMEOUT if p.proto == "tcp" else UDP_TIMEOUT
            self.table[key or (p.proto, p.src, p.dst)] = p.t + ttl
        return state, rule, verdict

CLIENT, DNS = ("198.51.100.40", 52344), ("10.20.0.2", 53)
packets = [
    Pkt(0.00, "in", "tcp", CLIENT, (SERVER, 443), "S"),
    Pkt(0.01, "out", "tcp", (SERVER, 443), CLIENT, "SA"),
    Pkt(0.02, "in", "tcp", CLIENT, (SERVER, 443), "A"),
    Pkt(1.00, "in", "tcp", ("198.51.100.9", 41000), (SERVER, 22), "S"),
    Pkt(1.50, "in", "tcp", ("10.20.3.4", 41001), (SERVER, 22), "S"),
    Pkt(2.00, "out", "udp", (SERVER, 40000), DNS),
    Pkt(2.01, "in", "udp", DNS, (SERVER, 40000)),
    Pkt(3.00, "in", "udp", ("198.51.100.66", 53), (SERVER, 40001)),
    Pkt(4.00, "in", "tcp", ("192.0.2.80", 80), (SERVER, 33000), "A"),
    Pkt(60.0, "in", "udp", DNS, (SERVER, 40000)),          # 30 秒逾時之後才到的回應
]
fw = Firewall()
verdicts = []
for p in packets:
    state, rule, verdict = fw.handle(p)
    verdicts.append(verdict)
    src, dst = f"{p.src[0]}:{p.src[1]}", f"{p.dst[0]}:{p.dst[1]}"
    print(f"t={p.t:<5} {p.direction:<3} {p.proto} {src:<20} → {dst:<16} {p.flags:<2} {state:<11} {verdict:<6} {rule}")
assert verdicts == ["ACCEPT"] * 3 + ["DROP", "ACCEPT", "ACCEPT", "ACCEPT", "DROP", "DROP", "DROP"]
print("\n規則命中次數：", {k: v for k, v in fw.hits.items() if v})

# 對照：stateless ACL 看不到「這是誰的回程」，要讓 DNS 回應進來只能寫「來源埠 53 的 UDP 都放行」
def stateless(p):
    return p.direction == "out" or (p.proto == "udp" and p.src[1] == 53)
print("stateless 對 t=3.0 那個陌生封包：", "ACCEPT" if stateless(packets[7]) else "DROP")
assert stateless(packets[7])
```

```text
t=0.0   in  tcp 198.51.100.40:52344  → 10.20.1.10:443   S  NEW         ACCEPT 3 HTTPS
t=0.01  out tcp 10.20.1.10:443       → 198.51.100.40:52344 SA ESTABLISHED ACCEPT 1 已建立連線的回程
t=0.02  in  tcp 198.51.100.40:52344  → 10.20.1.10:443   A  ESTABLISHED ACCEPT 1 已建立連線的回程
t=1.0   in  tcp 198.51.100.9:41000   → 10.20.1.10:22    S  NEW         DROP   預設政策
t=1.5   in  tcp 10.20.3.4:41001      → 10.20.1.10:22    S  NEW         ACCEPT 4 SSH 只限 VPC
t=2.0   out udp 10.20.1.10:40000     → 10.20.0.2:53        NEW         ACCEPT 5 對外連線都放行
t=2.01  in  udp 10.20.0.2:53         → 10.20.1.10:40000    ESTABLISHED ACCEPT 1 已建立連線的回程
t=3.0   in  udp 198.51.100.66:53     → 10.20.1.10:40001    NEW         DROP   預設政策
t=4.0   in  tcp 192.0.2.80:80        → 10.20.1.10:33000 A  INVALID     DROP   2 狀態不合法
t=60.0  in  udp 10.20.0.2:53         → 10.20.1.10:40000    NEW         DROP   預設政策

規則命中次數： {'1 已建立連線的回程': 3, '2 狀態不合法': 1, '3 HTTPS': 1, '4 SSH 只限 VPC': 1, '5 對外連線都放行': 1, '預設政策': 3}
stateless 對 t=3.0 那個陌生封包： ACCEPT
```

前三行是一次 HTTPS 交握：SYN 是 NEW，被規則 3 放行並寫入連線追蹤表；之後主機送出的 SYN+ACK 和客戶端的 ACK 都被認出是 ESTABLISHED，由規則 1 放行，根本不必再比對後面的規則。第四、五行是 SSH：來自網際網路的 198.51.100.9 落到預設政策被丟棄，來自 VPC 內 10.20.3.4 的被規則 4 放行。

第六、七行示範 stateful 最大的價值：主機主動查 DNS（規則 5 放行並建表），回應進來時被認成 ESTABLISHED，我們從頭到尾沒有為「DNS 回應」寫任何入站規則。第八行是偽裝成 DNS 回應的陌生封包，來源 port 也是 53，但它的五元組不在表裡，所以被丟棄。第九行是一個沒有 SYN 就出現的 ACK，被判為 INVALID，由規則 2 丟棄；掃描工具常用這種封包試探防火牆。最後一行是 DNS 回應在 30 秒逾時後才到，這時表中的紀錄已過期，它被當成 NEW，落到預設政策被丟棄。

最後一行是 stateless 的對照：要讓 DNS 回應進來，只能寫「來源 port 53 的 UDP 都放行」，於是第八行那個陌生封包就被放進來了。規則命中次數也透露一個實務事實：大多數封包都由第一條「已建立連線」規則處理，這就是為什麼這條規則永遠放在最前面。

## 7.11 在工作上怎麼用

回到三張工單。小晴照阿德的建議，把每一張都轉成具體的檢查與修正。

**後端：處理 Rita 的封鎖需求。** 先查 198.51.100.200 的 log 有多少不同帳號、不同 User-Agent，如果是上百個看起來正常的帳號，它八成是 CGNAT 出口。改成以帳號與裝置為單位限流，並對短時間大量註冊加上驗證。同時確認 nginx 與應用程式的 log 格式有記錄來源 port 與精確時間戳，並且取的是 LB 傳來的真實用戶位址，而不是 LB 自己的位址：

```bash
# nginx log_format 的一部分（示意）：$remote_port 是來源 port；在 LB 後面要搭配 realip 模組取得真實位址
log_format main '$remote_addr:$remote_port [$time_iso8601] "$request" $status';
```

**前端與即時服務：處理白板斷線。** 確認 WebSocket 每 25 秒左右送一次 ping，伺服器在一段時間沒收到 pong 時主動關閉並讓前端重連；同時檢查 LB 與 nginx 的 idle timeout 都比心跳間隔長（第 33 章與第 43 章）。驗證方法：在測試環境放一台 Linux 閘道，把 conntrack 的 TCP established 逾時調成 60 秒，開著白板不動兩分鐘，觀察有無心跳時的行為差異。

**影音：處理 TURN 比例。** Joe 從 getStats 統計各電信、各網路類型最後選中的 candidate 類型（host、srflx、prflx、relay），找出 relay 比例特別高的網路。如果集中在少數 CGNAT，代表那裡是 symmetric 行為，只能靠 TURN；這時重點變成把 TURN 部署在離用戶近的地區，並提供 TURN over TLS 443 給封鎖 UDP 的學校網路（第 37 章）。

**SRE：檢查 Linux 主機上的連線追蹤。** 聲聲 Live 的 NAT 閘道與高流量主機，要監控 conntrack 表的使用量；表滿時新連線會被無聲丟棄，而且 dmesg 會出現特定訊息：

```bash
# 連線追蹤表目前的筆數與上限（示意）
sysctl net.netfilter.nf_conntrack_count net.netfilter.nf_conntrack_max
# 表滿時核心會留下這行紀錄
dmesg | grep "nf_conntrack: table full"
# 依狀態統計，找出大量 SYN_SENT 或 TIME_WAIT 的來源
conntrack -L 2>/dev/null | awk '{print $4}' | sort | uniq -c | sort -rn | head
```

**資安：審查防火牆與 security group。** Rita 的檢查清單：預設政策是否為拒絕；ESTABLISHED、RELATED 是否在最前面、INVALID 是否丟棄；管理用 port（SSH、資料庫）是否只對內網或 bastion 開放；security group 是否用「引用 LB 的 security group」而不是 0.0.0.0/0；有沒有任何 port forwarding 或 UPnP 讓內部服務意外暴露；IPv6 是否有與 IPv4 對等的規則。最後一項很常被遺漏：只寫了 IPv4 的 iptables 規則，主機卻有全球 IPv6 位址，等於後門大開；nftables 的 `inet` 表可以同時涵蓋兩者。

遇到「連不上」時，可以照這個順序判斷問題出在 NAT、防火牆還是應用程式：

```text
 「從外面連不到服務」
   │
   ├─ 從主機本機連 127.0.0.1:port 成功嗎？ ── 否 ──► 應用程式沒在聽或綁錯介面（ss -ltnp）
   │        是
   ├─ 從同網段其他主機連私有位址成功嗎？ ── 否 ──► 主機防火牆（nft list ruleset、security group）
   │        是
   ├─ 從外部連公網位址：逾時還是被拒？
   │        ├─ 被拒（RST）──► 封包到了某台設備，但 DNAT 目的錯誤或該 port 沒人聽
   │        └─ 逾時 ────────► 邊界防火牆 DROP、port forwarding 沒設、或在 CGNAT 後面根本收不到
   │
   └─ 在閘道上抓包：tcpdump -ni eth0 port 8080，看 SYN 有沒有進來、DNAT 後有沒有送出
```

這個流程由內往外一層一層排除。第一層確認程式本身在聽，常見錯誤是程式只綁在 127.0.0.1，外面當然連不到。第二層繞過 NAT，只測主機防火牆。第三層才牽涉 NAT 與邊界，這時「逾時」與「被拒」的區別最有診斷價值：被拒代表封包抵達了某台設備，逾時代表封包在路上某處消失。最後在閘道兩側抓包，直接看 SYN 有沒有進來、改寫後有沒有送出去，就能確定問題在哪一段。

## 7.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| WebSocket 或 SSH 閒置幾分鐘後無聲斷線，下一個操作才報錯 | 路徑上某台 NAT 或防火牆的閒置逾時刪除了 mapping | 伺服器 log 看到同一用戶重連後來源 port 改變；在客戶端抓包看到送出後收到 RST | 應用層心跳（20–30 秒）或縮短 TCP keepalive；同步檢查 LB 與 proxy 的 idle timeout |
| 設好 port forwarding，外面還是連不到 | 只寫了 DNAT，FORWARD 鏈或主機防火牆仍然丟棄；或服務只綁 127.0.0.1；或用戶在 CGNAT 後面 | `ss -ltnp` 看綁定位址；閘道上 `tcpdump` 看 DNAT 後有沒有送出；比對路由器 WAN 位址是否落在 100.64.0.0/10 | 補上轉送規則與主機防火牆規則；服務綁到正確介面；CGNAT 下改用雲端主機或 tunnel |
| 在家裡用公網位址連自己的服務失敗，外部卻正常 | 路由器不支援 hairpinning | 從內網用私有位址連成功、用公網位址連失敗 | 內網直接用私有位址，或內部 DNS 用 split-horizon |
| 高流量時新連線隨機失敗，舊連線正常 | conntrack 表滿 | `dmesg` 出現「nf_conntrack: table full, dropping packet」；`nf_conntrack_count` 接近 `nf_conntrack_max` | 調高上限並評估記憶體；縮短不必要的逾時；不需要追蹤的流量考慮不經 conntrack |
| 封鎖一個濫用 IP 後，客服湧入大量「登入不了」 | 該 IP 是 CGNAT 或企業 NAT 的出口，後面有大量正常用戶 | 統計該 IP 的不同帳號數與 User-Agent 分布 | 撤銷 IP 封鎖，改以帳號、裝置與行為限流 |
| 視訊在特定電信或學校網路一律走 TURN，甚至完全連不上 | 對方是 symmetric NAT 或封鎖 UDP | getStats 看選中的 candidate 類型；用不同 STUN server 測得的對外 port 不同 | 部署 TURN（UDP、TCP、TLS 443），讓 relay 成為可靠的後備 |
| 關掉 network ACL 的某條規則後，連線都建立不起來 | stateless ACL 沒放行回程的 ephemeral port | 流量 log 中只看到入站被接受、出站回應被拒 | 補上 ephemeral port 範圍的回程規則，或改用 stateful 的 security group 控管 |
| 主機 IPv4 防火牆很嚴，掃描卻發現服務對外開放 | 只設定了 IPv4 規則，IPv6 沒有任何限制 | `ip -6 addr` 看到全球位址；從外部用 IPv6 連線成功 | 用 nftables `inet` 表同時涵蓋 IPv4 與 IPv6，或補上 IPv6 規則 |

這張表最值得記住的是第一列與第四列，它們都是「沒有錯誤訊息的失敗」：mapping 逾時讓封包無聲消失，conntrack 表滿讓新連線無聲被丟。這類問題在應用程式 log 裡只會看到 timeout，必須到網路設備或核心 log 上找證據。

## 7.13 動手練習

1. **加上 hairpinning。**修改程式一的 `Nat`，讓內網主機送往 `198.51.100.23:8080` 的封包能被 DNAT 到 192.168.1.20:8000，並同時 SNAT 成路由器位址，使回應正確回到發起者。驗證方法：加一個 `assert`，確認內網主機 192.168.1.30 經由公網位址連到測試 server，回程查表後交回 192.168.1.30。
2. **加入 address-dependent mapping。**在程式二的 `TYPES` 加入 `"ADM+ADF": ("AD", "AD")` 與 `"ADM+APDF": ("AD", "APD")`，先在紙上預測它們和四種舊類型配對的結果，再執行比對。答案要點：ADM 的行為和 symmetric 一樣，換了對方 IP 就換 port，所以配上 APDF 的一方會失敗，配上不檢查 port 的 filtering 則可以成功。
3. **加入 REJECT 與速率限制。**在程式三新增一種動作 `REJECT`，回傳時附上「會回 RST」或「會回 ICMP port unreachable」的說明；再加一條規則：同一來源 IP 每 10 秒最多 5 個 NEW 連線到 443。驗證方法：送 7 個 SYN，前 5 個 ACCEPT、後 2 個 DROP，且 ESTABLISHED 封包不受影響。
4. **找出自己在幾層 NAT 後面。**在家用網路與手機熱點下各做一次：看電腦的區網位址，登入路由器管理頁面看 WAN 位址，再用任何一個「顯示你的公網 IP」的服務看外面眼中的位址。驗證方法：如果路由器 WAN 位址落在 100.64.0.0/10 或另一段私有位址，而外面看到的又是另一個位址，代表你至少在兩層 NAT 後面。
5. **觀察逾時與被拒。**在一台 Linux VM 上用 nftables 對 TCP 9000 設定 `drop`、對 9001 設定 `reject with tcp reset`，用 `nc -l 9002` 開一個真實服務，從另一台機器分別 `nc -vz` 三個 port，記錄等待時間與錯誤訊息。答案要點：9000 等到逾時、9001 立刻「Connection refused」、9002 成功，而且 `conntrack -L` 只會看到成功的那一條變成 ESTABLISHED。
6. **用真實的 conntrack 驗證逾時。**在 Linux VM 上執行 `sudo conntrack -E -p udp`（事件模式），另開視窗用 `dig` 對區網內的 DNS resolver 送一個 UDP 查詢（若 VM 沒有對外網路，改對同網段的另一台機器送 `nc -u`）。驗證方法：看到 NEW 與 UPDATE 事件，約 30 秒後看到 DESTROY，時間差就是核心的 UDP 逾時設定。

## 本章重點整理

- NAT 存在的主因是 IPv4 位址不夠用；RFC 1918 私有位址可在各內網重複使用，出入網際網路時必須在邊界轉換成公網位址。
- 實務上的 NAT 幾乎都是 NAPT：同時改寫 IP 與 port，並重算 IPv4 header checksum 與受 pseudo-header 影響的 TCP／UDP checksum。
- SNAT 改寫出去封包的來源，DNAT 改寫進來封包的目的；port forwarding 就是一條預先設定的 DNAT 規則。
- 連線追蹤表記錄每條連線的原始與轉換後位址；回程封包查表才知道要交給誰，查不到就丟棄，所以 NAT 天生只允許「裡面先開口」。
- 連線追蹤的每一列都有閒置逾時，真實設備常比 RFC 建議的短；長連線必須用應用層心跳或 keepalive，讓間隔小於路徑上最短的逾時。
- NAT 類型用兩個問題描述：mapping（換目的地時對外 port 變不變）與 filtering（誰能送進來），各分為 endpoint-independent、address-dependent、address and port-dependent 三級。
- 舊稱 full cone、restricted、port restricted 都是 endpoint-independent mapping，只差在 filtering；symmetric 的 mapping 會隨目的地改變，使 STUN 學到的位址對對方無效。
- Hole punching 讓雙方同時往對方的公網位址送封包，各自在自己的 NAT 留下「送過給對方」的紀錄；當一方的 mapping 隨目的地改變、另一方的 filtering 又檢查 port 時就會失敗，只能靠 TURN 中繼。
- CGNAT 讓上千個用戶共用一個公網 IP；IP 不等於一個人，封鎖、限流與追查都要改以帳號為主，log 必須記錄來源 port 與精確時間戳。
- IPv6 不需要 NAT，但仍有 stateful 防火牆；NAT 不是安全機制，安全要靠明確的防火牆規則。
- Stateless 防火牆每個封包獨立判斷，回程要自己開 ephemeral port；stateful 防火牆用 conntrack 的 NEW、ESTABLISHED、RELATED、INVALID 狀態，自動放行回程。
- 規則依序比對、first match wins，ESTABLISHED 放最前面、INVALID 直接丟、最後預設拒絕；DROP 讓對方逾時，REJECT 讓對方立刻收到被拒。
- 雲端的 security group 是 stateful、掛在網路介面、只有允許規則；network ACL 是 stateless、掛在 subnet、依編號比對。

## 延伸問答

> [!question]- Q1. 「我們的主機在 NAT 後面，所以不需要防火牆。」這句話哪裡有問題？
> NAT 擋下外部主動連線，是因為連線追蹤表裡沒有對應的列，它不知道要把封包轉給誰；這是位址轉換的副作用，不是一個經過設計、可以審查的安全政策。只要有任何機制讓表裡出現對應，例如有人設了 port forwarding、某個程式透過 UPnP 自己開了 port、或內網主機中了惡意程式主動連出去建立反向通道，外部流量就能進來。
>
> 另外，主機若同時有 IPv6 全球位址，IPv6 流量根本不經過 NAT；同一個內網裡的其他主機也不受 NAT 限制，橫向移動完全不會被擋。正確的做法是把 NAT 當成位址轉換工具，安全性用明確的防火牆規則與 security group 表達，預設拒絕、只開必要的 port，並同時涵蓋 IPv4 與 IPv6。

> [!question]- Q2. 手算：一個公網 IPv4 位址最多能同時支撐多少條連往同一台伺服器 203.0.113.80:443 的 TCP 連線？如果 CGNAT 每個用戶分配 2,000 個 port，一個公網 IP 可以分給多少用戶？
> 對同一個目的地（IP 與 port 都相同），五元組裡只剩對外的來源 port 可以變化。port 是 16 位元，扣掉 1024 以下的 well-known port，1024 到 65535 共 64,512 個可用 port，所以理論上限約六萬多條。實際可用範圍依 NAT 設定而定，常見的設備只用其中一段。若 NAT 依完整五元組追蹤連線，連往不同目的地的連線可以重複使用同一個對外 port，總連線數可以超過這個上限。
>
> CGNAT 若用 port block allocation 每個用戶 2,000 個 port，一個公網 IP 大約可分給 64,512 ÷ 2,000 ≈ 32 個用戶。這也說明了一個取捨：每個用戶分得越多 port，一個公網 IP 能服務的用戶越少；分得太少，開很多分頁或很多 App 的用戶會耗盡 port，出現新連線失敗。

> [!question]- Q3. 你在 production 的 NAT 閘道上看到 dmesg 出現「nf_conntrack: table full, dropping packet」，同時應用程式回報間歇性的連線逾時。該怎麼處理？
> 這行訊息代表連線追蹤表已達 `nf_conntrack_max`，新連線無法建表，第一個封包就被丟棄，所以客戶端只看到 SYN 沒有回應、最後逾時；已建立的連線則照常運作，這和「間歇性、只影響新連線」的症狀完全吻合。先用 `nf_conntrack_count` 與 `conntrack -L` 依狀態統計，看看表被什麼佔滿。
>
> 如果是大量 SYN_SENT 或 UNREPLIED，可能是遭到掃描或某個下游服務沒有回應；如果是大量閒置的 ESTABLISHED，可能是逾時設定過長。短期內可以調高上限（每一筆都會佔用核心記憶體，要一起評估），中長期則縮短不必要的逾時、找出異常流量來源，必要時讓不需要追蹤的流量繞過 conntrack，並把 `nf_conntrack_count / nf_conntrack_max` 加進監控與告警。

> [!question]- Q4. 聲聲 Live 的 log 顯示，同一位學生的白板 WebSocket 每隔 5 到 6 分鐘就斷線重連一次，而且每次重連時來源 port 都不一樣。最可能的原因是什麼？
> 規律的時間間隔加上來源 port 改變，強烈暗示路徑上有一台 NAT 的閒置逾時大約是 5 分鐘：閒置期間 mapping 被刪除，下一個封包被當成新的流量並配上新的對外 port，伺服器眼中這是一個陌生的五元組，於是回 RST，前端偵測到斷線後重連，log 上就出現一個新的來源 port。
>
> 確認方法是看斷線前那段時間有沒有任何流量，以及前端的心跳設定是否真的生效。修法是讓 WebSocket 每 20 到 30 秒送一次 ping，間隔小於路徑上最短的逾時；同時確認 LB 與 nginx 的 idle timeout 比心跳長，否則換成那一層提早切斷連線。如果只有特定電信的用戶有這個現象，就更能確定是那家電信的 CGNAT 逾時較短。

> [!question]- Q5. 面試題：為什麼 symmetric NAT 會讓 P2P 失敗？為什麼 symmetric 對 full cone 或 restricted cone 卻能成功？
> P2P 打洞的前提是：透過 STUN 學到的公網位址，對另一個對象也成立。symmetric NAT 的 mapping 會隨目的地改變，送給 STUN server 用一個對外 port，送給對方又換一個，所以對方拿到的位址是錯的。若對方是 port restricted 或 symmetric，它只接受「自己送過的 IP 加 port」來的封包，而 symmetric 那一側的封包永遠來自另一個 port，雙方互相錯過。
>
> 若對方是 full cone，任何人送到它的對外 port 都會被接受；若是 restricted cone，只檢查 IP、不檢查 port，而對方早已往 symmetric 那一側的 IP 送過封包。所以 symmetric 那一側的封包能進來，對方再從封包學到真實的來源 port（peer-reflexive candidate），往那個 port 回覆就打通了。歸納成一句話：一方的 mapping 隨目的地改變時，另一方的 filtering 不能檢查 port。

> [!question]- Q6. Rita 想把來源 IP 198.51.100.200 加進拒絕清單，但這個 IP 背後是某家電信的 CGNAT。你會怎麼設計防濫用機制？
> 首先要承認 IP 在 CGNAT 時代只是一個弱訊號：它代表的是最後一台 NAT，後面可能有上千個正常用戶，直接封鎖的誤傷成本遠高於收益。所以防濫用的主體應該是帳號、裝置與行為：例如同一裝置短時間大量註冊、同一付款方式綁定大量帳號、試聽課申請的頻率異常，這些都比 IP 精準。
>
> IP 仍可以作為輔助：對單一 IP 設定較寬鬆的限流門檻，觸發時改成要求額外驗證而不是直接封鎖。log 要記錄來源 IP、來源 port 與精確時間戳，必要時才能請電信協助追查到單一用戶；並且確認拿到的是真實用戶位址，而不是 LB 或 CDN 的位址。這樣既能擋住濫用，也不會讓整個區域的學生登入不了。

> [!question]- Q7. 對外服務的防火牆應該用 DROP 還是 REJECT？兩者在除錯上有什麼差別？
> DROP 讓封包無聲消失，客戶端只能等到逾時，TCP 連線會重送 SYN 好幾次才放棄，curl 常常卡上數十秒；REJECT 會立刻回 TCP RST 或 ICMP port unreachable，客戶端馬上收到「Connection refused」。對掃描者來說，DROP 透露的資訊比較少，也讓大規模掃描變慢，所以面向網際網路的邊界常用 DROP。
>
> 對內部網路則通常建議 REJECT：誤設規則時錯誤會立刻浮現，不會讓服務之間的呼叫卡在逾時、拖垮整條呼叫鏈的延遲。除錯時這個差別本身就是線索：「被拒」代表封包抵達了某台設備，「逾時」代表封包在路上某處被丟、或回應回不來。兩者混用時，記得在文件中寫清楚各層的行為，否則值班的人會被誤導。

> [!question]- Q8. 如果全世界都改用 IPv6、不再有 NAT，P2P 視訊是不是就不需要 STUN 和 TURN 了？
> 不會完全不需要。IPv6 讓每台設備都有全球位址，位址與 port 不再被改寫，對方看到的就是真實位址，最大的障礙（symmetric mapping）消失了，打洞的成功率會高很多。但家用路由器與企業網路對 IPv6 仍有 stateful 防火牆，預設只放行內部先聯絡過的對象，所以雙方仍然要「同時往對方送封包」，也就是 ICE 的連線檢查仍然必要。
>
> STUN 仍有用處，例如做連線檢查與 keepalive，也能在 dual-stack 的環境中處理仍在 IPv4 NAT 後面的一方；而企業網路可能完全封鎖 UDP 或只允許經由 proxy 的 443，這時還是只能靠 TURN over TLS 中繼。實務上 IPv4 與 IPv6 會長期並存，WebRTC 會同時收集兩種位址的 candidate，選出能通的最佳路徑。

## 延伸閱讀

- RFC 4787〈Network Address Translation (NAT) Behavioral Requirements for Unicast UDP〉
- RFC 5382〈NAT Behavioral Requirements for TCP〉
- RFC 3022〈Traditional IP Network Address Translator (Traditional NAT)〉
- RFC 5128〈State of Peer-to-Peer (P2P) Communication across Network Address Translators (NATs)〉
- RFC 6888〈Common Requirements for Carrier-Grade NATs (CGNs)〉
- RFC 6598〈IANA-Reserved IPv4 Prefix for Shared Address Space〉
- RFC 6302〈Logging Recommendations for Internet-Facing Servers〉
- netfilter 與 nftables 專案的官方文件（nftables wiki、conntrack-tools 手冊）
