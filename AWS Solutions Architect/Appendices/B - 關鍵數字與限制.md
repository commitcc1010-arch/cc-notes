---
title: 關鍵數字與限制
---

# 附錄 B　關鍵數字與限制

## B.1 怎麼使用本附錄

架構題常常靠一個數字決定答案。例如工作要跑 20 分鐘，Lambda 就不能用。訊息 2 MB，SQS 本身放不下，就要用 claim check pattern。本附錄依服務整理全書各章提到的數字與限制。每一列都標出原本在哪一章講解，忘記原理時可以回頭讀。

表格欄位的意思如下：

- **項目／數值**：與章節正文一致。章節已經過技術審查，若本附錄與章節不同，以章節為準。
- **可否調整**：
  - **hard limit**：服務設計上的固定限制，申請也不能提高，碰到只能改設計。
  - **預設 quota，可申請提高**：透過 Service Quotas 或 AWS Support 申請提高的預設配額。
  - **可設定**：你在資源上自行選擇的參數，例如 retention、timeout，只能在列出的範圍內選。
  - **設計行為**：架構本身的特性，例如「EBS 綁定單一 AZ」，談不上配額。
- **考試注意**：考題常用的數字、常見陷阱，或考題與現行數字的差異。
- **出處**：講解這個數字的章節與小節。

> [!tip] 考試提示
> 考試很少直接問「上限是多少」，而是把數字藏在情境裡：「每則訊息約 600 KB」「批次工作約 40 分鐘」「每秒 8,000 次寫入同一個 key」。讀題時看到數字，先對照本附錄，判斷它有沒有超過某個 hard limit。超過了，那個服務的選項通常就可以刪掉。

已經改變、但考題可能仍用舊值的數字，集中整理在 B.40 節。

## B.2 認證考試本身

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| SAA-C03 題數 | 65 題（50 題計分、15 題不計分） | — | 不計分題看不出來，每題都要認真作答 | 第 1 章 1.2 |
| SAA-C03 時間 | 130 分鐘（每題約 2 分鐘） | 母語非英語者可申請 ESL +30 分鐘（僅英文考試） | 第一輪約 100 分鐘做完，保留 30 分鐘檢查 | 第 1 章 1.2、1.6 |
| SAA-C03 及格分數 | 720（量尺 100–1000） | — | 720 分不等於答對 72% | 第 1 章 1.2 |
| SAP-C02 題數 | 75 題（65 題計分、10 題不計分） | — | — | 第 1 章 1.2 |
| SAP-C02 時間 | 180 分鐘（每題約 2.4 分鐘） | 同上 | 第一輪約 150 分鐘做完 | 第 1 章 1.2、1.6 |
| SAP-C02 及格分數 | 750（量尺 100–1000） | — | — | 第 1 章 1.2 |
| 倒扣 | 無；空白算錯 | — | 每題都要作答 | 第 1 章 1.2 |
| 多選題 | 5 個以上選項中選 2 個以上，不給部分分數 | — | — | 第 1 章 1.2 |
| SAA domain 比重 | 安全 30%、韌性 26%、效能 24%、成本 20% | — | — | 第 1 章 1.3 |
| SAP-C02 domain 比重 | 組織複雜度 26%、新方案 29%、持續改善 25%、遷移與現代化 20% | — | SAP-C03 的比重可能不同 | 第 1 章 1.3 |
| 證照效期 | 3 年 | — | — | 第 1 章 1.2 |
| SAP 改版 | SAP-C03 自 2026-10-27 開放報名；SAP-C02 最後應考日 2026-11-17 | — | 報名前先到官方證照頁面確認版本 | 第 1 章 1.2；第 54 章 54.10 |

## B.3 全球基礎設施、帳號與可用性換算

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 Region 的 AZ 數 | 至少 3 個（部分舊 Region 對新帳號只開放 2 個，例如 us-west-1） | 設計行為 | — | 第 2 章 2.3 |
| AZ 之間延遲 | 個位數毫秒 | 設計行為 | 同步複寫可以跨 AZ，跨 Region 通常只能非同步 | 第 2 章 2.3 |
| Local Zones 延遲 | 個位數毫秒（多數需 opt-in） | — | 「某城市使用者要個位數毫秒延遲」→ Local Zones | 第 2 章 2.3 |
| AWS account ID | 12 位數 | — | — | 第 2 章 2.8 |
| Well-Architected pillars | 6 個 | — | — | 第 2 章 2.7 |
| 跨 AZ 資料傳輸 | 收費，雙向各計一次（常見每方向每 GB 0.01 美元起） | — | 同 AZ 走 private IP 免費 | 第 2 章 2.9；第 39 章 39.3 |
| Public IPv4 位址 | 自 2024-02 起每個位址按小時收費（不論是否使用） | — | 成本題要考慮 IPv6 或減少 public IP | 第 3 章 3.3；第 5 章 5.6 |
| 99.9% 可用性 | 每年約 8.76 小時、每月約 43.8 分鐘停機 | — | — | 第 4 章 4.8 |
| 99.99% 可用性 | 每年約 52.6 分鐘、每月約 4.4 分鐘停機 | — | — | 第 4 章 4.8 |
| 99.999% 可用性 | 每年約 5.26 分鐘、每月約 26 秒停機 | — | — | 第 4 章 4.8 |
| 串聯／並聯 | 串聯相乘（3 個 99.9% ≈ 99.7%）；並聯 1 − 失敗率相乘（2 個 99% → 99.99%） | — | 多一個串聯元件，整體可用性就下降 | 第 4 章 4.8 |
| 光纖傳播速度 | 每毫秒約 200 公里；台北到美東 RTT 常在 150–200 毫秒以上 | 物理限制 | 跨洲延遲靠 edge 或多 Region 解決，加大頻寬沒有用 | 第 3 章 3.14 |
| 靜態穩定容量 | 每個 AZ 要能承擔尖峰 ÷（AZ 數 − 1）：2 AZ 多備 100%、3 AZ 多備 50% | 設計公式 | 「AZ 故障時不能等擴展」→ 預先多備容量 | 第 18 章 18.16；第 34 章 34.4 |

## B.4 VPC、Subnet 與 IP 位址

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| VPC IPv4 CIDR 大小 | /16（65,536 個）到 /28（16 個） | hard limit | 每段 CIDR 最大 /16；要更多位址就加 secondary CIDR | 第 3 章 3.4；第 5 章 5.3 |
| 每個 VPC 的 IPv4 CIDR 數（含主要 CIDR） | 預設 5 個，最多 50 | 預設 quota，可申請提高 | 主要 CIDR 不能修改，只能追加 | 第 5 章 5.3 |
| Subnet 大小 | /16 到 /28 | hard limit | Subnet 建立後 CIDR 不能修改 | 第 5 章 5.4 |
| 每個 subnet 保留位址 | 5 個（第 0、1、2、3 個與最後一個） | hard limit | /24 可用 251 個，/28 只有 11 個 | 第 5 章 5.4 |
| 可用位址速查 | /28=11、/27=27、/26=59、/25=123、/24=251、/22=1,019、/20=4,091 | — | 算 subnet 大小時記得扣 5 | 第 5 章 5.4 |
| 一個 subnet 所在 AZ 數 | 1 | 設計行為 | — | 第 5 章 5.4 |
| Default VPC CIDR | 172.31.0.0/16 | — | — | 第 3 章 3.3；第 5 章 5.2 |
| RFC 1918 私有範圍 | 10.0.0.0/8、172.16.0.0/12、192.168.0.0/16 | — | 100.64.0.0/10 常用作額外 CIDR（例如 EKS Pod） | 第 3 章 3.3；第 5 章 5.3 |
| IPv6 | VPC /56、subnet 通常 /64 | — | — | 第 3 章 3.7；第 5 章 5.8 |
| Amazon DNS（Route 53 Resolver）位址 | VPC CIDR 起始 +2，或 169.254.169.253 | — | — | 第 3 章 3.13；第 5 章 5.9 |
| Instance metadata 位址 | 169.254.169.254 | — | — | 第 3 章 3.3；第 17 章 17.6 |
| 每個 subnet 關聯的 route table | 同一時間 1 張（一張可服務多個 subnet） | hard limit | — | 第 5 章 5.5 |
| 同一 route table 相同 destination | 只能 1 條 | hard limit | 不能有兩條 `0.0.0.0/0` | 第 5 章 練習 5-4 |
| 每個 VPC 的 Internet Gateway | 最多 1 個 | hard limit | IGW 沒有頻寬上限、本身不收費 | 第 5 章 5.6 |
| NAT Gateway 頻寬 | 5 Gbps 起，自動擴展到 100 Gbps | 自動，不需設定 | — | 第 5 章 5.7 |
| NAT Gateway 同時連線 | 每個唯一目的地（IP + port + 協定）約 55,000 條 | 可加 secondary IP 或更多 NAT Gateway | 「連到同一目的地的連線錯誤」→ 加 IP | 第 5 章 5.7 |
| NAT Gateway 範圍 | zonal；每個 AZ 一台，該 AZ 的 private subnet 走自己的 NAT | 設計行為 | 考題仍以「zonal、每 AZ 一台」為標準答案，見 B.40 | 第 5 章 5.7 |

## B.5 Security Group、NACL、VPC Endpoint 與 Flow Logs

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 SG 的規則數 | 入站、出站各 60 條 | 預設 quota，可申請提高 | 考試很少考精確數字 | 第 6 章 6.3 |
| 每個 ENI 的 SG 數 | 5 個 | 預設 quota，可申請提高 | — | 第 6 章 6.3 |
| SG 數 × 規則數 | 總上限 1,000 條 | hard limit | 兩個 quota 互相牽制 | 第 6 章 6.3 |
| 每個 NACL 的規則數 | 每個方向 20 條 | 預設 quota，可申請提高 | 規則依編號由小到大評估，建議間隔 10 或 100 | 第 6 章 6.4 |
| 每個 subnet 關聯的 NACL | 同一時間 1 個 | hard limit | — | 第 6 章 6.4 |
| Ephemeral port | Linux 32768–60999、Windows 49152–65535；NACL 回程建議放行 1024–65535 | — | NACL 是 stateless，回程流量要另外放行 | 第 3 章 3.8；第 6 章 6.4 |
| Gateway endpoint 支援服務 | 只有 S3 與 DynamoDB（同 Region） | 設計行為 | gateway endpoint 免費；省 NAT 處理費的標準答案 | 第 6 章 6.6–6.7 |
| Interface endpoint 計費 | 每個 AZ 每小時 + 每 GB | — | 大量 VPC 時集中 endpoint 省錢 | 第 6 章 6.8；第 41 章 41.6 |
| Flow Logs 聚合時間 | 預設 10 分鐘，可設 1 分鐘；Nitro instance 一律 1 分鐘以內 | 可設定 | Flow Logs 建立後不能修改設定 | 第 6 章 6.10 |
| Flow Logs 目的地 | 3 種：CloudWatch Logs、S3、Firehose | — | — | 第 6 章 6.10 |
| 協定編號 | 6 = TCP、17 = UDP、1 = ICMP | — | — | 第 6 章 6.10 |

