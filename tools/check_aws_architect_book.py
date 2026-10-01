#!/usr/bin/env python3
"""Quality gate for the generated AWS Solutions Architect handbook."""
from __future__ import annotations

import csv
import re
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aws_architect_content import (  # noqa: E402
    TOPICS,
    blueprint,
    chapter_story,
    labs,
    mechanics,
    qas,
    term_cards,
)
from aws_architect_deep_content import (  # noqa: E402
    components,
    config_examples,
    key_takeaways,
    practice_questions,
    scope_guide,
)
from aws_architect_external_coverage import (  # noqa: E402
    JAYENDRA_PATTERNS,
    OFFICIAL_OVERRIDE_NOTES,
)
from aws_architect_mock_exam import build_mock_exams  # noqa: E402
from aws_architect_model import PARTS, SAP_TASKS, SAA_TASKS, TASKS  # noqa: E402
from aws_architect_scope import SAP_SCOPE, SAA_SCOPE  # noqa: E402
from aws_architect_setting_guides import (  # noqa: E402
    chapter_glossary,
    setting_guides,
)
from aws_architect_survey_supplements import survey_supplements  # noqa: E402


BOOK = ROOT / "aws-solutions-architect-saa-sap.html"
SOURCE_DIR = ROOT / "AWS Solutions Architect"
JAYENDRA_INVENTORY = ROOT / "tools" / "jayendra_site_inventory.csv"


