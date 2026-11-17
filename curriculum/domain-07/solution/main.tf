resource "aws_s3_bucket" "imported" {
  bucket        = "tf004-${var.account_id}-${var.attempt_id}-import"
  force_destroy = true
}
resource "aws_iam_policy" "imported" {
  name        = "tf004-${var.attempt_id}-import"
  description = "Disposable Terraform import exercise"
  policy      = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["s3:GetBucketLocation"], Resource = "arn:aws:s3:::tf004-${var.account_id}-${var.attempt_id}-import" }] })
}
output "bucket_name" { value = aws_s3_bucket.imported.id }
output "policy_arn" { value = aws_iam_policy.imported.arn }