## B.6 VPC Peering 與 Transit Gateway

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 VPC 的 active peering | 預設 50，最多 125 | 預設 quota，可申請提高 | 不支援遞移路由 | 第 7 章 7.3 |
| 兩個 VPC 之間的 peering | 只能 1 條 | hard limit | — | 第 7 章 7.3 |
| Peering 請求過期 | 7 天未接受即過期 | 設計行為 | — | 第 7 章 7.3 |
| Full mesh 連線數 | n(n−1)/2（20 個 VPC = 190 條、60 個 = 1,770 條） | — | VPC 多時改用 Transit Gateway | 第 7 章 7.3；第 41 章 41.2 |
| CIDR 重疊 | 任何一段（含 secondary）重疊就不能 peering | hard limit | 重疊時考慮 PrivateLink 或 Private NAT | 第 7 章 7.3 |
| Peering 費用 | 無小時費；同 AZ 流量免費，跨 AZ 依跨 AZ 費率 | — | 大流量 VPC 對保留 peering 可省 TGW 處理費 | 第 7 章 7.3；第 39 章 39.3 |
| TGW attachment 關聯的 route table | 每個 attachment 只能 1 張（propagation 可多張） | hard limit | — | 第 7 章 7.4 |
| TGW VPC attachment 頻寬 | 每 AZ 每方向最高約 100 Gbps | 不能自助申請提高；更高需求需聯絡 SA／TAM | — | 第 7 章 7.4 |
| TGW peering 路由 | 只能 static route | hard limit | — | 第 7 章 7.4 |
| TGW subnet | 建議專用的小 subnet（例如 /28） | 建議 | — | 第 7 章 7.4 |
| TGW 引用 SG | 2024 年起支援，只能用在入站規則，不跨 TGW peering | 設計行為 | — | 第 6 章 6.3；第 7 章 7.4 |

## B.7 Site-to-Site VPN、Direct Connect 與 Resolver

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每條 VPN connection 的 tunnel | 固定 2 條，在不同 AZ | hard limit | 雙裝置 × 雙 connection = 4 條 tunnel | 第 8 章 8.3 |
| 每條 tunnel 頻寬 | 約 1.25 Gbps；large bandwidth tunnel 約 5 Gbps（僅 TGW／Cloud WAN） | hard limit | 考題用 1.25 Gbps；超過要用 TGW + ECMP，見 B.40 | 第 7 章 7.4；第 8 章 8.3 |
| ECMP | 只有 TGW + BGP 支援；VGW 與 static VPN 不支援 | 設計行為 | 「VPN 卡在約 1.2 Gbps」→ TGW + 多條 tunnel + ECMP | 第 8 章 8.3 |
| Accelerated VPN | 只能搭配 TGW，只能在建立時啟用 | hard limit | — | 第 8 章 8.3 |
| VPN 建置時間 | 數小時到數天 | — | 「下週就要連線」→ VPN；DX 太慢 | 第 8 章 8.3、8.12 |
| BGP private ASN | 64512–65534；AWS 端預設 64512 | 可設定 | — | 第 8 章 8.2 |
| Client VPN client CIDR | /12 到 /22，建立後不能修改 | hard limit | — | 第 8 章 8.4 |
| DX dedicated 速度 | 1、10、100 Gbps（部分地點 400 Gbps） | — | — | 第 8 章 8.5 |
| DX hosted 速度 | 50 Mbps 起，依夥伴到 10 Gbps 以上 | — | 需求小於 1 Gbps 時常用 hosted | 第 8 章 8.5 |
| 每個 hosted connection 的 VIF | 只有 1 個 | hard limit | 要多個 VIF 就要多條 hosted connection 或 dedicated | 第 8 章 8.5 |
| 每條 dedicated connection 的 private／public VIF | 50 個 | 不能提高 | 與 transit VIF 合計最多 51 個 | 第 8 章 8.14 |
| 每條 dedicated connection 的 transit VIF | 4 個 | 不能自助申請；需聯絡 SA／TAM | 大型環境用少數 transit VIF 接 DXGW | 第 8 章 8.14 |
| DXGW 與 TGW 關聯數 | 每個 TGW 最多 20 個 DXGW；每個 DXGW 最多 6 個 TGW | 不能提高 | — | 第 8 章 8.14 |
| DX 建置時間 | 數週到數個月 | — | 時程緊時先用 VPN，DX 完成後切換 | 第 8 章 8.5、8.14 |
| MTU | Private VIF 最大 9001；Transit VIF 最大 8500 | hard limit | — | 第 8 章 8.6 |
| DX Gateway 可達範圍 | 任何 Region（中國除外） | 設計行為 | — | 第 8 章 8.7 |
| DX 韌性模型 | Maximum：2 個 location × 各 2 條；High：2 × 1；Dev/Test：1 × 2 | — | 「最高韌性」→ 兩個 location 各兩條 | 第 8 章 8.9 |
| BFD 偵測 | 約 1 秒（BGP keepalive 要數十秒） | AWS 端預設啟用 | — | 第 8 章 8.9 |
| BGP local preference community | 7224:7300 高／7224:7200 中／7224:7100 低 | 可設定 | — | 第 8 章 8.9 |
| Public VIF 範圍 community | 7224:9100 本 Region／9200 同洲／9300 全球（預設） | 可設定 | — | 第 8 章 8.9 |
| Resolver endpoint IP | 每個 endpoint 至少 2 個 IP（不同 AZ）；每個 IP 約每秒 10,000 次查詢 | 加 IP 擴展 | 安全規則要開 UDP 與 TCP 53 | 第 8 章 8.10 |
| 傳輸時間估算 | 10 TB 走 1 Gbps、利用率 80% 約 28 小時；100 TB 超過 11 天 | 公式 | 先算線上傳輸要幾天，再決定是否離線傳輸 | 第 8 章 8.14；第 25 章 25.2 |

## B.8 Route 53

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 hosted zone 的 name server | 4 台 | 設計行為 | — | 第 9 章 9.3 |
| Alias record TTL | 不能自訂，由目標決定（指向 ELB 時為 60 秒） | 設計行為 | 指向 AWS 資源的 alias 查詢免費；zone apex 只能用 alias | 第 9 章 9.4 |
| TLD 的 NS 快取 | 可能長達 1–2 天 | AWS 無法控制 | 遷移 DNS 前先調低 NS TTL | 第 9 章 9.5 |
| Routing policy 種類 | 8 種 | — | — | 第 9 章 9.6 |
| Weighted 權重 | 0–255；權重 0 不回答（全部為 0 時平均分配） | 可設定 | — | 第 9 章 9.6 |
| Geoproximity bias | −99 到 +99 | 可設定 | — | 第 9 章 9.6 |
| Multivalue answer | 每次最多回答 8 筆健康記錄 | hard limit | 不能取代 load balancer | 第 9 章 9.6 |
| Health check 間隔 | 標準 30 秒或快速 10 秒 | 可設定（二選一） | — | 第 9 章 9.7 |
| Failure threshold | 預設 3 次 | 可設定 | 切換時間 ≈ 間隔 × threshold + TTL + 用戶端行為 | 第 9 章 9.7、9.13 |
| 判定健康 | 超過約 18% 的 checker 回報健康；HTTP 要 2xx 或 3xx | 設計行為 | — | 第 9 章 9.7 |
| Health check 指標、query logging、DNSSEC KSK | 都在 us-east-1（KSK 需非對稱 `ECC_NIST_P256` KMS key） | hard limit | — | 第 9 章 9.7、9.10、9.13 |
| ARC routing control cluster | 跨 5 個 Region | 設計行為 | 不依賴 DNS control plane 的切換開關 | 第 9 章 9.13；第 34 章 34.10 |
| Failover record TTL | 通常設 60 秒或更短 | 可設定 | — | 第 34 章 34.10 |

## B.9 Elastic Load Balancing

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Deregistration delay | 預設 300 秒，可設 0–3,600 秒 | 可設定 | 短請求 API 可調小以加快縮減 | 第 10 章 10.3；第 18 章 18.12 |
| ALB 最少 AZ | 2 個 | hard limit | NLB 可以只放 1 個 AZ | 第 10 章 10.4、10.5 |
| ALB subnet 大小 | 建議至少 /27 | 建議 | — | 第 10 章 10.4 |
| ALB idle timeout | 預設 60 秒 | 可設定 | 長連線或上傳逾時要調高 | 第 10 章 10.4 |
| ALB → Lambda | 每個 target group 只能 1 個函式；請求 body 與回應 JSON 各最大 1 MB | hard limit | 大於 1 MB 的回應改用 S3 presigned URL | 第 10 章 10.4 |
| NLB 固定 IP | 每個啟用的 AZ 1 個（可指定 EIP） | 設計行為 | 「客戶防火牆要白名單固定 IP」→ NLB 或 Global Accelerator | 第 10 章 10.5 |
| NLB security group | 只能在建立時附加，之後不能再加 | hard limit | — | 第 10 章 10.5 |
| Cross-zone load balancing | ALB 預設開啟、不收跨 AZ 費；NLB／GWLB 預設關閉，開啟後收跨 AZ 費 | 可設定 | — | 第 10 章 10.6 |
| GWLB | GENEVE，UDP 6081 | 設計行為 | — | 第 10 章 10.7 |
| ELB 計費 | 小時費 + LCU（新連線、活躍連線、流量、規則評估四項取最高） | — | — | 第 10 章 10.8 |

## B.10 CloudFront、邊緣函式與 Global Accelerator

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| ACM 憑證 Region | CloudFront 使用的憑證必須在 us-east-1 | hard limit | 高頻考點 | 第 3 章 3.9；第 11 章 11.7；第 15 章 15.13 |
| Invalidation 免費額度 | 每月前 1,000 個路徑；萬用字元路徑算 1 個 | 計費規則 | 頻繁發版改用版本化檔名 | 第 11 章 11.4 |
| Minimum TTL | 大於 0 時，即使 origin 回 no-store 也會快取到 minimum TTL | 可設定 | — | 第 11 章 11.4 |
| Field-level encryption | 最多 10 個欄位 | hard limit | — | 第 11 章 11.5 |
| Geo restriction | 被拒請求回 HTTP 403 | — | — | 第 11 章 11.5 |
| CloudFront Functions | 記憶體 2 MB、執行時間毫秒以下；只能用在 viewer 觸發 | hard limit | 簡單 header／URL 改寫選它，最便宜 | 第 11 章 11.8 |
| Lambda@Edge timeout | 最長 30 秒 | hard limit | 舊資料寫 viewer 觸發 5 秒，見 B.40 | 第 11 章 11.8 |
| Lambda@Edge 記憶體 | viewer 觸發 128 MB；origin 觸發最高 10 GB | hard limit | — | 第 11 章 11.8 |
| Lambda@Edge 產生的回應大小 | viewer 觸發 40 KB；origin 觸發 1 MB | hard limit | — | 第 11 章 11.8 |
| Lambda@Edge 建立 Region | us-east-1，使用已發布版本 | hard limit | — | 第 11 章 11.8 |
| Origin failover 狀態碼 | 可選 400、403、404、416、429、500、502、503、504；勾選 503／504 時連不上與逾時也觸發 | 可設定 | 只對 GET、HEAD、OPTIONS 生效 | 第 11 章 11.9 |
| Origin 連線嘗試 | 預設 3 次 × 每次 10 秒（約 30 秒）；可調 1–3 次、1–10 秒 | 可設定 | 要更快切換就調低 | 第 11 章 11.9 |
| WAF for CloudFront | global scope，在 us-east-1 管理 | hard limit | — | 第 11 章 11.13；第 16 章 16.3 |
| Global Accelerator 固定 IP | 2 個 anycast IPv4 | 設計行為 | 「固定 IP + 全球加速 + TCP／UDP」→ GA | 第 11 章 11.10 |
| GA traffic dial | 每個 endpoint group 0–100% | 可設定 | 藍綠或 Region 切換逐步調整 | 第 11 章 11.10 |
| GA endpoint weight | 0–255 | 可設定 | — | 第 11 章 11.10 |

