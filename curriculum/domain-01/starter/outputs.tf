output "bucket_name" {
  value = aws_s3_bucket.course.id
}

output "parameter_name" {
  value = aws_ssm_parameter.metadata.name
}

