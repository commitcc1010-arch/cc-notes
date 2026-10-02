# 附錄 B　工具指令速查

> [!abstract] 本附錄地圖
> **用途**：值班或除錯時，手上已經有一個症狀（「找不到主機」「連不上」「很慢」「憑證錯誤」「WebSocket 一直斷」），需要立刻知道該下哪個指令、加哪些參數、輸出要看哪一行。本附錄把第 3 章介紹的工具箱、第 45 章的除錯流程，以及散落在各章的進階用法，整理成依「任務」排列的速查表。
>
> **怎麼查**：先看 B.1 的任務索引，找到最像眼前症狀的那一列，再跳到對應小節。每個工具都依同樣的順序列出：常用指令、關鍵參數、輸出怎麼讀、平台差異（Linux／macOS／Windows）、對應章節。B.11 是三個平台的指令對照總表，B.12 是一段把 HAR 去敏感化並切分時間的 Python 小工具。
>
> **慣例**：指令中的位址與網域沿用聲聲 Live 的範例（`api.shengsheng.example` 是 API LB 203.0.113.80，`www` 的 CDN edge 是 203.0.113.10，VPC resolver 是 10.20.0.2）；標「示意輸出」的區塊是依真實工具格式整理的範例，不同版本的措辭與欄位會略有差異。需要 root 的指令以 `sudo` 標出。在 production 主機上抓封包、執行 `kubectl exec` 之前，先確認公司的權限與證據處理規範（第 45 章）。

## B.1 任務索引：從症狀找到工具

第 45 章的除錯方法可以濃縮成一句話：先確定是哪一層壞了，再用那一層的工具拿證據。下表把常見症狀對到「先問的是非題」與「先用的工具」，最後一欄是本附錄的小節與書中的章節。

| 症狀（使用者或告警的說法） | 先回答的是非題 | 先用的工具 | 本附錄 | 對應章節 |
|---|---|---|---|---|
| 找不到主機、`NXDOMAIN`、`ERR_NAME_NOT_RESOLVED` | DNS server 有沒有這筆紀錄？程式看到的答案和 dig 一樣嗎？ | `dig`、`getent hosts`、`resolvectl query` | B.2 | 第 3、14–16 章 |
| 部分使用者連到舊 IP | 不同 resolver 的答案與剩餘 TTL 一樣嗎？ | `dig @<resolver>`、`curl -w '%{remote_ip}'` | B.2、B.8 | 第 15、45 章 |
| `Connection refused` | 封包有到主機、只是沒人在聽嗎？ | `nc -vz`、`ss -ltnp` | B.3、B.7 | 第 3、10 章 |
| `Connection timed out` | SYN 有沒有抵達目標？ | `nc -vz`、目標端 `tcpdump` 抓 SYN | B.3、B.6 | 第 6、7、10、44 章 |
| `Network is unreachable` | 本機路由表有沒有符合的路由？ | `ip route get`、`route -n get` | B.3 | 第 6 章 |
| 很慢 | 慢在 DNS、交握、TLS、TTFB 還是下載？ | `curl -w`、DevTools Timing | B.4、B.8 | 第 3、45 章 |
| 只有大回應卡住 | 大封包過得去嗎？ | `ping` 加 DF、`tracepath`、`ss -tin` | B.3、B.4 | 第 8 章 |
| 憑證警告、`CERTIFICATE_VERIFY_FAILED` | 帶正確 SNI 拿到的憑證，鏈完整、日期與名稱都對嗎？ | `openssl s_client -servername`、`openssl x509` | B.5 | 第 18、19 章 |
| 偶爾「連線已重設」、502 | 是誰先送 FIN 或 RST？ | `tcpdump` 抓 FIN／RST | B.6 | 第 10、45 章 |
| `Too many open files`、連線數一直漲 | CLOSE_WAIT 是不是越來越多？ | `ss -tan state close-wait`、`lsof -p` | B.7 | 第 10 章 |
| Console 顯示 CORS 錯誤 | preflight 的 status 與 header 是什麼？ | DevTools Network、`curl -X OPTIONS` | B.8 | 第 23 章 |
| WebSocket 斷線 | close code 是多少？距離上一則訊息幾秒？ | DevTools WS、`curl` 握手、`ss` | B.9 | 第 32、33 章 |
| 視訊連不上或單向 | ICE 有沒有 connected？兩個方向的 bytes 都在增加嗎？ | `chrome://webrtc-internals` | B.9 | 第 36、39 章 |
| 直播推流破圖 | `pktRcvDrop` 有沒有在增加？ | `srt-live-transmit` 統計 | B.9 | 第 38 章 |
| Pod 連不到服務或外部 API | 失敗集中在哪些節點？DNS 與 NetworkPolicy 正常嗎？ | `kubectl get pod -o wide`、`kubectl exec` | B.10 | 第 16、44 章 |

這張表刻意讓第三欄的每個工具都只回答一個問題，而且多半一分鐘內就能執行完。第 45 章的「前五分鐘」檢查清單也是同樣的精神，下面這張流程圖把它和本附錄的小節對起來：

```text
 告警或工單進來
   │
   ├─① 寫下範圍與時間：誰受影響？從何時？最近改了什麼？（部署、DNS、憑證、設定）
   │
   ├─② 從外面量一次 ──► curl -sv -o /dev/null -w '…五段時間與 remote_ip…'          B.4、B.8
   │      │
   │      ├─ 卡在名稱解析 ──────► dig／getent／resolvectl                            B.2
   │      ├─ 卡在 TCP（refused／timeout）► nc、ss、ip route、目標端 tcpdump            B.3、B.6、B.7
   │      ├─ 卡在 TLS ──────────► openssl s_client -servername                       B.5
   │      └─ TTFB 或下載慢 ─────► x-request-id 查後端 log；ss -tin 看視窗            B.4
   │
   ├─③ 分半：--resolve 繞過 CDN 直打 LB，再直打一台 nginx                           B.8
   │
   └─④ 在可疑主機上先保留證據再止血：ss -s、ss -ltn、close-wait 數量、nstat、pcap    B.6、B.7
```

這張圖由上往下走。第 ① 步不下任何指令，但它決定了後面要在哪裡量：受影響的是單一學校，就要從那個網路量；受影響的是所有人，從自己的電腦量就夠。第 ② 步用一次 `curl -w` 把請求切成五段，最大的那一段直接決定下一個工具。第 ③ 步是第 45 章的分半法：`--resolve` 讓 Host、SNI 與憑證比對都保持正確，只換掉連線的目的 IP。第 ④ 步提醒的是紀律：重開服務會把 socket 狀態、accept queue 與封包證據一起清掉，所以要先記錄。

## B.2 名稱解析有問題：dig、nslookup、resolvectl、getent

名稱解析的除錯有一個核心觀念（第 3、16 章）：**dig 問的是 DNS server，應用程式問的是作業系統**。應用程式呼叫 `getaddrinfo()`，會先經過 `/etc/hosts`、nsswitch、本機快取與 search domain；dig 則直接組一個 DNS 封包送出去。兩者答案不同時，不要只相信其中一個。

```text
 問題：「程式解析到的 IP 不對／很慢」
   │
   ├─ 程式的視角 ──► getent ahosts（Linux）、dscacheutil -q host（macOS）、Resolve-DnsName（Windows）
   │                   └─ 經過 /etc/hosts、nsswitch、本機快取、search domain
   ├─ 本機 resolver 的設定 ──► resolvectl status（systemd-resolved）、scutil --dns（macOS）
   │                            cat /etc/resolv.conf（容器與多數伺服器）
   └─ DNS server 的回答 ──► dig @<resolver>、dig +norecurse（只看快取）、dig +trace（從 root 走一遍）
```

三層由上往下查。第一層是程式真正拿到的答案，第二層是作業系統把查詢交給誰、套了哪些 search domain，第三層才是 DNS server 本身。`getent` 慢而 `dig` 快，問題在本機這幾層（search 展開、`/etc/hosts`、nameserver 順序）；兩者都慢，問題在 nameserver 或上游；延遲剛好 5 秒或 10 秒，優先懷疑封包遺失與 conntrack 競態（第 16 章）。

### dig

```bash
dig api.shengsheng.example                          # 預設查 A，問 resolv.conf 裡的第一台
dig +short api.shengsheng.example AAAA              # 只印答案，查 IPv6
dig +noall +answer api.shengsheng.example @10.20.0.2        # 指定 resolver，只看 ANSWER
dig +noall +answer +norecurse api.shengsheng.example @198.51.100.53   # 只看對方快取
dig +trace api.shengsheng.example                   # 從 root 一路往下問（第 14 章）
dig api.shengsheng.example @203.0.113.53 +norecurse # 直接問權威 server，應該看到 aa
dig SOA shengsheng.example                          # 負面快取時間看 SOA（第 15 章）
dig -x 203.0.113.80                                 # 反查 PTR
dig +short www.shengsheng.example HTTPS             # HTTPS record（type 65，第 13 章）
dig +dnssec +multi shengsheng.example DNSKEY        # DNSSEC 相關紀錄
dig +tcp api.shengsheng.example                     # 強制用 TCP 53
dig +bufsize=1232 api.shengsheng.example            # 指定 EDNS UDP 大小（第 8、15 章）
```

| 參數 | 作用 | 什麼時候用 |
|---|---|---|
| `@server` | 指定要問的 DNS server | 比較 VPC resolver、ISP resolver 與權威 server 的答案 |
| `+short` | 只印答案 | 寫進腳本或快速確認 |
| `+noall +answer` | 只印 ANSWER section（含 TTL） | 比對不同 resolver 的剩餘 TTL |
| `+norecurse` | 不要求遞迴（rd 位元為 0） | 確認 resolver 快取裡有什麼；問權威 server |
| `+trace` | 從 root 開始迭代查詢 | 委派錯誤、NS 不一致、懷疑某一層 zone |
| `+tcp`、`+bufsize=N` | 改用 TCP、設定 EDNS UDP 大小 | 大回應被截斷（TC 位元）、懷疑分片被丟 |
| `+dnssec` | 要求 DNSSEC 紀錄（DO 位元） | 驗證失敗導致 SERVFAIL |
| `+search` | 套用 resolv.conf 的 search domain | 模擬程式對短名稱的展開（第 16 章） |
| `-x` | 反查 | 從 IP 找名稱（log 裡只有 IP 時） |

**輸出怎麼讀**（完整範例見第 3 章）：

| 位置 | 看什麼 | 判讀 |
|---|---|---|
| `status:` | NOERROR／NXDOMAIN／SERVFAIL／REFUSED | NXDOMAIN 是名稱不存在；NOERROR 但 ANSWER 為 0 是「名稱存在但沒有這種型別」；SERVFAIL 是 resolver 解析過程失敗（上游逾時、DNSSEC 驗證失敗）；REFUSED 是對方不替你服務 |
| `flags:` | `qr rd ra aa tc` | `aa` 代表權威回答；`ra` 缺少代表對方不做遞迴；`tc` 代表被截斷，應改用 TCP 重問 |
| ANSWER 的第二欄 | TTL（秒） | 在 resolver 上連續查會看到倒數；搬家時「全部切換完成」的時刻是「修改時刻＋舊 TTL」（第 45 章） |
| AUTHORITY 的 SOA | 負面快取時間 | NXDOMAIN 會被快取這麼久（第 15 章） |
| `Query time` | 查詢耗時 | 數千毫秒代表 resolver 慢或重試 |
| `SERVER:` | 實際回答的 server 與傳輸（UDP／TCP） | 確認你問的是你以為的那一台 |

