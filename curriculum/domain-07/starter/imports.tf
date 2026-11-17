import {
  to = aws_s3_bucket.imported
  id = "tf004-${var.account_id}-${var.attempt_id}-import"
}
import {
  to = aws_iam_policy.imported
  id = "arn:aws:iam::${var.account_id}:policy/tf004-${var.attempt_id}-import"
}
