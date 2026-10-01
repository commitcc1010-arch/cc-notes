"""Official in-scope service snapshots verified on 2026-10-01.

The AWS exam guides explicitly describe these lists as non-exhaustive and
subject to change.  They are retained here to make the generated coverage
appendix deterministic and auditable.
"""

SAA_SCOPE = {
    "Analytics": ("Amazon Athena", "AWS Data Exchange", "Amazon Data Firehose", "Amazon EMR", "AWS Glue", "Amazon Kinesis", "AWS Lake Formation", "Amazon Managed Streaming for Apache Kafka (Amazon MSK)", "Amazon OpenSearch Service", "Amazon Quick", "Amazon Redshift"),
    "Application Integration": ("Amazon AppFlow", "Amazon EventBridge", "Amazon MQ", "Amazon SNS", "Amazon SQS", "AWS Step Functions"),
    "AWS Cost Management": ("AWS Budgets", "AWS Cost and Usage Report", "AWS Cost Explorer", "Savings Plans"),
    "Compute": ("AWS Batch", "Amazon EC2", "Amazon EC2 Auto Scaling", "AWS Elastic Beanstalk", "AWS Outposts", "AWS Serverless Application Repository", "VMware Cloud on AWS", "AWS Wavelength"),
    "Containers": ("Amazon ECR", "Amazon ECS", "Amazon ECS Anywhere", "Amazon EKS", "Amazon EKS Anywhere", "Amazon EKS Distro"),
    "Database": ("Amazon Aurora", "Amazon Aurora Serverless", "Amazon DocumentDB", "Amazon DynamoDB", "Amazon ElastiCache", "Amazon Keyspaces", "Amazon Neptune", "Amazon RDS", "Amazon Redshift"),
    "Developer Tools": ("AWS X-Ray",),
    "Front-End Web and Mobile": ("AWS Amplify", "Amazon API Gateway", "AWS Device Farm"),
    "Machine Learning": ("Amazon Comprehend", "Amazon Lex", "Amazon Polly", "Amazon Rekognition", "Amazon SageMaker AI", "Amazon Textract", "Amazon Transcribe", "Amazon Translate"),
    "Management and Governance": ("AWS Auto Scaling", "AWS CLI", "AWS CloudFormation", "AWS CloudTrail", "Amazon CloudWatch", "AWS Compute Optimizer", "AWS Config", "AWS Control Tower", "AWS Health Dashboard", "AWS License Manager", "Amazon Managed Grafana", "Amazon Managed Service for Prometheus", "AWS Management Console", "AWS Organizations", "AWS Service Catalog", "AWS Systems Manager", "AWS Trusted Advisor", "AWS Well-Architected Tool"),
    "Media Services": ("Amazon Elastic Transcoder", "Amazon Kinesis Video Streams"),
    "Migration and Transfer": ("AWS Application Migration Service", "AWS DataSync", "AWS DMS", "AWS Snow Family", "AWS Transfer Family"),
    "Networking and Content Delivery": ("AWS Client VPN", "Amazon CloudFront", "AWS Direct Connect", "Elastic Load Balancing (ELB)", "AWS Global Accelerator", "AWS PrivateLink", "Amazon Route 53", "AWS Site-to-Site VPN", "AWS Transit Gateway", "Amazon VPC"),
    "Security, Identity, and Compliance": ("AWS Artifact", "AWS Certificate Manager (ACM)", "AWS CloudHSM", "Amazon Cognito", "Amazon Detective", "AWS Directory Service", "AWS Firewall Manager", "Amazon GuardDuty", "AWS IAM Identity Center", "Amazon Inspector", "AWS KMS", "Amazon Macie", "AWS Network Firewall", "AWS Resource Access Manager (AWS RAM)", "AWS Secrets Manager", "AWS Security Hub", "AWS Shield", "AWS WAF", "IAM"),
    "Serverless": ("AWS Fargate", "AWS Lambda"),
    "Storage": ("AWS Backup", "Amazon EBS", "Amazon EFS", "Amazon FSx (for all types)", "Amazon S3", "Amazon S3 Glacier", "AWS Storage Gateway"),
}