### nslookup 與 Windows 的 Resolve-DnsName

```bash
nslookup api.shengsheng.example                     # 用系統設定的 DNS server
nslookup -type=AAAA api.shengsheng.example 198.51.100.53   # 指定型別與 server
nslookup -debug api.shengsheng.example              # 印出更多細節（含 TTL）
```

```powershell
Resolve-DnsName api.shengsheng.example -Type A -Server 10.20.0.2
Resolve-DnsName api.shengsheng.example -DnsOnly     # 只走 DNS，不查 hosts 檔與其他本機機制
Get-DnsClientServerAddress                          # 每張網卡設定的 DNS server
ipconfig /displaydns                                # 看本機 DNS 快取
```

nslookup 在三個平台都有，輸出比 dig 簡略，而且不顯示 rcode 細節；它在 Windows 上最常見，但不走 Windows 的完整解析流程，所以「nslookup 查得到、瀏覽器查不到」在 Windows 上同樣可能發生。Windows 上的完整替代是 PowerShell 的 `Resolve-DnsName`：它能指定型別與 server，輸出包含 TTL 與 section，`-DnsOnly` 可以排除 hosts 檔等本機來源，用來對照兩者差異。

### resolvectl、getent 與各平台的「程式視角」

```bash
# Linux（systemd-resolved）
resolvectl status                    # 每張網卡實際的上游 DNS、search domain、DNSSEC 設定
resolvectl query api.shengsheng.example   # 透過 systemd-resolved 解析，顯示來源與耗時
resolvectl statistics                # 快取命中、DNSSEC 統計
sudo resolvectl flush-caches         # 清 systemd-resolved 的快取
# Linux（通用）：走 getaddrinfo＋nsswitch，等同程式的視角
getent ahosts api.shengsheng.example
time getent hosts pay.example.net
grep '^hosts:' /etc/nsswitch.conf; cat /etc/resolv.conf
# macOS
scutil --dns                         # 實際生效的 resolver（含 VPN 加入的網域）
dscacheutil -q host -a name api.shengsheng.example
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
# 任何平台：直接用 Python 呼叫 getaddrinfo
python3 -c "import socket; print({ai[4][0] for ai in socket.getaddrinfo('api.shengsheng.example', 443)})"
```

| 平台 | 程式視角的解析 | 看實際上游與 search | 清 OS 快取 |
|---|---|---|---|
| Linux（systemd-resolved） | `getent ahosts`、`resolvectl query` | `resolvectl status`（resolv.conf 只會看到 127.0.0.53） | `resolvectl flush-caches` |
| Linux（容器、無 systemd-resolved） | `getent ahosts` | `cat /etc/resolv.conf`（Pod 內看 nameserver 10.96.0.10 與 `ndots`） | 通常沒有 OS 快取；程式或 runtime 自己的快取要重啟 |
| macOS | `dscacheutil -q host -a name` | `scutil --dns` | `dscacheutil -flushcache` 並重啟 mDNSResponder |
| Windows | `Resolve-DnsName`（不加 `-DnsOnly`） | `Get-DnsClientServerAddress`、`ipconfig /all` | `ipconfig /flushdns` 或 `Clear-DnsClientCache` |
| Chrome | 瀏覽器自己的 host cache | `chrome://net-internals/#dns` | 同一頁的「Clear host cache」 |

清快取前先確認是哪一層的快取（第 15、16 章）：清了 OS 快取，瀏覽器、JVM 或連線池裡既有的長連線仍然記得舊答案。驗證「程式正在連誰」最可靠的方法不是 DNS 工具，而是 `ss -tn`（Linux）或 `lsof -nP -i`（macOS）看實際的遠端位址。

## B.3 連不上：ping、traceroute／mtr／tracert、nc、ip／ifconfig／route

「連不上」至少有四種完全不同的結果，先分清楚再選工具（第 10、45 章）：

| 結果 | 時間特徵 | 代表什麼 | 下一步 |
|---|---|---|---|
| `Network is unreachable` | 立刻失敗，線上沒有任何封包 | 本機路由表沒有符合的路由 | `ip route`、`ip route get` |
| `Connection refused` | 約一個 RTT | SYN 到了，對方核心回 RST：沒人聽、port 錯、只聽 127.0.0.1、REJECT 規則 | 對方主機 `ss -ltnp` |
| `Connection timed out` | 卡到 connect 逾時（Linux SYN 重傳間隔 1、2、4 秒…倍增） | SYN 沒有任何回應：security group／NACL／路由丟包、accept queue 滿、目標已不存在 | 目標端 `tcpdump` 抓 SYN；`nstat` |
| 連上了但沒回應 | 交握很快，卡在讀取 | 應用程式 worker 卡住或上游慢 | `curl -w`、nginx `$upstream_header_time` |

### ping

```bash
ping -c 4 api.shengsheng.example            # Linux／macOS：送 4 個就停
ping -c 4 -i 0.2 -W 1 10.20.3.21            # Linux：間隔 0.2 秒、每個回應最多等 1 秒
ping -M do -s 1472 -c 3 10.40.0.23          # Linux：設 DF，測 1500 MTU（1472＋8＋20）
ping -D -s 1472 -c 3 10.40.0.23             # macOS：-D 設 DF
ping -6 -c 4 api.shengsheng.example         # IPv6（舊系統用 ping6）
```

```powershell
ping -n 4 api.shengsheng.example            # Windows 預設送 4 個；-t 持續送
ping -f -l 1472 10.40.0.23                  # Windows：-f 設 DF、-l 指定資料大小
```

| 參數 | Linux | macOS | Windows |
|---|---|---|---|
| 次數 | `-c N`（預設一直送） | `-c N`（預設一直送） | `-n N`（預設 4）；`-t` 一直送 |
| 資料大小 | `-s N` | `-s N` | `-l N` |
| 不可分片（DF） | `-M do` | `-D` | `-f` |
| 逾時 | `-W 秒`（每個回應）、`-w 秒`（總時間） | `-W 毫秒`（每個回應）、`-t 秒`（總時間） | `-w 毫秒` |
| IPv4／IPv6 | `-4`／`-6` | `ping`／`ping6`（新版也接受 `-6` 等選項，依版本） | `-4`／`-6` |

**輸出怎麼讀**：第一行的位址就是一次 DNS 檢查；`icmp_seq` 跳號代表遺失；`ttl=` 可以粗略推測對方初始 TTL（64、128、255）與跳數；統計行的 `mdev` 是延遲的變異，大就是 jitter 大（第 3、34 章）。`56(84)` 的意思是 ICMP 資料 56 bytes，加 8 bytes ICMP header 與 20 bytes IPv4 header 共 84 bytes。測 MTU 時，IPv4 乙太網路的上限資料大小是 1500−20−8＝1472；IPv6 是 1500−40−8＝1452；出現 `Frag needed`、`Message too long` 或 Windows 的「Packet needs to be fragmented but DF set」，代表那個大小過不去（第 8 章）。

ping 用的是 ICMP，和服務的 TCP 不是同一條規則：ping 不通不代表服務掛了（許多 LB 與防火牆不回 echo），ping 得通也不代表 TCP 443 有開。

### traceroute、tracepath、mtr、tracert、pathping

```bash
traceroute -n api.shengsheng.example            # Linux 預設 UDP 33434 起、最多 30 跳；macOS 最多 64 跳
traceroute -n -I api.shengsheng.example         # 改用 ICMP echo
sudo traceroute -n -T -p 443 api.shengsheng.example   # Linux：TCP SYN 到 443，走和真實流量相同的規則
traceroute -n -P TCP -p 443 api.shengsheng.example    # macOS：-P 指定協定（依版本，可能要 sudo）
tracepath -n 10.20.3.17                         # Linux：不需要 root，逐跳顯示 PMTU（第 8 章）
mtr -n -r -w -c 100 api.shengsheng.example      # 報表模式，送 100 輪
mtr -n -T -P 443 -r -c 100 api.shengsheng.example     # 用 TCP 443 探測
mtr -n -u -r -c 100 turn.shengsheng.example     # 用 UDP 探測
```

```powershell
tracert -d api.shengsheng.example               # Windows：ICMP echo，-d 不反查名稱
pathping -n api.shengsheng.example              # Windows：先 tracert，再對每跳統計丟包（要數分鐘）
```

| 想做的事 | Linux | macOS | Windows |
|---|---|---|---|
| 不反查名稱 | `-n` | `-n` | `-d`（tracert）、`-n`（pathping） |
| 探測協定 | 預設 UDP；`-I` ICMP；`-T` TCP（root） | 預設 UDP；`-I` ICMP；`-P` 指定協定 | 只有 ICMP |
| 指定 port | `-p` | `-p` | 無 |
| 最大跳數 | `-m`（預設 30） | `-m`（預設 64） | `-h`（預設 30） |
| 持續統計 | `mtr` | `mtr`（需另外安裝，通常要 sudo） | `pathping` |
| 顯示 PMTU | `tracepath` | 無內建 | 無內建 |

**輸出怎麼讀**（第 3、6 章）：每一行是一跳，三個時間是三個探測的 RTT。中間某一跳顯示 `* * *`、但後面的跳都有回應，只代表那台路由器不回或限速回 ICMP；**真正的斷點是從某一跳開始，之後每一跳都是星號**。mtr 的判讀規則相同：丟包要從某一跳開始一路延續到終點才是真的丟包，只有中間某一跳 42%、終點 0%，是那台設備把回 ICMP 放在低優先順序。路徑常常不對稱，最好從使用者端與伺服器端各跑一次。

mtr 的欄位依序是 `Loss%`、`Snt`（送出數）、`Last`、`Avg`、`Best`、`Wrst`、`StDev`。加 `-z` 會顯示每跳的 AS 編號（需要查詢外部資料，離線環境不可用），對判斷「卡在哪一家 ISP」有幫助（第 6 章）。

### nc 與替代品

```bash
nc -vz -w 3 api.shengsheng.example 443      # 只做 TCP 交握，3 秒逾時
nc -vz -w 3 10.20.17.15 5432                # 資料庫 port 有沒有開
nc -vz 10.20.3.21 8000-8010                 # 掃一段 port（OpenBSD 版支援範圍）
nc -l 8000                                  # OpenBSD 版開 listener；傳統版要寫 nc -l -p 8000
nc -u -l 9910                               # UDP listener
printf 'GET /readyz HTTP/1.1\r\nHost: api.shengsheng.example\r\nConnection: close\r\n\r\n' \
  | nc 10.20.3.21 8000                      # 手打 HTTP/1.1（第 20 章）
timeout 3 bash -c '</dev/tcp/10.20.17.15/5432' && echo open   # 容器裡沒有 nc 時用 bash 內建功能
```

```powershell
Test-NetConnection 203.0.113.80 -Port 443   # Windows：看 TcpTestSucceeded（別名 tnc）
```

| 輸出 | 意思 |
|---|---|
| `succeeded!`／`open`／`TcpTestSucceeded : True` | 三向交握完成：有程式在 listen，而且路徑放行 |
| `Connection refused` | 收到 RST：主機在，但 port 沒人聽或被 REJECT |
| 等到 `-w` 秒數後 `timed out` | SYN 沒有回應：被 DROP、路由不通、主機不存在 |
| `-u` 模式顯示成功 | **幾乎不能證明什麼**：UDP 沒有交握，只有收到 ICMP Port Unreachable 才知道失敗 |

