---
chapter: 5
title: VPC 從零到可上線
part: 1
---

# 第 5 章　VPC 從零到可上線：CIDR、Subnet、Route Table、IGW 與 NAT

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 VPC、subnet、route table、Internet Gateway、NAT Gateway 各自負責什麼，以及它們怎麼串成一條完整的網路路徑
> - 為一個新環境規劃不會重疊、留有成長空間的 CIDR，並算出每個 subnet 的可用位址數
> - 分辨 public、private、isolated 三種 subnet，知道它們的差異只來自 route table 與 IP 設定
> - 設計一個跨兩個 AZ、可以正式上線的三層式 VPC
> - 遇到「EC2 連不上 Internet」時，依照封包路徑從裡到外逐項排查，分別處理「從 Internet 連不進來」與「連不到外部 API」兩種情境
>
> **前置知識**：第 3 章（IP、CIDR、路由與 NAT 基礎）
> **考試比重**：SAA ★★★（Domain 1 安全、Domain 3 網路效能、Domain 4 網路成本）｜SAP ★★☆（Domain 1 網路連線策略）

## 5.1 故事：Wanderly 的資料庫被看到了

Part 0 把共同語言建立好了：Region 與 AZ（第 2 章）、IP、CIDR、路由、NAT、防火牆（第 3 章）、儲存與可靠性（第 4 章）。從這一章開始，每一章都是「AWS 把其中某個觀念做成了什麼產品」。第一個就是第 3 章那套 IP 與路由：在 AWS 上，它叫 VPC。

Wanderly 剛上線時，工程師小林用最快的方式把系統架起來：在 AWS 帳號裡開一台 EC2 跑網站，再開一台 EC2 裝 MySQL。兩台機器都放在 AWS 幫每個帳號預先建好的 **default VPC**（預設虛擬網路）裡，都拿到了 public IP，security group 也為了方便開了 `0.0.0.0/0`（任何來源）的 3306 port。

三個月後，一家資安顧問公司做外部掃描，報告第一頁就寫著：「貴公司的 MySQL 可從 Internet 直接連線。」沒有人被入侵，但所有人都嚇出一身冷汗。小林發現，問題不是 MySQL 密碼太弱，而是**整個網路架構沒有「內外之分」**：資料庫和網站站在同一個開放的空間裡。

技術主管給小林一個任務：建立一個 Wanderly 自己的 VPC，讓網站可以被 Internet 存取、應用程式可以呼叫外部的金流 API，但資料庫**在網路層就不可能**被 Internet 碰到。同時，這個網路要能撐過一個 AZ（資料中心）故障，還要為未來的測試環境、公司辦公室連線預留空間。

這一章就跟著小林，從一個空白的 VPC 開始，一步一步把網路建起來。每加一個元件，我們都會問：它解決了什麼問題？少了它會發生什麼事？

## 5.2 VPC 是什麼：你在 AWS 裡的私人網路

**VPC（Virtual Private Cloud，虛擬私有雲）** 是你在 AWS 裡擁有的一個邏輯上隔離的網路。你可以把它想成「AWS 幫你蓋好的一棟大樓外殼」：大樓裡要怎麼隔房間（subnet）、走廊怎麼接（route table）、大門開在哪裡（Internet Gateway），都由你決定。別的 AWS 客戶在同一批實體機器上也有自己的大樓，但彼此的網路完全看不到對方。

關於 VPC，有三個一定要記住的事實：

1. **VPC 屬於一個 Region。** 一個 VPC 建在 `ap-northeast-1`（東京）就只存在於東京，它可以跨越這個 Region 裡的所有 AZ，但不能跨 Region。要跨 Region 互通，需要第 7 章的 peering 或 Transit Gateway。
2. **VPC 有一段自己的 IP 位址範圍（CIDR）。** 這個範圍決定 VPC 裡的機器可以拿到哪些 private IP。建立 VPC 時就要決定，而且之後不能修改主要範圍（只能追加）。
3. **VPC 本身不收費。** 收費的是放在裡面的東西，例如 NAT Gateway、VPC endpoint、public IPv4 位址與跨 AZ 傳輸的流量。

### Default VPC 與自建 VPC

每個 AWS 帳號在每個 Region 都有一個 **default VPC**，CIDR 是 `172.31.0.0/16`，每個 AZ 都有一個 public subnet，而且在裡面開的 EC2 預設會拿到 public IP。它的設計目標是「讓新手開了機器馬上能連上」，這正是小林踩到的坑：方便，但所有東西預設都暴露在 Internet 上。

正式環境應該使用**自建 VPC（custom VPC）**，自己決定 CIDR、哪些 subnet 能上 Internet、哪些完全不能。Default VPC 可以刪除；刪除後如有需要，也能透過 console 或 API 重新建立一個。

> [!tip] 考試提示
> 題目若提到「公司規定所有新 workload 不得使用 default VPC」或「EC2 意外取得 public IP」，答案通常牽涉自建 VPC、關閉 subnet 的 auto-assign public IP，或用 SCP／Config rule 限制（第 14、16 章）。

## 5.3 規劃 CIDR：一開始就決定未來能不能互連

建立 VPC 的第一個欄位就是 **IPv4 CIDR block**。第 3 章介紹過 CIDR 記法：`10.20.0.0/16` 表示前 16 個 bit 固定、後 16 個 bit 可變，共 2^16 = 65,536 個位址。

### AWS 的限制

- VPC 的 IPv4 CIDR 大小必須介於 **/16（65,536 個位址）到 /28（16 個位址）**。
- 建議使用 RFC 1918 的私有範圍：`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`。技術上也能用其他範圍，但若用了某個 Internet 上真實存在的 public 範圍，你的 VPC 將無法連到那段真實位址。
- 主要 CIDR 建立後不能修改，但可以追加 **secondary CIDR**（次要 CIDR）來擴充位址空間。每個 VPC 預設最多 5 個 IPv4 CIDR（主要 CIDR 也算在內），這是預設值，可申請提高（上限 50）。
- Secondary CIDR 有範圍限制：例如主要 CIDR 在 `10.0.0.0/8` 時，不能追加 `172.16.0.0/12` 或 `192.168.0.0/16` 的範圍，但可以追加 `10.0.0.0/8` 內其他不重疊的範圍或 `100.64.0.0/10`（常用於 EKS Pod 或 5.14 節的重疊網路解法）。
- 同一個 VPC 內的 CIDR 彼此不能重疊。

### 為什麼「不重疊」這麼重要？

路由的本質是「看目的位址，決定往哪裡送」。如果 Wanderly 的 VPC 是 `10.0.0.0/16`，辦公室網路也是 `10.0.0.0/16`，當 VPC 裡的機器要送封包到 `10.0.5.20` 時，路由器無從判斷這是 VPC 內部的機器還是辦公室的機器。結果就是：**兩個 CIDR 重疊的網路，無法用一般路由直接互通**（VPC peering 會直接拒絕建立，Transit Gateway 與 VPN 則會出現路由衝突）。

這個錯誤在第一天幾乎沒有代價，卻會在一年後公司要串接辦公室、併購另一家公司或建立第二個環境時爆發，而且修正方式通常是「重建 VPC 並搬遷所有資源」，代價非常高。所以**規劃 CIDR 時要用整個公司的視角，而不是只看眼前這個 VPC**。

### 小林的規劃

小林和網管同事一起列出公司所有現有與未來的網路，決定把 `10.0.0.0/8` 這個大空間切給不同用途。切法是「先分 Region、再分環境」：每個 Region 一個 /12，Region 內再切成 production 與 non-production 兩個 /13，每個 VPC 從所屬的區塊拿一個 /16：

| 用途 | CIDR | 說明 |
|---|---|---|
| 台北辦公室（既有） | `10.0.0.0/16` | 已存在，不能動 |
| AWS 東京（整個 Region） | `10.16.0.0/12` | 10.16.0.0–10.31.255.255 |
| 　東京 production 區塊 | `10.16.0.0/13` | 10.16–10.23；production 等級的 VPC |
| 　　shared services VPC | `10.16.0.0/16` | 預留（CI/CD、監控，第 7 章） |
| 　　production VPC | `10.20.0.0/16` | 本章要建立的 VPC |
| 　　data VPC | `10.21.0.0/16` | 預留（分析管線，第 7 章） |
| 　東京 non-production 區塊 | `10.24.0.0/13` | 10.24–10.31 |
| 　　staging VPC | `10.24.0.0/16` | 預留 |
| 　　development VPC | `10.25.0.0/16` | 預留 |
| AWS 新加坡（整個 Region） | `10.32.0.0/12` | 預留：production `10.32.0.0/13`、non-production `10.40.0.0/13`（第 8、41 章） |
| 其他 Region | `10.48.0.0/12` 起 | 每個 Region 再取一個 /12（第 42 章） |

每個 VPC 都分到 /16，代表單一 VPC 最多有 65,536 個位址。對大多數 workload 來說足夠，又不會把整個 `10.0.0.0/8` 一下子用光。區塊對齊的好處要到多 VPC、多 Region 時才看得出來：「往東京所有 VPC」只需要一條 `10.16.0.0/12` 的 route，「往東京所有 non-production」只需要一條 `10.24.0.0/13`（第 7、41 章）。後來併購的旅行社資料中心使用 `172.16.0.0/16`，不在 `10.0.0.0/8` 之內，也不會衝突（第 41 章）。

