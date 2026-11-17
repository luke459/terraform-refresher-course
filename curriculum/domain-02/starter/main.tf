resource "aws_ssm_parameter" "us" {
  name  = "/tf004/${var.attempt_id}/region"
  type  = "String"
  value = "us-east-1"
}
resource "aws_ssm_parameter" "uk" {
  provider = aws
  name     = "/tf004/${var.attempt_id}/region"
  type     = "String"
  value    = "wrong-region"
}
output "parameter_name" { value = aws_ssm_parameter.us.name }