平台差異：nc 有 OpenBSD 版、傳統 GNU 版與 Nmap 附帶的 `ncat`，旗標不完全相同；macOS 內建的 nc 用 `-G 秒數` 設定連線逾時，`-w` 是閒置逾時。Windows 沒有內建 nc，用 `Test-NetConnection`。驗證 UDP 服務要用該協定自己的工具：DNS 用 dig、STUN／TURN 用 WebRTC 的 `icecandidateerror`（B.9），SRT 用 `srt-live-transmit`。

### ip、ifconfig、route：本機的位址、路由與鄰居

```bash
ip -br addr                         # 每張網卡一行：狀態與位址（第 5 章）
ip link show eth0                   # MTU、狀態（Pod 內看 overlay 的 MTU，第 44 章）
ip route                            # 路由表；ip -6 route 看 IPv6
ip route get 203.0.113.80           # 這個目的地會走哪條路由、哪張網卡、哪個來源 IP（第 6 章）
ip route get 10.40.0.23             # 也會顯示 PMTU 快取（cache expires … mtu 1420，第 8 章）
ip neigh                            # ARP／NDP 表：REACHABLE、STALE、FAILED（第 4 章）
ip rule                             # policy routing 規則
sudo ip netns exec red ip route     # 在某個 network namespace 裡執行（第 44 章）
```

| 想看什麼 | Linux | macOS | Windows |
|---|---|---|---|
| 位址與遮罩 | `ip -br addr`、`ip addr` | `ifconfig en0`、`ipconfig getifaddr en0` | `ipconfig /all`、`Get-NetIPAddress` |
| MTU | `ip link show eth0` | `ifconfig en0`（mtu 欄） | `netsh interface ipv4 show subinterfaces` |
| 路由表 | `ip route`、`ip -6 route` | `netstat -rn -f inet`、`netstat -rn -f inet6` | `route print`、`Get-NetRoute` |
| 某個目的地走哪條路 | `ip route get <IP>` | `route -n get <IP>` | `Find-NetRoute -RemoteIPAddress <IP>` |
| ARP／鄰居表 | `ip neigh` | `arp -an`、`ndp -an` | `arp -a`、`Get-NetNeighbor` |
| 舊工具（net-tools） | `ifconfig`、`route -n`、`arp -n`（多數發行版已不預設安裝） | 即為主要工具 | 無 |

**輸出怎麼讀**：`ip route get` 一次列出最長匹配的結果、出口介面、gateway 與來源位址，比自己對著路由表手算可靠。路由表的顯示順序和優先順序無關，真正決定的是 prefix 長度，其次才是 metric（第 6 章）。連上 VPN 後某些內網連不到，先看 `ip route get` 的出口是不是 `docker0`、`br-*` 之類的本機網路：本機 Docker 網段與公司網段重疊是最常見的本機路由衝突（第 6、44 章）。

## B.4 慢：把一次請求切成五段

「慢」不能直接查，要先切開（第 3、45 章）。命令列用 `curl -w`，瀏覽器用 DevTools 的 Timing，兩者的欄位一一對應：

```text
 0        namelookup     connect        appconnect   pretransfer     starttransfer      total
 │── DNS ───│── TCP 交握 ───│── TLS 交握 ───│── 送請求 ──│── 等第一個 byte ──│── 下載 body ──│
   resolver    約 1 RTT        1 RTT＋憑證     ~0           RTT＋伺服器處理      頻寬、視窗、buffer
   第 14–16 章 第 6–8、10 章   第 18、19 章                 第 20、24、43 章     第 11、12、21、25 章
```

`curl -w` 的每個時間都是**從開始累計的秒數**，相鄰相減才是每一段的長度。HTTP（非 HTTPS）網址的 `time_appconnect` 是 0，要改用 `time_connect` 接下一段。

```bash
curl -s -o /dev/null -w '
dns        %{time_namelookup}
connect    %{time_connect}
tls        %{time_appconnect}
ttfb       %{time_starttransfer}
total      %{time_total}
code %{http_code} ip %{remote_ip}:%{remote_port} ver %{http_version} conns %{num_connects} size %{size_download}
' https://api.shengsheng.example/v1/schedule

curl -s -o /dev/null -w '%{json}\n' https://api.shengsheng.example/readyz   # 新版 curl：一次印出所有變數
for i in $(seq 1 20); do                                                   # 間歇性慢：重複量，看分布
  curl -s -o /dev/null -w '%{time_namelookup} %{time_connect} %{time_starttransfer}\n' \
    https://api.shengsheng.example/readyz
done
```

| 異常的那一段 | 典型原因 | 下一步 | 對應章節 |
|---|---|---|---|
| DNS 大（剛好 5 秒、10 秒） | 第一台 nameserver 不回應、A／AAAA 競態、search 展開 | `getent` 對照 `dig`；tcpdump port 53 | 第 16 章 |
| TCP 交握遠大於 RTT（多出約 1 秒） | 第一個 SYN 被丟後重傳、accept queue 滿 | 目標端抓 SYN；`nstat -az TcpExtListenOverflows` | 第 10 章 |
| TLS 大 | 憑證鏈長、終結端 CPU 滿、多一個 RTT（例如 TLS 1.2） | `openssl s_client -brief`；看終結端負載 | 第 18、19 章 |
| TTFB 大 | 應用程式、上游服務、DB 慢 | 拿 `x-request-id` 查 nginx 與 Flask log；`Server-Timing` | 第 20、43 章 |
| 下載大 | 視窗或 buffer 太小、bufferbloat、沒走 CDN | `ss -tin` 看 `rtt`、`cwnd`、`*_limited`；算 BDP | 第 11、12、25 章 |

### ss -tin：在 server 端看「下載為什麼慢」

```bash
ss -tin 'sport = :443 and dst 198.51.100.88'
```

```text
（示意輸出，節錄自第 12 章）
ESTAB 0 65160 203.0.113.70:443 198.51.100.88:51544
  cubic wscale:7,7 rto:452 rtt:251.3/2.1 mss:1448 cwnd:44 ssthresh:31
  bytes_acked:18233344 delivery_rate:2.0Mbps busy:72000ms sndbuf_limited:69000ms
  retrans:0/12 notsent:0
```

| 欄位 | 意思 | 判讀 |
|---|---|---|
| `rtt:251.3/2.1` | 平滑 RTT／變異（ms） | 確認是不是長距離路徑 |
| `cwnd`、`ssthresh` | 擁塞視窗（以 MSS 計）、慢啟動門檻 | cwnd × MSS ÷ RTT ≈ 吞吐上限 |
| `mss`、`pmtu` | 這條連線的 MSS 與路徑 MTU | MSS 明顯小於 1448 代表隧道或 PMTUD（第 8 章） |
| `retrans:a/b` | 目前未確認的重傳／累計重傳 | 持續增加且 cwnd 一直被砍，才是真的壅塞 |
| `sndbuf_limited`、`rwnd_limited` | 卡在本機傳送 buffer／對方接收視窗的時間 | 前者改 server 設定；後者看接收端 |
| `delivery_rate` | 估計的送達速率 | 和使用者回報的速度對照 |

`ss -ti` 只存在於 Linux，而且只能看「本機是 sender」的那個方向；cwnd 不在封包上，只能在 sender 端讀（第 12 章）。macOS 與 Windows 沒有同等的逐連線擁塞資訊，只能從封包（Wireshark 的 `tcp.analysis.*` 與 I/O Graph）推論。

## B.5 TLS 錯誤：openssl s_client 與 x509

TLS 除錯最重要的一個參數是 `-servername`（第 3、45 章）：同一個 IP 依 SNI 選憑證，少了它就可能拿到預設憑證，看到一個由測試方法本身造成的「名稱不符」。

```bash
openssl s_client -connect api.shengsheng.example:443 -servername api.shengsheng.example </dev/null
openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example -showcerts </dev/null
openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example -brief </dev/null  # 精簡摘要
openssl s_client -connect api.shengsheng.example:443 -servername api.shengsheng.example \
        -verify_hostname api.shengsheng.example -verify_return_error </dev/null   # 名稱不符就失敗
openssl s_client -connect api.shengsheng.example:443 -alpn h2,http/1.1 </dev/null # 看協商出的 ALPN
openssl s_client -connect api.shengsheng.example:443 -tls1_2 </dev/null           # 只試 TLS 1.2（-tls1_3 同理）
openssl s_client -connect ops.shengsheng.example:443 -CAfile internal-ca.pem \
        -cert xiaoqing-laptop.pem -key xiaoqing-laptop.key </dev/null              # 私有 CA 與 mTLS（第 18 章）
openssl s_client -connect api.shengsheng.example:443 -servername api.shengsheng.example -status </dev/null  # OCSP stapling

# 只看憑證的關鍵欄位
openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
# 數伺服器送了幾張憑證（只有 1 張多半是漏了中間憑證）
openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example -showcerts </dev/null 2>/dev/null \
  | grep -c 'BEGIN CERTIFICATE'
# 逐一檢查每個副本（第 45 章）
for ip in 10.20.2.11 10.20.2.12 10.20.2.13; do
  printf '%s ' "$ip"
  openssl s_client -connect "$ip:443" -servername rt.shengsheng.example </dev/null 2>/dev/null \
    | openssl x509 -noout -enddate
done
# 檔案形式的憑證
openssl x509 -in cert.pem -noout -text                  # 全部欄位
openssl x509 -in cert.pem -noout -checkend 2592000      # 30 天內到期就回傳非 0（適合監控腳本）
openssl x509 -in cert.pem -noout -fingerprint -sha256
openssl verify -CAfile root.pem -untrusted intermediate.pem leaf.pem   # 離線驗證一條鏈
```

| 參數 | 作用 |
|---|---|
| `-connect host:port` | 要連的位址；給 IP 時務必加 `-servername` |
| `-servername` | 設定 SNI |
| `-showcerts` | 印出伺服器送來的每一張憑證 |
| `-brief` | 只印協定版本、cipher、對方憑證摘要與驗證結果 |
| `-verify_hostname` | 檢查名稱（預設**不檢查**，名稱不符也可能顯示 `0 (ok)`） |
| `-verify_return_error` | 驗證失敗就中止交握，讓腳本拿到非 0 結束碼 |
| `-alpn`、`-tls1_2`、`-tls1_3` | 測 ALPN 與特定版本 |
| `-CAfile`、`-cert`、`-key` | 指定信任錨；提供 client 憑證做 mTLS |
| `< /dev/null` | 交握完立刻結束，不等鍵盤輸入 |

**輸出怎麼讀**：`depth=0` 是 leaf、`depth=1` 是中繼 CA、`depth=2` 是根；`Certificate chain` 區塊裡 `s:` 是 subject、`i:` 是 issuer，每一張的 issuer 應該等於下一張的 subject。最後看 `Verify return code`：