> [!warning] 常見誤解
> 「CIDR 越大越好，反正 VPC 不收錢。」VPC 確實不按 CIDR 大小收費，但企業可用的私有位址是有限的。每個團隊都拿一個 /8 或都用 `10.0.0.0/16`，最後一定會撞在一起。CIDR 是需要「分配」的公司資源，不是每個人自己挑。

## 5.4 Subnet：把 VPC 切成房間，每個房間只在一個 AZ

VPC 是一整棟大樓，**subnet（子網路）** 是大樓裡的房間。每個 subnet 是 VPC CIDR 裡的一小段，例如從 `10.20.0.0/16` 切出 `10.20.1.0/24`。

### Subnet 的關鍵規則

1. **一個 subnet 只屬於一個 AZ。** 這是 AWS 網路高可用設計的基礎：要讓服務撐過一個 AZ 故障，就必須在至少兩個 AZ 各建立 subnet，各放一份資源。一個 subnet 不能跨 AZ。
2. **Subnet 的 CIDR 必須落在 VPC CIDR 內**，同一 VPC 的 subnet 彼此不能重疊，大小同樣介於 /16 到 /28。
3. **Subnet 建立後 CIDR 不能修改。** 位址不夠用時，只能建立新的 subnet 再把資源移過去，所以一開始就要預留成長空間。
4. **每個 subnet 有 5 個位址被 AWS 保留**，不能分配給你的資源。

### AWS 保留的 5 個位址

以 `10.20.1.0/24` 為例：

| 位址 | 用途 |
|---|---|
| `10.20.1.0` | 網路位址（network address） |
| `10.20.1.1` | VPC router（路由器） |
| `10.20.1.2` | Amazon 提供的 DNS server（更精確地說，是「VPC CIDR 起始位址 +2」） |
| `10.20.1.3` | AWS 保留給未來使用 |
| `10.20.1.255` | 網路廣播位址（VPC 不支援廣播，但仍保留） |

所以一個 /24 共有 256 個位址，可用的是 256 − 5 = **251** 個。考試很喜歡考這個計算：

| Prefix | 總位址 | 可用位址 |
|---|---|---|
| /28 | 16 | 11 |
| /27 | 32 | 27 |
| /26 | 64 | 59 |
| /24 | 256 | 251 |
| /22 | 1,024 | 1,019 |
| /20 | 4,096 | 4,091 |

### 誰會吃掉 subnet 的位址？

不只 EC2。每個放在 subnet 裡的 **ENI（Elastic Network Interface，彈性網路介面，也就是虛擬網卡）** 至少占用一個 IP：EC2、RDS、Load Balancer 的節點、Lambda 連進 VPC 時建立的介面、VPC interface endpoint……。EKS 使用 VPC CNI 時更明顯：每個 Pod 都會從 subnet 拿到一個 IP（掛在節點 ENI 上的 secondary IP）。尤其 EKS 和大量 Lambda 的環境，位址消耗常常比預期快很多。

### Wanderly 的 subnet 切法

小林決定使用兩個 AZ（`ap-northeast-1a`、`ap-northeast-1c`），每個 AZ 有三種 subnet，並刻意讓 subnet 編號有規律，方便日後一眼看出用途：

| Subnet | AZ | CIDR | 可用位址 | 放什麼 |
|---|---|---|---|---|
| public-a | 1a | `10.20.0.0/24` | 251 | ALB 節點、NAT Gateway |
| public-c | 1c | `10.20.1.0/24` | 251 | ALB 節點、NAT Gateway |
| app-a | 1a | `10.20.16.0/20` | 4,091 | 應用程式 EC2／containers |
| app-c | 1c | `10.20.32.0/20` | 4,091 | 應用程式 EC2／containers |
| data-a | 1a | `10.20.64.0/24` | 251 | RDS、ElastiCache |
| data-c | 1c | `10.20.65.0/24` | 251 | RDS、ElastiCache |

App tier 給比較大的 /20，因為未來改用 containers 時會大量消耗 IP；public 與 data tier 放的東西少，/24 就夠。`10.20.2.0`～`10.20.15.255` 等空間刻意不用，留給第三個 AZ 或未來新增的 subnet 類型。

到這裡，房間都切好了，但房間之間的走廊還不存在：封包從一個 subnet 要去哪裡，由 route table 決定。

## 5.5 Route Table：每個 subnet 的導航規則

**Route table（路由表）** 是一組規則，每條規則（route）寫著「目的地是某個 CIDR 的封包，交給某個 target（下一站）」。VPC 裡有一個隱形的 **VPC router**，每個封包離開 ENI 時，router 會依照該 subnet 所關聯的 route table 決定往哪裡送。

### Local route：VPC 內部永遠互通

每個 route table 都自動有一條無法刪除的 route：

| Destination | Target |
|---|---|
| `10.20.0.0/16` | `local` |

意思是：「目的地在 VPC 範圍內的封包，直接在 VPC 內部送達。」所以**同一個 VPC 內不同 subnet 的機器，在路由層面預設就能互通**，即使它們在不同 AZ。要限制它們互相連線，靠的是 security group 與 NACL（第 6 章），而不是 route table。

### Main route table 與 custom route table

- 每個 VPC 有一個 **main route table**（主路由表）。沒有明確指定 route table 的 subnet，會自動使用 main route table。
- 你可以建立 **custom route table**，再把它「關聯（associate）」到特定 subnet。
- 一個 subnet 同一時間只能關聯一個 route table；一個 route table 可以被多個 subnet 共用。

> [!warning] 常見誤解
> 把 `0.0.0.0/0 → IGW` 加在 main route table 上，等於讓「所有沒有特別指定的 subnet」都變成 public subnet。包含之後新建、忘了關聯的 subnet。比較安全的做法是讓 main route table 只有 local route，需要上 Internet 的 subnet 明確關聯一個 public route table。

### Longest prefix match：最精確的規則優先

當多條 route 都符合目的位址時，VPC router 選擇 **prefix 最長（範圍最小、最精確）** 的那一條。例如：

| Destination | Target |
|---|---|
| `10.20.0.0/16` | local |
| `10.0.0.0/8` | Transit Gateway（往辦公室與其他 VPC） |
| `0.0.0.0/0` | NAT Gateway |

- 送往 `10.20.5.9` → 同時符合 /16、/8、/0，選 /16 → local。
- 送往 `10.0.3.4`（辦公室）→ 符合 /8 與 /0，選 /8 → Transit Gateway。
- 送往 `52.95.1.1`（Internet 上的 API）→ 只符合 /0 → NAT Gateway。

`0.0.0.0/0` 稱為 **default route（預設路由）**：所有沒有更精確規則的封包都走這裡。

### Route 的常見 target

| Target | 用途 | 本書章節 |
|---|---|---|
| `local` | VPC 內部 | 本章 |
| Internet Gateway（`igw-`） | 與 Internet 雙向通訊 | 本章 |
| NAT Gateway（`nat-`） | Private subnet 主動連出 | 本章 |
| Egress-only IGW（`eigw-`） | IPv6 只出不進 | 本章 |
| Gateway VPC endpoint（`vpce-`） | 私有存取 S3、DynamoDB | 第 6 章 |
| VPC peering（`pcx-`） | 連到另一個 VPC | 第 7 章 |
| Transit Gateway（`tgw-`） | 連到多個 VPC／地端 | 第 7、8 章 |
| Virtual private gateway（`vgw-`） | VPN／Direct Connect | 第 8 章 |
| ENI／instance | 導向防火牆或 NAT instance | 本章、第 41 章 |

## 5.6 Internet Gateway：VPC 對外的大門

到目前為止，Wanderly 的 VPC 是一個完全封閉的網路：裡面的機器可以互相通訊，但和 Internet 之間沒有任何路徑。要讓網站被使用者看到，需要 **Internet Gateway（IGW）**。

### IGW 的特性

- IGW 是一個附加（attach）在 VPC 上的元件，**一個 VPC 最多附加一個 IGW**。
- IGW 由 AWS 管理，**自動水平擴展、跨 AZ 高可用、沒有頻寬上限**。你不需要（也不能）為它規劃容量或做備援。這點和下一節的 NAT Gateway 不同。
- IGW 本身不收費。
- 對 IPv4 流量，IGW 負責把機器的 private IP 與它的 public IP 做一對一轉換。

### 什麼是「public subnet」？

這是本章最重要的觀念：**AWS 沒有一個叫做「public」的 subnet 開關。** 一個 subnet 是不是 public，完全由它關聯的 route table 決定：

> **Public subnet** = 關聯的 route table 中有一條 `0.0.0.0/0`（或特定 Internet 範圍）指向 Internet Gateway 的 route。
>
> **Private subnet** = 沒有指向 IGW 的 route。

Subnet 的名字叫 `public-a` 只是給人看的標籤。把一個叫 `private-db` 的 subnet 關聯到有 IGW route 的 route table，它就是 public subnet。

### 但光有 route 還不夠：public IP

封包要能在 Internet 上來回，機器還必須有一個 **public IPv4 位址**。EC2 取得 public IPv4 的方式有兩種：

