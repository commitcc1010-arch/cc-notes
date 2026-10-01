---
title: AI Autonomy Maturity Model
---

# 附錄 C　AI Autonomy Maturity Model

這份附錄把全書關於「AI agent 可以被授權做到哪裡」的內容整理成一份可以直接使用的參考。等級的定義以第 47 章 47.6 節為準，本附錄不另訂不同的定義，只把它展開成每一級的例子、升級證據、guardrails、降級條件與審計要求，並附上和第 31 章授權階梯的對照、一份組織導入檢核表，以及一份 agent policy 範本。

使用方式很簡單：先列出組織中每一個 agent 參與的 **workflow × 環境**（例如「清理磁碟 × production」），替每一格決定一個等級；再把等級、邊界與降級條件寫成 policy，交給 tool gateway 強制執行；最後用證據申請升級，用事先寫好的條件自動降級。第 2 章的責任分工、第 31 章的護欄與第 47 章的身份、gateway、eval，是這份附錄背後的三塊基礎。

> [!note] 這份附錄描述的是授權，不是模型能力
> 等級回答的是「agent 的動作會產生什麼 side effect、人在哪個環節把關」。一個很強的模型在某個 workflow 可以只有 L1，一個普通的模型在另一個 workflow 可以是 L4。換模型不會自動改變等級，但會觸發降級（C.4）。

## C.1 先記住六條原則

**第一，授權的單位是 workflow × 環境，不是 agent。** 同一個維運 agent，在「清理磁碟」可以是 L4，在「資料庫 failover」只能是 L2。第 47 章柏翰帳號事件的根源，就是 staging 的 L4 授權悄悄延伸到 production。只用一個數字描述一個 agent，授權一定會外溢。

**第二，等級是天花板，不是保證。** 即使是 L4，每一個動作仍要經過 tool 層的 policy 檢查（第 2 章的 `policy_check`、第 47 章的 tool gateway）。等級決定「最多能做到哪裡」，policy 決定「這一次能不能做」。

**第三，policy 必須在模型之外強制執行。** 寫在 prompt 裡的規則只是建議，會被誤解、被 prompt injection 覆蓋，也會在換模型時改變效果（第 2、48 章）。凡是違反時會造成單向損失的規則，都要在工具執行之前由確定性的程式檢查。

**第四，L3 有核准疲勞的風險。** 值班者一天核准兩百筆動作時，L3 實際上變成沒有邊界的 L4。L3 適合量少、每筆影響大的動作；量大、每筆影響小的動作，應該設計好邊界升到 L4，把人的注意力留給例外。

**第五，L5 很少，而且要被環境本身限制。** L5 只適用於所有動作都能完全回復的地方，例如開發環境或沙箱。L5 的成果若要進入 production，仍要走 L2 的路徑：開 PR、由人審查。Harbor 目前沒有任何 production 寫入的 workflow 在 L5。

**第六，agent 可以是 R，不能是 A。** 不論等級多高，每個 agent 都有一位具名的人類 owner 對它的行為負責，每一個被採用的產物都有一位核准的人（第 2、12、47 章）。等級越高，只是代表人把關的位置從「每個動作」移到「邊界與結果」，不代表責任轉移給 agent。

## C.2 等級總表

| 等級 | 名稱 | Agent 可以做什麼 | 人的角色 | 最常見的誤用 |
|---|---|---|---|---|
| L0 | 無存取（No access） | 不能接觸這個 workflow 的任何系統或資料 | 人完全自己做 | 以為「沒給工具」就等於 L0，卻讓 agent 讀得到含機密的文件或 log |
| L1 | 唯讀輔助（Read-only assist） | 讀取被授權的資料，回答、摘要、分析；產出不會被任何系統直接採用 | 人自己決定、自己執行 | 把 agent 的摘要直接當成事實，貼進事故結論或對外公告 |
| L2 | 提案（Propose） | 產生可被採用的產物（PR、設定 diff、指令、退款建議）；任何寫入都要經過人審查，由人或既有流程（CI／CD）執行 | 人審查每一個產物，決定是否採用 | Reviewer 對 agent 的 PR rubber stamp，審查名存實亡 |
| L3 | 核准後執行（Approve-to-execute） | 準備好參數完整、附 dry-run 結果的具體動作；人逐筆核准後，由工具代為執行 | 人核准每一筆動作 | 核准量太大，造成核准疲勞 |
| L4 | 有界自主（Bounded autonomy） | 在事先定義的邊界內自動執行，事後通知；超出邊界自動退回 L3 | 人定義邊界、抽查結果、處理被退回的例外 | 邊界只寫在文件或 prompt 裡，沒有由工具強制 |
| L5 | 目標自主（Goal-level autonomy） | 人只給目標與 policy，agent 自行規劃多步驟、跨工具的行動；仍受 policy、預算、稽核與 kill switch 約束 | 人審查結果與 policy，而不是個別動作 | 在無法完全回復的環境給 L5 |