| Verify return code | 意思 | 常見原因與第一個檢查 | 對應章節 |
|---|---|---|---|
| `0 (ok)` | 鏈驗證成功（不含名稱，除非加 `-verify_hostname`） | — | 第 3 章 |
| `9 (certificate is not yet valid)` | 尚未生效 | 多半是 client 時鐘錯 | 第 45 章 |
| `10 (certificate has expired)` | 已過期 | `x509 -dates`；逐一檢查每個副本 | 第 19、45 章 |
| `18 (self-signed certificate)` | leaf 本身就是自簽 | 測試憑證被部署到 production | 第 18 章 |
| `19 (self-signed certificate in certificate chain)` | 鏈上的根不受信任 | 公司代理換了憑證，或內部 CA 沒加進信任錨 | 第 18、45 章 |
| `20 (unable to get local issuer certificate)` | 找不到簽發者 | 鏈不完整，或 client 不信任這個 CA；內部 CA 用 `-CAfile` | 第 18、19 章 |
| `21 (unable to verify the first certificate)` | 只收到 leaf、接不上鏈 | 伺服器漏送中間憑證，改用 fullchain | 第 19 章 |
| `62 (hostname mismatch)` | 名稱不符（加了 `-verify_hostname` 時） | SAN 不涵蓋這個名稱，或 SNI 沒送 | 第 19 章 |

交握直接失敗時，錯誤訊息裡會帶 TLS alert 名稱，例如 `handshake_failure`（沒有共同的版本或 cipher）、`protocol_version`、`unrecognized_name`（server 不認得 SNI）、`no_application_protocol`（ALPN 沒有交集）、`unknown_ca` 與 `bad_certificate`（多半出現在 mTLS，代表對方不接受你的 client 憑證）。完整的 alert 清單見附錄 D。

**平台差異**：macOS 內建的 `openssl` 指令實際上是 LibreSSL，部分選項（例如較新的 `-ext`）可能不支援或行為不同，需要時另外安裝 OpenSSL 3。Windows 沒有內建 openssl，可以用其他套件附帶的版本；只想看一張憑證檔的內容時，Windows 內建的 `certutil -dump cert.cer` 也能用。curl 的 `-v` 同樣會印出憑證主體、到期日與名稱比對結果，是不想記 openssl 參數時的替代品；但絕對不要把 `curl -k` 或程式裡的「關閉驗證」當成修法（第 18 章）。

## B.6 抓封包：tcpdump、tshark 與 Wireshark

其他工具都在推論，封包是直接的證據（第 3 章）。常見的工作方式是：在伺服器上用 tcpdump 加 capture filter 抓、存成 pcap、拿回自己的電腦用 Wireshark 的 display filter 細看。

```bash
sudo tcpdump -D                                              # 列出可抓的介面
sudo tcpdump -i any -nn 'host 198.51.100.23 and tcp port 443'   # Linux：any 代表所有介面
sudo tcpdump -i en0 -nn 'udp port 53'                        # macOS：用實際介面名稱
sudo tcpdump -i eth0 -nn -c 200 -w /tmp/school.pcap 'tcp port 443 and net 198.51.100.0/24'
sudo tcpdump -i eth0 -nn -s 128 -w /tmp/hdr.pcap 'port 8000' # 只抓前 128 bytes：夠看 header、少存內容
sudo tcpdump -i eth0 -nn -w /tmp/ring.pcap -C 100 -W 10 'port 443'   # 環狀檔案：每檔約 100 MB、最多 10 個
tcpdump -nn -r /tmp/school.pcap 'tcp[tcpflags] & tcp-rst != 0'       # 讀檔再過濾
sudo tcpdump -i eth0 -nn -A 'tcp port 8000 and host 10.20.3.11'      # 以文字顯示 payload（明文 HTTP）
```

| 參數 | 作用 |
|---|---|
| `-i` | 介面；Linux 的 `any` 抓所有介面，macOS 用 `en0` 等名稱 |
| `-nn` | 不轉換主機名與 port 名（否則 tcpdump 自己會送 DNS 查詢，干擾觀察） |
| `-c N` | 抓 N 個就停 |
| `-w`、`-r` | 寫入 pcap／讀取 pcap |
| `-s N` | 每個封包只抓前 N bytes（新版預設抓完整封包） |
| `-C`、`-W`、`-G` | 依大小或時間輪替檔案，長時間抓間歇性問題 |
| `-A`、`-X` | 以 ASCII／十六進位顯示內容 |
| `-v`、`-vv` | 顯示更多 header 欄位（TTL、IP ID、選項） |

tcpdump 的文字輸出格式是：時間戳、`來源IP.port > 目的IP.port`、`Flags [...]`、序號、確認號、視窗、選項、長度。旗標縮寫是 `S`＝SYN、`.`＝ACK、`P`＝PSH、`F`＝FIN、`R`＝RST，所以 `[S.]` 是 SYN+ACK、`[F.]` 是 FIN+ACK（第 3、10 章）。

### BPF 會用到的 header 位元布局

capture filter 用 **BPF** 語法，在 kernel 裡依 header 的固定位移比對。基本詞彙（`host`、`net`、`port`）不夠用時，就要直接指定 byte 位移，下面兩張圖是最常用到的位置：

```text
 IPv4 header（ip[n] 的 n 是從 IPv4 header 開頭算起的 byte 位移）
  byte 0        byte 1        byte 2-3
 ┌──────┬──────┬─────────────┬───────────────────────────┐
 │ Ver  │ IHL  │ DSCP │ ECN  │ Total Length               │
 ├──────┴──────┴──────┴──────┼───┬──┬──┬──────────────────┤
 │ Identification (4-5)       │ 0 │DF│MF│ Fragment Offset  │  byte 6-7：ip[6] & 0x40 = DF
 ├─────────────┬─────────────┼───┴──┴──┴──────────────────┤             ip[6] & 0x20 = MF
 │ TTL (8)     │ Protocol (9)│ Header Checksum (10-11)     │  ip[8] = TTL
 ├─────────────┴─────────────┴─────────────────────────────┤
 │ Source Address (12-15)    │ Destination Address (16-19) │
 └─────────────────────────────────────────────────────────┘

 TCP header 的 byte 12-13（tcp[n] 的 n 是從 TCP header 開頭算起）
  byte 12                         byte 13 = tcp[tcpflags]
 ┌───────────────┬───────────────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
 │ Data Offset   │ 保留／AE       │ CWR │ ECE │ URG │ ACK │ PSH │ RST │ SYN │ FIN │
 │ (4 bits，×4)  │ (4 bits)      │0x80 │0x40 │0x20 │0x10 │0x08 │0x04 │0x02 │0x01 │
 └───────────────┴───────────────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
  TCP header 長度 = (tcp[12] >> 4) × 4 bytes；payload 從 tcp[((tcp[12] & 0xf0) >> 2)] 開始
```

第一張圖說明三個常用位移：`ip[8]` 是 TTL，第 3 章用「RST 的 TTL 和 SYN-ACK 差很多」判斷 RST 是中間設備冒名送的；`ip[6] & 0x40` 是 DF 位元，用來找 PMTUD 相關的大封包（第 8 章）。第二張圖是 TCP 旗標所在的 byte 13，`tcp[tcpflags]` 就是它的別名，每個旗標佔一個位元，所以 `tcp[13] == 0x02` 是「只有 SYN」，`tcp[13] & 0x12 == 0x12` 是 SYN+ACK。byte 12 的高 4 位元是 header 長度（以 4 bytes 為單位），把它換算成位移就能看到 payload 的第一個 byte，例如 TLS record 的類型。

要注意一個限制：在許多 libpcap 版本中，`tcp[...]`、`udp[...]` 這類位移語法只適用於 IPv4，對 IPv6 封包不會命中。要抓 IPv6 上的特定旗標，通常改成先粗抓（`ip6 and tcp port 443`），再用 Wireshark 細看。

### tcpdump capture filter 與 Wireshark display filter 對照表

兩種語法不同、用途也不同：BPF 在抓的當下過濾（只能看 header 的固定位置，但能大幅減少檔案大小），Wireshark display filter 在抓完之後過濾（理解協定欄位，還能做重傳、RTT 等分析）。

| 想看什麼 | tcpdump capture filter（BPF） | Wireshark display filter | 對應章節 |
|---|---|---|---|
| 某個 IP 的流量 | `host 203.0.113.80` | `ip.addr == 203.0.113.80` | 第 3 章 |
| 來源或目的 | `src host 198.51.100.23`、`dst host …` | `ip.src == …`、`ip.dst == …` | 第 3 章 |
| 某個網段 | `net 10.20.0.0/16` | `ip.addr == 10.20.0.0/16` | 第 5 章 |
| IPv6 | `ip6`、`host 2001:db8:5a5a::443` | `ipv6`、`ipv6.addr == 2001:db8:5a5a::443` | 第 5 章 |
| 某個 TCP port | `tcp port 443` | `tcp.port == 443` | 第 3 章 |
| 一段 port 範圍 | `udp portrange 49152-65535` | `udp.port >= 49152 && udp.port <= 65535` | 第 36、37 章 |
| 只看 SYN（連線開始） | `tcp[tcpflags] == tcp-syn` | `tcp.flags.syn == 1 && tcp.flags.ack == 0` | 第 10 章 |
| SYN+ACK | `tcp[tcpflags] & (tcp-syn\|tcp-ack) == (tcp-syn\|tcp-ack)` | `tcp.flags.syn == 1 && tcp.flags.ack == 1` | 第 10 章 |
| SYN 或 RST | `tcp[tcpflags] & (tcp-syn\|tcp-rst) != 0` | `tcp.flags.syn == 1 \|\| tcp.flags.reset == 1` | 第 3 章 |
| FIN 或 RST（誰先關） | `tcp[tcpflags] & (tcp-fin\|tcp-rst) != 0` | `tcp.flags.fin == 1 \|\| tcp.flags.reset == 1` | 第 45 章 |
| 有資料的 TCP 封包 | `tcp and (ip[2:2] - ((ip[0]&0xf)<<2) - ((tcp[12]&0xf0)>>2)) != 0` | `tcp.len > 0` | 第 11 章 |
| 只看某一條連線 | 指定兩端 IP 與 port | `tcp.stream eq 5`（右鍵 Follow 自動產生） | 第 3 章 |
| TCP 重傳 | 無法表達 | `tcp.analysis.retransmission` | 第 11 章 |
| 所有 TCP 異常 | 無法表達 | `tcp.analysis.flags` | 第 11、12 章 |
| 接收端視窗歸零 | 無法表達 | `tcp.analysis.zero_window` | 第 11 章 |
| 封包間隔超過 1 秒 | 無法表達 | `frame.time_delta_displayed > 1` | 第 45 章 |
| 特定 TTL 的 RST | `tcp[tcpflags] & tcp-rst != 0 and ip[8] > 100` | `tcp.flags.reset == 1 && ip.ttl > 100` | 第 3 章 |
| DF 位元的大封包 | `ip[6] & 0x40 != 0 and greater 1400` | `ip.flags.df == 1 && frame.len > 1400` | 第 8 章 |
| ICMP 需要分片（PMTUD） | `icmp[icmptype] == icmp-unreach and icmp[icmpcode] == 4` | `icmp.type == 3 && icmp.code == 4` | 第 8 章 |
| ICMPv6 Packet Too Big | `icmp6 and ip6[40] == 2` | `icmpv6.type == 2` | 第 8 章 |
| TTL 用完（traceroute 回應） | `icmp[icmptype] == icmp-timxceed` | `icmp.type == 11` | 第 6 章 |
| ARP | `arp` | `arp` | 第 4 章 |
| DNS | `udp port 53 or tcp port 53` | `dns` | 第 14 章 |
| DNS 錯誤回應 | 不容易表達 | `dns.flags.rcode != 0`（3 是 NXDOMAIN） | 第 14、15 章 |
| 查某個名稱 | 不容易表達 | `dns.qry.name contains "shengsheng"` | 第 16 章 |
| 慢的 DNS 回應 | 無法表達 | `dns.time > 1` | 第 16 章 |
| TLS 交握 record | `tcp[((tcp[12] & 0xf0) >> 2)] == 0x16`（僅 IPv4、僅看段落開頭） | `tls.record.content_type == 22` | 第 18 章 |
| TLS ClientHello | 上一列再加 `and tcp[((tcp[12] & 0xf0) >> 2) + 5] == 0x01` | `tls.handshake.type == 1` | 第 18 章 |
| 某個 SNI | 無法表達 | `tls.handshake.extensions_server_name == "auth.shengsheng.example"` | 第 18、19 章 |
| TLS alert | 不容易表達 | `tls.alert_message` | 第 18 章 |
| HTTP 錯誤回應（明文或已解密） | 不容易表達 | `http.response.code >= 500` | 第 20 章 |
| HTTP/2 frame（需解密） | 無法表達 | `http2`、`http2.type == 1`（HEADERS） | 第 22 章 |
| QUIC／HTTP/3 | `udp port 443` | `quic` | 第 13 章 |
| WebSocket（明文 ws 或已解密） | `tcp port 8001` | `websocket` | 第 32 章 |
| STUN／TURN | `udp port 3478 or tcp port 3478` | `stun` | 第 36 章 |
| DTLS（WebRTC 金鑰交換） | `udp port 40000` | `dtls` | 第 36 章 |
| RTP／RTCP | `udp port 40000` | `rtp`、`rtcp`、`rtp.ssrc == 0x5eed0034`、`rtp.p_type == 111` | 第 34 章 |
| SRT ingest | `udp port 9000 and host 203.0.113.25` | `udp.port == 9000`（SRT 解析依 Wireshark 版本而定） | 第 38 章 |
| 排除自己的 SSH | `not port 22` | `!(tcp.port == 22)` | — |

