resource "aws_s3_bucket" "course" {
  bucket        = "tf004-${var.account_id}-${var.attempt_id}-01"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "course" {
  bucket = aws_s3_bucket.course.id
  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_ssm_parameter" "metadata" {
  name  = "/tf004/${var.attempt_id}/metadata"
  type  = "String"
  tier  = "Standard"
  value = jsonencode({ environment = "outdated", project = "tf-004-prep" })
}

