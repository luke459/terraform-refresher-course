resource "aws_ssm_parameter" "us" {
  name  = "/tf004/${var.attempt_id}/region"
  type  = "String"
  value = "us-east-1"
}
resource "aws_ssm_parameter" "uk" {
  provider = aws.uk
  name     = "/tf004/${var.attempt_id}/region"
  type     = "String"
  value    = "eu-west-2"
}
output "parameter_name" { value = aws_ssm_parameter.us.name }