讀表時注意三件事。第一，BPF 的 `|` 在 shell 裡要放在引號內（表中為了 Markdown 表格寫成 `\|`，實際輸入時不需要反斜線）。第二，Wireshark 的 `rtp` 不會自動套在任意 UDP port 上：WebRTC 的媒體與 STUN、DTLS 多工在同一個 port，需要用「Decode As」或啟用 RTP 的 heuristic 解析，而且 SRTP 的 payload 是加密的，只看得到 RTP header（第 34、36 章）。第三，HTTPS 與 HTTP/2 的內容需要解密才看得到：在**自己的電腦**上設定 `SSLKEYLOGFILE` 讓瀏覽器或 curl 輸出金鑰，再在 Wireshark 的 TLS 協定設定指定這個檔案；這個檔案等於連線的鑰匙，只能用在自己的測試流量，用完即刪（第 3、18 章）。

### tshark 與 Wireshark 的常用功能

```bash
tshark -r /tmp/school.pcap -Y 'tcp.analysis.retransmission' | head          # 套 display filter
tshark -r /tmp/school.pcap -Y 'dns' -T fields -e frame.time_relative -e dns.qry.name -e dns.flags.rcode
tshark -r /tmp/school.pcap -q -z conv,tcp                                    # 等同 Statistics → Conversations
tshark -r /tmp/class-8812.pcap -q -z rtp,streams                             # 列出 RTP 串流與遺失
```

| Wireshark 功能 | 位置 | 用途 |
|---|---|---|
| Follow TCP／TLS／HTTP Stream | 封包右鍵 → Follow | 把一條連線的對話串起來看 |
| Conversations | Statistics → Conversations | 找流量最大或最久的連線 |
| Expert Information | Analyze → Expert Information | 一次列出重傳、zero window、RST 等異常 |
| I/O Graphs | Statistics → I/O Graphs | 看吞吐與重傳隨時間的變化 |
| TCP Stream Graphs | Statistics → TCP Stream Graphs | 看序號、吞吐、RTT 隨時間變化（第 11、12 章） |
| RTP Streams／Stream Analysis | Telephony → RTP | 每個 SSRC 的遺失、jitter、序號跳號（第 34 章） |
| 時間顯示格式 | View → Time Display Format | 改成「與上一個顯示封包的間隔」找停頓 |

### 平台差異與容器裡的抓包

| 平台 | 抓封包 | 注意事項 |
|---|---|---|
| Linux | `tcpdump`（需要 root 或 `CAP_NET_RAW`）；`-i any` 抓所有介面 | production 主機通常需要申請；用 `-s` 與過濾條件限制內容 |
| macOS | 內建 `tcpdump`（需要 sudo）；Wireshark | 介面名稱用 `tcpdump -D` 查（`en0`、`lo0`、`utun*` 是 VPN） |
| Windows | Wireshark（搭配 Npcap）；較新的 Windows 10／11 內建 `pktmon` | pktmon 的輸出可轉成 pcapng 後用 Wireshark 開，指令細節依 Windows 版本而定 |
| Kubernetes 節點 | 在節點上 `tcpdump -i any host <Pod IP>` | 封包在 overlay 中可能被封裝（VXLAN 走 UDP 4789，第 44 章） |
| 容器的 network namespace | `sudo nsenter -t <容器 PID> -n tcpdump -i eth0 -nn` | 容器映像不必內含 tcpdump；Kubernetes 可改用 B.10 的 `kubectl debug` |

## B.7 看連線狀態：ss、netstat、lsof

nc 是從外面敲門，ss 是在主機內部看門牌（第 3 章）：誰在 listen、有哪些連線、各在什麼狀態、屬於哪個程式。

```bash
ss -tlnp                                        # TCP listener 與所屬程式（看別人的程式要 root）
ss -ulnp                                        # UDP listener
ss -s                                           # 總覽：各狀態的數量
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c   # 各狀態的連線數
ss -tan state close-wait | wc -l                # CLOSE_WAIT 數量（洩漏的指標，第 10 章）
ss -tanp state close-wait '( sport = :8000 )'   # 哪個程式的哪個 port 在洩漏
ss -tn state established '( dport = :5432 )' | wc -l   # 到 PostgreSQL 的連線數
ss -tn state time-wait '( sport = :8001 )' | wc -l     # 誰主動關閉，TIME_WAIT 就在誰那邊
ss -tno                                         # 加上計時器（keepalive、重傳、TIME_WAIT 剩餘時間）
ss -ltn 'sport = :8000'                         # 單看一個 listener 的 accept queue
nstat -az TcpExtListenOverflows TcpExtListenDrops   # accept queue 溢出的累計次數
ss -xlp                                         # Unix domain socket（nginx 經 Unix socket 接 uvicorn，第 33 章）
```

| 欄位或狀態 | 意思 | 異常時代表什麼 | 對應章節 |
|---|---|---|---|
| LISTEN 的 `Recv-Q`／`Send-Q` | 目前在 accept queue 排隊的連線數／backlog 上限 | Recv-Q 接近或超過 Send-Q：應用程式來不及 accept | 第 10、40 章 |
| ESTAB 的 `Recv-Q` | 已到達、程式還沒讀走的 bytes | 持續很大：程式讀太慢 | 第 11 章 |
| ESTAB 的 `Send-Q` | 已送出、對方還沒確認的 bytes | 持續很大：對方或網路吞吐不夠 | 第 11、12 章 |
| `0.0.0.0:443`、`[::]:22` | 所有 IPv4／IPv6 介面 | 資料庫出現在這裡要確認防火牆 | 第 3 章 |
| `127.0.0.1:8000` | 只接受本機連線 | 從其他主機連會被拒（第 45 章案例三） | 第 41、45 章 |
| SYN-SENT | 送了 SYN，還在等 | 對方不可達或被丟包 | 第 10 章 |
| SYN-RECV | 收到 SYN、回了 SYN-ACK，等最後的 ACK | 大量出現：SYN flood 或回程不通 | 第 10 章 |
| TIME-WAIT | 主動關閉方的等待期（約 2×MSL） | 短連線太多；考慮連線重用 | 第 10 章 |
| CLOSE-WAIT | 對方關了，本機程式還沒 close | 幾乎都是程式漏關 socket 或連線池沒歸還 | 第 10 章 |
| FIN-WAIT-2 | 本機關了，等對方的 FIN | 對方程式沒有 close | 第 10 章 |

ss 的輸出與過濾關鍵字用連字號（`TIME-WAIT`、`close-wait`），本書正文提到狀態時用底線寫法（TIME_WAIT、CLOSE_WAIT），兩者指的是同一件事。

### lsof 與 netstat

```bash
lsof -nP -iTCP -sTCP:LISTEN                 # 所有 TCP listener（macOS 最常用）
lsof -nP -i :8000                           # 誰佔了 8000 port（Address already in use 時）
lsof -nP -iTCP -sTCP:CLOSE_WAIT             # CLOSE_WAIT 的連線與所屬程式
lsof -p 1290 | wc -l                        # 某個程式開了多少 fd（Too many open files）
netstat -an -p tcp | grep LISTEN            # macOS：listener
netstat -s -p tcp | grep -iE 'retrans|overflow'   # macOS：TCP 統計
netstat -tlnp                               # Linux 舊工具（net-tools，未必安裝）
```

```powershell
netstat -ano | findstr :443                 # Windows：-o 顯示 PID
netstat -b                                  # Windows：顯示程式名稱（需要系統管理員）
Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
Get-NetTCPConnection -State CloseWait | Group-Object OwningProcess
Get-Process -Id 4121
```

| 想看什麼 | Linux | macOS | Windows |
|---|---|---|---|
| listener 與程式 | `ss -tlnp` | `lsof -nP -iTCP -sTCP:LISTEN` | `Get-NetTCPConnection -State Listen`、`netstat -ano` |
| 各狀態數量 | `ss -s`、`ss -tan` | `netstat -an -p tcp` | `Get-NetTCPConnection \| Group-Object State` |
| 某 port 被誰佔用 | `ss -ltnp 'sport = :8000'` | `lsof -nP -i :8000` | `netstat -ano \| findstr :8000` |
| 程式的 fd 數 | `ls /proc/<PID>/fd \| wc -l`、`lsof -p` | `lsof -p` | 工作管理員的「控制代碼」欄 |
| 逐連線 RTT、cwnd | `ss -tin` | 無同等工具 | 無同等工具 |
| accept queue 溢出 | `nstat -az TcpExtListenOverflows` | `netstat -s -p tcp` | `netstat -s` |

## B.8 HTTP 除錯：curl、DevTools 與 HAR

### curl