讀這張表時，最重要的是「Agent 可以做什麼」一欄裡的 side effect 邊界：L1 的產出不被任何系統直接採用；L2 的產出可以被採用，但要經過人；L3 開始由工具替 agent 執行，但每一筆都有人按下核准；L4 把「每一筆」換成「邊界」；L5 把「邊界」換成「目標與 policy」。每往上一級，人看的東西就更少、更抽象，所以需要的證據與保護就更多。

## C.3 各等級詳解

下面每一級都用同樣的欄位描述。例子取自 Harbor 的三種 agent：工程團隊的 **coding agent**、SRE 的**維運 agent**，以及面向買家的 **AI 客服 agent**（第 48 章的 refund-assistant）。「升級證據」指從這一級升到下一級需要的證據，完整的門檻在 C.4。

### L0　無存取

L0 不是「什麼都沒做」，而是一個需要主動維持的狀態：agent 的身份不能取得這個 workflow 的任何憑證，相關資料也不能出現在 agent 能讀到的 context（文件、log、ticket）裡。第 47 章的 AI 政策規定了哪些決定**永遠留給人**：人事決策、對個別使用者有重大影響且無法回復的決定（例如永久停權）、資料的永久刪除，以及等級與 policy 本身的變更。這些 workflow 在 Harbor 都固定是 L0 或至多 L1，不開放申請升級。

| 項目 | 內容 |
|---|---|
| 定義 | 不能接觸這個 workflow 的任何系統或資料 |
| Coding agent | 存放金流商正式金鑰與 production secret 的設定；人事、薪資系統的 repository |
| 維運 agent | 金流商正式金鑰的輪替與管理（第 47 章的例子） |
| 客服 agent | 帳號永久停權、其他買家的訂單與個資（I4：只能操作目前登入買家本人的訂單） |
| 升到 L1 的證據 | 資料分級確認可以讓 agent 讀取；agent 有獨立身份與稽核紀錄 |
| Guardrails | 不發放憑證；gateway 對未授權的 workflow 一律 deny；資料分級標記讓檢索與 log 系統排除這些資料；「永遠留給人」的清單寫進 AI 政策 |
| 降級觸發 | 不適用（已是最低）；任何層級觸發 kill switch 時，該範圍實質上回到 L0，直到 owner 檢視 |
| 審計要求 | Gateway 記錄每一次被拒絕的請求；對 L0 範圍的存取嘗試即使被擋下，也依第 45 章的條件寫 postmortem |

### L1　唯讀輔助

L1 是所有 agent 的起點：Harbor 用 `harbor new agent` 建立的 agent 預設就是 L1（第 47 章）。L1 的風險不在 side effect，而在**資訊**：agent 可能讀到不該讀的資料、可能把錯誤的摘要寫得很有自信，也可能把讀到的惡意文字當成指令。所以 L1 的 guardrails 集中在資料權限與「輸出只是參考」這兩件事上。

| 項目 | 內容 |
|---|---|
| 定義 | 讀取被授權的資料（程式碼、metrics、logs、ticket），回答問題、摘要、分析；產出不會被任何系統直接採用 |
| Coding agent | 解釋程式碼、用 code search 回答「哪些服務呼叫了 `/v2/payments`」，回答附上檔案與行號 |
| 維運 agent | 值班時回答「過去一小時有哪些部署」；事故中擔任 scribe，由 IC 逐條確認（第 44、47 章） |
| 客服 agent | 查詢目前登入買家本人的訂單狀態並回答；檢索失敗時只能回答「目前無法確認政策，已為您轉人工」（第 48 章 game day 的發現） |
| 升到 L2 的證據 | 抽查回答的正確性；產物格式能被既有的 review 與 CI 流程處理 |
| Guardrails | 短效、唯讀的憑證；delegation 時權限取「agent 授權」與「委派者權限」的交集；讀到的內容一律視為資料而非指令；查詢附可重現的連結（第 31 章階段 0 的升級條件）；對話全文與個資預設不進 log |
| 降級觸發 | 本書沒有規定 L1 的自動降級。建議做法：升到 L1 的證據失效時退回 L0，例如資料被重新分類為機密，或 agent 失去獨立身份與稽核紀錄 |
| 審計要求 | 記錄 agent 身份、委派者、讀取了哪些資料與查詢；scribe 類用途要能區分「agent 起草」與「人確認」的內容 |

### L2　提案

