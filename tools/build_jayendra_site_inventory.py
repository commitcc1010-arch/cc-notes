#!/usr/bin/env python3
"""Inventory every post URL in Jayendra Patil's sitemap.

This is a scope ledger, not a claim that all 520 posts belong in an SAA/SAP
book.  Exact architecture-pattern links are mapped by the curated audit; other
posts receive a conservative topic candidate or an explicit out-of-scope flag.
"""
from __future__ import annotations

import argparse
import csv
import re
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from aws_architect_external_coverage import JAYENDRA_PATTERNS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITEMAP = "https://jayendrapatil.com/post-sitemap.xml"
OUTPUT = ROOT / "tools" / "jayendra_site_inventory.csv"
SUMMARY = ROOT / "tools" / "jayendra_site_inventory_summary.md"

TOPIC_RULES = (
    ((r"\bvpc\b", r"\bcidr\b", r"\bsubnet\b", r"\bnat\b", r"route-table", r"network-acl", r"security-group"), (4, 11, 12, 13, 14)),
    ((r"transit-gateway", r"vpc-peering", r"privatelink", r"vpc-lattice"), (15,)),
    ((r"route-?53", r"\bdns\b", r"resolver"), (5, 16, 20)),
    ((r"cloudfront", r"global-accelerator", r"lambdaedge", r"edge-functions"), (17,)),
    ((r"\balb\b", r"\bnlb\b", r"\bgwlb\b", r"load-balanc"), (18,)),
    ((r"direct-connect", r"\bvpn\b", r"cloud-wan", r"hybrid-network"), (19, 80)),
    ((r"\biam\b", r"identity-center", r"\bsts\b", r"federat", r"permission-boundar", r"\bscp"), (21, 22, 23, 24, 25, 26, 82)),
    ((r"\bkms\b", r"cloudhsm", r"encryption", r"key-polic"), (27,)),
    ((r"secrets-manager", r"parameter-store", r"certificate", r"\bacm\b", r"\bmtls\b"), (18, 28)),
    ((r"\bwaf\b", r"\bshield\b", r"network-firewall", r"firewall-manager"), (29, 80)),
    ((r"guardduty", r"inspector", r"macie", r"detective", r"security-hub", r"security-lake", r"incident-response"), (30, 76, 81)),
    ((r"\bec2\b", r"\bami\b", r"placement-group", r"\bena\b", r"\befa\b"), (3, 32, 33, 34)),
    ((r"\blambda\b", r"serverless", r"api-gateway", r"cognito"), (3, 36, 37, 98)),
    ((r"\becs\b", r"\beks\b", r"fargate", r"container", r"\becr\b"), (3, 38, 89)),
    ((r"\bbatch\b", r"\bemr\b", r"\bspark\b", r"spot-instance"), (39,)),
    ((r"beanstalk", r"app-runner", r"lightsail"), (40,)),
    ((r"\bs3\b", r"simple-storage", r"glacier", r"object-lock", r"storage-class"), (6, 41, 42)),
    ((r"\bebs\b", r"instance-store", r"\befs\b", r"\bfsx\b"), (6, 33, 43)),
    ((r"storage-gateway", r"datasync", r"transfer-family", r"snow-family"), (44,)),
    ((r"\brds\b", r"\baurora\b", r"rds-proxy", r"read-replica", r"multi-az"), (7, 45, 46)),
    ((r"dynamodb", r"\bdax\b"), (7, 47)),
    ((r"elasticache", r"\bredis\b", r"memcached", r"\bcache\b"), (7, 48, 110)),
    ((r"redshift", r"athena", r"\bglue\b", r"lake-formation", r"data-lake"), (49, 102)),
    ((r"kinesis", r"\bmsk\b", r"kafka", r"firehose", r"flink"), (50, 54)),
    ((r"opensearch", r"documentdb", r"neptune", r"timestream", r"keyspaces"), (51,)),
    ((r"\bsqs\b", r"dead-letter", r"\bdlq\b"), (52,)),
    ((r"\bsns\b", r"eventbridge", r"publish-subscribe"), (53,)),
    ((r"step-functions", r"\bsaga\b", r"workflow"), (55, 58, 95)),
    ((r"retry", r"backoff", r"jitter", r"idempot", r"circuit-break", r"backpressure"), (56, 57, 59)),
    ((r"disaster-recovery", r"\bdr\b", r"\brto\b", r"\brpo\b", r"backup", r"resilience"), (9, 61, 62, 63, 77, 84, 103, 114)),
    ((r"cloudwatch", r"\bx-ray\b", r"observab", r"open-telemetry"), (66, 67, 113)),
    ((r"cloudtrail", r"\bconfig\b", r"trusted-advisor"), (66, 76, 78, 81, 90)),
    ((r"savings-plan", r"reserved-instance", r"cost-optim", r"compute-optimizer", r"cost-explorer", r"\bcur\b"), (68, 69, 70, 71, 85, 115)),
    ((r"pricing", r"consolidated-billing", r"resource-tags", r"support-plan", r"support-tier"), (68, 69, 70, 71, 78, 85, 115)),
    ((r"cloudformation", r"\bcdk\b", r"infrastructure-as-code", r"\biac\b"), (72, 73)),
    ((r"codepipeline", r"codebuild", r"codedeploy", r"\bcicd\b", r"ci-cd"), (74,)),
    ((r"systems-manager", r"session-manager", r"patch-manager", r"\bssm\b"), (75, 76)),
    ((r"organizations", r"control-tower", r"landing-zone", r"multi-account"), (25, 79, 100)),
    ((r"resource-access-manager", r"service-catalog", r"root-access"), (25, 26, 79)),
    ((r"resource-based-polic",), (22, 26)),
    ((r"single-sign-on", r"directory-service", r"workspace"), (23, 24, 82)),
    ((r"verified-access",), (24,)),
    ((r"verified-permissions",), (26,)),
    ((r"bastion", r"network-connectivity-option", r"hybrid-environment", r"network-architecture-pattern"), (12, 15, 19, 20, 80)),
    ((r"global-vs-regional", r"regions-availability-zones", r"services-overview", r"interaction-tools"), (1, 2, 10)),
    ((r"application-auto-scaling", r"auto-scaling", r"autoscaling"), (34, 64)),
    ((r"elb-monitoring",), (18, 66)),
    ((r"security-whitepaper", r"risk-and-compliance", r"securing-data-at-rest", r"ddos-resiliency", r"intrusion-detection"), (10, 27, 29, 30, 31, 112)),
    ((r"architecting-for-the-cloud",), (8, 10, 105, 106, 107)),
    ((r"storage-options", r"data-transfer-services"), (6, 43, 44, 71)),
    ((r"simple-email-service", r"\bses\b"), (53,)),
    ((r"quicksight",), (49, 102)),
    ((r"sagemaker", r"amazon-nova", r"amazon-q", r"enterprise-ai-assistant", r"context-knowledge-graph", r"continuum-ai-security"), (91, 92, 93, 94, 96, 104)),
    ((r"iot-core",), (53, 112)),
    ((r"developer-tools",), (72, 74, 75)),
    ((r"blue-green-deployment",), (73, 74)),
    ((r"data-pipeline",), (49, 50, 102)),
    ((r"transform-code-modernization",), (87, 88, 89, 116)),
    ((r"architecture-patterns-reference-diagrams",), (1, 105, 116)),
    ((r"migration", r"\b7rs\b", r"application-discovery", r"\bmgn\b", r"\bdms\b", r"\bsct\b"), (86, 87, 88, 101, 116)),
    ((r"bedrock", r"\brag\b", r"generative-ai", r"genai", r"agentic-ai", r"guardrail"), (91, 92, 93, 94, 95, 96, 104)),
)