```bash
curl -v https://api.shengsheng.example/v1/health                 # 看 DNS、TCP、TLS、請求與回應
curl -sS -i https://api.shengsheng.example/v1/courses            # 印出回應 header 與 body
curl -sSI https://www.shengsheng.example/                        # HEAD：只拿 header（HEAD 與 GET 行為可能不同）
curl -sS -D - -o /dev/null https://www.shengsheng.example/       # GET 但只印 header
curl -v --resolve api.shengsheng.example:443:203.0.113.80 https://api.shengsheng.example/readyz  # 指定連到哪台
curl -v --connect-to api.shengsheng.example:443:10.20.3.11:443 https://api.shengsheng.example/readyz  # 連到另一組 host:port
curl -4 …／curl -6 …                                             # 強制 IPv4／IPv6
curl --http1.1 …／curl --http2 …                                 # 指定 HTTP 版本
curl --http3 -sv -o /dev/null https://www.shengsheng.example/    # 先試 HTTP/3，失敗退回 TCP
curl --http3-only -sv -o /dev/null https://www.shengsheng.example/   # 只用 HTTP/3（第 13 章）
curl -V | grep -i http3                                          # 這份 curl 有沒有編進 HTTP/3
curl --connect-timeout 3 -m 10 …                                 # 連線階段 3 秒、整個請求 10 秒
curl -sSL -o /dev/null -w '%{num_redirects} %{url_effective}\n' http://shengsheng.example/   # 跟隨重導向
curl --trace-ascii - --trace-time -o /dev/null https://api.shengsheng.example/readyz         # 更細的位元組級紀錄
curl -x http://10.40.0.8:3128 …／curl --noproxy '*' …            # 經過或繞過 proxy（環境變數 HTTPS_PROXY 也會生效）
curl --cacert internal-ca.pem --cert client.pem --key client.key https://ops.shengsheng.example/   # 私有 CA 與 mTLS
curl -s -r 0-1023 -o /dev/null -w '%{http_code}\n' https://www.shengsheng.example/recordings/lesson-0815.mp4  # Range，預期 206
curl -si -X OPTIONS https://api.shengsheng.example/v1/bookings \
  -H 'Origin: https://www.shengsheng.example' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization, content-type'   # 模擬 CORS preflight（第 23、45 章）
curl -si https://www.shengsheng.example/ | grep -iE '^(cache-control|age|vary|x-cache)'   # 快取（第 21、25 章）
```

| 參數 | 作用 | 陷阱 |
|---|---|---|
| `-v` | `*` 是 curl 的說明、`>` 是送出、`<` 是收到 | 卡在 `Trying` 是 TCP；`Could not resolve host` 是 DNS |
| `--resolve host:port:addr` | 只換連線的目的 IP，URL、SNI、Host、憑證比對都不變 | 用 IP 當 URL 再補 `-H "Host:"` 會讓 SNI 變成 IP |
| `--connect-to` | 把 host:port 對到另一組 host:port | 適合 port 也要換的情況 |
| `-w` | 依格式印出量測變數 | 時間是累計值，相鄰相減 |
| `--http2`、`--http3`、`--http3-only` | 指定或嘗試 HTTP 版本 | HTTP/3 要看編譯選項；`--http3` 失敗會靜靜退回 TCP |
| `--connect-timeout`、`-m` | 連線階段逾時、整體逾時 | 只設 `-m` 時，大檔下載可能被誤判為失敗 |
| `-k` | 跳過憑證驗證 | 只能用來確認「除了憑證其他都正常」，絕不能寫進程式或腳本 |
| `-H 'Upgrade: websocket'` 搭配 `--http1.1` | 測 WebSocket 握手（B.9） | 沒加 `--http1.1` 可能協商成 HTTP/2，而 HTTP/2 不允許 `Upgrade` |

| `-w` 變數 | 量的是什麼 |
|---|---|
| `time_namelookup`、`time_connect`、`time_appconnect` | DNS、TCP 交握、TLS 交握完成（累計） |
| `time_pretransfer`、`time_starttransfer`、`time_total` | 即將傳輸、收到第一個 byte、全部完成（累計） |
| `time_redirect`、`num_redirects`、`url_effective` | 重導向花的時間、次數、最後的 URL（搭配 `-L`） |
| `http_code`、`http_version` | 狀態碼、實際使用的 HTTP 版本（`1.1`、`2`、`3`） |
| `remote_ip`、`remote_port`、`local_port` | 實際連到哪裡、用哪個本機 port |
| `num_connects` | 這次新建了幾條連線（0 代表重用） |
| `size_download`、`speed_download` | 下載大小與平均速度（bytes／秒） |
| `ssl_verify_result` | 憑證驗證結果（0 為成功） |
| `%{json}` | 一次輸出所有變數（新版 curl） |

**平台差異**：Linux 發行版的 curl 版本差異很大，`--http3` 需要以支援 HTTP/3 的方式編譯，先用 `curl -V` 看 `Features` 是否列出 HTTP3。macOS 內建的 curl 不一定支援 HTTP/3，需要時另外安裝。Windows 10 以後內建 `curl.exe`；在 Windows PowerShell 5.1 中 `curl` 是 `Invoke-WebRequest` 的別名，要明確輸入 `curl.exe`，丟棄 body 用 `-o NUL`，而在 cmd 的批次檔裡 `%{…}` 的 `%` 要寫成 `%%`。

### 瀏覽器 DevTools 的 Network 面板

| 設定或功能 | 用途 |
|---|---|
| Preserve log | 頁面跳轉後紀錄不清空（登入、OAuth 重導向必開，第 28、29 章） |
| Disable cache | DevTools 開著時停用 HTTP 快取，避免看到快取結果 |
| 欄位：Protocol、Remote Address | 看 `h2`／`h3`，以及實際連到哪個 IP（有沒有走 CDN） |
| Size 欄的 `(memory cache)`、`(disk cache)`、`(ServiceWorker)` | 這個回應根本沒上網路 |
| Timing 分頁 | Queueing、Stalled、DNS Lookup、Initial connection、SSL、Waiting for server response、Content Download；`Server-Timing` 也顯示在這裡 |
| 篩選框 | `status-code:500`、`domain:api.shengsheng.example`、`method:OPTIONS`、`larger-than:1M`、`-domain:…`（排除） |
| WS／Fetch/XHR 篩選 | 只看 WebSocket 或 API 請求 |
| Cookies 分頁 | 被擋下的 cookie 與原因（SameSite、Secure、Domain，第 21、23 章） |
| Copy as cURL | 把瀏覽器的請求連同 header 變成一行 curl 指令重現（內含 cookie，分享前要刪） |
| Throttling | 模擬慢網路或離線 |
| Initiator 欄 | 是哪段程式或哪個資源觸發了這個請求 |

狀態欄的瀏覽器錯誤碼直接指出失敗的層：`ERR_NAME_NOT_RESOLVED` 是 DNS（B.2），`ERR_CONNECTION_REFUSED` 與 `ERR_CONNECTION_TIMED_OUT` 是 TCP（B.3），`ERR_CONNECTION_RESET` 要抓封包看誰送了 RST（B.6），`ERR_CERT_*` 是憑證（B.5），`(blocked:cors)` 或 Console 的 CORS 訊息則要先看 preflight 本身的 status：500 或 502 沒帶 CORS header，也會被報成 CORS 錯誤（第 45 章）。Chrome 另有兩個內部頁：`chrome://net-export` 錄下 netlog（QUIC 交握失敗、退回 TCP 的細節，第 13 章），`chrome://net-internals` 可以清 host cache 與 socket pool。Firefox 的對應工具是 Network Monitor 與 `about:networking`，Safari 是 Web Inspector 的 Network 分頁，欄位名稱各有差異。

### HAR

HAR（HTTP Archive）把 Network 面板的紀錄匯出成 JSON。每個請求是 `log.entries` 裡的一筆，時間分解在 `timings`：

| HAR `timings` 欄位 | DevTools Timing | `curl -w` 對應（相鄰相減） | 備註 |
|---|---|---|---|
| `blocked` | Queueing＋Stalled | 無（curl 不排隊） | 等可用連線、優先順序 |
| `dns` | DNS Lookup | `time_namelookup` | `-1` 代表沒有發生（重用連線） |
| `connect` | Initial connection | `time_appconnect − time_namelookup` | **已包含** `ssl` 的時間 |
| `ssl` | SSL | `time_appconnect − time_connect` | TCP 本身 = `connect − ssl` |
| `send` | Request sent | 無單獨的變數（併在下一列裡） | 通常接近 0 |
| `wait` | Waiting for server response（TTFB） | `time_starttransfer − time_pretransfer` | 伺服器處理＋一個 RTT（curl 這段也含送出請求） |
| `receive` | Content Download | `time_total − time_starttransfer` | 下載 body |

> [!warning] 常見誤解
> 「HAR 只是除錯紀錄，貼到工單裡沒關係。」HAR 可能含有 `Cookie`、`Set-Cookie`、`Authorization` 裡的 session 與 bearer token、URL 裡的一次性 ticket，以及表單內容。依 Rita 給聲聲 Live 的規定：收 HAR 只走有權限控管的管道，分析前先去敏感化，用完刪除，並請使用者匯出後登出讓 session 失效（第 3 章）。B.12 的程式示範去敏感化的做法。

> [!note] 2026 現況
> 截至 2026 年 10 月，新版 Chrome DevTools 的匯出選單會區分「不含敏感資料」與「含敏感資料」兩種 HAR，預設的版本會略過 cookie 等欄位；Firefox 與 Safari 的行為各自不同，且可能隨版本調整。無論工具預設為何，收到 HAR 時都要自己檢查一次。

## B.9 WebSocket／WebRTC 除錯（含 SRT 直播）

### WebSocket

```bash
# 不用瀏覽器測握手：看到 101 與這個固定的 Accept，代表整條路徑的升級都通了（第 32 章）
curl -i -N --http1.1 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Origin: https://www.shengsheng.example" \
  "https://rt.shengsheng.example/ws/healthz"
# 預期：HTTP/1.1 101 Switching Protocols、Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
ss -tn state established '( sport = :8001 )' | wc -l     # 即時服務節點上的 WebSocket 連線數
grep -n -A8 'location /ws/' /etc/nginx/conf.d/rt.conf | grep -E 'proxy_read_timeout|Upgrade|Connection'
sudo tcpdump -ni eth0 'host 10.20.1.41 and port 8001 and (tcp[tcpflags] & (tcp-fin|tcp-rst) != 0)'   # 誰先關
```

握手的回應碼說明了是哪一層擋下：400、404 或 200 代表中間某一層沒有轉送 `Upgrade`；403 多半是 `Origin` 不在允許清單；401 是 ticket 無效；426 是版本不對。瀏覽器的 WebSocket API 不會把這些狀態碼交給 JavaScript，前端只會看到 `error` 接著 1006，所以要去 DevTools 的 Network 面板篩選 WS：點開握手請求看狀態碼與 header，Messages 分頁看每一則收送的訊息、方向與大小（第 32 章）。

| close code | 誰送的 | 時間特徵 | 典型原因 | 對應章節 |
|---|---|---|---|---|
| 1000 | 任一方 | 正常結束 | — | 第 32 章 |
| 1001／1012 | server | 集中在部署時間 | 例行部署；前端要退避加抖動，避免重連驚群 | 第 31、33 章 |
| 1006 | 沒人送（連線被切斷） | 閒置固定秒數後；換網路時 | 某層 idle timeout 短於心跳、NAT 清表、握手被拒 | 第 32、45 章 |
| 1008 | server | 連線後立刻 | 政策違反（Origin、權限） | 第 32 章 |
| 1009 | 收訊方 | 送出大訊息後立刻斷 | 超過訊息上限（聊天 64 KiB、白板 1 MiB） | 第 32 章 |
| 4001 | server（聲聲 Live 自訂） | 連線滿 15 分鐘 | 連線授權到期，前端換票重連 | 第 32 章 |
| 4008 | server（聲聲 Live 自訂） | 尖峰、送端很快 | client 太慢，送出佇列超過上限 | 第 33 章 |