L2 是 coding agent 最主要的等級，也是累積升級證據的地方。**Shadow mode**（影子模式：agent 對真實事件做出判斷但不執行，系統記錄它與人的決定）不是獨立的等級，因為它的 side effect 和 L2 相同。L2 的關鍵風險是審查品質：產出量變大時，reviewer 會開始不看內容直接核准（第 16 章）。

| 項目 | 內容 |
|---|---|
| 定義 | 產生可被採用的產物；任何寫入都要經過人審查，並由人或既有流程（CI／CD）執行 |
| Coding agent | 開 PR，由 reviewer 與 code owner 核准合併（第 16、48 章的 PR #2317）；第 2 章的 policy：只能在分支上工作、不能直接合併到主線 |
| 維運 agent | Shadow mode 中記錄它對每件 toil 的判斷；針對 `db-failover × prod` 只能提出建議與指令（第 47 章 47.10） |
| 客服 agent | Rollout 階段 2（agent shadow）：處理真實對話並提出 refund intent，不回覆買家、不執行（第 48 章） |
| 升到 L3 的證據 | Shadow 期間有足夠樣本、與人的決定高度一致，而且零次不安全的建議；離線 eval 通過 |
| Guardrails | Agent 不能核准自己開的 PR，也不能由同一個 agent 的另一個實例核准；PR 描述揭露 AI 參與範圍（附錄 D 的 PR 模板）；agent PR 遵守同樣的大小限制；CI 的依賴 allowlist 擋下不存在或未核可的套件（第 20、48 章）；shadow 的每一筆不一致都要被檢視 |
| 降級觸發 | 本書沒有規定 L2 以下的自動降級。建議做法：抽查正確率明顯下降，或產物持續無法通過 review 與 CI 時退回 L1 |
| 審計要求 | 每個產物連到 agent 身份與版本；記錄誰審查、誰採用；shadow 期間保存 agent 判斷與人的決定，作為升級證據 |

### L3　核准後執行

L3 和 L2 的差別在「誰執行」：L2 的產物由人或既有流程執行；L3 由工具替 agent 執行，人只負責逐筆按下核准。所以 L3 的核准請求必須讓人在幾秒內看懂影響：參數完整、dry-run 結果、影響範圍。核准介面設計得不好，L3 就會退化成蓋章。

| 項目 | 內容 |
|---|---|
| 定義 | 準備好參數完整、附 dry-run 結果的具體動作；人逐筆核准後，由工具代為執行 |
| Coding agent | 在 staging 執行資料庫 migration 或 backfill：agent 產生指令並附 dry-run 的影響列數，工程師逐次核准後由 migration 工具執行（示意） |
| 維運 agent | 值班者按下核准後，agent 執行 rollback 或擴容（第 47 章）；L4 動作超出邊界時被退回成 escalate，也走這條路 |
| 客服 agent | Rollout 階段 3：agent 回覆買家，所有退款由客服一鍵核准；超過 I3 自動上限（1,000 元）的案件永遠走 L3 |
| 升到 L4 的證據 | 一段時間內核准後執行零事故、被人否決的比例低；邊界（動作、影響、速率、預算）寫成 policy 並由工具強制 |
| Guardrails | Dry-run 預設開啟；工具層檢查 invariant（例如 I1 累計退款 ≤ 已付金額、I2 idempotency key）；blast radius 上限；監控每位核准者的核准量與核准速度，量大時改設計成 L4 |
| 降級觸發 | 第 47 章的自動降級條件（C.4）一旦成立，立刻降回 L2 |
| 審計要求 | 記錄核准者身份、核准時看到的 dry-run 內容、實際參數、執行結果；被否決的請求與否決理由同樣保存 |

### L4　有界自主

L4 是大部分「讓 AI 真的省下人力」的地方，也是護欄最多的地方。邊界不是讓 agent 停下來，而是把超出常態的動作交還給人：超出邊界的請求自動變成 escalate，回到 L3 的流程。第 47 章 47.10 的程式示範了這一點：同樣是清理磁碟，影響 2 台主機時自動執行，影響 12 台時超過上限 3，轉人核准。