1. **Auto-assigned public IP**：subnet 啟用「auto-assign public IPv4 address」或啟動 instance 時勾選，instance 啟動時隨機拿到一個。**instance 停止（stop）再啟動後位址會改變**。
2. **Elastic IP（EIP）**：你向 AWS 申請一個固定的 public IPv4，綁到 instance 或 ENI 上，stop／start 都不會變，直到你主動釋放。

自 2024 年 2 月起，AWS 對**所有 public IPv4 位址**（不論是否在使用中、是 auto-assigned 還是 EIP）按小時收費。這讓「把所有機器都配 public IP」不只不安全，也有實際成本。

### 封包怎麼走：從使用者到 public subnet 的 EC2

假設 `public-a` 裡有一台 EC2，private IP `10.20.0.10`、public IP `54.10.20.30`：

```text
使用者 203.0.113.7
   │ ① 送出：src=203.0.113.7  dst=54.10.20.30
   ▼
Internet
   ▼
[Internet Gateway]
   │ ② IGW 查到 54.10.20.30 對應 10.20.0.10，把 dst 改成 10.20.0.10
   ▼
[VPC router] ── ③ local route，送進 public-a
   ▼
[EC2 10.20.0.10]（security group 必須允許 443 入站）
   │ ④ 回應：src=10.20.0.10  dst=203.0.113.7
   ▼
[VPC router] ── ⑤ 查 public-a 的 route table：0.0.0.0/0 → IGW
   ▼
[Internet Gateway]
   │ ⑥ 把 src 從 10.20.0.10 改回 54.10.20.30
   ▼
使用者收到來自 54.10.20.30 的回應
```

① 使用者只知道 public IP。② IGW 做一對一位址轉換；EC2 的作業系統裡其實只看得到 private IP。③ 進入 VPC 後走 local route。④⑤ 回程封包需要 route table 有指向 IGW 的 route；如果沒有，封包到不了 Internet，使用者只會看到 timeout。⑥ IGW 再把來源位址換回 public IP。

這條路徑上任何一環缺失都會失敗：沒有 IGW、route table 沒有 IGW route、instance 沒有 public IP、security group 沒放行、NACL 擋住回程。5.11 節會把它整理成除錯清單。

> [!note] 為什麼 Wanderly 的網站 EC2 最後不放在 public subnet？
> 正式架構裡，使用者連的是 **Application Load Balancer（ALB）**，ALB 的節點放在 public subnet，後端 EC2 放在 private subnet，只接受來自 ALB 的流量（第 10 章）。這樣後端機器不需要 public IP，攻擊面小很多。public subnet 裡通常只放「必須面對 Internet」的元件：Load Balancer、NAT Gateway，以及少數需要直接對外的機器。

## 5.7 NAT Gateway：只出不進的單向門

應用程式 EC2 放到 private subnet 後，馬上遇到新問題：它要呼叫外部的金流 API、下載作業系統更新、拉取第三方套件，但 private subnet 沒有通往 Internet 的路。我們想要的是**「它可以主動連出去，但 Internet 不能主動連進來」**，這就是 NAT 的用途。

### NAT Gateway 怎麼運作

**NAT Gateway** 是 AWS 受管的 NAT（Network Address Translation，網路位址轉換）服務。一個 public NAT Gateway 的設定方式是：

1. 建立在 **public subnet** 裡（因為它自己要能走 IGW 出去），並綁定一個 **Elastic IP**。
2. 在 **private subnet 的 route table** 加上 `0.0.0.0/0 → nat-xxxx`。

```text
[app EC2 10.20.16.25]（private subnet app-a）
   │ ① src=10.20.16.25:41000  dst=52.95.1.1:443
   ▼
[VPC router] ── app-a route table：0.0.0.0/0 → NAT Gateway
   ▼
[NAT Gateway]（public subnet public-a，private IP 10.20.0.50，EIP 18.180.1.1）
   │ ② 把 src 改成 10.20.0.50:62001，並記住這條對應關係
   ▼
[VPC router] ── public-a route table：0.0.0.0/0 → IGW
   ▼
[Internet Gateway] ── ③ 把 src 10.20.0.50 換成 EIP 18.180.1.1
   ▼
Internet 上的金流 API 看到：來自 18.180.1.1:62001
   │ ④ 回應送回 18.180.1.1:62001
   ▼
IGW → NAT Gateway ── ⑤ 查對應表，轉回 10.20.16.25:41000
   ▼
[app EC2] 收到回應
```

關鍵在第 ② 與 ⑤ 步：NAT Gateway 維護一張連線對應表。**只有從內部主動發起的連線才會在表裡留下紀錄**，所以 Internet 上的人主動送封包到 `18.180.1.1`，NAT Gateway 找不到對應的內部機器，封包會被丟棄。這就是「只出不進」。

一個額外好處：所有 private subnet 的機器對外都顯示為同一個 EIP。若金流商要求「把你們的來源 IP 加入允許清單」，Wanderly 只要提供 NAT Gateway 的 EIP 即可。

### NAT Gateway 是 zonal 資源：每個 AZ 一台

這是考試與實務都很重要的設計點。**NAT Gateway 建立在某一個 subnet 裡，所以它屬於那個 AZ。** 它在該 AZ 內由 AWS 做了備援，但如果整個 AZ 故障，那台 NAT Gateway 也會失效。

如果小林只在 `public-a` 建一台 NAT Gateway，讓 `app-a` 與 `app-c` 都指向它：

- 平常：`app-c` 的流量要先跨 AZ 到 1a 的 NAT Gateway，產生跨 AZ 傳輸費用。
- 1a 故障時：`app-c` 的機器雖然還活著，卻因為唯一的 NAT Gateway 在 1a 而**全部失去對外連線**。一個 AZ 的故障擴散到了另一個 AZ。

正確做法是**每個 AZ 一台 NAT Gateway，且每個 AZ 的 private subnet 使用自己 AZ 的 NAT Gateway**，因此每個 AZ 需要各自的 private route table：

| Route table | 關聯 subnet | Destination | Target |
|---|---|---|---|
| rt-app-a | app-a | `10.20.0.0/16` | local |
| rt-app-a | app-a | `0.0.0.0/0` | nat-a（位於 public-a） |
| rt-app-c | app-c | `10.20.0.0/16` | local |
| rt-app-c | app-c | `0.0.0.0/0` | nat-c（位於 public-c） |

> [!note] 新的 regional 模式
> AWS 近年另外推出可依 AZ 自動擴展的 regional 可用性模式 NAT Gateway，能減少逐 AZ 管理的負擔。不過大多數既有架構與 SAA-C03 題目仍以「NAT Gateway 是 zonal、每個 AZ 一台」為標準答案。看到題目要求「NAT 高可用」時，請先想到每 AZ 一台的設計。

### 容量與費用

- 頻寬自動擴展（從 5 Gbps 起，最高 100 Gbps），不需要調整 instance 大小。
- 對**同一個目的地（IP + port + protocol）** 最多約 55,000 條同時連線。若大量連到同一個外部端點而出現 `ErrorPortAllocation`，可以為 NAT Gateway 加入更多 secondary IP，或分散到多台 NAT Gateway。
- NAT Gateway **不支援 security group**；要過濾它的流量，使用 subnet 的 NACL 或在後端機器上的 security group。
- 費用有兩部分：**每小時費用**，加上**每 GB 處理費用**（不論流量方向）。另外還有一般的資料傳輸費。在流量大的環境，NAT Gateway 常常是帳單上意外的大項目。

> [!tip] 考試提示：NAT 省錢的經典題
> 「private subnet 的 EC2 大量讀寫 S3，NAT Gateway 費用很高，怎麼降低成本？」答案是建立 **S3 gateway VPC endpoint**（第 6 章）：S3 流量改走 endpoint，不經過 NAT Gateway，而 gateway endpoint 本身不收費。DynamoDB 同理。

### NAT instance：舊做法

在 NAT Gateway 出現前，大家用一台自己管理的 EC2 當 NAT，稱為 **NAT instance**。必須**關閉該 instance 的 source/destination check**（因為它要轉送不是給自己的封包），再讓 private route table 指向這台 instance。

| 比較 | NAT Gateway | NAT instance |
|---|---|---|
| 管理 | AWS 受管，免 patch | 自己管 OS、patch、監控 |
| 可用性 | AZ 內高可用 | 單台 EC2，要自己做 failover |
| 頻寬 | 自動擴展到 100 Gbps | 取決於 instance type |
| Security group | 不支援 | 支援 |
| Port forwarding／兼當 bastion host（跳板機，工程師先登入它，再從它連進內部機器） | 不支援 | 可以 |
| 成本 | 每小時 + 每 GB 處理費 | 只有 EC2 費用，低流量時可能較便宜 |

考試裡，除非題目明確要求「最低成本且流量極小」或「需要 port forwarding 等客製功能」，否則以 NAT Gateway 為標準答案，因為它的營運負擔最低。

### Private NAT Gateway

NAT Gateway 還有 **private** 類型：不綁 EIP，不連 Internet，用來讓 private subnet 透過 Transit Gateway 或 VPN 連到其他私有網路，同時把來源位址轉換成可路由的位址。它是解決「兩邊 CIDR 重疊」的一種手段，SAP 題目較常出現（見 5.14 節）。

## 5.8 IPv6：沒有 NAT，只有 egress-only