1006 要再看斷線時間點：和「最後一則訊息」的間隔固定在 60 秒，幾乎就是 nginx `proxy_read_timeout` 預設值碰上停用的心跳（第 45 章案例七）。聲聲 Live 的正確設定是 server 每 25 秒 ping、20 秒沒 pong 即關閉，`/ws/` 的 `proxy_read_timeout` 75 秒，LB idle timeout 120 秒。

### chrome://webrtc-internals 與 getStats

`chrome://webrtc-internals` 列出這個瀏覽器所有的 RTCPeerConnection，每一個都有建立時的設定、API 呼叫時間軸與 getStats 的即時圖表；**要在通話開始之前就打開**，早期事件才會被記錄。最上方的按鈕可以下載整頁 dump（JSON），請使用者重現問題後寄回，是遠端除錯最有用的一招（第 39 章）。

| 先看的區塊 | 看什麼 | 判讀 | 對應章節 |
|---|---|---|---|
| 設定 | `iceServers` 有沒有 TURN（含 `turns:…:443`）、`iceTransportPolicy` | 企業網路沒有 TLS 443 的 TURN 幾乎一定連不上 | 第 36、37 章 |
| API trace | `createOffer` → `setLocalDescription` → `setRemoteDescription` → ICE 狀態變化 | 沒有 `setRemoteDescription` 是 signaling 問題；停在 `checking` 再 `failed` 是連線路徑；都 connected 仍黑畫面是媒體 | 第 35、36、39 章 |
| `icecandidateerror` | `url`、`errorCode` | 701 是連不上那台 STUN／TURN server；401 多半是 TURN 帳密錯誤或過期 | 第 36、39 章 |
| candidate-pair（選中的那組） | `state`、`currentRoundTripTime`、`availableOutgoingBitrate`、`bytesSent`、`bytesReceived` | 兩個方向的 bytes 都在增加，網路層就可以排除（第 45 章案例八） | 第 36、45 章 |
| local／remote candidate | `candidateType`（host、srflx、prflx、relay）、`relayProtocol`（udp、tcp、tls） | relay 且 `tls`：走 TCP 中繼，RTT 高、對丟包敏感 | 第 36、39 章 |
| transport | `dtlsState`、ICE 狀態 | ICE connected 但 DTLS failed：fingerprint 被改或 setup 角色衝突 | 第 35、36 章 |
| outbound-rtp | `packetsSent`、`framesPerSecond`、`frameWidth`、`qualityLimitationReason`、`rid` | `cpu` 或 `bandwidth` 指出送端被什麼限制；`rid` 看 simulcast 各層 | 第 37、39 章 |
| inbound-rtp | `packetsReceived`、`packetsLost`、`jitter`、`framesDecoded`、`freezeCount`、`concealedSamples` | 封包有、播放沒有：往 autoplay 與播放元件找 | 第 34、39 章 |
| remote-inbound-rtp | `roundTripTime`、`fractionLost` | 對方回報的收訊品質 | 第 34 章 |

**平台差異**：Chromium 系瀏覽器（Chrome、Edge）用 `chrome://webrtc-internals`（Edge 也接受 `edge://` 開頭的同名頁）；Firefox 的對應頁是 `about:webrtc`；Safari 要用 Web Inspector 與開發者選單中的 WebRTC 記錄選項，可用的資訊比 Chrome 少。版面與按鈕名稱會隨版本調整，以 W3C webrtc-stats 定義的標準欄位為準，不要依賴舊文章裡以 `goog` 開頭的非標準欄位（第 39 章）。命令列這一側，`turn.shengsheng.example` 的 UDP 3478 是否可達無法用 `nc -u` 證明，要看瀏覽器的 `icecandidateerror`，或在 TURN 主機上用 `tcpdump -nn 'udp port 3478'` 確認請求有沒有抵達。

### srt-live-transmit：SRT 推流與 ingest 測試

```bash
# 測試用 listener：latency 單位是「毫秒」，每 1000 個封包印一次統計（第 38 章）
srt-live-transmit "srt://:9000?mode=listener&latency=500" udp://127.0.0.1:5000 -s:1000
# 測試用 caller：把本機 UDP 上的 TS 串流推到 ingest
srt-live-transmit udp://:5000 \
  "srt://live.shengsheng.example:9000?mode=caller&latency=500&passphrase=${SRT_PASS}&streamid=#!::r=live/talk-1017,m=publish" -s:1000
# 對照：ffmpeg 的 srt URL 參數 latency 單位是「微秒」，500000 = 500 ms
ffmpeg -re -i talk.mp4 -c copy -f mpegts \
  "srt://live.shengsheng.example:9000?mode=caller&latency=500000&pkt_size=1316&passphrase=${SRT_PASS}&streamid=#!::r=live/talk-1017,m=publish"
sudo tcpdump -ni any -c 20 'udp port 9000 and host 203.0.113.25'   # ingest 端：封包有沒有抵達
```

| URL 參數 | 意思 | 注意事項 |
|---|---|---|
| `mode` | `caller`、`listener`、`rendezvous` | 講者端通常是 caller、ingest 是 listener |
| `latency` | 接收端的重傳緩衝時間 | libsrt 與 srt-live-transmit 是**毫秒**（libsrt 預設 120 ms）；ffmpeg 是**微秒** |
| `passphrase` | 加密金鑰的密語（10–80 字元） | 從環境變數讀取，避免留在 shell history |
| `streamid` | 識別串流與用途 | 聲聲 Live 用 `#!::r=live/talk-1017,m=publish` |
| `pkt_size`（ffmpeg） | 每個 SRT 封包的 payload | 1316 = 7 × 188 bytes 的 TS 封包 |

| 統計欄位 | 意思 | 判讀 |
|---|---|---|
| `msRTT` | SRT 量到的 RTT | latency 至少要 RTT 的 3–4 倍 |
| `pktRcvLoss` | 收方偵測到的遺失 | 高但 `pktRcvDrop` 為 0：網路不好，SRT 補得回來 |
| `pktRetrans` | 送方的重傳數 | 和遺失數量相近是正常的 |
| `pktRcvDrop` | 太晚到而被丟棄的封包 | **最重要**：觀眾真的會看到破圖；持續增加就加大 latency 或降低 bitrate |
| `mbpsRecvRate` | 接收速率 | 對照推流 bitrate |
| `msRcvBuf` | 收方 buffer 的時間長度 | 約等於 latency 是正常狀態 |

srt-live-transmit 是 SRT 專案附帶的測試工具，Linux 與 macOS 多半可以從套件管理工具或原始碼編譯取得，Windows 的取得方式依發行管道而定；統計欄位名稱依版本略有不同，以 `srt-live-transmit -h` 為準。SRT 是 UDP，`nc -u` 無法證明 ingest 可用，用一次真正的 caller 推流加上統計最可靠。

## B.10 雲端與容器：kubectl 與節點層

第 44 章的原則是**由內往外查**：先看失敗是否集中在某些 Pod 或節點，再依序排除 Pod 內的路由與 DNS、NetworkPolicy、Service 與 endpoint、節點的 kube-proxy 與 conntrack，最後才是雲端的路由表、security group、NACL 與 NAT gateway。

```bash
kubectl get pod -n live -o wide                              # Pod IP 與所在節點：失敗集中在哪些節點？
kubectl get svc -n live -o wide                              # Service 的 ClusterIP、port、selector
kubectl get endpointslice -n live -l kubernetes.io/service-name=reco   # Service 後面有哪些 ready 的 Pod
kubectl describe svc reco -n live                            # selector、port、targetPort 是否對得上
kubectl exec -n live api-7d9f -- cat /etc/resolv.conf        # nameserver 10.96.0.10、search、ndots（第 16 章）
kubectl exec -n live api-7d9f -- getent hosts pay.example.net   # 用程式視角解析
kubectl exec -n live api-7d9f -- ip route                    # Pod 的路由；ip link show eth0 看 MTU
kubectl get networkpolicy -n live -o yaml                    # 有沒有 Egress 的 default-deny、是否放行 DNS
kubectl get pod -n kube-system -l k8s-app=kube-dns           # CoreDNS 是否正常
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
kubectl get events -n live --sort-by=.lastTimestamp          # readiness 失敗、被移出 endpoint
kubectl port-forward -n live svc/reco 50051:50051            # 從自己的電腦直連 Service，繞過 ingress
kubectl debug -n live -it api-7d9f --image=<含網路工具的除錯映像> --target=api   # ephemeral container，共用 Pod 的網路
# 在節點上
iptables-save -t nat | grep KUBE-SVC | head                  # kube-proxy 規則（nftables 模式用 nft list ruleset）
sudo conntrack -S                                            # insert_failed、drop 計數（第 7、16 章）
sudo tcpdump -i any -nn host 10.244.5.30                     # 在節點上抓某個 Pod IP
```

| 指令 | 回答的問題 | 看到什麼代表有問題 | 對應章節 |
|---|---|---|---|
| `get pod -o wide` | 失敗是否集中在某些節點 | 失敗的 Pod 都在新節點群組 | 第 44 章 |
| `get endpointslice` | Service 後面有沒有 ready 的 endpoint | endpoint 為空或都是 not ready | 第 44 章 |
| `exec … cat /etc/resolv.conf` | Pod 用哪個 DNS、`ndots` 多少 | `ndots:5` 加上大量外部名稱：查詢被 search 展開 | 第 16 章 |
| `exec … getent hosts` | 程式能不能解析 | 用名稱失敗、用 IP 成功：DNS 或 egress 政策擋了 53 | 第 16、44 章 |
| `get networkpolicy -o yaml` | 有沒有預設拒絕 | `policyTypes` 含 Egress 卻沒放行 DNS | 第 44 章 |
| `exec … ip link` | Pod 的 MTU | 照抄其他環境的 MTU，大封包卡住 | 第 8、44 章 |
| `conntrack -S` | conntrack 表是否出錯 | `insert_failed` 持續增加：DNS 5 秒延遲的常見原因 | 第 16 章 |

驗證 Service 時要測它宣告的 port（例如 `nc -vz 10.96.40.12 50051`），不要 ping ClusterIP：ClusterIP 只是規則裡的虛擬位址，iptables 模式下 ping 通常沒有回應，IPVS 模式下 ping 有回應也只代表節點核心收到了（第 44 章）。`kubectl exec` 需要容器內有對應的工具，精簡映像裡常常沒有 `getent` 以外的網路工具，這時用 `kubectl debug` 掛上 ephemeral container 會比在 production 映像裡安裝套件安全。

Docker 單機上的對應做法：

```bash
docker network ls; docker network inspect bridge       # 網段（與 VPN／VPC 重疊是常見事故，第 6 章）
docker exec -it api sh -c 'cat /etc/resolv.conf; ip route'
docker run --rm -it --network container:api <含網路工具的除錯映像> ss -tlnp   # 共用目標容器的網路
sudo nsenter -t "$(docker inspect -f '{{.State.Pid}}' api)" -n ss -tlnp      # 在主機上進入容器的 network namespace
```

雲端層的證據不在主機上，要從雲端的主控台或 CLI 看。下表列出每一層要看的東西；各家雲端的名稱與指令不同，但概念相同：

