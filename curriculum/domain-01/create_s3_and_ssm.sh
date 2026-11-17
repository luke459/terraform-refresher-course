#!/usr/bin/env bash
# Reading exercise only: use Terraform for the actual lab's creation/ownership.
set -euo pipefail
: "${COURSE_BUCKET:?Set a unique bucket name}"
: "${COURSE_PARAMETER:?Set a unique parameter name}"
aws s3api create-bucket --bucket "$COURSE_BUCKET" --region us-east-1
aws s3api put-bucket-versioning --bucket "$COURSE_BUCKET" --versioning-configuration Status=Enabled
aws ssm put-parameter --name "$COURSE_PARAMETER" --type String --value '{"environment":"refresher","project":"tf-004-prep"}'

