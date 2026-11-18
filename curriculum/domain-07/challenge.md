# Lab 07: bring existing resources under Terraform management

Your goal: import the course's existing S3 bucket and read-only IAM policy, generate a starting configuration, then finish with no replacements or unexpected changes.

1. Run `lab setup-import`. This creates uniquely named, tagged objects and records their IDs for cleanup before you import them.
2. Read `imports.tf`: the bucket's import ID is its name; the policy's is its ARN. Keep these exact objects.
3. Initialize, then use Terraform's plan option to generate `generated.tf`. Read that file before applying anything.
4. Refine `generated.tf`, or use the reference `main.tf` resource declarations. Keep one declaration per imported address and retain both import blocks.
5. Prefix your plan and apply commands with `TF_LOG_PROVIDER=DEBUG` to capture provider logs. Save and review `tfplan` before applying it. Use normal logging afterward. Compare the resource IDs with the setup baseline.
6. Make a fresh saved plan with detailed exit codes, then run `lab grade`. The checks look for the imports, configuration-generation record, preserved IDs, provider log and live owned resources.
7. Destroy the resources and run `lab check-cleanup`. If import stopped halfway through, use the recovery inventory: the setup objects still need cleanup.

Practise `state list`, `state show` and `state pull` with the lesson's disposable examples. Remember that `state rm` leaves the AWS object running. Read debug logs locally and remove them afterward; raw logs can contain secrets.

From the host repository, run `make state-drills` to try list/show/pull/mv/rm with a temporary `terraform_data` resource. The drill checks that moving keeps the ID and that forgetting an object leaves its configuration proposing creation. It cleans up its temporary directory and needs no AWS connection.

Allow 45 minutes. Resources: one empty S3 bucket and one unattached IAM policy allowing only GetBucketLocation on that bucket. IAM is account-global; the bucket uses your selected region. No compute or object uploads. Target cost: below $0.01 for a short session, before credits. Assumptions dated 2026-11-14.