## B.11 IAM、STS、Identity Center 與 Cognito

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 IAM user 的 access key | 最多 2 組 | hard limit | 2 組是為了輪替 | 第 12 章 12.3 |
| Customer managed policy 版本 | 最多保留 5 個 | hard limit | — | 第 12 章 12.5 |
| Customer managed policy 大小 | 6,144 字元（不含空白） | hard limit | — | 第 12 章 12.5 |
| 每個 user／role 的 managed policy | 預設 10 個 | 預設 quota，可申請提高 | — | 第 12 章 12.5 |
| Credential report | 最多每 4 小時產生一份新報表 | 設計行為 | — | 第 12 章 12.10 |
| IAM Access Analyzer 外部存取 | 免費、Regional | — | 每個 Region 都要啟用 | 第 12 章 12.10 |
| AssumeRole session | 預設 1 小時；`DurationSeconds` 最短 15 分鐘 | 可設定 | — | 第 13 章 13.2 |
| Role maximum session duration | 1–12 小時 | 可設定 | — | 第 13 章 13.2 |
| Role chaining | session 最長 1 小時 | hard limit | 調高目標 role 的 maximum 也沒用 | 第 13 章 13.2、13.12 |
| 臨時 key 前綴 | `ASIA`（臨時）、`AKIA`（長期） | — | — | 第 13 章 13.2 |
| Identity Center permission set session | 預設 1 小時，最長 12 小時 | 可設定 | 撤銷存取時 Deny 至少要保留到 session 過期 | 第 13 章 13.7、13.12 |
| Identity Center identity source | 同一時間只能 1 種 | 設計行為 | — | 第 13 章 13.7 |
| Cognito ID／access token | 預設 1 小時 | 可設定 | — | 第 13 章 13.9 |
| Managed Microsoft AD | 網域控制站部署在 2 個 AZ；Enterprise 版支援多 Region 複寫 | 設計行為 | — | 第 13 章 13.8 |

## B.12 Organizations、SCP 與 Landing Zone

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| OU 巢狀深度 | root 之下最多 5 層 | hard limit | — | 第 14 章 14.3 |
| Management account | 每個 organization 只有 1 個，不能更換 | hard limit | SCP 不影響 management account | 第 14 章 14.3 |
| 帳號所屬 organization | 同一時間只能 1 個；每個帳號或 OU 只有 1 個 parent | hard limit | — | 第 14 章 14.3 |
| 每個節點的 SCP | root、OU 或帳號各最多 5 個 | hard limit | Control Tower 也會占用 SCP 名額 | 第 14 章 14.5、14.15 |
| SCP 文件大小 | 5,120 字元 | hard limit | 規則多時合併 statement | 第 14 章 14.5 |
| RCP 推出時支援的服務 | 2024 年底推出，最初支援 S3、STS、KMS、SQS、Secrets Manager | — | RCP 管資源端、SCP 管身份端 | 第 14 章 14.8 |
| 帳號關閉後的 post-closure 期間 | 約 90 天，期間可聯繫 Support 救回 | 設計行為 | — | 第 40 章 40.4 |
| Cost allocation tag | 新 tag key 最多約 24 小時出現；backfill 最多回溯 12 個月 | — | 要在 management（payer）帳號啟用 | 第 39 章 39.9；第 40 章 40.10 |

## B.13 KMS、CloudHSM、Secrets Manager、Parameter Store 與 ACM

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| KMS `Encrypt` 資料大小 | 一次最多 4 KB | hard limit | 大資料用 envelope encryption（data key） | 第 15 章 15.4 |
| KMS 對稱金鑰 | 256-bit | 設計行為 | — | 第 15 章 15.3 |
| Customer managed key 自動輪替 | 預設每 365 天，可設 90–2,560 天 | 可設定 | 只對前 2 次輪替加收費用 | 第 15 章 15.7 |
| AWS managed key 輪替 | 每年，不能關閉或調整 | 設計行為 | 舊資料寫「每 3 年」，見 B.40 | 第 15 章 15.3、15.7 |
| Key 刪除等待期 | 7–30 天（預設 30） | 可設定（範圍內） | 不能立即刪除；誤刪風險用 disable 代替 | 第 15 章 15.7 |
| KMS 請求速率 | 每帳號每 Region 有配額，依 Region 不同 | 預設 quota，可申請提高 | 以帳號 + Region 計算，不是每把 key 各一份；S3 Bucket Key 最多可降 99% 請求 | 第 15 章 15.10 |
| Multi-Region key ID | 以 `mrk-` 開頭 | — | — | 第 15 章 15.8 |
| CloudHSM 高可用 | 至少 2 個 HSM，分散在不同 AZ | 建議 | — | 第 15 章 15.9 |
| Secrets Manager 輪替 | 4 個步驟（createSecret、setSecret、testSecret、finishSecret） | — | 「自動輪替 DB 密碼」→ Secrets Manager | 第 15 章 15.11 |
| Parameter Store 參數數 | Standard 10,000／Advanced 100,000（每帳號每 Region） | hard limit（換 tier 才能提高） | — | 第 15 章 15.12；第 38 章 38.5 |
| Parameter Store 參數大小 | Standard 4 KB／Advanced 8 KB | hard limit | Standard 可升 Advanced，不能降回 | 第 15 章 15.12 |
| ACM 到期事件 | 預設到期前 45 天開始送出 EventBridge 事件 | 可調整天數 | — | 第 15 章 15.13 |
| S3 SSE-S3 預設加密 | 自 2023-01 起所有新物件 | 設計行為 | 不能關閉 | 第 15 章 15.10；第 22 章 22.7 |
| S3 SSE-C | 自 2026-04 起新 bucket 預設封鎖 | 可在 bucket 預設加密設定解除 | 較新的變更，舊題不會反映 | 第 15 章 15.10 |

## B.14 邊界防護、稽核與合規

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| WAF rate-based rule 時間窗 | 預設 5 分鐘，可設 1、2 或 10 分鐘 | 可設定 | 「單一 IP 短時間大量請求」→ rate-based rule | 第 16 章 16.3 |
| WAF body 檢查大小 | ALB、AppSync 固定前 8 KB；CloudFront、API Gateway 預設 16 KB，可提高到 64 KB（另收費） | 部分可設定 | — | 第 16 章 16.3 |
| WAF log group 名稱 | 必須以 `aws-waf-logs-` 開頭 | hard limit | — | 第 16 章 16.3 |
| Shield Advanced | 一年承諾、按月計費；SRT 24 小時支援需 Business 以上支援方案 | — | 保護 CloudFront、Route 53、GA、ALB、CLB、EIP | 第 16 章 16.4 |
| GuardDuty 試用 | 新帳號 30 天免費 | — | 基礎資料來源：CloudTrail、VPC Flow Logs、DNS logs | 第 16 章 16.7 |
| CloudTrail Event history | 免費保留 90 天 management events | hard limit | 要保留更久就建 trail 送 S3 | 第 16 章 16.10；第 36 章 36.11 |
| CloudTrail digest file | 每小時一份，SHA-256 | 設計行為 | 「證明日誌未被竄改」→ log file validation | 第 16 章 16.10 |
| CloudTrail 送達延遲 | 通常數分鐘 | 設計行為 | 不是即時；即時偵測用 EventBridge | 第 16 章 16.10；第 36 章 36.11 |
| Config rule 週期 | periodic：每 1、3、6、12、24 小時 | 可設定 | 另有 configuration change 觸發 | 第 38 章 38.8 |
| Glacier Vault Lock 測試期 | 啟動後 24 小時（InProgress） | hard limit | 舊的 vault 型 Glacier 不再接受新客戶 | 第 16 章 16.13 |
| AWS Backup Vault Lock compliance mode | grace time 最少 72 小時，之後連 root 也不能改 | hard limit | — | 第 34 章 34.8 |

## B.15 EC2

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每 vCPU 記憶體 | C 約 2 GiB、M 約 4 GiB、R 約 8 GiB | 設計行為 | — | 第 17 章 17.3 |
| Graviton2 價格效能 | 最高好 40% | — | — | 第 17 章 17.3 |
| CPU credit | 1 credit = 1 vCPU 以 100% 跑 1 分鐘；T2 預設 Standard，T3／T3a／T4g 預設 Unlimited | 可設定 | — | 第 17 章 17.4 |
| User data 大小 | 16 KB（base64 前） | hard limit | 預設只在第一次開機執行 | 第 17 章 17.6 |
| IMDSv2 token 有效期 | 最長 6 小時 | hard limit | — | 第 17 章 17.6 |
| IMDS hop limit | 預設 1；container 內要設 2 | 可設定 | 「container 拿不到 metadata token」→ hop limit 2 | 第 17 章 17.6 |
| Hibernation | Linux 記憶體小於 150 GiB、Windows 最多 16 GiB；單次最長 60 天；必須在啟動時啟用 | hard limit | — | 第 17 章 17.7 |
| 單一 flow 頻寬 | placement group 外 5 Gbps；cluster placement group 內 10 Gbps；ENA Express 25 Gbps（同 AZ） | hard limit | — | 第 17 章 17.8 |
| 經 IGW 的頻寬 | 32 vCPU 以下約 5 Gbps | hard limit | — | 第 17 章 17.8 |
| Elastic IP | 每 Region 5 個 | 預設 quota，可申請提高 | — | 第 17 章 17.8 |
| Spread placement group | 每 AZ 每 group 最多 7 台運行中的 instance | hard limit | 高頻考點 | 第 17 章 17.9；第 34 章 34.2 |
| Partition placement group | 每 AZ 最多 7 個 partition | hard limit | 適合 HDFS、Cassandra、Kafka | 第 17 章 17.9 |
| On-Demand 計費 | 按秒計費，最低 60 秒 | — | — | 第 17 章 17.11 |
| On-Demand／Spot vCPU 配額 | 每 Region | 預設 quota，可申請提高 | — | 第 17 章 17.11 |
| Spot 中斷通知 | 2 分鐘（另可能提前發出 rebalance recommendation） | hard limit | 只適合可中斷、可重試的工作 | 第 17 章 17.11；第 39 章 39.5 |
| Spot 最高折扣 | 約 90% | — | — | 第 17 章 17.11；第 39 章 39.5 |
| Spot blocks（保證 1–6 小時不中斷） | 已停止提供 | — | 「不中斷的 Spot」永遠不是正確答案 | 第 17 章 17.11 |
| Instance store | stop、hibernate、terminate、主機故障時資料遺失；reboot 保留 | 設計行為 | — | 第 24 章 24.7 |