| 項目 | 內容 |
|---|---|
| 定義 | 在事先定義的邊界內自動執行，事後通知；邊界包括允許的動作清單、單次影響上限、速率、時段與預算；超出邊界自動退回 L3 |
| Coding agent | Harbor 的 coding agent 目前沒有 L4 workflow。若要開放，第 12 章 Q7 的條件是起點：只限可逆、小範圍的變更類型（lint 修正、文件、補測試）與指定路徑，CI 綠燈後自動合併，有具名的人當 A 並定期抽查；付款、資料庫遷移、權限、依賴升級一律排除 |
| 維運 agent | 清理磁碟（`disk-cleanup × prod`，單次最多影響 3 台）；重啟單一不健康的 pod（第 47 章） |
| 客服 agent | Rollout 階段 4：≤ 1,000 元且原因碼屬於自動清單的退款，經 refund-gateway 驗證 I1–I4 後直接執行（第 48 章） |
| 升到 L5 的證據 | 環境的所有動作可完全回復；架構審查與工程副總簽核；只限非 production 或被環境本身限制的範圍 |
| Guardrails | 邊界寫成 policy 由 gateway 強制；空集合與異常輸入即停止；分批與驗證；速率限制；idempotency；kill switch 可依 agent、workflow、團隊或全公司一鍵停用；單次任務的 token、步數、時間上限由程式強制（第 48 章對付 denial of wallet 的做法） |
| 降級觸發 | 第 47 章的自動降級條件成立時降回 L2；另有執行期的止血動作（例如切到 `approval` 模式），見 C.4 |
| 審計要求 | 每一個自動動作都有完整稽核紀錄並事後通知 owner；抽查結果留存；被邊界擋下的請求與 escalate 的數量進入 dashboard，拒絕率突然上升時告警（第 48 章的 `RefundPolicyDenySpike`） |

### L5　目標自主

L5 的人不再看個別動作，所以它的安全性幾乎完全來自環境：動作能完全回復、影響被環境天然限制、預算與 kill switch 由程式強制。L5 也是唯一一個升級不能由程式自動判斷的等級，第 47 章 47.10 的授權引擎刻意讓 L5 一律回傳「需要架構審查與工程副總簽核」。

| 項目 | 內容 |
|---|---|
| 定義 | 人只給目標與 policy，agent 自行規劃多步驟、跨工具的行動，決定做法與順序；仍受 policy、預算、稽核與 kill switch 約束 |
| Coding agent | 「讓開發環境的 flaky test 比例降到 1% 以下」：agent 自行找出、隔離、修復，並把修正以 PR 送出（第 47 章） |
| 維運 agent | 「讓閒置的開發環境成本回到預算內」：agent 在開發環境自行找出並關閉閒置資源（示意；production 不適用） |
| 客服 agent | 不適用。客服 agent 的動作直接影響買家與金錢，沒有任何 workflow 能滿足「完全可回復」；Harbor 也不打算在可預見的未來這麼做 |
| 升級證據 | 已是最高等級 |
| Guardrails | 只限可完全回復的環境；token、步數、時間與金錢預算；kill switch；成果進入 production 一律走 L2 的 PR；policy 定期審查 |
| 降級觸發 | 環境不再能完全回復，或 agent 嘗試觸及 production；以及第 47 章的自動降級條件，皆降回 L2 |
| 審計要求 | 保存完整的規劃與工具呼叫 trace；定期審查結果與 policy，而不是只看單一動作；每一個送進 production 的成果都有 L2 的審查紀錄 |

## C.4 升級與降級

### 升級需要的證據

| 升級 | 需要的證據（第 47 章 47.6） | 第 47 章 47.10 授權引擎的示意門檻 |
|---|---|---|
| L0 → L1 | 資料分級確認可以讓 agent 讀取；agent 有獨立身份與稽核紀錄 | — |
| L1 → L2 | 抽查回答的正確性；產物格式能被既有的 review 與 CI 流程處理 | 離線 eval 通過率 ≥ 95%；零次不安全行為 |
| L2 → L3 | Shadow 期間有足夠樣本、與人的決定高度一致，而且零次不安全的建議；離線 eval 通過 | Shadow ≥ 200 筆且一致率 ≥ 97%；eval ≥ 95%；零次不安全行為；90 天內無相關事故 |
| L3 → L4 | 一段時間內核准後執行零事故、被人否決的比例低；邊界寫成 policy 並由工具強制 | 同上，另加 L3 期間的否決比例 |
| L4 → L5 | 環境的所有動作可完全回復；架構審查與工程副總簽核；只限非 production 或被環境本身限制的範圍 | 不由程式判斷，一律需要人簽核 |

這張表有兩件事值得強調。第一，**一次不安全的行為就足以擋下升級**，平均表現再好也一樣；第 31 章 31.10 的例子中，58 筆有 55 筆一致，但其中一筆是「在資料庫遷移進行中建議重啟節點」，那一筆比 95% 的一致率更重要。第二，升級由 owner 申請、由指定的審查者核准（第 47 章 47.12），agent 不能修改自己的等級，「治理 agent」也不應該自動調整其他 agent 的等級：授權模型是整套架構中最需要確定性的部分。

### 兩種降級：止血與授權

降級要分清兩件事，否則事故中會不知道該做哪一個：

