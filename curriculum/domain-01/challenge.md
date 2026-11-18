# Lab 01: turn a script into Terraform configuration

Your goal: create a versioned S3 bucket and a standard SSM String parameter with the exact value `{"environment":"refresher","project":"tf-004-prep"}`.

Start by reading `create_s3_and_ssm.sh` to see the original approach. Leave the script unrun so Terraform can create and track the resources itself. The starter has two things to fix: versioning is suspended, and the parameter value is wrong. Keep the supplied account, region, attempt ID, tags and resource names.

1. Start an attempt. Your files appear in the workspace editor beside this challenge; you can also use your IDE.
2. Fix the HCL, then use the terminal to initialize, format and validate. Save a plan as `tfplan`, read it, then apply that saved plan.
3. Make a fresh saved plan with detailed exit codes. Look for no changes and exit code 0.
4. Run `lab grade`. Passing all checks earns 50%.
5. Destroy the resources from the terminal and confirm when prompted, then run `lab check-cleanup`. Once the bucket and parameter are gone, you'll reach 100%.

Allow 20–30 minutes. You'll create one bucket, its versioning configuration and one standard SSM parameter. Target cost: below $0.01 for a short session in eu-west-1, us-east-1 or eu-west-2, before credits. S3 storage and requests can cost money; this isn't a free-tier guarantee. Assumptions dated 2026-11-14: no uploads, no advanced SSM parameters, and cleanup in the same session.

If apply stops halfway through, keep the workspace and check the cleanup inventory before starting over. Deleting state won't clean up resources in AWS.
