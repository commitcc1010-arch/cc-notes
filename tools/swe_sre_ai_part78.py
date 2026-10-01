"""Parts 7 and 8: incident operations, organization design, and capstone."""
from __future__ import annotations

from swe_sre_ai_model import C


CHAPTERS = [
    C(
        43,
        "On-call 與 Evidence-driven Troubleshooting",
        "Pager 響起後，如何在資訊不足和時間壓力下縮小假設，而不是隨機重啟與同時改很多東西？",
        "中階",
        "建立健康 on-call 系統與科學化調查迴路：observe、localize、hypothesize、test、mitigate、verify。",
        ["oncall", "troubleshooting", "alert", "observability"],
        """
On-call 是 production feedback 的最後人類迴路。事件量過多、alert 無行動、runbook 過時或只有少數 expert 能處理，會造成疲勞並讓恢復依賴英雄。Troubleshooting 在壓力下更容易受 confirmation bias、最近事件和同時操作干擾，因此需要固定方法和角色支援。
""",
        """
Checkout error 上升。值班者若先重啟所有 pods，可能暫時改變症狀並破壞 evidence；若先確認使用者範圍、最近 changes、healthy/unhealthy 差異與 dependency traces，可發現只有新版本在特定 region 使用錯 config，安全 rollback。
""",
        r"""
actionable page
    ↓ acknowledge / assess severity / protect focus
scope: users, regions, versions, operations
    ↓
timeline + recent changes + dependency health
    ↓
hypotheses ranked by evidence
    ↓
one safe test / comparison at a time
    ↓
mitigate (rollback / shed / failover)
    ↓
verify SLI recovery + watch
    ↓
handoff / incident / follow-up
""",
        """
健康 on-call 需要可控事件量、合理輪值、訓練、shadow、backup 和 recovery time。Page 應有 owner、SLO、scope 和 first actions；runbook 讓一般值班者安全處理，不應只寫「找某人」。交班保存目前 impact、已驗證事實、操作、假設和下一步。

Troubleshooting 先分 symptom 與 cause。建立時間線、確認 blast radius、比較健康/不健康 cohort、檢查最近 change，再提出能被反證的假設。一次改一個變數，保存 query 和結果。Mitigation 的目標是使用者恢復，不必等待完整 root cause；rollback、load shed 和 feature disable 常比現場改 code 安全。

認知負荷也要管理。大型事故升級 incident command，小事件限制聊天室人數；固定記錄者避免值班者同時操作和寫報告。恢復後 watch SLI，確認不是短暫波動。Repeated pages 需轉 reliability work，不應把人類睡眠當無限 buffer。
""",
        [
            "建立 page quality、輪值、shadow、backup、handoff 和休息標準。",
            "先確認 user impact、scope、timeline、recent changes 和可用 safe actions。",
            "提出可反證 hypotheses，按 evidence/成本排序，一次驗證一項。",
            "優先 mitigation 恢復使用者，所有 mutation 記錄並能 rollback。",
            "以 SLI 驗證恢復與 watch，重複事件建立 owner/action 而非習慣化。",
        ],
        "範例用 evidence table 排序假設，避免只因『最近常見』就先操作。分數是結構化思考，不是自動 root cause。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Hypothesis:
    name: str
    supporting: int
    conflicting: int
    test_minutes: int
    test_risk: int

def priority(h: Hypothesis) -> float:
    evidence = h.supporting - 2 * h.conflicting
    cost = max(1, h.test_minutes + 3 * h.test_risk)
    return evidence / cost

candidates = [
    Hypothesis("bad rollout", 4, 0, 2, 1),
    Hypothesis("database", 2, 2, 8, 2),
]
print(sorted(candidates, key=priority, reverse=True))
""",
        [
            "Conflicting evidence 的權重較高，避免 confirmation bias 忽略反例。",
            "先測低風險、快速、資訊量高的假設，不等於它一定是 root cause。",
            "Production mutation 的 test risk 應高於唯讀 query 或 cohort comparison。",
            "每次結果要更新 table，不讓已被反證的假設反覆出現。",
        ],
        [
            "隨機重啟可能破壞 evidence，且未確認是否真的改善 user SLI。",
            "同時修改多項設定，恢復後無法知道哪個 action 有效。",
            "只有 primary on-call 懂服務，輪值其他人只是呼叫樹入口。",
            "將每次 page 視為個人表現問題，團隊不會投資降低事件量。",
        ],
        """
AI-SRE 很適合在事件初期收集 context、建立 timeline、關聯 recent changes、搜尋相似 incidents 和產生 hypotheses。它也可能把 correlation 寫成 root cause、被過時 runbook 誤導或在壓力下過度操作。最佳實務是 evidence-linked、read-only-first：每個主張附 query/trace/change，模型清楚分 facts、inferences 和 unknowns。
""",
        [
            "讓 AI 在 page 時自動準備 SLO、scope、recent changes、top traces 和 owners。",
            "用 agent 建立 supporting/conflicting evidence table 與下一個唯讀驗證。",
            "請 AI 搜尋相似 postmortems，但比較差異而非直接套用舊根因。",
            "讓 agent 產生 handoff/incident timeline，減少值班者文書負荷。",
        ],
        [
            "預設只讀 telemetry；mutation 必須 runbook allowlist、policy 或人類批准。",
            "AI 輸出明確標 fact/inference/unknown，附原始 evidence 與時間。",
            "任何 remediation 有 scope、idempotency、rollback、watch 和 audit。",
            "Agent timeout 或不可用時，原始 alert/runbook 和人類流程仍可運作。",
        ],
        """
優秀 troubleshooter 的核心不是記得所有故障，而是快速建立可驗證模型並保護 evidence。AI 可以擴大記憶與搜尋，但 production judgment 仍取決於當前系統、變更與使用者影響。健康 on-call 的終點是事件逐步減少、更多人能安全處理，而非某位英雄恢復得越來越快。
""",
        [
            "挑一個歷史 incident，重建 scope、timeline、hypotheses、tests、mitigation。",
            "執行 hypothesis ranking，加入一個高支持但高風險 production test。",
            "檢查十個 pages 是否 actionable、能否由一般 on-call 依 runbook處理。",
            "讓 AI 調查一段合成 telemetry，評分 evidence links、unknowns 和過度推論。",
        ],
        [
            ("Troubleshooting 第一個技術問題通常是什麼？", "確認使用者 impact 和 scope：哪些 journeys、regions、versions、tenants、時間受影響，先避免在錯誤範圍猜根因。"),
            ("Mitigation 與 root cause 有何差別？", "Mitigation 先恢復或限制傷害；root cause 分析解釋事故條件並防止再發。可先 rollback，再慢慢找完整原因。"),
            ("為何一次只改一個變數？", "保留因果辨識；多項同時改變，即使恢復也不知道何者有效，且可能引入新風險。"),
            ("健康 on-call 需要哪些組織條件？", "可控 page 量、actionable alerts、訓練/shadow、backup、runbooks、合理輪值、事故後改善和休息。"),
            ("AI incident summary 最大風險？", "把時間相關誤寫成因果、遺漏 conflicting evidence，生成過度完整單一敘事；需附來源與 unknowns。"),
            ("Read-only-first 為何重要？", "先建立模型和 evidence，避免 agent 誤判直接改 production；低風險可累積自治 evidence。"),
            ("什麼表示 troubleshooting 系統正在改善？", "MTTD/MTTR、重複 pages、升級到單一 expert 和 unsafe actions 下降，runbook coverage 與一般 on-call 成功率提升。"),
        ],
        ["sre-oncall", "sre-troubleshooting", "sre-alerting", "google-agentic-sre"],
    ),
    C(
        44,
        "Emergency Response 與 Incident Command",
        "事故擴大時，如何避免所有人同時操作、資訊爆炸、決策權模糊和利害關係人失聯？",
        "進階",
        "建立 severity、Incident Commander、Operations、Communication、Planning 與明確交班。",
        ["incident-command", "ownership", "feedback", "least-privilege"],
        """
大型事故的技術問題常被協作問題放大：多人同時改 production、重要資訊散在私訊、leader 一邊 debug 一邊回管理層、沒人追 action。Incident command 將決策、操作、溝通與記錄分離，讓有限認知資源用在降低使用者傷害。
""",
        """
全區 checkout outage 時，十位工程師同時進 dashboard、兩人各自 rollback 不同版本、客服沒有 ETA、管理者不斷私訊值班者。宣告 incident、指定 IC/ops/comms/scribe、建立單一 channel 和 action log 後，系統才能有序恢復。
""",
        r"""
detect / page
   ↓ severity assessment
declare incident + single coordination channel
   ↓
Incident Commander ── priorities / decisions / role assignment
Operations Lead ───── technical actions / verification
Communications ────── users / support / leadership updates
Scribe / Planning ─── timeline / hypotheses / next actions / handoff
   ↓
mitigate → verify → watch → resolve → review
""",
        """
先定 severity 和 declaration threshold；寧可早宣告後降級，不要等資訊完整。IC 不必是最懂技術的人，其責任是維持共同目標、分配角色、控制 work in progress、批准高風險 action 和定期重評。Technical experts 放在 operations 才能專心調查。

Communication 是 mitigation 的一部分。使用者需要影響與 workaround，support 需要一致訊息，領導層需要節奏而不是打斷 operator。更新要標記已知、未知、下一次時間，避免猜測 ETA。Action log 記錄誰、何時、做什麼、結果和 rollback。

Emergency access 要預先設計：break-glass 身份、短期權限、雙人核准和完整 audit。事故不是取消控制的理由，而是使用已演練的快速控制。長事故要輪班、交班和休息；疲勞本身會產生第二次事故。
""",
        [
            "定義 severity/declaration，建立單一 incident channel、document 和 roles。",
            "IC 管 priorities/decisions；ops 執行；comms 更新；scribe 保存 timeline。",
            "每個 mutation 有 owner、預期、結果、rollback 和同時操作限制。",
            "使用預先演練 break-glass、短期最小權限和 audit。",
            "定期 update/reassess，長事故安排輪班、handoff、watch 和結案條件。",
        ],
        "範例是 incident action log state machine，防止未指派或未驗證 action 被當成完成。",
        r"""
from dataclasses import dataclass

@dataclass
class Action:
    description: str
    owner: str
    status: str = "proposed"
    result: str = ""

ALLOWED = {
    "proposed": {"approved", "rejected"},
    "approved": {"running", "cancelled"},
    "running": {"verified", "failed", "rolled-back"},
}

def transition(action: Action, new_status: str, result: str = "") -> None:
    if new_status not in ALLOWED.get(action.status, set()):
        raise ValueError(f"invalid transition {action.status}->{new_status}")
    action.status = new_status
    action.result = result
""",
        [
            "Action 需要 owner，避免聊天室建議被誤以為有人執行。",
            "Proposed→approved 分離主意與已授權 production action。",
            "Running 不能直接標完成，必須 verified 或記錄 failed/rollback。",
            "真實 log 還要 timestamp、approver、scope、commands、evidence links。",
        ],
        [
            "最懂技術者同時當 IC/ops/comms，形成認知瓶頸。",
            "每個人都能自由 mutation，操作互相覆蓋且無法歸因。",
            "過早宣布單一 root cause，團隊忽略矛盾 evidence。",
            "狀態更新沒有固定節奏，support/leadership 反覆打斷 operators。",
        ],
        """
AI 可以擔任 scribe、timeline builder、translation、status draft 和 evidence retrieval assistant，讓人專注決策；它不適合取代 Incident Commander 或自主接受不可逆風險。AI-specific incidents 還可能包含 prompt injection、model/provider regression、資料洩漏和 tool misuse，需擴充 severity、containment 與 evidence preservation。
""",
        [
            "讓 AI 自動整理 action log、決策、evidence 和 unresolved questions。",
            "用 agent 草擬不同 audience 的 status update，由 comms owner 核准。",
            "請 AI 搜尋 runbooks/owners/similar incidents，維持單一 incident context。",
            "讓 AI 對 tool/model actions 建 timeline，支援 AI-specific containment。",
        ],
        [
            "AI 不擔任 IC、不自行宣告 root cause/resolution 或發布外部訊息。",
            "Production mutation 仍走 identity、approval、bounds、audit 和 rollback。",
            "Incident prompt/context 視為敏感資料，限制模型、retention 和 access。",
            "保存 model/instruction/tool trace，containment 後防止 evidence 被覆蓋。",
        ],
        """
Incident command 的價值在於降低協作熵，而非增加頭銜。小事故可一人兼任，規模擴大就拆角色。AI 最適合接手高頻資訊整理，不能接手價值衝突、風險接受與人員照顧。一次成功恢復也要問是否因英雄運氣，而非可重複系統。
""",
        [
            "為一個歷史事故重新分配 IC、ops、comms、scribe，找角色衝突。",
            "執行 action state machine，測未 approved 直接 running 等非法 transition。",
            "寫 status update 模板：impact、known、mitigation、next update、unknown。",
            "設計 AI incident containment：停 model/tool、保留 trace、切 fallback、通知 owners。",
        ],
        [
            ("IC 為何不一定是最資深技術者？", "IC 管目標、角色、決策和協作；最深 expert 放 operations 能專注診斷，避免同時承擔溝通與管理。"),
            ("何時應宣告 incident？", "影響跨團隊、severity 不明但可能擴大、需要多角色協作或高風險操作時；可早宣告再降級。"),
            ("Action log 最少記什麼？", "時間、description、owner、approver、預期、scope、結果、evidence 和 rollback，讓操作可協調與重建。"),
            ("Communication 為何是 mitigation？", "提供 workaround、降低重複請求與支援混亂，保護 operators 不被反覆打斷並維持信任。"),
            ("Break-glass 為何仍需 control？", "事故提高 urgency 也提高誤操作風險；使用預先設計的短期權限、雙人核准和 audit，而非共享 root。"),
            ("AI 最適合哪個 incident role？", "Scribe/assistant：整理 timeline、查資料、草擬 communication；人類保留 IC、risk 和外部承諾。"),
            ("AI-specific incident 要保存哪些 evidence？", "Model/version、prompts/instructions、retrieval、tool calls、identities、policy decisions、outputs 和 affected data。"),
        ],
        ["sre-emergency", "sre-incident", "google-agentic-sre", "microsoft-ai-incident"],
    ),
    C(
        45,
        "Blameless Postmortem、Outage Tracking 與 Action Quality",
        "事故結束後，如何避免報告變成找戰犯、流水帳，或列出永遠不會完成的 action items？",
        "進階",
        "從 impact、timeline、contributing conditions、decision context 到可驗證改善，建立組織學習迴路。",
        ["postmortem", "feedback", "ownership", "goal-signal-metric"],
        """
事故若只歸因「工程師按錯按鈕」，下一位合理操作的人仍會遇到相同系統。若完全不談 decision 和 responsibility，又無法改善 control。Blameless 的目的是理解當時資訊、工具、incentives 和防線為何讓行動看似合理，並建立更強系統。
""",
        """
部署造成 outage，報告寫「操作員未仔細確認」。深入後發現 staging 與 production 按鈕相鄰、無 canary、rollback 需 20 分鐘、alert 延遲。改善 UI、權限、progressive rollout 和 alert 比要求大家更小心可重複。
""",
        r"""
impact / SLO / affected users
        ↓
evidence-based timeline
        ↓
what happened? detection / response / recovery
        ↓
contributing conditions:
design · process · tools · knowledge · incentives · luck
        ↓
what went well / made worse / where defenses failed
        ↓
actions ranked by risk reduction
owner + deadline + verification + durable tracking
        ↓
fleet trends / recurring themes → roadmap / platform / policy
""",
        """
Postmortem 先準確描述 impact 與 timeline，再分析 contributing factors；避免單一 root cause，因複雜事故通常需要多個條件同時存在。記錄 decisions based on information available，不用事後全知視角評判。What went well 能保留有效防線，near misses 和 luck 也要記錄。

Action item 要改變系統：消除 hazard、加自動 guard、縮小 blast radius、改善 detection/response 或建立演練。每項有 owner、deadline、priority、verification 和 tracking；「提醒大家」「多加測試」太模糊。修文件可能必要，但高風險問題只靠文件通常較弱。

單一 postmortem 之外要追 outage corpus：impact、duration、detection、cause categories、repeat、action completion 和 recurring dependencies。分類不是追責，而是發現跨團隊槓桿，例如 deployment、quota 或 identity 平台反覆出問題。
""",
        [
            "以 user/SLO 定義 impact，從可信 evidence 建 timeline 和未知。",
            "分析多個 contributing conditions、failed defenses、decision context 和 luck。",
            "Actions 依風險降低排序，具有 owner、deadline、verification 和追蹤。",
            "Review action 完成不是 ticket closed，而是 signal/experiment 證明改善。",
            "聚合 outage corpus 找 recurring themes，投資跨組織 platform/policy。",
        ],
        "範例檢查 action item 是否具備最小可執行欄位，防止報告只有願望。",
        r"""
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class FollowUp:
    action: str
    owner: str
    due: date
    verification: str
    risk_reduction: str

def actionable(item: FollowUp) -> bool:
    return all([
        item.action.strip(),
        item.owner.strip(),
        item.verification.strip(),
        item.risk_reduction.strip(),
    ])
""",
        [
            "Owner 和 due 讓工作進入真實 capacity/priority，而非留在文末。",
            "Verification 說明如何知道改善生效，例如 game day 或新 SLI。",
            "Risk reduction 將 action 連回事故條件，避免無關 backlog。",
            "完整欄位仍不代表 action 足夠強，reviewer 要比較 hierarchy of controls。",
        ],
        [
            "把最後觸發者當 root cause，忽略讓單一操作可造成大傷害的系統。",
            "Action 全是文件/訓練，沒有自動 guard、blast-radius 或 design 改善。",
            "報告完成後 actions 無 priority/capacity，數月後全部過期。",
            "Outage 分類被用於團隊排名，造成少報、降 severity 和失去學習資料。",
        ],
        """
AI 可從 logs/chat/actions 草擬 timeline、聚類 outage themes 和生成 action 候選，但也容易補齊缺失事件、過早歸因或把個人語句誤讀成責任。它應保留 provenance、區分 evidence/inference，並由參與者 review。AI 也不應決定人事後果；其輸出本身可能是 incident evidence。
""",
        [
            "讓 AI 從多來源建立 timestamped draft，逐項附 source 和 confidence。",
            "用 agent 將 actions 按 eliminate/guard/detect/respond/document 分類。",
            "請 AI 聚類季度 incidents，找 recurring dependency、tool 和 process patterns。",
            "讓 agent 把完成 action 連回新 test、policy、dashboard 或 game-day evidence。",
        ],
        [
            "AI 不得虛構缺失 timeline；未知保留 unknown，conflict 同時呈現。",
            "敏感 incident data 限定批准模型、participants 和 retention。",
            "Root cause、責任、人事與 closure 由人類 committee/owners 判斷。",
            "Generated actions 不能自動建立 destructive changes；先經風險與 owner review。",
        ],
        """
Postmortem 品質不在文字漂亮，而在組織模型是否更新。專家關心 action hierarchy：刪除危險比提醒更強，automatic guard 比 checklist 更穩；也接受有些事故風險不值得完全消除，但應把接受理由與 SLO/cost 寫清楚。Blameless 與 accountability 可以同時存在。
""",
        [
            "挑一份舊 postmortem，將 root-cause 單句改成 contributing conditions graph。",
            "執行 action validator，加入 priority、status、evidence link 和 overdue check。",
            "把十個 actions 分類為 eliminate/guard/detect/respond/document，找過度弱項。",
            "讓 AI 草擬 timeline，人工標出推論、缺失與來源錯誤。",
        ],
        [
            ("Blameless 是否表示沒有人負責？", "不是。保留事實、decision ownership 和必要 accountability，但不把個人缺陷當完整解釋，專注改變系統條件。"),
            ("為何避免單一 root cause？", "複雜事故通常由多個 design、process、tool、knowledge 和環境條件共同形成；只修最後觸發點容易再發。"),
            ("好 action item 最少需要什麼？", "具體改變、owner、期限、風險連結、verification 和 durable tracking，且優先選較強 control。"),
            ("Ticket closed 為何不等於改善完成？", "Code/文件合併不代表防線有效；需 test、game day、SLI 或後續 evidence 驗證。"),
            ("Outage tracking 的組織價值？", "跨事故找到 recurring themes 和高槓桿平台投資，而非每隊只修局部表象。"),
            ("AI timeline 最大風險？", "把缺失補成合理故事、時間相關寫成因果、忽略 conflicting sources；需 provenance/confidence 和參與者 review。"),
            ("何時可以合理接受某事故風險？", "消除成本高於使用者/商業收益，且有量測、mitigation、owner 和明確風險接受；不是因 backlog 忙就默認。"),
        ],
        ["sre-postmortem", "sre-outages", "sre-simplicity", "microsoft-ai-incident"],
    ),
    C(
        46,
        "Game Day、Disaster Recovery 與 Reliable Launch",
        "如何在真正事故前證明 backup、failover、runbook、on-call 和 launch plan 能共同工作？",
        "進階",
        "以 hypothesis-driven exercise 驗證技術與人，將發現轉成 launch gate、automation 和 design 改善。",
        ["game-day", "canary", "production", "invariant"],
        """
文件、架構圖和單元測試無法證明真實權限、跨團隊協作、供應商、backup 和時間壓力下仍能恢復。Game day 在受控範圍注入故障；disaster recovery 驗證大範圍失效與資料恢復；launch review 則在新風險進入前檢查 readiness。
""",
        """
團隊相信 region failover 只需十分鐘，演練時才發現 DNS TTL、database promotion、secrets 和客服流程未對齊，實際要兩小時。這個安全失敗提供了 production outage 前最便宜的改善機會。
""",
        r"""
critical journey / launch risk
        ↓
hypothesis + success criteria (SLO / RTO / RPO / invariant)
        ↓
scope / blast radius / approvals / abort / rollback
        ↓
observe baseline
        ↓
inject failure or rehearse procedure
        ↓
detect → page → coordinate → mitigate → recover → verify
        ↓
gaps → owners/actions → re-test
        ↓
launch checklist / readiness evidence
""",
        """
演練從 hypothesis 開始，例如「失去單一區時 checkout 在 15 分鐘內恢復，無資料遺失且 error budget 消耗小於 X」。定義 scope、participants、customer impact、abort、rollback 和 observers。先桌上推演，再 staging，再低風險 production，逐步增加 fidelity。

DR 需同時驗證 control plane、data plane 和人。Backup restore、DNS、identity、secrets、quota、dependencies、communications 和 support 都可能是關鍵路徑。RTO/RPO 要以實測而非文件估計。演練也看是否只有某 expert 能完成。

Reliable launch review 依風險分級，檢查 ownership、SLO/capacity、monitoring/alerting、rollout/rollback、data migration、security/privacy、on-call/runbook 和 dependency readiness。Checklist 不是 approval theater；缺項要對應風險、owner 或正式 exception。
""",
        [
            "從 critical journey/launch risk 定義 hypothesis、RTO/RPO/SLO 和 invariant。",
            "由 tabletop→staging→bounded production 漸進提高 fidelity。",
            "事前確認 scope、approvals、abort、rollback、communication 和觀察者。",
            "演練 detection、roles、permissions、dependencies、data restore 與使用者 communication。",
            "將 gaps 轉有 owner/verification actions，修正後重演並更新 launch gate。",
        ],
        "範例驗證演練結果是否符合 RTO/RPO 與資料 invariant，而不是只記錄『failover 成功』。",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class DrillResult:
    recovery_minutes: int
    data_loss_minutes: int
    duplicate_transactions: int
    pages_actionable: bool

def passed(result: DrillResult, rto: int, rpo: int) -> list[str]:
    failures = []
    if result.recovery_minutes > rto:
        failures.append("RTO exceeded")
    if result.data_loss_minutes > rpo:
        failures.append("RPO exceeded")
    if result.duplicate_transactions:
        failures.append("transaction invariant violated")
    if not result.pages_actionable:
        failures.append("alerting/runbook gap")
    return failures
""",
        [
            "Recovery 成功仍可能超過承諾時間，需與 RTO 比較。",
            "Data loss 與 duplicate 是不同 integrity dimensions。",
            "Actionable pages 驗證人類 control loop，不只測基礎設施。",
            "Failure list 直接轉成 actions 和下一次 drill acceptance criteria。",
        ],
        [
            "無 hypothesis 的 chaos 只製造中斷，無法判斷學到什麼。",
            "演練永遠由原設計者執行，無法發現知識與權限單點。",
            "只測 failover、不測 failback/reconciliation，恢復後留下分裂 state。",
            "Launch checklist 所有項目都可口頭豁免，實際沒有 gate。",
        ],
        """
AI launch 增加 model/provider regression、prompt injection、RAG poisoning、tool excessive agency、成本暴增和不可重現品質等場景。演練應包含切換模型、停用 tools、fallback、trace preservation 和安全 containment。AI 可產生 scenario、擔任模擬使用者或 scribe，但 production fault scope 和 abort 由 deterministic controls。
""",
        [
            "讓 AI 從 architecture/threat model 產生 failure scenarios 和 hidden dependencies。",
            "用 agent 模擬使用者、support 或 dependency response，增加演練廣度。",
            "請 AI 即時整理 timeline/gaps，不參與 production mutation。",
            "讓 agent 比較多次 drill，追蹤 RTO/RPO、action completion 和 recurring gaps。",
        ],
        [
            "Production injection 使用 allowlisted faults、硬 scope、time limit、abort 和人類 IC。",
            "AI scenario 不得包含未批准 secrets/data 或鼓勵繞過 control。",
            "AI-specific drill 保存 model/prompt/tool trace，並驗證 deterministic fallback。",
            "Launch exception 有具名 risk owner、期限、補償 control 和 follow-up。",
        ],
        """
Game day 是把未知變成 backlog 的機器。成熟組織不以「沒有發現問題」為成功，反而希望在安全環境發現真缺口。AI 能擴展 scenario 和觀察能力，但若基本 restore、owner、SLO 都未建立，增加更花俏的 chaos 沒有意義。
""",
        [
            "為 region failure 寫 hypothesis、RTO/RPO、scope、abort、roles 和 verification。",
            "執行 drill validator，加入 failback/reconciliation 與 communication 指標。",
            "為新服務完成 launch checklist，將每個缺項連到 risk/owner。",
            "設計 AI-specific game day：provider outage、prompt injection、tool misuse、fallback。",
        ],
        [
            ("Game day 與隨機 chaos 差別？", "Game day 有明確 hypothesis、success criteria、scope、abort、observation 和 follow-up；不是為破壞而破壞。"),
            ("RTO 與 RPO 如何驗證？", "實際量從故障到恢復時間，以及恢復後遺失/需重建的資料時間，不能只讀文件設定。"),
            ("為何要測 failback？", "Failover 後資料、traffic 和 ownership 可能分裂；返回正常狀態與 reconciliation 也可能造成事故。"),
            ("Launch checklist 如何避免形式化？", "每項連到具體風險與 evidence，缺項有 owner/exception，並在 incident 後更新；不是全部勾選即可。"),
            ("誰不應總是執行演練？", "只有原作者/最資深 expert；應讓一般 on-call、跨團隊和 support參與，測知識與權限。"),
            ("AI-specific drill 需要哪些場景？", "模型/provider 退化、prompt injection、RAG poisoning、tool misuse、cost spike、trace/kill-switch/fallback。"),
            ("演練成功的真正標準？", "在可控傷害下取得可行動新 evidence，完成改善並重測；不是報表寫『所有系統正常』。"),
        ],
        ["sre-reliability-testing", "sre-launch", "microsoft-ai-incident", "owasp-llm"],
    ),
    C(
        47,
        "AI-ready Engineering Organization 與 SRE Engagement",
        "如何讓 AI 從個人工具變成可治理、可量測、可擴張的組織能力，而不形成 shadow systems？",
        "進階",
        "建立 policy、data/context、platform、eval、identity、skills、ownership 和自治成熟度模型。",
        ["scale", "ownership", "least-privilege", "eval"],
        """
零散導入 AI 時，每人使用不同模型、把資料貼到不同服務、重複建立 agents，組織看不見風險也無法共享成果。只發布禁令又沒有安全替代，使用需求會轉入 shadow AI。AI-ready 不是購買 license，而是讓使用者能在低 friction guardrails 內取得可靠 context、tools 和 feedback。
""",
        """
十個團隊各自做 incident bot，使用個人 token、不同 log 權限和未版本化 prompts。中央平台提供 approved models、workload identity、tool broker、audit、eval harness 和 reusable incident skill；domain teams 維護各自 runbook、SLO 和 action policy。
""",
        r"""
AI policy / risk tiers / approved use
        ↓
identity + data classification + model gateway
        ↓
context layer: canonical docs / code / telemetry / ACL
        ↓
tool platform: schemas / sandbox / approvals / audit / budgets
        ↓
skills / workflows owned by domain teams
        ↓
eval + observability + incidents + user feedback
        ↓
autonomy maturity and portfolio investment

central platform controls mechanisms
local owners control domain intent and risk
""",
        """
組織層先定義允許、需審查和禁止 use cases，依資料、side effect 和影響分 risk tiers。政策要清楚回答資料能否送入模型、輸出如何 review、哪些 actions 需批准、retention 和 incident reporting。提供 approved paved road，否則規則難以執行。

平台層提供 model gateway、identity、ACL-aware context、sandbox、tool schemas、budgets、audit、eval 和 observability。Domain teams 擁有 prompt/skill、knowledge sources、acceptance criteria 和 on-call。中央不應成為所有 workflow bottleneck，local 也不能自行繞過共用 security controls。

成熟度可從 assistive chat、scoped agent、agent-created PR、bounded merge、read-only SRE、approved mutation 到低風險 closed loop。每級以風險、eval、歷史 precision、reversibility 和 incident record取得，而非 vendor feature。Portfolio metrics 看 user value、flow、quality、security、cost 和 human experience。
""",
        [
            "建立 risk-tiered AI policy、資料分級、approved models 和透明使用規則。",
            "提供 model/context/tool 平台：identity、ACL、sandbox、budget、audit、eval。",
            "中央維護控制機制，domain owners 維護 workflow、knowledge、SLO 和 action policy。",
            "以成熟度梯逐步授權，每級有 entry/exit evidence 和 kill switch。",
            "量 outcome、rework、stability、security、cost、equity 和 developer experience。",
        ],
        "範例用 risk tier 決定最低 control。規則應在 tool gateway 執行，而非只放在政策文件。",
        r"""
CONTROLS = {
    "assist": {"human_review"},
    "code-write": {"sandbox", "tests", "independent_review", "audit"},
    "prod-read": {"workload_identity", "acl", "audit", "redaction"},
    "prod-write": {
        "workload_identity", "least_privilege", "approval",
        "idempotency", "rollback", "audit", "kill_switch",
    },
}

def required_controls(use_case: str) -> set[str]:
    if use_case not in CONTROLS:
        raise ValueError("unclassified AI use case")
    return CONTROLS[use_case]
""",
        [
            "Unknown use case fail closed，先分類而不是默認最低控制。",
            "Production read 仍需 ACL/redaction，唯讀不代表無資料風險。",
            "Production write 加入 approval、idempotency、rollback 和 kill switch。",
            "真實 controls 還依資料敏感度、impact、reversibility 和 jurisdiction 調整。",
        ],
        [
            "中央平台沒有 user research，approved path 太難用而促成 shadow AI。",
            "每個 team 自建 tool auth/audit，產生不一致和重複安全漏洞。",
            "只量 license adoption/accepted lines，忽略 rework、incidents 和成本。",
            "Autonomy 因 vendor demo 直接升級，沒有 representative eval 和 rollback。",
        ],
        """
業界 AI 工程的共同方向是把 AI 當 sociotechnical change：明確政策、健康可存取資料、成熟 version control、小批次、使用者導向和內部平台缺一不可。Coding/SRE agent 需要 context engineering、deterministic verification、least privilege、eval 和 observability。最重要的管理實務是將 AI 產出責任留給現有 owners，而非建立無人負責的模型層。
""",
        [
            "用 AI 分析重複 workflows，找 reusable skills/tools 而非只建聊天介面。",
            "讓 platform 提供 eval templates、safe sandboxes 和 model routing，自助落地。",
            "建立 AI champions/community 分享 cases、failures、security 和 domain patterns。",
            "用 agent 生成 adoption support 與 docs，但由政策/安全 owners 核准。",
        ],
        [
            "所有 agents 有 service catalog entry、owner、risk tier、data sources、tools 和 on-call。",
            "Tool gateway 統一 identity、ACL、approval、budgets、audit 和 emergency revoke。",
            "Eval/observability 與模型版本綁定，重大更新走 shadow/canary。",
            "人事、高影響決策、不可逆 production/data action 保留人類 authority。",
        ],
        """
組織不需要一次到達全自治。專家會先選有清楚 oracle、低 blast radius、高重複成本的 use case建立信任，再擴張。若基本 version control、tests、docs 和 SLO 不成熟，AI 會放大缺陷；因此 AI roadmap 其實也是改善工程基礎的 roadmap。
""",
        [
            "盤點所有 AI use cases：owner、data、model、tools、risk、eval、incident path。",
            "執行 control mapping，新增 high-impact decision 和 public-content 類別。",
            "畫中央平台/local domain responsibility，找 ownership gap 和 bottleneck。",
            "制定六個月成熟度路線，每級含 use cases、controls、metrics 和退出條件。",
        ],
        [
            ("AI-ready organization 不等於什麼？", "不等於全員購買 chatbot 或追 adoption；它需要 policy、data/context、platform、skills、eval、ownership 和安全 feedback。"),
            ("為何純禁令容易失敗？", "真實工作需求仍存在，成員會使用不可見工具；需提供低 friction、功能足夠的 approved paved road。"),
            ("中央平台與 domain team 如何分工？", "中央做 identity/model/tool/eval/audit 機制；domain 定義 intent、knowledge、SLO、風險與 action policy。"),
            ("Autonomy maturity 應依什麼升級？", "Representative eval、歷史 precision、可逆性、blast radius、controls、incident record 和 human trust，而非功能可用。"),
            ("唯讀 agent 為何仍有風險？", "可洩漏敏感資料、跨 tenant 存取、產生誤導建議或高成本查詢，需要 ACL、redaction、audit 和 quota。"),
            ("AI portfolio 應量哪些 outcome？", "User/business value、flow、rework/quality、stability/security、cost、equity 和 human experience，不只採用。"),
            ("何時不應優先建 agent？", "Problem deterministic 可用普通 automation、沒有可信 context/oracle、流程本身應刪除，或 blast radius 無法控制時。"),
        ],
        ["dora-ai", "openai-codex", "google-agentic-sre", "sre-engagement"],
    ),
    C(
        48,
        "Capstone：從 Commit 到可靠服務的完整 Operating System",
        "如何把前 47 章組成一條可執行路徑，設計、發布並營運一個含 AI 助手的服務？",
        "綜合實戰",
        "完成一個 end-to-end blueprint：需求、contract、code、tests、CI/CD、SLO、incident、postmortem 與 earned autonomy。",
        ["lifecycle", "feedback", "slo", "agent", "provenance"],
        """
單獨知道 review、SLO、retry 或 agent guardrail 不代表能設計整體系統。真正困難在於它們如何交接：需求如何成為 test oracle，build evidence 如何跟 artifact 進 production，SLO 如何控制 rollout，incident 如何生成下一個 test，AI 如何在相同 ownership 和 control 中工作。
""",
        """
Capstone 建立 Quote Service：提供商品報價、依賴 Catalog、寫入 quote ledger，另有 coding agent 協助變更與 SRE assistant 調查。需求是 99.9% availability、p99 300ms、報價不可為負、重試不可產生重複 quote，AI 不得直接無批准修改 production。
""",
        r"""
USER / PRODUCT
  ↓ requirements + SLO + threat model
DESIGN
  ↓ API/schema + ADR + failure model + ownership
DEVELOP
  ↓ small commits + style + review + tests
BUILD / CI
  ↓ hermetic artifact + provenance + gates
DELIVER
  ↓ canary + SLO burn + rollback + flag cleanup
OPERATE
  ↓ observability + capacity + alerts + on-call
INCIDENT
  ↓ command + mitigation + evidence + communication
LEARN
  ↓ postmortem + test/rule/runbook/platform improvement
  └──────────────────────────────────────────────→ DESIGN

AI layer:
bounded context → sandbox/tools → deterministic evidence
→ independent review → staged autonomy → audit/evals
""",
        """
第一階段定義 product contract：valid input、quote semantics、error codes、idempotency、privacy 和 SLI。Design doc 畫 request/dependency/data flow、timeout/retry、overload、migration 和 ownership；ADR 記錄為何選同步 catalog + stale cache fallback。Threat model 包含外部輸入與 agent tools。

第二階段建立 change system：formatter/linter、unit/property/contract/integration tests、hermetic build、dependency lock/provenance、risk-based review 和 CI。Coding agent 只在 worktree 修改，完成條件由 tests/type/static/security 決定。Artifact build once，以 canary 依 error/latency/correctness SLI 漸進。

第三階段營運：dashboard 連 user journey、dependency、queue、version 和 agent trace；burn-rate alert 有 runbook；capacity 保留 zone failure；load shedding 保護 quote API。SRE assistant 預設唯讀，建立 incident brief；rollback 需批准。事故後 postmortem 將漏掉的 failure 變成 test、policy、alert 或簡化設計，閉合 loop。
""",
        [
            "定義需求、non-goals、API/invariants、SLI/SLO/error budget 和 owners。",
            "設計 dependencies、state、timeouts/retries、capacity、overload、security 和 migration。",
            "建立 tests/build/CI/review，產出 immutable artifact、SBOM/provenance。",
            "以 canary/SLO/rollback/feature cleanup 發布，保存 change event。",
            "營運 dashboard/alerts/on-call/incident/postmortem，讓教訓返回 code與平台。",
            "AI agent 使用 context、sandbox、tools、eval、least privilege、audit 和成熟度梯。",
        ],
        "這個最小 service core 展示 contract、idempotency、dependency timeout 和 invariant。完整 companion lab 會將它接到測試、SLO 和 incident simulation。",
        r"""
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Quote:
    quote_id: str
    sku: str
    quantity: int
    total: Decimal

class QuoteService:
    def __init__(self, catalog, ledger):
        self.catalog = catalog
        self.ledger = ledger

    def create(self, request_id: str, sku: str, quantity: int) -> Quote:
        if quantity <= 0:
            raise ValueError("INVALID_QUANTITY")
        if previous := self.ledger.get(request_id):
            return previous
        price = self.catalog.price(sku, timeout_seconds=0.15)
        total = price * quantity
        if total < 0:
            raise RuntimeError("PRICE_INVARIANT")
        quote = Quote(request_id, sku, quantity, total)
        return self.ledger.put_if_absent(request_id, quote)
""",
        [
            "Request ID 同時是 quote identity，retry 會讀回或原子建立同一結果。",
            "Catalog call 有明確 timeout，整體 handler 還需端到端 deadline/retry policy。",
            "Total non-negative 是 domain invariant，即使 dependency 回錯也 fail safe。",
            "`put_if_absent` 需要真資料層 unique/transaction contract，unit fake 與 real 共用 tests。",
            "Service 尚未處理 overload、telemetry 和 fallback；它們由外層 operating system補齊。",
        ],
        [
            "只完成 service code，沒有 deployment、SLO、owner 和 incident path。",
            "Coding agent 同時改 tests 和實作，將錯誤 behavior 固化成綠燈。",
            "Canary 只看 process health，錯價 invariant 沒有 user/business signal。",
            "AI-SRE assistant 取得過大 production 權限，誤判時 blast radius 無界。",
            "Postmortem actions 沒有 capacity 和驗證，閉環在文件處中斷。",
        ],
        """
Capstone 的 AI 不是額外聊天框，而是兩條受控 workflow。Coding agent 讀 canonical design/contract，在 sandbox 實作並交付 evidence；SRE assistant 讀 ACL-filtered telemetry，區分 facts/inferences，提出唯讀驗證與批准後 remediation。兩者共享 identity、tool gateway、eval、audit 和 incident policy，且都不能修改自己的 guardrails。
""",
        [
            "Coding agent 先輸出 plan、affected contracts、tests 和 forbidden operations。",
            "獨立 reviewer agent從 requirement/ADR 檢查 diff，不共享生成過程的假設。",
            "SRE assistant 建 incident brief、timeline、hypotheses 和 evidence links。",
            "以 20 個 coding eval、20 個 incident eval、policy injection cases 做 release gate。",
            "觀測 agent quality、latency、cost、tool success、unsafe action 和 human takeover。",
        ],
        [
            "所有 AI actions 綁定 workload identity、scope、budgets、tool schema 和 audit。",
            "模型/skill更新走 eval、shadow、canary；不能直接替換 production behavior。",
            "Agent 無權修改 tests/policy/SLO 以自我通過，高風險操作 separation of duties。",
            "Deterministic fallback 能在模型/provider outage 時維持核心 quote journey。",
            "每次事故可立即 revoke identity、停 tools、保存 traces 並切回人工流程。",
        ],
        """
完整 engineering operating system 的目的不是堆齊所有流程，而是讓 evidence 以最低摩擦跟著 change 移動。小團隊可以使用較少工具，但 contract、ownership、可逆性和 feedback 不能消失；大型組織需要平台降低重複。AI 是否成熟，最終看它能否在不稀釋這些原則下縮短從 intent 到可信結果的時間。
""",
        [
            "寫 Quote Service design brief：goals/non-goals、contract、invariants、dependencies、owners。",
            "實作 fake/real ledger contract tests、catalog timeout、idempotency 和 property tests。",
            "建立 CI/CD blueprint、artifact provenance、canary health 和 error-budget policy。",
            "模擬 catalog latency→retry→overload incident，執行 IC、rollback、postmortem。",
            "設計 coding/SRE agents 的 context、tools、evals、risk tier 和 autonomy ladder。",
            "將 postmortem 的三個 actions 實際轉成 test、alert/policy 和 design simplification。",
        ],
        [
            ("Capstone 為何從 SLO/contract 開始而非先寫 code？", "它們定義使用者成功、invariants 和可接受風險，後續 tests、alerts、canary 和 agent acceptance 才有共同 oracle。"),
            ("Idempotency 應在哪一層保證？", "API 接收 stable request ID，service 重用結果，資料層以 unique/transaction 原子化，外部 side effects也傳同一 key；需端到端。"),
            ("Coding agent 和 reviewer agent 為何分離？", "降低共享同一 context/假設造成的盲點；reviewer從 requirement、contract 和風險建立獨立檢查。"),
            ("SRE assistant 為何預設唯讀？", "先累積 evidence 和 precision，限制誤判 blast radius；mutation 需成熟 eval、可逆 tools、approval 和 audit。"),
            ("Canary 應看哪些 signals？", "User availability/latency/correctness SLI、business invariant、resource/dependency、cohorts 和 version；不只 process up。"),
            ("Postmortem 如何真正閉環？", "Action 進 owner/priority，轉成可執行 control，經 test/game day/SLI驗證，並更新設計與平台。"),
            ("Startup 是否需要全部機制？", "不需相同工具規模，但需依風險保留核心：owner、contract、tests、可重現 release、基本 telemetry、rollback和事故學習。"),
            ("整本書最重要的一句話？", "讓每次 change 帶著與風險相稱、可追溯的 evidence 前進，並讓 production 的真實結果回到下一次設計。"),
        ],
        ["swe-preface", "sre-intro", "dora-ai", "google-agentic-sre", "openai-evals"],
    ),
]