class BookParser(HTMLParser):
    """Collect only the structural facts that affect the reading experience."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.remote_assets: list[str] = []
        self.chapter_stack: list[dict] = []
        self.article_stack: list[bool] = []
        self.chapters: list[dict] = []
        self.details = Counter()
        self.mock_questions = 0
        self.service_rows = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        classes = set(data.get("class", "").split())
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "a" and data.get("href"):
            self.hrefs.append(data["href"])
        if tag in {"script", "link", "img", "source"}:
            asset = data.get("src") or data.get("href")
            if asset and asset.startswith(("http://", "https://", "//")):
                self.remote_assets.append(asset)

        is_main_chapter = bool(
            tag == "article" and "chapter" in classes and data.get("data-chapter")
        )
        if tag == "article":
            self.article_stack.append(is_main_chapter)
        if is_main_chapter:
            chapter = {
                "number": int(data["data-chapter"]),
                "text": [],
                "term_cards": 0,
                "stories": 0,
                "story_sections": 0,
                "role_maps": 0,
                "worked_examples": 0,
                "reference_boxes": 0,
                "concept_definitions": 0,
                "takeaways": 0,
                "component_cards": 0,
                "setting_components": 0,
                "setting_guides": 0,
                "config_examples": 0,
                "survey_supplements": 0,
                "practice": 0,
                "practice_answers": 0,
                "option_analyses": 0,
                "scope_guides": 0,
                "qas": 0,
                "diagrams": 0,
                "labs": 0,
                "lab_items": 0,
                "exam_grids": 0,
                "sources": 0,
                "community": 0,
                "portable": 0,
            }
            self.chapter_stack.append(chapter)
            self.chapters.append(chapter)

        chapter = self.chapter_stack[-1] if self.chapter_stack else None
        if chapter is not None:
            chapter["stories"] += int("chapter-story" in classes)
            chapter["story_sections"] += int("story-section" in classes)
            chapter["role_maps"] += int(tag == "table" and "role-map" in classes)
            chapter["worked_examples"] += int("worked-example" in classes)
            chapter["reference_boxes"] += int("reference-box" in classes)
            chapter["term_cards"] += int("term-card" in classes)
            chapter["concept_definitions"] += int("concept-definition" in classes)
            chapter["takeaways"] += int(tag == "ol" and "takeaway-list" in classes)
            chapter["component_cards"] += int("component-card" in classes)
            chapter["setting_components"] += int("setting-component" in classes)
            chapter["setting_guides"] += int(
                tag == "article" and "setting-guide" in classes
            )
            chapter["config_examples"] += int("config-example" in classes)
            chapter["survey_supplements"] += int("survey-supplement" in classes)
            chapter["practice"] += int(
                tag == "article" and "chapter-exam-question" in classes
            )
            chapter["practice_answers"] += int(
                tag == "details" and "chapter-exam-answer" in classes
            )
            chapter["option_analyses"] += int(
                tag == "ul" and "option-analysis" in classes
            )
            chapter["scope_guides"] += int(tag == "div" and "scope-grid" in classes)
            chapter["qas"] += int(tag == "details" and "qa" in classes)
            chapter["diagrams"] += int(
                (tag == "pre" and "architecture-diagram" in classes)
                or (tag == "figure" and "network-overview" in classes)
            )
            chapter["labs"] += int(tag == "ol" and "lab-list" in classes)
            chapter["exam_grids"] += int(tag == "div" and "exam-grid" in classes)
            chapter["sources"] += int(tag == "ul" and "source-list" in classes)
            chapter["community"] += int("community" in classes)
            chapter["portable"] += int("portable" in classes)
            if tag == "li" and any(
                open_tag == "ol" and "lab-list" in open_classes
                for open_tag, open_classes in getattr(self, "_open_tags", [])
            ):
                chapter["lab_items"] += 1

        if tag == "details":
            if "qa" in classes:
                self.details["chapter"] += 1
            elif "chapter-exam-answer" in classes:
                self.details["practice"] += 1
            elif "mock-answer" in classes:
                self.details["mock"] += 1
            elif "atlas-qa" in classes:
                self.details["atlas"] += 1
        self.mock_questions += int(tag == "article" and "mock-question" in classes)
        self.service_rows += int(tag == "tr" and "atlas-question" in classes)

        if not hasattr(self, "_open_tags"):
            self._open_tags: list[tuple[str, set[str]]] = []
        self._open_tags.append((tag, classes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self.article_stack:
            if self.article_stack.pop() and self.chapter_stack:
                self.chapter_stack.pop()
        if hasattr(self, "_open_tags"):
            for index in range(len(self._open_tags) - 1, -1, -1):
                if self._open_tags[index][0] == tag:
                    del self._open_tags[index:]
                    break

    def handle_data(self, data: str) -> None:
        if self.chapter_stack:
            self.chapter_stack[-1]["text"].append(data)


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def normalized_service(value: str) -> str:
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\b(?:Amazon|AWS)\b", "", value, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalized_question_text(value: str) -> str:
    """Normalize wording enough to catch visually different duplicate choices."""

    return re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", value.casefold())


def relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    high, low = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (high + 0.05) / (low + 0.05)


def all_scope_services() -> dict[str, str]:
    result: dict[str, str] = {}
    for scope in (SAA_SCOPE, SAP_SCOPE):
        for services in scope.values():
            for service in services:
                result.setdefault(normalized_service(service), service)
    return result


def check_curriculum(problems: list[str]) -> None:
    numbers = [topic.number for topic in TOPICS]
    if numbers != list(range(1, 117)):
        fail(problems, "章節編號不是完整的 1–116")
    if len({topic.title for topic in TOPICS}) != 116:
        fail(problems, "章節標題重複")
    if len(PARTS) != 12:
        fail(problems, f"預期 12 個 Part，實際 {len(PARTS)}")

    covered_tasks = {task for topic in TOPICS for task in topic.tasks}
    missing_tasks = set(TASKS) - covered_tasks
    if missing_tasks:
        fail(problems, f"章節未覆蓋官方 tasks: {sorted(missing_tasks)}")

    for topic in TOPICS:
        if len(term_cards(topic)) < 4:
            fail(problems, f"Ch {topic.number} 少於 4 張概念卡")
        if len(mechanics(topic)) < 6:
            fail(problems, f"Ch {topic.number} 少於 6 個機制步驟")
        if len(labs(topic)) < 5:
            fail(problems, f"Ch {topic.number} 少於 5 個實驗")
        chapter_qas = qas(topic)
        if len(chapter_qas) < 5:
            fail(problems, f"Ch {topic.number} 少於 5 組問答")
        for index, (question, answer) in enumerate(chapter_qas, 1):
            if len(question) < 12:
                fail(problems, f"Ch {topic.number} Q{index} 問題過短")
            if len(answer) < 150:
                fail(problems, f"Ch {topic.number} Q{index} 答案不足 150 字元")
        if len(blueprint(topic).splitlines()) < 9:
            fail(problems, f"Ch {topic.number} 架構圖太短")


def check_external_coverage(problems: list[str]) -> None:
    if len(JAYENDRA_PATTERNS) != 54:
        fail(
            problems,
            f"Jayendra architecture-pattern map預期54項，實際{len(JAYENDRA_PATTERNS)}",
        )
    urls = [row[2] for row in JAYENDRA_PATTERNS]
    if len(urls) != len(set(urls)):
        fail(problems, "Jayendra architecture-pattern map有重複URL")
    valid_statuses = {"covered", "supplemented", "adjacent"}
    for category, title, url, chapters, status in JAYENDRA_PATTERNS:
        if not category or not title or not url.startswith("https://jayendrapatil.com/"):
            fail(problems, f"Jayendra map欄位不完整: {title!r}")
        if status not in valid_statuses:
            fail(problems, f"Jayendra map status異常: {status}")
        if not chapters or any(chapter not in range(1, 117) for chapter in chapters):
            fail(problems, f"Jayendra map chapter異常: {title}")
    if len(OFFICIAL_OVERRIDE_NOTES) < 4:
        fail(problems, "Jayendra official-override notes不足")
    if not JAYENDRA_INVENTORY.exists():
        fail(problems, "缺少Jayendra全站sitemap inventory")
        return
    with JAYENDRA_INVENTORY.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 520:
        fail(problems, f"Jayendra sitemap inventory預期520 URLs，實際{len(rows)}")
    status_counts = Counter(row["status"] for row in rows)
    expected_counts = {
        "legacy-reference": 8,
        "mapped-pattern": 54,
        "out-of-scope": 104,
        "study-meta": 68,
        "topic-candidate": 286,
    }
    if status_counts != expected_counts:
        fail(
            problems,
            "Jayendra sitemap分類數量改變，需重新人工稽核: "
            f"{dict(status_counts)}",
        )
    manual = [row["url"] for row in rows if row["status"] == "manual-review"]
    if manual:
        fail(problems, f"Jayendra sitemap inventory仍有{len(manual)}項待人工分類")


def check_deep_content(problems: list[str]) -> None:
    """Reject generic filler and missing service/config/exam teaching layers."""

    prompts: list[str] = []
    story_openings: list[str] = []
    for topic in TOPICS:
        profiles = components(topic)
        if len(profiles) != len(topic.services) or not profiles:
            fail(problems, f"Ch {topic.number} component profiles 與 services 不一致")
        story_title, story_paragraphs = chapter_story(topic)
        if len(story_title) < 12 or len(story_paragraphs) != 4:
            fail(problems, f"Ch {topic.number} 故事開場結構不完整")
        if any(len(paragraph) < 85 for paragraph in story_paragraphs):
            fail(problems, f"Ch {topic.number} 故事段落過短，尚未形成連貫敘事")
        story_openings.append(story_paragraphs[0])
        for name, profile in profiles:
            fields = {
                "purpose": (profile.purpose, 17),
                "mechanism": (profile.mechanism, 38),
                "config": (profile.config, 60),
                "choose": (profile.choose, 17),
                "replace": (profile.replace, 23),
            }
            for field, (value, minimum) in fields.items():
                if len(value) < minimum:
                    fail(
                        problems,
                        f"Ch {topic.number} {name} {field} 過短：{len(value)} < {minimum}",
                    )
            if profile.purpose.startswith("本章把"):
                fail(problems, f"Ch {topic.number} {name} 仍使用 generic profile fallback")

        if len(key_takeaways(topic)) != 8:
            fail(problems, f"Ch {topic.number} 重點整理不是 8 點")
        if len(scope_guide(topic)) < 2:
            fail(problems, f"Ch {topic.number} 缺少 SAA/SAP 分層")
        glossary = chapter_glossary(topic, profiles)
        if len(glossary) < 4:
            fail(problems, f"Ch {topic.number} 新名詞字典少於 4 個定義")
        if any(len(definition) < 35 for _, definition in glossary):
            fail(problems, f"Ch {topic.number} 新名詞字典有定義過短")

        for name, profile in profiles:
            guides = setting_guides(name, profile)
            if len(guides) < 3:
                fail(problems, f"Ch {topic.number} {name} 設定說明少於 3 項")
            guide_by_name = {guide.name: guide for guide in guides}
            for guide in guides:
                fields = (guide.controls, guide.when, guide.configure, guide.pitfall)
                if any(len(value) < 30 for value in fields):
                    fail(
                        problems,
                        f"Ch {topic.number} {name}/{guide.name} 設定解釋不足",
                    )
                if "control-plane設定" in guide.controls:
                    fail(
                        problems,
                        f"Ch {topic.number} {name}/{guide.name} 仍使用 generic setting fallback",
                    )
            semantic_contracts = {
                ("AWS Certification", "domain weights"): (
                    "能力領域",
                    "控制名稱如何被解析",
                ),
                ("AWS Regions", "service availability"): ("目標Region", "收集多少歷史資料"),
                ("Amazon OpenSearch Service", "domain／serverless collection"): (
                    "provisioned OpenSearch cluster",
                    "控制名稱如何被解析",
                ),
                ("VPC Peering", "DNS resolution"): (
                    "hostname翻成IP",
                    "control-plane設定",
                ),
                ("Amazon CloudFront", "cache policy"): (
                    "cache key",
                    "control-plane設定",
                ),
                ("Application Load Balancer", "stickiness"): (
                    "session affinity",
                    "control-plane設定",
                ),
            }
            for (contract_component, setting_name), (
                required,
                forbidden,
            ) in semantic_contracts.items():
                if name != contract_component or setting_name not in guide_by_name:
                    continue
                controls = guide_by_name[setting_name].controls
                if required not in controls or forbidden in controls:
                    fail(
                        problems,
                        f"Ch {topic.number} {name}/{setting_name} 語意分類錯誤",
                    )

        for example in config_examples(topic):
            if len(example.code) < 150:
                fail(problems, f"Ch {topic.number} config {example.title} 過短")
            if len(example.notes) < 3 or any(len(note) < 28 for note in example.notes):
                fail(problems, f"Ch {topic.number} config {example.title} 逐行解釋不足")

        questions = practice_questions(topic)
        expected_question_count = 10 if questions and questions[0].question_id else 5
        if len(questions) != expected_question_count:
            fail(
                problems,
                f"Ch {topic.number} 章內考題不是 {expected_question_count} 題",
            )
        for index, question in enumerate(questions, 1):
            prompts.append(question.prompt)
            if len(question.choices) not in (4, 5):
                fail(problems, f"Ch {topic.number} 練習題 {index} 選項數異常")
            if len(question.choices) != len(question.explanations):
                fail(problems, f"Ch {topic.number} 練習題 {index} 缺逐選項解析")
            normalized_choices = [
                normalized_question_text(choice) for choice in question.choices
            ]
            if len(normalized_choices) != len(set(normalized_choices)):
                fail(
                    problems,
                    f"Ch {topic.number} 練習題 {index} 有重複選項",
                )
            if any(len(reason) < 32 for reason in question.explanations):
                fail(problems, f"Ch {topic.number} 練習題 {index} 有解析不足 32 字元")
            expected_answers = 2 if question.kind == "multi" else 1
            if len(question.answers) != expected_answers:
                fail(
                    problems,
                    f"Ch {topic.number} 練習題 {index} 答案數與題型不一致",
                )
            if any(answer < 0 or answer >= len(question.choices) for answer in question.answers):
                fail(problems, f"Ch {topic.number} 練習題 {index} 答案 index 越界")

    expected_prompts = sum(len(practice_questions(topic)) for topic in TOPICS)
    if len(prompts) != expected_prompts:
        fail(problems, f"章內考題預期 {expected_prompts}，實際 {len(prompts)}")
    if len(prompts) != len(set(prompts)):
        fail(problems, f"章內考題有 {len(prompts) - len(set(prompts))} 個重複題幹")
    if len(story_openings) != len(set(story_openings)):
        fail(problems, "章節故事開場有重複，讀感仍像固定模板")
    all_examples = [
        example for topic in TOPICS for example in config_examples(topic)
    ]
    if len(all_examples) < 25:
        fail(problems, f"真正的config/policy範例不足25個，實際{len(all_examples)}")
    if any("configuration_review:" in example.code for example in all_examples):
        fail(problems, "仍有作者review contract冒充AWS config")

    joined = "\n".join(
        example.code
        for number in (15, 17, 18, 21, 22, 41)
        for example in config_examples(TOPICS[number - 1])
    )
    for phrase in (
        "sts:AssumeRole",
        "PermissionsBoundary",
        "DenyInsecureTransport",
        "aws:SecureTransport",
        "s3:ListBucket",
        "s3:GetObject",
        "BucketOwnerEnforced",
        "BlockPublicAcls",
        "Principal",
        "AllowDnsResolutionFromRemoteVpc",
        "modify-vpc-peering-connection-options",
        "AWS::CloudFront::OriginAccessControl",
        "ParametersInCacheKeyAndForwardedToOrigin",
        "stickiness.enabled",
        "stickiness.lb_cookie.duration_seconds",
        "idle_timeout.timeout_seconds",
    ):
        if phrase not in joined:
            fail(problems, f"IAM/S3 核心實例缺少 {phrase}")


def check_mock_exams(problems: list[str]) -> None:
    exams = build_mock_exams(TOPICS)
    sap_exam_name = "SAP-C02 + announced C03 watchlist"
    expected = {"Diagnostic": 20, "SAA-C03": 65, sap_exam_name: 75}
    actual = {name: len(questions) for name, questions in exams.items()}
    if actual != expected:
        fail(problems, f"模擬考題數錯誤: {actual}")

    prompts: list[str] = []
    multiple_response = 0
    for name, questions in exams.items():
        for question in questions:
            prompts.append(question.prompt)
            multiple_response += int(question.kind == "Multiple response")
            if len(question.choices) != len(question.explanations):
                fail(problems, f"{name} Q{question.number} 選項與解析數量不同")
            if question.kind == "Multiple response" and len(question.answers) != 2:
                fail(problems, f"{name} Q{question.number} 複選題答案數不是 2")
            if question.kind == "Multiple choice" and len(question.answers) != 1:
                fail(problems, f"{name} Q{question.number} 單選題答案數不是 1")
            if any(index < 0 or index >= len(question.choices) for index in question.answers):
                fail(problems, f"{name} Q{question.number} 答案 index 越界")
            if any(len(reason) < 45 for reason in question.explanations):
                fail(problems, f"{name} Q{question.number} 有選項解析過短")
    if multiple_response < 20:
        fail(problems, f"複選題不足 20 題，實際 {multiple_response}")
    if len(prompts) != len(set(prompts)):
        fail(problems, f"模擬題 prompt 有 {len(prompts) - len(set(prompts))} 題重複")

    saa_covered = {question.task for question in exams["SAA-C03"]}
    sap_covered = {question.task for question in exams[sap_exam_name]}
    if saa_covered != set(SAA_TASKS):
        fail(problems, f"SAA mock task coverage 不完整: {sorted(set(SAA_TASKS) - saa_covered)}")
    if sap_covered != set(SAP_TASKS):
        fail(problems, f"SAP mock task coverage 不完整: {sorted(set(SAP_TASKS) - sap_covered)}")


def check_html(problems: list[str]) -> BookParser:
    if not BOOK.exists():
        fail(problems, f"找不到 {BOOK.name}")
        return BookParser()
    raw = BOOK.read_text(encoding="utf-8")
    parser = BookParser()
    parser.feed(raw)

    numbers = [chapter["number"] for chapter in parser.chapters]
    if numbers != list(range(1, 117)):
        fail(problems, f"HTML 主章節不是完整 1–116: {numbers[:4]}…{numbers[-4:]}")
    for chapter in parser.chapters:
        number = chapter["number"]
        visible = len(re.sub(r"\s+", " ", "".join(chapter["text"])).strip())
        expected = {
            "stories": 1,
            "role_maps": 1,
            "worked_examples": 1,
            "reference_boxes": 3,
            "term_cards": 4,
            "concept_definitions": len(
                chapter_glossary(
                    TOPICS[number - 1], components(TOPICS[number - 1])
                )
            ),
            "takeaways": 1,
            "component_cards": len(TOPICS[number - 1].services),
            "setting_components": len(TOPICS[number - 1].services),
            "setting_guides": sum(
                len(setting_guides(name, profile))
                for name, profile in components(TOPICS[number - 1])
            ),
            "config_examples": len(config_examples(TOPICS[number - 1])),
            "survey_supplements": len(survey_supplements(number)),
            "practice": len(practice_questions(TOPICS[number - 1])),
            "practice_answers": len(practice_questions(TOPICS[number - 1])),
            "option_analyses": len(practice_questions(TOPICS[number - 1])),
            "scope_guides": 1,
            "qas": 6,
            "diagrams": 1,
            "labs": 1,
            "lab_items": 5,
            "exam_grids": 1,
            "sources": 1,
            "community": 1,
            "portable": 1,
        }
        for key, minimum in expected.items():
            if chapter[key] < minimum:
                fail(problems, f"Ch {number} HTML {key}={chapter[key]}，低於 {minimum}")
        expected_configs = len(config_examples(TOPICS[number - 1]))
        if chapter["config_examples"] != expected_configs:
            fail(
                problems,
                f"Ch {number} HTML config_examples={chapter['config_examples']}，"
                f"預期 {expected_configs}",
            )
        # Length is only a floor against accidentally empty chapters. A larger
        # fixed target rewarded repeating the same profile under several
        # headings, so structural teaching checks above carry the quality bar.
        if visible < 18_000:
            fail(problems, f"Ch {number} 可見內容不足 18,000 字元，實際 {visible}")

    if "先把本章看成一個contract" in raw:
        fail(problems, "HTML仍含舊版規格文件式心智模型")
    if "configuration_review:" in raw:
        fail(problems, "HTML仍有作者review contract冒充AWS config")
    if "真實 Config／Policy／Parameters：每一行為什麼存在？" in raw:
        fail(problems, "HTML仍使用會誤導讀者的通用config標題")
    if "可執行 Python 概念模型" in raw or "本章Python模型" in raw:
        fail(problems, "HTML仍含已移除的通用Python概念模型")
    for number in range(1, 117):
        marker = f'data-chapter="{number}"'
        marker_at = raw.find(marker)
        article_start = raw.rfind("<article", 0, marker_at)
        article_end = raw.find('<article class="chapter"', marker_at + len(marker))
        chapter_raw = raw[article_start : article_end if article_end != -1 else len(raw)]
        story_at = chapter_raw.find('class="chapter-story"')
        diagram_candidates = [
            position
            for position in (
                chapter_raw.find('class="architecture-diagram"'),
                chapter_raw.find('class="network-overview"'),
            )
            if position >= 0
        ]
        diagram_at = min(diagram_candidates) if diagram_candidates else -1
        term_at = chapter_raw.find('class="term-card"')
        setting_at = chapter_raw.find('class="setting-guide"')
        if not (0 <= story_at < diagram_at < term_at < setting_at):
            fail(
                problems,
                f"Ch {number} 閱讀順序不是故事 → 全圖 → 名詞工具箱 → 設定工具箱",
            )

    if len(parser.ids) != len(set(parser.ids)):
        duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
        fail(problems, f"HTML 有重複 id: {duplicates[:8]}")
    id_set = set(parser.ids)
    dangling = [href for href in parser.hrefs if href.startswith("#") and href[1:] not in id_set]
    if dangling:
        fail(problems, f"HTML 有 {len(dangling)} 個懸空內部連結")
    if parser.remote_assets:
        fail(problems, f"HTML 依賴遠端執行資產: {parser.remote_assets[:4]}")
    if parser.details["chapter"] != 696:
        fail(problems, f"HTML 章內 Q&A 預期 696，實際 {parser.details['chapter']}")
    expected_practice = sum(len(practice_questions(topic)) for topic in TOPICS)
    if parser.details["practice"] != expected_practice:
        fail(
            problems,
            f"HTML 章內考題答案預期 {expected_practice}，實際 {parser.details['practice']}",
        )
    if parser.mock_questions != 160 or parser.details["mock"] != 160:
        fail(
            problems,
            f"HTML mock 預期 160，題目={parser.mock_questions}、答案={parser.details['mock']}",
        )
    expected_services = len(all_scope_services())
    if parser.service_rows != expected_services or parser.details["atlas"] != expected_services:
        fail(
            problems,
            f"Service Atlas 預期 {expected_services}，rows={parser.service_rows}、QA={parser.details['atlas']}",
        )
    required_ids = {
        "start-here",
        "appendix-coverage",
        "appendix-service-atlas",
        "appendix-jayendra-coverage",
        "mock-diagnostic",
        "mock-saa-c03",
        "mock-sap-c02-announced-c03-watchlist",
    }
    missing_ids = required_ids - id_set
    if missing_ids:
        fail(problems, f"HTML 缺少關鍵附錄／模擬考: {sorted(missing_ids)}")
    for phrase in (
        "SAA-C03",
        "SAP-C02",
        "SAP-C03",
        "2026-10-27",
        "2026-11-17",
        "Bedrock Guardrails",
        "AgentCore Identity",
        "Step Functions human",
        "不包含 exam dumps",
    ):
        if phrase not in raw:
            fail(problems, f"HTML 缺少版本或誠信聲明: {phrase}")
    if re.search(r"\b(?:TODO|TBD)\b|lorem ipsum|待補(?:內容|章節)?", raw, re.I):
        fail(problems, "HTML 含未完成 placeholder")
    if BOOK.stat().st_size < 7_000_000:
        fail(problems, f"HTML 體積異常偏小: {BOOK.stat().st_size:,} bytes")

    root_css = re.search(r":root\s*\{([^}]+)\}", raw)
    dark_css = re.search(r'html\[data-theme="dark"\]\s*\{([^}]+)\}', raw)
    if not root_css or not dark_css:
        fail(problems, "找不到亮色或深色 CSS variables")
    else:
        def variables(block: str) -> dict[str, str]:
            return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block))

        for mode, palette in (
            ("light", variables(root_css.group(1))),
            ("dark", variables(dark_css.group(1))),
        ):
            for foreground in ("ink", "muted", "navy", "orange", "blue", "green", "red", "purple"):
                for background in ("paper", "paper2"):
                    ratio = contrast_ratio(palette[foreground], palette[background])
                    if ratio < 4.5:
                        fail(
                            problems,
                            f"{mode} {foreground}/{background} 對比度 {ratio:.2f}:1 低於 4.5:1",
                        )

    body = raw[raw.find("<script>") + len("<script>") : raw.rfind("</script>")]
    if body and subprocess.run(
        ["node", "--check", "-"],
        input=body,
        text=True,
        capture_output=True,
        check=False,
    ).returncode:
        fail(problems, "HTML inline JavaScript 無法通過 node --check")
    return parser


def check_service_atlas(problems: list[str]) -> None:
    raw = BOOK.read_text(encoding="utf-8")
    normalized_book = normalized_service(raw)
    missing = [
        display for key, display in all_scope_services().items()
        if key and key not in normalized_book
    ]
    if missing:
        fail(problems, f"Service Atlas 未納入官方 scope 服務: {missing[:10]}")


def check_sources(problems: list[str]) -> None:
    files = sorted(SOURCE_DIR.glob("*.md"))
    if len(files) != 13:
        fail(problems, f"Markdown source notes 預期 13 份，實際 {len(files)}")
    for path in files:
        text = path.read_text(encoding="utf-8")
        if len(text) < 2_000:
            fail(problems, f"{path.name} 內容異常偏短")
        if re.search(
            r"\b(?:TODO|TBD|PLACEHOLDER)\b|待補(?:內容|章節)?|(?:內容|章節)未完成",
            text,
            re.I,
        ):
            fail(problems, f"{path.name} 含 placeholder")


def check_question_publication_gates(problems: list[str]) -> None:
    """Require structural validation and independent review before publication."""
    for script, label in (
        ("check_aws_question_banks.py", "chapter question banks"),
        ("check_aws_question_reviews.py", "independent question reviews"),
    ):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stdout or result.stderr).strip().splitlines()
            suffix = f": {detail[0]}" if detail else ""
            fail(problems, f"{label} publication gate failed{suffix}")


def check_generator_idempotence(problems: list[str]) -> None:
    before = BOOK.read_bytes()
    with tempfile.TemporaryFile(mode="w+") as output:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_aws_architect_book.py")],
            cwd=ROOT,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "tools")},
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode:
        fail(problems, "書籍生成器重跑失敗")
    elif BOOK.read_bytes() != before:
        fail(problems, "書籍生成器重跑結果不一致")


def main() -> int:
    problems: list[str] = []
    config_count = sum(len(config_examples(topic)) for topic in TOPICS)
    glossary_count = sum(
        len(chapter_glossary(topic, components(topic))) for topic in TOPICS
    )
    setting_count = sum(
        len(setting_guides(name, profile))
        for topic in TOPICS
        for name, profile in components(topic)
    )
    checks = (
        ("question publication gates", check_question_publication_gates),
        ("curriculum", check_curriculum),
        ("external coverage", check_external_coverage),
        ("deep content", check_deep_content),
        ("mock exams", check_mock_exams),
        ("HTML", check_html),
        ("service atlas", check_service_atlas),
        ("Markdown sources", check_sources),
        ("idempotence", check_generator_idempotence),
    )
    for label, check in checks:
        check(problems)
        print(f"✓ {label}")

    if problems:
        print(f"\n❌ {len(problems)} quality gate failure(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        "\n✅ AWS book quality gate passed: 116 chapters, 464 term cards, "
        f"{glossary_count} chapter glossary definitions, {setting_count} setting guides, "
        f"{config_count} config/policy examples, "
        f"{sum(len(practice_questions(topic)) for topic in TOPICS)} chapter practice questions, "
        "696 chapter Q&A, 171 service entries, "
        "160 original mock questions, and all 34 official tasks covered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
