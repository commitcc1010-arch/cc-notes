"""Generate deterministic original mock exams from the chapter curriculum."""
from __future__ import annotations

from itertools import cycle

from aws_architect_model import MockQuestion, Topic


def _select(topics: list[Topic], prefix: str, count: int) -> list[tuple[Topic, str]]:
    eligible = [topic for topic in topics if any(task.startswith(prefix) for task in topic.tasks)]
    task_ids = sorted({task for topic in eligible for task in topic.tasks if task.startswith(prefix)})
    selected: list[tuple[Topic, str]] = []
    used: set[int] = set()
    for task in task_ids:
        candidate = next(
            (topic for topic in eligible if task in topic.tasks and topic.number not in used),
            next(topic for topic in eligible if task in topic.tasks),
        )
        selected.append((candidate, task))
        used.add(candidate.number)
    ordered = sorted(eligible, key=lambda topic: ((topic.number * 37) % 127, topic.number))
    for topic in cycle(ordered):
        if len(selected) >= count:
            break
        if topic.number in used and len(used) < len(eligible):
            continue
        matching = [task for task in topic.tasks if task.startswith(prefix)]
        selected.append((topic, matching[len(selected) % len(matching)]))
        used.add(topic.number)
    return selected


def _rotate(
    choices: list[str], explanations: list[str], correct: set[int], shift: int
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[int, ...]]:
    size = len(choices)
    shift %= size
    order = list(range(shift, size)) + list(range(shift))
    inverse = {old: new for new, old in enumerate(order)}
    return (
        tuple(choices[index] for index in order),
        tuple(explanations[index] for index in order),
        tuple(sorted(inverse[index] for index in correct)),
    )


def _question(
    number: int, exam: str, topic: Topic, variant: int, forced_task: str | None = None
) -> MockQuestion:
    multi = number % 5 == 0
    prefix = "SAA" if exam in {"Diagnostic", "SAA-C03"} else "SAP"
    task = forced_task or next(task for task in topic.tasks if task.startswith(prefix))
    level = {
        "Diagnostic": "這是一題基礎診斷，要求先辨識最重要的constraint，再以最少營運負擔滿足它",
        "SAA-C03": "以Associate層級作答：用最少營運負擔滿足目前workload限制",
        "SAP-C02 + announced C03 watchlist": (
            "以Professional層級作答：納入跨帳號或跨Region治理、降低變更風險，"
            "並保留可稽核的恢復路徑"
        ),
    }[exam]
    review_constraints = (
        "變更必須能逐步推出，且每一步都要有可觀測的rollback gate",
        "安全團隊要求權限與資料路徑都留下可稽核證據",
        "營運團隊不能依賴每次故障都由工程師手動介入",
        "財務團隊要求成本隨實際用量可解釋，而不是只看月末總帳",
        "尖峰流量不可讓同步依賴形成無界重試或連鎖過載",
        "單一Availability Zone故障時，核心business flow仍要持續",
        "資料擁有者要求先說清楚authoritative state與恢復順序",
        "架構審查要求列出答案翻轉時必須改變的constraint",
        "合規稽核要求control plane變更與data plane存取可以分別追蹤",
        "團隊要能用game day或failure injection驗證設計，而非只看部署成功",
        "既有client介面不宜大改，migration必須控制相容性風險",
        "方案必須明確限制blast radius，不能把所有環境放入同一故障邊界",
        "延遲目標看端到端percentile，不能只比較單一服務的平均值",
        "資料保護要求RTO與RPO分別量化，不能把backup直接等同可恢復",
        "流量與資料成長速度不確定，容量策略必須能被需求訊號驅動",
        "同一operation可能被重送，consumer必須保護business effect",
        "跨團隊共用能力要有清楚owner、quota與exception流程",
        "部署失敗時要能判斷最後正常狀態與第一個錯誤狀態",
        "敏感credential不可長期寫入程式、映像或人工runbook",
        "最終方案必須同時交代正常路徑、故障路徑與驗證證據",
    )
    review_constraint = review_constraints[(variant - 1) % len(review_constraints)]
    prompt = (
        f"一家公司正在處理以下情境：{topic.scenario} "
        f"主要問題是：{topic.problem}。{level}。此外，{review_constraint}。"
    )
    if multi:
        prompt += " 哪兩個動作應一起採用？（選兩項）"
        choices = [
            topic.decision,
            f"同時依「{topic.pattern}」建立界線、監控訊號與失敗後的恢復流程。",
            topic.alternative,
            f"先忽略限制並沿用現況；發生問題後再處理。這可能導致：{topic.failure}",
            "只增加更多容量或更昂貴的服務，不先確認瓶頸、資料語意與權限邊界。",
        ]
        explanations = [
            f"正確。這直接處理題目的主要限制：{topic.decision}",
            f"正確。第一個選項給出機制，本選項補足guardrail與可驗證性；通用原則是{topic.pattern}。",
            f"不選。這個替代方案在其他限制下可能合理，但本題仍存在缺口：{topic.alternative}",
            (
                f"不選。它保留已知failure mode：{topic.failure} "
                "而且沒有提供隔離、恢復或可觀測證據，無法證明business requirement已被滿足。"
            ),
            (
                "不選。單純堆容量或購買更昂貴服務，沒有先建立需求、資料語意、權限與"
                "failure contract；它可能增加固定成本，卻仍保留原始瓶頸與同一個故障邊界。"
            ),
        ]
        correct = {0, 1}
    else:
        prompt += " 哪一個方案最符合需求？"
        choices = [
            topic.decision,
            topic.alternative,
            f"維持現況，只在故障時人工處理；已知風險是：{topic.failure}",
            "選擇功能最多或價格最高的服務，不建立需求、state owner與failure boundary。",
        ]
        explanations = [
            f"正確。它直接將requirement映射到mechanism：{topic.decision} 通用pattern是「{topic.pattern}」。",
            f"不正確。它不是永遠錯，但只在不同constraint下成立：{topic.alternative}",
            f"不正確。題目要求可預期的架構行為，這會留下明確failure mode：{topic.failure}",
            "不正確。AWS題目比較的是需求與取捨，不是服務功能數量；此選項也無法證明安全、可靠、效能或成本目標。",
        ]
        correct = {0}
    rotated_choices, rotated_explanations, rotated_correct = _rotate(
        choices, explanations, correct, topic.number + variant
    )
    return MockQuestion(
        number=number,
        exam=exam,
        kind="Multiple response" if multi else "Multiple choice",
        prompt=prompt,
        choices=rotated_choices,
        answers=rotated_correct,
        explanations=rotated_explanations,
        task=task,
        chapter=topic.number,
        principle=topic.pattern,
    )


def build_mock_exams(topics: list[Topic]) -> dict[str, list[MockQuestion]]:
    diagnostic_topics = [
        (
            topic,
            [task for task in topic.tasks if task.startswith("SAA")][
                index % len([task for task in topic.tasks if task.startswith("SAA")])
            ],
        )
        for index, topic in enumerate(topics[:20])
    ]
    saa_topics = _select(topics, "SAA", 65)
    sap_topics = _select(topics, "SAP", 75)
    plans = (
        ("Diagnostic", diagnostic_topics),
        ("SAA-C03", saa_topics),
        ("SAP-C02 + announced C03 watchlist", sap_topics),
    )
    result: dict[str, list[MockQuestion]] = {}
    for exam, selected in plans:
        result[exam] = [
            _question(
                index,
                exam,
                topic,
                index,
                forced_task=task,
            )
            for index, (topic, task) in enumerate(selected, 1)
        ]
    return result
