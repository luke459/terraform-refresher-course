# Lab 08: HCP concepts with a local AWS workflow

No HCP Terraform organization, workspace, login or API token is required. Learn the hosted-platform concepts in the local Governance & Hierarchy Sandbox, then practice the same review/apply/cleanup discipline with a real SNS topic using your existing AWS connection.

The starter uses an incorrect topic name suffix. Correct it to tf004-${var.attempt_id}-hcp. Keep the injected account, region and ownership tags. This is a local Terraform workflow; it does not simulate a real remote deployment or earn evidence of an actual HCP run.

1. Complete the sandbox scenarios for projects/workspaces, variable-set scope, run triggers, speculative plans, and Sentinel versus OPA enforcement behavior.
2. Start the AWS lab. Fix the SNS topic name, then Init, Format and Validate config.
3. Plan, review, and apply the saved plan locally with the selected profile or access keys.
4. Run another Plan and Grade lab. The local state, live SNS topic, idempotency and ownership must pass.
5. Destroy the topic and Verify cleanup for 100% completion.

Allow 35 minutes for the AWS challenge plus the conceptual lesson. Resources: one empty SNS topic. No subscriptions, message publishing, paid HCP services or OIDC bootstrap resources. Gross usage target below $0.01 in any supported course region for this topology before account credits; assumptions dated 2026-11-14.

The exam still expects knowledge of HCP remote, local and agent execution; CLI/VCS/API triggers; team access; private registries; health and governance. The lesson and original questions cover these without introducing an external account dependency.