SAP_SCOPE = {
    "Analytics": ("Amazon Athena", "AWS Data Exchange", "Amazon Data Firehose", "Amazon EMR", "AWS Glue", "Amazon Kinesis Data Streams", "AWS Lake Formation", "Amazon Managed Service for Apache Flink", "Amazon Managed Streaming for Apache Kafka (Amazon MSK)", "Amazon OpenSearch Service", "Amazon QuickSight"),
    "Application Integration": ("Amazon AppFlow", "AWS AppSync", "Amazon EventBridge", "Amazon MQ", "Amazon Simple Notification Service (Amazon SNS)", "Amazon Simple Queue Service (Amazon SQS)", "AWS Step Functions"),
    "Blockchain": ("Amazon Managed Blockchain",),
    "Business Applications": ("Amazon Simple Email Service (Amazon SES)",),
    "Cloud Financial Management": ("AWS Budgets", "AWS Cost and Usage Report", "AWS Cost Explorer", "Savings Plans"),
    "Compute": ("AWS App Runner", "AWS Auto Scaling", "AWS Batch", "AWS Elastic Beanstalk", "Amazon Elastic Compute Cloud (Amazon EC2)", "Amazon EC2 Auto Scaling", "AWS Fargate", "AWS Lambda", "Amazon Lightsail", "AWS Outposts", "AWS Wavelength"),
    "Containers": ("Amazon Elastic Container Registry (Amazon ECR)", "Amazon Elastic Container Service (Amazon ECS)", "Amazon ECS Anywhere", "Amazon Elastic Kubernetes Service (Amazon EKS)", "Amazon EKS Anywhere", "Amazon EKS Distro"),
    "Database": ("Amazon Aurora", "Amazon Aurora Serverless", "Amazon DocumentDB (with MongoDB compatibility)", "Amazon DynamoDB", "Amazon ElastiCache", "Amazon Keyspaces (for Apache Cassandra)", "Amazon Neptune", "Amazon Relational Database Service (Amazon RDS)", "Amazon Redshift", "Amazon Timestream"),
    "Developer Tools": ("AWS CodeArtifact", "AWS CodeBuild", "AWS CodeDeploy", "Amazon CodeGuru", "AWS CodePipeline", "AWS X-Ray"),
    "End User Computing": ("Amazon AppStream 2.0", "Amazon WorkSpaces"),
    "Frontend Web and Mobile": ("AWS Amplify", "Amazon API Gateway", "AWS Device Farm", "Amazon Pinpoint"),
    "Internet of Things (IoT)": ("AWS IoT Core", "AWS IoT Device Defender", "AWS IoT Device Management", "AWS IoT Events", "AWS IoT Greengrass", "AWS IoT SiteWise", "AWS IoT Things Graph", "AWS IoT 1-Click"),
    "Machine Learning": ("Amazon Comprehend", "Amazon Fraud Detector", "Amazon Kendra", "Amazon Lex", "Amazon Personalize", "Amazon Polly", "Amazon Rekognition", "Amazon SageMaker AI (previously known as Amazon SageMaker)", "Amazon Textract", "Amazon Transcribe", "Amazon Translate"),
    "Media Services": ("Amazon Elastic Transcoder", "Amazon Kinesis Video Streams"),
    "Management and Governance": ("AWS CloudFormation", "AWS CloudTrail", "Amazon CloudWatch", "Amazon CloudWatch Logs", "AWS Command Line Interface (AWS CLI)", "AWS Compute Optimizer", "AWS Config", "AWS Control Tower", "AWS Health Dashboard", "AWS License Manager", "Amazon Managed Grafana", "Amazon Managed Service for Prometheus", "AWS Management Console", "AWS Organizations", "AWS Proton", "AWS Service Catalog", "Service Quotas", "AWS Systems Manager", "AWS Trusted Advisor", "AWS Well-Architected Tool"),
    "Migration and Transfer": ("AWS Application Discovery Service", "AWS Application Migration Service", "AWS Database Migration Service (AWS DMS)", "AWS DataSync", "AWS Migration Hub", "AWS Schema Conversion Tool (AWS SCT)", "AWS Snow Family", "AWS Transfer Family"),
    "Networking and Content Delivery": ("Amazon CloudFront", "AWS Direct Connect", "Elastic Load Balancing (ELB)", "AWS Global Accelerator", "AWS PrivateLink", "Amazon Route 53", "AWS Transit Gateway", "Amazon Virtual Private Cloud (Amazon VPC)", "AWS VPN"),
    "Security, Identity, and Compliance": ("AWS Artifact", "AWS Audit Manager", "AWS Certificate Manager (ACM)", "AWS CloudHSM", "Amazon Cognito", "Amazon Detective", "AWS Directory Service", "AWS Firewall Manager", "Amazon GuardDuty", "AWS IAM Identity Center", "AWS Identity and Access Management (IAM)", "Amazon Inspector", "AWS Key Management Service (AWS KMS)", "Amazon Macie", "AWS Network Firewall", "AWS Resource Access Manager (AWS RAM)", "AWS Secrets Manager", "AWS Security Hub", "AWS Security Token Service (AWS STS)", "AWS Shield", "AWS WAF"),
    "Storage": ("AWS Backup", "Amazon Elastic Block Store (Amazon EBS)", "AWS Elastic Disaster Recovery", "Amazon Elastic File System (Amazon EFS)", "Amazon FSx (for all types)", "Amazon Simple Storage Service (Amazon S3)", "Amazon S3 Glacier", "AWS Storage Gateway"),
}
