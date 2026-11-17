# Lab 05: create a reusable app tier

Use the local modules/app-tier child module for two environments, dev and stage. Each child accepts a typed network object and explicit environment/attempt inputs, creates a VPC/subnet/security group, and publishes IDs through outputs. The root writes a standard SSM summary of both VPC IDs.

The starter tries to read a child resource through tier.aws_vpc.app.id. Correct that boundary to use the child output tier.vpc_id. Keep for_each on the module call so the environment names determine stable addresses.

1. Inspect the child inputs and outputs, then fix the root summary expression.
2. Run Init, Format and Validate config. Local module initialization must succeed.
3. Plan both environments and apply the saved plan.
4. Inspect module.app_tier["dev"] and module.app_tier["stage"] state addresses and their distinct Environment tags.
5. Run a no-change Plan, then Grade lab. Both module hierarchies, their ownership and the output summary must match.
6. Destroy and Verify cleanup for both environments together.

Allow 40 minutes. Resources: two VPCs, two subnets, two security groups and one standard SSM parameter. Use only private, empty networking resources; no compute, NAT or public IPs. Gross short-session target below $0.01 in any supported course region before credits; assumptions dated 2026-11-14.

The lesson also covers registry, Git and S3 module sources. Registry modules use the version argument; Git modules use a source ref. The provider lockfile does not pin module packages.