## B.16 EC2 Auto Scaling

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Health check grace period | console 建立預設 300 秒；CLI／SDK 預設 0 | 可設定 | 太短會在開機途中被判定不健康 | 第 18 章 18.5 |
| Simple scaling cooldown | 預設 300 秒 | 可設定 | target tracking／step 改用 instance warmup | 第 18 章 18.6、18.7 |
| Predictive scaling | 至少需要 24 小時資料；預測未來 2 天 | — | 「每天固定尖峰、要提前擴展」→ predictive | 第 18 章 18.6 |
| Lifecycle hook heartbeat timeout | 預設 3,600 秒，最長 7,200 秒 | 可設定 | 用 heartbeat 延長，整體最長 48 小時 | 第 18 章 18.8 |
| Warm pool | 不支援 Spot 與 instance weighting | hard limit | 舊題寫「不能搭配 mixed instances policy」 | 第 18 章 18.8 |
| AZRebalance 暫時超量 | 最多超過 max 的 10% 或 1 台（取較大者） | 設計行為 | — | 第 18 章 18.4 |
| Instance refresh | minimum healthy 預設 90%；maximum healthy 100–200%（預設 100%） | 可設定 | 零停機：min 100%、max 110% 以上 | 第 18 章 18.10 |
| Launch configuration | 2023-01-01 後推出的 instance type 不支援；2024-10-01 後建立的帳號完全不能建立 | — | 新設計一律用 launch template | 第 18 章 18.3 |

## B.17 Lambda

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 最長執行時間 | 900 秒（15 分鐘），預設 3 秒 | hard limit（可設定到 15 分鐘） | 超過 15 分鐘 → ECS／Fargate、Batch、Step Functions 拆步 | 第 19 章 19.4；第 35 章 35.6；第 46 章 46.7 |
| 記憶體 | 128–10,240 MB，以 1 MB 為單位 | hard limit（範圍內可設定） | CPU 依記憶體比例分配；約 1,769 MB = 1 vCPU，最高 6 vCPU | 第 19 章 19.4 |
| `/tmp` | 512–10,240 MB（預設 512 MB） | 可設定 | 超過 512 MB 的部分另外計費 | 第 19 章 19.4 |
| 同步 payload | 請求與回應各 6 MB | hard limit | — | 第 19 章 19.4；第 20 章 20.11 |
| 非同步 event 大小 | 1 MB | hard limit | 舊值 256 KB，見 B.40 | 第 19 章 19.4 |
| 環境變數 | 總共 4 KB | hard limit | 大量設定放 Parameter Store | 第 19 章 19.4 |
| Zip 部署套件 | 直接上傳 50 MB（壓縮後）；解壓後含 layers 共 250 MB | hard limit | 大型相依套件 → container image | 第 19 章 19.4、19.11 |
| Container image | 最大 10 GB（存放在 ECR） | hard limit | — | 第 19 章 19.4 |
| Layers | 每個函式最多 5 個 | hard limit | 計入 250 MB | 第 19 章 19.4 |
| 帳號 concurrency | 每 Region 預設 1,000（新帳號可能更低），所有函式共用 | 預設 quota，可申請提高 | — | 第 19 章 19.4、19.8；第 35 章 35.6 |
| 擴展速率 | 每個函式每 10 秒最多新增 1,000 個執行環境 | 設計行為 | 舊教材的 burst 模型，見 B.40 | 第 19 章 19.8 |
| 最少未保留 concurrency | 100 | hard limit | reserved concurrency 設 0 = 暫停函式 | 第 19 章 19.8 |
| Init 階段 | 一般 on-demand 函式約 10 秒限制 | hard limit | — | 第 19 章 19.3 |
| 非同步重試 | 預設 2 次（可設 0–2）；maximum event age 60 秒到 6 小時 | 可設定 | 失敗事件送 on-failure destination 或 DLQ | 第 19 章 19.5 |
| SQS event source batch | Standard 最多 10,000（超過 10 要設 batching window）；FIFO 最多 10 | 可設定 | Queue 的 visibility timeout 至少設成函式 timeout 的 6 倍 | 第 19 章 19.7；第 32 章 32.6 |
| Kinesis／DynamoDB Streams parallelization factor | 每個 shard 1–10 | 可設定 | — | 第 19 章 19.7；第 31 章 31.4 |
| 遞迴迴圈偵測 | 連鎖呼叫約 16 次後擋下 | 設計行為 | — | 第 19 章 19.17 |
| 免費額度 | 每月 100 萬次請求、40 萬 GB-秒 | — | — | 第 19 章 19.14 |
| Savings Plans | 只有 Compute Savings Plans 適用 Lambda | — | — | 第 19 章 19.14 |

## B.18 API Gateway

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| REST API 整合逾時 | 預設最長 29 秒 | Regional／private 可申請提高（可能要降低帳號 throttle quota）；edge-optimized 維持 29 秒 | 考題常用 29 秒；長工作改非同步 | 第 20 章 20.3、20.11；第 33 章 33.2 |
| HTTP API 整合逾時 | 30 秒 | hard limit | — | 第 20 章 20.3、20.11 |
| WebSocket 整合逾時 | 29 秒 | — | — | 第 20 章 20.3 |
| Payload | 10 MB | hard limit | 上傳大檔 → S3 presigned URL | 第 20 章 20.11 |
| 帳號 throttle | 每 Region 約每秒 10,000 請求、burst 5,000 | 預設 quota，可申請提高 | 超過回 429 | 第 20 章 20.8；第 35 章 35.6 |
| Usage plan | throttle 與 quota（每天／週／月）是 best-effort | 可設定 | 不能當精確計費依據 | 第 20 章 20.8 |
| API cache | 0.5 GB–237 GB，按小時計費；TTL 預設 300 秒、0–3,600 秒 | 可設定 | — | 第 20 章 20.9 |
| Lambda authorizer 快取 | 預設 300 秒、最長 3,600 秒 | 可設定 | — | 第 20 章 20.7 |
| WebSocket 連線 | 閒置約 10 分鐘關閉；單一連線最長 2 小時 | hard limit | — | 第 20 章 20.13 |
| Response streaming | 最長 15 分鐘，可超過 10 MB；閒置逾時 regional／private 5 分鐘、edge-optimized 30 秒 | — | 較新的功能 | 第 20 章 20.11 |
| 自訂網域憑證 | edge-optimized 用 us-east-1；regional 用 API 所在 Region | hard limit | — | 第 20 章 20.4 |

## B.19 Containers 與 Batch

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Fargate 單一 task | 最大 16 vCPU、120 GB 記憶體 | hard limit | 更大或要 GPU → EC2 launch type | 第 21 章 21.6 |
| Fargate ephemeral storage | 預設 20 GB，可設到 200 GB | 可設定 | — | 第 21 章 21.6 |
| Fargate 計費 | 按秒計費（有最低計費時間） | — | — | 第 21 章 21.6 |
| Fargate Spot 中斷 | 收到 SIGTERM 後約 2 分鐘收尾 | 設計行為 | — | 第 21 章 21.6 |
| ECS task definition 單位 | `cpu: 1024` = 1 vCPU；`memory: 4096` = 4 GB | — | — | 第 21 章 21.4 |
| ECS rolling 部署 | minimumHealthyPercent 100%、maximumPercent 200%：先啟新 task，容量不下降 | 可設定 | — | 第 21 章 21.8；第 37 章 37.9 |
| EKS VPC CNI prefix delegation | 每個 ENI 分配 /28 前綴 | 可設定 | Pod IP 不夠 → prefix delegation 或 100.64.0.0/10 secondary CIDR | 第 21 章 21.9 |
| AWS Batch array job | 最多 10,000 個 child job | hard limit | minvCpus 可為 0 | 第 21 章 21.12 |

## B.20 S3 基礎

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 單一物件大小 | 考題用 5 TB；現行約 50 TB（48.8 TiB） | hard limit | 見 B.40 | 第 22 章 22.4；第 35 章 35.6 |
| 單一 PUT | 5 GB | hard limit（API 限制，不能申請提高） | 超過 5 GB 必須用 multipart；超過 100 MB 建議用 | 第 22 章 22.4；第 25 章 25.10 |
| Multipart part | part number 1–10,000；每個 part 5 MB–5 GB（最後一個可較小） | hard limit | — | 第 22 章 22.4 |
| Bucket 名稱 | 3–63 字元，partition 內唯一；小寫、數字、`.`、`-` | hard limit | 用 Transfer Acceleration 時名稱不能含 `.` | 第 22 章 22.2、22.12 |
| Object key | 最長 1,024 bytes | hard limit | — | 第 22 章 22.2 |
| Object tag | 每個物件最多 10 個 | hard limit | — | 第 22 章 22.2 |
| 耐久度／可用度（Standard） | 11 個 9；99.99%；至少 3 個 AZ | 設計值 | — | 第 4 章 4.8；第 22 章 22.2 |
| 一致性 | 自 2020-12 起 strong read-after-write（PUT、DELETE、LIST） | 設計行為 | 「寫入後立刻讀不到」不再是 S3 的問題 | 第 4 章 4.6；第 22 章 22.3 |
| 請求速率 | 每個 partitioned prefix 每秒至少 3,500 PUT／COPY／POST／DELETE、5,500 GET／HEAD；prefix 數不限 | 自動擴展（擴展期間可能 503 Slow Down） | 10 個 prefix 平行讀取約每秒 55,000 GET | 第 22 章 22.12；第 35 章 35.6 |
| Bucket policy 大小 | 20 KB | hard limit | 大量帳號改用 access points 或 `aws:PrincipalOrgID` | 第 22 章 22.6、22.9 |
| Presigned URL 效期 | SigV4 最長 7 天；console 產生最長 12 小時；臨時 credentials 過期時提早失效 | hard limit | — | 第 22 章 22.8 |
| 新 bucket 預設 | Block Public Access、ACL disabled（2023-04 起 Bucket owner enforced）、SSE-S3 | 設計行為 | — | 第 22 章 22.6、22.7 |
| BPA 視為公開的 IP 範圍 | 比 IPv4 /8 更大的範圍 | 設計行為 | — | 第 22 章 22.7 |
| 啟用 versioning 後 | 建議等約 15 分鐘再大量寫入 | 建議 | — | 第 22 章 22.3 |
| Event notification 目的地 | SQS standard（不支援 FIFO）、SNS、Lambda；EventBridge 可到 20 多種目標 | 設計行為 | — | 第 22 章 22.11 |