- **執行期降級（止血）**：在事故或異常中，用預先準備好的開關立刻縮小 agent 的動作能力，不需要先知道原因。例如第 48 章 refund-assistant 的 `refund_assistant.mode` 可以從 `auto` 切到 `approval`（全部人工核准）、`lookup_only`（只查詢）或 `off`，30 秒內生效；rollout 計畫中的 SLO fast burn、invariant 違反、核准佇列等待超過 30 分鐘都會自動停止。這是 runbook 的動作，由值班者或自動化執行（第 44 章的先止血再修復）。
- **授權降級**：事後把 workflow 的等級往下調，要求重新累積證據。這是 policy 的動作，由 gateway 依事先寫好的條件自動執行，不是臨時開會討論。

第 47 章規定，以下任一情況會讓相關 workflow 的等級**立刻降回 L2**，重新累積證據：

1. Agent 的模型、prompt、工具或資料來源有重大變更（第 47 章 47.10 的 `on_version_change`：所有 L3 以上的授權降到 L2）。
2. Agent 造成或延長了一次事故。
3. 被人否決的比例突然上升。
4. Agent 的 owner 離職或轉調，而沒有新的 owner；agent 會維持降級，直到有人認領。

第 48 章的事故顯示「資料來源」要包含知識庫：INC-0611 之後，Harbor 把知識庫以快照版本納入 agent bundle，知識庫變更就是一次版本變更，走同樣的 eval、canary 與降級規則。

## C.5 和第 31 章授權階梯、第 48 章 rollout 階段的對照

第 31 章為 SRE 的維運 agent 訂了五個階段，第 47 章把它推廣成全公司的 L0–L5，第 48 章的 refund-assistant rollout 又沿用了第 31 章的階段編號。三者的對應如下：

| 第 31 章的階段 | 第 47 章的等級 | 第 48 章 refund-assistant 的 rollout 階段 | 說明 |
|---|---|---|---|
| （未列出） | L0 無存取 | 階段 0 之前：`refund_assistant.mode = off` | 階段 0 是 gateway 本身的 shadow（人工退款同時送 gateway 判斷但不執行），驗證的是確定性程式，此時 agent 尚未接上 |
| 階段 0　唯讀觀察 | L1 唯讀輔助 | （上線前已存在）查詢訂單 | AI 客服從 Part 0 起就能查訂單 |
| 階段 1　建議 | L2 提案 | 由階段 2 的人工比對取代 | 第 48 章明確寫出：階段 1「建議」由 shadow 中的人工比對取代 |
| 階段 2　Shadow | L2 的運作方式之一 | 階段 2　Agent shadow（2 週） | Shadow 不是獨立等級，side effect 與 L2 相同；它是累積升到 L3 證據的方法 |
| 階段 3　核准後執行 | L3 核准後執行 | 階段 3　核准後執行（2 週） | 客服一鍵核准每筆退款 |
| 階段 4　有界自動 | L4 有界自主 | 階段 4　有界自動（1% → 5% → 25% → 100%） | ≤ 1,000 元且原因碼屬於自動清單者直接執行 |
| （未列出） | L5 目標自主 | 不適用 | — |

對照表的實用意義是：當你在某份文件看到「階段 3」，要先確認它指的是第 31 章的階梯（等於 L3），還是某個 rollout 計畫自己的編號。Harbor 的做法是在 rollout 計畫中沿用第 31 章的編號，並在 agent policy 中一律以 L0–L5 記錄，避免同一個詞有兩種意思。

## C.6 審計紀錄的最低欄位

不論等級，每一個經過 tool gateway 的請求都要留下一筆紀錄，包括被拒絕的請求。欄位依第 47 章 47.7：

| 欄位 | 範例 | 回答的問題 |
|---|---|---|
| Agent 身份與 owner | `reco-cleaner`／柏翰（search） | 這是哪個 agent？出事找誰？ |
| 委派者 | 無（排程觸發）或某位工程師、某位登入的買家 | 代表誰在行動？ |
| 版本 | 模型、prompt、工具版本；Harbor 第 5 年起含知識庫快照 | 行為改變時，是哪個版本開始的？ |
| Workflow、環境與等級 | `feature-table-cleanup`／prod／L2 | 當時被授權到哪裡？ |
| 工具與參數 | `delete_rows(table=..., where=...)` | 實際嘗試做什麼？ |
| Policy 決定與理由 | deny：L2 以下不能直接寫入 | 為什麼被允許或拒絕？ |
| Trace id | 連到 agent 的推理與工具呼叫紀錄 | 它為什麼決定這麼做？ |

依等級需要額外保存的內容已列在 C.3 各級的「審計要求」。兩條跨等級的規則：第一，對話全文與個資預設不進 log，trace 只記錄去識別化的摘要與文件 ID，需要全文時透過有權限控管、有存取紀錄的工具查詢（第 48 章）；第二，AI agent 執行了超出預期範圍的動作，即使已被攔下，也要寫 postmortem（第 45 章的觸發條件）。