| 雲端層 | 要看什麼 | 典型錯誤 | 對應章節 |
|---|---|---|---|
| route table | 子網關聯哪張表、default route 指向哪個 NAT gateway、到辦公室與 staging 的路由 | 新子網關聯了錯的表 | 第 6、44 章 |
| security group | 入站規則的來源與 port（stateful，回程自動放行） | 新節點沒掛上 SG；只開 TCP 沒開 UDP 4789 | 第 7、44 章 |
| network ACL | 入站與出站規則（stateless，回程要另外開 1024–65535） | 回程 ephemeral port 被擋，SYN 進得來、SYN-ACK 出不去 | 第 7、44 章 |
| NAT gateway／Elastic IP | 對外 IP 是否已登記給金流與合作夥伴 | 新 NAT 的 IP 不在對方允許清單 | 第 7、44 章 |
| VPC flow log | 每條流的五元組與 ACCEPT／REJECT | SYN 被 ACCEPT、回程被 REJECT 幾乎就是 NACL；完全沒有紀錄往 route table 找 | 第 44 章 |
| LB 與 target group | health check 狀態、idle timeout、監聽的 port 與協定 | idle timeout 與後端 keep-alive 不一致造成間歇性 502（第 45 章案例四） | 第 25、43、45 章 |

## B.11 跨平台指令對照總表

同一件事在三個平台的寫法常常不同。下表把本附錄出現過的任務放在一起，方便在別人的電腦上遠端指導對方操作：

| 任務 | Linux | macOS | Windows |
|---|---|---|---|
| 查 DNS（指定 server） | `dig @10.20.0.2 名稱` | `dig @10.20.0.2 名稱` | `Resolve-DnsName 名稱 -Server 10.20.0.2`、`nslookup 名稱 10.20.0.2` |
| 程式視角的解析 | `getent ahosts 名稱` | `dscacheutil -q host -a name 名稱` | `Resolve-DnsName 名稱` |
| 實際的 resolver 設定 | `resolvectl status`、`cat /etc/resolv.conf` | `scutil --dns` | `Get-DnsClientServerAddress` |
| 清 OS 的 DNS 快取 | `resolvectl flush-caches` | `dscacheutil -flushcache`＋重啟 mDNSResponder | `ipconfig /flushdns` |
| ping 4 次 | `ping -c 4` | `ping -c 4` | `ping -n 4` |
| 測 MTU（DF） | `ping -M do -s 1472` | `ping -D -s 1472` | `ping -f -l 1472` |
| 路徑 | `traceroute -n`、`tracepath -n`、`mtr -n` | `traceroute -n`、`mtr -n` | `tracert -d`、`pathping -n` |
| TCP port 檢查 | `nc -vz -w 3 主機 port` | `nc -vz -G 3 主機 port` | `Test-NetConnection 主機 -Port port` |
| 位址與 MTU | `ip -br addr`、`ip link` | `ifconfig` | `ipconfig /all`、`netsh interface ipv4 show subinterfaces` |
| 路由表 | `ip route` | `netstat -rn -f inet` | `route print` |
| 某目的地走哪條路由 | `ip route get IP` | `route -n get IP` | `Find-NetRoute -RemoteIPAddress IP` |
| ARP／鄰居 | `ip neigh` | `arp -an`、`ndp -an` | `arp -a`、`Get-NetNeighbor` |
| 誰在 listen | `ss -tlnp` | `lsof -nP -iTCP -sTCP:LISTEN` | `Get-NetTCPConnection -State Listen`、`netstat -ano` |
| 某 port 被誰佔用 | `ss -ltnp 'sport = :8000'` | `lsof -nP -i :8000` | `netstat -ano \| findstr :8000` |
| 各狀態連線數 | `ss -s`、`ss -tan` | `netstat -an -p tcp` | `Get-NetTCPConnection \| Group-Object State` |
| 逐連線 RTT、cwnd | `ss -tin` | 無 | 無 |
| HTTP 量測 | `curl -w` | `curl -w`（內建版本可能較舊） | `curl.exe -w`（PowerShell 中別寫成 `curl`） |
| TLS 與憑證 | `openssl s_client`、`openssl x509` | 內建為 LibreSSL，需要時裝 OpenSSL 3 | 無內建 openssl；`certutil -dump` 看憑證檔 |
| 抓封包 | `sudo tcpdump -i any` | `sudo tcpdump -i en0` | Wireshark＋Npcap、`pktmon` |
| 瀏覽器 WebRTC | `chrome://webrtc-internals` | `chrome://webrtc-internals`；Safari 用 Web Inspector | `chrome://webrtc-internals`、`edge://webrtc-internals` |

## B.12 動手做：把 HAR 去敏感化並切出時間

收到使用者的 HAR 之後，阿德要求的第一步不是打開它找問題，而是先把它變成「可以安全地貼進工單」的版本。下面這段程式只用標準函式庫：把 `Authorization`、`Cookie`、`Set-Cookie` 等 header、cookie 陣列、URL 裡的 `ticket` 與 `token` 參數，以及 request body 換成 `REDACTED`，但保留 `x-request-id` 讓後端能對照 log；接著依 HAR 1.2 的規則把 `timings` 換算成七段，指出每個請求最大的那一段。

```python
import copy
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# 一份縮小的 HAR（結構依 HAR 1.2）：學生在課表頁重現問題後匯出
HAR = {"log": {"version": "1.2", "creator": {"name": "DevTools", "version": "示意"}, "entries": [
    {"request": {"method": "GET", "url": "https://api.shengsheng.example/v1/schedule?week=41",
                 "headers": [{"name": "Authorization", "value": "Bearer eyJhbGciOiJFUzI1NiJ9.e30.sig"},
                             {"name": "Cookie", "value": "__Host-sid=A; lang=ja"}],
                 "cookies": [{"name": "__Host-sid", "value": "A"}]},
     "response": {"status": 200, "headers": [{"name": "x-request-id", "value": "7f3c9a2e"}]},
     "timings": {"blocked": 3.1, "dns": 4.0, "connect": 90.0, "ssl": 62.0,
                 "send": 0.2, "wait": 2286.0, "receive": 21.0}},
    {"request": {"method": "POST", "url": "https://api.shengsheng.example/v1/session/refresh",
                 "headers": [{"name": "Cookie", "value": "__Host-refresh=R"}],
                 "postData": {"mimeType": "application/json", "text": "{\"device\":\"web\"}"}},
     "response": {"status": 200, "headers": [{"name": "Set-Cookie", "value": "__Host-sid=B; Path=/; Secure"}]},
     "timings": {"blocked": 0.4, "dns": -1, "connect": -1, "ssl": -1,
                 "send": 0.1, "wait": 38.0, "receive": 0.6}},
    {"request": {"method": "GET", "url": "https://rt.shengsheng.example/ws/classroom/8812?ticket=tk_9f2c",
                 "headers": []},
     "response": {"status": 101, "headers": []},
     "timings": {"blocked": 1.0, "dns": 2.0, "connect": 41.0, "ssl": 25.0,
                 "send": 0.1, "wait": 35.0, "receive": 0.0}},
]}}

SECRET_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}
SECRET_PARAMS = {"ticket", "token", "access_token", "code"}


def scrub_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, "REDACTED" if k.lower() in SECRET_PARAMS else v) for k, v in parse_qsl(parts.query)]
    return urlunsplit(parts._replace(query=urlencode(query)))


def sanitize(har: dict) -> dict:
    clean = copy.deepcopy(har)          # 不改原檔：原始 HAR 之後要依規定刪除
    for e in clean["log"]["entries"]:
        for side in ("request", "response"):
            msg = e[side]
            for h in msg.get("headers", []):
                if h["name"].lower() in SECRET_HEADERS:
                    h["value"] = "REDACTED"
            msg["cookies"] = []
        e["request"]["url"] = scrub_url(e["request"]["url"])
        if "postData" in e["request"]:
            e["request"]["postData"]["text"] = "REDACTED"
    return clean


def phases(t: dict) -> dict:
    # HAR 1.2：ssl 的時間「同時」算在 connect 裡；-1 代表這一段沒有發生（例如連線重用）
    get = lambda k: max(t.get(k, -1), 0)
    return {"排隊": get("blocked"), "DNS": get("dns"), "TCP": get("connect") - get("ssl"),
            "TLS": get("ssl"), "送出": get("send"), "等待(TTFB)": get("wait"), "下載": get("receive")}


clean = sanitize(HAR)
dump = json.dumps(clean, ensure_ascii=False)
for secret in ("eyJhbGci", "__Host-sid=A", "__Host-refresh=R", "tk_9f2c", "device"):
    assert secret not in dump, secret
assert "7f3c9a2e" in dump                # x-request-id 要留著，才能去後端 log 對照

for e in clean["log"]["entries"]:
    p = phases(e["timings"])
    worst = max(p, key=p.get)
    total = sum(p.values())
    print(f"{e['request']['method']:4} {e['response']['status']} {e['request']['url']}")
    print("     " + " ".join(f"{k}={v:g}" for k, v in p.items()) + f"  合計={total:g} ms  最大段：{worst}")

first = phases(clean["log"]["entries"][0]["timings"])
assert first["TCP"] == 28.0 and max(first, key=first.get) == "等待(TTFB)"
assert phases(clean["log"]["entries"][1]["timings"])["TCP"] == 0   # 重用連線：沒有交握
print("去敏感化檢查通過：token、cookie、ticket、body 都已移除")
```

```text
GET  200 https://api.shengsheng.example/v1/schedule?week=41
     排隊=3.1 DNS=4 TCP=28 TLS=62 送出=0.2 等待(TTFB)=2286 下載=21  合計=2404.3 ms  最大段：等待(TTFB)
POST 200 https://api.shengsheng.example/v1/session/refresh
     排隊=0.4 DNS=0 TCP=0 TLS=0 送出=0.1 等待(TTFB)=38 下載=0.6  合計=39.1 ms  最大段：等待(TTFB)
GET  101 https://rt.shengsheng.example/ws/classroom/8812?ticket=REDACTED
     排隊=1 DNS=2 TCP=16 TLS=25 送出=0.1 等待(TTFB)=35 下載=0  合計=79.1 ms  最大段：等待(TTFB)
去敏感化檢查通過：token、cookie、ticket、body 都已移除
```

逐段解說。第一個請求就是第 3 章課表頁的數字：`connect` 是 90 ms、`ssl` 是 62 ms，因為 HAR 規定 `ssl` 已經包含在 `connect` 裡，TCP 交握本身是 90−62＝28 ms，和第 3 章 `curl -w` 相減得到的結果一致；2286 ms 的等待佔了九成以上，下一步是拿保留下來的 `x-request-id` 去後端 log 找慢查詢。第二個請求的 `dns`、`connect`、`ssl` 都是 −1，換算後是 0，代表它重用了既有連線，這也是為什麼同一頁裡只有第一個請求付出交握成本。第三個請求是 WebSocket 握手，狀態 101，URL 裡的一次性 ticket 已被換成 `REDACTED`。

程式最後的幾個 `assert` 是去敏感化的驗收條件：把清理後的整份 JSON 序列化成字串，確認 token、兩種 cookie、ticket 與 body 的內容都不在裡面。實務上要擴充的地方有兩個：一是把 `SECRET_HEADERS` 與 `SECRET_PARAMS` 依自家 API 補齊（例如自訂的 API key header）；二是回應的 `content.text` 也可能含個資，貼進工單前應一併移除。