## B.21 S3 儲存類別、Glacier、Lifecycle 與複寫

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Standard-IA | 最短存放 30 天、最小計費 128 KB、可用度 99.9%、≥ 3 AZ | 設計行為 | 約每月讀一次 | 第 23 章 23.3 |
| One Zone-IA | 最短 30 天、128 KB、可用度 99.5%、單一 AZ；約為 Standard-IA 的八成 | 設計行為 | 只放可重建的資料 | 第 23 章 23.3 |
| Intelligent-Tiering | 30 天未存取移到 IA tier；90 天移到 Archive Instant；可選 90 天以上／180 天以上的 archive tier；小於 128 KB 不監控 | 部分可設定 | 存取模式不明確時選它；沒有取回費 | 第 23 章 23.3；第 39 章 39.7 |
| Glacier Instant Retrieval | 最短 90 天、128 KB、毫秒讀取 | 設計行為 | 約每季讀一次 | 第 23 章 23.3 |
| Glacier Flexible Retrieval | 最短 90 天；Expedited 1–5 分鐘（< 250 MB）、Standard 3–5 小時、Bulk 5–12 小時（免取回費） | 設計行為 | — | 第 23 章 23.3、23.5 |
| Provisioned capacity | 每單位每 5 分鐘至少 3 次 Expedited，最多 300 MB/s | 可購買 | 「Expedited 一定要成功」→ provisioned capacity | 第 23 章 23.5 |
| Glacier Deep Archive | 最短 180 天；Standard 12 小時內、Bulk 48 小時內；沒有 Expedited | 設計行為 | 最便宜，但取回以小時計 | 第 23 章 23.3、23.5 |
| Glacier metadata 額外計費 | 每物件約 40 KB（32 KB 以 Glacier 價、8 KB 以 Standard 價） | — | 大量小物件不適合 Glacier | 第 23 章 23.3 |
| Express One Zone | 個位數毫秒、可用度 99.95%、單一 AZ（directory bucket） | 設計行為 | — | 第 23 章 23.3 |
| Restore 請求速率 | 每秒約 1,000 次 | 帳號配額 | 大量取回用 Batch Operations | 第 23 章 23.5 |
| Lifecycle 轉到 IA | 物件至少要在 Standard 待滿 30 天 | hard limit | — | 第 23 章 23.6 |
| Lifecycle 小物件 | 自 2024-09 起預設不轉換小於 128 KB 的物件 | 可用大小篩選明確納入 | — | 第 23 章 23.6；第 39 章 39.7 |
| Replication Time Control | 99.99% 的物件在 15 分鐘內完成（SLA） | 需付費啟用 | 「複寫時間要有 SLA」→ RTC | 第 23 章 23.7；第 34 章 34.7 |
| 沒有 RTC 的複寫 | 多數在 15 分鐘內，偶爾數小時，沒有保證 | — | — | 第 23 章 23.7 |
| Storage Lens 指標保留 | 免費 14 天；進階 15 個月 | — | — | 第 23 章 23.10 |

## B.22 EBS

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| AZ 範圍 | volume 綁定單一 AZ；snapshot 存在 S3（Regional） | 設計行為 | 跨 AZ 搬移 = snapshot → 在新 AZ restore | 第 24 章 24.3、24.5 |
| gp3 基準 | 3,000 IOPS、125 MiB/s，與容量無關 | 可另外加購 | 每 GB 比 gp2 便宜約 20%；可線上從 gp2 改 gp3 | 第 24 章 24.4；第 39 章 39.7 |
| gp3 上限 | 考題用 16 TiB、16,000 IOPS、1,000 MiB/s；2025 年起 64 TiB、80,000 IOPS、2,000 MiB/s | hard limit | 見 B.40 | 第 24 章 24.4 |
| gp2 | 每 GiB 3 IOPS（最低 100、最高 16,000）；小於 1 TiB 可 burst 到 3,000 | 隨容量決定 | 為了 IOPS 買大容量 → 改 gp3 | 第 24 章 24.4 |
| io2 Block Express | 最高 256,000 IOPS、4,000 MiB/s、64 TiB；耐久度 99.999% | hard limit | — | 第 24 章 24.4 |
| io1 | 最高 64,000 IOPS | hard limit | — | 第 24 章 24.4 |
| st1／sc1 | 最高 500／250 MiB/s；不能當開機磁碟 | hard limit | 大量循序讀寫 → st1；冷資料最便宜 → sc1 | 第 24 章 24.4 |
| gp2／gp3／st1／sc1 耐久度 | 年故障率 0.1%–0.2% | 設計值 | — | 第 24 章 24.4 |
| Elastic Volumes | 任意連續 24 小時內最多修改 4 次；只能放大不能縮小 | hard limit | 舊題寫「每次修改後等 6 小時」，見 B.40 | 第 24 章 24.3 |
| Multi-Attach | 只有 io1／io2；同一 AZ 最多 16 台 Nitro instance | hard limit | 應用程式要能處理並行寫入 | 第 24 章 24.7 |
| Snapshot archive tier | 儲存費約低 75%；最少 90 天；還原 24–72 小時 | 設計行為 | — | 第 24 章 24.5；第 39 章 39.7 |
| Recycle Bin | 保留 1 天到 1 年 | 可設定 | 「防止誤刪 snapshot」→ Recycle Bin | 第 24 章 24.5 |
| EBS 加密 | AES-256 | — | — | 第 24 章 24.6 |

## B.23 EFS 與 FSx

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| EFS 協定 | NFSv4.0、4.1；TCP 2049 | 設計行為 | Windows 共享檔案不是 EFS | 第 24 章 24.8 |
| Mount target | 每個 AZ 最多 1 個 | hard limit | — | 第 24 章 24.8 |
| Performance mode | 建立後不能修改 | hard limit | — | 第 24 章 24.8 |
| EFS IA／Archive 最小計費 | 128 KiB（lifecycle 不搬更小的檔案） | 設計行為 | — | 第 24 章 24.8 |
| EFS Archive | 最短存放 90 天；只支援使用 Elastic throughput 的 Regional 檔案系統 | 設計行為 | — | 第 24 章 24.8 |
| EFS Replication | 多數檔案系統 RPO 15 分鐘 | 設計行為 | — | 第 24 章 24.8 |
| EFS 靜態加密 | 只能在建立時啟用 | hard limit | — | 第 24 章 24.8 |
| FSx for Windows Multi-AZ | 2 個 AZ（preferred + standby） | 設計行為 | SMB、AD 整合 → FSx for Windows | 第 24 章 24.9 |
| FSx for Lustre | 每秒數百 GB、毫秒以下延遲；單一 AZ | 設計行為 | HPC／ML 訓練 + S3 整合 | 第 24 章 24.9 |
| FSx for OpenZFS | NFS v3、v4.0、v4.1、v4.2 | — | — | 第 24 章 24.9 |

## B.24 資料移轉與混合儲存

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 1 Gbps 理論傳輸量 | 125 MB/s，約每天 10.8 TB；實務抓 70%–80% | 公式 | 80% 時 1 Gbps 每天約 8.6 TB | 第 25 章 25.2 |
| Volume Gateway 單一 volume | cached 32 TiB；stored 16 TiB | hard limit | — | 第 25 章 25.5 |
| S3 File Gateway 協定 | NFS v3、v4.1；SMB | — | — | 第 25 章 25.4 |
| Tape Gateway 取回 | Flexible Retrieval 通常數小時；Deep Archive 12 小時內 | 設計行為 | — | 第 25 章 25.6 |
| DataSync 單一 task | 可吃滿約 10 Gbps 線路 | 可用 `BytesPerSecond` 限速 | agent 的 endpoint 類型選定後不能改 | 第 25 章 25.7 |
| Snowball Edge | 單台數十 TB 到約 200 TB；不再提供給新客戶 | — | 考題可能仍以它為答案，見 B.40 | 第 25 章 25.9 |
| Outposts | 2U 的 Outposts server、42U 的 Outposts rack | — | — | 第 25 章 25.9 |
| Transfer Family | Public endpoint 只支援 SFTP；FTP 只能用 internal VPC endpoint；AS2 後端只支援 S3 | hard limit | — | 第 25 章 25.8 |
| MGN 免費額度 | 每台來源伺服器 2,160 小時（約 90 天連續複寫） | — | staging area 的 EC2／EBS 仍照常計費 | 第 45 章 45.3 |
| 線上傳輸範例 | 38 TB 走約 600 Mbps 約 5.9 天 | 公式 | 先計算再決定線上或離線傳輸 | 第 45 章 45.9 |

## B.25 RDS 與 RDS Proxy

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 引擎 | 6 種：MySQL、MariaDB、PostgreSQL、Oracle、SQL Server、Db2 | — | RDS Custom 支援 Oracle、SQL Server | 第 26 章 26.2 |
| DB subnet group | 至少 2 個 AZ | hard limit | — | 第 26 章 26.2 |
| 儲存空間 | 只能加大、不能縮小 | hard limit | — | 第 26 章 26.2 |
| 停止 instance | 最長 7 天，之後自動啟動 | hard limit | 長期不用 → snapshot 後刪除 | 第 26 章 26.2；第 39 章 39.6 |
| Multi-AZ DB instance | 1 primary + 1 standby（standby 不能讀）；failover 通常 60–120 秒 | 設計行為 | 高可用不等於讀取擴展 | 第 4 章 4.7；第 26 章 26.3 |
| Multi-AZ DB cluster | 1 writer + 2 可讀 reader（3 AZ）；failover 通常 35 秒內；僅 MySQL、PostgreSQL | 設計行為 | — | 第 26 章 26.3；第 34 章 34.3 |
| Read replica 數 | MySQL、MariaDB、PostgreSQL 每個 source 最多 15 個（Oracle 可到 15，AWS 建議 5 個以內） | hard limit | 舊教材寫 5 個，見 B.40 | 第 26 章 26.4；第 35 章 35.3 |
| 建立 read replica 的前提 | source 要開啟 automated backups（retention > 0） | hard limit | — | 第 26 章 26.4 |
| Automated backup retention | 1–35 天；0 = 關閉 | 可設定（範圍內） | 超過 35 天 → manual snapshot 或 AWS Backup | 第 26 章 26.5 |
| PITR | transaction log 約每 5 分鐘上傳；最新可還原點通常在最近 5 分鐘內 | 設計行為 | — | 第 26 章 26.5 |
| 加密 | 只能在建立時啟用 | hard limit | 未加密 → 加密 snapshot copy → restore | 第 26 章 26.6 |
| IAM DB authentication token | 有效 15 分鐘 | 設計行為 | — | 第 26 章 26.6 |
| Enhanced Monitoring | 最細 1 秒 | 可設定 | — | 第 26 章 26.8 |
| Blue/Green switchover | 中斷通常在 1 分鐘以內 | 設計行為 | — | 第 26 章 26.12 |
| RDS Proxy | 必須與 DB 在同一 VPC，不能設為 public | hard limit | 「Lambda 大量連線打爆 DB」→ RDS Proxy | 第 26 章 26.7 |

