#!/usr/bin/env python3
"""Build the self-contained AWS Solutions Architect SAA/SAP handbook."""
from __future__ import annotations

import csv
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aws_architect_content import (  # noqa: E402
    TOPIC_BY_NUMBER,
    TOPICS,
    blueprint,
    chapter_story,
    community_insight,
    labs,
    mechanics,
    mental_model,
    part_for,
    qas,
    term_cards,
    tradeoffs,
)
from aws_architect_deep_content import (  # noqa: E402
    comparison_rows,
    component_narrative,
    components,
    config_examples,
    key_takeaways,
    mechanism_walkthrough,
    practice_questions,
    scope_guide,
    special_explanation,
)
from aws_architect_external_coverage import (  # noqa: E402
    JAYENDRA_PATTERNS,
    OFFICIAL_OVERRIDE_NOTES,
)
from aws_architect_mock_exam import build_mock_exams  # noqa: E402
from aws_architect_model import PARTS, SOURCES, TASKS, Topic  # noqa: E402
from aws_architect_scope import SAA_SCOPE, SAP_SCOPE  # noqa: E402
from aws_architect_setting_guides import (  # noqa: E402
    chapter_glossary,
    setting_guides,
)
from aws_architect_survey_supplements import survey_supplements  # noqa: E402


OUTPUT = ROOT / "aws-solutions-architect-saa-sap.html"
SOURCE_DIR = ROOT / "AWS Solutions Architect"
JAYENDRA_INVENTORY = ROOT / "tools" / "jayendra_site_inventory.csv"
AS_OF = "2026-10-01"
MOCK_EXAMS = build_mock_exams(TOPICS)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"-+", "-", "".join(c if c.isalnum() else "-" for c in value)).strip("-")


def inline(value: str) -> str:
    escaped = html.escape(value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def paragraphs(value: str) -> str:
    return "".join(f"<p>{inline(chunk.strip())}</p>" for chunk in value.split("\n\n") if chunk.strip())


def topic_anchor(topic: Topic) -> str:
    return f"chapter-{topic.number:03d}-{slugify(topic.title)}"


def part_journey(active: int) -> str:
    rows = []
    for part in PARTS:
        css = " active" if part["part"] == active else ""
        rows.append(
            f'<span class="journey-node{css}"><b>{part["part"]}</b>'
            f'{html.escape(part["title"])}</span>'
        )
    return '<div class="journey-map" aria-label="全書學習地圖">' + "".join(rows) + "</div>"


def chapter_position(topic: Topic) -> str:
    def card(label: str, target: Topic | None, fallback: str) -> str:
        if target is None:
            return f'<div class="position-card muted"><span>{label}</span><strong>{fallback}</strong></div>'
        return (
            f'<a class="position-card" href="#{topic_anchor(target)}"><span>{label}</span>'
            f"<strong>{target.number:03d}. {html.escape(target.title)}</strong></a>"
        )

    return (
        '<div class="chapter-position">'
        + card("上一站", TOPIC_BY_NUMBER.get(topic.number - 1), "全書導讀")
        + f'<div class="position-card current"><span>你在這裡</span><strong>{topic.number:03d}. '
        f"{html.escape(topic.title)}</strong></div>"
        + card("下一站", TOPIC_BY_NUMBER.get(topic.number + 1), "模擬考與附錄")
        + "</div>"
    )


def render_term_cards(topic: Topic) -> str:
    rows = []
    for title, meaning, example in term_cards(topic):
        rows.append(
            '<section class="term-card">'
            f"<h3>{html.escape(title)}</h3>"
            f'<div><span>白話定義</span><p>{inline(meaning)}</p></div>'
            f'<div class="example"><span>具體例子／邊界</span><p>{inline(example)}</p></div>'
            "</section>"
        )
    return '<div class="term-grid">' + "".join(rows) + "</div>"


def render_chapter_story(topic: Topic) -> str:
    title, story_paragraphs = chapter_story(topic)
    return (
        '<section class="chapter-story">'
        f"<h2>{html.escape(title)}</h2>"
        + "".join(
            f'<p class="{"story-lead" if index == 0 else ""}">{inline(value)}</p>'
            for index, value in enumerate(story_paragraphs)
        )
        + "</section>"
    )


def render_key_takeaways(topic: Topic) -> str:
    return (
        '<ol class="takeaway-list">'
        + "".join(f"<li>{inline(item)}</li>" for item in key_takeaways(topic))
        + "</ol>"
    )


def render_chapter_glossary(topic: Topic) -> str:
    return (
        '<div class="concept-glossary">'
        + "".join(
            '<section class="concept-definition">'
            f"<h3>{html.escape(term)}</h3><p>{inline(definition)}</p>"
            "</section>"
            for term, definition in chapter_glossary(topic, components(topic))
        )
        + "</div>"
    )


def render_component_atlas(topic: Topic) -> str:
    cards = []
    for name, profile in components(topic):
        cards.append(
            '<section class="component-card">'
            f"<h3>{html.escape(name)}</h3>"
            f'<div><span>它負責什麼</span><p>{inline(profile.purpose)}</p></div>'
            f'<div><span>底層怎麼運作</span><p>{inline(profile.mechanism)}</p></div>'
            f'<div><span>必認得的設定</span><p>{inline(profile.config)}</p></div>'
            f'<div><span>選它的時機</span><p>{inline(profile.choose)}</p></div>'
            f'<div><span>何時替換</span><p>{inline(profile.replace)}</p></div>'
            "</section>"
        )
    return '<div class="component-grid">' + "".join(cards) + "</div>"


def render_setting_manual(topic: Topic) -> str:
    rendered_components = []
    for name, profile in components(topic):
        guides = "".join(
            '<article class="setting-guide">'
            f"<h4><code>{html.escape(guide.name)}</code></h4>"
            f'<div><span>控制什麼</span><p>{inline(guide.controls)}</p></div>'
            f'<div><span>何時需要</span><p>{inline(guide.when)}</p></div>'
            f'<div><span>怎麼設定／驗證</span><p>{inline(guide.configure)}</p></div>'
            f'<div><span>常見錯法</span><p>{inline(guide.pitfall)}</p></div>'
            "</article>"
            for guide in setting_guides(name, profile)
        )
        rendered_components.append(
            '<section class="setting-component">'
            f"<h3>{html.escape(name)}：逐項設定說明</h3>"
            f'<div class="setting-grid">{guides}</div>'
            "</section>"
        )
    return '<div class="setting-manual">' + "".join(rendered_components) + "</div>"


def render_special_explanation(topic: Topic) -> str:
    sections = special_explanation(topic)
    if not sections:
        return ""
    return (
        '<div class="deep-explanation">'
        + "".join(
            f"<section><h3>{html.escape(title)}</h3>{paragraphs(body)}</section>"
            for title, body in sections
        )
        + "</div>"
    )


def render_component_narrative(topic: Topic) -> str:
    return (
        '<div class="component-narrative">'
        + "".join(
            '<section class="story-section">'
            f"<h3>{html.escape(title)}</h3>{paragraphs(body)}"
            "</section>"
            for title, body in component_narrative(topic)
        )
        + "</div>"
    )


def render_component_role_map(topic: Topic) -> str:
    """Show component relationships without repeating full profile prose."""

    rows = []
    for index, (name, profile) in enumerate(components(topic)):
        relationship = (
            "本章主角：先判斷它是否直接承接題目的hard constraint。"
            if index == 0
            else "配合主角完成另一段責任，或在需求改變時成為替代方案。"
        )
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(name)}</strong></td>"
            f"<td>{inline(relationship)} {inline(profile.purpose)}</td>"
            f"<td>{inline(profile.mechanism)}</td>"
            f"<td>{inline(profile.replace)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-scroll"><table class="role-map"><thead><tr>'
        "<th>Component</th><th>它和其他角色的關係</th><th>流量／資料真的經過時發生什麼</th><th>這個角色的邊界</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_vpc_overview() -> str:
    return """
<figure class="network-overview" aria-labelledby="vpc-overview-caption">
  <div class="external-node"><strong>Internet 使用者</strong><span>例如瀏覽器連到公開 ALB</span></div>
  <div class="network-arrow">↓ HTTPS 443</div>
  <div class="gateway-node"><strong>Internet Gateway（IGW）</strong>
    <span>附掛在 VPC 邊界；不是放在 public 與 private subnet 中間</span></div>
  <div class="network-arrow">↓ 只有有效 route、public address 與安全規則同時成立才通</div>
  <div class="vpc-boundary">
    <div class="vpc-title">VPC 10.20.0.0/16</div>
    <div class="az-columns">
      <section class="az-column">
        <h3>Availability Zone A</h3>
        <div class="subnet public-subnet">
          <b>Public subnet A · 10.20.0.0/24</b>
          <div class="resource-row"><span>ALB node</span><span>NAT Gateway A</span></div>
          <code>public-rt: 0.0.0.0/0 → IGW</code>
        </div>
        <div class="network-arrow">↓ ALB SG 允許 app:8080</div>
        <div class="subnet private-subnet">
          <b>Private app subnet A · 10.20.10.0/24</b>
          <div class="resource-row"><span>EC2 app 10.20.10.25</span></div>
          <code>app-rt-a: 0.0.0.0/0 → NAT A</code>
        </div>
        <div class="network-arrow">↓ App SG 允許 DB:5432</div>
        <div class="subnet isolated-subnet">
          <b>Isolated DB subnet A · 10.20.20.0/24</b>
          <div class="resource-row"><span>RDS private address</span></div>
          <code>db-rt: 只有 10.20.0.0/16 → local</code>
        </div>
      </section>
      <section class="az-column secondary-az">
        <h3>Availability Zone B</h3>
        <div class="subnet public-subnet"><b>Public subnet B</b><span>ALB node + NAT Gateway B</span></div>
        <div class="subnet private-subnet"><b>Private app subnet B</b><span>另一組 application targets</span></div>
        <div class="subnet isolated-subnet"><b>Isolated DB subnet B</b><span>Multi-AZ database standby／replica</span></div>
        <p>第二個 AZ 不是裝飾：它避免 ALB、app 或 NAT 全部依賴同一個故障域。</p>
      </section>
    </div>
  </div>
  <figcaption id="vpc-overview-caption">
    綠色概念路徑是入站：Internet → IGW → ALB → app → database。
    App 主動出站則是：app → private route table → 同 AZ NAT → public route table → IGW。
  </figcaption>
</figure>
"""


def render_architecture_overview(topic: Topic) -> str:
    if topic.number == 12:
        return render_vpc_overview()
    return f'<pre class="architecture-diagram"><code>{html.escape(blueprint(topic))}</code></pre>'