IPv4 位址不夠用，所以需要 NAT；IPv6 位址多到每個裝置都能拿到全球唯一的位址，所以 **AWS 提供給 VPC 的 IPv6 位址是 public 的 global unicast 位址（GUA，可在 Internet 上路由）**，VPC 不提供 IPv6 對 IPv6 的 NAT。（IPAM 另有 private IPv6 位址的選項，考試很少碰到，本書不展開。）

那麼「只出不進」怎麼做？答案是 **egress-only Internet Gateway（EIGW）**：

- 只處理 IPv6。
- 允許 VPC 內的機器主動連出去並收到回應，但阻擋 Internet 主動發起的 IPv6 連線。
- 在 private subnet 的 route table 加上 `::/0 → eigw-xxxx`。
- 本身不收處理費（相較 NAT Gateway 省錢）。

| 需求 | IPv4 | IPv6 |
|---|---|---|
| 雙向對 Internet | IGW + public IP／EIP | IGW（`::/0 → igw`） |
| 只出不進 | NAT Gateway | Egress-only IGW |

VPC 可以是 **dual-stack（雙棧）**：同時有 IPv4 CIDR 與 IPv6 CIDR（AWS 提供的 /56，或自帶位址 BYOIP），subnet 通常各分到一個 /64。IPv4 和 IPv6 的路由是分開的，兩邊都要設定。如果是只有 IPv6 的 workload 要連到只有 IPv4 的服務，可以使用 NAT Gateway 的 **NAT64** 搭配 Route 53 Resolver 的 **DNS64**。

## 5.9 VPC 裡的 DNS 與 DHCP

機器之間通訊常常用名稱而不是 IP，例如應用程式連 `wanderly-db.xxxx.ap-northeast-1.rds.amazonaws.com`。VPC 內建 DNS 解析服務，稱為 **Amazon Route 53 Resolver**（也常被稱為 Amazon-provided DNS），位址是 **VPC CIDR 起始位址 + 2**（例如 `10.20.0.2`），也可以用 `169.254.169.253` 存取。

VPC 有兩個 DNS 相關屬性：

| 屬性 | 作用 | 預設（自建 VPC） |
|---|---|---|
| `enableDnsSupport` | 是否啟用 Amazon-provided DNS 解析 | 開啟 |
| `enableDnsHostnames` | 有 public IP 的 instance 是否取得 public DNS 名稱 | 關閉 |

**兩者都必須開啟**，才能使用 private hosted zone（第 9 章）與 interface VPC endpoint 的 private DNS（第 6 章）。這是很常見的「endpoint 建了但名稱解析失敗」原因。

**DHCP option set** 決定 instance 開機時拿到哪個 DNS server、網域名稱、NTP server。若公司要求 instance 使用地端的 Active Directory DNS，可以修改 DHCP option set；但更常見、更推薦的做法是保留 Amazon-provided DNS，再用 Route 53 Resolver 的轉送規則把公司網域轉到地端（第 8 章）。

## 5.10 組起來：Wanderly 的上線版 VPC

現在把所有元件組成完整架構：

```text
                         Internet
                            │
                   [Internet Gateway]
                            │
  VPC 10.20.0.0/16 ─────────┼──────────────────────────────────────
  │                         │                                     │
  │   AZ ap-northeast-1a    │          AZ ap-northeast-1c         │
  │ ┌───────────────────────┴─┐      ┌──────────────────────────┐ │
  │ │ public-a 10.20.0.0/24   │      │ public-c 10.20.1.0/24    │ │
  │ │  ALB 節點   NAT-a(EIP)  │      │  ALB 節點   NAT-c(EIP)   │ │
  │ └──────┬───────────▲──────┘      └──────┬───────────▲───────┘ │
  │        │ ①         │ ③                  │           │         │
  │ ┌──────▼───────────┴──────┐      ┌──────▼───────────┴───────┐ │
  │ │ app-a 10.20.16.0/20     │      │ app-c 10.20.32.0/20      │ │
  │ │  App EC2 / containers   │      │  App EC2 / containers    │ │
  │ └──────┬──────────────────┘      └──────┬───────────────────┘ │
  │        │ ②                              │                     │
  │ ┌──────▼──────────────────┐      ┌──────▼───────────────────┐ │
  │ │ data-a 10.20.64.0/24    │      │ data-c 10.20.65.0/24     │ │
  │ │  RDS primary            │◄────►│  RDS standby             │ │
  │ └─────────────────────────┘      └──────────────────────────┘ │
  └───────────────────────────────────────────────────────────────┘
```

① 使用者連到 ALB，ALB 把請求轉到 app tier（第 10 章）。② App 透過 local route 存取資料庫。③ App 要呼叫外部 API 時，經過自己 AZ 的 NAT Gateway 出去。資料庫 subnet 沒有任何指向 IGW 或 NAT 的 route，因此**在路由層面就不可能和 Internet 通訊**，這正是技術主管要求的「網路層隔離」。

這裡出現了三種 subnet：

| 類型 | Route table 的 default route | 適合放 |
|---|---|---|
| Public | `0.0.0.0/0 → IGW` | Load Balancer、NAT Gateway、bastion host（若仍需要；第 38 章會用 Session Manager 取代它） |
| Private（有出站） | `0.0.0.0/0 → NAT Gateway` | 應用程式、需要下載更新的 worker |
| Isolated（無出站） | 沒有 default route | 資料庫、快取、只和 VPC 內部或 VPC endpoint 通訊的服務 |

完整的 route table 設計：

| Route table | 關聯 subnet | Destination → Target |
|---|---|---|
| rt-public | public-a、public-c | `10.20.0.0/16 → local`；`0.0.0.0/0 → igw` |
| rt-app-a | app-a | `10.20.0.0/16 → local`；`0.0.0.0/0 → nat-a` |
| rt-app-c | app-c | `10.20.0.0/16 → local`；`0.0.0.0/0 → nat-c` |
| rt-data | data-a、data-c | `10.20.0.0/16 → local` |
| main（不關聯任何 subnet） | — | `10.20.0.0/16 → local` |

Public subnet 可以共用一張 route table，因為 IGW 是跨 AZ 的；app tier 必須每個 AZ 一張，因為 NAT Gateway 是 zonal 的。

### 用 CloudFormation 描述（節錄）

正式環境應該用 Infrastructure as Code 建立網路（第 37 章），下面是一個 AZ 的關鍵片段：

```yaml
Resources:
  Vpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.20.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true

  Igw:
    Type: AWS::EC2::InternetGateway
  IgwAttach:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref Vpc
      InternetGatewayId: !Ref Igw

  PublicA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      AvailabilityZone: ap-northeast-1a
      CidrBlock: 10.20.0.0/24
      MapPublicIpOnLaunch: false   # ALB 與 NAT 不需要；避免誤放的 EC2 自動拿到 public IP

  AppA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      AvailabilityZone: ap-northeast-1a
      CidrBlock: 10.20.16.0/20

  PublicRt:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
  PublicDefault:
    Type: AWS::EC2::Route
    DependsOn: IgwAttach
    Properties:
      RouteTableId: !Ref PublicRt
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref Igw
  PublicAAssoc:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicA
      RouteTableId: !Ref PublicRt

  NatEipA:
    Type: AWS::EC2::EIP
    Properties:
      Domain: vpc
  NatA:
    Type: AWS::EC2::NatGateway
    Properties:
      SubnetId: !Ref PublicA          # NAT 放在 public subnet
      AllocationId: !GetAtt NatEipA.AllocationId

  AppRtA:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
  AppDefaultA:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref AppRtA
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatA         # 只指向同 AZ 的 NAT
  AppAAssoc:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref AppA
      RouteTableId: !Ref AppRtA
```

讀這段 template 時，注意三個細節：route 要 `DependsOn` IGW attachment，否則可能在 IGW 尚未附加時就建立 route 而失敗；NAT Gateway 的 `SubnetId` 是 public subnet；app route table 指向「同一個 AZ」的 NAT。

## 5.11 除錯：EC2 連不上 Internet，依序檢查

網路問題最常見的症狀是 timeout，而 timeout 不會告訴你是哪一層擋住。依照封包路徑，從裡到外檢查：

**情境 A：public subnet 的 EC2 無法從 Internet 連入**

1. VPC 有沒有附加 IGW？
2. Instance 所在 subnet 的 route table 有沒有 `0.0.0.0/0 → igw`？（注意是「這個 subnet 實際關聯的」route table，可能是 main route table。）
3. Instance 有沒有 public IPv4 或 EIP？
4. Security group 有沒有允許該 port 的入站流量？
5. NACL 是否允許入站，**以及回程的 ephemeral ports 出站**（第 6 章）？
6. 作業系統防火牆與應用程式本身是否在監聽該 port？

**情境 B：private subnet 的 EC2 無法連到外部 API**

1. Private subnet 的 route table 有沒有 `0.0.0.0/0 → nat`？
2. NAT Gateway 是否放在 **public** subnet（它所在 subnet 的 route table 要有 IGW route）？
3. NAT Gateway 狀態是否為 Available、有沒有 EIP？
4. Instance 的 security group 出站規則是否允許（預設全部允許，但可能被改過）？
5. 兩個 subnet 的 NACL 是否擋住了流量或回程？
6. DNS 能否解析外部名稱（`enableDnsSupport` 是否開啟）？

