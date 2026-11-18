# Lab 05: build an app tier you can reuse

Your goal: use `modules/app-tier` for two environments, dev and stage. Each child receives a typed network object and environment/attempt inputs, creates a VPC, subnet and security group, and returns IDs through outputs. The root saves both VPC IDs in a standard SSM parameter.

The starter tries to read `tier.aws_vpc.app.id` from inside the child. Find the child's output and use `tier.vpc_id` instead. Keep `for_each` on the module call so the environment names stay part of the addresses.

1. Read the child inputs and outputs, then fix the root summary expression.
2. Initialize, format and validate from the terminal. Check that the local module installs successfully.
3. Save a plan for both environments as `tfplan`, review the changes, then apply it.
4. Inspect the `module.app_tier["dev"]` and `module.app_tier["stage"]` state addresses and their different Environment tags.
5. Make a fresh saved plan with detailed exit codes, then run `lab grade`. The checks cover both module instances, ownership and the summary output.
6. Destroy the resources and run `lab check-cleanup` for both environments.

Allow 40 minutes. Resources: two VPCs, two subnets, two security groups and one standard SSM parameter. Keep the networking private and empty, with no compute, NAT or public IPs. Target cost: below $0.01 for a short session in any supported region, before credits. Assumptions dated 2026-11-14.

One versioning detail to remember: registry modules use `version`, Git modules use a source ref, and the provider lockfile doesn't pin module packages.