## B.26 Aurora

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 儲存副本 | 6 份跨 3 AZ；每 10 GB 一個 segment；寫入 4/6、讀取 3/6 | 設計行為 | 高頻考點 | 第 4 章 4.7；第 26 章 26.9 |
| Aurora Replicas | 每個 cluster 最多 15 個 | hard limit | replica lag 通常低於 100 毫秒 | 第 26 章 26.9 |
| Failover priority tier | 0–15，數字越小越優先 | 可設定 | — | 第 26 章 26.9 |
| 儲存上限 | 128 TiB；較新的 Aurora MySQL 3.10+ 與 Aurora PostgreSQL 版本為 256 TiB | hard limit | 見 B.40 | 第 26 章 26.9 |
| Backup retention | 1–35 天 | 可設定 | — | 第 26 章 26.9 |
| I/O-Optimized | I/O 費用超過總費用約 25% 時划算；從 Standard 切過去每 30 天限一次 | — | — | 第 26 章 26.9；第 39 章 39.8 |
| Serverless v2 | 每 ACU 約 2 GiB 記憶體；以 0.5 ACU 為單位；較新版本可設最小 0 ACU（auto-pause，恢復要幾秒） | 可設定 | Serverless v1 已結束支援 | 第 26 章 26.10 |
| Global Database | 複寫 lag 通常 < 1 秒；最多 10 個 secondary Region | 設計行為 | 「RPO 秒級、RTO 約 1 分鐘、跨 Region」→ Global Database；舊值 5 個 | 第 26 章 26.11；第 34 章 34.7 |
| Global Database switchover | RPO 0 | 設計行為 | 計畫性切換用 switchover，故障用 failover | 第 26 章 26.11 |
| Backtrack | 最多 72 小時；只有 Aurora MySQL；不支援 Global Database | hard limit | 「誤刪資料、幾分鐘內倒回」→ Backtrack | 第 26 章 26.11 |
| Cloning | 通常幾分鐘，與資料庫大小幾乎無關 | 設計行為 | — | 第 26 章 26.11 |

## B.27 DynamoDB 與 DAX

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Item 大小 | 最大 400 KB（含屬性名稱） | hard limit | 大物件放 S3，item 存指標 | 第 27 章 27.3；第 35 章 35.6 |
| Partition | 約 10 GB；每秒最多 3,000 RCU、1,000 WCU | hard limit | 熱 key → 分散 partition key 或 write sharding | 第 27 章 27.4；第 35 章 35.4 |
| Burst capacity | 保留約 5 分鐘未用完的容量（provisioned） | 設計行為 | — | 第 27 章 27.4 |
| RCU | 1 RCU = 每秒 1 次 strongly consistent 讀取（≤ 4 KB）；eventually consistent 為 0.5；transactional 為 2 | 計算公式 | 大小向上取整 | 第 27 章 27.6 |
| WCU | 1 WCU = 每秒 1 次寫入（≤ 1 KB）；transactional 為 2 | 計算公式 | — | 第 27 章 27.6 |
| Query／Scan 每頁 | 最多 1 MB | hard limit | 用 `LastEvaluatedKey` 分頁 | 第 27 章 27.5 |
| BatchGetItem／BatchWriteItem | 100 個／25 個 item | hard limit | BatchWriteItem 不是交易 | 第 27 章 27.5、27.9 |
| Transactions | TransactWriteItems 最多 100 個動作、合計 4 MB；TransactGetItems 100 個 | hard limit | 舊教材寫 25 個，見 B.40 | 第 27 章 27.9 |
| ClientRequestToken | 10 分鐘內重送不重複執行 | 設計行為 | — | 第 27 章 27.9 |
| On-demand 擴展 | 立即承受先前尖峰的 2 倍；30 分鐘內超過 2 倍可能 throttle；新表約每秒 4,000 寫、12,000 讀 | warm throughput 可提高 | — | 第 27 章 27.7 |
| Capacity mode 切換 | 24 小時內最多 4 次切到 on-demand；切回 provisioned 不限 | hard limit | 舊值 24 小時 1 次 | 第 27 章 27.7 |
| LSI | 每表最多 5 個，只能建表時建立；item collection 最多 10 GB | hard limit | — | 第 27 章 27.8 |
| GSI | 每表預設 20 個 | 預設 quota，可申請提高 | 可隨時新增 | 第 27 章 27.8 |
| TTL 刪除 | 到期後通常數天內完成，不耗 WCU | 設計行為 | 舊資料寫 48 小時；查詢時要自己過濾已過期的 item | 第 27 章 27.10 |
| Streams 保留 | 24 小時；每個 shard 建議最多 2 個消費者 | hard limit | 要保留更久或更多消費者 → Kinesis Data Streams for DynamoDB | 第 27 章 27.10；第 31 章 31.8 |
| Global tables MREC | 複寫通常約 1 秒；last writer wins | 設計行為 | — | 第 27 章 27.12；第 34 章 34.7 |
| Global tables MRSC | 剛好 3 個 Region（3 replica 或 2 replica + 1 witness）；RPO 0；不支援 transactions、TTL、LSI | hard limit | — | 第 27 章 27.12 |
| PITR | 最多 35 天（可設較短） | 可設定 | — | 第 27 章 27.13；第 34 章 34.7 |
| DAX | item／query cache TTL 預設 5 分鐘；建議至少 3 個 node 跨 AZ | 可設定 | 「DynamoDB 讀取要微秒級」→ DAX | 第 27 章 27.11；第 28 章 28.11 |

## B.28 ElastiCache 與 MemoryDB

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 shard 的 replica | 0–5 個 | hard limit | 要 failover 至少 1 個 replica 在另一個 AZ | 第 28 章 28.6、28.7 |
| Cluster mode hash slot | 16,384 個 | 設計行為 | — | 第 28 章 28.7 |
| Failover 時間 | 秒級到數十秒 | 設計行為 | — | 第 28 章 28.7 |
| 自動備份保留 | 最長 35 天 | 可設定 | Memcached 沒有複寫與備份 | 第 28 章 28.7 |
| 預設 port | Valkey／Redis OSS 6379；Memcached 11211 | 可設定 | — | 第 28 章 28.10 |
| 預設 eviction policy | `volatile-lru` | 可設定 | — | 第 28 章 28.5 |
| Valkey | 2024 年從 Redis OSS 7.2 分支；定價比 Redis OSS 低 | — | — | 第 28 章 28.6 |
| ElastiCache Serverless | 約 1 分鐘可用；預設 Multi-AZ、TLS、加密；可設資料量與 ECPU/s 上限 | 可設定 | — | 第 28 章 28.9 |
| Global Datastore | 跨 Region lag 通常 < 1 秒；只有 primary Region 可寫 | 設計行為 | — | 第 28 章 28.15 |
| MemoryDB | 微秒讀取、個位數毫秒寫入；Multi-AZ 交易日誌 | 設計行為 | 「Redis 相容 + 持久化主資料庫」→ MemoryDB | 第 28 章 28.11 |

## B.29 Purpose-built 資料庫

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| DocumentDB | 最多 15 個 replica；6 份副本跨 3 AZ；PITR 1–35 天 | hard limit／可設定 | — | 第 29 章 29.3 |
| Neptune | 1 primary + 最多 15 個 read replica；6 份副本跨 3 AZ；Gremlin、openCypher、SPARQL | hard limit | — | 第 29 章 29.5 |
| Keyspaces | 3 份副本跨多個 AZ | 設計行為 | — | 第 29 章 29.6 |
| OpenSearch | 正式環境建議 3 個 dedicated master；refresh 預設約 1 秒 | 可設定 | 從 Elasticsearch 7.10 分支 | 第 29 章 29.4 |
| Timestream for LiveAnalytics | 自 2025-06-20 起不開放新客戶 | — | 見 B.40 | 第 29 章 29.7 |
| QLDB | 2025-07-31 停止支援 | — | 新設計改用 Aurora PostgreSQL 等方案 | 第 29 章 29.8 |
| RDS for Oracle License Included | 只提供 Standard Edition 2 | 設計行為 | — | 第 29 章 29.11 |

## B.30 資料湖與分析

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Athena 最小計費 | 每個查詢 10 MB；DDL 與失敗的查詢不收費 | — | 用 Parquet + 分區減少掃描量 | 第 30 章 30.5 |
| Athena workgroup | 可設單一查詢掃描上限 | 可設定 | 「防止單一查詢掃描超過 1 TB」→ workgroup 限制 | 第 30 章 30.5 |
| 分區內檔案大小 | 建議數十 MB 到數百 MB | 建議 | 太多小檔案拖慢查詢 | 第 30 章 30.3 |
| Glue | 以 DPU 按秒計費 | — | — | 第 30 章 30.4 |
| Glue DataBrew | 超過 250 種內建轉換 | — | 「不寫程式清理資料」→ DataBrew | 第 30 章 30.4 |
| Redshift concurrency scaling | 每個 cluster 每天約累積 1 小時免費額度 | — | — | 第 30 章 30.7 |
| Redshift automated snapshot | provisioned 預設 1 天，最長 35 天；manual 保留到刪除為止 | 可設定 | — | 第 30 章 30.7 |
| Redshift Multi-AZ | 2 個 AZ（RA3） | 設計行為 | — | 第 30 章 30.7 |
| EMR 高可用 | 3 個 primary node | 可設定 | — | 第 30 章 30.8 |

## B.31 Kinesis、Firehose 與 MSK

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 每個 shard 寫入 | 每秒 1 MB 或 1,000 筆（先到者為準） | hard limit（加 shard 擴展） | 依此計算 shard 數 | 第 31 章 31.3；第 35 章 35.6 |
| 每個 shard 讀取（共用） | 每秒 2 MB，所有共用模式 consumer 一起分；每秒最多 5 次 GetRecords | hard limit | consumer 多 → enhanced fan-out | 第 31 章 31.3 |
| Enhanced fan-out | 每個 consumer 每 shard 各 2 MB/s；平均延遲約 70 毫秒（共用約 200 毫秒）；每 stream 預設最多 20 個 | 預設 quota | — | 第 31 章 31.3、31.4 |
| Record 大小 | 考題用 1 MB；現行 10 MiB | hard limit | 見 B.40 | 第 31 章 31.3 |
| Retention | 預設 24 小時，最長 365 天（超過 24 小時開始收延長保留費） | 可設定 | 「重播 3 天前的資料」→ 延長 retention | 第 31 章 31.3、31.10 |
| PutRecords | 一次最多 500 筆 | hard limit | — | 第 31 章 31.4 |
| 傳遞語意 | at-least-once | 設計行為 | consumer 要做到冪等 | 第 31 章 31.4 |
| Firehose buffer | S3 目的地 1–128 MB；間隔最長 900 秒（支援極小或零緩衝） | 可設定 | 延遲通常數十秒到數分鐘；不是毫秒級即時 | 第 31 章 31.5 |
| KDA for SQL | 2025-10-15 起不能新建；2026-01-27 起刪除既有應用程式 | — | 舊題的 Kinesis Data Analytics 對應到 Managed Service for Apache Flink | 第 31 章 31.6 |
| MSK replication factor | 通常 3，分散在 3 個 AZ | 可設定 | — | 第 31 章 31.7 |