工具方面，**VPC Reachability Analyzer** 可以分析兩個端點之間的路徑設定，直接指出是哪個 route table、security group 或 NACL 擋住；**VPC Flow Logs** 則記錄實際流量是被接受還是拒絕（第 6 章）。

## 5.12 比較與選型

### 我該把資源放在哪種 subnet？

```text
這個資源需要讓 Internet 主動連進來嗎？
├─ 是 → 能不能改成放在 Load Balancer / CloudFront 後面？
│        ├─ 能 → LB 放 public subnet，資源放 private subnet
│        └─ 不能（例如需要固定 public IP 的特殊服務）→ public subnet + EIP
└─ 否 → 它需要主動連到 Internet 嗎？
         ├─ 是 → 只需要連 AWS 服務（S3、DynamoDB…）？
         │        ├─ 是 → isolated/private subnet + VPC endpoint（第 6 章）
         │        └─ 否 → private subnet + NAT Gateway（IPv6 用 EIGW）
         └─ 否 → isolated subnet（無 default route）
```

### 元件對照

| 元件 | 範圍 | 高可用 | 收費 | 方向 |
|---|---|---|---|---|
| Internet Gateway | VPC（跨 AZ） | AWS 內建 | 免費 | IPv4／IPv6 雙向 |
| NAT Gateway | 單一 AZ | 每 AZ 各一台 | 每小時 + 每 GB | IPv4 只出不進 |
| NAT instance | 單一 AZ | 自己做 | EC2 費用 | IPv4 只出不進 |
| Egress-only IGW | VPC（跨 AZ） | AWS 內建 | 無處理費 | IPv6 只出不進 |
| Elastic IP | Region | — | 按小時（public IPv4） | 固定 public IPv4 |

## 5.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| private subnet 的 instance 要下載 patch／呼叫外部 API | NAT Gateway（放 public subnet）+ private route `0.0.0.0/0 → NAT` |
| NAT 要高可用、AZ 故障不影響其他 AZ | 每個 AZ 一台 NAT Gateway，每 AZ 獨立 private route table |
| IPv6 只允許出站 | Egress-only Internet Gateway |
| instance stop/start 後 public IP 變了，需要固定 | Elastic IP |
| 外部夥伴要把我們的來源 IP 加入允許清單 | NAT Gateway 的 EIP（所有 private instance 共用） |
| 子網路「一個 AZ 一個」、要跨 AZ 高可用 | 每個 AZ 建 subnet，資源分散 |
| subnet 位址不夠 | 加 secondary CIDR，建立新 subnet（既有 subnet 不能放大） |
| 計算可用 IP | 總數 − 5 |
| 未來要連地端或其他 VPC | CIDR 不能重疊；用 IPAM 集中規劃 |
| NAT Gateway 費用高、流量大多到 S3／DynamoDB | Gateway VPC endpoint |
| 資料庫不可被 Internet 存取 | 放在無 IGW／NAT route 的 subnet，且不給 public IP |
| interface endpoint／private hosted zone 名稱解析失敗 | 檢查 `enableDnsSupport` 與 `enableDnsHostnames` |

**常見陷阱**：

1. 把 NAT Gateway 放在 private subnet：NAT Gateway 本身必須能經 IGW 出去，放錯 subnet 就不通。
2. 以為 subnet 名稱或「勾選 public」就能讓它成為 public subnet：只有 route table 說了算。
3. 以為 IGW 需要做備援或可能成為頻寬瓶頸：它是 AWS 管理的高可用元件，選項裡「部署兩個 IGW」是錯的（一個 VPC 只能有一個）。
4. 以為 security group 可以套在 NAT Gateway 上：不行。
5. 只有一台 NAT Gateway 卻宣稱高可用：它是 zonal 的。
6. 想用 NAT Gateway 讓 Internet 連進 private instance：NAT 只出不進，入站要用 Load Balancer。

## 5.14 SAP 加深：大規模位址管理與重疊網路

SAA 考的是「一個 VPC 怎麼建」，SAP 考的是「一家有 50 個帳號、3 個 Region、兩個資料中心的公司，怎麼讓幾百個 VPC 不打架」。

### Amazon VPC IP Address Manager（IPAM）

**IPAM** 是集中規劃、分配、追蹤 IP 位址的服務，概念如下：

- **Scope**：最上層的位址空間容器。Private scope 管私有位址，public scope 管 public 位址。
- **Pool**：一段 CIDR 的集合，可以有階層。例如 top-level pool `10.0.0.0/8` → Region pool（東京 `10.16.0.0/12`）→ 環境 pool（東京 production `10.16.0.0/13`，production VPC `10.20.0.0/16` 就從這裡分配）。5.3 節的位址表就是這份 pool 階層；台北辦公室的 `10.0.0.0/16` 不屬於任何可分配的子 pool，因此不會被分配給 VPC。
- **Operating Regions**：IPAM 建立在一個 home Region，但可以設定多個 operating Region（它負責管理與監控的 Region）。Pool 的 locale 只能選 operating Region 之一。
- **Locale**：pool 可以分配給哪個 Region 的資源。要替東京的 VPC 分配 CIDR，必須從 locale 為 `ap-northeast-1` 的 pool 取得；locale 在建立 pool 時決定，之後不能修改。
- **Allocation rules**：限制從這個 pool 能拿的 CIDR 大小（例如最小 /24、最大 /20）以及必要 tag。
- 與 **AWS Organizations** 整合後，由 delegated administrator 帳號管理 IPAM，並透過 **AWS RAM** 把 pool 共享給其他帳號或 OU。帳號建立 VPC 時直接「從 IPAM pool 取得 CIDR」，自動保證不重疊。
- IPAM 會**監控**所有帳號的 VPC：哪些 CIDR 是從 pool 分配（managed）、哪些是有人繞過流程手動建立（unmanaged）、是否重疊、是否違反 allocation rules。它只負責發現與報告，**不會自動替既有 VPC 重新編址**。

### 已經重疊了怎麼辦？

併購是 SAP 的經典情境：兩家公司的 VPC 都用 `10.0.0.0/16`，短期內無法重新編址。可行方向：

1. **只需要呼叫少數服務** → **PrivateLink**（第 7 章）：provider 用 NLB 發布服務，consumer 在自己 VPC 建立 interface endpoint，完全不需要兩邊 CIDR 互通。這通常是最小暴露、最快的方案。
2. **需要較廣泛的連線** → **Private NAT Gateway**：在 VPC 加一段不重疊的 secondary CIDR（例如 `100.64.0.0/16`），把 private NAT Gateway 放在這段範圍的 subnet，經 Transit Gateway 出去時把來源位址轉成這段可路由位址。注意它解決的是「來源位址重疊」：要連的目的服務本身必須位於不重疊的位址（或放在對方 VPC 可路由範圍內的 Load Balancer 後面），否則封包在本 VPC 就會被 local route 留在 VPC 內。
3. **長期** → 用 IPAM 規劃新的不重疊位址，逐步遷移。

### 多帳號下的 VPC 共享

另一種減少 VPC 數量的方式是 **VPC sharing**：由網路帳號建立 VPC 與 subnet，再透過 AWS RAM 把 subnet 共享給同一 Organization 的其他帳號，各帳號在共享 subnet 裡建立自己的資源。這樣網路由中央團隊管理，應用團隊只管自己的資源，CIDR 數量也大幅減少（第 41 章）。

## 本章重點整理

- VPC 是 Region 範圍的私有網路，可以跨該 Region 的所有 AZ；VPC 本身免費，NAT Gateway、public IPv4、endpoint 與流量才收費。
- VPC CIDR 介於 /16 到 /28，主要 CIDR 不能修改，只能追加 secondary CIDR；要與其他網路互連，CIDR 絕對不能重疊。
- Subnet 只屬於一個 AZ；建立後 CIDR 不能修改；每個 subnet 有 5 個位址被 AWS 保留，可用數 = 總數 − 5。
- 每個 route table 都有不可刪除的 local route，所以 VPC 內所有 subnet 預設在路由上互通；限制互通要靠 security group 與 NACL。
- VPC router 以 longest prefix match 選擇 route；`0.0.0.0/0` 是 default route。
- Public subnet 的唯一定義是「route table 有指向 IGW 的 route」；資源還需要 public IPv4 或 Elastic IP 才能和 Internet 雙向通訊。
- IGW 一個 VPC 一個，AWS 管理、高可用、無頻寬瓶頸、免費。
- NAT Gateway 放在 public subnet、綁 EIP，讓 private subnet 主動連出；它是 zonal 資源，高可用設計是每 AZ 一台且每 AZ 一張 private route table。
- NAT Gateway 不支援 security group，按小時與處理量收費；S3 與 DynamoDB 流量改走 gateway endpoint 可以省下大量 NAT 費用。
- IPv6 位址都是 public，沒有 NAT；只出不進用 egress-only Internet Gateway。
- 使用 private hosted zone 與 interface endpoint private DNS 時，`enableDnsSupport` 與 `enableDnsHostnames` 都要開啟。
- 標準三層架構：public（LB、NAT）→ private（app）→ isolated（DB），每層跨至少兩個 AZ。
- SAP 層級用 IPAM（pool 階層、locale、RAM 共享）避免重疊；已重疊的網路用 PrivateLink 或 private NAT Gateway 處理。

## 本章練習題


### 練習 5-1｜SAA｜單選｜Subnet 可用位址計算

