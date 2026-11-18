# Lab 02: send each resource to the right region

Your goal: create two standard SSM String parameters with the same name, one in us-east-1 and one in eu-west-2. Each value should name its own region. Use us-east-1 for the default provider and eu-west-2 for `aws.uk`, regardless of your course's primary region.

The starter sends the UK parameter to the default provider and sets the wrong value. Fix both, keeping the `~> 5.80` constraint, compatible lockfile selection and ownership tags on both providers.

1. Start the lab and read `providers.tf` and `main.tf` in the editor.
2. Fix the UK resource, then initialize, format and validate from the terminal.
3. Use Terraform's provider-locking command to add checksums for linux_amd64, linux_arm64 and darwin_arm64. This command is part of the lab checks.
4. Save a plan as `tfplan`. Check the regions in its output, then apply that saved plan.
5. Make a fresh saved plan with detailed exit codes, then run `lab grade`. The checks look at both regional values and their ownership tags.
6. Destroy the resources, then run `lab check-cleanup`. Both parameters must be gone to finish.

Allow 35 minutes. Resources: two standard SSM parameters. Target cost: below $0.01 for a short session, before credits. Use standard parameters without high throughput; free allowances vary by account. Assumptions dated 2026-11-14. You won't need DynamoDB, EC2 or other paid compute.

If you're checking portability, don't look for platform labels inside lockfile hashes. Use the explicit locking command and test readonly initialization on each supported platform.