## B.32 SQS

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 訊息大小 | 考題用 256 KB；2025 年起 1 MiB（1,048,576 bytes） | hard limit | 超過上限 → 資料放 S3、訊息只帶指標（Extended Client，最大 2 GB），見 B.40 | 第 32 章 32.7；第 54 章 54.10 |
| Retention | 1 分鐘到 14 天，預設 4 天 | 可設定（範圍內） | DLQ 的 retention 要比來源 queue 長 | 第 32 章 32.3、32.4 |
| Visibility timeout | 預設 30 秒，可設 0 秒到 12 小時；從第一次取走起算最多隱藏 12 小時 | 可設定（範圍內） | 設成 Lambda timeout 的 6 倍以上 | 第 32 章 32.4、32.6 |
| Long polling | 最多等 20 秒（`ReceiveMessageWaitTimeSeconds` 1–20；0 = short polling） | 可設定 | 「減少空回應、降低成本」→ long polling | 第 32 章 32.4 |
| Delay queue | 0–15 分鐘；per-message timer 只有 Standard 支援 | 可設定（範圍內） | 延遲超過 15 分鐘 → EventBridge Scheduler 或 Step Functions | 第 32 章 32.4；第 33 章 練習 33-1 |
| ReceiveMessage | 一次最多 10 則 | hard limit | — | 第 32 章 32.3 |
| FIFO 吞吐量 | 每個 API 動作每秒 300 次；batch 10 則時約每秒 3,000 則 | 預設值；high throughput mode 可大幅提高（依 Region，例如東京每秒 9,000 次） | 「嚴格順序 + 超過 3,000 TPS」→ high throughput mode | 第 32 章 32.5 |
| FIFO 去重 | 5 分鐘 | hard limit | 只防 5 分鐘內的 producer 重送；consumer 仍要冪等 | 第 32 章 32.5；第 33 章 33.4 |
| Standard 吞吐量 | 幾乎沒有上限 | 設計行為 | at-least-once、不保證順序 | 第 32 章 32.5 |
| DLQ maxReceiveCount | 不要設成 1 | 建議 | — | 第 32 章 32.6 |

## B.33 SNS、EventBridge 與 Amazon MQ

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| SNS 訊息大小 | 不比 SQS 大 | hard limit | 大資料同樣用 claim check | 第 32 章 練習 32-5 |
| EventBridge 每個 rule 的 target | 最多 5 個 | hard limit | 超過 5 個 → 多條 rule 或先送 SNS 扇出 | 第 32 章 32.10 |
| EventBridge 重試 | 預設最長 24 小時、最多 185 次 | 可調低 | — | 第 32 章 32.10 |
| EventBridge archive | 保存期間可自訂或無限期 | 可設定 | — | 第 32 章 32.10 |
| 跨帳號事件 | 只能「跳一次」帳號；2025 年起 rule 可直接送到另一帳號的 target | 設計行為 | — | 第 32 章 32.10、32.14 |
| EventBridge Scheduler | 預設 quota 很高 | 預設 quota，可申請提高 | 取代 EC2 cron | 第 32 章 32.10 |
| Amazon MQ | ActiveMQ active/standby 2 個 broker 跨 AZ；RabbitMQ cluster 3 個節點 | 設計行為 | 「遷移既有 JMS／AMQP 應用」→ Amazon MQ | 第 32 章 32.11 |

## B.34 Step Functions

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| 最長執行時間 | Standard 1 年；Express 5 分鐘 | hard limit | 人工核准或長時間等待 → Standard | 第 33 章 33.6；第 47 章 47.9 |
| Express 限制 | 不支援 callback（`.waitForTaskToken`）；不能 redrive | 設計行為 | — | 第 33 章 33.6、33.13 |
| State 間資料 | input／output 上限 256 KB | hard limit | 大資料放 S3，只傳位置 | 第 33 章 33.7 |
| Standard 歷史事件 | 25,000 個 | hard limit | 大量 iteration → Distributed Map 或拆成 child execution | 第 33 章 33.7 |
| Inline Map | 最多 40 個並行 iteration | hard limit | — | 第 33 章 33.7 |
| Distributed Map | 最多 10,000 個並行 child workflow | hard limit | 「處理 S3 上數百萬個物件」→ Distributed Map | 第 33 章 33.7 |
| Standard 執行歷史保留 | 結束後 90 天；execution name 90 天內不能重複 | 設計行為 | — | 第 33 章 33.4、33.6 |
| Redrive | Standard 結束後 14 天內 | hard limit | — | 第 33 章 33.7 |
| Retry 預設 | IntervalSeconds 1、MaxAttempts 3、BackoffRate 2.0 | 可設定 | 沒設 TimeoutSeconds 的 task 可能卡到 1 年 | 第 33 章 33.7 |
| AWS SDK standard retry | 預設最多 3 次嘗試（含第一次） | 可設定 | 多層各重試 3 次 = 27 倍放大 | 第 33 章 33.3；第 35 章 35.8 |

## B.35 高可用、DR 與 AWS Backup

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Backup & Restore | RTO／RPO 數小時 | — | 最便宜 | 第 34 章 34.6 |
| Pilot light | RTO 數十分鐘到數小時（依點火的自動化程度）；RPO 秒到分鐘級 | — | 資料持續複寫，運算平時不跑 | 第 34 章 34.6 |
| Warm standby | RTO 數分鐘；RPO 秒級 | — | 縮小版環境一直在跑 | 第 34 章 34.6 |
| Active-active | RTO 接近 0；RPO 接近 0 到秒級 | — | 最貴 | 第 34 章 34.6 |
| 各保護方式的 RPO | 每日 snapshot 最多 24 小時；每小時 1 小時；PITR 分鐘級；非同步複寫秒級；同步接近 0 | — | — | 第 4 章 4.9；第 34 章 34.5 |
| AWS Backup cold storage | 轉入後至少存 90 天 | hard limit | — | 第 34 章 34.8 |
| AWS Backup continuous backup | 最長 35 天（PITR）；複製到其他 Region／帳號的副本沒有 PITR | hard limit | — | 第 34 章 34.8 |
| Elastic Disaster Recovery | RPO 秒級、RTO 分鐘級 | 設計行為 | — | 第 34 章 34.9 |

## B.36 CloudWatch、X-Ray 與監控

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| EC2 監控 | basic 每 5 分鐘（免費）；detailed 每 1 分鐘（付費） | 可設定 | — | 第 36 章 36.3 |
| High-resolution metric | 以 1 秒粒度儲存；alarm period 可設 10 秒或 30 秒 | 可設定 | 「秒級告警」→ high-resolution custom metric | 第 36 章 36.3 |
| Metric 保留 | 60 秒以下 3 小時；60 秒 15 天；5 分鐘 63 天；1 小時 455 天（約 15 個月） | 設計行為 | 要保留更久 → 匯出到 S3 | 第 36 章 36.3 |
| Logs retention | 預設永不過期，可設 1 天到 10 年 | 可設定 | 成本題記得設定 retention | 第 36 章 36.6 |
| Log class | 只能在建立 log group 時選；Infrequent Access 不支援 metric filter、subscription filter、Live Tail | hard limit | — | 第 36 章 36.6 |
| Subscription filter | 每個 log group 最多 5 個 | hard limit | — | 第 36 章 36.6 |
| X-Ray 預設取樣 | 每秒第一個請求，之後其餘的 5% | 可設定 | X-Ray SDK／daemon 已於 2026-02 進入維護模式 | 第 36 章 36.8 |
| X-Ray daemon | UDP 2000 | — | — | 第 36 章 36.8 |
| Service Quotas 自動通知 | 使用率 80%／95% | 可設定 | 「快要碰到 quota 要先知道」→ Service Quotas + CloudWatch alarm | 第 35 章 35.6 |

## B.37 IaC、部署與營運自動化

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| CloudFormation rollback trigger | 更新期間與完成後的監控期間（最長 180 分鐘） | 可設定 | 「部署後錯誤率上升要自動退回」→ rollback trigger | 第 37 章 37.4 |
| CodeDeploy Lambda／ECS canary | 例如 `Canary10Percent5Minutes`：10% 流量 5 分鐘後全切 | 預設設定可選 | alarm 觸發時自動切回 | 第 37 章 37.6、37.9 |
| Linear | 例如每 1 分鐘增加 10%，10 分鐘後 100% | 預設設定可選 | — | 第 37 章 37.8 |
| CodeCommit 狀態 | 2024-07 停止對新客戶開放；2025-11-24 宣布恢復 GA | — | 見 B.40 | 第 37 章 37.7；第 40 章 40.5 |
| Systems Manager State Manager | 例如每 30 分鐘檢查並修正一次 | 可設定 | — | 第 38 章 38.5 |
| Incident Manager／Change Manager | 自 2025-11-07 起不開放給新客戶 | — | — | 第 38 章 38.9 |
| Support 方案 | Developer、Business、Enterprise On-Ramp 將於 2027-01-01 停止 | — | 考題仍以「Business 以上才有完整 Trusted Advisor 與 Health API」描述 | 第 38 章 38.9；第 36 章 36.11 |

## B.38 成本最佳化

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Compute Savings Plans | 1 或 3 年；最高約 66%；適用 EC2（任何 family／Region）、Fargate、Lambda | — | 會換 family、Region 或改用 containers／Lambda 時選它 | 第 17 章 17.11；第 39 章 39.5 |
| EC2 Instance Savings Plans | 最高約 72%；family 與 Region 固定 | — | — | 第 39 章 39.5 |
| SageMaker Savings Plans | 最高約 64% | — | — | 第 39 章 39.5 |
| Standard RI | 最高約 72%；可在 Marketplace 轉賣 | — | — | 第 17 章 17.11；第 39 章 39.11 |
| Convertible RI | 最高約 66% | — | — | 第 17 章 17.11；第 39 章 39.11 |
| Database Savings Plans | 2025 年底推出；1 年、No Upfront；最高約 35%；跨引擎、family、Region 適用 | — | — | 第 39 章 39.5 |
| On-Demand Capacity Reservation | 本身不打折；future-dated 可提前 5–120 天申請，最少承諾 14 天 | — | 「確保容量」→ Capacity Reservation，「折扣」→ SP／RI | 第 39 章 39.5 |
| Compute Optimizer lookback | 預設 14 天；enhanced infrastructure metrics 可延長到 93 天 | 可設定（付費） | 記憶體指標需要 CloudWatch agent | 第 39 章 39.6；第 46 章 46.9 |
| 排程關機 | 一週 168 小時只開 50 小時，約省七成 compute 費用 | — | — | 第 39 章 39.6 |
| NAT Gateway 處理費 | us-east-1 常見每 GB 0.045 美元（各 Region 不同） | — | 大量 S3 流量 → gateway endpoint 免費 | 第 39 章 39.3 |