Wanderly 要為一個批次處理服務建立專用 subnet。這個服務在尖峰時最多同時執行 120 個 container，每個 container 都需要自己的 VPC IP 位址；同一個 subnet 還要放 4 個 interface VPC endpoint 的網卡。團隊希望在滿足尖峰需求的前提下，使用最小的 subnet。

應該選擇哪個 subnet 大小？

- A. /26
- B. /25
- C. /24
- D. /27

> [!answer]- 答案：C
> **A ✗** /26 共 64 個位址，扣掉 AWS 保留的 5 個只剩 59 個，遠低於所需的 124 個。
>
> **B ✗** 這是陷阱選項。需求是 120 + 4 = 124 個位址；/25 共 128 個位址，但扣掉 AWS 保留的 5 個後只剩 123 個，差 1 個就不夠。只算「總位址數」的人會選它。
>
> **C ✓** /24 共 256 個位址，可用 251 個，能容納 124 個需求並保留成長空間，是滿足需求的最小選項。
>
> **D ✗** /27 只有 32 − 5 = 27 個可用位址。
>
> **考點**：SAA-3.4｜subnet 可用位址 = 總位址數 − 5

### 練習 5-2｜SAA｜單選｜Public subnet 的真正定義

一位新進工程師在 VPC 中建立了一個名為 `public-web` 的 subnet，啟用了「auto-assign public IPv4 address」，並在裡面啟動一台 web server。這台 instance 有 public IP，security group 允許來自 `0.0.0.0/0` 的 TCP 443，但使用者從 Internet 連線時一律 timeout。VPC 已附加 Internet Gateway。

最可能的原因是什麼？

- A. 這個 subnet 關聯的 route table 沒有指向 Internet Gateway 的 `0.0.0.0/0` route
- B. Internet Gateway 需要部署兩個以上才能提供足夠頻寬
- C. Auto-assigned public IP 只能用於出站流量，入站流量必須使用 Elastic IP
- D. Security group 必須另外加入允許 443 回程的出站規則

> [!answer]- 答案：A
> **A ✓** Subnet 是否為 public，只由它關聯的 route table 決定。新 subnet 若沒有明確關聯，會使用 main route table；如果 main route table 只有 local route，回程封包無法送往 Internet，使用者就會看到 timeout。名稱與 auto-assign 設定都不會讓 subnet 變成 public。
>
> **B ✗** 一個 VPC 只能附加一個 IGW，IGW 由 AWS 管理、自動擴展，不會成為頻寬瓶頸。
>
> **C ✗** Auto-assigned public IP 與 Elastic IP 都能雙向使用，差別只在 stop/start 後位址是否改變。
>
> **D ✗** Security group 是 stateful，允許入站的連線，其回應會自動被允許出站，不需要另外設定回程規則。
>
> **考點**：SAA-3.4｜public subnet = route table 有 IGW route

### 練習 5-3｜SAA｜單選｜NAT Gateway 放置位置

Wanderly 的應用程式伺服器位於 private subnet，需要呼叫外部金流 API。工程師建立了一台 NAT Gateway 並把它放在應用程式所在的同一個 private subnet，再把該 subnet 的 `0.0.0.0/0` 指向這台 NAT Gateway，但應用程式仍然無法連出。

應如何修正，同時仍讓 Internet 無法主動連入應用程式伺服器？

- A. 為每台應用程式伺服器配置 Elastic IP，並保留 NAT Gateway 作為備援
- B. 把應用程式 subnet 的 `0.0.0.0/0` 改成指向 Internet Gateway
- C. 為 NAT Gateway 加上 security group，允許 443 出站
- D. 在 public subnet 重新建立 NAT Gateway 並綁定 Elastic IP，讓 private subnet 的 default route 指向它

> [!answer]- 答案：D
> **A ✗** 給應用程式伺服器 public IP 並讓它們直接對外，會增加攻擊面，也違反「Internet 不能主動連入」的需求；而且只配 EIP 但 route 仍指向 NAT，仍然不會通。
>
> **B ✗** 把 private subnet 的 default route 指向 IGW，就把它變成 public subnet，搭配 public IP 時 Internet 也能主動連入。
>
> **C ✗** NAT Gateway 不支援 security group。問題在於它所在的 subnet 沒有通往 IGW 的路徑。
>
> **D ✓** Public NAT Gateway 必須放在 route table 有 IGW route 的 public subnet，並綁定 Elastic IP，自己才能把流量送上 Internet。Private subnet 的 default route 指向它後，應用程式可以主動連出，而 NAT 只會轉送內部發起連線的回應。
>
> **考點**：SAA-1.2、SAA-3.4｜NAT Gateway 位於 public subnet、只出不進

### 練習 5-4｜SAA｜單選｜NAT Gateway 高可用

一家公司在兩個 AZ 各有一個 private subnet，兩個 subnet 共用一張 route table，`0.0.0.0/0` 指向位於 AZ-a 的唯一一台 NAT Gateway。一次 AZ-a 的故障中，AZ-b 的應用程式雖然正常運作，卻全部無法呼叫外部 API。公司要求一個 AZ 故障時，另一個 AZ 的對外連線不受影響。

最合適的設計是什麼？

- A. 把 NAT Gateway 的 instance size 調大，並啟用 Multi-AZ 選項
- B. 在每個 AZ 的 public subnet 各建立一台 NAT Gateway，為每個 AZ 的 private subnet 建立獨立 route table 並指向同 AZ 的 NAT Gateway
- C. 在 AZ-b 建立第二台 NAT Gateway，並在共用的 route table 加入第二條 `0.0.0.0/0` route 指向它
- D. 改用 egress-only Internet Gateway，因為它是跨 AZ 的

> [!answer]- 答案：B
> **A ✗** NAT Gateway 沒有 instance size，也沒有 Multi-AZ 選項；它本身就是 zonal 資源，頻寬會自動擴展。
>
> **B ✓** NAT Gateway 屬於單一 AZ。每個 AZ 一台、每個 AZ 的 private subnet 使用自己 AZ 的 NAT，才能讓故障留在單一 AZ 內，也能避免平時的跨 AZ 傳輸費用。
>
> **C ✗** 同一張 route table 不能有兩條相同 destination（`0.0.0.0/0`）的 route，也沒有自動 failover 的機制。
>
> **D ✗** Egress-only IGW 只處理 IPv6 流量；題目中的應用程式與外部 API 使用 IPv4 時無法替代 NAT Gateway。
>
> **考點**：SAA-2.2、SAA-3.4｜NAT Gateway 是 zonal，每 AZ 一台

### 練習 5-5｜SAA｜選兩項｜Subnet 位址不足

Wanderly 的 data VPC 是 `10.21.0.0/16`，早期建立時整個範圍都切成了 /24 subnet 分給各團隊。其中 app subnet `10.21.16.0/24` 的 IP 即將用完，因為分析團隊改用 EKS 後每個 Pod 都會占用一個 VPC IP。這個 subnet 正在服務正式流量，不能停機。VPC 已經沒有未使用的空間可以再切出大 subnet。

哪兩個步驟是可行的做法？（選兩項）

- A. 為 VPC 關聯一段與既有網路都不重疊的 secondary IPv4 CIDR
- B. 直接把 `10.21.16.0/24` 修改成 `10.21.16.0/20`
- C. 為每個 Pod 建立一個 NAT Gateway，讓多個 Pod 共用同一個 private IP
- D. 從新的 CIDR 建立新 subnet，讓新的節點與 Pod 使用新 subnet，再逐步移轉
- E. 刪除 VPC 的 local route，以釋放保留位址

> [!answer]- 答案：A、D
> **A ✓** VPC 主要 CIDR 不能修改，但可以追加 secondary CIDR 擴充位址空間。追加前要確認新範圍不與 peering、Transit Gateway 或地端網路重疊。
>
> **B ✗** Subnet 建立後 CIDR 不能修改，無法原地放大。
>
> **C ✗** NAT Gateway 只轉換「往外連」的來源位址，不會讓 subnet 內的 ENI 共用 IP，也不會增加 subnet 可分配的位址。
>
> **D ✓** 有了新的位址空間後，要建立新 subnet，再讓新資源使用它（EKS 可以新增 node group 或設定 Pod 使用新 subnet），逐步移轉而不中斷服務。
>
> **E ✗** Local route 無法刪除，它也與 AWS 保留的 5 個位址無關。
>
> **考點**：SAA-3.4｜secondary CIDR 與 subnet 不可修改

### 練習 5-6｜SAA｜單選｜Elastic IP 使用時機

一個合作夥伴的 API 只接受白名單中的來源 IP。Wanderly 有 20 台位於兩個 AZ private subnet 的應用程式 instance 會呼叫這個 API，instance 數量會隨 Auto Scaling 變動。團隊要提供給夥伴的 IP 數量最少且長期固定，並維持 AZ 層級的高可用。

最合適的做法是什麼？

- A. 為每台 instance 配置 Elastic IP，並把所有 EIP 提供給夥伴
- B. 把 instance 移到 public subnet 並使用 auto-assigned public IP
- C. 在每個 AZ 部署一台使用 Elastic IP 的 NAT Gateway，讓各 AZ 的 private subnet 使用同 AZ 的 NAT，並把這兩個 EIP 提供給夥伴
- D. 部署一台 NAT instance，關閉 source/destination check，並為它配置 Elastic IP