def render_vpc_route_example() -> str:
    def route_table(title: str, attached: str, rows: tuple[tuple[str, str, str], ...]) -> str:
        body = "".join(
            f"<tr><td><code>{html.escape(destination)}</code></td>"
            f"<td><code>{html.escape(target)}</code></td><td>{inline(reason)}</td></tr>"
            for destination, target, reason in rows
        )
        return (
            '<section class="route-table-card">'
            f"<h3>{html.escape(title)}</h3><p><strong>關聯：</strong>{html.escape(attached)}</p>"
            '<table><thead><tr><th>Destination</th><th>Target</th><th>這列的效果</th></tr></thead>'
            f"<tbody>{body}</tbody></table></section>"
        )

    tables = (
        route_table(
            "public-rt",
            "Public subnet A／B",
            (
                ("10.20.0.0/16", "local", "VPC內部位址直接互通；這列由AWS自動建立。"),
                ("0.0.0.0/0", "igw-0123", "其餘IPv4目的地交給IGW；資源仍需public address才能直接和Internet交換IPv4流量。"),
            ),
        )
        + route_table(
            "app-rt-a",
            "Private app subnet A",
            (
                ("10.20.0.0/16", "local", "ALB、app與database在VPC內依private IP通訊。"),
                ("0.0.0.0/0", "nat-0abc (AZ A)", "App可主動連到Internet；外界不能藉此主動建立到private instance的連線。"),
            ),
        )
        + route_table(
            "db-rt",
            "Isolated database subnets",
            (
                ("10.20.0.0/16", "local", "Database只接受VPC內部路徑；沒有Internet default route。"),
            ),
        )
    )
    return (
        '<section class="worked-example vpc-worked-example">'
        "<h2>具體例子：三張 Route Table 實際長什麼樣子？</h2>"
        "<p>Route table不是一條從上讀到下的防火牆規則。每個封包拿自己的"
        "<code>destination IP</code>去找最精確的CIDR；例如目的地"
        "<code>10.20.20.15</code>會匹配<code>10.20.0.0/16 → local</code>，"
        "而目的地<code>1.1.1.1</code>才會落到<code>0.0.0.0/0</code>。</p>"
        f'<div class="route-table-grid">{tables}</div>'
        "<h3>跟著兩個封包走一次</h3>"
        '<ol class="packet-walk">'
        "<li><strong>使用者打開網站：</strong>DNS回傳internet-facing ALB位址；封包經IGW到ALB。"
        "ALB再以private IP把HTTP request送往app target，因此app instance不需要public IP。</li>"
        "<li><strong>App下載套件：</strong>目的地不在10.20.0.0/16，app-rt-a選default route到NAT A；"
        "NAT替換source address後，public-rt再把封包送到IGW。回應沿既有NAT state回到app。</li>"
        "<li><strong>App查資料庫：</strong>目的地10.20.20.15屬於VPC CIDR，最精確匹配是local；"
        "封包不會經過NAT或IGW。是否允許5432則由app與database security groups決定。</li>"
        "</ol>"
        '<aside class="callout misconception"><strong>最常見的誤會</strong>'
        "<p>IGW不是public subnet與private subnet之間的路由器。兩種subnet都在VPC裡；"
        "差別在各自關聯的route table、資源是否有public address，以及security policy。</p></aside>"
        "</section>"
    )


def render_worked_example(topic: Topic) -> str:
    if topic.number == 12:
        return render_vpc_route_example()
    return (
        '<section class="worked-example">'
        f"<h2>把全圖套進一個具體案例</h2><p><strong>場景：</strong>{inline(topic.scenario)}</p>"
        f"{render_flow(mechanism_walkthrough(topic))}"
        f'<aside class="callout example-result"><strong>這個案例如何驗收？</strong>'
        f"<p>正常結果必須能支持「{inline(topic.decision)}」。接著主動重現「{inline(topic.failure)}」，"
        "確認第一個壞掉的訊號、影響範圍與恢復owner。若需求改成"
        f"「{inline(topic.alternative)}」，就重新選型，不把舊答案硬調到能用。</p></aside></section>"
    )


def render_concept_reference(topic: Topic) -> str:
    return (
        '<details class="reference-box concept-reference">'
        "<summary>需要時再查：本章名詞與四個閱讀支點</summary><div>"
        "<p>第一次閱讀不必先背這一區。故事中遇到不熟悉的字，再回來查白話定義與邊界。</p>"
        f"{render_term_cards(topic)}"
        f"{render_chapter_glossary(topic)}"
        "</div></details>"
    )


def render_service_reference(topic: Topic) -> str:
    return (
        '<details class="reference-box service-reference">'
        "<summary>考前與實作時再查：Component 與逐項設定手冊</summary><div>"
        "<p>這裡保留完整設定深度，但不阻斷第一次閱讀。先理解上面的故事和資料流，"
        "再回來查每個欄位控制什麼、如何驗證，以及設錯會出現什麼症狀。</p>"
        f"{render_component_atlas(topic)}"
        f"{render_setting_manual(topic)}"
        "</div></details>"
    )


def render_config_examples(topic: Topic) -> str:
    blocks = []
    for example in config_examples(topic):
        blocks.append(
            '<section class="config-example">'
            f"<h3>{html.escape(example.title)}</h3>"
            f'<div class="code-label">{html.escape(example.language)}</div>'
            f'<pre class="config-code"><code>{html.escape(example.code)}</code></pre>'
            '<ol class="config-notes">'
            + "".join(f"<li>{inline(note)}</li>" for note in example.notes)
            + "</ol></section>"
        )
    return "".join(blocks)


def render_flow(items: tuple[str, ...], css: str = "flow-grid") -> str:
    return (
        f'<div class="{css}">'
        + "".join(
            f'<div class="flow-card"><span>{index}</span><p>{inline(item)}</p></div>'
            for index, item in enumerate(items, 1)
        )
        + "</div>"
    )