## C.7 組織導入檢核表

這份檢核表依導入的先後順序排列。每一項都對應到書中的章節，讀者可以把它複製到自己組織的導入計畫中，逐項附上證據。

**一、身份與可見度（先做，否則後面都無從檢查）**

- [ ] 每個 agent 都有自己的 non-human identity，不借用任何人的 token（第 47 章 47.7）。
- [ ] 憑證是短效的（例如數十分鐘），不是永久 token。
- [ ] 每個 agent 登記在服務目錄：具名的人類 owner、所屬團隊、用途、各 workflow × 環境的等級（第 47 章 47.5、47.7）。
- [ ] 盤點既有的 agent：比對 token 使用紀錄與 API 呼叫來源，找出未登記者；給個人 token 一段遷移期（Harbor 是六十天），期滿後不能存取 production。
- [ ] 新 agent 走 golden path 建立（Harbor 的 `harbor new agent`），預設等級 L1，自動取得身份、目錄登記、gateway 接線與 eval 範本。

**二、控制面（讓 policy 在模型之外強制）**

- [ ] 所有對外動作都經過 tool gateway：身份驗證、授權等級、policy、決定（allow／escalate／deny）、稽核、kill switch 六道檢查（第 47 章 47.7）。
- [ ] Agent 只能呼叫預先定義、範圍很窄的工具，不直接拿到 shell 或資料庫寫入權限（第 31 章的 tool broker）。
- [ ] Delegation 時，有效權限是「agent 授權」與「委派者權限」的交集，防止 confused deputy。
- [ ] 單向門的動作（金錢、資料刪除、權限變更）由確定性的程式守門，invariant 寫在工具裡而不是 prompt 裡（第 2、48 章）。
- [ ] Kill switch 可依 agent、workflow、團隊或全公司停用，生效時間經過實測（第 48 章：宣稱 30 秒、實測 4 分鐘，修正後 25 秒）。
- [ ] 稽核紀錄包含 C.6 的所有欄位，包括被拒絕的請求。

**三、變更管理（agent 的變更也是變更）**

- [ ] Agent 的版本定義為模型、system prompt、工具與工具描述、retrieval 資料來源與設定、policy 的組合；知識庫以快照版本引用（第 47 章 47.8、第 48 章）。
- [ ] 任何一部分的變更都走 code review、eval、漸進 rollout，並與服務共用 error budget（第 32、35 章）。
- [ ] Eval 分三類：能力、安全（要求零次違規）、回歸（每次事故後加入新案例）。
- [ ] Eval 每題跑多次，安全類案例要求每次都通過（第 48 章：每題 5 次全部通過）。
- [ ] Rollout 依序經過離線 eval、shadow、canary、全量；canary 涵蓋一次流量高峰。
- [ ] 固定外部模型的版本識別；把「供應商宣布模型更新」視為一次變更，並在線上持續執行一小組 canary eval。
- [ ] 版本變更自動觸發 C.4 的降級。

**四、責任與治理**

- [ ] 每個 agent 的 owner 對它的 eval、等級申請、事故處理負責；每個被合併的 agent 產物都有一位核准的人（第 47 章 47.9）。
- [ ] 職責分離：agent 不能核准自己的 PR；不能修改自己的 policy、等級或 prompt；對 production 有寫入權限的 agent，其 prompt 與設定存放在 repository，變更需要 owner 以外的人 review。
- [ ] AI 政策依風險分級（低、中、高），而不是一份禁止清單；高風險（production 寫入、金錢、個資）要求 gateway、安全 eval、shadow 證據、kill switch 與非 owner 審查。
- [ ] 「永遠留給人」的決定寫進政策並由組織領導者簽核：人事、不可回復的使用者決定、永久刪除資料、等級與 policy 變更。
- [ ] 高風險 agent 上線前經過 agent readiness review，由 SRE 參與（第 47 章 47.12）；AI 功能的 launch checklist 包含第 46 章 46.8 的額外檢查。
- [ ] Postmortem 不寫「AI 出錯了」，而是追問：這個動作為什麼能通過 gateway？等級是否授得太高？Eval 為什麼沒有涵蓋？

**五、量測與人的能力**

- [ ] 不以「AI 產生的程式碼行數」或「建議接受率」作為成功指標（第 14 章）。
- [ ] 追蹤：DORA 指標（含 rework rate）、AI 參與變更的 change failure rate、review 等待時間與 reviewer 負擔、agent 造成的事故數、gateway 拒絕與 escalate 次數、開發者體驗調查。
- [ ] 追蹤核准者的負擔與核准速度，偵測 L3 的核准疲勞。
- [ ] Game day 定期演練「agent 不可用」與「agent 給出錯誤判斷」的情境（第 46 章）。
- [ ] 新進工程師的前幾次值班，先自己排查、再看 agent 的分析；postmortem 記錄「人是否能理解並驗證 agent 的判斷」（第 47 章 47.9）。

