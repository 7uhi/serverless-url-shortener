# Costs, Free plan support, and future deployment

## Current phase

Local development creates **no AWS usage charges**. The server uses SQLite, and DynamoDB tests use Moto in memory. No AWS resources, IAM permissions, plan settings, or billing settings were changed.

The previous read-only connection check identified the Blank Canvas project, an active Free plan, and selected Region `us-east-2`. The architecture uses services listed as supported in the [new experience Free Tier](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-free-tier): Lambda, API Gateway, DynamoDB, CloudWatch/Logs, IAM, CloudFormation, and S3 for eventual SAM deployment artifacts. SAM is a local infrastructure tool that generates CloudFormation resources.

The supported-service list establishes service compatibility, not proof that every deployment operation will be permitted. AWS-managed controls and the actual deployment permissions must be checked before deployment. No upgrade is required by this design.

## Small-demo estimate

Illustrative assumption: 10,000 total API/Lambda requests in a month, averaging 100 ms at 128 MB, including frontend asset requests; approximately 1,000 link creations and 8,000 redirects; records under 1 KB for this estimate, very small stored data, and less than 0.1 GB of logs. Actual record sizes can be larger (up to the validation limit), increasing billed write units.

Using public starting rates as a rough US-region planning example, before credits/allowances:

| Usage | Approximate amount |
| --- | --- |
| HTTP API: 10,000 requests at about $1/million | $0.01 |
| Lambda requests: 10,000 at $0.20/million | $0.002 |
| Lambda duration: 125 GB-seconds at about $0.0000166667 | $0.0021 |
| DynamoDB: ~11,000 small writes, including two limiter writes per creation, at ~$0.625/million | $0.0069 |
| DynamoDB statistics reads and small storage | Small additional usage |
| Logs: under 0.1 GB ingested, at about $0.50/GB | Under $0.05, plus storage |

This suggests ordinary light demo use well below $1/month before applicable credits. It is **not a quote or spending cap**. Regions, pricing tiers, request sizes, Lambda initialization/duration, failed conditions, retries, logs, data transfer, artifact storage, and expired retained data can change the total. Check Ohio-specific pricing and credit applicability again before deployment. Free credits are finite and plan eligibility/expiration matters; do not equate the Free plan with unlimited free operation.

Sources checked during this build:

- [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)

## Cost-conscious template choices

- Lambda on-demand, 128 MB, 10-second timeout; no always-running servers, VPC/NAT gateway, provisioned concurrency, or custom domain.
- DynamoDB on-demand, no secondary indexes or streams, 30-day link expiration.
- Seven-day retention for application and API access logs; no bodies, IPs, or destination URLs logged.
- API default throttling target: 5 requests/second, burst 10. This is not a hard cap or budget.
- Shared creation limits: 20/minute and 500/day. Reads, redirects, invalid requests, and rate-limit checks still incur AWS usage.
- Built-in service metrics; no custom metrics, alarm, or dashboard resources in this phase.
- Retain the DynamoDB table on stack deletion/replacement to prevent accidental data loss. Retention can leave billable storage and requires a separate, explicitly approved cleanup decision.

## Before the next phase

1. Confirm **AWS Settings → View all projects → Overview → Additional Info → Region** is `us-east-2`.
2. Check plan, remaining credits, expiration, and spending status in **AWS Settings → Billing**. Do not upgrade the plan implicitly.
3. Review the source, tests, SAM template, destination policy, and public access model together.
4. Install SAM CLI locally and run a build for Python 3.12. A build packages code locally; it does not deploy it.
5. Present the exact proposed cloud resources and expected costs. Obtain explicit approval for deployment, artifact storage, and the new least-privilege execution role.
6. Only after approval, use profile `student-aws`, Region `us-east-2`, review the CloudFormation change set, and deploy.
7. Verify create/redirect/stats in AWS, inspect CloudWatch metrics/logs, and record real usage.
8. Ask whether to keep the resources or perform an explicitly approved cleanup after the demo. Never delete resources automatically.

No deployment, upgrade, permissions change, GitHub publication, or cleanup command is executed by this repository's local run/test workflow.
