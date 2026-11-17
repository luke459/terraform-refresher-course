# Lab 01: turn an imperative script into desired state

Create a versioned S3 bucket and a standard SSM String parameter containing the exact value `{"environment":"refresher","project":"tf-004-prep"}`. Read `create_s3_and_ssm.sh` to understand the original workflow; do not run it, since the Terraform lab should own creation.

The starter deliberately suspends versioning and uses the wrong parameter value. Correct both without changing the injected account, region, attempt ID, ownership tags, or resource names.

1. Start an attempt and open its workspace in your IDE or the course editor.
2. Fix the HCL, then run Init, Format, Validate config, Plan and Apply saved plan.
3. Run Plan again. It must succeed with detailed exit code 0.
4. Run Grade lab. All checks must pass for 50% verification.
5. Run Destroy, then Verify cleanup. The bucket and parameter must be absent for 100% completion.

Expected resources: one bucket, its versioning configuration, and one standard SSM parameter. Allow 20–30 minutes. Short-lived usage targets less than $0.01 in eu-west-1, us-east-1 or eu-west-2 before account-specific credits; S3 storage/requests can incur charges. Pricing assumptions dated 2026-11-14: no object uploads, no advanced SSM parameters, and teardown in the same session. The estimate is not a free-tier guarantee.

If apply is interrupted, retain the workspace and use the cleanup inventory before starting another attempt. Never delete the state file as a cleanup shortcut.