> [!answer]- 答案：C
> **A ✗** Auto Scaling 會不斷增減 instance，每台配 EIP 需要持續更新白名單，而且每個 public IPv4 都要收費、也增加攻擊面。
>
> **B ✗** Auto-assigned public IP 在 instance 重新啟動或替換時會改變，無法提供固定白名單；把應用程式搬到 public subnet 也降低安全性。
>
> **C ✓** 所有經過 NAT Gateway 的流量都以它的 EIP 作為來源位址。每 AZ 一台 NAT 時，夥伴只需允許兩個固定 IP，instance 怎麼擴縮都不受影響，且一個 AZ 故障不會影響另一個 AZ。
>
> **D ✗** 單一 NAT instance 是單點故障，還需要自行維護作業系統與 failover，營運負擔較高。
>
> **考點**：SAA-1.2、SAA-2.2｜NAT Gateway EIP 作為固定出口位址

### 練習 5-7｜SAA｜單選｜降低 NAT Gateway 費用

Wanderly 的影像處理 worker 位於 private subnet，每天從同一 Region 的 S3 bucket 讀取並寫回約 5 TB 照片。每月帳單顯示 NAT Gateway 的資料處理費用非常高。Worker 不需要存取 Internet 上的其他服務。

哪個做法能以最少的變更降低成本？

- A. 把 NAT Gateway 改成 NAT instance
- B. 建立 S3 gateway VPC endpoint，並把它加入 worker subnet 的 route table
- C. 把 worker 移到 public subnet 並配置 Elastic IP，直接經 Internet Gateway 存取 S3
- D. 為 S3 bucket 啟用 Transfer Acceleration

> [!answer]- 答案：B
> **A ✗** NAT instance 沒有每 GB 處理費，但要自己維護、做高可用，且單台 instance 的頻寬可能不足以處理每天 5 TB；這不是最少變更也不是最好的做法。
>
> **B ✓** S3 gateway endpoint 會在 route table 中加入指向 S3 prefix list 的 route，S3 流量改走 endpoint 而不經過 NAT Gateway。Gateway endpoint 本身不收費，應用程式也不需要修改。
>
> **C ✗** 把 worker 暴露在 public subnet 會降低安全性，也增加 public IPv4 費用。
>
> **D ✗** Transfer Acceleration 是透過 edge location 加速遠距離上傳，會增加費用，與 NAT 處理費無關。
>
> **考點**：SAA-4.4｜gateway endpoint 取代 NAT 存取 S3

### 練習 5-8｜SAA｜單選｜IPv6 只出不進

Wanderly 的 VPC 已改為 dual-stack。一組新的 IPv6-only worker 位於 private subnet，需要主動連到 Internet 上的 IPv6 API，但安全規範要求 Internet 不能主動對這些 worker 建立 IPv6 連線。團隊希望營運成本最低。

應如何設定？

- A. 建立 NAT Gateway 並在 route table 加入 `::/0 → NAT Gateway`
- B. 在 route table 加入 `::/0 → Internet Gateway`，並移除 worker 的 IPv6 位址
- C. 為每台 worker 設定 IPv6 Elastic IP
- D. 建立 egress-only Internet Gateway，並在 worker subnet 的 route table 加入 `::/0 → egress-only Internet Gateway`

> [!answer]- 答案：D
> **A ✗** NAT Gateway 處理的是 IPv4 的來源位址轉換（另有 NAT64 讓 IPv6 連到 IPv4 目的地），不是 IPv6 對 IPv6 的出站控制方式，而且會產生處理費。
>
> **B ✗** 指向 IGW 的 IPv6 route 允許雙向流量；移除 IPv6 位址則讓 worker 完全無法使用 IPv6。
>
> **C ✗** Elastic IP 只適用於 IPv4。
>
> **D ✓** Egress-only Internet Gateway 專門提供 IPv6 的「只出不進」：允許內部發起的連線與其回應，阻擋 Internet 主動發起的連線，而且沒有像 NAT Gateway 那樣的處理費。
>
> **考點**：SAA-1.2、SAA-4.4｜egress-only IGW

### 練習 5-9｜SAA｜單選｜Main route table 風險

稽核發現，Wanderly VPC 的 main route table 中有一條 `0.0.0.0/0 → igw` 的 route。目前所有 subnet 都已明確關聯自己的 custom route table。

這個設定最主要的風險是什麼？

- A. 未來新建、沒有明確關聯 route table 的 subnet 會自動成為 public subnet
- B. 所有已關聯 custom route table 的 subnet 會同時套用 main route table，導致路由衝突
- C. Internet Gateway 會因為被 main route table 引用而無法分離
- D. Main route table 的 IGW route 會讓 VPC 內所有 security group 自動允許 Internet 入站

> [!answer]- 答案：A
> **A ✓** 沒有明確關聯的 subnet 會使用 main route table。保留 IGW route 等於讓之後任何「忘了關聯」的 subnet 一建立就有 Internet 路徑，若資源又拿到 public IP 就會暴露。最佳做法是讓 main route table 只保留 local route。
>
> **B ✗** 一個 subnet 同時只關聯一張 route table。已明確關聯 custom route table 的 subnet 完全不使用 main route table。
>
> **C ✗** Route table 引用 IGW 不會阻止分離 IGW，分離後該 route 會成為 blackhole。
>
> **D ✗** Route table 與 security group 是不同層的控制；route 不會修改任何 security group 規則。
>
> **考點**：SAA-1.2｜main route table 的隱性影響

### 練習 5-10｜SAP｜單選｜重疊 CIDR 的最小暴露連線

Wanderly 併購了一家旅行社。旅行社的核心 VPC 使用 `10.20.0.0/16`，恰好和 Wanderly 的 production VPC 相同，短期內無法重新編址。Wanderly 的訂房服務只需要呼叫旅行社 VPC 裡的一個庫存查詢 HTTPS API，其他系統不需要互通。安全團隊要求只暴露這一個服務，並盡快完成。

最合適的方案是什麼？

- A. 建立 VPC peering，並在兩邊 route table 加入更精確的 /24 route 避開衝突
- B. 把兩個 VPC 都連到 Transit Gateway，並把兩個 VPC 的 route 傳播到同一張 TGW route table
- C. 由旅行社以 Network Load Balancer 建立 PrivateLink endpoint service，Wanderly 在自己的 VPC 建立 interface endpoint 連線
- D. 在兩個 VPC 各部署 NAT instance，並在兩邊設定 port forwarding

> [!answer]- 答案：C
> **A ✗** VPC peering 不允許在 CIDR 重疊的 VPC 之間建立。
>
> **B ✗** 兩個相同的 prefix 傳播到同一張 TGW route table 會產生衝突，無法正確路由。
>
> **C ✓** PrivateLink 只在 consumer VPC 建立一個使用 consumer 自己位址的 endpoint ENI，流量由 AWS 轉送到 provider 的 NLB，不需要兩邊 CIDR 互相可路由。它只暴露一個服務，符合最小暴露與快速交付。
>
> **D ✗** 自建 NAT instance 與 port forwarding 營運負擔高、易出錯，而且仍需解決兩個 VPC 之間的路由問題。
>
> **考點**：SAP-1.1、SAP-4.3｜PrivateLink 解決 CIDR 重疊

### 練習 5-11｜SAP｜選兩項｜多帳號 CIDR 治理

Wanderly 預計在一年內成長到 60 個 AWS 帳號、3 個 Region，並以 Direct Connect 連回兩個既有資料中心。過去各團隊自行挑選 VPC CIDR，已經出現兩次重疊事故。平台團隊希望新帳號建立 VPC 時自動取得不重疊的 CIDR，並能發現繞過流程手動建立的 VPC。

哪兩個做法最合適？（選兩項）

- A. 要求各團隊在共用試算表登記 CIDR，並由網路團隊每季人工檢查
- B. 與 AWS Organizations 整合，在 delegated administrator 帳號建立 IPAM，先排除資料中心使用中的範圍，再依 Region 與環境建立具有正確 locale 的 pool 階層
- C. 在每個帳號的 VPC 加上 Name tag，IPAM 會依照 tag 自動重新編址重疊的 VPC
- D. 在每個 VPC 建立 NACL，拒絕來自其他 VPC 的流量，以避免重疊造成問題
- E. 透過 AWS RAM 把 pool 共享給對應 OU，讓 VPC 從 pool 配置 CIDR，並使用 IPAM 監控 unmanaged 與重疊的資源

> [!answer]- 答案：B、E
> **A ✗** 人工登記無法在建立 VPC 時強制檢查，衝突要到連線時才被發現，正是過去事故的原因。
>
> **B ✓** 由 delegated administrator 集中管理 IPAM，先把地端已用範圍排除，再用 pool 階層與 locale 把位址分配到各 Region 與環境，可以從源頭避免重疊。
>
> **C ✗** Tag 可以用於 allocation rules 與分類，但 IPAM 只負責規劃、分配與監控，不會自動替運作中的 VPC 重新編址。
>
> **D ✗** NACL 過濾流量，無法讓路由器分辨兩個相同的目的 prefix，也解決不了互連需求。
>
> **E ✓** 透過 RAM 共享 pool 讓各帳號自助從 pool 取得 CIDR；IPAM 的監控能找出未經 pool 分配的 unmanaged VPC 與重疊 CIDR，滿足「發現繞過流程」的需求。
>
> **考點**：SAP-1.1、SAP-1.4｜IPAM 與 Organizations／RAM 整合

