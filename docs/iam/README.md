# AWS lab permission templates

These per-lab JSON files are reviewable starting templates, not policies that the application attaches automatically. Replace `${ACCOUNT_ID}`, `${REGION}` and `${ATTEMPT_ID}` with the intended account, region and exact attempt. For domain 02, include the corresponding resource scopes for both us-east-1 and eu-west-2. IAM policy resources are account-global.

The templates restrict writes by course names or ownership tags and allow the list/describe operations needed for verification/recovery. Several AWS describe/list actions require Resource `*`; that does not grant arbitrary account-wide mutation. EC2 create/tag and resource-tag conditions should be reviewed with your organization's IAM rules, boundaries and SCPs. Some recovery operations can require temporarily restoring a missing tag before their resource-tag condition succeeds.

The course's test profile was provided by the user. A successful run under that profile does not prove these templates against every permission boundary. Validate and test a scoped lab role in your own environment before relying on a template as a final IAM policy. The app's STS identity check proves identity, not universal service authorization; a denied service call remains an explicit error.

| Lab | Write scope |
| --- | --- |
| 01 | Attempt-named S3 bucket/objects and SSM path |
| 02 | Attempt SSM path in both regions |
| 03 | Tagged disposable VPC/subnet/security group |
| 04 | Tagged disposable networking and attempt-named Secrets Manager secret |
| 05 | Tagged dev/stage networking and SSM summary |
| 06 | Attempt state bucket/objects/lockfile and SSM parameters |
| 07 | Attempt bucket and one unattached import-policy ARN |
| 08 | Attempt-named SNS topic |

No policy template grants NAT Gateway, EKS, RDS, EC2 instance, IAM access-key, HCP identity-provider or HCP role creation. The runner also checks planned managed resource types/counts and exact tags before applying a saved plan.

Reference the [AWS service authorization documentation](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) when adapting these policies. Attaching or modifying IAM policies is a separate administrative operation; generating these files does not change account permissions.
