# Lab cost assumptions

The course targets less than **$0.01 of gross AWS usage per short lab attempt**, before account-specific credits. This is an estimate rather than a price guarantee or spending cap. No required lab creates compute instances, NAT gateways, EKS clusters, RDS instances, public IPs or paid HCP infrastructure.

Available primary regions are eu-west-1 (Ireland), us-east-1 (N. Virginia), and eu-west-2 (London); the default remains us-east-1. Domain 02 uses its fixed us-east-1/eu-west-2 pair; other labs use the selected primary region. Every challenge records its resource count, intended duration, estimate and pricing date. The assumptions below were reviewed on 2026-11-14; primary S3 and Secrets Manager pricing sources were rechecked on 2026-11-16.

Budget **less than $0.10 for one full course run with prompt cleanup**, or **less than $1 for repeated build-verification runs**. These are gross usage estimates for resources created by this course, before credits and taxes; they are not measured billing totals or account-wide spending caps. Keeping resources longer increases usage, especially the Secrets Manager secret and retained S3 state versions. HCP concepts run locally and add no HCP subscription dependency.

| Lab | Intended resources | Main cost considerations |
| --- | --- | --- |
| 01 | Empty versioned bucket and standard SSM metadata parameter | S3 requests/storage; no uploads |
| 02 | Two standard SSM parameters in separate regions | Standard parameter settings only |
| 03 | Empty VPC/subnet/security group; temporary overlapping group replacement | No attached compute, NAT, endpoints or IP charges |
| 04 | Empty VPC/security groups and a short-lived secret/version | Secrets Manager storage time and API requests; no rotation service or replicas |
| 05 | Two empty VPC/subnet/security-group tiers and one standard parameter | No attached paid networking/compute features |
| 06 | Versioned encrypted state bucket, state/lock objects, two standard parameters | State object requests and retained versions; destroy the bucket last |
| 07 | Empty bucket and an unattached read-only IAM policy | Bucket requests; global IAM inventory |
| 08 | One empty SNS topic | No subscriptions or message publishing; no HCP dependency |

AWS Secrets Manager bills storage and API use; its pricing examples distinguish stored-secret duration and request count. S3 state versioning can retain older snapshots and deletion markers, so ordinary object deletion is not sufficient bucket cleanup. Free Tier eligibility and credits depend on the account, and billing data can arrive after the session.

For a learner session, a small account budget provides extra operational feedback, but the application does not claim that a billing alarm prevents every charge. The executable protections are constrained resource types/counts, unique attempt ownership, explicit apply actions, and mandatory teardown. Repeated test suites generate more service requests than one learner attempt.

Consult current primary pricing pages for your account and region:

- [S3 pricing](https://aws.amazon.com/s3/pricing/)
- [Systems Manager pricing](https://aws.amazon.com/systems-manager/pricing/)
- [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/)
- [SNS pricing](https://aws.amazon.com/sns/pricing/)
- [VPC pricing](https://aws.amazon.com/vpc/pricing/)
- [AWS Free Tier](https://aws.amazon.com/free/)