## C.8 Agent policy 範本

**Agent policy** 是把一個 agent 的身份、各 workflow × 環境的等級、邊界、降級條件與審計要求寫成一份機器可讀的檔案。它放在 repository 中，由 tool gateway 讀取並強制執行；它的變更和程式碼一樣走 code review，而且 reviewer 必須是 owner 以外的人。附錄 D 的模板清單也收錄這份範本，但以本節為唯一版本。

### 空白範本

```yaml
# agent-policy.yaml —— 由 tool gateway 讀取；變更需 owner 以外的人 review
agent_id: <agent 名稱>
owner: <具名的人>（<團隊>）
backup_owner: <具名的人>          # owner 離職或轉調時，無人認領即自動降級
purpose: <一句話說明這個 agent 為誰、解決什麼問題>
risk_tier: <low | medium | high>  # 依 AI 政策的風險分級

identity:
  type: non-human
  credential_ttl: <例如 30m>
  delegation: <none | on_behalf_of_user>   # 若代表某人行動，權限取交集

version_bundle:                   # 任何一項變更 = 一次 agent 版本變更
  model: <模型識別碼與版本>
  prompt: <prompt 版本>
  tools: <工具定義版本>
  rules: <規則或 policy 版本>
  knowledge_base: <索引名稱@快照版本>     # 必須是不可變快照

workflows:                        # 授權單位：workflow × 環境
  - workflow: <名稱>
    env: <dev | staging | prod>
    level: <L0–L5>
    allowed_tools: [<工具名稱>, ...]
    boundaries:                   # L4 以上必填；由 gateway 強制
      max_blast: <單次最多影響幾個資源>
      max_amount: <金額上限，若適用>
      rate_limit: <每小時最多幾次>
      time_window: <允許的時段>
      budget: <token、步數、時間、金錢上限>
    on_exceed: escalate           # 超出邊界退回 L3，轉人核准
    approvers: [<L3 的核准者角色>]

invariants:                       # 由工具在執行前檢查，不寫在 prompt 裡
  - <例如：累計退款 ≤ 已付金額>

runtime_degradation:              # 執行期止血開關（runbook 使用）
  switch: <flag 名稱>
  modes: [<由寬到窄的模式>]
  measured_effective_time: <實測生效時間與日期>
  auto_stop_on: [<自動切換的條件>]

promotion:
  requested_by: owner
  reviewed_by: [<指定的審查者，非 owner>]
  evidence_required: <依附錄 C.4 的門檻>

demotion:                         # 成立即自動降回 L2，重新累積證據
  - version_bundle_changed
  - caused_or_prolonged_incident
  - override_rate_spike
  - owner_missing

eval_gates:
  capability: <資料集版本、通過門檻>
  safety: <對抗性案例、要求零次違規>
  regression: <事故案例集>
  run_on: [model, prompt, tools, rules, knowledge_base]

audit:
  fields: [agent, owner, delegator, version, workflow, env, level, tool, params, decision, reason, trace_id]
  log_denied_requests: true
  pii_in_logs: false
  retention: <保存期限>

never_delegated:                  # 這個 agent 永遠不能做的事
  - <例如：修改自己的 policy 或 prompt>

review:
  last_reviewed: <日期>
  next_review: <日期>
```

### Harbor 範例：refund-assistant（第 5 年 5 月下旬，100% 買家）

下面是第 48 章 AI 退款助理推到 100% 買家時的 policy。數字都取自第 48 章的 design doc、rollout 計畫、容量估算與 runbook；以 `# INC-0611 後` 開頭的註解，標出 48.12 的 action items 改變了哪些欄位。

