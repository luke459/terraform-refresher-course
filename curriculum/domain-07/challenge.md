# Lab 07: adopt existing infrastructure

Create the course's unmanaged S3 bucket and read-only IAM policy through the provided setup action. Then adopt those exact objects with import blocks, generate their initial resource configuration, refine it, and finish with no replacements or plan changes.

1. Start the lab and choose Create import fixtures. The action creates uniquely named, tagged objects and saves their identities for cleanup even before import.
2. Inspect imports.tf: the bucket import ID is its name; the policy import ID is its ARN. Do not replace them with new objects.
3. Init, then Generate config. Terraform writes generated.tf. Review it rather than applying generated arguments blindly.
4. Refine generated.tf or replace its resource declarations with the reference main.tf. Avoid duplicate resource blocks: keep one declaration per imported address. Keep both import blocks for review.
5. Enable private provider debug capture, then Plan and Apply saved plan. Disable debug capture afterward. Review resource IDs against the setup baseline.
6. Run a no-change Plan and Grade lab. The grader requires import declarations, generation provenance, preserved IDs, provider log evidence, and owned live resources.
7. Destroy and Verify cleanup. If import failed halfway through, preview recovery inventory; the setup resources are still owned by this attempt and must not be orphaned.

Use state list/show/pull drills in the lesson's disposable examples. state rm removes an association and leaves infrastructure running. Debug logs can expose sensitive provider data: inspect locally, do not share raw logs, and purge them after the exercise.

From the repository, run `make state-drills` for an automated disposable local exercise of `state list`, `state show`, `state pull`, `state mv`, and `state rm`. It uses the built-in `terraform_data` resource, checks that moving preserves the ID and forgetting leaves configuration proposing creation, and removes its temporary directory. No AWS connection is needed.

Allow 45 minutes. Resources: one empty S3 bucket and one unattached IAM policy allowing only GetBucketLocation on that bucket. IAM is account-global; the bucket uses the selected region. No compute. Gross short-session target below $0.01 before credits, assuming no object uploads; assumptions dated 2026-11-14.
