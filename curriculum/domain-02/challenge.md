# Lab 02: route two provider configurations correctly

Create one standard SSM String parameter in us-east-1 and another with the same name in eu-west-2. Each parameter's value must be its own AWS region. The default provider belongs to us-east-1; the `uk` alias belongs to eu-west-2, regardless of your course's primary region.

The starter routes the UK parameter to the default provider and gives it an incorrect value. Fix its provider binding and value. Keep the `~> 5.80` constraint and the committed compatible lockfile selection. Both provider configurations must retain attempt ownership tags.

1. Start the lab and inspect providers.tf and main.tf.
2. Fix the UK resource. Run Init, Format and Validate config.
3. Run Provider lock to record linux_amd64, linux_arm64 and darwin_arm64 checksums. This is a graded command receipt.
4. Plan, inspect the two regional resources, and apply the saved plan.
5. Run a second Plan, then Grade lab. Both AWS regional values and ownership must pass.
6. Destroy and Verify cleanup; both regions must be empty for this attempt.

Allow 35 minutes. Resources: two standard SSM parameters, one per region. Budget target below $0.01 in gross short-session usage; use only standard parameters and no high-throughput feature. Account credits and free allowances vary. Pricing assumptions dated 2026-11-14. No DynamoDB, EC2, or other paid compute is needed.

Lockfile hashes do not contain platform labels. The explicit locking command and readonly initialization on each supported platform provide the portability evidence.
