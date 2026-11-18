# Lab 08: connect HCP concepts to a local AWS workflow

You don't need an HCP Terraform organization, workspace, login or token. Explore the hosted concepts in Governance & Hierarchy Sandbox, then use your existing AWS connection to practise with a real SNS topic.

The starter's topic suffix is wrong. Change the name to `tf004-${var.attempt_id}-hcp`, keeping the supplied account, region and ownership tags. Terraform runs locally here; this lab doesn't create a hosted HCP run.

1. Try the sandbox scenarios for projects and workspaces, variable-set scope, run triggers, speculative plans, and Sentinel versus OPA enforcement.
2. Start the AWS lab, fix the SNS name, then initialize, format and validate from the terminal.
3. Save a plan as `tfplan`, read the changes and apply it. The terminal uses your selected profile or access keys.
4. Make a fresh saved plan with detailed exit codes, then run `lab grade`. The checks cover local state, the live topic, no unexpected changes and ownership.
5. Destroy the resources and run `lab check-cleanup` to reach 100%.

Allow 35 minutes for the AWS challenge plus the conceptual lesson. Resources: one empty SNS topic. No subscriptions, message publishing, paid HCP services or OIDC setup. Target cost: below $0.01 for a short session in any supported region, before credits. Assumptions dated 2026-11-14.

For the exam, keep practising where remote, local and agent runs execute; what CLI, VCS and API workflows trigger; and how teams use registries, health checks and policies. The lesson and practice questions cover these without another account to set up.