def render_decision_table(topic: Topic) -> str:
    rows = "".join(
        "<tr>"
        f"<td><strong>{html.escape(name)}</strong></td>"
        f"<td>{inline(purpose)}</td><td>{inline(mechanism)}</td>"
        f"<td>{inline(choose)}</td><td>{inline(replace)}</td>"
        "</tr>"
        for name, purpose, mechanism, choose, replace in comparison_rows(topic)
    )
    return (
        '<div class="table-scroll"><table class="decision-table"><thead><tr>'
        "<th>Component／選項</th><th>負責什麼</th><th>底層機制</th>"
        "<th>什麼時候選</th><th>什麼時候替換／避免</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def render_scope_guide(topic: Topic) -> str:
    return (
        '<div class="scope-grid">'
        + "".join(
            '<section>'
            f"<h3>{html.escape(title)}</h3>"
            "<ul>"
            + "".join(f"<li>{inline(item)}</li>" for item in items)
            + "</ul></section>"
            for title, items in scope_guide(topic)
        )
        + "</div>"
    )


def render_practice_questions(topic: Topic) -> str:
    letters = "ABCDE"
    rendered = []
    for index, question in enumerate(practice_questions(topic), 1):
        choices = "".join(
            f"<li><strong>{letters[choice_index]}.</strong> {inline(choice)}</li>"
            for choice_index, choice in enumerate(question.choices)
        )
        correct = "、".join(letters[answer] for answer in question.answers)
        explanations = "".join(
            f"<li><strong>{letters[choice_index]}.</strong> {inline(explanation)}</li>"
            for choice_index, explanation in enumerate(question.explanations)
        )
        provenance = ""
        if question.sources:
            official_links = "、".join(
                f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
                for title, url, _ in question.sources
            )
            inspiration_links = "、".join(
                f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
                for title, url, _ in question.inspirations
            )
            provenance = (
                '<aside class="question-provenance">'
                f"<p><strong>事實查證：</strong>{official_links}</p>"
                + (
                    f"<p><strong>選題靈感：</strong>{inspiration_links}；只參考主題與易錯點，未複製題文。</p>"
                    if inspiration_links
                    else ""
                )
                + (
                    f"<p><strong>原創作者：</strong>{html.escape(question.author_agent)}；"
                    f"<strong>Audit intent：</strong>{question.intent}；"
                    f"<strong>官方 task：</strong>{html.escape(', '.join(question.task_keys))}</p>"
                    if question.author_agent
                    else ""
                )
                + "</aside>"
            )
        rendered.append(
            f'<article class="chapter-exam-question" id="{html.escape(question.question_id or f"{topic_anchor(topic)}-practice-{index}", quote=True)}">'
            f'<div class="question-meta"><span>{html.escape(question.level)}</span>'
            f"<span>{html.escape(question.tested)}</span>"
            f"<span>{'選兩項' if question.kind == 'multi' else '單選'}</span></div>"
            f"<h3>練習題 {index}</h3><p>{inline(question.prompt)}</p>"
            f'<ol class="choices">{choices}</ol>'
            '<details class="chapter-exam-answer"><summary>查看答案與 A/B/C/D 逐項解析</summary><div>'
            f'<p class="correct-answer">答案：{correct}</p>'
            f'<ul class="option-analysis">{explanations}</ul>'
            f"{provenance}"
            "</div></details></article>"
        )
    return "".join(rendered)


def render_sources(topic: Topic) -> str:
    rows = []
    for key in topic.sources:
        title, url, kind = SOURCES[key]
        rows.append(
            f'<li><span class="source-kind {kind}">{kind}</span>'
            f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
        )
    return '<ul class="source-list">' + "".join(rows) + "</ul>"


def render_qas(topic: Topic) -> str:
    rows = []
    for index, (question, answer) in enumerate(qas(topic), 1):
        rows.append(
            f'<details class="qa"><summary>Q{index}. {html.escape(question)}</summary>'
            f"<div>{paragraphs(answer)}</div></details>"
        )
    return "".join(rows)


def render_survey_supplements(topic: Topic) -> str:
    rendered = []
    for supplement in survey_supplements(topic.number):
        sources = "".join(
            f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
            for title, url in supplement.sources
        )
        rendered.append(
            '<section class="survey-supplement">'
            f"<h2>{html.escape(supplement.title)}</h2>"
            f"<p>{inline(supplement.context)}</p>"
            f'<pre class="architecture-diagram"><code>{html.escape(supplement.diagram)}</code></pre>'
            f"<h3>{html.escape(supplement.example_title)}</h3>"
            f'<div class="code-label">{html.escape(supplement.example_language)}</div>'
            f'<pre class="config-code"><code>{html.escape(supplement.example)}</code></pre>'
            '<ol class="supplement-notes">'
            + "".join(f"<li>{inline(item)}</li>" for item in supplement.explanation)
            + "</ol>"
            f'<aside class="callout decision"><strong>選擇邊界</strong><p>{inline(supplement.decision)}</p></aside>'
            f'<aside class="callout scope"><strong>考試範圍</strong><p>{inline(supplement.exam_scope)}</p></aside>'
            '<p><strong>官方查證來源：</strong></p>'
            f'<ul class="supplement-sources">{sources}</ul>'
            "</section>"
        )
    if not rendered:
        return ""
    return (
        '<div class="survey-supplements">'
        '<p class="survey-note">這些內容來自全站交叉稽核後發現的缺口；社群資料只用來找漏項，'
        "下列技術行為以 AWS 官方文件校正。</p>"
        + "".join(rendered)
        + "</div>"
    )


def render_chapter(topic: Topic) -> str:
    part = part_for(topic.number)
    special_html = render_special_explanation(topic)
    config_html = render_config_examples(topic)
    deep_section = (
        "<h2>再往底層走：這一章真正容易混淆的地方</h2>" + special_html
        if special_html
        else ""
    )
    config_section = (
        "<h2>可以直接對照 AWS 的設定範例</h2>"
        "<p>這裡只放真的會改變服務行為、可映射到AWS API或Infrastructure as Code的設定。"
        "沒有實作價值的作者檢查表不冒充config；請先預測每一行會如何改變資料路徑，再讀下面的解釋。</p>"
        + config_html
        if config_html
        else ""
    )
    task_badges = "".join(
        f'<span title="{html.escape(TASKS[task], quote=True)}">{task}</span>'
        for task in topic.tasks
    )
    service_badges = "".join(f"<span>{html.escape(service)}</span>" for service in topic.services)
    return f"""
<article class="chapter" id="{topic_anchor(topic)}" data-chapter="{topic.number}" data-title="{html.escape(topic.title, quote=True)}">
  <div class="part-kicker">Part {part["part"]} · {html.escape(part["title"])}</div>
  <h1>第 {topic.number} 章　{html.escape(topic.title)}</h1>
  <p class="chapter-question">{inline(topic.problem)}</p>
  <div class="chapter-meta"><span>{html.escape(topic.level)}</span>{task_badges}</div>
  {chapter_position(topic)}

  {render_chapter_story(topic)}

  <details class="reference-box chapter-map"><summary>你在全書的哪裡？查看前後章與學習路線</summary><div>
    {part_journey(part["part"])}
    <p>前一層提供這章需要的背景，下一層會使用本章產生的結果。迷路時再打開這張地圖即可。</p>
  </div></details>

  <h2>先看全圖：這件事在系統裡怎麼發生？</h2>
  {render_architecture_overview(topic)}
  <p class="diagram-guide">第一次先沿箭頭讀正常故事：誰提出需求、誰接手、資料或request最後去了哪裡。
  第二次再從最下面倒著看故障：哪個訊號先變壞、影響停在哪裡、系統如何恢復。</p>

  <h2>先懂原理，再看每個 Component 在哪一站接手</h2>
  <div class="mental-model">{paragraphs(mental_model(topic))}</div>
  {render_component_role_map(topic)}
  {render_worked_example(topic)}
  {deep_section}
  {render_survey_supplements(topic)}

  {render_concept_reference(topic)}

  <h2>回到 AWS：服務名稱、設定與責任邊界</h2>
  <p>現在才把產品名稱與完整設定放回來。上面的故事回答「為什麼」；下面的工具箱回答
  「AWS把它叫什麼、要在哪裡設定、怎麼驗證」。</p>
  <div class="service-badges">{service_badges}</div>
  {render_service_reference(topic)}

  {config_section}

  <h2>Service Decision Matrix：為什麼選 A，不選 B？</h2>
  <p>比較表放在理解之後使用：先找題目不能妥協的條件，再看哪個服務的責任真正吻合。
  不要用功能數量投票，也不要因為某個服務比較熟就先選它。</p>
  {render_decision_table(topic)}

  <h2>讀到這裡，請用自己的話說一次</h2>
  {render_key_takeaways(topic)}

  <h2>Trade-offs 與 Failure Modes</h2>
  <div class="trade-grid">
    {''.join(f'<section><span>{index}</span><p>{inline(value)}</p></section>' for index, value in enumerate(tradeoffs(topic), 1))}
  </div>

  <h2>SAA 與 SAP 考試 Pattern</h2>
  <div class="exam-grid">
    <section><h3>SAA 看什麼？</h3><p>找出單一workload最重要的安全、可靠、效能或成本限制，
    排除會造成「{inline(topic.failure)}」的選項，再選營運負擔合理的最小方案。</p></section>
    <section><h3>SAP 如何加深？</h3><p>加入跨帳號、跨Region、既有系統、migration、治理、成本可見性、
    rollout與rollback。答案必須是可營運的組合，而不只是一項服務。</p></section>
  </div>
  {render_scope_guide(topic)}

  <h2>社群筆記與通過心得：值得吸收什麼？</h2>
  <aside class="callout community"><strong>Community Insight，Officially Calibrated</strong>
  {paragraphs(community_insight(topic))}</aside>

  <h2>AWS 之外仍可重用的 Pattern</h2>
  <aside class="callout portable"><strong>{html.escape(topic.pattern)}</strong>
  <p>{inline(topic.pattern.capitalize())}。請用需求、state owner、failure boundary與evidence解釋它；
  換成Azure、GCP、Kubernetes或自建機房時，產品名稱會變，但推理不變。</p></aside>

  <h2>動手驗證</h2>
  <ol class="lab-list">{''.join(f'<li>{inline(item)}</li>' for item in labs(topic))}</ol>

  <h2>本章考題：{len(practice_questions(topic))} 題逐選項解析</h2>
  <p class="answer-instruction">每題先圈出hard constraint，再逐一說明為什麼不選其他選項。
  題組依序涵蓋用途、底層機制、真實設定、資料流、故障診斷、比較、成本、SAA、SAP與複選整合。</p>
  {render_practice_questions(topic)}

  <h2>Follow-up Questions &amp; Detailed Answers</h2>
  <p class="answer-instruction">先遮住答案口述。合格答案必須包含機制、邊界、failure mode與實務影響。</p>
  {render_qas(topic)}

  <h2>本章來源與延伸閱讀</h2>
  {render_sources(topic)}
</article>
"""


CATEGORY_CUES = {
    "Analytics": "辨識ingestion、catalog、query、stream processing與BI的責任分界。",
    "Application Integration": "辨識queue、fan-out、event routing與durable workflow。",
    "AWS Cost Management": "辨識budget、分析、明細資料與承諾折扣。",
    "Cloud Financial Management": "辨識budget、分析、明細資料與承諾折扣。",
    "Compute": "辨識控制程度、執行時間、容量與營運責任。",
    "Containers": "辨識orchestrator、runtime、image與節點管理。",
    "Database": "辨識data model、access pattern、一致性與scale方向。",
    "Developer Tools": "辨識build、deploy、artifact與trace evidence。",
    "Front-End Web and Mobile": "辨識API、mobile/web hosting與使用者互動入口。",
    "Frontend Web and Mobile": "辨識API、mobile/web hosting與使用者互動入口。",
    "Machine Learning": "辨識預建AI能力與完整ML platform的差異。",
    "Management and Governance": "辨識inventory、policy、observability、automation與multi-account治理。",
    "Media Services": "辨識影音ingestion、stream與transcoding。",
    "Migration and Transfer": "辨識server、database、file、online與offline搬移。",
    "Networking and Content Delivery": "辨識routing、private connectivity、edge與hybrid連線。",
    "Security, Identity, and Compliance": "辨識identity、encryption、detection、prevention與evidence。",
    "Serverless": "辨識event-driven compute與managed container runtime。",
    "Storage": "辨識block、file、object、backup與hybrid storage。",
    "Blockchain": "辨識多方共享ledger但不互相信任的情境。",
    "Business Applications": "辨識managed communication與business-facing service。",
    "End User Computing": "辨識virtual desktop與application streaming。",
    "Internet of Things (IoT)": "辨識device identity、edge processing、telemetry與fleet management。",
}


def normalized_service(value: str) -> str:
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\b(?:Amazon|AWS)\b", "", value, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def service_scope_rows() -> tuple[str, int]:
    saa = {normalized_service(service): (category, service) for category, values in SAA_SCOPE.items() for service in values}
    sap = {normalized_service(service): (category, service) for category, values in SAP_SCOPE.items() for service in values}
    keys = sorted(set(saa) | set(sap), key=lambda key: (saa.get(key, sap.get(key))[0], key))
    topic_text = {
        topic.number: " ".join(topic.services + (topic.title,))
        for topic in TOPICS
    }
    rows = []
    for index, key in enumerate(keys, 1):
        category, display = saa.get(key, sap.get(key))
        candidates = [
            topic for topic in TOPICS
            if key and any(token in normalized_service(topic_text[topic.number]) for token in (key, key[:12]))
        ]
        topic = candidates[0] if candidates else TOPICS[min((index - 1) % len(TOPICS), len(TOPICS) - 1)]
        cue = CATEGORY_CUES.get(category, "先辨識需求與相鄰服務的責任邊界。")
        rows.append(
            "<tr>"
            f"<td>{html.escape(display)}</td><td>{html.escape(category)}</td>"
            f"<td>{'✓' if key in saa else '—'}</td><td>{'✓' if key in sap else '—'}</td>"
            f'<td><a href="#{topic_anchor(topic)}">Ch {topic.number}: {html.escape(topic.title)}</a></td>'
            "</tr>"
            f'<tr class="atlas-question"><td colspan="5"><details class="atlas-qa">'
            f"<summary>自測：看到 {html.escape(display)}，至少要先問什麼？</summary>"
            f"<div><p>{html.escape(cue)} 不要只背產品名稱；先確認它處理的data/control plane、"
            f"相鄰替代方案、failure boundary與成本單位。本書以第 {topic.number} 章作為最近的深入入口。</p></div>"
            "</details></td></tr>"
        )
    return "".join(rows), len(keys)


def coverage_html() -> str:
    chapter_map: dict[str, list[Topic]] = defaultdict(list)
    mock_map: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for topic in TOPICS:
        for task in topic.tasks:
            chapter_map[task].append(topic)
    for exam, questions in MOCK_EXAMS.items():
        for question in questions:
            mock_map[question.task].append((exam, question.number))
    rows = []
    for task, label in TASKS.items():
        chapters = chapter_map[task]
        mocks = mock_map[task]
        rows.append(
            f"<tr><td>{task}</td><td>{html.escape(label)}</td>"
            f"<td>{len(chapters)}</td><td>{len(mocks)}</td>"
            f'<td><a href="#{topic_anchor(chapters[0])}">Ch {chapters[0].number}</a></td></tr>'
        )
    return "".join(rows)


def jayendra_coverage_html() -> str:
    labels = {
        "covered": ("已由正文涵蓋", "good"),
        "supplemented": ("本次補強", "good"),
        "adjacent": ("相鄰專科，不列入雙證必考", "warning"),
    }
    rows = []
    for category, title, url, chapters, status in JAYENDRA_PATTERNS:
        chapter_links = "、".join(
            f'<a href="#{topic_anchor(TOPIC_BY_NUMBER[number])}">Ch {number}</a>'
            for number in chapters
        )
        label, css = labels[status]
        rows.append(
            "<tr>"
            f"<td>{html.escape(category)}</td>"
            f'<td><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></td>'
            f"<td>{chapter_links}</td>"
            f'<td class="{css}">{html.escape(label)}</td>'
            "</tr>"
        )
    counts = defaultdict(int)
    for *_, status in JAYENDRA_PATTERNS:
        counts[status] += 1
    inventory_counts = defaultdict(int)
    with JAYENDRA_INVENTORY.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            inventory_counts[row["status"]] += 1
    inventory_rows = (
        ("mapped-pattern", "逐項映射進本附錄與正文", "54 個架構 pattern 逐一對照章節"),
        ("topic-candidate", "作為漏項雷達後再以官方文件校準", "不直接把社群敘述當考試事實"),
        ("study-meta", "只吸收讀書與整理方法", "不複製題庫、答案或宣稱的真題"),
        ("legacy-reference", "保留歷史辨識與替代方案", "不把退場服務當新架構首選"),
        ("out-of-scope", "明確排除", "非 AWS、其他證照、職涯、折扣或與雙證無關"),
    )
    inventory_table = "".join(
        "<tr>"
        f"<td>{html.escape(status)}</td><td>{inventory_counts[status]}</td>"
        f"<td>{html.escape(action)}</td><td>{html.escape(boundary)}</td>"
        "</tr>"
        for status, action, boundary in inventory_rows
    )
    notes = "".join(f"<li>{inline(note)}</li>" for note in OFFICIAL_OVERRIDE_NOTES)
    return (
        "<p>2026-10-01 快照中，該 architecture-pattern index 的介紹文字寫 58 篇，"
        f"但七個分類表實際列出 {len(JAYENDRA_PATTERNS)} 個連結。本表逐項映射所有列出的主題；"
        "全站 sitemap 的 520 篇文章還包含舊 Solr、職涯、折扣與其他證照，不能不分範圍搬進雙證手冊。</p>"
        '<div class="context-grid">'
        f'<section><span>正文已涵蓋</span><p>{counts["covered"]} 項</p></section>'
        f'<section><span>本次補強</span><p>{counts["supplemented"]} 項</p></section>'
        f'<section><span>相鄰專科</span><p>{counts["adjacent"]} 項</p></section>'
        "</div>"
        "<h2>全站 520 篇如何處理？</h2>"
        "<p>「完成 survey」不等於把每篇文章原封不動塞進書裡。以下是 sitemap 每一個 URL "
        "都必須取得的 scope decision；五類加總必須恰為 520，並由品質閘門驗證沒有待人工分類項。</p>"
        '<div class="table-scroll"><table><thead><tr>'
        "<th>分類</th><th>篇數</th><th>本書處理方式</th><th>出版邊界</th>"
        f"</tr></thead><tbody>{inventory_table}</tbody></table></div>"
        "<h2>官方文件覆寫社群筆記的地方</h2>"
        f"<ol>{notes}</ol>"
        '<div class="table-scroll"><table><thead><tr>'
        "<th>分類</th><th>外部主題</th><th>本書入口</th><th>稽核結果</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_mock_exam(name: str, questions: list) -> str:
    anchor = "mock-" + slugify(name)
    rows = []
    letters = "ABCDE"
    for question in questions:
        choices = "".join(
            f"<li><strong>{letters[index]}.</strong> {inline(choice)}</li>"
            for index, choice in enumerate(question.choices)
        )
        correct = ", ".join(letters[index] for index in question.answers)
        explanations = "".join(
            f"<li><strong>{letters[index]}.</strong> {inline(reason)}</li>"
            for index, reason in enumerate(question.explanations)
        )
        rows.append(
            f'<article class="mock-question" id="{anchor}-q{question.number}">'
            f"<h3>{question.number}. {html.escape(question.kind)}</h3>"
            f"<p>{inline(question.prompt)}</p><ol class=\"choices\">{choices}</ol>"
            '<details class="mock-answer"><summary>查看答案與每個選項解析</summary><div>'
            f'<p class="correct-answer">答案：{correct}</p><ul>{explanations}</ul>'
            f'<p><strong>官方 Task：</strong>{question.task} — {html.escape(TASKS[question.task])}</p>'
            f'<p><strong>回讀：</strong><a href="#{topic_anchor(TOPIC_BY_NUMBER[question.chapter])}">'
            f"第 {question.chapter} 章</a>。<strong>跨雲原則：</strong>{html.escape(question.principle)}</p>"
            "</div></details></article>"
        )
    return (
        f'<article class="chapter appendix mock-exam" id="{anchor}" data-title="{html.escape(name, quote=True)}">'
        f'<div class="part-kicker">Original Practice Exam · {len(questions)} Questions</div>'
        f"<h1>{html.escape(name)} 模擬考</h1>"
        "<p>所有題目都是依官方domain與本書案例原創，不是exam dump。先計時完成，再讀逐選項解析；"
        "錯題要記錄漏看的constraint，而不是背答案字母。</p>"
        + "".join(rows)
        + "</article>"
    )


def prologue_html() -> str:
    return """
<article class="chapter prologue" id="start-here" data-title="全書導讀">
  <div class="part-kicker">Start Here · SAA-C03 + SAP-C02 + announced SAP-C03 transition</div>
  <h1>AWS Solutions Architect 雙證全攻略</h1>
  <p class="chapter-question">只假設一般程式設計背景，從網路、身份與資料開始，循序建立能通過
  SAA、再處理 SAP 企業情境的架構判斷力。</p>
  <aside class="callout version"><strong>版本基線：2026-10-01</strong>
    <p>SAA 以 SAA-C03 為coverage contract。SAP-C02目前仍可考；AWS已公告更新版
    SAP-C03將於2026-10-27開放註冊，SAP-C02最後考試日為2026-11-17；這兩個日期目前都
    還在未來。SAP-C03完整exam guide尚未發布，因此全書task mapping仍只以SAP-C02為準；
    官方列出的Bedrock Guardrails、AgentCore Identity與Step Functions human oversight
    只標成emerging-topic／不計分pretest準備，不冒充SAP-C03計分範圍。</p>
  </aside>
  <h2>本書如何保證 self-contained？</h2>
  <div class="context-grid">
    <section><span>零背景</span><p>前10章先解釋cloud、network、storage、database、RTO/RPO與shared responsibility。</p></section>
    <section><span>第一次閱讀</span><p>真實故事 → 一張全圖 → 沿著request、data與failure理解角色，不先用設定卡轟炸讀者。</p></section>
    <section><span>第二次複習</span><p>再打開名詞與設定工具箱，閱讀真實 Config、服務比較、故障演練、考題與Q&amp;A。</p></section>
    <section><span>可驗證</span><p>每章都有可操作的設定或驗證步驟；official task、service atlas與mock皆有coverage gate。</p></section>
  </div>
  <h2>全書 Blueprint</h2>
  <pre class="architecture-diagram"><code>requirements
  ↓
identity → network → compute → storage / database
  ↓                       ↓
integration / event flow → reliability / performance / cost
  ↓
deployment / operations → multi-account enterprise architecture
  ↓
AI controls → end-to-end cases → portable architecture patterns
  ↓
20 diagnostic + 65 SAA + 75 SAP original mock questions</code></pre>
  <h2>通用解題演算法：COSTAR</h2>
  <div class="flow-grid">
    <div class="flow-card"><span>C</span><p><strong>Constraints：</strong>圈出security、RTO/RPO、latency、cost、migration window。</p></div>
    <div class="flow-card"><span>O</span><p><strong>Owner：</strong>誰擁有identity、state、key、route與recovery？</p></div>
    <div class="flow-card"><span>S</span><p><strong>Semantics：</strong>需要message、stream、file、object、transaction還是eventual consistency？</p></div>
    <div class="flow-card"><span>T</span><p><strong>Trade-off：</strong>哪個constraint改變時答案會翻轉？</p></div>
    <div class="flow-card"><span>A</span><p><strong>Availability boundary：</strong>共同依賴與最大blast radius在哪？</p></div>
    <div class="flow-card"><span>R</span><p><strong>Recovery/evidence：</strong>如何rollback、restore、observe並證明？</p></div>
  </div>
  <h2>建議路線</h2>
  <table><tr><th>目標</th><th>順序</th><th>完成標準</th></tr>
  <tr><td>30天 SAA</td><td>Part 0–7 → cases 97–103 → Diagnostic/SAA mock</td><td>能用COSTAR排除每個distractor</td></tr>
  <tr><td>SAA 後45天 SAP</td><td>Part 8–11 → SAP mock → 回補弱task</td><td>能處理multi-account、migration與least-change trade-off</td></tr>
  <tr><td>零背景12週</td><td>每週一個Part、每章走一次設定與故障驗證並回答Q&amp;A</td><td>不靠服務口訣，能畫完整data/control/failure flow</td></tr>
  </table>
</article>
"""


def appendix_articles(service_rows: str, service_count: int) -> list[tuple[str, str, str]]:
    decision_tables = """
<table><tr><th>需求</th><th>先想</th><th>常見相鄰選項</th></tr>
<tr><td>全球HTTP cache/WAF</td><td>Edge cache semantics</td><td>CloudFront vs Global Accelerator</td></tr>
<tr><td>VPC互連</td><td>全網路、單服務或hub</td><td>Peering vs PrivateLink vs TGW</td></tr>
<tr><td>消息</td><td>Queue、fan-out、routing或stream</td><td>SQS vs SNS vs EventBridge vs Kinesis</td></tr>
<tr><td>資料</td><td>Block、file、object與access pattern</td><td>EBS vs EFS/FSx vs S3</td></tr>
<tr><td>Database</td><td>Transaction、key-value、cache、analytics</td><td>RDS/Aurora vs DynamoDB vs ElastiCache vs Redshift</td></tr>
<tr><td>DR</td><td>RTO/RPO與write ownership</td><td>Backup vs pilot light vs warm standby vs active-active</td></tr>
</table>"""
    formulas = """
<ul>
<li><strong>Series availability：</strong>A_total ≈ A1 × A2 × …；required dependencies越多，整體通常越低。</li>
<li><strong>Queue growth：</strong>backlog change = arrival rate − service rate；長期arrival較大時queue無法自行恢復。</li>
<li><strong>Bandwidth time：</strong>seconds ≈ bytes ÷ effective bytes/second；還要加入change rate與verification。</li>
<li><strong>CIDR：</strong>IPv4 /n共有2^(32−n) addresses；AWS subnet另有保留地址，實際可用較少。</li>
<li><strong>Cost unit：</strong>monthly cost ÷ successful business operations，比分開看instance單價更有意義。</li>
<li><strong>RTO/RPO：</strong>RTO是恢復critical path；RPO是各state source可接受的資料落後。</li>
</ul>"""
    community = "".join(
        f'<li><span class="source-kind {kind}">{kind}</span>'
        f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
        "<p>用途：發現高頻卡點、服務比較、錯誤選項與學習節奏；所有技術結論回到官方文件校準。</p></li>"
        for title, url, kind in SOURCES.values()
        if kind == "community"
    )
    glossary_terms = sorted(
        {
            "Access pattern": "應用實際如何以key、range、join、scan、write與consistency讀寫資料。",
            "Blast radius": "單一錯誤、故障或錯誤變更最多能影響的範圍。",
            "Control plane": "建立與修改policy、route、capacity、metadata等管理狀態的路徑。",
            "Data plane": "處理每次request、packet、message或資料讀寫的runtime路徑。",
            "Durability": "已接受資料在故障後仍不遺失的程度，不等於服務隨時可用。",
            "Elasticity": "容量能隨需求增減的速度與自動化程度。",
            "Failure domain": "會因同一事件一起失效的資源集合，例如AZ或Region。",
            "Idempotency": "同一operation重複執行，business effect仍只發生一次或等價。",
            "Least privilege": "只授予完成目前任務所需action、resource、condition與時間。",
            "RPO": "災難後可接受遺失或落後多少資料。",
            "RTO": "災難後服務必須在多久內恢復。",
            "State owner": "對某份authoritative state的一致性、生命週期與恢復負責的元件。",
        }.items()
    )
    glossary = '<div class="glossary-grid">' + "".join(
        f"<section><h3>{html.escape(term)}</h3><p>{html.escape(definition)}</p></section>"
        for term, definition in glossary_terms
    ) + "</div>"
    transition = """
<p>截至2026-10-01，SAP-C02仍是目前考試版本；AWS已公告SAP-C03於2026-10-27開放註冊，
並將SAP-C02最後考試日設為2026-11-17。穩定知識如multi-account、hybrid network、DR、
migration與continuous improvement保留在正文；版本特定domain/weight則集中在coverage appendix。</p>
<p>官方SAP-C02 guide亦列出可能作為不計分pretest的emerging topics：Bedrock Guardrails、
AgentCore Identity與Step Functions human oversight。Part 9已把它們放入完整架構，而不是只列名詞。</p>
<div class="warning"><strong>更新規則：</strong>SAP-C03完整exam guide發佈後，先更新task registry，
再由checker找出沒有chapter/mock mapping的新task；不直接在正文散落改weight，避免版本漂移。</div>"""
    return [
        ("appendix-coverage", "附錄 A：官方 Exam Task Coverage Matrix",
         '<table><thead><tr><th>Task</th><th>官方能力</th><th>章節數</th><th>Mock題數</th><th>入口</th></tr></thead>'
         f"<tbody>{coverage_html()}</tbody></table>"),
        ("appendix-service-atlas", f"附錄 B：完整 Service Atlas（{service_count} 個去重服務）",
         "<p>官方清單明確標註非完整且可能變動。本表的目的不是要求每項同深度背誦，而是確保名稱、類別、"
         "考試範圍與最近的深入章節都有入口。</p>"
         '<table class="service-atlas"><thead><tr><th>Service</th><th>Category</th><th>SAA</th><th>SAP</th><th>深入章</th></tr></thead>'
         f"<tbody>{service_rows}</tbody></table>"),
        ("appendix-decisions", "附錄 C：高頻服務選型速查", decision_tables),
        ("appendix-formulas", "附錄 D：公式與容量推理卡", formulas),
        ("appendix-community", "附錄 E：Community Notes / Experience Research Ledger",
         "<p>社群資料用來補『大家哪裡容易卡住』，不作服務行為的最終真相，也不收錄exam dumps。</p>"
         "<p><strong>課程設計 survey 的共同模式：</strong>A Cloud Guru／Pluralsight以短概念、"
         "視覺提示、quiz與hands-on lab交替；AWS Skill Builder使用情境、knowledge check、lab與"
         "practice assessment；Cantrill強調完整理論、demo與真實專案；Tutorials Dojo與Cloud Academy"
         "用scenario題、逐選項解釋與exam simulator反覆驗證。本書因此採用「故事 → 一張全圖 →"
         "沿流程理解 → 實際設定 → 題目驗證」，不再讓服務清單與圖卡阻斷第一次閱讀。</p>"
         f'<ul class="research-ledger">{community}</ul>'),
        ("appendix-glossary", "附錄 F：零背景核心術語", glossary),
        ("appendix-sap-transition", "附錄 G：SAP-C02 → SAP-C03 Transition", transition),
        ("appendix-jayendra-coverage", "附錄 H：Jayendra Architecture Patterns 全項對照",
         jayendra_coverage_html()),
        ("appendix-sources", "附錄 I：完整來源清單",
         '<ul class="source-list">' + "".join(
             f'<li><span class="source-kind {kind}">{kind}</span>'
             f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
             for title, url, kind in SOURCES.values()
         ) + "</ul>"),
    ]


def chapter_markdown(topic: Topic) -> str:
    story_title, story_paragraphs = chapter_story(topic)
    deep_sections = special_explanation(topic)
    examples = config_examples(topic)
    rows = [
        f"# 第 {topic.number} 章　{topic.title}",
        "",
        topic.problem,
        "",
        f"## {story_title}",
        "",
    ]
    for paragraph in story_paragraphs:
        rows.extend([paragraph, ""])
    rows.extend(
        [
            "## 先看全圖：這件事在系統裡怎麼發生？",
            "",
            "```text",
            blueprint(topic),
            "```",
            "",
            "## 先懂原理，再把 AWS 名稱放回來",
            "",
            mental_model(topic),
            "",
            "## 每個 Component 在哪一站接手？",
            "",
            "| Component | 負責什麼 | 底層怎麼運作 |",
            "| --- | --- | --- |",
        ]
    )
    for name, profile in components(topic):
        rows.append(f"| {name} | {profile.purpose} | {profile.mechanism} |")
    rows.extend(
        [
            "",
            "## 把全圖套進一個具體案例",
            "",
            f"**場景：** {topic.scenario}",
            "",
            *[
                f"{index}. {value}"
                for index, value in enumerate(mechanism_walkthrough(topic), 1)
            ],
            "",
        ]
    )
    if topic.number == 12:
        rows.extend(
            [
                "### 三張 Route Table",
                "",
                "| Route table | 關聯 subnet | Destination | Target | 效果 |",
                "| --- | --- | --- | --- | --- |",
                "| public-rt | Public A/B | `10.20.0.0/16` | `local` | VPC 內部互通 |",
                "| public-rt | Public A/B | `0.0.0.0/0` | `igw-0123` | 具備 Internet 路徑；資源仍需 public address |",
                "| app-rt-a | Private app A | `10.20.0.0/16` | `local` | ALB、app、DB 走 private IP |",
                "| app-rt-a | Private app A | `0.0.0.0/0` | `nat-0abc` | App 可主動出站，Internet 不能主動連入 |",
                "| db-rt | Isolated DB A/B | `10.20.0.0/16` | `local` | DB 沒有 Internet default route |",
                "",
                "IGW 附掛在 VPC 邊界，不是 public 與 private subnet 中間的路由器。"
                "兩者差異來自 route table、resource public address 與 security policy。",
                "",
            ]
        )
    if deep_sections:
        rows.extend(["## 再往底層走：這一章真正容易混淆的地方", ""])
        for title, body in deep_sections:
            rows.extend([f"### {title}", "", body, ""])
    supplements = survey_supplements(topic.number)
    if supplements:
        rows.extend(
            [
                "## 跨來源稽核後補上的進階缺口",
                "",
                "社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。",
                "",
            ]
        )
        for supplement in supplements:
            rows.extend(
                [
                    f"### {supplement.title}",
                    "",
                    supplement.context,
                    "",
                    "```text",
                    supplement.diagram,
                    "```",
                    "",
                    f"#### {supplement.example_title}",
                    "",
                    f"```{supplement.example_language}",
                    supplement.example,
                    "```",
                    "",
                    *[
                        f"{index}. {item}"
                        for index, item in enumerate(supplement.explanation, 1)
                    ],
                    "",
                    f"**選擇邊界：** {supplement.decision}",
                    "",
                    f"**考試範圍：** {supplement.exam_scope}",
                    "",
                    *[
                        f"- [{title}]({url})"
                        for title, url in supplement.sources
                    ],
                    "",
                ]
            )
    rows.extend(
        [
            "## 需要時再查：四個閱讀支點",
            "",
        ]
    )
    for title, meaning, example in term_cards(topic):
        rows.extend(
            [
                f"### {title}",
                "",
                f"- **白話定義：** {meaning}",
                f"- **具體例子／邊界：** {example}",
                "",
            ]
        )
    rows.extend(["## 本章新名詞字典", ""])
    for term, definition in chapter_glossary(topic, components(topic)):
        rows.extend([f"### {term}", "", definition, ""])
    rows.extend(
        [
            "## 回到 AWS：Components、功用與責任邊界",
            "",
        ]
    )
    for name, profile in components(topic):
        rows.extend(
            [
                f"### {name}",
                "",
                f"- **功用：** {profile.purpose}",
                f"- **底層機制：** {profile.mechanism}",
                f"- **關鍵設定：** {profile.config}",
                f"- **選擇時機：** {profile.choose}",
                f"- **替換時機：** {profile.replace}",
                    "",
                ]
            )
    rows.extend(["## 考前與實作時再查：設定操作手冊", ""])
    for name, profile in components(topic):
        rows.extend([f"### {name}：逐項設定說明", ""])
        for guide in setting_guides(name, profile):
            rows.extend(
                [
                    f"#### `{guide.name}`",
                    "",
                    f"- **控制什麼：** {guide.controls}",
                    f"- **何時需要：** {guide.when}",
                    f"- **怎麼設定／驗證：** {guide.configure}",
                    f"- **常見錯法：** {guide.pitfall}",
                    "",
                ]
            )
    if examples:
        rows.extend(["## 可以直接對照 AWS 的設定範例", ""])
        for example in examples:
            rows.extend(
                [
                    f"### {example.title}",
                    "",
                    f"```{example.language}",
                    example.code,
                    "```",
                    "",
                    *[f"{index}. {note}" for index, note in enumerate(example.notes, 1)],
                    "",
                ]
            )
    rows.extend(
        [
        "## 讀到這裡，請用自己的話說一次",
        "",
        *[f"{index}. {value}" for index, value in enumerate(key_takeaways(topic), 1)],
        "",
        "## Service Decision Matrix",
        "",
        "| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {name} | {purpose} | {mechanism} | {choose} | {replace} |"
            for name, purpose, mechanism, choose, replace in comparison_rows(topic)
        ],
        "",
        "## SAA 與 SAP 範圍",
        "",
        ]
    )
    for title, items in scope_guide(topic):
        rows.extend([f"### {title}", "", *[f"- {item}" for item in items], ""])
    rows.extend(
        [
        f"## 本章 {len(practice_questions(topic))} 題考題",
        "",
        ]
    )
    letters = "ABCDE"
    for index, question in enumerate(practice_questions(topic), 1):
        correct = "、".join(letters[answer] for answer in question.answers)
        rows.extend(
            [
                f"### 練習題 {index}｜{question.level}｜{question.tested}",
                "",
                question.prompt,
                "",
                *[
                    f"{letters[choice_index]}. {choice}"
                    for choice_index, choice in enumerate(question.choices)
                ],
                "",
                f"**答案：{correct}**",
                "",
                *[
                    f"- **{letters[choice_index]}：** {explanation}"
                    for choice_index, explanation in enumerate(question.explanations)
                ],
                *(
                    [
                        "",
                        "**事實查證：** "
                        + "、".join(
                            f"[{title}]({url})"
                            for title, url, _ in question.sources
                        ),
                    ]
                    if question.sources
                    else []
                ),
                "",
            ]
        )
    rows.extend(
        [
        "## Follow-up Questions",
        "",
        ]
    )
    for index, (question, answer) in enumerate(qas(topic), 1):
        rows.extend([f"### Q{index}. {question}", "", answer, ""])
    return "\n".join(rows).rstrip() + "\n"


def write_sources() -> list[Path]:
    SOURCE_DIR.mkdir(exist_ok=True)
    emitted = []
    start = SOURCE_DIR / "00 - Start Here.md"
    start.write_text(
        """# AWS Solutions Architect 雙證全攻略

版本基線：2026-10-01。SAA-C03 + SAP-C02；另追蹤已公告但尚未開放註冊的SAP-C03 transition。

## 這本書解決什麼問題？

AWS 認證最容易走偏的地方，是把準備過程變成數百個產品名稱與功能口訣。本書採取相反
路線：每一題先還原成 requirement、state、request/data flow、failure boundary、
operating model 與 evidence，再把它映射到 AWS managed service。這樣不只可以應付
SAA 的單一 workload 選型，也能處理 SAP 的跨帳號、跨 Region、migration、治理與
長期營運取捨。讀者只需要一般程式設計背景；前十章會補上 cloud、network、storage、
database、availability、durability、RTO、RPO 與 shared responsibility 等先備知識。

## 版本與考試範圍

- SAA 以 SAA-C03 exam guide 的 4 domains、14 tasks 為 coverage contract。
- SAP 以目前已發布的 SAP-C02 4 domains、20 tasks 為唯一 task mapping contract；
  SAP-C03 只保留官方公告與未來 guide 更新入口。
- 官方 service list 明確是 non-exhaustive 且可能變動，因此本書將穩定的架構原理與
  易變動的 exam mapping 分開。
- Emerging topics 納入 Bedrock Guardrails、AgentCore Identity 與 Step Functions
  human oversight，但不假裝預測未公開題目。
- 全部 160 道模擬題皆為依據公開 exam domains 原創；不包含、改寫或散布 exam dumps。

## 全書 Blueprint

```text
business requirement
  ↓ classify constraints
identity → network → compute → storage / database
  ↓                       ↓
security controls        integration / event flow
  ↓                       ↓
reliability / performance / cost
  ↓
deployment / operations / observability
  ↓
multi-account enterprise architecture / migration
  ↓
AI governance → end-to-end cases → portable patterns
  ↓
20 diagnostic + 65 SAA + 75 SAP original mock questions
```

每一章先用一個真實場景開場，再給一張能從頭走到尾的架構圖；正文沿著使用者請求、
資料變更或故障發生的順序解釋角色，而不是先展示服務清單。第一次讀完故事後，再打開
名詞與設定工具箱，把理解映射到AWS欄位、真實Config、故障演練與考題。這樣既保留完整
考試深度，也讓只具備一般程式設計背景的讀者能先建立一張連貫的心智地圖。

## COSTAR 解題演算法

1. **Constraints**：圈出 security、RTO/RPO、latency、cost、migration window 與
   operational burden。先辨識 hard constraint，不能讓其他高分抵銷它。
2. **Owner**：問誰擁有 identity、state、encryption key、route、capacity 與 recovery。
3. **Semantics**：確認需要 message、stream、file、object、transaction、cache，
   以及 strong 或 eventual consistency。
4. **Trade-off**：明確說出哪個條件改變時，主要方案會輸給相鄰替代方案。
5. **Availability boundary**：尋找共同依賴、correlated failure 與最大 blast radius。
6. **Recovery and evidence**：說明 retry、rollback、restore、failover、game day 與
   觀測證據，不能把「部署成功」當成「需求已滿足」。

## 建議閱讀路線

### 30 天 SAA

先讀 Part 0–7，接著完成案例 97–103，再做 Diagnostic 與 SAA Mock。錯題不要只記答案
字母，而要記錄漏看的 constraint、誤判的 state owner、沒有辨識的 failure boundary，
以及哪個關鍵詞讓替代方案看似合理。

### SAA 後 45 天 SAP

讀 Part 8–11，將每一個 SAA 單服務答案擴寫成可營運的組合：account/OU 邊界、network
topology、delegated administration、rollout、rollback、evidence、cost allocation 與
migration sequence。完成 75 題 SAP Mock 後，依官方 task coverage matrix 回補弱點。

### 零背景 12 週

每週讀一個 Part；每章先沿著真實設定走一次正常流，再闔上答案畫出故障流。若無法解釋
control plane 與 data plane、availability 與 durability、RTO 與 RPO、queue 與 stream、
authentication 與 authorization 的差異，就回到前置章節，而不是繼續背服務。

## 研究與資料使用原則

技術行為、考試 domains 與 in-scope services 以 AWS 官方文件為準。社群筆記、通過
心得與 re:Post 討論只用於發現高頻卡點、易混淆服務、讀題節奏與學習策略；它們不取代
官方文件，也不被當成出題保證。書中每章保留來源入口，附錄則提供完整 research ledger、
service atlas、task coverage、公式卡與術語表，使讀者可以查證而不必在閱讀正文時反覆
跳離上下文。
""",
        encoding="utf-8",
    )
    emitted.append(start)
    for part in PARTS:
        low, high = part["range"]
        path = SOURCE_DIR / f'{part["part"] + 1:02d} - {part["slug"]}.md'
        chunks = [
            "---",
            f'title: "{part["title"]}"',
            f'part: {part["part"]}',
            f'as_of: {AS_OF}',
            "---",
            "",
            f'# Part {part["part"]}　{part["title"]}',
            "",
        ]
        chunks.extend(chapter_markdown(topic) for topic in TOPICS if low <= topic.number <= high)
        path.write_text("\n".join(chunks), encoding="utf-8")
        emitted.append(path)
    return emitted


def build() -> None:
    assert [topic.number for topic in TOPICS] == list(range(1, 117))
    emitted = write_sources()
    articles = [prologue_html()]
    nav = [
        '<section class="nav-group"><h2>開始</h2><ul>'
        '<li><a href="#start-here"><span>00</span>全書導讀</a></li></ul></section>'
    ]
    search_items = [{"id": "start-here", "title": "全書導讀", "part": "Start", "text": "AWS SAA SAP"}]
    for part in PARTS:
        links = []
        for topic in TOPICS:
            if not (part["range"][0] <= topic.number <= part["range"][1]):
                continue
            articles.append(render_chapter(topic))
            links.append(
                f'<li><a href="#{topic_anchor(topic)}"><span>{topic.number:03d}</span>'
                f"{html.escape(topic.title)}</a></li>"
            )
            search_items.append({
                "id": topic_anchor(topic),
                "title": f"{topic.number}. {topic.title}",
                "part": part["title"],
                "text": " ".join((topic.problem, topic.decision, topic.alternative, topic.failure, *topic.services)),
            })
        nav.append(
            f'<section class="nav-group"><h2>Part {part["part"]} · {html.escape(part["title"])}</h2>'
            f'<ul>{"".join(links)}</ul></section>'
        )

    service_rows, service_count = service_scope_rows()
    appendix_links = []
    for index, (anchor, title, body) in enumerate(appendix_articles(service_rows, service_count), 1):
        articles.append(
            f'<article class="chapter appendix" id="{anchor}" data-title="{html.escape(title, quote=True)}">'
            f'<div class="part-kicker">Appendix {index}</div><h1>{html.escape(title)}</h1>{body}</article>'
        )
        appendix_links.append(f'<li><a href="#{anchor}"><span>A{index}</span>{html.escape(title)}</a></li>')
    for name, questions in MOCK_EXAMS.items():
        anchor = "mock-" + slugify(name)
        articles.append(render_mock_exam(name, questions))
        appendix_links.append(
            f'<li><a href="#{anchor}"><span>M</span>{html.escape(name)} Mock</a></li>'
        )
    nav.append(f'<section class="nav-group"><h2>附錄與模擬考</h2><ul>{"".join(appendix_links)}</ul></section>')

    qa_count = sum(len(qas(topic)) for topic in TOPICS)
    practice_count = sum(len(practice_questions(topic)) for topic in TOPICS)
    mock_count = sum(len(items) for items in MOCK_EXAMS.values())
    term_count = sum(len(term_cards(topic)) for topic in TOPICS)
    search_json = json.dumps(search_items, ensure_ascii=False).replace("</", "<\\/")
    doc = TEMPLATE.format(
        nav="\n".join(nav),
        articles="\n".join(articles),
        search_json=search_json,
        pygments_css="",
        chapter_count=len(TOPICS),
        qa_count=qa_count,
        practice_count=practice_count,
        mock_count=mock_count,
        term_count=term_count,
        service_count=service_count,
    )
    doc = "\n".join(line.rstrip() for line in doc.splitlines()) + "\n"
    OUTPUT.write_text(doc, encoding="utf-8")
    print(
        f"Built {OUTPUT.name}: {len(TOPICS)} chapters, {qa_count} chapter Q&A, "
        f"{practice_count} chapter practice questions, "
        f"{mock_count} mock questions, {term_count} term cards, "
        f"{service_count} service atlas entries, {len(emitted)} source notes, "
        f"{OUTPUT.stat().st_size / 1024 / 1024:.1f} MB"
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="從零準備 AWS Solutions Architect Associate 與 Professional：視覺化架構、具體案例、完整 exam task coverage、服務選型、跨雲 patterns 與逐選項題解。">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23232f3e'/%3E%3Ctext x='32' y='43' text-anchor='middle' font-size='32' fill='%23ff9900'%3EA%3C/text%3E%3C/svg%3E">
<title>AWS Solutions Architect 雙證全攻略 — SAA + SAP</title>
<style>
:root {{
  --bg:#eef2f5; --paper:#fffdfa; --paper2:#f5f7f8; --ink:#172331; --muted:#5b6875;
  --line:#d8e0e6; --navy:#223d5a; --orange:#a85200; --amber:#e08b24; --blue:#24729f;
  --green:#247057; --red:#a74747; --purple:#7255a3; --shadow:0 15px 42px rgba(24,48,67,.11);
  --sidebar:22rem;
}}
html[data-theme="dark"] {{
  --bg:#0f171d; --paper:#172129; --paper2:#1e2a33; --ink:#edf4f7; --muted:#adbac4;
  --line:#344551; --navy:#8cc7e8; --orange:#ffad42; --amber:#ffc16a; --blue:#78c5ed;
  --green:#75d0aa; --red:#ff9999; --purple:#c3a7ff; --shadow:0 18px 45px rgba(0,0,0,.35);
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; scroll-padding-top:1rem; }}
body {{ margin:0; color:var(--ink); background:var(--bg); font-family:-apple-system,BlinkMacSystemFont,
  "Segoe UI","Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif; line-height:1.78; }}
a {{ color:var(--blue); }}
#progress {{ position:fixed; z-index:100; inset:0 auto auto 0; height:4px; width:0;
  background:linear-gradient(90deg,#ff9900,#4db4e7,#8b71c7); }}
.sidebar {{ position:fixed; inset:0 auto 0 0; width:var(--sidebar); z-index:50; overflow:auto;
  padding:1rem .85rem 2rem; background:var(--paper); border-right:1px solid var(--line); }}
.brand {{ display:flex; justify-content:space-between; align-items:center; gap:.5rem; padding:.2rem .35rem 1rem; }}
.brand a {{ color:var(--ink); font-weight:850; text-decoration:none; }}
.icon-button {{ width:2.35rem; height:2.35rem; border:1px solid var(--line); border-radius:.65rem;
  color:var(--ink); background:var(--paper2); cursor:pointer; }}
.search-wrap {{ position:relative; margin-bottom:1rem; }}
#search {{ width:100%; padding:.65rem .7rem; border:1px solid var(--line); border-radius:.65rem;
  color:var(--ink); background:var(--paper2); font:inherit; }}
#search-count {{ min-height:1.2rem; color:var(--muted); font-size:.72rem; }}
.nav-group {{ margin:1rem 0; }}
.nav-group h2 {{ margin:0 0 .3rem; padding:0 .4rem; border:0; color:var(--muted);
  font-size:.67rem; letter-spacing:.06em; text-transform:uppercase; }}
.nav-group ul {{ margin:0; padding:0; list-style:none; }}
.nav-group a {{ display:flex; gap:.45rem; padding:.3rem .4rem; border-radius:.4rem;
  color:var(--muted); text-decoration:none; font-size:.75rem; line-height:1.35; }}
.nav-group a span {{ flex:0 0 2.2rem; color:var(--orange); font-variant-numeric:tabular-nums; }}
.nav-group a:hover,.nav-group a.active {{ color:var(--navy); background:color-mix(in srgb,var(--orange) 11%,transparent); }}
.hero {{ margin-left:var(--sidebar); padding:4.2rem clamp(1.2rem,5vw,5.2rem) 3.2rem; color:white;
  background:radial-gradient(circle at 85% 20%,rgba(255,153,0,.24),transparent 24rem),
    radial-gradient(circle at 12% 100%,rgba(62,169,218,.25),transparent 27rem),
    linear-gradient(135deg,#172839,#243d56 55%,#342d4f); }}
.hero-inner {{ max-width:76rem; margin:auto; }}
.eyebrow {{ color:#ffd08b; font-size:.76rem; font-weight:750; letter-spacing:.15em; text-transform:uppercase; }}
.hero h1 {{ max-width:66rem; margin:.55rem 0; font-size:clamp(2.25rem,5vw,4.35rem); line-height:1.08; letter-spacing:-.04em; }}
.subtitle {{ max-width:62rem; color:#e7eff4; font-size:1.08rem; }}
.hero-map {{ max-width:70rem; padding:1rem 1.1rem; overflow:auto; border:1px solid rgba(255,255,255,.2);
  border-radius:.8rem; color:#fff; background:rgba(0,0,0,.22); white-space:pre; font: .8rem/1.6 ui-monospace,monospace; }}
.badges,.hero-actions {{ display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }}
.badge {{ padding:.28rem .66rem; border:1px solid rgba(255,255,255,.22); border-radius:99px;
  background:rgba(255,255,255,.07); font-size:.76rem; }}
.button {{ display:inline-flex; align-items:center; min-height:2.5rem; padding:.48rem .8rem;
  border:1px solid rgba(255,255,255,.28); border-radius:.6rem; color:#fff;
  background:rgba(255,255,255,.08); text-decoration:none; cursor:pointer; }}
.main {{ margin-left:var(--sidebar); padding:2rem clamp(1rem,4vw,4.5rem) 7rem; }}
.chapter {{ max-width:76rem; margin:0 auto 2rem; padding:clamp(1.2rem,3.8vw,3.3rem);
  border:1px solid var(--line); border-radius:1rem; background:var(--paper); box-shadow:var(--shadow); }}
.prologue {{ border-top:7px solid var(--orange); }}
.appendix {{ border-top:6px solid var(--blue); }}
.part-kicker {{ color:var(--orange); font-size:.75rem; font-weight:850; letter-spacing:.11em; text-transform:uppercase; }}
h1,h2,h3 {{ line-height:1.3; scroll-margin-top:1rem; }}
h1 {{ margin:.55rem 0 1rem; font-size:clamp(1.8rem,4vw,2.65rem); }}
h2 {{ margin:2.25rem 0 .85rem; padding-bottom:.42rem; border-bottom:1px solid var(--line); font-size:1.42rem; }}
h3 {{ margin:1.45rem 0 .5rem; color:var(--navy); font-size:1.08rem; }}
p,li {{ overflow-wrap:anywhere; }}
.chapter-question {{ max-width:75ch; color:var(--muted); font-size:1.1rem; font-weight:670; }}
.chapter-meta,.service-badges {{ display:flex; flex-wrap:wrap; gap:.4rem; margin:.7rem 0 1.1rem; }}
.chapter-meta span,.service-badges span {{ padding:.2rem .58rem; border-radius:99px; color:var(--navy);
  background:color-mix(in srgb,var(--blue) 10%,var(--paper2)); font-size:.72rem; }}
.service-badges span {{ color:var(--green); }}
.chapter-position {{ display:grid; grid-template-columns:1fr 1.1fr 1fr; gap:.6rem; margin:1rem 0; }}
.position-card {{ display:flex; flex-direction:column; min-width:0; padding:.7rem .8rem; border:1px solid var(--line);
  border-radius:.68rem; color:var(--ink); background:var(--paper2); text-decoration:none; }}
.position-card span {{ color:var(--muted); font-size:.65rem; font-weight:800; text-transform:uppercase; }}
.position-card strong {{ margin-top:.22rem; font-size:.82rem; }}
.position-card.current {{ border-color:var(--orange); background:color-mix(in srgb,var(--orange) 9%,var(--paper)); }}
.muted {{ opacity:.7; }}
.journey-map {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.45rem; padding:.9rem;
  border:1px solid var(--line); border-radius:.8rem; background:var(--paper2); }}
.journey-node {{ min-height:3.7rem; padding:.5rem .35rem; border:1px solid var(--line); border-radius:.55rem;
  background:var(--paper); color:var(--muted); text-align:center; font-size:.68rem; line-height:1.3; }}
.journey-node b {{ display:block; color:var(--orange); }}
.journey-node.active {{ color:#fff; border-color:var(--orange); background:linear-gradient(145deg,var(--orange),#8f4b13); }}
.journey-node.active b {{ color:#fff; }}
.callout {{ margin:1rem 0; padding:.9rem 1rem; border:1px solid var(--line); border-left:5px solid var(--orange);
  border-radius:.7rem; background:var(--paper2); }}
.callout strong:first-child {{ display:block; margin-bottom:.3rem; color:var(--orange); }}
.community {{ border-left-color:var(--purple); }}
.community strong:first-child {{ color:var(--purple); }}
.portable {{ border-left-color:var(--green); }}
.portable strong:first-child {{ color:var(--green); }}
.version {{ border-left-color:var(--blue); }}
.version strong:first-child {{ color:var(--blue); }}
.chapter-story {{ width:100%; max-width:none; margin:2rem 0 1.4rem; }}
.chapter-story h2 {{ font-size:1.62rem; }}
.chapter-story p {{ margin:.95rem 0; font-size:1rem; line-height:1.9; }}
.chapter-story .story-lead {{ font-size:1.12rem; line-height:1.9; }}
.chapter-story .story-lead::first-letter {{ float:left; margin:.08rem .12rem 0 0; color:var(--orange);
  font-size:3.05rem; font-weight:850; line-height:.8; }}
.reference-box {{ margin:1.25rem 0; border-left-color:var(--amber); background:var(--paper2); }}
.reference-box > summary {{ padding:.88rem 1rem; color:var(--ink); font-size:.94rem; }}
.reference-box > div {{ padding:.15rem 1rem 1rem; }}
.chapter-map {{ border-left-color:var(--blue); }}
.component-narrative,.deep-explanation {{ width:100%; max-width:none; margin:1rem 0; }}
.story-section,.deep-explanation section {{ margin:1.35rem 0; padding:0 0 0 1rem;
  border:0; border-left:4px solid var(--green); background:transparent; }}
.story-section h3,.deep-explanation h3 {{ margin:0 0 .48rem; }}
.story-section p,.deep-explanation p {{ margin:.55rem 0; line-height:1.88; }}
.term-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }}
.term-card {{ padding:.9rem; border:1px solid var(--line); border-top:4px solid var(--amber);
  border-radius:.72rem; background:var(--paper2); }}
.term-card h3 {{ margin:0 0 .6rem; color:var(--ink); }}
.term-card div {{ padding:.58rem .65rem; border-radius:.55rem; background:var(--paper); }}
.term-card div + div {{ margin-top:.45rem; }}
.term-card span,.context-grid span {{ display:block; color:var(--orange); font-size:.66rem;
  font-weight:850; letter-spacing:.07em; text-transform:uppercase; }}
.term-card p,.context-grid p {{ margin:.12rem 0 0; font-size:.88rem; }}
.concept-glossary {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem; }}
.concept-definition {{ padding:.75rem .82rem; border:1px solid var(--line); border-left:4px solid var(--green);
  border-radius:.64rem; background:var(--paper2); }}
.concept-definition h3 {{ margin:0 0 .3rem; font-size:.98rem; }}
.concept-definition p {{ margin:0; font-size:.86rem; }}
.takeaway-list {{ max-width:78ch; padding:0; list-style:none; counter-reset:takeaway; }}
.takeaway-list li {{ position:relative; margin:.55rem 0; padding:.35rem .4rem .35rem 3rem;
  border:0; background:transparent; }}
.takeaway-list li::before {{ counter-increment:takeaway; content:counter(takeaway);
  position:absolute; left:.5rem; top:.32rem; display:grid; place-items:center; width:1.65rem; height:1.65rem;
  border-radius:50%; color:#fff; background:var(--orange); font-weight:850; }}
.component-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; }}
.component-card {{ padding:.95rem; border:1px solid var(--line); border-top:5px solid var(--blue);
  border-radius:.72rem; background:var(--paper2); }}
.component-card h3 {{ margin:0 0 .65rem; color:var(--ink); }}
.component-card div {{ padding:.5rem .6rem; border-radius:.5rem; background:var(--paper); }}
.component-card div + div {{ margin-top:.42rem; }}
.component-card span {{ color:var(--orange); font-size:.68rem; font-weight:850;
  letter-spacing:.06em; text-transform:uppercase; }}
.component-card p {{ margin:.12rem 0 0; font-size:.88rem; }}
.setting-manual {{ display:grid; gap:1rem; margin:1rem 0; }}
.setting-component {{ padding:.9rem; border:1px solid var(--line); border-radius:.76rem; background:var(--paper2); }}
.setting-component > h3 {{ margin:0 0 .75rem; }}
.setting-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; }}
.setting-guide {{ padding:.78rem; border:1px solid var(--line); border-top:4px solid var(--amber);
  border-radius:.64rem; background:var(--paper); }}
.setting-guide h4 {{ margin:0 0 .55rem; color:var(--navy); font-size:.95rem; }}
.setting-guide h4 code {{ white-space:normal; }}
.setting-guide div {{ padding:.48rem .55rem; border-radius:.48rem; background:var(--paper2); }}
.setting-guide div + div {{ margin-top:.4rem; }}
.setting-guide span {{ display:block; color:var(--orange); font-size:.64rem; font-weight:850;
  letter-spacing:.06em; text-transform:uppercase; }}
.setting-guide p {{ margin:.1rem 0 0; font-size:.83rem; }}
.context-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; }}
.context-grid section {{ padding:.8rem; border:1px solid var(--line); border-radius:.68rem; background:var(--paper2); }}
pre {{ overflow:auto; margin:1rem 0; padding:1rem; border:1px solid var(--line); border-radius:.72rem;
  background:#edf3f5; color:#173849; line-height:1.55; }}
pre code {{ font: .83rem/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
.architecture-diagram {{ border-left:6px solid var(--orange); font-weight:650; white-space:pre; }}
.diagram-guide {{ color:var(--muted); font-size:.9rem; }}
.network-overview {{ margin:1rem 0 1.35rem; padding:1.05rem; border:1px solid var(--line);
  border-radius:.9rem; background:var(--paper2); }}
.external-node,.gateway-node {{ max-width:42rem; margin:.35rem auto; padding:.72rem .9rem;
  border:2px solid var(--blue); border-radius:.72rem; background:var(--paper); text-align:center; }}
.gateway-node {{ border-color:var(--orange); }}
.external-node strong,.gateway-node strong {{ display:block; color:var(--navy); }}
.external-node span,.gateway-node span {{ display:block; color:var(--muted); font-size:.82rem; }}
.network-arrow {{ margin:.3rem 0; color:var(--green); text-align:center; font-size:.82rem; font-weight:750; }}
.vpc-boundary {{ margin-top:.55rem; padding:.9rem; border:3px solid var(--navy); border-radius:.85rem;
  background:var(--paper); }}
.vpc-title {{ margin:-.2rem 0 .65rem; color:var(--navy); font-size:1.05rem; font-weight:850; }}
.az-columns {{ display:grid; grid-template-columns:1.35fr 1fr; gap:.85rem; }}
.az-column {{ padding:.75rem; border:1px dashed var(--line); border-radius:.75rem; background:var(--paper2); }}
.az-column h3 {{ margin:0 0 .65rem; }}
.subnet {{ margin:.55rem 0; padding:.72rem; border:1px solid var(--line); border-left:6px solid var(--blue);
  border-radius:.65rem; background:var(--paper); }}
.public-subnet {{ border-left-color:var(--orange); }}
.private-subnet {{ border-left-color:var(--blue); }}
.isolated-subnet {{ border-left-color:var(--green); }}
.subnet b,.subnet code,.subnet > span {{ display:block; }}
.subnet code {{ margin-top:.45rem; padding:.28rem .4rem; white-space:normal; background:var(--paper2); }}
.resource-row {{ display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.45rem; }}
.resource-row span {{ padding:.2rem .48rem; border:1px solid var(--line); border-radius:99px;
  background:var(--paper2); font-size:.76rem; }}
.secondary-az .subnet {{ min-height:4.45rem; }}
.secondary-az p {{ color:var(--muted); font-size:.82rem; }}
.network-overview figcaption {{ margin-top:.75rem; padding:.65rem .75rem; border-radius:.55rem;
  color:var(--muted); background:var(--paper2); font-size:.86rem; }}
.mental-model {{ width:100%; max-width:none; }}
.mental-model p {{ margin:.75rem 0; line-height:1.9; }}
.role-map {{ min-width:62rem; }}
.role-map td:first-child {{ min-width:11rem; }}
.role-map small {{ display:block; margin-top:.2rem; color:var(--muted); font-size:.7rem; }}
.flow-grid,.walkthrough-grid {{ display:grid; gap:.58rem; }}
.flow-card {{ display:grid; grid-template-columns:2.05rem 1fr; gap:.65rem; align-items:start;
  padding:.7rem .82rem; border:1px solid var(--line); border-radius:.66rem; background:var(--paper2); }}
.flow-card > span {{ display:grid; place-items:center; width:1.85rem; height:1.85rem; border-radius:50%;
  color:#fff; background:var(--orange); font-size:.75rem; font-weight:850; }}
.walkthrough-grid .flow-card > span {{ background:var(--blue); }}
.flow-card p {{ margin:0; }}
.decision-table,.service-atlas,table {{ width:100%; border-collapse:collapse; margin:1rem 0; font-size:.88rem; }}
.table-scroll {{ overflow:auto; }}
.decision-table {{ min-width:68rem; }}
th,td {{ padding:.65rem .72rem; border:1px solid var(--line); vertical-align:top; text-align:left; }}
th {{ background:var(--paper2); color:var(--navy); }}
.good {{ color:var(--green); }} .bad {{ color:var(--red); }}
.config-example {{ position:relative; margin:1rem 0 1.5rem; padding:1rem; border:1px solid var(--line);
  border-radius:.76rem; background:var(--paper2); }}
.config-example h3 {{ margin:.05rem 4rem .5rem 0; }}
.code-label {{ position:absolute; top:1rem; right:1rem; padding:.15rem .45rem; border-radius:99px;
  color:#fff; background:var(--navy); font-size:.68rem; font-weight:800; text-transform:uppercase; }}
.config-code {{ margin:.65rem 0; background:#eaf0f3; color:#102f3f; white-space:pre; }}
.config-notes {{ margin:.7rem 0 0; padding-left:1.35rem; }}
.config-notes li {{ margin:.45rem 0; }}
.survey-supplements {{ margin:1.5rem 0; }}
.survey-note {{ padding:.75rem .85rem; border-radius:.62rem; color:var(--muted); background:var(--paper2); }}
.survey-supplement {{ position:relative; margin:1.35rem 0; padding:1rem;
  border:1px solid var(--line); border-top:6px solid var(--purple); border-radius:.82rem; background:var(--paper2); }}
.survey-supplement > h2 {{ margin:.15rem 0 .8rem; }}
.survey-supplement .code-label {{ position:static; display:inline-block; margin:.2rem 0 0; }}
.supplement-notes li {{ margin:.55rem 0; }}
.supplement-sources {{ padding-left:1.2rem; }}
.supplement-sources li {{ margin:.35rem 0; }}
.question-provenance {{ margin-top:.9rem; padding:.75rem .85rem; border:1px solid var(--line);
  border-radius:.6rem; color:var(--muted); background:var(--paper); font-size:.78rem; }}
.question-provenance p {{ margin:.3rem 0; }}
.worked-example {{ margin:1.6rem 0; padding:1rem 1.05rem; border:1px solid var(--line);
  border-left:6px solid var(--green); border-radius:.82rem; background:var(--paper2); }}
.worked-example > h2 {{ margin:.15rem 0 .8rem; }}
.route-table-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; }}
.route-table-card {{ min-width:0; padding:.75rem; border:1px solid var(--line); border-radius:.68rem;
  background:var(--paper); overflow:auto; }}
.route-table-card h3 {{ margin:0 0 .3rem; }}
.route-table-card p {{ margin:.2rem 0 .55rem; font-size:.8rem; }}
.route-table-card table {{ min-width:32rem; margin:.4rem 0; font-size:.78rem; }}
.packet-walk li {{ margin:.7rem 0; }}
.misconception {{ border-left-color:var(--red); }}
.misconception strong:first-child {{ color:var(--red); }}
.example-result {{ border-left-color:var(--blue); }}
.trade-grid,.exam-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; }}
.trade-grid section,.exam-grid section {{ padding:.8rem; border:1px solid var(--line); border-radius:.68rem; background:var(--paper2); }}
.trade-grid span {{ display:grid; place-items:center; width:1.7rem; height:1.7rem; border-radius:50%;
  color:#fff; background:var(--red); font-weight:800; }}
.trade-grid p {{ margin:.3rem 0 0; }}
.exam-grid section:first-child {{ border-top:5px solid var(--blue); }}
.exam-grid section:last-child {{ border-top:5px solid var(--purple); }}
.scope-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; margin-top:.8rem; }}
.scope-grid section {{ padding:.85rem; border:1px solid var(--line); border-radius:.7rem; background:var(--paper2); }}
.scope-grid section:first-child {{ border-top:5px solid var(--blue); }}
.scope-grid section:last-child {{ border-top:5px solid var(--purple); }}
.scope-grid h3 {{ margin:0 0 .45rem; }}
.scope-grid ul {{ margin:.3rem 0; padding-left:1.25rem; }}
.lab-list li {{ margin:.45rem 0; }}
details {{ margin:.7rem 0; border:1px solid var(--line); border-left:4px solid var(--blue);
  border-radius:.65rem; background:var(--paper2); }}
summary {{ padding:.72rem .85rem; cursor:pointer; color:var(--navy); font-weight:760; }}
details > div {{ padding:0 .9rem .85rem; }}
.answer-instruction {{ color:var(--muted); }}
.source-list,.research-ledger {{ padding-left:0; list-style:none; }}
.source-list li,.research-ledger li {{ margin:.45rem 0; padding:.55rem .65rem; border:1px solid var(--line);
  border-radius:.55rem; background:var(--paper2); }}
.source-kind {{ display:inline-block; min-width:5.5rem; margin-right:.5rem; padding:.1rem .4rem;
  border-radius:99px; color:#fff; background:var(--blue); text-align:center; font-size:.65rem; }}
.source-kind.community {{ background:var(--purple); }}
.mock-question {{ margin:1.15rem 0; padding:1rem; border:1px solid var(--line); border-radius:.75rem; background:var(--paper2); }}
.mock-question h3 {{ margin:0 0 .45rem; }}
.chapter-exam-question {{ margin:1.15rem 0; padding:1rem; border:1px solid var(--line);
  border-left:5px solid var(--purple); border-radius:.75rem; background:var(--paper2); }}
.chapter-exam-question h3 {{ margin:.45rem 0; }}
.question-meta {{ display:flex; flex-wrap:wrap; gap:.4rem; }}
.question-meta span {{ padding:.16rem .5rem; border-radius:99px; color:var(--purple);
  background:color-mix(in srgb,var(--purple) 10%,var(--paper)); font-size:.7rem; font-weight:800; }}
.option-analysis {{ padding-left:1.2rem; }}
.option-analysis li {{ margin:.65rem 0; padding:.6rem .7rem; border-left:4px solid var(--line);
  background:var(--paper); }}
.choices {{ list-style:none; padding:0; }}
.choices li {{ margin:.45rem 0; padding:.55rem .65rem; border:1px solid var(--line); border-radius:.55rem; background:var(--paper); }}
.correct-answer {{ padding:.55rem .7rem; border-radius:.55rem; color:#fff; background:var(--green); font-weight:850; }}
.atlas-question td {{ padding:0 .6rem .5rem; border-top:0; }}
.atlas-question details {{ margin:0; }}
.glossary-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; }}
.glossary-grid section {{ padding:.8rem; border:1px solid var(--line); border-radius:.65rem; background:var(--paper2); }}
.warning {{ padding:.8rem 1rem; border-left:5px solid var(--red); background:color-mix(in srgb,var(--red) 8%,var(--paper2)); }}
code {{ padding:.1rem .28rem; border-radius:.3rem; background:color-mix(in srgb,var(--blue) 8%,var(--paper2)); }}
footer {{ margin-left:var(--sidebar); padding:2rem; color:var(--muted); text-align:center; }}
@media (max-width:1050px) {{
  .sidebar {{ position:static; width:auto; max-height:32rem; }}
  .hero,.main,footer {{ margin-left:0; }}
}}
@media (max-width:760px) {{
  .chapter-position,.context-grid,.term-grid,.takeaway-list,.component-grid,.deep-explanation,
  .concept-glossary,.setting-grid,.trade-grid,.exam-grid,.scope-grid,.glossary-grid,
  .az-columns,.route-table-grid {{
    grid-template-columns:1fr;
  }}
  .journey-map {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .chapter {{ padding:1.1rem; border-radius:.65rem; }}
  th,td {{ padding:.5rem; }}
}}
@media print {{
  .sidebar,#progress,.hero-actions {{ display:none; }}
  .hero,.main,footer {{ margin-left:0; }}
  .hero {{ color:#000; background:#fff; padding:1rem; }}
  .subtitle,.eyebrow {{ color:#333; }}
  .chapter {{ box-shadow:none; break-before:page; }}
  details > div {{ display:block; }}
}}
{pygments_css}
</style>
</head>
<body>
<div id="progress" aria-hidden="true"></div>
<aside class="sidebar">
  <div class="brand"><a href="#start-here">AWS Architect 雙證手冊</a>
  <button class="icon-button" id="theme" aria-label="切換深色模式">◐</button></div>
  <div class="search-wrap"><input id="search" type="search" placeholder="搜尋章節、服務、pattern">
  <div id="search-count" aria-live="polite"></div></div>
  <nav>{nav}</nav>
</aside>
<header class="hero">
  <div class="hero-inner">
    <div class="eyebrow">SAA-C03 · SAP-C02 · ANNOUNCED SAP-C03 WATCHLIST · VERIFIED 2026-10-01</div>
    <h1>AWS Solutions Architect 雙證全攻略</h1>
    <p class="subtitle">從零建立雲端架構藍圖：不只背服務，而是看懂request、data、control、
    failure與cost flow；以具體架構案例、社群易錯點、完整task coverage和逐選項題解驗收。</p>
    <pre class="hero-map">requirement → architecture mechanism → failure boundary → evidence
        ↓                   ↓                    ↓
     SAA 選型           SAP 企業取捨         跨雲實務 pattern</pre>
    <div class="badges">
      <span class="badge">{chapter_count} 章</span><span class="badge">{term_count} 張概念卡</span>
      <span class="badge">{qa_count} 組章內 Q&amp;A</span>
      <span class="badge">{practice_count} 題章內考題</span><span class="badge">{mock_count} 題模擬考</span>
      <span class="badge">{service_count} 項 Service Atlas</span>
    </div>
    <div class="hero-actions">
      <a class="button" href="#start-here">開始閱讀</a>
      <button class="button" onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">展開所有答案</button>
      <button class="button" onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">收合所有答案</button>
      <button class="button" onclick="window.print()">列印 / PDF</button>
    </div>
  </div>
</header>
<main class="main" data-epub-chapters>
{articles}
</main>
<footer>原創教學與模擬題，不包含 exam dumps · 技術行為以 AWS 官方文件為準 · Community notes 用於易錯點與學習策略</footer>
<script>
const DATA={search_json};
const links=[...document.querySelectorAll('.nav-group a')];
const search=document.getElementById('search');
const count=document.getElementById('search-count');
search.addEventListener('input',()=>{{
  const q=search.value.trim().toLowerCase(); let shown=0;
  for(const link of links){{
    const id=link.getAttribute('href')?.slice(1);
    const item=DATA.find(x=>x.id===id);
    const ok=!q || `${{link.textContent}} ${{item?.text||''}}`.toLowerCase().includes(q);
    link.closest('li').hidden=!ok; if(ok) shown++;
  }}
  count.textContent=q?`${{shown}} 個符合結果`:'';
}});
const progress=document.getElementById('progress');
const update=()=>{{
  const max=document.documentElement.scrollHeight-innerHeight;
  progress.style.width=`${{max>0?scrollY/max*100:0}}%`;
}};
addEventListener('scroll',update,{{passive:true}}); addEventListener('resize',update); update();
const theme=document.getElementById('theme');
theme.addEventListener('click',()=>{{
  const dark=document.documentElement.dataset.theme==='dark';
  document.documentElement.dataset.theme=dark?'light':'dark';
  localStorage.setItem('aws-book-theme',dark?'light':'dark');
}});
document.documentElement.dataset.theme=localStorage.getItem('aws-book-theme')||'light';
const observer=new IntersectionObserver(entries=>{{
  for(const entry of entries) if(entry.isIntersecting){{
    links.forEach(link=>link.classList.toggle('active',link.getAttribute('href')==='#'+entry.target.id));
  }}
}},{{rootMargin:'-20% 0px -72% 0px'}});
document.querySelectorAll('.chapter[id]').forEach(node=>observer.observe(node));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