META_MARKERS = (
    "certification",
    "exam",
    "learning-path",
    "practice-test",
    "practice-question",
    "study-guide",
    "cheat-sheet",
    "interview-question",
)
NON_AWS_MARKERS = (
    "solr",
    "ibm-bluemix",
    "black-friday",
    "data-science",
    "data-analytics",
    "python-",
    "java-",
    "google-cloud",
    "azure-",
    "partnerships-that-have-upgraded",
)
LEGACY_MARKERS = (
    "opsworks",
    "aws-importexport",
    "aws-swf",
    "aws-elasticsearch",
    "aws-cloudsearch",
    "aws-elastic-transcoder",
)


def classify(url: str, exact: dict[str, tuple[int, ...]]) -> tuple[str, tuple[int, ...], str]:
    normalized_url = url.rstrip("/") + "/"
    slug = urlparse(url).path.strip("/").lower()
    if normalized_url in exact:
        return "mapped-pattern", exact[normalized_url], "curated 54-pattern audit"
    if any(marker in slug for marker in NON_AWS_MARKERS):
        return "out-of-scope", (), "non-AWS or non-SAA/SAP article"
    if any(marker in slug for marker in LEGACY_MARKERS):
        return "legacy-reference", (), "retired/legacy service; retained only for migration recognition"
    if any(marker in slug for marker in META_MARKERS):
        return "study-meta", (1,), "exam strategy/version material; official guide overrides"
    chapters: set[int] = set()
    for patterns, targets in TOPIC_RULES:
        if any(re.search(pattern, slug) for pattern in patterns):
            chapters.update(targets)
    if chapters:
        return "topic-candidate", tuple(sorted(chapters)), "keyword candidate; curated chapters remain authoritative"
    if "aws" in slug or "amazon" in slug:
        return "manual-review", (), "AWS-related slug without a safe automatic chapter mapping"
    return "out-of-scope", (), "no SAA/SAP AWS topic signal"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sitemap-file", type=Path)
    args = parser.parse_args()
    raw = (
        args.sitemap_file.read_text(encoding="utf-8")
        if args.sitemap_file
        else urllib.request.urlopen(DEFAULT_SITEMAP, timeout=30).read().decode()
    )
    urls = re.findall(r"<loc>(.*?)</loc>", raw)
    exact = {
        url.rstrip("/") + "/": tuple(chapters)
        for _, _, url, chapters, _ in JAYENDRA_PATTERNS
    }
    rows = []
    for url in urls:
        status, chapters, note = classify(url, exact)
        rows.append((url, status, " ".join(map(str, chapters)), note))
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("url", "status", "candidate_chapters", "note"))
        writer.writerows(rows)
    counts = Counter(row[1] for row in rows)
    manual = [row[0] for row in rows if row[1] == "manual-review"]
    summary = [
        "# Jayendra sitemap inventory summary",
        "",
        f"- Snapshot URLs: **{len(rows)}**",
        *[f"- `{status}`: **{count}**" for status, count in sorted(counts.items())],
        "",
        "This inventory guarantees every sitemap URL receives a scope decision.",
        "A `topic-candidate` is not a factual endorsement; the curated 54-pattern",
        "map and AWS official documentation remain authoritative.",
        "",
        "## Manual-review queue",
        "",
        *[f"- {url}" for url in manual],
        "",
    ]
    SUMMARY.write_text("\n".join(summary).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {len(rows)} URLs; manual review={len(manual)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