```yaml
agent_id: refund-assistant
owner: 阿凱（客服平台）
purpose: 讓規則明確的退款案件在對話內完成，取代平均 19 小時的人工佇列
risk_tier: high                   # 涉及金錢與個資

identity:
  type: non-human
  credential_ttl: 30m
  delegation: on_behalf_of_user   # 代表目前登入的買家；I4 由 gateway 強制

version_bundle:
  model: <固定的模型版本識別>
  prompt: refund-assistant prompt（版本號隨 bundle）
  tools: propose_refund、get_order 的 JSON schema 版本
  rules: 規則引擎版本（寫入每筆 audit log）
  knowledge_base: policy-kb        # INC-0611 後：改為 policy-kb@v57 這類快照（ADR-047）

workflows:
  - workflow: order-lookup
    env: prod
    level: L1
    allowed_tools: [get_order]
  - workflow: refund-intent-auto
    env: prod
    level: L4
    allowed_tools: [propose_refund]   # 只能提出 refund intent，執行者是 refund-gateway
    boundaries:
      max_amount: 1000                # I3：超過轉人工核准
      auto_reason_codes: [未出貨取消, 物流遺失, 商品瑕疵]
      per_conversation: {tokens: 40000, tool_calls: 15, minutes: 10}
      per_buyer: 每小時 ≤ 3 次新對話
      # INC-0611 後：gateway 增加每小時自動退款預算，超過的案件轉人工（action item 4）
    on_exceed: escalate
    approvers: [客服當班人員]
  - workflow: refund-intent-approval
    env: prod
    level: L3                         # 超過 1,000 元或不在自動清單的原因碼
    allowed_tools: [propose_refund]
    approvers: [客服當班人員]
  - workflow: dispute-and-merged-refund
    env: prod
    level: L0                         # 賣家爭議、跨訂單合併退款：design doc 的非目標

invariants:
  - I1 單筆訂單累計退款 ≤ 已付金額
  - I2 同一 idempotency key 至多產生一筆退款
  - I3 自動退款單筆 ≤ 1,000 元，超過轉人工核准
  - I4 只能操作目前登入買家本人的訂單

runtime_degradation:
  switch: refund_assistant.mode
  modes: [auto, approval, lookup_only, off]
  measured_effective_time: 25 秒（game day 修正 app 端快取後重測）
  auto_stop_on:
    - SLO fast burn
    - 任何 invariant 違反            # 切到 off，並撤銷 agent 身份的 refund scope
    - 核准佇列等待 > 30 分鐘
    - 模型供應商連續失敗            # circuit breaker 切到 lookup_only

promotion:
  requested_by: 阿凱（附數據連結）
  reviewed_by: [美華（payments owner）, 志明（SRE）]
  evidence_required: 依 rollout 計畫各階段的晉升條件；L4 由 Kevin 在 launch checklist 簽核

demotion:
  - version_bundle_changed            # INC-0611 後：知識庫快照變更也算
  - caused_or_prolonged_incident
  - override_rate_spike               # 客服駁回比例突然上升
  - owner_missing

eval_gates:
  capability: 一般案例 600 題 × 5 次，通過率 ≥ 95%，且比上一版退步 ≤ 1 個百分點
  safety: 對抗性案例 120 題，每題 5 次全部通過；任一題嘗試越權工具呼叫即擋下發布
  fairness: 依書寫流暢度與語言分層，各層通過率差距 ≤ 3 個百分點
  regression: 事故案例集          # INC-0611 後：新增 40 題被誘導成瑕疵的案例與政策互相矛盾的案例
  run_on: [model, prompt, tools, rules, knowledge_base]

audit:
  fields: [agent, owner, delegator, version, workflow, env, level, tool, params, decision, reason, rule_version, trace_id]
  log_denied_requests: true
  pii_in_logs: false                # 對話全文不進 log；trace 只記去識別化摘要與文件 ID
  retention: 180 天

never_delegated:
  - 修改自己的 policy、等級、prompt 或知識庫
  - 在 production 直接改 prompt 或知識庫來「修正」行為（runbook 第 4 節）
  - 手動重送失敗的退款（一律用帶原 idempotency key 的對帳工具）

review:
  next_review: 第 5 年 7 月 1 日（與 SLO 文件一起檢討）
```

這份 policy 有三個地方值得對照前面幾節。第一，同一個 agent 有四個 workflow，等級從 L0 到 L4 都有，這就是 C.1 第一條原則的樣子。第二，L4 的邊界全部是 gateway 能檢查的數字，`on_exceed: escalate` 把超出邊界的案件交回 L3。第三，`runtime_degradation` 與 `demotion` 是兩個不同的區塊：前者是事故中 30 秒內能做的止血，後者是事後由 gateway 自動執行的授權降級。

### 第二個範例：SRE 維運 agent（節錄）

第 47 章 47.10 的授權引擎登記了 SRE 的維運 agent。寫成 policy 時只需要 workflow 區塊不同，其他欄位結構相同：

```yaml
agent_id: ops-agent
owner: 志明（SRE）
workflows:
  - workflow: disk-cleanup
    env: prod
    level: L4
    boundaries:
      max_blast: 3            # 影響超過 3 台主機即 escalate
    on_exceed: escalate
  - workflow: db-failover
    env: prod
    level: L2                 # 只能提出建議與指令；罕見但高風險，維持半自動（第 31 章 31.8）
demotion:
  - version_bundle_changed    # 換模型時 L3 以上全部降到 L2（47.10 的 on_version_change）
```
