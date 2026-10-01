"""Shared data model for the AWS Solutions Architect SAA/SAP handbook."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Topic:
    number: int
    title: str
    problem: str
    decision: str
    alternative: str
    failure: str
    pattern: str
    scenario: str
    services: tuple[str, ...]
    tasks: tuple[str, ...]
    sources: tuple[str, ...]
    level: str


@dataclass(frozen=True)
class MockQuestion:
    number: int
    exam: str
    kind: str
    prompt: str
    choices: tuple[str, ...]
    answers: tuple[int, ...]
    explanations: tuple[str, ...]
    task: str
    chapter: int
    principle: str


def T(
    number: int,
    title: str,
    problem: str,
    decision: str,
    alternative: str,
    failure: str,
    pattern: str,
    scenario: str,
    services: Iterable[str],
    tasks: Iterable[str],
    sources: Iterable[str],
    level: str = "SAA → SAP",
) -> Topic:
    return Topic(
        number=number,
        title=title,
        problem=problem.strip(),
        decision=decision.strip(),
        alternative=alternative.strip(),
        failure=failure.strip(),
        pattern=pattern.strip(),
        scenario=scenario.strip(),
        services=tuple(services),
        tasks=tuple(tasks),
        sources=tuple(sources),
        level=level,
    )


PARTS = [
    {"part": 0, "title": "零背景 Cloud Primer", "slug": "cloud-primer", "range": (1, 10)},
    {"part": 1, "title": "Networking 與流量入口", "slug": "networking", "range": (11, 20)},
    {"part": 2, "title": "Identity、Security 與 Governance", "slug": "security", "range": (21, 31)},
    {"part": 3, "title": "Compute 與 Application Architecture", "slug": "compute", "range": (32, 40)},
    {"part": 4, "title": "Storage 與 Data Architecture", "slug": "data", "range": (41, 51)},
    {"part": 5, "title": "Integration 與 Distributed Systems", "slug": "integration", "range": (52, 60)},
    {"part": 6, "title": "Reliability、Performance 與 Cost", "slug": "reliability-cost", "range": (61, 71)},
    {"part": 7, "title": "Deployment 與 Operations", "slug": "operations", "range": (72, 78)},
    {"part": 8, "title": "SAP Enterprise Architecture", "slug": "enterprise", "range": (79, 90)},
    {"part": 9, "title": "AI 與新興架構", "slug": "ai", "range": (91, 96)},
    {"part": 10, "title": "完整實戰案例", "slug": "case-studies", "range": (97, 104)},
    {"part": 11, "title": "跨雲通用 Architecture Patterns", "slug": "patterns", "range": (105, 116)},
]


SAA_TASKS = {
    "SAA-1.1": "Design secure access to AWS resources",
    "SAA-1.2": "Design secure workloads and applications",
    "SAA-1.3": "Determine appropriate data security controls",
    "SAA-2.1": "Design scalable and loosely coupled architectures",
    "SAA-2.2": "Design highly available and/or fault-tolerant architectures",
    "SAA-3.1": "Determine high-performing and/or scalable storage solutions",
    "SAA-3.2": "Design high-performing and elastic compute solutions",
    "SAA-3.3": "Determine high-performing database solutions",
    "SAA-3.4": "Determine high-performing and/or scalable network architectures",
    "SAA-3.5": "Determine high-performing data ingestion and transformation solutions",
    "SAA-4.1": "Design cost-optimized storage solutions",
    "SAA-4.2": "Design cost-optimized compute solutions",
    "SAA-4.3": "Design cost-optimized database solutions",
    "SAA-4.4": "Design cost-optimized network architectures",
}


SAP_TASKS = {
    "SAP-1.1": "Architect network connectivity strategies",
    "SAP-1.2": "Prescribe security controls",
    "SAP-1.3": "Design reliable and resilient architectures",
    "SAP-1.4": "Design a multi-account AWS environment",
    "SAP-1.5": "Determine cost optimization and visibility strategies",
    "SAP-2.1": "Design a deployment strategy to meet business requirements",
    "SAP-2.2": "Design a solution to ensure business continuity",
    "SAP-2.3": "Determine security controls based on requirements",
    "SAP-2.4": "Design a strategy to meet reliability requirements",
    "SAP-2.5": "Design a solution to meet performance objectives",
    "SAP-2.6": "Determine a cost optimization strategy to meet solution goals",
    "SAP-3.1": "Determine a strategy to improve overall operational excellence",
    "SAP-3.2": "Determine a strategy to improve security",
    "SAP-3.3": "Determine a strategy to improve performance",
    "SAP-3.4": "Determine a strategy to improve reliability",
    "SAP-3.5": "Identify opportunities for cost optimizations",
    "SAP-4.1": "Select existing workloads and processes for potential migration",
    "SAP-4.2": "Determine the optimal migration approach for existing workloads",
    "SAP-4.3": "Determine a new architecture for existing workloads",
    "SAP-4.4": "Determine opportunities for modernization and enhancements",
}


TASKS = {**SAA_TASKS, **SAP_TASKS}


SOURCES = {
    "saa-guide": (
        "AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html",
        "official",
    ),
    "saa-sample": (
        "AWS Certified Solutions Architect – Associate (SAA-C03) Official Sample Questions",
        "https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf",
        "official",
    ),
    "saa-d1": (
        "SAA-C03 Domain 1: Design Secure Architectures",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html",
        "official",
    ),
    "saa-d2": (
        "SAA-C03 Domain 2: Design Resilient Architectures",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html",
        "official",
    ),
    "saa-d3": (
        "SAA-C03 Domain 3: Design High-Performing Architectures",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html",
        "official",
    ),
    "saa-d4": (
        "SAA-C03 Domain 4: Design Cost-Optimized Architectures",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain4.html",
        "official",
    ),
    "sap-guide": (
        "AWS Certified Solutions Architect – Professional (SAP-C02) Exam Guide",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html",
        "official",
    ),
    "sap-sample": (
        "AWS Certified Solutions Architect – Professional (SAP-C02) Official Sample Questions",
        "https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf",
        "official",
    ),
    "sap-d1": (
        "SAP-C02 Domain 1: Organizational Complexity",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html",
        "official",
    ),
    "sap-d2": (
        "SAP-C02 Domain 2: Design for New Solutions",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html",
        "official",
    ),
    "sap-d3": (
        "SAP-C02 Domain 3: Continuous Improvement",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html",
        "official",
    ),
    "sap-d4": (
        "SAP-C02 Domain 4: Migration and Modernization",
        "https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html",
        "official",
    ),
    "well-architected": (
        "AWS Well-Architected Framework",
        "https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html",
        "official",
    ),
    "security": (
        "AWS Security Reference Architecture",
        "https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html",
        "official",
    ),
    "iam": (
        "IAM Policy Evaluation Logic",
        "https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html",
        "official",
    ),
    "network": (
        "Amazon VPC User Guide",
        "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html",
        "official",
    ),
    "vpc-route-tables": (
        "Amazon VPC User Guide: Configure route tables",
        "https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html",
        "official",
    ),
    "vpc-public-private-example": (
        "Amazon VPC User Guide: VPC with public and private subnets",
        "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html",
        "official",
    ),
    "vpc-cli-example": (
        "Amazon VPC User Guide: Create a VPC with private subnets and NAT gateways using AWS CLI",
        "https://docs.aws.amazon.com/vpc/latest/userguide/create-a-vpc-with-private-subnets-and-nat-gateways-using-aws-cli.html",
        "official",
    ),
    "route53": (
        "Amazon Route 53 Developer Guide",
        "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html",
        "official",
    ),
    "cloudfront": (
        "Amazon CloudFront Developer Guide",
        "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html",
        "official",
    ),
    "compute": (
        "Amazon EC2 User Guide",
        "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
        "official",
    ),
    "lambda": (
        "AWS Lambda Developer Guide",
        "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
        "official",
    ),
    "containers": (
        "AWS Containers Decision Guide",
        "https://docs.aws.amazon.com/decision-guides/latest/containers-on-aws-how-to-choose/guide.html",
        "official",
    ),
    "s3": (
        "Amazon S3 User Guide",
        "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
        "official",
    ),
    "storage": (
        "AWS Storage Services Overview",
        "https://docs.aws.amazon.com/whitepapers/latest/aws-overview/storage-services.html",
        "official",
    ),
    "database": (
        "AWS Database Services Overview",
        "https://docs.aws.amazon.com/whitepapers/latest/aws-overview/database.html",
        "official",
    ),
    "dynamodb": (
        "Amazon DynamoDB Developer Guide",
        "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html",
        "official",
    ),
    "integration": (
        "AWS Prescriptive Guidance: Cloud Design Patterns",
        "https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/introduction.html",
        "official",
    ),
    "reliability": (
        "AWS Well-Architected Reliability Pillar",
        "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
        "official",
    ),
    "dr": (
        "Disaster Recovery of Workloads on AWS",
        "https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html",
        "official",
    ),
    "cost": (
        "AWS Well-Architected Cost Optimization Pillar",
        "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
        "official",
    ),
    "operations": (
        "AWS Well-Architected Operational Excellence Pillar",
        "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html",
        "official",
    ),
    "migration": (
        "AWS Prescriptive Guidance: Migration Strategy",
        "https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-journey.html",
        "official",
    ),
    "bedrock": (
        "Amazon Bedrock User Guide",
        "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",
        "official",
    ),
    "community-saa": (
        "Community SAA-C03 Study Guide",
        "https://github.com/ChathurangaVKD/AWS-Certified-Solutions-Architect-Associate-SAA-C03",
        "community",
    ),
    "community-traps": (
        "Community SAA Scenario Guides and Service Comparisons",
        "https://github.com/RonitSachdev/aws-saa-c03-guides",
        "community",
    ),
    "community-sap": (
        "Community SAP-C02 Study Guide",
        "https://github.com/LongBu/AWS-SAP-C02-Study-Guide",
        "community",
    ),
    "community-sap-notes": (
        "Community SAP-C02 Notes",
        "https://github.com/zhuweiyou/aws-sap-c02",
        "community",
    ),
    "repost-plan": (
        "AWS re:Post Community: 30-day SAA preparation discussion",
        "https://repost.aws/questions/QUw7MjHJqWSZyf_uMi6wgG4w/",
        "community",
    ),
    "repost-tips": (
        "AWS re:Post: Certification preparation tips and resources",
        "https://repost.aws/articles/ARb_Y9l1DpTmyIXR2Ei-W_Lw/",
        "community",
    ),
    "jayendra-index": (
        "Jayendra's Cloud Certification Study Notes and Topic Index",
        "https://jayendrapatil.com/",
        "community",
    ),
    "jayendra-patterns": (
        "Jayendra's AWS Architecture Patterns Reference Diagrams",
        "https://jayendrapatil.com/aws-architecture-patterns-reference-diagrams/",
        "community",
    ),
    "jayendra-iam": (
        "Jayendra's IAM Access Management Notes",
        "https://jayendrapatil.com/aws-iam-access-management/",
        "community",
    ),
    "jayendra-s3": (
        "Jayendra's Amazon S3 Study Notes",
        "https://jayendrapatil.com/aws-simple-storage-service-s3-overview/",
        "community",
    ),
    "aws-skill-builder-exam-prep": (
        "AWS Skill Builder: Exam Prep Standard Course for SAA-C03",
        "https://skillbuilder.aws/exam-prep/solutions-architect-associate",
        "official",
    ),
    "pluralsight-aws-learning": (
        "Pluralsight / A Cloud Guru AWS Learning Paths and Hands-on Labs",
        "https://www.pluralsight.com/product/cloud/aws",
        "community",
    ),
    "cantrill-saa-course": (
        "Adrian Cantrill: AWS Certified Solutions Architect Associate Course",
        "https://learn.cantrill.io/p/aws-certified-solutions-architect-associate-saa-c03",
        "community",
    ),
    "tutorials-dojo-saa": (
        "Tutorials Dojo: AWS Certified Solutions Architect Associate Study Guide",
        "https://tutorialsdojo.com/aws-certified-solutions-architect-associate-saa-c03/",
        "community",
    ),
    "cloud-academy-saa": (
        "Cloud Academy: AWS Solutions Architect Associate Learning Path",
        "https://cloudacademy.com/learning-paths/aws-solutions-architect-associate-saa-c03-certification-preparation-1/",
        "community",
    ),
    "s3-policy-examples": (
        "Amazon S3 User Guide: Bucket policy examples",
        "https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html",
        "official",
    ),
    "iam-policy-elements": (
        "IAM User Guide: JSON policy elements reference",
        "https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html",
        "official",
    ),
}
