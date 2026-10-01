"""Curated coverage map for Jayendra Patil's architecture-pattern index.

The index introduction says 58 posts, while the category tables contained 54
linked pattern pages in the 2026-10-01 snapshot.  We map every enumerated page
to this book and keep specialty-only depth explicitly out of the SAA/SAP
coverage claim.
"""
from __future__ import annotations


# category, title, URL, chapters, status
JAYENDRA_PATTERNS = (
    ("Core", "Three-Tier Web & Caching", "https://jayendrapatil.com/aws-three-tier-web-caching-architecture-elasticache-dax-cloudfront/", (35, 48, 97), "covered"),
    ("Core", "Serverless API Architecture", "https://jayendrapatil.com/aws-serverless-api-architecture-api-gateway-lambda/", (37, 98), "covered"),
    ("Core", "Event-Driven Serverless", "https://jayendrapatil.com/aws-event-driven-serverless-architecture/", (52, 53, 55, 58), "covered"),
    ("Core", "Container Platform", "https://jayendrapatil.com/aws-container-platform-architecture-ecs-eks-fargate/", (38, 89), "covered"),
    ("Core", "Multi-Region Active-Active", "https://jayendrapatil.com/aws-multi-region-active-active-architecture/", (61, 83, 103), "covered"),
    ("Core", "Disaster Recovery", "https://jayendrapatil.com/aws-disaster-recovery-architecture-strategies/", (62, 63, 103), "covered"),
    ("Core", "Auto Scaling & Performance", "https://jayendrapatil.com/aws-auto-scaling-performance-architecture-policies-predictive-warm-pools/", (34, 64), "covered"),
    ("Core", "Cost Optimization", "https://jayendrapatil.com/aws-cost-optimization-architecture-strategies/", (68, 69, 70, 71, 85, 115), "covered"),
    ("Networking", "VPC Connectivity Decision Guide", "https://jayendrapatil.com/aws-vpc-peering-vs-transit-gateway-vs-privatelink-decision-guide/", (15,), "covered"),
    ("Networking", "Hybrid Cloud Networking", "https://jayendrapatil.com/aws-hybrid-cloud-networking-architecture-direct-connect-transit-gateway/", (19, 80), "covered"),
    ("Networking", "Direct Connect Deep Dive", "https://jayendrapatil.com/aws-direct-connect-deep-dive-dx-gateway-lag-resiliency/", (19,), "covered"),
    ("Networking", "Global Traffic Management", "https://jayendrapatil.com/aws-global-traffic-management-route53-global-accelerator-cloudfront/", (16, 17, 83), "covered"),
    ("Networking", "Route 53 Resolver & Hybrid DNS", "https://jayendrapatil.com/aws-route53-resolver-hybrid-dns-dnssec-forwarding-split-horizon/", (20,), "supplemented"),
    ("Networking", "ALB vs NLB vs GWLB", "https://jayendrapatil.com/aws-alb-vs-nlb-vs-gwlb-load-balancer-decision-guide/", (18,), "covered"),
    ("Networking", "VPC Advanced: CIDR, ENI, IPv6", "https://jayendrapatil.com/aws-vpc-advanced-networking-cidr-eni-prefix-lists-ipv6/", (11, 13), "covered"),
    ("Networking", "Network Performance", "https://jayendrapatil.com/aws-network-performance-ena-efa-jumbo-frames-placement-groups/", (32,), "supplemented"),
    ("Security", "IAM Security", "https://jayendrapatil.com/aws-iam-security-architecture-scps-permission-boundaries-abac/", (21, 22, 25, 26), "covered"),
    ("Security", "Data Encryption", "https://jayendrapatil.com/aws-data-encryption-architecture-kms-cloudhsm-key-policies/", (27,), "covered"),
    ("Security", "Centralized Logging", "https://jayendrapatil.com/aws-centralized-logging-architecture-cloudtrail-security-lake/", (81,), "supplemented"),
    ("Security", "DDoS & Edge Protection", "https://jayendrapatil.com/aws-ddos-edge-protection-architecture-waf-shield-cloudfront/", (17, 29), "covered"),
    ("Security", "Incident Response", "https://jayendrapatil.com/aws-incident-response-architecture-forensics-containment-remediation/", (30, 76, 81), "supplemented"),
    ("Security", "Secrets & Certificate Management", "https://jayendrapatil.com/aws-secrets-certificate-management-secrets-manager-acm-rotation/", (18, 28), "supplemented"),
    ("Security", "Zero Trust Architecture", "https://jayendrapatil.com/aws-zero-trust-architecture-verified-access-vpc-lattice/", (15, 24), "supplemented"),
    ("Security", "Network Firewall & Inspection", "https://jayendrapatil.com/aws-network-firewall-traffic-inspection-ids-ips-gwlb/", (29, 80), "covered"),
    ("Security", "Federation & SSO", "https://jayendrapatil.com/aws-federation-sso-architecture-identity-center-cognito-saml/", (23, 24, 37), "covered"),
    ("Security", "Security Services", "https://jayendrapatil.com/aws-security-services-architecture-guardduty-security-hub/", (30,), "covered"),
    ("Security", "Config vs CloudTrail vs CloudWatch", "https://jayendrapatil.com/aws-config-vs-cloudtrail-vs-cloudwatch-compared/", (66, 76, 81), "covered"),
    ("Security", "Multi-Account Governance", "https://jayendrapatil.com/aws-multi-account-architecture-organizations-control-tower/", (25, 79, 100), "covered"),
    ("AI/ML", "GenAI Architecture", "https://jayendrapatil.com/aws-genai-architecture-bedrock-rag-agents-guardrails/", (91, 92, 93, 94, 95, 96), "covered"),
    ("AI/ML", "Agentic AI", "https://jayendrapatil.com/aws-agentic-ai-architecture-bedrock-agents-mcp-multi-agent/", (91, 94, 104), "covered"),
    ("AI/ML", "RAG Architecture", "https://jayendrapatil.com/aws-rag-architecture-bedrock-knowledge-bases/", (91,), "covered"),
    ("AI/ML", "RAG Advanced", "https://jayendrapatil.com/aws-rag-advanced-patterns-vector-db-hybrid-search-chunking-reranking/", (91, 96), "adjacent"),
    ("AI/ML", "GenAI Cost & Performance", "https://jayendrapatil.com/aws-genai-cost-performance-optimization-tokens-caching-model-routing/", (96,), "covered"),
    ("AI/ML", "GenAI Observability & Evaluation", "https://jayendrapatil.com/aws-genai-observability-evaluation-monitoring-llm-judge-testing/", (96,), "covered"),
    ("AI/ML", "GenAI Security & Guardrails", "https://jayendrapatil.com/aws-genai-security-guardrails-pii-prompt-injection-network-isolation/", (92, 93), "covered"),
    ("AI/ML", "Bedrock vs SageMaker", "https://jayendrapatil.com/aws-bedrock-vs-sagemaker/", (91,), "adjacent"),
    ("AI/ML", "MLOps Pipeline", "https://jayendrapatil.com/aws-mlops-pipeline-architecture-sagemaker/", (74, 96), "adjacent"),
    ("AI/ML", "Prompt Engineering", "https://jayendrapatil.com/aws-prompt-engineering-techniques-best-practices/", (93,), "adjacent"),
    ("AI/ML", "Responsible AI", "https://jayendrapatil.com/aws-responsible-ai-guardrails-governance/", (93,), "covered"),
    ("AI/ML", "AI Services Decision Guide", "https://jayendrapatil.com/aws-ai-services-decision-guide/", (91,), "adjacent"),
    ("Data", "Data Lake & Analytics", "https://jayendrapatil.com/aws-data-lake-analytics-architecture/", (49, 102), "covered"),
    ("Data", "Glue ETL & Data Pipeline", "https://jayendrapatil.com/aws-glue-etl-data-pipeline-architecture-catalog-crawlers-quality/", (49, 102), "covered"),
    ("Data", "EMR & Spark Architecture", "https://jayendrapatil.com/aws-emr-spark-architecture-cluster-modes-emrfs-optimization/", (39,), "covered"),
    ("Data", "Kinesis vs MSK Streaming", "https://jayendrapatil.com/aws-kinesis-vs-msk-kafka-streaming-comparison/", (50, 54), "covered"),
    ("Data", "RDS & Aurora Performance", "https://jayendrapatil.com/aws-rds-aurora-performance-read-replicas-proxy-global-insights/", (45, 46), "covered"),
    ("Data", "DynamoDB Advanced", "https://jayendrapatil.com/aws-dynamodb-advanced-streams-global-tables-ttl-capacity/", (47,), "covered"),
    ("Data", "Database Migration", "https://jayendrapatil.com/aws-database-migration-architecture-dms-sct/", (87,), "covered"),
    ("Data", "SNS vs SQS vs EventBridge", "https://jayendrapatil.com/aws-sns-vs-sqs-vs-eventbridge-comparison/", (52, 53), "covered"),
    ("DevOps", "CI/CD Pipeline", "https://jayendrapatil.com/aws-cicd-pipeline-architecture-codepipeline-codebuild/", (74,), "supplemented"),
    ("DevOps", "CloudFormation Advanced", "https://jayendrapatil.com/aws-cloudformation-advanced-stacksets-drift-custom-resources-guard/", (72, 73), "supplemented"),
    ("DevOps", "Systems Manager Operations", "https://jayendrapatil.com/aws-systems-manager-operations-patch-session-automation/", (75, 76), "covered"),
    ("Migration", "Migration Architecture: 7Rs", "https://jayendrapatil.com/aws-migration-architecture-7rs-tools-strategies/", (86, 87, 88, 116), "covered"),
    ("Migration", "Storage Gateway vs DataSync vs Snow", "https://jayendrapatil.com/aws-storage-gateway-vs-datasync-vs-snow-hybrid-data-transfer/", (44,), "covered"),
    ("Migration", "EFS vs FSx Decision Guide", "https://jayendrapatil.com/aws-efs-vs-fsx-decision-guide-shared-file-storage/", (43,), "covered"),
)


OFFICIAL_OVERRIDE_NOTES = (
    "該站 2026-06 的 SAA learning path 宣稱 SAA-C04 已公告且與 SAA-C03 並行；截至本書基線日，"
    "AWS 官方 certification 頁仍以 SAA-C03 為 current exam guide，因此本書不採納未被官方證實的版本資訊。",
    "該站部分文章仍寫『DynamoDB Global Tables 不支援 global strong consistency』；AWS 已提供 "
    "multi-Region strong consistency（MRSC）模式，選型必須區分 MREC 與 MRSC。",
    "服務停售、maintenance mode、Region availability、quota 與 feature support 都是時間敏感資訊；"
    "書中只把社群頁面當漏項雷達，最終行為與考試版本以 AWS 官方文件為準。",
    "架構索引涵蓋所有 12 張證照的內容；MLOps、Prompt Engineering、AI Services 等 specialty 深度被標為 adjacent，"
    "不會假裝成 SAA-C03／SAP-C02 必考範圍。",
)