### 練習 5-12｜SAP｜單選｜IPAM pool locale

Wanderly 的 IPAM 建立在 `ap-northeast-1`（東京），由網路帳號集中管理。新加坡（`ap-southeast-1`）的團隊要從 IPAM 為新 VPC 取得 CIDR，但建立時發現無法選到任何可用的 pool。目前 pool 階層是：top-level pool（無 locale）→ production pool（locale：`ap-northeast-1`）。

應如何處理？

- A. 把 production pool 的 locale 改成 `ap-southeast-1`
- B. 在新加坡另外建立一個獨立的 IPAM，自行管理新加坡的位址
- C. 直接從 top-level pool 配置 CIDR 給新加坡 VPC
- D. 從 top-level pool 建立一個 locale 為 `ap-southeast-1` 的新 child pool，分配適當 CIDR 並共享給新加坡團隊的帳號

> [!answer]- 答案：D
> **A ✗** Pool 的 locale 建立後不能修改；而且改了也會影響原本東京的配置。
>
> **B ✗** 另建 IPAM 會失去集中視野，重新製造跨 Region 重疊的風險。
>
> **C ✗** 要配置給 Regional 資源（VPC），必須使用 locale 與該資源 Region 相符的 pool；無 locale 的 top-level pool 不能直接配置給新加坡 VPC。
>
> **D ✓** IPAM 可以在一個 home Region 集中管理全球位址，各 Region 透過 locale 相符的 child pool 配置 CIDR。建立新加坡 locale 的 pool 並透過 RAM 共享，是標準做法（前提是 IPAM 的 operating Regions 已包含 `ap-southeast-1`，若沒有要先加入）。
>
> **考點**：SAP-1.1｜IPAM home Region 與 pool locale

### 練習 5-13｜SAP｜單選｜集中出口的位址轉換

Wanderly 透過 Transit Gateway 連接數十個 VPC 與地端資料中心。新併購團隊的 VPC 使用 `10.0.0.0/16`，和地端某段網路重疊，因此這個 VPC 的位址不能直接在 Transit Gateway 上路由。這個 VPC 裡的應用程式只需要「主動連到」地端幾個位於 `172.16.10.0/24`（不重疊）的服務，地端不需要主動連入該 VPC。團隊希望在不重新編址既有 subnet 的情況下盡快完成。

最合適的做法是什麼？

- A. 為該 VPC 加入一段不重疊的 secondary CIDR，在其中建立 subnet 並放置 private NAT Gateway；應用程式往地端的流量先經 private NAT Gateway 轉換來源位址，再送往 Transit Gateway
- B. 在該 VPC 建立 public NAT Gateway，讓往地端的流量經 Internet 繞過重疊問題
- C. 在 Transit Gateway route table 為重疊的 `10.0.0.0/16` 建立兩條相同 route，分別指向 VPC 與地端
- D. 為該 VPC 建立 egress-only Internet Gateway，讓流量只出不進

> [!answer]- 答案：A
> **A ✓** Private NAT Gateway 不連 Internet，用來把來源位址轉換成它所在 subnet 的位址。把它放在一段不重疊、可在 TGW 上路由的 secondary CIDR 中，地端看到的來源就是這段不重疊位址，回應也能正確送回。需求只有「單向主動連出」，正好符合 NAT 的特性。
>
> **B ✗** 往地端私有服務的流量不應經過 Internet，也無法直接到達地端私有位址。
>
> **C ✗** 同一個 route domain 中相同 prefix 無法同時指向兩個目的地，會造成衝突。
>
> **D ✗** Egress-only IGW 只處理 IPv6 往 Internet 的流量，與 IPv4 私有網路的重疊無關。
>
> **考點**：SAP-1.1、SAP-4.3｜private NAT Gateway 處理重疊網路

### 練習 5-14｜SAA｜單選｜Isolated subnet 與資料庫

Wanderly 的 RDS for MySQL 需要滿足以下要求：只有應用程式 tier 能連線、在網路層完全沒有和 Internet 互通的路徑，並且跨兩個 AZ 高可用。應用程式 tier 位於兩個 AZ 的 private subnet，經 NAT Gateway 對外。

資料庫 subnet 應如何設計？

- A. 把 RDS 放在應用程式所在的同一組 private subnet，讓 security group 限制只有應用程式能連
- B. 在兩個 AZ 各建立一個 data subnet，關聯一張只有 local route 的 route table，用這兩個 subnet 組成 DB subnet group，並把 RDS 設為不可公開存取
- C. 在兩個 AZ 各建立 data subnet，route table 的 `0.0.0.0/0` 指向 NAT Gateway，方便資料庫下載 patch
- D. 建立一個跨兩個 AZ 的大型 data subnet，讓 Multi-AZ standby 共用同一個 subnet

> [!answer]- 答案：B
> **A ✗** 與應用程式共用 subnet 時，資料庫所在 subnet 有通往 NAT 的 default route，不符合「網路層完全沒有 Internet 路徑」；也讓兩個 tier 的網路政策難以分開管理。
>
> **B ✓** Isolated subnet 的 route table 只有 local route，在路由層面就無法和 Internet 通訊。DB subnet group 需要涵蓋至少兩個 AZ 的 subnet，才能使用 Multi-AZ。RDS 的作業系統與引擎 patch 由 AWS 透過受管機制處理，資料庫 subnet 不需要 NAT。
>
> **C ✗** 加上 NAT route 會讓資料庫可以主動連到 Internet，違反要求；RDS 也不需要它來 patch。
>
> **D ✗** Subnet 只能屬於一個 AZ，不能跨 AZ。
>
> **考點**：SAA-1.2、SAA-2.2｜isolated subnet 與 DB subnet group

### 練習 5-15｜SAP｜單選｜集中管理網路的多帳號共享

Wanderly 有 15 個應用團隊，各自擁有 AWS 帳號。網路團隊希望集中管理 VPC、subnet、route table 與 NAT Gateway，讓應用團隊無法修改網路設定，但仍能在指定的 subnet 中部署自己的 EC2 與 RDS。公司也希望減少 VPC 數量與跨 VPC 的連線成本。

最合適的做法是什麼？

- A. 每個應用帳號各自建立 VPC，再用 VPC peering 全互連，並用 SCP 禁止修改 route table
- B. 把所有團隊的 IAM user 都建立在網路帳號中，在同一個帳號內部署所有資源
- C. 由網路帳號擁有 VPC，透過 AWS RAM 把指定 subnet 共享給各應用帳號（VPC sharing），應用團隊在共享 subnet 中建立並管理自己的資源
- D. 在每個應用帳號建立 VPC，並把每個 VPC 的 route table 指向網路帳號的 NAT Gateway ENI

> [!answer]- 答案：C
> **A ✗** 15 個 VPC 全互連需要 105 條 peering，管理複雜；VPC 數量並沒有減少。
>
> **B ✗** 把所有團隊放進同一個帳號會失去帳號層級的權限、帳單與故障隔離。
>
> **C ✓** VPC sharing 讓 VPC owner（網路帳號）管理 VPC、subnet、route table、NAT 等網路資源，participant 帳號只能在共享的 subnet 中建立與管理自己的資源，不能修改 owner 的 subnet、route table 等網路設定。VPC 數量減少，同一 VPC 內的流量也不需要經過 peering 或 Transit Gateway。
>
> **D ✗** Route table 不能指向另一個帳號的 NAT Gateway；跨 VPC 的流量也需要先有 peering 或 TGW 連線。
>
> **考點**：SAP-1.4、SAP-1.1｜VPC sharing（AWS RAM）

### 練習 5-16｜SAA｜選兩項｜Private DNS 名稱解析失敗

Wanderly 在自建 VPC 中建立了 Secrets Manager 的 interface VPC endpoint，並啟用了 private DNS。但應用程式解析 `secretsmanager.ap-northeast-1.amazonaws.com` 時仍拿到 public IP，流量因此走 NAT Gateway。Endpoint 的 security group 已允許來自應用程式 subnet 的 443。

應檢查並開啟哪兩個 VPC 屬性？（選兩項）

- A. Default VPC 選項
- B. Auto-assign public IPv4 address
- C. `enableDnsSupport`
- D. `enableDnsHostnames`
- E. Source/destination check

> [!answer]- 答案：C、D
> **A ✗** 是否為 default VPC 與 private DNS 無關，自建 VPC 一樣可以使用。
>
> **B ✗** Auto-assign public IP 決定 instance 是否取得 public IPv4，與名稱解析無關。
>
> **C ✓** `enableDnsSupport` 開啟 Amazon-provided DNS（VPC CIDR + 2）。沒有它，VPC 內部無法使用 Route 53 Resolver 提供的 private DNS 記錄。
>
> **D ✓** Interface endpoint 的 private DNS 需要 `enableDnsHostnames` 與 `enableDnsSupport` 同時開啟。自建 VPC 預設 `enableDnsHostnames` 是關閉的，這是最常見的原因。
>
> **E ✗** Source/destination check 只和 NAT instance 這類需要轉送他人封包的 instance 有關。
>
> **考點**：SAA-3.4、SAA-1.2｜VPC DNS 屬性與 interface endpoint private DNS
