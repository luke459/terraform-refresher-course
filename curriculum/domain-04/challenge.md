# Lab 04: check your inputs and keep a password out of state

Your goal: create one security group per service from the typed services map, and send an ephemeral password to Secrets Manager without saving it in Terraform state or plans.

Use input validation for CIDRs and ports, a precondition to block public SSH, a postcondition to check the VPC, and a top-level check for the service count. Generate an ephemeral `random_password` and pass it through `secret_string_wo` with its version counter.

1. Initialize, format and validate from the terminal. The pinned providers support the ephemeral password and write-only field.
2. Try planning before fixing the starter. Find the precondition that rejects SSH from `0.0.0.0/0`. Invalid ports and CIDRs must also be rejected.
3. Change the SSH CIDR to `10.44.1.0/24`, keeping the supplied VPC and ownership values. Save and review a plan as `tfplan`, then apply it; all conditions and checks must pass.
4. Make another saved plan with detailed exit codes, then run `lab grade`. It must show no managed-resource or root-output changes. A scoped check data source can still need a read on Terraform 1.12, producing detailed exit code 2; this grader checks the structured plan. It also compares the actual secret with state, plan data and saved files in memory, without printing it.
5. Try State Leak Inspector to see why hiding output isn't enough. Keep the password out of outputs too.
6. Destroy the resources and run `lab check-cleanup`. This disposable secret uses a zero-day recovery window, but AWS deletion can take time. Retry the check if deletion is still pending.

When you deliberately change the write-only value, increment `secret_version`: Terraform can't compare its old value in state. Keep AWS access keys out of HCL. You won't need a Vault service for this lesson.

Allow 50 minutes. Resources: one VPC, two security groups, one ephemeral password and one Secrets Manager secret/version. Target cost: below $0.01 for a short session in any supported region, with no replicas or rotation service. Secrets Manager storage and API requests are billable; this isn't a free-tier guarantee. Assumptions dated 2026-11-14.