## B.39 遷移與 AI

| 項目 | 數值 | 可否調整 | 考試注意 | 出處 |
|---|---|---|---|---|
| Migration Hub／Application Discovery Service | 自 2025-11-07 起不開放給新客戶 | — | 新評估改用 AWS Transform；見 B.40 | 第 44 章 44.4 |
| TCO 比較期間 | 通常 3–5 年 | — | — | 第 44 章 44.5 |
| Retire 比例 | 大型遷移常有 10%–20% 可退役 | — | — | 第 44 章 44.6 |
| DMS archived log | 保留時間要長於 task 可能中斷的時間 | 設計考量 | 太短 → 只能重新 full load | 第 45 章 45.6 |
| Cutover 前 DNS TTL | 提前（例如兩週前）從 1 小時降到 60 秒 | 可設定 | 舊 TTL 要先過期，新 TTL 才生效 | 第 45 章 45.10 |
| SageMaker asynchronous inference | 結果寫 S3 並以 SNS 通知；沒有請求時可縮到 0 | 設計行為 | 大型輸入、處理數分鐘 → async inference | 第 47 章 47.4 |
| Bedrock human-in-the-loop | Step Functions Standard 等待核准；Express 5 分鐘、Lambda 15 分鐘都不適合 | 設計行為 | — | 第 47 章 47.9、47.14 |

## B.40 考試常用數字 vs 現行數字

這一節列出 AWS 已經調整、但考題或舊教材可能仍用舊值的數字。作答原則：**題目給了數字，就照題目的數字推理**；題目沒給，用考試常見的數字判斷，因為題庫更新比服務慢。實際設計系統時，以現行數字為準。

### 限制數值

| 項目 | 考題／舊教材常用 | 現行數字 | 作答建議 | 出處 |
|---|---|---|---|---|
| SQS 訊息大小 | 256 KB | 1 MiB（2025 年起） | 「訊息超過 256 KB」→ 放 S3、訊息只帶指標 | 第 32 章 32.7 |
| Lambda 非同步 event 大小 | 256 KB | 1 MB（2025 年起） | 大資料一樣改傳 S3 位置 | 第 19 章 19.4 |
| Kinesis Data Streams record | 1 MB | 10 MiB（1–10 MiB 依賴 burst capacity） | 依題目的數字計算 shard | 第 31 章 31.3 |
| S3 單一物件 | 5 TB | 約 50 TB（48.8 TiB = 10,000 parts × 5 GiB） | 單一 PUT 仍是 5 GB，part 數仍是 10,000 | 第 22 章 22.4 |
| EBS gp3 上限 | 16 TiB、16,000 IOPS、1,000 MiB/s | 64 TiB、80,000 IOPS、2,000 MiB/s（2025 年起） | 題目要求超過 16,000 IOPS 時，傳統答案是 io2 | 第 24 章 24.4 |
| EBS Elastic Volumes 修改頻率 | 每次修改後要等 6 小時 | 任意連續 24 小時內最多 4 次 | — | 第 24 章 24.3 |
| Aurora 儲存上限 | 128 TiB | 較新的 Aurora MySQL 3.10+ 與 Aurora PostgreSQL 版本為 256 TiB | — | 第 26 章 26.9 |
| Aurora Global Database secondary Region | 5 個 | 10 個 | — | 第 26 章 26.11 |
| RDS（MySQL、MariaDB、PostgreSQL）read replica | 5 個 | 15 個 | — | 第 26 章 26.4 |
| DynamoDB TransactWriteItems | 25 個動作 | 100 個動作、合計 4 MB | — | 第 27 章 27.9 |
| DynamoDB TTL 刪除時間 | 48 小時內 | 通常數天內 | 兩者都不是即時；查詢要自己過濾已過期的 item | 第 27 章 27.10 |
| DynamoDB 切換到 on-demand | 每 24 小時 1 次 | 每 24 小時最多 4 次 | — | 第 27 章 27.7 |
| Lambda@Edge timeout | viewer 觸發 5 秒、origin 觸發 30 秒 | 一律 30 秒 | 「viewer 端極短的輕量改寫」仍優先考慮 CloudFront Functions | 第 11 章 11.8 |
| Lambda 擴展速率 | 依 Region 先 burst 500–3,000，之後每分鐘 +500 | 每個函式每 10 秒最多新增 1,000 個執行環境 | 本書只講現行模型；看到舊說法知道是同一件事 | 第 19 章 19.8 |
| API Gateway REST 整合逾時 | 29 秒（不可調整） | 預設 29 秒；Regional／private 可申請提高 | 題目說 29 秒時，長工作就改非同步 | 第 20 章 20.11 |
| Site-to-Site VPN tunnel 頻寬 | 1.25 Gbps | 標準 1.25 Gbps；large bandwidth tunnel 約 5 Gbps（僅 TGW／Cloud WAN） | 考題仍以 1.25 Gbps 加「VGW 不支援 ECMP」判斷 | 第 8 章 8.3 |
| KMS AWS managed key 輪替 | 每 3 年 | 每年 | — | 第 15 章 15.3 |
| Convertible RI 最高折扣 | 約 54% | 約 66% | — | 第 17 章 17.11 |
| Auto Scaling warm pool | 不能搭配 mixed instances policy | 全部 On-Demand、不用 weight 時可以；Spot 仍然不行 | — | 第 18 章 18.8 |

### 架構與服務現況

| 項目 | 考題／舊教材常見說法 | 現況 | 作答建議 | 出處 |
|---|---|---|---|---|
| NAT Gateway | zonal、每 AZ 一台 | 另有較新的 regional 可用性選項 | SAA 考題仍以「每個 AZ 一台」為標準答案 | 第 5 章 5.7 |
| CloudFront 存取 S3 | OAI | OAC（OAI 是舊做法） | 新設計選 OAC | 第 11 章 11.5 |
| 固定 IP | Global Accelerator | CloudFront 另有 Anycast static IP | 「需要固定 IP」的標準答案仍是 Global Accelerator | 第 11 章 11.11 |
| PrivateLink 跨 Region | 只能同 Region | 已支援跨 Region | 考題情境多以同 Region 為前提 | 第 7 章 7.5 |
| S3 Select／Glacier Select | 篩選物件內容的答案 | 自 2024-07 起不開放新客戶 | 舊題可能仍以它為答案 | 第 22 章 22.13 |
| S3 Object Lambda | 讀取時轉換資料的答案 | 自 2025-11-07 起只提供給既有客戶 | 考試仍是這個需求的典型對應 | 第 22 章 22.13 |
| Snowball Edge／Snowcone／Snowmobile | 離線大量傳輸 | Snowball Edge 不再提供給新客戶；Snowcone、Snowmobile 已停止 | 考題可能仍以 Snowball 為答案；實務先算線上傳輸 | 第 25 章 25.9 |
| FSx File Gateway | 地端快取 FSx for Windows | 不再提供給新客戶 | — | 第 25 章 25.4 |
| Timestream for LiveAnalytics | 時間序列資料庫答案 | 自 2025-06-20 起不開放新客戶 | 考題可能仍以它為答案 | 第 29 章 29.7 |
| QLDB | 不可竄改帳本的答案 | 2025-07-31 停止支援 | 新設計改用其他方案 | 第 29 章 29.8 |
| Kinesis Data Analytics for SQL | 串流 SQL 分析 | 已停止；改用 Managed Service for Apache Flink | 看到 KDA 就對應到 Flink | 第 31 章 31.6 |
| CodeCommit | 已不接受新客戶（2024-07 的狀態） | 2025-11-24 宣布恢復 GA，重新開放新客戶 | 舊題或舊文章仍可能寫「已關閉」；現在新帳號可以使用，不要以此排除它 | 第 37 章 37.7；第 40 章 40.5 |
| Migration Hub／ADS | 遷移評估與探索 | 自 2025-11-07 起不開放新客戶；改用 AWS Transform | 舊題仍以 ADS 為答案 | 第 44 章 44.4 |
| Aurora Serverless v1 | 可自動暫停的 serverless DB | 已結束支援；v2 較新版本可縮到 0 ACU | 選 Serverless v2 | 第 26 章 26.10 |
| Security Hub | 集中 findings 與合規檢查 | 2025 年起改稱 Security Hub CSPM，另推出新版 Security Hub | 功能定位不變 | 第 40 章 40.7 |
| CloudTrail Lake | 集中查詢稽核事件 | 自 2026-05-31 起不開放新客戶；既有客戶可繼續使用 | 新設計用 trail → S3 + Athena，或依 AWS 建議匯入 CloudWatch | 第 16 章 16.10 |
| Audit Manager | 自動收集稽核證據 | 維護模式；自 2026-04-30 起新帳號無法設定，既有客戶不能擴展到新 Region 或新 organization | 考題仍可能以它為答案；新帳號改用 Config conformance packs | 第 16 章 16.12；第 50 章 |
| App Runner | 只給 image 或原始碼就上線的 web 服務 | 已不開放新客戶；既有客戶可照常使用（含建立新服務），不再新增功能 | 考題仍可能以它為答案；新專案評估 ECS Express Mode | 第 21 章 21.11 |
| Incident Manager／Change Manager | 事故應變、變更核准 | 自 2025-11-07 起不開放新客戶 | 新設計用含 `aws:approve` 的 runbook 或 pipeline 人工核准 | 第 38 章 38.9 |
| ARC readiness check | 檢查 DR 端是否準備好 | 已不開放新客戶；既有客戶可繼續使用 | 新環境用 ARC Region switch 的 plan evaluation | 第 34 章 34.10 |
| Bedrock Agents | 受管 agent（action group + Lambda） | 更名為 Agents Classic；自 2026-07-30 起不開放新客戶（維護模式） | 考題概念仍適用；新開發用 AgentCore | 第 47 章 47.7 |
| Amazon Forecast | 時間序列預測 | 已不開放新客戶；既有客戶可繼續使用 | 新需求評估 SageMaker Canvas 等 | 第 47 章 47.3 |
| App2Container | 不需原始碼把既有應用容器化 | 自 2025-11-07 起不開放新客戶 | 新專案改用 AWS Transform | 第 46 章 46.7 |
| Elastic Transcoder | 檔案型影片轉碼 | 已終止服務 | 改用 AWS Elemental MediaConvert | 第 48 章 48.7 |
| SAP 考試版本 | SAP-C02 | SAP-C03 自 2026-10-27 開放報名；SAP-C02 最後應考日 2026-11-17 | 報名前確認版本 | 第 1 章 1.2；第 54 章 54.10 |

> [!warning] 常見誤解
> 「可申請提高」不代表題目可以用它當解法。題目寫「不能修改程式、要立即解決」，而瓶頸是 hard limit（Lambda 15 分鐘、DynamoDB 400 KB、partition 1,000 WCU）時，申請 quota 永遠不是答案。瓶頸是預設 quota（Lambda concurrency、API Gateway throttle、EC2 vCPU）時，「申請提高 quota」才可能是最省力的正確選項。
